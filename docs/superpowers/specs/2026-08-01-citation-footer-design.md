# Citation And Footer Design

## Goal

Turn the page ending into a compact research utility instead of a second promotional hero.

## Citation

- Replace the oversized repeated product name with the functional heading `Cite this work.`
- Use a narrow explanation column and a wider BibTeX column, aligned at the top.
- Give the BibTeX tool a small header that names the format and contains the copy action.
- Use a neutral white section with a restrained border; remove the large cream color field and excessive vertical space.

## Footer

- Make the dark footer background span the full viewport width.
- Keep footer content aligned to the same `1180px` content grid as the page.
- Stack footer content and links cleanly on mobile.

## Verification

- Regression tests require the new functional heading, BibTeX header, and full-width footer wrapper.
- Desktop and mobile browser checks verify alignment, readable code, no horizontal page overflow, and working copy feedback.
