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
  * capacity is only ever claimed when market impact was actually modelled. A
    missing or non-positive ADV BLOCKS the capacity conclusion — it never
    degrades to "zero impact", which would be a claim of unlimited size;
  * a metric that cannot be computed is ``null`` with a stated reason. It is
    never an invented ``0.0``.

AGGREGATION LAW
---------------
Names are NEVER pooled as independent samples. Per-name Sharpe ratios are not
averaged and no name-level statistic is treated as a draw. Instead every name is
simulated over one COMMON session window and the statistics are computed from a
single equal-weight portfolio return series built from that window. A name whose
history does not reach the common window shrinks the window for everyone, rather
than contributing a shorter, flattering sample.

TIMING LAW
----------
Signals are closed-bar. An allocation decided from session t's close fills at
session t+1's OPEN via ``engine.validation.next_open_sim``; a holder who was
invested before that open keeps the overnight gap, and a post-close entrant does
not receive it. Costs are charged on actual traded notional, including the
initial buy and every sale. Terminal holdings are marked, not liquidated, and
that convention is disclosed rather than buried.

SIDE-EFFECT LAW
---------------
Import performs no I/O. This module opens no network connection, reads no
account, QLedger, credential or allocation file, and writes nothing. Publication
belongs to the caller, which must name an explicit output path.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from engine import strategy_signals as _sig
from engine.validation import (
    CapacityBlocked,
    NextOpenError,
    TERMINAL_MARK_UNLIQUIDATED,
    next_open_sim,
)

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

_ADV_WINDOW = 21

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
_LIQUIDITY_BLOCKED = (
    "Capacity is BLOCKED: liquidity is missing or non-positive, so no size "
    "conclusion is available. This is recorded as blocked rather than as zero "
    "impact, which would wrongly claim unlimited size."
)
_CAPACITY_NOT_MODELLED = (
    "Capacity is NOT modelled: no AUM/impact request was supplied, so this "
    "module makes no capacity claim at all."
)
_UNIVERSE = (
    "Universe is the supplied instrument list only. It is not a "
    "delisting-complete or point-in-time membership-correct universe, so "
    "survivorship bias is present and not corrected."
)


# --------------------------------------------------------------------------- #
# input contract
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PriceFrame:
    """One instrument's daily prices plus the metadata that makes it knowable.

    ``frame``      OHLCV indexed by unique, chronological session dates.
    ``available_at`` when each observation became knowable. Rows whose
                   ``available_at`` is after the cutoff are EXCLUDED, which is
                   what makes appending future bars unable to change history.
    ``adjustment_basis`` a single string applied to every price/volume column,
                   or a per-column mapping. When a mapping is given every value
                   must agree — an unadjusted open against an adjusted close is
                   an unreproducible fill, not a default.
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
                frame=df, available_at=pd.Series(dtype="datetime64[ns]"),
                adjustment_basis=attrs.get("adjustment_basis", ""), ticker=str(ticker),
            )
            continue
        out[str(ticker)] = PriceFrame(
            frame=df.drop(columns=["available_at"]),
            available_at=pd.Series(available, index=df.index),
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


def validate_price_frame(pf: PriceFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame | None, list[str], dict]:
    """Return (usable frame, reasons, detail). A non-empty ``reasons`` means the
    instrument is EXCLUDED — it is never partially used."""
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

    available = pd.to_datetime(pd.Series(pf.available_at).reindex(df.index), errors="coerce")
    if available.isna().all():
        reasons.append("available_at_not_declared")
    elif available.isna().any():
        reasons.append("available_at_not_declared_for_every_session")

    # observation-before-availability: nothing may be knowable before it happened
    if not available.isna().any():
        early = available < pd.Series(df.index, index=df.index)
        if early.any():
            reasons.append("available_at_before_observation")

    for col in ("open", "high", "low", "close"):
        vals = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        if (~np.isfinite(vals)).any():
            reasons.append(f"{col}_not_finite")
        elif (vals <= 0.0).any():
            reasons.append(f"{col}_not_positive")
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(dtype=float)
    if (~np.isfinite(vol)).any():
        reasons.append("volume_not_finite")
    elif (vol < 0.0).any():
        reasons.append("volume_negative")

    detail["synthetic"] = bool(pf.synthetic)
    detail["sessions_per_year"] = int(pf.sessions_per_year)

    if reasons:
        return None, reasons, detail

    # Point-in-time exclusion. A bar that was not yet knowable at the cutoff
    # cannot enter a cutoff — this is what makes appending future data inert.
    keep = available <= as_of
    dropped = int((~keep).sum())
    detail["future_rows_excluded"] = dropped
    if dropped:
        clean = df[keep.to_numpy()].copy()
        clean_available = available[keep.to_numpy()]
    else:
        clean = df.copy()
        clean_available = available
    if len(clean) == 0:
        return None, ["no_observation_available_at_cutoff"], detail
    detail["available_from"] = clean_available.min()
    detail["available_to"] = clean_available.max()
    return clean, [], detail


# --------------------------------------------------------------------------- #
# candidate features — reuse the installed strategies verbatim
# --------------------------------------------------------------------------- #
def candidate_raw_position(df: pd.DataFrame, key: str) -> tuple[pd.Series | None, int]:
    """The candidate's RAW (pre-shift) position plus its warmup length.

    The registry entry's own ``signal`` callable is what produces the tradable
    series, so there is no second, competing implementation of either candidate.
    A ``None`` position is reported, not replaced with zeros.
    """
    strat = _sig.by_key()[key]
    feature, raw = strat.signal(df)
    feature = pd.Series(feature, index=df.index) if not isinstance(feature, pd.Series) else feature
    finite = np.isfinite(pd.to_numeric(feature, errors="coerce").to_numpy(dtype=float))
    warmup = int((~finite).sum())
    if raw is None:
        return None, warmup
    return pd.Series(raw, index=df.index, dtype=float), warmup


# --------------------------------------------------------------------------- #
# statistics — null with a reason, never an invented zero
# --------------------------------------------------------------------------- #
def _sharpe(returns: pd.Series, ppy: int) -> float | None:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 3:
        return None
    sd = float(r.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0.0:
        return None
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
    r = pd.to_numeric(returns, errors="coerce").dropna()
    if len(r) < 2:
        return None
    curve = np.cumprod(1.0 + r.to_numpy(dtype=float))
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


# --------------------------------------------------------------------------- #
# per-candidate historical evaluation
# --------------------------------------------------------------------------- #
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
        _UNIVERSE,
        TERMINAL_MARK_UNLIQUIDATED,
        ("Aggregate is an EQUAL-WEIGHT portfolio over one COMMON session window; "
         "names are not pooled as independent samples and per-name statistics are "
         "not averaged."),
        f"Annualised at the declared {ppy} sessions/year.",
    ]
    if not usable:
        return {"state": "unavailable", "reason": "no_usable_instrument",
                "sample_start": None, "sample_end": None, "observations": 0,
                "net_sharpe": None, "net_cagr": None, "max_drawdown": None,
                "turnover": None, "benchmark_sharpe": None,
                "limitations": limitations + ["No instrument survived input validation."]}

    window = pd.DatetimeIndex(common)
    needed = len(window) + 1                      # +1: the terminal-mark session
    if needed < MIN_COMMON_SESSIONS:
        return {"state": "unavailable", "reason": "common_history_too_short",
                "sample_start": None, "sample_end": None, "observations": 0,
                "net_sharpe": None, "net_cagr": None, "max_drawdown": None,
                "turnover": None, "benchmark_sharpe": None,
                "limitations": limitations + [
                    f"Common window holds {len(window)} sessions, below the "
                    f"{MIN_COMMON_SESSIONS}-session sufficiency floor."]}

    # Warm up each name on its FULL point-in-time history, then slice. Recomputing
    # on the truncated window would change the indicator values themselves.
    warmups: dict[str, int] = {}
    for ticker, df in sorted(usable.items()):
        _, warmup = candidate_raw_position(df, key)
        warmups[ticker] = warmup

    per_name_ret: list[pd.Series] = []
    per_name_gross: list[pd.Series] = []
    per_name_bench: list[pd.Series] = []
    turnovers: list[float] = []
    contributors: list[str] = []
    adv_series: dict[str, pd.Series] = {}

    for ticker, df in sorted(usable.items()):
        raw, _ = candidate_raw_position(df, key)
        if raw is None:
            continue
        sub = df.reindex(window)
        if sub["open"].isna().any() or sub["close"].isna().any():
            continue
        pos = raw.reindex(window).to_numpy(dtype=float)
        if not np.isfinite(pos).all():
            continue                                   # never coerce a bad fill to flat
        opens = sub["open"]
        closes = sub["close"]
        try:
            sim = next_open_sim(
                opens, closes, pd.Series(pos, index=window), cost_bps=cost_bps,
                dollar_adv=(opens * sub["volume"]).rolling(_ADV_WINDOW, min_periods=1).median()
                if aum_usd is not None else None,
                aum_usd=aum_usd, impact_eta=impact_eta,
            )
        except CapacityBlocked:
            raise
        except NextOpenError:
            continue
        per_name_ret.append(sim["ret"])
        per_name_gross.append(sim["gross_ret"])
        per_name_bench.append(sim["benchmark_open_to_open"])
        turnovers.extend(float(v) for v in sim["turnover"].to_numpy(dtype=float))
        adv_series[ticker] = sim["capacity"]
        contributors.append(ticker)

    if not per_name_ret:
        return {"state": "unavailable", "reason": "no_name_produced_a_valid_position",
                "sample_start": None, "sample_end": None, "observations": 0,
                "net_sharpe": None, "net_cagr": None, "max_drawdown": None,
                "turnover": None, "benchmark_sharpe": None,
                "limitations": limitations + [
                    "No supplied instrument produced a finite in-bounds position."]}

    # ONE equal-weight series; every statistic below is read off it.
    net = pd.concat(per_name_ret, axis=1).mean(axis=1)
    bench = pd.concat(per_name_bench, axis=1).mean(axis=1)
    observations = int(net.notna().sum())

    capacity_limit = _CAPACITY_NOT_MODELLED
    if aum_usd is None:
        limitations.append(_CAPACITY_NOT_MODELLED)
    else:
        statuses = {c["status"] for c in adv_series.values()}
        if statuses == {"ready"}:
            limitations.append(
                "Market impact is modelled at the declared AUM, so a size "
                "sensitivity is available in the simulator; it is still not a "
                "capital authorisation.")
        else:
            limitations.append(_LIQUIDITY_BLOCKED)
            capacity_limit = _LIQUIDITY_BLOCKED

    warm_note = ("Warm-up dropped from each name's head: "
                 + ", ".join(f"{t}={warmups[t]}" for t in sorted(warmups)) + ".")
    limitations.append(warm_note)

    return {
        "state": "available",
        "reason": None,
        "sample_start": window[0].date().isoformat(),
        "sample_end": window[-1].date().isoformat(),
        "observations": observations,
        "net_sharpe": _finite(_sharpe(net, ppy)),
        "net_cagr": _finite(_cagr(net, ppy)),
        "max_drawdown": _finite(_max_drawdown(net)),
        "turnover": _finite(float(np.mean(turnovers))) if turnovers else None,
        "benchmark_sharpe": _finite(_sharpe(bench, ppy)),
        "limitations": sorted(set(limitations)),
        "_capacity_note": capacity_limit,
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


def _cutoff(as_of: str) -> pd.Timestamp:
    """Resolve the point-in-time cutoff.

    A BARE DATE means "everything knowable through the CLOSE of that date", so it
    resolves to the last nanosecond of that day. A full timestamp is honoured as
    the instant it names, which is what an intraday cutoff needs. Without this
    rule a daily bar available at 21:00 on the cutoff date would be excluded by a
    midnight cutoff, and every same-day observation would silently vanish.
    """
    ts = pd.Timestamp(as_of)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of).strip()):
        ts = ts + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    return ts


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

    ``as_of`` is a point-in-time CUTOFF: a bare date resolves to that day's close
    (see ``_cutoff``); anything with a time component is honoured as that instant.
    """
    cutoff = _cutoff(as_of)
    ppy = int(sessions_per_year or DEFAULT_SESSIONS_PER_YEAR)
    if ppy <= 0:
        raise ValueError("sessions_per_year_must_be_positive")
    if not math.isfinite(cost_bps) or cost_bps < 0.0:
        raise ValueError("cost_bps_must_be_finite_and_non_negative")

    loaded = _as_frame_mapping(frames)
    usable: dict[str, pd.DataFrame] = {}
    health_reasons: list[str] = []
    seen_sessions: list[pd.Timestamp] = []
    synthetic_names: list[str] = []

    for ticker in sorted(loaded):
        pf = loaded[ticker]
        clean, reasons, detail = validate_price_frame(pf, cutoff)
        if reasons:
            health_reasons.extend(f"{ticker}:{r}" for r in reasons)
            continue
        usable[ticker] = clean
        seen_sessions.extend(list(clean.index))
        if detail.get("synthetic"):
            synthetic_names.append(ticker)

    last_session = (max(seen_sessions).date().isoformat() if seen_sessions else None)

    # Freshness is an EXPLICIT contract. This module never guesses whether a gap
    # is a weekend, a holiday or a stale feed, and never asserts freshness it was
    # not told about.
    if not usable:
        health_reasons.append("no_usable_instrument")
    if expected_last_session is None:
        health_reasons.append("expected_last_session_not_declared")
    elif last_session is not None and last_session != expected_last_session:
        health_reasons.append(
            f"last_session_{last_session}_does_not_match_expected_"
            f"{expected_last_session}")

    # Finalised AFTER the candidate loop, because a requested impact/capacity
    # conclusion that the liquidity input cannot support is itself a data-health
    # failure (see the CapacityBlocked handler below).
    if usable:
        common = sorted(set.intersection(*(set(df.index) for df in usable.values())))
        common_index = pd.DatetimeIndex(common)
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
        ]
        try:
            hist = _evaluate_candidate(key, usable, list(common_index), ppy,
                                       float(cost_bps), aum_usd, float(impact_eta))
        except CapacityBlocked as exc:
            capacity_blocked = True
            # A requested impact/capacity conclusion that the liquidity input
            # cannot support is a DATA-health failure, not a quiet downgrade to
            # zero impact. It blocks the whole requested evaluation.
            health_reasons.append(f"capacity_blocked:{exc}")
            hist = {"state": "unavailable", "reason": str(exc),
                    "sample_start": None, "sample_end": None, "observations": 0,
                    "net_sharpe": None, "net_cagr": None, "max_drawdown": None,
                    "turnover": None, "benchmark_sharpe": None,
                    "limitations": [_LIQUIDITY_BLOCKED, _DESCRIPTIVE_NOT_VALIDATION]}
        available = hist.get("state") == "available"
        if not available:
            blockers.insert(0, f"historical simulation unavailable: {hist.get('reason')}")
            blockers.append(_LIQUIDITY_BLOCKED if capacity_blocked
                            else "no valid point-in-time inputs for this candidate")
        strategies.append({
            "id": key,
            "name": strat.name,
            "family": strat.family,
            "horizon_sessions": int(strat.horizon),
            "status": "research_only" if available else "blocked",
            "stance": "Observe only",
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
            "instruments": sorted(hist.get("_instruments", sorted(usable))),
        })

    health_reasons = sorted(set(health_reasons))
    data_ready = not health_reasons

    root_limitations = [
        _DESCRIPTIVE_NOT_VALIDATION,
        _NO_PROMOTION_RULE,
        _NO_PROJECTION,
        "Research simulation only. This engine holds no ranking, sizing, alert or "
        "execution authority and does not write orders or positions.",
        f"Annualised at the declared {ppy} sessions/year.",
    ]
    if synthetic_names:
        root_limitations.append(
            "SYNTHETIC FIXTURE INPUT for: " + ", ".join(sorted(synthetic_names))
            + ". Figures describe generated data and are not an observation of any "
              "real instrument.")
    if capacity_blocked:
        root_limitations.append(_LIQUIDITY_BLOCKED)
    elif aum_usd is None:
        root_limitations.append(_CAPACITY_NOT_MODELLED)

    report = {
        "schema": SCHEMA,
        "generated_at": str(generated_at),
        "as_of": str(as_of),
        "mode": "RESEARCH_ONLY",
        "live_orders_enabled": False,
        "status": "research_available" if data_ready else "inputs_blocked",
        "source": {"code_revision": str(code_revision),
                   "data_revision": str(data_revision)},
        "summary": {
            "candidate_count": len(CANDIDATE_KEYS),
            "evaluated_count": sum(1 for s in strategies
                                    if s["historical"]["state"] == "available"),
            "capital_eligible_count": 0,
        },
        "strategies": strategies,
        "data_health": {"state": "ready" if data_ready else "blocked",
                        "reasons": health_reasons, "last_session": last_session},
        "limitations": root_limitations,
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
    "PriceFrame",
    "build_report",
    "validate_price_frame",
    "candidate_raw_position",
    "dumps",
]