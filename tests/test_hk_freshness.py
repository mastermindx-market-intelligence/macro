"""Tests for the HK freshness sentinel + hk_calendar.

Covers:
  (a) Fake stores with mismatched stamps -> sentinel returns stale
  (b) Coherent fresh stores -> ok
  (c) Regression: cache max going backwards -> flagged
  (d) July-8 replay: cache/standouts at 2026-07-02 while expected session is 2026-07-08
      -> stale verdict + banner present (cannot render as live)

Tests are discriminating: they fail against absence of the sentinel code, then pass.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# hk_calendar tests
# ---------------------------------------------------------------------------

class TestHKCalendar:
    def test_weekends_not_sessions(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2026, 7, 4))   # Saturday
        assert not is_session(date(2026, 7, 5))   # Sunday

    def test_weekday_is_session(self):
        from lib.hk_calendar import is_session
        # 2026-07-08 is Wednesday
        assert is_session(date(2026, 7, 8))

    def test_christmas_not_session(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2026, 12, 25))   # Christmas Friday

    def test_new_years_not_session(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2026, 1, 1))   # New Year's Day

    def test_labour_day_not_session(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2026, 5, 1))   # Labour Day Friday

    def test_hk_sar_day_not_session(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2026, 7, 1))   # HK SAR Day Wednesday

    def test_one_off_closure_not_session(self):
        from lib.hk_calendar import is_session
        assert not is_session(date(2023, 9, 8))   # Typhoon Saola

    def test_expected_last_session_july8_incident(self):
        """At 03:00 UTC on 2026-07-08 (before HKT 17:30 settle), expected session is 2026-07-07."""
        from lib.hk_calendar import expected_last_session
        now = datetime(2026, 7, 8, 3, 0, tzinfo=timezone.utc)
        result = expected_last_session(now)
        # If 2026-07-07 is a session, that's the expected
        from lib.hk_calendar import is_session
        # Expect the most recent session before 17:30 HKT on July 8
        # July 7 (Mon) = session; July 8 (Tue) = session but not yet closed at 03:00 UTC
        assert result <= date(2026, 7, 8)
        # Must not return anything stale like 2026-07-02
        assert result >= date(2026, 7, 6)

    def test_expected_last_session_after_settle(self):
        """At 11:00 UTC on 2026-07-08 (= 19:00 HKT, after 17:30 settle), expected = today."""
        from lib.hk_calendar import expected_last_session, is_session
        now = datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc)
        result = expected_last_session(now)
        if is_session(date(2026, 7, 8)):
            assert result == date(2026, 7, 8)

    def test_expected_last_session_uses_hkt(self):
        """UTC 10:00 on a Monday that's after HKT 17:30 should expect Monday, not Friday."""
        from lib.hk_calendar import expected_last_session, is_session
        # Try a Monday that isn't a holiday (2026-07-06, if a session)
        if is_session(date(2026, 7, 6)):
            # 10:00 UTC = 18:00 HKT — after close
            now = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
            result = expected_last_session(now)
            assert result == date(2026, 7, 6)


# ---------------------------------------------------------------------------
# Fixtures and helpers for sentinel tests
# ---------------------------------------------------------------------------

def _write_parquet_with_date(path: Path, d: date) -> None:
    """Write a minimal parquet with a DatetimeIndex containing `d`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    idx = pd.DatetimeIndex([pd.Timestamp(d)])
    df = pd.DataFrame({"close": [100.0]}, index=idx)
    df.to_parquet(path)


def _write_southbound_parquet(path: Path, d: date) -> None:
    """Write a southbound holdings parquet matching PRODUCTION shape.

    The real store (collectors/hk_southbound_holdings.py) persists a long-form
    panel keyed by a ``MultiIndex(['date', 'ticker'])`` — NOT a flat
    DatetimeIndex. Using the flat writer here masked a bug where the sentinel's
    _parquet_index_max returned None for the MultiIndex store and falsely
    reported southbound "dead" on every render.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    idx = pd.MultiIndex.from_tuples(
        [(pd.Timestamp(d), "0700.HK"), (pd.Timestamp(d), "9988.HK")],
        names=["date", "ticker"],
    )
    df = pd.DataFrame({"close": [100.0, 200.0], "own_pct": [1.0, 2.0]}, index=idx)
    df.to_parquet(path)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


class TestHKFreshnessSentinel:
    """Sentinel tests using temporary directories."""

    def _run_sentinel(self, tmpdir: Path, now: datetime,
                      cache_date: date | None = None,
                      bell_date: date | None = None,
                      standouts_asof: date | None = None,
                      regime_date: date | None = None,
                      prev_cache_max: date | None = None,
                      southbound_date: date | None = None) -> dict:
        """Set up fake stores in tmpdir and run sentinel."""
        data_root = tmpdir / "data"
        site_root = tmpdir / "site"

        # Write cache parquet
        if cache_date is not None:
            _write_parquet_with_date(
                data_root / "hk_breadth" / "_closes_cache.parquet", cache_date)

        # Write bellwether parquet
        if bell_date is not None:
            _write_parquet_with_date(
                data_root / "hk_stocks" / "9988.HK.parquet", bell_date)

        # Write standouts JSON
        if standouts_asof is not None:
            _write_json(
                site_root / "factordata" / "hk_standouts.json",
                {"as_of": str(standouts_asof), "buy": [], "watch": []})

        # Write regime JSON
        if regime_date is not None:
            _write_json(
                data_root / "hk_regime" / "latest.json",
                {"date": str(regime_date), "quad": "Q1"})

        # Write previous state (for regression check)
        if prev_cache_max is not None:
            state_dir = data_root / "hk_freshness"
            _write_json(state_dir / "state.json",
                        {"cache_max": str(prev_cache_max)})

        # Write southbound holdings parquet (check 7 — W5 addition).
        # Production shape is a MultiIndex(['date','ticker']) long-form panel.
        if southbound_date is not None:
            _write_southbound_parquet(
                data_root / "hk_southbound" / "holdings.parquet", southbound_date)

        with (patch("lib.config.data_dir", return_value=data_root),
              patch("lib.config.load", return_value={"storage": {"site_dir": str(site_root)}}),
              patch("lib.config.ROOT", tmpdir)):
            from engine.hk_freshness import hk_freshness_sentinel
            return hk_freshness_sentinel(now=now)

    def test_b_coherent_fresh_stores_ok(self, tmp_path):
        """(b) Coherent fresh stores -> verdict ok."""
        # Use a fixed "now" well after the settle buffer: 2026-07-08 12:00 UTC = 20:00 HKT
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        # We need to know what expected_last_session returns for this now
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            southbound_date=expected,
        )
        assert result["verdict"] == "ok", f"Expected ok, got {result['verdict']}: {result}"

    def test_a_stale_cache_mismatched_stamps(self, tmp_path):
        """(a) Cache is stale (2026-07-02 while expected is 2026-07-08) -> stale."""
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        stale_date = date(2026, 7, 2)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=stale_date,
            bell_date=stale_date,
            standouts_asof=stale_date,
            regime_date=stale_date,
        )
        assert result["verdict"] == "stale", f"Expected stale, got {result['verdict']}"
        assert result["stores"]["cache"]["state"] in ("stale",)
        lag = result["stores"]["cache"]["lag_days"]
        assert lag is not None and lag > 2

    def test_c_regression_cache_goes_backward(self, tmp_path):
        """(c) Cache max going backwards -> regression flagged, verdict stale."""
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        # Current cache date is OLDER than the previously seen max
        prev_max = expected   # was fresh yesterday
        curr_date = date(2026, 7, 2)   # now rolled back (the incident!)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=curr_date,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            prev_cache_max=prev_max,
        )
        assert not result["regression"]["ok"], "Expected regression to be flagged"
        assert result["verdict"] == "stale", f"Regression should force stale, got {result['verdict']}"
        assert result["regression"]["note"] is not None
        assert "clobber" in result["regression"]["note"].lower() or "rolled" in result["regression"]["note"].lower()

    def test_d_july8_incident_replay(self, tmp_path):
        """(d) July-8 incident replay: cache/standouts at 2026-07-02, expected 2026-07-07/08
        -> stale verdict + banner present."""
        # Simulate: nightly run at 2026-07-08 02:00 UTC (before HKT open)
        now = datetime(2026, 7, 8, 2, 0, tzinfo=timezone.utc)
        stale_date = date(2026, 7, 2)   # the incident: cache frozen at July 2

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=stale_date,
            bell_date=stale_date,
            standouts_asof=stale_date,
            regime_date=stale_date,
        )
        # The page CANNOT render as live
        assert result["verdict"] == "stale", (
            f"July-8 incident replay must be stale, got {result['verdict']}: {result}")
        # Banner must be present
        assert result["banner_message"] is not None, "Banner must be present when stale"
        assert "en" in result["banner_message"]
        assert "zh" in result["banner_message"]
        assert "2026-07-02" in result["banner_message"]["en"]

    def test_d_july8_expected_session_not_july2(self, tmp_path):
        """The expected session on 2026-07-08 morning must be after 2026-07-02."""
        from lib.hk_calendar import expected_last_session
        now = datetime(2026, 7, 8, 2, 0, tzinfo=timezone.utc)
        expected = expected_last_session(now)
        assert expected > date(2026, 7, 2), (
            f"Expected session should be after 2026-07-02, got {expected}")

    def test_banner_absent_when_ok(self, tmp_path):
        """No banner when verdict is ok."""
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            southbound_date=expected,
        )
        if result["verdict"] == "ok":
            assert result["banner_message"] is None

    def test_coherence_broken_forces_stale(self, tmp_path):
        """Standouts and regime dates diverge by MORE than one session -> coherence bad
        -> stale. (A one-session lag is tolerated — see the phase-tolerance tests below.)
        """
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=date(2026, 7, 1),   # regime is a week old (>1 session gap)
        )
        assert not result["coherence"]["ok"], "Coherence must be broken"
        assert result["verdict"] == "stale"

    # ------------------------------------------------------------------
    # 2026-07-23 revision: coherence phase tolerance (<= 1 business day)
    # ------------------------------------------------------------------

    def test_coherence_one_session_lag_is_ok(self, tmp_path):
        """standouts = T, regime = T-1 (one business day behind, the normal pipeline
        phase) -> coherence ok WITH a note, verdict ok when everything else is fresh.

        This is the chronic false-red case: the committed regime artifact advances one
        asia-close behind the evening stock scan. It must NOT fire "stale".
        """
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)   # 2026-07-08 (Wed)
        regime_prev = date(2026, 7, 7)           # Tue — exactly one session behind

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=regime_prev,
            southbound_date=expected,
        )
        assert result["coherence"]["ok"], (
            f"One-session lag must be coherent, got {result['coherence']}")
        assert result["coherence"].get("gap_sessions") == 1
        assert result["coherence"].get("note"), "One-session lag should carry a note"
        assert result["verdict"] == "ok", (
            f"One-session regime lag must not fire stale, got {result['verdict']}: {result}")

    def test_coherence_two_session_gap_is_stale(self, tmp_path):
        """standouts = T, regime = T-2 (two business days) -> coherence bad -> stale."""
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)   # 2026-07-08 (Wed)
        regime_two_back = date(2026, 7, 6)       # Mon — two sessions behind Wed

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=regime_two_back,
        )
        assert result["coherence"].get("gap_sessions") == 2
        assert not result["coherence"]["ok"], "Two-session gap must break coherence"
        assert result["verdict"] == "stale", (
            f"Two-session gap must be stale, got {result['verdict']}")

    # ------------------------------------------------------------------
    # 2026-07-23 revision: cache missing (absent) vs stale (present-but-old)
    # ------------------------------------------------------------------

    def test_missing_cache_is_degraded_not_stale(self, tmp_path):
        """No cache FILE at all (the ephemeral-runner case: gitignored cache never
        shipped) -> state 'missing' -> verdict 'degraded', NOT 'stale'.

        A merely-absent cache is a runner condition, not stale data. It must not fire
        the full-red "do not act" banner.
        """
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        # Omit cache_date entirely -> file absent
        result = self._run_sentinel(
            tmp_path, now,
            cache_date=None,   # cache file missing
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            southbound_date=expected,
        )
        assert result["stores"]["cache"]["state"] == "missing", (
            f"Absent cache should be 'missing', got {result['stores']['cache']}")
        assert result["verdict"] == "degraded", (
            f"Absent cache must be degraded, not stale, got {result['verdict']}")

    def test_present_but_old_cache_is_stale(self, tmp_path):
        """Cache PRESENT but 5+ days old (the 2026-07-08 rollback incident) -> stale.

        Incident protection: a present-but-stale cache still forces full-red.
        """
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)
        old_cache = date(2026, 7, 2)   # 6 cal days behind 2026-07-08 -> lag >= 5

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=old_cache,   # present but stale
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            southbound_date=expected,
        )
        assert result["stores"]["cache"]["state"] == "stale", (
            f"Present-but-old cache should be 'stale', got {result['stores']['cache']}")
        assert result["verdict"] == "stale", (
            f"Present-but-old cache must force stale, got {result['verdict']}")

    def test_banner_copy_has_no_internal_vocab(self, tmp_path):
        """Banner strings (stale AND degraded) must be plain words — no store slugs,
        no 'incoherent', no 'snapshot'. Tier-1 User-First Design Doctrine.
        """
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)
        banned = ("incoherent", "snapshot", "bellwether", "southbound",
                  "standouts", "_closes_cache", "cache")

        # Separate subdirs so the first run's cache parquet + state.json don't leak into
        # the second scenario (the helper doesn't delete files it isn't asked to write).
        stale = self._run_sentinel(
            tmp_path / "stale_case", now,
            cache_date=date(2026, 7, 2), bell_date=expected,
            standouts_asof=expected, regime_date=expected, southbound_date=expected,
        )
        assert stale["verdict"] == "stale"
        for lang in ("en", "zh"):
            msg = stale["banner_message"][lang].lower()
            for term in banned:
                assert term not in msg, (
                    f"Stale banner[{lang}] leaks '{term}': {stale['banner_message'][lang]}")

        # Degraded banner (missing cache)
        degraded = self._run_sentinel(
            tmp_path / "degraded_case", now,
            cache_date=None, bell_date=expected,
            standouts_asof=expected, regime_date=expected, southbound_date=expected,
        )
        assert degraded["verdict"] == "degraded"
        for lang in ("en", "zh"):
            msg = degraded["banner_message"][lang].lower()
            for term in banned:
                assert term not in msg, (
                    f"Degraded banner[{lang}] leaks '{term}': "
                    f"{degraded['banner_message'][lang]}")

    def test_result_is_always_a_dict(self, tmp_path):
        """Sentinel never raises; always returns a dict.

        Paths are redirected to tmp_path so no git-tracked files are mutated.
        """
        from engine.hk_freshness import hk_freshness_sentinel
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        data_root = tmp_path / "data"
        site_root = tmp_path / "site"
        with (patch("lib.config.data_dir", return_value=data_root),
              patch("lib.config.load",
                    return_value={"storage": {"site_dir": str(site_root)}}),
              patch("lib.config.ROOT", tmp_path)):
            result = hk_freshness_sentinel(now=now)
        assert isinstance(result, dict)
        assert "verdict" in result

    def test_regression_does_not_fire_when_cache_advances(self, tmp_path):
        """Cache advancing forward (healthy update) -> regression ok."""
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        from lib.hk_calendar import expected_last_session
        expected = expected_last_session(now)

        result = self._run_sentinel(
            tmp_path, now,
            cache_date=expected,
            bell_date=expected,
            standouts_asof=expected,
            regime_date=expected,
            southbound_date=expected,
            prev_cache_max=date(2026, 7, 7),   # yesterday was fresh, today is fresh
        )
        assert result["regression"]["ok"], f"Regression should not fire: {result['regression']}"


class TestRunSentinelSafe:
    """Test that run_sentinel (the public wrapper) never crashes."""

    def test_run_sentinel_returns_dict(self, tmp_path):
        """Paths are redirected to tmp_path so no git-tracked files are mutated."""
        from engine.hk_freshness import run_sentinel
        now = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        data_root = tmp_path / "data"
        site_root = tmp_path / "site"
        with (patch("lib.config.data_dir", return_value=data_root),
              patch("lib.config.load",
                    return_value={"storage": {"site_dir": str(site_root)}}),
              patch("lib.config.ROOT", tmp_path)):
            result = run_sentinel(now=now)
        assert isinstance(result, dict)
        assert "verdict" in result
        assert result["verdict"] in ("ok", "degraded", "stale")


class TestHKFreshnessJSON:
    """Test that write_freshness_json creates the expected file."""

    def test_write_freshness_json(self, tmp_path):
        site_root = tmp_path / "site"
        site_root.mkdir()
        from engine.hk_freshness import write_freshness_json
        result = {
            "verdict": "ok",
            "banner_message": None,
            "checked_at": "2026-07-08T12:00:00+00:00",
        }
        with (patch("lib.config.load",
                    return_value={"storage": {"site_dir": str(site_root)}}),
              patch("lib.config.ROOT", tmp_path)):
            write_freshness_json(result, site_root=site_root)
        out = site_root / "factordata" / "hk_freshness.json"
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["verdict"] == "ok"


class TestParquetIndexMax:
    """Directly exercise _parquet_index_max against both store shapes."""

    def test_flat_datetimeindex(self, tmp_path):
        from engine.hk_freshness import _parquet_index_max
        p = tmp_path / "flat.parquet"
        _write_parquet_with_date(p, date(2026, 7, 13))
        assert _parquet_index_max(p) == date(2026, 7, 13)

    def test_multiindex_date_ticker(self, tmp_path):
        """The southbound holdings shape: MultiIndex(['date','ticker'])."""
        from engine.hk_freshness import _parquet_index_max
        p = tmp_path / "holdings.parquet"
        _write_southbound_parquet(p, date(2026, 7, 15))
        # Must read the max of the 'date' level, not silently return None.
        assert _parquet_index_max(p) == date(2026, 7, 15)

    def test_missing_file_is_none(self, tmp_path):
        from engine.hk_freshness import _parquet_index_max
        assert _parquet_index_max(tmp_path / "nope.parquet") is None


# HKEX settled-close recovery: 2026-10-12 Yahoo panel missing the complete day

def _hk_close_fixture(n=20):
    symbols=[f"{i:04d}.HK" for i in range(1,n+1)]
    dates=pd.to_datetime(["2026-10-08","2026-10-09","2026-10-12"])
    df=pd.DataFrame({s:[99.,100.,float("nan")] for s in symbols},index=dates)
    return df,symbols


def _hk_candle(base=100.0,close=101.0):
    return pd.DataFrame({"close":[99.,base,close]},index=pd.to_datetime([
        "2026-10-08","2026-10-09","2026-10-12"]))


def test_hk_vendor_code_volume_units_and_auction_cutoff():
    from datetime import datetime,timezone
    from collectors import china_stock_tencent as tx
    assert tx.tencent_code("0700.HK")=="hk00700"
    assert tx.tencent_code("9988.HK")=="hk09988"
    assert tx.tencent_code("601398.SS")=="sh601398"
    assert tx.tencent_code("000001.SZ")=="sz000001"
    node={"data":{"hk00700":{"day":[
        ["2026-10-09","100","100","101","99","1234"],
        ["2026-10-12","100","102","103","99","1357"],
        ["2026-10-13","99","98","100","97","1511"]]}}}
    df=tx.frame_from_payload("0700.HK",node)
    assert float(df.loc["2026-10-12","volume"])==1357.0  # HK shares, never x100
    before=tx.keep_completed_sessions(
        df,datetime(2026,10,12,8,30,tzinfo=timezone.utc),market="HK")
    assert str(before.index.max().date())=="2026-10-09"  # 16:30 HKT pre-settle
    after=tx.keep_completed_sessions(
        df,datetime(2026,10,12,11,tzinfo=timezone.utc),market="HK")
    assert str(after.index.max().date())=="2026-10-12"
    cn={"data":{"sh600519":{"qfqday":[
        ["2026-10-09","100","100","101","99","13"]]}}}
    assert float(tx.frame_from_payload("600519.SS",cn).iloc[-1]["volume"])==1300.0


def test_hk_settled_candles_qualify_exact_95pct_without_fabricating_missing():
    from datetime import datetime,timezone
    from collectors.hk_breadth import repair_settled_hk_closes
    closes,members=_hk_close_fixture()
    def fetch(ticker,count,retries):
        assert count==12 and retries==1
        return _hk_candle(base=104) if ticker==members[-1] else _hk_candle()
    fixed=repair_settled_hk_closes(
        closes,members,now=datetime(2026,10,12,12,tzinfo=timezone.utc),
        fetcher=fetch,max_workers=6)
    assert int(fixed.loc["2026-10-12"].notna().sum())==19
    assert pd.isna(fixed.at[pd.Timestamp("2026-10-12"),members[-1]])
    assert float(fixed.at[pd.Timestamp("2026-10-12"),members[0]])==101
    assert closes.loc["2026-10-12"].isna().all()


def test_hk_close_refuses_below_95pct_and_never_mutates_source():
    from datetime import datetime,timezone
    import pytest
    from collectors.hk_breadth import repair_settled_hk_closes
    closes,members=_hk_close_fixture()
    def partial(ticker,*_args):
        return _hk_candle() if ticker in members[:18] else None
    with pytest.raises(RuntimeError,match="18/20"):
        repair_settled_hk_closes(
            closes,members,now=datetime(2026,10,12,12,tzinfo=timezone.utc),
            fetcher=partial,max_workers=6)
    assert closes.loc["2026-10-12"].isna().all()


def test_hk_preauction_does_not_accept_early_or_future_close():
    from datetime import datetime,timezone
    from collectors.hk_breadth import repair_settled_hk_closes
    closes,members=_hk_close_fixture()
    def cannot_fetch(*_args):
        raise AssertionError("vendor may not certify an unfinished HKEX session")
    same=repair_settled_hk_closes(
        closes,members,now=datetime(2026,10,12,8,30,tzinfo=timezone.utc),
        fetcher=cannot_fetch)
    assert same.index.max()==pd.Timestamp("2026-10-09")
    assert pd.Timestamp("2026-10-12") not in same.index


def _hk_publisher_fixture(n=160, observed=152):
    symbols=[f"{i:04d}.HK" for i in range(1,n+1)]
    cons=pd.DataFrame({
        "name":[f"HK {i}" for i in range(1,n+1)],
        "sector":["Financial Services" for _ in symbols],
    },index=pd.Index(symbols,name="ticker"))
    idx=pd.to_datetime(["2026-10-08","2026-10-09","2026-10-12"])
    closes=pd.DataFrame({
        t:[100.,101.,102. if i<observed else float("nan")]
        for i,t in enumerate(symbols)
    },index=idx)
    return cons,closes


def test_hk_heatmap_atomic_publisher_requires_settled_source_and_ssr(tmp_path,monkeypatch):
    from scripts import build_market_heatmap as publisher
    current=datetime(2026,10,12,12,tzinfo=timezone.utc)
    cons,closes=_hk_publisher_fixture()
    monkeypatch.setitem(publisher._LOADERS,"hk",lambda: (cons,closes,{}, {},{}))
    monkeypatch.setattr(publisher,"_board_breadth",lambda _:None)
    site=tmp_path/"site"
    result=publisher.publish("hk",site=site,now=current,
                             generated_utc="2026-10-12 12:00")
    json_path=site/"marketdata/hk_heatmap.json"
    page=site/"hk_heatmap.html"
    assert result["asof"]=="2026-10-12"
    assert page.is_file() and json_path.is_file()
    assert publisher._validate_hk_page(page.read_text(),"2026-10-12") is None
    assert publisher._validate_hk_completed_session(result,closes,cons,current)=="2026-10-12"
    old_json=json_path.read_bytes()
    old_html=page.read_bytes()
    # A current source/session with byte-identical semantics may be rebuilt;
    # a transient stale date must never replace the accepted coherent pair.
    monkeypatch.setitem(publisher._LOADERS,"hk",
                        lambda: (cons,closes.loc[closes.index<"2026-10-12"],{},{},{}))
    with pytest.raises(RuntimeError,match="HK heatmap close stale"):
        publisher.publish("hk",site=site,now=current,
                          generated_utc="2026-10-12 12:10")
    assert json_path.read_bytes()==old_json
    assert page.read_bytes()==old_html


def test_hk_heatmap_publisher_rejects_94pct_and_preauction(monkeypatch,tmp_path):
    from scripts import build_market_heatmap as publisher
    cons,partial=_hk_publisher_fixture(observed=150)
    monkeypatch.setitem(publisher._LOADERS,"hk",lambda:(cons,partial,{}, {},{}))
    monkeypatch.setattr(publisher,"_board_breadth",lambda _:None)
    now=datetime(2026,10,12,12,tzinfo=timezone.utc)
    with pytest.raises(RuntimeError,match="only 150/160"):
        publisher.publish("hk",site=tmp_path/"site",now=now)
    assert not (tmp_path/"site/marketdata/hk_heatmap.json").exists()
    assert not (tmp_path/"site/hk_heatmap.html").exists()
    # At 16:30 HKT the new session is not complete and its temporary candles
    # may not be used to advance the EOD map.
    earlier=datetime(2026,10,12,8,30,tzinfo=timezone.utc)
    prior=publisher.publish("hk",site=tmp_path/"site",now=earlier)
    assert prior["asof"]=="2026-10-09", (
        "Before HKEX settlement, the most recent completed day remains Friday"
    )


def test_hk_heatmap_uses_the_incumbent_asia_publisher_not_us_nightly():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    workflow=(root/".github/workflows/asia-close.yml").read_text()
    dag=(root/"config/dag.yml").read_text()
    first=workflow.index("name: publish HK heatmap from settled close")
    cn=workflow.index("name: publish China heatmap from the settled close")
    successor=workflow.index("name: CN Prophet Live arming pass",first)
    assert cn<first<successor
    assert workflow.count("name: publish HK heatmap from settled close")==1
    opening=workflow[first:successor]
    assert "continue-on-error: true" in opening
    assert '--market hk --render-page' in opening
    assert 'HK_HEATMAP_GENERATED_UTC' in opening
    assert 'touch "$RUNNER_TEMP/hk-heatmap-failed"' in opening
    assert 'git checkout HEAD -- site/marketdata/hk_heatmap.json site/hk_heatmap.html' in opening
    engine=workflow[workflow.index("name: commit engine outputs"):]
    assert engine.count('python -m scripts.build_market_heatmap --market hk --render-page')==2
    assert 'git checkout origin/main -- site/marketdata/hk_heatmap.json site/hk_heatmap.html' in engine
    assert 'render-heal: hold stale HK heatmap at origin main' in engine
    tail=workflow[workflow.index("name: fail if China/HK heatmap missed settled close"):]
    assert 'if [ -f "$RUNNER_TEMP/hk-heatmap-failed" ]' in tail
    assert 'if [ "$failed" -ne 0 ]; then exit 1; fi' in tail
    assert "id: publish_hk_heatmap" in dag
    assert "module: scripts.build_market_heatmap" in dag


def test_hk_deep_source_reuses_adjusted_breadth_cache_for_completed_day():
    """Same existing HK stock owner, no new provider and 95% exact session."""
    from collectors.hk_closes_deep import reconcile_settled_hk_cache
    names=[f"{i:04d}.HK" for i in range(1,161)]
    days=pd.to_datetime(["2026-10-08","2026-10-09"])
    baseline=pd.DataFrame({s:[99.,100.] for s in names},index=days)
    cache=pd.DataFrame({s:[99.,100.,101. if i<152 else float("nan")]
                        for i,s in enumerate(names)},
                      index=pd.to_datetime(["2026-10-08","2026-10-09","2026-10-12"]))
    before=baseline.copy(deep=True)
    result=reconcile_settled_hk_cache(
        baseline,names,cache=cache,reference=baseline,
        now=datetime(2026,10,12,12,tzinfo=timezone.utc))
    assert result.index.max()==pd.Timestamp("2026-10-12")
    assert int(result.loc["2026-10-12"].notna().sum())==152
    assert pd.isna(result.at[pd.Timestamp("2026-10-12"),names[-1]])
    pd.testing.assert_frame_equal(before,baseline)
    assert (result.loc["2026-10-09"]==100.).all()


def test_hk_deep_source_never_rebases_different_adjustment_histories():
    import pytest
    from collectors.hk_closes_deep import reconcile_settled_hk_cache
    names=[f"{i:04d}.HK" for i in range(1,21)]
    dates=pd.to_datetime(["2026-10-08","2026-10-09"])
    baseline=pd.DataFrame({s:[99.,100.] for s in names},index=dates)
    cache=pd.DataFrame({s:[99.,100.,101.] for s in names},
                       index=pd.to_datetime(["2026-10-08","2026-10-09","2026-10-12"]))
    for name in names[18:]:
        cache.loc["2026-10-09",name]=105.
    with pytest.raises(RuntimeError,match="18/20"):
        reconcile_settled_hk_cache(
            baseline,names,cache=cache,reference=baseline,
            now=datetime(2026,10,12,12,tzinfo=timezone.utc))
    assert baseline.index.max()==pd.Timestamp("2026-10-09")


def test_hk_deep_source_respects_1730_hkt_settlement():
    from collectors.hk_closes_deep import reconcile_settled_hk_cache
    names=[f"{i:04d}.HK" for i in range(1,21)]
    dates=pd.to_datetime(["2026-10-08","2026-10-09"])
    baseline=pd.DataFrame({s:[99.,100.] for s in names},index=dates)
    cache=pd.DataFrame({s:[99.,100.,101.] for s in names},
                       index=pd.to_datetime(["2026-10-08","2026-10-09","2026-10-12"]))
    before_close=reconcile_settled_hk_cache(
        baseline,names,cache=cache,reference=baseline,
        now=datetime(2026,10,12,8,30,tzinfo=timezone.utc))
    assert before_close.index.max()==pd.Timestamp("2026-10-09")
    assert pd.Timestamp("2026-10-12") not in before_close.index


def test_hk_deep_owner_orders_after_breadth_in_existing_asia_shard():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[1]/"scripts/collect.py").read_text()
    assert src.index('("hk_breadth", "collectors.hk_breadth"') < src.index(
        '("hk_closes_deep", "collectors.hk_closes_deep"')
    assert 'serial_keys = [k for k in registry if k not in _CONCURRENT_HOSTS]' in src


def test_hk_deep_cold_runner_preserves_published_close_without_breadth_cache():
    """A missed Actions cache restore cannot erase a qualified deep close."""
    from collectors.hk_closes_deep import reconcile_settled_hk_cache
    names=[f"{i:04d}.HK" for i in range(1,161)]
    old=pd.DataFrame({s:[99.,100.] for s in names},
                     index=pd.to_datetime(["2026-10-08","2026-10-09"]))
    durable=old.copy()
    durable.loc[pd.Timestamp("2026-10-12"),:] = float("nan")
    for t in names[:153]:
        durable.at[pd.Timestamp("2026-10-12"),t]=101.
    out=reconcile_settled_hk_cache(
        old,names,cache=None,reference=durable,
        now=datetime(2026,10,13,6,45,tzinfo=timezone.utc))
    assert out.index.max()==pd.Timestamp("2026-10-12")
    assert int(out.loc["2026-10-12"].notna().sum())==153
    assert (out.loc["2026-10-09"]==100.).all()


def test_hk_deep_cold_runner_rejects_unverified_stored_prices():
    from collectors.hk_closes_deep import reconcile_settled_hk_cache
    names=[f"{i:04d}.HK" for i in range(1,21)]
    old=pd.DataFrame({s:[99.,100.] for s in names},
                     index=pd.to_datetime(["2026-10-08","2026-10-09"]))
    wrong=old.copy()
    wrong.loc[pd.Timestamp("2026-10-12"),:] = 101.
    # A forged back-adjusted reference that disagrees on the prior close can
    # never be laundered through the durable-store fallback.
    for ticker in names[18:]:
        wrong.loc["2026-10-09",ticker]=105.
    import pytest
    with pytest.raises(RuntimeError,match="18/20"):
        reconcile_settled_hk_cache(
            old,names,cache=None,reference=wrong,
            now=datetime(2026,10,13,6,45,tzinfo=timezone.utc))
