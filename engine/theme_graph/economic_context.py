"""Read-only GMI context over the incumbent private disclosure owner.

This is a view, not a Graph1 publisher, evidence store, identity resolver or
propagation generator. The host must authenticate/entitle its caller BEFORE
calling this library, and must inject its adopted DisclosureAuthority and
read-only native store. Neither a caller-supplied fact dict nor a syntactically
plausible edge identifier is an input.

The first supported native species is planned product integration. It is NOT a
supplier/customer contract, shipment, current plan, cash-flow share or forecast.
The native owner controls source selection, rights, identity, clocks, revisions
and corrections. No observer, cache, source fetch, publication or retry is added.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from engine.company_intelligence import issuer_disclosures as native

SCHEMA = "theme_graph.native_economic_context/v1"
NATIVE_SCHEMA = "company_intelligence.private_product_integration/v2"
REQUIRED_FIELDS = frozenset({
    "fact_id", "revision", "kind", "lifecycle", "subject_id", "object_id",
    "product", "platform", "amount", "economic_share",
})
_REASON = re.compile(r"[A-Z][A-Z0-9_]{0,95}\Z")


def _unavailable(code: str) -> dict[str, Any]:
    # Do not serialize exception messages, requested identifiers, raw source,
    # references, generation metadata or a previous positive on a refusal.
    if type(code) is not str or _REASON.fullmatch(code) is None:
        code = "NATIVE_DISCLOSURE_UNAVAILABLE"
    return {"schema": SCHEMA, "status": "unavailable", "reason": code,
            "context": None, "authority": "context_only"}


def _project_selected(admission: native.Admission, request: native.Request, selected: dict) -> dict[str, Any]:
    """Internal rendering of a same-request native read, not an admission API."""
    if (type(selected) is not dict
            or selected.get("schema") not in {NATIVE_SCHEMA, "company_intelligence.private_disclosed_supplier/v1"}
            or selected.get("authority") != "context_only"
            or selected.get("reference") != admission.reference.payload()
            or selected.get("edition") != admission.edition.payload()
            or selected.get("generation") != admission.generation):
        return _unavailable("NATIVE_PROJECTION_CONTRACT_MISMATCH")
    fact = selected.get("fact")
    timing = selected.get("source_timing")
    supplier = admission.reference.schema == native.SUPPLIER_FACT_SCHEMA
    if (type(fact) is not dict or not REQUIRED_FIELDS <= fact.keys()
            or type(timing) is not dict
            or set(timing) != {"published_date", "published_at",
                              "publication_precision", "known_at"} | ({"sec_source"} if supplier else set())):
        return _unavailable("NATIVE_PROJECTION_CONTRACT_MISMATCH")
    if ((fact["kind"], fact["lifecycle"]) !=
            (("disclosed_supplier", "reported_use") if supplier else ("product_integration", "planned"))
            or fact["amount"] is not None or fact["economic_share"] is not None):
        return _unavailable("ECONOMIC_SPECIES_NOT_MAPPED")
    context = {
        "usage": {"purpose": request.purpose, "audience": request.audience},
        "relationship": {k: fact[k] for k in (
            "kind", "lifecycle", "subject_id", "object_id", "product",
            "platform", "amount", "economic_share",
        )},
        "provenance": {
            "fact_id": fact["fact_id"], "revision": fact["revision"],
            "reference": selected["reference"], "edition": selected["edition"],
            "generation": selected["generation"],
        },
        "timing": {
            "source_published_date": timing["published_date"],
            "source_published_at": timing["published_at"],
            "publication_precision": timing["publication_precision"],
            "edition_known_at": timing["known_at"],
            "fact_known_at": admission.known_at,
            "identity_mode": admission.identity_mode,
            "query_mode": request.mode, "query_as_of": request.as_of,
        },
        "mapping": {
            "state": "native_fact_context_only",
            "legacy_theme_graph_edge": None, "propagation_hypothesis": None,
            "reason": "PLANNED_INTEGRATION_MAPPING_NOT_ADOPTED",
        },
        "limitations": {
            "current_plan_established": False,
            "current_commercial_relationship_established": False,
            "fulfilled_shipment_established": False,
            "economic_sensitivity_established": False,
            "historical_identity_inferred": False,
        },
    }
    if supplier:
        # read_disclosure has verified both native identities, source/span
        # linkage, immutable revisions and the exact purpose admission. This
        # is one role input; it never composes a propagation hypothesis itself.
        q = selected.get("supplier_binding")
        if (selected["schema"] != "company_intelligence.private_disclosed_supplier/v1"
                or type(q) is not dict or q.get("direction") != "object_supplies_subject"
                or q.get("identity_mode") != "current"
                or any(type(q.get(k)) is not str or re.fullmatch(r"[0-9a-f]{64}", q[k]) is None
                       for k in ("current_subject_identity", "current_object_identity"))):
            return _unavailable("NATIVE_PROJECTION_CONTRACT_MISMATCH")
        # These are the current receipt digests used by this native qualification,
        # separate from immutable fact decision hashes. A K3 join must match both.
        context["provenance"]["current_identity_sha256s"] = {
            "subject": q["current_subject_identity"], "object": q["current_object_identity"]}
        s = timing["sec_source"]
        context["timing"].update(sec_accepted_at=s["accepted_at"], retained_retrieved_at=s["retrieved_at"],
            retained_recorded_at=s["recorded_at"], pinned_snapshot_at=s["snapshot_at"],
            identity_observed_at=q["identity_observed_at"], native_fact_adopted_at=admission.known_at)
        context["relationship"]["direction"] = "object_supplies_subject"
        context["mapping"] = {"state": "qualified_disclosed_role_input", "legacy_theme_graph_edge": None,
            "propagation_hypothesis": None, "reason": None, "k3_input": {
                "leg_id": "sec_supplier:" + admission.reference.sha256,
                "graph": "graph_1", "construct": "disclosed_customer_supplier", "role": "supplier",
                "role_evidence_class": "disclosed_role_specific", "claim_strength": "disclosed",
                "owner_ref": {"owner_program": "gmi-theme-graph", "artifact": "native_disclosure:" + admission.reference.sha256,
                              "artifact_schema": SCHEMA},
                "evidence_refs": ["native_fact:sha256:" + admission.reference.sha256,
                                  "native_edition:sha256:" + admission.edition.sha256],
                "asof": native.datetime.now(native.timezone.utc).date().isoformat(),
                "known_at": admission.known_at, "usability_state": "usable"}}
        context["source_attribution"] = {"source": "SEC public issuer filing", "archive_url": s["archive_url"],
            "accession": s["accession"], "document_id": s["document_id"]}
        context["authority"] = {key: False for key in ("rank", "gate", "size", "trade", "prediction")}
        context["limitations"]["current_status_from_selected_filing_established"] = False
        context["limitations"]["historical_system_availability_established"] = False
        context["limitations"]["source_body_export_authorized"] = False
    return {"schema": SCHEMA, "status": "available", "reason": None,
            "context": deepcopy(context), "authority": "context_only"}


def read_economic_context(
    store: object,
    authority: native.DisclosureAuthority,
    request: native.Request,
    *, expected_admission: native.Admission | None = None,
) -> dict[str, Any]:
    """Return one native-owner-qualified fact view or a sanitized typed refusal.

    The composing preflight checks field eligibility without artifact reads.
    The existing reader then pins that exact Admission, verifies immutable
    objects/revision chains and rechecks the owner after reads. Failures have
    no fallback or retry. Authorization and historical eligibility are NOT
    inferred from a request flag, fact date, hash or this response's schema.

    Subject/object retain their native component/platform-issuer meaning;
    this function never emits a legacy theme-graph edge or K3-D hypothesis.
    An optional existing Admission pin avoids an extra composing preflight,
    never the native reader's live pre/post-read authority checks.
    """
    try:
        if expected_admission is None:
            admission = native.preflight(authority, request)
        else:
            if type(expected_admission) is not native.Admission:
                return _unavailable("ADMISSION_INVALID")
            # An existing compositor may already have performed its native
            # metadata preflight. This pin is NOT trusted as fresh permission:
            # read_disclosure still resolves/rechecks the actual owner before
            # and after artifact reads, against the exact supplied Admission.
            admission = expected_admission
            admission.validate(request, None)
        if not REQUIRED_FIELDS <= admission.allowed_fields:
            return _unavailable("PROJECTION_FIELDS_NOT_ADMITTED")
        selected = native.read_disclosure(
            store, authority, request, expected_admission=admission,
        )
        return _project_selected(admission, request, selected)
    except native.DisclosureError as exc:
        return _unavailable(exc.code)
