# Text2Physics Flow Redesign

## Goal

Make the Text2Physics section explain, at a glance, how a 3D asset becomes a text-conditioned, simulation-ready training example. The current cropped paper image is too low-resolution to communicate that process.

## User-Facing Explanation

The visual explains this data-generation path:

1. Engineering references provide plausible material-property ranges.
2. A source asset is split into semantic 3D parts.
3. Natural-language conditions state which parts change and how.
4. The result is a dense voxel field with density, Young's modulus, and Poisson's ratio for simulation and supervision.

## Layout

### Desktop

Use a two-column CSS grid with equal-height rows. The left column contains the section label, heading, short explanation, and dataset link. The right column contains a single framed flow panel. Both columns align at their top and bottom edges within the same section band.

The flow panel has four equal-width stages on one baseline. Each stage includes a concise label, a small supporting visual, and one sentence. Directional connectors make the left-to-right progression explicit. A full-width output strip below the stages names the voxel fields `rho`, `E`, and `nu`.

### Mobile

Stack the left-column copy, flow panel, and dataset link in reading order. The flow stages become a compact vertical sequence with connectors between adjacent stages. The output strip remains attached to the flow panel.

## Visual Direction

Replace the low-resolution paper crop with a code-native, accessible flow illustration built from HTML and CSS. It must use the existing restrained editorial palette and type system, avoid decorative cards, and remain readable without zooming. The visual is explanatory, not a paper reproduction.

## Content

| Stage | Label | Explanation |
| --- | --- | --- |
| 01 | Source | Engineering references define plausible ranges for material behavior. |
| 02 | Segment | The asset is represented as named semantic 3D parts. |
| 03 | Condition | Text selects parts and describes their intended physical behavior. |
| 04 | Ground | The selected values become dense material fields for every occupied voxel. |

Output strip: `Voxel field: density rho | Young's modulus E | Poisson's ratio nu`.

## Implementation Boundaries

- Retain the `#dataset` anchor, Text2Physics copy, and dataset link.
- Remove the paper-crop figure and its three-item explanatory rail.
- Keep the section within the established desktop and mobile container widths.
- Do not change the Results, Method, Benchmark, or navigation sections.

## Verification

- Update the existing shell regression test for the new flow structure and removal of `data-generation.webp` from the dataset section.
- Confirm desktop and mobile screenshots have aligned section columns, readable stage labels, visible connectors, and no clipping or overlap.
- Run the page regression test, JavaScript syntax check, and `git diff --check`.
