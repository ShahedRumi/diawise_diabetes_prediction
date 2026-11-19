"""Static contract tests for the understandable explanation interface."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_result_panel_contains_accessible_explanation_region():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')

    assert 'id="explanation-panel"' in html
    assert 'Why the model predicted this' in html
    assert 'id="explanation-features"' in html
    assert 'aria-labelledby="explanation-heading"' in html


def test_browser_renders_baseline_output_directions_and_catalog_provenance():
    javascript = (ROOT / 'static' / 'js' / 'main.js').read_text(encoding='utf-8')

    for phrase in (
        'Baseline', 'Model output', 'percentage points',
        'toward the positive class', 'away from the positive class',
        'catalog_provenance',
    ):
        assert phrase in javascript


def test_result_ui_uses_one_clean_explanation_region_without_repeated_commentary_cards():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    javascript = (ROOT / 'static' / 'js' / 'main.js').read_text(encoding='utf-8')

    for removed_id in ('form-help', 'result-extras', 'result-disclaimer'):
        assert f'id="{removed_id}"' not in html
    assert 'class="info-card"' not in html
    assert "result.notes" not in javascript
    assert 'Show all factors' in javascript
    assert 'Show fewer factors' in javascript


def test_result_summary_has_probability_ring_and_polarity_caption():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    css = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')

    assert 'id="result-ring"' in html
    assert 'id="result-polarity"' in html
    assert 'conic-gradient' in css
    assert '--result-progress' in css
