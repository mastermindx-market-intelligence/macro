"""Run the complete uninstalled candidate contract suite, including force consumers."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

NAMES = ['RRU_COMPOSITION_ACCEPTANCE_2026_09_08', 'RRU_COMPOSITION_EDGE_TESTS_2026_09_08',
    'RRU_COMPOSITION_CONSUMER_CLOSURE_2026_09_09', 'RRU_COMPOSITION_NUMERICAL_TESTS_2026_09_08',
    'RRU_DOWNSTREAM_ACCEPTANCE_2026_09_09', 'RRU_CONSTRUCTION_SERIALIZATION_2026_09_09',
    'RRU_REFERENCE_WINDOW_TESTS_2026_09_09', 'RRU_LEGACY_COHORT_TESTS_2026_09_09',
    'RRU_FORCE_APPLICABILITY_TESTS_2026_09_09', 'RRU_FORCE_BLOCK_TESTS_2026_09_09',
    'RRU_FORCE_FULL_CONSUMER_2026_09_09', 'RRU_INTL_JOURNEY_TESTS_2026_09_09']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-modules', action='store_true')
    args = parser.parse_args()
    modules = [importlib.import_module(n) for n in NAMES]
    def state(p):
        f = a.ROOT / p
        return f.read_bytes() if f.exists() else None
    before = {p: state(p) for p in candidate.bundle}
    a.apply_bundle(candidate.bundle)
    if args.full_modules:
        # Load whole amended engine modules, not only selected function AST nodes.
        # No runner/build function is invoked, and source files remain unchanged.
        for module in (a.radar, a.market_state, a.recovery, a.radar_audit, a.radar_tune, a.intl_dashboard, a.intl_builder):
            path = ('scripts/' if module is a.intl_builder else 'engine/') + module.__name__.rsplit('.', 1)[-1] + '.py'
            exec(compile(candidate.edited[path], path, 'exec'), module.__dict__)
    suites = [unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules]
    print(json.dumps(dict(source_pin=a.PIN, mode='whole_modules' if args.full_modules else 'function_injection',
        counts={n:s.countTestCases() for n,s in zip(NAMES,suites)},
        source_hashes={p:hashlib.sha256(candidate.edited[p].encode()).hexdigest()
                       for p in candidate.bundle})), flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(suites))
    unchanged = all(state(p) == v for p,v in before.items())
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        source_unchanged=unchanged, synthetic_only=True, production=False,
        full_pipeline=False, force_probe_included=True)), flush=True)
    return 0 if result.wasSuccessful() and unchanged else 1

if __name__ == '__main__':
    raise SystemExit(main())
