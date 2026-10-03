"""Pure source-specific adapters for Radar catalyst context.

Adapters consume already-retained owner records. They do not open files, query a network,
claim source coverage, or create Radar episodes. Each adapter returns only presence evidence.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from engine.earnings_release.filing_key import FilingIdentityError, filing_key_from_8k_row
from engine.entry_radar.catalyst_context import CatalystContextError, CatalystEvidence, _require_ts

EDGAR_EARNINGS_OWNER = "collectors.edgar_earnings_8k"
EDGAR_ITEM_202_EVIDENCE_PREFIX = "sec-edgar-item202:"
_SUPPORTED_FORMS = frozenset({"8-K", "8-K/A"})


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

    ``owner_observed_at`` is mandatory. The historical store's SEC acceptance timestamp is
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
