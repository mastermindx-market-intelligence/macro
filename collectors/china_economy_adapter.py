"""Optional acquisition extension of ChinaMacroAdapter, not another adapter.

The existing collect runner owns scheduling, retries, validation and upserts.
Disabled by default. Release selection is constrained by approved source indexes
or exact per-period URLs; a pinned old release never masquerades as a new one.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse

from collectors.china_economy_acquisition import (
    CollectionBatch, checked_url, check_robots, collect_releases, discover_release,
    qualify_against_owner, MAX_BYTES, USER_AGENT,
)
from engine.china_economy import month_from_index, month_index, timestamp


def _period(clock):
    from zoneinfo import ZoneInfo
    now = timestamp(clock()).astimezone(ZoneInfo('Asia/Shanghai'))
    return month_from_index(now.year * 12 + now.month - 2)


def configured_targets(config: dict, http_get, expected_period: str, robots_cache: dict | None = None):
    """Resolve each index at most once; no oldest-working-release fallback."""
    month_index(expected_period)
    robots_cache = robots_cache if robots_cache is not None else {}
    sources = config.get('sources')
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 8:
        raise ValueError('enabled_economy_requires_one_to_eight_sources')
    targets = {}; failures = {}; index_cache = {}; denied_hosts = set()
    for family, spec in sources.items():
        try:
            if not isinstance(spec, dict) or set(spec) - {'url', 'period', 'index_url'}:
                raise ValueError('invalid_source_configuration')
            if ('url' in spec) == ('index_url' in spec):
                raise ValueError('choose_exact_release_or_index_not_both')
            candidate = checked_url(spec.get('url', spec.get('index_url')), family)
            if 'url' in spec:
                if spec.get('period') != expected_period:
                    raise ValueError('configured_release_is_not_expected_period')
                targets[family] = candidate
                continue
            if 'period' in spec:
                raise ValueError('index_configuration_must_not_pin_a_stale_period')
            host = urlparse(candidate).hostname
            if host in denied_hosts:
                raise ValueError('index_host_denied_this_batch')
            if candidate not in index_cache:
                try:
                    check_robots(candidate, http_get, robots_cache)
                    r = http_get(candidate, timeout=15, retries=1, allow_redirects=False,
                                 headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'})
                    if r.status_code in {401, 403, 429}:
                        denied_hosts.add(host)
                    if r.status_code != 200 or getattr(r, 'url', candidate) != candidate:
                        raise ValueError('index_http_status_' + str(r.status_code))
                    if 'text/html' not in r.headers.get('Content-Type', '').lower() or not 0 < len(r.content) <= MAX_BYTES:
                        raise ValueError('index_body_not_admitted')
                    index_cache[candidate] = r.content.decode('utf-8-sig', errors='strict')
                except Exception as exc:
                    response = getattr(exc, 'response', None)
                    if response is not None and response.status_code in {401,403,429}:
                        denied_hosts.add(host)
                    index_cache[candidate] = exc
            index = index_cache[candidate]
            if isinstance(index, Exception):
                raise ValueError('index_acquisition_failed')
            targets[family] = discover_release(index, candidate, family, expected_period)
        except Exception as exc:
            failures[family] = {'error_class': type(exc).__name__,
                                'reason': str(exc)[:100] if isinstance(exc, ValueError) else 'discovery_failed'}
    return targets, failures


def enrich_existing_frames(adapter, legacy_frames, read, *, catalog=None,
                           clock=lambda: datetime.now(timezone.utc)):
    """Called only after the original adapter has produced usable legacy frames.

    Returns (normal runner frames, batch). Records are on the returned batch;
    it is neither a persisted control state nor proof that upsert happened.
    """
    config = adapter.cfg.get('economy_releases', {})
    if not config or (isinstance(config, dict) and config.get('enabled') is not True):
        return legacy_frames, None
    if not legacy_frames:
        raise ValueError('economy_extension_cannot_mask_primary_source_failure')
    batch = CollectionBatch()
    try:
        if not isinstance(config, dict) or set(config) - {'enabled', 'sources'}:
            raise ValueError('invalid_economy_acquisition_configuration')
        if catalog is None:
            path = Path(__file__).resolve().parents[1] / 'config/china_economy_catalog.json'
            catalog = json.loads(path.read_text())['metrics']
        expected = _period(clock)
        robots_cache = {}
        targets, failed = configured_targets(config, adapter.http_get, expected, robots_cache)
        batch = collect_releases(
            targets, expected, adapter.http_get, catalog, clock, robots_cache=robots_cache)
        batch.requested = len(config['sources']); batch.failures.update(failed)
        frames = qualify_against_owner(batch, legacy_frames, read, catalog)
        return frames, batch
    except Exception as exc:
        batch.failures['_configuration_or_owner'] = {
            'error_class': type(exc).__name__,
            'reason': str(exc)[:100] if isinstance(exc, ValueError) else 'extension_failed'}
        return legacy_frames, batch
