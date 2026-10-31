"""Private native-APT stage/hook implementation; no automatic activation.

Only the explicit pack adapter may stage these bound bytes in a root-owned
job directory. Native hooks consume configuration privately; it is never
printed or persisted. No retry, transport override, shared cache or service.
"""
from __future__ import annotations

import hashlib
import fcntl
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import pwd
import selectors
import shutil
import socket
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ci_apt_cold_acquisition import AcquisitionRefused, Archive
from scripts.ci_apt_native_plan import complete_archive_inventory, DIRECT_PACKAGES
from scripts.ci_apt_native_plan import no_download_install_argv, resolver_argv, completion_download_argv, trusted_package_indexes_argv, require_trusted_package_indexes
from scripts.ci_apt_cold_acquisition import download_argv
from scripts.ci_apt_transaction_contract import normalize_transaction, assert_same_transaction, parse_preinstall_v3

LIMIT = 1024 * 1024
RESULT_PREFIX = b"CI_APT_NATIVE_RESULT="

# Reported native text categories only: never a cause, authority, retry grant
# or semantic/settlement classifier. Raw output and matched text stay private.
REPORTED_ERROR_CODES = ("PERMISSION", "SELECTION", "AUTH", "MIRROR_LIST", "HASH", "FETCH", "METHOD", "UNCLASSIFIED")


def sanitize_reported_errors(value) -> list[str]:
    if (type(value) is not list or not 1 <= len(value) <= len(REPORTED_ERROR_CODES) or
            any(type(code) is not str or code not in REPORTED_ERROR_CODES for code in value) or
            len(set(value)) != len(value) or ("UNCLASSIFIED" in value and len(value) != 1)):
        return ["UNCLASSIFIED"]
    return [code for code in REPORTED_ERROR_CODES if code in value]


def reported_download_errors(output) -> list[str]:
    """Bounded private inspection; return ONLY fixed enum values, never text."""
    if type(output) is not bytes or len(output) > LIMIT or b"\x00" in output:
        return ["UNCLASSIFIED"]
    try:
        output.decode("utf-8", errors="strict")
    except UnicodeError:
        return ["UNCLASSIFIED"]
    text = output.lower()
    patterns = (
        ("PERMISSION", (b"permission denied",)),
        ("SELECTION", (b"unable to locate package", b"has no installation candidate", b"can't find a source to download version")),
        ("AUTH", (b"could not be authenticated", b"cannot be authenticated", b"unauthenticated packages")),
        ("MIRROR_LIST", (b"couldn't determine mirror list to query for",)),
        ("HASH", (b"hash sum mismatch", b"size mismatch")),
        ("FETCH", (b"failed to fetch",)),
        ("METHOD", (b"method driver", b"method has died unexpectedly")),
    )
    found = [code for code, phrases in patterns if any(phrase in text for phrase in phrases)]
    return sanitize_reported_errors(found)



class NativeUnknown(RuntimeError):
    def __init__(self, reason: str, child_pid: int | None = None, outcome: str = "failed"):
        super().__init__(reason)
        self.child_pid = child_pid
        self.outcome = outcome


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def read_json(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise AcquisitionRefused("PRIVATE_INPUT_UNQUALIFIED")
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise AcquisitionRefused("PRIVATE_INPUT_LIMIT")
    return json.loads(raw)


def retain_once(path: Path, value) -> None:
    data = canonical(value)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if canonical(read_json(path)) != data:
            raise AcquisitionRefused("PRIVATE_RESULT_CONFLICT") from None
        return
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def observe_command(argv, *, deadline: float, cwd: Path | None = None,
                    command_env: dict | None = None) -> tuple[int, bytes]:
    """Own one native child: positive exit AND pipe EOF, or sticky unknown.

    Nothing here kills a child or infers descendant death from root exit.
    Any postlaunch observation failure/overflow/deadline preserves unknown.
    """
    if not math.isfinite(deadline) or time.monotonic() >= deadline:
        raise AcquisitionRefused("TOTAL_DEADLINE_BEFORE_LAUNCH")
    env = dict(os.environ if command_env is None else command_env, LC_ALL="C")
    env.pop("DPKG_FRONTEND_LOCKED", None)
    process = None
    try:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        output = bytearray()
        eof = False
        with selectors.DefaultSelector() as events:
            events.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise NativeUnknown("TOTAL_DEADLINE", process.pid, "timed_out")
                for key, _ in events.select(min(remaining, 0.05)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        eof = True
                        events.unregister(key.fileobj)
                    else:
                        output.extend(chunk)
                        if len(output) > LIMIT:
                            raise NativeUnknown("NATIVE_OUTPUT_LIMIT")
                code = process.poll()
                if code is not None and eof:
                    process.wait(timeout=0)
                    process.stdout.close()
                    return code, bytes(output)
    except Exception as error:
        if process is not None:
            raise NativeUnknown("NATIVE_OBSERVATION_UNKNOWN", process.pid,
                                error.outcome if isinstance(error, NativeUnknown) else "failed") from error
        raise


def root_directory() -> Path:
    root = Path(__file__).resolve().parent.parent
    if os.geteuid() != 0 or root.parent != Path("/tmp") or not root.name.startswith("ci-apt-"):
        raise AcquisitionRefused("PRIVATE_ROOT_UNQUALIFIED")
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise AcquisitionRefused("PRIVATE_ROOT_UNQUALIFIED")
    return root


def archives_at(root: Path) -> tuple[Archive, ...]:
    return tuple(Archive(**row) for row in read_json(root / "archives.json"))


def verify_file(path: Path, expected: Archive, *, immutable: bool) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected.size:
            raise AcquisitionRefused("ARCHIVE_FILE_UNQUALIFIED")
        if immutable and (before.st_uid != 0 or before.st_mode & 0o022):
            raise AcquisitionRefused("ARCHIVE_FILE_MUTABLE")
        digest = hashlib.sha256()
        remaining = expected.size
        while remaining:
            chunk = stream.read(min(65536, remaining))
            if not chunk:
                raise AcquisitionRefused("ARCHIVE_FILE_TRUNCATED")
            digest.update(chunk)
            remaining -= len(chunk)
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ) or digest.hexdigest() != expected.sha256:
        raise AcquisitionRefused("ARCHIVE_BYTES_CHANGED")
    current = path.lstat()
    if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
        raise AcquisitionRefused("ARCHIVE_PATH_REPLACED")


def adopt_archive(source: Path, destination: Path, expected: Archive) -> None:
    """Copy through one nofollow descriptor; publish readable bytes only after verification."""
    source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(source_fd, "rb") as data:
        before = os.fstat(data.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected.size:
            raise AcquisitionRefused("ARCHIVE_FILE_UNQUALIFIED")
        target_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(target_fd, "wb") as target:
            remaining, digest = expected.size, hashlib.sha256()
            while remaining:
                chunk = data.read(min(65536, remaining))
                if not chunk:
                    raise AcquisitionRefused("ARCHIVE_FILE_TRUNCATED")
                target.write(chunk); digest.update(chunk); remaining -= len(chunk)
            after = os.fstat(data.fileno())
            current = source.lstat()
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
            ) or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino) or digest.hexdigest() != expected.sha256:
                raise AcquisitionRefused("ARCHIVE_BYTES_CHANGED")
            target.flush(); os.fsync(target.fileno())
            os.fchmod(target.fileno(), 0o644)


def json_hook(root: Path, connection) -> None:
    def message():
        line = connection.readline(LIMIT + 1)
        if not line or len(line) > LIMIT or connection.readline(2) != b"\n":
            raise AcquisitionRefused("JSON_HOOK_FRAME")
        return line

    hello = json.loads(message())
    if hello.get("method") != "org.debian.apt.hooks.hello" or "0.2" not in hello.get("params", {}).get("versions", []):
        raise AcquisitionRefused("JSON_HOOK_VERSION")
    connection.write(b'{"jsonrpc":"2.0","id":0,"result":{"version":"0.2"}}\n\n')
    connection.flush()
    raw = message()
    body = json.loads(raw)
    method = body.get("method")
    if method in {"org.debian.apt.hooks.install.pre-prompt", "org.debian.apt.hooks.install.package-list"}:
        normalized = normalize_transaction(raw)
        if normalized["search-terms"] != list(DIRECT_PACKAGES):
            raise AcquisitionRefused("DIRECT_DEPENDENCIES_CHANGED")
        if (root / "install-attempt").exists():
            assert_same_transaction(read_json(root / "frozen-native.json"), normalized)
            retain_once(root / "actual-native.json", normalized)
        elif (root / "completion-attempt").exists():
            assert_same_transaction(read_json(root / "frozen-native.json"), normalized)
            retain_once(root / "completion-native.json", normalized)
        else:
            retain_once(root / "frozen-native.json", normalized)
    elif method not in {"org.debian.apt.hooks.install.statistics", "org.debian.apt.hooks.install.post", "org.debian.apt.hooks.install.fail"}:
        raise AcquisitionRefused("JSON_HOOK_METHOD")
    bye = json.loads(message())
    if bye.get("method") != "org.debian.apt.hooks.bye":
        raise AcquisitionRefused("JSON_HOOK_FRAME")


def validate_actions(expected: dict, actions: tuple[dict, ...], archives: tuple[Archive, ...], cache: Path, *, verify_archives: bool = True) -> None:
    """Exact package transitions; native configure ordering remains native."""
    rows = expected["packages"]
    seen_install, seen_remove = set(), set()
    for action in actions:
        name, old, new = action["name"], action["oldversion"], action["newversion"]
        candidates = [row for row in rows if row["name"] == name and
                      row["versions"].get("current", {}).get("version", "-") == old and
                      row["versions"].get("install", {}).get("version", "-") == new and
                      row["versions"].get("current", {}).get("architecture", "-") == action["oldarch"] and
                      row["versions"].get("install", {}).get("architecture", "-") == action["newarch"]]
        if len(candidates) != 1:
            raise AcquisitionRefused("ACTUAL_PACKAGE_CHANGED")
        row = candidates[0]
        identity = name, row["architecture"]
        operation = action["action"]
        if operation == "**REMOVE**":
            if row["mode"] not in {"deinstall", "purge"} or identity in seen_remove:
                raise AcquisitionRefused("ACTUAL_PACKAGE_CHANGED")
            seen_remove.add(identity)
        elif operation == "**CONFIGURE**":
            if row["mode"] in {"deinstall", "purge"}:
                raise AcquisitionRefused("ACTUAL_PACKAGE_CHANGED")
        else:
            matches = [a for a in archives if a.package == name and a.package_architecture == row["architecture"]]
            if len(matches) != 1 or identity in seen_install:
                raise AcquisitionRefused("ACTUAL_ARCHIVE_CHANGED")
            archive = matches[0]
            if operation != str(cache / archive.filename):
                raise AcquisitionRefused("ACTUAL_ARCHIVE_CHANGED")
            if verify_archives:
                verify_file(cache / archive.filename, archive, immutable=True)
            seen_install.add(identity)
    if seen_install != {(a.package, a.package_architecture) for a in archives} or seen_remove != {
        (r["name"], r["architecture"]) for r in rows if r["mode"] in {"deinstall", "purge"}
    }:
        raise AcquisitionRefused("ACTUAL_TRANSACTION_INCOMPLETE")


def preinstall_hook(root: Path, raw: bytes) -> None:
    if os.environ.get("APT_HOOK_INFO_FD") != "0" or os.environ.get("DPKG_FRONTEND_LOCKED") != "true":
        raise AcquisitionRefused("NATIVE_LOCK_CONTEXT_ABSENT")
    actions = parse_preinstall_v3(raw)
    # Configuration stays private. Check effective mandatory controls, never
    # return/dump unknown configuration values or include exception bodies.
    configuration = raw.split(b"\n\n", 1)[0].splitlines()[1:]
    controls = {"apt::get::download": False, "apt::get::fix-missing": False,
                "apt::get::allowunauthenticated": False, "debug::nolocking": False,
                "acquire::allowinsecurerepositories": False,
                "acquire::allowdowngradetoinsecurerepositories": False}
    seen = set()
    for line in configuration:
        key, separator, value = line.partition(b"=")
        name = key.decode("ascii", errors="strict").lower()
        if name in controls:
            if not separator or name in seen or value.lower() not in {b"false", b"0", b"no"}:
                raise AcquisitionRefused("NATIVE_CONTROL_UNQUALIFIED")
            seen.add(name)
    if seen != controls.keys():
        raise AcquisitionRefused("NATIVE_CONTROL_ABSENT")
    expected = read_json(root / "frozen-native.json")
    assert_same_transaction(expected, read_json(root / "actual-native.json"))
    validate_actions(expected, actions, archives_at(root), root / "install-cache")
    retain_once(root / "preinstall-actions.json", list(actions))


def apt_directory(path: Path) -> None:
    path.mkdir(mode=0o755)
    partial = path / "partial"
    partial.mkdir(mode=0o700)
    os.chown(partial, pwd.getpwnam("_apt").pw_uid, pwd.getpwnam("_apt").pw_gid)



def sync_directory(root: Path) -> None:
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def acquisition_admission(root: Path, mode: str):
    """Job-local fence only; never hostwide or a restart/retry authority."""
    if mode not in {"download", "complete", "install"}:
        yield
        return
    fd = os.open(root / "acquisition.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise AcquisitionRefused("ACQUISITION_LOCK_UNQUALIFIED")
        fcntl.flock(fd, (fcntl.LOCK_SH if mode == "download" else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        # Installation validates completed members and creates install-attempt
        # inside this same exclusive interval; a verified completion may enter.
        if mode != "install" and (root / "completion-attempt").exists():
            raise AcquisitionRefused("COMPLETION_ALREADY_ATTEMPTED")
        yield
    finally:
        os.close(fd)


def completion_inputs(root: Path, archives: tuple[Archive, ...]) -> tuple[int, ...]:
    completed, failed = [], []
    for index, archive in enumerate(archives):
        directory = root / f"download-{index}"
        receipt = root / f"download-result-{index}.json"
        if not directory.exists() and not receipt.exists():
            continue  # never launched: the whole native transaction may acquire it
        row = read_json(receipt)  # missing/partial/unknown cannot become a new operation
        if row.get("mode") != "download" or type(row.get("index")) is not int or row["index"] != index or row.get("settlement") != "settled":
            raise AcquisitionRefused("ORIGINAL_DOWNLOAD_UNPROVEN")
        if row.get("outcome") == "passed" and type(row.get("returncode")) is int and row["returncode"] == 0:
            verify_file(directory / archive.filename, archive, immutable=False)
            completed.append(index)
        elif (row.get("outcome") == "failed" and type(row.get("returncode")) is int and row["returncode"] == 100 and row.get("reported_errors") == ["FETCH"]):
            failed.append(index)
        else:
            raise AcquisitionRefused("ORIGINAL_DOWNLOAD_INELIGIBLE")
    if not failed:
        raise AcquisitionRefused("NO_SETTLED_NATIVE_DOWNLOAD_FAILURE")
    return tuple(completed)


def complete_native_transaction(root: Path, archives: tuple[Archive, ...], deadline: float) -> dict:
    if (root / "install-attempt").exists():
        raise AcquisitionRefused("INSTALL_ALREADY_ATTEMPTED")
    completed = completion_inputs(root, archives)
    # Atomic one-shot marker precedes every native qualification/acquisition
    # call. It survives failed replies and is never removed or reset here.
    (root / "completion-attempt").mkdir()
    sync_directory(root)
    code, output = observe_command(trusted_package_indexes_argv(), deadline=deadline)
    if code != 0:
        raise NativeUnknown("NATIVE_INDEX_TRUST_UNPROVEN")
    require_trusted_package_indexes(output)
    cache = root / "completion-cache"
    apt_directory(cache)
    for index in completed:
        adopt_archive(root / f"download-{index}" / archives[index].filename, cache / archives[index].filename, archives[index])
    code, output = observe_command(completion_download_argv(hook=str(root / "txn-hook"), cache=str(cache)), deadline=deadline)
    # Download-only excludes dpkg/manual marking, but inherited hooks still
    # run. Nonzero/response loss is not proof that every hook had no effect.
    if code != 0:
        raise NativeUnknown("NATIVE_COMPLETION_INCOMPLETE")
    if b"unsandboxed" in output.lower():
        raise NativeUnknown("NATIVE_SANDBOX_UNPROVEN")
    assert_same_transaction(read_json(root / "frozen-native.json"), read_json(root / "completion-native.json"))
    verified = root / "completion-verified-cache"
    verified.mkdir(mode=0o755)
    for archive in archives:
        # Native sandbox output may be _apt-owned. Copy exact stable bytes
        # into fresh root-owned immutable members before trusting them.
        adopt_archive(cache / archive.filename, verified / archive.filename, archive)
        verify_file(verified / archive.filename, archive, immutable=True)
    retain_once(root / "completion-verified.json", [a.__dict__ for a in archives])
    return {"outcome": "passed", "settlement": "settled", "returncode": 0}


def run_stage(root: Path, mode: str, index: int | None, deadline: float) -> dict:
    if not math.isfinite(deadline) or time.monotonic() >= deadline:
        raise AcquisitionRefused("TOTAL_DEADLINE_BEFORE_LAUNCH")
    if mode == "update":
        (root / "update-attempt").mkdir()
        code, _ = observe_command(("/usr/bin/apt-get", "-o", "Acquire::AllowInsecureRepositories=false", "update"), deadline=deadline)
    elif mode == "resolve":
        (root / "resolve-attempt").mkdir()
        apt_directory(root / "planning-cache")
        code, output = observe_command(resolver_argv(hook=str(root / "txn-hook"), cache=str(root / "planning-cache")), deadline=deadline)
        if code == 0:
            frozen = read_json(root / "frozen-native.json")
            archives = complete_archive_inventory(frozen, output)
            retain_once(root / "archives.json", [a.__dict__ for a in archives])
            return {"outcome": "passed", "settlement": "settled", "archives": [a.__dict__ for a in archives],
                    "transaction_sha256": hashlib.sha256(canonical(frozen)).hexdigest()}
    elif mode == "download":
        archives = archives_at(root)
        if type(index) is not int or not 0 <= index < len(archives):
            raise AcquisitionRefused("ARCHIVE_INDEX")
        directory = root / f"download-{index}"
        directory.mkdir(mode=0o700)
        account = pwd.getpwnam("_apt")
        os.chown(directory, account.pw_uid, account.pw_gid)
        code, output = observe_command((*download_argv(archives[index]), "-o", "APT::Sandbox::User=_apt"), deadline=deadline, cwd=directory)
        if code == 0:
            if b"unsandboxed" in output.lower():
                raise AcquisitionRefused("NATIVE_SANDBOX_UNPROVEN")
            verify_file(directory / archives[index].filename, archives[index], immutable=False)
        else:
            return {"outcome": "failed", "settlement": "settled", "returncode": code,
                    "reported_errors": reported_download_errors(output)}
    elif mode == "complete":
        return complete_native_transaction(root, archives_at(root), deadline)
    elif mode == "install":
        (root / "install-attempt").mkdir()
        apt_directory(root / "install-cache")
        archives = archives_at(root)
        completion = (root / "completion-attempt").exists()
        if completion and read_json(root / "completion-verified.json") != [a.__dict__ for a in archives]:
            raise AcquisitionRefused("COMPLETION_ARCHIVES_UNPROVEN")
        for i, archive in enumerate(archives):
            source = (root / "completion-verified-cache" if completion else root / f"download-{i}") / archive.filename
            destination = root / "install-cache" / archive.filename
            adopt_archive(source, destination, archive)
            verify_file(destination, archive, immutable=True)
        code, _ = observe_command(no_download_install_argv(hook=str(root / "txn-hook"), cache=str(root / "install-cache")), deadline=deadline)
        if code != 0:
            raise NativeUnknown("NATIVE_INSTALL_INCOMPLETE")
        frozen = read_json(root / "frozen-native.json")
        assert_same_transaction(frozen, read_json(root / "actual-native.json"))
        if frozen["packages"]:
            # The lock-held pre-dpkg hook already verified immutable bytes.
            # Native APT may legitimately remove downloaded archives after a
            # successful install under inherited Keep-Downloaded-Packages.
            # Preserve that policy: recheck retained actual actions and native
            # exit, rather than requiring deleted cache bytes after the effect.
            validate_actions(frozen, tuple(read_json(root / "preinstall-actions.json")), archives, root / "install-cache", verify_archives=False)
    elif mode == "cleanup-downloads":
        if not shutil.rmtree.avoids_symlink_attacks:
            raise AcquisitionRefused("CLEANUP_UNQUALIFIED")
        for index, _ in enumerate(archives_at(root)):
            shutil.rmtree(root / f"download-{index}")
        shutil.rmtree(root / "planning-cache")
        code = 0
    elif mode == "cleanup":
        if not shutil.rmtree.avoids_symlink_attacks:
            raise AcquisitionRefused("CLEANUP_UNQUALIFIED")
        shutil.rmtree(root)
        code = 0
    else:
        raise AcquisitionRefused("NATIVE_STAGE_UNQUALIFIED")
    return {"outcome": "passed" if code == 0 else "failed", "settlement": "settled", "returncode": code}


def main() -> int:
    try:
        root = root_directory()
        mode = sys.argv[1]
        if mode == "json":
            fd = int(os.environ["APT_HOOK_SOCKET"])
            with socket.socket(fileno=os.dup(fd)) as channel, channel.makefile("rwb", buffering=0) as connection:
                json_hook(root, connection)
            return 0
        if mode == "preinstall":
            preinstall_hook(root, sys.stdin.buffer.read(LIMIT + 1))
            return 0
        deadline = float(sys.argv[2])
        with acquisition_admission(root, mode):
            result = run_stage(root, mode, int(sys.argv[3]) if len(sys.argv) > 3 else None, deadline)
    except NativeUnknown as error:
        result = {"outcome": error.outcome, "settlement": "unknown", "reason": "NATIVE_EFFECT_UNPROVEN", "child_pid": error.child_pid}
    except Exception:
        # Do not echo native config, URIs, credentials or exception text.
        if len(sys.argv) > 1 and sys.argv[1] in {"json", "preinstall"}:
            return 1
        result = {"outcome": "failed", "settlement": "unknown", "reason": "NATIVE_STAGE_UNPROVEN"}
    result["mode"] = sys.argv[1] if len(sys.argv) > 1 else None
    if len(sys.argv) > 3:
        result["index"] = int(sys.argv[3])
    if result["mode"] in {"download", "complete"}:
        target = root / f"download-result-{result['index']}.json" if result["mode"] == "download" else root / "completion-result.json"
        retain_once(target, result)
        sync_directory(root)
    sys.stdout.buffer.write(RESULT_PREFIX + canonical(result) + b"\n")
    return 73 if result["settlement"] == "unknown" else (0 if result["outcome"] == "passed" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
