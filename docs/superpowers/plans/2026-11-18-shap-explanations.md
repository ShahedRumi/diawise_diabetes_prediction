# DiaWise SHAP Explanations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add faithful, understandable Exact SHAP explanations to every DiaWise model-inference result and transparent provenance to catalog-only food results.

**Architecture:** Build one startup-owned `ExplanationService` containing four warmed `ExactExplainer` instances over deterministic 32-row reference backgrounds. API routes pass their existing ordered model-input rows into the service and return additive, display-ready JSON; the existing frontend renders baseline-to-output context and accessible contribution bars without introducing a plotting framework.

**Tech Stack:** Python 3.11–3.13, SHAP 0.51.0, NumPy, pandas, FastAPI, pytest, vanilla JavaScript, Node test runner.

**Spec:** `docs/superpowers/specs/2026-11-18-shap-explanations-design.md`

## Global Constraints

- Pin `shap==0.51.0`; keep the project fully local and offline after installation.
- Preserve all model artifacts, probabilities, thresholds, classifications, and existing response fields.
- Explain the final positive-class probability using exact input-level SHAP; do not substitute approximate or heuristic attributions.
- SHAP language describes model behavior, never medical causation or individualized clinical risk.
- Do not apply SHAP to direct known-food catalog labels.
- Do not persist, cache, or access-log user inputs.
- This directory is not a Git repository, so commit steps are omitted and the execution ledger records task gates.

## Review Focus

- Binary/multi-output SHAP shapes must be normalized without selecting the wrong class or feature axis.
- PIMA zero-as-missing and engineered features must stay inside the explained pipeline while the response shows exactly eight raw inputs.
- General category contributions must calculate on encoded values but display original labels.
- Food contributions must explain the final calibrated probability and normalized 100 g values, not an individual base estimator.
- Explanation initialization, locking, additivity failures, and request timeouts must never yield an unexplained medical result.

---

### Task 1: Exact SHAP explanation service

**Files:**
- Create: `app/ml/explanations.py`
- Create: `tests/test_explanations.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `ExplanationService.build(pima_model, general_bundle, food_model, data_dir: Path, background_size: int = 32) -> ExplanationService`.
- Produces: `explain_pima(row: pd.DataFrame, display_values: dict[str, str]) -> dict`.
- Produces: `explain_general(mode: Literal['full', 'nonlab'], row: pd.DataFrame, display_values: dict[str, str]) -> dict`.
- Produces: `explain_food(row: pd.DataFrame, display_values: dict[str, str]) -> dict`.
- Produces: `warm_up() -> None`.

- [ ] **Step 1: Write failing service tests**

Add tests named `test_pima_explanation_is_additive_and_has_eight_raw_features`, `test_general_modes_preserve_display_categories_and_feature_counts`, `test_food_explains_calibrated_probability_on_normalized_features`, `test_features_are_finite_deterministic_and_sorted_by_absolute_effect`, `test_explainer_calls_are_lock_protected`, and `test_additivity_failure_raises_without_returning_an_explanation`.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_explanations.py -q`

Expected: FAIL because `app.ml.explanations` does not exist.

- [ ] **Step 3: Pin and install SHAP**

Add `shap==0.51.0` to `requirements.txt`, install the updated requirements in the local environment, and verify `python -c "import shap; print(shap.__version__)"` prints `0.51.0`.

- [ ] **Step 4: Implement `ExplanationService`**

Build fixed-seed 32-row backgrounds from the three included datasets, construct four `shap.ExactExplainer` instances over positive-probability wrapper functions, add per-explainer locks, serialize finite sorted contributions with user-facing metadata, enforce `1e-5` additivity, and warm every explainer using a fixed reference row.

- [ ] **Step 5: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_explanations.py -q`

Expected: all service tests pass.

### Task 2: Startup and API integration

**Files:**
- Modify: `app/main.py`
- Modify: `app/launcher.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_launcher.py`

**Interfaces:**
- Consumes: `ExplanationService` methods from Task 1.
- Produces: existing artifact tuple extended with one startup-warmed explanation service.
- Produces: `explanation` response object on PIMA, General, and Food prediction routes.

- [ ] **Step 1: Write failing API and launcher tests**

Add endpoint tests proving PIMA has 8 additive factors, General Full/Non-Lab have 8/6 readable factors, custom food has 5 calibrated factors, known food returns `kind='dataset_lookup'` without SHAP, identical requests are deterministic, explanation initialization failure makes health unavailable, and launcher arguments disable Uvicorn access logging.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_launcher.py -q`

Expected: new assertions fail because responses have no `explanation` and launcher access logs are enabled.

- [ ] **Step 3: Integrate startup and response generation**

Construct and warm `ExplanationService` inside `load_artifacts`; update every artifact unpack; call the appropriate explainer only after constructing the exact row used for probability; build original-label display maps; add the catalog-provenance object; translate explanation failures to an actionable 503 that does not return the prediction; add `--no-access-log` to the Uvicorn subprocess.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_launcher.py -q`

Expected: all API and launcher tests pass.

### Task 3: Understandable explanation UI

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/main.js`
- Modify: `static/css/style.css`
- Modify: `tests/http.test.mjs`

**Interfaces:**
- Consumes: the API `explanation` contract from Task 2.
- Produces: `renderExplanation(explanation) -> void` rendering into `#explanation-panel`.

- [ ] **Step 1: Write failing browser-realm tests**

Extend the existing VM-based browser tests with `SHAP explanation renders baseline output all factors directions and caveat`, `dataset lookup renders provenance without contribution bars`, and `explanation remains complete at mobile width`. Assert signed percentage-point text and explicit direction words, not only CSS classes.

- [ ] **Step 2: Verify RED**

Run: `node --test tests/http.test.mjs`

Expected: new tests fail because the explanation panel and renderer do not exist.

- [ ] **Step 3: Implement accessible explanation rendering**

Add the result-panel section; render baseline/output context, target-specific orientation, all factor rows, normalized diverging bars, readable values, signed percentage points, and caveat using text nodes; render catalog provenance without bars; add responsive styles for 320 px width; reset/hide stale explanation state between predictions.

- [ ] **Step 4: Verify GREEN**

Run: `node --test tests/http.test.mjs`

Expected: all frontend tests pass.

### Task 4: Documentation, integrity, and end-to-end evidence

**Files:**
- Modify: `README.md`
- Modify: `START_HERE.txt` only if installation copy requires it
- Modify: `CHECKSUMS.sha256`
- Modify: `screenshots/prediction_studio_desktop.png`
- Modify: `screenshots/prediction_studio_mobile.png`

- [ ] **Step 1: Update documentation**

Document SHAP dependency/version, exact input-level explanation behavior, API response contract, limitations/non-causation, troubleshooting, file structure, and removal of the previous “no personally tailored SHAP” statement.

- [ ] **Step 2: Run complete automated verification**

Run: `.venv\Scripts\python.exe -m pytest -q`

Run: `node --test tests/http.test.mjs`

Run: `node --check static/js/http.js` and `node --check static/js/main.js`

Run: `run_windows.bat -Check`

Expected: zero failures; only documented third-party warnings may remain.

- [ ] **Step 3: Verify real API behavior and additivity**

Start through `app.launcher` without opening a browser. Exercise PIMA, both General modes, custom food, and known food; assert HTTP 200, correct explanation kind/count, and full-precision additivity for every SHAP response.

- [ ] **Step 4: Measure performance and concurrency**

Measure cold readiness including warm-up, five serial warm calls for each inference route, and two simultaneous calls to one locked explainer. Expected: each serial median under 2 seconds and every measured request under 10 seconds. If not, stop for a product decision rather than changing algorithms.

- [ ] **Step 5: Capture and inspect explanation screenshots**

Capture desktop and 480 px mobile result cards after a real explained prediction; inspect that all factors, direction text, signed contributions, and the caveat are visible and readable.

- [ ] **Step 6: Recompute and verify integrity**

Update checksums for every changed/added distributable file, verify every listed hash, and confirm the project-wide English-only scan remains clean.
