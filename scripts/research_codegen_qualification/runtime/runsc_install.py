#!/usr/bin/env python3
"""Research Factory rf-runsc installer / rollback helper (source-only v2 correction).

TRUST BOUNDARY (must stay true; auditors read this first):
  * This file is a reviewed source artifact.  Its existence grants no
    authority, admission, capacity or effect clearance.
  * Caller-supplied JSON (binding, receipts, commission token) is data.  It is
    NEVER authentication and NEVER root authority.  The effect commission token
    is recorded only as a SHA256 for out-of-band human comparison; this program
    cannot verify it.
  * No effect happens by default.  ``--execute`` additionally requires a
    binding file whose own SHA256 is passed independently on the command line,
    and fails closed before any subprocess or host mutation if any pin,
    binding, platform, scratch, socket or approval field is missing or a
    placeholder.
  * This helper never downloads or fetches anything.  It consumes ONE local
    regular pinned archive prepared by a future approved same-operation
    acquisition; the acquisition happens exactly once in that commission, not
    here.  The operation is bound durably to the freshly validated actual
    normal-router-selected host at action time -- there is no stale pinned
    hostname and no separate dispatch solely because a hostname changed.
  * Current host control facts are evidence inputs, never fresh permission
    proof.  A new consumer lock is not exclusivity; compare-before-commit is
    honest best effort with a real race window -- no atomic CAS is claimed.
  * JSON/hashes/ids are binding data, not authentication, admin permission,
    lock exclusivity or acceptance.

DESIGN LIMITS (hard, finite; see LIMITS):
  180 s total wall budget with an independent 60 s / 8 KiB rollback reserve,
  16 KiB combined raw control-output cap, 20 s per command, 262144 B config
  cap, archive <= 200 MiB, expanded six-file bundle exactly 284471010 B.
  All subprocess output is collected by bounded streaming (select + capped
  os.read); children are terminated only on cap breach or timeout; the whole
  archive and each member are hashed in bounded 64 KiB chunks -- the 284 MB
  expanded bundle is never buffered in RAM and the 262144 B cap applies only
  to config/binding documents, never to archive members.
"""

from __future__ import annotations

import copy
import ctypes
import errno
import hashlib
import json
import os
import platform
import select
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Fixed contract constants.  Nothing here is configurable by the caller; every
# path, pin and size below is pinned by the root-reviewed byte contract.
# --------------------------------------------------------------------------- #

RUNTIME_NAME = "rf-runsc"
VERSION_ROOT = "/usr/local/lib/mastermind/research-factory/runsc"
VERSION_TAG = "20261005.0"
RUNSC_BINARY_PATH = VERSION_ROOT + "/" + VERSION_TAG + "/runsc"
RUNSC_RUNTIME_ARGS = ["--platform=systrap", "--network=none", "--oci-seccomp"]
EXPECTED_RUNTIME_ENTRY = {"path": RUNSC_BINARY_PATH, "runtimeArgs": RUNSC_RUNTIME_ARGS}
DAEMON_JSON_PATH = "/etc/docker/daemon.json"
DOCKER_BIN = "/usr/bin/docker"
DOCKER_SOCKET_ARG = "unix:///var/run/docker.sock"
DOCKER_SOCKET_PATH = "/var/run/docker.sock"
DOCKERD_BIN = "/usr/sbin/dockerd"
SYSTEMCTL_BIN = "/usr/bin/systemctl"
SUDO_BIN = "/usr/bin/sudo"
DOCKER_SERVICE_UNIT = "docker.service"
EXPECTED_DOCKER_VERSION = "29.1.3"
BINDING_SCHEMA = "mastermind.rf_runsc_install_binding.v2"
ROOT_ID = "01a1333c-a475-7052-95a8-72a88eb8c17b"

# Root byte-pin adjudication (accepted BYTE PINS ONLY; never weakened for tests
# -- hermetic tests construct a separate Contract instance instead).
ARCHIVE_SHA256 = "bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede"
ARCHIVE_SIZE_BYTES = 166822039
ARCHIVE_MAX_BYTES = 200 * 1024 * 1024
RUNSC_MEMBER_SHA256 = "210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a"
GVISOR_BIN_DIR = "gvisor-bin"
# Exact required archive members: name -> exact size in bytes (sum = 284471010).
REQUIRED_MEMBERS = {
    "runsc": 109966750,
    "gvisor-bin/checkpointgofer": 69128994,
    "gvisor-bin/gvisor-sentry-prewarmer": 1416,
    "gvisor-bin/gvisor_sentry": 52149808,
    "gvisor-bin/runsc-fd-parking": 1320,
    "gvisor-bin/runsc-metric-server": 53222722,
}
EXPANDED_BUNDLE_BYTES = 284471010
OPTIONAL_DIR_MEMBER = GVISOR_BIN_DIR + "/"
OPTIONAL_SHIM_MEMBER = "containerd-shim-runsc-v1"  # never installed for Docker

CONFIG_EXPECTED_MODE = 0o644
FILE_EXPECTED_MODE = 0o755
BACKUP_EXPECTED_MODE = 0o600
SCRATCH_EXPECTED_MODE = 0o700
NEWDIR_EXPECTED_MODE = 0o755
ELF_MAGIC = b"\x7fELF"
CHUNK_BYTES = 65536
DISK_ADMISSION_MARGIN_BYTES = 8 * 1024 * 1024
ALLOWED_BINARIES = frozenset({DOCKER_BIN, DOCKERD_BIN, SYSTEMCTL_BIN, SUDO_BIN})

LIMITS = {
    "total_wall_seconds": 180.0,
    "rollback_reserve_wall_seconds": 60.0,
    "combined_subprocess_output_bytes": 16384,
    "rollback_reserve_output_bytes": 8192,
    "per_command_timeout_seconds": 20.0,
    "max_config_read_bytes": 262144,
    "archive_max_bytes": ARCHIVE_MAX_BYTES,
    "expanded_bundle_bytes": EXPANDED_BUNDLE_BYTES,
    "archive_acquisition_cap_seconds": 240.0,  # future phase; not this helper
}
MINIMAL_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C"}
FORBIDDEN_ENV_KEYS = ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "SSH_AUTH_SOCK")
SYSTEMD_ALLOWED_KEYS = ("ActiveState", "SubState", "LoadState", "CanReload", "ExecReload")
SENSITIVE_KEY_PATTERNS = ("auth", "token", "secret", "password", "cred",
                          "mirror", "registry", "proxy", "pass", "key")
PLACEHOLDER_TOKENS = {"", "UNSET", "TBD", "PENDING", "PLACEHOLDER",
                      "TO_BE_BOUND", "NOT_SET", "0" * 64}
HEX64_LEN = 64
TRUTHY_ACTIVE = "active"
INFO_OSTYPE = "linux"
INFO_ARCH = "x86_64"
EXPECTED_CONTAINER_COUNT = 0
SETTLEMENT_WINDOW_SECONDS = 45.0
# At most six ordinary observations across the same 45-second window. Sixteen
# polls at 3 seconds exhausted the unchanged 8192-byte main output allowance on
# a modest existing runtime inventory before reaching the intended window.
SETTLEMENT_INTERVAL_SECONDS = 9.0


class Contract:
    """Immutable release contract.  The production instance is built from the
    fixed constants above and is never modified; hermetic tests construct a
    separate TEST-only instance with fictional pins/sizes so production pins
    are never weakened or monkeypatched."""

    def __init__(self, archive_sha256: str = ARCHIVE_SHA256,
                 archive_size: int = ARCHIVE_SIZE_BYTES,
                 runsc_member_sha256: str = RUNSC_MEMBER_SHA256,
                 member_sizes: Optional[Dict[str, int]] = None,
                 expanded_total: int = EXPANDED_BUNDLE_BYTES,
                 version_tag: str = VERSION_TAG) -> None:
        self.archive_sha256 = archive_sha256
        self.archive_size = int(archive_size)
        self.runsc_member_sha256 = runsc_member_sha256
        self.member_sizes = dict(REQUIRED_MEMBERS if member_sizes is None
                                 else member_sizes)
        self.expanded_total = int(expanded_total)
        self.version_tag = version_tag

    @property
    def version_dir(self) -> str:
        return VERSION_ROOT + "/" + self.version_tag

    @property
    def runsc_path(self) -> str:
        return self.version_dir + "/runsc"

    @property
    def member_names(self) -> Tuple[str, ...]:
        return tuple(sorted(self.member_sizes))


PRODUCTION_CONTRACT = Contract()


class InstallError(Exception):
    """Category-carrying failure.  ``category`` is always safe for receipts;
    ``detail`` carries only fixed field names, hex prefixes or contract paths
    -- never config bodies, private values or raw exception text."""

    def __init__(self, category: str, detail: str = "") -> None:
        super().__init__(detail or category)
        self.category = category
        self.detail = detail


class EffectFrozen(InstallError):
    """Raised when a command is attempted after a refusal froze all effects."""

    def __init__(self) -> None:
        super().__init__("EFFECTS_FROZEN_BY_REFUSAL")


# --------------------------------------------------------------------------- #
# Budget: finite wall-clock and output envelopes with an independent rollback
# reserve that main-budget exhaustion cannot touch.
# --------------------------------------------------------------------------- #

class Budget:
    def __init__(self, total_seconds: Optional[float] = None,
                 combined_output_bytes: Optional[int] = None,
                 rollback_reserve_seconds: Optional[float] = None,
                 rollback_reserve_output_bytes: Optional[int] = None,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self._mono = monotonic
        self._start = monotonic()
        self.total_seconds = float(total_seconds if total_seconds is not None
                                   else LIMITS["total_wall_seconds"])
        self.combined_output_bytes = int(
            combined_output_bytes if combined_output_bytes is not None
            else LIMITS["combined_subprocess_output_bytes"])
        self.rollback_reserve_seconds = float(
            rollback_reserve_seconds if rollback_reserve_seconds is not None
            else LIMITS["rollback_reserve_wall_seconds"])
        self.rollback_reserve_output_bytes = int(
            rollback_reserve_output_bytes if rollback_reserve_output_bytes is not None
            else LIMITS["rollback_reserve_output_bytes"])
        self.spent_output_bytes = 0
        self.rollback_spent_output_bytes = 0
        self._rollback_start: Optional[float] = None

    def wall_left(self, rollback: bool = False) -> float:
        if rollback:
            base = (self._rollback_start if self._rollback_start is not None
                    else self._mono())
            now = self._mono()
            return min(self.rollback_reserve_seconds - (now - base),
                       self._start + self.total_seconds - now)
        deadline = self._start + self.total_seconds - self.rollback_reserve_seconds
        return deadline - self._mono()

    def out_left(self, rollback: bool = False) -> int:
        if rollback:
            return self.rollback_reserve_output_bytes - self.rollback_spent_output_bytes
        return self.combined_output_bytes - self.rollback_reserve_output_bytes - self.spent_output_bytes

    def spend_output(self, n: int, rollback: bool = False) -> bool:
        if rollback:
            self.rollback_spent_output_bytes += n
            return self.rollback_spent_output_bytes <= self.rollback_reserve_output_bytes
        self.spent_output_bytes += n
        return self.spent_output_bytes <= self.combined_output_bytes - self.rollback_reserve_output_bytes

    def expired(self, rollback: bool = False) -> bool:
        return self.wall_left(rollback) <= 0.0

    def begin_rollback(self) -> None:
        if self._rollback_start is None:
            self._rollback_start = self._mono()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "main_wall_left_seconds": round(max(self.wall_left(), 0.0), 3),
            "main_output_left_bytes": max(self.out_left(), 0),
            "rollback_wall_left_seconds": round(max(self.wall_left(True), 0.0), 3),
            "rollback_output_left_bytes": max(self.out_left(True), 0),
        }


# --------------------------------------------------------------------------- #
# Refusal classification: allowlist class + exit status + stream presence
# ONLY.  Output CONTENT is never scanned -- workload/config bytes are never
# classified as permission strings.  rc0 with a nonempty stderr on a trusted
# privileged control command is a control error, never a pass.
# --------------------------------------------------------------------------- #

def classify_outcome(binary: str, rc: Optional[int], timed_out: bool,
                     stderr_present: bool = False) -> Tuple[bool, Optional[str]]:
    if timed_out:
        return True, "COMMAND_TIMEOUT_UNKNOWN"
    if rc == 0:
        if stderr_present and binary in (SUDO_BIN, SYSTEMCTL_BIN, DOCKER_BIN):
            return True, "CONTROL_STDERR_WITH_RC0"
        return False, None
    if binary == SUDO_BIN:
        return True, "SUDO_NONZERO_AMBIGUOUS_REFUSAL"
    if binary == SYSTEMCTL_BIN:
        return True, "PRIVILEGED_NONZERO_AMBIGUOUS"
    if binary == DOCKER_BIN:
        return True, "DOCKER_QUERY_UNVERIFIED_NONZERO"
    if binary == DOCKERD_BIN:
        return False, "VALIDATION_TECHNICAL_FAILURE"
    return True, "UNCLASSIFIED_NONZERO"


def validate_argv(argv: List[str], binaries: frozenset) -> None:
    if not argv or not isinstance(argv[0], str) or argv[0] not in binaries:
        raise InstallError("COMMAND_NOT_ALLOWLISTED")
    if argv[0] == SUDO_BIN:
        if len(argv) < 3 or argv[1] != "-n" or argv[2] not in binaries:
            raise InstallError("COMMAND_NOT_ALLOWLISTED", "sudo form rejected")
        if "-l" in argv or "-i" in argv or "-S" in argv:
            raise InstallError("COMMAND_NOT_ALLOWLISTED",
                               "sudo probing/interactive form rejected")


class BoundedRunner:
    """Production runner: allowlisted binaries, minimal fixed environment,
    per-command timeout, shared bounded output collection via select() and
    capped os.read().  Output is bounded BEFORE accumulating; the child is
    terminated only on cap breach or timeout; truncation/timeout flags are
    recorded and any mutation timeout stays uncertain (never retried)."""

    def __init__(self, budget: Budget,
                 popen: Callable[..., Any] = subprocess.Popen,
                 selector: Any = select,
                 binaries: frozenset = ALLOWED_BINARIES,
                 env: Optional[Dict[str, str]] = None,
                 per_command_timeout: Optional[float] = None,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self.budget = budget
        self._popen = popen
        self._select = selector.select
        self._mono = monotonic
        self._binaries = binaries
        self.env = dict(env) if env is not None else dict(MINIMAL_ENV)
        self.per_command_timeout = float(
            per_command_timeout if per_command_timeout is not None
            else LIMITS["per_command_timeout_seconds"])
        self.calls: List[Dict[str, Any]] = []
        self._frozen = False

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        self._frozen = True

    def run(self, argv: List[str], timeout: Optional[float] = None,
            role: str = "main") -> Dict[str, Any]:
        if self._frozen:
            raise EffectFrozen()
        validate_argv(argv, self._binaries)
        for key in FORBIDDEN_ENV_KEYS:
            if key in self.env:
                raise InstallError("AMBIENT_ENV_LEAK", key)
        rollback = role == "rollback"
        wall = self.budget.wall_left(rollback)
        if wall <= 0.0 or self.budget.out_left(rollback) <= 0:
            raise InstallError("BUDGET_EXCEEDED")
        effective = min(float(timeout) if timeout else self.per_command_timeout, wall)
        deadline = self._mono() + effective
        rec: Dict[str, Any] = {"binary": argv[0], "argv_tail": list(argv[1:4]),
                               "role": role, "rc": None, "timed_out": False,
                               "truncated": False, "out_len": 0, "err_len": 0}
        proc = self._popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, env=self.env, close_fds=True)
        fd_out, fd_err = proc.stdout.fileno(), proc.stderr.fileno()
        bufs = {fd_out: bytearray(), fd_err: bytearray()}
        names = {fd_out: "out_len", fd_err: "err_len"}
        open_fds = [fd_out, fd_err]
        try:
            while open_fds:
                left = deadline - self._mono()
                if left <= 0.0:
                    rec["timed_out"] = True
                    self._kill(proc)
                    break
                ready, _, _ = self._select(open_fds, [], [], left)
                for fd in ready:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        open_fds.remove(fd)
                        continue
                    room = self.budget.out_left(rollback) - rec["out_len"] - rec["err_len"]
                    if room <= 0:
                        rec["truncated"] = True
                        self._kill(proc)
                        open_fds = []
                        break
                    keep = chunk[:room]
                    bufs[fd] += keep
                    rec[names[fd]] = len(bufs[fd])
                    if len(keep) < len(chunk):
                        rec["truncated"] = True
                        self._kill(proc)
                        open_fds = []
                        break
            if not rec["timed_out"] and proc.poll() is None:
                try:
                    proc.wait(timeout=max(deadline - self._mono(), 0.001))
                except subprocess.TimeoutExpired:
                    rec["timed_out"] = True
                    self._kill(proc)
            rec["rc"] = proc.returncode
        finally:
            for stream in (proc.stdout, proc.stderr):
                try:
                    stream.close()
                except OSError:
                    pass
        out_bytes, err_bytes = bytes(bufs[fd_out]), bytes(bufs[fd_err])
        self.budget.spend_output(len(out_bytes) + len(err_bytes), rollback)
        rec["out_sha256"] = hashlib.sha256(out_bytes).hexdigest()
        rec["err_sha256"] = hashlib.sha256(err_bytes).hexdigest()
        if rec["truncated"]:
            refused, category = False, "OUTPUT_BUDGET_TRUNCATED"
        else:
            refused, category = classify_outcome(argv[0], rec["rc"],
                                                 rec["timed_out"],
                                                 len(err_bytes) > 0)
        rec["refused"], rec["category"] = refused, category
        self.calls.append(rec)
        if refused:
            self.freeze()
            raise InstallError(category or "REFUSED", "command refused/unknown")
        return {"rc": rec["rc"], "out": out_bytes, "err": err_bytes,
                "timed_out": rec["timed_out"], "truncated": rec["truncated"]}

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


# --------------------------------------------------------------------------- #
# Linux renameat2 RENAME_NOREPLACE via ctypes with exact errno.  There is NO
# plain-rename fallback: plain rename can replace an empty destination and is
# therefore not a publication primitive.  Unsupported platforms fail closed.
# --------------------------------------------------------------------------- #

AT_FDCWD = -100
RENAME_NOREPLACE = 1


def rename_noreplace(old_path: str, new_path: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    fn = getattr(libc, "renameat2", None)
    if fn is None:
        raise OSError(errno.ENOSYS, "renameat2 unavailable on this platform")
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                   ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = fn(AT_FDCWD, os.fsencode(old_path), AT_FDCWD, os.fsencode(new_path),
            RENAME_NOREPLACE)
    if rc != 0:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e), old_path, None, new_path)


# --------------------------------------------------------------------------- #
# Strict JSON, filesystem metadata, bounded streamed hashing.
# --------------------------------------------------------------------------- #

def json_loads_strict(text: str, what: str) -> Any:
    def hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}
        for k, _v in pairs:
            if k in obj:
                raise InstallError("DUPLICATE_JSON_KEY", what)
            obj[k] = _v
        return obj
    try:
        parsed = json.loads(text, object_pairs_hook=hook)
    except InstallError:
        raise
    except json.JSONDecodeError:
        raise InstallError("CONFIG_PARSE_ERROR", what)
    if not isinstance(parsed, dict):
        raise InstallError("CONFIG_TOPLEVEL_NOT_OBJECT", what)
    return parsed


def lstat_meta(path: str) -> Optional[Dict[str, Any]]:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM):
            raise InstallError("PERMISSION_REFUSED_STAT") from None
        raise InstallError("STAT_ERROR", os.path.basename(path)) from None
    return {
        "mode": stat.S_IMODE(st.st_mode), "uid": st.st_uid, "gid": st.st_gid,
        "size": st.st_size, "inode": st.st_ino, "device": st.st_dev,
        "mtime_ns": st.st_mtime_ns, "is_regular": stat.S_ISREG(st.st_mode),
        "is_dir": stat.S_ISDIR(st.st_mode), "is_symlink": stat.S_ISLNK(st.st_mode),
    }


def read_regular_bounded(path: str, max_bytes: int) -> bytes:
    """Read a regular non-symlink file with a hard size cap (O_NOFOLLOW).
    Used ONLY for small documents (config, binding, backup), never archives."""
    meta = lstat_meta(path)
    if meta is None:
        raise InstallError("PATH_MISSING")
    if meta["is_symlink"] or not meta["is_regular"]:
        raise InstallError("PATH_NOT_REGULAR_FILE")
    if meta["size"] > max_bytes:
        raise InstallError("PATH_OVERSIZED")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except PermissionError:
        raise InstallError("PERMISSION_REFUSED_READ") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > max_bytes:
            raise InstallError("PATH_NOT_REGULAR_FILE")
        data = b""
        while len(data) < st.st_size:
            chunk = os.read(fd, min(CHUNK_BYTES, st.st_size - len(data)))
            if not chunk:
                break
            data += chunk
    finally:
        os.close(fd)
    return data


def sha256_streamed(path: str, max_bytes: int, checkpoint=None) -> Tuple[str, int]:
    """Stream a regular non-symlink file in bounded chunks, returning
    (sha256, size).  Never buffers the file in RAM; aborts past max_bytes."""
    meta = lstat_meta(path)
    if meta is None:
        raise InstallError("PATH_MISSING")
    if meta["is_symlink"] or not meta["is_regular"]:
        raise InstallError("PATH_NOT_REGULAR_FILE")
    if meta["size"] > max_bytes:
        raise InstallError("PATH_OVERSIZED")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except PermissionError:
        raise InstallError("PERMISSION_REFUSED_READ") from None
    digest = hashlib.sha256()
    total = 0
    try:
        while True:
            if checkpoint is not None:
                checkpoint()
            chunk = os.read(fd, CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise InstallError("PATH_OVERSIZED")
            digest.update(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest(), total


def fsync_dir(path: str) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def check_ancestors(path: str, expect_uid: int, base: str = "") -> Optional[List[str]]:
    """Validate every ancestor directory of the RESOLVED ``path``: real
    directory (no symlink traversal), owned by expect_uid, without group or
    other write.  Ancestors at or above ``base`` (the hermetic fixture root,
    empty in production so / down is checked) are skipped."""
    base = base.rstrip("/")
    skip = len([p for p in base.split("/") if p]) if base else 0
    parts = [p for p in path.split("/") if p]
    missing: List[str] = []
    current = ""
    for i, part in enumerate(parts[:-1]):
        current += "/" + part
        if i < skip:
            continue
        meta = lstat_meta(current)
        if meta is None:
            missing.append(current)
            continue
        if missing:
            raise InstallError("ANCESTOR_CHAIN_UNEXPECTED", "exists below missing")
        if meta["is_symlink"] or not meta["is_dir"]:
            raise InstallError("ANCESTOR_NOT_DIRECTORY")
        if meta["uid"] != expect_uid:
            raise InstallError("ANCESTOR_OWNER_UNEXPECTED")
        if meta["mode"] & 0o022:
            raise InstallError("ANCESTOR_MODE_UNSAFE")
    return missing or None


def ensure_ancestors(path: str, expect_uid: int,
                     chown_fn: Callable[[str, int, int], None],
                     base: str = "") -> None:
    """Create ONLY missing ancestor directories of the RESOLVED path, mode
    0755, owner pinned to expect_uid, fsynced.  Never touches existing
    entries and never creates anything above the fixture base."""
    base = base.rstrip("/")
    skip = len([p for p in base.split("/") if p]) if base else 0
    parts = [p for p in path.split("/") if p]
    current = ""
    for i, part in enumerate(parts[:-1]):
        current += "/" + part
        if i < skip:
            continue
        meta = lstat_meta(current)
        if meta is None:
            os.mkdir(current, NEWDIR_EXPECTED_MODE)
            chown_fn(current, expect_uid, expect_uid)
            fsync_dir(os.path.dirname(current) or "/")
        else:
            check_ancestors(current + "/.anchor", expect_uid, base=base)


def semantic_leaves(obj: Any, prefix: Tuple[str, ...] = ()):
    """Yield (path, value) leaves; dicts/lists recurse, empty containers are
    themselves leaves so structural removals stay visible."""
    if isinstance(obj, dict):
        if not obj:
            yield prefix, obj
        for k in obj:
            yield from semantic_leaves(obj[k], prefix + (str(k),))
    elif isinstance(obj, list):
        yield prefix, obj
    else:
        yield prefix, obj


def assert_exact_addition(original: Any, candidate: Any,
                          expected_entry: Dict[str, Any],
                          runtime_name: str = RUNTIME_NAME) -> List[str]:
    """Prove the candidate differs from the original by exactly one added
    semantic leaf path with exactly the expected value.  Any other change,
    removal or value drift raises."""
    added_prefix = "runtimes/" + runtime_name + "/"
    orig = dict(semantic_leaves(original))
    cand = dict(semantic_leaves(candidate))
    changed = [p for p in cand
               if p not in orig
               or json.dumps(orig[p], sort_keys=True) != json.dumps(cand[p], sort_keys=True)]
    if [p for p in orig if p not in cand]:
        raise InstallError("ADDITIVE_PROOF_FAILED", "removal detected")
    joined = ["/".join(p) for p in changed]
    if not joined or any(not p.startswith(added_prefix) for p in joined):
        raise InstallError("ADDITIVE_PROOF_FAILED", "unexpected semantic change")
    got = candidate
    for key in ("runtimes", runtime_name):
        got = got[key]
    if json.dumps(got, sort_keys=True) != json.dumps(expected_entry, sort_keys=True):
        raise InstallError("ADDITIVE_PROOF_FAILED", "added value drift")
    return ["runtimes." + runtime_name]


# --------------------------------------------------------------------------- #
# Binding: strict required pins, placeholder rejection.  The preimage and host
# are deliberately NOT binding fields: the config preimage and the actual
# normal-router-selected host are acquired fresh at action time and bound
# durably into the operation's private intent receipt in the same commission.
# --------------------------------------------------------------------------- #

def _hex64(raw: Dict[str, Any], key: str) -> str:
    v = _required(raw, key)
    if len(v) != HEX64_LEN or any(c not in "0123456789abcdef" for c in v):
        raise InstallError("BINDING_PIN_MALFORMED", key)
    if v == "0" * HEX64_LEN:
        raise InstallError("BINDING_PIN_PLACEHOLDER", key)
    return v


def _required(raw: Dict[str, Any], key: str) -> str:
    if key not in raw:
        raise InstallError("BINDING_FIELD_MISSING", key)
    v = raw[key]
    if not isinstance(v, str):
        raise InstallError("BINDING_FIELD_TYPE", key)
    stripped = v.strip()
    if stripped.upper() in PLACEHOLDER_TOKENS:
        raise InstallError("BINDING_PIN_PLACEHOLDER", key)
    return stripped


class Binding:
    """Strict pin/binding view validated against the operation's Contract."""

    def __init__(self, raw: Any, contract: Contract) -> None:
        if not isinstance(raw, dict):
            raise InstallError("BINDING_NOT_OBJECT")
        if _required(raw, "schema") != BINDING_SCHEMA:
            raise InstallError("BINDING_SCHEMA_UNEXPECTED")
        if _required(raw, "root_id") != ROOT_ID:
            raise InstallError("BINDING_ROOT_UNEXPECTED")
        op = _required(raw, "operation_id")
        if not op or len(op) > 64 or any(
                c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                for c in op):
            raise InstallError("BINDING_OPERATION_ID_MALFORMED")
        self.operation_id = op
        self.effect_commission_token = _required(raw, "effect_commission_token")
        if len(self.effect_commission_token) < 16:
            raise InstallError("BINDING_PIN_PLACEHOLDER", "effect_commission_token")
        archive_path = _required(raw, "archive_path")
        if not archive_path.startswith("/"):
            raise InstallError("BINDING_ARCHIVE_PATH_UNSAFE")
        self.archive_path = archive_path
        scratch = _required(raw, "operation_scratch_dir")
        if not scratch.startswith("/") or scratch == "/" or scratch.endswith("/"):
            raise InstallError("BINDING_SCRATCH_PATH_UNSAFE")
        self.operation_scratch_dir = scratch
        if _required(raw, "binary_version_path") != contract.runsc_path:
            raise InstallError("BINDING_VERSION_PATH_UNEXPECTED")
        pins = raw.get("member_sha256")
        if not isinstance(pins, dict) or sorted(pins) != list(contract.member_names):
            raise InstallError("BINDING_MEMBER_SET_UNEXPECTED")
        checked: Dict[str, str] = {}
        for name in sorted(pins):
            checked[name] = _hex64(pins, name)
        if checked.get("runsc") != contract.runsc_member_sha256:
            raise InstallError("BINDING_RUNSC_PIN_MISMATCH")
        self.member_sha256 = checked
        self.commission_token_sha256 = sha256_bytes(self.effect_commission_token.encode("utf-8"))

    def curated(self) -> Dict[str, Any]:
        """Facts safe for receipts.  The commission token itself is never
        emitted -- only its hash for out-of-band comparison by a human."""
        return {
            "operation_id": self.operation_id,
            "root_id": ROOT_ID,
            "archive_path": self.archive_path,
            "operation_scratch_dir": self.operation_scratch_dir,
            "member_sha256": dict(self.member_sha256),
            "effect_commission_token_sha256": self.commission_token_sha256,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Layout:
    """Path resolver.  Production resolves the pinned absolute contract paths
    unchanged; tests resolve the identical paths under a temporary root so no
    production path is ever touched.  Only contract constants are resolved."""

    def __init__(self, base: str = "") -> None:
        self.base = base.rstrip("/") if base else ""

    @classmethod
    def production(cls) -> "Layout":
        return cls("")

    @classmethod
    def under_root(cls, root: str) -> "Layout":
        return cls(root)

    @property
    def is_production(self) -> bool:
        return self.base == ""

    def p(self, absolute: str) -> str:
        if not absolute.startswith("/"):
            raise InstallError("INTERNAL_PATH_SHAPE")
        return self.base + absolute

    @property
    def daemon_json(self) -> str:
        return self.p(DAEMON_JSON_PATH)

    @property
    def docker_socket(self) -> str:
        return self.p(DOCKER_SOCKET_PATH)


def write_private_file(path: str, data: bytes, mode: int,
                       owner: Optional[Tuple[int, int]],
                       chown_fn: Callable[[str, int, int], None],
                       checkpoint: Optional[Callable[[], None]] = None) -> None:
    """Create a NEW regular file O_EXCL with the given mode, fsync it and its
    parent directory.  Never truncates or overwrites an existing entry."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    check = checkpoint or (lambda: None)
    check()
    try:
        fd = os.open(path, flags, mode)
    except PermissionError:
        raise InstallError("PERMISSION_REFUSED_WRITE") from None
    try:
        view = memoryview(data)
        while view:
            check()
            written = os.write(fd, view)
            if written <= 0:
                raise InstallError("PRIVATE_WRITE_NO_PROGRESS")
            view = view[written:]
        check()
        os.chmod(path, mode)  # enforce exact mode regardless of umask
        check()
        os.fsync(fd)
    finally:
        os.close(fd)
    if owner is not None:
        check()
        chown_fn(path, owner[0], owner[1])
    check()
    fsync_dir(os.path.dirname(path) or "/")


def inspect_docker_socket(path: str, expect_uid: int) -> Dict[str, Any]:
    """Verified local safe socket owner/type for the pinned daemon endpoint.
    Evidence input only -- never a permission grant."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        raise InstallError("SOCKET_MISSING") from None
    except PermissionError:
        raise InstallError("PERMISSION_REFUSED_SOCKET") from None
    if not stat.S_ISSOCK(st.st_mode):
        raise InstallError("SOCKET_TYPE_UNSAFE")
    if st.st_uid != expect_uid:
        raise InstallError("SOCKET_OWNER_UNSAFE")
    if st.st_mode & 0o002:
        raise InstallError("SOCKET_MODE_UNSAFE")
    return {"is_socket": True, "uid": st.st_uid, "mode": stat.S_IMODE(st.st_mode),
            "device": st.st_dev, "inode": st.st_ino}


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_BLOCKED = 3
EXIT_UNCERTAIN = 4
EXIT_INTERNAL = 5


def qualified_reload_hup(value):
    """Return True iff `value` is the canonical kill -s HUP $MAINPID shape."""
    if not isinstance(value, str):
        return False
    if len(value) > 4096:
        return False
    # ASCII printable only, no control characters
    for o in (ord(c) for c in value):
        if o < 0x20 or o > 0x7e:
            return False

    s = value.strip()
    if len(s) < 2 or s[0] != '{' or s[-1] != '}':
        return False
    inner = s[1:-1]
    if '{' in inner or '}' in inner:
        return False
    if not inner.strip():
        return False

    # Fields emitted by systemctl-show.c for ExecReload
    allowed = {
        'path', 'argv[]', 'ignore_errors',
        'start_time', 'stop_time', 'pid', 'code', 'status',
    }
    required = ('path', 'argv[]', 'ignore_errors')

    parsed = {}
    seen = set()
    for raw in inner.split(';'):
        f = raw.strip()
        if not f:
            return False
        if '=' not in f:
            return False
        key, _, val = f.partition('=')
        key = key.strip()
        val = val.strip()
        if not key or not val:
            return False
        if key not in allowed:
            return False
        if key in seen:
            return False
        seen.add(key)
        parsed[key] = val

    for k in required:
        if k not in parsed:
            return False

    if parsed['ignore_errors'] != 'no':
        return False

    path = parsed['path']
    if path not in ('/bin/kill', '/usr/bin/kill'):
        return False

    # argv[] must exactly match path + " -s HUP $MAINPID" with ordinary
    # single space separation. No shell, no extra flags, no extra targets,
    # no substitutions, no quoted/escaped spellings.
    if parsed['argv[]'] != path + ' -s HUP $MAINPID':
        return False

    return True


class InstallEngine:
    """Gated orchestration.  Default is a no-effects proposal; mutations happen
    only inside execute() after every pin/platform/scratch/socket/preimage
    gate.  Refusal or PermissionError freezes ALL later privileged actions
    including cleanup; an unconfirmed settlement freezes even rollback."""

    def __init__(self, layout: Layout, runner: Any,
                 contract: Optional[Contract] = None,
                 euid: Optional[int] = None,
                 root_uid: int = 0, root_gid: int = 0,
                 chown_fn: Optional[Callable[[str, int, int], None]] = None,
                 rename_fn: Optional[Callable[[str, str], None]] = None,
                 monotonic: Callable[[], float] = time.monotonic,
                 budget: Optional[Budget] = None,
                 sleeper: Callable[[float], None] = time.sleep,
                 socket_inspector: Optional[Callable[[str, int], Dict[str, Any]]] = None,
                 platform_probe: Optional[Callable[[], Tuple[str, str]]] = None,
                 disk_free_fn: Optional[Callable[[str], int]] = None,
                 settlement_window_seconds: Optional[float] = None,
                 settlement_interval_seconds: Optional[float] = None) -> None:
        self.layout = layout
        self.runner = runner
        self.contract = contract if contract is not None else PRODUCTION_CONTRACT
        self.host_id = platform.node()
        self.euid = euid if euid is not None else os.geteuid()
        # Production semantics pin root ownership (0:0).  Hermetic tests run
        # identical code with the fixture owner injected; defaults never change.
        self.root_uid = root_uid
        self.root_gid = root_gid
        self.chown_fn = chown_fn or os.chown
        self.rename_fn = rename_fn or rename_noreplace
        self.monotonic = monotonic
        runner_budget = getattr(runner, "budget", None)
        if budget is not None and runner_budget is not None and budget is not runner_budget:
            raise InstallError("BUDGET_IDENTITY_MISMATCH")
        self.budget = budget if budget is not None else (runner_budget if runner_budget is not None else Budget(monotonic=monotonic))
        self.sleeper = sleeper
        self.socket_inspector = socket_inspector or inspect_docker_socket
        self.platform_probe = platform_probe or (lambda: (platform.system(),
                                                          platform.machine()))
        self.disk_free_fn = disk_free_fn or (lambda p: shutil.disk_usage(p).free)
        self.settlement_window = float(settlement_window_seconds
                                       if settlement_window_seconds is not None
                                       else SETTLEMENT_WINDOW_SECONDS)
        self.settlement_interval = float(settlement_interval_seconds
                                         if settlement_interval_seconds is not None
                                         else SETTLEMENT_INTERVAL_SECONDS)
        self.notes: List[Dict[str, Any]] = []
        self.phase_seq = 0
        self.forbidden: List[str] = []
        self.binding: Optional[Binding] = None
        self._intent_written = False
        self._frozen = False
        # Truthful effect state for partial-failure receipts.
        self.status = "INTERNAL_NO_RESULT"
        self.unknowns: List[str] = []
        self.preimage_meta: Optional[Dict[str, Any]] = None
        self.preimage_sha: Optional[str] = None
        self.original_bytes: Optional[bytes] = None
        self.default_runtime_before: Optional[str] = None
        self.runtime_names_before: List[str] = []
        self.runtime_mapping_before: Dict[str, Any] = {}
        self.docker_config_path: Optional[str] = None
        self.docker_config_identity = None
        self.daemon_name: Optional[str] = None
        self.daemon_id: Optional[str] = None
        self.docker_client_version: Optional[str] = None
        self.docker_server_version: Optional[str] = None
        self.container_total = -1
        self.container_running = -1
        self.exec_reload_hup: Optional[bool] = None
        self.archive_sha: Optional[str] = None
        self.archive_size_seen = -1
        self.backup_path: Optional[str] = None
        self.backup_sha: Optional[str] = None
        self.bundle_created = False
        self.bundle_reused = False
        self.staging_path: Optional[str] = None
        self.staging_owned_created = False
        self.staging_published = False
        self.committed = False
        self.committed_sha: Optional[str] = None
        self.committed_meta: Optional[Dict[str, Any]] = None
        self.commit_uncertain = False
        self.settlement: Dict[str, Any] = {}
        self.rollback_result: Dict[str, Any] = {}

    # ---------------- freezing / notes / receipts ---------------- #

    @property
    def frozen(self) -> bool:
        return self._frozen or getattr(self.runner, "frozen", False)

    def freeze(self) -> None:
        self._frozen = True
        freeze = getattr(self.runner, "freeze", None)
        if callable(freeze):
            freeze()

    def _assert_effect_safe(self, role: str = "main") -> None:
        if self.frozen:
            raise EffectFrozen()
        if self.budget.expired(role == "rollback"):
            raise InstallError("BUDGET_EXCEEDED")

    def _note(self, phase: str, status: str, **extra: Any) -> None:
        rec: Dict[str, Any] = {"phase": phase, "status": status}
        rec.update(extra)
        rec["budget"] = self.budget.snapshot()
        self.notes.append(rec)
        if self._intent_written and self.binding is not None:
            self.phase_seq += 1
            path = "%s/phase_%s_%02d_%s.json" % (
                self.binding.operation_scratch_dir,
                self.binding.operation_id, self.phase_seq, phase)
            self._write_receipt_file(path, rec)  # failure must stop later phases

    def _guard_clean(self, obj: Any) -> bool:
        try:
            blob = json.dumps(obj, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return False
        return not any(f and f in blob for f in self.forbidden)

    def _write_receipt_file(self, path: str, obj: Dict[str, Any]) -> str:
        # Receipt publication is still a privileged filesystem mutation. After
        # refusal the caller receives only the in-memory result on this carrier.
        # Final/rollback receipts may use the existing total time reserve, never
        # a fresh deadline, and every filesystem step checks it again.
        def check() -> None:
            if self.frozen:
                raise EffectFrozen()
            if self.budget.wall_left(rollback=True) <= 0:
                raise InstallError("BUDGET_EXCEEDED")
        check()
        if not self._guard_clean(obj):
            obj = {"phase": obj.get("phase"), "status": "INTERNAL_REDACTION_FAULT"}
        try:
            write_private_file(path,
                               json.dumps(obj, indent=2, sort_keys=True).encode("utf-8"),
                               BACKUP_EXPECTED_MODE, (self.root_uid, self.root_gid),
                               self.chown_fn, checkpoint=check)
        except PermissionError:
            self.freeze()
            raise
        except InstallError as exc:
            if exc.category.startswith("PERMISSION_REFUSED"):
                self.freeze()
            raise
        return path

    def _collect_forbidden(self, obj: Any) -> None:
        """Register private config values so receipts can be guarded against
        leaking them.  Values stay private; only the guard uses them."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(p in str(k).lower() for p in SENSITIVE_KEY_PATTERNS):
                    self._collect_forbidden(v)
                else:
                    self._collect_forbidden(v)
        elif isinstance(obj, list):
            for v in obj:
                self._collect_forbidden(v)
        elif isinstance(obj, str):
            if ("://" in obj or len(obj) >= 40) and obj not in (
                    RUNSC_BINARY_PATH, DOCKER_SOCKET_ARG):
                self.forbidden.append(obj)

    def _gate_failure(self, where: str, exc: InstallError) -> InstallError:
        if self.status.startswith("UNKNOWN_"):
            return exc  # keep an already recorded unsettled effect classification
        if exc.category == "BUDGET_EXCEEDED":
            self.status = "STOP_BUDGET_EXCEEDED_" + where
        elif exc.category in ("COMMAND_TIMEOUT_UNKNOWN",):
            self.status = "UNKNOWN_" + where + "_TIMEOUT"
        elif exc.category == "PRE_EFFECT_GATE_FAILED" and exc.detail:
            self.status = "BLOCKED_PRE_EFFECT_GATE_" + exc.detail
        elif exc.category.startswith(("PERMISSION_REFUSED",)) or exc.category in (
                "SUDO_NONZERO_AMBIGUOUS_REFUSAL", "PRIVILEGED_NONZERO_AMBIGUOUS",
                "DOCKER_QUERY_UNVERIFIED_NONZERO", "CONTROL_STDERR_WITH_RC0",
                "EFFECTS_FROZEN_BY_REFUSAL", "UNCLASSIFIED_NONZERO"):
            self.status = "REFUSED_" + where
        else:
            self.status = "BLOCKED_" + where + "_" + exc.category
        return exc

    # ---------------- curated docker/systemctl readers ---------------- #

    def _run(self, argv: List[str], role: str = "main") -> Dict[str, Any]:
        rollback = role == "rollback"
        if self.budget.expired(rollback) or self.budget.out_left(rollback) <= 0:
            raise InstallError("BUDGET_EXCEEDED")
        self._assert_effect_safe(role)
        try:
            result = self.runner.run(argv, role=role)
            if (result.get("truncated") is not False or result.get("timed_out") is not False
                    or type(result.get("rc")) is not int or result["rc"] != 0):
                self.freeze()
                raise InstallError("INCOMPLETE_COMMAND_OBSERVATION")
            return result
        except EffectFrozen:
            raise
        except InstallError:
            self.freeze()
            raise

    def _docker(self, args: List[str], role: str = "main") -> Dict[str, Any]:
        self._verify_client_config()
        return self._run([DOCKER_BIN, "--host", DOCKER_SOCKET_ARG,
                          "--config", self.docker_config_path] + args, role)

    @staticmethod
    def _text(res: Dict[str, Any]) -> str:
        return res["out"].decode("utf-8", "replace").strip()

    def _parse_show(self, out: bytes) -> Dict[str, Any]:
        facts: Dict[str, Any] = {}
        for line in out.decode("utf-8", "replace").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in SYSTEMD_ALLOWED_KEYS:
                # Multiple ExecReload commands render as repeated properties;
                # none may be hidden by accepting the final line alone.
                if key in facts:
                    raise InstallError("SERVICE_FACT_DUPLICATE")
                facts[key] = value
        return facts

    def _service_facts(self, role: str = "main") -> Dict[str, Any]:
        res = self._run([SUDO_BIN, "-n", SYSTEMCTL_BIN, "show", DOCKER_SERVICE_UNIT,
                         "--property=" + ",".join(SYSTEMD_ALLOWED_KEYS)], role)
        facts = self._parse_show(res["out"])
        reload_value = facts.get("ExecReload", "")
        # systemctl renders argv[] as a joined string. This only qualifies
        # the narrow standard kill/HUP rendering, not argv authentication or
        # effect settlement; the existing reload and settlement gates remain.
        self.exec_reload_hup = qualified_reload_hup(reload_value)
        return facts

    def _info_field(self, fmt: str, what: str, role: str = "main") -> str:
        raw = self._docker(["info", "--format", fmt], role)["out"]
        return raw.decode("utf-8", "replace").strip()

    def _container_counts(self, role: str = "main") -> Tuple[int, int]:
        total_raw = self._info_field("{{.Containers}}", "containers", role)
        run_raw = self._info_field("{{.ContainersRunning}}", "containers-running", role)
        try:
            return int(total_raw), int(run_raw)
        except ValueError:
            raise InstallError("DOCKER_FACT_UNPARSEABLE") from None

    def _runtime_mapping(self, role: str = "main") -> Dict[str, Any]:
        # Docker 29.1.3 RuntimeWithStatus embeds Runtime plus potentially large
        # capability/status data. Project the complete Runtime configuration
        # in the CLI before its output enters our unchanged bounded collector.
        # This preserves path, args, shim type and options for every runtime;
        # only volatile status is excluded from before/after configuration
        # comparisons. JSON encoding also preserves unusual map keys safely.
        fmt = ('{ {{ $first := true }}{{range $name, $runtime := .Runtimes}}'
               '{{if not $first}},{{end}}{{ $first = false }}'
               '{{json $name}}:{{json $runtime.Runtime}}{{end}} }')
        raw = self._info_field(fmt, "runtimes", role)
        mapping = json_loads_strict(raw, "docker-info-runtimes")
        if not isinstance(mapping, dict) or not mapping or not all(isinstance(v, dict)
                                                    for v in mapping.values()):
            raise InstallError("DOCKER_FACT_UNPARSEABLE")
        return mapping

    def _expected_entry(self) -> Dict[str, Any]:
        return {"path": self.layout.p(self.contract.runsc_path),
                "runtimeArgs": list(RUNSC_RUNTIME_ARGS)}

    @staticmethod
    def _entry_matches(entry: Any, expected: Dict[str, Any]) -> bool:
        return (isinstance(entry, dict)
                and entry.get("path") == expected["path"]
                and entry.get("runtimeArgs") == expected["runtimeArgs"])

    # ---------------- archive: whole pin + member scan (streamed) ---------------- #

    def _check_archive_metadata(self) -> None:
        path = self.binding.archive_path if self.binding else ""
        meta = lstat_meta(path)
        if meta is None:
            raise InstallError("ARCHIVE_MISSING")
        if meta["is_symlink"] or not meta["is_regular"]:
            raise InstallError("ARCHIVE_NOT_REGULAR_FILE")
        if meta["size"] != self.contract.archive_size:
            raise InstallError("ARCHIVE_SIZE_MISMATCH")
        if meta["size"] > LIMITS["archive_max_bytes"]:
            raise InstallError("ARCHIVE_OVERSIZE")

    def _verify_archive_pin(self) -> None:
        """Whole-archive SHA256 streamed in bounded chunks BEFORE any
        privileged mutation.  The 262144 B cap never applies here."""
        self._check_archive_metadata()
        sha, size = sha256_streamed(self.binding.archive_path, ARCHIVE_MAX_BYTES, self._assert_effect_safe)
        if size != self.contract.archive_size:
            raise InstallError("ARCHIVE_SIZE_MISMATCH")
        if sha != self.contract.archive_sha256:
            raise InstallError("ARCHIVE_PIN_MISMATCH")
        self.archive_sha = sha
        self.archive_size_seen = size

    def _consume_member(self, tf: Any, member: Any, name: str,
                        staging_dir: Optional[str]) -> str:
        """Stream one member in bounded chunks: hash every byte, optionally
        write it into the stage tree.  Detects short and oversize streams.
        Never buffers a whole member in RAM."""
        expected = self.contract.member_sizes[name]
        fobj = tf.extractfile(member)
        if fobj is None:
            raise InstallError("ARCHIVE_MEMBER_TYPE_UNSAFE")
        digest = hashlib.sha256()
        total = 0
        out_fd = None
        dest = None
        if staging_dir is not None:
            dest = staging_dir + "/" + name
            try:
                out_fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                 FILE_EXPECTED_MODE)
            except PermissionError:
                self.freeze()
                raise InstallError("PERMISSION_REFUSED_WRITE") from None
        first = b""
        try:
            while True:
                self._assert_effect_safe()
                try:
                    chunk = fobj.read(CHUNK_BYTES)
                except tarfile.ReadError:
                    break  # compressed stream ended early: classified below
                if not chunk:
                    break
                if not first:
                    first = chunk[:4]
                total += len(chunk)
                digest.update(chunk)
                if out_fd is not None:
                    remaining = memoryview(chunk)
                    while remaining:
                        written = os.write(out_fd, remaining)
                        if written <= 0:
                            raise InstallError("BUNDLE_WRITE_NO_PROGRESS")
                        remaining = remaining[written:]
                if total > expected:
                    raise InstallError("ARCHIVE_MEMBER_OVERSIZE_STREAM")
            # Completion metadata is never a finally action: a denied write or
            # elapsed deadline must leave the partial stage untouched.
            if out_fd is not None:
                self._assert_effect_safe()
                os.fsync(out_fd)
                self._assert_effect_safe()
                self.chown_fn(dest, self.root_uid, self.root_gid)
        except PermissionError:
            self.freeze()
            raise
        finally:
            if out_fd is not None:
                os.close(out_fd)
        if total != expected:
            raise InstallError("ARCHIVE_MEMBER_SHORT_STREAM")
        if name == "runsc":
            if first != ELF_MAGIC:
                raise InstallError("ARCHIVE_RUNSC_NOT_ELF")
        return digest.hexdigest()

    def _scan_archive(self, staging_dir: Optional[str]) -> Dict[str, Any]:
        """One sequential pass over the pinned archive: exact name/type/size
        set, duplicate/traversal/link rejection, streamed member hashes
        compared to the binding pins (all derived from this exact archive by
        the acquisition commission and re-derived here).  Optional shim and
        the gvisor-bin directory entry are tolerated; the shim is NEVER
        installed."""
        sizes = self.contract.member_sizes
        pins = self.binding.member_sha256
        seen: Dict[str, int] = {}
        found: set = set()
        try:
            tf = tarfile.open(self.binding.archive_path, "r|bz2")
        except tarfile.TarError:
            raise InstallError("ARCHIVE_UNPARSEABLE") from None
        try:
            for member in tf:
                self._assert_effect_safe()
                name = member.name
                if name.startswith("/") or ".." in name.split("/"):
                    raise InstallError("ARCHIVE_MEMBER_UNSAFE")
                if member.isdir():
                    # tarfile strips the trailing slash on read: accept both
                    # spellings of the gvisor-bin directory entry only. The
                    # pinned publisher places it after the shim and runsc;
                    # previous regular members are not directory duplicates.
                    if name not in (OPTIONAL_DIR_MEMBER, GVISOR_BIN_DIR):
                        raise InstallError("ARCHIVE_MEMBER_UNEXPECTED")
                    if OPTIONAL_DIR_MEMBER in seen:
                        raise InstallError("ARCHIVE_MEMBER_DUPLICATE")
                    seen[OPTIONAL_DIR_MEMBER] = 0
                    continue
                if member.issym() or member.islnk() or member.isdev() \
                        or not member.isfile():
                    raise InstallError("ARCHIVE_MEMBER_TYPE_UNSAFE")
                if name in seen:
                    raise InstallError("ARCHIVE_MEMBER_DUPLICATE")
                if name in sizes:
                    if member.size != sizes[name]:
                        raise InstallError("ARCHIVE_MEMBER_SIZE_MISMATCH")
                    sha = self._consume_member(tf, member, name, staging_dir)
                    if sha != pins[name]:
                        raise InstallError("ARCHIVE_MEMBER_HASH_MISMATCH")
                    found.add(name)
                    seen[name] = member.size
                elif name == OPTIONAL_SHIM_MEMBER:
                    # tolerated by name/type; drained bounded, NEVER installed
                    shim_obj = tf.extractfile(member)
                    if shim_obj is None:
                        raise InstallError("ARCHIVE_MEMBER_TYPE_UNSAFE")
                    drained = 0
                    while True:
                        self._assert_effect_safe()
                        chunk = shim_obj.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        drained += len(chunk)
                    seen[name] = drained
                else:
                    raise InstallError("ARCHIVE_MEMBER_UNEXPECTED")
        except tarfile.TarError:
            raise InstallError("ARCHIVE_UNPARSEABLE") from None
        finally:
            tf.close()
        missing = [n for n in sizes if n not in found]
        if missing:
            raise InstallError("ARCHIVE_MEMBER_MISSING", str(len(missing)))
        return {"members_seen": len(seen), "members_installed": sorted(found),
                "shim_installed": False}

    # ---------------- stage / publish the complete version directory ------- #

    def _stage_bundle(self) -> str:
        self._assert_effect_safe()
        version_dir = self.layout.p(self.contract.version_dir)
        parent = version_dir.rsplit("/", 1)[0]
        stage = parent + "/.stage-" + (self.binding.operation_id if self.binding else "op")
        self.staging_path = stage
        missing = check_ancestors(stage, self.root_uid, base=self.layout.base)
        if missing:
            ensure_ancestors(stage, self.root_uid, self.chown_fn,
                             base=self.layout.base)
        if lstat_meta(stage) is not None:
            raise InstallError("STAGE_PATH_OCCUPIED")
        os.mkdir(stage, NEWDIR_EXPECTED_MODE)
        self.staging_owned_created = True
        self.chown_fn(stage, self.root_uid, self.root_gid)
        os.mkdir(stage + "/" + GVISOR_BIN_DIR, NEWDIR_EXPECTED_MODE)
        self.chown_fn(stage + "/" + GVISOR_BIN_DIR, self.root_uid, self.root_gid)
        try:
            scan = self._scan_archive(staging_dir=stage)
            # Verify every staged file from disk: exact size, mode, owner,
            # bytes; ELF magic only for runsc; scripts accepted by exact
            # bytes/type.  Then fsync both directories.
            for name in self.contract.member_names:
                p = stage + "/" + name
                m = lstat_meta(p)
                if m is None or m["is_symlink"] or not m["is_regular"]:
                    raise InstallError("BUNDLE_STAGE_VERIFY_FAILED")
                if m["mode"] != FILE_EXPECTED_MODE or m["uid"] != self.root_uid \
                        or m["gid"] != self.root_gid \
                        or m["size"] != self.contract.member_sizes[name]:
                    raise InstallError("BUNDLE_STAGE_VERIFY_FAILED")
                sha, _ = sha256_streamed(p, self.contract.member_sizes[name], lambda: self._assert_effect_safe("rollback" if self.budget._rollback_start is not None else "main"))
                if sha != self.binding.member_sha256[name]:
                    raise InstallError("BUNDLE_STAGE_VERIFY_FAILED")
                if name == "runsc":
                    with open(p, "rb") as fh:
                        if fh.read(4) != ELF_MAGIC:
                            raise InstallError("ARCHIVE_RUNSC_NOT_ELF")
            fsync_dir(stage + "/" + GVISOR_BIN_DIR)
            fsync_dir(stage)
            fsync_dir(parent)
        except PermissionError:
            self.freeze()
            raise
        except OSError:
            raise InstallError("BUNDLE_STAGE_WRITE_FAILED") from None
        scan["stage_path"] = stage
        return stage

    def _verify_bundle_dir(self, d: str) -> bool:
        """True only for the complete exact reviewed member set: every file
        regular (no symlink), exact mode/owner/size/hash, no extras at either
        level.  Anything else is a collision that is never adopted or
        overwritten."""
        for directory in (d, d + "/" + GVISOR_BIN_DIR):
            meta = lstat_meta(directory)
            if (meta is None or meta["is_symlink"] or not meta["is_dir"]
                    or meta["mode"] != NEWDIR_EXPECTED_MODE
                    or meta["uid"] != self.root_uid or meta["gid"] != self.root_gid):
                return False
        try:
            if sorted(os.listdir(d)) != ["gvisor-bin", "runsc"]:
                return False
            expected_sidecars = sorted(n.split("/", 1)[1]
                                       for n in self.contract.member_names
                                       if n != "runsc")
            if sorted(os.listdir(d + "/" + GVISOR_BIN_DIR)) != expected_sidecars:
                return False
        except OSError:
            raise InstallError("BUNDLE_LIST_FAILED") from None
        for name in self.contract.member_names:
            p = d + "/" + name
            m = lstat_meta(p)
            if m is None or m["is_symlink"] or not m["is_regular"]:
                return False
            if m["mode"] != FILE_EXPECTED_MODE or m["uid"] != self.root_uid \
                    or m["gid"] != self.root_gid \
                    or m["size"] != self.contract.member_sizes[name]:
                return False
            sha, _ = sha256_streamed(p, self.contract.member_sizes[name], lambda: self._assert_effect_safe("rollback" if self.budget._rollback_start is not None else "main"))
            if sha != self.binding.member_sha256[name]:
                return False
        return True

    def _publish_bundle(self, stage: str) -> None:
        """ONE genuine directory publication via renameat2 RENAME_NOREPLACE.
        No plain-rename fallback.  Collision preserves the prior directory
        (even an empty one); reuse only after full exact verification."""
        self._assert_effect_safe()
        dest = self.layout.p(self.contract.version_dir)
        parent = dest.rsplit("/", 1)[0]
        try:
            self.rename_fn(stage, dest)
        except PermissionError:
            self.freeze()
            raise
        except OSError as exc:
            if isinstance(exc, FileExistsError) or exc.errno == errno.EEXIST:
                if self._verify_bundle_dir(dest):
                    self.bundle_reused = True
                    self._note("bundle_publish", "OK_REUSED_EXISTING")
                    return
                raise InstallError("BUNDLE_COLLISION_PRESERVED") from None
            if exc.errno in (errno.ENOSYS, errno.EINVAL, errno.ENOTTY):
                raise InstallError("PUBLISH_PRIMITIVE_UNAVAILABLE") from None
            raise InstallError("PUBLISH_FAILED", "stage retained") from None
        self.bundle_created = True  # Publication happened even if later sync/verification fails.
        self.staging_published = True
        fsync_dir(parent)
        if not self._verify_bundle_dir(dest):
            raise InstallError("PUBLISH_POSTVERIFY_FAILED", "published state retained")
        self.bundle_created = True

    def _remove_bundle(self) -> bool:
        """Remove the ENTIRE newly created, fully identified bundle using only
        the fixed member paths (no arbitrary recursion).  rmdir fails closed
        on any extra entry, preserving unknown content."""
        self._assert_effect_safe("rollback")
        dest = self.layout.p(self.contract.version_dir)
        if not self._verify_bundle_dir(dest):
            return False
        try:
            for name in sorted(self.contract.member_names):
                self._assert_effect_safe("rollback")
                os.unlink(dest + "/" + name)
            os.rmdir(dest + "/" + GVISOR_BIN_DIR)
            os.rmdir(dest)
            fsync_dir(dest.rsplit("/", 1)[0])
        except PermissionError:
            self.freeze()
            raise
        except OSError:
            return False
        return True

    # ---------------- private config / backup / candidate / commit --------- #

    def _read_config(self) -> Any:
        path = self.layout.daemon_json
        if check_ancestors(path, self.root_uid, base=self.layout.base) is not None:
            raise InstallError("CONFIG_ANCESTOR_MISSING")
        meta = lstat_meta(path)
        if meta is None:
            raise InstallError("CONFIG_MISSING")
        if meta["is_symlink"] or not meta["is_regular"]:
            raise InstallError("CONFIG_NOT_REGULAR_FILE")
        if meta["mode"] != CONFIG_EXPECTED_MODE:
            raise InstallError("CONFIG_MODE_UNEXPECTED")
        if meta["uid"] != self.root_uid or meta["gid"] != self.root_gid:
            raise InstallError("CONFIG_OWNER_UNEXPECTED")
        data = read_regular_bounded(path, LIMITS["max_config_read_bytes"])
        self.preimage_meta = meta
        self.preimage_sha = sha256_bytes(data)
        self.original_bytes = data
        obj = json_loads_strict(data.decode("utf-8"), "daemon-json")
        self._collect_forbidden(obj)
        return obj

    def _write_backup(self) -> None:
        self._assert_effect_safe()
        scratch = self.binding.operation_scratch_dir
        if check_ancestors(scratch, self.root_uid, base=self.layout.base) is not None:
            raise InstallError("SCRATCH_ANCESTOR_MISSING")
        self.backup_path = scratch + "/daemon.json.preimage"
        write_private_file(self.backup_path, self.original_bytes or b"",
                           BACKUP_EXPECTED_MODE, (self.root_uid, self.root_gid),
                           self.chown_fn)
        self.backup_sha = sha256_bytes(read_regular_bounded(
            self.backup_path, LIMITS["max_config_read_bytes"]))
        if self.backup_sha != self.preimage_sha:
            raise InstallError("BACKUP_HASH_MISMATCH")

    def _build_candidate(self, obj: Any) -> Tuple[Any, bytes]:
        cand = copy.deepcopy(obj)
        existing = obj.get("runtimes") if isinstance(obj.get("runtimes"), dict) else {}
        runtimes = dict(existing)
        runtimes[RUNTIME_NAME] = copy.deepcopy(self._expected_entry())
        cand["runtimes"] = runtimes
        assert_exact_addition(obj, cand, self._expected_entry(), RUNTIME_NAME)
        cand_bytes = (json.dumps(cand, indent=2) + "\n").encode("utf-8")
        if len(cand_bytes) > LIMITS["max_config_read_bytes"]:
            raise InstallError("CANDIDATE_OVERSIZED")
        return cand, cand_bytes

    def _validate_with_dockerd(self, cand_bytes: bytes) -> None:
        """Qualified dockerd config validation only -- never a daemon start."""
        self._assert_effect_safe()
        scratch = self.binding.operation_scratch_dir
        validate_path = scratch + "/validate-candidate.json"
        write_private_file(validate_path, cand_bytes, BACKUP_EXPECTED_MODE,
                           (self.root_uid, self.root_gid), self.chown_fn)
        try:
            res = self._run([DOCKERD_BIN, "--validate", "--config-file", validate_path])
            if res["rc"] != 0:
                raise InstallError("VALIDATION_TECHNICAL_FAILURE")
        finally:
            if not self.frozen and not self.budget.expired():
                try:
                    os.unlink(validate_path)
                    fsync_dir(scratch)
                except PermissionError:
                    self.freeze()
                    raise
                except OSError:
                    pass

    def _fresh_config_state(self) -> Tuple[Dict[str, Any], str]:
        path = self.layout.daemon_json
        meta = lstat_meta(path)
        if meta is None:
            raise InstallError("CONFIG_MISSING")
        data = read_regular_bounded(path, LIMITS["max_config_read_bytes"])
        return meta, sha256_bytes(data)

    @staticmethod
    def _meta_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        keys = ("device", "inode", "mtime_ns", "uid", "gid", "mode", "size")
        return all(a.get(k) == b.get(k) for k in keys)

    def _commit(self, cand_bytes: bytes, cand_sha: str) -> None:
        """Compare-before-commit is honest best effort: hash/inode/device/
        mtime/mode are re-read immediately before the replace, but a race
        window remains and there is no atomic compare-and-swap and no
        exclusive lease.  The irreversible boundary is recorded IMMEDIATELY
        after the rename: post-replace errors record committed-or-uncertain,
        never a pre-effect label."""
        self._assert_effect_safe()
        path = self.layout.daemon_json
        meta, sha = self._fresh_config_state()
        if sha != self.preimage_sha or not self._meta_equal(meta, self.preimage_meta or {}):
            raise InstallError("CONTROL_GAP_PREIMAGE_CHANGED")
        stage = path + ".stage-" + (self.binding.operation_id if self.binding else "op")
        if lstat_meta(stage) is not None:
            raise InstallError("STAGE_PATH_OCCUPIED")
        try:
            write_private_file(stage, cand_bytes, meta["mode"],
                               (meta["uid"], meta["gid"]), self.chown_fn)
        except PermissionError:
            self.freeze()
            raise
        except OSError:
            raise InstallError("CONFIG_STAGE_WRITE_FAILED") from None
        self._assert_effect_safe()
        try:
            os.rename(stage, path)
        except PermissionError:
            self.freeze()
            raise
        except OSError:
            try:
                os.unlink(stage)
            except OSError:
                pass
            raise InstallError("CONFIG_REPLACE_FAILED") from None
        # Irreversible boundary: the replace happened; record it now.
        self.committed = True
        fsync_dir(os.path.dirname(path))
        new_meta, new_sha = self._fresh_config_state()
        if new_sha != cand_sha:
            self.commit_uncertain = True
            self.committed_sha = new_sha
            self.committed_meta = new_meta
            raise InstallError("POSTCOMMIT_HASH_UNVERIFIED")
        if new_meta["mode"] != meta["mode"] or new_meta["uid"] != meta["uid"] \
                or new_meta["gid"] != meta["gid"]:
            self.commit_uncertain = True
            self.committed_sha = new_sha
            self.committed_meta = new_meta
            raise InstallError("POSTCOMMIT_METADATA_UNVERIFIED")
        self.committed_sha = new_sha
        self.committed_meta = new_meta

    # ---------------- reload / settlement / rollback ----------------------- #

    def _reload(self, role: str) -> None:
        self._run([SUDO_BIN, "-n", SYSTEMCTL_BIN, "reload", DOCKER_SERVICE_UNIT],
                  role=role)

    def _poll_state(self, role: str) -> Dict[str, Any]:
        socket_now = self.socket_inspector(self.layout.docker_socket, self.root_uid)
        if socket_now != self.socket_facts or self._info_field("{{.ID}}", "id", role) != self.daemon_id:
            self.freeze()
            raise InstallError("DAEMON_IDENTITY_CHANGED")
        service = self._service_facts(role)
        runtimes = self._runtime_mapping(role)
        default_now = self._info_field("{{.DefaultRuntime}}", "default", role)
        return {"service": service, "runtimes": runtimes, "default": default_now}

    def _state_verified(self, st: Dict[str, Any], expect_rf: bool) -> bool:
        ok_service = st["service"].get("ActiveState") == TRUTHY_ACTIVE
        ok_default = st["default"] == self.default_runtime_before
        entry = st["runtimes"].get(RUNTIME_NAME)
        if expect_rf:
            ok_rf = self._entry_matches(entry, self._expected_entry())
        else:
            ok_rf = entry is None
        before = {k: v for k, v in self.runtime_mapping_before.items() if k != RUNTIME_NAME}
        current = {k: v for k, v in st["runtimes"].items() if k != RUNTIME_NAME}
        return bool(ok_service and ok_default and ok_rf and current == before)

    def _settle(self, role: str, expect_rf: bool) -> Dict[str, Any]:
        """Bounded read-only same-daemon settlement.  CLI rc0 alone is never
        sufficient.  Delayed registration settles without a second mutation.
        A readable non-active service is a proven ordinary failure (rollback
        may proceed).  The deadline WITHOUT confirmation is UNKNOWN and
        freezes even rollback -- no mutation retry ever follows."""
        deadline = self.monotonic() + self.settlement_window
        polls = 0
        def record(state: Dict[str, Any]) -> Dict[str, Any]:
            if role == "rollback":
                self.rollback_result["settlement"] = dict(state)
            else:
                self.settlement = dict(state)
            return state
        while True:
            try:
                st = self._poll_state(role)
            except (InstallError, OSError) as exc:
                reason = exc.category if isinstance(exc, InstallError) else "OS_ERROR"
                record({"confirmed": False, "verified": False, "polls": polls,
                        "outcome": "OBSERVATION_FAILED", "reason": reason})
                self.status = ("UNKNOWN_ROLLBACK_SETTLEMENT" if role == "rollback"
                               else "UNKNOWN_INSTALL_SETTLEMENT")
                self.unknowns.append("same-daemon settlement observation failed: " + reason)
                self.freeze()
                if isinstance(exc, InstallError):
                    raise
                raise InstallError("SETTLEMENT_OBSERVATION_FAILED") from None
            polls += 1
            summary = {"runtime_names": sorted(st["runtimes"]),
                       "default_runtime": st["default"]}
            if self._state_verified(st, expect_rf):
                return record({"confirmed": True, "verified": True,
                               "polls": polls, "outcome": "VERIFIED", **summary})
            if st["service"].get("ActiveState") != TRUTHY_ACTIVE:
                return record({"confirmed": True, "verified": False,
                               "polls": polls, "outcome": "SERVICE_NOT_ACTIVE",
                               **summary})
            if self.monotonic() >= deadline:
                return record({"confirmed": False, "verified": False,
                               "polls": polls,
                               "outcome": "DEADLINE_UNCONFIRMED", **summary})
            self.sleeper(self.settlement_interval)

    def _rollback(self) -> Dict[str, Any]:
        """Guarded rollback: ONE config restore and ONE qualified reload,
        followed by bounded read-only settlement.  Requires settled effect
        state, the exact owned committed config and the private backup.
        Intervening writer, invalid backup, refusal or unconfirmed reload
        forbids rollback, reload and delete retries.  The newly created fully
        identified bundle is removed only after exact runtime-entry absence,
        actual inventory removal, default preservation and a zero container
        census; reused bundles are preserved."""
        self.budget.begin_rollback()
        self._assert_effect_safe("rollback")
        result: Dict[str, Any] = {"attempted": True, "status": "UNKNOWN"}
        self.rollback_result = result
        if not self.committed:
            result["status"] = "STOP_ROLLBACK_NOT_COMMITTED"
            return result
        path = self.layout.daemon_json
        meta, sha = self._fresh_config_state()
        cm = self.committed_meta or {}
        if sha != self.committed_sha or meta["inode"] != cm.get("inode") \
                or meta["device"] != cm.get("device"):
            result["status"] = "STOP_ROLLBACK_DENIED_INTERVENING_WRITER"
            return result
        if self.backup_path is None or self.backup_sha != self.preimage_sha:
            result["status"] = "STOP_ROLLBACK_DENIED_BACKUP_INVALID"
            return result
        bmeta = lstat_meta(self.backup_path) or {}
        if bmeta.get("mode") != BACKUP_EXPECTED_MODE or bmeta.get("uid") != self.root_uid:
            result["status"] = "STOP_ROLLBACK_DENIED_BACKUP_INVALID"
            return result
        original_bytes = read_regular_bounded(self.backup_path,
                                              LIMITS["max_config_read_bytes"])
        if sha256_bytes(original_bytes) != self.preimage_sha:
            result["status"] = "STOP_ROLLBACK_DENIED_BACKUP_INVALID"
            return result
        stage = path + ".restore-" + (self.binding.operation_id if self.binding else "op")
        if lstat_meta(stage) is not None:
            result["status"] = "STOP_ROLLBACK_DENIED_STAGE_OCCUPIED"
            return result
        pm = self.preimage_meta or {}
        write_private_file(stage, original_bytes, pm.get("mode", CONFIG_EXPECTED_MODE),
                           (pm.get("uid", self.root_uid), pm.get("gid", self.root_gid)),
                           self.chown_fn)
        self._assert_effect_safe("rollback")
        try:
            os.rename(stage, path)
        except PermissionError:
            self.freeze()
            raise
        except OSError:
            result["status"] = "STOP_ROLLBACK_REPLACE_FAILED"
            return result
        self.committed = False
        fsync_dir(os.path.dirname(path))
        rmeta, rsha = self._fresh_config_state()
        if rsha != self.preimage_sha or rmeta["mode"] != pm.get("mode") \
                or rmeta["uid"] != pm.get("uid") or rmeta["gid"] != pm.get("gid"):
            result["status"] = "UNKNOWN_ROLLBACK_POSTSTATE"
            return result
        result["restored_sha256"] = rsha
        try:
            self._reload("rollback")
            facts = self._settle("rollback", expect_rf=False)
        except InstallError as exc:
            self._gate_failure("AT_ROLLBACK", exc)
            result["status"] = self.status
            return result
        if not (facts.get("confirmed") and facts.get("verified")):
            result["status"] = "UNKNOWN_ROLLBACK_SETTLEMENT"
            result["settlement"] = facts
            return result
        result["runtime_names"] = facts.get("runtime_names", [])
        result["default_runtime"] = facts.get("default_runtime")
        # removal: only a bundle this operation created, still fully identified
        if self.bundle_created and not self.bundle_reused:
            total, running = self._container_counts("rollback")
            if total != EXPECTED_CONTAINER_COUNT or running != EXPECTED_CONTAINER_COUNT:
                result["cleanup_obligation"] = "container census nonzero; bundle preserved"
            elif self._remove_bundle():
                result["new_bundle_removed"] = True
            else:
                result["cleanup_obligation"] = ("bundle not fully identified at "
                                                "removal time; preserved")
        result["status"] = "OK_ROLLED_BACK"
        return result

    # ---------------- orchestration ---------------- #

    def _validate_scratch(self) -> None:
        """The operation scratch (already admitted own scratch) must pre-exist
        as a root-owned 0700 real directory with safe ancestors.  This helper
        never creates system directories and never creates the scratch."""
        scratch = self.binding.operation_scratch_dir if self.binding else ""
        if check_ancestors(scratch, self.root_uid, base=self.layout.base) is not None:
            raise InstallError("SCRATCH_MISSING")
        meta = lstat_meta(scratch)
        if meta is None:
            raise InstallError("SCRATCH_MISSING")
        if meta["is_symlink"] or not meta["is_dir"]:
            raise InstallError("SCRATCH_NOT_DIRECTORY")
        if meta["mode"] != SCRATCH_EXPECTED_MODE:
            raise InstallError("SCRATCH_MODE_UNEXPECTED")
        if meta["uid"] != self.root_uid or meta["gid"] != self.root_gid:
            raise InstallError("SCRATCH_OWNER_UNEXPECTED")

    def _prepare_client_config(self) -> None:
        # Fresh operation-owned anonymous config: no saved config or helper discovery.
        directory = self.binding.operation_scratch_dir + "/docker-client"
        os.mkdir(directory, 0o700)
        self.chown_fn(directory, self.root_uid, self.root_gid)
        raw = b'{"auths":{"https://index.docker.io/v1/":{}}}\n'
        write_private_file(directory + "/config.json", raw, 0o600,
                           (self.root_uid, self.root_gid), self.chown_fn)
        fsync_dir(self.binding.operation_scratch_dir)
        self.docker_config_path = directory
        d = os.lstat(directory); f = os.lstat(directory + "/config.json")
        self.docker_config_identity = ((d.st_dev, d.st_ino), (f.st_dev, f.st_ino), raw)
        self._verify_client_config()

    def _verify_client_config(self) -> None:
        if self.docker_config_path is None or self.docker_config_identity is None:
            raise InstallError("CLIENT_CONFIG_UNBOUND")
        directory = self.docker_config_path
        d = os.lstat(directory); f = os.lstat(directory + "/config.json")
        expected_dir, expected_file, expected_bytes = self.docker_config_identity
        if (not stat.S_ISDIR(d.st_mode) or not stat.S_ISREG(f.st_mode)
                or f.st_nlink != 1 or stat.S_IMODE(d.st_mode) != 0o700
                or stat.S_IMODE(f.st_mode) != 0o600
                or (d.st_uid, d.st_gid) != (self.root_uid, self.root_gid)
                or (f.st_uid, f.st_gid) != (self.root_uid, self.root_gid)
                or (d.st_dev, d.st_ino) != expected_dir
                or (f.st_dev, f.st_ino) != expected_file
                or sorted(os.listdir(directory)) != ["config.json"]
                or read_regular_bounded(directory + "/config.json", 1024) != expected_bytes):
            self.freeze()
            raise InstallError("CLIENT_CONFIG_CHANGED")

    def _write_intent(self) -> None:
        scratch = self.binding.operation_scratch_dir
        try:
            self._write_receipt_file(scratch + "/intent.json", {
                "schema": "mastermind.rf_runsc_install_intent.v2",
                "operation_id": self.binding.operation_id,
                "root_id": ROOT_ID,
                "binding": self.binding.curated(),
                "observed_host": {"hostname": self.host_id, "uid": self.euid,
                                  "platform": list(self.platform_probe())},
                "plan": ["preflight", "archive_pin", "member_pins", "candidate",
                         "backup", "bundle_stage", "bundle_publish", "validate",
                         "commit", "reload", "settle"],
                "trust_boundary": "caller-supplied JSON is not root authority; "
                                  "execution requires an explicit root effect commission",
            })
        except PermissionError:
            raise InstallError("PERMISSION_REFUSED_INTENT_WRITE") from None
        except OSError:
            raise InstallError("INTERNAL_INTENT_WRITE_FAILED") from None
        self._intent_written = True

    def _preflight(self) -> Any:
        socket_facts = self.socket_inspector(self.layout.docker_socket, self.root_uid)
        self.socket_facts = socket_facts
        self.docker_client_version = self._text(self._docker(
            ["version", "--format", "{{.Client.Version}}"]))
        self.docker_server_version = self._text(self._docker(
            ["version", "--format", "{{.Server.Version}}"]))
        self.daemon_name = self._info_field("{{.Name}}", "name")
        self.daemon_id = self._info_field("{{.ID}}", "id")
        ostype = self._info_field("{{.OSType}}", "ostype")
        arch = self._info_field("{{.Architecture}}", "architecture")
        self.container_total, self.container_running = self._container_counts()
        self.default_runtime_before = self._info_field("{{.DefaultRuntime}}", "default")
        self.runtime_mapping_before = self._runtime_mapping()
        self.runtime_names_before = sorted(self.runtime_mapping_before)
        facts = self._service_facts()
        obj = self._read_config()
        gates = {
            "docker_client_29_1_3": self.docker_client_version == EXPECTED_DOCKER_VERSION,
            "docker_server_29_1_3": self.docker_server_version == EXPECTED_DOCKER_VERSION,
            "ostype_linux": ostype == INFO_OSTYPE,
            "arch_x86_64": arch == INFO_ARCH,
            "containers_zero": (self.container_total == EXPECTED_CONTAINER_COUNT
                                and self.container_running == EXPECTED_CONTAINER_COUNT),
            "service_active": facts.get("ActiveState") == TRUTHY_ACTIVE,
            "can_reload": facts.get("CanReload") == "yes",
            "exec_reload_hup": self.exec_reload_hup,
        }
        failed = sorted(k for k, v in gates.items() if not v)
        if failed:
            raise InstallError("PRE_EFFECT_GATE_FAILED", ",".join(failed))
        self._note("preflight", "OK", socket=socket_facts,
                   docker_client_version=self.docker_client_version,
                   docker_server_version=self.docker_server_version,
                   daemon_name=self.daemon_name, daemon_id=self.daemon_id,
                   ostype=ostype, arch=arch,
                   container_total=self.container_total,
                   container_running=self.container_running,
                   service={k: facts.get(k) for k in
                            ("ActiveState", "SubState", "LoadState", "CanReload")},
                   exec_reload_hup=self.exec_reload_hup,
                   default_runtime=self.default_runtime_before,
                   runtime_names=self.runtime_names_before,
                   observed_host={"hostname": self.host_id, "uid": self.euid})
        return obj

    def _execute_inner(self, binding_path: str, expected_binding_sha: str) -> None:
        if not (len(expected_binding_sha) == 64
                and all(c in "0123456789abcdef" for c in expected_binding_sha)):
            raise InstallError("BINDING_SHA_ARG_MALFORMED")
        try:
            raw = read_regular_bounded(binding_path, LIMITS["max_config_read_bytes"])
        except InstallError as exc:
            raise InstallError("BINDING_UNREADABLE_" + exc.category) from None
        if sha256_bytes(raw) != expected_binding_sha:
            raise InstallError("BINDING_SHA_MISMATCH")
        binding = Binding(json_loads_strict(raw.decode("utf-8"), "binding"),
                          self.contract)
        self.binding = binding
        self.forbidden.append(binding.effect_commission_token)
        self._note("binding", "OK_VALIDATED", binding=binding.curated())
        # Fresh actual-host binding: the operation is bound durably to the
        # freshly validated normal-router-selected host at action time.  There
        # is no forced stale hostname and no separate dispatch for a hostname
        # change alone.
        system, machine = self.platform_probe()
        if system != "Linux" or machine != "x86_64":
            raise InstallError("PRE_EFFECT_PLATFORM_UNQUALIFIED")
        if self.layout.is_production and self.euid != self.root_uid:
            raise InstallError("PRE_EFFECT_NO_ROOT_EUID")
        self._validate_scratch()
        self._write_intent()
        self._note("intent", "OK_WRITTEN")
        self._prepare_client_config()
        # Read-only action-time preflight BEFORE any privileged mutation.
        try:
            obj = self._preflight()
        except InstallError as exc:
            raise self._gate_failure("PRE_EFFECT", exc)
        # Whole-archive pin and all six member pins, derived from the exact
        # archive bytes, BEFORE any privileged mutation.
        try:
            self._verify_archive_pin()
            member_facts = self._scan_archive(staging_dir=None)
        except InstallError as exc:
            raise self._gate_failure("ARCHIVE", exc)
        self._note("archive", "OK", sha256=self.archive_sha,
                   size_bytes=self.archive_size_seen, members=member_facts)
        # Existing exact alias: reuse only, with bundle + settlement proof.
        if RUNTIME_NAME in obj.get("runtimes", {}):
            entry = obj["runtimes"].get(RUNTIME_NAME)
            if not isinstance(entry, dict):
                raise InstallError("ALIAS_CONFLICT")
            if not self._entry_matches(entry, self._expected_entry()):
                raise InstallError("ALIAS_CONFLICT")
            version_dir = self.layout.p(self.contract.version_dir)
            if not self._verify_bundle_dir(version_dir):
                raise InstallError("BUNDLE_COLLISION_PRESERVED")
            self.bundle_reused = True
            try:
                state = self._settle("main", expect_rf=True)
            except InstallError as exc:
                raise self._gate_failure("REUSE_VERIFY", exc)
            if not state.get("verified"):
                raise InstallError("REUSE_STATE_UNVERIFIED")
            self._note("alias_check", "OK_REUSE_EXISTING",
                       runtime_names=state.get("runtime_names", []),
                       default_runtime=self.default_runtime_before)
            self.status = "OK_REUSE_EXISTING"
            return
        # Finite disk-space admission for archive + staged bundle.
        version_dir = self.layout.p(self.contract.version_dir)
        parent = version_dir.rsplit("/", 1)[0]
        needed = self.contract.archive_size + self.contract.expanded_total \
            + DISK_ADMISSION_MARGIN_BYTES
        # Disk admission is read-only even when the version parents do not yet exist.
        check_ancestors(parent + "/.anchor", self.root_uid, base=self.layout.base)
        disk_parent = parent
        while lstat_meta(disk_parent) is None:
            disk_parent = os.path.dirname(disk_parent)
        try:
            free = self.disk_free_fn(disk_parent)
        except OSError:
            raise InstallError("DISK_ADMISSION_UNAVAILABLE") from None
        if free < needed:
            raise InstallError("DISK_INSUFFICIENT")
        self._note("disk_admission", "OK", free_bytes=free, required_bytes=needed)
        # Candidate + exact additive proof.
        cand, cand_bytes = self._build_candidate(obj)
        cand_sha = sha256_bytes(cand_bytes)
        self._note("candidate", "OK", added_paths=["runtimes." + RUNTIME_NAME],
                   candidate_sha256=cand_sha, candidate_size=len(cand_bytes))
        # Hash-bound private backup (exact preimage bytes, 0600 root) in the
        # admitted scratch, before any host mutation.
        try:
            self._write_backup()
        except InstallError as exc:
            raise self._gate_failure("BACKUP", exc)
        # Stage the complete six-file bundle and publish it with ONE genuine
        # RENAME_NOREPLACE directory publication.
        try:
            stage = self._stage_bundle()
            self._note("bundle_stage", "OK")
            self._publish_bundle(stage)
            if not self.bundle_reused:
                self._note("bundle_publish", "OK_PUBLISHED",
                           version_dir=version_dir)
        except InstallError as exc:
            raise self._gate_failure("BUNDLE", exc)
        # Qualified dockerd validation of the candidate (never a daemon start).
        try:
            self._validate_with_dockerd(cand_bytes)
        except InstallError as exc:
            raise self._gate_failure("VALIDATE", exc)
        self._note("validate", "OK")
        # Commit with honest compare-before-commit; the irreversible boundary
        # is recorded immediately after the rename.
        try:
            self._commit(cand_bytes, cand_sha)
        except InstallError as exc:
            raise self._gate_failure("COMMIT", exc)
        self._note("commit", "OK", postimage_sha256=self.committed_sha,
                   commit_uncertain=self.commit_uncertain,
                   race_note="compare-before-commit is best effort; a race window "
                             "remains and there is no atomic compare-and-swap")
        # Qualified reload ONCE, then bounded read-only settlement.
        try:
            self._reload("main")
        except InstallError as exc:
            raise self._gate_failure("AT_RELOAD", exc)
        state = self._settle("main", expect_rf=True)
        if state.get("verified"):
            self._note("verify", "OK", settlement=state,
                       runtime_names=state.get("runtime_names", []),
                       default_runtime=self.default_runtime_before)
            self.status = "OK_INSTALLED"
            return
        if state.get("confirmed") and not state.get("verified"):
            # proven ordinary local pre-registration failure with settled
            # effect state: guarded rollback, once
            result = self._rollback()
            self._note("rollback", result["status"], rollback=result)
            self.status = result["status"]
            return
        # Deadline without confirmation: UNKNOWN -- freezes even rollback and
        # all later phases; no second reload, no rollback, no removal.
        self.freeze()
        self.status = "UNKNOWN_RELOAD_SETTLEMENT"
        self._note("settlement", "UNKNOWN_DEADLINE_UNCONFIRMED", settlement=state)

    def _exit_for(self, status: str) -> int:
        if status.startswith("OK_"):
            return EXIT_OK
        if status.startswith(("REFUSED_", "PERMISSION_REFUSED", "UNKNOWN_",
                              "FROZEN_", "UNCERTAIN_", "STOP_")):
            return EXIT_UNCERTAIN
        if status.startswith("INTERNAL_"):
            return EXIT_INTERNAL
        return EXIT_BLOCKED

    def execute(self, binding_path: str,
                expected_binding_sha: str) -> Tuple[int, Dict[str, Any]]:
        self.status = "INTERNAL_NO_RESULT"
        self.unknowns = []
        exit_code = EXIT_INTERNAL
        try:
            self._execute_inner(binding_path, expected_binding_sha)
            exit_code = self._exit_for(self.status)
        except InstallError as exc:
            if exc.category.startswith("PERMISSION_REFUSED"):
                self.freeze()
            if self.status == "INTERNAL_NO_RESULT":
                self.status = ("STOP_BUDGET_EXCEEDED" if exc.category == "BUDGET_EXCEEDED"
                               else exc.category or "INTERNAL_UNCLASSIFIED_INSTALL_ERROR")
            exit_code = self._exit_for(self.status)
        except PermissionError:
            # A real permission denial from the OS freezes every later
            # privileged action, including cleanup.
            self.status = "REFUSED_PERMISSION_DENIED"
            self.freeze()
            exit_code = EXIT_UNCERTAIN
        except OSError:
            self.status = "INTERNAL_OS_FAULT"
            exit_code = EXIT_INTERNAL
        except BaseException as exc:  # BaseException-safe: record truthfully,
            # never replay a denied or interrupted mutation
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                self.status = "INTERNAL_INTERRUPTED_" + type(exc).__name__
            else:
                self.status = "INTERNAL_FAULT_" + type(exc).__name__
            self.freeze()
            exit_code = EXIT_INTERNAL
        receipt = self._final_receipt()
        receipt_write_failed = False
        if self._intent_written and self.binding is not None:
            try:
                name = "final_%s_%d.json" % (self.binding.operation_id, time.time_ns())
                self._write_receipt_file(
                    self.binding.operation_scratch_dir + "/" + name, receipt)
            except (OSError, ValueError, InstallError):
                receipt_write_failed = True
        receipt["receipt_write_failed"] = receipt_write_failed
        if receipt_write_failed:
            # A durable receipt write failure cannot keep a success verdict.
            if self.status.startswith("OK_"):
                receipt["pre_downgrade_status"] = self.status
                self.unknowns.append("durable final receipt write failed; success "
                                     "downgraded to uncertain")
                self.status = "UNCERTAIN_RECEIPT_WRITE_FAILED"
                receipt["status"] = self.status
            exit_code = self._exit_for(self.status)
        return exit_code, receipt

    def _final_receipt(self) -> Dict[str, Any]:
        commands = []
        for call in getattr(self.runner, "calls", []):
            commands.append({
                "binary": call.get("binary"), "argv_tail": call.get("argv_tail"),
                "role": call.get("role"), "rc": call.get("rc"),
                "timed_out": call.get("timed_out"), "truncated": call.get("truncated"),
                "out_len": call.get("out_len"), "err_len": call.get("err_len"),
                "out_sha256": call.get("out_sha256"), "err_sha256": call.get("err_sha256"),
                "refused": call.get("refused"), "category": call.get("category"),
            })
        return {
            "schema": "mastermind.rf_runsc_install_receipt.v2",
            "root_id": ROOT_ID,
            "operation_id": self.binding.operation_id if self.binding else None,
            "status": self.status,
            "exit_code": self._exit_for(self.status),
            "host": {"hostname": self.host_id, "uid": self.euid,
                     "platform": list(self.platform_probe())},
            "docker_endpoint": DOCKER_SOCKET_ARG,
            "docker": {"client_version": self.docker_client_version,
                       "server_version": self.docker_server_version,
                       "expected_version": EXPECTED_DOCKER_VERSION,
                       "daemon_name": self.daemon_name, "daemon_id": self.daemon_id,
                       "container_total": self.container_total,
                       "container_running": self.container_running,
                       "default_runtime": self.default_runtime_before,
                       "runtime_names_before": self.runtime_names_before},
            "service": {"exec_reload_uses_hup": self.exec_reload_hup,
                        "reload_mode": "docker.service reload only; no restart, "
                                       "no PID kill, no default-runtime or "
                                       "live-restore change"},
            "binding": self.binding.curated() if self.binding else None,
            "archive": {"sha256": self.archive_sha,
                        "size_bytes": self.archive_size_seen,
                        "expected_sha256": self.contract.archive_sha256,
                        "expected_size_bytes": self.contract.archive_size},
            "bundle": {
                "version_dir": self.layout.p(self.contract.version_dir),
                "runtime_entry": self._expected_entry(),
                "member_sha256": dict(self.binding.member_sha256)
                if self.binding else None,
                "member_sizes": dict(self.contract.member_sizes),
                "created": self.bundle_created, "reused": self.bundle_reused,
                "shim_installed": False,
            },
            "bundle_staging": {
                "path": self.staging_path,
                "owned_created": self.staging_owned_created,
                "published_by_rename": self.staging_published,
                "cleanup_obligation": self.staging_owned_created and not self.staging_published,
                "observation": "operation history only; no new read or cleanup after refusal",
            },
            "config": {
                "path": DAEMON_JSON_PATH,
                "preimage_sha256": self.preimage_sha,
                "postimage_sha256": self.committed_sha,
                "preimage_meta": self.preimage_meta,
                "postimage_meta": self.committed_meta,
                "committed": self.committed,
                "commit_uncertain": self.commit_uncertain,
                "additive_diff_asserted": self.committed,
                "alias_added": RUNTIME_NAME,
            },
            "backup": {
                "present": self.backup_path is not None,
                "sha256": self.backup_sha,
                "mode": BACKUP_EXPECTED_MODE,
                "body_exported": False,
            },
            "settlement": self.settlement,
            "rollback": dict(self.rollback_result),
            "commands": commands,
            "limits": dict(LIMITS),
            "budget": self.budget.snapshot(),
            "unknowns": self.unknowns,
            "notes": self.notes,
            "trust_boundary": "Caller-supplied JSON is data, not authentication or "
                              "root authority. Receipts carry curated facts and "
                              "hashes only; config bodies, sudoers, credentials, "
                              "stderr text and unit private paths are never emitted.",
        }

# --------------------------------------------------------------------------- #
# Default: no-effects proposal.  Never reads host state, never spawns.
# --------------------------------------------------------------------------- #

OPEN_ACTION_TIME_GATES = [
    "explicit root effect commission naming this operation is required before "
    "--execute; caller-supplied JSON, hashes and tokens are not root authority",
    "binding must pin the exact archive SHA256/size and all six member SHA256 "
    "pins derived from that exact archive; runsc pin must equal the contract pin",
    "the ONE archive must already exist locally as a regular file prepared by "
    "the separately approved same-operation acquisition (cap 240 s there); this "
    "helper never downloads",
    "action-time preflight: actual Linux x86_64 host, invoking UID recorded, "
    "root euid for effects, explicit unix:///var/run/docker.sock on every Docker "
    "call, socket owner/type verified, Docker client+server 29.1.3, daemon "
    "Name/ID recorded, zero active AND total containers, docker.service active "
    "with CanReload=yes and a qualified HUP ExecReload method",
    "current safe root-owned 0644 /etc/docker/daemon.json preimage is acquired "
    "fresh at action time and bound privately in the same commission; no stale "
    "external hostname or preimage prerequisite exists",
    "execution requires euid 0 on the production host, an already admitted "
    "root-owned 0700 scratch directory, and renameat2 RENAME_NOREPLACE support; "
    "no host forcing, no sudo probing, and any real permission refusal freezes "
    "all following actions including cleanup",
]


def build_plan() -> Dict[str, Any]:
    return {
        "schema": "mastermind.rf_runsc_install_proposal.v2",
        "status": "NO_EFFECTS_PROPOSAL",
        "root_id": ROOT_ID,
        "named_consumer": "Research Factory isolated feature-primitive runner",
        "runtime_name": RUNTIME_NAME,
        "runtime_entry": EXPECTED_RUNTIME_ENTRY,
        "binary_version_path": RUNSC_BINARY_PATH,
        "version_directory": VERSION_ROOT + "/" + VERSION_TAG,
        "archive": {"sha256": ARCHIVE_SHA256, "size_bytes": ARCHIVE_SIZE_BYTES,
                    "max_bytes": ARCHIVE_MAX_BYTES},
        "required_members": {"sizes": dict(REQUIRED_MEMBERS),
                             "expanded_total_bytes": EXPANDED_BUNDLE_BYTES},
        "config_path": DAEMON_JSON_PATH,
        "binding_schema": BINDING_SCHEMA,
        "required_binding_fields": ["schema", "root_id", "operation_id",
                                    "effect_commission_token", "archive_path",
                                    "member_sha256", "operation_scratch_dir",
                                    "binary_version_path"],
        "limits": dict(LIMITS),
        "rollback": "guarded, same owner/carrier; one restore and one qualified "
                    "reload; refusal or unconfirmed settlement freezes even "
                    "rollback; only the newly created fully identified bundle is "
                    "removed after runtime-entry absence, inventory removal, "
                    "default preservation and zero container census",
        "no_effects_statement": "This invocation performed no reads, no "
                                "subprocesses and no mutations. Acquisition, "
                                "installation, registration, reload, selection "
                                "and acceptance remain separate root-owned claims.",
        "open_action_time_gates": OPEN_ACTION_TIME_GATES,
        "trust_boundary": "Caller-supplied JSON is not authentication and not root "
                          "authority. An admitted future owner invokes --execute "
                          "only after an explicit root effect commission.",
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args == ["--plan"]:
        print(json.dumps(build_plan(), indent=2))
        return EXIT_OK
    if args[0] != "--execute":
        print(json.dumps({"schema": "mastermind.rf_runsc_install_proposal.v2",
                          "status": "USAGE_ERROR"}, indent=2))
        return EXIT_USAGE
    binding_path: Optional[str] = None
    expected_sha: Optional[str] = None
    i = 1
    while i < len(args):
        if args[i] == "--binding" and i + 1 < len(args) and binding_path is None:
            binding_path = args[i + 1]
            i += 2
        elif args[i] == "--expect-binding-sha256" and i + 1 < len(args) \
                and expected_sha is None:
            expected_sha = args[i + 1]
            i += 2
        else:
            print(json.dumps({"schema": "mastermind.rf_runsc_install_proposal.v2",
                              "status": "USAGE_ERROR"}, indent=2))
            return EXIT_USAGE
    if not binding_path or not expected_sha:
        print(json.dumps({"schema": "mastermind.rf_runsc_install_proposal.v2",
                          "status": "USAGE_ERROR"}, indent=2))
        return EXIT_USAGE
    engine = InstallEngine(Layout.production(), BoundedRunner(Budget()))
    code, receipt = engine.execute(binding_path, expected_sha)
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
