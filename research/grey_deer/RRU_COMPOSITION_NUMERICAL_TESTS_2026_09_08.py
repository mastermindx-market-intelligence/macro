"""Numerical parity and independent row-wise oracle with the real percentile code."""
from __future__ import annotations
import argparse
import ast
from contextlib import ExitStack
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a

BASELINE = False

def baseline(profile, sub):
    env = dict(a.radar.__dict__)
    env.update(_read=lambda *args: a.BENCH, _sub_legs=lambda *args: sub,
               _gate_series=lambda *args: a.pd.Series(True, index=a.INDEX))
    node = next(n for n in ast.parse(a.SOURCES[a.PATHS[0]]).body
                if isinstance(n, ast.FunctionDef) and n.name == 'composite_series')
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    code = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
    exec(compile(code, 'pinned_original_composite', 'exec'), env)
    return env['composite_series'](profile)[2]

def observed(profile, sub):
    if BASELINE:
        return baseline(profile, sub)
    with patch.object(a.radar, '_read', return_value=a.BENCH), \
         patch.object(a.radar, '_sub_legs', return_value=sub), \
         patch.object(a.radar, '_gate_series', return_value=a.pd.Series(True, index=a.INDEX)):
        return a.radar.composite_series(profile)[2]

def oracle(profile, sub):
    rows = []
    for stamp in a.INDEX:
        terms = []
        for key, codes, weight in profile.comp_legs:
            values = [float(sub[code].get(stamp, a.np.nan)) for code in codes if code in sub]
            values = [v for v in values if a.np.isfinite(v)]
            if values:
                terms.append((sum(values) / len(values), weight))
        rows.append(sum(v * w for v, w in terms) / sum(w for _, w in terms) if terms else a.np.nan)
    raw = a.pd.Series(rows, index=a.INDEX).dropna()
    return a.radar.pct_rank_window(raw, a.radar._PCT_WIN)

class NumericalTests(unittest.TestCase):
    pass

def make_test(profile, partial):
    def test(self):
        sub = a.fixture(profile)
        if partial:
            group = profile.comp_legs[0][1]
            for code in group:
                sub[code].iloc[300::7] = a.np.nan
            sub[group[-1]] = sub[group[-1]].drop(a.INDEX[303::11])
            expected = oracle(profile, sub)
            a.pd.testing.assert_series_equal(observed(profile, sub), expected, check_exact=False,
                                           rtol=1e-12, atol=1e-12)
        else:
            a.pd.testing.assert_series_equal(observed(profile, sub), baseline(profile, sub), check_exact=True)
    return test

for profile in a.radar.PROFILES.values():
    for partial in (False, True):
        name = f'test_{profile.key}_' + ('missing_input_oracle' if partial else 'complete_exact_parity')
        setattr(NumericalTests, name, make_test(profile, partial))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    BASELINE = args.baseline
    before = {p: (a.ROOT / p).read_bytes() for p in a.PATHS[:3]}
    if not BASELINE:
        import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
        a.apply_bundle(candidate.bundle)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NumericalTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = all((a.ROOT / p).read_bytes() == raw for p, raw in before.items())
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'baseline': BASELINE,
                      'synthetic_only': True, 'source_unchanged': unchanged,
                      'oracle': 'independent_rowwise_available_weight_plus_actual_percentile'}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
