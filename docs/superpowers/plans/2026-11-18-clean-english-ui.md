# Clean English UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a cache-safe, English-only, visually simpler DiaWise interface while preserving all model and SHAP behavior.

**Architecture:** Keep the existing FastAPI and vanilla JavaScript application. Simplify its existing DOM/CSS, render only essential result content, and add response/asset cache busting at the HTTP boundary.

**Tech Stack:** FastAPI, HTML, CSS, vanilla JavaScript, pytest, Node test runner.

**Spec:** `docs/superpowers/specs/2026-11-18-clean-english-ui-design.md`

## Global Constraints

- Preserve every prediction input and explanation value.
- Use English-only user-facing copy.
- Keep all SHAP factors accessible.
- Do not add dependencies.

## Review Focus

- An already-open browser must receive new English assets after refresh.
- Known-food provenance must still render without feature bars.
- Hidden lower-impact factors must be keyboard-expandable.
- Mobile layout must remain single-column.
- Medical caveats must remain visible once, without repeated warning boxes.

---

### Task 1: English and cache regression contract

**Files:**
- Modify: `tests/test_english_only.py`
- Modify: `tests/test_explanation_ui.py`
- Modify: `app/main.py`
- Modify: `templates/index.html`

**Interfaces:**
- Produces: cache-safe HTML/static responses and versioned frontend asset URLs.

- [ ] Write tests asserting no Bengali text, versioned assets, `no-store`, and absence of redundant UI regions.
- [ ] Run the focused tests and observe failure.
- [ ] Add cache headers/versioned assets and remove redundant markup.
- [ ] Run the focused tests and observe success.

### Task 2: Simplified explanation and layout

**Files:**
- Modify: `static/js/main.js`
- Modify: `static/css/style.css`
- Modify: `tests/test_explanation_ui.py`

**Interfaces:**
- Consumes: existing explanation JSON.
- Produces: compact explanation rendering with all factors accessible.

- [ ] Write failing UI contract assertions for compact factor disclosure and removed commentary rendering.
- [ ] Run the focused test and observe failure.
- [ ] Implement the compact result renderer and simplified responsive styles.
- [ ] Run Python and Node UI tests.

### Task 3: Distribution integrity and verification

**Files:**
- Modify: `CHECKSUMS.sha256`
- Modify: `README.md`

**Interfaces:**
- Consumes: completed clean UI.
- Produces: verified distributable project.

- [ ] Document the simplified UI and cache-safe refresh behavior.
- [ ] Update changed-file checksums.
- [ ] Run the full Python suite, Node suite, JavaScript syntax check, checksum verification, and responsive visual smoke test.
