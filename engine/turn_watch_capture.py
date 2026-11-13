"""Forward-only producer clocks for the existing Turn Watch artifact pair.

These metadata receipts never enter the public artifact, B1 input digest or event
identity. A retained producer capture is neither first source availability nor
repository publication, customer visibility, or executable entry availability.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from engine.us_candidate_episode import canonical_json

SCHEMA = "prophet.turn_watch_producer_capture/v1"
STAGE = "ARTIFACT_PAIR_WRITTEN"
CLOCK_BASIS = "FIRST_RETAINED_PRODUCER_CAPTURE"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _binding(raw: bytes, doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise ValueError("invalid Turn Watch source envelope")
    digest = doc.get("content_sha256")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ValueError("invalid Turn Watch source receipt")
    expected = sha256(canonical_json({k: v for k, v in doc.items()
                                     if k != "content_sha256"}).encode()).hexdigest()
    if digest != expected or doc.get("schema") != "prophet.candidate_episode_input.turn_watch/v1":
        raise ValueError("invalid Turn Watch source envelope")
    return {"source_session": doc["data_session"], "source_receipt": "sha256:" + digest,
            "source_file_receipt": "sha256:" + sha256(raw).hexdigest(),
            "source_artifact_receipt": doc["source_artifact_sha256"]}


def capture_path(source_path: Path, digest: str) -> Path:
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ValueError("invalid Turn Watch capture key")
    # Direct *.json children remain exclusively session inputs for the B1 selector.
    return Path(source_path).parent / "producer_captures" / (digest + ".json")


def _validate(raw: bytes, binding: dict, known_at: str) -> dict:
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("invalid producer capture envelope")
    digest = sha256(canonical_json({k: v for k, v in record.items()
                                   if k != "content_sha256"}).encode()).hexdigest()
    stamp = record.get("producer_captured_at")
    if (record.get("schema") != SCHEMA or record.get("stage") != STAGE
            or record.get("clock_basis") != CLOCK_BASIS
            or record.get("content_sha256") != digest
            or any(record.get(k) != v for k, v in binding.items())
            or not isinstance(stamp, str) or not _UTC.fullmatch(stamp)
            or not isinstance(known_at, str) or not _UTC.fullmatch(known_at)):
        raise ValueError("producer capture does not match this exact artifact pair")
    captured = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if captured < datetime.fromisoformat(known_at.replace("Z", "+00:00")):
        raise ValueError("producer capture precedes the logical source close")
    execution = record.get("execution")
    if (not isinstance(execution, dict)
            or set(execution) != {"github_run_id", "github_run_attempt", "github_job"}
            or any(v is not None and (not isinstance(v, str) or not v or len(v) > 128)
                   for v in execution.values())):
        raise ValueError("invalid producer execution context")
    return record


def record_producer_capture(source_path: Path, public_path: Path) -> Path:
    """Record the first retained completed readback; never overwrite an old claim."""
    source_raw, public_raw = Path(source_path).read_bytes(), Path(public_path).read_bytes()
    doc = json.loads(source_raw)
    binding = _binding(source_raw, doc)
    if binding["source_artifact_receipt"] != "sha256:" + sha256(public_raw).hexdigest():
        raise ValueError("public/private Turn Watch pair changed before capture")
    out = capture_path(source_path, doc["content_sha256"])
    if out.exists():
        _validate(out.read_bytes(), binding, doc["known_at"])
        return out
    record = {"schema": SCHEMA, "stage": STAGE, "clock_basis": CLOCK_BASIS,
              **binding, "producer_captured_at": _now(),
              "execution": {k.lower(): os.environ.get(k) for k in
                            ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB")}}
    record["content_sha256"] = sha256(canonical_json(record).encode()).hexdigest()
    payload = (canonical_json(record) + "\n").encode()
    _validate(payload, binding, doc["known_at"])
    out.parent.mkdir(parents=True, exist_ok=True)
    # Publish complete bytes without replacing a concurrent first capture. A failed
    # write leaves no final receipt; only this call's temporary file is removed.
    with tempfile.NamedTemporaryFile(dir=out.parent, prefix=".capture-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            try:
                os.link(temporary, out)
            except FileExistsError:
                _validate(out.read_bytes(), binding, doc["known_at"])
        finally:
            temporary.unlink(missing_ok=True)
    return out


def producer_capture_unavailable(reason="PRODUCER_RECEIPT_NOT_FOUND") -> dict:
    return {"state": "UNAVAILABLE", "reason": reason, "producer_captured_at": None,
            "clock_basis": CLOCK_BASIS, "stage": STAGE, "receipt": None, "execution": None}


def load_producer_capture(source_path: Path, source_raw: bytes, source_doc: dict) -> dict:
    """Read metadata only after the caller verifies the exact public partition."""
    try:
        binding = _binding(source_raw, source_doc)
        raw = capture_path(source_path, source_doc["content_sha256"]).read_bytes()
    except FileNotFoundError:
        return producer_capture_unavailable()
    except (OSError, ValueError, TypeError, KeyError):
        return producer_capture_unavailable("PRODUCER_RECEIPT_UNREADABLE")
    try:
        record = _validate(raw, binding, source_doc["known_at"])
    except (ValueError, TypeError, KeyError):
        return producer_capture_unavailable("PRODUCER_RECEIPT_INVALID")
    return {"state": "RECORDED", "reason": None,
            "producer_captured_at": record["producer_captured_at"],
            "clock_basis": CLOCK_BASIS, "stage": STAGE,
            "receipt": "sha256:" + sha256(raw).hexdigest(), "execution": record["execution"]}
