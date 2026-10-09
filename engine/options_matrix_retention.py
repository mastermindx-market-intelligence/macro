"""Exact-byte retention for the existing EOD matrix publisher and bucket.

This module establishes artifact identity only. It grants neither source-use
rights nor root-to-security identity, and does not make an empty matrix savable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

SCHEMA = "options_structure.matrix/v1"
R2_PREFIX = "options_structure/matrix/"
MAX_MATRIX_BYTES = 16 * 1024 * 1024
_ROOT = re.compile(r"[A-Z0-9](?:[A-Z0-9.-]{0,13}[A-Z0-9])?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SHA = re.compile(r"[0-9a-f]{64}")
_REF = re.compile(r"sha256:([0-9a-f]{64}):bytes:([1-9][0-9]*):session:(unknown|[0-9]{4}-[0-9]{2}-[0-9]{2})")


class HistoricalUnavailable(ValueError):
    """Exact history cannot be established; never substitute the current head."""


class _MissingSnapshot(HistoricalUnavailable):
    pass


def validate_root(root: str) -> str:
    """Use the existing Options producer root grammar without normalization."""
    if not isinstance(root, str) or not _ROOT.fullmatch(root) or ".." in root:
        raise HistoricalUnavailable("invalid canonical producer root")
    return root


def _session(value: object) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise HistoricalUnavailable("invalid source session")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise HistoricalUnavailable("invalid source session") from exc
    return value


def source_session(payload: dict) -> str | None:
    """Missing/null falls back; malformed or contradictory clocks refuse."""
    if not isinstance(payload, dict):
        raise HistoricalUnavailable("matrix is not an object")
    meta = payload.get("_build_meta")
    if meta is not None and not isinstance(meta, dict):
        raise HistoricalUnavailable("invalid build metadata")
    direct = payload.get("session")
    fallback = meta.get("asof_date") if meta is not None else None
    direct = _session(direct) if direct is not None else None
    fallback = _session(fallback) if fallback is not None else None
    if direct is not None and fallback is not None and direct != fallback:
        raise HistoricalUnavailable("contradictory source sessions")
    return direct if direct is not None else fallback


@dataclass(frozen=True)
class SnapshotReference:
    root: str
    sha256: str
    byte_length: int
    session: str | None

    @property
    def version_ref(self) -> str:
        return f"sha256:{self.sha256}:bytes:{self.byte_length}:session:{self.session or 'unknown'}"

    @property
    def key(self) -> str:
        return f"{R2_PREFIX}history/{self.root}/{self.sha256}.json"


def parse_reference(root: str, version_ref: str, fingerprint: str) -> SnapshotReference:
    validate_root(root)
    if not isinstance(version_ref, str) or len(version_ref) > 256:
        raise HistoricalUnavailable("invalid version reference")
    match = _REF.fullmatch(version_ref)
    if match is None or not isinstance(fingerprint, str) or not _SHA.fullmatch(fingerprint):
        raise HistoricalUnavailable("invalid version reference or fingerprint")
    digest, count, session = match.groups()
    if digest != fingerprint:
        raise HistoricalUnavailable("fingerprint mismatch")
    size = int(count)
    if not 0 < size <= min(MAX_MATRIX_BYTES, 2**53 - 1):
        raise HistoricalUnavailable("matrix exceeds byte limit")
    return SnapshotReference(root, digest, size, None if session == "unknown" else _session(session))


def _checked_ref(ref: SnapshotReference) -> None:
    if not isinstance(ref, SnapshotReference) or type(ref.byte_length) is not int:
        raise HistoricalUnavailable("invalid snapshot reference")
    if parse_reference(ref.root, ref.version_ref, ref.sha256) != ref:
        raise HistoricalUnavailable("noncanonical snapshot reference")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HistoricalUnavailable("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise HistoricalUnavailable("nonfinite JSON number")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        _nonfinite(value)
    return result


def _decode(root: str, raw: bytes) -> dict:
    validate_root(root)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MATRIX_BYTES:
        raise HistoricalUnavailable("invalid matrix bytes or byte limit exceeded")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                             parse_constant=_nonfinite, parse_float=_finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HistoricalUnavailable("invalid matrix JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("root") != root:
        raise HistoricalUnavailable("matrix schema or root mismatch")
    source_session(payload)
    return payload


def reference_for_bytes(root: str, raw: bytes) -> SnapshotReference:
    payload = _decode(root, raw)
    return SnapshotReference(root, hashlib.sha256(raw).hexdigest(), len(raw), source_session(payload))


def verify_snapshot(ref: SnapshotReference, raw: bytes) -> dict:
    _checked_ref(ref)
    if not isinstance(raw, bytes) or len(raw) != ref.byte_length:
        raise HistoricalUnavailable("retained byte length mismatch")
    if hashlib.sha256(raw).hexdigest() != ref.sha256:
        raise HistoricalUnavailable("retained digest mismatch")
    payload = _decode(ref.root, raw)
    if source_session(payload) != ref.session:
        raise HistoricalUnavailable("retained source session mismatch")
    return payload


def load_snapshot(s3, bucket: str, ref: SnapshotReference) -> bytes:
    """Read only the exact immutable key, bounding allocation and stream reads."""
    _checked_ref(ref)
    try:
        response = s3.get_object(Bucket=bucket, Key=ref.key)
    except Exception as exc:
        error = getattr(exc, "response", {})
        detail = error.get("Error") if isinstance(error, dict) else None
        code = detail.get("Code") if isinstance(detail, dict) else None
        if code in {"NoSuchKey", "NotFound", "404"}:
            raise _MissingSnapshot("retained matrix missing") from exc
        raise HistoricalUnavailable("retained matrix read failed") from exc
    if not isinstance(response, dict):
        raise HistoricalUnavailable("invalid retained response")
    body = response.get("Body")
    try:
        length = response.get("ContentLength")
        if type(length) is not int or length != ref.byte_length:
            raise HistoricalUnavailable("retained ContentLength mismatch")
        raw = bytearray()
        # Read one byte beyond the declared length: a lying ContentLength cannot
        # hide a suffix. Short reads are not treated as EOF.
        while len(raw) <= length:
            chunk = body.read(min(64 * 1024, length + 1 - len(raw)))
            if not isinstance(chunk, bytes):
                raise HistoricalUnavailable("invalid retained stream")
            if not chunk:
                break
            if len(chunk) > length + 1 - len(raw):
                raise HistoricalUnavailable("retained stream exceeded read bound")
            raw.extend(chunk)
        result = bytes(raw)
        verify_snapshot(ref, result)
        return result
    except HistoricalUnavailable:
        raise
    except Exception as exc:
        raise HistoricalUnavailable("retained matrix stream failed") from exc
    finally:
        if body is not None:
            body.close()


def retain_snapshot(s3, bucket: str, ref: SnapshotReference, raw: bytes) -> None:
    """Create once, then verify bytes; uncertainty never advances a mutable head."""
    verify_snapshot(ref, raw)
    try:
        prior = load_snapshot(s3, bucket, ref)
    except _MissingSnapshot:
        pass
    else:
        if prior != raw:
            raise HistoricalUnavailable("retained byte collision")
        return
    try:
        s3.put_object(Bucket=bucket, Key=ref.key, Body=raw,
                      ContentType="application/json", IfNoneMatch="*")
    except Exception:
        # A timeout or conditional-create race may have committed. Reconcile
        # this same key and exact bytes once; never overwrite or choose a new key.
        pass
    if load_snapshot(s3, bucket, ref) != raw:
        raise HistoricalUnavailable("retained byte collision")


def matrix_coordinate_tokens(ref: SnapshotReference, raw: bytes) -> tuple[tuple[str, str], ...]:
    """Return exact (expiry, strike-decimal) keys from verified source bytes.

    Decimal parsing retains the original JSON numeric value. UI Number values
    cannot be used to reconstruct it. These keys prove neither side availability,
    subject identity nor rights; callers must apply those separate admission gates.
    Empty matrices return no keys and cannot satisfy primary membership.
    """
    verify_snapshot(ref, raw)
    payload = json.loads(raw.decode("utf-8"), parse_float=Decimal, parse_int=Decimal,
                         object_pairs_hook=_unique_object, parse_constant=_nonfinite)
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise HistoricalUnavailable("matrix cells unavailable")
    keys = []
    seen = set()
    for cell in cells:
        if not isinstance(cell, dict):
            raise HistoricalUnavailable("invalid source cell")
        expiry = _session(cell.get("expiry"))
        value = cell.get("strike")
        if not isinstance(value, Decimal) or not value.is_finite() or not 0 < value < 10**12:
            raise HistoricalUnavailable("source strike outside selection domain")
        # Decimal.normalize() applies the ambient precision/Emin and can underflow
        # a tiny nonzero value to zero. Derive scale directly from the exact tuple,
        # then trim the coefficient BEFORE fixed-point rendering. No context math.
        sign, digits, exponent = value.as_tuple()
        end = len(digits)
        while end > 1 and digits[end - 1] == 0:
            end -= 1
        exponent += len(digits) - end
        if exponent < -8 or len(digits[:end]) > 20:
            raise HistoricalUnavailable("source strike outside selection domain")
        canonical = Decimal((sign, digits[:end], exponent))
        strike = format(canonical, "f")
        if "." in strike:
            strike = strike.rstrip("0").rstrip(".")
        if not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{0,7}[1-9])?", strike):
            raise HistoricalUnavailable("source strike outside selection domain")
        key = (expiry, strike)
        if key in seen:
            raise HistoricalUnavailable("ambiguous duplicate source coordinate")
        seen.add(key)
        keys.append(key)
    return tuple(keys)
