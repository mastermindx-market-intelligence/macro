"""Private retrospective basket research, NOT a source qualification authority.

The already held files may describe a past session without proving what was known
then. This pure leaf permits that explicitly labeled research computation while
leaving the incumbent qualified product API, dealer signs and publication intact.
No I/O, timestamps invented from dates, covariance store or portfolio writer.
"""
from __future__ import annotations

from datetime import date, datetime
from math import fsum, isfinite, sqrt
from numbers import Real
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from engine.options_basket_aggregation import standardized_iv

MAX_SPREAD = .15
MAX_MONEYNESS = .015
IV_RANGE = (.05, 2.5)
SHRINKAGE = .1
_COLUMNS = {"root", "date", "expiration", "strike", "right", "bid", "ask",
            "underlying_price", "implied_vol", "iv_error"}


def _numeric(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        return False
    try:
        return isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _root(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _day(value: object) -> bool:
    return type(value) is date


def select_iv30(frame: pd.DataFrame | None, *, root: str, anchor: date,
                research_iv_error_abs_max: float = 0.0) -> dict:
    """Matched-strike C/P variance, then incumbent total-variance interpolation.

    Expiry minus source day is an explicit calendar-date tenor approximation, not
    exact intraday time to expiry. The default exact-zero IV error filter is
    the prior baseline. Explicit *research* residual tolerances remain
    unqualified and can never certify fresh/executable quotes, entitlement,
    American exercise/dividend treatment or historical mark publication.
    """
    if not _root(root) or not _day(anchor):
        raise ValueError("root and calendar anchor required")
    if not _numeric(research_iv_error_abs_max) or research_iv_error_abs_max not in (0.0, 5e-5, 1e-4, 5e-4):
        raise ValueError("research iv_error sensitivity threshold must be a declared finite value")
    result = {"root": root, "iv30": None, "tenors": [], "rows_at_anchor": 0,
              "candidate_expiries": 0, "max_selected_spread": None, "reasons": []}
    if research_iv_error_abs_max > 0:
        # This is an exploratory research *policy*, not a vendor-correctness,
        # quote-age, rights or product-qualification decision.
        result["research_sensitivity"] = {
            "iv_error_abs_max": research_iv_error_abs_max,
            "only_exploratory": True,
            "source_quality_certified": False,
            "historical_known_at_certified": False,
        }

    def refuse(reason):
        result["reasons"].append(reason)
        return result

    if frame is None or (isinstance(frame, pd.DataFrame) and frame.empty):
        return refuse("NO_SOURCE_ROWS")
    if not isinstance(frame, pd.DataFrame) or not _COLUMNS.issubset(frame.columns):
        return refuse("SOURCE_COLUMNS_MISSING")
    if frame.columns.duplicated().any():
        return refuse("SOURCE_COLUMNS_AMBIGUOUS")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.dt.tz is not None:
        return refuse("AMBIGUOUS_SOURCE_SESSION_CLOCK")
    f = frame.loc[dates.dt.normalize() == pd.Timestamp(anchor)].copy()
    result["rows_at_anchor"] = len(f)
    if f.empty:
        return refuse("NO_ANCHOR_ROWS")
    if not f["root"].eq(root).fillna(False).all():
        return refuse("ROOT_MISMATCH")
    f["expiration"] = pd.to_datetime(f["expiration"], errors="coerce")
    if f["expiration"].dt.tz is not None:
        return refuse("AMBIGUOUS_EXPIRY_CLOCK")
    if f.duplicated(["expiration", "strike", "right"]).any():
        return refuse("DUPLICATE_CONTRACT")
    spots = f["underlying_price"]
    good_spots = spots.loc[spots.map(_numeric)]
    good_spots = good_spots.loc[good_spots > 0].astype(float)
    if good_spots.empty:
        return refuse("SPOT_UNAVAILABLE")
    spot = float(good_spots.median())
    if float(good_spots.max() / good_spots.min() - 1) > 1e-6:
        return refuse("INCONSISTENT_SPOT")
    numeric = ["bid", "ask", "strike", "implied_vol", "iv_error", "underlying_price"]
    for column in numeric:
        f = f.loc[f[column].map(_numeric)].copy()
    if f.empty:
        return refuse("NO_QUALITY_PAIRS")
    f[numeric] = f[numeric].astype(float)
    f = f.loc[(f.bid > 0) & (f.ask >= f.bid) & (f.strike > 0)
              & (f.underlying_price > 0) & f.implied_vol.between(*IV_RANGE)
              & f.iv_error.abs().le(research_iv_error_abs_max)
              & ((f.strike / spot - 1).abs() <= MAX_MONEYNESS)].copy()
    f["spread"] = (f.ask - f.bid) / ((f.ask + f.bid) / 2)
    f = f.loc[f.spread <= MAX_SPREAD]
    nodes = []
    for expiry, group in f.groupby("expiration", sort=True):
        dte = (expiry.date() - anchor).days
        if not 0 < dte <= 90:
            continue
        pairs = []
        for strike, contracts in group.groupby("strike", sort=True):
            if sorted(contracts.right.tolist()) != ["C", "P"]:
                continue
            pairs.append((abs(float(strike) / spot - 1), float(strike),
                          sqrt(float(np.mean(contracts.implied_vol.to_numpy() ** 2))),
                          float(contracts.spread.max())))
        if pairs:
            _, _, iv, spread = min(pairs)
            nodes.append((dte, iv, spread))
    result["candidate_expiries"] = len(nodes)
    left = max((n for n in nodes if n[0] <= 30), default=None)
    right = min((n for n in nodes if n[0] >= 30), default=None)
    if left is None or right is None:
        return refuse("NO_30D_BRACKET")
    selected = [left] if left[0] == right[0] else [left, right]
    try:
        value = standardized_iv([(d, iv) for d, iv, _ in selected])
    except ValueError:
        return refuse("DECLINING_TOTAL_VARIANCE")
    result.update(iv30=value, tenors=[n[0] for n in selected],
                  max_selected_spread=max(n[2] for n in selected))
    return result


def build_study(*, weights: Mapping[str, float], greeks: Mapping[str, pd.DataFrame],
                closes: pd.DataFrame, sessions: Sequence[date], anchor: date,
                captured_at: datetime, windows: Sequence[int] = (63, 126, 252),
                research_iv_error_abs_max: float = 0.) -> dict:
    """Research measurements with full original membership and exact session grids.

    Correlations use window+1 consecutive owner-supplied session closes. Missing
    prices are never filled, gaps are never bridged, and windows are not extended
    backward to obtain a desired number of complete rows. Nothing here establishes
    historic PIT identity, quote age, data rights, executable prices or prediction.
    """
    if not _day(anchor) or not isinstance(captured_at, datetime) or captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("calendar anchor and aware acquisition timestamp required")
    if captured_at.date() < anchor:
        raise ValueError("anchor must not be after acquisition")
    if not isinstance(weights, Mapping) or not 3 <= len(weights) <= 50:
        raise ValueError("bounded house basket requires 3 to 50 members")
    if any(not _root(r) or not _numeric(w) or w <= 0 for r, w in weights.items()):
        raise ValueError("positive finite original weights and root identities required")
    if abs(fsum(float(w) for w in weights.values()) - 1) > 1e-12:
        raise ValueError("original weights must sum to one; renormalization refused")
    if not isinstance(greeks, Mapping) or not set(greeks).issubset(weights):
        raise ValueError("unexpected Greek root identity")
    if not windows or any(type(w) is not int or not 3 <= w <= 756 for w in windows) or len(set(windows)) != len(windows):
        raise ValueError("unique bounded integer return windows required")
    if not sessions or any(not _day(s) for s in sessions) or list(sessions) != sorted(set(sessions)) or sessions[-1] != anchor:
        raise ValueError("ordered unique incumbent sessions ending exactly at anchor required")
    if not isinstance(closes, pd.DataFrame) or not isinstance(closes.index, pd.DatetimeIndex):
        raise ValueError("session-indexed close panel required")
    if closes.columns.duplicated().any() or closes.index.duplicated().any():
        raise ValueError("duplicate price identity or date")
    if closes.index.tz is not None or not closes.index.equals(closes.index.normalize()):
        raise ValueError("daily session labels required, not intraday/ambiguous clocks")
    roots = sorted(weights)
    selected = {r: select_iv30(greeks.get(r), root=r, anchor=anchor,
               research_iv_error_abs_max=research_iv_error_abs_max) for r in roots}
    covered = [r for r in roots if selected[r]["iv30"] is not None]
    cw = fsum(weights[r] for r in covered)
    mean = fsum(weights[r] * selected[r]["iv30"] for r in covered) / cw if covered else None
    rms = sqrt(fsum(weights[r] * selected[r]["iv30"] ** 2 for r in covered) / cw) if covered else None
    cut = closes.loc[closes.index <= pd.Timestamp(anchor)].sort_index()
    panel = cut.reindex(index=pd.to_datetime(sessions), columns=roots)
    # No coercion of strings/booleans to prices; missing/invalid cells retain gaps.
    for column in panel.columns:
        panel[column] = panel[column].map(lambda v: float(v) if _numeric(v) and v > 0 else np.nan)
    model_results = {}
    for window in windows:
        rec = {"move": None, "shrunken_move": None, "n_returns": 0,
               "first_return_session": None, "last_return_session": anchor.isoformat(),
               "mean_pairwise_correlation": None, "minimum_correlation_eigenvalue": None,
               "max_abs_log_return": None, "reasons": []}
        if len(covered) != len(roots):
            rec["reasons"].append("INCOMPLETE_IV_COVERAGE")
        sample = panel.tail(window + 1)
        if len(sample) != window + 1 or sample.isna().any().any():
            rec["reasons"].append("INCOMPLETE_PRICE_WINDOW")
        else:
            returns = np.diff(np.log(sample.to_numpy(dtype=float)), axis=0)
            rec["n_returns"] = window
            rec["first_return_session"] = sample.index[1].date().isoformat()
            rec["max_abs_log_return"] = float(np.abs(returns).max())
            if (returns.std(axis=0, ddof=1) <= 1e-14).any():
                rec["reasons"].append("CONSTANT_PRICE_SERIES")
            elif not rec["reasons"]:
                R = np.corrcoef(returns, rowvar=False)
                eigen = np.linalg.eigvalsh(R)
                if not np.isfinite(R).all() or eigen.min() < -1e-10:
                    rec["reasons"].append("INVALID_CORRELATION")
                else:
                    weighted = np.array([weights[r] * selected[r]["iv30"] for r in roots])
                    rec["move"] = sqrt(max(0, float(weighted @ R @ weighted)) * 30 / 365)
                    shrunk = (1 - SHRINKAGE) * R + SHRINKAGE * np.eye(len(roots))
                    rec["shrunken_move"] = sqrt(max(0, float(weighted @ shrunk @ weighted)) * 30 / 365)
                    rec["mean_pairwise_correlation"] = float((R.sum() - np.trace(R)) / (len(roots) * (len(roots) - 1)))
                    rec["minimum_correlation_eigenvalue"] = float(eigen.min())
        model_results[str(window)] = rec
    result = {
        "schema": "factor_atlas.options_retrospective/v1",
        "classification": "PRIVATE_RETROSPECTIVE_RESEARCH_NOT_PRODUCT_QUALIFIED",
        "anchor": anchor.isoformat(), "captured_at": captured_at.isoformat(),
        "historical_known_at": None, "quote_timestamps": "NOT_AVAILABLE_IN_LEGACY_FILES",
        "coverage": {"count": len(covered), "total_count": len(roots), "weight": float(cw),
                     "missing_weight": max(0., 1 - float(cw)), "excluded_roots": sorted(set(roots) - set(covered))},
        "research": {"mean_iv": mean, "rms_iv": rms,
                     "label": "covered constituent IV statistics, not traded basket IV"},
        "method": {"calendar_days": 30, "year_denominator": 365,
                   "tenor_basis": "calendar_date_difference_not_exact_expiry_clock",
                   "membership_basis": "retrospective_current_roster", "return_basis": "supplied_close_basis_unqualified",
                   "pair_method": "same_strike_call_put_mean_variance",
                   "quote_max_relative_spread": MAX_SPREAD, "strike_max_spot_distance": MAX_MONEYNESS,
                   "iv_min": IV_RANGE[0], "iv_max": IV_RANGE[1], "stored_iv_error_required": 0,
                   "covariance": "common_session_log_return_sample_correlation",
                   "shrinkage_to_identity": SHRINKAGE, "shrinkage_calibrated": False,
                   "no_price_fill": True, "no_historical_availability_claim": True},
        "members": [{"root": r, "weight": float(weights[r]), **selected[r]} for r in roots],
        "models": model_results,
        "product": {"qualified": False, "headline_iv": None, "expected_move": None},
        "authority": {"publication": False, "prophet": False, "position_sizing": False},
    }
    if research_iv_error_abs_max>0:
        result['research_sensitivity']={
            'iv_error_abs_max':float(research_iv_error_abs_max),
            'source_quality_certified':False,
            'historical_known_at_certified':False,
            'publication':False,
        }
    return result
