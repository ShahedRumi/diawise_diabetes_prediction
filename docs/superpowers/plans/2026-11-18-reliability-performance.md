# DiaWise Reliability and Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DiaWise start reliably, report readiness only after its models are loaded, and bound browser requests so failures do not hang indefinitely.

**Architecture:** Keep the existing FastAPI and vanilla-JavaScript application. Add an explicit artifact-loading boundary with startup preloading, make the Windows batch launcher validate/recover its virtual environment and delegate server supervision/readiness polling to a small standard-library Python launcher, and centralize frontend JSON requests behind an abortable timeout helper.

**Tech Stack:** Python 3.11/3.12, FastAPI, Uvicorn, pytest, Windows batch, vanilla JavaScript, Node's built-in test runner.

**Spec:** `docs/superpowers/specs/2026-11-18-reliability-performance-design.md`

## Global Constraints

- Remain fully local and offline after dependencies are installed.
- Preserve model outputs, thresholds, datasets, and research claims.
- Preserve the existing FastAPI, Uvicorn, and vanilla-JavaScript architecture.
- Preserve a broken environment under a timestamped backup name instead of deleting it silently.
- This directory is not a Git repository, so commit steps are omitted.

## Review Focus

- Missing or corrupt model artifact must prevent readiness with a concise actionable error.
- Two simultaneous first requests must not load the model set twice.
- A stale or non-running `.venv` must be backed up and rebuilt with Python 3.11/3.12.
- A server that never becomes healthy must terminate with a nonzero exit instead of opening the browser.
- A browser request that exceeds its deadline must abort and restore the enabled UI state.

---

### Task 1: Backend artifact readiness

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `load_artifacts() -> tuple`, `artifact_status() -> dict`, and a FastAPI lifespan that preloads once before accepting requests.

- [ ] **Step 1: Write failing tests**

Add `test_lifespan_preloads_artifacts_once`, `test_health_reports_artifact_load_failure_as_503`, and `test_concurrent_load_uses_one_artifact_instance`; assert observable readiness/status and a single loader execution.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api.py -q`

Expected: the new tests fail because startup does not own artifact loading or expose a stable failure state.

- [ ] **Step 3: Implement minimal preload/readiness behavior**

Replace request-triggered `lru_cache` loading with one lock-protected artifact store initialized in FastAPI lifespan; make `/api/health` return readiness without triggering work, and translate artifact parsing/loading errors into a concise 503 response.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api.py -q`

Expected: all API tests pass.

### Task 2: Recoverable Windows startup and readiness polling

**Files:**
- Create: `app/launcher.py`
- Create: `tests/test_launcher.py`
- Modify: `run_windows.bat`
- Modify: `README.md`

**Interfaces:**
- Produces: `wait_until_ready(url: str, process: subprocess.Popen, timeout_seconds: float) -> None` and `run_server(open_browser: bool = True) -> int`.

- [ ] **Step 1: Write failing launcher tests**

Add `test_wait_until_ready_returns_after_healthy_response`, `test_wait_until_ready_fails_when_server_exits`, and `test_wait_until_ready_times_out`; use a local in-process HTTP server or controlled fake process, not network mocks.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_launcher.py -q`

Expected: import fails because `app.launcher` does not exist.

- [ ] **Step 3: Implement the standard-library supervisor**

Start Uvicorn with the current interpreter, poll `/api/health` for at most 45 seconds, open the browser only after a 200 response, propagate early server exit, and terminate the child on Ctrl+C.

- [ ] **Step 4: Harden `run_windows.bat`**

Select only `py -3.12` or `py -3.11`; validate the existing environment with an executable/version/import probe; rename an invalid `.venv` to `.venv.broken-<timestamp>`; create/install when missing; then run `python -m app.launcher`.

- [ ] **Step 5: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_launcher.py -q`

Expected: all launcher tests pass.

### Task 3: Bounded frontend requests

**Files:**
- Create: `static/js/http.js`
- Create: `tests/http.test.mjs`
- Modify: `templates/index.html`
- Modify: `static/js/main.js`

**Interfaces:**
- Produces: `window.DiaWiseHttp.fetchJson(url, options = {}, timeoutMs = 10000) -> Promise<object>`.

- [ ] **Step 1: Write failing frontend tests**

Add `fetchJson returns parsed JSON`, `fetchJson surfaces API detail`, and `fetchJson aborts after the deadline`; exercise real `AbortController` behavior with controlled promises.

- [ ] **Step 2: Verify RED**

Run: `node --test tests/http.test.mjs`

Expected: import fails because `static/js/http.js` does not exist.

- [ ] **Step 3: Implement and integrate the timeout helper**

Load `http.js` before `main.js`; route prediction, autocomplete, and metrics requests through `fetchJson`; keep prediction errors visible and ensure `finally` restores the submit button.

- [ ] **Step 4: Verify GREEN**

Run: `node --test tests/http.test.mjs`

Expected: all frontend request tests pass.

### Task 4: Full verification and performance evidence

**Files:**
- Modify only if verification reveals a regression in files already listed above.

- [ ] **Step 1: Run the complete automated suites**

Run: `.venv\Scripts\python.exe -m pytest -q`

Run: `node --test tests/http.test.mjs`

Expected: zero failures and no unexpected warnings.

- [ ] **Step 2: Verify the production startup path**

Run the launcher with browser opening disabled, confirm `/api/health` reports ready, exercise one request for each model, then stop the server cleanly.

- [ ] **Step 3: Measure cold and warm behavior**

Record server-ready duration plus at least five warm calls to `/api/health`, `/api/models`, and each prediction route; report median and worst latency. The first user request must not include artifact loading.

- [ ] **Step 4: Recheck project integrity**

Recompute `CHECKSUMS.sha256` entries for intentionally changed distributable files and verify every listed checksum.
