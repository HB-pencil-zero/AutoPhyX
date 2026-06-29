# AutoPhyX

AutoPhyX-style text-conditioned physics property prediction.

This repository contains the training and data augmentation scripts used for
PixieVerse/VoMP-style experiments where 3D visual voxel features are conditioned
on natural-language physical descriptions. The model predicts dense voxel-level
physical properties:

- density
- Young's modulus `E`
- Poisson ratio `nu`

The core model is a 3D U-Net with FiLM conditioning from OpenCLIP text
embeddings.

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

## Target Normalization

The distribution CSV reports raw physical-property statistics in `min`, `max`,
`mean`, and `std`. It also records the training target transform in
`training_normalization` and the resulting normalized statistics in
`normalized_*` columns.

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

## Notes

Large data artifacts are intentionally excluded from git. Do not commit
`*.npy`, `*.pt`, checkpoints, logs, or rendered assets.
