"""Pytest for Lane C1 invariants.

Path safety: every test derives the repo from C1_REPO env (set by run.py's harness / CI) or
walks up from this file. Tests use pytest's `tmp_path` fixture for any scratch dir — never
hardcoded /tmp paths. The exported parquet location is read from the run module, which
itself uses _find_repo(), so a portable checkout can run the tests.
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import pytest

import run as R


# ────────────────────── shared helpers ──────────────────────
EXPECTED_COLUMNS = [
    "LP", "retention", "rotation_speed", "rotation_tercile",
    "breadth_spread", "breadth_tercile", "participation_share",
    "dfii_impulse", "dfii_tercile", "n_sectors",
]


def _write_panel(tmp_path: Path, n_sessions: int, *, seed: int = 0,
                 include_real: bool = True) -> tuple[Path, Path, pd.DatetimeIndex]:
    """Build a synthetic sector + SPY + RSP (+ optional real) under
    tmp_path/yahoo and tmp_path/fred; return (yahoo_dir, fred_dir, master_index)."""
    dates = pd.bdate_range("2024-01-01", periods=n_sessions)
    rng = np.random.default_rng(seed)
    yahoo = tmp_path / "yahoo"
    fred = tmp_path / "fred"
    yahoo.mkdir(parents=True, exist_ok=True)
    fred.mkdir(parents=True, exist_ok=True)
    sectors = {}
    for t in R.SECTOR_ETFS:
        walk = 100 + np.cumsum(rng.normal(0, 0.5, n_sessions))
        sectors[t] = pd.Series(walk, index=dates, name=t)
        df = pd.DataFrame({"close": sectors[t], "close_price": sectors[t], "volume": 0},
                          index=dates)
        df.index.name = "Date"
        df.to_parquet(yahoo / f"{t}.parquet", engine="pyarrow")
    spy = pd.Series(100 + np.cumsum(rng.normal(0, 0.5, n_sessions)), index=dates, name="SPY")
    rsp = pd.Series(100 + np.cumsum(rng.normal(0, 0.5, n_sessions)), index=dates, name="RSP")
    pd.DataFrame({"close": spy, "close_price": spy, "volume": 0}, index=dates) \
        .rename_axis("Date").to_parquet(yahoo / "SPY.parquet", engine="pyarrow")
    pd.DataFrame({"close": rsp, "close_price": rsp, "volume": 0}, index=dates) \
        .rename_axis("Date").to_parquet(yahoo / "RSP.parquet", engine="pyarrow")
    if include_real:
        real = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.01, n_sessions)),
                         index=dates, name="us10y_real")
        pd.DataFrame({"us10y_real": real}, index=dates) \
            .rename_axis("date").to_parquet(fred / "DFII10.parquet", engine="pyarrow")
    return yahoo, fred, dates


def _swap_paths(monkeypatch, yahoo: Path, rd: Path) -> tuple[object, object]:
    """Monkey-patch run.YAHOO / run.FRED for the duration of a context manager."""
    saved_yahoo = R.YAHOO
    saved_fred = R.FRED
    monkeypatch.setattr(R, "YAHOO", yahoo)
    monkeypatch.setattr(R, "FRED", rd)
    return saved_yahoo, saved_fred


def _row_matches(actual, expected) -> bool:
    """Return True if a (state) row matches the expected (raw) row element-wise."""
    if pd.isna(actual) and pd.isna(expected):
        return True
    if isinstance(actual, str) or isinstance(expected, str):
        return str(actual) == str(expected)
    return np.isclose(float(actual), float(expected), equal_nan=True)


# ────────────────────── 1. one-session shift applied at export ──────────────────────
def test_one_session_shift():
    """Exported row at date t equals the unshifted computation at t-1."""
    state = pd.read_parquet(R.OUT_PARQUET)
    raw = R.build_rotation_state_daily(shift=0)
    pairs = []
    raw_dates = raw.index
    for i in range(1, len(raw_dates)):
        t = raw_dates[i]
        t_prev = raw_dates[i - 1]
        if t in state.index:
            pairs.append((t, t_prev))
    rng = np.random.default_rng(20261004)
    rng.shuffle(pairs)
    pairs = pairs[:20]
    assert len(pairs) >= 20, f"only {len(pairs)} comparable date pairs found"
    for t, t_prev in pairs:
        for col in EXPECTED_COLUMNS:
            v_state = state.loc[t, col]
            v_raw = raw.loc[t_prev, col]
            assert _row_matches(v_state, v_raw), \
                f"{col} @ {t}: state={v_state!r} raw@t-1={v_raw!r}"


# ────────────────────── 2. no same-day leakage (R1: perturb ONE input) ──────────────────────
def _leakage_check_one_sector(monkeypatch, tmp_path: Path, fname: str, value_col: str,
                              factor: float, kind: str):
    """Perturb ONE input file at ONE date and check the PIT shift semantics.

    Panel is 1,100 sessions (above MIN_TERCILE_HISTORY=756) so the three tercile
    columns are non-NaN at target_t and the row-t identity check exercises them.
    """
    yahoo, fred, dates = _write_panel(tmp_path, n_sessions=1100, seed=42)
    _swap_paths(monkeypatch, yahoo, fred)

    if kind == "real":
        path = fred / fname
    else:
        path = yahoo / fname
    base_df = pd.read_parquet(path)
    target_t = _pick_target_date(monkeypatch, base_df, value_col, factor, fname, kind)
    state0 = R.build_rotation_state_daily()
    for col in ("rotation_tercile", "breadth_tercile", "dfii_tercile"):
        assert pd.notna(state0.loc[target_t, col]), \
            f"{col} @ {target_t} is NaN; need larger panel"

    df = pd.read_parquet(path)
    assert target_t in df.index, f"target date {target_t} missing in {path}"
    df.loc[target_t, value_col] = df.loc[target_t, value_col] * factor
    df.to_parquet(path, engine="pyarrow")
    state1 = R.build_rotation_state_daily()

    for col in EXPECTED_COLUMNS:
        assert _row_matches(state0.loc[target_t, col], state1.loc[target_t, col]), \
            f"{col} @ {target_t}: leaked: {state0.loc[target_t, col]!r} -> {state1.loc[target_t, col]!r}"

    if target_t in state1.index and target_t != state1.index[-1]:
        next_t = state1.index[state1.index.get_loc(target_t) + 1]
        if kind == "sector":
            moved = {"LP", "rotation_speed", "rotation_tercile", "retention", "participation_share"}
        elif kind == "rsp":
            moved = {"breadth_spread", "breadth_tercile"}
        elif kind == "real":
            moved = {"dfii_impulse", "dfii_tercile"}
        elif kind == "spy":
            moved = {"LP", "rotation_speed", "rotation_tercile", "retention",
                     "breadth_spread", "breadth_tercile", "participation_share"}
        any_moved = False
        for col in moved:
            if not _row_matches(state0.loc[next_t, col], state1.loc[next_t, col]):
                any_moved = True
                break
        assert any_moved, f"row {next_t} did not change despite {kind} perturbation at {target_t}"


def _pick_target_date(monkeypatch, base_df: pd.DataFrame, value_col: str, factor: float,
                      fname: str, kind: str) -> pd.Timestamp:
    """Find the first output date where the perturbation actually changes the rank."""
    state0 = R.build_rotation_state_daily()
    valid_idx = state0.dropna(how="all").index
    candidates = valid_idx[800::10]
    assert len(candidates) > 0, "no candidate dates for rank-change probe"
    for target_t in candidates:
        yahoo_dir = R.YAHOO
        fred_dir = R.FRED
        is_real = (kind == "real")
        path = (fred_dir / fname) if is_real else (yahoo_dir / fname)
        df = pd.read_parquet(path)
        if target_t not in df.index:
            continue
        orig = df.loc[target_t, value_col]
        df.loc[target_t, value_col] = orig * factor
        df.to_parquet(path, engine="pyarrow")
        state1 = R.build_rotation_state_daily()
        df.loc[target_t, value_col] = orig
        df.to_parquet(path, engine="pyarrow")
        next_t_idx = state0.index.get_loc(target_t) + 1
        if next_t_idx >= len(state0.index):
            continue
        next_t = state0.index[next_t_idx]
        if kind == "sector":
            if not _row_matches(state0.loc[next_t, "LP"], state1.loc[next_t, "LP"]):
                return target_t
        elif kind in ("spy", "rsp"):
            if not _row_matches(state0.loc[next_t, "breadth_spread"],
                                state1.loc[next_t, "breadth_spread"]):
                return target_t
        elif kind == "real":
            if not _row_matches(state0.loc[next_t, "dfii_impulse"],
                                state1.loc[next_t, "dfii_impulse"]):
                return target_t
    raise AssertionError(
        f"Could not find a target date where the {kind} perturbation at factor={factor} "
        "changes the rank/r21 — test is vacuous for this factor"
    )


def test_no_same_day_leakage_xlk(monkeypatch, tmp_path):
    _leakage_check_one_sector(monkeypatch, tmp_path, "XLK.parquet", "close",
                              1.5, kind="sector")


def test_no_same_day_leakage_rsp(monkeypatch, tmp_path):
    _leakage_check_one_sector(monkeypatch, tmp_path, "RSP.parquet", "close",
                              1.5, kind="rsp")


def test_no_same_day_leakage_dfii10(monkeypatch, tmp_path):
    _leakage_check_one_sector(monkeypatch, tmp_path, "DFII10.parquet", "us10y_real",
                              1.5, kind="real")


# ────────────────────── 3. leak-detection power (R1 power check) ──────────────────────
def test_leak_detection_power_with_shift_zero(monkeypatch, tmp_path):
    """With SHIFT=0 the XLK perturbation MUST change row t — proves the leak test
    above can detect a leak when one exists."""
    yahoo, fred, dates = _write_panel(tmp_path, n_sessions=1100, seed=11)
    _swap_paths(monkeypatch, yahoo, fred)
    target_t = _pick_target_date(monkeypatch, pd.read_parquet(yahoo / "XLK.parquet"),
                                  "close", 1.5, "XLK.parquet", "sector")
    state0 = R.build_rotation_state_daily(shift=0)
    df = pd.read_parquet(yahoo / "XLK.parquet")
    df.loc[target_t, "close"] = df.loc[target_t, "close"] * 1.5
    df.to_parquet(yahoo / "XLK.parquet", engine="pyarrow")
    state1 = R.build_rotation_state_daily(shift=0)

    changed_cols = [c for c in EXPECTED_COLUMNS
                    if not _row_matches(state0.loc[target_t, c], state1.loc[target_t, c])]
    assert changed_cols, \
        f"Power check FAILED: SHIFT=0 + XLK perturbation at {target_t} did not move any row-t column"


# ────────────────────── 3a. G1 round-3: pipeline cuts match tercile_cuts (Test A) ─────
def test_pipeline_cuts_match_tercile_cuts(monkeypatch, tmp_path):
    """On a 1,100-session synthetic panel, for ≥ 50 sessions t ≥ MIN_TERCILE_HISTORY
    the pipeline's cut (exposed via rotation_cuts_daily.parquet sidecar) at t must
    equal tercile_cuts(v_arr[:i]) where v_arr is the UNSHIFTED, UNTRIMMED value
    array the pipeline feeds into compute_cuts, and i is the position of t in
    that full master index — same call path (G1 round-3).
    """
    yahoo, fred, dates = _write_panel(tmp_path, n_sessions=1100, seed=2024)
    _swap_paths(monkeypatch, yahoo, fred)
    state = R.build_rotation_state_daily()
    cuts = R.build_rotation_cuts()
    master, lp_un, bs_un, dfii_un = R._unshifted_value_arrays()

    eligible = [d for d in state.index if state.index.get_loc(d) >= R.MIN_TERCILE_HISTORY]
    assert len(eligible) >= 50, f"need ≥50 eligible t, got {len(eligible)}"
    rng = np.random.default_rng(20261004)
    sampled = rng.choice(eligible, size=50, replace=False)

    var_arrays = {"LP": lp_un.to_numpy(), "breadth_spread": bs_un.to_numpy(),
                  "dfii_impulse": dfii_un.to_numpy()}
    for var in ["LP", "breadth_spread", "dfii_impulse"]:
        v_arr = var_arrays[var]
        cut_lo_col = f"{var}_cut_lo"
        cut_hi_col = f"{var}_cut_hi"
        for t in sampled:
            i_master = master.get_loc(t)
            # The sidecar at t = unshifted cut at (i_master - DEFAULT_SHIFT) — the
            # pipeline shifts cuts by DEFAULT_SHIFT before trimming.
            expected_lo, expected_hi = R.tercile_cuts(v_arr, i_master - R.DEFAULT_SHIFT)
            actual_lo = cuts.loc[t, cut_lo_col]
            actual_hi = cuts.loc[t, cut_hi_col]
            if pd.isna(expected_lo):
                assert pd.isna(actual_lo), \
                    f"{var} cut_lo at {t}: pipeline={actual_lo!r} expected=NaN"
                assert pd.isna(actual_hi)
            else:
                assert actual_lo == pytest.approx(expected_lo, abs=0, rel=0), (
                    f"{var} cut_lo at {t}: pipeline={actual_lo} vs tercile_cuts={expected_lo}"
                )
                assert actual_hi == pytest.approx(expected_hi, abs=0, rel=0), (
                    f"{var} cut_hi at {t}: pipeline={actual_hi} vs tercile_cuts={expected_hi}"
                )


# ────────────────────── 3b. G1 round-3: planted include-t mutant detected (Test B) ─
def test_planted_include_t_leak_caught_by_cuts(monkeypatch, tmp_path):
    """Plant an include-t leak in tercile_cuts: cuts at t read v[:t+1] instead of
    v[:t]. The test compares the pipeline's cuts (under the leak) against the
    CLEAN expected (using the original, pre-monkeypatch tercile_cuts) so the
    leak is detected. G1 round-3.
    """
    yahoo, fred, dates = _write_panel(tmp_path, n_sessions=1100, seed=99)
    _swap_paths(monkeypatch, yahoo, fred)

    # Capture the ORIGINAL clean tercile_cuts BEFORE monkeypatching
    clean_tercile_cuts = R.tercile_cuts

    def leaked_cuts(v_arr, i, lo_q=1.0 / 3, hi_q=2.0 / 3, min_history=R.MIN_TERCILE_HISTORY):
        n = len(v_arr)
        if (i + 1) <= 0:
            return float("nan"), float("nan")
        prior = v_arr[: min(i + 1, n)]
        prior = prior[~np.isnan(prior)]
        if len(prior) < min_history:
            return float("nan"), float("nan")
        return float(np.quantile(prior, lo_q)), float(np.quantile(prior, hi_q))

    monkeypatch.setattr(R, "tercile_cuts", leaked_cuts)
    state = R.build_rotation_state_daily()
    cuts = R.build_rotation_cuts()
    master, lp_un, bs_un, dfii_un = R._unshifted_value_arrays()

    eligible = [d for d in state.index if state.index.get_loc(d) >= R.MIN_TERCILE_HISTORY]
    assert len(eligible) >= 5, "need ≥5 eligible t"
    rng = np.random.default_rng(7)
    sampled = rng.choice(eligible, size=5, replace=False)

    var_arrays = {"LP": lp_un.to_numpy(), "breadth_spread": bs_un.to_numpy(),
                  "dfii_impulse": dfii_un.to_numpy()}
    leak_detected = False
    for var in ["LP", "breadth_spread", "dfii_impulse"]:
        v_arr = var_arrays[var]
        cut_lo_col = f"{var}_cut_lo"
        cut_hi_col = f"{var}_cut_hi"
        for t in sampled:
            i_master = master.get_loc(t)
            # Use CLEAN tercile_cuts (captured before monkeypatch) for the expected
            expected_lo, expected_hi = clean_tercile_cuts(v_arr, i_master - R.DEFAULT_SHIFT)
            actual_lo = cuts.loc[t, cut_lo_col]
            actual_hi = cuts.loc[t, cut_hi_col]
            if pd.isna(expected_lo):
                continue
            if (not np.isclose(actual_lo, expected_lo, atol=1e-12)
                    or not np.isclose(actual_hi, expected_hi, atol=1e-12)):
                leak_detected = True
                break
        if leak_detected:
            break
    assert leak_detected, (
        "Planted include-t leak NOT detected: pipeline cuts at t >= MIN_TERCILE_HISTORY "
        "still match the clean tercile_cuts(v_arr[:i_master - DEFAULT_SHIFT]) under "
        "the leak. The leak test is vacuous for the include-t class."
    )


# ────────────────────── 3c. M1 Test B: unshifted V[t0]=+1e6 via compute_cuts ─
def test_pipeline_cut_unchanged_when_v_prior_only(monkeypatch, tmp_path):
    """M1 Test B. 1,100-session synthetic panel; unshifted V at one t0 ≥ 800 is
    set to +1e6; the pipeline's own compute_cuts path is re-run.

    Clean code: cut(t0) identical (reads v[:t0] only) and cut(t0+1) different
    (t0 now sits in the prior window). The include-t mutant at compute_cuts
    (`tercile_cuts(v_arr, min(i + 1, n))`) changes cut(t0) and this test FAILS.
    """
    yahoo, fred, dates = _write_panel(tmp_path, n_sessions=1100, seed=33)
    _swap_paths(monkeypatch, yahoo, fred)
    master, lp, _bs, _dfii = R._unshifted_value_arrays()
    v_arr = lp.to_numpy(dtype=float)
    assert len(v_arr) >= 1100, f"synthetic panel too short: {len(v_arr)}"

    t0 = None
    for i in range(800, len(v_arr) - 1):
        cl_probe, ch_probe = R.tercile_cuts(v_arr, i)
        cl_next, ch_next = R.tercile_cuts(v_arr, i + 1)
        if (np.isfinite(cl_probe) and np.isfinite(ch_probe)
                and np.isfinite(cl_next) and np.isfinite(ch_next)
                and np.isfinite(v_arr[i])):
            t0 = i
            break
    assert t0 is not None and t0 >= 800, "no eligible t0 ≥ 800 with finite cuts"

    cl0, ch0 = R.compute_cuts(v_arr)
    assert np.isfinite(cl0[t0]) and np.isfinite(ch0[t0]), f"cut at t0={t0} is NaN"
    assert np.isfinite(cl0[t0 + 1]) and np.isfinite(ch0[t0 + 1])

    v1 = v_arr.copy()
    v1[t0] = 1.0e6
    cl1, ch1 = R.compute_cuts(v1)

    assert cl0[t0] == cl1[t0] and ch0[t0] == ch1[t0], (
        f"cut at t0={t0} changed after v[{t0}]=+1e6: "
        f"({cl0[t0]}, {ch0[t0]}) -> ({cl1[t0]}, {ch1[t0]})"
    )
    assert (cl0[t0 + 1] != cl1[t0 + 1]) or (ch0[t0 + 1] != ch1[t0 + 1]), (
        f"cut at t0+1={t0 + 1} did not change after v[{t0}]=+1e6 — "
        "Test B has no power"
    )


# ────────────────────── 4. tercile cuts at t use only dates < t (R2) ──────────────────────
def test_tercile_cut_uses_prior_only():
    """Pure function tercile_cuts(v_arr, i) reads only v_arr[:i]."""
    rng = np.random.default_rng(7)
    v = rng.normal(0, 1, 1500)
    cl0, ch0 = R.tercile_cuts(v, 800)
    p1 = v.copy()
    p1[800] = 1.0e6
    cl1, ch1 = R.tercile_cuts(p1, 800)
    assert cl0 == cl1 and ch0 == ch1, \
        f"cut at i=800 changed: ({cl0}, {ch0}) -> ({cl1}, {ch1})"
    p2 = v.copy()
    p2[801:] = 1.0e6
    cl2, ch2 = R.tercile_cuts(p2, 800)
    assert cl0 == cl2 and ch0 == ch2, \
        f"cut at i=800 changed by mutation after 800: ({cl0}, {ch0}) -> ({cl2}, {ch2})"
    # Power check: include-t variant (v_arr[:i+1]) produces a different cut at i=800
    prior_incl = p1[: 800 + 1]
    prior_incl = prior_incl[~np.isnan(prior_incl)]
    cl_incl = float(np.quantile(prior_incl, 1.0 / 3))
    ch_incl = float(np.quantile(prior_incl, 2.0 / 3))
    assert (cl0, ch0) != (cl_incl, ch_incl), (
        "Include-t variant did not change the cut at i=800 even with v[800]=+1e6 — "
        "power check is vacuous for the include-t class"
    )


def test_tercile_cut_power_include_t():
    """Include-t variant (v_arr[:i+1]) produces a different cut at t for at least one i."""
    rng = np.random.default_rng(7)
    v = rng.normal(0, 1, 1500)
    saw_difference = False
    for i in (800, 1000, 1200):
        cl_excl, ch_excl = R.tercile_cuts(v, i)
        prior = v[: i + 1]
        prior = prior[~np.isnan(prior)]
        cl_incl = float(np.quantile(prior, 1.0 / 3))
        ch_incl = float(np.quantile(prior, 2.0 / 3))
        if (cl_excl, ch_excl) != (cl_incl, ch_incl):
            saw_difference = True
            break
    assert saw_difference, "Include-t variant never changed the cut at any probe index — power check fails"


# ────────────────────── 5. controls PASS/FAIL check (R9: assert values) ──────────────────────
def test_controls_status_and_values():
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    ctl = res["controls"]
    for k in ("ar1_lag21", "ar1_pass", "mean_LP_fast_windows", "mean_LP_persistent_windows",
              "mean_LP_overall", "window_means", "fast_share_by_window", "direction_pass",
              "window_n", "lp_autocorr_profile", "status"):
        assert k in ctl, f"missing key {k}"
    assert ctl["status"] in ("PASS", "BROKEN")
    assert ctl["status"] == "BROKEN", f"expected BROKEN, got {ctl['status']}"

    state = pd.read_parquet(R.OUT_PARQUET)
    lp = state["LP"]
    ar1_recomputed = float(lp.dropna().autocorr(lag=21))
    assert abs(ctl["ar1_lag21"] - ar1_recomputed) < 1e-4, (
        f"ar1_lag21 = {ctl['ar1_lag21']} disagrees with parquet recompute "
        f"{ar1_recomputed:.4f}"
    )
    assert ctl["ar1_lag21"] < 0.5, "ar1_lag21 must remain below the 0.5 PASS gate"
    assert ctl["ar1_pass"] is False
    # Window means — recompute and assert at 1e-4
    for start, end in (("2020-11-09", "2020-12-31"), ("2021-02-01", "2021-03-31"),
                       ("2022-01-03", "2022-06-30"), ("2023-03-01", "2023-06-30")):
        m = float(lp.loc[start:end].mean())
        cls = "fast" if start < "2022-01-01" else "persistent"
        tag = f"{cls}:{start}..{end}"
        assert abs(ctl["window_means"][tag] - m) < 1e-4, (
            f"{tag}: json={ctl['window_means'][tag]} vs recompute={m:.4f}"
        )
    mean_fast = float(np.nanmean([ctl["window_means"][k] for k in ctl["window_means"] if k.startswith("fast")]))
    mean_persist = float(np.nanmean([ctl["window_means"][k] for k in ctl["window_means"] if k.startswith("persistent")]))
    assert abs(ctl["mean_LP_fast_windows"] - mean_fast) < 1e-4
    assert abs(ctl["mean_LP_persistent_windows"] - mean_persist) < 1e-4
    assert ctl["direction_pass"] is True
    assert ctl["mean_LP_fast_windows"] < ctl["mean_LP_persistent_windows"]
    # LP autocorr profile — recompute and assert at 1e-4
    for k in (1, 5, 10, 21, 42, 63):
        recomputed = float(lp.dropna().autocorr(lag=k))
        assert abs(ctl["lp_autocorr_profile"][f"lag_{k}"] - recomputed) < 1e-4, (
            f"lag_{k}: json={ctl['lp_autocorr_profile'][f'lag_{k}']} vs recompute={recomputed:.4f}"
        )


# ────────────────────── 5b. window n_sessions recompute (G4 round-3) ─────
def test_window_n_recompute():
    """G4 round-3: assert every window's n_sessions recomputed from the parquet."""
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    ctl = res["controls"]
    state = pd.read_parquet(R.OUT_PARQUET)
    for tag in ("fast:2020-11-09..2020-12-31", "fast:2021-02-01..2021-03-31",
                "persistent:2022-01-03..2022-06-30", "persistent:2023-03-01..2023-06-30"):
        cls, rng_str = tag.split(":")
        start, end = rng_str.split("..")
        n_sessions_recomputed = int(len(state.loc[start:end]))
        assert ctl["window_n"][tag]["n_sessions"] == n_sessions_recomputed, (
            f"{tag}: n_sessions json={ctl['window_n'][tag]['n_sessions']} vs "
            f"recompute={n_sessions_recomputed}"
        )


# ────────────────────── 6. agreement table values (R9 + E4 + G4) ──────────────────────
def test_agreement_table_values():
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    ag = res["agreement"]
    for k in ("contingency_flag", "kappa_persistent", "kappa_fast", "kappa_overall",
              "kappa_by_era", "contingency_transition", "pit_class_share_by_era",
              "n_joined_raw", "n_joined_used", "n_dropped_nan_tercile", "join_end_date",
              "era_n"):
        assert k in ag, f"missing key {k}"
    assert ag["n_joined_used"] == 6124, f"n_joined_used = {ag['n_joined_used']}, expected 6124"
    assert ag["n_joined_raw"] == 6880, f"n_joined_raw = {ag['n_joined_raw']}, expected 6880"
    assert ag["n_dropped_nan_tercile"] == 756
    assert ag["join_end_date"] == "2026-07-02"
    assert ag["era_n"]["<=2009"] == 1975
    assert ag["era_n"]["2010-2019"] == 2516
    assert ag["era_n"]["2020-2026"] == 1633
    assert abs(ag["kappa_persistent"] - (-0.0129)) < 1e-3, \
        f"kappa_persistent={ag['kappa_persistent']}, expected -0.0129"
    assert ag["kappa_overall"] == ag["kappa_persistent"]
    assert "kappa_fast" in ag and ag["kappa_fast"] is not None

    state = pd.read_parquet(R.OUT_PARQUET)
    regime = pd.read_parquet(R.REPO / "data/regime/regime_v2_pit.parquet")
    regime.index = pd.DatetimeIndex(pd.to_datetime(regime.index)).normalize()
    regime = regime[~regime.index.duplicated(keep="last")].sort_index()
    j = state.join(regime[["flag_rotation_persistence"]], how="inner")
    j = j.dropna(subset=["rotation_tercile", "flag_rotation_persistence"])
    rot = j["rotation_tercile"].astype(str)
    flag = j["flag_rotation_persistence"].astype(bool)

    # G4 round-3: assert ALL three era kappas against recomputed values
    def _recompute_kappa(sub_df, label: str):
        a = (sub_df["rotation_tercile"].astype(str) == label).astype(int).to_numpy() == 1
        b = sub_df["flag_rotation_persistence"].astype(bool).to_numpy()
        po = float((a == b).mean())
        p1 = float(a.mean())
        p2 = float(b.mean())
        pe = p1 * p2 + (1 - p1) * (1 - p2)
        return (po - pe) / (1 - pe) if pe != 1.0 else float("nan")

    for era in ("<=2009", "2010-2019", "2020-2026"):
        if era == "<=2009":
            sub_era = j[j.index.to_series().apply(lambda d: d.year <= 2009)]
        elif era == "2010-2019":
            sub_era = j[j.index.to_series().apply(lambda d: 2010 <= d.year <= 2019)]
        else:
            sub_era = j[j.index.to_series().apply(lambda d: d.year >= 2020)]
        k_fast_recomputed = _recompute_kappa(sub_era, "fast")
        k_pers_recomputed = _recompute_kappa(sub_era, "persistent")
        assert abs(ag["kappa_by_era"][era]["fast"] - k_fast_recomputed) < 1e-4, (
            f"{era} kappa_fast json={ag['kappa_by_era'][era]['fast']} vs "
            f"recompute={k_fast_recomputed:.4f}"
        )
        assert abs(ag["kappa_by_era"][era]["persistent"] - k_pers_recomputed) < 1e-4, (
            f"{era} kappa_persistent json={ag['kappa_by_era'][era]['persistent']} vs "
            f"recompute={k_pers_recomputed:.4f}"
        )
        assert ag["kappa_by_era"][era]["n"] == len(sub_era), (
            f"{era} n json={ag['kappa_by_era'][era]['n']} vs recompute={len(sub_era)}"
        )

    # kappa_fast and kappa_persistent overall recompute
    k_fast_overall = _recompute_kappa(j, "fast")
    k_pers_overall = _recompute_kappa(j, "persistent")
    assert abs(ag["kappa_fast"] - k_fast_overall) < 1e-4, (
        f"kappa_fast json={ag['kappa_fast']} vs recompute={k_fast_overall:.4f}"
    )
    assert abs(ag["kappa_persistent"] - k_pers_overall) < 1e-4, (
        f"kappa_persistent json={ag['kappa_persistent']} vs recompute={k_pers_overall:.4f}"
    )

    # G4 round-3: assert EVERY contingency cell (rotation_tercile × flag_rotation_persistence)
    for rt in ("fast", "mid", "persistent"):
        for f_val in (True, False):
            count_recomputed = int(((rot == rt) & (flag == f_val)).sum())
            json_val = ag["contingency_flag"][rt][str(f_val)]
            assert json_val == count_recomputed, (
                f"contingency_flag[{rt}][{f_val}] json={json_val} vs recompute={count_recomputed}"
            )
    # Transition state contingency — assert every cell
    j_full = state.join(regime[["flag_rotation_persistence", "transition_state", "pit_class"]],
                        how="inner")
    j_full = j_full.dropna(subset=["rotation_tercile", "flag_rotation_persistence"])
    rot_full = j_full["rotation_tercile"].astype(str)
    ts_full = j_full["transition_state"].astype(str).fillna("NA")
    cats = sorted(ts_full.unique().tolist())
    for rt in ("fast", "mid", "persistent"):
        for c in cats:
            count_recomputed = int(((rot_full == rt) & (ts_full == c)).sum())
            json_val = ag["contingency_transition"][rt].get(c, 0)
            assert json_val == count_recomputed, (
                f"contingency_transition[{rt}][{c}] json={json_val} vs recompute={count_recomputed}"
            )

    # kappa_by_era must carry persistent + fast + n
    for era in ("<=2009", "2010-2019", "2020-2026"):
        assert "persistent" in ag["kappa_by_era"][era]
        assert "fast" in ag["kappa_by_era"][era]
        assert "n" in ag["kappa_by_era"][era]


# ────────────────────── 6b. calibrated_control recompute (G5 + M4) ──────────
def test_calibrated_control_recompute():
    """G5 + M4: recompute p95/median/p5 from stored null.draws (200 lag-21
    autocorrelations, one per permutation panel) and assert them against the
    stored summary at 1e-4; re-evaluate the AND-rule; observed lag-21 must
    equal _lp_autocorr(LP, 21) from the parquet at 1e-4.

    A calibrated_status=PASS tamper fails the rule assertion. A p95_lag21=-0.5
    tamper fails the draws-vs-summary assertion (the draws still produce +0.0498).
    """
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    cc = res["calibrated_control"]

    state = pd.read_parquet(R.OUT_PARQUET)
    observed_recomputed = float(R._lp_autocorr(state["LP"], R.LAG))
    assert abs(cc["observed_lag21"] - observed_recomputed) < 1e-4, (
        f"observed_lag21 json={cc['observed_lag21']} vs recompute={observed_recomputed:.4f}"
    )

    draws = np.asarray(cc["null"]["draws"], dtype=float)
    assert len(draws) == 200, f"null.draws length {len(draws)} != 200"
    assert cc["null"]["n_used"] == 200
    p95_from_draws = float(np.percentile(draws, 95))
    median_from_draws = float(np.median(draws))
    p5_from_draws = float(np.percentile(draws, 5))
    assert abs(p95_from_draws - cc["null"]["p95_lag21"]) < 1e-4, (
        f"p95 from draws={p95_from_draws} vs stored {cc['null']['p95_lag21']}"
    )
    assert abs(median_from_draws - cc["null"]["median_lag21"]) < 1e-4, (
        f"median from draws={median_from_draws} vs stored {cc['null']['median_lag21']}"
    )
    assert abs(p5_from_draws - cc["null"]["p5_lag21"]) < 1e-4, (
        f"p5 from draws={p5_from_draws} vs stored {cc['null']['p5_lag21']}"
    )
    assert abs(cc["null"]["p95_lag21"] - 0.0498) < 1e-4, (
        f"stored p95_lag21={cc['null']['p95_lag21']} != frozen +0.0498"
    )

    # Re-evaluate the pre-declared rule from stored stats
    null_p95 = cc["null"]["p95_lag21"]
    pos_median = cc["positive_control"]["median_lag21"]
    observed = cc["observed_lag21"]
    pass_rule = bool(
        np.isfinite(null_p95) and np.isfinite(pos_median)
        and observed > null_p95 and observed >= 0.5 * pos_median
    )
    expected_status = "CALIBRATED_PASS" if pass_rule else "CALIBRATED_FAIL"
    assert cc["calibrated_status"] == expected_status, (
        f"calibrated_status json={cc['calibrated_status']} vs recomputed={expected_status}"
    )


def test_positive_control_drifts_std_equals_cs_std():
    """M2: np.std(positive_control_drifts(cs_std), ddof=0) == cs_std.

    Deleting the rescale in positive_control_drifts makes this FAIL.
    """
    for cs_std in (0.030204, 0.01, 1.0):
        drifts = R.positive_control_drifts(cs_std, n_sectors=len(R.SECTOR_ETFS))
        got = float(np.std(drifts, ddof=0))
        assert abs(got - cs_std) < 1e-12, (
            f"std(drifts, ddof=0)={got} vs cs_std={cs_std}"
        )


def test_idio_cs_std_4dp_deviation_disclosed():
    """M3: the 4-dp idio_std == cs_std deviation is recorded in both files."""
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    needle = R.IDIO_CS_4DP_DEVIATION
    assert any(needle in str(d) for d in res["deviations"]), (
        f"result.json deviations missing {needle!r}; got {res['deviations']!r}"
    )
    md = R.OUT_RESULT_MD.read_text()
    assert needle in md, f"RESULT.md missing {needle!r}"


# ────────────────────── 7. parquet schema (R9: exact columns + dtypes) ──────────────────────
def test_parquet_columns_and_dtypes():
    df = pd.read_parquet(R.OUT_PARQUET)
    assert list(df.columns) == EXPECTED_COLUMNS, \
        f"column mismatch: {list(df.columns)} vs {EXPECTED_COLUMNS}"
    assert df.index.name == "date"
    assert pd.api.types.is_float_dtype(df["LP"])
    assert pd.api.types.is_float_dtype(df["retention"])
    assert pd.api.types.is_float_dtype(df["rotation_speed"])
    assert (df["rotation_tercile"].dtype == object
            or pd.api.types.is_string_dtype(df["rotation_tercile"]))
    assert pd.api.types.is_float_dtype(df["breadth_spread"])
    assert (df["breadth_tercile"].dtype == object
            or pd.api.types.is_string_dtype(df["breadth_tercile"]))
    assert pd.api.types.is_float_dtype(df["participation_share"])
    assert pd.api.types.is_float_dtype(df["dfii_impulse"])
    assert (df["dfii_tercile"].dtype == object
            or pd.api.types.is_string_dtype(df["dfii_tercile"]))
    assert str(df["n_sectors"].dtype) == "Int64"
    assert df.index[0].strftime("%Y-%m-%d") == "1999-02-25"
    assert df.index[-1].strftime("%Y-%m-%d") == "2026-09-30"
    assert len(df) == 6942

    # cuts sidecar schema
    cuts = pd.read_parquet(R.OUT_CUTS_PARQUET)
    expected_cut_cols = [
        "LP_cut_lo", "LP_cut_hi", "breadth_spread_cut_lo", "breadth_spread_cut_hi",
        "dfii_impulse_cut_lo", "dfii_impulse_cut_hi",
    ]
    assert list(cuts.columns) == expected_cut_cols, \
        f"cuts columns mismatch: {list(cuts.columns)} vs {expected_cut_cols}"
    assert len(cuts) == 6942


# ────────────────────── 8. test summary sidecar (R5 round-2: full string + mtime) ─────
def test_test_summary_sidecar_full_string_and_mtime():
    """E3 round-2 / G7 round-3: the three copies of the pytest summary must be byte-identical
    as FULL strings (no leading-prefix match), AND the sidecar's mtime must be
    >= result.json's mtime (the sidecar is the freshest artifact).

    After orchestrator stamps result.json with pass/skip/fail counts (G7 round-3:
    no wall time in result.json), reconstruct the pytest-style summary from counts
    for the equality check.
    """
    p = R.OUT_TEST_SUMMARY
    if not p.exists():
        pytest.skip(
            f"sidecar {p} not yet written — orchestrator writes it AFTER pytest"
        )
    sidecar_text = p.read_text().strip()
    assert sidecar_text, "_test_summary.txt is empty"
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    if not res.get("tests_pass"):
        pytest.skip("Orchestrator has not yet stamped result.json")
    md_text = R.OUT_RESULT_MD.read_text()
    assert "## Tests" in md_text, "RESULT.md missing ## Tests heading"
    tests_section = md_text.split("## Tests", 1)[1]
    md_match = re.search(r"```\s*\n(.+?)\n```", tests_section)
    assert md_match, "RESULT.md missing ## Tests code fence"
    md_summary = md_match.group(1).strip()

    # Reconstruct summary from counts (no wall time per G7). The sidecar and
    # RESULT.md carry the FULL pytest line (with wall time); result.json carries
    # counts only. Verify the prefix containing the counts matches.
    counts_summary = f"{res['tests_pass']} passed"
    if res.get("tests_skip"):
        counts_summary += f", {res['tests_skip']} skipped"
    if res.get("tests_fail"):
        counts_summary += f", {res['tests_fail']} failed"
    assert sidecar_text.startswith(counts_summary), (
        f"sidecar ({sidecar_text!r}) does not start with counts_summary ({counts_summary!r})"
    )
    assert md_summary.startswith(counts_summary), (
        f"md ({md_summary!r}) does not start with counts_summary ({counts_summary!r})"
    )
    # sidecar and md carry the same full pytest line and must be byte-identical
    assert sidecar_text == md_summary, (
        f"sidecar ({sidecar_text!r}) != md ({md_summary!r})"
    )

    sidecar_mtime = p.stat().st_mtime
    json_mtime = R.OUT_RESULT_JSON.stat().st_mtime
    md_mtime = R.OUT_RESULT_MD.stat().st_mtime
    assert sidecar_mtime >= json_mtime, (
        f"sidecar mtime {sidecar_mtime} < result.json mtime {json_mtime}"
    )
    assert R.OUT_HASHES.stat().st_mtime >= sidecar_mtime, (
        "hashes.txt mtime not the newest — orchestrator did not write it last"
    )


# ────────────────────── 9. hashes.txt repo-relative (G7 round-3) ─────
def test_hashes_txt_repo_relative():
    """G7 round-3: hashes.txt paths must be repo-relative so `shasum -a 256 -c hashes.txt`
    from the repo root works without sed."""
    p = R.OUT_HASHES
    if not p.exists():
        pytest.skip("hashes.txt not yet written")
    text = p.read_text()
    repo = R.REPO
    for line in text.splitlines():
        if not line.strip():
            continue
        # Format: `<hex>  <relative-path>` — path must NOT be absolute
        parts = line.split("  ")
        assert len(parts) == 2, f"unexpected line format: {line!r}"
        hex_hash, path = parts
        assert len(hex_hash) == 64, f"bad hash: {hex_hash!r}"
        assert not path.startswith("/"), f"absolute path in hashes.txt: {path}"
        assert not path.startswith("~"), f"home-relative path in hashes.txt: {path}"
        # Verify the file exists at the repo-relative path
        assert (repo / path).exists(), f"missing file: {path}"