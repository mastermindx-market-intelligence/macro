"""FIF S2-p: the pure production-dataset lineage mint (v1 pairs ∪ v2 chains).

Seat ruling R-S2P-1 (2026-10-12, binding): ONE function, ONE mint path.  The
production write side mints its ``ProductionDatasetMaterial.lineage_evidence``
bundle as the union of the two admitted confirmation rule versions over one
issuer's ledger — v1 (``derive_confirmation_receipts``) mints only logical keys
spanning exactly two accessions, v2 (``derive_chain_confirmation_receipts``)
only keys spanning three or more accessions classified ``repeated``.  The two
scopes are disjoint by construction, so the concatenation never double-mints a
key and every minted receipt carries exactly one ``evidence_rule_version``.

The golden path is NOT switched: ``ixbrl_raw_ledger`` keeps minting v1 alone
(census Q5, keep-v1).  This module is the C0-b producer's hook — at
``ProductionDatasetMaterial`` assembly the producer calls
``mint_production_lineage_evidence(ledger, packages, system_available_at=<the
material's admission clock>)``; the field and its role serialization are
already version-agnostic.  The admission clock must be at least
``max(capture-recorded clocks ∪ {CONFIRMATION_RULE_AVAILABLE_AT,
CONFIRMATION_CHAIN_RULE_AVAILABLE_AT})`` — a clock derived from the filings'
acceptance times instead is below the rule floors and refuses (C0-b §5 CLOCK
RULE; pinned by this lane's tests).

Everything here is pure: no wall clock, no environment, no store, no I/O
beyond the in-memory package bytes, and no mutation of the inputs.  A naive
``system_available_at`` or a clock below a rule floor raises
``LineageEvidenceError`` from the mint layers and is never swallowed; an
unparseable primary document raises this module's own typed error; an empty
bundle is lawful (a two-filing issuer with no repeated chain mints nothing).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Mapping, Sequence

from collectors.sec_filing_parser import SecFilingParseError, parse_sec_filing_document

from .ixbrl_raw_ledger import _clark_parts
from .lineage_evidence import (
    LineageEvidenceReceipt,
    derive_chain_confirmation_receipts,
    derive_confirmation_receipts,
)
from .raw_ledger import RawFactLedger

if TYPE_CHECKING:  # pragma: no cover - typing only, duck-typed at runtime
    from .admitted_filing_package import AdmittedFilingPackage
    from .statement_graph import GoldenFilingPackage

__all__ = [
    "ProductionLineageError",
    "admitted_concept_namespace_uris",
    "mint_production_lineage_evidence",
]


class ProductionLineageError(ValueError):
    """A production mint input is malformed (never a query-side fault)."""


def admitted_concept_namespace_uris(
    packages: Sequence[GoldenFilingPackage | AdmittedFilingPackage],
) -> dict[tuple[str, str], str]:
    """Map ``(accession, parser fact_id)`` to the original Clark namespace URI.

    The issuer-neutral twin of ``ixbrl_raw_ledger
    .original_concept_namespace_uris``: same law, same parser primitive
    (``parse_sec_filing_document`` plus ``_clark_parts`` — namespace extraction
    is never re-implemented here), issuer-neutral error text, and open to any
    digest-admitted ``AdmittedFilingPackage`` rather than the golden set alone.
    Guard 11 is unprovable without this map, which is read back from the source
    packages at mint time and attested on the immutable receipts.
    """
    mapping: dict[tuple[str, str], str] = {}
    for package in packages:
        manifest = getattr(package, "manifest", None)
        members = getattr(package, "members", None)
        if not isinstance(manifest, Mapping) or not isinstance(members, Mapping):
            raise ProductionLineageError("filing package manifest is malformed")
        accession = manifest.get("accession")
        primary = manifest.get("primary_document")
        if not isinstance(accession, str) or not accession:
            raise ProductionLineageError("filing package manifest is malformed")
        if not isinstance(primary, str) or not primary:
            raise ProductionLineageError("filing package manifest is malformed")
        if primary not in members:
            raise ProductionLineageError(
                "filing package primary document is not retained"
            )
        try:
            parsed = parse_sec_filing_document(
                members[primary], document_name=primary
            )
        except SecFilingParseError as exc:
            raise ProductionLineageError(
                f"primary document cannot be parsed for accession {accession}"
            ) from exc
        for fact in parsed.get("facts") or []:
            if not isinstance(fact, Mapping):
                continue
            fact_id = fact.get("fact_id")
            parts = _clark_parts(fact.get("concept_qname") or "")
            if fact_id and parts is not None:
                mapping[(accession, str(fact_id))] = parts[0]
    return mapping


def mint_production_lineage_evidence(
    ledger: RawFactLedger,
    packages: Sequence[GoldenFilingPackage | AdmittedFilingPackage],
    *,
    system_available_at: datetime,
) -> tuple[LineageEvidenceReceipt, ...]:
    """Mint the v1 pairs plus v2 repeated chains for one admitted ledger.

    Returns ``derive_confirmation_receipts(...) +
    derive_chain_confirmation_receipts(...)`` over ``ledger.events`` with the
    taxonomy URI map derived from ``packages``.  v1 receipts carry
    ``evidence_rule_version == 1`` and span exactly two accessions; v2
    receipts carry ``evidence_rule_version == 2`` and are the n-1 adjacent
    edges of a ``repeated`` chain.  Pure and deterministic: identical inputs
    mint byte-identical receipts, receipt ids included.

    Raises ``LineageEvidenceError`` (from the mint layers, never swallowed)
    for a naive ``system_available_at`` or a clock below a rule's floor; the
    empty tuple is lawful.
    """
    taxonomy_uris = admitted_concept_namespace_uris(packages)
    v1 = derive_confirmation_receipts(
        ledger.events,
        system_available_at=system_available_at,
        original_taxonomy_uris=taxonomy_uris,
    )
    v2 = derive_chain_confirmation_receipts(
        ledger.events,
        system_available_at=system_available_at,
        original_taxonomy_uris=taxonomy_uris,
    )
    return v1 + v2
