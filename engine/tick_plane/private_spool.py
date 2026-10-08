"""Crash-safe, private local T.* spool for the existing TP-1 source owner.

Source-only private data, never a public data product or parallel market-data
store. Quote Q.* payloads are NEVER persisted here; only a bounded in-flight
NBBO ring holds quote updates. No R2 upload, network connection, credential,
scheduler, replay controller or publication authority exists in this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from engine.tick_plane.stream_events import SCHEMA as SOURCE_SCHEMA, _SESSION, _SYMBOL

SPOOL_SCHEMA = "equity.tick_plane.private_part/v0"
MAX_RECORDS = 2000
MAX_PART_BYTES = 4 * 1024 * 1024
_TRADE_FIELDS = frozenset({
    "schema", "ticker", "session", "source", "event_type", "native_sequence",
    "sip_timestamp_ns", "participant_timestamp_ns", "source_timestamp_precision",
    "original_frame_received_ns", "source_receipt_id", "source_frame_sha256",
    "frame_event_index", "source_status", "correction_status",
    "eligible_for_pressure", "conditions_rules_ref", "market_tape",
    "trade_id", "dedup_key", "price", "size_integer_shares",
    "decimal_size_shares", "trade_conditions", "exchange", "trf_id",
    "trf_timestamp_ns", "venue_class", "trade_action",
})


class PrivateSpoolRefusal(ValueError):
    pass


def _private_root(root):
    path = Path(root)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise PrivateSpoolRefusal("pre-existing real absolute private directory required")
    canonical = path.resolve()
    source_repo = Path(__file__).resolve().parents[2]
    if canonical == source_repo or source_repo in canonical.parents:
        raise PrivateSpoolRefusal("refuse any private-source spool inside repository")
    if stat.S_IMODE(canonical.stat().st_mode) & 0o077:
        raise PrivateSpoolRefusal("private spool directory has group/other access")
    return canonical


def _validated_record(record, *, session, ticker):
    if not isinstance(record, dict) or set(record) != _TRADE_FIELDS:
        raise PrivateSpoolRefusal("unrecognized or extra source fields; refuse raw credentials/payloads")
    if (record["schema"] != SOURCE_SCHEMA or record["event_type"] != "T"
            or record["session"] != session or record["ticker"] != ticker):
        raise PrivateSpoolRefusal("only same-session normalized trades may be spooled")
    if record["correction_status"] != "STREAM_PROVISIONAL_UNRECONCILED":
        raise PrivateSpoolRefusal("do not falsely finalize a live-stream trade")
    if not isinstance(record["dedup_key"], str) or not record["dedup_key"]:
        raise PrivateSpoolRefusal("missing native trade identity")
    if (type(record["sip_timestamp_ns"]) is not int or
            type(record["original_frame_received_ns"]) is not int or
            record["original_frame_received_ns"] < record["sip_timestamp_ns"]):
        raise PrivateSpoolRefusal("invalid source event/receipt clocks")
    if not isinstance(record["source_frame_sha256"], str) or len(record["source_frame_sha256"]) != 64:
        raise PrivateSpoolRefusal("missing raw-source digest")
    return dict(record)


def write_private_trade_part(*, root, session, ticker, events):
    """Atomically append a content-addressed immutable part; idempotent by digest.

    The caller owns singleton-writer custody, partition selection and PRIVATE R2
    handling. This module never creates an authority to delete or advertise
    raw trade data. Temp + fsync + atomic rename preserve crash-safe whole parts.
    """
    base = _private_root(root)
    if (not isinstance(session, str) or _SESSION.fullmatch(session) is None or
            not isinstance(ticker, str) or _SYMBOL.fullmatch(ticker) is None):
        raise PrivateSpoolRefusal("invalid session or symbol partition")
    if not isinstance(events, (tuple, list)) or not 1 <= len(events) <= MAX_RECORDS:
        raise PrivateSpoolRefusal("bounded nonempty source part required")
    unique = {}
    for item in events:
        e = _validated_record(item, session=session, ticker=ticker)
        old = unique.get(e["dedup_key"])
        if old is not None and old != e:
            raise PrivateSpoolRefusal("conflicting duplicate native print identity")
        unique[e["dedup_key"]] = e
    records = sorted(unique.values(), key=lambda r: (
        r["sip_timestamp_ns"], r["native_sequence"], r["dedup_key"]))
    payload = b"".join(
        (json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        for x in records
    )
    if len(payload) > MAX_PART_BYTES:
        raise PrivateSpoolRefusal("source part exceeds byte budget")
    digest = hashlib.sha256(payload).hexdigest()
    date_part, session_part = session.split(":")
    output = base / date_part / session_part / ticker
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    for folder in (base / date_part, base / date_part / session_part, output):
        if folder.is_symlink() or stat.S_IMODE(folder.stat().st_mode) & 0o077:
            raise PrivateSpoolRefusal("partition directory is not private")
    target = output / (digest + ".jsonl")
    if target.exists():
        if target.is_symlink() or target.read_bytes() != payload:
            raise PrivateSpoolRefusal("immutable part target differs; no overwrite")
        return {"schema": SPOOL_SCHEMA, "state": "ALREADY_PRESENT",
                "sha256": digest, "n": len(records), "bytes": len(payload),
                "path_private_only": str(target)}
    scratch = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=output, prefix=".pending-",
                                         delete=False) as fh:
            scratch = Path(fh.name)
            os.fchmod(fh.fileno(), 0o600)
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(scratch, target)
        dir_fd = os.open(output, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if scratch is not None and scratch.exists():
            scratch.unlink()
    return {"schema": SPOOL_SCHEMA, "state": "PART_CREATED",
            "sha256": digest, "n": len(records), "bytes": len(payload),
            "path_private_only": str(target)}
