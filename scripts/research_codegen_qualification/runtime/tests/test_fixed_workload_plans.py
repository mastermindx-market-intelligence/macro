"""Pinned workload bytes are inert data throughout these source tests."""
import dataclasses
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from engine.research_codegen import transport
import fixed_workload_plans as plans

WORKLOADS = Path(__file__).parents[2]
SOURCES = {
    "w01": "w01_boundary.py", "w02": "w02_cpu_deadline.py",
    "w03": "w03_output_cap.py", "w04": "w04_memory_limit.py",
    "w05": "w05_process_limit.py", "w06": "w06_scratch_limit.py",
    "w07": "w07_fresh_recovery.py",
}


@pytest.fixture(autouse=True)
def no_host_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("host effect forbidden in plan tests")
    for obj, attr in ((subprocess, "Popen"), (socket, "socket"),
                      (os, "system"), (os, "fork")):
        monkeypatch.setattr(obj, attr, forbidden)


@pytest.mark.parametrize("case", SOURCES)
def test_exact_source_fixed_plan_and_description(case):
    raw = (WORKLOADS / SOURCES[case]).read_bytes()
    plan = plans.build_workload_plan(case, raw)
    assert type(plan) is transport.TransportPlan
    assert dataclasses.asdict(plan) == {
        "operation_id": "rf-containment-" + case + "-01a1333c-v1",
        "image": "docker.io/library/python@sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed",
        "entrypoint": "/usr/bin/env", "docker_binary": "/usr/bin/docker",
        "argv": ("-i", "LANG=C.UTF-8", "PATH=/usr/local/bin:/usr/bin:/bin",
                 "/usr/local/bin/python3", "-I", "-S", "-c", raw.decode("ascii")),
        "uid": 65534, "gid": 65534, "pids_limit": 128,
        "memory_bytes": 268435456, "cpus": 0.5, "wall_clock_seconds": 5.0,
        "output_cap_bytes": 65536, "tmpfs_bytes": 8388608, "stop_timeout_seconds": 2.0,
    }
    args = transport.build_create_argv(plan)
    assert args[0:2] == ("/usr/bin/docker", "create")
    assert args[-1].encode("ascii") == raw
    description = plans.describe_workload(case, raw)
    assert description["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert description["source_bytes"] == len(raw)
    assert description["operation_id"] == plan.operation_id
    assert description["plan_sha256"] == transport.plan_identity(plan)
    assert description["required_transport_sha256"] == plans.REQUIRED_TRANSPORT_SHA256
    assert description["runtime"] == "rf-runsc"
    assert description["whole_attempt_seconds"] == 120
    assert description["cleanup_reserve_seconds"] == 30
    assert description["serial_seven_attempt_ceiling_seconds"] == 840
    assert all(description[k] is False for k in (
        "candidate_admission", "containment_qualified", "execute_authorized"))
    assert {"fixture_listener", "trusted_host_resource_mapping",
            "complete_helper_census", "cleanup_observations"} <= set(description["still_required"])
    assert raw.decode("ascii") not in json.dumps(description)


@pytest.mark.parametrize("case", SOURCES)
def test_altered_swapped_or_nonbytes_source_refuses_redacted(case):
    raw = (WORKLOADS / SOURCES[case]).read_bytes()
    other = next(k for k in SOURCES if k != case)
    bad = [raw[:-1] + bytes([raw[-1] ^ 1]), raw + b"x", raw[:-1], b"",
           b"x" * 65537, bytearray(raw), memoryview(raw), raw.decode("ascii"),
           None, True, (WORKLOADS / SOURCES[other]).read_bytes()]
    for value in bad:
        for fn in (plans.build_workload_plan, plans.describe_workload):
            with pytest.raises(plans.WorkloadPlanRefused) as exc:
                fn(case, value)
            assert len(str(exc.value)) < 100
            assert "import " not in str(exc.value)


class HostileString(str):
    def __hash__(self):
        raise AssertionError("must reject subclass before hashing")


class HostileBytes(bytes):
    def __len__(self):
        raise AssertionError("must reject subclass before length")


@pytest.mark.parametrize("case", [None, 1, True, [], {}, b"w01", "w00", "w08",
                                  "W01", "w01\n", HostileString("w01")])
def test_case_types_and_unknown_values(case):
    with pytest.raises(plans.WorkloadPlanRefused):
        plans.build_workload_plan(case, b"private payload")


def test_bytes_subclass_and_pins_are_closed():
    raw = (WORKLOADS / SOURCES["w01"]).read_bytes()
    with pytest.raises(plans.WorkloadPlanRefused):
        plans.build_workload_plan("w01", HostileBytes(raw))
    with pytest.raises(TypeError):
        plans.SOURCE_PINS["w08"] = (0, "0" * 64)
    with pytest.raises(TypeError):
        plans.build_workload_plan("w01", raw, image="untrusted")


def test_import_and_factory_do_not_read_environment_or_payload(monkeypatch):
    raw = (WORKLOADS / SOURCES["w01"]).read_bytes()
    def forbidden(*args, **kwargs):
        raise AssertionError("factory must not read files/environment or import payload")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(os, "getenv", forbidden)
        patch.setattr(os, "environ", {})
        importlib.reload(plans)
        plans.build_workload_plan("w01", raw)
        plans.describe_workload("w01", raw)


def test_general_engine_stays_dormant():
    engine = transport.SubprocessDockerEngine("/usr/bin/docker")
    assert engine.dormant is True
    with pytest.raises(transport.TransportDormantError):
        engine.run(("/usr/bin/docker", "info"), deadline_seconds=1.0,
                   output_cap_bytes=1024)
    with pytest.raises(transport.TransportDormantError):
        transport.TransportQualification()
    assert transport._QUALIFICATION_ISSUED is False
