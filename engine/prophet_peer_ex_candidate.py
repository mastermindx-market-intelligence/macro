"""Pure adapter from the canonical peer-context owner to Early Leadership peer evidence.

This module creates no peer-selection rule. It delegates focal/same-issuer exclusion,
fixed denominators, missing-market handling and identity qualification to
engine.group_flow.independent_peer_observation and only packages that owner's
observation into the closed prophet.peer_ex_candidate/v1 envelope consumed by
Early Leadership research.

It owns no rank, score, candidate admission, B4 Availability, plan, sizing,
execution, persistence or trading authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from math import fsum, isfinite
import re
from typing import Any

from engine.group_flow import independent_peer_observation

SCHEMA = "prophet.peer_ex_candidate/v1"

_RFC3339_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class PeerExCandidateAdapterError(ValueError):
    """The upstream peer observation cannot honestly satisfy the closed envelope."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise PeerExCandidateAdapterError(f"{field}_invalid")
    if any(ord(character) < 32 for character in value):
        raise PeerExCandidateAdapterError(f"{field}_invalid")
    return value


def _instant(value: object, field: str) -> tuple[str, datetime]:
    text = _text(value, field)
    if not _RFC3339_UTC_RE.fullmatch(text):
        raise PeerExCandidateAdapterError(f"{field}_invalid")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PeerExCandidateAdapterError(f"{field}_invalid") from exc
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    return canonical, parsed


def _vintage(value: object) -> str:
    text = _text(value, "membership_vintage")
    if not _DATE_RE.fullmatch(text):
        raise PeerExCandidateAdapterError("membership_vintage_invalid")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise PeerExCandidateAdapterError("membership_vintage_invalid") from exc
    if parsed.isoformat() != text:
        raise PeerExCandidateAdapterError("membership_vintage_invalid")
    return text


def _window(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PeerExCandidateAdapterError("return_window_sessions_invalid")
    return value


def _finite_observation(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return out if isfinite(out) else None


def build_peer_ex_candidate(
    *,
    member_returns: Mapping[str, Any],
    focal_ticker: str,
    issuer_by_ticker: Mapping[str, str | None],
    security_by_ticker: Mapping[str, str | None],
    candidate_issuer_id: str,
    candidate_security_id: str,
    theme_id: str,
    asof: str,
    known_at: str,
    membership_vintage: str,
    return_window_sessions: int,
    return_basis: str,
    source_ref: str,
) -> dict[str, Any]:
    """Project one source-qualified leave-issuer-out peer observation.

    member_returns is the owner's already-aligned return window for the dated
    theme roster. The canonical group-flow owner decides who is an independent peer
    and what remains missing. This adapter refuses unresolved issuer identity because
    the downstream issuer_aliases_excluded=True field is a proof claim, not best effort.
    """
    if not isinstance(member_returns, Mapping) or not member_returns:
        raise PeerExCandidateAdapterError("member_returns_required")
    if not isinstance(issuer_by_ticker, Mapping):
        raise PeerExCandidateAdapterError("issuer_by_ticker_required")
    if not isinstance(security_by_ticker, Mapping):
        raise PeerExCandidateAdapterError("security_by_ticker_required")

    ticker = _text(focal_ticker, "focal_ticker")
    issuer = _text(candidate_issuer_id, "candidate_issuer_id")
    security = _text(candidate_security_id, "candidate_security_id")
    theme = _text(theme_id, "theme_id")
    basis = _text(return_basis, "return_basis")
    source = _text(source_ref, "source_ref")
    window = _window(return_window_sessions)
    vintage = _vintage(membership_vintage)
    asof_text, asof_dt = _instant(asof, "asof")
    known_text, known_dt = _instant(known_at, "known_at")
    if asof_dt > known_dt:
        raise PeerExCandidateAdapterError("peer_clock_invalid")
    if date.fromisoformat(vintage) > asof_dt.date():
        raise PeerExCandidateAdapterError("membership_vintage_after_measurement")

    keys = list(member_returns)
    if any(
        not isinstance(key, str) or not key or key != key.strip()
        for key in keys
    ):
        raise PeerExCandidateAdapterError("member_ticker_invalid")
    if ticker not in member_returns:
        raise PeerExCandidateAdapterError("focal_ticker_missing_from_roster")

    mapped_focal = issuer_by_ticker.get(ticker)
    if mapped_focal != issuer:
        raise PeerExCandidateAdapterError("candidate_issuer_mismatch")
    mapped_security = security_by_ticker.get(ticker)
    if mapped_security != security:
        raise PeerExCandidateAdapterError("candidate_security_mismatch")

    try:
        observation = independent_peer_observation(
            member_returns,
            focal_ticker=ticker,
            issuer_by_ticker=issuer_by_ticker,
        )
    except (TypeError, ValueError) as exc:
        raise PeerExCandidateAdapterError("peer_owner_refused_input") from exc

    if observation.get("independence_status") != "AVAILABLE":
        raise PeerExCandidateAdapterError("peer_identity_unavailable")
    if observation.get("focal_issuer") != issuer:
        raise PeerExCandidateAdapterError("peer_owner_candidate_issuer_mismatch")

    total = observation.get("peer_denominator")
    priced = observation.get("observed_independent_peers")
    if (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total < 1
        or isinstance(priced, bool)
        or not isinstance(priced, int)
        or not 0 <= priced <= total
    ):
        raise PeerExCandidateAdapterError("peer_owner_counts_invalid")

    excluded = set(observation.get("excluded_same_issuer") or ())
    unknown_identity = set(observation.get("unknown_peer_identity") or ())
    missing_market = set(observation.get("missing_market_observation") or ())
    if ticker not in excluded or unknown_identity:
        raise PeerExCandidateAdapterError("peer_identity_unavailable")

    priced_tickers = [
        key
        for key in sorted(member_returns)
        if key not in excluded
        and key not in unknown_identity
        and key not in missing_market
    ]
    priced_values = [
        value
        for key in priced_tickers
        if (value := _finite_observation(member_returns.get(key))) is not None
    ]
    if len(priced_values) != priced:
        raise PeerExCandidateAdapterError("peer_owner_priced_count_mismatch")

    coverage = priced / total
    if priced <= 1:
        equal_weight_return = median_return = positive_share = None
    else:
        equal_weight_return = fsum(priced_values) / priced
        median_return = observation.get("peer_median")
        if not isinstance(median_return, (int, float)) or isinstance(median_return, bool):
            raise PeerExCandidateAdapterError("peer_owner_median_invalid")
        median_return = float(median_return)
        if not isfinite(median_return):
            raise PeerExCandidateAdapterError("peer_owner_median_invalid")
        positive = observation.get("n_positive")
        if isinstance(positive, bool) or not isinstance(positive, int) or not 0 <= positive <= priced:
            raise PeerExCandidateAdapterError("peer_owner_positive_count_invalid")
        positive_share = positive / priced

    return {
        "schema": SCHEMA,
        "candidate_issuer_id": issuer,
        "candidate_security_id": security,
        "theme_id": theme,
        "asof": asof_text,
        "known_at": known_text,
        "membership_vintage": vintage,
        "return_window_sessions": window,
        "return_basis": basis,
        "candidate_excluded": True,
        "issuer_aliases_excluded": True,
        "peer_member_count": total,
        "priced_peer_count": priced,
        "coverage": coverage,
        "equal_weight_return": equal_weight_return,
        "median_return": median_return,
        "positive_share": positive_share,
        "source_ref": source,
    }
