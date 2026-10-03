"""Optional acquisition extension of ChinaMacroAdapter, not another adapter.

The existing collect runner owns scheduling, retries, validation and upserts.
Release discovery follows each source family's admitted store cursor; a source
that has not published its next period is pending, not a failed collector.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from collectors.china_economy_acquisition import (
    CollectionBatch, checked_url, check_robots, collect_releases, discover_release,
    indexed_releases, qualify_against_owner, MAX_BYTES, USER_AGENT, VERSION,
)
from engine.china_economy import month_from_index, month_index, timestamp, select_observations
from engine.china_economy_store import document_from_store

# Automatic index discovery is commissioned only for these NBS release families.
# Other families remain exact-URL only until their own index contract is reviewed.
AUTO_INDEX_FAMILIES = frozenset({"industry", "retail", "investment", "pmi", "profits"})
ANCHOR_METRICS = {
    "industry": "industrial_sa",
    "retail": "retail_sa",
    "investment": "investment_sa",
    "pmi": "pmi_mfg",
    "profits": "profits_ytd",
    "fiscal": "fiscal_general_spending_growth",
    "safe": "external_receipts",
    "power": "power_total",
}
# NBS release-calendar note: no standalone January report for these families;
# the next official observation is the January-February report labelled February.
JANUARY_OMISSION_FAMILIES = frozenset({"industry", "retail", "investment", "profits"})


def _period(clock):
    now = timestamp(clock()).astimezone(ZoneInfo("Asia/Shanghai"))
    return month_from_index(now.year * 12 + now.month - 2)


def _current_period(now: datetime) -> str:
    local = timestamp(now).astimezone(ZoneInfo("Asia/Shanghai"))
    return month_from_index(local.year * 12 + local.month - 1)


def _next_reported_period(family: str, period: str) -> str:
    nxt = month_from_index(month_index(period) + 1)
    if nxt.endswith("-01") and family in JANUARY_OMISSION_FAMILIES:
        nxt = month_from_index(month_index(nxt) + 1)
    return nxt


def _latest_admitted_cursor(read, catalog: dict, family: str,
                            as_of: datetime) -> tuple[str | None, str | None]:
    """Read period + parser vintage through the same receipt admission as the UI."""
    ident = ANCHOR_METRICS.get(family)
    meta = catalog.get(ident) if ident else None
    if not isinstance(meta, dict):
        return None, None
    document = document_from_store(
        read, {ident: meta}, as_of=as_of, reference_period=_period(lambda: as_of)
    )
    raw_rows = document.get("observations", [])
    rows, problems = select_observations(meta, raw_rows, document["sources"], as_of)
    if not rows:
        if problems or document.get("source_errors"):
            raise ValueError("store_cursor_unverified")
        return None, None
    latest = max(rows, key=lambda row: month_index(row["period"]))
    if (latest.get("value") is None or any(
            p.get("period") and month_index(p["period"]) >= month_index(latest["period"])
            for p in problems)):
        raise ValueError("store_cursor_unverified")
    source = document.get("sources", {}).get(latest.get("source_id"), {})
    parser_version = source.get("parser_version")
    return latest["period"], parser_version if isinstance(parser_version, str) else None


def _latest_admitted_period(read, catalog: dict, family: str, as_of: datetime) -> str | None:
    """Backward-compatible period-only cursor helper."""
    return _latest_admitted_cursor(read, catalog, family, as_of)[0]


def _load_index(candidate: str, family: str, http_get, robots_cache: dict,
                index_cache: dict, denied_hosts: set[str]) -> str:
    host = urlparse(candidate).hostname
    if host in denied_hosts:
        raise ValueError("index_host_denied_this_batch")
    if candidate not in index_cache:
        try:
            check_robots(candidate, http_get, robots_cache)
            response = http_get(
                candidate, timeout=15, retries=1, allow_redirects=False,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            )
            if response.status_code in {401, 403, 429}:
                denied_hosts.add(host)
            if response.status_code != 200 or getattr(response, "url", candidate) != candidate:
                raise ValueError("index_http_status_" + str(response.status_code))
            if ("text/html" not in response.headers.get("Content-Type", "").lower()
                    or not 0 < len(response.content) <= MAX_BYTES):
                raise ValueError("index_body_not_admitted")
            index_cache[candidate] = response.content.decode("utf-8-sig", errors="strict")
        except Exception as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code in {401, 403, 429}:
                denied_hosts.add(host)
            index_cache[candidate] = exc
    index = index_cache[candidate]
    if isinstance(index, Exception):
        raise ValueError("index_acquisition_failed")
    return index


def _validated_sources(config: dict) -> dict:
    sources = config.get("sources")
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 8:
        raise ValueError("enabled_economy_requires_one_to_eight_sources")
    return sources


def configured_targets(config: dict, http_get, expected_period: str,
                       robots_cache: dict | None = None):
    """Compatibility helper: resolve one explicitly requested period."""
    month_index(expected_period)
    robots_cache = robots_cache if robots_cache is not None else {}
    sources = _validated_sources(config)
    targets = {}; failures = {}; index_cache = {}; denied_hosts: set[str] = set()
    for family, spec in sources.items():
        try:
            if not isinstance(spec, dict) or set(spec) - {"url", "period", "index_url"}:
                raise ValueError("invalid_source_configuration")
            if ("url" in spec) == ("index_url" in spec):
                raise ValueError("choose_exact_release_or_index_not_both")
            candidate = checked_url(spec.get("url", spec.get("index_url")), family)
            if "url" in spec:
                if spec.get("period") != expected_period:
                    raise ValueError("configured_release_is_not_expected_period")
                targets[family] = candidate
                continue
            if "period" in spec:
                raise ValueError("index_configuration_must_not_pin_a_stale_period")
            index = _load_index(
                candidate, family, http_get, robots_cache, index_cache, denied_hosts
            )
            targets[family] = discover_release(index, candidate, family, expected_period)
        except Exception as exc:
            failures[family] = {
                "error_class": type(exc).__name__,
                "reason": str(exc)[:100] if isinstance(exc, ValueError) else "discovery_failed",
            }
    return targets, failures


def planned_targets(config: dict, http_get, read, catalog: dict, *,
                    clock=lambda: datetime.now(timezone.utc),
                    robots_cache: dict | None = None):
    """Plan each family from its own admitted publication cursor.

    Pending means the publisher has not yet published the next expected period.
    A later indexed period with the expected successor missing is a hard gap:
    never jump over a missing release merely to look fresh.
    """
    sources = _validated_sources(config)
    robots_cache = robots_cache if robots_cache is not None else {}
    now = timestamp(clock())
    current = _current_period(now)
    targets = {}; pending = {}; failures = {}
    index_cache = {}; denied_hosts: set[str] = set()

    for family, spec in sources.items():
        try:
            if not isinstance(spec, dict) or set(spec) - {"url", "period", "index_url"}:
                raise ValueError("invalid_source_configuration")
            if ("url" in spec) == ("index_url" in spec):
                raise ValueError("choose_exact_release_or_index_not_both")
            candidate = checked_url(spec.get("url", spec.get("index_url")), family)

            if "url" in spec:
                period = spec.get("period")
                month_index(period)
                if month_index(period) > month_index(current):
                    raise ValueError("configured_release_period_is_future")
                targets[family] = {"url": candidate, "period": period}
                continue

            if family not in AUTO_INDEX_FAMILIES:
                raise ValueError("index_auto_discovery_not_reviewed_for_family")
            if "period" in spec:
                raise ValueError("index_configuration_must_not_pin_a_stale_period")

            index = _load_index(
                candidate, family, http_get, robots_cache, index_cache, denied_hosts
            )
            releases = {
                period: url for period, url in indexed_releases(
                    index, candidate, family
                ).items()
                if month_index(period) <= month_index(current)
            }
            if not releases:
                raise ValueError("index_has_no_eligible_release")

            latest, parser_version = _latest_admitted_cursor(
                read, catalog, family, now)
            newest = max(releases, key=month_index)
            if latest is None:
                targets[family] = {"url": releases[newest], "period": newest}
                continue
            if month_index(latest) > month_index(current):
                raise ValueError("admitted_store_period_is_future")
            if month_index(newest) < month_index(latest):
                raise ValueError("publisher_index_behind_admitted_store")

            # A parser repair must be able to heal the latest admitted release
            # even when no newer month has published yet. Re-acquire exactly the
            # same official release once under the new parser version; after its
            # receipt is upserted, normal next-period planning resumes. If a newer
            # release already exists, take that release instead so current data is
            # never delayed merely to refresh an older parser vintage.
            if newest == latest and parser_version != VERSION:
                targets[family] = {"url": releases[latest], "period": latest}
                continue

            expected = _next_reported_period(family, latest)
            if expected in releases:
                targets[family] = {"url": releases[expected], "period": expected}
                continue
            later = [p for p in releases if month_index(p) > month_index(expected)]
            if later:
                raise ValueError("sequential_release_gap")
            pending[family] = {
                "reason": "not_yet_published",
                "current_store_period": latest,
                "expected_period": expected,
                "latest_index_period": newest,
            }
        except Exception as exc:
            failures[family] = {
                "error_class": type(exc).__name__,
                "reason": str(exc)[:100] if isinstance(exc, ValueError) else "discovery_failed",
            }
    return targets, pending, failures


def enrich_existing_frames(adapter, legacy_frames, read, *, catalog=None,
                           clock=lambda: datetime.now(timezone.utc)):
    """Called only after the original adapter has produced usable legacy frames.

    Returns (normal runner frames, batch). Records are on the returned batch;
    it is neither a persisted control state nor proof that upsert happened.
    """
    config = adapter.cfg.get("economy_releases", {})
    if not config or (isinstance(config, dict) and config.get("enabled") is not True):
        return legacy_frames, None
    if not legacy_frames:
        raise ValueError("economy_extension_cannot_mask_primary_source_failure")
    batch = CollectionBatch()
    try:
        if not isinstance(config, dict) or set(config) - {"enabled", "sources"}:
            raise ValueError("invalid_economy_acquisition_configuration")
        if catalog is None:
            path = Path(__file__).resolve().parents[1] / "config/china_economy_catalog.json"
            catalog = json.loads(path.read_text())["metrics"]
        observed = timestamp(clock())
        robots_cache = {}
        targets, pending, failed = planned_targets(
            config, adapter.http_get, read, catalog,
            clock=lambda: observed, robots_cache=robots_cache,
        )
        batch = collect_releases(
            targets, None, adapter.http_get, catalog,
            lambda: observed, robots_cache=robots_cache,
        )
        batch.requested = len(config["sources"])
        batch.pending.update(pending)
        batch.failures.update(failed)
        frames = qualify_against_owner(batch, legacy_frames, read, catalog)
        return frames, batch
    except Exception as exc:
        batch.failures["_configuration_or_owner"] = {
            "error_class": type(exc).__name__,
            "reason": str(exc)[:100] if isinstance(exc, ValueError) else "extension_failed",
        }
        return legacy_frames, batch
