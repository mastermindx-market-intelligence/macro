"""Read-only composition for the entitled institutional research consumer.

The catalog owns the reporting facts. Neither a reporting CIK nor a position's
SOLE discretion establishes economic vehicle, strategy or canonical security
identity. This consumer exposes that distinction without constructing a recipe,
writing a store, or admitting purpose-specific K3E use.
"""
from __future__ import annotations

from threading import BoundedSemaphore
from time import monotonic
from typing import Any

from engine.institutional_census.k3e_projection import project_reported_holding
from engine.institutional_census.storage import build_institutional_13f_store
from lib.evidence_foundation import ALL_FALSE_AUTHORITY

SCHEMA = "institutional_13f.authenticated_research_context.v1"
MAX_READ_BYTES = 64 * 1024 * 1024
MAX_READ_CALLS = 16
MAX_READ_SECONDS = 30
_READ_SLOT = BoundedSemaphore(1)
_CONTEXT_FIELDS = frozenset({
    "schema", "valid", "state", "refusals", "owner", "authority",
    "financial_influence", "k3e_admissible", "generation", "filing", "holding",
    "reporting_structure", "interpretation", "qualification",
})


class ResearchContextUnavailable(RuntimeError):
    """The bounded consumer could not safely complete its owner read."""


class _ReadOnlyBudget:
    """Limit aggregate reads in addition to the owner's per-object bounds.

    Time checks are cooperative between owner operations, not cancellation of
    an in-flight network read. The single read slot remains held until it exits.
    There is no unbounded read fallback and no write capability on this facade.
    """

    def __init__(self, store: Any):
        self._store = store
        self._remaining = MAX_READ_BYTES
        self._calls = 0
        self._deadline = monotonic() + MAX_READ_SECONDS
        self.exhausted = False

    def _check(self):
        if self._calls >= MAX_READ_CALLS or monotonic() > self._deadline:
            self.exhausted = True
            raise ResearchContextUnavailable("institutional research read budget exceeded")

    def get_bytes_strict(self, key):
        self.exhausted = True
        raise ResearchContextUnavailable("unbounded institutional research read refused")

    def _forbidden(self, *args, **kwargs):
        self.exhausted = True
        raise ResearchContextUnavailable("non-read institutional store operation refused")

    # The owner's legacy structural read protocol inherits Store's write/list
    # names. Refusal stubs satisfy its type check without delegating effects.
    get_bytes = put_bytes = list_prefix = exists = upload_time = _forbidden

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        self._check()
        if self._remaining <= 0:
            self.exhausted = True
            raise ResearchContextUnavailable("institutional research byte budget exceeded")
        self._calls += 1
        bound = min(maximum_bytes, self._remaining)
        try:
            payload = self._store.get_bytes_strict_bounded(key, bound)
        except Exception:
            # A source larger than the aggregate bound must not fall back to an
            # unbounded read. The HTTP boundary redacts all backend exceptions.
            if bound < maximum_bytes:
                self.exhausted = True
            raise
        if payload is not None:
            if type(payload) is not bytes or len(payload) > bound:
                self.exhausted = True
                raise ResearchContextUnavailable("institutional owner exceeded read bound")
            self._remaining -= len(payload)
        if monotonic() > self._deadline:
            self.exhausted = True
            raise ResearchContextUnavailable("institutional research time budget exceeded")
        return payload


def _compose_context(context: dict) -> dict:
    if (type(context) is not dict or set(context) - _CONTEXT_FIELDS
            or not ALL_FALSE_AUTHORITY
            or any(value is not False for value in ALL_FALSE_AUTHORITY.values())
            or context.get("authority") != "descriptive_context_only"
            or context.get("k3e_admissible") is not False
            or context.get("financial_influence") is not False
            or context.get("state") not in {"AVAILABLE_UNQUALIFIED", "UNAVAILABLE", "REFUSED"}):
        raise ResearchContextUnavailable("unexpected institutional authority contract")
    if context["state"] == "AVAILABLE_UNQUALIFIED" and context.get("valid") is not True:
        raise ResearchContextUnavailable("incoherent institutional availability")
    available = context.get("valid") is True and context["state"] == "AVAILABLE_UNQUALIFIED"
    filing = context.get("filing") or {}
    holding = context.get("holding") or {}
    # JSON numbers cannot carry every native int64 row key through browser
    # clients. Transport the exact decimal identity as text, never a rounded key.
    if holding.get("infotable_sk") is not None:
        if type(holding["infotable_sk"]) is not int or not 0 <= holding["infotable_sk"] <= 2**63 - 1:
            raise ResearchContextUnavailable("invalid native holding row identity")
        holding = {**holding, "infotable_sk": str(holding["infotable_sk"])}
        context = {**context, "holding": holding}
    return {
        "schema": SCHEMA,
        "state": context["state"],
        "context": context,
        "semantic_bindings": {
            "reporting_entity": {
                "state": "OWNER_VERIFIED" if available else "UNAVAILABLE",
                "owner": "engine.institutional_census",
                "filer_cik": filing.get("filer_cik") if available else None,
                "filer_name": filing.get("filer_name") if available else None,
                "accession": filing.get("accession") if available else None,
                "source_receipt_id": filing.get("source_receipt_id") if available else None,
            },
            "security": {
                "state": "UNRESOLVED",
                "reported_cusip": holding.get("cusip") if available else None,
                "canonical_security_id": None,
                "reason": "CANONICAL_SECURITY_BINDING_UNAVAILABLE",
            },
            "economic_vehicle": {
                "state": "UNRESOLVED", "vehicle_epoch_id": None,
                "vehicle_class": None, "manager_complex_id": None,
                "reason": "REPORTING_SCOPE_DOES_NOT_IDENTIFY_ECONOMIC_VEHICLE",
            },
            "strategy": {
                "state": "UNRESOLVED", "decision_mode": None,
                "reason": "POSITION_DISCRETION_DOES_NOT_IDENTIFY_STRATEGY",
            },
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
        "persistence": "none",
    }


def read_reported_holding_context(**selection) -> dict:
    """Use only the dedicated native store and exact selection supplied by API.

    Production accepts no local path, URL, owner payload, credentials or resolver
    registry. Tests may replace the existing store-builder function explicitly.
    Missing dedicated configuration is unavailable, never a generic R2 fallback.
    """
    if not _READ_SLOT.acquire(blocking=False):
        raise ResearchContextUnavailable("institutional research read busy")
    try:
        store = _ReadOnlyBudget(build_institutional_13f_store())
        context = project_reported_holding(store, **selection, accession_scope=True)
        if store.exhausted:
            raise ResearchContextUnavailable("institutional research read budget exceeded")
        return _compose_context(context)
    finally:
        _READ_SLOT.release()
