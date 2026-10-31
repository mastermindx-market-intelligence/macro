"""Publish ONE Capital Structure state generation over the verified compiler generation.

Capital Structure Intelligence V2, masterplan row U1 (SPEC_U1_API §1-§3, §5, §6,
§10).  This is the producer half: nothing before it built a
:class:`~engine.capital_structure.issuer_state_contracts.CapitalState`.  One
offline run turns the verified event compiler generation, its bound ingestion
health horizon and the served ``projection.json`` into a single published
``state_bundle.json`` holding one state per covered issuer -- every state bound
to the SAME three input generations -- or nothing at all.

The law this module enforces:

* **One generation or nothing.**  The served projection must bind the verified
  telemetry generation and its own body digest; a mismatch withholds the whole
  bundle rather than publishing a partial one (SPEC §2, gate 5).
* **No second calculation path.**  Every family is integrated by
  :func:`engine.capital_structure.registration_integration.integrate_registration_paths`
  and every record is built by the frozen contract classes.  The reader
  re-derives a then-known view through :func:`then_known_state`, which calls the
  SAME integrator (SPEC §5).
* **Inherited unavailability is whole.**  ``unavailable`` is
  ``INHERITED_UNAVAILABLE_CAPABILITIES`` and ``capabilities_proven`` is empty;
  dropping one capability without a :class:`CapabilityProof` is a
  :class:`ContractViolation` (A06, gate 4).
* **Three horizons stay independent.**  Source observation, material filing and
  generation age are separate fields; telemetry ``status`` and throughput never
  enter any of them (A03, gate 8).
* **Coverage names its denominator.**  ``examined``/``total`` always ship with a
  ``partial`` support and ``no_active_path`` is emitted only when every declared
  route was examined and found ineligible (A33, gate 11).
* **Separation law (SPEC §10).**  Facts and historical knowledge only: no
  supply, no cash number, no rank, size, entry, score, probability or
  recommendation anywhere in the bundle.  Authority is ``AUTHORITY`` verbatim.

Deterministic, offline, exact-arithmetic only: no float and no float-returning
``timedelta`` accessor anywhere in this module -- an age is whole days times
86400 plus whole seconds -- and no SEC request.  Every URL written into the
evidence index is copied from source-ledger data and only when it is
accession-specific.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from engine.capital_structure.issuer_state_contracts import (
    AUTHORITY,
    COMPATIBLE_INPUT_SCHEMAS,
    INHERITED_UNAVAILABLE_CAPABILITIES,
    STATE_CONTRACT_VERSION,
    CalculationReceipt,
    CapabilityProof,
    CapitalInputs,
    CapitalState,
    ContractViolation,
    FamilyProvenance,
    FamilyState,
    GenerationBinding,
    StateRequest,
    _assert_safe_keys,
    load_state_schema,
    sha256_of,
    stable_id,
)
from engine.capital_structure.projection import PROJECTION_BUNDLE_SCHEMA
from engine.capital_structure.projection import _stable_id as _projection_stable_id
from engine.capital_structure.registration_integration import (
    REGISTRATION_FAMILY,
    RegistrationIntegration,
    _iso_z,
    integrate_registration_paths,
)
from engine.capital_structure.rule_applicability import RuleApplicabilityPack
from engine.capital_structure.verified_projection_generation import (
    VerifiedProjectionGeneration,
)

# ---------------------------------------------------------------------------
# Names and versions
# ---------------------------------------------------------------------------

STATE_BUNDLE_SCHEMA = "capital_structure.state_bundle.v1"
STATE_BUNDLE_VERSION = "capital-structure-state-bundle/1.0.0"
STATE_BUNDLE_SCHEMA_FILE = "capital_structure_state_bundle.v1.schema.json"
STATE_BUNDLE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / STATE_BUNDLE_SCHEMA_FILE
)

#: Implementation half of the calculation receipt: the frozen contract version
#: this producer was written against plus this producer's own version.  Derived,
#: never hand-written, so a contract bump changes every receipt.
STATE_BUNDLE_IMPLEMENTATION_DIGEST = sha256_of(
    {"contract": STATE_CONTRACT_VERSION, "implementation": STATE_BUNDLE_VERSION}
)

EVENTS_FAMILY = "events"
EVENT_EDGES_FAMILY = "event_edges"
PROJECTION_FAMILY = "event_projection"

#: The shelf form families whose eligibility routes a coverage denominator may
#: declare (SPEC §6).  A non-shelf family observes no route at all, which is its
#: own named reason rather than a zero denominator.
_SHELF_ROUTE_PREFIXES = {
    "registration_s3": "form_s3.I.B.",
    "registration_f3": "form_f3.I.B.",
}

_ANCHOR_NOT_SPECIFIC = "anchor_not_accession_specific"
_MANIFEST_UNRESOLVED = "manifest_unresolved"
_UNKNOWN_GRADE = "unknown"
_NOT_EVALUATED = "eligibility_route_not_evaluated"
_NO_SHELF_FAMILY = "no_shelf_form_family_observed"
_UNKNOWN_AT_DATE = "unknown_at_date"
_SECONDS_PER_DAY = 86400


# ---------------------------------------------------------------------------
# Small exact helpers (no float anywhere in this module)
# ---------------------------------------------------------------------------


def _parse_instant(value: Any, field: str = "timestamp") -> datetime:
    """Aware UTC instant, normalized through the lifecycle compiler's own form."""
    return datetime.fromisoformat(_iso_z(value, field).replace("Z", "+00:00"))


def _require_generation(telemetry: Any) -> Mapping[str, Any]:
    if not isinstance(telemetry, Mapping):
        raise ValueError("no verified capital-structure generation")
    if not telemetry.get("generation_id"):
        raise ValueError("no verified capital-structure generation")
    return telemetry


def _ledger_digest(telemetry: Mapping[str, Any], artifact: str) -> str:
    """One 64-hex ledger digest of the verified generation, or a refusal."""
    hashes = telemetry.get("artifact_hashes")
    digest = hashes.get(artifact) if isinstance(hashes, Mapping) else None
    if not isinstance(digest, str) or not digest:
        raise ValueError(
            f"no verified capital-structure generation: telemetry.artifact_hashes.{artifact} is missing"
        )
    return digest


def _issuer_of(record: Mapping[str, Any]) -> str:
    issuer = record.get("issuer")
    if not isinstance(issuer, Mapping):
        return ""
    return str(issuer.get("issuer_id") or "")


def _available_at(event: Mapping[str, Any], field: str = "event.point_in_time.available_at") -> Any:
    point_in_time = event.get("point_in_time")
    if not isinstance(point_in_time, Mapping):
        return None
    return point_in_time.get("available_at")


def _filing_of(event: Mapping[str, Any]) -> Mapping[str, Any]:
    filing = event.get("filing")
    return filing if isinstance(filing, Mapping) else {}


def _cited_event_ids(path: Mapping[str, Any]) -> list[str]:
    """Every event a registration path's predicates cite (SPEC §2 evidence join)."""
    predicates = path.get("predicates")
    if not isinstance(predicates, Mapping):
        return []
    cited: set[str] = set()
    for predicate in predicates.values():
        if not isinstance(predicate, Mapping):
            continue
        for event_id in predicate.get("evidence_event_ids") or ():
            if event_id:
                cited.add(str(event_id))
    return sorted(cited)


def _lifecycle_event_ids(path: Mapping[str, Any]) -> set[str]:
    """The predicate citations plus the origin event that opened the lifecycle."""
    cited = set(_cited_event_ids(path))
    origin = path.get("origin")
    if isinstance(origin, Mapping) and origin.get("event_id"):
        cited.add(str(origin["event_id"]))
    return cited


def _family_records(family_state: Any) -> tuple[Mapping[str, Any], ...]:
    """Registration path records of a ``FamilyState`` or of its serialized form."""
    if isinstance(family_state, FamilyState):
        return tuple(family_state.records)
    if isinstance(family_state, Mapping):
        return tuple(family_state.get("records") or ())
    raise ContractViolation("family state must be a FamilyState or its record")


# ---------------------------------------------------------------------------
# Bindings (R3/R4): the served projection must bind the verified generation
# ---------------------------------------------------------------------------


def _require_bound_projection(
    telemetry: Mapping[str, Any], projection: Mapping[str, Any]
) -> None:
    """Refuse unless the served projection binds this exact verified generation.

    Two independent facts are required: the projection's ``source_receipt`` is
    the verified telemetry receipt, and the projection's ``generation_id`` is
    still the digest of its own body.  Either failure withholds the WHOLE bundle
    (SPEC §2, gate 5) -- a state generation may never bind a projection that was
    built from another generation, nor one whose bytes moved after signing.
    """
    if not isinstance(projection, Mapping):
        raise ValueError("served projection is required")
    receipt = projection.get("source_receipt")
    receipt = receipt if isinstance(receipt, Mapping) else {}
    if (
        receipt.get("generation_id") != telemetry.get("generation_id")
        or receipt.get("as_of") != telemetry.get("as_of")
        or dict(receipt.get("artifact_hashes") or {})
        != dict(telemetry.get("artifact_hashes") or {})
    ):
        raise ValueError("served projection does not bind the verified generation")
    body = {key: value for key, value in projection.items() if key != "generation_id"}
    if projection.get("generation_id") != _projection_stable_id("projection:cs:", body):
        raise ValueError("served projection generation_id does not match its body")


def _input_bindings(
    *, telemetry: Mapping[str, Any], projection: Mapping[str, Any], projection_sha256: str
) -> tuple[GenerationBinding, ...]:
    """The three bindings every state in one bundle shares, in family order.

    ``support`` is ``partial`` for all three: the projection is an event-state
    reader and the ledgers are correction-complete but term-poor.  Nothing here
    may ever claim ``supported`` (SPEC §10, A06).
    """
    generation_id = str(telemetry["generation_id"])
    source_as_of = _iso_z(telemetry.get("as_of"), "telemetry.as_of")
    events = GenerationBinding(
        EVENTS_FAMILY,
        COMPATIBLE_INPUT_SCHEMAS[EVENTS_FAMILY][0],
        "partial",
        generation_id=generation_id,
        artifact_sha256=_ledger_digest(telemetry, "event_versions"),
        as_of=source_as_of,
    )
    event_edges = GenerationBinding(
        EVENT_EDGES_FAMILY,
        COMPATIBLE_INPUT_SCHEMAS[EVENT_EDGES_FAMILY][0],
        "partial",
        generation_id=generation_id,
        artifact_sha256=_ledger_digest(telemetry, "event_edges"),
        as_of=source_as_of,
    )
    projection_generation_id = projection.get("generation_id")
    if not projection_generation_id:
        raise ValueError("served projection carries no generation_id")
    event_projection = GenerationBinding(
        PROJECTION_FAMILY,
        PROJECTION_BUNDLE_SCHEMA,
        "partial",
        generation_id=str(projection_generation_id),
        artifact_sha256=projection_sha256,
        as_of=_iso_z(projection.get("as_of"), "projection.as_of"),
    )
    return (events, event_edges, event_projection)


def _select_records(
    events: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """ALL event rows plus every edge whose two endpoints are both bound.

    Every correction version is kept: the lifecycle compiler owns version
    selection, and pre-filtering here would silently change the input digest the
    reader re-derives.  An edge whose endpoint is not a bound event is dropped
    exactly as the projection drops it; an edge crossing two issuers is refused.
    """
    bound: dict[str, Mapping[str, Any]] = {}
    for event in events:
        bound.setdefault(str(event["event_id"]), event)
    selected: list[dict[str, Any]] = []
    for edge in edges:
        from_id = str(edge.get("from_event_id") or "")
        to_id = str(edge.get("to_event_id") or "")
        if from_id not in bound or to_id not in bound:
            continue
        from_issuer = _issuer_of(bound[from_id])
        to_issuer = _issuer_of(bound[to_id])
        if not from_issuer or from_issuer != to_issuer:
            raise ValueError(f"cross-issuer event edge is forbidden: {edge.get('edge_id')}")
        selected.append(dict(edge))
    return tuple(dict(event) for event in events), tuple(selected)


def _inputs_from_generation(
    bindings: Sequence[GenerationBinding], generation: VerifiedProjectionGeneration
) -> CapitalInputs:
    """The ONE code path from a verified generation to accepted inputs.

    Both :func:`build_capital_inputs` (the producer) and :func:`issuer_inputs`
    (the reader's re-derivation) go through here, so a published ``input_digest``
    can only ever be reproduced by the same selection rule.
    """
    events, edges = _select_records(generation.events, generation.edges)
    return CapitalInputs(bindings=tuple(bindings), events=events, edges=edges)


def build_capital_inputs(
    generation: VerifiedProjectionGeneration,
    projection: Mapping[str, Any],
    *,
    projection_sha256: str,
) -> CapitalInputs:
    """Accepted inputs over the WHOLE verified generation, bound to the projection."""
    telemetry = _require_generation(generation.telemetry)
    _require_bound_projection(telemetry, projection)
    bindings = _input_bindings(
        telemetry=telemetry, projection=projection, projection_sha256=projection_sha256
    )
    return _inputs_from_generation(bindings, generation)


def inputs_for_issuer(inputs: CapitalInputs, issuer_id: str) -> CapitalInputs:
    """The same bindings narrowed to one issuer, in the generation's row order.

    Records are never sorted: ``input_digest`` is order-sensitive and the reader
    re-derives it the same way, so a reorder here would break the binding proof.
    """
    if not isinstance(inputs, CapitalInputs):
        raise ContractViolation("inputs must be a CapitalInputs")
    events = tuple(event for event in inputs.events if _issuer_of(event) == issuer_id)
    bound = {str(event["event_id"]) for event in events}
    edges = tuple(
        edge
        for edge in inputs.edges
        if str(edge.get("from_event_id") or "") in bound
        and str(edge.get("to_event_id") or "") in bound
    )
    return CapitalInputs(bindings=inputs.bindings, events=events, edges=edges)


# ---------------------------------------------------------------------------
# One issuer state (R5)
# ---------------------------------------------------------------------------


def issuer_state(
    inputs: CapitalInputs,
    *,
    issuer_id: str,
    as_of: str,
    generated_at: str,
    rule_pack: RuleApplicabilityPack | None,
    projection_generation_id: str,
    view_mode: str = "current",
) -> tuple[CapitalState, RegistrationIntegration]:
    """Integrate the registration family and seal it into one ``CapitalState``.

    The receipt carries THIS issuer's ``input_digest`` (the integrator's own
    receipt digests only the bindings, so it is identical across issuers and
    cannot prove which issuer's rows were read); its ``rule_digest`` is the
    integrator's, and its ``implementation_digest`` is this producer's.
    """
    if not isinstance(inputs, CapitalInputs):
        raise ContractViolation("inputs must be a CapitalInputs")
    for event in inputs.events:
        observed = _issuer_of(event)
        if observed != issuer_id:
            raise ValueError(
                f"inputs for issuer {issuer_id!r} carry an event of issuer {observed!r}"
            )
    reg = integrate_registration_paths(
        inputs, as_of=as_of, generated_at=generated_at, rule_pack=rule_pack
    )
    request = StateRequest(
        issuer_id,
        as_of,
        view_mode,
        inputs.bindings,
        rule_pack.rule_pack_id,
        rule_pack.version,
        rule_pack.file_sha256,
    )
    receipt = CalculationReceipt(
        input_digest=inputs.input_digest,
        rule_digest=reg.receipt.rule_digest,
        implementation_digest=STATE_BUNDLE_IMPLEMENTATION_DIGEST,
        computed_at=generated_at,
    )
    state = CapitalState(
        request,
        generated_at,
        families=(reg.family_state(),),
        receipt=receipt,
        projection_generation_id=projection_generation_id,
    )
    return state, reg


# ---------------------------------------------------------------------------
# Horizons (R7) -- three independent clocks, never telemetry status
# ---------------------------------------------------------------------------


def _horizons(
    *,
    events: Sequence[Mapping[str, Any]],
    generated_at: str,
    telemetry: Mapping[str, Any],
    health: Mapping[str, Any],
) -> dict[str, Any]:
    """The three independent horizons plus the health SLA they are judged against.

    ``source_observation_horizon`` is house knowledge (when Mastermind could see
    a row), ``material_filing_horizon`` is valid time (when the SEC accepted it)
    and ``generation_age_seconds`` is the compiler's own clock.  A throughput or
    ``status`` field in telemetry changes none of them (A03, gate 8).
    """
    observation: tuple[datetime, str] | None = None
    filing_horizon: tuple[date, str] | None = None
    for event in events:
        available_at = _available_at(event)
        if available_at:
            moment = _parse_instant(available_at)
            if observation is None or moment > observation[0]:
                observation = (moment, _iso_z(available_at, "event.point_in_time.available_at"))
        filed = _filing_of(event).get("filing_date")
        if isinstance(filed, str) and filed:
            try:
                day = date.fromisoformat(filed)
            except ValueError as exc:
                raise ValueError(
                    f"event.filing.filing_date: {filed!r} is not an ISO date"
                ) from exc
            if filing_horizon is None or day > filing_horizon[0]:
                filing_horizon = (day, day.isoformat())
    horizon = health.get("horizon") if isinstance(health, Mapping) else None
    if not isinstance(horizon, Mapping) or "target_sla_hours" not in horizon:
        raise ValueError("capital-structure health horizon is required for the state bundle")
    delta = _parse_instant(generated_at, "generated_at") - _parse_instant(
        telemetry.get("as_of"), "telemetry.as_of"
    )
    age_seconds = delta.days * _SECONDS_PER_DAY + delta.seconds
    if delta.days < 0 or age_seconds < 0:
        raise ValueError("generated_at cannot precede the verified generation clock")
    return {
        "source_observation_horizon": observation[1] if observation else None,
        "material_filing_horizon": filing_horizon[1] if filing_horizon else None,
        "generation_age_seconds": age_seconds,
        "freshness_sla_hours": horizon["target_sla_hours"],
    }


# ---------------------------------------------------------------------------
# Coverage denominators (R10, SPEC §6, A33)
# ---------------------------------------------------------------------------


def coverage_for(
    family_state: Any,
    *,
    rule_pack: RuleApplicabilityPack | None,
    route_verdicts: Mapping[str, str] | None = None,
    deferred: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Explicit denominator for one family: what was examined against what exists.

    ``total`` is derived from the rule pack for the shelf form families actually
    observed -- never a hard-coded count.  ``no_active_path`` is a STRONG claim
    and is emitted only when every declared route was examined and every verdict
    was ``ineligible``; otherwise the page shows partial/unknown copy.
    """
    records = _family_records(family_state)
    observed = set()
    for path in records:
        registration = path.get("registration") if isinstance(path, Mapping) else None
        if isinstance(registration, Mapping) and registration.get("registration_family"):
            observed.add(str(registration["registration_family"]))
    prefixes = tuple(
        prefix
        for family, prefix in sorted(_SHELF_ROUTE_PREFIXES.items())
        if family in observed
    )
    declared = rule_pack.rules if rule_pack is not None else {}
    routes = sorted(
        rule_id
        for rule_id in declared
        if any(str(rule_id).startswith(prefix) for prefix in prefixes)
    )
    total = len(routes)
    verdicts = dict(route_verdicts or {})
    examined = sum(1 for rule_id in routes if rule_id in verdicts)
    limits = family_state.provenance.support_limits if isinstance(
        family_state, FamilyState
    ) else tuple((family_state.get("provenance") or {}).get("support_limits") or ())
    codes = {str(code) for code in limits}
    for row in deferred:
        reason = row.get("reason") if isinstance(row, Mapping) else None
        if reason:
            codes.add(f"deferred:{reason}")
    if examined < total:
        codes.add(_NOT_EVALUATED)
    if total == 0:
        codes.add(_NO_SHELF_FAMILY)
    no_active_path = (
        total > 0
        and examined == total
        and all(verdicts.get(rule_id) == "ineligible" for rule_id in routes)
    )
    support = (
        family_state.provenance.support
        if isinstance(family_state, FamilyState)
        else str((family_state.get("provenance") or {}).get("support") or "")
    )
    return {
        "support": support,
        "examined": examined,
        "total": total,
        "routes": routes,
        "unexamined_reason_codes": sorted(codes),
        "no_active_path": no_active_path,
    }


def _bundle_coverage(per_issuer: Sequence[Mapping[str, Any]], issuer_count: int) -> dict[str, Any]:
    """The bundle denominator: sums of examined/total and the union of reasons.

    Support is ``unavailable`` only when EVERY issuer is unavailable; otherwise
    ``partial``.  It is never ``supported`` (SPEC §6, gate 3).
    """
    examined = 0
    total = 0
    codes: set[str] = set()
    supports: list[str] = []
    for row in per_issuer:
        examined += int(row["examined"])
        total += int(row["total"])
        codes.update(str(code) for code in row["unexamined_reason_codes"])
        supports.append(str(row["support"]))
    support = "unavailable" if all(item == "unavailable" for item in supports) else "partial"
    return {
        "issuer_count": issuer_count,
        "families": {
            REGISTRATION_FAMILY: {
                "support": support,
                "examined": examined,
                "total": total,
                "unexamined_reason_codes": sorted(codes),
            }
        },
    }


# ---------------------------------------------------------------------------
# Per-issuer side index (R8/R9) -- what the API needs and the contract forbids
# ---------------------------------------------------------------------------


def _ticker_observations(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Ticker changes as Mastermind observed them, collapsed to the transitions."""
    rows: list[dict[str, Any]] = []
    for event in events:
        issuer = event.get("issuer")
        ticker = issuer.get("ticker") if isinstance(issuer, Mapping) else None
        if not isinstance(ticker, str) or not ticker:
            continue
        available_at = _available_at(event)
        if not available_at:
            continue
        accession = _filing_of(event).get("accession")
        rows.append(
            {
                "ticker": ticker,
                "first_observed_at": _iso_z(
                    available_at, "event.point_in_time.available_at"
                ),
                "event_id": str(event["event_id"]),
                "accession": str(accession) if accession else None,
            }
        )
    rows.sort(key=lambda row: (row["first_observed_at"], row["event_id"]))
    kept: list[dict[str, Any]] = []
    for row in rows:
        if kept and kept[-1]["ticker"] == row["ticker"]:
            continue
        kept.append(row)
    return kept


def _path_evidence(
    records: Sequence[Mapping[str, Any]], by_event: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    """``path_id -> sorted evidence keys`` for one issuer's registration paths."""
    out: dict[str, list[str]] = {}
    for path in records:
        keys: set[str] = set()
        for event_id in _cited_event_ids(path):
            event = by_event.get(event_id)
            if event is None:
                continue
            keys.update(_evidence_keys(event))
        out[str(path["path_id"])] = sorted(keys)
    return out


def _evidence_keys(event: Mapping[str, Any]) -> list[str]:
    keys: list[str] = []
    for ref in event.get("evidence") or ():
        if not isinstance(ref, Mapping):
            continue
        manifest_id = ref.get("manifest_id")
        span_id = ref.get("span_id")
        if manifest_id and span_id:
            keys.append(f"{manifest_id}/{span_id}")
    return keys


def _accession_specific(url: Any, accession: Any) -> bool:
    """True only for an SEC Archives URL that names THIS accession.

    A generic homepage or company page is never an anchor: the whole point of the
    evidence index is that a reader can land on the exact cited document.
    """
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    if "/Archives/" not in url:
        return False
    if not isinstance(accession, str) or not accession:
        return False
    if accession in url:
        return True
    digits = accession.replace("-", "")
    return bool(digits) and digits in url


def _ledger_span_sha256(manifest: Mapping[str, Any], span_id: str) -> str | None:
    for span in manifest.get("spans") or ():
        if isinstance(span, Mapping) and str(span.get("span_id") or "") == span_id:
            digest = span.get("text_sha256")
            return str(digest) if isinstance(digest, str) and digest else None
    return None


def _manifest_filing(manifest: Mapping[str, Any]) -> dict[str, Any]:
    filing = manifest.get("filing")
    filing = filing if isinstance(filing, Mapping) else {}
    return {
        "accession": filing.get("accession"),
        "form": filing.get("form"),
        "filed_at": filing.get("filing_date"),
    }


def _event_filing(event: Mapping[str, Any]) -> dict[str, Any]:
    filing = _filing_of(event)
    return {
        "accession": filing.get("accession"),
        "form": filing.get("form"),
        "filed_at": filing.get("filing_date"),
    }


def _evidence_index(
    citations: Sequence[Mapping[str, Any]],
    *,
    by_event: Mapping[str, Mapping[str, Any]],
    by_manifest: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Retained-byte evidence joined to the source ledger (SPEC §2).

    A manifest the ledger no longer carries is written with
    ``reason="manifest_unresolved"`` and the citing event's own filing -- it is
    NEVER dropped, because a dropped citation is an unprovable predicate.  No
    ``excerpt`` key is ever written: the bundle publishes a locator and a
    digest, never retained text.
    """
    index: dict[str, dict[str, Any]] = {}
    for citation in citations:
        key = str(citation["key"])
        manifest_id = str(citation["manifest_id"])
        span_id = str(citation["span_id"])
        event_ids = sorted(citation["event_ids"])
        path_ids = sorted(citation["path_ids"])
        issuer_ids = sorted(citation["issuer_ids"])
        moments = sorted(
            _iso_z(by_event[event_id].get("point_in_time", {}).get("available_at"),
                   "event.point_in_time.available_at")
            for event_id in event_ids
            if event_id in by_event and _available_at(by_event[event_id])
        )
        manifest = by_manifest.get(manifest_id)
        digests = sorted(str(digest) for digest in citation["text_sha256"])
        entry: dict[str, Any] = {
            "manifest_id": manifest_id,
            "span_id": span_id,
            "text_sha256": digests[0] if digests else None,
            "ledger_text_sha256": None,
            "issuer_id": issuer_ids[0] if issuer_ids else None,
            "event_ids": event_ids,
            "path_ids": path_ids,
            "available_at": {"system": moments[0] if moments else None},
        }
        if manifest is None:
            first_event = by_event.get(event_ids[0]) if event_ids else None
            entry["ledger_text_sha256"] = None
            entry["filing"] = _event_filing(first_event) if first_event is not None else {
                "accession": None,
                "form": None,
                "filed_at": None,
            }
            entry["document"] = {"sequence": None, "filename": None}
            entry["anchor"] = None
            entry["reason"] = _MANIFEST_UNRESOLVED
            entry["grade"] = _UNKNOWN_GRADE
        else:
            document = manifest.get("document")
            document = document if isinstance(document, Mapping) else {}
            rights = manifest.get("rights")
            rights = rights if isinstance(rights, Mapping) else {}
            filing = _manifest_filing(manifest)
            url = document.get("canonical_url")
            if _accession_specific(url, filing.get("accession")):
                entry["anchor"] = str(url)
                entry["reason"] = None
            else:
                entry["anchor"] = None
                entry["reason"] = _ANCHOR_NOT_SPECIFIC
            entry["ledger_text_sha256"] = _ledger_span_sha256(manifest, span_id)
            entry["filing"] = filing
            entry["document"] = {
                "sequence": document.get("sequence"),
                "filename": document.get("document_name"),
            }
            grade = rights.get("redistribution_class")
            entry["grade"] = str(grade) if isinstance(grade, str) and grade else _UNKNOWN_GRADE
        index[key] = entry
    return index


def _collect_citations(
    per_issuer: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    by_event: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate every predicate citation into one row per retained-byte span."""
    grouped: dict[str, dict[str, Any]] = {}
    for issuer_id, records in per_issuer:
        for path in records:
            path_id = str(path["path_id"])
            for event_id in _cited_event_ids(path):
                event = by_event.get(event_id)
                if event is None:
                    continue
                for ref in event.get("evidence") or ():
                    if not isinstance(ref, Mapping):
                        continue
                    manifest_id = ref.get("manifest_id")
                    span_id = ref.get("span_id")
                    if not manifest_id or not span_id:
                        continue
                    key = f"{manifest_id}/{span_id}"
                    slot = grouped.setdefault(
                        key,
                        {
                            "key": key,
                            "manifest_id": str(manifest_id),
                            "span_id": str(span_id),
                            "text_sha256": set(),
                            "event_ids": set(),
                            "path_ids": set(),
                            "issuer_ids": set(),
                        },
                    )
                    if ref.get("text_sha256"):
                        slot["text_sha256"].add(str(ref["text_sha256"]))
                    slot["event_ids"].add(event_id)
                    slot["path_ids"].add(path_id)
                    slot["issuer_ids"].add(issuer_id)
    return [grouped[key] for key in sorted(grouped)]


# ---------------------------------------------------------------------------
# The bundle (R6)
# ---------------------------------------------------------------------------


def _covered_issuer_ids(projection: Mapping[str, Any]) -> list[str]:
    """The projection's covered issuers: the same denominator as ``/coverage``."""
    records = projection.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError("served projection carries no records")
    issuer_ids = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("served projection record must be an object")
        issuer_id = record.get("issuer_id")
        if not isinstance(issuer_id, str) or not issuer_id:
            raise ValueError("served projection record carries no issuer_id")
        issuer_ids.add(issuer_id)
    return sorted(issuer_ids)


def build_state_bundle(
    *,
    generation: VerifiedProjectionGeneration,
    projection: Mapping[str, Any],
    health: Mapping[str, Any],
    rule_pack: RuleApplicabilityPack,
    as_of: str,
    generated_at: str,
    projection_sha256: str,
    source_manifests: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """One published state generation: every issuer bound to the same inputs.

    Nothing is written by this function; it returns the bundle dict or raises.
    A refusal anywhere withholds the WHOLE bundle (SPEC §2).
    """
    telemetry = _require_generation(generation.telemetry)
    whole = build_capital_inputs(
        generation, projection, projection_sha256=projection_sha256
    )
    cutoff = _iso_z(as_of, "as_of")
    produced = _iso_z(generated_at, "generated_at")
    projection_generation_id = str(projection["generation_id"])
    by_event = {str(event["event_id"]): event for event in whole.events}

    issuer_ids = _covered_issuer_ids(projection)
    issuer_records: list[dict[str, Any]] = []
    issuer_index: dict[str, Any] = {}
    per_coverage: list[dict[str, Any]] = []
    citations_input: list[tuple[str, Sequence[Mapping[str, Any]]]] = []
    for issuer_id in issuer_ids:
        inputs = inputs_for_issuer(whole, issuer_id)
        state, reg = issuer_state(
            inputs,
            issuer_id=issuer_id,
            as_of=cutoff,
            generated_at=produced,
            rule_pack=rule_pack,
            projection_generation_id=projection_generation_id,
        )
        family = reg.family_state()
        coverage = coverage_for(family, rule_pack=rule_pack, deferred=reg.deferred)
        issuer_records.append(state.as_record())
        per_coverage.append(coverage)
        citations_input.append((issuer_id, family.records))
        issuer_index[issuer_id] = {
            "event_count": len(inputs.events),
            "edge_count": len(inputs.edges),
            "coverage": {REGISTRATION_FAMILY: coverage},
            "ticker_observations": _ticker_observations(inputs.events),
            "path_evidence": _path_evidence(family.records, by_event),
            "registration_receipt": reg.receipt.as_record(),
        }

    input_generations = [binding.as_record() for binding in whole.bindings]
    rule_pack_record = {
        "rule_pack_id": rule_pack.rule_pack_id,
        "rule_pack_version": rule_pack.version,
        "rule_pack_digest": rule_pack.file_sha256,
    }
    by_manifest = {
        str(row.get("manifest_id")): row
        for row in source_manifests
        if isinstance(row, Mapping) and row.get("manifest_id")
    }
    bundle: dict[str, Any] = {
        "schema": STATE_BUNDLE_SCHEMA,
        "contract_version": STATE_CONTRACT_VERSION,
        "bundle_version": STATE_BUNDLE_VERSION,
        "generation_id": stable_id(
            "state_bundle",
            {
                "input_generations": input_generations,
                "rule_pack": rule_pack_record,
                "as_of": cutoff,
            },
        ),
        "as_of": cutoff,
        "generated_at": produced,
        "projection_generation_id": projection_generation_id,
        "input_generations": input_generations,
        "rule_pack": rule_pack_record,
        "horizons": _horizons(
            events=whole.events,
            generated_at=produced,
            telemetry=telemetry,
            health=health,
        ),
        "coverage": _bundle_coverage(per_coverage, len(issuer_ids)),
        "unavailable": sorted(INHERITED_UNAVAILABLE_CAPABILITIES),
        "capabilities_proven": [],
        "issuers": issuer_records,
        "issuer_index": issuer_index,
        "evidence_index": _evidence_index(
            _collect_citations(citations_input, by_event),
            by_event=by_event,
            by_manifest=by_manifest,
        ),
        "authority": dict(AUTHORITY),
    }
    return bundle


# ---------------------------------------------------------------------------
# Reading a published bundle back through the contract classes (R11/R12)
# ---------------------------------------------------------------------------


def state_from_record(record: Mapping[str, Any]) -> CapitalState:
    """Rebuild a published issuer record through the frozen contract classes.

    The rebuilt record must equal the published one byte for byte: that is how a
    dropped capability, a widened authority or a tampered digest fails closed
    instead of being served (A06).
    """
    if not isinstance(record, Mapping):
        raise ContractViolation("state record must be an object")
    try:
        request_row = dict(record["request"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"state record is unreadable: {exc}") from exc
    request_row.pop("schema", None)
    request_row.pop("request_id", None)
    request_row["input_generations"] = tuple(
        GenerationBinding(**dict(row)) for row in request_row["input_generations"]
    )
    families: list[FamilyState] = []
    for row in record["families"]:
        provenance_row = dict(row["provenance"])
        provenance_row["support_limits"] = tuple(provenance_row.get("support_limits") or ())
        families.append(
            FamilyState(
                str(row["family"]),
                FamilyProvenance(**provenance_row),
                records=tuple(row.get("records") or ()),
                unavailable=tuple(row.get("unavailable") or ()),
            )
        )
    receipt_row = dict(record["receipt"])
    receipt_row.pop("schema", None)
    receipt_row.pop("receipt_id", None)
    state = CapitalState(
        StateRequest(**request_row),
        str(record["generated_at"]),
        tuple(families),
        CalculationReceipt(**receipt_row),
        unavailable=tuple(record["unavailable"]),
        capabilities_proven=tuple(
            CapabilityProof(**dict(row)) for row in record["capabilities_proven"]
        ),
        projection_generation_id=record["projection_generation_id"],
    )
    if state.as_record() != dict(record):
        raise ContractViolation(
            "published state record does not survive contract re-construction"
        )
    return state


def _schema_errors(validator: Any, record: Mapping[str, Any]) -> list[str]:
    errors = sorted(validator.iter_errors(dict(record)), key=lambda error: list(error.path))
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in errors[:10]
    ]


def validate_state_bundle(bundle: Mapping[str, Any]) -> None:
    """Validate the whole publication or refuse it (SPEC §2: one generation or nothing).

    Three layers, in order: this bundle's own JSON schema, the frozen
    ``capital_structure.state.v2`` schema per issuer (one compiled validator for
    the whole call), and the contract re-construction plus every cross-issuer
    binding identity that makes the bundle ONE generation.
    """
    from jsonschema import Draft202012Validator, FormatChecker

    if not isinstance(bundle, Mapping):
        raise ContractViolation("state bundle must be an object")
    bundle_schema = json.loads(STATE_BUNDLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    messages = _schema_errors(
        Draft202012Validator(bundle_schema, format_checker=FormatChecker()), bundle
    )
    if messages:
        raise ContractViolation(
            "capital-structure state bundle contract violation: " + "; ".join(messages)
        )

    state_validator = Draft202012Validator(
        load_state_schema(), format_checker=FormatChecker()
    )
    seen: set[str] = set()
    for record in bundle["issuers"]:
        messages = _schema_errors(state_validator, record)
        if messages:
            raise ContractViolation(
                "capital-structure state contract violation: " + "; ".join(messages)
            )
        state_from_record(record)
        issuer_id = str(record["request"]["issuer_id"])
        if issuer_id in seen:
            raise ContractViolation(f"state bundle carries issuer {issuer_id!r} twice")
        seen.add(issuer_id)
        request = record["request"]
        if request["input_generations"] != bundle["input_generations"]:
            raise ContractViolation(
                f"issuer {issuer_id!r} is not bound to the bundle's input generations"
            )
        if record["as_of"] != bundle["as_of"]:
            raise ContractViolation(f"issuer {issuer_id!r} is cut at another as_of")
        if record["projection_generation_id"] != bundle["projection_generation_id"]:
            raise ContractViolation(
                f"issuer {issuer_id!r} binds another served projection generation"
            )

    expected_generation_id = stable_id(
        "state_bundle",
        {
            "input_generations": bundle["input_generations"],
            "rule_pack": bundle["rule_pack"],
            "as_of": bundle["as_of"],
        },
    )
    if bundle["generation_id"] != expected_generation_id:
        raise ContractViolation("state bundle generation_id does not match its inputs")
    if list(bundle["unavailable"]) != sorted(INHERITED_UNAVAILABLE_CAPABILITIES):
        raise ContractViolation(
            "state bundle must inherit every projection-era unavailable capability"
        )
    if list(bundle["capabilities_proven"]) != []:
        raise ContractViolation("a capability proof must name the generation and test that proved it")
    if dict(bundle["authority"]) != dict(AUTHORITY):
        raise ContractViolation("state bundle authority differs from the context-only contract")
    if bundle["schema"] != STATE_BUNDLE_SCHEMA:
        raise ContractViolation(f"state bundle schema must be {STATE_BUNDLE_SCHEMA!r}")
    if bundle["contract_version"] != STATE_CONTRACT_VERSION:
        raise ContractViolation("state bundle contract_version differs from the frozen contract")
    if bundle["bundle_version"] != STATE_BUNDLE_VERSION:
        raise ContractViolation(f"state bundle version must be {STATE_BUNDLE_VERSION!r}")
    _assert_safe_keys(dict(bundle), "state_bundle")


def issuer_inputs(
    bundle: Mapping[str, Any],
    generation: VerifiedProjectionGeneration,
    issuer_id: str,
) -> CapitalInputs:
    """The reader's re-derivation: the published inputs for one issuer, proved.

    The reader never integrates from a stored copy of the rows.  It rebuilds them
    from the verified generation through the SAME selection rule the producer
    used, then requires the result to digest to the published ``input_digest``.
    A generation that moved under the bundle therefore fails closed instead of
    being served as if it were the published one.
    """
    if not isinstance(bundle, Mapping):
        raise ContractViolation("state bundle must be an object")
    bindings = tuple(
        GenerationBinding(**dict(row)) for row in bundle["input_generations"]
    )
    events_binding = next(
        (binding for binding in bindings if binding.input_family == EVENTS_FAMILY), None
    )
    telemetry = generation.telemetry if isinstance(generation.telemetry, Mapping) else {}
    if events_binding is None or str(
        telemetry.get("generation_id") or ""
    ) != str(events_binding.generation_id or ""):
        raise ContractViolation(
            "state generation does not bind the verified capital-structure generation"
        )
    record = next(
        (
            row
            for row in bundle["issuers"]
            if str((row.get("request") or {}).get("issuer_id") or "") == issuer_id
        ),
        None,
    )
    if record is None:
        raise ContractViolation("issuer not covered")
    whole = _inputs_from_generation(bindings, generation)
    inputs = inputs_for_issuer(whole, issuer_id)
    published = (record.get("receipt") or {}).get("input_digest")
    if inputs.input_digest != published:
        raise ContractViolation("state generation does not bind the published inputs")
    return inputs


# ---------------------------------------------------------------------------
# Then-known derivation (R14/R15, SPEC §5) -- historical knowledge, not facts
# ---------------------------------------------------------------------------


def then_known_state(
    current_record: Mapping[str, Any],
    inputs: CapitalInputs,
    *,
    cutoff: str,
    rule_pack: RuleApplicabilityPack | None,
    generated_at: str | None = None,
) -> CapitalState:
    """What Mastermind knew at ``cutoff``, through the SAME integrator.

    The generation did not change -- the view did -- so the bindings are reused
    verbatim and only the rows whose ``point_in_time.available_at`` had already
    arrived survive.  ``generated_at`` defaults to the published state's own so
    the derived ``state_id`` is a deterministic function of (generation, cutoff).
    The result is per request, bounded to one issuer, and never written to disk.
    """
    if not isinstance(current_record, Mapping):
        raise ContractViolation("current state record must be an object")
    moment = _parse_instant(cutoff, "cutoff")
    published_as_of = _iso_z(current_record["as_of"], "state.as_of")
    if moment > _parse_instant(published_as_of, "state.as_of"):
        raise ValueError("a then-known cutoff cannot exceed the published as_of")
    normalized = _iso_z(cutoff, "cutoff")
    events = tuple(
        event
        for event in inputs.events
        if _available_at(event)
        and _parse_instant(_available_at(event)) <= moment
    )
    bound = {str(event["event_id"]) for event in events}
    edges = tuple(
        edge
        for edge in inputs.edges
        if str(edge.get("from_event_id") or "") in bound
        and str(edge.get("to_event_id") or "") in bound
    )
    filtered = CapitalInputs(bindings=inputs.bindings, events=events, edges=edges)
    produced = generated_at or str(current_record["generated_at"])
    state, _ = issuer_state(
        filtered,
        issuer_id=str(current_record["request"]["issuer_id"]),
        as_of=normalized,
        generated_at=produced,
        rule_pack=rule_pack,
        projection_generation_id=str(current_record["projection_generation_id"]),
        view_mode="then_known",
    )
    return state


def not_yet_observed(
    current_record: Mapping[str, Any],
    derived_state: Any,
    inputs: CapitalInputs,
) -> list[dict[str, Any]]:
    """Current paths that had not happened yet at the derived cutoff.

    A path whose only evidence postdates the cutoff renders as
    ``unknown_at_date`` -- never absent, and never as a current path.  Absence of
    an observation is not a fact about the registration (U0 §4, A31).  The
    identity compared is ``lifecycle_id``: ``path_id`` embeds ``as_of``, so it
    differs between the two views by construction.
    """
    if not isinstance(current_record, Mapping):
        raise ContractViolation("current state record must be an object")
    current = next(
        (
            row
            for row in current_record["families"]
            if str(row.get("family") or "") == REGISTRATION_FAMILY
        ),
        None,
    )
    derived = None
    if isinstance(derived_state, CapitalState):
        derived = derived_state.family(REGISTRATION_FAMILY)
        derived_records = tuple(derived.records) if derived is not None else ()
    elif isinstance(derived_state, Mapping):
        derived = next(
            (
                row
                for row in derived_state.get("families") or ()
                if str(row.get("family") or "") == REGISTRATION_FAMILY
            ),
            None,
        )
        derived_records = tuple((derived or {}).get("records") or ())
    else:
        raise ContractViolation("derived state must be a CapitalState or its record")
    observed = {
        str(path["lifecycle_id"])
        for path in derived_records
        if isinstance(path, Mapping) and path.get("lifecycle_id")
    }
    by_event = {str(event["event_id"]): event for event in inputs.events}
    rows: list[dict[str, Any]] = []
    for path in (current or {}).get("records") or ():
        if not isinstance(path, Mapping):
            continue
        lifecycle_id = str(path.get("lifecycle_id") or "")
        if not lifecycle_id or lifecycle_id in observed:
            continue
        moments = sorted(
            _iso_z(
                by_event[event_id].get("point_in_time", {}).get("available_at"),
                "event.point_in_time.available_at",
            )
            for event_id in sorted(_lifecycle_event_ids(path))
            if event_id in by_event and _available_at(by_event[event_id])
        )
        rows.append(
            {
                "path_id": str(path["path_id"]),
                "lifecycle_id": lifecycle_id,
                "first_available_at": moments[0] if moments else None,
                "status": _UNKNOWN_AT_DATE,
            }
        )
    rows.sort(key=lambda row: (row["first_available_at"] or "", row["path_id"]))
    return rows


__all__ = [
    "STATE_BUNDLE_IMPLEMENTATION_DIGEST",
    "STATE_BUNDLE_SCHEMA",
    "STATE_BUNDLE_SCHEMA_FILE",
    "STATE_BUNDLE_SCHEMA_PATH",
    "STATE_BUNDLE_VERSION",
    "build_capital_inputs",
    "build_state_bundle",
    "coverage_for",
    "inputs_for_issuer",
    "issuer_inputs",
    "issuer_state",
    "not_yet_observed",
    "state_from_record",
    "then_known_state",
    "validate_state_bundle",
]
