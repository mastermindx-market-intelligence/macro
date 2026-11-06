"""s1_challenger.py — the ONE bounded IPCA-family challenger (D13, frozen).

"Restricted IPCA with one OBSERVED factor": beta_i(t) = z_i(t-1)' Gamma with
z = [1, mom_12_1, vol_63, rev_21]; f_t = SPY daily log return. Gamma (4
numbers) is pooled OLS (no intercept) of r_i,t on
[f_t, mom*f_t, vol*f_t, rev*f_t] over the TRAIN panel only (t < 2024-01-01).

Characteristics are point-in-time: computed from adjusted close bars strictly
before the date t (i.e. bars <= t-1), then cross-sectionally rank-standardised
per date to [-0.5, 0.5] across names with valid values. A date with < 30 valid
names is dropped.

Universe selection (sealed, outcome-free): schemas + index dates only.
Disclosed limits: survivorship (today's file set), ETFs mixed with single
names, no point-in-time membership.
"""
from __future__ import annotations

import hashlib
from bisect import bisect_left
from datetime import date

import numpy as np

UNIVERSE_DIR = "data/yahoo"
SKIP_BASENAMES = {"SPY.parquet", "KWEB.parquet", "BABA.parquet"}
UNIVERSE_START = date(2012, 1, 3)
UNIVERSE_END = date(2026, 9, 30)
MIN_FIRST_DATE = UNIVERSE_START      # first index date <= 2012-01-03
MIN_LAST_DATE = date(2026, 9, 30)    # last index date >= 2026-09-30
MIN_SESSION_COVERAGE = 0.95
MAX_ADMITTED = 150
MIN_XSEC = 30                        # drop a date with < 30 valid names
MIN_TRAIN_MONTHS = 60

CHAR_NAMES = ("mom_12_1", "vol_63", "rev_21")


def path_sort_key(path: str) -> str:
    """Ascending sha256(path) order (D13), hex digest."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def build_universe(store, blob_sha, nyse_sessions: list[date]) -> dict:
    """Outcome-free universe census (schemas + index dates ONLY)."""
    candidates = [p for p in store.list_dir(UNIVERSE_DIR + "/") if p.endswith(".parquet")]
    candidates.sort(key=path_sort_key)
    sessions = set(nyse_sessions)
    n_sessions = len(sessions)
    admitted: list[dict] = []
    rejected: dict[str, int] = {
        "no_adjusted_close_column": 0,
        "late_first_date": 0,
        "stale_last_date": 0,
        "low_session_coverage": 0,
        "skipped_benchmark_or_subject": 0,
        "cap_break_unclassified": 0,
    }
    examined = 0
    for path in candidates:
        examined += 1
        base = path.rsplit("/", 1)[-1]
        if base in SKIP_BASENAMES:
            rejected["skipped_benchmark_or_subject"] += 1
            continue
        if len(admitted) >= MAX_ADMITTED:
            rejected["cap_break_unclassified"] += 1
            break
        cols = store.schema(path)
        if "close" not in cols:
            rejected["no_adjusted_close_column"] += 1
            continue
        dates = store.index_dates(path)
        if not dates or dates[0] > MIN_FIRST_DATE:
            rejected["late_first_date"] += 1
            continue
        if dates[-1] < MIN_LAST_DATE:
            rejected["stale_last_date"] += 1
            continue
        cov = len(sessions.intersection(dates)) / n_sessions if n_sessions else 0.0
        if cov < MIN_SESSION_COVERAGE:
            rejected["low_session_coverage"] += 1
            continue
        admitted.append({
            "path": path,
            "blob_sha256": blob_sha(path),
            "first_index_date": dates[0].isoformat(),
            "last_index_date": dates[-1].isoformat(),
            "session_coverage": round(cov, 6),
        })
    return {
        "order": "ascending sha256(path)",
        "criteria": {
            "adjusted_close_column": "close",
            "first_index_date_lte": MIN_FIRST_DATE.isoformat(),
            "last_index_date_gte": MIN_LAST_DATE.isoformat(),
            "min_nyse_session_coverage": MIN_SESSION_COVERAGE,
            "session_window": [UNIVERSE_START.isoformat(), UNIVERSE_END.isoformat()],
            "skipped": sorted(SKIP_BASENAMES),
            "max_admitted": MAX_ADMITTED,
        },
        "files_examined": examined,
        "rejected_by_reason": rejected,
        "admitted_count": len(admitted),
        "admitted": admitted,
        "disclosures": [
            "survivorship: today's file set at the pinned ref; no point-in-time membership",
            "non-single-names admitted by the frozen criteria: ETFs, ETNs and FX pairs "
            "(e.g. USDBRL_X) are mixed with single names",
            "the frozen admission criteria are schema- and index-date-only and are not "
            "re-tuned after outcomes",
        ],
    }


def characteristics_at(dates: list[date], closes: list[float], t: date) -> dict | None:
    """mom_12_1 / vol_63 / rev_21 from bars STRICTLY before t (bars <= t-1).

    Bar-position indexing on the name's own bar series:
      P[t-1] = last bar before t, P[t-22] = 22nd bar before t, P[t-253] = 253rd.
    None unless at least 253 bars exist before t (vol_63 needs 64 of them and
    is dominated by the momentum requirement).
    """
    j = bisect_left(dates, t)              # bars strictly before t: 0..j-1
    if j < 253:
        return None
    p1 = closes[j - 1]
    p22 = closes[j - 22]
    p253 = closes[j - 253]
    if p1 <= 0 or p22 <= 0 or p253 <= 0:
        return None
    mom = float(np.log(p22 / p253))
    rev = float(np.log(p1 / p22))
    seg = np.asarray(closes[j - 64:j], dtype=float)
    lr = np.diff(np.log(seg))
    vol = float(np.std(lr, ddof=1))
    if vol != vol or mom != mom or rev != rev:
        return None
    return {"mom_12_1": mom, "vol_63": vol, "rev_21": rev}


def rank_standardise(values: dict[str, float]) -> dict[str, float]:
    """Cross-sectional rank map to [-0.5, 0.5]: (rank-1)/(count-1) - 0.5.
    Deterministic: ties broken by name order (float ties are not expected)."""
    names = sorted(values)
    n = len(names)
    if n < 2:
        return {k: 0.0 for k in names}
    order = sorted(names, key=lambda k: values[k])
    rank = {k: i + 1 for i, k in enumerate(order)}
    return {k: (rank[k] - 1) / (n - 1) - 0.5 for k in names}


def gamma_design(y: float, f: float, z: dict[str, float]) -> list[float]:
    """[f_t, mom*f_t, vol*f_t, rev*f_t] — no intercept (frozen)."""
    return [f, z["mom_12_1"] * f, z["vol_63"] * f, z["rev_21"] * f]


def fit_gamma(rows: list[dict]) -> np.ndarray:
    """Pooled OLS, no intercept, of r on the interaction design. rows carry
    y (r_i,t), f (f_t) and z (standardised characteristics)."""
    X = np.asarray([gamma_design(r["y"], r["f"], r["z"]) for r in rows])
    yv = np.asarray([r["y"] for r in rows])
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    return coef


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def estimability(universe: dict, train_months: dict[str, int]) -> dict:
    """Sealed thresholds: >= 30 admitted names, 3 characteristics, >= 60
    distinct TRAIN months with a valid cross-section."""
    n_names = int(universe["admitted_count"])
    n_char = len(CHAR_NAMES)
    n_months = len(train_months)
    checks = {
        "admitted_names_ge_30": n_names >= 30,
        "characteristics_eq_3": n_char == 3,
        "train_months_ge_60": n_months >= MIN_TRAIN_MONTHS,
    }
    return {
        "admitted_names": n_names,
        "characteristics": n_char,
        "train_months_with_valid_cross_section": n_months,
        "thresholds": {"min_admitted_names": 30, "n_characteristics": 3,
                       "min_train_months": MIN_TRAIN_MONTHS},
        "checks": checks,
        "estimable": all(checks.values()),
    }
