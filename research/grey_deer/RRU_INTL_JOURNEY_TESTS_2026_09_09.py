"""Complete international view/adapter/template tests; synthetic, no production IO."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
from functools import lru_cache
import hashlib
import json
import unittest
from unittest.mock import patch
from jinja2 import BaseLoader, Environment, TemplateNotFound
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from scripts import build_international_macro as builder
from engine import international_macro_dashboard as dashboard

TEMPLATE = 'templates/international_macro.html.j2'
BUILDER = 'scripts/build_international_macro.py'
VIEW = 'engine/international_macro_dashboard.py'
LABELS = {'JP': ('Japan', '日本'), 'KR': ('South Korea', '韩国'),
          'EZ': ('Euro Area', '欧元区'), 'GB': ('United Kingdom', '英国'),
          'IN': ('India', '印度')}
READ_SOURCES = {}

class PinnedLoader(BaseLoader):
    def get_source(self, environment, template):
        path = 'templates/' + template
        raw = a.RENDER_SOURCES.get(path) or pinned(path)
        READ_SOURCES[path] = hashlib.sha256(raw.encode()).hexdigest()
        return raw, path, lambda: True

@lru_cache(maxsize=80)
def pinned(path):
    return a.committed(path)

def snapshot(profile, case):
    sub = a.fixture(profile)
    if case == 'partial': next(iter(sub.values())).iloc[-1] = a.np.nan
    if case == 'unavailable':
        for values in sub.values(): values.iloc[-1] = a.np.nan
    return a.compute(profile, sub)

def record(cc, radar):
    en, zh = LABELS[cc]
    return dict(cc=cc, name=en, name_zh=zh, flag='', date='2026-09-09',
        quad='Q1', quad_name='Goldilocks', growth_score=.35, inflation_score=.1,
        confidence=.7, liquidity='neutral', recession_score=15, recession_band='low',
        macro=dict(cpi_yoy=2., gdp_yoy=2.1, unemployment=4., yield_10y=3.,
                   policy_rate=2.5, curve=.5, fx=1., drawdown=-2., realvol=12.),
        macro_asof={k:'2026-08-31' for k in ('cpi_yoy','gdp','unemployment','yield_10y')},
        risk_radar=radar)

def adapt(rec):
    with patch.object(a.market_state, '_rr_scorecard_track', return_value=None):
        return builder._radar_display(rec)

def render(rec, force_direct=False):
    view = dashboard.build_country_view(rec, today=date(2026,9,9))
    dashboard.validate_view(view)
    if force_direct:
        with patch.object(a.market_state, '_rr_scorecard_track', return_value=None):
            rd = a.market_state._radar_to_rd(rec['risk_radar'])
    else:
        rd = adapt(rec)
    env = Environment(loader=PinnedLoader(), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    return view, rd, env.get_template('international_macro.html.j2').render(D=view,RADAR=rd)

class AdapterJourney(unittest.TestCase):
    pass

def adapter_case(profile, case):
    def test(self):
        snap = snapshot(profile, case)
        rec = dict(cc=profile.key.upper(), risk_radar=snap)
        before = deepcopy(rec)
        rd = adapt(rec)
        self.assertIsNotNone(rd, 'Explicit assessment disappears in outer adapter')
        self.assertEqual(rd['composition'], snap['composition'])
        self.assertIsNone(rd['dd21'])
        self.assertFalse(rd['can_force'])
        self.assertEqual(rec, before)
    return test

for profile in a.radar.PROFILES.values():
    for case in ('complete','partial','unavailable'):
        setattr(AdapterJourney, 'test_'+profile.key+'_'+case, adapter_case(profile,case))

class CompletePage(unittest.TestCase):
    pass

def page_case(cc, case):
    def test(self):
        snap = snapshot(a.radar.PROFILES[cc.lower()],case)
        view,rd,html = render(record(cc,snap), force_direct=True)
        self.assertEqual(html.count('class="rrx '),1)
        self.assertNotIn('Calibrated risk monitor',html)
        self.assertNotIn('Calibrated risk receipt',html)
        self.assertNotIn("Odds measured on this market's own history",html)
        self.assertNotIn('current calibrated-risk state',html)
        self.assertIn('Forecast not available',html)
        self.assertIn('Input coverage',html)
        self.assertIsNone(view['risk']['h21'])
        self.assertFalse(view['risk']['calibrated'])
        self.assertEqual(view['risk'].get('composition'),snap['composition'])
        if case=='unavailable': self.assertIn('Reading unavailable',html)
    return test

for cc in dashboard.REGIONS:
    for case in ('complete','partial','unavailable'):
        setattr(CompletePage,'test_'+cc+'_'+case,page_case(cc,case))

class ViewIntegrity(unittest.TestCase):
    def test_modern_caution_does_not_adjust_measured_score(self):
        rec = record('JP', snapshot(a.radar.PROFILES['jp'],'complete'))
        rec['risk_radar']['state']='caution'
        measured = dashboard.decision_score({**rec,'risk_radar':{}})
        self.assertEqual(dashboard.decision_score(rec),measured)

    def test_legacy_caution_keeps_original_adjustment(self):
        rec=record('JP',dict(state='caution',drawdown_prob=dict(h21=.42)))
        score,parts=dashboard.decision_score(rec)
        self.assertEqual(parts['risk_state'],-4.)
        view,rd,html=render(rec)
        self.assertEqual(view['risk']['h21'],.42)
        self.assertTrue(view['risk']['calibrated'])
        self.assertIn('Calibrated risk monitor',html)
        self.assertIsNotNone(rd)
        self.assertNotIn('composition',view['risk'])

    def test_explicit_modern_metadata_never_advertises_raw_old_odds(self):
        for q in (None,{},[],True,{'method':'future'}):
            with self.subTest(metadata=q):
                rec=record('JP',dict(state='caution',composition=q,drawdown_prob=dict(h21=.42)))
                saved=deepcopy(rec)
                view=dashboard.build_country_view(rec,today=date(2026,9,9))
                self.assertIsNone(view['risk']['h21'])
                self.assertFalse(view['risk']['calibrated'])
                self.assertEqual(view['decision']['parts']['risk_state'],0.)
                self.assertEqual(rec,saved)

    def test_composition_is_published_without_aliasing(self):
        rec=record('JP',snapshot(a.radar.PROFILES['jp'],'partial'))
        view=dashboard.build_country_view(rec,today=date(2026,9,9))
        self.assertEqual(view['risk'].get('composition'),rec['risk_radar']['composition'])
        view['risk']['composition']['groups'][0]['missing'].append('changed-copy')
        self.assertNotIn('changed-copy',rec['risk_radar']['composition']['groups'][0]['missing'])

    def test_legacy_absent_snapshot_remains_absent(self):
        self.assertIsNone(adapt(dict(cc='JP')))
        self.assertIsNone(adapt(dict(cc='JP',risk_radar={'state':'calm'})))

    def test_real_adapter_reaches_complete_page(self):
        rec=record('JP',snapshot(a.radar.PROFILES['jp'],'complete'))
        view,rd,html=render(rec)
        self.assertIsNotNone(rd)
        self.assertIn('Input coverage',html)
        self.assertNotIn('Calibrated risk monitor',html)
        json.dumps(view,allow_nan=False)

if __name__=='__main__':
    paths=set(candidate.bundle)|{BUILDER,VIEW,TEMPLATE}
    def state(p):
        f=a.ROOT/p
        return f.read_bytes() if f.exists() else None
    before={p:state(p) for p in paths}
    a.apply_bundle(candidate.bundle)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)
                           for c in (AdapterJourney,CompletePage,ViewIntegrity))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    unchanged=all(state(p)==v for p,v in before.items())
    print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        source_unchanged=unchanged,synthetic_only=True,full_template=True,production=False,
        template_sources=READ_SOURCES)),flush=True)
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
