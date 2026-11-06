"""Collector never-silent disclosure (R4, research/ADJUDICATION_20260803_UNIVERSE_
SIDE_STORE_FRESHNESS.md): collectors/yahoo.py's requested-vs-returned reconciliation
+ store-tip audit, collectors/breadth.py's current-constituent column disclosure,
and the explicit-input ACQUISITION SEAM's typed refusal vocabulary.

CTRA/TPH/TCNNF froze because `_extract()` drops a requested-but-unreturned symbol
via a log-only `except KeyError`, invisible to every downstream guard; CWEN-A froze
because `_merge_refreshed`'s `fresh.combine_first(cached)` (a deliberate perpetual-
archive feature) carries a dead column forward with zero disclosure. No network —
every fixture here is a hand-built DataFrame/dict; store reads are monkeypatched.

The acquisition seam section extends the same law to a NEW shape: a runtime owner
may stage the closed US Sector cycle benchmark set from EXPLICIT inputs (selected
symbols, prior frames, evaluation instant, session policy) without a second
collector and without touching the repository. Its contract is all-or-nothing — a
partial result is a typed refusal with NO frames — so a name can never go missing
without a reason attached, which is the same never-silent law the reconciliation
and the audit enforce.
"""
from __future__ import annotations

import copy
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import breadth as bp  # noqa: E402
from collectors import yahoo as yh  # noqa: E402
from lib import config, store, us_cash_calendar  # noqa: E402


# ---------------------------------------------------------------------------
# collectors/yahoo.py::_report_missing_symbols
# ---------------------------------------------------------------------------

def test_missing_symbols_prints_bare_warning_and_returns_list(capsys):
    requested = ["AAPL", "CTRA", "TPH", "TCNNF"]
    returned = {"AAPL"}   # CTRA/TPH/TCNNF silently absent, mirroring the incident
    missing = yh._report_missing_symbols(requested, returned)
    assert missing == ["CTRA", "TPH", "TCNNF"]
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("::")]
    assert len(lines) == 1
    assert lines[0].startswith("::warning title=yahoo collector missing symbols::")
    assert "CTRA" in lines[0] and "TPH" in lines[0] and "TCNNF" in lines[0]


def test_missing_symbols_silent_when_nothing_missing(capsys):
    missing = yh._report_missing_symbols(["AAPL", "MSFT"], {"AAPL", "MSFT"})
    assert missing == []
    out = capsys.readouterr().out
    assert not [ln for ln in out.splitlines() if ln.startswith("::")]


def test_missing_symbols_caps_display_at_15(capsys):
    # T1/T10/T11.../T19 share a prefix — a naive "T1 in line" substring check would
    # pass even if T1 itself were silently dropped from the shown set (it would
    # still match inside "T10"). Assert on the exact comma-delimited token list.
    requested = [f"T{i}" for i in range(20)]
    missing = yh._report_missing_symbols(requested, set())
    assert len(missing) == 20
    out = capsys.readouterr().out
    line = [ln for ln in out.splitlines() if ln.startswith("::")][0]
    assert "20 requested" in line
    assert "+5 more" in line
    body = line.split("returned no data: ", 1)[1]
    names_part = body.split(", +", 1)[0]
    shown_tokens = [t.strip() for t in names_part.split(",")]
    assert shown_tokens == requested[:15]


# ---------------------------------------------------------------------------
# collectors/yahoo.py::audit_store_freshness
# ---------------------------------------------------------------------------

def _idx(start: str, periods: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=periods, freq="D")


# Wall-clock anchor for every "fresh" fixture: the M1 backstops compare a fixture's own
# tip against utcnow, so a hardcoded fresh-tip date is a scheduled failure fuse — it
# passes until (date + 7d) and then reds the suite with no code change. Same idiom as
# the production backstops (Timestamp.utcnow kept for consistency with breadth.py:436).
_TODAY = pd.Timestamp.utcnow().tz_localize(None).normalize()


def _idx_ending(periods: int, end: pd.Timestamp = _TODAY, lag_days: int = 0) -> pd.DatetimeIndex:
    return pd.date_range(end=end - pd.Timedelta(days=lag_days), periods=periods, freq="D")


def test_audit_store_freshness_classifies_stale_stub_missing(monkeypatch, capsys):
    fresh_df = pd.DataFrame({"close": range(80)}, index=_idx_ending(80))              # tip today
    stale_df = pd.DataFrame({"close": range(70)}, index=_idx_ending(70, lag_days=27))  # tip today-27d
    stub_df = pd.DataFrame({"close": [1.0, 2.0]}, index=_idx_ending(2))               # tip today, 2 rows
    _stale_tip = str((_TODAY - pd.Timedelta(days=27)).date())

    fixtures = {"FRESH": fresh_df, "STALE": stale_df, "STUB": stub_df}

    def fake_read(group, name):
        assert group == "yahoo"
        return fixtures.get(name)

    monkeypatch.setattr(yh.store, "read", fake_read)
    result = yh.audit_store_freshness(["FRESH", "STALE", "STUB", "GHOST"], group="yahoo")

    assert result["ref"] == str(_TODAY.date())     # FRESH sets the group's own tip
    assert "STALE" in result["stale"] and result["stale"]["STALE"] == _stale_tip
    assert "FRESH" not in result["stale"] and "STUB" not in result["stale"]
    assert "STUB" in result["stub"]
    assert "FRESH" not in result["stub"] and "STALE" not in result["stub"]
    assert result["missing"] == ["GHOST"]

    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("::")]
    joined = "\n".join(lines)
    assert "STALE" in joined and "STUB" in joined and "GHOST" in joined
    assert "FRESH" not in joined   # only the bad ones get named


def test_audit_store_freshness_all_fresh_prints_nothing(monkeypatch, capsys):
    fresh_df = pd.DataFrame({"close": range(80)}, index=_idx_ending(80))

    def fake_read(group, name):
        return fresh_df

    monkeypatch.setattr(yh.store, "read", fake_read)
    result = yh.audit_store_freshness(["A", "B"], group="yahoo")
    assert result["stale"] == {} and result["stub"] == {} and result["missing"] == []
    out = capsys.readouterr().out
    assert not [ln for ln in out.splitlines() if ln.startswith("::")]


def test_audit_store_freshness_no_stores_returns_none_ref(monkeypatch):
    monkeypatch.setattr(yh.store, "read", lambda group, name: None)
    result = yh.audit_store_freshness(["A", "B"], group="yahoo")
    assert result["ref"] is None
    assert result["missing"] == ["A", "B"]


def test_audit_store_freshness_m1_wall_clock_backstop_on_old_ref(monkeypatch, capsys):
    """M1: a store-tip audit is self-relative to its OWN ref tip — a store whose
    every ticker is stuck at the same ancient date reads as internally consistent
    (nothing is `stale` relative to `ref`) unless something also checks `ref` against
    wall-clock now. Old, fixed dates (not utcnow-anchored) are the point of this test —
    utcnow is naturally far ahead of them."""
    old_df = pd.DataFrame({"close": range(60)}, index=_idx("2020-01-01", 60))

    def fake_read(group, name):
        return old_df

    monkeypatch.setattr(yh.store, "read", fake_read)
    result = yh.audit_store_freshness(["A", "B"], group="yahoo")
    assert result["stale"] == {}   # internally consistent — nothing is behind `ref`
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("::")]
    assert any(ln.startswith("::warning title=yahoo store audit tip stale::") for ln in lines)


# ---------------------------------------------------------------------------
# collectors/breadth.py::disclose_stale_constituent_columns
# ---------------------------------------------------------------------------

def test_breadth_column_disclosure_names_only_the_bad_ones(capsys):
    idx = _idx_ending(40)   # ends today — a hardcoded end date would arm the M1 backstop
    fresh = pd.Series(1.0, index=idx)
    # CWEN-A class: real values only through day 5 (idx[4]) -> 35 days behind the tip
    frozen = pd.Series(1.0, index=idx[:5]).reindex(idx)
    never_pop = pd.Series([float("nan")] * len(idx), index=idx)
    closes = pd.DataFrame({"FRESH": fresh, "FROZEN": frozen, "NEVERPOP": never_pop})

    members = ["FRESH", "FROZEN", "NEVERPOP", "GONE"]   # GONE isn't even a column
    result = bp.disclose_stale_constituent_columns(members, closes, "smallcap_breadth")

    assert result["frozen"] == {"FROZEN": str(idx[4].date())}
    assert result["never_populated"] == ["NEVERPOP"]
    assert result["no_column"] == ["GONE"]
    assert "FRESH" not in result["frozen"] and "FRESH" not in result["never_populated"] \
        and "FRESH" not in result["no_column"]

    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("::")]
    assert len(lines) == 1
    assert lines[0].startswith("::warning title=smallcap_breadth breadth constituents not refreshing::")
    assert "FROZEN" in lines[0] and "NEVERPOP" in lines[0] and "GONE" in lines[0]
    assert "FRESH" not in lines[0]


def test_breadth_column_disclosure_all_fresh_prints_nothing(capsys):
    # anchored to wall-clock "today" (not a hardcoded date) so the new M1 wall-clock
    # backstop doesn't fire here — this test's whole point is that a genuinely fresh
    # frame prints NOTHING, from either check.
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    idx = pd.date_range(today - pd.Timedelta(days=9), periods=10, freq="D")
    a = pd.Series(1.0, index=idx)
    b = pd.Series(2.0, index=idx)
    closes = pd.DataFrame({"A": a, "B": b})
    result = bp.disclose_stale_constituent_columns(["A", "B"], closes, "breadth")
    assert result == {"no_column": [], "never_populated": [], "frozen": {}}
    out = capsys.readouterr().out
    assert not [ln for ln in out.splitlines() if ln.startswith("::")]


def test_breadth_column_disclosure_empty_closes_marks_all_no_column():
    closes = pd.DataFrame()
    result = bp.disclose_stale_constituent_columns(["A", "B"], closes, "breadth")
    assert set(result["no_column"]) == {"A", "B"}


def test_breadth_column_disclosure_m1_wall_clock_backstop_on_total_freeze(capsys):
    """M1: every member frozen TOGETHER at the same old date is invisible to the
    `frozen` check (nothing is behind `overall_tip` — it IS overall_tip). Old, fixed
    dates are the point here — utcnow is naturally far ahead of them."""
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    a = pd.Series(1.0, index=idx)
    b = pd.Series(2.0, index=idx)
    closes = pd.DataFrame({"A": a, "B": b})
    result = bp.disclose_stale_constituent_columns(["A", "B"], closes, "breadth")
    assert result == {"no_column": [], "never_populated": [], "frozen": {}}
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("::")]
    assert any(ln.startswith("::warning title=breadth breadth tip stale::") for ln in lines)


# ---------------------------------------------------------------------------
# M3: collectors/yahoo.py::YahooAdapter.fetch — a basis-DEFERRED name (returned by
# yfinance this run, pulled out of `frames` only by `_rebase_shifted`'s failed re-
# pull) must not be relabeled "returned no data".
# ---------------------------------------------------------------------------

def test_fetch_missing_warning_excludes_basis_deferred_names(monkeypatch, capsys):
    served = {"OK0", "OK1", "OK2", "OK3", "OK4", "OK5", "OK6", "DEFERRED1"}
    idx = pd.date_range("2026-08-01", periods=3, freq="D")

    def fake_download(self, batch, period):
        cols = [t for t in batch if t in served]
        if not cols:
            raise RuntimeError("empty yfinance response")
        col_idx = pd.MultiIndex.from_product([cols, ["Close", "Adj Close", "Volume"]])
        return pd.DataFrame(1.0, index=idx, columns=col_idx)

    def fake_rebase(self, frames, ohlc):
        # DEFERRED1 WAS returned by yfinance (it's in `served`/`frames`) but the
        # basis-guard's re-pull failed, so it's popped from `frames` for this run —
        # never "requested symbol returned no data".
        frames.pop("DEFERRED1", None)
        return ["DEFERRED1"]

    monkeypatch.setattr(yh.YahooAdapter, "_download", fake_download)
    monkeypatch.setattr(yh.YahooAdapter, "_rebase_shifted", fake_rebase)
    monkeypatch.setattr(yh.config, "load", lambda: {"stock_search": {"extra_tickers": []}})

    adapter = yh.YahooAdapter.__new__(yh.YahooAdapter)
    adapter.cfg = {"batch_size": 20, "retries": 1, "backoff_base_s": 0, "tickers": {"vol": []}}
    tickers = ["OK0", "OK1", "OK2", "OK3", "OK4", "OK5", "OK6",
               "DEFERRED1", "REALLYMISSING1", "REALLYMISSING2"]
    monkeypatch.setattr(adapter, "all_tickers", lambda: tickers)

    frames = adapter.fetch(full_history=False)
    assert "DEFERRED1" not in frames
    assert set(frames) == {"OK0", "OK1", "OK2", "OK3", "OK4", "OK5", "OK6"}

    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines()
             if ln.startswith("::warning title=yahoo collector missing symbols::")]
    assert len(lines) == 1
    body = lines[0].split("returned no data: ", 1)[1]
    shown = [t.strip() for t in body.split(",")]
    assert "REALLYMISSING1" in shown and "REALLYMISSING2" in shown
    assert "DEFERRED1" not in shown


# ---------------------------------------------------------------------------
# The explicit-input ACQUISITION SEAM: collectors/yahoo.py::YahooAdapter.
# acquire_cycle_benchmarks — the never-silent law at the acquisition boundary.
#
# A runtime owner may stage the closed US Sector cycle benchmark set from
# EXPLICIT inputs (selected symbols, prior frames, evaluation instant, session
# policy) without a second collector and without touching the repository: no
# store.read, no store.upsert, no config.data_dir, no all_tickers, no Stooq
# refill for unrelated names, no report/ledger/grader/notification, and no
# process-global config mutation. The result is ALL-OR-NOTH — a partial
# fourteen-name result is a typed refusal with NO frames — so a name can never
# go missing without a reason attached, exactly like the reconciliation above.
#
# No network: the download layer is stubbed with faithful yfinance-shaped
# frames; the session calendar is the repository's own published US slate.
# ---------------------------------------------------------------------------

#: The closed US Sector cycle benchmark set, exactly as the seam declares it.
CYCLE_14 = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
            "XLU", "XLV", "XLY", "SPY", "QQQ", "IWM")

#: One dividend's worth of re-basing — the measured SPY signature.
DRIFT = 1.002576

#: After the US close on the last fixture session: today's bar IS complete.
AFTER_CLOSE = datetime(2026, 11, 5, 22, 0, tzinfo=timezone.utc)
#: Mid-session on the same day: today's bar is the RUNNING session, not yet an
#: observation.
DURING_SESSION = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)


def _seam_sessions(end: str = "2026-11-05", n: int = 30) -> pd.DatetimeIndex:
    """The last n REAL US cash sessions ending on ``end`` (holidays excluded)."""
    last = date.fromisoformat(end)
    days = us_cash_calendar.sessions_between(date(last.year, 1, 1), last)
    return pd.DatetimeIndex([pd.Timestamp(d) for d in days[-n:]], name="Date")


def _seam_bars(index: pd.DatetimeIndex, base: float = 100.0, adj_factor: float = 1.0,
               volume: float = 1e6) -> pd.DataFrame:
    """One symbol's yfinance-shaped bars.

    ``adj_factor`` < 1 simulates a dividend payer: Adj Close (total-return)
    sits BELOW Close (split-adjusted, dividend-unadjusted)."""
    close = [base + 0.1 * i for i in range(len(index))]
    return pd.DataFrame({"Close": close, "Adj Close": [c * adj_factor for c in close],
                         "Volume": volume}, index=index)


def _seam_yf_multi(frames_by_ticker: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Assemble a MultiIndex (ticker, field) frame like yf.download(group_by='ticker')."""
    parts: dict[tuple[str, str], pd.Series] = {}
    for ticker, frame in frames_by_ticker.items():
        for column in frame.columns:
            parts[(ticker, column)] = frame[column]
    out = pd.DataFrame(parts)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    return out


def _seam_stored_frame(index: pd.DatetimeIndex, base: float = 100.0) -> pd.DataFrame:
    """A stored series in the store's own schema (close / close_price / volume)."""
    close = [base + 0.1 * i for i in range(len(index))]
    return pd.DataFrame({"close_price": close, "close": close, "volume": 1e6},
                        index=index)


def _seam_adapter(monkeypatch, responder, calls: list | None = None):
    """A YahooAdapter whose download layer is stubbed; calls record (period, batch).

    The adapter is built WITHOUT ``__init__`` so no repository config is read:
    the fetch tunables are the same values the collector's own config carries,
    written out here so the seam's use of them is visible and hermetic."""
    adapter = yh.YahooAdapter.__new__(yh.YahooAdapter)
    adapter.cfg = {"batch_size": 80, "retries": 1, "backoff_base_s": 0,
                   "upsert_basis_tol": 1e-3, "tickers": {"vol": []}}
    recorded = calls if calls is not None else []

    def fake_download(self, batch, period):
        recorded.append((period, list(batch)))
        return responder(list(batch), period)

    monkeypatch.setattr(yh.YahooAdapter, "_download", fake_download)
    return adapter, recorded


def test_seam_requests_only_the_selected_symbols(monkeypatch):
    selected = ["SPY", "XLK", "IWM"]
    index = _seam_sessions()
    adapter, calls = _seam_adapter(
        monkeypatch, lambda batch, period: _seam_yf_multi({t: _seam_bars(index) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        selected, prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    requested = [symbol for _, batch in calls for symbol in batch]
    assert sorted(requested) == sorted(selected)
    assert set(requested).isdisjoint(set(CYCLE_14) - set(selected))


def test_seam_refuses_a_symbol_outside_the_closed_set(monkeypatch):
    index = _seam_sessions()
    adapter, calls = _seam_adapter(
        monkeypatch, lambda batch, period: _seam_yf_multi({t: _seam_bars(index) for t in batch}))

    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(
            ["SPY", "AAPL"], prior_frames={}, evaluation_instant=AFTER_CLOSE)
    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(
            [], prior_frames={}, evaluation_instant=AFTER_CLOSE)
    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(
            ["SPY", "SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)
    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(
            ["SPY"], prior_frames={}, evaluation_instant=datetime(2026, 11, 5, 22, 0))
    assert calls == [], "a refused request must not reach the vendor"


def test_seam_preserves_both_bases(monkeypatch):
    index = _seam_sessions()
    # A dividend payer: Adj Close (total-return) sits below Close (div-unadjusted).
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index, adj_factor=0.98) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    frame = result.frames["SPY"]
    assert {"close", "close_price", "volume"} <= set(frame.columns)
    # The store schema is a CONTRACT with readers that never go through this
    # module (engine/trajectory.py:66, engine/desk_grader.py:124).
    assert tuple(frame.columns[:3]) == yh.STORE_COLUMNS
    assert not frame["close"].equals(frame["close_price"])
    expected = _seam_bars(index, adj_factor=0.98)
    assert list(frame["close"]) == list(expected["Adj Close"])
    assert list(frame["close_price"]) == list(expected["Close"])


def test_seam_never_mutates_the_explicit_prior_frames(monkeypatch):
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    before = prior.copy(deep=True)
    prior_index = prior.index.copy()

    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    pd.testing.assert_frame_equal(prior, before)
    assert prior.index.equals(prior_index)
    assert result.frames["SPY"] is not prior


def test_seam_treats_an_absent_prior_as_explicit_absence(monkeypatch):
    index = _seam_sessions()
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    def boom(*_args, **_kwargs):
        raise AssertionError("the seam must not read the repository for a prior")

    monkeypatch.setattr(store, "read", boom)

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    assert result.lineage["SPY"]["prior"] == "absent"


def test_seam_touches_no_store_config_or_report_path(monkeypatch):
    index = _seam_sessions()

    def boom(*_args, **_kwargs):
        raise AssertionError("the seam must not touch the repository")

    for target, name in (
            (store, "read"), (store, "upsert"), (store, "write_status"),
            (store, "capture_yahoo_observation"), (config, "data_dir"),
            (yh, "_report_missing_symbols"), (yh, "_report_delisted_exclusions")):
        monkeypatch.setattr(target, name, boom)

    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))
    monkeypatch.setattr(adapter, "all_tickers", boom)
    monkeypatch.setattr(adapter, "maintained_tickers", boom)
    monkeypatch.setattr(adapter, "_fill_missing_extras", boom)

    globals_before = copy.deepcopy(config.load())
    result = adapter.acquire_cycle_benchmarks(
        ["SPY", "QQQ"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    assert set(result.frames) == {"SPY", "QQQ"}
    assert config.load() == globals_before, "process-global config was mutated"


def test_seam_refuses_a_missing_adj_close_and_never_synthesises_it(monkeypatch):
    index = _seam_sessions()

    def responder(batch, period):
        frames = {}
        for ticker in batch:
            bars = _seam_bars(index).drop(columns=["Adj Close"])
            frames[ticker] = bars
        return _seam_yf_multi(frames)

    adapter, _ = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_MISSING_ADJ_CLOSE
    assert result.failed == ("SPY",)
    assert dict(result.frames) == {}, "a refused result carries no frames at all"
    assert result.lineage["SPY"]["adj_close_present"] is False


def test_seam_treats_holiday_future_and_running_session_rows_as_non_observations(monkeypatch):
    index = _seam_sessions()
    holiday = pd.Timestamp("2026-12-25")   # a verified US closure
    future = pd.Timestamp("2026-11-06")    # a real session, but after the instant

    def responder(batch, period):
        frames = {}
        for ticker in batch:
            bars = _seam_bars(index)
            extra = pd.DataFrame(
                {"Close": [101.0, 101.0], "Adj Close": [101.0, 101.0],
                 "Volume": [1e6, 1e6]},
                index=pd.DatetimeIndex([holiday, future], name="Date"))
            frames[ticker] = pd.concat([bars, extra])
        return _seam_yf_multi(frames)

    adapter, _ = _seam_adapter(monkeypatch, responder)

    # The running session (2026-11-05) is not an observation yet at 10:00 ET.
    running = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=DURING_SESSION)
    assert running.accepted is True
    assert running.frames["SPY"].index.max() == pd.Timestamp("2026-11-04")
    assert holiday not in running.frames["SPY"].index
    assert future not in running.frames["SPY"].index

    # After the close the same day's bar IS a completed session.
    closed = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)
    assert closed.accepted is True
    assert closed.frames["SPY"].index.max() == pd.Timestamp("2026-11-05")
    assert holiday not in closed.frames["SPY"].index
    assert future not in closed.frames["SPY"].index


def test_seam_refuses_a_partial_result_with_no_frames(monkeypatch):
    index = _seam_sessions()

    def responder(batch, period):
        return _seam_yf_multi({t: _seam_bars(index) for t in batch if t != "QQQ"})

    adapter, _ = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        list(CYCLE_14), prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_MISSING_SYMBOL
    assert result.failed == ("QQQ",)
    assert dict(result.frames) == {}
    assert result.returned == ()


def test_seam_rebases_a_drifted_window_with_period_max(monkeypatch):
    index = _seam_sessions()
    prior = _seam_stored_frame(index)

    def responder(batch, period):
        bars = _seam_bars(index)
        if period == "1mo":
            bars = bars.tail(20)
        bars = bars.copy()
        bars["Adj Close"] = bars["Adj Close"] / DRIFT
        return _seam_yf_multi({t: bars for t in batch})

    adapter, calls = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert [period for period, _ in calls] == ["1mo", "max"]
    assert calls[1][1] == ["SPY"], "only the drifted name is re-pulled"
    assert result.accepted is True
    assert result.lineage["SPY"]["acquisition"] == "max_rebase"
    assert result.lineage["SPY"]["basis_comparison"] == store.BASIS_SHIFTED


def test_seam_keeps_the_prior_input_when_the_max_rebase_fails(monkeypatch):
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    before = prior.copy(deep=True)

    def responder(batch, period):
        if period == "max":
            raise RuntimeError("vendor down")
        bars = _seam_bars(index).tail(20).copy()
        bars["Adj Close"] = bars["Adj Close"] / DRIFT
        return _seam_yf_multi({t: bars for t in batch})

    adapter, _ = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_BASIS_REBASE_FAILED
    assert result.failed == ("SPY",)
    assert dict(result.frames) == {}, "a shifted window is never published"
    pd.testing.assert_frame_equal(prior, before), "the prior input must survive intact"


def test_seam_rejects_a_refresh_older_than_the_prior(monkeypatch):
    index = _seam_sessions()
    prior = _seam_stored_frame(index)          # the stored series ends 2026-11-05

    # A refresh that reaches the prior's tip is NOT stale.
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index).tail(20) for t in batch}))
    current = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)
    assert current.accepted is True
    assert current.reason == yh.ACCEPTED

    # A refresh whose tip PRECEDES the prior's tip is stale: keeping it would
    # regress the series, and mixing its adjustment window beside newer stored
    # bars mixes bases. The store's own writer refuses the same span.
    older_index = _seam_sessions(end="2026-10-20", n=20)
    adapter2, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(older_index) for t in batch}))
    stale = adapter2.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert stale.accepted is False
    assert stale.reason == yh.REFUSED_STALE_REFRESH
    assert stale.failed == ("SPY",)
    assert dict(stale.frames) == {}


def test_seam_leaves_the_legacy_fetch_path_untouched(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    index = _seam_sessions()
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))
    monkeypatch.setattr(adapter, "all_tickers", lambda: ["SPY"])
    monkeypatch.setattr(adapter, "_fill_missing_extras", lambda frames, extras: frames)

    frames = adapter.fetch(full_history=False)

    assert set(frames) == {"SPY"}
    assert {"close", "close_price", "volume"} <= set(frames["SPY"].columns)


def test_the_pure_basis_comparison_and_the_store_backed_guard_never_disagree(
        monkeypatch, tmp_path):
    """The seam compares against the caller's prior; the writer compares against
    the store. Both must answer the same question the same way."""
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    index = _seam_sessions()
    prior = _seam_stored_frame(index)

    drifted = prior.tail(20).copy()
    drifted["close"] = drifted["close"] / DRIFT
    aligned = prior.tail(20).copy()

    assert store.compare_basis(prior, drifted, col="close").status == store.BASIS_SHIFTED
    assert store.compare_basis(prior, aligned, col="close").status == store.BASIS_ALIGNED
    assert store.compare_basis(None, aligned, col="close").status == store.BASIS_NO_PRIOR
    assert store.compare_basis(prior, prior.tail(5).iloc[:0], col="close").status \
        == store.BASIS_NO_PRIOR
    assert store.basis_shifted("yahoo", "NEWNAME", aligned) is False


# ---------------------------------------------------------------------------
# The reviewer's gaps: the uncovered branches, the untested paths, and the
# assertions that would pass even if the seam were broken.
# ---------------------------------------------------------------------------

def test_seam_refuses_every_failed_name_not_only_the_headline_reason(monkeypatch):
    """Two DISTINCT failure reasons in one call: every failed name is named.

    A caller that retries "the failed names" must retry all of them — a name
    that failed for a different reason must not vanish from the account."""
    index = _seam_sessions()

    def responder(batch, period):
        frames = {}
        for ticker in batch:
            if ticker == "QQQ":
                # Served WITHOUT an Adj Close: the total-return basis is missing.
                frames[ticker] = _seam_bars(index).drop(columns=["Adj Close"])
            elif ticker == "IWM":
                continue          # served no data at all
            else:
                frames[ticker] = _seam_bars(index)
        return _seam_yf_multi(frames)

    adapter, _ = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        ["SPY", "QQQ", "IWM"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_MISSING_ADJ_CLOSE      # the headline
    assert result.failed == ("IWM", "QQQ"), "EVERY failed name is named"
    assert result.primary_failed == ("QQQ",), "the headline reason names its own"
    assert dict(result.failure_reasons) == {
        "QQQ": yh.REFUSED_MISSING_ADJ_CLOSE, "IWM": yh.REFUSED_MISSING_SYMBOL}
    assert dict(result.frames) == {}


def test_seam_refuses_a_bare_adj_close_column_as_a_missing_basis(monkeypatch):
    """Adj Close PRESENT but all-NaN is still no total-return basis."""
    index = _seam_sessions()

    def responder(batch, period):
        frames = {}
        for ticker in batch:
            bars = _seam_bars(index).copy()
            bars["Adj Close"] = float("nan")
            frames[ticker] = bars
        return _seam_yf_multi(frames)

    adapter, _ = _seam_adapter(monkeypatch, responder)
    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_MISSING_ADJ_CLOSE
    assert result.lineage["SPY"]["adj_close_present"] is False
    assert dict(result.frames) == {}


def test_seam_accepts_the_running_session_when_the_policy_says_so(monkeypatch):
    """The second session-policy branch: completed_sessions_only=False keeps the
    running session, exactly as the nightly collect path does."""
    index = _seam_sessions()
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    completed = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=DURING_SESSION,
        completed_sessions_only=True)
    assert completed.frames["SPY"].index.max() == pd.Timestamp("2026-11-04")

    observed = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=DURING_SESSION,
        completed_sessions_only=False)
    assert observed.accepted is True
    assert observed.frames["SPY"].index.max() == pd.Timestamp("2026-11-05")
    assert observed.clocks["known"]["completed_sessions_only"] is False


def test_seam_accepts_a_max_pull_and_says_it_made_no_comparison(monkeypatch):
    """A "max" pull already rebases, so no basis comparison is needed — and the
    lineage must say so instead of claiming a comparison that never happened."""
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    adapter, calls = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE,
        period="max")

    assert result.accepted is True
    assert [period for period, _ in calls] == ["max"], "one pull, no re-pull"
    assert result.lineage["SPY"]["acquisition"] == "max"
    assert result.lineage["SPY"]["basis_comparison"] == "not_compared"


def test_seam_refuses_every_drifted_name_when_a_later_rebase_batch_fails(monkeypatch):
    """A batch size below the name count: the abandoned batches must be refused
    as a failed rebase, never reported as 'returned no data'."""
    index = _seam_sessions()
    prior = _seam_stored_frame(index)

    def responder(batch, period):
        if period == "max":
            raise RuntimeError("vendor down")
        bars = _seam_bars(index).tail(20).copy()
        bars["Adj Close"] = bars["Adj Close"] / DRIFT
        return _seam_yf_multi({t: bars for t in batch})

    adapter, _ = _seam_adapter(monkeypatch, responder)
    adapter.cfg["batch_size"] = 2
    result = adapter.acquire_cycle_benchmarks(
        ["SPY", "QQQ", "IWM", "XLK"],
        prior_frames={t: prior for t in ("SPY", "QQQ", "IWM", "XLK")},
        evaluation_instant=AFTER_CLOSE)

    assert result.accepted is False
    assert result.reason == yh.REFUSED_BASIS_REBASE_FAILED
    assert result.failed == ("IWM", "QQQ", "SPY", "XLK")
    assert all(r == yh.REFUSED_BASIS_REBASE_FAILED
               for r in result.failure_reasons.values())


def test_seam_handles_a_timezone_aware_prior_without_mutating_it(monkeypatch):
    """A prior stored on a tz-aware midnight index is normalised, not mutated."""
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    prior.index = prior.index.tz_localize("America/New_York")
    before = prior.copy(deep=True)

    adapter, calls = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    assert [period for period, _ in calls] == ["1mo"], "no needless full re-pull"
    assert result.lineage["SPY"]["basis_comparison"] == store.BASIS_ALIGNED
    pd.testing.assert_frame_equal(prior, before)


def test_seam_rejects_a_prior_indexed_by_position_rather_than_by_date(monkeypatch):
    """An integer index is a position, not a date: coercing it would place every
    bar in 1970 and buy a full-history re-pull of nothing."""
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    prior.index = range(len(prior))

    adapter, calls = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    with pytest.raises(ValueError):
        adapter.acquire_cycle_benchmarks(
            ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)
    assert calls == [], "a refused request must not reach the vendor"


def test_seam_reports_its_known_and_unknown_clocks(monkeypatch):
    index = _seam_sessions()
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: _seam_bars(index) for t in batch}))

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={}, evaluation_instant=AFTER_CLOSE)

    known = result.clocks["known"]
    assert known["evaluation_instant"] == AFTER_CLOSE.isoformat()
    assert known["session_calendars"] == ["us"]
    assert known["basis_tolerance"] == pytest.approx(1e-3)
    assert known["calendar_verified"]["us"]["2026"] is True
    unknown = result.clocks["unknown"]
    for key in ("vendor_publication_clock", "provider_available_at",
                "vendor_session_metadata", "upstream_correction_clock"):
        assert unknown[key], f"{key} must be named as unknown, not omitted"


def test_seam_never_reaches_the_repository_on_the_drifted_prior_path(monkeypatch):
    """The drift path is where a naive implementation would call the STORE-backed
    guard (`store.basis_shifted`, which reads the repository). It must not."""
    index = _seam_sessions()
    prior = _seam_stored_frame(index)

    def boom(*_args, **_kwargs):
        raise AssertionError("the seam must not reach the repository")

    monkeypatch.setattr(store, "read", boom)
    monkeypatch.setattr(store, "upsert", boom)

    def responder(batch, period):
        bars = _seam_bars(index).tail(20).copy()
        bars["Adj Close"] = bars["Adj Close"] / DRIFT
        return _seam_yf_multi({t: bars for t in batch})

    adapter, _ = _seam_adapter(monkeypatch, responder)
    monkeypatch.setattr(adapter, "_rebase_shifted", boom)

    result = adapter.acquire_cycle_benchmarks(
        ["SPY"], prior_frames={"SPY": prior}, evaluation_instant=AFTER_CLOSE)

    assert result.accepted is True
    assert result.lineage["SPY"]["basis_comparison"] == store.BASIS_SHIFTED


def test_the_store_backed_guard_and_the_pure_comparison_answer_the_same_question(
        monkeypatch, tmp_path):
    """The seam compares against the caller's prior; the writer compares against
    the store. Both must answer the same question the same way — on the SAME
    frames, with the store really holding the series."""
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    index = _seam_sessions()
    prior = _seam_stored_frame(index)
    (tmp_path / "yahoo").mkdir(parents=True, exist_ok=True)
    prior.to_parquet(tmp_path / "yahoo" / "SPY.parquet")

    drifted = prior.tail(20).copy()
    drifted["close"] = drifted["close"] / DRIFT
    aligned = prior.tail(20).copy()
    sub_tol = prior.tail(20).copy()
    sub_tol["close"] = sub_tol["close"] * 1.0005      # half the 1e-3 tolerance
    disjoint = pd.DataFrame({"close": [1.0] * 5},
                             index=pd.bdate_range("2026-09-01", periods=5))

    cases = [
        (drifted, store.BASIS_SHIFTED, True),
        (aligned, store.BASIS_ALIGNED, False),
        (sub_tol, store.BASIS_ALIGNED, False),
        (disjoint, store.BASIS_NO_OVERLAP, True),
    ]
    for fresh, pure_status, store_backed in cases:
        assert store.compare_basis(prior, fresh, col="close").status == pure_status
        assert store.basis_shifted("yahoo", "SPY", fresh) is store_backed


def test_the_legacy_no_adj_close_fallback_is_unchanged(monkeypatch):
    """The legacy path's FX/index fallback (close_price := close) is untouched:
    only the seam's own path refuses a missing Adj Close."""
    index = _seam_sessions()
    bars = _seam_bars(index).drop(columns=["Adj Close"])
    adapter, _ = _seam_adapter(monkeypatch, lambda batch, period: _seam_yf_multi(
        {t: bars for t in batch}))

    no_adj_close: list[str] = []
    frame = adapter._extract(_seam_yf_multi({"SPY": bars}), "SPY", set(), no_adj_close)

    assert frame is not None
    assert no_adj_close == ["SPY"]
    assert list(frame["close_price"]) == list(frame["close"]), \
        "the legacy fallback still equates the bases"
    assert list(frame["close"]) == list(bars["Close"])


def test_no_cycle_benchmark_is_in_the_vols_group_so_the_store_schema_holds():
    """STORE_COLUMNS is a contract with readers that read the parquet directly.
    A cycle name in the config's vol group would add high/low and break it."""
    vol = set(config.load()["yahoo"]["tickers"].get("vol", []))
    assert not (vol & set(CYCLE_14))
    assert yh.STORE_COLUMNS == ("close_price", "close", "volume")
