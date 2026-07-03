"""Datasets and losses for AutoPhyX training."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)
SPATIAL = (2, 3, 4)
PROPERTY_CHANNELS = ("rho", "E", "nu")

LOG_RHO_RANGE = (-2.0, 5.0)
LOG_E_RANGE = (-2.0, 13.0)
NU_RANGE = (0.01, 0.50)
LOG_RHO_SCALE = 15.0
LOG_E_SCALE = 15.0


def normalize_material_grid(material_grid: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize a material grid to target channels and occupancy mask.

    Input channel order is `[density, E, nu, material_id]`.
    Output target shape is `[3, D, H, W]`, approximately normalized to a stable
    training range. The mask is 1 where `material_id >= 0`.
    """
    density = material_grid[..., 0]
    youngs_modulus = material_grid[..., 1]
    poisson = material_grid[..., 2]
    mask = (material_grid[..., 3] >= 0).astype(np.float32)

    eps = 1e-8
    density_log = np.clip(np.log10(np.maximum(density, eps)), *LOG_RHO_RANGE)
    youngs_log = np.clip(np.log10(np.maximum(youngs_modulus, eps)), *LOG_E_RANGE)
    poisson = np.clip(poisson, *NU_RANGE)

    target = np.stack(
        [
            2.0 * density_log / LOG_RHO_SCALE,
            2.0 * youngs_log / LOG_E_SCALE,
            2.0 * (poisson - NU_RANGE[0]) / (NU_RANGE[1] - NU_RANGE[0]) - 1.0,
        ],
        axis=0,
    ).astype(np.float32)
    return target, mask


def denormalize_material_grid(target_grid: np.ndarray) -> np.ndarray:
    """Convert normalized `[3, D, H, W]` targets back to raw `[D, H, W, 3]`.

    Output channel order is `[density, E, nu]`, matching `PROPERTY_CHANNELS`.
    """
    target = np.asarray(target_grid, dtype=np.float32)
    if target.ndim != 4 or target.shape[0] != 3:
        raise ValueError(f"expected [3, D, H, W] target grid, got {target.shape}")

    density_log = target[0] * LOG_RHO_SCALE / 2.0
    youngs_log = target[1] * LOG_E_SCALE / 2.0
    poisson = (target[2] + 1.0) * (NU_RANGE[1] - NU_RANGE[0]) / 2.0 + NU_RANGE[0]
    return np.stack([10.0**density_log, 10.0**youngs_log, poisson], axis=-1).astype(np.float32)


def denormalize_material_tensor(target: torch.Tensor) -> torch.Tensor:
    """Torch equivalent of `denormalize_material_grid`.

    Accepts `[3, D, H, W]` or `[B, 3, D, H, W]` and returns the same spatial
    shape with channels moved to the last dimension.
    """
    if target.dim() == 4:
        density_log = target[0] * LOG_RHO_SCALE / 2.0
        youngs_log = target[1] * LOG_E_SCALE / 2.0
        poisson = (target[2] + 1.0) * (NU_RANGE[1] - NU_RANGE[0]) / 2.0 + NU_RANGE[0]
        return torch.stack([10.0**density_log, 10.0**youngs_log, poisson], dim=-1)
    if target.dim() == 5:
        density_log = target[:, 0] * LOG_RHO_SCALE / 2.0
        youngs_log = target[:, 1] * LOG_E_SCALE / 2.0
        poisson = (target[:, 2] + 1.0) * (NU_RANGE[1] - NU_RANGE[0]) / 2.0 + NU_RANGE[0]
        return torch.stack([10.0**density_log, 10.0**youngs_log, poisson], dim=-1)
    raise ValueError(f"expected [3, D, H, W] or [B, 3, D, H, W], got {tuple(target.shape)}")


def apply_json_factors(material_grid: np.ndarray, factors: Dict[str, float]) -> np.ndarray:
    """Apply compact JSON augmentation factors to a base material grid."""
    out = material_grid.copy()
    if "E" in factors:
        out[..., 1] *= float(factors["E"])
    if "rho" in factors:
        out[..., 0] *= float(factors["rho"])
    return out


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """MSE averaged over occupied voxels."""
    if mask.dim() == 4:
        mask = mask.unsqueeze(1)
    return ((pred - target) ** 2 * mask).sum(dim=SPATIAL).mean() / (
        mask.sum(dim=SPATIAL).mean() + 1e-8
    )


def masked_channel_mse(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    channel_names: Tuple[str, ...] = PROPERTY_CHANNELS,
) -> Dict[str, torch.Tensor]:
    """Per-property MSE over occupied voxels in normalized/log target space."""
    if mask.dim() == 4:
        mask = mask.unsqueeze(1)
    per_channel = ((pred - target) ** 2 * mask).sum(dim=SPATIAL) / (
        mask.sum(dim=SPATIAL) + 1e-8
    )
    return {name: per_channel[:, idx].mean() for idx, name in enumerate(channel_names)}


def split_indices_by_object(
    dataset: "PixieVerseJsonDataset",
    train_fraction: float,
    seed: int,
) -> Tuple[list[int], list[int]]:
    """Create deterministic train/val indices with no object ID overlap."""
    obj_ids = list(dataset.object_ids())
    rng = random.Random(seed)
    rng.shuffle(obj_ids)
    n_train = int(len(obj_ids) * train_fraction)
    train_objs = set(obj_ids[:n_train])
    train_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] in train_objs]
    val_idx = [idx for idx, sample in enumerate(dataset.samples) if sample[0] not in train_objs]
    return train_idx, val_idx


class PixieVerseJsonDataset(Dataset):
    """PixieVerse features + base material grids + JSON factor augmentations."""

    def __init__(
        self,
        features_root: str | Path,
        render_root: str | Path,
        aug_root: str | Path,
        emb_root: str | Path,
        max_objects: Optional[int] = None,
    ):
        self.features_root = Path(features_root)
        self.render_root = Path(render_root)
        self.aug_root = Path(aug_root)
        self.emb_root = Path(emb_root)
        self.samples = []

        object_count = 0
        for obj_dir in sorted(self.aug_root.iterdir()):
            if not obj_dir.is_dir():
                continue
            obj_id = obj_dir.name
            feat_path = self.features_root / obj_id / "clip_features_features.npy"
            mat_path = self.render_root / obj_id / "sample_0" / "material_grid.npy"
            if not feat_path.exists() or not mat_path.exists() or mat_path.stat().st_size == 0:
                continue

            added = 0
            for aug_path in sorted(obj_dir.glob("augment_*.json")):
                emb_path = self.emb_root / obj_id / f"{aug_path.stem}.pt"
                if emb_path.exists():
                    self.samples.append((obj_id, feat_path, mat_path, aug_path, emb_path))
                    added += 1
            if added:
                object_count += 1
                if max_objects and object_count >= max_objects:
                    break

        logger.info("PixieVerseJsonDataset: %d samples from %d objects", len(self.samples), object_count)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        obj_id, feat_path, mat_path, aug_path, emb_path = self.samples[index]
        features = np.load(feat_path).astype(np.float32)
        material = np.load(mat_path).astype(np.float32)
        with open(aug_path, "r", encoding="utf-8") as handle:
            aug = json.load(handle)
        target, mask = normalize_material_grid(apply_json_factors(material, aug.get("factors", {})))
        text_emb = torch.load(emb_path, map_location="cpu").float()
        return {
            "features": torch.from_numpy(features),
            "target": torch.from_numpy(target),
            "mask": torch.from_numpy(mask),
            "text_emb": text_emb,
            "obj_id": obj_id,
        }

    def object_ids(self) -> Iterable[str]:
        return sorted(set(sample[0] for sample in self.samples))


class AugmentedGridDataset(Dataset):
    """Dataset for full augmented material-grid directories."""

    def __init__(self, render_root: str | Path, aug_root: str | Path):
        self.render_root = Path(render_root)
        self.aug_root = Path(aug_root)
        self.samples = []

        for obj_dir in sorted(self.aug_root.iterdir()):
            if not obj_dir.is_dir():
                continue
            obj_id = obj_dir.name
            clip_path = self.render_root / obj_id / "clip_features_features.npy"
            mask_path = self.render_root / obj_id / "clip_features_mask.npy"
            sample_dir = obj_dir / "sample_0"
            if not clip_path.exists() or not sample_dir.is_dir():
                continue
            for aug_dir in sorted(sample_dir.glob("augment_*")):
                mat_path = aug_dir / "material_grid_augmented.npy"
                info_path = aug_dir / "augmentation_info.json"
                if mat_path.exists():
                    self.samples.append((obj_id, clip_path, mask_path, mat_path, info_path))

        logger.info("AugmentedGridDataset: %d samples", len(self.samples))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor | str]:
        obj_id, clip_path, mask_path, mat_path, info_path = self.samples[index]
        features = np.load(clip_path).astype(np.float32)
        material = np.load(mat_path).astype(np.float32)
        target, mask = normalize_material_grid(material)
        if mask_path.exists():
            mask = np.load(mask_path).astype(np.float32)
        text = f"{obj_id}:{mat_path.parent.name}"
        if info_path.exists():
            with open(info_path, "r", encoding="utf-8") as handle:
                info = json.load(handle)
            text = info.get("summary") or info.get("description") or text
        return {
            "features": torch.from_numpy(features),
            "target": torch.from_numpy(target),
            "mask": torch.from_numpy(mask),
            "text": text,
            "obj_id": obj_id,
        }
