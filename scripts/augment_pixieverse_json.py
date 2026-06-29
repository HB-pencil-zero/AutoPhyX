#!/usr/bin/env python3
"""Generate compact JSON physical-property augmentations for PixieVerse."""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

STIFFER = [
    "the {part} is rigid and stiff",
    "the {part} feels firm and resistant",
    "the {part} is hardened, holding its shape",
]
SOFTER = [
    "the {part} is soft and deforms easily",
    "the {part} is pliable and yields under pressure",
    "the {part} bends readily, feeling flexible",
]
DENSER = [
    "the {part} is heavy and dense",
    "the {part} has a solid, weighty feel",
    "the {part} is substantial and sinks",
]
LIGHTER = [
    "the {part} is light and airy",
    "the {part} is buoyant, floating easily",
    "the {part} has little weight, feeling hollow",
]
GRANULAR = {"sand", "mud", "soil", "dirt", "snow", "gravel", "salt", "dust", "powder"}
GR_SOFT = ["the {part} is loose and flows freely", "the {part} is soft and shifting"]
GR_STIFF = ["the {part} is densely packed and resists movement", "the {part} is compact and firm"]


def clean_name(name: str) -> str:
    name = name.split(" and ")[-1].split(" & ")[-1]
    words = name.replace("_", " ").replace("SM ", "").replace("M ", "").split()
    prefixes = ("A0", "B0", "C0", "D0", "E0", "F0", "G0")
    meaningful = [word for word in words if len(word) > 1 and not word.startswith(prefixes)]
    return " ".join(meaningful[-2:]) if meaningful else (words[-1] if words else "object")


def gen_augments(parts: dict, obj_id: str, n: int) -> list[dict]:
    rng = random.Random(hash(obj_id))
    part_names = [clean_name(part) for part in parts if part and part.strip()]
    if not part_names:
        part_names = ["object"]
    label = ", ".join(part_names[:2])
    augments = [{"text": f"A {label}.", "desc": "default", "factors": {}}]

    for _ in range(n - 1):
        direction = rng.choice(["stiffer", "softer", "denser", "lighter"])
        factors = {}
        desc_parts = []
        for part_name in parts:
            cleaned = clean_name(part_name)
            is_granular = any(word in cleaned.lower() for word in GRANULAR)
            if direction == "stiffer":
                factors["E"] = 10 ** rng.uniform(0.5, 2.0)
                desc_parts.append(rng.choice(GR_STIFF if is_granular else STIFFER).format(part=cleaned))
            elif direction == "softer":
                factors["E"] = 10 ** rng.uniform(-2.0, -0.5)
                desc_parts.append(rng.choice(GR_SOFT if is_granular else SOFTER).format(part=cleaned))
            elif direction == "denser":
                factors["rho"] = rng.uniform(1.3, 2.5)
                desc_parts.append(rng.choice(DENSER).format(part=cleaned))
            else:
                factors["rho"] = rng.uniform(0.3, 0.7)
                desc_parts.append(rng.choice(LIGHTER).format(part=cleaned))

        rng.shuffle(desc_parts)
        mentioned = desc_parts[: min(2, len(desc_parts))]
        if len(mentioned) == 1:
            text = f"A {label} where {mentioned[0]}."
        elif len(mentioned) >= 2:
            text = f"A {label} where {mentioned[0]}, while {mentioned[1]}."
        else:
            text = f"A {label}."
        augments.append({"text": text, "desc": direction, "factors": factors})
    return augments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--features-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--num-augmentations", type=int, default=8)
    parser.add_argument("--max-objects", type=int, default=0)
    args = parser.parse_args()

    render_root = Path(args.render_root)
    features_root = Path(args.features_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    total_objects = 0
    total_augments = 0
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
        augments = gen_augments(parts, obj_id, args.num_augmentations)

        obj_out = output_root / obj_id
        obj_out.mkdir(parents=True, exist_ok=True)
        for idx, aug in enumerate(augments):
            with open(obj_out / f"augment_{idx}.json", "w", encoding="utf-8") as handle:
                json.dump(aug, handle, indent=2)

        total_objects += 1
        total_augments += len(augments)
        if total_objects % 100 == 0:
            logger.info("%d objects, %d augmentations", total_objects, total_augments)
        if args.max_objects and total_objects >= args.max_objects:
            break

    logger.info("Done: %d objects, %d augmentations -> %s", total_objects, total_augments, output_root)


if __name__ == "__main__":
    main()
