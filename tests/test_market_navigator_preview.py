from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_study_is_not_a_claimed_paper_or_production_artifact():
    html = (ROOT/'research/market_navigator/preview.html').read_text()
    assert 'ILLUSTRATIVE' in html and 'NOT LIVE' in html
    assert 'Not applied to Paper' in html
    assert 'disabled aria-describedby="save-note"' in html
    assert '../../templates/theme.css' in html
    assert 'meta name="robots" content="noindex,nofollow"' in html


def test_study_has_no_network_or_account_effects():
    js = (ROOT/'research/market_navigator/preview.js').read_text()
    for token in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'eval(', 'innerHTML'):
        assert token not in js
    assert 'showModal()' in js
    assert 'Missing study translation' in js


def test_shared_tokens_and_accessible_states():
    css = (ROOT/'research/market_navigator/preview.css').read_text()
    assert ':root{' not in css and ':root {' not in css
    assert 'prefers-reduced-motion' in css and ':focus-visible' in css
    assert 'border-left:' not in css
    html = (ROOT/'research/market_navigator/preview.html').read_text()
    assert 'aria-pressed' in html and 'role="status"' in html and '<dialog' in html
