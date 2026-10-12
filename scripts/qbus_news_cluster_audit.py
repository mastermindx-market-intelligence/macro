#!/usr/bin/env python3
"""Read-only audit of qbus news clustering outcomes.

One JSON document on stdout. No writes, no network, and no process-environment reads.
Opens a sqlite store with ``file:<path>?mode=ro`` and reads only
``news_clusters``, ``news_cluster_members``, and ``news_state_projection``.

``--jsonl`` reads a fixture instead. Each line is one story object:

    {"story_id":"benzinga:1","title":"...","observed_at":"2026-10-04T20:00:00+00:00",
     "subject_ids":["sec-NVDA"],"event_family":"company","cluster_id":"ev2_optional"}

``story_id`` may be omitted when ``source`` and ``source_item_id`` are present.
If every row carries ``cluster_id``, those assignments are audited as stored.
If none do, assignments are computed in memory with ``cluster_candidates`` in
file order and are not persisted. A mix of the two shapes is rejected.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.qbus_news_cluster import (  # noqa: E402
    ClusterCandidate,
    ClusterItem,
    ClusterPolicy,
    _RATING_VERB_RE,
    _actions,
    _analyst_actor,
    _negated,
    _numbers,
    _outcome_polarity,
    _periods,
    _rating_target_classes,
    _seconds,
    _terminated,
    cluster_candidates,
)
from engine.qkernel import title_similarity  # noqa: E402

_NEAR_MISS_LIMIT = 50
_SCHEMA = "qbus.news_cluster_audit.v1"


class AuditError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class _Story:
    story_id: str
    title: str
    observed_at: datetime | None
    subject_ids: tuple[str, ...]
    event_family: str
    cluster_id: str
    source: str
    source_item_id: str


def _parse_time(raw: object) -> datetime:
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AuditError("qbus_news_cluster_audit:timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuditError("qbus_news_cluster_audit:naive_timestamp")
    return parsed


def _subjects(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise AuditError("qbus_news_cluster_audit:subject_ids")
    return tuple(raw)


def _title_reject_reason(left: str, right: str) -> str | None:
    left_numbers, right_numbers = _numbers(left), _numbers(right)
    if left_numbers and right_numbers and left_numbers != right_numbers:
        return "number_mismatch"
    left_periods, right_periods = _periods(left), _periods(right)
    if left_periods and right_periods and left_periods != right_periods:
        return "period_mismatch"
    if _negated(left) != _negated(right):
        return "negation_mismatch"
    left_actions, right_actions = _actions(left), _actions(right)
    if left_actions and right_actions and not (left_actions & right_actions):
        return "action_mismatch"
    actor_left, actor_right = _analyst_actor(left), _analyst_actor(right)
    rating_left = bool(_RATING_VERB_RE.search(left))
    rating_right = bool(_RATING_VERB_RE.search(right))
    if (
        rating_left
        and rating_right
        and actor_left
        and actor_right
        and actor_left != actor_right
    ):
        return "analyst_actor_mismatch"
    outcome_left, outcome_right = _outcome_polarity(left), _outcome_polarity(right)
    if outcome_left and outcome_right and not (outcome_left & outcome_right):
        return "outcome_polarity_mismatch"
    target_left, target_right = _rating_target_classes(left), _rating_target_classes(right)
    if target_left and target_right and not (target_left & target_right):
        return "rating_target_mismatch"
    if _terminated(left) != _terminated(right):
        return "termination_mismatch"
    return None


def _pair_reason(left: _Story, right: _Story, policy: ClusterPolicy) -> str:
    if not (set(left.subject_ids) & set(right.subject_ids)):
        return "no_shared_subject"
    if (
        left.event_family
        and right.event_family
        and left.event_family != right.event_family
    ):
        return "event_family_mismatch"
    rejected = _title_reject_reason(left.title, right.title)
    if rejected:
        return rejected
    if title_similarity(left.title, right.title) < policy.title_threshold:
        return "below_title_threshold"
    return "passed_gates_unjoined"


def _histogram(sizes: dict[str, int]) -> dict[str, int]:
    counts: dict[int, int] = {}
    for size in sizes.values():
        counts[size] = counts.get(size, 0) + 1
    return {str(size): counts[size] for size in sorted(counts)}


def _report(stories: list[_Story], sizes: dict[str, int], policy: ClusterPolicy) -> dict:
    near: list[dict] = []
    mismatched: list[dict] = []
    for index, left in enumerate(stories):
        for right in stories[index + 1 :]:
            ordered = (left, right) if left.story_id <= right.story_id else (right, left)
            a_story, b_story = ordered
            if left.cluster_id == right.cluster_id:
                a_numbers, b_numbers = _numbers(a_story.title), _numbers(b_story.title)
                if a_numbers and b_numbers and a_numbers != b_numbers:
                    mismatched.append(
                        {
                            "cluster_id": left.cluster_id,
                            "a_story": a_story.story_id,
                            "b_story": b_story.story_id,
                            "a_numbers": sorted(a_numbers),
                            "b_numbers": sorted(b_numbers),
                        }
                    )
                continue
            if left.observed_at is None or right.observed_at is None:
                continue
            if _seconds(left.observed_at, right.observed_at) > policy.window_seconds:
                continue
            near.append(
                {
                    "a_story": a_story.story_id,
                    "b_story": b_story.story_id,
                    "similarity": title_similarity(a_story.title, b_story.title),
                    "reason": _pair_reason(a_story, b_story, policy),
                }
            )
    near.sort(key=lambda row: (-row["similarity"], row["a_story"], row["b_story"]))
    del near[_NEAR_MISS_LIMIT:]
    mismatched.sort(
        key=lambda row: (row["cluster_id"], row["a_story"], row["b_story"])
    )
    return {
        "schema": _SCHEMA,
        "clusters": len(sizes),
        "multi_member_clusters": sum(1 for size in sizes.values() if size > 1),
        "size_histogram": _histogram(sizes),
        "near_misses": near,
        "joined_with_number_mismatch": mismatched,
        "policy": {
            "title_threshold": policy.title_threshold,
            "window_seconds": policy.window_seconds,
            "max_candidates": policy.max_candidates,
        },
    }


def _open_ro(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise AuditError("qbus_news_cluster_audit:not_a_file")
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise AuditError("qbus_news_cluster_audit:sqlite_error") from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def audit_store(path: Path, policy: ClusterPolicy | None = None) -> dict:
    policy = policy or ClusterPolicy()
    connection = _open_ro(Path(path))
    try:
        clusters = connection.execute(
            """
            SELECT cluster_id, anchor_story_id, anchor_title,
                   anchor_observed_at, subject_ids_json, event_family
            FROM news_clusters
            """
        ).fetchall()
        members = connection.execute(
            """
            SELECT source, source_item_id, cluster_id, story_id
            FROM news_cluster_members
            """
        ).fetchall()
        projections = connection.execute(
            """
            SELECT source, source_item_id, title, received_at
            FROM news_state_projection
            """
        ).fetchall()
    except sqlite3.Error as exc:
        raise AuditError("qbus_news_cluster_audit:sqlite_error") from exc
    finally:
        connection.close()

    by_cluster = {str(row["cluster_id"]): row for row in clusters}
    by_projection = {
        (str(row["source"]), str(row["source_item_id"])): row for row in projections
    }
    sizes = {cluster_id: 0 for cluster_id in by_cluster}
    stories: list[_Story] = []
    for member in members:
        cluster_id = str(member["cluster_id"])
        sizes[cluster_id] = sizes.get(cluster_id, 0) + 1
        cluster = by_cluster.get(cluster_id)
        projection = by_projection.get(
            (str(member["source"]), str(member["source_item_id"]))
        )
        story_id = str(member["story_id"])
        title = ""
        observed: datetime | None = None
        if projection is not None:
            title = str(projection["title"])
            observed = _parse_time(projection["received_at"])
        if cluster is not None and story_id == str(cluster["anchor_story_id"]):
            if not title:
                title = str(cluster["anchor_title"])
            if observed is None:
                observed = _parse_time(cluster["anchor_observed_at"])
        subject_ids: tuple[str, ...] = ()
        event_family = ""
        if cluster is not None:
            try:
                parsed_subjects = json.loads(str(cluster["subject_ids_json"]))
            except json.JSONDecodeError as exc:
                raise AuditError("qbus_news_cluster_audit:subject_ids") from exc
            subject_ids = _subjects(parsed_subjects)
            event_family = str(cluster["event_family"])
        stories.append(
            _Story(
                story_id=story_id,
                title=title,
                observed_at=observed,
                subject_ids=subject_ids,
                event_family=event_family,
                cluster_id=cluster_id,
                source=str(member["source"]),
                source_item_id=str(member["source_item_id"]),
            )
        )
    return _report(stories, sizes, policy)


def _split_story_id(story_id: str) -> tuple[str, str]:
    source, sep, source_item_id = story_id.partition(":")
    if not sep or not source or not source_item_id:
        raise AuditError("qbus_news_cluster_audit:story_id")
    return source, source_item_id


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise AuditError("qbus_news_cluster_audit:not_a_file")
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditError(
                f"qbus_news_cluster_audit:jsonl_invalid:{line_number}"
            ) from exc
        if not isinstance(payload, dict):
            raise AuditError(f"qbus_news_cluster_audit:jsonl_invalid:{line_number}")
        rows.append(payload)
    return rows


def _stories_from_jsonl(rows: list[dict]) -> tuple[list[_Story], bool]:
    stories: list[_Story] = []
    labeled_flags: list[bool] = []
    for row in rows:
        source = str(row["source"]) if row.get("source") else ""
        source_item_id = str(row["source_item_id"]) if row.get("source_item_id") else ""
        story_id = str(row["story_id"]) if row.get("story_id") else ""
        if story_id and source and source_item_id:
            if story_id != f"{source}:{source_item_id}":
                raise AuditError("qbus_news_cluster_audit:story_id_mismatch")
        elif story_id:
            source, source_item_id = _split_story_id(story_id)
        elif source and source_item_id:
            story_id = f"{source}:{source_item_id}"
        else:
            raise AuditError("qbus_news_cluster_audit:story_id")
        if "title" not in row or not isinstance(row["title"], str):
            raise AuditError("qbus_news_cluster_audit:title")
        if "observed_at" not in row:
            raise AuditError("qbus_news_cluster_audit:timestamp")
        cluster_id = row.get("cluster_id")
        labeled = isinstance(cluster_id, str) and cluster_id != ""
        labeled_flags.append(labeled)
        stories.append(
            _Story(
                story_id=story_id,
                title=row["title"],
                observed_at=_parse_time(row["observed_at"]),
                subject_ids=_subjects(row.get("subject_ids")),
                event_family=str(row.get("event_family") or ""),
                cluster_id=cluster_id if labeled else "",
                source=source,
                source_item_id=source_item_id,
            )
        )
    if not stories:
        return stories, False
    if any(labeled_flags) and not all(labeled_flags):
        raise AuditError("qbus_news_cluster_audit:mixed_cluster_ids")
    return stories, all(labeled_flags)


def _assign_clusters(stories: list[_Story], policy: ClusterPolicy) -> None:
    candidates: list[ClusterCandidate] = []
    seen: dict[str, str] = {}
    for story in stories:
        prior = seen.get(story.story_id)
        if prior is not None:
            story.cluster_id = prior
            continue
        if story.observed_at is None:
            raise AuditError("qbus_news_cluster_audit:timestamp")
        item = ClusterItem(
            source=story.source,
            source_item_id=story.source_item_id,
            title=story.title,
            observed_at=story.observed_at,
            subject_ids=story.subject_ids,
            event_family=story.event_family,
        )
        decision = cluster_candidates(item, candidates, policy=policy)
        story.cluster_id = decision.cluster_id
        seen[story.story_id] = decision.cluster_id
        if decision.action == "new":
            candidates.append(
                ClusterCandidate(
                    cluster_id=decision.cluster_id,
                    anchor_story_id=item.story_id,
                    anchor_title=item.title,
                    anchor_observed_at=item.observed_at,
                    subject_ids=item.subject_ids,
                    event_family=item.event_family,
                )
            )


def audit_jsonl(path: Path, policy: ClusterPolicy | None = None) -> dict:
    policy = policy or ClusterPolicy()
    stories, labeled = _stories_from_jsonl(_load_jsonl(Path(path)))
    if stories and not labeled:
        _assign_clusters(stories, policy)
    sizes: dict[str, int] = {}
    for story in stories:
        sizes[story.cluster_id] = sizes.get(story.cluster_id, 0) + 1
    return _report(stories, sizes, policy)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of qbus news cluster outcomes."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--store", type=Path)
    source.add_argument("--jsonl", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.store is not None:
            report = audit_store(args.store)
        else:
            report = audit_jsonl(args.jsonl)
    except AuditError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    json.dump(report, sys.stdout, indent=2, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
