"""Real-template contracts for the investigation workspace."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parents[1]


def render(*, partial=False):
    from engine import i18n
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    return env.get_template('alerts.html.j2').render(
        board_date='2026-09-09', board_tz='America/New_York', generated_utc='2026-09-09 07:31',
        asof='2026-09-08', window_days=30, regime={}, cross_asset={}, risk_backdrop={},
        events={'items': [], 'next': None}, alerts=[], storylines=[], volume={},
        summary={'total': 0, 'actionable': 0, 'new_today': 0, 'major': 0, 'recurring': 0},
        coverage={'state': 'partial' if partial else 'complete', 'sources': [],
                  'backdrop_missing': partial, 'blocking': ['Bonds'] if partial else []},
        board_read={'stance': 'partial' if partial else 'mixed',
                    'score': None if partial else 25, 'one_liner': 'Partial tape read' if partial else 'Mixed observations'},
        explorer={'signals': [], 'sources': [], 'situations': [], 'history': [],
                  'total_signals': 0, 'history_total': 0, 'history_truncated': 0})


def test_workspace_has_four_real_tasks_and_an_evidence_inspector():
    html = render()
    assert 'id="alert-center"' in html
    for view in ('now', 'situations', 'signals', 'history'):
        assert f'data-view="{view}"' in html
    assert '<dialog' in html and 'id="ac-detail"' in html
    assert 'aria-labelledby="ac-detail-title"' in html
    assert 'id="ac-source"' in html and 'id="ac-search"' in html
    assert 'id="ac-data"' in html and 'application/json' in html


def test_empty_and_partial_are_different_states_and_do_not_claim_calm():
    empty = render()
    partial = render(partial=True)
    assert 'No observations in this window' in empty
    assert 'data-coverage-state="partial"' in partial
    assert 'Partial evidence' in partial
    assert 'Missing evidence is not a quiet market' in partial
    assert 'data-overall-score=' not in partial
    assert 'A quiet tape is a position' not in partial


def test_bilingual_controls_and_non_javascript_source_path_are_present():
    html = render()
    assert '全部信号' in html and '历史记录' in html and '相关变化' in html
    assert '<noscript>' in html and 'id="ac-noresults"' in html
    assert 'id="ac-reset"' in html and 'id="ac-show-more"' in html
    assert 'alerts_last_visit' not in html


def test_javascript_does_not_create_a_second_style_or_storage_plane():
    path = ROOT / 'templates/alert_center.js'
    assert path.exists()
    source = path.read_text()
    assert "createElement('style')" not in source and 'localStorage.setItem' not in source


def test_shared_html_never_inlines_account_specific_legacy_rows():
    from engine import i18n
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    private = dict(alert_id='PRIVATE_ID', source='watchlist', headline='PRIVATE_SENTINEL_TITLE',
                   source_label='Personal watchlist', board_date='2026-09-09')
    html = env.get_template('alerts.html.j2').render(
        alerts=[private], board_date='2026-09-09', generated_utc='2026-09-09 07:31',
        asof='2026-09-09', regime={}, cross_asset={}, events={'next':None},
        coverage={'state':'complete','sources':[]}, board_read={'score':None},
        summary={'total':1})
    assert 'PRIVATE_SENTINEL_TITLE' not in html
    assert 'PRIVATE_ID' not in html
