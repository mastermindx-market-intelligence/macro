"""s1_decomposition.py — P03 contemporaneous factor decomposition (D8).

CONTEMPORANEOUS ONLY. This is a historical-descriptive account of how much of
an observed window return a transparent market/sector factor baseline carries;
it is never a pre-move forecast and supports no direction.

Decision-cutoff quantities (fitted on bars <= D(s) only) carry the `__dc`
suffix; observation-cutoff quantities (the window itself, fill -> coverage)
carry `__oc`. The two are never mixed in one name (masterplan §5.3 via REG P03).

Window return rule cites engine/qledger.py `_leg_ret_in_window` (L2540): the
entry bar must sit ON `fill_date`, the exit bar ON `coverage_date`; a shortened
window is refused (None), never graded. Here both endpoints are log returns on
the adjusted (total-return) close.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

import numpy as np

WINDOW = 252
MIN_OBS = 200

MODEL_FACTORS = {
    "M0": [],
    "M1": None,   # filled per market by the caller: US ["SPY"], HK ["2800.HK"]
    "M2": None,   # US ["SPY","KWEB"], HK ["2800.HK","3033.HK"]
}
MARKET_FACTORS = {
    "US": {"M1": ["SPY"], "M2": ["SPY", "KWEB"]},
    "HK": {"M1": ["2800.HK"], "M2": ["2800.HK", "3033.HK"]},
}

# Abstention states (D8).
OK = "OK"
ABSTAIN_INSUFFICIENT_HISTORY = "ABSTAIN_INSUFFICIENT_HISTORY"
ABSTAIN_MISSING_ENDPOINT = "ABSTAIN_MISSING_ENDPOINT"
ABSTAIN_RESOLVER_NONE = "ABSTAIN_RESOLVER_NONE"
ABSTAIN_FILL_MISMATCH = "ABSTAIN_FILL_MISMATCH"
PURGED = "PURGED"
QUARANTINE = "QUARANTINE"


def spec_hash(model: str, subject_security_id: str, factors: list[str], h: int) -> str:
    spec = {
        "model": model,
        "subject_security_id": subject_security_id,
        "factors": list(factors),
        "window": WINDOW,
        "min_obs": MIN_OBS,
        "h": h,
        "return": "log",
        "intercept": "excluded_from_common",
    }
    raw = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def factors_for(model: str, market: str) -> list[str]:
    if model == "M0":
        return []
    return list(MARKET_FACTORS[market][model])


def daily_log_returns(closes: dict[date, float], dates: list[date]) -> dict[date, float]:
    """log(c_t / c_prev) on each series' OWN consecutive bars."""
    out: dict[date, float] = {}
    prev_d = None
    for d in dates:
        c = closes.get(d)
        if c is None or c <= 0:
            prev_d = None
            continue
        if prev_d is not None:
            p = closes.get(prev_d)
            if p is not None and p > 0:
                out[d] = float(np.log(c / p))
        prev_d = d
    return out


def window_log_ret(closes: dict[date, float], fill: date, coverage: date) -> float | None:
    """The `_leg_ret_in_window` (L2540) endpoint rule on log returns: bars must
    exist on EXACTLY the fill and coverage sessions, else None."""
    a, b = closes.get(fill), closes.get(coverage)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return float(np.log(b / a))


def beta_window_dates(subject_dates: list[date], d_cutoff: date,
                      window: int = WINDOW) -> list[date]:
    """The last `window` subject bar dates on or before D(s)."""
    past = [d for d in subject_dates if d <= d_cutoff]
    return past[-window:]


def fit_ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS with intercept (column 0). Returns (coef incl. intercept, resid)."""
    design = np.column_stack([np.ones(len(X)), X]) if X.size else np.ones((len(y), 1))
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ coef
    return coef, resid


def decompose_unit(model: str, market: str, h: int, s: date, d_s: date,
                   fill: date, coverage: date,
                   subject_closes: dict[date, float], subject_dates: list[date],
                   factor_closes: dict[str, dict[date, float]],
                   factor_dates: dict[str, list[date]]) -> dict:
    """One unit x model row: decision-cutoff fit plus observation-cutoff outcome."""
    factors = factors_for(model, market)
    row: dict = {
        "model": model,
        "anchor_session_date": s.isoformat(),
        "abstention": OK,
        "n_obs__dc": None,
        "beta_window_first__dc": None,
        "beta_window_last__dc": None,
        "subject_endpoint_fill__oc": False,
        "subject_endpoint_coverage__oc": False,
        "factor_endpoint_flags__oc": {},
        "sigma_hat__dc": None,
        "r__oc": None,
        "common__oc": None,
        "resid__oc": None,
        "z__oc": None,
    }
    for f in factors:
        row[f"beta_{f}__dc"] = None
        row[f"F_{f}__oc"] = None

    # -- decision cutoff: beta window on bars <= D(s) ------------------------ #
    win_dates = beta_window_dates(subject_dates, d_s)
    if not win_dates:
        row["abstention"] = ABSTAIN_INSUFFICIENT_HISTORY
        return row
    row["beta_window_first__dc"] = win_dates[0].isoformat()
    row["beta_window_last__dc"] = win_dates[-1].isoformat()

    subj_ret = daily_log_returns(subject_closes, subject_dates)
    fac_ret = {f: daily_log_returns(factor_closes[f], factor_dates[f]) for f in factors}

    if model == "M0":
        in_win = [subj_ret[d] for d in win_dates if d in subj_ret]
        row["n_obs__dc"] = len(in_win)
        if len(in_win) < MIN_OBS:
            row["abstention"] = ABSTAIN_INSUFFICIENT_HISTORY
            return row
        arr = np.asarray(in_win)
        row["sigma_hat__dc"] = float(np.std(arr, ddof=1))
        beta = 0.0
    else:
        joint = [d for d in win_dates
                 if d in subj_ret and all(d in fac_ret[f] for f in factors)]
        row["n_obs__dc"] = len(joint)
        if len(joint) < MIN_OBS:
            row["abstention"] = ABSTAIN_INSUFFICIENT_HISTORY
            return row
        y = np.asarray([subj_ret[d] for d in joint])
        X = np.asarray([[fac_ret[f][d] for f in factors] for d in joint])
        coef, resid = fit_ols(y, X)
        row["sigma_hat__dc"] = float(np.std(resid, ddof=1))
        for i, f in enumerate(factors):
            row[f"beta_{f}__dc"] = float(coef[1 + i])   # intercept excluded from common

    # -- observation cutoff: the shared window ------------------------------ #
    row["subject_endpoint_fill__oc"] = fill in subject_closes
    row["subject_endpoint_coverage__oc"] = coverage in subject_closes
    for f in factors:
        okf = fill in factor_closes[f] and coverage in factor_closes[f]
        row["factor_endpoint_flags__oc"][f] = bool(okf)
    r = window_log_ret(subject_closes, fill, coverage)
    if r is None:
        row["abstention"] = ABSTAIN_MISSING_ENDPOINT
        return row
    row["r__oc"] = r
    common = 0.0
    for f in factors:
        fr = window_log_ret(factor_closes[f], fill, coverage)
        if fr is None:
            row["abstention"] = ABSTAIN_MISSING_ENDPOINT
            return row
        row[f"F_{f}__oc"] = fr
        beta = 0.0 if model == "M0" else row[f"beta_{f}__dc"]
        common += beta * fr
    row["common__oc"] = common
    row["resid__oc"] = r - common
    sig = row["sigma_hat__dc"]
    if sig is None or sig <= 0:
        # A degenerate in-window residual scale carries no usable variation;
        # the normalisation cannot be formed, so the unit abstains (A25).
        row["abstention"] = ABSTAIN_INSUFFICIENT_HISTORY
        return row
    row["z__oc"] = row["resid__oc"] / (sig * float(np.sqrt(h)))
    return row
