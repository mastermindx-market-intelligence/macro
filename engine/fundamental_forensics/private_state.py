"""Private Filing Forensics state transport.

The browser workbench state is deliberately absent from git and GitHub Pages.
Nightly builds publish one validated gzip object to the existing private R2
store; server-side consumers read that object (or the ignored local build copy)
through this module.  The source panels and detector code may be public, but the
assembled premium artifact never gets a public static URL.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Literal

log = logging.getLogger("fundamental_forensics.private_state")

STATE_SCHEMA = "fundamental_forensics_state.v1"
STATE_KEY = "fundamental_forensics/state.json.gz"
LOCAL_STATE_RELATIVE = Path("data/fundamental_forensics/private/state.json.gz")
MAX_COMPRESSED_BYTES = 5 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 32 * 1024 * 1024
DEFAULT_CACHE_SECONDS = 60.0

ORIGIN_LOCAL = "local"
ORIGIN_R2 = "r2"
ORIGIN_LAST_GOOD = "last_good"
ORIGIN_MISSING = "missing"
StateOrigin = Literal["local", "r2", "last_good", "missing"]


class PrivateStateError(RuntimeError):
    """A private-state publish could not be completed lawfully."""


class PrivateStateEffectUnknownError(PrivateStateError):
    """A18: the write's effect on its ORIGINAL target is unknown.

    A lost put-ack whose bounded read-back on the SAME carrier could not
    prove idempotent completion (object absent or unreadable). There is no
    failover key and no unconditional retry inside the publish; the caller
    re-runs ``publish_state_blob`` with the same source once the store is
    observable again. Messages are fixed literals: never a storage key or
    path.
    """


class PrivateStateConflictError(PrivateStateError):
    """The private state object holds different bytes than the publish.

    The read-back after a lost put-ack observed a conflicting object; the
    outcome is neither success nor silently "not published".
    """

_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, bytes]] = {}


@dataclass(frozen=True)
class LoadedState:
    """One state read, with the origin health needs to classify last-good."""

    blob: bytes | None
    origin: StateOrigin

    @property
    def sha256(self) -> str | None:
        if self.blob is None:
            return None
        return hashlib.sha256(self.blob).hexdigest()


def decode_state_blob(blob: bytes) -> dict[str, Any]:
    """Decode and validate the compact transport envelope.

    Size limits are checked before and during decompression so an object-store
    substitution cannot turn this route into an unbounded gzip allocation.
    """
    if not isinstance(blob, bytes) or not blob:
        raise ValueError("state blob is empty")
    if len(blob) > MAX_COMPRESSED_BYTES:
        raise ValueError("compressed state exceeds size limit")
    with gzip.GzipFile(fileobj=io.BytesIO(blob), mode="rb") as fh:
        decoded = fh.read(MAX_DECOMPRESSED_BYTES + 1)
    if len(decoded) > MAX_DECOMPRESSED_BYTES:
        raise ValueError("decompressed state exceeds size limit")
    doc = json.loads(decoded)
    if not isinstance(doc, dict) or doc.get("schema") != STATE_SCHEMA:
        raise ValueError("unsupported forensics state schema")
    if not isinstance(doc.get("companies"), dict):
        raise ValueError("forensics state companies must be an object")
    if not isinstance(doc.get("generated_at"), str) or not doc["generated_at"]:
        raise ValueError("forensics state generated_at is missing")
    return doc


def local_state_path(root: str | Path) -> Path:
    return Path(root) / LOCAL_STATE_RELATIVE


def _private_store():
    from engine.research_vault.r2_store import build_store  # noqa: PLC0415
    return build_store()


def clear_state_cache() -> None:
    """Test/operator hook; production refreshes naturally on the short TTL."""
    with _cache_lock:
        _cache.clear()


def load_state_record(
    root: str | Path,
    *,
    store_factory: Callable[[], Any] | None = None,
    cache_seconds: float | None = DEFAULT_CACHE_SECONDS,
) -> LoadedState:
    """Return a validated blob plus the origin health uses to flag last-good."""
    ttl = DEFAULT_CACHE_SECONDS if cache_seconds is None else cache_seconds
    root_path = Path(root)
    local = local_state_path(root_path)
    if local.is_file():
        try:
            blob = local.read_bytes()
            decode_state_blob(blob)
            return LoadedState(blob=blob, origin=ORIGIN_LOCAL)
        except Exception as exc:  # noqa: BLE001
            log.warning("ignored invalid local forensics state %s: %s", local, exc)

    factory = store_factory or _private_store
    cache_key = f"{root_path.resolve()}::{id(factory)}"
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now < cached[0]:
            return LoadedState(blob=cached[1], origin=ORIGIN_R2)

    try:
        store = factory()
        blob = store.get_bytes(STATE_KEY) if store is not None else None
        if blob is not None:
            decode_state_blob(blob)
            with _cache_lock:
                _cache[cache_key] = (now + max(0.0, ttl), blob)
            return LoadedState(blob=blob, origin=ORIGIN_R2)
    except Exception as exc:  # noqa: BLE001
        log.warning("private forensics state fetch failed: %s", exc)

    # Availability fallback: an already-validated in-process copy is safer than
    # turning a transient object-store miss into a blank paid product.
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached:
            return LoadedState(blob=cached[1], origin=ORIGIN_LAST_GOOD)
    return LoadedState(blob=None, origin=ORIGIN_MISSING)


def load_state_blob(
    root: str | Path,
    *,
    store_factory: Callable[[], Any] | None = None,
    cache_seconds: float = DEFAULT_CACHE_SECONDS,
) -> bytes | None:
    """Return a validated local/private-R2 blob, retaining last-good on R2 error."""
    return load_state_record(
        root,
        store_factory=store_factory,
        cache_seconds=cache_seconds,
    ).blob


def load_state(
    root: str | Path,
    *,
    store_factory: Callable[[], Any] | None = None,
    cache_seconds: float = DEFAULT_CACHE_SECONDS,
) -> dict[str, Any] | None:
    blob = load_state_blob(root, store_factory=store_factory, cache_seconds=cache_seconds)
    if blob is None:
        return None
    try:
        return decode_state_blob(blob)
    except Exception as exc:  # pragma: no cover - load_state_blob already validates
        log.warning("private forensics state decode failed: %s", exc)
        return None


def _reconcile_state_write(store: Any, blob: bytes, *, cause: BaseException | None) -> None:
    """A18 reconciliation for a lost put-ack: ONE bounded read-back, no retry.

    Exact bytes prove idempotent completion (return normally). Different
    bytes are a conflict; an absent or unreadable object leaves the effect on
    the original target unknown. Never a second ``put_bytes``, never a
    failover key, and never a key/path in the raised message.
    """
    try:
        echoed = store.get_bytes(STATE_KEY)
    except Exception as read_exc:  # noqa: BLE001 - unreadable == unproven
        raise PrivateStateEffectUnknownError(
            "private forensics state write outcome could not be reconciled"
        ) from read_exc
    if echoed is None:
        raise PrivateStateEffectUnknownError(
            "private forensics state write outcome could not be reconciled"
        ) from cause
    if echoed != blob:
        raise PrivateStateConflictError(
            "private forensics state object conflicts with the published bytes"
        ) from cause


def publish_state_blob(path: str | Path, *, store_factory: Callable[[], Any] | None = None) -> bool:
    """Publish and byte-verify one state object in the private store.

    A18 write discipline (FIF P1 / F4): an exceptional or ``False`` put
    outcome is reconciled by exactly one bounded read-back on the SAME
    carrier — exact bytes prove idempotent completion; different bytes raise
    :class:`PrivateStateConflictError`; an absent or unreadable object
    raises :class:`PrivateStateEffectUnknownError` (returning neither True
    nor False). ``put_bytes`` is never called a second time inside this
    function, and the last-good READ fallback in ``load_state_record`` is
    read-side availability, never a write success.
    """
    source = Path(path)
    try:
        blob = source.read_bytes()
        decode_state_blob(blob)
        store = (store_factory or _private_store)()
        if store is None:
            log.error("private forensics store is unavailable")
            return False
    except Exception as exc:  # noqa: BLE001
        log.error("private forensics state publish failed: %s", exc)
        return False
    try:
        written = store.put_bytes(STATE_KEY, blob, "application/gzip")
    except Exception as exc:  # noqa: BLE001 - the commit may have succeeded
        _reconcile_state_write(store, blob, cause=exc)
    else:
        if written is False:
            _reconcile_state_write(store, blob, cause=None)
    echoed = store.get_bytes(STATE_KEY)
    if echoed is None or hashlib.sha256(echoed).digest() != hashlib.sha256(blob).digest():
        log.error("private forensics state read-back mismatch")
        return False
    decode_state_blob(echoed)
    clear_state_cache()
    return True
