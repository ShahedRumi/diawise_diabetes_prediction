# DiaWise SHAP Explanations Design

## Intent

Every model-generated result must explain, in plain English, how the submitted feature values moved the model from a reference baseline to its final output. The explanation must be faithful to the probability actually shown, remain understandable to a non-technical user, and never imply that a SHAP contribution is a medical cause or personalized clinical risk factor.

The known-food catalog path does not run a model. It must provide a transparent dataset-label explanation and explicitly state that SHAP is not applicable, rather than presenting a fabricated model explanation.

## Goals

- Add local SHAP explanations to PIMA, General Full, General Non-Lab, and custom-food ML predictions.
- Explain the final positive-class probability at the original user-input boundary, including the calibrated food probability.
- Show the reference baseline, final probability, all feature contributions, entered/model values, direction, and relative magnitude.
- Use natural labels and units instead of encoded categories or PIMA engineered-feature names.
- Keep the result mathematically additive: `baseline + sum(contributions) = displayed probability` within a small numerical tolerance.
- Preserve the current model artifacts, classifications, thresholds, privacy behavior, and fully local operation.
- Keep explanations fast enough for an interactive local application and measure the actual latency before completion.

## Non-goals

- Retraining, replacing, or recalibrating any model.
- Claiming causal effects, clinical risk, diagnosis, treatment guidance, or individualized dietary advice.
- Generating global cohort-level SHAP dashboards or dependence plots.
- Applying SHAP to the known-food catalog lookup, which is a direct curated label rather than model inference.
- Returning raw SHAP library plot HTML or adding a plotting framework; the existing UI will render accessible contribution bars from JSON.

## Constraints

- The project supports 64-bit Python 3.11–3.13.
- Pin `shap==0.51.0`, whose official package metadata supports Python 3.11–3.13 and NumPy 2.
- The application must remain usable offline after dependencies are installed.
- User inputs remain in process memory only and are not written to disk or logged.
- Disable Uvicorn access logging in the local launcher so prediction paths and typed food-search query strings are not printed to the terminal.
- Explanations use the included source datasets only; no external data or service is contacted.
- Existing prediction response fields remain backward compatible.

## Approaches considered

### 1. Native Tree SHAP

Use `TreeExplainer` directly on Random Forest, LightGBM, and XGBoost estimators. This is fastest, but PIMA would expose 22 engineered features rather than the eight inputs, and the calibrated food result would not be explained in the same probability space the UI displays.

### 2. Exact input-level SHAP — selected

Wrap each complete prediction function so it accepts the same original model inputs used by the API and returns the displayed positive-class probability. Use `shap.ExactExplainer` with deterministic background records from the included datasets. With only 5–8 features, exact enumeration is appropriate and gives one consistent, additive explanation for pipelines, direct estimators, and the calibrated food ensemble.

### 3. Hybrid native SHAP with feature grouping

Use native Tree SHAP where possible and heuristically distribute engineered-feature contributions back to raw inputs. This is faster but the grouping is subjective, and different models would explain different output spaces.

The selected approach prioritizes fidelity and consistent user meaning. Performance will be bounded through small deterministic reference backgrounds, one-time explainer construction, and benchmark-driven tuning that does not change the algorithm.

## Explanation architecture

Create `app/ml/explanations.py` with an `ExplanationService` constructed once during application startup after the three artifacts load. It owns four exact explainers:

- PIMA: eight raw PIMA inputs → complete pipeline positive probability.
- General Full: eight encoded model inputs → full LightGBM positive probability.
- General Non-Lab: six encoded model inputs → non-lab LightGBM positive probability.
- Custom Food: five normalized per-100g inputs → calibrated XGBoost `Score = 1` probability.

Each wrapper accepts a NumPy matrix from SHAP, converts it to a DataFrame with the exact feature order, and calls the same `predict_proba(...)[..., 1]` path used by the endpoint. This means PIMA preprocessing/engineering and food calibration are included in the explanation.

The service constructs deterministic independent background samples from:

- `data/pima_original.csv`, using `PIMA_INPUTS`.
- `data/general_diabetes_original.csv`, after duplicate removal and the existing gender/smoking encodings, using the mode-specific columns.
- `data/food_100g.csv`, using `FOOD_FEATURES`.

Start with 32 fixed-seed reference rows per explainer. The builder may raise the sample size only if the final benchmark remains comfortably interactive; it must not silently switch to an approximate SHAP algorithm.

Explainers and backgrounds are immutable after startup. Protect each explainer call with its own lock because FastAPI sync routes can run concurrently. Do not cache explanations or retain submitted feature rows after the response is built.

Run one explanation for a fixed reference row through every explainer during startup. Readiness is not reported until these warm-up calls and their additivity checks pass, so the first user prediction does not pay a hidden first-use initialization or compilation cost.

If the SHAP dependency, dataset, or explainer construction fails, readiness is unavailable with an actionable local error. If a per-request explanation cannot be computed or fails additivity/finite-value validation, do not show an unexplained prediction; return an actionable service error.

Readiness is intentionally all-or-nothing. If SHAP initialization fails, the launcher does not open a partial catalog-only interface; known-food lookup becomes available again after the local explanation dependency or reference-data problem is repaired.

## Explanation calculation and validation

For each inference:

1. Build the same ordered model-input row already used for prediction.
2. Compute the endpoint probability through the existing model path.
3. Ask the corresponding exact explainer for the row explanation.
4. Extract the scalar base value and one signed contribution per original feature.
5. Verify all values are finite.
6. Verify `abs(base + sum(contributions) - probability) <= 1e-5`.
7. Sort feature entries by absolute contribution, descending, while retaining stable keys and display metadata.

A positive contribution means “pushed the model output toward the positive class.” A negative contribution means “pushed the model output away from the positive class.” It does not mean the feature medically caused or prevented the outcome.

PIMA explanations show the eight entered values. The full pipeline still handles zero-as-missing and engineered features internally, but those transformations are not shown as separate factors. Existing notes continue to disclose zero-value imputation.

General explanations calculate with encoded values but display the original category labels submitted by the user. Category numbers are never shown as ordered medical quantities.

Custom-food explanations use the five normalized values that actually enter the model. The UI labels mass features as “per 100 g” and preserves glycemic index as an unscaled index.

## API contract

Add an `explanation` object to every prediction response.

For model inference:

```json
{
  "kind": "shap",
  "method": "Exact SHAP",
  "target": "probability of diabetes-positive classification",
  "base_probability": 0.126,
  "output_probability": 0.612,
  "features": [
    {
      "key": "Glucose",
      "label": "Glucose",
      "display_value": "145 mg/dL",
      "contribution": 0.284,
      "direction": "toward_positive"
    }
  ],
  "caveat": "SHAP explains this model's behavior relative to reference data; it does not establish medical causation or personal clinical risk."
}
```

`target` is model-specific:

- PIMA and General: probability of the diabetes-positive class.
- Custom Food: probability of `Score = 1` under the author-curated training labels.

For known-food lookup:

```json
{
  "kind": "dataset_lookup",
  "title": "Why this result appears",
  "message": "This result comes directly from the author-curated dataset label; no model inference was performed, so SHAP does not apply.",
  "decision_basis": "Curated dataset Score",
  "caveat": "The label is not an individualized dietary prescription."
}
```

No raw background records, encoded category numbers, or internal estimator objects are returned.

## User interface

Add a “Why the model predicted this” section to the result card below the probability meter and above the existing notes.

For SHAP explanations it shows:

- A baseline-to-output sentence: “Reference baseline 12.6% → This model output 61.2%.”
- A short orientation: “Positive bars pushed toward the diabetes-positive class; negative bars pushed away.” For food, use “toward/away from Score = 1.”
- One accessible horizontal contribution row for every feature, ordered by absolute effect.
- Feature label and entered/model value.
- Signed percentage-point contribution, such as `+28.4 pp` or `−7.1 pp`.
- A diverging bar with a shared scale based on the largest absolute contribution in that explanation.
- The non-causation caveat in a visually distinct, readable notice.

Use neutral explanatory colors and text labels; color alone must not carry direction. Avoid language such as “risk factor,” “caused,” “healthy,” or “safe.”

For catalog lookup, the same section is titled “Why this result appears” and explains the direct curated-label source without contribution bars.

The section must fit the existing desktop and mobile result layouts, remain readable at 320 px width, and use semantic text that screen readers can understand.

## Documentation

Update README sections for dependencies, model behavior, API responses, limitations, troubleshooting, and file structure. Replace the old statement that the application does not provide personal SHAP explanations. Explain that the new output is a local model-behavior explanation, not a clinical explanation.

Update the quick-start guide only where the additional dependency or first-run installation behavior matters. Recompute `CHECKSUMS.sha256` for all changed and added distributable files.

## Testing and verification

Follow test-first development.

Backend tests must prove:

- PIMA returns eight readable SHAP factors and passes additivity against its displayed probability.
- General Full returns eight factors; Non-Lab returns six; original category labels are displayed.
- Custom Food returns five normalized factors and explains the calibrated probability.
- Known-food lookup returns `dataset_lookup` explanation and never claims SHAP.
- Contributions are finite, sorted by absolute magnitude, and deterministic for a fixed input.
- Explainer construction is single-instance and concurrency-safe.
- Missing SHAP or invalid reference data prevents readiness with an actionable message.
- A failed additivity check does not return an unexplained prediction.

Frontend tests must prove:

- SHAP explanations render baseline, output, all factors, direction text, signed percentage points, and caveat.
- Dataset lookup renders provenance without contribution bars.
- Mobile-width output remains structurally complete.
- Existing timeout and submit-button recovery behavior remains intact.

Final verification must include:

- Full Python and Node suites.
- Windows bootstrap `-Check`.
- Integrity checksum validation.
- Real endpoint calls for PIMA, both General modes, custom food, and known food.
- Additivity checks on those real responses.
- Cold startup timing and at least five warm explanation calls per inference route.
- Visual inspection of desktop and mobile result cards containing explanations.

The primary target on the current machine is a serial warm median under two seconds per explanation route. Startup timing includes all explainer warm-up calls. A two-request concurrent check must also complete both responses within the existing ten-second frontend timeout, including time queued behind a per-explainer lock. This reflects the application's single-user local scope while still protecting accidental double submissions. If exact SHAP cannot meet those targets, stop and discuss the measured trade-off instead of silently changing algorithms.
