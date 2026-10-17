"""One attended capture into Macro's existing Treasury auction data owner.

No imports fetch data. No scheduler, collector registration or feed publication is
installed by this command. Body receipt, publication and build clocks are distinct.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
# Promote this checkout even when its root already appears after ambient packages.
sys.path.insert(0, str(ROOT))

from engine import treasury_auction_lifecycle as lifecycle

SOURCES = {
    "announced": ("treasurydirect_json", "https://www.treasurydirect.gov/TA_WS/securities/announced?format=json"),
    "upcoming": ("treasurydirect_json", "https://www.treasurydirect.gov/TA_WS/securities/upcoming?format=json"),
    "tentative": ("quarterly_tentative_xml", "https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.xml"),
    "pending": ("pending_auctions_xml", "https://www.treasurydirect.gov/xml/PendingAuctions.xml"),
}
OFFICIAL_HOSTS = {"www.treasurydirect.gov", "treasurydirect.gov", "home.treasury.gov"}


def _now():
    return datetime.now(timezone.utc)


def _clock(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("capture clock must be an offset-aware datetime")
    return value.astimezone(timezone.utc)


def _official_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("response/redirect URL is outside the fixed official HTTPS hosts")
    return url


class _OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url):
    _official_url(url)
    request = Request(url, headers={"User-Agent": "Mastermind-Auction-Research/1.0", "Accept": "application/json, application/xml, text/xml"})
    with build_opener(_OfficialRedirects()).open(request, timeout=25) as response:
        _official_url(response.url)
        body = response.read(lifecycle.MAX_PAYLOAD_BYTES + 1)
        if len(body) > lifecycle.MAX_PAYLOAD_BYTES:
            raise ValueError("source body exceeds capture byte limit; not retained or interpreted")
        return body, {
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "http_date": response.headers.get("Date"),
            "http_last_modified": response.headers.get("Last-Modified"),
            "final_url": response.url,
        }


def _persist(directory, receipt):
    """Publish a complete receipt with a no-overwrite hard link, then remove temp."""
    directory.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(receipt, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    observed = datetime.fromisoformat(receipt["observed_at"])
    target = directory / (observed.strftime("%Y%m%dT%H%M%S%fZ") + "-" + digest + ".json")
    fd, temporary = tempfile.mkstemp(prefix=".auction-receipt-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != raw:
                raise RuntimeError("immutable receipt collision")
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"path": str(target), "receipt_sha256": digest, "bytes": len(raw)}


def capture(data_dir, *, source_names=None, fetcher=None, clock=None):
    """Capture fixed official endpoints. Fetch/parse failures remain visible receipts.

    Inject fetcher/clock for bounded offline tests. This function does not infer a
    historical first-seen time from source metadata. A successful receipt is dated
    after the complete response body returns; failed attempts have their own clock.
    """
    fetcher, clock = fetcher or _fetch, clock or _now
    names = list(SOURCES) if source_names is None else list(source_names)
    if not names or len(names) > len(SOURCES) or len(set(names)) != len(names) or any(n not in SOURCES for n in names):
        raise ValueError("source_names must be a nonempty unique subset of the fixed official sources")
    directory = Path(data_dir) / "treasury_auctions" / "observations"
    writes = []
    for name in names:
        kind, url = SOURCES[name]
        started = _clock(clock())
        body = None
        metadata = {}
        try:
            body, metadata = fetcher(url)
            completed = _clock(clock())
            if completed < started:
                raise ValueError("capture clock moved backwards")
            if not isinstance(body, bytes):
                raise TypeError("fetcher must return exact response bytes")
            _official_url(metadata["final_url"])
            receipt = lifecycle.make_observation(
                body, source_kind=kind, source_url=url, observed_at=completed,
                metadata={**metadata, "request_started_at": started.isoformat(),
                          "body_received_at": completed.isoformat(),
                          "publication_time": None, "rights_status": "OFFICIAL_PUBLIC_SOURCE"},
            )
            checked = lifecycle.build_context([receipt], completed)
            validated_at = _clock(clock())
            if validated_at < completed:
                raise ValueError("capture clock moved backwards")
            # The body-receipt clock remains literal metadata. The availability
            # bound includes successful decoding/validation before use in replay.
            receipt["observed_at"] = validated_at.isoformat()
            receipt["metadata"]["parse_completed_at"] = validated_at.isoformat()
            receipt["metadata"]["observed_at_basis"] = "conservative_parse_completion_bound"
            validation_status = checked["status"]
            receipt["metadata"]["validation_status"] = validation_status
        except Exception as exc:
            failed_at = _clock(clock())
            if failed_at < started:
                raise ValueError("capture clock moved backwards") from exc
            receipt = {"receipt_version": lifecycle.RECEIPT_VERSION, "status": "unavailable",
                       "source_kind": kind, "schema_id": lifecycle.SOURCE_SCHEMAS[kind],
                       "source_url": url, "observed_at": failed_at.isoformat(),
                       "error": f"{type(exc).__name__}: {exc}",
                       "metadata": {**metadata, "request_started_at": started.isoformat(),
                                    "attempt_completed_at": failed_at.isoformat()}}
            validation_status = "unavailable"
            # Preserve an unreadable bounded body for audit without claiming valid
            # UTF-8 or a parsed observation. It cannot supply a forecasting input.
            if isinstance(body, bytes) and len(body) <= lifecycle.MAX_PAYLOAD_BYTES:
                receipt["unparsed_body_sha256"] = hashlib.sha256(body).hexdigest()
                receipt["unparsed_body_base64"] = base64.b64encode(body).decode("ascii")
        saved = _persist(directory, receipt)
        writes.append({"source_name": name, "source_url": url, "status": validation_status,
                       "body_status": receipt["status"],
                       "observed_at": receipt["observed_at"], **saved})
    return {"schema_version": "treasury_auction_capture_receipt_v1", "captures": writes,
            "data_owner": "treasury_auctions", "scheduled": False, "published": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="Existing Macro data root, or an explicitly isolated verification root")
    parser.add_argument("--source", action="append", choices=tuple(SOURCES), dest="sources")
    args = parser.parse_args()
    result = capture(args.data_dir, source_names=args.sources)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 1 if any(c["status"] != "available" for c in result["captures"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
