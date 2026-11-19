# SDD ledger — plan: docs/superpowers/plans/2026-11-18-clean-english-ui.md

Ruling: Work in the existing checkout because the user explicitly requested immediate implementation and it already contains the uncommitted SHAP feature from the preceding task — committing or moving those user-visible changes would broaden the request — cost if wrong: this cleanup is not isolated in its own commit.
Pre-flight: Task 1 cache-safe assets are consumed by Task 2's simplified frontend; Task 3 hashes the outputs of both.
Root cause: repository scan found zero Bengali characters; the supplied screenshot showed the pre-English JavaScript bundle, so the visible mixed-language state came from an already-open stale page rather than current source text.
Task 1: complete (tests: focused English/UI/cache contract RED with 3 expected failures, then 7 passed).
Task 2: complete (JavaScript syntax passed; live desktop/mobile DOM measured; compact result visually inspected; all-factor toggle exposed 6/6 factors and changed to “Show fewer factors”).
Task 3: complete (32 Python tests passed; 6 Node tests passed; JavaScript syntax and diff checks passed; 50 checksums verified).
Final review: fresh reviewer found no Critical or Important issues.
Final: minor (deferred): English-only scan covers source/document text but not future CSV/JSON data updates; current datasets and rendered UI are clean.
Final: minor (deferred): factor toggle is keyboard-operable with `aria-expanded` but does not also declare `aria-controls` for the factor list.
