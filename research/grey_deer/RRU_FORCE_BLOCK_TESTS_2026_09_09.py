"""Execute original/candidate audit-attachment blocks, with ledger/tuner IO mocked."""
from __future__ import annotations
import argparse
import ast
from contextlib import ExitStack
import json
import logging
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from RRU_FORCE_APPLICABILITY_TESTS_2026_09_09 import RUNNERS, sample
BASELINE = False

def assignments(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Assign) and len(n.targets)==1
        and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant)
        and n.targets[0].slice.value=='can_force']

class BlockTests(unittest.TestCase):
    pass

def case_test(path, nightly, modern):
    def test(self):
        source = a.committed(path) if BASELINE else a.RUNNER_SOURCES[path]
        choices = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Try) and len(assignments(n))==2]
        self.assertTrue(choices, 'Must execute the actual import/lane/attachment block')
        node = min(choices, key=lambda n:n.end_lineno-n.lineno)
        snap = sample(modern)
        snap.pop('forward_log')
        snap.pop('can_force')
        rec = dict(risk_radar=snap)
        sc = dict(market='cn', n_graded=200, can_force=True)
        ns = dict(rec=rec, latest=rec, _rri=a.radar, _prof=a.radar.CN_PROFILE,
                  _ledger_lane_armed=lambda:nightly, log=logging.getLogger('rru-block-test'), cc='CN')
        with ExitStack() as stack:
            stack.enter_context(patch.object(a.radar_audit, 'ledger_lane_armed', return_value=nightly))
            graded = stack.enter_context(patch.object(a.radar_audit, 'snapshot_and_grade', return_value=sc))
            readonly = stack.enter_context(patch.object(a.radar_audit, 'scorecard', return_value=sc))
            tuned = stack.enter_context(patch.object(a.radar_tune, 'tune', return_value=dict(status='fixture')))
            for name in ('_path', '_read', '_write'):
                stack.enter_context(patch.object(a.radar_audit, name, side_effect=AssertionError('No ledger IO')))
            code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
            exec(compile(code, path, 'exec'), ns)
            self.assertEqual(graded.call_count, int(nightly))
            self.assertEqual(readonly.call_count, int(not nightly))
            self.assertEqual(tuned.call_count, int(nightly))
            self.assertIs(snap['forward_log'], sc)
            self.assertEqual(snap['can_force'], not modern)
            self.assertTrue(sc['can_force'])
    return test

for i, path in enumerate(RUNNERS[:4]):
    for nightly in (True, False):
        for modern in (True, False):
            name = f'test_block_{i}_' + ('nightly_' if nightly else 'readonly_') + ('modern' if modern else 'legacy')
            setattr(BlockTests, name, case_test(path, nightly, modern))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-blocks', action='store_true')
    BASELINE = parser.parse_args().baseline_blocks
    before = {p:(a.ROOT/p).read_bytes() for p in RUNNERS[:4]}
    a.apply_bundle(candidate.bundle)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BlockTests))
    unchanged = all((a.ROOT/p).read_bytes()==v for p,v in before.items())
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        original_blocks=BASELINE, source_unchanged=unchanged, synthetic_only=True, effects_mocked=True,
        full_pipeline=False)))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
