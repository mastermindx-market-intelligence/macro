"""Derived, bounded static shards for the public earnings-record route catalog.

The canonical redacted route-catalog.json remains the sole source of truth.
Shards are byte-for-byte reproducible *projections* for browser lookups, not a
second publication/continuation state or another place to store source facts.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping


SHARD_COUNT = 64
SHARD_DIRNAME = "route-shards"
SHARD_SCHEMA = "earnings.public_wire_route_shard/v1"
CATALOG_SCHEMA = "earnings.public_wire_routes/v2"
_TICKER_RE = re.compile(r"[A-Z0-9](?:[A-Z0-9.\-]{0,14}[A-Z0-9])?\Z")


class EarningsRouteShardError(ValueError):
    """Refuse malformed public routing state rather than publishing a partial index."""


def shard_index(ticker: str) -> int:
    """Stable 31x ASCII hash shared with the browser (modulo 64)."""
    if not isinstance(ticker, str) or not _TICKER_RE.fullmatch(ticker):
        raise EarningsRouteShardError("invalid earnings route ticker")
    value = 0
    for character in ticker:
        value = (value * 31 + ord(character)) & (SHARD_COUNT - 1)
    return value


def shard_filename(ticker: str) -> str:
    return f"part-{shard_index(ticker):02x}.json"


def _client_route(record: object) -> dict[str, str]:
    if not isinstance(record, Mapping):
        raise EarningsRouteShardError("invalid public earnings record route")
    keys = ("href", "period", "transcript_id")
    if any(not isinstance(record.get(key), str) or not record[key] for key in keys):
        raise EarningsRouteShardError("incomplete public earnings record route")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.html", record["href"]):
        raise EarningsRouteShardError("unsafe public earnings record href")
    return {key: record[key] for key in keys}


def build_route_shards(catalog_bytes: bytes) -> dict[str, bytes]:
    """Return all 64 deterministic browser shards, including empty buckets.

    Never copy company names, event facts, receipt hashes, private identifiers,
    or source/continuation fields into a lookup payload. A shard only provides
    an exact public href and its matching transcript/period evidence.
    """
    try:
        catalog = json.loads(catalog_bytes)
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise EarningsRouteShardError("invalid canonical public route catalog") from exc
    if not isinstance(catalog, Mapping) or catalog.get("schema") != CATALOG_SCHEMA:
        raise EarningsRouteShardError("public route catalog schema is not v2")
    routes = catalog.get("routes")
    if (not isinstance(routes, Mapping)
            or not isinstance(catalog.get("source_generation_id"), str)
            or not isinstance(catalog.get("verified_at"), str)):
        raise EarningsRouteShardError("incomplete canonical public route catalog")
    buckets: list[dict[str, dict]] = [{} for _ in range(SHARD_COUNT)]
    for ticker, route in routes.items():
        slot = shard_index(ticker)
        if not isinstance(route, Mapping) or not isinstance(route.get("events"), Mapping):
            raise EarningsRouteShardError("invalid public ticker route events")
        events = {key: _client_route(value) for key, value in route["events"].items()
                  if isinstance(key, str)}
        if len(events) != len(route["events"]):
            raise EarningsRouteShardError("invalid public ticker transcript ID")
        buckets[slot][ticker] = {
            "events": {key: events[key] for key in sorted(events)},
            "latest": _client_route(route.get("latest")),
        }

    result: dict[str, bytes] = {}
    for index, subset in enumerate(buckets):
        filename = f"part-{index:02x}.json"
        payload = {
            "schema": SHARD_SCHEMA,
            # No generation clock/receipt here: unchanged ticker routes MUST
            # retain identical bytes across hourly source verifications.
            "shard": f"{index:02x}",
            "routes": {ticker: subset[ticker] for ticker in sorted(subset)},
        }
        result[filename] = (
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n"
        ).encode("utf-8")
    return result
