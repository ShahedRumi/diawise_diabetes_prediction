"""Keep all user-facing project text consistently English."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BENGALI = re.compile(r'[\u0980-\u09ff]')
TEXT_SUFFIXES = {'.bat', '.css', '.html', '.js', '.md', '.ps1', '.py', '.sh', '.txt'}


def test_project_text_contains_no_bengali_characters():
    matches = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or '.venv' in path.parts:
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        if BENGALI.search(text):
            matches.append(str(path.relative_to(ROOT)))

    assert matches == []


def test_frontend_declares_english_and_quick_start_is_english_named():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')

    assert '<html lang="en">' in html
    assert (ROOT / 'START_HERE.txt').is_file()
    assert not (ROOT / 'START_HERE_BN.txt').exists()


def test_frontend_assets_use_a_release_version_to_replace_stale_language_bundles():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')

    assert '/static/css/style.css?v=20261118-ring' in html
    assert '/static/js/http.js?v=20261118-ring' in html
    assert '/static/js/main.js?v=20261118-ring' in html
