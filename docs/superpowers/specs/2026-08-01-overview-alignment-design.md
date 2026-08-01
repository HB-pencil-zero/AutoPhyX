# Overview Alignment Design

## Goal

Replace the promotional split treatment in the overview with a restrained, paper-like hierarchy whose text blocks share explicit horizontal and vertical alignment.

## Information Hierarchy

- `Why text matters` remains the section label.
- `Resolving visual ambiguity with language` becomes the only section heading. It spans the content width and uses the same section-heading scale as the rest of the page.
- The oversized sentence `Appearance alone does not determine physics.` is removed. It does not name a section or report a result, so its visual weight is not justified.
- Two normal-weight paragraphs summarize the paper's motivation and output. Neither paragraph contains decorative bold text.

## Layout

- Desktop: the heading spans the full content width. Below it, two equal columns begin at the same top coordinate, use the same typography, and are separated by a single rule.
- The first paragraph explains why visual input is ambiguous; the second explains how AutoPhyX resolves the ambiguity and what it predicts.
- The overview figure and caption use the same outer content width as the heading and paragraphs.
- Mobile: the paragraphs stack into one column with a horizontal separator and no fixed height.

## Verification

- Structural regression tests reject the old heading and require the new heading and paragraph grid.
- CSS assertions require two equal desktop columns, top alignment, and a one-column mobile layout.
- Browser checks at desktop and mobile sizes verify common left/right boundaries, matched paragraph top positions on desktop, and no horizontal overflow.
