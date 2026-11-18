"""API regression tests."""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from app import main


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def test_status_and_static_page(client):
    assert client.get('/').status_code == 200
    assert client.get('/static/js/main.js').status_code == 200
    assert client.get('/api/health').json()['models_loaded'] == 3


def test_pima(client):
    response = client.post('/api/predict/pima', json={
        'Pregnancies': 2, 'Glucose': 125, 'BloodPressure': 72,
        'SkinThickness': 25, 'Insulin': 88, 'BMI': 28.4,
        'DiabetesPedigreeFunction': .42, 'Age': 38,
    })
    assert response.status_code == 200
    assert 0 <= response.json()['probability'] <= 1
    assert response.json()['threshold'] == .48


def test_general_both_modes(client):
    payload = {
        'gender': 'Female', 'age': 47, 'hypertension': 0,
        'heart_disease': 0, 'smoking_history': 'never', 'bmi': 29.7,
    }
    assert client.post('/api/predict/general', json={**payload, 'mode':'nonlab'}).json()['features_used'] == 6
    full = client.post('/api/predict/general', json={**payload, 'mode':'full', 'HbA1c_level': 6.3, 'blood_glucose_level': 140})
    assert full.status_code == 200
    assert full.json()['features_used'] == 8
    assert client.post('/api/predict/general', json={**payload, 'mode':'full'}).status_code == 422


def test_food_known_lookup_and_custom_normalization(client):
    known = client.post('/api/predict/food', json={'food_name':'mango'})
    assert known.status_code == 200
    assert known.json()['source'] == 'dataset_lookup'
    assert known.json()['probability'] is None
    new_food = client.post('/api/predict/food', json={
        'food_name':'Homemade Snack', 'serving_size_g':200,
        'carbohydrate_g':60,'sugar_g':12,'fiber_g':8,'fat_g':6,'glycemic_index':55
    })
    assert new_food.status_code == 200
    obj = new_food.json()
    assert obj['source']=='xgboost_inference'
    assert obj['per_100g']['Carbohydrate (g)']==30.0
    assert obj['per_100g']['Glycemic Index']==55.0


def test_food_invalid_serving(client):
    r=client.post('/api/predict/food',json={'food_name':'Unknown','serving_size_g':0,'carbohydrate_g':20,'sugar_g':4,'fiber_g':2,'fat_g':2,'glycemic_index':50})
    assert r.status_code==422


def _clear_artifact_state(monkeypatch):
    cache_clear = getattr(main.get_artifacts, 'cache_clear', None)
    if cache_clear:
        cache_clear()
    monkeypatch.setattr(main, '_artifacts', None, raising=False)
    monkeypatch.setattr(main, '_artifact_error', None, raising=False)


def test_lifespan_preloads_artifacts_once(monkeypatch):
    original = main.get_artifacts()
    calls = 0

    def fake_load():
        nonlocal calls
        calls += 1
        return original

    _clear_artifact_state(monkeypatch)
    monkeypatch.setattr(main, 'load_artifacts', fake_load, raising=False)

    with TestClient(main.app) as test_client:
        assert calls == 1
        assert test_client.get('/api/health').status_code == 200
        assert calls == 1


def test_health_reports_artifact_load_failure_as_503(monkeypatch):
    def fail_load():
        raise ValueError('corrupt artifact')

    _clear_artifact_state(monkeypatch)
    monkeypatch.setattr(main, 'load_artifacts', fail_load, raising=False)

    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        response = test_client.get('/api/health')

    assert response.status_code == 503
    assert 'corrupt artifact' in response.json()['detail']


def test_concurrent_load_uses_one_artifact_instance(monkeypatch):
    original = main.get_artifacts()
    calls = 0

    def slow_load():
        nonlocal calls
        calls += 1
        time.sleep(0.05)
        return original

    _clear_artifact_state(monkeypatch)
    monkeypatch.setattr(main, 'load_artifacts', slow_load, raising=False)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: main.get_artifacts(), range(4)))

    assert calls == 1
    assert all(result is results[0] for result in results)


def test_readable_but_unusable_artifact_prevents_readiness(monkeypatch):
    class Predictor:
        def predict_proba(self, _frame):
            return [[0.5, 0.5]]

    loaded = iter([Predictor(), {'full': Predictor()}, Predictor()])
    monkeypatch.setattr(main.joblib, 'load', lambda _path: next(loaded))

    with pytest.raises(ValueError, match=r'general_diabetes_model\.pkl.*nonlab'):
        main.load_artifacts()
