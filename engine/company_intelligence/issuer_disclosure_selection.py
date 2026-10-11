"""Current issuer-scoped discovery from trusted Company Intelligence selections.

This is a projection of the native current selection, never a ticker-to-fact
allocator or an earnings event. The production owner must publish/admit its
selection before exposing this capability. No default empty generation exists.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Callable, Protocol

from lib.dataos.identity import parse_id
from . import issuer_disclosures as native

SCHEMA = "company_intelligence.private_issuer_selections/v1"
MAX_SELECTIONS = 16


def issuer_identity(value: str) -> str:
    try:
        kind, _ = parse_id(value)
    except (ValueError, TypeError):
        raise native.DisclosureError("ISSUER_INVALID") from None
    native._require(type(value) is str and kind == "issuer" and value.startswith("ISS:")
                    and value == value.strip() and len(value) <= 128, "ISSUER_INVALID")
    return value


@dataclass(frozen=True)
class SelectionEntry:
    fact_id: str
    fact_reference: native.Reference
    edition_reference: native.Reference

    def validate(self) -> None:
        native._require(type(self.fact_id) is str and re.fullmatch(r"integration:[0-9a-f]{64}", self.fact_id) is not None, "SELECTION_INVALID")
        native._require(type(self.fact_reference) is native.Reference and self.fact_reference.schema == native.FACT_SCHEMA, "SELECTION_INVALID")
        native._require(type(self.edition_reference) is native.Reference and self.edition_reference.schema == native.EDITION_SCHEMA, "SELECTION_INVALID")


@dataclass(frozen=True)
class IssuerSelection:
    issuer_id: str
    evidenced_cik: str
    identity_snapshot_schema: str
    identity_snapshot_sha256: str
    identity_snapshot_byte_length: int
    generation: str
    purpose: str
    audience: str
    selections: tuple[SelectionEntry, ...]

    def validate(self, issuer_id: str, purpose: str, audience: str) -> None:
        native._require(self.issuer_id == issuer_identity(issuer_id)
                        and (self.purpose, self.audience) == (purpose, audience), "SELECTION_BINDING_MISMATCH")
        native._require(type(self.evidenced_cik) is str and re.fullmatch(r"[0-9]{10}", self.evidenced_cik) is not None
                        and int(self.evidenced_cik) > 0, "SELECTION_IDENTITY_INVALID")
        native._identifier(self.identity_snapshot_schema)
        native._digest(self.identity_snapshot_sha256)
        native._integer(self.identity_snapshot_byte_length, 1, native.MAX_OBJECT_BYTES)
        native._identifier(self.generation)
        native._require(type(self.selections) is tuple and len(self.selections) <= MAX_SELECTIONS, "SELECTION_LIMIT")
        ids = []
        for entry in self.selections:
            native._require(type(entry) is SelectionEntry, "SELECTION_INVALID")
            entry.validate(); ids.append(entry.fact_id)
        native._require(ids == sorted(set(ids)), "SELECTION_DUPLICATE_OR_UNORDERED")


class SelectionOwner(Protocol):
    def resolve_issuer(self, issuer_id: str, purpose: str, audience: str) -> IssuerSelection | None:
        """Metadata-only, current subject/disclosing issuer selection.

        Resolve the evidenced CIK and exact immutable identity snapshot through
        the incumbent identity owner, never trust a caller CIK or ticker. Return
        only a qualified owner generation; None is unavailable, not empty. Each
        selected native artifact must be published and independently admitted
        for the same server purpose/audience before appearing in this projection.
        """
        ...


def _resolve(owner: SelectionOwner, issuer_id: str, purpose: str, audience: str) -> IssuerSelection:
    try:
        selection = owner.resolve_issuer(issuer_id, purpose, audience)
    except Exception:
        raise native.DisclosureError("SELECTION_UNAVAILABLE") from None
    native._require(type(selection) is IssuerSelection, "SELECTION_UNAVAILABLE")
    selection.validate(issuer_id, purpose, audience)
    return selection


def read_issuer_selection(owner: SelectionOwner, authority: native.DisclosureAuthority,
                          store_factory: Callable[[], object], issuer_id: str, *, purpose: str, audience: str) -> dict:
    """Authenticate upstream; admit every row before constructing private Store."""
    issuer_identity(issuer_id)
    snapshot = _resolve(owner, issuer_id, purpose, audience)
    requests, admissions = [], []
    for entry in snapshot.selections:
        req = native.Request(entry.fact_id, purpose, audience)
        admission = native.preflight(authority, req)
        native._require(admission.reference == entry.fact_reference and admission.edition == entry.edition_reference
                        and admission.generation == snapshot.generation and admission.identity_mode == 'current'
                        and 'subject_id' in admission.allowed_fields, "SELECTION_ADMISSION_MISMATCH")
        binding = admission.subject_binding
        native._require(type(binding) is native.SubjectIdentityBinding
                        and (binding.issuer_id, binding.evidenced_cik, binding.snapshot_schema,
                             binding.snapshot_sha256, binding.snapshot_byte_length)
                        == (snapshot.issuer_id, snapshot.evidenced_cik, snapshot.identity_snapshot_schema,
                            snapshot.identity_snapshot_sha256, snapshot.identity_snapshot_byte_length),
                        "SELECTION_IDENTITY_MISMATCH")
        requests.append(req); admissions.append(admission)
    store = store_factory() if requests else None
    for entry, req in zip(snapshot.selections, requests):
        result = native.read_disclosure(store, authority, req)
        native._require(result['reference'] == entry.fact_reference.payload()
                        and result['edition'] == entry.edition_reference.payload()
                        and result['generation'] == snapshot.generation
                        and result['fact'].get('subject_id') == issuer_id, "SELECTION_ARTIFACT_MISMATCH")
    native._require(_resolve(owner, issuer_id, purpose, audience) == snapshot, "SELECTION_CHANGED")
    for req, admission in zip(requests, admissions):
        native._require(native.preflight(authority, req) == admission, "SELECTION_ADMISSION_CHANGED")
    return {'schema': SCHEMA, 'generation': snapshot.generation, 'identity_mode': 'current',
            'issuer_role': 'subject_disclosing_company',
            'issuer_binding': {'issuer_id': issuer_id, 'evidenced_cik': snapshot.evidenced_cik,
                               'identity_snapshot_reference': {'schema': snapshot.identity_snapshot_schema,
                                   'sha256': snapshot.identity_snapshot_sha256,
                                   'byte_length': snapshot.identity_snapshot_byte_length}},
            'selections': [{'fact_id': e.fact_id, 'fact_reference': e.fact_reference.payload(),
                            'edition_reference': e.edition_reference.payload(),
                            'kind': 'product_integration', 'lifecycle': 'planned'} for e in snapshot.selections]}
