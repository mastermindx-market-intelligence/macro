"""Bounded source-only daily refresh of private BOATS minute-bar history.

One NYSE session per invocation, dry run by default. ``--capture`` performs at
most one archived provider request per explicitly selected symbol for that
session's overnight BOATS window (20:00 ET prior day .. 04:00 ET session day,
which falls inside the session's UTC date under both EST and EDT), retains the
immutable raw response through the existing archive collector first, and only
then builds the exact new receipt and selects its whole session window over
the prior private history. Older windows and immutable raw vintages remain intact.

No scheduler, publication, activation, retry or substitute collector logic
lives here. Existing private inputs are never modified. Every effect lands in
one new private output directory guarded by an exclusively created start
receipt, so crashed or uncertain work cannot silently replay. A final compact
manifest lists exact output hashes, bar counts, empty/unavailable symbols and
complete_history=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCHEMA = "terminal.tiingo_boats_history_refresh.v1"
HISTORY_SCHEMA = "terminal.tiingo_boats_history.v1"
SOURCE = "boats-bars"
RESAMPLE = "1min"
COLUMNS = "open,high,low,close,volume"
ET = ZoneInfo("America/New_York")
UTC = timezone.utc

MIN_ARCHIVE_FREE = 40 * 1024**3            # capture reserve: >= 40 GiB
MAX_SYMBOLS = 20_000
MAX_SYMBOL_FILE_BYTES = 1_000_000
MAX_HISTORY_FILE_BYTES = 32 * 1024 * 1024
MAX_RECEIPT_FILES = 200_000
MAX_RECEIPT_FILE_BYTES = 1_000_000
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024

SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,31}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
DAY = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

START_RECEIPT = "start-receipt.json"
RESULT_RECEIPT = "result-receipt.json"
ERROR_RECEIPT = "error-receipt.json"
MANIFEST = "manifest.json"


class RefreshRefused(RuntimeError):
    """Explicit pre-effect refusal; no provider call or output was made."""


# --------------------------------------------------------------------------- #
# Small private-file primitives. All outputs are new bounded regular files.   #
# --------------------------------------------------------------------------- #

def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as fp:
        fp.write(data)
        fp.flush()
        os.fsync(fp.fileno())


def _read_regular(path: Path, limit: int) -> bytes:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise OSError("refusing symlink input")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise OSError("input is not a bounded regular file")
        chunks, remaining = [], limit + 1
        while remaining > 0:
            chunk = os.read(fd, min(1 << 20, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(fd)
    data = b"".join(chunks)
    if len(data) > limit:
        raise OSError("input exceeds bounded size")
    return data


def _refuse_public_tree(path: Path) -> None:
    parts = path.absolute().parts
    if "public" in parts or "site" in parts:
        raise RefreshRefused("path must remain a private delivery candidate")


# --------------------------------------------------------------------------- #
# Session calendar: real NYSE session check plus the overnight window bounds. #
# --------------------------------------------------------------------------- #

def is_nyse_session(day: str) -> bool:
    """Existing lib.nyse_calendar remains the session authority (lazy import)."""
    from lib.nyse_calendar import is_session
    return bool(is_session(date.fromisoformat(day)))


def _now_et() -> datetime:
    return datetime.now(ET)


def window_utc_bounds(session: str) -> tuple[datetime, datetime]:
    """UTC bounds of the BOATS overnight window for one session date.

    20:00 ET (prior day) .. 04:00 ET (session day) lands inside the session's
    UTC date under both EST and EDT; a regime where that stops holding is a
    refusal, never a silent off-by-one-day request.
    """
    day = date.fromisoformat(session)
    start = datetime.combine(day - timedelta(days=1), dt_time(20, 0), ET).astimezone(UTC)
    end = datetime.combine(day, dt_time(4, 0), ET).astimezone(UTC)
    if start.date().isoformat() != session or end.date().isoformat() != session:
        raise RefreshRefused("BOATS overnight window does not map onto session UTC date")
    return start, end


def session_gate(session: str, *, session_check: Callable, now: datetime) -> dict:
    end = session_end_et(session)
    return {"is_session": bool(session_check(session)), "window_closed": now >= end,
            "end_et": end.isoformat(), "now_et": now.astimezone(ET).isoformat()}


def session_end_et(session: str) -> datetime:
    return window_utc_bounds(session)[1]


# --------------------------------------------------------------------------- #
# Dependency seams. Defaults reach the existing collectors/builders through   #
# lazy imports; tests inject fakes without importing repository modules.      #
# --------------------------------------------------------------------------- #

def _default_archive(root: Path, *, check_mount: bool = True):
    from collectors.tiingo_archive import Archive, MIN_FREE_BYTES
    return Archive(root, check_mount=check_mount,
                   free_floor=max(MIN_FREE_BYTES, MIN_ARCHIVE_FREE))


def _default_request_path(symbol: str, session: str) -> str:
    from collectors.tiingo_archive import request_path
    return request_path(SOURCE, symbol, {"resampleFreq": RESAMPLE,
                                         "startDate": session, "endDate": session,
                                         "columns": COLUMNS})


def _default_fetch(path: str, key: str, *, max_bytes: int) -> tuple[bytes, str]:
    from collectors.tiingo_archive import fetch_json_bytes
    return fetch_json_bytes(path, key, max_bytes=max_bytes)


def _default_read_key() -> str:
    from collectors.tiingo_archive import read_key
    return read_key()


def _default_materialize(root: Path, receipt: dict, *, free_floor: int) -> dict:
    from scripts.tiingo_materialize import materialize_one
    return materialize_one(root, receipt, free_floor=free_floor)


def _default_build_history(symbol: str, refs: list[tuple[str, str]], *, root: Path,
                           check_mount: bool,
                           receipt_paths: dict[tuple[str, str], Path]) -> dict:
    from scripts.tiingo_chart_history import build_chart_history
    return build_chart_history(symbol, refs, root=root, check_mount=check_mount,
                               receipt_paths=receipt_paths)


@dataclass
class RefreshDeps:
    """Late-bound seams so tests and callers can inject isolated fakes."""

    archive_factory: Callable = field(default_factory=lambda: _default_archive)
    request_path: Callable = field(default_factory=lambda: _default_request_path)
    fetch: Callable = field(default_factory=lambda: _default_fetch)
    read_key: Callable = field(default_factory=lambda: _default_read_key)
    materialize: Callable = field(default_factory=lambda: _default_materialize)
    build_history: Callable = field(default_factory=lambda: _default_build_history)
    session_check: Callable = field(default_factory=lambda: is_nyse_session)
    clock: Callable = field(default_factory=lambda: _now_et)


@dataclass
class RefreshConfig:
    session: str
    symbols_path: Path
    history_dir: Path
    output_dir: Path
    root: Path
    capture: bool = False
    max_requests: int | None = None
    max_total_bytes: int | None = None
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    check_mount: bool = True


# --------------------------------------------------------------------------- #
# Bounded input parsing, all of it pre-effect.                                #
# --------------------------------------------------------------------------- #

def _validate_session(session: str) -> None:
    if not isinstance(session, str) or not DAY.fullmatch(session):
        raise RefreshRefused("session must be YYYY-MM-DD")
    try:
        window_utc_bounds(session)
    except ValueError as exc:
        raise RefreshRefused(f"invalid session date: {exc}") from None


def _load_symbols(path: Path) -> list[str]:
    try:
        raw = _read_regular(path, MAX_SYMBOL_FILE_BYTES)
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise RefreshRefused(f"symbols file unreadable: {exc}") from None
    symbols: list[str] = []
    for line in text.splitlines():
        token = line.strip()
        if not token or token.startswith("#"):
            continue
        if not SYMBOL.fullmatch(token):
            raise RefreshRefused(f"invalid vendor ticker in symbols file: {token!r}")
        if token not in symbols:
            symbols.append(token)
    if not symbols:
        raise RefreshRefused("symbols file selects no symbols")
    if len(symbols) > MAX_SYMBOLS:
        raise RefreshRefused(f"symbols file exceeds {MAX_SYMBOLS} symbols")
    return symbols


def _check_dirs(cfg: RefreshConfig) -> None:
    _refuse_public_tree(cfg.output_dir)
    _refuse_public_tree(cfg.history_dir)
    history = cfg.history_dir
    if history.is_symlink() or not history.is_dir():
        raise RefreshRefused("existing private chart-history directory required")
    out = cfg.output_dir.absolute()
    hist = history.absolute()
    if out == hist or out.is_relative_to(hist):
        raise RefreshRefused("output directory must not live inside the history tree")


def _prior_history(path: Path, symbol: str
                   ) -> tuple[dict, list[tuple[str, str]], bytes] | tuple[None, None, str]:
    """Read one immutable prior history file; never write or repair it.

    A missing file is a first refresh, not an error; an unreadable or foreign
    existing file is an explicit refusal (refs None) for that symbol only.
    """
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return (None, [], b"")
    if stat.S_ISLNK(st.st_mode):
        return (None, None, "prior_history_symlink")
    try:
        data = _read_regular(path, MAX_HISTORY_FILE_BYTES)
        doc = json.loads(data)
    except (OSError, UnicodeError, ValueError):
        return (None, None, "prior_history_unreadable")
    if not isinstance(doc, dict) or doc.get("symbol") != symbol:
        return (None, None, "prior_history_symbol_mismatch")
    if doc.get("schema") != HISTORY_SCHEMA or not isinstance(doc.get("bars"), list):
        return (None, None, "prior_history_schema_invalid")
    receipts = doc.get("receipts")
    if not isinstance(receipts, list):
        return (None, None, "prior_history_receipts_invalid")
    refs: list[tuple[str, str]] = []
    for entry in receipts:
        rid = entry.get("receipt_id") if isinstance(entry, dict) else None
        observed = entry.get("observed_at_utc") if isinstance(entry, dict) else None
        day = observed[:10] if isinstance(observed, str) else None
        if (not isinstance(rid, str) or not SHA.fullmatch(rid)
                or not isinstance(day, str) or not DAY.fullmatch(day)):
            return (None, None, "prior_history_receipt_invalid")
        refs.append((day, rid))
    if len(set(refs)) != len(refs):
        return (None, None, "prior_history_duplicate_receipt")
    return (doc, refs, data)


def index_receipts(root: Path, days: set[str] | None = None) -> tuple[dict[str, Path], dict]:
    """One bounded pass over the boats-bars receipt tree, once per capture day.

    Receipt identity is content-addressed, so each receipt file is read once
    here instead of rescanning thousands of receipts per symbol later.
    """
    base = Path(root) / "receipts" / SOURCE
    found: dict[str, Path] = {}
    stats = {"days": 0, "files": 0, "skipped": 0}
    if not base.is_dir():
        return found, stats
    for day_dir in sorted(base.iterdir()):
        if days is not None and day_dir.name not in days:
            continue
        if day_dir.is_symlink() or not day_dir.is_dir():
            stats["skipped"] += 1
            continue
        stats["days"] += 1
        day_files = 0
        for entry in sorted(day_dir.iterdir()):
            day_files += 1
            if day_files > MAX_RECEIPT_FILES:
                raise RefreshRefused("receipt day exceeded bounded scan")
            try:
                receipt = json.loads(_read_regular(entry, MAX_RECEIPT_FILE_BYTES))
            except (OSError, UnicodeError, ValueError):
                stats["skipped"] += 1
                continue
            rid = receipt.get("receipt_id") if isinstance(receipt, dict) else None
            stats["files"] += 1
            if isinstance(rid, str) and SHA.fullmatch(rid):
                found[rid] = entry
    return found, stats


# --------------------------------------------------------------------------- #
# Orchestration.                                                              #
# --------------------------------------------------------------------------- #

def _prepare_output_dir(cfg: RefreshConfig) -> None:
    if cfg.output_dir.exists() or cfg.output_dir.is_symlink():
        raise RefreshRefused("output directory already exists; no silent replay")
    parent = cfg.output_dir.parent
    if parent.is_symlink():
        raise RefreshRefused("output parent is a symlink")
    os.mkdir(cfg.output_dir, 0o700)
    _refuse_public_tree(cfg.output_dir)


def _capture_budget_ok(cfg: RefreshConfig, made: int, used: int) -> bool:
    assert cfg.max_requests is not None and cfg.max_total_bytes is not None
    if made >= cfg.max_requests:
        return False
    return used + cfg.max_response_bytes <= cfg.max_total_bytes


def run_refresh(cfg: RefreshConfig, deps: RefreshDeps) -> tuple[dict, int]:
    """Return (manifest, exit_code); 0 complete, 3 explicit partial outcome."""
    _validate_session(cfg.session)
    if cfg.max_requests is not None and cfg.max_requests < 1:
        raise RefreshRefused("max_requests must be positive")
    if cfg.max_total_bytes is not None and cfg.max_total_bytes < 1:
        raise RefreshRefused("max_total_bytes must be positive")
    if cfg.max_response_bytes < 1:
        raise RefreshRefused("max_response_bytes must be positive")
    _check_dirs(cfg)
    symbols = _load_symbols(cfg.symbols_path)
    if cfg.capture:
        if cfg.max_requests is None or cfg.max_total_bytes is None:
            raise RefreshRefused("capture requires explicit request and byte budgets")
        if len(symbols) > cfg.max_requests:
            raise RefreshRefused("selected symbols exceed max_requests budget")
    prior = {s: _prior_history(cfg.history_dir / f"{s}.json", s) for s in symbols}
    now = deps.clock().astimezone(UTC)
    try:
        gate = session_gate(cfg.session, session_check=deps.session_check, now=now)
    except ImportError as exc:
        if cfg.capture:
            raise RefreshRefused(f"session calendar unavailable: {exc}") from None
        end = session_end_et(cfg.session)
        gate = {"is_session": None, "window_closed": now >= end,
                "end_et": end.isoformat(), "now_et": now.astimezone(ET).isoformat(),
                "calendar": "unavailable"}

    manifest: dict[str, Any] = {
        "schema": SCHEMA, "session": cfg.session, "mode": "capture" if cfg.capture else "dry_run",
        "gate": gate, "activated": False, "complete_history": False,
        "budgets": {"max_requests": cfg.max_requests,
                    "max_total_bytes": cfg.max_total_bytes,
                    "reserved_per_request": cfg.max_response_bytes},
        "symbols": symbols, "outputs": [], "unavailable": [], "not_requested": [],
    }
    for symbol, (doc, refs, err) in prior.items():
        if refs is None:  # existing but unreadable/foreign prior history
            manifest["unavailable"].append({"symbol": symbol, "reason": err, "stage": "input"})

    if not cfg.capture:
        manifest["requests_planned"] = len(symbols)
        manifest["output_dir_exists"] = bool(cfg.output_dir.exists())
        manifest["runnable"] = bool(gate["is_session"] and gate["window_closed"])
        return manifest, 0

    if not gate["is_session"]:
        raise RefreshRefused("session date is not an NYSE session")
    if not gate["window_closed"]:
        raise RefreshRefused("session BOATS window has not ended (04:00 America/New_York)")

    _prepare_output_dir(cfg)
    try:
        return _run_capture(cfg, deps, symbols, prior, manifest)
    except Exception as exc:  # error receipt, then re-raise; never a fake success
        _write_private(cfg.output_dir / ERROR_RECEIPT, (
            json.dumps({"schema": SCHEMA + ".error", "session": cfg.session,
                        "error": type(exc).__name__, "detail": str(exc)[:500],
                        "at_utc": datetime.now(UTC).isoformat()},
                       separators=(",", ":")) + "\n").encode())
        raise


def _run_capture(cfg: RefreshConfig, deps: RefreshDeps, symbols: list[str],
                 prior: dict, manifest: dict) -> tuple[dict, int]:
    started = datetime.now(UTC).isoformat()
    digest = hashlib.sha256("\n".join(symbols).encode()).hexdigest()
    _write_private(cfg.output_dir / START_RECEIPT, (
        json.dumps({"schema": SCHEMA + ".start", "session": cfg.session,
                    "started_at_utc": started, "symbols": len(symbols),
                    "symbols_sha256": digest, "budgets": manifest["budgets"]},
                   separators=(",", ":")) + "\n").encode())

    archive = deps.archive_factory(cfg.root, check_mount=cfg.check_mount)
    key = deps.read_key()
    free_floor = getattr(archive, "free_floor", MIN_ARCHIVE_FREE)

    captured: dict[str, tuple[bytes, dict, str, Any]] = {}
    made = used = 0
    print(json.dumps({"event": "capture_started", "session": cfg.session,
                      "symbols": len(symbols), "budgets": manifest["budgets"]}), file=sys.stderr, flush=True)
    for index, symbol in enumerate(symbols):
        if not _capture_budget_ok(cfg, made, used):
            manifest["not_requested"].extend(symbols[index:])
            break
        path = deps.request_path(symbol, cfg.session)
        # Reserve each attempt before calling the provider. A restart leaves an
        # explicit uncertain request instead of losing the in-flight boundary.
        _write_private(cfg.output_dir / f"attempt-{index + 1:05d}.json", (
            json.dumps({"symbol": symbol, "request_path": path, "ordinal": index + 1},
                       separators=(",", ":")) + "\n").encode())
        made += 1  # a provider attempt consumes the request budget, failure or not
        try:
            raw, mime = deps.fetch(path, key, max_bytes=cfg.max_response_bytes)
        except Exception as exc:
            manifest["unavailable"].append(
                {"symbol": symbol, "reason": f"provider_unavailable: {type(exc).__name__}: {exc}"[:300],
                 "stage": "capture"})
            from collectors.tiingo_archive import TiingoArchiveError
            if (isinstance(exc, TiingoArchiveError)
                    and str(exc) == "Tiingo HTTP 404; source not admitted"):
                # An unavailable ticker does not suppress other tickers. Auth,
                # capacity and transport failures still stop this entire run.
                continue
            manifest["not_requested"].extend(symbols[index + 1:])
            break
        used += len(raw)
        # Immutable raw retention always precedes any normalization attempt.
        try:
            saved = archive.store_response(SOURCE, symbol, path, raw, content_type=mime)
        except Exception as exc:
            manifest["unavailable"].append(
                {"symbol": symbol, "reason": f"archive_store_failed: {type(exc).__name__}: {exc}"[:300],
                 "stage": "capture"})
            manifest["not_requested"].extend(symbols[index + 1:])
            break
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = None
        if not isinstance(parsed, list):
            manifest["unavailable"].append({"symbol": symbol, "reason": "response_shape_not_list",
                                            "stage": "capture"})
            manifest["not_requested"].extend(symbols[index + 1:])
            break
        _write_private(cfg.output_dir / f"captured-{index + 1:05d}.json", (
            json.dumps({"symbol": symbol, "request_path": path, **saved},
                       separators=(",", ":")) + "\n").encode())
        captured[symbol] = (raw, saved, path, parsed)
        if made % 100 == 0:
            print(json.dumps({"event": "capture_progress", "attempted": made,
                              "archived": len(captured), "bytes": used}), file=sys.stderr, flush=True)

    manifest["requests"] = {"made": made, "limit": cfg.max_requests}
    manifest["bytes"] = {"used": used, "limit": cfg.max_total_bytes}
    print(json.dumps({"event": "capture_complete", "attempted": made,
                      "archived": len(captured), "bytes": used}), file=sys.stderr, flush=True)
    receipt_days = {day for _doc, refs, _raw in prior.values() for day, _ in (refs or [])}
    receipt_days.update(str(saved.get("observed_at_utc", started))[:10]
                        for _raw, saved, _path, _parsed in captured.values())
    index, index_stats = index_receipts(cfg.root, receipt_days)
    manifest["receipt_index"] = index_stats

    for symbol in symbols:
        if symbol not in captured:
            continue
        _raw, saved, _path, parsed = captured[symbol]
        rid = saved["receipt_id"]
        if rid not in index:
            manifest["unavailable"].append({"symbol": symbol, "reason": "new_receipt_not_indexed",
                                            "stage": "normalize"})
            continue
        try:
            receipt = json.loads(_read_regular(index[rid], MAX_RECEIPT_FILE_BYTES))
            deps.materialize(cfg.root, receipt, free_floor=free_floor)
        except Exception as exc:
            manifest["unavailable"].append(
                {"symbol": symbol, "reason": f"materialize_failed: {type(exc).__name__}: {exc}"[:300],
                 "stage": "normalize"})
            continue
        doc, prior_refs, prior_bytes = prior[symbol]
        if prior_refs is None:  # prior history refused: already listed at input stage
            continue
        if not parsed and doc is None:
            manifest["outputs"].append(
                {"symbol": symbol, "status": "vendor_empty", "bars": 0,
                 "prior_receipts": 0, "new_receipt": rid})
            continue
        new_day = str(receipt.get("observed_at_utc", ""))[:10]
        if not DAY.fullmatch(new_day):
            manifest["unavailable"].append({"symbol": symbol, "reason": "new_receipt_day_invalid",
                                            "stage": "normalize"})
            continue
        refs = [(new_day, rid)]
        hints: dict[tuple[str, str], Path] = {}
        for ref in refs:
            located = index.get(ref[1])
            if located is None:
                manifest["unavailable"].append(
                    {"symbol": symbol, "reason": f"receipt_not_found_in_archive: {ref[1]}",
                     "stage": "normalize"})
                break
            hints[ref] = located
        else:
            try:
                from scripts.boats_history_window import CONSTANTS, merge_session_window
                if parsed:
                    update = deps.build_history(symbol, refs, root=cfg.root,
                                                check_mount=cfg.check_mount, receipt_paths=hints)
                else:
                    update = {**CONSTANTS, "symbol": symbol, "bars": [], "bar_receipt_ids": [],
                              "receipts": [{k: receipt[k] for k in
                                           ("receipt_id", "raw_sha256", "observed_at_utc", "request_path")}]}
                result = merge_session_window(doc, update, cfg.session)
                payload = (json.dumps(result, separators=(",", ":"),
                                      allow_nan=False) + "\n").encode()
                _write_private(cfg.output_dir / f"{symbol}.json", payload)
            except Exception as exc:
                manifest["unavailable"].append(
                    {"symbol": symbol,
                     "reason": f"rebuild_refused: {type(exc).__name__}: {exc}"[:300],
                     "stage": "normalize"})
                continue
            manifest["outputs"].append(
                {"symbol": symbol, "file": f"{symbol}.json", "status": "rebuilt" if parsed else "refreshed_empty_window",
                 "bars": len(result.get("bars", [])), "complete": bool(result.get("complete", False)),
                 "prior_receipts": len(prior_refs), "new_receipt": rid,
                 "receipts": len(result.get("receipts", [])),
                 "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})

    complete = not manifest["unavailable"] and not manifest["not_requested"]
    manifest["status"] = "complete" if complete else "partial"
    payload = (json.dumps(manifest, separators=(",", ":"), allow_nan=False) + "\n").encode()
    _write_private(cfg.output_dir / MANIFEST, payload)
    _write_private(cfg.output_dir / RESULT_RECEIPT, (
        json.dumps({"schema": SCHEMA + ".result", "session": cfg.session,
                    "status": manifest["status"], "outputs": len(manifest["outputs"]),
                    "unavailable": len(manifest["unavailable"]),
                    "not_requested": len(manifest["not_requested"]),
                    "finished_at_utc": datetime.now(UTC).isoformat()},
                   separators=(",", ":")) + "\n").encode())
    return manifest, (0 if complete else 3)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, help="NYSE session date YYYY-MM-DD")
    parser.add_argument("--symbols", required=True, type=Path,
                        help="explicit uppercase symbol text file")
    parser.add_argument("--history-dir", required=True, type=Path,
                        help="existing private chart-history directory (immutable input)")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new private output directory; never overwrites")
    parser.add_argument("--root", required=True, type=Path, help="external archive root")
    parser.add_argument("--capture", action="store_true",
                        help="perform archived provider requests (default: dry run)")
    parser.add_argument("--max-requests", type=int, help="explicit request budget")
    parser.add_argument("--max-total-bytes", type=int, help="explicit cumulative byte budget")
    parser.add_argument("--max-response-bytes", type=int, default=DEFAULT_MAX_RESPONSE_BYTES)
    args = parser.parse_args(argv)
    cfg = RefreshConfig(session=args.session, symbols_path=args.symbols,
                        history_dir=args.history_dir, output_dir=args.output_dir,
                        root=args.root, capture=args.capture, max_requests=args.max_requests,
                        max_total_bytes=args.max_total_bytes,
                        max_response_bytes=args.max_response_bytes)
    try:
        manifest, code = run_refresh(cfg, RefreshDeps())
    except RefreshRefused as exc:
        print(json.dumps({"schema": SCHEMA, "refused": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:  # error receipt already persisted where possible
        print(json.dumps({"schema": SCHEMA, "error": type(exc).__name__,
                          "detail": str(exc)[:300]}), file=sys.stderr)
        return 4
    print(json.dumps(manifest, separators=(",", ":"), allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
