"""Issuer-level GMI context from the existing native selection transaction.

Host authentication/feature entitlement must precede this library. The host
injects the adopted owners and a read-only store factory; this module cannot
create a source owner, select a ticker identity, grant rights or publish data.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Callable

from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence import issuer_disclosure_selection as selection
from . import economic_context

SCHEMA = "theme_graph.native_issuer_economic_context/v1"


def _unavailable(reason: str) -> dict:
    result = economic_context._unavailable(reason)
    result["schema"] = SCHEMA
    return result


def read_issuer_economic_context(
    owner: selection.SelectionOwner,
    authority: native.DisclosureAuthority,
    store_factory: Callable[[], object],
    issuer_id: str, *, purpose: str, audience: str,
) -> dict:
    """Read the owner's current subject selection with no duplicate fact I/O.

    A qualified empty selection is distinct from unavailable and never claims
    that the issuer has no economic relationships globally. If any selected
    fact becomes ineligible, return no partial issuer context or prior result.
    This view does not manufacture historical, counterparty or ticker queries.
    """
    def open_store():
        try:
            return store_factory()
        except Exception:
            raise native.DisclosureError("PRIVATE_STORE_UNAVAILABLE") from None

    try:
        bundle = selection.read_issuer_disclosure_bundle(
            owner, authority, open_store, issuer_id, purpose=purpose, audience=audience,
            required_fields=economic_context.REQUIRED_FIELDS,
        )
        snapshot = bundle.selection
        contexts = []
        for item in bundle.disclosures:
            result = economic_context._project_selected(item.admission, item.request, item.payload)
            if result["status"] != "available":
                return _unavailable(result["reason"])
            contexts.append(result["context"])
        return {"schema": SCHEMA, "status": "available", "reason": None,
                "authority": "context_only", "context": {
                    "issuer_role": "subject_disclosing_company",
                    "issuer_binding": {
                        "issuer_id": snapshot.issuer_id, "evidenced_cik": snapshot.evidenced_cik,
                        "identity_snapshot_reference": {
                            "schema": snapshot.identity_snapshot_schema,
                            "sha256": snapshot.identity_snapshot_sha256,
                            "byte_length": snapshot.identity_snapshot_byte_length,
                        },
                    },
                    "generation": snapshot.generation, "identity_mode": "current",
                    "usage": {"purpose": snapshot.purpose, "audience": snapshot.audience},
                    "coverage": {"scope": "native_owner_current_subject_selection",
                                 "selected_count": len(contexts),
                                 "selection_limit": selection.MAX_SELECTIONS,
                                 "global_relationship_coverage_established": False},
                    "relationships": deepcopy(contexts),
                }}
    except native.DisclosureError as exc:
        return _unavailable(exc.code)
