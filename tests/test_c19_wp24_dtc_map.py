"""C19 WP24 DQ4 — the narrative-rotation crowding block reads days-to-cover by TICKER.

`collectors/finra.py` writes the short-interest snapshot ticker-INDEXED, but
`compute_narrative_rotation` keyed its days-to-cover map by `si.columns[0]` —
a data column (short_shares) — so every `dtc_map.get(<ticker>)` was None and the
context-only `avg_days_to_cover` never reached a basket's crowding extension.
Keying it positionally would also have averaged FINRA's 999.99 censored sentinel
(average daily volume ~0) into that mean as if it were a measurement.

`_dtc_map` now keys by the index (or a `ticker` column if a writer resets it) and
drops a censored value: the collector's `dtc_capped` flag, else
days_to_cover >= DTC_SENTINEL.

Every test is hermetic: config.data_dir points at tmp_path and the collector's
network entry points are monkeypatched, so nothing touches the real data/ tree.
"""
from __future__ import annotations

import inspect
import math

import pandas as pd
import pytest

from collectors import finra
from engine import narrative_rotation as nr
from engine import theme_crowding as tc
from engine.narrative_rotation import _dtc_map
from engine.short_volume import DTC_SENTINEL
from lib import config


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


def _si_snapshot(settlement: str) -> pd.DataFrame:
    df = pd.DataFrame({
        "ticker": ["AAA", "BBB", "ZZZ"],
        "short_shares": [1000.0, 300.0, 50.0],
        "prev_short_shares": [900.0, 300.0, 50.0],
        "avg_daily_vol": [200.0, 100.0, 0.0],
        "days_to_cover": [5.0, 3.0, 999.99],
        "si_change_pct": [11.1, 0.0, 0.0],
    })
    df["settlement_date"] = settlement
    return df.set_index("ticker")


@pytest.fixture
def collector_snapshot(data_root, monkeypatch) -> pd.DataFrame:
    """The snapshot exactly as the real collector writes it."""
    monkeypatch.setattr(finra, "_latest_settlement", lambda: "2026-09-30")
    monkeypatch.setattr(finra, "_snapshot", _si_snapshot)
    monkeypatch.setattr(finra, "_universe_tickers", lambda: set())
    finra.fetch_short_interest(force=True)
    return pd.read_parquet(data_root / "finra" / "short_interest.parquet")


def test_collector_snapshot_is_keyed_by_ticker_and_drops_the_sentinel(collector_snapshot):
    assert collector_snapshot.index.name == "ticker", "precondition: the writer indexes by ticker"
    assert _dtc_map(collector_snapshot) == {"AAA": 5.0, "BBB": 3.0}


def test_ticker_column_variant_is_keyed_by_ticker(collector_snapshot):
    assert _dtc_map(collector_snapshot.reset_index()) == {"AAA": 5.0, "BBB": 3.0}


def test_capped_flag_excludes_a_row_below_the_sentinel():
    si = pd.DataFrame(
        {"days_to_cover": [5.0, 40.0], "dtc_capped": [False, True]},
        index=pd.Index(["AAA", "BBB"], name="ticker"),
    )
    assert _dtc_map(si) == {"AAA": 5.0}


def test_sentinel_excluded_without_the_flag_column():
    si = pd.DataFrame(
        {"days_to_cover": [5.0, 999.99, DTC_SENTINEL]},
        index=pd.Index(["AAA", "ZZZ", "YYY"], name="ticker"),
    )
    assert _dtc_map(si) == {"AAA": 5.0}


def test_sentinel_excluded_even_when_the_flag_says_false():
    si = pd.DataFrame(
        {"days_to_cover": [5.0, 999.99], "dtc_capped": [False, False]},
        index=pd.Index(["AAA", "ZZZ"], name="ticker"),
    )
    assert _dtc_map(si) == {"AAA": 5.0}


def test_missing_flag_value_does_not_exclude_a_measurement():
    si = pd.DataFrame(
        {"days_to_cover": [5.0, 7.0], "dtc_capped": [None, False]},
        index=pd.Index(["AAA", "BBB"], name="ticker"),
    )
    assert _dtc_map(si) == {"AAA": 5.0, "BBB": 7.0}


def test_nan_and_non_numeric_are_dropped():
    si = pd.DataFrame(
        {"days_to_cover": [5.0, float("nan"), "n/a"]},
        index=pd.Index(["AAA", "BBB", "CCC"], name="ticker"),
    )
    assert _dtc_map(si) == {"AAA": 5.0}


@pytest.mark.parametrize("si", [None, pd.DataFrame({"short_shares": [1.0]}, index=["AAA"])])
def test_absent_snapshot_or_column_is_empty(si):
    assert _dtc_map(si) == {}


def test_basket_crowding_averages_only_uncensored_members(collector_snapshot):
    m = _dtc_map(collector_snapshot)
    dtc = [m.get(t) for t in ["AAA", "BBB", "ZZZ", "NOPE"]]
    out = tc.basket_crowding(None, None, None, dtc)
    assert out["extension"]["avg_days_to_cover"] == round((5.0 + 3.0) / 2, 1)
    assert not math.isclose(out["extension"]["avg_days_to_cover"], 999.99)


def test_compute_narrative_rotation_never_keys_positionally():
    src = inspect.getsource(nr.compute_narrative_rotation)
    assert "si.columns[0]" not in src
    assert "_dtc_map(si)" in src
