"""Pure decoder for two different runsc identity records; no host reads or calls.

Contract source: gVisor 97e8e896904cb364319cd9758241d3f0bd27a6f4.
OCI state exposes one sandbox PID. The internal Container record separately
exposes sandbox.pid, goferPid and sandbox.cgroup. Neither declares a complete
helper census or proves current kernel identity, exclusive custody or cleanup.
This module is not part of the commissioned fixed-canary capsule.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re

SOURCE_CONTRACT_COMMIT = "97e8e896904cb364319cd9758241d3f0bd27a6f4"
MAX_RECORD_BYTES = 131072


class IdentityRefused(ValueError):
    pass


def _check(condition, reason):
    if not condition:
        raise IdentityRefused(reason)


def _pairs(items):
    result = {}
    for key, value in items:
        _check(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _float(text):
    value = float(text)
    _check(math.isfinite(value), "nonfinite_json")
    return value


def _decode(raw):
    _check(type(raw) is bytes and 0 < len(raw) <= MAX_RECORD_BYTES,
           "record_bound")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_float,
                         parse_constant=lambda _: _check(False, "nonfinite_json"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, IdentityRefused):
            raise
        raise IdentityRefused("record_json") from None
    _check(type(doc) is dict, "record_object")
    return doc


def _container_id(value):
    _check(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value),
           "exact_container_id")
    return value


def state_basename(container_id):
    """Exact single-container filename, never a root path, lookup or glob."""
    cid = _container_id(container_id)
    return cid + "_sandbox:" + cid + ".state"


@dataclass(frozen=True)
class DeclaredIdentity:
    container_id: str
    sandbox_pid: int
    gofer_pid: int | None
    status: str
    cgroup_kind: str
    cgroup_descriptor_sha256: str
    oci_state_sha256: str
    internal_metadata_sha256: str
    source_contract_commit: str = SOURCE_CONTRACT_COMMIT
    host_observed: bool = False
    helper_census_complete: bool = False
    cleanup_proven: bool = False


def decode_identity(oci_raw, metadata_raw, *, expected_container_id):
    """Join declared identities only, for the fixed single-container use case.

    A caller still owes authenticated capture, installed-source and runtime-root
    binding, PID start identity, executable/cgroup observations and an independent
    helper census. Stopped/missing state never means cleanup has been proved.
    No runtime root is guessed and no descriptor-selected path is accessed.
    """
    cid = _container_id(expected_container_id)
    oci, metadata = _decode(oci_raw), _decode(metadata_raw)
    _check(set(oci) in ({"ociVersion", "id", "status", "pid", "bundle"},
                       {"ociVersion", "id", "status", "pid", "bundle", "annotations"}),
           "oci_state_fields")
    _check(type(oci["ociVersion"]) is str and 0 < len(oci["ociVersion"]) <= 32,
           "oci_version_shape")
    _check(type(oci["bundle"]) is str and oci["bundle"].startswith("/"),
           "oci_bundle_shape")
    _check(oci["id"] == cid and metadata.get("id") == cid, "container_identity")
    sandbox = metadata.get("sandbox")
    _check(type(sandbox) is dict and sandbox.get("id") == cid,
           "single_container_sandbox_identity")
    status = oci["status"]
    _check(type(status) is str and status in ("created", "running", "paused")
           and metadata.get("status") == status, "live_declared_status")
    pid, gofer = oci["pid"], metadata.get("goferPid")
    _check(type(pid) is int and 0 < pid < 2**31
           and type(sandbox.get("pid")) is int and sandbox["pid"] == pid,
           "sandbox_pid_identity")
    _check(type(gofer) is int and 0 <= gofer < 2**31 and gofer != pid,
           "gofer_pid_shape")
    # This descriptor is opaque. CompatCgroup is deliberately not substituted:
    # its limits do not control a multi-container sandbox's resources.
    cgroup = sandbox.get("cgroup")
    _check(type(cgroup) is dict and len(cgroup) == 1, "cgroup_descriptor")
    kind = next(iter(cgroup))
    _check(kind in ("cgroupv1", "cgroupv2", "cgroupsystemd", "cgroupunknown"),
           "cgroup_descriptor_kind")
    _check(cgroup[kind] is None if kind == "cgroupunknown"
           else type(cgroup[kind]) is dict and bool(cgroup[kind]),
           "cgroup_descriptor_value")
    descriptor = json.dumps(cgroup, sort_keys=True, separators=(",", ":"),
                            allow_nan=False).encode("utf-8")
    return DeclaredIdentity(cid, pid, gofer or None, status, kind,
                            hashlib.sha256(descriptor).hexdigest(),
                            hashlib.sha256(oci_raw).hexdigest(),
                            hashlib.sha256(metadata_raw).hexdigest())
