# Semantic Hierarchy Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unsupported visual emphasis from benchmarks and rebuild Text2Physics as an aligned, paper-backed information sequence.

**Architecture:** Keep the static page and existing assets. Replace metric callout cards with contextual prose, flatten the dataset split grid into a full-width sequence, and expand step copy using the paper's documented generation protocol.

**Tech Stack:** HTML5, CSS, shell regression tests

---

### Task 1: Remove Disconnected Benchmark Emphasis

**Files:**
- Modify: `tests/test_project_page.sh`
- Modify: `index.html`
- Modify: `static/css/site.css`

- [ ] **Step 1: Add failing benchmark assertions**

```bash
if rg -q 'abo-callout' index.html static/css/site.css; then exit 1; fi
rg -q 'On the real-world ABO-500 benchmark' index.html
rg -q 'Highlighted row marks the best result' index.html
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `bash tests/test_project_page.sh`

Expected: exit 1 because `.abo-callout` still exists.

- [ ] **Step 3: Replace cards with contextual notes**

Add a table caption that explains the highlighted best row and a normal-weight paragraph that compares ADE 9.433 with 11.826/12.565 and 2-second inference with optimization methods that take minutes to hours. Remove all `.abo-callout` markup and CSS.

- [ ] **Step 4: Run the test and confirm green**

Run: `bash tests/test_project_page.sh`

Expected: exit 0.

### Task 2: Rebuild Text2Physics Reading Order

**Files:**
- Modify: `tests/test_project_page.sh`
- Modify: `index.html`
- Modify: `static/css/site.css`

- [ ] **Step 1: Add failing dataset assertions**

```bash
rg -q 'Part-aware supervision for text-conditioned physics' index.html
rg -q '1,700 3D assets' index.html
rg -q 'eight text-and-property annotations' index.html
rg -q '15 upper-hemisphere views' index.html
rg -q 'five segmentation candidates' index.html
rg -Fq 'grid-template-columns: repeat(3, minmax(0, 1fr));' static/css/site.css
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `bash tests/test_project_page.sh`

Expected: exit 1 because the literal heading and paper-derived facts are missing.

- [ ] **Step 3: Implement the full-width sequence**

Place `.dataset-heading`, `.dataset-figure`, and `.dataset-process` in document order inside `.dataset-layout`. Use a single-column layout, constrain the heading to a readable width, keep the figure full width, and retain three equal process columns on desktop.

- [ ] **Step 4: Add detailed process copy**

Describe 15 upper-hemisphere views and five segmentation candidates in `Segment`; selected part subsets and plausible language variants in `Describe`; and MatWeb/Wikipedia/Engineering Toolbox ranges for `E`, `nu`, and `rho` in `Assign`.

- [ ] **Step 5: Bust CSS cache and verify**

Run: `bash tests/test_project_page.sh && node --check static/js/site.js && git diff --check`

Expected: exit 0.

- [ ] **Step 6: Verify desktop and mobile**

At 1440x1000, confirm the dataset heading, figure, and process occupy one aligned full-width flow with three equal step columns. At 500x844, confirm one-column steps, readable text, and no horizontal overflow.

- [ ] **Step 7: Commit, push, and verify Pages**

Push to `origin/main`, wait for Pages success, then repeat the structural and browser checks against the deployed URL.
