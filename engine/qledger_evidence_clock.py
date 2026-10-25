"""engine/qledger_evidence_clock.py — write-once record of each qledger claim
FAMILY's first PROSPECTIVE registration (Eval OS P3).

WHY THIS EXISTS. The CEO's P3 directive requires "the exact first
prospective-registration timestamp for each family" — the instant the evidence
clock starts for that family's forward record. That instant matters because
every honesty claim downstream ("N graded dates", "this family has been live
M days") is measured FROM it; a start timestamp that could be quietly moved
forward would let a family's track record look older (more matured, more
credible) than it actually is. So the record is WRITE-ONCE: once a family has
a start timestamp, nothing may ever change it — not a re-run, not a later
family activation, not a backfill.

ONE FILE PER FAMILY, DELIBERATELY (not one shared JSON keyed by family). The
three P3 families (stock_desk, thematic_desk, demand_chain) each register from
a DIFFERENT nightly script (scripts/build_stock_briefs.py,
scripts/build_allocation.py, scripts/build_demand.py) that may run in
different Actions jobs. A single shared `evidence_clock_start.json` would make
two families' FIRST-EVER writes a real read-modify-write race on one whole-file
JSON document — and unlike this repo's append-only JSONL ledgers (which get
`merge=union` in .gitattributes, see data/qledger/claims.jsonl), a JSON object
cannot be union-merged: two concurrent single-key insertions land as a
same-region text conflict, and the push-retry loop's `-X theirs` resolution
(scripts/ci/push_retry.sh) would silently keep one side's key and drop the
other's — exactly the failure class B4 warns about for claims.jsonl, just one
document over. Splitting per family removes the conflict at the object level:
two families can never collide on the SAME path, and even a same-family double
write (which should never happen — this fires at most once per family, ever)
degrades to picking one of two honestly-near-simultaneous timestamps rather
than losing one family's record to another's.

NOTHING PRE-CREATES THESE FILES. They are written into existence by the first
real prospective registration on the nightly path — never stubbed or seeded by
this PR (data/qledger/ must stay untouched by a build task; see
CLAUDE.md "the ledgers are append-only nightly stores").
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("qledger_evidence_clock")

# data/qledger/evidence_clock_start/<family>.json — one small whole-file JSON
# document per claim family. See the module note for why per-family, not
# one shared file.
_CLOCK_DIR = ("data", "qledger", "evidence_clock_start")


def _clock_path(family: str, root: Path | str | None) -> Path:
    from lib import config  # local import — mirrors engine/qledger.py's own _root()
    base = Path(root) if root else config.ROOT
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(family))
    return base.joinpath(*_CLOCK_DIR, f"{safe}.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any] | None:
    """Best-effort recorded start, or unavailable; never permission to restamp.

    The installing path uses the bounded non-overwriting reader below. A failed
    public read cannot establish absence or authorize a replacement chronology.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("qledger_evidence_clock: %s is unreadable (%s) — existing chronology "
                   "unavailable; original bytes preserved", path, exc)
        return None
    if (not isinstance(raw, dict) or not isinstance(raw.get("first_prospective_registration_utc"), str)
            or not raw["first_prospective_registration_utc"]):
        log.warning("qledger_evidence_clock: %s has no qualified original start; bytes preserved", path)
        return None
    return raw


def read_start(family: str, root: Path | str | None = None) -> dict[str, Any] | None:
    """The recorded first-prospective-registration record for `family`, or None
    if absent or unavailable. None never authorizes a new registration stamp."""
    return _read(_clock_path(family, root))


class _StrictClockRecord(dict):
    """Process-local stable-file observation, never original settlement authority."""
    def __init__(self, path, observation):
        super().__init__(observation[2])
        self.path, self.observation, self.pid = path, observation, os.getpid()

    def __reduce_ex__(self, protocol):
        raise TypeError("clock observations cannot transfer original authority")


def _clock_directory(path):
    import stat
    from engine.qledger_store_sources import _open_directory
    descriptor = _open_directory(path)
    info = os.fstat(descriptor)
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
        os.close(descriptor)
        raise ValueError("unsafe original clock directory")
    return descriptor


def _strict_clock_snapshot(path, field):
    """Bounded stable bytes plus file/directory barriers, not original authority."""
    import stat
    from engine.qledger_store_native import _sync_file, _sync_dir
    from engine.qledger_store_sources import _file_identity
    try:
        directory = _clock_directory(path.parent)
    except FileNotFoundError:
        return None
    fd = None
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            return None
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o022 or info.st_size > 65536):
            raise ValueError("unsafe or oversized original clock")
        payload = bytearray()
        while len(payload) <= 65536:
            block = os.read(fd, min(8192, 65537 - len(payload)))
            if not block:
                break
            payload.extend(block)
        value = json.loads(payload)
        if (len(payload) != info.st_size or len(payload) > 65536 or not isinstance(value, dict)
                or not isinstance(value.get(field), str) or not value[field]):
            raise ValueError("existing clock is unproven; preserve original")
        _sync_file(fd)
        _sync_dir(directory)
        if (_file_identity(info) != _file_identity(os.fstat(fd))
                or _file_identity(info) != _file_identity(os.stat(path.name, dir_fd=directory, follow_symlinks=False))):
            raise ValueError("original clock changed during readback")
        other = _clock_directory(path.parent)
        try:
            if (os.fstat(other).st_dev, os.fstat(other).st_ino) != (os.fstat(directory).st_dev, os.fstat(directory).st_ino):
                raise ValueError("original clock directory changed")
        finally:
            os.close(other)
        return bytes(payload), _file_identity(info), value
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def _install_strict_clock(path, record, field):
    """Existing clock format, non-overwriting install and durable exact readback."""
    from engine.qledger_store_native import _sync_file, _sync_dir
    existing = _strict_clock_snapshot(path, field)
    if existing is not None:
        return _StrictClockRecord(path, existing)
    # Preserve the existing strict API's directory creation, with a bound and
    # barriers for each new parent; no symlinked ancestor is followed.
    missing, ancestor = [], path.parent
    while True:
        try:
            parent = _clock_directory(ancestor)
            break
        except FileNotFoundError:
            if len(missing) >= 128:
                raise ValueError("clock directory depth exceeds bound")
            missing.append(ancestor.name)
            ancestor = ancestor.parent
    try:
        for name in reversed(missing):
            try:
                os.mkdir(name, 0o755, dir_fd=parent)
            except FileExistsError:
                pass
            _sync_dir(parent)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            import stat
            if os.fstat(child).st_uid != os.geteuid() or stat.S_IMODE(os.fstat(child).st_mode) & 0o022:
                os.close(child)
                raise ValueError("unsafe original clock directory")
            os.close(parent)
            parent = child
    finally:
        os.close(parent)
    payload = json.dumps(record, indent=2, sort_keys=(field == "first_prospective_registration_utc"),
                         ensure_ascii=False) + "\n"
    if len(payload.encode("utf-8")) > 65536:
        raise ValueError("original clock exceeds explicit readback bound")
    directory = _clock_directory(path.parent)
    temporary = None
    try:
        for attempt in range(16):
            name = f".{path.name}.{os.urandom(12).hex()}.tmp"
            try:
                descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=directory)
                temporary = name
                break
            except FileExistsError:
                continue
        else:
            raise ValueError("private clock staging collision bound")
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            _sync_file(handle.fileno())
        # Confirm the pathname still names the held directory before linking.
        other = _clock_directory(path.parent)
        try:
            if (os.fstat(other).st_dev, os.fstat(other).st_ino) != (os.fstat(directory).st_dev, os.fstat(directory).st_ino):
                raise ValueError("clock directory changed before installation")
        finally:
            os.close(other)
        installed_here = False
        try:
            os.link(Path(temporary).name, path.name, src_dir_fd=directory, dst_dir_fd=directory,
                    follow_symlinks=False)
            installed_here = True
        except FileExistsError:
            pass  # Preserve/read the winner; original-scoped caller decides provenance.
        os.unlink(Path(temporary).name, dir_fd=directory)
        temporary = None
        _sync_dir(directory)
        installed = _strict_clock_snapshot(path, field)
        if installed is None:
            raise ValueError("clock collision winner unavailable; effect uncertain")
        if installed_here and installed[2] != record:
            raise ValueError("evidence clock readback differs; original effect uncertain")
        return _StrictClockRecord(path, installed)
    finally:
        if temporary is not None:
            os.unlink(Path(temporary).name, dir_fd=directory)
        os.close(directory)


def record_start(family: str, *, horizon_d: int, horizon_unit: str,
                 git_sha: str | None = None, root: Path | str | None = None,
                 now: str | None = None, strict: bool = False) -> dict[str, Any] | None:
    """Record the first prospective start without overwriting any prior object.

    Both modes require bounded stable readback and the existing non-overwriting
    install. An unreadable/unqualified existing object is unavailable, never
    absent. Default callers receive None on storage uncertainty; no proposed
    timestamp is returned as though persisted. Strict native callers keep their
    raising/process-local observation contract. A visible family record alone
    never settles an uncertain original registration.
    """
    path = _clock_path(family, root)

    def unavailable(exc):
        log.error("qledger_evidence_clock: original start unavailable for %s: %s", family, exc)
        print(f"::error title={family}-evidence-clock-write-failed::qledger evidence-clock "
              f"start for {family} is unavailable; original preserved: {exc}", flush=True)

    try:
        observation = _strict_clock_snapshot(path, "first_prospective_registration_utc")
    except Exception as exc:  # noqa: BLE001 — default annotation remains nonfatal
        unavailable(exc)
        if strict:
            raise
        return None
    if observation is not None:
        value = _StrictClockRecord(path, observation)
        return value if strict else dict(value)

    # Preserve argument validation for a genuinely absent family only. Existing
    # records ignore subsequent horizon/time arguments as before.
    record: dict[str, Any] = {
        "claim_family": family,
        "first_prospective_registration_utc": now or _now_iso(),
        "declared_horizon_d": int(horizon_d),
        "horizon_unit": horizon_unit,
        "git_sha": git_sha,
    }
    try:
        value = _install_strict_clock(path, record, "first_prospective_registration_utc")
        return value if strict else dict(value)
    except Exception as exc:  # noqa: BLE001 — never fabricate a persisted annotation
        unavailable(exc)
        if strict:
            raise
        return None


def git_sha(root: Path | str | None = None) -> str | None:
    """Best-effort current commit SHA — `GITHUB_SHA` first (set on every Actions
    run, cheap and exact), then `git rev-parse HEAD` as a local fallback. None,
    never raises, when neither source is available."""
    import os
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha:
        return env_sha.strip()
    try:
        import subprocess  # noqa: PLC0415
        from lib import config  # noqa: PLC0415
        base = Path(root) if root else config.ROOT
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base),
                             capture_output=True, text=True, timeout=5, check=False)
        sha = (out.stdout or "").strip()
        return sha or None
    except Exception:  # noqa: BLE001
        return None
