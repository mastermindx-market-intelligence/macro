"""Price clocks follow the actual producer price, not the universe analysis clock."""
import ast
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import stock_technicals, technicals
from scripts import build_stock_library as library


def closes(end="2026-10-08", rows=310):
    return pd.Series(np.linspace(100, 131, rows), index=pd.bdate_range(end=end, periods=rows))


def ohlcv(close):
    return pd.DataFrame({"close": close, "high": close + 1, "low": close - 1,
                         "volume": pd.Series(1_000_000.0, index=close.index)})


def seed(close):
    return {"asof": str(close.index[-1].date()),
            "tech": {**technicals.snapshot(close), "price_asof": str(close.index[-1].date())},
            "valuation": {"asof": str(close.index[-1].date())}}


def test_actual_one_binds_thin_price_without_rewriting_record_clock(monkeypatch):
    close = closes()
    monkeypatch.setattr(library, "analyze", lambda *a, **kw: {"ladder": {"state": "WATCH"}})
    monkeypatch.setattr(library, "seasonality", lambda *a: {})
    monkeypatch.setattr(library, "season_line", lambda *a, **kw: None)
    monkeypatch.setattr(library.ticker_alerts, "build_feed", lambda *a, **kw: [])
    monkeypatch.setattr(library.ticker_alerts, "compact_feed", lambda *a, **kw: [])
    from engine import anticipation, roc_blowoff
    monkeypatch.setattr(anticipation, "anticipate", lambda *a, **kw: None)
    monkeypatch.setattr(roc_blowoff, "assess", lambda *a, **kw: None)
    rec = library._one("TEST", close, None, "Test", "Test")
    assert rec["tech"]["price"] == technicals.snapshot(close)["price"]
    assert rec["tech"]["price_asof"] == "2026-10-08"
    assert rec["asof"] == "2026-10-08"
    assert "currency" not in rec["tech"]


def test_older_actual_rich_price_replaces_only_its_own_clock():
    recent, older = closes(), closes("2026-09-25") * 0.7
    rec = seed(recent)
    assert rec["tech"]["price"] != stock_technicals.snapshot(older)["price"]
    rec["tech"]["thin_only"] = "preserved"
    library._enrich_stock_technicals(rec, recent, ohlcv(older), None)
    assert rec["tech"]["price"] == stock_technicals.snapshot(older)["price"]
    assert rec["tech"]["price_asof"] == "2026-09-25"
    assert rec["tech"]["thin_only"] == "preserved"
    assert rec["asof"] == rec["valuation"]["asof"] == "2026-10-08"
    assert "currency" not in rec["tech"]


@pytest.mark.parametrize("store", [None, pd.DataFrame({"close": [1.0]})])
def test_actual_close_only_fallback_uses_its_supplied_series(store):
    close = closes()
    rec = seed(close)
    library._enrich_stock_technicals(rec, close, store, None)
    assert rec["tech"]["price"] == stock_technicals.snapshot(close)["price"]
    assert rec["tech"]["price_asof"] == "2026-10-08"


@pytest.mark.parametrize("last", [np.nan, "bad"])
def test_rich_numeric_filter_and_clock_select_the_same_last_valid_bar(last):
    close = closes().astype(object)
    close.iloc[-1] = last
    rec = seed(closes())
    library._enrich_stock_technicals(rec, close, None, None)
    valid = pd.to_numeric(close, errors="coerce").astype(float).dropna()
    assert rec["tech"]["price"] == stock_technicals.snapshot(valid)["price"]
    assert rec["tech"]["price_asof"] == str(valid.index[-1].date())
    assert rec["asof"] == "2026-10-08"


def test_rich_invalid_price_cannot_inherit_the_thin_clock():
    close = closes()
    close.iloc[-1] = np.inf
    rec = seed(closes())
    library._enrich_stock_technicals(rec, close, None, None)
    assert rec["tech"]["price"] is None
    assert "price_asof" not in rec["tech"]


def test_rich_price_cannot_inherit_an_unqualified_thin_currency():
    rec = seed(closes())
    rec["tech"]["currency"] = "USD"
    library._enrich_stock_technicals(rec, closes("2026-09-25") * 0.7, None, None)
    assert rec["tech"]["price"] == 91.7
    assert rec["tech"]["price_asof"] == "2026-09-25"
    assert "currency" not in rec["tech"]


@pytest.mark.parametrize("price", [None, True, "131", np.nan, np.inf, -1, 0, 999])
def test_invalid_or_mismatched_price_has_no_borrowed_clock(price):
    original = {"price": price, "price_asof": "2099-01-01", "other": "untouched"}
    result = library._bind_price_clock(original, closes())
    assert "price_asof" not in result
    assert result["price"] is price
    assert result["other"] == "untouched"
    assert original["price_asof"] == "2099-01-01"


@pytest.mark.parametrize("index", [pd.RangeIndex(3),
    pd.DatetimeIndex(["2026-10-08", "2026-10-07", "2026-10-06"]),
    pd.DatetimeIndex(["2026-10-06", "2026-10-08", "2026-10-08"]),
    pd.DatetimeIndex(["2026-10-06", "2026-10-07", pd.NaT])])
def test_ambiguous_or_missing_calendar_index_is_not_sorted_or_guessed(index):
    close = pd.Series([100.0, 120.0, 131.0], index=index)
    assert "price_asof" not in library._bind_price_clock({"price": 131.0}, close)


def test_valid_clock_keeps_source_calendar_date_and_python_price_rounding():
    close = pd.Series([100.0, 131.005], index=pd.date_range("2026-10-07 23:30", periods=2,
                                                        tz="America/New_York"))
    result = library._bind_price_clock({"price": round(131.005, 2)}, close)
    assert result["price_asof"] == "2026-10-08"
    assert result["price"] == round(131.005, 2)


@pytest.mark.parametrize("failed", ["snapshot", "squeeze"])
def test_failed_actual_enrichment_preserves_the_entire_prior_pair(monkeypatch, failed):
    rec = seed(closes())
    before = copy.deepcopy(rec)
    def fail(*a, **kw):
        raise RuntimeError("injected " + failed)
    target = library.stock_technicals if failed == "snapshot" else library.vol_squeeze
    monkeypatch.setattr(target, "snapshot" if failed == "snapshot" else "assess", fail)
    with pytest.raises(RuntimeError, match="injected"):
        library._enrich_stock_technicals(rec, closes("2026-09-25"), None, None)
    assert rec == before


def test_real_main_calls_the_same_tested_enrichment_boundary():
    tree = ast.parse(Path(library.__file__).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n for n in ast.walk(main) if isinstance(n, ast.Call) and
             isinstance(n.func, ast.Name) and n.func.id == "_enrich_stock_technicals"]
    assert len(calls) == 1
    assert [n.id for n in calls[0].args] == ["rec", "close", "_ohlcv", "bench"]
