"""Native Daily Brief factual evidence adapter over the unchanged Earnings D5 owner.

This module is a read-only presentation adapter.  It binds one caller-supplied
candidate source key + sha256 receipt to exactly one unretracted native B1
candidate relation inside a real, disk-revalidated
``CandidateEpisodeStoreSnapshot``, derives every identity from the matched
native content (never from a ticker/date join or a client-copied attestation),
reads the canonical issuer master from the fixed
``<repo_root>/data/reference/security_master.parquet`` bytes, and calls the
unchanged Earnings D5 owner (``build_earnings_intelligence_vector``) with the
genuine episode, the snapshot generation id, and the original OPENED
``known_at``.  The read is one-shot: the completion clock is captured only
after the owner read and validation return, and the issuer reference bytes and
the B1 snapshot head are re-attested afterwards, so state that moved underneath
the read refuses it instead of rebinding to newer bytes.

It returns a typed result envelope plus, when the owner read is admissible, one
closed ``prophet.daily_brief_evidence_input/v1`` record whose state is PARTIAL
at best.  The adapter originates no rank, score, probability, sizing, entry,
plan, or trading authority, never renews an owner clock (the fresh adapter
assembly clock is a separate field and never upgrades the fact asof), never
touches the owner's ``assembly_receipt.assembled_at``, and never leaks
filesystem paths, raw workspaces, or the whole owner vector into DailyBrief
input.  The pending B3 repair is deliberately NOT an import dependency here;
only the frozen owners listed above are reused.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from typing import Mapping, Sequence

import pandas as pd

from engine.neuralweb import company_intelligence_reader as _owner_reader
from engine.prophet_daily_brief import DailyBriefContractError
from engine.prophet_daily_brief import _reject_forbidden as _daily_brief_reject_forbidden
from engine.prophet_lab.intelligence_vector import (
    EARNINGS_FAMILY_ID,
    IntelligenceVectorContractError,
    build_earnings_intelligence_vector,
    validate_intelligence_vector,
)
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot,
    EpisodeContractError,
    ValidatedCandidateEpisodeGeneration,
    canonical_json,
    validate_candidate_episode_generation,
)
from lib.dataos.identity import (
    IdentityError,
    IssuerMaster,
    parse_id,
    security_id as canonical_security_id,
)


__all__ = [
    "DailyBriefEvidenceContractError",
    "EVIDENCE_INPUT_SCHEMA",
    "OWNER_REF",
    "REASON_VOCABULARY",
    "RESULT_SCHEMA",
    "read_native_daily_brief_evidence",
    "validate_daily_brief_evidence_input",
    "validate_daily_brief_evidence_result",
]


EVIDENCE_INPUT_SCHEMA = "prophet.daily_brief_evidence_input/v1"
RESULT_SCHEMA = "prophet.daily_brief_evidence_result/v1"
OWNER_REF = "engine/prophet_daily_brief_evidence_sources.py:read_native_daily_brief_evidence"
EVIDENCE_METHOD = "daily_brief_evidence_sources/earnings-d5-native/v1"

# The typed result vocabulary.  AVAILABLE is reserved for a future versioned
# cross-session proof and is deliberately unreachable in v1; the aggregate is
# therefore PARTIAL at best and never CURRENT.
STATE_AVAILABLE = "AVAILABLE"
STATE_PARTIAL = "PARTIAL"
STATE_UNAVAILABLE = "UNAVAILABLE"
_RESULT_STATES = frozenset({STATE_AVAILABLE, STATE_PARTIAL, STATE_UNAVAILABLE})
_PRODUCIBLE_RESULT_STATES = frozenset({STATE_PARTIAL, STATE_UNAVAILABLE})

_CANDIDATE_SOURCE_SYSTEM = "candidate"
_CANDIDATE_SOURCE_SCHEMA = "us_prophet_rank.candidates/v1"
_CANDIDATE_SOURCE_KEY_RE = re.compile(r"^candidate:(\d{4}-\d{2}-\d{2}):(.+)$")
_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256_RECEIPT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PEG_RE = re.compile(r"^peg:[0-9a-f]{64}$")
_EPISODE_ID_RE = re.compile(
    r"^pe:(?P<security>SEC:[^:]+):(?P<epoch>[^:]+):sa:[0-9a-f]{24}:[1-9][0-9]*$"
)
_EVENT_ID_RE = re.compile(r"^evt_[A-Za-z0-9_.:-]{1,127}$")
_EARNINGS_COMPANY_ID_RE = re.compile(r"^cik:[0-9]{10}$")
_WORKSPACE_GENERATION_RE = re.compile(r"^[0-9a-f]{24,64}$")
_INSTANT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_REFERENCE_RELATIVE = ("data", "reference", "security_master.parquet")
_OBSERVED_AT_BASIS = "event_workspace.lifecycle.observed_at"

_SCOPE_REASONS = frozenset({
    "SCOPE_CURRENT_GENERATION_EVENT_DISCOVERY_ONLY",
    "SCOPE_HISTORICAL_EVENT_SET_INCOMPLETE",
    "SCOPE_IDENTITY_CURRENT_REGISTRANT_ONLY",
})
_CAPPED_REASON = "STATE_CAPPED_PARTIAL_BY_CONTRACT"
_PARTIAL_BASE_REASONS = frozenset({*_SCOPE_REASONS, _CAPPED_REASON})
REASON_VOCABULARY = frozenset({
    "B1_BINDING_KEY_MALFORMED",
    "B1_BINDING_RECEIPT_MALFORMED",
    "B1_DECISION_CUT_MISMATCH",
    "B1_EPISODE_NOT_FOUND",
    "B1_OPENED_NOT_UNIQUE",
    "B1_RELATION_AMBIGUOUS",
    "B1_RELATION_NOT_FOUND",
    "B1_RELATION_RECEIPT_MISMATCH",
    "B1_RELATION_RETRACTED",
    "B1_RELATION_SUPPRESSED",
    "B1_SNAPSHOT_INVALID",
    "B1_SNAPSHOT_REVALIDATION_FAILED",
    "D5_OWNER_CONTRACT_REFUSAL",
    "IDENTITY_AMBIGUOUS",
    "IDENTITY_UNRESOLVED",
    "ISSUER_MASTER_CHANGED_DURING_READ",
    "ISSUER_MASTER_UNREADABLE",
    "OWNER_CURRENT_EVENT_NOT_PUBLISHED",
    "OWNER_EVIDENCE_AFTER_DECISION_CUT",
    "OWNER_EVIDENCE_CLOCK_FUTURE",
    "OWNER_EVIDENCE_NOT_CAPTURED_AT_DECISION",
    "OWNER_MISSING_DECISION_CLOCK",
    "OWNER_READ_CHAIN_INTEGRITY",
    "OWNER_READ_SOURCE_FETCH_FAILED",
    "OWNER_REVISION_HISTORY_EMPTY",
    "OWNER_UNRESOLVED_CLOCK_TIE",
    "SOURCE_TUPLE_SESSION_DIFFERS_FROM_OPENED_SESSION",
    *_SCOPE_REASONS,
    _CAPPED_REASON,
})

_EVIDENCE_KEYS = frozenset({
    "asof", "candidate_generation_id", "coverage", "episode_id", "fact_asof_basis",
    "market_session", "method", "owner_ref", "provenance", "read_completed_at",
    "schema", "security_id", "source_receipt", "state", "summary",
})
_COVERAGE_KEYS = frozenset({"basis", "notes", "state"})
_SUMMARY_KEYS = frozenset({
    "absent", "decision_admissibility", "evidence_family_id",
    "owner_coverage_basis", "owner_coverage_state", "source_ref_ids",
    "evidence_root_ids", "supported", "owner_warnings",
})
_SUPPORTED_KEYS = frozenset({
    "correction_lineage_state", "evidence_root_ids", "native_metric_id",
    "observation_ref", "quality_flags", "source_ref_ids", "units", "value",
    "value_state",
})
_SUPPORTED_REVENUE_KEYS = frozenset({*_SUPPORTED_KEYS, "value_usd"})
_ABSENT_KEYS = frozenset({
    "absence_reasons", "correction_lineage_state", "native_metric_id",
    "observation_ref", "value_state",
})
_PROVENANCE_KEYS = frozenset({
    "candidate_relation_event_id", "candidate_relation_event_type",
    "candidate_relation_known_at", "candidate_source_event_id",
    "candidate_source_receipt", "chosen_revision_generation_id",
    "chosen_workspace_receipt", "decision_version_ref_ids",
    "earnings_company_id", "episode_opened_at", "episode_opened_session",
    "episode_original_opened_known_at", "identity_state",
    "issuer_master_sha256", "later_correction_ref_ids",
    "later_revision_receipt_ids", "later_revision_state",
    "owner_adapter_set_version", "owner_assembly_assembled_at",
    "owner_correction_current_state", "owner_event_discovery_scope",
    "owner_family_projection_id", "owner_historical_event_set_reconstruction",
    "owner_identity_resolution_scope", "owner_lane_assessment_id",
    "owner_lanes", "owner_point_in_time_basis", "owner_projection_id",
    "owner_revision_visibility_scope", "owner_source_reader",
    "owner_source_receipts", "owner_subject_event_id", "owner_vector_errors",
    "revision_chain_bound_disclosure", "source_tuple_market_session",
})
_LANE_KEYS = frozenset({"candidate_state", "disposition", "lane", "owner_lane_receipt_id"})
_OWNER_SOURCE_RECEIPT_KEYS = frozenset({"content_hash", "object_id", "source_ref_id"})
_RESULT_KEYS = frozenset({
    "evidence_input", "owner_ref", "reasons", "schema", "source_receipt", "state",
})


class DailyBriefEvidenceContractError(ValueError):
    """Raised when a DailyBrief evidence result would invent or widen authority."""


class _Refusal(Exception):
    """Internal typed refusal carrying its canonical reason id."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _refuse(reason: str) -> None:
    if reason not in REASON_VOCABULARY:
        raise AssertionError(f"unregistered refusal reason: {reason}")
    raise _Refusal(reason)


def _read_completed_at() -> datetime:
    """The one real adapter assembly clock; fact asofs are never renewed to it.

    Captured only after the one real owner read and its canonical validation
    have both returned, so it is the actual read-completion instant and never
    a pre-read stamp."""
    return datetime.now(timezone.utc)


def _read_reference_bytes(path: Path) -> bytes:
    return Path(path).read_bytes()


def _reference_path(repo_root: object) -> Path:
    try:
        return Path(repo_root).joinpath(*_REFERENCE_RELATIVE)
    except TypeError as exc:
        raise _Refusal("ISSUER_MASTER_UNREADABLE") from exc


def _format_instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not _INSTANT_RE.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return None if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _receipt_of(envelope: Mapping[str, object]) -> str:
    material = {key: value for key, value in envelope.items() if key != "source_receipt"}
    return "sha256:" + sha256(canonical_json(material).encode("utf-8")).hexdigest()


def _load_issuer_master(repo_root: object) -> tuple[IssuerMaster, str]:
    """Read the fixed reference parquet bytes once, attest an identical re-read."""
    reference = _reference_path(repo_root)
    try:
        payload = _read_reference_bytes(reference)
        reloaded = _read_reference_bytes(reference)
    except (OSError, ValueError):
        _refuse("ISSUER_MASTER_UNREADABLE")
    read_sha256 = "sha256:" + sha256(payload).hexdigest()
    if reloaded != payload:
        _refuse("ISSUER_MASTER_CHANGED_DURING_READ")
    try:
        records = pd.read_parquet(BytesIO(payload)).to_dict("records")
        return IssuerMaster.from_records(records), read_sha256
    except Exception as exc:  # noqa: BLE001 — any decode failure fails closed, typed below
        raise _Refusal("ISSUER_MASTER_UNREADABLE") from exc


def _assert_issuer_master_unchanged(repo_root: object, issuer_master_sha256: str) -> None:
    """Final post-read guard: the exact issuer bytes that fed the one owner
    read must still be the on-disk reference bytes.  A reference that moved
    underneath the read means the read mixed two issuer identities, so the
    whole read refuses instead of rebinding to the newer bytes."""
    try:
        reference = _reference_path(repo_root)
        current = "sha256:" + sha256(_read_reference_bytes(reference)).hexdigest()
    except (OSError, ValueError) as exc:
        raise _Refusal("ISSUER_MASTER_CHANGED_DURING_READ") from exc
    if current != issuer_master_sha256:
        _refuse("ISSUER_MASTER_CHANGED_DURING_READ")


def _assert_snapshot_head_unchanged(snapshot: object, generation_id: str) -> None:
    """Final post-read guard: revalidate the actual B1 snapshot head against
    its own on-disk generation after the one owner read.  The same generation
    identity plus byte-identical validated content is required; any drift in
    the immutable generation or its head binding refuses the read instead of
    re-reading or rebinding to a newer head."""
    if _revalidate_snapshot(snapshot)[0] != generation_id:
        _refuse("B1_SNAPSHOT_REVALIDATION_FAILED")


def _validate_binding_text(candidate_source_event_id: object, candidate_source_receipt: object) -> tuple[str, str, str]:
    if not isinstance(candidate_source_event_id, str) or any(
        ord(character) < 32 for character in candidate_source_event_id
    ):
        _refuse("B1_BINDING_KEY_MALFORMED")
    key_match = _CANDIDATE_SOURCE_KEY_RE.fullmatch(candidate_source_event_id)
    if key_match is None or not key_match.group(2):
        _refuse("B1_BINDING_KEY_MALFORMED")
    try:
        date.fromisoformat(key_match.group(1))
    except ValueError:
        _refuse("B1_BINDING_KEY_MALFORMED")
    if not isinstance(candidate_source_receipt, str) or not _SHA256_RECEIPT_RE.fullmatch(
        candidate_source_receipt
    ):
        _refuse("B1_BINDING_RECEIPT_MALFORMED")
    return candidate_source_event_id, key_match.group(1), candidate_source_receipt


def _revalidate_snapshot(snapshot: object) -> tuple[str, ValidatedCandidateEpisodeGeneration]:
    """Bind only a real B1 snapshot, revalidated against its own on-disk bytes."""
    if not isinstance(snapshot, CandidateEpisodeStoreSnapshot):
        _refuse("B1_SNAPSHOT_INVALID")
    generation = snapshot.generation
    generation_id = snapshot.generation_id
    if not isinstance(generation, ValidatedCandidateEpisodeGeneration) or not isinstance(
        generation_id, str
    ) or not _PEG_RE.fullmatch(generation_id) or not isinstance(generation.path, Path):
        _refuse("B1_SNAPSHOT_INVALID")
    try:
        validated = validate_candidate_episode_generation(
            generation.path, expected_generation_id=generation_id,
        )
    except EpisodeContractError as exc:
        raise _Refusal("B1_SNAPSHOT_REVALIDATION_FAILED") from exc
    for field in ("events", "suppressions", "episodes", "receipt"):
        if canonical_json(getattr(validated, field)) != canonical_json(getattr(generation, field)):
            _refuse("B1_SNAPSHOT_REVALIDATION_FAILED")
    return generation_id, validated


def _match_candidate_relation(
    events: Sequence[Mapping[str, object]],
    suppressions: Sequence[Mapping[str, object]],
    *,
    candidate_source_event_id: str,
    candidate_source_receipt: str,
) -> Mapping[str, object]:
    """Bind the caller pair to one unretracted native B1 candidate relation.

    The inputs are assertions matched against native data, never authority:
    security, episode, generation, and market session are derived afterwards
    from the matched native content.  Matching never joins by ticker or date.
    """
    retracted: set[str] = set()
    for raw in events:
        if raw.get("event_type") == "RETRACTED" and isinstance(raw.get("correction_of"), str):
            retracted.add(str(raw["correction_of"]))
    matches = [
        raw for raw in events
        if raw.get("event_type") in {"OPENED", "OBSERVED"}
        and raw.get("source_system") == _CANDIDATE_SOURCE_SYSTEM
        and raw.get("source_schema") == _CANDIDATE_SOURCE_SCHEMA
        and raw.get("source_event_id") == candidate_source_event_id
    ]
    if not matches:
        for row in suppressions:
            if (
                row.get("source_system") == _CANDIDATE_SOURCE_SYSTEM
                and row.get("source_schema") == _CANDIDATE_SOURCE_SCHEMA
                and row.get("source_event_id") == candidate_source_event_id
            ):
                _refuse("B1_RELATION_SUPPRESSED")
        _refuse("B1_RELATION_NOT_FOUND")
    if len(matches) > 1:
        _refuse("B1_RELATION_AMBIGUOUS")
    relation = matches[0]
    if str(relation.get("event_id")) in retracted:
        _refuse("B1_RELATION_RETRACTED")
    if relation.get("source_receipt") != candidate_source_receipt:
        _refuse("B1_RELATION_RECEIPT_MISMATCH")
    return relation


def _match_episode_and_cut(
    validated: ValidatedCandidateEpisodeGeneration, relation: Mapping[str, object],
) -> tuple[Mapping[str, object], str]:
    episode_rows = [
        row for row in validated.episodes
        if isinstance(row, Mapping) and row.get("episode_id") == relation.get("episode_id")
    ]
    if len(episode_rows) != 1:
        _refuse("B1_EPISODE_NOT_FOUND")
    episode = episode_rows[0]
    episode_id = str(relation.get("episode_id"))
    openings = [
        raw for raw in validated.events
        if raw.get("event_type") == "OPENED" and raw.get("episode_id") == episode_id
    ]
    if len(openings) != 1:
        _refuse("B1_OPENED_NOT_UNIQUE")
    opened_known_at = str(openings[0].get("known_at"))
    anchor = episode.get("structural_anchor")
    anchor_time = anchor.get("time") if isinstance(anchor, Mapping) else None
    cut = episode.get("opened_at")
    parsed = (_parse_instant(cut), _parse_instant(anchor_time), _parse_instant(opened_known_at))
    if any(value is None for value in parsed) or parsed[0] != max(parsed[1], parsed[2]):  # type: ignore[type-var]
        _refuse("B1_DECISION_CUT_MISMATCH")
    return episode, opened_known_at


def _owner_refusals(vector: Mapping[str, object]) -> list[str]:
    """Map one unchanged owner D5 read outcome to typed adapter reasons."""
    family = vector["evidence_families"][0]
    identity_state = str(family["identity_state"])
    if identity_state == "AMBIGUOUS":
        return ["IDENTITY_AMBIGUOUS"]
    if identity_state == "UNRESOLVED":
        return ["IDENTITY_UNRESOLVED"]
    for error in vector["assembly_receipt"]["errors"]:
        if error.get("type") == "WorkspaceChainIntegrityError":
            return ["OWNER_READ_CHAIN_INTEGRITY"]
        if error.get("type") == "CompanyIntelligenceReadError":
            return ["OWNER_READ_SOURCE_FETCH_FAILED"]
    coverage = family["coverage"]
    if coverage["state"] == "NOT_COVERED":
        return [{
            "no_current_generation_event": "OWNER_CURRENT_EVENT_NOT_PUBLISHED",
            "no_verified_revisions": "OWNER_REVISION_HISTORY_EMPTY",
        }.get(str(coverage["basis"]), "OWNER_EVIDENCE_NOT_CAPTURED_AT_DECISION")]
    if coverage["state"] == "UNKNOWN" and coverage["basis"] in {
        "current_manifest_integrity_failure", "source_fetch_failed",
    }:
        return [
            "OWNER_READ_CHAIN_INTEGRITY"
            if coverage["basis"] == "current_manifest_integrity_failure"
            else "OWNER_READ_SOURCE_FETCH_FAILED"
        ]
    admissibility = str(family["point_in_time"]["decision_admissibility"])
    if family["point_in_time"]["missing_clocks"]:
        return ["OWNER_MISSING_DECISION_CLOCK"]
    if admissibility == "AFTER_DECISION_CUT":
        return ["OWNER_EVIDENCE_AFTER_DECISION_CUT"]
    if admissibility == "UNVERIFIABLE":
        if "unresolved_clock_tie" in family["quality"]["flags"]:
            return ["OWNER_UNRESOLVED_CLOCK_TIE"]
        return ["OWNER_EVIDENCE_NOT_CAPTURED_AT_DECISION"]
    if admissibility != "ADMISSIBLE":
        return ["OWNER_EVIDENCE_NOT_CAPTURED_AT_DECISION"]
    return []


def _literal_observation_rows(observations: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Copy the literal supported/absent observation facts, never the raw vector."""
    supported: list[dict[str, object]] = []
    absent: list[dict[str, object]] = []
    for item in observations:
        if item.get("value_state") == "ABSENT":
            absent.append({
                "absence_reasons": list(item["absence_reasons"]),
                "correction_lineage_state": item["correction_lineage_state"],
                "native_metric_id": item["native_metric_id"],
                "observation_ref": item["observation_id"],
                "value_state": "ABSENT",
            })
            continue
        row: dict[str, object] = {
            "correction_lineage_state": item["correction_lineage_state"],
            "evidence_root_ids": list(item["evidence_root_ids"]),
            "native_metric_id": item["native_metric_id"],
            "observation_ref": item["observation_id"],
            "quality_flags": list(item["quality_flags"]),
            "source_ref_ids": list(item["source_ref_ids"]),
            "units": deepcopy(item["units"]),
            "value": deepcopy(item["value"]),
            "value_state": item["value_state"],
        }
        if "value_usd" in item:
            row["value_usd"] = deepcopy(item["value_usd"])
        supported.append(row)
    return supported, absent


def _evidence_input(
    *, episode: Mapping[str, object], market_session: str,
    candidate_source_event_id: str, candidate_source_receipt: str,
    relation: Mapping[str, object], opened_known_at: str,
    vector: Mapping[str, object], generation_id: str,
    issuer_master_sha256: str, read_completed_at: datetime,
    reasons: list[str],
) -> dict[str, object]:
    family = vector["evidence_families"][0]
    supported, absent = _literal_observation_rows(family["observations"])
    binding = family["subject_binding"]
    lanes = family["owner_lane_dispositions"]
    assembly = vector["assembly_receipt"]
    point_in_time = family["point_in_time"]
    known_clock = point_in_time["known_at"]
    asof = known_clock["value"]
    evidence: dict[str, object] = {
        "schema": EVIDENCE_INPUT_SCHEMA,
        "security_id": str(episode["security_id"]),
        "episode_id": str(episode["episode_id"]),
        "candidate_generation_id": generation_id,
        "market_session": market_session,
        "owner_ref": OWNER_REF,
        "state": STATE_PARTIAL,
        "asof": str(asof),
        "fact_asof_basis": str(known_clock["basis"]),
        "method": EVIDENCE_METHOD,
        "read_completed_at": _format_instant(read_completed_at),
        "summary": {
            "evidence_family_id": EARNINGS_FAMILY_ID,
            "owner_coverage_state": str(family["coverage"]["state"]),
            "owner_coverage_basis": str(family["coverage"]["basis"]),
            "decision_admissibility": str(point_in_time["decision_admissibility"]),
            "supported": supported,
            "absent": absent,
            "source_ref_ids": sorted(str(ref["source_ref_id"]) for ref in family["source_refs"]),
            "evidence_root_ids": sorted(str(root["evidence_root_id"]) for root in family["evidence_roots"]),
            "owner_warnings": sorted(str(warning) for warning in family["owner_warnings"]),
        },
        "coverage": {"state": str(family["coverage"]["state"]), "basis": str(family["coverage"]["basis"]), "notes": sorted(set(reasons))},
        "provenance": {
            "candidate_relation_event_id": str(relation["event_id"]),
            "candidate_relation_event_type": str(relation["event_type"]),
            "candidate_relation_known_at": str(relation["known_at"]),
            "candidate_source_event_id": candidate_source_event_id,
            "candidate_source_receipt": candidate_source_receipt,
            "chosen_revision_generation_id": str(lanes["generation_id"]),
            "chosen_workspace_receipt": dict(lanes["workspace_receipt"]),
            "decision_version_ref_ids": sorted(str(ref) for ref in family["correction"]["decision_version_ref_ids"]),
            "earnings_company_id": str(binding["earnings_company_id"]),
            "episode_opened_at": str(episode["opened_at"]),
            "episode_opened_session": str(episode["opened_session"]),
            "episode_original_opened_known_at": opened_known_at,
            "identity_state": str(binding["state"]),
            "issuer_master_sha256": issuer_master_sha256,
            "later_correction_ref_ids": sorted(str(ref) for ref in family["correction"]["later_correction_ref_ids"]),
            "later_revision_receipt_ids": sorted(
                str(row["later_revision_receipt_id"])
                for row in family["correction"]["later_revision_receipts"]
            ),
            "later_revision_state": str(family["correction"]["later_revision_state"]),
            "owner_adapter_set_version": str(vector["adapter_set_version"]),
            # The owner assembly receipt stays untouched (assembled_at is None);
            # the fresh adapter clock lives only in read_completed_at above.
            "owner_assembly_assembled_at": assembly["assembled_at"],
            "owner_correction_current_state": str(family["correction"]["current_state"]),
            "owner_event_discovery_scope": str(assembly["event_discovery_scope"]),
            "owner_family_projection_id": str(family["family_projection_id"]),
            "owner_historical_event_set_reconstruction": bool(assembly["historical_event_set_reconstruction"]),
            "owner_identity_resolution_scope": str(assembly["identity_resolution_scope"]),
            "owner_lane_assessment_id": str(lanes["owner_lane_assessment_id"]),
            "owner_lanes": [
                {
                    "candidate_state": str(lane["candidate_state"]),
                    "disposition": str(lane["disposition"]),
                    "lane": str(lane["lane"]),
                    "owner_lane_receipt_id": str(lane["owner_lane_receipt_id"]),
                }
                for lane in lanes["lanes"]
            ],
            "owner_point_in_time_basis": str(point_in_time["basis"]),
            "owner_projection_id": str(vector["projection_id"]),
            "owner_revision_visibility_scope": str(assembly["revision_visibility_scope"]),
            "owner_source_reader": str(assembly["source_reader"]),
            "owner_source_receipts": [
                {
                    "content_hash": deepcopy(ref["content_hash"]),
                    "object_id": str(ref["object_id"]),
                    "source_ref_id": str(ref["source_ref_id"]),
                }
                for ref in family["source_refs"]
            ],
            "owner_subject_event_id": str(binding["owner_subject_id"]),
            "owner_vector_errors": [],
            "revision_chain_bound_disclosure": str(assembly["revision_chain_bound_disclosure"]),
            "source_tuple_market_session": market_session,
        },
    }
    evidence["source_receipt"] = _receipt_of(evidence)
    return evidence


def _read(
    repo_root: object,
    *,
    snapshot: object,
    candidate_source_event_id: object,
    candidate_source_receipt: object,
) -> dict[str, object]:
    key, market_session, receipt = _validate_binding_text(
        candidate_source_event_id, candidate_source_receipt,
    )
    generation_id, validated = _revalidate_snapshot(snapshot)
    relation = _match_candidate_relation(
        validated.events, validated.suppressions,
        candidate_source_event_id=key, candidate_source_receipt=receipt,
    )
    episode, opened_known_at = _match_episode_and_cut(validated, relation)
    if market_session != str(episode.get("opened_session")):
        # A source tuple from a different session than the episode cut is not
        # representable as a current aggregate; it stays typed and capped.
        extra_reasons = ["SOURCE_TUPLE_SESSION_DIFFERS_FROM_OPENED_SESSION"]
    else:
        extra_reasons = []
    issuer_master, issuer_master_sha256 = _load_issuer_master(repo_root)
    try:
        vector = build_earnings_intelligence_vector(
            episode=dict(episode),
            episode_generation_id=generation_id,
            episode_known_at=opened_known_at,
            issuer_master=issuer_master,
            # Resolved at call time from the canonical owner reader module so a
            # controlled local fixture transport can bind the same lawful seam;
            # production resolves to the unchanged native owner functions.
            find_event_id=_owner_reader.find_current_event_id_for_company,
            read_revisions=_owner_reader.read_event_source_revisions,
        )
        validate_intelligence_vector(vector)
    except (IntelligenceVectorContractError, EpisodeContractError) as exc:
        raise _Refusal("D5_OWNER_CONTRACT_REFUSAL") from exc
    # The adapter read is complete: the one real owner read and its canonical
    # validation have both returned.  Only now is the completion clock taken,
    # and only against the exact issuer bytes and B1 snapshot head that fed
    # the read — state that moved underneath the read refuses the whole read.
    read_completed_at = _read_completed_at()
    _assert_issuer_master_unchanged(repo_root, issuer_master_sha256)
    _assert_snapshot_head_unchanged(snapshot, generation_id)
    refusals = _owner_refusals(vector)
    if refusals:
        return _unavailable_result(refusals)
    family = vector["evidence_families"][0]
    known_clock = family["point_in_time"]["known_at"]
    if known_clock["state"] != "ASSERTED" or _parse_instant(known_clock["value"]) is None:
        _refuse("OWNER_MISSING_DECISION_CLOCK")
    if _parse_instant(known_clock["value"]) > read_completed_at:
        _refuse("OWNER_EVIDENCE_CLOCK_FUTURE")
    reasons = sorted({*_PARTIAL_BASE_REASONS, *extra_reasons})
    evidence = _evidence_input(
        episode=episode, market_session=market_session,
        candidate_source_event_id=key, candidate_source_receipt=receipt,
        relation=relation, opened_known_at=opened_known_at,
        vector=vector, generation_id=generation_id,
        issuer_master_sha256=issuer_master_sha256,
        read_completed_at=read_completed_at, reasons=reasons,
    )
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "owner_ref": OWNER_REF,
        "state": STATE_PARTIAL,
        "evidence_input": evidence,
        "reasons": reasons,
    }
    result["source_receipt"] = _receipt_of(result)
    return result


def _unavailable_result(reasons: Sequence[str]) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "owner_ref": OWNER_REF,
        "state": STATE_UNAVAILABLE,
        "evidence_input": None,
        "reasons": sorted(set(reasons)),
    }
    result["source_receipt"] = _receipt_of(result)
    return result


def read_native_daily_brief_evidence(
    repo_root: object,
    *,
    snapshot: object,
    candidate_source_event_id: object,
    candidate_source_receipt: object,
) -> dict[str, object]:
    """Read one native DailyBrief factual evidence result for one B1 binding.

    Strictly native read path: the snapshot must be a real
    ``CandidateEpisodeStoreSnapshot`` whose exact content is revalidated against
    its own on-disk generation before any fact is used; the caller's source
    key/receipt must match one unretracted native candidate relation; identity
    is resolved only through the canonical issuer master read from the fixed
    reference parquet bytes; and the unchanged Earnings D5 owner is called with
    the genuine episode, generation, and the original OPENED ``known_at``.
    Read-only: no store write, no ledger mutation, no owner-clock renewal.
    Every failure returns a typed UNAVAILABLE envelope with evidence_input None;
    every success is PARTIAL at best.
    """
    try:
        return _read(
            repo_root,
            snapshot=snapshot,
            candidate_source_event_id=candidate_source_event_id,
            candidate_source_receipt=candidate_source_receipt,
        )
    except _Refusal as refusal:
        return _unavailable_result([refusal.reason])


def _reject_forbidden_keys(value: object, *, path: str) -> None:
    try:
        _daily_brief_reject_forbidden(value, path=path)
    except DailyBriefContractError as exc:
        raise DailyBriefEvidenceContractError(str(exc)) from exc


def _require_closed_keys(value: object, expected: frozenset[str], *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DailyBriefEvidenceContractError(f"{name} must be an object")
    keys = set(value)
    if keys != set(expected):
        raise DailyBriefEvidenceContractError(
            f"{name} closed keys mismatch: missing={sorted(set(expected) - keys)!r}, "
            f"extra={sorted(keys - set(expected))!r}"
        )
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(ch) < 32 for ch in value):
        raise DailyBriefEvidenceContractError(f"{name} must be non-empty text")
    return value


def _require_instant(value: object, name: str) -> datetime:
    parsed = _parse_instant(value)
    if parsed is None:
        raise DailyBriefEvidenceContractError(f"{name} must be an RFC3339 UTC Z instant")
    return parsed


def _require_receipt(value: object, name: str, pattern: re.Pattern[str] = _SHA256_RECEIPT_RE) -> str:
    text = _require_text(value, name)
    if not pattern.fullmatch(text):
        raise DailyBriefEvidenceContractError(f"{name} is not a canonical receipt")
    return text


def _require_sorted_ids(value: object, name: str, prefix: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item.startswith(prefix) for item in value)
        or value != sorted(set(value))
    ):
        raise DailyBriefEvidenceContractError(f"{name} must be sorted unique {prefix} ids")
    return value


def _validate_native_identity(value: object, name: str) -> None:
    text = _require_text(value, name)
    if not text.startswith("SEC:"):
        raise DailyBriefEvidenceContractError(f"{name} must be a canonical Data OS security id")
    try:
        kind, listing = parse_id(text)
        canonical = canonical_security_id(listing)
    except IdentityError as exc:
        raise DailyBriefEvidenceContractError(f"{name} must be a canonical Data OS security id") from exc
    if kind != "security" or canonical != text:
        raise DailyBriefEvidenceContractError(f"{name} must be a canonical Data OS security id")


def _validate_summary(value: object) -> None:
    summary = _require_closed_keys(value, _SUMMARY_KEYS, name="summary")
    if summary["evidence_family_id"] != EARNINGS_FAMILY_ID:
        raise DailyBriefEvidenceContractError("summary evidence family mismatch")
    if summary["decision_admissibility"] != "ADMISSIBLE":
        raise DailyBriefEvidenceContractError("summary decision admissibility mismatch")
    _require_text(summary["owner_coverage_state"], "summary.owner_coverage_state")
    _require_text(summary["owner_coverage_basis"], "summary.owner_coverage_basis")
    _require_sorted_ids(summary["source_ref_ids"], "summary.source_ref_ids", "src:")
    _require_sorted_ids(summary["evidence_root_ids"], "summary.evidence_root_ids", "er:")
    if not isinstance(summary["owner_warnings"], list) or any(
        not isinstance(item, str) for item in summary["owner_warnings"]
    ) or summary["owner_warnings"] != sorted(set(summary["owner_warnings"])):
        raise DailyBriefEvidenceContractError("summary.owner_warnings must be sorted unique strings")
    supported = summary["supported"]
    absent = summary["absent"]
    if not isinstance(supported, list) or not isinstance(absent, list):
        raise DailyBriefEvidenceContractError("summary observations must be lists")
    for row in supported:
        item = _require_closed_keys(
            row,
            _SUPPORTED_REVENUE_KEYS if "value_usd" in row else _SUPPORTED_KEYS,
            name="summary.supported row",
        )
        if item["value_state"] not in {"PRESENT", "MEASURED_NEUTRAL"} or item["value"] is None:
            raise DailyBriefEvidenceContractError("supported observation value_state invalid")
        if not item["source_ref_ids"] or not item["evidence_root_ids"]:
            raise DailyBriefEvidenceContractError("supported observation requires lineage refs")
        _require_sorted_ids(item["source_ref_ids"], "supported.source_ref_ids", "src:")
        _require_sorted_ids(item["evidence_root_ids"], "supported.evidence_root_ids", "er:")
        _require_text(item["observation_ref"], "supported.observation_ref")
        _require_text(item["correction_lineage_state"], "supported.correction_lineage_state")
        if item.get("value_usd") is not None and not isinstance(item["value_usd"], (int, float)):
            raise DailyBriefEvidenceContractError("supported value_usd must be numeric")
    for row in absent:
        item = _require_closed_keys(row, _ABSENT_KEYS, name="summary.absent row")
        if item["value_state"] != "ABSENT" or not isinstance(item["absence_reasons"], list):
            raise DailyBriefEvidenceContractError("absent observation shape invalid")
        if not item["absence_reasons"] or any(
            not isinstance(reason, str) or not reason for reason in item["absence_reasons"]
        ):
            raise DailyBriefEvidenceContractError("absent observation reasons invalid")
        _require_text(item["observation_ref"], "absent.observation_ref")


def _validate_provenance(value: object, evidence: Mapping[str, object]) -> None:
    provenance = _require_closed_keys(value, _PROVENANCE_KEYS, name="provenance")
    if not _EPISODE_ID_RE.fullmatch(str(evidence["episode_id"])):
        raise DailyBriefEvidenceContractError("episode_id is not a canonical B1 episode id")
    _require_receipt(provenance["candidate_relation_event_id"], "provenance.candidate_relation_event_id", re.compile(r"^pee:[0-9a-f]{64}$"))
    if provenance["candidate_relation_event_type"] not in {"OPENED", "OBSERVED"}:
        raise DailyBriefEvidenceContractError("provenance relation event type invalid")
    _require_instant(provenance["candidate_relation_known_at"], "provenance.candidate_relation_known_at")
    key_match = _CANDIDATE_SOURCE_KEY_RE.fullmatch(
        _require_text(provenance["candidate_source_event_id"], "provenance.candidate_source_event_id")
    )
    if key_match is None or not key_match.group(2):
        raise DailyBriefEvidenceContractError("provenance candidate source key malformed")
    if provenance["source_tuple_market_session"] != evidence["market_session"]:
        raise DailyBriefEvidenceContractError("provenance source tuple session disagrees with binding")
    _require_receipt(provenance["candidate_source_receipt"], "provenance.candidate_source_receipt")
    _require_receipt(
        provenance["chosen_revision_generation_id"],
        "provenance.chosen_revision_generation_id",
        _WORKSPACE_GENERATION_RE,
    )
    receipt = _require_closed_keys(
        provenance["chosen_workspace_receipt"], frozenset({"bytes", "sha256"}),
        name="provenance.chosen_workspace_receipt",
    )
    _require_receipt(receipt["sha256"], "chosen_workspace_receipt.sha256", _HEX64_RE)
    if type(receipt["bytes"]) is not int or receipt["bytes"] <= 0:
        raise DailyBriefEvidenceContractError("chosen_workspace_receipt.bytes invalid")
    if not _EARNINGS_COMPANY_ID_RE.fullmatch(str(provenance["earnings_company_id"])):
        raise DailyBriefEvidenceContractError("provenance earnings company id invalid")
    episode_opened_at = _require_instant(provenance["episode_opened_at"], "provenance.episode_opened_at")
    _require_text(provenance["episode_opened_session"], "provenance.episode_opened_session")
    opened_known_at = _require_instant(
        provenance["episode_original_opened_known_at"],
        "provenance.episode_original_opened_known_at",
    )
    if opened_known_at > episode_opened_at:
        # The original B1 OPENED known_at anchors the decision cut and can
        # never postdate it; the cut itself is never restamped later.
        raise DailyBriefEvidenceContractError("original opened known_at postdates the episode cut")
    if provenance["identity_state"] != "RESOLVED":
        raise DailyBriefEvidenceContractError("evidence input requires a resolved native identity")
    _require_receipt(provenance["issuer_master_sha256"], "provenance.issuer_master_sha256")
    _require_sorted_ids(provenance["decision_version_ref_ids"], "provenance.decision_version_ref_ids", "src:")
    _require_sorted_ids(provenance["later_correction_ref_ids"], "provenance.later_correction_ref_ids", "src:")
    _require_sorted_ids(provenance["later_revision_receipt_ids"], "provenance.later_revision_receipt_ids", "lrr:")
    _require_text(provenance["later_revision_state"], "provenance.later_revision_state")
    _require_text(provenance["owner_adapter_set_version"], "provenance.owner_adapter_set_version")
    if provenance["owner_assembly_assembled_at"] is not None:
        raise DailyBriefEvidenceContractError("owner assembly receipt must remain untouched (assembled_at None)")
    _require_text(provenance["owner_correction_current_state"], "provenance.owner_correction_current_state")
    if provenance["owner_event_discovery_scope"] != "CURRENT_GENERATION_ONLY":
        raise DailyBriefEvidenceContractError("owner event discovery scope must stay current-generation only")
    if provenance["owner_historical_event_set_reconstruction"] is not False:
        raise DailyBriefEvidenceContractError("historical event set reconstruction must stay false")
    _require_text(provenance["owner_identity_resolution_scope"], "provenance.owner_identity_resolution_scope")
    _require_receipt(provenance["owner_lane_assessment_id"], "provenance.owner_lane_assessment_id", re.compile(r"^ola:[0-9a-f]{64}$"))
    if not isinstance(provenance["owner_lanes"], list) or not provenance["owner_lanes"]:
        raise DailyBriefEvidenceContractError("provenance owner lanes must be a non-empty list")
    for lane in provenance["owner_lanes"]:
        item = _require_closed_keys(lane, _LANE_KEYS, name="provenance.owner_lanes row")
        _require_receipt(item["owner_lane_receipt_id"], "owner_lane_receipt_id", re.compile(r"^olr:[0-9a-f]{64}$"))
        _require_text(item["lane"], "owner lane")
        _require_text(item["candidate_state"], "owner lane candidate_state")
        _require_text(item["disposition"], "owner lane disposition")
    _require_text(provenance["owner_point_in_time_basis"], "provenance.owner_point_in_time_basis")
    _require_receipt(provenance["owner_projection_id"], "provenance.owner_projection_id", re.compile(r"^piv:[0-9a-f]{64}$"))
    _require_receipt(provenance["owner_family_projection_id"], "provenance.owner_family_projection_id", re.compile(r"^pif:[0-9a-f]{64}$"))
    _require_text(provenance["owner_source_reader"], "provenance.owner_source_reader")
    _require_text(provenance["owner_revision_visibility_scope"], "provenance.owner_revision_visibility_scope")
    _require_text(provenance["revision_chain_bound_disclosure"], "provenance.revision_chain_bound_disclosure")
    summary = evidence["summary"]
    if not isinstance(provenance["owner_source_receipts"], list):
        raise DailyBriefEvidenceContractError("provenance owner source receipts must be a list")
    if not provenance["owner_source_receipts"] and (
        summary["supported"] or summary["source_ref_ids"]
    ):
        # Projected lineage must always carry its captured owner document
        # receipts; an empty list is truthful only for an admissible owner
        # packet that projected no allowlisted lane at all.
        raise DailyBriefEvidenceContractError("provenance owner source receipts must be retained")
    for row in provenance["owner_source_receipts"]:
        item = _require_closed_keys(row, _OWNER_SOURCE_RECEIPT_KEYS, name="provenance.owner_source_receipts row")
        _require_receipt(item["source_ref_id"], "owner_source_receipts.source_ref_id", re.compile(r"^src:[0-9a-f]{64}$"))
        _require_text(item["object_id"], "owner_source_receipts.object_id")
        if row["content_hash"] is not None:
            _require_receipt(row["content_hash"], "owner_source_receipts.content_hash", _HEX64_RE)
    _require_receipt(provenance["owner_subject_event_id"], "provenance.owner_subject_event_id", _EVENT_ID_RE)
    if provenance["owner_vector_errors"] != []:
        raise DailyBriefEvidenceContractError("a partial evidence input cannot carry owner vector errors")


def validate_daily_brief_evidence_input(payload: object) -> None:
    """Validate the closed owner-issued ``prophet.daily_brief_evidence_input/v1``."""
    _reject_forbidden_keys(payload, path="evidence_input")
    evidence = _require_closed_keys(payload, _EVIDENCE_KEYS, name="evidence_input")
    if evidence["schema"] != EVIDENCE_INPUT_SCHEMA or evidence["owner_ref"] != OWNER_REF:
        raise DailyBriefEvidenceContractError("evidence input schema or owner_ref mismatch")
    if evidence["state"] != STATE_PARTIAL:
        raise DailyBriefEvidenceContractError("evidence input state is PARTIAL at best in v1")
    if evidence["method"] != EVIDENCE_METHOD:
        raise DailyBriefEvidenceContractError("evidence input method mismatch")
    if evidence["fact_asof_basis"] != _OBSERVED_AT_BASIS:
        raise DailyBriefEvidenceContractError("fact asof must be derived from the owner observed clock")
    _validate_native_identity(evidence["security_id"], "security_id")
    _require_text(evidence["episode_id"], "episode_id")
    _require_receipt(evidence["candidate_generation_id"], "candidate_generation_id", _PEG_RE)
    session = _require_text(evidence["market_session"], "market_session")
    if not _SESSION_RE.fullmatch(session):
        raise DailyBriefEvidenceContractError("market_session must be a YYYY-MM-DD session date")
    try:
        date.fromisoformat(session)
    except ValueError as exc:
        raise DailyBriefEvidenceContractError("market_session must be a YYYY-MM-DD session date") from exc
    asof = _require_instant(evidence["asof"], "asof")
    read_completed_at = _require_instant(evidence["read_completed_at"], "read_completed_at")
    if asof > read_completed_at:
        raise DailyBriefEvidenceContractError("fact asof may never postdate the adapter read clock")
    _validate_summary(evidence["summary"])
    coverage = _require_closed_keys(evidence["coverage"], _COVERAGE_KEYS, name="coverage")
    _require_text(coverage["state"], "coverage.state")
    _require_text(coverage["basis"], "coverage.basis")
    if (
        not isinstance(coverage["notes"], list)
        or any(not isinstance(note, str) or not note for note in coverage["notes"])
        or coverage["notes"] != sorted(set(coverage["notes"]))
    ):
        raise DailyBriefEvidenceContractError("coverage notes must be sorted unique strings")
    _validate_provenance(evidence["provenance"], evidence)
    if evidence["source_receipt"] != _receipt_of(evidence):
        raise DailyBriefEvidenceContractError("evidence input source_receipt does not cover the closed envelope")


def validate_daily_brief_evidence_result(payload: object) -> None:
    """Validate the typed result envelope and its pair coherence with the input."""
    _reject_forbidden_keys(payload, path="evidence_result")
    result = _require_closed_keys(payload, _RESULT_KEYS, name="evidence_result")
    if result["schema"] != RESULT_SCHEMA or result["owner_ref"] != OWNER_REF:
        raise DailyBriefEvidenceContractError("evidence result schema or owner_ref mismatch")
    state = result["state"]
    if state not in _PRODUCIBLE_RESULT_STATES:
        if state in _RESULT_STATES:
            raise DailyBriefEvidenceContractError(
                "AVAILABLE results require versioned cross-session proof and are unreachable in v1"
            )
        raise DailyBriefEvidenceContractError("evidence result state invalid")
    reasons = result["reasons"]
    if (
        not isinstance(reasons, list)
        or not reasons
        or any(not isinstance(reason, str) or reason not in REASON_VOCABULARY for reason in reasons)
        or reasons != sorted(set(reasons))
    ):
        raise DailyBriefEvidenceContractError("evidence result reasons must be sorted unique vocabulary ids")
    if state == STATE_UNAVAILABLE:
        if result["evidence_input"] is not None:
            raise DailyBriefEvidenceContractError("an unavailable result carries no evidence input")
        if not [reason for reason in reasons if reason not in _PARTIAL_BASE_REASONS]:
            raise DailyBriefEvidenceContractError("an unavailable result needs a specific typed cause")
    else:
        if not _PARTIAL_BASE_REASONS.issubset(set(reasons)):
            raise DailyBriefEvidenceContractError("a partial result must retain the standing scope reasons")
        evidence = result["evidence_input"]
        if not isinstance(evidence, Mapping):
            raise DailyBriefEvidenceContractError("a partial result carries its evidence input")
        validate_daily_brief_evidence_input(evidence)
    if result["source_receipt"] != _receipt_of(result):
        raise DailyBriefEvidenceContractError("evidence result source_receipt does not cover the closed envelope")
