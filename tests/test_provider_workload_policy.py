"""Opted-in product inference must not consume native developer subscriptions.

All external SDK/account/telemetry boundaries are inert. Assertions exercise the real
provider builder and policy, not a simulated router or provider response.
"""
from __future__ import annotations

import json
import sys
import types

import pytest


@pytest.fixture(autouse=True)
def isolated_boundaries(monkeypatch):
    from engine import codex_provider, llm_auth, provider_health
    from engine.neuralweb import key_pool
    from lib import config

    touched = {"secrets": [], "codex": 0}
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setattr(llm_auth, "_oauth_pool_candidates", lambda *a, **kw: [])
    monkeypatch.setattr(key_pool, "discover_present_keys", lambda *a, **kw: [])
    monkeypatch.setattr(key_pool, "is_enabled", lambda *a, **kw: True)
    monkeypatch.setattr(key_pool, "is_cooling", lambda *a, **kw: False)
    monkeypatch.setattr(key_pool, "window_load", lambda *a, **kw: 0)
    monkeypatch.setattr(provider_health, "record_waterfall", lambda **kw: None)

    def secret(name):
        touched["secrets"].append(name)
        return "synthetic-test-credential"

    def accounts():
        touched["codex"] += 1
        return [("codex_account", None)]

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.messages = types.SimpleNamespace(create=lambda **kw: None)

    sdk = types.ModuleType("anthropic")
    sdk.Anthropic = Client
    sdk.DefaultHttpxClient = lambda **kw: object()
    monkeypatch.setitem(sys.modules, "anthropic", sdk)
    monkeypatch.setattr(config, "secret", secret)
    monkeypatch.setattr(codex_provider, "available_accounts", accounts)
    monkeypatch.setattr(codex_provider, "CodexClient", Client)
    yield touched


@pytest.mark.parametrize("profile", [
    "site_interactive", "site_batch", "portfolio_analysis", "lobe_analysis",
])
def test_site_profiles_do_not_build_subscription_rungs(profile, isolated_boundaries):
    from engine.llm_auth import build_providers

    providers = build_providers({
        "workload_profile": profile,
        "provider_order": ["oauth", "codex"],
    })
    assert providers == []
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def test_host_floor_applies_without_a_caller_profile(monkeypatch, isolated_boundaries):
    from engine.llm_auth import build_providers

    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_interactive")
    assert build_providers({"provider_order": ["oauth", "codex"]}) == []
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def test_no_implicit_codex_and_no_model_rewrite(isolated_boundaries):
    from engine.llm_auth import build_providers

    providers = build_providers({
        "workload_profile": "site_batch",
        "provider_order": ["deepseek"],
        "deepseek_model": "configured-model",
    })
    assert [p["name"] for p in providers] == ["deepseek"]
    assert providers[0]["model"] == "configured-model"
    assert isolated_boundaries == {"secrets": ["DEEPSEEK_API_KEY"], "codex": 0}


def test_explicit_empty_order_stays_empty(isolated_boundaries):
    from engine.llm_auth import build_providers

    assert build_providers({"workload_profile": "site_batch", "provider_order": []}) == []
    assert isolated_boundaries == {"secrets": [], "codex": 0}


@pytest.mark.parametrize("profile", ["unknown", "", None])
def test_invalid_profile_fails_before_secret_access(profile, isolated_boundaries):
    from engine.llm_auth import build_providers

    with pytest.raises(ValueError):
        build_providers({"workload_profile": profile, "provider_order": ["oauth"]})
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def test_native_agent_profile_is_not_an_inference_or_spawn_shortcut(isolated_boundaries):
    from engine.llm_auth import build_providers

    with pytest.raises(ValueError, match="NATIVE_AGENT_PATH_REQUIRED"):
        build_providers({
            "workload_profile": "fable_orchestration",
            "provider_order": ["oauth", "codex"],
        })
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def test_unprofiled_legacy_builder_is_unchanged():
    from engine.llm_auth import build_providers

    providers = build_providers({"provider_order": ["oauth", "anthropic"]})
    assert [p["name"] for p in providers] == ["oauth", "codex", "anthropic"]
    assert all("workload_policy" not in p for p in providers)


@pytest.mark.parametrize("order", [None, "deepseek", ["unknown"], ["deepseek", "deepseek"], [7]])
def test_profiled_order_is_explicit_and_closed(order, isolated_boundaries):
    from engine.llm_auth import build_providers
    from engine.provider_workload_policy import ProviderWorkloadPolicyError

    with pytest.raises(ProviderWorkloadPolicyError):
        build_providers({"workload_profile": "site_batch", "provider_order": order})
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def test_profile_requires_an_explicit_order(isolated_boundaries):
    from engine.llm_auth import build_providers
    from engine.provider_workload_policy import ProviderWorkloadPolicyError

    with pytest.raises(ProviderWorkloadPolicyError, match="WORKLOAD_PROVIDER_ORDER_REQUIRED"):
        build_providers({"workload_profile": "site_batch"})
    assert isolated_boundaries == {"secrets": [], "codex": 0}


@pytest.mark.parametrize("profile", ["", "unknown", "../../credentials", "site_batch\n"])
def test_invalid_host_profile_cannot_fall_back(monkeypatch, profile, isolated_boundaries):
    from engine.llm_auth import build_providers
    from engine.provider_workload_policy import ProviderWorkloadPolicyError

    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", profile)
    with pytest.raises(ProviderWorkloadPolicyError):
        build_providers({"provider_order": ["oauth", "codex"]})
    assert isolated_boundaries == {"secrets": [], "codex": 0}


def _policy_file(tmp_path):
    from engine.provider_workload_policy import DEFAULT_POLICY_PATH

    document = json.loads(DEFAULT_POLICY_PATH.read_text())
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(document))
    return path, document


def test_caller_can_only_narrow_the_host_floor(tmp_path):
    from engine.provider_workload_policy import decide_workload

    path, document = _policy_file(tmp_path)
    document["profiles"]["site_interactive"]["allowed_providers"] = ["deepseek"]
    path.write_text(json.dumps(document))
    decision = decide_workload({
        "workload_profile": "site_batch",
        "provider_order": ["anthropic", "deepseek", "oauth", "codex", "ollama"],
    }, host_profile="site_interactive", policy_path=path)
    assert decision.allowed_order == ("deepseek",)
    assert decision.denied_order == ("anthropic", "oauth", "codex", "ollama")
    assert decision.profiles == ("site_interactive", "site_batch")


def test_same_process_policy_reload_changes_content_identity_and_eligibility(tmp_path):
    from engine.provider_workload_policy import decide_workload

    path, document = _policy_file(tmp_path)
    cfg = {"workload_profile": "site_batch", "provider_order": ["anthropic", "deepseek"]}
    before = decide_workload(cfg, policy_path=path)
    document["profiles"]["site_batch"]["allowed_providers"] = ["deepseek"]
    document["revision"] += 1
    path.write_text(json.dumps(document))
    after = decide_workload(cfg, policy_path=path)
    assert before.allowed_order == ("anthropic", "deepseek")
    assert after.allowed_order == ("deepseek",)
    assert before.policy_hash != after.policy_hash
    assert after.policy_revision == before.policy_revision + 1


def test_whitespace_does_not_change_policy_identity(tmp_path):
    from engine.provider_workload_policy import decide_workload

    path, document = _policy_file(tmp_path)
    cfg = {"workload_profile": "site_batch", "provider_order": ["deepseek"]}
    before = decide_workload(cfg, policy_path=path)
    path.write_text(json.dumps(document, indent=4, sort_keys=True))
    assert decide_workload(cfg, policy_path=path) == before


def test_receipt_is_closed_and_does_not_capture_caller_data():
    from engine.provider_workload_policy import decide_workload

    decision = decide_workload({
        "workload_profile": "site_batch", "provider_order": ["oauth", "deepseek"],
        "api_key": "synthetic-sensitive-value", "prompt": "private user data",
    }, host_profile="site_batch")
    receipt = decision.receipt()
    assert set(receipt) == {
        "schema", "policy_revision", "policy_hash", "profiles", "execution_surface",
        "allowed_order", "denied_order",
    }
    assert receipt["profiles"] == ["site_batch"]
    assert receipt["allowed_order"] == ["deepseek"]
    assert receipt["denied_order"] == ["oauth"]
    assert "synthetic-sensitive-value" not in json.dumps(receipt)
    assert "private user data" not in json.dumps(receipt)
    receipt["allowed_order"].clear()
    assert decision.receipt()["allowed_order"] == ["deepseek"]


def test_internal_descriptors_get_only_the_closed_policy_receipt():
    from engine.llm_auth import build_providers

    providers = build_providers({
        "workload_profile": "site_interactive",
        "provider_order": ["deepseek", "anthropic"],
        "respect_provider_cooling": False,
    })
    assert [p["name"] for p in providers] == ["deepseek", "anthropic"]
    assert providers[0]["workload_policy"] == providers[1]["workload_policy"]
    assert providers[0]["workload_policy"] is not providers[1]["workload_policy"]
    assert "synthetic-test-credential" not in json.dumps(providers[0]["workload_policy"])


def test_unprofiled_legacy_path_does_not_need_the_new_manifest(tmp_path):
    from engine.provider_workload_policy import decide_workload

    assert decide_workload({}, policy_path=tmp_path / "absent.json") is None


@pytest.mark.parametrize("change", [
    "schema", "owner", "revision_bool", "revision_zero", "root_extra", "row_extra",
    "subscription_rung", "duplicate_rung", "unknown_surface", "native_with_api",
    "invalid_profile_name", "empty_profiles",
])
def test_malformed_or_broadened_manifest_is_refused(tmp_path, change):
    from engine.provider_workload_policy import ProviderWorkloadPolicyError, load_policy

    path, document = _policy_file(tmp_path)
    row = document["profiles"]["site_batch"]
    if change == "schema":
        document["schema"] = "wrong"
    elif change == "owner":
        document["owner_program"] = "second-router"
    elif change == "revision_bool":
        document["revision"] = True
    elif change == "revision_zero":
        document["revision"] = 0
    elif change == "root_extra":
        document["credentials"] = "synthetic-sensitive-value"
    elif change == "row_extra":
        row["credentials"] = "synthetic-sensitive-value"
    elif change == "subscription_rung":
        row["allowed_providers"] = ["oauth"]
    elif change == "duplicate_rung":
        row["allowed_providers"] = ["deepseek", "deepseek"]
    elif change == "unknown_surface":
        row["execution_surface"] = "shell"
    elif change == "native_with_api":
        document["profiles"]["fable_orchestration"]["allowed_providers"] = ["anthropic"]
    elif change == "invalid_profile_name":
        document["profiles"]["../secret"] = row
    elif change == "empty_profiles":
        document["profiles"] = {}
    path.write_text(json.dumps(document))
    with pytest.raises(ProviderWorkloadPolicyError) as caught:
        load_policy(path)
    assert "synthetic-sensitive-value" not in str(caught.value)
    assert str(path) not in str(caught.value)


@pytest.mark.parametrize("body", ['{"revision":1,"revision":2}', '{"revision":NaN}', '[]', '{bad'])
def test_bad_json_is_bounded_and_fail_closed(tmp_path, body):
    from engine.provider_workload_policy import ProviderWorkloadPolicyError, load_policy

    path = tmp_path / "policy.json"
    path.write_text(body)
    with pytest.raises(ProviderWorkloadPolicyError):
        load_policy(path)


def test_oversized_policy_is_refused(tmp_path):
    from engine.provider_workload_policy import MAX_POLICY_BYTES, ProviderWorkloadPolicyError, load_policy

    path = tmp_path / "policy.json"
    path.write_bytes(b" " * (MAX_POLICY_BYTES + 1))
    with pytest.raises(ProviderWorkloadPolicyError, match="WORKLOAD_POLICY_TOO_LARGE"):
        load_policy(path)


def test_missing_policy_is_not_an_allow_all_fallback(tmp_path):
    from engine.provider_workload_policy import ProviderWorkloadPolicyError, decide_workload

    with pytest.raises(ProviderWorkloadPolicyError, match="WORKLOAD_POLICY_UNAVAILABLE"):
        decide_workload({"workload_profile": "site_batch", "provider_order": ["oauth"]},
                        policy_path=tmp_path / "missing.json")


def test_json_integer_limit_is_a_typed_configuration_refusal(tmp_path):
    from engine.provider_workload_policy import ProviderWorkloadPolicyError, load_policy

    path = tmp_path / "policy.json"
    path.write_text('{"revision":' + "1" * 5000 + '}')
    with pytest.raises(ProviderWorkloadPolicyError, match="WORKLOAD_POLICY_JSON_INVALID"):
        load_policy(path)


@pytest.mark.parametrize("job_name", [
    "biocatalyst-history", "biocatalyst-serving", "flow-surface",
    "unrun-government-revenue-grader", "unrun-picks-boards",
])
def test_existing_curated_jobs_cover_the_new_shared_dependency(job_name):
    # The hosted contract-delta gate found these real transitive consumers of
    # llm_auth. Keep their existing exclusive scopes additive, never bypassed.
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    jobs = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())["jobs"]
    paths = jobs[job_name]["paths"]
    assert "engine/provider_workload_policy.py" in paths
    assert "config/**" in paths or "config/provider_workloads.v1.json" in paths


def test_workload_guard_executes_in_the_real_pull_request_code_packs():
    # R7179-R1: a gate-free inventory marked this suite RUN even though it
    # existed only in the nightly data gate. Exercise the real gate loader
    # and pack partitioner, and require an executable, unconditional step.
    import shlex
    from pathlib import Path
    from scripts.run_ci_pack import load_legacy_jobs, partition_jobs

    root = Path(__file__).resolve().parents[1]
    manifest = root / ".github/ci/legacy-jobs.yml"
    command = ["python", "-m", "pytest", "tests/test_provider_workload_policy.py", "-q"]
    matches = []
    for pack in partition_jobs(load_legacy_jobs(manifest, gate="code"), 12):
        for job in pack:
            for step in job.definition["steps"]:
                if shlex.split(step.get("run", ""), comments=True) == command:
                    matches.append((job, step))
    assert len(matches) == 1, "workload guard must execute exactly once in PR code packs"
    job, step = matches[0]
    assert job.gate == "code"
    assert "if" not in step
    assert not step.get("continue-on-error", False)
    assert next(j for j in load_legacy_jobs(manifest)
                if j.job_id == "capability-broker").gate == "data"
