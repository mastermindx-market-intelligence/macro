#!/usr/bin/env python3
"""Command line entry points for the historical Market Memory archive.

All archive behaviour lives in ``engine.neuralweb.market_memory_history_archive``;
this module only parses arguments, bounds and validates the build request
document, composes existing read/export consumers, and renders their
results as finite JSON.

Commands:
  extend --archive PATH --manifest-sha256 EXACT64 --input NEXT_REQUEST --output NEW_DIR
              Preserve the entire existing historical state and publish only
              genuinely new dates as a separately hash-bound generation.
  build   --input PATH --output PATH
              Assemble a history from a UTF-8 JSON request (<= 128 KiB) and
              write it to a NEW archive directory.
  day     --archive PATH --manifest-sha256 EXACT64 --date YYYY-MM-DD
          [--reveal-outcomes]
              Read one archived market day.
  inspect --archive PATH --manifest-sha256 EXACT64
              Read an archive manifest.
  dossier --archive PATH --manifest-sha256 EXACT64 --date YYYY-MM-DD
          [--macro PATH --macro-sha256 EXACT64] [--reveal-outcomes]
              Join the exact market day and optional first-print chronology.
  export --archive PATH --manifest-sha256 EXACT64 --output NEW_HTML
          [--macro PATH --macro-sha256 EXACT64] [--include-outcomes]
              Produce a private offline browser. Default export has no outcomes.

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
# Always pin ahead of ambient or sibling-repository import paths.
sys.path.insert(0, str(_REPO_ROOT))

try:  # the real archive module exists only inside the commissioned checkout
    from engine.neuralweb.market_memory_history_archive import (
        assemble_history,
        read_day,
        read_manifest,
        write_archive,
    )
    from engine.neuralweb.market_memory_history_dossier import build_daily_dossier
    from engine.neuralweb.market_memory_history_view import export_browser
    from engine.neuralweb.market_memory_history_extend import extend_archive
except ImportError:
    assemble_history = None  # type: ignore[assignment]
    read_day = None  # type: ignore[assignment]
    read_manifest = None  # type: ignore[assignment]
    write_archive = None  # type: ignore[assignment]
    build_daily_dossier = None  # type: ignore[assignment]
    export_browser = None  # type: ignore[assignment]
    extend_archive = None  # type: ignore[assignment]

_ARCHIVE_CALLABLES = ("assemble_history", "write_archive", "read_manifest", "read_day",
                      "build_daily_dossier", "export_browser", "extend_archive")
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
    return text.lower()


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


def _run_extend(args: argparse.Namespace) -> dict:
    _require_archive_module()
    request = _load_request(args.input)
    return extend_archive(Path(args.archive), request, Path(args.output),
                          expected_parent_manifest_sha256=args.manifest_sha256)


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


def _macro_binding(args: argparse.Namespace) -> dict:
    if (args.macro is None) != (args.macro_sha256 is None):
        raise CliError("macro path and exact source digest must be supplied together")
    return {"macro_path":Path(args.macro) if args.macro is not None else None,
            "expected_macro_sha256":args.macro_sha256}


def _filing_binding(args: argparse.Namespace) -> dict:
    if (args.filings is None) != (args.filings_sha256 is None):
        raise CliError("filing path and exact source digest must be supplied together")
    if args.filings is None:
        if getattr(args, "filings_offset", 0) != 0:
            raise CliError("a filing offset requires the selected filing source")
        return {}
    result = {"filings_path": Path(args.filings), "expected_filings_sha256": args.filings_sha256}
    if hasattr(args, "filings_offset"):
        result["filings_offset"] = args.filings_offset
    return result


def _run_dossier(args: argparse.Namespace) -> dict:
    _require_archive_module()
    binding=_macro_binding(args)
    return build_daily_dossier(Path(args.archive),args.date,
        expected_manifest_sha256=args.manifest_sha256,
        reveal_outcomes=args.reveal_outcomes,**binding,**_filing_binding(args))


def _run_transcripts_catalog(args: argparse.Namespace) -> dict:
    from lib.dataos.web_workspace import load_workspace_config, WorkspaceError
    from lib.dataos.web_history import _transcript_binding
    from engine.neuralweb.market_memory_history_transcripts import read_transcript_catalog, MAX_METADATA_BYTES
    from engine.neuralweb.market_memory_history_archive import _bytes, _write_exclusive
    destination=Path(args.output)
    if destination.exists():raise FileExistsError(destination)
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise CliError('catalogue output cannot traverse symlinks')
    try:
        workspace=load_workspace_config(Path(args.config))
        _transcript_binding(workspace,args.ref,args.expected_version)
        with workspace._file(args.ref,args.expected_version) as (stream,source):
            catalog=read_transcript_catalog(stream,file_bytes=source['file_bytes'],
                source_ref=args.ref,source_version=source['file_version'])
        # The existing source descriptor guard has closed before output creation.
    except WorkspaceError as exc:
        raise CliError(exc.code) from None
    raw=_bytes(catalog)
    if len(raw)>MAX_METADATA_BYTES:raise CliError('transcript catalogue exceeds byte budget')
    _write_exclusive(destination,raw)
    import hashlib
    return {'schema':'market_memory.transcript_catalog_receipt.v1','records':len(catalog['rows']),
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'source_ref':args.ref,
        'source_version':args.expected_version,'body_columns_read':False,'source_written':False,
        'point_in_time_eligible':False,'public_publication':False}


def _run_export(args: argparse.Namespace) -> dict:
    _require_archive_module()
    binding=_macro_binding(args)
    catalog={}
    if (args.transcripts_catalog is None)!=(args.transcripts_catalog_sha256 is None):
        raise CliError('transcript catalogue path and exact digest must be supplied together')
    if args.transcripts_catalog is not None:
        catalog={'transcripts_catalog_path':Path(args.transcripts_catalog),
                 'expected_transcripts_catalog_sha256':args.transcripts_catalog_sha256}
    return export_browser(Path(args.archive),Path(args.output),
        expected_manifest_sha256=args.manifest_sha256,
        include_outcomes=args.include_outcomes,**binding,**_filing_binding(args),**catalog)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="market_memory_history",
        description="Build and read the historical Market Memory archive.",
    )
    commands = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="{build,extend,day,inspect,dossier,export,transcripts-catalog}",
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

    extension = commands.add_parser("extend", help="append new dates into a new immutable generation")
    extension.add_argument("--archive", required=True, metavar="PATH", help="exact parent archive")
    extension.add_argument("--manifest-sha256", required=True, type=_sha256_argument, metavar="EXACT64")
    extension.add_argument("--input", required=True, metavar="PATH", help="explicit next source-reference request")
    extension.add_argument("--output", required=True, metavar="PATH", help="new archive; never overwrite the parent")
    extension.set_defaults(handler=_run_extend)

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
    for name,help_text,handler in (
            ("dossier","read a source-bound daily market and macro dossier",_run_dossier),
            ("export","create a private offline browser with explicit source evidence",_run_export)):
        consumer=commands.add_parser(name,help=help_text)
        consumer.add_argument("--archive",required=True,metavar="PATH")
        consumer.add_argument("--manifest-sha256",required=True,type=_sha256_argument,metavar="EXACT64")
        consumer.add_argument("--macro",metavar="PATH",help="optional retained first-print chronology")
        consumer.add_argument("--macro-sha256",type=_sha256_argument,metavar="EXACT64")
        consumer.add_argument("--filings",metavar="PATH",help="optional retained earnings_8k_dates.parquet")
        consumer.add_argument("--filings-sha256",type=_sha256_argument,metavar="EXACT64")
        if name=="dossier":
            consumer.add_argument("--date",required=True,type=_date_argument,metavar="YYYY-MM-DD")
            consumer.add_argument("--filings-offset",type=int,default=0,help="matched filing-record offset")
            consumer.add_argument("--reveal-outcomes",action="store_true")
        else:
            consumer.add_argument("--output",required=True,metavar="NEW_HTML")
            consumer.add_argument("--transcripts-catalog", default=None, metavar="PATH", help="metadata-only transcript catalogue")
            consumer.add_argument("--transcripts-catalog-sha256", default=None, type=_sha256_argument, metavar="EXACT64")
            consumer.add_argument("--include-outcomes",action="store_true",
                                 help="embed future outcomes for explicit educational reveal; not blind evaluation")
        consumer.set_defaults(handler=handler)
    catalog=commands.add_parser("transcripts-catalog", help="export bound transcript metadata only; no call bodies")
    catalog.add_argument("--config", required=True, metavar="HOST_CONFIG")
    catalog.add_argument("--ref", required=True, metavar="BOUND_REF")
    catalog.add_argument("--expected-version", required=True, metavar="OBSERVED_FILE_VERSION")
    catalog.add_argument("--output", required=True, metavar="NEW_PATH")
    catalog.set_defaults(handler=_run_transcripts_catalog)
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
