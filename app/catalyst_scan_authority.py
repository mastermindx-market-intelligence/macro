"""Anonymous-first scan proof for the existing Catalyst funnel's ScanAuthority.

A signed receipt proves only that a server just returned rights-qualified public
event evidence for these exact tickers/revision. It is NOT identity, email consent,
authorization to send, a market data source, or a new durable store. Every verify
rechecks the current public producer. No token is minted without a strong secret.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

_DOMAIN = b"mastermind.catalyst.public-scan.v1\x00"
_TTL = timedelta(minutes=20)
_EVENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:\-]{0,95}\Z")
_TICKER = re.compile(r"[A-Z]{1,6}(?:[.\-][A-Z]{1,2})?\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\Z")


@dataclass(frozen=True)
class ScanEvidence:
    """Structural match for Session 02's ScanAuthority/ScanEvidence protocol."""

    event_id: str
    tickers: tuple[str, ...]
    as_of_utc: str
    public_safe: bool


def _fail(code: str, status: int = 400) -> Exception:
    # Session 02 owns the public FunnelGate class. Import lazily because the
    # independent 02 PR remains Draft/HOLD while 00 can still serve the scan.
    try:
        from engine.marketing.catalyst_lifecycle import FunnelGate
    except ImportError:
        return ValueError(code)
    return FunnelGate(code, status)


def _encoded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decoded(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _as_utc(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ValueError("scan clock must be timezone aware")
    return current.astimezone(timezone.utc)


def _secret(value: str | None) -> str:
    secret = os.environ.get("CATALYST_SCAN_RECEIPT_SECRET", "") if value is None else value
    if len(secret) < 32:
        raise _fail("SCAN_PROOF_NOT_CONFIGURED", 503)
    return secret


def _supported(scan: dict) -> tuple[str, ...]:
    if (not isinstance(scan, dict) or scan.get("schema") != "catalyst.scan/v1"
            or scan.get("publication_state") not in ("PUBLIC_QUALIFIED", "PARTIAL")
            or not isinstance(scan.get("event_id"), str)
            or not _EVENT.fullmatch(scan["event_id"])
            or type(scan.get("generation")) is not int or scan["generation"] < 1):
        return ()
    results = scan.get("results")
    if not isinstance(results, list):
        return ()
    tickers = []
    for row in results:
        if not isinstance(row, dict) or row.get("status") != "SUPPORTED":
            continue
        t = row.get("ticker")
        if not isinstance(t, str) or not _TICKER.fullmatch(t) or t in tickers:
            return ()
        tickers.append(t)
    if not 1 <= len(tickers) <= 10:
        return ()
    return tuple(tickers)


class ScanReceiptAuthority:
    """Issuer/validator shared by the public route and Session 02 FunnelService.

    Optional reader and clock are for deterministic contract tests only; production
    uses the canonical producer through app.catalyst_integration.scan_with_reader.
    """

    def __init__(self, *, reader: Callable[..., dict] | None = None,
                 secret: str | None = None, now: Callable[[], datetime] | None = None):
        self._reader = reader
        self._secret = secret
        self._now = now

    def _clock(self) -> datetime:
        return _as_utc(self._now() if self._now is not None else None)

    def issue(self, scan: dict) -> str | None:
        """Return a short-lived opaque public-scan receipt; absent secret -> None."""
        tickers = _supported(scan)
        if not tickers:
            return None
        try:
            secret = _secret(self._secret)
        except Exception:
            return None
        now = self._clock()
        as_of = scan.get("as_of_utc")
        if not isinstance(as_of, str) or len(as_of) > 40:
            return None
        try:
            source_time = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            if source_time.tzinfo is None or source_time.utcoffset() != timedelta(0):
                return None
            if source_time > now + timedelta(minutes=5) or now - source_time > timedelta(days=7):
                return None
        except ValueError:
            return None
        body = {"v": 1, "event_id": scan["event_id"], "generation": scan["generation"],
                "tickers": list(tickers), "as_of_utc": as_of,
                "issued_at": int(now.timestamp())}
        packed = _encoded(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        sig = _encoded(hmac.new(secret.encode(), _DOMAIN + packed.encode(), hashlib.sha256).digest())
        token = packed + "." + sig
        return token if len(token) <= 1024 else None

    def require_public_scan(self, receipt: str) -> ScanEvidence:
        """Validate MAC, time, and re-read rights/current revision before consent."""
        secret = _secret(self._secret)
        if not isinstance(receipt, str) or len(receipt) > 1024 or not _TOKEN.fullmatch(receipt):
            raise _fail("INVALID_SCAN_PROOF")
        try:
            body, sig = receipt.split(".")
            expected = hmac.new(secret.encode(), _DOMAIN + body.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _decoded(sig)):
                raise ValueError("bad mac")
            payload = json.loads(_decoded(body))
            if not isinstance(payload, dict) or payload.get("v") != 1:
                raise ValueError("wrong version")
            event_id, tickers = payload.get("event_id"), payload.get("tickers")
            generation, issued_at = payload.get("generation"), payload.get("issued_at")
            as_of = payload.get("as_of_utc")
            if (not isinstance(event_id, str) or not _EVENT.fullmatch(event_id)
                    or type(generation) is not int or generation < 1
                    or type(issued_at) is not int
                    or not isinstance(as_of, str) or len(as_of) > 40
                    or not isinstance(tickers, list) or not 1 <= len(tickers) <= 10
                    or any(not isinstance(t, str) or not _TICKER.fullmatch(t) for t in tickers)
                    or len(set(tickers)) != len(tickers)):
                raise ValueError("bad receipt fields")
            current = self._clock()
            lag = current - datetime.fromtimestamp(issued_at, tz=timezone.utc)
            if lag > _TTL or lag < -timedelta(seconds=30):
                raise ValueError("expired or future proof")
        except (ValueError, TypeError, KeyError, OverflowError, binascii.Error):
            raise _fail("INVALID_SCAN_PROOF") from None

        # A MAC is NOT a promise of evergreen rights. Always ask the canonical
        # producer again, so a correction/retraction/rights withdrawal blocks
        # even a still-unexpired token.
        from app.catalyst_integration import scan_with_reader
        try:
            current_public = scan_with_reader(tickers, event_id, reader=self._reader,
                                              now_utc=self._clock())
        except Exception:
            raise _fail("SCAN_PROOF_SOURCE_UNAVAILABLE", 503) from None
        if (current_public.get("event_id") != event_id
                or current_public.get("generation") != generation
                or tuple(_supported(current_public)) != tuple(tickers)):
            raise _fail("SCAN_PROOF_SUPERSEDED", 403)
        current_clock = current_public.get("as_of_utc", "")
        if not isinstance(current_clock, str) or current_clock < as_of:
            raise _fail("SCAN_PROOF_STALE", 403)
        return ScanEvidence(event_id=event_id, tickers=tuple(tickers),
                            as_of_utc=current_clock, public_safe=True)
