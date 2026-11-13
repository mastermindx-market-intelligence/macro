"""Test-first research scenarios; no native imports, model or production permission."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parent
P = ROOT / 'R16_CHANGE_CONTENT_EXERCISE_2026-09-24.py'
spec = importlib.util.spec_from_file_location('research_change', P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ContentTests(unittest.TestCase):
    def test_scenarios(self):
        cases = mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')
        for c in cases:
            with self.subTest(case=c['id']):
                original=copy.deepcopy(c['input'])
                result=mod.assess(c['input'])
                for k,v in c['expected'].items():
                    self.assertEqual(result[k],v,(c['id'],k,result))
                self.assertEqual(c['input'],original)
                self.assertTrue(result['decision_unchanged'])
                self.assertFalse(result['production_admitted'])
                self.assertFalse(result['can_rank'])
                self.assertFalse(result['can_notify'])
                if result['status']=='refused':
                    self.assertIsNone(result['text'])
                    self.assertIsNone(result['evidence_ref'])

    def test_no_implicit_sort_or_state(self):
        doc={'cases':mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')}
        a=[c['input'] for c in doc['cases'][:3]]
        self.assertEqual([mod.assess(x) for x in a],[mod.assess(x) for x in a])

    def test_public_copy_excludes_private_inputs(self):
        doc={'cases':mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')}
        for row in doc['cases']:
            if row['id'] in {'C24','C27'}:
                case=copy.deepcopy(row['input'])
                case['item']['private_text']='PRIVATE_SENTINEL_NEVER_RELEASE'
                result=mod.assess(case)
                self.assertNotIn('PRIVATE_SENTINEL_NEVER_RELEASE',json.dumps(result))
                self.assertIsNone(result['evidence_ref'])
                self.assertNotIn('decision_snapshot',result)
                self.assertNotIn('ranking',json.dumps(result))

    def test_bad_source_revision_is_not_freshness(self):
        doc={'cases':mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')}
        c=next(x for x in doc['cases'] if x['id']=='C15')
        self.assertEqual(mod.assess(c['input'])['reason'],'revision_content_conflict')

    def test_corrected_boundary_and_missing_comparison(self):
        doc={'cases':mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')}
        rows={c['id']:c for c in doc['cases']}
        self.assertEqual(mod.assess(rows['C37']['input'])['status'],'background')
        self.assertEqual(mod.assess(rows['C38']['input'])['reason'],'consensus_baseline_required')

    def test_rejects_live_use_and_unknown_fields(self):
        base=mod.load_cases(ROOT/'R16_CHANGE_CONTENT_CASES_2026-09-24.json')[0]['input']
        for key,value in [('synthetic',False),('score_override',100)]:
            b=copy.deepcopy(base); b[key]=value
            with self.assertRaises(ValueError): mod.assess(b)
        b=copy.deepcopy(base);b['item']['can_rank']=True
        with self.assertRaises(ValueError):mod.assess(b)

if __name__=='__main__': unittest.main(verbosity=2)
