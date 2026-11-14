import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from admin import capacity_history as history
from admin.capacity_fabric_schema import SCHEMA, TOKEN_FIELDS
from admin.capacity_ingest import ingest

NOW = 1_800_000_000
EPOCH = 'a' * 32


def snapshot(sequence=1, *, epoch=EPOCH, started=NOW-7200, at=NOW, output=7, rid='b'*32):
    usage = {k: None for k in TOKEN_FIELDS}
    usage.update(input_tokens=11, output_tokens=output)
    bucket = {"at": int(at//60)*60, "completed": 1, "failed": 0, "usage_known": int(output is not None),
              **{k: usage[k] or 0 for k in TOKEN_FIELDS},
              **{k+'_known': int(usage[k] is not None) for k in TOKEN_FIELDS}}
    return {"schema": SCHEMA, "epoch": epoch, "sequence": sequence, "started_at": started,
        "generated_at": at, "routes": [], "aliases": {}, "active": [],
        "recent": [{"id": rid, "started_at": at-2, "ended_at": at, "state": "completed",
                    "provider": "pool-a", "served_model": "model-a", "requested_model": "model-a",
                    "lane": "fabric/fast", "usage": usage, "usage_source": "provider_reported"}],
        "series": [bucket], "totals": {"completed": 1, "usage_known": int(output is not None),
                                       **{k: usage[k] or 0 for k in TOKEN_FIELDS}}}


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'history.sqlite3'
    def tearDown(self):
        self.tmp.cleanup()
    def write(self, s, **kw):
        return history.record(s, path=self.path, now=s['generated_at'], **kw)
    def query(self, minutes='all', **kw):
        return history.query(minutes, path=self.path, now=NOW+1, **kw)

    def test_cumulative_frames_are_replaced_not_added(self):
        self.write(snapshot())
        self.write(snapshot(2))
        result = self.query()
        self.assertEqual(result['summary']['output_tokens'], 7)
        self.assertEqual(sum(b['output_tokens'] for b in result['series']), 7)
        self.assertEqual(result['pools'][0]['requests'], 1)
        self.assertFalse(self.write(snapshot(2)))

    def test_updated_bucket_does_not_duplicate_old_request(self):
        self.write(snapshot())
        s = snapshot(2)
        s['series'][0].update(completed=2, output_tokens=12, usage_known=2)
        s['totals'].update(completed=2, output_tokens=12, usage_known=2)
        self.write(s)
        result = self.query()
        self.assertEqual(result['summary']['output_tokens'], 12)
        self.assertEqual(result['coverage']['model_pool_requests'], 1)
        self.assertEqual(result['coverage']['counter_requests'], 2)

    def test_restart_keeps_two_epochs_and_same_request_id_is_scoped(self):
        self.write(snapshot())
        self.write(snapshot(epoch='c'*32, started=NOW, at=NOW+1, output=5))
        result = self.query()
        self.assertEqual(result['summary']['output_tokens'], 12)
        self.assertEqual(result['coverage']['epochs'], 2)
        self.assertEqual(result['pools'][0]['requests'], 2)
        self.assertFalse(self.write(snapshot(99)))

    def test_partial_time_series_not_invented_from_epoch_total(self):
        s = snapshot()
        s['totals']['output_tokens'] = 700
        self.write(s)
        result = self.query()
        self.assertEqual(result['summary']['output_tokens'], 700)
        self.assertEqual(sum(b['output_tokens'] for b in result['series']), 7)
        self.assertLess(result['coverage']['totals_since'], result['coverage']['time_series_since'])
        self.assertEqual(self.query('60')['summary']['output_tokens'], 7)

    def test_missing_usage_is_not_zero(self):
        s = snapshot(output=None)
        s['recent'][0]['usage']['input_tokens'] = None
        s['series'][0]['input_tokens'] = 0
        s['series'][0]['input_tokens_known'] = 0
        s['totals']['input_tokens'] = 0
        self.write(s)
        for minutes in ('all', '60'):
            result = self.query(minutes)
            self.assertIsNone(result['summary']['output_tokens'])
            self.assertIsNone(result['summary']['input_tokens'])
            self.assertIsNone(result['summary']['cache_read_tokens'])

    def test_reported_zero_is_preserved(self):
        self.write(snapshot(output=0))
        self.assertEqual(self.query()['summary']['output_tokens'], 0)
        self.assertEqual(self.query('60')['summary']['output_tokens'], 0)

    def test_long_window_and_custom_range(self):
        self.write(snapshot(at=NOW-86400, started=NOW-90000))
        self.write(snapshot(2, started=NOW-90000, output=13, rid='d'*32))
        full = self.query('10080')
        self.assertEqual(sum(b['output_tokens'] for b in full['series']), 20)
        custom = self.query(start=NOW-3600, end=NOW+1)
        self.assertEqual(custom['summary']['output_tokens'], 13)
        self.assertLessEqual(len(full['series']), history.MAX_POINTS)
        self.assertGreater(full['resolution_s'], 60)

    def test_database_reopen_and_private_permissions(self):
        self.write(snapshot())
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.query()['ok'])
        self.assertTrue(self.query()['ok'])

    def test_symlink_is_refused(self):
        target = Path(self.tmp.name)/'target'
        target.write_text('unchanged')
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.write(snapshot())
        self.assertEqual(target.read_text(), 'unchanged')
        self.assertFalse(self.query()['ok'])

    def test_history_ingress_fences_and_idempotent_recovery(self):
        p = Path(self.tmp.name)/'snapshot.json'
        s = snapshot()
        # A ledger transaction may survive a later snapshot replace failure.
        history.record(s, path=history.database_path(p), now=NOW)
        self.assertTrue(ingest(json.dumps(s).encode(), p, now=NOW))
        self.assertFalse(ingest(json.dumps(s).encode(), p, now=NOW))
        result = history.query('all', path=history.database_path(p), now=NOW+1)
        self.assertEqual(result['pools'][0]['requests'], 1)
        self.assertEqual(json.loads(p.read_text())['history_state'], 'recorded')

    def test_storage_failure_does_not_break_live_ingestion(self):
        p = Path(self.tmp.name)/'snapshot.json'
        with patch.object(history, 'record', side_effect=sqlite3.OperationalError('fixture')):
            self.assertTrue(ingest(json.dumps(snapshot()).encode(), p, now=NOW))
        self.assertEqual(json.loads(p.read_text())['history_state'], 'degraded')

    def test_content_is_not_stored(self):
        s = snapshot()
        s['prompt'] = 'PRIVATE SECRET PROMPT'
        s['recent'][0]['completion'] = 'PRIVATE SECRET COMPLETION'
        self.write(s)
        with closing(sqlite3.connect(self.path)) as db:
            text = ' '.join(db.iterdump())
        self.assertNotIn('PRIVATE SECRET', text)

    def test_ingestion_gaps_reported(self):
        self.write(snapshot(at=NOW-100))
        self.write(snapshot(2))
        self.assertEqual(self.query()['coverage']['ingestion_gaps'], 1)

    def test_bad_ranges_rejected_before_storage_access(self):
        for kw in ({'start': 'nan'}, {'end': NOW+100}, {'start': NOW+2, 'end': NOW+1}, {'resolution': 7}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.query(**kw)

    def test_quota_lookup_uses_observation_time_not_minute_key(self):
        from admin.tests.test_capacity_intelligence import quota
        for sequence, at in enumerate((NOW-3620, NOW-3590), 1):
            frame = snapshot(sequence, at=at)
            frame['claude'] = quota(at)
            self.write(frame)
        # The newest minute key precedes this cutoff but its observation does not.
        previous = history.previous_quota(path=self.path, before=NOW-3595)
        self.assertEqual(previous['observed_at'], NOW-3620)

    def test_quota_lookup_inclusive_boundary_and_no_eligible_sample(self):
        from admin.tests.test_capacity_intelligence import quota
        frame = snapshot(at=NOW-3600)
        frame['claude'] = quota(NOW-3600)
        self.write(frame)
        self.assertEqual(history.previous_quota(path=self.path, before=NOW-3600)['observed_at'], NOW-3600)
        self.assertIsNone(history.previous_quota(path=self.path, before=NOW-3601))
        self.assertIsNone(history.previous_quota(path=self.path.with_name('absent.db'), before=NOW))

    def test_quota_lookup_refuses_invalid_or_inconsistent_timestamps(self):
        self.write(snapshot())
        for observed in (None, True, 'old', 0, -1, float('nan'), float('inf'), NOW+1, NOW-61):
            with self.subTest(observed=observed):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute('DELETE FROM quota_samples')
                    db.execute('INSERT INTO quota_samples VALUES (?,?)', (NOW, json.dumps({'observed_at': observed})))
                self.assertIsNone(history.previous_quota(path=self.path, before=NOW))

    def test_absent_history_is_explicit(self):
        result = self.query()
        self.assertFalse(result['ok'])
        self.assertEqual(result['state'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
