from datetime import date
from scripts.research.market_navigator_daily_audit import inspect_bytes


def test_daily_low_cannot_claim_close_or_intraday_order():
    raw = b'DATE,OPEN,HIGH,LOW,CLOSE\n10/20/2026,7,8,6,7\n10/21/2026,6,7,5,6\n10/22/2026,5,7,4,5\n'
    x = inspect_bytes(raw, symbol='VIX1D', cutoff=date(2026,10,21))
    t = x['threshold_6_88_descriptive_only']
    assert t['daily_low_at_or_below'] == 2
    assert t['daily_close_at_or_below'] == 1
    assert t['low_hit_but_close_above'] == 1
    assert x['future_rows_excluded'] == 1
    assert not x['operational_pit'] and not x['supports_intraday_trigger_ordering']


def test_malformed_nonfinite_and_duplicate_rows_are_disclosed():
    raw = b'DATE,OPEN,HIGH,LOW,CLOSE\n10/20/2026,7,8,6,7\n10/20/2026,7,8,6,7\n10/21/2026,7,8,6,nan\nbad,1,2,0,1\n'
    x = inspect_bytes(raw, symbol='VIX1D', cutoff=date(2026,10,21))
    assert x['duplicate_dates'] == 1
    assert x['malformed_rows'] == 2
