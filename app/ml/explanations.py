"""Exact, input-level SHAP explanations for DiaWise model outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable, Literal

import numpy as np
import pandas as pd
import shap

from app.ml.constants import (
    FOOD_FEATURES,
    GENERAL_INPUTS,
    GENDER_MAP,
    NONLAB_INPUTS,
    PIMA_INPUTS,
    SMOKING_MAP,
)


_CAVEAT = (
    "SHAP describes this model's behavior relative to its reference data. "
    "It does not establish medical causation, a diagnosis, or personal clinical risk."
)

_LABELS = {
    'Pregnancies': 'Pregnancies',
    'Glucose': 'Glucose',
    'BloodPressure': 'Blood pressure',
    'SkinThickness': 'Skin thickness',
    'Insulin': 'Insulin',
    'BMI': 'BMI',
    'DiabetesPedigreeFunction': 'Diabetes pedigree function',
    'Age': 'Age',
    'gender': 'Gender',
    'age': 'Age',
    'hypertension': 'Hypertension',
    'heart_disease': 'Heart disease',
    'smoking_history': 'Smoking history',
    'bmi': 'BMI',
    'HbA1c_level': 'HbA1c',
    'blood_glucose_level': 'Blood glucose',
    'Carbohydrate (g)': 'Carbohydrate',
    'Sugar (g)': 'Sugar',
    'Fiber (g)': 'Fiber',
    'Fat (g)': 'Fat',
    'Glycemic Index': 'Glycemic index',
}


@dataclass
class _ExplanationContext:
    explainer: object
    predict: Callable[[pd.DataFrame], np.ndarray]
    feature_keys: list[str]
    target: str
    background: pd.DataFrame
    lock: Lock = field(default_factory=Lock)


def _sample(frame: pd.DataFrame, size: int) -> pd.DataFrame:
    if size < 1:
        raise ValueError('SHAP background size must be at least 1.')
    return frame.sample(n=min(size, len(frame)), random_state=42).reset_index(drop=True)


def _positive_probability(model, features: list[str]) -> Callable[[pd.DataFrame], np.ndarray]:
    def predict(values) -> np.ndarray:
        frame = pd.DataFrame(np.asarray(values, dtype=float), columns=features)
        return np.asarray(model.predict_proba(frame)[:, 1], dtype=float)

    return predict


def _make_context(model, background: pd.DataFrame, features: list[str], target: str) -> _ExplanationContext:
    predict = _positive_probability(model, features)
    explainer = shap.ExactExplainer(predict, background, feature_names=features)
    return _ExplanationContext(explainer, predict, features, target, background)


class ExplanationService:
    """Owns deterministic exact SHAP explainers and serializes their execution."""

    def __init__(self, pima_model, general_bundle, food_model, contexts: dict[str, _ExplanationContext]):
        self.pima_model = pima_model
        self.general_bundle = general_bundle
        self.food_model = food_model
        self._contexts = contexts

    @classmethod
    def build(
        cls,
        pima_model,
        general_bundle,
        food_model,
        data_dir: Path,
        *,
        background_size: int = 32,
    ) -> 'ExplanationService':
        data_dir = Path(data_dir)

        pima_data = pd.read_csv(data_dir / 'pima_original.csv')[PIMA_INPUTS].astype(float)

        general_data = pd.read_csv(data_dir / 'general_diabetes_original.csv').drop_duplicates().copy()
        general_data['gender'] = general_data['gender'].map(GENDER_MAP)
        general_data['smoking_history'] = general_data['smoking_history'].map(SMOKING_MAP)
        if general_data[GENERAL_INPUTS].isna().any().any():
            raise ValueError('General-model SHAP reference data contains unsupported categories or missing values.')
        general_data = general_data[GENERAL_INPUTS].astype(float)

        food_data = pd.read_csv(data_dir / 'food_100g.csv', encoding='utf-8-sig')[FOOD_FEATURES].astype(float)

        pima_background = _sample(pima_data, background_size)
        general_background = _sample(general_data, background_size)
        food_background = _sample(food_data, background_size)

        contexts = {
            'pima': _make_context(
                pima_model,
                pima_background,
                PIMA_INPUTS,
                'Probability of the diabetes-positive classification',
            ),
            'general_full': _make_context(
                general_bundle['full'],
                general_background[GENERAL_INPUTS],
                GENERAL_INPUTS,
                'Probability of the diabetes-positive classification',
            ),
            'general_nonlab': _make_context(
                general_bundle['nonlab'],
                general_background[NONLAB_INPUTS],
                NONLAB_INPUTS,
                'Probability of the diabetes-positive classification',
            ),
            'food': _make_context(
                food_model,
                food_background,
                FOOD_FEATURES,
                'Probability of the recommended-food classification',
            ),
        }
        return cls(pima_model, general_bundle, food_model, contexts)

    def _explain(self, context_key: str, row: pd.DataFrame, display_values: dict[str, str]) -> dict:
        context = self._contexts[context_key]
        frame = row.loc[:, context.feature_keys].astype(float)
        if len(frame) != 1:
            raise ValueError('Exactly one row is required for a prediction explanation.')

        with context.lock:
            result = context.explainer(frame)
            output = float(context.predict(frame)[0])

        values = np.asarray(result.values, dtype=float).reshape(-1)
        base_values = np.asarray(result.base_values, dtype=float).reshape(-1)
        if len(values) != len(context.feature_keys) or len(base_values) < 1:
            raise RuntimeError('SHAP returned an unexpected explanation shape.')
        base = float(base_values[0])
        if not np.isfinite(base) or not np.isfinite(output) or not np.isfinite(values).all():
            raise RuntimeError('SHAP returned a non-finite explanation value.')
        if not np.isclose(base + float(values.sum()), output, rtol=0.0, atol=1e-5):
            raise RuntimeError('SHAP additivity validation failed; no explanation was returned.')

        features = []
        for key, contribution in zip(context.feature_keys, values, strict=True):
            value = float(contribution)
            direction = 'neutral'
            if value > 1e-12:
                direction = 'toward_positive'
            elif value < -1e-12:
                direction = 'away_from_positive'
            features.append({
                'key': key,
                'label': _LABELS[key],
                'display_value': str(display_values.get(key, frame.iloc[0][key])),
                'contribution': round(value, 10),
                'direction': direction,
            })
        features.sort(key=lambda item: abs(item['contribution']), reverse=True)

        return {
            'kind': 'shap',
            'method': 'Exact SHAP',
            'target': context.target,
            'base_probability': round(base, 10),
            'output_probability': round(output, 10),
            'features': features,
            'caveat': _CAVEAT,
        }

    def explain_pima(self, row: pd.DataFrame, display_values: dict[str, str]) -> dict:
        return self._explain('pima', row, display_values)

    def explain_general(
        self,
        mode: Literal['full', 'nonlab'],
        row: pd.DataFrame,
        display_values: dict[str, str],
    ) -> dict:
        return self._explain(f'general_{mode}', row, display_values)

    def explain_food(self, row: pd.DataFrame, display_values: dict[str, str]) -> dict:
        return self._explain('food', row, display_values)

    def warm_up(self) -> None:
        """Compute one explanation per model before the API reports readiness."""
        for key, context in self._contexts.items():
            row = context.background.iloc[[0]].copy()
            display = {name: f'{float(row.iloc[0][name]):g}' for name in context.feature_keys}
            self._explain(key, row, display)
