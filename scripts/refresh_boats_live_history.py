"""Finite, demand-driven private BOATS history refresh using the incumbent archive.

Run once during a real overnight session. Dry-run is the default. Each selected
symbol receives a single bounded REST attempt, an immutable raw receipt, the
existing normalizer and history builder, then one private SSH snapshot delivery.
Current-session snapshots are whole vendor vintages, never merged trade samples.
The permanent session start receipt prevents replay after a crash or unknown PUT.
This does not start a websocket, alter the quote relay, or install a scheduler.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
import tempfile
from typing import Callable
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors.tiingo_archive import (
    Archive, TiingoArchiveError, fetch_json_bytes, read_key, request_path,
    require_space, receipt_identity,
)
from scripts.build_ext_quotes import boats_session_date
from scripts.boats_history_bridge import (
    INTEREST_SCHEMA, MAX_INTERESTS, MAX_SNAPSHOT, SNAPSHOT_SCHEMA, SYMBOL,
    read_regular, stamp, validate_interest, validate_snapshot, private_directory, PROTOCOL,
)
from scripts.tiingo_chart_history import build_chart_history, TiingoViewRefusal
from scripts.tiingo_materialize import materialize_one

RESERVE = 40 * 1024**3
MAX_REQUESTS = 12_000
MAX_BYTES = 1024**3
MAX_RESPONSE = 256 * 1024
MAX_HOURLY = 1_500
MAX_SECONDS = 8 * 3600
PER_CYCLE = 24
INTERVAL = 60
SCHEMA = "mastermind.boats_live_history_run.v1"


class RefreshStopped(RuntimeError):
    pass


class SymbolDataInvalid(RefreshStopped):
    """Recognized vendor-data failure after immutable raw storage; no retry."""
    def __init__(self, reason: str, raw_bytes: int, receipt_id: str):
        super().__init__(reason)
        self.raw_bytes, self.receipt_id = raw_bytes, receipt_id


class DeliveryUnknown(RefreshStopped):
    """The exact SSH write could have happened; no replay or replacement."""


def reject_nonfinite_json(value: str):
    raise ValueError("non-finite private bridge JSON: " + value)


def write_once(path: Path, document: dict) -> None:
    raw = (json.dumps(document, separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fp:
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        os.link(temporary, path, follow_symlinks=False)  # atomic and never overwrites
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def symbols_from(path: Path, *, allow_empty: bool = False) -> set[str]:
    raw = read_regular(path, 1_000_000).decode("utf8")
    symbols = {line.strip() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    if not (0 if allow_empty else 1) <= len(symbols) <= 20_000 or any(not SYMBOL.fullmatch(s) for s in symbols):
        raise ValueError("invalid bounded coverage/hold file")
    return symbols


@dataclass(frozen=True)
class Config:
    root: Path
    symbols: Path
    held: Path
    capture: bool = False
    max_requests: int = MAX_REQUESTS
    max_bytes: int = MAX_BYTES
    max_seconds: int = MAX_SECONDS
    scheduled: bool = False

    def __post_init__(self):
        for value, cap in ((self.max_requests, MAX_REQUESTS), (self.max_bytes, MAX_BYTES), (self.max_seconds, MAX_SECONDS)):
            if type(value) is not int or not 1 <= value <= cap:
                raise ValueError("invalid finite budget")


class SSHBridge:
    """One existing SSH carrier; no reconnect/retry, credential copying or shell data."""

    def __init__(self, host: str, identity: Path, remote_script: str, remote_root: str):
        if not host or host.startswith("-") or any(c.isspace() for c in host):
            raise ValueError("invalid SSH destination")
        if not Path(remote_script).is_absolute() or not Path(remote_root).is_absolute():
            raise ValueError("absolute private remote paths required")
        self.command = ["ssh", "-i", str(identity), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                        "-o", "ConnectTimeout=10", host,
                        shlex.join(["python3", remote_script, "--root", remote_root])]

    def __call__(self, request: dict) -> dict:
        write = request.get("operation") == "publish"
        try:
            result = subprocess.run(self.command, input=json.dumps(request).encode(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=False)
            if result.returncode or len(result.stdout) > 256 * 1024:
                raise RefreshStopped("private SSH bridge did not return a bounded successful result")
            parsed = json.loads(result.stdout, parse_constant=reject_nonfinite_json)
            if not isinstance(parsed, dict) or parsed.get("protocol") != PROTOCOL:
                raise RefreshStopped("private bridge returned a malformed result")
            return parsed
        except (OSError, ValueError, subprocess.TimeoutExpired, RefreshStopped, KeyboardInterrupt) as exc:
            if write:
                raise DeliveryUnknown("private snapshot write requires same-carrier reconciliation") from exc
            raise RefreshStopped("private interest read failed; no alternate carrier") from exc


def capture_snapshot(symbol: str, session: str, archive: Archive, key: str,
                     fetch: Callable = fetch_json_bytes, *, check_mount: bool = True) -> tuple[dict, int]:
    # Tiingo's date-free endpoint selects the latest overnight session. A
    # trading-date lower bound can exclude its prior-evening bars. Keep the
    # captured-session validation below: a stale/default window is not accepted.
    params = {"resampleFreq": "1min",
              "columns": "open,high,low,close,volume", "forceFill": "false"}
    route = request_path("boats-bars", symbol, params)
    raw, mime = fetch(route, key, max_bytes=MAX_RESPONSE)
    saved = archive.store_response("boats-bars", symbol, route, raw, content_type=mime)
    day = saved["observed_at_utc"][:10]
    # The incumbent archive owns this content-addressed receipt name. Check the
    # exact returned identity before normalization; never choose by newest mtime.
    name = hashlib.sha256(route.encode()).hexdigest()[:16] + "-" + saved["raw_sha256"][:24] + ".json"
    receipt_path = archive.root / "receipts" / "boats-bars" / day / name
    receipt = json.loads(read_regular(receipt_path, 1_000_000))
    if receipt_identity(receipt) != saved["receipt_id"]:
        raise TiingoArchiveError("captured receipt identity mismatch")
    materialized = materialize_one(archive.root, receipt, free_floor=archive.free_floor)
    if materialized["status"] == "EMPTY_NORMALIZED":
        # The strict builder intentionally has no Parquet view for an empty raw
        # array. Preserve its exact receipt in an explicitly empty live snapshot.
        if json.loads(raw) != []:
            raise TiingoArchiveError("empty normalization is not an empty provider array")
        history = {"schema": "terminal.tiingo_boats_history.v1", "symbol": symbol,
                   "source": "tiingo-boats-rest", "venue": "BOATS", "timestamp_basis": "utc",
                   "bar_seconds": 60, "price_basis": "vendor_reported_unqualified",
                   "volume_basis": "vendor_reported_shares", "coverage": "captured_vendor_bars_only",
                   "complete": False, "receipts": [{"receipt_id": saved["receipt_id"],
                   "raw_sha256": saved["raw_sha256"], "observed_at_utc": saved["observed_at_utc"],
                   "request_path": route}], "bars": [], "bar_receipt_ids": []}
    else:
        ref = (day, saved["receipt_id"])
        try:
            history = build_chart_history(symbol, [ref], root=archive.root,
                                          check_mount=check_mount,
                                          receipt_paths={ref: receipt_path})
        except TiingoViewRefusal as exc:
            if str(exc) not in {"missing or non-finite vendor OHLCV", "invalid vendor OHLCV range",
                    "bar lacks source timezone", "bar is not a bounded UTC minute boundary",
                    "BOATS bar outside overnight wall-clock window", "inconsistent vendor OHLC",
                    "duplicate timestamp within source partition"}:
                raise  # custody, raw lineage and storage refusals remain terminal
            raise SymbolDataInvalid(str(exc), len(raw), saved["receipt_id"]) from exc
    observed = stamp(saved["observed_at_utc"])
    if boats_session_date(observed) != session:
        raise TiingoArchiveError("capture completed outside its active overnight session")
    for bar in history["bars"]:
        instant = datetime.fromtimestamp(bar[0], timezone.utc)
        if boats_session_date(instant) != session or instant > observed:
            raise SymbolDataInvalid("provider bar lies outside the captured session or in the future", len(raw), saved["receipt_id"])
    snapshot = {"schema": SNAPSHOT_SCHEMA, "session_date": session,
                "captured_at_utc": saved["observed_at_utc"], "history": history}
    validate_snapshot(snapshot)
    if len(json.dumps(snapshot).encode()) > MAX_SNAPSHOT:
        raise TiingoArchiveError("snapshot exceeds private delivery bound")
    return snapshot, len(raw)


def run(config: Config, bridge: Callable, *, now: Callable = lambda: datetime.now(timezone.utc),
        monotonic: Callable = time.monotonic, sleep: Callable = time.sleep,
        archive_factory: Callable = lambda root: Archive(root, free_floor=RESERVE),
        key_reader: Callable = read_key, capture: Callable = capture_snapshot) -> dict:
    covered, excluded = symbols_from(config.symbols), symbols_from(config.held, allow_empty=True)
    started, started_mono = now(), monotonic()
    session = boats_session_date(started)
    result = {"schema": SCHEMA, "session_date": session, "mode": "capture" if config.capture else "plan",
              "requests": 0, "raw_bytes": 0, "delivered": 0, "held": [], "reason": "plan",
              "complete_history": False, "budget": {"requests": config.max_requests, "raw_bytes": config.max_bytes,
              "seconds": config.max_seconds, "requests_per_hour": MAX_HOURLY},
              "eligible_symbols": len(covered - excluded), "started_at_utc": started.isoformat()}
    if not config.capture:
        return result
    if config.scheduled:
        eastern = started.astimezone(ZoneInfo("America/New_York"))
        if session is None or eastern.hour != 20 or eastern.minute >= 15:
            result["reason"] = "scheduled_candidate_not_due"
            return result
    if session is None:
        raise RefreshStopped("outside a real BOATS overnight session")
    archive = archive_factory(config.root)
    area = archive.root / "run-receipts"
    area.mkdir(mode=0o700, exist_ok=True)
    if area.is_symlink() or not area.resolve().is_relative_to(archive.root):
        raise RefreshStopped("run receipt area escapes the archive")
    lock = os.open(area / "boats-live-history.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        private_directory(area)
        start_path = area / f"boats-live-history-start-{session}.json"
        if start_path.exists():
            raise FileExistsError("session already started; reconcile original operation")
        holds = area / "boats-live-history-held"
        holds.mkdir(mode=0o700, exist_ok=True)
        if holds.is_symlink() or not holds.resolve().is_relative_to(area):
            raise RefreshStopped("hold area escapes run receipts")
        private_directory(holds)
        with os.scandir(holds) as entries:
            for index, entry in enumerate(entries):
                if index >= 20000:
                    raise RefreshStopped("persistent hold bound exceeded")
                if entry.name.startswith("."):
                    # A crash may retain write_once's private temporary. It is
                    # never a published hold; keep it for reconciliation.
                    continue
                symbol = entry.name.removesuffix(".json")
                if entry.name != symbol+".json" or not SYMBOL.fullmatch(symbol):
                    raise RefreshStopped("invalid persistent hold identity")
                held = json.loads(read_regular(Path(entry.path), 4096))
                if not isinstance(held, dict) or held.get("symbol") != symbol or held.get("http_status") != 404:
                    raise RefreshStopped("invalid persistent hold receipt")
                excluded.add(symbol)
        result["eligible_symbols"] = len(covered - excluded)
        key = key_reader()
        initial = bridge({"operation":"read"}) if config.max_bytes >= MAX_RESPONSE else None
        if initial is not None and (not isinstance(initial, dict) or not isinstance(initial.get("interests"), list)
                                    or len(initial["interests"]) > MAX_INTERESTS):
            raise RefreshStopped("invalid preflight interest response")
        write_once(start_path, result)
        run_area = area / f"boats-live-history-{session}"
        run_area.mkdir(mode=0o700)
        last, recent, retained = {}, deque(), set()
        result["newer_retained"] = 0
        failure = None
        try:
            while True:
                tick, wall = monotonic(), now()
                elapsed = tick - started_mono
                if abs((wall - started).total_seconds() - elapsed) > 2 or elapsed < 0:
                    raise RefreshStopped("clock discontinuity")
                if boats_session_date(wall) != session:
                    result["reason"] = "window_closed"
                    break
                if elapsed >= config.max_seconds:
                    result["reason"] = "seconds_budget"
                    break
                if result["requests"] >= config.max_requests or result["raw_bytes"] + MAX_RESPONSE > config.max_bytes:
                    result["reason"] = "capture_budget"
                    break
                response = initial if initial is not None else bridge({"operation": "read"})
                initial = None
                rows = response.get("interests")
                if not isinstance(rows, list) or len(rows) > MAX_INTERESTS:
                    raise RefreshStopped("invalid interest response")
                eligible = set()
                admitted = covered - excluded - retained
                for row in rows:
                    if not isinstance(row, dict):
                        raise RefreshStopped("malformed interest row")
                    symbol = row.get("symbol", "")
                    validate_interest(row, symbol)
                    age = (wall - stamp(row["requested_at_utc"])).total_seconds()
                    if (symbol in admitted and row["session_date"] == session and 0 <= age <= 120
                            and tick - last.get(symbol, -float("inf")) >= INTERVAL
                            and not (holds / f"{symbol}.json").exists()):
                        eligible.add(symbol)
                for symbol in sorted(eligible, key=lambda s: (last.get(s, -float("inf")), s))[:PER_CYCLE]:
                    attempt = monotonic()
                    if abs((now() - started).total_seconds() - (attempt - started_mono)) > 2:
                        raise RefreshStopped("clock discontinuity")
                    while recent and attempt - recent[0] >= 3600:
                        recent.popleft()
                    if (len(recent) >= MAX_HOURLY or result["requests"] >= config.max_requests
                            or result["raw_bytes"] + MAX_RESPONSE > config.max_bytes
                            or attempt - started_mono >= config.max_seconds or boats_session_date(now()) != session):
                        break
                    last[symbol] = attempt
                    recent.append(attempt)
                    result["requests"] += 1
                    seq = result["requests"]
                    write_once(run_area / f"{seq:05d}-{symbol}-attempt.json", {"symbol": symbol, "at": now().isoformat()})
                    try:
                        snapshot, size = capture(symbol, session, archive, key)
                    except SymbolDataInvalid as exc:
                        if type(exc.raw_bytes) is not int or not 0 <= exc.raw_bytes <= MAX_RESPONSE:
                            raise RefreshStopped("invalid failed-capture byte count") from exc
                        result["raw_bytes"] += exc.raw_bytes
                        retained.add(symbol)
                        result["held"].append(symbol)
                        write_once(run_area / f"{seq:05d}-{symbol}-invalid.json",
                            {"symbol":symbol, "reason":str(exc), "raw_bytes":exc.raw_bytes,
                             "receipt_id":exc.receipt_id, "retry_authorized":False})
                        continue
                    except TiingoArchiveError as exc:
                        if str(exc) == "Tiingo HTTP 404; source not admitted":
                            excluded.add(symbol)
                            result["held"].append(symbol)
                            write_once(holds / f"{symbol}.json", {"symbol": symbol, "http_status": 404,
                                       "session_date": session, "at": now().isoformat()})
                            continue
                        raise
                    if type(size) is not int or not 0 <= size <= MAX_RESPONSE:
                        raise RefreshStopped("invalid captured byte count")
                    result["raw_bytes"] += size
                    require_space(archive.root, floor=archive.free_floor)
                    write_once(run_area / f"{seq:05d}-{symbol}-snapshot.json", snapshot)
                    delivered = bridge({"operation": "publish", "snapshot": snapshot})
                    write_once(run_area / f"{seq:05d}-{symbol}-delivery.json", delivered)
                    expected_sha = hashlib.sha256((json.dumps(snapshot, separators=(",", ":"), allow_nan=False) + "\n").encode()).hexdigest()
                    if (delivered.get("symbol") != symbol or delivered.get("status") not in {"published", "unchanged", "newer_retained"}
                            or not isinstance(delivered.get("sha256"), str) or len(delivered["sha256"]) != 64
                            or any(c not in "0123456789abcdef" for c in delivered["sha256"])
                            or (delivered["status"] != "newer_retained" and delivered["sha256"] != expected_sha)):
                        raise DeliveryUnknown("snapshot write returned no qualified acknowledgment")
                    if delivered["status"] == "newer_retained":
                        result["newer_retained"] += 1
                        retained.add(symbol)
                    else:
                        result["delivered"] += 1
                sleep(max(0.1, min(INTERVAL - (monotonic() - tick), config.max_seconds - (monotonic() - started_mono))))
        except BaseException as exc:
            failure = exc
            result["reason"] = "effect_unknown" if isinstance(exc, DeliveryUnknown) else "stopped"
            result["error_type"] = type(exc).__name__
            result["cause_type"] = type(exc.__cause__).__name__ if exc.__cause__ is not None else None
            raise
        finally:
            result["eligible_symbols"] = len(covered - excluded - retained)
            result["finished_at_utc"] = now().isoformat()
            try:
                write_once(area / f"boats-live-history-final-{session}.json", result)
            except Exception as final_error:
                if failure is None:
                    raise
                failure.add_note("Final receipt could not be saved: " + type(final_error).__name__)
        return result
    finally:
        os.close(lock)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--symbols", type=Path, required=True)
    p.add_argument("--held", type=Path, required=True)
    p.add_argument("--capture", action="store_true")
    p.add_argument("--scheduled", action="store_true")
    p.add_argument("--ssh-host")
    p.add_argument("--ssh-identity", type=Path)
    p.add_argument("--remote-script")
    p.add_argument("--remote-root")
    p.add_argument("--max-requests", type=int, default=MAX_REQUESTS)
    p.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    p.add_argument("--max-seconds", type=int, default=MAX_SECONDS)
    a = p.parse_args(argv)
    cfg = Config(a.root, a.symbols, a.held, a.capture, a.max_requests, a.max_bytes, a.max_seconds, a.scheduled)
    if a.capture and not all((a.ssh_host, a.ssh_identity, a.remote_script, a.remote_root)):
        p.error("capture requires the complete existing SSH binding")
    bridge = SSHBridge(a.ssh_host, a.ssh_identity, a.remote_script, a.remote_root) if a.capture else None
    def interrupt(signum, _frame):
        raise RefreshStopped(f"signal {signum}")
    previous = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        result = run(cfg, bridge)
        print(json.dumps(result, separators=(",", ":")))
        return 0 if result["reason"] in {"plan", "window_closed", "seconds_budget", "capture_budget", "scheduled_candidate_not_due"} else 5
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
