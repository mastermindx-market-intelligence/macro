"""Tests for the four-phase factor build-out (research/QUANT_FACTOR_EXPANSION.md):
commodity carry, EIA supply, FINRA short interest, SEC Form-4 insider.

Pure-logic tests run offline; integration checks run only when a real cache
exists in this environment."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.commodity_carry import _enumerate_symbols, _reconstruct  # noqa: E402
from collectors.finra import _candidate_dates, _last_business_day  # noqa: E402
from collectors.sec_insider import _candidate_quarters  # noqa: E402
from lib import config  # noqa: E402


# --- Phase 1: commodity carry -----------------------------------------------
def _contract(deliv_y: int, deliv_m: int, level: float, n: int = 120) -> tuple[int, int, pd.Series]:
    idx = pd.bdate_range("2026-01-02", periods=n)
    return (deliv_y, deliv_m, pd.Series(level, index=idx, dtype=float))


def test_carry_reconstruct_backwardation() -> None:
    # front (Jul) priced ABOVE second (Aug) => positive roll yield (backwardation)
    contracts = [_contract(2026, 7, 85.0), _contract(2026, 8, 83.0), _contract(2026, 9, 81.0)]
    df = _reconstruct(contracts, history_d=200)
    assert not df.empty and "roll_yield_ann" in df.columns
    assert df["roll_yield_ann"].iloc[-1] > 0           # backwardated
    assert df["front"].iloc[-1] == 85.0 and df["second"].iloc[-1] == 83.0


def test_carry_reconstruct_contango() -> None:
    contracts = [_contract(2026, 7, 80.0), _contract(2026, 8, 82.0)]  # front below second
    df = _reconstruct(contracts, history_d=200)
    assert df["roll_yield_ann"].iloc[-1] < 0           # contango


def test_carry_reconstruct_needs_two() -> None:
    assert _reconstruct([_contract(2026, 7, 80.0)], 200).empty


def test_enumerate_symbols_format() -> None:
    syms = _enumerate_symbols("CL", ".NYM", 2, 2)
    assert len(syms) == 5
    assert all(re.match(r"CL[FGHJKMNQUVXZ]\d\d\.NYM", s) for s, _, _ in syms)


# --- Phase 3: FINRA short interest ------------------------------------------
def test_last_business_day_skips_weekend() -> None:
    import datetime as dt
    assert _last_business_day(dt.date(2026, 5, 17)) == dt.date(2026, 5, 15)  # Sun -> Fri
    assert _last_business_day(dt.date(2026, 5, 15)).weekday() < 5


def test_finra_candidate_dates_descending() -> None:
    dates = _candidate_dates(6)
    assert len(dates) == 6
    assert dates == sorted(dates, reverse=True)
    assert all(re.match(r"\d{4}-\d{2}-\d{2}", d) for d in dates)


# --- Phase 4: SEC insider ----------------------------------------------------
def test_insider_parse_synthetic() -> None:
    """Parse a synthetic SEC insider zip (real SUBMISSION/NONDERIV_TRANS schema):
    open-market P/S only, min-trade and universe filters, net aggregation."""
    import io
    import zipfile

    from collectors.sec_insider import _parse
    sub = ("ACCESSION_NUMBER\tFILING_DATE\tISSUERTRADINGSYMBOL\tISSUERNAME\n"
           "0001-A\t01-APR-2026\tAAPL\tApple Inc\n"
           "0002-A\t02-APR-2026\tAAPL\tApple Inc\n"
           "0003-A\t03-APR-2026\tXYZ\tXyz Corp\n"
           "0004-A\t04-APR-2026\tTINY\tTiny Co\n")
    tr = ("ACCESSION_NUMBER\tTRANS_CODE\tTRANS_SHARES\tTRANS_PRICEPERSHARE\tTRANS_ACQUIRED_DISP_CD\n"
          "0001-A\tP\t10000\t150\tA\n"
          "0001-A\tP\t5000\t150\tA\n"
          "0002-A\tS\t8000\t150\tD\n"
          "0003-A\tS\t20000\t50\tD\n"
          "0003-A\tA\t999999\t50\tA\n"      # grant — must be excluded
          "0004-A\tP\t1000\t5\tA\n")        # $5k < min_trade_usd — must be dropped
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026q1_SUBMISSION.tsv", sub)
        z.writestr("2026q1_NONDERIV_TRANS.tsv", tr)
    buf.seek(0)
    out = _parse("2026q1", zipfile.ZipFile(buf), universe={"AAPL", "XYZ", "TINY"})
    assert out.loc["AAPL", "buy_usd"] == 15000 * 150
    assert out.loc["AAPL", "sell_usd"] == 8000 * 150
    assert out.loc["AAPL", "net_usd"] == (15000 - 8000) * 150
    assert out.loc["AAPL", "n_buys"] == 2 and out.loc["AAPL", "n_sells"] == 1
    assert out.loc["XYZ", "buy_usd"] == 0 and out.loc["XYZ", "sell_usd"] == 20000 * 50  # grant excluded
    assert "TINY" not in out.index                                                       # sub-threshold dropped


def test_insider_candidate_quarters() -> None:
    qs = _candidate_quarters(5)
    assert len(qs) == 5
    assert all(re.match(r"\d{4}q[1-4]", q) for q in qs)
    # strictly newest-first (each subsequent quarter is earlier)
    ords = [int(q[:4]) * 4 + int(q[-1]) for q in qs]
    assert ords == sorted(ords, reverse=True)


# --- integration checks (only if a real cache exists) -----------------------
def test_short_interest_factor_if_cache() -> None:
    if not (config.data_dir() / "finra" / "short_interest.parquet").exists():
        return
    from engine.equity_factors import compute_factors
    r = compute_factors()
    if r:
        assert "short_interest" in r["leaders"]
        # least-shorted leaders should have a positive factor z
        assert r["leaders"]["short_interest"][0]["z"] > 0


def test_eia_supply_read_if_cache() -> None:
    if not (config.data_dir() / "eia" / "crude_stocks.parquet").exists():
        return
    from scripts.build_commodities import _oil_supply_read
    s = _oil_supply_read()
    assert s is not None
    assert s["crude_stocks_mb"] > 0                                  # M bbl
    assert s["balance_word"] in ("tight", "ample", "balanced", "n/a")
    assert s["crude_z"] is None or isinstance(s["crude_z"], float)   # seasonal anomaly z
    assert s["caveat_en"] and "≠" in s["caveat_en"]                  # display-only honesty layer


def test_carry_read_if_cache() -> None:
    if not (config.data_dir() / "commodity_carry" / "oil.parquet").exists():
        return
    from scripts.build_commodities import _carry_read
    c = _carry_read("oil")
    assert c is not None and c["state"] in ("backwardation", "contango")


# --- Carry history admission regression (#34, 2026-11-12) ------------------
def _staggered_carry_contracts(far_start: str = "2026-10-01"):
    """The far contract is observed later but is never one of the nearest two."""
    idx = pd.bdate_range("2026-08-03", "2026-11-11")
    return [
        (2026, 11, pd.Series(np.linspace(84.0, 80.0, len(idx)), index=idx)),
        (2026, 12, pd.Series(82.0, index=idx)),
        (2027, 1, pd.Series(79.0, index=idx[idx >= far_start])),
    ]


def test_carry_late_unused_contract_preserves_history() -> None:
    # All six inputs have the same end. The existing end/cap contract is unchanged.
    for start in ("2026-08-04", "2026-08-17", "2026-09-01",
                  "2026-09-15", "2026-10-01", "2026-10-15"):
        contracts = _staggered_carry_contracts(start)
        expected = _reconstruct(contracts[:2], 200)
        actual = _reconstruct(contracts, 200)
        assert len(expected) == 73
        pd.testing.assert_frame_equal(actual, expected)


def test_carry_history_cap_preserves_eligible_tail() -> None:
    contracts = _staggered_carry_contracts()
    for cap in (1, 20, 30, 50, 200):
        expected = _reconstruct(contracts[:2], cap)
        pd.testing.assert_frame_equal(_reconstruct(contracts, cap), expected)
        assert len(expected) == min(cap, 73)


def test_carry_contract_order_does_not_set_history_start() -> None:
    import itertools
    contracts = _staggered_carry_contracts()
    expected = _reconstruct(contracts[:2], 200)
    for order in itertools.permutations(contracts):
        pd.testing.assert_frame_equal(_reconstruct(list(order), 200), expected)


def test_carry_does_not_emit_before_second_contract_exists() -> None:
    contracts = _staggered_carry_contracts()
    # With only one observed contract before October, no earlier pair exists.
    contracts[1] = (2026, 12, contracts[1][2].loc["2026-10-01":])
    result = _reconstruct(contracts, 200)
    assert result.index.min() == pd.Timestamp("2026-10-01")
    assert len(result) == 30
    # Nonoverlapping contracts never create a fabricated pair.
    separated = [contracts[0], (2027, 1, pd.Series(
        79.0, index=pd.bdate_range("2026-12-01", periods=25)))]
    assert _reconstruct(separated, 200).empty


def test_carry_retains_roll_price_and_month_gap_rules() -> None:
    idx = pd.bdate_range("2026-08-03", periods=30)
    front = pd.Series(-5.0, index=idx)  # legitimate negative futures quote
    second = pd.Series(80.0, index=idx)
    second.iloc[4:6] = [0.0, -1.0]  # existing nonpositive-second refusal
    pair = [(2026, 11, front), (2027, 1, second)]
    far = (2027, 3, pd.Series(90.0, index=idx[10:]))
    actual = _reconstruct(pair + [far], 200)
    expected = _reconstruct(pair, 200)
    pd.testing.assert_frame_equal(actual, expected)
    assert len(actual) == 28
    assert (actual["gap_months"] == 2).all()
    assert (actual["front"] == -5.0).all()
    assert np.allclose(actual["roll_yield_ann"], (-5.0 / 80.0 - 1.0) * 6.0)


def test_carry_date_pair_oracle() -> None:
    """Independent explicit date walk; use observed quotes, not the source loop."""
    rng = np.random.default_rng(341112)
    dates = pd.bdate_range("2026-03-02", periods=90)
    for _ in range(80):
        contracts = []
        for month in range(6, 11):
            start = int(rng.integers(0, 25))
            end = int(rng.integers(50, 91))
            quotes = pd.Series(rng.uniform(50, 150, end - start),
                               index=dates[start:end])
            contracts.append((2026, month, quotes))
        cap = int(rng.integers(1, 121))
        # Walk the independently known fixture calendar, then apply the same
        # documented calendar-tail cap before selecting observable quote pairs.
        observed_dates = {t for _, _, s in contracts for t in s.index}
        scan = [t for t in dates if min(observed_dates) <= t <= max(observed_dates)][-cap:]
        rows = []
        for t in scan:
            observed = [(year * 12 + month, float(s.loc[t]))
                        for year, month, s in contracts if t in s.index]
            if len(observed) < 2:
                continue
            (d1, p1), (d2, p2) = sorted(observed)[:2]
            rows.append({"date": t, "front": p1, "second": p2,
                         "roll_yield_ann": (p1 / p2 - 1.0) * 12.0 / (d2 - d1),
                         "gap_months": d2 - d1})
        expected = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()
        pd.testing.assert_frame_equal(_reconstruct(contracts, cap), expected)


def test_carry_force_fetch_and_weekly_cache_preserve_history(tmp_path, monkeypatch) -> None:
    """Real writer/cache code, synthetic quote fetches, no provider/network access."""
    from collectors import commodity_carry

    contracts = _staggered_carry_contracts()
    spec = [("near", 2026, 11), ("second", 2026, 12), ("far", 2027, 1)]
    quotes = {name: c[2] for (name, _, _), c in zip(spec, contracts)}
    expected = _reconstruct(contracts[:2], 200)
    cdir = tmp_path / "commodity_carry"
    cdir.mkdir()
    expected.to_parquet(cdir / "oil.parquet")
    monkeypatch.setattr(commodity_carry, "_cfg", lambda: {
        "contracts": {"oil": ["CL", ".NYM"]}, "months_back": 2,
        "months_fwd": 3, "history_d": 200})
    monkeypatch.setattr(commodity_carry.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(commodity_carry, "_enumerate_symbols", lambda *args: spec)
    monkeypatch.setattr(commodity_carry, "_fetch_contract", quotes.__getitem__)

    built = commodity_carry.fetch_carry(force=True)["oil"]
    pd.testing.assert_frame_equal(built, expected)
    pd.testing.assert_frame_equal(pd.read_parquet(cdir / "oil.parquet"), expected)

    def forbid_fetch(*args):
        raise AssertionError("fresh weekly cache must not contact the provider")

    monkeypatch.setattr(commodity_carry, "_fetch_contract", forbid_fetch)
    cached = commodity_carry.fetch_carry()["oil"]
    pd.testing.assert_frame_equal(cached, expected)
