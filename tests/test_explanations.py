"""Exact input-level SHAP explanation service tests."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml.constants import FOOD_FEATURES, GENERAL_INPUTS, NONLAB_INPUTS, PIMA_INPUTS
from app.ml.explanations import ExplanationService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def explanation_service():
    pima = joblib.load(ROOT / 'models' / 'pima_model.pkl')
    general = joblib.load(ROOT / 'models' / 'general_diabetes_model.pkl')
    food = joblib.load(ROOT / 'models' / 'food_model.pkl')
    return ExplanationService.build(pima, general, food, ROOT / 'data', background_size=4)


@pytest.fixture
def pima_row():
    return pd.DataFrame([{
        'Pregnancies': 2, 'Glucose': 125, 'BloodPressure': 72,
        'SkinThickness': 25, 'Insulin': 88, 'BMI': 28.4,
        'DiabetesPedigreeFunction': .42, 'Age': 38,
    }], columns=PIMA_INPUTS)


def _assert_additive(explanation):
    total = explanation['base_probability'] + sum(item['contribution'] for item in explanation['features'])
    assert total == pytest.approx(explanation['output_probability'], abs=1e-5)


def test_pima_explanation_is_additive_and_has_eight_raw_features(explanation_service, pima_row):
    display = {name: str(pima_row.iloc[0][name]) for name in PIMA_INPUTS}

    explanation = explanation_service.explain_pima(pima_row, display)

    assert explanation['kind'] == 'shap'
    assert explanation['method'] == 'Exact SHAP'
    assert len(explanation['features']) == 8
    assert {item['key'] for item in explanation['features']} == set(PIMA_INPUTS)
    _assert_additive(explanation)


def test_general_modes_preserve_display_categories_and_feature_counts(explanation_service):
    full = pd.DataFrame([{
        'gender': 0, 'age': 47, 'hypertension': 0, 'heart_disease': 0,
        'smoking_history': 4, 'bmi': 29.7, 'HbA1c_level': 6.3,
        'blood_glucose_level': 140,
    }], columns=GENERAL_INPUTS)
    display = {name: str(full.iloc[0][name]) for name in GENERAL_INPUTS}
    display.update({'gender': 'Female', 'smoking_history': 'Never'})

    full_explanation = explanation_service.explain_general('full', full, display)
    nonlab_explanation = explanation_service.explain_general('nonlab', full[NONLAB_INPUTS], display)

    assert len(full_explanation['features']) == 8
    assert len(nonlab_explanation['features']) == 6
    assert next(item for item in full_explanation['features'] if item['key'] == 'gender')['display_value'] == 'Female'
    assert next(item for item in full_explanation['features'] if item['key'] == 'smoking_history')['display_value'] == 'Never'
    _assert_additive(full_explanation)
    _assert_additive(nonlab_explanation)


def test_food_explains_calibrated_probability_on_normalized_features(explanation_service):
    row = pd.DataFrame([{
        'Carbohydrate (g)': 30.0, 'Sugar (g)': 6.0, 'Fiber (g)': 4.0,
        'Fat (g)': 3.0, 'Glycemic Index': 55.0,
    }], columns=FOOD_FEATURES)
    display = {name: f'{row.iloc[0][name]:g}' for name in FOOD_FEATURES}

    explanation = explanation_service.explain_food(row, display)

    expected = explanation_service.food_model.predict_proba(row)[0, 1]
    assert len(explanation['features']) == 5
    assert explanation['output_probability'] == pytest.approx(expected, abs=1e-6)
    _assert_additive(explanation)


def test_features_are_finite_deterministic_and_sorted_by_absolute_effect(explanation_service, pima_row):
    display = {name: str(pima_row.iloc[0][name]) for name in PIMA_INPUTS}

    first = explanation_service.explain_pima(pima_row, display)
    second = explanation_service.explain_pima(pima_row, display)

    assert first == second
    contributions = [item['contribution'] for item in first['features']]
    assert all(np.isfinite(contributions))
    assert [abs(value) for value in contributions] == sorted((abs(value) for value in contributions), reverse=True)


def test_explainer_calls_are_lock_protected(explanation_service, pima_row, monkeypatch):
    context = explanation_service._contexts['pima']
    active = 0
    maximum = 0
    guard = threading.Lock()

    class SlowExplainer:
        def __call__(self, frame):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.03)
            with guard:
                active -= 1
            return SimpleNamespace(values=np.zeros((1, len(frame.columns))), base_values=np.array([.5]))

    monkeypatch.setattr(context, 'explainer', SlowExplainer())
    monkeypatch.setattr(context, 'predict', lambda frame: np.full(len(frame), .5))
    display = {name: str(pima_row.iloc[0][name]) for name in PIMA_INPUTS}

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: explanation_service.explain_pima(pima_row, display), range(2)))

    assert maximum == 1


def test_additivity_failure_raises_without_returning_an_explanation(explanation_service, pima_row, monkeypatch):
    context = explanation_service._contexts['pima']
    monkeypatch.setattr(
        context,
        'explainer',
        lambda frame: SimpleNamespace(values=np.zeros((1, len(frame.columns))), base_values=np.array([0.])),
    )
    monkeypatch.setattr(context, 'predict', lambda frame: np.full(len(frame), .5))
    display = {name: str(pima_row.iloc[0][name]) for name in PIMA_INPUTS}

    with pytest.raises(RuntimeError, match='additivity'):
        explanation_service.explain_pima(pima_row, display)
