"""tests/test_prophet_plan_clock.py — the Prophet US plan pipeline's clock, trigger,
price reach, lossless intake, closed-state copy and shipped order (P1-P6, 2026-08-06).

WHY THIS FILE EXISTS
--------------------
The pre-existing prophet fixtures are DEGENERATE for every defect below: they set
``asof == signal_date`` and carry no ``trigger``, so the two worst defects in the
pipeline were invisible to a green suite.

  * ``signal_date`` is the base-FORMATION anchor (``hold.anchor``) and preceded
    origination by up to 152 days on the shipped book (94 of 103 plans had a gap).
    ``entry`` is the ORIGINATION-day close.  Anchoring the horizon clock and the
    outcome scan to ``signal_date`` graded plans on bars that predated them: all 9
    EXPIRED ledger rows and both winners closed before their own plan existed, and
    14 plans were born already past horizon.
  * The plan's own copy says "No position until trigger is confirmed" while
    ``_determine_outcome`` never read ``plan["trigger"]`` — 5 of 16 shipped rows
    booked full P&L on positions the plan told the reader not to take.

Every fixture here therefore has ``asof`` MONTHS after ``signal_date`` and a trigger
above the graded window.  A fixture that cannot express the defect cannot pin its fix.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import scripts.build_prophet as bp  # noqa: E402
from engine.prophet_bridge import (  # noqa: E402
    N_CANDIDATES,
    load_quarantined_ids,
    originate_plans,
    plan_clock_date,
    select_candidates,
)
from engine.prophet_management import compute_management_state  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures — the SHIPPED shape, not the degenerate one
# ---------------------------------------------------------------------------

FORMATION = "2026-03-01"   # hold.anchor — the base formed here
ORIGINATION = "2026-07-01"  # the night the plan was written; entry IS this close
# 122 calendar days apart. A 45-day horizon read off FORMATION is already 77 days
# past expiry on the plan's own birthday.


def _plan(
    *,
    plan_id: str = "AAA-BULL-20260301",
    ticker: str = "AAA",
    entry: float = 100.0,
    trigger: float | None = 105.0,
    invalidation: float = 90.0,
    targets: tuple[float, ...] = (115.0, 130.0),
    signal_date: str = FORMATION,
    entry_date: str | None = ORIGINATION,
    asof: str | None = ORIGINATION,
    horizon_days: int = 45,
    direction: str = "BULL",
) -> dict:
    """A plan in the shape the shipped book actually holds: an OLD formation anchor,
    a RECENT origination, and a trigger the plan says must confirm first."""
    plan: dict = {
        "schema": "prophet.trade_plan/v1",
        "id": plan_id,
        "asset": ticker,
        "direction": direction,
        "signal_date": signal_date,
        "_signal_date": signal_date,
        "entry": entry,
        "trigger": trigger,
        "invalidation": invalidation,
        "targets": list(targets),
        "horizon_days": horizon_days,
        "min_hold_days": 10,
        "tranche": 1,
        "option_contract": None,
        "authority_tier": "display",
        "source_engines": ["us_standouts_buy_lane"],
    }
    if asof is not None:
        plan["asof"] = asof
    if entry_date is not None:
        plan["entry_date"] = entry_date
    return plan


def _closes(values: list[float], start: str) -> pd.DataFrame:
    """Daily closes on business days from `start` (inclusive)."""
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.DataFrame({"close": values}, index=idx)


def _advance(tmp_path, plans: dict, ph_map: dict, asof: str) -> list:
    """advance_ledger against a tmp ledger with a stubbed price loader."""
    orig_path, orig_dir = bp.LEDGER_PATH, bp.LEDGER_DIR
    try:
        bp.LEDGER_PATH = tmp_path / "ledger.jsonl"
        bp.LEDGER_DIR = tmp_path
        bp._initialize_ledger()
        with patch("scripts.build_prophet._load_price_history_for_management",
                   side_effect=lambda t: ph_map.get(t)):
            return bp.advance_ledger(plans, asof)
    finally:
        bp.LEDGER_PATH, bp.LEDGER_DIR = orig_path, orig_dir


# ===========================================================================
# P1 — the grading clock
# ===========================================================================

class TestTheClockIsTheEntryDate:

    def test_a_plan_with_a_100_day_old_anchor_is_not_expired_at_birth(self, tmp_path):
        """THE defect, stated as a test.

        Formation 2026-03-01, origination 2026-07-01, horizon 45 days.  Under the old
        clock the very first bar after formation is already day 1 of 45 and the plan
        EXPIRES months before it was written.  Under the entry-date clock it is simply
        open: five bars have printed since entry.
        """
        plan = _plan(trigger=None)   # trigger isolated in its own section below
        # Bars run from FORMATION so the frame contains the whole poisoned window.
        ph = _closes([100.0] * 120, start=FORMATION)
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2026-07-08")
        assert rows == [], (
            "a plan originated on 2026-07-01 cannot have expired: the old clock read "
            "its 2026-03-01 formation anchor and closed it as EXPIRED on bars that "
            "predated the plan"
        )

    def test_the_same_plan_on_the_old_clock_would_have_expired(self, tmp_path):
        """Mutation direction: strip entry_date AND asof, and the old behaviour returns.

        This is the test's own falsifier — without it, the assertion above would pass
        just as well against a function that never closes anything.
        """
        plan = _plan(trigger=None, entry_date=None, asof=None)
        ph = _closes([100.0] * 120, start=FORMATION)
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2026-07-08")
        assert len(rows) == 1 and rows[0]["outcome"] == "EXPIRED", (
            "with nothing but signal_date to read, the scan MUST fall back to it — "
            "this is the shape the fix is measured against"
        )

    def test_the_scan_starts_after_the_entry_bar_not_after_formation(self, tmp_path):
        """A dip below invalidation BEFORE origination must not close the plan.

        The name traded at 80 in April — 10 points through the plan's stop — but the
        plan did not exist then and its entry was taken in July.  The old scan saw
        that April bar and booked INVALIDATED with a −20% result.
        """
        closes = [100.0] * 30 + [80.0] + [100.0] * 120   # the April hole
        ph = _closes(closes, start=FORMATION)
        plan = _plan(trigger=None)
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2026-07-08")
        assert rows == [], "a pre-origination stop-out is not this plan's outcome"

    def test_horizon_expiry_counts_from_entry_date(self, tmp_path):
        """The clock must not merely be un-stuck — it must actually run."""
        plan = _plan(trigger=None, horizon_days=10)
        # Flat from formation; the asof is 20 calendar days past origination.
        ph = _closes([100.0] * 200, start=FORMATION)
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2026-07-25")
        assert len(rows) == 1
        assert rows[0]["outcome"] == "EXPIRED"
        assert rows[0]["days_held"] >= 10
        # close_date is entry_date + days_held, never formation + days_held.
        assert rows[0]["close_date"] > ORIGINATION, (
            f"close_date {rows[0]['close_date']} predates origination {ORIGINATION} — "
            "the ledger row was written from the formation anchor again"
        )
        assert rows[0]["entry_date"] == ORIGINATION

    def test_management_tau_reads_the_entry_date(self):
        """The third call site: elapsed/τ inside compute_management_state."""
        plan = _plan(trigger=None, horizon_days=45)
        ph = _closes([100.0] * 200, start=FORMATION)
        ph = ph[ph.index <= pd.Timestamp(ORIGINATION)]
        state = compute_management_state(plan=plan, price_history=ph,
                                         asof=ORIGINATION)
        assert state["days_elapsed"] == 0, (
            "on origination night the plan has spent none of its horizon; reading "
            "signal_date gave 122 days of a 45-day horizon and forced overtime"
        )
        assert state["phase"] != "overtime"

    def test_close_date_never_precedes_the_plans_own_origination(self, tmp_path):
        """The exact invariant the quarantine rule tests for, enforced going forward."""
        closes = [100.0] * 30 + [130.0] + [100.0] * 130   # a pre-origination T2 spike
        ph = _closes(closes, start=FORMATION)
        plan = _plan(trigger=None)
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2026-09-01")
        for row in rows:
            assert row["close_date"] >= ORIGINATION, row


# ===========================================================================
# P2 — the trigger is read
# ===========================================================================

class TestTriggerConfirmation:

    def test_an_unconfirmed_trigger_closes_no_entry_with_a_null_result(self, tmp_path):
        """Price never reaches 105. The plan said "no position until confirmed", so
        the −8% drift below it is not a loss this plan took."""
        plan = _plan(trigger=105.0, invalidation=None, horizon_days=10)
        closes = [100.0] * 40 + [99.0, 98.0, 97.0, 96.0, 95.0,
                                 94.0, 93.0, 92.0, 92.0, 92.0, 92.0, 92.0]
        ph = _closes(closes, start=FORMATION)
        # Re-index so the post-origination bars are the tail of the frame.
        ph.index = pd.date_range(FORMATION, periods=len(closes), freq="B")
        plan["entry_date"] = str(ph.index[39].date())
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2027-01-01")
        assert len(rows) == 1
        assert rows[0]["outcome"] == "NO_ENTRY"
        assert rows[0]["stock_result_pct"] is None, (
            "a trade that never opened has no P&L; booking one is the defect"
        )

    def test_no_entry_is_in_neither_side_of_the_rate(self):
        """The exclusion is the point — a NO_ENTRY in the denominator would report a
        losing trade the plan explicitly told the reader not to take."""
        ledger = [
            {"id": "W", "outcome": "T1_HIT", "stock_result_pct": 12.0},
            {"id": "L", "outcome": "INVALIDATED", "stock_result_pct": -8.0},
            {"id": "N", "outcome": "NO_ENTRY", "stock_result_pct": None},
        ]
        summary = bp.record_summary(ledger, set())
        assert summary["n_scored"] == 2
        assert summary["n_no_entry"] == 1
        assert summary["win_rate"] == 0.5, (
            "3 rows, 1 win — but the NO_ENTRY is not a loss, so the rate is 1/2"
        )

    def test_the_scan_starts_at_confirmation_not_at_the_clock(self, tmp_path):
        """A stop-level print BEFORE the trigger confirms is not an exit.

        Entry 100, trigger 105, stop 90.  The tape goes 88 (no position — the plan is
        still waiting), then 106 (confirmed), then 120 (T1).  Scanning from the clock
        books INVALIDATED at 88 on a position that did not exist.
        """
        closes = [100.0] * 40 + [88.0, 106.0, 120.0, 120.0]
        ph = _closes(closes, start=FORMATION)
        plan = _plan(trigger=105.0, invalidation=90.0, horizon_days=45)
        plan["entry_date"] = str(ph.index[39].date())
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2027-01-01")
        assert len(rows) == 1
        assert rows[0]["outcome"] == "T1_HIT", (
            f"got {rows[0]['outcome']} — the pre-confirmation 88 print was read as an "
            "exit from a position the plan had not entered"
        )

    def test_confirmation_is_inclusive_of_the_published_level(self, tmp_path):
        """The plan publishes "above 105" as the level to act on; trading AT it acts
        on the plan. Pinned in both directions so a refactor cannot quietly flip it."""
        plan = _plan(trigger=105.0, invalidation=None, horizon_days=3)
        exact = _closes([100.0] * 40 + [105.0, 105.0, 105.0, 105.0], start=FORMATION)
        plan["entry_date"] = str(exact.index[39].date())
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": exact}, "2027-01-01")
        assert rows[0]["outcome"] == "EXPIRED", "105.0 confirms the 105.0 trigger"

        plan2 = _plan(plan_id="BBB-BULL-1", ticker="BBB", trigger=105.0,
                      invalidation=None, horizon_days=3)
        under = _closes([100.0] * 40 + [104.99] * 4, start=FORMATION)
        plan2["entry_date"] = str(under.index[39].date())
        rows2 = _advance(tmp_path, {plan2["id"]: plan2}, {"BBB": under}, "2027-01-01")
        assert rows2[0]["outcome"] == "NO_ENTRY", "104.99 does not confirm 105.0"

    def test_a_null_trigger_is_treated_as_confirmed(self, tmp_path):
        """Legacy plans and fixtures predate the field; they must grade as before."""
        plan = _plan(trigger=None, horizon_days=5)
        ph = _closes([100.0] * 40 + [100.0] * 10, start=FORMATION)
        plan["entry_date"] = str(ph.index[39].date())
        rows = _advance(tmp_path, {plan["id"]: plan}, {"AAA": ph}, "2027-01-01")
        assert rows[0]["outcome"] == "EXPIRED"

    def test_bear_confirmation_is_mirrored(self, tmp_path):
        plan = _plan(plan_id="CCC-BEAR-1", ticker="CCC", direction="BEAR",
                     entry=100.0, trigger=95.0, invalidation=None,
                     targets=(85.0, 70.0), horizon_days=45)
        ph = _closes([100.0] * 40 + [97.0, 94.0, 84.0, 84.0], start=FORMATION)
        plan["entry_date"] = str(ph.index[39].date())
        rows = _advance(tmp_path, {plan["id"]: plan}, {"CCC": ph}, "2027-01-01")
        assert rows[0]["outcome"] == "T1_HIT"


# ===========================================================================
# Quarantine — derived, excluded, disclosed, and the jsonl untouched
# ===========================================================================

class TestLedgerQuarantine:

    @staticmethod
    def _fixture():
        plans = {
            "OLD-BULL-1": {"id": "OLD-BULL-1", "asof": "2026-07-14"},
            "OK-BULL-1": {"id": "OK-BULL-1", "asof": "2026-07-01"},
            "EDGE-BULL-1": {"id": "EDGE-BULL-1", "asof": "2026-07-10"},
        }
        ledger = [
            # closed 2026-05-04, plan written 2026-07-14 → graded before it existed
            {"id": "OLD-BULL-1", "close_date": "2026-05-04", "outcome": "EXPIRED",
             "stock_result_pct": 6.4},
            {"id": "OK-BULL-1", "close_date": "2026-07-20", "outcome": "INVALIDATED",
             "stock_result_pct": -9.8},
            # same day = NOT poisoned; the rule is STRICTLY predates
            {"id": "EDGE-BULL-1", "close_date": "2026-07-10", "outcome": "T1_HIT",
             "stock_result_pct": 15.9},
        ]
        return ledger, plans

    def test_the_list_is_derived_from_the_arithmetic_not_enumerated(self):
        ledger, plans = self._fixture()
        rows = bp.derive_quarantine(ledger, plans)
        assert [r["id"] for r in rows] == ["OLD-BULL-1"]
        assert rows[0]["reason"] == "graded_on_pre_origination_clock"
        assert rows[0]["quarantined"] == "2026-08-06"

    def test_moving_a_plans_origination_moves_the_list(self):
        """Mutation check: nothing here may be hardcoded. Re-date the OK plan's
        origination past its own close and it becomes poisoned too."""
        ledger, plans = self._fixture()
        plans["OK-BULL-1"]["asof"] = "2026-08-01"
        assert {r["id"] for r in bp.derive_quarantine(ledger, plans)} == {
            "OLD-BULL-1", "OK-BULL-1"}

    def test_a_row_with_no_locatable_plan_is_not_quarantined(self):
        """Silence is not evidence of poison."""
        ledger, plans = self._fixture()
        ledger.append({"id": "GHOST-BULL-1", "close_date": "2020-01-01",
                       "outcome": "EXPIRED", "stock_result_pct": 1.0})
        assert "GHOST-BULL-1" not in {r["id"] for r in bp.derive_quarantine(ledger, plans)}

    def test_the_file_round_trips_through_the_shared_reader(self, tmp_path):
        ledger, plans = self._fixture()
        orig_dir = bp.LEDGER_DIR
        try:
            bp.LEDGER_DIR = tmp_path
            payload = bp.write_quarantine(ledger, plans)
        finally:
            bp.LEDGER_DIR = orig_dir
        path = tmp_path / "ledger_quarantine.json"
        assert path.exists()
        assert payload["count"] == 1
        assert load_quarantined_ids(path) == {"OLD-BULL-1"}

    def test_an_absent_file_is_an_empty_quarantine_not_a_crash(self, tmp_path):
        assert load_quarantined_ids(tmp_path / "nope.json") == set()

    def test_summaries_exclude_the_quarantined_rows(self):
        ledger, plans = self._fixture()
        ids = {r["id"] for r in bp.derive_quarantine(ledger, plans)}
        summary = bp.record_summary(ledger, ids)
        assert summary["n_rows_total"] == 3
        assert summary["n_quarantined"] == 1
        assert summary["n_scored"] == 2
        # The poisoned row is the +6.4% "winner". Dropping it halves the win rate.
        assert summary["win_rate"] == 0.5
        assert bp.record_summary(ledger, set())["n_scored"] == 3

    def test_the_disclosure_line_is_plain_words_and_bilingual(self, tmp_path):
        ledger, plans = self._fixture()
        orig_dir = bp.LEDGER_DIR
        try:
            bp.LEDGER_DIR = tmp_path
            payload = bp.write_quarantine(ledger, plans)
        finally:
            bp.LEDGER_DIR = orig_dir
        assert payload["note"] == (
            "1 early rows quarantined 2026-08-06 — graded on a clock that predated "
            "the plan")
        assert payload["note_zh"], "an EN-only disclosure desyncs the bilingual pair"
        # No raw enum slugs or internal study names in the reader-facing line.
        for banned in ("EXPIRED", "T1_HIT", "_determine_outcome", "signal_date"):
            assert banned not in payload["note"]

    def test_the_ledger_file_itself_is_never_rewritten(self, tmp_path):
        """Append-only means append-only: quarantine SUBTRACTS from summaries, it does
        not edit the record."""
        ledger, plans = self._fixture()
        path = tmp_path / "ledger.jsonl"
        body = "# header\n" + "\n".join(json.dumps(r) for r in ledger) + "\n"
        path.write_text(body, encoding="utf-8")
        before = path.read_bytes()
        orig_path, orig_dir = bp.LEDGER_PATH, bp.LEDGER_DIR
        try:
            bp.LEDGER_PATH, bp.LEDGER_DIR = path, tmp_path
            bp.write_quarantine(bp._load_ledger_rows(), plans)
        finally:
            bp.LEDGER_PATH, bp.LEDGER_DIR = orig_path, orig_dir
        assert path.read_bytes() == before

    def test_the_committed_ledger_derives_exactly_the_reported_set(self):
        """Against the REAL artifacts: the count is an observation of the rule, and
        this test states it so a later change to either side is visible."""
        ledger_path = _REPO / "data" / "prophet" / "ledger.jsonl"
        plans_dir = _REPO / "site" / "prophet" / "plans"
        if not (ledger_path.exists() and plans_dir.exists()):
            pytest.skip("committed prophet artifacts absent")
        plans = {}
        for p in plans_dir.glob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            plans[d["id"]] = d
        rows = [json.loads(ln) for ln in ledger_path.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")]
        derived = {r["id"] for r in bp.derive_quarantine(rows, plans)}
        # Every derived row must actually satisfy the stated rule — the property, not
        # the count, is what must hold on any future artifact.
        for plan_id in derived:
            row = next(r for r in rows if r["id"] == plan_id)
            assert row["close_date"] < plans[plan_id]["asof"]
        assert derived, "the shipped ledger is the reason this rule exists"


# ===========================================================================
# P3 — the plan lane can price its own plans
# ===========================================================================

class TestPlanLanePriceReach:

    def test_the_panel_rung_prices_a_name_no_per_ticker_parquet_covers(self):
        """PINS has no ohlcv and no stocks parquet — 27 of 103 plans were like it, and
        an unpriceable plan can never be managed, never closed, and blocks its slot
        forever."""
        for sub in ("data/baskets/ohlcv", "data/stocks"):
            assert not (_REPO / sub / "PINS.parquet").exists(), (
                "fixture assumption broken: PINS now has a per-ticker parquet")
        df = bp._load_price_history_for_management("PINS")
        if df is None:
            pytest.skip("breadth close panels absent in this checkout")
        assert "close" in df.columns and not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_origination_and_management_resolve_to_the_same_series(self):
        """A plan priced at birth but not a night later is worse than one never born."""
        from engine.prophet_bridge import _load_price_history  # noqa: PLC0415
        a = _load_price_history("PINS")
        b = bp._load_price_history_for_management("PINS")
        if a is None or b is None:
            pytest.skip("breadth close panels absent in this checkout")
        assert list(a.index) == list(b.index)
        assert a["close"].tolist() == b["close"].tolist()

    def test_a_per_ticker_parquet_still_wins(self):
        """Priority order is the reason the panels can never disagree with the
        per-ticker store on a shipped plan."""
        from engine.prophet_bridge import _PLAN_PRICE_DIRS  # noqa: PLC0415
        assert _PLAN_PRICE_DIRS[0].endswith("ohlcv")
        assert _PLAN_PRICE_DIRS[1].endswith("stocks")
        aapl = bp._load_price_history_for_management("AAPL")
        if aapl is None:
            pytest.skip("no committed AAPL history")
        # A panel frame is close-only; the per-ticker store carries full OHLCV.
        assert len(aapl.columns) > 1, "AAPL resolved to a panel instead of its parquet"

    def test_an_unreachable_name_is_still_a_null(self):
        """The fix widens reach; it does not fabricate. Foreign issuers in no US index
        cache stay unpriced, and that is a real null."""
        assert bp._load_price_history_for_management("ZZZZNOTATICKER") is None


# ===========================================================================
# P4 — every survivor is attempted; helper slicing is not an opportunity gate
# ===========================================================================

def _buy_row(ticker: str, *, priority: float, spot: float = 100.0,
             anchor: str = "2026-07-02") -> dict:
    return {
        "ticker": ticker,
        "dir": "up",
        "conviction": {"score": 70, "band": "neutral", "drivers": ["momentum"],
                       "cautions": ["macro"], "trust_tier": {"en": "tier-2"}},
        "entry_signal": {"act_level": 3, "status": "partial", "spot": spot,
                         "chase_above": spot * 1.03, "atr_pct": 2.0,
                         "entry_grade": "solid"},
        "hold": {"state": "HOLD", "anchor": anchor, "invalidation": spot * 0.9},
        "prophet": {"version": "us_prophet_v1", "score": priority},
    }


def _write_standouts(tmp_path: Path, buys: list[dict], *, as_of="2026-07-02") -> Path:
    path = tmp_path / "us_standouts.json"
    path.write_text(json.dumps({
        "as_of": as_of,
        "staleness": {
            "price_through": as_of,
            "delayed": False,
            "unknown": False,
            "basis": "panel_majority",
            "inputs": {"panel": {"mixed_vintage": False}},
        },
        "gate_go": True,
        "buy": buys,
    }),
                    encoding="utf-8")
    return path


class TestFiltersThenLosslessOrigination:

    def test_a_board_of_already_live_names_still_originates_from_below_the_line(
            self, tmp_path):
        """THE 2026-08-05 night: all 12 capped candidates were re-admissions, so the
        run originated ZERO plans while eligible names sat one row below the cap."""
        buys = ([_buy_row(f"LIVE{i:02d}", priority=99.0 - i) for i in range(N_CANDIDATES)]
                + [_buy_row(f"NEW{i:02d}", priority=50.0 - i) for i in range(6)])
        path = _write_standouts(tmp_path, buys)
        active = {f"LIVE{i:02d}-BULL" for i in range(N_CANDIDATES)}

        stats: dict = {}
        plans = originate_plans(path, "2026-07-02", set(), None,
                                active_keys=active, intake_stats=stats)
        assert [p["asset"] for p in plans] == [f"NEW{i:02d}" for i in range(6)], (
            "the cap was spent on names that were skipped anyway"
        )
        assert stats["reorigination_blocked"] == N_CANDIDATES
        assert stats["eligible_after_skips"] == 6
        assert stats["admitted"] == N_CANDIDATES + 6

    def test_the_old_cap_semantics_would_have_yielded_nothing(self, tmp_path):
        """The falsifier: cap-then-filter, computed here, returns an empty set on the
        same artifact. Without this the test above could pass on any implementation
        that simply originates everything."""
        buys = ([_buy_row(f"LIVE{i:02d}", priority=99.0 - i) for i in range(N_CANDIDATES)]
                + [_buy_row(f"NEW{i:02d}", priority=50.0 - i) for i in range(6)])
        path = _write_standouts(tmp_path, buys)
        with path.open(encoding="utf-8") as fh:
            standouts = json.load(fh)
        old_capped = select_candidates(standouts, n=N_CANDIDATES)
        active = {f"LIVE{i:02d}-BULL" for i in range(N_CANDIDATES)}
        survivors_of_the_old_cap = [
            row for row in old_capped
            if f"{row['ticker']}-BULL" not in active
        ]
        assert survivors_of_the_old_cap == [], (
            "cap-then-filter must yield nothing here, or this fixture does not "
            "reproduce the defect"
        )

    def test_the_old_cap_no_longer_truncates_live_origination(self, tmp_path):
        buys = [_buy_row(f"T{i:02d}", priority=99.0 - i) for i in range(30)]
        path = _write_standouts(tmp_path, buys)
        stats: dict = {}
        plans = originate_plans(path, "2026-07-02", set(), None,
                                active_keys=set(), intake_stats=stats)
        assert len(plans) == 30
        assert stats["eligible_after_skips"] == 30
        assert stats["cap"] is None
        assert stats["cap_applied"] is False
        assert stats["truncated"] == 0
        assert stats["lossless"] is True

    def test_admission_and_order_are_untouched(self, tmp_path):
        """The fence: this change may only ever ADD names from further down the same
        ordering, never re-rank the ones above."""
        buys = [_buy_row(f"T{i:02d}", priority=99.0 - i) for i in range(20)]
        path = _write_standouts(tmp_path, buys)
        plans = originate_plans(path, "2026-07-02", set(), None, active_keys=set())
        with path.open(encoding="utf-8") as fh:
            expected = [r["ticker"] for r in
                        select_candidates(json.load(fh), n=None)]
        assert [p["asset"] for p in plans] == expected

    def test_uncapped_select_returns_the_whole_admitted_pool(self, tmp_path):
        buys = [_buy_row(f"T{i:02d}", priority=99.0 - i) for i in range(30)]
        path = _write_standouts(tmp_path, buys)
        with path.open(encoding="utf-8") as fh:
            standouts = json.load(fh)
        assert len(select_candidates(standouts, n=None)) == 30
        assert len(select_candidates(standouts, n=N_CANDIDATES)) == N_CANDIDATES

    def test_duplicate_ids_are_still_suppressed_before_origination(self, tmp_path):
        buys = [_buy_row(f"T{i:02d}", priority=99.0 - i) for i in range(4)]
        path = _write_standouts(tmp_path, buys)
        existing = {"T00-BULL-20260702", "T01-BULL-20260702"}
        stats: dict = {}
        plans = originate_plans(path, "2026-07-02", set(existing), None,
                                active_keys=set(), intake_stats=stats)
        assert [p["asset"] for p in plans] == ["T02", "T03"]
        assert stats["duplicate_id_blocked"] == 2


# ===========================================================================
# P1 (origination side) — every new plan carries its entry_date
# ===========================================================================

class TestOriginationStampsTheClock:

    def test_every_new_plan_separates_entry_price_session_from_run_date(self, tmp_path):
        price_session = "2026-07-02"
        run_date = "2026-07-03"
        path = _write_standouts(
            tmp_path,
            [_buy_row("AAA", priority=90.0, anchor=FORMATION)],
            as_of=price_session,
        )
        plans = originate_plans(path, run_date, set(), None, active_keys=set())
        assert len(plans) == 1
        plan = plans[0]
        assert plan["entry_date"] == plan["price_basis_date"] == price_session
        assert plan["asof"] == plan["recorded_at"] == run_date
        assert plan["signal_date"] == FORMATION, "the id anchor is unchanged"
        assert plan["id"].endswith("20260301"), "no key migration"
        assert plan_clock_date(plan) == price_session

    def test_the_priority_score_the_pick_was_ordered_by_is_frozen_on_the_plan(
            self, tmp_path):
        path = _write_standouts(tmp_path, [_buy_row("AAA", priority=88.5)])
        plans = originate_plans(path, "2026-07-02", set(), None, active_keys=set())
        assert plans[0]["_priority_score"] == 88.5


# ===========================================================================
# Prospective Plan source_origin — original producer binding propagation
# ===========================================================================

_BOARD_EMIT = {
    "emit": {
        "pair_id": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
        "at_utc": "2026-07-02T21:00:00Z",
    },
    "board_definition": "us_prophet_v3",
}


def _producer_binding(raw: bytes) -> dict:
    """The frozen producer contract, mirrored over the SAME raw bytes.

    Mirrors ``scripts.build_stock_library.today_selection_source_binding`` so
    these tests pin the binding's own shape without importing the builder
    module; the production derivation path imports the real callable.
    """
    from engine.us_candidate_episode import canonical_json  # noqa: PLC0415

    doc = json.loads(raw)
    rows = [
        {"selection_index": index,
         "row_receipt": "sha256:" + hashlib.sha256(
             canonical_json(row).encode("utf-8")).hexdigest()}
        for index, row in enumerate(doc["buy"])
    ]
    material = {
        "source_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "pair_id": doc["emit"]["pair_id"],
        "market_session": doc["as_of"],
        "ordered_rows": rows,
    }
    return {
        **material,
        "selection_receipt": "sha256:" + hashlib.sha256(
            canonical_json(material).encode("utf-8")).hexdigest(),
        "schema": "prophet.today_selection_source_binding/v1",
        "receipt_kind": "EXACT_DISPLAYED_SOURCE",
    }


class TestPlanSourceOriginOrigination:
    """source_origin propagation: original positions, refusals, both index paths."""

    @staticmethod
    def _binding_for(tmp_path, buys):
        path = TestPlanSourceOriginOrigination._write_emit_standouts(tmp_path, buys)
        return _producer_binding(path.read_bytes())

    @staticmethod
    def _write_emit_standouts(tmp_path, buys):
        path = _write_standouts(tmp_path, buys)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.update(_BOARD_EMIT)
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_original_positions_survive_selection_and_duplicate_tickers(
            self, tmp_path):
        """Duplicate tickers and lower-ranked rows keep their ORIGINAL buy[] index.

        Positions come from object identity captured before selection reorders
        the board — never from a ticker join, which would collide on the two DUP
        rows.
        """
        binding = self._binding_for(tmp_path, [
            _buy_row("DUP", priority=99.0, spot=101.0),
            _buy_row("OTHER", priority=90.0),
            _buy_row("DUP", priority=80.0, spot=102.0, anchor="2026-07-01"),
        ])
        stats: dict = {}
        plans = originate_plans(
            tmp_path / "us_standouts.json", "2026-07-02", set(), None,
            source_binding=binding, intake_stats=stats)
        assert stats["lossless"] is True and len(plans) == 3
        origins = {p["source_origin"]["selection_index"]: p for p in plans}
        assert sorted(origins) == [0, 1, 2]
        for index, plan in origins.items():
            origin = plan["source_origin"]
            assert origin["schema"] == "prophet.plan_source_origin/v1"
            assert origin["owner_ref"] == "scripts/build_stock_library.py::main"
            assert origin["receipt_kind"] == "EXACT_DISPLAYED_SOURCE"
            assert origin["source_binding"] == binding
            assert origin["row_receipt"] == \
                binding["ordered_rows"][index]["row_receipt"]
        # the two same-ticker rows are distinguished by POSITION, not by ticker
        assert origins[0]["entry"] == 101.0 and origins[2]["entry"] == 102.0
        assert origins[1]["asset"] == "OTHER"
        from engine.options_structure import validate_trade_plan  # noqa: PLC0415
        assert all(validate_trade_plan(p) == [] for p in plans)

    def test_missing_binding_keeps_plans_unstamped_and_admission_identical(
            self, tmp_path):
        buys = [_buy_row("AAA", priority=90.0), _buy_row("BBB", priority=80.0)]
        path = _write_standouts(tmp_path, buys)
        stats: dict = {}
        plans = originate_plans(path, "2026-07-02", set(), None, intake_stats=stats)
        assert len(plans) == 2 and stats["lossless"] is True
        assert all("source_origin" not in plan for plan in plans)

    def test_wrong_typed_binding_is_refused_at_the_boundary(self, tmp_path):
        path = _write_standouts(tmp_path, [_buy_row("AAA", priority=90.0)])
        assert len(originate_plans(path, "2026-07-02", set(), None)) == 1
        for bad in (["not", "a", "mapping"], "sha256:stuff", 7, {"ordered_rows": 3}):
            with pytest.raises(TypeError):
                originate_plans(path, "2026-07-02", set(), None, source_binding=bad)

    def test_binding_for_a_differently_shaped_board_is_refused(self, tmp_path):
        """Cover is checked at the boundary: one receipt per ORIGINAL buy row.

        Byte identity itself is pinned upstream, where the derivation refuses a
        retained snapshot that does not hash and parse to the frozen board.
        """
        binding = self._binding_for(tmp_path, [_buy_row("AAA", priority=90.0)])
        (tmp_path / "other").mkdir()
        other = _write_standouts(tmp_path / "other", [
            _buy_row("BBB", priority=90.0), _buy_row("CCC", priority=89.0)])
        with pytest.raises(ValueError):
            originate_plans(other, "2026-07-02", set(), None, source_binding=binding)

    def test_refuse_binding_for_changed_same_count_board(self, tmp_path):
        """A same-count board that is NOT the bound source refuses.

        A replaced row and a reordered board both carry the right NUMBER of buy
        rows, so count-cover alone would stamp them with positions the original
        producer never published.  Per-row receipt identity refuses both.
        """
        from scripts.build_stock_library import (  # noqa: PLC0415
            today_selection_source_binding,
        )

        path = self._write_emit_standouts(tmp_path, [
            _buy_row("AAA", priority=90.0), _buy_row("BBB", priority=89.0)])
        binding = today_selection_source_binding(path.read_bytes())
        doc = json.loads(path.read_bytes())
        doc["buy"][0]["ticker"] = "CCC"
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=binding)
        doc = json.loads(path.read_bytes())
        doc["buy"].reverse()
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=binding)

    def test_actual_producer_binding_stamps_exact_original_origins(self, tmp_path):
        """The REAL frozen producer callable, over the original raw bytes, clears
        the boundary and stamps each plan with its exact original origin.

        The mirrored ``_producer_binding`` helper is not the oracle here: this is
        the production callable over the exact displayed bytes.
        """
        from scripts.build_stock_library import (  # noqa: PLC0415
            today_selection_source_binding,
        )

        path = self._write_emit_standouts(tmp_path, [
            _buy_row("DUP", priority=99.0, spot=101.0),
            _buy_row("OTHER", priority=90.0),
            _buy_row("DUP", priority=80.0, spot=102.0, anchor="2026-07-01"),
        ])
        binding = today_selection_source_binding(path.read_bytes())
        stats: dict = {}
        plans = originate_plans(path, "2026-07-02", set(), None,
                                source_binding=binding, intake_stats=stats)
        assert stats["lossless"] is True and len(plans) == 3
        origins = {p["source_origin"]["selection_index"]: p for p in plans}
        assert sorted(origins) == [0, 1, 2]
        for index, plan in origins.items():
            assert plan["source_origin"]["source_binding"] == binding
            assert plan["source_origin"]["row_receipt"] == \
                binding["ordered_rows"][index]["row_receipt"]
        # duplicate tickers keep their ORIGINAL ordinals — position, not a join
        assert origins[0]["entry"] == 101.0 and origins[2]["entry"] == 102.0
        assert origins[1]["asset"] == "OTHER"

    def test_refuse_wrong_scalar_pins_and_malformed_bound_metadata(self, tmp_path):
        """Pair/session pins must match the supplied board where representable,
        and malformed bound metadata refuses rather than stamps."""
        from scripts.build_stock_library import (  # noqa: PLC0415
            today_selection_source_binding,
        )

        path = self._write_emit_standouts(
            tmp_path, [_buy_row("AAA", priority=90.0), _buy_row("BBB", priority=89.0)])
        raw = path.read_bytes()
        doc = json.loads(raw)

        wrong_session = today_selection_source_binding(raw)
        wrong_session["market_session"] = "2026-07-01"
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=wrong_session)

        wrong_pair = today_selection_source_binding(raw)
        wrong_pair["pair_id"] = "ffffffffffffffffffffffffffffffff"
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=wrong_pair)

        malformed_sha = today_selection_source_binding(raw)
        malformed_sha["source_sha256"] = "sha256:" + "z" * 64
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=malformed_sha)

        duplicate_ordinal = today_selection_source_binding(raw)
        duplicate_ordinal["ordered_rows"][1]["selection_index"] = 0
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=duplicate_ordinal)

        tampered_envelope = today_selection_source_binding(raw)
        tampered_envelope["selection_receipt"] = "sha256:" + "0" * 64
        with pytest.raises(ValueError):
            originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=doc, source_binding=tampered_envelope)

    def test_builder_derives_the_binding_from_the_retained_snapshot_only(
            self, tmp_path, monkeypatch):
        """The moving source file is GONE; the binding still derives, unchanged.

        Proves the derivation decompresses only the content-addressed snapshot
        written by the freeze, never re-reads the live board path.
        """
        import scripts.build_prophet as bp  # noqa: PLC0415

        path = self._write_emit_standouts(tmp_path, [_buy_row("AAA", priority=90.0)])
        raw = path.read_bytes()
        monkeypatch.setattr(bp, "STANDOUTS_PATH", path)
        monkeypatch.setattr(bp, "LEDGER_DIR", tmp_path / "data" / "prophet")
        monkeypatch.setattr(bp, "LEDGER_PATH",
                            tmp_path / "data" / "prophet" / "ledger.jsonl")
        _, board_sha, _rel = bp._freeze_origination_source_board(path)
        path.unlink()
        binding = bp._load_origination_source_binding(
            source_board_sha256=board_sha, source_board_doc=json.loads(raw))
        assert binding["source_sha256"] == "sha256:" + board_sha
        assert binding["market_session"] == "2026-07-02"
        assert binding["receipt_kind"] == "EXACT_DISPLAYED_SOURCE"
        assert len(binding["ordered_rows"]) == 1
        assert binding == _producer_binding(raw)

    def test_builder_stamps_new_plans_on_both_index_paths_and_spares_history(
            self, tmp_path, monkeypatch):
        """Ordinary AND degraded index rows carry the exact new-plan origin; a
        historical plan stays key-absent everywhere and its file is untouched."""
        import scripts.build_prophet as bp  # noqa: PLC0415

        path = self._write_emit_standouts(
            tmp_path, [_buy_row("AAA", priority=90.0), _buy_row("BBB", priority=89.0)])
        binding = _producer_binding(path.read_bytes())
        historical = {
            "schema": "prophet.trade_plan/v1",
            "id": "OLD-BULL-20200101",
            "asof": "2020-01-01",
            "asset": "OLD",
            "direction": "BULL",
            "source_engines": ["us_standouts_buy_lane"],
        }
        plans_dir = tmp_path / "site" / "prophet" / "plans"
        plans_dir.mkdir(parents=True)
        (plans_dir / "OLD-BULL-20200101.json").write_text(
            json.dumps(historical), encoding="utf-8")
        monkeypatch.setattr(bp, "STANDOUTS_PATH", path)
        monkeypatch.setattr(bp, "SITE_PROPHET", tmp_path / "site" / "prophet")
        monkeypatch.setattr(bp, "PLANS_DIR", plans_dir)
        monkeypatch.setattr(bp, "STATES_DIR", tmp_path / "site" / "prophet" / "states")
        monkeypatch.setattr(bp, "INDEX_PATH",
                            tmp_path / "site" / "prophet" / "index.json")
        monkeypatch.setattr(bp, "LEDGER_DIR", tmp_path / "data" / "prophet")
        monkeypatch.setattr(bp, "LEDGER_PATH",
                            tmp_path / "data" / "prophet" / "ledger.jsonl")
        monkeypatch.setattr(bp, "write_showcase", lambda: None)
        frame = _closes([100.0] * 5, start="2026-06-25")
        monkeypatch.setattr(
            bp, "_load_price_history_for_management",
            lambda ticker: None if ticker == "BBB" else frame)
        with patch("scripts.build_prophet.compute_management_state") as mock_mgmt:
            mock_mgmt.return_value = {
                "schema": "prophet.management_state/v1",
                "id": "x",
                "asof": "2026-07-02",
                "phase": "pre_trigger",
                "management_confidence": 55.0,
                "raw_confidence": 55.0,
                "recommended_action": "wait",
                "components": {},
                "geometry": {},
                "change_reason": "",
            }
            with patch("engine.prophet_arena.run_arena", return_value={
                "policies": [], "harness_validity": {"harness_ok": True},
            }):
                with patch.object(sys, "argv",
                                  ["build_prophet", "--date", "2026-07-02"]):
                    bp.main()

        index = json.loads(bp.INDEX_PATH.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in index["plans"]}
        new_plan = json.loads((plans_dir / "AAA-BULL-20260702.json").read_text())
        assert new_plan["source_origin"]["source_binding"] == binding
        assert new_plan["source_origin"]["selection_index"] == 0
        assert index["source_board_sha256"] == binding["source_sha256"][len("sha256:"):]
        # ordinary row: the plan's origin, unchanged
        assert rows["AAA-BULL-20260702"]["source_origin"] == new_plan["source_origin"]
        # degraded row: the same exact origin
        degraded_plan = json.loads(
            (plans_dir / "BBB-BULL-20260702.json").read_text())
        assert rows["BBB-BULL-20260702"]["management_status"] == "unavailable"
        assert (rows["BBB-BULL-20260702"]["source_origin"]
                == degraded_plan["source_origin"])
        # historical plan: key ABSENT on the row and on the untouched file
        assert "source_origin" not in rows["OLD-BULL-20200101"]
        assert json.loads(
            (plans_dir / "OLD-BULL-20200101.json").read_text()) == historical


# ===========================================================================
# P5 / P6 — closed-state copy and shipped order
# ===========================================================================

class TestClosedStateCopy:

    def test_a_closed_plan_ships_no_live_instruction(self):
        en, zh = bp._closed_state_lines("INVALIDATED")
        assert len(en) == 1 and len(zh) == 1
        text = en[0].lower()
        assert "closed" in text
        for banned in ("buy", "stop at", "trim", "add ", "enter"):
            assert banned not in text, f"{banned!r} is an instruction on a dead thesis"

    def test_the_outcome_is_stated_in_plain_words_not_ledger_slugs(self):
        en, zh = bp._closed_state_lines("T1_HIT")
        assert "hit first target" in en[0]
        assert "T1_HIT" not in en[0]
        assert zh[0].startswith("该计划已结束")

    def test_an_unmapped_outcome_still_says_it_is_over(self):
        en, zh = bp._closed_state_lines(None)
        assert "closed" in en[0].lower() and zh[0]
        en2, _ = bp._closed_state_lines("SOMETHING_NEW")
        assert "closed" in en2[0].lower()

    def test_both_halves_are_always_present(self):
        for outcome in (None, "", "T1_HIT", "T2_HIT", "INVALIDATED", "EXPIRED", "XX"):
            en, zh = bp._closed_state_lines(outcome)
            assert en and zh, outcome


class TestIndexOrderMatchesTheDeclaredKey:

    @staticmethod
    def _sorted(entries):
        rows = list(entries)
        rows.sort(key=lambda e: (
            0 if isinstance(e.get("_priority_score"), (int, float))
            and not isinstance(e.get("_priority_score"), bool) else 1,
            -(e.get("_priority_score")
              if isinstance(e.get("_priority_score"), (int, float))
              and not isinstance(e.get("_priority_score"), bool)
              else (e.get("_conviction_score") or 0)),
            e.get("id", ""),
        ))
        return [r["id"] for r in rows]

    def test_priority_score_outranks_conviction(self):
        """The artifact declares the priority score; conviction carries ZERO ordering
        authority in this system (US_BOARD_MEASUREMENT.md). The two disagree here."""
        entries = [
            {"id": "LOWPRI", "_priority_score": 10.0, "_conviction_score": 95},
            {"id": "HIGHPRI", "_priority_score": 90.0, "_conviction_score": 40},
        ]
        assert self._sorted(entries) == ["HIGHPRI", "LOWPRI"]

    def test_an_unscored_plan_sorts_below_every_scored_one(self):
        entries = [
            {"id": "LEGACY", "_priority_score": None, "_conviction_score": 99},
            {"id": "SCORED", "_priority_score": 1.0, "_conviction_score": 1},
        ]
        assert self._sorted(entries) == ["SCORED", "LEGACY"]

    def test_legacy_rows_keep_the_old_key_among_themselves(self):
        entries = [
            {"id": "A", "_priority_score": None, "_conviction_score": 10},
            {"id": "B", "_priority_score": None, "_conviction_score": 80},
        ]
        assert self._sorted(entries) == ["B", "A"]

    def test_id_breaks_a_tie_so_the_order_is_deterministic(self):
        entries = [
            {"id": "ZZZ", "_priority_score": 5.0},
            {"id": "AAA", "_priority_score": 5.0},
        ]
        assert self._sorted(entries) == ["AAA", "ZZZ"]


def test_source_origin_extension_preserves_existing_positional_frozen_board(tmp_path):
    path = TestPlanSourceOriginOrigination._write_emit_standouts(
        tmp_path, [_buy_row("AAA", priority=90.0)])
    frozen = json.loads(path.read_bytes())
    path.unlink()
    # The existing seventh argument is the immutable document, never a receipt.
    plans = originate_plans(path, "2026-07-02", set(), None, None, {}, frozen)
    assert len(plans) == 1 and plans[0]["id"] == "AAA-BULL-20260702"
    assert "source_origin" not in plans[0]


# ===========================================================================
# Fixed Plan-native source read — read_plan_candidate_source
#
# Every fixture here is real: the board is frozen by the real
# `_freeze_origination_source_board`, the plans are originated by the real
# `originate_plans` with the REAL producer binding over the exact board bytes,
# and the native B1 store is written by the ordinary nightly reconciler. The
# reader itself must stay a pure read: the byte/head state assertions below
# are part of every scenario's contract, not a separate test.
# ===========================================================================

import gzip  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
from datetime import datetime as _RealDatetime, timezone as _timezone  # noqa: E402

from engine.us_candidate_episode import (  # noqa: E402
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from scripts import reconcile_us_candidate_episodes as _episode_writer  # noqa: E402
from scripts.build_stock_library import (  # noqa: E402
    today_selection_row_receipts as _producer_row_receipts,
    today_selection_source_binding as _producer_binding_of,
)

_PLAN_READ_KEYS = {
    "schema", "plan_id", "read_status", "reason_codes", "plan_sha256",
    "source_relation_status", "source_relation_reasons", "current_action_status",
    "current_action_reasons", "source_origin", "source_binding", "native_identity",
    "episode_lifecycle", "clocks", "generated_at",
}
_PLAN_SESSION = "2026-07-02"
_PLAN_CURRENT_REASON = "PLAN_CURRENT_DECISION_QUALIFICATION_UNAVAILABLE"


def _plan_identity_rows(ticker: str) -> tuple[list[dict], list[dict]]:
    """Data OS identity rows in the exact shape the shared fixtures use."""
    listing = f"US-XNAS-{ticker}"
    return (
        [{"issuer_id": f"ISS:{listing}", "issuer_state": "ACTIVE",
          "listing_key": listing, "security_id": f"SEC:{listing}"}],
        [{"security_id": f"SEC:{listing}", "valid_from": "2020-01-01",
          "valid_to": None, "vendor": "membership", "vendor_symbol": ticker}],
    )


def _plan_turn_watch_document(session: str, tickers) -> dict:
    """Generation-local TURN WATCH source for every requested ticker."""
    document = {"schema": "prophet.candidate_episode_input.turn_watch/v1",
                "anchor_era": "anchor-v1", "selection_era": "anticipation-v1",
                "data_session": session, "known_at": session + "T22:00:00Z",
                "rows": [{"asof": session, "ticker": ticker,
                          "reset": {"reset_low": 42.1, "reset_low_date": session},
                          "triggers": {"dot_1d": {"evaluated": True, "fired": True,
                                                  "last_date": session}}}
                         for ticker in tickers]}
    document["content_sha256"] = hashlib.sha256(canonical_json(
        {key: value for key, value in document.items()
         if key != "content_sha256"}).encode()).hexdigest()
    return document


def _plan_fixture(
    tmp_path, monkeypatch, buys, *, tickers,
    with_candidates=True, recorded_at="2026-07-02T22:06:00Z",
):
    """Real frozen board + real originated plans + real native B1 store."""
    from scripts import build_stock_library as native_owner
    monkeypatch.setattr(native_owner, "__file__", str(tmp_path / "scripts/build_stock_library.py"))
    monkeypatch.setattr(_episode_writer, "nightly_advance_enabled", lambda: True)
    reference = tmp_path / "data/reference"
    reference.mkdir(parents=True)
    masters: list[dict] = []
    aliases: list[dict] = []
    for ticker in tickers:
        master_rows, alias_rows = _plan_identity_rows(ticker)
        masters.extend(master_rows)
        aliases.extend(alias_rows)
    pd.DataFrame(masters).to_parquet(reference / "security_master.parquet", index=False)
    pd.DataFrame(aliases).to_parquet(reference / "vendor_aliases.parquet", index=False)
    turn = tmp_path / "data/us_prophet_rank/episode_inputs/turn_watch/2026-07-02.json"
    turn.parent.mkdir(parents=True)
    turn.write_text(canonical_json(_plan_turn_watch_document(_PLAN_SESSION, tickers)) + "\n")
    _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                              recorded_at="2026-07-02T22:05:00Z", correction_path=None)

    path = TestPlanSourceOriginOrigination._write_emit_standouts(tmp_path, buys)
    raw = path.read_bytes()
    binding = _producer_binding_of(raw)
    monkeypatch.setattr(bp, "STANDOUTS_PATH", path)
    monkeypatch.setattr(bp, "LEDGER_DIR", tmp_path / "data" / "prophet")
    monkeypatch.setattr(bp, "LEDGER_PATH", tmp_path / "data" / "prophet" / "ledger.jsonl")
    monkeypatch.setattr(bp, "SITE_PROPHET", tmp_path / "site" / "prophet")
    monkeypatch.setattr(bp, "STATES_DIR", tmp_path / "site" / "prophet" / "states")
    monkeypatch.setattr(bp, "INDEX_PATH", tmp_path / "site" / "prophet" / "index.json")
    bp._freeze_origination_source_board(path)
    stats: dict = {}
    plans = originate_plans(path, "2026-07-02", set(), None,
                            standouts_doc=json.loads(raw), source_binding=binding,
                            intake_stats=stats)
    assert stats["lossless"] is True and len(plans) == len(buys)
    plans_dir = tmp_path / "site" / "prophet" / "plans"
    plans_dir.mkdir(parents=True)
    for plan in plans:
        (plans_dir / f"{plan['id']}.json").write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(bp, "PLANS_DIR", plans_dir)
    _plan_write_native_candidates(tmp_path, monkeypatch, path, tickers,
                                  recorded_at=recorded_at, reconcile=with_candidates)
    return plans, binding, path


def _plan_write_native_candidates(tmp_path, monkeypatch, path, tickers, *,
                                  recorded_at="2026-07-02T22:06:00Z", reconcile=True):
    """The ordinary writer run that binds the board rows into the B1 ledger."""
    from engine import us_context_vector as context_owner  # noqa: PLC0415

    raw = path.read_bytes()
    records = context_owner.build_records(
        {ticker: {} for ticker in tickers}, stamp_date=_PLAN_SESSION,
        board_definition="us_prophet_v3", is_buyable=lambda _: False,
        today_selection_row_receipts=_producer_row_receipts(raw))
    candidate = tmp_path / "data/us_prophet_rank/candidates/2026-07.parquet"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(candidate, index=False)
    if reconcile:
        _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                  recorded_at=recorded_at, correction_path=None)


def _plan_episode_root(tmp_path):
    return tmp_path / "data" / "us_prophet_rank" / "episodes"


def _plan_owner_state(tmp_path) -> dict:
    """Every byte the reader must leave exactly where it found it."""
    state = {}
    for path in sorted(tmp_path.rglob("*")):
        if path.is_file() and not path.is_symlink():
            state[str(path.relative_to(tmp_path))] = hashlib.sha256(
                path.read_bytes()).hexdigest()
    return state


def _plan_write(plan_file, plan):
    plan_file.write_text(json.dumps(plan), encoding="utf-8")


def _plan_source_snapshot(tmp_path, binding):
    """The ONE content-addressed snapshot file this plan's binding names."""
    digest = binding["source_sha256"][len("sha256:"):]
    return tmp_path / "data" / "prophet" / "origination_sources" / (digest + ".json.gz")


class TestPlanNativeSourceRead:

    def test_the_exact_original_source_relation_is_resolved(self, tmp_path, monkeypatch):
        plans, binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        before = _plan_owner_state(tmp_path)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert set(read) == _PLAN_READ_KEYS
        assert read["read_status"] == "AVAILABLE" and read["reason_codes"] == []
        assert read["source_relation_status"] == "BOUND"
        assert read["source_relation_reasons"] == []
        # ACTIVE never grants anything: the current action is unavailable by
        # construction, with the explicit missing current-decision qualifier.
        assert read["current_action_status"] == "UNAVAILABLE"
        assert read["current_action_reasons"] == [_PLAN_CURRENT_REASON]
        plan_file = bp.PLANS_DIR / f"{plans[0]['id']}.json"
        assert read["plan_sha256"] == (
            "sha256:" + hashlib.sha256(plan_file.read_bytes()).hexdigest())
        assert read["source_binding"] == binding
        assert read["source_origin"] == {
            "selection_index": 0,
            "row_receipt": binding["ordered_rows"][0]["row_receipt"],
            "source_event_id": f"candidate:{_PLAN_SESSION}:AAA:us_prophet_v3",
            "source_receipt": read["source_origin"]["source_receipt"],
        }
        assert read["source_origin"]["source_receipt"].startswith("sha256:")
        snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
        relation = next(event for event in snapshot.generation.events
                        if event.get("source_event_id") == read["source_origin"]["source_event_id"])
        assert read["native_identity"] == {
            "security_id": "SEC:US-XNAS-AAA",
            "episode_id": relation["episode_id"],
            "candidate_generation_id": snapshot.generation_id,
            "market_session": _PLAN_SESSION,
        }
        # Original clocks are kept original and separate — never relabeled.
        assert read["clocks"] == {
            "source_emitted_at": "2026-07-02T21:00:00Z",
            "source_session": _PLAN_SESSION,
            "formation_date": "2026-07-01",
            "plan_recorded_at": "2026-07-02",
            "native_known_at": relation["known_at"],
            "native_recorded_at": relation["recorded_at"],
            "generation_recorded_at": snapshot.generation.receipt["recorded_at"],
        }
        assert read["episode_lifecycle"]["episode_state"] == "ACTIVE"
        assert read["episode_lifecycle"]["terminal_reason"] is None
        assert read["episode_lifecycle"]["security_id"] == "SEC:US-XNAS-AAA"
        assert read["generated_at"].endswith("Z") and "T" in read["generated_at"]
        # The reader changed nothing it read.
        assert _plan_owner_state(tmp_path) == before

    def test_non_featured_and_repeated_ticker_rows_keep_their_original_positions(
            self, tmp_path, monkeypatch):
        buys = [
            _buy_row("DUP", priority=99.0, spot=101.0, anchor="2026-07-01"),
            _buy_row("OTHER", priority=90.0, anchor="2026-07-01"),
            _buy_row("DUP", priority=80.0, spot=102.0, anchor="2026-06-30"),
        ]
        plans, binding, _path = _plan_fixture(tmp_path, monkeypatch, buys,
                                              tickers=["DUP", "OTHER"])
        by_ordinal = {plan["source_origin"]["selection_index"]: plan for plan in plans}
        assert sorted(by_ordinal) == [0, 1, 2]
        first = bp.read_plan_candidate_source(by_ordinal[0]["id"])
        second = bp.read_plan_candidate_source(by_ordinal[1]["id"])
        third = bp.read_plan_candidate_source(by_ordinal[2]["id"])
        # Position, never a ticker join: the two DUP plans read DIFFERENT
        # original rows at their own ordinals.
        assert first["source_origin"]["selection_index"] == 0
        assert third["source_origin"]["selection_index"] == 2
        assert (first["source_origin"]["row_receipt"]
                == binding["ordered_rows"][0]["row_receipt"])
        assert (third["source_origin"]["row_receipt"]
                == binding["ordered_rows"][2]["row_receipt"])
        assert first["source_origin"]["row_receipt"] != third["source_origin"]["row_receipt"]
        assert second["read_status"] == "AVAILABLE"
        assert second["source_relation_status"] == "BOUND"
        # The two same-ticker board rows are one ambiguous native row: no
        # receipt was ever published for them, so the source relation is
        # unavailable — never silently joined by ticker.
        for dup_read in (first, third):
            assert dup_read["source_relation_status"] == "UNAVAILABLE"
            assert dup_read["source_relation_reasons"] == ["ROW_PROVENANCE_UNAVAILABLE"]
            assert dup_read["native_identity"] is None
            assert dup_read["current_action_reasons"] == [
                _PLAN_CURRENT_REASON, "ROW_PROVENANCE_UNAVAILABLE"]

    def test_pending_before_the_native_writer_then_resolved_by_ordinary_reread(
            self, tmp_path, monkeypatch):
        plans, _binding, path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"],
            with_candidates=False)
        pending = bp.read_plan_candidate_source(plans[0]["id"])
        assert pending["source_relation_status"] == "PENDING"
        assert pending["source_relation_reasons"] == ["CANDIDATE_RECONCILIATION_PENDING"]
        assert pending["native_identity"] is None
        assert pending["episode_lifecycle"] is None
        assert pending["current_action_reasons"] == [_PLAN_CURRENT_REASON]
        _plan_write_native_candidates(tmp_path, monkeypatch, path, ["AAA"])
        head_before = (_plan_episode_root(tmp_path) / "HEAD.json").read_bytes()
        resolved = bp.read_plan_candidate_source(plans[0]["id"])
        assert resolved["source_relation_status"] == "BOUND"
        assert resolved["read_status"] == "AVAILABLE"
        assert (_plan_episode_root(tmp_path) / "HEAD.json").read_bytes() == head_before

    def test_a_replaced_current_board_cannot_substitute_for_the_original(
            self, tmp_path, monkeypatch):
        plans, binding, path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        # The live board is GONE: the reader must run on the retained snapshot.
        path.unlink()
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["read_status"] == "AVAILABLE"
        assert read["source_binding"]["source_sha256"] == binding["source_sha256"]
        # A newer board exists now; its bytes can never enter this envelope.
        newer = TestPlanSourceOriginOrigination._write_emit_standouts(tmp_path, [
            _buy_row("NEW", priority=10.0, anchor="2026-07-01")])
        newer_raw = newer.read_bytes()
        assert read["source_binding"]["source_sha256"] != (
            "sha256:" + hashlib.sha256(newer_raw).hexdigest())
        again = bp.read_plan_candidate_source(plans[0]["id"])
        assert {k: v for k, v in again.items() if k != "generated_at"} == {
            k: v for k, v in read.items() if k != "generated_at"}

    def test_same_count_replacement_and_reordering_are_refused_not_renumbered(
            self, tmp_path, monkeypatch):
        plans, binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01"),
            _buy_row("BBB", priority=80.0, anchor="2026-07-01")], tickers=["AAA", "BBB"])
        plan_file = bp.PLANS_DIR / f"{plans[0]['id']}.json"
        # Self-consistently renumbered onto ANOTHER original row of the SAME
        # board: the terms at that ordinal are not this plan's original row.
        swapped = json.loads(json.dumps(plans[0]))
        swapped["source_origin"]["selection_index"] = 1
        swapped["source_origin"]["row_receipt"] = binding["ordered_rows"][1]["row_receipt"]
        _plan_write(plan_file, swapped)
        assert bp.read_plan_candidate_source(plans[0]["id"])[
            "reason_codes"] == ["PLAN_SOURCE_ROW_MISMATCH"]
        # A binding that is internally consistent but is NOT over the retained
        # snapshot bytes refuses against the actual producer derivation.
        forged = json.loads(json.dumps(swapped))
        forged["source_origin"]["selection_index"] = 0
        forged["source_origin"]["source_binding"] = json.loads(json.dumps(binding))
        forged["source_origin"]["source_binding"]["ordered_rows"][0]["row_receipt"] = (
            "sha256:" + hashlib.sha256(b"other bytes").hexdigest())
        forged["source_origin"]["row_receipt"] = (
            forged["source_origin"]["source_binding"]["ordered_rows"][0]["row_receipt"])
        forged["source_origin"]["source_binding"]["selection_receipt"] = (
            "sha256:" + hashlib.sha256(canonical_json({
                "source_sha256": forged["source_origin"]["source_binding"]["source_sha256"],
                "pair_id": binding["pair_id"],
                "market_session": binding["market_session"],
                "ordered_rows": forged["source_origin"]["source_binding"]["ordered_rows"],
            }).encode()).hexdigest())
        _plan_write(plan_file, forged)
        assert bp.read_plan_candidate_source(plans[0]["id"])[
            "reason_codes"] == ["PLAN_SOURCE_BINDING_MISMATCH"]

    def test_missing_corrupt_and_symlinked_sources_fail_closed(self, tmp_path, monkeypatch):
        plans, binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        plan_id = plans[0]["id"]
        historical = json.loads(json.dumps(plans[0]))
        historical.pop("source_origin")
        historical.update(id="OLD-BULL-20200101", asset="OLD", formation_date="2020-01-01")
        _plan_write(bp.PLANS_DIR / "OLD-BULL-20200101.json", historical)
        # Missing old source_origin is explicitly unavailable, never inferred.
        assert bp.read_plan_candidate_source("OLD-BULL-20200101")[
            "reason_codes"] == ["PLAN_SOURCE_ORIGIN_UNAVAILABLE"]
        assert bp.read_plan_candidate_source("NOPE-BULL-20260101")[
            "reason_codes"] == ["PLAN_READ_UNAVAILABLE"]
        # Noncanonical and traversal identities refuse before any read.
        for bad_id in ("../etc/passwd", "AAA/BULL/20260701", "AAA-BULL-2026070",
                       "AAA-BULL-2026-07-01", ""):
            read = bp.read_plan_candidate_source(bad_id)
            assert read["read_status"] == "UNAVAILABLE"
            assert read["reason_codes"] == ["PLAN_IDENTITY_UNAVAILABLE"]
        snapshot = _plan_source_snapshot(tmp_path, binding)
        retained = snapshot.read_bytes()
        snapshot.write_bytes(b"corrupt")
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_SOURCE_SNAPSHOT_UNAVAILABLE"]
        snapshot.write_bytes(gzip.compress(b"{}", mtime=0))
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_SOURCE_SNAPSHOT_DIGEST_MISMATCH"]
        snapshot.unlink()
        snapshot.write_bytes(retained)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "copy.json.gz").write_bytes(retained)
        snapshot.unlink()
        os.symlink(elsewhere / "copy.json.gz", snapshot)
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_SOURCE_SNAPSHOT_SYMLINK_UNAVAILABLE"]
        snapshot.unlink()
        snapshot.write_bytes(retained)
        plan_bytes = (bp.PLANS_DIR / f"{plan_id}.json").read_bytes()
        (elsewhere / "plan.json").write_bytes(plan_bytes)
        (bp.PLANS_DIR / f"{plan_id}.json").unlink()
        os.symlink(elsewhere / "plan.json", bp.PLANS_DIR / f"{plan_id}.json")
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_PATH_SYMLINK_UNAVAILABLE"]
        (bp.PLANS_DIR / f"{plan_id}.json").unlink()
        _plan_write(bp.PLANS_DIR / f"{plan_id}.json", plans[0])
        real_plans_dir = bp.PLANS_DIR
        os.symlink(real_plans_dir, tmp_path / "plans_link")
        monkeypatch.setattr(bp, "PLANS_DIR", tmp_path / "plans_link")
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_PATH_SYMLINK_UNAVAILABLE"]
        monkeypatch.setattr(bp, "PLANS_DIR", real_plans_dir)
        # Unavailable native inputs are typed, not guessed around.
        shutil.rmtree(tmp_path / "data" / "us_prophet_rank" / "candidates")
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["CANDIDATE_SNAPSHOT_UNAVAILABLE"]
        _plan_write_native_candidates(tmp_path, monkeypatch, _path, ["AAA"])
        shutil.rmtree(_plan_episode_root(tmp_path))
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["CANDIDATE_SNAPSHOT_UNAVAILABLE"]

    def test_plan_and_source_bytes_changed_under_the_read_discard_it(
            self, tmp_path, monkeypatch):
        import scripts.build_stock_library as producer  # noqa: PLC0415

        plans, binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        plan_id = plans[0]["id"]
        plan_file = bp.PLANS_DIR / f"{plan_id}.json"
        snapshot = _plan_source_snapshot(tmp_path, binding)
        plan_bytes = plan_file.read_bytes()
        snapshot_bytes = snapshot.read_bytes()
        real_core = producer._today_native_source_candidates

        def racing_plan(raw_source, **kwargs):
            plan_file.write_bytes(plan_bytes + b" ")
            return real_core(raw_source, **kwargs)

        def racing_snapshot(raw_source, **kwargs):
            snapshot.write_bytes(snapshot_bytes + b" ")
            return real_core(raw_source, **kwargs)

        monkeypatch.setattr(producer, "_today_native_source_candidates", racing_plan)
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_SNAPSHOT_CHANGED"]
        plan_file.write_bytes(plan_bytes)
        monkeypatch.setattr(producer, "_today_native_source_candidates", racing_snapshot)
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["PLAN_SOURCE_SNAPSHOT_CHANGED"]
        snapshot.write_bytes(snapshot_bytes)

    def test_ucv_part_and_b1_head_races_are_typed(self, tmp_path, monkeypatch):
        from engine import us_context_vector as context_owner  # noqa: PLC0415

        plans, binding, path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        plan_id = plans[0]["id"]
        part = tmp_path / "data" / "us_prophet_rank" / "candidates" / "2026-07.parquet"
        real_rows = context_owner.read_today_candidate_source_rows
        reads: list = []

        def racing_part(root):
            reads.append(root)
            if len(reads) == 2:
                frame = pd.read_parquet(part)
                frame["extra_provenance"] = "changed"
                frame.to_parquet(part, index=False)
            return real_rows(root)

        monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", racing_part)
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["CANDIDATE_SNAPSHOT_CHANGED"]
        part.unlink()
        _plan_write_native_candidates(tmp_path, monkeypatch, path, ["AAA"])

        heads: list = []

        def racing_head(root):
            heads.append(root)
            if len(heads) == 2:
                snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
                relation = next(event for event in snapshot.generation.events
                                if event.get("source_event_id")
                                == f"candidate:{_PLAN_SESSION}:AAA:us_prophet_v3")
                corrections = tmp_path / "corrections.jsonl"
                corrections.write_text(canonical_json({
                    "event_type": "RETRACTED", "episode_id": relation["episode_id"],
                    "source_system": "candidate_governance",
                    "source_schema": "prophet_candidate_governance/v1",
                    "source_event_id": "candidate_retraction:2026-07-02:AAA:us_prophet_v3",
                    "occurred_at": "2026-07-02T22:07:00Z",
                    "known_at": "2026-07-02T22:07:00Z",
                    "source_receipt": "sha256:" + "b" * 64,
                    "correction_of": relation["event_id"],
                    "payload": {"reason": "duplicate candidate source row"},
                }) + "\n")
                _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                          recorded_at="2026-07-02T22:07:30Z",
                                          correction_path=corrections)
            return real_rows(root)

        monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", racing_head)
        assert bp.read_plan_candidate_source(plan_id)[
            "reason_codes"] == ["CANDIDATE_SNAPSHOT_CHANGED"]

    def test_a_genuine_terminal_episode_keeps_history_with_unavailable_action(
            self, tmp_path, monkeypatch):
        plans, _binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
        relation = next(event for event in snapshot.generation.events
                        if event.get("source_event_id")
                        == f"candidate:{_PLAN_SESSION}:AAA:us_prophet_v3")
        corrections = tmp_path / "corrections.jsonl"
        corrections.write_text(canonical_json({
            "event_type": "STATE_TRANSITIONED", "episode_id": relation["episode_id"],
            "source_system": "candidate_governance",
            "source_schema": "prophet_candidate_governance/v1",
            "source_event_id": "candidate_close:2026-07-02:AAA",
            "occurred_at": "2026-07-02T22:08:00Z", "known_at": "2026-07-02T22:08:00Z",
            "source_receipt": "sha256:" + "c" * 64, "payload": {
                "episode_state": "EXPIRED", "terminal_reason": "horizon reached"},
        }) + "\n")
        _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                  recorded_at="2026-07-02T22:08:30Z",
                                  correction_path=corrections)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        # The ORIGINAL relation stays exactly bound and inspectable.
        assert read["source_relation_status"] == "BOUND"
        assert read["source_relation_reasons"] == []
        assert read["clocks"]["native_known_at"] == relation["known_at"]
        assert read["clocks"]["native_recorded_at"] == relation["recorded_at"]
        # The actual native lifecycle is preserved, and no action is granted.
        assert read["episode_lifecycle"]["episode_state"] == "EXPIRED"
        assert read["episode_lifecycle"]["terminal_reason"] == "horizon reached"
        assert read["episode_lifecycle"]["superseded_by"] is None
        assert read["native_identity"] is None
        assert read["current_action_status"] == "UNAVAILABLE"
        assert read["current_action_reasons"] == [
            _PLAN_CURRENT_REASON, "CANDIDATE_EPISODE_TERMINAL"]

    def test_retraction_is_explicit_and_distinct_from_a_lifecycle_close(
            self, tmp_path, monkeypatch):
        plans, _binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
        relation = next(event for event in snapshot.generation.events
                        if event.get("source_event_id")
                        == f"candidate:{_PLAN_SESSION}:AAA:us_prophet_v3")
        corrections = tmp_path / "corrections.jsonl"
        corrections.write_text(canonical_json({
            "event_type": "RETRACTED", "episode_id": relation["episode_id"],
            "source_system": "candidate_governance",
            "source_schema": "prophet_candidate_governance/v1",
            "source_event_id": "candidate_retraction:2026-07-02:AAA:us_prophet_v3",
            "occurred_at": "2026-07-02T22:07:00Z", "known_at": "2026-07-02T22:07:00Z",
            "source_receipt": "sha256:" + "b" * 64,
            "correction_of": relation["event_id"],
            "payload": {"reason": "duplicate candidate source row"},
        }) + "\n")
        _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                  recorded_at="2026-07-02T22:07:30Z",
                                  correction_path=corrections)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["source_relation_status"] == "RETRACTED"
        assert read["source_relation_reasons"] == ["CANDIDATE_SOURCE_RETRACTED"]
        # A retraction is not a lifecycle close: no episode lifecycle is
        # implied, and the original relation's clocks remain reportable.
        assert read["episode_lifecycle"] is None
        assert read["clocks"]["native_known_at"] == relation["known_at"]
        assert read["current_action_reasons"] == [
            _PLAN_CURRENT_REASON, "CANDIDATE_SOURCE_RETRACTED"]

    def test_pins_are_equality_checks_without_retry_and_completion_is_stamped_once(
            self, tmp_path, monkeypatch):
        plans, _binding, _path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        plan_id = plans[0]["id"]
        plan_file = bp.PLANS_DIR / f"{plan_id}.json"
        plan_sha = "sha256:" + hashlib.sha256(plan_file.read_bytes()).hexdigest()
        snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
        generation_id = snapshot.generation_id
        assert bp.read_plan_candidate_source(
            plan_id, expected_plan_sha256=plan_sha,
            expected_candidate_generation_id=generation_id)["read_status"] == "AVAILABLE"
        mismatched = bp.read_plan_candidate_source(
            plan_id, expected_plan_sha256="sha256:" + "0" * 64)
        assert mismatched["read_status"] == "UNAVAILABLE"
        assert mismatched["reason_codes"] == ["PLAN_SHA256_MISMATCH"]
        assert mismatched["source_relation_status"] == "UNAVAILABLE"
        assert mismatched["current_action_reasons"] == [_PLAN_CURRENT_REASON]
        assert set(mismatched) == _PLAN_READ_KEYS
        assert bp.read_plan_candidate_source(
            plan_id, expected_candidate_generation_id="peg:" + "0" * 64)[
                "reason_codes"] == ["CANDIDATE_GENERATION_MISMATCH"]
        started = _RealDatetime.now(_timezone.utc)
        read = bp.read_plan_candidate_source(plan_id)
        completed = _RealDatetime.now(_timezone.utc)
        assert started <= _RealDatetime.fromisoformat(
            read["generated_at"].replace("Z", "+00:00")) <= completed


class TestPlanNativeSourceReadGuards:
    def test_original_row_identity_includes_id_direction_and_formation(self, tmp_path, monkeypatch):
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        for changes in (
            {"id": "OTHER-BULL-20260701"},
            {"id": "AAA-BEAR-20260701", "direction": "BEAR"},
            {"id": "AAA-BULL-20260630", "formation_date": "2026-06-30"},
        ):
            changed = {**plans[0], **changes}
            _plan_write(bp.PLANS_DIR / (changed["id"] + ".json"), changed)
            assert bp.read_plan_candidate_source(changed["id"])["reason_codes"] == [
                "PLAN_SOURCE_ROW_MISMATCH"]

    def test_every_owned_path_ancestor_must_be_real(self, tmp_path, monkeypatch):
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        for relative, reason in (("site", "PLAN_PATH_SYMLINK_UNAVAILABLE"),
                                 ("data", "PLAN_SOURCE_SNAPSHOT_SYMLINK_UNAVAILABLE")):
            path = tmp_path / relative
            moved = tmp_path / (relative + "_real")
            path.rename(moved)
            path.symlink_to(moved, target_is_directory=True)
            try:
                assert bp.read_plan_candidate_source(plans[0]["id"])["reason_codes"] == [reason]
            finally:
                path.unlink()
                moved.rename(path)

    def test_future_source_and_native_clocks_cannot_enter_the_read(self, tmp_path, monkeypatch):
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        class BeforeSource(_RealDatetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 7, 2, 20, 59, tzinfo=_timezone.utc)
        monkeypatch.setattr(bp, "datetime", BeforeSource)
        assert bp.read_plan_candidate_source(plans[0]["id"])["reason_codes"] == [
            "PLAN_SOURCE_CLOCK_UNAVAILABLE"]
        class BeforeGeneration(_RealDatetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 7, 2, 22, 5, 30, tzinfo=_timezone.utc)
        monkeypatch.setattr(bp, "datetime", BeforeGeneration)
        assert bp.read_plan_candidate_source(plans[0]["id"])["reason_codes"] == [
            "CANDIDATE_CLOCK_UNAVAILABLE"]

    def test_late_source_replacement_during_final_native_check_discards_read(self, tmp_path, monkeypatch):
        from engine import us_context_vector as context_owner
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        snapshot = _plan_source_snapshot(tmp_path, binding)
        real_rows = context_owner.read_today_candidate_source_rows
        calls = []
        def replace_at_recheck(root):
            calls.append(root)
            if len(calls) == 2:
                snapshot.write_bytes(snapshot.read_bytes() + b" ")
            return real_rows(root)
        monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", replace_at_recheck)
        assert bp.read_plan_candidate_source(plans[0]["id"])["reason_codes"] == [
            "PLAN_SOURCE_SNAPSHOT_CHANGED"]


    @pytest.mark.parametrize("change", ["add_part", "delete_part", "replace_plan_inode"])
    def test_inventory_and_path_identity_changes_are_discarded(self, tmp_path, monkeypatch, change):
        from scripts import build_stock_library as producer
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        part = tmp_path / "data/us_prophet_rank/candidates/2026-07.parquet"
        plan_file = bp.PLANS_DIR / (plans[0]["id"] + ".json")
        real_core = producer._today_native_source_candidates
        def raced(raw, **kwargs):
            result = real_core(raw, **kwargs)
            if change == "add_part":
                pd.DataFrame([{"stamp_date": "2026-06-01"}]).to_parquet(
                    part.parent / "2026-06.parquet", index=False)
            elif change == "delete_part":
                part.unlink()
            else:
                replacement = tmp_path / "same-plan-bytes.json"
                replacement.write_bytes(plan_file.read_bytes())
                replacement.replace(plan_file)
            return result
        monkeypatch.setattr(producer, "_today_native_source_candidates", raced)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["read_status"] == "UNAVAILABLE"
        assert read["native_identity"] is None and read["source_origin"] is None
        expected = {
            "add_part": "CANDIDATE_SNAPSHOT_CHANGED",
            "delete_part": "PLAN_SOURCE_RECHECK_UNAVAILABLE",
            "replace_plan_inode": "PLAN_PATH_CHANGED",
        }[change]
        assert read["reason_codes"] == [expected]

    @pytest.mark.parametrize("case", ["superseded", "suppressed"])
    def test_native_history_never_becomes_current_action(self, tmp_path, monkeypatch, case):
        from engine.us_candidate_episode import episode_id
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"],
            with_candidates=case != "suppressed")
        snapshot = load_candidate_episode_store_snapshot(_plan_episode_root(tmp_path))
        old = snapshot.generation.episodes[0]
        correction = None
        if case == "superseded":
            successor = episode_id(old["security_id"], "epoch_1", old["structural_anchor"], 1)
            correction = tmp_path / "corrections.jsonl"
            correction.write_text(canonical_json({
                "event_type": "IDENTITY_SUPERSEDED", "episode_id": old["episode_id"],
                "source_system": "stock_identity", "source_schema": "stock_identity.epoch/v1",
                "source_event_id": "identity:plan-fixture", "source_receipt": "sha256:" + "c" * 64,
                "occurred_at": "2026-07-02T22:08:00Z", "known_at": "2026-07-02T22:08:00Z",
                "payload": {"successor_episode_id": successor, "reason": "epoch detected"},
            }) + "\n")
        else:
            (tmp_path / "data/us_prophet_rank/episode_inputs/turn_watch/2026-07-02.json").unlink()
            aliases = tmp_path / "data/reference/vendor_aliases.parquet"
            pd.read_parquet(aliases).iloc[:0].to_parquet(aliases, index=False)
        _episode_writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                  recorded_at="2026-07-02T22:08:30Z", correction_path=correction)
        before = _plan_owner_state(tmp_path)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["read_status"] == "AVAILABLE"
        assert read["current_action_status"] == "UNAVAILABLE"
        assert read["current_action_reasons"][0] == _PLAN_CURRENT_REASON
        assert _plan_owner_state(tmp_path) == before
        if case == "superseded":
            assert read["source_relation_status"] == "BOUND"
            assert read["episode_lifecycle"]["superseded_by"] == successor
            assert read["episode_lifecycle"]["episode_id"] == old["episode_id"]
            assert "CANDIDATE_EPISODE_TERMINAL" in read["current_action_reasons"]
        else:
            assert read["source_relation_status"] == "SUPPRESSED"
            assert read["source_relation_reasons"] == ["CANDIDATE_SOURCE_SUPPRESSED"]


class TestPlanNativeSourceReadReviewDelta:

    def test_actual_b3_refusal_is_disclosed_without_losing_original_relation(self, tmp_path, monkeypatch):
        from engine import prophet_candidate_state as owner
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        def refuse_index(snapshot):
            raise owner.CandidateStateSourceError("native source index unavailable")
        monkeypatch.setattr(owner, "index_turn_watch_events", refuse_index)
        before = _plan_owner_state(tmp_path)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["read_status"] == "AVAILABLE"
        assert read["source_relation_status"] == "BOUND"
        assert read["source_binding"] == binding
        assert read["source_origin"]["source_event_id"] == "candidate:2026-07-02:AAA:us_prophet_v3"
        assert read["current_action_reasons"] == [
            "ASSESSMENT_NATIVE_OWNER_READ_UNAVAILABLE", _PLAN_CURRENT_REASON]
        assert read["native_identity"] is None
        assert _plan_owner_state(tmp_path) == before

    def test_cross_bound_real_b3_result_is_disclosed(self, tmp_path, monkeypatch):
        from engine import prophet_candidate_state as owner
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01"),
            _buy_row("BBB", priority=80.0, anchor="2026-07-01")], tickers=["AAA", "BBB"])
        real = owner.build_native_factual_assessment_result
        def swapped(snapshot, *, candidate_source_event_id, candidate_source_receipt):
            ticker = "BBB" if ":AAA:" in candidate_source_event_id else "AAA"
            other = "candidate:2026-07-02:" + ticker + ":us_prophet_v3"
            relation = next(e for e in snapshot.generation.events if e.get("source_event_id") == other)
            return real(snapshot, candidate_source_event_id=other,
                        candidate_source_receipt=relation["source_receipt"])
        monkeypatch.setattr(owner, "build_native_factual_assessment_result", swapped)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["source_relation_status"] == "BOUND"
        assert read["source_binding"] == binding
        assert read["current_action_reasons"] == [
            "ASSESSMENT_NATIVE_BINDING_UNAVAILABLE", _PLAN_CURRENT_REASON]
        assert read["native_identity"] is None

    def test_genuine_b3_after_completion_is_unavailable_and_completion_is_once(self, tmp_path, monkeypatch):
        from engine import prophet_candidate_state as owner
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        class ReadClock(_RealDatetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return cls(2026, 7, 3, 0, 0, cls.calls, tzinfo=_timezone.utc)
        monkeypatch.setattr(bp, "datetime", ReadClock)
        monkeypatch.setattr(owner, "_assembly_now", lambda: _RealDatetime(
            2026, 7, 3, 0, 0, 3, tzinfo=_timezone.utc))
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert ReadClock.calls == 2  # one request start, one completion
        assert read["generated_at"] == "2026-07-03T00:00:02Z"
        assert read["source_relation_status"] == "BOUND"
        assert read["clocks"]["source_session"] == "2026-07-02"
        assert read["current_action_reasons"] == [
            "ASSESSMENT_AFTER_READ_COMPLETION_UNAVAILABLE", _PLAN_CURRENT_REASON]
        assert read["native_identity"] is None

    def test_completion_guard_refuses_a_non_utc_core_clock(self, tmp_path, monkeypatch):
        # A defensive consumer witness over an intentionally corrupted core return,
        # not a claim that the genuine B3 owner emits this malformed clock.
        from scripts import build_stock_library as producer
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        real = producer._today_native_source_candidates
        def invalid_clock(raw, **kwargs):
            items, native = real(raw, **kwargs)
            candidate, assessment = native[0]
            assert assessment is not None
            native[0] = (candidate, {**assessment, "asof": "2026-07-03T01:00:00+01:00"})
            return items, native
        monkeypatch.setattr(producer, "_today_native_source_candidates", invalid_clock)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["current_action_reasons"] == [
            "ASSESSMENT_AFTER_READ_COMPLETION_UNAVAILABLE", _PLAN_CURRENT_REASON]
        assert read["native_identity"] is None

    def test_same_gzip_bytes_with_replaced_inode_are_discarded(self, tmp_path, monkeypatch):
        from scripts import build_stock_library as producer
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        snapshot = _plan_source_snapshot(tmp_path, binding)
        real = producer._today_native_source_candidates
        def replace_inode(raw, **kwargs):
            result = real(raw, **kwargs)
            replacement = tmp_path / "same-original-source.gz"
            replacement.write_bytes(snapshot.read_bytes())
            replacement.replace(snapshot)
            return result
        monkeypatch.setattr(producer, "_today_native_source_candidates", replace_inode)
        read = bp.read_plan_candidate_source(plans[0]["id"])
        assert read["read_status"] == "UNAVAILABLE"
        assert read["reason_codes"] == ["PLAN_SOURCE_PATH_CHANGED"]
        assert read["source_origin"] is None and read["native_identity"] is None


class TestPlanNativeSourceReadOwnership:
    def test_plan_module_cannot_acquire_or_steer_native_ledger(self):
        import ast
        import inspect
        from scripts import build_stock_library as producer
        text = Path(bp.__file__).read_text()
        for token in ("us_candidate_episode", "us_context_vector", "us_prophet_rank",
                      "_today_native_source_candidates", "attest_candidate_episode_store_bytes",
                      "load_candidate_episode_store_snapshot", "read_today_candidate_source_rows"):
            assert token not in text
        helper = producer._read_original_selection_native_relation
        assert tuple(inspect.signature(helper).parameters) == (
            "raw", "selection_index", "started_at", "expected_candidate_generation_id")
        native = inspect.getsource(helper)
        assert "build_prophet" not in native and "LEDGER_DIR" not in native
        tree = ast.parse(inspect.getsource(producer))
        assert not any(isinstance(n, ast.ImportFrom) and n.module == "scripts.build_prophet"
                       for n in ast.walk(tree))
        assert text.count("read_plan_candidate_source(") == 1

    def test_native_owner_uses_its_own_root_and_only_yields_immutable_facts(self, tmp_path, monkeypatch):
        from scripts import build_stock_library as producer
        from engine import us_context_vector as owner
        plans, binding, path = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        real = owner.read_today_candidate_source_rows
        roots = []
        def spy(root):
            roots.append(root)
            return real(root)
        monkeypatch.setattr(owner, "read_today_candidate_source_rows", spy)
        monkeypatch.setattr(bp, "LEDGER_DIR", tmp_path / "unrelated-plan-root")
        with producer._read_original_selection_native_relation(
                path.read_bytes(), selection_index=0, started_at="2026-07-04T00:00:00Z") as facts:
            assert set(facts) == {"status", "reason_codes", "native_identity", "episode_lifecycle",
                                  "native_clocks", "source_event_id", "source_receipt",
                                  "has_assessment", "assessment_asof", "assessment_codes"}
            assert facts["status"] == "AVAILABLE"
            assert set(facts["native_identity"]) == {
                "security_id", "episode_id", "candidate_generation_id", "market_session"}
            with pytest.raises(TypeError):
                facts["status"] = "invented"
            with pytest.raises(TypeError):
                facts["native_identity"]["security_id"] = "invented"
            assert roots == [tmp_path]
        assert roots == [tmp_path, tmp_path]

    def test_native_recheck_stays_between_both_plan_guard_groups(self, tmp_path, monkeypatch):
        from engine import us_context_vector as owner
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        plan_path = bp.PLANS_DIR / (plans[0]["id"] + ".json")
        source_path = _plan_source_snapshot(tmp_path, binding)
        original_read = Path.read_bytes
        original_rows = owner.read_today_candidate_source_rows
        events = []
        def read(path):
            if path == plan_path:
                events.append("plan")
            if path == source_path:
                events.append("gzip")
            return original_read(path)
        def rows(root):
            events.append("native")
            return original_rows(root)
        monkeypatch.setattr(Path, "read_bytes", read)
        monkeypatch.setattr(owner, "read_today_candidate_source_rows", rows)
        result = bp.read_plan_candidate_source(plans[0]["id"])
        assert result["read_status"] == "AVAILABLE"
        assert events == ["plan", "gzip", "native", "plan", "gzip", "native", "plan", "gzip"]

    def test_plan_cannot_redirect_native_owner_with_a_changed_plan_root(self, tmp_path, monkeypatch):
        from scripts import build_stock_library as producer
        plans, binding, _ = _plan_fixture(tmp_path, monkeypatch, [
            _buy_row("AAA", priority=90.0, anchor="2026-07-01")], tickers=["AAA"])
        # A different installed native owner has no ledger. The Plan's fully
        # populated data root cannot substitute for that independent owner.
        monkeypatch.setattr(producer, "__file__", str(tmp_path / "other-native-owner/scripts/build_stock_library.py"))
        result = bp.read_plan_candidate_source(plans[0]["id"])
        assert result["read_status"] == "UNAVAILABLE"
        assert result["reason_codes"] == ["CANDIDATE_SNAPSHOT_UNAVAILABLE"]
        assert result["native_identity"] is None


# Nightly publication reads the canonical ledger a second time after advancing it.
# These tests live with the existing PlanNativeSourceRead producer contract
# because that CI gate owns native source-read safety and runs this named subset
# on every relevant code change (no new unregistered test suite).
class TestPlanNativeSourceReadSameBuildLedger:
    @staticmethod
    def _open(plan_id="A-20261023"):
        return {
            "id": plan_id,
            "closed": False,
            "phase": "triggered",
            "clock_age_days": 8,
            "pulse": "8d · triggered",
            "pulse_zh": "8天 · 已触发",
            "what_to_do_now": ["Buy above trigger"],
            "what_to_do_now_zh": ["突破触发价买入"],
            "recommended_action": "buy",
            "state": {"recommended_action": "buy", "phase": "triggered"},
            "targets": [120.0, 140.0],
            "profit_plan": [{
                "level": 120.0, "label": "T1",
                "action": "Scale out 40%", "status": "ACTIVE"
            }],
            "profit_plan_zh": [{
                "level": 120.0, "label": "T1",
                "action": "减仓 40%", "status": "ACTIVE"
            }],
        }

    def test_new_close_withholds_all_live_action_in_both_languages(self):
        entry = self._open()
        bp._reconcile_same_build_closures([entry], {"A-20261023": "INVALIDATED"})
        assert entry["closed"] is True
        en, zh = bp._plan_pulse(
            8, "triggered", None, closed=True, outcome="INVALIDATED"
        )
        assert (entry["pulse"], entry["pulse_zh"]) == (en, zh)
        now_en, now_zh = bp._closed_state_lines("INVALIDATED")
        assert (entry["what_to_do_now"], entry["what_to_do_now_zh"]) == (
            now_en, now_zh
        )
        assert "Buy above" not in repr(entry)
        assert entry["recommended_action"] is None
        assert entry["state"]["recommended_action"] is None
        assert entry["profit_plan"] == []
        assert entry["profit_plan_zh"] == []
        # Historical price levels remain available; no grading is rewritten.
        assert entry["targets"] == [120.0, 140.0]

    def test_open_unchanged_and_previously_closed_actions_withheld(self):
        opened = self._open("OPEN")
        closed = self._open("ALREADY")
        closed.update(
            closed=True,
            pulse="existing historical pulse",
            what_to_do_now=bp._closed_state_lines("T1_HIT")[0],
            what_to_do_now_zh=bp._closed_state_lines("T1_HIT")[1],
        )
        opened_snapshot = json.loads(json.dumps(opened))
        bp._reconcile_same_build_closures(
            [opened, closed], {"ALREADY": "T1_HIT"}
        )
        assert opened == opened_snapshot
        assert closed["pulse"] == "existing historical pulse"
        assert closed["closed"] is True
        assert closed["what_to_do_now"] == bp._closed_state_lines("T1_HIT")[0]
        assert closed["profit_plan"] == []
        assert closed["profit_plan_zh"] == []
        assert closed["recommended_action"] is None
        assert closed["state"]["recommended_action"] is None
        assert closed["targets"] == [120.0, 140.0]

    def test_missing_id_and_unnamed_outcome_withhold_action(self):
        missing = self._open("")
        fresh = self._open("NEW")
        bp._reconcile_same_build_closures(
            [missing, fresh], {"": "EXPIRED", "NEW": ""}
        )
        assert missing["closed"] is False
        assert fresh["closed"] is True
        assert fresh["what_to_do_now"] == bp._closed_state_lines("")[0]
        assert fresh["what_to_do_now_zh"] == bp._closed_state_lines("")[1]
        assert fresh["recommended_action"] is None
        assert fresh["profit_plan"] == []

    def test_no_entry_is_closed_without_suggesting_position_exits(self):
        plan = self._open("NEVER-ENTERED")
        bp._reconcile_same_build_closures([plan], {"NEVER-ENTERED": "NO_ENTRY"})
        assert plan["closed"] is True
        assert plan["profit_plan"] == []
        assert plan["profit_plan_zh"] == []
        assert plan["what_to_do_now"] == bp._closed_state_lines("NO_ENTRY")[0]
        assert plan["recommended_action"] is None


class TestClosedStateSidecarConsistency:
    """A closed index row and its persisted state cannot disagree on action."""

    @staticmethod
    def _state(path: Path, plan_id: str) -> dict:
        value = {
            "schema": "prophet.management_state/v1",
            "id": plan_id,
            "asof": "2026-10-23",
            "phase": "triggered_pre_t1",
            "recommended_action": "buy",
            "human_state": "Advancing Cleanly",
            "components": {"progress": 45.0},
            "geometry": {"dist_to_t1_r": 0.55},
            "reliability": {"recommended_action": "display — unconfirmed"},
            "_mfe": 9.0,
        }
        path.write_text(json.dumps(value), encoding="utf-8")
        return value

    def test_nightly_new_close_reconciles_disk_sidecar_and_index(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(bp, "STATES_DIR", tmp_path)
        plan_id = "A-20261023"
        path = tmp_path / f"{plan_id}.json"
        previous = self._state(path, plan_id)
        entry = {
            "id": plan_id, "closed": False, "clock_age_days": 8,
            "phase": "triggered", "recommended_action": "buy",
            "state": {"recommended_action": "buy"},
            "profit_plan": [{"status": "ACTIVE"}],
            "profit_plan_zh": [{"status": "ACTIVE"}],
        }
        closes = {plan_id: "INVALIDATED"}
        bp._reconcile_same_build_closures([entry], closes)
        bp._reconcile_closed_state_sidecars([entry], closes)
        updated = json.loads(path.read_text(encoding="utf-8"))
        assert entry["closed"] is True
        assert entry["recommended_action"] is None
        assert updated["closed"] is True
        assert updated["outcome"] == "INVALIDATED"
        assert updated["recommended_action"] is None
        assert updated["human_state"] == "Closed"
        assert "withheld" in updated["reliability"]["recommended_action"]
        assert updated["components"] == previous["components"]
        assert updated["geometry"] == previous["geometry"]
        assert updated["_mfe"] == previous["_mfe"]
        # Idempotent second projection: no gratuitous rewrite or new authority.
        once = path.read_bytes()
        bp._reconcile_closed_state_sidecars([entry], closes)
        assert path.read_bytes() == once

    def test_open_plan_sidecar_unchanged_and_no_entry_closes_without_action(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(bp, "STATES_DIR", tmp_path)
        open_path = tmp_path / "OPEN.json"
        original = self._state(open_path, "OPEN")
        noentry_path = tmp_path / "NOENTRY.json"
        self._state(noentry_path, "NOENTRY")
        entries = [
            {"id": "OPEN", "closed": False},
            {"id": "NOENTRY", "closed": False},
        ]
        closes = {"NOENTRY": "NO_ENTRY"}
        bp._reconcile_same_build_closures(entries, closes)
        bp._reconcile_closed_state_sidecars(entries, closes)
        assert json.loads(open_path.read_text(encoding="utf-8")) == original
        noentry = json.loads(noentry_path.read_text(encoding="utf-8"))
        assert noentry["closed"] and noentry["outcome"] == "NO_ENTRY"
        assert noentry["recommended_action"] is None
        assert noentry["human_state"] == "Closed"

    def test_already_closed_and_missing_sidecars_degrade_without_minting(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(bp, "STATES_DIR", tmp_path)
        closed_path = tmp_path / "ALREADY.json"
        self._state(closed_path, "ALREADY")
        entries = [
            {"id": "ALREADY", "closed": True},
            {"id": "MISSING", "closed": True},
            {"id": "../TRAVERSAL", "closed": True},
        ]
        closes = {
            "ALREADY": "T1_HIT", "MISSING": "EXPIRED",
            "../TRAVERSAL": "EXPIRED",
        }
        bp._reconcile_closed_state_sidecars(entries, closes)
        state = json.loads(closed_path.read_text(encoding="utf-8"))
        assert state["recommended_action"] is None
        assert state["closed"] is True and state["outcome"] == "T1_HIT"
        assert sorted(p.name for p in tmp_path.glob("*.json")) == ["ALREADY.json"]
