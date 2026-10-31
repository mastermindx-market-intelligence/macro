"""Private SSH bridge for Terminal's bounded BOATS history demand and snapshots.

This is a filesystem component, not a network service. Its directory is explicitly
provisioned by deployment. It never creates the root, reads credentials, calls a
provider, follows a leaf symlink, or writes outside that directory. Input/output
are one bounded JSON document over the existing SSH connection.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import errno
import os
from pathlib import Path
import re
import stat
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, parse_qs

SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,31}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_SNAPSHOT = 512 * 1024
MAX_INTERESTS = 256
INTEREST_SCHEMA = "terminal.boats_history_interest.v1"
PROTOCOL = "terminal.boats_history_bridge.v1"
SNAPSHOT_SCHEMA = "terminal.boats_live_history.v1"


def stamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires offset")
    return parsed.astimezone(timezone.utc)


def read_regular(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as fp:
        info = os.fstat(fp.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_size > limit
                or info.st_uid != os.geteuid() or info.st_mode & 0o022):
            raise ValueError("not a bounded regular file")
        raw = fp.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("file grew beyond bound")
        return raw


def private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("expected private real directory")
    if info.st_uid != os.geteuid():
        raise ValueError("private directory has another owner")


def validate_interest(doc: dict, symbol: str) -> None:
    if not isinstance(doc, dict) or set(doc) != {"schema", "symbol", "session_date", "requested_at_utc"}:
        raise ValueError("unknown interest fields")
    if doc["schema"] != INTEREST_SCHEMA or doc["symbol"] != symbol or not SYMBOL.fullmatch(symbol):
        raise ValueError("invalid interest identity")
    if not isinstance(doc["session_date"], str) or not DAY.fullmatch(doc["session_date"]):
        raise ValueError("invalid session date")
    if datetime.fromisoformat(doc["session_date"]).date().isoformat() != doc["session_date"]:
        raise ValueError("invalid session calendar")
    stamp(doc["requested_at_utc"])


def validate_snapshot(doc: dict) -> tuple[str, datetime]:
    if not isinstance(doc, dict) or set(doc) != {"schema", "session_date", "captured_at_utc", "history"}:
        raise ValueError("unknown snapshot fields")
    if doc["schema"] != SNAPSHOT_SCHEMA or not DAY.fullmatch(str(doc["session_date"])):
        raise ValueError("invalid snapshot identity")
    history = doc["history"]
    if not isinstance(history, dict) or not SYMBOL.fullmatch(str(history.get("symbol", ""))):
        raise ValueError("invalid history symbol")
    if history.get("schema") != "terminal.tiingo_boats_history.v1" or history.get("source") != "tiingo-boats-rest":
        raise ValueError("invalid history source")
    receipts = history.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != 1 or not isinstance(receipts[0], dict):
        raise ValueError("snapshot must bind one receipt")
    observed = stamp(doc["captured_at_utc"])
    if observed != stamp(receipts[0].get("observed_at_utc")):
        raise ValueError("snapshot observation differs from receipt")
    if not isinstance(history.get("bars"), list) or len(history["bars"]) > 480:
        raise ValueError("snapshot bar bound")
    expected = {"schema", "symbol", "source", "venue", "timestamp_basis", "bar_seconds",
                "price_basis", "volume_basis", "coverage", "complete", "receipts", "bars", "bar_receipt_ids"}
    if (set(history) != expected or history["venue"] != "BOATS" or history["timestamp_basis"] != "utc"
            or type(history["bar_seconds"]) is not int or history["bar_seconds"] != 60
            or history["complete"] is not False or history["price_basis"] != "vendor_reported_unqualified"
            or history["volume_basis"] != "vendor_reported_shares"
            or history["coverage"] != "captured_vendor_bars_only"):
        raise ValueError("unsupported history contract")
    receipt = receipts[0]
    sha = re.compile(r"[a-f0-9]{64}\Z")
    if (set(receipt) != {"receipt_id", "raw_sha256", "observed_at_utc", "request_path"}
            or not isinstance(receipt["receipt_id"], str) or not sha.fullmatch(receipt["receipt_id"])
            or not isinstance(receipt["raw_sha256"], str) or not sha.fullmatch(receipt["raw_sha256"])
            or not isinstance(receipt["request_path"], str)):
        raise ValueError("invalid receipt identity")
    url = urlsplit(receipt["request_path"])
    query = parse_qs(url.query, keep_blank_values=True)
    latest_session = "startDate" not in query and "endDate" not in query
    dated_session = (query.get("startDate") == [doc["session_date"]]
                     and query.get("endDate") == [doc["session_date"]])
    if (url.scheme or url.netloc or url.path != f"/boats/{history['symbol']}/prices"
            or query.get("resampleFreq") != ["1min"]
            or not (latest_session or dated_session)):
        raise ValueError("receipt does not bind one overnight session")
    # A date-free request explicitly selects Tiingo's latest session. Bind it
    # to the receipt observation and every returned minute below, never to the
    # wall clock at delivery. Retain compatibility with original dated receipts.
    def session_at(value):
        local = value.astimezone(ZoneInfo("America/New_York"))
        if 4 <= local.hour < 20:
            return None
        day = local.date() + timedelta(days=1) if local.hour >= 20 else local.date()
        return day.isoformat() if day.weekday() < 5 else None
    if session_at(observed) != doc["session_date"]:
        raise ValueError("observation outside snapshot session")
    lineage, previous = history["bar_receipt_ids"], 0
    if not isinstance(lineage, list) or len(lineage) != len(history["bars"]):
        raise ValueError("bar receipt coverage mismatch")
    for row, ids in zip(history["bars"], lineage):
        if not isinstance(row, list) or len(row) != 6 or ids != [receipt["receipt_id"]]:
            raise ValueError("invalid bar or receipt lineage")
        epoch, opening, high, low, close, volume = row
        if (type(epoch) is not int or not 946684800 <= epoch < 4102444800 or epoch % 60
                or epoch <= previous or epoch > observed.timestamp()
                or session_at(datetime.fromtimestamp(epoch, timezone.utc)) != doc["session_date"]):
            raise ValueError("bar outside ordered snapshot minutes")
        if (any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in row[1:5])
                or type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0
                or low > min(opening, close) or high < max(opening, close) or low > high):
            raise ValueError("invalid snapshot OHLCV")
        previous = epoch
    return history["symbol"], observed


def exchange(root: Path, request: dict) -> dict:
    if not root.is_absolute():
        raise ValueError("absolute private root required")
    for directory in (root, root / "requests", root / "bars"):
        private_directory(directory)
    if request == {"operation": "read"}:
        rows, rejected, truncated = [], 0, False
        with os.scandir(root / "requests") as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_INTERESTS + 16:
                    truncated = True
                    break
                # Atomic writers use private dot-prefixed temporary files.
                if entry.name.startswith("."):
                    continue
                symbol = entry.name.removesuffix(".json")
                if entry.name != symbol + ".json" or not SYMBOL.fullmatch(symbol):
                    rejected += 1
                    continue
                try:
                    doc = json.loads(read_regular(Path(entry.path), 512))
                    validate_interest(doc, symbol)
                except FileNotFoundError:
                    continue  # expiry removal raced the read; no demand remains
                except (ValueError, UnicodeError):
                    rejected += 1
                    continue
                except OSError as exc:
                    if exc.errno != errno.ELOOP:
                        raise
                    rejected += 1
                    continue
                if len(rows) == MAX_INTERESTS:
                    truncated = True
                    break
                rows.append(doc)
        return {"protocol": PROTOCOL, "interests": rows, "rejected": rejected, "truncated": truncated}
    if not isinstance(request, dict) or set(request) != {"operation", "snapshot"} or request["operation"] != "publish":
        raise ValueError("unsupported operation")
    doc = request["snapshot"]
    symbol, observed = validate_snapshot(doc)
    raw = (json.dumps(doc, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if len(raw) > MAX_SNAPSHOT:
        raise ValueError("snapshot too large")
    target = root / "bars" / f"{symbol}.json"
    lock = os.open(root / ".publish.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            old = read_regular(target, MAX_SNAPSHOT)
            old_doc = json.loads(old)
            old_symbol, previous = validate_snapshot(old_doc)
            if old_symbol != symbol:
                raise ValueError("stored identity differs")
            if previous >= observed:
                if previous == observed and old_doc != doc:
                    raise ValueError("conflicting same-vintage snapshot")
                return {"protocol": PROTOCOL, "status": "unchanged" if old_doc == doc else "newer_retained",
                        "symbol": symbol, "sha256": hashlib.sha256(raw if old_doc == doc else old).hexdigest(),
                        "stored_sha256": hashlib.sha256(old).hexdigest()}
        except FileNotFoundError:
            pass
        temporary = target.with_name(f".{symbol}.{os.getpid()}.tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as fp:
                fp.write(raw)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(temporary, target)
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)
        return {"protocol": PROTOCOL, "status": "published", "symbol": symbol, "sha256": hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(lock)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_SNAPSHOT + 1025)
    if len(raw) > MAX_SNAPSHOT + 1024:
        raise ValueError("request too large")
    result = exchange(args.root, json.loads(raw))
    print(json.dumps(result, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
