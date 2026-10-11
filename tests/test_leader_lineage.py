"""Lineage descriptor: failed leadership versus deep corrective continuation (synthetic, PIT, read-only)."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

import engine.leader_lineage as mod
from engine.leader_lineage import (AUTHORITY, LADDER, LineageSpec, describe_lineage, replay_lineage)

SPEC = LineageSpec(high_window=120, fast_window=10, slow_window=40, rs_window=5, confirm_sessions=3,
                   higher_low_sessions=5, structural_below_slow=20, horizon_sessions=60)
RISE = list(np.linspace(50, 100, 130))            # 130 sessions: qualifies once n > high_window
CRASH = [97, 94, 91, 88, 85, 82, 79, 76, 73, 70, 67]   # -33% close drawdown, PLTR-shaped
END = "2026-10-09"


def series(tail=(), bench=None, end=END):
    values = np.asarray(list(RISE) + list(tail), dtype=float)
    idx = pd.bdate_range(end=end, periods=len(values))
    close = pd.Series(values, index=idx)
    benchmark = pd.Series(100.0 if bench is None else np.asarray(bench, dtype=float), index=idx)
    return close, benchmark


def peers_for(close):
    return {"P1": pd.Series(100.0, index=close.index), "P2": pd.Series(100.0, index=close.index)}


def run(close, benchmark, **kw):
    return replay_lineage(close, benchmark, as_of=kw.pop("as_of", close.index[-1].date()),
                          sessions=kw.pop("sessions", list(close.index.date)), spec=SPEC, **kw)


def first_row(rows, **conds):
    for row in rows:
        if all(row.get(k) == v for k, v in conds.items()):
            return row
    raise AssertionError(f"no row matching {conds}")


# ---------------------------------------------------------------------------- T1 deep stay then repair
def test_pltr_shaped_deep_stay_is_structural_until_the_ordered_ladder_repairs_it():
    tail = CRASH + [68] * 65 + list(np.linspace(69, 98, 25))
    c, b = series(tail)
    rows = run(c, b, ticker="PLTR", peers=peers_for(c))
    damaged = first_row(rows, state="DAMAGED")
    ep = damaged["episode"]
    assert damaged["thesis_state"] == "DAMAGED" and damaged["setup_state"] == "RESET"
    assert ep["correction_peak_price"] == 100.0 and ep["leadership_qualified_at"] < ep["correction_peak_on"]
    # trough and drawdown frozen at the deepest close, RS peak-to-trough on the ratio basis
    trough = rows[len(RISE) + len(CRASH) - 1]["episode"]
    assert trough["correction_trough_price"] == 67.0 and trough["max_close_drawdown"] == pytest.approx(-0.33)
    assert trough["rs_peak_to_trough"] == pytest.approx(-0.33)
    # long stay below the slow average -> structural break at the frozen horizon, thesis CONTRADICTED with named evidence
    structural = first_row(rows, break_class="STRUCTURAL_BREAK")
    sep = structural["episode"]
    assert sep["sessions_below_200"]["consecutive_max"] >= SPEC.structural_below_slow
    assert sep["structural_on"] is not None and sep["ladder"]["reclaim_200d_on"] is None
    assert structural["thesis_state"] == "CONTRADICTED"
    assert structural["contradiction_evidence"] == ["structural_break_no_slow_reclaim_by_horizon"]
    assert sep["revisable"] is True and sep["revision_requires"]
    # the ordered ladder then repairs the trend; the verdict is revised, never erased
    last = rows[-1]
    lep = last["episode"]
    lad = lep["ladder"]
    assert last["state"] == "REPAIRED" and last["break_class"] == "REPAIRED_TREND"
    assert lep["revised_from"] == "STRUCTURAL_BREAK" and lep["revised_on"] == lad["rs_vs_peer_basket_rising_on"]
    assert (lad["higher_low_confirmed_on"] < lad["reclaim_50d_on"] < lad["reclaim_200d_on"]
            <= lad["rs_vs_spy_rising_on"])
    assert lad["rs_vs_peer_basket_rising_on"] is not None
    assert last["setup_state"] == "RE_IGNITION"
    assert last["thesis_state"] == "UNKNOWN"          # no owner-dated fundamentals: never rendered healthy
    assert lep["structural_watch"] is False and lep["failed_on"] is None
    # price recovered to 98 < 100: ATHs persist separately and are not reclaimed
    assert last["price_ath"] == 100.0 and last["rs_ath"] == 1.0
    # the shallow-lane names are not touched: the episode never left the single deep episode
    assert len({r["episode"]["episode_id"] for r in rows if r["episode"]}) == 1


def test_owner_dated_stabilisation_makes_the_repaired_thesis_intact_and_fills_r5():
    tail = CRASH + [68] * 65 + list(np.linspace(69, 98, 25))
    c, b = series(tail)
    stab_day = c.index[len(RISE) + len(CRASH) + 65].date().isoformat()
    rows = run(c, b, ticker="PLTR", peers=peers_for(c),
               fundamentals=[{"as_of": stab_day, "state": "STABILIZED", "source_ref": "owner:revisions#1"}])
    last = rows[-1]
    assert last["state"] == "REPAIRED" and last["thesis_state"] == "INTACT"
    assert last["episode"]["ladder"]["revisions_news_stabilized_on"] == stab_day
    assert last["episode"]["fundamental_deterioration"] == {"state": "NONE", "source_ref": "owner:revisions#1",
                                                             "as_of": stab_day}
    # before the owner row's date the same history reads UNKNOWN (never back-dated)
    before = rows[len(RISE) + len(CRASH) + 60]
    assert before["episode"]["fundamental_deterioration"]["state"] == "UNKNOWN"


# ---------------------------------------------------------------------------- T2 failed repair
def test_failed_break_after_reclaim_is_invalidated_but_revisable_and_only_contradicted_with_evidence():
    tail = CRASH + [68] * 12 + [76] * 4 + [60] + [61] * 3
    c, b = series(tail)
    rows = run(c, b, ticker="X", peers=peers_for(c))
    r2 = first_row(rows, setup_state="REBUILDING")
    assert r2["episode"]["ladder"]["higher_low_confirmed_on"] is not None
    reclaimed = [r for r in rows if r["episode"] and r["episode"]["ladder"]["reclaim_50d_on"]]
    assert reclaimed and reclaimed[0]["episode"]["repair_floor_price"] == 67.0
    failed = first_row(rows, state="FAILED")
    assert failed["break_class"] == "FAILED_BREAK" and failed["setup_state"] == "INVALIDATED"
    assert failed["thesis_state"] == "DAMAGED" and failed["contradiction_evidence"] == []
    assert failed["episode"]["failed_on"] == failed["as_of"] and failed["price"] == 60.0
    assert failed["episode"]["revisable"] is True
    assert rows[-1]["state"] == "FAILED"      # no silent relabel after the break
    # owner-sourced deterioration is the only other route to CONTRADICTED
    rows2 = run(c, b, ticker="X", peers=peers_for(c),
                fundamentals=[{"as_of": failed["as_of"], "state": "PRESENT", "source_ref": "owner:guide-cut"}])
    last = rows2[-1]
    assert last["thesis_state"] == "CONTRADICTED"
    assert last["contradiction_evidence"] == ["fundamental_deterioration_present"]
    assert last["setup_state"] == "INVALIDATED"


# ---------------------------------------------------------------------------- T3 shallow reset is not a deep episode
def test_shallow_reset_never_opens_the_deep_phase():
    tail = [98, 96, 94, 92, 94, 96, 98, 100, 102, 104]
    c, b = series(tail)
    rows = run(c, b, ticker="AVGO", peers=peers_for(c))
    states = {r["state"] for r in rows[len(RISE):]}
    assert states == {"ACTIVE"}
    ep = rows[-1]["episode"]
    assert ep["max_close_drawdown"] == pytest.approx(-0.08)
    assert ep["correction_peak_price"] is None and ep["correction_trough_price"] is None
    assert ep["sessions_below_50"]["total"] == 0 and ep["sessions_below_200"]["total"] == 0
    assert ep["break_class"] == "UNRESOLVED" and rows[-1]["setup_state"] == "WATCH"
    assert rows[-1]["price_ath"] == 104.0 and rows[-1]["price_ath"] == ep["price_ath"]


def test_module_imports_no_incumbent_lane_and_carries_no_authority():
    tree = ast.parse(inspect.getsource(mod))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(name.startswith("engine") or name.startswith("scripts") for name in imported), imported
    assert set(AUTHORITY) == {"may_rank", "may_gate", "may_size", "may_trade", "may_alert"}
    assert not any(AUTHORITY.values())


# ---------------------------------------------------------------------------- T4 price ATH vs RS ATH persist separately
def test_price_ath_reclaim_does_not_imply_rs_ath_reclaim():
    tail = [90, 80, 70] + list(np.linspace(72, 110, 30))
    bench = [100.0] * (len(RISE) + 3) + list(np.linspace(102, 160, 30))
    c, b = series(tail, bench=bench)
    rows = run(c, b, ticker="Y")
    last = rows[-1]
    ep = last["episode"]
    assert ep["price_ath"] == 110.0 and ep["price_ath_on"] == last["as_of"]
    assert ep["rs_ath"] == 1.0 and ep["rs_ath_on"] == c.index[len(RISE) - 1].date().isoformat()
    assert ep["price_ath_on"] > ep["rs_ath_on"]
    assert last["rs"] == pytest.approx(110 / 160)
    assert last["state"] in ("DAMAGED",)       # RS still lagging: no new qualification was manufactured
    assert ep["correction_peak_price"] == 100.0 and ep["correction_trough_price"] == 70.0


# ---------------------------------------------------------------------------- T5 chronology is enforced
def test_out_of_order_rungs_are_recorded_as_violations_and_never_counted():
    tail = CRASH + [68] * 45 + [76, 76, 69, 76, 76, 76, 76, 76]
    c, b = series(tail)
    rows = run(c, b, ticker="Z", peers=peers_for(c))
    ep = rows[-1]["episode"]
    lad = ep["ladder"]
    violated = [v for v in ep["ladder_order_violations"] if v["rung"] == "reclaim_200d_on"]
    assert violated and violated[0]["missing"] == "reclaim_50d_on"
    assert lad["reclaim_50d_on"] is not None and lad["reclaim_200d_on"] is not None
    assert lad["reclaim_200d_on"] > lad["reclaim_50d_on"] > lad["higher_low_confirmed_on"]
    assert violated[0]["on"] < lad["reclaim_50d_on"]
    assert ep["break_class"] in ("UNRESOLVED", "REPAIRED_TREND") and ep["structural_on"] is None


def test_reclaim_before_a_higher_low_is_a_violation_not_a_rung():
    tail = CRASH + [80, 81, 82, 83, 84, 85, 86, 87]
    c, b = series(tail)
    rows = run(c, b, ticker="Q", peers=peers_for(c))
    ep = rows[-1]["episode"]
    early = [v for v in ep["ladder_order_violations"] if v["rung"] == "reclaim_50d_on"]
    assert early and early[0]["missing"] == "higher_low_confirmed_on"
    assert ep["ladder"]["reclaim_50d_on"] is None or ep["ladder"]["reclaim_50d_on"] > early[0]["on"]


# ---------------------------------------------------------------------------- T6 missing owners stall, never fabricate
def test_missing_owner_inputs_are_unknown_and_stall_the_ladder_without_a_verdict():
    tail = CRASH + [68] * 65 + list(np.linspace(69, 98, 25))
    c, b = series(tail)
    rows = run(c, b, ticker="PLTR")     # no peers, no fundamentals, no volume, no pivot
    last = rows[-1]
    ep = last["episode"]
    assert last["state"] == "DAMAGED" and last["break_class"] == "UNRESOLVED"
    assert ep["ladder_stalled"] == ["rs_vs_peer_basket_rising_on"]
    assert ep["revised_from"] == "STRUCTURAL_BREAK"        # the structural verdict was revised, not kept blindly
    assert last["thesis_state"] == "UNKNOWN" and last["setup_state"] == "REBUILDING"
    assert ep["rs_vs_peer_basket"] == "UNKNOWN"
    for rung in ("rs_vs_peer_basket_rising_on", "revisions_news_stabilized_on",
                 "volume_demand_confirmed_on", "pivot_confirmed_on"):
        assert ep["ladder"][rung] is None
    assert ep["fundamental_deterioration"] == {"state": "UNKNOWN", "source_ref": None}
    assert ep["distribution_evidence"]["state"] == "UNKNOWN" and ep["accumulation_evidence"]["state"] == "UNKNOWN"
    # undated or future-dated owner claims are ignored, never back-dated into the history
    rows2 = run(c, b, ticker="PLTR",
                fundamentals=[{"state": "PRESENT", "source_ref": "owner:undated"}],
                volume_demand=[{"as_of": "2030-01-01", "state": "ACCUMULATION", "source_ref": "owner:future"}],
                pivot={"confirmed_on": "2030-01-02"})
    ep2 = rows2[-1]["episode"]
    assert ep2["fundamental_deterioration"]["state"] == "UNKNOWN"
    assert ep2["accumulation_evidence"]["state"] == "UNKNOWN"
    assert ep2["ladder"]["volume_demand_confirmed_on"] is None and ep2["ladder"]["pivot_confirmed_on"] is None
    assert rows2[-1]["thesis_state"] == "UNKNOWN"


def test_owner_dated_volume_and_pivot_rows_are_projected_read_only():
    tail = CRASH + [68] * 20
    c, b = series(tail)
    day = c.index[-3].date().isoformat()
    rows = run(c, b, ticker="V", volume_demand=[{"as_of": day, "state": "ACCUMULATION", "source_ref": "owner:vol"}],
               pivot={"confirmed_on": day, "source": "#8649"})
    ep = rows[-1]["episode"]
    assert ep["accumulation_evidence"] == {"state": "PRESENT", "basis": {"source_ref": "owner:vol", "as_of": day}}
    assert ep["distribution_evidence"]["state"] == "ABSENT"
    assert ep["ladder"]["volume_demand_confirmed_on"] == day and ep["ladder"]["pivot_confirmed_on"] == day
    assert rows[-4]["episode"]["ladder"]["pivot_confirmed_on"] is None


# ---------------------------------------------------------------------------- T7 point in time
def test_a_later_close_never_alters_an_earlier_row():
    tail = CRASH + [68] * 65 + list(np.linspace(69, 98, 25))
    c, b = series(tail)
    fund = [{"as_of": c.index[-5].date().isoformat(), "state": "STABILIZED", "source_ref": "owner:late"}]
    full = run(c, b, ticker="PLTR", peers=peers_for(c), fundamentals=fund)
    dates = list(c.index.date)
    for cut in (len(RISE) + 5, len(RISE) + len(CRASH) + 30, len(dates) - 10, len(dates) - 1):
        part = replay_lineage(c, b, as_of=dates[cut], sessions=dates[:cut + 1], ticker="PLTR",
                              peers=peers_for(c), fundamentals=fund, spec=SPEC)
        assert part == full[:cut + 1]
    assert full[-6]["episode"]["fundamental_deterioration"]["state"] == "UNKNOWN"


def test_missing_session_is_a_gap_not_a_carried_value():
    tail = CRASH + [68] * 20
    c, b = series(tail)
    c2 = c.copy()
    c2.iloc[-8] = np.nan
    rows = run(c2, b, ticker="G")
    gap = rows[-8]
    assert gap["state"] == "UNAVAILABLE" and gap["reason"] == "missing_or_invalid_completed_session"
    assert rows[-1]["episode"]["history_complete"] is False
    assert run(c, b, ticker="G")[-1]["episode"]["history_complete"] is True


def test_calendar_and_source_guards_fail_closed():
    c, b = series(CRASH)
    dates = list(c.index.date)
    bad = replay_lineage(c, b, as_of=dates[-2], sessions=dates, spec=SPEC)
    assert bad == [{"as_of": dates[-2].isoformat(), "state": "UNAVAILABLE",
                    "reason": "invalid_or_incomplete_calendar", "thesis_state": "UNKNOWN",
                    "setup_state": "WATCH", "break_class": None, "contradiction_evidence": [],
                    "revisable": None, "episode": None, "price_ath": None, "rs_ath": None}]
    empty = replay_lineage(c, pd.Series(dtype=float), as_of=dates[-1], sessions=dates, spec=SPEC)
    assert empty[0]["reason"] == "missing_source"
    tz = pd.Series(c.values, index=c.index.tz_localize("UTC"))
    assert replay_lineage(tz, b, as_of=dates[-1], sessions=dates, spec=SPEC)[0]["reason"] == "expected_naive_session_date"


# ---------------------------------------------------------------------------- T8 frozen definitions, no authority
def test_spec_is_frozen_checked_and_digested():
    assert LineageSpec().digest == hashlib.sha256(json.dumps(asdict(LineageSpec()), sort_keys=True).encode()).hexdigest()
    assert LineageSpec().digest != LineageSpec(deep_fraction=0.25).digest
    assert LineageSpec().digest == "cf43eb5deb69ca7b3c14aa5d96f72a1c8b829b0c015e364293f04763bfc1c5cf"
    with pytest.raises(ValueError, match="invalid_window_order"):
        LineageSpec(fast_window=50, slow_window=40)
    with pytest.raises(ValueError, match="invalid_horizon_order"):
        LineageSpec(structural_below_slow=200, horizon_sessions=100)
    with pytest.raises(ValueError, match="invalid_fraction"):
        LineageSpec(deep_fraction=1.5)
    with pytest.raises(ValueError, match="invalid_window"):
        LineageSpec(confirm_sessions=1)
    with pytest.raises(Exception):
        LineageSpec().deep_fraction = 0.3   # frozen


def test_describe_lineage_reports_descriptive_authority_and_linked_episodes():
    tail = CRASH + [68] * 12 + [76] * 4 + [60] + list(np.linspace(61, 150, 140))
    c, b = series(tail)
    out = describe_lineage(c, b, as_of=c.index[-1].date(), sessions=list(c.index.date), ticker="R",
                           source_ref="synthetic", spec=SPEC, peers=peers_for(c))
    assert out["schema"] == "leader_lineage.v1" and out["evidence_mode"] == "RECONSTRUCTED_CURRENT_VINTAGE"
    assert out["authority"] == {k: False for k in AUTHORITY} and out["definition_sha256"] == SPEC.digest
    assert out["source_ref"] == "synthetic" and len(out["source_fingerprint_sha256"]) == 64
    eps = out["episodes"]
    assert len(eps) == 2
    first, second = eps
    assert first["phase"] == "FAILED" and first["closed_on"] is not None
    assert first["close_reason"] == "re_admitted_new_episode"
    assert second["prior_episode_id"] == first["episode_id"] and second["phase"] == "ACTIVE"
    assert second["episode_id"] == hashlib.sha256(f"R|{second['leadership_qualified_at']}".encode()).hexdigest()[:16]
    assert out["state"] == "ACTIVE" and out["episode"]["episode_id"] == second["episode_id"]
    assert set(out["episode"]["ladder"]) == set(LADDER)
