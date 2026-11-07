"""Pure PTSE relation resolver from one incumbent candidate row to canonical B1."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

class PTSECandidateRelationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class CandidateEpisodeRelation:
    source_event_id: str
    candidate_generation_id: str
    episode_id: str
    security_id: str
    company_id: str
    identity_epoch: str

def _fail(code: str) -> None:
    raise PTSECandidateRelationError(code)

def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        _fail(code)
    return value

def candidate_source_event_id(candidate_row: Mapping[str, object]) -> str:
    if not isinstance(candidate_row, Mapping):
        _fail("CANDIDATE_ROW_REQUIRED")
    stamp = _text(candidate_row.get("stamp_date"), "CANDIDATE_STAMP_REQUIRED")
    ticker = _text(candidate_row.get("ticker"), "CANDIDATE_TICKER_REQUIRED")
    definition = _text(candidate_row.get("board_definition"), "CANDIDATE_BOARD_DEFINITION_REQUIRED")
    return f"candidate:{stamp}:{ticker}:{definition}"

def resolve_candidate_episode_relation(candidate_row: Mapping[str, object], snapshot: object, *, expected_episode_id: str | None = None) -> CandidateEpisodeRelation:
    source_id = candidate_source_event_id(candidate_row)
    generation_id = _text(getattr(snapshot, "generation_id", None), "B1_GENERATION_ID_REQUIRED")
    generation = getattr(snapshot, "generation", None)
    episodes = getattr(generation, "episodes", None)
    if not isinstance(episodes, tuple):
        _fail("B1_VALIDATED_EPISODES_REQUIRED")
    matches: list[Mapping[str, object]] = []
    for raw in episodes:
        if not isinstance(raw, Mapping):
            _fail("B1_EPISODE_ROW_INVALID")
        source_ids = raw.get("source_event_ids")
        if isinstance(source_ids, str) or not isinstance(source_ids, Sequence):
            _fail("B1_SOURCE_EVENT_IDS_INVALID")
        if source_id in source_ids:
            matches.append(raw)
    if not matches:
        _fail("CANDIDATE_B1_RELATION_UNAVAILABLE")
    if len(matches) != 1:
        _fail("CANDIDATE_B1_RELATION_AMBIGUOUS")
    episode = matches[0]
    episode_id = _text(episode.get("episode_id"), "B1_EPISODE_ID_REQUIRED")
    security_id = _text(episode.get("security_id"), "B1_SECURITY_ID_REQUIRED")
    company_id = _text(episode.get("company_id"), "B1_COMPANY_ID_REQUIRED")
    identity_epoch = _text(episode.get("identity_epoch"), "B1_IDENTITY_EPOCH_REQUIRED")
    if expected_episode_id is not None:
        expected = _text(expected_episode_id, "EXPECTED_EPISODE_ID_INVALID")
        if episode_id != expected:
            _fail("CANDIDATE_PTSE_EPISODE_MISMATCH")
    return CandidateEpisodeRelation(source_id, generation_id, episode_id, security_id, company_id, identity_epoch)

__all__ = ["CandidateEpisodeRelation", "PTSECandidateRelationError", "candidate_source_event_id", "resolve_candidate_episode_relation"]
