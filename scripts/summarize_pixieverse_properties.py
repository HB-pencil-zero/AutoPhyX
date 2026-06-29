#!/usr/bin/env python3
"""Summarize PixieVerse material-property distributions into one CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np


DEFAULT_RENDER_ROOT = "/mnt/fillipo/huangbei/pixieverse/render_outputs"
DEFAULT_JSON_AUG_ROOT = "/mnt/fillipo/huangbei/code/pixieverse_aug_json"
DEFAULT_FULL_GRID_AUG_ROOT = "/mnt/fillipo/huangbei/code/pixieverse_augmented"
DEFAULT_OUTPUT = "docs/pixieverse_property_distribution.csv"

PROPERTIES = {
    "rho": {
        "channel": 0,
        "unit": "kg_m3",
        "scale": "log10",
        "range": (-2.0, 5.0),
        "clip_raw": (1e-2, 1e5),
        "normalization": "target=2*clip(log10(max(rho,1e-8)),-2,5)/15",
    },
    "E": {
        "channel": 1,
        "unit": "Pa",
        "scale": "log10",
        "range": (-2.0, 13.0),
        "clip_raw": (1e-2, 1e13),
        "normalization": "target=2*clip(log10(max(E,1e-8)),-2,13)/15",
    },
    "nu": {
        "channel": 2,
        "unit": "ratio",
        "scale": "linear",
        "range": (0.01, 0.5),
        "clip_raw": (0.01, 0.5),
        "normalization": "target=2*(clip(nu,0.01,0.50)-0.01)/0.49-1",
    },
}

SKIPPED_FILES: list[tuple[str, str]] = []


@dataclass
class PropertyStats:
    """Histogram plus streaming moments for one source/property pair."""

    source: str
    prop: str
    unit: str
    scale: str
    edges: np.ndarray
    root: str
    notes: str
    hist: np.ndarray = field(init=False)
    underflow: int = 0
    overflow: int = 0
    nonpositive: int = 0
    total: int = 0
    samples: int = 0
    objects: set[str] = field(default_factory=set)
    sum_value: float = 0.0
    sumsq_value: float = 0.0
    min_value: float = math.inf
    max_value: float = -math.inf
    norm_sum: float = 0.0
    norm_sumsq: float = 0.0
    norm_min: float = math.inf
    norm_max: float = -math.inf

    def __post_init__(self) -> None:
        self.hist = np.zeros(len(self.edges) - 1, dtype=np.int64)

    def add(self, values: np.ndarray, obj_id: str) -> None:
        values = np.asarray(values)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return

        self.samples += 1
        self.objects.add(obj_id)
        values64 = values.astype(np.float64, copy=False)
        self.total += int(values64.size)
        self.sum_value += float(values64.sum())
        self.sumsq_value += float(np.square(values64).sum())
        self.min_value = min(self.min_value, float(values64.min()))
        self.max_value = max(self.max_value, float(values64.max()))

        if self.scale == "log10":
            positive = values64 > 0
            self.nonpositive += int((~positive).sum())
            log_values = np.log10(values64[positive])
            self.underflow += int((log_values < self.edges[0]).sum())
            self.overflow += int((log_values >= self.edges[-1]).sum())
            self.hist += np.histogram(log_values, bins=self.edges)[0]
            norm = 2.0 * np.clip(np.log10(np.maximum(values64, 1e-8)), self.edges[0], self.edges[-1]) / 15.0
        else:
            self.underflow += int((values64 < self.edges[0]).sum())
            self.overflow += int((values64 >= self.edges[-1]).sum())
            self.hist += np.histogram(values64, bins=self.edges)[0]
            norm = 2.0 * (np.clip(values64, self.edges[0], self.edges[-1]) - self.edges[0]) / (
                self.edges[-1] - self.edges[0]
            ) - 1.0
        self.norm_sum += float(norm.sum())
        self.norm_sumsq += float(np.square(norm).sum())
        self.norm_min = min(self.norm_min, float(norm.min()))
        self.norm_max = max(self.norm_max, float(norm.max()))

    @property
    def mean(self) -> float:
        return self.sum_value / self.total if self.total else math.nan

    @property
    def std(self) -> float:
        if self.total == 0:
            return math.nan
        var = max(self.sumsq_value / self.total - self.mean * self.mean, 0.0)
        return math.sqrt(var)

    @property
    def norm_mean(self) -> float:
        return self.norm_sum / self.total if self.total else math.nan

    @property
    def norm_std(self) -> float:
        if self.total == 0:
            return math.nan
        var = max(self.norm_sumsq / self.total - self.norm_mean * self.norm_mean, 0.0)
        return math.sqrt(var)


def property_edges(prop: str, bins_log: int, bins_nu: int) -> np.ndarray:
    spec = PROPERTIES[prop]
    low, high = spec["range"]
    bins = bins_log if spec["scale"] == "log10" else bins_nu
    return np.linspace(low, high, bins + 1, dtype=np.float64)


def make_stats(source: str, root: Path, notes: str, bins_log: int, bins_nu: int) -> dict[str, PropertyStats]:
    return {
        prop: PropertyStats(
            source=source,
            prop=prop,
            unit=spec["unit"],
            scale=spec["scale"],
            edges=property_edges(prop, bins_log, bins_nu),
            root=str(root),
            notes=notes,
        )
        for prop, spec in PROPERTIES.items()
    }


def occupied_channels(material_grid: np.ndarray) -> dict[str, np.ndarray]:
    mask = material_grid[..., 3] >= 0
    return {prop: material_grid[..., spec["channel"]][mask] for prop, spec in PROPERTIES.items()}


def load_grid(path: Path) -> np.ndarray | None:
    try:
        return np.load(path, mmap_mode="r")
    except (OSError, ValueError) as exc:
        SKIPPED_FILES.append((str(path), str(exc)))
        return None


def add_values(stats: dict[str, PropertyStats], values: dict[str, np.ndarray], obj_id: str, factors: dict[str, float] | None = None) -> None:
    factors = factors or {}
    stats["rho"].add(values["rho"] * float(factors.get("rho", 1.0)), obj_id)
    stats["E"].add(values["E"] * float(factors.get("E", 1.0)), obj_id)
    stats["nu"].add(values["nu"], obj_id)


def add_grid(stats: dict[str, PropertyStats], material_grid: np.ndarray, obj_id: str, factors: dict[str, float] | None = None) -> None:
    add_values(stats, occupied_channels(material_grid), obj_id, factors)


def iter_base_grids(render_root: Path) -> Iterable[tuple[str, Path]]:
    for mat_path in sorted(render_root.glob("*/sample_0/material_grid.npy")):
        yield mat_path.parents[1].name, mat_path


def summarize_base(render_root: Path, stats: dict[str, PropertyStats]) -> None:
    for obj_id, mat_path in iter_base_grids(render_root):
        material_grid = load_grid(mat_path)
        if material_grid is None:
            continue
        add_grid(stats, material_grid, obj_id)


def summarize_json_augments(render_root: Path, aug_root: Path, stats: dict[str, PropertyStats]) -> None:
    for obj_dir in sorted(aug_root.iterdir()):
        if not obj_dir.is_dir():
            continue
        obj_id = obj_dir.name
        mat_path = render_root / obj_id / "sample_0" / "material_grid.npy"
        if not mat_path.exists() or mat_path.stat().st_size == 0:
            continue
        material_grid = load_grid(mat_path)
        if material_grid is None:
            continue
        values = occupied_channels(material_grid)
        for aug_path in sorted(obj_dir.glob("augment_*.json")):
            with open(aug_path, "r", encoding="utf-8") as handle:
                aug = json.load(handle)
            add_values(stats, values, obj_id, aug.get("factors", {}))


def iter_full_grid_augments(aug_root: Path) -> Iterable[tuple[str, Path]]:
    for mat_path in sorted(aug_root.glob("*/augment_*/material_grid_augmented.npy")):
        yield mat_path.parents[1].name, mat_path


def summarize_full_grid_augments(aug_root: Path, stats: dict[str, PropertyStats]) -> None:
    for obj_id, mat_path in iter_full_grid_augments(aug_root):
        material_grid = load_grid(mat_path)
        if material_grid is None:
            continue
        add_grid(stats, material_grid, obj_id)


def write_rows(output_path: Path, all_stats: list[dict[str, PropertyStats]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source",
        "property",
        "unit",
        "scale",
        "bin_index",
        "bin_left",
        "bin_right",
        "bin_label",
        "count",
        "fraction",
        "total_count",
        "num_samples",
        "num_objects",
        "min",
        "max",
        "mean",
        "std",
        "training_normalization",
        "clip_min_raw",
        "clip_max_raw",
        "normalized_min",
        "normalized_max",
        "normalized_mean",
        "normalized_std",
        "root",
        "notes",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for stats_by_prop in all_stats:
            for prop in ("rho", "E", "nu"):
                stats = stats_by_prop[prop]
                spec = PROPERTIES[prop]
                total = stats.total or 1
                common = {
                    "source": stats.source,
                    "property": stats.prop,
                    "unit": stats.unit,
                    "scale": stats.scale,
                    "total_count": stats.total,
                    "num_samples": stats.samples,
                    "num_objects": len(stats.objects),
                    "min": f"{stats.min_value:.9g}" if stats.total else "",
                    "max": f"{stats.max_value:.9g}" if stats.total else "",
                    "mean": f"{stats.mean:.9g}" if stats.total else "",
                    "std": f"{stats.std:.9g}" if stats.total else "",
                    "training_normalization": spec["normalization"],
                    "clip_min_raw": f"{spec['clip_raw'][0]:.9g}",
                    "clip_max_raw": f"{spec['clip_raw'][1]:.9g}",
                    "normalized_min": f"{stats.norm_min:.9g}" if stats.total else "",
                    "normalized_max": f"{stats.norm_max:.9g}" if stats.total else "",
                    "normalized_mean": f"{stats.norm_mean:.9g}" if stats.total else "",
                    "normalized_std": f"{stats.norm_std:.9g}" if stats.total else "",
                    "root": stats.root,
                    "notes": stats.notes,
                }

                special_bins = []
                if stats.scale == "log10":
                    special_bins.append(("nonpositive", "", "0", "<=0", stats.nonpositive))
                special_bins.append(("underflow", "", f"{stats.edges[0]:.9g}", f"<{stats.edges[0]:.3g}", stats.underflow))
                special_bins.append(("overflow", f"{stats.edges[-1]:.9g}", "", f">={stats.edges[-1]:.3g}", stats.overflow))
                for label, left, right, bin_label, count in special_bins:
                    writer.writerow(
                        {
                            **common,
                            "bin_index": label,
                            "bin_left": left,
                            "bin_right": right,
                            "bin_label": bin_label,
                            "count": int(count),
                            "fraction": f"{count / total:.9g}",
                        }
                    )

                for idx, count in enumerate(stats.hist):
                    left = stats.edges[idx]
                    right = stats.edges[idx + 1]
                    if stats.scale == "log10":
                        label = f"10^{left:.3g}..10^{right:.3g}"
                    else:
                        label = f"{left:.3g}..{right:.3g}"
                    writer.writerow(
                        {
                            **common,
                            "bin_index": idx,
                            "bin_left": f"{left:.9g}",
                            "bin_right": f"{right:.9g}",
                            "bin_label": label,
                            "count": int(count),
                            "fraction": f"{count / total:.9g}",
                        }
                    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-root", default=DEFAULT_RENDER_ROOT)
    parser.add_argument("--json-aug-root", default=DEFAULT_JSON_AUG_ROOT)
    parser.add_argument("--full-grid-aug-root", default=DEFAULT_FULL_GRID_AUG_ROOT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--bins-log", type=int, default=48)
    parser.add_argument("--bins-nu", type=int, default=50)
    args = parser.parse_args()

    render_root = Path(args.render_root)
    json_aug_root = Path(args.json_aug_root)
    full_grid_aug_root = Path(args.full_grid_aug_root)
    output_path = Path(args.output)

    all_stats: list[dict[str, PropertyStats]] = []

    base_stats = make_stats(
        "base_material_grid",
        render_root,
        "One base full material_grid.npy per PixieVerse object.",
        args.bins_log,
        args.bins_nu,
    )
    summarize_base(render_root, base_stats)
    all_stats.append(base_stats)

    json_stats = make_stats(
        "json_factor_augmented_full_grid",
        json_aug_root,
        "Base full material_grid.npy with compact JSON E/rho factors applied; includes augment_0 default samples.",
        args.bins_log,
        args.bins_nu,
    )
    summarize_json_augments(render_root, json_aug_root, json_stats)
    all_stats.append(json_stats)

    full_grid_stats = make_stats(
        "saved_full_grid_augmented",
        full_grid_aug_root,
        "Previously saved material_grid_augmented.npy files.",
        args.bins_log,
        args.bins_nu,
    )
    summarize_full_grid_augments(full_grid_aug_root, full_grid_stats)
    all_stats.append(full_grid_stats)

    write_rows(output_path, all_stats)
    print(f"Wrote {output_path}")
    for stats_by_prop in all_stats:
        ref = stats_by_prop["rho"]
        print(
            f"{ref.source}: samples={ref.samples} objects={len(ref.objects)} "
            f"occupied_voxels_per_property={ref.total}"
        )
    if SKIPPED_FILES:
        print(f"skipped_bad_grids={len(SKIPPED_FILES)}")
        for path, reason in SKIPPED_FILES[:10]:
            print(f"  {path}: {reason}")


if __name__ == "__main__":
    main()
