"""Current-reading integrity; missing evidence must not masquerade as calm."""
from pathlib import Path
import copy
import re
import pandas as pd
import pytest
from jinja2 import Environment
from engine import risk_radar as rr

ROOT = Path(__file__).resolve().parents[1]

def _signals():
    idx = pd.bdate_range('2026-08-03', periods=32)
    return pd.DataFrame({'growth_defensives': .3, 'growth_cyc_def': .3,
                         'nh_contraction': [0.9] * 31 + [float('nan')],
                         'ai_breadth_divergence': 0.0}, index=idx)

def test_unavailable_reading_preserves_legacy_score_but_discloses_absence():
    out = rr.compute(sigs=_signals(), gate={'met': False})
    row = next(s for s in out['scares'] if s['scare'] == 'internals')
    assert row['score'] == 0.0  # immutable legacy definition, not a reweight
    assert row['n_legs_resolved'] == 0
    assert row.get('reading_state') == 'UNAVAILABLE'
    assert row.get('display_score') is None
    assert row.get('display_band') is None

def _ladder(row):
    src = (ROOT / 'templates/dashboard.html.j2').read_text()
    src = src.split('{# — 6. Risk Ladder', 1)[1].split('{# MX2-SENTIMENT-START #}', 1)[0]
    src = '{# — 6. Risk Ladder' + src
    env = Environment(autoescape=True)
    env.globals.update(t=lambda en, zh='': en + ' / ' + zh,
                       rkc_scare_glyph=lambda x: '', rkc_scare_fam=lambda x: '')
    return env.from_string(src).render(latest={'risk_radar': {'scares': [row]}})

@pytest.mark.parametrize('coverage', [
    {'n_legs_resolved': 0, 'weight_coverage': 0.0},
    {'reading_state': 'UNAVAILABLE', 'display_score': None, 'display_band': None},
])
def test_existing_ladder_never_prints_calm_for_unavailable_reading(coverage):
    row = dict(scare='internals', label_en='Breadth internals', label_zh='内部广度',
               score=0.0, band='calm', **coverage)
    html = _ladder(row)
    assert 'Unavailable' in html and '不可用' in html
    assert '>0.0<' not in html
    assert re.search(r'class="l-en">calm<', html) is None
    assert 'sc-bar-fill' not in html

@pytest.mark.parametrize('coverage', [{}, {'n_legs_resolved': 1, 'weight_coverage': 1.0}])
def test_real_zero_reading_stays_calm(coverage):
    html = _ladder(dict(scare='internals', label_en='Breadth', label_zh='广度',
                        score=0.0, band='calm', **coverage))
    assert '>0.0<' in html and 'Unavailable' not in html

def test_loss_of_eligible_input_is_not_fading_risk():
    out = rr.compute(sigs=_signals(), gate={'met': False})
    assert out['deescalation']['receding_scare'] != 'internals'
    assert 'internals' not in {r['key'] for r in out['deescalation']['deescalated']}
    assert 'internals' not in {r['key'] for r in (out.get('trajectory') or {}).get('drivers', {}).get('faded', [])}


@pytest.mark.parametrize('display_leg_last', [float('nan'), 0.0])
def test_domain_exit_cannot_reuse_yesterdays_warm_or_fading_read(display_leg_last):
    sigs = _signals()
    sigs['nh_contraction'] = [0.9] * 20 + [0.6] * 11 + [float('nan')]
    sigs['ai_breadth_divergence'] = [float('nan')] * 31 + [display_leg_last]
    out = rr.compute(sigs=sigs, gate={'met': False})
    drivers = (out.get('trajectory') or {}).get('drivers', {})
    for field in ('faded', 'warm'):
        assert 'internals' not in {entry['key'] for entry in drivers.get(field, [])}
    assert 'internals' not in {entry['key'] for entry in out['deescalation']['deescalated']}
    assert out['deescalation']['receding_scare'] != 'internals'
