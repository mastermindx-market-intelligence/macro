"""Systematic Strategies research engine — the first HONEST, DETERMINISTIC
descriptive simulation over the frozen RESEARCH_ONLY candidates.

WHAT THIS IS
------------
A read-only research projection. It reuses the already-installed
``engine.strategy_signals`` candidates and the ``engine.validation`` cost/fill
engine rather than standing up a competing accounting or simulator service.

WHAT THIS IS NOT
----------------
It is NOT predictive validation, NOT a paper-trading loop, NOT a ranking, sizing
or execution authority, and NOT a promotion gate. The two candidates it reports
on (``tsmom_200``, ``rsi2_oversold``) are RESEARCH_ONLY research candidates, not
approved alpha. Every statistic it emits is a DESCRIPTIVE property of one
historical path; there is no held-out period, no purged/embargoed split and no
selection accounting, so none of it supports a claim that the rule predicts.

Three separations the contract keeps explicit:

  * historical simulation  != prospective evidence != capital eligibility
    (``historical`` is descriptive, ``prospective`` is ``not_started`` with zero
    registered and zero graded records, ``capital_eligible`` is always false);
  * capacity is NEVER claimed. Impact/capacity certification is disabled in this
    engine (see ``engine.validation.IMPACT_NOT_QUALIFIED``); a requested AUM/ADV
    conclusion is ``CapacityBlocked``, and missing ADV never degrades to "zero
    impact", which is a claim of unlimited size;
  * a metric that cannot be computed is ``null`` with a stated reason. It is
    never an invented ``0.0``.

TIMESTAMP LAW
-------------
Every receipt timestamp is TIMEZONE-AWARE and normalised to UTC before anything
compares it. A naive timestamp is refused, and so is a BARE DATE: "2026-10-22"
is ambiguous between an instant and a session label, and silently picking one of
them is how the same cutoff stops meaning the same thing. Session labels in the
price frames stay EXCHANGE dates (a daily bar is labelled by its NYSE session
date, not by its UTC arrival time), and that is the only place a naive date is
legitimate.

A full daily OHLC bar cannot be knowable before that session's close, so an
``available_at`` earlier than 16:00 ET on its own session date is refused.

Nothing here reconstructs historical KNOWABILITY from a current capture. The
receipt is asserted by the caller and taken at its word; this engine verifies
internal consistency only. ``CURRENT_VINTAGE_LIMITATION`` says so in the output.

AGGREGATION LAW
---------------
Names are NEVER pooled as independent samples, and returns are NEVER averaged
across names. Each admitted name gets its OWN subaccount starting from the SAME
initial capital; the portfolio equity curve is the MEAN of the subaccount NAV
curves, and portfolio returns are DERIVED from that mean curve. Averaging each
day's per-name returns would quietly rebalance between assets for free on every
date, which is a leverage and correlation the contract does not have. There are
no transfers between subaccounts, ever.

Turnover is the SAMPLE TOTAL of ACTUAL traded notional over contemporaneous
portfolio pre-trade equity, summed over the reported sample.

CALENDAR LAW
------------
The supported contract is US cash daily bars. Session existence comes from the
repository's own ``lib.nyse_calendar`` — never a hand-rolled holiday list. A
missing INTERNAL market session is a blocking reason, and an invalid instrument
blocks the FULL cohort: quietly evaluating on whatever names survived would
present a reduced universe as if it were the declared one.

WARMUP LAW
----------
Warmup is ACTUAL leading feature availability: the count of sessions from the
start of a name's history until its candidate feature is first finite. Nothing is
called "dropped" unless rows were really removed. Evaluation starts only once
the feature is valid for EVERY admitted name, and the reported sample window is
the window actually evaluated.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from engine import strategy_signals as _sig
from engine.validation import (
    CapacityBlocked,
    IMPACT_NOT_QUALIFIED,
    NextOpenError,
    TERMINAL_MARK_UNLIQUIDATED,
    next_open_sim,
)
from lib import nyse_calendar as _cal

SCHEMA = "systematic_research.v1"

#: The frozen candidate identities. Sorted so the emitted identity order is
#: stable regardless of registry order or dict iteration.
CANDIDATE_KEYS: tuple[str, ...] = ("rsi2_oversold", "tsmom_200")

#: Sessions per year used to annualize. EXPLICIT, not inferred from a guess about
#: the sampling cadence; every caller must state it or accept the declared 252.
DEFAULT_SESSIONS_PER_YEAR = 252

#: Minimum common-history sessions before any statistic is reported. Below this
#: the candidate reports blocked with nulls rather than a number off a handful of
#: observations. This is a sample-sufficiency floor for HONESTY, not a
#: performance threshold: there is no Sharpe gate anywhere in this module.
MIN_COMMON_SESSIONS = 30

#: The regular US cash equity close. A FULL daily OHLC bar does not exist before
#: this instant, so it is the floor for when its session can be knowable.
SESSION_CLOSE_ET = time(16, 0)

#: The interval a reported return is measured over. ``ret[t]`` is the return
#: earned by the position held from ``open[t]`` to ``open[t+1]``; it is not a
#: prediction about any future outcome, and the index is the INTERVAL-OPENING
#: session, never the session whose close produced the decision.
RETURN_INTERVAL = "open[t]->open[t+1]"

_REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")

_DESCRIPTIVE_NOT_VALIDATION = (
    "Historical statistics are DESCRIPTIVE of one simulated path over one "
    "sample. They are not held-out validation: this module runs no purged or "
    "embargoed split, no untouched test period and no selection accounting, so "
    "no figure here supports a claim that the candidate predicts."
)
_NO_PROMOTION_RULE = (
    "No Sharpe, CAGR or drawdown threshold exists in this engine and none is "
    "implied by these numbers. There is no universal pass mark; promotion "
    "requires prospective evidence held by the existing owner, not a statistic."
)
_NO_PROJECTION = (
    "net_cagr is the CAGR REALISED on the historical path that was simulated. "
    "It is not a projection, a forecast or an expected future return."
)
_CURRENT_VINTAGE_LIMITATION = (
    "CURRENT-VINTAGE RECONSTRUCTION: the price history is reconstructed from a "
    "capture taken now, so historical KNOWABILITY is asserted by the receipt, "
    "not independently proven here. This engine verifies internal consistency "
    "(ordering, timing, calendar, basis) and does NOT certify that each bar was "
    "genuinely available at the moment it claims."
)
_PRICE_BASIS_LIMITATION = (
    "PRICE BASIS is declared per column, not qualified. Agreement of the "
    "adjustment basis across open/high/low/close/volume is an internal "
    "consistency check; it is NOT a corporate-action qualification, and raw "
    "prices matching on column basis alone are not qualified split/dividend "
    "economics. Qualified source admission is owned by the caller's input "
    "bridge, not asserted here."
)
_CAPACITY_DISABLED = (
    "Capacity and market impact are NOT modelled and NOT certified. This engine "
    "runs an explicit flat one-way cost only; impact, capacity, borrow and "
    "funding costs are absent, so no size conclusion of any kind is available."
)
_LIQUIDITY_BLOCKED = (
    "Capacity is BLOCKED: liquidity is missing or non-positive, so no size "
    "conclusion is available. This is recorded as blocked rather than as zero "
    "impact, which would wrongly claim unlimited size."
)
_UNIVERSE = (
    "Universe is the supplied instrument list only. It is not a "
    "delisting-complete or point-in-time membership-correct universe, so "
    "survivorship bias is present and not corrected."
)
_HORIZON_NOT_PROOF = (
    "The candidate's horizon is a RULE PARAMETER, not evidence that the sample "
    "holds that many independent observations. Overlapping horizons mean the "
    "effective independent-sample count is below the session count, and this "
    "engine does not claim otherwise."
)
_NO_TUNING = (
    "Candidate parameters are the installed registry's own fixed defaults "
    "(tsmom_200 200dma; rsi2_oversold RSI(2)<10 in an uptrend, 5-session hold). "
    "Nothing here was tuned, and no candidate was selected on this sample."
)


# --------------------------------------------------------------------------- #
# timestamps — aware only, normalised to UTC
# --------------------------------------------------------------------------- #
_BARE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _aware_utc(value: Any, name: str) -> pd.Timestamp:
    """Parse a receipt timestamp into UTC, REFUSING naive and bare-date inputs.

    A bare date is ambiguous between an instant and a session label. The prior
    implementation resolved it by guessing "the end of that day" after discarding
    the offset, which made two spellings of the SAME instant compare unequal and
    made a midnight cutoff silently drop every same-day observation.
    """
    text = str(value).strip()
    if _BARE_DATE.fullmatch(text):
        raise ValueError(
            f"{name}_must_be_a_timezone_aware_iso_timestamp_not_a_bare_date:{text}")
    try:
        ts = pd.Timestamp(text)
    except Exception as exc:                       # noqa: BLE001 - re-raised as a contract error
        raise ValueError(f"{name}_is_not_a_parseable_timestamp:{text}") from exc
    if ts.tzinfo is None:
        raise ValueError(
            f"{name}_must_be_timezone_aware_offending_value:{text}")
    return ts.tz_convert("UTC")


def _cutoff(as_of: str) -> pd.Timestamp:
    """Resolve the point-in-time cutoff to an aware UTC instant.

    Aware timestamps naming the same instant are equal no matter which offset
    they are written in. Naive input and bare dates are refused rather than
    guessed at.
    """
    return _aware_utc(as_of, "as_of")


def _session_close_utc(session_date: Any) -> pd.Timestamp:
    """The 16:00 ET close of a session, as an aware UTC instant."""
    d = pd.Timestamp(session_date).date()
    return pd.Timestamp(datetime.combine(d, SESSION_CLOSE_ET, tzinfo=_cal.ET)).tz_convert("UTC")


# --------------------------------------------------------------------------- #
# input contract
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PriceFrame:
    """One instrument's daily prices plus the metadata that makes it knowable.

    ``frame``      OHLCV indexed by EXCHANGE session dates (naive, normalised).
                   A session label is a date, never a UTC arrival instant.
    ``available_at`` when each observation became knowable, TIMEZONE-AWARE and
                   normalised to UTC. Rows whose ``available_at`` is after the
                   cutoff are EXCLUDED, which is what makes appending future bars
                   unable to change history.
    ``adjustment_basis`` a single string applied to every price/volume column,
                   or a per-column mapping. When a mapping is given every value
                   must agree — an unadjusted open against an adjusted close is
                   an unreproducible fill, not a default. Agreement is an internal
                   consistency check, NOT a corporate-action qualification.
    ``sessions_per_year`` explicit sampling cadence for annualisation.
    ``synthetic`` marks a fixture. Synthetic inputs are LABELLED, never
                    presented as an observation of a real instrument.
    """
    frame: pd.DataFrame
    available_at: pd.Series
    adjustment_basis: str | Mapping[str, str]
    sessions_per_year: int = DEFAULT_SESSIONS_PER_YEAR
    synthetic: bool = False
    source: str = ""
    ticker: str = ""
    notes: Sequence[str] = field(default_factory=tuple)


def _as_frame_mapping(frames: Any) -> dict[str, PriceFrame]:
    """Accept either {ticker: PriceFrame} or {ticker: DataFrame-with-attrs}.

    The DataFrame form keeps small fixtures readable: ``available_at`` may be a
    column, and the declaration lives in ``df.attrs``.
    """
    if not isinstance(frames, Mapping):
        raise TypeError("frames must be a mapping of ticker -> PriceFrame")
    out: dict[str, PriceFrame] = {}
    for ticker, value in frames.items():
        if isinstance(value, PriceFrame):
            out[str(ticker)] = value
            continue
        df = value.copy()
        attrs = dict(getattr(df, "attrs", {}) or {})
        available = df["available_at"] if "available_at" in df.columns else attrs.get("available_at")
        if available is None:
            out[str(ticker)] = PriceFrame(
                frame=df, available_at=pd.Series(dtype="datetime64[ns, UTC]"),
                adjustment_basis=attrs.get("adjustment_basis", ""), ticker=str(ticker),
            )
            continue
        out[str(ticker)] = PriceFrame(
            frame=df.drop(columns=["available_at"]),
            available_at=pd.Series(available, index=df.index).copy(),
            adjustment_basis=attrs.get("adjustment_basis", ""),
            sessions_per_year=int(attrs.get("sessions_per_year", DEFAULT_SESSIONS_PER_YEAR)),
            synthetic=bool(attrs.get("synthetic", False)),
            source=str(attrs.get("source", "")),
            ticker=str(ticker),
            notes=tuple(attrs.get("notes", ()) or ()),
        )
    return out


# --------------------------------------------------------------------------- #
# validation — every failure yields a stable reason string, never a zero
# --------------------------------------------------------------------------- #
def _basis_agrees(basis: str | Mapping[str, str]) -> tuple[bool, str | None]:
    """True only when every price/volume column declares the SAME basis."""
    if isinstance(basis, Mapping):
        declared = {col: str(basis.get(col, "")).strip() for col in _REQUIRED_COLUMNS}
        if any(not v for v in declared.values()):
            missing = sorted(c for c, v in declared.items() if not v)
            return False, f"adjustment_basis_not_declared_for_{','.join(missing)}"
        distinct = sorted(set(declared.values()))
        if len(distinct) != 1:
            return False, f"mixed_adjustment_basis:{','.join(distinct)}"
        return True, None
    text = str(basis).strip()
    if not text:
        return False, "adjustment_basis_not_declared"
    return True, None


def _available_series(values: pd.Series, index: pd.DatetimeIndex
                      ) -> tuple[pd.Series, np.ndarray]:
    """Coerce declared availability into an aware UTC Series plus a naive mask.

    A naive receipt names an ambiguous instant. Normalising it by ASSUMING UTC
    would invent a knowability fact the writer never stated, so it is reported
    and the caller blocks the instrument. Values that cannot be parsed come back
    as NaT, which blocks too: unknown availability is never assumed knowable.
    """
    raw = pd.Series(values).copy()
    raw.index = pd.RangeIndex(len(raw))

    naive = np.zeros(len(raw), dtype=bool)
    try:
        probe = pd.to_datetime(raw, errors="coerce")
    except Exception:                                  # noqa: BLE001 - fall through
        probe = None
    if isinstance(probe, pd.Series):
        dtype = str(probe.dtype)
        if dtype == "datetime64[ns]":
            naive[probe.notna().to_numpy()] = True      # uniformly naive
        elif not (dtype.startswith("datetime64[") and "UTC" not in dtype
                  and getattr(probe.dt, "tz", None) is not None):
            # Mixed offsets land here; check each element.
            for i, v in enumerate(raw.to_numpy()):
                try:
                    ts = pd.Timestamp(v)
                except Exception:                      # noqa: BLE001
                    continue
                if pd.notna(ts) and ts.tzinfo is None:
                    naive[i] = True

    as_utc = pd.to_datetime(raw, errors="coerce", utc=True)
    return pd.Series(as_utc.to_numpy(), index=index), naive


def validate_price_frame(pf: PriceFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame | None, list[str], dict]:
    """Return (usable frame, reasons, detail). A non-empty ``reasons`` means the
    instrument is EXCLUDED — it is never partially used.

    ORDER MATTERS: known-future rows are removed by availability BEFORE any price
    value is validated. Otherwise appending a bad future bar would change the
    reported history for an old cutoff, which is exactly the invariance this
    engine exists to provide.
    """
    reasons: list[str] = []
    detail: dict[str, Any] = {}
    df = pf.frame

    if not isinstance(df.index, pd.DatetimeIndex):
        return None, ["session_index_not_datetime"], detail
    if len(df) == 0:
        return None, ["frame_is_empty"], detail
    if not df.index.is_monotonic_increasing:
        reasons.append("session_index_not_chronological")
    if df.index.has_duplicates:
        reasons.append("session_index_not_unique")

    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return None, [f"missing_column_{','.join(missing)}"], detail

    ok, why = _basis_agrees(pf.adjustment_basis)
    if not ok:
        reasons.append(why)

    # --- availability must be fully declared, aware, and knowable after close ---
    available, naive_mask = _available_series(pf.available_at, df.index)
    if naive_mask.any():
        reasons.append("available_at_must_be_timezone_aware")
    if available.isna().all():
        reasons.append("available_at_not_declared")
        return None, reasons, detail
    if available.isna().any():
        reasons.append("available_at_not_declared_for_every_session")

    if not available.isna().any():
        closes = {d.date(): _session_close_utc(d) for d in df.index.unique()}
        floor = pd.Series([closes[pd.Timestamp(d).date()] for d in df.index],
                          index=df.index)
        early = available < floor
        if early.any():
            reasons.append(
                f"available_at_before_session_close_at_index_{int(np.flatnonzero(early.to_numpy())[0])}")

    detail["synthetic"] = bool(pf.synthetic)
    detail["sessions_per_year"] = int(pf.sessions_per_year)

    if reasons:
        return None, reasons, detail

    # --- point-in-time exclusion BEFORE price validation ---
    keep = (available <= as_of).to_numpy()
    dropped = int((~keep).sum())
    detail["future_rows_excluded"] = dropped
    clean = df[keep].copy()
    clean_available = available[keep]
    if len(clean) == 0:
        return None, ["no_observation_available_at_cutoff"], detail

    # --- now, and only now, validate the values that are actually in scope ---
    if not df.index.equals(pd.DatetimeIndex(df.index.normalize())):
        reasons.append("session_index_carries_a_time_of_day")

    for col in ("open", "high", "low", "close"):
        vals = pd.to_numeric(clean[col], errors="coerce").to_numpy(dtype=float)
        if (~np.isfinite(vals)).any():
            reasons.append(f"{col}_not_finite")
        elif (vals <= 0.0).any():
            reasons.append(f"{col}_not_positive")
    vol = pd.to_numeric(clean["volume"], errors="coerce").to_numpy(dtype=float)
    if (~np.isfinite(vol)).any():
        reasons.append("volume_not_finite")
    elif (vol < 0.0).any():
        reasons.append("volume_negative")

    # OHLC INEQUALITIES: a bar whose close sits outside its own high/low range is
    # not a bar. Positivity alone does not catch it.
    o = pd.to_numeric(clean["open"], errors="coerce").to_numpy(dtype=float)
    h = pd.to_numeric(clean["high"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(clean["low"], errors="coerce").to_numpy(dtype=float)
    c = pd.to_numeric(clean["close"], errors="coerce").to_numpy(dtype=float)
    if np.isfinite(o).all() and np.isfinite(h).all() and np.isfinite(low).all() \
            and np.isfinite(c).all():
        # Relative slack, so an ordinary float round-trip through CSV/parquet is
        # not reported as a malformed bar but a genuine violation still is.
        def _outside(value: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> bool:
            scale = np.maximum(np.maximum(np.abs(lo), np.abs(hi)), 1.0)
            slack = 1e-9 * scale
            return bool((value < lo - slack).any() or (value > hi + slack).any())

        if _outside(low, low, h):
            reasons.append("low_above_high")
        if _outside(o, low, h):
            reasons.append("open_outside_high_low_range")
        if _outside(c, low, h):
            reasons.append("close_outside_high_low_range")

    # --- exchange calendar: the supported contract is US cash daily bars ---
    dates = [pd.Timestamp(d).date() for d in clean.index]
    off_calendar = [d.isoformat() for d in dates if not _cal.is_session(d)]
    if off_calendar:
        reasons.append(f"row_on_non_market_session:{off_calendar[0]}")
    first, last = min(dates), max(dates)
    absent = _cal.missing_sessions(dates, first, last)
    if absent:
        reasons.append(
            f"missing_internal_market_sessions:{len(absent)}:first={absent[0].isoformat()}")

    if reasons:
        return None, reasons, detail

    detail["available_from"] = clean_available.min()
    detail["available_to"] = clean_available.max()
    detail["first_session"] = first.isoformat()
    detail["last_session"] = last.isoformat()
    detail["sessions"] = int(len(clean))
    return clean, [], detail


# --------------------------------------------------------------------------- #
# candidate features — reuse the installed strategies verbatim
# --------------------------------------------------------------------------- #
def _leading_nonfinite(values: np.ndarray) -> int:
    """Count LEADING non-finite entries of a FLOAT array.

    This is ACTUAL availability: sessions before the feature first exists. It is
    not a count of rows that were dropped — nothing is dropped here — and it is
    not the total number of NaNs, because an interior NaN is a different (worse)
    fact from a leading one.
    """
    finite = np.isfinite(values)
    idx = np.flatnonzero(finite)
    return int(idx[0]) if idx.size else int(values.size)


def _candidate_parts(df: pd.DataFrame, key: str) -> tuple[pd.Series, pd.Series | None]:
    """The candidate's own feature and RAW (pre-shift) position, from the registry.

    The registry entry's own ``signal`` callable is what produces both, so there
    is no second, competing implementation of either candidate.
    """
    strat = _sig.by_key()[key]
    feature, raw = strat.signal(df)
    feature = pd.Series(feature, index=df.index) if not isinstance(feature, pd.Series) else feature
    position = None if raw is None else pd.Series(raw, index=df.index, dtype=float)
    return feature, position


def candidate_raw_position(df: pd.DataFrame, key: str) -> tuple[pd.Series | None, int]:
    """The candidate's RAW (pre-shift) position plus its LEADING warmup length.

    A ``None`` position is reported, not replaced with zeros.

    The returned warmup is how many leading sessions have no finite feature — the
    real availability lag of the indicator, not a number of "dropped" rows.
    """
    feature, raw = _candidate_parts(df, key)
    vals = pd.to_numeric(feature, errors="coerce").to_numpy(dtype=float)
    return raw, _leading_nonfinite(vals)


def feature_available_from(df: pd.DataFrame, key: str) -> pd.Timestamp | None:
    """The first session at which the candidate's feature is finite, or ``None``."""
    feature, _ = _candidate_parts(df, key)
    ok = np.isfinite(pd.to_numeric(feature, errors="coerce").to_numpy(dtype=float))
    if not ok.any():
        return None
    return df.index[int(np.flatnonzero(ok)[0])]


# --------------------------------------------------------------------------- #
# statistics — null with a reason, never an invented zero
# --------------------------------------------------------------------------- #
def _sharpe(returns: pd.Series, ppy: int) -> float | None:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 3:
        return None
    sd = float(r.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0.0:
        return None                      # zero volatility -> Sharpe undefined, not 0
    value = float(r.mean()) / sd * math.sqrt(ppy)
    return value if np.isfinite(value) else None


def _cagr(returns: pd.Series, ppy: int) -> float | None:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 2:
        return None
    growth = float(np.prod(1.0 + r.to_numpy(dtype=float)))
    if not np.isfinite(growth) or growth <= 0.0:
        return None
    years = len(r) / float(ppy)
    if years <= 0.0:
        return None
    value = growth ** (1.0 / years) - 1.0
    return value if np.isfinite(value) else None


def _max_drawdown(returns: pd.Series) -> float | None:
    """Max drawdown of the NAV curve INCLUDING the initial capital of 1.0.

    The initial capital is a real part of the curve. Excluding it silently
    forgives a loss on the first bar, because a curve that only ever falls has
    its peak at the (unrecorded) starting point and would report a drawdown of 0.
    """
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 2:
        return None
    curve = np.concatenate(([1.0], np.cumprod(1.0 + r.to_numpy(dtype=float))))
    peak = np.maximum.accumulate(curve)
    if (peak <= 0).any():
        return None
    value = float(np.min(curve / peak - 1.0))
    return value if np.isfinite(value) else None


def _finite(value: float | None) -> float | None:
    """Round for stable serialisation; refuse to serialise a non-finite number."""
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    out = round(float(value), 6)
    return out if math.isfinite(out) else None


def _blocked(reason: str, limitations: list[str], cost_bps: float | None) -> dict:
    """One canonical unavailable row: nulls with a reason, never invented zeros."""
    row = {
        "state": "unavailable",
        "reason": reason,
        "sample_start": None,
        "sample_end": None,
        "observations": 0,
        "warmup_sessions": 0,
        "net_sharpe": None,
        "net_cagr": None,
        "max_drawdown": None,
        "turnover": None,
        "turnover_basis": "sample_total_traded_notional_over_portfolio_pretrade_equity",
        "benchmark_sharpe": None,
        "return_interval": RETURN_INTERVAL,
        "initial_capital_per_subaccount": 1.0,
        "limitations": sorted(set(limitations)),
    }
    # The cost assumption is part of every row's identity, INCLUDING a blocked one
    # where it was known, so a consumer can never read a null as "no cost".
    if cost_bps is not None and math.isfinite(float(cost_bps)):
        row["cost_bps"] = float(cost_bps)
    else:
        row["cost_bps"] = None
    return row


# --------------------------------------------------------------------------- #
# per-candidate historical evaluation
# --------------------------------------------------------------------------- #
def _portfolio_curve(sims: Mapping[str, dict], field: str) -> pd.Series:
    """The MEAN of the subaccount curves — one equal-initial-capital portfolio.

    Averaging RETURNS instead would rebalance between names for free on every
    date, which is free cross-asset leverage the contract never had. The
    subaccounts start from the same capital and never transfer between themselves.
    """
    frame = pd.DataFrame({t: s[field] for t, s in sims.items()})
    return frame.mean(axis=1)


def _evaluate_candidate(key: str, usable: dict[str, pd.DataFrame],
                        common: list[pd.Timestamp], ppy: int,
                        cost_bps: float, aum_usd: float | None,
                        impact_eta: float) -> dict:
    """Simulate one candidate over the COMMON window and describe the result."""
    strat = _sig.by_key()[key]
    limitations = [
        _DESCRIPTIVE_NOT_VALIDATION,
        _NO_PROMOTION_RULE,
        _NO_PROJECTION,
        _CURRENT_VINTAGE_LIMITATION,
        _PRICE_BASIS_LIMITATION,
        _CAPACITY_DISABLED,
        _UNIVERSE,
        _HORIZON_NOT_PROOF,
        _NO_TUNING,
        TERMINAL_MARK_UNLIQUIDATED,
        ("Each admitted name is an INDEPENDENT subaccount starting from the SAME "
         "initial capital of 1.0; the portfolio curve is the MEAN of the "
         "subaccount NAVs and portfolio returns are DERIVED from it. Returns are "
         "never averaged across names, which would rebalance between assets for "
         "free on every date. There are no transfers between subaccounts."),
        ("Names are not pooled as independent samples and per-name statistics are "
         "not averaged."),
        (f"Annualised at the declared {ppy} sessions/year; a reported return is "
         f"the {RETURN_INTERVAL} interval."),
    ]

    if not usable:
        return _blocked("no_usable_instrument",
                        limitations + ["No instrument survived input validation."],
                        cost_bps)

    # A requested AUM/ADV capacity conclusion is refused outright: the impact
    # model behind it is not qualified, so it is BLOCKED rather than certified
    # and rather than degraded to "no impact", which claims unlimited size.
    if aum_usd is not None:
        raise CapacityBlocked(IMPACT_NOT_QUALIFIED)

    window = pd.DatetimeIndex(common)
    if len(window) + 1 < MIN_COMMON_SESSIONS:
        return _blocked("common_history_too_short", limitations + [
            f"Common window holds {len(window)} sessions, below the "
            f"{MIN_COMMON_SESSIONS}-session sufficiency floor."], cost_bps)

    # Warm up each name on its FULL point-in-time history, then slice. Recomputing
    # on the truncated window would change the indicator values themselves.
    ready: dict[str, pd.Timestamp] = {}
    warmups: dict[str, int] = {}
    for ticker, df in sorted(usable.items()):
        feature, _ = _candidate_parts(df, key)
        vals = pd.to_numeric(feature, errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(vals)
        if not ok.any():
            return _blocked("feature_never_becomes_available", limitations + [
                f"{ticker}: the candidate feature is never finite on this history."],
                cost_bps)
        ready[ticker] = df.index[int(np.flatnonzero(ok)[0])]
        warmups[ticker] = _leading_nonfinite(vals)

    # Evaluate only once the feature is valid for EVERY admitted name.
    eval_from = max(ready.values())
    eval_window = window[window >= eval_from]
    warm_sessions = int(len(window) - len(eval_window))
    if len(eval_window) + 1 < MIN_COMMON_SESSIONS:
        return _blocked("history_after_warmup_too_short", limitations + [
            f"Only {len(eval_window)} sessions remain once the candidate feature "
            f"is valid for every admitted name, below the "
            f"{MIN_COMMON_SESSIONS}-session sufficiency floor."], cost_bps)

    sims: dict[str, dict] = {}
    bench_sims: dict[str, dict] = {}
    gross_ref: dict[str, dict] = {}
    contributors: list[str] = []
    for ticker, df in sorted(usable.items()):
        raw, _ = candidate_raw_position(df, key)
        if raw is None:
            continue
        sub = df.reindex(eval_window)
        if sub[["open", "close"]].isna().any().any():
            return _blocked("common_window_has_a_hole", limitations + [
                f"{ticker}: a session inside the common window carries no "
                f"open/close."], cost_bps)
        pos = raw.reindex(eval_window).to_numpy(dtype=float)
        if not np.isfinite(pos).all():
            return _blocked("position_not_finite_inside_the_sample", limitations + [
                f"{ticker}: the candidate position is not finite after warm-up, "
                f"so a bad fill would have to be read as flat."], cost_bps)
        ones = pd.Series(1.0, index=eval_window)
        try:
            sims[ticker] = next_open_sim(sub["open"], sub["close"],
                                         pd.Series(pos, index=eval_window),
                                         cost_bps=float(cost_bps))
            # The comparator shares EVERY convention: same cohort, same first
            # fillable open, same cost, same terminal mark. It cannot be filled
            # earlier than the strategy, because session 0 opens flat for both.
            bench_sims[ticker] = next_open_sim(sub["open"], sub["close"], ones,
                                               cost_bps=float(cost_bps))
            gross_ref[ticker] = next_open_sim(sub["open"], sub["close"], ones,
                                               cost_bps=0.0)
        except CapacityBlocked:
            raise
        except NextOpenError as exc:
            return _blocked(str(exc), limitations, cost_bps)
        contributors.append(ticker)

    if not sims:
        return _blocked("no_name_produced_a_valid_position", limitations + [
            "No supplied instrument produced a finite in-bounds position."], cost_bps)

    # ONE portfolio curve; every statistic below is read off it.
    portfolio_nav = _portfolio_curve(sims, "equity")
    span = slice(0, len(eval_window) - 1)
    net = portfolio_nav.iloc[1:].to_numpy(dtype=float) / \
        portfolio_nav.iloc[:-1].to_numpy(dtype=float) - 1.0
    net = pd.Series(net, index=eval_window[1:])

    bench_nav = _portfolio_curve(bench_sims, "equity")
    bench = pd.Series(bench_nav.iloc[1:].to_numpy(dtype=float) /
                      bench_nav.iloc[:-1].to_numpy(dtype=float) - 1.0,
                      index=eval_window[1:])
    gross_nav = _portfolio_curve(gross_ref, "equity")
    gross_reference = pd.Series(
        gross_nav.iloc[1:].to_numpy(dtype=float) /
        gross_nav.iloc[:-1].to_numpy(dtype=float) - 1.0, index=eval_window[1:])

    # SAMPLE TOTAL turnover: actual traded notional summed across subaccounts over
    # the CONTEMPORANEOUS portfolio pre-trade equity, summed over the sample.
    traded = pd.DataFrame({t: s["traded_notional"] for t, s in sims.items()}).sum(axis=1)
    pretrade = pd.DataFrame({t: s["pretrade_equity"] for t, s in sims.items()}).sum(axis=1)
    daily_turnover = (traded / pretrade).iloc[span]
    turnover = float(daily_turnover.sum())

    cost = pd.DataFrame({t: s["cost"] for t, s in sims.items()}).sum(axis=1)

    limitations.append(
        "Warm-up is ACTUAL leading feature availability, not a count of discarded "
        "rows — no row was removed from a name's history: "
        + ", ".join(f"{t}={warmups[t]}" for t in sorted(warmups))
        + f" leading sessions had no finite feature. Evaluation starts once the "
          f"feature is valid for EVERY admitted name, so {warm_sessions} leading "
          f"common-window sessions sit outside the reported sample.")
    limitations.append(
        "The benchmark is a fully-invested portfolio over the SAME cohort under "
        "IDENTICAL start, fill, cost and terminal conventions, so its excess is "
        "not inflated by an earlier fill. benchmark_gross_reference is the "
        "separate zero-cost GROSS reference and is labelled as such.")
    limitations.append(
        "turnover is the SAMPLE TOTAL of actual traded notional over "
        "contemporaneous portfolio pre-trade equity, summed over the reported "
        "sample. It is neither a per-name mean, a per-session mean, nor an "
        "annualised figure.")

    return {
        "state": "available",
        "reason": None,
        "sample_start": eval_window[0].date().isoformat(),
        "sample_end": eval_window[-1].date().isoformat(),
        "observations": int(net.notna().sum()),
        "warmup_sessions": warm_sessions,
        "net_sharpe": _finite(_sharpe(net, ppy)),
        "net_cagr": _finite(_cagr(net, ppy)),
        "max_drawdown": _finite(_max_drawdown(net)),
        "turnover": _finite(turnover),
        "turnover_basis": "sample_total_traded_notional_over_portfolio_pretrade_equity",
        "benchmark_sharpe": _finite(_sharpe(bench, ppy)),
        "benchmark_gross_sharpe": _finite(_sharpe(gross_reference, ppy)),
        "benchmark_convention": "identical_cohort_start_fill_cost_terminal",
        "total_cost_fraction": _finite(float(cost.sum())),
        "return_interval": RETURN_INTERVAL,
        "initial_capital_per_subaccount": 1.0,
        "cost_bps": float(cost_bps),
        "limitations": sorted(set(limitations)),
        "_capacity_note": _CAPACITY_DISABLED,
        "_instruments": sorted(contributors),
    }


# --------------------------------------------------------------------------- #
# report compiler
# --------------------------------------------------------------------------- #
def _assert_strict_finite(node: Any, path: str = "$") -> None:
    """Refuse to serialise NaN or +/-Infinity anywhere in the report."""
    if isinstance(node, float):
        if not math.isfinite(node):
            raise ValueError(f"non_finite_number_at_{path}")
    elif isinstance(node, dict):
        for key in node:
            _assert_strict_finite(node[key], f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for i, item in enumerate(node):
            _assert_strict_finite(item, f"{path}[{i}]")


def build_report(
    frames: Mapping[str, Any],
    *,
    as_of: str,
    generated_at: str,
    code_revision: str,
    data_revision: str,
    cost_bps: float,
    expected_last_session: str | None = None,
    sessions_per_year: int | None = None,
    aum_usd: float | None = None,
    impact_eta: float = 0.1,
) -> dict:
    """Compile the frozen ``systematic_research.v1`` report from PRELOADED frames.

    This function performs no I/O of any kind: it opens no file, no network
    connection, no account/QLedger store and no credential path, and it writes
    nothing. Every argument that could otherwise vary run to run is supplied
    explicitly, so identical inputs and identical arguments produce byte-identical
    JSON.

    ``as_of`` and ``generated_at`` are TIMEZONE-AWARE instants, normalised to
    UTC. A naive timestamp or a bare date is refused. ``generated_at`` must not
    precede ``as_of``.
    """
    cutoff = _cutoff(as_of)
    generated = _aware_utc(generated_at, "generated_at")
    if generated < cutoff:
        raise ValueError(
            f"generated_at_precedes_as_of:{generated.isoformat()}<{cutoff.isoformat()}")

    ppy = int(sessions_per_year or DEFAULT_SESSIONS_PER_YEAR)
    if ppy <= 0:
        raise ValueError("sessions_per_year_must_be_positive")
    if not math.isfinite(cost_bps) or cost_bps < 0.0:
        raise ValueError("cost_bps_must_be_finite_and_non_negative")

    code_rev = str(code_revision).strip()
    data_rev = str(data_revision).strip()
    if not code_rev or not data_rev:
        raise ValueError("code_revision_and_data_revision_must_both_be_non_empty")
    if code_rev == data_rev:
        raise ValueError("code_revision_and_data_revision_must_be_two_distinct_identities")

    loaded = _as_frame_mapping(frames)
    health_reasons: list[str] = []
    usable: dict[str, pd.DataFrame] = {}
    invalid: dict[str, list[str]] = {}
    synthetic_names: list[str] = []
    last_by_instrument: dict[str, str] = {}

    for ticker in sorted(loaded):
        pf = loaded[ticker]
        clean, reasons, detail = validate_price_frame(pf, cutoff)
        if reasons:
            invalid[ticker] = reasons
            health_reasons.extend(f"{ticker}:{r}" for r in reasons)
            continue
        usable[ticker] = clean
        last_by_instrument[ticker] = str(detail["last_session"])
        if detail.get("synthetic"):
            synthetic_names.append(ticker)

    seen_sessions: list[pd.Timestamp] = []
    for df in usable.values():
        seen_sessions.extend(list(df.index))
    last_session = max(seen_sessions).date().isoformat() if seen_sessions else None

    if not loaded:
        health_reasons.append("no_instrument_declared")
    if not usable:
        health_reasons.append("no_usable_instrument")

    # An invalid instrument blocks the FULL cohort. Quietly evaluating on the
    # survivors would present a reduced universe as the declared one.
    if invalid:
        health_reasons.append(
            "cohort_blocked_by_invalid_instrument:" + ",".join(sorted(invalid)))
        usable = {}

    # Freshness is EXPLICIT and PER-INSTRUMENT. A maximum across names hides a
    # stale name behind a fresh one.
    if expected_last_session is None:
        health_reasons.append("expected_last_session_not_declared")
    else:
        for ticker, got in sorted(last_by_instrument.items()):
            if got != expected_last_session:
                health_reasons.append(
                    f"{ticker}:last_session_{got}_does_not_match_expected_"
                    f"{expected_last_session}")

    if usable:
        # Shrink to the span EVERY name covers. This is a DISCLOSED window
        # reduction, not an intersection that could quietly drop a hole: each
        # name was already blocked above if its own span had a missing session.
        first = max(df.index.min() for df in usable.values())
        last = min(df.index.max() for df in usable.values())
        window = pd.date_range(first, last, freq="C") if first <= last \
            else pd.DatetimeIndex([])
        window = window[window.isin(set.intersection(*(set(df.index)
                                                       for df in usable.values())))]
        common_index = pd.DatetimeIndex(window)
    else:
        common_index = pd.DatetimeIndex([])

    capacity_blocked = False
    strategies: list[dict] = []
    for key in sorted(CANDIDATE_KEYS):
        strat = _sig.by_key()[key]
        blockers = [
            "candidates are RESEARCH_ONLY research candidates, not approved alpha",
            _DESCRIPTIVE_NOT_VALIDATION,
            "no prospective shadow record exists: prospective is not_started with "
            "zero registered and zero graded observations",
            "paper trading is not connected",
            _CAPACITY_DISABLED,
        ]
        try:
            hist = _evaluate_candidate(key, usable, list(common_index), ppy,
                                       float(cost_bps), aum_usd, float(impact_eta))
        except CapacityBlocked as exc:
            capacity_blocked = True
            reason = IMPACT_NOT_QUALIFIED if str(exc) == IMPACT_NOT_QUALIFIED else str(exc)
            health_reasons.append(f"capacity_blocked:{reason}")
            hist = _blocked(reason, [_CAPACITY_DISABLED, _DESCRIPTIVE_NOT_VALIDATION,
                                     _CURRENT_VINTAGE_LIMITATION], cost_bps)
        available = hist.get("state") == "available"
        if not available:
            # A candidate that could not be evaluated is a DATA-health fact, not
            # just a per-row annotation: reporting "available" while every
            # candidate is unavailable would be an inconsistent artifact.
            health_reasons.append(f"candidate_blocked:{key}:{hist.get('reason')}")
            blockers.insert(0, f"historical simulation unavailable: {hist.get('reason')}")
            blockers.append(
                "no valid point-in-time inputs for this candidate" if not capacity_blocked
                else "no capacity conclusion: impact model is not qualified")
        strategies.append({
            "id": key,
            "name": strat.name,
            "family": strat.family,
            "horizon_sessions": int(strat.horizon),
            "status": "research_only" if available else "blocked",
            "stance": "Observe only" if available else "Stand aside",
            "reason": (strat.thesis if available
                       else f"blocked: {hist.get('reason')}"),
            "historical": {k: v for k, v in hist.items() if not k.startswith("_")},
            "prospective": {"state": "not_started", "registered": 0, "graded": 0},
            "paper": {"state": "not_connected"},
            "capital_eligible": False,
            "blockers": sorted(set(blockers)),
            "invalidation": [
                "a prospective shadow record over a pre-registered window that "
                "does not reproduce the historical sign",
                "net-of-cost performance that stops being non-negative under a "
                "plausible higher cost assumption",
                "a common-history window shorter than the candidate's own horizon",
                "a data revision that changes the qualifying sessions or the "
                "declared adjustment basis",
            ],
            "instruments": sorted(hist.get("_instruments", [])) or sorted(loaded),
        })

    health_reasons = sorted(set(health_reasons))
    data_ready = not health_reasons

    root_limitations = [
        _DESCRIPTIVE_NOT_VALIDATION,
        _NO_PROMOTION_RULE,
        _NO_PROJECTION,
        _CURRENT_VINTAGE_LIMITATION,
        _PRICE_BASIS_LIMITATION,
        "Research simulation only. This engine holds no ranking, sizing, alert or "
        "execution authority and does not write orders or positions.",
        f"Annualised at the declared {ppy} sessions/year.",
    ]
    if synthetic_names:
        root_limitations.append(
            "SYNTHETIC FIXTURE INPUT for: " + ", ".join(sorted(synthetic_names))
            + ". Figures describe generated data and are not an observation of any "
              "real instrument.")
    # Capacity is never claimed, whether or not it was requested: a blocked
    # request is disclosed above through data_health, and an unrequested one is
    # simply not modelled.
    root_limitations.append(_CAPACITY_DISABLED)

    report = {
        "schema": SCHEMA,
        "generated_at": generated.isoformat(),
        "as_of": cutoff.isoformat(),
        "mode": "RESEARCH_ONLY",
        "live_orders_enabled": False,
        "status": "research_available" if data_ready else "inputs_blocked",
        "source": {"code_revision": code_rev,
                   "data_revision": data_rev},
        "metadata": {
            "synthetic": bool(synthetic_names),
            "synthetic_instruments": sorted(synthetic_names),
            "price_vintage": "current_capture",
            "knowability": "caller_asserted_receipt_not_independently_verified",
            "calendar": "NYSE_us_cash_daily",
            "return_interval": RETURN_INTERVAL,
            "cost_model": "explicit_flat_one_way_cost",
            "cost_bps": float(cost_bps),
            "terminal_convention": "mark_only_no_final_rebalance",
            "declared_instruments": sorted(loaded),
            "excluded_instruments": {t: sorted(r) for t, r in sorted(invalid.items())},
        },
        "summary": {
            "candidate_count": len(CANDIDATE_KEYS),
            "evaluated_count": sum(1 for s in strategies
                                    if s["historical"]["state"] == "available"),
            "capital_eligible_count": 0,
        },
        "strategies": strategies,
        "data_health": {"state": "ready" if data_ready else "blocked",
                        "reasons": health_reasons, "last_session": last_session,
                        "last_session_by_instrument": last_by_instrument},
        "limitations": sorted(set(root_limitations)),
    }

    _assert_strict_finite(report)
    return report


def dumps(report: Mapping[str, Any]) -> str:
    """Deterministic JSON text: fixed separators, no NaN/Infinity tokens ever."""
    import json

    _assert_strict_finite(report)
    return json.dumps(report, indent=2, sort_keys=False, allow_nan=False,
                      ensure_ascii=False) + "\n"


__all__ = [
    "SCHEMA",
    "CANDIDATE_KEYS",
    "MIN_COMMON_SESSIONS",
    "DEFAULT_SESSIONS_PER_YEAR",
    "RETURN_INTERVAL",
    "SESSION_CLOSE_ET",
    "PriceFrame",
    "build_report",
    "validate_price_frame",
    "candidate_raw_position",
    "feature_available_from",
    "dumps",
]