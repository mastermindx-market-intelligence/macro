"""Build the regime-vintage PIT spine — data/regime/regime_v2_pit.parquet.

CPI program P-D5-1 (regime_v2_pit), phase 4a: builder + divergence audit ONLY.
The W4.4 cell re-keying onto this spine is a LATER, preregistration-governed wave.

What this does
--------------
Re-runs the live quad classification (engine.regime.classify + the transition
flag/state machine, i.e. the exact engine/run.py history pipeline) over full
history with the five revision-leaky macro legs read AS-OF each date from the
ALFRED vintage store (data/fred_vintage/vintages.parquet), instead of the
latest-revised values the live store keeps:

    growth:    payrolls (PAYEMS), indpro (INDPRO), wei (WEI), gdpnow (GDPNOW)
    inflation: sticky_cpi (STICKCPIM157SFRBATL, via the sticky_cpi_3m derivation)

Every other leg is market-priced (rates/OAS/equities/commodities/breadth) and
therefore PIT-pure by construction — untouched.

PIT semantics (vectorized; the as_of_series(series, d) loop over ~14k dates would
be O(n^2)): per series, one availability panel — the initial-release value of the
latest published period, stamped at its realtime_start. On any date d the panel
carries exactly what collectors.fred.as_of_series(sid, d) would return as its
latest observation. The panel is injected into engine.inputs.build_features via
the `overrides` seam, so alignment (dedupe/union-reindex/ffill limits), axis
scoring, hysteresis, refinements, flags and the transition state machine are the
SAME code the live path runs — zero forked math.

Fallback (flagged, never silent): dates before a series' vintage coverage begins
(PAYEMS/INDPRO 1997-01, GDPNOW 2016-08, sticky CPI 2014-03, WEI 2020-04) read the
latest-revised live series — identical to the live frame there. Per-date columns:

    pit_class      in {pit_vintage, revised_latest, mixed}
                   (all active macro legs vintage / all fallback / some of each;
                   rows with NO active macro leg are classed by date vs the
                   earliest vintage coverage — they carry no revision leak either way)
    fallback_notes comma-joined legs that fell back on that date ('' if none)

Known honesty bounds (documented, not fixable from this store):
  * The vintage store keeps INITIAL releases only — for GDPNOW that is the first
    nowcast of each quarter; the live intra-quarter updates are genuinely new
    information a real-time reader had but this spine does not.
  * Legacy pit_class remains a current-value source-region label only. Additive
    macro_window_* columns expose revised/unknown inputs across the actual slow
    component endpoints and smoothing windows. No score or state is changed.
  * Initial-release input support is not full-vintage information, market-source
    availability, fitted-model provenance, or proof of historical forecast issuance.

ADDITIVE: writes ONLY data/regime/regime_v2_pit.parquet and
data/regime/regime_v2_pit_divergence.json. Never touches regime_history.parquet,
latest.json, or any live consumer. Not wired into any DAG lane this wave
(synapse cadence: on-demand).

Usage:  python scripts/build_regime_v2_pit.py [--out-dir data/regime]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from lib import config, store  # noqa: E402

log = logging.getLogger(__name__)

# The revision-leaky macro legs of the quad axes: live-frame column -> FRED sid +
# the classify() component-score column that tells us the leg was ACTIVE (non-NaN
# component => it contributed weight to the axis that day).
LEGS: dict[str, dict[str, str]] = {
    "payrolls":   {"sid": "PAYEMS", "component": "c_growth_payrolls_trend"},
    "indpro":     {"sid": "INDPRO", "component": "c_growth_indpro_trend"},
    "wei":        {"sid": "WEI", "component": "c_growth_wei_trend"},
    "gdpnow":     {"sid": "GDPNOW", "component": "c_growth_gdpnow_trend"},
    "sticky_cpi": {"sid": "STICKCPIM157SFRBATL",
                   "component": "c_inflation_sticky_cpi_direction"},
}

PIT_CLASSES = ("pit_vintage", "revised_latest", "mixed")

# Descriptive dependencies of the existing slow components, not another scoring
# implementation. Tests bind these to the actual axes.monthly_sign calls and
# inputs.build_features rolling mean. All offsets refer to aligned feature rows,
# NOT months, calendar days or exchange sessions. Scoring itself is unchanged.
MACRO_WINDOW_SPECS = {
    "payrolls": {"scored_feature": "payrolls", "lag_rows": 63, "smooth_rows": 1, "min_periods": 1},
    "indpro": {"scored_feature": "indpro", "lag_rows": 252, "smooth_rows": 1, "min_periods": 1},
    "wei": {"scored_feature": "wei", "lag_rows": 65, "smooth_rows": 1, "min_periods": 1},
    "gdpnow": {"scored_feature": "gdpnow", "lag_rows": 63, "smooth_rows": 1, "min_periods": 1},
    "sticky_cpi": {"scored_feature": "sticky_cpi_3m", "lag_rows": 63, "smooth_rows": 63, "min_periods": 21},
}
MACRO_WINDOW_COLUMNS = (
    "macro_window_basis", "macro_window_revised_legs",
    "macro_window_unknown_legs", "macro_window_active_count",
)


def _per_value_source_dates(source: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """For each row in `index`, the source's last index date <= row date where
    the source had a finite observation. NaT when no prior finite observation
    exists in the source.

    Matches `engine/inputs.put()`: duplicate stamps are de-duplicated keeping
    the LAST row (the value carried by the forward-fill), BEFORE the dropna
    pass — so a finite-then-NaN duplicate at the same stamp does not resurrect
    an earlier observation as the per-value source date.
    """
    if not isinstance(source, pd.Series) or len(source) == 0:
        return pd.Series(pd.NaT, index=index)
    if source.index.has_duplicates:
        source = source[~source.index.duplicated(keep="last")]
    finite = source.dropna()
    if finite.empty:
        return pd.Series(pd.NaT, index=index)
    src_idx = pd.DatetimeIndex(finite.index)
    if src_idx.has_duplicates:
        src_idx = src_idx[~src_idx.duplicated(keep="last")]
    # F6: normalise a tz-aware index to naive UTC before comparison; if any
    # step raises, the leg is UNKNOWN (the caller marks every finite row
    # unknown_inputs and never lets the exception escape).
    try:
        if isinstance(src_idx, pd.DatetimeIndex) and src_idx.tz is not None:
            src_idx = src_idx.tz_convert("UTC").tz_localize(None)
        if isinstance(index, pd.DatetimeIndex) and index.tz is not None:
            compare_index = index.tz_convert("UTC").tz_localize(None)
        else:
            compare_index = index
        if src_idx.hasnans or not src_idx.is_monotonic_increasing:
            src_idx = src_idx.sort_values()
        positions = src_idx.searchsorted(compare_index, side="right") - 1
    except (ValueError, TypeError):
        return pd.Series(pd.NaT, index=index)
    out = pd.Series(pd.NaT, index=index)
    valid = (positions >= 0) & (positions < len(src_idx))
    if valid.any():
        out.iloc[valid.nonzero()[0]] = src_idx[positions[valid]]
    return out


def macro_window_provenance(
    features: pd.DataFrame,
    active: dict[str, pd.Series],
    coverage_start: dict[str, pd.Timestamp | None],
    *,
    sources: dict[str, pd.Series] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Describe the contributing slow-component inputs, never certify a replay.

    Uses the SAME aligned raw features that the numeric classifier consumed.
    A difference depends on its two endpoints. Sticky CPI additionally depends
    on the non-null observations of BOTH rolling means, honoring min_periods;
    missing observations do not become revised inputs or a uniform embargo.

    Per-value provenance: when `sources` provides an un-forward-filled leg
    series for a leg, `revised` is set from the per-value source date (the
    last index date at which the source had a finite observation, carried
    forward the same way the value is) rather than the row's own date. A
    forward-filled post-coverage row whose supplying observation predates
    `first` is therefore still `revised_fallback_inputs`, never
    `initial_vintage_inputs`. A NaN initial-vintage value never upgrades a
    label.

    Default path is UNKNOWN. If `sources` is None, or lacks a leg, that
    leg's per-value source date is UNKNOWN and every row that depends on
    it resolves to `unknown_inputs`. The forward-filled feature column is
    never used as its own source — without the un-filled series the
    function cannot tell an observed value from one carried forward from
    before coverage, and the conservative label is the only honest one.

    Source-series comparison normalises a timezone-aware source index to
    naive UTC before lookup; if comparison is still impossible the leg is
    UNKNOWN, never an exception. None coverage means a known latest-
    revised fallback. A coverage value that is not a string, date or
    Timestamp (bool, int, float, NaT, etc.) is unparseable and resolves
    that leg to UNKNOWN. An absent coverage key or component activity
    series is UNKNOWN, not proof of inactivity. The legacy pit_class,
    model inputs, scores and state machine are never modified.
    """
    if not isinstance(features, pd.DataFrame):
        raise ValueError("aligned feature frame required")
    index = features.index
    if (not isinstance(index, pd.DatetimeIndex) or index.hasnans
            or not index.is_unique or not index.is_monotonic_increasing):
        raise ValueError("unique ordered datetime feature index required")
    states = pd.DataFrame(index=index)
    active_count = pd.Series(0, index=index, dtype="int64")
    for leg, spec in MACRO_WINDOW_SPECS.items():
        activity = active.get(leg)
        if not isinstance(activity, pd.Series) or not pd.api.types.is_bool_dtype(activity.dtype):
            states[leg] = "unknown_inputs"
            continue
        activity = activity.reindex(index)
        is_active = activity.fillna(False).astype(bool)
        active_count += is_active.astype(int)
        unknown_activity = activity.isna()
        raw = features.get(leg, pd.Series(np.nan, index=index))
        numeric = pd.to_numeric(raw, errors="coerce")
        finite = pd.Series(np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan)), index=index)
        if pd.api.types.is_bool_dtype(raw.dtype):
            finite[:] = False
        invalid = raw.notna() & ~finite
        revised = pd.Series(False, index=index)
        unknown = invalid.copy()
        if leg not in coverage_start:
            unknown |= finite
        elif coverage_start[leg] is None:
            revised = finite.copy()
        else:
            raw_coverage = coverage_start[leg]
            # F7: only string/date/Timestamp values are valid coverage starts;
            # bool/int/float/None-coverage are unparseable -> UNKNOWN.
            if not isinstance(raw_coverage, (str, pd.Timestamp, _dt.date, np.datetime64)):
                unknown |= finite
            else:
                first = None
                try:
                    first = pd.Timestamp(raw_coverage)
                except (ValueError, TypeError):
                    first = None
                if first is None or pd.isna(first) or (first.tzinfo is None) != (index.tz is None):
                    unknown |= finite
                else:
                    # F1: default path is UNKNOWN — the forward-filled feature
                    # column is never used as its own source.
                    source = None
                    if sources is not None and isinstance(sources, dict) and leg in sources:
                        source = sources[leg]
                    if not isinstance(source, pd.Series) or len(source) == 0:
                        unknown |= finite
                    else:
                        source_dates = _per_value_source_dates(source, index)
                        try:
                            revised = finite & source_dates.notna() & (source_dates < first)
                            unknown |= finite & source_dates.isna()
                        except (TypeError, ValueError):
                            # Defensive: a comparison that cannot be resolved
                            # (e.g. tz-aware coverage vs. naive source dates
                            # surviving _per_value_source_dates, or an
                            # out-of-order timestamp index). The leg's finite
                            # rows become unknown_inputs rather than raising.
                            unknown |= finite
                            revised = pd.Series(False, index=index)
        window, minimum, lag = spec["smooth_rows"], spec["min_periods"], spec["lag_rows"]
        counts = finite.astype(int).rolling(window, min_periods=1).sum()
        usable = counts >= minimum
        revised_count = revised.astype(int).rolling(window, min_periods=1).sum()
        unknown_count = unknown.astype(int).rolling(window, min_periods=1).sum()
        complete = usable & usable.shift(lag, fill_value=False)
        has_unknown = (unknown_count + unknown_count.shift(lag).fillna(0)) > 0
        has_revised = (revised_count + revised_count.shift(lag).fillna(0)) > 0
        row = pd.Series("not_active", index=index)
        row.loc[is_active] = "unknown_inputs"
        known = is_active & complete & ~has_unknown
        row.loc[known & has_revised] = "revised_fallback_inputs"
        row.loc[known & ~has_revised] = "initial_vintage_inputs"
        row.loc[unknown_activity] = "unknown_inputs"
        states[leg] = row

    unknown_any = states.eq("unknown_inputs").any(axis=1)
    revised_any = states.eq("revised_fallback_inputs").any(axis=1)
    basis = pd.Series("no_active_macro_components", index=index)
    basis.loc[active_count > 0] = "initial_vintage_inputs"
    basis.loc[revised_any] = "revised_fallback_inputs"
    basis.loc[unknown_any] = "unknown_inputs"

    def names(status: str) -> pd.Series:
        result = pd.Series("", index=index)
        for leg in MACRO_WINDOW_SPECS:
            mask = states[leg].eq(status)
            result.loc[mask] = result.loc[mask].map(lambda value: value + "," if value else "") + leg
        return result

    result = pd.DataFrame({
        "macro_window_basis": basis,
        "macro_window_revised_legs": names("revised_fallback_inputs"),
        "macro_window_unknown_legs": names("unknown_inputs"),
        "macro_window_active_count": active_count,
    }, index=index)
    audit = {
        "schema": "regime_v2_pit.macro_window_basis.v1",
        "scope": "active_slow_component_inputs_only",
        "method": "source_region_and_actual_nonnull_transform_support",
        "offset_basis": "aligned_business_day_feature_rows_not_exchange_sessions",
        "dependencies": {key: dict(value) for key, value in MACRO_WINDOW_SPECS.items()},
        "counts": {str(key): int(value) for key, value in basis.value_counts().items()},
        "by_leg": {leg: {str(key): int(value) for key, value in states[leg].value_counts().items()}
                   for leg in MACRO_WINDOW_SPECS},
        "legacy_pit_class_changed": False,
        "numeric_model_changed": False,
        "historical_replay_eligible": False,
        "market_input_availability_verified": False,
        "fitted_model_and_state_history_verified": False,
        "actual_historical_issuance_verified": False,
        "state_columns_qualified": False,
        "note": "Initial-vintage input support is not complete as-of information, fitted-model provenance or an issued forecast. macro_window_* columns qualify the slow-component input windows only; they do not qualify quad, pending_quad, or any other state column because confirmation hysteresis can carry a state entered under revised inputs into rows whose inputs are initial-vintage.",
    }
    return result, audit

ERAS: dict[str, tuple[str | None, str | None]] = {
    "pre_2008": (None, "2007-12-31"),
    "2008_09": ("2008-01-01", "2009-12-31"),
    "2010_19": ("2010-01-01", "2019-12-31"),
    "2020_plus": ("2020-01-01", None),
}
TRANSITION_WINDOWS: dict[str, tuple[str, str]] = {
    "2008_09": ("2008-01-01", "2009-12-31"),
    "2020": ("2020-01-01", "2020-12-31"),
}


# --------------------------------------------------------------------------- #
# PIT panel construction (vectorized as-of)
# --------------------------------------------------------------------------- #
def pit_availability_panel(vintages: pd.DataFrame, sid: str) -> pd.Series:
    """Initial-release value of the LATEST published period, stamped at its
    realtime_start. Reindex+ffill of this panel gives, on every date d, exactly
    what collectors.fred.as_of_series(sid, d) returns as its last observation —
    without the O(n_dates * n_rows) per-date loop.

    Steps: initial release per period (earliest realtime_start wins — the store
    keeps initials, but a revision row would be dropped here, not leaked);
    running-max filter on period (a late release of an OLDER period never
    overwrites newer information); same-day multi-period releases keep the
    latest period.
    """
    sub = vintages[vintages["series"] == sid]
    if sub.empty:
        return pd.Series(dtype=float)
    sub = sub.copy()
    sub["period"] = pd.to_datetime(sub["period"])
    sub["realtime_start"] = pd.to_datetime(sub["realtime_start"])
    # initial release per period
    sub = (sub.sort_values(["period", "realtime_start"])
              .drop_duplicates(subset="period", keep="first"))
    # publication order; never step back to an older period
    sub = sub.sort_values(["realtime_start", "period"])
    sub = sub[sub["period"].cummax() == sub["period"]]
    # same-day multi-period release: latest period wins
    sub = sub.drop_duplicates(subset="realtime_start", keep="last")
    return pd.Series(sub["value"].to_numpy(),
                     index=pd.DatetimeIndex(sub["realtime_start"]), name=sid)


def live_reference_series(sid: str) -> pd.Series:
    """The latest-revised, reference-stamped store series exactly as the live
    frame reads it (engine.inputs._fred: first parquet column)."""
    df = store.read("fred", sid)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    s = df.iloc[:, 0].dropna()
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def merged_leg_series(live: pd.Series, panel: pd.Series,
                      first_rt: pd.Timestamp) -> pd.Series:
    """Vintage availability panel where coverage exists; latest-revised live
    values (reference-stamped) strictly BEFORE the first vintage realtime_start.
    The fallback region reproduces live behaviour and is flagged per-date."""
    pre = live[live.index < first_rt]
    out = pd.concat([pre, panel]).sort_index(kind="stable")
    # stable sort keeps the panel row last on a stamp collision; put() dedupes keep-last
    return out


# --------------------------------------------------------------------------- #
# pit_class / fallback flagging
# --------------------------------------------------------------------------- #
def classify_pit_rows(index: pd.DatetimeIndex,
                      active: dict[str, pd.Series],
                      coverage_start: dict[str, pd.Timestamp | None]) -> pd.DataFrame:
    """Per-date pit_class + fallback_notes from per-leg activity masks and
    vintage coverage starts. A leg 'fell back' on d when it was ACTIVE (non-NaN
    component score) and d predates its vintage coverage."""
    starts = [t for t in coverage_start.values() if t is not None]
    earliest = min(starts) if starts else None
    n_active = pd.Series(0, index=index)
    n_fb = pd.Series(0, index=index)
    fb_masks: dict[str, pd.Series] = {}
    for leg, act in active.items():
        act = act.reindex(index).fillna(False).astype(bool)
        first_rt = coverage_start.get(leg)
        fb = act & (pd.Series(index < first_rt, index=index) if first_rt is not None
                    else True)
        fb_masks[leg] = fb
        n_active = n_active + act.astype(int)
        n_fb = n_fb + fb.astype(int)

    pit_class = pd.Series("mixed", index=index)
    pit_class[n_fb == 0] = "pit_vintage"
    pit_class[(n_active > 0) & (n_fb == n_active)] = "revised_latest"
    if earliest is not None:
        # no active macro leg: no revision-leaky input at all; class by era for
        # legibility (pre-coverage rows sit with their revised_latest neighbours)
        pit_class[(n_active == 0) & (index < earliest)] = "revised_latest"

    notes = pd.Series("", index=index)
    for leg in LEGS:  # fixed order — deterministic notes
        if leg not in fb_masks:
            continue
        m = fb_masks[leg]
        notes[m] = notes[m].where(notes[m] == "", notes[m] + ",") + leg
    return pd.DataFrame({"pit_class": pit_class, "fallback_notes": notes})


# --------------------------------------------------------------------------- #
# Divergence audit
# --------------------------------------------------------------------------- #
def _pct(mask: pd.Series) -> float:
    return round(float(mask.mean()) * 100, 2) if len(mask) else float("nan")


def _run_lengths(mask: pd.Series) -> list[int]:
    """Lengths of consecutive-True runs (in row order of the mask's index)."""
    if mask.empty or not mask.any():
        return []
    grp = (mask != mask.shift()).cumsum()
    return [int(g.sum()) for _, g in mask.groupby(grp) if g.iloc[0]]


def _transitions(quad: pd.Series) -> list[dict]:
    """Confirmed-quad transition dates: rows where quad differs from the prior
    non-null quad."""
    q = quad.dropna()
    chg = q != q.shift()
    out = []
    prev = None
    for d, v in q.items():
        if prev is not None and v != prev:
            out.append({"date": str(pd.Timestamp(d).date()), "from": prev, "to": v})
        prev = v
    del chg
    return out


def divergence_audit(pit: pd.DataFrame, rev: pd.DataFrame,
                     committed_history: pd.DataFrame | None,
                     vintage_covered_from: pd.Timestamp | None = None) -> dict:
    """PIT-vs-revised divergence stats. `pit`/`rev` are classify()-style frames
    aligned on the same index (quad, raw_quad, growth_score, inflation_score).
    `vintage_covered_from`: earliest vintage coverage — dates before it are
    fallback-everywhere (structurally identical to live), so the overall rate is
    also reported normalized to vintage-covered dates."""
    both = pit["quad"].notna() & rev["quad"].notna()
    idx = pit.index[both]
    dq = pd.Series(pit.loc[idx, "quad"].to_numpy() != rev.loc[idx, "quad"].to_numpy(),
                   index=idx)
    raw_both = pit["raw_quad"].notna() & rev["raw_quad"].notna()
    ridx = pit.index[raw_both]
    draw = pd.Series(pit.loc[ridx, "raw_quad"].to_numpy()
                     != rev.loc[ridx, "raw_quad"].to_numpy(), index=ridx)

    by_era = {}
    for era, (lo, hi) in ERAS.items():
        m = pd.Series(True, index=idx)
        if lo:
            m &= idx >= pd.Timestamp(lo)
        if hi:
            m &= idx <= pd.Timestamp(hi)
        sub = dq[m]
        by_era[era] = {"n_dates": int(len(sub)), "pct_quad_divergent": _pct(sub)}
    worst_era = max((e for e in by_era if by_era[e]["n_dates"] > 0),
                    key=lambda e: by_era[e]["pct_quad_divergent"])

    # per-axis: sign divergence (the raw_quad convention: g >= 0) + score deltas
    per_axis = {}
    for ax in ("growth", "inflation"):
        p, r = pit[f"{ax}_score"], rev[f"{ax}_score"]
        m = p.notna() & r.notna()
        sign_flip = (p[m] >= 0) != (r[m] >= 0)
        per_axis[ax] = {
            "n_dates": int(m.sum()),
            "pct_sign_divergent": _pct(sign_flip),
            "mean_abs_score_delta": round(float((p[m] - r[m]).abs().mean()), 4),
            "max_abs_score_delta": round(float((p[m] - r[m]).abs().max()), 4),
        }

    runs = _run_lengths(dq)
    run_stats = {
        "n_runs": len(runs),
        "mean_bd": round(float(np.mean(runs)), 1) if runs else None,
        "median_bd": float(np.median(runs)) if runs else None,
        "p90_bd": float(np.percentile(runs, 90)) if runs else None,
        "max_bd": int(max(runs)) if runs else None,
    }

    # transition-date shifts on revision-prone windows
    shifts = {}
    for name, (lo, hi) in TRANSITION_WINDOWS.items():
        lo_t, hi_t = pd.Timestamp(lo), pd.Timestamp(hi)
        rev_tr = [t for t in _transitions(rev["quad"])
                  if lo_t <= pd.Timestamp(t["date"]) <= hi_t]
        pit_tr = [t for t in _transitions(pit["quad"])
                  if lo_t - pd.Timedelta(days=120) <= pd.Timestamp(t["date"])
                  <= hi_t + pd.Timedelta(days=120)]
        rows = []
        for t in rev_tr:
            cands = [p for p in pit_tr if p["to"] == t["to"]
                     and abs((pd.Timestamp(p["date"]) - pd.Timestamp(t["date"])).days) <= 90]
            best = min(cands, key=lambda p: abs(
                (pd.Timestamp(p["date"]) - pd.Timestamp(t["date"])).days)) if cands else None
            rows.append({
                "revised_date": t["date"], "from": t["from"], "to": t["to"],
                "pit_date": best["date"] if best else None,
                "shift_days": (pd.Timestamp(best["date"])
                               - pd.Timestamp(t["date"])).days if best else None,
            })
        shifts[name] = {"n_revised_transitions": len(rev_tr),
                        "n_pit_transitions_in_window": len(
                            [p for p in pit_tr
                             if lo_t <= pd.Timestamp(p["date"]) <= hi_t]),
                        "matched": rows}

    control = None
    if committed_history is not None and "quad" in committed_history:
        common = rev.index.intersection(committed_history.index)
        a = rev.loc[common, "quad"]
        b = committed_history.loc[common, "quad"]
        m = a.notna() & b.notna()
        control = {
            "n_common_dates": int(m.sum()),
            "fresh_revised_vs_committed_quad_match_pct": _pct(
                pd.Series(a[m].to_numpy() == b[m].to_numpy(), index=common[m])),
            "note": ("control: the fresh latest-revised rebuild vs the committed "
                     "regime_history.parquet; <100% reflects store data drift since "
                     "the last engine run, NOT the PIT change"),
        }

    cov = None
    if vintage_covered_from is not None:
        sub = dq[dq.index >= vintage_covered_from]
        cov = {"from": str(vintage_covered_from.date()),
               "n_dates": int(len(sub)), "pct_quad_divergent": _pct(sub)}

    return {
        "schema_version": 1,
        "headline": {
            "pct_dates_quad_divergent": _pct(dq),
            "pct_vintage_covered_dates_divergent": (cov or {}).get("pct_quad_divergent"),
            "worst_era": worst_era,
            "worst_era_pct": by_era[worst_era]["pct_quad_divergent"],
        },
        "overall": {
            "n_comparable_dates": int(len(dq)),
            "pct_quad_divergent": _pct(dq),
            "pct_raw_quad_divergent": _pct(draw),
            "vintage_covered_dates": cov,
        },
        "by_era": by_era,
        "per_axis": per_axis,
        "divergence_run_lengths": run_stats,
        "transition_shifts": shifts,
        "control": control,
    }


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def _state_inheritance(quad: pd.Series | None, basis: pd.Series) -> dict:
    """Count and first/last date of rows whose `macro_window_basis` is
    `initial_vintage_inputs` while the start of their current contiguous
    `quad` run has a different basis. Confirmation hysteresis can carry a
    state entered under revised inputs into rows whose inputs are
    initial-vintage, so the `macro_window_*` columns must not be used to
    qualify `quad`, `pending_quad`, or any other state column. The audit
    always reports this count so consumers can see the surface area of
    the effect — `state_columns_qualified` is False regardless of size."""
    empty = {"n_rows": 0, "first_date": None, "last_date": None}
    if quad is None or len(quad) == 0 or len(basis) == 0:
        return empty
    df = pd.DataFrame({"quad": quad, "basis": basis}).dropna(subset=["quad"])
    if df.empty:
        return empty
    grp = (df["quad"] != df["quad"].shift()).cumsum()
    df = df.assign(_run_start_basis=df.groupby(grp)["basis"].transform("first"))
    flagged = df[(df["basis"] == "initial_vintage_inputs")
                 & (df["_run_start_basis"] != "initial_vintage_inputs")]
    if flagged.empty:
        return empty
    return {
        "n_rows": int(len(flagged)),
        "first_date": str(pd.Timestamp(flagged.index[0]).date()),
        "last_date": str(pd.Timestamp(flagged.index[-1]).date()),
    }


def build_frames(vintages: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Returns (pit_history_frame, divergence_dict). Pure compute — no writes."""
    from collectors.fred import load_vintages
    from engine.inputs import build_features
    from engine.regime import classify
    from engine.transition import compute_flags, state_machine_detail

    v = vintages if vintages is not None else load_vintages()
    if v is None or v.empty:
        raise RuntimeError("no vintage store at data/fred_vintage/vintages.parquet "
                           "— run the FRED vintage collector first")
    vintage_store_asof = str(pd.to_datetime(v["realtime_start"]).max().date())

    overrides: dict[str, pd.Series] = {}
    coverage_start: dict[str, pd.Timestamp | None] = {}
    for col, spec in LEGS.items():
        panel = pit_availability_panel(v, spec["sid"])
        first_rt = panel.index.min() if len(panel) else None
        coverage_start[col] = first_rt
        if first_rt is None:
            log.warning("regime_v2_pit: no vintage rows for %s (%s) — leg stays "
                        "latest-revised everywhere (flagged)", col, spec["sid"])
            continue
        overrides[col] = merged_leg_series(live_reference_series(spec["sid"]),
                                           panel, first_rt)

    # PIT leg: identical engine/run.py history pipeline, macro legs injected
    f_pit = build_features(overrides=overrides)
    reg_pit = classify(f_pit)
    flags = compute_flags(f_pit, reg_pit)
    reg_pit = reg_pit.join(flags)
    reg_pit = reg_pit.join(state_machine_detail(flags, reg_pit))

    # revised control leg: the same code with NO overrides (fresh latest-revised)
    f_rev = build_features()
    reg_rev = classify(f_rev)

    active = {leg: reg_pit[spec["component"]].notna()
              for leg, spec in LEGS.items() if spec["component"] in reg_pit}
    pc = classify_pit_rows(reg_pit.index, active, coverage_start)

    hist_cols = [c for c in reg_pit.columns if not c.startswith("c_")]
    out = reg_pit[hist_cols].copy()
    out["pit_class"] = pc["pit_class"]
    out["fallback_notes"] = pc["fallback_notes"]
    out["vintage_store_asof"] = vintage_store_asof
    windows, window_audit = macro_window_provenance(f_pit, active, coverage_start, sources=overrides)
    out = out.join(windows.reindex(out.index))
    window_audit["state_inheritance"] = _state_inheritance(out.get("quad"), out["macro_window_basis"])

    committed = None
    hist_path = config.data_dir() / "regime" / "regime_history.parquet"
    if hist_path.exists():
        committed = pd.read_parquet(hist_path)

    starts = [t for t in coverage_start.values() if t is not None]
    div = divergence_audit(reg_pit, reg_rev, committed,
                           vintage_covered_from=min(starts) if starts else None)
    div["vintage_store_asof"] = vintage_store_asof
    div["frame_asof"] = str(out.index.max().date())
    div["pit_class_counts"] = {k: int(c) for k, c in
                               out["pit_class"].value_counts().items()}
    div["fallback_coverage"] = {
        leg: {
            "sid": spec["sid"],
            "vintage_from": (str(coverage_start[leg].date())
                             if coverage_start[leg] is not None else None),
            "n_dates_active": int(active[leg].sum()) if leg in active else 0,
            "n_dates_fallback": int(out["fallback_notes"].str.contains(
                leg, regex=False).sum()),
        }
        for leg, spec in LEGS.items()
    }
    div["macro_window_provenance"] = window_audit
    div["columns_dropped_vs_regime_history"] = []  # full 29-column parity
    return out, div


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        df.to_parquet(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _atomic_write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="output directory (default: <data_dir>/regime)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    out_dir = args.out_dir if args.out_dir is not None else config.data_dir() / "regime"
    frame, div = build_frames()
    _atomic_write_parquet(frame, out_dir / "regime_v2_pit.parquet")
    _atomic_write_json(div, out_dir / "regime_v2_pit_divergence.json")

    h = div["headline"]
    print(f"regime_v2_pit: {len(frame)} rows {frame.index.min().date()} -> "
          f"{frame.index.max().date()} | quad PIT!=revised on "
          f"{h['pct_dates_quad_divergent']}% of comparable dates "
          f"(worst era {h['worst_era']}: {h['worst_era_pct']}%)")
    print(f"pit_class counts: {div['pit_class_counts']}")
    print(f"slow-component input-window basis: {div['macro_window_provenance']['counts']}")
    print("Window support is not historical forecast or full replay certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
