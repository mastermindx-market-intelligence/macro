"""Pure plans for seven pinned, trusted containment-qualification workloads.

No payload is imported or executed here. A plan is not an execution grant, and
these planned limits are not evidence of host enforcement. The general Docker
engine remains dormant; a separately admitted caller must select rf-runsc and
provide trusted host observations, supervision and cleanup before adjudication.
"""
import hashlib
from types import MappingProxyType

from engine.research_codegen import transport


SOURCE_PINS = MappingProxyType({
    "w01": (4032, "1b6f8bc7729804a8fd0eaed02f2d19cf8b82b5893bc45ac522dab1ae8d13edc3"),
    "w02": (2600, "a8720d83173292d4fa59ea2c8e04ad1c911b2d103bb9eff1f68c5cb468d7ac57"),
    "w03": (3140, "f8e1d6f2d4a7bd44c7abe7cf6ea1affd8b11a295ef2484397485ab9f3b623098"),
    "w04": (2982, "454af2f25905afea25ab7aec1d00a5096531078fccae410d9b8bc1b2b51d596e"),
    "w05": (3314, "a9b44deacc6c002b9eb1a190f048c433f34ce4ee1a4b20bbdb211d12d87af222"),
    "w06": (4085, "b02a99c46a12f006e110c886ad672a8a15b18a0a1ac242e6e38fe802c7aee8d7"),
    "w07": (2660, "0d8205428e4a6c26275b3207b90c02579d7cb1d455106fa5fab4a025e02c71e1"),
})
IMAGE = "docker.io/library/python@sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed"
RUNTIME = "rf-runsc"
WHOLE_ATTEMPT_SECONDS = 120.0
CLEANUP_RESERVE_SECONDS = 30.0
SERIAL_SEVEN_ATTEMPT_SECONDS = 840.0
REQUIRED_TRANSPORT_SHA256 = "b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633"


class WorkloadPlanRefused(ValueError):
    """Input is outside the closed trusted-workload contract."""


def _fixed_fields(case_id, source_bytes):
    """Validate inert input and return fields without consulting a lifecycle."""
    if type(case_id) is not str or case_id not in SOURCE_PINS:
        raise WorkloadPlanRefused("unknown fixed workload case")
    size, digest = SOURCE_PINS[case_id]
    # Bound before hashing, and refuse subclasses without invoking user methods.
    if type(source_bytes) is not bytes or len(source_bytes) != size:
        raise WorkloadPlanRefused("fixed workload source type or size mismatch")
    if hashlib.sha256(source_bytes).hexdigest() != digest:
        raise WorkloadPlanRefused("fixed workload source digest mismatch")
    return dict(
        operation_id="rf-containment-" + case_id + "-01a1333c-v1",
        image=IMAGE,
        docker_binary="/usr/bin/docker",
        entrypoint="/usr/bin/env",
        argv=("-i", "LANG=C.UTF-8", "PATH=/usr/local/bin:/usr/bin:/bin",
              "/usr/local/bin/python3", "-I", "-S", "-c", source_bytes.decode("ascii")),
        uid=65534, gid=65534, pids_limit=128, memory_bytes=268435456,
        cpus=0.5, wall_clock_seconds=5.0, output_cap_bytes=65536,
        tmpfs_bytes=8388608, stop_timeout_seconds=2.0,
    )


def build_workload_plan(case_id, source_bytes):
    """Return a fixed plan only for the exact case and committed source bytes."""
    return transport.TransportPlan(**_fixed_fields(case_id, source_bytes))


def describe_workload(case_id, source_bytes):
    """Return source/plan identity and outstanding obligations, never payload."""
    plan = build_workload_plan(case_id, source_bytes)
    return _describe_plan(case_id, plan, transport)


def _describe_plan(case_id, plan, lifecycle):
    size, digest = SOURCE_PINS[case_id]
    return {
        "case_id": case_id,
        "source_sha256": digest,
        "source_bytes": size,
        "operation_id": plan.operation_id,
        "plan_sha256": lifecycle.plan_identity(plan),
        # This pure factory declares a requirement; the execution composition
        # must load those exact bytes before claiming a verified lifecycle.
        "required_transport_sha256": REQUIRED_TRANSPORT_SHA256,
        "runtime": RUNTIME,
        "whole_attempt_seconds": WHOLE_ATTEMPT_SECONDS,
        "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
        "serial_seven_attempt_ceiling_seconds": SERIAL_SEVEN_ATTEMPT_SECONDS,
        "candidate_admission": False,
        "containment_qualified": False,
        "execute_authorized": False,
        "still_required": (
            "fixture_listener", "trusted_host_resource_mapping",
            "complete_helper_census", "cleanup_observations",
            "installed_runtime_check", "outer_supervision", "execution_grant",
        ),
    }
