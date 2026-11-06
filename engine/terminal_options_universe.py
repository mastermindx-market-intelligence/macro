"""Resolve Terminal US equity and fund candidates against the subscribed options catalog."""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
import re
import time

import requests

from collectors import thetadata

_MANIFEST = "https://app.mastermind-x.com/data/manifest.json"
_US_VENUES = {"US", "NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSEARCA", "CBOE", "BATS"}
_ROOT = re.compile(r"[A-Z0-9]{1,10}(?:[.-][A-Z0-9]{1,4})?")


def _catalog_bytes(url: str, limit: int, deadline: float) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("catalog_deadline")
    with requests.get(url, stream=True, allow_redirects=False,
                      timeout=(min(3, remaining), min(8, remaining))) as response:
        if response.status_code != 200:
            raise ValueError(f"catalog_http_{response.status_code}")
        body = bytearray()
        for chunk in response.iter_content(65536):
            if time.monotonic() >= deadline:
                raise TimeoutError("catalog_deadline")
            body.extend(chunk)
            if len(body) > limit:
                raise ValueError("catalog_size_exceeded")
    return bytes(body)


def match_catalogs(manifest: dict, listed: set[str], session: date) -> tuple[set[str], dict]:
    stamped = date.fromisoformat(manifest["as_of"])
    if not 0 <= (session - stamped).days <= 7:
        raise ValueError("terminal_manifest_clock_invalid")
    symbols = manifest["symbols"]
    if not isinstance(symbols, dict) or not symbols or not listed:
        raise ValueError("catalog_empty")
    eligible_market = {root for root, metadata in symbols.items()
                       if isinstance(metadata, dict) and _ROOT.fullmatch(root)
                       and metadata.get("sec") in {"Equities", "Funds"}
                       and str(metadata.get("mkt") or "").upper() in _US_VENUES}
    matched = eligible_market & listed
    if not matched:
        raise ValueError("catalog_no_matching_roots")
    digest = hashlib.sha256("\n".join(sorted(matched)).encode("ascii")).hexdigest()
    return matched, {"manifest_as_of": stamped.isoformat(), "manifest_symbols": len(symbols),
                     "us_equities_and_funds": len(eligible_market), "vendor_symbols": len(listed),
                     "matched_roots": len(matched), "unmatched_roots": len(eligible_market - listed),
                     "matched_roster_sha256": digest}


def terminal_candidates(session: date, deadline: float) -> tuple[set[str], dict]:
    manifest = json.loads(_catalog_bytes(_MANIFEST, 8_000_000, deadline))
    source = _catalog_bytes(f"{thetadata._base_url()}/v3/option/list/symbols?format=csv", 2_000_000, deadline)
    records = csv.DictReader(io.StringIO(source.decode("utf-8-sig")))
    if "symbol" not in (records.fieldnames or ()):
        raise ValueError("vendor_catalog_schema_invalid")
    listed = {row["symbol"].strip().upper() for row in records if row.get("symbol")}
    return match_catalogs(manifest, listed, session)
