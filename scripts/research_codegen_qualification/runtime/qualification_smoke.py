"""Corrected compact qualification-only fixed Docker smoke composition.

Loads the root-provided transport source and fixed probe after exact SHA-256
verification, injects one fixed qualification engine into the accepted
TransportOrchestrator/Session, and either emits a bounded dry-run plan (no
Docker, no subprocess) or, on the explicit root-reviewed --execute path, runs
ONE single-use known-ID attempt: binding/image/daemon/version preflight,
pre-start policy inspection, attached workload, independent state inspect and
same-ID finally cleanup.  Only the exact fixed create, exact known-CID
lifecycle argv and the two exact inspect forms are mapped; no generic
interface, no bypass.  candidate_admission/containment_qualified stay false;
configuration is not containment proof.  Host identity facts come only from
the externally SHA-bound root-approved binding file; fixed root/operation/
source/probe/image digests/platform/runtime constants stay exact constants.
"""
import argparse
import base64
import hashlib
import json
import os
import stat
import re
import sys
import time
import types

# Root-owned identity; the future commission id is rf-fixed-smoke-01a1333c-v1,
# not this correction operation.  Trusted caller data, never an authentication
# or capability service.
TRANSPORT_SHA256 = "b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633"
PROBE_SHA256 = "92fad6f371419f4cbb4bafba83257846429eae2df77feead83678905a9988cf7"
ROOT_ID = "01a1333c-a475-7052-95a8-72a88eb8c17b"
OPERATION_ID = "rf-fixed-smoke-01a1333c-v1"
CONTAINER_NAME = "rf-fixed-smoke-01a1333c-v1"
ROOT_LABEL_KEY, RUN_LABEL_KEY = "org.mastermind.root", "org.mastermind.run"
ROOT_LABEL = ROOT_LABEL_KEY + "=" + ROOT_ID
RUN_LABEL = RUN_LABEL_KEY + "=" + OPERATION_ID
DOCKER_BINARY = "/usr/bin/docker"
DOCKER_ENDPOINT = "unix:///var/run/docker.sock"
IMAGE_REF = "docker.io/library/python@sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed"
DAEMON_IMAGE_ID = "sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed"
OCI_CONFIG_DIGEST = "sha256:607dc744833974b365cc338d565e01bb76eaebe25993fe328ce185170bcd8f05"
# Fixed platform/runtime facts.  `docker info` reports the uname-style daemon
# architecture x86_64 and linux OSType; the image/version world reports Go
# arch amd64.  Distinct source-specific bindings, never substring-normalized.
EXPECTED_SERVER_VERSION = "29.1.3"
EXPECTED_PLATFORM = "linux/amd64"
DAEMON_ARCH, DAEMON_OSTYPE = "x86_64", "linux"
BINDING_SCHEMA = "rf.qualification_smoke.binding.v3"
EXPECTED_IMAGE_ENV = (
    "PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG=C.UTF-8", "GPG_KEY=A035C8C19219BA821ECEA86B64E628F8D684696D",
    "PYTHON_VERSION=3.11.17",
    "PYTHON_SHA256=bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599",
)
UID = GID = 65534
PIDS_LIMIT = 16
MEMORY_BYTES = 64 * 1024 * 1024
CPUS = 0.5
WALL_CLOCK_SECONDS = 20.0
OUTPUT_CAP_BYTES = 16 * 1024
TMPFS_BYTES = 1024 * 1024
STOP_TIMEOUT_SECONDS = 2.0
TMPFS_BASE_VALUE = "/tmp:rw,noexec,nosuid,size=%d" % TMPFS_BYTES
TMPFS_HOST_VALUE = "rw,noexec,nosuid,size=%d,mode=1777" % TMPFS_BYTES
WHOLE_ATTEMPT_BUDGET_SECONDS = 130.0
WORKLOAD_PHASE_BUDGET_SECONDS = 90.0
TOTAL_OUTPUT_CAP_BYTES = 16 * 1024
CLEANUP_RESERVE_BYTES = 4 * 1024
_CLEANUP_CMD_CAP_BYTES = 1024
_CMD_MAX = {"preflight_image": 10.0, "preflight_info": 10.0, "preflight_version": 10.0,
            "create": 20.0, "policy": 10.0, "start": 20.0, "state": 10.0, "stop": 10.0,
            "kill": 10.0, "rm": 10.0, "absence": 10.0}  # per-command ceiling seconds
_CLEANUP_KINDS = frozenset({"stop", "kill", "rm", "absence"})
_STATE_INSPECT_FORMAT = "[{{json .Id}},{{json .State}}]"
_HOST_PREFIX = (DOCKER_BINARY, "--host", DOCKER_ENDPOINT)
ANONYMOUS_CLIENT_CONFIG = b'{"auths":{"https://index.docker.io/v1/":{}}}\n'
ANONYMOUS_CLIENT_CONFIG_SHA256 = hashlib.sha256(ANONYMOUS_CLIENT_CONFIG).hexdigest()
_DRY_CLIENT_CONFIG_DIR = "/var/tmp/rf-operation-owned/docker-client"

def verify_client_config(directory, expected_sha256):
    if (type(directory) is not str or not os.path.isabs(directory)
            or len(directory) > 1024 or expected_sha256 != ANONYMOUS_CLIENT_CONFIG_SHA256):
        raise BindingMismatch("anonymous client config binding mismatch")
    meta = os.lstat(directory)
    if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.geteuid()
            or stat.S_IMODE(meta.st_mode) != 0o700):
        raise BindingMismatch("client directory must be owned0700 and not a symlink")
    if set(os.listdir(directory)) != {"config.json"}:
        raise BindingMismatch("client directory must contain only reviewed config.json")
    fd = os.open(os.path.join(directory, "config.json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                or stat.S_IMODE(meta.st_mode) != 0o600
                or meta.st_size != len(ANONYMOUS_CLIENT_CONFIG)):
            raise BindingMismatch("client config must be owned regular0600 exact bytes")
        raw = os.read(fd, len(ANONYMOUS_CLIENT_CONFIG) + 1)
        if raw != ANONYMOUS_CLIENT_CONFIG:
            raise BindingMismatch("anonymous client config bytes mismatch")
    finally:
        os.close(fd)
_POLICY_FORMAT = (
    '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},'
    '"StateRunning":{{json .State.Running}},'
    '"Cfg":{"Image":{{json .Config.Image}},"Entrypoint":{{json .Config.Entrypoint}},'
    '"Cmd":{{json .Config.Cmd}},"User":{{json .Config.User}},'
    '"WorkingDir":{{json .Config.WorkingDir}},"Env":{{json .Config.Env}},'
    '"Labels":{{json .Config.Labels}},"Healthcheck":{{json .Config.Healthcheck}}},'
    '"HC":{"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},'
    '"CapDrop":{{json .HostConfig.CapDrop}},"CapAdd":{{json .HostConfig.CapAdd}},'
    '"SecurityOpt":{{json .HostConfig.SecurityOpt}},"IpcMode":{{json .HostConfig.IpcMode}},'
    '"PidMode":{{json .HostConfig.PidMode}},"UTSMode":{{json .HostConfig.UTSMode}},'
    '"CgroupnsMode":{{json .HostConfig.CgroupnsMode}},"Privileged":{{json .HostConfig.Privileged}},'
    '"PidsLimit":{{json .HostConfig.PidsLimit}},"Memory":{{json .HostConfig.Memory}},'
    '"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},'
    '"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},'
    '"PortBindings":{{json .HostConfig.PortBindings}},"Links":{{json .HostConfig.Links}},'
    '"VolumesFrom":{{json .HostConfig.VolumesFrom}},"Devices":{{json .HostConfig.Devices}},'
    '"Binds":{{json .HostConfig.Binds}},"GroupAdd":{{json .HostConfig.GroupAdd}},'
    '"ExtraHosts":{{json .HostConfig.ExtraHosts}},"AutoRemove":{{json .HostConfig.AutoRemove}},'
    '"RestartPolicy":{{json .HostConfig.RestartPolicy}},"LogConfig":{{json .HostConfig.LogConfig}}}}'
)
# `image inspect` sees the daemon manifest Id plus the OCI image config; the
# OCIv1 ImageConfig User/WorkingDir are Go strings with omitempty, so an
# absent JSON User decodes to the typed empty string, never null.
_IMAGE_FORMAT = (
    '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Os":{{json .Os}},'
    '"Architecture":{{json .Architecture}},"Cfg":{"Entrypoint":{{json .Config.Entrypoint}},'
    '"Cmd":{{json .Config.Cmd}},"User":{{json .Config.User}},'
    '"WorkingDir":{{json .Config.WorkingDir}},"Volumes":{{json .Config.Volumes}},'
    '"Env":{{json .Config.Env}}}}'
)
# `docker info` (dockerInfo embeds *system.Info) exposes .ServerVersion,
# .OSType and .Architecture at the top level; there is no .Server object here.
_INFO_FORMAT = (
    '{"Name":{{json .Name}},"KernelVersion":{{json .KernelVersion}},'
    '"ServerVersion":{{json .ServerVersion}},"OperatingSystem":{{json .OperatingSystem}},'
    '"OSType":{{json .OSType}},"Architecture":{{json .Architecture}}}'
)
# Only `docker version` carries the .Client/.Server objects.
_VERSION_FORMAT = '{"Client":{{json .Client.Version}},"Server":{{json .Server.Version}}}'
VERDICT_SCHEMA = "rf.fixed_docker_smoke.v1"
ACTIVE_CHECKS = ("allowed_computation", "uid_gid", "minimal_environment", "readonly_root",
                 "allowed_small_scratch", "no_new_privileges", "capabilities_dropped",
                 "seccomp_present", "api_socket_absent", "public_egress")
SKIP_CHECKS = ("dns", "host_labels", "vault", "siblings", "subtree_exhaustion",
               "malicious_code_escape")
SKIP_REASON = "no_authorized_fixture_or_out_of_smoke_scope"
# Attached workload stdout/stderr never classifies a denial; only these fixed
# control commands run through the trusted classifier.
_CONTROL_VERB = {"preflight_image": "inspect", "preflight_info": "inspect",
                 "preflight_version": "inspect", "create": "create",
                 "policy": "inspect", "state": "inspect", "stop": "stop",
                 "kill": "kill", "rm": "rm", "absence": "inspect"}
_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")

class SourceContractError(Exception):
    """Typed composition refusal: source/probe/binding/verdict contract violated."""

class BindingMismatch(SourceContractError):
    """Binding file or preflight fact does not equal the single approved binding."""

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _read_verified(path: str, expected_sha: str, label: str) -> bytes:
    with open(path, "rb") as stream:
        data = stream.read()
    if _sha256(data) != expected_sha:
        raise SourceContractError("%s at %s has sha256 %s, expected pinned %s"
                                  % (label, path, _sha256(data), expected_sha))
    return data

def load_transport_module(path: str):
    """Import the exact pinned transport source bytes into a fresh module."""
    data = _read_verified(path, TRANSPORT_SHA256, "transport source")
    module = types.ModuleType("transport")
    module.__file__ = path
    sys.modules["transport"] = module  # dataclass processing needs the module registered
    exec(compile(data, path, "exec"), module.__dict__)
    return module

def build_composition(transport_path: str, probe_path: str):
    """Verify both pinned sources and build the immutable plan."""
    t = load_transport_module(transport_path)
    probe_bytes = _read_verified(probe_path, PROBE_SHA256, "fixed probe source")
    plan = t.TransportPlan(
        operation_id=OPERATION_ID, image=IMAGE_REF, entrypoint="/usr/bin/env",
        argv=("-i", "LANG=C.UTF-8", "PATH=/usr/local/bin:/usr/bin:/bin",
              "/usr/local/bin/python3", "-I", "-S", "-c", probe_bytes.decode("ascii")),
        docker_binary=DOCKER_BINARY, uid=UID, gid=GID, pids_limit=PIDS_LIMIT,
        memory_bytes=MEMORY_BYTES, cpus=CPUS,
        wall_clock_seconds=WALL_CLOCK_SECONDS, output_cap_bytes=OUTPUT_CAP_BYTES,
        tmpfs_bytes=TMPFS_BYTES, stop_timeout_seconds=STOP_TIMEOUT_SECONDS)
    return types.SimpleNamespace(t=t, plan=plan, probe_bytes=probe_bytes,
                                 probe_sha256=PROBE_SHA256,
                                 transport_sha256=TRANSPORT_SHA256)

def argv_sha256(argv) -> str:
    return _sha256(json.dumps(list(argv), separators=(",", ":"),
                              ensure_ascii=True).encode("ascii"))

class FixedQualificationEngine:
    """Narrow fixed engine interposed into the accepted orchestrator.
    Maps only the exact fixed create (name, root/run labels, tmpfs mode 1777,
    unix endpoint), exact known-CID lifecycle argv and the two exact inspect
    forms onto the fixed docker binary/endpoint.  Enforces budgets and output
    caps, binding/image/daemon/version preflight, pre-start policy inspection,
    durable known-CID receipt before start, same-ID cleanup even when caller
    receipt persistence fails or is interrupted, and freezing after any
    classified control permission refusal.  ``executor=None`` is dry-run.
    """
    policy_format = _POLICY_FORMAT
    runtime_requirement = None
    container_name = CONTAINER_NAME
    run_label = RUN_LABEL
    operation_id = OPERATION_ID
    pids_limit, memory_bytes, cpus = PIDS_LIMIT, MEMORY_BYTES, CPUS
    wall_clock_seconds = WALL_CLOCK_SECONDS
    output_cap_bytes = OUTPUT_CAP_BYTES
    tmpfs_bytes, stop_timeout_seconds = TMPFS_BYTES, STOP_TIMEOUT_SECONDS
    def __init__(self, t, plan, executor=None, cid_sink=None, binding=None):
        self._t, self._plan = t, plan
        self._executor, self._cid_sink, self._binding = executor, cid_sink, binding
        self._cid, self._frozen, self._create_issued = None, False, False
        self._t0, self._bytes_used, self.ledger = None, 0, []
        self.cid_persist_problem = None
        self.self_cleanup_confirmed = None
    @property
    def settled_cid(self):
        return self._cid
    @property
    def frozen(self):
        return self._frozen
    def set_cid_sink(self, sink):
        self._cid_sink = sink
    def _prefix(self):
        directory = (self._binding or {}).get("client_config_dir", _DRY_CLIENT_CONFIG_DIR)
        return _HOST_PREFIX + ("--config", directory)
    def effective_create_argv(self):
        base = self._t.build_create_argv(self._plan)
        sep = list(base).index("--")
        head = list(base[1:sep])
        tmpfs_index = head.index("--tmpfs")
        if head[tmpfs_index + 1] != TMPFS_BASE_VALUE:
            raise SourceContractError("unexpected base tmpfs option string")
        head[tmpfs_index + 1] = TMPFS_BASE_VALUE + ",mode=1777"
        addendum = ("--name", self.container_name,
                    "--label", ROOT_LABEL, "--label", self.run_label)
        return self._prefix() + tuple(head) + addendum + tuple(base[sep:])
    def _effective(self, argv):
        return self._prefix() + tuple(argv[1:])
    def preflight_argv_image(self):
        return self._prefix() + ("image", "inspect", "--format", _IMAGE_FORMAT, IMAGE_REF)
    def preflight_argv_info(self):
        return self._prefix() + ("info", "--format", _INFO_FORMAT)
    def preflight_argv_version(self):
        return self._prefix() + ("version", "--format", _VERSION_FORMAT)
    def policy_argv(self):
        return self._prefix() + ("inspect", "--type", "container", "--format",
                               self.policy_format, self._cid)
    def describe(self):
        plan, create = self._plan, self.effective_create_argv()
        doc = {
            "schema": "rf.qualification_smoke.dryrun.v1",
            "operation": self.operation_id, "root": ROOT_ID,
            "transport_sha256": TRANSPORT_SHA256, "probe_sha256": PROBE_SHA256,
            "plan_sha256": self._t.plan_identity(plan),
            "effective_create_argv": list(create),
            "effective_create_argv_sha256": argv_sha256(create),
            "plan_identity_stored_separately_from_effective_argv_hash": True,
            "preflight_argv_image": list(self.preflight_argv_image()),
            "preflight_argv_info": list(self.preflight_argv_info()),
            "preflight_argv_version": list(self.preflight_argv_version()),
            "create_addendum": {"name": self.container_name,
                                "labels": [ROOT_LABEL, self.run_label],
                                "tmpfs_host_value": TMPFS_HOST_VALUE,
                                "endpoint": DOCKER_ENDPOINT},
            "limits": {"uid": UID, "gid": GID, "pids_limit": self.pids_limit,
                       "memory_bytes": self.memory_bytes, "cpus": self.cpus,
                       "wall_clock_seconds": self.wall_clock_seconds,
                       "output_cap_bytes": self.output_cap_bytes,
                       "tmpfs_bytes": self.tmpfs_bytes,
                       "stop_timeout_seconds": self.stop_timeout_seconds,
                       "network": "none", "read_only_rootfs": True,
                       "cap_drop": "ALL", "no_new_privileges": True},
            "budgets": {"whole_attempt_seconds": WHOLE_ATTEMPT_BUDGET_SECONDS,
                        "workload_phase_seconds": WORKLOAD_PHASE_BUDGET_SECONDS,
                        "aggregate_output_bytes": TOTAL_OUTPUT_CAP_BYTES,
                        "cleanup_reserved_bytes": CLEANUP_RESERVE_BYTES,
                        "per_command_max_seconds": dict(_CMD_MAX)},
            "binding": {"binding_schema": BINDING_SCHEMA,
                        "required_keys": sorted(_BINDING_KEYS), "fixed_values": {"docker_endpoint": DOCKER_ENDPOINT,
                                         "expected_uid": UID, "expected_gid": GID,
                                         "docker_server_version": EXPECTED_SERVER_VERSION,
                                         "daemon_arch": DAEMON_ARCH, "ostype": DAEMON_OSTYPE},
                        "host_facts_from_root_approved_file": True,
                        "image_ref": IMAGE_REF, "daemon_image_id": DAEMON_IMAGE_ID,
                        "oci_config_digest": OCI_CONFIG_DIGEST, "platform": EXPECTED_PLATFORM},
            "selected_runtime": self.runtime_requirement,
            "execute_authorized": False, "candidate_admission": False,
            "containment_qualified": False,
        }
        doc.update(self.describe_extras())
        return doc
    def describe_extras(self):
        return {}
    def _budget(self, kind, phase, requested):
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        elapsed = now - self._t0
        remaining = WHOLE_ATTEMPT_BUDGET_SECONDS - elapsed
        if phase != "cleanup":
            remaining = min(remaining, WORKLOAD_PHASE_BUDGET_SECONDS - elapsed)
        effective = min(_CMD_MAX[kind], remaining, requested)
        if effective <= 0:
            raise self._t.TransportStateError("attempt budget exhausted before " + kind)
        return effective
    def _cap(self, kind, phase, requested):
        pool = (TOTAL_OUTPUT_CAP_BYTES if phase == "cleanup"
                else TOTAL_OUTPUT_CAP_BYTES - CLEANUP_RESERVE_BYTES) - self._bytes_used
        limit = (_CLEANUP_CMD_CAP_BYTES if phase == "cleanup"
                 else TOTAL_OUTPUT_CAP_BYTES - CLEANUP_RESERVE_BYTES)
        effective = min(pool, limit, requested)
        if effective <= 0:
            raise self._t.TransportStateError(
                "aggregate output pool exhausted before " + kind)
        return effective
    def _call(self, kind, argv, phase, requested_deadline, requested_cap):
        if self._frozen:
            raise self._t.TransportPermissionRefusal("engine frozen; no subsequent command")
        try:
            verify_client_config(self._binding.get("client_config_dir"),
                                 self._binding.get("client_config_sha256"))
        except PermissionError:
            self._frozen = True
            raise self._t.TransportPermissionRefusal("owned client config access refused") from None
        deadline = self._budget(kind, phase, requested_deadline)
        cap = self._cap(kind, phase, requested_cap)
        started = time.monotonic()
        entry = {"kind": kind, "argv_sha256": argv_sha256(argv),
                 "deadline_seconds": deadline, "cap_bytes": cap,
                 "started_offset_seconds": round(started - (self._t0 or started), 6),
                 "effective_argv": list(argv), "stdout": b"", "stderr": b""}
        self.ledger.append(entry)
        try:
            result = self._executor(argv, deadline_seconds=deadline,
                                    output_cap_bytes=cap)
        except Exception as exc:
            # A trusted local PermissionError from exec/collector is an actual
            # control refusal and freezes; any other executor crash stays typed.
            refused = isinstance(exc, PermissionError)
            entry["error_type"] = type(exc).__name__
            entry["duration_seconds"] = round(time.monotonic() - started, 6)
            self._frozen = self._frozen or refused
            return self._t.EngineCommandResult(
                None, b"", b"", deadline, cap, permission_refused=refused,
                error_type=None if refused else type(exc).__name__)
        entry["duration_seconds"] = round(time.monotonic() - started, 6)
        t = self._t
        if (type(result) is not t.EngineCommandResult
                or type(result.stdout) is not bytes or type(result.stderr) is not bytes
                or type(result.timed_out) is not bool
                or type(result.output_truncated) is not bool
                or type(result.permission_refused) is not bool
                or (result.returncode is not None and type(result.returncode) is not int)):
            entry["error_type"] = "malformed_engine_result"
            return t.EngineCommandResult(None, b"", b"", deadline, cap,
                                         error_type="malformed_engine_result")
        entry.update(returncode=result.returncode, stdout=result.stdout,
                     stderr=result.stderr, timed_out=result.timed_out,
                     output_truncated=result.output_truncated,
                     permission_refused=result.permission_refused,
                     error_type=result.error_type,
                     bytes=len(result.stdout) + len(result.stderr),
                     output_sha256=_sha256(result.stdout + result.stderr))
        self._bytes_used += entry["bytes"]
        command = _CONTROL_VERB.get(kind)
        if (command is not None and result.returncode not in (0, None)
                and t.control_permission_refusal(command, result.returncode,
                                                 result.stdout + result.stderr)):
            result = t.EngineCommandResult(
                result.returncode, result.stdout, result.stderr, deadline, cap,
                result.timed_out, result.output_truncated,
                result.observed_container_id, True, result.error_type)
            entry["permission_refused"] = True
        # An actual control refusal freezes ALL later docker calls, including
        # finally cleanup.
        self._frozen = self._frozen or result.permission_refused
        return result
    def _classify(self, argv):
        t = self._t
        if type(argv) is not tuple or len(argv) < 2 or argv[0] != DOCKER_BINARY:
            raise t.TransportPlanError("trusted Docker command binding mismatch")
        if argv == t.build_create_argv(self._plan):
            return "create", None
        if (len(argv) == 5 and argv[1:4] == ("inspect", "--type", "container")):
            return "absence", t._require_container_id(argv[4])
        if (len(argv) == 7 and argv[1:6] == ("inspect", "--type", "container",
                                             "--format", _STATE_INSPECT_FORMAT)):
            return "state", t._require_container_id(argv[6])
        builders = {"start": t.build_start_argv, "stop": t.build_stop_argv,
                    "kill": t.build_kill_argv, "rm": t.build_remove_argv}
        for kind, builder in builders.items():
            try:
                expected = builder(self._plan, t._require_container_id(argv[-1]))
            except t.TransportPlanError:
                continue
            if argv == expected:
                return kind, argv[-1]
        raise t.TransportPlanError("trusted Docker command binding mismatch")
    def _json_doc(self, result, label):
        if result.permission_refused:
            raise self._t.TransportPermissionRefusal(
                label + " permission refused; all further docker commands frozen")
        if (result.error_type is not None or result.timed_out
                or result.output_truncated or result.returncode != 0):
            raise self._t.TransportStateError(label + " unconfirmed; refused")
        try:
            return json.loads(result.stdout.decode("utf-8"))
        except Exception:
            raise self._t.TransportStateError(label + " malformed; refused") from None
    def _preflight(self):
        if type(self._binding) is not dict:
            raise BindingMismatch("execute requires the root-approved SHA-bound"
                                  " binding file")
        try:
            verify_client_config(self._binding.get("client_config_dir"),
                                 self._binding.get("client_config_sha256"))
        except PermissionError:
            self._frozen = True
            raise
        image = self._call("preflight_image", self.preflight_argv_image(),
                           "workload", 10.0, TOTAL_OUTPUT_CAP_BYTES)
        doc = self._json_doc(image, "image preflight inspection")
        cfg = doc.get("Cfg") if isinstance(doc, dict) else None
        digests = doc.get("RepoDigests") if isinstance(doc, dict) else None
        # One exact approved ref spelling only; no permissive normalization of
        # any repo ending in the same digest.  Absent OCI config User decodes
        # to the typed empty Go string, never null.
        d_cfg = lambda key: isinstance(cfg, dict) and cfg.get(key)
        checks = [("Id", doc.get("Id"), DAEMON_IMAGE_ID),
                  ("RepoDigests", isinstance(digests, list) and IMAGE_REF in digests, True),
                  ("platform", (doc.get("Os"), doc.get("Architecture")), ("linux", "amd64")),
                  ("Cfg.Entrypoint", d_cfg("Entrypoint"), None),
                  ("Cfg.Cmd", d_cfg("Cmd"), ["python3"]),
                  ("Cfg.User", d_cfg("User"), ""),  # typed empty Go string, never null
                  ("Cfg.WorkingDir", d_cfg("WorkingDir"), "/"),
                  ("Cfg.Volumes", d_cfg("Volumes"), None),
                  ("Cfg.Env", d_cfg("Env"), list(EXPECTED_IMAGE_ENV))]
        problems = [name for name, value, expected in checks if value != expected]
        if problems:
            raise BindingMismatch("selected image preflight mismatch: "
                                  + ",".join(problems))
        info = self._call("preflight_info", self.preflight_argv_info(),
                          "workload", 10.0, TOTAL_OUTPUT_CAP_BYTES)
        doc = self._json_doc(info, "daemon preflight inspection")
        b = self._binding
        if (doc.get("Name") != b["expected_hostname"]
                or doc.get("KernelVersion") != b["expected_kernel"]
                or doc.get("OperatingSystem") != b["expected_host_os"]
                or (doc.get("ServerVersion"), doc.get("OSType"),
                    doc.get("Architecture")) != (EXPECTED_SERVER_VERSION,
                                                 DAEMON_OSTYPE, DAEMON_ARCH)):
            raise BindingMismatch("daemon identity/version mismatch against"
                                  " the root-approved binding")
        version = self._call("preflight_version", self.preflight_argv_version(),
                             "workload", 10.0, TOTAL_OUTPUT_CAP_BYTES)
        doc = self._json_doc(version, "daemon version inspection")
        if (doc.get("Client") != EXPECTED_SERVER_VERSION
                or doc.get("Server") != EXPECTED_SERVER_VERSION):
            raise BindingMismatch("docker client/server version mismatch")
    def _policy_expectations(self):
        return {}
    def _policy_gate(self):
        result = self._call("policy", self.policy_argv(), "workload",
                            10.0, TOTAL_OUTPUT_CAP_BYTES)
        doc = self._json_doc(result, "pre-start policy inspection")
        if not isinstance(doc, dict) or doc.get("Id") != self._cid:
            raise self._t.TransportPlanError(
                "pre-start policy mismatch; start refused: Id-not-settled-cid")
        reason = _policy_mismatch(self._plan, doc, **self._policy_expectations())
        if reason is not None:
            raise self._t.TransportPlanError(
                "pre-start policy mismatch; start refused: " + reason)
    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        t = self._t
        if self._frozen:
            raise t.TransportPermissionRefusal(
                "engine frozen by an earlier control permission refusal;"
                " no further docker command")
        if self._executor is None:
            raise t.TransportDormantError(
                "dry-run composition: no physical executor injected;"
                " no docker effect")
        kind, cid = self._classify(argv)
        if kind == "create":
            if self._create_issued or self._cid is not None:
                raise t.TransportStateError("single-use engine: create already"
                                            " attempted; no replacement create")
            self._preflight()
            self._create_issued = True
            effective = self.effective_create_argv()
        else:
            if self._cid is None or cid != self._cid:
                raise t.TransportPlanError(
                    kind + " argv cid does not match the settled engine cid")
            effective = self._effective(argv)
            if kind == "start":
                if self.cid_persist_problem is not None:
                    raise t.TransportStateError(
                        "caller receipt for the settled container id failed ("
                        + self.cid_persist_problem + "); start blocked;"
                        " same-known-id cleanup remains required")
                self._policy_gate()
        # stop/kill/rm/absence draw from the reserved after-workload pool.
        phase = "cleanup" if kind in _CLEANUP_KINDS else "workload"
        result = self._call(kind, effective, phase, deadline_seconds, output_cap_bytes)
        if kind == "create" and result.error_type is None \
                and not result.permission_refused:
            settled = t.parse_container_id(result.stdout)
            if settled is not None:
                self._cid = settled
                if self._cid_sink is not None:
                    try:
                        self._cid_sink(settled)
                    except Exception as exc:
                        self.cid_persist_problem = type(exc).__name__
                        self._frozen = self._frozen or isinstance(exc, PermissionError)
                    except BaseException as exc:
                        # Durable caller receipt interrupted: never start, and
                        # still finish the same-known-id ordinary cleanup.
                        self.cid_persist_problem = type(exc).__name__
                        self._self_cleanup(settled)  # same exact known id
                        raise
        return result
    def _self_cleanup(self, cid):
        """Ordinary same-known-id cleanup when the caller receipt sink dies."""
        t, plan = self._t, self._plan
        def ok(result):
            return (result.error_type is None and not result.permission_refused
                    and not result.timed_out and not result.output_truncated
                    and result.returncode == 0)
        def call(kind, argv):
            return self._call(kind, self._effective(argv), "cleanup", 10.0,
                              _CLEANUP_CMD_CAP_BYTES)
        try:
            stopped = ok(call("stop", t.build_stop_argv(plan, cid)))
            if not stopped:
                stopped = ok(call("kill", t.build_kill_argv(plan, cid)))
            removed = ok(call("rm", t.build_remove_argv(plan, cid)))
            inspected = call("absence", t.build_inspect_argv(plan, cid))
            absent = (inspected.error_type is None
                      and not inspected.permission_refused
                      and not inspected.timed_out
                      and not inspected.output_truncated
                      and inspected.returncode == 1
                      and t.parse_container_absence(inspected.stdout,
                                                    inspected.stderr, cid))
            self.self_cleanup_confirmed = bool(stopped and removed and absent)
        except Exception:
            self.self_cleanup_confirmed = False
    def evidence_ledger(self):
        records = []
        for entry in self.ledger:
            record = {key: value for key, value in entry.items()
                      if key not in ("stdout", "stderr")}
            record["stdout_b64"] = base64.b64encode(entry["stdout"]).decode("ascii")
            record["stderr_b64"] = base64.b64encode(entry["stderr"]).decode("ascii")
            record["capture_mode"] = "combined_stdout_stderr" if self._executor and getattr(self._executor, "combined_capture", False) else "injected_separate_channels"
            record["output_sha256"] = entry.get(
                "output_sha256", _sha256(entry["stdout"] + entry["stderr"]))
            records.append(record)
        return records  # bounded original raw channels for independent caller review

# __TAIL2__

def _policy_mismatch(plan, doc, *, expect_name="/" + CONTAINER_NAME,
                     expect_run_label=OPERATION_ID, require_runtime=None):
    """Return None when the created container matches the fixed policy exactly.
    The document is the container's own: ``.Id`` is the known 64-hex container
    id (never the image manifest id), ``.Image`` is the exact daemon image
    manifest id and ``.Config.Image`` is the one approved fixed ref spelling.
    Everything is exact-bound, never suffix-normalized.
    """
    if not isinstance(doc, dict):
        return "document"
    doc_id = doc.get("Id")
    if (type(doc_id) is not str or _HEX64_RE.fullmatch(doc_id) is None
            or doc_id == DAEMON_IMAGE_ID):
        return "Id"
    if doc.get("Name") != expect_name or doc.get("Image") != DAEMON_IMAGE_ID:
        return "Name/Image"
    cfg, hc = doc.get("Cfg"), doc.get("HC")
    if not isinstance(cfg, dict) or not isinstance(hc, dict):
        return "Cfg/HC"
    if require_runtime is not None and hc.get("Runtime") != require_runtime:
        return "Runtime"
    cfg_expect = {"Image": IMAGE_REF, "Entrypoint": ["/usr/bin/env"],
                  "Cmd": list(plan.argv), "User": "%d:%d" % (plan.uid, plan.gid),
                  "WorkingDir": "/", "Env": list(EXPECTED_IMAGE_ENV),
                  "Labels": {ROOT_LABEL_KEY: ROOT_ID, RUN_LABEL_KEY: expect_run_label}}
    # HC numeric policy is read from the trusted immutable plan itself, so the
    # selected-runtime derivative binds its own root-reviewed canary budget.
    hc_expect = {"ReadonlyRootfs": True, "CapDrop": ["ALL"],
                 "SecurityOpt": ["no-new-privileges"], "IpcMode": "private",
                 "CgroupnsMode": "private", "Privileged": False,
                 "PidsLimit": plan.pids_limit, "Memory": plan.memory_bytes,
                 "MemorySwap": plan.memory_bytes, "NanoCpus": int(plan.cpus * 1e9),
                 "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=%d,mode=1777"
                                   % plan.tmpfs_bytes},
                 "NetworkMode": "none", "AutoRemove": False}
    for name, expected in cfg_expect.items():
        if cfg.get(name) != expected:
            return "Cfg." + name
    if doc.get("StateRunning") is not False:
        return "StateRunning"
    for name, expected in hc_expect.items():
        if hc.get(name) != expected:
            return name
    for name in ("CapAdd", "Links", "VolumesFrom", "Devices", "Binds",
                 "GroupAdd", "ExtraHosts", "PortBindings"):
        if hc.get(name) not in (None, [], {}):
            return name
    if (hc.get("PidMode") not in ("", "private")
            or hc.get("UTSMode") not in ("", "private")):
        return "Pid/UTS mode"
    restart, log = hc.get("RestartPolicy"), hc.get("LogConfig")
    if not isinstance(restart, dict) or restart.get("Name") != "no":
        return "RestartPolicy"
    if not isinstance(log, dict) or log.get("Type") != "none":
        return "LogConfig"
    health = cfg.get("Healthcheck")
    if (health is not None and (not isinstance(health, dict)
                                or health.get("Test") != ["NONE"])):
        return "Healthcheck"
    return None

def validate_verdict(t, attempt):
    """Strict single-document probe gate; admission flags stay false."""
    if type(attempt) is not t.TransportAttempt:
        raise SourceContractError("no transport attempt")
    if (attempt.state is not t.AttemptState.CLEANED_SUCCESS
            or not attempt.workload_confirmed or not attempt.cleanup_confirmed
            or attempt.execution_uncertain or attempt.reconciliation_required
            or attempt.workload_returncode != 0 or attempt.workload_problem is not None):
        raise SourceContractError("attempt is not a settled clean success")
    try:
        text = attempt.workload_output.decode("utf-8")
        verdict = json.loads(text)
    except UnicodeDecodeError:
        raise SourceContractError("workload output is not utf-8") from None
    except Exception:
        raise SourceContractError("workload output is not exactly one JSON document") from None
    canonical = json.dumps(verdict, sort_keys=True, separators=(",", ":"))
    if text not in (canonical, canonical + "\n"):
        raise SourceContractError("workload output carries extra JSON or text")
    if (type(verdict) is not dict
            or set(verdict) != {"schema", "mechanical_checks_passed",
                                "candidate_admission", "containment_qualified", "records"}
            or verdict["schema"] != VERDICT_SCHEMA
            or verdict["mechanical_checks_passed"] is not True
            or verdict["candidate_admission"] is not False
            or verdict["containment_qualified"] is not False
            or type(verdict["records"]) is not list):  # fixed envelope, admission false
        raise SourceContractError("verdict envelope violates the fixed schema")
    records = verdict["records"]
    if len(records) != len(ACTIVE_CHECKS) + len(SKIP_CHECKS):
        raise SourceContractError("verdict record count mismatch")
    for index, record in enumerate(records):
        if type(record) is not dict or "check" not in record or "status" not in record:
            raise SourceContractError("malformed verdict record")
        if index < len(ACTIVE_CHECKS):
            expected, status = ACTIVE_CHECKS[index], "PASS"
        else:
            expected, status = SKIP_CHECKS[index - len(ACTIVE_CHECKS)], "SKIP"
        keys, check = set(record), record["check"]
        if check != expected or record["status"] != status:
            raise SourceContractError("verdict record %d is not the expected %s/%s"
                                      % (index, expected, status))
        if status == "SKIP" and (keys != {"check", "status", "reason"}
                                 or record["reason"] != SKIP_REASON):
            raise SourceContractError("skip record contract violated: " + expected)
        if expected == "public_egress" and (keys != {"check", "status", "errno"}
                                            or type(record["errno"]) is not int):
            raise SourceContractError("egress record contract violated")
        if (status != "SKIP" and expected != "public_egress"
                and keys != {"check", "status", "observed"}):
            raise SourceContractError("active record contract violated: " + expected)
    return verdict
def _receipt_doc(operation, **fields):
    return dict({"schema": "rf.qualification_smoke.receipt.v1",
                 "operation": operation, "root": ROOT_ID,
                 "candidate_admission": False, "containment_qualified": False},
                **fields)

def _write_receipt(path, doc, excl, *, expected_identity=None):
    flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    flags |= (os.O_CREAT | os.O_EXCL) if excl else os.O_APPEND
    fd = os.open(path, flags, 0o600)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                or stat.S_IMODE(meta.st_mode) != 0o600):
            raise OSError("receipt must remain owned regular0600")
        identity = (meta.st_dev, meta.st_ino)
        if expected_identity is not None and identity != expected_identity:
            raise OSError("receipt inode changed; no append")
        body = (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        offset = 0
        while offset < len(body):
            written = os.write(fd, body[offset:])
            if not isinstance(written, int) or not 0 < written <= len(body) - offset:
                raise OSError("receipt write incomplete")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    current = os.stat(path, follow_symlinks=False)
    if (current.st_dev, current.st_ino) != identity:
        raise OSError("receipt locator changed after write")
    return identity

def execute_attempt(comp, engine, receipt_path):
    """Run the one single-use attempt with fresh O_EXCL receipt bookkeeping."""
    t, plan = comp.t, comp.plan
    if engine.frozen:
        raise t.TransportPermissionRefusal(
            "frozen effect: no privileged receipt publication")
    binding = getattr(engine, "_binding", None) or {}
    operation = getattr(engine, "operation_id", plan.operation_id)
    receipt_identity = _write_receipt(receipt_path, _receipt_doc(
        operation,
        phase="pre_create", plan_sha256=t.plan_identity(plan),
        transport_sha256=TRANSPORT_SHA256, probe_sha256=PROBE_SHA256,
        image_receipt_sha256=binding.get("image_receipt_sha256"),
        image_adjudication_sha256=binding.get("image_adjudication_sha256"),
        whole_attempt_budget_seconds=WHOLE_ATTEMPT_BUDGET_SECONDS,
        workload_phase_budget_seconds=WORKLOAD_PHASE_BUDGET_SECONDS,
        aggregate_output_cap_bytes=TOTAL_OUTPUT_CAP_BYTES,
        cleanup_reserved_bytes=CLEANUP_RESERVE_BYTES), excl=True)
    def sink(cid):
        _write_receipt(receipt_path, _receipt_doc(
            operation, phase="container_id_settled", container_id=cid), excl=False,
                       expected_identity=receipt_identity)
    engine.set_cid_sink(sink)
    try:
        attempt = t.TransportOrchestrator(engine).execute(t.TransportSession(plan))
    except BaseException as exc:
        # The caller keeps the original exception and partial state even when
        # this interrupted-receipt write itself fails; never mask it.
        if not engine.frozen:
            try:
                _write_receipt(receipt_path, _receipt_doc(
                    operation,
                    phase="attempt_interrupted", exception_type=type(exc).__name__,
                    engine_settled_container_id=engine.settled_cid,
                    cid_persist_problem=engine.cid_persist_problem,
                    self_cleanup_confirmed=engine.self_cleanup_confirmed,
                    engine_ledger=engine.evidence_ledger()), excl=False,
                               expected_identity=receipt_identity)
            except Exception:
                pass
        raise
    if engine.frozen:
        # Keep the prior durable receipt and original engine state. The caller's
        # existing stdout return can carry failure facts without another write.
        raise t.TransportPermissionRefusal(
            "frozen effect: settlement receipt publication refused")
    # The settled receipt is the durable caller record; if this write fails
    # the OSError propagates truthfully after cleanup already settled.
    workload_raw = attempt.workload_output[:TOTAL_OUTPUT_CAP_BYTES]
    _write_receipt(receipt_path, _receipt_doc(
        operation,
        phase="attempt_settled", container_id=attempt.container_id,
        state=attempt.state.value,
        workload_confirmed=attempt.workload_confirmed,
        workload_returncode=attempt.workload_returncode,
        workload_output_b64=base64.b64encode(workload_raw).decode("ascii"),
        workload_output_sha256=_sha256(attempt.workload_output),
        workload_problem=attempt.workload_problem,
        execution_uncertain=attempt.execution_uncertain,
        cleanup_confirmed=attempt.cleanup_confirmed,
        reconciliation_required=attempt.reconciliation_required,
        detail=attempt.detail, cid_persist_problem=engine.cid_persist_problem,
        engine_ledger=engine.evidence_ledger()), excl=False,
                           expected_identity=receipt_identity)
    return attempt
def _real_executor(t):
    def executor(argv, *, deadline_seconds, output_cap_bytes):
        captured = t.collect_process(argv, deadline_seconds=deadline_seconds,
                                     output_cap_bytes=output_cap_bytes)
        command = (argv[5] if len(argv) > 5 and argv[:3] == _HOST_PREFIX
                   and argv[3] == "--config" else "")
        # Local typed collector failure is authoritative even for attached start.
        refused = captured.error_type == "PermissionError"
        if command in {"create", "stop", "kill", "rm", "inspect", "image", "info", "version"}:
            verb = "inspect" if command in {"image", "info", "version"} else command
            refused = refused or t.control_permission_refusal(verb, captured.returncode, captured.output)
            if captured.returncode == 0:
                # Docker29 info may write this trusted error while returning rc0.
                # No attached workload or JSON field contents are scanned.
                markers = (b"permission denied", b"access denied", b"authorization denied",
                           b"unauthorized", b"forbidden", b"not authorized")
                refused = refused or any(line.startswith(b"Error response from daemon: ")
                    and any(marker in line.lower() for marker in markers)
                    for line in captured.output.split(b"\n"))
        observed = (t.parse_container_id(captured.output)
                    if command == "create" else None)
        return t.EngineCommandResult(
            captured.returncode, captured.output, b"", deadline_seconds,
            output_cap_bytes, captured.timed_out, captured.output_truncated,
            observed_container_id=observed, permission_refused=refused,
            error_type=captured.error_type)
    executor.combined_capture = True
    return executor

_BINDING_KEYS = frozenset({
    "binding_schema", "expected_hostname", "expected_uid", "expected_gid",
    "expected_kernel", "expected_host_os", "daemon_arch", "ostype",
    "docker_endpoint", "docker_server_version", "image_receipt_sha256",
    "image_adjudication_sha256", "client_config_dir", "client_config_sha256"})

def load_binding_file(path, binding_sha256):
    """Load the SHA-bound root-approved host binding (trusted caller data,
    never an authentication or capability)."""
    data = _read_verified(path, binding_sha256, "root-approved binding file")
    try:
        doc = json.loads(data.decode("utf-8"))
    except Exception:
        raise BindingMismatch("binding file is not one JSON document") from None
    if type(doc) is not dict or set(doc) != _BINDING_KEYS:
        raise BindingMismatch("binding file schema is not the closed root-approved"
                              " binding schema " + BINDING_SCHEMA)
    fixed = {"binding_schema": BINDING_SCHEMA, "expected_uid": UID,
             "expected_gid": GID, "docker_endpoint": DOCKER_ENDPOINT,
             "docker_server_version": EXPECTED_SERVER_VERSION,
             "daemon_arch": DAEMON_ARCH, "ostype": DAEMON_OSTYPE}
    for key, value in fixed.items():
        if doc[key] != value:
            raise BindingMismatch("binding %s conflicts with the fixed root constant %r"
                                  % (key, value))
    for key in ("expected_hostname", "expected_kernel", "expected_host_os"):
        value = doc[key]
        if (type(value) is not str or not value or len(value) > 128
                or any(not 0x20 <= ord(char) <= 0x7E for char in value)):
            raise BindingMismatch("binding %s is not a bounded printable host fact" % key)
    if (type(doc["client_config_dir"]) is not str or not os.path.isabs(doc["client_config_dir"])
            or len(doc["client_config_dir"]) > 1024
            or doc["client_config_sha256"] != ANONYMOUS_CLIENT_CONFIG_SHA256):
        raise BindingMismatch("anonymous client config binding mismatch")
    for key in ("image_receipt_sha256", "image_adjudication_sha256"):
        if type(doc[key]) is not str or _HEX64_RE.fullmatch(doc[key]) is None:
            raise BindingMismatch("binding %s is not a settled sha256 hash" % key)
    return doc
def _emit(doc, stream=None):
    print(json.dumps(doc, sort_keys=True, separators=(",", ":")), file=stream)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("--transport", "--probe", "--binding", "--binding-sha256",
                 "--receipt"):
        parser.add_argument(flag, default=None)
    parser.add_argument("--execute", action="store_true",
                        help="root-reviewed physical smoke-only path")
    args = parser.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    transport_path = args.transport or os.path.join(here, "transport.py")
    probe_path = args.probe or os.path.join(here, "fixed_smoke_probe.py")
    engine = None
    try:
        comp = build_composition(transport_path, probe_path)
        if not args.execute:
            _emit(_dry_run(comp))
            return 0
        if not args.binding or not args.binding_sha256 or not args.receipt:
            _emit({"refusal": "ExecuteGateIncomplete",
                   "detail": "execute requires --binding, --binding-sha256"
                             " and --receipt", "candidate_admission": False,
                   "containment_qualified": False}, sys.stderr)
            return 2
        binding = load_binding_file(args.binding, args.binding_sha256)
        engine = FixedQualificationEngine(comp.t, comp.plan,
                                          executor=_real_executor(comp.t),
                                          binding=binding)
        attempt = execute_attempt(comp, engine, args.receipt)
        verdict = validate_verdict(comp.t, attempt)
        _emit({"operation": OPERATION_ID, "container_id": attempt.container_id,
               "mechanical_checks_passed": True, "candidate_admission": False,
               "containment_qualified": False,
               "verdict_schema": verdict["schema"]})
        return 0
    except BaseException as exc:
        _emit({"refusal": type(exc).__name__, "detail": str(exc),
               "known_container_id": engine.settled_cid if engine is not None else None,
               "self_cleanup_confirmed": engine.self_cleanup_confirmed if engine is not None else None,
               "candidate_admission": False, "containment_qualified": False},
              sys.stderr)
        if not isinstance(exc, Exception):
            raise
        return 2
def _dry_run(comp):
    return FixedQualificationEngine(comp.t, comp.plan, executor=None).describe()

if __name__ == "__main__":
    sys.exit(main())
