# Volumetric Stage Alignment Design

## Goal

Make the two volumetric-grounding figures read as one comparison: equal column widths, equal media heights, aligned borders, and substantially more method detail drawn from the ECCV paper.

## Layout

- Use a two-column `1fr 1fr` grid on desktop.
- Give both media areas the same 16:9 canvas and center each source image with `object-fit: contain`; do not crop figure labels.
- Keep the existing single-column mobile layout and return media areas to their natural aspect ratios below 640px.
- Keep both captions in the same index/title/body structure so their baselines and text widths align.

## Paper-Derived Copy

The extraction explanation will state that AutoPhyX lifts multi-view 2D OpenCLIP features into a continuous 3D field through differentiable volume rendering. It will contrast this with VoMP-style naive averaging and explain that accumulated transmittance suppresses occluded observations, preventing foreground features from contaminating hidden parts.

The completion explanation will state why a surface-only field is insufficient for physical parameters such as Young's modulus, Poisson's ratio, and density. It will describe coarse six-direction enclosure checks, even-odd ray-surface intersection refinement for concavities, and nearest-neighbor propagation of semantic surface features into accepted interior voxels.

## Verification

- Automated checks assert equal desktop columns, a shared media aspect ratio, and representative paper terminology.
- Browser checks at 1440x1000 and 500x844 confirm equal desktop geometry, readable figures, natural mobile stacking, and no horizontal overflow.
