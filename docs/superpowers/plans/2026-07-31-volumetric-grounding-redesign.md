# Volumetric Grounding Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the oversized dark volumetric-grounding block with a concise, paper-faithful two-stage explanation using the original ECCV figures.

**Architecture:** Keep the site as static HTML and CSS. Export the paper's `extract3d.pdf` and `filling.pdf` as optimized WebP assets, then render them as two semantic figures in a responsive 60/40 grid with direct captions.

**Tech Stack:** HTML5, CSS, shell regression tests, Poppler, ImageMagick

---

### Task 1: Add Structure Regression Coverage

**Files:**
- Modify: `tests/test_project_page.sh`

- [ ] **Step 1: Add assertions for the new section contract**

```bash
rg -q 'From visible surfaces to a complete 3D field' index.html
rg -q 'static/images/visibility-extraction.webp' index.html
rg -q 'static/images/interior-filling.webp' index.html
! rg -q 'Preserve structure, including what the camera cannot see' index.html
! rg -q 'class="check-list"' index.html
```

- [ ] **Step 2: Run the regression test and confirm it fails**

Run: `bash tests/test_project_page.sh`

Expected: non-zero exit because the new heading and image references do not exist yet.

### Task 2: Export Paper Figures

**Files:**
- Create: `static/images/visibility-extraction.webp`
- Create: `static/images/interior-filling.webp`

- [ ] **Step 1: Render each source PDF at 180 DPI**

```bash
pdftoppm -f 1 -singlefile -png -r 180 "$PAPER_ASSETS/figures/extract3d.pdf" /tmp/visibility-extraction
pdftoppm -f 1 -singlefile -png -r 180 "$PAPER_ASSETS/figures/filling.pdf" /tmp/interior-filling
```

- [ ] **Step 2: Crop whitespace and export optimized WebP files**

```bash
magick /tmp/visibility-extraction.png -trim +repage -quality 88 static/images/visibility-extraction.webp
magick /tmp/interior-filling.png -trim +repage -quality 88 static/images/interior-filling.webp
```

- [ ] **Step 3: Inspect both images and confirm labels remain legible**

Expected: extraction shows the source bonsai, VoMP field, and AutoPhyX field; filling shows both ray-test conditions and the legend.

### Task 3: Rebuild the Volumetric Grounding Section

**Files:**
- Modify: `index.html`
- Modify: `static/css/site.css`

- [ ] **Step 1: Replace the current dark two-column block**

Use a centered heading with the title `From visible surfaces to a complete 3D field.` followed by two figures: `Visibility-aware extraction` and `Interior completion`. Each figure contains one paper asset and a short explanation of its role.

- [ ] **Step 2: Add responsive two-stage layout styles**

Use a 60/40 desktop grid, top borders instead of card containers, `height: auto` on both images, and a single-column layout below 900px. Remove obsolete `.feature-grid` and `.check-list` dependencies from this section.

- [ ] **Step 3: Bust the stylesheet cache**

Update the `site.css` query string in `index.html` so GitHub Pages clients receive the new layout.

- [ ] **Step 4: Run the regression test**

Run: `bash tests/test_project_page.sh`

Expected: exit 0.

### Task 4: Verify and Publish

**Files:**
- Test: `tests/test_project_page.sh`

- [ ] **Step 1: Run static verification**

```bash
bash tests/test_project_page.sh
node --check static/js/site.js
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 2: Inspect local desktop and mobile layouts**

At 1440x1000 and 500x844, verify both figures load, labels remain readable, captions do not overlap, and `document.documentElement.scrollWidth <= innerWidth`.

- [ ] **Step 3: Commit and push to `main`**

Commit the plan separately, then commit the tested implementation. Push the feature branch to `origin/main`.

- [ ] **Step 4: Verify GitHub Pages**

Confirm the Pages workflow succeeds and repeat desktop/mobile checks against the deployed URL.
