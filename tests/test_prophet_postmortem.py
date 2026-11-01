"""Prophet Learning Loop §2 — postmortem taxonomy + aggregation (gates G1, G2).

Two halves, and they check different things:

  * TestLoserCohortFixture runs the real classifier over the COMMITTED ledgers and
    pins gate G1: every name on the operator's 2026-07-31 worst-rows list must come
    back with a classification, entry-time context and visible-at-entry flags, and the
    IPGP double-admission must be flagged. A fixture test is the only thing that can
    catch a rule that is individually correct and collectively finds nothing.
  * The rule tests build synthetic rows so each threshold is exercised on BOTH sides
    and, critically, so an absent input is proven to produce a NULL rather than a
    silent negative — the failure mode that would have made every rate in the artifact
    look better than the data supports.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import postmortem as pm  # noqa: E402
from scripts import prophet_postmortem as ppm  # noqa: E402


# ===========================================================================
# helpers — the smallest context/row that exercises one rule at a time
# ===========================================================================
def _ctx(**over) -> dict:
    """A neutral entry context: every leg present, none of them firing.

    Present-but-negative is the right baseline. A context of Nones would make every
    rule NULL and the tests would pass while proving nothing.
    """
    base = {
        "sector": "Industrials",
        "basket_asof": "2026-07-01",
        "themes": [{"id": "defense", "reco": "hold", "label": "neutral",
                    "score": 50.0, "bull_days": 10.0, "rank": 5.0}],
        "spotlight_theme_id": "defense",
        "sector_basket": {"id": "us_sector_industrials", "reco": "hold",
                          "label": "neutral", "score": 50.0, "bull_days": 10.0,
                          "rank": 5.0},
        "spotlight": {"dir": "neutral", "z": 0.1, "sector_stage": "improving",
                      "sector_extended": False, "sector_pctile_252d": 60.0},
        "extension": {"overextended": False, "entry_tier": "Prime entry",
                      "ext_risk": 0.0, "ext_z": -0.2, "price": 100.0,
                      "chase_above": 110.0, "above_chase": False,
                      "off_high_pct": -8.0},
        "conviction": {"band": "neutral", "score": 50.0, "composite_z": 0.0,
                       "alpha": 0.1, "tier": None, "tier_cascade": None,
                       "urgency": "now", "state": "FRESH BUY"},
        "entry_plan": {"status": "buy_soon", "stop": 90.0, "atr_pct": 2.0,
                       "invalidation": 92.0, "hold_state": "intact"},
        "days_since_signal": 1.0,
        "board_tenure_days": 0.0,
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


def _blank_ctx() -> dict:
    """A context with NO entry state recorded — the pre-archive history's shape."""
    return {
        "sector": "Industrials", "basket_asof": None, "themes": [],
        "spotlight_theme_id": None, "sector_basket": None,
        "spotlight": {"dir": None, "z": None, "sector_stage": None,
                      "sector_extended": None, "sector_pctile_252d": None},
        "extension": {"overextended": None, "entry_tier": None, "ext_risk": None,
                      "ext_z": None, "price": None, "chase_above": None,
                      "above_chase": False, "off_high_pct": None},
        "conviction": {}, "entry_plan": {"status": None, "stop": None},
        "days_since_signal": None, "board_tenure_days": None,
    }


def _path(**over) -> dict:
    base = {"n_bars": 10, "worst_session_pct": -1.5, "worst_session_date": "2026-07-06",
            "stop_level": 90.0, "stop_cross_date": None, "stop_cross_px": None}
    base.update(over)
    return base


def _names(labels) -> set[str]:
    return {lb["label"] for lb in labels}


def _trigger(labels, name) -> dict:
    return next(lb for lb in labels if lb["label"] == name)["trigger"]


def _visible(labels, name) -> bool:
    return next(lb for lb in labels if lb["label"] == name)["visible_at_entry"]


def _null_reasons(nulls, name) -> list[str]:
    return sorted(n["reason"] for n in nulls if n["label"] == name)


def _row(**over) -> dict:
    base = {"ticker": "AAA", "entry_date": "2026-07-01", "maturity": "matured",
            "outcome_pct": -10.0, "excess_pct": -9.0, "cohort": "loser",
            "labels": [], "labels_null": []}
    base.update(over)
    if "cohort" not in over:
        base["cohort"] = pm.cohort_of(base["outcome_pct"], base["excess_pct"])
    return base


def _labelled(name: str, visible: bool = False, **trigger) -> dict:
    return {"label": name, "visible_at_entry": visible, "trigger": dict(trigger)}


# ===========================================================================
# 0. THRESHOLD PINS — literals, never the constants they guard
# ===========================================================================
class TestThresholdsArePinnedAsLiterals:
    """Every threshold written out by hand.

    The rest of this file reads `pm.GAP_PCT` and friends so each boundary test stays
    honest when a threshold legitimately moves. That is the right shape for a boundary
    test and the WRONG shape for the only record of what the numbers are: with nothing
    but symbolic references, editing `GAP_PCT = -8.0` to `-5.0` re-points every test at
    the new value and the whole suite goes green on a silently redefined taxonomy — the
    artifact, the report and the masterplan would then be describing a rule no test
    disagrees with. These literals are that disagreement. A threshold change must land
    HERE, in a diff a reviewer reads, alongside the doc and masterplan edits.
    """

    def test_gap_event_threshold(self):
        assert pm.GAP_PCT == -8.0

    def test_extension_risk_threshold(self):
        assert pm.EXT_RISK_MIN == 0.10

    def test_readmission_window_in_sessions(self):
        assert pm.READMIT_MAX_SESSIONS == 10

    def test_cohort_and_remaining_thresholds(self):
        assert pm.LOSER_ABS_PCT == -8.0
        assert pm.LOSER_EXCESS_PCT == -5.0
        assert pm.WINNER_ABS_PCT == 8.0
        assert pm.BETA_SHARE_MAX == 0.40
        assert pm.READMIT_LOSS_PCT == -8.0

    def test_the_thresholds_the_artifact_publishes_match_the_module(self):
        # The artifact prints its own thresholds block; a reader re-deriving a label by
        # hand uses THOSE numbers. They must not be able to drift from the ones the
        # classifier actually applied.
        th = pm.aggregate([])["thresholds"]
        assert th["gap_pct"] == -8.0
        assert th["ext_risk_min"] == 0.10
        assert th["readmit_max_sessions"] == 10
        assert th["loser_abs_pct"] == -8.0
        assert th["loser_excess_pct"] == -5.0
        assert th["winner_abs_pct"] == 8.0
        assert th["beta_share_max"] == 0.40
        assert th["readmit_loss_pct"] == -8.0


# ===========================================================================
# 1. cohort gates
# ===========================================================================
class TestCohortGates:
    def test_absolute_leg(self):
        assert pm.cohort_of(-8.0, 0.0) == "loser"
        assert pm.cohort_of(-7.99, -1.0) == "neutral"

    def test_excess_leg_alone_makes_a_loser(self):
        # -6% in a +2% tape is a loss to the desk even though the absolute leg misses.
        assert pm.cohort_of(-4.0, -5.0) == "loser"

    def test_winner_gate_mirrors_the_absolute_loser_gate(self):
        assert pm.cohort_of(8.0, 0.0) == "winner"
        assert pm.cohort_of(7.99, 0.0) == "neutral"
        assert pm.WINNER_ABS_PCT == abs(pm.LOSER_ABS_PCT)

    def test_no_numbers_is_unscored_not_neutral(self):
        assert pm.cohort_of(None, None) == "unscored"

    def test_a_profitable_pick_is_a_WINNER_however_fast_the_tape_ran(self):
        # PRECEDENCE PIN. +9% against a +14.5% tape is -5.5% excess, which trips the
        # loser gate's excess leg. Testing the loser legs first booked that pick as a
        # LOSS — and, worse, deleted it from the winners-forfeited column, so every veto
        # in `veto_cost` looked cheaper than it is. The masterplan's winner gate is
        # absolute (">= +8%"), so the absolute return decides first.
        assert pm.cohort_of(9.0, -5.5) == "winner"
        assert pm.cohort_of(8.0, -20.0) == "winner"
        # ...and the excess leg keeps its real job: a name that LOST while the tape rose.
        assert pm.cohort_of(-4.0, -5.5) == "loser"
        assert pm.cohort_of(7.99, -5.5) == "loser"

    def test_a_winner_by_absolute_return_never_lands_in_the_loser_cohort(self):
        # The two gates cannot both be satisfied by an absolute return, so the only
        # overlap is via the excess leg — pinned above. This walks the boundary.
        for excess in (-50.0, -5.0, -4.99, 0.0, 5.0):
            assert pm.cohort_of(8.0, excess) == "winner"


# ===========================================================================
# 1b. path_tails — the gates the PATH crossed that the VERDICT does not show
# ===========================================================================
class TestPathTails:
    """The round-trip record.

    A verdict is one number off one bar. FN 2026-07-21 fell 19.3% and closed +1.66%:
    `neutral` is the right verdict and a useless description of the episode. These
    flags carry the other half.
    """

    def test_a_neutral_verdict_that_crossed_the_loser_gate_is_recorded(self):
        # The FN shape, in miniature.
        assert pm.path_tails("neutral", -19.31, 3.38) == ["loser"]

    def test_a_neutral_verdict_that_crossed_the_winner_gate_is_recorded(self):
        assert pm.path_tails("neutral", -2.0, 12.0) == ["winner"]

    def test_an_episode_can_cross_both_gates(self):
        assert pm.path_tails("neutral", -12.0, 14.0) == ["loser", "winner"]

    def test_an_uneventful_episode_records_nothing(self):
        assert pm.path_tails("neutral", -3.0, 4.0) == []

    def test_a_tail_verdict_never_reports_its_own_tail(self):
        # A loser that bottomed at -20% did not "round trip" into the loser gate — it
        # LIVES there, and its own table already prints the MAE. Only the gate it did
        # NOT finish in is news.
        assert pm.path_tails("loser", -20.0, 1.0) == []
        assert pm.path_tails("winner", -1.0, 25.0) == []
        # ...but the crossing a tail verdict hides IS reported: a winner that was 12%
        # under water first is the exact case a stop would have destroyed.
        assert pm.path_tails("winner", -12.0, 25.0) == ["loser"]
        assert pm.path_tails("loser", -20.0, 9.0) == ["winner"]

    def test_the_gates_are_inclusive_and_walk_the_boundary(self):
        assert pm.path_tails("neutral", -8.0, 0.0) == ["loser"]
        assert pm.path_tails("neutral", -7.99, 0.0) == []
        assert pm.path_tails("neutral", 0.0, 8.0) == ["winner"]
        assert pm.path_tails("neutral", 0.0, 7.99) == []

    def test_a_missing_excursion_is_not_a_crossing(self):
        # An unscored episode has no path. Absence must never read as a gate crossing.
        assert pm.path_tails("unscored", None, None) == []
        assert pm.path_tails("neutral", None, 12.0) == ["winner"]
        assert pm.path_tails("neutral", -12.0, None) == ["loser"]


# ===========================================================================
# 2. sector_headwind
# ===========================================================================
class TestSectorHeadwind:
    @pytest.mark.parametrize("reco", ["avoid", "trim"])
    def test_theme_reco_fires_and_is_visible_at_entry(self, reco):
        ctx = _ctx(themes=[{"id": "defense", "reco": reco, "label": "fading"}])
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        assert "sector_headwind" in _names(labels)
        assert _visible(labels, "sector_headwind") is True
        legs = _trigger(labels, "sector_headwind")["legs"]
        assert {"leg": "theme_reco", "theme_id": "defense", "reco": reco,
                "label": "fading"} in legs

    def test_sector_basket_reco_fires_when_the_name_is_in_no_theme(self):
        ctx = _ctx(themes=[], sector_basket={"id": "us_sector_tech", "reco": "avoid",
                                             "label": "deteriorating"})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        legs = _trigger(labels, "sector_headwind")["legs"]
        assert [lg["leg"] for lg in legs] == ["sector_basket_reco"]

    def test_lagging_stage_and_out_of_play_each_fire(self):
        ctx = _ctx(spotlight={"sector_stage": "lagging", "dir": "out_of_play"})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        legs = {lg["leg"] for lg in _trigger(labels, "sector_headwind")["legs"]}
        assert legs == {"sector_stage", "spotlight_dir"}

    def test_weakening_stage_does_not_fire(self):
        # The RRG leading-but-rolling quadrant. Folding it in would push the label's
        # base rate past half the board and make it uninformative — a documented choice.
        ctx = _ctx(spotlight={"sector_stage": "weakening"})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        assert "sector_headwind" not in _names(labels)
        assert "weakening" not in pm.HEADWIND_STAGES

    def test_hold_and_accumulate_do_not_fire(self):
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                    ctx=_ctx(), path=_path())
        assert "sector_headwind" not in _names(labels)
        assert _null_reasons(nulls, "sector_headwind") == []   # decided, not skipped

    def test_no_theme_state_at_all_is_NULL_not_a_clean_bill(self):
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                    ctx=_blank_ctx(), path=_path())
        assert "sector_headwind" not in _names(labels)
        assert _null_reasons(nulls, "sector_headwind") == [
            "no_theme_state_or_spotlight_at_entry"]


# ===========================================================================
# 3. bought_extended
# ===========================================================================
class TestBoughtExtended:
    def test_overextended_flag(self):
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                ctx=_ctx(extension={"overextended": True}), path=_path())
        assert _visible(labels, "bought_extended") is True
        assert {"leg": "alignment_overextended", "value": True} in \
            _trigger(labels, "bought_extended")["legs"]

    def test_entry_tier_prefix(self):
        ctx = _ctx(extension={"entry_tier": "Extended — wait"})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        assert "bought_extended" in _names(labels)

    def test_ext_risk_threshold_is_inclusive_at_the_boundary(self):
        below = _ctx(extension={"ext_risk": pm.EXT_RISK_MIN - 0.001})
        at = _ctx(extension={"ext_risk": pm.EXT_RISK_MIN})
        assert "bought_extended" not in _names(
            pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=below, path=_path())[0])
        assert "bought_extended" in _names(
            pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=at, path=_path())[0])

    def test_fill_above_the_chase_level(self):
        ctx = _ctx(extension={"price": 120.0, "chase_above": 110.0, "above_chase": True})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=ctx, path=_path())
        trig = _trigger(labels, "bought_extended")["legs"]
        assert {"leg": "above_chase_level", "price": 120.0, "chase_above": 110.0} in trig

    def test_absent_extension_state_is_NULL_not_negative(self):
        # `above_chase` is False both when the fill was cheap AND when price is missing,
        # so it must never stand in as evidence on its own.
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                    ctx=_blank_ctx(), path=_path())
        assert "bought_extended" not in _names(labels)
        assert _null_reasons(nulls, "bought_extended") == ["no_entry_state_recorded"]


# ===========================================================================
# 4. thesis_break
# ===========================================================================
class TestThesisBreak:
    def test_hold_state_history_wins_over_the_stop_cross(self):
        labels, _ = pm.classify(
            outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
            path=_path(stop_cross_date="2026-07-09", stop_cross_px=88.0),
            hold_broken={"board_date": "2026-07-07", "date": "2026-07-07"})
        trig = _trigger(labels, "thesis_break")
        assert trig["source"] == "hold_state_history"
        assert trig["date"] == "2026-07-07"

    def test_stop_cross_fallback_records_the_level_it_crossed(self):
        labels, _ = pm.classify(
            outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
            path=_path(stop_cross_date="2026-07-09", stop_cross_px=88.0))
        trig = _trigger(labels, "thesis_break")
        assert (trig["source"], trig["stop_level"], trig["close"]) == \
            ("stop_cross", 90.0, 88.0)
        assert _visible(labels, "thesis_break") is False

    def test_no_price_path_is_NULL(self):
        _labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                     ctx=_ctx(), path=None)
        assert "no_price_path" in _null_reasons(nulls, "thesis_break")

    def test_no_stop_recorded_is_NULL(self):
        _labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                     path=_path(stop_level=None))
        assert _null_reasons(nulls, "thesis_break") == ["no_stop_level_recorded"]

    def test_stop_present_and_uncrossed_is_a_decided_negative(self):
        _labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                     ctx=_ctx(), path=_path())
        assert _null_reasons(nulls, "thesis_break") == []


# ===========================================================================
# 5. gap_event
# ===========================================================================
class TestGapEvent:
    def test_threshold_is_inclusive_and_records_the_date(self):
        labels, _ = pm.classify(
            outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
            path=_path(worst_session_pct=pm.GAP_PCT, worst_session_date="2026-07-08"))
        trig = _trigger(labels, "gap_event")
        assert (trig["pct"], trig["date"], trig["basis"]) == \
            (pm.GAP_PCT, "2026-07-08", "close_to_close")

    def test_just_inside_the_threshold_does_not_fire(self):
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(worst_session_pct=pm.GAP_PCT + 0.01))
        assert "gap_event" not in _names(labels)

    def test_no_price_path_is_NULL(self):
        _labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                     ctx=_ctx(), path=None)
        assert _null_reasons(nulls, "gap_event") == ["no_price_path"]

    def test_the_caller_owns_the_missing_path_reason(self):
        # A too-young episode is not an unpriceable one. Collapsing the two once made
        # the artifact report 67 unpriceable episodes where 12 were unpriceable.
        _labels, nulls = pm.classify(outcome_pct=None, excess_pct=None, ctx=_ctx(),
                                     path=None,
                                     path_missing_reason="fill_not_yet_printed")
        assert _null_reasons(nulls, "gap_event") == ["fill_not_yet_printed"]
        assert _null_reasons(nulls, "thesis_break") == ["fill_not_yet_printed"]


# ===========================================================================
# 6. market_beta
# ===========================================================================
class TestMarketBeta:
    def test_fires_when_most_of_the_loss_was_the_tape(self):
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-2.0,
                                ctx=_ctx(), path=_path())
        trig = _trigger(labels, "market_beta")
        assert trig["excess_share_of_loss"] == 0.2

    def test_does_not_fire_when_the_pick_carried_the_loss(self):
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                ctx=_ctx(), path=_path())
        assert "market_beta" not in _names(labels)

    def test_boundary_is_strict(self):
        at = pm.classify(outcome_pct=-10.0, excess_pct=-(pm.BETA_SHARE_MAX * 10.0),
                         ctx=_ctx(), path=_path())[0]
        assert "market_beta" not in _names(at)

    def test_missing_benchmark_leg_is_NULL(self):
        _labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=None,
                                     ctx=_ctx(), path=_path())
        assert _null_reasons(nulls, "market_beta") == ["no_benchmark_excess"]

    def test_a_winner_is_never_asked(self):
        _labels, nulls = pm.classify(outcome_pct=9.0, excess_pct=None,
                                     ctx=_ctx(), path=_path())
        assert _null_reasons(nulls, "market_beta") == []


# ===========================================================================
# 7. re_admission
# ===========================================================================
class TestReAdmission:
    def test_open_drawdown_leg_is_visible_at_entry(self):
        prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                 "sessions_since_prior_exit": 2, "mark_at_readmit_pct": -9.0}
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(), prior=prior)
        assert _visible(labels, "re_admission") is True
        assert _trigger(labels, "re_admission")["leg"] == "open_drawdown_at_readmit"

    def test_prior_episode_loss_leg_is_NOT_visible_at_entry(self):
        # The IPGP shape: the first position was still GREEN on the night the board
        # re-admitted the name, and only rolled over afterwards. Real pattern, but the
        # engine could not have known — and the row says so.
        prior = {"entry_date": "2026-07-10", "outcome_pct": -14.35,
                 "sessions_since_prior_exit": 1, "mark_at_readmit_pct": 3.04}
        labels, _ = pm.classify(outcome_pct=-17.9, excess_pct=-16.7, ctx=_ctx(),
                                path=_path(), prior=prior)
        assert "re_admission" in _names(labels)
        assert _visible(labels, "re_admission") is False
        trig = _trigger(labels, "re_admission")
        assert trig["leg"] == "prior_episode_loss"
        assert trig["mark_at_readmit_pct"] == 3.04

    def test_outside_the_session_window_does_not_fire(self):
        prior = {"entry_date": "2026-05-01", "outcome_pct": -20.0,
                 "sessions_since_prior_exit": pm.READMIT_MAX_SESSIONS + 1,
                 "mark_at_readmit_pct": -20.0}
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(), prior=prior)
        assert "re_admission" not in _names(labels)

    def test_a_profitable_prior_episode_does_not_fire(self):
        prior = {"entry_date": "2026-07-01", "outcome_pct": 5.0,
                 "sessions_since_prior_exit": 1, "mark_at_readmit_pct": 4.0}
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(), prior=prior)
        assert "re_admission" not in _names(labels)

    def test_a_BIG_profitable_prior_episode_does_not_fire(self):
        """SIGN GUARD. The two legs read `<= -8%`; both thresholds are signed.

        A prior that made +12% has |12| >= |−8|, so any rewrite that reaches for an
        absolute value — `abs(prior_out) >= abs(READMIT_LOSS_PCT)`, the natural typo
        when the constant is negative — turns "re-bought a name that had just LOST
        money" into "re-bought a name that had just MOVED", flags winners, and quietly
        fills the winners-forfeited column that
        `test_the_readmission_veto_forfeits_exactly_zero_winners` pins at zero. The
        +5% prior above cannot catch that (|5| < 8); this one can.
        """
        prior = {"entry_date": "2026-07-01", "outcome_pct": 12.0,
                 "sessions_since_prior_exit": 1, "mark_at_readmit_pct": 11.0,
                 "prior_matured": True}
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                    path=_path(), prior=prior)
        assert "re_admission" not in _names(labels)
        assert _null_reasons(nulls, "re_admission") == []   # decided, not skipped

    def test_no_prior_episode_does_not_fire_and_is_a_decided_negative(self):
        # `prior=None` means the caller's scan found no prior run in the window. That is
        # a decided negative and the row must stay in every denominator — nulling it
        # would shrink the universe by every name that has only ever been bought once.
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                    path=_path(), prior=None)
        assert "re_admission" not in _names(labels)
        assert _null_reasons(nulls, "re_admission") == []

    def test_the_window_boundary_is_inclusive_at_ten_sessions(self):
        # Literal 10/11, not pm.READMIT_MAX_SESSIONS: see TestThresholdsArePinned.
        def _fire(gap):
            prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                     "sessions_since_prior_exit": gap, "mark_at_readmit_pct": -9.0}
            return "re_admission" in _names(pm.classify(
                outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                path=_path(), prior=prior)[0])
        assert _fire(10) is True
        assert _fire(11) is False

    def test_an_unpriceable_prior_episode_is_NULL_on_the_label_and_BOTH_legs(self):
        # A previous run that cannot be priced is not evidence that the name came back
        # clean. It nulls the label AND both leg keys, because the leg keys are the
        # denominators `veto_cost` costs each variant over — leaving them in would let
        # the buildable row's "0 of N" count rows it never got to look at.
        _labels, nulls = pm.classify(
            outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(), path=_path(),
            prior={"undecidable": "prior_episode_not_scoreable",
                   "n_priors_in_window": 1, "n_priors_unscoreable": 1})
        assert _null_reasons(nulls, "re_admission") == ["prior_episode_not_scoreable"]
        assert _null_reasons(nulls, pm.READMIT_NULL_OPEN_DRAWDOWN) == \
            ["prior_episode_not_scoreable"]
        assert _null_reasons(nulls, pm.READMIT_NULL_PRIOR_LOSS) == \
            ["prior_episode_not_scoreable"]

    def test_a_missing_mark_nulls_ONLY_the_buildable_leg(self):
        # The prior resolved to a loss (hindsight leg decidable) but there is no mark at
        # the re-admission, so the buildable leg had no input at all. Nulling both would
        # throw away a real finding; nulling neither would let the buildable variant
        # report a zero it never measured.
        prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                 "sessions_since_prior_exit": 2, "mark_at_readmit_pct": None,
                 "prior_matured": True}
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                    path=_path(), prior=prior)
        assert _trigger(labels, "re_admission")["leg"] == pm.READMIT_LEG_PRIOR_LOSS
        assert _null_reasons(nulls, pm.READMIT_NULL_OPEN_DRAWDOWN) == \
            ["no_mark_at_readmit"]
        assert _null_reasons(nulls, pm.READMIT_NULL_PRIOR_LOSS) == []
        assert _null_reasons(nulls, "re_admission") == []

    def test_an_unmeasurable_gap_is_NULL_not_out_of_window(self):
        prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                 "sessions_since_prior_exit": None, "mark_at_readmit_pct": -9.0}
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                    path=_path(), prior=prior)
        assert "re_admission" not in _names(labels)
        assert _null_reasons(nulls, "re_admission") == ["prior_gap_not_measurable"]

    def test_the_trigger_says_whether_the_prior_had_MATURED(self):
        # An unmatured prior's `outcome_pct` is a MARK — outcome-conditioned, and not
        # the same evidence as a resolved loss. The row has to say which it was.
        prior = {"entry_date": "2026-07-10", "outcome_pct": -14.0, "prior_matured": False,
                 "sessions_since_prior_exit": 1, "mark_at_readmit_pct": 3.0,
                 "n_priors_in_window": 2, "selected_by": pm.READMIT_LEG_PRIOR_LOSS}
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(), prior=prior)
        trig = _trigger(labels, "re_admission")
        assert trig["prior_matured"] is False
        assert trig["n_priors_in_window"] == 2
        assert trig["selected_by"] == pm.READMIT_LEG_PRIOR_LOSS

    def test_a_caller_that_says_nothing_about_maturity_gets_a_NULL_not_a_False(self):
        prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                 "sessions_since_prior_exit": 2, "mark_at_readmit_pct": -9.0}
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                                path=_path(), prior=prior)
        assert _trigger(labels, "re_admission")["prior_matured"] is None


# ===========================================================================
# 7b. re_admission is HINDSIGHT wearing a visible-at-entry badge (M7)
# ===========================================================================
class TestReAdmissionIsNotAVisibleAtEntryLabel:
    def test_the_label_is_not_in_the_visible_at_entry_list(self):
        """The headline is carried by a leg that cannot be read at entry.

        `re_admission`'s +79.08pp counterfactual (2026-07-31 artifact) comes entirely
        from `prior_episode_loss`, which needs the PRIOR episode's resolved outcome — a
        number that does not exist on the night the board re-admits the name (the IPGP
        case was +3.04% green at re-admission). Listing the label as visible-at-entry
        published that hindsight figure under a buildable badge.
        """
        assert "re_admission" not in pm.VISIBLE_AT_ENTRY_LABELS
        assert pm.VISIBLE_AT_ENTRY_LABELS == ("sector_headwind", "bought_extended")

    def test_the_row_level_flag_stays_leg_specific(self):
        # The label-level list is the weaker claim. A row that fired on the open-drawdown
        # leg really WAS visible at entry, and must keep saying so.
        open_leg = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                    "sessions_since_prior_exit": 2, "mark_at_readmit_pct": -9.0}
        hindsight = {"entry_date": "2026-07-10", "outcome_pct": -14.35,
                     "sessions_since_prior_exit": 1, "mark_at_readmit_pct": 3.04}
        a, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                           path=_path(), prior=open_leg)
        b, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0, ctx=_ctx(),
                           path=_path(), prior=hindsight)
        assert _visible(a, "re_admission") is True
        assert _visible(b, "re_admission") is False

    def test_the_aggregation_reports_the_label_as_not_visible_at_entry(self):
        rows = [_row(ticker="A", outcome_pct=-10.0,
                     labels=[_labelled("re_admission", False,
                                       leg=pm.READMIT_LEG_PRIOR_LOSS)])]
        agg = pm.aggregate(rows)
        freq = {f["label"]: f for f in agg["label_frequency"]}
        assert freq["re_admission"]["visible_at_entry"] is False
        assert freq["sector_headwind"]["visible_at_entry"] is True
        tax = {t["label"]: t for t in agg["taxonomy"]}
        assert tax["re_admission"]["visible_at_entry"] is False
        # ...and the reader is told WHY, not just "no": one leg is buildable.
        legs = {lg["leg"]: lg for lg in tax["re_admission"]["legs"]}
        assert legs[pm.READMIT_LEG_OPEN_DRAWDOWN]["visible_at_entry"] is True
        assert legs[pm.READMIT_LEG_PRIOR_LOSS]["visible_at_entry"] is False

    def test_veto_cost_splits_the_label_into_one_row_per_leg(self):
        rows = [
            _row(ticker="H", outcome_pct=-20.0,
                 labels=[_labelled("re_admission", False,
                                   leg=pm.READMIT_LEG_PRIOR_LOSS)]),
            _row(ticker="N", outcome_pct=1.0, labels=[]),
        ]
        veto = {v["key"]: v for v in pm.aggregate(rows)["veto_cost"]}
        assert set(veto) == {"sector_headwind", "bought_extended",
                             "re_admission:open_drawdown_at_readmit",
                             "re_admission:prior_episode_loss"}
        build = veto["re_admission:open_drawdown_at_readmit"]
        hind = veto["re_admission:prior_episode_loss"]
        assert (build["variant"], build["visible_at_entry"]) == ("buildable", True)
        assert (hind["variant"], hind["visible_at_entry"]) == \
            ("hindsight_upper_bound", False)
        # The whole counterfactual sits on the hindsight leg...
        assert (hind["n_flagged"], hind["loss_avoided_pct"]) == (1, 20.0)
        # ...and the buildable row is PRINTED with its zero, never dropped.
        assert (build["n_flagged"], build["loss_avoided_pct"]) == (0, 0.0)
        assert build["n_universe"] == 2

    def test_a_leg_null_shrinks_only_ITS_variants_universe(self):
        rows = [
            _row(ticker="H", outcome_pct=-20.0,
                 labels=[_labelled("re_admission", False,
                                   leg=pm.READMIT_LEG_PRIOR_LOSS)],
                 labels_null=[{"label": pm.READMIT_NULL_OPEN_DRAWDOWN,
                               "reason": "no_mark_at_readmit"}]),
            _row(ticker="N", outcome_pct=1.0, labels=[]),
        ]
        veto = {v["key"]: v for v in pm.aggregate(rows)["veto_cost"]}
        assert veto["re_admission:open_drawdown_at_readmit"]["n_universe"] == 1
        assert veto["re_admission:open_drawdown_at_readmit"]["n_null_disclosed"] == 1
        assert veto["re_admission:prior_episode_loss"]["n_universe"] == 2

    def test_a_row_with_no_recorded_leg_is_never_credited_to_one(self):
        # `_labelled` with no trigger is the shape a hand-written row takes. It must not
        # be guessed into either leg — a veto variant may only count triggers it can see.
        rows = [_row(ticker="H", outcome_pct=-20.0, labels=[_labelled("re_admission")])]
        veto = {v["key"]: v for v in pm.aggregate(rows)["veto_cost"]}
        assert veto["re_admission:open_drawdown_at_readmit"]["n_flagged"] == 0
        assert veto["re_admission:prior_episode_loss"]["n_flagged"] == 0


# ===========================================================================
# 8. multi-label + the residual
# ===========================================================================
class TestMultiLabelAndResidual:
    def test_one_episode_carries_every_label_that_fired(self):
        ctx = _ctx(themes=[{"id": "defense", "reco": "avoid", "label": "fading"}],
                   extension={"overextended": True})
        prior = {"entry_date": "2026-07-01", "outcome_pct": -12.0,
                 "sessions_since_prior_exit": 1, "mark_at_readmit_pct": -9.0}
        labels, _ = pm.classify(
            outcome_pct=-10.0, excess_pct=-2.0, ctx=ctx,
            path=_path(worst_session_pct=-9.0, worst_session_date="2026-07-08",
                       stop_cross_date="2026-07-09", stop_cross_px=88.0),
            prior=prior)
        assert _names(labels) == {"sector_headwind", "bought_extended", "thesis_break",
                                  "gap_event", "market_beta", "re_admission"}

    def test_labels_come_back_in_taxonomy_order(self):
        ctx = _ctx(themes=[{"id": "defense", "reco": "avoid"}],
                   extension={"overextended": True})
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-2.0, ctx=ctx,
                                path=_path(worst_session_pct=-9.0))
        order = [pm.TAXONOMY.index(lb["label"]) for lb in labels]
        assert order == sorted(order)

    def test_idiosyncratic_when_nothing_else_fired(self):
        labels, _ = pm.classify(outcome_pct=-10.0, excess_pct=-9.0,
                                ctx=_ctx(), path=_path())
        assert _names(labels) == {"idiosyncratic"}
        assert _trigger(labels, "idiosyncratic")["fully_checked"] is True

    def test_idiosyncratic_still_fires_with_unchecked_legs_but_says_so(self):
        # An episode with no labels at all would read as a classifier bug; hiding the
        # residual would hide the rows the taxonomy fails to explain. It fires, and the
        # trigger names the legs that were never decidable.
        labels, nulls = pm.classify(outcome_pct=-10.0, excess_pct=None,
                                    ctx=_blank_ctx(), path=None)
        assert "idiosyncratic" in _names(labels)
        trig = _trigger(labels, "idiosyncratic")
        assert trig["fully_checked"] is False
        assert set(trig["unchecked"]) == {"sector_headwind", "bought_extended",
                                          "thesis_break", "gap_event", "market_beta"}
        assert trig["checked"] == ["re_admission"]
        assert len(nulls) >= 5

    def test_every_label_carries_bilingual_copy(self):
        for name in pm.TAXONOMY:
            assert pm.TAXONOMY_COPY[name]["en"]
            assert pm.TAXONOMY_COPY[name]["zh"]
            assert pm.TAXONOMY_COPY[name]["en"] != pm.TAXONOMY_COPY[name]["zh"]


# ===========================================================================
# 9. path_features
# ===========================================================================
class TestPathFeatures:
    @staticmethod
    def _series(vals):
        idx = pd.bdate_range("2026-07-01", periods=len(vals))
        return pd.Series(vals, index=idx, dtype=float)

    def test_worst_session_and_stop_cross(self):
        s = self._series([100, 99, 90, 92, 88])
        out = pm.path_features(s, s.index[0], 4, 91.0)
        assert out["worst_session_pct"] == pytest.approx(-9.0909, abs=1e-3)
        assert out["worst_session_date"] == str(s.index[2].date())
        assert out["stop_cross_date"] == str(s.index[2].date())

    def test_window_stops_at_n_bars(self):
        s = self._series([100, 101, 102, 103, 50])
        out = pm.path_features(s, s.index[0], 3, None)
        assert out["n_bars"] == 3
        assert out["worst_session_pct"] > 0      # the -51% bar is outside the window

    def test_fill_bar_itself_is_never_a_stop_cross(self):
        s = self._series([80, 100, 101])
        out = pm.path_features(s, s.index[0], 2, 90.0)
        assert out["stop_cross_date"] is None    # the 80 IS the fill, not a break

    def test_absent_series_returns_none_not_a_dict_of_nulls(self):
        assert pm.path_features(None, "2026-07-01", 10, 90.0) is None
        assert pm.path_features(pd.Series(dtype=float), "2026-07-01", 10, 90.0) is None

    def test_fill_after_the_series_ends_returns_none(self):
        s = self._series([100, 101])
        assert pm.path_features(s, "2027-01-01", 10, None) is None


# ===========================================================================
# 10. aggregation
# ===========================================================================
class TestAggregate:
    def test_in_flight_rows_enter_no_rate(self):
        rows = [
            _row(ticker="A", outcome_pct=-20.0, excess_pct=-19.0,
                 labels=[_labelled("gap_event")]),
            _row(ticker="B", maturity="in_flight", outcome_pct=-30.0, excess_pct=None,
                 labels=[_labelled("gap_event")]),
        ]
        agg = pm.aggregate(rows)
        assert agg["n_matured"] == 1 and agg["n_in_flight"] == 1
        assert agg["cohorts"]["n_losers"] == 1              # the in-flight row excluded
        gap = next(f for f in agg["label_frequency"] if f["label"] == "gap_event")
        assert gap["n_losers"] == 1
        assert agg["in_flight"]["n_losers_marked"] == 1     # still visible, separately

    def test_veto_cost_counts_winners_forfeited_as_a_first_class_column(self):
        rows = [
            _row(ticker="L", outcome_pct=-10.0, excess_pct=-10.0,
                 labels=[_labelled("sector_headwind", True)]),
            _row(ticker="W", outcome_pct=12.0, excess_pct=12.0,
                 labels=[_labelled("sector_headwind", True)]),
            _row(ticker="C", outcome_pct=1.0, excess_pct=1.0, labels=[]),
        ]
        v = next(x for x in pm.aggregate(rows)["veto_cost"]
                 if x["label"] == "sector_headwind")
        assert v["n_losers_avoided"] == 1 and v["loss_avoided_pct"] == 10.0
        assert v["n_winners_forfeited"] == 1 and v["winners_forfeited_pct"] == 12.0
        assert v["net_pct_if_vetoed"] == -2.0     # the veto LOSES money here

    def test_veto_universe_excludes_rows_the_label_could_not_decide(self):
        rows = [
            _row(ticker="L", outcome_pct=-10.0, labels=[_labelled("sector_headwind", True)]),
            _row(ticker="U", outcome_pct=1.0, labels=[],
                 labels_null=[{"label": "sector_headwind",
                               "reason": "no_theme_state_or_spotlight_at_entry"}]),
        ]
        agg = pm.aggregate(rows)
        v = next(x for x in agg["veto_cost"] if x["label"] == "sector_headwind")
        assert v["n_universe"] == 1 and v["n_matured_total"] == 2
        assert v["flagged_share_of_universe_pct"] == 100.0
        f = next(x for x in agg["label_frequency"] if x["label"] == "sector_headwind")
        assert f["n_null_disclosed"] == 1 and f["n_evaluated"] == 1

    def test_undecidable_rows_never_land_in_the_clean_split(self):
        rows = [
            _row(ticker="H", outcome_pct=-10.0, labels=[_labelled("sector_headwind", True)]),
            _row(ticker="N", outcome_pct=2.0, labels=[]),
            _row(ticker="U", outcome_pct=2.0, labels=[],
                 labels_null=[{"label": "sector_headwind", "reason": "x"}]),
        ]
        splits = pm.aggregate(rows)["cohort_splits"]
        assert splits["headwind_at_entry"]["n"] == 1
        assert splits["no_headwind_at_entry"]["n"] == 1     # NOT 2

    def test_systemic_read_counts_dates_not_rows(self):
        rows = [_row(ticker=f"T{i}", entry_date="2026-07-01", outcome_pct=-10.0,
                     labels=[_labelled("gap_event")]) for i in range(9)]
        rows += [_row(ticker="X", entry_date="2026-07-02", outcome_pct=-10.0, labels=[])]
        sysd = next(x for x in pm.aggregate(rows)["systemic_vs_anomalous"]
                    if x["label"] == "gap_event")
        assert sysd["n_dates"] == 1 and sysd["read"] == "anomalous"

    def test_repeat_offenders_are_sorted_by_total_loss(self):
        rows = [
            _row(ticker="A", entry_date="2026-07-01", outcome_pct=-9.0),
            _row(ticker="A", entry_date="2026-07-08", outcome_pct=-9.0),
            _row(ticker="B", entry_date="2026-07-01", outcome_pct=-20.0),
            _row(ticker="B", entry_date="2026-07-08", outcome_pct=-20.0),
        ]
        rep = pm.aggregate(rows)["repeat_offenders"]
        assert [r["ticker"] for r in rep] == ["B", "A"]

    def test_loss_contribution_uses_ONE_denominator_and_prints_its_coverage(self):
        """The loss-contribution column is comparable down the table, or it is noise.

        Numerator and denominator used to come from different populations' worth of
        thinking: the share column beside it is over the DECIDABLE losers while the
        contribution is over the whole loser book, so a label evaluable on a third of
        the book and one with full reach printed two different 100%s in one column. The
        contribution keeps the whole-book denominator — the only one that is the same on
        every row — and the per-label reach is disclosed separately as coverage.
        """
        rows = [
            # a big loser this label could NOT be decided on
            _row(ticker="U", outcome_pct=-30.0, labels=[],
                 labels_null=[{"label": "sector_headwind", "reason": "x"}]),
            _row(ticker="H", outcome_pct=-10.0,
                 labels=[_labelled("sector_headwind", True)]),
            _row(ticker="C", outcome_pct=-10.0, labels=[]),
        ]
        f = next(x for x in pm.aggregate(rows)["label_frequency"]
                 if x["label"] == "sector_headwind")
        assert f["loss_contribution_pct"] == 20.0            # 10pp of the 50pp book
        assert f["loss_contribution_denominator_pp"] == 50.0
        assert f["loss_contribution_basis"] == "all matured losers' summed absolute loss"
        # ...and the reach that number was earned on, so 20% is never read as full reach
        assert (f["n_losers_evaluated"], f["n_losers_total"]) == (2, 3)
        assert f["loser_coverage_pct"] == 66.7
        assert f["decidable_loss_share_pct"] == 40.0         # 20pp of the 50pp book

    def test_every_label_shares_the_same_contribution_denominator(self):
        rows = [
            _row(ticker="A", outcome_pct=-20.0, labels=[_labelled("gap_event")],
                 labels_null=[{"label": "sector_headwind", "reason": "x"}]),
            _row(ticker="B", outcome_pct=-10.0,
                 labels=[_labelled("sector_headwind", True)]),
        ]
        agg = pm.aggregate(rows)
        denoms = {f["loss_contribution_denominator_pp"] for f in agg["label_frequency"]}
        assert denoms == {30.0} == {agg["cohorts"]["total_loser_loss_pct"]}

    def test_market_beta_diagnostics_print_the_distribution_behind_a_zero(self):
        rows = [_row(ticker="A", outcome_pct=-10.0, excess_pct=-9.0),
                _row(ticker="B", outcome_pct=-20.0, excess_pct=-15.0)]
        d = pm.aggregate(rows)["diagnostics"]["market_beta_excess_share"]
        assert d["n"] == 2 and d["min"] == 0.75 and d["max"] == 0.9

    def test_aggregate_is_order_independent(self):
        rows = [
            _row(ticker="A", entry_date="2026-07-01", outcome_pct=-10.0,
                 labels=[_labelled("gap_event")]),
            _row(ticker="B", entry_date="2026-07-02", outcome_pct=11.0, labels=[]),
            _row(ticker="C", entry_date="2026-07-03", outcome_pct=-9.0,
                 labels=[_labelled("sector_headwind", True)]),
        ]
        assert pm.aggregate(rows) == pm.aggregate(list(reversed(copy.deepcopy(rows))))


# ===========================================================================
# 10b. the prior-episode scan (scripts/prophet_postmortem.prior_episodes)
# ===========================================================================
CAL = pd.bdate_range("2026-06-01", periods=60)


def _series(dips: dict[str, float] | None = None) -> pd.Series:
    s = pd.Series(100.0, index=CAL, dtype=float)
    for day, px in (dips or {}).items():
        s.loc[pd.Timestamp(day)] = px
    return s


def _item(ticker: str, entry: str, exit_: str | None, *, pnl: float | None = None,
          matured: bool = True, series: "pd.Series | None" = None) -> dict:
    sc = None if pnl is None else {"pnl": pnl, "mark": pnl, "matured": matured,
                                   "entry": 100.0}
    return {"ep": {"ticker": ticker, "entry_date": entry, "exit_date": exit_},
            "sc": sc, "series": _series() if series is None and pnl is not None
            else series}


class TestPriorEpisodeScan:
    def test_it_scans_EVERY_prior_in_the_window_not_just_the_last_one(self):
        """`items[i-1]` answered a different question than the label prints.

        A name re-admitted twice inside a fortnight was compared only against its most
        recent run, so a qualifying loss one run further back — still inside the same
        10-session window — was invisible to the label. Here the OLDER prior is the
        loser and the newer one is flat; the scan has to find the older one.
        """
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=-12.0),
            _item("AAA", "2026-06-18", "2026-06-19", pnl=1.0),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert prior["entry_date"] == "2026-06-15"
        assert prior["outcome_pct"] == -12.0
        assert prior["selected_by"] == pm.READMIT_LEG_PRIOR_LOSS
        assert prior["n_priors_in_window"] == 2
        assert prior["prior_matured"] is True

    def test_the_buildable_leg_outranks_the_hindsight_leg_in_selection(self):
        # One prior was already under water on the night of the re-admission; the other
        # only resolved into a loss later. Report the one somebody could have acted on.
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=-20.0),
            _item("AAA", "2026-06-18", "2026-06-19", pnl=-9.0,
                  series=_series({"2026-06-22": 88.0})),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert prior["selected_by"] == pm.READMIT_LEG_OPEN_DRAWDOWN
        assert prior["entry_date"] == "2026-06-18"
        assert prior["mark_at_readmit_pct"] == pytest.approx(-12.0)

    def test_an_unpriceable_prior_makes_the_row_UNDECIDABLE_not_clean(self):
        # The prior run has no series at all, so nobody can say what it did. Reporting
        # "no re-admission" here is a silent zero — the exact failure this scan owns.
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=None),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert prior["undecidable"] == "prior_episode_not_scoreable"
        assert prior["n_priors_unscoreable"] == 1

    def test_a_qualifying_scored_prior_outranks_an_unpriceable_sibling(self):
        # An unpriceable prior only makes the row undecidable when nothing else fired:
        # once a leg has fired, the verdict is the same whatever the sibling did.
        scored = [
            _item("AAA", "2026-06-15", "2026-06-16", pnl=None),
            _item("AAA", "2026-06-17", "2026-06-19", pnl=-12.0),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert "undecidable" not in prior
        assert prior["entry_date"] == "2026-06-17"
        assert prior["n_priors_unscoreable"] == 1

    def test_a_prior_outside_the_window_leaves_no_comparison_at_all(self):
        scored = [
            _item("AAA", "2026-06-01", "2026-06-02", pnl=-30.0),
            _item("AAA", "2026-06-29", None, pnl=-5.0),
        ]
        assert ("AAA", "2026-06-29") not in ppm.prior_episodes(scored, CAL)

    def test_a_non_qualifying_prior_is_still_reported_as_the_comparison_made(self):
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=-2.0),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert prior["selected_by"] == "nearest_prior_no_leg_fired"
        assert prior["outcome_pct"] == -2.0

    def test_an_unmatured_prior_is_carried_with_its_maturity_flag(self):
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=-12.0, matured=False),
            _item("AAA", "2026-06-22", None, pnl=-5.0),
        ]
        prior = ppm.prior_episodes(scored, CAL)[("AAA", "2026-06-22")]
        assert prior["prior_matured"] is False

    def test_tickers_never_borrow_each_others_history(self):
        scored = [
            _item("AAA", "2026-06-15", "2026-06-17", pnl=-30.0),
            _item("BBB", "2026-06-22", None, pnl=-5.0),
        ]
        assert ppm.prior_episodes(scored, CAL) == {}


# ===========================================================================
# 11. GATE G1 — the operator's loser cohort, over the COMMITTED ledgers
# ===========================================================================
#: The 2026-07-31 track-record worst rows (masterplan §0 G1). Dates are the BOARD log
#: dates; the episode's entry_date is matched with a one-session tolerance because a
#: name can be re-admitted on the adjacent night.
#:
#: SPLIT BY WHETHER THE VERDICT HAD LANDED ON 2026-07-31. The operator's list is the
#: worst rows on the board THAT NIGHT — and a board shows MARKS. Six of these had already
#: run their full H=10 and were reporting a realised loss. The other five were still
#: open: their horizon ended on 08-03/08-05, so the number that put them on the list was
#: an outcome-conditioned mark, not a result.
#:
#: Pinning all eleven as `cohort == "loser"` therefore pinned a mark as a verdict, and it
#: detonated the night the last of those horizons completed. `data: daily collection
#: 2026-08-06` (361136284f2) added the 08-03/04/05 bars; FN 07-21, marked -15.24% on
#: 07-31 with a -19.31% MAE, closed its tenth bar at +1.66%. `neutral` is the correct
#: verdict and the fixture said it was false. The other four stayed down and merely
#: hid the same defect.
#:
#: So the two blocks are asserted on what is actually true of each, and neither
#: assertion can drift again: a matured episode's cohort is fixed forever, and MAE is
#: fixed once the window closes.
RESOLVED_BY_ASOF = [
    ("IPGP", "2026-07-15"), ("STAA", "2026-07-15"), ("PSKY", "2026-07-01"),
    ("CDNS", "2026-07-09"), ("IPGP", "2026-07-10"), ("HL", "2026-07-01"),
]
#: Still open on 2026-07-31 — on the list by their mark. The tape decided them later.
OPEN_AT_ASOF = [
    ("OLN", "2026-07-21"), ("AMKR", "2026-07-17"), ("FN", "2026-07-21"),
    ("UNIT", "2026-07-21"), ("BG", "2026-07-17"),
]
#: The operator's full cohort. Everything the gate demands of the ENGINE — found,
#: classified, labelled, full entry context, named in the report — is demanded of all
#: eleven. Only the cohort LABEL is split, because only the label was ever in doubt.
LOSER_COHORT = RESOLVED_BY_ASOF + OPEN_AT_ASOF


@pytest.fixture(scope="module")
def artifact():
    """One real run over the committed ledgers (~5s, git archaeology included)."""
    return ppm.build_rows(ROOT)


def _match(doc, ticker, board_date):
    """The episode for (ticker, board_date), tolerating one session of drift."""
    dates = sorted({r["entry_date"] for r in doc["episodes"]})
    if board_date in dates:
        window = {board_date}
    else:
        window = set()
    i = dates.index(board_date) if board_date in dates else None
    if i is not None:
        window |= {dates[j] for j in (i - 1, i + 1) if 0 <= j < len(dates)}
    hits = [r for r in doc["episodes"]
            if r["ticker"] == ticker and r["entry_date"] in window]
    return hits[0] if hits else None


class TestLoserCohortFixture:
    def test_the_run_produces_a_populated_artifact(self, artifact):
        assert artifact["schema"] == ppm.SCHEMA
        assert artifact["method"]["llm_used"] is False
        assert artifact["summary"]["n_matured"] > 100
        assert artifact["coverage"]["basket_revisions"] > 0, \
            "git archaeology returned no baskets revisions — theme context would be empty"

    def test_every_cohort_name_is_classified(self, artifact):
        missing, unlabelled = [], []
        for ticker, date in LOSER_COHORT:
            row = _match(artifact, ticker, date)
            if row is None:
                missing.append(f"{ticker}@{date}")
                continue
            if not row["labels"]:
                unlabelled.append(f"{ticker}@{date}")
        assert not missing, f"cohort names absent from the ledgers: {missing}"
        assert not unlabelled, f"cohort names with no classification: {unlabelled}"

    def test_every_resolved_name_is_in_the_loser_cohort(self, artifact):
        """The six whose H=10 verdict had landed by 2026-07-31. Permanent: a matured
        episode's outcome is read off a bar that has already printed, so this can never
        drift the way the pooled version did."""
        not_losers = [
            f"{t}@{d} -> {(_match(artifact, t, d) or {}).get('cohort')}"
            for t, d in RESOLVED_BY_ASOF
            if (_match(artifact, t, d) or {}).get("cohort") != "loser"
        ]
        assert not not_losers, not_losers

    def test_every_resolved_name_really_had_resolved(self, artifact):
        """Guards the SPLIT itself: if a name in the resolved block were still open, the
        block above would be pinning a mark again under a name that says otherwise."""
        for ticker, date in RESOLVED_BY_ASOF:
            row = _match(artifact, ticker, date)
            assert row["maturity"] == "matured", f"{ticker}@{date} is {row['maturity']}"
            assert row["outcome_pct"] == row["pnl_pct"], \
                f"{ticker}@{date} outcome is a mark, not a realised pnl"

    def test_every_open_name_crossed_the_loser_gate_on_its_path(self, artifact):
        """The five that were open on 2026-07-31 earned their place on the operator's
        list — by the PATH, which is the claim the board was actually making.

        This is the assertion the old pooled one should always have been. It is what put
        them on a worst-rows list on a night they had not finished, it is true of all
        five, and MAE is frozen once the window closes — so it cannot rot.
        """
        for ticker, date in OPEN_AT_ASOF:
            row = _match(artifact, ticker, date)
            assert row["mae_pct"] is not None, f"{ticker}@{date} has no MAE"
            assert row["mae_pct"] <= pm.LOSER_ABS_PCT, (
                f"{ticker}@{date} never crossed the {pm.LOSER_ABS_PCT}% loser gate "
                f"(MAE {row['mae_pct']}%) — it does not belong in this block")

    def test_the_recovered_loser_is_carried_as_a_round_trip_not_a_loss(self, artifact):
        """FN 2026-07-21 by name — the episode that broke the pooled gate.

        Down 19.31% at its worst and marked -15.24% on the as-of date, it closed its
        tenth bar at +1.66%. Every clause below is a fact about the tape, and together
        they pin the whole failure mode: the verdict is honest, the drawdown is not
        thrown away with it, and the row survives serialization intact.
        """
        row = _match(artifact, "FN", "2026-07-21")
        assert row["maturity"] == "matured"
        assert row["outcome_pct"] > 0, "FN's tenth bar closed green"
        assert row["cohort"] == "neutral", \
            "a +1.66% forced-horizon verdict is not a loss, whatever the mark once said"
        assert row["mae_pct"] <= pm.LOSER_ABS_PCT
        assert "loser" in row["path_tails"], \
            "the drawdown must survive on the row — it is the exit-policy evidence"
        assert not row["entry_context"].get("compact"), \
            "the round-trip rows are exactly the ones whose context must NOT be trimmed"

    def test_the_round_trip_set_is_not_silently_empty(self, artifact):
        """A `path_tails` that stopped populating would compact these rows away again and
        every assertion above would still pass on a re-derived empty set."""
        rt = artifact["summary"]["round_trips"]
        assert rt["n_crossed_loser_gate"] > 0 and rt["n_crossed_winner_gate"] > 0
        assert rt["n"] == (rt["n_crossed_loser_gate"] + rt["n_crossed_winner_gate"]
                           - rt["n_crossed_both"])
        assert rt["n"] == len([r for r in artifact["episodes"] if r["path_tails"]])

    def test_a_round_trip_row_keeps_its_full_context_but_a_flat_one_does_not(
            self, artifact):
        """The retention rule, both directions — a rule that kept EVERYTHING would pass
        the round-trip half while quietly abandoning the compaction it replaced."""
        kept = [r for r in artifact["episodes"]
                if r["cohort"] not in ("loser", "winner") and r["path_tails"]]
        trimmed = [r for r in artifact["episodes"]
                   if r["cohort"] not in ("loser", "winner") and not r["path_tails"]]
        assert kept and trimmed, "one side of the retention rule is unexercised"
        assert not any(r["entry_context"].get("compact") for r in kept)
        assert all(r["entry_context"].get("compact") for r in trimmed)

    def test_every_cohort_name_carries_entry_time_context(self, artifact):
        for ticker, date in LOSER_COHORT:
            ctx = _match(artifact, ticker, date)["entry_context"]
            assert ctx["sector"], f"{ticker}@{date} has no sector at entry"
            # Both tails keep the FULL context, never the compact form.
            assert not ctx.get("compact"), f"{ticker}@{date} was trimmed"
            assert "spotlight" in ctx and "extension" in ctx and "entry_plan" in ctx

    def test_every_label_carries_a_visible_at_entry_flag_and_triggers(self, artifact):
        for ticker, date in LOSER_COHORT:
            for lb in _match(artifact, ticker, date)["labels"]:
                assert isinstance(lb["visible_at_entry"], bool)
                assert lb["label"] in pm.TAXONOMY
                assert lb["trigger"] != {} or lb["label"] == "idiosyncratic"

    def test_IPGP_double_admission_is_flagged(self, artifact):
        """G1's named pin: same ticker re-admitted <= 10 sessions after a >= 8% loss."""
        row = _match(artifact, "IPGP", "2026-07-15")
        labels = {lb["label"]: lb for lb in row["labels"]}
        assert "re_admission" in labels, \
            f"IPGP 07-15 not flagged as a re-admission (labels: {sorted(labels)})"
        trig = labels["re_admission"]["trigger"]
        assert trig["prior_entry_date"] == "2026-07-10"
        assert trig["prior_outcome_pct"] <= pm.READMIT_LOSS_PCT
        assert trig["sessions_since_prior_exit"] <= pm.READMIT_MAX_SESSIONS
        # The honest half: on the night it was re-admitted the first position was still
        # GREEN, so this pattern was NOT visible at entry — and the row says so.
        assert labels["re_admission"]["visible_at_entry"] is False
        assert trig["mark_at_readmit_pct"] > 0

    def test_the_aggregation_carries_the_symmetric_winners_cost(self, artifact):
        for v in artifact["summary"]["veto_cost"]:
            assert "n_winners_forfeited" in v and "winners_forfeited_pct" in v
            assert v["net_pct_if_vetoed"] == pytest.approx(
                v["loss_avoided_pct"] - v["winners_forfeited_pct"], abs=0.01)
        headwind = next(v for v in artifact["summary"]["veto_cost"]
                        if v["label"] == "sector_headwind")
        assert headwind["n_winners_forfeited"] > 0, \
            "a headwind veto that forfeits no winners would be a free lunch — check it"

    def test_the_readmission_veto_forfeits_exactly_zero_winners(self, artifact):
        """A LITERAL zero, on real data, on both legs.

        `re_admission` is the one veto row in the artifact whose winners-forfeited
        column is empty, and an empty symmetric column is the shape of a free lunch —
        so it is the one that has to be pinned rather than admired. The zero is only
        earned because both legs read a SIGNED threshold (`<= -8%`): swap either for an
        absolute value and the label starts flagging names re-bought after a big WIN,
        winners land in the flagged set, and this assertion goes red. Pinned as `== 0`,
        never `is not None`, so the mutation cannot pass by producing some other number.
        """
        readmit = [v for v in artifact["summary"]["veto_cost"]
                   if v["label"] == "re_admission"]
        assert len(readmit) == 2, "both legs must be costed, including an empty one"
        for v in readmit:
            assert v["n_winners_forfeited"] == 0, (
                f"{v['key']} forfeits winners — the label is firing on names that MADE "
                f"money, which means a threshold lost its sign")
            assert v["winners_forfeited_pct"] == 0.0
            assert v["net_pct_if_vetoed"] == v["loss_avoided_pct"]

    def test_the_buildable_readmission_trigger_fires_zero_times_and_prints_it(self, artifact):
        # The finding, not an omission: on this window the ONLY buildable version of the
        # re-admission rule — the earlier position already 8% under water on the night
        # the name came back — never fires. The row exists anyway, with its zero.
        veto = {v["key"]: v for v in artifact["summary"]["veto_cost"]}
        build = veto["re_admission:open_drawdown_at_readmit"]
        hind = veto["re_admission:prior_episode_loss"]
        assert build["variant"] == "buildable" and build["visible_at_entry"] is True
        assert build["n_flagged"] == 0
        assert build["loss_avoided_pct"] == 0.0
        assert build["n_universe"] > 0, "a zero over an empty universe is not a finding"
        # ...and every percentage point of the headline sits on the hindsight leg.
        assert hind["variant"] == "hindsight_upper_bound"
        assert hind["visible_at_entry"] is False
        assert hind["n_flagged"] > 0 and hind["loss_avoided_pct"] > 0

    def test_no_readmission_fire_claims_to_have_been_visible_at_entry(self, artifact):
        # Today every fire is the hindsight leg. If that ever changes the row-level flag
        # may legitimately go True — but a row flagged visible-at-entry must be carrying
        # the open-drawdown leg, never the resolved-loss one.
        seen = set()
        for r in artifact["episodes"]:
            for lb in r["labels"]:
                if lb["label"] != "re_admission":
                    continue
                leg = lb["trigger"]["leg"]
                seen.add(leg)
                assert lb["visible_at_entry"] is (leg == pm.READMIT_LEG_OPEN_DRAWDOWN)
                assert "prior_matured" in lb["trigger"]
        assert seen == {pm.READMIT_LEG_PRIOR_LOSS}, \
            f"the leg mix moved: {sorted(seen)} — re-read the veto table before shipping"

    def test_prior_episode_comparisons_are_written_onto_the_rows(self, artifact):
        # Every comparison the scan made, including the ones that produced no label —
        # those are the ones a reader cannot otherwise see.
        with_prior = [r for r in artifact["episodes"] if r["prior_episode"]]
        assert with_prior, "no prior-episode comparisons recorded at all"
        for r in with_prior:
            p = r["prior_episode"]
            assert p["n_priors_in_window"] >= 1
            if p.get("undecidable"):
                assert p["n_priors_unscoreable"] >= 1
                # an undecidable prior nulls the label AND both legs
                nulled = {n["label"] for n in r["labels_null"]}
                assert {"re_admission", pm.READMIT_NULL_OPEN_DRAWDOWN,
                        pm.READMIT_NULL_PRIOR_LOSS} <= nulled
            else:
                assert isinstance(p["prior_matured"], bool)
                assert p["selected_by"] in (
                    pm.READMIT_LEG_OPEN_DRAWDOWN, pm.READMIT_LEG_PRIOR_LOSS,
                    "nearest_prior_no_leg_fired")
        # ...and a row with no in-window prior says so with a null, not a missing key.
        assert all("prior_episode" in r for r in artifact["episodes"])

    def test_no_price_path_tickers_are_disclosed_not_dropped(self, artifact):
        cov = artifact["coverage"]
        assert cov["n_no_price_path"] == len(
            [r for r in artifact["episodes"]
             if any(n["reason"] == "no_price_path" for n in r["labels_null"])])

    def test_the_run_is_deterministic(self, artifact):
        again = ppm.build_rows(ROOT)
        assert again["summary"] == artifact["summary"]
        assert [r["ticker"] for r in again["episodes"]] == \
            [r["ticker"] for r in artifact["episodes"]]

    def test_the_report_renders_and_names_the_cohort(self, artifact):
        text = ppm.render_report(artifact)
        for ticker, _date in LOSER_COHORT:
            assert f"| {ticker} |" in text, f"{ticker} missing from the report tables"
        assert "Winners forfeited" in text
        assert "validated" not in text.lower()

    def test_the_report_tables_the_round_trips_after_the_loser_book(self, artifact):
        """The round trips appear in no verdict-keyed table, so the page needs its own —
        placed AFTER the loser book so it can never be read as a third maturity block.

        Without this section a recovered loser is simply absent from the report: FN was
        missing from every table on the page the night its horizon completed.
        """
        text = ppm.render_report(artifact)
        rt = artifact["summary"]["round_trips"]
        head, sep, tail = text.partition(
            "## Round trips — crossed a gate, finished outside both tails")
        assert sep, "the round-trip section is missing from the report"
        assert "Every loser, with its trigger values" in head, \
            "the round trips must not precede the loser book"
        # the reconciliation is printed, not left for the reader to do
        assert (f"{rt['n_crossed_loser_gate']} through the {rt['loser_gate_pct']}% loser "
                f"gate + {rt['n_crossed_winner_gate']} through the "
                f"+{rt['winner_gate_pct']}% winner gate − {rt['n_crossed_both']} that "
                f"crossed both = {rt['n']}") in tail
        # ...and it is stated as evidence, never as a rate
        assert "NOT a rate" in tail
        for r in artifact["episodes"]:
            if r["path_tails"] and r["cohort"] not in ("loser", "winner"):
                assert f"| {r['ticker']} | {r['entry_date']} |" in tail, \
                    f"{r['ticker']}@{r['entry_date']} round-tripped but is not tabled"

    def test_the_report_splits_the_loser_book_by_maturity_and_the_counts_add_up(
            self, artifact):
        """Matured and marked-to-market rows never share a table.

        One pooled loser table sorted today's worst OPEN positions to the top of the
        page — which is the read the maturity gate exists to prevent, arriving through
        the layout instead of through a rate. Two labelled blocks, and section counts
        that reconcile to the stated total, so a reader can check nothing was dropped
        between them.
        """
        text = ppm.render_report(artifact)
        losers = [r for r in artifact["episodes"] if r["cohort"] == "loser"]
        n_matured = len([r for r in losers if r["maturity"] == "matured"])
        n_flight = len([r for r in losers if r["maturity"] == "in_flight"])
        n_other = len(losers) - n_matured - n_flight

        assert f"### Matured losers ({n_matured})" in text
        assert f"### In-flight losers ({n_flight})" in text
        assert f"= {len(losers)}." in text
        assert n_matured + n_flight + n_other == len(losers)
        # the matured block is exactly what every rate above was computed on
        assert n_matured == artifact["summary"]["cohorts"]["n_losers"]
        # each block's table carries its own rows, and only its own
        head, _, tail = text.partition(f"### In-flight losers ({n_flight})")
        matured_block = head.rpartition(f"### Matured losers ({n_matured})")[2]
        for r in losers:
            line = f"| {r['ticker']} | {r['entry_date']} |"
            assert (line in matured_block) is (r["maturity"] == "matured"), \
                f"{r['ticker']}@{r['entry_date']} is in the wrong maturity block"
        assert "In-flight rows (classified, counted in no rate)" in tail

    def test_the_in_flight_block_reconciles_to_its_own_total(self, artifact):
        text = ppm.render_report(artifact)
        f = artifact["summary"]["in_flight"]
        assert (f["n_losers_marked"] + f["n_winners_marked"] + f["n_neutral_marked"]
                + f["n_unscored_marked"]) == f["n"]
        assert (f"{f['n_losers_marked']} at loser levels · "
                f"{f['n_winners_marked']} at winner levels · "
                f"{f['n_neutral_marked']} neutral · "
                f"{f['n_unscored_marked']} unscored = {f['n']}") in text

    def test_the_report_marks_the_hindsight_row_as_hindsight(self, artifact):
        """The +79pp may not appear on the page without its epistemic status attached."""
        text = ppm.render_report(artifact)
        veto = {v["key"]: v for v in artifact["summary"]["veto_cost"]}
        hind = veto["re_admission:prior_episode_loss"]
        build = veto["re_admission:open_drawdown_at_readmit"]
        assert "| `re_admission:prior_episode_loss` | hindsight upper bound |" in text
        assert "| `re_admission:open_drawdown_at_readmit` | buildable |" in text
        assert f"{hind['loss_avoided_pct']:.2f}pp on this line is a CEILING" in text
        # the buildable row is printed WITH its zero rather than dropped
        assert build["n_flagged"] == 0
        assert "it fires **zero** times on this window" in text
        assert "Dates flagged" in text      # n_dates_flagged reaches the reader

    def test_the_taxonomy_table_prints_per_label_coverage(self, artifact):
        text = ppm.render_report(artifact)
        assert "loser coverage" in text
        for f in artifact["summary"]["label_frequency"]:
            assert f"| {f['n_losers_evaluated']} / {f['n_losers_total']} " in text


# ===========================================================================
# W-E.3 — the close-series ladder (D21: extras-universe names were ungradeable)
# ===========================================================================
class TestCloseResolverLadder:
    """ADJUSTED-FIRST since 2026-08-06 (ppm.PRICE_BASIS_ERA).

    This class used to assert the opposite — "the rungs may only APPEND; a name the four
    caches carry must resolve to the identical series it did before the fallbacks
    existed". That property was real, and it was the licence for adding rungs without an
    era stamp, but it also PINNED THE DEFECT: the caches are unadjusted while `bench` is
    an adjusted SPY, so 796 of 807 episodes differenced two bases and booked each name's
    own dividend as underperformance. The reordering is the era-stamped change the old
    note itself said would be required; the stamp lives in `method.price_basis`.

    What replaces byte-identity as the safety property: the cache is still the LAST rung
    (coverage is never traded for basis purity) and every episode carries `price_source`
    plus `price_basis`, so a name resolved on the raw cache says so on the artifact."""

    @staticmethod
    def _cache_frame() -> pd.DataFrame:
        idx = pd.bdate_range("2026-01-02", periods=40)
        return pd.DataFrame(
            {"INCACHE": [float(10 + i) for i in range(40)],
             "BOTH": [float(50 + i) for i in range(40)]}, index=idx)

    @staticmethod
    def _write_ohlcv(root: Path, ticker: str, values: list) -> None:
        d = root / ppm.BASKET_OHLCV_REL
        d.mkdir(parents=True, exist_ok=True)
        idx = pd.bdate_range("2026-01-02", periods=len(values))
        pd.DataFrame({"open": values, "high": values, "low": values,
                      "close": values, "volume": [1] * len(values)},
                     index=idx).to_parquet(d / f"{ticker}.parquet")

    @staticmethod
    def _write_extras(root: Path, cols: dict) -> None:
        d = root / ppm.BASKET_EXTRAS_REL
        d.parent.mkdir(parents=True, exist_ok=True)
        n = len(next(iter(cols.values())))
        pd.DataFrame(cols, index=pd.bdate_range("2026-01-02", periods=n)).to_parquet(d)

    def test_an_adjusted_rung_outranks_the_cache(self, tmp_path):
        """INVERTED 2026-08-06. A name carried by BOTH the cache and an adjusted store
        must resolve to the ADJUSTED one — otherwise `excess_pct` keeps differencing an
        unadjusted name leg against an adjusted SPY."""
        closes = self._cache_frame()
        self._write_ohlcv(tmp_path, "BOTH", [999.0] * 40)
        series, source = ppm.close_resolver(tmp_path, closes)("BOTH")
        assert source == ppm.SOURCE_BASKET_OHLCV, "the cache must not win any more"
        assert float(series.iloc[-1]) == 999.0

    def test_a_cache_only_ticker_is_kept_and_stamped_unadjusted(self, tmp_path):
        """Coverage is not traded for basis purity: a name with no adjusted counterpart
        still resolves — on the cache, named as such so the residual is visible."""
        closes = self._cache_frame()
        series, source = ppm.close_resolver(tmp_path, closes)("INCACHE")
        assert source == ppm.SOURCE_CACHE
        assert series.equals(closes["INCACHE"].dropna())
        from engine.price_ladder import is_adjusted
        assert is_adjusted(source) is False

    def test_ohlcv_is_the_second_rung_and_extras_the_third(self, tmp_path):
        closes = self._cache_frame()
        self._write_ohlcv(tmp_path, "DEEP", [float(100 + i) for i in range(40)])
        self._write_extras(tmp_path, {"DEEP": [1.0] * 40, "SHALLOW": [2.0] * 40})
        resolve = ppm.close_resolver(tmp_path, closes)
        deep, deep_src = resolve("DEEP")
        shallow, shallow_src = resolve("SHALLOW")
        assert deep_src == ppm.SOURCE_BASKET_OHLCV and float(deep.iloc[0]) == 100.0
        assert shallow_src == ppm.SOURCE_BASKET_EXTRAS and float(shallow.iloc[0]) == 2.0

    def test_a_ticker_on_no_rung_is_still_none(self, tmp_path):
        assert ppm.close_resolver(tmp_path, self._cache_frame())("NOWHERE") == (
            None, None)

    def test_a_fallback_series_arrives_clean_and_sorted(self, tmp_path):
        """A rung that returned raw frames would grade the right name off the wrong
        bars — NaNs and an unsorted index are the two ways that happens."""
        d = tmp_path / ppm.BASKET_OHLCV_REL
        d.mkdir(parents=True, exist_ok=True)
        idx = pd.bdate_range("2026-01-02", periods=5)[::-1]      # reversed
        pd.DataFrame({"close": [5.0, float("nan"), 3.0, 2.0, 1.0]},
                     index=idx).to_parquet(d / "MESSY.parquet")
        series, source = ppm.close_resolver(tmp_path, self._cache_frame())("MESSY")
        assert source == ppm.SOURCE_BASKET_OHLCV
        assert len(series) == 4 and not series.isna().any()
        assert series.index.is_monotonic_increasing
        assert isinstance(series.index, pd.DatetimeIndex)

    def test_an_unreadable_rung_is_a_miss_not_a_crash(self, tmp_path):
        d = tmp_path / ppm.BASKET_OHLCV_REL
        d.mkdir(parents=True, exist_ok=True)
        (d / "JUNK.parquet").write_bytes(b"not a parquet file")
        self._write_extras(tmp_path, {"JUNK": [4.0] * 40})
        series, source = ppm.close_resolver(tmp_path, self._cache_frame())("JUNK")
        assert source == ppm.SOURCE_BASKET_EXTRAS, "a bad rung must fall through"
        assert float(series.iloc[0]) == 4.0

    def test_resolution_is_memoized(self, tmp_path):
        resolve = ppm.close_resolver(tmp_path, self._cache_frame())
        first = resolve("INCACHE")
        assert resolve("INCACHE")[0] is first[0], "a second call must not re-read"


class TestLadderOnTheCommittedLedgers:
    """The ladder against real data — a unit test on tmp_path cannot say whether the
    class it was built for actually resolves."""

    def test_the_asts_class_now_resolves_and_names_its_rung(self):
        """Re-pinned 2026-08-19 (main-red-repair): the rung moved, honestly.

        `data/baskets/ohlcv/ASTS.parquet` stops at 2026-08-17 while the cache
        panel's ceiling (`min_last`) has advanced to 2026-08-18 — the same
        "a rung that hits but ends before the ceiling is a MISS, so the walk
        continues" mechanism `resolve_close`'s own docstring documents for
        ARWR/FN/HL/TR. Measured directly (`resolve_close("ASTS", ...).tried`
        == ``['baskets_ohlcv', 'yahoo']``): baskets_ohlcv is tried and found,
        but rejected as stale against the ceiling, and yahoo (through
        2026-08-18) wins. This is the ladder doing exactly what it is built
        to do, not a regression — so the pin moves to match, asserting the
        one honest rung rather than loosening to "any adjusted rung"."""
        closes = ppm.load_closes(ROOT)
        assert "ASTS" not in closes.columns, (
            "ASTS must be absent from the caches or this proves nothing")
        series, source = ppm.close_resolver(ROOT, closes)("ASTS")
        assert series is not None and source == ppm.SOURCE_YAHOO
        assert len(series) > 250

    def test_most_cached_names_now_resolve_on_an_adjusted_rung(self):
        """INVERTED 2026-08-06 (was: every cache-resolved name is byte-identical).

        The old assertion is exactly what the defect looked like from the inside: it
        PASSED, on every one of these names, while each of them was being differenced
        against an adjusted SPY. Now the majority must come off an adjusted rung, and any
        that still falls back to the cache must be STAMPED rather than silent."""
        from engine.price_ladder import is_adjusted, ADJUSTED_SOURCES

        closes = ppm.load_closes(ROOT)
        resolve = ppm.close_resolver(ROOT, closes)
        sample = list(closes.columns)[::7]
        assert len(sample) > 50, "sample must be wide enough to mean something"

        adjusted, unadjusted = [], []
        for ticker in sample:
            series, source = resolve(ticker)
            if series is None:
                continue
            assert is_adjusted(source) is not None, f"{ticker}: unclassifiable {source}"
            (adjusted if source in ADJUSTED_SOURCES else unadjusted).append(ticker)

        assert len(adjusted) > len(unadjusted), (
            f"only {len(adjusted)}/{len(adjusted) + len(unadjusted)} sampled names came "
            "off an adjusted rung — the ladder has regressed to cache-first")
        for ticker in unadjusted:
            assert resolve(ticker)[1] == ppm.SOURCE_CACHE, ticker

    def test_coverage_separates_a_missing_name_from_a_stale_store(self, artifact):
        """`U` resolves to a real series whose store stops before its fill bar. That
        is a stale STORE, not a missing NAME, and merging the two would have the
        coverage receipt claim we hold no prices for a ticker we do hold."""
        cov = artifact["coverage"]
        resolve = ppm.close_resolver(ROOT, ppm.load_closes(ROOT))
        assert set(cov["tickers_no_price_series"]) <= set(cov["tickers_no_price_path"])
        assert cov["n_tickers_no_price_series"] == len(cov["tickers_no_price_series"])
        for ticker in cov["tickers_no_price_series"]:
            assert resolve(ticker)[0] is None, ticker
        for ticker in set(cov["tickers_no_price_path"]) - set(
                cov["tickers_no_price_series"]):
            assert resolve(ticker)[0] is not None, ticker

    def test_the_ladder_receipt_reaches_the_artifact(self, artifact):
        from engine.price_ladder import LADDER

        cov = artifact["coverage"]
        sources = cov["price_path_sources"]
        assert sum(sources.values()) + cov["n_no_price_path"] == cov["n_episodes"]
        assert set(sources) <= set(LADDER), (
            "every rung on the receipt must be a tag the shared ladder defines, or the "
            "artifact names a basis nothing can classify")
        assert "closes_ladder" in artifact["generated_from"]

    def test_the_artifact_declares_its_price_basis_era(self, artifact):
        """The era stamp IS the boundary — episodes are regenerated wholesale, never
        re-graded in place, so an artifact with no stamp is era 1 and its excess_pct is
        not row-for-row comparable with this one's."""
        method = artifact["method"]
        assert method["price_basis"] == ppm.PRICE_BASIS_ERA
        assert method["price_basis_era_boundary"] == ppm.PRICE_BASIS_ERA_BOUNDARY
        assert "adjusted-first" in method["price_ladder"]

    def test_every_episode_carries_its_basis_stamp(self, artifact):
        """Basis must be readable off the row, not re-derived by archaeology — the exact
        gap that made #4698 unable to say which path fed the us_board ledger."""
        from engine.price_ladder import is_adjusted

        eps = artifact["episodes"]
        assert eps, "no episodes to check"
        for ep in eps:
            src = ep.get("price_source")
            if src is None:                       # unresolved name: no basis to claim
                assert ep.get("price_basis") is None, ep["ticker"]
                continue
            expected = {True: "adjusted", False: "unadjusted"}[is_adjusted(src)]
            assert ep["price_basis"] == expected, f"{ep['ticker']}: {src}"
        assert any(e.get("price_basis") == "adjusted" for e in eps)

    def test_the_fallback_rungs_actually_graded_something(self, artifact):
        """The point of the wave. If this ever goes to zero the ladder is dead code
        and `tickers_no_price_path` should be re-read, not the test relaxed."""
        assert artifact["coverage"]["price_path_sources"].get(
            ppm.SOURCE_BASKET_OHLCV, 0) > 0


# Q02/B22 descriptive source-cohort integrity
"""Focused tests for the Q02/B22 descriptive learning-cohort integrity contract.

What is pinned here, per the frozen contract:

  1. two raw eras never share qualified rate denominators;
  2. an existing episode crossing a source era boundary is `mixed` with its score and
     return fields untouched;
  3. a missing source stamp stays unknown (`unassigned`) — never a manufactured era;
  4. same-date conflicting source/horizon stamps stay `conflict`;
  5. disjoint source reach stays non-conflicting (documented reach, not disagreement);
  6. membership disagreement between the sources is exposed on the receipt;
  7. in-flight / unscored rows enter no rate in the qualified per-era summaries;
  8. legacy summary equality and input immutability (the block is strictly additive);
  9. deterministic ordering and idempotence;
  10. old artifacts without the field render unchanged;
  11. `--cohort-integrity-only` reads a preserved artifact and the membership sources,
      forbids every scoring/outcome entrypoint, and writes nothing;
 12. the frozen original `as_of` cut: later membership vintages can never assign,
      conflict or re-era an episode, and the excluded future reach is disclosed;
 13. observed membership gaps split an episode from later readmission stamps
      (partial at best, never single); strict ISO calendar-date refusal everywhere;
 14. per-era wrappers carry descriptive_only plus an explicit no-promotion
      authority, and conflicting original membership blocks clean rates.

No fixture data, no study reruns: every input is synthetic and every scorer touch in
the bypass tests is monkeypatched to raise.
"""

import copy
import hashlib
import json

import pandas as pd
import pytest

from engine import postmortem as pm
from scripts import prophet_postmortem as pp


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #
def _integrity_ep(ticker, entry, exit_=None, maturity="matured"):
    return {"ticker": ticker, "entry_date": entry, "board_exit_date": exit_,
            "maturity": maturity}


def _integrity_graded_row(ticker, entry, outcome=-10.0, excess=-9.0, maturity="matured",
                exit_=None, labels=None, labels_null=None):
    """A row shaped like an artifact episode row (only the fields integrity reads)."""
    row = _integrity_ep(ticker, entry, exit_, maturity)
    row.update({
        "outcome_pct": outcome,
        "excess_pct": excess,
        "cohort": pm.cohort_of(outcome, excess),
        "labels": labels or [],
        "labels_null": labels_null or [],
        # Rendered blocks read these; integrity itself only reads identity/maturity.
        "path_tails": [],
        "mae_pct": None,
        "mfe_pct": None,
        "held": None,
    })
    return row


def _integrity_mem(retro=None, snap=None):
    return {"retro": retro or {}, "snapshot": snap or {}}


def _integrity_labelled(name, **trigger):
    return {"label": name, "visible_at_entry": False, "trigger": dict(trigger)}


@pytest.fixture()
def _integrity_forbid_scoring(monkeypatch):
    """Every scoring/outcome entrypoint raises — for the receipt-only path."""
    def _boom(*_a, **_k):
        raise AssertionError("scoring/outcome entrypoint invoked in receipt-only path")

    monkeypatch.setattr(pp, "build_rows", _boom)
    monkeypatch.setattr(pp.ts, "build_episodes", _boom)
    monkeypatch.setattr(pp.ts, "score_episode", _boom)
    monkeypatch.setattr(pp.pm, "classify", _boom)
    monkeypatch.setattr(pp.pm, "aggregate", _boom)
    monkeypatch.setattr(pp.pm, "entry_context", _boom)
    return _boom


def _integrity_write_ledger(root, retro_rows, snap_docs):
    ledger = root / "data" / "us_board_ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(retro_rows).to_parquet(ledger / "retro_grades.parquet", index=False)
    with (ledger / "snapshots.jsonl").open("w", encoding="utf-8") as fh:
        for doc in snap_docs:
            fh.write(json.dumps(doc) + "\n")


# ===========================================================================
# 1. two raw eras never share qualified rate denominators
# ===========================================================================
def test_two_raw_eras_never_share_qualified_denominators():
    retro = {
        "2026-07-01": {"AAA": ["us_prophet_v1"]},
        "2026-08-10": {"BBB": ["us_prophet_v2"]},
    }
    rows = [
        # era 1: one matured loser carrying sector_headwind (closed inside its era)
        _integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0,
                    exit_="2026-07-03",
                    labels=[_integrity_labelled("sector_headwind", leg="theme_reco")]),
        # era 2: one matured loser with the label decidable-but-unfired
        _integrity_graded_row("BBB", "2026-08-10", outcome=-12.0, excess=-11.0,
                    exit_="2026-08-12"),
    ]
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), rows,
                                      as_of="2026-08-10")

    assert sorted(block["per_era"]) == ["us_prophet_v1", "us_prophet_v2"]
    e1 = block["per_era"]["us_prophet_v1"]["aggregate"]
    e2 = block["per_era"]["us_prophet_v2"]["aggregate"]
    # Each era's denominators count ONLY its own episode.
    assert e1["n_episodes"] == 1 and e2["n_episodes"] == 1
    assert e1["n_matured"] == 1 and e2["n_matured"] == 1
    hw1 = next(f for f in e1["label_frequency"] if f["label"] == "sector_headwind")
    hw2 = next(f for f in e2["label_frequency"] if f["label"] == "sector_headwind")
    assert hw1["n_losers_evaluated"] == 1 and hw1["n_losers"] == 1
    assert hw2["n_losers_evaluated"] == 1 and hw2["n_losers"] == 0
    # The era-2 loser carries no headwind trigger, and none of era 1's evidence leaks
    # into era 2's counts: 0 of 1, never 1 of 2.
    assert hw2["loser_share_pct"] == 0.0
    # And no pooled qualified block exists alongside the per-era ones.
    assert not any(k in block for k in ("qualified", "pooled", "overall"))
    # Every per-era block is a wrapper: descriptive_only plus an explicit
    # no-promotion authority, with the legacy aggregate underneath unchanged.
    for era in block["per_era"].values():
        assert era["descriptive_only"] is True
        assert era["promotion_authority"].startswith("none")
        assert set(era["aggregate"]) >= {"n_episodes", "label_frequency"}


# ===========================================================================
# 2. an episode crossing a source era boundary is mixed, without mutation
# ===========================================================================
def test_era_crossing_episode_is_mixed_without_score_mutation():
    retro = {
        "2026-07-01": {"AAA": ["us_prophet_v1"]},
        "2026-07-05": {"AAA": ["us_prophet_v2"]},
    }
    row = _integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0,
                      exit_="2026-07-10",
                      labels=[_integrity_labelled("gap_event", pct=-9.4)])
    before = copy.deepcopy(row)
    ep = _integrity_ep("AAA", "2026-07-01", "2026-07-10")
    ep_before = copy.deepcopy(ep)

    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), [row],
                                      as_of="2026-07-10")

    a = block["episodes"][0]
    assert a["partition"] == "mixed"
    assert a["stamps"] == ["us_prophet_v1", "us_prophet_v2"]
    assert a["stamp"] is None
    assert a["n_stamped_records"] == 2 and a["n_missing_stamp_records"] == 0
    # Score and return fields untouched — identity read, never written.
    assert row == before
    assert ep == ep_before
    assert a["maturity"] == "matured"


def test_conflict_outranks_mixed_in_precedence():
    retro = {
        "2026-07-01": {"AAA": ["us_prophet_v1"]},      # day 1: clean v1 stamp
        "2026-07-03": {"AAA": ["us_prophet_v2", "v1"]},  # day 3: same-key conflict
    }
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-10")
    a = block["episodes"][0]
    assert a["partition"] == "conflict"
    assert block["partition_precedence"] == "conflict > mixed > partial > single > unassigned"
    assert a["conflicts"] == [{"date": "2026-07-03",
                               "stamps_by_source": {"retro": ["us_prophet_v2", "v1"]}}]


# ===========================================================================
# 3. a missing source stamp stays unknown
# ===========================================================================
def test_missing_stamp_stays_unassigned_never_legacy():
    retro = {"2026-07-01": {"AAA": [None]}}
    snap = {"2026-07-02": {"AAA": [""]}}          # empty string: explicitly missing too
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-02")
    a = block["episodes"][0]
    assert a["partition"] == "unassigned"
    assert a["stamps"] == [] and a["stamp"] is None
    assert a["n_membership_records"] == 2 and a["n_missing_stamp_records"] == 2
    # No membership record at all is unassigned the same way.
    block2 = pm.cohort_integrity_block(_integrity_mem(),
                                       [_integrity_ep("ZZZ", "2026-07-01", "2026-07-10")],
                                       as_of="2026-07-02")
    assert block2["episodes"][0]["partition"] == "unassigned"
    assert block2["episodes"][0]["n_membership_records"] == 0
    # And per-era summaries never exist for a manufactured era name.
    assert block["per_era"] == {} or "legacy" not in block.get("per_era", {})


def test_nullish_spelling_folds_to_missing_but_real_strings_are_kept():
    assert pm.integrity_stamp("us_prophet_v1") == "us_prophet_v1"
    assert pm.integrity_stamp(" alpha ") == " alpha "      # real pre-ranker era
    assert pm.integrity_stamp("legacy") == "legacy"      # recorded string, NOT invented
    for missing in (None, "", "   ", "None", "nan", "NaN", "<NA>", "null", 7, 1.5, True):
        assert pm.integrity_stamp(missing) is None, missing


def test_partial_is_agreeing_stamps_plus_a_missing_record():
    retro = {"2026-07-01": {"AAA": ["us_prophet_v1"]}}
    snap = {"2026-07-02": {"AAA": [None]}}       # known stamp + a missing membership stamp
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-02")
    a = block["episodes"][0]
    assert a["partition"] == "partial"
    assert a["stamp"] == "us_prophet_v1"
    assert a["n_missing_stamp_records"] == 1
    # A present stamp in one record never silently overrides the missing one: partial
    # episodes are excluded from the qualified per-era slices, which are single-only.
    assert block["per_era"] == {}


# ===========================================================================
# 4. same-date conflicting stamps (across sources, or across horizons)
# ===========================================================================
def test_same_date_conflict_between_sources_and_within_one_source():
    retro = {"2026-07-01": {"AAA": ["us_prophet_v1", "alpha"]}}   # two horizons disagree
    snap = {"2026-07-01": {"AAA": ["us_prophet_v1"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-02")
    a = block["episodes"][0]
    assert a["partition"] == "conflict"
    # The same date also sits in the snapshot source, so the conflict record names
    # every carrier of that date, not only the disagreeing one.
    assert a["conflicts"] == [{"date": "2026-07-01",
                               "stamps_by_source": {"retro": ["alpha", "us_prophet_v1"],
                                                    "snapshot": ["us_prophet_v1"]}}]

    retro2 = {"2026-07-01": {"BBB": ["us_prophet_v1"]}}
    snap2 = {"2026-07-01": {"BBB": ["us_prophet_v2"]}}            # sources disagree
    block2 = pm.cohort_integrity_block(_integrity_mem(retro=retro2, snap=snap2),
                                       [_integrity_ep("BBB", "2026-07-01", "2026-07-10")],
                                       as_of="2026-07-02")
    a2 = block2["episodes"][0]
    assert a2["partition"] == "conflict"
    assert a2["conflicts"][0]["stamps_by_source"] == {
        "retro": ["us_prophet_v1"], "snapshot": ["us_prophet_v2"]}
    # A conflicting original membership record blocks clean rates entirely:
    # per-era slices are single-only AND conflict-free.
    assert "per_era" not in block2
    assert block2["per_era_unavailable_reason"] == "conflicting_original_membership"


# ===========================================================================
# 5. disjoint source reach stays non-conflicting
# ===========================================================================
def test_disjoint_reach_is_not_a_conflict():
    retro = {"2026-06-15": {"AAA": ["alpha"]}}          # retro-only date
    snap = {"2026-07-20": {"BBB": ["us_prophet_v2"]}}   # snapshot-only date
    rows = [_integrity_graded_row("AAA", "2026-06-15", exit_="2026-06-20"),
            _integrity_graded_row("BBB", "2026-07-20", outcome=+9.0, excess=+1.0)]
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap), rows,
                                      as_of="2026-07-20")

    assert [a["partition"] for a in block["episodes"]] == ["single", "single"]
    srcs = block["sources"]
    assert srcs["per_source_only_dates"] == {"retro": ["2026-06-15"],
                                             "snapshot": ["2026-07-20"]}
    assert srcs["overlap_dates"] == []
    assert srcs["n_overlap_dates_with_membership_difference"] == 0
    assert all(not entry["conflicts"] for entry in block["episodes"])
    assert srcs["note_en"]


# ===========================================================================
# 6. membership disagreement on an overlap date is exposed
# ===========================================================================
def test_membership_disagreement_is_exposed_on_the_receipt():
    retro = {"2026-07-05": {"AAA": ["us_prophet_v1"], "GHOST_R": ["us_prophet_v1"]}}
    snap = {"2026-07-05": {"AAA": ["us_prophet_v1"], "GHOST_S": ["us_prophet_v1"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-05", "2026-07-10")],
                                      as_of="2026-07-10")
    per_date = block["sources"]["membership_on_overlap_dates"]
    assert len(per_date) == 1
    day = per_date[0]
    assert day["date"] == "2026-07-05"
    assert day["only_in"] == {"retro": ["GHOST_R"], "snapshot": ["GHOST_S"]}
    assert day["membership_difference"] is True
    assert block["sources"]["n_overlap_dates_with_membership_difference"] == 1
    # The shared ticker itself is fine: both sources agree on its stamp.
    assert block["episodes"][0]["partition"] == "single"


def test_cross_source_stamp_disagreement_is_listed_per_overlap_date():
    retro = {"2026-07-05": {"AAA": ["us_prophet_v1"]}}
    snap = {"2026-07-05": {"AAA": ["us_prophet_v2"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-05", "2026-07-10")],
                                      as_of="2026-07-10")
    day = block["sources"]["membership_on_overlap_dates"][0]
    assert day["stamp_disagreements"] == [{
        "ticker": "AAA",
        "stamps_by_source": {"retro": ["us_prophet_v1"], "snapshot": ["us_prophet_v2"]},
    }]
    assert block["episodes"][0]["partition"] == "conflict"


# ===========================================================================
# 7. in-flight / unscored rows enter no qualified rate
# ===========================================================================
def test_inflight_and_unscored_rows_enter_no_rate():
    retro = {"2026-07-01": {"AAA": ["v1"]},
             "2026-07-02": {"BBB": ["v1"]},
             "2026-07-03": {"CCC": ["v1"]}}
    rows = [
        _integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0, maturity="matured",
                    exit_="2026-07-02"),
        _integrity_graded_row("BBB", "2026-07-02", outcome=-30.0, excess=-25.0,
                    maturity="in_flight", exit_="2026-07-03"),
        _integrity_graded_row("CCC", "2026-07-03", outcome=None, excess=None, maturity="unscored"),
    ]
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), rows,
                                      as_of="2026-07-03")
    era = block["per_era"]["v1"]["aggregate"]
    assert era["n_episodes"] == 3 and era["n_matured"] == 1
    assert era["n_in_flight"] == 1 and era["n_unscored"] == 1
    assert era["cohorts"]["n_losers"] == 1          # the in-flight mark is NOT a rate
    assert era["in_flight"]["n"] == 1
    assert era["n_board_dates"] == 1
    # Maturity is disclosed per partition, not folded into rates anywhere.
    assert block["partitions"]["single"]["maturity"] == {
        "matured": 1, "in_flight": 1, "unscored": 1}


# ===========================================================================
# 8. legacy summary equality and input immutability
# ===========================================================================
def test_block_is_additive_and_leaves_rows_and_legacy_summary_equal():
    retro = {"2026-07-01": {"AAA": ["us_prophet_v1"]},
             "2026-07-05": {"AAA": ["us_prophet_v2"]}}
    rows = [
        _integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0,
                    labels=[_integrity_labelled("sector_headwind", leg="theme_reco")],
                    labels_null=[{"label": "thesis_break",
                                  "reason": "no_stop_level_recorded"}]),
        _integrity_graded_row("BBB", "2026-07-01", outcome=+9.0, excess=+1.0),
    ]
    rows_snapshot = copy.deepcopy(rows)
    legacy = pm.aggregate(rows)

    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), rows,
                                      as_of="2026-07-01")

    assert rows == rows_snapshot                     # no row mutated
    assert pm.aggregate(rows) == legacy              # legacy summary identical
    assert pm.aggregate([r for r in rows]) == legacy
    doc = {"summary": legacy, "cohort_integrity": block}
    assert doc["summary"] == legacy                  # field coexists additively


# ===========================================================================
# 9. deterministic ordering / idempotence
# ===========================================================================
def test_deterministic_ordering_and_idempotence():
    retro = {
        "2026-07-02": {"B": ["v2"], "A": ["v2"]},
        "2026-07-01": {"A": ["v1"]},
        "2026-06-20": {"C": ["alpha"]},
    }
    eps = [_integrity_ep("B", "2026-07-02", "2026-07-06"),
           _integrity_ep("A", "2026-07-01", "2026-07-06"),
           _integrity_ep("C", "2026-06-20", "2026-06-24")]
    one = pm.cohort_integrity_block(_integrity_mem(retro=retro), eps,
                                    as_of="2026-07-06")
    two = pm.cohort_integrity_block(_integrity_mem(retro=retro), eps,
                                    as_of="2026-07-06")
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)
    assert [(a["entry_date"], a["ticker"]) for a in one["episodes"]] == sorted(
        (a["entry_date"], a["ticker"]) for a in one["episodes"])
    for src in one["sources"]["sources"].values():
        assert src["dates"] == sorted(src["dates"])
    # Membership-window bounds: exit date itself is EXCLUSIVE for closed episodes.
    a_b = next(a for a in one["episodes"] if a["ticker"] == "B")
    assert a_b["window_dates"] == ["2026-07-02"]        # 07-06 excluded
    a_c = next(a for a in one["episodes"] if a["ticker"] == "C")
    assert a_c["window_dates"] == ["2026-06-20"]
    # Open episodes run to the latest board date INCLUSIVE.
    block_open = pm.cohort_integrity_block(_integrity_mem(retro=retro),
                                           [_integrity_ep("A", "2026-07-01")],
                                           as_of="2026-07-06")
    a_open = block_open["episodes"][0]
    assert a_open["open_episode"] is True
    assert a_open["window_dates"] == ["2026-07-01", "2026-07-02"]


# ===========================================================================
# 10. old frozen artifacts (no cohort_integrity) render unchanged
# ===========================================================================
def _integrity_legacy_doc() -> dict:
    rows = [_integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0,
                        exit_="2026-07-05")]
    summary = pm.aggregate(rows)
    summary["round_trips"] = pp._round_trip_counts(rows)
    return {
        "schema": pp.SCHEMA,
        "as_of": "2026-07-31",
        "method": {"horizon": 10},
        "coverage": {
            "n_episodes": len(rows), "board_dates": 1,
            "board_date_first": "2026-07-01", "board_date_last": "2026-07-01",
            "n_no_price_path": 0, "tickers_no_price_path": [],
            "basket_revisions": 0, "basket_asof_first": None,
            "basket_asof_last": None,
        },
        "caveats": [],
        "summary": summary,
        "episodes": rows,
    }


def test_old_artifact_renders_unchanged_and_new_section_is_additive():
    old = _integrity_legacy_doc()
    old_render = pp.render_report(old)
    assert "Cohort integrity" not in old_render       # frozen doc, no new section

    # Every old line survives, in order, when the field is present (additive render).
    retro = {"2026-07-01": {"AAA": ["us_prophet_v1"]}}
    new = copy.deepcopy(old)
    new["cohort_integrity"] = pm.cohort_integrity_block(
        _integrity_mem(retro=retro), copy.deepcopy(old["episodes"]), as_of="2026-07-01")
    new_render = pp.render_report(new)
    assert "## Cohort integrity — original source eras (descriptive receipt)" in new_render
    assert "retained" in new_render and "compatibility" in new_render
    old_lines = old_render.splitlines()
    new_lines = new_render.splitlines()
    it = iter(new_lines)
    assert all(any(line == candidate for candidate in it) for line in old_lines)
    # And the new section sits BEFORE the pooled taxonomy rates.
    assert new_render.index("## Cohort integrity") < new_render.index("## Failure taxonomy")


# ===========================================================================
# 11. --cohort-integrity-only: read-only receipt, scoring forbidden, no writes
# ===========================================================================
def test_cohort_integrity_only_reads_artifact_forbids_scoring_and_writes_nothing(
        tmp_path, monkeypatch, capsys, _integrity_forbid_scoring):
    retro_rows = [
        {"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy", "horizon": 10,
         "rank_by": "us_prophet_v1"},
        {"as_of": "2026-07-05", "ticker": "AAA", "lane": "buy", "horizon": 10,
         "rank_by": "us_prophet_v2"},
        {"as_of": "2026-07-05", "ticker": "AAA", "lane": "buy", "horizon": 5,
         "rank_by": "us_prophet_v2"},
        {"as_of": "2026-07-05", "ticker": "AAA", "lane": "watch", "horizon": 10,
         "rank_by": "should_never_add_membership"},
    ]
    snap_docs = [
        {"as_of": "2026-07-05", "rank_by": "us_prophet_v2",
         "buy": [{"ticker": "AAA"}, {"ticker": "BBB"}]},
    ]
    _integrity_write_ledger(tmp_path, retro_rows, snap_docs)

    doc = {"schema": pp.SCHEMA, "as_of": "2026-07-05", "episodes": [
        {"ticker": "AAA", "entry_date": "2026-07-01", "board_exit_date": "2026-07-10",
         "maturity": "matured", "outcome_pct": -10.0},
    ]}
    art = tmp_path / "summary.json"
    art.write_text(json.dumps(doc), encoding="utf-8")
    art_bytes = art.read_bytes()

    rc = pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                  "--artifact", str(art)])
    assert rc == 0
    out = capsys.readouterr().out
    receipt = json.loads(out)                     # stdout is ONLY the receipt JSON

    a = receipt["episodes"][0]
    assert a["partition"] == "mixed"              # v1 on entry night, v2 later in window
    assert a["stamps"] == ["us_prophet_v1", "us_prophet_v2"]
    # 1 retro record on entry night + 2 retro horizons + 1 snapshot record on 07-05;
    # the `watch` row never added a record.
    assert a["n_membership_records"] == 4
    assert a["records_by_source"] == {"retro": 3, "snapshot": 1}
    assert receipt["partitions"]["single"]["n_episodes"] == 0
    assert receipt["sources"]["n_overlap_dates"] == 1
    assert receipt["sources"]["membership_on_overlap_dates"][0]["only_in"] == {
        "retro": [], "snapshot": ["BBB"]}
    assert receipt["sources_read"]["retro"]["readable"] is True
    assert receipt["sources_read"]["retro"]["n_buy_records"] == 3
    # Receipt-only: no per-era rate summaries — the read-only path never re-aggregates.
    assert "per_era" not in receipt
    assert receipt["receipt_only_note_en"]
    assert receipt["artifact"] == str(art)

    # Input artifact byte-identical, and nothing was written anywhere under root.
    assert art.read_bytes() == art_bytes
    writes = [p for p in tmp_path.rglob("*")
              if p.is_file() and p.resolve() not in (art.resolve(),)
              and "us_board_ledger" not in p.parts]
    assert writes == []


def test_cohort_integrity_only_reports_unreadable_and_malformed_sources(
        tmp_path, monkeypatch, capsys, _integrity_forbid_scoring):
    ledger = tmp_path / "data" / "us_board_ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "retro_grades.parquet").write_bytes(b"not a parquet file at all")
    with (ledger / "snapshots.jsonl").open("w", encoding="utf-8") as fh:
        fh.write("{this is not json\n")
        fh.write(json.dumps({"as_of": "2026-07-05", "rank_by": "us_prophet_v2",
                             "buy": [{"ticker": "AAA"}]}) + "\n")

    doc = {"schema": pp.SCHEMA, "as_of": "2026-07-05", "episodes": [
        {"ticker": "AAA", "entry_date": "2026-07-05", "board_exit_date": None,
         "maturity": "in_flight"},
    ]}
    art = tmp_path / "summary.json"
    art.write_text(json.dumps(doc), encoding="utf-8")

    rc = pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                  "--artifact", str(art)])
    assert rc == 0
    receipt = json.loads(capsys.readouterr().out)
    retro_status = receipt["sources_read"]["retro"]
    assert retro_status["readable"] is False and retro_status["error"]
    snap_status = receipt["sources_read"]["snapshot"]
    assert snap_status["readable"] is True and snap_status["n_malformed_lines"] == 1
    # The snapshot stamp still resolves the episode; the broken parquet must NOT be
    # allowed to look like validated source absence.
    assert receipt["episodes"][0]["partition"] == "single"
    assert receipt["episodes"][0]["records_by_source"] == {"snapshot": 1}


def test_cohort_integrity_only_requires_artifact_path(_integrity_forbid_scoring):
    with pytest.raises(SystemExit):
        pp.main(["--cohort-integrity-only"])


def test_generation_path_stamps_artifact_rows(tmp_path, monkeypatch):
    """Full-run wiring: build_rows' own I/O layers stay mocked; only the integrity
    loaders are exercised against synthetic ledgers, verifying the additive key."""
    retro_rows = [{"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy",
                   "horizon": 10, "rank_by": "us_prophet_v1"}]
    _integrity_write_ledger(tmp_path, retro_rows, [])

    rows = [_integrity_graded_row("AAA", "2026-07-01", exit_="2026-07-04")]
    monkeypatch.setattr(pp, "load_retro", lambda root: pd.DataFrame(retro_rows))
    monkeypatch.setattr(pp, "load_snapshots", lambda root: {})
    monkeypatch.setattr(pp, "load_closes", lambda root: pd.DataFrame())
    monkeypatch.setattr(pp, "load_bench", lambda root: None)
    monkeypatch.setattr(pp, "basket_history", lambda root: [])
    monkeypatch.setattr(pp, "membership_map", lambda root: {})
    monkeypatch.setattr(pp.ts, "build_episodes", lambda days: [
        {"ticker": "AAA", "entry_date": "2026-07-01", "exit_date": "2026-07-04"}])
    monkeypatch.setattr(pp.ts, "score_episode", lambda *a, **k: {
        "matured": True, "fill_pending": False, "pnl": -10.0, "excess": -9.0,
        "mark": -10.0, "mae": -10.0, "mfe": 0.5, "held": 3, "entry": 100.0,
        "entry_date": "2026-07-02"})
    monkeypatch.setattr(pp, "close_resolver", lambda root, closes: (
        lambda tk: (pd.Series([100.0, 95.0, 92.0, 90.5],
                              index=pd.to_datetime(
                                  ["2026-07-01", "2026-07-02", "2026-07-03",
                                   "2026-07-04"])),
                    "closes_cache_UNADJUSTED")))
    monkeypatch.setattr(pp, "prior_episodes", lambda scored, calendar: {})

    doc = pp.build_rows(tmp_path)
    ci = doc["cohort_integrity"]
    assert ci["schema"] == pm.COHORT_INTEGRITY_SCHEMA
    assert ci["episodes"][0]["partition"] == "single"
    assert ci["episodes"][0]["stamp"] == "us_prophet_v1"
    assert ci["per_era"]["us_prophet_v1"]["aggregate"]["n_matured"] == 1
    # Legacy summary untouched by the additive block.
    assert doc["summary"]["n_episodes"] == 1
    assert doc["episodes"][0]["outcome_pct"] == -10.0
    render = pp.render_report(doc)
    assert "## Cohort integrity — original source eras (descriptive receipt)" in render


def test_integrity_preserves_original_nonempty_stamp_bytes():
    assert pm.integrity_stamp("  era-A  ") == "  era-A  "
    assert pm.integrity_stamp("  NULL  ") is None
    block = pm.cohort_integrity_block(_integrity_mem(retro={"2026-07-01": {"AAA": ["era-A", " era-A "]}}), [_integrity_ep("AAA", "2026-07-01")], as_of="2026-07-01", include_era_rates=False)
    assert block["episodes"][0]["partition"] == "conflict"


def test_integrity_later_stamp_cannot_attest_missing_original_admission():
    row = _integrity_graded_row('AAA', '2026-07-01', exit_='2026-07-03')
    before = copy.deepcopy(row)
    block = pm.cohort_integrity_block(_integrity_mem(retro={'2026-07-02': {'AAA': ['later-era']}}), [row], as_of='2026-07-03')
    assignment = block['episodes'][0]
    assert assignment['partition'] == 'partial'
    assert assignment['entry_attribution'] == {'state': 'unassigned', 'records': [], 'stamps': [], 'n_missing_stamp_records': 0}
    assert block['per_era'] == {}
    assert row == before


def test_integrity_missing_entry_stamp_remains_partial_despite_later_stamp():
    block = pm.cohort_integrity_block(_integrity_mem(retro={'2026-07-01': {'AAA': [None]}, '2026-07-02': {'AAA': ['later-era']}}), [_integrity_graded_row('AAA', '2026-07-01')], as_of='2026-07-02')
    assignment = block['episodes'][0]
    assert assignment['partition'] == 'partial'
    assert assignment['entry_attribution']['state'] == 'unassigned'
    assert assignment['entry_attribution']['n_missing_stamp_records'] == 1
    assert block['per_era'] == {}


def test_integrity_loader_projects_provenance_without_reading_outcomes(tmp_path, monkeypatch):
    _integrity_write_ledger(tmp_path, [{'as_of': '2026-07-01', 'ticker': 'AAA', 'lane': 'buy', 'rank_by': 'raw-era', 'outcome_pct': 99}], [])
    original = pd.read_parquet
    reads = []
    def provenance_only(path, *args, **kwargs):
        columns = kwargs.get('columns')
        assert columns == ['as_of', 'ticker', 'lane', 'rank_by']
        reads.append(columns)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(pd, 'read_parquet', provenance_only)
    memberships, status = pp.load_retro_membership(tmp_path)
    assert reads and status['readable']
    assert memberships == {'2026-07-01': {'AAA': ['raw-era']}}


def test_integrity_missing_membership_columns_are_explicit_unreadable(tmp_path):
    directory = tmp_path / 'data/us_board_ledger'
    directory.mkdir(parents=True)
    pd.DataFrame([{'as_of': '2026-07-01', 'ticker': 'AAA', 'rank_by': 'raw-era'}]).to_parquet(directory / 'retro_grades.parquet', index=False)
    memberships, status = pp.load_retro_membership(tmp_path)
    assert memberships == {}
    assert status['readable'] is False
    assert status['error'] == 'missing_membership_columns: lane'


@pytest.mark.parametrize('document', [{}, {'schema': 'other/v1', 'episodes': []}, {'schema': pp.SCHEMA, 'episodes': [None]}])
def test_integrity_rejects_invalid_artifact_instead_of_empty_success(tmp_path, document, _integrity_forbid_scoring):
    artifact = tmp_path / 'invalid.json'
    artifact.write_text(json.dumps(document))
    original = artifact.read_bytes()
    with pytest.raises(SystemExit, match='prophet_postmortem/v1'):
        pp.main(['--root', str(tmp_path), '--cohort-integrity-only', '--artifact', str(artifact)])
    assert artifact.read_bytes() == original


def test_integrity_recorded_zero_buy_date_is_coverage_not_source_absence(tmp_path):
    _integrity_write_ledger(tmp_path, [{'as_of': '2026-07-01', 'ticker': 'AAA', 'lane': 'watch', 'rank_by': 'era'}], [{'as_of': '2026-07-01', 'rank_by': 'era', 'buy': [{'ticker': 'AAA'}]}])
    block = pp._cohort_integrity_block(tmp_path, [], as_of="2026-07-01",
                                       include_era_rates=False)
    sources = block['sources']
    assert sources['n_overlap_dates'] == 1
    assert sources['n_overlap_dates_with_membership_difference'] == 1
    assert sources['membership_on_overlap_dates'][0]['only_in'] == {'retro': [], 'snapshot': ['AAA']}
    _integrity_write_ledger(tmp_path, [{'as_of': '2026-07-01', 'ticker': 'AAA', 'lane': 'buy', 'rank_by': 'era'}], [{'as_of': '2026-07-01', 'rank_by': 'era', 'buy': []}])
    block = pp._cohort_integrity_block(tmp_path, [], as_of="2026-07-01",
                                       include_era_rates=False)
    assert block['sources']['n_overlap_dates'] == 1
    assert block['sources']['membership_on_overlap_dates'][0]['only_in'] == {'retro': ['AAA'], 'snapshot': []}


def test_integrity_incomplete_source_never_emits_per_era_rates(tmp_path, monkeypatch):
    directory = tmp_path / 'data/us_board_ledger'
    directory.mkdir(parents=True)
    (directory / 'retro_grades.parquet').write_bytes(b'not parquet')
    (directory / 'snapshots.jsonl').write_text(json.dumps({'as_of': '2026-07-01', 'rank_by': 'observed-era', 'buy': [{'ticker': 'AAA'}]}) + '\n')
    def no_aggregate(*args, **kwargs):
        raise AssertionError('Incomplete original sources cannot produce per-era rates')
    monkeypatch.setattr(pm, 'aggregate', no_aggregate)
    block = pp._cohort_integrity_block(tmp_path, [_integrity_graded_row('AAA', '2026-07-01')],
                                       as_of='2026-07-01')
    assert 'per_era' not in block
    assert block['per_era_unavailable_reason'] == 'original_membership_source_incomplete'
    assert block['source_validation']['state'] == 'incomplete'
    assert block['episodes'][0]['partition'] == 'single'  # available-source observation only


@pytest.mark.parametrize('buy_rows', [{}, None, [None], [{}]])
def test_integrity_invalid_membership_is_disclosed_and_blocks_rates(tmp_path, monkeypatch, buy_rows):
    _integrity_write_ledger(tmp_path, [
        {'as_of': '2026-07-01', 'ticker': 'AAA', 'lane': 'buy', 'rank_by': 'era'},
        {'as_of': '2026-07-01', 'ticker': None, 'lane': 'buy', 'rank_by': 'era'},
    ], [{'as_of': '2026-07-01', 'rank_by': 'era', 'buy': buy_rows}])
    def no_aggregate(*args, **kwargs):
        raise AssertionError('Malformed original membership cannot produce per-era rates')
    monkeypatch.setattr(pm, 'aggregate', no_aggregate)
    block = pp._cohort_integrity_block(tmp_path, [_integrity_graded_row('AAA', '2026-07-01')],
                                       as_of='2026-07-01')
    assert block['sources_read']['retro']['n_invalid_membership_records'] == 1
    assert block['sources_read']['snapshot']['n_invalid_membership_records'] == 1
    assert block['source_validation']['state'] == 'incomplete'
    assert block['per_era_unavailable_reason'] == 'original_membership_source_incomplete'
    assert 'per_era' not in block


def test_integrity_unreadable_snapshot_encoding_is_explicit_incomplete(tmp_path, monkeypatch):
    _integrity_write_ledger(tmp_path, [
        {'as_of': '2026-07-01', 'ticker': 'AAA', 'lane': 'buy', 'rank_by': 'era'},
    ], [])
    snapshot = tmp_path / 'data/us_board_ledger/snapshots.jsonl'
    snapshot.write_bytes(b'\xff\n')
    before = snapshot.read_bytes()
    def no_aggregate(*args, **kwargs):
        raise AssertionError('Unreadable original source cannot produce rates')
    monkeypatch.setattr(pm, 'aggregate', no_aggregate)
    block = pp._cohort_integrity_block(tmp_path, [_integrity_graded_row('AAA', '2026-07-01')],
                                       as_of='2026-07-01')
    assert block['sources_read']['snapshot']['readable'] is False
    assert block['sources_read']['snapshot']['error'].startswith('UnicodeDecodeError:')
    assert block['source_validation']['state'] == 'incomplete'
    assert 'per_era' not in block
    assert snapshot.read_bytes() == before


# ===========================================================================
# 12. Q02/B22 time-cut + source-integrity repair (frozen as_of, gaps, strict dates)
# ===========================================================================
def test_future_source_disagreement_cannot_withhold_cut_era_description():
    retro = {"2026-07-01": {"AAA": ["era"]},
             "2026-08-10": {"AAA": ["later-a", "later-b"]}}
    snapshot = {"2026-07-01": {"AAA": ["era"]},
                "2026-08-10": {"BBB": ["other"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snapshot),
            [_integrity_graded_row("AAA", "2026-07-01")], as_of="2026-07-31")
    assert block["membership_conflict_free"] is True
    assert block["per_era"]["era"]["aggregate"]["n_episodes"] == 1
    assert block["as_of_cut"]["dates_after_cut"] == ["2026-08-10"]


def test_future_duplicate_snapshot_conflict_cannot_withhold_cut_description(tmp_path):
    _integrity_write_ledger(tmp_path, [
        {"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy", "rank_by": "era"},
    ], [
        {"as_of": "2026-07-01", "rank_by": "era", "buy": [{"ticker": "AAA"}]},
        {"as_of": "2026-08-10", "rank_by": "later-a", "buy": [{"ticker": "AAA"}]},
        {"as_of": "2026-08-10", "rank_by": "later-b", "buy": [{"ticker": "BBB"}]},
    ])
    block = pp._cohort_integrity_block(tmp_path,
            [_integrity_graded_row("AAA", "2026-07-01")], as_of="2026-07-31")
    assert block["sources_read"]["snapshot"]["n_conflicting_duplicate_observations"] == 1
    assert block["source_validation"]["state"] == "complete"
    assert block["per_era"]["era"]["aggregate"]["n_episodes"] == 1


def test_membership_after_frozen_cut_cannot_assign_conflict_or_mixed():
    retro = {"2026-07-01": {"AAA": ["v1"]}, "2026-08-10": {"AAA": ["v2"]}}
    row = _integrity_graded_row("AAA", "2026-07-01")
    before = copy.deepcopy(row)
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), [row],
                                      as_of="2026-07-31")
    a = block["episodes"][0]
    assert a["partition"] == "single" and a["stamp"] == "v1"
    assert a["observed_gap"] is None
    assert a["as_of"] == "2026-07-31"
    cut = block["as_of_cut"]
    assert cut["as_of"] == "2026-07-31"
    assert cut["n_membership_records_after_cut"] == 1
    assert cut["dates_after_cut"] == ["2026-08-10"]
    assert block["per_era"]["v1"]["aggregate"]["n_episodes"] == 1
    assert "v2" not in block["per_era"]
    assert row == before


def test_frozen_cut_removes_the_false_later_readmission_mix_bkr_shape():
    # The reproduced counterexample, in miniature: BKR admitted 07-27 under v1,
    # absent from every source while the board continued, then re-admitted 09-25
    # under a later stamp. With the cut at the artifact's own as_of the later
    # vintage never reaches the episode: single, not mixed.
    retro = {
        "2026-07-27": {"BKR": ["v1"], "AAA": ["v1"]},
        "2026-09-20": {"AAA": ["v1"]},
        "2026-09-25": {"BKR": ["v2"], "AAA": ["v1"]},
    }
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro),
                                      [_integrity_ep("BKR", "2026-07-27")],
                                      as_of="2026-07-31")
    a = block["episodes"][0]
    assert a["partition"] == "single" and a["stamp"] == "v1"
    assert a["stamps"] == ["v1"]
    assert a["observed_gap"] is None
    assert block["as_of_cut"]["dates_after_cut"] == ["2026-09-20", "2026-09-25"]
    assert block["as_of_cut"]["n_membership_records_after_cut"] == 3


def test_bkr_later_readmission_beyond_the_cut_is_gap_split_never_absorbed():
    # Same sources, inspected at a LATER as_of: the re-admission is inside the
    # window, so contiguity does the work the cut did — the first recorded date
    # absent from ALL sources is a genuine gap, and the 09-25 stamp belongs to the
    # later admission, never to the earlier episode.
    retro = {
        "2026-07-27": {"BKR": ["v1"], "AAA": ["v1"]},
        "2026-09-20": {"AAA": ["v1"]},
        "2026-09-25": {"BKR": ["v2"], "AAA": ["v1"]},
    }
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro),
                                      [_integrity_ep("BKR", "2026-07-27")],
                                      as_of="2026-09-30")
    a = block["episodes"][0]
    assert a["stamps"] == ["v1"]
    assert a["stamp"] == "v1"
    assert a["observed_gap"]["date"] == "2026-09-20"
    assert a["observed_gap"]["n_records_after_gap_excluded"] == 1
    assert a["observed_gap"]["dates_after_gap"] == ["2026-09-25"]
    # affected attribution can never enter the per-era summaries
    assert a["partition"] == "partial"
    assert block["per_era"] == {}


def test_gap_inside_a_closed_window_excludes_later_reentry_and_discloses_it():
    retro = {"2026-07-01": {"AAA": ["v1"]},
             "2026-07-05": {"BBB": ["v1"]},
             "2026-07-08": {"AAA": ["v2"]}}
    ep = _integrity_ep("AAA", "2026-07-01", "2026-07-10")
    before = copy.deepcopy(ep)
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), [ep],
                                      as_of="2026-07-10")
    a = block["episodes"][0]
    assert a["observed_gap"]["date"] == "2026-07-05"
    assert a["observed_gap"]["n_records_after_gap_excluded"] == 1
    assert a["stamps"] == ["v1"] and a["partition"] == "partial"
    assert ep == before
    # disclosure, not deletion: the receipt still counts every original record
    assert block["sources"]["sources"]["retro"]["n_membership_records"] == 3


def test_a_date_no_source_recorded_is_never_an_inferred_gap():
    retro = {"2026-07-01": {"AAA": ["v1"]}, "2026-07-04": {"AAA": ["v1"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-10")
    a = block["episodes"][0]
    assert a["observed_gap"] is None
    assert a["partition"] == "single" and a["stamp"] == "v1"


def test_absence_from_one_source_alone_is_coverage_not_a_gap():
    retro = {"2026-07-01": {"AAA": ["v1"]}}
    snap = {"2026-07-02": {"AAA": ["v1"]}}
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap),
                                      [_integrity_ep("AAA", "2026-07-01", "2026-07-10")],
                                      as_of="2026-07-02")
    a = block["episodes"][0]
    assert a["observed_gap"] is None
    assert a["partition"] == "single"


@pytest.mark.parametrize("bad", [
    "2026-7-31", "2026-13-01", "2026-02-30", "20260731", "2026-07-31T00:00:00",
    "not-a-date", "", " 2026-07-01", "2026-07-31 ", None, 20260731, 31.0,
])
def test_engine_refuses_any_non_canonical_iso_as_of(bad):
    with pytest.raises(ValueError):
        pm.integrity_assignments({}, [], as_of=bad)
    with pytest.raises(ValueError):
        pm.cohort_integrity_block({}, [], as_of=bad)


def test_engine_refuses_malformed_membership_date_keys_instead_of_lexical_compare():
    with pytest.raises(ValueError):
        pm.integrity_assignments({"retro": {"2026/07/01": {"AAA": ["v1"]}}},
                                 [], as_of="2026-07-01")
    with pytest.raises(ValueError):
        pm.integrity_assignments({"retro": {"nan": {"AAA": ["v1"]}}},
                                 [], as_of="2026-07-01")


@pytest.mark.parametrize("bad_exit", ["2026-13-99", "2026-1-1", float("nan"),
                                      20260731, ""])
def test_invalid_board_exit_is_explicit_unavailability_never_a_window_bound(bad_exit):
    retro = {"2026-07-01": {"AAA": ["v1"]}, "2026-07-05": {"AAA": ["v2"]}}
    block = pm.cohort_integrity_block(
        _integrity_mem(retro=retro),
        [_integrity_ep("AAA", "2026-07-01", bad_exit)],
        as_of="2026-07-31")
    a = block["episodes"][0]
    assert a["partition"] is None and a["identity_error"]
    assert block["n_episodes_unavailable"] == 1
    assert block["partitions"]["mixed"]["n_episodes"] == 0


def test_nan_exit_is_not_treated_as_the_open_sentinel():
    retro = {"2026-07-01": {"AAA": ["v1"]}, "2026-07-05": {"AAA": ["v2"]}}
    block = pm.cohort_integrity_block(
        _integrity_mem(retro=retro),
        [_integrity_ep("AAA", "2026-07-01", float("nan"))],
        as_of="2026-07-31")
    a = block["episodes"][0]
    assert a["unavailable"] is True
    assert "NaN" in a["identity_error"]


def test_one_source_receipt_never_claims_overlap_or_disagreement():
    rec = pm.integrity_source_receipt(
        {"retro": {"2026-07-01": {"AAA": ["v1"]}, "2026-07-02": {"BBB": ["v1"]}}})
    assert rec["overlap_dates"] == []
    assert rec["n_overlap_dates"] == 0
    assert rec["n_overlap_dates_with_membership_difference"] == 0
    assert rec["membership_on_overlap_dates"] == []
    assert rec["dates_in_one_source_only"] == ["2026-07-01", "2026-07-02"]
    assert rec["per_source_only_dates"] == {"retro": ["2026-07-01", "2026-07-02"]}
    assert rec["within_source_stamp_disagreements"] == []
    assert rec["n_within_source_stamp_disagreements"] == 0


def test_within_source_horizon_disagreement_on_a_disjoint_date_is_published():
    retro = {"2026-06-15": {"AAA": ["v1", "v2"]}, "2026-07-20": {"BBB": ["v1"]}}
    snap = {"2026-07-21": {"CCC": ["v1"]}}
    rows = [_integrity_graded_row("AAA", "2026-06-15", exit_="2026-06-16")]
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro, snap=snap), rows,
                                      as_of="2026-07-21")
    rec = block["sources"]
    # the two sources share NO date, yet the within-source conflict is still published
    assert rec["overlap_dates"] == []
    assert rec["n_overlap_dates_with_membership_difference"] == 0
    assert rec["within_source_stamp_disagreements"] == [
        {"source": "retro", "date": "2026-06-15", "ticker": "AAA", "stamps": ["v1", "v2"]}]
    assert block["episodes"][0]["partition"] == "conflict"
    # conflicting original membership blocks clean rates
    assert block["membership_conflict_free"] is False
    assert "per_era" not in block
    assert block["per_era_unavailable_reason"] == "conflicting_original_membership"


def test_duplicate_same_date_snapshot_docs_with_differing_stamps_block_rates(tmp_path):
    _integrity_write_ledger(tmp_path, [], [
        {"as_of": "2026-07-01", "rank_by": "v1", "buy": [{"ticker": "AAA"}]},
        {"as_of": "2026-07-01", "rank_by": "v2", "buy": [{"ticker": "AAA"}]},
    ])
    block = pp._cohort_integrity_block(
        tmp_path, [_integrity_graded_row("AAA", "2026-07-01")],
        as_of="2026-07-01")
    st = block["sources_read"]["snapshot"]
    assert st["n_duplicate_as_of_docs"] == 1
    assert st["n_conflicting_duplicate_observations"] == 1
    assert block["source_validation"]["state"] == "incomplete"
    assert "per_era" not in block
    # both original records stay counted; the same-source disagreement conflicts
    assert block["episodes"][0]["n_membership_records"] == 2
    assert block["episodes"][0]["partition"] == "conflict"


def test_identical_duplicate_snapshot_docs_are_disclosed_without_invented_conflict(tmp_path):
    doc = {"as_of": "2026-07-01", "rank_by": "v1", "buy": [{"ticker": "AAA"}]}
    _integrity_write_ledger(
        tmp_path,
        [{"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy", "rank_by": "v1"}],
        [doc, doc])
    block = pp._cohort_integrity_block(
        tmp_path, [_integrity_graded_row("AAA", "2026-07-01")],
        as_of="2026-07-01")
    st = block["sources_read"]["snapshot"]
    assert st["n_duplicate_as_of_docs"] == 1
    assert st["n_conflicting_duplicate_observations"] == 0
    assert block["source_validation"]["state"] == "complete"
    assert block["episodes"][0]["partition"] == "single"
    assert block["per_era"]["v1"]["aggregate"]["n_matured"] == 1


def test_missing_rank_by_column_is_a_warning_and_missing_attribution(tmp_path):
    ledger = tmp_path / "data" / "us_board_ledger"
    ledger.mkdir(parents=True)
    pd.DataFrame([{"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy"}]).to_parquet(
        ledger / "retro_grades.parquet", index=False)
    with (ledger / "snapshots.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"as_of": "2026-07-01", "rank_by": "snap-era",
                             "buy": []}) + "\n")
    block = pp._cohort_integrity_block(
        tmp_path, [_integrity_graded_row("AAA", "2026-07-01")],
        as_of="2026-07-01")
    rs = block["sources_read"]["retro"]
    assert rs["readable"] is True and rs["rank_by_column_present"] is False
    assert rs["n_missing_stamp_records"] == 1
    assert any("rank_by" in w for w in block["warnings"])
    # read/schema integrity is fine; the missing STAMP is attribution, not a bad read
    assert block["source_validation"]["state"] == "complete"
    assert block["episodes"][0]["partition"] == "unassigned"


def test_loaders_disclose_malformed_dates_and_invalid_tickers(tmp_path):
    ledger = tmp_path / "data" / "us_board_ledger"
    ledger.mkdir(parents=True)
    pd.DataFrame([
        {"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy", "rank_by": "v1"},
        {"as_of": "07/02/2026", "ticker": "AAA", "lane": "buy", "rank_by": "v1"},
        {"as_of": "2026-07-01", "ticker": None, "lane": "buy", "rank_by": "v1"},
    ]).to_parquet(ledger / "retro_grades.parquet", index=False)
    memberships, status = pp.load_retro_membership(tmp_path)
    assert memberships == {"2026-07-01": {"AAA": ["v1"]}}
    assert status["n_malformed_dates"] == 1
    assert status["n_invalid_membership_records"] == 1
    assert status["n_buy_records"] == 1


def test_retro_timestamp_as_of_keys_are_converted_never_stringified(tmp_path):
    ledger = tmp_path / "data" / "us_board_ledger"
    ledger.mkdir(parents=True)
    pd.DataFrame([{"as_of": pd.Timestamp("2026-07-01"), "ticker": "AAA",
                   "lane": "buy", "rank_by": "v1"}]).to_parquet(
        ledger / "retro_grades.parquet", index=False)
    memberships, status = pp.load_retro_membership(tmp_path)
    assert status["readable"] is True
    assert memberships == {"2026-07-01": {"AAA": ["v1"]}}
    assert status["n_malformed_dates"] == 0


def test_inspection_refuses_invalid_as_of_and_malformed_identity_rows(
        tmp_path, _integrity_forbid_scoring):
    art = tmp_path / "artifact.json"
    good_row = {"ticker": "AAA", "entry_date": "2026-07-01",
                "board_exit_date": None, "maturity": "matured"}
    cases = [
        {"schema": pp.SCHEMA, "as_of": "2026-7-1", "episodes": [dict(good_row)]},
        {"schema": pp.SCHEMA, "as_of": None, "episodes": [dict(good_row)]},
        {"schema": pp.SCHEMA, "as_of": "2026-07-01",
         "episodes": [{**good_row, "entry_date": "2026-07-99"}]},
        {"schema": pp.SCHEMA, "as_of": "2026-07-01",
         "episodes": [{**good_row, "board_exit_date": "07/10/2026"}]},
        {"schema": pp.SCHEMA, "as_of": "2026-07-01", "episodes": []},
        {"schema": pp.SCHEMA, "as_of": "2026-07-01", "episodes": [None]},
        {"schema": pp.SCHEMA, "as_of": "2026-07-01",
         "episodes": [{**good_row, "ticker": ""}]},
        [1, 2],
    ]
    for document in cases:
        art.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(SystemExit):
            pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                     "--artifact", str(art)])
        assert art.read_bytes()   # refused, never rewritten or removed


def test_inspection_refuses_undecodable_artifact_bytes(tmp_path, _integrity_forbid_scoring):
    art = tmp_path / "artifact.json"
    art.write_bytes(b"\xff\xfe\x00 not utf-8")
    with pytest.raises(SystemExit):
        pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                 "--artifact", str(art)])
    art.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit):
        pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                 "--artifact", str(art)])


def test_artifact_flag_without_integrity_only_is_refused_before_generation(
        tmp_path, _integrity_forbid_scoring):
    art = tmp_path / "artifact.json"
    art.write_text(json.dumps({
        "schema": pp.SCHEMA, "as_of": "2026-07-01",
        "episodes": [{"ticker": "AAA", "entry_date": "2026-07-01",
                      "board_exit_date": None, "maturity": "matured"}]}), encoding="utf-8")
    # build_rows is forbidden by the fixture: reaching the generation path would
    # raise AssertionError, not SystemExit — the refusal must happen BEFORE it.
    with pytest.raises(SystemExit):
        pp.main(["--root", str(tmp_path), "--artifact", str(art)])


@pytest.mark.parametrize("extra", [
    ["--out", "x.json"], ["--report-dir", "r"], ["--dry-run"], ["--horizon", "5"],
])
def test_integrity_only_refuses_incompatible_generation_flags(
        tmp_path, _integrity_forbid_scoring, extra):
    with pytest.raises(SystemExit):
        pp.main(["--root", str(tmp_path), "--cohort-integrity-only"] + extra)


def test_full_input_byte_immutability_including_us_board_ledger(
        tmp_path, capsys, _integrity_forbid_scoring):
    _integrity_write_ledger(
        tmp_path,
        [{"as_of": "2026-07-01", "ticker": "AAA", "lane": "buy", "horizon": 10,
          "rank_by": "v1"}],
        [{"as_of": "2026-07-01", "rank_by": "v1", "buy": [{"ticker": "AAA"}]}])
    art = tmp_path / "summary.json"
    art.write_text(json.dumps({
        "schema": pp.SCHEMA, "as_of": "2026-07-01",
        "episodes": [{"ticker": "AAA", "entry_date": "2026-07-01",
                      "board_exit_date": "2026-07-04", "maturity": "matured"}]}),
        encoding="utf-8")

    def snapshot_all() -> dict:
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(tmp_path.rglob("*")) if p.is_file()}

    before = snapshot_all()
    assert pp.main(["--root", str(tmp_path), "--cohort-integrity-only",
                    "--artifact", str(art)]) == 0
    assert snapshot_all() == before    # inputs AND artifact, byte for byte
    json.loads(capsys.readouterr().out)


def test_per_era_wrappers_carry_descriptive_only_and_no_promotion_authority():
    retro = {"2026-07-01": {"AAA": ["v1"]}}
    rows = [_integrity_graded_row("AAA", "2026-07-01", outcome=-10.0, excess=-9.0,
                                  exit_="2026-07-02")]
    block = pm.cohort_integrity_block(_integrity_mem(retro=retro), rows,
                                      as_of="2026-07-02")
    era = block["per_era"]["v1"]
    assert era["descriptive_only"] is True
    assert era["promotion_authority"].startswith("none")
    assert era["aggregate"]["n_episodes"] == 1          # legacy behavior underneath
    assert era["aggregate"]["n_matured"] == 1


def test_integrity_duplicate_identity_is_explicit_without_row_loss():
    rows = [_integrity_graded_row("AAA", "2026-07-01"),
            _integrity_graded_row("AAA", "2026-07-01")]
    rows[1]["horizon"] = 20
    block = pm.cohort_integrity_block(_integrity_mem(retro={"2026-07-01": {"AAA": ["v1"]}}), rows, as_of="2026-07-02")
    assert block["n_episode_rows"] == 2
    assert block["n_episodes"] == sum(x["n_episodes"] for x in block["partitions"].values()) == 0
    assert block["n_episodes_unavailable"] == 2
    assert {a["episode_row_index"] for a in block["episodes"]} == {0, 1}
    assert all(a["unavailable_reason"] == "ambiguous_episode_identity" for a in block["episodes"])
    assert "per_era" not in block


@pytest.mark.parametrize("entry,exit_,reason", [
    ("2026-08-05", None, "episode_entry_after_cut"),
    ("2026-07-02", "2026-07-01", "invalid_episode_interval"),
    ("2026-07-02", "2026-07-02", "invalid_episode_interval"),
])
def test_integrity_invalid_interval_is_not_missing_attribution(entry, exit_, reason):
    block = pm.cohort_integrity_block({}, [_integrity_ep("AAA", entry, exit_)], as_of="2026-07-31")
    assert block["n_episode_rows"] == block["n_episodes_unavailable"] == 1
    assert block["n_episodes"] == 0
    assert block["episodes"][0]["unavailable_reason"] == reason


@pytest.mark.parametrize("rows", [
    [{"ticker": "AAA", "entry_date": "2026-08-05", "board_exit_date": None}],
    [{"ticker": "AAA", "entry_date": "2026-07-02", "board_exit_date": "2026-07-01"}],
    [{"ticker": "AAA", "entry_date": "2026-07-02", "board_exit_date": "2026-07-02"}],
    [{"ticker": "AAA", "entry_date": "2026-07-01", "board_exit_date": None}] * 2,
])
def test_inspection_refuses_ambiguous_or_incoherent_episodes_without_effects(tmp_path, _integrity_forbid_scoring, rows):
    art = tmp_path / "artifact.json"
    raw = json.dumps({"schema": pp.SCHEMA, "as_of": "2026-07-31", "episodes": rows}).encode()
    art.write_bytes(raw)
    with pytest.raises(SystemExit):
        pp.main(["--root", str(tmp_path), "--cohort-integrity-only", "--artifact", str(art)])
    assert art.read_bytes() == raw


@pytest.mark.parametrize("value", [pd.NaT, pd.Timestamp("NaT"), None, pd.NA, float("nan")])
def test_integrity_source_null_date_rejected_before_native_date(value):
    assert pp._iso_date_key(value) is None


def test_integrity_nonobject_row_retained_unavailable():
    block = pm.cohort_integrity_block({}, [None], as_of="2026-07-31")
    assert block["n_episode_rows"] == block["n_episodes_unavailable"] == 1
    assert block["episodes"][0]["unavailable_reason"] == "malformed_episode_identity"


def test_integrity_overlapping_episode_intervals_are_ambiguous():
    rows = [_integrity_ep("AAA", "2026-07-01", "2026-07-05"), _integrity_ep("AAA", "2026-07-03")]
    block = pm.cohort_integrity_block({}, rows, as_of="2026-07-04")
    assert block["n_episodes_unavailable"] == 2
    assert all(a["unavailable_reason"] == "overlapping_episode_intervals" for a in block["episodes"])


def test_integrity_adjacent_episode_intervals_keep_distinct_rows():
    rows = [_integrity_ep("AAA", "2026-07-01", "2026-07-03"), _integrity_ep("AAA", "2026-07-03")]
    block = pm.cohort_integrity_block({}, rows, as_of="2026-07-04")
    assert block["n_episode_rows"] == block["n_episodes"] == 2
    assert block["n_episodes_unavailable"] == 0


def test_retro_nat_is_malformed_source_not_clean_absence(tmp_path):
    ledger = tmp_path / "data" / "us_board_ledger"
    ledger.mkdir(parents=True)
    pd.DataFrame([
        {"as_of": pd.Timestamp("2026-07-01"), "ticker": "AAA", "lane": "buy", "rank_by": "v1"},
        {"as_of": pd.NaT, "ticker": "AAA", "lane": "buy", "rank_by": "v1"},
    ]).to_parquet(ledger / "retro_grades.parquet", index=False)
    memberships, status = pp.load_retro_membership(tmp_path)
    assert memberships == {"2026-07-01": {"AAA": ["v1"]}}
    assert status["n_malformed_dates"] == 1
    block = pp._cohort_integrity_block(tmp_path, [_integrity_ep("AAA", "2026-07-01")], as_of="2026-07-01", include_era_rates=False)
    assert block["source_validation"]["state"] == "incomplete"
