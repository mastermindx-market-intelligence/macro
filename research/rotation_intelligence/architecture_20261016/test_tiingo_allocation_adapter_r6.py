"""Contract-only cases: invented native-shaped source histories, NO vendor reads.
The isolated test shim is NOT the installed Data OS reader or exchange calendar.
"""
from dataclasses import replace
from datetime import datetime,date,timezone
from collections import OrderedDict
import hashlib
import unittest
from lib.dataos.tiingo_reader import TiingoResearchHistory
from lib.nyse_calendar import session_n_back,sessions_between
from tiingo_allocation_adapter_r6 import project_histories, Refused, public_summary, SECTORS, INPUTS

ANCHOR="2026-09-30"
CUTOFF="2026-10-17T13:00:00+00:00"
SHA="a"*64
OTHER="b"*64

def fixtures():
    d=date.fromisoformat(ANCHOR)
    days=tuple(x.isoformat() for x in sessions_between(session_n_back(d,252),d))
    out={}
    for j,t in enumerate(INPUTS):
        rows=[]
        for i,day in enumerate(days):
            rows.append(dict(ticker_vendor=t, market_date=day,source_vendor="tiingo",dataset_source="eod-bars",
                         source_sha256=SHA,source_receipt_id=OTHER,source_view_schema="mastermind.tiingo.research_views.v2",
                         source_observed_at_utc="2026-10-12T18:00:00+00:00", adjustment_asof_utc="2026-10-12T18:00:00+00:00",
                         timestamp_source="vendor_market_date_only",vendor_historical_availability="UNVERIFIED",
                         adjustment_basis_detail="vendor_adjusted_not_historical_vintage",
                         pit_backtest_eligible=False,dataos_identity_admitted=False,source_rights_admitted=False,
                         close_raw=100+j+i/10,close_tradj=100+j+i/10,split_factor=1.0,dividend_cash=0.0))
        out[t]=TiingoResearchHistory(source="eod-bars",vendor_symbol=t,start_market_date=days[0],
                  end_market_date=ANCHOR,observed_before_utc=CUTOFF,rows=tuple(rows),
                  source_partitions=(("2026-10-12",OTHER),),identical_overlap_dates=0)
    return out,days

def corrupt(history,ticker=None,**changes):
    d=dict(history.__dict__);d.update(changes);return TiingoResearchHistory(**d)

class Projection(unittest.TestCase):
    def setUp(self):self.data,self.days=fixtures()
    def invoke(self,ds=None,**kwargs):return project_histories(self.data if ds is None else ds,
                         anchor_market_day=ANCHOR, capture_cutoff_utc=CUTOFF, **kwargs)
    def test_complete_13_native_research_histories(self):
        v=self.invoke()
        self.assertEqual(len(v.series),13)
        self.assertEqual(len(v.session_days),253)
        self.assertEqual(tuple(x.symbol for x in v.series),INPUTS)
        self.assertEqual(v.series[0].values[0],100.0)
        self.assertEqual(len(v.series[0].values[-64:]),64)
        self.assertEqual(v.evidence_mode,"RETROSPECTIVE_EXPLORATORY_NOT_PIT")
        self.assertFalse(v.historical_pit_admitted or v.may_rank or v.may_size or v.may_gate)
        self.assertEqual(len(v.digest_sha256),64)
        self.assertEqual(len(v.series[0].receipt_refs),1)
        self.assertEqual(self.invoke().digest_sha256,v.digest_sha256)
    def test_summary_contains_no_values(self):
        v=self.invoke();s=public_summary(v)
        self.assertEqual(s['symbols'],list(INPUTS))
        self.assertEqual(s['sessions'],253)
        self.assertEqual(s['source_use'],'UNQUALIFIED')
        self.assertNotIn('values',str(s))
        self.assertNotIn('close_tradj',str(s))
        self.assertFalse(s['historical_pit_admitted'])
    def test_missing_bil_refused(self):
        del self.data['BIL'];self.assertRaisesRegex(Refused,'EXACT_13',self.invoke)
    def test_unexpected_extra_symbol_refused(self):
        self.data['SOXX']=self.data['BIL'];self.assertRaisesRegex(Refused,'EXACT_13',self.invoke)
    def test_non_native_object_refused(self):
        self.data['BIL']=dict(rows=[]);self.assertRaisesRegex(Refused,'NATIVE_HISTORY',self.invoke)
    def test_history_date_cannot_extend_into_future_outcomes(self):
        self.data['BIL']=replace(self.data['BIL'],end_market_date='2026-10-01')
        self.assertRaisesRegex(Refused,'EXACT_ORIGIN_END',self.invoke)
    def test_wrong_capture_vintage_refused(self):
        self.data['BIL']=replace(self.data['BIL'],observed_before_utc='2026-10-18T13:00:00+00:00')
        self.assertRaisesRegex(Refused,'CAPTURE_CUTOFF',self.invoke)
    def test_hindsight_cannot_be_promoted_by_forging_flags(self):
        for changes in ({'pit_backtest_eligible':True},{'historical_identity_admitted':True},
                        {'redistribution_admitted':True},{'market_session_completeness_proven':True},
                        {'authority':'PRODUCTION'}):
            with self.subTest(changes=changes):
                self.data['BIL']=replace(fixtures()[0]['BIL'],**changes)
                self.assertRaisesRegex(Refused,'AUTHORITY',self.invoke)
    def test_source_kind_and_id_cannot_change(self):
        for changes in ({'source':'fund-daily'},{'vendor_symbol':'SPY'},{'source_partitions':()},
                        {'source_partitions':(('2026-10-12','invalid'),)},
                        {'source_partitions':(('2026-10-12',OTHER),('2026-10-12',OTHER))}):
            with self.subTest(changes=changes):
                self.data['BIL']=replace(fixtures()[0]['BIL'],**changes)
                self.assertRaises(Refused,self.invoke)
    def test_missing_mid_calendar_session_refused(self):
        x=self.data['BIL'];self.data['BIL']=replace(x,rows=x.rows[:20]+x.rows[21:])
        self.assertRaisesRegex(Refused,'SESSION_COVERAGE',self.invoke)
    def test_duplicate_session_refused(self):
        x=self.data['BIL'];self.data['BIL']=replace(x,rows=x.rows[:25]+(x.rows[24],)+x.rows[25:])
        self.assertRaisesRegex(Refused,'SESSION_COVERAGE',self.invoke)
    def test_adjustment_vintage_change_refused(self):
        x=self.data['BIL'];b=dict(x.rows[-1],adjustment_asof_utc='2026-10-16T18:00:00+00:00',source_observed_at_utc='2026-10-16T18:00:00+00:00')
        self.data['BIL']=replace(x,rows=x.rows[:-1]+(b,))
        self.assertRaisesRegex(Refused,'MIXED_ADJUSTMENT_VINTAGE',self.invoke)
    def test_bad_adjusted_price_refused(self):
        for bad in (None,0,-1,True,float('nan'),float('inf'),"100"):
            with self.subTest(bad=bad):
                x=fixtures()[0]['BIL'];self.data['BIL']=replace(x,rows=x.rows[:-1]+(dict(x.rows[-1],close_tradj=bad),))
                self.assertRaisesRegex(Refused,'INVALID_ADJUSTED_CLOSE',self.invoke)
    def test_source_capture_clock_future_refused(self):
        x=self.data['BIL'];self.data['BIL']=replace(x,rows=x.rows[:-1]+(dict(x.rows[-1],source_observed_at_utc='2026-11-01T14:00:00+00:00',adjustment_asof_utc='2026-11-01T14:00:00+00:00'),))
        self.assertRaisesRegex(Refused,'SOURCE_AFTER_CAPTURE_CUTOFF',self.invoke)
    def test_source_manifest_forged_pit_eligible_refused(self):
        x=self.data['BIL'];self.data['BIL']=replace(x,rows=x.rows[:-1]+(dict(x.rows[-1],pit_backtest_eligible=True),))
        self.assertRaisesRegex(Refused,'ROW_AUTHORITY',self.invoke)
    def test_ticker_mismatch_refused(self):
        x=self.data['BIL'];self.data['BIL']=replace(x,rows=x.rows[:-1]+(dict(x.rows[-1],ticker_vendor='SPY'),))
        self.assertRaisesRegex(Refused,'ROW_SOURCE',self.invoke)
    def test_does_not_backdate_current_capture_into_historical_forecast(self):
        v=self.invoke()
        self.assertTrue(v.as_known_historically is False)
        self.assertEqual(v.anchor_market_day,ANCHOR)
        self.assertEqual(v.capture_cutoff_utc,CUTOFF)
        self.assertNotIn('forecast',public_summary(v))
    def test_invalid_calendar_date_refused(self):
        self.assertRaisesRegex(Refused,'ANCHOR_SESSION',lambda: project_histories(self.data,anchor_market_day='2026-09-27',capture_cutoff_utc=CUTOFF))
    def test_invalid_capture_clock_refused(self):
        self.assertRaisesRegex(Refused,'UTC_CUTOFF',lambda:project_histories(self.data,anchor_market_day=ANCHOR,capture_cutoff_utc='2026-10-17T13:00:00'))

if __name__=='__main__':unittest.main()
