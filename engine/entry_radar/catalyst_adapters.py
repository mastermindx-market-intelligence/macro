"""Pure source-specific adapters for Radar catalyst context.

Adapters consume already-retained owner records. They do not open files, query a network,
claim source coverage, or create Radar episodes. Each adapter returns only presence evidence.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from engine.company_intelligence.event_workspace import (
    WorkspaceError,
    validate_event_workspace,
)
from engine.company_intelligence.events import EventError, parse_canonical_event_id
from engine.earnings_release.filing_key import FilingIdentityError, filing_key_from_8k_row
from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    CatalystEvidence,
    _require_ts,
)

EDGAR_EARNINGS_OWNER = "collectors.edgar_earnings_8k"
EDGAR_ITEM_202_EVIDENCE_PREFIX = "sec-edgar-item202:"
_SUPPORTED_FORMS = frozenset({"8-K", "8-K/A"})

COMPANY_EVENT_OWNER = "company_intelligence.event_workspace"
COMPANY_EVENT_EVIDENCE_PREFIX = "company-intelligence-workspace:"
_COMPANY_EVENT_BLOCKING_STATES = frozenset({
    "started",
    "completed_partial",
    "complete",
    "corrected",
    "derived_ready",
    "distributed",
})


def _has_exact_item_202(raw: Any) -> bool:
    if raw in (None, ""):
        return False
    return "2.02" in {part.strip() for part in str(raw).split(",") if part.strip()}


def adapt_edgar_earnings_item_202(
    row: Mapping[str, Any],
    *,
    owner_observed_at: datetime,
) -> CatalystEvidence:
    """Map one canonical Item-2.02 filing into presence evidence.

    owner_observed_at is mandatory. The historical store SEC acceptance timestamp is
    source availability, not proof of when Mastermind observed the row.
    """
    if not isinstance(row, Mapping):
        raise CatalystContextError("EDGAR earnings row must be a mapping")
    ticker = str(row.get("ticker") or "").strip().upper()
    if not ticker:
        raise CatalystContextError("EDGAR earnings row carries no ticker")
    form = str(row.get("form") or "").strip().upper()
    if form not in _SUPPORTED_FORMS:
        raise CatalystContextError(f"unsupported EDGAR earnings form {form!r}")
    if not _has_exact_item_202(row.get("items")):
        raise CatalystContextError("EDGAR earnings row does not contain exact Item 2.02")
    try:
        key = filing_key_from_8k_row(row)
    except FilingIdentityError as exc:
        raise CatalystContextError(str(exc)) from exc
    acceptance = _require_ts("acceptance_datetime", row.get("acceptance_datetime"))
    observed = _require_ts("owner_observed_at", owner_observed_at)
    event_kind = (
        "earnings_results_item_2_02_amendment"
        if form == "8-K/A"
        else "earnings_results_item_2_02"
    )
    return CatalystEvidence(
        owner=EDGAR_EARNINGS_OWNER,
        native_id=key.key,
        ticker=ticker,
        event_kind=event_kind,
        source_available_at=acceptance,
        known_at=observed,
        owner_disposition="blocking",
        evidence_ref=f"{EDGAR_ITEM_202_EVIDENCE_PREFIX}{key.key}",
    )


def adapt_company_intelligence_earnings_workspace(
    workspace: Mapping[str, Any],
    *,
    ticker: str,
    owner_observed_at: datetime,
) -> CatalystEvidence:
    """Map one published Company Intelligence results workspace into presence evidence.

    This adapter never claims source coverage. owner_observed_at is the actual consumer
    observation clock for this immutable workspace version; neither the issuer event clock nor
    the workspace generation clock is promoted to a historical consumer clock.
    """
    try:
        validate_event_workspace(workspace)
    except WorkspaceError as exc:
        raise CatalystContextError(str(exc)) from exc

    symbol = str(ticker or "").strip().upper()
    if not symbol:
        raise CatalystContextError("ticker is required")

    event_id = str(workspace.get("event_id") or "").strip()
    try:
        _, _, event_type = parse_canonical_event_id(event_id)
    except EventError as exc:
        raise CatalystContextError(str(exc)) from exc
    if event_type != "earnings_results":
        raise CatalystContextError(
            f"Company Intelligence event {event_id!r} is {event_type!r}, not earnings_results"
        )

    issuer = workspace.get("issuer")
    if not isinstance(issuer, Mapping):
        raise CatalystContextError("Company Intelligence workspace issuer must be a mapping")
    listings = issuer.get("listings")
    if not isinstance(listings, list):
        raise CatalystContextError("Company Intelligence workspace issuer listings must be a list")
    listed = {
        str(row.get("ticker") or "").strip().upper()
        for row in listings
        if isinstance(row, Mapping)
    }
    if symbol not in listed:
        raise CatalystContextError(
            f"ticker {symbol!r} is not one of the workspace issuer listings {sorted(listed)!r}"
        )

    lifecycle = workspace.get("lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise CatalystContextError("Company Intelligence workspace lifecycle must be a mapping")
    state = str(lifecycle.get("state") or "").strip()
    if state not in _COMPANY_EVENT_BLOCKING_STATES:
        raise CatalystContextError(
            f"Company Intelligence lifecycle state {state!r} is not an admitted post-release state"
        )

    source_available = _require_ts(
        "lifecycle.source_available_at", lifecycle.get("source_available_at")
    )
    owner_event_observed = _require_ts(
        "lifecycle.observed_at", lifecycle.get("observed_at")
    )
    generated = _require_ts("generated_at", workspace.get("generated_at"))
    consumer_observed = _require_ts("owner_observed_at", owner_observed_at)

    if owner_event_observed < source_available:
        raise CatalystContextError(
            "Company Intelligence lifecycle observed_at precedes source_available_at"
        )
    if generated < owner_event_observed:
        raise CatalystContextError(
            "Company Intelligence generated_at precedes lifecycle observed_at"
        )
    if consumer_observed < generated:
        raise CatalystContextError(
            "owner_observed_at precedes Company Intelligence workspace generation"
        )

    generation_id = str(workspace.get("generation_id") or "").strip()
    native_id = f"{event_id}@{generation_id}"
    return CatalystEvidence(
        owner=COMPANY_EVENT_OWNER,
        native_id=native_id,
        ticker=symbol,
        event_kind="earnings_results_company_event",
        source_available_at=source_available,
        known_at=consumer_observed,
        owner_disposition="blocking",
        evidence_ref=f"{COMPANY_EVENT_EVIDENCE_PREFIX}{native_id}",
    )
