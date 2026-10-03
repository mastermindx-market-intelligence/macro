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
    CatalystContext,
    CatalystContextError,
    CatalystEvidence,
    _require_ts,
    assess_catalyst_context_for_live_episode,
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


def assess_company_intelligence_current_read_for_live_episode(
    *,
    episode: Any,
    read_result: Mapping[str, Any],
    read_observed_at: datetime,
    decision_at: datetime,
) -> CatalystContext:
    """Compose one prospective owner read with a validated Radar episode.

    The input envelope must be the shape returned by Company Intelligence
    ``read_current_event_workspace``. This helper performs no network or filesystem read.
    It is forward-shadow only: an unavailable/currently-uncovered result remains
    ``coverage_unknown`` and never becomes evidence that no catalyst existed historically.
    """
    if not isinstance(read_result, Mapping):
        raise CatalystContextError("Company Intelligence current read must be a mapping")
    if read_result.get("authority") != "context_only" or read_result.get("is_context_only") is not True:
        raise CatalystContextError(
            "Company Intelligence current read must preserve context_only authority"
        )
    available = read_result.get("available")
    if type(available) is not bool:
        raise CatalystContextError("Company Intelligence current read requires boolean available")

    observed = _require_ts("read_observed_at", read_observed_at)
    base = assess_catalyst_context_for_live_episode(
        episode=episode,
        decision_at=decision_at,
        required_sources=[COMPANY_EVENT_OWNER],
        source_reads=[],
        evidence=[],
    )

    if not available:
        return base

    read_ticker = str(read_result.get("ticker") or "").strip().upper()
    if read_ticker != base.ticker:
        raise CatalystContextError(
            f"Company Intelligence read ticker {read_ticker!r} does not match Radar episode "
            f"ticker {base.ticker!r}"
        )
    workspace = read_result.get("workspace")
    if not isinstance(workspace, Mapping):
        raise CatalystContextError("available Company Intelligence read carries no workspace")
    receipt = read_result.get("receipt")
    if not isinstance(receipt, Mapping):
        raise CatalystContextError("available Company Intelligence read carries no receipt")
    workspace_sha = str(receipt.get("workspace_sha256") or "")
    if len(workspace_sha) != 64 or any(ch not in "0123456789abcdef" for ch in workspace_sha):
        raise CatalystContextError(
            "available Company Intelligence read carries no valid workspace SHA-256 receipt"
        )

    evidence = adapt_company_intelligence_earnings_workspace(
        workspace,
        ticker=base.ticker,
        owner_observed_at=observed,
    )
    return assess_catalyst_context_for_live_episode(
        episode=episode,
        decision_at=decision_at,
        required_sources=[COMPANY_EVENT_OWNER],
        source_reads=[],
        evidence=[evidence],
    )
