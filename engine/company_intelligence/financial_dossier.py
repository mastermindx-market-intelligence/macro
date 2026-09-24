"""Pure validation helpers for the financial dossier delivery boundary."""

from __future__ import annotations

from collections.abc import Mapping
import re
from urllib.parse import urlparse

from engine.company_intelligence.documents import ABSENCE_REASONS


DELIVERY_INPUT_VALIDATOR_VERSION = "v1"
_ALLOWED_INPUT_KEYS = frozenset(
    {
        "synthetic",
        "issuer",
        "sources",
        "cells",
        "events",
        "release_binding",
        "private_binding",
        "identity",
        "cross_subject_join",
    }
)
_TYPED_ABSENCE_REASONS = ABSENCE_REASONS
_CIK_SHAPE = re.compile(r"\d{10}")
_NINE_M_OR_LATER = 90_000_000


def validate_delivery_inputs(inputs: Mapping[str, object]) -> dict[str, object]:
    """Classify inert research inputs without issuing any delivery permission."""
    if not isinstance(inputs, Mapping):
        raise TypeError("delivery inputs must be a mapping")

    unknown = sorted(set(inputs) - _ALLOWED_INPUT_KEYS)
    reasons: list[str] = []
    if unknown:
        reasons.extend(f"unknown_field:{name}" for name in unknown)

    release_binding = inputs.get("release_binding")
    private_binding = inputs.get("private_binding")
    if not _accepted_binding(release_binding) or not _accepted_binding(private_binding):
        reasons.append("accepted_binding_missing")

    identity = inputs.get("identity")
    if not _resolved_identity(identity):
        reasons.append("identity_unresolved")

    join = inputs.get("cross_subject_join")
    if join is not None:
        reasons.append("unsupported_cross_subject_join")

    rights = inputs.get("private_binding")
    if _accepted_binding(rights) and isinstance(rights, Mapping) and rights.get("rights_state") not in {
        "public_primary",
        "licensed",
        "internal_only",
    }:
        reasons.append("rights_unqualified")

    bindings: dict[str, object] = {
        "release_binding": _checked_binding(release_binding),
        "private_binding": _checked_binding(private_binding),
        "identity": _checked_identity(identity),
    }
    return {
        "live_admission": "admissible" if not reasons else "refused",
        "research_usable": _research_usable(inputs),
        "reasons": reasons,
        "bindings": bindings,
    }


def _research_usable(inputs: Mapping[str, object]) -> bool:
    sources = inputs.get("sources")
    cells = inputs.get("cells")
    valid_sources = isinstance(sources, list) and bool(sources) and all(
        isinstance(source, Mapping)
        and isinstance(source.get("url"), str)
        and urlparse(source.get("url")).hostname == "example.invalid"
        and source.get("rights_state") in {"public_primary", "licensed", "internal_only", "unknown"}
        for source in sources
    )
    valid_cells = not isinstance(cells, list) or all(
        isinstance(item, Mapping)
        and "owner_ref" in item
        and ("value" in item or _valid_typed_absence(item.get("absence")))
        for item in cells
    )
    return valid_sources and valid_cells


def _accepted_binding(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("status") == "accepted"
        and isinstance(value.get("owner_ref"), str)
        and bool(value.get("owner_ref"))
        and isinstance(value.get("revision"), str)
        and bool(value.get("revision"))
        and isinstance(value.get("digest"), str)
        and len(str(value.get("digest"))) == 64
        and not isinstance(value.get("digest"), bool)
    )


def _valid_typed_absence(value: object) -> bool:
    return isinstance(value, str) and value in _TYPED_ABSENCE_REASONS


def _resolved_identity(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    company_id = value.get("company_id")
    external_ids = value.get("external_ids")
    if not isinstance(company_id, str) or not company_id:
        return False
    if not isinstance(external_ids, Mapping) or "cik" not in external_ids:
        return False
    cik = external_ids.get("cik")
    if not isinstance(cik, str) or not _CIK_SHAPE.fullmatch(cik):
        return False
    return int(cik) < _NINE_M_OR_LATER


def _checked_binding(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {"status": "unavailable", "reason": "missing"}
    result: dict[str, object] = {
        "owner_ref": value.get("owner_ref"),
        "revision": value.get("revision"),
        "digest": value.get("digest"),
    }
    result["status"] = "accepted" if _accepted_binding(value) else "unavailable"
    if result["status"] == "unavailable":
        result["reason"] = "binding_not_accepted"
    return result


def _checked_identity(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {"status": "unresolved", "reason": "missing"}
    resolved = _resolved_identity(value)
    result = {
        "company_id": value.get("company_id"),
        "external_ids": value.get("external_ids") if isinstance(value.get("external_ids"), Mapping) else {},
    }
    result["status"] = "resolved" if resolved else "unresolved"
    if not resolved:
        result["reason"] = "identity_unresolved"
    return result
