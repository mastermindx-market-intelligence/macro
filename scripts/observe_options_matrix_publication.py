"""One-shot read-only Options Matrix publication observer.


Observes already-published local and authenticated remote snapshot bytes for
the incumbent publisher DEFAULT_ROOTS. This is not a scheduler, repair tool,
publisher, or natural-invocation verifier. Importing this module does not
create a client or read live objects.

natural_invocation_verified is always false. natural_session_count is always
null. Repeated source dates are complete observations of the same session,
not advances. A successful collection is snapshot evidence only.

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


def _verify_prior_retention(client, bucket, prior, roots, retention, output_dir: Path) -> None:
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
) -> dict:
    """Collect one read-only observation of published matrix snapshots.

    `client` must already exist. This function never constructs a publisher
    client, never lists buckets, and never writes production objects. A receipt
    is created only at an explicitly supplied new path.
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

    prior_session = None
    repeated = False
    advancing = False
    if prior is not None:
        prior_session = next(iter({prior["roots"][root]["session"] for root in required}))
        try:
            _verify_prior_retention(client, bucket, prior, required, retention, output_dir)
        except _ReadIssue as issue:
            failures["_prior"] = issue.as_dict()
            issues.append("invalid_prior_retention")
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
    if receipt is not None:
        _write_receipt(receipt, result)
    return result


def _ensure_repo_path(repo) -> Path:
    path = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parent.parent
    rendered = str(path)
    if rendered not in sys.path:
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
    args = parser.parse_args(argv)

    repo = _ensure_repo_path(args.repo)
    from engine import options_matrix_retention as retention
    from scripts.build_options_matrix import DEFAULT_ROOTS as publisher_roots
    if tuple(publisher_roots) != tuple(DEFAULT_ROOTS):
        print("observer DEFAULT_ROOTS drifted from publisher", file=sys.stderr)
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
        )
    except ObservationRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, allow_nan=False)
    sys.stdout.write("\n")
    return 0 if result.get("complete") and result.get("stable") else 1


if __name__ == "__main__":
    sys.exit(main())
