"""One-shot read-only Options Matrix publication observer.


Observes already-published local and authenticated remote snapshot bytes for
the incumbent publisher DEFAULT_ROOTS. This is not a scheduler, repair tool,
publisher, or natural-invocation verifier. Importing this module does not
create a client or read live objects.

natural_invocation_verified is always false. natural_session_count is always
null. Repeated source dates are complete observations of the same session,
not advances. A successful collection is snapshot evidence only.

Optional --identity-vendor thetadata joins SPY only through the existing captured
canonical SEC consumer. It uses the exact verified Matrix bytes and source session.
Publication complete/stable keep their original meaning; identity.scope and
identity.complete report the separate join. An opt-in CLI requires both to succeed.
This does not authenticate capture provenance, prove natural invocation, grant
rights, or enable Save. Local capture is bounded but not an atomic filesystem read.

Optional --selection FILE verifies one retained selection
(options_matrix_selection.v1) against the exact SPY snapshot bytes named by
--selection-target: the current observed head, or the prior observation's
retained snapshot read. It requires --identity-vendor thetadata and its captured
identity inputs, joins only through the existing resolve_option_matrix_selection
consumer, and reports a separate result["selection"] entry. A selected snapshot
that failed, moved, or is unbound yields an unavailable selection and never
substitutes different bytes. This is stored membership and recorded view only:
no metric availability, no source authentication, no rights, no Save, and no
cross-time atomicity between a prior read and the current heads.

Canonical observed-side token-set encoding
(options_structure.matrix_observed_side_token_set/v1):
  1. Tokens come from engine.options_matrix_retention.matrix_observed_side_tokens
     as (expiry, strike, side). expiry is YYYY-MM-DD; strike is the retention
     canonical decimal string; side is the ASCII token call or put.
  2. Each unique token becomes one UTF-8 record:
       expiry + 0x1F + strike + 0x1F + side
  3. Records are sorted as raw UTF-8 bytes (set semantics).
  4. Nonempty sets join records with 0x0A and terminate the last record with
     0x0A. The empty set encodes to the empty byte string.
  5. The digest is lowercase hex SHA-256 of those bytes.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import sys
from pathlib import Path

# File-path execution must select this checkout before any repository import.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

SCHEMA = "options_structure.matrix_observation/v1"
TOKEN_SET_ENCODING = "options_structure.matrix_observed_side_token_set/v1"
_UNIT = "\x1f"

# Must match scripts.build_options_matrix.DEFAULT_ROOTS. CLI verifies at runtime.
DEFAULT_ROOTS = (
    "SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "META", "AMD", "GOOGL",
    "MU", "ARM",
)

_MISSING_CODES = {"NoSuchKey", "NotFound", "404"}
_DENIED_CODES = {"AccessDenied", "403", "Forbidden", "Unauthorized", "AccessForbidden"}
_PRIOR_IDENTITY = ("root", "sha256", "byte_length", "session", "version_ref", "key")

_SELECTION_TARGETS = ("current", "prior")


class ObservationRefused(RuntimeError):
    """Caller contract refused. No production object was written."""


class _ReadIssue(Exception):
    def __init__(self, code, error_code=None, http_status=None):
        super().__init__(code)
        self.code = code
        self.error_code = error_code
        self.http_status = http_status

    def as_dict(self):
        item = {"code": self.code}
        if self.error_code is not None:
            item["error_code"] = self.error_code
        if self.http_status is not None:
            item["http_status"] = self.http_status
        return item


def token_set_digest(tokens) -> str:
    """Return the SHA-256 hex digest of the canonical observed-side token set."""
    records = sorted({
        f"{expiry}{_UNIT}{strike}{_UNIT}{side}".encode("utf-8")
        for expiry, strike, side in tokens
    })
    payload = b"".join(record + b"\n" for record in records)
    return hashlib.sha256(payload).hexdigest()


def _retention(module=None):
    if module is not None:
        return module
    from engine import options_matrix_retention as retention
    return retention


def _classify_s3_error(exc):
    """Map a client exception to missing, denied, or unavailable.

    HTTP 403 / AccessDenied is never treated as absence.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return "unavailable", None, None
    error = response.get("Error")
    code = error.get("Code") if isinstance(error, dict) else None
    if code is not None and not isinstance(code, str):
        code = str(code)
    meta = response.get("ResponseMetadata")
    status = meta.get("HTTPStatusCode") if isinstance(meta, dict) else None
    if type(status) is not int:
        status = None
    if status == 403 or code in _DENIED_CODES:
        return "denied", code, status if status is not None else 403
    if status == 404 or code in _MISSING_CODES:
        return "missing", code, status
    return "unavailable", code, status


def read_local_bytes(path: Path, limit: int) -> bytes:
    """Read a local snapshot, bounding allocation to limit + 1 bytes."""
    path = Path(path)
    try:
        st = path.stat()
    except FileNotFoundError as exc:
        raise _ReadIssue("missing") from exc
    except OSError as exc:
        raise _ReadIssue("unavailable") from exc
    if not path.is_file():
        raise _ReadIssue("unavailable")
    if st.st_size > limit:
        raise _ReadIssue("oversize")
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as exc:
        raise _ReadIssue("unavailable") from exc
    if not 0 < len(raw) <= limit:
        raise _ReadIssue("oversize")
    return raw


def _read_body(response, limit: int) -> bytes:
    if not isinstance(response, dict):
        raise _ReadIssue("unavailable")
    body = response.get("Body")
    try:
        length = response.get("ContentLength")
        if type(length) is int and length > limit:
            raise _ReadIssue("oversize")
        if type(length) is not int or not 0 < length <= limit:
            raise _ReadIssue("unavailable")
        if body is None:
            raise _ReadIssue("unavailable")
        raw = bytearray()
        while len(raw) <= length:
            chunk = body.read(min(64 * 1024, length + 1 - len(raw)))
            if not isinstance(chunk, bytes):
                raise _ReadIssue("unavailable")
            if not chunk:
                break
            if len(chunk) > length + 1 - len(raw):
                raise _ReadIssue("unavailable")
            raw.extend(chunk)
        if len(raw) != length:
            raise _ReadIssue("unavailable")
        return bytes(raw)
    finally:
        if body is not None:
            body.close()


def read_remote_bytes(client, bucket: str, key: str, limit: int) -> bytes:
    """Authenticated bounded GET of one known key. 403 is denied, not missing."""
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except _ReadIssue:
        raise
    except Exception as exc:
        kind, code, status = _classify_s3_error(exc)
        raise _ReadIssue(kind, error_code=code, http_status=status) from None
    try:
        return _read_body(response, limit)
    except _ReadIssue:
        raise
    except Exception:
        raise _ReadIssue("unavailable") from None


def _require_measured(doc: dict) -> None:
    cells = doc.get("cells")
    if not isinstance(cells, list) or not cells:
        raise _ReadIssue("empty_cells")
    spot = doc.get("spot")
    if isinstance(spot, bool) or not isinstance(spot, (int, float)):
        raise _ReadIssue("invalid_spot")
    if not math.isfinite(spot) or not spot > 0:
        raise _ReadIssue("invalid_spot")


def _source_clocks(ref, doc: dict) -> dict:
    meta = doc.get("_build_meta")
    meta = meta if isinstance(meta, dict) else {}
    dates = meta.get("source_dates")
    dates = dates if isinstance(dates, dict) else {}

    def _clock(value):
        return value if isinstance(value, str) else None

    return {
        "session": ref.session,
        "eod": _clock(dates.get("eod")),
        "greeks": _clock(dates.get("greeks")),
        "oi_publication": _clock(dates.get("oi_publication")),
        "previous_oi_publication": _clock(dates.get("previous_oi_publication")),
        "latest_oi_publication": _clock(dates.get("latest_oi_publication")),
        "unusual_history_window_start": _clock(meta.get("unusual_history_window_start")),
        "unusual_history_window_end": _clock(meta.get("unusual_history_window_end")),
        "unusual_history_sessions_available": meta.get("unusual_history_sessions_available"),
        "unusual_history_sessions_seen": meta.get("unusual_history_sessions_seen"),
    }


def _require_clocks_aligned(clocks: dict) -> None:
    session = clocks.get("session")
    if not isinstance(session, str):
        raise _ReadIssue("undated")
    for name in ("eod", "greeks", "oi_publication"):
        value = clocks.get(name)
        if value is not None and value != session:
            raise _ReadIssue("mixed_source_dates")


def _classify_decode(exc) -> str:
    msg = str(exc)
    if "byte limit" in msg:
        return "oversize"
    if "JSON" in msg or "nonfinite" in msg:
        return "invalid_json"
    if "root" in msg or "schema" in msg:
        return "wrong_root"
    return "invalid_snapshot"


def _receipt_conflict(output_dir: Path, receipt_path: Path) -> None:
    out = output_dir.resolve()
    receipt = receipt_path.expanduser()
    parent = receipt.parent
    if not parent.exists() or not parent.is_dir():
        raise ObservationRefused("receipt parent directory is missing")
    resolved = receipt.resolve()
    if receipt.exists() or resolved.exists():
        raise ObservationRefused("receipt already exists")
    try:
        resolved.relative_to(out)
    except ValueError:
        return
    raise ObservationRefused("receipt path is inside live output or history")


def _load_prior(path: Path, roots, retention, limit: int) -> dict:
    raw = read_local_bytes(Path(path), limit)
    try:
        doc = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=retention._unique_object,
            parse_constant=retention._nonfinite,
            parse_float=retention._finite_float,
        )
    except (ValueError, UnicodeError, RecursionError, _ReadIssue) as exc:
        raise ObservationRefused("invalid prior observation") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ObservationRefused("invalid prior observation schema")
    if (doc.get("complete") is not True or doc.get("stable") is not True
            or doc.get("failures") != {} or doc.get("issues") != []):
        raise ObservationRefused("prior observation was not complete and stable")
    items = doc.get("roots")
    if not isinstance(items, dict) or set(items) != set(roots):
        raise ObservationRefused("invalid prior observation roots")
    sessions = set()
    for root in roots:
        item = items[root]
        if not isinstance(item, dict):
            raise ObservationRefused("invalid prior observation identity")
        for field in _PRIOR_IDENTITY:
            if field not in item:
                raise ObservationRefused("invalid prior observation identity")
        if item.get("root") != root:
            raise ObservationRefused("invalid prior observation identity")
        if type(item.get("byte_length")) is not int:
            raise ObservationRefused("invalid prior observation identity")
        try:
            ref = retention.parse_reference(root, item["version_ref"], item["sha256"])
        except retention.HistoricalUnavailable as exc:
            raise ObservationRefused("invalid prior observation reference") from exc
        if (
            ref.sha256 != item["sha256"]
            or ref.byte_length != item["byte_length"]
            or ref.session != item["session"]
            or ref.key != item["key"]
        ):
            raise ObservationRefused("invalid prior observation reference")
        digest = item.get("observed_side_token_set_digest")
        if digest is not None and (
            not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ObservationRefused("invalid prior observation reference")
        encoding = item.get("observed_side_token_set_encoding")
        if encoding is not None and encoding != TOKEN_SET_ENCODING:
            raise ObservationRefused("invalid prior observation reference")
        sessions.add(ref.session)
    if len(sessions) != 1 or None in sessions:
        raise ObservationRefused("invalid prior observation sessions")
    return doc


def _verify_prior_retention(client, bucket, prior, roots, retention, output_dir: Path,
                            capture_root=None):
    """Re-verify retained prior history; optionally capture one root's bytes.

    The optional capture reuses the exact bytes the existing per-root GET already
    read and records that read's completion clock. It adds no second read of the
    same object, does not reorder any failure check, and claims no cross-time
    atomicity; the caller's final post-prior head re-read still decides currency.
    """
    captured = None
    for root in roots:
        item = prior["roots"][root]
        ref = retention.parse_reference(root, item["version_ref"], item["sha256"])
        try:
            retained = retention.load_snapshot(client, bucket, ref)
        except retention.HistoricalUnavailable as exc:
            missing = getattr(retention, "_MissingSnapshot", ())
            if missing and isinstance(exc, missing):
                raise _ReadIssue("missing_prior_history") from None
            kind, code, status = _classify_s3_error(exc.__cause__ or exc)
            if kind == "denied" or kind == "missing":
                raise _ReadIssue(
                    "denied_prior_history" if kind == "denied" else "missing_prior_history",
                    error_code=code,
                    http_status=status,
                ) from None
            raise _ReadIssue("unavailable_prior_history") from None
        captured_at = _utc_now() if root == capture_root else None
        prior_doc = retention.verify_snapshot(ref, retained)
        _require_measured(prior_doc)
        _require_clocks_aligned(_source_clocks(ref, prior_doc))
        prior_tokens = retention.matrix_observed_side_tokens(ref, retained)
        if item.get("observed_side_token_set_digest") != token_set_digest(prior_tokens):
            raise _ReadIssue("mismatched_prior_observed_sides")
        local_hist = output_dir / "history" / root / f"{ref.sha256}.json"
        if local_hist.exists():
            local_raw = read_local_bytes(local_hist, retention.MAX_MATRIX_BYTES)
            if local_raw != retained:
                raise _ReadIssue("mismatched_prior_history")
        if captured_at is not None:
            captured = (retained, captured_at)
    return captured


def _write_receipt(path: Path, result: dict) -> None:
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    data = payload.encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            written = handle.write(data)
            if written != len(data):
                raise OSError("short receipt write")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _observe_root(root, output_dir, client, bucket, retention, limit):
    retention.validate_root(root)
    local_path = output_dir / f"{root}.json"
    try:
        local = read_local_bytes(local_path, limit)
    except _ReadIssue as issue:
        mapped = {
            "missing": "missing_local_head",
            "oversize": "oversize",
        }.get(issue.code, issue.code)
        raise _ReadIssue(mapped, issue.error_code, issue.http_status) from issue
    head_key = f"{retention.R2_PREFIX}{root}.json"
    try:
        remote = read_remote_bytes(client, bucket, head_key, limit)
    except _ReadIssue as issue:
        if issue.code == "missing":
            raise _ReadIssue("missing_remote_head", issue.error_code, issue.http_status) from issue
        if issue.code == "denied":
            raise _ReadIssue("denied", issue.error_code, issue.http_status) from issue
        if issue.code == "oversize":
            raise _ReadIssue("oversize", issue.error_code, issue.http_status) from issue
        raise _ReadIssue("unavailable", issue.error_code, issue.http_status) from issue
    if local != remote:
        raise _ReadIssue("mismatched_head_bytes")
    try:
        ref = retention.reference_for_bytes(root, local)
        doc = retention.verify_snapshot(ref, local)
    except retention.HistoricalUnavailable as exc:
        raise _ReadIssue(_classify_decode(exc)) from exc
    _require_measured(doc)
    clocks = _source_clocks(ref, doc)
    _require_clocks_aligned(clocks)
    history_path = output_dir / "history" / root / f"{ref.sha256}.json"
    try:
        local_history = read_local_bytes(history_path, limit)
    except _ReadIssue as issue:
        if issue.code == "missing":
            raise _ReadIssue("missing_local_history") from issue
        raise _ReadIssue(
            "mismatched_local_history" if issue.code == "oversize" else issue.code
        ) from issue
    if local_history != local:
        raise _ReadIssue("mismatched_local_history")
    try:
        remote_history = retention.load_snapshot(client, bucket, ref)
    except retention.HistoricalUnavailable as exc:
        missing = getattr(retention, "_MissingSnapshot", ())
        if missing and isinstance(exc, missing):
            raise _ReadIssue("missing_remote_history") from None
        raise _ReadIssue("unavailable_remote_history") from None
    if remote_history != local:
        raise _ReadIssue("mismatched_remote_history")
    try:
        tokens = retention.matrix_observed_side_tokens(ref, local)
    except retention.HistoricalUnavailable as exc:
        raise _ReadIssue("invalid_observed_sides") from exc
    return local, {
        "root": root,
        "sha256": ref.sha256,
        "byte_length": ref.byte_length,
        "session": ref.session,
        "version_ref": ref.version_ref,
        "key": ref.key,
        "cells": len(doc["cells"]),
        "spot": doc["spot"],
        "observed_sides": len(tokens),
        "observed_side_token_set_digest": token_set_digest(tokens),
        "observed_side_token_set_encoding": TOKEN_SET_ENCODING,
        "source_clocks": clocks,
        "local_head_history_remote_head_history_equal": True,
    }


def _reread_heads(roots, snapshots, output_dir, client, bucket, retention, limit):
    issues = {}
    for root in roots:
        expected = snapshots.get(root)
        if expected is None:
            continue
        try:
            local = read_local_bytes(output_dir / f"{root}.json", limit)
            remote = read_remote_bytes(
                client, bucket, f"{retention.R2_PREFIX}{root}.json", limit,
            )
        except _ReadIssue as issue:
            issues[root] = _ReadIssue(
                "concurrent_head_change" if issue.code != "denied" else "denied",
                error_code=issue.error_code,
                http_status=issue.http_status,
            ).as_dict()
            continue
        if local != expected or remote != expected:
            issues[root] = {"code": "concurrent_head_change"}
    return issues


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def capture_spy_identity_inputs(repo, *, vendor):
    """Capture existing canonical files for an optional identity join.

    The existing writer currently retains only a SPY source admission. Read
    clocks describe this capture, not historical availability or HTTP provenance.
    Uses the observer's bounded local reader; no atomic snapshot or hostile
    filesystem replacement guarantee is introduced.
    """
    from engine.intelligence_workspace.entity import IdentityArtifactRead
    if vendor != "thetadata":
        raise ObservationRefused("SPY source receipt requires explicit thetadata namespace")
    retention = _retention()
    base = Path(repo) / "data/reference"

    def captured(name):
        raw = read_local_bytes(base / name, retention.MAX_MATRIX_BYTES)
        return IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), _utc_now())

    try:
        aliases = captured("vendor_aliases.parquet")
        master = captured("security_master.parquet")
        receipt = captured("_receipt.json")
        document = json.loads(receipt.body.decode("utf-8"),
                              object_pairs_hook=retention._unique_object,
                              parse_constant=retention._nonfinite,
                              parse_float=retention._finite_float)
        evidence = document["spy_option_root"]
        if (type(evidence) is not dict
                or evidence.get("schema") != "mastermind.spy_option_root_sources.v1"
                or evidence.get("vendor") != vendor or evidence.get("root") != "SPY"):
            raise ValueError("unexpected source receipt")
        # This is the existing writer's evidence serialization, which the alias
        # independently binds. The enclosing receipt hash remains visible too.
        body = (json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        root_evidence = IdentityArtifactRead(body, hashlib.sha256(body).hexdigest(), receipt.read_at)
    except (_ReadIssue, KeyError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ObservationRefused("canonical SPY identity inputs unavailable or invalid") from exc
    return {"vendor": vendor, "roots": ("SPY",), "aliases": aliases, "security_master": master,
            "root_evidence": root_evidence, "writer_receipt_sha256": receipt.sha256}


def capture_selection_input(path):
    """Capture one exact retained selection file for the optional selection join.

    Uses the observer's existing bounded local reader, so an oversize or empty
    file refuses here before any client GET. The returned read clock describes
    this finite read only; it is not an atomic filesystem guarantee, a source
    authentication, or a rights or Save decision.
    """
    from engine.intelligence_workspace.entity import IdentityArtifactRead
    from engine.intelligence_workspace.options_identity import _SELECTION_MAX_BYTES
    try:
        raw = read_local_bytes(Path(path), _SELECTION_MAX_BYTES)
    except _ReadIssue as exc:
        raise ObservationRefused("selection input unavailable, empty, or oversize") from exc
    return IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), _utc_now())


def _join_observed_identity(required, snapshots, failures, inputs, matrix_reads, retention):
    """Resolve only exact successfully observed bytes through the existing reader."""
    from engine.intelligence_workspace.entity import IdentityArtifactRead, IdentityResolutionError
    from engine.intelligence_workspace.options_identity import resolve_option_matrix_security
    decision_at = _utc_now()
    items = {}
    for root in required:
        if root in failures or root not in snapshots:
            items[root] = {"status": "UNAVAILABLE", "reason": "snapshot_not_verified"}
            continue
        raw = snapshots[root]
        ref = retention.reference_for_bytes(root, raw)
        read = IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), matrix_reads[root])
        try:
            resolved = resolve_option_matrix_security(
                ref, read, vendor=inputs["vendor"], decision_at=decision_at,
                aliases=inputs["aliases"], security_master=inputs["security_master"],
                root_evidence=inputs["root_evidence"],
            )
        except IdentityResolutionError:
            items[root] = {"status": "UNAVAILABLE", "reason": "identity_contract_invalid"}
            continue
        if resolved is None:
            items[root] = {"status": "UNAVAILABLE", "reason": "root_session_unbound"}
            continue
        underlying = resolved.underlying
        items[root] = {
            "status": "RESOLVED", "security_id": underlying.binding.security_id,
            "listing_key": underlying.listing_key, "vendor": inputs["vendor"],
            "root": ref.root, "session": ref.session, "matrix_sha256": ref.sha256,
            "version_ref": ref.version_ref, "matrix_read_at": read.read_at.isoformat(),
            "available_at": resolved.available_at.isoformat(),
            "aliases_sha256": underlying.aliases_sha256,
            "security_master_sha256": underlying.master_sha256,
            "root_evidence_sha256": inputs["root_evidence"].sha256,
            "binding_sha256": underlying.binding.binding_sha256,
        }
    return {"scope": list(required), "complete": all(item["status"] == "RESOLVED" for item in items.values()),
            "decision_at": decision_at.isoformat(), "roots": items,
            "writer_receipt_sha256": inputs["writer_receipt_sha256"]}


def _validate_selection_input(selection_input):
    """Refuse a wrong captured selection before any client GET or receipt write."""
    from engine.intelligence_workspace.entity import (
        IdentityArtifactRead,
        _identity_evidence_clock,
        _identity_read,
    )
    from engine.intelligence_workspace.options_identity import _SELECTION_MAX_BYTES
    if not isinstance(selection_input, IdentityArtifactRead):
        raise ObservationRefused("invalid captured selection input")
    body = selection_input.body
    if (type(body) is not bytes
            or not 0 < len(body) <= _SELECTION_MAX_BYTES
            or type(selection_input.sha256) is not str
            or len(selection_input.sha256) != 64
            or any(c not in "0123456789abcdef" for c in selection_input.sha256)
            or hashlib.sha256(body).hexdigest() != selection_input.sha256):
        raise ObservationRefused("invalid captured selection bytes or digest")
    try:
        _identity_read(selection_input, _identity_evidence_clock(_utc_now()))
    except (ValueError, TypeError) as exc:
        raise ObservationRefused("invalid captured selection read clock") from exc


def _resolve_observed_selection(
    *, target, identity_inputs, snapshots, matrix_reads, failures, result,
    retention, prior_capture, selection_input,
) -> dict:
    """Join the exact captured selection to one exact observed SPY snapshot.

    Membership is decided only by the existing resolve_option_matrix_selection
    over the selected snapshot's own verified bytes: the observed current head,
    or the bytes the prior verification GET already read. Any unavailable outcome
    stays inside result["selection"]; publication complete/stable/advancing are
    unchanged and a failed or unbound selected snapshot never falls back to the
    other snapshot's bytes.
    """
    from engine.intelligence_workspace.entity import (
        IdentityArtifactRead,
        IdentityResolutionError,
        _identity_evidence_clock,
        _identity_read,
    )
    from engine.intelligence_workspace.options_identity import resolve_option_matrix_selection

    def unavailable(reason):
        return {"target": target, "status": "UNAVAILABLE", "complete": False, "reason": reason}

    if result.get("complete") is not True:
        return unavailable("publication_not_complete")
    if result.get("stable") is not True:
        return unavailable("publication_unstable")
    if result.get("identity", {}).get("complete") is not True:
        return unavailable("identity_incomplete")
    if target == "prior":
        if prior_capture is None or "invalid_prior_retention" in result.get("issues", []):
            return unavailable("prior_snapshot_not_verified")
        raw, matrix_read_at = prior_capture
    else:
        if "SPY" in failures or "SPY" not in snapshots or "SPY" not in matrix_reads:
            return unavailable("snapshot_not_verified")
        raw = snapshots["SPY"]
        matrix_read_at = matrix_reads["SPY"]
    matrix_clock = _identity_evidence_clock(matrix_read_at)
    decision_at = _utc_now()
    ref = retention.reference_for_bytes("SPY", raw)
    read = IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), matrix_clock)
    try:
        selection_read_at = _identity_read(selection_input, decision_at)
        resolved = resolve_option_matrix_selection(
            ref, read, selection_input.body,
            vendor=identity_inputs["vendor"], decision_at=decision_at,
            aliases=identity_inputs["aliases"],
            security_master=identity_inputs["security_master"],
            root_evidence=identity_inputs["root_evidence"],
        )
    except IdentityResolutionError:
        return unavailable("selection_unresolved")
    return {
        "target": target,
        "status": "RESOLVED",
        "complete": True,
        "root": ref.root,
        "session": ref.session,
        "version_ref": ref.version_ref,
        "matrix_sha256": ref.sha256,
        "security_id": resolved.matrix.underlying.binding.security_id,
        "selection_sha256": selection_input.sha256,
        "selection_read_at": selection_read_at.isoformat(),
        "matrix_read_at": matrix_clock.isoformat(),
        "decision_at": decision_at.isoformat(),
        "available_at": max(resolved.matrix.available_at, selection_read_at).isoformat(),
        "primary": {
            "expiry": resolved.primary.expiry,
            "strike": resolved.primary.strike,
            "side": resolved.primary.side,
        },
        "comparisons": [
            {"expiry": coordinate.expiry, "strike": coordinate.strike, "side": coordinate.side}
            for coordinate in resolved.comparisons
        ],
        "view": {
            "lens": resolved.view.lens,
            "metric": resolved.view.metric,
            "side": resolved.view.side,
            "expiry": resolved.view.expiry,
            "display_mode": resolved.view.display_mode,
        },
        "primary_hidden": resolved.primary_hidden,
        "comparisons_hidden": list(resolved.comparisons_hidden),
    }


def observe_publication(
    *,
    output_dir,
    client,
    bucket,
    roots=None,
    prior_path=None,
    receipt_path=None,
    retention_module=None,
    now=None,
    identity_inputs=None,
    selection_input=None,
    selection_target="current",
) -> dict:
    """Collect one read-only observation of published matrix snapshots.

    `client` must already exist. This function never constructs a publisher
    client, never lists buckets, and never writes production objects. A receipt
    is created only at an explicitly supplied new path. Optional identity_inputs
    come from capture_spy_identity_inputs; the join covers SPY, not the other roots.
    Its captured files and clocks describe a finite read, not a current/live grant.

    Optional selection_input is one exact captured retained selection read from
    capture_selection_input; it requires identity_inputs, and selection_target
    "prior" additionally requires prior_path. selection_target picks which exact
    SPY bytes the selection joins to: "current" uses the observed head, "prior"
    uses the bytes the prior retention verification already read. The selection
    is reported only in a separate result["selection"] entry built before any
    receipt write. It never changes publication complete/stable/advancing,
    never substitutes a different snapshot for the selected one, and proves
    stored membership and recorded view only.
    """
    if client is None:
        raise ObservationRefused("observer requires an injected or CLI-provisioned client")
    if not isinstance(bucket, str) or not bucket:
        raise ObservationRefused("bucket is required")
    retention = _retention(retention_module)
    limit = retention.MAX_MATRIX_BYTES
    required = tuple(roots) if roots is not None else tuple(DEFAULT_ROOTS)
    if not required:
        raise ObservationRefused("roots are required")
    seen = set()
    for root in required:
        retention.validate_root(root)
        if root in seen:
            raise ObservationRefused("duplicate observer root")
        seen.add(root)
    if identity_inputs is not None:
        from engine.intelligence_workspace.entity import IdentityArtifactRead
        fields = {"vendor", "roots", "aliases", "security_master", "root_evidence", "writer_receipt_sha256"}
        if (type(identity_inputs) is not dict or set(identity_inputs) != fields
                or identity_inputs["vendor"] != "thetadata"
                or identity_inputs["roots"] != ("SPY",) or "SPY" not in required
                or any(not isinstance(identity_inputs[name], IdentityArtifactRead)
                       for name in ("aliases", "security_master", "root_evidence"))
                or type(identity_inputs["writer_receipt_sha256"]) is not str
                or len(identity_inputs["writer_receipt_sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in identity_inputs["writer_receipt_sha256"])):
            raise ObservationRefused("invalid captured SPY identity input bundle")
    if selection_target not in _SELECTION_TARGETS:
        raise ObservationRefused("selection target must be current or prior")
    if selection_input is None:
        if selection_target != "current":
            raise ObservationRefused("selection target requires a selection input")
    else:
        if identity_inputs is None:
            raise ObservationRefused("selection verification requires captured SPY identity inputs")
        if selection_target == "prior" and prior_path is None:
            raise ObservationRefused("prior selection target requires a prior observation")
        _validate_selection_input(selection_input)
    capture_root = (
        "SPY" if selection_input is not None and selection_target == "prior" else None
    )
    output_dir = Path(output_dir)
    if not output_dir.exists() or not output_dir.is_dir():
        raise ObservationRefused("output directory is missing")
    receipt = Path(receipt_path) if receipt_path is not None else None
    if receipt is not None:
        _receipt_conflict(output_dir, receipt)
    prior = None
    if prior_path is not None:
        try:
            prior = _load_prior(Path(prior_path), required, retention, limit)
        except _ReadIssue as exc:
            raise ObservationRefused("invalid prior observation") from exc

    observed_at = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    items = {}
    snapshots = {}
    matrix_reads = {}
    failures = {}
    for root in required:
        try:
            raw, item = _observe_root(root, output_dir, client, bucket, retention, limit)
        except _ReadIssue as issue:
            failures[root] = issue.as_dict()
            continue
        except retention.HistoricalUnavailable:
            failures[root] = {"code": "invalid_snapshot"}
            continue
        items[root] = item
        snapshots[root] = raw
        if identity_inputs is not None:
            matrix_reads[root] = _utc_now()

    issues = []
    if len(items) != len(required):
        issues.append("partial_roots")
    sessions = {item["session"] for item in items.values()}
    if any(item.get("source_clocks", {}).get("session") != item["session"] for item in items.values()):
        issues.append("mixed_source_dates")
    if len(sessions) > 1:
        issues.append("mixed_source_dates")
    common_session = next(iter(sessions)) if len(sessions) == 1 and None not in sessions else None

    concurrent = _reread_heads(required, snapshots, output_dir, client, bucket, retention, limit)
    for root, item in concurrent.items():
        failures[root] = item
        issues.append("unstable")
    if concurrent:
        issues.append("unstable")
    # de-dup issues while preserving order
    seen_issues = set()
    unique_issues = []
    for name in issues:
        if name not in seen_issues:
            seen_issues.add(name)
            unique_issues.append(name)
    issues = unique_issues

    prior_capture = None
    prior_session = None
    repeated = False
    advancing = False
    if prior is not None:
        prior_session = next(iter({prior["roots"][root]["session"] for root in required}))
        try:
            prior_capture = _verify_prior_retention(
                client, bucket, prior, required, retention, output_dir,
                capture_root=capture_root,
            )
        except _ReadIssue as issue:
            failures["_prior"] = issue.as_dict()
            issues.append("invalid_prior_retention")
            prior_capture = None
        else:
            # Reopening A must finish before the final observation that B is
            # still current. A prior read can overlap a publisher advancing B.
            # Already failed observations need no additional remote reads.
            if not failures:
                after_prior = _reread_heads(
                    required, snapshots, output_dir, client, bucket, retention, limit)
                failures.update(after_prior)
                if after_prior and "unstable" not in issues:
                    issues.append("unstable")
        if common_session is not None and prior_session is not None:
            if common_session < prior_session:
                issues.append("older_than_prior")
            elif common_session == prior_session:
                repeated = True
            elif (
                len(items) == len(required)
                and "unstable" not in issues
                and "invalid_prior_retention" not in issues
                and "mixed_source_dates" not in issues
            ):
                advancing = True

    complete = (
        len(items) == len(required)
        and common_session is not None
        and not issues
    )
    if not complete:
        advancing = False

    result = {
        "schema": SCHEMA,
        "observed_at": observed_at,
        "roots": items,
        "failures": failures,
        "issues": issues,
        "session": common_session,
        "complete": complete,
        "advancing": advancing,
        "repeated_source_date": repeated,
        "stable": "unstable" not in issues,
        "natural_invocation_verified": False,
        "natural_session_count": None,
        "mutable_writes": False,
        "prior_session": prior_session,
        "receipt_written": receipt is not None,
        "observed_side_token_set_encoding": TOKEN_SET_ENCODING,
    }
    if identity_inputs is not None:
        result["identity"] = _join_observed_identity(
            identity_inputs["roots"], snapshots, failures, identity_inputs, matrix_reads, retention)
        result["identity"]["complete"] = complete and result["identity"]["complete"]
    if selection_input is not None:
        result["selection"] = _resolve_observed_selection(
            target=selection_target,
            identity_inputs=identity_inputs,
            snapshots=snapshots,
            matrix_reads=matrix_reads,
            failures=failures,
            result=result,
            retention=retention,
            prior_capture=prior_capture,
            selection_input=selection_input,
        )
    if receipt is not None:
        _write_receipt(receipt, result)
    return result


def _ensure_repo_path(repo) -> Path:
    path = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parent.parent
    rendered = str(path)
    # An explicit deployed checkout takes precedence even if already on sys.path.
    sys.path[:] = [entry for entry in sys.path if entry != rendered]
    sys.path.insert(0, rendered)
    return path


def main(argv=None, *, client=None) -> int:
    parser = argparse.ArgumentParser(
        description="One-shot read-only observation of published options matrix snapshots.",
    )
    parser.add_argument("--repo", default=None, help="Macro checkout providing engine/ and scripts/")
    parser.add_argument("--out", required=True, help="Local matrix output directory (explicit path)")
    parser.add_argument("--receipt", default=None, help="New exclusive receipt path (optional)")
    parser.add_argument("--prior", default=None, help="Prior observation receipt to compare (optional)")
    parser.add_argument("--bucket", default=None, help="R2 bucket; default R2_BUCKET from provisioned env")
    parser.add_argument("--identity-vendor", choices=("thetadata",), default=None,
                        help="Also join exact observed Matrix bytes to captured canonical SPY identity")
    parser.add_argument("--selection", default=None,
                        help="Exact retained selection JSON file to verify (optional)")
    parser.add_argument("--selection-target", choices=("current", "prior"), default="current",
                        help="Which exact SPY snapshot bytes the selection joins to (default current)")
    args = parser.parse_args(argv)

    # Option combinations are refused before any capture, client provisioning,
    # or network read.
    if args.selection is None and args.selection_target != "current":
        print("--selection-target requires --selection", file=sys.stderr)
        return 2
    if args.selection is not None:
        if args.identity_vendor is None:
            print("--selection requires --identity-vendor thetadata", file=sys.stderr)
            return 2
        if args.selection_target == "prior" and args.prior is None:
            print("--selection-target prior requires --prior", file=sys.stderr)
            return 2

    repo = _ensure_repo_path(args.repo)
    from engine import options_matrix_retention as retention
    from scripts.build_options_matrix import DEFAULT_ROOTS as publisher_roots
    if tuple(publisher_roots) != tuple(DEFAULT_ROOTS):
        print("observer DEFAULT_ROOTS drifted from publisher", file=sys.stderr)
        return 2
    identity_inputs = None
    if args.identity_vendor is not None:
        try:
            identity_inputs = capture_spy_identity_inputs(repo, vendor=args.identity_vendor)
        except ObservationRefused as exc:
            print(str(exc), file=sys.stderr)
            return 2
    selection_input = None
    if args.selection is not None:
        try:
            selection_input = capture_selection_input(args.selection)
        except ObservationRefused as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if client is None:
        from scripts.build_options_matrix import _r2_client
        client = _r2_client()
        if client is None:
            print(
                "R2 client unavailable; invoke through existing run_with_env.sh "
                "with provisioned environment",
                file=sys.stderr,
            )
            return 2
    bucket = args.bucket or os.environ.get("R2_BUCKET")
    if not bucket:
        print("--bucket or provisioned R2_BUCKET is required", file=sys.stderr)
        return 2
    try:
        result = observe_publication(
            output_dir=args.out,
            client=client,
            bucket=bucket,
            roots=DEFAULT_ROOTS,
            prior_path=args.prior,
            receipt_path=args.receipt,
            retention_module=retention,
            identity_inputs=identity_inputs,
            selection_input=selection_input,
            selection_target=args.selection_target,
        )
    except ObservationRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, allow_nan=False)
    sys.stdout.write("\n")
    identity_ok = identity_inputs is None or result.get("identity", {}).get("complete") is True
    if selection_input is not None and result.get("selection", {}).get("complete") is not True:
        return 1
    return 0 if result.get("complete") and result.get("stable") and identity_ok else 1


if __name__ == "__main__":
    sys.exit(main())
