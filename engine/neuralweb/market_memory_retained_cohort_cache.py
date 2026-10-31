"""Private bounded, thread-safe LRU storage for sealed cohort capabilities.

Scope: this module is finite storage only. It retains already-sealed
``RetainedContextCohortCapability`` objects addressed by exact tuple keys and
performs no authorization, disclosure, policy, rights or admission work of any
kind. The owner of the surrounding request path integrates it.

Caller authorization requirement (explicit): a cache hit is not an
authorization decision. Current authorization is ALWAYS performed by the
caller after ``BoundedCohortCache.get`` and before any use of the returned
object. The cache never rechecks policy, never discloses capability contents
and never grants any right; ``get`` returns whichever sealed object is
currently retained under the key, or ``None``.

Bounds semantics: the cache keeps at most ``max_entries`` entries (positive
exact int, capped at 8) whose accounted payload totals at most ``max_bytes``
(positive exact int, capped at 16 MiB). Accounted payload for one entry is
the UTF-8 length of the key plus the retained cohort ``_body``/``_resource``
byte lengths and the UTF-8 length of the cohort ``_digest``, plus the same
body/resource/digest accounting for every aligned feature slot that holds an
exact ``EpisodeFeatureCapability``. These byte limits bound retained payload
bytes only; they do not bound exact interpreter RSS. Accounting walks the
aligned feature tuple once, costs O(number of aligned features) and is capped
at ``_MAX_CAPTURES`` (256) features; malformed shape or counter inputs are
rejected, never clamped and never partially stored.

Concurrency: one ``threading.Lock`` guards the finite entry map and the
running byte total, and nothing but those dictionary operations runs under
it. Payload measurement happens outside the lock because the retained classes
are pinned sealed immutable objects. There are no callbacks, I/O, scheduler,
service, singleflight, TTL, inflight jobs, environment access, global cache
instance or registry here, and nothing is ever printed.

Malformed keys, bounds and capability shapes raise ``BoundedCohortCacheError``
with fixed diagnostic codes that never contain key parts, payload bytes or
other caller input.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from engine.neuralweb.market_memory_episode_features import (
    EpisodeFeatureCapability,
)
from engine.neuralweb.market_memory_retained_context_cohort import (
    RetainedContextCohortCapability,
)

__all__ = ["BoundedCohortCache", "BoundedCohortCacheError"]


_MAX_ENTRIES_LIMIT = 8
_MAX_BYTES_LIMIT = 16 * 1024 * 1024
_MAX_KEY_PARTS = 16
_MAX_KEY_PART_CHARS = 4096
_MAX_CAPTURES = 256


class BoundedCohortCacheError(Exception):
    """Raised for malformed cache arguments; messages carry no caller input."""


class _CohortEntry:
    """One retained map slot: the sealed capability and its accounted bytes."""

    __slots__ = ("capability", "cost")

    def __init__(self, capability, cost):
        self.capability = capability
        self.cost = cost


def _validated_key(key):
    """Return ``key`` unchanged after exact shape validation (never echoed)."""
    if type(key) is not tuple:
        raise BoundedCohortCacheError("cohort_cache_key_must_be_exact_tuple")
    if len(key) < 1 or len(key) > _MAX_KEY_PARTS:
        raise BoundedCohortCacheError("cohort_cache_key_part_count_out_of_range")
    for part in key:
        if type(part) is not str:
            raise BoundedCohortCacheError("cohort_cache_key_part_must_be_exact_str")
        if len(part) < 1 or len(part) > _MAX_KEY_PART_CHARS:
            raise BoundedCohortCacheError("cohort_cache_key_part_length_out_of_range")
    return key


def _validated_bound(value, limit, code):
    """Return ``value`` as a positive exact int within ``limit``; bool refused."""
    if type(value) is not int:
        raise BoundedCohortCacheError(code)
    if value < 1 or value > limit:
        raise BoundedCohortCacheError(code)
    return value


def _sealed_attr(owner, name, expected_type, code):
    """Read one pinned private attribute and require its exact type."""
    try:
        value = getattr(owner, name)
    except AttributeError:
        raise BoundedCohortCacheError(code) from None
    if type(value) is not expected_type:
        raise BoundedCohortCacheError(code)
    return value


def _utf8_length(text):
    return len(text.encode("utf-8"))


def _key_utf8_bytes(key):
    return sum(_utf8_length(part) for part in key)


def _capability_payload_bytes(capability):
    """Account retained payload bytes for one cohort capability.

    Counts the cohort ``_body``/``_resource`` byte lengths plus the UTF-8
    length of ``_digest``, then the same accounting for every aligned feature
    slot. The walk is O(number of aligned features) and is capped by
    ``_MAX_CAPTURES``; malformed shape or counter inputs raise instead of
    being clamped. The capability is never serialized and never mutated.
    """
    if type(capability) is not RetainedContextCohortCapability:
        raise BoundedCohortCacheError("cohort_cache_capability_type_invalid")
    body = _sealed_attr(
        capability, "_body", bytes, "cohort_cache_capability_body_type_invalid"
    )
    resource = _sealed_attr(
        capability, "_resource", bytes, "cohort_cache_capability_resource_type_invalid"
    )
    digest = _sealed_attr(
        capability, "_digest", str, "cohort_cache_capability_digest_type_invalid"
    )
    features = _sealed_attr(
        capability, "_features", tuple, "cohort_cache_capability_features_type_invalid"
    )
    if len(features) > _MAX_CAPTURES:
        raise BoundedCohortCacheError("cohort_cache_feature_count_out_of_range")
    total = len(body) + len(resource) + _utf8_length(digest)
    for feature in features:
        if feature is None:
            continue
        if type(feature) is not EpisodeFeatureCapability:
            raise BoundedCohortCacheError("cohort_cache_feature_type_invalid")
        feature_body = _sealed_attr(
            feature, "_body", bytes, "cohort_cache_feature_body_type_invalid"
        )
        feature_resource = _sealed_attr(
            feature, "_resource", bytes, "cohort_cache_feature_resource_type_invalid"
        )
        feature_digest = _sealed_attr(
            feature, "_digest", str, "cohort_cache_feature_digest_type_invalid"
        )
        total += (
            len(feature_body) + len(feature_resource) + _utf8_length(feature_digest)
        )
    return total


class BoundedCohortCache:
    """Finite thread-safe LRU map from exact tuple keys to sealed cohorts.

    Storage only: current authorization is always performed by the caller
    after ``get`` and before use of a returned capability. Retained objects
    are never serialized, mutated, disclosed or authenticated here.
    """

    def __init__(self, max_entries=8, max_bytes=16 * 1024 * 1024):
        self._max_entries = _validated_bound(
            max_entries, _MAX_ENTRIES_LIMIT, "cohort_cache_max_entries_out_of_range"
        )
        self._max_bytes = _validated_bound(
            max_bytes, _MAX_BYTES_LIMIT, "cohort_cache_max_bytes_out_of_range"
        )
        self._lock = threading.Lock()
        self._entries = OrderedDict()
        self._retained_bytes = 0

    def get(self, key: tuple) -> RetainedContextCohortCapability | None:
        """Return the currently retained capability for ``key``, else ``None``.

        A hit promotes the entry to most-recently-used. The caller must
        perform current authorization after this returns and before any use
        of the returned object; a hit grants nothing by itself.
        """
        _validated_key(key)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry.capability

    def put(self, key: tuple, capability: RetainedContextCohortCapability) -> bool:
        """Retain ``capability`` under ``key``; ``True`` when retained.

        A valid payload whose accounted bytes exceed ``max_bytes`` is refused
        with ``False`` and evicts nothing. Replacing an existing key adjusts
        the byte total exactly once and refreshes recency. Eviction removes
        least-recently-used entries until both the entry and byte bounds fit;
        the payload just stored is always within both bounds, so it is never
        its own eviction victim. Malformed keys or capability shapes raise
        before any map mutation.
        """
        _validated_key(key)
        cost = _key_utf8_bytes(key) + _capability_payload_bytes(capability)
        if cost > self._max_bytes:
            return False
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None and existing.capability is capability:
                self._entries.move_to_end(key)
                return True
            if existing is not None:
                self._retained_bytes -= existing.cost
                del self._entries[key]
            self._entries[key] = _CohortEntry(capability, cost)
            self._retained_bytes += cost
            while (
                len(self._entries) > self._max_entries
                or self._retained_bytes > self._max_bytes
            ):
                _, evicted = self._entries.popitem(last=False)
                self._retained_bytes -= evicted.cost
        return True

    def discard(self, key: tuple, capability: RetainedContextCohortCapability) -> bool:
        """Remove ``key`` only if it currently retains this exact capability.

        Identity-conditional: an older capability object (for example one held
        from a read that was later denied) can never evict a newer replacement
        retained under the same key. Returns ``True`` only when an entry was
        removed and its accounting released.
        """
        _validated_key(key)
        if type(capability) is not RetainedContextCohortCapability:
            return False
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.capability is not capability:
                return False
            del self._entries[key]
            self._retained_bytes -= entry.cost
        return True
