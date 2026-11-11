"""Tests for the per-MEMBER price state capture in scripts/fetch_finviz_themes.py.

Covers four contracts (commission 2026-11-11, lane 10, COO ruling 6 + amendment 1):
  (a) every field of a roster row equals a HAND-COMPUTED value from a synthetic
      price file — 50/200-row average ratios, 20/63/252-row high and low flags,
      60-session total return, last-row closes on both bases, row count, vintage,
      index membership/sector/weight with the snapshot's own date;
  (b) the roster is the UNION of vendor members and that night's S&P 500
      members: one row per DISTINCT ticker (a multi-membership ticker keeps one
      row with sorted membership keys), an index-only ticker carries null
      theme/subsector, and a LATER weight snapshot is never used;
  (c) immutability and determinism: a second run for the same session skips and
      leaves the file byte-identical; a fresh write of the same inputs is
      byte-identical (gzip mtime=0); no .tmp is left behind;
  (d) capture-only resilience: a short or missing price file yields nulls, not
      an error; a last price row older than the session keeps its REAL date; an
      exception inside the step never propagates to main().

All fixtures are synthetic parquets under tmp_path (pandas+pyarrow, both on the
owning step's install line). Zero network calls; every date is pinned.
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

import scripts.fetch_finviz_themes as fft
from scripts.fetch_finviz_themes import write_member_price_state

FETCHED_AT = "2026-11-11T22:30:41+00:00"
ASOF = "2026-11-11"

TREE = [
    {"key": "tech", "theme": "Technology", "subsectors": [
        {"key": "aicompute", "name": "AI Compute", "members": ["AAA", "DECK"]},
        {"key": "fintech", "name": "Fintech", "members": ["DECK", "SHORT"]},
    ]},
    {"key": "energy", "theme": "Energy", "subsectors": [
        {"key": "oilservices", "name": "Oil Services", "members": ["NOFILE"]},
    ]},
]
#: vendor distinct = AAA, DECK, SHORT, NOFILE; sp500 active = AAA, IDXONLY
EXPECTED_ROWS = 5


def _write_yahoo(yahoo_dir: Path, ticker: str, closes: list[float],
                 last_date: str, *, close_price_last: float | None = None,
                 start: str = "2025-01-01") -> None:
    """One synthetic data/yahoo parquet: ascending Date index, close (adjusted)
    and close_price columns. close_price = 2x close by default so the two bases
    are distinguishable; the last row's raw close is overridable."""
    idx = pd.date_range(start, periods=len(closes), freq="D")
    cp = [2.0 * c for c in closes]
    if close_price_last is not None:
        cp[-1] = close_price_last
    df = pd.DataFrame({"close_price": cp, "close": closes}, index=idx)
    df.index.name = "Date"
    # force the last index entry to last_date (index values themselves don't
    # matter beyond ordering; only the LAST date is asserted on)
    if len(idx):
        df = df.rename(index={df.index[-1]: pd.Timestamp(last_date)})
    p = yahoo_dir / f"{ticker}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    # pin the mtime so the vintage assertion is exact
    ts = datetime(2026, 11, 11, 22, 15, 0, tzinfo=timezone.utc).timestamp()
    import os

    os.utime(p, (ts, ts))


def _write_ledger(ledger_path: Path, rows: list[dict]) -> None:
    df = pd.DataFrame(rows, columns=["ticker", "group", "name", "sector",
                                     "first_seen", "last_seen", "active"])
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ledger_path, index=False)


def _write_spy(spy_dir: Path, date: str, rows: list[dict]) -> None:
    df = pd.DataFrame(rows, columns=["ticker", "name", "weight_pct", "shares",
                                     "market_value", "as_of"])
    spy_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(spy_dir / f"{date}.parquet", index=False)


LEDGER_ROWS = [
    {"ticker": "AAA", "group": "sp500", "name": "A", "sector": "Information Technology",
     "first_seen": "2026-06-13", "last_seen": "2026-11-11", "active": True},
    {"ticker": "IDXONLY", "group": "sp500", "name": "I", "sector": "Financials",
     "first_seen": "2026-06-13", "last_seen": "2026-11-11", "active": True},
    {"ticker": "GONE", "group": "sp500", "name": "G", "sector": "Energy",
     "first_seen": "2026-06-13", "last_seen": "2026-08-01", "active": False},
    {"ticker": "MID", "group": "sp400", "name": "M", "sector": "Industrials",
     "first_seen": "2026-06-13", "last_seen": "2026-11-11", "active": True},
]


def _read(path: Path) -> tuple[dict, list[dict]]:
    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    parsed = [json.loads(x) for x in lines if x.strip()]
    return parsed[0], parsed[1:]


def _build(tmp_path: Path):
    """The full fixture world: prices, ledger, SPY snapshots (one admissible,
    one LATER), wired through the writer's injectable paths."""
    yahoo = tmp_path / "yahoo"
    # AAA: 300 rows. Rows 0..298 close=100.0 except row 10 = 150.0 (outside
    # every window except 252); row 299 (the last) close=120.0.
    closes = [100.0] * 300
    closes[10] = 150.0
    closes[299] = 120.0
    _write_yahoo(yahoo, "AAA", closes, "2026-11-11", close_price_last=240.0)
    # SHORT: 30 rows, all 10.0, last = 5.0
    short = [10.0] * 30
    short[-1] = 5.0
    _write_yahoo(yahoo, "SHORT", short, "2026-11-11")
    # DECK: 300 flat rows, last 100.0 (a second vendor member with a price file)
    _write_yahoo(yahoo, "DECK", [100.0] * 300, "2026-11-11")
    # IDXONLY: 61 rows, first 60 = 50.0, last = 55.0 -> 60d return 55/50-1 = 0.1
    idx_closes = [50.0] * 61
    idx_closes[-1] = 55.0
    _write_yahoo(yahoo, "IDXONLY", idx_closes, "2026-11-11")
    # NOFILE: in the tree, no parquet at all
    ledger = tmp_path / "universe" / "membership.parquet"
    _write_ledger(ledger, LEDGER_ROWS)
    spy = tmp_path / "etf_holdings" / "SPY"
    _write_spy(spy, "2026-06-11", [
        {"ticker": "AAA", "name": "A", "weight_pct": 1.5, "shares": 100.0,
         "market_value": None, "as_of": "2026-06-11"},
        {"ticker": "DECK", "name": "D", "weight_pct": 0.25, "shares": 10.0,
         "market_value": 1_000.0, "as_of": "2026-06-11"},
    ])
    # a LATER snapshot that must never be read for asof 2026-11-11
    _write_spy(spy, "2026-11-20", [
        {"ticker": "AAA", "name": "A", "weight_pct": 9.9, "shares": 1.0,
         "market_value": None, "as_of": "2026-11-20"},
    ])
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    return dict(dir_path=out, yahoo_dir=yahoo, ledger_path=ledger,
                spy_holdings_dir=spy)


def _write(tmp_path: Path) -> tuple[bool, Path, int]:
    kw = _build(tmp_path)
    return write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)


# ------------------------------------------------------------------ #
# (a) hand-computed field values
# ------------------------------------------------------------------ #

class TestHandComputedFields:
    def test_row_count_is_union_of_distinct_tickers(self, tmp_path):
        written, p, rows = _write(tmp_path)
        assert written is True and rows == EXPECTED_ROWS
        meta, file_rows = _read(p)
        assert meta["row_count"] == EXPECTED_ROWS == len(file_rows)
        assert sorted(r["ticker"] for r in file_rows) == \
            ["AAA", "DECK", "IDXONLY", "NOFILE", "SHORT"]

    def test_50_and_200_row_ratios_hand_computed(self, tmp_path):
        """AAA: last close 120; the last 50 closes are 49x100 + 120 = 5020
        -> sma50 = 100.4, ratio = 120/100.4. The last 200 closes contain row
        10's 150.0 ONLY IF it falls inside the window: with 300 rows the last
        200 are rows 100..299, all 100 except the last -> sma200 = 20020/200 =
        100.1, ratio = 120/100.1."""
        _, p, _ = _write(tmp_path)
        aaa = next(r for r in _read(p)[1] if r["ticker"] == "AAA")
        assert aaa["close_over_sma_50"] == pytest.approx(120.0 / (5020.0 / 50.0),
                                                         rel=1e-12)
        assert aaa["close_over_sma_200"] == pytest.approx(120.0 / (20020.0 / 200.0),
                                                          rel=1e-12)

    def test_20_63_252_high_low_flags_hand_computed(self, tmp_path):
        """AAA last close 120 vs: last 20 (rows 280..299, max 120, min 100)
        -> high True, low False; last 63 (rows 237..299, same extremes)
        -> high True, low False; last 252 (rows 48..299, CONTAINS row 10? no —
        rows 48..299 exclude row 10=150) -> max 120 -> high True, low False.
        SHORT last close 5: last 20 max 10 min 5 -> low True, high False; the
        63/252 windows are null (only 30 rows)."""
        _, p, _ = _write(tmp_path)
        rows = {r["ticker"]: r for r in _read(p)[1]}
        aaa = rows["AAA"]
        assert (aaa["is_high_20d"], aaa["is_low_20d"]) == (True, False)
        assert (aaa["is_high_63d"], aaa["is_low_63d"]) == (True, False)
        assert (aaa["is_high_252d"], aaa["is_low_252d"]) == (True, False)
        short = rows["SHORT"]
        assert (short["is_high_20d"], short["is_low_20d"]) == (False, True)
        assert short["is_high_63d"] is None and short["is_low_63d"] is None
        assert short["is_high_252d"] is None and short["is_low_252d"] is None

    def test_60_session_total_return_hand_computed(self, tmp_path):
        """IDXONLY: 61 rows; c[-61] = 50.0 (the FIRST row), last = 55.0 ->
        55/50 - 1 = 0.1 exactly. SHORT: only 30 rows -> null."""
        _, p, _ = _write(tmp_path)
        rows = {r["ticker"]: r for r in _read(p)[1]}
        assert rows["IDXONLY"]["total_return_60d"] == pytest.approx(0.1, rel=1e-12)
        assert rows["SHORT"]["total_return_60d"] is None

    def test_last_row_closes_on_both_bases(self, tmp_path):
        """AAA's raw (split-adjusted, dividend-unadjusted) close on the last row
        was pinned to 240.0 (2x is the default; the pin proves it is the LAST
        row's value, not a series recomputation)."""
        _, p, _ = _write(tmp_path)
        aaa = next(r for r in _read(p)[1] if r["ticker"] == "AAA")
        assert aaa["close"] == 120.0
        assert aaa["close_price"] == 240.0
        assert aaa["n_price_rows"] == 300
        assert aaa["last_price_date"] == "2026-11-11"
        assert aaa["price_vintage"] == "2026-11-11T22:15:00+00:00"

    def test_index_weight_facts_carry_their_own_snapshot_date(self, tmp_path):
        _, p, _ = _write(tmp_path)
        rows = {r["ticker"]: r for r in _read(p)[1]}
        assert rows["AAA"]["index_weight_pct"] == 1.5
        assert rows["AAA"]["index_weight_snapshot_date"] == "2026-06-11"
        # a source column that is null stays null — never derived
        assert rows["AAA"]["index_market_value"] is None
        assert rows["DECK"]["index_market_value"] == 1_000.0


# ------------------------------------------------------------------ #
# (b) union roster semantics
# ------------------------------------------------------------------ #

class TestUnionRoster:
    def test_multi_membership_ticker_is_one_row_with_sorted_keys(self, tmp_path):
        _, p, _ = _write(tmp_path)
        decks = [r for r in _read(p)[1] if r["ticker"] == "DECK"]
        assert len(decks) == 1
        assert decks[0]["theme"] == ["tech"]
        assert decks[0]["subsector"] == ["aicompute", "fintech"]

    def test_index_only_ticker_has_null_membership_keys(self, tmp_path):
        _, p, _ = _write(tmp_path)
        idx = next(r for r in _read(p)[1] if r["ticker"] == "IDXONLY")
        assert idx["theme"] is None and idx["subsector"] is None
        assert idx["in_sp500"] is True
        assert idx["gics_sector"] == "Financials"

    def test_vendor_only_ticker_is_not_index_member(self, tmp_path):
        _, p, _ = _write(tmp_path)
        deck = next(r for r in _read(p)[1] if r["ticker"] == "DECK")
        assert deck["in_sp500"] is False and deck["gics_sector"] is None

    def test_inactive_or_other_group_ledger_rows_are_not_members(self, tmp_path):
        _, p, _ = _write(tmp_path)
        tickers = {r["ticker"] for r in _read(p)[1]}
        assert "GONE" not in tickers   # sp500, active=False
        assert "MID" not in tickers    # sp400, active — not the sp500 group

    def test_later_weight_snapshot_is_never_used(self, tmp_path):
        _, p, _ = _write(tmp_path)
        aaa = next(r for r in _read(p)[1] if r["ticker"] == "AAA")
        assert aaa["index_weight_pct"] == 1.5          # the 2026-06-11 file
        assert aaa["index_weight_snapshot_date"] == "2026-06-11"
        assert aaa["index_weight_pct"] != 9.9          # the 2026-11-20 file

    def test_ticker_absent_from_snapshot_gets_null_weight(self, tmp_path):
        """A ticker the admissible snapshot does not hold carries the whole
        weight fact as null — weight AND its date (a null weight with a dated
        snapshot would read as 'confirmed not held as of that date', which the
        writer does not claim). Which snapshot the FILE consulted stays in the
        meta record."""
        _, p, _ = _write(tmp_path)
        idx = next(r for r in _read(p)[1] if r["ticker"] == "IDXONLY")
        assert idx["index_weight_pct"] is None
        assert idx["index_market_value"] is None
        assert idx["index_weight_snapshot_date"] is None
        assert _read(p)[0]["index_weights"]["snapshot_date"] == "2026-06-11"

    def test_no_admissible_snapshot_means_null_dates(self, tmp_path):
        kw = _build(tmp_path)
        for f in kw["spy_holdings_dir"].glob("*.parquet"):
            f.unlink()
        written, p, _rows = write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)
        aaa = next(r for r in _read(p)[1] if r["ticker"] == "AAA")
        assert aaa["index_weight_pct"] is None
        assert aaa["index_weight_snapshot_date"] is None
        meta = _read(p)[0]
        assert meta["index_weights"]["snapshot_date"] is None


# ------------------------------------------------------------------ #
# (c) immutability + determinism
# ------------------------------------------------------------------ #

class TestImmutability:
    def test_second_run_same_session_is_skip_and_byte_identical(self, tmp_path):
        _, p, _rows = _write(tmp_path)
        first = p.read_bytes()
        kw = _build(tmp_path)  # same world, fresh dicts
        written2, p2, rows2 = write_member_price_state(
            ASOF, "2026-11-12T22:30:00+00:00", TREE, **kw)
        assert written2 is False and rows2 == 0 and p2 == p
        assert p.read_bytes() == first

    def test_payload_is_deterministic_across_fresh_writes(self, tmp_path):
        _write(tmp_path / "a")
        _write(tmp_path / "b")
        a = (tmp_path / "a" / "out" / f"{ASOF}.jsonl.gz").read_bytes()
        b = (tmp_path / "b" / "out" / f"{ASOF}.jsonl.gz").read_bytes()
        assert a == b

    def test_distinct_sessions_are_distinct_files(self, tmp_path):
        kw = _build(tmp_path)
        write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)
        w2, _p2, r2 = write_member_price_state("2026-11-12", FETCHED_AT, TREE, **kw)
        assert w2 is True and r2 == EXPECTED_ROWS
        assert sorted(x.name for x in kw["dir_path"].glob("*.jsonl.gz")) == [
            "2026-11-11.jsonl.gz", "2026-11-12.jsonl.gz"]

    def test_no_tmp_leftover_after_success(self, tmp_path):
        _write(tmp_path)
        assert list((tmp_path / "out").glob("*.tmp")) == []


# ------------------------------------------------------------------ #
# (d) capture-only resilience: nulls, never errors
# ------------------------------------------------------------------ #

class TestNullsNotFills:
    def test_missing_price_file_yields_nulls_not_error(self, tmp_path):
        _, p, _ = _write(tmp_path)
        nofile = next(r for r in _read(p)[1] if r["ticker"] == "NOFILE")
        assert nofile["n_price_rows"] is None
        assert nofile["last_price_date"] is None
        assert nofile["close_price"] is None and nofile["close"] is None
        assert nofile["close_over_sma_50"] is None
        assert nofile["total_return_60d"] is None
        assert nofile["price_vintage"] is None
        # roster facts are still real
        assert nofile["subsector"] == ["oilservices"] and nofile["in_sp500"] is False

    def test_short_file_yields_null_windows_not_error(self, tmp_path):
        _, p, _ = _write(tmp_path)
        short = next(r for r in _read(p)[1] if r["ticker"] == "SHORT")
        assert short["n_price_rows"] == 30
        assert short["close_over_sma_50"] is None       # needs 50
        assert short["close_over_sma_200"] is None      # needs 200
        assert short["is_high_63d"] is None             # needs 63
        assert short["is_high_20d"] is not None         # 30 >= 20

    def test_stale_last_row_keeps_its_real_date(self, tmp_path):
        """The writer ran 'tonight' (asof 2026-11-11) but the file's last row
        is dated 2026-11-08: the row keeps the REAL last date — never carried
        forward to the session date."""
        kw = _build(tmp_path)
        yahoo = kw["yahoo_dir"]
        _write_yahoo(yahoo, "AAA", [100.0] * 300, "2026-11-08")
        write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)
        aaa = next(r for r in _read(kw["dir_path"] / f"{ASOF}.jsonl.gz")[1]
                   if r["ticker"] == "AAA")
        assert aaa["last_price_date"] == "2026-11-08"

    def test_missing_ledger_means_vendor_only_roster(self, tmp_path):
        kw = _build(tmp_path)
        kw["ledger_path"].unlink()
        written, p, rows = write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)
        assert written is True and rows == 4  # AAA, DECK, SHORT, NOFILE
        assert all(r["in_sp500"] is False for r in _read(p)[1])


# ------------------------------------------------------------------ #
# (e) an exception never propagates to the build
# ------------------------------------------------------------------ #

class TestFailureIsolation:
    def _run_main(self, monkeypatch, tmp_path, *, price_state_impl=None):
        """Drive real main() with the network and every data path redirected."""
        out = tmp_path / "out"
        out.mkdir(parents=True, exist_ok=True)
        tree_path = out / "themes_tree.json"
        tree_path.write_text(json.dumps(TREE))
        monkeypatch.setattr(fft, "OUT_DIR", out)
        monkeypatch.setattr(fft, "TREE_PATH", tree_path)
        monkeypatch.setattr(fft, "PERF_PATH", out / "perf_snapshot.json")
        monkeypatch.setattr(fft, "SUBSECTOR_PERF_HISTORY_PATH",
                            out / "subsector_perf_history.jsonl")
        monkeypatch.setattr(fft, "TREE_HISTORY_PATH", out / "tree_history.jsonl")
        monkeypatch.setattr(fft, "MEMBER_PERF_ARCHIVE_DIR", out / "member_perf_archive")
        monkeypatch.setattr(fft, "MEMBER_PRICE_STATE_DIR", out / "member_price_state")
        monkeypatch.setattr(fft, "PRICE_STATE_YAHOO_DIR", tmp_path / "yahoo")
        monkeypatch.setattr(fft, "PRICE_STATE_UNIVERSE_LEDGER",
                            tmp_path / "universe" / "membership.parquet")
        monkeypatch.setattr(fft, "PRICE_STATE_SPY_HOLDINGS_DIR",
                            tmp_path / "etf_holdings" / "SPY")
        monkeypatch.setattr(fft, "fetch_subsector_perf",
                            lambda: {"aicompute": {"1D": 1.0}})
        monkeypatch.setattr(fft, "fetch_member_perf",
                            lambda tickers: {"AAA": {"1D": 1.0}})
        monkeypatch.setattr(fft, "_asof_stamp", lambda now_utc=None: ASOF)
        if price_state_impl is not None:
            monkeypatch.setattr(fft, "write_member_price_state", price_state_impl)
        monkeypatch.setattr(sys, "argv", ["fetch_finviz_themes.py"])
        try:
            fft.main()
            return None
        except SystemExit as e:
            return e.code

    def test_price_state_exception_does_not_propagate(self, monkeypatch, tmp_path,
                                                      capsys):
        _build(tmp_path)  # world exists; the writer itself is what explodes

        def boom(*a, **kw):
            raise OSError("disk full mid-price-state")

        code = self._run_main(monkeypatch, tmp_path, price_state_impl=boom)
        assert code is None, "price-state failure must not exit the build"
        assert (tmp_path / "out" / "perf_snapshot.json").exists()
        assert (tmp_path / "out" / "member_perf_archive" / f"{ASOF}.jsonl.gz").exists()
        err = capsys.readouterr().err
        assert any(l.startswith("::error::") and "member price state" in l
                   for l in err.splitlines())

    def test_healthy_main_writes_price_state(self, monkeypatch, tmp_path):
        _build(tmp_path)
        code = self._run_main(monkeypatch, tmp_path)
        assert code is None
        p = tmp_path / "out" / "member_price_state" / f"{ASOF}.jsonl.gz"
        meta, rows = _read(p)
        assert meta["asof"] == ASOF and len(rows) == EXPECTED_ROWS

    def test_corrupt_parquet_nulls_one_ticker_not_the_file(self, tmp_path, capsys):
        """A per-ticker read failure (here: a non-parquet file) must not lose
        the session — the row is written with null price facts and a loud
        warning names the ticker."""
        kw = _build(tmp_path)
        bad = kw["yahoo_dir"] / "AAA.parquet"
        bad.write_bytes(b"this is not a parquet")
        written, p, rows = write_member_price_state(ASOF, FETCHED_AT, TREE, **kw)
        assert written is True and rows == EXPECTED_ROWS
        aaa = next(r for r in _read(p)[1] if r["ticker"] == "AAA")
        assert aaa["n_price_rows"] is None
        meta = _read(p)[0]
        assert meta["counts"]["price_read_errors"] == 1
