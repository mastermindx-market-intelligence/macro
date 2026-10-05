"""Lane C2 invariants (NOT DONE UNLESS) + round-2 N1..N3 / J1..J3.

Repo discovery: C2_REPO if set, else `git rev-parse --show-toplevel`.
Never a fixed parent count.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _repo() -> Path:
    env = os.environ.get("C2_REPO")
    if env:
        return Path(env).resolve()
    out = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(Path(__file__).resolve().parent),
        text=True,
    ).strip()
    return Path(out)


REPO = _repo()
CODE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = CODE_DIR.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import run as R  # noqa: E402


# ────────────────────── (1) join leak ──────────────────────
def _synth_state(dates: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(dates)
    terc = np.array(["fast", "mid", "persistent"] * ((n // 3) + 1))[:n]
    brd = np.array(["narrow", "mid", "broad"] * ((n // 3) + 1))[:n]
    dfii = np.array(["falling", "mid", "rising"] * ((n // 3) + 1))[:n]
    st = pd.DataFrame(
        {
            "LP": np.linspace(-0.2, 0.2, n),
            "rotation_tercile": terc,
            "breadth_tercile": brd,
            "dfii_tercile": dfii,
        },
        index=pd.DatetimeIndex(dates, name="date"),
    )
    return st


def _synth_1d(signal_dates, names=None, h10=None, h21=None) -> pd.DataFrame:
    signal_dates = pd.to_datetime(list(signal_dates)).normalize()
    if names is None:
        names = ["AAA"] * len(signal_dates)
    months = pd.Index(signal_dates).to_period("M").astype(str)
    eras = np.where(signal_dates <= pd.Timestamp("2019-12-31"), "2014-2019", "2020-2026")
    n = len(signal_dates)
    return pd.DataFrame(
        {
            "variant": ["1D"] * n,
            "name": list(names),
            "signal_date": signal_dates,
            "entry_date": signal_dates + pd.Timedelta(days=1),
            "entry_month": months,
            "era": eras,
            "excess_h10_net": np.linspace(-0.05, 0.05, n) if h10 is None else h10,
            "excess_h21_net": np.linspace(-0.08, 0.08, n) if h21 is None else h21,
        }
    )


def test_join_ignores_state_rows_after_signal_date():
    dates = pd.bdate_range("2020-01-02", periods=12)
    signal = dates[5]
    state = _synth_state(dates)
    events = _synth_1d([signal])
    joined, dropped = R.attach_state_to_1d(events, state)
    assert dropped == 0
    assert len(joined) == 1
    baseline_lp = float(joined["LP"].iloc[0])
    baseline_t = str(joined["rotation_tercile"].iloc[0])

    perturbed = state.copy()
    future = perturbed.index > signal
    assert future.any(), "need future rows to perturb"
    perturbed.loc[future, "LP"] = 999.0
    perturbed.loc[future, "rotation_tercile"] = "persistent"
    joined2, dropped2 = R.attach_state_to_1d(events, perturbed)
    assert dropped2 == 0
    assert float(joined2["LP"].iloc[0]) == pytest.approx(baseline_lp)
    assert str(joined2["rotation_tercile"].iloc[0]) == baseline_t

    on = state.copy()
    on.loc[on.index == signal, "LP"] = -123.0
    on.loc[on.index == signal, "rotation_tercile"] = "mid"
    joined3, _ = R.attach_state_to_1d(events, on)
    assert float(joined3["LP"].iloc[0]) == pytest.approx(-123.0)
    assert str(joined3["rotation_tercile"].iloc[0]) == "mid"


def test_join_drops_absent_date_instead_of_asof_future():
    dates = pd.bdate_range("2020-01-02", periods=10)
    missing = dates[4]
    state = _synth_state(dates.drop(missing))
    events = _synth_1d([missing])
    joined, dropped = R.attach_state_to_1d(events, state)
    assert dropped == 1
    assert len(joined) == 0


def test_confirmed_inherits_parent_state_not_later_date():
    dates = pd.bdate_range("2020-01-02", periods=12)
    s1 = dates[3]
    s3 = dates[7]
    state = _synth_state(dates)
    e1 = _synth_1d([s1], names=["AAA"])
    parents, _ = R.attach_state_to_1d(e1, state)
    parent_lp = float(parents["LP"].iloc[0])
    parent_t = str(parents["rotation_tercile"].iloc[0])

    events_panel = pd.concat(
        [
            e1,
            pd.DataFrame(
                {
                    "variant": ["3D.p0"],
                    "name": ["AAA"],
                    "signal_date": [s3],
                    "entry_date": [s3 + pd.Timedelta(days=1)],
                    "entry_month": [pd.Timestamp(s3).to_period("M").strftime("%Y-%m")],
                    "era": ["2020-2026"],
                    "excess_h10_net": [0.01],
                    "excess_h21_net": [0.02],
                }
            ),
        ],
        ignore_index=True,
    )
    pairs = pd.DataFrame(
        {
            "variant": ["3D.p0"],
            "name": ["AAA"],
            "signal_session_1d": [s1],
            "signal_session_other": [s3],
            "delay_sessions": [4.0],
            "confirmation_cost_pct": [0.01],
            "mfe21_consumed_frac": [0.2],
            "no_confirmation": [False],
        }
    )
    conf = R.attach_confirmed(pairs, events_panel, parents, "3D.p0")
    assert len(conf) == 1
    assert float(conf["LP"].iloc[0]) == pytest.approx(parent_lp)
    assert str(conf["rotation_tercile"].iloc[0]) == parent_t

    state2 = state.copy()
    later = state2.index >= s3
    state2.loc[later, "LP"] = 42.0
    state2.loc[later, "rotation_tercile"] = "persistent"
    parents2, _ = R.attach_state_to_1d(e1, state2)
    conf2 = R.attach_confirmed(pairs, events_panel, parents2, "3D.p0")
    assert float(conf2["LP"].iloc[0]) == pytest.approx(parent_lp)
    assert str(conf2["rotation_tercile"].iloc[0]) == parent_t


# ────────────────────── (2) paired bootstrap helpers ──────────────────────
def test_paired_bootstrap_one_draw_per_replicate():
    rng = np.random.default_rng(20261004)
    n_months, n_boot = 7, 200
    draws = R.make_paired_draws(n_months, n_boot, rng)
    assert draws.shape == (n_boot, n_months)
    month_idx = np.array([0, 0, 1, 1, 2, 2, 3, 4, 5, 6], dtype=np.int64)
    a = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0])
    b = 10.0 * a
    boot_a = R.cell_boot_means(draws, month_idx, a)
    boot_b = R.cell_boot_means(draws, month_idx, b)
    np.testing.assert_allclose(boot_b, 10.0 * boot_a, rtol=0, atol=1e-12)


def test_paired_draws_shared_across_disjoint_cells():
    rng = np.random.default_rng(20261004)
    draws = R.make_paired_draws(3, 50, rng)
    ma = np.array([0, 0, 0], dtype=np.int64)
    va = np.array([1.0, 1.0, 1.0])
    mb = np.array([2, 2], dtype=np.int64)
    vb = np.array([5.0, 5.0])
    ba = R.cell_boot_means(draws, ma, va)
    bb = R.cell_boot_means(draws, mb, vb)
    for b in range(draws.shape[0]):
        w = np.bincount(draws[b], minlength=3)
        if w[0] == 0:
            assert np.isnan(ba[b])
        else:
            assert ba[b] == pytest.approx(1.0)
        if w[2] == 0:
            assert np.isnan(bb[b])
        else:
            assert bb[b] == pytest.approx(5.0)


# ────────────────────── (3) support table ──────────────────────
def test_support_cell_ids_complete():
    ids = R.all_support_cell_ids()
    expected = {
        R.support_cell_id(v, t, e)
        for v in R.SUPPORT_VARIANTS
        for t in R.ROT_TERCILES
        for e in R.ERAS
    }
    assert set(ids) == expected
    assert len(ids) == 6 * 3 * 2


def _tiny_panel_for_compute_all(*, identical_cells: bool, fast_worse: bool, tiny_floors: bool):
    """Build events/pairs/state for compute_all tests."""
    if tiny_floors:
        dates = pd.bdate_range("2020-01-02", periods=8)
        state = _synth_state(dates)
        sigs = list(dates[2:6])
        names = [f"N{i}" for i in range(len(sigs))]
        e1 = _synth_1d(sigs, names=names)
    elif identical_cells:
        dates = pd.bdate_range("2020-01-02", periods=30)
        # Force rotation tercile by overwriting state so dates 0-9 fast, 10-19 also
        # map to the SAME values on matching months. Easier: duplicate each 1D
        # event onto both terciles via the state table matching signal dates.
        state = _synth_state(dates)
        # Use a handful of months; put the same names/values on dates whose
        # state tercile is fast AND dates whose tercile is persistent, with
        # identical outcomes and identical month labels.
        fast_dates = [d for d in dates if str(state.loc[d, "rotation_tercile"]) == "fast"][:4]
        pers_dates = [d for d in dates if str(state.loc[d, "rotation_tercile"]) == "persistent"][:4]
        assert len(fast_dates) == 4 and len(pers_dates) == 4
        rows = []
        pairs_rows = []
        ev_rows = []
        months = ["2020-01", "2020-01", "2020-02", "2020-02"]
        vals = [0.01, 0.02, -0.01, 0.00]
        for i, (fd, pdte, m, v) in enumerate(zip(fast_dates, pers_dates, months, vals)):
            for dt, rot_name in ((fd, "F"), (pdte, "P")):
                nm = f"N{i}"
                rows.append({
                    "variant": "1D",
                    "name": nm,
                    "signal_date": dt,
                    "entry_date": dt + pd.Timedelta(days=1),
                    "entry_month": m,  # shared month label across terciles
                    "era": "2020-2026",
                    "excess_h10_net": v,
                    "excess_h21_net": v,
                })
                for var in list(R.VARIANTS_2D) + list(R.VARIANTS_3D):
                    ev_rows.append({
                        "variant": var,
                        "name": nm,
                        "signal_date": dt,
                        "entry_date": dt + pd.Timedelta(days=1),
                        "entry_month": m,
                        "era": "2020-2026",
                        "excess_h10_net": v,
                        "excess_h21_net": v,
                    })
                    pairs_rows.append({
                        "variant": var,
                        "name": nm,
                        "signal_session_1d": dt,
                        "signal_session_other": dt,
                        "delay_sessions": 0.0,
                        "confirmation_cost_pct": 0.01,
                        "mfe21_consumed_frac": 0.1,
                        "no_confirmation": False,
                    })
        e1 = pd.DataFrame(rows)
        events = pd.concat([e1, pd.DataFrame(ev_rows)], ignore_index=True)
        pairs = pd.DataFrame(pairs_rows)
        return events, pairs, state
    else:
        # fast_worse: confirmed H10 much lower on fast dates than persistent
        dates = pd.bdate_range("2018-01-02", periods=40)
        state = _synth_state(dates)
        fast_dates = [d for d in dates if str(state.loc[d, "rotation_tercile"]) == "fast"][:6]
        pers_dates = [d for d in dates if str(state.loc[d, "rotation_tercile"]) == "persistent"][:6]
        mid_dates = [d for d in dates if str(state.loc[d, "rotation_tercile"]) == "mid"][:4]
        rows = []
        ev_rows = []
        pairs_rows = []
        def add_event(dt, nm, h10_1d, h10_conf):
            era = "2014-2019" if dt.year <= 2019 else "2020-2026"
            m = pd.Timestamp(dt).to_period("M").strftime("%Y-%m")
            rows.append({
                "variant": "1D", "name": nm, "signal_date": dt,
                "entry_date": dt + pd.Timedelta(days=1), "entry_month": m, "era": era,
                "excess_h10_net": h10_1d, "excess_h21_net": h10_1d,
            })
            for var in list(R.VARIANTS_2D) + list(R.VARIANTS_3D):
                ev_rows.append({
                    "variant": var, "name": nm, "signal_date": dt,
                    "entry_date": dt + pd.Timedelta(days=1), "entry_month": m, "era": era,
                    "excess_h10_net": h10_conf, "excess_h21_net": h10_conf,
                })
                pairs_rows.append({
                    "variant": var, "name": nm, "signal_session_1d": dt,
                    "signal_session_other": dt, "delay_sessions": 0.0,
                    "confirmation_cost_pct": 0.01, "mfe21_consumed_frac": 0.2,
                    "no_confirmation": False,
                })
        for i, dt in enumerate(fast_dates):
            add_event(dt, f"F{i}", 0.00, -0.04)  # gap_fast ≈ -0.04
        for i, dt in enumerate(pers_dates):
            add_event(dt, f"P{i}", 0.00, -0.005)  # gap_pers ≈ -0.005
        for i, dt in enumerate(mid_dates):
            add_event(dt, f"M{i}", 0.00, -0.02)
        e1 = pd.DataFrame(rows)
        events = pd.concat([e1, pd.DataFrame(ev_rows)], ignore_index=True)
        pairs = pd.DataFrame(pairs_rows)
        return events, pairs, state

    # tiny_floors path
    rows = [e1]
    pairs_rows = []
    for v in list(R.VARIANTS_2D) + list(R.VARIANTS_3D):
        ev = e1.copy()
        ev["variant"] = v
        rows.append(ev)
        for _, r in e1.iterrows():
            pairs_rows.append({
                "variant": v,
                "name": r["name"],
                "signal_session_1d": r["signal_date"],
                "signal_session_other": r["signal_date"],
                "delay_sessions": 0.0,
                "confirmation_cost_pct": 0.01,
                "mfe21_consumed_frac": 0.1,
                "no_confirmation": False,
            })
    events = pd.concat(rows, ignore_index=True)
    pairs = pd.DataFrame(pairs_rows)
    return events, pairs, state


def test_support_table_from_compute_all_is_complete():
    events, pairs, state = _tiny_panel_for_compute_all(identical_cells=False, fast_worse=False, tiny_floors=True)
    stats = R.compute_all(events, pairs, state, n_boot=20, seed=20261004)
    assert set(stats["support"].keys()) == set(R.all_support_cell_ids())
    for cid, rec in stats["support"].items():
        assert "n_events" in rec and "n_months" in rec and "n_names" in rec
        assert "meets_floor" in rec
        assert isinstance(rec["meets_floor"], bool)


# ────────────────────── J1 ──────────────────────
def test_compute_all_paired_zero():
    """J1 — two cells with identical values in identical months ⇒ boot DiD == 0.

    Mutant M7 (each cell draws its own months inside gap_pack) must FAIL this.
    """
    events, pairs, state = _tiny_panel_for_compute_all(identical_cells=True, fast_worse=False, tiny_floors=False)
    stats = R.compute_all(events, pairs, state, n_boot=80, seed=20261004)
    d = stats["did"]["3D"]["pooled"]["h10"]["delta"]
    assert d is not None and abs(float(d)) < 1e-9, f"observed pooled DiD must be ~0, got {d}"
    boot = stats["did"]["3D"].get("_boot_h10_pooled")
    assert boot is not None, "compute_all must keep pooled boot array for the J1 test"
    finite = np.asarray(boot, dtype=float)
    finite = finite[np.isfinite(finite)]
    assert finite.size >= 20, f"too few finite boot draws ({finite.size})"
    max_abs = float(np.abs(finite).max())
    assert max_abs < 1e-9, (
        f"J1 FAIL: paired bootstrap max |DiD| = {max_abs:.3e}; "
        "mutant M7 (per-cell month draws) would produce non-zero DiDs"
    )


# ────────────────────── J2 ──────────────────────
def test_compute_all_did_sign_under_h10():
    """J2 — DiD = gap(fast) − gap(persistent); fast gap < persistent gap ⇒ DiD < 0.

    Mutant M5 (persistent − fast) must FAIL this.
    """
    events, pairs, state = _tiny_panel_for_compute_all(identical_cells=False, fast_worse=True, tiny_floors=False)
    stats = R.compute_all(events, pairs, state, n_boot=40, seed=20261004)
    d = stats["did"]["3D"]["pooled"]["h10"]["delta"]
    assert d is not None and float(d) < -0.02, (
        f"J2 FAIL: pooled DiD should be clearly negative (fast gap << persistent gap), got {d}. "
        "Mutant M5 would flip the sign."
    )


# ────────────────────── J3 ──────────────────────
def test_compute_all_floors():
    """J3 — a cell under 300 events / 24 months / 100 names ⇒ meets_floor False.

    Mutant M6 (meets = True) must FAIL this.
    """
    events, pairs, state = _tiny_panel_for_compute_all(identical_cells=False, fast_worse=False, tiny_floors=True)
    stats = R.compute_all(events, pairs, state, n_boot=10, seed=20261004)
    recs = list(stats["support"].values())
    assert recs, "support table empty"
    # at least one populated cell is under all three floors
    populated = [r for r in recs if r["n_events"] > 0]
    assert populated, "no populated support cells"
    for r in populated:
        assert r["n_events"] < 300 or r["n_months"] < 24 or r["n_names"] < 100
        assert r["meets_floor"] is False, (
            "J3 FAIL: tiny cell must have meets_floor False; mutant M6 would force True"
        )
    assert stats["meta"]["floors_ok_3d"] is False
    assert stats["meta"]["floors_ok_2d"] is False


# ────────────────────── N1 verdict rule ──────────────────────
def _stat_not_supported():
    return dict(
        pooled_h10={"delta": 0.003, "ci": [-0.001, 0.007]},
        by_phase_h10={
            "p0": {"delta": 0.002, "ci": [-0.002, 0.007]},
            "p1": {"delta": 0.004, "ci": [-0.001, 0.008]},
            "p2": {"delta": 0.003, "ci": [-0.001, 0.008]},
        },
        by_era_h10={
            "2014-2019": {"delta": 0.003, "ci": [-0.002, 0.008]},
            "2020-2026": {"delta": 0.005, "ci": [-0.001, 0.011]},
        },
        n_phases_required=2,
        phases=R.PHASES_3D,
        monotonic=False,
        floors_ok=True,
    )


def _stat_supported():
    return dict(
        pooled_h10={"delta": -0.01, "ci": [-0.02, -0.005]},
        by_phase_h10={
            "p0": {"delta": -0.01, "ci": [-0.02, -0.004]},
            "p1": {"delta": -0.012, "ci": [-0.02, -0.003]},
            "p2": {"delta": -0.008, "ci": [-0.015, -0.001]},
        },
        by_era_h10={
            "2014-2019": {"delta": -0.009, "ci": [-0.02, -0.001]},
            "2020-2026": {"delta": -0.011, "ci": [-0.02, -0.002]},
        },
        n_phases_required=2,
        phases=R.PHASES_3D,
        monotonic=True,
        floors_ok=True,
    )


def test_verdict_insufficient_when_c1_broken():
    """N1 — BROKEN C1 forces INSUFFICIENT SUPPORT even when floors_ok and CI includes 0.

    Mutant MC2 (delete the BROKEN clause) must FAIL this.
    """
    ns = _stat_not_supported()
    out_b = R.compute_verdict(**ns, c1_status="BROKEN", b1_3d_verdicts=["NOT SUPPORTED"] * 3)
    assert out_b["verdict"] == "INSUFFICIENT SUPPORT"
    out_ok = R.compute_verdict(**ns, c1_status="OK", b1_3d_verdicts=["NOT SUPPORTED"] * 3)
    assert out_ok["verdict"] == "NOT SUPPORTED"
    sup = _stat_supported()
    out_s = R.compute_verdict(**sup, c1_status="OK", b1_3d_verdicts=["NOT SUPPORTED"] * 3)
    assert out_s["verdict"] == "SUPPORTED"


def test_c1_status_is_read_from_record(tmp_path):
    """N1 — production loader reads controls.status from C1 result.json.

    Mutant MC1 (hard-code OK) must FAIL this.
    """
    ns = _stat_not_supported()
    stats = {
        "did": {
            "3D": {
                "pooled": {"h10": ns["pooled_h10"]},
                "by_phase": {p: {"h10": ns["by_phase_h10"][p]} for p in R.PHASES_3D},
                "by_era": {e: {"h10": ns["by_era_h10"][e]} for e in R.ERAS},
            }
        },
        "meta": {"monotonic_3d": False, "floors_ok_3d": True},
    }
    p_broken = tmp_path / "c1_broken.json"
    p_ok = tmp_path / "c1_ok.json"
    p_broken.write_text(json.dumps({"controls": {"status": "BROKEN"}}))
    p_ok.write_text(json.dumps({"controls": {"status": "OK"}}))
    assert R.load_c1_controls_status(p_broken) == "BROKEN"
    assert R.load_c1_controls_status(p_ok) == "OK"
    lab_b = R.verdict_from_loaded_inputs(stats=stats, c1_json_path=p_broken, grain="3D")
    lab_o = R.verdict_from_loaded_inputs(stats=stats, c1_json_path=p_ok, grain="3D")
    assert lab_b["verdict"] == "INSUFFICIENT SUPPORT"
    assert lab_o["verdict"] == "NOT SUPPORTED"


# ────────────────────── N2 ──────────────────────
def test_phase_count_packet_definition():
    by_phase = {
        "p0": {"delta": -0.01, "ci": [-0.02, -0.001]},  # neg, excl 0
        "p1": {"delta": -0.01, "ci": [-0.02, 0.001]},   # neg, includes 0
        "p2": {"delta": 0.01, "ci": [0.001, 0.02]},     # pos, excl 0
        "eq0": {"delta": 0.0, "ci": [-0.02, -0.001]},  # DiD exactly 0.0, CI excl 0 — must NOT count
        "hi0": {"delta": -0.01, "ci": [-0.02, 0.0]},   # DiD < 0, CI upper bound exactly 0.0 — must NOT count
    }
    assert R.phase_count_packet(by_phase, R.PHASES_3D) == 1
    extra = tuple(R.PHASES_3D) + ("eq0", "hi0")
    assert R.phase_count_packet(by_phase, extra) == 1


def test_cost_curve_monotonic_strict():
    assert R.cost_curve_monotonic_strict(0.14, 0.158, 0.012) is False
    assert R.cost_curve_monotonic_strict(0.20, 0.15, 0.10) is True
    assert R.cost_curve_monotonic_strict(0.15, 0.15, 0.10) is False


# ────────────────────── N3 mapping ──────────────────────
def test_confirmed_share_mapping_by_key():
    """Integer-index Series.map is wrong when index order ≠ key order.

    The old code must FAIL this test; map_confirmed_by_key must pass.
    """
    # keys in this order: B, A, C
    ev_keys = [("B", pd.Timestamp("2020-01-02")), ("A", pd.Timestamp("2020-01-01")),
               ("C", pd.Timestamp("2020-01-03"))]
    # dict insertion order A, B, C with values True, False, True
    confirmed = {
        ("A", pd.Timestamp("2020-01-01")): True,
        ("B", pd.Timestamp("2020-01-02")): False,
        ("C", pd.Timestamp("2020-01-03")): True,
    }
    right = R.map_confirmed_by_key(ev_keys, confirmed)
    assert list(right) == [False, True, True]

    any_confirmed = pd.Series(
        [True, False, True],
        index=pd.RangeIndex(3),  # integer index, values in A,B,C insertion order
    )
    wrong = R.map_confirmed_by_integer_index(ev_keys, any_confirmed)
    # integer-index map aligns by position 0,1,2 — not by key — so it cannot
    # recover [False, True, True] from this Series.
    assert list(wrong) != [False, True, True], (
        "sanity: the integer-index mapping should be wrong on this synthetic"
    )


# ────────────────────── schema (records exist; no skip) ──────────────────────
REQUIRED_TOP = [
    "lane", "status", "repo_head", "inputs", "n_1d_events_joined",
    "n_1d_events_dropped_no_state", "did", "gaps", "cost_curve",
    "false_starts_avoided", "large_winners_excluded", "breadth_axis",
    "support", "verdict", "tests", "deviations",
]


def test_result_json_schema_if_present():
    path = R.OUT_JSON
    assert path.exists(), "result.json must exist (run.py writes records before pytest)"
    obj = json.loads(path.read_text())
    for k in REQUIRED_TOP:
        assert k in obj, f"missing top-level key {k}"
    assert obj["lane"] == "C2"
    for k in ("B1_events_panel_sha256", "B1_confirmation_pairs_sha256",
              "C1_rotation_state_sha256", "C1_controls_status", "B1_verdict"):
        assert k in obj["inputs"], f"missing inputs.{k}"
    assert isinstance(obj["gaps"], dict) and "3D" in obj["gaps"] and "2D" in obj["gaps"]
    assert obj["verdict"]["3D"] in {"SUPPORTED", "NOT SUPPORTED", "INSUFFICIENT SUPPORT"}
    assert obj["verdict"]["2D"] in {"SUPPORTED", "NOT SUPPORTED", "INSUFFICIENT SUPPORT"}
    assert "BROKEN" in obj["verdict"]["rule"] or "INSUFFICIENT SUPPORT otherwise" in obj["verdict"]["rule"]
    # tests field must not embed wall-clock timing
    assert " in " not in str(obj.get("tests") or "") or "passed" in str(obj.get("tests"))
    if isinstance(obj.get("tests"), str):
        assert not str(obj["tests"]).rstrip().endswith("s") or "passed" in obj["tests"]
        assert " in " not in obj["tests"]
    # era_labels is the definition table with bare keys
    assert "era_labels" in obj
    assert "2014-2019" in obj["era_labels"]
    assert "2020-2026" in obj["era_labels"]


def test_result_md_present_and_contains_answer_first():
    path = R.OUT_MD
    assert path.exists(), "RESULT.md must exist (run.py writes records before pytest)"
    text = path.read_text()
    assert "H10: INSUFFICIENT SUPPORT" in text or "H10: NOT SUPPORTED" in text or "H10: SUPPORTED" in text
    assert "COUNTERFACTUAL (if C1 controls were PASS; not a verdict):" in text
    assert text.count("COUNTERFACTUAL (if C1 controls were PASS; not a verdict):") == 1
    assert "FINAL-VINTAGE" in text and "SURVIVOR-SELECTED" in text


def test_verdict_rule_fires_insufficient_when_c1_broken():
    # keep round-0 helper coverage on evaluate_verdict
    pooled = {"delta": -0.01, "ci": [-0.02, -0.005]}
    by_phase = {
        "p0": {"delta": -0.01, "ci": [-0.02, -0.004]},
        "p1": {"delta": -0.012, "ci": [-0.02, -0.003]},
        "p2": {"delta": -0.008, "ci": [-0.015, -0.001]},
    }
    by_era = {
        "2014-2019": {"delta": -0.009, "ci": [-0.02, -0.001]},
        "2020-2026": {"delta": -0.011, "ci": [-0.02, -0.002]},
    }
    label, reasons, diag = R.evaluate_verdict(
        pooled_h10=pooled, by_phase_h10=by_phase, by_era_h10=by_era,
        n_phases_required=2, phases=R.PHASES_3D, monotonic=True, floors_ok=True,
        c1_broken=True, b1_3d_insufficient=False,
    )
    assert label == "INSUFFICIENT SUPPORT"
