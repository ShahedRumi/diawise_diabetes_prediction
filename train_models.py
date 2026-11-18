"""Train the three saved project artifacts from the original research datasets.

Execution: python train_models.py
Outputs exactly three .pkl files in models/ plus reproducible held-out metrics.
The general-diabetes artifact intentionally contains TWO independently fitted estimators
(full eight-feature and six-feature non-lab), because they are the two variants of Model 2.
"""

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTENC
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from app.ml.constants import (FOOD_FEATURES, GENERAL_INPUTS, GENDER_MAP,
                              NONLAB_INPUTS, PIMA_INPUTS, SMOKING_MAP)
from app.ml.transforms import PimaFeatureBuilder

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUT = ROOT / 'models'
OUT.mkdir(exist_ok=True)
SEED = 42


def report(y, scores, threshold=0.5):
    labels = (np.asarray(scores) >= threshold).astype(int)
    return {
        'accuracy': round(float(accuracy_score(y, labels)), 6),
        'precision': round(float(precision_score(y, labels, zero_division=0)), 6),
        'recall': round(float(recall_score(y, labels, zero_division=0)), 6),
        'f1': round(float(f1_score(y, labels, zero_division=0)), 6),
        'roc_auc': round(float(roc_auc_score(y, scores)), 6),
        'confusion_matrix': confusion_matrix(y, labels, labels=[0, 1]).tolist(),
        'test_size': int(len(y)),
        'threshold': threshold,
    }


def train_pima():
    print('[1/3] PIMA: preprocessing + 22 features + tuned Random Forest', flush=True)
    df = pd.read_csv(DATA / 'pima_original.csv')
    if len(df) < 100:
        raise ValueError('PIMA dataset has too few records to train reliably')
    x = df[PIMA_INPUTS]
    y = df['Outcome'].astype(int)
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=.2, stratify=y, random_state=SEED)
    pipeline = Pipeline([
        ('features', PimaFeatureBuilder()),
        ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
        ('model', RandomForestClassifier(
            n_estimators=200, min_samples_split=10, min_samples_leaf=6,
            max_features='sqrt', max_depth=15,
            class_weight='balanced_subsample', bootstrap=False,
            random_state=SEED, n_jobs=-1
        )),
    ])
    pipeline.fit(xtr, ytr)
    p = pipeline.predict_proba(xte)[:, 1]
    result = report(yte, p, threshold=.48)
    joblib.dump(pipeline, OUT / 'pima_model.pkl', compress=3)
    print('PIMA result:', result, flush=True)
    return result


def train_general():
    print('[2/3] General: deduplication, categorical encoding, SMOTENC + LightGBM (full + non-lab)', flush=True)
    df = pd.read_csv(DATA / 'general_diabetes_original.csv').drop_duplicates().reset_index(drop=True)
    if len(df) < 1000:
        raise ValueError('General diabetes dataset has too few records')
    if df[GENERAL_INPUTS].isna().any().any():
        raise RuntimeError('Unexpected missing data in general dataset')
    df['gender'] = df['gender'].map(GENDER_MAP)
    df['smoking_history'] = df['smoking_history'].map(SMOKING_MAP)
    if df[GENERAL_INPUTS].isna().any().any():
        raise RuntimeError('Unrecognized categories detected')
    xtr, xte, ytr, yte = train_test_split(
        df[GENERAL_INPUTS], df['diabetes'].astype(int),
        test_size=.2, stratify=df['diabetes'].astype(int), random_state=SEED,
    )
    fitted = {}
    metrics = {}
    for mode, features in (('full', GENERAL_INPUTS), ('nonlab', NONLAB_INPUTS)):
        print('   training', mode, 'on', len(xtr), 'original train records', flush=True)
        cols = ['gender', 'hypertension', 'heart_disease', 'smoking_history']
        indices = [features.index(name) for name in cols]
        sampler = SMOTENC(categorical_features=indices, random_state=SEED)
        x_res, y_res = sampler.fit_resample(xtr[features], ytr)
        estimator = LGBMClassifier(
            n_estimators=150, learning_rate=.05, random_state=SEED,
            n_jobs=-1, verbosity=-1,
        )
        estimator.fit(x_res, y_res)
        scores = estimator.predict_proba(xte[features])[:, 1]
        fitted[mode] = estimator
        metrics[mode] = report(yte, scores)
        print('  ', mode, metrics[mode], flush=True)
    bundle = {
        'full': fitted['full'],
        'nonlab': fitted['nonlab'],
        'full_features': GENERAL_INPUTS,
        'nonlab_features': NONLAB_INPUTS,
        'gender_map': GENDER_MAP,
        'smoking_map': SMOKING_MAP,
        'threshold': .5,
    }
    joblib.dump(bundle, OUT / 'general_diabetes_model.pkl', compress=3)
    return metrics


def train_food():
    print('[3/3] Food: author-created 718-food dataset, calibrated XGBoost', flush=True)
    df = pd.read_csv(DATA / 'food_100g.csv', encoding='utf-8-sig')
    if len(df) < 40 or not (df['Serving Size (g)'] == 100).all():
        raise ValueError('Food dataset must contain at least 40 foods and have 100 g serving rows')
    if not df['Score'].isin([0, 1]).all():
        raise ValueError('Food dataset Score must contain only class labels 0 and 1')
    x, y = df[FOOD_FEATURES], df['Score'].astype(int)
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=.2, stratify=y, random_state=SEED)
    ratio = float((ytr == 0).sum() / (ytr == 1).sum())
    pipeline = Pipeline([
        ('fill', SimpleImputer(strategy='median')),
        ('model', XGBClassifier(
            n_estimators=150, max_depth=3, learning_rate=.05,
            subsample=.9, colsample_bytree=.9,
            scale_pos_weight=ratio, objective='binary:logistic',
            eval_metric='logloss', random_state=SEED, n_jobs=1,
        )),
    ])
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='X does not have valid feature names.*')
        calibrator = CalibratedClassifierCV(estimator=pipeline, method='sigmoid', cv=3)
        calibrator.fit(xtr, ytr)
    scores = calibrator.predict_proba(xte)[:, 1]
    result = report(yte, scores)
    joblib.dump(calibrator, OUT / 'food_model.pkl', compress=3)
    print('Food result:', result, flush=True)
    return result


def main():
    result = {
        'trained_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'random_state': SEED,
        'dataset_provenance': {
            'pima': 'Kaggle PIMA Indians Diabetes dataset (user-provided CSV)',
            'general': 'Kaggle Diabetes Prediction dataset (user-provided CSV)',
            'food': 'Primarily author-created and curated food suitability dataset (user-provided workbook)',
        },
        'model_1_pima': train_pima(),
        'model_2_general': train_general(),
        'model_3_food': train_food(),
        'research_caveats': [
            'Prediction is not a medical diagnosis.',
            'Food suitability labels are author-curated, not an individualized dietary prescription.',
            'The food workbook audit includes estimated, unverified nutrition values.',
            'These are held-out results after retraining with pinned implementations; published thesis values may vary by package version.',
        ],
    }
    (OUT / 'metrics.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\nSaved: pima_model.pkl, general_diabetes_model.pkl, food_model.pkl, metrics.json', flush=True)


if __name__ == '__main__':
    main()
