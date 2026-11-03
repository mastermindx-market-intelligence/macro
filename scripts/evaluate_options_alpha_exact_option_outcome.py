#!/usr/bin/env python3
"""Read-only offline CLI adapter for the OA-3 exact-option outcome ruler.

This script is a thin transport adapter around the incumbent evaluator
``engine.options_alpha_exact_option_outcome``.  Every economic rule — window
identity, clock causality, quote admissibility, return arithmetic, reason
vocabularies, authority blocks — is owned by that module; this adapter only
reads a local JSON handoff manifest plus the local raw-byte capture files it
references, hands them to the evaluator's public constructors
(``expression_receipt_from_bytes``, ``quote_evidence_from_bytes``,
``evaluate``), and prints the returned fixture record as canonical JSON on
stdout.

The adapter never performs network I/O, never writes a file, never reads the
current clock, never derives or recomputes the upstream expression digest,
never infers a missing role timestamp, and never fabricates evidence: both
role captures (entry and exit) must exist as real local byte files even when
the evaluated outcome is ``pending``.

Minimal manifest shape (keys are exact — extra or missing keys are rejected;
duplicate keys and non-finite JSON numbers are rejected by the strict
parser)::

    {
      "expression": {
        "raw_path": "expression.json",
        "upstream_digest_sha256": "<64-hex lowercase upstream digest>"
      },
      "entry": {
        "contract": {...}, "boundary_at": "<ISO aware datetime>",
        "query_end_at": "<ISO aware datetime>", "query": {...},
        "raw_path": "entry_quotes.json",
        "endpoint": "/v3/option/history/quote",
        "request_started_at": "<ISO aware datetime>",
        "response_observed_at": "<ISO aware datetime>",
        "retrieval_observed_at": "<ISO aware datetime>",
        "computed_at": "<ISO aware datetime>"
      },
      "exit": { "...same ten role keys as entry...": "..." }
    }

* ``raw_path`` values are relative to the manifest's own directory; absolute
  paths, ``..`` components, and symlink escapes out of that directory are
  refused.  Inputs are bounded regular files (manifest <= 1 MiB, expression
  <= 1 MiB, each role capture <= 16 MiB) whose bytes are passed to the
  evaluator verbatim — the adapter never reserializes a raw body.
* Every clock is a caller-supplied ISO-8601 string with an explicit aware
  timezone.  The adapter parses them and delegates all causality and window
  rules to the evaluator; a missing or naive clock is a rejected input,
  never an inferred one.  The ``endpoint`` is explicit in the manifest and
  is bound to the frozen source endpoint by the evaluator.

Provenance and authority limits: the manifest and its captures are
caller-supplied local bytes.  The adapter validates local shape only; it does
NOT verify that the manifest provenance was produced or witnessed by any
external capture process.  The emitted record is a local evaluation of
locally supplied evidence; it is NOT proof of live capture, not a training
admission, and not trading authority of any kind (the record's ``authority``
block is all-false by construction).

Usage::

    python3 scripts/evaluate_options_alpha_exact_option_outcome.py --input PATH

Exit codes: ``0`` — the manifest was evaluated and the fixture record was
printed as one canonical JSON line; ``2`` — the input was missing or
malformed (concise stderr message carrying no raw payload, no filesystem
paths, and no secret values).
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from datetime import date as _date_cls
from datetime import datetime as _datetime_cls
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

# ─── ROOT bootstrap ──────────────────────────────────────────────────────────
# The script ships as a standalone file under ``scripts/`` and must import
# the incumbent engine from the repository root regardless of the caller's
# working directory.  The insert is unconditional: even when REPO_ROOT is
# already present further down sys.path (for example as a caller-supplied
# PYTHONPATH entry), it must be moved to the front so a foreign ``engine``
# package earlier on the path cannot shadow the incumbent one.

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine import options_alpha_exact_option_outcome as oa3  # noqa: E402
from engine import options_nbbo_cohort as cohort  # noqa: E402

EXIT_OK = 0
EXIT_INPUT_ERROR = 2

MANIFEST_MAX_BYTES = 1024 * 1024
EXPRESSION_MAX_BYTES = 1024 * 1024
QUOTE_MAX_BYTES = 16 * 1024 * 1024

_MANIFEST_KEYS = {"expression", "entry", "exit"}
_EXPRESSION_SECTION_KEYS = {"raw_path", "upstream_digest_sha256"}
_ROLE_SECTION_KEYS = {
    "contract",
    "boundary_at",
    "query_end_at",
    "query",
    "raw_path",
    "endpoint",
    "request_started_at",
    "response_observed_at",
    "retrieval_observed_at",
    "computed_at",
}
_ROLE_CLOCK_FIELDS = (
    "boundary_at",
    "query_end_at",
    "request_started_at",
    "response_observed_at",
    "retrieval_observed_at",
    "computed_at",
)


class ManifestInputError(Exception):
    """The handoff input is missing or malformed; the CLI exits 2.

    The message names the offending manifest section and key only — never a
    raw payload, a filesystem path, or a secret value.
    """


def _fail(message: str) -> NoReturn:
    raise ManifestInputError(message)


# ─── Manifest shape validation ───────────────────────────────────────────────


def _require_exact_keys(section: object, expected: set[str], where: str) -> None:
    if not isinstance(section, dict):
        _fail(f"{where} must be a JSON object")
    present = set(section)
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append(f"unexpected key count: {len(extra)}")
        _fail(f"{where} keys are not exact (" + "; ".join(details) + ")")


def _parse_clock(value: object, field: str) -> _datetime_cls:
    if not isinstance(value, str) or not value:
        _fail(f"{field} must be an ISO-8601 datetime string with an explicit aware timezone")
    text = value[:-1] + "+00:00" if value[-1] in ("Z", "z") else value
    try:
        parsed = _datetime_cls.fromisoformat(text)
    except ValueError:
        _fail(f"{field} must be an ISO-8601 datetime string with an explicit aware timezone")
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        _fail(f"{field} must be an ISO-8601 datetime string with an explicit aware timezone")
    return parsed


# ─── Bounded, escape-free raw file access ────────────────────────────────────


def _resolve_raw_path(manifest_dir: Path, value: object, where: str) -> Path:
    """Resolve one caller-supplied raw_path strictly inside the manifest dir.

    The path must be a relative string with no ``..`` component and must
    resolve (symlinks included) to a path still inside the manifest's own
    directory.  No filesystem path ever appears in a refusal message.
    """

    if not isinstance(value, str) or not value or value != value.strip():
        _fail(f"{where} raw_path must be a non-empty relative path string")
    candidate = Path(value)
    if candidate.is_absolute() or value.startswith(("/", "\\")):
        _fail(f"{where} raw_path must be relative to the manifest directory")
    if any(part == ".." for part in candidate.parts):
        _fail(f"{where} raw_path must not contain '..' components")
    try:
        base = manifest_dir.resolve()
        target = (manifest_dir / candidate).resolve()
    except (OSError, ValueError, RuntimeError):
        _fail(f"{where} raw_path cannot be resolved inside the manifest directory")
    if target == base or base not in target.parents:
        _fail(f"{where} raw_path escapes the manifest directory")
    return target


def _read_bounded(target: Path, *, limit: int, where: str) -> bytes:
    """Read one bounded regular file byte-exactly; never reserialize."""

    # Check the opened object, then cap the actual read. A pre-open stat alone
    # does not bound a growing file or prevent a replaced FIFO from blocking.
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        with os.fdopen(os.open(target, flags), "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                _fail(f"{where} raw capture file is not a regular file")
            if info.st_size > limit:
                _fail(f"{where} raw capture file exceeds the {limit}-byte bound")
            data = handle.read(limit + 1)
    except (OSError, ValueError):
        _fail(f"{where} raw capture file is missing or unreadable")
    if len(data) > limit:
        _fail(f"{where} raw capture file exceeds the {limit}-byte bound")
    if not data:
        _fail(f"{where} raw capture file is empty")
    return data


def _load_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    """Read and strictly parse the manifest; return (manifest, base_dir)."""

    raw = _read_bounded(manifest_path, limit=MANIFEST_MAX_BYTES, where="input manifest")
    try:
        manifest = cohort.strict_json_object(raw, label="oa3 handoff manifest")
    except (cohort.NbboCohortError, RecursionError):
        _fail(
            "input manifest is not a strict JSON object "
            "(malformed JSON, duplicate keys, or non-finite numbers)"
        )
    return manifest, manifest_path.resolve().parent


# ─── Evaluation entry points ────────────────────────────────────────────────


def evaluate_input(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Evaluate one local handoff manifest and return the OA-3 fixture record.

    Raises ``ManifestInputError`` when the manifest, its raw capture files,
    or the evidence the evaluator refuses to bind make the input malformed.
    All economic rules are delegated to the incumbent evaluator; this adapter
    derives no digest, reads no clock, and fabricates no evidence.
    """

    manifest_path = Path(path)
    manifest, manifest_dir = _load_manifest(manifest_path)
    _require_exact_keys(manifest, _MANIFEST_KEYS, "manifest")

    expression_section = manifest["expression"]
    _require_exact_keys(expression_section, _EXPRESSION_SECTION_KEYS, "manifest 'expression' section")
    upstream_digest = expression_section["upstream_digest_sha256"]
    if not isinstance(upstream_digest, str) or not upstream_digest:
        _fail("manifest 'expression' section upstream_digest_sha256 must be a non-empty string")
    expression_bytes = _read_bounded(
        _resolve_raw_path(manifest_dir, expression_section["raw_path"], "manifest 'expression' section"),
        limit=EXPRESSION_MAX_BYTES,
        where="expression",
    )
    try:
        receipt = oa3.expression_receipt_from_bytes(expression_bytes, upstream_digest)
    except oa3.Oa3InputError as exc:
        _fail(f"evaluator rejected the expression receipt input ({type(exc).__name__})")

    evidence_by_role: dict[str, oa3.QuoteEvidence] = {}
    for role in (oa3.ROLE_ENTRY, oa3.ROLE_EXIT):
        where = f"manifest {role!r} section"
        section = manifest[role]
        _require_exact_keys(section, _ROLE_SECTION_KEYS, where)
        endpoint = section["endpoint"]
        if not isinstance(endpoint, str) or not endpoint:
            _fail(f"{where} endpoint must be a non-empty string")
        contract = section["contract"]
        query = section["query"]
        if not isinstance(contract, dict):
            _fail(f"{where} contract must be a JSON object")
        if not isinstance(query, dict):
            _fail(f"{where} query must be a JSON object")
        clocks = {
            field: _parse_clock(section[field], f"{where} {field!r}")
            for field in _ROLE_CLOCK_FIELDS
        }
        raw_bytes = _read_bounded(
            _resolve_raw_path(manifest_dir, section["raw_path"], where),
            limit=QUOTE_MAX_BYTES,
            where=role,
        )
        try:
            evidence_by_role[role] = oa3.quote_evidence_from_bytes(
                role=role,
                contract=contract,
                boundary_at=clocks["boundary_at"],
                query_end_at=clocks["query_end_at"],
                query=query,
                raw_bytes=raw_bytes,
                request_started_at=clocks["request_started_at"],
                response_observed_at=clocks["response_observed_at"],
                retrieval_observed_at=clocks["retrieval_observed_at"],
                computed_at=clocks["computed_at"],
                endpoint=endpoint,
            )
        except oa3.Oa3InputError as exc:
            _fail(f"evaluator rejected the {role} evidence input ({type(exc).__name__})")

    try:
        return oa3.evaluate(
            receipt,
            entry_evidence=evidence_by_role[oa3.ROLE_ENTRY],
            exit_evidence=evidence_by_role[oa3.ROLE_EXIT],
        )
    except oa3.Oa3InputError as exc:
        _fail(f"evaluator refused the handoff input ({type(exc).__name__})")


def fixture_json_bytes(record: Mapping[str, Any]) -> bytes:
    """Serialize one fixture record to canonical JSON bytes (one line + LF).

    Datetimes become ISO-8601 strings and Decimals become exact decimal
    strings; keys are sorted and separators compact so the same record always
    emits the same stdout bytes.
    """

    def _default(value: Any) -> Any:
        if isinstance(value, _datetime_cls):
            return value.isoformat()
        if isinstance(value, _date_cls):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Mapping):
            return dict(value)
        raise TypeError(
            f"fixture record contains a value that is not JSON-encodable: {type(value).__name__}"
        )

    text = json.dumps(
        record,
        default=_default,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8") + b"\n"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: evaluate ``--input PATH`` and print the fixture JSON."""

    parser = argparse.ArgumentParser(
        prog="evaluate_options_alpha_exact_option_outcome",
        description=(
            "Offline read-only OA-3 exact-option outcome evaluation of one "
            "local handoff manifest (no network, no writes, no clock reads)."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="path to the local OA-3 handoff manifest JSON",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse usage error (2) or --help (0)
        return exc.code if isinstance(exc.code, int) else EXIT_INPUT_ERROR
    try:
        record = evaluate_input(args.input)
    except ManifestInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    sys.stdout.write(fixture_json_bytes(record).decode("utf-8"))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
