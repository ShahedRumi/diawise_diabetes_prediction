"""Local-only diabetes lifestyle research demonstration API (FastAPI)."""
from __future__ import annotations

import json
import re
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ml.constants import (
    FOOD_FEATURES, GENERAL_INPUTS, GENDER_MAP, NONLAB_INPUTS,
    PIMA_INPUTS, SMOKING_MAP,
)
from app.ml.explanations import ExplanationService

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'models'
DATA = ROOT / 'data'

_artifacts = None
_artifact_error: str | None = None
_artifact_lock = Lock()


def load_artifacts():
    paths = [MODELS / name for name in
             ('pima_model.pkl', 'general_diabetes_model.pkl', 'food_model.pkl')]
    if not all(path.is_file() for path in paths):
        missing = [path.name for path in paths if not path.is_file()]
        raise FileNotFoundError('Missing model artifacts: ' + ', '.join(missing) + '. Run python train_models.py.')
    # SECURITY: Only load trusted, locally trained .pkl files.
    loaded = []
    for path in paths:
        try:
            loaded.append(joblib.load(path))
        except Exception as exc:
            raise RuntimeError(
                f'Could not load {path.name}: {exc}. Run python train_models.py to recreate the artifacts.'
            ) from exc
    pima, general, food = loaded
    if not callable(getattr(pima, 'predict_proba', None)):
        raise ValueError('pima_model.pkl is not a compatible probability estimator. Run python train_models.py.')
    if not isinstance(general, dict):
        raise ValueError('general_diabetes_model.pkl must contain the full and nonlab estimators. Run python train_models.py.')
    missing_modes = [mode for mode in ('full', 'nonlab') if mode not in general]
    if missing_modes:
        raise ValueError(
            'general_diabetes_model.pkl is missing mode(s): '
            + ', '.join(missing_modes)
            + '. Run python train_models.py.'
        )
    for mode in ('full', 'nonlab'):
        if not callable(getattr(general[mode], 'predict_proba', None)):
            raise ValueError(
                f'general_diabetes_model.pkl mode {mode} is not a compatible probability estimator. '
                'Run python train_models.py.'
            )
    if not callable(getattr(food, 'predict_proba', None)):
        raise ValueError('food_model.pkl is not a compatible probability estimator. Run python train_models.py.')
    catalog = pd.read_csv(DATA / 'food_100g.csv', encoding='utf-8-sig')
    lookup = {}
    for _, row in catalog.iterrows():
        key = normalize_name(str(row['Food Name']))
        lookup[key] = {
            'name': str(row['Food Name']),
            'category': str(row['Category']),
            'score': int(row['Score']),
            'nutrients': {col: round(float(row[col]), 3) for col in FOOD_FEATURES},
        }
    metrics = json.loads((MODELS / 'metrics.json').read_text(encoding='utf-8'))
    explanations = ExplanationService.build(pima, general, food, DATA)
    explanations.warm_up()
    return pima, general, food, lookup, metrics, explanations


def _initialize_artifacts() -> None:
    global _artifacts, _artifact_error
    if _artifacts is not None or _artifact_error is not None:
        return
    with _artifact_lock:
        if _artifacts is not None or _artifact_error is not None:
            return
        try:
            _artifacts = load_artifacts()
        except Exception as exc:  # Artifact formats can fail in several dependency-specific ways.
            _artifact_error = f'{type(exc).__name__}: {exc}'


def artifact_status() -> dict[str, str | bool]:
    return {'ready': _artifacts is not None, 'error': _artifact_error or ''}


def get_artifacts():
    _initialize_artifacts()
    if _artifacts is None:
        raise HTTPException(
            status_code=503,
            detail='Model artifacts are unavailable. ' + (_artifact_error or 'Loading has not completed.'),
        )
    return _artifacts


@asynccontextmanager
async def lifespan(_: FastAPI):
    _initialize_artifacts()
    yield


app = FastAPI(
    title='DiaWise — Diabetes & Nutrition Research',
    version='1.0.0',
    description='Locally hosted demonstration of three thesis research models. Not medical advice.',
    docs_url='/api/docs',
    redoc_url=None,
    lifespan=lifespan,
)


@app.middleware('http')
async def prevent_stale_local_frontend(request, call_next):
    response = await call_next(request)
    if request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')


def normalize_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()


def _explain_or_503(explain, *args) -> dict:
    try:
        return explain(*args)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail='The prediction explanation could not be computed safely. Please retry or restart DiaWise.',
        ) from exc


class PimaRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    Pregnancies: int = Field(ge=0, le=25)
    Glucose: float = Field(ge=0, le=400)
    BloodPressure: float = Field(ge=0, le=250)
    SkinThickness: float = Field(ge=0, le=110)
    Insulin: float = Field(ge=0, le=1000)
    BMI: float = Field(ge=0, le=100)
    DiabetesPedigreeFunction: float = Field(ge=0, le=5)
    Age: float = Field(ge=1, le=120)


class GeneralRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    mode: Literal['full', 'nonlab'] = 'nonlab'
    gender: Literal['Female', 'Male', 'Other']
    age: float = Field(ge=0, le=120)
    hypertension: Literal[0, 1]
    heart_disease: Literal[0, 1]
    smoking_history: Literal['No Info', 'current', 'ever', 'former', 'never', 'not current']
    bmi: float = Field(gt=0, le=100)
    HbA1c_level: float | None = Field(default=None, ge=0, le=20)
    blood_glucose_level: float | None = Field(default=None, ge=0, le=700)

    @model_validator(mode='after')
    def check_laboratory_features(self):
        if self.mode == 'full' and (self.HbA1c_level is None or self.blood_glucose_level is None):
            raise ValueError('HbA1c and blood glucose are required in full mode.')
        return self


class FoodRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    food_name: str = Field(default='', max_length=120)
    serving_size_g: float | None = Field(default=None, gt=0, le=10000)
    carbohydrate_g: float | None = Field(default=None, ge=0, le=10000)
    sugar_g: float | None = Field(default=None, ge=0, le=10000)
    fiber_g: float | None = Field(default=None, ge=0, le=10000)
    fat_g: float | None = Field(default=None, ge=0, le=10000)
    glycemic_index: float | None = Field(default=None, ge=0, le=100)


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(ROOT / 'templates' / 'index.html')


@app.get('/api/health')
def health():
    status = artifact_status()
    if not status['ready']:
        raise HTTPException(
            status_code=503,
            detail='Model artifacts are unavailable. ' + (status['error'] or 'Loading has not completed.'),
        )
    _, _, _, catalog, _, _ = get_artifacts()
    return {'status': 'ok', 'models_loaded': 3, 'food_catalog_size': len(catalog)}


@app.get('/api/models')
def model_information():
    _, _, _, _, meta, _ = get_artifacts()
    return {
        'data_provenance': meta['dataset_provenance'],
        'metrics': {
            'pima': meta['model_1_pima'],
            'general_full': meta['model_2_general']['full'],
            'general_nonlab': meta['model_2_general']['nonlab'],
            'food': meta['model_3_food'],
        },
        'trained_at_utc': meta['trained_at_utc'],
        'disclaimer': 'Research prototype. Neither a medical diagnosis nor individualized nutritional advice.',
    }


@app.post('/api/predict/pima')
def predict_pima(payload: PimaRequest):
    model, _, _, _, _, explanations = get_artifacts()
    df = pd.DataFrame([{col: getattr(payload, col) for col in PIMA_INPUTS}], columns=PIMA_INPUTS)
    p = float(model.predict_proba(df)[0, 1])
    positive = p >= .48
    flags = []
    if payload.Age < 21:
        flags.append('The source PIMA dataset focuses on adult women aged 21 and above; extrapolation is unreliable.')
    if any(getattr(payload, c) == 0 for c in ('Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI')):
        flags.append('One or more entered zero values were treated as missing and imputed from training data.')
    display = {
        'Pregnancies': f'{payload.Pregnancies:g}',
        'Glucose': f'{payload.Glucose:g} mg/dL',
        'BloodPressure': f'{payload.BloodPressure:g} mmHg',
        'SkinThickness': f'{payload.SkinThickness:g} mm',
        'Insulin': f'{payload.Insulin:g} µU/mL',
        'BMI': f'{payload.BMI:g} kg/m²',
        'DiabetesPedigreeFunction': f'{payload.DiabetesPedigreeFunction:g}',
        'Age': f'{payload.Age:g} years',
    }
    explanation = _explain_or_503(explanations.explain_pima, df, display)
    return {
        'model': 'pima', 'classification': int(positive),
        'probability': round(p, 6), 'threshold': .48,
        'label': 'Diabetes-positive classification' if positive else 'Diabetes-negative classification',
        'source': 'trained_random_forest',
        'notes': flags,
        'explanation': explanation,
        'disclaimer': 'Research-only classification. It does not confirm or rule out diabetes. Consult a qualified clinician for diagnosis.',
    }


@app.post('/api/predict/general')
def predict_general(payload: GeneralRequest):
    _, model_set, _, _, _, explanations = get_artifacts()
    features = GENERAL_INPUTS if payload.mode == 'full' else NONLAB_INPUTS
    row = {
        'gender': GENDER_MAP[payload.gender],
        'age': payload.age,
        'hypertension': payload.hypertension,
        'heart_disease': payload.heart_disease,
        'smoking_history': SMOKING_MAP[payload.smoking_history],
        'bmi': payload.bmi,
        'HbA1c_level': payload.HbA1c_level,
        'blood_glucose_level': payload.blood_glucose_level,
    }
    df = pd.DataFrame([{name: row[name] for name in features}], columns=features)
    estimator = model_set[payload.mode]
    p = float(estimator.predict_proba(df)[0, 1])
    positive = p >= .5
    flags = []
    if payload.mode == 'nonlab':
        flags.append('This 6-feature model has low diabetic precision on held-out research data; positive classifications may often be false alarms.')
    if payload.age > 80:
        flags.append('Age is outside the main source-data range; prediction reliability is unknown.')
    display = {
        'gender': payload.gender,
        'age': f'{payload.age:g} years',
        'hypertension': 'Yes' if payload.hypertension else 'No',
        'heart_disease': 'Yes' if payload.heart_disease else 'No',
        'smoking_history': payload.smoking_history.replace('_', ' ').title(),
        'bmi': f'{payload.bmi:g} kg/m²',
        'HbA1c_level': f'{payload.HbA1c_level:g}%' if payload.HbA1c_level is not None else 'Not provided',
        'blood_glucose_level': (
            f'{payload.blood_glucose_level:g} mg/dL'
            if payload.blood_glucose_level is not None else 'Not provided'
        ),
    }
    explanation = _explain_or_503(explanations.explain_general, payload.mode, df, display)
    return {
        'model': 'general', 'mode': payload.mode,
        'features_used': len(features),
        'classification': int(positive), 'probability': round(p, 6),
        'threshold': .5,
        'label': 'Diabetes-positive classification' if positive else 'Diabetes-negative classification',
        'source': 'trained_smote_lightgbm',
        'notes': flags,
        'explanation': explanation,
        'disclaimer': 'Research-only classification. Laboratory-free output must not be used as a diagnostic replacement.',
    }


@app.get('/api/foods')
def search_foods(query: str = Query(default='', min_length=0, max_length=80)):
    _, _, _, catalog, _, _ = get_artifacts()
    needle = normalize_name(query)
    if len(needle) < 2:
        return {'matches': []}
    matches = sorted(
        (item for key, item in catalog.items() if needle in key),
        key=lambda item: (not normalize_name(item['name']).startswith(needle), len(item['name'])),
    )[:10]
    return {'matches': [{'name': item['name'], 'category': item['category']} for item in matches]}


@app.post('/api/predict/food')
def predict_food(payload: FoodRequest):
    _, _, model, catalog, _, explanations = get_artifacts()
    food_key = normalize_name(payload.food_name)
    known = catalog.get(food_key) if food_key else None
    if known:
        return {
            'model': 'food', 'source': 'dataset_lookup',
            'label': 'Recommended in dataset' if known['score'] == 1 else 'Not recommended in dataset',
            'classification': known['score'], 'probability': None,
            'food_name': known['name'], 'category': known['category'],
            'per_100g': known['nutrients'], 'notes': [
                'Exact match returned the author-curated dataset label; no ML model inference was performed.',
            ],
            'explanation': {
                'kind': 'catalog_provenance',
                'method': 'Direct dataset lookup',
                'target': 'Author-curated food suitability label',
                'summary': (
                    'This result is the stored label for an exact food-catalog match. '
                    'No predictive model was used, so there are no model feature contributions.'
                ),
                'caveat': (
                    'The catalog label is a research annotation, not an individualized dietary prescription.'
                ),
            },
            'disclaimer': 'Curated research labels are not a clinical dietary prescription. Portions and personal health context matter.',
        }
    needed = ('serving_size_g', 'carbohydrate_g', 'sugar_g', 'fiber_g', 'fat_g', 'glycemic_index')
    absent = [name for name in needed if getattr(payload, name) is None]
    if absent:
        raise HTTPException(status_code=422, detail='Unknown food requires nutrition inputs: ' + ', '.join(absent))
    normalized = {
        'Carbohydrate (g)': payload.carbohydrate_g * 100 / payload.serving_size_g,
        'Sugar (g)': payload.sugar_g * 100 / payload.serving_size_g,
        'Fiber (g)': payload.fiber_g * 100 / payload.serving_size_g,
        'Fat (g)': payload.fat_g * 100 / payload.serving_size_g,
        'Glycemic Index': payload.glycemic_index,  # GI is an index, NOT a mass scaled by serving size.
    }
    if any(normalized[k] > 110 for k in FOOD_FEATURES[:4]):
        raise HTTPException(status_code=422, detail='Per-100g nutrient amounts appear implausible; check serving size and units.')
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='X does not have valid feature names.*')
        score = float(model.predict_proba(pd.DataFrame([normalized], columns=FOOD_FEATURES))[0, 1])
    frame = pd.DataFrame([normalized], columns=FOOD_FEATURES)
    display = {
        key: (f'{value:g}' if key == 'Glycemic Index' else f'{value:g} g per 100 g')
        for key, value in normalized.items()
    }
    explanation = _explain_or_503(explanations.explain_food, frame, display)
    if score >= .75:
        category, label = 1, 'Likely recommended under training labels'
    elif score <= .25:
        category, label = 0, 'Likely not recommended under training labels'
    else:
        category, label = None, 'Uncertain — review nutritional details'
    return {
        'model': 'food', 'source': 'xgboost_inference',
        'food_name': payload.food_name.strip() or 'Custom food',
        'classification': category, 'probability': round(score, 6), 'thresholds': [0.25, 0.75],
        'label': label, 'per_100g': {key: round(float(value), 3) for key, value in normalized.items()},
        'notes': [
            'Carbohydrate, sugar, fiber and fat were normalized to a 100 g basis.',
            'Glycemic index was not normalized because it is not a nutrient mass.',
            'The dataset includes estimated nutrition values not independently verified.',
        ],
        'explanation': explanation,
        'disclaimer': 'Research-prototype food classification, not an individualized meal plan or clinical dietary recommendation.',
    }
