"""Current-function boundary regression, NOT a full production/live-data test.

Default: execute the captured build_situations function, keeping its complete body
unchanged; isolate parquet/config/classifier/identity/lifecycle collaborators.
With --repo-root: import the repository's actual engine module, mock only its I/O
boundaries and use its real classify/noise/cross-border/floor/lifecycle helpers.
Neither mode writes the repository, starts models, calls a network or publishes.
Fixtures use invented CIKs/IDs. They reproduce the reported role shape; they are
not exported MGLD/USCF production rows or an economic-rights assertion.
"""
from __future__ import annotations
import argparse, hashlib, importlib, inspect, json, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

HERE = Path(__file__).resolve().parent
MODE = 'captured_function_isolated_collaborators'
REPO_ROOT = None
CANDIDATE = False


def load_engine():
    if REPO_ROOT:
        sys.path.insert(0, str(Path(REPO_ROOT).resolve()))
        return importlib.import_module('engine.special_situations')
    source_bytes = (HERE / 'inputs' / 'build_situations_excerpt.py').read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != '57a042fd3a998860fb0ea0d084e5eefb4ba3c61a4b09512eb973b3ff2ec24355':
        raise ValueError('CAPTURE_IDENTITY_MISMATCH: reconcile source before using this fixture')
    src = source_bytes.decode('utf-8')
    mod = types.ModuleType('captured_special_situations')
    labels = dict(ACQ='Acquisitions', DIV='Divestitures', ACT='Activist Campaigns', REV='Strategic Reviews',
        TO='Tender Offers', GP='Going-Private', CAP='Capital Returns', SPIN='Spin-Offs',
        RIGHTS='Rights Offerings', RESTR='Restructuring', LIQ='Liquidations', DELIST='Delistings',
        ITEND='Issuer Tenders', TERM='Deal Terminations', SPAC='SPACs', MGMT='Management Changes', OTHER='Other')
    mod.__dict__.update(labels)
    mod.pd = pd; mod.GROUP = 'special_situations'; mod.SCORED = False
    mod.LLM_PROMOTABLE = frozenset(labels.values()) - {labels['MGMT']}
    mod.LLM_STAGE_DEFAULT = {x: 'announced' for x in labels.values()}
    mod.LLM_STAGE_DEFAULT.update({labels['GP']: 'live', labels['TO']: 'live'})
    # These are deliberately isolated collaborators; the full repository mode
    # below is the required owner-side follow-up, not a claimed local result.
    mod.classify = lambda form, items: (labels['GP'], 'live', 'ok') if form == 'SC 13E3' else (None, None, 'defer')
    mod._is_noise_filer = lambda company: False
    mod._is_cross_border = lambda row: False
    mod.apply_floor = lambda cap, floor: None if cap is None else cap >= floor
    mod.lifecycle = lambda df: {}
    mod.config = types.SimpleNamespace(data_dir=lambda: None)
    mod._universe_caps = lambda: ({}, {})
    mod._cfg = lambda: {}
    exec(compile(src, 'captured:engine/special_situations.py@ff3b55d3', 'exec'), mod.__dict__)
    return mod

ENGINE = None

def row(role='none', category='Going-Private', **changes):
    item = dict(id='fixture-event-100', cik=10001, company='Example affected fund',
        form_type='8-K', items='1.01|8.01', date_filed='2026-09-25',
        llm_category=category, llm_role=role, llm_confidence='high',
        summary='A control-chain transaction is disclosed; registrant role is not a direct target.',
        source_url='https://example.invalid/fixture-not-a-real-filing')
    item.update(changes)
    return item


def run_rows(rows):
    frame = pd.DataFrame(rows)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root / 'special_situations').mkdir(); (root / 'special_situations' / 'events.parquet').touch()
        with patch.object(ENGINE.config,'data_dir',return_value=root), \
             patch.object(ENGINE.pd,'read_parquet',return_value=frame.copy(deep=True)), \
             patch.object(ENGINE,'_universe_caps',return_value=({10001:'FIX-A',10002:'FIX-B'},{'FIX-A':200.,'FIX-B':250.})), \
             patch.object(ENGINE,'_cfg',return_value={'market_cap_floor_musd':100}):
            return ENGINE.build_situations()


class RoleRegression(unittest.TestCase):
    def assert_withheld(self, raw):
        result=run_rows([raw]); self.assertEqual(len(result),1, 'Keep raw evidence discoverable')
        self.assertEqual(result.iloc[0]['status'],'defer', 'Non-target GP must not be eligible as a direct situation')
        self.assertTrue(pd.isna(result.iloc[0]['category']), 'Do not leave a direct-target category')
        self.assertIsInstance(result.iloc[0]['llm_category'],str,'Original annotation must survive')
        self.assertEqual(result.iloc[0]['llm_category'],'Going-Private', 'Keep the original annotation for review')
        self.assertEqual(result.iloc[0]['source_url'],raw['source_url'])
    def test_none_role_withheld(self): self.assert_withheld(row('none'))
    def test_filer_role_withheld(self): self.assert_withheld(row('filer'))
    def test_acquirer_role_withheld(self): self.assert_withheld(row('acquirer'))
    def test_seller_role_withheld(self): self.assert_withheld(row('seller'))
    def test_issuer_role_not_assumed_target(self): self.assert_withheld(row('issuer'))
    def test_null_role_withheld(self): self.assert_withheld(row(None))
    def test_blank_role_withheld(self): self.assert_withheld(row(''))
    def test_pdna_role_withheld(self): self.assert_withheld(row(pd.NA))
    def test_absent_role_column_withheld(self):
        item=row(); del item['llm_role']; self.assert_withheld(item)
    def test_unknown_role_withheld(self): self.assert_withheld(row('beneficiary'))
    def test_keyword_does_not_repromote_role_conflict(self):
        self.assert_withheld(row('none',text_category='Acquisitions',text_stage='announced'))
    def test_target_keeps_existing_classification(self):
        out=run_rows([row('target')]).iloc[0]
        self.assertEqual((out['category'],out['status'],out['role']),('Going-Private','ok','target'))
    def test_structured_without_llm_is_unchanged(self):
        raw=row(form_type='SC 13E3'); del raw['llm_category']; del raw['llm_role']
        out=run_rows([raw]).iloc[0]; self.assertEqual((out['category'],out['status']),('Going-Private','ok'))
    def test_normalized_target_is_not_rejected(self):
        out=run_rows([row(' TARGET ')]).iloc[0]
        self.assertEqual((out['category'],out['status']),('Going-Private','ok'))
    def test_normalized_none_is_withheld(self): self.assert_withheld(row(' NONE '))
    def test_non_gp_acquirer_keeps_existing_classification(self):
        out=run_rows([row('acquirer','Acquisitions')]).iloc[0]
        self.assertEqual((out['category'],out['status']),('Acquisitions','ok'))
    def test_none_category_stays_skip(self):
        out=run_rows([row('none','None')]).iloc[0]; self.assertEqual(out['status'],'skip')
    def test_empty_input_stays_empty(self): self.assertTrue(run_rows([]).empty)
    def test_separate_direct_and_non_target_rows(self):
        raw=[row('target',id='direct'), row('none',id='related',cik=10002)]
        out=run_rows(raw).set_index('id'); self.assertEqual(len(out),2)
        self.assertEqual(out.loc['direct','status'],'ok'); self.assertEqual(out.loc['related','status'],'defer')
    def test_reread_preserves_result_and_fixture(self):
        raw=[row('target',id='direct'),row('none',id='related',cik=10002)]
        before=json.dumps(raw,sort_keys=True)
        first=run_rows(raw); second=run_rows(raw)
        pd.testing.assert_frame_equal(first,second)
        self.assertEqual(before,json.dumps(raw,sort_keys=True))
    def test_withheld_stage_not_live(self):
        frame=run_rows([row('none')]); self.assertEqual(len(frame),1)
        out=frame.iloc[0]
        self.assertTrue(pd.isna(out['stage']))
    def test_input_annotation_preserved(self):
        raw=row('none'); frame=run_rows([raw]); self.assertEqual(len(frame),1)
        out=frame.iloc[0]
        self.assertEqual(out['llm_role'],'none'); self.assertEqual(out['summary'],raw['summary'])
        self.assertEqual(out['id'],raw['id']); self.assertFalse(ENGINE.SCORED)


def main():
    global ENGINE,REPO_ROOT,MODE,CANDIDATE
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root'); ap.add_argument('--candidate',action='store_true')
    ap.add_argument('--report',default=str(HERE/'reports'/'role_result.json')); args=ap.parse_args()
    REPO_ROOT=args.repo_root; CANDIDATE=args.candidate
    if REPO_ROOT: MODE='repository_module_fixture_io'
    ENGINE=load_engine()
    if CANDIDATE:
        if REPO_ROOT: raise SystemExit('Candidate transformation is capture-only; apply reviewed repair separately in the owning repository.')
        from candidate_guard import patched_source
        src=(HERE/'inputs'/'build_situations_excerpt.py').read_text()
        exec(compile(patched_source(src),'candidate:build_situations','exec'),ENGINE.__dict__)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoleRegression))
    failures=[{'test':str(t),'detail':trace} for t,trace in result.failures]
    errors=[{'test':str(t),'detail':trace} for t,trace in result.errors]
    actual_module = Path(ENGINE.__file__) if REPO_ROOT else None
    actual_function = inspect.getsource(ENGINE.build_situations) if REPO_ROOT else None
    report={'scope':MODE,'source_ref':'ff3b55d3e8935d236c03cf4d74223a18fbe52b53',
        'repository_blob':'4e79fc0b22045917bcb1110092ad402187cddef0',
        'source_identity_note':'source_ref/repository_blob identify the captured baseline, not an arbitrary --repo-root checkout',
        'actual_module_sha256':hashlib.sha256(actual_module.read_bytes()).hexdigest() if actual_module else None,
        'actual_function_sha256':hashlib.sha256(actual_function.encode()).hexdigest() if actual_function else None,
        'candidate':CANDIDATE,
        'tests':result.testsRun,'passed':result.testsRun-len(failures)-len(errors),
        'failures':failures,'errors':errors,'production_modified':False,'live_data_used':False,
        'excerpt_sha256':hashlib.sha256((HERE/'inputs'/'build_situations_excerpt.py').read_bytes()).hexdigest()}
    destination = Path(args.report); destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__': raise SystemExit(main())
