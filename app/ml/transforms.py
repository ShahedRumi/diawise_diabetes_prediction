"""Stable, importable transformer for loading the PIMA pipeline from joblib/Pickle.

Original notebook performs zero replacement and deterministic feature engineering before
fitting the median imputer. Keeping this code in a module permits .pkl deserialization.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

PIMA_INPUTS = [
    'Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness',
    'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age',
]
ZERO_AS_MISSING = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']


class PimaFeatureBuilder(BaseEstimator, TransformerMixin):
    """Convert eight raw PIMA inputs into the notebook's 22 engineered predictors."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            data = X.loc[:, PIMA_INPUTS].copy()
        else:
            data = pd.DataFrame(X, columns=PIMA_INPUTS)
        for col in PIMA_INPUTS:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        for col in ZERO_AS_MISSING:
            data[col] = data[col].replace(0, np.nan)

        data['Glucose_BMI'] = data['Glucose'] * data['BMI']
        data['Glucose_Age'] = data['Glucose'] * data['Age']
        data['BMI_Age'] = data['BMI'] * data['Age']
        data['Glucose_Pedigree'] = data['Glucose'] * data['DiabetesPedigreeFunction']
        data['BMI_Pedigree'] = data['BMI'] * data['DiabetesPedigreeFunction']
        data['Pregnancy_Age_Ratio'] = data['Pregnancies'] / data['Age']
        data['Glucose_BMI_Age'] = data['Glucose'] * data['BMI'] * data['Age']
        data['Insulin_Glucose_Ratio'] = data['Insulin'] / data['Glucose']
        data['Glucose_per_BMI'] = data['Glucose'] / data['BMI']
        data['BP_BMI'] = data['BloodPressure'] * data['BMI']
        data['Age_sq'] = data['Age'] ** 2
        data['BMI_sq'] = data['BMI'] ** 2
        data['Glucose_sq'] = data['Glucose'] ** 2
        data['Pregnancies_sq'] = data['Pregnancies'] ** 2
        return data.replace([np.inf, -np.inf], np.nan)
