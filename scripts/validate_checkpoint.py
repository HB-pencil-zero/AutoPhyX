#!/usr/bin/env python3
"""Validate a saved AutoPhyX checkpoint on held-out objects."""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autophyx.data import PixieVerseJsonDataset, masked_mse
from autophyx.model import TextConditionedPropertyPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def split_by_object(dataset: PixieVerseJsonDataset, train_fraction: float, seed: int) -> tuple[Subset, Subset]:
    obj_ids = list(dataset.object_ids())
    rng = random.Random(seed)
    rng.shuffle(obj_ids)
    n_train = int(len(obj_ids) * train_fraction)
    train_objs = set(obj_ids[:n_train])
    train_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] in train_objs]
    val_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] not in train_objs]
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
    args = parser.parse_args()

    device = torch.device(args.device)
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=True)
    model = TextConditionedPropertyPredictor(clip_feature_dim=768, freeze_text_encoder=True).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    logger.info("Loaded checkpoint epoch=%s val=%s", ckpt.get("epoch"), ckpt.get("val_loss"))

    dataset = PixieVerseJsonDataset(args.features_root, args.render_root, args.aug_root, args.emb_root)
    _, val_ds = split_by_object(dataset, args.train_fraction, args.seed)
    loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    total = 0.0
    count = 0
    nan = 0
    for batch in loader:
        feat = batch["features"].to(device)
        target = batch["target"].to(device)
        mask = batch["mask"].to(device)
        emb = batch["text_emb"].to(device)
        pred = torch.clamp(model.unet(feat, text_emb=emb), -10.0, 10.0)
        loss = masked_mse(pred, target, mask)
        if torch.isfinite(loss):
            total += loss.item() * feat.size(0)
            count += feat.size(0)
        else:
            nan += feat.size(0)

    print(f"FINAL: val_loss={total / max(count, 1):.4f} ({count} samples, {nan} NaN)")


if __name__ == "__main__":
    main()
