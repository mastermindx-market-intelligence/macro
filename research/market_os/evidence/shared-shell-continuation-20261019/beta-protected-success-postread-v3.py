"""Attended, read-only beta acceptance postread; importing this file has no effects.

Run only with the actual invocation binding. This is an evidence collector and
validator, not an installer, repair tool, source audit, or bootstrap authorization.
"""
from pathlib import Path
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request

A = "e45bde2cac07ac3b29285ff70c40d68900fad62c"
OWNER_SHA = "c6759cc653e0f19102a015ec52842795bde24eb85766d2e73f3024b4eefe409d"
SOURCE_SHA = "9aac8ec8c132eecf4d2664d8f1e18e8a6bffce5f6d7176e4021b15d6d953cfa4"
POLICY_SHA = "9b6c95d2f3134f37640312106fcf10dd2be5a1d4c01002e959ac5cb71614fae9"
POLICY_ID = "99f76cb211b086d1f83bb86c10747e2711a4c318fa4bd5dab1b94e84d46fe1d6"
B = Path("/opt/terminal/beta")
APP = B / "terminal"
S = Path("/var/lib/mastermind-terminal-beta/source-provisioned")
PREFLIGHT = S.parent / "release-preflight"
REPO = Path("/opt/terminal/.gitsrc-beta")
POLICY = REPO / "ops/terminal_source_audit.beta.json"
LOCK = Path("/opt/terminal/.terminal-build-resource.lock")
STATUS_URL = "http://127.0.0.1:3001/api/shared-shell/status"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
PROPS = (
    "ActiveState,SubState,UnitFileState,MainPID,ExecMainStartTimestampMonotonic,"
    "FragmentPath,DropInPaths,User,Group,SupplementaryGroups,WorkingDirectory,"
    "ProtectSystem,ProtectHome,PrivateTmp,PrivateDevices,NoNewPrivileges,"
    "CapabilityBoundingSet,AmbientCapabilities,ReadWritePaths,ReadOnlyPaths,"
    "BindReadOnlyPaths,InaccessiblePaths,RestrictAddressFamilies,"
    "RestrictNamespaces,SystemCallFilter,UMask"
)
STABLE_PROPS = ("MainPID", "ExecMainStartTimestampMonotonic",
                "ActiveState", "SubState", "UnitFileState")
REQUIRED = (
    "binding_valid", "services_read_successful", "production_service_identity",
    "beta_active_enabled", "runtime_pointer_present", "runtime_record_valid",
    "source_record_valid", "source_provenance_hash", "source_provenance_binding",
    "live_build_binding", "preflight_valid", "attempt_records_valid",
    "committing_attempt_present", "policy_preserved", "beta_HEAD_A",
    "production_owner_preserved", "Caddy_preserved", "production_build_identity",
    "protected_owner_artifact_bytes", "caller_observed_installer_exit_zero",
    "caller_observed_transaction_commit", "pending_absent", "owned_hold_absent",
    "owned_stage_absent", "no_beta_stage_remains", "observed_archives_absent",
    "archive_parent_empty", "generation_marker_scratch_absent",
    "status_contract", "status_cache_private_no_store",
    "status_robots_noindex_nofollow", "beta_service_stable_across_read",
    "lifecycle_and_build_stable_across_read", "owner_process_scan_complete",
    "owner_process_absent", "collection_complete",
)


class ProbeError(RuntimeError):
    pass


def demand(condition, message):
    if not condition:
        raise ProbeError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        demand(key not in result, "Duplicate JSON object key")
        result[key] = value
    return result


def object_json(raw, label):
    value = json.loads(raw, object_pairs_hook=unique_object)
    demand(isinstance(value, dict) and bool(value), label + " must be a nonempty object")
    return value


def matches(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def exact_fields(record, expected):
    return all(k in record and type(record[k]) is type(value) and record[k] == value
               for k, value in expected.items())


def record_id(payload, key="record_id"):
    body = {k: v for k, v in payload.items() if k not in {"generated_at", key}}
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def valid_id(payload, key="record_id"):
    return matches(payload.get(key), HEX64) and payload[key] == record_id(payload, key)


def bound_decimal(value, label):
    demand(type(value) in (str, int), label + " must be a positive decimal")
    text = str(value)
    demand(re.fullmatch(r"[0-9]+", text) is not None and int(text) > 0,
           label + " must be a positive decimal")
    return str(int(text))


def binding(raw):
    value = object_json(raw, "Invocation binding")
    demand(value.get("schema") == "mastermind.attended.beta_success_postread_binding.v1",
           "Missing exact invocation binding schema")
    demand(matches(value.get("protected_owner_R"), HEX40), "Invalid protected owner R")
    demand(isinstance(value.get("attempt_id"), str)
           and re.fullmatch(r"[0-9a-f]{32}", value["attempt_id"]), "Invalid attempt ID")
    demand(isinstance(value.get("owned_stage"), str)
           and re.fullmatch(r"/opt/terminal/beta/\.stage\.[A-Za-z0-9]{6}",
                            value["owned_stage"]), "Invalid owned beta stage")
    archives = value.get("owned_archive_paths")
    demand(isinstance(archives, list) and len(archives) <= 64, "Invalid observed archive list")
    demand(all(isinstance(p, str) and re.fullmatch(
        r"/opt/terminal/\.terminal-build-resource\.lock/beta-bootstrap\.[A-Za-z0-9]{6}", p)
        for p in archives), "Archive outside the canonical profile namespace")
    demand(len(set(archives)) == len(archives), "Duplicate observed archive path")
    artifact = value.get("protected_owner_artifact")
    demand(isinstance(artifact, str) and os.path.isabs(artifact)
           and os.path.normpath(artifact) == artifact, "Invalid owner artifact path")
    artifact = Path(artifact)
    demand(artifact.name == "terminal-build.sh" and artifact.parent.parent == Path("/root")
           and artifact.parent.name.startswith(
               "mastermind-beta-owner-" + value["protected_owner_R"][:8] + "-"),
           "Owner artifact is not the bound private protected entrance")
    demand(type(value.get("installer_exit")) is int, "Installer exit must be an integer")
    demand(type(value.get("transaction_commit_observed")) is bool,
           "Transaction-commit observation must be a boolean")
    prod = value.get("production_entry")
    demand(isinstance(prod, dict) and bool(prod), "Missing fresh production entry binding")
    for key in ("owner_sha256", "caddy_sha256"):
        demand(matches(prod.get(key), HEX64), "Invalid production " + key)
    demand(matches(prod.get("deployment_sha"), HEX40), "Invalid production deployment SHA")
    demand(matches(prod.get("next_build_id"), TOKEN), "Invalid production BUILD_ID")
    # Accept a caller's numeric or string PID while comparing canonical strings.
    value = dict(value)
    value["production_entry"] = dict(prod, pid=bound_decimal(prod.get("pid"), "Production PID"),
                                    start_monotonic=bound_decimal(
                                        prod.get("start_monotonic"), "Production start"))
    return value


def stat_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def directory_identity(info):
    # Unrelated directory membership changes do not alter custody of an ancestor.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)


def metadata(path, info):
    return {
        "path": str(path), "mode": oct(stat.S_IMODE(info.st_mode)),
        "uid": info.st_uid, "gid": info.st_gid, "dev": info.st_dev,
        "ino": info.st_ino, "nlink": info.st_nlink, "size": info.st_size,
        "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns,
        "type": ("symlink" if stat.S_ISLNK(info.st_mode) else
                 "regular" if stat.S_ISREG(info.st_mode) else
                 "directory" if stat.S_ISDIR(info.st_mode) else "other"),
    }


def directory_custody(info, label, exact_mode=None):
    demand(stat.S_ISDIR(info.st_mode) and info.st_uid == 0
           and not stat.S_IMODE(info.st_mode) & 0o022,
           label + " is not a real root-owned non-writable directory")
    if exact_mode is not None:
        demand(info.st_gid == 0 and stat.S_IMODE(info.st_mode) == exact_mode,
               label + " differs from the canonical root:root directory mode")


def file_custody(info, kind, label):
    if kind is None:
        return
    # beta_statectl require_regular: uid == deployment principal and no 0022.
    # Lifecycle mode 0640 is umask-sensitive; 0600 is admissible.
    demand(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022,
           label + " violates canonical owner/read-only file custody")
    if kind == "preflight":
        demand(info.st_gid == 0 and stat.S_IMODE(info.st_mode) == 0o640,
               label + " is not the canonical root:root 0640 preflight receipt")


@contextmanager
def parent_handle(path, trusted=False):
    path = Path(path)
    demand(path.is_absolute() and os.path.normpath(str(path)) == str(path)
           and path.name, "Evidence path must be normalized and absolute")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    handles = []
    try:
        fd = os.open("/", flags)
        handles.append((fd, None, None, directory_identity(os.fstat(fd))))
        if trusted:
            directory_custody(os.fstat(fd), "/")
        for component in path.parts[1:-1]:
            named = os.stat(component, dir_fd=fd, follow_symlinks=False)
            child_fd = os.open(component, flags, dir_fd=fd)
            opened = os.fstat(child_fd)
            handles.append((child_fd, fd, component, directory_identity(opened)))
            demand(directory_identity(named) == directory_identity(opened),
                   "Evidence ancestor changed while opening")
            if trusted:
                directory_custody(opened, component)
            fd = child_fd
        yield fd, path.name
        for current_fd, parent_fd, name, pinned in handles:
            demand(directory_identity(os.fstat(current_fd)) == pinned,
                   "Evidence ancestor custody changed")
            if parent_fd is not None:
                demand(directory_identity(os.stat(name, dir_fd=parent_fd,
                                                 follow_symlinks=False)) == pinned,
                       "Evidence named ancestry changed")
    finally:
        for fd, _, _, _ in reversed(handles):
            os.close(fd)


def inspect(path, trusted=False):
    with parent_handle(path, trusted) as (fd, name):
        try:
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return {"path": str(path), "exists": False}
        result = metadata(path, info)
        if stat.S_ISLNK(info.st_mode):
            result["symlink"] = os.readlink(name, dir_fd=fd)
            demand(stat_identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
                   == stat_identity(info), "Pointer changed while inspected")
        return result


def regular(path, limit=1024 * 1024, custody=None, trusted=False):
    with parent_handle(path, trusted) as (parent_fd, name):
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        demand(stat.S_ISREG(named.st_mode) and 0 < named.st_size <= limit,
               "Evidence is not a bounded nonempty regular file: " + str(path))
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        try:
            before = os.fstat(fd)
            demand(stat_identity(before) == stat_identity(named),
                   "Evidence metadata changed while opening")
            file_custody(before, custody, str(path))
            chunks, size = [], 0
            while True:
                chunk = os.read(fd, min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                demand(size <= limit, "Evidence exceeds its size bound")
            after = os.fstat(fd)
            demand(stat_identity(before) == stat_identity(after)
                   == stat_identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False))
                   and size == after.st_size, "Evidence changed while reading")
            file_custody(after, custody, str(path))
            result = metadata(path, after)
        finally:
            os.close(fd)
    data = b"".join(chunks)
    result["sha256"] = hashlib.sha256(data).hexdigest()
    return data, result


def read_record(path, custody="lifecycle", limit=1024 * 1024):
    data, info = regular(path, limit, custody, trusted=True)
    return object_json(data, "Evidence record"), info


def read_pointer(path):
    with parent_handle(path, trusted=True) as (fd, name):
        before = os.stat(name, dir_fd=fd, follow_symlinks=False)
        demand(stat.S_ISLNK(before.st_mode), "Lifecycle pointer must be a symlink")
        text = os.readlink(name, dir_fd=fd)
        dest = Path(os.path.normpath(text if os.path.isabs(text)
                                    else os.path.join(str(Path(path).parent), text)))
        demand(dest != S and S in dest.parents, "Lifecycle pointer escaped the state tree")
        value, info = read_record(dest)
        demand(os.readlink(name, dir_fd=fd) == text
               and stat_identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
               == stat_identity(before), "Lifecycle pointer changed during its record read")
    result = metadata(path, before)
    result.update(symlink=text, destination=info)
    return value, result


def identity(path, trusted=False, custody=None):
    data, info = regular(path, 512, custody, trusted)
    text = data.decode("ascii").strip()
    demand(matches(text, TOKEN), "Missing or invalid live identity token")
    return dict(info, text=text)


def directory_snapshot(path, exact_mode=None):
    with parent_handle(path, trusted=True) as (parent_fd, name):
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                     dir_fd=parent_fd)
        try:
            before = os.fstat(fd)
            directory_custody(before, str(path), exact_mode)
            demand(stat_identity(before) == stat_identity(named), "Directory changed on open")
            names = sorted(os.listdir(fd))
            demand(len(names) <= 4096, "Directory census exceeds diagnostic bound")
            rows = [metadata(Path(path) / child, os.stat(
                child, dir_fd=fd, follow_symlinks=False)) for child in names]
            demand(names == sorted(os.listdir(fd))
                   and stat_identity(before) == stat_identity(os.fstat(fd))
                   == stat_identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)),
                   "Directory changed during census")
            return metadata(path, before), rows
        finally:
            os.close(fd)


def command(args, git=False):
    env = None
    if git:
        # Preserve the attended PATH; inherited Git selectors cannot redirect -C.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(args, capture_output=True, text=True, timeout=45, env=env)
    demand(len(done.stdout) <= 65536 and len(done.stderr) <= 65536,
           "Read command output exceeds diagnostic bound")
    return {"exit": done.returncode, "out": done.stdout.strip(), "error": done.stderr.strip()}


def service_values(observation):
    demand(observation["exit"] == 0, "Required systemctl read did not succeed")
    result = {}
    for line in observation["out"].splitlines():
        demand("=" in line, "Malformed systemctl property")
        key, value = line.split("=", 1)
        demand(key not in result, "Duplicate systemctl property")
        result[key] = value
    for key in STABLE_PROPS:
        demand(isinstance(result.get(key), str) and bool(result[key]),
               "Missing required systemctl identity property: " + key)
    for key in ("MainPID", "ExecMainStartTimestampMonotonic"):
        demand(re.fullmatch(r"[0-9]+", result[key]) and int(result[key]) > 0,
               "Invalid/nonrunning service identity: " + key)
        result[key] = str(int(result[key]))
    return result


def owner_script(argv, executable):
    """Return only an executing owner script, never a filename inside JSON/-c."""
    if not argv:
        return None
    exe_name = os.path.basename(executable.removesuffix(" (deleted)"))
    if exe_name == "terminal-build.sh":
        return executable
    if exe_name not in {"bash", "sh", "dash", "zsh", "ksh", "ksh93"}:
        return None
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--":
            index += 1
            break
        if arg.startswith("--"):
            if arg in {"--rcfile", "--init-file"}:
                index += 2
            else:
                index += 1
            continue
        if arg.startswith(("-", "+")) and len(arg) > 1:
            # -c command strings and -s stdin do not identify a script argv.
            if arg[0] == "-" and ("c" in arg[1:] or "s" in arg[1:]):
                return None
            index += 2 if arg[-1] in {"o", "O"} else 1
            continue
        break
    if index < len(argv) and os.path.basename(argv[index]) == "terminal-build.sh":
        return argv[index]
    return None


def proc_stat(data):
    end = data.rfind(b") ")
    demand(end >= 0, "Malformed process stat")
    fields = data[end + 2:].split()
    demand(len(fields) >= 20, "Incomplete process stat")
    return {"state": fields[0].decode("ascii"),
            "flags": int(fields[6]), "start": int(fields[19])}


def bounded_bytes(path, limit):
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    demand(len(data) <= limit, "Process evidence exceeds read bound")
    return data


def scan_owner_processes(proc_root=Path("/proc")):
    """One bounded census. Other processes' argv/environment are never emitted."""
    result = {"complete": True, "scanned": 0, "vanished": 0,
              "nonexecuting": 0, "owners": [], "errors": [], "error_count": 0}
    try:
        pids = sorted((p for p in proc_root.iterdir() if p.name.isdecimal()),
                      key=lambda p: int(p.name))
        demand(len(pids) <= 65536, "Process census exceeds bound")
    except (OSError, ProbeError) as exc:
        result.update(complete=False, error_count=1,
                      errors=[{"stage": "enumeration", "type": type(exc).__name__}])
        return result
    for proc in pids:
        try:
            before = proc_stat(bounded_bytes(proc / "stat", 65536))
            if before["state"] in {"Z", "X", "x"} or before["flags"] & 0x00200000:
                # Kernel threads and already-dead tasks cannot execute the owner.
                result["nonexecuting"] += 1
                continue
            raw = bounded_bytes(proc / "cmdline", 1024 * 1024)
            demand(raw and raw.endswith(b"\0"), "Incomplete live-process cmdline")
            executable = os.readlink(proc / "exe")
            raw_after = bounded_bytes(proc / "cmdline", 1024 * 1024)
            executable_after = os.readlink(proc / "exe")
            after = proc_stat(bounded_bytes(proc / "stat", 65536))
            if after["state"] in {"Z", "X", "x"}:
                result["nonexecuting"] += 1
                continue
            demand(before["start"] == after["start"] and raw == raw_after
                   and executable == executable_after,
                   "Process identity changed during inspection")
            argv = [os.fsdecode(item) for item in raw[:-1].split(b"\0")]
            script = owner_script(argv, executable)
            result["scanned"] += 1
            if script is not None:
                result["owners"].append({"pid": int(proc.name), "executable": executable,
                                         "script": script, "start_ticks": after["start"]})
        except FileNotFoundError:
            # ENOENT for a field alone is not proof the process vanished.
            try:
                current = proc_stat(bounded_bytes(proc / "stat", 65536))
                demand(current["state"] in {"Z", "X", "x"},
                       "Live process evidence unavailable")
                result["nonexecuting"] += 1
                continue
            except FileNotFoundError:
                result["vanished"] += 1
                continue
            except (OSError, ProbeError, ValueError, UnicodeError):
                pass
            result["complete"] = False
            result["error_count"] += 1
            if len(result["errors"]) < 16:
                result["errors"].append({"pid": int(proc.name), "type": "IncompleteProcess"})
        except (OSError, ProbeError, ValueError, UnicodeError) as exc:
            result["complete"] = False
            result["error_count"] += 1
            if len(result["errors"]) < 16:
                result["errors"].append({"pid": int(proc.name), "type": type(exc).__name__})
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProbeError("Status redirect refused")


def status_read():
    # Empty ProxyHandler explicitly disables inherited HTTP/HTTPS proxy settings.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(STATUS_URL, headers={
        "Host": "beta.mastermind-x.com", "Accept": "application/json"})
    with opener.open(req, timeout=20) as response:
        demand(response.geturl() == STATUS_URL and response.status == 200,
               "Status endpoint did not directly return HTTP 200")
        data = response.read(65537)
        demand(len(data) <= 65536, "Status response exceeds size bound")
        # Retain only headers relevant to this read; do not emit cookies/tokens.
        headers = {key: ", ".join(response.headers.get_all(key, []))
                   for key in ("Cache-Control", "X-Robots-Tag", "Content-Type")}
        return {"http_status": response.status, "effective_url": response.geturl(),
                "headers": headers, "body": object_json(data, "Status response")}


def bounded_summary(value, depth=0):
    if depth > 6:
        return "<diagnostic depth limit>"
    if isinstance(value, str):
        return value if len(value) <= 2048 else value[:2048] + "<truncated>"
    if isinstance(value, dict):
        return {str(k)[:256]: bounded_summary(v, depth + 1)
                for k, v in list(value.items())[:96]}
    if isinstance(value, list):
        return [bounded_summary(v, depth + 1) for v in value[:96]]
    return value


def put_record(out, key, value, info):
    # Exact bytes remain named and hash-bound; chat diagnostics need not repeat
    # full source-audit mapping inventories or arbitrary unknown JSON fields.
    fields = {
        "schema", "generated_at", "record_id", "receipt_id", "target", "accepted_sha",
        "policy_digest", "policy_path", "canonical_repo", "target_root", "app_root",
        "deployment_marker", "provisioned", "provision_authorized", "accepted_runtime",
        "runtime_accepted", "rollback_baseline", "source_provisioned_record",
        "source_provisioned_record_id", "release_receipt_path", "release_receipt_id",
        "source_audit_receipt_id", "acceptance_attempt_id", "build_id",
        "previous_runtime_record", "previous_runtime_record_id", "result",
    }
    selected = {k: value[k] for k in fields if k in value}
    if isinstance(value.get("source_audit"), dict):
        inner = value["source_audit"]
        selected["source_audit"] = {k: inner[k] for k in (
            "schema", "receipt_id", "status", "accepted_sha", "policy_digest",
            "canonical_repo_head", "findings", "summary") if k in inner}
    out[key] = dict(info, record_summary=bounded_summary(selected),
                   exact_record_retained_at=(info["destination"]["path"]
                                             if "destination" in info else info["path"]))


def optional_quarantine():
    path = APP / ".next.broken"
    result = {"acceptance_gate": False}
    for label, operation in (
        ("metadata", lambda: inspect(path, trusted=True)),
        ("BUILD_ID", lambda: identity(path / "BUILD_ID")),
        ("nft", lambda: regular(path / "next-minimal-server.js.nft.json")[1]),
    ):
        try:
            if label != "metadata" and result.get("metadata", {}).get("type") != "directory":
                continue
            result[label] = operation()
        except Exception as exc:
            result[label] = {"diagnostic_error": type(exc).__name__}
    return result


def collect(bound, out, checks):
    out["protected_owner_R"] = bound["protected_owner_R"]
    out["invocation_binding"] = bounded_summary(bound)
    prod = bound["production_entry"]
    attempt = bound["attempt_id"]
    services = {name: command(["systemctl", "show", name, "--property=" + PROPS])
                for name in ("terminal.service", "terminal-beta.service")}
    out["services"] = services
    ps = service_values(services["terminal.service"])
    bs = service_values(services["terminal-beta.service"])
    checks["services_read_successful"] = True
    checks["production_service_identity"] = exact_fields(ps, {
        "MainPID": prod["pid"], "ExecMainStartTimestampMonotonic": prod["start_monotonic"],
        "ActiveState": "active", "SubState": "running", "UnitFileState": "enabled"})
    checks["beta_active_enabled"] = exact_fields(bs, {
        "ActiveState": "active", "SubState": "running", "UnitFileState": "enabled"})

    out["lifecycle_directories"] = {}
    for path, mode in ((B, None), (S, None), (S.parent, 0o750), (PREFLIGHT, 0o750)):
        info, _ = directory_snapshot(path, mode)
        out["lifecycle_directories"][str(path)] = info
    pointer_meta = inspect(B / ".runtime-accepted", trusted=True)
    out["runtime_pointer_observation"] = pointer_meta
    checks["runtime_pointer_present"] = pointer_meta.get("type") == "symlink"
    runtime, rp = read_pointer(B / ".runtime-accepted")
    source, sp = read_pointer(B / ".source-provisioned")
    put_record(out, "runtime_accepted", runtime, rp)
    put_record(out, "source_provisioned", source, sp)
    runtime_expected = {
        "schema": "mastermind.terminal.beta_runtime_accepted.v1",
        "target": "beta", "accepted_sha": A, "runtime_accepted": True,
        "rollback_baseline": True, "canonical_repo": str(REPO), "target_root": str(B),
        "app_root": str(APP), "policy_path": str(POLICY), "policy_digest": POLICY_ID,
        "previous_runtime_record": None, "previous_runtime_record_id": None,
        "acceptance_attempt_id": attempt,
    }
    checks["runtime_record_valid"] = (
        valid_id(runtime) and exact_fields(runtime, runtime_expected)
        and matches(runtime.get("build_id"), TOKEN)
        and Path(rp["destination"]["path"]).name
        == "runtime-accepted-" + A + "-" + runtime.get("record_id", "")[:16] + ".json"
        and all(matches(runtime.get(key), HEX64) for key in
                ("release_receipt_id", "source_audit_receipt_id", "source_provisioned_record_id"))
    )
    source_expected = {
        "schema": "mastermind.terminal.beta_source_provisioned.v1",
        "target": "beta", "accepted_sha": A, "policy_digest": POLICY_ID,
        "policy_path": str(POLICY), "canonical_repo": str(REPO), "target_root": str(B),
        "app_root": str(APP), "deployment_marker": str(APP / ".deployment-id"),
        "provision_authorized": True, "accepted_runtime": False, "rollback_baseline": False,
    }
    checks["source_record_valid"] = valid_id(source) and exact_fields(source, source_expected)
    checks["source_provenance_hash"] = sp["destination"]["sha256"] == SOURCE_SHA
    checks["source_provenance_binding"] = exact_fields(runtime, {
        "source_provisioned_record": sp["destination"]["path"],
        "source_provisioned_record_id": source.get("record_id")}) and valid_id(source)
    # No nullable equality: both the runtime token and actual files must be valid.
    before_ids = [identity(APP / name, trusted=True, custody="lifecycle")
                  for name in (".deployment-id", ".next/BUILD_ID")]
    out["beta_identity"] = before_ids
    checks["live_build_binding"] = (matches(runtime.get("build_id"), TOKEN)
                                   and before_ids[0]["text"] == A
                                   and before_ids[1]["text"] == runtime["build_id"])

    receipt_value = runtime.get("release_receipt_path")
    demand(isinstance(receipt_value, str) and receipt_value
           and not any(c in receipt_value for c in "\r\n\t"), "Missing named final preflight")
    receipt = Path(receipt_value)
    demand(receipt.parent == PREFLIGHT and os.path.normpath(receipt_value) == receipt_value,
           "Named final preflight is outside the reviewed receipt directory")
    outer, pf = read_record(receipt, "preflight", 2 * 1024 * 1024)
    inner = outer.get("source_audit")
    demand(isinstance(inner, dict) and bool(inner), "Missing nested final source audit")
    put_record(out, "accepted_preflight", outer, pf)
    checks["preflight_valid"] = (
        valid_id(outer, "receipt_id") and valid_id(inner, "receipt_id")
        and exact_fields(outer, {
            "schema": "mastermind.terminal.release_preflight_receipt.v1",
            "result": "CLEAN", "accepted_sha": A, "policy_digest": POLICY_ID,
            "receipt_id": runtime.get("release_receipt_id"),
            "source_audit_receipt_id": runtime.get("source_audit_receipt_id")})
        and exact_fields(inner, {
            "schema": "mastermind.terminal.source_audit_receipt.v1",
            "status": "CLEAN", "accepted_sha": A, "policy_digest": POLICY_ID,
            "receipt_id": runtime.get("source_audit_receipt_id"), "findings": []})
        and isinstance(inner.get("summary"), dict)
        and exact_fields(inner["summary"], {"blocking_findings": 0})
    )
    _, lifecycle_entries = directory_snapshot(S)
    paths = [Path(row["path"]) for row in lifecycle_entries
             if Path(row["path"]).name.startswith("attempt-" + attempt + "-")
             and Path(row["path"]).suffix == ".json"]
    demand(0 < len(paths) <= 64, "Missing or excessive immutable attempt evidence")
    attempts, attempt_info = [], []
    for path in paths:
        value, info = read_record(path)
        attempts.append(value)
        attempt_info.append(dict(info, record=bounded_summary(value)))
    out["attempt_records"] = attempt_info
    expected_attempt = {
        "schema": "mastermind.terminal.beta_release_attempt.v1",
        "target": "beta", "attempt_id": attempt, "target_sha": A,
        "target_root": str(B), "app_root": str(APP), "canonical_repo": str(REPO),
        "policy_digest": POLICY_ID, "mode": "bootstrap",
        "prior_runtime_record": None, "prior_runtime_record_id": None,
        "source_provisioned_record": sp["destination"]["path"],
        "source_provisioned_record_id": source.get("record_id"),
    }
    phases = {"staging", "activation", "inputs-dirty", "validated", "committing", "failed"}
    checks["attempt_records_valid"] = all(
        valid_id(value) and exact_fields(value, expected_attempt)
        and value.get("phase") in phases and type(value.get("live_inputs_dirty")) is bool
        for value in attempts)
    checks["committing_attempt_present"] = any(
        value.get("phase") == "committing"
        and matches(value.get("build_id"), TOKEN)
        and value.get("build_id") == runtime.get("build_id") for value in attempts)
    out["attempt_scope"] = ("Canonical successful finish leaves a committing immutable record, "
                            "removes pending, and does not write a committed JSON record.")

    policy_data, policy_meta = regular(POLICY, custody="lifecycle", trusted=True)
    policy = object_json(policy_data, "Beta policy")
    out["policy"] = policy_meta
    checks["policy_preserved"] = (
        policy_meta["sha256"] == POLICY_SHA
        and hashlib.sha256(json.dumps(policy, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest() == POLICY_ID)
    head = command(["git", "--no-optional-locks", "-C", str(REPO), "rev-parse", "HEAD"], git=True)
    out["beta_source_HEAD"] = head
    checks["beta_HEAD_A"] = head["exit"] == 0 and head["out"] == A
    for output_key, check_key, path, expected in (
        ("production_owner", "production_owner_preserved", "/opt/terminal/terminal-build.sh",
         prod["owner_sha256"]),
        ("Caddy", "Caddy_preserved", "/etc/caddy/Caddyfile", prod["caddy_sha256"]),
        ("protected_owner_artifact", "protected_owner_artifact_bytes",
         bound["protected_owner_artifact"], OWNER_SHA),
    ):
        _, info = regular(path, 5 * 1024 * 1024,
                          custody="lifecycle" if output_key == "protected_owner_artifact" else None,
                          trusted=output_key == "protected_owner_artifact")
        out[output_key] = info
        checks[check_key] = info["sha256"] == expected
    production_ids = [identity(Path("/opt/terminal/terminal") / name)
                      for name in (".deployment-id", ".next/BUILD_ID")]
    out["production_identity"] = production_ids
    checks["production_build_identity"] = (production_ids[0]["text"] == prod["deployment_sha"]
                                          and production_ids[1]["text"] == prod["next_build_id"])
    checks["caller_observed_installer_exit_zero"] = bound["installer_exit"] == 0
    checks["caller_observed_transaction_commit"] = bound["transaction_commit_observed"] is True

    status = status_read()
    out["status"] = bounded_summary(status)
    checks["status_contract"] = exact_fields(status["body"], {
        "enabled": True, "protocol": "mmx.shared-shell.v1", "buildId": A,
        "bridgeVersion": "20261018.1", "documentVersion": "20261018.1",
        "registrySha256": "5307ea5a7964fde609a8f20f1af30b6bf483b7631f7232e5db74f9ef1d710023"})
    cache = {x.strip().lower() for x in status["headers"]["Cache-Control"].split(",")}
    robots = {x.strip().lower() for x in status["headers"]["X-Robots-Tag"].split(",")}
    checks["status_cache_private_no_store"] = {"private", "no-store", "max-age=0"} <= cache
    checks["status_robots_noindex_nofollow"] = {"noindex", "nofollow"} <= robots
    after = command(["systemctl", "show", "terminal-beta.service",
                     "--property=" + ",".join(STABLE_PROPS)])
    out["beta_service_after"] = after
    after_values = service_values(after)
    checks["beta_service_stable_across_read"] = all(after_values[k] == bs[k] for k in STABLE_PROPS)
    runtime_after, rp_after = read_pointer(B / ".runtime-accepted")
    source_after, sp_after = read_pointer(B / ".source-provisioned")
    after_ids = [identity(APP / name, trusted=True, custody="lifecycle")
                 for name in (".deployment-id", ".next/BUILD_ID")]
    out["beta_identity_after"] = after_ids
    out["lifecycle_after"] = {"runtime": rp_after, "source": sp_after}
    checks["lifecycle_and_build_stable_across_read"] = (
        rp == rp_after and sp == sp_after and runtime == runtime_after
        and source == source_after and before_ids == after_ids)

    lock_meta, lock_entries = directory_snapshot(LOCK)
    out["shared_lock_parent"], out["shared_lock_entries"] = lock_meta, lock_entries
    _, beta_entries = directory_snapshot(B)
    out["beta_children"] = beta_entries
    absent = lambda path: inspect(path, trusted=True).get("exists") is False
    out["release_pending"] = inspect(B / ".release-pending", trusted=True)
    checks["pending_absent"] = out["release_pending"].get("exists") is False
    checks["owned_hold_absent"] = absent(LOCK / "hold")
    checks["owned_stage_absent"] = absent(bound["owned_stage"])
    checks["no_beta_stage_remains"] = not any(
        Path(row["path"]).name.startswith(".stage.") for row in beta_entries)
    checks["observed_archives_absent"] = all(absent(path) for path in bound["owned_archive_paths"])
    checks["archive_parent_empty"] = not lock_entries
    checks["generation_marker_scratch_absent"] = all(absent(APP / name) for name in
        (".deployment-id.bak", ".deployment-id.absent", ".deployment-id.new"))
    out["archive_proof_scope"] = (
        "Checks cover observed archive-path absence, postread resource-parent emptiness, "
        "and caller-bound canonical-owner final exit. This probe makes no pre-empty-parent "
        "claim; an empty observed-path list does not identify an individually observed archive.")
    out["historical_quarantine"] = optional_quarantine()
    out["owner_processes"] = scan_owner_processes()
    checks["owner_process_scan_complete"] = out["owner_processes"]["complete"] is True
    checks["owner_process_absent"] = (
        checks["owner_process_scan_complete"] and not out["owner_processes"]["owners"])
    checks["collection_complete"] = True


def verdict(out, checks):
    out["checks"] = checks
    out["unobserved_checks"] = [key for key in REQUIRED if checks.get(key) is None]
    out["failed_checks"] = [key for key in REQUIRED if checks.get(key) is not True]
    out["all_checks_pass"] = not out["errors"] and not out["failed_checks"]
    out["acceptance_disposition"] = (
        "ACCEPTED_RUNTIME_POSTREAD_PASS" if out["all_checks_pass"] else
        "ACCEPTED_POINTER_PRESENT_COMPLETION_UNRESOLVED"
        if checks.get("runtime_pointer_present") is True else "POSTREAD_UNQUALIFIED")
    out["bootstrap_retry_authorized"] = False
    return 0 if out["all_checks_pass"] else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = {
        "schema": "mastermind.attended.beta_success_postread.v3",
        "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "application_A": A, "readonly": True, "errors": [],
        "rollback_scope": ("First accepted installation. rollback_baseline=true is future "
                           "eligibility, not an executed accepted-runtime rollback."),
        "acceptance_scope": ("Bound installed-runtime postread only. Independent source, "
                             "namespace, public browser, auth and rollback acceptance are separate."),
    }
    checks = dict.fromkeys(REQUIRED)
    stage = "binding"
    try:
        demand(len(argv) == 1, "Exactly one JSON invocation binding is required")
        bound = binding(argv[0])
        checks["binding_valid"] = True
        stage = "collection"
        demand(sys.platform == "linux" and os.geteuid() == 0 and os.getegid() == 0,
               "Canonical attended postread requires the Linux root:root deployment principal")
        collect(bound, out, checks)
    except Exception as exc:
        # Do not echo parser documents, process argv, environments, or HTTP bodies.
        detail = str(exc)[:512] if isinstance(exc, ProbeError) else type(exc).__name__
        out["errors"].append({"stage": stage, "type": type(exc).__name__, "detail": detail})
    code = verdict(out, checks)
    print(json.dumps(out, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
