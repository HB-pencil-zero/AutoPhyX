# Citation And Footer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the citation and footer as a compact, aligned page ending.

**Architecture:** Preserve the existing BibTeX data and copy JavaScript. Change only the citation HTML hierarchy, its CSS grid/tool styling, and the footer content wrapper.

**Tech Stack:** HTML5, CSS, existing JavaScript copy handler, shell regression tests

---

### Task 1: Add the layout contract

**Files:**
- Modify: `tests/test_project_page.sh`

- [ ] Require `Cite this work.`, `.citation-block-header`, and `.site-footer-inner`.
- [ ] Reject the old oversized citation heading and verify the test fails.

### Task 2: Implement the citation tool and footer

**Files:**
- Modify: `index.html`
- Modify: `static/css/site.css`

- [ ] Replace the repeated product heading with a functional citation heading.
- [ ] Move the copy button into a labeled BibTeX toolbar.
- [ ] Use a top-aligned `0.68fr / 1.32fr` citation grid with compact section spacing.
- [ ] Wrap footer content in `.site-footer-inner` so its background spans the viewport.
- [ ] Update the stylesheet cache key.

### Task 3: Verify and publish

- [ ] Run `bash tests/test_project_page.sh && node --check static/js/site.js && git diff --check`.
- [ ] Check desktop and mobile geometry, appearance, copy feedback, and console output.
- [ ] Commit, push to `main`, and verify GitHub Pages plus deployed HTML/CSS.
