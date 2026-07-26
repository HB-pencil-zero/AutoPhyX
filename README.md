# AutoPhyX

AutoPhyX-style text-conditioned physics property prediction.

[Project Page](https://hb-pencil-zero.github.io/AutoPhyX/) |
[Paper](static/paper/autophyx.pdf) |
[Text2Physics Data](https://huggingface.co/datasets/hbpencil01/pixieverse)

This repository contains the training and data augmentation scripts used for
Text2Physics experiments where 3D visual voxel features are conditioned
on natural-language physical descriptions. The model predicts dense voxel-level
physical properties:

- density
- Young's modulus `E`
- Poisson ratio `nu`

The core model is a 3D U-Net with FiLM conditioning from OpenCLIP text
embeddings.

The implementation follows the main paper design:

- OpenCLIP voxel features are the 3D visual input.
- Frozen OpenCLIP text embeddings condition the predictor.
- FiLM layers modulate U-Net features at multiple scales.
- The physics loss is masked to occupied voxels.
- `rho` and `E` are learned in log space, while `nu` is learned linearly.

## Contents

- `autophyx/model.py` - OpenCLIP text encoder, FiLM layers, Pixie-style U-Net,
  and text-conditioned AutoPhyX U-Net.
- `autophyx/data.py` - PixieVerse JSON augmentation datasets, material-grid
  datasets, target normalization, and masked MSE.
- `scripts/augment_pixieverse_json.py` - Generates compact JSON augmentation
  descriptions and scale factors.
- `scripts/augment_pixieverse_grids.py` - Generates full augmented material
  grids with text descriptions.
- `scripts/preencode_texts.py` - Pre-encodes JSON augmentation text to `.pt`
  embeddings with OpenCLIP.
- `scripts/train_pixieverse.py` - Trains AutoPhyX on PixieVerse features and
  JSON augmentations.
- `scripts/validate_checkpoint.py` - Evaluates a saved checkpoint on held-out
  objects.
- `scripts/export_prediction.py` - Exports one checkpoint prediction to both
  normalized targets and raw `rho/E/nu` physical units.
- `scripts/summarize_pixieverse_properties.py` - Summarizes base and augmented
  material-property distributions into CSV.
- `docs/pixieverse_v7_log_excerpt.md` - Preserved training-log excerpt from the
  run that reached validation loss near `0.01`.
- `docs/pixieverse_property_distribution.csv` - Current PixieVerse `rho`, `E`,
  and `nu` distribution summary, including JSON-factor and saved full-grid
  augmentations.

## Expected Data Layout

The PixieVerse training scripts expect these roots to be passed explicitly:

```text
features_root/
  <obj_id>/clip_features_features.npy

render_root/
  <obj_id>/sample_0/material_grid.npy
  <obj_id>/sample_0/material_dict.json

aug_root/
  <obj_id>/augment_0.json
  <obj_id>/augment_1.json
  ...

emb_root/
  <obj_id>/augment_0.pt
  <obj_id>/augment_1.pt
  ...
```

`material_grid.npy` is expected to be `[64, 64, 64, 4]` with channels:

```text
[density, E, nu, material_id]
```

Voxel features are expected to be `[64, 64, 64, 768]`.

Model targets and exported physical predictions use this channel order:

```text
[rho, E, nu]
```

## Property Distribution CSV

`docs/pixieverse_property_distribution.csv` reports raw physical-property
statistics only. The `rho` and `E` histograms use log-spaced bins, but
`bin_left`, `bin_right`, `min`, `max`, `mean`, and `std` are all raw physical
values in the units shown by the `unit` column.

## Target Normalization

Training normalizes raw properties before loss computation, but those
normalized target values are intentionally not included in the distribution CSV.

Training uses these transforms:

```text
rho_target = 2 * clip(log10(max(rho, 1e-8)), -2, 5) / 15
E_target   = 2 * clip(log10(max(E,   1e-8)), -2, 13) / 15
nu_target  = 2 * (clip(nu, 0.01, 0.50) - 0.01) / 0.49 - 1
```

`nu` is not log-transformed. Negative `nu_target` values are expected because
the raw `nu` interval `[0.01, 0.50]` is linearly mapped to `[-1, 1]`.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate JSON augmentations:

```bash
python scripts/augment_pixieverse_json.py \
  --render-root /path/to/render_outputs \
  --features-root /path/to/features \
  --output-root /path/to/pixieverse_aug_json \
  --num-augmentations 8
```

Pre-encode text descriptions:

```bash
python scripts/preencode_texts.py \
  --features-root /path/to/features \
  --aug-root /path/to/pixieverse_aug_json \
  --output-root /path/to/pixieverse_text_emb
```

Train:

```bash
python scripts/train_pixieverse.py \
  --features-root /path/to/features \
  --render-root /path/to/render_outputs \
  --aug-root /path/to/pixieverse_aug_json \
  --emb-root /path/to/pixieverse_text_emb \
  --output-dir ./checkpoints_pixieverse \
  --epochs 10 \
  --batch-size 2
```

Validate a checkpoint:

```bash
python scripts/validate_checkpoint.py \
  --checkpoint ./checkpoints_pixieverse/run/best.pth \
  --features-root /path/to/features \
  --render-root /path/to/render_outputs \
  --aug-root /path/to/pixieverse_aug_json \
  --emb-root /path/to/pixieverse_text_emb
```

Export a single prediction:

```bash
python scripts/export_prediction.py \
  --checkpoint ./checkpoints_pixieverse/run/best.pth \
  --features /path/to/features/<obj_id>/clip_features_features.npy \
  --text-embedding /path/to/pixieverse_text_emb/<obj_id>/augment_0.pt \
  --output ./prediction_<obj_id>.npz
```

The `.npz` contains:

```text
pred_normalized  # [3, D, H, W], training target space
pred_physical    # [D, H, W, 3], raw [rho, E, nu]
physical_channels
```

New checkpoints include `model_config` and `val_metrics`, so validation and
export scripts can recover model dimensions without guessing. Older checkpoints
still load with the default `clip_feature_dim=768`, `text_dim=768`, and
`base_channels=64`.

## Notes

Large data artifacts are intentionally excluded from git. Do not commit
`*.npy`, `*.pt`, checkpoints, logs, or rendered assets.
