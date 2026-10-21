"""SIC-D-B07 — grader schema v2 interpretability tests (US + China Sector Central).

Masterplan §6.2 "Grader denominator": legacy ``dir_hit_rate`` divides correct up+down
calls by ALL graded rows (Neutral included), so it is neither a conditional directional
hit rate nor a win rate.  These tests pin the ADDITIVE v2 reading — conditional rate
with date-clustered SE, Neutral outcomes, matured/excluded/accruing counts, IC/excess
distributions, call-month cohorts — and the byte-identical survival of the legacy value.

Every frame is synthetic and built in-test; loaders are monkeypatched (no data/ files,
no network).  Price paths are hand-computed two-point ladders (entry bar and exit bar
only, every other bar flat at 100) so each asserted forward return is exact by
construction; the China parity test uses geometric paths instead, which make the US
next-bar and CN same-bar fill conventions produce the same h-bar return.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import china_sector_central_grader as cscg
from engine import china_sector_index as csi
from engine import sector_central_grader as scg

N_BARS = 200
IDX = pd.bdate_range("2026-01-02", periods=N_BARS)   # IDX[1]=Jan 5, IDX[2]=Jan 6, IDX[21]=Feb 3
DEF = ("legacy: correct up + correct down calls / all graded rows including Neutral "
       "(not a conditional hit rate, not a win rate)")
INTERP = ("descriptive evaluation over correlated observations; not a win rate, "
          "not trading P&L")
M_JAN = IDX[1].strftime("%Y-%m")
M_FEB = IDX[21].strftime("%Y-%m")
LATE = N_BARS - 5                                    # IDX[195] — horizon end past last session


def _two_point(f: float, call_pos: int, h: int = 21) -> list[float]:
    """Path whose h-bar US forward return from call_pos is exactly f (next-bar fill:
    entry = bar call_pos+1, exit = bar call_pos+1+h; all other bars flat at 100)."""
    v = [100.0] * N_BARS
    v[call_pos + 1 + h] = 100.0 * (1.0 + f)
    return v


def _geo(g: float) -> pd.Series:
    """Geometric path (+g per bar) — h-bar returns are window-position invariant."""
    return pd.Series(100.0 * np.cumprod(np.full(N_BARS, 1.0 + g)), index=IDX)


def _call(i: int, pos: int, ticker: str, direction: str, score: float = 50.0) -> dict:
    return {"date": str(IDX[pos].date()), "id": f"s-{i}", "kind": "sector",
            "ticker": ticker, "basket_id": None, "name": ticker,
            "score": score, "label": "Constructive", "dir": direction,
            "confluence": True, "trend_pass": True, "ret_12m": 0.1,
            "gate_factor": 1.0, "level": None}


def _cn_call(i: int, pos: int, code: str, direction: str, score: float = 50.0) -> dict:
    return {"date": str(IDX[pos].date()), "id": f"s-{i}", "kind": "sector",
            "shenwan_code": code, "basket_id": None, "name": code,
            "score": score, "label": "Constructive", "dir": direction,
            "confluence": True, "fwd_cond_rate": None, "fwd_lift": None,
            "gate_factor": 1.0, "level": None}


def _us_grade(tmp_path, monkeypatch, rows, paths) -> dict:
    p = tmp_path / "sector_central" / "calls.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(p, index=False)
    panel = pd.DataFrame({t: pd.Series(v, index=IDX) for t, v in paths.items()})
    panel["SPY"] = 100.0                      # flat bench → excess == fwd exactly
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(scg, "_yahoo_panel", lambda: panel)
    monkeypatch.setattr(scg, "_basket_levels", lambda: {})
    return scg.grade()


def _se_frame():
    """3-date frame: 7 directional + 3 neutral rows, 4 correct directional calls.

    A (Jan 5): up +5% ok, down +3% wrong          → 1 of 2 correct
    B (Jan 6): up +2% ok, up 0.0% flat (wrong — a flat fwd is correct for NEITHER
               side, the legacy rule), down +1% wrong → 1 of 3 correct
    C (Feb 3): down −6% ok, down −2% ok           → 2 of 2 correct
    plus one neutral row per date (+1% / 0.0% / −1%).
    """
    fwd = {"A_UP1": .05, "A_DN1": .03, "A_NT1": .01,
           "B_UP1": .02, "B_UP2": 0.0, "B_DN1": .01, "B_NT1": 0.0,
           "C_DN1": -.06, "C_DN2": -.02, "C_NT1": -.01}
    pos = {"A_UP1": 1, "A_DN1": 1, "A_NT1": 1,
           "B_UP1": 2, "B_UP2": 2, "B_DN1": 2, "B_NT1": 2,
           "C_DN1": 21, "C_DN2": 21, "C_NT1": 21}
    dirs = {"A_UP1": "up", "A_DN1": "down", "A_NT1": "neutral",
            "B_UP1": "up", "B_UP2": "up", "B_DN1": "down", "B_NT1": "neutral",
            "C_DN1": "down", "C_DN2": "down", "C_NT1": "neutral"}
    rows = [_call(i, pos[t], t, dirs[t], score=10.0 * i)
            for i, t in enumerate(fwd, start=1)]
    paths = {t: _two_point(f, pos[t]) for t, f in fwd.items()}
    return rows, paths


def test_legacy_vs_conditional_hand_computed(tmp_path, monkeypatch):
    # 4 up, 3 down, 3 neutral on ONE date.  Correct: 3 of 4 ups (the −1% up call is
    # wrong), 2 of 3 downs (the +3% down call is wrong) → 5 correct directional calls.
    #   legacy dir_hit_rate       = 5 / 10 graded rows  = 0.5     (Neutral in denominator)
    #   conditional dir hit rate  = 5 / 7 directional    = 0.7143
    D = 1
    fwd = {"UP1": .05, "UP2": .02, "UP3": -.01, "UP4": .10,
           "DN1": -.06, "DN2": .03, "DN3": -.02,
           "NT1": .01, "NT2": -.01, "NT3": 0.0}
    dirs = {"UP1": "up", "UP2": "up", "UP3": "up", "UP4": "up",
            "DN1": "down", "DN2": "down", "DN3": "down",
            "NT1": "neutral", "NT2": "neutral", "NT3": "neutral"}
    rows = [_call(i, D, t, dirs[t], score=10.0 * i) for i, t in enumerate(fwd, start=1)]
    paths = {t: _two_point(f, D) for t, f in fwd.items()}
    g = _us_grade(tmp_path, monkeypatch, rows, paths)

    assert g["grader_schema_version"] == 2
    assert g["interpretation"] == INTERP
    h21 = g["by_horizon"]["21d"]
    assert h21["dir_hit_rate"] == 0.5                          # legacy formula, unchanged
    assert h21["dir_hit_rate_definition"] == DEF
    assert h21["n"] == 10
    assert h21["n_directional"] == 7
    assert h21["n_neutral"] == 3
    assert h21["n_correct_directional"] == 5
    assert h21["directional_coverage"] == 0.7
    assert h21["conditional_directional_hit_rate"] == 0.7143    # 5/7 ≠ 0.5 legacy
    assert h21["conditional_hit_rate_se"] is None               # single date → G = 1 < 2
    assert h21["uncertainty_method"] == "date_clustered_se"
    no = h21["neutral_outcomes"]
    assert no == {"n": 3, "mean_fwd": 0.0,          # (+1% − 1% + 0) / 3
                  "mean_abs_fwd": 0.0067,           # (1% + 1% + 0) / 3
                  "mean_excess": 0.0}               # flat SPY → excess == fwd
    assert h21["counts"] == {"matured": 10, "excluded_membership": 0,
                             "excluded_pre_chain": 0, "excluded_no_forward": 0,
                             "accruing": 0}


def test_date_clustered_se_three_dates(tmp_path, monkeypatch):
    # Hand computation (see _se_frame): n_directional = 7, n_correct = 4, p = 4/7.
    # Per-date residual cluster sums (Σ r_i over the date's directional rows):
    #   A: 1 − 2p = −1/7     B: 1 − 3p = −5/7     C: 2 − 2p = +6/7
    #   se = sqrt( G/(G−1) · Σ(Σr)² ) / n_dir   with G = 3 dates
    #      = sqrt( (3/2) · (1 + 25 + 36)/49 ) / 7
    #      = sqrt( (3/2) · 62/49 ) / 7 = sqrt(93/49)/7 = √93/49 ≈ 0.19681
    rows, paths = _se_frame()
    g = _us_grade(tmp_path, monkeypatch, rows, paths)
    h21 = g["by_horizon"]["21d"]
    assert h21["n"] == 10 and "note" not in h21                  # graded path, not the stub
    assert h21["n_directional"] == 7
    assert h21["n_correct_directional"] == 4                     # the flat up call is NOT correct
    assert h21["conditional_directional_hit_rate"] == 0.5714     # 4/7
    assert h21["dir_hit_rate"] == 0.4                            # 4/10 — differs from 4/7
    assert h21["conditional_hit_rate_se"] == 0.1968              # √93/49, hand-computed above
    assert h21["uncertainty_method"] == "date_clustered_se"
    assert h21["n_neutral"] == 3
    cm = h21["by_cohort_month"]
    assert set(cm) == {M_JAN, M_FEB}
    assert cm[M_JAN] == {"n_logged": 7, "n_matured": 7, "n_accruing": 0, "n_excluded": 0}
    assert cm[M_FEB] == {"n_logged": 3, "n_matured": 3, "n_accruing": 0, "n_excluded": 0}


def test_zero_directional_rows(tmp_path, monkeypatch):
    # 4 Neutral calls over 2 dates — no up/down row exists at all.
    fwd = {"N1": .10, "N2": -.10, "N3": .05, "N4": -.05}
    pos = {"N1": 1, "N2": 1, "N3": 2, "N4": 2}
    rows = [_call(i, pos[t], t, "neutral", score=10.0 * i)
            for i, t in enumerate(fwd, start=1)]
    paths = {t: _two_point(f, pos[t]) for t, f in fwd.items()}
    g = _us_grade(tmp_path, monkeypatch, rows, paths)
    h21 = g["by_horizon"]["21d"]
    assert h21["n_directional"] == 0
    assert h21["n_neutral"] == 4
    assert h21["n_correct_directional"] == 0
    assert h21["directional_coverage"] == 0.0
    assert h21["conditional_directional_hit_rate"] is None
    assert h21["conditional_hit_rate_se"] is None
    assert h21["dir_hit_rate"] == 0.0                            # 0 correct / 4 graded
    assert h21["neutral_outcomes"] == {"n": 4, "mean_fwd": 0.0, "mean_abs_fwd": 0.075,
                                       "mean_excess": 0.0}
    # no date reaches the >= 3 distinct-score rule → empty IC distribution, None fields
    assert h21["rank_ic_distribution"] == {"n_dates": 0, "mean": None, "median": None,
                                           "p25": None, "p75": None, "share_positive": None}


def test_accruing_vs_excluded_no_forward(tmp_path, monkeypatch):
    # The 10 matured January/February calls of _se_frame, plus:
    #   DEAD — called Jan 5 but its price series ENDS after 21 bars while the panel
    #          runs to October: the horizon had plenty of sessions to mature, so it is
    #          an OLD call with no forward price → excluded_no_forward.
    #   LATE — called 5 bars before the panel's last session: its horizon end is after
    #          the latest available session → too young → accruing.
    rows, paths = _se_frame()
    rows.append(_call(11, 1, "DEAD", "up"))
    dead = [100.0] * 21 + [float("nan")] * (N_BARS - 21)
    paths["DEAD"] = dead
    rows.append(_call(12, LATE, "LATE", "up"))
    paths["LATE"] = [100.0] * N_BARS        # never matures — path content is irrelevant
    g = _us_grade(tmp_path, monkeypatch, rows, paths)
    expected = {"matured": 10, "excluded_membership": 0, "excluded_pre_chain": 0,
                "excluded_no_forward": 1, "accruing": 1}
    for key in ("21d", "63d", "126d"):
        assert g["by_horizon"][key]["counts"] == expected, key
    cm = g["by_horizon"]["21d"]["by_cohort_month"]
    assert cm[M_JAN] == {"n_logged": 8, "n_matured": 7, "n_accruing": 0, "n_excluded": 1}
    assert cm[M_FEB] == {"n_logged": 3, "n_matured": 3, "n_accruing": 0, "n_excluded": 0}
    assert cm[IDX[LATE].strftime("%Y-%m")] == {"n_logged": 1, "n_matured": 0,
                                               "n_accruing": 1, "n_excluded": 0}


def test_accruing_stub_carries_counts_and_cohorts(tmp_path, monkeypatch):
    # A single too-young call → the < 3 records accruing stub keeps its legacy shape
    # AND carries the v2 counts / cohort months that exist.
    rows = [_call(1, LATE, "LATE", "up")]
    g = _us_grade(tmp_path, monkeypatch, rows, {"LATE": [100.0] * N_BARS})
    h21 = g["by_horizon"]["21d"]
    assert h21["note"] == "accruing" and h21["n"] == 0
    assert h21.get("dir_hit_rate") is None
    assert h21["counts"] == {"matured": 0, "excluded_membership": 0, "excluded_pre_chain": 0,
                             "excluded_no_forward": 0, "accruing": 1}
    assert h21["by_cohort_month"] == {IDX[LATE].strftime("%Y-%m"):
                                      {"n_logged": 1, "n_matured": 0, "n_accruing": 1,
                                       "n_excluded": 0}}
    assert g["grader_schema_version"] == 2


def test_rank_ic_distribution_negative_mean_preserved(tmp_path, monkeypatch):
    # Two dates × three calls; the conviction score ranks EXACTLY opposite the
    # realized forward return on both dates → per-date IC = −1.0.  The unfavourable
    # reading must stay visible in the distribution, and `rank_ic` stays as it was.
    rows, paths = [], {}
    for d in (1, 2):
        for k, (score, f) in enumerate(((10.0, .05), (50.0, -.01), (90.0, -.04))):
            t = f"IC{d}{k}"
            rows.append(_call(10 * d + k, d, t, "neutral", score=score))
            paths[t] = _two_point(f, d)
    g = _us_grade(tmp_path, monkeypatch, rows, paths)
    h21 = g["by_horizon"]["21d"]
    assert h21["rank_ic"] == -1.0                                # legacy key, unchanged
    assert h21["rank_ic_distribution"] == {"n_dates": 2, "mean": -1.0, "median": -1.0,
                                           "p25": -1.0, "p75": -1.0, "share_positive": 0.0}
    # excess == fwd (flat SPY): sorted [−4,−4,−1,−1,+5,+5]% → quartiles by hand.
    assert h21["excess_distribution"] == {"n": 6, "mean": 0.0, "median": -0.01,
                                          "p25": -0.0325, "p75": 0.035,
                                          "share_positive": 0.3333}


def test_china_grader_parity_on_the_same_frame(tmp_path, monkeypatch):
    # The same logical calls through the China grader (Shenwan sectors, benchmark
    # close) must carry the same v2 reading.  Geometric per-bar paths make the US
    # next-bar fill and the CN same-bar fill produce identical h-bar returns, so
    # every count-based and rank-based v2 field must match exactly.
    per_bar = {"A_UP1": .002, "A_DN1": .004, "A_NT1": .003,
               "B_UP1": .0025, "B_UP2": 0.0, "B_DN1": .0035, "B_NT1": .001,
               "C_DN1": -.004, "C_DN2": -.0025, "C_NT1": -.001}
    pos = {"A_UP1": 1, "A_DN1": 1, "A_NT1": 1,
           "B_UP1": 2, "B_UP2": 2, "B_DN1": 2, "B_NT1": 2,
           "C_DN1": 21, "C_DN2": 21, "C_NT1": 21}
    dirs = {"A_UP1": "up", "A_DN1": "down", "A_NT1": "neutral",
            "B_UP1": "up", "B_UP2": "up", "B_DN1": "down", "B_NT1": "neutral",
            "C_DN1": "down", "C_DN2": "down", "C_NT1": "neutral"}
    us_rows = [_call(i, pos[t], t, dirs[t], score=10.0 * i)
               for i, t in enumerate(per_bar, start=1)]
    us = _us_grade(tmp_path, monkeypatch, us_rows,
                   {t: _geo(g) for t, g in per_bar.items()})

    cn_rows = [_cn_call(i, pos[t], t, dirs[t], score=10.0 * i)
               for i, t in enumerate(per_bar, start=1)]
    p = tmp_path / "china_sector_central" / "calls.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(cn_rows).to_parquet(p, index=False)
    series = {t: _geo(g) for t, g in per_bar.items()}
    monkeypatch.setattr(cscg.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(cscg, "_basket_levels_cn", lambda: ({}, None))
    monkeypatch.setattr(csi, "sw_close", lambda code: series.get(code))
    monkeypatch.setattr(csi, "benchmark_close_price",
                        lambda: pd.Series(100.0, index=IDX))
    cn = cscg.grade()

    assert cn["grader_schema_version"] == us["grader_schema_version"] == 2
    assert cn["interpretation"] == us["interpretation"] == INTERP
    for key in ("n", "dir_hit_rate", "dir_hit_rate_definition", "n_directional",
                "n_neutral", "n_correct_directional", "directional_coverage",
                "conditional_directional_hit_rate", "conditional_hit_rate_se",
                "uncertainty_method", "counts", "by_cohort_month",
                "rank_ic_distribution"):
        assert cn["by_horizon"]["21d"][key] == us["by_horizon"]["21d"][key], key
    # and the parity frame itself still hand-checks: 4 of 7 directional, se = √93/49
    assert cn["by_horizon"]["21d"]["n_correct_directional"] == 4
    assert cn["by_horizon"]["21d"]["conditional_hit_rate_se"] == 0.1968


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
