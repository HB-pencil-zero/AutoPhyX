# Overview Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reformat the overview as an aligned, paper-like heading and two-column explanation without unjustified oversized or bold text.

**Architecture:** Keep the static page structure and existing paper figure. Replace the current asymmetric `.intro-grid` with a full-width heading followed by a dedicated equal-column `.intro-copy-grid`, then add a mobile single-column rule.

**Tech Stack:** HTML5, CSS, shell regression tests

---

### Task 1: Lock the overview hierarchy and alignment contract

**Files:**
- Modify: `tests/test_project_page.sh`

- [ ] **Step 1: Add failing assertions**

Require the new literal heading and `.intro-copy-grid`, reject the old promotional heading, and assert equal desktop columns with `align-items: start` plus a single mobile column.

- [ ] **Step 2: Verify the test fails for the missing structure**

Run: `bash tests/test_project_page.sh`

Expected: non-zero exit because the new heading and paragraph grid do not exist.

### Task 2: Implement the paper-like overview

**Files:**
- Modify: `index.html`
- Modify: `static/css/site.css`

- [ ] **Step 1: Replace the asymmetric markup**

Use a full-width `.intro-heading` followed by `.intro-copy-grid` containing two normal-weight paragraphs. Keep the figure immediately after this text sequence.

- [ ] **Step 2: Add the alignment CSS**

Set `.intro-copy-grid` to `repeat(2, minmax(0, 1fr))`, `align-items: start`, and a single vertical divider. Stack it at `max-width: 900px` and replace the divider with a horizontal rule.

- [ ] **Step 3: Update the stylesheet cache key**

Change the `site.css` query value in `index.html` and its regression assertion so deployed browsers load the new layout.

- [ ] **Step 4: Verify the implementation**

Run: `bash tests/test_project_page.sh && node --check static/js/site.js && git diff --check`

Expected: all commands exit zero.

### Task 3: Verify and publish

**Files:**
- No source changes expected

- [ ] **Step 1: Inspect desktop and mobile rendering**

At desktop width, confirm both paragraphs start at the same vertical coordinate and occupy equal-width columns. At mobile width, confirm a single readable column and no horizontal overflow.

- [ ] **Step 2: Commit and push**

Commit the tested changes to `main`, push to `origin/main`, and verify the GitHub Pages workflow succeeds.
