# DiaWise reliability and performance repair

## Intent

Make the existing local research application start consistently, become ready before the browser opens, respond promptly on the first interaction, and recover with a useful message instead of hanging.

## Goals

- Detect and repair an unusable or incompatible virtual environment at launch.
- Start only with a supported Python runtime and verified dependencies.
- Load and validate all three model artifacts before the server reports ready.
- Wait for readiness before opening the browser.
- Give browser requests bounded timeouts and actionable failure messages.
- Protect the repaired behavior with focused regression tests and measure cold/warm request latency.

## Non-goals

- Retraining or changing model outputs, thresholds, datasets, or research claims.
- Redesigning the interface or packaging the project as an executable.
- Broad refactoring unrelated to startup, readiness, and request reliability.

## Constraints

- Remain fully local and offline after dependencies are installed.
- Preserve the existing FastAPI, Uvicorn, and vanilla-JavaScript architecture.
- Never silently discard the existing environment; replacement must be deliberate and recoverable.

## Approaches considered

1. Launcher-only repair: smallest change, but leaves cold first requests and indefinite browser waits.
2. Full reliability repair: launcher validation, fail-fast model preload, readiness polling, client timeouts, and tests. Selected because it addresses all observed failure boundaries without changing model behavior.
3. Standalone Windows packaging: easier distribution but substantially larger and risks new native-library compatibility problems.

## Implementation shape

- Extract testable artifact loading/readiness behavior in the API and preload it during application lifespan.
- Strengthen the Windows launcher so it validates the interpreter and environment, installs only when needed, starts Uvicorn, polls `/api/health`, and opens the browser only after success.
- Add a small reusable fetch timeout in the frontend for predictions, autocomplete, and metrics.
- Add focused API tests for readiness/load failures and frontend/launcher behavior where practical, followed by the full test suite and startup/request benchmarks.
