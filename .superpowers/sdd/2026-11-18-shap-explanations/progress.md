# SDD ledger — plan: docs/superpowers/plans/2026-11-18-shap-explanations.md

Pre-flight: Task 1 produces `ExplanationService`; Task 2 consumes its four explain methods and extends the startup artifact tuple; Task 3 consumes the exact API JSON contract; Task 4 verifies the integrated result.

Completed:
- Task 1: Added `shap==0.51.0` and a deterministic, lock-protected Exact SHAP service with additivity/finite validation and startup warm-up.
- Task 2: Integrated explanations into PIMA, General Full/Non-Lab, and calibrated custom-food responses; added direct catalog provenance and disabled access logging.
- Task 3: Added accessible baseline-to-output UI, signed percentage-point directions, diverging bars, caveats, and responsive behavior.
- Task 4: Updated README and checksums; added unit, API, UI, launcher, and performance regression tests.

Verification:
- Python: 30 passed.
- Node: 6 passed; JavaScript syntax check passed.
- End-to-end localhost smoke: health OK; factor counts PIMA 8, General Full 8, custom food 5; catalog provenance returned.
- Warm medians: PIMA 0.076s, General Full 0.005s, General Non-Lab 0.003s, food 0.012s; two concurrent PIMA calls 0.152s.
- Responsive desktop/mobile visual inspection passed.
- 50 distributable checksums verified; English-only test passed in the full suite.
