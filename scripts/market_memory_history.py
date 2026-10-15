#!/usr/bin/env python3
"""Command line entry points for the historical Market Memory archive.

All archive behaviour lives in ``engine.neuralweb.market_memory_history_archive``;
this module only parses arguments, bounds and validates the build request
document, forwards the four archive callables unchanged, and renders their
results as finite JSON.

Commands:
  build   --input PATH --output PATH
              Assemble a history from a UTF-8 JSON request (<= 128 KiB) and
              write it to a NEW archive directory.
  day     --archive PATH --manifest-sha256 EXACT64 --date YYYY-MM-DD
          [--reveal-outcomes]
              Read one archived market day.
  inspect --archive PATH --manifest-sha256 EXACT64
              Read an archive manifest.

Exit status: ``0`` on success, ``1`` on a supported operational error
(reported as a compact ``{"error": ...}`` JSON document on stderr, never a
traceback), ``2`` for invalid command line usage (handled by argparse).
``KeyboardInterrupt`` and other ``BaseException``s are never swallowed.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

__all__ = ["main", "make_parser"]

# Normal Python script convention: make the checkout root importable so the
# engine package also resolves when this file is executed by path.  Importing
# this module as ``scripts.market_memory_history`` needs no adjustment.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:  # the real archive module exists only inside the commissioned checkout
    from engine.neuralweb.market_memory_history_archive import (
        assemble_history,
        read_day,
        read_manifest,
        write_archive,
    )
except ImportError:  # pragma: no cover - reachable only outside the checkout
    assemble_history = None  # type: ignore[assignment]
    read_day = None  # type: ignore[assignment]
    read_manifest = None  # type: ignore[assignment]
    write_archive = None  # type: ignore[assignment]

_ARCHIVE_CALLABLES = ("assemble_history", "write_archive", "read_manifest", "read_day")
MAX_INPUT_BYTES = 128 * 1024
_SHA256_PATTERN = re.compile(r"\A[0-9a-fA-F]{64}\Z")
_DATE_PATTERN = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


class CliError(Exception):
    """A supported operational refusal that must be reported, not raised."""


def _dumps(payload: object) -> str:
    """Render a compact, key-sorted, strictly finite JSON document."""
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _require_archive_module() -> None:
    missing = sorted(name for name in _ARCHIVE_CALLABLES if globals()[name] is None)
    if missing:
        raise CliError(
            "engine.neuralweb.market_memory_history_archive is unavailable "
            f"(unresolved: {', '.join(missing)})"
        )


def _sha256_argument(text: str) -> str:
    if not _SHA256_PATTERN.match(text):
        raise argparse.ArgumentTypeError(
            "--manifest-sha256 must be exactly 64 hexadecimal characters"
        )
    return text


def _date_argument(text: str) -> str:
    if not _DATE_PATTERN.match(text):
        raise argparse.ArgumentTypeError("--date must be a calendar date as YYYY-MM-DD")
    year, month, day = (int(part) for part in text.split("-"))
    try:
        datetime.date(year, month, day)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--date is not a real calendar date: {exc}") from None
    return text


def _load_request(raw_path: str) -> dict:
    """Read the bounded UTF-8 JSON build request without touching the engine."""
    request_path = Path(raw_path)
    if request_path.is_symlink():
        raise CliError(f"--input is a symlink; refusing: {raw_path}")
    with open(request_path, "rb") as handle:
        payload = handle.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise CliError(
            f"--input exceeds the {MAX_INPUT_BYTES} byte limit ({len(payload)} bytes read)"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliError(f"--input is not valid UTF-8: {exc}") from None
    try:
        request = json.loads(text)
    except ValueError as exc:
        raise CliError(f"--input is not valid JSON: {exc}") from None
    if not isinstance(request, dict):
        raise CliError("--input must contain a JSON object (null and arrays are invalid)")
    return request


def _run_build(args: argparse.Namespace) -> dict:
    _require_archive_module()
    request = _load_request(args.input)
    packet = assemble_history(request)
    if not isinstance(packet, dict):
        raise CliError("assemble_history returned a non-object packet; refusing to archive")
    receipt = write_archive(packet, Path(args.output))
    if not isinstance(receipt, dict):
        raise CliError("write_archive returned a non-object receipt")
    return receipt


def _run_day(args: argparse.Namespace) -> dict:
    _require_archive_module()
    record = read_day(
        Path(args.archive),
        args.date,
        expected_manifest_sha256=args.manifest_sha256,
        reveal_outcomes=args.reveal_outcomes,
    )
    if not isinstance(record, dict):
        raise CliError("read_day returned a non-object record")
    return record


def _run_inspect(args: argparse.Namespace) -> dict:
    _require_archive_module()
    manifest = read_manifest(
        Path(args.archive),
        expected_manifest_sha256=args.manifest_sha256,
    )
    if not isinstance(manifest, dict):
        raise CliError("read_manifest returned a non-object manifest")
    return manifest


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="market_memory_history",
        description="Build and read the historical Market Memory archive.",
    )
    commands = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="{build,day,inspect}",
        required=True,
    )

    build = commands.add_parser(
        "build", help="assemble a history and write it to a new archive directory"
    )
    build.add_argument(
        "--input", required=True, metavar="PATH",
        help="UTF-8 JSON request document, at most 128 KiB",
    )
    build.add_argument(
        "--output", required=True, metavar="PATH",
        help="archive directory to create; it must not already exist",
    )
    build.set_defaults(handler=_run_build)

    day = commands.add_parser("day", help="read one archived market day")
    day.add_argument("--archive", required=True, metavar="PATH", help="archive root directory")
    day.add_argument(
        "--manifest-sha256", required=True, metavar="EXACT64", type=_sha256_argument,
        help="expected manifest SHA-256, exactly 64 hex characters",
    )
    day.add_argument(
        "--date", required=True, metavar="YYYY-MM-DD", type=_date_argument,
        help="market date to read",
    )
    day.add_argument(
        "--reveal-outcomes", action="store_true",
        help="include outcome fields in the returned record",
    )
    day.set_defaults(handler=_run_day)

    inspect = commands.add_parser("inspect", help="read an archive manifest")
    inspect.add_argument("--archive", required=True, metavar="PATH", help="archive root directory")
    inspect.add_argument(
        "--manifest-sha256", required=True, metavar="EXACT64", type=_sha256_argument,
        help="expected manifest SHA-256, exactly 64 hex characters",
    )
    inspect.set_defaults(handler=_run_inspect)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        rendered = _dumps(args.handler(args))
    except (CliError, ValueError, OSError) as exc:
        message = str(exc) or exc.__class__.__name__
        sys.stderr.write(_dumps({"error": message}) + "\n")
        return 1
    sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
