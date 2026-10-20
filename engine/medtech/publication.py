"""Atomic, bounded MedTech product publication; the API reads only this surface."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from engine.medtech.events import EVENT_ID_RE, MedTechError, PATHWAYS, instant, source_date, source_record_url

MAX_PUBLIC_BYTES = 32 * 1024 * 1024
_GENERATION = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_KEYS = {
    "schema", "event_id", "submission_id", "parent_submission_id", "pathway",
    "pathway_label", "device", "applicant", "decision", "received_on", "supplement",
    "source", "company_link", "commercial_evidence", "next_milestone",
    "first_observed_at", "last_observed_at", "last_changed_at", "revision_id", "history",
}


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise MedTechError("PUBLIC_SCHEMA_INVALID")


def _optional_text(value, maximum=4000):
    if value is not None and (not isinstance(value, str) or len(value) > maximum):
        raise MedTechError("PUBLIC_SCHEMA_INVALID")


def validate_snapshot(payload: dict) -> None:
    _keys(payload, {"schema", "generated_at", "sources", "events", "capabilities"})
    if payload["schema"] != "medtech.watchdesk/v1":
        raise MedTechError("PUBLIC_SCHEMA_INVALID")
    generated = instant(payload["generated_at"])
    if not isinstance(payload["events"], list) or len(payload["events"]) > 100000:
        raise MedTechError("PUBLIC_SCHEMA_INVALID")
    identities = set()
    for event in payload["events"]:
        _keys(event, _EVENT_KEYS)
        event_id = event["event_id"]
        if (not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id)
                or event_id in identities or event["schema"] != "medtech.event/v1"
                or event["pathway"] not in PATHWAYS
                or event["pathway_label"] != PATHWAYS[event["pathway"]]):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        identities.add(event_id)
        for key in ("submission_id", "parent_submission_id", "received_on"):
            _optional_text(event[key], 32)
        for key, fields in (
            ("device", {"name", "generic_name", "product_code"}),
            ("applicant", {"name"}),
            ("decision", {"code", "status", "label", "date", "date_precision", "source_description"}),
            ("supplement", {"number", "type", "reason"}),
        ):
            _keys(event[key], fields)
            for value in event[key].values():
                _optional_text(value)
        _keys(event["source"], {"publisher", "dataset", "record_id", "url", "source_published_at"})
        source = event["source"]
        dataset, number, supplement = source["dataset"], event["submission_id"], event["supplement"]["number"]
        if dataset not in {"510k", "pma"} or not isinstance(number, str):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        expected_id = f"fda-{dataset}-{number}" + (f"-{supplement}" if supplement else "")
        source_id = number + (supplement or "")
        expected_url = source_record_url(dataset, number, supplement)
        if (event_id != expected_id or source["record_id"] != source_id
                or source["publisher"] != "FDA" or source["url"] != expected_url
                or source["source_published_at"] is not None):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        if (event["company_link"] != {"status": "not_joined"}
                or event["commercial_evidence"] != {"status": "not_assessed"}
                or event["next_milestone"] is not None):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        first, changed, seen = (instant(event[k]) for k in
                              ("first_observed_at", "last_changed_at", "last_observed_at"))
        if not first <= changed <= seen <= generated:
            raise MedTechError("PUBLIC_CLOCK_INVALID")
        if not isinstance(event["revision_id"], str) or not _GENERATION.fullmatch(event["revision_id"]):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        history = event["history"]
        if not isinstance(history, list) or not history:
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        previous = None
        for index, revision in enumerate(history):
            _keys(revision, {"revision_id", "observed_at", "kind", "changes", "decision_date", "device_name"})
            _optional_text(revision["device_name"])
            if source_date(revision["decision_date"], observed_at=revision["observed_at"]) != revision["decision_date"]:
                raise MedTechError("PUBLIC_SCHEMA_INVALID")
            current = instant(revision["observed_at"])
            if (current > changed or (previous is not None and current <= previous)
                    or not isinstance(revision["revision_id"], str)
                    or not _GENERATION.fullmatch(revision["revision_id"])
                    or (revision["kind"] != "first_observed" if index == 0 else
                        revision["kind"] not in {"source_record_changed", "normalization_changed",
                                                 "source_and_normalization_changed"})
                    or not isinstance(revision["changes"], list)):
                raise MedTechError("PUBLIC_SCHEMA_INVALID")
            if index == 0 and revision["changes"]:
                raise MedTechError("PUBLIC_SCHEMA_INVALID")
            allowed_paths = {
                "/decision/code", "/decision/status", "/decision/label", "/decision/date",
                "/decision/date_precision", "/decision/source_description", "/received_on",
                "/device/name", "/device/generic_name", "/device/product_code", "/applicant/name",
                "/supplement/number", "/supplement/type", "/supplement/reason", "/pathway",
            }
            for change in revision["changes"]:
                _keys(change, {"op", "json_path", "before_value", "after_value",
                               "before_state", "after_state", "change_family"})
                path = change["json_path"]
                if (not isinstance(path, str) or path not in allowed_paths
                        or change["op"] != "replace"
                        or change["before_state"] != "present" or change["after_state"] != "present"
                        or change["change_family"] != path.split("/")[1]
                        or change["before_value"] == change["after_value"]):
                    raise MedTechError("PUBLIC_SCHEMA_INVALID")
                _optional_text(change["before_value"])
                _optional_text(change["after_value"])
            previous = current
        if (history[0]["observed_at"] != event["first_observed_at"]
                or history[-1]["observed_at"] != event["last_changed_at"]
                or history[-1]["revision_id"] != event["revision_id"]
                or history[-1]["decision_date"] != event["decision"]["date"]
                or history[-1]["device_name"] != event["device"]["name"]):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
    if not isinstance(payload["sources"], list) or len(payload["sources"]) > 2:
        raise MedTechError("PUBLIC_SCHEMA_INVALID")
    seen_sources = set()
    for source in payload["sources"]:
        _keys(source, {"dataset", "last_checked_at", "dataset_updated_at", "cadence",
                       "timely_alert_source", "coverage"})
        if (source["dataset"] not in {"510k", "pma"} or source["dataset"] in seen_sources
                or instant(source["last_checked_at"]) > generated
                or source["cadence"] != "monthly" or source["timely_alert_source"] is not False):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        seen_sources.add(source["dataset"])
        if source_date(source["dataset_updated_at"], observed_at=source["last_checked_at"]) != source["dataset_updated_at"]:
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
        coverage = source["coverage"]
        _keys(coverage, {"kind", "start", "end", "records", "complete_for_query"})
        if (coverage["kind"] != "decision_date_range" or coverage["complete_for_query"] is not True
                or type(coverage["records"]) is not int or not 0 <= coverage["records"] <= 10000
                or source_date(coverage["start"], observed_at=source["last_checked_at"]) != coverage["start"]
                or source_date(coverage["end"], observed_at=source["last_checked_at"]) != coverage["end"]
                or not coverage["start"] or not coverage["end"] or coverage["start"] > coverage["end"]):
            raise MedTechError("PUBLIC_SCHEMA_INVALID")
    if any(event["source"]["dataset"] not in seen_sources for event in payload["events"]):
        raise MedTechError("PUBLIC_SCHEMA_INVALID")
    if (not isinstance(payload["capabilities"], dict)
            or any(type(value) is not bool for value in payload["capabilities"].values())):
        raise MedTechError("PUBLIC_SCHEMA_INVALID")
    if payload["capabilities"] != {
        "decision_history": True, "prospective_calendar": False,
        "company_economic_rights": False, "coverage_decisions": False,
        "safety_alerts": False, "delivered_notifications": False,
    }:
        raise MedTechError("PUBLIC_SCHEMA_INVALID")


def _read(path: Path, limit: int) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise MedTechError("PUBLIC_FILE_INVALID")
            result = handle.read(limit + 1)
        if len(result) > limit:
            raise MedTechError("PUBLIC_FILE_INVALID")
        return result
    except OSError:
        raise MedTechError("PUBLICATION_UNAVAILABLE") from None


def _atomic(path: Path, raw: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".medtech-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o640)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if _read(Path(temporary), len(raw)) != raw:
            raise MedTechError("PUBLIC_WRITE_UNVERIFIED")
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_snapshot(root: Path | str) -> tuple[dict, str]:
    root = Path(root)
    if root.is_symlink() or (root / "generations").is_symlink():
        raise MedTechError("PUBLIC_PATH_INVALID")
    try:
        pointer = json.loads(_read(root / "current.json", 1024))
        _keys(pointer, {"schema", "generation", "generated_at"})
        generation = pointer["generation"]
        if pointer["schema"] != "medtech.pointer/v1" or not _GENERATION.fullmatch(generation):
            raise MedTechError("PUBLIC_POINTER_INVALID")
        raw = _read(root / "generations" / (generation + ".json"), MAX_PUBLIC_BYTES)
        if sha256(raw).hexdigest() != generation:
            raise MedTechError("PUBLIC_DIGEST_MISMATCH")
        payload = json.loads(raw)
        validate_snapshot(payload)
        if pointer["generated_at"] != payload["generated_at"]:
            raise MedTechError("PUBLIC_CLOCK_INVALID")
        return payload, generation
    except (ValueError, TypeError, KeyError, UnicodeDecodeError):
        raise MedTechError("PUBLICATION_INVALID") from None


def publish_snapshot(root: Path | str, payload: dict) -> str:
    import fcntl
    from engine.sector_intelligence import canonical_json_bytes

    validate_snapshot(payload)
    raw = canonical_json_bytes(payload)
    if len(raw) > MAX_PUBLIC_BYTES:
        raise MedTechError("PUBLICATION_TOO_LARGE")
    generation, root = sha256(raw).hexdigest(), Path(root)
    if root.is_symlink() or (root / "generations").is_symlink():
        raise MedTechError("PUBLIC_PATH_INVALID")
    (root / "generations").mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(root / ".publish.lock",
                      os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(lock_fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (root / "current.json").exists():
            current, current_id = read_snapshot(root)
            if instant(current["generated_at"]) > instant(payload["generated_at"]):
                raise MedTechError("PUBLICATION_CLOCK_REGRESSION")
            if current_id == generation:
                return generation
            if instant(current["generated_at"]) == instant(payload["generated_at"]):
                raise MedTechError("PUBLICATION_CLOCK_CONFLICT")
        target = root / "generations" / (generation + ".json")
        if target.exists():
            if _read(target, MAX_PUBLIC_BYTES) != raw:
                raise MedTechError("PUBLIC_GENERATION_CONFLICT")
        else:
            _atomic(target, raw)
        _atomic(root / "current.json", canonical_json_bytes({
            "schema": "medtech.pointer/v1", "generation": generation,
            "generated_at": payload["generated_at"],
        }))
    return generation


def record_attempt(root: Path | str, *, observed_at: str, status: str, code: str | None = None):
    from engine.sector_intelligence import canonical_json_bytes

    if status not in {"succeeded", "failed"} or (code is not None and not re.fullmatch(r"[A-Z0-9_]{1,80}", code)):
        raise MedTechError("ATTEMPT_INVALID")
    instant(observed_at)
    root = Path(root)
    if root.is_symlink():
        raise MedTechError("PUBLIC_PATH_INVALID")
    root.mkdir(parents=True, exist_ok=True)
    _atomic(root / "last_attempt.json", canonical_json_bytes({
        "observed_at": observed_at, "status": status, "code": code,
    }))


def read_attempt(root: Path | str) -> dict | None:
    try:
        attempt = json.loads(_read(Path(root) / "last_attempt.json", 1024))
        _keys(attempt, {"observed_at", "status", "code"})
        instant(attempt["observed_at"])
        if attempt["status"] not in {"succeeded", "failed"}:
            return None
        if attempt["code"] is not None and not re.fullmatch(r"[A-Z0-9_]{1,80}", attempt["code"]):
            return None
        return attempt
    except (MedTechError, ValueError, TypeError, KeyError):
        return None
