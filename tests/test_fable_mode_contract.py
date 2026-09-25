"""R3.1 source-contract regression checks, not model-behavior tests."""
import os
from pathlib import Path
import unittest
ROOT = Path(os.environ.get('FABLE_ROOT', Path(__file__).resolve().parents[1]))
SKILL = ROOT / '.claude/skills/fable-mode'
def text(name):
    return (SKILL / name).read_text()
class R31Contract(unittest.TestCase):
    def test_missing_watch_has_no_fictional_wake(self):
        s = text('references/harness-adapters.md')
        self.assertNotIn('it ends its turn on a state and is re-invoked by the event', s)
        self.assertNotIn('let the event re-invoke you', s)
        self.assertIn('verified return path', s)
    def test_missing_return_does_not_duplicate_worker(self):
        s = text('references/orchestration.md')
        self.assertNotIn('answer the gating sub-questions yourself with a few targeted probes in parallel with the worker', s)
        self.assertIn('do not duplicate the live assignment', s)
        self.assertIn('read-only', s)
    def test_no_effect_does_not_authorize_retry(self):
        s = text('references/long-horizon.md')
        self.assertIn('EFFECT_NONE is not retry permission', s)
        self.assertIn('permission denial', s)
    def test_economics_not_universal_fable_price(self):
        s = text('references/long-horizon.md')
        self.assertIn('historical Fable measurement', s)
        self.assertIn('cost per accepted outcome', s)
        self.assertIn('rejected attempts', s)
    def test_codex_checks_discovery_and_child_effort(self):
        s = text('references/harness-adapters.md')
        for expected in ('skills/list', 'forceReload', 'reasoning effort', 'sparse', 'not model-behavior proof'):
            self.assertIn(expected, s)
    def test_distillation_requires_return_proof(self):
        s = (ROOT / 'config/fable_mode_core.md').read_text()
        self.assertIn('verified return path', s)
    def test_ownership_gate_accepts_native_return_binding(self):
        for source in (text('SKILL.md'), (ROOT / 'config/fable_mode_core.md').read_text()):
            self.assertTrue('one owner, one verified return binding' in source,
                            'Ownership gate must allow a verified native return, not require a duplicate watcher')
    def test_existing_numbered_rules_and_references_survive(self):
        s = text('SKILL.md')
        for prefix, count in [('S', 8), ('O', 17), ('L', 14), ('A', 7)]:
            for n in range(1, count + 1):
                self.assertIn(f'**{prefix}.{n} ', s)
        for name in ('engineering','orchestration','long-horizon','adjudication','packets','harness-adapters'):
            self.assertTrue((SKILL / 'references' / (name + '.md')).is_file())
if __name__ == '__main__':
    import json
    import sys
    result = unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromTestCase(R31Contract).run(result)
    report = {'kind':'SOURCE_CONTRACT_ONLY', 'root':str(ROOT), 'tests':result.testsRun,
              'failures':[t.id() for t,_ in result.failures],
              'errors':[t.id() for t,_ in result.errors],
              'behavioral_trials':0}
    encoded = json.dumps(report, indent=2) + '\n'
    print(encoded)
    if os.environ.get('FABLE_REPORT'):
        Path(os.environ['FABLE_REPORT']).write_text(encoded)
    sys.exit(0 if result.wasSuccessful() else 1)
