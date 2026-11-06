"""Synthetic pytest suite for the dormant research-codegen transport.

Everything here is hermetic: the Docker engine is only ever a scripted fake,
no Docker subprocess is ever launched, and process-collector tests run only
tiny trusted stdlib fixtures under ``sys.executable``.  The tests
discriminate the transport's claims (dormancy, immutability, identity
pinning, uncertainty retention) rather than mirroring its helpers.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import os
import subprocess
import sys

import pytest

from engine.research_codegen import transport
from engine.research_codegen.transport import (
    AttemptState,
    EngineCommandResult,
    SubprocessDockerEngine,
    TransportAttempt,
    TransportDormantError,
    TransportOrchestrator,
    TransportPlan,
    TransportPlanError,
    TransportQualification,
    TransportSession,
    TransportStateError,
    build_create_argv,
    build_inspect_argv,
    build_kill_argv,
    build_remove_argv,
    build_start_argv,
    build_stop_argv,
    collect_process,
    parse_container_id,
)

CID = "ab" * 32
FOREIGN_CID = "cd" * 32
CID_STDOUT = (CID + "\n").encode("ascii")
IMAGE = "registry.example/repo@sha256:" + "ab" * 32

TRACKED_SUBCOMMANDS = frozenset({"stop", "kill", "rm", "inspect"})
ENGINE_SUBCOMMANDS = frozenset(
    {"create", "start", "stop", "kill", "rm", "inspect"}
)


# --------------------------------------------------------------------------
# Fixtures and synthetic engine
# --------------------------------------------------------------------------

def plan_kwargs(**overrides):
    base = dict(
        operation_id="op-transport-1",
        image=IMAGE,
        entrypoint="/usr/local/bin/trusted-entrypoint",
        argv=("run-check",),
        docker_binary="/usr/bin/docker",
        uid=4711,
        gid=4712,
        pids_limit=256,
        memory_bytes=268435456,
        cpus=1.5,
        wall_clock_seconds=60.0,
        output_cap_bytes=4096,
        tmpfs_bytes=16777216,
        stop_timeout_seconds=10.0,
    )
    base.update(overrides)
    return base


@pytest.fixture
def plan():
    return TransportPlan(**plan_kwargs())


def ok(stdout=b"", stderr=b"", rc=0, observed=None):
    return EngineCommandResult(
        rc, stdout, stderr, 60.0, 4096, observed_container_id=observed
    )


def absent(cid):
    """Installed closed absence protocol: rc 1, known empty JSON stdout,
    single container-specific daemon error line for this exact full id."""
    return EngineCommandResult(
        1,
        b"[]\n",
        f"Error response from daemon: No such container: {cid}\n".encode("ascii"),
        30.0,
        4096,
    )


class FakeEngine:
    """Scripted synthetic engine.

    Records every bounded call, refuses a second create outright, and pins
    every tracked subcommand to the expected container id.
    """

    def __init__(self, script=None, expected_cid=None):
        self.script = dict(script or {})
        self.calls = []
        self.expected_cid = expected_cid
        self._creates = 0

    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        assert isinstance(argv, tuple), "engine argv must be a tuple"
        assert all(isinstance(item, str) for item in argv)
        assert deadline_seconds > 0, "engine command must be bounded in time"
        assert output_cap_bytes > 0, "engine command must be bounded in bytes"
        self.calls.append(
            {
                "argv": argv,
                "deadline": deadline_seconds,
                "cap": output_cap_bytes,
            }
        )
        sub = argv[1]
        assert sub in ENGINE_SUBCOMMANDS, f"unexpected subcommand {sub!r}"
        if sub == "create":
            assert self._creates == 0, "a second create was issued"
            self._creates += 1
        if self.expected_cid is not None and sub in TRACKED_SUBCOMMANDS:
            assert argv[-1] == self.expected_cid, (
                "engine command is not pinned to the tracked container id:"
                f" {argv}"
            )
        phase = "workload_state" if sub == "inspect" and "--format" in argv else sub
        queue = self.script.get(phase)
        outcome = queue.pop(0) if queue else None
        if outcome is None:
            if sub == "create":
                outcome = ok(stdout=CID_STDOUT)
            elif phase == "workload_state":
                outcome = ok(stdout=json.dumps([CID, {"Running": False, "ExitCode": 0, "OOMKilled": False}]).encode())
            else:
                outcome = ok()
        if isinstance(outcome, Exception):
            raise outcome
        if callable(outcome):
            outcome = outcome(
                argv,
                deadline_seconds=deadline_seconds,
                output_cap_bytes=output_cap_bytes,
            )
        return outcome


def subcommands(engine):
    return [call["argv"][1] for call in engine.calls]


# --------------------------------------------------------------------------
# Source hygiene: stdlib-only imports, no research plane, no shell
# --------------------------------------------------------------------------

MODULE_SOURCE = inspect.getsource(transport)


def test_module_imports_are_pure_stdlib_with_no_research_plane():
    allowed = {
        "__future__",
        "dataclasses",
        "typing",
        "enum", "json", "hashlib",
        "math",
        "os",
        "re",
        "select",
        "subprocess",
        "time",
        "types",
    }
    tree = ast.parse(MODULE_SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed, node.module
    # Inspect executable imports/calls rather than words in explanatory docs.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"__import__", "eval", "exec"}


def test_module_has_no_enabling_switch_for_the_dormant_engine():
    public_names = [name for name in dir(transport)]
    assert not any(name.startswith("enable") for name in public_names)
    assert not any("ENABLE" in name for name in public_names)
    assert transport._QUALIFICATION_ISSUED is False
    with pytest.raises(TransportDormantError):
        TransportQualification()


# --------------------------------------------------------------------------
# Plan validation
# --------------------------------------------------------------------------

def test_valid_plan_is_accepted_with_normalized_argv(plan):
    assert plan.argv == ("run-check",)
    assert plan.image == IMAGE
    assert isinstance(plan.cpus, float)


def test_create_argv_is_exactly_the_fixed_hardened_tuple(plan):
    expected = (
        "/usr/bin/docker",
        "create",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--no-healthcheck", "--log-driver=none", "--restart=no",
        "--cgroupns=private", "--ipc=private",
        "--user",
        "4711:4712",
        "--pids-limit",
        "256",
        "--memory",
        "268435456",
        "--memory-swap",
        "268435456",
        "--cpus",
        "1.5",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16777216",
        "--entrypoint",
        "/usr/local/bin/trusted-entrypoint",
        "--", IMAGE,
        "run-check",
    )
    assert build_create_argv(plan) == expected


def test_only_immutable_digurized_image_references_accepted():
    digests = {
        "repo:latest": "tag form",
        "repo": "mutable bare name",
        "repo@" + "a" * 64: "no sha256 algorithm",
        "repo@sha256:" + "a" * 63: "short digest",
        "repo@sha256:" + "a" * 65: "long digest",
        "repo@sha256:" + "AB" * 32: "uppercase digest",
        "repo:latest@sha256:" + "ab" * 32: "tag plus digest",
        "Repo/example@sha256:" + "ab" * 32: "uppercase repository",
        "repo@sha384:" + "ab" * 32: "wrong algorithm",
        "repo@md5:d41d8cd98f00b204e9800998ecf8427e": "tiny digest",
        "repo/..@sha256:" + "ab" * 32: "dot-dot component",
        "registry.example:port/repo@sha256:" + "ab" * 32: "non-numeric port",
    }
    for image, label in digests.items():
        with pytest.raises(TransportPlanError) as excinfo:
            TransportPlan(**plan_kwargs(image=image))
        assert "image" in str(excinfo.value), label


@pytest.mark.parametrize(
    "override",
    [
        {"uid": True},
        {"gid": False},
        {"pids_limit": True},
        {"memory_bytes": True},
        {"cpus": True},
        {"output_cap_bytes": True},
        {"tmpfs_bytes": True},
        {"memory_bytes": 1.5},
        {"output_cap_bytes": 4096.0},
        {"uid": "4711"},
        {"cpus": float("inf")},
        {"cpus": float("nan")},
        {"cpus": 0.0},
        {"cpus": 4.5},
        {"wall_clock_seconds": float("inf")},
        {"wall_clock_seconds": float("nan")},
        {"wall_clock_seconds": 0},
        {"wall_clock_seconds": 3601.0},
        {"wall_clock_seconds": transport._MAX_COLLECT_DEADLINE_SECONDS + 1},
        {"stop_timeout_seconds": 0},
        {"stop_timeout_seconds": float("inf")},
        {"stop_timeout_seconds": 121.0},
        {"memory_bytes": 0},
        {"memory_bytes": -1},
        {"memory_bytes": transport.MAX_MEMORY_BYTES + 1},
        {"pids_limit": 0},
        {"pids_limit": transport.MAX_PIDS + 1},
        {"output_cap_bytes": 0},
        {"output_cap_bytes": transport.MAX_OUTPUT_BYTES + 1},
        {"tmpfs_bytes": 0},
        {"tmpfs_bytes": transport.MAX_TMPFS_BYTES + 1},
        {"uid": 0},
        {"uid": -5},
        {"operation_id": "-leading-dash"},
        {"operation_id": "op\nid"},
        {"operation_id": "op\x00id"},
        {"operation_id": ""},
        {"entrypoint": "bin/tool"},
        {"entrypoint": "/a/../b/tool"},
        {"entrypoint": "/a//tool"},
        {"entrypoint": "/usr/bin/tool\x00"},
        {"docker_binary": "docker"},
        {"docker_binary": "/usr/../bin/docker"},
        {"docker_binary": "/usr/bin/docker; rm -rf /"},
        {"entrypoint": "/bin/sh"},
        {"argv": ("/bin/bash",)},
        {"argv": ("",)},
        {"argv": ("a\nb",)},
        {"argv": ("caf\xe9",)},
        {"argv": ("a\x00b",)},
        {"argv": "run-check"},
        {"argv": ["ok", 7]},
    ],
)
def test_bool_type_nonfinite_and_out_of_range_plans_rejected(override):
    with pytest.raises(TransportPlanError):
        TransportPlan(**plan_kwargs(**override))


def test_no_extra_fields_shell_env_mount_or_override_interfaces(plan):
    field_names = {field.name for field in dataclasses.fields(TransportPlan)}
    for hostile in (
        "shell",
        "env",
        "environment",
        "mounts",
        "volumes",
        "devices",
        "command",
        "container_name",
        "admission_proof",
        "qualified",
        "enabled",
    ):
        assert hostile not in field_names
    with pytest.raises(TypeError):
        TransportPlan(**plan_kwargs(env={"INJECTED": "1"}))
    with pytest.raises(TypeError):
        TransportPlan(**plan_kwargs(command={"run": ["sh", "-c", "x"]}))
    with pytest.raises(TypeError):
        TransportPlan(**plan_kwargs(mounts=[("/host", "/container")]))
    with pytest.raises(TypeError):
        TransportPlan(**plan_kwargs(shell=True))


def test_no_shell_env_or_mount_interfaces_in_any_builder(plan):
    create = build_create_argv(plan)
    hostile_flags = {
        "--env",
        "-e",
        "--env-file",
        "--volume",
        "-v",
        "--mount",
        "--device",
        "--privileged",
        "--hostname",
        "--pid",
        "--userns",
        "--uts",
        "--ipc",
        "--cap-add",
    }
    for builder in (
        build_create_argv,
        build_start_argv,
        build_stop_argv,
        build_kill_argv,
        build_remove_argv,
        build_inspect_argv,
    ):
        if builder is build_create_argv:
            argv = builder(plan)
        else:
            argv = builder(plan, CID)
        assert not (set(argv) & hostile_flags), (builder, argv)
        assert "sh" not in argv and "-c" not in argv and "bash" not in argv
    assert "--network=none" in create
    assert "--pull=never" in create
    assert "--read-only" in create
    assert "--cap-drop=ALL" in create
    assert "--security-opt=no-new-privileges" in create
    tmpfs = create[create.index("--tmpfs") + 1]
    assert tmpfs.startswith("/tmp:")
    assert "noexec" in tmpfs and "nosuid" in tmpfs and "size=" in tmpfs
    user = create[create.index("--user") + 1]
    assert user == "4711:4712"


def test_tracked_builders_pin_exactly_one_full_container_id(plan):
    builders = {
        "start": build_start_argv,
        "stop": build_stop_argv,
        "kill": build_kill_argv,
        "rm": build_remove_argv,
        "inspect": build_inspect_argv,
    }
    for sub, builder in builders.items():
        argv = builder(plan, CID)
        assert argv[0] == plan.docker_binary
        assert argv[1] == sub
        assert argv.count(CID) == 1 and argv[-1] == CID
    for bad in ("", "short", CID.upper(), "z" * 64, CID + " ", CID + ";rm"):
        with pytest.raises(TransportPlanError):
            build_stop_argv(plan, bad)


def test_parse_container_id_accepts_only_one_exact_64_hex_id():
    assert parse_container_id(CID_STDOUT) == CID
    assert parse_container_id(b"  " + CID.encode() + b" \n") == CID
    for malformed in (
        b"",
        b"\n",
        CID.encode()[:63] + b"\n",
        (CID + "0").encode(),
        CID.upper().encode() + b"\n",
        (CID + " extra").encode(),
        b"prefix " + CID.encode(),
        b"CID",
        bytearray(b"\xff\xfe"),
        None,
        123,
    ):
        assert parse_container_id(malformed) is None, malformed


# --------------------------------------------------------------------------
# Dormancy
# --------------------------------------------------------------------------

def test_real_engine_dormant_refusal_makes_no_process_call(
    monkeypatch, plan
):
    def _no_popen(*args, **kwargs):
        raise AssertionError("Popen must never be called while dormant")

    monkeypatch.setattr(transport.subprocess, "Popen", _no_popen)
    monkeypatch.setenv("FABRIC_TRANSPORT_ENABLE", "1")
    monkeypatch.setenv("TRANSPORT_QUALIFICATION_FILE", "/tmp/qual.json")
    monkeypatch.setenv("MASTERMIND_TRANSPORT_ENABLED", "yes")

    engine = SubprocessDockerEngine(plan.docker_binary)
    assert engine.dormant is True
    with pytest.raises(TransportDormantError) as excinfo:
        engine.run(
            build_create_argv(plan),
            deadline_seconds=1.0,
            output_cap_bytes=plan.output_cap_bytes,
        )
    assert "no process call was made" in str(excinfo.value)

    # Orchestrating through the dormant engine also refuses, and the session
    # is spent: no retry path exists after the typed refusal.
    session = TransportSession(plan)
    with pytest.raises(TransportDormantError):
        TransportOrchestrator(engine).execute(session)
    assert session.consumed is True


def test_qualification_object_cannot_be_constructed():
    with pytest.raises(TransportDormantError):
        TransportQualification()
    with pytest.raises(TransportDormantError):
        TransportQualification(image=IMAGE, entrypoint_proof="unused")


# --------------------------------------------------------------------------
# Orchestrator: full success requires verified absence
# --------------------------------------------------------------------------

def test_full_known_id_success_only_after_verified_absence(plan):
    engine = FakeEngine(script={"inspect": [absent(CID)]}, expected_cid=CID)
    session = TransportSession(plan)
    attempt = TransportOrchestrator(engine).execute(session)
    assert attempt.state is AttemptState.CLEANED_SUCCESS
    assert attempt.reconciliation_required is False
    assert attempt.container_id == CID
    assert attempt.operation_id == plan.operation_id
    assert session.attempt is attempt
    assert subcommands(engine) == ["create", "start", "inspect", "stop", "rm", "inspect"]
    assert engine.calls[0]["argv"] == build_create_argv(plan)
    assert engine.calls[1]["argv"] == build_start_argv(plan, CID)


def test_success_blocked_when_absence_check_reports_container_exists(plan):
    engine = FakeEngine(expected_cid=CID)  # default inspect rc=0: exists
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert attempt.reconciliation_required is True
    assert attempt.container_id == CID
    assert "still exists" in attempt.detail


# --------------------------------------------------------------------------
# Create uncertainty: no start, no retry, retained obligation
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kind",
    [
        "rc1",
        "timeout",
        "truncated",
        "empty_stdout",
        "short_id",
        "junk_suffix",
        "uppercase_id",
        "engine_exception",
    ],
)
def test_create_uncertainty_never_starts_never_repeats_create(plan, kind):
    scripts = {
        "rc1": {"create": [ok(rc=1, stderr=b"boom")]},
        "timeout": {
            "create": [
                EngineCommandResult(
                    None, b"", b"", 120.0, 4096, timed_out=True
                )
            ]
        },
        "truncated": {
            "create": [
                EngineCommandResult(
                    None,
                    CID.encode()[:30],
                    b"",
                    120.0,
                    4096,
                    output_truncated=True,
                )
            ]
        },
        "empty_stdout": {"create": [ok(stdout=b"")]},
        "short_id": {"create": [ok(stdout=CID.encode()[:63] + b"\n")]},
        "junk_suffix": {"create": [ok(stdout=CID_STDOUT + b" extra\n")]},
        "uppercase_id": {"create": [ok(stdout=CID.upper().encode() + b"\n")]},
        "engine_exception": {"create": [RuntimeError("create exploded")]},
    }
    engine = FakeEngine(script=scripts[kind])
    orchestrator = TransportOrchestrator(engine)
    session = TransportSession(plan)

    attempt = orchestrator.execute(session)
    assert attempt.state is AttemptState.CREATE_UNCERTAIN
    assert attempt.container_id is None
    assert attempt.reconciliation_required is True
    assert subcommands(engine) == ["create"]

    with pytest.raises(TransportStateError):
        orchestrator.execute(session)
    assert subcommands(engine) == ["create"]

    reconciled = orchestrator.reconcile(plan, attempt)
    assert reconciled.state is AttemptState.CREATE_UNCERTAIN
    assert reconciled.reconciliation_required is True
    assert reconciled.container_id is None
    assert subcommands(engine) == ["create"]


def test_create_foreign_identity_echo_blocks_all_mutations(plan):
    engine = FakeEngine(script={"create": [ok(stdout=CID_STDOUT, observed=FOREIGN_CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.state is AttemptState.CREATE_UNCERTAIN
    assert receipt.container_id is None
    assert receipt.reconciliation_required
    assert subcommands(engine) == ["create"]
    assert receipt.plan_sha256 == transport.plan_identity(plan)



# --------------------------------------------------------------------------
# Start uncertainty preserves the known id for bounded cleanup
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kind",
    ["rc1", "timeout", "truncated", "engine_exception", "foreign_echo"],
)
def test_start_uncertainty_preserves_known_id_cleanup(plan, kind):
    scripts = {
        "rc1": {
            "start": [ok(rc=1, stderr=b"cannot start")],
            "inspect": [absent(CID)],
        },
        "timeout": {
            "start": [
                EngineCommandResult(
                    None, b"", b"", 60.0, 4096, timed_out=True
                )
            ],
            "inspect": [absent(CID)],
        },
        "truncated": {
            "start": [
                EngineCommandResult(
                    None, b"", b"", 60.0, 4096, output_truncated=True
                )
            ],
            "inspect": [absent(CID)],
        },
        "engine_exception": {
            "start": [RuntimeError("start exploded")],
            "inspect": [absent(CID)],
        },
        "foreign_echo": {
            "start": [ok(observed=FOREIGN_CID)],
            "inspect": [absent(CID)],
        },
    }
    engine = FakeEngine(script=scripts[kind], expected_cid=CID)
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.container_id == CID
    assert subcommands(engine)[:2] == ["create", "start"]
    assert any(
        "start not confirmed" in event for event in attempt.engine_events
    )
    if kind == "foreign_echo":
        assert attempt.state is AttemptState.CLEANED_FAILURE
        assert attempt.reconciliation_required is True
        assert "wrong identity" in attempt.workload_problem
    else:
        assert attempt.state is AttemptState.CLEANED_FAILURE
        assert attempt.workload_confirmed is False
        assert subcommands(engine) == [
            "create", "start", "stop", "rm", "inspect",
        ]


# --------------------------------------------------------------------------
# Cleanup ladder: stop, then kill, then remove, then absence
# --------------------------------------------------------------------------

def test_stop_failure_falls_back_to_bounded_kill(plan):
    engine = FakeEngine(
        script={"stop": [ok(rc=1)], "inspect": [absent(CID)]},
        expected_cid=CID,
    )
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANED_SUCCESS
    assert subcommands(engine) == [
        "create", "start", "inspect", "stop", "kill", "rm", "inspect",
    ]


def test_stop_and_kill_failure_retains_uncertainty_without_removal(plan):
    engine = FakeEngine(
        script={"stop": [ok(rc=1)], "kill": [ok(rc=1)]}, expected_cid=CID
    )
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert attempt.reconciliation_required is True
    assert attempt.container_id == CID
    assert "unknown" in attempt.detail
    assert subcommands(engine) == ["create", "start", "inspect", "stop", "kill", "rm", "inspect"]


def test_kill_exception_is_retained(plan):
    engine = FakeEngine(
        script={"stop": [ok(rc=1)], "kill": [RuntimeError("kill exploded)]")]},
        expected_cid=CID,
    )
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert "kill engine exception: RuntimeError" in attempt.detail
    assert subcommands(engine) == ["create", "start", "inspect", "stop", "kill", "rm", "inspect"]


def test_remove_failure_retains_uncertainty(plan):
    engine = FakeEngine(script={"rm": [ok(rc=1)]}, expected_cid=CID)
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert attempt.reconciliation_required is True
    assert attempt.container_id == CID
    assert "remove did not confirm" in attempt.detail
    assert subcommands(engine) == ["create", "start", "inspect", "stop", "rm", "inspect"]


def test_remove_exception_is_retained(plan):
    engine = FakeEngine(script={"rm": [RuntimeError("rm exploded")]},
                        expected_cid=CID)
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert "rm engine exception" in attempt.detail


@pytest.mark.parametrize(
    "inspect_result, label",
    [
        (ok(rc=0), "still-exists"),
        (
            EngineCommandResult(1, b"", b"unknown error", 30.0, 4096),
            "no-absence-marker",
        ),
        (
            EngineCommandResult(
                1, b"",
                f"Error response from daemon: No such container: {FOREIGN_CID}\n".encode(),
                30.0, 4096,
            ),
            "foreign-id-marker",
        ),
        (
            EngineCommandResult(
                1, b"", f"Error: No such object: {CID}\n".encode(), 30.0, 4096
            ),
            "old-generic-object-grammar",
        ),
        (
            EngineCommandResult(
                None, b"", b"", 30.0, 4096, timed_out=True
            ),
            "inspect-timeout",
        ),
        (
            EngineCommandResult(
                None, b"", b"", 30.0, 4096, output_truncated=True
            ),
            "inspect-truncated",
        ),
        (
            EngineCommandResult(
                None, b"", f"Error response from daemon: No such container: {CID}\n".encode(),
                30.0, 4096,
            ),
            "unreaped-client",
        ),
        (
            EngineCommandResult(
                1, b"", f"Error response from daemon: No such container: {CID}\n".encode(),
                30.0, 4096, error_type="OSError",
            ),
            "collector-error",
        ),
        (
            EngineCommandResult(
                0, b"",
                json.dumps([{CID: {"Id": CID}}]).encode() +
                f"Error response from daemon: No such container: {CID}\n".encode(),
                30.0, 4096,
            ),
            "current-object-rc0-never-absence",
        ),
    ],
)
def test_absence_check_failures_retain_uncertainty(
    plan, inspect_result, label
):
    engine = FakeEngine(script={"inspect": [inspect_result]}, expected_cid=CID)
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN, label
    assert attempt.reconciliation_required is True, label
    assert attempt.container_id == CID, label
    assert attempt.state is not AttemptState.CLEANED_SUCCESS


def test_inspect_exception_retains_uncertainty(plan):
    engine = FakeEngine(
        script={"inspect": [RuntimeError("inspect exploded")]},
        expected_cid=CID,
    )
    attempt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert attempt.state is AttemptState.CLEANUP_UNCERTAIN
    assert "absence check failed" in attempt.detail


# --------------------------------------------------------------------------
# Closed installed absence grammar: precise acceptance and discrimination
# --------------------------------------------------------------------------

ABSENCE_ERROR_LINE = (
    f"Error response from daemon: No such container: {CID}\n".encode()
)


def test_dormant_engine_still_refuses_inspect_before_any_process(
    monkeypatch, plan
):
    def _no_popen(*args, **kwargs):
        raise AssertionError("Popen must never be called while dormant")

    monkeypatch.setattr(transport.subprocess, "Popen", _no_popen)
    engine = SubprocessDockerEngine(plan.docker_binary)
    with pytest.raises(TransportDormantError) as excinfo:
        engine.run(
            build_inspect_argv(plan, CID),
            deadline_seconds=1.0,
            output_cap_bytes=4096,
        )
    assert "no process call was made" in str(excinfo.value)


def test_absence_parser_accepts_installed_grammar_on_both_channels():
    assert transport.parse_container_absence(b"[]\n", ABSENCE_ERROR_LINE, CID)
    assert transport.parse_container_absence(
        b"[]\n" + ABSENCE_ERROR_LINE, b"", CID
    )
    assert transport.parse_container_absence(b"", ABSENCE_ERROR_LINE, CID)
    assert transport.parse_container_absence(
        b"", ABSENCE_ERROR_LINE.rstrip(b"\n"), CID
    )


@pytest.mark.parametrize(
    "stdout, stderr, cid, label",
    [
        (b"", b"", CID, "empty-payload"),
        (
            b"",
            f"Error response from daemon: No such container: {FOREIGN_CID}\n".encode(),
            CID,
            "wrong-id",
        ),
        (
            b"",
            f"Error response from daemon: No such container: {CID[:63]}\n".encode(),
            CID,
            "short-id-payload",
        ),
        (b"x" + ABSENCE_ERROR_LINE, b"", CID, "embedded-prefix"),
        (ABSENCE_ERROR_LINE.rstrip(b"\n") + b"y\n", b"", CID, "embedded-suffix"),
        (
            b"",
            ABSENCE_ERROR_LINE.rstrip(b"\n") + b" (retrying)\n",
            CID,
            "annotated-error-line",
        ),
        (
            b"",
            f"Error: No such object: {CID}\n".encode(),
            CID,
            "generic-object-grammar",
        ),
        (
            b"",
            b"the log mentioned No such container: " + CID.encode() + b" in transit\n",
            CID,
            "arbitrary-text-contains-phrase",
        ),
        (
            b"",
            ABSENCE_ERROR_LINE + b"Error response from daemon: authorization denied\n",
            CID,
            "extra-error-line",
        ),
        (
            b"",
            b"Error response from daemon: Permission denied\n",
            CID,
            "permission-line-only",
        ),
        (b"", b"No such container: " + b"f" * 63 + b"\n", "f" * 63, "short-cid-argument"),
    ],
)
def test_absence_parser_refuses_every_non_installed_form(
    stdout, stderr, cid, label
):
    assert transport.parse_container_absence(stdout, stderr, cid) is False, label


@pytest.mark.parametrize(
    "stdout, stderr",
    [
        (b"x" + ABSENCE_ERROR_LINE, b""),
        (ABSENCE_ERROR_LINE.rstrip(b"\n") + b"y\n", b""),
        (
            b"",
            ABSENCE_ERROR_LINE.rstrip(b"\n") + b" (retrying)\n",
        ),
        (
            b"",
            b"the log mentioned No such container: " + CID.encode() + b" in transit\n",
        ),
        (
            b"",
            ABSENCE_ERROR_LINE + b"Error response from daemon: authorization denied\n",
        ),
    ],
)
def test_weak_substring_predicate_fails_these_negatives(stdout, stderr):
    combined = stdout + stderr
    weak = (b"No such container" in combined) and (
        CID.encode("ascii") in combined
    )
    assert weak is True, "probe precondition: weak predicate would accept"
    assert transport.parse_container_absence(stdout, stderr, CID) is False


def test_old_no_such_object_predicate_fails_installed_protocol():
    combined = b"" + ABSENCE_ERROR_LINE
    old_predicate = (b"No such object" in combined) and (
        CID.encode("ascii") in combined
    )
    assert old_predicate is False
    assert not hasattr(transport, "CONTAINER_ABSENCE_MARKER")
    assert transport.parse_container_absence(b"", combined, CID) is True


# --------------------------------------------------------------------------
# Bounded, identity-pinned engine usage; session/attempt guards
# --------------------------------------------------------------------------

def test_every_engine_command_is_bounded_and_pinned_to_the_same_id(plan):
    engine = FakeEngine(
        script={"stop": [ok(rc=1)], "inspect": [absent(CID)]},
        expected_cid=CID,
    )
    TransportOrchestrator(engine).execute(TransportSession(plan))
    assert engine.calls
    for call in engine.calls:
        argv = call["argv"]
        assert argv[0] == plan.docker_binary
        assert argv[1] in ENGINE_SUBCOMMANDS
        assert 0 < call["deadline"] <= 200.0
        assert call["cap"] == plan.output_cap_bytes
        if argv[1] in TRACKED_SUBCOMMANDS:
            assert argv.count(CID) == 1
            assert argv[-1] == CID
        if argv[1] == "create":
            assert CID not in argv
            assert argv[len(argv) - len(plan.argv):] == tuple(plan.argv)


def test_second_create_refused_and_settled_attempt_not_reused(plan):
    engine = FakeEngine(script={"inspect": [absent(CID)]}, expected_cid=CID)
    orchestrator = TransportOrchestrator(engine)
    session = TransportSession(plan)
    first = orchestrator.execute(session)
    assert first.state is AttemptState.CLEANED_SUCCESS
    with pytest.raises(TransportStateError):
        orchestrator.execute(session)
    assert subcommands(engine) == ["create", "start", "inspect", "stop", "rm", "inspect"]
    again = orchestrator.reconcile(plan, first)
    assert again is first
    assert len(engine.calls) == 6


def test_changed_attempt_identity_rejected(plan):
    other_attempt = TransportAttempt(
        "op-transport-other",
        CID,
        AttemptState.CLEANUP_UNCERTAIN,
        True,
        "foreign receipt",
    )
    with pytest.raises(TransportStateError):
        TransportOrchestrator(FakeEngine()).reconcile(plan, other_attempt)


def test_reconcile_runs_cleanup_only_and_never_creates(plan):
    first_engine = FakeEngine(script={"rm": [ok(rc=1)]}, expected_cid=CID)
    first = TransportOrchestrator(first_engine).execute(
        TransportSession(plan)
    )
    assert first.state is AttemptState.CLEANUP_UNCERTAIN

    reconcile_engine = FakeEngine(
        script={"inspect": [absent(CID)]}, expected_cid=CID
    )
    reconciled = TransportOrchestrator(reconcile_engine).reconcile(plan, first)
    assert reconciled.state is AttemptState.CLEANED_SUCCESS
    assert reconciled.container_id == CID
    assert reconciled.reconciliation_required is False
    assert subcommands(reconcile_engine) == ["stop", "rm", "inspect"]


# --------------------------------------------------------------------------
# Bounded local process collector (synthetic stdlib fixtures only)
# --------------------------------------------------------------------------

def test_collector_captures_small_output_exactly():
    result = collect_process(
        [sys.executable, "-c", "print('hello-transport')"],
        deadline_seconds=30.0,
        output_cap_bytes=4096,
    )
    assert result.returncode == 0
    assert result.output == b"hello-transport\n"
    assert result.timed_out is False
    assert result.output_truncated is False
    assert result.argv[0] == sys.executable


def test_collector_never_uses_a_shell(monkeypatch):
    seen = {}
    real_popen = subprocess.Popen

    def recorder(*args, **kwargs):
        seen["shell"] = kwargs.get("shell", "absent")
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(transport.subprocess, "Popen", recorder)
    result = collect_process(
        [sys.executable, "-c", "print('ok')"],
        deadline_seconds=30.0,
        output_cap_bytes=4096,
    )
    assert seen["shell"] is False
    assert result.output.strip() == b"ok"


def test_collector_uses_minimal_trusted_env_only(monkeypatch):
    supplied = {}
    real_popen = subprocess.Popen

    def recorder(*args, **kwargs):
        supplied.update(kwargs["env"])
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(transport.subprocess, "Popen", recorder)
    monkeypatch.setenv("FABRIC_ENV_SENTINEL", "leak-attempt")
    result = collect_process(
        [
            sys.executable,
            "-c",
            "import json, os; print(json.dumps(dict(os.environ)))",
        ],
        deadline_seconds=30.0,
        output_cap_bytes=65536,
    )
    child_env = json.loads(result.output.decode("ascii"))
    assert "FABRIC_ENV_SENTINEL" not in child_env
    assert child_env["PATH"] == "/usr/bin:/bin"
    expected = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"}
    assert supplied == expected
    assert all(child_env[key] == value for key, value in expected.items())
    # CoreFoundation adds this metadata on macOS even with an explicit env.
    native_metadata = {"__CF_USER_TEXT_ENCODING"} if sys.platform == "darwin" else set()
    assert set(child_env) <= set(expected) | native_metadata


def test_collector_enforces_output_cap_and_reaps():
    result = collect_process(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('x' * 2000000); sys.stdout.flush()",
        ],
        deadline_seconds=30.0,
        output_cap_bytes=4096,
    )
    assert result.output_truncated is True
    assert len(result.output) == 4096
    assert result.timed_out is False
    assert type(result.returncode) is int
    assert "reaped" in result.detail


def test_collector_enforces_deadline_and_reaps():
    result = collect_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        deadline_seconds=0.5,
        output_cap_bytes=4096,
    )
    assert result.timed_out is True
    assert result.output_truncated is False
    assert type(result.returncode) is int and result.returncode != 0
    assert "deadline" in result.detail


@pytest.mark.parametrize(
    "argv, kwargs",
    [
        ("sh -c 'boom'", {}),
        (["sh", "-c", "echo\x00hidden"], {}),
        ([], {}),
        (["ok"], {"deadline_seconds": float("inf")}),
        (["ok"], {"deadline_seconds": 0.0}),
        (["ok"], {"deadline_seconds": -1.0}),
        (["ok"], {"output_cap_bytes": 0}),
        (["ok"], {"output_cap_bytes": transport.MAX_OUTPUT_BYTES + 1}),
        (["bad\x00"], {}),
    ],
)
def test_collector_rejects_unbounded_or_hostile_arguments(argv, kwargs):
    kwargs.setdefault("deadline_seconds", 10.0)
    kwargs.setdefault("output_cap_bytes", 4096)
    with pytest.raises(transport.TransportPlanError):
        collect_process(argv, **kwargs)


# Independent regressions: failed workload outcome must survive successful cleanup.
@pytest.mark.parametrize("outcome", [
    ok(rc=7),
    EngineCommandResult(None, b"partial", b"", 60.0, 4096, timed_out=True),
    EngineCommandResult(0, b"partial", b"", 60.0, 4096, output_truncated=True),
    RuntimeError("ordinary start failure"),
])
def test_failed_start_never_becomes_execution_success(outcome, plan):
    engine = FakeEngine(script={"start": [outcome], "inspect": [absent(CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.state is not AttemptState.CLEANED_SUCCESS

def test_workload_uses_attached_output_and_actual_wall_budget(plan):
    assert "--attach" in build_start_argv(plan, CID)

def test_typed_start_failure_still_cleans_known_id(plan):
    engine = FakeEngine(script={"start": [TransportStateError("synthetic engine error")], "inspect": [absent(CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert "rm" in subcommands(engine)
    assert receipt.state is not AttemptState.CLEANED_SUCCESS

def test_collector_read_exception_reaps_with_fake_process(monkeypatch):
    class Pipe:
        def fileno(self): return 123
        def close(self): pass
    class Process:
        stdout = Pipe()
        returncode = None
        def terminate(self): self.returncode = -15
        def kill(self): self.returncode = -9
        def wait(self, timeout=None): return self.returncode
        def poll(self): return self.returncode
    proc = Process()
    monkeypatch.setattr(transport.subprocess, "Popen", lambda *a, **k: proc)
    monkeypatch.setattr(transport.select, "select", lambda *a: ([123], [], []))
    monkeypatch.setattr(transport.os, "read", lambda *a: (_ for _ in ()).throw(OSError("synthetic read failure")))
    receipt = collect_process(["/fake/client"], deadline_seconds=1.0, output_cap_bytes=64)
    assert receipt.error_type == "OSError"
    assert receipt.output == b""
    assert proc.returncode is not None


def test_owner_flags_are_container_arguments_not_docker_options():
    p = TransportPlan(**plan_kwargs(entrypoint="/usr/bin/env", argv=("-i", "/usr/local/bin/python3", "-I", "-S", "-c", "print(42)")))
    command = build_create_argv(p)
    assert command[command.index("--") + 1] == IMAGE
    assert command[-len(p.argv):] == p.argv

@pytest.mark.parametrize("cpus", [0.000001, 0.0001])
def test_cpu_never_rounds_to_unlimited_zero(cpus):
    with pytest.raises(TransportPlanError):
        TransportPlan(**plan_kwargs(cpus=cpus))

def test_attached_workload_budget_and_output_are_retained():
    p = TransportPlan(**plan_kwargs(wall_clock_seconds=17.5))
    engine = FakeEngine(script={"start": [ok(stdout=b"42\n")], "inspect": [absent(CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(p))
    assert engine.calls[1]["deadline"] == 17.5
    assert "--attach" in engine.calls[1]["argv"]
    assert receipt.workload_output == b"42\n"
    assert receipt.workload_returncode == 0
    assert receipt.workload_confirmed and receipt.cleanup_confirmed

@pytest.mark.parametrize("state", [
    {"Running": False, "ExitCode": 7, "OOMKilled": False},
    {"Running": False, "ExitCode": 0, "OOMKilled": True},
    {"Running": True, "ExitCode": 0, "OOMKilled": False},
    {"Running": False, "ExitCode": True, "OOMKilled": False},
])
def test_container_state_not_client_ack_decides_success(plan, state):
    engine = FakeEngine(script={"workload_state": [ok(stdout=json.dumps([CID, state]).encode())], "inspect": [absent(CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.state is AttemptState.CLEANED_FAILURE
    assert not receipt.workload_confirmed
    assert receipt.cleanup_confirmed

def test_reconciliation_cannot_erase_original_failed_workload(plan):
    first_engine = FakeEngine(script={"start": [ok(rc=3)], "rm": [ok(rc=1)]}, expected_cid=CID)
    first = TransportOrchestrator(first_engine).execute(TransportSession(plan))
    assert first.state is AttemptState.CLEANUP_UNCERTAIN
    second_engine = FakeEngine(script={"inspect": [absent(CID)]}, expected_cid=CID)
    resolved = TransportOrchestrator(second_engine).reconcile(plan, first)
    assert resolved.state is AttemptState.CLEANED_FAILURE
    assert resolved.workload_problem == first.workload_problem
    assert not resolved.workload_confirmed
    assert resolved.execution_uncertain and resolved.reconciliation_required
    assert "create" not in subcommands(second_engine)

def test_engine_false_output_bound_is_not_trusted(plan):
    engine = FakeEngine(script={"start": [ok(stdout=b"x" * 5000)], "inspect": [absent(CID)]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.state is AttemptState.CLEANED_FAILURE
    assert len(receipt.workload_output) == 4096
    assert receipt.execution_uncertain
    assert receipt.cleanup_confirmed

def test_permission_refusal_does_not_try_stronger_cleanup_mutation(plan):
    denied = dataclasses.replace(ok(rc=1), permission_refused=True)
    engine = FakeEngine(script={"stop": [denied]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.state is AttemptState.CLEANUP_UNCERTAIN
    assert subcommands(engine)[-1] == "stop"
    assert "kill" not in subcommands(engine) and "rm" not in subcommands(engine)
    assert "permission refusal" in receipt.detail

def test_nonexact_text_is_refused_without_running_its_hooks():
    class Hook(str):
        def startswith(self, *a): raise AssertionError("hook executed")
    with pytest.raises(TransportPlanError):
        TransportPlan(**plan_kwargs(entrypoint=Hook("/bin/sh")))


def test_workload_text_cannot_freeze_cleanup_as_permission_refusal():
    assert not transport.control_permission_refusal("start", 1, b"permission denied")
    assert transport.control_permission_refusal("stop", 1, b"Error response from daemon: authorization denied")
    assert not transport.control_permission_refusal("stop", 0, b"permission denied")

def test_collector_has_no_environment_override_interface():
    with pytest.raises(TypeError):
        collect_process(["/fake/client"], deadline_seconds=1, output_cap_bytes=64, env={"SECRET": "x"})


def test_combined_control_stream_absence_is_supported(plan):
    combined = dataclasses.replace(absent(CID), stdout=absent(CID).stderr, stderr=b"")
    engine = FakeEngine(script={"inspect": [combined]}, expected_cid=CID)
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    assert receipt.workload_confirmed and receipt.cleanup_confirmed


def test_unrepresentable_number_is_typed_refusal():
    with pytest.raises(TransportPlanError):
        TransportPlan(**plan_kwargs(cpus=10 ** 10000))

def test_reviewed_fixed_probe_fits_owner_argument_budget():
    p = TransportPlan(**plan_kwargs(entrypoint="/usr/local/bin/python3", argv=("-I", "-S", "-c", "x" * 3000)))
    assert len(p.argv[-1]) == 3000


def test_fixed_python_source_can_contain_newlines_without_shell_split():
    body = "if True:\n    print(42)"
    p = TransportPlan(**plan_kwargs(entrypoint="/usr/bin/env", argv=("-i", "/usr/local/bin/python3", "-I", "-S", "-c", body)))
    assert build_create_argv(p)[-1] == body
    assert body not in build_create_argv(p)[:build_create_argv(p).index("--")]


def test_local_permission_refusal_does_not_escalate_to_kill_or_retry(monkeypatch):
    class Process:
        count = 0
        def terminate(self):
            self.count += 1
            raise PermissionError("synthetic actual signal refusal")
        def kill(self): raise AssertionError("must not escalate")
        def poll(self): return None
    process = Process()
    code, reason = transport._terminate_and_reap(process)
    assert code is None and "permission refusal" in reason
    assert process.count == 1


@pytest.mark.parametrize("change", [{"docker_binary": "/opt/bin/docker"}, {"image": "other.example/repo@sha256:" + "ef" * 32}, {"output_cap_bytes": 2048}])
def test_same_operation_changed_original_plan_rejected_before_cleanup(plan, change):
    first_engine = FakeEngine(script={"rm": [ok(rc=1)]}, expected_cid=CID)
    receipt = TransportOrchestrator(first_engine).execute(TransportSession(plan))
    changed = dataclasses.replace(plan, **change)
    second_engine = FakeEngine(expected_cid=CID)
    with pytest.raises(TransportStateError, match="plan identity"):
        TransportOrchestrator(second_engine).reconcile(changed, receipt)
    assert second_engine.calls == []

def test_contradictory_create_receipt_never_cleans_either_id(plan):
    engine = FakeEngine(script={"create": [ok(stdout=CID_STDOUT, observed=FOREIGN_CID)]})
    receipt = TransportOrchestrator(engine).execute(TransportSession(plan))
    owner = TransportOrchestrator(engine)
    assert owner.reconcile(plan, receipt) is receipt
    assert subcommands(engine) == ["create"]


@pytest.mark.parametrize("raw", [
    ABSENCE_ERROR_LINE + ABSENCE_ERROR_LINE,
    b"[]\n[]\n" + ABSENCE_ERROR_LINE,
    ABSENCE_ERROR_LINE + b"[]\n",
    b"[]\n" + ABSENCE_ERROR_LINE + b"\n",
    b"[]\r\n" + ABSENCE_ERROR_LINE,
    b"[]\n\n" + ABSENCE_ERROR_LINE,
])
def test_absence_parser_rejects_duplicate_reordered_or_extra_blank_lines(raw):
    assert not transport.parse_container_absence(raw, b"", CID)
