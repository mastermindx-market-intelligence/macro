"""One non-authoritative interpretation shared by settled and live risk views."""
from copy import deepcopy
from importlib.util import find_spec
import pytest


def view(ms, envelope=None):
    assert find_spec('lib.risk_presentation') is not None, 'missing shared risk presentation'
    from lib.risk_presentation import market_read
    return market_read(ms, envelope)


def sample():
    return {'asof': '2026-09-15', 'market': 'us', 'score': 61, 'raw_score': 61,
            'verdict': 'RISK_ON', 'label_en': 'Risk-on', 'label_zh': '风险偏好',
            'color': 'green', 'components': [
                {'key': 'trend', 'score': 55, 'tone': 'warn'},
                {'key': 'breadth', 'score': 14, 'tone': 'bad'}],
            'radar': {'is_warning': True, 'can_force': False}}


def envelope():
    return {'schema': 'mastermind.risk_envelope/v1', 'market': 'US',
            'revision': 'settled', 'source_session': '2026-09-15',
            'measured_state': {'as_of': '2026-09-15', 'verdict': 'RISK_ON', 'usable': True},
            'hazard_summary': {'stage': 'FRAGILE'},
            'coherence': {'state': 'CONTRADICTORY'}, 'data_state': 'FRESH',
            'policy_summary': {'policy_count': 0, 'posture': 'NORMAL'}}


def test_current_contradiction_leads_without_changing_any_input():
    ms, re = sample(), envelope()
    original = deepcopy((ms, re))
    out = view(ms, re)
    assert (ms, re) == original
    assert out['label_en'] == 'Fragile'
    assert out['measured_verdict'] == 'RISK_ON'
    assert out['score'] == 61 and out['qualified'] is True
    assert out['hazard_stage'] == 'FRAGILE'
    assert out['context_session'] == '2026-09-15'
    assert 'breadth' in out['headline_en'].lower()
    assert out['authority'] == 'presentation_only'
    assert not any(k in out for k in ('may_size', 'gross', 'ceiling', 'probability'))


@pytest.mark.parametrize('change', [
    {'source_session': '2026-09-14'}, {'market': 'HK'},
    {'data_state': 'STALE'}, {'schema': 'unknown'},
])
def test_mismatched_context_cannot_claim_current_hazard(change):
    re = envelope(); re.update(change)
    out = view(sample(), re)
    assert out['hazard_stage'] is None
    assert out['context_session'] is None
    assert out['label_en'] == 'Uneven support'


def test_no_envelope_still_cannot_claim_breadth_confirms():
    out = view(sample())
    assert out['qualified'] and out['label_en'] == 'Uneven support'
    assert 'line up' not in out['headline_en']
    assert 'Trend-following supported' not in out['subline_en']


@pytest.mark.parametrize('ms', [None, {}, [], {'verdict': 'RISK_ON', 'components': None}])
def test_absence_is_not_broad_confirmation(ms):
    out = view(ms)
    assert 'line up' not in out['headline_en']
    assert out['hazard_stage'] is None


def test_risk_off_cannot_be_softened_by_fragile_context():
    ms = sample(); ms.update(verdict='RISK_OFF', score=30, label_en='Risk-off')
    assert view(ms, envelope())['label_en'] == 'Risk-off'


def test_known_good_participation_remains_supportive():
    ms = sample(); ms['radar'] = {}
    for c in ms['components']: c.update(score=80, tone='good')
    out = view(ms)
    assert out['label_en'] == 'Risk-on'
    assert out['qualified'] is False


def test_unknown_policy_count_never_supplies_market_support():
    re = envelope(); re['policy_summary'] = {}
    assert view(sample(), re)['label_en'] == 'Fragile'


def test_boolean_scores_are_not_numbers():
    ms = sample(); ms['score'] = True
    assert view(ms)['score'] is None


def test_live_verdict_block_consumes_the_shared_formatter():
    from scripts.build_risk_state import _verdict_block
    ms = sample(); old = deepcopy(ms)
    out = _verdict_block(ms)
    assert out.get('presentation', {}).get('label_en') == 'Uneven support'
    assert out['score'] == 61 and out['verdict'] == 'RISK_ON'
    assert ms == old


def test_server_hero_uses_the_same_presentation():
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    root = Path(__file__).resolve().parents[1]
    assert (root / 'templates/_market_read.html.j2').exists(), 'missing shared hero presentation'
    ms = sample(); ms['presentation'] = view(ms, envelope())
    env = Environment(loader=FileSystemLoader(root / 'templates'), autoescape=True)
    html = env.from_string('{% import "_market_read.html.j2" as mr %}'
                          '{{ mr.word(ms) }}{{ mr.subline(ms) }}{{ mr.headline(ms) }}').render(ms=ms)
    assert 'Fragile' in html and '脆弱' in html
    assert 'line up' not in html and 'Trend-following supported' not in html
    assert 'Measured blend' in html


def test_legacy_engine_risk_on_cannot_claim_breadth_agrees():
    from engine.market_state import _HEADLINES
    assert 'line up' not in _HEADLINES['RISK_ON'][0]
    assert 'adding on strength is supported' not in _HEADLINES['RISK_ON'][0]


@pytest.mark.parametrize('degraded', [
    {'stale_inputs': ['recession_risk']},
    {'degraded_components': ['liquidity']},
    {'freshness': {'stale': True}},
    {'freshness': {'any_input_stale': True}},
])
def test_incomplete_evidence_cannot_claim_broad_confirmation(degraded):
    ms = sample(); ms['radar'] = {}
    for row in ms['components']:
        row.update(score=80, tone='good')
    ms.update(degraded)
    out = view(ms)
    assert out['qualified'] is True
    assert out['label_en'] == 'Confirmation incomplete'
    assert 'inputs' in out['headline_en'].lower()
    assert out['score'] == ms['score'] and out['measured_verdict'] == ms['verdict']


@pytest.mark.parametrize('source', ['radar_ceiling', 'hard_force', 'verdict_cap'])
def test_a_capped_display_is_not_labelled_as_the_measured_blend(source):
    ms = sample()
    ms.update(verdict='MIXED', score=50, raw_score=61, capped=True, score_source=source)
    out = view(ms)
    assert out['score'] == 50 and out['measured_verdict'] == 'MIXED'
    assert 'Capped' in out['subline_en']
    assert '61' in out['subline_en'] and '封顶' in out['subline_zh']


def test_cap_with_missing_original_blend_does_not_invent_a_measurement():
    ms = sample()
    ms.update(verdict='MIXED', score=50, raw_score=None, capped=True)
    out = view(ms)
    assert 'Capped' in out['subline_en']
    assert 'unavailable' in out['subline_en']
    assert '61' not in out['subline_en']


def test_incomplete_auxiliary_inputs_do_not_erase_observed_breadth_damage():
    ms = sample(); ms['stale_inputs'] = ['recession_risk']
    original = deepcopy(ms)
    out = view(ms)
    assert out['label_en'] == 'Confirmation incomplete'
    assert 'breadth is weak' in out['headline_en'].lower()
    assert 'inputs' in out['headline_en'].lower()
    assert '广度偏弱' in out['headline_zh']
    assert out['score'] == 61 and out['breadth_score'] == 14
    assert ms == original


@pytest.mark.parametrize('source', ['radar_ceiling', 'hard_force', 'verdict_cap'])
def test_capped_headline_does_not_claim_the_original_blend_is_risk_off(source):
    ms = sample()
    ms.update(verdict='RISK_OFF', score=30, raw_score=61, capped=True, score_source=source)
    original = deepcopy(ms)
    out = view(ms)
    assert out['label_en'] == 'Risk-off' and out['score'] == 30
    assert 'measured blend indicates risk-off' not in out['headline_en'].lower()
    assert '实测综合读数显示避险状态' not in out['headline_zh']
    assert 'constraint' in out['headline_en'].lower() and '约束' in out['headline_zh']
    assert '61' in out['subline_en'] and ms == original


@pytest.mark.parametrize('capped', [False, True])
def test_server_accessible_gauge_carries_qualification_and_provenance(capped):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    root = Path(__file__).resolve().parents[1]
    ms = sample()
    if capped:
        ms.update(verdict='MIXED', score=50, raw_score=61, capped=True,
                  score_source='radar_ceiling')
    ms['presentation'] = view(ms, None if capped else envelope())
    env = Environment(loader=FileSystemLoader(root/'templates'), autoescape=True)
    text = env.from_string('{% import "_market_read.html.j2" as mr %}{{ mr.aria(ms) }}').render(ms=ms)
    assert 'Displayed score' in text and str(ms['score']) in text
    assert ms['presentation']['label_en'] in text
    assert ms['presentation']['label_zh'] in text
    if capped:
        assert 'Capped' in text and '61' in text
    else:
        assert 'Fragile' in text
