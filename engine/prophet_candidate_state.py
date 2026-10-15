"""Pure, non-authoritative B3 candidate-state projection over canonical B1.

This module is a replaceable read model. It does not own B1 identity/lifecycle,
B4 Availability, ranking, plans, origination, sizing, execution, or trades.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re

from engine.prophet_candidate_state_sources import (
    CandidateStateSourceError,
    index_turn_watch_events,
)
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot,
    EpisodeContractError,
    ValidatedCandidateEpisodeGeneration,
    _parse_episode_id as _parse_b1_episode_id,
    canonical_json as _owner_canonical_json,
    validate_candidate_episode_generation,
)

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

        security_id = _text(row.get("security_id"), "security_id")
        _text(row.get("company_id"), "company_id")
        identity_epoch = _text(row.get("identity_epoch"), "identity_epoch")
        try:
            episode_security_id, episode_identity_epoch, _, _ = _parse_b1_episode_id(episode_id)
        except EpisodeContractError as exc:
            raise CandidateStateContractError(
                "episode_id is not a canonical B1 candidate episode identifier"
            ) from exc
        if (
            episode_security_id != security_id
            or episode_identity_epoch != identity_epoch
        ):
            raise CandidateStateContractError(
                "candidate identity does not match canonical B1 episode identity"
            )
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


# ---------------------------------------------------------------------------
# Prospective native factual observation assessment (strict owner read).
#
# Additive to the pure projection above: ``project_candidate_states`` keeps its
# duck-typed compatibility, and only this native owner entry point is strict.
# The assessment is a read-only, non-authoritative factual observation over one
# already-published B1 generation. It performs no store write and mints no
# rank, score, probability, sizing, entry decision, plan, or trading authority.
# The caller supplies only the candidate source key and its source receipt as
# assertions to match against native data; security, episode, generation and
# market session are always derived from the validated B1 owner content. The
# state stays REVIEW_REQUIRED because native thesis/model/review lineage is not
# readable here, and the assembly asof never renews source freshness.
# ---------------------------------------------------------------------------

ASSESSMENT_INPUT_SCHEMA = "prophet.daily_brief_assessment_input/v1"
ASSESSMENT_OWNER_REF = (
    "engine/prophet_candidate_state.py::build_native_factual_assessment"
)
ASSESSMENT_METHOD = (
    "engine.prophet_candidate_state.build_native_factual_assessment/v1"
)
ASSESSMENT_STATE = "REVIEW_REQUIRED"
ASSESSMENT_METHOD_SUMMARY = "deterministic_native_factual_observation"
B4_NATIVE_OWNER_READ_UNAVAILABLE = "B4_NATIVE_OWNER_READ_UNAVAILABLE"
_SHA256_RECEIPT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROJECTION_ID_RE = re.compile(r"^pcs:[0-9a-f]{64}$")
_CANDIDATE_SOURCE_SYSTEM = "candidate"
_CANDIDATE_SOURCE_SCHEMA = "us_prophet_rank.candidates/v1"
_TURN_WATCH_SOURCE_SYSTEM = "turn_watch"
_CANDIDATE_SOURCE_KEY_RE = re.compile(r"^candidate:([0-9]{4}-[0-9]{2}-[0-9]{2}):(.+)$")
_ASSESSMENT_FIELDS = frozenset(
    {
        "schema",
        "security_id",
        "episode_id",
        "candidate_generation_id",
        "market_session",
        "owner_ref",
        "asof",
        "state",
        "summary",
        "provenance",
        "receipt_material",
        "source_receipt",
    }
)
_ASSESSMENT_SUMMARY_FIELDS = frozenset(
    {
        "method",
        "assessment_state",
        "emergence_state",
        "emergence_reason",
        "emergence_source_system",
        "emergence_source_token",
        "emergence_source_ref",
        "episode_lifecycle_state",
        "maturity_state",
        "entry_availability_state",
        "b4_native_owner_read",
        "model_thesis",
        "review_lineage",
        "review_ref",
        "source_freshness",
    }
)
_ASSESSMENT_PROVENANCE_FIELDS = frozenset(
    {
        "candidate_generation_id",
        "generation_recorded_at",
        "generation_receipt_sha256",
        "definition_era",
        "market_session",
        "episode_id",
        "episode_opened_at",
        "episode_opened_session",
        "episode_lifecycle_state",
        "matched_relation",
        "input_binding",
        "turn_watch",
        "b3_projection_id",
        "b3_projection_sha256",
    }
)
_ASSESSMENT_RELATION_FIELDS = frozenset(
    {
        "relation_event_id",
        "relation_event_type",
        "relation_source_system",
        "relation_source_schema",
        "relation_source_event_id",
        "relation_source_receipt",
        "relation_occurred_at",
        "relation_known_at",
        "relation_recorded_at",
    }
)
_ASSESSMENT_INPUT_BINDING_FIELDS = frozenset(
    {"candidate_source_event_id", "candidate_source_receipt"}
)
_ASSESSMENT_TURN_WATCH_FIELDS = frozenset(
    {
        "source",
        "generation_recorded_at",
        "content_sha256",
        "facts",
        "selected_relation_event_id",
        "selected_known_at",
    }
)
_ASSESSMENT_RECEIPT_FIELDS = frozenset(
    {
        "method",
        "candidate_generation_id",
        "generation_receipt_sha256",
        "security_id",
        "episode_id",
        "market_session",
        "matched_relation",
        "turn_watch",
        "b3_projection_sha256",
    }
)


@dataclass(frozen=True)
class NativeFactualAssessmentResult:
    """One fixed native owner read result, receipt-bound end to end.

    ``assessment`` is the closed assessment envelope; ``projection`` is the
    exact internally derived B3 projection whose id and bytes the receipt
    binds. Construction deep-copies both documents and enforces the full
    one-read identity between them: exact receipted projection id and byte
    digest agreement, the same candidate generation, market session and
    assembly instant, and exactly one bound episode/security row whose
    lifecycle, emergence and maturity the displayed summary restates.

    That binding is enforced at construction; it is not live afterwards. The
    exposed mappings stay plain mappings for backward compatibility — they
    can still be mutated in place, and hash integrity alone is not native
    authentication. A later B4 consumer must therefore take its consumable
    bytes from :meth:`verified_pair`, which re-enforces the same one-read
    identity and returns detached validated copies, so nested-map drift
    after construction is typed-refused instead of silently served.
    """

    assessment: Mapping[str, object]
    projection: Mapping[str, object]

    def __post_init__(self) -> None:
        # Copy once at construction so no caller-held alias can drift the
        # stored documents of this fixed read from outside.
        object.__setattr__(self, "assessment", deepcopy(self.assessment))
        object.__setattr__(self, "projection", deepcopy(self.projection))
        self._verify_one_read_identity()

    def verified_pair(
        self,
    ) -> tuple[Mapping[str, object], Mapping[str, object]]:
        """Return the detached, re-verified ``(assessment, projection)`` pair.

        Re-enforces the full construction binding against the stored
        documents — closed validation of both, exact receipted projection
        id/digest agreement, and one-read identity between the summary and
        the bound projection row — then returns freshly deep-copied
        documents. A nested mutation that drifted the stored result since
        construction is typed-refused here, and later mutation of the
        returned copies can never alter this result or another consumer's
        pair.
        """
        self._verify_one_read_identity()
        # Re-validate the cross-document binding on the detached copy itself.
        # Independent schema checks do not catch drift between the two copies.
        detached = NativeFactualAssessmentResult(
            self.assessment, self.projection
        )
        return detached.assessment, detached.projection

    def _verify_one_read_identity(self) -> None:
        projection = self.projection
        assessment = self.assessment
        validate_candidate_state_projection(projection)
        validate_native_factual_assessment(assessment)
        provenance = assessment["provenance"]
        summary = assessment["summary"]
        projection_digest = (
            "sha256:"
            + sha256(_canonical_json(projection).encode("utf-8")).hexdigest()
        )
        if (
            provenance.get("b3_projection_id") != projection.get("projection_id")
            or provenance.get("b3_projection_sha256") != projection_digest
        ):
            raise CandidateStateContractError(
                "native result projection disagrees with the receipted "
                "assessment"
            )
        # One-read identity: this must be the very decision session the
        # assessed native read assembled, not a same-generation reprojection
        # or a foreign native read behind re-pointed provenance.
        for field in ("candidate_generation_id", "market_session"):
            if projection.get(field) != assessment.get(field):
                raise CandidateStateContractError(
                    f"native result projection {field} disagrees with the "
                    "assessed native read"
                )
        if projection.get("generated_at") != assessment.get("asof"):
            raise CandidateStateContractError(
                "native result projection generated_at disagrees with the "
                "assessed read assembly asof"
            )
        episode_id = assessment.get("episode_id")
        rows = [
            row
            for row in projection["rows"]
            if isinstance(row, Mapping) and row.get("episode_id") == episode_id
        ]
        if len(rows) != 1:
            raise CandidateStateContractError(
                "native result projection does not carry exactly one bound "
                "episode row"
            )
        row = rows[0]
        if (
            row.get("security_id") != assessment.get("security_id")
            or row["episode_lifecycle"]["state"]
            != summary.get("episode_lifecycle_state")
            or row["emergence_state"]["state"] != summary.get("emergence_state")
            or row["emergence_state"]["reason"]
            != summary.get("emergence_reason")
            or row["emergence_state"]["source_system"]
            != summary.get("emergence_source_system")
            or row["emergence_state"]["source_token"]
            != summary.get("emergence_source_token")
            or row["emergence_state"]["source_ref"]
            != summary.get("emergence_source_ref")
            or row["maturity_state"]["state"] != summary.get("maturity_state")
            or row["entry_availability"]["state"]
            != summary.get("entry_availability_state")
        ):
            raise CandidateStateContractError(
                "native result summary disagrees with its bound projection "
                "row"
            )


def _assembly_now() -> datetime:
    """The single module assembly clock; tests monkeypatch only this seam."""
    return datetime.now(timezone.utc)


def _assembly_clock() -> datetime:
    """Type a naive owner clock instead of leaking or localizing it."""
    now = _assembly_now()
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise CandidateStateContractError(
            "assembly clock must be a timezone-aware instant"
        )
    return now


def _envelope_receipt(assessment: Mapping[str, object]) -> str:
    """Content-address the complete presented envelope minus the receipt.

    Hash integrity alone is not native authentication, but whatever the
    receipt covers cannot be forged: the displayed summary, asof and
    provenance are exactly the receipted material.
    """
    material = {
        key: value
        for key, value in assessment.items()
        if key != "source_receipt"
    }
    return (
        "sha256:"
        + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    )


def _asof_text(now: datetime) -> str:
    return (
        now.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _native_instant(value: object, field: str) -> datetime:
    """Parse one canonical B1 UTC clock for chronological comparison only."""
    text = _text(value, field)
    if not _RFC3339_UTC_RE.fullmatch(text):
        raise CandidateStateContractError(
            f"{field} must be a canonical UTC RFC3339 instant"
        )
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise CandidateStateContractError(
            f"{field} is not a real UTC instant"
        ) from exc
    return parsed.astimezone(timezone.utc)


def _require_not_future(instant: datetime, now: datetime, field: str) -> None:
    if instant > now:
        raise CandidateStateContractError(
            f"{field} is in the future of the assembly clock"
        )


def _match_candidate_relation(
    events: Sequence[Mapping[str, object]],
    suppressions: Sequence[Mapping[str, object]],
    *,
    candidate_source_event_id: str,
    candidate_source_receipt: str,
) -> tuple[Mapping[str, object], str]:
    """Bind one caller source key/receipt pair to one unretracted B1 relation.

    The inputs are assertions to match against native data, never authority:
    security, episode, generation and market session are derived afterwards
    from the matched native content. Matching never joins by ticker.
    """
    candidate_source_event_id = _text(
        candidate_source_event_id, "candidate_source_event_id"
    )
    candidate_source_receipt = _text(
        candidate_source_receipt, "candidate_source_receipt"
    )
    if not _SHA256_RECEIPT_RE.fullmatch(candidate_source_receipt):
        raise CandidateStateContractError(
            "candidate_source_receipt must be a sha256 receipt"
        )
    key_match = _CANDIDATE_SOURCE_KEY_RE.fullmatch(candidate_source_event_id)
    if key_match is None or not key_match.group(2):
        raise CandidateStateContractError(
            "candidate_source_event_id is not a canonical "
            "candidate:{YYYY-MM-DD}:... source key"
        )
    market_session = _market_session(key_match.group(1))

    retracted_relation_ids: set[str] = set()
    for raw in events:
        if not isinstance(raw, Mapping):
            raise CandidateStateContractError("B1 event must be an object")
        if raw.get("event_type") != "RETRACTED":
            continue
        target = raw.get("correction_of")
        if not isinstance(target, str) or not target:
            raise CandidateStateContractError(
                "B1 retraction must identify correction_of relation"
            )
        retracted_relation_ids.add(target)

    matches: list[Mapping[str, object]] = []
    for raw in events:
        if not isinstance(raw, Mapping):
            raise CandidateStateContractError("B1 event must be an object")
        if raw.get("event_type") not in {"OPENED", "OBSERVED"}:
            continue
        if (
            raw.get("source_system") != _CANDIDATE_SOURCE_SYSTEM
            or raw.get("source_schema") != _CANDIDATE_SOURCE_SCHEMA
        ):
            continue
        if raw.get("source_event_id") != candidate_source_event_id:
            continue
        matches.append(raw)

    if not matches:
        for row in suppressions:
            if not isinstance(row, Mapping):
                raise CandidateStateContractError(
                    "B1 suppression must be an object"
                )
            if (
                row.get("source_system") == _CANDIDATE_SOURCE_SYSTEM
                and row.get("source_schema") == _CANDIDATE_SOURCE_SCHEMA
                and row.get("source_event_id") == candidate_source_event_id
            ):
                raise CandidateStateContractError(
                    "candidate source key is suppressed in the native B1 "
                    "ledger and cannot be bound"
                )
        raise CandidateStateContractError(
            "candidate source key has no OPENED/OBSERVED relation in the "
            "native B1 ledger"
        )
    if len(matches) > 1:
        raise CandidateStateContractError(
            "candidate source key binding is ambiguous in the native B1 ledger"
        )
    relation = matches[0]
    if str(relation.get("event_id")) in retracted_relation_ids:
        raise CandidateStateContractError(
            "candidate source relation is retracted in the native B1 ledger"
        )
    if relation.get("source_receipt") != candidate_source_receipt:
        raise CandidateStateContractError(
            "candidate_source_receipt does not match the native B1 relation "
            "source receipt"
        )
    return relation, market_session


def _select_native_turn_watch_fact(
    turn_watch: object, episode_id: str
) -> Mapping[str, object] | None:
    """Pick the latest generation-local TURN WATCH fact by native semantics.

    This mirrors the native owner ordering (known_at, source_event_id,
    relation_event_id) over facts already filtered by index_turn_watch_events
    for generation locality and retraction.
    """
    facts = [
        fact
        for fact in turn_watch.facts_by_event_id.values()
        if fact.get("episode_id") == episode_id
    ]
    if not facts:
        return None
    return max(
        facts,
        key=lambda fact: (
            _native_instant(fact.get("known_at"), "turn_watch known_at"),
            str(fact.get("source_event_id") or ""),
            str(fact.get("relation_event_id") or ""),
        ),
    )


def _validate_native_chronology(
    *,
    opened_at: object,
    opened_session: object,
    relation: Mapping[str, object],
    generation_recorded_at: object,
    turn_fact: Mapping[str, object] | None,
    now: datetime,
) -> None:
    """Fail closed on missing, malformed or future source clocks.

    No staleness duration is invented and source freshness is never renewed by
    asof. Ordering is enforced only where the B1 owner guarantees it, and every
    refusal is fail-closed: episode opened_at is owner derived, so a genuine
    generation whose opened_at postdates a candidate relation clock is
    typed-refused rather than guessed about — B1 guarantees no ordering
    between those clocks.
    """
    opened = _native_instant(opened_at, "episode opened_at")
    if opened_session != str(opened_at)[:10]:
        raise CandidateStateContractError(
            "episode opened_session disagrees with opened_at"
        )
    _require_not_future(opened, now, "episode opened_at")

    occurred = _native_instant(
        relation.get("occurred_at"), "candidate relation occurred_at"
    )
    known = _native_instant(
        relation.get("known_at"), "candidate relation known_at"
    )
    recorded = _native_instant(
        relation.get("recorded_at"), "candidate relation recorded_at"
    )
    if occurred > known or known > recorded:
        raise CandidateStateContractError(
            "candidate relation clocks are not chronological"
        )
    if relation.get("event_type") == "OPENED":
        if opened > recorded:
            raise CandidateStateContractError(
                "episode opened_at is after the candidate relation recorded_at"
            )
    else:
        if opened > occurred:
            raise CandidateStateContractError(
                "episode opened_at is after the candidate relation occurred_at"
            )

    generation_instant = _native_instant(
        generation_recorded_at, "B1 generation recorded_at"
    )
    if recorded > generation_instant:
        raise CandidateStateContractError(
            "candidate relation recorded_at is after the B1 generation "
            "recorded_at"
        )
    if opened > generation_instant:
        raise CandidateStateContractError(
            "episode opened_at is after the B1 generation recorded_at"
        )
    _require_not_future(recorded, now, "candidate relation recorded_at")
    _require_not_future(generation_instant, now, "B1 generation recorded_at")

    if turn_fact is not None:
        turn_occurred = _native_instant(
            turn_fact.get("occurred_at"), "turn_watch occurred_at"
        )
        turn_known = _native_instant(
            turn_fact.get("known_at"), "turn_watch known_at"
        )
        if turn_occurred > turn_known:
            raise CandidateStateContractError(
                "turn_watch occurred_at is after known_at"
            )
        _require_not_future(turn_known, now, "turn_watch known_at")


def build_native_factual_assessment_result(
    snapshot: object,
    *,
    candidate_source_event_id: str,
    candidate_source_receipt: str,
) -> NativeFactualAssessmentResult:
    """Assemble one native factual observation read result.

    Strictly native read path: the snapshot must be a real
    ``CandidateEpisodeStoreSnapshot`` whose exact content is re-validated
    against its own on-disk generation (``validate_candidate_episode_generation``
    with the snapshot generation id) before any fact is used, so a constructed
    or mutated snapshot cannot bypass native disk validation. Read-only: no
    store write, no ledger mutation.

    Binding: the caller-supplied candidate source key and receipt must match
    one unretracted native B1 candidate relation (OPENED/OBSERVED,
    ``us_prophet_rank.candidates/v1``); missing, ambiguous, suppressed,
    retracted, or wrong-receipt bindings fail closed, and matching never joins
    by ticker. ``market_session`` comes only from the canonical
    ``candidate:{YYYY-MM-DD}:...`` source key and is kept separate from the
    episode ``opened_session`` and the generation ``recorded_at``.

    Facts: emergence is derived only through the existing native owner
    semantics (``index_turn_watch_events`` generation-local, retraction-aware
    facts; latest by native ``known_at`` with the stable native tie breaker),
    so a real generation-local TURN WATCH relation may produce TRIGGERED with
    the genuine relation id; otherwise emergence is
    UNESTIMABLE/SOURCE_NOT_SUPPLIED. Maturity stays UNESTIMABLE (no supplied
    stage), B4 entry availability stays UNAVAILABLE_DATA, and lifecycle
    preserves the literal B1 state (terminal never implies SUPERSEDED without
    an actual superseded_by).

    Envelope: an existing ``prophet.daily_brief_assessment_input/v1`` compositor
    input whose state is always REVIEW_REQUIRED while native thesis/model/
    review lineage is unreadable here; no review_ref is invented and CURRENT is
    never produced. The owner-issued sha256 source_receipt authenticates the
    complete presented envelope minus the receipt itself, so the displayed
    summary, asof and provenance are exactly the receipted material; hash
    integrity alone is not native authentication and the read stays guarded by
    the typed snapshot and on-disk revalidation above. The assembly asof is
    the actual owner UTC assembly instant and never renews source freshness.

    Result: the B3 projection is derived exactly once per read through the
    native TURN WATCH index and returned on the frozen
    :class:`NativeFactualAssessmentResult` beside the assessment, with the
    full one-read identity enforced at construction and re-enforced by
    :meth:`NativeFactualAssessmentResult.verified_pair`; B4 later consumes
    that verified detached pair of the same source-session projection —
    never a reprojected decision session, second read, or stamped receipt.
    """
    if not isinstance(snapshot, CandidateEpisodeStoreSnapshot):
        raise CandidateStateContractError(
            "native factual assessment requires a real "
            "CandidateEpisodeStoreSnapshot"
        )
    generation = snapshot.generation
    if not isinstance(generation, ValidatedCandidateEpisodeGeneration):
        raise CandidateStateContractError(
            "native factual assessment requires a real validated B1 generation"
        )
    generation_id = snapshot.generation_id
    if not isinstance(generation_id, str) or not _GENERATION_RE.fullmatch(
        generation_id
    ):
        raise CandidateStateContractError("snapshot generation_id is invalid")
    if not isinstance(generation.path, Path):
        raise CandidateStateContractError(
            "snapshot generation path is not a native filesystem path"
        )
    try:
        validated = validate_candidate_episode_generation(
            generation.path,
            expected_generation_id=generation_id,
        )
    except EpisodeContractError as exc:
        raise CandidateStateContractError(
            f"snapshot failed native B1 disk validation: {exc}"
        ) from exc
    for field in ("events", "suppressions", "episodes", "receipt"):
        try:
            matches = _owner_canonical_json(getattr(validated, field)) == (
                _owner_canonical_json(getattr(generation, field))
            )
        except EpisodeContractError as exc:
            raise CandidateStateContractError(
                f"snapshot {field} is not canonical native B1 JSON: {exc}"
            ) from exc
        if not matches:
            raise CandidateStateContractError(
                "snapshot content disagrees with native B1 disk validation"
            )

    relation, market_session = _match_candidate_relation(
        validated.events,
        validated.suppressions,
        candidate_source_event_id=candidate_source_event_id,
        candidate_source_receipt=candidate_source_receipt,
    )

    episode_rows = [
        row
        for row in validated.episodes
        if isinstance(row, Mapping) and row.get("episode_id") == relation["episode_id"]
    ]
    if len(episode_rows) != 1:
        raise CandidateStateContractError(
            "matched candidate relation has no unique episode in the "
            "validated B1 projection"
        )
    episode = episode_rows[0]
    episode_id = _text(episode.get("episode_id"), "episode_id")
    security_id = _text(episode.get("security_id"), "episode security_id")

    now = _assembly_clock()
    try:
        turn_watch = index_turn_watch_events(snapshot)
    except CandidateStateSourceError as exc:
        raise CandidateStateContractError(
            f"native TURN WATCH indexing failed closed: {exc}"
        ) from exc
    generation_recorded_at = turn_watch.receipt["generation_recorded_at"]
    selected = _select_native_turn_watch_fact(turn_watch, episode_id)
    _validate_native_chronology(
        opened_at=episode.get("opened_at"),
        opened_session=episode.get("opened_session"),
        relation=relation,
        generation_recorded_at=generation_recorded_at,
        turn_fact=selected,
        now=now,
    )

    emergence = None
    if selected is not None:
        emergence = {
            "state": "TRIGGERED",
            "reason": None,
            "source_system": "turn_watch",
            "source_token": f"B1_{selected.get('relation_event_type')}",
            "source_ref": selected.get("relation_event_id"),
        }

    asof = _generated_at(_asof_text(now))
    projection = project_candidate_states(
        snapshot,
        market_session=market_session,
        generated_at=asof,
        emergence_by_episode=(
            {episode_id: emergence} if emergence is not None else None
        ),
    )
    matched_rows = [
        row for row in projection["rows"] if row["episode_id"] == episode_id
    ]
    if len(matched_rows) != 1:
        raise CandidateStateContractError(
            "native projection did not return exactly one bound candidate row"
        )
    row = matched_rows[0]

    matched_relation_material = {
        "relation_event_id": relation.get("event_id"),
        "relation_event_type": relation.get("event_type"),
        "relation_source_system": relation.get("source_system"),
        "relation_source_schema": relation.get("source_schema"),
        "relation_source_event_id": relation.get("source_event_id"),
        "relation_source_receipt": relation.get("source_receipt"),
        "relation_occurred_at": relation.get("occurred_at"),
        "relation_known_at": relation.get("known_at"),
        "relation_recorded_at": relation.get("recorded_at"),
    }
    turn_watch_material = {
        "source": turn_watch.receipt["source"],
        "generation_recorded_at": generation_recorded_at,
        "content_sha256": turn_watch.receipt["content_sha256"],
        "facts": turn_watch.receipt["facts"],
        "selected_relation_event_id": (
            selected.get("relation_event_id") if selected is not None else None
        ),
        "selected_known_at": (
            selected.get("known_at") if selected is not None else None
        ),
    }
    projection_sha256 = "sha256:" + sha256(
        _canonical_json(projection).encode("utf-8")
    ).hexdigest()
    receipt_material = {
        "method": ASSESSMENT_METHOD,
        "candidate_generation_id": generation_id,
        "generation_receipt_sha256": turn_watch.receipt[
            "generation_receipt_sha256"
        ],
        "security_id": security_id,
        "episode_id": episode_id,
        "market_session": market_session,
        "matched_relation": matched_relation_material,
        "turn_watch": turn_watch_material,
        "b3_projection_sha256": projection_sha256,
    }

    assessment = {
        "schema": ASSESSMENT_INPUT_SCHEMA,
        "security_id": security_id,
        "episode_id": episode_id,
        "candidate_generation_id": generation_id,
        "market_session": market_session,
        "owner_ref": ASSESSMENT_OWNER_REF,
        "asof": asof,
        "state": ASSESSMENT_STATE,
        "summary": {
            "method": ASSESSMENT_METHOD_SUMMARY,
            "assessment_state": ASSESSMENT_STATE,
            "emergence_state": row["emergence_state"]["state"],
            "emergence_reason": row["emergence_state"]["reason"],
            "emergence_source_system": row["emergence_state"]["source_system"],
            "emergence_source_token": row["emergence_state"]["source_token"],
            "emergence_source_ref": row["emergence_state"]["source_ref"],
            "episode_lifecycle_state": row["episode_lifecycle"]["state"],
            "maturity_state": row["maturity_state"]["state"],
            "entry_availability_state": row["entry_availability"]["state"],
            "b4_native_owner_read": B4_NATIVE_OWNER_READ_UNAVAILABLE,
            "model_thesis": "UNAVAILABLE",
            "review_lineage": "UNAVAILABLE",
            "review_ref": None,
            "source_freshness": "NOT_RENEWED_BY_ASOF",
        },
        "provenance": {
            "candidate_generation_id": generation_id,
            "generation_recorded_at": generation_recorded_at,
            "generation_receipt_sha256": turn_watch.receipt[
                "generation_receipt_sha256"
            ],
            "definition_era": DEFINITION_ERA,
            "market_session": market_session,
            "episode_id": episode_id,
            "episode_opened_at": episode.get("opened_at"),
            "episode_opened_session": episode.get("opened_session"),
            "episode_lifecycle_state": row["episode_lifecycle"]["state"],
            "matched_relation": dict(matched_relation_material),
            "input_binding": {
                "candidate_source_event_id": candidate_source_event_id,
                "candidate_source_receipt": candidate_source_receipt,
            },
            "turn_watch": dict(turn_watch_material),
            "b3_projection_id": projection["projection_id"],
            "b3_projection_sha256": projection_sha256,
        },
        "receipt_material": {
            "method": ASSESSMENT_METHOD,
            "candidate_generation_id": generation_id,
            "generation_receipt_sha256": turn_watch.receipt[
                "generation_receipt_sha256"
            ],
            "security_id": security_id,
            "episode_id": episode_id,
            "market_session": market_session,
            "matched_relation": dict(matched_relation_material),
            "turn_watch": dict(turn_watch_material),
            "b3_projection_sha256": projection_sha256,
        },
        "source_receipt": "",
    }
    # The owner receipt covers the complete presented envelope minus itself,
    # so the shipped summary/asof/provenance bytes are exactly what is hashed.
    assessment["source_receipt"] = _envelope_receipt(assessment)
    validate_native_factual_assessment(assessment)
    return NativeFactualAssessmentResult(
        assessment=assessment, projection=projection
    )


def build_native_factual_assessment(
    snapshot: object,
    *,
    candidate_source_event_id: str,
    candidate_source_receipt: str,
) -> dict[str, object]:
    """Compatible wrapper: the receipt-bound assessment of one fixed read.

    Same strict native read and single derivation as
    :func:`build_native_factual_assessment_result`; only the assessment
    envelope is returned, while the actual derived B3 projection stays
    available on the frozen result for the later B4 consumer.
    """
    return build_native_factual_assessment_result(
        snapshot,
        candidate_source_event_id=candidate_source_event_id,
        candidate_source_receipt=candidate_source_receipt,
    ).assessment


def validate_native_factual_assessment(payload: Mapping[str, object]) -> None:
    """Validate the closed native assessment envelope against its receipt.

    Closed typed fields, coherence of the presented summary/asof/provenance
    with the receipted native material, and a source receipt over the complete
    presented envelope minus the receipt itself.
    """
    if not isinstance(payload, Mapping) or set(payload) != _ASSESSMENT_FIELDS:
        raise CandidateStateContractError(
            "native factual assessment fields are not closed"
        )
    if payload.get("schema") != ASSESSMENT_INPUT_SCHEMA:
        raise CandidateStateContractError(
            "native factual assessment schema mismatch"
        )
    if payload.get("owner_ref") != ASSESSMENT_OWNER_REF:
        raise CandidateStateContractError(
            "native factual assessment owner_ref mismatch"
        )
    if payload.get("state") != ASSESSMENT_STATE:
        raise CandidateStateContractError(
            "native factual assessment must stay REVIEW_REQUIRED while "
            "thesis/model/review lineage is unavailable"
        )
    for field in ("security_id", "episode_id", "candidate_generation_id"):
        _text(payload.get(field), f"assessment.{field}")
    if not _GENERATION_RE.fullmatch(str(payload.get("candidate_generation_id"))):
        raise CandidateStateContractError(
            "assessment candidate_generation_id is invalid"
        )
    if payload.get("market_session") != _market_session(
        payload.get("market_session")
    ):
        raise CandidateStateContractError(
            "assessment market_session is not canonical"
        )
    if payload.get("asof") != _generated_at(payload.get("asof")):
        raise CandidateStateContractError("assessment asof is not canonical")
    if not _SHA256_RECEIPT_RE.fullmatch(str(payload.get("source_receipt"))):
        raise CandidateStateContractError(
            "assessment source_receipt must be a sha256 receipt"
        )

    summary = payload.get("summary")
    if not isinstance(summary, Mapping) or set(summary) != (
        _ASSESSMENT_SUMMARY_FIELDS
    ):
        raise CandidateStateContractError(
            "assessment summary fields are not closed"
        )
    expected_summary = {
        "method": ASSESSMENT_METHOD_SUMMARY,
        "assessment_state": ASSESSMENT_STATE,
        "maturity_state": "UNESTIMABLE",
        "entry_availability_state": "UNAVAILABLE_DATA",
        "b4_native_owner_read": B4_NATIVE_OWNER_READ_UNAVAILABLE,
        "model_thesis": "UNAVAILABLE",
        "review_lineage": "UNAVAILABLE",
        "review_ref": None,
        "source_freshness": "NOT_RENEWED_BY_ASOF",
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise CandidateStateContractError(
                f"assessment summary {field} must be {expected!r}"
            )
    if summary.get("emergence_state") not in _EMERGENCE_STATES:
        raise CandidateStateContractError(
            "assessment summary emergence_state is invalid"
        )
    if summary.get("episode_lifecycle_state") not in _LIFECYCLE_STATES:
        raise CandidateStateContractError(
            "assessment summary episode_lifecycle_state is invalid"
        )
    for field in ("emergence_reason", "emergence_source_system",
                  "emergence_source_token", "emergence_source_ref"):
        if summary.get(field) is not None:
            _text(summary.get(field), f"assessment summary {field}")

    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != (
        _ASSESSMENT_PROVENANCE_FIELDS
    ):
        raise CandidateStateContractError(
            "assessment provenance fields are not closed"
        )
    for field in _ASSESSMENT_PROVENANCE_FIELDS - {
        "matched_relation", "input_binding", "turn_watch",
    }:
        value = provenance.get(field)
        if value is not None:
            _text(value, f"assessment provenance.{field}")
    for field, expected_fields in (
        ("matched_relation", _ASSESSMENT_RELATION_FIELDS),
        ("input_binding", _ASSESSMENT_INPUT_BINDING_FIELDS),
    ):
        nested = provenance.get(field)
        if not isinstance(nested, Mapping) or set(nested) != expected_fields:
            raise CandidateStateContractError(
                f"assessment provenance {field} fields are not closed"
            )
        for key in expected_fields:
            if nested.get(key) is not None:
                _text(nested.get(key), f"assessment provenance.{field}.{key}")
    turn_watch = provenance.get("turn_watch")
    if not isinstance(turn_watch, Mapping) or set(turn_watch) != (
        _ASSESSMENT_TURN_WATCH_FIELDS
    ):
        raise CandidateStateContractError(
            "assessment provenance turn_watch fields are not closed"
        )
    for key in _ASSESSMENT_TURN_WATCH_FIELDS - {"facts"}:
        if turn_watch.get(key) is not None:
            _text(turn_watch.get(key), f"assessment provenance.turn_watch.{key}")
    facts = turn_watch.get("facts")
    if (
        not isinstance(facts, int)
        or isinstance(facts, bool)
        or facts < 0
    ):
        raise CandidateStateContractError(
            "assessment provenance turn_watch facts is invalid"
        )
    # Native selection coherence: a selected relation always carries its real
    # native known-at instant, and a zero-fact generation can never select.
    selected_relation = turn_watch.get("selected_relation_event_id")
    selected_known_at = turn_watch.get("selected_known_at")
    if (selected_relation is None) != (selected_known_at is None):
        raise CandidateStateContractError(
            "assessment provenance turn_watch selection clocks are not "
            "coherent"
        )
    if selected_known_at is not None:
        _native_instant(
            selected_known_at,
            "assessment provenance.turn_watch.selected_known_at",
        )
    if facts == 0 and selected_relation is not None:
        raise CandidateStateContractError(
            "assessment provenance turn_watch cannot select a native "
            "relation with zero receipted facts"
        )

    receipt_material = payload.get("receipt_material")
    if not isinstance(receipt_material, Mapping) or set(receipt_material) != (
        _ASSESSMENT_RECEIPT_FIELDS
    ):
        raise CandidateStateContractError(
            "assessment receipt material fields are not closed"
        )
    if receipt_material.get("method") != ASSESSMENT_METHOD:
        raise CandidateStateContractError(
            "assessment receipt material method mismatch"
        )
    # The receipted digests are content addresses, not free-form text: a
    # non-canonical digest can never be the receipted native material.
    for field in ("generation_receipt_sha256", "b3_projection_sha256"):
        digest = receipt_material.get(field)
        if not isinstance(digest, str) or not _SHA256_RECEIPT_RE.fullmatch(
            digest
        ):
            raise CandidateStateContractError(
                f"assessment receipted {field} must be a canonical sha256 "
                "receipt"
            )
    for field in (
        "candidate_generation_id", "security_id", "episode_id", "market_session"
    ):
        if receipt_material.get(field) != payload.get(field):
            raise CandidateStateContractError(
                f"assessment {field} disagrees with receipted material"
            )
    for field in ("candidate_generation_id", "episode_id", "market_session"):
        if provenance.get(field) != payload.get(field):
            raise CandidateStateContractError(
                f"assessment {field} disagrees with provenance"
            )
    binding = provenance.get("input_binding")
    relation_provenance = provenance.get("matched_relation")
    if (
        not isinstance(binding, Mapping)
        or not isinstance(relation_provenance, Mapping)
        or binding.get("candidate_source_event_id")
        != relation_provenance.get("relation_source_event_id")
        or binding.get("candidate_source_receipt")
        != relation_provenance.get("relation_source_receipt")
    ):
        raise CandidateStateContractError(
            "assessment input binding disagrees with the matched native "
            "relation"
        )
    # Coherence: the receipted material is the only source of the presented
    # provenance facts, and the summary may only restate receipted truth.
    for field in (
        "generation_receipt_sha256",
        "matched_relation",
        "turn_watch",
        "b3_projection_sha256",
    ):
        if provenance.get(field) != receipt_material.get(field):
            raise CandidateStateContractError(
                f"assessment provenance {field} disagrees with receipted "
                "material"
            )
    if provenance.get("definition_era") != DEFINITION_ERA:
        raise CandidateStateContractError(
            "assessment provenance definition_era mismatch"
        )
    b3_projection_id = provenance.get("b3_projection_id")
    if not isinstance(b3_projection_id, str) or not _PROJECTION_ID_RE.fullmatch(
        b3_projection_id
    ):
        raise CandidateStateContractError(
            "assessment provenance b3_projection_id is invalid"
        )
    if provenance.get("generation_recorded_at") != turn_watch.get(
        "generation_recorded_at"
    ):
        raise CandidateStateContractError(
            "assessment provenance generation clock disagrees with the "
            "receipted TURN WATCH generation"
        )
    # The original source clocks are bound literally, never null-erased or
    # renewed by the assembly asof.
    _native_instant(
        provenance.get("episode_opened_at"),
        "assessment provenance.episode_opened_at",
    )
    if provenance.get("episode_opened_session") != str(
        provenance.get("episode_opened_at")
    )[:10]:
        raise CandidateStateContractError(
            "assessment provenance episode_opened_session disagrees with "
            "episode_opened_at"
        )
    _native_instant(
        provenance.get("generation_recorded_at"),
        "assessment provenance.generation_recorded_at",
    )
    try:
        episode_security_id, _, _, _ = _parse_b1_episode_id(
            payload.get("episode_id")
        )
    except EpisodeContractError as exc:
        raise CandidateStateContractError(
            "assessment episode_id is not a canonical B1 candidate episode "
            "identifier"
        ) from exc
    if episode_security_id != payload.get("security_id"):
        raise CandidateStateContractError(
            "assessment episode_id does not parse to the assessed security_id"
        )
    if provenance.get("episode_lifecycle_state") not in _LIFECYCLE_STATES:
        raise CandidateStateContractError(
            "assessment provenance episode_lifecycle_state is invalid"
        )
    if summary.get("episode_lifecycle_state") != provenance.get(
        "episode_lifecycle_state"
    ):
        raise CandidateStateContractError(
            "assessment summary episode_lifecycle_state disagrees with "
            "provenance"
        )
    if selected_relation is None:
        # Without a receipted native selection no emergence token can exist;
        # a fabricated token would claim provenance the envelope never held.
        expected_emergence = {
            "emergence_state": "UNESTIMABLE",
            "emergence_reason": "SOURCE_NOT_SUPPLIED",
            "emergence_source_system": None,
            "emergence_source_ref": None,
            "emergence_source_token": None,
        }
    else:
        expected_emergence = {
            "emergence_state": "TRIGGERED",
            "emergence_reason": None,
            "emergence_source_system": _TURN_WATCH_SOURCE_SYSTEM,
            "emergence_source_ref": selected_relation,
        }
    for field, expected in expected_emergence.items():
        if summary.get(field) != expected:
            raise CandidateStateContractError(
                f"assessment summary {field} disagrees with the receipted "
                "native TURN WATCH emergence"
            )
    if selected_relation is not None:
        # The exact selected native relation type is not receipted in this
        # envelope, so only the B1_ token prefix is provable coherence here.
        emergence_token = summary.get("emergence_source_token")
        if not isinstance(emergence_token, str) or not emergence_token.startswith(
            "B1_"
        ):
            raise CandidateStateContractError(
                "assessment summary emergence_source_token disagrees with "
                "the receipted native TURN WATCH emergence"
            )
    key_match = _CANDIDATE_SOURCE_KEY_RE.fullmatch(
        str(binding.get("candidate_source_event_id"))
    )
    if key_match is None or key_match.group(1) != payload.get("market_session"):
        raise CandidateStateContractError(
            "assessment market_session disagrees with the bound candidate "
            "source key"
        )
    # Authentication: the owner receipt covers the complete presented envelope
    # minus the receipt itself, so every displayed fact is receipted material.
    if payload.get("source_receipt") != _envelope_receipt(payload):
        raise CandidateStateContractError(
            "assessment source_receipt mismatch"
        )
