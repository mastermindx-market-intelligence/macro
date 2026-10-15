"""Fixed selected-runtime derivative: the same smoke under rf-runsc only.

Tiny fixed frontend/composition preset over qualification_smoke.  It inserts
exactly one ``--runtime=rf-runsc`` token into the fixed create argv and
requires ``HostConfig.Runtime == "rf-runsc"`` in the pre-start policy document
before start.  No envelope/candidate runtime, path or flags, no dormant
general engine activation, and no installer code: the pending
rf-runsc-installer draft stays a separate incumbent operation.  The derivative
binds the complete installed six-file bundle member hashes and the exact
config hash/consumer mapping/actual host from a root-reviewed same-operation
installer receipt, and verifies the fixed consumer-path bytes and the current
config hash privately before create (in a future commission); no file body
and no other config value ever reaches the output.  An empty, placeholder or
unconfirmed manifest stops before any Docker mutation.

Installed runsc Sentry/Gofer resource accounting is host-side and is not
independently attested by guest /proc or dmesg; this smoke proves only the
fixed guest checks and never claims candidate capacity, and installed
runtime/guest dmesg/proc alone is not independent S02 attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import time
import sys

import qualification_smoke as qsm

OPERATION_ID = "rf-fixed-smoke-runsc-01a1333c-v4"
CONTAINER_NAME = "rf-fixed-smoke-runsc-01a1333c-v4"
RUN_LABEL = qsm.RUN_LABEL_KEY + "=" + OPERATION_ID
RUNTIME_NAME = "rf-runsc"
RUNTIME_FLAG = "--runtime=" + RUNTIME_NAME
RUNTIME_ARGS = ("--platform=systrap", "--network=none", "--oci-seccomp")
CONSUMER_PATH = "/usr/local/lib/mastermind/research-factory/runsc/20261005.0/runsc"
ARCHIVE_SHA256 = "bd4eb2ca0ee74f0fbbb5f5273ba011e79c56a29fbb047393b88b981cd3230ede"
RUNSC_BINARY_SHA256 = "210b437a9cfae51e8f8c9074ed19b8b5e59477178e2e391a18117d8d6b924f7a"
PIN_ADJUDICATION_SHA256 = "d470b91e5699529ccca008beb3d1b174c344f9c2762b3fc9316c80f84ce6e6f6"
MANIFEST_SCHEMA = "rf.qualification_runsc.installer_receipt.v1"
# Exact installed byte sizes; member hashes come only from the accepted
# same-operation archive/install receipt (no fresh download in this repair).
MEMBER_SPECS = {
    "runsc": 109966750,
    "gvisor-bin/checkpointgofer": 69128994,
    "gvisor-bin/gvisor-sentry-prewarmer": 1416,
    "gvisor-bin/gvisor_sentry": 52149808,
    "gvisor-bin/runsc-fd-parking": 1320,
    "gvisor-bin/runsc-metric-server": 53222722,
}
# Root-reviewed runsc canary budget (never a candidate-capacity claim).
PIDS_LIMIT = 64
MEMORY_BYTES = 256 * 1024 * 1024
CPUS = 0.5
WALL_CLOCK_SECONDS = 30.0
TMPFS_BYTES = 1024 * 1024
STOP_TIMEOUT_SECONDS = 2.0

# Consumer-only oci-seccomp: release flags.go registers it false by default,
# while guest proc task_files.go emits NoNewPrivs/task.SeccompMode and CapEff.
# Enabling it here explicitly preserves the fixed probe's guest Seccomp 2
# expectation; host Sentry filters remain a separate proof.
_RUNSC_POLICY_FORMAT = qsm._POLICY_FORMAT.replace(
    '"HC":{', '"HC":{"Runtime":{{json .HostConfig.Runtime}},', 1)
ACCOUNTING_LIMITATION = ("runsc Sentry/Gofer resource accounting is host-side and"
                         " not independently attested by guest /proc or dmesg;"
                         " no candidate-capacity claim")
S02_NOTE = "installed runtime/guest dmesg/proc alone is not independent S02 attestation"


class RunscQualificationEngine(qsm.FixedQualificationEngine):
    """Base fixed engine plus exactly one create token and one policy field."""

    policy_format = _RUNSC_POLICY_FORMAT
    runtime_requirement = RUNTIME_NAME
    container_name = CONTAINER_NAME
    run_label = RUN_LABEL
    operation_id = OPERATION_ID
    pids_limit, memory_bytes, cpus = PIDS_LIMIT, MEMORY_BYTES, CPUS
    wall_clock_seconds = WALL_CLOCK_SECONDS
    output_cap_bytes = qsm.OUTPUT_CAP_BYTES
    tmpfs_bytes, stop_timeout_seconds = TMPFS_BYTES, STOP_TIMEOUT_SECONDS

    def effective_create_argv(self):
        base = super().effective_create_argv()
        position = len(self._prefix())
        if base[position] != "create":
            raise qsm.SourceContractError("unexpected base create argv head")
        return base[:position + 1] + (RUNTIME_FLAG,) + base[position + 1:]

    def _policy_expectations(self):
        return {"require_runtime": RUNTIME_NAME, "expect_name": "/" + CONTAINER_NAME,
                "expect_run_label": OPERATION_ID}

    def describe_extras(self):
        return {"selected_runtime": RUNTIME_NAME,
                "runtime_flag": RUNTIME_FLAG, "runtime_args": list(RUNTIME_ARGS),
                "consumer_path": CONSUMER_PATH, "manifest_schema": MANIFEST_SCHEMA,
                "member_specs_bytes": dict(MEMBER_SPECS),
                "archive_sha256": ARCHIVE_SHA256,
                "runsc_binary_sha256": RUNSC_BINARY_SHA256,
                "pin_adjudication_sha256": PIN_ADJUDICATION_SHA256,
                "accounting_limitation": ACCOUNTING_LIMITATION,
                "s02_note": S02_NOTE,
                "installer_operation": "rf-runsc-installer-draft-01a137ac-v1"
                                       " (separate incumbent; no install code here)"}


def build_runsc_composition(transport_path: str, probe_path: str):
    """Same pinned sources, runsc canary budget plan."""
    comp = qsm.build_composition(transport_path, probe_path)
    t = comp.t
    plan = t.TransportPlan(
        operation_id=OPERATION_ID, image=qsm.IMAGE_REF, entrypoint="/usr/bin/env",
        argv=("-i", "LANG=C.UTF-8", "PATH=/usr/local/bin:/usr/bin:/bin",
              "/usr/local/bin/python3", "-I", "-S", "-c",
              comp.probe_bytes.decode("ascii")),
        docker_binary=qsm.DOCKER_BINARY, uid=qsm.UID, gid=qsm.GID,
        pids_limit=PIDS_LIMIT, memory_bytes=MEMORY_BYTES, cpus=CPUS,
        wall_clock_seconds=WALL_CLOCK_SECONDS,
        output_cap_bytes=qsm.OUTPUT_CAP_BYTES, tmpfs_bytes=TMPFS_BYTES,
        stop_timeout_seconds=STOP_TIMEOUT_SECONDS)
    comp.plan = plan
    return comp


def _manifest_problem(manifest, binding):
    """Return None only for the exact closed installer receipt contract."""
    required = {"manifest_schema", "root", "installer_operation", "archive_sha256",
                "consumer_path", "runtime_name", "runtime_args", "config_path",
                "config_sha256", "actual_hostname", "status", "members",
                "pin_adjudication_sha256"}
    if type(manifest) is not dict or set(manifest) != required:
        return "schema"
    if manifest["manifest_schema"] != MANIFEST_SCHEMA:
        return "manifest_schema"
    if manifest["root"] != qsm.ROOT_ID or manifest["status"] != "installed":
        return "root/status"
    if manifest["archive_sha256"] != ARCHIVE_SHA256:
        return "archive_sha256"
    if manifest["consumer_path"] != CONSUMER_PATH:
        return "consumer_path"
    if manifest["runtime_name"] != RUNTIME_NAME or tuple(
            manifest["runtime_args"]) != RUNTIME_ARGS:
        return "runtime mapping"
    if manifest["pin_adjudication_sha256"] != PIN_ADJUDICATION_SHA256:
        return "pin_adjudication_sha256"
    if manifest["config_path"] != "/etc/docker/daemon.json":
        return "config_path"
    members = manifest["members"]
    if type(members) is not dict or set(members) != set(MEMBER_SPECS):
        return "members"
    for name, spec in MEMBER_SPECS.items():
        member = members[name]
        if type(member) is not dict or set(member) != {"size", "sha256"}:
            return "member " + name
        if member["size"] != spec:
            return "member size " + name
        digest = member["sha256"]
        if type(digest) is not str or qsm._HEX64_RE.fullmatch(digest) is None \
                or set(digest) == {"0"}:
            return "member sha256 " + name  # placeholder digests never pass
    if members["runsc"]["sha256"] != RUNSC_BINARY_SHA256:
        return "runsc binary sha256"
    if (type(manifest["config_sha256"]) is not str
            or qsm._HEX64_RE.fullmatch(manifest["config_sha256"]) is None
            or manifest["config_sha256"] == "0" * 64):
        return "config digest"
    if (type(manifest["actual_hostname"]) is not str or not manifest["actual_hostname"]
            or len(manifest["actual_hostname"]) > 128
            or type(manifest["installer_operation"]) is not str
            or not manifest["installer_operation"] or len(manifest["installer_operation"]) > 128):
        return "host/operation"
    if binding is not None and manifest["actual_hostname"] != binding["expected_hostname"]:
        return "actual host"
    return None


def load_installer_manifest(path, manifest_sha256, binding):
    """Load the SHA-bound same-operation installer receipt; refuse anything else."""
    data = qsm._read_verified(path, manifest_sha256, "installer receipt")
    try:
        manifest = json.loads(data.decode("utf-8"))
    except Exception:
        raise qsm.SourceContractError("installer receipt is not one JSON document") from None
    problem = _manifest_problem(manifest, binding)
    if problem is not None:
        raise qsm.SourceContractError(
            "installer receipt is empty, placeholder or unconfirmed: " + problem)
    return manifest


def _sha256_file(path, size, deadline, *, config=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or meta.st_gid != 0
                or stat.S_IMODE(meta.st_mode) != (0o644 if config else 0o755)
                or (meta.st_size > size if config else meta.st_size != size)):
            raise qsm.SourceContractError("fixed installed file metadata mismatch")
        digest, count = hashlib.sha256(), 0
        while True:
            if time.monotonic() > deadline:
                raise qsm.SourceContractError("private bundle verification deadline")
            chunk = os.read(fd, min(65536, meta.st_size - count + 1))
            if not chunk:
                break
            count += len(chunk)
            if count > meta.st_size:
                raise qsm.SourceContractError("installed file grew during verification")
            digest.update(chunk)
        final = os.fstat(fd)
        if (count != meta.st_size or (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns)):
            raise qsm.SourceContractError("installed file changed during verification")
        return digest.hexdigest()
    finally:
        os.close(fd)


def verify_installed_bundle(manifest):
    """Bounded private check of the complete exact six-file installed unit."""
    if _manifest_problem(manifest, None) is not None:
        raise qsm.SourceContractError("unconfirmed closed installer manifest")
    root = os.path.dirname(CONSUMER_PATH)
    deadline = time.monotonic() + 15
    for directory, names in ((root, {"runsc", "gvisor-bin"}),
            (os.path.join(root, "gvisor-bin"), {name.split("/", 1)[1]
                for name in MEMBER_SPECS if name != "runsc"})):
        meta = os.lstat(directory)
        if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != 0 or meta.st_gid != 0
                or stat.S_IMODE(meta.st_mode) != 0o755 or set(os.listdir(directory)) != names):
            raise qsm.SourceContractError("complete version directory metadata/member-set mismatch")
    for name, size in MEMBER_SPECS.items():
        if _sha256_file(os.path.join(root, name), size, deadline) != manifest["members"][name]["sha256"]:
            raise qsm.SourceContractError("installed bundle member hash mismatch: " + name)
    if _sha256_file("/etc/docker/daemon.json", 262144, deadline, config=True) != manifest["config_sha256"]:
        raise qsm.SourceContractError("current daemon config hash differs from installer receipt")


def _emit(doc, stream=None):
    print(json.dumps(doc, sort_keys=True, separators=(",", ":")), file=stream)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("--transport", "--probe", "--binding", "--binding-sha256",
                 "--receipt", "--installer-receipt", "--installer-receipt-sha256"):
        parser.add_argument(flag, default=None)
    parser.add_argument("--execute", action="store_true",
                        help="root-reviewed physical runsc smoke-only path")
    parser.add_argument("--verify-installed", action="store_true",
                        help="privately verify installed bytes/config hash, no Docker")
    args = parser.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    transport_path = args.transport or os.path.join(here, "transport.py")
    probe_path = args.probe or os.path.join(here, "fixed_smoke_probe.py")
    engine = None
    try:
        comp = build_runsc_composition(transport_path, probe_path)
        if not args.execute and not args.verify_installed:
            _emit(RunscQualificationEngine(comp.t, comp.plan).describe())
            return 0
        if not (args.binding and args.binding_sha256 and args.installer_receipt
                and args.installer_receipt_sha256):
            _emit({"refusal": "RunscGateIncomplete",
                   "detail": "requires --binding, --binding-sha256,"
                             " --installer-receipt and --installer-receipt-sha256",
                   "candidate_admission": False, "containment_qualified": False},
                  sys.stderr)
            return 2
        binding = qsm.load_binding_file(args.binding, args.binding_sha256)
        manifest = load_installer_manifest(args.installer_receipt,
                                           args.installer_receipt_sha256, binding)
        verify_installed_bundle(manifest)
        if args.verify_installed and not args.execute:
            _emit({"operation": OPERATION_ID, "installed_bundle_verified": True,
                   "consumer_path": CONSUMER_PATH, "runtime_name": RUNTIME_NAME,
                   "runtime_args": list(RUNTIME_ARGS),
                   "candidate_admission": False, "containment_qualified": False})
            return 0
        if not args.receipt:
            _emit({"refusal": "RunscGateIncomplete", "detail": "--receipt required",
                   "candidate_admission": False, "containment_qualified": False},
                  sys.stderr)
            return 2
        engine = RunscQualificationEngine(comp.t, comp.plan,
                                          executor=qsm._real_executor(comp.t),
                                          binding=binding)
        attempt = qsm.execute_attempt(comp, engine, args.receipt)
        verdict = qsm.validate_verdict(comp.t, attempt)
        _emit({"operation": OPERATION_ID, "container_id": attempt.container_id,
               "selected_runtime": RUNTIME_NAME, "mechanical_checks_passed": True,
               "candidate_admission": False, "containment_qualified": False,
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

if __name__ == "__main__":
    sys.exit(main())
