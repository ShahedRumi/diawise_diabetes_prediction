# Clean English UI Design

## Intent

Make DiaWise visibly English-only and substantially calmer without removing prediction inputs, model selection, probabilities, or SHAP explanations.

## Chosen approach

Use one restrained two-column workspace. Keep the form and result as the only major cards; remove the redundant form commentary box, per-result notes list, repeated disclaimer card, and decorative hero illustration. Keep required units beside fields and preserve one concise medical caveat inside the explanation. Collapse lower-impact SHAP factors behind a plain “Show all factors” control.

Prevent stale language from surviving releases by versioning frontend asset URLs and sending `Cache-Control: no-store` for the local HTML and static assets. Automated tests scan all user-facing text for Bengali characters and assert the removed UI fragments cannot return.

## Constraints

- Prediction and explanation behavior must not change.
- All visible copy must be English.
- Every SHAP factor remains available.
- The interface remains responsive and keyboard accessible.
