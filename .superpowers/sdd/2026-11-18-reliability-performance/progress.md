# SDD ledger — plan: docs/superpowers/plans/2026-11-18-reliability-performance.md

Ruling: The prescribed SDD scripts require a Git repository, but this distributed project has no `.git`; task briefs, test gates, and review records will be maintained directly in this ledger — cost if wrong: there is no commit-range recovery, so verification output and file backups are the recovery evidence.
Pre-flight: Task 1 readiness is consumed by Task 2 launcher polling; `/api/health` remains the shared interface and must return HTTP 200 only after artifacts are loaded.
Pre-flight: Task 3 has no shared production interface with Tasks 1–2 beyond existing HTTP JSON contracts, which remain unchanged.
Task 1: complete (no Git range, tests: `.venv\Scripts\python.exe -m pytest tests/test_api.py -q` → 8 passed, 1 third-party deprecation warning).
Task 2: Ruling: Support Python 3.13 in addition to the plan's 3.11/3.12 because the supplied environment is Python 3.13.14 and loaded all bundled artifacts successfully — cost if wrong: a future 3.13 dependency wheel or pickle incompatibility could require rebuilding with 3.11/3.12.
Task 2: complete (no Git range, tests: `.venv\Scripts\python.exe -m pytest tests/test_launcher.py -q` → 3 passed).
Task 3: complete (no Git range, tests: `node --test tests/http.test.mjs` → 3 passed).
Final: fixed occupied-port readiness race — `test_run_server_reuses_an_existing_healthy_instance` RED→GREEN, suite 12/12 Python and 3/3 Node.
Task 4: complete (real startup ready in 1799.43 ms; page, static helper, health, metadata, PIMA, general, known-food, and custom-food routes all HTTP 200; warm worst latency 34.24 ms; 43/43 checksums valid; no listener left on port 8000).
Final: fixed browser global-scope collision — `classic browser scripts share one realm and restore the form after failure` RED→GREEN.
Final: fixed response-body timeout and malformed-success handling — two `fetchJson` regression tests RED→GREEN.
Final: fixed readable-but-incompatible model readiness — `test_readable_but_unusable_artifact_prevents_readiness` RED→GREEN.
Final: fixed swallowed terminal artifact error — `test_wait_until_ready_surfaces_terminal_artifact_failure` RED→GREEN.
Final: fixed Windows CMD parsing, first-install variable expansion, and recoverable broken-environment handling by moving bootstrap logic to `run_windows.ps1` — two PowerShell integration tests RED→GREEN; actual `run_windows.bat -Check` passed.
Final: Ruling: Model accuracy and training methodology remain unchanged because the repair preserves the supplied artifacts and research behavior — cost if wrong: an existing model-quality limitation remains outside this reliability repair.
Final: Ruling: Keep the standard subprocess supervisor after the reviewer declined real Windows console-interrupt testing; normal Ctrl+C is handled and `finally` terminates the child, but abrupt parent termination outside Python cleanup may leave Uvicorn running — cost if wrong: a user may need to close a leftover Python process or restart before relaunching.
Final: minor (deferred): A non-DiaWise service returning a JSON array from `/api/health` can raise `AttributeError` instead of the clearer occupied-port message.
