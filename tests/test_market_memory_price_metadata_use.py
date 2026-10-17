"""Discriminating tests for the installed price-metadata CLI composition.

All authorization here is explicitly synthetic (workspace fixtures and injected
verifier doubles).  No test claims that a mock is production authorization; the
production main is only the exact installed script under /opt/macro with euid 0,
and its environment gate is tested by rejection.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_technical_observation as obs
from engine.neuralweb import market_memory_technical_store as store
from engine.neuralweb import market_memory_price_metadata_use as use
from scripts import inspect_market_memory_price_coverage as cli
from tests import test_market_memory_technical_store as fixtures

REPO = Path(__file__).resolve().parents[1]
SOURCE_REPO = REPO
_FAILURES = (
    "usage",
    "environment",
    "policy_denied",
    "policy_qualification_failed",
    "store_unavailable",
    "read_budget_exhausted",
    "output_limit_exceeded",
    "wall_clock_limit_exceeded",
    "inspection_failed",
)
_FORBIDDEN_OUTPUT_MARKERS = (
    "start_close",
    "end_close",
    '"value"',
    '"state"',
    "object_key",
    "technicals-v1/",
    '"url"',
    "etag_md5",
    '"close"',
    "forecast",
    "returns",
)


def _workspace_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


class _FakeVerifier:
    """Synthetic closure verifier double; never production authorization."""

    def __init__(self, closure: dict | None = None):
        self.closure = closure or {
            "deployed_head": "0" * 40,
            "modules": {},
            "git_sources": {},
        }
        self.calls = 0
        self.drift_from = None
        self.fail = False

    def __call__(self, repository_root, *, expected_head):
        self.calls += 1
        if self.fail:
            raise use.MarketMemoryPriceMetadataPolicyError("synthetic outage")
        if self.drift_from is not None and self.calls >= self.drift_from:
            drifted = json.loads(json.dumps(self.closure))
            drifted["git_sources"].setdefault("technical_price_basis_contract", {})["sha256"] = "f" * 64
            return drifted
        return json.loads(json.dumps(self.closure))


@pytest.fixture(scope="module")
def installed_repo(tmp_path_factory):
    """Real Git closure fixture, containing the candidate bytes, no stubs."""
    root = tmp_path_factory.mktemp("metadata-installed")
    for relative in (*use._CLOSURE_CODE_MODULE_PATHS.values(), *use._CLOSURE_GIT_SOURCE_PATHS.values()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_REPO / relative, target)
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    for args in (("init", "-q"), ("add", "."),
                 ("-c", "user.name=Synthetic test", "-c", "user.email=test@example.invalid",
                  "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Synthetic installed closure")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)
    return root


@pytest.fixture
def pinned(tmp_path, monkeypatch, installed_repo):
    monkeypatch.setitem(globals(), "REPO", installed_repo)
    root, stored = fixtures._capture(tmp_path, monkeypatch)
    pin = store.pin_technical_actual_output_generation(root)
    argv = [
        "--store-id",
        pin.store_id,
        "--generation-id",
        pin.generation_id,
        "--generation-sha256",
        pin.generation_sha256,
        "--source-observation-id",
        pin.captures[0].source_observation_id,
    ]
    return root, pin, argv


def _run(root, argv, monkeypatch=None):
    return cli._run_inspection(repository_root=REPO, store_root=root, argv=argv)


def _policy(pin, **kwargs):
    defaults = dict(
        repository_root=REPO,
        expected_head=_workspace_head(),
        store_id=pin.store_id,
        generation_id=pin.generation_id,
        generation_sha256=pin.generation_sha256,
        source_observation_id=pin.captures[0].source_observation_id,
    )
    defaults.update(kwargs)
    return use.RetainedSourceBarMetadataUsePolicy(**defaults)


def test_cli_discloses_whitelisted_metadata_only(pinned, monkeypatch):
    root, pin, argv = pinned

    def forbidden(*args, **kwargs):
        pytest.fail("price-bearing or mutating owner path was invoked")

    monkeypatch.setattr(store, "_load_capture", forbidden)
    monkeypatch.setattr(store, "capture_technical_actual_output", forbidden)
    monkeypatch.setattr(store, "initialize_technical_actual_output_store", forbidden)
    monkeypatch.setattr(
        store, "observe_technical_actual_output_generation_head", forbidden
    )
    monkeypatch.setattr(obs, "project_current_spy_raw_close_ratio", forbidden)
    monkeypatch.setattr(obs, "validate_technical_snapshot_bundle", forbidden)
    monkeypatch.setattr(obs, "_read_spy_parquet", forbidden)
    original_read = obs.pq.ParquetFile.read

    def date_only(self, *args, **kwargs):
        assert not args and kwargs == {"columns": ["date"], "use_threads": False}
        return original_read(self, **kwargs)

    monkeypatch.setattr(obs.pq.ParquetFile, "read", date_only)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 0 and payload.endswith(b"\n") and payload.count(b"\n") == 1
    assert len(payload) <= 1024 * 1024
    value = json.loads(payload)
    assert value["schema"] == cli.INSPECTION_SCHEMA
    assert set(value) == {
        "schema",
        "policy_id",
        "profile",
        "store_id",
        "generation_id",
        "generation_sha256",
        "source_observation_id",
        "capture_id",
        "capture_receipt_sha256",
        "revision_id",
        "source_commit",
        "session",
        "bar_sessions",
        "first_observed_at",
        "available_at",
        "freshness",
        "subject",
        "calendar",
        "price_basis",
        "transform_version",
        "source_observation_sha256",
        "source_bodies",
        "feature_ref",
        "feature_body_read",
        "source_closure",
        "flags",
    }
    text = payload.decode("utf-8")
    assert not any(marker in text for marker in _FORBIDDEN_OUTPUT_MARKERS)
    assert value["bar_sessions"] == [
        item.isoformat() for item in fixtures._sessions()
    ]
    assert value["session"] == "2026-08-07"
    assert value["available_at"] == value["first_observed_at"] == (
        "2026-08-10T02:00:00Z"
    )
    assert value["freshness"]["policy"].endswith("max_one_lag.v1")
    assert value["feature_body_read"] is False
    assert value["flags"] == {
        "price_values_read": False,
        "feature_body_read": False,
        "writes": False,
        "evaluation": False,
        "operational_study_admission": False,
    }
    assert set(value["source_bodies"]) == {
        "publish_manifest",
        "spy_daily_parquet",
        "canary_identity_config",
        "xnys_calendar_module",
        "massive_entitlement_record",
        "technical_price_basis_contract",
    }
    assert set(value["feature_ref"]) == {"snapshot_id", "sha256", "bytes"}
    assert value["source_closure"]["deployed_head"] == _workspace_head()
    assert value["source_closure"]["git_sources"][
        "massive_entitlement_record"
    ]["sha256"] == store._GIT_SOURCE_SHA256["massive_entitlement_record"]


def test_owner_budget_is_unchanged_and_store_bytes_never_written(pinned, monkeypatch):
    root, pin, argv = pinned
    observed_limits = []
    original_scope = pit.bounded_owner_reads

    def scope(*, maximum_bytes):
        observed_limits.append(maximum_bytes)
        return original_scope(maximum_bytes=maximum_bytes)

    monkeypatch.setattr(pit, "bounded_owner_reads", scope)
    before = fixtures._tree(root)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 0
    assert observed_limits and set(observed_limits) == {64 * 1024 * 1024}
    assert fixtures._tree(root) == before


def test_missing_or_extra_arguments_are_usage_failures(pinned):
    root, pin, argv = pinned
    code, payload = _run(root, argv[1:], None)
    assert code == 2
    assert json.loads(payload)["failure"] == "usage"
    code, payload = _run(root, [*argv, "--store-root", "/tmp/evil"], None)
    assert code == 2 and json.loads(payload)["failure"] == "usage"


def test_exact_identity_is_required_and_latest_fallback_never_happens(pinned):
    root, pin, argv = pinned
    wrong_sha = replace(pin, generation_sha256="0" * 64)
    code, payload = _run(
        root,
        [
            "--store-id",
            pin.store_id,
            "--generation-id",
            pin.generation_id,
            "--generation-sha256",
            wrong_sha.generation_sha256,
            "--source-observation-id",
            pin.captures[0].source_observation_id,
        ],
        None,
    )
    assert code == 1
    value = json.loads(payload)
    assert value["failure"] == "store_unavailable"
    assert set(value) == {"schema", "failure", "policy_id"}

    unpublished = "mmactualgeneration_" + "e" * 64
    code, payload = _run(
        root,
        [
            "--store-id",
            pin.store_id,
            "--generation-id",
            unpublished,
            "--generation-sha256",
            "a" * 64,
            "--source-observation-id",
            pin.captures[0].source_observation_id,
        ],
        None,
    )
    assert code == 1
    assert json.loads(payload)["failure"] in _FAILURES


def test_policy_denial_precedes_any_private_store_io(pinned, monkeypatch):
    root, pin, argv = pinned
    verifier = _FakeVerifier()
    policy = _policy(pin, closure_verifier=verifier)
    verifier.fail = True

    def forbidden(*args, **kwargs):
        pytest.fail("private IO before authorization")

    monkeypatch.setattr(
        store, "validate_technical_actual_output_store_root", forbidden
    )
    with pytest.raises(PermissionError):
        policy.check("read_retained_source_bar_metadata", policy.resource)

    def outage(*_args, **_kwargs):
        raise use.MarketMemoryPriceMetadataPolicyError("synthetic outage")

    monkeypatch.setattr(use, "verify_installed_price_metadata_closure", outage)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 1 and json.loads(payload)["failure"] == "policy_qualification_failed"


def test_policy_denies_unknown_action_and_resource_drift(pinned):
    root, pin, argv = pinned
    policy = _policy(pin)
    drifts = [
        ("read_source_bar_metadata", policy.resource),
        ("read_retained_source_bar_metadata ", policy.resource),
        ("read_retained_source_bar_metadata", {**policy.resource, "extra": True}),
        (
            "read_retained_source_bar_metadata",
            {
                key: value
                for key, value in policy.resource.items()
                if key != "profile"
            },
        ),
        (
            "read_retained_source_bar_metadata",
            dict(policy.resource, generation_sha256="0" * 64),
        ),
        ("disclose_retained_source_bar_metadata", dict(policy.resource, profile="x")),
    ]
    for action, resource in drifts:
        with pytest.raises(PermissionError):
            policy.check(action, resource)
    assert policy.check(
        "disclose_retained_source_bar_metadata", policy.resource
    ) is True


def test_exact_one_source_identity_is_enforced_before_private_io(pinned, monkeypatch):
    root, pin, argv = pinned
    other_source = "mmtechsrc_" + "1" * 64
    policy = _policy(pin, source_observation_id=other_source)

    def forbidden(*args, **kwargs):
        pytest.fail("private IO before authorization")

    monkeypatch.setattr(
        store, "validate_technical_actual_output_store_root", forbidden
    )
    with pytest.raises(PermissionError):
        store.read_retained_source_bar_metadata(
            root,
            technical_pin=pin,
            source_observation_id=pin.captures[0].source_observation_id,
            policy=policy,
        )


def test_current_grant_or_basis_drift_after_read_denies_disclosure(pinned):
    root, pin, argv = pinned
    verifier = _FakeVerifier({"deployed_head": _workspace_head(), "modules": {}, "git_sources": {}})
    policy = _policy(pin, closure_verifier=verifier)
    capability = store.read_retained_source_bar_metadata(
        root,
        technical_pin=pin,
        source_observation_id=pin.captures[0].source_observation_id,
        policy=policy,
    )
    assert verifier.calls >= 2
    verifier.drift_from = verifier.calls + 1
    with pytest.raises(PermissionError):
        store.disclose_retained_source_bar_metadata(capability, policy=policy)

    code, payload = _run(root, argv, None)
    assert code == 0  # the CLI path itself remains intact under its own verifier


def test_cli_drift_after_read_returns_typed_policy_failure(pinned, monkeypatch):
    root, pin, argv = pinned
    real = use.verify_installed_price_metadata_closure
    calls = {"n": 0}

    def drifting(root_arg, *, expected_head):
        calls["n"] += 1
        closure = real(root_arg, expected_head=expected_head)
        if calls["n"] >= 6:  # qualification, pre-read check, read checks, disclose
            closure["git_sources"]["technical_price_basis_contract"]["sha256"] = "f" * 64
        return closure

    monkeypatch.setattr(use, "verify_installed_price_metadata_closure", drifting)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 1
    assert json.loads(payload)["failure"] == "policy_denied"
    assert calls["n"] >= 6


def test_deployed_head_mismatch_refuses_qualification(pinned):
    root, pin, argv = pinned
    with pytest.raises(use.MarketMemoryPriceMetadataPolicyError, match="HEAD"):
        _policy(pin, expected_head="0" * 64)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"platform": "darwin"},
        {"euid": 1000},
        {"script": False},
    ],
)
def test_production_main_rejects_non_linux_non_root_or_wrong_script(
    pinned, monkeypatch, kwargs
):
    root, pin, argv = pinned
    monkeypatch.setattr(cli.os, "geteuid", lambda: kwargs.get("euid", 0))
    monkeypatch.setattr(cli.sys, "platform", kwargs.get("platform", "linux"))
    if not kwargs.get("script", True):
        monkeypatch.setattr(
            cli,
            "INSTALLED_SCRIPT_PATH",
            Path(__file__).resolve(),
        )
    with pytest.raises(cli._ProductionEnvironmentError):
        cli._verify_production_environment()
    code = cli.main(argv)
    assert code == 1


@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="the environment gate only trips for the non-root workspace invocation",
)
def test_main_gate_blocks_this_workspace_copy_without_runtime_error(pinned, capsys):
    root, pin, argv = pinned
    code = cli.main(argv)
    assert code == 1
    payload = capsys.readouterr().out
    value = json.loads(payload)
    assert value["failure"] == "environment"
    assert set(value) == {"schema", "failure", "policy_id"}


def test_environment_cannot_grant_an_alternate_store_root(pinned, monkeypatch):
    root, pin, argv = pinned
    rogue = root.parents[0] / "rogue-store"
    monkeypatch.setenv("MARKET_MEMORY_TECHNICAL_STORE_DIR", str(rogue))
    code, payload = _run(root, argv, monkeypatch)
    assert code == 0
    assert not rogue.exists()
    assert json.loads(payload)["store_id"] == pin.store_id


def test_no_network_transport_is_possible(pinned, monkeypatch):
    root, pin, argv = pinned

    def forbidden(*args, **kwargs):
        pytest.fail("network transport was attempted")

    monkeypatch.setattr(obs.requests, "Session", forbidden)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 0


def test_output_limit_is_enforced_without_disclosure(pinned, monkeypatch):
    root, pin, argv = pinned
    monkeypatch.setattr(cli, "_OUTPUT_BYTE_LIMIT", 16)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 1
    assert json.loads(payload)["failure"] == "output_limit_exceeded"


def test_wall_clock_bound_is_typed_and_nonzero(pinned, monkeypatch):
    root, pin, argv = pinned

    def exhausted(argv):
        raise cli._WallClockExceeded

    monkeypatch.setattr(cli, "_parse_invocation", exhausted)
    code, payload = _run(root, argv, monkeypatch)
    assert code == 1
    assert json.loads(payload)["failure"] == "wall_clock_limit_exceeded"


def test_policy_qualification_is_repeatable_and_immutable(pinned):
    root, pin, argv = pinned
    policy = _policy(pin)
    first = policy.qualified_closure
    assert policy.resource == policy.resource
    assert policy.qualified_closure == first
    assert first["deployed_head"] == _workspace_head()
    assert use.POLICY_ID == policy.policy_id
    assert set(first["modules"]) == {
        "price_metadata_use_policy",
        "price_metadata_cli",
        "technical_store",
        "technical_observation",
        "technical_pit_kernel",
    }
    assert set(first["git_sources"]) == set(store._GIT_SOURCE_SHA256)


def test_policy_captures_current_deployment_then_rejects_head_change(pinned, monkeypatch):
    _, pin, _ = pinned
    policy = _policy(pin, expected_head=None)
    assert policy.qualified_closure["deployed_head"] == _workspace_head()
    original = use._git_bounded
    def changed(root, *args):
        if args == ("rev-parse", "--verify", "HEAD^{commit}"):
            return "f" * 40 + "\n"
        return original(root, *args)
    monkeypatch.setattr(use, "_git_bounded", changed)
    with pytest.raises(PermissionError):
        policy.check("disclose_retained_source_bar_metadata", policy.resource)


def test_git_qualification_disables_lazy_fetch_and_optional_writes(monkeypatch):
    calls = []
    def capture(args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
    monkeypatch.setattr(use.subprocess, "run", capture)
    assert use._git_bounded(Path("/synthetic"), "rev-parse", "HEAD").strip() == "a" * 40
    assert calls[0]["env"]["GIT_NO_LAZY_FETCH"] == "1"
    assert calls[0]["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    assert calls[0]["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_symlinked_install_root_refused(pinned, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(REPO, target_is_directory=True)
    with pytest.raises(use.MarketMemoryPriceMetadataPolicyError, match="symlink"):
        use.verify_installed_price_metadata_closure(alias, expected_head=_workspace_head())


def test_grant_change_during_serialization_prevents_stdout_payload(pinned, monkeypatch):
    root, _, argv = pinned
    original_serialize = cli._serialize
    grant = REPO / use._CLOSURE_GIT_SOURCE_PATHS["massive_entitlement_record"]
    original_grant = grant.read_bytes()
    def serialize_then_revoke(output):
        payload = original_serialize(output)
        grant.write_bytes(original_grant + b"\nSynthetic revocation\n")
        return payload
    monkeypatch.setattr(cli, "_serialize", serialize_then_revoke)
    try:
        code, payload = _run(root, argv)
    finally:
        grant.write_bytes(original_grant)
    assert code == 1 and json.loads(payload)["failure"] == "policy_denied"
    assert "bar_sessions" not in json.loads(payload)


def test_output_bound_includes_newline(monkeypatch):
    monkeypatch.setattr(cli, "_OUTPUT_BYTE_LIMIT", 2)
    with pytest.raises(OverflowError):
        cli._serialize({})


def test_bad_arguments_do_not_echo_private_text(pinned, capsys):
    root, _, argv = pinned
    code, payload = _run(root, [*argv, "--private-path=/do/not/disclose"])
    assert code == 2 and json.loads(payload)["failure"] == "usage"
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
