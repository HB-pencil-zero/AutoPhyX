"""AutoPhyX-style text-conditioned physics property predictor."""

from __future__ import annotations

import logging
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class DoubleConv3d(nn.Module):
    """Two Conv3d-BatchNorm-LeakyReLU blocks."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm3d(out_channels, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm3d(out_channels, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Down3d(nn.Module):
    """Downsample by 2, then apply DoubleConv3d."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.net = nn.Sequential(nn.MaxPool3d(2), DoubleConv3d(in_channels, out_channels))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Up3d(nn.Module):
    """Upsample, concatenate skip features, then apply DoubleConv3d."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode="trilinear", align_corners=True)
        self.conv = DoubleConv3d(in_channels + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        diff_d = skip.size(2) - x.size(2)
        diff_h = skip.size(3) - x.size(3)
        diff_w = skip.size(4) - x.size(4)
        if diff_d or diff_h or diff_w:
            x = F.pad(
                x,
                [
                    diff_w // 2,
                    diff_w - diff_w // 2,
                    diff_h // 2,
                    diff_h - diff_h // 2,
                    diff_d // 2,
                    diff_d - diff_d // 2,
                ],
            )
        return self.conv(torch.cat([skip, x], dim=1))


class OpenClipTextEncoder(nn.Module):
    """Lazy OpenCLIP text encoder.

    The default ViT-L-14-336-quickgelu model returns 768-dimensional text
    embeddings, matching common CLIP/OpenCLIP voxel feature dimensions.
    """

    def __init__(
        self,
        model_name: str = "ViT-L-14-336-quickgelu",
        pretrained: str = "openai",
        freeze: bool = True,
        max_length: int = 77,
    ):
        super().__init__()
        self.model_name = model_name
        self.pretrained = pretrained
        self.freeze = freeze
        self.max_length = max_length
        self.output_dim = 768
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self, device: torch.device) -> None:
        if self._model is not None:
            if next(self._model.parameters()).device != device:
                self._model = self._model.to(device)
            return

        try:
            import open_clip
        except ImportError as exc:
            raise ImportError("Install open-clip-torch to use OpenClipTextEncoder") from exc

        self._model, _, _ = open_clip.create_model_and_transforms(
            self.model_name,
            pretrained=self.pretrained,
            device=device,
        )
        self._tokenizer = open_clip.get_tokenizer(self.model_name)
        if self.freeze:
            for param in self._model.parameters():
                param.requires_grad = False
            self._model.eval()
        logger.info("Loaded OpenCLIP %s/%s on %s", self.model_name, self.pretrained, device)

    @torch.no_grad()
    def forward(self, texts: List[str], device: Optional[torch.device] = None) -> torch.Tensor:
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._ensure_loaded(device)
        tokens = self._tokenizer(texts, context_length=self.max_length).to(device)
        features = self._model.encode_text(tokens).float()
        return features / features.norm(dim=-1, keepdim=True)


class FiLMLayer3D(nn.Module):
    """Feature-wise linear modulation for 3D feature maps."""

    def __init__(self, text_dim: int, feature_dim: int):
        super().__init__()
        self.feature_dim = feature_dim
        self.film_proj = nn.Sequential(
            nn.Linear(text_dim, feature_dim * 2),
            nn.GELU(),
            nn.Linear(feature_dim * 2, feature_dim * 2),
        )
        nn.init.zeros_(self.film_proj[-1].weight)
        nn.init.zeros_(self.film_proj[-1].bias)
        self.film_proj[-1].bias.data[:feature_dim] = 1.0

    def forward(self, x: torch.Tensor, text_emb: torch.Tensor) -> torch.Tensor:
        gamma, beta = self.film_proj(text_emb).chunk(2, dim=-1)
        gamma = gamma.view(gamma.size(0), -1, 1, 1, 1)
        beta = beta.view(beta.size(0), -1, 1, 1, 1)
        return gamma * x + beta


class TextConditionedUNet3D(nn.Module):
    """3D U-Net with FiLM at the bottleneck and decoder stages."""

    def __init__(
        self,
        clip_feature_dim: int = 768,
        text_dim: int = 768,
        base_channels: int = 64,
        out_channels: int = 3,
    ):
        super().__init__()
        self.clip_branch = nn.Sequential(
            nn.Conv3d(clip_feature_dim, 64, kernel_size=3, padding=1),
            nn.BatchNorm3d(64, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(64, 32, kernel_size=3, padding=1),
            nn.BatchNorm3d(32, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(32, 16, kernel_size=3, padding=1),
            nn.BatchNorm3d(16, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
        )

        self.inc = DoubleConv3d(16, base_channels)
        self.down1 = Down3d(base_channels, base_channels * 2)
        self.down2 = Down3d(base_channels * 2, base_channels * 4)
        self.down3 = Down3d(base_channels * 4, base_channels * 8)
        self.down4 = Down3d(base_channels * 8, base_channels * 16)

        self.film_bottleneck = FiLMLayer3D(text_dim, base_channels * 16)
        self.film1 = FiLMLayer3D(text_dim, base_channels * 8)
        self.film2 = FiLMLayer3D(text_dim, base_channels * 4)
        self.film3 = FiLMLayer3D(text_dim, base_channels * 2)
        self.film4 = FiLMLayer3D(text_dim, base_channels)

        self.up1 = Up3d(base_channels * 16, base_channels * 8, base_channels * 8)
        self.up2 = Up3d(base_channels * 8, base_channels * 4, base_channels * 4)
        self.up3 = Up3d(base_channels * 4, base_channels * 2, base_channels * 2)
        self.up4 = Up3d(base_channels * 2, base_channels, base_channels)

        self.out_conv = nn.Sequential(
            nn.Conv3d(base_channels, base_channels, kernel_size=3, padding=1),
            nn.BatchNorm3d(base_channels, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(base_channels, out_channels, kernel_size=1),
        )

    def forward(
        self,
        clip_features: torch.Tensor,
        text_emb: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        x = clip_features.permute(0, 4, 1, 2, 3)
        x = self.clip_branch(x)

        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        if text_emb is not None:
            x5 = self.film_bottleneck(x5, text_emb)

        x = self.up1(x5, x4)
        if text_emb is not None:
            x = self.film1(x, text_emb)
        x = self.up2(x, x3)
        if text_emb is not None:
            x = self.film2(x, text_emb)
        x = self.up3(x, x2)
        if text_emb is not None:
            x = self.film3(x, text_emb)
        x = self.up4(x, x1)
        if text_emb is not None:
            x = self.film4(x, text_emb)

        return self.out_conv(x)


class PixieStyleUNet3D(nn.Module):
    """Pure-vision Pixie-style baseline with multi-scale fusion."""

    def __init__(
        self,
        clip_feature_dim: int = 768,
        base_channels: int = 64,
        out_channels: int = 3,
    ):
        super().__init__()
        self.clip_branch = nn.Sequential(
            nn.Conv3d(clip_feature_dim, 128, kernel_size=3, padding=1),
            nn.BatchNorm3d(128, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(128, 64, kernel_size=3, padding=1),
            nn.BatchNorm3d(64, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(64, 32, kernel_size=3, padding=1),
            nn.BatchNorm3d(32, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm3d(64, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
        )
        self.inc = DoubleConv3d(64, base_channels)
        self.down1 = Down3d(base_channels, base_channels * 2)
        self.down2 = Down3d(base_channels * 2, base_channels * 4)
        self.down3 = Down3d(base_channels * 4, base_channels * 8)
        self.down4 = Down3d(base_channels * 8, base_channels * 16)
        self.up1 = Up3d(base_channels * 16, base_channels * 8, base_channels * 8)
        self.up2 = Up3d(base_channels * 8, base_channels * 4, base_channels * 4)
        self.up3 = Up3d(base_channels * 4, base_channels * 2, base_channels * 2)
        self.up4 = Up3d(base_channels * 2, base_channels, base_channels)
        self.scale_conv1 = nn.Conv3d(base_channels * 16, base_channels, kernel_size=1)
        self.scale_conv2 = nn.Conv3d(base_channels * 8, base_channels, kernel_size=1)
        self.scale_conv3 = nn.Conv3d(base_channels * 4, base_channels, kernel_size=1)
        self.scale_conv4 = nn.Conv3d(base_channels * 2, base_channels, kernel_size=1)
        self.fusion_conv = DoubleConv3d(base_channels * 5, base_channels * 2)
        self.out_conv = nn.Sequential(
            nn.Conv3d(base_channels * 2, base_channels, kernel_size=3, padding=1),
            nn.BatchNorm3d(base_channels, track_running_stats=False),
            nn.LeakyReLU(0.02, inplace=True),
            nn.Conv3d(base_channels, out_channels, kernel_size=1),
        )

    def forward(self, clip_features: torch.Tensor) -> torch.Tensor:
        x = clip_features.permute(0, 4, 1, 2, 3)
        x = self.clip_branch(x)
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        y = self.up1(x5, x4)
        y = self.up2(y, x3)
        y = self.up3(y, x2)
        y = self.up4(y, x1)
        size = y.shape[2:]
        s1 = F.interpolate(self.scale_conv1(x5), size=size, mode="trilinear", align_corners=True)
        s2 = F.interpolate(self.scale_conv2(x4), size=size, mode="trilinear", align_corners=True)
        s3 = F.interpolate(self.scale_conv3(x3), size=size, mode="trilinear", align_corners=True)
        s4 = F.interpolate(self.scale_conv4(x2), size=size, mode="trilinear", align_corners=True)
        return self.out_conv(self.fusion_conv(torch.cat([s1, s2, s3, s4, y], dim=1)))


class TextConditionedPropertyPredictor(nn.Module):
    """OpenCLIP text encoder plus FiLM-conditioned 3D U-Net."""

    def __init__(
        self,
        clip_feature_dim: int = 768,
        text_dim: int = 768,
        base_channels: int = 64,
        out_channels: int = 3,
        text_encoder_name: str = "ViT-L-14-336-quickgelu",
        text_encoder_pretrained: str = "openai",
        freeze_text_encoder: bool = True,
    ):
        super().__init__()
        self.default_text_emb = nn.Parameter(torch.empty(text_dim).normal_(mean=0.0, std=0.02))
        self.text_encoder = OpenClipTextEncoder(
            model_name=text_encoder_name,
            pretrained=text_encoder_pretrained,
            freeze=freeze_text_encoder,
        )
        self.unet = TextConditionedUNet3D(
            clip_feature_dim=clip_feature_dim,
            text_dim=text_dim,
            base_channels=base_channels,
            out_channels=out_channels,
        )

    def forward(
        self,
        clip_features: torch.Tensor,
        text_descriptions: Optional[List[str]] = None,
        text_embeddings: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        batch_size = clip_features.size(0)
        if text_embeddings is not None:
            text_emb = text_embeddings.to(clip_features.device)
        elif text_descriptions is not None:
            text_emb = self.text_encoder(text_descriptions, device=clip_features.device)
        else:
            text_emb = self.default_text_emb.unsqueeze(0).expand(batch_size, -1)
        return self.unet(clip_features, text_emb)


def create_text_conditioned_predictor(
    clip_feature_dim: int = 768,
    text_dim: int = 768,
    base_channels: int = 64,
    out_channels: int = 3,
    freeze_text_encoder: bool = True,
    device: Optional[str] = None,
) -> TextConditionedPropertyPredictor:
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model = TextConditionedPropertyPredictor(
        clip_feature_dim=clip_feature_dim,
        text_dim=text_dim,
        base_channels=base_channels,
        out_channels=out_channels,
        freeze_text_encoder=freeze_text_encoder,
    )
    return model.to(device)
