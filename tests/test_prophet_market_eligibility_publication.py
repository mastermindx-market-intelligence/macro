"""Native frozen-source -> producer -> published-file/receipt tests.

All observations are synthetic. Actual build_prophet helper, existing gzip
snapshot owner, native calendar and native Risk Envelope execute; only paths
and the supplied observation clock are isolated. No policy is activated.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.risk_envelope import SourceRead, compose_envelope, canonical_json
from engine.prophet_market_eligibility import bind_shadow_view
from scripts import build_prophet as bp
from scripts.build_prophet_market_eligibility import (
    prepare_publication_shadow, read_publication_shadow, MarketEligibilityError,
)


class NativePublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / 'data/prophet'
        self.board_path = self.root / 'site/factordata/us_standouts.json'
        self.risk_path = self.root / 'site/riskdata/risk_envelope.json'
        self.index_path = self.root / 'site/prophet/index.json'
        self.now = datetime(2026, 9, 28, 13, 0, tzinfo=timezone.utc)
        self.reads = [
            SourceRead(source_id='market-state-latest', role='measured_state',
                       state='RISK_ON', score=77, as_of='2026-09-25', required=True),
            SourceRead(source_id='leadership-crack-latest', role='hazard_evidence',
                       state='BROKEN', hazard_stage='FRAGILE', as_of='2026-09-25', required=True),
        ]
        self.board = {
            'as_of':'2026-09-25','board_definition':'us_prophet_v3',
            'staleness':{'price_through':'2026-09-25','delayed':False,'unknown':False,'basis':'panel_majority'},
            'buy':[{'ticker':'SYNTH_A','prophet':{'rank':1,'score':99}},
                   {'ticker':'SYNTH_B','prophet':{'rank':2,'score':90}}],
        }
        self.board_path.parent.mkdir(parents=True)
        self.board_path.write_text(json.dumps(self.board))
        self.risk_path.parent.mkdir(parents=True)
        self.write_envelope()
        self.addCleanup(patch.stopall)
        patch.object(bp, 'LEDGER_DIR', self.ledger).start()
        patch.object(bp, 'INDEX_PATH', self.index_path).start()
        _, digest, path = bp._freeze_origination_source_board(self.board_path)
        self.index = {'source_asof':'2026-09-25','source_board_asof':'2026-09-25',
                      'source_board_sha256':digest,'source_board_snapshot_path':path,
                      'source_board_snapshot_encoding':'gzip','plans':[{'id':'KEEP_ME'}]}

    def write_envelope(self, reads=None, session='2026-09-25'):
        self.native = compose_envelope(sources=self.reads if reads is None else reads,
            market='US',source_session=session,observed_at='2026-09-28T06:00:00Z',
            produced_at='2026-09-28T06:00:00Z',stale_after=None)
        self.risk_path.write_text(canonical_json(self.native)+'\n')

    def publish(self):
        before = deepcopy(self.index)
        receipt = bp._write_market_eligibility_shadow(self.index, self.now)
        self.assertEqual(self.index,before)
        self.assertEqual(receipt['production_behavior'],'UNCHANGED')
        if receipt['artifact_status']=='WRITTEN':
            raw=(self.index_path.parent/receipt['file']).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(),receipt['sha256'])
            doc=json.loads(raw)
            self.assertFalse(any(doc['authority'].values()))
            self.assertEqual(len(doc['rows']),len(self.board['buy']))
            return receipt,doc
        return receipt,None

    def test_native_source_to_artifact_and_bound_consumer(self):
        receipt,doc=self.publish()
        self.assertEqual(receipt['artifact_status'],'WRITTEN')
        self.assertEqual(doc['source_state'],'AVAILABLE')
        raw_board=gzip.decompress((self.root/self.index['source_board_snapshot_path']).read_bytes())
        raw_risk=gzip.decompress((self.root/receipt['risk_envelope_snapshot_path']).read_bytes())
        view=bind_shadow_view(doc,raw_board,raw_risk,
            expected_board_sha256=self.index['source_board_sha256'],
            expected_board_definition='us_prophet_v3',expected_source_session='2026-09-25',
            expected_envelope_sha256=receipt['risk_envelope_sha256'],
            expected_decision_at=receipt['decision_at'],expected_valid_until=receipt['valid_until'],
            read_at='2026-09-28T13:01:00Z')
        self.assertEqual([r['candidate'] for r in view['rows']],self.board['buy'])

    def test_publication_clock_preserves_subsecond_availability(self):
        self.now = self.now.replace(microsecond=223456)
        self.native['observed_at'] = '2026-09-28T13:00:00.123456Z'
        self.native['produced_at'] = '2026-09-28T13:00:00.123456Z'
        self.risk_path.write_text(canonical_json(self.native)+'\n')
        receipt, doc = self.publish()
        self.assertEqual(doc['source_state'], 'AVAILABLE')
        self.assertEqual(receipt['decision_at'], '2026-09-28T13:00:00.223456Z')

    def test_calendar_window_uses_existing_completed_session_rollover(self):
        receipt,doc=self.publish()
        self.assertEqual(doc['board']['source_session'],'2026-09-25')
        self.assertEqual(receipt['valid_until'],'2026-09-28T21:00:00Z')

    def test_mutable_board_replacement_cannot_change_frozen_population(self):
        self.board_path.write_text('{"buy":[]}')
        receipt,doc=self.publish()
        self.assertEqual(receipt['row_count'],2)
        self.assertEqual([r['ticker'] for r in doc['rows']],['SYNTH_A','SYNTH_B'])

    def test_missing_risk_is_unavailable_not_zero_policy(self):
        self.risk_path.unlink()
        receipt,doc=self.publish()
        self.assertEqual(receipt['artifact_status'],'WRITTEN')
        self.assertEqual(doc['source_state'],'UNAVAILABLE')
        self.assertIn('ENVELOPE_MISSING',doc['errors'])
        self.assertIsNone(receipt['risk_envelope_snapshot_path'])

    def test_unreadable_risk_does_not_reuse_old_available_file(self):
        self.publish()
        self.risk_path.write_text('not json')
        receipt,doc=self.publish()
        self.assertEqual(doc['source_state'],'UNAVAILABLE')
        self.assertEqual(receipt['risk_source_read'],'UNAVAILABLE')

    def test_required_unmapped_hazard_is_not_qualified(self):
        self.write_envelope([self.reads[0],replace(self.reads[1],state='NEW_UNKNOWN_STATE',hazard_stage=None)])
        self.assertEqual(self.native['data_state'],'FRESH')
        receipt,doc=self.publish()
        self.assertEqual(doc['source_state'],'UNAVAILABLE')
        self.assertIn('ENVELOPE_HAZARD_UNAVAILABLE',doc['errors'])

    def test_no_hazard_source_is_not_qualified(self):
        self.write_envelope([self.reads[0]])
        _,doc=self.publish()
        self.assertIn('ENVELOPE_HAZARD_UNAVAILABLE',doc['errors'])

    def test_no_measured_source_is_not_qualified(self):
        self.write_envelope([self.reads[1]])
        _,doc=self.publish()
        self.assertIn('ENVELOPE_MEASURED_STATE_UNAVAILABLE',doc['errors'])

    def test_newer_wrapper_does_not_change_price_source_session(self):
        self.board['as_of']='2026-09-28'
        self.board_path.write_text(json.dumps(self.board))
        _,digest,path=bp._freeze_origination_source_board(self.board_path)
        self.index.update(source_board_sha256=digest,source_board_snapshot_path=path,source_board_asof='2026-09-28')
        _,doc=self.publish()
        self.assertEqual(doc['source_state'],'AVAILABLE')
        self.assertEqual(doc['board']['source_session'],'2026-09-25')
        self.assertEqual(doc['board']['source_board_asof'],'2026-09-28')

    def test_stale_price_source_cannot_qualify_with_new_wrapper(self):
        self.board['as_of']='2026-09-28'
        self.board['staleness']['price_through']='2026-09-24'
        self.board_path.write_text(json.dumps(self.board))
        _,digest,path=bp._freeze_origination_source_board(self.board_path)
        self.index.update(source_board_sha256=digest,source_board_snapshot_path=path,source_board_asof='2026-09-28',source_asof='2026-09-24')
        receipt,doc=self.publish()
        self.assertEqual(receipt['artifact_status'],'WRITTEN')
        self.assertEqual(doc['source_state'],'UNAVAILABLE')
        self.assertIn('BOARD_SOURCE_HEALTH_UNQUALIFIED',doc['errors'])

    def test_index_cannot_retarget_snapshot_by_changing_path(self):
        self.index['source_board_snapshot_path']='data/prophet/origination_sources/other.json.gz'
        receipt,_=self.publish();self.assertIsNone(receipt['file'])

    def test_corrupt_existing_snapshot_is_not_rebuilt_from_latest_board(self):
        (self.root/self.index['source_board_snapshot_path']).write_bytes(b'bad gzip')
        receipt,_=self.publish();self.assertIsNone(receipt['file'])

    def test_same_input_clock_is_idempotent_and_snapshots_reused(self):
        a,one=self.publish(); files=set(self.ledger.rglob('*.json.gz'))
        b,two=self.publish();self.assertEqual(a,b);self.assertEqual(one,two)
        self.assertEqual(files,set(self.ledger.rglob('*.json.gz')))
        self.assertEqual(len(files),2)

    def test_next_settled_refresh_binds_new_generation(self):
        a,one=self.publish()
        self.now=datetime(2026,9,29,13,0,tzinfo=timezone.utc)
        self.board['as_of']='2026-09-28';self.board['staleness']['price_through']='2026-09-28'
        self.board['buy'][0]['prophet']['score']=100
        self.board_path.write_text(json.dumps(self.board))
        _,digest,path=bp._freeze_origination_source_board(self.board_path)
        self.index.update(source_board_sha256=digest,source_board_snapshot_path=path,source_board_asof='2026-09-28',source_asof='2026-09-28')
        self.write_envelope([replace(x,as_of='2026-09-28') for x in self.reads],session='2026-09-28')
        b,two=self.publish()
        self.assertEqual(two['source_state'],'AVAILABLE')
        self.assertNotEqual(a['sidecar_id'],b['sidecar_id'])
        self.assertEqual(b['valid_until'],'2026-09-29T21:00:00Z')
        self.assertTrue((self.root/a['risk_envelope_snapshot_path']).exists())

    def test_write_failure_exposes_no_previous_artifact_reference(self):
        self.publish()
        with patch.object(bp,'_write_json',side_effect=OSError('synthetic write failure')):
            receipt,_=self.publish()
        self.assertEqual(receipt['artifact_status'],'UNAVAILABLE')
        self.assertIsNone(receipt['file'])

    def test_naive_clock_refused(self):
        self.now=self.now.replace(tzinfo=None)
        receipt,_=self.publish();self.assertIsNone(receipt['file'])

    def test_actual_checkpoint_allowlist_accepts_only_named_addition(self):
        source=(ROOT/'scripts/ci/daily_engine_prophet_checkpoint.sh').read_text()
        start=source.index('  case "$rel" in')
        stop=source.index('  esac',start)+len('  esac')
        case=source[start:stop]
        for path,allowed in [('site/prophet/market_eligibility.json',True),
            ('site/prophet/index.json',True),('data/prophet/origination_sources/abc.json.gz',True),
            ('site/prophet/market_eligibility_extra.json',False),('site/riskdata/risk_envelope.json',False)]:
            with self.subTest(path=path):
                r=subprocess.run(['bash','-c','rel="$1"\n'+case,'--',path],capture_output=True,text=True)
                self.assertEqual(r.returncode==0,allowed)


    def published_index(self):
        receipt, doc = self.publish()
        self.assertEqual(receipt['artifact_status'], 'WRITTEN')
        index = deepcopy(self.index)
        index['market_eligibility_shadow'] = receipt
        return index, doc

    def read_index(self, index, read_at=None):
        return read_publication_shadow(index, ledger_dir=self.ledger,
            index_dir=self.index_path.parent, read_at=read_at or self.now)

    def test_read_published_full_source_chain(self):
        index, _ = self.published_index()
        before = {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        view = self.read_index(index)
        self.assertEqual([r['candidate'] for r in view['rows']], self.board['buy'])
        self.assertEqual(view['source_state'], 'AVAILABLE')
        self.assertFalse(any(view['authority'].values()))
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()})

    def test_read_uses_frozen_sources_not_mutable_latest(self):
        index, _ = self.published_index()
        self.board_path.unlink(); self.risk_path.unlink()
        self.assertEqual(len(self.read_index(index)['rows']), 2)

    def test_read_written_missing_risk_preserves_research(self):
        self.risk_path.unlink()
        index, _ = self.published_index()
        view = self.read_index(index)
        self.assertEqual(view['source_state'], 'UNAVAILABLE')
        self.assertEqual([r['candidate'] for r in view['rows']], self.board['buy'])

    def test_read_legacy_absence_does_not_open_old_file(self):
        self.publish()
        with patch('scripts.build_prophet_market_eligibility._read', side_effect=AssertionError('no file read')):
            self.assertIsNone(self.read_index(self.index))

    def test_read_failed_publication_never_reuses_old_file(self):
        self.publish()
        index = deepcopy(self.index)
        index['market_eligibility_shadow'] = {
            'mode':'SHADOW_ONLY','production_behavior':'UNCHANGED',
            'source_state':'UNAVAILABLE','artifact_status':'UNAVAILABLE',
            'file':None,'error_type':'OSError'}
        with patch('scripts.build_prophet_market_eligibility._read', side_effect=AssertionError('no file read')):
            self.assertIsNone(self.read_index(index))

    def test_read_bad_unavailable_receipt_refused(self):
        index, _ = self.published_index()
        index['market_eligibility_shadow']['artifact_status'] = 'UNAVAILABLE'
        with self.assertRaises(MarketEligibilityError): self.read_index(index)

    def test_read_null_receipt_not_legacy(self):
        index = deepcopy(self.index); index['market_eligibility_shadow'] = None
        with self.assertRaises(MarketEligibilityError): self.read_index(index)

    def test_read_artifact_hash_mismatch(self):
        index, _ = self.published_index()
        (self.index_path.parent/'market_eligibility.json').write_text('{}')
        with self.assertRaisesRegex(MarketEligibilityError, 'ARTIFACT_HASH_MISMATCH'): self.read_index(index)

    def test_read_rehashed_authority_cannot_pass(self):
        index, doc = self.published_index()
        doc['authority']['can_gate_new_entry'] = True
        raw = json.dumps(doc).encode(); (self.index_path.parent/'market_eligibility.json').write_bytes(raw)
        index['market_eligibility_shadow']['sha256'] = sha256(raw).hexdigest()
        with self.assertRaisesRegex(MarketEligibilityError, 'SIDECAR_SEMANTIC_MISMATCH'): self.read_index(index)

    def test_read_rehashed_population_change_cannot_pass(self):
        index, doc = self.published_index(); doc['rows'].pop()
        raw = json.dumps(doc).encode(); (self.index_path.parent/'market_eligibility.json').write_bytes(raw)
        index['market_eligibility_shadow']['sha256'] = sha256(raw).hexdigest()
        with self.assertRaisesRegex(MarketEligibilityError, 'SIDECAR_SEMANTIC_MISMATCH'): self.read_index(index)

    def test_read_receipt_summary_cannot_override_source(self):
        index, _ = self.published_index()
        for key, value in [('row_count', 0), ('row_count', True), ('source_state', 'UNAVAILABLE'),
                           ('source_board_sha256', 'f'*64), ('sidecar_id', 'pme:'+'f'*64),
                           ('can_gate_new_entry', True), ('risk_source_read', 'UNAVAILABLE')]:
            trial = deepcopy(index); trial['market_eligibility_shadow'][key] = value
            with self.subTest(key=key,value=value), self.assertRaises(MarketEligibilityError):
                self.read_index(trial)

    def test_read_receipt_path_cannot_select_another_file(self):
        index, _ = self.published_index()
        index['market_eligibility_shadow']['file'] = '../../riskdata/risk_envelope.json'
        with self.assertRaisesRegex(MarketEligibilityError, 'REFERENCE_INVALID'): self.read_index(index)

    def test_read_board_snapshot_corruption_refused(self):
        index, _ = self.published_index()
        (self.root/index['source_board_snapshot_path']).write_bytes(gzip.compress(b'{}'))
        with self.assertRaises(MarketEligibilityError): self.read_index(index)

    def test_read_risk_snapshot_missing_is_not_silent_fallback(self):
        index, _ = self.published_index()
        (self.root/index['market_eligibility_shadow']['risk_envelope_snapshot_path']).unlink()
        with self.assertRaisesRegex(MarketEligibilityError, 'PUBLICATION_SOURCE_UNREADABLE'): self.read_index(index)

    def test_read_risk_reference_retarget_refused(self):
        index, _ = self.published_index()
        index['market_eligibility_shadow']['risk_envelope_snapshot_path'] = index['source_board_snapshot_path']
        with self.assertRaisesRegex(MarketEligibilityError, 'PUBLICATION_RISK_REFERENCE_INVALID'): self.read_index(index)

    def test_read_expired_and_predecision_refused(self):
        index, _ = self.published_index()
        for now in [datetime(2026,9,28,12,59,tzinfo=timezone.utc), datetime(2026,9,28,21,tzinfo=timezone.utc)]:
            with self.subTest(now=now), self.assertRaisesRegex(MarketEligibilityError, 'OUTSIDE_VALIDITY'):
                self.read_index(index, now)

    def test_read_window_is_calendar_bound_not_caller_extended(self):
        index, _ = self.published_index()
        index['market_eligibility_shadow']['valid_until'] = '2026-09-29T21:00:00Z'
        with self.assertRaisesRegex(MarketEligibilityError, 'PUBLICATION_WINDOW_MISMATCH'): self.read_index(index)

    def test_read_naive_clock_refused(self):
        index, _ = self.published_index()
        with self.assertRaisesRegex(MarketEligibilityError, 'NAIVE_READ_CLOCK'):
            self.read_index(index, datetime(2026,9,28,13))

    def test_read_symlinked_sidecar_refused(self):
        index, _ = self.published_index(); p=self.index_path.parent/'market_eligibility.json'
        other=p.with_suffix('.bak');p.rename(other);p.symlink_to(other)
        with self.assertRaisesRegex(MarketEligibilityError, 'SYMLINKED'): self.read_index(index)

    def acceptance_input(self, index):
        index = deepcopy(index)
        index['plans'] = []
        index['intake'] = {k:0 for k in ['originated','admitted','duplicate_id_blocked',
            'reorigination_blocked','eligible_after_skips','validation_failed','truncated','unaccounted']}
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index))

    def test_native_acceptance_consumes_correct_shadow(self):
        from scripts.prophet_board_acceptance import check
        index, _ = self.published_index();self.acceptance_input(index)
        self.assertEqual(check(self.root,'synthetic-run',self.now), [])

    def test_native_acceptance_detects_wrong_published_file(self):
        from scripts.prophet_board_acceptance import check
        index, _ = self.published_index();self.acceptance_input(index)
        (self.index_path.parent/'market_eligibility.json').write_text('{}')
        problems=check(self.root,'synthetic-run',self.now)
        self.assertEqual(problems,['market eligibility publication: unqualified source/receipt binding'])

    def test_native_acceptance_missing_risk_is_not_a_breach(self):
        from scripts.prophet_board_acceptance import check
        self.risk_path.unlink();index,_=self.published_index();self.acceptance_input(index)
        self.assertEqual(check(self.root,'synthetic-run',self.now), [])

    def test_native_acceptance_legacy_index_unchanged(self):
        from scripts.prophet_board_acceptance import check
        self.acceptance_input(self.index)
        self.assertEqual(check(self.root,'synthetic-run',self.now), [])


if __name__=='__main__':
    unittest.main(verbosity=2)
