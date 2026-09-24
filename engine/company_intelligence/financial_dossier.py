"""Pure validation helpers for the financial dossier delivery boundary."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from urllib.parse import urlparse

from engine.company_intelligence.documents import ABSENCE_REASONS


DELIVERY_INPUT_VALIDATOR_VERSION = "v1"
# Closed set of top-level refusal reasons. The pattern ``unknown_field:<name>``
# stays open-ended so unknown delivery-input keys can name themselves.
DELIVERY_REFUSAL_REASONS = frozenset(
    {
        "accepted_binding_missing",
        "identity_unresolved",
        "unsupported_cross_subject_join",
        "rights_unqualified",
        "route_unbound",
    }
)
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
# CIK length is 10 digits, with real issuers historically under 90M;
# any value at or above this threshold is treated as malformed, not as a
# future-tense registry. The shape is the only well-formedness rule — the
# registry call decides whether a shape-correct CIK resolves to a real issuer.
_CIK_UPPER_EXCLUSIVE = 90_000_000
_DIGEST_HEX = re.compile(r"[0-9a-f]{64}")
_OWNER_NAMESPACES: frozenset[str] = frozenset({"synthetic"})


def validate_delivery_inputs(
    inputs: Mapping[str, object],
    *,
    registry: Iterable[tuple[str, str]] | None = None,
    research_hosts: frozenset[str],
) -> dict[str, object]:
    """Classify inert research inputs without issuing any delivery permission.

    ``research_hosts`` is a closed set of research hosts supplied by the
    caller; the synthetic corpus supplies its own. No source URL outside that
    set is research-usable. A well-formed 10-digit CIK is necessary but not
    sufficient identity proof. ``identity`` is resolved only when
    ``company_id`` carries the corpus namespace and ``(company_id,
    external_ids.cik)`` is a registered pair in ``registry``. A missing/empty
    ``registry`` resolves nothing.

    ``registry`` is materialized into a ``frozenset`` once at entry so a
    generator caller cannot get contradictory ``live_admission`` and
    ``bindings.identity`` answers — every read in this function consumes the
    SAME frozen registry view.
    """
    if not isinstance(inputs, Mapping):
        raise TypeError("delivery inputs must be a mapping")

    materialized_registry: frozenset[tuple[str, str]] | None
    materialized_registry = None if registry is None else frozenset(registry)

    unknown = sorted(set(inputs) - _ALLOWED_INPUT_KEYS)
    reasons: list[str] = []
    if unknown:
        reasons.extend(f"unknown_field:{name}" for name in unknown)

    release_binding = inputs.get("release_binding")
    private_binding = inputs.get("private_binding")
    if not _accepted_binding(release_binding) or not _accepted_binding(private_binding):
        reasons.append("accepted_binding_missing")

    identity = inputs.get("identity")
    identity_status, identity_reason = _check_identity(identity, materialized_registry)
    if identity_status != "resolved":
        # Top-level reasons stay in the closed set; the finer
        # ``identity_not_registered`` lives only in ``bindings["identity"]["reason"]``.
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
        "identity": _checked_identity_value(identity, materialized_registry),
    }
    return {
        "live_admission": "admissible" if not reasons else "refused",
        "research_usable": _research_usable(inputs, research_hosts),
        "reasons": reasons,
        "bindings": bindings,
    }


def _research_usable(inputs: Mapping[str, object], research_hosts: frozenset[str]) -> bool:
    sources = inputs.get("sources")
    cells = inputs.get("cells")
    valid_sources = isinstance(sources, list) and bool(sources) and all(
        isinstance(source, Mapping)
        and isinstance(source.get("url"), str)
        and urlparse(source.get("url")).hostname in research_hosts
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
    return _inspect_binding(value)[0] == "accepted"


def _inspect_binding(value: object) -> tuple[str, str]:
    """Return ``(status, reason)`` for a release/private binding.

    ``status`` is ``"accepted"`` iff ``owner_ref`` carries a registered
    namespace and ``digest`` is a 64-character lowercase hex string. Any
    malformed field returns the most specific reason code first.
    """
    if not isinstance(value, Mapping):
        return ("unavailable", "missing")
    status = value.get("status")
    if status != "accepted":
        return ("unavailable", "binding_not_accepted")
    owner_ref = value.get("owner_ref")
    if not isinstance(owner_ref, str) or not owner_ref:
        return ("unavailable", "owner_ref_missing")
    namespace = owner_ref.split(":", 1)[0]
    if namespace not in _OWNER_NAMESPACES:
        return ("unavailable", "owner_namespace_unregistered")
    revision = value.get("revision")
    if not isinstance(revision, str) or not revision:
        return ("unavailable", "revision_missing")
    digest = value.get("digest")
    if not isinstance(digest, str) or isinstance(digest, bool):
        return ("unavailable", "digest_malformed")
    if not _DIGEST_HEX.fullmatch(digest):
        return ("unavailable", "digest_malformed")
    return ("accepted", "")


def _valid_typed_absence(value: object) -> bool:
    return isinstance(value, str) and value in _TYPED_ABSENCE_REASONS


def _check_identity(
    value: object,
    registry: Iterable[tuple[str, str]] | None,
) -> tuple[str, str]:
    """Return ``(status, reason)`` for the identity block.

    Reason codes:
    - ``identity_unresolved``: malformed/missing fields, cik fails 10-digit shape.
    - ``identity_not_registered``: well-formed but pair not in ``registry``
      (or registry not supplied).
    """
    if not isinstance(value, Mapping):
        return ("unresolved", "identity_unresolved")
    company_id = value.get("company_id")
    external_ids = value.get("external_ids")
    if not isinstance(company_id, str) or not company_id:
        return ("unresolved", "identity_unresolved")
    if not isinstance(external_ids, Mapping) or "cik" not in external_ids:
        return ("unresolved", "identity_unresolved")
    cik = external_ids.get("cik")
    if not isinstance(cik, str) or not _CIK_SHAPE.fullmatch(cik):
        return ("unresolved", "identity_unresolved")
    if int(cik) >= _CIK_UPPER_EXCLUSIVE:
        return ("unresolved", "identity_unresolved")
    if not company_id.startswith("synthetic:"):
        return ("unresolved", "identity_not_registered")
    if registry is None:
        return ("unresolved", "identity_not_registered")
    if (company_id, cik) not in frozenset(registry):
        return ("unresolved", "identity_not_registered")
    return ("resolved", "")


def _checked_binding(value: object) -> dict[str, object]:
    status, reason = _inspect_binding(value)
    if not isinstance(value, Mapping):
        return {"status": status, "reason": reason}
    result: dict[str, object] = {
        "owner_ref": value.get("owner_ref"),
        "revision": value.get("revision"),
        "digest": value.get("digest"),
    }
    result["status"] = status
    if reason:
        result["reason"] = reason
    return result


def _checked_identity_value(
    value: object,
    registry: Iterable[tuple[str, str]] | None,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {"status": "unresolved", "reason": "missing"}
    status, reason = _check_identity(value, registry)
    external_ids = value.get("external_ids")
    result = {
        "company_id": value.get("company_id"),
        "external_ids": external_ids if isinstance(external_ids, Mapping) else {},
    }
    result["status"] = status
    if reason:
        result["reason"] = reason
    return result
