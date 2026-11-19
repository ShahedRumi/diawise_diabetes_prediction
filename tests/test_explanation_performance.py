"""Interactive-latency guardrails for local Exact SHAP explanations."""
from concurrent.futures import ThreadPoolExecutor
import statistics
import time

import pandas as pd

from app.main import load_artifacts


def _timed(call, repeats=3):
    durations = []
    for _ in range(repeats):
        started = time.perf_counter()
        call()
        durations.append(time.perf_counter() - started)
    return durations


def test_warm_explanations_remain_interactive():
    *_, service = load_artifacts()
    cases = {
        'pima': lambda: service.explain_pima(pd.DataFrame([[
            2, 125, 72, 25, 88, 28.4, .42, 38,
        ]], columns=service._contexts['pima'].feature_keys), {}),
        'general_full': lambda: service.explain_general('full', pd.DataFrame([[
            0, 47, 0, 0, 4, 29.7, 6.3, 140,
        ]], columns=service._contexts['general_full'].feature_keys), {}),
        'general_nonlab': lambda: service.explain_general('nonlab', pd.DataFrame([[
            0, 47, 0, 0, 4, 29.7,
        ]], columns=service._contexts['general_nonlab'].feature_keys), {}),
        'food': lambda: service.explain_food(pd.DataFrame([[
            30, 6, 4, 3, 55,
        ]], columns=service._contexts['food'].feature_keys), {}),
    }

    for name, call in cases.items():
        durations = _timed(call)
        print(f'{name}: median={statistics.median(durations):.3f}s max={max(durations):.3f}s')
        assert statistics.median(durations) < 2
        assert max(durations) < 10


def test_two_same_model_explanations_finish_inside_frontend_timeout():
    *_, service = load_artifacts()
    row = pd.DataFrame([[
        2, 125, 72, 25, 88, 28.4, .42, 38,
    ]], columns=service._contexts['pima'].feature_keys)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: service.explain_pima(row, {}), range(2)))
    duration = time.perf_counter() - started

    print(f'two concurrent PIMA explanations: total={duration:.3f}s')
    assert duration < 10
