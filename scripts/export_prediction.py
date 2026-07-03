#!/usr/bin/env python3
"""Export one AutoPhyX prediction as normalized and raw physical-property grids."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autophyx.data import PROPERTY_CHANNELS, denormalize_material_tensor
from autophyx.model import TextConditionedPropertyPredictor


def load_model(checkpoint: str, device: torch.device, args: argparse.Namespace) -> TextConditionedPropertyPredictor:
    ckpt = torch.load(checkpoint, map_location=device, weights_only=True)
    config = ckpt.get("model_config", {})
    model = TextConditionedPropertyPredictor(
        clip_feature_dim=args.clip_feature_dim or config.get("clip_feature_dim", 768),
        text_dim=args.text_dim or config.get("text_dim", 768),
        base_channels=args.base_channels or config.get("base_channels", 64),
        freeze_text_encoder=config.get("freeze_text_encoder", True),
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model


@torch.no_grad()
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--features", required=True, help="Path to [D,H,W,C] OpenCLIP voxel .npy")
    parser.add_argument("--output", required=True, help="Output .npz path")
    parser.add_argument("--text", default="", help="Optional text prompt; uses OpenCLIP at runtime")
    parser.add_argument("--text-embedding", default="", help="Optional pre-encoded .pt embedding")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--clip-feature-dim", type=int, default=0)
    parser.add_argument("--text-dim", type=int, default=0)
    parser.add_argument("--base-channels", type=int, default=0)
    args = parser.parse_args()

    if args.text and args.text_embedding:
        raise SystemExit("Use either --text or --text-embedding, not both.")

    device = torch.device(args.device)
    model = load_model(args.checkpoint, device, args)

    features = np.load(args.features).astype(np.float32)
    if features.ndim != 4:
        raise SystemExit(f"Expected [D,H,W,C] features, got {features.shape}")
    feat = torch.from_numpy(features).unsqueeze(0).to(device)

    if args.text_embedding:
        text_emb = torch.load(args.text_embedding, map_location=device, weights_only=True).float().unsqueeze(0)
        pred_norm = torch.clamp(model.unet(feat, text_emb=text_emb), -10.0, 10.0)
    elif args.text:
        pred_norm = torch.clamp(model(feat, text_descriptions=[args.text]), -10.0, 10.0)
    else:
        pred_norm = torch.clamp(model(feat), -10.0, 10.0)

    pred_raw = denormalize_material_tensor(pred_norm).squeeze(0).cpu().numpy()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        pred_normalized=pred_norm.squeeze(0).cpu().numpy(),
        pred_physical=pred_raw,
        physical_channels=np.asarray(PROPERTY_CHANNELS),
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
