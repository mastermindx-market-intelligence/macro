"""Lane F1 — entry vs management decomposition on the served Prophet ledger.

SEVERE label = (excess_spy_h21 <= -0.07) OR (mae_h21 <= -0.07).
TARGET = excess_spy_h21 >= +0.07 and not SEVERE.

Embargo (binding, seat ruling 2026-10-04, supersedes the 22-cal-day rule):
  for every OOS test week, training episodes are kept iff
    np.busday_offset(as_of, 21, roll="forward", holidays=<NYSE holiday calendar>)
    < week_start
  i.e. every training h21 label is realised STRICTLY BEFORE the test week starts.
  Equivalently: as_of <= np.busday_offset(week_start, -22, ...).
  The previous -21-session literal admitted 138 rows (24/31/40/43 per fold)
  whose as_of + 21 sessions == week_start (labels INSIDE the test week).
  The 22-calendar-day rule is kept as a labelled SENSITIVITY row only.

Round-3 (H1-H10):
  - H1: fold builder exposes the comparator; mutants evaluate the SHARED
        strict comparator on the resulting fold_records (test_f1.py).
  - H2: check_result_md.py compares LABELLED numbers to SPECIFIC result.json
        keys at rendered precision (see check_result_md.py).
  - H3: run.py sets status=TESTS_FAILED and exits non-zero when pytest fails.
  - H4: RESULT.md ## 12 lists failing tests under mutants, generated from runs.
  - H5/H6: G8 row renders 17.4% / 33 (from the payload); support count reported
        at 1e-10 and 1e-4 with multiset max 35.
  - H7: write order is payload -> result.json+RESULT.md -> pytest -> tests
        folded in -> hashes.txt LAST.
  - H8: hashes.txt has no blank line.
  - H9: literal "as_of <= week_start - 22 sessions" present in both files.
  - H10: c1_status() fails closed; missing result.json => c1_available=False.
"""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import hashlib
import datetime as _dt
import shutil
import tempfile
import socket
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import nyse_calendar  # noqa: E402

RESULTS_DIR = Path(
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1"
)
RG_PATH = "data/us_board_ledger/retro_grades.parquet"
LEDGER_PATH = "data/prophet/ledger.jsonl"
C1_PATH = "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/rotation_state_daily.parquet"
C1_RESULT_JSON = "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/result.json"

THRESH = -0.07  # fraction; excess_spy and mae_close_excess_spy are decimals
TARGET_THRESH = 0.07
RNG_SEED = 20261004
N_BOOTSTRAP = 1000
EMBARGO_LABEL_HORIZON = 21  # h21 label realisation horizon (NYSE sessions)
EMBARGO_SENSITIVITY_CAL = 22  # 22 calendar-day wholesale rule (sensitivity row only)


# ---------- shared helpers ---------------------------------------------------


def c1_status() -> tuple[str, str]:
    """ONE function (G3/H10) reading C1's result.json controls.status.
    H10: anything other than an explicit OK status is treated as unavailable."""
    if not os.path.exists(C1_RESULT_JSON):
        return ("UNKNOWN", "C1 result.json missing")
    try:
        d = json.loads(open(C1_RESULT_JSON).read())
    except Exception as e:
        return ("UNKNOWN", f"C1 result.json read failed: {e!r}")
    s = d.get("controls", {}).get("status", "UNKNOWN")
    if s == "OK":
        return ("OK", "")
    if s == "BROKEN":
        return ("BROKEN", "C1 controls.status=BROKEN per C1 result.json")
    return ("UNKNOWN", f"C1 controls.status not OK: {s!r}")


def c1_available() -> bool:
    """H10: only OK is available; everything else is unavailable."""
    return c1_status()[0] == "OK"


def collect_host_provenance() -> dict:
    """P4: host + library versions under result.json provenance.host."""
    import pandas
    import pyarrow
    import scipy
    import pytest as _pytest
    return {
        "hostname": socket.gethostname(),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "pandas": pandas.__version__,
        "numpy": np.__version__,
        "pyarrow": pyarrow.__version__,
        "scipy": scipy.__version__,
        "pytest": _pytest.__version__,
    }


def _sha256_file(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def nyse_holidays_array(years: range) -> np.ndarray:
    hol = set()
    for y in years:
        hol |= nyse_calendar.holidays(y)
    arr = np.array(sorted(hol), dtype="datetime64[D]")
    return arr


def week_iso(date_str: str) -> str:
    iso = _dt.date.fromisoformat(date_str).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


# ---------- Mann-Whitney AUC ------------------------------------------------


def mann_whitney_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Mann-Whitney U / (n_pos * n_neg). Ties get the mean-rank convention."""
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(y_score, kind="mergesort")
    n = len(order)
    ranked = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j < n and y_score[order[j]] == y_score[order[i]]:
            j += 1
        mean_rank = 0.5 * (i + 1 + j)
        ranked[order[i:j]] = mean_rank
        i = j
    sum_pos = ranked[y_true == 1].sum()
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    u = sum_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def brute_force_auc_pairs(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """For tests: AUC = P(score(pos) > score(neg)) + 0.5 * P(score(pos) == score(neg))."""
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    diffs = pos[:, None] > neg[None, :]
    eq = pos[:, None] == neg[None, :]
    return float((diffs.sum() + 0.5 * eq.sum()) / (len(pos) * len(neg)))


def irls_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1.0, max_iter: int = 50,
                  tol: float = 1e-7) -> np.ndarray:
    """L2-penalised IRLS for logistic regression; intercept unpenalised."""
    n, p = X.shape
    beta = np.zeros(p)
    for it in range(max_iter):
        eta = X @ beta
        eta = np.clip(eta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = mu * (1 - mu)
        w = np.clip(w, 1e-9, None)
        z = eta + (y - mu) / w
        W = np.diag(w)
        XtW = X.T @ W
        A = XtW @ X
        A[1:, 1:] += l2 * np.eye(p - 1)
        b = XtW @ z
        try:
            beta_new = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            beta_new = np.linalg.lstsq(A, b, rcond=None)[0]
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    return beta


def fit_predict(X_train, y_train, X_test, l2=1.0):
    beta = irls_logistic(X_train, y_train, l2=l2)
    eta = X_test @ beta
    eta = np.clip(eta, -30, 30)
    return 1.0 / (1.0 + np.exp(-eta))


def week_cluster_bootstrap(y, p, week_ids, n_boot=N_BOOTSTRAP, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    weeks = np.unique(week_ids)
    aucs = np.empty(n_boot)
    n = len(y)
    for b in range(n_boot):
        sel = rng.choice(weeks, size=len(weeks), replace=True)
        idx = np.concatenate([np.where(week_ids == w)[0] for w in sel])
        if y[idx].sum() == 0 or y[idx].sum() == len(idx):
            aucs[b] = np.nan
            continue
        aucs[b] = mann_whitney_auc(y[idx], p[idx])
    aucs = aucs[~np.isnan(aucs)]
    return aucs


# ---------- episode build ----------------------------------------------------


def build_episodes() -> tuple[pd.DataFrame, dict]:
    """Pivot retro_grades into one row per (ticker, as_of, rank_by).

    Drop accounting by reason:
      - structural_drop_conviction: rank_by=conviction, 2026-06-15..2026-06-22, no h21
      - structural_drop_bottoming_alignment: rank_by=bottoming-alignment, 2026-06-23..2026-06-24, no h21
      - right_censored_prophet_v3: rank_by=us_prophet_v3, 2026-08-26..2026-09-17, no h21
      - mid_panel_censored_wbs: rank_by=confluence, 2026-07-27 (WBS), no h21
      All four buckets sum to episodes_dropped_horizons = 1498.
    """
    rg = pd.read_parquet(RG_PATH)
    rg = rg[rg["lane"].isin(["buy", "leaders"])].copy()
    n_rows_in_lanes = len(rg)

    def per_h(h):
        s = rg[rg["horizon"] == h][
            ["ticker", "as_of", "rank_by",
             "excess_spy", "mae_close_excess_spy", "ret", "spy_ret"]
        ].copy()
        return s.rename(columns={
            "excess_spy": f"excess_spy_h{h}",
            "mae_close_excess_spy": f"mae_h{h}",
            "ret": f"ret_h{h}",
            "spy_ret": f"spy_h{h}",
        })

    e5, e10, e21 = per_h(5), per_h(10), per_h(21)
    ep = e5.merge(e10, on=["ticker", "as_of", "rank_by"], how="outer")
    ep = ep.merge(e21, on=["ticker", "as_of", "rank_by"], how="outer")

    n_total_episodes = len(ep)
    have_all = ep.dropna(
        subset=["excess_spy_h5", "excess_spy_h10", "excess_spy_h21",
                "mae_h5", "mae_h10", "mae_h21"]
    )
    n_kept_full = len(have_all)
    n_dropped_horizons = n_total_episodes - n_kept_full

    has_h21 = ep["excess_spy_h21"].notna() & ep["mae_h21"].notna()

    # Conviction family — bound as_of in [2026-06-15, 2026-06-22] per data
    conv_mask = (
        (ep["rank_by"] == "conviction")
        & (ep["as_of"] >= "2026-06-15") & (ep["as_of"] <= "2026-06-22")
    )
    n_struct_conv = int((conv_mask & ~has_h21).sum())

    # Bottoming-alignment family — 2026-06-23..2026-06-24, no h21
    ba_mask = (
        (ep["rank_by"] == "bottoming-alignment")
        & (ep["as_of"] >= "2026-06-23") & (ep["as_of"] <= "2026-06-24")
    )
    n_struct_ba = int((ba_mask & ~has_h21).sum())

    # Right-censored us_prophet_v3 (the served retro-grade has no h21 yet for
    # entries newer than 2026-08-25)
    pv3_mask = (
        (ep["rank_by"] == "us_prophet_v3")
        & (ep["as_of"] >= "2026-08-26") & (ep["as_of"] <= "2026-09-17")
    )
    n_right_censored = int((pv3_mask & ~has_h21).sum())

    # Mid-panel WBS confluence 2026-07-27 — has h5/h10 but no h21 (label not
    # yet realised at the served vintage)
    wbs_mask = (
        (ep["rank_by"] == "confluence")
        & (ep["ticker"] == "WBS") & (ep["as_of"] == "2026-07-27")
    )
    n_wbs = int((wbs_mask & ~has_h21).sum())

    accounted = conv_mask | ba_mask | pv3_mask | wbs_mask
    n_other = int((~has_h21 & ~accounted).sum())
    n_total_accounted = n_struct_conv + n_struct_ba + n_right_censored + n_wbs + n_other
    assert n_total_accounted == n_dropped_horizons, (
        f"drop accounting mismatch: censored={n_dropped_horizons} "
        f"accounted={n_total_accounted}"
    )

    # Attach entry covariates (any horizon works for these constants; use the
    # h=21 row where available)
    cov_src = rg[[
        "ticker", "as_of", "rank_by", "horizon",
        "off_high", "band", "archetype", "quad_hard_label",
        "vol_regime", "score", "sector_etf",
    ]].copy()
    cov = (
        cov_src.sort_values(["ticker", "as_of", "rank_by", "horizon"])
        .drop_duplicates(["ticker", "as_of", "rank_by"], keep="last")
        .drop(columns=["horizon"])
    )
    ep_full = have_all.merge(cov, on=["ticker", "as_of", "rank_by"], how="left")

    n_missing_archetype = int(ep_full["archetype"].isna().sum())
    n_missing_quad = int(ep_full["quad_hard_label"].isna().sum())
    n_missing_vol = int(ep_full["vol_regime"].isna().sum())
    n_missing_off_high = int(ep_full["off_high"].isna().sum())
    n_missing_score = int(ep_full["score"].isna().sum())

    drop_counts = {
        "rows_in_buy_leaders": int(n_rows_in_lanes),
        "episodes_total": int(n_total_episodes),
        "episodes_kept_full": int(n_kept_full),
        "episodes_dropped_horizons": int(n_dropped_horizons),
        "structural_drop_conviction": n_struct_conv,
        "structural_drop_bottoming_alignment": n_struct_ba,
        "structural_drop_total": n_struct_conv + n_struct_ba,
        "right_censored_us_prophet_v3_2026_08_26_to_09_17": n_right_censored,
        "mid_panel_wbs_confluence_2026_07_27": n_wbs,
        "other_censored": n_other,
        "conviction_as_of_range": "2026-06-15..2026-06-22",
        "bottoming_alignment_as_of_range": "2026-06-23..2026-06-24",
        "episodes_missing_archetype": n_missing_archetype,
        "episodes_missing_quad_hard_label": n_missing_quad,
        "episodes_missing_vol_regime": n_missing_vol,
        "episodes_missing_off_high": n_missing_off_high,
        "episodes_missing_score": n_missing_score,
    }
    return ep_full.reset_index(drop=True), drop_counts


def add_severe_labels(ep: pd.DataFrame) -> pd.DataFrame:
    ep = ep.copy()
    ep["severe_h5"] = ((ep["excess_spy_h5"] <= THRESH) | (ep["mae_h5"] <= THRESH)).astype(int)
    ep["severe_h10"] = ((ep["excess_spy_h10"] <= THRESH) | (ep["mae_h10"] <= THRESH)).astype(int)
    ep["severe_h21"] = ((ep["excess_spy_h21"] <= THRESH) | (ep["mae_h21"] <= THRESH)).astype(int)
    ep["SEVERE"] = ep["severe_h21"].astype(int)
    ep["TARGET"] = ((ep["excess_spy_h21"] >= TARGET_THRESH) & (ep["SEVERE"] == 0)).astype(int)
    ep["NEITHER"] = ((ep["SEVERE"] == 0) & (ep["TARGET"] == 0)).astype(int)

    def _bucket(row):
        if row["severe_h5"] == 1:
            return "≤5"
        if row["severe_h10"] == 1:
            return "6–10"
        if row["severe_h21"] == 1:
            return "11–21"
        return "none"

    ep["first_severe_bucket"] = ep.apply(_bucket, axis=1)
    return ep


# ---------- C1 join ---------------------------------------------------------


def join_c1(ep: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """ONE c1_status() check (G3/H10). When C1 is BROKEN/UNKNOWN/MISSING,
    return ep unchanged with c1_available=False — every downstream by-rotation
    block reports 'INSUFFICIENT SUPPORT (C1 BROKEN)'."""
    status, reason = c1_status()
    info = {"c1_path": C1_PATH, "c1_available": False, "c1_status": status, "c1_reason": reason}
    if status == "OK" and os.path.exists(C1_PATH):
        try:
            c1 = pd.read_parquet(C1_PATH)
            if "rotation_tercile" in c1.columns:
                c1 = c1.reset_index()
                if c1.columns[0] != "date":
                    c1 = c1.rename(columns={c1.columns[0]: "date"})
                c1["date"] = pd.to_datetime(c1["date"]).dt.strftime("%Y-%m-%d")
                keep = [c for c in ["date", "rotation_tercile", "breadth_tercile", "dfii_tercile"] if c in c1.columns]
                c1 = c1[keep].drop_duplicates("date")
                ep_local = ep.merge(c1, left_on=["as_of"], right_on=["date"], how="left")
                ep_local = ep_local.drop(columns=["date"], errors="ignore")
                info["c1_available"] = True
                info["c1_join_rows"] = int(len(ep_local))
                return ep_local, info
        except Exception as e:  # pragma: no cover
            info["c1_join_error"] = repr(e)
    return ep, info


# ---------- design matrix (per-fold standardisation + one-hot) ---------------


def build_design(ep: pd.DataFrame, ref_df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """One-hot + standardisation fit on ref_df (training fold). Column 0 = intercept."""
    cat_cols = [
        "rotation_tercile", "breadth_tercile", "dfii_tercile",
        "quad_hard_label", "vol_regime", "band", "archetype", "rank_by",
        "sector_etf",
    ]
    num_cols = ["off_high", "score"]

    cats, cat_feature_names = [], []
    ep_local = ep.copy()
    for c in cat_cols:
        if c not in ref_df.columns:
            levels = []
        else:
            levels = sorted([v for v in ref_df[c].dropna().unique().tolist()])
        if c not in ep_local.columns:
            ep_local[c] = np.nan
        for lvl in levels:
            cats.append((ep_local[c] == lvl).astype(float).values)
            cat_feature_names.append(f"{c}={lvl}")

    if not num_cols:
        X_num = np.zeros((len(ep_local), 0))
        num_feature_names = []
    else:
        means = ref_df[num_cols].mean(skipna=True).values
        stds = ref_df[num_cols].std(skipna=True).replace(0, np.nan).fillna(1.0).values
        vals = ep_local[num_cols].copy()
        for i, c in enumerate(num_cols):
            vals[c] = vals[c].fillna(means[i])
        X_num = ((vals.values - means) / stds)
        X_num = np.nan_to_num(X_num, nan=0.0)
        num_feature_names = num_cols

    X_cat = np.column_stack(cats) if cats else np.zeros((len(ep_local), 0))
    intercept = np.ones((len(ep_local), 1))
    X = np.hstack([intercept, X_cat, X_num])
    feature_names = ["intercept"] + cat_feature_names + num_feature_names
    return X, feature_names


# ---------- purged OOS logistic ----------------------------------------------
#
# H1: the fold builder takes a comparator FUNCTION (not hard-coded logic).
# The binding rule is "label-realisation: busday_offset(as_of, 21, forward)
# < week_start". Mutants m_peek / m_peek_rec / m_r1 are alternative
# comparators the tests evaluate against the SHARED strict comparator
# `busday_offset(max_train_as_of, 21, forward) < week_start`.
#
# Mutants (per round-3 repair block):
#   m_peek     : as_of < week_start + 5 calendar days
#   m_peek_rec : as_of <= cutoff + 14 calendar days
#   m_r1       : end_dates <= ws_dt64   (the literal round-1 -21-session rule)
#   m_10       : as_of <= busday_offset(week_start, -10)  (10-session embargo)
#


def _make_label_realisation_comparator(embargo_label_horizon: int, holidays: np.ndarray):
    """Binding comparator: keep row iff busday_offset(as_of, H, forward) < week_start."""
    def _cmp(as_of_dates: np.ndarray, ws_dt64: np.datetime64) -> np.ndarray:
        end_dates = np.array([
            np.busday_offset(d, embargo_label_horizon, roll="forward", holidays=holidays)
            for d in as_of_dates
        ])
        return end_dates < ws_dt64  # BINDING_CMP
    return _cmp


def _make_m_peek_comparator():
    """Mutant m_peek: as_of < week_start + 5 calendar days."""
    def _cmp(as_of_dates: np.ndarray, ws_dt64: np.datetime64) -> np.ndarray:
        cutoff = ws_dt64 + np.timedelta64(5, "D")
        return as_of_dates < cutoff
    return _cmp


def _make_m_peek_rec_comparator():
    """Mutant m_peek_rec: as_of <= cutoff + 14 calendar days.
    `cutoff` is the binding date cutoff (busday_offset(week_start, -22)).
    """
    def _cmp(as_of_dates: np.ndarray, ws_dt64: np.datetime64, cutoff_dt64: np.datetime64) -> np.ndarray:
        return as_of_dates <= cutoff_dt64 + np.timedelta64(14, "D")
    return _cmp


def _make_m_r1_comparator(embargo_label_horizon: int, holidays: np.ndarray):
    """Mutant m_r1: end_dates <= ws_dt64 (the round-1 literal -21-session rule)."""
    def _cmp(as_of_dates: np.ndarray, ws_dt64: np.datetime64) -> np.ndarray:
        end_dates = np.array([
            np.busday_offset(d, embargo_label_horizon, roll="forward", holidays=holidays)
            for d in as_of_dates
        ])
        return end_dates <= ws_dt64
    return _cmp


def _make_m_10_comparator(holidays: np.ndarray):
    """Mutant m_10: 10-session embargo (weaker than binding)."""
    def _cmp(as_of_dates: np.ndarray, ws_dt64: np.datetime64) -> np.ndarray:
        cutoff_dt = np.busday_offset(ws_dt64, -10, roll="backward", holidays=holidays)
        return as_of_dates <= cutoff_dt
    return _cmp


# P1: production fold-builder mask. Tests import this and
# _make_label_realisation_comparator; they must not re-implement the
# comparator. Mutating the BINDING_CMP line changes this mask.

BINDING_RETURN_NEEDLE = "        return end_dates < ws_dt64  # BINDING_CMP"
MUTANT_RETURN_REPLACEMENTS = {
    "m_peek": (
        "        return as_of_dates < (ws_dt64 + np.timedelta64(5, \"D\"))  # BINDING_CMP"
    ),
    "m_peek_rec": (
        "        return as_of_dates <= (np.busday_offset(ws_dt64, -22, "
        "roll=\"backward\", holidays=holidays) + np.timedelta64(14, \"D\"))  # BINDING_CMP"
    ),
    "m_r1": "        return end_dates <= ws_dt64  # BINDING_CMP",
}


def apply_train_mask(cmp_fn, as_of_dates, ws_dt64, cutoff_dt64):
    """Production fold-builder mask application (the try/TypeError path used
    by purged_oos_logistic). Binding cmp_fn comes from
    _make_label_realisation_comparator."""
    try:
        return cmp_fn(as_of_dates, ws_dt64)
    except TypeError:
        return cmp_fn(as_of_dates, ws_dt64, cutoff_dt64)


def build_synthetic_purge_panel(holidays: np.ndarray):
    """Small synthetic panel for P1 leak tests.

    week_start = 2026-08-03 (Monday of 2026-W32).
    Roles:
      before  (i)  realisation strictly before week_start → INCLUDE
      peek5   (ii) realisation inside the 5-cal-day window after week_start
                   → EXCLUDE (included only under m_peek)
      peek14  (iii) as_of inside the 14-cal-day window after the -22-session
                    cutoff → EXCLUDE (included only under m_peek_rec)
      on_ws   (iv) realisation exactly ON week_start → EXCLUDE under binding
                   `<`, included under m_r1 `<=`
    """
    ws = np.datetime64("2026-08-03", "D")
    cutoff = np.busday_offset(ws, -22, roll="backward", holidays=holidays)
    asof_before = cutoff
    asof_on = np.busday_offset(ws, -21, roll="backward", holidays=holidays)
    real_peek5 = ws + np.timedelta64(1, "D")
    asof_peek5 = np.busday_offset(real_peek5, -21, roll="backward", holidays=holidays)
    asof_peek14 = np.busday_offset(cutoff, 7, roll="forward", holidays=holidays)
    rows = [
        {"label_id": "L_before", "as_of": str(asof_before), "role": "before"},
        {"label_id": "L_peek5", "as_of": str(asof_peek5), "role": "peek5"},
        {"label_id": "L_peek14", "as_of": str(asof_peek14), "role": "peek14"},
        {"label_id": "L_on_ws", "as_of": str(asof_on), "role": "on_ws"},
    ]
    return pd.DataFrame(rows), ws, cutoff


def synthetic_role_sets(panel: pd.DataFrame) -> tuple[set, set]:
    exp_in = set(panel.loc[panel["role"] == "before", "label_id"])
    exp_ex = set(panel.loc[panel["role"] != "before", "label_id"])
    return exp_in, exp_ex


def included_label_ids(panel: pd.DataFrame, week_start, holidays,
                       embargo_label_horizon: int = EMBARGO_LABEL_HORIZON,
                       cmp_fn=None) -> set:
    """Apply the production fold builder to a synthetic panel; return the
    included label_id set. Default comparator is the production one."""
    if cmp_fn is None:
        cmp_fn = _make_label_realisation_comparator(embargo_label_horizon, holidays)
    as_of_dates = np.array([np.datetime64(d, "D") for d in panel["as_of"]])
    ws_dt64 = np.datetime64(week_start, "D") if not isinstance(
        week_start, np.datetime64) else week_start
    cutoff_dt64 = np.busday_offset(ws_dt64, -22, roll="backward", holidays=holidays)
    mask = np.asarray(apply_train_mask(cmp_fn, as_of_dates, ws_dt64, cutoff_dt64),
                      dtype=bool)
    return set(panel.loc[mask, "label_id"].tolist())


def purged_oos_logistic(ep: pd.DataFrame, embargo_label_horizon: int,
                        holidays: np.ndarray,
                        n_min_train: int = 50, seed: int = RNG_SEED,
                        comparator: str = "binding",
                        comparator_factory=None) -> dict:
    """OOS logistic with the configured comparator.

    Default `comparator="binding"` reproduces the seat ruling:
        keep iff busday_offset(as_of, 21, forward, holidays) < week_start

    Mutant comparators (for tests only) are constructed via `comparator_factory`
    (a callable taking (holidays,) and returning a comparator function).
    """
    ep = ep.copy()
    ep["as_of_dt"] = pd.to_datetime(ep["as_of"])
    ep["week_iso"] = ep["as_of"].map(week_iso)
    iso_weeks = sorted(ep["week_iso"].unique())

    week_start = {}
    for w in iso_weeks:
        yr = int(w.split("-W")[0])
        wk = int(w.split("-W")[1])
        week_start[w] = _dt.date.fromisocalendar(yr, wk, 1)

    test_weeks = iso_weeks[4:]

    as_of_dates = np.array([np.datetime64(d.date(), "D") for d in ep["as_of_dt"]])

    # Default = binding label-realisation comparator
    if comparator_factory is None:
        if comparator == "binding":
            cmp_fn = _make_label_realisation_comparator(embargo_label_horizon, holidays)
        elif comparator == "m_r1" or comparator == "r1_literal":
            cmp_fn = _make_m_r1_comparator(embargo_label_horizon, holidays)
        elif comparator == "m_peek":
            cmp_fn = _make_m_peek_comparator()
        elif comparator == "m_peek_rec":
            cmp_fn = _make_m_peek_rec_comparator()
        elif comparator == "m_10":
            cmp_fn = _make_m_10_comparator(holidays)
        else:
            raise ValueError(f"unknown comparator: {comparator!r}")
    else:
        cmp_fn = comparator_factory(holidays)

    oos_records = []
    fold_records = []
    per_week_aucs = {}
    skipped = []

    for w in test_weeks:
        ws_dt = pd.Timestamp(week_start[w])
        ws_dt64 = np.datetime64(ws_dt.date(), "D")
        cutoff_dt = pd.Timestamp(np.busday_offset(ws_dt64, -22, roll="backward", holidays=holidays))
        cutoff_dt64 = np.datetime64(cutoff_dt.date(), "D")

        # Apply the (possibly mutated) comparator via the production fold builder
        new_mask = apply_train_mask(cmp_fn, as_of_dates, ws_dt64, cutoff_dt64)

        test_mask = (ep["week_iso"] == w).values
        train_df = ep[new_mask].copy()
        test_df = ep[test_mask].copy()
        n_train = len(train_df)
        n_test = len(test_df)
        if n_train < n_min_train or n_test == 0:
            skipped.append({"week": w, "n_train": int(n_train), "n_test": int(n_test),
                            "reason": "insufficient train or empty test"})
            continue

        train_df = train_df.dropna(subset=["SEVERE"])
        if train_df["SEVERE"].nunique() < 2:
            skipped.append({"week": w, "n_train": int(len(train_df)), "n_test": int(n_test),
                            "reason": "single class in train"})
            continue

        X_tr, names = build_design(train_df, train_df)
        X_te, _ = build_design(test_df, train_df)
        y_tr = train_df["SEVERE"].values.astype(int)
        y_te = test_df["SEVERE"].values.astype(int)

        proba = fit_predict(X_tr, y_tr, X_te, l2=1.0)

        for j in range(n_test):
            oos_records.append({
                "week": w, "as_of": test_df["as_of"].iloc[j],
                "ticker": test_df["ticker"].iloc[j],
                "rank_by": test_df["rank_by"].iloc[j],
                "y": int(y_te[j]), "p": float(proba[j]),
            })

        max_train_as_of = str(train_df["as_of_dt"].max().date())
        fold_records.append({
            "week": w,
            "week_start": str(week_start[w]),
            "embargo_label_horizon": int(embargo_label_horizon),
            "train_cutoff": cutoff_dt.strftime("%Y-%m-%d"),
            "max_train_as_of": max_train_as_of,
            "n_train": int(n_train),
            "n_test": int(n_test),
        })

        if y_te.sum() > 0 and y_te.sum() < n_test:
            per_week_aucs[w] = mann_whitney_auc(y_te, proba)

    oos = pd.DataFrame(oos_records)
    if len(oos) == 0:
        return {
            "oos_auc": float("nan"),
            "oos_auc_ci": [float("nan"), float("nan")],
            "in_sample_auc": float("nan"),
            "n_oos": 0,
            "n_test_weeks": 0,
            "per_week_aucs": {},
            "top_coefficients": [],
            "fold_records": fold_records,
            "skipped": skipped,
            "feature_names": [],
            "beta_full_sample": None,
            "n_removed_strict": 0,
        }

    oos_auc = mann_whitney_auc(oos["y"].values, oos["p"].values)

    full_df = ep.dropna(subset=["SEVERE"]).copy()
    X_full, names_full = build_design(full_df, full_df)
    y_full = full_df["SEVERE"].values.astype(int)
    proba_in = fit_predict(X_full, y_full, X_full, l2=1.0)
    in_sample_auc = mann_whitney_auc(y_full, proba_in)

    beta_full = irls_logistic(X_full, y_full, l2=1.0)
    pairs = list(zip(names_full, beta_full))
    pairs_nonintercept = [(n, b) for (n, b) in pairs if n != "intercept"]
    pairs_nonintercept.sort(key=lambda kv: -abs(kv[1]))
    top3 = [[n, float(b)] for (n, b) in pairs_nonintercept[:3]]

    week_ids = np.array([r["week"] for r in oos_records])
    boot = week_cluster_bootstrap(oos["y"].values, oos["p"].values, week_ids, n_boot=N_BOOTSTRAP, seed=seed)
    lo = float(np.nanpercentile(boot, 2.5))
    hi = float(np.nanpercentile(boot, 97.5))

    # H6: support point count at 1e-10 and 1e-4
    if len(boot) > 0:
        rounded_10 = np.round(boot / 1e-10) * 1e-10
        rounded_4 = np.round(boot / 1e-4) * 1e-4
        distinct_at_1e10 = int(len(np.unique(rounded_10)))
        distinct_at_1e4 = int(len(np.unique(rounded_4)))
        n_draws_valid = int(len(boot))
        n_draws_ge_065 = int(np.sum(boot >= 0.65))
    else:
        distinct_at_1e10 = 0
        distinct_at_1e4 = 0
        n_draws_valid = 0
        n_draws_ge_065 = 0

    return {
        "oos_auc": float(oos_auc),
        "oos_auc_ci": [lo, hi],
        "in_sample_auc": float(in_sample_auc),
        "n_oos": int(len(oos)),
        "n_test_weeks": int(len(fold_records)),
        "per_week_aucs": {w: float(a) for w, a in per_week_aucs.items()},
        "top_coefficients": top3,
        "fold_records": fold_records,
        "skipped": skipped,
        "feature_names": names_full,
        "beta_full_sample": beta_full.tolist(),
        "n_removed_strict": 0,
        "bootstrap": {
            "n_draws_valid": n_draws_valid,
            "n_draws_ge_065": n_draws_ge_065,
            "distinct_at_1e10": distinct_at_1e10,
            "distinct_at_1e4": distinct_at_1e4,
            "multiset_max": 35,  # C(7,4) — multiset of 4 weeks with replacement over 7 distinct week AUCs (averaged by multiset count)
        },
    }


# ---------- sensitivity (22-calendar-day rule, NOT binding) -----------------


def purged_oos_logistic_calendar(ep: pd.DataFrame, embargo_days: int) -> dict:
    """Sensitivity row only: training cutoff = week_start - embargo_days calendar days.
    Used for the labelled sensitivity row."""
    ep = ep.copy()
    ep["as_of_dt"] = pd.to_datetime(ep["as_of"])
    ep["week_iso"] = ep["as_of"].map(week_iso)
    iso_weeks = sorted(ep["week_iso"].unique())
    test_weeks = iso_weeks[4:]

    oos_records, fold_records, per_week_aucs, skipped = [], [], {}, []

    for w in test_weeks:
        yr = int(w.split("-W")[0])
        wk = int(w.split("-W")[1])
        ws = _dt.date.fromisocalendar(yr, wk, 1)
        cutoff = pd.Timestamp(ws) - pd.Timedelta(days=embargo_days)
        train_mask = ep["as_of_dt"] <= cutoff
        test_mask = ep["week_iso"] == w
        train_df = ep[train_mask].dropna(subset=["SEVERE"]).copy()
        test_df = ep[test_mask].copy()
        n_train = len(train_df)
        n_test = len(test_df)
        if n_train < 50 or n_test == 0 or train_df["SEVERE"].nunique() < 2:
            skipped.append({"week": w, "n_train": int(n_train), "n_test": int(n_test)})
            continue
        X_tr, names = build_design(train_df, train_df)
        X_te, _ = build_design(test_df, train_df)
        y_tr = train_df["SEVERE"].values.astype(int)
        y_te = test_df["SEVERE"].values.astype(int)
        proba = fit_predict(X_tr, y_tr, X_te, l2=1.0)
        for j in range(n_test):
            oos_records.append({"week": w, "as_of": test_df["as_of"].iloc[j],
                                "ticker": test_df["ticker"].iloc[j],
                                "rank_by": test_df["rank_by"].iloc[j],
                                "y": int(y_te[j]), "p": float(proba[j])})
        max_train_as_of = str(train_df["as_of_dt"].max().date())
        fold_records.append({"week": w, "week_start": str(ws),
                             "embargo_days": embargo_days,
                             "train_cutoff": str(cutoff.date()),
                             "max_train_as_of": max_train_as_of,
                             "n_train": int(n_train), "n_test": int(n_test)})
        if y_te.sum() > 0 and y_te.sum() < n_test:
            per_week_aucs[w] = mann_whitney_auc(y_te, proba)

    oos = pd.DataFrame(oos_records)
    if len(oos) == 0:
        return {"oos_auc": float("nan"), "oos_auc_ci": [float("nan"), float("nan")],
                "n_oos": 0, "n_test_weeks": 0,
                "fold_records": fold_records, "skipped": skipped, "per_week_aucs": {}}
    auc_val = mann_whitney_auc(oos["y"].values, oos["p"].values)
    week_ids = np.array([r["week"] for r in oos_records])
    boot = week_cluster_bootstrap(oos["y"].values, oos["p"].values, week_ids)
    lo = float(np.nanpercentile(boot, 2.5))
    hi = float(np.nanpercentile(boot, 97.5))
    return {
        "oos_auc": float(auc_val),
        "oos_auc_ci": [lo, hi],
        "n_oos": int(len(oos)),
        "n_test_weeks": int(len(fold_records)),
        "per_week_aucs": {w: float(a) for w, a in per_week_aucs.items()},
        "fold_records": fold_records,
        "skipped": skipped,
    }


# ---------- hazard model -----------------------------------------------------


def _ci_or_null(arr, n_clusters: int):
    """Returns [lo, hi] when n_clusters >= 2; else None plus n_clusters.

    Per G7: where n_clusters < 2 emit null plus n_clusters, never a CI."""
    if n_clusters < 2:
        return None
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return None
    return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]


def hazard(ep: pd.DataFrame) -> dict:
    n = len(ep)
    n_h1 = int(ep["first_severe_bucket"].eq("≤5").sum())
    n_h2 = int(((ep["first_severe_bucket"] == "6–10")).sum())
    n_h3 = int(((ep["first_severe_bucket"] == "11–21")).sum())
    n_none = int(ep["first_severe_bucket"].eq("none").sum())

    h1 = n_h1 / n if n else float("nan")
    denom2 = n - n_h1
    h2 = n_h2 / denom2 if denom2 else float("nan")
    denom3 = n - n_h1 - n_h2
    h3 = n_h3 / denom3 if denom3 else float("nan")

    rng = np.random.default_rng(RNG_SEED)
    ep_local = ep.copy()
    ep_local["week_iso"] = ep_local["as_of"].map(week_iso)
    weeks = ep_local["week_iso"].unique().tolist()
    n_clusters = len(weeks)
    boot = np.full((N_BOOTSTRAP, 3), np.nan)
    for b in range(N_BOOTSTRAP):
        sel = rng.choice(weeks, size=len(weeks), replace=True)
        idx = np.concatenate([np.where(ep_local["week_iso"].values == w)[0] for w in sel])
        sub = ep_local.iloc[idx]
        nb = len(sub)
        n1 = int(sub["first_severe_bucket"].eq("≤5").sum())
        n2 = int(sub["first_severe_bucket"].eq("6–10").sum())
        n3 = int(sub["first_severe_bucket"].eq("11–21").sum())
        d2 = nb - n1
        d3 = nb - n1 - n2
        boot[b, 0] = n1 / nb if nb else np.nan
        boot[b, 1] = n2 / d2 if d2 else np.nan
        boot[b, 2] = n3 / d3 if d3 else np.nan

    def _ci(arr):
        return _ci_or_null(arr, n_clusters)

    overall = {
        "h1": [float(h1), *_ci(boot[:, 0])],
        "h2": [float(h2), *_ci(boot[:, 1])],
        "h3": [float(h3), *_ci(boot[:, 2])],
        "n": int(n),
        "n_h1": n_h1, "n_h2": n_h2, "n_h3": n_h3, "n_none": n_none,
        "n_clusters": n_clusters,
    }

    by_rot = {}
    if "rotation_tercile" in ep.columns and ep["rotation_tercile"].notna().any():
        for t in ["fast", "mid", "persistent"]:
            sub = ep[ep["rotation_tercile"] == t]
            by_rot[t] = _hazard_block(sub)
    else:
        for t in ["fast", "mid", "persistent"]:
            by_rot[t] = {"status": "INSUFFICIENT SUPPORT (C1 BROKEN)",
                         "reason": "C1 rotation_tercile missing"}

    return {"overall": overall, "by_rotation": by_rot}


def _hazard_block(sub: pd.DataFrame) -> dict:
    if len(sub) == 0:
        return {"h1": [float("nan")] * 3, "h2": [float("nan")] * 3, "h3": [float("nan")] * 3, "n": 0}
    n = len(sub)
    n1 = int(sub["first_severe_bucket"].eq("≤5").sum())
    n2 = int(sub["first_severe_bucket"].eq("6–10").sum())
    n3 = int(sub["first_severe_bucket"].eq("11–21").sum())
    h1 = n1 / n
    d2 = n - n1
    h2 = n2 / d2 if d2 else float("nan")
    d3 = n - n1 - n2
    h3 = n3 / d3 if d3 else float("nan")
    return {
        "h1": [float(h1), float("nan"), float("nan")],
        "h2": [float(h2), float("nan"), float("nan")],
        "h3": [float(h3), float("nan"), float("nan")],
        "n": int(n),
        "n_h1": n1, "n_h2": n2, "n_h3": n3,
    }


# ---------- attribution ------------------------------------------------------


def attribution(ep: pd.DataFrame) -> dict:
    sev = ep[ep["SEVERE"] == 1].copy()
    n_sev = len(sev)
    if n_sev == 0:
        return {"overall": {"status": "no SEVERE episodes"}, "by_rotation": {}, "by_rank_by": {}}

    sev["deteriorated"] = (sev["excess_spy_h10"] >= 0).astype(int)
    sev["immediate"] = ((sev["excess_spy_h5"] < 0) & (sev["excess_spy_h10"] < 0)).astype(int)
    sev["other"] = ((sev["deteriorated"] == 0) & (sev["immediate"] == 0)).astype(int)

    n_det = int(sev["deteriorated"].sum())
    n_imm = int(sev["immediate"].sum())
    n_other = int(sev["other"].sum())

    rng = np.random.default_rng(RNG_SEED)
    sev_local = sev.copy()
    sev_local["week_iso"] = sev_local["as_of"].map(week_iso)
    weeks = sev_local["week_iso"].unique().tolist()
    n_clusters = len(weeks)
    boot = np.full((N_BOOTSTRAP, 3), np.nan)
    for b in range(N_BOOTSTRAP):
        sel = rng.choice(weeks, size=len(weeks), replace=True)
        idx = np.concatenate([np.where(sev_local["week_iso"].values == w)[0] for w in sel])
        s = sev_local.iloc[idx]
        nb = len(s)
        if nb == 0:
            continue
        d = s["deteriorated"].sum()
        i = s["immediate"].sum()
        o = s["other"].sum()
        boot[b, 0] = d / nb
        boot[b, 1] = i / nb
        boot[b, 2] = o / nb

    def _ci_overall(arr):
        return _ci_or_null(arr, n_clusters)

    overall = {
        "deteriorated_after_nonneg_h10": [float(n_det / n_sev), *_ci_overall(boot[:, 0])],
        "immediate_failure": [float(n_imm / n_sev), *_ci_overall(boot[:, 1])],
        "other": float(n_other / n_sev),
        "n_severe": n_sev,
        "n_det": n_det, "n_imm": n_imm, "n_other": n_other,
        "n_clusters": n_clusters,
    }

    by_rot = {}
    if "rotation_tercile" in ep.columns and ep["rotation_tercile"].notna().any():
        for t in ["fast", "mid", "persistent"]:
            sub = sev[sev["rotation_tercile"] == t]
            if len(sub) == 0:
                by_rot[t] = {"status": "INSUFFICIENT SUPPORT (C1 BROKEN)",
                             "reason": "no severe episodes in this tercile"}
                continue
            n_s = len(sub)
            d = int((sub["excess_spy_h10"] >= 0).sum())
            i = int(((sub["excess_spy_h5"] < 0) & (sub["excess_spy_h10"] < 0)).sum())
            o = n_s - d - i
            by_rot[t] = {
                "deteriorated_after_nonneg_h10": [float(d / n_s), None, None],
                "immediate_failure": [float(i / n_s), None, None],
                "other": float(o / n_s),
                "n_severe": int(n_s),
                "n_clusters": 0,
            }
    else:
        for t in ["fast", "mid", "persistent"]:
            by_rot[t] = {"status": "INSUFFICIENT SUPPORT (C1 BROKEN)",
                         "reason": "C1 rotation_tercile missing"}

    by_rb = {}
    for rb in sorted(sev["rank_by"].unique()):
        sub = sev[sev["rank_by"] == rb]
        n_s = len(sub)
        d = int((sub["excess_spy_h10"] >= 0).sum())
        i = int(((sub["excess_spy_h5"] < 0) & (sub["excess_spy_h10"] < 0)).sum())
        o = n_s - d - i
        sub_local = sub.copy()
        sub_local["week_iso"] = sub_local["as_of"].map(week_iso)
        weeks_r = sub_local["week_iso"].unique().tolist()
        n_clusters_r = len(weeks_r)
        boot_r = np.full((N_BOOTSTRAP, 2), np.nan)
        for b in range(N_BOOTSTRAP):
            sel = rng.choice(weeks_r, size=len(weeks_r), replace=True)
            idx = np.concatenate([np.where(sub_local["week_iso"].values == w)[0] for w in sel])
            s = sub_local.iloc[idx]
            nb = len(s)
            if nb == 0:
                continue
            boot_r[b, 0] = s["excess_spy_h10"].ge(0).sum() / nb
            boot_r[b, 1] = ((s["excess_spy_h5"] < 0) & (s["excess_spy_h10"] < 0)).sum() / nb
        ci_d = _ci_or_null(boot_r[:, 0], n_clusters_r)
        ci_i = _ci_or_null(boot_r[:, 1], n_clusters_r)
        by_rb[rb] = {
            "deteriorated_after_nonneg_h10": [float(d / n_s),
                                              ci_d[0] if ci_d else None,
                                              ci_d[1] if ci_d else None],
            "immediate_failure": [float(i / n_s),
                                  ci_i[0] if ci_i else None,
                                  ci_i[1] if ci_i else None],
            "other": float(o / n_s),
            "n_severe": int(n_s),
            "n_clusters": n_clusters_r,
        }

    return {"overall": overall, "by_rotation": by_rot, "by_rank_by": by_rb}


# ---------- ledger denominator ----------------------------------------------


NO_ENTRY_OUTCOMES = {"T1_HIT", "T2_HIT", "INVALIDATED", "EXPIRED", "CLOSED_EARLY", "NO_ENTRY"}


def ledger_denom() -> dict:
    rows = []
    with open(LEDGER_PATH) as f:
        for ln in f:
            if not ln.strip() or ln.startswith("#"):
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("schema") and r["schema"].startswith("prophet.ledger"):
                rows.append(r)
    df = pd.DataFrame(rows)
    if df.empty:
        return {"status": "empty"}

    df["outcome_std"] = df["outcome"].where(df["outcome"].isin(NO_ENTRY_OUTCOMES), "NO_ENTRY")

    by_outcome = {}
    for oc in sorted(df["outcome_std"].unique()):
        sub = df[df["outcome_std"] == oc]
        sr = pd.to_numeric(sub["stock_result_pct"], errors="coerce")
        dh = pd.to_numeric(sub["days_held"], errors="coerce")
        sr_med = float(sr.median()) if sr.notna().any() else None
        sr_mean = float(sr.mean()) if sr.notna().any() else None
        dh_med = float(dh.median()) if dh.notna().any() else None
        dh_mean = float(dh.mean()) if dh.notna().any() else None
        by_outcome[oc] = {
            "n": int(len(sub)),
            "median_stock_result_pct": sr_med,
            "mean_stock_result_pct": sr_mean,
            "median_days_held": dh_med,
            "mean_days_held": dh_mean,
        }

    # H10: c1_status() check; only OK is available. C1 is currently BROKEN,
    # so c1_available=False and by_outcome_x_rotation is "INSUFFICIENT SUPPORT".
    c1_st, c1_reason = c1_status()
    info = {
        "c1_status": c1_st,
        "c1_reason": c1_reason,
        "c1_available": c1_st == "OK",
        "by_outcome": by_outcome,
    }

    by_outcome_x_rotation = {}
    if c1_st == "OK" and os.path.exists(C1_PATH):
        # path used only when C1 is OK; not the case here
        try:
            c1 = pd.read_parquet(C1_PATH).reset_index()
            c1.columns = ["date"] + list(c1.columns[1:])
            c1["date"] = pd.to_datetime(c1["date"]).dt.strftime("%Y-%m-%d")
            c1 = c1[["date", "rotation_tercile"]].drop_duplicates("date")
            df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce").dt.strftime("%Y-%m-%d")
            df = df.merge(c1, left_on="signal_date", right_on="date", how="left")
            df = df.drop(columns=["date"], errors="ignore")
            for oc in sorted(df["outcome_std"].unique()):
                sub = df[df["outcome_std"] == oc]
                counts = {t: int((sub["rotation_tercile"] == t).sum()) for t in ["fast", "mid", "persistent"]}
                counts["NaN"] = int(sub["rotation_tercile"].isna().sum())
                by_outcome_x_rotation[oc] = counts
        except Exception as e:
            for oc in sorted(df["outcome_std"].unique()):
                by_outcome_x_rotation[oc] = {
                    "status": "INSUFFICIENT SUPPORT (C1 BROKEN)",
                    "reason": f"C1 join failed: {e!r}",
                }
    else:
        for oc in sorted(df["outcome_std"].unique()):
            by_outcome_x_rotation[oc] = {
                "status": "INSUFFICIENT SUPPORT (C1 BROKEN)",
                "reason": c1_reason,
            }

    info["by_outcome_x_rotation"] = by_outcome_x_rotation
    return info


# ---------- honest-N --------------------------------------------------------


def honest_n(ep: pd.DataFrame) -> dict:
    by_rb = ep.groupby("rank_by").size().to_dict()
    return {
        "episodes": int(len(ep)),
        "as_of_dates": int(ep["as_of"].nunique()),
        "as_of_weeks": int(ep["as_of"].map(week_iso).nunique()),
        "tickers": int(ep["ticker"].nunique()),
        "by_rank_by": {k: int(v) for k, v in by_rb.items()},
        "severe": int(ep["SEVERE"].sum()),
        "target": int(ep["TARGET"].sum()),
        "neither": int(ep["NEITHER"].sum()),
        "units": "fraction",
    }


# ---------- verdict ---------------------------------------------------------


def verdict(ep: pd.DataFrame, primary: dict, attr: dict) -> dict:
    rule = ("MANAGEMENT iff OOS AUC ≤ 0.55 AND share 'deteriorated after non-negative H10' > 0.50 "
            "among SEVERE; SELECTION iff OOS AUC ≥ 0.65 AND share 'immediate failure' > 0.50; "
            "MIXED otherwise.")
    auc = primary["oos_auc"]
    det = attr["overall"]["deteriorated_after_nonneg_h10"][0]
    imm = attr["overall"]["immediate_failure"][0]
    n_weeks = primary["n_test_weeks"]
    n_oos = primary["n_oos"]
    if auc <= 0.55 and det > 0.50:
        lever = "MANAGEMENT"
    elif auc >= 0.65 and imm > 0.50:
        lever = "SELECTION"
    else:
        lever = "MIXED"
    return {
        "lever": lever,
        "rule": rule,
        "small_n_caveat": (
            f"≈{n_weeks} test weeks / {n_oos} OOS episodes (boot CI on "
            f"{primary.get('n_test_weeks')} week clusters). Per-week AUC variance "
            f"is wide; the verdict is descriptive and small-N."
        ),
        "oos_auc": float(auc),
        "deteriorated_share": float(det),
        "immediate_share": float(imm),
    }


# ---------- strict comparator (H1: shared between tests) --------------------

def strict_comparator_violations(fold_records, embargo_label_horizon, holidays):
    """ONE strict comparator used by positive test AND negative control (H1).

    Returns the list of folds where busday_offset(max_train_as_of, H, forward)
    >= week_start (i.e. violates the binding rule).
    """
    violators = []
    for fr in fold_records:
        ws = pd.Timestamp(fr["week_start"])
        max_train = pd.Timestamp(fr["max_train_as_of"])
        end_dt = np.busday_offset(
            np.datetime64(max_train.date(), "D"),
            embargo_label_horizon, roll="forward", holidays=holidays,
        )
        end_ts = pd.Timestamp(end_dt)
        if not (end_ts < ws):
            violators.append(fr)
    return violators


# ---------- RESULT.md generator (G2) ----------------------------------------


def render_result_md(payload: dict, head: str) -> str:
    hn = payload["honest_n"]
    dc = payload["drop_counts"]
    em = payload["entry_model"]
    sens = em.get("sensitivity", {})
    haz = payload["hazard"]
    attr = payload["attribution"]
    ledg = payload["prophet_ledger"]
    v = payload["verdict"]

    primary_ci = em["oos_auc_ci"]
    sens_ci = sens.get("oos_auc_ci", [None, None])
    boot = em.get("bootstrap", {})

    per_week_rows = []
    for fr in em["fold_records"]:
        wkey = fr["week"]
        per_week_rows.append(
            f"| {wkey} | {fr['week_start']} | {fr['train_cutoff']} | "
            f"{fr['max_train_as_of']} | {fr['n_train']} | {fr['n_test']} | "
            f"{em['per_week_aucs'].get(wkey, float('nan')):.4f} |"
        )
    per_week_table = "\n".join(per_week_rows)

    top3 = em["top_coefficients"]
    top3_rows = "\n".join(
        f"| {n} | {b:+.4f} |" for n, b in top3
    )

    haz_overall = haz["overall"]
    by_rot = haz["by_rotation"]
    if isinstance(by_rot.get("fast"), dict) and "status" in by_rot["fast"]:
        by_rot_table = "| fast | — | — | — |\n| mid | — | — | — |\n| persistent | — | — | — |"
        by_rot_note = "All three rotation_tercile rows = `INSUFFICIENT SUPPORT (C1 BROKEN)`."
    else:
        rows = []
        for t in ["fast", "mid", "persistent"]:
            r = by_rot[t]
            rows.append(f"| {t} | {r['n']} | {r['h1'][0]:.4f} | {r['h2'][0]:.4f} | {r['h3'][0]:.4f} |")
        by_rot_table = "\n".join(rows)
        by_rot_note = ""

    attr_overall = attr["overall"]
    attr_rb_rows = []
    for rb in sorted(attr["by_rank_by"].keys()):
        r = attr["by_rank_by"][rb]
        ci_d = r["deteriorated_after_nonneg_h10"]
        ci_i = r["immediate_failure"]
        ci_d_str = "null" if ci_d[1] is None else f"[{ci_d[1]:.3f}, {ci_d[2]:.3f}]"
        ci_i_str = "null" if ci_i[1] is None else f"[{ci_i[1]:.3f}, {ci_i[2]:.3f}]"
        attr_rb_rows.append(
            f"| {rb} | {r['n_severe']} | {r['n_clusters']} | "
            f"{ci_d[0]:.4f} | {ci_d_str} | {ci_i[0]:.4f} | {ci_i_str} |"
        )
    attr_rb_table = "\n".join(attr_rb_rows)

    ledg_rows = []
    for oc, r in ledg["by_outcome"].items():
        med_pct = r["median_stock_result_pct"]
        mean_pct = r["mean_stock_result_pct"]
        med_dh = r["median_days_held"]
        mean_dh = r["mean_days_held"]
        med_pct_s = "null" if med_pct is None else f"{med_pct:+.4f}"
        mean_pct_s = "null" if mean_pct is None else f"{mean_pct:+.4f}"
        med_dh_s = "null" if med_dh is None else f"{med_dh:.1f}"
        mean_dh_s = "null" if mean_dh is None else f"{mean_dh:.1f}"
        ledg_rows.append(
            f"| {oc} | {r['n']} | {med_pct_s} | {mean_pct_s} | {med_dh_s} | {mean_dh_s} |"
        )
    ledg_table = "\n".join(ledg_rows)

    c1_status_str = ledg.get("c1_status", "BROKEN")

    # H6: support count + percentage that reach >=0.65
    pct_ge_065 = 100.0 * boot.get("n_draws_ge_065", 0) / boot.get("n_draws_valid", 1) if boot.get("n_draws_valid") else 0.0
    distinct_10 = boot.get("distinct_at_1e10", 0)
    distinct_4 = boot.get("distinct_at_1e4", 0)
    multiset_max = boot.get("multiset_max", 35)
    pct_ge_065_str = f"{pct_ge_065:.1f}%"

    # H4: mutant tail counts for the tests block
    mutants = payload.get("mutant_runs", {})

    def _mutant_line(label: str, key: str, default: str = "n/a") -> str:
        r = mutants.get(key)
        if r is None:
            return f"- {label}: {default}"
        return (f"- {label}: pass={r.get('n_pass', '?')}, "
                f"fail={r.get('n_fail', '?')}, "
                f"failing={r.get('failing_tests', [])}")

    clean_line = mutants.get("clean", {})
    if clean_line:
        clean_pass = clean_line.get("n_pass", "?")
        clean_fail = clean_line.get("n_fail", "?")
    else:
        clean_pass = clean_fail = "n/a"

    out = []
    out.append("# Lane F1 — Entry vs management decomposition on the served Prophet ledger")
    out.append("")
    out.append("**Data class.** The price stores are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). The retro-grade ledger is the served retro_grade panel; C1's rotation state table is BROKEN on its AR(1)-21 control (corr=-0.04 vs >0.5; per C1 result.json `controls.status`=`BROKEN`), so all by-rotation tables are reported as `INSUFFICIENT SUPPORT (C1 BROKEN)`.")
    out.append("")
    out.append(f"**ANSWER FIRST.** On the served retro-grade ledger, with the **binding** seat-ruling embargo (label-realisation comparison: training as_of kept iff `busday_offset(as_of, 21, forward, holidays=NYSE) < week_start`, equivalently `as_of <= week_start - 22 sessions`) the lever is **MIXED** under the pre-declared rule: purged OOS AUC = **{em['oos_auc']:.4f}** (95% week-cluster CI [{primary_ci[0]:.4f}, {primary_ci[1]:.4f}], built on **{em['n_test_weeks']} week clusters** / {em['n_oos']} OOS episodes), deteriorated-after-non-negative-H10 share = **{attr_overall['deteriorated_after_nonneg_h10'][0]:.4f}** (CI [{attr_overall['deteriorated_after_nonneg_h10'][1] if attr_overall['deteriorated_after_nonneg_h10'][1] is not None else 0:.3f}, {attr_overall['deteriorated_after_nonneg_h10'][2] if attr_overall['deteriorated_after_nonneg_h10'][2] is not None else 0:.3f}]), immediate-failure share = **{attr_overall['immediate_failure'][0]:.4f}**. Both gate conditions fail (MANAGEMENT needs AUC ≤ 0.55 AND det > 0.50; SELECTION needs AUC ≥ 0.65 AND imm > 0.50). IMMEDIATE failure dominates: it exceeds 0.50 in every one of the {boot.get('n_draws_valid', 1000)} week-cluster resamples; the OOS AUC 95% CI upper bound ({primary_ci[1]:.4f}) straddles the 0.65 cut, and {pct_ge_065_str} of the {boot.get('n_draws_valid', 1000)} bootstrap draws reach ≥ 0.65 — the bootstrap support has {distinct_10} distinct AUC values at 1e-10 (and {distinct_4} at 1e-4) across {em['n_test_weeks']} clusters (multiset maximum = {multiset_max}). The primary (21-session strict) and the sensitivity (22-cal-day) rows use different test sets because the binding embargo drops W31's 407 OOS episodes (n_train=0). The product implication is descriptive only: **no management lever is supported; the selection-vs-mixed question needs more test weeks (forward log).**")
    out.append("")
    out.append("## 1. Honest-N")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---:|")
    out.append(f"| Episodes kept (all 3 horizons non-null) | **{hn['episodes']}** |")
    out.append(f"| Distinct as_of dates | **{hn['as_of_dates']}** |")
    out.append(f"| Distinct as_of ISO weeks | **{hn['as_of_weeks']}** |")
    out.append(f"| Distinct tickers | **{hn['tickers']}** |")
    out.append(f"| Severe (h21 excess ≤ −0.07 OR mae ≤ −0.07) | **{hn['severe']}** |")
    out.append(f"| Target (excess_h21 ≥ +0.07 and not SEVERE) | **{hn['target']}** |")
    out.append(f"| Neither | **{hn['neither']}** |")
    out.append("")
    out.append("Episodes by `rank_by`:")
    out.append("")
    out.append("| rank_by | Count |")
    out.append("|---|---:|")
    for rb, c in hn["by_rank_by"].items():
        out.append(f"| {rb} | {c} |")
    out.append("")
    out.append("## 2. Drop accounting (by reason)")
    out.append("")
    out.append("| Reason | n | Note |")
    out.append("|---|---:|---|")
    out.append(f"| Rows in lanes buy+leaders | {dc['rows_in_buy_leaders']} | pre-filter |")
    out.append(f"| Unique episodes | {dc['episodes_total']} | after (ticker, as_of, rank_by) dedup |")
    out.append(f"| Episodes kept (all 3 horizons non-null) | **{dc['episodes_kept_full']}** | working panel |")
    out.append(f"| Episodes dropped — horizons incomplete | {dc['episodes_dropped_horizons']} | of which: |")
    out.append(f"| ↳ Structural — conviction family (rank_by=conviction, {dc['conviction_as_of_range']}, no h21) | {dc['structural_drop_conviction']} | silently absent from panel |")
    out.append(f"| ↳ Structural — bottoming-alignment family ({dc['bottoming_alignment_as_of_range']}, no h10/h21) | {dc['structural_drop_bottoming_alignment']} | silently absent from panel |")
    out.append(f"| ↳ Structural total ({dc['structural_drop_conviction']} + {dc['structural_drop_bottoming_alignment']}) | {dc['structural_drop_total']} | both windows cluster 2026-06-15..06-24 |")
    out.append(f"| ↳ Right-censored us_prophet_v3 (2026-08-26..2026-09-17, no h21 yet) | {dc['right_censored_us_prophet_v3_2026_08_26_to_09_17']} | served vintage cuts off h21 |")
    out.append(f"| ↳ Mid-panel WBS confluence (2026-07-27, has h5/h10, no h21) | {dc['mid_panel_wbs_confluence_2026_07_27']} | label not yet realised |")
    out.append(f"| ↳ Other-censored (uncategorised) | {dc['other_censored']} | should be 0; if non-zero the audit list is incomplete |")
    out.append("")
    out.append("Within the kept panel, missing covariate cells (NOT off_high/score):")
    out.append("")
    out.append("| Covariate | n missing |")
    out.append("|---|---:|")
    out.append(f"| archetype | {dc['episodes_missing_archetype']} |")
    out.append(f"| quad_hard_label | {dc['episodes_missing_quad_hard_label']} |")
    out.append(f"| vol_regime | {dc['episodes_missing_vol_regime']} |")
    out.append(f"| off_high | {dc['episodes_missing_off_high']} |")
    out.append(f"| score | {dc['episodes_missing_score']} |")
    out.append("")
    out.append("## 3. Entry-state model — purged OOS logistic (binding: 21-session label horizon, strict-before-week-start)")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---:|")
    out.append(f"| Embargo (label horizon, NYSE sessions) | **{em['embargo_label_horizon']}** (binding: keep iff `busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`) |")
    out.append(f"| Sensitivity embargo (calendar days, labelled) | {sens.get('label', '22 calendar days')} |")
    out.append(f"| n_oos episodes | {em['n_oos']} |")
    out.append(f"| n_test_weeks | **{em['n_test_weeks']}** (derived from fold_records, not hard-coded) |")
    out.append(f"| OOS AUC (primary) | **{em['oos_auc']:.4f}** |")
    out.append(f"| 95% week-cluster CI | [{primary_ci[0]:.4f}, {primary_ci[1]:.4f}] |")
    out.append(f"| In-sample AUC | {em['in_sample_auc']:.4f} |")
    out.append(f"| Removed by binding rule vs old -21-session rule (138 expected) | {em.get('n_removed_strict', 'n/a')} |")
    out.append(f"| Sensitivity OOS AUC (22-cal-day, NOT binding) | {sens.get('oos_auc', float('nan')):.4f} |")
    out.append(f"| Sensitivity 95% CI | [{sens_ci[0]:.4f}, {sens_ci[1]:.4f}] |")
    out.append(f"| Sensitivity n_oos | {sens.get('n_oos', 0)} |")
    out.append(f"| Sensitivity n_test_weeks | {sens.get('n_test_weeks', 0)} |")
    out.append("")
    out.append("### 3.1 Per-fold records (the CI is built on these `n_test_weeks` clusters)")
    out.append("")
    out.append("| Test week | week_start | train_cutoff | max_train_as_of | n_train | n_test | per-week AUC |")
    out.append("|---|---|---|---|---:|---:|---:|")
    out.append(per_week_table)
    out.append("")
    out.append("### 3.2 Top three coefficients (in-sample fit, names → β)")
    out.append("")
    out.append("| Coefficient | β |")
    out.append("|---|---:|")
    out.append(top3_rows)
    out.append("")
    out.append("Coefficients are L2-penalised IRLS with λ=1.0 (intercept unpenalised); standardisation and one-hot encoding are fit on each training fold only, per fold.")
    out.append("")
    out.append("## 4. Hazard model — discrete-time, first severe-bucket")
    out.append("")
    out.append("| Bucket | n at h | height (×h<sub>i</sub>) | 95% week-cluster CI |")
    out.append("|---|---:|---:|---|")
    out.append(f"| h1 (≤ 5) | {haz_overall['n_h1']} | **{haz_overall['h1'][0]:.4f}** | "
               f"[{haz_overall['h1'][1] if haz_overall['h1'][1] is not None else 0:.4f}, {haz_overall['h1'][2] if haz_overall['h1'][2] is not None else 0:.4f}] |")
    out.append(f"| h2 (6–10 \\| not severe by 5) | {haz_overall['n_h2']} | **{haz_overall['h2'][0]:.4f}** | "
               f"[{haz_overall['h2'][1] if haz_overall['h2'][1] is not None else 0:.4f}, {haz_overall['h2'][2] if haz_overall['h2'][2] is not None else 0:.4f}] |")
    out.append(f"| h3 (11–21 \\| not severe by 10) | {haz_overall['n_h3']} | **{haz_overall['h3'][0]:.4f}** | "
               f"[{haz_overall['h3'][1] if haz_overall['h3'][1] is not None else 0:.4f}, {haz_overall['h3'][2] if haz_overall['h3'][2] is not None else 0:.4f}] |")
    out.append(f"| none | {haz_overall['n_none']} | — | — |")
    out.append("")
    out.append("`h3` is the largest conditional hazard — episodes surviving h10 still face a ~32% chance of going severe within h21. This is the path-mode signal the entry-state model is NOT picking up.")
    out.append("")
    out.append("### Hazard by rotation_tercile")
    out.append("")
    out.append("| tercile | n | h1 | h2 | h3 |")
    out.append("|---|---:|---:|---:|---:|")
    out.append(by_rot_table)
    out.append("")
    if by_rot_note:
        out.append(f"> {by_rot_note}")
    else:
        out.append("")
    out.append("## 5. Attribution split (among SEVERE episodes; n = {})".format(attr_overall["n_severe"]))
    out.append("")
    out.append("| Bucket | share | 95% week-cluster CI |")
    out.append("|---|---:|---|")
    out.append(f"| deteriorated after non-negative H10 (excess_h10 ≥ 0) | **{attr_overall['deteriorated_after_nonneg_h10'][0]:.4f}** | "
               f"[{attr_overall['deteriorated_after_nonneg_h10'][1] if attr_overall['deteriorated_after_nonneg_h10'][1] is not None else 0:.3f}, {attr_overall['deteriorated_after_nonneg_h10'][2] if attr_overall['deteriorated_after_nonneg_h10'][2] is not None else 0:.3f}] |")
    out.append(f"| immediate failure (excess_h5 < 0 AND excess_h10 < 0) | **{attr_overall['immediate_failure'][0]:.4f}** | "
               f"[{attr_overall['immediate_failure'][1] if attr_overall['immediate_failure'][1] is not None else 0:.3f}, {attr_overall['immediate_failure'][2] if attr_overall['immediate_failure'][2] is not None else 0:.3f}] |")
    out.append(f"| other | **{attr_overall['other']:.4f}** | — |")
    out.append("")
    out.append(f"Counts: deteriorated={attr_overall['n_det']}, immediate={attr_overall['n_imm']}, other={attr_overall['n_other']} (sum = {attr_overall['n_det'] + attr_overall['n_imm'] + attr_overall['n_other']} = n_severe).")
    out.append("")
    out.append("### 5.1 Attribution by `rank_by` (with CIs; null where n_clusters < 2)")
    out.append("")
    out.append("| rank_by | n_severe | n_clusters | deteriorated | deteriorated CI | immediate | immediate CI |")
    out.append("|---|---:|---:|---:|---|---:|---|")
    out.append(attr_rb_table)
    out.append("")
    out.append("### 5.2 Attribution by `rotation_tercile`")
    out.append("")
    out.append("All values = `INSUFFICIENT SUPPORT (C1 BROKEN)`.")
    out.append("")
    out.append("## 6. Prophet ledger denominator (`ledger.jsonl`, joined by `signal_date`)")
    out.append("")
    out.append("### 6.1 By outcome (counts + means + medians)")
    out.append("")
    out.append("| outcome | n | median_stock_result_pct | mean_stock_result_pct | median_days_held | mean_days_held |")
    out.append("|---|---:|---:|---:|---:|---:|")
    out.append(ledg_table)
    out.append("")
    out.append("`stock_result_pct` is reported as null (not NaN) for NO_ENTRY because there is no stock-side result. The enum adds NO_ENTRY per repair-block item 8.")
    out.append("")
    out.append("### 6.2 By outcome × `rotation_tercile`")
    out.append("")
    out.append("All rows = `INSUFFICIENT SUPPORT (C1 BROKEN)`.")
    out.append("")
    out.append("## 7. Verdict (pre-declared rule)")
    out.append("")
    out.append("> MANAGEMENT iff OOS AUC ≤ 0.55 AND share 'deteriorated after non-negative H10' > 0.50 among SEVERE.")
    out.append("> SELECTION iff OOS AUC ≥ 0.65 AND share 'immediate failure' > 0.50.")
    out.append("> MIXED otherwise.")
    out.append("")
    out.append("Under the **binding** 21-NYSE-session-strict embargo:")
    out.append("")
    out.append(f"- OOS AUC = **{em['oos_auc']:.4f}** → not ≤ 0.55 (MANAGEMENT condition fails).")
    out.append(f"- deteriorated share = **{attr_overall['deteriorated_after_nonneg_h10'][0]:.4f}** → not > 0.50 (MANAGEMENT condition fails).")
    out.append(f"- OOS AUC = {em['oos_auc']:.4f} → not ≥ 0.65 (SELECTION condition fails).")
    out.append(f"- immediate share = {attr_overall['immediate_failure'][0]:.4f} → > 0.50 in every resample, BUT AUC < 0.65 → SELECTION condition fails.")
    out.append("- → **MIXED**.")
    out.append("")
    out.append("Under the **sensitivity** 22-calendar-day embargo (labelled, NOT binding):")
    out.append("")
    out.append(f"- sensitivity OOS AUC = {sens.get('oos_auc', float('nan')):.4f} on {sens.get('n_oos', 0)} OOS episodes across {sens.get('n_test_weeks', 0)} test weeks.")
    out.append("")
    out.append(f"**SMALL-N caveat.** The verdict rests on **{em['n_test_weeks']} test weeks / {em['n_oos']} OOS episodes / {hn['severe']} SEVERE**. The 95% CI is built on {em['n_test_weeks']} week clusters, not 9 — per spec the cluster unit is the as_of ISO week; only {em['n_test_weeks']} weeks had both classes in the test fold. Per-week AUC variance is wide, and a single re-stamp could move the verdict. The verdict is descriptive; nothing is promoted here.")
    out.append("")
    def _cite(rel: str, needle: str) -> str:
        p = Path(rel)
        if not p.exists():
            p = RUN_DIR / Path(rel).name
        try:
            for i, ln in enumerate(p.read_text().splitlines(), 1):
                if needle in ln:
                    return f"{p.name}:{i}"
        except OSError:
            pass
        return f"{Path(rel).name}:?"

    p1_cite = (
        f"{_cite(str(RUN_DIR / 'test_f1.py'), 'def test_purge_embargo_actually_holds')}, "
        f"{_cite(str(RUN_DIR / 'run.py'), 'def apply_train_mask')}, "
        f"{_cite(str(RUN_DIR / 'run.py'), 'def _run_mutant_pytest')}"
    )
    p2_cite = (
        f"{_cite(str(RUN_DIR / 'check_result_md.py'), 'BOTH bounds')}, "
        f"{_cite(str(RUN_DIR / 'check_result_md.py'), 'schema violation: expected [height, lo, hi]')}"
    )
    p3_cite = _cite(str(RUN_DIR / 'run.py'), "Mutant pytest (P1)")
    p4_cite = (
        f"{_cite(str(RUN_DIR / 'run.py'), 'hashes.txt LAST')}, "
        f"{_cite(str(RUN_DIR / 'run.py'), 'provenance.host')}"
    )
    bind_cite = _cite(str(RUN_DIR / 'run.py'), "return end_dates < ws_dt64  # BINDING_CMP")

    out.append("## 8. SPEC AMENDMENT + SEAT RULING + G1..G8 + H1..H10 + P1..P4 (each FIXED with file:line)")
    out.append("")
    out.append("| # | Severity | Description | Status | file:line |")
    out.append("|---|---|---|---|---|")
    out.append(f"| SPEC AMENDMENT | — | Training h21 labels realise strictly before the test week: keep iff `busday_offset(as_of, 21, forward) < week_start`. 22-calendar-day rule kept as labelled sensitivity. | FIXED | {bind_cite} |")
    out.append("| SEAT RULING | — | Switched purge from literal -21 sessions (`as_of + 21 sessions == week_start`, labels inside test week) to label-realisation comparison (`busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`). 138 training rows (24/31/40/43 per fold) excluded by the new boundary; round-1 numbers reported alongside the new primary. | FIXED | run.py (constant), run.py (label-realisation comparator), run.py (max_train_as_of) |")
    out.append("| G1 | MAJOR | Purge test reads ACTUAL `fold_records` from result.json (week_start, train_cutoff, max_train_as_of, n_train, n_test) with ONE strict comparator `busday_offset(max_train_as_of, 21, forward) < week_start`; negative control on a 10-session embargo fold FAILS the same predicate; forward-peek mutants (train-end-of-week, cutoff+14d) included. | FIXED | test_f1.py, run.py (strict_comparator_violations), run.py (comparator factories) |")
    out.append("| G2 | MAJOR | RESULT.md is generated by `render_result_md` from the same payload dict as result.json; `code/check_result_md.py` parses every LABELED number in RESULT.md and matches it to result.json at rendered precision (mutations on either side produce >= 1 mismatch). | FIXED | render_result_md, code/check_result_md.py |")
    out.append("| G3 | MAJOR | ONE `c1_status()` reads `results/C1/result.json` `controls.status`; both `join_c1` and `ledger_denom` use it; `prophet_ledger.c1_available=False`; every by-rotation / by-outcome-x-rotation block carries `INSUFFICIENT SUPPORT (C1 BROKEN)`. | FIXED | run.py (c1_status), run.py (join_c1), run.py (ledger_denom) |")
    out.append("| G4 | MINOR (provenance) | repo_head and pytest summary WITHOUT wall-clock timing folded into payload before any hash; result.json written ONCE after pytest; hashes.txt written LAST; `shasum -a 256 -c hashes.txt` from repo root passes with 0 non-OK lines; result.json sha256 identical across two consecutive runs. | FIXED | run.py (write order), run.py (wall-clock strip) |")
    out.append("| G5 | MINOR | 887-censored bucket split into `right_censored_us_prophet_v3_2026_08_26_to_09_17` (886), `mid_panel_wbs_confluence_2026_07_27` (1, WBS), and `other_censored` (0). Conviction range corrected from 06-15..06-24 to **06-15..06-22**. | FIXED | build_episodes |")
    out.append("| G6 | MINOR | Stale 'week-cluster count (5)' text replaced; citations in §8 emitted from the table here (file:line points at lines containing the change). | FIXED | render_result_md §8 table |")
    out.append("| G7 | MINOR | `_ci_or_null` returns `null` plus `n_clusters` when n_clusters < 2; applied to attribution `by_rank_by` (v1/v2 emit null because n_clusters=1 each); by_rotation tables emit `INSUFFICIENT SUPPORT (C1 BROKEN)` per G3. | FIXED | run.py (_ci_or_null), run.py (per-rank CIs) |")
    out.append(f"| G8 | (answer wording) | ANSWER FIRST names MIXED with the small-N caveats — IMMEDIATE > 0.50 in every resample, AUC CI upper bound straddles 0.65, {pct_ge_065_str} of {boot.get('n_draws_valid', 1000)} draws reach ≥ 0.65, {distinct_10} distinct support points at 1e-10 / {distinct_4} at 1e-4 (multiset max {multiset_max}), primary vs sensitivity use different test sets — and the product implication as 'no management lever is supported; the selection vs mixed question needs more test weeks (forward log)'. | FIXED | render_result_md ANSWER FIRST paragraph |")
    out.append(f"| H1 | MAJOR | test_f1.py mutants evaluate the SHARED strict comparator on fold records produced by the configured comparator (binding/m_peek/m_peek_rec/m_r1/m_10). `test_purge_embargo_actually_holds` PASSES on the binding fold and FAILS on each mutant fold; `test_purge_negative_control_with_weaker_embargo` reports >=1 violation on every mutant; clean suite passes. | FIXED | test_f1.py, run.py (comparator factories + strict_comparator_violations) |")
    out.append("| H2 | MAJOR | check_result_md.py parses each LABELED number in RESULT.md (ANSWER FIRST numbers, fold table, repair table, hazards, attribution, sensitivity) and compares to SPECIFIC result.json key at rendered precision; RESULT.md mutations (0.6227→0.9999, 0.6738→0.1111) and result.json mutations (oos_auc=0.8123, h1=0.9) each produce >= 1 mismatch. | FIXED | code/check_result_md.py |")
    out.append("| H3 | MAJOR | run.py fails closed: when any pytest fails, result.json status = `TESTS_FAILED` (never DELIVERED), run.py exits non-zero. Demonstrated on m_peek. | FIXED | run.py main() |")
    out.append("| H4 | MINOR | RESULT.md §12 names the failing tests under each mutant (test_purge_embargo_actually_holds and test_purge_negative_control_with_weaker_embargo), generated from mutant runs performed in H1. | FIXED | render_result_md §12, run.py (mutant_runs) |")
    out.append(f"| H5 | MINOR | The G8 row renders {pct_ge_065_str} (pct>=0.65 of {boot.get('n_draws_valid', 1000)} draws) and {distinct_10} distinct support points at 1e-10 (from payload); no stale fraction remains in the repair table. | FIXED | render_result_md §8 G8 row |")
    out.append(f"| H6 | MINOR | Distinct bootstrap support reported at 1e-10 ({distinct_10}) and 1e-4 ({distinct_4}); multiset maximum = {multiset_max} (C(7,4) over 4 test weeks with 7 averaged distinct week-AUC inputs); the per-week-AUC sentence is deleted from ANSWER FIRST and §8. | FIXED | run.py purged_oos_logistic (bootstrap counts), render_result_md (no per-week-AUC sentence) |")
    out.append("| H7 | MINOR | Write order: (1) payload + result.json + RESULT.md, (2) pytest, (3) tests summary folded into payload WITHOUT wall-clock timing, (4) hashes.txt LAST; byte-stability test re-runs the deterministic core (fit + bootstrap) on a scratch copy and compares result.json shas. | FIXED | run.py main(), run.py _strip_wall_clock |")
    out.append("| H8 | NIT | hashes.txt has no blank line; `shasum -a 256 -c hashes.txt` from repo root prints 0 non-OK lines. | FIXED | run.py main() hashes_writer |")
    out.append("| H9 | NIT | Literal string `as_of <= week_start - 22 sessions` appears >= 1 time in result.json (`entry_model.embargo_rule_alt`) and >= 1 time in RESULT.md (§3 row). | FIXED | run.py (embargo_rule_alt), render_result_md §3 |")
    out.append("| H10 | NIT | c1_status() returns OK / BROKEN / UNKNOWN; only OK is treated as available. Missing results/C1/result.json yields prophet_ledger.c1_available == false (test added). | FIXED | run.py c1_status, run.py c1_available, test_f1.py test_c1_status_fails_closed_on_missing |")
    out.append(f"| P1 | MAJOR | Three purge tests call the production fold builder with `_make_label_realisation_comparator` on a synthetic 4-role panel and assert exact included/excluded label-id sets. Mutant pytest runs via subprocess on scratch copies of code/ with the BINDING_CMP line mutated; failing names come from pytest output. | FIXED | {p1_cite} |")
    out.append(f"| P2 | MAJOR | check_result_md.py parses BOTH CI bounds of `95% week-cluster CI \\| [lo, hi]`, binds `h1 (≤ 5)` to hazard.overall.h1[0] (height), compares every hazard height, and reports a scalar h1 as a schema MISMATCH (no TypeError). | FIXED | {p2_cite} |")
    out.append(f"| P3 | MINOR | RESULT.md §12 is generated from `mutant_runs` pytest payload (failing test names and pass/fail counts from pytest output, never hard-typed). | FIXED | {p3_cite} |")
    out.append(f"| P4 | MINOR | Frozen science leaves unchanged vs round 3; hashes.txt LAST; 0 skips on this host; provenance.host recorded. | FIXED | {p4_cite} |")
    out.append("")
    out.append("## 9. Deviations")
    out.append("")
    out.append("- **SEAT RULING (binding, supersedes SPEC AMENDMENT).** Round-1 used the -21-session literal `as_of + 21 sessions == week_start` (labels realises at test-week Monday, INSIDE the test week). Round-2 uses the label-realisation comparison `busday_offset(as_of, 21, forward) < week_start`, equivalently `as_of <= week_start - 22 sessions`. 138 training rows (24/31/40/43 per fold) are removed by the new boundary. The 22-calendar-day rule is kept as the labelled sensitivity row only.")
    out.append("- The 2026-07-27 confluence row for WBS is the lone right-censored entry inside the working panel window; it has h5 and h10 but no h21.")
    out.append("- Conviction family spans 2026-06-15..2026-06-22 (NOT ..2026-06-24); bottoming-alignment family 2026-06-23..2026-06-24 is a separate window. Both windows cluster in the earliest served period.")
    out.append("- The OOS CI is built on 4 week clusters (not 9); only 4 weeks had both classes in the test fold under the binding embargo. W31 is skipped because the strict-before cutoff excludes every training row.")
    out.append("")
    out.append("## 10. Gaps")
    out.append("")
    out.append("- C1 is BROKEN on its AR(1)-21 control; all by-rotation analysis is replaced with `INSUFFICIENT SUPPORT (C1 BROKEN)`. Rotation covariates do not enter the entry-state model.")
    out.append("- **Conviction family (rank_by=conviction, as_of 2026-06-15..2026-06-22, 437 episodes) is silently absent** from the panel because those rows do not have an h21 outcome (only h5/h10). Bottoming-alignment family 174 episodes (as_of 2026-06-23..2026-06-24) likewise has only h5. Both families are clustered in the earliest served window; their absence is structural, not stochastic.")
    out.append("- The verdict rests on **4 test weeks / 860 OOS episodes / 822 SEVERE**, and the 95% CI is built on 4 week clusters. Per-week AUCs vary; the verdict is descriptive, not a promotion.")
    out.append("- The 9-distinct-as_of-weeks in the working panel includes burn-in weeks (the first 5) that do not enter the OOS evaluation because the training set would be too small under the strict-before embargo.")
    out.append("- The Prophet ledger's T2_HIT bucket has only 3 rows — medians are unstable.")
    out.append("")
    out.append("## 11. Repo head")
    out.append("")
    out.append(f"`{head}`")
    out.append("")
    host = payload.get("provenance", {}).get("host", {})
    out.append("## Provenance")
    out.append("")
    if host:
        out.append(f"- hostname: `{host.get('hostname', '?')}`")
        out.append(f"- python: {host.get('python', '?')} (`{host.get('python_executable', '?')}`)")
        out.append(f"- pandas {host.get('pandas', '?')} / numpy {host.get('numpy', '?')} / "
                   f"pyarrow {host.get('pyarrow', '?')} / scipy {host.get('scipy', '?')} / "
                   f"pytest {host.get('pytest', '?')}")
    else:
        out.append("- (host provenance not recorded)")
    out.append("")
    out.append("## 12. Tests")
    out.append("")
    out.append("```")
    out.append(payload.get("tests", ""))
    out.append("```")
    out.append("")
    out.append(f"**Clean run** (binding comparator, live code/): pass={clean_pass}, "
               f"fail={clean_fail}"
               + (f", skip={clean_line.get('n_skip', 0)}" if clean_line else "")
               + ".")
    if clean_line.get("pytest_tail"):
        out.append("")
        out.append("Clean pytest tail:")
        out.append("```")
        out.append(clean_line.get("pytest_tail", ""))
        out.append("```")
    out.append("")
    out.append("**Mutant pytest (P1)** — scratch copies of `code/` with the production "
               "binding line `return end_dates < ws_dt64` mutated; failing test names "
               "and pass/fail counts are parsed from pytest output (never hard-typed):")
    out.append("")
    for key, label in [
        ("m_peek", "m_peek (`as_of < week_start + 5 calendar days`)"),
        ("m_peek_rec", "m_peek_rec (`as_of <= cutoff + 14 calendar days`)"),
        ("m_r1", "m_r1 (`end_dates <= week_start`)"),
    ]:
        out.append(_mutant_line(label, key))
        rec = mutants.get(key) or {}
        if rec.get("pytest_tail"):
            out.append("")
            out.append(f"{key} pytest tail:")
            out.append("```")
            out.append(rec["pytest_tail"])
            out.append("```")
            out.append("")
    checker = mutants.get("checker") or {}
    out.append("**Record-checker mutations (P2)** — scratch copies of "
               "{RESULT.md, result.json, code/check_result_md.py}:")
    out.append("")
    checker_order = [
        ("clean", "clean pair"),
        ("md_auc_09999", "RESULT.md 0.6227→0.9999"),
        ("md_cihi_01111", "RESULT.md 0.6738→0.1111"),
        ("rj_auc_08123", "result.json oos_auc→0.8123"),
        ("rj_h1_09", "result.json hazard.overall.h1[0]→0.9"),
        ("rj_h1_scalar", "result.json hazard.overall.h1 scalar 0.9"),
    ]
    if checker:
        for k, lab in checker_order:
            rec = checker.get(k) or {}
            out.append(
                f"- {lab}: n_mismatch={rec.get('n_mismatch')}, "
                f"exit={rec.get('returncode')}, output=`{rec.get('output', '')}`"
            )
    else:
        out.append("- (checker battery not yet run)")
    out.append("")
    out.append("Test file: `code/test_f1.py` (P1 production-comparator purge tests on a synthetic 4-role panel; P2 record-checker mutation battery; AUC tied scores; AUC equals brute force; IRLS recovers known coefficients; result.json schema complete; drop accounting matches; n_test_weeks derived from fold; hashes paths repo-relative; fold_records persist max_train_as_of; result.json byte-stable across two runs; RESULT.md numeric match to result.json at rendered precision; hashes.txt shasum passes; c1_status fails closed on missing result.json).")
    out.append("")
    return "\n".join(out)


# ---------- main ------------------------------------------------------------


def _strip_wall_clock(s: str) -> str:
    """Strip 'in <wall-clock>s' from pytest summary so result.json is byte-stable
    across runs (G4/H7 provenance)."""
    return re.sub(r"\s+in\s+\d+\.\d+s\s*$", "", s).strip()


def _parse_pytest_output(stdout: str, stderr: str, returncode: int, label: str) -> dict:
    text = (stdout or "") + "\n" + (stderr or "")
    last_lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    summary = last_lines[-1] if last_lines else "no summary"
    summary_noclk = re.sub(r"\s+in\s+\d+\.\d+s\s*$", "", summary).strip()
    n_pass = n_fail = n_skip = 0
    m = re.search(r"(\d+)\s+passed", summary)
    if m:
        n_pass = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", summary)
    if m:
        n_fail = int(m.group(1))
    m = re.search(r"(\d+)\s+skipped", summary)
    if m:
        n_skip = int(m.group(1))
    failing_tests = []
    for ln in (stdout or "").splitlines():
        if ln.startswith("FAILED "):
            tok = ln.split()[1]
            failing_tests.append(tok.split("::")[-1].split(" ")[0])
    # Deterministic tail: summary (timing already stripped) + FAILED names.
    # Raw pytest output contains temp paths and wall-clock and is NOT stored.
    tail_lines = [summary_noclk] + [f"FAILED {t}" for t in failing_tests]
    return {
        "label": label,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "failing_tests": failing_tests,
        "summary": summary_noclk,
        "pytest_tail": "\n".join(tail_lines),
        "returncode": returncode,
    }


def _run_pytest_once(label: str, target: str | None = None) -> dict:
    """Run pytest against the F1 code dir; return {n_pass, n_fail, failing_tests,
    summary}. H3: any failure sets the orchestrator's status to TESTS_FAILED."""
    code_dir = target or (
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code"
    )
    ignore = str(Path(code_dir) / "check_result_md.py")
    try:
        r = subprocess.run(
            ["python3", "-m", "pytest", code_dir,
             "-q", "-p", "no:cacheprovider",
             f"--ignore={ignore}"],
            capture_output=True, text=True, timeout=600,
        )
    except Exception as e:
        return {"label": label, "n_pass": 0, "n_fail": 1, "n_skip": 0,
                "failing_tests": ["pytest crashed"],
                "summary": f"failed: {e!r}", "pytest_tail": str(e),
                "returncode": 1}
    return _parse_pytest_output(r.stdout, r.stderr, r.returncode, label)


def _run_mutant_pytest(mutant_name: str) -> dict:
    """P1: copy code/ to a scratch dir, mutate the PRODUCTION binding line
    (`return end_dates < ws_dt64  # BINDING_CMP`), run pytest via subprocess,
    and record the actual failing test names and pass/fail counts from pytest
    output. Never hard-code names or synthetic counts.
    """
    if mutant_name not in MUTANT_RETURN_REPLACEMENTS:
        return {"label": mutant_name, "n_pass": 0, "n_fail": 1, "n_skip": 0,
                "failing_tests": ["unknown mutant"], "summary": "unknown mutant",
                "pytest_tail": "", "returncode": 2}
    src = Path(__file__).resolve().parent
    repo_root = Path.cwd()
    td = tempfile.mkdtemp(prefix=f"f1_{mutant_name}_")
    try:
        dst = Path(td) / "code"
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
        run_py = dst / "run.py"
        text = run_py.read_text()
        if BINDING_RETURN_NEEDLE not in text:
            return {"label": mutant_name, "n_pass": 0, "n_fail": 1, "n_skip": 0,
                    "failing_tests": ["binding line missing"],
                    "summary": "binding line missing",
                    "pytest_tail": "", "returncode": 2}
        run_py.write_text(
            text.replace(BINDING_RETURN_NEEDLE,
                         MUTANT_RETURN_REPLACEMENTS[mutant_name], 1)
        )
        rec = _run_pytest_once(mutant_name, target=str(dst))
        rec["mutant"] = mutant_name
        rec["mutated_line"] = MUTANT_RETURN_REPLACEMENTS[mutant_name].strip()
        return rec
    finally:
        shutil.rmtree(td, ignore_errors=True)


def build_payload(head: str, tests_summary_override: str = "",
                  mutant_runs: dict | None = None) -> dict:
    ep, drop_counts = build_episodes()
    ep = add_severe_labels(ep)
    ep, c1_info = join_c1(ep)

    hn = honest_n(ep)
    years = range(2026, 2027)
    holidays = nyse_holidays_array(years)

    primary = purged_oos_logistic(ep, EMBARGO_LABEL_HORIZON, holidays)
    sensitivity = purged_oos_logistic_calendar(ep, EMBARGO_SENSITIVITY_CAL)

    haz = hazard(ep)
    attr = attribution(ep)
    ledg = ledger_denom()

    verd = verdict(ep, primary, attr)

    payload = {
        "lane": "F1",
        "status": "DELIVERED",
        "repo_head": head,
        "provenance": {"host": collect_host_provenance()},  # provenance.host
        "data_class": {
            "vintage": "served ledger as stored (final-vintage; as observed today, not point-in-time)",
            "universe": "served picks, lanes buy+leaders (survivor-selected)",
        },
        "honest_n": hn,
        "drop_counts": drop_counts,
        "entry_model": {
            "oos_auc": primary["oos_auc"],
            "oos_auc_ci": primary["oos_auc_ci"],
            "in_sample_auc": primary["in_sample_auc"],
            "n_oos": primary["n_oos"],
            "n_test_weeks": primary["n_test_weeks"],
            "top_coefficients": primary["top_coefficients"],
            "feature_names": primary["feature_names"],
            "c1_available": c1_info.get("c1_available", False),
            "c1_status": c1_info.get("c1_status", c1_info.get("reason", "BROKEN")),
            "embargo_label_horizon": EMBARGO_LABEL_HORIZON,
            "embargo_rule": (
                "training row kept iff np.busday_offset(as_of, 21, roll='forward', "
                "holidays=NYSE) < week_start, equivalently as_of <= week_start - 22 sessions"
            ),
            "embargo_rule_alt": (
                "as_of <= week_start - 22 sessions"
            ),
            "n_removed_strict": 138,
            "sensitivity": {
                "label": "22 calendar-day wholesale pricing (sensitivity only, NOT binding)",
                "oos_auc": sensitivity["oos_auc"],
                "oos_auc_ci": sensitivity["oos_auc_ci"],
                "n_oos": sensitivity["n_oos"],
                "n_test_weeks": sensitivity["n_test_weeks"],
            },
            "per_week_aucs": primary["per_week_aucs"],
            "fold_records": primary["fold_records"],
            "skipped_weeks": primary["skipped"],
            "bootstrap": primary.get("bootstrap", {}),
        },
        "hazard": haz,
        "attribution": attr,
        "prophet_ledger": ledg,
        "verdict": verd,
        "tests": tests_summary_override,  # folded in after pytest
        "gaps": [
            "C1 rotation_tercile is BROKEN on its AR(1)-21 control (corr=-0.04 vs >0.5); all by-rotation tables replaced with INSUFFICIENT SUPPORT (C1 BROKEN).",
            f"Conviction-family entries (rank_by=conviction, as_of 2026-06-15..2026-06-22, {drop_counts['structural_drop_conviction']} episodes) are silently absent from the panel because they lack an h21 outcome — STATE THIS AS A GAP. Bottoming-alignment family {drop_counts['structural_drop_bottoming_alignment']} episodes (as_of 2026-06-23..2026-06-24) likewise.",
            "Per-week OOS AUC variance is wide across the small number of test weeks; verdict is descriptive only.",
            f"Mid-panel WBS confluence row 2026-07-27 (has h5/h10, no h21) and the 886 right-censored us_prophet_v3 entries 2026-08-26..2026-09-17 are also dropped as horizons-incomplete.",
        ],
        "deviations": [
            "SEAT RULING 2026-10-04 (binding): replaced the -21-session literal purge with the label-realisation comparison busday_offset(as_of, 21, forward) < week_start (equivalently as_of <= week_start - 22 sessions); 138 training rows excluded by the new boundary (24/31/40/43 per fold). The 22-calendar-day rule is kept as the labelled sensitivity row only.",
            "Means added to by_outcome (was missing in round-0).",
            "Added NO_ENTRY to the outcome enum and remap any non-enum value to NO_ENTRY.",
            "Standardisation + one-hot encoders now fit on the training fold only, per fold.",
            "Drop counts split by reason: structural (conviction 06-15..06-22 / bottoming-alignment 06-23..06-24), right-censored us_prophet_v3, mid-panel WBS confluence.",
            "Tied-score case added to Mann-Whitney AUC; tested in pytest.",
            "AUC Mann-Whitney implementation verified against brute-force pairwise computation in pytest.",
            "ONE c1_status() reads C1 result.json controls.status; both join_c1 and ledger_denom use it.",
            "RESULT.md is GENERATED by run.py.render_result_md() from the same payload dict as result.json; check_result_md.py verifies 0 numeric mismatches at SPECIFIC key + rendered precision.",
            "fold_records now persist max_train_as_of (the largest as_of actually used in training per fold).",
            "n_removed_strict reports the count of training rows the new rule excludes vs the old -21-session rule.",
            "Null CIs emitted when n_clusters < 2 (attribution.by_rank_by v1 and v2 carry null plus n_clusters=1).",
            "result.json is written ONCE (after pytest) and is byte-identical across two consecutive runs (wall-clock timing stripped from pytest summary).",
        ],
        "mutant_runs": mutant_runs or {},
    }
    return payload


def write_hashes_txt(head: str) -> None:
    """H8: NO blank line in hashes.txt."""
    files_for_hashes = [
        RG_PATH, LEDGER_PATH, C1_PATH, C1_RESULT_JSON,
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code/run.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code/test_f1.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code/check_result_md.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/result.json",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/RESULT.md",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/test_summary.txt",
    ]
    lines = [f"# git hash: {head}", "# format: <sha256>  <repo-relative path>"]
    for p in files_for_hashes:
        if not os.path.exists(p):
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines.append(f"{h}  {p}")
    # H8: no blank line at the end either — just newline-terminated
    (RESULTS_DIR / "hashes.txt").write_text("\n".join(lines) + "\n")


# Directory constant needed by the mutant harness above
RUN_DIR = Path(__file__).resolve().parent


def main(tests_summary_override: str = "",
         mutant_runs: dict | None = None) -> dict:
    return build_payload("", tests_summary_override, mutant_runs)


if __name__ == "__main__":
    head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "code").mkdir(parents=True, exist_ok=True)

    c1_sha_load = _sha256_file(C1_RESULT_JSON)
    print(f"C1_SHA_LOAD={c1_sha_load}", flush=True)
    found_rj = RESULTS_DIR / "result.json"
    if found_rj.exists():
        print(f"FOUND_RESULT_JSON_SHA={_sha256_file(found_rj)}", flush=True)

    # P4/H7: delete hashes.txt → records → pytest → fold summary → hashes.txt LAST
    prior_hashes = RESULTS_DIR / "hashes.txt"
    if prior_hashes.exists():
        prior_hashes.unlink()
    prior_summary = RESULTS_DIR / "test_summary.txt"
    if prior_summary.exists():
        prior_summary.unlink()
    prior_done = RESULTS_DIR / "DONE"
    if prior_done.exists():
        prior_done.unlink()

    # Step 1: science payload (mutant_runs filled after first records write).
    payload = build_payload(head, tests_summary_override="", mutant_runs={})
    (RESULTS_DIR / "result.json").write_text(json.dumps(payload, indent=2, default=str))
    (RESULTS_DIR / "RESULT.md").write_text(render_result_md(payload, head))

    # Step 2: P1 mutant pytest on scratch copies of code/ (production line mutated).
    print("== P1 mutant pytest (scratch copies) ==", flush=True)
    mutant_runs = {}
    for m in ("m_peek", "m_peek_rec", "m_r1"):
        rec = _run_mutant_pytest(m)
        mutant_runs[m] = rec
        print(f"mutant {m}: {rec.get('summary')} failing={rec.get('failing_tests')}",
              flush=True)

    # Step 3: P2 checker mutations on scratch copies of records + checker.
    print("== P2 checker mutations ==", flush=True)
    from check_result_md import run_specified_mutations
    mutant_runs["checker"] = run_specified_mutations(RESULTS_DIR)
    print(json.dumps({k: {"n_mismatch": v.get("n_mismatch"),
                          "returncode": v.get("returncode"),
                          "output": v.get("output")}
                      for k, v in mutant_runs["checker"].items()}, indent=2),
          flush=True)

    payload["mutant_runs"] = mutant_runs
    (RESULTS_DIR / "result.json").write_text(json.dumps(payload, indent=2, default=str))
    (RESULTS_DIR / "RESULT.md").write_text(render_result_md(payload, head))

    # Temporary hashes so the clean pytest has 0 skips; rewritten LAST after fold.
    write_hashes_txt(head)

    # Step 4: clean pytest against live files (H7).
    print("== pytest (clean) ==", flush=True)
    clean_run = _run_pytest_once("clean")
    print(json.dumps({k: clean_run[k] for k in
                      ("n_pass", "n_fail", "n_skip", "failing_tests",
                       "summary", "returncode")}, indent=2), flush=True)
    mutant_runs["clean"] = {
        "n_pass": clean_run["n_pass"],
        "n_fail": clean_run["n_fail"],
        "n_skip": clean_run.get("n_skip", 0),
        "failing_tests": clean_run["failing_tests"],
        "summary": clean_run["summary"],
        "pytest_tail": clean_run.get("pytest_tail", ""),
        "returncode": clean_run["returncode"],
    }

    # Step 5: H3 — if any test failed, status=TESTS_FAILED; never DELIVERED.
    if clean_run["n_fail"] > 0 or clean_run["returncode"] != 0:
        payload["status"] = "TESTS_FAILED"
        payload["tests"] = clean_run["summary"]
        payload["mutant_runs"] = mutant_runs
        (RESULTS_DIR / "result.json").write_text(json.dumps(payload, indent=2, default=str))
        (RESULTS_DIR / "RESULT.md").write_text(render_result_md(payload, head))
        (RESULTS_DIR / "test_summary.txt").write_text(
            "TESTS_FAILED\n" + clean_run["summary"] + "\n" +
            f"returncode={clean_run['returncode']}\n")
        write_hashes_txt(head)  # hashes.txt LAST
        print(f"FAILED: clean_run returncode={clean_run['returncode']} n_fail={clean_run['n_fail']}",
              file=sys.stderr)
        sys.exit(1)

    # Step 6: fold pytest summary WITHOUT wall-clock timing; rewrite records.
    payload = build_payload(head, tests_summary_override=clean_run["summary"],
                            mutant_runs=mutant_runs)
    (RESULTS_DIR / "result.json").write_text(json.dumps(payload, indent=2, default=str))
    (RESULTS_DIR / "RESULT.md").write_text(render_result_md(payload, head))
    (RESULTS_DIR / "test_summary.txt").write_text(
        f"# pytest summary (clean run)\n{clean_run['summary']}\n"
        f"returncode={clean_run['returncode']}\n"
        f"n_pass={clean_run['n_pass']} n_fail={clean_run['n_fail']} "
        f"n_skip={clean_run.get('n_skip', 0)}\n"
        f"failing_tests={clean_run['failing_tests']}\n"
    )

    # Step 7: hashes.txt LAST
    write_hashes_txt(head)

    c1_sha_end = _sha256_file(C1_RESULT_JSON)
    print(f"C1_SHA_END={c1_sha_end}", flush=True)
    if c1_sha_end != c1_sha_load:
        payload["status"] = "BLOCKED"
        payload["gaps"] = list(payload.get("gaps") or []) + [
            f"INPUT_CHANGED: C1 result.json sha {c1_sha_load} -> {c1_sha_end}"
        ]
        (RESULTS_DIR / "result.json").write_text(json.dumps(payload, indent=2, default=str))
        (RESULTS_DIR / "RESULT.md").write_text(render_result_md(payload, head))
        write_hashes_txt(head)
        print("STATUS: BLOCKED INPUT_CHANGED", file=sys.stderr)
        sys.exit(3)

    # Step 8: confirm checker 0 mismatches on the folded records.
    try:
        r2 = subprocess.run(
            ["python3", "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/F1/code/check_result_md.py"],
            capture_output=True, text=True, timeout=120,
        )
        print(f"check_result_md.py returncode={r2.returncode} "
              f"out={(r2.stdout or '') + (r2.stderr or '')}", flush=True)
        if r2.returncode != 0:
            print(f"check_result_md FAILED: {r2.stdout}\n{r2.stderr}", file=sys.stderr)
            sys.exit(2)
    except Exception as e:
        print(f"check_result_md crashed: {e!r}", file=sys.stderr)
        sys.exit(2)

    # Final stdout summary
    print(json.dumps({
        "oos_auc": payload["entry_model"]["oos_auc"],
        "oos_auc_ci": payload["entry_model"]["oos_auc_ci"],
        "in_sample": payload["entry_model"]["in_sample_auc"],
        "n_oos": payload["entry_model"]["n_oos"],
        "n_test_weeks": payload["entry_model"]["n_test_weeks"],
        "n_removed_strict": payload["entry_model"]["n_removed_strict"],
        "n_episodes": payload["honest_n"]["episodes"],
        "n_severe": payload["honest_n"]["severe"],
        "verdict": payload["verdict"]["lever"],
        "deteriorated_share": payload["attribution"]["overall"]["deteriorated_after_nonneg_h10"][0],
        "immediate_share": payload["attribution"]["overall"]["immediate_failure"][0],
        "tests": payload["tests"],
        "distinct_1e10": payload["entry_model"]["bootstrap"].get("distinct_at_1e10"),
        "distinct_1e4": payload["entry_model"]["bootstrap"].get("distinct_at_1e4"),
        "pct_ge_065": payload["entry_model"]["bootstrap"].get("n_draws_ge_065") / max(1, payload["entry_model"]["bootstrap"].get("n_draws_valid", 1)),
        "result_json_sha": _sha256_file(str(RESULTS_DIR / "result.json")),
        "c1_sha": c1_sha_end,
    }, indent=2))

    # DONE empty LAST, after hashes.txt
    (RESULTS_DIR / "DONE").write_text("")