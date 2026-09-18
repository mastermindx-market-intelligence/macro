"""Synthetic extractor checks; no historical outcomes read."""
import json, unittest
from types import SimpleNamespace
import recorded_context_join as m

class ExtractorTests(unittest.TestCase):
    def owner(self):
        def parse(d):
            rows = [dict(lane='buy', ticker=r['ticker'], position=i) for i,r in enumerate(d.get('buy',[]))]
            return dict(as_of=d['as_of'],rank_by=d.get('rank_by'),rows=rows)
        return SimpleNamespace(LANES=['buy'],_board_to_record=parse,_row_features=lambda r: r)
    def test_extractor_returns_archived_values_and_refs(self):
        raw = json.dumps(dict(as_of='2026-06-30',rank_by='fixture',buy=[dict(ticker='A',entry_signal=dict(horizon=dict(d3=.58,d21=-.2),confidence=41.4))])).encode()+b'\n'
        result = m.snapshot_context(raw,self.owner())
        self.assertIsNotNone(result,'unfinished extractor must not return None')
        self.assertEqual(len(result),1)
        self.assertEqual(result.iloc[0].recorded_horizon_d21,-.2)
        self.assertTrue(result.iloc[0].recorded_horizon_d63 is None or __import__('pandas').isna(result.iloc[0].recorded_horizon_d63))
        self.assertEqual(result.iloc[0].recorded_confidence,41.4)
        self.assertEqual(result.iloc[0].snapshot_position,0)
        self.assertEqual(len(result.iloc[0].snapshot_record_sha256),64)
    def test_duplicate_snapshots_refused(self):
        raw = json.dumps(dict(as_of='2026-06-30',buy=[dict(ticker='A')])).encode()+b'\n'
        with self.assertRaises(ValueError): m.snapshot_context(raw+raw,self.owner())

if __name__ == '__main__': unittest.main(verbosity=2)
