"""SNI-local DRAFT contract for reference-twin records.

This module is an R1-gated DRAFT. It CONSUMES owner-supplied values
(payload, owner_key, owner_digest, clocks) and does not fork or
re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.
Identity ids are caller-supplied opaque strings owned by Stock Identity /
Data OS; this module never mints, derives or guesses HK/US issuer or
security identifiers from a ticker, name, code or CIK. Unknown identity
stays UNRESOLVED / null at the caller.

Authority flags are const false. Nothing here feeds a ranker, gate, sizer,
signal, escalation or trade path. Setting any authority flag true is refused.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
from dataclasses import dataclass, field

AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


class TwinRefused(Exception):
    """Refusal with a stable machine-readable .code."""

    def __init__(self, code, detail=""):
        self.code = code
        super().__init__(detail or code)


def canonical_json(obj):
    """UTF-8 JSON with sorted keys, compact separators, trailing newline."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_utc(value):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(text)


def _copy_json(obj):
    return json.loads(json.dumps(obj))


def _authority_flags_all_false():
    return {name: False for name in AUTHORITY_FLAG_NAMES}


def _refuse_if_authority_true(flags):
    if not flags:
        return
    for name in AUTHORITY_FLAG_NAMES:
        if flags.get(name) is True:
            raise TwinRefused("AUTHORITY_FLAG_TRUE", "%s must stay false" % name)


def _read_lines(path):
    p = pathlib.Path(path)
    if not p.is_file():
        return []
    lines = []
    with p.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line[:-1] if line.endswith("\n") else line
            if raw.strip():
                lines.append(raw)
    return lines


def _read_all(path):
    out = []
    for raw in _read_lines(path):
        out.append(json.loads(raw))
    return out


class OwnerRegistry(dict):
    """owner_key -> {"allowed": bool}. Keys are caller-supplied, never minted here."""

    def admit(self, owner_key, payload, owner_digest):
        if owner_key not in self:
            raise TwinRefused("UNKNOWN_OWNER", "owner_key is not in the registry")
        meta = self[owner_key] or {}
        if not meta.get("allowed"):
            raise TwinRefused("OWNER_NOT_ALLOWED", "owner_key is registered but not allowed")
        computed = sha256_text(canonical_json(payload))
        if computed != owner_digest:
            raise TwinRefused("DIGEST_MISMATCH", "owner_digest does not match payload")
        return True


def make_record(
    *,
    twin_key,
    owner_key,
    payload,
    owner_digest,
    clocks,
    registry,
    prev=None,
    correction_reason=None,
):
    """Admit an owner payload and mint an SNI-local record dict.

    record_id is a hash of SNI envelope fields. prev_hash and row_hash are
    filled by TwinStore. generation 1 has supersedes None; a correction is a
    NEW record (A16) and requires correction_reason.
    """
    registry.admit(owner_key, payload, owner_digest)
    if any(name in payload for name in AUTHORITY_FLAG_NAMES):
        raise TwinRefused(
            "AUTHORITY_KEY_IN_PAYLOAD",
            "payload must not contain an authority flag key",
        )

    clocks_copy = _copy_json(clocks)
    payload_copy = _copy_json(payload)
    period = clocks_copy["economic_period"]
    start = period["start"]
    end = period.get("end")
    if end is not None and end < start:
        raise TwinRefused("PERIOD_ORDER", "economic_period.end must be >= start")

    known = _parse_utc(clocks_copy["owner_known_at_utc"])
    published = _parse_utc(clocks_copy["sni_published_at_utc"])
    if known > published:
        raise TwinRefused(
            "CLOCK_ORDER",
            "sni_published_at_utc cannot precede owner_known_at_utc",
        )

    if prev is not None:
        if not correction_reason:
            raise TwinRefused(
                "CORRECTION_REASON_REQUIRED",
                "a correction (prev given) requires correction_reason",
            )
        generation = int(prev["generation"]) + 1
        supersedes = prev["record_id"]
        correction = {
            "reason": correction_reason,
            "corrected_at_utc": clocks_copy["sni_published_at_utc"],
        }
    else:
        generation = 1
        supersedes = None
        correction = {"reason": None, "corrected_at_utc": None}

    authority_flags = _authority_flags_all_false()
    _refuse_if_authority_true(authority_flags)

    id_body = {
        "clocks": clocks_copy,
        "generation": generation,
        "owner_digest": owner_digest,
        "owner_key": owner_key,
        "supersedes": supersedes,
        "twin_key": twin_key,
    }
    record_id = sha256_text(canonical_json(id_body))
    return {
        "record_id": record_id,
        "twin_key": twin_key,
        "generation": generation,
        "supersedes": supersedes,
        "owner_key": owner_key,
        "owner_digest": owner_digest,
        "payload": payload_copy,
        "clocks": clocks_copy,
        "correction": correction,
        "authority_flags": authority_flags,
        "prev_hash": None,
    }


@dataclass
class TwinStore:
    """Append-only JSONL store. Hash-chained. EFFECT_UNKNOWN-safe acks (A17)."""

    path: object
    _after_write_hook: object = field(default=None, repr=False)

    def __post_init__(self):
        self.path = pathlib.Path(self.path)

    def _last_row_hash(self):
        recs = _read_all(self.path)
        if not recs:
            return None
        return recs[-1].get("row_hash")

    def append(self, record):
        rec = _copy_json(record)
        _refuse_if_authority_true(rec.get("authority_flags") or {})
        rec["prev_hash"] = self._last_row_hash()
        body = {key: value for key, value in rec.items() if key != "row_hash"}
        rec["row_hash"] = sha256_text(canonical_json(body))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(rec))
            handle.flush()
            os.fsync(handle.fileno())
        if self._after_write_hook is not None:
            self._after_write_hook()
        return rec["row_hash"]

    def write_with_ack(self, record):
        """ACKED with row_hash, or EFFECT_UNKNOWN without retry (A17)."""
        try:
            return ("ACKED", self.append(record))
        except TwinRefused:
            raise
        except Exception:
            return ("EFFECT_UNKNOWN", None)

    def reconcile(self, record_id):
        """Same-carrier re-read. Never a blind retry (A17)."""
        for rec in _read_all(self.path):
            if rec.get("record_id") == record_id:
                return "PRESENT"
        return "ABSENT"


def verify_chain(path):
    """Return violation strings: hash, prev_hash, generation gap, immutability."""
    violations = []
    raw_lines = _read_lines(path)
    first_bytes = {}
    last_row_hash = None
    last_by_twin = {}
    for raw in raw_lines:
        rec = json.loads(raw)
        rid = rec.get("record_id")
        body = {key: value for key, value in rec.items() if key != "row_hash"}
        expected_hash = sha256_text(canonical_json(body))
        if rec.get("row_hash") != expected_hash:
            violations.append("hash mismatch at record_id=%s" % rid)
        expected_prev = last_row_hash
        if rec.get("prev_hash") != expected_prev:
            violations.append("prev_hash mismatch at record_id=%s" % rid)
        last_row_hash = rec.get("row_hash")

        if rid in first_bytes and first_bytes[rid] != raw:
            violations.append(
                "immutability: record_id=%s bytes differ from first appearance" % rid
            )
        else:
            first_bytes.setdefault(rid, raw)

        twin_key = rec.get("twin_key")
        generation = rec.get("generation")
        supersedes = rec.get("supersedes")
        if twin_key in last_by_twin:
            last_gen, last_id = last_by_twin[twin_key]
            if generation != last_gen + 1 or supersedes != last_id:
                violations.append(
                    "generation gap for twin_key=%s generation=%s" % (twin_key, generation)
                )
        else:
            if generation != 1 or supersedes is not None:
                violations.append(
                    "generation gap for twin_key=%s generation=%s" % (twin_key, generation)
                )
        last_by_twin[twin_key] = (generation, rid)
    return violations


def latest(path, twin_key):
    chosen = None
    for rec in _read_all(path):
        if rec.get("twin_key") != twin_key:
            continue
        if chosen is None or rec["generation"] > chosen["generation"]:
            chosen = rec
    return chosen


def view_as_of(path, twin_key, as_of_utc):
    """Highest-generation record with sni_published_at_utc <= as_of_utc (A07)."""
    cutoff = _parse_utc(as_of_utc)
    chosen = None
    for rec in _read_all(path):
        if rec.get("twin_key") != twin_key:
            continue
        published = _parse_utc(rec["clocks"]["sni_published_at_utc"])
        if published <= cutoff:
            if chosen is None or rec["generation"] > chosen["generation"]:
                chosen = rec
    return chosen


def history(path, twin_key):
    return [rec for rec in _read_all(path) if rec.get("twin_key") == twin_key]
