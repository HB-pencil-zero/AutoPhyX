# Volumetric Stage Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the two volumetric figures on equal desktop canvases and expand both explanations with method details from the ECCV paper.

**Architecture:** Keep the existing semantic figure markup and static CSS. Add regression checks for the equal-column/equal-canvas contract, expand the two captions, and make the desktop media geometry equal while preserving natural mobile image ratios.

**Tech Stack:** HTML5, CSS, shell regression tests

---

### Task 1: Define the Alignment and Copy Contract

**Files:**
- Modify: `tests/test_project_page.sh`

- [ ] **Step 1: Add failing assertions**

```bash
rg -Fq 'grid-template-columns: repeat(2, minmax(0, 1fr));' static/css/site.css
rg -Fq 'aspect-ratio: 16 / 9;' static/css/site.css
rg -q 'accumulated transmittance' index.html
rg -q 'six-direction boundary checks' index.html
rg -q 'even-odd rule' index.html
rg -q 'nearest-neighbor' index.html
```

- [ ] **Step 2: Verify the old page fails**

Run: `bash tests/test_project_page.sh`

Expected: exit 1 because the equal-column rule and detailed copy are missing.

### Task 2: Implement and Publish the Refinement

**Files:**
- Modify: `index.html`
- Modify: `static/css/site.css`
- Modify: `tests/test_project_page.sh`

- [ ] **Step 1: Expand both figure captions**

Add two paragraphs per stage. The extraction stage explains multi-view OpenCLIP lifting, accumulated transmittance, and prevention of occlusion contamination. The completion stage explains why physical parameters require a solid interior, then covers six-direction checks, the even-odd rule, and nearest-neighbor semantic propagation.

- [ ] **Step 2: Equalize desktop geometry**

```css
.volumetric-stages {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
}

.volumetric-stage-media {
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
}

.volumetric-stage-media img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
```

Below 640px, remove the fixed aspect ratio and return each image to `height: auto`.

- [ ] **Step 3: Bust the stylesheet cache and run verification**

Run: `bash tests/test_project_page.sh && node --check static/js/site.js && git diff --check`

Expected: exit 0.

- [ ] **Step 4: Verify browser geometry**

At 1440x1000, assert both stage widths and media heights match within one pixel. At 500x844, assert a single column, both images load at natural ratios, and no horizontal overflow exists.

- [ ] **Step 5: Commit, push, and verify Pages**

Push the tested commit to `origin/main`, wait for the Pages workflow to succeed, then repeat the geometry checks against the deployed URL.
