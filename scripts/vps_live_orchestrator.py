"""Resource-bounded VPS lanes for ephemeral live dashboard computation.

The VPS owns short-lived ``site/live`` products; the Mac/PC nightly runners own
canonical history, revisions, forward ledgers, calibration, and the full render.
Each lane is independently scheduled and locked so a slow full-universe quote pull
cannot block the one-minute publication/fast-price lane.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import logging
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

log = logging.getLogger("vps_live")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Snapshot work shares the source owner's absolute monotonic deadline.
# Leave 20s under systemd's 420s ceiling for source entry/final status.
SNAPSHOT_WORK_SECONDS = 400.0
BARS_WORK_SECONDS = 880.0  # 20s below the incumbent bars service ceiling.
COMMAND_CLEANUP_SECONDS = 3.0


class ProcessGroupCleanupUnconfirmed(RuntimeError):
    def __init__(self, group_id: int, *, timed_out: bool = False):
        self.group_id = group_id
        self.timed_out = timed_out
        super().__init__(f"command process-group cleanup unconfirmed: {group_id}")


def _process_group_exists(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _stop_command_group(process) -> tuple[str, str]:
    """Terminate the original group even when its direct parent exited first."""
    deadline = time.monotonic() + COMMAND_CLEANUP_SECONDS
    for sig, grace in ((signal.SIGTERM, 2.0), (signal.SIGKILL, 1.0)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        except OSError as exc:
            raise ProcessGroupCleanupUnconfirmed(process.pid) from exc
        try:
            output = process.communicate(timeout=max(.001, min(grace, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            continue
        if not _process_group_exists(process.pid):
            return output
    # A terminated orphan may need a short reap interval before its group vanishes.
    while time.monotonic() < deadline and _process_group_exists(process.pid):
        time.sleep(min(.02, max(0, deadline - time.monotonic())))
    if _process_group_exists(process.pid):
        raise ProcessGroupCleanupUnconfirmed(process.pid)
    try:
        return process.communicate(timeout=max(.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as exc:
        raise ProcessGroupCleanupUnconfirmed(process.pid) from exc


def _run_command_group(args, *, cwd, env, text, capture_output, timeout, check,
                       pass_fds=()):
    """The incumbent command boundary with bounded whole-child cleanup."""
    if text is not True or capture_output is not True or check is not False:
        raise ValueError("unsupported live command options")
    process = subprocess.Popen(args, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        pass_fds=pass_fds)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            stdout, stderr = _stop_command_group(process)
        except ProcessGroupCleanupUnconfirmed as exc:
            exc.timed_out = True
            raise
        raise subprocess.TimeoutExpired(args, timeout, output=stdout, stderr=stderr) from None
    if _process_group_exists(process.pid):
        _stop_command_group(process)
        raise RuntimeError("command descendant outlived its direct parent")
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)



@dataclass
class TaskResult:
    name: str
    status: str
    elapsed_s: float
    returncode: int | None = None
    published: tuple[str, ...] = ()
    detail: str | None = None
    publication_sha256: dict[str, str] = field(default_factory=dict)
    cleanup_group_id: int | None = None
    generation_publication: dict[str, Any] | None = None
    native_input_attempt: dict[str, Any] | None = None
    timed_out: bool = False


class DurabilityUnconfirmed(OSError):
    """The replacement is visible, but its directory entry is not known to be durable.

    The rename already happened: the new name is in place. What is missing is
    the filesystem's promise that the name survives a crash. The EFFECT and
    the DURABILITY are therefore two separate facts, and the effect is never
    rolled back or retried on the strength of a failed durability hint.
    """


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    mode: int = 0o600,
    sort_keys: bool = False,
    require_durable: bool = False,
) -> None:
    """Replace one JSON object after flushing its file bytes.

    The default preserves the legacy file-fsync-and-rename contract; it
    performs no directory fsync. The generation primitive explicitly sets
    ``require_durable=True``: its directory fsync must succeed. A failure
    after rename raises :class:`DurabilityUnconfirmed`, so the caller must
    reconcile the visible selection separately from its durability.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(
                payload, fh, separators=(",", ":"), ensure_ascii=False, sort_keys=sort_keys
            )
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
            os.fchmod(fh.fileno(), mode)
        os.replace(tmp_name, path)
        if require_durable:
            try:
                _fsync_dir(path.parent)
            except OSError as exc:
                raise DurabilityUnconfirmed(
                    "the replacement is visible but its directory entry could not "
                    f"be made durable: {exc}"
                ) from exc
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return path.stat().st_size > 1
    except (OSError, ValueError, TypeError):
        return False


def atomic_publish(source: Path, target: Path, *, mode: int = 0o644) -> str:
    """Publish a complete artifact and return the hash of those exact copied bytes."""
    if source.suffix == ".json" and not _valid_json(source):
        raise ValueError(f"refusing invalid JSON artifact: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        digest = hashlib.sha256()
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
                digest.update(chunk)
            dst.flush()
            os.fsync(dst.fileno())
            os.fchmod(dst.fileno(), mode)
        os.replace(tmp_name, target)
        return digest.hexdigest()
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def quote_snapshot_error(
    path: Path,
    *,
    min_resolved: int,
    min_coverage: float,
    require_source_clock: bool = False,
) -> str | None:
    """Return a quality error for an empty/severely degraded quote snapshot."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("meta") or {}
        quotes = payload.get("quotes") or {}
        requested = int(meta.get("requested") or 0)
        resolved = int(meta.get("resolved") or 0)
        if not isinstance(quotes, dict) or resolved != len(quotes):
            return "quote snapshot resolved count does not match payload"
        if requested <= 0:
            return "quote snapshot requested no symbols"
        coverage = resolved / requested
        if resolved < min_resolved or coverage < min_coverage:
            return (
                f"quote snapshot quality too low: {resolved}/{requested} "
                f"({coverage:.1%})"
            )
        if require_source_clock:
            # Presence and parseability only. Age is not a publish condition.
            source_asof = meta.get("source_asof")
            if not isinstance(source_asof, str) or not source_asof.strip():
                return "quote snapshot has no source clock (meta.source_asof)"
            try:
                datetime.fromisoformat(source_asof.strip().replace("Z", "+00:00"))
            except ValueError:
                return "quote snapshot has no source clock (meta.source_asof)"
        return None
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return f"quote snapshot quality check failed: {exc}"


def flow_pulse_error(path: Path, *, min_coverage: float) -> str | None:
    """Reject an age-fresh pulse that carries no usable intraday bars."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("tickers") or []
        requested = int(payload.get("n_tickers") or 0)
        if payload.get("mode") != "fastpath":
            return f"flow pulse is not live: mode={payload.get('mode') or 'missing'}"
        if not isinstance(rows, list) or requested <= 0 or requested != len(rows):
            return "flow pulse ticker count does not match payload"
        # Presence and parseability only. Age is not a publish condition.
        source_asof = payload.get("source_asof")
        if not isinstance(source_asof, str) or not source_asof.strip():
            return "flow pulse has no source clock"
        try:
            datetime.fromisoformat(source_asof.strip().replace("Z", "+00:00"))
        except ValueError:
            return "flow pulse has no source clock"
        if "n_universe" in payload:
            n_universe = payload.get("n_universe")
            if (
                type(n_universe) is not int
                or n_universe <= 0
                or len(rows) != n_universe
                or n_universe != requested
            ):
                return "flow pulse ticker count does not match payload"
            denominator = n_universe
        else:
            denominator = requested
        resolved = sum(
            1 for row in rows
            if isinstance(row, dict) and int(row.get("bars_today") or 0) > 0
        )
        coverage = resolved / denominator
        if coverage < min_coverage:
            return (
                f"flow pulse quality too low: {resolved}/{denominator} "
                f"({coverage:.1%}) have current-session bars"
            )
        return None
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return f"flow pulse quality check failed: {exc}"


def intraday_flow_symbols(path: Path) -> list[str]:
    """Return the exact disclosed Intraday Flow board universe."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    leaders = payload.get("leaders") or []
    symbols = {
        str(row.get("ticker") or row.get("symbol") or "").strip().upper()
        for row in leaders
        if isinstance(row, dict)
    }
    symbols.discard("")
    if not symbols:
        raise RuntimeError(f"Intraday Flow board has no leader symbols: {path}")
    return sorted(symbols)


# ─────────────────────────────────────────────────────────────────────────────
# Coherent domain generation publication
#
# ``atomic_publish`` above makes ONE artifact visible at a time. A domain
# generation is different: several artifacts that must agree with one another
# (a free surface, a paid surface, a manifest) only mean anything together, so
# a reader that observes them one at a time can see a bundle that never
# existed. The pinned runtime data contract requires one coherent generation
# per domain, selected by exactly one pointer.
#
# This is the SAME owner — the live publisher that already owns
# atomic_write_json, atomic_publish and the per-lane flock — extended with a
# generation primitive. It is not a second publication control plane: it
# writes into the same private state root, reuses the same atomic helpers and
# the same lock owner, and adds no scheduler, queue, database, watcher, auth
# or serving route.
#
# Everything here is private by construction. Artifacts are mode 0600 inside a
# mode 0700 store under the state root; the selection names a generation
# RELATIVE to the store, so a consumer is handed no absolute path; and nothing
# in this section writes into the served tree.
# ─────────────────────────────────────────────────────────────────────────────

GENERATION_SCHEMA = "vps_live_generation.v1"
GENERATION_SELECTION_SCHEMA = "vps_live_generation_selection.v1"

#: A generation is a BOUNDED bundle. A wide bundle is a platform, not a
#: generation, and the bound keeps one publication attempt inside the VPS
#: lane's memory and time budget.
MAX_GENERATION_ARTIFACTS = 64
MAX_GENERATION_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_GENERATION_BYTES = 512 * 1024 * 1024

_GENERATION_MANIFEST_NAME = "manifest.json"
_GENERATION_SELECTION_NAME = "current.json"
_GENERATION_RESERVED_NAMES = frozenset(
    {_GENERATION_MANIFEST_NAME, _GENERATION_SELECTION_NAME}
)
_GENERATION_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$")
_GENERATION_MAX_NAME_DEPTH = 4
_GENERATION_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GenerationRejected(Exception):
    """Internal signal: this candidate generation is not publishable."""


class SourceReadRejected(GenerationRejected):
    """A typed source-read refusal; existing publisher rejection handling applies."""

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class GenerationArtifact:
    """One member of a bounded coherent generation bundle.

    ``validator`` is called with the CAPTURED copy inside the staging
    directory, never with the producer's source path. The bytes that were
    validated are therefore the bytes that get published: a producer that
    rewrites its source mid-capture cannot change what this bundle contains.
    """

    name: str
    source: Path
    validator: Callable[[Path], str | None] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", Path(self.source))


@dataclass(frozen=True)
class GenerationValidationContext:
    """Captured values for final domain admission under the publication owner.

    Admission time is sampled once after member capture. The publication string
    is the actual target manifest's original value, including on retained reuse.
    Metadata is privately detached; members are verified bytes, not paths to reopen.
    """
    domain: str
    generation_id: str
    input_identity: Mapping[str, Any]
    members: Mapping[str, bytes]
    published_at: str
    admission_time: datetime
    source_revision: str
    computed_at: str | None


@dataclass(frozen=True)
class GenerationRequest:
    """The declared identity of one candidate generation.

    ``input_identity`` is the caller's explicit statement of which source
    versions produced the bundle and ``source_revision`` is the producer's
    revision. Both are content-bound into the generation identity and are kept
    strictly apart from the publisher's own clock: a source clock says when
    the DATA applies, a publication clock says when these BYTES became
    readable, and a bundle never lets the second stand in for the first.
    """

    generation_id: str
    domain: str
    lane: str
    source_revision: str
    artifacts: tuple[GenerationArtifact, ...]
    input_identity: Mapping[str, Any]
    computed_at: str | None = None
    bundle_validator: Callable[[GenerationValidationContext], str | None] | None = None


@dataclass(frozen=True)
class GenerationPublishResult:
    """Outcome of one publication attempt.

    ``status`` is ``published`` (the selection changed), ``unchanged`` (the
    exact same generation was already selected and nothing was written),
    ``rejected`` (this candidate is not publishable; the previous selection
    stands) or ``uncertain`` (the pointer replacement failed in a way that
    leaves the published pointer unknown, so no claim is made either way).

    ``durability`` is a SEPARATE fact from ``status``, and it describes the
    EFFECT this attempt applied: ``confirmed`` means every effect it applied
    had its directory entry fsynced after the rename; ``unconfirmed`` means
    it applied an effect whose directory entry is not known to be durable;
    ``not_applicable`` means it applied no effect at all. A failed
    durability hint never turns an applied effect into a rejection, and
    never licenses a retry.
    """

    status: str
    generation_id: str
    content_id: str | None = None
    generation_dir: str | None = None
    published_at: str | None = None
    artifacts: tuple[str, ...] = ()
    detail: str | None = None
    durability: str = "not_applicable"


def _canonical_json(payload: Any) -> bytes:
    """Deterministic JSON bytes: the same value yields the same bytes."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _publication_clock(now: datetime | None) -> datetime:
    """The publisher's own clock, always UTC.

    The publisher's clock is the ONLY clock it owns. A caller's source clock,
    computation clock and revision arrive as declared fields and are never
    rewritten here, so a publication timestamp can never be mistaken for a
    source observation time.
    """
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fsync_dir(path: Path) -> None:
    """Make a directory entry durable, not just the bytes it points at.

    The generation primitive CLAIMS durability, so this contract is STRICT:
    a filesystem that cannot fsync a directory at all (EINVAL, ENOTSUP,
    EOPNOTSUPP) and a permission or descriptor failure (EPERM, EBADF) are
    explicit failures. An unsupported filesystem is a failure to be
    reported, never a durability that is silently claimed.
    """
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)




def _private_dir(path: Path) -> Path:
    """Create a mode-0700 directory chain, one level at a time.

    ``Path.mkdir(parents=True)`` creates the missing ancestors with the
    process umask, which would leave the private store's parents group- and
    world-readable. Walking down explicitly keeps every created level 0700.

    Every created level is fsynced into its parent, so the directory chain is
    durable before anything is written inside it.
    """
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
        _fsync_dir(directory.parent)
    return path


def _read_json_state(path: Path, *, dir_fd: int | None = None) -> tuple[str, dict[str, Any] | None]:
    """Read a JSON object, telling genuine absence apart from corruption.

    ``"absent"`` means the file is not there, ``"unreadable"`` means it is
    there but could not be read, ``"corrupt"`` means it could not be parsed
    as a JSON object, ``"symlink"`` means the path is a symbolic link, and
    ``"ok"`` means the object was read. The distinction matters: a corrupt
    or symlinked pointer must never be mistaken for an absent one and then
    silently overwritten.

    The read is taken through ONE descriptor opened with ``O_NOFOLLOW``, so
    a symlink is REFUSED rather than followed, and a DANGLING symlink stays
    a symlink instead of collapsing into ``"absent"``. The open is
    non-blocking where the platform supports it, so a FIFO is classified by
    its identity instead of parking the lane until a writer appears.
    """
    try:
        linked = (path.is_symlink() if dir_fd is None else
                  S_ISLNK(os.stat(path, dir_fd=dir_fd, follow_symlinks=False).st_mode))
        if linked:
            return "symlink", None
    except FileNotFoundError:
        return "absent", None
    except OSError:
        return "unreadable", None
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(path, flags) if dir_fd is None else os.open(path, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        return "absent", None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return "symlink", None
        return "unreadable", None
    try:
        info = os.fstat(fd)
        if not S_ISREG(info.st_mode):
            return "unreadable", None
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_GENERATION_ARTIFACT_BYTES:
                return "unreadable", None
            chunks.append(chunk)
        raw = b"".join(chunks)
    except OSError:
        return "unreadable", None
    finally:
        os.close(fd)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "corrupt", None
    if not isinstance(payload, dict):
        return "corrupt", None
    return "ok", payload


def _sha256_error(label: str, value: Any) -> str | None:
    """Return why a value is not a lowercase sha256 hex digest."""
    if not isinstance(value, str) or not _GENERATION_SHA256_RE.match(value):
        return f"{label} is not a sha256 digest"
    return None


def _symlink_error(label: str, path: Path) -> str | None:
    """Return why a path is a symlink that this primitive refuses to follow."""
    try:
        if path.is_symlink():
            return f"{label} is a symlink: {path}"
    except OSError:
        return f"{label} cannot be inspected: {path}"
    return None


def _generation_segment_error(label: str, value: str) -> str | None:
    """Return why a generation_id/domain/lane is unusable as a path segment."""
    if not isinstance(value, str) or not value:
        return f"{label} is empty"
    if value in (".", ".."):
        return f"{label} is a path component alias"
    if not _GENERATION_SAFE_SEGMENT.match(value):
        return f"{label} has unsafe characters: {value!r}"
    return None


def _generation_id_error(value: Any) -> str | None:
    """Return why a generation id is unusable as a directory inside the store.

    A generation id names a directory inside the domain directory, so it may
    not collide with the layout's own files: ``current.json`` is the
    selection pointer and ``manifest.json`` belongs to a generation.
    """
    error = _generation_segment_error("generation_id", value)
    if error:
        return error
    if value in _GENERATION_RESERVED_NAMES:
        return f"generation_id collides with a reserved generation file: {value!r}"
    return None


def _artifact_name_error(name: str) -> str | None:
    """Return why an artifact name is unusable inside a generation directory."""
    if not isinstance(name, str) or not name:
        return "artifact name is empty"
    if name != name.strip():
        return "artifact name has surrounding whitespace"
    if "\x00" in name:
        return "artifact name contains a NUL byte"
    if "\\" in name:
        return "artifact name contains a backslash"
    if name.startswith("/"):
        return "artifact name is absolute"
    parts = name.split("/")
    if len(parts) > _GENERATION_MAX_NAME_DEPTH:
        return "artifact name is nested too deeply"
    for part in parts:
        if part in ("", ".", ".."):
            return "artifact name is not a clean relative path"
    if parts[0] in _GENERATION_RESERVED_NAMES:
        return "artifact name collides with a reserved generation file"
    return None


def _artifact_collision_error(names: Sequence[str]) -> str | None:
    """Return why a set of artifact names cannot coexist in one directory."""
    seen: set[str] = set()
    for name in names:
        if name in seen:
            return f"duplicate artifact name: {name}"
        seen.add(name)
    prefixes: set[str] = set()
    for name in names:
        parts = name.split("/")
        for index in range(1, len(parts)):
            prefixes.add("/".join(parts[:index]))
    for name in names:
        if name in prefixes:
            return f"artifact name collides with a sibling directory: {name}"
    return None


def _read_bundle_member(member: Path, *, limit: int) -> tuple[bytes | None, str | None]:
    """Read ONE bundle member through a single descriptor, within a bound.

    The member is opened with ``O_NOFOLLOW`` — a symlink is refused, not
    followed — and non-blocking, so a FIFO is classified by its identity
    instead of parking the reader. Its identity is read from that same
    descriptor, so the check and the read cannot disagree about which file
    was captured, and at most ``limit + 1`` bytes are read: a member that
    grew past the length its manifest recorded is truncated by that bound
    and refused by the caller's length and hash checks, rather than being
    loaded whole.

    Returns ``(bytes, None)`` or ``(None, reason)``.
    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(member, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return None, "is a symlink"
        if exc.errno == errno.ENOENT:
            return None, "is missing"
        return None, f"cannot be opened: {exc}"
    try:
        info = os.fstat(fd)
        if not S_ISREG(info.st_mode):
            return None, "is not a regular file"
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            try:
                chunk = os.read(fd, min(65536, remaining))
            except OSError as exc:
                return None, f"cannot be read: {exc}"
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(fd)
    return data, None


def _read_source_bytes(source: Path, *, limit: int, directory_fd: int | None = None,
                       require_stable: bool = False) -> bytes:
    """Read one bounded source descriptor without following a leaf symlink.

    Existing callers retain their absolute-path behavior. A capture owner may
    supply a retained parent descriptor plus a single relative leaf, and request
    before/after descriptor stability. This binds the observed object, not a
    continued pathname selection or an atomic multi-file snapshot.
    """
    if (type(limit) is not int or limit < 0 or type(require_stable) is not bool):
        raise SourceReadRejected("invalid source read options", reason="invalid_request")
    if directory_fd is not None:
        if (type(directory_fd) is not int or directory_fd < 0
                or source.is_absolute() or len(source.parts) != 1
                or source.name in {"", ".", ".."}
                or "/" in str(source) or "\\" in str(source)):
            raise SourceReadRejected("relative source leaf required", reason="invalid_request")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        if directory_fd is not None or require_stable:
            raise SourceReadRejected("safe source open unsupported", reason="unsupported")
        if source.is_symlink():
            raise SourceReadRejected(f"artifact source is a symlink: {source}", reason="symlink")

    def os_reason(error):
        if error.errno == errno.ENOENT:
            return "not_found"
        if error.errno in {errno.EACCES, errno.EPERM}:
            return "read_denied"
        if error.errno == errno.ELOOP:
            return "symlink"
        return "io_error"

    try:
        # Do not pass a new keyword to the unchanged legacy open path.
        fd = (os.open(source, flags | nofollow) if directory_fd is None else
              os.open(source, flags | nofollow, dir_fd=directory_fd))
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            message = f"artifact source is a symlink: {source}"
        elif exc.errno == errno.ENOENT:
            message = f"artifact source does not exist: {source}"
        else:
            message = f"artifact source cannot be opened: {source}: {exc}"
        raise SourceReadRejected(message, reason=os_reason(exc)) from exc
    try:
        try:
            info = os.fstat(fd)
        except OSError as exc:
            raise SourceReadRejected(f"artifact source cannot be inspected: {source}: {exc}",
                                     reason=os_reason(exc)) from exc
        if not S_ISREG(info.st_mode):
            raise SourceReadRejected(f"artifact source is not a regular file: {source}",
                                     reason="not_regular")
        if require_stable and info.st_size > limit:
            raise SourceReadRejected(f"artifact source exceeds the {limit} byte limit: {source}",
                                     reason="encoded_bound")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            try:
                chunk = os.read(fd, min(65536, remaining))
            except OSError as exc:
                raise SourceReadRejected(f"artifact source cannot be read: {source}: {exc}",
                                         reason=os_reason(exc)) from exc
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > limit:
            raise SourceReadRejected(f"artifact source exceeds the {limit} byte limit: {source}",
                                     reason="encoded_bound")
        if require_stable:
            try:
                after = os.fstat(fd)
            except OSError as exc:
                raise SourceReadRejected(f"artifact source cannot be inspected: {source}: {exc}",
                                         reason=os_reason(exc)) from exc
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            if (any(getattr(info, key) != getattr(after, key) for key in fields)
                    or len(data) != after.st_size):
                raise SourceReadRejected(f"artifact source changed during capture: {source}",
                                         reason="unstable_read")
    finally:
        os.close(fd)
    if len(data) > limit:
        raise SourceReadRejected(f"artifact source exceeds the {limit} byte limit: {source}",
                                 reason="encoded_bound")
    return data


def _prepare_parent_dirs(base: Path, name: str) -> None:
    """Create the artifact's parent directories, refusing a symlinked one."""
    current = base
    for part in name.split("/")[:-1]:
        current = current / part
        if current.is_symlink():
            raise GenerationRejected(
                f"artifact path component is a symlink: {current}"
            )
        if current.exists():
            if not current.is_dir():
                raise GenerationRejected(
                    f"artifact path component is not a directory: {current}"
                )
            continue
        current.mkdir(mode=0o700)
        _fsync_dir(current.parent)


def _write_private_bytes(target: Path, data: bytes) -> None:
    """Write bytes into a fresh mode-0600 file, refusing to follow anything.

    ``O_EXCL`` fails if the path already exists, so a symlink planted at the
    destination cannot be written through.
    """
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600)
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
    finally:
        os.close(fd)


def _clear_staging(staging_root: Path) -> None:
    """Drop leftover staging directories from an interrupted attempt."""
    try:
        entries = list(staging_root.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_symlink() or not entry.is_dir():
                entry.unlink()
            else:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            continue


def _generation_content_id(
    *,
    domain: str,
    generation_id: str,
    lane: str,
    source_revision: str,
    input_identity: Mapping[str, Any],
    captured: Sequence[Mapping[str, Any]],
) -> str:
    """Hash the generation's declared identity and its captured bytes.

    The publisher's own clock is deliberately absent: two attempts over the
    same bytes and the same declared inputs are the SAME generation, however
    long apart they happened.

    The same function hashes a candidate at publication time and recomputes
    the hash of a RETAINED generation from its manifest, so a manifest whose
    recorded content id does not match its own contents is detected.
    """
    return _sha256_hex(
        _canonical_json(
            {
                "schema": GENERATION_SCHEMA,
                "domain": domain,
                "generation_id": generation_id,
                "lane": lane,
                "source_revision": source_revision,
                "input_identity": input_identity,
                "artifacts": sorted(captured, key=lambda row: row["name"]),
            }
        )
    )


def _generation_artifact_rows(
    captured: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return sorted((dict(row) for row in captured), key=lambda row: row["name"])


def _tree_members(root: Path) -> tuple[set[str], set[str], list[str]]:
    """List the files, the directories and the symlinks under ``root``.

    A symlink is never followed: it is reported instead, because a retained
    generation's members must all be ordinary files inside that generation.
    """
    files: set[str] = set()
    directories: set[str] = set()
    symlinks: list[str] = []
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            symlinks.append(str(current))
            continue
        for entry in entries:
            relative = os.path.relpath(entry.path, root)
            if entry.is_symlink():
                symlinks.append(relative)
            elif entry.is_dir(follow_symlinks=False):
                directories.add(relative)
                pending.append(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                files.add(relative)
            else:
                # A socket, a fifo or a device is not a member of a bundle.
                symlinks.append(relative)
    return files, directories, symlinks


def _expected_directories(names: Sequence[str]) -> set[str]:
    """The directories a set of member names implies."""
    directories: set[str] = set()
    for name in names:
        parts = name.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return directories


def _verify_staged_set(
    staging: Path, captured: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Verify the COMPLETE staged bundle after every validator has run.

    A validator is READ-ONLY by contract: it may read the captured copy, but
    it may not change it, add to it or remove from it. The manifest must hash
    the bytes that are actually published, so the staged set is re-read and
    compared once every validator has run — a validator that rewrote its own
    target, or an earlier member, is caught here rather than published.
    """
    rows = [dict(row) for row in captured]
    expected = {str(row["name"]) for row in rows}
    for row in rows:
        name = str(row["name"])
        member = staging / name
        try:
            info = member.lstat()
        except OSError:
            raise GenerationRejected(
                f"staged artifact {name!r} is missing after validation"
            ) from None
        if S_ISLNK(info.st_mode):
            raise GenerationRejected(
                f"staged artifact {name!r} is a symlink after validation"
            )
        if not S_ISREG(info.st_mode):
            raise GenerationRejected(
                f"staged artifact {name!r} is not a regular file after validation"
            )
        if info.st_size != int(row["bytes"]):
            raise GenerationRejected(
                f"staged artifact {name!r} changed after validation"
            )
        if _sha256_hex(member.read_bytes()) != str(row["sha256"]):
            raise GenerationRejected(
                f"staged artifact {name!r} changed after validation"
            )
    files, directories, symlinks = _tree_members(staging)
    if symlinks:
        raise GenerationRejected(
            f"staged bundle contains a symlink: {sorted(symlinks)[0]!r}"
        )
    unexpected = files - expected
    if unexpected:
        raise GenerationRejected(
            f"staged bundle contains an unexpected member: "
            f"{sorted(unexpected)[0]!r}"
        )
    unexpected_directories = directories - _expected_directories(sorted(expected))
    if unexpected_directories:
        raise GenerationRejected(
            f"staged bundle contains an unexpected directory: "
            f"{sorted(unexpected_directories)[0]!r}"
        )
    missing = expected - files
    if missing:
        raise GenerationRejected(
            f"staged bundle is missing {sorted(missing)[0]!r}"
        )
    return rows


def _verify_retained_generation(
    directory: Path,
    *,
    domain: str,
    expected_content_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Strictly verify one retained generation directory.

    A retained generation is REUSED — published again, rolled back to, or
    declared unchanged — only when its manifest and its bytes agree with each
    other. The manifest's schema, domain, generation id, artifact names,
    bounds and lengths are checked, every member is re-hashed, the member set
    is checked for anything unexpected, and the recorded content id is
    RECOMPUTED from the manifest's own contents.

    Returns ``(manifest, None)`` when the directory is one complete,
    self-consistent generation, or ``(None, reason)`` when it is not.
    """
    manifest, error, _ = _verify_retained_generation_capture(
        directory, domain=domain, expected_content_id=expected_content_id
    )
    return manifest, error


def _verify_retained_generation_capture(
    directory: Path,
    *,
    domain: str,
    expected_content_id: str | None = None,
    capture_names: Sequence[str] | None = None,
) -> tuple[dict[str, Any] | None, str | None, dict[str, bytes] | None]:
    """Strictly verify one retained generation directory, capturing named members.

    The member bytes are the SAME bytes that are hashed: a requested member
    is read once, and the bytes read are both hashed and returned. There is
    therefore no window in which a member is verified and then read again,
    differently, by a consumer.

    Returns ``(manifest, None, captured)`` when the directory is one
    complete, self-consistent generation, or ``(None, reason, None)`` when
    it is not. ``captured`` holds only the requested member names.
    """
    label = directory.name
    if directory.is_symlink():
        return None, f"retained generation {label!r} is a symlink", None
    if not directory.is_dir():
        return None, f"retained generation {label!r} is not a directory", None

    state, manifest = _read_json_state(directory / _GENERATION_MANIFEST_NAME)
    if state != "ok" or manifest is None:
        return None, f"retained generation {label!r} manifest is {state}", None
    if manifest.get("schema") != GENERATION_SCHEMA:
        return None, (
            f"retained generation {label!r} manifest schema is not "
            f"{GENERATION_SCHEMA!r}"
        ), None
    if manifest.get("domain") != domain:
        return None, (
            f"retained generation {label!r} manifest names another domain"
        ), None
    error = _generation_id_error(manifest.get("generation_id"))
    if error:
        return None, f"retained generation {label!r} manifest: {error}", None
    if manifest["generation_id"] != label:
        return None, (
            f"retained generation {label!r} manifest names another generation"
        ), None
    error = _sha256_error("content_id", manifest.get("content_id"))
    if error:
        return None, f"retained generation {label!r} manifest: {error}", None
    if (
        expected_content_id is not None
        and manifest["content_id"] != expected_content_id
    ):
        return None, (
            f"retained generation {label!r} holds content "
            f"{manifest['content_id']!r}, not {expected_content_id!r}"
        ), None
    lane = manifest.get("lane")
    if not isinstance(lane, str) or not lane.strip():
        return None, f"retained generation {label!r} manifest lane is empty", None
    source_revision = manifest.get("source_revision")
    if not isinstance(source_revision, str) or not source_revision.strip():
        return None, (
            f"retained generation {label!r} manifest source_revision is empty"
        ), None
    input_identity = manifest.get("input_identity")
    if not isinstance(input_identity, dict) or not input_identity:
        return None, (
            f"retained generation {label!r} manifest input_identity is empty"
        ), None

    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        return None, (
            f"retained generation {label!r} manifest declares no artifacts"
        ), None
    if len(rows) > MAX_GENERATION_ARTIFACTS:
        return None, (
            f"retained generation {label!r} declares {len(rows)} artifacts; the "
            f"bound is {MAX_GENERATION_ARTIFACTS}"
        ), None
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            return None, (
                f"retained generation {label!r} manifest artifact row is not an object"
            ), None
        name = row.get("name")
        error = _artifact_name_error(name)
        if error:
            return None, (
                f"retained generation {label!r} artifact {name!r}: {error}"
            ), None
        names.append(name)
    collision = _artifact_collision_error(names)
    if collision:
        return None, f"retained generation {label!r}: {collision}", None

    total_bytes = 0
    captured: dict[str, bytes] = {}
    for row in rows:
        name = str(row["name"])
        error = _sha256_error("sha256", row.get("sha256"))
        if error:
            return None, (
                f"retained generation {label!r} artifact {name!r}: {error}"
            ), None
        size = row.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return None, (
                f"retained generation {label!r} artifact {name!r} has no valid "
                "byte count"
            ), None
        if size > MAX_GENERATION_ARTIFACT_BYTES:
            return None, (
                f"retained generation {label!r} artifact {name!r} is larger than "
                f"the {MAX_GENERATION_ARTIFACT_BYTES} byte limit"
            ), None
        total_bytes += size
        if total_bytes > MAX_GENERATION_BYTES:
            return None, (
                f"retained generation {label!r} exceeds {MAX_GENERATION_BYTES} bytes"
            ), None
        member = directory / name
        try:
            info = member.lstat()
        except OSError:
            return None, (
                f"retained generation {label!r} artifact {name!r} is missing"
            ), None
        if S_ISLNK(info.st_mode):
            return None, (
                f"retained generation {label!r} artifact {name!r} is a symlink"
            ), None
        if not S_ISREG(info.st_mode):
            return None, (
                f"retained generation {label!r} artifact {name!r} is not a regular file"
            ), None
        if info.st_size > MAX_GENERATION_ARTIFACT_BYTES:
            return None, (
                f"retained generation {label!r} artifact {name!r} is larger than "
                f"the {MAX_GENERATION_ARTIFACT_BYTES} byte limit"
            ), None
        try:
            raw, read_error = _read_bundle_member(member, limit=size)
        except OSError as exc:
            return None, (
                f"retained generation {label!r} artifact {name!r} cannot be read: "
                f"{exc}"
            ), None
        if raw is None:
            return None, (
                f"retained generation {label!r} artifact {name!r} {read_error}"
            ), None
        if _sha256_hex(raw) != str(row["sha256"]):
            return None, (
                f"retained generation {label!r} artifact {name!r} does not match "
                "its recorded hash"
            ), None
        if len(raw) != size:
            return None, (
                f"retained generation {label!r} artifact {name!r} does not match "
                "its recorded length"
            ), None
        if capture_names is not None and name in capture_names:
            captured[name] = raw

    files, directories, symlinks = _tree_members(directory)
    if symlinks:
        return None, (
            f"retained generation {label!r} contains a symlink: "
            f"{sorted(symlinks)[0]!r}"
        ), None
    expected_files = set(names) | {_GENERATION_MANIFEST_NAME}
    unexpected = files - expected_files
    if unexpected:
        return None, (
            f"retained generation {label!r} contains an unexpected member: "
            f"{sorted(unexpected)[0]!r}"
        ), None
    unexpected_directories = directories - _expected_directories(sorted(names))
    if unexpected_directories:
        return None, (
            f"retained generation {label!r} contains an unexpected directory: "
            f"{sorted(unexpected_directories)[0]!r}"
        ), None
    missing = expected_files - files
    if missing:
        return None, (
            f"retained generation {label!r} is missing {sorted(missing)[0]!r}"
        ), None

    recomputed = _generation_content_id(
        domain=manifest["domain"],
        generation_id=manifest["generation_id"],
        lane=lane,
        source_revision=source_revision,
        input_identity=input_identity,
        captured=[
            {"name": row["name"], "sha256": row["sha256"], "bytes": row["bytes"]}
            for row in rows
        ],
    )
    if recomputed != manifest["content_id"]:
        return None, (
            f"retained generation {label!r} content id does not match its manifest "
            "contents"
        ), None
    return manifest, None, captured


def _artifact_rows_signature(rows: Any) -> list[tuple[str, str, int]] | None:
    """Normalise an artifact list for comparison, or None when it is malformed."""
    if not isinstance(rows, list) or not rows:
        return None
    signature: list[tuple[str, str, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        name = row.get("name")
        sha256 = row.get("sha256")
        size = row.get("bytes")
        if not isinstance(name, str) or not isinstance(sha256, str):
            return None
        if not isinstance(size, int) or isinstance(size, bool):
            return None
        signature.append((name, sha256, size))
    return sorted(signature)


def _selection_fields_error(
    selection: Mapping[str, Any], manifest: Mapping[str, Any]
) -> str | None:
    """Return why a selection's redundant fields disagree with its manifest.

    A selection repeats the generation id, the artifact list and the
    publication stamp of the generation it names. Those repeats are not
    decoration: a reader may act on them instead of opening the manifest, so
    they are bound to the VERIFIED manifest rather than trusted.
    """
    if selection.get("generation_id") != manifest.get("generation_id"):
        return "the selection names another generation than its manifest"
    if selection.get("published_at") != manifest.get("published_at"):
        return "the selection's publication stamp does not match its manifest"
    declared = _artifact_rows_signature(selection.get("artifacts"))
    expected = _artifact_rows_signature(manifest.get("artifacts"))
    if declared is None or expected is None or declared != expected:
        return "the selection's artifact list does not match its manifest"
    return None


def _verify_selected_generation(
    selection: Mapping[str, Any],
    *,
    root: Path,
    domain: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Verify the generation that the published selection names.

    The selection names a directory RELATIVE to the store, so the read is
    constrained to that hierarchy: the name must resolve inside the store,
    and the generation it names must verify in full.
    """
    manifest, error, _ = _verify_selected_generation_capture(
        selection, root=root, domain=domain
    )
    return manifest, error


def _verify_selected_generation_capture(
    selection: Mapping[str, Any],
    *,
    root: Path,
    domain: str,
    capture_names: Sequence[str] | None = None,
) -> tuple[dict[str, Any] | None, str | None, dict[str, bytes] | None]:
    """Verify the selected generation AND bind the pointer's redundant fields.

    The selection names a directory RELATIVE to the store, so the read is
    constrained to that hierarchy: the name must resolve inside the store,
    and the generation it names must verify in full.

    The directory leaf IS the generation id, and the selection's redundant
    fields — its artifact list and its publication stamp — are bound to the
    VERIFIED manifest. A pointer that names one generation but describes
    another is not a selection, and it is refused rather than believed.

    ``capture_names`` are the member names whose verified bytes are
    returned, so a consumer never re-reads a member it was just told is
    sound.
    """
    generation_dir = selection.get("generation_dir")
    if not isinstance(generation_dir, str) or not generation_dir:
        return None, "the selection names no generation directory", None
    relative = Path(generation_dir)
    if relative.is_absolute() or any(part in ("..", "") for part in relative.parts):
        return None, (
            "the selection names a generation directory outside the store"
        ), None
    directory = root / relative
    try:
        directory.resolve().relative_to(root)
    except (ValueError, OSError):
        return None, (
            "the selection names a generation directory outside the store"
        ), None
    if relative.name != selection.get("generation_id"):
        return None, (
            "the selection names a generation directory that is not its own "
            "generation"
        ), None
    manifest, error, captured = _verify_retained_generation_capture(
        directory,
        domain=domain,
        expected_content_id=str(selection.get("content_id")),
        capture_names=capture_names,
    )
    if error or manifest is None:
        return None, error or "the selected generation could not be verified", None
    error = _selection_fields_error(selection, manifest)
    if error:
        return None, error, None
    return manifest, None, captured


def _selection_error(payload: Mapping[str, Any], domain: str) -> str | None:
    """Return why a published selection is not a usable selection."""
    if payload.get("schema") != GENERATION_SELECTION_SCHEMA:
        return f"schema is not {GENERATION_SELECTION_SCHEMA!r}"
    if payload.get("domain") != domain:
        return "names another domain"
    error = _sha256_error("content_id", payload.get("content_id"))
    if error:
        return error
    error = _generation_id_error(payload.get("generation_id"))
    if error:
        return error
    generation_dir = payload.get("generation_dir")
    if not isinstance(generation_dir, str) or not generation_dir:
        return "names no generation directory"
    parts = generation_dir.split("/")
    if len(parts) != 2 or parts[0] != domain:
        return "names a generation directory outside the store"
    if _generation_segment_error("generation directory", parts[1]):
        return "names a generation directory outside the store"
    if parts[1] != payload.get("generation_id"):
        # The directory leaf IS the generation: a pointer that names one
        # generation and points at another is not a selection.
        return "names a generation directory that is not its own generation"
    rows = payload.get("artifacts")
    if not isinstance(rows, list) or not rows:
        return "declares no artifacts"
    for row in rows:
        if not isinstance(row, dict):
            return "has an artifact row that is not an object"
        error = _artifact_name_error(row.get("name"))
        if error:
            return f"artifact {row.get('name')!r}: {error}"
        error = _sha256_error("sha256", row.get("sha256"))
        if error:
            return error
    return None


def _selection_applied(
    path: Path,
    *,
    root: Path,
    domain: str,
    expected: Mapping[str, Any],
    prior_state: str,
    prior: Mapping[str, Any] | None,
) -> bool | None:
    """Reconcile a failed write against the intended and captured selections.

    Only an exact, fully verified target proves application. Only the exact,
    still-verifiable captured prior (including captured absence) establishes
    an unchanged selection. Every other state is uncertain, even if one
    content-id field happens to match.
    """
    try:
        state, payload = _read_json_state(path)
        if state == "absent":
            return False if prior_state == "absent" else None
        if state != "ok" or payload is None:
            return None
        if payload == expected:
            applied = True
        elif prior_state == "ok" and payload == prior:
            applied = False
        else:
            return None
        if _selection_error(payload, domain):
            return None
        verified, error = _verify_selected_generation(
            payload, root=root, domain=domain
        )
        return applied if verified is not None and error is None else None
    except (OSError, ValueError, TypeError, RecursionError):
        return None


def publish_generation(
    request: GenerationRequest,
    *,
    generations_root: Path,
    state_dir: Path,
    expected_current_content_id: str | None,
    public_root: Path | None = None,
    now: datetime | None = None,
) -> GenerationPublishResult:
    """Publish ONE coherent domain generation into the private store.

    The attempt is fenced twice. The existing per-domain flock serialises
    publishers, and ``expected_current_content_id`` must equal the selection
    that is actually published when the attempt begins — so a caller that
    computed its artifacts against a selection that has since moved is refused
    instead of silently overwriting a newer generation.

    The selection pointer is replaced exactly once, after every artifact has
    been captured and validated, so a failure at any earlier point leaves the
    previous selection in place.
    """
    generation_id = request.generation_id
    artifacts = tuple(request.artifacts)

    def rejected(detail: str) -> GenerationPublishResult:
        return GenerationPublishResult(
            status="rejected", generation_id=generation_id, detail=detail
        )

    for label, value in (
        ("generation_id", generation_id),
        ("domain", request.domain),
        ("lane", request.lane),
    ):
        error = _generation_segment_error(label, value)
        if error:
            return rejected(error)
    error = _generation_id_error(generation_id)
    if error:
        return rejected(error)
    if not isinstance(request.source_revision, str) or not request.source_revision.strip():
        return rejected("source_revision is empty")
    if request.bundle_validator is not None and not callable(request.bundle_validator):
        return rejected("bundle validator is not callable")
    if not artifacts:
        return rejected("generation has no artifacts")
    if len(artifacts) > MAX_GENERATION_ARTIFACTS:
        return rejected(
            f"generation has {len(artifacts)} artifacts; the bound is "
            f"{MAX_GENERATION_ARTIFACTS}"
        )
    # A validator is REQUIRED and there is no opt-out: a bundle that was
    # never checked against its domain's own rules establishes no upstream
    # freshness. The PRESENCE of a validator is not a qualification — the
    # primitive can only see that a validator ran and accepted the captured
    # bytes. Whether that validator is the domain's real semantic gate is
    # the caller's wiring, and nothing here implies otherwise.
    for artifact in artifacts:
        if artifact.validator is None:
            return rejected(
                f"artifact {artifact.name!r} has no validator: a bundle does not "
                "establish upstream freshness"
            )
    collision = _artifact_collision_error([artifact.name for artifact in artifacts])
    if collision:
        return rejected(collision)
    for artifact in artifacts:
        error = _artifact_name_error(artifact.name)
        if error:
            return rejected(f"artifact {artifact.name!r}: {error}")

    try:
        input_identity = json.loads(
            _canonical_json(dict(request.input_identity)).decode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        return rejected(f"input_identity is not JSON-serialisable: {exc}")
    if not isinstance(input_identity, dict) or not input_identity:
        return rejected("input_identity must be a non-empty mapping")

    store = Path(generations_root)
    error = _symlink_error("generations_root", store)
    if error:
        return rejected(error)
    root = store.resolve()
    if public_root is not None:
        public = Path(public_root).resolve()
        if root == public or public in root.parents:
            return rejected(
                "generations_root must live in the private state root, not under "
                "the served tree"
            )

    lock = _lock_lane(state_dir, f"generation-{request.domain}")
    if lock is None:
        return rejected(
            f"another writer holds the {request.domain!r} generation lock"
        )
    try:
        return _publish_generation_locked(
            request,
            artifacts=artifacts,
            input_identity=input_identity,
            root=root,
            expected_current_content_id=expected_current_content_id,
            now=now,
        )
    finally:
        lock.close()


def _publish_generation_locked(
    request: GenerationRequest,
    *,
    artifacts: tuple[GenerationArtifact, ...],
    input_identity: Mapping[str, Any],
    root: Path,
    expected_current_content_id: str | None,
    now: datetime | None,
) -> GenerationPublishResult:
    """The body of :func:`publish_generation`, run under the domain lock."""
    generation_id = request.generation_id
    domain = request.domain

    # The durability of the effect this attempt applies, tracked separately
    # from the outcome: "not_applicable" (nothing applied), "confirmed" (the
    # applied effect was fsynced) or "unconfirmed" (it was applied but its
    # directory entry is not known to be durable).
    durability = "not_applicable"

    def rejected(detail: str, *, effect: str | None = None) -> GenerationPublishResult:
        return GenerationPublishResult(
            status="rejected",
            generation_id=generation_id,
            detail=detail,
            durability=effect if effect is not None else durability,
        )

    domain_dir = root / domain
    error = _symlink_error(f"domain directory {domain!r}", domain_dir)
    if error:
        return rejected(error)
    try:
        _private_dir(domain_dir)
    except OSError as exc:
        return rejected(f"could not create the domain directory: {exc}")
    selection_path = domain_dir / _GENERATION_SELECTION_NAME
    state, current = _read_json_state(selection_path)
    if state == "absent":
        current_content_id = None
    elif state != "ok" or current is None:
        # A corrupt, unreadable or symlinked pointer is NOT an absent one: it
        # is refused rather than overwritten, so the damaged state is
        # preserved for an operator instead of being silently replaced.
        return rejected(
            f"the published selection is {state}; refusing to overwrite it"
        )
    else:
        error = _selection_error(current, domain)
        if error:
            return rejected(f"the published selection is not usable: {error}")
        # The CAPTURED current selection is verified in full before its
        # content id is trusted: a pointer that names another generation, or
        # that describes a bundle its manifest does not hold, is not a
        # selection. It is refused, not healed and not overwritten.
        try:
            verified_current, verify_error = _verify_selected_generation(
                current, root=root, domain=domain
            )
        except OSError as exc:
            return rejected(
                f"the published selection could not be verified: {exc}"
            )
        if verify_error or verified_current is None:
            return rejected(
                "the published selection is not reusable: "
                f"{verify_error or 'it could not be verified'}"
            )
        current_content_id = str(current.get("content_id"))
    if current_content_id != expected_current_content_id:
        return rejected(
            "expected selection does not match the published selection "
            f"(expected {expected_current_content_id!r}, found {current_content_id!r})"
        )

    staging_root = domain_dir / ".staging"
    error = _symlink_error("the staging directory", staging_root)
    if error:
        return rejected(error)
    try:
        _private_dir(staging_root)
        # An interrupted attempt leaves staging garbage behind; it never left a
        # generation directory behind, because the directory only ever appears by
        # an atomic rename of a fully written staging directory.
        _clear_staging(staging_root)
        staging = staging_root / uuid.uuid4().hex
        staging.mkdir(mode=0o700)
    except OSError as exc:
        return rejected(f"could not prepare the staging directory: {exc}")

    captured: list[dict[str, Any]] = []
    captured_member_bytes: dict[str, bytes] = {}
    total_bytes = 0
    written_dirs: set[Path] = set()
    try:
        for artifact in artifacts:
            data = _read_source_bytes(
                artifact.source, limit=MAX_GENERATION_ARTIFACT_BYTES
            )
            total_bytes += len(data)
            if total_bytes > MAX_GENERATION_BYTES:
                raise GenerationRejected(
                    f"generation exceeds {MAX_GENERATION_BYTES} bytes"
                )
            _prepare_parent_dirs(staging, artifact.name)
            target = staging / artifact.name
            _write_private_bytes(target, data)
            written_dirs.add(target.parent)
            if artifact.validator is not None:
                try:
                    error = artifact.validator(target)
                except Exception as exc:  # noqa: BLE001 - a broken validator is a rejection
                    raise GenerationRejected(
                        f"artifact {artifact.name!r} validator raised "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                if error:
                    raise GenerationRejected(
                        f"artifact {artifact.name!r} failed validation: {error}"
                    )
            if request.bundle_validator is not None:
                captured_member_bytes[artifact.name] = data
            captured.append(
                {
                    "name": artifact.name,
                    "sha256": _sha256_hex(data),
                    "bytes": len(data),
                }
            )
        # A validator is read-only by contract, so the COMPLETE staged set is
        # re-read and compared once every validator has run. A validator that
        # rewrote its own target, or an earlier member, is caught here.
        captured = _verify_staged_set(staging, captured)
        publication_time = _publication_clock(now)
    except GenerationRejected as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return rejected(str(exc))
    except (OSError, ValueError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return rejected(f"{type(exc).__name__}: {exc}")

    content_id = _generation_content_id(
        domain=domain,
        generation_id=generation_id,
        lane=request.lane,
        source_revision=request.source_revision,
        input_identity=input_identity,
        captured=captured,
    )
    published_at = publication_time.isoformat()
    manifest = {
        "schema": GENERATION_SCHEMA,
        "domain": domain,
        "generation_id": generation_id,
        "lane": request.lane,
        "content_id": content_id,
        "source_revision": request.source_revision,
        "input_identity": input_identity,
        "computed_at": request.computed_at,
        "published_at": published_at,
        "artifacts": _generation_artifact_rows(captured),
    }

    def admit_bundle(target: Mapping[str, Any], retained: Path | None = None) -> str | None:
        if request.bundle_validator is None:
            return None
        try:
            context = GenerationValidationContext(
                domain=domain, generation_id=generation_id,
                input_identity=MappingProxyType(json.loads(
                    _canonical_json(target["input_identity"]))),
                members=MappingProxyType(dict(captured_member_bytes)),
                published_at=target.get("published_at"),
                admission_time=publication_time,
                source_revision=target.get("source_revision"),
                computed_at=target.get("computed_at"),
            )
            error = request.bundle_validator(context)
            if error:
                return "bundle failed validation: " + str(error)
            # A callback cannot rewrite the staged bytes it just admitted.
            _verify_staged_set(staging, captured)
            if retained is not None:
                checked, verify_error = _verify_retained_generation(
                    retained, domain=domain, expected_content_id=content_id)
                # published_at is deliberately outside content_id. Compare the
                # complete verified manifest as well, so its original receipt
                # cannot change after domain admission.
                if verify_error or checked != target:
                    return "retained generation changed during bundle admission"
        except Exception as exc:  # noqa: BLE001 - domain admission fails closed
            return "bundle validator raised " + type(exc).__name__
        return None

    final = domain_dir / generation_id
    if final.exists() or final.is_symlink():
        if final.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(
                f"generation {generation_id!r} already exists and is a symlink"
            )
        existing_state, existing = _read_json_state(final / _GENERATION_MANIFEST_NAME)
        if existing_state != "ok" or existing is None:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(
                f"generation {generation_id!r} already exists and its manifest is "
                "unreadable"
            )
        if str(existing.get("content_id")) != content_id:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(
                f"generation {generation_id!r} is immutable and already holds "
                f"content {existing.get('content_id')!r}"
            )
        # The same content is already materialised. The generation directory is
        # never rewritten; only the selection may move — and the retained
        # bytes are VERIFIED before they are reused.
        verified, verify_error = _verify_retained_generation(
            final, domain=domain, expected_content_id=content_id
        )
        if verify_error or verified is None:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(
                f"generation {generation_id!r} is not reusable: "
                f"{verify_error or 'it could not be verified'}"
            )
        admission_error = admit_bundle(verified, retained=final)
        if admission_error:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(admission_error)
        shutil.rmtree(staging, ignore_errors=True)
        if current_content_id == content_id:
            return GenerationPublishResult(
                status="unchanged",
                generation_id=generation_id,
                content_id=content_id,
                generation_dir=str(final.relative_to(root)),
                published_at=str(verified.get("published_at") or published_at),
                artifacts=tuple(
                    str(row.get("name")) for row in (verified.get("artifacts") or [])
                ),
                detail="the selected generation already holds this content",
            )
        target_manifest = verified
        target_dir = final
    else:
        admission_error = admit_bundle(manifest)
        if admission_error:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(admission_error)
        try:
            atomic_write_json(
                staging / _GENERATION_MANIFEST_NAME,
                manifest,
                mode=0o600,
                sort_keys=True,
                require_durable=True,
            )
            # The bundle's own bytes and its directory entries are durable before
            # the rename that publishes them.
            for directory in sorted(
                written_dirs, key=lambda item: len(item.parts), reverse=True
            ):
                _fsync_dir(directory)
            _fsync_dir(staging)
            os.replace(staging, final)
        except OSError as exc:
            shutil.rmtree(staging, ignore_errors=True)
            return rejected(f"could not publish the generation directory: {exc}")
        try:
            _fsync_dir(domain_dir)
        except OSError as exc:
            # The generation directory is in place, but its directory entry is
            # not known to be durable. The POINTER has not been replaced, so
            # the previous selection still stands and no pointer effect is
            # claimed either way.
            return rejected(
                "the generation directory was published but its directory entry "
                "could not be made durable; the published selection is "
                f"unchanged: {exc}",
                effect="unconfirmed",
            )
        durability = "confirmed"
        target_manifest = manifest
        target_dir = final

    selection = {
        "schema": GENERATION_SELECTION_SCHEMA,
        "domain": domain,
        "generation_id": generation_id,
        "content_id": content_id,
        "generation_dir": str(target_dir.relative_to(root)),
        "published_at": target_manifest.get("published_at"),
        "selected_at": published_at,
        "artifacts": target_manifest.get("artifacts") or [],
    }
    try:
        atomic_write_json(
            selection_path,
            selection,
            mode=0o600,
            sort_keys=True,
            require_durable=True,
        )
    except OSError as exc:
        # The pointer is replaced by a single os.replace, but an exception
        # AFTER that replacement may still leave the NEW pointer published. The
        # pointer is read back and reconciled: the previous selection is never
        # claimed to stand without evidence, and the new one is never claimed
        # to have landed without evidence either.
        #
        # Only an exact, verified target readback proves the EFFECT is
        # applied. If the failure that followed it was the directory fsync,
        # the DURABILITY is not confirmed — two different facts, and neither
        # is a licence to retry or to roll the pointer back.
        applied = _selection_applied(
            selection_path, root=root, domain=domain, expected=selection,
            prior_state=state, prior=current,
        )
        if applied is True:
            return GenerationPublishResult(
                status="published",
                generation_id=generation_id,
                content_id=content_id,
                generation_dir=str(target_dir.relative_to(root)),
                published_at=str(target_manifest.get("published_at") or published_at),
                artifacts=tuple(
                    str(row.get("name"))
                    for row in (target_manifest.get("artifacts") or [])
                ),
                detail=(
                    "the generation selection was replaced; the failure that "
                    "followed it did not undo it, and its durability was not "
                    f"confirmed: {exc}"
                ),
                durability="unconfirmed",
            )
        if applied is False:
            return rejected(f"could not publish the generation selection: {exc}")
        return GenerationPublishResult(
            status="uncertain",
            generation_id=generation_id,
            content_id=content_id,
            generation_dir=str(target_dir.relative_to(root)),
            detail=(
                "could not publish the generation selection and the published "
                f"pointer could not be reconciled with the captured or intended selection: {exc}"
            ),
            durability="unconfirmed",
        )

    return GenerationPublishResult(
        status="published",
        generation_id=generation_id,
        content_id=content_id,
        generation_dir=str(target_dir.relative_to(root)),
        published_at=str(target_manifest.get("published_at") or published_at),
        artifacts=tuple(str(row.get("name")) for row in (target_manifest.get("artifacts") or [])),
        durability="confirmed",
    )


def select_generation(
    *,
    generations_root: Path,
    state_dir: Path,
    domain: str,
    expected_current_content_id: str | None,
    target_content_id: str,
    public_root: Path | None = None,
    now: datetime | None = None,
) -> GenerationPublishResult:
    """Re-point a domain's selection at a generation already on disk.

    Every published generation is retained, so a bounded rollback does not
    have to re-derive the old bytes. The retained generation is re-verified
    against its own manifest before it is selected, and the same
    expected-current fence applies.

    The domain and the target content id are validated BEFORE any effect: an
    unsafe domain never reaches the store, and a target that is not a sha256
    digest never becomes a lock name or a directory name.
    """

    def rejected(detail: str) -> GenerationPublishResult:
        return GenerationPublishResult(
            status="rejected",
            generation_id=target_content_id,
            detail=detail,
        )

    error = _generation_segment_error("domain", domain)
    if error:
        return rejected(error)
    error = _sha256_error("target_content_id", target_content_id)
    if error:
        return rejected(error)

    store = Path(generations_root)
    error = _symlink_error("generations_root", store)
    if error:
        return rejected(error)
    root = store.resolve()
    if public_root is not None:
        public = Path(public_root).resolve()
        if root == public or public in root.parents:
            return rejected(
                "generations_root must live in the private state root, not under "
                "the served tree"
            )

    lock = _lock_lane(state_dir, f"generation-{domain}")
    if lock is None:
        return rejected(f"another writer holds the {domain!r} generation lock")
    try:
        domain_dir = root / domain
        error = _symlink_error(f"domain directory {domain!r}", domain_dir)
        if error:
            return rejected(error)
        try:
            _private_dir(domain_dir)
        except OSError as exc:
            return rejected(f"could not create the domain directory: {exc}")
        selection_path = domain_dir / _GENERATION_SELECTION_NAME
        state, current = _read_json_state(selection_path)
        if state == "absent":
            current_content_id = None
        elif state != "ok" or current is None:
            return rejected(
                f"the published selection is {state}; refusing to overwrite it"
            )
        else:
            error = _selection_error(current, domain)
            if error:
                return rejected(f"the published selection is not usable: {error}")
            # The CAPTURED current selection is verified before its content id
            # is trusted, exactly as in the publication path: a pointer that
            # names another generation, or that describes a bundle its
            # manifest does not hold, is refused rather than believed.
            try:
                verified_current, verify_error = _verify_selected_generation(
                    current, root=root, domain=domain
                )
            except OSError as exc:
                return rejected(
                    f"the published selection could not be verified: {exc}"
                )
            if verify_error or verified_current is None:
                return rejected(
                    "the published selection is not reusable: "
                    f"{verify_error or 'it could not be verified'}"
                )
            current_content_id = str(current.get("content_id"))
        if current_content_id != expected_current_content_id:
            return rejected(
                "expected selection does not match the published selection "
                f"(expected {expected_current_content_id!r}, found "
                f"{current_content_id!r})"
            )

        if current_content_id == target_content_id:
            # The selection already names this content, so the rollback is a
            # no-op — and the CAPTURED selection was verified above, so the
            # no-op rests on a generation that is known to be sound.
            return GenerationPublishResult(
                status="unchanged",
                generation_id=str(
                    verified_current.get("generation_id") or target_content_id
                ),
                content_id=target_content_id,
                generation_dir=str(current.get("generation_dir") or ""),
                published_at=str(verified_current.get("published_at") or ""),
                artifacts=tuple(
                    str(row.get("name"))
                    for row in (verified_current.get("artifacts") or [])
                ),
                detail="the selected generation already holds this content",
            )

        selected: tuple[Path, dict[str, Any]] | None = None
        matching_error: str | None = None
        try:
            candidates = sorted(domain_dir.iterdir())
        except OSError as exc:
            return rejected(f"could not read the generation store: {exc}")
        for candidate in candidates:
            if candidate.is_symlink():
                continue
            if not candidate.is_dir() or candidate.name == ".staging":
                continue
            manifest_state, manifest = _read_json_state(
                candidate / _GENERATION_MANIFEST_NAME
            )
            if manifest_state != "ok" or manifest is None:
                continue
            if str(manifest.get("content_id")) != target_content_id:
                continue
            # An invalid alias or orphan must not shadow a genuine retained
            # target later in the directory order. Verify each matching
            # candidate in full before choosing it; leave all files intact.
            try:
                verified, verify_error = _verify_retained_generation(
                    candidate, domain=domain, expected_content_id=target_content_id
                )
            except OSError as exc:
                matching_error = str(exc)
                continue
            if verify_error or verified is None:
                matching_error = verify_error or "it could not be verified"
                continue
            selected = (candidate, verified)
            break
        if selected is None:
            if matching_error is not None:
                return rejected(
                    f"retained generation is not verifiable: {matching_error}"
                )
            return rejected(
                f"no retained generation holds content {target_content_id!r}"
            )
        candidate_dir, manifest = selected

        published_at = _publication_clock(now).isoformat()
        selection = {
            "schema": GENERATION_SELECTION_SCHEMA,
            "domain": domain,
            "generation_id": manifest.get("generation_id"),
            "content_id": target_content_id,
            "generation_dir": str(candidate_dir.relative_to(root)),
            "published_at": manifest.get("published_at"),
            "selected_at": published_at,
            "artifacts": manifest.get("artifacts") or [],
        }
        try:
            atomic_write_json(
                selection_path,
                selection,
                mode=0o600,
                sort_keys=True,
                require_durable=True,
            )
        except OSError as exc:
            # The pointer is replaced by a single os.replace, but an exception
            # AFTER that replacement may still leave the NEW pointer published.
            # Read it back and reconcile rather than claiming either outcome.
            # Only the exact verified target proves the EFFECT; durability
            # remains a separate fact after the failed write.
            applied = _selection_applied(
                selection_path, root=root, domain=domain, expected=selection,
                prior_state=state, prior=current,
            )
            if applied is True:
                return GenerationPublishResult(
                    status="published",
                    generation_id=str(manifest.get("generation_id") or ""),
                    content_id=target_content_id,
                    generation_dir=str(candidate_dir.relative_to(root)),
                    published_at=str(manifest.get("published_at") or published_at),
                    artifacts=tuple(
                        str(row.get("name"))
                        for row in (manifest.get("artifacts") or [])
                    ),
                    detail=(
                        "the generation selection was replaced; the failure that "
                        "followed it did not undo it, and its durability was not "
                        f"confirmed: {exc}"
                    ),
                    durability="unconfirmed",
                )
            if applied is False:
                return rejected(f"could not publish the generation selection: {exc}")
            return GenerationPublishResult(
                status="uncertain",
                generation_id=str(manifest.get("generation_id") or ""),
                content_id=target_content_id,
                generation_dir=str(candidate_dir.relative_to(root)),
                detail=(
                    "could not publish the generation selection and the published "
                    f"pointer could not be reconciled with the captured or intended selection: {exc}"
                ),
                durability="unconfirmed",
            )
        return GenerationPublishResult(
            status="published",
            generation_id=str(manifest.get("generation_id") or ""),
            content_id=target_content_id,
            generation_dir=str(candidate_dir.relative_to(root)),
            published_at=str(manifest.get("published_at") or published_at),
            artifacts=tuple(
                str(row.get("name")) for row in (manifest.get("artifacts") or [])
            ),
            durability="confirmed",
        )
    finally:
        lock.close()


class SelectedGenerationUnavailable(Exception):
    """The selected generation could not be read as ONE coherent snapshot.

    The read seam never repairs, rewrites, heals or falls back: a selection
    that cannot be read as a whole is reported, not substituted with some
    other tree.
    """


class SelectedGenerationAbsent(SelectedGenerationUnavailable):
    """A safe initialized store was observed without a selected generation.

    This observation alone does not authorize bootstrap. A caller still needs
    explicit bootstrap intent and publication must retain the original None
    selection fence. Storage, permission and integrity failures are unavailable.
    """

    def __init__(self, *, domain: str, reason: str):
        super().__init__(f"no generation is selected for domain {domain!r}: {reason}")
        self.domain = domain
        self.reason = reason


@dataclass(frozen=True)
class SelectedGenerationSnapshot:
    """One detached verified generation, either selected or explicitly retained.

    ``members`` holds the VERIFIED bytes of the requested member names — the
    very bytes the verifier hashed — so a consumer never re-reads a member it
    has just been told is sound. ``manifest`` is the verified manifest of
    the captured generation, not a re-read of it. A retained read is not evidence
    of current selection.
    """

    domain: str
    generation_id: str
    content_id: str
    generation_dir: str
    published_at: str | None
    manifest: Mapping[str, Any]
    members: Mapping[str, bytes]


def read_selected_generation(
    *,
    generations_root: Path,
    domain: str,
    members: Sequence[str],
) -> SelectedGenerationSnapshot:
    """Read the currently selected generation as ONE verified snapshot.

    The pointer is captured ONCE. The CAPTURED selection is then verified in
    full — its own directory, its own manifest, every member's bytes — and
    the requested members are returned as the bytes that were verified.

    The read is read-only: it creates no directory, takes no lock file,
    writes nothing, mutates no selection and falls back to no other tree.
    The root, the domain and the pointer leaf are fixed by this primitive;
    the caller chooses only WHICH verified members it wants.

    A selection that cannot be read as a whole raises
    :class:`SelectedGenerationUnavailable`. Only positive absence in a stable,
    initialized store raises its :class:`SelectedGenerationAbsent` subtype.
    """
    error = _generation_segment_error("domain", domain)
    if error:
        raise SelectedGenerationUnavailable(error)
    wanted: list[str] = []
    for name in members:
        error = _artifact_name_error(name)
        if error:
            raise SelectedGenerationUnavailable(f"member {name!r}: {error}")
        wanted.append(name)
    collision = _artifact_collision_error(wanted)
    if collision:
        raise SelectedGenerationUnavailable(collision)

    store = Path(generations_root)
    if not store.is_absolute():
        raise SelectedGenerationUnavailable("absolute generations root required")
    try:
        if any(path.is_symlink() for path in (store, *store.parents)):
            raise SelectedGenerationUnavailable("generations_root has a symlink")
        root_info = store.lstat()
        if not S_ISDIR(root_info.st_mode):
            raise SelectedGenerationUnavailable("generations_root is not a directory")
        root = store.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SelectedGenerationUnavailable("generations_root is unavailable") from exc

    def same_directory(path: Path, observed) -> bool:
        try:
            current = path.lstat()
            return (S_ISDIR(current.st_mode) and
                    (current.st_dev, current.st_ino) == (observed.st_dev, observed.st_ino))
        except OSError:
            return False

    # Pin both directories. A pathname moved away and restored between checks
    # must not make a populated captured directory appear empty (directory ABA).
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = domain_fd = None
    domain_dir = root / domain
    try:
        root_fd = os.open(store, directory_flags)
        opened_root = os.fstat(root_fd)
        if (not S_ISDIR(opened_root.st_mode) or
                (opened_root.st_dev, opened_root.st_ino) != (root_info.st_dev, root_info.st_ino)):
            raise SelectedGenerationUnavailable("generations_root changed during capture")
        try:
            domain_fd = os.open(domain, directory_flags, dir_fd=root_fd)
        except FileNotFoundError:
            if not same_directory(store, root_info):
                raise SelectedGenerationUnavailable("generations_root changed during capture")
            raise SelectedGenerationAbsent(domain=domain, reason="domain_absent") from None
        domain_info = os.fstat(domain_fd)
        if not S_ISDIR(domain_info.st_mode):
            raise SelectedGenerationUnavailable("generation domain is not a directory")
        state, captured = _read_json_state(Path(_GENERATION_SELECTION_NAME), dir_fd=domain_fd)
        if not same_directory(store, root_info) or not same_directory(domain_dir, domain_info):
            raise SelectedGenerationUnavailable("generation store changed during capture")
        if state == "absent":
            raise SelectedGenerationAbsent(domain=domain, reason="selection_absent")
    except OSError as exc:
        raise SelectedGenerationUnavailable("generation store cannot be captured") from exc
    finally:
        if domain_fd is not None:
            os.close(domain_fd)
        if root_fd is not None:
            os.close(root_fd)
    if state != "ok" or captured is None:
        raise SelectedGenerationUnavailable(f"the published selection is {state}")
    error = _selection_error(captured, domain)
    if error:
        raise SelectedGenerationUnavailable(
            f"the published selection is not usable: {error}"
        )
    try:
        manifest, verify_error, member_bytes = _verify_selected_generation_capture(
            captured, root=root, domain=domain, capture_names=wanted
        )
    except OSError as exc:
        raise SelectedGenerationUnavailable(
            f"the selected generation could not be verified: {exc}"
        ) from exc
    if verify_error or manifest is None:
        raise SelectedGenerationUnavailable(
            "the selected generation is not verifiable: "
            f"{verify_error or 'it could not be verified'}"
        )
    captured_members = member_bytes or {}
    missing = [name for name in wanted if name not in captured_members]
    if missing:
        raise SelectedGenerationUnavailable(
            f"the selected generation does not contain {missing[0]!r}"
        )
    return SelectedGenerationSnapshot(
        domain=domain,
        generation_id=str(manifest.get("generation_id") or ""),
        content_id=str(manifest.get("content_id") or ""),
        generation_dir=str(captured.get("generation_dir") or ""),
        published_at=manifest.get("published_at"),
        # The manifest is a PRIVATE DEEP COPY: nothing a consumer does to the
        # snapshot can reach the manifest the verifier proved.
        manifest=MappingProxyType(json.loads(json.dumps(manifest))),
        members=MappingProxyType(
            {name: captured_members[name] for name in wanted}
        ),
    )


def read_retained_generation(
    *, generations_root: Path, domain: str, generation_id: str,
    content_id: str, members: Sequence[str],
) -> SelectedGenerationSnapshot:
    """Verify one pinned dependency without reading or changing current.json.

    The incumbent retained verifier hashes the entire exact generation and
    returns the same captured member bytes. There is no directory discovery,
    retry, alternative-generation fallback, lock creation, or state mutation.
    """
    for error in (_generation_segment_error("domain", domain),
                  _generation_id_error(generation_id), _sha256_error("content_id", content_id)):
        if error:
            raise SelectedGenerationUnavailable(error)
    if (not _GENERATION_SAFE_SEGMENT.fullmatch(domain)
            or not _GENERATION_SAFE_SEGMENT.fullmatch(generation_id)
            or not _GENERATION_SHA256_RE.fullmatch(content_id)):
        raise SelectedGenerationUnavailable("invalid retained identity")
    wanted = list(members)
    for name in wanted:
        error = _artifact_name_error(name)
        if error:
            raise SelectedGenerationUnavailable(error)
    collision = _artifact_collision_error(wanted)
    if collision:
        raise SelectedGenerationUnavailable(collision)
    store = Path(generations_root)
    if not store.is_absolute():
        raise SelectedGenerationUnavailable("absolute generations root required")
    try:
        if any(path.is_symlink() for path in (store, *store.parents)) or not store.is_dir():
            raise SelectedGenerationUnavailable("retained root unavailable")
        root = store.resolve()
        directory = root / domain / generation_id
        if (directory.parent.is_symlink() or not directory.parent.is_dir()
                or directory.is_symlink() or not directory.is_dir()
                or root not in directory.resolve().parents):
            raise SelectedGenerationUnavailable("retained generation unavailable")
        manifest, error, captured = _verify_retained_generation_capture(directory,
            domain=domain, expected_content_id=content_id, capture_names=wanted)
    except OSError as exc:
        raise SelectedGenerationUnavailable("retained generation cannot be verified") from exc
    if error or manifest is None:
        raise SelectedGenerationUnavailable("retained generation is not verifiable: " + (error or "unavailable"))
    captured = captured or {}
    if any(name not in captured for name in wanted):
        raise SelectedGenerationUnavailable("retained generation member missing")
    return SelectedGenerationSnapshot(domain=domain, generation_id=manifest["generation_id"],
        content_id=manifest["content_id"], generation_dir=f"{domain}/{generation_id}",
        published_at=manifest.get("published_at"),
        manifest=MappingProxyType(json.loads(json.dumps(manifest))),
        members=MappingProxyType({name: captured[name] for name in wanted}))


class Orchestrator:
    def __init__(
        self,
        *,
        live_dir: Path,
        state_dir: Path,
        data_dir: Path,
        now: datetime | None = None,
        runner=None,
        source_revision: str | None = None,
        deadline_monotonic: float | None = None,
        source_lock_fd: int | None = None,
        work_budget_seconds: float = SNAPSHOT_WORK_SECONDS,
    ) -> None:
        self.live_dir = live_dir
        self.public_dir = (
            live_dir.parent
            if live_dir.name == "live" and live_dir.parent.name == "public"
            else live_dir
        )
        self.state_dir = state_dir
        self.data_dir = data_dir
        self.stage_dir = ROOT / "site" / "live"
        self.now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        # A supplied clock remains deterministic for tests/replay. Normal
        # publication samples after capture, not at orchestrator construction.
        self._publication_now = now
        self.runner = runner
        self.source_revision = source_revision
        self.source_lock_fd = source_lock_fd
        if work_budget_seconds not in (SNAPSHOT_WORK_SECONDS, BARS_WORK_SECONDS):
            raise ValueError("closed live work budget required")
        if deadline_monotonic is not None:
            if (type(deadline_monotonic) not in {int, float}
                    or not math.isfinite(deadline_monotonic) or deadline_monotonic <= 0):
                raise ValueError("finite absolute monotonic deadline required")
            deadline_monotonic = min(deadline_monotonic, time.monotonic() + work_budget_seconds)
        self._command_deadline = deadline_monotonic
        self._cleanup_group_id = None
        self._native_lock_fd = None
        self._status_write_blocked = set()
        self._prior_snapshot = None
        self._prior_snapshot_error = None
        self.python = Path(sys.executable)
        self.results: list[TaskResult] = []

    def command(
        self,
        name: str,
        args: list[str],
        *,
        outputs: tuple[tuple[Path, Path], ...] = (),
        timeout: int,
        reserve_s: float = 0.0,
        env: dict[str, str] | None = None,
        validator: Callable[[Path], str | None] | None = None,
    ) -> TaskResult:
        started = time.monotonic()
        if self._cleanup_group_id is not None:
            result = TaskResult(name, "cleanup_unconfirmed", 0.0,
                detail="original command group remains unresolved",
                cleanup_group_id=self._cleanup_group_id)
            self.results.append(result)
            return result
        if self._command_deadline is not None:
            timeout = min(timeout, self._command_deadline - started - reserve_s - COMMAND_CLEANUP_SECONDS)
            if timeout <= 0:
                result = TaskResult(name, "budget_exhausted", 0.0,
                    detail="shared source deadline/reserve exhausted")
                self.results.append(result)
                return result
        merged_env = os.environ.copy()
        merged_env.update(env or {})
        # The first output is the task's required product. Remove only that
        # staging file before launch so a builder which exits 0 without writing
        # cannot make an old checkout artifact look like a fresh success. Keep
        # optional sidecars in place because basket/flow builders use their
        # lastgood files as inputs outside active sessions.
        optional_before: dict[Path, tuple[int, int] | None] = {}
        if outputs:
            try:
                outputs[0][0].unlink(missing_ok=True)
            except OSError as exc:
                result = TaskResult(
                    name,
                    "error",
                    round(time.monotonic() - started, 3),
                    detail=f"could not clear required staging output: {exc}"[:800],
                )
                self.results.append(result)
                return result
            for source, _ in outputs[1:]:
                try:
                    stat = source.stat()
                    optional_before[source] = (stat.st_mtime_ns, stat.st_size)
                except OSError:
                    optional_before[source] = None
        try:
            runner = self.runner or (_run_command_group if self._command_deadline is not None else subprocess.run)
            descriptors = tuple(dict.fromkeys(fd for fd in
                (self.source_lock_fd, self._native_lock_fd) if fd is not None))
            inherited = {"pass_fds": descriptors} if descriptors else {}
            completed = runner(
                args,
                cwd=ROOT,
                env=merged_env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                **inherited,
            )
            published: list[str] = []
            publication_sha256: dict[str, str] = {}
            if completed.returncode == 0:
                required_missing = bool(outputs and not outputs[0][0].is_file())
                validation_error = (
                    validator(outputs[0][0])
                    if validator is not None and not required_missing
                    else None
                )
                if required_missing:
                    status = "failed"
                    detail = f"required output was not produced: {outputs[0][0]}"
                elif validation_error:
                    status = "failed"
                    detail = validation_error
                else:
                    for index, (source, target) in enumerate(outputs):
                        if not source.is_file():
                            continue
                        if index > 0 and optional_before.get(source) is not None:
                            stat = source.stat()
                            if (stat.st_mtime_ns, stat.st_size) == optional_before[source]:
                                continue
                        try:
                            label = str(target.relative_to(self.public_dir))
                            mode = 0o644
                        except ValueError:
                            label = target.name
                            mode = 0o600
                        publication_sha256[label] = atomic_publish(source, target, mode=mode)
                        published.append(label)
                    status = "ok"
                    detail = (completed.stdout or "").strip()[-500:] or None
            else:
                status = "failed"
                detail = (completed.stderr or completed.stdout or "").strip()[-800:] or None
            result = TaskResult(
                name,
                status,
                round(time.monotonic() - started, 3),
                returncode=completed.returncode,
                published=tuple(published),
                detail=detail,
                publication_sha256=publication_sha256,
            )
        except ProcessGroupCleanupUnconfirmed as exc:
            self._cleanup_group_id = exc.group_id
            result = TaskResult(name, "cleanup_unconfirmed", round(time.monotonic() - started, 3),
                detail=str(exc), cleanup_group_id=exc.group_id, timed_out=exc.timed_out)
        except subprocess.TimeoutExpired:
            result = TaskResult(
                name, "timeout", round(time.monotonic() - started, 3), detail=f">{timeout}s", timed_out=True
            )
        except Exception as exc:  # noqa: BLE001 - one task must not darken the lane
            result = TaskResult(
                name,
                "error",
                round(time.monotonic() - started, 3),
                detail=f"{type(exc).__name__}: {exc}"[:800],
            )
        self.results.append(result)
        log.info("%s: %s (%.2fs)", result.name, result.status, result.elapsed_s)
        return result

    def module(
        self,
        name: str,
        module: str,
        module_args: list[str],
        **kwargs: Any,
    ) -> TaskResult:
        return self.command(
            name, [str(self.python), "-m", module, *module_args], **kwargs
        )

    def _publish_pairs(self, names: tuple[str, ...]) -> tuple[tuple[Path, Path], ...]:
        return tuple((self.stage_dir / name, self.live_dir / name) for name in names)

    def fast(self) -> None:
        """One-minute lane: releases first, then small quote/signal leaves."""
        self.module(
            "release_publications",
            "scripts.watch_release_publications",
            [
                "--out",
                str(self.stage_dir / "release_publications.json"),
                "--state-dir",
                str(self.state_dir),
            ],
            outputs=self._publish_pairs(("release_publications.json",)),
            timeout=60,
        )
        self.module(
            "display_quotes",
            "scripts.build_live_quotes",
            ["--display", "--out", str(self.stage_dir / "quotes.json")],
            outputs=self._publish_pairs(("quotes.json",)),
            timeout=45,
            # Coverage is resolved/REQUESTED, and --display's universe is no longer
            # ~35 macro tiles: it now carries the scraped board leg too (2026-08-13,
            # ~168 symbols). A total Yahoo outage on the .SS/.SZ leg alone would put
            # a perfectly good tile-only snapshot at ~21% and a single missing tile
            # under the old 0.20 floor — refusing the publish and freezing the served
            # file for EVERY page. 0.10 keeps the gate on what it was built to catch
            # (an empty/collapsed fetch) instead of on the size of the new leg; it is
            # the same floor the full-universe lane below already uses.
            validator=lambda path: quote_snapshot_error(
                path, min_resolved=5, min_coverage=0.10
            ),
        )

        weekday = self.now.weekday() < 5
        hour, minute = self.now.hour, self.now.minute
        if weekday and 11 <= hour <= 22:
            # GD-3: live provisional Risk Envelope. EVERY fire (not the odd/even
            # split below) — it is cheap (no network, reads two small JSON files
            # plus the risk_state.json this same gate already refreshes), and the
            # chip's own freshness timestamp still benefits from a 60s refresh even
            # though the dwell/debounce below cannot move that often. debounce_ticks
            # (scripts/build_live_risk_envelope.py, a CODE constant — no config.yml
            # key exists) counts DISTINCT risk_state.json observations, not fires:
            # this module runs every minute but risk_state.json itself only
            # refreshes on odd minutes (the odd/even split below), so 3 ticks is
            # ~3 distinct confirmations spread over ~6 minutes of wall-clock at the
            # current cadence, not ~3.

            self.module(
                "risk_envelope_live",
                "scripts.build_live_risk_envelope",
                [],
                outputs=self._publish_pairs(("risk_envelope.json",)),
                timeout=30,
            )
            if minute % 2 == 0:
                self.module(
                    "live_overlay",
                    "scripts.build_live_overlay",
                    [],
                    outputs=self._publish_pairs(("overlay.json",)),
                    timeout=70,
                )
            else:
                self.module(
                    "risk_state",
                    "scripts.build_risk_state",
                    [],
                    outputs=self._publish_pairs(
                        ("risk_state.json", "market_drivers.json", "shock_state.json")
                    ),
                    timeout=90,
                )
                self.module(
                    "turn_notifications",
                    "scripts.notify_turn_events",
                    [],
                    timeout=30,
                    env={
                        "MACRO_LIVE_DIR": str(self.live_dir),
                        "MACRO_NOTIFY_STATE_DIR": str(self.state_dir),
                    },
                )

        if weekday and 1 <= hour < 9 and minute % 2 == 0:
            self.module(
                "china_risk_state",
                "scripts.build_china_risk_state",
                [],
                outputs=self._publish_pairs(("china_risk_state.json",)),
                timeout=70,
            )

        if weekday and 13 <= hour <= 21 and minute % 10 == 7:
            heatmap_stage = self.stage_dir / "sp500_heatmap.json"
            self.module(
                "sp500_heatmap",
                "scripts.build_sp500_heatmap",
                ["--out", str(heatmap_stage)],
                outputs=((heatmap_stage, self.live_dir.parent / "marketdata" / heatmap_stage.name),),
                timeout=100,
            )

    def snapshot(self) -> None:
        """Five-minute, network-heavy full snapshot followed by both basket pulses."""
        snapshot_stage = self.stage_dir / "quotes_full.json"
        snapshot_live = self.state_dir / "quotes_full.json"
        quote_result = self.module(
            "full_quotes",
            "scripts.build_live_quotes",
            ["--private-provenance", "--out", str(snapshot_stage)],
            outputs=((snapshot_stage, snapshot_live),),
            timeout=230,
            validator=lambda path: quote_snapshot_error(
                path, min_resolved=50, min_coverage=0.10
            ),
        )
        if quote_result.status != "ok" or not snapshot_live.exists():
            return
        intraday_quote_stage = self.stage_dir / "intraday_quotes.json"
        self.module(
            "intraday_quotes",
            "scripts.build_intraday_flow_quotes",
            [
                "--base", str(ROOT / "site" / "flowtracker" / "base.json"),
                "--quotes", str(snapshot_live),
                "--out", str(intraday_quote_stage),
            ],
            outputs=self._publish_pairs(("intraday_quotes.json",)),
            timeout=30,
            validator=lambda path: quote_snapshot_error(
                path, min_resolved=80, min_coverage=0.90, require_source_clock=True,
            ),
        )
        for market, filename in (
            ("us", "basket_pulse.json"),
            ("hk", "basket_pulse_hk.json"),
        ):
            args = [
                "--market",
                market,
                "--quotes",
                str(snapshot_live),
                "--out",
                str(self.stage_dir / filename),
            ]
            sidecar = filename.replace(".json", "_lastgood.json")
            self.module(
                f"basket_{market}",
                "scripts.build_basket_pulse",
                args,
                outputs=self._publish_pairs((filename, sidecar)),
                timeout=90,
            )

    def bars(self) -> None:
        """Hourly low-priority bar accrual followed by the site-only flow pulse."""
        intraday_dir = self.data_dir / "intraday"
        symbols = intraday_flow_symbols(ROOT / "site" / "flowtracker" / "base.json")
        bars = self.module(
            "intraday_bars",
            "scripts.build_polygon_intraday",
            [
                "--lookback-days", "5",
                "--symbols", ",".join(symbols),
                "--out-dir", str(intraday_dir),
            ],
            timeout=720,
        )
        if bars.status != "ok":
            return
        self.module(
            "intraday_flow",
            "scripts.build_intraday_flow",
            ["--mode", "fastpath"],
            env={"MACRO_INTRADAY_DIR": str(intraday_dir)},
            outputs=self._publish_pairs(("flow_pulse.json", "flow_pulse_lastgood.json")),
            timeout=180,
            validator=lambda path: flow_pulse_error(path, min_coverage=0.80),
        )

    def write_status(self, lane: str, started_at: datetime, *, finished=True,
                     private_only=False, require_durable=False) -> None:
        if lane in self._status_write_blocked:
            raise RuntimeError("original status write requires reconciliation")
        invocation = os.environ.get("INVOCATION_ID")
        invocation = invocation if invocation and re.fullmatch(r"[0-9a-f]{32}", invocation) else None
        lane_payload = {
            "schema": "vps_live_lane.v1",
            "lane": lane,
            "invocation_id": invocation,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat() if finished else None,
            "ok": all(result.status == "ok" for result in self.results),
            "tasks": [asdict(result) for result in self.results],
        }
        atomic_write_json(self.state_dir / f"status-{lane}.json", lane_payload, require_durable=require_durable)
        if private_only:
            return
        lanes: dict[str, Any] = {}
        for status_path in sorted(self.state_dir.glob("status-*.json")):
            try:
                row = json.loads(status_path.read_text(encoding="utf-8"))
                # Public health is intentionally terse: stderr/stdout detail stays
                # in the root-only state file/journal where a vendor URL or
                # diagnostic can never leak through /live/.
                lanes[str(row.get("lane") or status_path.stem)] = {
                    "lane": row.get("lane"),
                    "started_at": row.get("started_at"),
                    "finished_at": row.get("finished_at"),
                    "ok": row.get("ok"),
                    "tasks": [
                        {
                            key: task.get(key)
                            for key in (
                                "name",
                                "status",
                                "elapsed_s",
                                "returncode",
                                "published",
                            )
                        }
                        for task in (row.get("tasks") or [])
                    ],
                }
            except (OSError, ValueError, TypeError):
                continue
        atomic_write_json(
            self.live_dir / "orchestrator_status.json",
            {
                "schema": "vps_live_orchestrator.v1",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "lanes": lanes,
            },
            mode=0o644,
        )

    def publish_generation(
        self,
        request: GenerationRequest,
        *,
        expected_current_content_id: str | None,
        generations_root: Path | None = None,
    ) -> GenerationPublishResult:
        """Publish one coherent domain generation into the private store.

        The store defaults to ``<state-dir>/generations`` — the private state
        root, never the served tree — and the selection is fenced by the
        caller's observed current content id under the existing per-domain
        flock, so two publishers cannot silently overwrite each other.

        Every artifact MUST carry a validator, and there is no option to
        publish without one. That is a floor, not a qualification: a
        non-null validator only proves that some validator ran and accepted
        the captured bytes. Wiring the domain's own SEMANTIC validator is the
        caller's job, and this primitive neither performs nor implies it.

        This publishes into the private store only. It adds no serving route,
        no scheduler and no second publication control plane: an entitled
        consumer reads the selected generation through its own existing path.
        """
        root = generations_root or (self.state_dir / "generations")
        return publish_generation(
            request,
            generations_root=root,
            state_dir=self.state_dir,
            expected_current_content_id=expected_current_content_id,
            public_root=self.public_dir,
            now=self._publication_now,
        )

    def select_generation(
        self,
        *,
        domain: str,
        expected_current_content_id: str | None,
        target_content_id: str,
        generations_root: Path | None = None,
    ) -> GenerationPublishResult:
        """Re-point a domain's selection at a generation already on disk."""
        root = generations_root or (self.state_dir / "generations")
        return select_generation(
            generations_root=root,
            state_dir=self.state_dir,
            domain=domain,
            expected_current_content_id=expected_current_content_id,
            target_content_id=target_content_id,
            public_root=self.public_dir,
            now=self._publication_now,
        )


def _lock_lane(state_dir: Path, lane: str):
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_file = (state_dir / f"{lane}.lock").open("a+")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return None
    return lock_file


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", choices=("fast", "snapshot", "bars"), required=True)
    parser.add_argument(
        "--live-dir",
        default=os.environ.get("MACRO_LIVE_DIR", "/var/lib/macro-live/public/live"),
    )
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("MACRO_LIVE_STATE_DIR", "/var/lib/macro-live/state"),
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("MACRO_LIVE_DATA_DIR", "/var/lib/macro-live/data"),
    )
    parser.add_argument("--now", default=None, help="test override: ISO-8601 UTC timestamp")
    args = parser.parse_args()

    live_dir, state_dir, data_dir = map(
        Path, (args.live_dir, args.state_dir, args.data_dir)
    )
    lock_file = _lock_lane(state_dir, args.lane)
    if lock_file is None:
        log.info("%s lane already active; coalescing timer tick", args.lane)
        return 0
    try:
        live_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.fromisoformat(args.now) if args.now else None
        if now and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        started_at = datetime.now(timezone.utc)
        orchestrator = Orchestrator(
            live_dir=live_dir, state_dir=state_dir, data_dir=data_dir, now=now
        )
        getattr(orchestrator, args.lane)()
        orchestrator.write_status(args.lane, started_at)
        return 0 if all(result.status == "ok" for result in orchestrator.results) else 1
    finally:
        lock_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
