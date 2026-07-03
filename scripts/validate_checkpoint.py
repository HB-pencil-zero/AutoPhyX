#!/usr/bin/env python3
"""Validate a saved AutoPhyX checkpoint on held-out objects."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autophyx.data import PixieVerseJsonDataset, masked_channel_mse, masked_mse, split_indices_by_object
from autophyx.model import TextConditionedPropertyPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def split_by_object(dataset: PixieVerseJsonDataset, train_fraction: float, seed: int) -> tuple[Subset, Subset]:
    train_idx, val_idx = split_indices_by_object(dataset, train_fraction, seed)
    return Subset(dataset, train_idx), Subset(dataset, val_idx)


@torch.no_grad()
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--features-root", required=True)
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--aug-root", required=True)
    parser.add_argument("--emb-root", required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--train-fraction", type=float, default=0.85)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clip-feature-dim", type=int, default=0)
    parser.add_argument("--text-dim", type=int, default=0)
    parser.add_argument("--base-channels", type=int, default=0)
    args = parser.parse_args()

    device = torch.device(args.device)
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=True)
    config = ckpt.get("model_config", {})
    model = TextConditionedPropertyPredictor(
        clip_feature_dim=args.clip_feature_dim or config.get("clip_feature_dim", 768),
        text_dim=args.text_dim or config.get("text_dim", 768),
        base_channels=args.base_channels or config.get("base_channels", 64),
        freeze_text_encoder=config.get("freeze_text_encoder", True),
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    logger.info(
        "Loaded checkpoint epoch=%s val=%s config=%s",
        ckpt.get("epoch"),
        ckpt.get("val_loss"),
        config or "legacy-defaults",
    )

    dataset = PixieVerseJsonDataset(args.features_root, args.render_root, args.aug_root, args.emb_root)
    _, val_ds = split_by_object(dataset, args.train_fraction, args.seed)
    loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    total = 0.0
    count = 0
    nan = 0
    channel_totals = {"rho": 0.0, "E": 0.0, "nu": 0.0}
    for batch in loader:
        feat = batch["features"].to(device)
        target = batch["target"].to(device)
        mask = batch["mask"].to(device)
        emb = batch["text_emb"].to(device)
        pred = torch.clamp(model.unet(feat, text_emb=emb), -10.0, 10.0)
        loss = masked_mse(pred, target, mask)
        if torch.isfinite(loss):
            total += loss.item() * feat.size(0)
            channel_loss = masked_channel_mse(pred, target, mask)
            for key in channel_totals:
                channel_totals[key] += channel_loss[key].item() * feat.size(0)
            count += feat.size(0)
        else:
            nan += feat.size(0)

    denom = max(count, 1)
    print(
        "FINAL: "
        f"val_loss={total / denom:.4f} "
        f"rho={channel_totals['rho'] / denom:.4f} "
        f"E={channel_totals['E'] / denom:.4f} "
        f"nu={channel_totals['nu'] / denom:.4f} "
        f"({count} samples, {nan} NaN)"
    )


if __name__ == "__main__":
    main()
