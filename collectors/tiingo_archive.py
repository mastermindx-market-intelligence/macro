"""Tiingo raw-source adapter for the existing Mastermind Data OS.

This module is an L0 archive producer, NOT a second Data OS price or identity authority.
All REST responses are kept byte-for-byte; normalized BOATS event views are explanatory
only until a Data OS as-of identity/venue/basis contract enrolls their receipts.

No token in URLs, manifests, logs, repository files, or printed exceptions.
External-drive-only storage. No implicit publication or redistribution.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

API_ORIGIN = "https://api.tiingo.com"
BOATS_WS = "wss://api.tiingo.com/boats"
EXTERNAL_MOUNT = Path("/Volumes/Mastermind")
DEFAULT_ARCHIVE = EXTERNAL_MOUNT / "market-data" / "tiingo"
DEFAULT_KEY_FILE = EXTERNAL_MOUNT / ".mastermind_private" / "tiingo" / "api_key"
MIN_FREE_BYTES = 35 * 1024**3
MAX_RESPONSE_BYTES = 512 * 1024**2
_SYMBOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$")
_ALLOWED_PARAMS = frozenset({
    "startDate", "endDate", "startExDate", "endExDate", "exDate",
    "resampleFreq", "afterHours", "forceFill", "columns", "asReported",
    "tickers", "limit", "offset", "sortBy", "tags", "sources", "onlyWithTickers",
    "query",
})


@dataclass(frozen=True)
class Source:
    path: str
    symbol: bool = False
    date_range: bool = False
    group: str = ""
    note: str = ""


# Only documented fixed-origin vendor paths; no raw URL entrypoint.
SOURCES: dict[str, Source] = {
    "eod-bars": Source("/tiingo/daily/{symbol}/prices", True, True, "eod"),
    "eod-metadata": Source("/tiingo/daily/{symbol}", True, False, "eod"),
    "fund-statements": Source("/tiingo/fundamentals/{symbol}/statements", True, False, "fundamentals"),
    "fund-daily": Source("/tiingo/fundamentals/{symbol}/daily", True, False, "fundamentals"),
    "fund-meta": Source("/tiingo/fundamentals/meta", False, False, "fundamentals"),
    "fund-definitions": Source("/tiingo/fundamentals/definitions", False, False, "fundamentals"),
    "boats-bars": Source("/boats/{symbol}/prices", True, True, "boats"),
    "boats-symbol": Source("/boats/{symbol}", True, False, "boats"),
    "boats-market": Source("/boats", False, False, "boats"),
    "equity-intraday-bars": Source("/tiingo/equity/intraday/{symbol}/prices", True, True, "equity-intraday"),
    "equity-intraday-symbol": Source("/tiingo/equity/intraday/{symbol}", True, False, "equity-intraday"),
    "equity-intraday-market": Source("/tiingo/equity/intraday", False, False, "equity-intraday"),
    "iex-bars": Source("/iex/{symbol}/prices", True, True, "iex"),
    "iex-symbol": Source("/iex/{symbol}", True, False, "iex"),
    "news": Source("/tiingo/news", False, False, "news"),
    "news-bulk-index": Source("/tiingo/news/bulk_download", False, False, "news"),
    "crypto-bars": Source("/tiingo/crypto/prices", False, True, "crypto"),
    "crypto-meta": Source("/tiingo/crypto", False, False, "crypto"),
    "forex-bars": Source("/tiingo/fx/{symbol}/prices", True, True, "forex"),
    "forex-top": Source("/tiingo/fx/{symbol}/top", True, False, "forex"),
    "distributions": Source("/tiingo/corporate-actions/{symbol}/distributions", True, False, "actions"),
    "distribution-yield": Source("/tiingo/corporate-actions/{symbol}/distribution-yield", True, False, "actions"),
    "splits": Source("/tiingo/corporate-actions/{symbol}/splits", True, False, "actions"),
    "fund-fee-profile": Source("/tiingo/funds/{symbol}", True, False, "funds"),
    "fund-fee-history": Source("/tiingo/funds/{symbol}/metrics", True, False, "funds"),
    "security-search": Source("/tiingo/utilities/search", False, False, "reference"),
}


class TiingoArchiveError(RuntimeError):
    """Safe, credential-free failure message."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def symbol_path(symbol: str) -> str:
    if not _SYMBOL.fullmatch(symbol) or symbol in {".", ".."}:
        raise ValueError("unsafe Tiingo symbol")
    return urllib.parse.quote(symbol, safe="")


def request_path(source: str, symbol: str | None, params: dict[str, Any] | None = None) -> str:
    if source not in SOURCES:
        raise ValueError("unknown Tiingo source")
    item = SOURCES[source]
    if bool(symbol) != item.symbol:
        raise ValueError("source and symbol selection mismatch")
    if symbol is not None:
        path = item.path.replace("{symbol}", symbol_path(symbol))
    else:
        path = item.path
    params = dict(params or {})
    if not set(params).issubset(_ALLOWED_PARAMS):
        raise ValueError("unknown Tiingo request parameter")
    for k, v in params.items():
        if v is None or (isinstance(v, str) and len(v) > 150):
            raise ValueError("invalid Tiingo parameter")
        if "token" in k.lower() or "auth" in k.lower():
            raise ValueError("credentials cannot occur in URL")
    query = urllib.parse.urlencode(sorted(params.items()), safe=",")
    return path + ("?" + query if query else "")


def require_external_root(root: Path, *, check_mount: bool = True) -> Path:
    path = root.resolve()
    mount = EXTERNAL_MOUNT.resolve()
    if path == mount or not path.is_relative_to(mount):
        raise TiingoArchiveError("archive path must remain under dedicated external drive")
    if check_mount and not EXTERNAL_MOUNT.is_mount():
        raise TiingoArchiveError("external Mastermind drive not mounted; no SSD fallback")
    return path


def require_space(root: Path, *, floor: int = MIN_FREE_BYTES) -> None:
    if shutil.disk_usage(root).free < floor:
        raise TiingoArchiveError("external archive space reserve reached; stop ingest")


def read_key(key_file: Path = DEFAULT_KEY_FILE) -> str:
    # Secrets remain owned by the operator, not by this source tree.
    token = os.environ.get("TIINGO_API_KEY")
    if token is None:
        st = key_file.stat()
        if st.st_mode & 0o077:
            raise TiingoArchiveError("Tiingo key-file permissions must be owner-only")
        token = key_file.read_text(encoding="utf-8").strip()
    if not token or not re.fullmatch(r"[A-Za-z0-9._-]{20,256}", token):
        raise TiingoArchiveError("Tiingo token missing or malformed")
    return token


def decode_boats(message: dict[str, Any], received_at: str) -> dict[str, Any] | None:
    """Pure explanatory projection. Keep raw envelope as source of truth.

    Q: 9 slots [kind, vendor_datetime, epoch_ns, ticker, bid_size, bid, mid, ask, ask_size].
    T/B: 10 slots [kind, vendor_datetime, epoch_ns, ticker, last, size, 4 raw conditions].
    Trade breaks do NOT add executed volume.
    """
    if not isinstance(message, dict) or message.get("service") != "boats":
        return None
    data = message.get("data")
    if not isinstance(data, list) or not data:
        return None
    kind = data[0]
    if kind not in {"Q", "T", "B"}:
        return None
    if len(data) != (9 if kind == "Q" else 10):
        raise TiingoArchiveError("BOATS payload length mismatch")
    ticker = str(data[3])
    symbol_path(ticker)
    event = {
        "source": "tiingo", "venue": "BOATS", "venue_scope": "single_ats",
        "session": "overnight", "kind": kind,
        "event_datetime": data[1], "event_epoch_ns": int(data[2]),
        "received_at": received_at, "ticker": ticker,
        "is_nbbo": False, "is_canonical_price": False,
    }
    if kind == "Q":
        event.update(bid_size=data[4], bid_raw=data[5], mid_vendor=data[6],
                     ask_raw=data[7], ask_size=data[8])
    else:
        event.update(last_raw=data[4], last_size=data[5],
                     sale_conditions=list(data[6:10]), is_break=(kind == "B"))
    return event


def _publish_once(path: Path, data: bytes) -> bool:
    """Write-if-absent: same fingerprint is idempotent; changed response is new vintage."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".incoming-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as fp:
            fp.write(data)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            os.link(tmp, path)  # atomic no-replace, even under a second worker
            return True
        except FileExistsError:
            return False
    finally:
        Path(tmp).unlink(missing_ok=True)


class Archive:
    def __init__(self, root: Path = DEFAULT_ARCHIVE, *, check_mount: bool = True,
                 free_floor: int = MIN_FREE_BYTES):
        self.root = require_external_root(root, check_mount=check_mount)
        self.root.mkdir(parents=True, exist_ok=True)
        self.free_floor = free_floor
        require_space(self.root, floor=free_floor)

    def store_response(self, source: str, symbol: str | None, path: str,
                       raw: bytes, *, received_at: str | None = None,
                       content_type: str = "application/json", http_status: int = 200
                       ) -> dict[str, Any]:
        if source not in SOURCES or SOURCES[source].symbol != bool(symbol):
            raise ValueError("invalid source/symbol")
        if not path.startswith(SOURCES[source].path.split("{symbol}")[0]):
            raise ValueError("source path mismatch")
        require_space(self.root, floor=self.free_floor)
        received_at = received_at or utc_now()
        day = received_at[:10]
        safe_symbol = symbol_path(symbol) if symbol else "all"
        fingerprint = hashlib.sha256(raw).hexdigest()
        request_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
        rel = Path("raw") / source / day / safe_symbol / f"{request_hash}-{fingerprint[:24]}.raw.gz"
        blob = gzip.compress(raw, mtime=0)
        added = _publish_once(self.root / rel, blob)
        count = None
        if "json" in content_type.lower() and len(raw) < 50 * 1024 * 1024:
            try:
                parsed = json.loads(raw)
                count = len(parsed) if isinstance(parsed, (list, dict)) else None
            except (json.JSONDecodeError, UnicodeError):
                pass
        receipt = {
            "schema": "mastermind.tiingo.raw_receipt.v1",
            "source": source, "vendor": "tiingo", "symbol": symbol,
            "request_path": path, "observed_at_utc": received_at,
            "publication_time_status": "UNVERIFIED_HISTORICALLY",
            "rights_status": "PER_PRODUCT_REDISTRIBUTION_NOT_VERIFIED",
            "http_status": http_status, "content_type": content_type,
            "raw_path": rel.as_posix(), "raw_sha256": fingerprint,
            "raw_bytes": len(raw), "compressed_bytes": len(blob),
            "record_count_hint": count, "source_modified_at": None,
            "correction_policy": "APPEND_VINTAGE_NEVER_IN_PLACE",
            "price_basis_policy": "PRESERVE_VENDOR_RAW_AND_ADJUSTED_AS_DIFFERENT_FIELDS",
        }
        _publish_once(self.root / "receipts" / source / day /
                      f"{request_hash}-{fingerprint[:24]}.json",
                      (json.dumps(receipt, sort_keys=True) + "\n").encode())
        return {"new_raw": added, "raw_sha256": fingerprint, "path": rel.as_posix(),
                "rows_hint": count, "raw_bytes": len(raw)}

    def store_boats_batch(self, messages: Iterable[tuple[str, str]]) -> dict[str, Any]:
        """One append-only segment of timestamped raw websocket envelopes."""
        require_space(self.root, floor=self.free_floor)
        data = bytearray()
        count = {"Q": 0, "T": 0, "B": 0, "other": 0}
        seen_start = seen_end = None
        for arrival, raw in messages:
            if seen_start is None:
                seen_start = arrival
            seen_end = arrival
            try:
                decoded = decode_boats(json.loads(raw), arrival)
                kind = decoded["kind"] if decoded else "other"
            except (ValueError, TypeError, TiingoArchiveError):
                kind = "other"
            count[kind] += 1
            data.extend(json.dumps({"received_at": arrival, "raw_message": raw},
                                   separators=(",", ":")).encode() + b"\n")
        if not data:
            return {"new_raw": False, "messages": 0}
        day = (seen_start or utc_now())[:10]
        fingerprint = hashlib.sha256(data).hexdigest()
        rel = Path("raw") / "boats-firehose" / day / f"{fingerprint}.ndjson.gz"
        zipped = gzip.compress(bytes(data), mtime=0)
        added = _publish_once(self.root / rel, zipped)
        receipt = {
            "schema": "mastermind.tiingo.boats_firehose_receipt.v1",
            "vendor": "tiingo", "venue": "BOATS", "nbbo": False,
            "session": "overnight", "first_received_at_utc": seen_start,
            "last_received_at_utc": seen_end, "transport_continuity": "NOT_PROVEN",
            "counts": count, "raw_path": rel.as_posix(),
            "raw_sha256": fingerprint, "raw_bytes": len(data),
            "compressed_bytes": len(zipped),
            "rights_status": "BOATS_REDISTRIBUTION_NOT_VERIFIED",
            "coverage": "SOURCE_MESSAGES_RECEIVED_ONLY",
        }
        _publish_once(self.root / "receipts" / "boats-firehose" / day /
                      f"{fingerprint}.json",
                      (json.dumps(receipt, sort_keys=True) + "\n").encode())
        return {"new_raw": added, "messages": sum(count.values()),
                "raw_sha256": fingerprint, "path": rel.as_posix(),
                "raw_bytes": len(data), "counts": count}


def fetch_json_bytes(path: str, key: str, *, timeout: float = 30,
                     max_bytes: int = MAX_RESPONSE_BYTES) -> tuple[bytes, str]:
    # Caller constructs a fixed-origin, documented endpoint via request_path().
    if not path.startswith("/") or "//" in path or "@" in path:
        raise ValueError("unsafe API path")
    req = urllib.request.Request(API_ORIGIN + path, headers={
        "Authorization": "Token " + key, "Accept": "application/json",
        "User-Agent": "MastermindDataOS-TiingoArchive/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            mime = response.headers.get("Content-Type", "application/octet-stream")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise TiingoArchiveError("Tiingo response exceeded bounded archive size")
            return raw, mime
    except urllib.error.HTTPError as exc:
        # Do not print response body; vendors sometimes echo authentication details.
        raise TiingoArchiveError(f"Tiingo HTTP {exc.code}; source not admitted") from None
    except urllib.error.URLError:
        raise TiingoArchiveError("Tiingo transport unavailable") from None


def collect_one(archive: Archive, source: str, symbol: str | None, key: str,
                params: dict[str, Any] | None = None) -> dict[str, Any]:
    path = request_path(source, symbol, params)
    raw, mime = fetch_json_bytes(path, key)
    return archive.store_response(source, symbol, path, raw, content_type=mime)
