"""K3E read-only projection over one verified institutional 13F catalog row.

The institutional-census owner remains authoritative for catalog integrity,
filing/holding joins, source receipts, generation clocks, and immutable row
identity. This module adds no store, resolver, score, flow model, or lifecycle.

One exact (accession, infotable_sk) row may be exposed as delayed reported
holding context after the owner generation was published by the requested
decision cutoff. It remains K3E-inadmissible until canonical security resolution
and purpose-specific source-use evidence are supplied by their existing owners.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.institutional_census.catalog import PublishedCatalogGeneration


SCHEMA = "institutional_13f.k3e_reported_holding_context.v1"


def _clock(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _base() -> dict:
    return {
        "schema": SCHEMA,
        "valid": False,
        "state": "UNAVAILABLE",
        "refusals": [],
        "owner": "engine.institutional_census",
        "authority": "descriptive_context_only",
        "financial_influence": False,
        "k3e_admissible": False,
        "generation": None,
        "filing": None,
        "holding": None,
        "interpretation": {
            "class": "DELAYED_REPORTED_HOLDING_CONTEXT",
            "is_current_ownership": False,
            "is_flow": False,
            "is_intent": False,
            "is_conviction": False,
        },
        "qualification": {
            "state": "NOT_QUALIFIED",
            "missing": [
                "canonical_security_resolution_receipt",
                "source_use_receipt",
            ],
            "canonical_security_id": None,
            "source_use": "UNKNOWN",
        },
    }


def _generation_projection(generation: PublishedCatalogGeneration) -> dict:
    clocks = generation.manifest.clocks
    return {
        "generation_id": generation.generation_id,
        "report_period": clocks.report_period,
        "source_cutoff_at": clocks.source_cutoff_at,
        "published_at": clocks.published_at,
        "current_generation_id": generation.current_generation_id,
        "superseded": generation.superseded,
    }


def _select_filing(generation: PublishedCatalogGeneration, accession: str):
    rows = [row for row in generation.filings if row.get("accession") == accession]
    return rows[0] if len(rows) == 1 else None


def _select_holding(
    generation: PublishedCatalogGeneration,
    *,
    accession: str,
    infotable_sk: int,
):
    rows = [
        row
        for row in generation.holdings
        if row.get("accession") == accession
        and row.get("infotable_sk") == infotable_sk
    ]
    return rows[0] if len(rows) == 1 else None


def project_reported_holding(
    generation: object,
    *,
    accession: object,
    infotable_sk: object,
    decision_cutoff: object,
) -> dict:
    """Project one exact immutable holding row without inferring positioning."""
    out = _base()
    if not isinstance(generation, PublishedCatalogGeneration):
        out["state"] = "REFUSED"
        out["refusals"] = ["OWNER_GENERATION_REQUIRED"]
        return out

    out["generation"] = _generation_projection(generation)

    if not isinstance(accession, str) or not accession.strip():
        out["state"] = "REFUSED"
        out["refusals"].append("INVALID_HOLDING_KEY")
        return out
    if isinstance(infotable_sk, bool) or not isinstance(infotable_sk, int) or infotable_sk < 0:
        out["state"] = "REFUSED"
        out["refusals"].append("INVALID_HOLDING_KEY")
        return out

    cutoff = _clock(decision_cutoff)
    published = _clock(generation.manifest.clocks.published_at)
    if cutoff is None:
        out["state"] = "REFUSED"
        out["refusals"].append("INVALID_DECISION_CUTOFF")
        return out
    if published is None:
        out["state"] = "REFUSED"
        out["refusals"].append("OWNER_PUBLICATION_CLOCK_INVALID")
        return out
    if published > cutoff:
        out["refusals"].append("GENERATION_NOT_AVAILABLE_AT_CUTOFF")
        return out

    holding = _select_holding(
        generation,
        accession=accession,
        infotable_sk=infotable_sk,
    )
    if holding is None:
        out["refusals"].append("HOLDING_ROW_NOT_FOUND")
        return out

    filing = _select_filing(generation, accession)
    if filing is None:
        # The owner normally prevents this, but keep this projection fail-closed
        # if a foreign object bypassed that invariant.
        out["state"] = "REFUSED"
        out["refusals"].append("FILING_PROVENANCE_UNAVAILABLE")
        return out

    quantity_value = holding.get("ssh_prn_amt")
    quantity_type = holding.get("ssh_prn_type")
    limitations: list[str] = []
    normalized_quantity = None
    if quantity_value is None:
        limitations.append("QUANTITY_VALUE_UNAVAILABLE")
    if quantity_type is None:
        limitations.append("QUANTITY_TYPE_UNQUALIFIED")
    # Source tokens remain source tokens.  K3E does not coerce an unknown share /
    # principal type into a comparable numeric quantity.
    if quantity_value is not None and quantity_type is not None:
        limitations.append("NORMALIZED_QUANTITY_NOT_ADMITTED")

    out["filing"] = {
        "accession": filing.get("accession"),
        "filer_cik": filing.get("filer_cik"),
        "filer_name": filing.get("filer_name"),
        "form": filing.get("form"),
        "filing_date": filing.get("filing_date"),
        "accepted_at": filing.get("accepted_at"),
        "report_period": filing.get("report_period"),
        "is_amendment": filing.get("is_amendment"),
        "amendment_number": filing.get("amendment_number"),
        "amendment_type": filing.get("amendment_type"),
        "amends_accession": filing.get("amends_accession"),
        "lineage_state": filing.get("lineage_state"),
        "confidential_omitted": filing.get("confidential_omitted"),
        "source_receipt_id": filing.get("source_receipt_id"),
        "raw_sha256": filing.get("raw_sha256"),
        "first_seen_at": filing.get("first_seen_at"),
        "retained_at": filing.get("retained_at"),
        "parser_version": filing.get("parser_version"),
        "quality_state": filing.get("quality_state"),
    }
    out["holding"] = {
        "infotable_sk": holding.get("infotable_sk"),
        "row_hash": holding.get("row_hash"),
        "name_of_issuer": holding.get("name_of_issuer"),
        "title_of_class": holding.get("title_of_class"),
        "cusip": holding.get("cusip"),
        "figi": holding.get("figi"),
        "quantity": {
            "value": quantity_value,
            "type": quantity_type,
        },
        "normalized_quantity": normalized_quantity,
        "reported_value": {
            "source_value": holding.get("value_reported"),
            "source_unit": holding.get("value_unit"),
            "normalized_value_usd": holding.get("value_usd"),
        },
        "put_call": holding.get("put_call"),
        "investment_discretion": holding.get("investment_discretion"),
        "limitations": limitations,
    }
    out["valid"] = True
    out["state"] = "AVAILABLE_UNQUALIFIED"
    return out
