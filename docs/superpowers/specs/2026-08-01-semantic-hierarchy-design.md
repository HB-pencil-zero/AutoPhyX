# Semantic Hierarchy Cleanup Design

## Goal

Ensure that visual emphasis on the project page always has an explicit informational reason. Remove disconnected large-number callouts and replace the uneven Text2Physics split layout with a coherent, paper-backed reading order.

## Benchmark Section

- Keep the highlighted AutoPhyX (OpenCLIP) table row because the paper reports it as the best result in every displayed metric.
- Add a plain-language table caption explaining that the highlighted row is best and that up/down labels indicate the preferred direction.
- Remove the two large `ABO-500 / 9.433` and `Runtime / 2 seconds` cards.
- Preserve the results as normal-weight contextual prose below the table: ABO-500 ADE is 9.433 versus 11.826 and 12.565 for NeRF2Physics and Pixie; feed-forward inference takes 2 seconds versus minutes to hours for optimization-based methods.

## Text2Physics Section

- Replace the asymmetric two-column layout with one full-width vertical sequence: heading, lead, dataset link, paper figure, figure caption, and three aligned process steps.
- Use the literal heading `Part-aware supervision for text-conditioned physics.` at a restrained section size.
- Include the paper's dataset context in body copy: 1,700 assets, eight text/property annotations per asset, 15 upper-hemisphere views, five segmentation candidates, and engineering-database ranges for Young's modulus, Poisson's ratio, and density.
- Keep emphasis only on the section heading and step names; all supporting facts use normal body weight.

## Responsive Behavior

- Desktop: full-width figure and three equal process columns.
- Mobile: natural-ratio figure followed by stacked process steps with separators.
- No fixed heights or artificial bottom alignment; the single reading flow removes the original top/bottom mismatch.

## Verification

- Regression tests require removal of `.abo-callout`, presence of the contextual benchmark note, the literal dataset heading, and all paper-derived dataset facts.
- Browser checks at 1440x1000 and 500x844 verify the dataset sequence, equal process columns, natural mobile stacking, and no horizontal overflow.
