"""FIF catalog: the statement filings an issuer's admitted generation serves.

The page's company panel is a manually refreshed snapshot, so an accession it
carries can name a filing the production generation never admitted; the
statements route then answers 400 ``unknown filing`` and the revisions panel
has no period starts to ask for. This route answers from the same immutable
generation the statements route resolves against, so every accession it lists
is one ``/financial/statements`` can serve.

Request-path law matches the statement adapter: admission first, then the
provider; only the generation's statement index role is read — no member
bytes, no SEC fetch, no parse, no wall clock. A provider without a catalog
(the golden demonstration wiring) is the typed unavailability, never a
fallback list.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .query_service import (
    MAX_RESPONSE_BYTES,
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    admit_request_bytes,
    canonical_financial_delivery,
)
from .raw_ledger import canonical_json

_REQUEST_SCHEMA = "fundamental_forensics.financial_catalog_request/v1"
_RESPONSE_SCHEMA = "fundamental_forensics.financial_catalog_response/v1"
_ROOT_FIELDS = frozenset({"schema", "entity_id"})
_REQUIRED_TEXT_FIELDS = ("accession", "form", "period_of_report", "filing_date")


@dataclass(frozen=True)
class FinancialCatalogResult:
    body: bytes
    sha256: str
    envelope: dict[str, Any]


def admit_catalog_request(body: bytes) -> str:
    parsed = admit_request_bytes(body)
    if set(parsed) != _ROOT_FIELDS:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    if parsed.get("schema") != _REQUEST_SCHEMA:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    entity_id = parsed["entity_id"]
    if not isinstance(entity_id, str) or not entity_id:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    return entity_id


def _filing_row(item: Any, *, entity_id: str, cik: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise FinancialQueryUnavailableError()
    row: dict[str, Any] = {}
    for field in _REQUIRED_TEXT_FIELDS:
        value = item.get(field)
        if not isinstance(value, str) or not value:
            raise FinancialQueryUnavailableError()
        row[field] = value
    accepted = item.get("source_accepted_at")
    if accepted is not None and (not isinstance(accepted, str) or not accepted):
        raise FinancialQueryUnavailableError()
    row["source_accepted_at"] = accepted
    # Same identity pin the statement adapter applies to a resolved package.
    if item.get("entity_id") != entity_id or item.get("cik") != cik:
        raise FinancialQueryUnavailableError()
    return row


def execute_financial_catalog(
    *,
    body: bytes,
    provider: Any | None = None,
    provider_factory: Callable[[], Any] | None = None,
) -> FinancialCatalogResult:
    entity_id = admit_catalog_request(body)
    if provider is None:
        if provider_factory is None:
            raise FinancialQueryUnavailableError()
        provider = provider_factory()
    catalog = getattr(provider, "catalog", None)
    if not callable(catalog):
        raise FinancialQueryUnavailableError()
    listing = catalog(entity_id)
    if not isinstance(listing, dict):
        raise FinancialQueryUnavailableError()
    cik = listing.get("cik")
    generation_id = listing.get("dataset_generation_id")
    admitted_at = listing.get("admitted_at")
    if listing.get("entity_id") != entity_id:
        raise FinancialQueryUnavailableError()
    for value in (cik, generation_id, admitted_at):
        if not isinstance(value, str) or not value:
            raise FinancialQueryUnavailableError()
    raw_filings = listing.get("filings")
    if not isinstance(raw_filings, (list, tuple)):
        raise FinancialQueryUnavailableError()
    filings = [_filing_row(item, entity_id=entity_id, cik=cik) for item in raw_filings]
    accessions = [row["accession"] for row in filings]
    if len(set(accessions)) != len(accessions):
        raise FinancialQueryUnavailableError()
    filings.sort(key=lambda row: (row["filing_date"], row["accession"]))
    delivery = canonical_financial_delivery(listing.get("delivery"))
    if delivery is None:
        raise FinancialQueryUnavailableError()

    envelope = {
        "schema": _RESPONSE_SCHEMA,
        "entity": {"entity_id": entity_id, "cik": cik},
        "dataset_generation_id": generation_id,
        "admitted_at": admitted_at,
        "filings": filings,
        "authority": {"class": "context_only", "display_only": True},
        "delivery": delivery,
    }
    body_out = canonical_json(envelope).encode("utf-8")
    if len(body_out) > MAX_RESPONSE_BYTES:
        raise FinancialQueryAdmissionError(413, "response exceeds bound")
    digest = hashlib.sha256(body_out).hexdigest()
    return FinancialCatalogResult(body=body_out, sha256=digest, envelope=envelope)


__all__ = [
    "FinancialCatalogResult",
    "admit_catalog_request",
    "execute_financial_catalog",
]
