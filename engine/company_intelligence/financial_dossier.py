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

# --------------------------------------------------------------------------------------
# Required-versus-optional evidence view (Industrials T06: IND-D23, IND-R201, IND-R215,
# IND-R218, IND-SF04, commissioned as ONE capability by Sol ruling 5894912727 on #7789).
# --------------------------------------------------------------------------------------

EVIDENCE_VIEW_VERSION = "v1"

#: Conclusions this view may never originate. Withheld whenever the market expectation
#: they would be measured against is absent. IND-R218 lets the operating economics be
#: EXPLAINED without consensus; it forbids the conclusion, not the explanation.
WITHHELD_CONCLUSIONS: frozenset[str] = frozenset(
    {"mispricing", "valuation_gap", "probability", "rank", "entry", "size", "trade"}
)

#: Extensions whose ABSENCE is a disclosed limitation rather than a refusal. The theme
#: graph belongs to another owner and is legitimately unbuilt here (IND-R201); consensus
#: is third-party and often simply does not exist for a name (IND-R218).
OPTIONAL_EXTENSIONS: frozenset[str] = frozenset({"theme_graph", "consensus"})

#: Physical-production vocabulary that must never be attached to a service business
#: (IND-SF04). A supplied key is REFUSED by name rather than echoed or silently dropped:
#: dropping it would make a fabricated dependency indistinguishable from an absent one.
_PHYSICAL_PRODUCTION_FIELDS: frozenset[str] = frozenset(
    {"bom", "bill_of_materials", "wafer_starts", "wafer_measure", "production_stage", "stage"}
)

_SERVICE_MODELS: frozenset[str] = frozenset({"service"})

#: Limitation prefixes that describe a MODEL MISMATCH rather than an evidence gap, and so
#: must be disclosed without degrading the page verdict. A service company with no bill of
#: materials is completely described, not partially evidenced (``IND-SF04`` clause 1). Kept
#: as an explicit tuple, never a general rule: widening it is how a real gap gets
#: reclassified as harmless.
_NON_EVIDENCE_LIMITATION_PREFIXES: tuple[str, ...] = ("physical_model_refused:",)
_DERIVATION_REF_FIELDS = ("formula", "formula_version", "operand_refs", "receipt_ref")


def assemble_evidence_view(
    *,
    derivations: Mapping[str, Mapping[str, object]],
    prose: Mapping[str, Iterable[str]] | None = None,
    extensions: Mapping[str, object] | None = None,
    business_model: str,
    operating_model: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose one dossier view from already-derived result-to-cash values.

    The view NEVER computes, re-rounds, re-signs or re-labels a number: each section
    mirrors its derivation's own ``status`` and quotes its ``value`` verbatim, or reports
    the refusal the derivation returned (R-IND ruling R3/R7). ``derivations`` values are
    ``derive_result_cash`` results; this function does not call it, so it cannot disagree
    with it.

    The four behaviours it makes true, each the compliant half of an obligation whose
    violating half is the thing that used to be possible:

    * a section whose REQUIRED operand is unavailable is not ``ready``, carries no value,
      and every prose block depending on it is withheld with that section named -- so a
      missing number cannot surface as a zero, an invented figure, or a page that reports
      success while one of its claims has no evidence (``IND-D23``);
    * an absent OPTIONAL extension is disclosed as a limitation and leaves every section
      that does not depend on it at its own status, so qualified operating analysis stays
      usable when the theme graph is unbuilt (``IND-R201``);
    * required refusal and optional absence stay distinct outcomes, never collapsing into
      one (``IND-R215``);
    * with consensus absent, every conclusion in :data:`WITHHELD_CONCLUSIONS` is withheld
      by name while the operating explanation remains readable (``IND-R218``);
    * a service business carries no physical-production field at all, and a supplied one
      is refused by name rather than echoed (``IND-SF04``).

    ``prose`` maps a prose block to the section names it asserts over, and lands in one of
    three states, because "not ready" and "not readable" are different facts:

    * ``ready`` - every section it asserts over is ``ready``;
    * ``qualified`` - some section is ``limited``, so the supported figure stands and the
      block is READABLE with the limitation attached (this is the half that keeps an
      optional absence from reading like a refusal, ``IND-R215``);
    * ``withheld`` - some section is ``refused``, or names a section that does not exist.

    The dependency is declared by the caller because only the caller knows what its
    sentences claim - inferring it from section names would let a renamed section silently
    un-block prose. An undeclared section name fails CLOSED: a block asserting over
    something absent is withheld, never published.

    The returned ``status`` is the PAGE's own verdict, and it exists because two of these
    obligations are about the page rather than a section - ``IND-D23``'s "no all-page false
    success" and ``IND-R201``'s "no full-vertical acceptance". It is ``ready`` only when
    the view carries no EVIDENCE limitation, ``incomplete`` when anything is refused or
    withheld, and ``qualified`` in between: readable, disclosed, and explicitly not an
    acceptance. A refused physical-production field is disclosed but does not degrade it -
    see :data:`_NON_EVIDENCE_LIMITATION_PREFIXES`.
    """
    if not isinstance(derivations, Mapping):
        raise TypeError("derivations must be a mapping of section name to derivation")
    if business_model not in _SERVICE_MODELS | {"manufacturing"}:
        raise ValueError("business_model must be 'service' or 'manufacturing'")

    limitations: list[str] = []

    sections: dict[str, object] = {}
    for name in sorted(derivations):
        derivation = derivations[name]
        if not isinstance(derivation, Mapping):
            raise TypeError(f"derivation for {name!r} must be a mapping")
        status = derivation.get("status")
        value = derivation.get("value")
        # Quoted verbatim, with ONE exception that is not a recomputation: a `refused`
        # derivation may not publish a number. `derive_result_cash` already returns None
        # there, so this only fires out-of-contract - and a figure sitting under a refusal
        # is worse than an invented one, because it looks derived. The drop is recorded, so
        # it can never be a silent substitution (``IND-D23``).
        if status == "refused" and value is not None:
            limitations.append(f"value_dropped_under_refusal:{name}")
            value = None
        row: dict[str, object] = {
            "status": status,
            "value": value,
            "limitations": list(derivation.get("limitations") or ()),
        }
        for field in _DERIVATION_REF_FIELDS:
            row[field] = derivation.get(field)
        sections[name] = row
        if status != "ready":
            limitations.append(f"section_not_ready:{name}")
        for code in row["limitations"]:
            limitations.append(f"section_limitation:{name}:{code}")

    extension_states: dict[str, object] = {}
    supplied = dict(extensions or {})
    unknown_extensions = sorted(set(supplied) - OPTIONAL_EXTENSIONS)
    for name in sorted(OPTIONAL_EXTENSIONS):
        value = supplied.get(name)
        if value is None:
            extension_states[name] = {"state": "absent", "reason": "not_supplied"}
            limitations.append(f"extension_absent:{name}")
        elif isinstance(value, str):
            # A typed absence: the caller knows it is gone and why.
            reason = value if _valid_typed_absence(value) else "reason_unrecognised"
            extension_states[name] = {"state": "absent", "reason": reason}
            limitations.append(f"extension_absent:{name}")
        else:
            extension_states[name] = {"state": "present", "reason": None}

    prose_blocks: dict[str, object] = {}
    for block in sorted(prose or {}):
        depends = list((prose or {})[block])
        # An undeclared dependency BLOCKS. A block asserting over a section this view does
        # not hold has no evidence at all, which is strictly worse than a refused one.
        unknown_deps = {dep for dep in depends if dep not in sections}
        blocking = sorted(
            {
                dep
                for dep in depends
                if dep in sections and sections[dep]["status"] == "refused"
            }
            | unknown_deps
        )
        qualifying = sorted(
            dep
            for dep in depends
            if dep in sections and sections[dep]["status"] == "limited"
        )
        if blocking:
            status = "withheld"
        elif qualifying:
            status = "qualified"
        else:
            status = "ready"
        prose_blocks[block] = {
            "status": status,
            "blocked_by": blocking,
            "qualified_by": qualifying,
        }
        for dep in blocking:
            limitations.append(f"prose_withheld:{block}:{dep}")
        if status == "qualified":
            for dep in qualifying:
                limitations.append(f"prose_qualified:{block}:{dep}")

    # IND-R218: the conclusion is withheld exactly when the expectation it would be
    # measured against is absent. Nothing here produces one when it is present either -
    # this module never originates a conclusion at all; it reports which ones are barred.
    consensus_absent = extension_states["consensus"]["state"] == "absent"
    withheld = sorted(WITHHELD_CONCLUSIONS) if consensus_absent else []
    if consensus_absent:
        limitations.append("conclusions_withheld:no_consensus")

    model: dict[str, object] = {"business_model": business_model}
    refused_fields: list[str] = []
    for key in sorted(operating_model or {}):
        if business_model in _SERVICE_MODELS and key in _PHYSICAL_PRODUCTION_FIELDS:
            refused_fields.append(key)
            continue
        model[key] = (operating_model or {})[key]
    if refused_fields:
        limitations.extend(f"physical_model_refused:{key}" for key in refused_fields)
    model["refused_fields"] = refused_fields

    for name in unknown_extensions:
        limitations.append(f"unknown_extension:{name}")

    # IND-D23 / IND-R201: the page may not read as a success while any part of it is
    # missing. `ready` therefore requires an EMPTY limitation list rather than merely
    # the absence of a refusal - an undisclosed absence is exactly the false success.
    refused_anything = any(row["status"] == "refused" for row in sections.values())
    withheld_anything = any(
        block["status"] == "withheld" for block in prose_blocks.values()
    )
    evidence_limitations = [
        code
        for code in limitations
        if not code.startswith(_NON_EVIDENCE_LIMITATION_PREFIXES)
    ]
    if refused_anything or withheld_anything:
        status = "incomplete"
    elif evidence_limitations:
        status = "qualified"
    else:
        status = "ready"

    return {
        "view_version": EVIDENCE_VIEW_VERSION,
        "status": status,
        "sections": sections,
        "prose": prose_blocks,
        "extensions": extension_states,
        "operating_model": model,
        "withheld_conclusions": withheld,
        "limitations": sorted(set(limitations)),
    }
