"""R26 consumer contract tests — display-only projection of forex/latest.json.

Covers lib.forex_r26_consumer only (no engine, no network, no rendered page):

1. Quote-correct direction from displayed pair letters: USDJPY -0.42% means
   the quote (JPY) moved down and JPY is stronger; EURUSD +0.28% means EUR
   is stronger. The payload's assessed/favored currency list is never used.
2. Null is not zero: missing/malformed/non-finite change produces no
   direction and no "0.00%"; a literal finite 0 is the only flat display.
3. Source as-of fails closed: unknown / malformed / future asof withholds
   every destination; malformed declared source values fail closed; absence
   of source is the explicit "unknown" status, not invented provenance.
4. Exactly four pair-tab availability statuses; missing rows invent nothing;
   degraded rows name every gap; missing evidence never becomes actionable.
5. Source-reported status strings pass through verbatim and are never turned
   into consumer bullishness/bearishness.
6. My-watches is NOT_ACTIVE with no persistence and no module state.
7. Determinism, loader behavior, and a smoke pass over the real canonical
   data/forex/latest.json when the tree materializes it (sparse trees skip).
8. Keyboard and localization claims are out of scope: this contract has no
   rendered consumer, so those behaviors are not asserted here.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from lib import forex_r26_consumer as r26  # noqa: E402

REF = date(2026, 10, 19)


def _payload(**overrides):
    base = {
        'asof': '2026-10-17',
        'regime': 'Risk-off haven bid',
        'risk': 'risk-off',
        'favored': ['USD', 'JPY', 'CHF'],
        'pairs': {
            'EURUSD': {'label': 'EUR/USD', 'quote': 1.1244, 'chg': 0.28,
                       'action': 'SHORT', 'score': -21.2, 'reliable': True,
                       'headline': 'src headline EUR', 'sub': 'src sub EUR'},
            'USDJPY': {'label': 'USD/JPY', 'quote': 157.987, 'chg': -0.42,
                       'action': 'FLAT', 'score': -7.6, 'reliable': True,
                       'headline': 'src headline JPY', 'sub': 'src sub JPY'},
            'DXY': {'label': 'DXY', 'quote': 101.78, 'chg': 1.5},
        },
        'stance': {'word_en': "Watch — don't chase", 'word_zh': '观望，别追',
                   'tone': 'calm'},
    }
    base.update(overrides)
    return base


def _view(payload, **kwargs):
    return r26.project_r26_consumer(payload, reference_date=REF, **kwargs)


def _tab(view, pair):
    for tab in view['destinations']['today']['pair_tabs']:
        if tab['pair'] == pair:
            return tab
    raise AssertionError(f'no tab for {pair}')


# ─────────────────────────────────────────────────────────────────────────────
# 1. Quote-correct direction from displayed pair letters
# ─────────────────────────────────────────────────────────────────────────────

def test_usdjpy_negative_chg_quote_down_jpy_stronger():
    """USDJPY -0.42%: the quote (JPY) moved down, so JPY stronger / USD weaker."""
    view = _view(_payload())
    tab = _tab(view, 'USDJPY')
    assert tab['chg_display'] == '-0.42%'
    assert tab['base_ccy'] == 'USD' and tab['quote_ccy'] == 'JPY'
    assert tab['direction']['base_ccy_state'] == 'weaker'
    assert tab['direction']['quote_ccy_state'] == 'stronger'
    assert tab['status'] == 'available'


def test_eurusd_positive_chg_base_eur_stronger():
    """EURUSD +0.28%: EUR is stronger / USD weaker."""
    view = _view(_payload())
    tab = _tab(view, 'EURUSD')
    assert tab['chg_display'] == '+0.28%'
    assert tab['direction']['base_ccy_state'] == 'stronger'
    assert tab['direction']['quote_ccy_state'] == 'weaker'
    assert tab['status'] == 'available'


def test_direction_ignores_meta_assessed_favored_currencies():
    """Direction comes from displayed letters + reported chg, never from favored."""
    view = _view(_payload(favored=['JPY'], risk='risk-on'))
    jpy_tab = _tab(view, 'USDJPY')
    assert view['destinations']['today']['favored'] == ['JPY']
    assert jpy_tab['direction']['quote_ccy_state'] == 'stronger'
    assert jpy_tab['direction']['base_ccy_state'] == 'weaker'
    eur_tab = _tab(view, 'EURUSD')
    assert eur_tab['direction']['base_ccy_state'] == 'stronger'


def test_dxy_index_claims_no_currency_direction():
    """Non six-letter keys are displayed rows, not currency-vs-currency pairs."""
    view = _view(_payload())
    tab = _tab(view, 'DXY')
    assert tab['pair_scope'] == 'non_pair'
    assert tab['base_ccy'] is None and tab['quote_ccy'] is None
    assert tab['direction'] is None
    assert tab['direction_reason'] == 'no_displayed_pair_letters'
    assert tab['status'] == 'degraded'
    assert 'reliability_unstated' in tab['gaps']


# ─────────────────────────────────────────────────────────────────────────────
# 2. Null is not zero; non-finite and malformed numbers are withheld
# ─────────────────────────────────────────────────────────────────────────────

def test_null_chg_is_not_zero():
    """A null change shows no direction and never displays 0.00%."""
    payload = _payload()
    payload['pairs']['USDJPY'] = dict(payload['pairs']['USDJPY'], chg=None)
    tab = _tab(_view(payload), 'USDJPY')
    assert tab['chg'] is None
    assert tab['chg_display'] is None
    assert tab['chg_display'] != '0.00%'
    assert tab['direction'] is None
    assert tab['direction_reason'] == 'chg_unavailable'
    assert tab['status'] == 'degraded'
    assert 'chg_missing' in tab['gaps']


def test_zero_chg_is_the_only_flat_display():
    """A literal finite 0 displays 0.00% with flat states on both sides."""
    payload = _payload()
    payload['pairs']['USDJPY'] = dict(payload['pairs']['USDJPY'], chg=0.0)
    tab = _tab(_view(payload), 'USDJPY')
    assert tab['chg_display'] == '0.00%'
    assert tab['direction']['base_ccy_state'] == 'flat'
    assert tab['direction']['quote_ccy_state'] == 'flat'
    assert tab['status'] == 'available'


@pytest.mark.parametrize('bad_chg', [float('nan'), float('inf'), float('-inf'), '-0.42', True])
def test_non_finite_and_malformed_chg_is_withheld(bad_chg):
    """NaN/inf/string/boolean changes are invalid evidence, never zero or flat."""
    payload = _payload()
    payload['pairs']['USDJPY'] = dict(payload['pairs']['USDJPY'], chg=bad_chg)
    tab = _tab(_view(payload), 'USDJPY')
    assert tab['chg'] is None
    assert tab['chg_display'] is None
    assert tab['direction'] is None
    assert 'chg_invalid' in tab['gaps']
    assert tab['status'] == 'degraded'


def test_missing_price_is_not_actionable():
    """A missing price degrades the tab and invents no 0 price."""
    payload = _payload()
    payload['pairs']['EURUSD'] = dict(payload['pairs']['EURUSD'], quote=None)
    tab = _tab(_view(payload), 'EURUSD')
    assert tab['price'] is None
    assert 'price_missing' in tab['gaps']
    assert tab['status'] == 'degraded'
    assert tab['direction']['base_ccy_state'] == 'stronger'


def test_source_unreliable_row_is_degraded_not_available():
    """Source reliability is evidence: false degrades the tab and names the gap."""
    payload = _payload()
    payload['pairs']['USDJPY'] = dict(payload['pairs']['USDJPY'], reliable=False)
    tab = _tab(_view(payload), 'USDJPY')
    assert tab['reliability'] == 'unreliable'
    assert 'source_marks_unreliable' in tab['gaps']
    assert tab['status'] == 'degraded'


# ─────────────────────────────────────────────────────────────────────────────
# 3. Source as-of and declared source fail closed
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('bad_asof,reason', [
    ('missing', 'asof_unknown'),
    (None, 'asof_unknown'),
    ('  ', 'asof_unknown'),
    ('unknown', 'asof_malformed'),
    ('17/10/2026', 'asof_malformed'),
    ('2026-13-45', 'asof_malformed'),
    (20261019, 'asof_malformed'),
    ('2026-10-20', 'asof_future'),
])
def test_bad_asof_fails_closed_everywhere(bad_asof, reason):
    """Unknown/malformed/future asof withholds gate, today, explore and tabs."""
    payload = _payload()
    if bad_asof == 'missing':
        del payload['asof']
    else:
        payload['asof'] = bad_asof
    view = _view(payload)
    assert view['gate']['status'] == 'withheld'
    assert view['gate']['reason'] == reason
    assert view['destinations']['today']['status'] == 'withheld'
    assert view['destinations']['today']['reason'] == reason
    assert view['destinations']['explore']['status'] == 'withheld'
    assert 'gate_withheld:' + reason in view['destinations']['today']['gaps']
    for tab in view['destinations']['today']['pair_tabs']:
        assert tab['status'] == 'withheld'
        assert tab['direction'] is None
        assert any(g.startswith('gate_withheld:') for g in tab['gaps'])
    assert view['destinations']['my_watches']['status'] == 'not_active'


def test_asof_at_reference_date_is_not_future():
    """An asof equal to the reference date is usable, not future."""
    payload = _payload(asof='2026-10-19')
    view = _view(payload)
    assert view['gate']['status'] == 'ok'
    assert view['destinations']['today']['status'] == 'ok'


def test_declared_source_rules():
    """Declared source passes through; malformed declared source fails closed."""
    ok = _view(_payload(source='canonical-forex-builder:v1'))
    assert ok['gate']['source_status'] == 'declared'
    assert ok['gate']['source_label'] == 'canonical-forex-builder:v1'
    view_absent = _view(_payload())
    assert 'source' not in _payload()
    assert view_absent['gate']['source_status'] == 'unknown'
    assert view_absent['gate']['source_label'] is None
    for bad in (None, '', '   ', 123, ['x']):
        payload = _payload()
        payload['source'] = bad
        view = _view(payload)
        assert view['gate']['status'] == 'withheld'
        assert view['gate']['reason'] == 'source_malformed'
        assert view['destinations']['today']['status'] == 'withheld'


# ─────────────────────────────────────────────────────────────────────────────
# 4. Four statuses; missing rows invent nothing; universe rules
# ─────────────────────────────────────────────────────────────────────────────

def test_exactly_four_tab_statuses_across_cases():
    """Every projected tab status is one of the four contract statuses."""
    views = [_view(_payload()), _view(_payload(favored=[])),
             _view(_payload(), universe=['EURUSD', 'EURGBP']),
             _view(_payload(asof='2027-01-01'))]
    for view in views:
        for tab in view['destinations']['today']['pair_tabs']:
            assert tab['status'] in r26.TAB_STATUSES
    statuses = {tab['status'] for view in views
                for tab in view['destinations']['today']['pair_tabs']}
    assert statuses <= set(r26.TAB_STATUSES)
    assert len(r26.TAB_STATUSES) == 4


def test_missing_pair_row_invents_nothing():
    """A requested pair without a payload row is a missing tab, never a fabricated row."""
    view = _view(_payload(), universe=['EURUSD', 'EURGBP'])
    tab = _tab(view, 'EURGBP')
    assert tab['status'] == 'missing'
    assert tab['gaps'] == ['row_missing']
    assert tab['price'] is None and tab['chg'] is None
    assert tab['chg_display'] is None and tab['direction'] is None
    assert tab['label'] is None
    assert _tab(view, 'EURUSD')['status'] == 'available'


def test_row_not_a_mapping_is_degraded_with_named_gap():
    """A malformed row is degraded evidence, not a crash or a fabricated row."""
    payload = _payload()
    payload['pairs']['USDJPY'] = 'not-a-row'
    tab = _tab(_view(payload), 'USDJPY')
    assert tab['status'] == 'degraded'
    assert tab['gaps'] == ['row_malformed']
    assert tab['direction'] is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Source status passes through verbatim; no invented bullishness
# ─────────────────────────────────────────────────────────────────────────────

def test_source_action_and_score_pass_through_verbatim():
    """The consumer echoes source status fields; it adds no sentiment field."""
    view = _view(_payload())
    tab = _tab(view, 'EURUSD')
    assert tab['source_action'] == 'SHORT'
    assert tab['source_score'] == -21.2
    assert tab['source_headline'] == 'src headline EUR'
    for key in tab:
        assert 'bull' not in key and 'bear' not in key and 'sentiment' not in key
    assert set(tab['direction'].values()) & set(r26.DIRECTION_STATES)
    assert tab['direction']['basis'] == 'displayed_pair_letters_and_reported_chg'


def test_today_stance_and_regime_pass_through_en_zh_verbatim():
    """Raw EN/ZH source strings pass through untouched; no translation claims."""
    payload = _payload()
    today = _view(payload)['destinations']['today']
    assert today['stance'] == payload['stance']
    assert today['stance']['word_zh'] == '观望，别追'
    assert today['regime'] == 'Risk-off haven bid'
    assert today['risk'] == 'risk-off'
    assert today['favored_basis'] == ('source_assessed_currencies_display_only'
                                      '_not_used_for_pair_direction')


# ─────────────────────────────────────────────────────────────────────────────
# 6. My-watches: NOT_ACTIVE, no persistence, no module state
# ─────────────────────────────────────────────────────────────────────────────

def test_my_watches_not_active_constant():
    """The watches destination is inactive, empty, and persistence-free."""
    view = _view(_payload())
    watches = view['destinations']['my_watches']
    assert watches == r26.watches_view()
    assert watches['status'] == 'not_active'
    assert watches['active'] is False
    assert watches['persistence'] == 'none'
    assert watches['watches'] == []


def test_add_watch_refuses_and_stores_nothing():
    """add_watch refuses identically every call; nothing is retained anywhere."""
    first = r26.add_watch('USDJPY')
    second = r26.add_watch('EURUSD', note='x')
    assert first == second == {'status': 'not_active', 'stored': False,
                               'reason': 'watches_not_active_in_r26'}
    view_a = _view(_payload())
    view_b = _view(_payload())
    assert view_a['destinations']['my_watches']['watches'] == []
    assert view_a == view_b


# ─────────────────────────────────────────────────────────────────────────────
# 7. Determinism, loader, and canonical smoke
# ─────────────────────────────────────────────────────────────────────────────

def test_projection_is_deterministic():
    """Same payload and reference date produce identical views."""
    assert _view(_payload()) == _view(_payload())


def test_destinations_and_gate_shape():
    """The view exposes exactly the three destinations plus the gate."""
    view = _view(_payload())
    assert set(view['destinations']) == set(r26.DESTINATIONS)
    assert view['gate']['status'] == 'ok'
    assert view['gate']['asof'] == '2026-10-17'
    assert view['contract_version'] == r26.CONTRACT_VERSION


def test_loader_roundtrip_and_errors(tmp_path):
    """load_latest_payload reads canonical JSON and raises on missing/malformed."""
    path = tmp_path / 'latest.json'
    path.write_text(json.dumps(_payload()), encoding='utf-8')
    payload = r26.load_latest_payload(str(path))
    assert _view(payload)['gate']['status'] == 'ok'
    with pytest.raises(FileNotFoundError):
        r26.load_latest_payload(str(tmp_path / 'absent.json'))
    bad = tmp_path / 'bad.json'
    bad.write_text('{"asof": ', encoding='utf-8')
    with pytest.raises(ValueError):
        r26.load_latest_payload(str(bad))


def test_scope_exclusions_hold_over_real_projection():
    """No forecast/rank/sizing/alert/persistence surface exists in the view."""
    view = _view(_payload())

    banned = ('forecast', 'probability', 'prob', 'rank',
              'sizing', 'entry', 'alert', 'queue', 'store')

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                assert not any(word in lowered for word in banned), \
                    f'unexpected key: {key}'
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(view)


def test_canonical_latest_json_smoke():
    """Smoke over the real canonical file when this tree materializes it.

    Sparse session trees omit data/; the skip is explicit rather than a silent
    pass, and the real build tree runs this against the actual publication.
    """
    path = _REPO_ROOT / 'data' / 'forex' / 'latest.json'
    if not path.exists():
        pytest.skip('sparse tree: data/forex/latest.json not materialized')
    payload = r26.load_latest_payload(str(path))
    view = r26.project_r26_consumer(payload, reference_date=date.today())
    assert view['gate']['status'] == 'ok'
    pairs = payload['pairs']
    tabs = view['destinations']['today']['pair_tabs']
    assert [t['pair'] for t in tabs] == list(pairs)
    assert all(t['status'] in r26.TAB_STATUSES for t in tabs)
    usdjpy = next(t for t in tabs if t['pair'] == 'USDJPY')
    assert usdjpy['status'] == 'available'
    chg = pairs['USDJPY']['chg']
    expected = ('flat', 'flat') if chg == 0 else (
        ('stronger', 'weaker') if chg > 0 else ('weaker', 'stronger'))
    assert (usdjpy['direction']['base_ccy_state'],
            usdjpy['direction']['quote_ccy_state']) == expected
    assert view['destinations']['my_watches']['status'] == 'not_active'
