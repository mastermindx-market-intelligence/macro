#!/usr/bin/env python3
"""Qualify a caller-supplied R2 price capture for the systematic backtester.

Reads ONE capture directory and ONE receipt, verifies them against their own
declared sizes and digests and against the live dataset registry, and writes ONE
explicitly chosen JSON qualification document.

This script performs no network access, contacts no account, writes no ledger,
creates no source of price authority and has no default output path: the caller
names where the diagnostic document goes.  Sources are opened read-only, and an
object that changes between its before-read and after-read observation is a
failure, not a warning.

Usage:
    python -m scripts.qualify_systematic_inputs \
        --capture-root /path/to/capture \
        --output /path/to/qualification.json \
        --as-of 2026-10-22T19:05:00Z \
        --expected-session 2026-10-21

Run: python -m pytest tests/test_systematic_inputs.py -q
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Mapping

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.systematic_inputs import (  # noqa: E402
    DEFAULT_MAX_OBJECT_BYTES,
    DEFAULT_JUMP_FRACTION,
    MODE_CURRENT,
    MODE_HISTORICAL_RECONSTRUCTION,
    SCHEMA,
    CaptureError,
    QualificationInputs,
    _aware,
    loads_strict,
    parse_manifest,
    qualify_systematic_inputs,
    read_frame,
    read_object_bytes,
    resolve_capture_path,
)
from lib.dataos.registry import RegistryError, load_registry  # noqa: E402

DEFAULT_RECEIPT_NAME = "receipt.json"
DEFAULT_PRICE_DATASET = "equity.bars.daily.massive"
DEFAULT_ACTION_DATASET = "reference.corporate_actions.massive_split_evidence"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_INTEGRITY = 3


def _symbol_from_key(object_key: str) -> str:
    """Derive the declared instrument symbol from a declared key's basename."""
    return object_key.rsplit("/", 1)[-1].rsplit(".", 1)[0].upper()


def _read_json_evidence(path: Path | None, *, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise CaptureError(f"ACTION_EVIDENCE_MALFORMED: {label} file not found: {path}")
    document = loads_strict(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise CaptureError(f"ACTION_EVIDENCE_MALFORMED: {label} must be a JSON object")
    return dict(document)


def _write_atomic(path: Path, payload: str) -> str:
    """Write *payload* atomically; a byte-identical existing file is left alone.

    Duplicate-safe: re-running with unchanged inputs does not rewrite the file,
    so a repeated qualification cannot churn the output's mtime.
    """
    data = payload.encode("utf-8")
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise CaptureError(f"OUTPUT_PATH_UNSAFE: {path} is not a regular file")
        if path.read_bytes() == data:
            return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return "written"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qualify_systematic_inputs",
        description="Qualify a caller-supplied price capture (RESEARCH_ONLY, read-only).",
    )
    parser.add_argument("--capture-root", required=True,
                        help="Directory holding the captured objects. Only basenames under "
                             "this root are opened; receipt local_file paths are never trusted.")
    parser.add_argument("--output", required=True,
                        help="Explicit destination for the qualification document. There is "
                             "no default and no production path.")
    parser.add_argument("--receipt", default=None,
                        help=f"Receipt JSON (default: <capture-root>/{DEFAULT_RECEIPT_NAME}).")
    parser.add_argument("--as-of", required=True,
                        help="Offset-aware ISO-8601 evaluation instant. Objects received "
                             "after it are refused.")
    parser.add_argument("--expected-session", default=None,
                        help="The completed US session the caller expects (YYYY-MM-DD). "
                             "Omit it and freshness is reported as not evaluable.")
    parser.add_argument("--mode", choices=[MODE_CURRENT, MODE_HISTORICAL_RECONSTRUCTION],
                        default=MODE_CURRENT,
                        help="current (default) or historical_reconstruction. A historical "
                             "reconstruction is never reported as current freshness.")
    parser.add_argument("--price-dataset", default=DEFAULT_PRICE_DATASET)
    parser.add_argument("--action-dataset", default=DEFAULT_ACTION_DATASET)
    parser.add_argument("--registry", default=None,
                        help="Dataset registry path (default: config/dataset_registry.yml).")
    parser.add_argument("--action-evidence", default=None,
                        help="JSON file of the caller's corporate-action observation, in the "
                             "shape lib.dataos.registry.qualify_action_input consumes.")
    parser.add_argument("--economic-evidence", default=None,
                        help="JSON file declaring the adjustment basis the owner intends to "
                             "use. It does not by itself qualify anything.")
    parser.add_argument("--universe", default=None,
                        help="Comma-separated declared universe. Default: every symbol "
                             "declared by the receipt's object keys.")
    parser.add_argument("--expect-receipt-sha256", default=None,
                        help="If given, the receipt file itself must hash to this value.")
    parser.add_argument("--volume-requires-positive", action="store_true",
                        help="Refuse zero-volume sessions, which the registry records as "
                             "suspected erased missingness.")
    parser.add_argument("--jump-fraction", type=float, default=DEFAULT_JUMP_FRACTION,
                        help="Close-to-close move that raises a SUSPECTED reason only.")
    parser.add_argument("--max-object-bytes", type=int, default=DEFAULT_MAX_OBJECT_BYTES)
    parser.add_argument("--max-total-bytes", type=int, default=2 * 1024 * 1024 * 1024)
    parser.add_argument("--fail-on-blocked", action="store_true",
                        help="Exit non-zero when economic_inputs_ready is false.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    root = Path(args.capture_root)
    receipt_path = Path(args.receipt) if args.receipt else root / DEFAULT_RECEIPT_NAME

    try:
        as_of = _aware(args.as_of, what="--as-of")
        if args.expected_session:
            expected_session = date.fromisoformat(args.expected_session.strip())
        else:
            expected_session = None

        if not receipt_path.is_file():
            raise CaptureError(f"RECEIPT_JSON_INVALID: receipt not found: {receipt_path}")
        receipt_bytes = receipt_path.read_bytes()
        if args.expect_receipt_sha256:
            actual = hashlib.sha256(receipt_bytes).hexdigest()
            if actual != args.expect_receipt_sha256.strip().lower():
                raise CaptureError(
                    f"RECEIPT_HASH_MISMATCH: declared {args.expect_receipt_sha256}, "
                    f"actual {actual}"
                )
        manifest = parse_manifest(receipt_bytes)

        registry = load_registry(args.registry) if args.registry else load_registry()
        price_contract = registry.get(args.price_dataset)
        if price_contract is None:
            raise CaptureError(f"UNREGISTERED_SOURCE: {args.price_dataset} is not registered")

        if args.universe:
            universe = tuple(
                part.strip().upper() for part in args.universe.split(",") if part.strip()
            )
        else:
            universe = tuple(sorted({_symbol_from_key(o.object_key) for o in manifest.objects}))
        if not universe:
            raise CaptureError("RECEIPT_JSON_INVALID: declared universe is empty")

        action_evidence = _read_json_evidence(
            Path(args.action_evidence) if args.action_evidence else None, label="action-evidence"
        )
        economic_evidence = _read_json_evidence(
            Path(args.economic_evidence) if args.economic_evidence else None,
            label="economic-evidence",
        )

        # Read + verify every declared object BEFORE qualifying anything, so a
        # capture that fails integrity never produces a partially-trusted
        # document.  A declared object with no corresponding frame slot is an
        # integrity failure too — the universe is the declared keys.
        frames: dict[str, Any] = {}
        read_records: list[dict[str, Any]] = []
        total = 0
        for obj in manifest.objects:
            path = resolve_capture_path(root, obj.basename)
            if total + obj.bytes > args.max_total_bytes:
                raise CaptureError(
                    f"OBJECT_TOO_LARGE: declared total exceeds --max-total-bytes "
                    f"{args.max_total_bytes}"
                )
            total += obj.bytes
            payload = read_object_bytes(
                path,
                expected_bytes=obj.bytes,
                expected_sha256=obj.sha256,
                max_bytes=args.max_object_bytes,
            )
            frames[_symbol_from_key(obj.object_key)] = read_frame(payload, obj.basename)
            read_records.append(
                {
                    "object_key": obj.object_key,
                    "resolved_name": path.name,
                    "bytes": obj.bytes,
                    "sha256": obj.sha256,
                    "verified": True,
                }
            )

        document = qualify_systematic_inputs(
            QualificationInputs(
                manifest=manifest,
                frames=frames,
                declared_universe=universe,
                as_of=as_of,
                expected_session=expected_session,
                price_contract=price_contract,
                action_dataset_id=args.action_dataset,
                action_evidence=action_evidence,
                economic_evidence=economic_evidence,
                registry=registry,
                mode=args.mode,
                volume_requires_positive=args.volume_requires_positive,
                jump_fraction=args.jump_fraction,
            )
        )
        document["capture"]["objects_verified"] = read_records
        document["capture"]["receipt_file_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()

        payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False)
        state = _write_atomic(Path(args.output), payload)

    except CaptureError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return EXIT_INTEGRITY
    except (RegistryError, FileNotFoundError, ValueError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "output": str(Path(args.output)),
                "write": state,
                "current_data_ready": document["current_data_ready"],
                "economic_inputs_ready": document["economic_inputs_ready"],
                "allowed_use": document["allowed_use"],
                "capital_eligible": document["capital_eligible"],
                "live_orders_enabled": document["live_orders_enabled"],
                "blockers": sorted(
                    set(document["source"]["blockers"])
                    | set(document["actions"]["blockers"])
                    | set(document["economics_blockers"])
                    | {
                        b
                        for inst in document["instruments"]
                        for b in inst["blockers"]
                    }
                ),
            },
            sort_keys=True,
        )
    )
    if args.fail_on_blocked and not document["economic_inputs_ready"]:
        return EXIT_INTEGRITY
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())