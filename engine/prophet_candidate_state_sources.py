"""Read-only owner-fact adapters for the Prophet V4 B3 candidate-state projection.

These adapters do not recreate B1 identity, TURN WATCH trigger logic, Radar event
minting, B4 Availability, or any trading authority. They snapshot already-owned
facts into deterministic, content-receipted indexes for the pure B3 projector.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import MappingProxyType
import json
import math
import re
from typing import Any

_TURN_WATCH_SCHEMA = "prophet.candidate_episode_input.turn_watch/v1"
_RADAR_EVENT_SCHEMA = "mastermind.entry_event.v1"
_GENERATION_RE = re.compile(r"^peg:[0-9a-f]{64}$")


class CandidateStateSourceError(ValueError):
    """Raised when source facts cannot be indexed without inventing truth."""


@dataclass(frozen=True)
class SourceFactIndex:
    source: str
    facts_by_event_id: Mapping[str, Mapping[str, object]]
    receipt: Mapping[str, object]
    degraded_reasons: tuple[str, ...]


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
        raise CandidateStateSourceError(
            f"source fact is not canonical JSON: {exc}"
        ) from exc


def _plain(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _plain(item())
        except Exception:  # pragma: no cover - foreign scalar stays fail-closed
            pass
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat) and not isinstance(value, str):
        try:
            return str(isoformat())
        except Exception:  # pragma: no cover
            pass
    return value


def _text(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < 32 for character in value)
    ):
        raise CandidateStateSourceError(
            f"{field} must be non-empty control-free text"
        )
    return value


def _freeze_index(
    source: str,
    rows: Mapping[str, Mapping[str, object]],
    receipt: Mapping[str, object],
    degraded: Sequence[str] = (),
) -> SourceFactIndex:
    frozen_rows = MappingProxyType(
        {
            key: MappingProxyType(dict(rows[key]))
            for key in sorted(rows)
        }
    )
    return SourceFactIndex(
        source=source,
        facts_by_event_id=frozen_rows,
        receipt=MappingProxyType(dict(receipt)),
        degraded_reasons=tuple(sorted(set(degraded))),
    )


def _insert_unique(
    target: dict[str, Mapping[str, object]],
    key: str,
    value: Mapping[str, object],
    *,
    source: str,
) -> None:
    prior = target.get(key)
    if prior is None:
        target[key] = dict(value)
        return
    if _canonical_json(prior) != _canonical_json(value):
        raise CandidateStateSourceError(
            f"{source} conflicting duplicate source event id {key!r}"
        )


def index_turn_watch_events(
    events: Iterable[Mapping[str, object]],
    *,
    candidate_generation_id: str,
) -> SourceFactIndex:
    """Index exact TURN WATCH OPENED relations from the validated B1 ledger."""

    if not _GENERATION_RE.fullmatch(str(candidate_generation_id or "")):
        raise CandidateStateSourceError(
            "candidate generation id is invalid"
        )

    facts: dict[str, Mapping[str, object]] = {}
    scanned = 0
    for raw in events:
        if not isinstance(raw, Mapping):
            raise CandidateStateSourceError("B1 event must be an object")
        scanned += 1
        if (
            raw.get("event_type") != "OPENED"
            or raw.get("source_system") != "turn_watch"
            or raw.get("source_schema") != _TURN_WATCH_SCHEMA
        ):
            continue

        source_event_id = _text(
            raw.get("source_event_id"), "turn_watch source_event_id"
        )
        source_receipt = _text(
            raw.get("source_receipt"), "turn_watch source_receipt"
        )
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", source_receipt):
            raise CandidateStateSourceError(
                "turn_watch source receipt is invalid"
            )

        fact = {
            "episode_id": _text(raw.get("episode_id"), "turn_watch episode_id"),
            "source_system": "turn_watch",
            "source_schema": _TURN_WATCH_SCHEMA,
            "source_event_id": source_event_id,
            "source_receipt": source_receipt,
            "occurred_at": _text(
                raw.get("occurred_at"), "turn_watch occurred_at"
            ),
            "known_at": _text(raw.get("known_at"), "turn_watch known_at"),
            "relation_event_id": _text(
                raw.get("event_id"), "turn_watch B1 relation event_id"
            ),
        }
        _insert_unique(
            facts, source_event_id, fact, source="turn_watch"
        )

    receipt = {
        "state": "OK",
        "source": "turn_watch_via_b1",
        "source_schema": _TURN_WATCH_SCHEMA,
        "candidate_generation_id": candidate_generation_id,
        "b1_events_scanned": scanned,
        "facts": len(facts),
        "content_sha256": "sha256:"
        + sha256(
            _canonical_json(
                {key: facts[key] for key in sorted(facts)}
            ).encode("utf-8")
        ).hexdigest(),
    }
    return _freeze_index("turn_watch", facts, receipt)


_RADAR_FIELDS = (
    "episode_address",
    "ticker",
    "detector_id",
    "family",
    "subtype",
    "decision_session",
    "signal_ts",
    "signal_known_ts",
    "observed_at",
    "observed_at_basis",
    "bar_state",
    "final",
    "detector_spec_hash",
    "lobe_enlisted",
    "lobe_ids",
    "state",
    "first_seen_session",
    "spool_path",
)


def index_radar_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    source_receipt: Mapping[str, object],
) -> SourceFactIndex:
    """Index the append-only Radar forward store by exact episode_address."""

    facts: dict[str, Mapping[str, object]] = {}
    count = 0
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise CandidateStateSourceError("Radar row must be an object")
        count += 1
        plain = _plain(dict(raw))
        if not isinstance(plain, Mapping):
            raise CandidateStateSourceError("Radar row normalization failed")
        event_id = _text(
            plain.get("episode_address"), "radar episode_address"
        )
        fact = {field: plain.get(field) for field in _RADAR_FIELDS}
        fact["source_system"] = "entry_radar"
        fact["source_schema"] = _RADAR_EVENT_SCHEMA
        _insert_unique(facts, event_id, fact, source="radar")

    receipt = dict(source_receipt)
    receipt.setdefault("state", "OK")
    receipt["source"] = "entry_radar_forward"
    receipt["source_schema"] = _RADAR_EVENT_SCHEMA
    receipt["rows_scanned"] = count
    receipt["facts"] = len(facts)
    return _freeze_index("entry_radar", facts, receipt)


def load_radar_fact_index(path: Path) -> SourceFactIndex:
    """Read one exact Radar parquet byte snapshot; missing/malformed is typed."""

    source = Path(path)
    try:
        payload = source.read_bytes()
    except FileNotFoundError:
        return _freeze_index(
            "entry_radar",
            {},
            {"state": "MISSING", "path": str(source)},
            ("RADAR_SOURCE_MISSING",),
        )
    except OSError:
        return _freeze_index(
            "entry_radar",
            {},
            {"state": "UNREADABLE", "path": str(source)},
            ("RADAR_SOURCE_UNREADABLE",),
        )

    receipt = {
        "state": "OK",
        "path": str(source),
        "bytes": len(payload),
        "sha256": "sha256:" + sha256(payload).hexdigest(),
    }
    try:
        import pandas as pd  # noqa: PLC0415

        frame = pd.read_parquet(BytesIO(payload))
        rows = frame.to_dict("records")
        return index_radar_rows(rows, source_receipt=receipt)
    except CandidateStateSourceError:
        raise
    except Exception as exc:  # noqa: BLE001 - malformed source is typed, not guessed
        return _freeze_index(
            "entry_radar",
            {},
            {**receipt, "state": "MALFORMED"},
            ("RADAR_SOURCE_MALFORMED", type(exc).__name__),
        )


def emergence_inputs(
    snapshot: object,
    *,
    turn_watch: SourceFactIndex,
    radar: SourceFactIndex,
) -> tuple[dict[str, dict[str, object]], dict[str, tuple[str, ...]]]:
    """Resolve exact B1 source relations into conservative B3 emergence inputs."""

    generation_id = getattr(snapshot, "generation_id", None)
    if not isinstance(generation_id, str) or not _GENERATION_RE.fullmatch(
        generation_id
    ):
        raise CandidateStateSourceError("snapshot generation_id is invalid")

    generation = getattr(snapshot, "generation", None)
    episodes = getattr(generation, "episodes", None)
    if not isinstance(episodes, tuple):
        raise CandidateStateSourceError(
            "snapshot must expose validated tuple episodes"
        )

    tw_generation = turn_watch.receipt.get("candidate_generation_id")
    if tw_generation is not None and tw_generation != generation_id:
        raise CandidateStateSourceError(
            "TURN WATCH facts belong to a different B1 generation"
        )

    tw_by_episode: dict[str, list[Mapping[str, object]]] = {}
    for fact in turn_watch.facts_by_event_id.values():
        episode_id = _text(fact.get("episode_id"), "turn_watch episode_id")
        tw_by_episode.setdefault(episode_id, []).append(fact)

    emergence: dict[str, dict[str, object]] = {}
    degraded: dict[str, tuple[str, ...]] = {}

    for episode in episodes:
        if not isinstance(episode, Mapping):
            raise CandidateStateSourceError("B1 episode must be an object")
        episode_id = _text(episode.get("episode_id"), "episode_id")
        expert_ids = episode.get("expert_events") or []
        if not isinstance(expert_ids, list) or not all(
            isinstance(value, str) and value for value in expert_ids
        ):
            raise CandidateStateSourceError(
                "B1 expert_events must be strings"
            )

        reasons: list[str] = []
        radar_facts: list[Mapping[str, object]] = []
        for expert_id in sorted(set(expert_ids)):
            fact = radar.facts_by_event_id.get(expert_id)
            if fact is None:
                reasons.append(f"RADAR_EVENT_UNRESOLVED:{expert_id}")
            else:
                radar_facts.append(fact)

        if expert_ids and radar.degraded_reasons:
            reasons.extend(radar.degraded_reasons)

        if radar_facts:
            def radar_clock(fact: Mapping[str, object]) -> tuple[str, str]:
                clock = (
                    fact.get("observed_at")
                    or fact.get("signal_known_ts")
                    or fact.get("signal_ts")
                    or ""
                )
                return str(clock), str(fact.get("episode_address") or "")

            selected = max(radar_facts, key=radar_clock)
            family = str(selected.get("family") or "unknown")
            subtype = selected.get("subtype")
            token = family + (f":{subtype}" if subtype else "")
            emergence[episode_id] = {
                "state": "TRIGGERED",
                "reason": None,
                "source_system": "entry_radar",
                "source_token": token,
                "source_ref": _text(
                    selected.get("episode_address"),
                    "radar episode_address",
                ),
            }
        else:
            turn_facts = tw_by_episode.get(episode_id, [])
            if turn_facts:
                selected = max(
                    turn_facts,
                    key=lambda fact: (
                        str(fact.get("known_at") or ""),
                        str(fact.get("source_event_id") or ""),
                    ),
                )
                emergence[episode_id] = {
                    "state": "TRIGGERED",
                    "reason": None,
                    "source_system": "turn_watch",
                    "source_token": "B1_OPENED",
                    "source_ref": _text(
                        selected.get("source_event_id"),
                        "turn_watch source_event_id",
                    ),
                }
            else:
                emergence[episode_id] = {
                    "state": "UNESTIMABLE",
                    "reason": (
                        "SOURCE_RELATION_UNRESOLVED"
                        if reasons
                        else "SOURCE_NOT_SUPPLIED"
                    ),
                    "source_system": None,
                    "source_token": None,
                    "source_ref": None,
                }

        degraded[episode_id] = tuple(sorted(set(reasons)))

    return emergence, degraded
