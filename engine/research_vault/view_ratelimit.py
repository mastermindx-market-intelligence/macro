"""research_vault.view_ratelimit — per-user+IP hourly soft cap on /view (RV W2).

``/api/research/view`` streams the FULL PDF bytes to an authenticated paid user,
so it is the surface a subscriber could script to bulk-scrape the whole vault.
The download route is quota-metered (5/20 a day); the *view* route is not, so it
needs its own anti-scrape control. This is that control: a soft hourly cap keyed
on BOTH the user id AND the client IP (a shared account behind one box still gets
throttled; a rotating-IP scraper on one account still gets throttled).

Default cap: ~60 views/hour (env ``RESEARCH_VIEW_HOURLY`` overrides). Period = UTC
hour (``YYYY-MM-DDTHH``). Dual ledger, allowed only if BOTH are under the cap; on
allow BOTH increment. Reported ``remaining`` is the WORSE of the two.

SECURITY:
  * The raw IP is NEVER written to a filename — it is sha256-hashed first, so the
    ledger dir cannot leak visitor IPs and a crafted IP string cannot inject a
    path (the hash is hex-only). ``_safe_uid`` further sanitizes both keys.
  * Fail-OPEN but LOUD on ledger I/O error — a broken state dir must not hard-lock
    a paying subscriber out of the viewer (same rule as the download quota).

State layout (mirrors the download quota, separate subdir):
    $MACRO_API_STATE_DIR/research_view_rl/vh_{safe_uid}_{YYYY-MM-DDTHH}.json   (user)
    $MACRO_API_STATE_DIR/research_view_rl/vip_{iphash}_{YYYY-MM-DDTHH}.json    (IP)

Pure + stdlib-only → offline-testable; ``now`` is injectable for period tests.

Brain pair metering (atomic, added)
---------------------------------------------------------------------------
``preflight_many(user_id, report_ids, now=None) -> bool`` and
``commit_many(user_id, report_ids, now=None) -> bool`` meter a Brain *pair*
view (up to 2 report ids) against the SAME canonical per-user JSON ledger and
the SAME hourly cap / accounting as the ordinary web/Brain allow — never two
sequential allows and never a separate counter or budget file. JSON stays the
canonical owner of the state; no migration to another store is introduced.

  * ``preflight_many`` is advisory: no charge, no lock. Malformed or uncertain
    ledger state fails closed (False).
  * ``commit_many`` RECHECKS capacity UNDER the same per-user/per-IP locks the
    ordinary allow takes, in the SAME acquisition order (user lock, then IP
    lock), so a concurrent web allow and Brain commit cannot lose each other's
    user/IP update. It then charges ``len(dedup(report_ids))`` with ONE atomic
    canonical user-file replacement (tmp write + ``os.replace``).
  * The Brain IP leg is synthetic (``brain:<uid>`` hashed like any IP) and
    REDUNDANT: it is mirrored best-effort for ledger parity, but it can never
    gate — and its failure can never deny — a proven canonical user commit.
  * The Brain path is deliberately stricter than ordinary allow: malformed,
    unwritable or uncertain (locks unavailable) canonical state fails CLOSED
    (False, no output) BEFORE output, because the caller streams the report
    bytes only on True. Ordinary ``allow`` keeps its legacy fail-open-but-loud
    availability policy.
  * Malformed CALL arguments (empty/overlong uid, non-list ids, >2 ids,
    empty/overlong/non-string ids) raise ``RateLimitArgError`` — that is a
    protocol bug, not a capacity denial.

Locks are process-safe ``flock`` handles on dedicated
``research_view_rl/locks/*.lock`` files, acquired non-blocking with a bounded
poll deadline (env ``RESEARCH_VIEW_RL_LOCK_TIMEOUT``, default 5.0s, clamped to
[0.05, 30]) — never unbounded blocking.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import stat
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # POSIX process-safe advisory locks; absent → allow stays fail-open,
    import fcntl  # Brain commit fails closed (exclusion uncertain).
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover
    fcntl = None
    _HAVE_FCNTL = False

log = logging.getLogger("research_vault.view_ratelimit")

_STATE_DIR = Path(os.environ.get("MACRO_API_STATE_DIR", "/var/lib/macro-api"))
_SUBDIR = "research_view_rl"

_DEFAULT_HOURLY = 60

# --- Brain pair metering bounds / knobs -------------------------------------
_MAX_UID_LEN = 256           # raw uid bound; _safe_uid still truncates filenames
_MAX_REPORT_ID_LEN = 512
_MAX_PAIR = 2                # a Brain pair view carries at most 2 report ids
_BRAIN_IP_PREFIX = "brain:"

_LOCK_POLL = 0.005
_LOCK_TIMEOUT_DEFAULT = 5.0
_LOCK_TIMEOUT_MIN = 0.05
_LOCK_TIMEOUT_MAX = 30.0


class RateLimitArgError(ValueError):
    """Malformed call arguments (protocol/programmer error, not a cap denial)."""


class LedgerStateError(RuntimeError):
    """Canonical ledger state is malformed/unreadable — the Brain path fails
    closed on this rather than guessing a count."""


def _hourly_limit() -> int:
    """Resolve the hourly cap fresh each call (env override, sane fallback)."""
    raw = os.environ.get("RESEARCH_VIEW_HOURLY", "")
    try:
        v = int(raw)
        return v if v > 0 else _DEFAULT_HOURLY
    except (TypeError, ValueError):
        return _DEFAULT_HOURLY


def _rl_dir() -> Path:
    base = Path(os.environ.get("MACRO_API_STATE_DIR", str(_STATE_DIR)))
    return base / _SUBDIR


def _safe_uid(user_id: str) -> str:
    """Filesystem-safe fragment (brain_gateway._safe_uid idiom)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", user_id or "")[:64]


def _hash_ip(ip: str) -> str:
    """sha256 the IP → 16 hex chars. NEVER put a raw IP in a filename.

    Empty/unknown IP → 'noip' so a missing IP still meters (a scraper can't dodge
    the cap by hiding its address — the user ledger still applies)."""
    if not ip or ip == "unknown":
        return "noip"
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def _period_key(now: datetime | None = None) -> str:
    """UTC hour key (``YYYY-MM-DDTHH``). Naive input treated as UTC."""
    n = now or datetime.now(timezone.utc)
    if n.tzinfo is None:
        n = n.replace(tzinfo=timezone.utc)
    return n.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def _user_file(user_id: str, period: str) -> Path:
    return _rl_dir() / f"vh_{_safe_uid(user_id)}_{period}.json"


def _ip_file(ip_hash: str, period: str) -> Path:
    return _rl_dir() / f"vip_{_safe_uid(ip_hash)}_{period}.json"


def _read(path: Path) -> dict:
    try:
        if path.exists():
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
    except Exception:  # noqa: BLE001
        pass
    return {"count": 0}


def _write(path: Path, data: dict) -> None:
    """Fail-open but LOUD (a broken ledger must not lock a subscriber out)."""
    try:
        _rl_dir().mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "::error::research_vault: VIEW RATE-LIMIT WRITE FAILED (%s) — not "
            "advancing, view throttle uncapped until the state dir is writable", exc)


# --- process-safe, bounded locking (shared by allow and Brain commit) --------

def _lock_dir() -> Path:
    return _rl_dir() / "locks"


def _user_lock(user_id: str, period: str) -> Path:
    return _lock_dir() / f"lku_{_safe_uid(user_id)}_{period}.lock"


def _ip_lock(ip_hash: str, period: str) -> Path:
    return _lock_dir() / f"lki_{_safe_uid(ip_hash)}_{period}.lock"


def _lock_timeout() -> float:
    """Bounded lock deadline (never unbounded blocking)."""
    raw = os.environ.get("RESEARCH_VIEW_RL_LOCK_TIMEOUT", "")
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return _LOCK_TIMEOUT_DEFAULT
    if not math.isfinite(v):
        return _LOCK_TIMEOUT_DEFAULT
    return max(_LOCK_TIMEOUT_MIN, min(_LOCK_TIMEOUT_MAX, v))


def _acquire_pair_locks(user_id: str, ip_hash: str, period: str) -> list[int] | None:
    """flock BOTH ledger locks in the canonical order: user lock, then IP lock.

    Ordinary ``allow`` and ``commit_many`` take the SAME two locks in the SAME
    order, so neither can lose the other's user/IP update and no lock-order
    deadlock is possible (every IP-lock holder already holds its user lock).
    Bounded: LOCK_NB + poll until a hard deadline. Returns the held fds, or
    None when the locks could not be taken in time (caller decides policy:
    allow returns without mutating state, Brain commit fails closed).
    """
    if not _HAVE_FCNTL:
        return None
    deadline = time.monotonic() + _lock_timeout()
    fds: list[int] = []
    try:
        _lock_dir().mkdir(parents=True, exist_ok=True)
        for path in (_user_lock(user_id, period), _ip_lock(ip_hash, period)):
            fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                os.close(fd)
                raise OSError("view lock is not regular")
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        os.close(fd)
                        raise TimeoutError(f"view-rl lock timeout: {path.name}")
                    time.sleep(_LOCK_POLL)
            fds.append(fd)
    except (OSError, TimeoutError) as exc:
        _release_locks(fds)
        log.error(
            "::error::research_vault: VIEW RL LOCKS UNAVAILABLE (%s) — caller "
            "policy applies (allow=fail-open, Brain commit=fail-closed)", exc)
        return None
    return fds


def _release_locks(fds: list[int] | None) -> None:
    for fd in reversed(fds or []):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass


# --- fail-closed primitives for the Brain pair path --------------------------

_MAX_LEDGER_BYTES = 64 * 1024


def _read_state_strict(path: Path) -> dict:
    """Only actual absence starts a period; corrupt/present state is unknown."""
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj: raise ValueError("duplicate ledger field")
            obj[key] = value
        return obj
    def constant(_): raise ValueError("nonfinite ledger number")
    try:
        if path.is_symlink(): raise ValueError("ledger symlink")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError("ledger is not a regular file")
            raw = handle.read(_MAX_LEDGER_BYTES + 1)
        if len(raw) > _MAX_LEDGER_BYTES: raise ValueError("ledger exceeds byte bound")
        obj = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        if (type(obj) is not dict or type(obj.get("count")) is not int or obj["count"] < 0):
            raise ValueError("ledger count must be a nonnegative integer")
        return obj
    except FileNotFoundError:
        return {"count": 0}
    except (OSError, ValueError, UnicodeError) as exc:
        raise LedgerStateError("canonical view ledger unavailable or malformed") from exc


def _read_count_strict(path: Path) -> int:
    return _read_state_strict(path)["count"]


def _write_atomic(path: Path, data: dict) -> None:
    """ONE atomic replacement: tmp write + ``os.replace``. Raises on failure.

    Strict twin of the legacy fail-open ``_write``: the Brain commit must KNOW
    whether the canonical charge landed, and must not leave a tmp behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        _rl_dir().mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data).encode("utf-8")
        if len(payload) > _MAX_LEDGER_BYTES:
            raise LedgerStateError("updated ledger exceeds byte bound")
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise


def _brain_ip_hash(user_id: str) -> str:
    """Synthetic Brain IP hash — REDUNDANT by construction (derived from the uid
    already metered by the canonical user ledger). Mirrored for parity with the
    web IP ledger, never allowed to gate a commit."""
    return _hash_ip(_BRAIN_IP_PREFIX + user_id)


def _validate_pair_args(user_id: str, report_ids: object) -> tuple[str, tuple[str, ...]]:
    """Validate Brain pair arguments; return (uid, order-preserving deduped ids).

    Raises :class:`RateLimitArgError` on any malformed argument."""
    if type(user_id) is not str or not user_id.strip():
        raise RateLimitArgError("user_id must be a nonempty string")
    if len(user_id) > _MAX_UID_LEN:
        raise RateLimitArgError(f"user_id longer than {_MAX_UID_LEN} chars")
    if type(report_ids) not in (tuple, list):
        raise RateLimitArgError("report_ids must be a tuple or list of report id strings")
    if not 1 <= len(report_ids) <= _MAX_PAIR:
        raise RateLimitArgError(f"at most {_MAX_PAIR} report ids per Brain view")
    seen: dict[str, None] = {}
    for rid in report_ids:
        if type(rid) is not str or not rid.strip():
            raise RateLimitArgError("each report id must be a nonempty string")
        if len(rid) > _MAX_REPORT_ID_LEN:
            raise RateLimitArgError(f"report id longer than {_MAX_REPORT_ID_LEN} chars")
        seen.setdefault(rid, None)
    return user_id, tuple(seen)


def allow(
    user_id: str,
    ip: str,
    root: Path | None = None,  # signature-parity; unused (env-rooted state)
    now: datetime | None = None,
) -> tuple[bool, dict]:
    """Check + increment the hourly view cap for (user, IP).

    Returns ``(allowed, {remaining, limit})``. Allowed only when BOTH the user
    counter and the IP counter are under the cap; on allow both increment and
    ``remaining`` is the worse of the two. Fail-open (allow) on I/O error.

    Both ledger legs are read+written under the same per-user then per-IP
    ``flock`` pair the Brain commit uses (same order), so a concurrent web
    allow and Brain commit can no longer lose each other's update. If the
    locks cannot be taken in time the legacy fail-open-but-loud rule applies
    and the view is allowed without any unlocked counter mutation.
    """
    limit = _hourly_limit()
    period = _period_key(now)
    ip_hash = _hash_ip(ip)

    uf = _user_file(user_id, period)
    ipf = _ip_file(ip_hash, period)

    locks = _acquire_pair_locks(user_id, ip_hash, period)
    if locks is None:
        # Preserve paid-view availability without racing a successful locked
        # writer. Never run an unlocked read/modify/write on canonical state.
        return True, {"remaining": 0, "limit": limit}
    try:
        try:
            udata = _read_state_strict(uf)
            idata = _read_state_strict(ipf)
        except LedgerStateError:
            log.error("::error::research_vault: VIEW LEDGER UNKNOWN; allowing legacy view without rewriting counters")
            return True, {"remaining": 0, "limit": limit}
        ucount, icount = udata["count"], idata["count"]
        if ucount >= limit or icount >= limit:
            return False, {"remaining": max(0, min(limit - ucount, limit - icount)), "limit": limit}
        udata["count"] = ucount + 1
        _write(uf, udata)
        idata["count"] = icount + 1
        _write(ipf, idata)
        return True, {"remaining": max(0, min(limit - ucount - 1, limit - icount - 1)), "limit": limit}
    finally:
        _release_locks(locks)


def peek(user_id: str, ip: str, now: datetime | None = None) -> dict:
    """Read-only remaining views this hour (no increment). For the quota route."""
    limit = _hourly_limit()
    period = _period_key(now)
    ucount = int(_read(_user_file(user_id, period)).get("count") or 0)
    icount = int(_read(_ip_file(_hash_ip(ip), period)).get("count") or 0)
    remaining = min(limit - ucount, limit - icount)
    return {"remaining": max(0, remaining), "limit": limit}


def preflight_many(user_id: str, report_ids: object, now: datetime | None = None) -> bool:
    """Advisory capacity check for a Brain pair view. NO charge, NO lock.

    Same canonical user ledger, hourly cap and accounting as ordinary allow.
    Malformed or uncertain ledger state fails closed (False) so the caller
    denies output before streaming it; ``commit_many`` rechecks under the
    locks regardless. Raises :class:`RateLimitArgError` on malformed args.
    """
    user_id, ids = _validate_pair_args(user_id, report_ids)
    limit = _hourly_limit()
    period = _period_key(now)
    try:
        ucount = _read_count_strict(_user_file(user_id, period))
    except LedgerStateError as exc:
        log.error(
            "::error::research_vault: BRAIN PAIR PREFLIGHT REFUSED — uncertain "
            "ledger state (%s); failing closed", exc)
        return False
    return ucount + len(ids) <= limit


def commit_many(user_id: str, report_ids: object, now: datetime | None = None) -> bool:
    """Charge one Brain pair view atomically against the canonical USER ledger.

    Rechecks capacity UNDER the shared per-user/per-IP locks (never trusting a
    preflight), then charges ``len(dedup(report_ids))`` with ONE atomic
    canonical user-file replacement — never two sequential allows and never a
    separate counter or budget. The synthetic ``brain:<uid>`` IP mirror is
    updated best-effort afterwards and can never gate the proven commit.

    Fail-CLOSED (False, no output) on malformed/uncertain ledger state,
    unavailable locks, or an unconfirmed canonical user write. A failed
    acknowledgement is reconciled by exact readback, never a second write. Raises
    :class:`RateLimitArgError` on malformed call arguments.
    """
    user_id, ids = _validate_pair_args(user_id, report_ids)
    n = len(ids)
    limit = _hourly_limit()
    period = _period_key(now)
    ip_hash = _brain_ip_hash(user_id)
    uf = _user_file(user_id, period)
    ipf = _ip_file(ip_hash, period)

    locks = _acquire_pair_locks(user_id, ip_hash, period)
    if locks is None:
        # Exclusion uncertain → state uncertain → deny BEFORE output, no charge.
        log.error(
            "::error::research_vault: BRAIN PAIR COMMIT REFUSED — view ledger "
            "locks unavailable; failing closed, nothing charged")
        return False
    try:
        try:
            udata = _read_state_strict(uf)
            ucount = udata["count"]
        except LedgerStateError as exc:
            log.error(
                "::error::research_vault: BRAIN PAIR COMMIT REFUSED — malformed "
                "canonical user ledger (%s); failing closed, nothing charged", exc)
            return False

        if ucount + n > limit:
            return False  # plain cap denial, all-or-nothing, no partial charge

        udata["count"] = ucount + n
        try:
            _write_atomic(uf, udata)
        except Exception as exc:  # noqa: BLE001
            # A local replace can land before its acknowledgement is lost.
            # Reconcile only by reading this exact canonical state under the
            # original locks. Never replay the modifying write.
            try:
                confirmed = _read_state_strict(uf) == udata
            except LedgerStateError:
                confirmed = False
            if not confirmed:
                log.error("::error::research_vault: BRAIN PAIR COMMIT UNCONFIRMED (%s); refusing output, whole charge may have landed", exc)
                return False

        # Canonical user charge landed → commit is proven. The synthetic IP
        # mirror is redundant: best-effort only, never a gate.
        try:
            idata = _read_state_strict(ipf)
            idata["count"] += n
            _write_atomic(ipf, idata)
        except Exception as exc:  # noqa: BLE001
            log.error(
                "::error::research_vault: BRAIN VIEW IP MIRROR WRITE FAILED "
                "(%s) — canonical user charge stands", exc)
        return True
    finally:
        _release_locks(locks)
