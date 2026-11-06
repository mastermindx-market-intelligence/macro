"""FIF-2C: thin HTTP-transport adapter serving canonical_packet_bytes.

The frozen assembler remains the authority. This module does not invent a
second financial representation, refuse unsupported metrics, or stamp
built_at=now. Authentication and entitlement happen at the HTTP layer; the
packet provider is never opened before they succeed.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

from .financial_intelligence_packet import (
    assemble_financial_intelligence_packet,
    canonical_packet_bytes,
)
from .issuer_sic import IssuerSicResolver, resolve_issuer_sic
from .query_service import (
    MAX_RESPONSE_BYTES,
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    admit_financial_request,
    enforce_dataset_admission_floor,
)
from .revision_service import (
    FinancialPacketProvider,
    occurrence_keyed_filing_metadata,
    packet_query_request,
    validate_packet_dataset,
)

_REQUEST_SCHEMA = "fundamental_forensics.financial_packet_request/v1"


@dataclass(frozen=True)
class FinancialPacketResult:
    """Exact canonical packet bytes plus the SHA-256 of those HTTP bytes."""

    packet: dict[str, Any]
    body: bytes
    response_sha256: str


def execute_financial_packet(
    *,
    body: bytes,
    provider: FinancialPacketProvider | None = None,
    provider_factory: Callable[[], FinancialPacketProvider] | None = None,
    issuer_sic_resolver: IssuerSicResolver | None = None,
) -> FinancialPacketResult:
    """Admit, construct PacketQueryRequest, resolve, assemble, and serialize.

    PacketQueryRequest is built immediately after shared HTTP admission and
    before the provider factory or resolve. Unsupported metrics are packet
    cells, not API 400s. built_at is never supplied.
    """
    admitted = admit_financial_request(body, request_schema=_REQUEST_SCHEMA)
    query_request = packet_query_request(admitted)
    if provider is None:
        if provider_factory is None:
            raise FinancialQueryUnavailableError()
        provider = provider_factory()
    dataset = provider.resolve(admitted.entity_id)
    binding = validate_packet_dataset(admitted.entity_id, dataset)
    # FIF D3 (A12): the dataset's own admission clock gates the system view.
    # The canonical packet bytes themselves stay exactly the frozen assembler's
    # output — the production delivery object rides the revisions envelope,
    # never the packet body, whose content_sha256 is a frozen contract.
    enforce_dataset_admission_floor(admitted.policy, dataset)
    # R1-SIC: resolve the issuer SIC from the shipped coverage contract by
    # the binding's own CIK; no record means no SIC (fail-closed).
    sic_resolver = (
        issuer_sic_resolver
        if issuer_sic_resolver is not None
        else partial(resolve_issuer_sic)
    )
    # A0 (D-2): the production store keys filing metadata by accession while
    # the frozen assembler resolves it by occurrence id; normalize at this
    # boundary. Identity for the occurrence-keyed golden/FIP1 fixtures.
    # A0-h1 (MINOR-4): the normalization sits INSIDE the assemble try, AFTER
    # the admission floor above and immediately before the assembly it feeds
    # — so a request the floor refuses keeps its typed refusal instead of
    # the helper's raw ValueError winning the race, and a metadata defect
    # (unknown key, conflicting metadata) surfaces as a typed
    # FinancialQueryUnavailableError from the service, never a raw
    # ValueError into the API catch-all.
    try:
        filing_metadata = occurrence_keyed_filing_metadata(dataset.ledger, dataset.filing_metadata)
        packet = assemble_financial_intelligence_packet(
            entity=dataset.entity,
            ledger=dataset.ledger,
            filing_metadata=filing_metadata,
            query_request=query_request,
            metric_registry=dataset.registry,
            context=dataset.context,
            input_digests=dataset.input_digests,
            issuer_sic_resolver=sic_resolver,
        )
    except FinancialQueryAdmissionError:
        raise
    except Exception:
        raise FinancialQueryUnavailableError() from None

    entity = packet.get("entity")
    if not isinstance(entity, dict):
        raise FinancialQueryUnavailableError()
    if entity.get("entity_id") != binding.entity_id:
        raise FinancialQueryUnavailableError()
    if entity.get("cik") != binding.cik:
        raise FinancialQueryUnavailableError()
    if entity.get("ticker") != binding.ticker:
        raise FinancialQueryUnavailableError()
    if entity.get("source_entity_id") != binding.source_entity_id:
        raise FinancialQueryUnavailableError()

    response_body = canonical_packet_bytes(packet)
    if len(response_body) > MAX_RESPONSE_BYTES:
        raise FinancialQueryAdmissionError(413, "response exceeds bound")
    digest = hashlib.sha256(response_body).hexdigest()
    return FinancialPacketResult(
        packet=packet,
        body=response_body,
        response_sha256=digest,
    )


__all__ = [
    "FinancialPacketResult",
    "execute_financial_packet",
]
