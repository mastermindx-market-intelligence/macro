"""Public Cortex -> real shared owner/client -> pinned 8af HTTP/A/SQLite.

Provider responses, credentials and qualifications are synthetic. Cortex state,
tools, memo publication, native admission/close and both usage writers are real.
"""
import copy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import Mock, patch

import pytest
import pandas.core.arrays.arrow.extension_types  # noqa: F401

from engine.neuralweb import cortex as cx
# Load before NativeApplicationHTTPFixture snapshots sys.modules. Its cleanup
# restores that snapshot; a late import can leave a stale package attribute.
from engine.neuralweb import metabolism
from engine import fabric_inference_client as transport, llm_auth as auth
from engine import provider_production_modes as owner, provider_health
from lib import ai_costs
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="exact paired Mastermind8af source required")
_CLIENT = transport.FabricInferenceClient
_USAGE_WRITER = ai_costs.record_usage
_HEALTH_WRITER = provider_health.record_attempt


def tool(name, arguments=None, identifier="tool-1"):
    return {"id": identifier, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments or {})}}


def packet(*tools, text="Deliberation complete.", finish=None, model=MODEL, usage=True):
    value = {"model": model, "choices": [{"index": 0,
        "finish_reason": finish or ("tool_calls" if tools else "stop"),
        "message": {"role": "assistant", "content": None if tools else text}}]}
    if tools:
        value["choices"][0]["message"]["tool_calls"] = list(tools)
    if usage:
        value["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
    return value


@pytest.fixture
def cortex(selected, tmp_path_factory, monkeypatch):
    state = selected
    state.native.grant["workloads"] = ["lobe_analysis"]
    state.native.grant["max_steps"] = 8
    state.native.save()
    state.service = replace(state.native.service, workload="lobe_analysis")
    state.server = state.native.go.make_server(state.native.router,
        lease_gateway=state.native.gateway, application_services=(state.service,))
    state.native._serve(state.server)
    state.transport = replace(state.transport,
        base_url=f"http://127.0.0.1:{state.server.server_port}/v1")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", state.transport)
    state.row.update({key: getattr(state.transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    state.manifest["capabilities"][0]["allowed_lanes"] = ["cortex"]
    state.save()
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "lobe_analysis")
    monkeypatch.setattr(auth, "_repo_root", lambda: state.root / "wrong-module-root")
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setattr(provider_health, "record_attempt", _HEALTH_WRITER)
    telemetry = tmp_path_factory.mktemp("cortex-telemetry")
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
    state.closes = []
    close = _CLIENT.close
    def recorded_close(client):
        state.closes.append(client.operation_id)
        return close(client)
    monkeypatch.setattr(_CLIENT, "close", recorded_close)
    state.responses = [packet(tool("read_world_state", identifier="read-1")),
        packet(tool("write_memo", {"summary": "The original context remains uncertain."}, "memo-1")),
        packet()]
    def respond():
        index = len(state.native.posts) - 1
        state.native.response = state.responses[min(index, len(state.responses) - 1)]
    state.native.on_upstream = respond
    return state


def call(state, force=False):
    assert cx.run(root=state.root, force=force) == 0


def record(state):
    return cx._fabric_read_state(state.root)["fabric"]


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def no_native(state):
    state.native_builder.assert_not_called()
    state.native_fallback.assert_not_called()


def held_no_replay(state, monkeypatch):
    before = (len(state.native.posts), list(state.closes), rows(state.cost_path), rows(state.health_path))
    assert record(state)["phase"] == "held" or record(state)["phase"] not in {"complete"}
    state.cfg.clear()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    (state.root / "data/neuralweb/world_state.json").write_text('{"inputs_hash":"changed"}')
    call(state, force=True)
    assert (len(state.native.posts), state.closes, rows(state.cost_path), rows(state.health_path)) == before
    no_native(state)


def test_public_loop_retains_full_history_one_real_turn_usage_and_closed_memo(cortex):
    state = cortex
    call(state)
    run = record(state)
    assert run["phase"] == "complete" and run["business_complete"]
    assert [s["request_id"] for s in run["steps"]] == [run["operation_id"] + f":brain:{n}" for n in range(3)]
    assert [s["phase"] for s in run["steps"]] == ["response"] * 3
    assert run["census"] == {"read_world_state": 1, "write_memo": 1}
    assert len(state.native.rows("application_turns")) == len(state.native.rows("leases")) == len(state.closes) == 1
    assert state.native.rows("application_turns")[0]["workload"] == "lobe_analysis"
    assert state.native.rows("leases")[0]["state"] == "released"
    assert len(state.native.posts) == 3
    sent = [json.loads(item[1]) for item in state.native.posts]
    assert [m["role"] for m in sent[1]["messages"]] == ["system", "user", "assistant", "tool"]
    assert sent[1]["messages"][2]["tool_calls"][0]["id"] == "read-1"
    assert sent[1]["messages"][3]["tool_call_id"] == "read-1"
    assert json.loads(sent[1]["messages"][3]["content"])["inputs_hash"] == "input-original"
    assert sent[2]["messages"][:4] == sent[1]["messages"]
    cost = rows(state.cost_path)
    assert len(cost) == 3 and {r["model"] for r in cost} == {MODEL}
    assert {r["cycle_id"] for r in cost} == {run["operation_id"]}
    assert {r["lane"] for r in cost} == {"cortex"}
    assert sum(r["input_tokens"] for r in cost) == 33
    assert len(rows(state.health_path)) == 3
    assert all(r["lane"] == "cortex" for r in rows(state.health_path))
    memo = state.root / "data/neuralweb/cortex/memo.json"
    assert memo.read_bytes() == (state.root / "site/neuralweb/cortex_memo.json").read_bytes()
    document = json.loads(memo.read_text())
    assert document["is_context_only"] is True
    assert document["run_status"]["model_used"] == MODEL
    assert document["run_status"]["close"]["closed"] is True
    assert document["run_status"]["context_stale"]
    assert document["deserves_operator"][0].startswith("[context_stale]")
    events = list(state.events)
    call(state, force=True)
    assert len(state.native.posts) == 3 and state.events == events and rows(state.cost_path) == cost
    no_native(state)


@pytest.mark.parametrize("invalid", ["unknown", "duplicate", "missing", "wrong-type", "nested-type",
    "enum", "extra", "provenance", "bounds"])
def test_invalid_whole_batch_does_not_execute_the_preceding_valid_write(cortex, monkeypatch, invalid):
    bad = tool("read_world_state", identifier="bad-1")
    if invalid == "unknown": bad = tool("originate_trade", identifier="bad-1")
    elif invalid == "duplicate": bad["id"] = "memo-1"
    elif invalid == "missing": bad = tool("write_memo", {}, "bad-1")
    elif invalid == "wrong-type": bad = tool("read_company_intelligence", {"ticker": 17}, "bad-1")
    elif invalid == "nested-type": bad = tool("flag_attention", {"items": [{"scope_key": "A", "falsifier": 5}]}, "bad-1")
    elif invalid == "enum": bad = tool("flag_attention", {"items": [{"scope_key": "A", "falsifier": "f", "direction": 2}]}, "bad-1")
    elif invalid == "extra": bad = tool("read_world_state", {"root": "/outside"}, "bad-1")
    elif invalid == "provenance": bad = tool("write_memo", {"summary": "s", "run_status": {"status": "ok"}}, "bad-1")
    elif invalid == "bounds": bad = tool("read_company_intelligence", {"ticker": "A", "limit": 13}, "bad-1")
    cortex.responses = [packet(tool("write_memo", {"summary": "must not write"}, "memo-1"), bad)]
    dispatch = Mock(wraps=cx.dispatch_tool)
    monkeypatch.setattr(cx, "dispatch_tool", dispatch)
    call(cortex)
    dispatch.assert_not_called()
    assert not (cortex.path.parent / "memo.json").exists()
    assert len(cortex.native.posts) == 1
    held_no_replay(cortex, monkeypatch)


def test_tool_id_cannot_be_reused_in_later_intent(cortex, monkeypatch):
    cortex.responses = [packet(tool("read_world_state", identifier="same")),
                        packet(tool("write_memo", {"summary": "s"}, "same"))]
    call(cortex)
    assert len(record(cortex)["tools"]) == 1
    assert len(rows(cortex.cost_path)) == 2
    assert not (cortex.path.parent / "memo.json").exists()
    held_no_replay(cortex, monkeypatch)


@pytest.mark.parametrize("failure", ["429", "503", "model", "empty", "truncated", "json", "timeout", "typeerror", "disconnect"])
def test_selected_failure_retains_original_and_never_retries(cortex, monkeypatch, failure):
    if failure in ("429", "503"): cortex.native.response_status = int(failure)
    elif failure == "model": cortex.responses = [packet(model="observed-other")]
    elif failure == "empty": cortex.responses = [packet(text="")]
    elif failure == "truncated": cortex.responses = [packet(finish="length")]
    elif failure == "json": cortex.responses = [b'{"model":']
    elif failure == "disconnect": cortex.native.reset = True
    else:
        exc = TimeoutError if failure == "timeout" else TypeError
        def fail(*args, **kwargs): raise exc("synthetic failure")
        monkeypatch.setattr(_CLIENT, "create", fail)
    call(cortex)
    assert len(cortex.native.posts) <= 1 and len(cortex.closes) == 1
    assert len(record(cortex)["steps"]) == 1
    if failure in ("429", "503", "model", "empty", "truncated"):
        assert len(rows(cortex.cost_path)) == 1
    held_no_replay(cortex, monkeypatch)


def test_missing_usage_is_nullable_evidence_and_cannot_be_logged_as_zero(cortex):
    cortex.responses = [packet(tool("write_memo", {"summary": "Useful context"}, "memo-1"), usage=False),
                        packet(usage=False)]
    call(cortex)
    run = record(cortex)
    assert run["receipt"]["usage"]["usage_state"] == "unknown"
    assert run["receipt"]["usage"]["input_tokens"] is None
    assert rows(cortex.cost_path) == []
    assert run["phase"] == "complete" and run["receipt"]["close"]["closed"]
    before = len(cortex.native.posts)
    call(cortex, force=True)
    assert len(cortex.native.posts) == before


def test_unknown_close_retains_paid_memo_without_healthy_projection(cortex, monkeypatch):
    def close(client):
        cortex.closes.append(client.operation_id)
        return {"disposition": "effect_unknown", "closed": False, "effect_unknown": True, "attempted": True}
    monkeypatch.setattr(_CLIENT, "close", close)
    call(cortex)
    run = record(cortex)
    assert run["memo"] is not None and run["projection"]["phase"] == "unsent"
    assert run["receipt"]["usage"]["completed_input_tokens"] == 33
    assert json.loads((cortex.path.parent / "memo.json").read_text())["run_status"]["degraded"]
    assert len(rows(cortex.cost_path)) == 3
    held_no_replay(cortex, monkeypatch)


@pytest.mark.parametrize("stage", ["before-intent", "after-response", "after-tool", "final-projection", "final-state"])
def test_persistence_acknowledgement_loss_never_replays_effects(cortex, monkeypatch, stage):
    commit = cx._fabric_commit
    injected = []
    def fail(root, prior, run):
        match = ((stage == "before-intent" and run["phase"] == "claimed")
            or (stage == "after-response" and run["phase"] == "response" and not run["tools"])
            or (stage == "after-tool" and run["tools"] and run["tools"][-1]["phase"] == "complete")
            or (stage == "final-projection" and run["projection"]["phase"] == "intent")
            or (stage == "final-state" and run["phase"] == "complete"))
        value = commit(root, prior, run)
        if match and not injected:
            injected.append(stage)
            raise OSError("synthetic lost publication acknowledgment")
        return value
    monkeypatch.setattr(cx, "_fabric_commit", fail)
    call(cortex)
    assert injected
    count = len(cortex.native.posts)
    costs = rows(cortex.cost_path)
    memo = (cortex.path.parent / "memo.json").read_bytes() if (cortex.path.parent / "memo.json").exists() else None
    monkeypatch.setattr(cx, "_fabric_commit", commit)
    call(cortex, force=True)
    assert len(cortex.native.posts) == count and rows(cortex.cost_path) == costs
    assert ((cortex.path.parent / "memo.json").read_bytes() if (cortex.path.parent / "memo.json").exists() else None) == memo
    if stage == "before-intent": assert count == 0 and not cortex.events


@pytest.mark.parametrize("boundary", ["replace", "parent-sync", "readback"])
def test_claim_publication_boundaries_precede_bind(cortex, monkeypatch, boundary):
    if boundary == "replace":
        original = cx.os.replace
        def fail(src, dst):
            if str(dst) == str(cortex.path): raise OSError("synthetic replace failure")
            return original(src, dst)
        monkeypatch.setattr(cx.os, "replace", fail)
    elif boundary == "parent-sync":
        original = cx._fabric_sync_dir
        def fail(path):
            if cortex.path.exists(): raise OSError("synthetic parent fsync failure")
            return original(path)
        monkeypatch.setattr(cx, "_fabric_sync_dir", fail)
    else:
        original = cx._fabric_read_state
        def fail(root):
            if cortex.path.exists(): raise OSError("synthetic readback failure")
            return original(root)
        monkeypatch.setattr(cx, "_fabric_read_state", fail)
    call(cortex)
    assert not cortex.events and not cortex.native.posts


@pytest.mark.parametrize("corruption", ["truncated", "duplicate", "nonfinite", "version", "checksum", "symlink", "ancestor", "fifo"])
def test_invalid_state_cannot_fall_into_native_or_a_fresh_selected_call(cortex, monkeypatch, corruption):
    if corruption == "ancestor":
        cortex.path.parent.rmdir()
        other = cortex.root / "other-state"
        other.mkdir()
        cortex.path.parent.symlink_to(other, target_is_directory=True)
    elif corruption == "symlink":
        other = cortex.root / "other.json"; other.write_text("{}")
        cortex.path.symlink_to(other)
    elif corruption == "fifo": os.mkfifo(cortex.path)
    else:
        data = {"truncated": '{"schema":', "duplicate": '{"a":1,"a":2}', "nonfinite": '{"a":NaN}',
                "version": '{"schema":"unknown"}', "checksum": '{"schema":"neuralweb.cortex_run.v2"}'}[corruption]
        cortex.path.write_text(data)
    cortex.cfg.clear(); monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    call(cortex, force=True)
    assert not cortex.native.posts and not cortex.events
    no_native(cortex)


@pytest.mark.parametrize("selector", [None, "", False, "other_lane"])
def test_explicit_caller_profile_cannot_be_replaced_by_startup_default(cortex, selector):
    cortex.cfg["workload_profile"] = selector
    call(cortex)
    assert not cortex.events and not cortex.native.posts and not cortex.path.exists()
    no_native(cortex)


@pytest.mark.parametrize("change", ["mode", "host", "disabled", "capability", "required-model", "binding-drift", "native-workload"])
def test_real_owner_intersection_and_binding_commitment(cortex, monkeypatch, change):
    if change == "mode": monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    elif change == "host": monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "development_agent")
    elif change == "disabled": cortex.row["enabled"] = False; cortex.save()
    elif change == "capability": cortex.manifest["capabilities"][0]["allowed_lanes"] = ["brain"]; cortex.save()
    elif change == "required-model": cortex.cfg["llm_model"] = "explicit-other-model"
    elif change == "native-workload": cortex.native.grant["workloads"] = ["site_interactive"]; cortex.native.save()
    else:
        original = cx._fabric_commit
        def drift(root, prior, run):
            value = original(root, prior, run)
            if run["phase"] == "claimed":
                cortex.row["enabled"] = False; cortex.save()
            return value
        monkeypatch.setattr(cx, "_fabric_commit", drift)
    call(cortex)
    assert not cortex.native.posts
    if change != "native-workload": assert not cortex.events
    no_native(cortex)


@pytest.mark.parametrize("profile", ["site_interactive", "site_batch", "portfolio_analysis"])
def test_host_profile_intersection_uses_real_allowed_providers(cortex, monkeypatch, profile):
    # Different profile labels may still admit the same inference provider.
    # The incumbent policy intersects allowed providers; Cortex must not add
    # a competing profile-equality rule.
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", profile)
    cortex.responses = [packet()]
    call(cortex)
    assert record(cortex)["phase"] == "complete"
    assert cortex.native.rows("application_turns")[0]["workload"] == "lobe_analysis"
    assert len(cortex.native.posts) == 1


def test_stake_registration_unknown_does_not_append_or_retry(cortex, monkeypatch):
    effects = []
    def register(hypothesis, **kwargs):
        effects.append(hypothesis)
        raise OSError("synthetic owner wrote then lost acknowledgment")
    monkeypatch.setattr(metabolism, "register_hypothesis", register)
    cortex.responses = [packet(tool("stake_hypothesis", {"claim": "Context hypothesis", "horizon_d": 5,
        "pre_committed_gate": {"metric": "ic", "threshold": 0.2, "min_n": 25, "horizon_d": 5}}, "hyp-1"))]
    call(cortex)
    assert len(effects) == 1 and record(cortex)["tools"][0]["phase"] == "intent"
    assert not (cortex.path.parent / "hypothesis_inbox.jsonl").exists()
    held_no_replay(cortex, monkeypatch)
    assert len(effects) == 1


def test_lost_tool_acknowledgment_does_not_repeat_real_attention_write(cortex, monkeypatch):
    cortex.responses = [packet(tool("flag_attention", {"items": [{"scope_key": "fixture", "falsifier": "A contrary observation."}]}, "attention-1"))]
    original = cx.dispatch_tool
    def dispatch(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt("synthetic process interruption after tool write")
    monkeypatch.setattr(cx, "dispatch_tool", dispatch)
    with pytest.raises(KeyboardInterrupt): call(cortex)
    attention = cortex.root / "data/reflexes/cortex_attention/firings.jsonl"
    before = attention.read_bytes()
    assert len(before.splitlines()) == 1
    monkeypatch.setattr(cx, "dispatch_tool", original)
    held_no_replay(cortex, monkeypatch)
    assert attention.read_bytes() == before


def test_memo_mirror_failure_retains_partial_write_and_original_tool(cortex, monkeypatch):
    cortex.responses = [packet(tool("write_memo", {"summary": "Paid original memo"}, "memo-1"))]
    original = Path.write_text
    def write(path, *args, **kwargs):
        if path == cortex.root / "site/neuralweb/cortex_memo.json": raise OSError("synthetic mirror failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", write)
    call(cortex)
    assert (cortex.path.parent / "memo.json").is_file()
    assert record(cortex)["tools"][0]["phase"] == "intent"
    held_no_replay(cortex, monkeypatch)


def test_original_captured_input_not_late_input_controls_next_run(cortex):
    original = cortex.native.on_upstream
    def update():
        original()
        (cortex.root / "data/neuralweb/world_state.json").write_text('{"inputs_hash":"late-input"}')
    cortex.native.on_upstream = update
    call(cortex)
    first = record(cortex)
    assert first["phase"] == "complete" and first["source"]["ws_inputs_hash"] == "input-original"
    cortex.responses = [packet()]
    call(cortex)
    assert record(cortex)["operation_id"] != first["operation_id"]
    assert record(cortex)["source"]["ws_inputs_hash"] == "late-input"


def test_stale_native_save_cannot_erase_selected_claim(cortex, monkeypatch):
    monkeypatch.setattr(_CLIENT, "close", lambda self: {
        "disposition": "effect_unknown", "closed": False, "effect_unknown": True, "attempted": True})
    cortex.native.on_upstream = lambda: setattr(cortex.native, "response", packet())
    call(cortex)
    before = cortex.path.read_bytes()
    cx._save_last_run_state(cortex.root, {"ws_inputs_hash": "stale-native", "spine_rows": 0, "contradictions_hash": ""})
    assert cortex.path.read_bytes() == before


def test_completed_fabric_evidence_survives_a_later_native_warm_tuple(cortex):
    call(cortex)
    before = record(cortex)
    assert cx._load_last_run_state(cortex.root) == {}
    native = {"ws_inputs_hash": "later-native", "spine_rows": 3, "contradictions_hash": "fresh"}
    cx._save_last_run_state(cortex.root, native)
    assert cx._load_last_run_state(cortex.root) == native
    assert record(cortex) == before
    assert not cx._state_changed(native, cx._load_last_run_state(cortex.root))


@pytest.mark.parametrize("failure", ["owner-error", "missing-append"])
def test_attention_requires_the_existing_owners_positive_append(cortex, monkeypatch, failure):
    from engine.neuralweb import reflexes
    returned = {"claim_id": "unacknowledged"}
    if failure == "owner-error": returned["_write_error"] = "synthetic write error"
    writer = Mock(return_value=returned)
    monkeypatch.setattr(reflexes, "record_firing", writer)
    cortex.responses = [packet(tool("flag_attention", {"items": [{"scope_key": "fixture", "falsifier": "Contrary evidence"}]}, "attention-1"))]
    call(cortex)
    assert writer.call_count == 1 and record(cortex)["tools"][0]["phase"] == "intent"
    assert record(cortex)["census"] == {}
    held_no_replay(cortex, monkeypatch)
    assert writer.call_count == 1


def hypothesis():
    return {"subject": "XLK", "claim": "XLK outperforms SPY when MACD crosses signal on 5d",
        "claim_shape": "lead_lag", "spine_query": {"subject": "XLK", "lead_series": "MACD"},
        "falsifier": "XLK excess return > 0 over 21 days in 55%+ of events", "horizon_d": 21,
        "pre_committed_gate": {"metric": "hit_rate", "threshold": 0.55, "min_n": 5, "horizon_d": 21}}


def test_stake_uses_actual_registry_trial_governance_and_inbox_receipts(cortex):
    cortex.responses = [packet(tool("stake_hypothesis", hypothesis(), "hyp-1")), packet()]
    call(cortex)
    run = record(cortex)
    assert run["phase"] == "complete" and run["tools"][0]["result"]["status"] == "registered"
    registered = rows(cortex.root / "data/neuralweb/machine_registry.jsonl")
    trial = rows(cortex.root / "data/trial_ledger.jsonl")
    governance = rows(cortex.root / "data/neuralweb/governance.jsonl")
    inbox = rows(cortex.path.parent / "hypothesis_inbox.jsonl")
    assert len(registered) == len(trial) == len(governance) == len(inbox) == 1
    assert registered[0]["pre_committed_gate"]["min_n"] == 25
    assert governance[0]["evidence"]["pre_committed_gate"]["min_n"] == 25
    assert inbox[0]["id"] == registered[0]["id"] == run["tools"][0]["result"]["id"]
    assert run["census"] == {"stake_hypothesis": 1}


@pytest.mark.parametrize("failure", ["registry", "trial", "governance", "inbox"])
def test_stake_partial_business_writes_retain_original_intent(cortex, monkeypatch, failure):
    assert sys.modules["engine.neuralweb.metabolism"] is metabolism
    assert metabolism.register_hypothesis.__globals__ is vars(metabolism)
    if failure in {"registry", "trial", "governance"}:
        helper = {"registry": "_append_registry", "trial": "_log_to_trial_ledger",
                  "governance": "_emit_governance"}[failure]
        fault = Mock(return_value=False if failure == "registry" else None)
        monkeypatch.setattr(metabolism, helper, fault)
    else:
        original = Path.open
        fault = Mock(side_effect=OSError("synthetic inbox write failure"))
        def fail(path, *args, **kwargs):
            if path == cortex.path.parent / "hypothesis_inbox.jsonl" and args and args[0] == "a":
                return fault()
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", fail)
    cortex.responses = [packet(tool("stake_hypothesis", hypothesis(), "hyp-1"))]
    call(cortex)
    fault.assert_called_once()
    assert len(cortex.native.posts) == 1 and record(cortex)["tools"][0]["phase"] == "intent"
    paths = cx._fabric_effect_paths(cortex.root, "stake_hypothesis")
    before = [p.read_bytes() if p.exists() else None for p in paths]
    held_no_replay(cortex, monkeypatch)
    assert [p.read_bytes() if p.exists() else None for p in paths] == before
    fault.assert_called_once()


def test_invalid_hypothesis_is_audited_as_business_refusal(cortex):
    value = hypothesis(); value["claim"] = ""
    cortex.responses = [packet(tool("stake_hypothesis", value, "hyp-1")), packet()]
    call(cortex)
    run = record(cortex)
    assert run["phase"] == "complete" and run["tools"][0]["result"]["status"] == "invalid"
    assert len(rows(cortex.root / "data/neuralweb/machine_registry.jsonl")) == 1
    assert len(rows(cortex.path.parent / "hypothesis_inbox.jsonl")) == 1
    assert not rows(cortex.root / "data/trial_ledger.jsonl")


def test_hardlinked_output_refuses_before_the_real_tool_writer(cortex, monkeypatch):
    target = cortex.root / "data/reflexes/cortex_attention/firings.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text('{"existing":"evidence"}\n')
    os.link(target, cortex.root / "other-ledger.jsonl")
    from engine.neuralweb import reflexes
    writer = Mock(side_effect=AssertionError("must not write a hardlinked ledger"))
    monkeypatch.setattr(reflexes, "record_firing", writer)
    cortex.responses = [packet(tool("flag_attention", {"items": [{"scope_key": "fixture", "falsifier": "Contrary evidence"}]}, "attention-1"))]
    call(cortex)
    writer.assert_not_called()
    held_no_replay(cortex, monkeypatch)


def test_budget_exhausted_without_model_memo_is_a_closed_degraded_result(cortex):
    cortex.cfg["max_tool_calls"] = 1
    call(cortex)
    run = record(cortex)
    assert run["phase"] == "complete" and len(cortex.native.posts) == 1
    status = run["memo"]["document"]["run_status"]
    assert status["degraded"] and status["degradation_reason"] == "memo_not_submitted"
    assert status["close"]["closed"] and status["usage"]["usage_state"] == "known"
    call(cortex, force=True)
    assert len(cortex.native.posts) == 1


def test_oversized_token_limit_refuses_before_claim_and_credentials(cortex):
    cortex.cfg["max_tokens"] = 32769
    call(cortex)
    assert not cortex.path.exists() and not cortex.events and not cortex.native.posts


@pytest.mark.parametrize("corruption", ["memo", "projection", "history", "usage", "observation", "root"])
def test_checksum_valid_but_impossible_completion_never_rebinds(cortex, monkeypatch, corruption):
    call(cortex)
    value = json.loads(cortex.path.read_text())
    run = value["fabric"]
    if corruption == "memo": run["memo"] = None
    elif corruption == "projection": run["projection"]["result"] = {}
    elif corruption == "history": run["messages"].append({"role": "user", "content": "invented history"})
    elif corruption == "usage": run["receipt"]["usage"]["completed_input_tokens"] += 1
    elif corruption == "observation":
        run["steps"][0]["observation"] = None
        run["receipt"]["observations"].pop(0)
        for key in ("input_tokens", "completed_input_tokens"): run["receipt"]["usage"][key] -= 11
        for key in ("output_tokens", "completed_output_tokens"): run["receipt"]["usage"][key] -= 7
    else: run["root"] = str(cortex.root / "different-root")
    value["sha256"] = cx._fabric_digest({k: v for k, v in value.items() if k != "sha256"})
    cortex.path.write_bytes(cx._fabric_json_bytes(value))
    before = (cortex.path.read_bytes(), list(cortex.events), len(cortex.native.posts), rows(cortex.cost_path))
    cortex.cfg.clear(); monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    call(cortex, force=True)
    assert (cortex.path.read_bytes(), cortex.events, len(cortex.native.posts), rows(cortex.cost_path)) == before
    no_native(cortex)


def test_later_failed_step_does_not_inherit_the_previous_usage_observation(cortex, monkeypatch):
    original = _CLIENT.create
    calls = []
    def fail(client, *args, **kwargs):
        calls.append(client.operation_id)
        if len(calls) == 2: raise TimeoutError("synthetic later request uncertainty")
        return original(client, *args, **kwargs)
    monkeypatch.setattr(_CLIENT, "create", fail)
    call(cortex)
    run = record(cortex)
    assert len(run["steps"]) == 2 and run["steps"][1]["observation"] is None
    assert run["steps"][0]["observation"]["input_tokens"] == 11
    assert run["receipt"]["usage"]["completed_input_tokens"] == 11
    assert len(rows(cortex.cost_path)) == 1
    held_no_replay(cortex, monkeypatch)


def test_two_real_processes_share_one_claim_and_network_operation(cortex):
    specification = cortex.root / "test-transport.json"
    specification.write_text(json.dumps(asdict(cortex.transport)))
    script = """import json,sys\nfrom pathlib import Path\nfrom engine import provider_production_modes as owner\nfrom engine.neuralweb import cortex\nroot=Path(sys.argv[1])\nowner._APPLICATION_FABRIC_TRANSPORTS['fixture_v1']=owner._ApplicationFabricTransport(**json.loads((root/'test-transport.json').read_text()))\nraise SystemExit(cortex.run(root=root,force=True))\n"""
    arrived = threading.Event(); release = threading.Event()
    def response():
        cortex.native.response = packet()
        arrived.set()
        assert release.wait(20)
    cortex.native.on_upstream = response
    command = [sys.executable, "-c", script, str(cortex.root)]
    first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = None
    try:
        assert arrived.wait(20)
        second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = second.communicate(timeout=20)
        assert second.returncode == 0, output
        assert len(cortex.native.posts) == 1
        release.set()
        output = first.communicate(timeout=20)
        assert first.returncode == 0, output
    finally:
        release.set()
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill(); process.communicate()
    assert len(cortex.native.posts) == len(cortex.native.rows("leases")) == 1
    assert record(cortex)["phase"] == "complete"
    assert len(rows(cortex.cost_path)) == 1
