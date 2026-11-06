"""Actual downstream render/override probes; synthetic data, no product writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from jinja2 import Environment, ChainableUndefined
from playwright.sync_api import sync_playwright
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

TARGETS = ('templates/china.html.j2', 'templates/baskets_desk.js',
           'templates/cn_reversal_sleeve.html.j2')
ORIGINALS = {p: a.committed(p) for p in TARGETS}

def source(path):
    return getattr(a, 'RENDER_SOURCES', {}).get(path, ORIGINALS[path])

def reading(case):
    sub = a.fixture(a.radar.CN_PROFILE)
    for values in sub.values():
        values.iloc[-1] = .01 if case == 'complete_low' else .99
    if case == 'partial':
        next(iter(sub.values())).iloc[-1] = a.np.nan
    if case == 'unavailable':
        for values in sub.values():
            values.iloc[-1] = a.np.nan
    return a.compute(a.radar.CN_PROFILE, sub)

def chip(case):
    with patch.object(a.radar, 'snapshot', return_value=reading(case)):
        return a.radar.cn_sleeve_chip()

def jinja_region(kind, payload):
    env = Environment(autoescape=True, undefined=ChainableUndefined)
    env.globals['t'] = lambda en, zh: en + ' | ' + zh
    if kind == 'china':
        text = source(TARGETS[0])
        text = text[text.index('{% set _sc = setups.sleeve_chip'):]
        text = text.split('\n  </div>\n\n  {# CN Breathing', 1)[0]
        lens = SimpleNamespace(lens=lambda **kw: ' | '.join(kw.get('body', ())))
        return env.from_string(text).render(setups={'sleeve_chip': payload}, lens=lens)
    text = source(TARGETS[2])
    text = text[text.index('{# ---- SLEEVE SIZE chip'):]
    text = text.split('<div class="strip">', 1)[0]
    return env.from_string(text).render(d={'sizing': payload})

LEGACY = {'sleeve_factor': .9, 'radar_state': 'caution', 'can_force': False,
          'radar_as_of': '2026-09-08', 'label_en': 'Sleeve ×0.90',
          'label_zh': '仓位 ×0.90', 'passport': {'note': 'Legacy control'}}
CASES = ('complete_low', 'complete_high', 'partial', 'unavailable')

class DisplayAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def js_render(self, payload):
        text = source(TARGETS[1])
        function = text.split('function renderSleeveChip(){', 1)[1]
        function = 'function renderSleeveChip(){' + function.split('\n// renderRegimeSizing()', 1)[0]
        page = self.browser.new_page()
        try:
            page.set_content('<div id="sleeve-chip"></div>')
            page.evaluate('(p) => { window.BASKETS={sleeve_chip:p}; }', payload)
            page.add_script_tag(content='const L=(e,z)=>e+" | "+z; const esc=s=>{const x=document.createElement("span");x.textContent=String(s);return x.innerHTML;};' + function)
            page.evaluate('renderSleeveChip()')
            return page.locator('#sleeve-chip').inner_text()
        finally:
            page.close()

    def test_stock_board_never_turns_unreviewed_sizing_into_a_trade_instruction(self):
        for case in CASES:
            with self.subTest(case=case):
                html = jinja_region('china', chip(case))
                self.assertIn('Sizing unavailable', html)
                self.assertNotIn('normal sizing', html)
                self.assertNotIn('trade smaller', html)
                self.assertNotIn('how big to trade', html)

    def test_reversal_sleeve_renders_unavailable_without_numeric_crash(self):
        for case in CASES:
            with self.subTest(case=case):
                try:
                    html = jinja_region('reversal', chip(case))
                except (TypeError, ValueError) as exc:
                    self.fail(f'Actual reversal template cannot render candidate: {exc}')
                self.assertIn('Sizing unavailable', html)
                self.assertNotIn('×1.00', html)

    def test_shared_baskets_client_keeps_explicit_unavailable_assessment_visible(self):
        for case in CASES:
            with self.subTest(case=case):
                visible = self.js_render(chip(case))
                self.assertIn('Sizing unavailable', visible)
                self.assertNotIn('Drawdown-control sizing;', visible)

    def test_legacy_numeric_reversal_remains_renderable(self):
        self.assertIn('×0.90', jinja_region('reversal', LEGACY))

    def test_legacy_numeric_stock_board_keeps_its_original_advisory(self):
        self.assertIn('avoid chasing', jinja_region('china', LEGACY))

    def test_legacy_numeric_and_absent_baskets_states_are_unchanged(self):
        self.assertIn('Sleeve ×0.90', self.js_render(LEGACY))
        self.assertEqual(self.js_render(None), '')

class AuthorityAcceptance(unittest.TestCase):
    def test_corrected_construction_must_not_inherit_legacy_market_permission(self):
        out = reading('complete_high')
        self.assertIn(out['state'], ('caution', 'elevated', 'risk-off'))
        self.assertIsNone(out.get('gross_factor'))
        # This is exactly the existing runner's attachment shape; no ledger is read.
        out['forward_log'] = {'market': 'cn', 'n_graded': 200, 'can_force': True}
        out['can_force'] = bool(out['forward_log']['can_force'])
        overrides = []
        with patch.object(a.market_state, '_rr_scorecard_track', return_value=None), \
             patch.object(a.recovery, 'assess', return_value=None):
            rd = a.market_state._radar_override_intl({'risk_radar': out}, overrides)
        self.assertFalse(rd.get('binding'),
                         f'Unreviewed construction acquired ceiling={rd.get("ceiling")}; overrides={overrides}')

    def test_legacy_proven_payload_retains_existing_permission(self):
        out = {'market': 'cn', 'state': 'risk-off', 'can_force': True, 'top_score': 99}
        with patch.object(a.market_state, '_rr_scorecard_track', return_value=None), \
             patch.object(a.recovery, 'assess', return_value=None):
            rd = a.market_state._radar_override_intl({'risk_radar': out}, [])
        self.assertTrue(rd['binding'])
        self.assertEqual(rd['ceiling'], 26)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=('all', 'display', 'authority'), default='all')
    args = parser.parse_args()
    def file_state(path):
        p = a.ROOT / path
        return p.read_bytes() if p.exists() else None
    before = {p: file_state(p) for p in (*a.PATHS, *TARGETS)}
    a.apply_bundle(candidate.bundle)
    suite = unittest.TestSuite()
    for name, cls in (('display', DisplayAcceptance), ('authority', AuthorityAcceptance)):
        if args.scope in ('all', name):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = all(file_state(p) == raw for p, raw in before.items())
    print(json.dumps({'scope': args.scope, 'tests': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'source_unchanged': unchanged, 'synthetic_only': True,
        'source_sha256': {p: hashlib.sha256(v.encode()).hexdigest() for p, v in ORIGINALS.items()}}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)

if __name__ == '__main__':
    main()
