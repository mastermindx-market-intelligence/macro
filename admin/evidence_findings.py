"""Read recorded owner disagreements for A1 without running their detector.

Only the existing display-only confluence artifact is read. Exact T4 paths may
associate its context with canonical engines; association never changes evidence
bands. Native numerical receipts are request-scoped and rights-projected. Their
references-only history manifests cannot be reconstructed into proof here.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

ARTIFACT_REL = Path("data/neuralweb/confluence_graph.json")
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024


def _text(value: Any, limit: int = 2048) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError("invalid owner scalar")
    return value


def _relative(value: Any) -> str:
    value = _text(value, 512)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("not a repository-relative artifact")
    return path.as_posix()


def _generation(path: Path) -> tuple[int, ...] | None:
    try:
        s = path.lstat()
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
    except OSError:
        return None


def _base() -> dict:
    return {"status": "unavailable", "records": None, "gaps": None,
            "rejected_records": None, "unbound_records": None,
            "display_only": True, "affects_evidence_status": False,
            "current_source_qualification": "unavailable",
            "source": {"path": ARTIFACT_REL.as_posix(), "as_of": None, "sha256": None},
            "numeric_attribution": {
                "status": "unavailable", "reason": "no_request_scoped_subscriber_receipt",
                "scope": "this_evidence_view", "owner_contract": "brain.native_fact_receipt.v1",
                "reference_manifest_is_proof": False}}


def load_findings(root: Path, canonical_outputs: Iterable[Mapping[str, Any]]) -> dict:
    """Bounded file read; the caller supplies only current canonical T4 outputs.

    Missing/bad/changed/oversized reports have no known record count. A valid empty
    report has zero records. Rejected individual records make the result partial,
    with an explicit count, rather than silently becoming evidence of absence.
    """
    result = _base()
    path = Path(root) / ARTIFACT_REL
    before = _generation(path)
    if before is None:
        return {**result, "reason": "owner_artifact_unavailable"}
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return {**result, "reason": "owner_artifact_not_regular"}
        # Nonblocking/no-follow protects the open itself from an intervening FIFO
        # or symlink replacement; the descriptor must still be a regular file.
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                return {**result, "reason": "owner_artifact_not_regular"}
            opened = info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
            if opened != before:
                return {**result, "reason": "changed_during_read"}
            raw = stream.read(MAX_ARTIFACT_BYTES + 1)
        if len(raw) > MAX_ARTIFACT_BYTES:
            return {**result, "reason": "artifact_exceeds_read_budget"}
        document = json.loads(raw)
        if before != _generation(path):
            return {**result, "reason": "changed_during_read"}
        if (not isinstance(document, dict)
                or document.get("schema") != "neuralweb.confluence_graph.v1"
                or document.get("artifact_id") != "confluence-graph"
                or document.get("produced_by") != "engine/neuralweb/confluence.py"
                or document.get("tier") != "display"
                or document.get("display_only") is not True
                or document.get("is_context_only") is not True
                or not isinstance(document.get("contradiction_records"), list)
                or not isinstance(document.get("gaps"), list)):
            raise ValueError("incompatible owner contract")
        as_of = _text(document.get("asof"), 96)
        produced_at = _text(document.get("produced_at"), 96)
        gaps = [_text(gap, 4096) for gap in document["gaps"]]
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        return {**result, "reason": "invalid_owner_artifact"}

    owners: dict[str, set[str]] = {}
    for output in canonical_outputs:
        try:
            rel = _relative(output.get("path"))
            owner = _text(output.get("engine_id"), 512)
            owners.setdefault(rel, set()).add(owner)
        except (ValueError, AttributeError):
            continue

    rows, rejected = [], 0
    for record in document["contradiction_records"]:
        try:
            if (not isinstance(record, dict) or record.get("display_only") is not True
                    or record.get("severity") not in {"note", "tension"}
                    or record.get("kind") not in {"label-lag", "label-tension", "directional-opposition"}):
                raise ValueError("unsupported finding")
            row = {key: _text(record.get(key), 4096 if key == "note" else 128)
                   for key in ("pair_id", "kind", "severity", "as_of", "note")}
            engine_ids: set[str] = set()
            for side in ("a", "b"):
                item = record.get(side)
                if not isinstance(item, dict):
                    raise ValueError("missing source side")
                rel = _relative(item.get("artifact"))
                matches = owners.get(rel, set())
                unique = next(iter(matches)) if len(matches) == 1 else None
                if unique:
                    engine_ids.add(unique)
                row[side] = {"artifact": rel, "reading": _text(item.get("reading")),
                             "engine_id": unique,
                             "binding": "exact_path" if unique else "ambiguous" if matches else "unbound"}
            row.update(display_only=True, engine_ids=sorted(engine_ids))
            rows.append(row)
        except (ValueError, TypeError):
            rejected += 1
    return {**result, "status": "partial" if rejected else "recorded",
            "reason": "unsupported_owner_records" if rejected else None,
            "source": {"path": ARTIFACT_REL.as_posix(), "schema": document["schema"],
                       "as_of": as_of, "produced_at": produced_at,
                       "sha256": hashlib.sha256(raw).hexdigest()},
            "records": rows, "gaps": gaps, "rejected_records": rejected,
            "unbound_records": sum(not row["engine_ids"] for row in rows)}


def for_engine(findings: Mapping[str, Any], engine_id: str) -> dict:
    """A detail projection of the same recorded report, with unbound gaps retained."""
    rows = findings.get("records")
    return {**findings, "global_unbound_records": findings.get("unbound_records"),
            "records": [row for row in rows if engine_id in row["engine_ids"]]
            if isinstance(rows, list) else None}
