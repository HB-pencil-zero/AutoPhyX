#!/usr/bin/env python3
"""Generate full augmented material grids with text descriptions."""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

MATERIAL_RANGES = {
    "rubber": ((0.7e6, 2.3e9), (0.45, 0.50), (910, 1200)),
    "plastic": ((0.4e9, 5.0e9), (0.30, 0.46), (900, 2250)),
    "metal": ((68e9, 215e9), (0.27, 0.36), (2700, 8940)),
    "wood": ((6e9, 20e9), (0.20, 0.30), (500, 800)),
    "glass": ((48e9, 90e9), (0.17, 0.30), (2300, 2700)),
    "ceramic": ((50e9, 400e9), (0.17, 0.25), (2300, 6000)),
    "concrete": ((20e9, 50e9), (0.10, 0.20), (2200, 2500)),
    "leather": ((0.01e9, 0.2e9), (0.35, 0.45), (600, 1000)),
    "fabric": ((0.001e9, 0.04e9), (0.20, 0.40), (200, 1500)),
    "paper": ((0.5e9, 5.0e9), (0.20, 0.40), (500, 800)),
    "stone": ((30e9, 100e9), (0.15, 0.30), (2000, 3000)),
    "organic": ((0.001e9, 1e9), (0.30, 0.45), (500, 1200)),
}
DEFAULT_RANGE = ((0.1e9, 100e9), (0.20, 0.45), (500, 5000))

STIFFER_TEXTS = [
    "the {part} is quite rigid and stiff",
    "the {part} feels firm and resistant to bending",
    "the {part} is hardened, holding its shape well",
]
SOFTER_TEXTS = [
    "the {part} is soft and deforms easily",
    "the {part} is pliable and yields under light pressure",
    "the {part} bends readily, feeling flexible to the touch",
]
DENSER_TEXTS = [
    "the {part} is heavy and dense",
    "the {part} has a solid, weighty feel",
    "the {part} is substantial and sinks rather than floats",
]
LIGHTER_TEXTS = [
    "the {part} is light and airy",
    "the {part} is buoyant, floating easily",
    "the {part} has little weight, feeling hollow",
]
GRANULAR = {"sand", "mud", "soil", "dirt", "snow", "gravel", "salt", "dust", "powder"}


def clean_name(name: str) -> str:
    name = name.split(" and ")[-1].split(" & ")[-1]
    words = name.replace("_", " ").replace("SM ", "").replace("M ", "").split()
    prefixes = ("A0", "B0", "C0", "D0", "E0", "F0", "G0")
    meaningful = [word for word in words if len(word) > 1 and not word.startswith(prefixes)]
    return " ".join(meaningful[-2:]) if meaningful else (words[-1] if words else "object")


def guess_material_type(part_name: str, base_e: float) -> str:
    name = part_name.lower()
    keywords = {
        "rubber": ["rubber", "elastic", "elastomer", "tire", "gasket", "seal"],
        "metal": ["metal", "steel", "iron", "aluminum", "copper", "brass", "chrome", "bolt", "screw"],
        "wood": ["wood", "oak", "pine", "maple", "birch", "bamboo", "board", "plank"],
        "glass": ["glass", "mirror", "window", "lens", "crystal"],
        "fabric": ["fabric", "cloth", "textile", "cushion", "pillow", "canvas", "curtain", "rug"],
        "leather": ["leather", "suede", "hide"],
        "concrete": ["concrete", "cement", "mortar"],
        "ceramic": ["ceramic", "porcelain", "clay", "pottery", "tile", "vase"],
        "paper": ["paper", "cardboard", "carton", "label", "book"],
        "stone": ["stone", "rock", "granite", "marble", "slate"],
        "organic": ["leaf", "flower", "fruit", "bark", "branch", "grass", "plant", "tree"],
        "plastic": ["plastic", "pvc", "nylon", "acrylic", "bucket", "container", "bottle", "toy"],
    }
    for material, words in keywords.items():
        if any(word in name for word in words):
            return material
    if base_e > 50e9:
        return "metal"
    if base_e > 5e9:
        return "wood"
    if base_e > 0.5e9:
        return "plastic"
    if base_e > 1e6:
        return "rubber"
    return "organic"


def get_range(part_name: str, base_e: float) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    return MATERIAL_RANGES.get(guess_material_type(part_name, base_e), DEFAULT_RANGE)


def gen_augmented_samples(material_grid: np.ndarray, parts: dict, obj_id: str, n: int) -> list[dict]:
    base_grid = material_grid.copy()
    material_id = material_grid[..., 3]
    part_names = [clean_name(part) for part in parts if part and part.strip()]
    if not part_names:
        part_names = ["object"]
    parts_label = ", ".join(part_names[:2])
    results = [
        {
            "material_grid": base_grid,
            "text": f"A {parts_label}.",
            "summary": "default",
            "obj_id": obj_id,
            "augment_id": 0,
        }
    ]

    rng = random.Random(hash(obj_id))
    part_items = list(parts.items()) or [("object", {})]
    for augment_id in range(1, n):
        aug_grid = base_grid.copy()
        desc_parts = []
        direction = rng.choice(["stiffer", "softer", "denser", "lighter"])
        for part_name, _ in part_items:
            cleaned = clean_name(part_name)
            mask = material_id >= 0
            if direction == "stiffer":
                factor = 10 ** rng.uniform(0.5, 2.0)
                aug_grid[..., 1][mask] *= factor
                desc_parts.append(
                    f"the {cleaned} is densely packed and resists movement"
                    if any(word in cleaned.lower() for word in GRANULAR)
                    else rng.choice(STIFFER_TEXTS).format(part=cleaned)
                )
            elif direction == "softer":
                factor = 10 ** rng.uniform(-2.0, -0.5)
                aug_grid[..., 1][mask] *= factor
                desc_parts.append(
                    f"the {cleaned} is loose and flows freely"
                    if any(word in cleaned.lower() for word in GRANULAR)
                    else rng.choice(SOFTER_TEXTS).format(part=cleaned)
                )
            elif direction == "denser":
                aug_grid[..., 0][mask] *= rng.uniform(1.3, 2.5)
                desc_parts.append(rng.choice(DENSER_TEXTS).format(part=cleaned))
            else:
                aug_grid[..., 0][mask] *= rng.uniform(0.3, 0.7)
                desc_parts.append(rng.choice(LIGHTER_TEXTS).format(part=cleaned))

        rng.shuffle(desc_parts)
        mentioned = desc_parts[: min(2, len(desc_parts))]
        if len(mentioned) == 1:
            text = f"A {parts_label} where {mentioned[0]}."
        elif len(mentioned) == 2:
            text = f"A {parts_label} where {mentioned[0]}, while {mentioned[1]}."
        else:
            text = f"A {parts_label}."
        results.append(
            {
                "material_grid": aug_grid,
                "text": text,
                "summary": text[:100],
                "obj_id": obj_id,
                "augment_id": augment_id,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--features-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--num-augmentations", type=int, default=6)
    parser.add_argument("--max-objects", type=int, default=0)
    args = parser.parse_args()

    render_root = Path(args.render_root)
    features_root = Path(args.features_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    total_augments = 0
    processed = 0
    for obj_dir in sorted(render_root.iterdir()):
        if not obj_dir.is_dir():
            continue
        obj_id = obj_dir.name
        feat_path = features_root / obj_id / "clip_features_features.npy"
        mat_path = obj_dir / "sample_0" / "material_grid.npy"
        mat_dict_path = obj_dir / "sample_0" / "material_dict.json"
        if not feat_path.exists() or not mat_path.exists():
            continue

        parts = {}
        if mat_dict_path.exists():
            with open(mat_dict_path, "r", encoding="utf-8") as handle:
                parts = json.load(handle).get("material_dict", {})

        try:
            material_grid = np.load(mat_path)
            if material_grid.size == 0:
                continue
        except (ValueError, OSError):
            continue

        out_sample_dir = output_root / obj_id / "sample_0"
        out_sample_dir.mkdir(parents=True, exist_ok=True)
        for result in gen_augmented_samples(material_grid, parts, obj_id, args.num_augmentations):
            aug_dir = out_sample_dir / f"augment_{result['augment_id']}"
            aug_dir.mkdir(parents=True, exist_ok=True)
            np.save(aug_dir / "material_grid_augmented.npy", result["material_grid"].astype(np.float32))
            info = {key: value for key, value in result.items() if key != "material_grid"}
            with open(aug_dir / "augmentation_info.json", "w", encoding="utf-8") as handle:
                json.dump(info, handle, indent=2)
            total_augments += 1

        processed += 1
        if processed % 50 == 0:
            logger.info("%d objects, %d augmentations", processed, total_augments)
        if args.max_objects and processed >= args.max_objects:
            break

    logger.info("Done: %d objects, %d augmentations -> %s", processed, total_augments, output_root)


if __name__ == "__main__":
    main()
