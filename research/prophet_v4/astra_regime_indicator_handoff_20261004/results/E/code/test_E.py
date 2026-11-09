"""Tests for E lane invariants (round-1 repair; K1–K12).

NOT DONE UNLESS coverage:
  (1) regime join never uses a row dated on or after the signal_date (poison).
  (2) each family feature at t is unchanged when a close AFTER t is perturbed
      and changes when a close AT or BEFORE t (that the feature uses) is perturbed.
  (3) bootstrap is month-clustered; an unclustered resample FAILS the cluster
      invariant (K6); a keep-all-months mutant (mutation B) also fails it.
  (4) Holm step-down on a fixed vector against hand-computed adjusted p-values.
  (5) twelve-test table in RESULT.md and result.json read the same numbers.
  (6) every drop is counted by reason.
  (7) hashes.txt verifies.
  K1 floor gate counts eight era cells; pooled-6 mutant fails the assertion.
  K2 weighted bootstrap SE matches analytic cluster SE; isin mutant fails it.
  K5 regime-clock citations resolve to real file:line fragments.
  K8 participation warm-up names are excluded from the denominator.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
_default_repo = RESULTS_DIR.parent.parent.parent.parent.parent

REPO = Path(os.environ.get("E_REPO", str(_default_repo)))

if not (REPO / "engine").is_dir():
    raise RuntimeError(f"derived REPO does not look right: {REPO}")

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import features as F  # noqa: E402
import stats as S  # noqa: E402


# ───────────────────────────────────────────────────────────────── #
# (1) regime join — STRICTLY BEFORE the signal_date (poison test)
# ───────────────────────────────────────────────────────────────── #
def test_regime_join_strictly_before_signal_date_poisons_exact_match():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]).values.astype("datetime64[ns]")
    rg = pd.DataFrame({
        "growth_score": [0.5, 0.1, -0.5],
        "n_flags": [0, 2, 1],
        "quad": ["Q1", "Q2", "Q3"],
        "recession": [False, False, True],
        "transition_ratcheted": [True, False, False],
    }, index=pd.DatetimeIndex(dates))

    events = pd.DataFrame({
        "variant": ["1D", "1D", "1D"],
        "name": ["A", "B", "C"],
        "signal_date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]).values.astype("datetime64[ns]"),
        "entry_date": pd.to_datetime(["2020-01-03"] * 3).values.astype("datetime64[ns]"),
        "entry_month": pd.to_datetime(["2020-01-01"] * 3).values.astype("datetime64[ns]"),
        "era": ["2020-2026"] * 3,
        "excess_h10_net": [0.01, 0.02, 0.03],
        "excess_h21_net": [0.04, 0.05, 0.06],
        "mfe21": [0.05, 0.05, 0.05],
        "mae21": [-0.04, -0.04, -0.04],
        "sessions_to_mfe": [3, 3, 3],
    })

    joined, drops = S.join_regime(events, rg, fallback_max_days=14)

    b_rows = joined[joined["name"] == "B"]
    assert len(b_rows) == 1
    assert (b_rows["growth_score"] == 0.5).all(), (
        "event B must NOT pick the exact-date row's growth_score=0.1"
    )
    assert (b_rows["n_flags"] == 0).all()

    c_rows = joined[joined["name"] == "C"]
    assert len(c_rows) == 1
    assert (c_rows["growth_score"] == 0.1).all()
    assert (c_rows["n_flags"] == 2).all()


def test_regime_join_drops_old_match_and_missing_separately():
    dates = pd.to_datetime(["2020-01-02", "2020-01-10"]).values.astype("datetime64[ns]")
    rg = pd.DataFrame({
        "growth_score": [0.5, -0.1],
        "n_flags": [0, 1],
        "quad": ["Q1", "Q2"],
        "recession": [False, False],
        "transition_ratcheted": [True, False],
    }, index=pd.DatetimeIndex(dates))

    events = pd.DataFrame({
        "variant": ["1D"] * 4,
        "name": ["A", "B", "C", "D"],
        "signal_date": pd.to_datetime(
            ["2020-01-30", "2020-01-12", "2020-01-12", "2020-01-05"]
        ).values.astype("datetime64[ns]"),
        "entry_date": pd.to_datetime(["2020-01-31"] * 4).values.astype("datetime64[ns]"),
        "entry_month": pd.to_datetime(["2020-01-01"] * 4).values.astype("datetime64[ns]"),
        "era": ["2020-2026"] * 4,
        "excess_h10_net": [0.01, 0.02, 0.03, 0.04],
        "excess_h21_net": [0.04, 0.05, 0.06, 0.07],
        "mfe21": [0.05] * 4,
        "mae21": [-0.04] * 4,
        "sessions_to_mfe": [3] * 4,
    })
    rg_with_nan = rg.copy()
    rg_with_nan.loc[pd.DatetimeIndex(["2020-01-10"]).values.astype("datetime64[ns]")[0]] = [
        np.nan, np.nan, "Q2", False, False,
    ]

    joined, drops = S.join_regime(events, rg_with_nan, fallback_max_days=7)
    reasons = drops.set_index("reason")["n"].to_dict()
    assert reasons.get("match_older_than_7d", 0) >= 1, "event A should be too-old-dropped"
    assert "no_prior_regime_row" in reasons


# ───────────────────────────────────────────────────────────────── #
# (2) features — no look-ahead, no dead feature
# ───────────────────────────────────────────────────────────────── #
def test_features_no_lookahead_and_alive():
    rng = np.random.default_rng(42)
    n = 400
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n)), index=dates)
    spy = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.008, n)), index=dates)
    rolling = F.per_name_rolling(close)
    t = dates[300]
    t_after = dates[301]
    t_before = dates[279]  # t-21 sessions

    base = {
        "trend": F.feat_trend(rolling).loc[t],
        "momentum": F.feat_momentum(rolling).loc[t],
        "compression": F.feat_compression(rolling).loc[t],
        "structure": F.feat_structure(rolling).loc[t],
        "rs": F.feat_rs(rolling, spy).loc[t],
    }

    # AFTER t: every feature at t must be unchanged (look-ahead = 0).
    close2 = close.copy()
    close2.loc[t_after] = close.loc[t_after] * 1000
    spy2 = spy.copy()
    spy2.loc[t_after] = spy.loc[t_after] * 1000
    rolling2 = F.per_name_rolling(close2)
    assert F.feat_trend(rolling2).loc[t] == base["trend"]
    assert F.feat_momentum(rolling2).loc[t] == base["momentum"]
    assert F.feat_compression(rolling2).loc[t] == base["compression"]
    assert F.feat_structure(rolling2).loc[t] == base["structure"]
    assert F.feat_rs(rolling2, spy2).loc[t] == base["rs"]

    # AT t: trend / compression / structure / rs must change.
    close3 = close.copy()
    close3.loc[t] = close.loc[t] * 2.0
    rolling3 = F.per_name_rolling(close3)
    assert F.feat_trend(rolling3).loc[t] != base["trend"]
    assert F.feat_structure(rolling3).loc[t] != base["structure"]
    assert F.feat_compression(rolling3).loc[t] != base["compression"]
    assert F.feat_rs(rolling3, spy).loc[t] != base["rs"]
    # momentum uses t-21 and t-252, not close[t]
    assert F.feat_momentum(rolling3).loc[t] == base["momentum"]

    # BEFORE t (t-21): momentum must change.
    close4 = close.copy()
    close4.loc[t_before] = close.loc[t_before] * 2.0
    rolling4 = F.per_name_rolling(close4)
    assert F.feat_momentum(rolling4).loc[t] != base["momentum"]

    # participation: steadily rising prices so close > SMA50 at t; perturb AFTER t
    # does not change the share; perturb AT t (crash A through SMA50) does.
    rising = pd.Series(np.linspace(50.0, 150.0, n), index=dates)
    roll_a = F.per_name_rolling(rising)
    roll_b = F.per_name_rolling(rising * 1.01)
    part0 = F.participation_series({"A": roll_a, "B": roll_b}, min_names_with_sma50=1)
    assert part0.loc[t] == 1.0
    rising_after = rising.copy()
    rising_after.loc[t_after] *= 1000
    part_after = F.participation_series(
        {"A": F.per_name_rolling(rising_after), "B": roll_b}, min_names_with_sma50=1,
    )
    assert part0.loc[t] == part_after.loc[t]
    rising_at = rising.copy()
    rising_at.loc[t] = 1.0  # drive A below its SMA50; B unchanged and still above
    part_at = F.participation_series(
        {"A": F.per_name_rolling(rising_at), "B": roll_b}, min_names_with_sma50=1,
    )
    assert part_at.loc[t] != part0.loc[t]
    assert part_at.loc[t] == 0.5


def test_tercile_assignment_and_cuts():
    rng = np.random.default_rng(7)
    values = pd.Series(rng.normal(0, 1, 500))
    lo, hi = F.fixed_tercile_cuts(values)
    bins = F.assign_terciles(values, lo, hi)
    counts = bins.value_counts().to_dict()
    assert abs(counts.get("T1", 0) - 167) < 30
    assert abs(counts.get("T2", 0) - 167) < 30
    assert abs(counts.get("T3", 0) - 167) < 30


def test_participation_excludes_sma50_warmup():
    """K8: a name still in SMA50 warm-up is excluded from num and denom."""
    idx = pd.bdate_range("2020-01-01", periods=5)
    roll_a = pd.DataFrame(
        {"close": [10.0, 11.0, 12.0, 13.0, 14.0],
         "sma50": [9.0, 10.0, 11.0, 12.0, 13.0]},
        index=idx,
    )
    roll_b = pd.DataFrame(
        {"close": [10.0, 11.0, 12.0, 13.0, 14.0],
         "sma50": [np.nan, np.nan, 11.0, 12.0, 13.0]},
        index=idx,
    )
    part = F.participation_series({"A": roll_a, "B": roll_b}, min_names_with_sma50=1)
    # date 0: only A valid (10>9 True) → share 1.0 over valid names, not 0.5
    assert part.iloc[0] == 1.0
    assert part.iloc[1] == 1.0
    # date 2: both valid and both above → 1.0
    assert part.iloc[2] == 1.0


# ───────────────────────────────────────────────────────────────── #
# K1 floor gate — eight era cells; pooled-6 mutant fails
# ───────────────────────────────────────────────────────────────── #
def _synthetic_floor_frame(months_t1_exp_2014: int) -> pd.DataFrame:
    """Build a frame where every 8-cell is above floor EXCEPT 2014-2019/T1/EXPANSION
    which has `months_t1_exp_2014` months (and enough events/names on those months).
    Pooled-era 6-cell view (including T2) is entirely above floor.
    """
    rng = np.random.default_rng(0)
    rows = []

    def add_cell(era, terc, state, n_months, n_per_month=120, n_names=120):
        months = pd.period_range("2015-01" if era == "2014-2019" else "2021-01",
                                 periods=n_months, freq="M")
        names = [f"N{i}" for i in range(n_names)]
        for m in months:
            for j in range(n_per_month):
                rows.append({
                    "tercile": terc,
                    "state": state,
                    "era": era,
                    "entry_month": m.to_timestamp(),
                    "name": names[j % n_names],
                    "y": float(rng.normal(0, 0.01)),
                })

    # eight T1/T3 × state × era cells; one under the month floor
    for era in ("2014-2019", "2020-2026"):
        for terc in ("T1", "T3"):
            for st in ("EXPANSION", "CONTRACTION"):
                n_m = months_t1_exp_2014 if (era == "2014-2019" and terc == "T1"
                                             and st == "EXPANSION") else 30
                add_cell(era, terc, st, n_m)
    # T2 pooled cells so the 6-cell mutant sees 6 rows all above floor
    for st in ("EXPANSION", "CONTRACTION"):
        add_cell("2014-2019", "T2", st, 30)
        add_cell("2020-2026", "T2", st, 30)
    return pd.DataFrame(rows)


def test_floor_gate_counts_eight_cells():
    df = _synthetic_floor_frame(months_t1_exp_2014=17)
    floor_pass, cells, failing = S.floor_gate_eight_cells(
        df, "EXPANSION", "CONTRACTION",
    )
    assert floor_pass is False
    assert "2014-2019/T1/EXPANSION" in failing
    assert len(cells) == 8

    # Mutant restoring the pooled 6-cell count (round-0 bug) incorrectly PASSES.
    mutant_pass, n_total = S.floor_gate_pooled_six_MUTANT(
        df, "EXPANSION", "CONTRACTION",
    )
    assert n_total == 6
    assert mutant_pass is True, "the 6-cell mutant must be the round-0 false-pass"
    # Production function must NOT agree with the mutant.
    assert floor_pass != mutant_pass


# ───────────────────────────────────────────────────────────────── #
# K2 / K6 bootstrap: weighted SE matches analytic; isin/row/keep-all fail
# ───────────────────────────────────────────────────────────────── #
def _month_clustered_I_frame(n_months=40, n_per_cell=30, sigma_u=0.02, sigma_e=0.005):
    """Equal-sized 4-cell panel with a month shock, so I_pooled = mean(I_m)."""
    rng = np.random.default_rng(123)
    rows = []
    month_I = []
    months = pd.period_range("2015-01", periods=n_months, freq="M")
    # Cell intercepts such that I = 0.04
    intercept = {
        ("EXPANSION", "T3"): 0.03,
        ("EXPANSION", "T1"): 0.00,
        ("CONTRACTION", "T3"): 0.01,
        ("CONTRACTION", "T1"): 0.02,
    }
    # I = (0.03-0.00) - (0.01-0.02) = 0.03 - (-0.01) = 0.04
    for m in months:
        u = rng.normal(0, sigma_u)
        # signed so the month shock survives in I_m
        cell_u = {
            ("EXPANSION", "T3"): +u,
            ("EXPANSION", "T1"): -u,
            ("CONTRACTION", "T3"): -u,
            ("CONTRACTION", "T1"): +u,
        }
        # I_m extra = (u-(-u)) - ((-u)-(+u)) = 2u - (-2u) = 4u
        month_I.append(0.04 + 4 * u)
        for (st, terc), a0 in intercept.items():
            for j in range(n_per_cell):
                y = a0 + cell_u[(st, terc)] + rng.normal(0, sigma_e)
                rows.append({
                    "tercile": terc, "state": st,
                    "entry_month": m.to_timestamp(),
                    "name": f"N{j}", "y": y, "era": "2014-2019",
                })
    return pd.DataFrame(rows), np.asarray(month_I)


def test_cluster_bootstrap_matches_analytic_se():
    df, month_I = _month_clustered_I_frame()
    analytic = S.analytic_cluster_se_equal_months(month_I)
    rng = np.random.default_rng(np.random.SeedSequence(20261004).spawn(1)[0])
    obs, samples = S.cluster_bootstrap_I(
        df, state_a="EXPANSION", state_b="CONTRACTION",
        n_draws=800, rng=rng, mode="weight",
    )
    se = float(np.nanstd(samples, ddof=1))
    assert np.isfinite(obs) and np.isfinite(se) and np.isfinite(analytic)
    rel = abs(se - analytic) / analytic
    assert rel < 0.10, f"weighted SE {se:.5f} vs analytic {analytic:.5f} rel={rel:.3f}"

    # isin mutant understates SE — must FAIL the 10% match.
    rng2 = np.random.default_rng(np.random.SeedSequence(20261004).spawn(1)[0])
    _, samp_isin = S.cluster_bootstrap_I(
        df, state_a="EXPANSION", state_b="CONTRACTION",
        n_draws=800, rng=rng2, mode="isin",
    )
    se_isin = float(np.nanstd(samp_isin, ddof=1))
    rel_isin = abs(se_isin - analytic) / analytic
    assert rel_isin >= 0.10, (
        f"isin mutant unexpectedly matched analytic (se={se_isin:.5f}, rel={rel_isin:.3f}); "
        "the 10% gate must FAIL under np.isin"
    )


def test_unclustered_resample_fails_cluster_invariant():
    """K6: unclustered SE is ≥30% below clustered; unclustered fails the
    analytic-cluster match; mutation B (keep-all-months) also fails it.
    """
    df, month_I = _month_clustered_I_frame(n_months=50, sigma_u=0.03, sigma_e=0.002)
    analytic = S.analytic_cluster_se_equal_months(month_I)
    ss = np.random.SeedSequence(20261004).spawn(3)
    obs_c, samp_c = S.cluster_bootstrap_I(
        df, state_a="EXPANSION", state_b="CONTRACTION",
        n_draws=600, rng=np.random.default_rng(ss[0]), mode="weight",
    )
    _, samp_row = S.cluster_bootstrap_I(
        df, state_a="EXPANSION", state_b="CONTRACTION",
        n_draws=600, rng=np.random.default_rng(ss[1]), mode="row",
    )
    _, samp_keep = S.cluster_bootstrap_I(
        df, state_a="EXPANSION", state_b="CONTRACTION",
        n_draws=200, rng=np.random.default_rng(ss[2]), mode="keep_all",
    )
    se_c = float(np.nanstd(samp_c, ddof=1))
    se_row = float(np.nanstd(samp_row, ddof=1))
    se_keep = float(np.nanstd(samp_keep, ddof=1))

    assert se_row <= se_c * 0.70, (
        f"unclustered SE {se_row:.5f} is not ≥30% below clustered {se_c:.5f}"
    )
    assert abs(se_c - analytic) / analytic < 0.10
    assert abs(se_row - analytic) / analytic >= 0.10
    # mutation B: keep-all-months → SE ≈ 0, fails the cluster-SE invariant
    assert se_keep < analytic * 0.10
    assert abs(se_keep - analytic) / analytic >= 0.10


def test_bootstrap_month_clustered_paired_across_cells():
    rng = np.random.default_rng(99)
    n_per_month = 100
    rows = []
    for m_idx, month in enumerate(pd.date_range("2020-01-01", periods=4, freq="5D")):
        for _ in range(n_per_month):
            terc = rng.choice(["T1", "T3"])
            state = "EXPANSION" if m_idx % 2 == 0 else "CONTRACTION"
            y = rng.normal(0.05 if (state == "EXPANSION" and terc == "T3") else
                          (-0.05 if (state == "CONTRACTION" and terc == "T3") else 0.0),
                          0.01)
            rows.append({
                "tercile": terc, "state": state, "entry_month": month,
                "name": "X", "y": y, "era": "2020-2026",
            })
    df = pd.DataFrame(rows)
    ss = np.random.SeedSequence(20261004).spawn(1)[0]
    obs, samples = S._bootstrap_interaction_for_family_partition(
        df, state_col="state", outcome_col="y",
        state_a="EXPANSION", state_b="CONTRACTION", n_draws=500,
        rng=np.random.default_rng(ss),
    )
    assert np.isfinite(obs)
    assert np.isfinite(samples).sum() >= 250
    assert obs > 0


# ───────────────────────────────────────────────────────────────── #
# (4) Holm step-down
# ───────────────────────────────────────────────────────────────── #
def test_holm_step_down_hand_computable():
    pvals = np.array([0.01, 0.04, 0.03, 0.005])
    adj = S.holm(pvals)
    expected = np.array([0.030, 0.060, 0.060, 0.020])
    np.testing.assert_allclose(adj, expected, atol=1e-9)


# ───────────────────────────────────────────────────────────────── #
# K3 — no builtin hash() in run.py / stats.py
# ───────────────────────────────────────────────────────────────── #
def test_no_builtin_hash_token_in_run_or_stats():
    for fname in ("run.py", "stats.py"):
        src = (CODE_DIR / fname).read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "hash", f"{fname} calls builtin hash()"


# ───────────────────────────────────────────────────────────────── #
# K5 regime-clock citations resolve
# ───────────────────────────────────────────────────────────────── #
REGIME_CLOCK_CITATIONS = [
    ("scripts/build_regime_v2_pit.py", 376, "f_pit = build_features(overrides=overrides)"),
    ("engine/inputs.py", 171, "idx = pd.bdate_range(closes.index.min(), end)"),
    ("engine/inputs.py", 262, "basket_index(closes, g[\"cyclical_basket\"]).reindex(idx).ffill(limit=5)"),
    ("scripts/build_regime_v2_pit.py", 103, "def pit_availability_panel"),
    ("scripts/build_regime_v2_pit.py", 105, "Reindex+ffill of this panel gives, on every date d, exactly"),
]


def test_regime_clock_citation_resolves():
    for rel, lineno, quote in REGIME_CLOCK_CITATIONS:
        path = REPO / rel
        lines = path.read_text().splitlines()
        assert 1 <= lineno <= len(lines), f"{rel}:{lineno} out of range"
        # allow a small window so 262-267 is covered by line 262
        window = "\n".join(lines[lineno - 1: min(len(lines), lineno + 5)])
        assert quote in window, f"{rel}:{lineno} missing {quote!r}; saw {window!r}"


# ───────────────────────────────────────────────────────────────── #
# (5) result.json / RESULT.md consistency
# ───────────────────────────────────────────────────────────────── #
def test_result_json_schema_if_present():
    p = RESULTS_DIR / "result.json"
    assert p.exists(), "result.json must be written before pytest"
    payload = json.loads(p.read_text())
    for k in ("lane", "status", "repo_head", "data_class", "design", "verdict",
              "answer_first", "tests_12", "holm_stepdown", "verdict_rule"):
        assert k in payload, f"missing key {k}"
    assert payload["lane"] == "E"
    assert len(payload["tests_12"]) == 12
    for t in payload["tests_12"]:
        assert t["family"] in F.FAMILIES
        assert t["partition"] in ("P1_growth", "P2_stress")
        assert all(k in t for k in ("observed", "ci_lo", "ci_hi", "se",
                                     "p_two_sided", "era_2014_2019", "era_2020_2026",
                                     "same_sign_eras", "floor_pass", "cells"))
        assert len(t["cells"]) == 8, "floor cells must be the eight era × T1/T3 × state cells"
    assert payload["verdict"] in ("WINNERS", "SCOPED_NULL", "INSUFFICIENT_SUPPORT")
    # secondaries carry era values (K7)
    for s in payload["h21_secondary_12"]:
        assert "era_2014_2019" in s and "era_2020_2026" in s
    for s in payload["three_d_p0_confirmed_secondary"]["tests_12"]:
        assert "era_2014_2019" in s and "era_2020_2026" in s
    panel_sha = payload["inputs"]["panel_sha256"]
    if isinstance(panel_sha, dict):
        panel_sha = panel_sha.get("load") or panel_sha.get("sha256")
    assert str(panel_sha).startswith("209e2246"), f"expected B1 ROUND 3 panel, got {panel_sha}"
    assert "ROUND 3" in (RESULTS_DIR / "RESULT.md").read_text()
    assert "iso_weekday_or" not in (RESULTS_DIR / "RESULT.md").read_text()
    assert "iso_weekday_or" not in json.dumps(payload.get("regime_clock", {}))


def test_result_md_present_and_has_answer_first():
    p = RESULTS_DIR / "RESULT.md"
    assert p.exists(), "RESULT.md must be written before pytest"
    text = p.read_text()
    assert "ANSWER FIRST" in text or "## Answer first" in text
    assert "## The twelve primary tests" in text
    assert "B1 ROUND 3" in text
    assert "final-vintage" in text.lower() or "FINAL-VINTAGE" in text
    assert "survivor-selected" in text.lower() or "SURVIVOR-SELECTED" in text


def test_twelve_table_json_md_match():
    """(5) twelve-test table in RESULT.md and result.json read the same numbers."""
    payload = json.loads((RESULTS_DIR / "result.json").read_text())
    md = (RESULTS_DIR / "RESULT.md").read_text()
    # rows like: | 1 | trend | P1_growth | +0.00227 | ...
    rows = []
    in_table = False
    for line in md.splitlines():
        if line.startswith("| # | family |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if re.match(r"\|[-: ]+\|", line):
                continue
            rows.append(line)
    assert len(rows) == 12, f"expected 12 md rows, got {len(rows)}"
    for i, (line, t) in enumerate(zip(rows, payload["tests_12"]), 1):
        parts = [c.strip() for c in line.strip("|").split("|")]
        assert parts[1] == t["family"]
        assert parts[2] == t["partition"]
        assert parts[3] == f"{t['observed']:+.5f}"
        assert parts[4] == f"{t['ci_lo']:+.5f}"
        assert parts[5] == f"{t['ci_hi']:+.5f}"
        assert parts[6] == f"{t['se']:.5f}"
        assert parts[7] == f"{t['p_two_sided']:.4f}"
        assert parts[8] == f"{t['p_holm']:.4f}"


# ───────────────────────────────────────────────────────────────── #
# (6) drops counted by reason
# ───────────────────────────────────────────────────────────────── #
def test_drops_counted_by_reason_in_result():
    payload = json.loads((RESULTS_DIR / "result.json").read_text())
    drops = payload.get("drops_by_reason", [])
    assert drops, "drops_by_reason must be present and non-empty (K12 late-2026)"
    reasons = {d["reason"] for d in drops}
    for d in drops:
        assert "reason" in d and "n" in d
        assert isinstance(d["n"], int)
    assert "match_older_than_7d" in reasons


# ───────────────────────────────────────────────────────────────── #
# (7) hashes.txt verifies
# ───────────────────────────────────────────────────────────────── #
def test_hashes_txt_verifies():
    p = RESULTS_DIR / "hashes.txt"
    assert p.exists(), "hashes.txt must exist for this test"
    n_ok = 0
    for line in p.read_text().splitlines():
        if not line.strip() or line.startswith(("MISSING", "ERR")):
            continue
        sha, _, target = line.partition("  ")
        path = (REPO / target).resolve()
        assert path.exists(), f"hashed path missing: {target}"
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        assert h.hexdigest() == sha, f"hash mismatch for {target}"
        n_ok += 1
    assert n_ok >= 6
    text = p.read_text()
    assert "209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8" in text
    assert "d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae" in text
