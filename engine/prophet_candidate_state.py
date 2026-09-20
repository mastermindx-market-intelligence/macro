"""Pure, non-authoritative B3 candidate-state projection over canonical B1.

This module is a replaceable read model. It does not own B1 identity/lifecycle,
B4 Availability, ranking, plans, origination, sizing, execution, or trades.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re

ROW_SCHEMA = "prophet.candidate_state/v1"
PROJECTION_SCHEMA = "prophet.candidate_state_projection/v1"
DEFINITION_ERA = "candidate-state-v1-2026-09-18"

_GENERATION_RE = re.compile(r"^peg:[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_RFC3339_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_SOURCE_EPISODE_STATES = frozenset(
    {"ACTIVE", "RESOLVED", "INVALIDATED", "EXPIRED", "RETRACTED"}
)
_LIFECYCLE_STATES = frozenset(
    {
        "ACTIVE",
        "CLOSED",
        "INVALIDATED",
        "RETRACTED",
        "SUPERSEDED",
        "UNAVAILABLE_DATA",
    }
)
_EMERGENCE_STATES = frozenset(
    {"FORMING", "ARMED", "TRIGGERED", "FAILED_TO_TRIGGER", "DECAYED", "UNESTIMABLE"}
)
_MATURITY_STATES = frozenset(
    {
        "PRE_CONFIRMATION",
        "EARLY_CONFIRMATION",
        "CONFIRMED",
        "MATURE",
        "EXHAUSTION_RISK",
        "UNESTIMABLE",
    }
)
_STAGE_MAP = {
    "EARLY": "PRE_CONFIRMATION",
    "CONFIRMING": "EARLY_CONFIRMATION",
    "CONFIRMED": "CONFIRMED",
}
_AUTHORITY = {
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_originate_signal": False,
    "can_change_entry_open": False,
    "can_change_execution": False,
}


class CandidateStateContractError(ValueError):
    """Raised when an input would weaken the closed B3 projection contract."""


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
        raise CandidateStateContractError(
            f"value is not canonical JSON: {exc}"
        ) from exc


def _text(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 32 for character in value)
    ):
        raise CandidateStateContractError(
            f"{field} must be non-empty control-free text"
        )
    return value


def _market_session(value: object) -> str:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise CandidateStateContractError("market_session must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CandidateStateContractError(
            "market_session must be a real calendar date"
        ) from exc
    if parsed.isoformat() != value:
        raise CandidateStateContractError("market_session is not canonical")
    return value


def _generated_at(value: object) -> str:
    if not isinstance(value, str) or not _RFC3339_UTC_RE.fullmatch(value):
        raise CandidateStateContractError("generated_at must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CandidateStateContractError(
            "generated_at must be a real UTC RFC3339 instant"
        ) from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise CandidateStateContractError("generated_at must be UTC RFC3339")
    parsed = parsed.astimezone(timezone.utc)
    return (
        parsed.isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
        .replace(".000000Z", "Z")
    )


def _expected_lifecycle_state(
    source_state: object, successor: object
) -> str:
    if successor is not None:
        return "SUPERSEDED"
    if source_state == "ACTIVE":
        return "ACTIVE"
    if source_state == "INVALIDATED":
        return "INVALIDATED"
    if source_state == "RETRACTED":
        return "RETRACTED"
    return "CLOSED"


def _validate_lifecycle_projection(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "state",
        "source_state",
        "terminal_reason",
        "superseded_by",
    }:
        raise CandidateStateContractError("lifecycle fields are not closed")
    source_state = value.get("source_state")
    if source_state not in _SOURCE_EPISODE_STATES:
        raise CandidateStateContractError("lifecycle source state invalid")
    terminal_reason = value.get("terminal_reason")
    if source_state == "ACTIVE":
        if terminal_reason is not None:
            raise CandidateStateContractError(
                "ACTIVE lifecycle cannot carry terminal_reason"
            )
    else:
        _text(terminal_reason, "lifecycle.terminal_reason")
    successor = value.get("superseded_by")
    if successor is not None:
        _text(successor, "lifecycle.superseded_by")
    expected_state = _expected_lifecycle_state(source_state, successor)
    if value.get("state") != expected_state:
        raise CandidateStateContractError(
            "lifecycle state is inconsistent with B1 source state"
        )


def _validate_emergence_projection(value: object) -> None:
    if not isinstance(value, Mapping):
        raise CandidateStateContractError("emergence state invalid")
    normalized = _emergence(value)
    if dict(value) != normalized:
        raise CandidateStateContractError("emergence state is not canonical")


def _validate_maturity_projection(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "state",
        "reason",
        "source_token",
    }:
        raise CandidateStateContractError("maturity fields are not closed")
    expected = _maturity(value.get("source_token"))
    if dict(value) != expected:
        raise CandidateStateContractError(
            "maturity state is inconsistent with source token"
        )


def _lifecycle(episode: Mapping[str, object]) -> dict[str, object]:
    source_state = episode.get("episode_state")
    if source_state not in _SOURCE_EPISODE_STATES:
        raise CandidateStateContractError("B1 episode_state is invalid")

    terminal_reason = episode.get("terminal_reason")
    if source_state == "ACTIVE":
        if terminal_reason is not None:
            raise CandidateStateContractError(
                "ACTIVE B1 episode has terminal_reason"
            )
    elif not isinstance(terminal_reason, str) or not terminal_reason:
        raise CandidateStateContractError(
            "terminal B1 episode requires terminal_reason"
        )

    successor = episode.get("superseded_by")
    if successor is not None:
        successor = _text(successor, "superseded_by")
        state = "SUPERSEDED"
    elif source_state == "ACTIVE":
        state = "ACTIVE"
    elif source_state == "INVALIDATED":
        state = "INVALIDATED"
    elif source_state == "RETRACTED":
        state = "RETRACTED"
    else:
        state = "CLOSED"

    return {
        "state": state,
        "source_state": source_state,
        "terminal_reason": terminal_reason,
        "superseded_by": successor,
    }


def _emergence(value: object) -> dict[str, object]:
    if value is None:
        return {
            "state": "UNESTIMABLE",
            "reason": "SOURCE_NOT_SUPPLIED",
            "source_system": None,
            "source_token": None,
            "source_ref": None,
        }
    if not isinstance(value, Mapping):
        raise CandidateStateContractError(
            "emergence evidence must be an object"
        )

    allowed = {
        "state",
        "reason",
        "source_system",
        "source_token",
        "source_ref",
    }
    if set(value) - allowed:
        raise CandidateStateContractError(
            "emergence evidence has unknown fields"
        )

    state = value.get("state")
    if state not in _EMERGENCE_STATES:
        raise CandidateStateContractError("emergence state is invalid")

    out = {
        "state": state,
        "reason": value.get("reason"),
        "source_system": value.get("source_system"),
        "source_token": value.get("source_token"),
        "source_ref": value.get("source_ref"),
    }
    for key in ("source_system", "source_token", "source_ref"):
        if out[key] is not None:
            out[key] = _text(out[key], f"emergence.{key}")

    if state != "UNESTIMABLE" and any(
        out[key] is None
        for key in ("source_system", "source_token", "source_ref")
    ):
        raise CandidateStateContractError(
            "estimable emergence requires source provenance"
        )

    if out["reason"] is not None:
        out["reason"] = _text(out["reason"], "emergence.reason")
    return out


def _maturity(source_stage: object) -> dict[str, object]:
    if source_stage is None:
        return {
            "state": "UNESTIMABLE",
            "reason": "SOURCE_NOT_SUPPLIED",
            "source_token": None,
        }

    token = _text(source_stage, "maturity source token")
    state = _STAGE_MAP.get(token.upper(), "UNESTIMABLE")
    return {
        "state": state,
        "reason": (
            None
            if state != "UNESTIMABLE"
            else "UNMAPPED_SOURCE_TOKEN"
        ),
        "source_token": token,
    }


def _row(
    episode: Mapping[str, object],
    *,
    generation_id: str,
    emergence: object,
    maturity_stage: object,
) -> dict[str, object]:
    if episode.get("schema") != "prophet.candidate_episode/v1":
        raise CandidateStateContractError("B1 episode schema mismatch")

    episode_id = _text(episode.get("episode_id"), "episode_id")
    security_id = _text(episode.get("security_id"), "security_id")
    company_id = _text(episode.get("company_id"), "company_id")
    identity_epoch = _text(episode.get("identity_epoch"), "identity_epoch")

    return {
        "schema": ROW_SCHEMA,
        "definition_era": DEFINITION_ERA,
        "episode_id": episode_id,
        "security_id": security_id,
        "company_id": company_id,
        "identity_epoch": identity_epoch,
        "candidate_generation_id": generation_id,
        "episode_lifecycle": _lifecycle(episode),
        "emergence_state": _emergence(emergence),
        "maturity_state": _maturity(maturity_stage),
        "entry_availability": {
            "state": "UNAVAILABLE_DATA",
            "reason": "B4_NOT_AVAILABLE",
        },
        "authority": dict(_AUTHORITY),
    }


def project_candidate_states(
    snapshot: object,
    *,
    market_session: str,
    generated_at: str,
    emergence_by_episode: Mapping[str, object] | None = None,
    maturity_stage_by_episode: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Project orthogonal B3 state without inferring B4 or trading authority."""

    generation_id = getattr(snapshot, "generation_id", None)
    if (
        not isinstance(generation_id, str)
        or not _GENERATION_RE.fullmatch(generation_id)
    ):
        raise CandidateStateContractError(
            "snapshot generation_id is invalid"
        )
    market_session = _market_session(market_session)
    generated_at = _generated_at(generated_at)

    generation = getattr(snapshot, "generation", None)
    episodes = getattr(generation, "episodes", None)
    if not isinstance(episodes, tuple):
        raise CandidateStateContractError(
            "snapshot must expose validated tuple episodes"
        )

    emergence_by_episode = emergence_by_episode or {}
    maturity_stage_by_episode = maturity_stage_by_episode or {}

    episode_ids = {
        _text(episode.get("episode_id"), "episode_id")
        for episode in episodes
        if isinstance(episode, Mapping)
    }
    if (
        set(emergence_by_episode) - episode_ids
        or set(maturity_stage_by_episode) - episode_ids
    ):
        raise CandidateStateContractError(
            "state input references unknown episode"
        )

    rows: list[dict[str, object]] = []
    for episode in episodes:
        if not isinstance(episode, Mapping):
            raise CandidateStateContractError(
                "B1 episode row must be an object"
            )
        episode_id = _text(episode.get("episode_id"), "episode_id")
        rows.append(
            _row(
                episode,
                generation_id=generation_id,
                emergence=emergence_by_episode.get(episode_id),
                maturity_stage=maturity_stage_by_episode.get(episode_id),
            )
        )

    rows.sort(key=lambda row: str(row["episode_id"]))
    material: dict[str, object] = {
        "schema": PROJECTION_SCHEMA,
        "definition_era": DEFINITION_ERA,
        "candidate_generation_id": generation_id,
        "market_session": market_session,
        "generated_at": generated_at,
        "row_count": len(rows),
        "rows": rows,
        "authority": dict(_AUTHORITY),
    }
    material["projection_id"] = (
        "pcs:"
        + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    )
    validate_candidate_state_projection(material)
    return material


def validate_candidate_state_projection(
    payload: Mapping[str, object],
) -> None:
    """Validate the closed non-authoritative B3 projection schema."""

    if not isinstance(payload, Mapping):
        raise CandidateStateContractError("projection must be an object")

    expected = {
        "schema",
        "definition_era",
        "candidate_generation_id",
        "market_session",
        "generated_at",
        "row_count",
        "rows",
        "authority",
        "projection_id",
    }
    if set(payload) != expected:
        raise CandidateStateContractError(
            "projection fields are not closed"
        )
    if (
        payload.get("schema") != PROJECTION_SCHEMA
        or payload.get("definition_era") != DEFINITION_ERA
    ):
        raise CandidateStateContractError(
            "projection schema/era mismatch"
        )

    generation_id = payload.get("candidate_generation_id")
    if (
        not isinstance(generation_id, str)
        or not _GENERATION_RE.fullmatch(generation_id)
    ):
        raise CandidateStateContractError(
            "projection generation invalid"
        )
    if payload.get("market_session") != _market_session(
        payload.get("market_session")
    ):
        raise CandidateStateContractError("market_session is not canonical")
    if payload.get("generated_at") != _generated_at(payload.get("generated_at")):
        raise CandidateStateContractError("generated_at is not canonical")

    rows = payload.get("rows")
    if (
        not isinstance(rows, list)
        or payload.get("row_count") != len(rows)
    ):
        raise CandidateStateContractError(
            "projection row count invalid"
        )
    if payload.get("authority") != _AUTHORITY:
        raise CandidateStateContractError(
            "projection authority must be all false"
        )

    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise CandidateStateContractError(
                "candidate state row must be object"
            )
        required = {
            "schema",
            "definition_era",
            "episode_id",
            "security_id",
            "company_id",
            "identity_epoch",
            "candidate_generation_id",
            "episode_lifecycle",
            "emergence_state",
            "maturity_state",
            "entry_availability",
            "authority",
        }
        if set(row) != required:
            raise CandidateStateContractError(
                "candidate state row fields are not closed"
            )
        if (
            row.get("schema") != ROW_SCHEMA
            or row.get("definition_era") != DEFINITION_ERA
            or row.get("candidate_generation_id") != generation_id
        ):
            raise CandidateStateContractError(
                "candidate state row identity mismatch"
            )

        episode_id = _text(row.get("episode_id"), "episode_id")
        if episode_id in seen:
            raise CandidateStateContractError("duplicate episode_id")
        seen.add(episode_id)

        _text(row.get("security_id"), "security_id")
        _text(row.get("company_id"), "company_id")
        _text(row.get("identity_epoch"), "identity_epoch")
        _validate_lifecycle_projection(row.get("episode_lifecycle"))
        _validate_emergence_projection(row.get("emergence_state"))
        _validate_maturity_projection(row.get("maturity_state"))

        if row.get("entry_availability") != {
            "state": "UNAVAILABLE_DATA",
            "reason": "B4_NOT_AVAILABLE",
        }:
            raise CandidateStateContractError(
                "B4 availability must remain unavailable"
            )
        if row.get("authority") != _AUTHORITY:
            raise CandidateStateContractError(
                "row authority must be all false"
            )

    if [row["episode_id"] for row in rows] != sorted(seen):
        raise CandidateStateContractError(
            "candidate state rows must be sorted"
        )

    material = {
        key: value
        for key, value in payload.items()
        if key != "projection_id"
    }
    expected_id = (
        "pcs:"
        + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    )
    if payload.get("projection_id") != expected_id:
        raise CandidateStateContractError(
            "projection_id mismatch"
        )
