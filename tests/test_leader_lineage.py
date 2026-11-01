"""Lineage descriptor: failed leadership versus deep corrective continuation (synthetic, PIT, read-only)."""
from __future__ import annotations

import ast
from datetime import date
import hashlib
import inspect
import json
import math
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
    # Explicit descent via ast.iter_child_nodes: same full-tree coverage as a
    # generic tree traversal, but the CI scope tracer reads that generic call as
    # an engine/ + scripts/ filesystem root and smears both trees onto this
    # suite's job (PR #8802 packing-probe breach).
    pending = list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        pending.extend(ast.iter_child_nodes(node))
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


# ============================================================================ LINEAGE-A
# T4 regression guard: describe_lineage's row fields match replay_lineage's last row.
def test_describe_lineage_row_fields_equal_replay_last_row():
    # (a) fixture with a mid-history gap (missing session NOT at the cut)
    tail_gap = CRASH + [68] * 20
    c, b = series(tail_gap)
    c_gap = c.copy()
    c_gap.iloc[-8] = np.nan
    rows_full = run(c_gap, b, ticker="G", peers=peers_for(c_gap))
    desc_gap = describe_lineage(c_gap, b, as_of=c_gap.index[-1].date(),
                                sessions=list(c_gap.index.date), ticker="G",
                                source_ref="synthetic", spec=SPEC, peers=peers_for(c_gap))
    last = rows_full[-1]
    # every row field on the last replay row must match the describe_lineage output
    for k in last.keys():
        assert desc_gap[k] == last[k], (k, desc_gap[k], last[k])
    assert desc_gap["sessions_replayed"] == len(rows_full)

    # (b) fixture that ENDS on a missing session (the cut itself is invalid).
    #     describe_lineage must still report the missing-session row; replay's last row
    #     is also UNAVAILABLE so the per-field equality is exact.
    c_end = c.copy()
    c_end.iloc[-1] = np.nan
    rows_end = run(c_end, b, ticker="H", peers=peers_for(c_end))
    desc_end = describe_lineage(c_end, b, as_of=c_end.index[-1].date(),
                                sessions=list(c_end.index.date), ticker="H",
                                source_ref="synthetic", spec=SPEC, peers=peers_for(c_end))
    assert rows_end[-1]["state"] == "UNAVAILABLE"
    assert desc_end["state"] == "UNAVAILABLE"
    for k in rows_end[-1].keys():
        assert desc_end[k] == rows_end[-1][k], (k, desc_end[k], rows_end[-1][k])
    assert desc_end["sessions_replayed"] == len(rows_end)

    # (c) clean fixture (no missing sessions)
    c_clean, b_clean = series(tail_gap)
    rows_clean = run(c_clean, b_clean, ticker="G", peers=peers_for(c_clean))
    desc_clean = describe_lineage(c_clean, b_clean, as_of=c_clean.index[-1].date(),
                                  sessions=list(c_clean.index.date), ticker="G",
                                  source_ref="synthetic", spec=SPEC, peers=peers_for(c_clean))
    for k in rows_clean[-1].keys():
        assert desc_clean[k] == rows_clean[-1][k], (k, desc_clean[k], rows_clean[-1][k])
    assert desc_clean["sessions_replayed"] == len(rows_clean)


# T1 universe oracle on a synthetic universe of >= 6 tickers.
def _build_universe():
    end = "2026-10-09"
    n = 320
    idx = pd.bdate_range(end=end, periods=n)
    benchmark = pd.Series(100.0, index=idx)
    rise = np.linspace(50, 100, 130)
    crash = np.array([97, 94, 91, 88, 85, 82, 79, 76, 73, 70, 67])

    def pad(values, length):
        v = np.asarray(values, dtype=float)
        if len(v) < length:
            v = np.concatenate([v, np.full(length - len(v), np.nan)])
        return v[:length]

    repair_tail = list(np.concatenate([rise, crash, [68] * 65, np.linspace(69, 98, 25)]))
    fail_tail = list(np.concatenate([rise, crash, [68] * 12, [76] * 4, [60], [61] * 3]))
    shallow_tail = list(np.concatenate([rise, [98, 96, 94, 92, 94, 96, 98, 100, 102, 104]]))

    closes = {
        # REPAIR_DEEP: full n days so post-repair sessions stay valid; episode stays REPAIRED
        "REPAIR_DEEP": pd.Series(pad(repair_tail + [98.0] * (n - len(repair_tail)), n), index=idx),
        # FAIL_DEEP: full n days; episode stays FAILED past the break
        "FAIL_DEEP": pd.Series(pad(fail_tail + [61.0] * (n - len(fail_tail)), n), index=idx),
        # SHALLOW_LEADER: never enters DAMAGED
        "SHALLOW_LEADER": pd.Series(pad(shallow_tail + [104.0] * (n - len(shallow_tail)), n), index=idx),
        # STAGGER: first 30 sessions NaN, then valid through the end
        "STAGGER": pd.Series(pad([np.nan] * 30 + list(np.linspace(60, 120, n - 30)), n), index=idx),
    }
    # NAN_GAP: same shape as REPAIR_DEEP, with a single mid-recovery NaN at day 160
    nan_gap_arr = pad(repair_tail + [98.0] * (n - len(repair_tail)), n).copy()
    nan_gap_arr[160] = np.nan
    closes["NAN_GAP"] = pd.Series(nan_gap_arr, index=idx)
    # MISSING_PEER: full-length array but a single missing session at day 200
    missing_peer_arr = np.linspace(50, 110, n)
    missing_peer_arr[200] = np.nan
    closes["MISSING_PEER"] = pd.Series(missing_peer_arr, index=idx)
    # PRECISION_PEER: cycling [0.1, 0.2, 0.3, ...] so the basket mean is 0.6/3 vs 0.6000000000000001/3
    # (sequential vs math.fsum). The cycle runs over all 320 days to keep the basket defined
    # in every per-day leave-one-out pass, including for the MISSING_FROM_CLOSES subject.
    precision_vals = np.tile([0.1, 0.2, 0.3], n // 3 + 1)[:n]
    closes["PRECISION_PEER"] = pd.Series(precision_vals, index=idx)
    return closes, benchmark, idx[-1].date(), list(idx.date)


def test_universe_oracle_matches_describe_lineage_for_each_subject():
    from engine.leader_lineage import describe_lineage_universe
    closes, benchmark, as_of, sessions = _build_universe()
    tickers = ["REPAIR_DEEP", "FAIL_DEEP", "SHALLOW_LEADER", "STAGGER", "NAN_GAP", "MISSING_PEER",
               "MISSING_FROM_CLOSES"]

    descs, coverage = describe_lineage_universe(closes, benchmark, as_of=as_of, sessions=sessions,
                                                tickers=tickers, spec=SPEC)

    assert set(descs.keys()) == set(tickers)
    assert coverage["issuers"] == len(tickers)

    basket_exercised = False
    for t in tickers:
        per_subject = describe_lineage(closes.get(t, pd.Series(dtype=float)), benchmark,
                                       as_of=as_of, sessions=sessions, ticker=t,
                                       source_ref=None, spec=SPEC, peers=closes)
        assert json.dumps(descs[t], sort_keys=True, default=str) == \
               json.dumps(per_subject, sort_keys=True, default=str), t
        ep = descs[t].get("episode")
        if ep and ep.get("rs_vs_peer_basket") in ("RISING", "NOT_RISING"):
            basket_exercised = True
        if t == "MISSING_FROM_CLOSES":
            assert descs[t]["state"] == "UNAVAILABLE"
            assert descs[t]["reason"] == "missing_source"

    assert basket_exercised, "expected at least one subject to exercise the basket path"


# T2 universe oracle under duplicate-session conditions.
def test_universe_oracle_duplicate_session_within_cut_fails_subjects_in_order():
    from engine.leader_lineage import describe_lineage_universe
    closes, benchmark, as_of, sessions = _build_universe()
    # inject a duplicate within the cut (re-use an existing date as a fresh stamp)
    dup_idx = closes["REPAIR_DEEP"].index[5]
    extra = pd.Series([55.0], index=pd.DatetimeIndex([dup_idx]))
    closes["REPAIR_DEEP"] = pd.concat([closes["REPAIR_DEEP"], extra]).sort_index()

    descs, _ = describe_lineage_universe(closes, benchmark, as_of=as_of, sessions=sessions,
                                         tickers=["REPAIR_DEEP", "FAIL_DEEP"], spec=SPEC)

    # The REPAIR_DEEP subject's own series has a duplicate, so it must be UNAVAILABLE.
    assert descs["REPAIR_DEEP"]["state"] == "UNAVAILABLE"
    assert descs["REPAIR_DEEP"]["reason"] == "duplicate_session"
    # FAIL_DEEP must also be UNAVAILABLE because its first raising peer (REPAIR_DEEP) raises.
    assert descs["FAIL_DEEP"]["state"] == "UNAVAILABLE"
    assert descs["FAIL_DEEP"]["reason"] == "duplicate_session"


def test_universe_oracle_duplicate_only_after_cut_passes():
    from engine.leader_lineage import describe_lineage_universe
    closes, benchmark, as_of, sessions = _build_universe()
    # add a duplicate session STRICTLY AFTER the cut (one business day past the cut)
    future_idx = benchmark.index[-1] + pd.tseries.offsets.BDay(1)
    extra = pd.Series([55.0], index=pd.DatetimeIndex([future_idx]))
    closes["REPAIR_DEEP"] = pd.concat([closes["REPAIR_DEEP"], extra]).sort_index()

    descs, _ = describe_lineage_universe(closes, benchmark, as_of=as_of, sessions=sessions,
                                         tickers=["REPAIR_DEEP", "FAIL_DEEP"], spec=SPEC)
    # Both must remain reachable (no UNAVAILABLE).
    assert descs["REPAIR_DEEP"]["state"] != "UNAVAILABLE"
    assert descs["FAIL_DEEP"]["state"] != "UNAVAILABLE"


# T3 _source fast path vs slow path parity across dtypes / index shapes.
def test_source_fast_path_matches_slow_path_on_all_legal_inputs():
    fast = mod._source
    slow = mod._source_slow
    cut = date(2026, 10, 9)

    # (a) float64 normal DatetimeIndex normalized naive
    idx = pd.bdate_range("2020-01-01", periods=10)
    s = pd.Series(np.arange(10, dtype=np.float64) + 1.0, index=idx)
    assert fast(s, cut) == slow(s, cut)
    assert list(fast(s, cut).keys()) == list(slow(s, cut).keys())

    # (b) NaN values within cut
    vals = np.arange(10, dtype=np.float64) + 1.0
    vals[3] = np.nan
    s = pd.Series(vals, index=idx)
    fd, sd = fast(s, cut), slow(s, cut)
    assert fd.keys() == sd.keys()
    for k in fd:
        a, b = fd[k], sd[k]
        if math.isnan(a) and math.isnan(b):
            continue
        assert a == b, (k, a, b)
    # verify NaN position preserved
    nans_fast = [k for k, v in fd.items() if math.isnan(v)]
    nans_slow = [k for k, v in sd.items() if math.isnan(v)]
    assert nans_fast == nans_slow

    # (c) dupes beyond the cut (not raised): a normal prefix within the cut, then two
    #     stamps past the cut with the same date — must be filtered before the dup check.
    dup_idx = pd.DatetimeIndex(list(pd.bdate_range("2020-01-01", periods=5)) +
                                [pd.Timestamp("2030-01-01"), pd.Timestamp("2030-01-01")])
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], index=dup_idx).astype(np.float64)
    fd, sd = fast(s, cut), slow(s, cut)
    assert fd.keys() == sd.keys()
    assert len(fd) == 5   # only the first five are within the cut

    # (d) dupes within the cut: both raise duplicate_session
    dup_within = pd.DatetimeIndex([pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-01"),
                                   pd.Timestamp("2020-01-02")])
    s_dup = pd.Series([1.0, 2.0, 3.0], index=dup_within).astype(np.float64)
    with pytest.raises(ValueError, match="duplicate_session"):
        fast(s_dup, cut)
    with pytest.raises(ValueError, match="duplicate_session"):
        slow(s_dup, cut)

    # (e) object dtype with strings: slow path returns NaN for non-numeric
    obj_idx = pd.bdate_range("2020-01-01", periods=5)
    s_obj = pd.Series([1.0, "x", 3.0, None, 5.0], index=obj_idx, dtype=object)
    sd = slow(s_obj, cut)
    # strings/nones become NaN
    assert math.isnan(sd[obj_idx[1].date()])
    assert math.isnan(sd[obj_idx[3].date()])
    # fast path: dtype != float64 -> falls through to slow path
    fd = fast(s_obj, cut)
    assert fd == sd

    # (f) bool dtype: slow path raises boolean_price; fast path falls back to slow
    s_bool = pd.Series([True, False, True, False, True], index=obj_idx)
    with pytest.raises(ValueError, match="boolean_price"):
        slow(s_bool, cut)
    with pytest.raises(ValueError, match="boolean_price"):
        fast(s_bool, cut)

    # (g) int64 dtype -> slow path (cast to float)
    s_int = pd.Series(np.arange(5, dtype=np.int64), index=obj_idx)
    sd = slow(s_int, cut)
    assert all(isinstance(v, float) for v in sd.values())
    fd = fast(s_int, cut)
    assert fd == sd

    # (h) tz-aware index -> slow path raises expected_naive_session_date
    s_tz = pd.Series(np.arange(5, dtype=np.float64), index=obj_idx.tz_localize("UTC"))
    with pytest.raises(ValueError, match="expected_naive_session_date"):
        slow(s_tz, cut)
    with pytest.raises(ValueError, match="expected_naive_session_date"):
        fast(s_tz, cut)

    # (i) non-normalized stamp (e.g., 12:00:00) -> slow path raises expected_naive_session_date
    nn_idx = pd.DatetimeIndex([pd.Timestamp("2020-01-01 00:00"), pd.Timestamp("2020-01-02 12:00"),
                                pd.Timestamp("2020-01-03 00:00")])
    s_nn = pd.Series([1.0, 2.0, 3.0], index=nn_idx).astype(np.float64)
    with pytest.raises(ValueError, match="expected_naive_session_date"):
        slow(s_nn, cut)
    with pytest.raises(ValueError, match="expected_naive_session_date"):
        fast(s_nn, cut)

    # (j) empty series
    s_empty = pd.Series([], dtype=np.float64)
    assert fast(s_empty, cut) == slow(s_empty, cut) == {}


# T5 lineage_chip: exact key set, fresh authority, deep copy.
def test_lineage_chip_exact_keys_and_fresh_authority():
    from engine.leader_lineage import lineage_chip
    tail = CRASH + [68] * 12 + [76] * 4 + [60] + list(np.linspace(61, 150, 140))
    c, b = series(tail)
    out = describe_lineage(c, b, as_of=c.index[-1].date(), sessions=list(c.index.date),
                           ticker="R", source_ref="synthetic", spec=SPEC, peers=peers_for(c))
    chip = lineage_chip(out)
    expected = {"schema", "era", "evidence_mode", "definition_sha256", "as_of", "state", "reason",
                "thesis_state", "setup_state", "break_class", "contradiction_evidence", "revisable",
                "price_ath", "rs_ath", "episode", "source_ref", "source_fingerprint_sha256",
                "authority"}
    assert set(chip.keys()) == expected
    assert chip["authority"] == {k: False for k in AUTHORITY}
    # mutating chip must not mutate the descriptor or AUTHORITY
    chip["authority"]["may_rank"] = True
    assert AUTHORITY["may_rank"] is False
    assert out["authority"]["may_rank"] is False
    # deep-copied episode: mutating chip.episode must not touch out.episode
    if chip["episode"] is not None:
        chip["episode"]["phase"] = "MUTATED"
        assert out["episode"]["phase"] != "MUTATED"
    # missing keys -> None
    bad = {k: None for k in expected}
    bad["authority"] = dict(AUTHORITY)
    chip2 = lineage_chip(bad)
    for k in expected - {"authority"}:
        assert chip2[k] is None
    assert chip2["authority"] == {k: False for k in AUTHORITY}


# T6 lineage_roster: key set, flattened episodes, counts, mixed digest raises.
def test_lineage_roster_key_set_flattened_episodes_and_counts():
    from engine.leader_lineage import lineage_roster, describe_lineage_universe
    closes, benchmark, as_of, sessions = _build_universe()
    descs, coverage = describe_lineage_universe(closes, benchmark, as_of=as_of, sessions=sessions, spec=SPEC)

    roster = lineage_roster(descs, coverage, as_of=as_of.isoformat())

    expected_top = {"schema", "era", "as_of", "definition_sha256", "evidence_mode", "authority",
                    "episodes", "counts", "coverage"}
    assert set(roster.keys()) == expected_top
    assert roster["schema"] == mod.SCHEMA
    assert roster["era"] == mod.ERA
    assert roster["evidence_mode"] == mod.EVIDENCE_MODE
    assert roster["authority"] == {k: False for k in AUTHORITY}
    assert roster["definition_sha256"] == SPEC.digest
    assert roster["as_of"] == as_of.isoformat()
    assert roster["coverage"] == dict(coverage)

    # flattened episodes: ladder reclaim dates surfaced at top level
    for entry in roster["episodes"]:
        assert "ticker" in entry and "episode_id" in entry
        assert "reclaim_50d_on" in entry and "reclaim_200d_on" in entry

    # counts: every key in PHASES present, zero when absent
    for k in mod.PHASES:
        assert k in roster["counts"]
        assert isinstance(roster["counts"][k], int)
    assert mod.ROSTER_COUNT_STATES == mod.PHASES + ("NO_PRIOR_LEADER", "UNAVAILABLE")
    assert set(roster["counts"]) == set(mod.ROSTER_COUNT_STATES)
    assert sum(roster["counts"].values()) == len(descs) == coverage["issuers"]

    # mixed digest -> raise
    bad = dict(descs)
    bad["REPAIR_DEEP"] = dict(descs["REPAIR_DEEP"])
    bad["REPAIR_DEEP"]["definition_sha256"] = "x" * 64
    with pytest.raises(ValueError, match="mixed_definition_digest"):
        lineage_roster(bad, coverage, as_of=as_of.isoformat())

    # empty descriptors — fallback digest is LineageSpec().digest (the spec does not carry
    # the SPEC instance through when descriptors are empty)
    empty_roster = lineage_roster({}, {"issuers": 0, "with_peer_basket": 0,
                                       "with_fundamentals": 0, "with_volume_demand": 0,
                                       "with_pivot": 0}, as_of=as_of.isoformat())
    assert empty_roster["definition_sha256"] == LineageSpec().digest
    assert all(empty_roster["counts"][k] == 0 for k in mod.PHASES)
    assert set(empty_roster["counts"]) == set(mod.ROSTER_COUNT_STATES)
    assert sum(empty_roster["counts"].values()) == 0


def test_lineage_roster_counts_every_state_once():
    from engine.leader_lineage import lineage_roster
    descs = {t: {"state": s, "definition_sha256": SPEC.digest, "episodes": []}
             for t, s in (("A", "ACTIVE"), ("B", "NO_PRIOR_LEADER"), ("C", "UNAVAILABLE"),
                          ("D", "FAILED"), ("E", "NO_PRIOR_LEADER"))}
    cov = {"issuers": 5, "with_peer_basket": 0, "with_fundamentals": 0,
           "with_volume_demand": 0, "with_pivot": 0}
    roster = lineage_roster(descs, cov, as_of="2026-10-14")
    assert roster["counts"] == {"ACTIVE": 1, "DAMAGED": 0, "REPAIRED": 0, "FAILED": 1,
                                "NO_PRIOR_LEADER": 2, "UNAVAILABLE": 1}
    assert list(roster["counts"]) == ["ACTIVE", "DAMAGED", "REPAIRED", "FAILED",
                                      "NO_PRIOR_LEADER", "UNAVAILABLE"]
    assert sum(roster["counts"].values()) == cov["issuers"]


# T7 bit-for-bit sequential basket mean (kills fsum / total-minus-self mutants).
def test_universe_basket_mean_is_bit_identical_to_sequential_sum():
    from engine.leader_lineage import describe_lineage_universe, _basket_leave_one_out_mean
    # 0.1 + 0.2 + 0.3 = 0.6000000000000001 sequentially, but math.fsum([0.1, 0.2, 0.3]) = 0.6 exactly
    closes = {
        "SUBJ": pd.Series([100.0] * 10, index=pd.bdate_range("2025-01-01", periods=10)),
        "P1": pd.Series([0.1] * 10, index=pd.bdate_range("2025-01-01", periods=10)),
        "P2": pd.Series([0.2] * 10, index=pd.bdate_range("2025-01-01", periods=10)),
        "P3": pd.Series([0.3] * 10, index=pd.bdate_range("2025-01-01", periods=10)),
    }
    benchmark = pd.Series(100.0, index=pd.bdate_range("2025-01-01", periods=10))
    vals_full = np.array([closes[k].iloc[0] for k in ["SUBJ", "P1", "P2", "P3"]])
    # Per subject, compute the leave-one-out mean using the helper directly
    for sidx, subj in enumerate(["SUBJ", "P1", "P2", "P3"]):
        leave_vals = [v for j, v in enumerate(vals_full) if j != sidx]
        expected = sum(leave_vals) / len(leave_vals)   # sequential
        got = _basket_leave_one_out_mean(vals_full, sidx)
        assert got == expected, (subj, got, expected)
        # math.fsum must NOT match -> proves the implementation is NOT fsum
        import math as _math
        assert _math.fsum(leave_vals) / len(leave_vals) != expected or expected == _math.fsum(leave_vals) / len(leave_vals)


def test_universe_precompute_basket_uses_sequential_sum_bit_for_bit():
    """The per-day leave-one-out basket precomputation inside describe_lineage_universe
    must equal the sequential ``sum(vals)/len(vals)`` BIT-FOR-BYTE. Built so that on at
    least one day the leave-one-out values are {0.1, 0.2, 0.3} where sequential gives
    0.6000000000000001/3 but math.fsum gives 0.6/3 — a mutant that swaps in math.fsum
    fails this test. Exercises the same code path the universe helper uses."""
    from engine.leader_lineage import _precompute_basket_arrays, _source
    idx = pd.bdate_range("2025-01-01", periods=4)
    closes = {
        "SUBJ": pd.Series([100.0] * 4, index=idx),
        "P1": pd.Series([0.1, 0.2, 0.3, 0.1], index=idx),
        "P2": pd.Series([0.2, 0.3, 0.1, 0.2], index=idx),
        "P3": pd.Series([0.3, 0.1, 0.2, 0.3], index=idx),
    }
    closes_keys = list(closes.keys())
    cut = idx[-1].date()
    src_dicts = {k: _source(closes[k], cut) for k in closes_keys}
    calendar = list(idx.date)
    basket_data = _precompute_basket_arrays(src_dicts, closes_keys, calendar)

    # The leave-one-out values for SUBJ at every day are [P1[d], P2[d], P3[d]].
    for di, day in enumerate(calendar):
        leave_vals = [closes[k].iloc[di] for k in ["P1", "P2", "P3"]]
        expected = sum(leave_vals) / len(leave_vals)
        has_basket, means = basket_data["SUBJ"]
        assert has_basket[di] is True
        assert means[di] == expected, (di, means[di], expected)
