#!/usr/bin/env python3
"""Pre-encode PixieVerse augmentation texts through OpenCLIP."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autophyx.model import OpenClipTextEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-root", required=True)
    parser.add_argument("--aug-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--model-name", default="ViT-L-14-336-quickgelu")
    parser.add_argument("--pretrained", default="openai")
    args = parser.parse_args()

    features_root = Path(args.features_root)
    aug_root = Path(args.aug_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)
    encoder = OpenClipTextEncoder(model_name=args.model_name, pretrained=args.pretrained, freeze=True)
    total = 0

    for obj_dir in sorted(aug_root.iterdir()):
        if not obj_dir.is_dir():
            continue
        obj_id = obj_dir.name
        feat_path = features_root / obj_id / "clip_features_features.npy"
        if not feat_path.exists():
            continue

        texts = []
        names = []
        for aug_path in sorted(obj_dir.glob("augment_*.json")):
            with open(aug_path, "r", encoding="utf-8") as handle:
                aug = json.load(handle)
            texts.append(aug["text"])
            names.append(aug_path.stem)
        if not texts:
            continue

        with torch.no_grad():
            embeddings = encoder(texts, device=device)

        obj_out = output_root / obj_id
        obj_out.mkdir(parents=True, exist_ok=True)
        for name, embedding in zip(names, embeddings.cpu()):
            torch.save(embedding, obj_out / f"{name}.pt")

        total += len(texts)
        if total % 500 == 0:
            logger.info("%d texts encoded", total)

    logger.info("Done: %d texts -> %s", total, output_root)


if __name__ == "__main__":
    main()
