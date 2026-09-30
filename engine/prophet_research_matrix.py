"""Point-in-time research matrix spine for Prophet North-Star RQ1.

This module is a read-only research projection over existing canonical owners.  It
never writes B1, Radar, Evaluation/QLedger, candidate, Availability, plan, or
publication state.  The first slice deliberately solves the temporal join and
provenance problem before any model or outcome label is allowed to exist.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from engine.entry_radar.entry_events import EntryEvent
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
    validate_strategy_definition,
)
from engine.us_candidate_episode import (
    ACTIVE_STATE,
    CandidateEpisodeStoreSnapshot,
    load_candidate_episode_store_snapshot,
    project_events,
    validate_events,
)
from lib.nyse_calendar import expected_last_session

MATRIX_SCHEMA = "prophet.research_matrix/v1"
ROW_SCHEMA = "prophet.research_matrix_row/v1"
CONTROL_SCHEMA = "prophet.research_control_observation/v1"
DEFINITION = "prophet-north-star-rq1-pit-matrix-2026-09-23"
POPULATION_SCOPE = "ACTIVE_CANONICAL_B1_EPISODES_AS_OF_DECISION"

_AUTHORITY = {
    "can_rank": False,
    "can_gate_candidate_admission": False,
    "can_compute_b4_availability": False,
    "can_originate_plan": False,
    "can_change_entry_open": False,
    "can_size": False,
    "can_publish_trade_instruction": False,
    "can_execute": False,
    "can_trade": False,
    "can_promote_model": False,
}


class ResearchMatrixContractError(ValueError):
    """Raised when a PIT research projection would weaken owner truth."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ResearchMatrixContractError(f"research matrix is not canonical JSON: {exc}") from exc


def _timestamp(value: object, *, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ResearchMatrixContractError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ResearchMatrixContractError(f"{field} is not RFC3339: {value!r}") from exc
    parsed = parsed.astimezone(timezone.utc)
    normalized = parsed.isoformat(timespec="microseconds").replace("+00:00", "Z").replace(".000000Z", "Z")
    return normalized, parsed


def _sha_receipt(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ResearchMatrixContractError(f"{field} must be a sha256: provenance receipt")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ResearchMatrixContractError(f"{field} must be a sha256: provenance receipt") from exc
    return value


def _matrix_receipt(material: object) -> str:
    return "sha256:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _normalize_control(
    raw: Mapping[str, object] | None,
    *,
    episode_id: str,
    decision_at: datetime,
) -> dict[str, object]:
    """Validate one owner-supplied incumbent-control observation.

    RQ1 does not guess the V3/current-control score from B1.  A control may be
    carried only when its own owner supplies an exact clock + receipt.  Absence is
    typed as NOT_SUPPLIED rather than converted to zero/false.
    """
    if raw is None:
        return {
            "status": "NOT_SUPPLIED",
            "schema": None,
            "control_id": None,
            "known_at": None,
            "source_system": None,
            "source_receipt": None,
            "payload": None,
        }
    if not isinstance(raw, Mapping):
        raise ResearchMatrixContractError("incumbent control observation must be an object")
    required = {
        "schema", "episode_id", "control_id", "known_at",
        "source_system", "source_receipt", "payload",
    }
    if set(raw) != required:
        raise ResearchMatrixContractError("incumbent control observation fields are closed")
    if raw.get("schema") != CONTROL_SCHEMA:
        raise ResearchMatrixContractError("incumbent control schema is unsupported")
    if raw.get("episode_id") != episode_id:
        raise ResearchMatrixContractError("incumbent control episode_id does not match row")
    control_id = raw.get("control_id")
    source_system = raw.get("source_system")
    if not isinstance(control_id, str) or not control_id:
        raise ResearchMatrixContractError("incumbent control requires control_id")
    if not isinstance(source_system, str) or not source_system:
        raise ResearchMatrixContractError("incumbent control requires source_system")
    known_text, known_at = _timestamp(raw.get("known_at"), field="incumbent_control.known_at")
    if known_at > decision_at:
        raise ResearchMatrixContractError("incumbent control is future-known at decision_at")
    receipt = _sha_receipt(raw.get("source_receipt"), field="incumbent_control.source_receipt")
    # Canonicalisation is a strict JSON/finite-value check; the payload remains
    # owner-native and opaque to this adapter.
    payload = raw.get("payload")
    _canonical_json(payload)
    return {
        "status": "OBSERVED",
        "schema": CONTROL_SCHEMA,
        "control_id": control_id,
        "known_at": known_text,
        "source_system": source_system,
        "source_receipt": receipt,
        "payload": payload,
    }


def _expert_projection(
    *,
    expert_event_id: str,
    attachment: Mapping[str, object],
    radar_event: EntryEvent | None,
    decision_at: datetime,
) -> dict[str, object]:
    relationship_known_text, relationship_known = _timestamp(
        attachment.get("known_at"), field="expert_attachment.known_at"
    )
    relationship_recorded_text, relationship_recorded = _timestamp(
        attachment.get("recorded_at"), field="expert_attachment.recorded_at"
    )
    if relationship_known > decision_at or relationship_recorded > decision_at:
        raise ResearchMatrixContractError("future B1 expert attachment entered as-of projection")
    base: dict[str, object] = {
        "expert_event_id": expert_event_id,
        "relationship_source_system": attachment.get("source_system"),
        "relationship_source_schema": attachment.get("source_schema"),
        "relationship_source_receipt": attachment.get("source_receipt"),
        "relationship_known_at": relationship_known_text,
        "relationship_recorded_at": relationship_recorded_text,
        "resolution_status": "OWNER_EVENT_NOT_SUPPLIED",
        "producer": None,
        "detector_id": None,
        "family": None,
        "subtype": None,
        "stage": None,
        "quality": None,
        "signal_ts": None,
        "signal_known_ts": None,
        "bar_state": None,
        "final": None,
        "finality_basis": None,
        "family_era": None,
        "context": None,
        "authority": None,
    }
    if radar_event is None:
        return base
    payload = radar_event.to_dict()
    if payload.get("event_id") != expert_event_id:
        raise ResearchMatrixContractError("Radar event address does not match B1 expert attachment")
    signal_known = payload.get("signal_known_ts")
    if signal_known is not None:
        signal_known_text, signal_known_at = _timestamp(signal_known, field="radar_event.signal_known_ts")
        if signal_known_at > decision_at:
            # A resolved owner event whose own known clock lies in the future is
            # not merely missing; it contradicts the PIT join and must fail closed.
            raise ResearchMatrixContractError("resolved Radar event is future-known at decision_at")
    else:
        signal_known_text = None
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or any(bool(value) for value in authority.values()):
        raise ResearchMatrixContractError("Radar research event must retain all-false authority")
    base.update({
        "resolution_status": "RESOLVED" if signal_known_text is not None else "RESOLVED_KNOWN_CLOCK_ABSENT",
        "producer": payload.get("producer"),
        "detector_id": payload.get("detector_id"),
        "family": payload.get("family"),
        "subtype": payload.get("subtype"),
        "stage": payload.get("stage"),
        "quality": payload.get("quality"),
        "signal_ts": payload.get("signal_ts"),
        "signal_known_ts": signal_known_text,
        "bar_state": payload.get("bar_state"),
        "final": payload.get("final"),
        "finality_basis": payload.get("finality_basis"),
        "family_era": payload.get("family_era"),
        "context": payload.get("context"),
        "authority": dict(authority),
    })
    return base


def build_pit_research_matrix(
    *,
    events: Sequence[Mapping[str, object]],
    generation_id: str,
    decision_at: str,
    radar_events: Mapping[str, EntryEvent] | None = None,
    incumbent_controls: Mapping[str, Mapping[str, object]] | None = None,
    strategy_definition: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build one authority-false, as-of research matrix from canonical B1 events.

    Only events materially recorded by ``decision_at`` are replayed.  Later B1
    corrections/retractions therefore cannot leak backward.  Expert semantics are
    resolved only by exact immutable Entry Radar event_id; missing owner bytes stay
    explicit missingness rather than a negative feature.
    """
    if not isinstance(generation_id, str) or not generation_id:
        raise ResearchMatrixContractError("generation_id must be a non-empty string")
    decision_text, decision_dt = _timestamp(decision_at, field="decision_at")
    definition = dict(strategy_definition or build_early_leadership_sector_rotation_definition())
    validate_strategy_definition(definition)
    strategy_definition_id = str(definition["strategy_definition_id"])

    validated = validate_events(events)
    asof_events: list[dict[str, object]] = []
    for event in validated:
        _, recorded = _timestamp(event.get("recorded_at"), field="event.recorded_at")
        if recorded <= decision_dt:
            asof_events.append(event)
    projected = project_events(asof_events)
    eligible = [
        row for row in projected
        if row.get("episode_state") == ACTIVE_STATE and row.get("superseded_by") is None
    ]
    eligible.sort(key=lambda row: str(row["episode_id"]))
    population_ids = [str(row["episode_id"]) for row in eligible]
    population_receipt = _matrix_receipt({
        "scope": POPULATION_SCOPE,
        "decision_at": decision_text,
        "generation_id": generation_id,
        "episode_ids": population_ids,
    })

    attachments: dict[tuple[str, str], Mapping[str, object]] = {}
    for event in asof_events:
        if event.get("event_type") != "EXPERT_EVENT_ATTACHED":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        expert_id = payload.get("expert_event_id")
        if isinstance(expert_id, str) and expert_id:
            attachments[(str(event["episode_id"]), expert_id)] = event

    radar_events = radar_events or {}
    incumbent_controls = incumbent_controls or {}
    rows: list[dict[str, object]] = []
    for episode in eligible:
        episode_id = str(episode["episode_id"])
        experts: list[dict[str, object]] = []
        for expert_id in sorted(str(value) for value in episode.get("expert_events", [])):
            attachment = attachments.get((episode_id, expert_id))
            if attachment is None:
                raise ResearchMatrixContractError("projected expert event lacks effective B1 attachment")
            experts.append(_expert_projection(
                expert_event_id=expert_id,
                attachment=attachment,
                radar_event=radar_events.get(expert_id),
                decision_at=decision_dt,
            ))
        control = _normalize_control(
            incumbent_controls.get(episode_id),
            episode_id=episode_id,
            decision_at=decision_dt,
        )
        missingness: list[str] = []
        if control["status"] != "OBSERVED":
            missingness.append("INCUMBENT_CONTROL_NOT_SUPPLIED")
        if any(expert["resolution_status"] == "OWNER_EVENT_NOT_SUPPLIED" for expert in experts):
            missingness.append("RADAR_OWNER_EVENT_NOT_SUPPLIED")
        if any(expert["resolution_status"] == "RESOLVED_KNOWN_CLOCK_ABSENT" for expert in experts):
            missingness.append("RADAR_SOURCE_KNOWN_CLOCK_ABSENT")
        anchor = episode.get("structural_anchor")
        anchor_basis = anchor.get("basis") if isinstance(anchor, Mapping) else None
        anchor_receipt = anchor.get("source_receipt") if isinstance(anchor, Mapping) else None
        rows.append({
            "schema": ROW_SCHEMA,
            "candidate_episode_id": episode_id,
            "candidate_generation_id": generation_id,
            "security_id": episode.get("security_id"),
            "identity_epoch": episode.get("identity_epoch"),
            "strategy_definition_id": strategy_definition_id,
            "decision_at": decision_text,
            "completed_session": expected_last_session(decision_dt).isoformat(),
            "population_scope": POPULATION_SCOPE,
            "eligible_population_n": len(eligible),
            "eligible_population_receipt": population_receipt,
            "episode_opened_at": episode.get("opened_at"),
            "episode_opened_session": episode.get("opened_session"),
            "episode_definition_era": episode.get("definition_era"),
            "episode_correction_state": episode.get("correction_state"),
            "intake_classes": list(episode.get("intake_classes", [])),
            "structural_anchor_basis": anchor_basis,
            "structural_anchor_source_receipt": anchor_receipt,
            "incumbent_control": control,
            "expert_observations": experts,
            "missingness": sorted(set(missingness)),
            "rights_coverage_state": "NOT_BOUND_RQ1_SPINE",
            "basis_version": anchor_basis,
            "b4_availability_state": "NOT_BOUND_RQ1_SPINE",
            "authority": dict(_AUTHORITY),
        })

    material = {
        "schema": MATRIX_SCHEMA,
        "definition": DEFINITION,
        "decision_at": decision_text,
        "completed_session": expected_last_session(decision_dt).isoformat(),
        "candidate_generation_id": generation_id,
        "strategy_definition_id": strategy_definition_id,
        "population_scope": POPULATION_SCOPE,
        "eligible_population_n": len(eligible),
        "eligible_population_receipt": population_receipt,
        "rows": rows,
        "source_law": {
            "candidate_owner": "prophet.candidate_episode/v1",
            "expert_owner": "mastermind.entry_event.v1",
            "incumbent_control": "OWNER_SUPPLIED_ONLY",
            "asof_boundary": "event.recorded_at <= decision_at",
            "later_corrections_may_leak_backward": False,
            "unknown_becomes_zero": False,
            "creates_event_store": False,
            "creates_outcome_store": False,
        },
        "authority": dict(_AUTHORITY),
    }
    material["matrix_receipt"] = _matrix_receipt(material)
    return material


def build_pit_research_matrix_from_store(
    candidate_store_root: Path,
    *,
    decision_at: str,
    radar_events: Mapping[str, EntryEvent] | None = None,
    incumbent_controls: Mapping[str, Mapping[str, object]] | None = None,
    strategy_definition: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Load one atomic B1 HEAD snapshot, then build the read-only RQ1 matrix."""
    snapshot: CandidateEpisodeStoreSnapshot = load_candidate_episode_store_snapshot(candidate_store_root)
    return build_pit_research_matrix(
        events=snapshot.generation.events,
        generation_id=snapshot.generation_id,
        decision_at=decision_at,
        radar_events=radar_events,
        incumbent_controls=incumbent_controls,
        strategy_definition=strategy_definition,
    )
