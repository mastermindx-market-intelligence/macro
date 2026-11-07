"""UK public entries -> durable processed state -> real shared/native owners.

Qualification, credentials and upstream answers are isolated synthetic fixtures.
No real government fetch, paid inference, service or production state is used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine import provider_production_modes as owner, uk_policy_brain as brain
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
CLIENT = transport.FabricInferenceClient
ANSWER = {"summary_en": "The Treasury published a policy update.",
          "summary_zh": "财政部发布政策更新。", "stance": "routine",
          "watch_en": "Watch the next Treasury update.", "watch_zh": "关注下次更新。"}


@pytest.fixture
def desk(selected, monkeypatch, tmp_path):
    state = selected
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    state.cfg = {**brain._DEFAULTS, "enabled": True}
    state.content_root = tmp_path / "desk"
    state.content_root.mkdir()
    state.item = {"id": "uk-original-announcement", "title": "Treasury policy update",
        "body_text": "The Treasury published a policy update. Watch the next Treasury update.",
        "url": "https://www.gov.uk/government/news/fixture", "doc_version": "v1",
        "doc_type": "News Story", "published": datetime.now(timezone.utc).isoformat()}
    monkeypatch.setattr(brain, "_cfg", lambda: dict(state.cfg))
    monkeypatch.setattr(brain, "_provider", Mock(side_effect=AssertionError("legacy discovery")))
    monkeypatch.setattr(brain, "collect", lambda *_a, **_kw: [dict(state.item)])
    monkeypatch.setattr(brain, "fetch_body", Mock(side_effect=AssertionError("unexpected GOV.UK fetch")))
    monkeypatch.setattr(brain, "fetch_version", Mock(side_effect=AssertionError("unexpected version fetch")))
    state.native.response = {"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(ANSWER)}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    state.operations, state.closes = [], []
    original_begin, original_close = auth.begin_operation, CLIENT.close

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(CLIENT, "close", close)
    state.run = lambda **kw: brain.run(root=state.content_root, **kw)
    state.evaluate = lambda **kw: brain.evaluate(state.item, state.cfg,
        state.content_root, **kw)
    state.processed = lambda: brain._read_processed_strict(state.content_root)
    state.entry = lambda: state.processed()["fabric_operations"][state.item["id"]]
    return state


def closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def test_public_success_claims_before_binding_and_preserves_actual_model_and_usage(desk, monkeypatch):
    state = desk
    original_bind = auth.build_fabric_provider

    def bind(*args, **kw):
        entry = state.entry()
        assert entry["state"] == "pending" and entry["receipt"] is None
        assert entry["operation_id"] == kw["request_id"]
        assert entry["source_identity"]["id"] == state.item["id"]
        return original_bind(*args, **kw)

    monkeypatch.setattr(auth, "build_fabric_provider", bind)
    assert brain.enabled() and brain.provider_label(state.cfg) == "assistant"
    assert state.events == state.native.posts == []
    first = state.run(call=Mock(side_effect=AssertionError("selected injected bypass")))
    assert first["state"] == "ok" and first["stance"] == "routine"
    assert first["summary_en"] == ANSWER["summary_en"] and first["serving_model"] == MODEL
    entry = state.entry()
    assert entry["state"] == "terminal" and entry["outcome"] == "usable"
    assert entry["receipt"]["usage"]["input_tokens"] == 11
    assert entry["receipt"]["close"]["closed"]
    assert state.operations[0][1][0]["client"]._client._timeout == 15.0
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == 600
    assert request["stream"] is False and "tools" not in request
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == MODEL and state.costs[0]["stage"] == "uk_policy_brain"
    assert state.run(force=True)["summary_en"] == first["summary_en"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert brain.latest(state.content_root)["fabric_operation"]["operation_id"] == entry["operation_id"]
    closed(state)


@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_selection_exclusive_before_native_credentials(desk, monkeypatch, mode):
    state = desk
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg[auth.APPLICATION_MODE_CFG_KEY] = mode
    assert not brain.enabled() and brain.provider_label(state.cfg) == ""
    result = state.run(force=True)
    assert result["model_unavailable"] and result["fabric_selected"]
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_invalid_explicit_workload_does_not_become_default(desk, profile):
    desk.cfg["workload_profile"] = profile
    assert desk.run(force=True)["model_unavailable"]
    assert desk.events == desk.native.posts == desk.operations == []


@pytest.mark.parametrize("entry", ["evaluate", "run"])
def test_selected_nonpersistent_public_entry_never_binds_or_sends(desk, entry):
    state = desk
    result = state.evaluate() if entry == "evaluate" else state.run(persist=False)
    assert result["fabric_reason"] == "fabric_durable_state_required"
    assert state.events == state.native.posts == state.operations == []
    assert not brain._state_path(state.content_root).exists()
    assert not brain._artifact_path(state.content_root).exists()


@pytest.mark.parametrize("fault", ["write", "fsync", "directory", "readback"])
def test_failed_claim_prevents_all_provider_effects(desk, monkeypatch, fault):
    state = desk
    if fault == "write":
        monkeypatch.setattr(brain, "_write_processed_strict", Mock(side_effect=OSError("write failed")))
    elif fault == "fsync":
        monkeypatch.setattr(brain.os, "fsync", Mock(side_effect=OSError("fsync failed")))
    elif fault == "directory":
        monkeypatch.setattr(brain, "_fsync_directory", Mock(side_effect=OSError("directory failed")))
    else:
        read = brain._read_processed_strict
        def readback(root):
            value = read(root)
            if value.get("fabric_operations"):
                raise OSError("readback failed")
            return value
        monkeypatch.setattr(brain, "_read_processed_strict", readback)
    assert state.evaluate(persist=True)["model_unavailable"]
    assert state.events == state.native.posts == state.operations == state.costs == []


def test_concurrent_same_item_has_one_claim_and_one_inference(desk):
    state = desk
    state.native.block = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(state.evaluate, persist=True)
            assert state.native.arrived.wait(2)
            other = state.evaluate(persist=True)
            assert other["fabric_operation"]["state"] == "pending"
            assert other["fabric_operation"]["operation_id"] == state.entry()["operation_id"]
            state.native.block.set()
            assert first.result(timeout=3)["stance"] == "routine"
    finally:
        state.native.block.set()
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


def test_failed_ancestor_sync_is_reestablished_before_later_binding(desk, monkeypatch):
    state = desk
    sync = brain._fsync_directory
    visits = []
    fail = True

    def observed(path):
        visits.append(Path(path))
        if fail and Path(path) == state.content_root:
            raise OSError("caller-root fsync not confirmed")
        return sync(path)

    monkeypatch.setattr(brain, "_fsync_directory", observed)
    for _ in range(2):
        assert state.evaluate(persist=True)["model_unavailable"]
        assert brain._state_path(state.content_root).parent.is_dir()
        assert state.events == state.native.posts == state.operations == []
    assert visits == [state.content_root, state.content_root]
    fail = False
    visits.clear()
    bind = auth.build_fabric_provider

    def verified_bind(*args, **kwargs):
        assert visits[:3] == [state.content_root, state.content_root / "data",
                              brain._state_path(state.content_root).parent]
        return bind(*args, **kwargs)

    monkeypatch.setattr(auth, "build_fabric_provider", verified_bind)
    assert state.evaluate(persist=True)["stance"] == "routine"
    assert len(state.native.posts) == 1


def test_selected_state_owner_requires_existing_caller_root(desk):
    state = desk
    absent = state.content_root / "missing-root"
    result = brain.evaluate(state.item, state.cfg, absent, persist=True)
    assert result["model_unavailable"] and not absent.exists()
    assert state.events == state.native.posts == state.operations == []


def test_unknown_survives_new_process_force_selector_removal_and_changed_item(desk, monkeypatch):
    state = desk
    monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("commit unknown")))
    first = state.run()
    entry = state.entry()
    assert entry["state"] == "held" and first["model_unavailable"]
    assert entry["receipt"]["usage"]["usage_state"] == "unknown"
    assert entry["receipt"]["usage"]["input_tokens"] is None
    assert entry["receipt"]["usage"]["completed_input_tokens"] == 11
    child = """import json,sys
from engine import uk_policy_brain as b
item,cfg,root=json.loads(sys.stdin.read())
print(json.dumps(b.evaluate(item,cfg,root,persist=True)))
"""
    environment = {**os.environ, auth.APPLICATION_MODE_ENV: "invalid mode"}
    process = subprocess.run([sys.executable, "-c", child],
        input=json.dumps([state.item, state.cfg, str(state.content_root)]), text=True,
        capture_output=True, env=environment, cwd=Path(brain.__file__).resolve().parent.parent, timeout=10)
    assert process.returncode == 0, process.stderr
    restarted = json.loads(process.stdout)
    assert restarted["fabric_operation"]["operation_id"] == entry["operation_id"]
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.item["title"] = "Changed headline for original ID"
    assert state.run(force=True)["fabric_reason"] == "fabric_original_input_conflict"
    state.cfg[auth.APPLICATION_MODE_CFG_KEY] = ""
    assert state.evaluate(persist=True)["fabric_operation"]["operation_id"] == entry["operation_id"]
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


@pytest.mark.parametrize("fault", ["empty", "blank", "tools", "truncated", "refusal", "http",
    "mismatch", "malformed", "list", "scalar", "wrong-stance", "invented-number"])
def test_terminal_failure_is_retained_without_native_retry_cap_or_regeneration(desk, fault):
    state = desk
    response = state.native.response
    choice = response["choices"][0]
    if fault == "empty": choice["message"]["content"] = ""
    elif fault == "blank": choice["message"]["content"] = "   "
    elif fault == "tools":
        choice["finish_reason"] = "tool_calls"
        choice["message"]["tool_calls"] = [{"id": "tool1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
    elif fault == "truncated": choice["finish_reason"] = "length"
    elif fault == "refusal": choice["finish_reason"] = "content_filter"
    elif fault == "http": state.native.response_status = 503
    elif fault == "mismatch": response["model"] = "unexpected-model"
    elif fault == "malformed": choice["message"]["content"] = "not JSON"
    elif fault == "list": choice["message"]["content"] = "[]"
    elif fault == "scalar": choice["message"]["content"] = "1"
    elif fault == "wrong-stance": choice["message"]["content"] = json.dumps({**ANSWER, "stance": []})
    else: choice["message"]["content"] = json.dumps({**ANSWER, "summary_en": "A new 999999 scheme."})
    for _ in range(brain.MODEL_ATTEMPT_CAP + 1):
        assert state.run(force=True)["model_unavailable"]
    assert state.entry()["state"] == "terminal"
    assert len(state.native.posts) == len(state.operations) == 1
    assert state.processed().get("attempts", {}) == {}
    closed(state)


@pytest.mark.parametrize("usage_known", [True, False])
def test_valid_answer_and_uncertain_close_preserve_separate_evidence(desk, monkeypatch, usage_known):
    state = desk
    if not usage_known:
        state.native.response["usage"]["completion_tokens"] = None
    monkeypatch.setattr(CLIENT, "close", Mock(side_effect=OSError("close lost")))
    first = state.run()
    assert first["stance"] == "routine" and first["summary_en"] == ANSWER["summary_en"]
    entry = state.entry()
    assert entry["state"] == "held" and entry["outcome"] == "usable"
    assert entry["receipt"]["effect_unknown"] and entry["receipt"]["close"]["effect_unknown"]
    assert entry["receipt"]["usage"]["input_tokens"] == (11 if usage_known else None)
    assert state.run(force=True)["summary_en"] == first["summary_en"]
    assert len(state.native.posts) == 1 and len(state.costs) == (1 if usage_known else 0)


def test_final_state_failure_keeps_original_pending_and_never_replays(desk, monkeypatch):
    state = desk
    write = brain._write_processed_strict
    def fail_settlement(root, value):
        if next(iter(value.get("fabric_operations", {}).values()))["state"] != "pending":
            raise OSError("settlement unavailable")
        return write(root, value)
    monkeypatch.setattr(brain, "_write_processed_strict", fail_settlement)
    first = state.run()
    assert first["stance"] == "routine" and first["fabric_operation"]["state"] == "held"
    assert first["fabric_operation"]["receipt"]["state_publication"] == "unconfirmed"
    assert state.entry()["state"] == "pending"
    assert state.run(force=True)["model_unavailable"]
    assert len(state.native.posts) == len(state.costs) == 1
    closed(state)


def test_crash_after_durable_claim_is_a_restart_barrier(desk, monkeypatch):
    state = desk
    monkeypatch.setattr(brain, "_selected_completion", Mock(side_effect=KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        state.evaluate(persist=True)
    original = state.entry()
    assert original["state"] == "pending"
    assert state.run(force=True)["fabric_operation"]["operation_id"] == original["operation_id"]
    assert state.events == state.native.posts == state.operations == []


def test_legacy_state_and_stale_native_save_preserve_selected_original(desk):
    state = desk
    legacy = {"seen": {"older": {"at": "2026-01-01"}}, "attempts": {"older": 2}, "custom": {"retained": True}}
    brain.save_processed(state.content_root, legacy)
    assert state.run()["state"] == "ok"
    original = state.entry()
    brain.save_processed(state.content_root, {**legacy, "seen": {"another": {"at": "later"}}})
    retained = state.processed()
    assert retained["fabric_operations"][state.item["id"]] == original
    assert set(retained["seen"]) == {"older", "another", state.item["id"]}
    assert retained["attempts"] == {"older": 2} and retained["custom"] == {"retained": True}


@pytest.mark.parametrize("bad", ['{"seen":', '{"seen":{},"fabric_operations":[]}',
    '{"seen":{},"seen":{}}', '{"seen":{},"fabric_operations":{"x":{}}}'])
def test_corrupt_state_fails_closed_without_reset_or_spend(desk, bad):
    state = desk
    path = brain._state_path(state.content_root)
    path.parent.mkdir(parents=True)
    path.write_text(bad)
    assert state.run(force=True)["model_unavailable"]
    assert path.read_text() == bad
    assert state.events == state.native.posts == state.operations == []


def test_display_write_failure_does_not_erase_original_answer(desk, monkeypatch):
    state = desk
    monkeypatch.setattr(brain, "_persist", lambda *_: None)
    first = state.run()
    assert first["summary_en"] == ANSWER["summary_en"] and brain.latest(state.content_root) is None
    second = state.run(force=True)
    assert second["summary_en"] == first["summary_en"]
    assert second["fabric_operation"]["operation_id"] == first["fabric_operation"]["operation_id"]
    assert len(state.native.posts) == len(state.costs) == 1


def test_identity_changed_after_inspection_stops_binding_and_retains_terminal_original(desk, monkeypatch):
    state = desk
    original = owner.ApplicationFabricFactory.with_inspection
    def change(factory, identity):
        narrowed = original(factory, identity)
        state.row["application_allowed"] = False
        state.save()
        return narrowed
    monkeypatch.setattr(owner.ApplicationFabricFactory, "with_inspection", change)
    result = state.evaluate(persist=True)
    assert result["model_unavailable"]
    assert state.events == state.native.posts == state.operations == []
    assert state.entry()["state"] == "terminal"


def test_private_native_helper_cannot_bypass_selected_durable_entry(desk):
    state = desk
    injected = Mock(side_effect=AssertionError("selected private bypass"))
    assert brain._call_model(state.item, state.item["body_text"], state.cfg, call=injected) == {}
    assert state.events == state.native.posts == state.operations == []
