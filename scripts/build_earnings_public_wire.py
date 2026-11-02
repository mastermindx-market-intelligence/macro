"""Build the public, exact-evidence earnings-call wire under ``/stocks/earnings``.

This builder consumes an immutable public story-packet generation, verifies
every object receipt and packet contract in memory, and emits a source-record
archive.  It is *not* a Press publication lane: it never uses upstream story
copy/SEO fields, does not call a model, and cannot publish an unverified
summary.

Git retains rendered public pages plus a tiny redacted route catalog only. No
packet, source marker, receipt graph, or last-good manifest is persisted. A
source outage preserves existing bytes for at most 48 hours; it then fails
closed rather than indefinitely masquerading stale research as current.

Usage:
    python -m scripts.build_earnings_public_wire
    python -m scripts.build_earnings_public_wire --offline
    python -m scripts.build_earnings_public_wire --out-dir /tmp/earnings-wire
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
import email.utils
from hashlib import sha256
import html
from inspect import signature
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
import requests

from jinja2 import Environment, FileSystemLoader, StrictUndefined


_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from engine.earnings_narrative.public_wire import (  # noqa: E402
    PUBLIC_WIRE_MANIFEST_SCHEMA,
    PublicWireContractError,
    build_public_wire_manifest,
    compile_public_wire_article,
    source_manifest_sha256,
    verify_public_wire_manifest,
)
from engine.earnings_narrative.context_packets import (  # noqa: E402
    build_context_generation,
    build_weekly_intelligence,
    canonical_json_bytes as context_json_bytes,
    select_public_facts,
)
from engine.earnings_narrative.story_packets import (  # noqa: E402
    validate_story_packet,
    validate_story_packet_manifest,
)
from lib.pages import write_page  # noqa: E402
from lib.seo import BRAND_NAME, SITE_BASE, page_url  # noqa: E402
from engine.neuralweb import company_intelligence_reader as _company_reader  # noqa: E402


log = logging.getLogger("build_earnings_public_wire")

DEFAULT_SOURCE_BASE = "https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev"
DEFAULT_SOURCE_MANIFEST = "earnings_story_packets/manifest.json"
DEFAULT_TRANSCRIPT_INDEX_URL = "https://app.mastermind-x.com/data/tx/index.json"
OUTPUT_RELATIVE = Path("stocks") / "earnings"
ROUTE_CATALOG_FILENAME = "route-catalog.json"
FEED_FILENAME = "feed.xml"
WIRE_SITEMAP_FILENAME = "sitemap.xml"
ASSET_DIRNAME = "assets"
ASSET_NAMES = ("earnings-wire.css", "earnings-wire.js")
ARTICLE_PUBLIC_FACT_LIMIT = 2
PREMIUM_PAYLOAD_SCHEMA = "earnings.tier_payload/v1"
PRIVATE_RECORDS_DIRNAME = "records"
PRIVATE_CONTEXT_DIRNAME = "context"
CONTEXT_FILENAME = "latest.json"
FEED_LIMIT = 100
INDEX_PAGE_SIZE = 96
# This lane is intentionally memory-bound while it hydrates a generation.  The
# served route catalog is its only persisted state; the packet graph and source
# marker must never become a Git artifact or a public bulk-data endpoint.
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_TRANSCRIPT_INDEX_BYTES = 16 * 1024 * 1024
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_SOURCE_PACKET_COUNT = 100_000
MAX_SELECTED_PACKET_COUNT = 10_000
MAX_SELECTED_PACKET_BYTES = 1024 * 1024 * 1024
MAX_DEFERRED_PACKET_COUNT = 10_000
MAX_EXISTING_AGE_SECONDS = 48 * 60 * 60
HTTP_FETCH_MAX_ATTEMPTS = 3
HTTP_FETCH_RETRY_BACKOFF_SECONDS = 0.25
ROUTE_CATALOG_SCHEMA_V1 = "earnings.public_wire_routes/v1"
ROUTE_CATALOG_SCHEMA_V2 = "earnings.public_wire_routes/v2"
ROUTE_CATALOG_SCHEMA = ROUTE_CATALOG_SCHEMA_V2


def _renderer_version() -> str:
    """Fingerprint every code/template input that can change rendered bytes.

    Source and Company generations can remain unchanged while this product's
    templates, shared public chrome, or renderer logic advances.  Pinning this
    digest in the redacted route catalog makes those deploys invalidate the
    packet-hydration fast path instead of leaving stale HTML in production.
    """
    inputs = [
        Path(__file__),
        _REPO / "engine" / "earnings_narrative" / "public_wire.py",
        _REPO / "lib" / "pages.py",
        _REPO / "lib" / "seo.py",
        _REPO / "templates" / "seo_base.html.j2",
        _REPO / "templates" / "_public_nav.html.j2",
        _REPO / "templates" / "_public_chrome_css.html.j2",
        *sorted((_REPO / "templates" / "earnings_wire").glob("*")),
    ]
    digest = sha256()
    for path in inputs:
        if not path.is_file():
            raise PublicWireBuildError(f"renderer input missing: {path}")
        digest.update(str(path.relative_to(_REPO)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class PublicWireBuildError(RuntimeError):
    """Fresh source collection failed before a safe public publication existed."""


@dataclass(frozen=True)
class BuildResult:
    manifest_id: str
    source: str
    article_count: int
    output_dir: Path


@dataclass(frozen=True)
class PacketSelection:
    admitted_keys: frozenset[str]
    changed_keys: frozenset[str]
    forward_new_keys: frozenset[str]
    skipped_historical_keys: frozenset[str]
    skipped_future_keys: frozenset[str]
    selected_keys: frozenset[str]


@dataclass(frozen=True)
class StoryManifestSnapshot:
    manifest: dict[str, Any]
    raw: bytes
    generation_id: str
    manifest_sha256: str


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def _safe_jsonld(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _json_bytes(value: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicWireBuildError(f"{label} is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise PublicWireBuildError(f"{label} must be a JSON object")
    return decoded


def _retryable_source_transport_error(exc: requests.RequestException) -> bool:
    """Return whether one immutable GET may be retried on the same origin."""
    return isinstance(
        exc,
        (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError,
        ),
    )


def _http_fetch(url: str, *, timeout: float, max_bytes: int) -> bytes:
    """Fetch one immutable-source object without unbounded buffering.

    Public packet storage is an input boundary, not a trusted local file.  The
    source never needs redirects, so rejecting them also closes a server-side
    request pivot.  ``max_bytes`` protects both builder memory and CI time.
    Transient connection/read failures retry only this idempotent immutable GET;
    source-policy, HTTP-status, size, receipt, and contract failures remain
    immediate fail-closed errors.
    """
    parsed = urlsplit(url)
    expected_origin = (parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port or 443)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise PublicWireBuildError("public story packet source must be a safe https URL")
    for attempt in range(1, HTTP_FETCH_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "MastermindX-EarningsWire/1.0 (+https://www.mastermind-x.com)"},
                timeout=timeout,
                stream=True,
                allow_redirects=False,
            )
            with response:
                landed = urlsplit(str(getattr(response, "url", url) or url))
                landed_origin = (landed.scheme.lower(), (landed.hostname or "").lower(), landed.port or 443)
                if response.is_redirect or 300 <= response.status_code < 400 or landed_origin != expected_origin:
                    raise PublicWireBuildError("public story packet source redirected or changed origin")
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise PublicWireBuildError("public story packet object exceeds safe size bound")
                    except ValueError as exc:
                        raise PublicWireBuildError("public story packet object has invalid Content-Length") from exc
                chunks: list[bytes] = []
                used = 0
                for chunk in response.iter_content(chunk_size=65_536):
                    if not chunk:
                        continue
                    used += len(chunk)
                    if used > max_bytes:
                        raise PublicWireBuildError("public story packet object exceeds safe size bound")
                    chunks.append(chunk)
                return b"".join(chunks)
        except PublicWireBuildError:
            raise
        except requests.RequestException as exc:
            if attempt >= HTTP_FETCH_MAX_ATTEMPTS or not _retryable_source_transport_error(exc):
                raise PublicWireBuildError(f"unable to fetch {url}: {exc}") from exc
            delay = HTTP_FETCH_RETRY_BACKOFF_SECONDS * attempt
            log.warning(
                "retrying immutable source transport read after %s (%d/%d): %s",
                type(exc).__name__,
                attempt,
                HTTP_FETCH_MAX_ATTEMPTS,
                parsed.path,
            )
            if delay > 0:
                time.sleep(delay)
    raise AssertionError("unreachable immutable source retry state")


def _source_url(base: str, relative: str) -> str:
    cleaned = relative.lstrip("/")
    if ".." in Path(cleaned).parts or not cleaned:
        raise PublicWireBuildError("unsafe public story packet object path")
    return base.rstrip("/") + "/" + cleaned


def _validate_remote_manifest(manifest: Mapping[str, Any]) -> None:
    try:
        validate_story_packet_manifest(manifest)
    except Exception as exc:  # noqa: BLE001 - domain contract error converted at this boundary.
        raise PublicWireBuildError(f"public story packet manifest failed contract verification: {exc}") from exc


def _read_remote_bytes(
    url: str,
    *,
    limit: int,
    timeout: float,
    fetch: Callable[[str], bytes] | None,
) -> bytes:
    if limit <= 0:
        raise PublicWireBuildError("remote read byte limit must be positive")
    if fetch is None:
        return _http_fetch(url, timeout=timeout, max_bytes=limit)
    try:
        try:
            accepts_limit = signature(fetch).bind(url, limit)
        except (TypeError, ValueError):
            accepts_limit = None
        payload = fetch(url, limit) if accepts_limit is not None else fetch(url)
    except PublicWireBuildError:
        raise
    except Exception as exc:  # noqa: BLE001 - injected fixtures share the production boundary.
        raise PublicWireBuildError(f"unable to fetch {url}: {exc}") from exc
    if not isinstance(payload, bytes):
        raise PublicWireBuildError(f"source fetch did not return bytes for {url}")
    if len(payload) > limit:
        raise PublicWireBuildError(f"remote object exceeds safe size bound: {url}")
    return payload


def _story_snapshot_from_bytes(
    raw: bytes,
    *,
    label: str,
    expected_generation_id: str | None = None,
    expected_manifest_sha256: str | None = None,
) -> StoryManifestSnapshot:
    manifest = _json_bytes(raw, label=label)
    if raw != _canonical_json(manifest):
        raise PublicWireBuildError(f"{label} is not canonical bytes")
    _validate_remote_manifest(manifest)
    generation_id = manifest.get("generation_id")
    packets = manifest.get("packets")
    files = manifest.get("files")
    if not isinstance(generation_id, str) or not isinstance(packets, Mapping) or not isinstance(files, Mapping):
        raise PublicWireBuildError(f"{label} lacks generation, packets, or files")
    if len(packets) > MAX_SOURCE_PACKET_COUNT:
        raise PublicWireBuildError("public story packet catalog exceeds safe count bound")
    manifest_sha = sha256(raw).hexdigest()
    if expected_generation_id is not None and generation_id != expected_generation_id:
        raise PublicWireBuildError(f"{label} generation does not match accepted route state")
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise PublicWireBuildError(f"{label} sha256 does not match accepted route state")
    return StoryManifestSnapshot(
        manifest=dict(manifest),
        raw=raw,
        generation_id=generation_id,
        manifest_sha256=manifest_sha,
    )


def _load_current_story_snapshot(
    *,
    source_base: str,
    fetch: Callable[[str], bytes] | None,
    timeout: float,
) -> StoryManifestSnapshot:
    base = source_base.rstrip("/")
    if not base.startswith("https://"):
        raise PublicWireBuildError("public packet source must use https")
    marker_url = _source_url(base, DEFAULT_SOURCE_MANIFEST)
    marker_raw = _read_remote_bytes(
        marker_url, limit=MAX_MANIFEST_BYTES, timeout=timeout, fetch=fetch,
    )
    marker = _story_snapshot_from_bytes(marker_raw, label="public story packet marker")
    immutable_url = _source_url(
        base, f"earnings_story_packets/generations/{marker.generation_id}/manifest.json",
    )
    immutable_raw = _read_remote_bytes(
        immutable_url, limit=MAX_MANIFEST_BYTES, timeout=timeout, fetch=fetch,
    )
    immutable = _story_snapshot_from_bytes(
        immutable_raw,
        label="immutable public story packet manifest",
        expected_generation_id=marker.generation_id,
        expected_manifest_sha256=marker.manifest_sha256,
    )
    if marker.raw != immutable.raw or marker.manifest != immutable.manifest:
        raise PublicWireBuildError(
            "mutable story packet marker does not equal immutable generation manifest"
        )
    return marker


def _load_prior_story_snapshot(
    state: Mapping[str, Any],
    *,
    source_base: str,
    fetch: Callable[[str], bytes] | None,
    timeout: float,
) -> StoryManifestSnapshot:
    generation_id = str(state["source_generation_id"])
    manifest_sha = str(state["source_manifest_sha256"])
    url = _source_url(
        source_base.rstrip("/"),
        f"earnings_story_packets/generations/{generation_id}/manifest.json",
    )
    raw = _read_remote_bytes(url, limit=MAX_MANIFEST_BYTES, timeout=timeout, fetch=fetch)
    return _story_snapshot_from_bytes(
        raw,
        label="accepted prior story packet manifest",
        expected_generation_id=generation_id,
        expected_manifest_sha256=manifest_sha,
    )


def _load_transcript_index(
    *,
    fetch: Callable[[str], bytes] | None,
    timeout: float,
    index_url: str = DEFAULT_TRANSCRIPT_INDEX_URL,
) -> dict[str, Any]:
    raw = _read_remote_bytes(
        index_url, limit=MAX_TRANSCRIPT_INDEX_BYTES, timeout=timeout, fetch=fetch,
    )
    payload = _json_bytes(raw, label="terminal transcript index")
    generated_at = payload.get("generated_at")
    dates = payload.get("dates")
    if not isinstance(generated_at, str) or len(generated_at) < 10:
        raise PublicWireBuildError("terminal transcript index generated_at is invalid")
    if not isinstance(dates, Mapping):
        raise PublicWireBuildError("terminal transcript index dates map is invalid")
    if len(dates) > MAX_SOURCE_PACKET_COUNT:
        raise PublicWireBuildError("terminal transcript index exceeds safe count bound")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in dates.items()):
        raise PublicWireBuildError("terminal transcript index dates map is invalid")
    return dict(payload)


def _hydrate_publication(
    snapshot: StoryManifestSnapshot,
    *,
    selected_keys: set[str] | frozenset[str],
    source_base: str,
    fetch: Callable[[str], bytes] | None,
    workers: int,
    timeout: float,
) -> dict[str, Any]:
    if workers < 1 or workers > 32:
        raise PublicWireBuildError("workers must be between 1 and 32")
    if timeout <= 0:
        raise PublicWireBuildError("timeout must be positive")
    manifest = snapshot.manifest
    files = manifest.get("files")
    packets = manifest.get("packets")
    policy = manifest.get("policy")
    if not isinstance(files, Mapping) or not isinstance(packets, Mapping) or not isinstance(policy, Mapping):
        raise PublicWireBuildError("public story packet manifest lacks files, packets, or policy")
    policy_snapshot = policy.get("snapshot")
    if not isinstance(policy_snapshot, Mapping):
        raise PublicWireBuildError("public story packet manifest policy is invalid")
    selected = set(selected_keys)
    if len(selected) > MAX_SELECTED_PACKET_COUNT:
        raise PublicWireBuildError("selected packet catalog exceeds safe count bound")
    unknown = selected - set(packets)
    if unknown:
        raise PublicWireBuildError(f"selected packet keys are absent from current source: {sorted(unknown)[:3]}")

    selected_receipts: dict[str, tuple[Mapping[str, Any], str, str, int]] = {}
    selected_bytes = 0
    for event_key in sorted(selected):
        index = packets[event_key]
        if not isinstance(index, Mapping):
            raise PublicWireBuildError(f"packet index is invalid for {event_key}")
        object_key = index.get("object_key")
        if not isinstance(object_key, str):
            raise PublicWireBuildError(f"packet index object key missing for {event_key}")
        receipt = files.get(object_key)
        if not isinstance(receipt, Mapping):
            raise PublicWireBuildError(f"packet receipt missing for {event_key}")
        expected_sha = receipt.get("sha256")
        expected_bytes = receipt.get("bytes")
        if not isinstance(expected_sha, str) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
            raise PublicWireBuildError(f"packet receipt is invalid for {event_key}")
        if expected_bytes > MAX_PACKET_BYTES:
            raise PublicWireBuildError(f"packet receipt exceeds safe size bound for {event_key}")
        selected_bytes += expected_bytes
        if selected_bytes > MAX_SELECTED_PACKET_BYTES:
            raise PublicWireBuildError("selected packet bytes exceed safe bound")
        selected_receipts[event_key] = (index, object_key, expected_sha, expected_bytes)

    base = source_base.rstrip("/")

    def one(event_key: str) -> tuple[str, dict[str, Any] | None]:
        index, object_key, expected_sha, expected_bytes = selected_receipts[event_key]
        packet_url = _source_url(base, f"earnings_story_packets/{object_key}")
        raw_packet = _read_remote_bytes(
            packet_url, limit=MAX_PACKET_BYTES, timeout=timeout, fetch=fetch,
        )
        if len(raw_packet) != expected_bytes or sha256(raw_packet).hexdigest() != expected_sha:
            raise PublicWireBuildError(f"packet receipt mismatch for {event_key}")
        packet = _json_bytes(raw_packet, label=f"story packet {event_key}")
        if packet.get("packet_id") != index.get("packet_id"):
            raise PublicWireBuildError(f"packet identity mismatch for {event_key}")
        story = packet.get("story")
        if (
            not isinstance(story, Mapping)
            or story.get("story_id") != index.get("story_id")
            or story.get("story_revision_id") != index.get("story_revision_id")
        ):
            raise PublicWireBuildError(f"story identity mismatch for {event_key}")
        try:
            validate_story_packet(packet, policy=policy_snapshot)
        except Exception as exc:  # noqa: BLE001 - never skip malformed receipt-bound packets.
            raise PublicWireBuildError(f"story packet contract failed for {event_key}: {exc}") from exc
        digest = packet.get("digest")
        source = story.get("source")
        promotion = story.get("promotion")
        if not (
            story.get("status") == "source_ready"
            and isinstance(promotion, Mapping)
            and promotion.get("article_eligible") is True
            and promotion.get("tier") in {"A", "B"}
            and isinstance(digest, Mapping)
            and digest.get("citation_coverage") == 1.0
            and isinstance(digest.get("quality"), Mapping)
            and digest["quality"].get("status") == "ready"
            and isinstance(source, Mapping)
            and source.get("source_kind") == "transcript"
        ):
            return event_key, None
        article = compile_public_wire_article(
            packet,
            policy_snapshot=policy_snapshot,
            generation_id=snapshot.generation_id,
            object_key=object_key,
            object_sha256=expected_sha,
            object_bytes=expected_bytes,
        )
        expected_event_key = f"{article['event']['ticker']}/{article['event']['transcript_id']}"
        if event_key != expected_event_key:
            raise PublicWireBuildError(f"packet event identity mismatch for {event_key}")
        return event_key, article

    outcomes: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="earnings-wire") as executor:
        futures = {executor.submit(one, key): key for key in sorted(selected)}
        for future in as_completed(futures):
            event_key = futures[future]
            try:
                key, article = future.result()
            except Exception as exc:  # noqa: BLE001 - preserve the first source error and identity.
                for outstanding in futures:
                    outstanding.cancel()
                raise PublicWireBuildError(f"public packet hydration failed at {event_key}: {exc}") from exc
            if article is not None:
                outcomes[key] = article
    if not outcomes:
        raise PublicWireBuildError("selected packet catalog contains no public-wire-eligible exact evidence")
    return build_public_wire_manifest(
        list(outcomes.values()),
        source_generation_id=snapshot.generation_id,
        source_manifest_sha256=snapshot.manifest_sha256,
        source_packet_count=len(packets),
        source_packet_manifest_schema=str(manifest.get("schema") or ""),
        canonical_base=SITE_BASE.rstrip("/"),
    )


def fetch_current_publication(
    *, source_base: str = DEFAULT_SOURCE_BASE,
    fetch: Callable[[str], bytes] | None = None,
    workers: int = 12,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Hydrate one bounded complete source generation for standalone callers."""
    snapshot = _load_current_story_snapshot(
        source_base=source_base, fetch=fetch, timeout=timeout,
    )
    packets = snapshot.manifest.get("packets")
    assert isinstance(packets, Mapping)
    if len(packets) > MAX_SELECTED_PACKET_COUNT:
        raise PublicWireBuildError(
            "standalone full hydration exceeds selected packet safe count; "
            "incremental route state is required"
        )
    return _hydrate_publication(
        snapshot,
        selected_keys=set(packets),
        source_base=source_base,
        fetch=fetch,
        workers=workers,
        timeout=timeout,
    )


def _parse_iso_day(value: object, *, name: str) -> date:
    if not isinstance(value, str):
        raise PublicWireBuildError(f"{name} must be an ISO date")
    normalized = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized) is None:
        raise PublicWireBuildError(f"{name} must be an ISO date")
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise PublicWireBuildError(f"{name} must be an ISO date") from exc


def _latest_route_date(routes: Mapping[str, Any]) -> date:
    latest: date | None = None
    for ticker, raw_route in routes.items():
        if not isinstance(ticker, str) or not isinstance(raw_route, Mapping):
            raise PublicWireBuildError("public earnings wire routes are invalid")
        events = raw_route.get("events")
        if not isinstance(events, Mapping):
            raise PublicWireBuildError("public earnings wire route events are invalid")
        for raw_event in events.values():
            if not isinstance(raw_event, Mapping):
                raise PublicWireBuildError("public earnings wire route event is invalid")
            event_day = _parse_iso_day(
                raw_event.get("date"), name="public earnings wire route event date",
            )
            if latest is None or event_day > latest:
                latest = event_day
    if latest is None:
        raise PublicWireBuildError("public earnings wire routes contain no dated events")
    return latest


def _admitted_packet_keys(state: Mapping[str, Any]) -> frozenset[str]:
    routes = state.get("routes")
    if not isinstance(routes, Mapping):
        raise PublicWireBuildError("public earnings wire state has no routes")
    keys: set[str] = set()
    for ticker, raw_route in routes.items():
        if not isinstance(ticker, str) or not isinstance(raw_route, Mapping):
            raise PublicWireBuildError("public earnings wire routes are invalid")
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise PublicWireBuildError("public earnings wire ticker is invalid")
        events = raw_route.get("events")
        if not isinstance(events, Mapping):
            raise PublicWireBuildError("public earnings wire route events are invalid")
        for fallback_tx, raw_event in events.items():
            if not isinstance(raw_event, Mapping):
                raise PublicWireBuildError("public earnings wire route event is invalid")
            transcript_id = raw_event.get("transcript_id", fallback_tx)
            if not isinstance(transcript_id, str):
                raise PublicWireBuildError("public earnings wire transcript id is invalid")
            normalized_transcript = transcript_id.strip().upper()
            if not normalized_transcript:
                raise PublicWireBuildError("public earnings wire transcript id is invalid")
            keys.add(f"{normalized_ticker}/{normalized_transcript}")
    return frozenset(keys)


def _canonical_packet_key(value: object, *, name: str) -> str:
    if not isinstance(value, str):
        raise PublicWireBuildError(f"{name} must be a packet key")
    parts = value.strip().split("/")
    if len(parts) != 2:
        raise PublicWireBuildError(f"{name} must be a packet key")
    ticker, transcript_id = (part.strip().upper() for part in parts)
    if not ticker or not transcript_id or len(ticker) > 32 or len(transcript_id) > 96:
        raise PublicWireBuildError(f"{name} must be a packet key")
    return f"{ticker}/{transcript_id}"


def _deferred_packet_keys(state: Mapping[str, Any]) -> frozenset[str]:
    raw = state.get("deferred_packet_keys", [])
    if not isinstance(raw, (list, tuple, set, frozenset)):
        raise PublicWireBuildError("deferred packet keys must be a list")
    if len(raw) > MAX_DEFERRED_PACKET_COUNT:
        raise PublicWireBuildError("deferred packet keys exceed safe count bound")
    normalized = {
        _canonical_packet_key(value, name="deferred packet key")
        for value in raw
    }
    if len(normalized) != len(raw):
        raise PublicWireBuildError("deferred packet keys contain duplicates")
    return frozenset(normalized)


def _select_incremental_packet_keys(
    *,
    prior_packets: Mapping[str, Any],
    current_packets: Mapping[str, Any],
    prior_state: Mapping[str, Any],
    transcript_index: Mapping[str, Any] | None,
) -> PacketSelection:
    prior_keys = set(prior_packets)
    current_keys = set(current_packets)

    admitted = set(_admitted_packet_keys(prior_state))
    deferred = set(_deferred_packet_keys(prior_state))
    overlap = admitted & deferred
    if overlap:
        raise PublicWireBuildError(
            f"deferred packet keys overlap admitted routes: {sorted(overlap)[:3]}"
        )
    missing_prior_admitted = admitted - prior_keys
    if missing_prior_admitted:
        raise PublicWireBuildError(
            f"accepted route state is not contained in its source generation: {sorted(missing_prior_admitted)[:3]}"
        )
    missing_prior_deferred = deferred - prior_keys
    if missing_prior_deferred:
        raise PublicWireBuildError(
            f"deferred packet state is not contained in its source generation: {sorted(missing_prior_deferred)[:3]}"
        )
    missing_admitted = admitted - current_keys
    if missing_admitted:
        raise PublicWireBuildError(
            f"current story packet catalog lost admitted keys: {sorted(missing_admitted)[:3]}"
        )
    missing_deferred = deferred - current_keys
    if missing_deferred:
        raise PublicWireBuildError(
            f"current story packet catalog lost deferred keys: {sorted(missing_deferred)[:3]}"
        )
    missing = prior_keys - current_keys
    if missing:
        raise PublicWireBuildError(
            f"current story packet catalog shrank; missing prior keys: {sorted(missing)[:3]}"
        )
    raw_changed = {
        key for key in prior_keys & current_keys
        if current_packets[key] != prior_packets[key]
    }
    new = current_keys - prior_keys
    pending = new | deferred

    floor = _parse_iso_day(
        prior_state.get("forward_selection_floor_date"),
        name="forward selection floor date",
    )
    forward_new: set[str] = set()
    skipped_historical: set[str] = set()
    skipped_future: set[str] = set()
    if pending:
        if not isinstance(transcript_index, Mapping):
            raise PublicWireBuildError("terminal transcript index is required for pending packet selection")
        generated_at = transcript_index.get("generated_at")
        if not isinstance(generated_at, str) or len(generated_at) < 10:
            raise PublicWireBuildError("terminal transcript index generated_at is invalid")
        ceiling = _parse_iso_day(
            generated_at[:10], name="terminal transcript index generated_at",
        )
        dates = transcript_index.get("dates")
        if not isinstance(dates, Mapping):
            raise PublicWireBuildError("terminal transcript index dates map is invalid")
    else:
        ceiling = floor
        dates = {}

    for key in sorted(pending):
        event_day = _parse_iso_day(
            dates.get(key), name=f"terminal transcript date for {key}",
        )
        # The shared transcript index also carries scheduled calls. Persist
        # their bounded identities so advancing the source receipt cannot
        # strand them after the completed-call ceiling catches up.
        if event_day > ceiling:
            skipped_future.add(key)
            continue
        # The persisted floor is inclusive. A source generation can advance
        # during the same UTC day as the newest accepted call, so a strict
        # comparison would permanently strand legitimate same-day additions.
        if event_day >= floor:
            forward_new.add(key)
        else:
            skipped_historical.add(key)

    if len(skipped_future) > MAX_DEFERRED_PACKET_COUNT:
        raise PublicWireBuildError("deferred packet keys exceed safe count bound")
    changed = raw_changed - skipped_future
    selected = admitted | changed | forward_new
    if len(selected) > MAX_SELECTED_PACKET_COUNT:
        raise PublicWireBuildError("selected packet catalog exceeds safe count bound")
    return PacketSelection(
        admitted_keys=frozenset(admitted),
        changed_keys=frozenset(changed),
        forward_new_keys=frozenset(forward_new),
        skipped_historical_keys=frozenset(skipped_historical),
        skipped_future_keys=frozenset(skipped_future),
        selected_keys=frozenset(selected),
    )


def load_public_build_state(
    out_dir: Path, *, strict: bool = False,
) -> dict[str, Any] | None:
    """Read and normalize the redacted public routing state.

    Version 1 is accepted only as a migration source. Its forward-selection
    floor is derived once from the newest already-published event. Version 2
    carries that floor explicitly and must preserve it across later builds.
    Strict callers preserve the first validation cause instead of misreporting
    a corrupt catalog as an uninitialized bootstrap.
    """
    path = Path(out_dir) / ROUTE_CATALOG_FILENAME
    if not path.is_file():
        return None
    def reject(message: str) -> None:
        if strict:
            raise PublicWireBuildError(message)
        return None

    try:
        payload = _json_bytes(path.read_bytes(), label="public earnings wire route catalog")
        common = {
            "schema", "source_generation_id", "source_manifest_sha256", "verified_at",
            "company_generation_id", "renderer_version", "article_count", "as_of", "routes",
        }
        schema = payload.get("schema")
        if schema == ROUTE_CATALOG_SCHEMA_V1:
            if set(payload) != common:
                return reject("public earnings wire v1 route catalog keys are invalid")
        elif schema == ROUTE_CATALOG_SCHEMA_V2:
            v2_required = common | {"forward_selection_floor_date"}
            if set(payload) not in {frozenset(v2_required), frozenset(v2_required | {"deferred_packet_keys"})}:
                return reject("public earnings wire v2 route catalog keys are invalid")
        else:
            return reject("public earnings wire route catalog schema is invalid")
        if not isinstance(payload.get("source_generation_id"), str) or not re.fullmatch(r"[0-9a-f]{32}", payload["source_generation_id"]):
            return reject("public earnings wire source generation id is invalid")
        if not isinstance(payload.get("source_manifest_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", payload["source_manifest_sha256"]):
            return reject("public earnings wire source manifest sha256 is invalid")
        if not isinstance(payload.get("verified_at"), str):
            return reject("public earnings wire verified_at is invalid")
        article_count = payload.get("article_count")
        if not isinstance(article_count, int) or isinstance(article_count, bool) or article_count < 1:
            return reject("public earnings wire article count is invalid")
        if not isinstance(payload.get("as_of"), str):
            return reject("public earnings wire as_of is invalid")
        if payload.get("company_generation_id") is not None and not isinstance(payload.get("company_generation_id"), str):
            return reject("public earnings wire company generation id is invalid")
        if not isinstance(payload.get("renderer_version"), str) or not re.fullmatch(r"[0-9a-f]{64}", payload["renderer_version"]):
            return reject("public earnings wire renderer version is invalid")
        routes = payload.get("routes")
        if not isinstance(routes, Mapping):
            return reject("public earnings wire routes are invalid")
        latest_route_day = _latest_route_date(routes)
        normalized = dict(payload)
        if schema == ROUTE_CATALOG_SCHEMA_V1:
            normalized["forward_selection_floor_date"] = latest_route_day.isoformat()
            normalized["deferred_packet_keys"] = []
        else:
            normalized["forward_selection_floor_date"] = _parse_iso_day(
                payload.get("forward_selection_floor_date"),
                name="forward selection floor date",
            ).isoformat()
            normalized["deferred_packet_keys"] = sorted(_deferred_packet_keys(payload))
        overlap = _admitted_packet_keys(normalized) & set(normalized["deferred_packet_keys"])
        if overlap:
            raise PublicWireBuildError(
                f"deferred packet keys overlap published routes: {sorted(overlap)[:3]}"
            )
        return normalized
    except PublicWireBuildError:
        if strict:
            raise
        return None


def _state_age_seconds(state: Mapping[str, Any], *, now: datetime) -> float:
    value = state.get("verified_at")
    if not isinstance(value, str):
        return float("inf")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    if parsed.tzinfo is None:
        return float("inf")
    return max(0.0, (now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())


def _safe_existing_state_or_raise(out_dir: Path, *, now: datetime) -> dict[str, Any]:
    state = load_public_build_state(out_dir, strict=True)
    if state is None:
        raise PublicWireBuildError("no safe existing earnings-wire build state")
    if _state_age_seconds(state, now=now) > MAX_EXISTING_AGE_SECONDS:
        raise PublicWireBuildError("existing earnings-wire publication is older than 48 hours")
    if not (Path(out_dir) / "index.html").is_file():
        raise PublicWireBuildError("existing earnings-wire publication has no index page")
    return state


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _route_catalog(
    manifest: Mapping[str, Any], *, alignment: Mapping[str, Mapping[str, Any]], verified_at: str,
    company_generation_id: str | None, forward_selection_floor_date: str | None = None,
    deferred_packet_keys: set[str] | frozenset[str] = frozenset(),
) -> bytes:
    """Emit the redacted routing and bounded continuation contract.

    No facts, excerpts, hashes, source locators, or receipt coordinates cross
    this boundary. Deferred identities contain only ticker/transcript ids and
    exist solely so a scheduled call cannot be stranded by a receipt advance.
    """
    routes: dict[str, dict[str, Any]] = {}
    for article in manifest["articles"]:
        event = article["event"]
        ticker = str(event["ticker"])
        tx = str(event["transcript_id"])
        row = alignment.get(str(article["article_id"]), {})
        candidate = {
            "href": f"{event['slug']}.html",
            "period": str(event["period"]),
            "date": str(event["date"]),
            "transcript_id": tx,
            "dossier_available": row.get("dossier_available") is True,
        }
        current = routes.setdefault(ticker, {
            "company_name": str(row.get("company_name") or ticker), "latest": None, "events": {},
        })
        events = current["events"]
        assert isinstance(events, dict)
        events[tx] = candidate
        latest = current["latest"]
        if latest is None or (candidate["date"], candidate["period"], candidate["href"]) > (
            latest["date"], latest["period"], latest["href"]
        ):
            current["latest"] = candidate
    floor = (
        _parse_iso_day(forward_selection_floor_date, name="forward selection floor date")
        if forward_selection_floor_date is not None
        else _latest_route_date(routes)
    )
    normalized_deferred = sorted(_deferred_packet_keys({
        "deferred_packet_keys": deferred_packet_keys,
    }))
    admitted_keys = {
        f"{ticker}/{transcript_id}"
        for ticker, route in routes.items()
        for transcript_id in route["events"]
    }
    overlap = admitted_keys & set(normalized_deferred)
    if overlap:
        raise PublicWireBuildError(
            f"deferred packet keys overlap published routes: {sorted(overlap)[:3]}"
        )
    payload = {
        "schema": ROUTE_CATALOG_SCHEMA,
        "forward_selection_floor_date": floor.isoformat(),
        "deferred_packet_keys": normalized_deferred,
        "source_generation_id": str(manifest["source"]["generation_id"]),
        "source_manifest_sha256": str(manifest["source"]["manifest_sha256"]),
        "company_generation_id": company_generation_id,
        "renderer_version": _renderer_version(),
        "verified_at": verified_at,
        "article_count": len(manifest["articles"]),
        "as_of": max((str(route["lastmod"]) for route in manifest["routes"]), default=""),
        "routes": {
            ticker: {
                "company_name": routes[ticker]["company_name"],
                "latest": routes[ticker]["latest"],
                "events": {tx: routes[ticker]["events"][tx] for tx in sorted(routes[ticker]["events"])},
            }
            for ticker in sorted(routes)
        },
    }
    return _canonical_json(payload)


def _remove_legacy_public_state(out_dir: Path) -> None:
    """Delete the old served bulk manifests after the redacted catalog exists."""
    (out_dir / "article_manifest.json").unlink(missing_ok=True)
    legacy_publications = out_dir / "publications"
    if not legacy_publications.exists():
        return
    if not legacy_publications.is_dir():
        raise PublicWireBuildError("legacy public-wire publications path is not a directory")
    for entry in legacy_publications.iterdir():
        if not entry.is_file() or entry.suffix != ".json":
            raise PublicWireBuildError(f"unexpected file in legacy public-wire state: {entry}")
        entry.unlink()
    legacy_publications.rmdir()




def _copy_assets(out_dir: Path) -> None:
    asset_dir = out_dir / ASSET_DIRNAME
    template_dir = _REPO / "templates" / "earnings_wire"
    for name in ASSET_NAMES:
        source = template_dir / name
        if not source.is_file():
            raise PublicWireBuildError(f"earnings wire asset missing: {source}")
        _atomic_write(asset_dir / name, source.read_bytes())


def _template_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_REPO / "templates")), autoescape=True,
        undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
    )
    # ``seo_base`` owns the bilingual macro. Nested fragments also call ``t``
    # when rendered into a protected payload, so keep their deterministic
    # English fallback available outside a full-page render.
    env.globals["t"] = lambda en, zh="": en
    return env


def _private_output_dir(private_out_dir: Path) -> Path:
    """Require member bytes to stage outside the public repository checkout."""
    candidate = Path(private_out_dir).expanduser().resolve()
    repository = _REPO.resolve()
    if candidate == repository or repository in candidate.parents:
        raise PublicWireBuildError(
            "earnings member output must be outside the public repository"
        )
    return candidate


def _write_premium_payloads(
    views: list[Mapping[str, Any]], *, private_out_dir: Path,
) -> None:
    """Stage member continuations off-repo for private object-store publish."""
    premium_dir = _private_output_dir(private_out_dir) / PRIVATE_RECORDS_DIRNAME
    premium_dir.mkdir(parents=True, exist_ok=True)
    env = _template_environment()
    facts_template = env.get_template("earnings_wire/_facts.html.j2")
    receipts_template = env.get_template("earnings_wire/_receipt_rows.html.j2")
    expected: set[Path] = set()
    for view in views:
        if not view["locked_facts"]:
            continue
        slug = str(view["event"]["slug"])
        destination = premium_dir / f"{slug}.json"
        expected.add(destination)
        payload = {
            "schema": PREMIUM_PAYLOAD_SCHEMA,
            "page": "earnings_wire_article",
            "slug": slug,
            "required_tier": "essential",
            "public_facts": int(view["public_fact_count"]),
            "locked_facts": int(view["locked_fact_count"]),
            "facts_html": facts_template.render(facts=view["locked_facts"]),
            "receipt_rows_html": receipts_template.render(spans=view["locked_spans"]),
        }
        _atomic_write(destination, _canonical_json(payload))
    for candidate in premium_dir.glob("*.json"):
        if candidate not in expected:
            candidate.unlink()


def _write_context_manifest(
    manifest: Mapping[str, Any], *, private_out_dir: Path,
) -> None:
    context_dir = _private_output_dir(private_out_dir) / PRIVATE_CONTEXT_DIRNAME
    context_dir.mkdir(parents=True, exist_ok=True)
    catalog, packets = build_context_generation(manifest)
    expected = {context_dir / CONTEXT_FILENAME}
    for ticker, packet in packets.items():
        destination = context_dir / str(catalog["objects"][ticker]["path"])
        expected.add(destination)
        _atomic_write(destination, context_json_bytes(packet))
    _atomic_write(context_dir / CONTEXT_FILENAME, context_json_bytes(catalog))
    for candidate in context_dir.glob("*.json"):
        if candidate not in expected:
            candidate.unlink()


def _rfc822(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.fromisoformat(value + "T00:00:00+00:00")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return email.utils.format_datetime(parsed.astimezone(timezone.utc), usegmt=True)


def _view_article(article: Mapping[str, Any], *, alignment: Mapping[str, Any]) -> dict[str, Any]:
    """Add UI-only counters and labels without altering the frozen evidence payload."""
    facts = article["facts"]
    spans = [fact["quote"] for fact in facts] + [numeric for fact in facts for numeric in fact["numeric"]]
    spans.sort(key=lambda row: (
        int(row["receipt"]["segment_index"]),
        int(row["receipt"]["span_start_byte"]),
        str(row["claim_id"]),
    ))
    categories = []
    for fact in facts:
        categories.extend(str(item) for item in fact["categories"])
    unique_categories = list(dict.fromkeys(categories))
    public_facts = list(select_public_facts(facts, limit=ARTICLE_PUBLIC_FACT_LIMIT))
    public_claim_ids = {str(fact["claim_id"]) for fact in public_facts}
    locked_facts = [fact for fact in facts if str(fact["claim_id"]) not in public_claim_ids]
    preview = public_facts[0]
    public_claims = {
        str(item["claim_id"])
        for fact in public_facts
        for item in [fact["quote"], *fact["numeric"]]
    }
    public_spans = [span for span in spans if str(span["claim_id"]) in public_claims]
    locked_spans = [span for span in spans if str(span["claim_id"]) not in public_claims]
    ticker = str(article["event"]["ticker"])
    company_name = str(alignment.get("company_name") or ticker).strip() or ticker
    company_label = company_name if company_name.upper() != ticker else ticker
    searchable = " ".join([
        ticker, company_name, str(article["event"]["period"]),
        str(article["event"]["date"]), " ".join(categories),
        " ".join(str(fact["speaker"]) for fact in facts),
    ]).lower()
    return {
        **article,
        "facts": facts,
        "spans": spans,
        "public_facts": public_facts,
        "locked_facts": locked_facts,
        "public_spans": public_spans,
        "locked_spans": locked_spans,
        "fact_count": len(facts),
        "public_fact_count": len(public_facts),
        "locked_fact_count": len(locked_facts),
        "numeric_count": sum(len(fact["numeric"]) for fact in facts),
        "display_categories": [item.replace("_", " ") for item in unique_categories[:3]],
        "category_search": " ".join(unique_categories).lower(),
        "search_text": searchable,
        "preview_quote": preview["quote"]["text"],
        "preview_speaker": preview["speaker"],
        "href": f"{article['event']['slug']}.html",
        "company_name": company_name,
        "company_label": company_label,
        "dossier_available": alignment.get("dossier_available") is True,
        "gate": ({
            "schema": "earnings.member_gate/v1",
            "payload": f"/api/earnings/v1/records/{article['event']['slug']}",
            "slug": str(article["event"]["slug"]),
            "required_tier": "essential",
            "preview": len(public_facts),
            "locked": len(locked_facts),
        } if locked_facts else None),
    }


def _index_jsonld(manifest: Mapping[str, Any], *, route: str, item_count: int) -> str:
    return _safe_jsonld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "MastermindX Earnings Wire",
        "description": "Receipt-bound excerpts from earnings-call transcripts.",
        "url": page_url(route),
        "isPartOf": {"@type": "WebSite", "name": BRAND_NAME, "url": SITE_BASE},
        "numberOfItems": item_count,
    })


def _article_jsonld(article: Mapping[str, Any]) -> str:
    route = f"stocks/earnings/{article['event']['slug']}.html"
    title = f"{article['event']['ticker']} — {article['company_label']} {article['event']['period']} earnings call record"
    return _safe_jsonld({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": f"Receipt-bound excerpts from {article['company_label']}'s earnings-call transcript. Transcript-only source record; not investment advice.",
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url(route)},
        # This is the durable source-record indexing time, not a fabricated
        # editorial publication timestamp.
        "dateCreated": article["source"]["index_generated_at"],
        "dateModified": article["source"]["index_generated_at"],
        "temporalCoverage": article["event"]["date"],
        "author": {"@type": "Organization", "name": BRAND_NAME},
        "publisher": {"@type": "Organization", "name": BRAND_NAME},
        "isBasedOn": f"https://app.mastermind-x.com/terminal?sym={article['event']['ticker']}&pane=transcripts&tx={article['event']['transcript_id']}&from=macro",
    })


def _weekly_jsonld(weekly: Mapping[str, Any], *, route: str) -> str:
    return _safe_jsonld({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"Weekly Earnings Intelligence — {weekly['week_start']}",
        "description": "A deterministic cross-call brief built from exact, receipt-bound earnings transcript excerpts.",
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url(route)},
        "datePublished": weekly["week_end"],
        "dateModified": weekly["knowledge_cutoff"],
        "author": {"@type": "Organization", "name": BRAND_NAME},
        "publisher": {"@type": "Organization", "name": BRAND_NAME},
        "isAccessibleForFree": True,
    })


def _feed(views: list[Mapping[str, Any]]) -> bytes:
    rows = views[:FEED_LIMIT]
    items = []
    for article in rows:
        route = f"stocks/earnings/{article['event']['slug']}.html"
        title = f"{article['event']['ticker']} — {article['company_label']} {article['event']['period']} earnings call record"
        description = f"Receipt-bound excerpts from {article['company_label']}'s earnings-call transcript. Transcript-only source record; not a recommendation."
        items.append(
            "<item>"
            f"<title>{html.escape(title)}</title>"
            f"<link>{html.escape(page_url(route))}</link>"
            f"<guid isPermaLink=\"true\">{html.escape(page_url(route))}</guid>"
            f"<pubDate>{html.escape(_rfc822(str(article['source']['index_generated_at'])))}</pubDate>"
            f"<description><![CDATA[{description}]]></description>"
            "</item>"
        )
    body = "".join(items)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<rss version=\"2.0\"><channel>"
        "<title>MastermindX Earnings Wire</title>"
        f"<link>{html.escape(page_url('stocks/earnings/index.html'))}</link>"
        "<description>Receipt-bound excerpts from company earnings-call transcripts.</description>"
        "<language>en</language>"
        f"{body}</channel></rss>\n"
    ).encode("utf-8")


def _wire_sitemap(manifest: Mapping[str, Any], *, weekly: list[Mapping[str, Any]] | None = None) -> bytes:
    """Build the wire-owned sitemap; the nightly remains sole root owner."""
    routes = list(manifest["routes"])
    latest = max((str(route["lastmod"]) for route in routes), default="")
    rows = [
        "  <url><loc>"
        + html.escape(page_url("stocks/earnings/index.html"), quote=False)
        + "</loc>"
        + (f"<lastmod>{html.escape(latest, quote=False)}</lastmod>" if latest else "")
        + "<changefreq>hourly</changefreq><priority>0.7</priority></url>"
    ]
    rows.extend(
        "  <url><loc>"
        + html.escape(str(route["canonical"]), quote=False)
        + "</loc><lastmod>"
        + html.escape(str(route["lastmod"]), quote=False)
        + "</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>"
        for route in routes
    )
    weeks = weekly or []
    if weeks:
        rows.append(
            "  <url><loc>" + html.escape(page_url("stocks/earnings/weekly/index.html"), quote=False)
            + "</loc><lastmod>" + html.escape(str(weeks[0]["knowledge_cutoff"]), quote=False)
            + "</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>"
        )
        rows.extend(
            "  <url><loc>"
            + html.escape(page_url(f"stocks/earnings/weekly/{row['week_start']}.html"), quote=False)
            + "</loc><lastmod>" + html.escape(str(row["knowledge_cutoff"]), quote=False)
            + "</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>"
            for row in weeks
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    ).encode("utf-8")


def _local_company_name(out_dir: Path, ticker: str) -> str | None:
    """Recover a presentational name from an already-rendered safe ticker page."""
    path = out_dir.parent / f"{ticker}.html"
    if not path.is_file():
        return None
    try:
        title = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"<title>\s*[^<]*?\b" + re.escape(ticker) + r"\b\s*[—-]\s*([^<:|]{2,180})", title, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _company_event_is_exact(event: Mapping[str, Any], *, transcript_id: str, call_date: str) -> bool:
    """Require the same transcript identity (or fiscal tuple) *and* call date."""
    if str(event.get("call_date") or "") != call_date:
        return False
    explicit = str(event.get("transcript_id") or "")
    event_id = str(event.get("event_id") or "")
    if explicit == transcript_id or event_id.rsplit(":", 1)[-1] == transcript_id:
        return True
    year = event.get("fiscal_year")
    quarter = event.get("fiscal_quarter")
    try:
        normalized = f"{int(year)}Q{int(quarter)}"
    except (TypeError, ValueError):
        return False
    return normalized == transcript_id


def _company_alignment_snapshot(
    manifest: Mapping[str, Any], *, out_dir: Path,
    company_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Return a fail-closed, redacted public alignment for every wire article.

    A static ticker page is necessary but not sufficient: an article earns a
    dossier route only when the Company Intelligence history independently
    contains that exact transcript/fiscal tuple on the same call date.  Reader
    outages, partial history, stale quarters and identity mismatches always
    fall back to Terminal rather than manufacturing a cross-layer join.
    """
    reader = company_reader or _company_reader.read_company_intelligence
    by_ticker: dict[str, list[Mapping[str, Any]]] = {}
    for article in manifest["articles"]:
        by_ticker.setdefault(str(article["event"]["ticker"]), []).append(article)
    def read_one(ticker: str) -> tuple[str, Mapping[str, Any]]:
        try:
            result = reader({"ticker": ticker, "limit": 12})
        except Exception:  # noqa: BLE001 - public links must fail closed on reader failure.
            result = {"available": False}
        return ticker, result if isinstance(result, Mapping) else {"available": False}

    contexts: dict[str, Mapping[str, Any]] = {}
    # The reader internally caches the immutable Company snapshot, while this
    # bounded fan-out keeps a new wire generation from taking one network
    # round-trip per ticker serially. Each failed ticker still becomes a
    # Terminal-only CTA; no parallel failure can make a link more permissive.
    with ThreadPoolExecutor(max_workers=min(12, max(1, len(by_ticker))), thread_name_prefix="wire-company-align") as executor:
        futures = {executor.submit(read_one, ticker): ticker for ticker in sorted(by_ticker)}
        for future in as_completed(futures):
            ticker, result = future.result()
            contexts[ticker] = result

    generations = {
        str(context.get("generation_id"))
        for context in contexts.values()
        if isinstance(context.get("generation_id"), str) and context.get("generation_id")
    }
    # A mixed reader snapshot is not a meaningful release receipt.  Preserve
    # the rendered alignment but omit a generation pin, forcing the next same-
    # earnings pass to probe again rather than claiming a false joint snapshot.
    company_generation_id = next(iter(generations)) if len(generations) == 1 else None
    rows: dict[str, dict[str, Any]] = {}
    for ticker, articles in by_ticker.items():
        context = contexts[ticker]
        company = context.get("company") if isinstance(context.get("company"), Mapping) else {}
        reader_name = company.get("display_name") if isinstance(company.get("display_name"), str) else None
        # Local ticker pages are operator-curated presentation surfaces.  Their
        # spelling/casing wins over an upstream all-caps display name, while
        # the reader remains the useful fallback for unrendered pages.
        name = _local_company_name(out_dir, ticker) or reader_name or ticker
        raw_history = context.get("history") if isinstance(context.get("history"), list) else []
        history = [item for item in raw_history if isinstance(item, Mapping)] if context.get("available") is True else []
        latest = context.get("latest_event") if isinstance(context.get("latest_event"), Mapping) else None
        static_dossier = (out_dir.parent / f"{ticker}.html").is_file()
        for article in articles:
            event = article["event"]
            exact_history = any(
                _company_event_is_exact(
                    candidate,
                    transcript_id=str(event["transcript_id"]),
                    call_date=str(event["date"]),
                )
                for candidate in history
            )
            exact_latest = latest is not None and _company_event_is_exact(
                latest,
                transcript_id=str(event["transcript_id"]),
                call_date=str(event["date"]),
            )
            status = "aligned_latest" if exact_latest and static_dossier else (
                "missing_static_dossier" if exact_latest else (
                    "historical_only" if exact_history else "unavailable_or_stale"
                )
            )
            rows[str(article["article_id"])] = {
                "company_name": str(name),
                # The anonymous dossier intentionally returns only its latest
                # event.  A history-only match would make an old public wire
                # page appear to deep-link into its own analysis while the
                # browser actually rendered the latest quarter.
                "dossier_available": exact_latest and static_dossier,
                "alignment_status": status,
            }
    return rows, company_generation_id


def build_company_alignment(
    manifest: Mapping[str, Any], *, out_dir: Path,
    company_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compatibility façade for direct alignment tests and callers."""
    return _company_alignment_snapshot(
        manifest, out_dir=out_dir, company_reader=company_reader,
    )[0]


def _probe_company_generation(
    state: Mapping[str, Any], *, company_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
) -> str | None:
    """Read one covered ticker to decide whether a same-wire run is truly stale."""
    reader = company_reader or _company_reader.read_company_intelligence
    routes = state.get("routes") if isinstance(state.get("routes"), Mapping) else {}
    for ticker in sorted(str(key) for key in routes):
        try:
            result = reader({"ticker": ticker, "limit": 1})
        except Exception:  # noqa: BLE001 - a failed probe never widens publication work.
            return None
        if isinstance(result, Mapping) and isinstance(result.get("generation_id"), str):
            return str(result["generation_id"])
        return None
    return None


def _render_pages(
    manifest: Mapping[str, Any], *, out_dir: Path, alignment: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[Path, str], list[dict[str, Any]], list[dict[str, Any]]]:
    env = _template_environment()
    views = [_view_article(article, alignment=alignment.get(str(article["article_id"]), {})) for article in manifest["articles"]]
    view_by_article = {str(view["article_id"]): view for view in views}
    weekly_contracts = build_weekly_intelligence(manifest)
    weekly_views: list[dict[str, Any]] = []
    for weekly in weekly_contracts:
        row = dict(weekly)
        row["notable_records"] = [
            {
                **record,
                "company_label": view_by_article.get(
                    str(record["identities"]["article_id"]), {}
                ).get("company_label", str(record["event"]["ticker"])),
            }
            for record in weekly["notable_records"]
        ]
        weekly_views.append(row)
    summary = {
        "article_count": len(views),
        "ticker_count": len({str(view["event"]["ticker"]) for view in views}),
        "source_packet_count": int(manifest["source"]["packet_count"]),
        "held_count": max(0, int(manifest["source"]["packet_count"]) - len(views)),
    }
    site = {"base": SITE_BASE, "brand": BRAND_NAME}
    index_template = env.get_template("earnings_wire/earnings_wire_index.html.j2")
    page_count = max(1, (len(views) + INDEX_PAGE_SIZE - 1) // INDEX_PAGE_SIZE)
    rendered: dict[Path, str] = {}
    for page_number in range(1, page_count + 1):
        filename = "index.html" if page_number == 1 else f"page-{page_number}.html"
        route = f"stocks/earnings/{filename}"
        start = (page_number - 1) * INDEX_PAGE_SIZE
        items = views[start:start + INDEX_PAGE_SIZE]
        index_page = {
            "title": "Earnings call records" + (f" — page {page_number}" if page_number > 1 else ""),
            "description": "Receipt-bound excerpts from company earnings-call transcripts.",
            "canonical": page_url(route),
            "url_path": "/" + route,
            "breadcrumbs": [
                {"label": "Home", "href": "/index.html"},
                {"label": "Earnings call records", "href": None},
            ],
        }
        pages = [
            {
                "number": number,
                "href": "index.html" if number == 1 else f"page-{number}.html",
                "current": number == page_number,
            }
            for number in range(1, page_count + 1)
        ]
        rendered[out_dir / filename] = index_template.render(
            page=index_page,
            rel="../../",
            site=site,
            items=items,
            summary=summary,
            latest_week=weekly_views[0] if weekly_views else None,
            pagination={
                "number": page_number,
                "count": page_count,
                "start": start + 1 if items else 0,
                "end": start + len(items),
                "pages": pages,
                "previous": pages[page_number - 2]["href"] if page_number > 1 else None,
                "next": pages[page_number]["href"] if page_number < page_count else None,
            },
            jsonld=_index_jsonld(manifest, route=route, item_count=len(items)),
        )
    article_template = env.get_template("earnings_wire/earnings_wire_article.html.j2")
    for view in views:
        route = f"stocks/earnings/{view['event']['slug']}.html"
        page = {
            "title": f"{view['event']['ticker']} — {view['company_label']} {view['event']['period']} earnings call record",
            "description": f"Receipt-bound excerpts from {view['company_label']}'s {view['event']['period']} earnings call transcript.",
            "canonical": page_url(route),
            "url_path": "/" + route,
            "breadcrumbs": [
                {"label": "Home", "href": "/index.html"},
                {"label": "Earnings call records", "href": "/stocks/earnings/index.html"},
                {"label": str(view["event"]["ticker"]), "href": None},
            ],
        }
        rendered[out_dir / f"{view['event']['slug']}.html"] = article_template.render(
            page=page, rel="../../", site=site, article=view, jsonld=_article_jsonld(view),
        )
    if weekly_views:
        weekly_template = env.get_template("earnings_wire/earnings_weekly.html.j2")
        archive = [
            {
                "week_start": row["week_start"], "call_records": row["coverage"]["call_records"],
                "href": f"{row['week_start']}.html",
            }
            for row in weekly_views
        ]
        render_targets = [("index.html", weekly_views[0]), *[
            (f"{row['week_start']}.html", row) for row in weekly_views
        ]]
        for filename, weekly in render_targets:
            route = f"stocks/earnings/weekly/{filename}"
            page = {
                "title": f"Weekly Earnings Intelligence — {weekly['week_start']}",
                "description": "Cross-call earnings intelligence built from exact, receipt-bound transcript evidence.",
                "canonical": page_url(route),
                "url_path": "/" + route,
                "breadcrumbs": [
                    {"label": "Home", "href": "/index.html"},
                    {"label": "Earnings call records", "href": "/stocks/earnings/index.html"},
                    {"label": "Weekly intelligence", "href": None},
                ],
            }
            rendered[out_dir / "weekly" / filename] = weekly_template.render(
                page=page, rel="../../../", site=site, weekly=weekly,
                archive=[{**item, "current": item["week_start"] == weekly["week_start"]} for item in archive],
                jsonld=_weekly_jsonld(weekly, route=route),
            )
    return rendered, views, weekly_contracts


def _prior_page_paths(out_dir: Path, state: Mapping[str, Any] | None) -> set[Path]:
    """Read stale article names from the prior *redacted* route catalog only."""
    if state is None:
        return set()
    paths: set[Path] = set()
    routes = state.get("routes") if isinstance(state.get("routes"), Mapping) else {}
    for company in routes.values():
        events = company.get("events") if isinstance(company, Mapping) and isinstance(company.get("events"), Mapping) else {}
        for event in events.values():
            href = event.get("href") if isinstance(event, Mapping) else None
            if not isinstance(href, str) or not re.fullmatch(r"[a-z0-9.-]{1,180}\.html", href):
                continue
            paths.add(out_dir / href)
    return paths


def _route_path(out_dir: Path, route: Mapping[str, Any]) -> Path:
    prefix = "/stocks/earnings/"
    raw = str(route["url_path"])
    if not raw.startswith(prefix):
        raise PublicWireBuildError("wire route escapes its public family")
    name = raw[len(prefix):]
    if not name.endswith(".html") or "/" in name or "\\" in name:
        raise PublicWireBuildError("wire route filename is invalid")
    return out_dir / name


def publish_public_wire(
    manifest: Mapping[str, Any], *, out_dir: Path,
    private_out_dir: Path | None = None,
    prior_state: Mapping[str, Any] | None = None,
    deferred_packet_keys: set[str] | frozenset[str] = frozenset(),
    company_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    now: datetime | None = None,
) -> BuildResult:
    """Render a fully verified catalog and atomically replace only wire files."""
    verify_public_wire_manifest(manifest)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    alignment, company_generation_id = _company_alignment_snapshot(
        manifest, out_dir=out_dir, company_reader=company_reader,
    )
    rendered, views, weekly = _render_pages(manifest, out_dir=out_dir, alignment=alignment)
    for destination, markup in rendered.items():
        # All static HTML goes through the shared injection path so this family
        # retains the same data-base bootstrap and future page hygiene as the
        # rest of the public estate.
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_page(destination, markup, encoding="utf-8")
    current_index_pages = {path for path in rendered if path.name == "index.html" or path.name.startswith("page-")}
    for stale_index in out_dir.glob("page-*.html"):
        if stale_index not in current_index_pages:
            stale_index.unlink(missing_ok=True)
    current_weekly_pages = {path for path in rendered if path.parent == out_dir / "weekly"}
    weekly_dir = out_dir / "weekly"
    if weekly_dir.is_dir():
        for stale_week in weekly_dir.glob("*.html"):
            if stale_week not in current_weekly_pages:
                stale_week.unlink(missing_ok=True)
    _copy_assets(out_dir)
    if private_out_dir is not None:
        private_destination = _private_output_dir(private_out_dir)
        _write_premium_payloads(views, private_out_dir=private_destination)
        _write_context_manifest(manifest, private_out_dir=private_destination)
    _atomic_write(out_dir / FEED_FILENAME, _feed(views))
    _atomic_write(out_dir / WIRE_SITEMAP_FILENAME, _wire_sitemap(manifest, weekly=weekly))
    verified_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _atomic_write(
        out_dir / ROUTE_CATALOG_FILENAME,
        _route_catalog(
            manifest, alignment=alignment, verified_at=verified_at,
            company_generation_id=company_generation_id,
            forward_selection_floor_date=(
                str(prior_state["forward_selection_floor_date"])
                if prior_state is not None and prior_state.get("forward_selection_floor_date") is not None
                else None
            ),
            deferred_packet_keys=deferred_packet_keys,
        ),
    )
    _remove_legacy_public_state(out_dir)

    current_paths = {_route_path(out_dir, route) for route in manifest["routes"]}
    if prior_state is not None:
        for stale in _prior_page_paths(out_dir, prior_state) - current_paths:
            stale.unlink(missing_ok=True)
    return BuildResult(str(manifest["manifest_id"]), "remote", len(manifest["articles"]), out_dir)


def build(
    *, out_dir: Path | None = None, source_base: str = DEFAULT_SOURCE_BASE,
    private_out_dir: Path | None = None,
    offline: bool = False, force: bool = False, workers: int = 12, timeout: float = 30.0,
    fetch: Callable[[str], bytes] | None = None,
    company_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    now: datetime | None = None,
) -> BuildResult:
    """Build from current immutable truth with bounded incremental hydration.

    The redacted route catalog identifies the last accepted story generation and
    the fixed forward-selection floor. A refresh rebuilds admitted records,
    re-evaluates corrections, and considers only newly added calls on or after
    that floor. Historical backfill never turns the hourly lane into a corpus replay.
    """
    destination = Path(out_dir) if out_dir is not None else _REPO / "site" / OUTPUT_RELATIVE
    now = now or datetime.now(timezone.utc)
    state = load_public_build_state(destination, strict=True)
    deferred_packet_keys: frozenset[str] = frozenset()
    if offline:
        safe = _safe_existing_state_or_raise(destination, now=now)
        return BuildResult("existing", "existing", int(safe["article_count"]), destination)

    try:
        current = _load_current_story_snapshot(
            source_base=source_base, fetch=fetch, timeout=timeout,
        )
        current_packets = current.manifest.get("packets")
        if not isinstance(current_packets, Mapping):
            raise PublicWireBuildError("current story packet manifest has no packet catalog")

        precomputed_selection: PacketSelection | None = None
        if not force and private_out_dir is None and state is not None and (
            state["source_generation_id"] == current.generation_id
            and state["source_manifest_sha256"] == current.manifest_sha256
            and state["renderer_version"] == _renderer_version()
        ):
            safe = _safe_existing_state_or_raise(destination, now=now)
            company_generation = _probe_company_generation(safe, company_reader=company_reader)
            if company_generation is None or company_generation == safe.get("company_generation_id"):
                deferred = _deferred_packet_keys(safe)
                if not deferred:
                    return BuildResult("unchanged", "unchanged", int(safe["article_count"]), destination)
                transcript_index = _load_transcript_index(fetch=fetch, timeout=timeout)
                precomputed_selection = _select_incremental_packet_keys(
                    prior_packets=current_packets,
                    current_packets=current_packets,
                    prior_state=safe,
                    transcript_index=transcript_index,
                )
                if precomputed_selection.skipped_historical_keys:
                    raise PublicWireBuildError(
                        "deferred packet date predates the preserved forward-selection floor"
                    )
                if not precomputed_selection.forward_new_keys:
                    log.info(
                        "earnings wire deferred selection unchanged: pending=%d source_total=%d",
                        len(precomputed_selection.skipped_future_keys),
                        len(current_packets),
                    )
                    return BuildResult("unchanged", "unchanged", int(safe["article_count"]), destination)

        if state is None:
            if len(current_packets) > MAX_SELECTED_PACKET_COUNT:
                raise PublicWireBuildError(
                    "large story packet catalog requires a valid prior earnings-wire route catalog "
                    "for bounded bootstrap"
                )
            selected_keys = set(current_packets)
        else:
            if (
                state["source_generation_id"] == current.generation_id
                and state["source_manifest_sha256"] == current.manifest_sha256
            ):
                prior = current
            else:
                prior = _load_prior_story_snapshot(
                    state, source_base=source_base, fetch=fetch, timeout=timeout,
                )
            prior_packets = prior.manifest.get("packets")
            if not isinstance(prior_packets, Mapping):
                raise PublicWireBuildError("accepted prior story manifest has no packet catalog")
            if precomputed_selection is not None:
                selection = precomputed_selection
            else:
                needs_dates = bool(
                    set(current_packets) - set(prior_packets)
                    or _deferred_packet_keys(state)
                )
                transcript_index = (
                    _load_transcript_index(fetch=fetch, timeout=timeout)
                    if needs_dates
                    else None
                )
                selection = _select_incremental_packet_keys(
                    prior_packets=prior_packets,
                    current_packets=current_packets,
                    prior_state=state,
                    transcript_index=transcript_index,
                )
            selected_keys = set(selection.selected_keys)
            deferred_packet_keys = selection.skipped_future_keys
            log.info(
                "earnings wire incremental selection: admitted=%d changed=%d "
                "forward_new=%d skipped_historical=%d skipped_future=%d "
                "selected=%d source_total=%d",
                len(selection.admitted_keys),
                len(selection.changed_keys),
                len(selection.forward_new_keys),
                len(selection.skipped_historical_keys),
                len(selection.skipped_future_keys),
                len(selection.selected_keys),
                len(current_packets),
            )

        manifest = _hydrate_publication(
            current,
            selected_keys=selected_keys,
            source_base=source_base,
            fetch=fetch,
            workers=workers,
            timeout=timeout,
        )
    except PublicWireBuildError as fresh_error:
        try:
            safe = _safe_existing_state_or_raise(destination, now=now)
        except PublicWireBuildError as fallback_error:
            raise PublicWireBuildError(
                "fresh earnings wire source failed: "
                f"{fresh_error}; existing publication fallback unavailable: {fallback_error}"
            ) from fresh_error
        log.warning("fresh earnings wire source failed; retaining recent existing publication: %s", fresh_error)
        return BuildResult("existing", "existing", int(safe["article_count"]), destination)

    return publish_public_wire(
        manifest,
        out_dir=destination,
        private_out_dir=private_out_dir,
        prior_state=state,
        deferred_packet_keys=deferred_packet_keys,
        company_reader=company_reader,
        now=now,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build receipt-bound public earnings-call records.")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--private-out-dir",
        type=Path,
        default=None,
        help="Off-repository staging root for member records and context; never written under site/.",
    )
    parser.add_argument("--source-base", default=DEFAULT_SOURCE_BASE)
    parser.add_argument("--offline", action="store_true", help="Validate and retain a recent existing publication without fetching.")
    parser.add_argument(
        "--force", action="store_true",
        help="Rehydrate and render even when the verified source generations are unchanged.",
    )
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        result = build(
            out_dir=args.out_dir,
            private_out_dir=args.private_out_dir,
            source_base=args.source_base, offline=args.offline, force=args.force,
            workers=args.workers, timeout=args.timeout,
        )
    except PublicWireBuildError as exc:
        log.error("earnings public wire failed: %s", exc)
        return 1
    print(json.dumps({
        "schema": "earnings.public_wire_build_result/v1", "status": "ready",
        "source": result.source, "manifest_id": result.manifest_id,
        "article_count": result.article_count, "out_dir": str(result.output_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
