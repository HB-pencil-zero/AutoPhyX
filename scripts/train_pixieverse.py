#!/usr/bin/env python3
"""Train AutoPhyX on PixieVerse JSON augmentations."""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autophyx.data import PixieVerseJsonDataset, masked_mse
from autophyx.model import TextConditionedPropertyPredictor

logger = logging.getLogger(__name__)


@torch.no_grad()
def evaluate(model: TextConditionedPropertyPredictor, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total = 0.0
    count = 0
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
    model.train()
    return total / max(count, 1)


def split_by_object(dataset: PixieVerseJsonDataset, train_fraction: float, seed: int) -> tuple[Subset, Subset]:
    obj_ids = list(dataset.object_ids())
    rng = random.Random(seed)
    rng.shuffle(obj_ids)
    n_train = int(len(obj_ids) * train_fraction)
    train_objs = set(obj_ids[:n_train])
    train_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] in train_objs]
    val_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] not in train_objs]
    return Subset(dataset, train_idx), Subset(dataset, val_idx)


def train(args: argparse.Namespace) -> None:
    device = torch.device(args.device)
    dataset = PixieVerseJsonDataset(
        args.features_root,
        args.render_root,
        args.aug_root,
        args.emb_root,
        max_objects=args.max_objects if args.max_objects > 0 else None,
    )
    train_ds, val_ds = split_by_object(dataset, args.train_fraction, args.seed)
    logger.info("Train samples: %d  Val samples: %d", len(train_ds), len(val_ds))

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=args.device.startswith("cuda"),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=args.device.startswith("cuda"),
    )

    model = TextConditionedPropertyPredictor(
        clip_feature_dim=args.clip_feature_dim,
        freeze_text_encoder=True,
    ).to(device)
    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=True)
        model.load_state_dict(ckpt["model"])
        logger.info("Resumed from %s (epoch=%s val=%s)", args.resume, ckpt.get("epoch"), ckpt.get("val_loss"))

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=args.epochs,
        eta_min=args.lr * 0.01,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ckpt_dir = Path(args.output_dir) / f"pixieverse_{timestamp}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Checkpoints: %s", ckpt_dir)
    logger.info("Params: %s", f"{sum(p.numel() for p in model.parameters()):,}")

    best_val = float("inf")
    nan_skips = 0
    for epoch in range(args.epochs):
        model.train()
        epoch_loss = 0.0
        finite_steps = 0
        progress = tqdm(train_loader, desc=f"E{epoch + 1}/{args.epochs}")
        for batch in progress:
            feat = batch["features"].to(device)
            target = batch["target"].to(device)
            mask = batch["mask"].to(device)
            emb = batch["text_emb"].to(device)

            pred = torch.clamp(model.unet(feat, text_emb=emb), -10.0, 10.0)
            loss = masked_mse(pred, target, mask)
            if not torch.isfinite(loss):
                nan_skips += 1
                continue

            optimizer.zero_grad()
            loss.backward()
            if args.grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            optimizer.step()
            epoch_loss += loss.item()
            finite_steps += 1
            progress.set_postfix(loss=f"{loss.item():.4f}")

        scheduler.step()
        val = evaluate(model, val_loader, device)
        train_loss = epoch_loss / max(finite_steps, 1)
        logger.info("E %d | train=%.4f val=%.4f (nan=%d)", epoch + 1, train_loss, val, nan_skips)
        sys.stderr.flush()

        ckpt = {"epoch": epoch + 1, "model": model.state_dict(), "val_loss": val}
        torch.save(ckpt, ckpt_dir / "latest.pth")
        if val < best_val:
            best_val = val
            torch.save(ckpt, ckpt_dir / "best.pth")
            logger.info("  best=%.4f", best_val)
            sys.stderr.flush()

    logger.info("Done, best=%.4f", best_val)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-root", required=True)
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--aug-root", required=True)
    parser.add_argument("--emb-root", required=True)
    parser.add_argument("--output-dir", default="checkpoints_pixieverse")
    parser.add_argument("--resume", default="")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--clip-feature-dim", type=int, default=768)
    parser.add_argument("--train-fraction", type=float, default=0.85)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-objects", type=int, default=0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    train(args)


if __name__ == "__main__":
    main()
