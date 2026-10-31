"""Synthetic-only causal first-seen/revision guards, not live market evidence."""
from datetime import date, timedelta
from pathlib import Path
import sys
import math
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.entry_radar.replay.oscillator_mtf_research import oscillator_events


def synthetic_long_prefix(late_revision=False):
    # Forty synthetic complete RTH sessions, each with three 120m bars plus
    # an explicit 30m stub.  No real prices or vendor observation is used.
    rows, eligibility = [], {}
    days = pd.bdate_range('2026-01-05', periods=40)
    for day in days:
        session = day.date().isoformat()
        opening = pd.Timestamp(session+' 09:30', tz='America/New_York').tz_convert('UTC')
        prior = (day - pd.Timedelta(days=1)).date().isoformat()
        for ordinal in range(3):
            start = opening + pd.Timedelta(minutes=ordinal*120)
            end = start + pd.Timedelta(minutes=120)
            known = end + pd.Timedelta(seconds=2)
            i = len(rows)
            price = 100. + .15*i + 3.*math.sin(i/4.)
            row = dict(schema='macro.rs_oscillator_mtf_bars.v1',symbol='A',session_date=session,
                       grain_minutes=120,bar_start_utc=start.isoformat(),bar_end_utc=end.isoformat(),
                       known_at_utc=known.isoformat(),source_sha256='a'*64,
                       ohlcv=dict(open=price,high=price+1.,low=price-1.,close=price,volume=100_000.),
                       status='FULL_KNOWN',refusals=[],source_admitted=False)
            rows.append(row)
            eligibility[('A',end.isoformat())] = dict(is_leader=True,
                known_at_utc=(opening-pd.Timedelta(days=1)).isoformat(),
                asof_session=prior,expected_prior_session=prior,receipt_sha256='b'*64)
        stub_start=opening+pd.Timedelta(minutes=360)
        stub_end=stub_start+pd.Timedelta(minutes=30)
        rows.append(dict(schema='macro.rs_oscillator_mtf_bars.v1',symbol='A',
                         session_date=session,grain_minutes=120,
                         bar_start_utc=stub_start.isoformat(),bar_end_utc=stub_end.isoformat(),
                         known_at_utc=None,source_sha256=None,ohlcv=None,
                         status='STUB_EXCLUDED',refusals=['NONFULL_SESSION_STUB'],
                         source_admitted=False,stub_minutes=30))
    late = pd.Timestamp(rows[-1]['bar_end_utc']) + pd.Timedelta(days=1)
    if late_revision:
        rows[1]['known_at_utc'] = late.isoformat()
    return rows,eligibility,late


def owner_predecessors(rows):
    dates = sorted({x['session_date'] for x in rows})
    return {date.fromisoformat(current): date.fromisoformat(previous)
            for previous, current in zip(dates, dates[1:])}


@pytest.mark.parametrize("indicator", ["CANON_RSI_MACD", "PRICE_MACD_RSI_PROXY"])
def test_future_early_bar_revision_cannot_backdate_canonical_oscillator(indicator):
    original, eligibility, late = synthetic_long_prefix()
    base = oscillator_events(bars=original,indicator=indicator,eligibility=eligibility,
                             prior_session_by_day=owner_predecessors(original),
                             decision_cutoff_utc=(late+pd.Timedelta(hours=2)).isoformat())
    assert any(x['signal'] is not None and pd.Timestamp(x['issued_at_utc']) < late for x in base)
    revised, eligibility, late = synthetic_long_prefix(late_revision=True)
    revised[1]['ohlcv']['close'] += 2.0
    revised[1]['ohlcv']['high'] = max(revised[1]['ohlcv']['high'], revised[1]['ohlcv']['close'])
    revised[1]['source_sha256'] = 'c'*64
    events = oscillator_events(bars=revised,indicator=indicator,eligibility=eligibility,
                               prior_session_by_day=owner_predecessors(revised),
                               decision_cutoff_utc=(late+pd.Timedelta(hours=2)).isoformat())
    assert not any(x['signal'] is not None and pd.Timestamp(x['issued_at_utc']) < late for x in events), 'prior later-known revision was backdated'
    assert any(x['state'] == 'SOURCE_HISTORICAL_REVISION_UNAVAILABLE' for x in events)


def test_later_genuine_post_revision_session_can_be_classified_again():
    rows, eligibility, _ = synthetic_long_prefix()
    revision_known = pd.Timestamp(rows[90]['bar_end_utc']) - pd.Timedelta(hours=1)
    rows[1]['known_at_utc'] = revision_known.isoformat()
    end_cutoff = pd.Timestamp(rows[-1]['bar_end_utc']) + pd.Timedelta(days=1)
    events = oscillator_events(bars=rows, indicator='CANON_RSI_MACD',
                               eligibility=eligibility,
                               prior_session_by_day=owner_predecessors(rows),
                               decision_cutoff_utc=end_cutoff.isoformat())
    assert all(ev['signal'] is None for ev in events[2:90])
    assert any(ev['signal'] is not None for ev in events[91:])
