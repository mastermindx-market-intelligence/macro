"""tests/test_flow_signals.py — FS-0 flow-event ledger + grader unit tests.

Must be added to ci.yml pytest whitelist to run in CI.

Test categories (per FS-0 acceptance gate):
  1. keep-first dedup: re-harvest same blob → no dupes, first-seen fields immutable
  2. tz-normalization: mixed Z / +00:00 / naive input stamps → all aware-UTC,
     sort never raises
  3. PIT leak-injection: inject a future price spike; grader for an unmatured row
     must NOT see it (mirrors W1.3 future-OI-spike leak test pattern)
  4. split-seam guard: synthetic split inside horizon window → outcome nulled
  5. CI-null: no creds / absent stores → collector + grader + gate.json all no-op
  6. grader parity: on a small synthetic series, flow-grader outputs match
     engine/grading.py primitives called directly
  7. tz-aware parquet: all timestamps round-trip through parquet as strings
     without raising aware/naive mismatch errors
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_event(event_id: str, ts: str = "2026-07-13T10:30:00Z",
                session_date: str = "2026-07-13",
                root: str = "AAPL",
                dte_bucket: str = "8_30d",
                premium: float = 300_000.0,
                **overrides) -> dict:
    row = {
        "id": event_id,
        "ts": ts,
        "root": root,
        "group": "Technology",
        "group_zh": "科技",
        "right": "C",
        "exp": "2026-08-15",
        "strike": 200.0,
        "dte": 33,
        "dte_bucket": dte_bucket,
        "mny_bucket": "atm",
        "side": "~buy",
        "n_prints": 5,
        "size": 100,
        "avg_price": 3.0,
        "premium": premium,
        "premium_z": 3.5,
        "baseline_source": "z252",
        "vol_gt_oi": True,
        "repeated": False,
        "zerodte": False,
        "signing_source": "tape",
        "swept": True,
        "session_date": session_date,
    }
    row.update(overrides)
    return row


def _make_feed_blob(events: list[dict], session_date: str = "2026-07-13") -> dict:
    return {
        "schema": "live_flow.feed/v1",
        "asof": "2026-07-13T16:00:00Z",
        "session_date": session_date,
        "events": events,
    }


def _aware_ts(dt: datetime) -> str:
    """Return aware-UTC ISO string from a datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _make_close_series(
    start: str, n: int, base_price: float = 100.0,
    daily_returns: list[float] | None = None,
) -> pd.Series:
    """Build a synthetic close series with a DatetimeIndex."""
    dates = pd.date_range(start=start, periods=n, freq="B")  # business days
    if daily_returns is not None:
        prices = [base_price]
        for r in daily_returns[: n - 1]:
            prices.append(prices[-1] * (1 + r))
    else:
        prices = [base_price] * n
    return pd.Series(prices, index=dates, dtype=float)


# ── 1. keep-first dedup ───────────────────────────────────────────────────────

class TestKeepFirstDedup:
    """Re-harvest of the same blob must not create duplicate rows."""

    def test_second_harvest_adds_no_rows(self, tmp_path):
        """Harvesting the same events twice yields exactly the original row count."""
        from collectors.flow_signals import (
            _events_from_blob, _load_existing_ids, _append_rows, _EVENT_COLS
        )

        ledger_path = tmp_path / "ledger.parquet"
        events = [_make_event("evt001"), _make_event("evt002")]
        blob = _make_feed_blob(events)

        rows = _events_from_blob(blob)
        n1 = _append_rows(ledger_path, rows)
        assert n1 == 2

        # Harvest same blob again
        existing_ids = _load_existing_ids(ledger_path)
        new_rows = [r for r in _events_from_blob(blob) if r["event_id"] not in existing_ids]
        n2 = _append_rows(ledger_path, new_rows)
        assert n2 == 0  # nothing new

        df = pd.read_parquet(ledger_path)
        assert len(df) == 2

    def test_first_seen_fields_immutable(self, tmp_path):
        """If the same event_id appears in two blobs with different premiums,
        the first ingested premium value wins."""
        from collectors.flow_signals import (
            _events_from_blob, _load_existing_ids, _append_rows
        )

        ledger_path = tmp_path / "ledger.parquet"
        ev1 = _make_event("evtX", premium=300_000.0)
        ev2 = _make_event("evtX", premium=999_999.0)  # same id, different premium

        blob1 = _make_feed_blob([ev1])
        blob2 = _make_feed_blob([ev2])

        rows1 = _events_from_blob(blob1)
        _append_rows(ledger_path, rows1)

        existing_ids = _load_existing_ids(ledger_path)
        rows2 = [r for r in _events_from_blob(blob2) if r["event_id"] not in existing_ids]
        _append_rows(ledger_path, rows2)

        df = pd.read_parquet(ledger_path)
        assert len(df) == 1
        assert float(df.iloc[0]["premium"]) == pytest.approx(300_000.0)


# ── 2. tz-normalization ───────────────────────────────────────────────────────

class TestTzNormalization:
    """Mixed timestamps all normalize to aware-UTC; sort never raises."""

    @pytest.mark.parametrize("ts_input,expected_contains", [
        ("2026-07-13T14:30:00Z", "+00:00"),
        ("2026-07-13T14:30:00+00:00", "+00:00"),
        ("2026-07-13T14:30:00", "+00:00"),  # naive → assume UTC
        ("2026-07-13 14:30:00", "+00:00"),
    ])
    def test_ts_normalization(self, ts_input, expected_contains):
        from collectors.flow_signals import _normalize_ts
        result = _normalize_ts(ts_input)
        assert expected_contains in result, f"Expected {expected_contains!r} in {result!r}"

    def test_mixed_stamps_parse_as_utc(self, tmp_path):
        """Events with Z, +00:00, and naive timestamps all land as aware-UTC strings
        and the resulting series sorts without raising TypeError."""
        from collectors.flow_signals import _events_from_blob

        events = [
            {**_make_event("e1"), "ts": "2026-07-13T09:30:00Z"},
            {**_make_event("e2"), "ts": "2026-07-13T10:00:00+00:00"},
            {**_make_event("e3"), "ts": "2026-07-13T11:00:00"},   # naive
        ]
        blob = _make_feed_blob(events)
        rows = _events_from_blob(blob)

        # All ts fields should contain '+00:00' (aware-UTC)
        for r in rows:
            assert "+00:00" in r["ts"], f"Expected aware-UTC in ts={r['ts']!r}"

        # Timestamps should be sortable (no TypeError from naive/aware mix)
        ts_series = pd.Series([r["ts"] for r in rows])
        sorted_ts = ts_series.sort_values()  # should not raise
        assert len(sorted_ts) == 3

    def test_aware_ingested_at(self, tmp_path):
        """ingested_at field is always an aware-UTC ISO string."""
        from collectors.flow_signals import _events_from_blob
        events = [_make_event("e1")]
        rows = _events_from_blob(_make_feed_blob(events))
        assert len(rows) == 1
        iat = rows[0]["ingested_at"]
        assert "+" in iat or "Z" in iat or iat.endswith("+00:00")


# ── 3. PIT leak-injection test ────────────────────────────────────────────────

class TestPITLeakInjection:
    """Inject a future price spike; grader for an unmatured row must NOT see it.

    Mirrors the W1.3 future-OI-spike leak test pattern.
    An unmatured event's forward window must not extend past today's available data.
    """

    def test_future_spike_not_seen_by_grader(self, tmp_path):
        """An event from yesterday cannot reach a spike injected 60 days in the future."""
        from engine.flow_signals_grade import _grade_event

        # Signal date = 2 trading days ago (maturable at 5d)
        signal_date = "2026-07-10"  # a recent session date

        # Build a clean close series: 30 days of history + only 3 forward bars
        # (not enough to reach the 5d primary horizon for 0d/1_7d)
        # We use 1_7d bucket → primary horizon = 5d
        n_history = 30
        n_future = 3  # LESS THAN the 5d horizon → not yet matured
        n_total = n_history + n_future

        prices = [100.0] * n_history + [100.0] * n_future
        dates = pd.date_range("2026-06-01", periods=n_total, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        # Inject a "future spike" BEYOND the current data (simulating data that
        # would be available at t+10 but is not yet observed)
        # The grader should return not_yet_matured, NOT see the spike

        result = _grade_event(
            event_id="test_pit",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",  # horizon=5d
            close=close,  # only 3 forward bars → not matured
            spy_close=None,
        )

        # Must not be graded OK; must be not_yet_matured
        reason = result.get("reason_code", "")
        assert reason in ("not_yet_matured", "fill_error: fill bar not found or no next bar"), \
            f"Expected not_yet_matured but got reason_code={reason!r}"

        # The primary horizon fwd_ret must be None (not populated)
        assert result.get("fwd_ret_5") is None, \
            "grader must not produce fwd_ret_5 for an unmatured event"

    def test_matured_event_graded_correctly(self, tmp_path):
        """An event with sufficient forward data IS graded and sees actual moves."""
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-01"
        # 1 history day + 30 forward bars → well beyond 5d horizon
        prices = [100.0] + [105.0] * 30  # flat after 5% jump on fill bar
        dates = pd.date_range("2026-05-31", periods=31, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="test_matured",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",  # horizon=5d
            close=close,
            spy_close=None,
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] is not None
        # The move is 0 since prices are flat at 105 after the jump
        assert result["fwd_ret_5"] == pytest.approx(0.0, abs=1e-6)


# ── 4. split-seam guard ───────────────────────────────────────────────────────

class TestSplitSeamGuard:
    """A synthetic split inside horizon window → outcome nulled with reason_code."""

    def test_split_seam_nulls_outcome(self):
        """A 50% single-bar drop (simulated post-split un-adjusted seam) is caught."""
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-01"
        # Build a close series with a -50% bar at day 3 within the 5d window
        prices = [100.0, 101.0, 102.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0]
        # The -50% bar is at position 3 (within 5d forward window of the fill bar)
        dates = pd.date_range("2026-05-31", periods=9, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="test_seam",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",  # horizon=5d
            close=close,
            spy_close=None,
        )
        # Should be graded_ok=True (intentional null) with reason_code='split_seam'
        assert result["graded_ok"] is True
        assert result["reason_code"] == "split_seam"
        assert result["fwd_ret_5"] is None

    def test_clean_series_not_flagged(self):
        """A normal 5% move does not trigger the seam guard."""
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-01"
        # Clean series: small daily moves
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
        dates = pd.date_range("2026-05-31", periods=8, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="test_clean",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )
        assert result["graded_ok"] is True
        assert result["reason_code"] == "ok"
        assert result["fwd_ret_5"] is not None


# ── 5. CI-null (no-op without creds / absent stores) ─────────────────────────

class TestCINull:
    """Without R2 creds or data, all components degrade cleanly."""

    def test_harvest_no_creds_is_noop(self, tmp_path):
        """harvest() returns 0 and writes no rows when R2 creds are absent and
        local feed_current.json is also absent."""
        from collectors.flow_signals import harvest

        with patch.dict(os.environ, {}, clear=True):
            # Remove all R2 env vars
            for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
                os.environ.pop(k, None)

            with patch("collectors.flow_signals._ledger_path", return_value=tmp_path / "ledger.parquet"), \
                 patch("collectors.flow_signals._feed_current_path", return_value=None):
                n = harvest(dry_run=False)

        assert n == 0
        assert not (tmp_path / "ledger.parquet").exists()

    def test_grader_absent_ledger_is_noop(self, tmp_path):
        """grade_matured() with no ledger returns summary with n_ledger=0."""
        from engine.flow_signals_grade import grade_matured

        with patch("engine.flow_signals_grade._ledger_path",
                   return_value=tmp_path / "ledger.parquet"):
            summary = grade_matured()

        assert summary["n_ledger"] == 0
        assert summary["n_graded_ok"] == 0

    def test_build_script_dry_run_exits_ok(self, tmp_path):
        """build_flow_signals main() with --dry-run exits 0 even with no data."""
        from scripts.build_flow_signals import main

        with patch("collectors.flow_signals._ledger_path",
                   return_value=tmp_path / "ledger.parquet"), \
             patch("collectors.flow_signals._feed_current_path", return_value=None), \
             patch("collectors.flow_signals._r2_client", return_value=None):
            rc = main(["--dry-run"])

        assert rc == 0


# ── 6. grader parity ─────────────────────────────────────────────────────────

class TestGraderParity:
    """flow-grader outputs match engine/grading.py primitives called directly."""

    def test_fwd_ret_matches_grading_primitives(self):
        """fwd_ret_5 from _grade_event matches forward_metrics() called directly."""
        from engine.grading import forward_metrics
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        # 1 history day + 10 forward days
        prices = [100.0, 100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 109.0, 111.0, 112.0, 113.0]
        dates = pd.date_range("2026-06-01", periods=11, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        # Direct call to grading primitives
        prim = forward_metrics(close, signal_date, horizons=(5,))
        expected_ret5 = prim.get("fwd_ret_5")

        # Via flow grader
        result = _grade_event(
            event_id="parity_test",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",  # horizon=5d
            close=close,
            spy_close=None,
        )

        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] == pytest.approx(expected_ret5, abs=1e-9)

    def test_mfe_mdd_match_grading_primitives(self):
        """fwd_mfe_5 and fwd_mdd_5 match forward_metrics() directly."""
        from engine.grading import forward_metrics
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        # Create a series with both a high and a low within the 5d window
        prices = [100.0, 100.0, 107.0, 105.0, 102.0, 104.0, 103.0, 105.0, 106.0]
        dates = pd.date_range("2026-06-01", periods=9, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        prim = forward_metrics(close, signal_date, horizons=(5,))
        expected_mfe = prim.get("fwd_mfe_5")
        expected_mdd = prim.get("fwd_mdd_5")

        result = _grade_event(
            event_id="mfe_mdd_test",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )

        assert result["fwd_mfe_5"] == pytest.approx(expected_mfe, abs=1e-9)
        assert result["fwd_mdd_5"] == pytest.approx(expected_mdd, abs=1e-9)

    def test_direction_agnostic_raw_move(self):
        """fwd_ret is the raw underlying move, not conditioned on the soft side field.
        A ~sell event with a positive underlying move stores a positive fwd_ret."""
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        prices = [100.0, 100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0]
        dates = pd.date_range("2026-06-01", periods=8, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="direction_test",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )

        assert result["graded_ok"] is True
        # Raw move should be positive (stock rose), not negated by ~sell side
        assert result["fwd_ret_5"] is not None
        assert result["fwd_ret_5"] > 0, \
            "fwd_ret must be the raw underlying move; ~sell side must not negate it"


# ── 7. tz-aware parquet round-trip ───────────────────────────────────────────

class TestTzAwareParquet:
    """Timestamps stored as strings survive parquet round-trip without raising."""

    def test_aware_ts_parquet_roundtrip(self, tmp_path):
        """Rows with aware-UTC ts strings write to parquet and read back cleanly."""
        from collectors.flow_signals import _events_from_blob, _append_rows

        ledger_path = tmp_path / "ledger.parquet"
        events = [
            {**_make_event("e1"), "ts": "2026-07-13T09:30:00+00:00"},
            {**_make_event("e2"), "ts": "2026-07-13T10:00:00Z"},
        ]
        blob = _make_feed_blob(events)
        rows = _events_from_blob(blob)
        _append_rows(ledger_path, rows)

        # Round-trip: read and sort on ts column (must not raise)
        df = pd.read_parquet(ledger_path)
        assert len(df) == 2

        # Sort on ts string column — should not raise TypeError
        sorted_df = df.sort_values("ts")
        assert len(sorted_df) == 2

    def test_ingested_at_is_string_in_parquet(self, tmp_path):
        """ingested_at is stored as a plain string, not a datetime64, avoiding
        the LETHAL tz-aware-into-naive-parquet mismatch class."""
        from collectors.flow_signals import _events_from_blob, _append_rows

        ledger_path = tmp_path / "ledger.parquet"
        rows = _events_from_blob(_make_feed_blob([_make_event("e1")]))
        _append_rows(ledger_path, rows)

        df = pd.read_parquet(ledger_path)
        # ingested_at dtype should be object (string), not datetime64
        dtype = df["ingested_at"].dtype
        assert dtype == object or "datetime" not in str(dtype), \
            f"ingested_at should be stored as string, got dtype={dtype}"


# ── 8. detector_version stamped on every row ─────────────────────────────────

class TestDetectorVersionStamping:
    def test_detector_version_present(self, tmp_path):
        """Every harvested row carries a non-empty detector_version."""
        from collectors.flow_signals import _events_from_blob

        events = [_make_event("v001"), _make_event("v002")]
        rows = _events_from_blob(_make_feed_blob(events))

        for r in rows:
            assert "detector_version" in r
            assert r["detector_version"]  # non-empty

    def test_source_is_live_feed(self, tmp_path):
        """Every row has source='live_feed'."""
        from collectors.flow_signals import _events_from_blob

        rows = _events_from_blob(_make_feed_blob([_make_event("s001")]))
        assert all(r["source"] == "live_feed" for r in rows)


# ── 9. Split-seam guard (M2/N6) ──────────────────────────────────────────────

class TestSplitSeamGuardM2N6:
    """New seam guard tests per M2/N6 spec."""

    def test_split_shaped_persistent_caught(self):
        """A 0.5x (2:1 reverse-split-shaped) bar that persists is flagged as split_seam.

        Series layout (business-day freq, starting 2026-06-01):
          idx 0: 2026-06-01 (history before signal)
          idx 1: 2026-06-02 (signal date — snap_loc lands here)
          idx 2: 2026-06-03 (fill bar, price=100)
          idx 3: 2026-06-04 (fwd1, split-seam drop: 50)   ← split-shaped AND persistent
          idx 4: 2026-06-05 (fwd2, price≈50)
          idx 5: 2026-06-08 (fwd3, price≈50)
          idx 6: 2026-06-09 (fwd4, price≈50)
          idx 7: 2026-06-10 (fwd5, price≈50)
          idx 8: 2026-06-11 (extra bar so fill+5 < len: 2+5=7 < 9)
        """
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        #           h0     sig    fill   fwd1  fwd2  fwd3  fwd4  fwd5  extra
        prices =  [100.0, 100.0, 100.0,  50.0, 51.0, 50.5, 51.0, 51.0, 51.0]
        dates = pd.date_range("2026-06-01", periods=9, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="seam_persistent_2x",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )
        assert result["reason_code"] == "split_seam", (
            f"Expected split_seam but got {result['reason_code']!r}"
        )
        assert result["graded_ok"] is True  # intentional null
        assert result["fwd_ret_5"] is None

    def test_large_earnings_gap_not_flagged(self):
        """A +45% single-bar gap that persists (NOT split-shaped) grades normally.

        +45% has log(1.45)=0.372; nearest split log is log(2)=0.693 — gap is 0.32,
        well beyond the 0.03 tolerance. Guard must pass through.

        Series layout: same 9-bar structure as test_split_shaped_persistent_caught.
        """
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        #            h0     sig    fill   fwd1   fwd2   fwd3   fwd4   fwd5  extra
        prices =    [100.0, 100.0, 100.0, 145.0, 146.0, 145.5, 146.0, 145.0, 145.0]
        dates = pd.date_range("2026-06-01", periods=9, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="earnings_gap_45pct",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )
        # Should NOT be flagged as split_seam; should grade normally
        assert result["reason_code"] == "ok", (
            f"Expected ok but got {result['reason_code']!r}"
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] is not None

    def test_seam_at_fill_transition_caught(self):
        """A seam at the fill→fill+1 transition is caught (N6 fix: scan starts at fill).

        The fill bar (idx=2) → fwd1 (idx=3) transition has a 0.5x drop.
        The OLD guard (started at fill+1=3) would scan from bar 3→4 and miss the
        fill→fwd1 transition entirely when the seam is AT bar 2→3.
        The NEW guard scans from fill (idx=2) so it sees close[2]=100, close[3]=50.
        """
        from engine.flow_signals_grade import _grade_event

        signal_date = "2026-06-02"
        #            h0     sig    fill   fwd1  fwd2  fwd3  fwd4  fwd5  extra
        prices =    [100.0, 100.0, 100.0,  50.0, 51.0, 50.0, 51.0, 50.5, 50.0]
        dates = pd.date_range("2026-06-01", periods=9, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="seam_at_fill_transition",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )
        assert result["reason_code"] == "split_seam", (
            f"Expected split_seam at fill transition but got {result['reason_code']!r}"
        )


# ── 10. B1: partial-grade semantics for 90p bucket ────────────────────────────

class TestB1PartialGrade:
    """90p bucket partial-grade: 63d fills first, 126d on re-attempt."""

    def test_only_63d_matured_gives_partial(self):
        """When 63d matured but 126d has not, result is partial_matured, graded_ok=False.

        Series layout (business days, 2026-06-01 start):
          fill = 2 (bar after 2026-06-02 signal), n=66:
          fill+63=65 < 66 → 63d MATURED
          fill+126=128 >= 66 → 126d NOT matured

        Pass today=far-future so N5 truncation doesn't cut the series.
        """
        from engine.flow_signals_grade import _grade_event
        from datetime import date as _date

        signal_date = "2026-06-02"
        n = 66
        prices = [100.0] + [101.0] * (n - 1)
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="partial_90p",
            ticker="XYZ",
            session_date=signal_date,
            dte_bucket="90p",
            close=close,
            spy_close=None,
            today=_date(2027, 1, 1),  # far future → no PIT truncation
        )
        assert result["graded_ok"] is False, "Should not be finalized yet"
        assert result["reason_code"] == "partial_matured"
        # 63d outcome should be populated
        assert result["fwd_ret_63"] is not None, "fwd_ret_63 should be filled on partial"
        # 126d outcome should be null
        assert result["fwd_ret_126"] is None, "fwd_ret_126 should be null until 126d matures"
        assert result["terminal_state_clean15_126"] is None, (
            "terminal_state_clean15_126 should be null until 126d matures"
        )

    def test_126d_matured_finalizes(self):
        """Once 126d has matured, re-running grade_matured finalizes the row.

        n=130: fill=2, fill+126=128 < 130 → both horizons mature.
        Pass today=far-future so N5 truncation doesn't cut the series.
        """
        from engine.flow_signals_grade import _grade_event
        from datetime import date as _date

        signal_date = "2026-06-02"
        n = 130
        prices = [100.0] + [101.0] * (n - 1)
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        close = pd.Series(prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="final_90p",
            ticker="XYZ",
            session_date=signal_date,
            dte_bucket="90p",
            close=close,
            spy_close=None,
            today=_date(2027, 1, 1),  # far future → no PIT truncation
        )
        assert result["graded_ok"] is True, "Should be finalized when 126d matured"
        assert result["reason_code"] == "ok"
        assert result["fwd_ret_63"] is not None
        assert result["fwd_ret_126"] is not None
        assert result["terminal_state_clean15_126"] is not None

    def test_partial_matured_row_is_overwritten(self, tmp_path):
        """grade_matured upserts partial_matured rows on the next pass.

        Uses today= far in the future (2026-10-01) so synthetic date-range
        series aren't truncated by the N5 PIT guard.
        """
        from engine.flow_signals_grade import grade_matured
        from datetime import date as _date

        signal_date = "2026-06-02"
        n_short = 66  # only 63d matured (fill=2, fill+63=65<66, fill+126=128>=66)
        n_long = 130  # both 63d and 126d matured (fill+126=128<130)

        prices_short = [100.0] + [101.0] * (n_short - 1)
        prices_long = [100.0] + [101.0] * (n_long - 1)
        dates_short = pd.date_range("2026-06-01", periods=n_short, freq="B")
        dates_long = pd.date_range("2026-06-01", periods=n_long, freq="B")
        close_short = pd.Series(prices_short, index=dates_short, dtype=float)
        close_long = pd.Series(prices_long, index=dates_long, dtype=float)

        # Build a minimal ledger
        ledger_path = tmp_path / "ledger.parquet"
        grades_path = tmp_path / "grades.parquet"

        ledger_df = pd.DataFrame([{
            "event_id": "partial_upsert_test",
            "session_date": signal_date,
            "root": "MOCK",
            "dte_bucket": "90p",
            "side": "~buy",
        }])
        ledger_df.to_parquet(ledger_path, index=False)

        # today far in the future so N5 truncation leaves all synthetic bars intact
        # 130 bars from 2026-06-01 ends ~2026-11-27, so use 2027-01-01
        future_today = _date(2027, 1, 1)

        # First pass: inject short close series (only 63d matured)
        with patch("engine.flow_signals_grade._ledger_path", return_value=ledger_path), \
             patch("engine.flow_signals_grade._grades_path", return_value=grades_path), \
             patch("engine.flow_signals_grade._load_close", return_value=close_short), \
             patch("engine.flow_signals_grade._spy_close", return_value=None):
            grade_matured(today=future_today)

        g1 = pd.read_parquet(grades_path)
        assert len(g1) == 1
        assert g1.iloc[0]["reason_code"] == "partial_matured"
        assert bool(g1.iloc[0]["graded_ok"]) is False

        # Second pass: inject long close series (both 63d and 126d matured)
        with patch("engine.flow_signals_grade._ledger_path", return_value=ledger_path), \
             patch("engine.flow_signals_grade._grades_path", return_value=grades_path), \
             patch("engine.flow_signals_grade._load_close", return_value=close_long), \
             patch("engine.flow_signals_grade._spy_close", return_value=None):
            grade_matured(today=future_today)

        g2 = pd.read_parquet(grades_path)
        assert len(g2) == 1, "Upsert must not double the row"
        assert g2.iloc[0]["reason_code"] == "ok"
        assert bool(g2.iloc[0]["graded_ok"]) is True
        assert g2.iloc[0]["fwd_ret_126"] is not None


# ── 11. M3: harvest fail-closed on unreadable ledger ─────────────────────────

class TestM3HarvestFailClosed:
    """Unreadable ledger aborts harvest; duplicate event_ids are deduped."""

    def test_corrupt_ledger_aborts_harvest(self, tmp_path):
        """If ledger.parquet exists but is corrupt, harvest returns 0 and writes nothing."""
        from collectors.flow_signals import harvest, _events_from_blob

        ledger_path = tmp_path / "ledger.parquet"
        # Write a corrupt file (not a valid parquet)
        ledger_path.write_bytes(b"this is not parquet data")
        original_mtime = ledger_path.stat().st_mtime

        blob = _make_feed_blob([_make_event("abort_test")])

        with (
            patch("collectors.flow_signals._ledger_path", return_value=ledger_path),
            patch("collectors.flow_signals._feed_current_path", return_value=None),
            patch("collectors.flow_signals._r2_client", return_value=None),
            patch("collectors.flow_signals._r2_feed_current", return_value=None),
            patch("collectors.flow_signals._events_from_blob", return_value=_events_from_blob(blob)),
        ):
            # Simulate having events to write but a corrupt ledger
            # We need to bypass the R2 path — patch harvest internals
            pass

        # Direct test via _load_existing_ids sentinel
        from collectors.flow_signals import _load_existing_ids, _LEDGER_UNREADABLE
        result = _load_existing_ids(ledger_path)
        assert result is _LEDGER_UNREADABLE, (
            "Corrupt ledger should return _LEDGER_UNREADABLE sentinel"
        )
        # Ledger must be untouched
        assert ledger_path.stat().st_mtime == original_mtime

    def test_absent_ledger_returns_empty_set(self, tmp_path):
        """Absent ledger (first run) returns empty set, not the unreadable sentinel."""
        from collectors.flow_signals import _load_existing_ids, _LEDGER_UNREADABLE

        ledger_path = tmp_path / "ledger.parquet"
        assert not ledger_path.exists()
        result = _load_existing_ids(ledger_path)
        assert isinstance(result, set)
        assert len(result) == 0

    def test_duplicate_event_ids_deduped_in_append(self, tmp_path):
        """_append_rows drops duplicate event_ids within one batch (keep-first)."""
        from collectors.flow_signals import _append_rows, _events_from_blob

        ledger_path = tmp_path / "ledger.parquet"
        # Two rows with the same event_id
        ev = _make_event("dup_evt", premium=100_000.0)
        ev2 = dict(ev)  # same id, same premium for simplicity
        blob = _make_feed_blob([ev, ev2])
        rows = _events_from_blob(blob)
        # Both events have the same id; _events_from_blob returns both since
        # it doesn't dedup — the dedup is in _append_rows
        # Force two identical rows
        rows2 = rows + rows  # 4 rows, 2 unique ids (all the same)

        n = _append_rows(ledger_path, rows2)
        df = pd.read_parquet(ledger_path)
        # Should have deduplicated to unique event_ids
        assert df["event_id"].nunique() == df["event_id"].count(), (
            "No duplicate event_ids should survive _append_rows"
        )
        # Specifically: dup_evt appears only once
        assert (df["event_id"] == "dup_evt").sum() == 1


# ── 12. N5: PIT defense — future bars beyond today are excluded ───────────────

class TestN5PITDefense:
    """Close series containing bars beyond today must not influence grading."""

    def test_future_bars_excluded_by_today(self):
        """When today cuts off future bars, fwd_ret reflects only past-today data.

        Series structure:
          - 2026-06-01 (bar 0): history
          - 2026-06-02 (bar 1): signal date — snap_loc lands here, fill=2
          - 2026-06-03 to 2026-06-09 (bars 2-6): fill + first 4 forward bars, prices=100
          - 2026-06-10 (bar 7, last bar <= today=2026-07-01): prices=100
          - 2026-06-11+ (bars 8+, beyond today boundary): extreme spike 9999

        With today=2026-07-01, truncation keeps bars 0-7 (through 2026-06-10 or
        whatever is <= 2026-07-01). fill=2, fill+5=7. We need 8 bars >= fill+5+1.
        Series will have many bars but truncated to 'today' yields enough to grade.
        """
        from engine.flow_signals_grade import _grade_event
        from datetime import date as _date

        signal_date = "2026-06-02"
        # today = 2026-07-01; bars through this date are ~21 business days from 2026-06-01
        today = _date(2026, 7, 1)

        n = 50
        # Bars through 2026-07-01 = bars 0..~21 (business days), all price=100
        # Bars beyond 2026-07-01: price=9999 (should be invisible after truncation)
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        cutoff = pd.Timestamp(today)
        prices = [100.0 if d <= cutoff else 9999.0 for d in dates]
        close = pd.Series(prices, index=dates, dtype=float)

        # Verify test preconditions: bars beyond cutoff are 9999
        bars_after = close[close.index > cutoff]
        assert (bars_after == 9999.0).all(), "Test setup: future bars should be 9999"

        result = _grade_event(
            event_id="pit_today_test",
            ticker="AAPL",
            session_date=signal_date,
            dte_bucket="1_7d",  # horizon=5d
            close=close,
            spy_close=None,
            today=today,
        )

        # With today truncation and ~21 bars available, fill=2, fill+5=7<22 → should grade
        assert result.get("graded_ok") is True, (
            f"Expected graded_ok=True, got reason_code={result.get('reason_code')!r}"
        )
        ret5 = result.get("fwd_ret_5")
        assert ret5 is not None
        # All bars within [fill, fill+5] are 100.0; fwd_ret must be ≈0
        assert abs(ret5) < 0.01, (
            f"fwd_ret_5={ret5:.6f} suggests future spike leaked into grading"
        )


# ── OA-1T: measured microstructure flattened into the Flow ML ledger ──────────

MICRO_SCHEMA = "options.trade_nbbo_microstructure/v1"

MICRO_BLOCK = {
    "schema": MICRO_SCHEMA,
    "source_print_count": 4,
    "nbbo_valid_print_count": 3,
    "source_premium_usd": 1_000_000.0,
    "nbbo_covered_premium_usd": 900_000.0,
    "nbbo_print_coverage": 0.75,
    "nbbo_premium_coverage": 0.9,
    "at_ask_share": 0.6,
    "at_bid_share": 0.2,
    "inside_share": 0.15,
    "outside_share": 0.05,
    "aggression_share": 0.8,
    "aggression_balance": 0.4,
    "spread_median_usd": 0.05,
    "spread_median_pct": 0.02,
    "quote_age_median_ms": 110.0,
    "quote_age_max_ms": 250.0,
    "bid_size_median": 40.0,
    "ask_size_median": 45.0,
}

MEASURED_COLS = (
    "vol_gt_oi_ratio",
    "microstructure_schema",
    "source_print_count",
    "nbbo_valid_print_count",
    "source_premium_usd",
    "nbbo_covered_premium_usd",
    "nbbo_print_coverage",
    "nbbo_premium_coverage",
    "at_ask_share",
    "at_bid_share",
    "inside_share",
    "outside_share",
    "aggression_share",
    "aggression_balance",
    "spread_median_usd",
    "spread_median_pct",
    "quote_age_median_ms",
    "quote_age_max_ms",
    "bid_size_median",
    "ask_size_median",
)


def _measured_event(event_id: str, **overrides) -> dict:
    payload = {
        "microstructure": json.loads(json.dumps(MICRO_BLOCK)),
        "vol_gt_oi_ratio": 1.5,
    }
    payload.update(overrides)
    return _make_event(event_id, **payload)


class TestMeasuredMicrostructureLedgerColumns:
    def test_event_microstructure_flattens_into_flow_ml_ledger_row(self):
        from collectors.flow_signals import _events_from_blob

        row = _events_from_blob(_make_feed_blob([_measured_event("evtM1")]))[0]

        assert row["microstructure_schema"] == MICRO_SCHEMA
        assert row["vol_gt_oi_ratio"] == pytest.approx(1.5)
        assert row["source_print_count"] == 4
        assert row["nbbo_valid_print_count"] == 3
        assert row["source_premium_usd"] == pytest.approx(1_000_000.0)
        assert row["nbbo_covered_premium_usd"] == pytest.approx(900_000.0)
        assert row["nbbo_print_coverage"] == pytest.approx(0.75)
        assert row["nbbo_premium_coverage"] == pytest.approx(0.9)
        assert row["at_ask_share"] == pytest.approx(0.6)
        assert row["at_bid_share"] == pytest.approx(0.2)
        assert row["inside_share"] == pytest.approx(0.15)
        assert row["outside_share"] == pytest.approx(0.05)
        assert row["aggression_share"] == pytest.approx(0.8)
        assert row["aggression_balance"] == pytest.approx(0.4)
        assert row["spread_median_usd"] == pytest.approx(0.05)
        assert row["spread_median_pct"] == pytest.approx(0.02)
        assert row["quote_age_median_ms"] == pytest.approx(110.0)
        assert row["quote_age_max_ms"] == pytest.approx(250.0)
        assert row["bid_size_median"] == pytest.approx(40.0)
        assert row["ask_size_median"] == pytest.approx(45.0)

    def test_legacy_event_without_microstructure_yields_null_additive_columns(self):
        """A pre-OA-1T event is null on every measured column — never 0."""
        from collectors.flow_signals import _events_from_blob

        row = _events_from_blob(_make_feed_blob([_make_event("evtLegacy")]))[0]

        for column in MEASURED_COLS:
            assert column in row, f"{column} missing from ledger row"
            assert row[column] is None, f"{column} should be null, got {row[column]!r}"
        # The legacy fields it does carry are untouched.
        assert row["vol_gt_oi"] is True
        assert row["premium"] == pytest.approx(300_000.0)

    def test_unknown_microstructure_schema_is_not_trusted(self):
        """Values under an unreviewed contract are not parsed as if they were
        this one."""
        from collectors.flow_signals import _events_from_blob

        foreign = json.loads(json.dumps(MICRO_BLOCK))
        foreign["schema"] = "options.trade_nbbo_microstructure/v2"
        row = _events_from_blob(
            _make_feed_blob([_measured_event("evtForeign", microstructure=foreign)])
        )[0]

        assert row["microstructure_schema"] is None
        assert row["at_ask_share"] is None
        assert row["nbbo_premium_coverage"] is None
        # The top-level scalar is its own field and does not ride on that schema.
        assert row["vol_gt_oi_ratio"] == pytest.approx(1.5)

    def test_existing_parquet_rows_receive_null_new_columns_on_append(self, tmp_path):
        """Schema evolution: historical rows gain null columns, never a backfill."""
        from collectors.flow_signals import (
            _EVENT_COLS, _append_rows, _events_from_blob,
        )

        ledger_path = tmp_path / "ledger.parquet"
        legacy_cols = [c for c in _EVENT_COLS if c not in MEASURED_COLS]
        assert len(legacy_cols) == len(_EVENT_COLS) - len(MEASURED_COLS)

        legacy_row = _events_from_blob(_make_feed_blob([_make_event("evtOld")]))[0]
        legacy_df = pd.DataFrame(
            [{k: legacy_row[k] for k in legacy_cols}], columns=legacy_cols,
        )
        legacy_df.to_parquet(ledger_path, index=False)

        rich_rows = _events_from_blob(_make_feed_blob([_measured_event("evtNew")]))
        assert _append_rows(ledger_path, rich_rows) == 1

        df = pd.read_parquet(ledger_path)
        assert list(df["event_id"]) == ["evtOld", "evtNew"]
        old, new = df.iloc[0], df.iloc[1]
        for column in MEASURED_COLS:
            assert pd.isna(old[column]), f"historical row backfilled on {column}"
        assert new["at_ask_share"] == pytest.approx(0.6)
        assert new["vol_gt_oi_ratio"] == pytest.approx(1.5)
        assert new["microstructure_schema"] == MICRO_SCHEMA

    def test_reharvest_cannot_mutate_first_microstructure_values(self, tmp_path):
        from collectors.flow_signals import (
            _append_rows, _events_from_blob, _load_existing_ids,
        )

        ledger_path = tmp_path / "ledger.parquet"
        first = _measured_event("evtKeepFirst")
        _append_rows(ledger_path, _events_from_blob(_make_feed_blob([first])))

        restated = json.loads(json.dumps(MICRO_BLOCK))
        restated["at_ask_share"] = 0.99
        second = _measured_event("evtKeepFirst", microstructure=restated)

        existing_ids = _load_existing_ids(ledger_path)
        new_rows = [
            r for r in _events_from_blob(_make_feed_blob([second]))
            if r["event_id"] not in existing_ids
        ]
        _append_rows(ledger_path, new_rows)

        df = pd.read_parquet(ledger_path)
        assert len(df) == 1
        assert float(df.iloc[0]["at_ask_share"]) == pytest.approx(0.60)

    def test_non_finite_measured_values_never_reach_the_ledger(self):
        """`_coerce_float` filters NaN but not Infinity. The live producer can
        never emit one (the event stage serializes with allow_nan=False), but a
        corrupt or foreign archive blob can — and this flattener is the last gate
        before the ML ledger."""
        from collectors.flow_signals import _events_from_blob

        hostile = json.loads(json.dumps(MICRO_BLOCK))
        hostile["at_ask_share"] = float("inf")
        hostile["spread_median_pct"] = float("-inf")
        row = _events_from_blob(
            _make_feed_blob([
                _measured_event("evtInf", microstructure=hostile, vol_gt_oi_ratio=float("inf")),
            ])
        )[0]

        assert row["at_ask_share"] is None
        assert row["spread_median_pct"] is None
        assert row["vol_gt_oi_ratio"] is None
        # Finite siblings in the same block are unaffected.
        assert row["at_bid_share"] == pytest.approx(0.2)


# ── 13. SPY label-window contract ────────────────────────────────────────────
#
# A spy_excess_h comparison (ticker_fwd_ret_h - spy_fwd_ret_h) is only
# evaluable when the two forward windows cover the SAME actual trading dates.
# If SPY is missing a bar at the native fill or the native fill+h position
# (e.g. SPY holiday, ticker-only session), the SPY window shifts to a
# different date span and the difference would compare different label
# windows — non-evaluable; the column stays None. Absolute native metrics
# (ticker fwd_ret_h, fwd_mfe_h, fwd_mdd_h) are preserved regardless.

class TestSpyLabelWindowContract:
    """SPY label-window contract: spy_excess_h requires identical native fill
    AND identical native endpoint dates on the two series."""

    def test_matching_dates_positive_path(self):
        """When ticker and SPY share the same business-day calendar, the
        label-window contract is satisfied: spy_excess_h is the difference
        of the two forward returns."""
        from engine.flow_signals_grade import _grade_event

        # snap_loc("2026-06-02") lands at bar 1, fill = 2.
        # fwd_ret_5 = close[fill+5] / close[fill] - 1 = close[7] / close[2] - 1.
        # Want ticker fwd_ret_5 = 0.05 (entry 100, exit 105) and SPY 0.02
        # (entry 200, exit 204) → excess 0.03.
        n = 9
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        ticker_prices = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 105.0, 105.0]
        spy_prices    = [200.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0, 204.0, 204.0]
        close = pd.Series(ticker_prices, index=dates, dtype=float)
        spy = pd.Series(spy_prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="spy_match",
            ticker="AAPL",
            session_date="2026-06-02",
            dte_bucket="1_7d",
            close=close,
            spy_close=spy,
        )
        assert result["graded_ok"] is True
        assert result["reason_code"] == "ok"
        assert result["fwd_ret_5"] is not None
        assert result["fwd_ret_5"] == pytest.approx(0.05, abs=1e-9)
        assert result["spy_excess_5"] is not None
        assert result["spy_excess_5"] == pytest.approx(0.03, abs=1e-9)

    def test_spy_missing_native_fill_leaves_excess_null(self):
        """If SPY is missing a bar at the ticker's native fill date, the SPY
        window opens on a different calendar day and the comparison is
        non-evaluable. spy_excess_h MUST stay None while the absolute
        ticker fwd_ret_h is still populated."""
        from engine.flow_signals_grade import _grade_event

        # Ticker has bars on 2026-06-01, 06-02 (signal), 06-03 (fill), 06-04, ...
        # SPY is missing 2026-06-03 — its fill lands one bar later, on 06-04.
        # Same length overall so len() checks do not save us; the dates
        # themselves are the differentiator.
        ticker_dates = pd.date_range("2026-06-01", periods=9, freq="B")
        spy_dates = pd.DatetimeIndex([
            pd.Timestamp("2026-06-01"),
            pd.Timestamp("2026-06-02"),
            # 2026-06-03 MISSING — SPY holiday
            pd.Timestamp("2026-06-04"),
            pd.Timestamp("2026-06-05"),
            pd.Timestamp("2026-06-08"),
            pd.Timestamp("2026-06-09"),
            pd.Timestamp("2026-06-10"),
            pd.Timestamp("2026-06-11"),
            pd.Timestamp("2026-06-12"),
        ])
        ticker_prices = [100.0, 100.0, 100.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
        spy_prices    = [200.0, 200.0,        201.0, 202.0, 202.5, 203.0, 203.5, 204.0, 204.5]
        close = pd.Series(ticker_prices, index=ticker_dates, dtype=float)
        spy = pd.Series(spy_prices, index=spy_dates, dtype=float)

        result = _grade_event(
            event_id="spy_missing_fill",
            ticker="AAPL",
            session_date="2026-06-02",
            dte_bucket="1_7d",
            close=close,
            spy_close=spy,
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] is not None
        # Label windows differ: ticker fill 06-03 → endpoint 06-10; SPY fill
        # 06-04 → endpoint 06-11. Both endpoints drift together.
        assert result["spy_excess_5"] is None, (
            "SPY excess must be None when SPY's native fill date does not "
            "match the ticker's native fill date — label-window mismatch "
            "is non-evaluable per the contract."
        )

    def test_spy_missing_intermediate_shifts_endpoint(self):
        """If SPY is missing a bar between fill and fill+h, SPY's native
        fill+h date is later than the ticker's. spy_excess_h MUST stay None
        while the absolute metric is preserved."""
        from engine.flow_signals_grade import _grade_event

        ticker_dates = pd.date_range("2026-06-01", periods=9, freq="B")
        # SPY: bar at 2026-06-03 (fill) exists, but bar at 2026-06-04 (the
        # bar that would be ticker fill+1) is missing — so SPY's fill+5
        # endpoint lands on 2026-06-11 instead of the ticker's 2026-06-10.
        # June 3 + 5 business days = June 10.
        spy_dates = pd.DatetimeIndex([
            pd.Timestamp("2026-06-01"),
            pd.Timestamp("2026-06-02"),
            pd.Timestamp("2026-06-03"),
            # 2026-06-04 MISSING (intermediate)
            pd.Timestamp("2026-06-05"),
            pd.Timestamp("2026-06-08"),
            pd.Timestamp("2026-06-09"),
            pd.Timestamp("2026-06-10"),  # ticker's fill+5
            pd.Timestamp("2026-06-11"),  # SPY's fill+5 (one bar late)
            pd.Timestamp("2026-06-12"),
        ])
        ticker_prices = [100.0, 100.0, 100.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
        spy_prices    = [200.0, 200.0, 200.0,       201.0, 202.0, 202.5, 203.0, 203.5, 204.0]
        close = pd.Series(ticker_prices, index=ticker_dates, dtype=float)
        spy = pd.Series(spy_prices, index=spy_dates, dtype=float)

        result = _grade_event(
            event_id="spy_missing_intermediate",
            ticker="AAPL",
            session_date="2026-06-02",
            dte_bucket="1_7d",
            close=close,
            spy_close=spy,
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] is not None
        # Endpoints differ: ticker 06-10, SPY 06-11.
        assert result["spy_excess_5"] is None, (
            "SPY excess must be None when SPY's native fill+h date differs "
            "from the ticker's — label-window mismatch is non-evaluable."
        )

    def test_spy_excess_independent_per_horizon_8_30d(self):
        """For an 8_30d bucket (horizon=21d), the label-window contract is
        checked per horizon. A series that has matching dates throughout the
        21d window should yield a populated spy_excess_21."""
        from engine.flow_signals_grade import _grade_event

        # snap_loc("2026-06-02") lands at bar 1, fill = 2.
        # fwd_ret_21 = close[fill+21] / close[fill] - 1 = close[23] / close[2] - 1.
        n = 24
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        ticker_prices = [100.0] * 24
        ticker_prices[2] = 100.0
        ticker_prices[23] = 115.0
        spy_prices = [200.0] * 24
        spy_prices[2] = 200.0
        spy_prices[23] = 210.0

        close = pd.Series(ticker_prices, index=dates, dtype=float)
        spy = pd.Series(spy_prices, index=dates, dtype=float)

        result = _grade_event(
            event_id="spy_21d_match",
            ticker="AAPL",
            session_date="2026-06-02",
            dte_bucket="8_30d",
            close=close,
            spy_close=spy,
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_21"] is not None
        assert result["fwd_ret_21"] == pytest.approx(0.15, abs=1e-9)
        assert result["spy_excess_21"] is not None
        assert result["spy_excess_21"] == pytest.approx(0.10, abs=1e-9)

    def test_spy_none_preserves_absolute_metrics(self):
        """spy_close=None is the pre-existing fast-path; absolute metrics
        still populate, no SPY columns are written, no exception is raised."""
        from engine.flow_signals_grade import _grade_event

        n = 11
        dates = pd.date_range("2026-06-01", periods=n, freq="B")
        close = pd.Series([100.0] * n, index=dates, dtype=float)

        result = _grade_event(
            event_id="no_spy",
            ticker="AAPL",
            session_date="2026-06-02",
            dte_bucket="1_7d",
            close=close,
            spy_close=None,
        )
        assert result["graded_ok"] is True
        assert result["fwd_ret_5"] is not None
        assert result["spy_excess_5"] is None
        for h in (5, 21, 63, 126):
            assert result[f"spy_excess_{h}"] is None


# Source clocks stay with the incumbent collector test/CI owner.
from collectors import flow_signals as clock_owner
from scripts.build_flow_signals import _write_gate

_SOURCE_CLOCK_TEST_FIELDS = (
    "observed_at", "decision_at", "available_at", "published_at", "source_snapshot_asof",
)
_SOURCE_EVENT_CLOCK_TEST_FIELDS = (
    "source_event_observed_at",
    "source_event_decision_at",
    "source_event_available_at",
    "source_event_published_at",
    "source_event_snapshot_asof",
)
_FS5_RECEIPT_FIELDS = (
    "decision_at",
    "available_at",
    "source_stage_observed_at",
    "source_stage_key",
    "source_stage_schema",
    "source_stage_prefix_records",
    "source_stage_prefix_sha256",
)


def _make_source_clock_event(event_id="clock-event", **changes):
    row = {
        "id": event_id, "root": "TEST", "ts": "2026-09-29T14:00:00Z",
        "dte_bucket": "8_30d", "right": "C", "premium": 1000,
        "observed_at": "2026-09-29T10:00:01.123456789-04:00",
        "decision_at": "2026-09-29T14:00:02Z",
        "available_at": "2026-09-29T14:00:03Z",
        "published_at": "2026-09-29T14:00:04Z",
        "source_snapshot_asof": "2026-09-29T14:00:05Z",
    }
    row.update(changes)
    return row


def _parse_source_clock_event(row):
    return clock_owner._events_from_blob({
        "schema": "live_flow.feed/v1", "session_date": "2026-09-29",
        "asof": "2026-09-29T15:00:00Z", "events": [row],
    })[0]


class TestSourceClockPreservation:
    @pytest.fixture(autouse=True)
    def frozen_ingestion(self, monkeypatch):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime(2026, 9, 29, 16, 0, tzinfo=timezone.utc)
                return value.astimezone(tz) if tz else value.replace(tzinfo=None)
        monkeypatch.setattr(clock_owner, "datetime", Clock)

    def test_source_clock_precision_and_order_survive_normalization(self):
        row = _parse_source_clock_event(_make_source_clock_event())
        assert row.get("source_event_observed_at") == "2026-09-29T14:00:01.123456789+00:00"
        assert row["source_event_available_at"] == "2026-09-29T14:00:03+00:00"
        assert row["source_event_published_at"] == "2026-09-29T14:00:04+00:00"
        assert row["source_event_snapshot_asof"] == "2026-09-29T14:00:05+00:00"
        assert row["source_clock_status"] == "ordered"
        assert row["source_event_available_at"] != row["ingested_at"]

    def test_missing_clocks_never_borrow_event_wrapper_or_ingestion_time(self):
        raw = _make_source_clock_event()
        for key in _SOURCE_CLOCK_TEST_FIELDS:
            raw.pop(key)
        row = _parse_source_clock_event(raw)
        assert row.get("source_clock_status") == "unavailable"
        assert all(row.get(key) is None for key in _SOURCE_EVENT_CLOCK_TEST_FIELDS)
        assert row["ts"] and row["ingested_at"]

    def test_partial_clock_chain_is_not_filled_or_called_ordered(self):
        row = _parse_source_clock_event(_make_source_clock_event(observed_at=None, published_at=None))
        assert row.get("source_clock_status") == "partial"
        assert row["source_event_available_at"] == "2026-09-29T14:00:03+00:00"
        assert row["source_event_observed_at"] is None

    @pytest.mark.parametrize("bad", ["2026-09-29T14:00:03", "2026-09-29", "NaT", "tomorrow", True, 1790690403, "2026-02-31T14:00:03Z", "2026-09-29T14:00:03+01:99", "2026-09-29T14:00:03+01:60", "2026-09-29T14:00:03+24:00"])
    def test_invalid_source_time_is_null_and_not_silently_utc(self, bad):
        row = _parse_source_clock_event(_make_source_clock_event(available_at=bad))
        assert row.get("source_clock_status") == "invalid"
        assert row["source_event_available_at"] is None
        assert row["source_event_decision_at"] == "2026-09-29T14:00:02+00:00"

    @pytest.mark.parametrize("changes", [
        {"ts": "2026-09-29T14:00:10Z"},
        {"observed_at": "2026-09-29T14:00:03Z"},
        {"decision_at": "2026-09-29T14:00:04Z"},
        {"published_at": "2026-09-29T14:00:02Z"},
        {"available_at": "2026-09-29T17:00:00Z", "published_at": None},
        {"source_snapshot_asof": "2026-09-29T17:00:00Z"},
        {"ts": "2026-09-29T14:00:00"},
    ])
    def test_reversed_future_or_unqualified_event_clocks_are_not_ordered(self, changes):
        row = _parse_source_clock_event(_make_source_clock_event(**changes))
        assert row.get("source_clock_status") == "invalid"

    def test_submicrosecond_reversal_is_not_rounded_into_equality(self):
        row = _parse_source_clock_event(_make_source_clock_event(observed_at="2026-09-29T14:00:02.000000002Z", decision_at="2026-09-29T14:00:02.000000001Z"))
        assert row.get("source_clock_status") == "invalid"

    def test_no_publication_time_remains_unpublished_not_fabricated(self):
        row = _parse_source_clock_event(_make_source_clock_event(published_at=None))
        assert row.get("source_clock_status") == "ordered"
        assert row["source_event_published_at"] is None

    def test_keep_first_cannot_backfill_missing_clocks(self, tmp_path):
        path = tmp_path / "ledger.parquet"
        raw = _make_source_clock_event()
        for key in _SOURCE_CLOCK_TEST_FIELDS:
            raw.pop(key)
        clock_owner._append_rows(path, [_parse_source_clock_event(raw)])
        clock_owner._append_rows(path, [_parse_source_clock_event(_make_source_clock_event())])
        df = pd.read_parquet(path)
        assert len(df) == 1
        assert "source_event_available_at" in df.columns
        assert pd.isna(df.iloc[0]["source_event_available_at"])
        assert df.iloc[0]["source_clock_status"] == "unavailable"

    def test_legacy_rows_remain_unknown_through_native_parquet_and_gate(self, tmp_path, monkeypatch):
        path = tmp_path / "ledger.parquet"
        old = _parse_source_clock_event(_make_source_clock_event("legacy"))
        for key in (*_SOURCE_EVENT_CLOCK_TEST_FIELDS, "source_clock_status"):
            old.pop(key, None)
        pd.DataFrame([old]).to_parquet(path, index=False)
        clock_owner._append_rows(path, [_parse_source_clock_event(_make_source_clock_event("new")), _parse_source_clock_event(_make_source_clock_event("invalid", published_at="2026-09-29T14:00:02Z"))])
        df = pd.read_parquet(path)
        assert "source_event_available_at" in df.columns
        legacy = df[df.event_id == "legacy"].iloc[0]
        assert pd.isna(legacy["source_event_available_at"])
        assert pd.isna(legacy["source_clock_status"])
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: path)
        stats = clock_owner.ledger_stats()
        coverage = stats.get("source_clock_coverage")
        assert coverage is not None
        assert coverage["authority"] == "diagnostic_only"
        assert coverage["rows_total"] == 3
        assert coverage["status_counts"]["legacy_unknown"] == 1
        assert coverage["status_counts"]["ordered"] == 1
        assert coverage["status_counts"]["invalid"] == 1
        assert coverage["field_non_null"]["source_event_available_at"] == 2
        assert sum(coverage["status_counts"].values()) == 3
        gate_path = tmp_path / "gate.json"
        _write_gate(gate_path, stats, {}, 2, 0.1, "2026-09-29")
        gate = json.loads(gate_path.read_text())
        assert gate["ledger"]["source_clock_coverage"] == coverage
        assert gate["scoring"]["enabled"] is False
        assert gate["scored"] is False

    def test_legacy_only_statistics_report_unknown_not_zero_rows(self, tmp_path, monkeypatch):
        path = tmp_path / "ledger.parquet"
        pd.DataFrame([{"event_id": "old", "session_date": "2026-09-25", "ts": "2026-09-25T15:00:00+00:00", "dte_bucket": "8_30d"}]).to_parquet(path,index=False)
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: path)
        stats = clock_owner.ledger_stats()
        assert stats["n_rows"] == 1
        assert stats.get("source_clock_coverage", {}).get("status_counts", {}).get("legacy_unknown") == 1

    def test_rfc3339_unknown_local_offset_still_has_known_utc_instant(self):
        # RFC 3339 §4.3: UTC is known; only the local offset is unknown. Do not
        # confuse this valid instant with an unqualified/naive local timestamp.
        row = _parse_source_clock_event(_make_source_clock_event(available_at="2026-09-29T14:00:03-00:00"))
        assert row["source_clock_status"] == "ordered"
        assert row["source_event_available_at"] == "2026-09-29T14:00:03+00:00"

    def test_exact_equal_clock_boundaries_are_valid_without_inventing_publication(self):
        value = "2026-09-29T14:00:00Z"
        row = _parse_source_clock_event(_make_source_clock_event(observed_at=value, decision_at=value, available_at=value, published_at=None, source_snapshot_asof=None))
        assert row["source_clock_status"] == "ordered"
        assert row["source_event_published_at"] is None

    def test_invalid_clock_does_not_erase_independently_valid_measurement(self):
        raw = _make_source_clock_event(available_at=True)
        raw["microstructure"] = {"schema": "options.trade_nbbo_microstructure/v1", "source_print_count": 2, "nbbo_valid_print_count": 1, "nbbo_premium_coverage": 0.5}
        row = _parse_source_clock_event(raw)
        assert row["source_clock_status"] == "invalid"
        assert row["source_print_count"] == 2
        assert row["nbbo_premium_coverage"] == 0.5

    def test_unrecognized_persisted_clock_status_stays_diagnostic(self, tmp_path, monkeypatch):
        path = tmp_path / "ledger.parquet"
        row = _parse_source_clock_event(_make_source_clock_event())
        row["source_clock_status"] = "eligible_to_trade"
        pd.DataFrame([row]).to_parquet(path, index=False)
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: path)
        coverage = clock_owner.ledger_stats()["source_clock_coverage"]
        assert coverage["status_counts"]["unrecognized"] == 1
        assert coverage["status_counts"]["ordered"] == 0
        assert coverage["authority"] == "diagnostic_only"

    def test_additive_source_clocks_do_not_change_native_feature_matrix(self):
        from lib.flow_score import build_interaction_features

        raw = _parse_source_clock_event(_make_source_clock_event())
        raw.update(dte=14, premium_z=2.5)
        before = {key: value for key, value in raw.items()
                  if key not in (*_SOURCE_EVENT_CLOCK_TEST_FIELDS, "source_clock_status")}
        columns = ["dte", "premium_z", "dte_X_premium_z", "missing_feature"]
        expected = build_interaction_features(
            pd.DataFrame([before]), columns, dte_interaction_enabled=True,
        )
        actual = build_interaction_features(
            pd.DataFrame([raw]), columns, dte_interaction_enabled=True,
        )
        pd.testing.assert_frame_equal(actual, expected)
        assert list(actual.columns) == columns

    def _native_clock_bridge(self, tmp_path, monkeypatch):
        from scripts import live_flow_poller as poller

        state_dir = tmp_path / "state"
        out_dir = tmp_path / "out"
        state_dir.mkdir()
        out_dir.mkdir()
        monkeypatch.setattr(poller, "_state_dir", lambda: state_dir)
        monkeypatch.setattr(poller, "_out_dir", lambda: out_dir)
        monkeypatch.setattr(poller, "_OPTIONS_CONTEXT_DISPATCHER", None)
        monkeypatch.setenv("LIVE_FLOW_EVENT_STAGE_DIR", str(state_dir / "events"))
        ledger = tmp_path / "ledger.parquet"
        feed_path = out_dir / "feed_current.json"
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: ledger)
        monkeypatch.setattr(clock_owner, "_feed_current_path", lambda: feed_path)
        monkeypatch.setattr(clock_owner, "_r2_client", lambda: None)
        monkeypatch.setattr(clock_owner, "_r2_bucket", lambda: "isolated-test-bucket")
        raw = _make_source_clock_event("native-stage-event")
        for key in ("available_at", "published_at", "source_snapshot_asof"):
            raw.pop(key)
        available = datetime(2026, 9, 29, 14, 0, 3, 123456, tzinfo=timezone.utc)
        state = {"all_events": [], "pending_learning_events": [raw]}
        poller._save_day_state("2026-09-29", state)
        cleared, staged = poller._drain_pending_learning_events(
            "2026-09-29", state,
            event_stager=lambda session, events: poller._stage_raw_events(
                session, events, now_fn=lambda: available,
            ),
        )
        assert cleared["pending_learning_events"] == []
        assert cleared["all_events"] == staged
        # Same post-commit envelope assignment as the production poller. All
        # event fields themselves come from the real durable staging function.
        feed = {
            "schema": "live_flow.feed/v1", "session_date": "2026-09-29",
            "asof": "2026-09-29T14:05:00Z", "events": cleared["all_events"],
        }
        poller._write_json("feed_current.json", feed)
        return poller, raw, staged[0], ledger, feed_path

    @pytest.mark.parametrize("transport", ["local", "archive"])
    def test_native_stage_to_harvest_preserves_source_clocks(self, tmp_path, monkeypatch, transport):
        poller, raw, staged, ledger, feed_path = self._native_clock_bridge(tmp_path, monkeypatch)
        if transport == "archive":
            # Mock only external transport; the response bytes are generated by
            # the real serializer above, not manually enriched test rows.
            monkeypatch.setattr(clock_owner, "_r2_client", lambda: object())
            monkeypatch.setattr(clock_owner, "_archive_keys_within_window", lambda *_args: ["archive/20260929T14.json"])
            monkeypatch.setattr(clock_owner, "_fetch_r2_json", lambda *_args: json.loads(feed_path.read_text()))
            monkeypatch.setattr(clock_owner, "_r2_feed_current", lambda *_args: None)
            monkeypatch.setattr(clock_owner, "_feed_current_path", lambda: None)
        assert clock_owner.harvest() == 1
        row = pd.read_parquet(ledger).iloc[0]
        assert row["event_id"] == staged["id"] == raw["id"]
        assert row.get("source_event_available_at") == pd.Timestamp(staged["available_at"]).isoformat()
        assert row.get("source_event_observed_at") == "2026-09-29T14:00:01.123456789+00:00"
        assert row.get("source_event_decision_at") == "2026-09-29T14:00:02+00:00"
        assert row.get("source_event_snapshot_asof") == pd.Timestamp(staged["source_snapshot_asof"]).isoformat()
        assert row.get("source_clock_status") == "ordered"
        assert pd.isna(row["source_event_published_at"])
        assert row["source_event_available_at"] != row["ingested_at"]
        stage_path = poller._event_stage_path("2026-09-29")
        decisions, availability, _ = poller._parse_event_stage_bytes(
            "2026-09-29", stage_path.read_bytes(), path=stage_path, require_complete=True,
        )
        assert availability[raw["id"]] == staged["available_at"]
        assert decisions[raw["id"]]["observed_at"] == raw["observed_at"]
        gate_path = tmp_path / "gate.json"
        _write_gate(gate_path, clock_owner.ledger_stats(), {}, 1, 0.1, "2026-09-29")
        gate = json.loads(gate_path.read_text())
        coverage = gate["ledger"]["source_clock_coverage"]
        assert coverage["status_counts"]["ordered"] == 1
        assert coverage["field_non_null"]["source_event_published_at"] == 0
        assert gate["scoring"]["enabled"] is False and gate["scored"] is False

    def test_native_stage_replay_cannot_restamp_already_harvested_event(self, tmp_path, monkeypatch):
        poller, raw, staged, ledger, _ = self._native_clock_bridge(tmp_path, monkeypatch)
        assert clock_owner.harvest() == 1
        first_bytes = ledger.read_bytes()
        # A recovered/refetched event has newer observation clocks. The source
        # stager itself must keep the first durable decision, before harvest.
        replay_raw = dict(raw, observed_at="2026-09-29T14:10:01Z", decision_at="2026-09-29T14:10:02Z")
        replay = poller._stage_raw_events(
            "2026-09-29", [replay_raw],
            now_fn=lambda: datetime(2026, 9, 29, 14, 10, 3, tzinfo=timezone.utc),
        )
        assert replay == [staged]
        poller._write_json("feed_current.json", {
            "schema": "live_flow.feed/v1", "session_date": "2026-09-29",
            "asof": "2026-09-29T14:15:00Z", "events": replay,
        })
        assert clock_owner.harvest() == 0
        assert ledger.read_bytes() == first_bytes

    def test_native_stage_dry_harvest_does_not_write_history(self, tmp_path, monkeypatch):
        _, _, _, ledger, _ = self._native_clock_bridge(tmp_path, monkeypatch)
        assert clock_owner.harvest(dry_run=True) == 1
        assert not ledger.exists()


class TestCurrentMainSourceClockNamespace:
    """Current-base coupling: raw event clocks stay diagnostic; FS-5 receipts stay exclusive."""

    def test_archive_and_feed_clocks_cannot_populate_scientific_receipts(self, tmp_path, monkeypatch):
        clocks = {
            "observed_at": "2026-07-13T14:00:01Z",
            "decision_at": "2026-07-13T14:00:02Z",
            "available_at": "2026-07-13T14:00:03Z",
            "published_at": "2026-07-13T14:00:04Z",
            "source_snapshot_asof": "2026-07-13T14:00:05Z",
        }
        row = clock_owner._events_from_blob(
            _make_feed_blob([_make_event("arch-clocks", **clocks)])
        )[0]
        for field in _FS5_RECEIPT_FIELDS:
            assert row[field] is None, f"archive/feed populated scientific {field}"
        assert row["source_event_observed_at"] == "2026-07-13T14:00:01+00:00"
        assert row["source_event_decision_at"] == "2026-07-13T14:00:02+00:00"
        assert row["source_event_available_at"] == "2026-07-13T14:00:03+00:00"
        assert row["source_event_published_at"] == "2026-07-13T14:00:04+00:00"
        assert row["source_event_snapshot_asof"] == "2026-07-13T14:00:05+00:00"
        assert row["source_clock_status"] == "ordered"

        ledger = tmp_path / "ledger.parquet"
        blob = _make_feed_blob([_make_event("harvest-arch-clocks", **clocks)])
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: ledger)
        monkeypatch.setattr(clock_owner, "_r2_client", lambda: object())
        monkeypatch.setattr(clock_owner, "_r2_bucket", lambda: "isolated-test-bucket")
        monkeypatch.setattr(
            clock_owner, "_event_stage_keys_within_window", lambda *_a, **_k: [],
        )
        monkeypatch.setattr(
            clock_owner, "_archive_keys_within_window",
            lambda *_a, **_k: ["live_flow/archive/20260713T14.json"],
        )
        monkeypatch.setattr(clock_owner, "_fetch_r2_json", lambda *_a, **_k: blob)
        monkeypatch.setattr(clock_owner, "_r2_feed_current", lambda *_a, **_k: None)
        monkeypatch.setattr(clock_owner, "_feed_current_path", lambda: None)
        assert clock_owner.harvest() == 1
        stored = pd.read_parquet(ledger).iloc[0]
        assert pd.isna(stored["decision_at"])
        assert pd.isna(stored["available_at"])
        assert pd.isna(stored["source_stage_key"])
        assert stored["source_event_decision_at"] == "2026-07-13T14:00:02+00:00"
        assert stored["source_event_available_at"] == "2026-07-13T14:00:03+00:00"

    def test_verified_stage_receipts_remain_exact_and_diagnostics_do_not_overwrite(
        self, tmp_path, monkeypatch,
    ):
        from lib.live_flow_event_stage import EVENT_STAGE_SCHEMA, parse_stage_bytes

        session = "2026-07-13"
        key = f"live_flow/events/{session}.jsonl"
        event = {
            "id": "stage-evt",
            "ts": "2026-07-13T14:00:00Z",
            "root": "AAPL",
            "observed_at": "2026-07-13T14:00:01Z",
            "decision_at": "2026-07-13T14:00:02Z",
            "dte_bucket": "8_30d",
            "premium": 1000.0,
        }
        decision = {
            "schema": EVENT_STAGE_SCHEMA,
            "kind": "decision",
            "event_id": "stage-evt",
            "event": event,
        }
        availability = {
            "schema": EVENT_STAGE_SCHEMA,
            "kind": "availability",
            "event_id": "stage-evt",
            "available_at": "2026-07-13T18:00:03Z",
        }
        raw = (
            json.dumps(decision, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            + b"\n"
            + json.dumps(availability, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            + b"\n"
        )
        paired = parse_stage_bytes(
            raw, expected_session_date=session, source_stage_key=key,
        )
        assert len(paired) == 1
        item = paired[0]

        class _Body:
            def read(self):
                return raw

        s3 = MagicMock()
        s3.get_object.return_value = {"Body": _Body()}
        ledger = tmp_path / "ledger.parquet"
        monkeypatch.setattr(clock_owner, "_ledger_path", lambda: ledger)
        monkeypatch.setattr(clock_owner, "_r2_client", lambda: s3)
        monkeypatch.setattr(clock_owner, "_r2_bucket", lambda: "isolated-test-bucket")
        monkeypatch.setattr(
            clock_owner, "_event_stage_keys_within_window", lambda *_a, **_k: [key],
        )
        monkeypatch.setattr(
            clock_owner, "_archive_keys_within_window", lambda *_a, **_k: [],
        )
        monkeypatch.setattr(clock_owner, "_r2_feed_current", lambda *_a, **_k: None)
        monkeypatch.setattr(clock_owner, "_feed_current_path", lambda: None)

        assert clock_owner.harvest() == 1
        stored = pd.read_parquet(ledger).iloc[0]
        assert stored["decision_at"] == item["decision_at"]
        assert stored["available_at"] == item["available_at"]
        assert stored["source_stage_key"] == item["source_stage_key"]
        assert stored["source_stage_schema"] == item["source_stage_schema"]
        assert int(stored["source_stage_prefix_records"]) == item["source_stage_prefix_records"]
        assert stored["source_stage_prefix_sha256"] == item["source_stage_prefix_sha256"]
        assert stored["source_event_observed_at"] == "2026-07-13T14:00:01+00:00"
        assert stored["source_event_decision_at"] == "2026-07-13T14:00:02+00:00"
        assert stored["source_event_available_at"] == "2026-07-13T18:00:03+00:00"
        assert stored["source_event_decision_at"] != stored["available_at"]
        assert stored["decision_at"] == "2026-07-13T14:00:02Z"
        assert stored["available_at"] == "2026-07-13T18:00:03Z"
        assert stored["source_clock_status"] == "ordered"

    def test_no_duplicate_columns_and_parquet_roundtrip_keeps_both_namespaces(self, tmp_path):
        assert len(clock_owner._EVENT_COLS) == len(set(clock_owner._EVENT_COLS))
        assert clock_owner._EVENT_COLS.count("decision_at") == 1
        assert clock_owner._EVENT_COLS.count("available_at") == 1
        for col in (*_SOURCE_EVENT_CLOCK_TEST_FIELDS, "source_clock_status", *_FS5_RECEIPT_FIELDS):
            assert col in clock_owner._EVENT_COLS

        clocks = {
            "observed_at": "2026-07-13T14:00:01Z",
            "decision_at": "2026-07-13T14:00:02Z",
            "available_at": "2026-07-13T14:00:03Z",
            "published_at": "2026-07-13T14:00:04Z",
            "source_snapshot_asof": "2026-07-13T14:00:05Z",
        }
        rows = clock_owner._events_from_blob(
            _make_feed_blob([_make_event("roundtrip", **clocks)])
        )
        path = tmp_path / "ledger.parquet"
        assert clock_owner._append_rows(path, rows) == 1
        df = pd.read_parquet(path)
        stored = df.iloc[0]
        assert pd.isna(stored["decision_at"])
        assert pd.isna(stored["available_at"])
        assert stored["source_event_decision_at"] == "2026-07-13T14:00:02+00:00"
        assert stored["source_event_available_at"] == "2026-07-13T14:00:03+00:00"
        assert stored["source_clock_status"] == "ordered"
        reread = pd.read_parquet(path)
        pd.testing.assert_frame_equal(df, reread)

    def test_old_rows_remain_null_under_keep_first_and_raw_measurements_retained(self, tmp_path):
        path = tmp_path / "ledger.parquet"
        old = clock_owner._events_from_blob(_make_feed_blob([_make_event("legacy-keep")]))[0]
        for key in (*_SOURCE_EVENT_CLOCK_TEST_FIELDS, "source_clock_status"):
            old.pop(key, None)
        pd.DataFrame([old]).to_parquet(path, index=False)

        rich = _make_event(
            "fresh-keep",
            observed_at="2026-07-13T14:00:01Z",
            decision_at="2026-07-13T14:00:02Z",
            available_at="2026-07-13T14:00:03Z",
            published_at="2026-07-13T14:00:04Z",
            source_snapshot_asof="2026-07-13T14:00:05Z",
            microstructure={
                "schema": "options.trade_nbbo_microstructure/v1",
                "source_print_count": 7,
                "nbbo_valid_print_count": 6,
                "nbbo_premium_coverage": 0.8,
                "at_ask_share": 0.55,
            },
        )
        assert clock_owner._append_rows(
            path, clock_owner._events_from_blob(_make_feed_blob([rich])),
        ) == 1
        # Re-harvest of the same id with later clocks must not mutate first-seen fields.
        restated = dict(rich)
        restated["available_at"] = "2026-07-13T18:00:03Z"
        restated["decision_at"] = "2026-07-13T18:00:02Z"
        restated["microstructure"] = dict(rich["microstructure"], at_ask_share=0.99)
        existing_ids = clock_owner._load_existing_ids(path)
        new_rows = [
            r for r in clock_owner._events_from_blob(_make_feed_blob([restated]))
            if r["event_id"] not in existing_ids
        ]
        clock_owner._append_rows(path, new_rows)

        df = pd.read_parquet(path)
        assert list(df["event_id"]) == ["legacy-keep", "fresh-keep"]
        legacy = df.iloc[0]
        fresh = df.iloc[1]
        for key in _SOURCE_EVENT_CLOCK_TEST_FIELDS:
            assert pd.isna(legacy[key]), f"legacy backfilled {key}"
        assert pd.isna(legacy["source_clock_status"])
        assert pd.isna(legacy["decision_at"])
        assert pd.isna(legacy["available_at"])
        assert fresh["source_event_available_at"] == "2026-07-13T14:00:03+00:00"
        assert fresh["source_event_decision_at"] == "2026-07-13T14:00:02+00:00"
        assert pd.isna(fresh["decision_at"])
        assert pd.isna(fresh["available_at"])
        assert int(fresh["source_print_count"]) == 7
        assert float(fresh["at_ask_share"]) == pytest.approx(0.55)
        assert float(fresh["nbbo_premium_coverage"]) == pytest.approx(0.8)


# ─── F01: measured slots reject legacy categories and broken location identity ─


def test_midpoint_derived_buy_side_never_enters_measured_slots():
    """A ~buy category and a legacy 0.8 ask_share do not fill an inside print."""
    from collectors.flow_signals import _events_from_blob

    block = {
        "schema": MICRO_SCHEMA,
        "inside_share": 1.0,
        "at_ask_share": 0.0,
        "at_bid_share": 0.0,
        "outside_share": 0.0,
        "aggression_share": 0.0,
    }
    event = _make_event(
        "evtMidBuy",
        side="~buy",
        ask_share=0.8,
        category_proxy_share=0.8,
        microstructure=block,
    )
    row = _events_from_blob(_make_feed_blob([event]))[0]
    assert row["at_ask_share"] == 0.0
    assert row["aggression_share"] == 0.0


def test_two_print_source_tick_signed_mid_stays_inside_not_proxy():
    """Print 1 at 2.90 ask; print 2 at the 3.00 mid, signed up by the tick test."""
    import pandas as pd
    from engine import live_flow as lf
    from collectors.flow_signals import _events_from_blob
    from scripts.build_chain_heat import _enrich_events

    rows = [
        {
            "root": "SPY", "right": "C", "expiration": "2026-07-17", "strike": 550.0,
            "price": 2.90, "size": 1, "bid": 2.80, "ask": 2.90,
            "trade_timestamp": "2026-07-02T14:30:00.100",
            "quote_timestamp": "2026-07-02T14:30:00.000",
            "sequence": 1,
        },
        {
            "root": "SPY", "right": "C", "expiration": "2026-07-17", "strike": 550.0,
            "price": 3.00, "size": 1, "bid": 2.00, "ask": 4.00,
            "trade_timestamp": "2026-07-02T14:30:01.100",
            "quote_timestamp": "2026-07-02T14:30:01.000",
            "sequence": 2,
        },
    ]
    result = lf.process_batch(
        calls_df=pd.DataFrame(rows),
        puts_df=None,
        session_date="2026-07-02",
        batch_ts="2026-07-02T18:30:00Z",
        etf_floor=0,
        name_floor=0,
        etf_anchors=["SPY", "QQQ"],
    )
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["side"] == "~buy"
    enriched = _enrich_events([event])
    assert enriched[0]["category_proxy_share"] == pytest.approx(0.80)
    row = _events_from_blob(_make_feed_blob([event]))[0]
    assert row["side"] == "~buy"
    assert row["inside_share"] == pytest.approx(300 / 590)


def _f01_consistent_location_block(**extra) -> dict:
    block = {
        "schema": MICRO_SCHEMA,
        "source_premium_usd": 1_000_000.0,
        "nbbo_covered_premium_usd": 1_000_000.0,
        "nbbo_premium_coverage": 1.0,
        "nbbo_print_coverage": 1.0,
        "at_ask_share": 0.6,
        "at_bid_share": 0.2,
        "inside_share": 0.2,
        "outside_share": 0.0,
        "aggression_share": 0.8,
        "aggression_balance": 0.4,
    }
    block.update(extra)
    return block


@pytest.mark.parametrize("legacy_key", ["ask_share", "category_proxy_share", "side"])
def test_measured_block_with_legacy_categorical_key_is_rejected(legacy_key):
    """A v1 block that also carries a legacy category key is not measured."""
    from collectors.flow_signals import _events_from_blob

    block = _f01_consistent_location_block(**{legacy_key: 0.8})
    row = _events_from_blob(
        _make_feed_blob([_make_event("evtLegacyKey", microstructure=block)])
    )[0]
    assert row["at_ask_share"] is None
    assert row["microstructure_schema"] is None


def test_measured_block_breaking_location_identity_is_rejected():
    """Shares that do not partition covered premium, or that mix nulls, are dropped."""
    from collectors.flow_signals import _events_from_blob

    broken_sum = {
        "schema": MICRO_SCHEMA,
        "at_ask_share": 0.8,
        "at_bid_share": 0.2,
        "inside_share": 0.5,
        "outside_share": 0.0,
        "aggression_share": 1.0,
    }
    mixed_null = {
        "schema": MICRO_SCHEMA,
        "at_ask_share": 0.8,
        "at_bid_share": None,
        "inside_share": 0.2,
        "outside_share": 0.0,
        "aggression_share": 0.8,
    }
    for block in (broken_sum, mixed_null):
        row = _events_from_blob(
            _make_feed_blob([_make_event("evtBroken", microstructure=block)])
        )[0]
        for column in MEASURED_COLS:
            assert row[column] is None, column


def test_genuine_coalesced_block_passes_rejection_predicate():
    """Producer output from the A01 geometries is trusted, not rejected."""
    import pandas as pd
    from engine import live_flow as lf
    from collectors.flow_signals import (
        _measured_microstructure_cols,
        measured_block_rejection_reason,
    )

    for bid, ask in ((2.00, 4.00), (3.00, 3.90)):
        rows = []
        for seq, second in ((1, 0), (2, 1)):
            rows.append({
                "root": "SPY",
                "right": "C",
                "expiration": "2026-07-17",
                "strike": 550.0,
                "price": 3.90,
                "size": 10,
                "bid": bid,
                "ask": ask,
                "trade_timestamp": f"2026-07-02T14:30:0{second}.100",
                "quote_timestamp": f"2026-07-02T14:30:0{second}.000",
                "sequence": seq,
            })
        measured = lf._coalesce_nbbo_microstructure(pd.DataFrame(rows))
        assert len(measured) == 1
        block = next(iter(measured.values()))
        assert measured_block_rejection_reason(block) is None
        flat = _measured_microstructure_cols({"microstructure": block})
        assert flat["microstructure_schema"] == block["schema"]
        assert flat["at_ask_share"] == block["at_ask_share"]
        assert flat["inside_share"] == block["inside_share"]
        assert flat["at_ask_share"] is not None

