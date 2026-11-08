"""Attended beta mount/root/credential filesystem probe; import has no effects.

Prepare/review first. Operational invocation requires root, the frozen source
digest, exact successful v3 postread bytes, an observed existing public-data
relative filename, expected UID/GID, and a unique cache nonce in JSON argv.
This does not install, repair, restart, publish, or authorize bootstrap.

The only filesystem mutation is one exclusively created private beta-cache
file, with descriptor/name identity-bound cleanup. Data write-open probes never
write, create, truncate, append, change modes, or unlink a data file.
"""
import base64
from contextlib import contextmanager
import datetime
import errno
import hashlib
import json
import os
import posixpath
import re
import signal
import stat
import subprocess
import sys
import urllib.error
import urllib.request

A = "e45bde2cac07ac3b29285ff70c40d68900fad62c"
OWNER_SHA = "c6759cc653e0f19102a015ec52842795bde24eb85766d2e73f3024b4eefe409d"
BETA = "/opt/terminal/beta"
APP = BETA + "/terminal"
CACHE = APP + "/.next/cache"
STATE = "/var/lib/mastermind-terminal-beta/source-provisioned"
RUNTIME = BETA + "/.runtime-accepted"
DATA_ROOTS = ("/opt/terminal/terminal/public/data", APP + "/public/data")
URL = "http://127.0.0.1:3001/api/shared-shell/status"
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
PROPS = (
    "LoadState", "ActiveState", "SubState", "UnitFileState", "MainPID",
    "ExecMainStartTimestampMonotonic", "InvocationID", "NRestarts",
    "FragmentPath", "DropInPaths", "NeedDaemonReload", "User", "Group",
    "SupplementaryGroups", "WorkingDirectory", "RootDirectory", "RootImage",
    "ProtectSystem", "ProtectHome", "PrivateTmp", "PrivateDevices",
    "NoNewPrivileges", "CapabilityBoundingSet", "AmbientCapabilities",
    "ReadWritePaths", "ReadOnlyPaths", "BindReadOnlyPaths", "InaccessiblePaths",
    "RestrictAddressFamilies", "RestrictNamespaces", "SystemCallFilter", "UMask",
)
POSTREAD_GATES = (
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
READS = (
    ("app", APP + "/package.json", 1024 * 1024),
    ("dependency", APP + "/node_modules/next/package.json", 1024 * 1024),
    ("build", APP + "/.next/routes-manifest.json", 8 * 1024 * 1024),
    ("marker", APP + "/.deployment-id", 512),
    ("build_marker", APP + "/.next/BUILD_ID", 512),
)
LIMITS = [
    "Reproduces only the observed mount namespace, root, UID/GID/groups, "
    "zero capability sets, and NoNewPrivs for this attended filesystem probe.",
    "Does not join the service cgroup, PID/user/network namespaces, or install "
    "its seccomp filter or LSM execution profile. Their observed values are "
    "retained separately and are not asserted equivalent.",
    "Successful before/after identity observations bound this interval; they "
    "do not guarantee future process, publisher, or mount stability.",
    "Public browser, DNS/TLS, auth, source publication, and rollback execution "
    "acceptance remain separate. No installer or bootstrap is authorized.",
]


class ProbeError(RuntimeError):
    pass


def demand(condition, message):
    if not condition:
        raise ProbeError(message)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        demand(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def json_object(raw):
    value = json.loads(raw, object_pairs_hook=unique_object)
    demand(isinstance(value, dict) and bool(value), "nonempty JSON object required")
    return value


def pattern(value, regex):
    return isinstance(value, str) and regex.fullmatch(value) is not None


def positive(value):
    return type(value) is int and 0 < value < 2 ** 31


def safe_path(path):
    demand(isinstance(path, str) and path.startswith("/")
           and not path.startswith("//") and posixpath.normpath(path) == path
           and all(ord(c) >= 32 and ord(c) != 127 for c in path),
           "invalid absolute path")
    return path


def public_relative(value):
    demand(isinstance(value, str) and 0 < len(value) <= 512
           and not value.startswith("/") and posixpath.normpath(value) == value,
           "public filename must be a normalized relative path")
    demand(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", p)
               and p not in (".", "..") for p in value.split("/")),
           "public filename contains an inadmissible component")
    return value


def info(st):
    return {"dev": st.st_dev, "ino": st.st_ino, "mode": oct(stat.S_IMODE(st.st_mode)),
            "uid": st.st_uid, "gid": st.st_gid, "nlink": st.st_nlink,
            "size": st.st_size, "mtime_ns": st.st_mtime_ns,
            "ctime_ns": st.st_ctime_ns}


def identity(st, directory=False):
    basic = (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid)
    return basic if directory else basic + (
        st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def inode(st):
    return st.st_dev, st.st_ino


def read_fd(fd, limit):
    chunks = []
    total = 0
    while True:
        chunk = os.read(fd, min(65536, limit + 1 - total))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        demand(total <= limit, "bounded read limit exceeded")
        chunks.append(chunk)


def kernel_read(path, limit=2 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        return read_fd(fd, limit)
    finally:
        os.close(fd)


def parse_properties(raw):
    result = {}
    for line in raw.strip().splitlines():
        key, sep, value = line.partition("=")
        demand(sep and key and key not in result, "invalid service property response")
        result[key] = value
    return result


def mount_unescape(value):
    demand(not re.search(r"\\(?![0-7]{3})", value), "invalid mountinfo escape")
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), value)


def parse_mountinfo(raw):
    records = {}
    for line in raw.decode("utf-8", "strict").splitlines():
        fields = line.split()
        demand(fields.count("-") == 1, "invalid mountinfo separator")
        split = fields.index("-")
        demand(split >= 6 and len(fields) == split + 4,
               "incomplete mountinfo record")
        mid, parent = int(fields[0]), int(fields[1])
        demand(mid > 0 and parent > 0 and mid not in records,
               "invalid or duplicate mount ID")
        dev = fields[2].split(":")
        demand(len(dev) == 2 and all(v.isdecimal() for v in dev),
               "invalid mount device")
        root, point = mount_unescape(fields[3]), mount_unescape(fields[4])
        safe_path(root)
        safe_path(point)
        opts = sorted(set(fields[5].split(",")))
        demand(("ro" in opts) != ("rw" in opts), "mount lacks a unique ro/rw flag")
        records[mid] = {
            "id": mid, "parent": parent, "device": [int(v) for v in dev],
            "root": root, "point": point, "options": opts,
            "optional": fields[6:split], "fstype": fields[split + 1],
            "source": mount_unescape(fields[split + 2]),
            "super_options": sorted(set(fields[split + 3].split(","))),
        }
    demand(bool(records), "empty mountinfo")
    for mid in records:
        seen, current = set(), mid
        while current in records:
            demand(current not in seen, "cyclic mount parent graph")
            seen.add(current)
            parent = records[current]["parent"]
            if parent == current:
                break  # Linux namespace root may refer to itself.
            current = parent
    return records


def mount_digest(table):
    return digest(canonical([table[key] for key in sorted(table)]))


def fd_mount(fd, table):
    fields = {}
    for line in kernel_read("/proc/self/fdinfo/" + str(fd), 8192).decode().splitlines():
        key, sep, value = line.partition(":")
        if sep:
            demand(key not in fields, "duplicate fdinfo key")
            fields[key] = value.strip()
    value = fields.get("mnt_id", "")
    demand(value.isdecimal() and int(value) in table,
           "descriptor mount is absent from mountinfo")
    record = table[int(value)]
    st = os.fstat(fd)
    demand([os.major(st.st_dev), os.minor(st.st_dev)] == record["device"],
           "descriptor device disagrees with selected mount")
    return record


def below(path, parent):
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def mount_ancestor(table, ancestor, current):
    seen = set()
    while current in table and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        current = table[current]["parent"]
    return False


class DirectoryChain:
    """All directory descriptors are opened by the calling (already dropped) process."""
    def __init__(self, path, table=None, cache_uid=None, cache_gid=None):
        self.path = safe_path(path)
        self.table, self.cache_uid, self.cache_gid = table, cache_uid, cache_gid
        self.entries = []

    def _check(self, fd, path):
        st = os.fstat(fd)
        demand(stat.S_ISDIR(st.st_mode), "ancestor is not a directory")
        ro = self.table is not None and "ro" in fd_mount(fd, self.table)["options"]
        trusted = st.st_uid == 0 and not stat.S_IMODE(st.st_mode) & 0o022
        private_cache = (
            path == CACHE and self.cache_uid is not None
            and st.st_uid == self.cache_uid and st.st_gid == self.cache_gid
            and stat.S_IMODE(st.st_mode) & 0o700 == 0o700
            and not stat.S_IMODE(st.st_mode) & 0o022 and not ro)
        demand(trusted or ro or private_cache, "untrusted writable ancestor: " + path)
        return st

    def __enter__(self):
        try:
            fd = os.open("/", os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                checked = self._check(fd, "/")
            except BaseException:
                os.close(fd)
                raise
            self.entries.append(("/", fd, checked))
            current = ""
            for name in self.path.strip("/").split("/") if self.path != "/" else []:
                current += "/" + name
                fd = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW
                             | os.O_CLOEXEC, dir_fd=self.entries[-1][1])
                try:
                    checked = self._check(fd, current)
                except BaseException:
                    os.close(fd)
                    raise
                self.entries.append((current, fd, checked))
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    @property
    def fd(self):
        return self.entries[-1][1]

    def verify(self):
        for path, fd, original in self.entries:
            demand(identity(self._check(fd, path), True) == identity(original, True),
                   "ancestor descriptor custody changed: " + path)
        # Rewalk from root so a renamed/displaced ancestor cannot silently pass.
        with DirectoryChain(self.path, self.table, self.cache_uid, self.cache_gid) as fresh:
            demand([identity(v[2], True) for v in self.entries]
                   == [identity(v[2], True) for v in fresh.entries],
                   "ancestor name no longer identifies the opened directory")

    def __exit__(self, *_):
        for _, fd, _ in reversed(self.entries):
            os.close(fd)
        self.entries = []


def read_regular(path, limit, table=None, root_custody=False):
    safe_path(path)
    with DirectoryChain(posixpath.dirname(path), table) as parent:
        name = posixpath.basename(path)
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent.fd)
        try:
            before = os.fstat(fd)
            demand(stat.S_ISREG(before.st_mode), "read target is not a regular file: " + path)
            if root_custody:
                demand(before.st_uid == 0 and before.st_nlink == 1
                       and not stat.S_IMODE(before.st_mode) & 0o022,
                       "immutable root file custody failed: " + path)
            raw = read_fd(fd, limit)
            after = os.fstat(fd)
            named = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
            demand(identity(before) == identity(after) == identity(named),
                   "file changed during descriptor read: " + path)
            parent.verify()
            result = {"path": path, **info(after), "sha256": digest(raw)}
            if table is not None:
                result["mount"] = fd_mount(fd, table)
            return result, raw
        finally:
            os.close(fd)


def runtime_observation(expected):
    with DirectoryChain(BETA) as parent:
        st = os.stat(".runtime-accepted", dir_fd=parent.fd, follow_symlinks=False)
        demand(stat.S_ISLNK(st.st_mode) and st.st_uid == 0, "invalid runtime pointer")
        link = os.readlink(".runtime-accepted", dir_fd=parent.fd)
        destination = posixpath.normpath(posixpath.join(BETA, link))
        demand(posixpath.dirname(destination) == STATE
               and destination == expected["destination"]["path"],
               "runtime pointer destination differs from successful postread")
        meta, raw = read_regular(destination, 65536, root_custody=True)
        record = json_object(raw)
        demand(meta["sha256"] == expected["destination"]["sha256"],
               "accepted runtime raw bytes differ from successful postread")
        demand(record == expected["record_summary"], "accepted runtime record changed")
        demand(identity(st) == identity(os.stat(
            ".runtime-accepted", dir_fd=parent.fd, follow_symlinks=False))
            and link == os.readlink(".runtime-accepted", dir_fd=parent.fd),
            "runtime pointer changed during observation")
        parent.verify()
        return {"pointer": {"path": RUNTIME, **info(st), "symlink": link},
                "destination": meta, "record": record}


def service_observation():
    result = subprocess.run(
        ["/usr/bin/systemctl", "show", "--no-pager", "--property=" + ",".join(PROPS),
         "terminal-beta.service"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=ENV, close_fds=True, timeout=12, check=False)
    demand(result.returncode == 0, "service property read failed")
    demand(len(result.stdout) <= 131072, "service property output exceeds bound")
    values = parse_properties(result.stdout.decode("utf-8", "strict"))
    demand(set(PROPS) <= set(values), "mandatory loaded-unit observations missing")
    for key, required in (("LoadState", "loaded"), ("ActiveState", "active"),
                          ("SubState", "running"), ("UnitFileState", "enabled"),
                          ("NeedDaemonReload", "no"), ("NoNewPrivileges", "yes")):
        demand(values[key] == required, "beta service gate failed: " + key)
    for key in ("MainPID", "ExecMainStartTimestampMonotonic"):
        demand(values[key].isdecimal() and int(values[key]) > 0,
               "missing live service identity: " + key)
    demand(pattern(values["InvocationID"], NONCE) and values["NRestarts"].isdecimal(),
           "invalid service invocation/restart identity")
    demand(values["FragmentPath"] and values["WorkingDirectory"] == APP,
           "loaded beta unit path/working directory is unobserved or unexpected")
    return values


def proc_status(raw):
    parsed = {}
    for line in raw.decode("utf-8", "strict").splitlines():
        key, sep, value = line.partition(":")
        if sep:
            demand(key not in parsed, "duplicate process-status field")
            parsed[key] = value.strip()
    result = {}
    for key in ("Uid", "Gid", "Groups"):
        demand(key in parsed, "missing process credential field: " + key)
        parts = parsed[key].split()
        demand(all(p.isdecimal() for p in parts), "invalid process credential vector")
        result[key] = [int(p) for p in parts]
    demand(len(result["Uid"]) == len(result["Gid"]) == 4, "incomplete process IDs")
    demand(len(result["Groups"]) == len(set(result["Groups"])), "duplicate process group")
    result["Groups"].sort()
    for key in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
        value = parsed.get(key)
        demand(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]+", value),
               "missing process capability field: " + key)
        result[key] = int(value, 16)
    for key in ("NoNewPrivs", "Seccomp", "Seccomp_filters"):
        demand(parsed.get(key, "").isdecimal(), "missing process security field: " + key)
        result[key] = int(parsed[key])
    demand(re.fullmatch(r"[0-7]{4}", parsed.get("Umask", "")), "missing process umask")
    result["Umask"] = parsed["Umask"]
    return result


def proc_start(raw):
    text = raw.decode("utf-8", "strict")
    closing = text.rfind(")")
    demand(closing > 0, "invalid proc stat command boundary")
    fields = text[closing + 1:].split()
    demand(len(fields) >= 20 and fields[19].isdecimal(), "missing process start ticks")
    demand(fields[0] not in ("Z", "X", "x"), "observed process is not live")
    return int(fields[19])


def link_observation(path):
    link = os.readlink(path)
    st = os.stat(path)  # Deliberate observation of the kernel /proc magic link.
    return {"link": link, "dev": st.st_dev, "ino": st.st_ino}


def process_observation(pid):
    prefix = "/proc/" + str(pid)
    start = proc_start(kernel_read(prefix + "/stat", 65536))
    status = proc_status(kernel_read(prefix + "/status", 65536))
    root = link_observation(prefix + "/root")
    namespace = link_observation(prefix + "/ns/mnt")
    executable = link_observation(prefix + "/exe")
    cgroup = kernel_read(prefix + "/cgroup", 65536).decode("utf-8", "strict").strip()
    lsm = kernel_read(prefix + "/attr/current", 65536).decode("utf-8", "strict").strip()
    demand(cgroup and lsm, "missing cgroup or LSM observation")
    table = parse_mountinfo(kernel_read(prefix + "/mountinfo"))
    demand(start == proc_start(kernel_read(prefix + "/stat", 65536)),
           "process start changed during observation")
    return {"pid": int(pid) if str(pid).isdecimal() else os.getpid(),
            "start_ticks": start, "status": status, "root": root,
            "mount_namespace": namespace, "executable": executable,
            "cgroup": cgroup, "lsm": lsm, "mountinfo_sha256": mount_digest(table)}, table


def require_credentials(status, uid, gid, groups=None):
    demand(positive(uid) and positive(gid), "root or invalid expected principal")
    demand(status["Uid"] == [uid] * 4 and status["Gid"] == [gid] * 4,
           "real/effective/saved/fs credentials do not match exact beta principal")
    if groups is not None:
        demand(status["Groups"] == groups, "supplementary group vector differs")
    demand(all(status[k] == 0 for k in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")),
           "nonzero capability set")
    demand(status["NoNewPrivs"] == 1, "NoNewPrivs is not set")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def status_observation(expected_body):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(URL, headers={"Accept": "application/json"})
    with opener.open(request, timeout=6) as response:
        demand(response.status == 200 and response.geturl() == URL,
               "beta HTTP status or endpoint mismatch")
        raw = response.read(1024 * 1024 + 1)
        demand(len(raw) <= 1024 * 1024, "beta status response exceeds bound")
        body = json_object(raw)
        demand(body == expected_body and body.get("buildId") == A
               and body.get("enabled") is True
               and body.get("protocol") == "mmx.shared-shell.v1",
               "beta HTTP contract differs from accepted postread")
        cache = response.headers.get("Cache-Control", "")
        robots = response.headers.get("X-Robots-Tag", "")
        demand({"private", "no-store"} <= {
            v.strip().lower() for v in cache.split(",")}, "private/no-store header missing")
        demand({"noindex", "nofollow"} <= {
            v.strip().lower() for v in robots.split(",")}, "robots exclusion header missing")
        return {"url": URL, "status": 200, "body": body, "sha256": digest(raw),
                "cache_control": cache, "x_robots_tag": robots}


def parse_binding(raw):
    value = json_object(raw)
    demand(value.get("schema") == "mastermind.attended.beta_namespace_binding.v1",
           "wrong namespace binding schema")
    for key in ("probe_sha256", "accepted_postread_sha256"):
        demand(pattern(value.get(key), HEX64), "invalid binding digest: " + key)
    demand(pattern(value.get("protected_owner_R"), HEX40), "invalid protected owner R")
    demand(positive(value.get("uid")) and positive(value.get("gid")), "invalid beta IDs")
    demand(pattern(value.get("cache_probe_nonce"), NONCE), "invalid private cache nonce")
    public_relative(value.get("public_relative_path"))
    encoded = value.get("accepted_postread_base64")
    demand(isinstance(encoded, str) and 0 < len(encoded) <= 180000,
           "missing or oversized exact successful postread bytes")
    postraw = base64.b64decode(encoded, validate=True)
    demand(digest(postraw) == value["accepted_postread_sha256"], "postread digest mismatch")
    post = json_object(postraw)
    demand(post.get("schema") == "mastermind.attended.beta_success_postread.v3"
           and post.get("application_A") == A
           and post.get("protected_owner_R") == value["protected_owner_R"]
           and post.get("all_checks_pass") is True
           and post.get("acceptance_disposition") == "ACCEPTED_RUNTIME_POSTREAD_PASS"
           and all(post.get(k) == [] for k in ("failed_checks", "unobserved_checks", "errors")),
           "caller postread is not the exact successful acceptance contract")
    checks = post.get("checks")
    demand(isinstance(checks, dict) and set(POSTREAD_GATES) <= set(checks)
           and all(v is True for v in checks.values()), "postread gates incomplete or failed")
    runtime = post.get("runtime_accepted")
    demand(isinstance(runtime, dict) and runtime.get("path") == RUNTIME
           and runtime.get("type") == "symlink", "postread runtime pointer missing")
    record = runtime.get("record_summary")
    destination = runtime.get("destination")
    demand(isinstance(record, dict) and bool(record)
           and isinstance(destination, dict) and bool(destination),
           "empty accepted-runtime binding")
    for key in ("record_id", "release_receipt_id", "source_audit_receipt_id",
                "source_provisioned_record_id"):
        demand(pattern(record.get(key), HEX64), "empty or invalid runtime ID: " + key)
    demand(pattern(record.get("acceptance_attempt_id"), NONCE)
           and record.get("runtime_accepted") is True and record.get("accepted_sha") == A
           and record.get("target") == "beta" and record.get("target_root") == BETA
           and record.get("app_root") == APP
           and isinstance(record.get("build_id"), str) and bool(record["build_id"])
           and record.get("previous_runtime_record") is None
           and record.get("previous_runtime_record_id") is None,
           "runtime record is not the bound first accepted A")
    required_record_keys = {"previous_runtime_record", "previous_runtime_record_id"}
    demand(required_record_keys <= set(record), "null previous-runtime fields are missing")
    id_body = {k: v for k, v in record.items() if k not in {"record_id", "generated_at"}}
    demand(digest(canonical(id_body)) == record["record_id"], "runtime content ID mismatch")
    demand(pattern(destination.get("sha256"), HEX64)
           and destination.get("path") == STATE + "/runtime-accepted-" + A + "-"
           + record["record_id"][:16] + ".json", "runtime destination binding invalid")
    svc = post.get("beta_service_after")
    demand(isinstance(svc, dict) and svc.get("exit") == 0 and not svc.get("error")
           and isinstance(svc.get("out"), str), "successful postread service read missing")
    service = parse_properties(svc["out"])
    demand(all(service.get(k) == v for k, v in (
        ("ActiveState", "active"), ("SubState", "running"), ("UnitFileState", "enabled"))),
        "postread service was not active/enabled")
    for k in ("MainPID", "ExecMainStartTimestampMonotonic"):
        demand(service.get(k, "").isdecimal() and int(service[k]) > 0,
               "postread live process identity missing")
    demand(isinstance(post.get("status"), dict)
           and isinstance(post["status"].get("body"), dict), "accepted HTTP body missing")
    return value, post, service


def verify_live_build(post, table=None):
    expected = post["runtime_accepted"]["record_summary"]
    result = []
    for path, text in ((APP + "/.deployment-id", A),
                       (APP + "/.next/BUILD_ID", expected["build_id"])):
        meta, raw = read_regular(path, 512, table, root_custody=True)
        demand(raw.decode("ascii", "strict").strip() == text, "live build/marker mismatch")
        result.append(meta)
    return result


def data_snapshot(path, table):
    meta, raw = read_regular(path, 64 * 1024 * 1024, table)
    demand("ro" in meta["mount"]["options"], "selected public-file mount is writable")
    return meta


def alias_equivalent(first, second):
    demand((first["dev"], first["ino"], first["sha256"], first["size"])
           == (second["dev"], second["ino"], second["sha256"], second["size"]),
           "production and beta aliases do not identify the same readable bytes/inode")


def visible_readonly_subtree(path, table):
    with DirectoryChain(path, table) as root:
        selected_root = fd_mount(root.fd, table)
        demand("ro" in selected_root["options"], "public-data root mount is writable")
        root.verify()
    selected = {path: selected_root["id"]}
    visible = [{"path": path, "mount": selected_root}]
    hidden = []
    points = sorted({r["point"] for r in table.values()
                     if r["point"] != path and below(r["point"], path)},
                    key=lambda p: (len(p.split("/")), p))
    for point in points:
        containing = max((p for p in selected if below(point, p)), key=len)
        ancestor = selected[containing]
        candidates = [r for r in table.values() if r["point"] == point
                      and mount_ancestor(table, ancestor, r["id"])]
        if not candidates:
            hidden.append({"path": point, "reason": "below an overmounted hidden layer"})
            continue
        # O_PATH handles directory or file mountpoints without reading contents.
        with DirectoryChain(posixpath.dirname(point), table) as parent:
            fd = os.open(posixpath.basename(point), os.O_PATH | os.O_NOFOLLOW
                         | os.O_CLOEXEC, dir_fd=parent.fd)
            try:
                demand(not stat.S_ISLNK(os.fstat(fd).st_mode),
                       "visible descendant mountpoint is a symlink")
                actual = fd_mount(fd, table)
                demand(actual["id"] in {r["id"] for r in candidates},
                       "visible descendant mount lacks expected ancestry")
                demand("ro" in actual["options"], "visible descendant mount is writable")
                parent.verify()
                selected[point] = actual["id"]
                visible.append({"path": point, "mount": actual})
            finally:
                os.close(fd)
    return {"root": path, "visible": visible, "hidden": hidden}


def refusal(path, expected, table):
    flags = os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    result = {"path": path, "flags": flags,
              "flag_names": ["O_WRONLY", "O_CLOEXEC", "O_NOFOLLOW"],
              "readable_before": expected, "opened": False}
    with DirectoryChain(posixpath.dirname(path), table) as parent:
        name = posixpath.basename(path)
        named = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
        demand(info(named) == {k: expected[k] for k in info(named)},
               "public file changed before denial check")
        try:
            fd = os.open(name, flags, dir_fd=parent.fd)
        except OSError as exc:
            result["errno"] = exc.errno
            result["errno_name"] = errno.errorcode.get(exc.errno, "UNKNOWN")
            result["accepted_denial"] = (
                exc.errno == errno.EROFS or
                (exc.errno in (errno.EACCES, errno.EPERM)
                 and "ro" in expected["mount"]["options"]))
            result["meaning"] = (
                "kernel EROFS" if exc.errno == errno.EROFS else
                "access denial corroborated by actual descriptor mount ro"
                if result["accepted_denial"] else "unqualified failure")
        else:
            os.close(fd)  # NO read, write, truncate, chmod, or cleanup on this fd.
            result.update(opened=True, accepted_denial=False,
                          meaning="write-only open unexpectedly succeeded; closed without write")
        parent.verify()
    return result


def own_cache_file(uid, gid, nonce, table, result):
    """One exclusive file; never cleanup an unowned/replaced name or directory."""
    name = ".market-os-namespace-acceptance-" + nonce
    result.update(path=CACHE + "/" + name, created=False, cleanup_complete=False)
    payload1 = ("namespace-probe:" + nonce + ":phase-one\n").encode()
    payload2 = ("namespace-probe:" + nonce + ":phase-two\n").encode()
    demand(len(payload1) == len(payload2), "internal cache payload size mismatch")
    with DirectoryChain(CACHE, table, uid, gid) as parent:
        pst = os.fstat(parent.fd)
        demand(pst.st_uid == uid and pst.st_gid == gid
               and stat.S_IMODE(pst.st_mode) & 0o700 == 0o700
               and not stat.S_IMODE(pst.st_mode) & 0o022
               and "rw" in fd_mount(parent.fd, table)["options"],
               "cache leaf lacks exact private service ownership/writable mount")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fd, created = None, None
        known = b""

        def guard(expected_bytes):
            parent.verify()
            actual = os.fstat(fd)
            named = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
            demand(stat.S_ISREG(actual.st_mode) and inode(actual) == inode(created)
                   and actual.st_uid == uid and actual.st_gid == gid
                   and stat.S_IMODE(actual.st_mode) == 0o600 and actual.st_nlink == 1
                   and identity(actual) == identity(named),
                   "owned cache name/descriptor custody changed")
            os.lseek(fd, 0, os.SEEK_SET)
            demand(read_fd(fd, 1024) == expected_bytes, "owned cache bytes changed")
            demand(identity(actual) == identity(os.fstat(fd)),
                   "owned cache changed during byte check")

        error = None
        try:
            previous_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT, signal.SIGHUP})
            try:
                fd = os.open(name, flags, 0o600, dir_fd=parent.fd)
                result["created"] = True
                created = os.fstat(fd)
                result.update(created_identity=info(created),
                              create_flags=["O_RDWR", "O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_CLOEXEC"])
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            guard(known)
            for phase, payload in (("create_read", payload1), ("update_read", payload2)):
                guard(known)
                os.lseek(fd, 0, os.SEEK_SET)
                previous_mask = signal.pthread_sigmask(
                    signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT, signal.SIGHUP})
                try:
                    written = os.write(fd, payload)
                    # No truncation: a short update retains the known prior tail.
                    # Record actual syscall progress before any signal or fsync.
                    demand(0 <= written <= len(payload), "invalid cache write result")
                    known = payload[:written] + known[written:]
                    result["last_write"] = {
                        "phase": phase, "requested": len(payload), "written": written,
                        "known_bytes": len(known), "known_sha256": digest(known)}
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                demand(written == len(payload), "partial private cache write")
                os.fsync(fd)
                guard(known)
                result[phase] = {"sha256": digest(payload), "bytes": len(payload), "pass": True}
        except BaseException as exc:
            error = exc
        finally:
            # Suppress further interruption only for this exact owned cleanup.
            old = {sig: signal.signal(sig, signal.SIG_IGN)
                   for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
            try:
                if fd is not None:
                    demand(created is not None, "cache allocation identity unobserved; no cleanup")
                    guard(known)
                    os.unlink(name, dir_fd=parent.fd)
                    try:
                        os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ProbeError("cache name unexpectedly exists after exact unlink")
                    demand(os.fstat(fd).st_nlink == 0, "unlinked cache descriptor retains links")
                    parent.verify()
                    result["cleanup_complete"] = True
            except BaseException as cleanup_error:
                result["cleanup_error"] = type(cleanup_error).__name__ + ": " + str(cleanup_error)[:256]
                result["cleanup_unresolved"] = True
                if error is None:
                    error = cleanup_error
            finally:
                if fd is not None:
                    os.close(fd)
                for sig, handler in old.items():
                    signal.signal(sig, handler)
        if error is not None:
            raise error


def no_inherited_handles():
    for fd in (0, 1, 2):
        demand(stat.S_ISFIFO(os.fstat(fd).st_mode), "standard probe handle is not a pipe")
    inherited = []
    for text in os.listdir("/proc/self/fd"):
        fd = int(text)
        if fd <= 2:
            continue
        try:
            st = os.fstat(fd)
        except OSError as exc:
            if exc.errno == errno.EBADF:
                continue  # os.listdir's transient descriptor has already closed.
            raise
        inherited.append({"fd": fd, "type": stat.S_IFMT(st.st_mode)})
    demand(not inherited, "unexpected inherited handle after namespace/drop")


def interrupted(signum, _frame):
    raise ProbeError("owned probe interrupted by signal " + str(signum))


def inner_run(binding, result):
    # Only kernel identity/handle observations precede these refusal gates.
    no_inherited_handles()
    before, table = process_observation("self")
    result["probe_process_before"] = before
    require_credentials(before["status"], binding["uid"], binding["gid"], binding["groups"])
    for key in ("root", "mount_namespace"):
        demand({k: before[key][k] for k in ("dev", "ino")}
               == {k: binding["process"][key][k] for k in ("dev", "ino")},
               "probe did not enter exact target " + key)
    demand(before["mountinfo_sha256"] == binding["process"]["mountinfo_sha256"],
           "probe mount table differs from target process")
    demand(os.getcwd() == "/", "probe working directory is not namespace root")
    os.umask(0o077)  # Private creation policy for the single new file only.
    result["credential_namespace_gate"] = True
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)
    result["readable_files"] = []
    for role, path, limit in READS:
        meta, raw = read_regular(path, limit, table)
        demand(len(raw) > 0, "representative runtime file is empty")
        if role == "marker":
            demand(raw.decode("ascii").strip() == A, "inner deployment marker mismatch")
        elif role == "build_marker":
            demand(raw.decode("ascii").strip() == binding["build_id"], "inner BUILD_ID mismatch")
        else:
            json_object(raw)
        result["readable_files"].append({"role": role, **meta})
    result["readonly_mount_subtrees"] = [
        visible_readonly_subtree(path, table) for path in DATA_ROOTS]
    paths = [root + "/" + binding["public_relative_path"] for root in DATA_ROOTS]
    initial = [data_snapshot(path, table) for path in paths]
    alias_equivalent(*initial)
    result["public_data_before"] = initial
    denials = [refusal(path, meta, table) for path, meta in zip(paths, initial)]
    result["write_open_refusals"] = denials
    after_denial = [data_snapshot(path, table) for path in paths]
    demand(after_denial == initial, "public publisher changed during write-open checks")
    demand(all(d.get("accepted_denial") is True and not d["opened"] for d in denials),
           "a public-data write-open did not produce a qualified refusal")
    result["cache"] = {}
    own_cache_file(binding["uid"], binding["gid"], binding["cache_probe_nonce"],
                   table, result["cache"])
    final = [data_snapshot(path, table) for path in paths]
    alias_equivalent(*final)
    demand(final == initial, "public publisher changed during filesystem probe")
    result["public_data_after"] = final
    after, table_after = process_observation("self")
    result["probe_process_after"] = after
    require_credentials(after["status"], binding["uid"], binding["gid"], binding["groups"])
    # umask is deliberately stricter only for our new private file.
    before_cmp = dict(before, status={k: v for k, v in before["status"].items() if k != "Umask"})
    after_cmp = dict(after, status={k: v for k, v in after["status"].items() if k != "Umask"})
    demand(before_cmp == after_cmp and table == table_after,
           "probe process/namespace/security identity changed")
    result["all_checks_pass"] = True


def load_self(expected_hash):
    path = os.path.abspath(__file__)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        demand(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
               and not stat.S_IMODE(st.st_mode) & 0o022,
               "reviewed probe must be an immutable root-owned regular file")
        raw = read_fd(fd, 131072)
        demand(identity(st) == identity(os.fstat(fd))
               and identity(st) == identity(os.stat(path, follow_symlinks=False)),
               "reviewed probe source changed during read")
        demand(digest(raw) == expected_hash, "executing probe source digest mismatch")
        return raw
    finally:
        os.close(fd)


def bounded_child(cmd, source, result):
    """Signal only this wrapper's child; never touch a service PID or cache from root."""
    # A launch/second-signal/final-wait interruption must never imply completion.
    result["owned_probe_completion_unresolved"] = True
    result["cache_cleanup_unobserved"] = True
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=ENV, close_fds=True)
    result["owned_probe_pid"] = proc.pid
    interrupted_error = None
    try:
        stdout, stderr = proc.communicate(source, timeout=45)
    except BaseException as exc:
        interrupted_error = exc
        result["owned_probe_completion_interrupted"] = type(exc).__name__
        # SIGTERM permits the inner handler to perform its exact own-file cleanup.
        if proc.poll() is None:
            proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=7)
        except subprocess.TimeoutExpired:
            result["owned_probe_forced_kill"] = True
            result["cache_cleanup_unobserved"] = True
            if proc.poll() is None:
                proc.kill()
            stdout, stderr = proc.communicate(timeout=3)
    result["owned_probe_completion_unresolved"] = False
    result["child_exit"] = proc.returncode
    result["child_stdout_sha256"] = digest(stdout)
    result["child_stderr"] = {"bytes": len(stderr), "sha256": digest(stderr),
                              "base64": base64.b64encode(stderr).decode("ascii")}
    demand(len(stdout) <= 1024 * 1024, "inner receipt exceeds bound")
    if stdout:
        result["inner"] = json_object(stdout)
        if result["inner"].get("cache", {}).get("cleanup_complete") is True:
            result["cache_cleanup_unobserved"] = False
    demand(interrupted_error is None,
           "owned probe completion interrupted; no retry or root cleanup authorized")
    demand(proc.returncode == 0 and result.get("inner", {}).get("all_checks_pass") is True
           and result["inner"].get("errors") == [],
           "inner namespace/filesystem proof failed")


def outer_run(raw_binding, result):
    binding, post, prior_service = parse_binding(raw_binding)
    result["binding"] = {k: v for k, v in binding.items() if k != "accepted_postread_base64"}
    result["accepted_postread_observed_at"] = post.get("observed_at")
    result["accepted_runtime_record_id"] = post["runtime_accepted"]["record_summary"]["record_id"]
    demand(sys.platform.startswith("linux") and os.geteuid() == 0,
           "operational wrapper requires Linux root")
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)
    source = load_self(binding["probe_sha256"])
    unit_before = service_observation()
    result["loaded_unit_before"] = unit_before
    demand(all(unit_before[k] == prior_service[k] for k in (
        "MainPID", "ExecMainStartTimestampMonotonic", "ActiveState", "SubState", "UnitFileState")),
        "current service differs from successful postread process")
    demand(unit_before["User"] in ("terminal-beta", str(binding["uid"]))
           and unit_before["Group"] in ("", "terminal-beta", str(binding["gid"])),
           "loaded unit principal differs from bound beta identity")
    process_before, _ = process_observation(int(unit_before["MainPID"]))
    result["service_process_before"] = process_before
    require_credentials(process_before["status"], binding["uid"], binding["gid"])
    runtime_before = runtime_observation(post["runtime_accepted"])
    build_before = verify_live_build(post)
    result["runtime_before"] = runtime_before
    result["build_before"] = build_before
    result["http_before"] = status_observation(post["status"]["body"])
    # Repeat just before namespace entry; no root-opened file/dir fd is retained.
    demand(service_observation() == unit_before
           and process_observation(process_before["pid"])[0] == process_before,
           "service identity drifted before namespace entry")
    child = {"uid": binding["uid"], "gid": binding["gid"],
             "groups": process_before["status"]["Groups"],
             "process": process_before, "cache_probe_nonce": binding["cache_probe_nonce"],
             "public_relative_path": binding["public_relative_path"],
             "build_id": runtime_before["record"]["build_id"]}
    cmd = [
        "/usr/bin/nsenter", "--target", str(process_before["pid"]), "--mount",
        "--root", "--wdns=/", "--no-fork", "--",
        "/usr/bin/setpriv", "--reuid=" + str(binding["uid"]),
        "--regid=" + str(binding["gid"]),
    ]
    cmd.append("--groups=" + ",".join(map(str, child["groups"])) if child["groups"]
               else "--clear-groups")
    cmd.extend(["--inh-caps=-all", "--ambient-caps=-all", "--bounding-set=-all",
                "--no-new-privs", "--", "/usr/bin/python3", "-I", "-B", "-",
                "--inner", canonical(child).decode()])
    result["entry_options"] = {
        "nsenter": ["--target", str(process_before["pid"]), "--mount", "--root",
                    "--wdns=/", "--no-fork"],
        "uid": child["uid"], "gid": child["gid"], "groups": child["groups"],
        "capability_sets": "all zero", "no_new_privs": 1,
        "close_fds": True, "stdin_stdout_stderr": "pipes only",
        "environment_keys": sorted(ENV), "code_sha256": digest(source),
    }
    child_error = None
    try:
        bounded_child(cmd, source, result)
    except BaseException as exc:
        child_error = exc
    # Even an inner refusal receives fresh read-only stability observations.
    result["runtime_after"] = runtime_observation(post["runtime_accepted"])
    result["build_after"] = verify_live_build(post)
    result["http_after"] = status_observation(post["status"]["body"])
    result["service_process_after"], _ = process_observation(process_before["pid"])
    result["loaded_unit_after"] = service_observation()
    demand(result["runtime_after"] == runtime_before
           and result["build_after"] == build_before
           and result["service_process_after"] == process_before
           and result["loaded_unit_after"] == unit_before,
           "service/runtime/build/namespace identity changed across filesystem probe")
    result["service_stable_across_probe"] = True
    if child_error is not None:
        raise child_error
    result["all_checks_pass"] = True
    result["disposition"] = "ACCEPTED_BETA_MOUNT_ROOT_CREDENTIAL_FILESYSTEM_PASS"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    inner = len(argv) == 2 and argv[0] == "--inner"
    result = {"schema": "mastermind.attended.beta_namespace_inner.v1" if inner else
              "mastermind.attended.beta_namespace_acceptance.v1",
              "application_A": A, "reviewed_owner_sha256": OWNER_SHA,
              "started_at": now(), "all_checks_pass": False, "errors": [],
              "disposition": "UNQUALIFIED_NO_REPAIR_OR_BOOTSTRAP_AUTHORIZED",
              "scope_limits": LIMITS}
    try:
        demand(len(argv) == (2 if inner else 1), "exact JSON invocation binding required")
        if inner:
            inner_run(json_object(argv[1]), result)
        else:
            outer_run(argv[0], result)
    except BaseException as exc:
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)[:512]})
    result["finished_at"] = now()
    if not result["all_checks_pass"]:
        result["disposition"] = "UNQUALIFIED_ACCEPTED_RUNTIME_REMAINS_NO_BOOTSTRAP_AUTHORIZED"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0 if result["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
