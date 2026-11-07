"""Cortex AUTO composed with its real durable/tool/memo owners and current A/B."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from engine import fabric_inference_client as transport, llm_auth as auth, provider_health
from engine import provider_production_modes as owner
from engine.neuralweb import cortex as cx, metabolism
from lib import ai_costs
from tests import test_cortex_fabric_composition as fixed
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL  # noqa: F401
from tests.test_fabric_workload_auto_composition import auto_workloads  # noqa: F401

_USAGE_WRITER = ai_costs.record_usage
_HEALTH_WRITER = provider_health.record_attempt
_CLIENT = transport.FabricInferenceClient


@pytest.fixture
def cortex_auto(auto_workloads, tmp_path_factory, monkeypatch):
    state = auto_workloads
    for grant in state.native.document["application_grants"]:
        if grant["principal_id"] == "macro_analysis_fabric":
            grant["max_steps"] = 8
    state.native.save()
    monkeypatch.setattr(auth, "_repo_root", lambda: state.root / "wrong-module-root")
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setattr(provider_health, "record_attempt", _HEALTH_WRITER)
    telemetry = tmp_path_factory.mktemp("cortex-auto-telemetry")
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(telemetry))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(telemetry / "health.jsonl"))
    monkeypatch.delenv("PROVIDER_HEALTH_DISABLED", raising=False)
    state.cost_path = telemetry / "data/ai_costs/usage.jsonl"
    state.health_path = telemetry / "health.jsonl"
    state.path = state.root / "data/neuralweb/cortex/last_run_state.json"
    state.path.parent.mkdir(parents=True)
    (state.root / "site/neuralweb").mkdir(parents=True)
    (state.root / "data/neuralweb/world_state.json").write_text(json.dumps({
        "inputs_hash": "input-original", "as_of": "2026-01-01", "verdict": "context only"}))
    state.cfg = {"application_fabric_mode": "shared_fabric", "workload_profile": "lobe_analysis",
                 "max_tool_calls": 4, "max_tokens": 128}
    (state.root / "config.yml").write_text(json.dumps({"cortex": state.cfg}))
    monkeypatch.setattr(cx, "_cfg", lambda root: state.cfg)
    state.native_builder = Mock(side_effect=AssertionError("native provider discovery"))
    state.native_fallback = Mock(side_effect=AssertionError("native fallback"))
    monkeypatch.setattr(cx, "_build_providers", state.native_builder)
    monkeypatch.setattr(cx, "_single_call_fallback", state.native_fallback)
    state.responses = [fixed.packet(fixed.tool("read_world_state", identifier="read-1")),
        fixed.packet(fixed.tool("write_memo", {"summary": "The original context remains uncertain."}, "memo-1")),
        fixed.packet()]
    def respond():
        index = len(state.native.posts) - 1
        state.native.response = state.responses[min(index, len(state.responses) - 1)]
    state.native.on_upstream = respond
    return state


def test_auto_public_loop_has_original_requests_actual_identity_and_closed_business_memo(cortex_auto):
    state = cortex_auto
    fixed.test_public_loop_retains_full_history_one_real_turn_usage_and_closed_memo(state)
    run = fixed.record(state)
    assert run["schema"] == cx._FABRIC_AUTO_RUN_SCHEMA
    assert run["inspection"]["requested_model"] is None
    assert run["request_payload"]["system"] == cx._SYSTEM_PROMPT
    assert run["route_identity"]["pool"] == "go"
    turn = state.native.rows("application_turns")[0]
    assert turn["principal_id"] == "macro_analysis_fabric"
    for step in run["steps"]:
        original = cx._fabric_auto_request(run, step)
        doc = step["application_observation"]
        assert step["normalized_request_digest"] == transport._auto_request_digest(original)
        assert step["routed_request_digest"] == transport._auto_request_digest(dict(original, model=MODEL))
        assert doc["request_id"] == step["request_id"] and doc["serving_model"] == MODEL
    status = run["memo"]["document"]["run_status"]
    assert status["model_used"] == MODEL and status["pool"] == "go" and status["provider"] == "fabric"
    assert all(row["provider"] == "go" and row["cost_basis"] == "unknown"
               for row in fixed.rows(state.cost_path))


@pytest.mark.parametrize("value", [None, "", MODEL, "another-model", [], False])
def test_any_explicit_required_model_cannot_be_ignored_by_auto(cortex_auto, value):
    state = cortex_auto
    state.cfg["llm_model"] = value
    fixed.call(state)
    assert not state.path.exists() and not state.events and not state.native.posts
    fixed.no_native(state)


def test_completed_auto_input_reuse_and_changed_input_keep_original_custody(cortex_auto):
    state = cortex_auto
    fixed.call(state)
    original = fixed.record(state)
    before = (list(state.events), len(state.native.posts), len(fixed.rows(state.cost_path)))
    fixed.call(state, force=True)
    assert (state.events, len(state.native.posts), len(fixed.rows(state.cost_path))) == before
    (state.root / "data/neuralweb/world_state.json").write_text('{"inputs_hash":"changed-input"}')
    state.responses = [fixed.packet()]
    fixed.call(state, force=True)
    next_run = fixed.record(state)
    assert next_run["operation_id"] != original["operation_id"]
    assert next_run["phase"] == "complete" and len(state.native.rows("application_turns")) == 2
    assert len(state.closes) == 2


def test_auto_later_failed_step_does_not_reuse_prior_routing_or_usage(cortex_auto, monkeypatch):
    fixed.test_later_failed_step_does_not_inherit_the_previous_usage_observation(cortex_auto, monkeypatch)
    run = fixed.record(cortex_auto)
    assert run["steps"][0]["application_observation"] is not None
    assert run["steps"][1]["application_observation"] is None
    assert run["steps"][1]["routed_request_digest"] is None


def test_auto_unknown_close_retains_original_memo_without_healthy_projection(cortex_auto, monkeypatch):
    fixed.test_unknown_close_retains_paid_memo_without_healthy_projection(cortex_auto, monkeypatch)
    run = fixed.record(cortex_auto)
    assert run["route_identity"]["selected_model"] == MODEL
    assert all(step["application_observation"] is not None for step in run["steps"])


def test_auto_lost_business_ack_preserves_original_tool_intent(cortex_auto, monkeypatch):
    fixed.test_lost_tool_acknowledgment_does_not_repeat_real_attention_write(cortex_auto, monkeypatch)


@pytest.mark.parametrize("stage", ["before-intent", "after-response", "after-tool", "final-projection", "final-state"])
def test_auto_persistence_ack_loss_never_replays_original_effect(cortex_auto, monkeypatch, stage):
    fixed.test_persistence_acknowledgement_loss_never_replays_effects(cortex_auto, monkeypatch, stage)


@pytest.mark.parametrize("invalid", ["unknown", "duplicate", "provenance", "nested-type"])
def test_auto_valid_first_tool_does_not_run_before_whole_batch_validation(cortex_auto, monkeypatch, invalid):
    fixed.test_invalid_whole_batch_does_not_execute_the_preceding_valid_write(cortex_auto, monkeypatch, invalid)


@pytest.mark.parametrize("profile", ["site_interactive", "site_batch", "portfolio_analysis"])
def test_host_policy_intersection_keeps_actual_analysis_authority(cortex_auto, monkeypatch, profile):
    fixed.test_host_profile_intersection_uses_real_allowed_providers(cortex_auto, monkeypatch, profile)
    assert cortex_auto.native.rows("application_turns")[0]["principal_id"] == "macro_analysis_fabric"


@pytest.mark.parametrize("corruption", ["discriminator", "payload_system", "payload_tools",
    "original_digest", "routed_digest", "route_freeze", "actual_model", "raw_usage", "memo_pool",
    "scope", "missing_observation"])
def test_checksum_valid_auto_corruption_cannot_trigger_new_model_or_business_work(cortex_auto, monkeypatch, corruption):
    state = cortex_auto
    fixed.call(state)
    value = json.loads(state.path.read_text())
    assert value["fabric"]["phase"] == "complete"
    run, step = value["fabric"], value["fabric"]["steps"][0]
    doc = step["application_observation"]
    if corruption == "discriminator":
        del run["schema"]
    elif corruption == "payload_system":
        run["request_payload"]["system"] += "changed"
    elif corruption == "payload_tools":
        run["request_payload"]["tools"] = []
    elif corruption == "original_digest":
        step["normalized_request_digest"] = doc["routing"]["request_digest"] = "a" * 64
    elif corruption == "routed_digest":
        step["routed_request_digest"] = doc["routing"]["routed_request_digest"] = "b" * 64
    elif corruption == "route_freeze":
        run["route_identity"]["selection_digest"] = "c" * 64
    elif corruption == "actual_model":
        doc["serving_model"] = "different"
    elif corruption == "raw_usage":
        doc["usage"]["input_tokens"] += 1
    elif corruption == "memo_pool":
        run["memo"]["document"]["run_status"]["pool"] = "codex"
        run["memo"]["document_sha256"] = cx._fabric_digest(run["memo"]["document"])
        run["projection"]["params"]["run_status"]["pool"] = "codex"
    elif corruption == "scope":
        doc["routing"]["route_scope"]["pools"] = ["codex-native"]
    else:
        step["application_observation"] = None
        step["routed_request_digest"] = None
    value["sha256"] = cx._fabric_digest({k: v for k, v in value.items() if k != "sha256"})
    state.path.write_bytes(cx._fabric_json_bytes(value))
    before = (state.path.read_bytes(), list(state.events), len(state.native.posts), fixed.rows(state.cost_path))
    state.cfg.clear()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    fixed.call(state, force=True)
    assert (state.path.read_bytes(), state.events, len(state.native.posts), fixed.rows(state.cost_path)) == before
    fixed.no_native(state)


def test_actual_mismatched_terminal_keeps_usage_and_model_without_success(cortex_auto, monkeypatch):
    state = cortex_auto
    state.responses = [fixed.packet(model="observed-other")]
    fixed.call(state)
    run = fixed.record(state)
    assert run["phase"] == "held"
    step = run["steps"][0]
    assert step["response"] is None and step["observation"]["serving_model"] == "observed-other"
    assert step["application_observation"]["serving_model"] == "observed-other"
    cost = fixed.rows(state.cost_path)
    assert len(cost) == 1 and cost[0]["model"] == "observed-other"
    assert cost[0]["input_tokens"] == 11 and cost[0]["cost_basis"] == "unknown"
    fixed.held_no_replay(state, monkeypatch)


def test_missing_usage_stays_nullable_without_a_zero_ledger_row(cortex_auto):
    fixed.test_missing_usage_is_nullable_evidence_and_cannot_be_logged_as_zero(cortex_auto)


def test_auto_dispatch_uses_payload_frozen_before_claim_not_late_globals(cortex_auto, monkeypatch):
    state = cortex_auto
    commit = cx._fabric_commit
    original_system, original_schemas = cx._SYSTEM_PROMPT, cx._tool_schemas()
    def mutate(root, prior, run):
        document = commit(root, prior, run)
        if run["phase"] == "claimed":
            monkeypatch.setattr(cx, "_SYSTEM_PROMPT", "Late mutation must not be dispatched.")
        return document
    monkeypatch.setattr(cx, "_fabric_commit", mutate)
    fixed.call(state)
    run = fixed.record(state)
    assert run["phase"] == "complete"
    assert run["request_payload"] == {"system": original_system, "tools": original_schemas}
    sent = json.loads(state.native.posts[0][1])
    assert sent["messages"][0]["content"] == original_system
    assert "Late mutation" not in json.dumps(sent)


@pytest.mark.parametrize("change", ["payload", "route_reset", "route_replace", "prior_response"])
def test_same_operation_cannot_rewrite_committed_payload_route_or_step(cortex_auto, change):
    state = cortex_auto
    fixed.call(state)
    original = cx._fabric_read_state(state.root)
    assert original["fabric"]["phase"] == "complete"
    run = copy.deepcopy(original["fabric"])
    if change == "payload":
        run["request_payload"]["system"] += " changed"
        run["request"]["system_sha256"] = cx._fabric_digest(run["request_payload"]["system"])
    elif change == "route_reset":
        run["route_identity"] = None
    elif change == "route_replace":
        run["route_identity"]["selection_digest"] = "a" * 64
    else:
        run["steps"][0]["response"]["model"] = "changed-model"
    before = state.path.read_bytes()
    with pytest.raises(cx._CortexFabricHold, match="original_identity_changed"):
        cx._fabric_commit(state.root, original, run)
    assert state.path.read_bytes() == before
    assert len(state.native.posts) == 3


def test_cleanup_receipt_error_preserves_original_base_exception_and_durable_intent(cortex_auto, monkeypatch):
    state = cortex_auto
    marker = KeyboardInterrupt("synthetic original interruption")
    monkeypatch.setattr(_CLIENT, "create", Mock(side_effect=marker))
    monkeypatch.setattr(cx, "_fabric_receipt", Mock(side_effect=ValueError("synthetic receipt failure")))
    with pytest.raises(KeyboardInterrupt) as observed:
        cx.run(root=state.root, force=True)
    assert observed.value is marker
    run = fixed.record(state)
    assert run["phase"] == "inference_pending" and run["steps"][0]["phase"] == "intent"
    assert not state.native.posts and len(state.closes) == 1


def test_later_native_warm_state_preserves_completed_auto_receipt(cortex_auto):
    fixed.test_completed_fabric_evidence_survives_a_later_native_warm_tuple(cortex_auto)


def test_native_step_limit_remains_an_original_hold_not_a_new_operation(cortex_auto, monkeypatch):
    state = cortex_auto
    for grant in state.native.document["application_grants"]:
        if grant["principal_id"] == "macro_analysis_fabric":
            grant["max_steps"] = 2
    state.native.save()
    fixed.call(state)
    run = fixed.record(state)
    assert run["phase"] == "held" and len(run["steps"]) == 3
    assert run["steps"][-1]["phase"] == "intent"
    assert run["steps"][-1]["application_observation"] is None
    assert len(state.native.posts) == 2
    assert len(fixed.rows(state.cost_path)) == 2
    fixed.held_no_replay(state, monkeypatch)
