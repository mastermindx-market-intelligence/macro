"""Descriptive COT projection over canonical exact-contract source frames.

No forecasts, execution permissions, ranking, portfolio sizing or trade signals.
History is latest-revised source context with explicit observed-version clocks.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Callable

import numpy as np
import pandas as pd

from lib import store
from lib.cot_contracts import COHORT_FIELDS, DATASETS, MARKETS, Market, store_name
from lib.cot_publication import NY, PUBLICATION_DATES, available_at, scheduled_release, utc_timestamp

SCHEMA = "cot_snapshot.v1"
LOOKBACK = 156
MIN_HISTORY = 52
HISTORY_LIMIT = 208
AUTHORITY = {"can_rank": False, "can_size": False, "can_gate_entry": False, "can_trade": False}


def _number(value: object) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if np.isfinite(n) else None


def _instant(value: object) -> str | None:
    instant = utc_timestamp(value)
    return None if pd.isna(instant) else instant.isoformat()


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def percentile(series: pd.Series, *, lookback: int = LOOKBACK, minimum: int = MIN_HISTORY) -> tuple[float | None, int]:
    """Weekly endpoint-normalized empirical midrank; ties stay symmetric.

    Equal-value history = 50, minimum = 0 and maximum = 100 with unique tails.
    Missing current values never resurrect the previous report's score.
    """
    if series.empty or _number(series.iloc[-1]) is None:
        return None, 0
    window = pd.to_numeric(series.tail(lookback), errors="coerce")
    window = window[np.isfinite(window)]
    n = len(window)
    if n < max(2, minimum):
        return None, n
    current = float(window.iloc[-1])
    rank = ((window < current).sum() + 0.5 * ((window == current).sum() - 1)) / (n - 1)
    return round(float(rank) * 100, 2), n


def tier(score: float | None) -> dict:
    if score is None:
        return {"level": "unavailable", "relative_side": None}
    distance = min(score, 100 - score)
    level = "extreme" if distance <= 5 else "setup" if distance <= 10 else "watch" if distance <= 15 else "neutral"
    return {"level": level, "relative_side": ("low" if score < 50 else "high") if level != "neutral" else None}


def expected_report_date(now: pd.Timestamp) -> str | None:
    """Schedule expectation for a late flag, never proof a report was released."""
    local = now.tz_convert(NY).tz_localize(None).normalize()
    tuesday = local - pd.Timedelta(days=(local.weekday() - 1) % 7)
    candidates = []
    for weeks in range(16):
        day = tuesday - pd.Timedelta(weeks=weeks)
        # A Monday report can replace Tuesday; known exceptions are explicit.
        key = day.date().isoformat()
        prior = (day - pd.Timedelta(days=1)).date().isoformat()
        if prior in PUBLICATION_DATES and key not in PUBLICATION_DATES:
            key = prior
        if key in PUBLICATION_DATES:
            clock = (pd.Timestamp(PUBLICATION_DATES[key]) + pd.Timedelta(hours=15, minutes=30)).tz_localize(NY).tz_convert("UTC")
        else:
            clock = scheduled_release(day)
        if not pd.isna(clock) and clock <= now:
            candidates.append(key)
    return max(candidates) if candidates else None


def family_view(frame: pd.DataFrame | None, market: Market, family: str,
                now: pd.Timestamp) -> dict:
    result = {"family": family, "source_dataset": DATASETS[family], "state": "unavailable",
              "null_reason": "not_collected", "report_asof_date": None, "cohorts": {}, "history": []}
    if frame is None or frame.empty:
        return result
    required = {"cftc_contract_market_code", "report_family", "source_record_sha256", "open_interest", "version_observed_at"}
    if not required.issubset(frame.columns):
        result["null_reason"] = "source_contract_incomplete"
        return result
    if frame.index.has_duplicates or not frame["cftc_contract_market_code"].eq(market.code).all() or not frame["report_family"].eq(family).all():
        result["null_reason"] = "source_identity_conflict"
        return result
    frame = frame.sort_index()
    # The public projection needs at most 208 weekly rows, not every archived
    # year on every render. Filter future observation dates before taking tail.
    frame = frame.loc[frame.index <= pd.Timestamp(now.tz_convert(NY).date())].tail(HISTORY_LIMIT)
    eligible = [not pd.isna(t := available_at(row, report_date=date)) and t <= now for date, row in frame.iterrows()]
    frame = frame.loc[eligible]
    if frame.empty:
        result["null_reason"] = "no_observed_version_available"
        return result
    last = frame.iloc[-1]
    asof = frame.index[-1].date().isoformat()
    age = (now.tz_convert(NY).date() - frame.index[-1].date()).days
    expected = expected_report_date(now)
    state = "stale" if age > 12 else "awaiting_update" if expected and asof < expected else "current"
    oi = _number(last["open_interest"])
    if oi is None or oi <= 0:
        result["null_reason"] = "invalid_open_interest"
        return result
    result.update(state=state, null_reason=None, report_asof_date=asof,
                  report_age_days=age, expected_report_asof=expected,
                  open_interest=int(oi), version_observed_at=_instant(last["version_observed_at"]),
                  first_observed_at=_instant(last.get("first_observed_at")), revised_at=_instant(last.get("revised_at")),
                  source_record_sha256=_text(last["source_record_sha256"]),
                  source_response_sha256=_text(last.get("source_response_sha256")),
                  source_url=_text(last.get("source_url")), market_and_exchange_names=_text(last.get("market_and_exchange_names")),
                  availability_basis="observed_source_version", original_vintage_certified=False)
    for cohort in COHORT_FIELDS[family]:
        col = f"{cohort}_net_pct_oi"
        values = frame[col] if col in frame else pd.Series(dtype=float)
        score, n = percentile(values)
        net = _number(last.get(f"{cohort}_net"))
        last_pct = _number(last.get(col))
        change = None
        if len(frame) >= 2:
            previous = _number(frame.iloc[-2].get(f"{cohort}_net"))
            if previous is not None and net is not None:
                change = net - previous
        result["cohorts"][cohort] = {
            "long": _number(last.get(f"{cohort}_long")), "short": _number(last.get(f"{cohort}_short")),
            "spread": _number(last.get(f"{cohort}_spread")), "net": net, "net_pct_oi": last_pct,
            "change_since_previous_report": change,
            "previous_report_date": frame.index[-2].date().isoformat() if len(frame) > 1 else None,
            "percentile_156w": score, "history_observations": n,
            "score_null_reason": None if score is not None else "insufficient_or_missing_history",
            "absolute_side": None if net is None else "net_long" if net > 0 else "net_short" if net < 0 else "flat",
            "tier": tier(score),
        }
    for date, row in frame.tail(HISTORY_LIMIT).iterrows():
        result["history"].append({
            "report_asof_date": date.date().isoformat(),
            "version_observed_at": _instant(row.get("version_observed_at")),
            "open_interest": _number(row.get("open_interest")),
            "net_pct_oi": {c: _number(row.get(f"{c}_net_pct_oi")) for c in COHORT_FIELDS[family]},
        })
    result["history_basis"] = "latest_revised_context_not_original_vintage_replay"
    return result


def build_snapshot(*, now: object = None,
                   reader: Callable[[str, str], pd.DataFrame | None] = store.read) -> dict:
    clock = utc_timestamp(now if now is not None else datetime.now(timezone.utc))
    if pd.isna(clock):
        raise ValueError("COT snapshot requires an explicit UTC/offset instant")
    markets = []
    for market in MARKETS:
        families = {}
        for family in ("legacy", market.detail_family):
            try:
                frame = reader("cot", store_name(market.code, family))
                families[family] = family_view(frame, market, family, clock)
            except (ValueError, TypeError, KeyError, OSError):
                families[family] = {"family": family, "state": "unavailable", "null_reason": "source_read_failed", "cohorts": {}, "history": []}
        markets.append({"market_id": market.key, "cftc_code": market.code,
                        "name": market.name, "name_zh": market.name_zh,
                        "category": market.category, "contract_basis": "futures_only",
                        "families": families})
    counts = {state: sum(m["families"]["legacy"]["state"] == state for m in markets)
              for state in ("current", "stale", "awaiting_update", "unavailable")}
    out = {"schema": SCHEMA, "generated_at": clock.isoformat(), "authority": AUTHORITY.copy(),
           "coverage": {"expected_markets": len(MARKETS), **counts}, "markets": markets,
           "method": {"name": "weekly_endpoint_normalized_midrank", "window_reports": LOOKBACK,
                      "minimum_reports": MIN_HISTORY, "history_limit": HISTORY_LIMIT,
                      "bands": {"watch": [15, 85], "setup": [10, 90], "extreme": [5, 95]},
                      "is_trade_recommendation": False},
           "source_credit": "U.S. Commodity Futures Trading Commission (CFTC). Mastermind calculations.",
           "limitations": ["Weekly futures positions, not live flow or stock ownership.",
                           "Alternative report families are not additive exposures.",
                           "An extreme percentile is not a reversal forecast.",
                           "Historical charts are latest-revised; original-vintage replay is not certified."]}
    encoded = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False)
    out["content_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    return out


def validate_snapshot(snapshot: dict) -> None:
    """Validate the publication envelope before it becomes a path or output.

    A digest detects accidental corruption, not source authenticity. Raw CFTC
    provenance and the exact-contract parser remain the evidence authority.
    """
    import re

    if not isinstance(snapshot, dict) or snapshot.get('schema') != SCHEMA:
        raise ValueError('unsupported COT snapshot')
    digest = snapshot.get('content_sha256')
    if not isinstance(digest, str) or re.fullmatch(r'[a-f0-9]{64}', digest) is None:
        raise ValueError('invalid COT content digest')
    if snapshot.get('authority') != AUTHORITY:
        raise ValueError('COT publication cannot grant trading authority')
    rows = snapshot.get('markets')
    if not isinstance(rows, list) or len(rows) != len(MARKETS):
        raise ValueError('incomplete COT market denominator')
    expected = {(m.key, m.code) for m in MARKETS}
    try:
        actual = {(m['market_id'], m['cftc_code']) for m in rows}
    except (TypeError, KeyError) as exc:
        raise ValueError('malformed COT identities') from exc
    if actual != expected:
        raise ValueError('COT market identities do not match the source registry')
    content = {key: value for key, value in snapshot.items() if key != 'content_sha256'}
    encoded = json.dumps(content, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if hashlib.sha256(encoded.encode()).hexdigest() != digest:
        raise ValueError('COT snapshot digest mismatch')
