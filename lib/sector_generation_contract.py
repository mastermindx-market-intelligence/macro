"""Sector semantics over captured generation members; no publication or auth owner.

The generic publisher verifies byte identity. This domain contract binds those bytes
to the existing Sector projection and freshness policy. Both reader and producer
preflight call it; neither invents a second calendar, hash meaning or wire format.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any

from engine.sector_native_view import (
    SectorViewInputs, SectorViewReceipt, _receipt, project_sector_view,
)
from lib.sector_generation_wire import encode_sector_generation
from scripts.check_sector_intelligence_freshness import (
    check_action_board, check_basket_dependency, evaluate_session_age,
)

SECTOR_GENERATION_DOMAIN = "sector"
SECTOR_INPUT_SCHEMA = "sector.view_inputs.v1"
SECTOR_GENERATION_MEMBERS = (
    "sectordata/sector_central.json",
    "sectordata/sector_cycles.json",
    "basketdata/baskets.json",
    "basketdata/si_handoff.json",
    "basketdata/action_board.json",
)
_IDENTITY_FIELDS = frozenset((
    "schema", "source_session", "input_version", "baseline_session",
    "source_qualification",
))


class SectorGenerationContractError(ValueError):
    """A closed source-contract failure; never embed private data or paths."""


def _refuse_constant(value: str) -> None:
    raise SectorGenerationContractError("invalid_member_json")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise SectorGenerationContractError("invalid_member_json")
    return parsed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SectorGenerationContractError("duplicate_member_key")
        result[key] = value
    return result


def _decode_member(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise SectorGenerationContractError("invalid_member_bytes")
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_float=_finite_float, parse_constant=_refuse_constant,
        )
    except (UnicodeError, ValueError, OverflowError, RecursionError):
        raise SectorGenerationContractError("invalid_member_json") from None
    if not isinstance(document, dict):
        raise SectorGenerationContractError("invalid_member_object")
    return document


def _capture_view(
    *, member_bytes: Mapping[str, bytes], input_identity: Mapping[str, Any],
    generation_id: str, published_at: str, now: datetime,
) -> tuple[SectorViewInputs, SectorViewReceipt]:
    """Capture local values and apply existing semantic owners to one byte set."""
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        raise SectorGenerationContractError("aware_evaluation_clock_required")
    if (not isinstance(member_bytes, Mapping)
            or set(member_bytes) != set(SECTOR_GENERATION_MEMBERS)):
        raise SectorGenerationContractError("invalid_member_set")
    if not isinstance(input_identity, Mapping):
        raise SectorGenerationContractError("missing_sector_identity")
    identity = input_identity.get("sector_view")
    if (not isinstance(identity, Mapping)
            or not _IDENTITY_FIELDS.issubset(identity)
            or identity.get("schema") != SECTOR_INPUT_SCHEMA):
        raise SectorGenerationContractError("missing_sector_identity")
    baseline_value = identity["baseline_session"]
    if baseline_value is not None and (
            not isinstance(baseline_value, str) or not baseline_value):
        raise SectorGenerationContractError("invalid_baseline_session")
    receipt = SectorViewReceipt(
        generation_id=generation_id, source_session=identity["source_session"],
        published_at=published_at, qualification=identity["source_qualification"],
        input_version=identity["input_version"],
        baseline_session=identity["baseline_session"],
    )
    # Use the existing projection owner's receipt validation, including the
    # narrower public token grammar. A publisher-valid colon/@ ID is not relabeled.
    _, baseline = _receipt(receipt)
    # The incumbent publisher emits an aware UTC datetime.isoformat() string,
    # at most 32 characters. Bound this fact for retained-generation wire admission.
    if not isinstance(published_at, str) or len(published_at) > 32:
        raise SectorGenerationContractError("invalid_publication_clock")
    publication = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    if publication > now:
        raise SectorGenerationContractError("future_publication_clock")
    # Required metadata values are not inferred from whichever artifact is oldest.
    core_day = date.fromisoformat(receipt.source_session)
    baseline_day = date.fromisoformat(baseline)
    try:
        days = (core_day,) if baseline_day == core_day else (core_day, baseline_day)
        ages = [evaluate_session_age(day, now=now) for day in days]
        publication_ages = [evaluate_session_age(day, now=publication) for day in days]
    except Exception:
        raise SectorGenerationContractError("calendar_unavailable") from None
    if any(not age["is_session"] or age["future"] for age in ages):
        raise SectorGenerationContractError("invalid_source_session")
    if any(age["future"] for age in publication_ages):
        raise SectorGenerationContractError("source_after_publication")
    # Time passing cannot turn developing-at-publication bytes into a final close.
    # Preserve that qualification floor even when the read happens after settlement.
    all_ages = ages + publication_ages
    if receipt.qualification == "stale" or any(age["age_breach"] for age in all_ages):
        qualification = "stale"
    elif receipt.qualification == "degraded" or any(age["developing"] for age in all_ages):
        qualification = "degraded"
    else:
        qualification = "accepted"
    receipt = replace(receipt, qualification=qualification)
    documents = [_decode_member(member_bytes[name]) for name in SECTOR_GENERATION_MEMBERS]
    inputs = SectorViewInputs(*documents)
    if check_action_board(inputs.action_board):
        raise SectorGenerationContractError("invalid_action_board")
    if check_basket_dependency(inputs.action_board, member_bytes[SECTOR_GENERATION_MEMBERS[2]]):
        raise SectorGenerationContractError("action_board_dependency_mismatch")
    return inputs, receipt


def project_sector_bundle(
    *, member_bytes: Mapping[str, bytes], input_identity: Mapping[str, Any],
    generation_id: str, published_at: str, now: datetime,
    audience: str, preview_rows: int = 3,
) -> dict[str, Any]:
    """Project one captured bundle for an already-authorized audience.

    The projector checks core/baseline alignment and emits the allowlisted core,
    reconstructed history, Brief and board under one authorized content hash.
    """
    inputs, receipt = _capture_view(
        member_bytes=member_bytes, input_identity=input_identity,
        generation_id=generation_id, published_at=published_at, now=now,
    )
    return project_sector_view(inputs, receipt, audience=audience, preview_rows=preview_rows)


def population_from_bundle(
    *, member_bytes: Mapping[str, bytes], input_identity: Mapping[str, Any],
    generation_id: str, published_at: str, now: datetime,
):
    """Project the FULL group-membership population of one captured bundle.

    Qualification is the incumbent one: the same ``_capture_view`` (calendar,
    freshness floor, basket dependency, action-board binding) that gates the
    native view also gates the population, so a bundle the view refuses is never
    served as a population. Returns ``(receipt, population)``; no value is
    invented and nothing is truncated.
    """
    from lib.sector_population import PopulationError, build_population

    inputs, receipt = _capture_view(
        member_bytes=member_bytes, input_identity=input_identity,
        generation_id=generation_id, published_at=published_at, now=now,
    )
    try:
        population = build_population(
            baskets=inputs.baskets, handoff=inputs.handoff,
            action_board=inputs.action_board, central=inputs.central)
    except PopulationError as exc:
        raise SectorGenerationContractError(str(exc)) from None
    return receipt, population


def preflight_sector_bundle(
    *, member_bytes: Mapping[str, bytes], input_identity: Mapping[str, Any],
    generation_id: str, published_at: str, now: datetime, preview_rows: int = 3,
) -> dict[str, dict[str, Any]]:
    """Qualify BOTH actual API representations before a producer may select bytes.

    This is read-only qualification, not publication. It uses one parsed byte set
    and the exact HTTP encoder. It additionally reserves the existing maximum token
    and timestamp widths, so content reuse with an older publication receipt and
    later accepted→degraded/stale aging cannot strand a selected oversized response.
    The reserved values are size probes only and are never returned as source facts.
    """
    inputs, receipt = _capture_view(
        member_bytes=member_bytes, input_identity=input_identity,
        generation_id=generation_id, published_at=published_at, now=now,
    )
    results = {}
    for audience in ("preview", "entitled"):
        projection = project_sector_view(
            inputs, receipt, audience=audience, preview_rows=preview_rows)
        facts = projection["receipt"]
        encode_sector_generation(
            audience=audience, source_session=facts["source_session"],
            published_at=facts["published_at"], qualification=facts["qualification"],
            projection=projection,
        )
        reserved = deepcopy(projection)
        reserved["receipt"].update({
            "generation_id": "g" * 128,
            "input_version": "v" * 128,
            "published_at": "2000-01-01T00:00:00.000000+00:00",
            "qualification": "degraded",
        })
        encode_sector_generation(
            audience=audience, source_session=facts["source_session"],
            published_at=reserved["receipt"]["published_at"], qualification="degraded",
            projection=reserved,
        )
        results[audience] = projection
    return results


def prepare_sector_generation_request(
    *, sources: Mapping[str, Path], input_identity: Mapping[str, Any],
    generation_id: str, source_revision: str, lane: str,
    computed_at: str | None = None, preview_rows: int = 3,
):
    """Assemble the existing fixed-five request and final bundle admission.

    The existing publisher supplies verified captured bytes, captured input identity
    and its actual target publication receipt and admission clock to the callback. New selection
    requires accepted qualification; retained generations still age truthfully when
    read. No preparation-time clock can authorize a later or backdated publication.
    """
    from scripts.vps_live_orchestrator import GenerationArtifact, GenerationRequest

    if set(sources) != set(SECTOR_GENERATION_MEMBERS):
        raise SectorGenerationContractError("invalid_member_set")
    identity = deepcopy(dict(input_identity))
    if computed_at is not None:
        try:
            if not isinstance(computed_at, str) or len(computed_at) > 32:
                raise ValueError
            computed = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
            if computed.tzinfo is None or computed.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise SectorGenerationContractError("invalid_computation_clock") from None

    def validate_member(captured_path: Path) -> str | None:
        try:
            _decode_member(captured_path.read_bytes())
        except Exception as exc:
            return "sector_member_rejected:" + type(exc).__name__
        return None

    def validate_bundle(context) -> str | None:
        if (context.domain != SECTOR_GENERATION_DOMAIN
                or context.generation_id != generation_id
                or context.input_identity != identity):
            return "sector_identity_changed_during_admission"
        try:
            if computed_at is not None:
                # The incumbent publisher supplies the actual target receipt,
                # including an original receipt when reusing retained bytes.
                publication = datetime.fromisoformat(context.published_at.replace("Z", "+00:00"))
                if context.computed_at != computed_at or computed > publication:
                    return "sector_computation_after_publication_or_changed"
            views = preflight_sector_bundle(
                member_bytes=context.members, input_identity=context.input_identity,
                generation_id=context.generation_id,
                published_at=context.published_at,
                now=context.admission_time, preview_rows=preview_rows,
            )
            if any(view["receipt"]["qualification"] != "accepted"
                   for view in views.values()):
                return "sector_source_not_accepted"
        except Exception as exc:
            return "sector_semantic_rejected:" + type(exc).__name__
        return None

    return GenerationRequest(
        generation_id=generation_id, domain=SECTOR_GENERATION_DOMAIN, lane=lane,
        source_revision=source_revision, computed_at=computed_at,
        input_identity=deepcopy(identity), bundle_validator=validate_bundle,
        artifacts=tuple(GenerationArtifact(
            name=name, source=Path(sources[name]), validator=validate_member,
        ) for name in SECTOR_GENERATION_MEMBERS),
    )
