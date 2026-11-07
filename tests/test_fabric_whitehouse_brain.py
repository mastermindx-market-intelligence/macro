"""White House/Treasury public paths through the real shared and pinned A/B owners."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import Mock, patch

import pytest

from engine import whitehouse_brain as wh, catalyst_tone as cache
from engine import fabric_inference_client as transport, provider_production_modes as owner, llm_auth as auth
from lib import ai_costs, config
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="exact paired native source required")
_USAGE_WRITER = ai_costs.record_usage
_CLIENT = transport.FabricInferenceClient
ITEM = {"guid": "government:original-1", "id": "wh-original-1", "title": "Auto tariff order",
        "url": "https://fixture.invalid/government/order", "section": "presidential-actions",
        "published": "2026-11-01T12:00:00Z", "body": "A 25% tariff on imported autos."}


def answer(**changes):
    return {"activate": True, "importance": 88, "banner_days": 12, "tone": "mixed",
            "banner_title": "Auto tariff", "banner_title_zh": "汽车关税", "summary": "Import costs rise.",
            "summary_zh": "进口成本上升。", "analysis": "A policy context assessment.", "confidence": "high",
            "sectors": [{"name": "Autos", "impact": "headwind", "rationale": "Import costs."}],
            "tickers": [{"symbol": "GM", "direction": "benefit", "rationale": "Domestic exposure."}], **changes}


def packet(value=None, *, finish="stop", model=MODEL, usage=True):
    value = answer() if value is None else value
    result = {"model": model, "choices": [{"index": 0, "finish_reason": finish,
        "message": {"role": "assistant", "content": value if isinstance(value, str) else json.dumps(value)}}]}
    if usage:
        result["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
    return result


@pytest.fixture
def whitehouse(selected, tmp_path_factory, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"].append("whitehouse")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "data_dir", lambda: state.root / "data")
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    state.cfg = {"enabled": True, "max_tokens": 128, "min_importance": 60, "max_banner_days": 7}
    state.native.response = packet()
    state.usage_root = tmp_path_factory.mktemp("whitehouse-usage")
    state.cost_path = state.usage_root / "data/ai_costs/usage.jsonl"
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(state.usage_root))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setattr(wh, "_provider", Mock(side_effect=AssertionError("legacy provider discovery")))
    monkeypatch.setattr(wh, "_client", Mock(side_effect=AssertionError("legacy client")))
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("legacy provider build")))
    state.closes = []
    original_close = _CLIENT.close
    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)
    monkeypatch.setattr(_CLIENT, "close", close)
    return state


def call(state, item=None, **cfg):
    return wh.evaluate(copy.deepcopy(ITEM if item is None else item), {**state.cfg, **cfg}, root=state.root)


def original_path(state, item=None):
    return cache._fabric_cache_path(state.root / "data/whitehouse/reply_cache",
                                   wh._wh_source_key(ITEM if item is None else item))


def original(state, item=None):
    return json.loads(original_path(state, item).read_text())["entries"][-1]


def usage(state):
    return [json.loads(line) for line in state.cost_path.read_text().splitlines()] if state.cost_path.exists() else []


@pytest.mark.parametrize("section", ["presidential-actions", "treasury"])
def test_public_cold_warm_actual_model_usage_and_context_only(whitehouse, section):
    state = whitehouse
    item = {**ITEM, "section": section}
    def before_send():
        row = original(state, item)
        assert row["state"] == "pending"
        assert row["operation_id"] == state.native.pending_at_send[0][0]["turn_id"]
        with cache._cache_lock(original_path(state, item), state.root):
            assert cache._fabric_cache_state(original_path(state, item), wh._wh_source_key(item))["entries"]
    state.native.on_upstream = before_send
    first = call(state, item)
    assert first["activated"] and first["model"] == MODEL and first["banner_days"] == 7
    assert first["banner_title_zh"] == "汽车关税" and first["is_context_only"]
    assert first["disclaimer"] == wh.DISCLAIMER and first["degraded_reason"] is None
    assert first["tickers"][0]["symbol"] == "GM"
    row = original(state, item)
    assert row["state"] == "terminal" and row["receipt"]["close"]["closed"]
    assert len(state.native.posts) == len(state.closes) == len(usage(state)) == 1
    actual = usage(state)[0]
    assert (actual["model"], actual["lane"], actual["input_tokens"], actual["output_tokens"]) == (MODEL, "whitehouse", 11, 7)
    assert len(ai_costs.read_usage(root=state.usage_root)) == 1
    request = json.loads(state.native.posts[0][1])
    assert request["max_tokens"] == 128 and "temperature" not in request and "seed" not in request
    assert ("TREASURY LIQUIDITY EVENT" in request["messages"][-1]["content"]) == (section == "treasury")
    before = list(state.events)
    warm = call(state, item)
    assert {k: v for k, v in warm.items() if k != "generated_at"} == {k: v for k, v in first.items() if k != "generated_at"}
    assert state.events == before and len(state.native.posts) == len(state.closes) == len(usage(state)) == 1


@pytest.mark.parametrize("field", ["guid", "id", "url"])
def test_stable_source_precedence_and_pending_before_changed_inputs(whitehouse, monkeypatch, field):
    state = whitehouse
    item = {k: v for k, v in ITEM.items() if k not in ("guid", "id", "url") or k == field}
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(call, state, item)
        try:
            assert state.native.arrived.wait(3)
            saved = original(state, item)["operation_id"]
            monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
            duplicate = call(state, {**item, "body": "A changed body.", "title": "Changed title"}, max_tokens=64)
            assert not duplicate["activated"] and duplicate["degraded_reason"] == "fabric_original_held"
            assert duplicate["model"] == "(none)" and original(state, item)["operation_id"] == saved
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert first.result(timeout=5)["activated"]
    assert len(usage(state)) == len(state.closes) == 1


def test_fresh_process_observes_original_before_selector_or_credentials(whitehouse):
    state = whitehouse
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(call, state)
        try:
            assert state.native.arrived.wait(3)
            script = """import json,sys
from pathlib import Path
from lib import config
from engine import whitehouse_brain as wh, llm_auth as auth
config.ROOT=Path(sys.argv[1])
def forbidden(*args,**kwargs):raise SystemExit('unexpected provider discovery')
wh._provider=forbidden;auth.build_providers=forbidden;config.secret=forbidden
print(json.dumps(wh.evaluate(json.loads(sys.argv[2]), {'enabled':True}, root=config.ROOT)))
"""
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            env.pop(auth.APPLICATION_MODE_ENV, None)
            r = subprocess.run([sys.executable, "-c", script, str(state.root), json.dumps(ITEM)],
                               env=env, capture_output=True, text=True, timeout=20)
            assert r.returncode == 0, r.stderr
            assert json.loads(r.stdout)["degraded_reason"] == "fabric_original_held"
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert first.result(timeout=5)["activated"]


def test_two_processes_compete_for_one_durable_source_claim(whitehouse):
    ctx = multiprocessing.get_context("fork")
    start = ctx.Event()
    children = []
    def run(connection):
        start.wait(5)
        connection.send(call(whitehouse))
        connection.close()
    try:
        for _ in range(2):
            receiver, sender = ctx.Pipe(duplex=False)
            child = ctx.Process(target=run, args=(sender,))
            child.start();sender.close();children.append((child, receiver))
        start.set()
        results = []
        for child, receiver in children:
            assert receiver.poll(10)
            results.append(receiver.recv());child.join(10)
            assert child.exitcode == 0
        assert any(result["activated"] for result in results)
        assert len(whitehouse.native.posts) == len(usage(whitehouse)) == 1
        assert whitehouse.native.rows("leases")[0]["state"] == "released"
        assert original(whitehouse)["state"] == "terminal"
    finally:
        start.set()
        for child, receiver in children:
            if child.is_alive(): child.terminate();child.join(5)
            receiver.close()


@pytest.mark.parametrize("mutation", ["remove", "invalid", "profile", "empty-profile", "model", "identity", "capability"])
def test_warm_rechecks_eligibility_and_identity_without_regrading(whitehouse, monkeypatch, mutation):
    state = whitehouse
    assert call(state)["activated"]
    before = list(state.events)
    changes = {}
    if mutation == "remove": monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    elif mutation == "invalid": monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    elif mutation == "profile": changes["workload_profile"] = "development_agent"
    elif mutation == "empty-profile": changes["workload_profile"] = None
    elif mutation in ("model", "identity"):
        replacement = replace(state.transport, **({"model": "other-model"} if mutation == "model" else {"cap_id": "fabric:new"}))
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", replacement)
        state.row.update({k: getattr(replacement, k) for k in owner._APPLICATION_IDENTITY_FIELDS});state.save()
    else:
        state.manifest["capabilities"][0]["allowed_lanes"] = ["unrelated"];state.save()
    result = call(state, **changes)
    assert not result["activated"] and result["degraded_reason"] and result["model"] == "(none)"
    assert state.events == before and len(state.native.posts) == len(state.closes) == len(usage(state)) == 1


def test_selection_removal_after_durable_claim_refuses_before_binding(whitehouse, monkeypatch):
    save = cache._cache_save
    def remove(path, value):
        save(path, value)
        if value["entries"][-1]["state"] == "pending": monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(cache, "_cache_save", remove)
    result = call(whitehouse)
    assert not result["activated"] and result["degraded_reason"]
    assert whitehouse.events == whitehouse.native.posts == whitehouse.closes == usage(whitehouse) == []
    assert original(whitehouse)["operation_id"]


def test_inspection_to_bind_identity_change_refuses_without_credentials(whitehouse, monkeypatch):
    inspect = owner.ApplicationFabricFactory.inspect
    def race(factory, *args, **kwargs):
        value = inspect(factory, *args, **kwargs)
        changed = replace(whitehouse.transport, cap_id="fabric:changed")
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
        whitehouse.row["cap_id"] = changed.cap_id;whitehouse.save()
        return value
    monkeypatch.setattr(owner.ApplicationFabricFactory, "inspect", race)
    assert not call(whitehouse)["activated"]
    assert whitehouse.events == whitehouse.native.posts == usage(whitehouse) == []


@pytest.mark.parametrize("case", ["length", "refusal", "stop_sequence", "empty", "bad-json", "list", "sectors", "tickers", "tools", "model", "http-error"])
def test_unacceptable_response_never_activates_repairs_or_replays(whitehouse, case):
    state = whitehouse
    if case in ("length", "refusal", "stop_sequence"): state.native.response = packet(finish=case)
    elif case in ("empty", "bad-json"): state.native.response = packet("" if case == "empty" else "not json")
    elif case == "list": state.native.response = packet([answer()])
    elif case in ("sectors", "tickers"): state.native.response = packet(answer(**{case: {"bad": "shape"}}))
    elif case == "tools":
        state.native.response = packet(finish="tool_calls")
        state.native.response["choices"][0]["message"].update(tool_calls=[{"id": "unasked", "type": "function",
            "function": {"name": "write", "arguments": "{}"}}])
    elif case == "model": state.native.response = packet(model="actual-other-model")
    else: state.native.response_status = 503
    first = call(state)
    assert not first["activated"] and first["degraded_reason"] and first["model"] == "(none)"
    assert original(state)["result"] is None
    assert not call(state)["activated"]
    assert len(state.native.posts) == len(state.closes) == 1
    assert len(usage(state)) <= 1
    if case in ("http-error", "model"):
        assert len(usage(state)) == 1 and usage(state)[0]["input_tokens"] == 11
        assert usage(state)[0]["model"] == ("actual-other-model" if case == "model" else MODEL)


@pytest.mark.parametrize("failure", ["settlement", "close"])
def test_known_answer_unknown_settlement_stays_inactive_and_held(whitehouse, monkeypatch, failure):
    state = whitehouse
    target = "complete_application" if failure == "settlement" else "close_application_turn"
    with patch.object(state.native.gateway, target, side_effect=OSError("synthetic lost acknowledgement")):
        first = call(state)
    assert not first["activated"] and first["degraded_reason"]
    saved = original(state)
    assert saved["state"] == "held" and saved["receipt"]["effect_unknown"]
    assert saved["receipt"]["observed_usage"]["input_tokens"] == 11
    if failure == "close": assert saved["result"] == answer()
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert call(state)["degraded_reason"] == "fabric_original_held"
    assert len(state.native.posts) == len(state.closes) == len(usage(state)) == 1


def test_missing_usage_never_becomes_zero_or_another_call(whitehouse):
    whitehouse.native.response = packet(usage=False)
    first = call(whitehouse)
    assert first["activated"]
    saved = original(whitehouse)["receipt"]
    assert saved["usage"]["usage_state"] == "unknown"
    assert saved["usage"]["input_tokens"] is saved["usage"]["output_tokens"] is None
    assert call(whitehouse)["activated"] and len(whitehouse.native.posts) == 1


@pytest.mark.parametrize("body", ['{"schema":1,"schema":2}', '{"schema":"foreign"}', 'null', '{"v":NaN}', 'broken'])
def test_corruption_is_not_absence_when_selector_is_removed(whitehouse, monkeypatch, body):
    p = original_path(whitehouse);p.parent.mkdir(parents=True);p.write_text(body)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert call(whitehouse)["degraded_reason"] == "fabric_cache_refused"
    assert whitehouse.events == whitehouse.native.posts == usage(whitehouse) == []


@pytest.mark.parametrize("phase", ["ancestry", "lock", "replace", "file-fsync", "readback"])
def test_preclaim_durability_failure_never_binds_and_does_not_bypass_next_call(whitehouse, monkeypatch, phase):
    state = whitehouse
    if phase == "ancestry": monkeypatch.setattr(cache, "_cache_sync_directory", Mock(side_effect=OSError("sync")))
    elif phase == "lock": monkeypatch.setattr(cache, "_cache_lock", Mock(side_effect=OSError("lock")))
    elif phase == "replace": monkeypatch.setattr(cache.os, "replace", Mock(side_effect=OSError("replace")))
    elif phase == "file-fsync":
        import stat
        fsync = cache.os.fsync
        def fail_file(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode): raise OSError("file fsync")
            return fsync(fd)
        monkeypatch.setattr(cache.os, "fsync", fail_file)
    else:
        save = cache._cache_save
        def lost_ack(path, value): save(path, value);raise OSError("save readback acknowledgement")
        monkeypatch.setattr(cache, "_cache_save", lost_ack)
    assert not call(state)["activated"] and not call(state)["activated"]
    assert state.events == state.native.posts == usage(state) == []


def test_response_publication_failure_retains_original_and_usage_once(whitehouse, monkeypatch):
    save = cache._cache_save
    def fail_outcome(path, value):
        if value["entries"][-1]["state"] != "pending": raise OSError("before result publication")
        return save(path, value)
    monkeypatch.setattr(cache, "_cache_save", fail_outcome)
    assert not call(whitehouse)["activated"] and original(whitehouse)["state"] == "pending"
    assert call(whitehouse)["degraded_reason"] == "fabric_original_held"
    assert len(whitehouse.native.posts) == len(whitehouse.closes) == len(usage(whitehouse)) == 1


def test_cancellation_after_bind_closes_once_and_retains_pending(whitehouse, monkeypatch):
    def interrupted(client, **kwargs): raise KeyboardInterrupt("synthetic cancellation")
    monkeypatch.setattr(_CLIENT, "create", interrupted)
    with pytest.raises(KeyboardInterrupt): call(whitehouse)
    assert original(whitehouse)["state"] == "pending"
    assert call(whitehouse)["degraded_reason"] == "fabric_original_held"
    assert len(whitehouse.closes) == 1 and whitehouse.native.posts == []


def test_pure_label_and_disabled_paths_have_no_provider_effects(whitehouse):
    label = wh.provider_label(whitehouse.cfg)
    assert MODEL in label and "eligible" in label
    assert call(whitehouse, enabled=False)["degraded_reason"] == "disabled"
    assert whitehouse.events == whitehouse.native.posts == whitehouse.closes == usage(whitehouse) == []


@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_invalid_purpose_cannot_be_replaced_by_batch(whitehouse, profile):
    assert not call(whitehouse, workload_profile=profile)["activated"]
    assert whitehouse.events == whitehouse.native.posts == usage(whitehouse) == []


@pytest.mark.parametrize("value", ["Infinity", 10 ** 400])
def test_extreme_numbers_preserve_incumbent_bounded_coercion_on_cold_and_warm(whitehouse, value):
    whitehouse.native.response = packet(answer(importance=value))
    first = call(whitehouse)
    assert not first["activated"] and first["importance"] == 0
    assert not call(whitehouse)["activated"] and len(whitehouse.native.posts) == 1
    whitehouse.native.response = packet(answer(banner_days=value))
    second = call(whitehouse, {**ITEM, "guid": "government:extreme-days"})
    assert second["activated"] and second["banner_days"] == 3
    assert call(whitehouse, {**ITEM, "guid": "government:extreme-days"})["banner_days"] == 3
    assert len(whitehouse.native.posts) == 2


def test_default_token_contract_is_four_thousand_without_sampling(whitehouse):
    whitehouse.cfg.pop("max_tokens")
    assert call(whitehouse)["activated"]
    request = json.loads(whitehouse.native.posts[0][1])
    assert request["max_tokens"] == 4000 and "temperature" not in request and "seed" not in request


def test_direct_tuple_contract_has_its_own_exact_prompt_owner(whitehouse):
    first = wh._call_model("Fixture system", "Fixture user", whitehouse.cfg)
    assert isinstance(first, tuple) and len(first) == 2 and json.loads(first[0]) == answer() and first[1] is None
    assert wh._call_model("Fixture system", "Fixture user", whitehouse.cfg) == first
    assert len(whitehouse.native.posts) == len(whitehouse.closes) == len(usage(whitehouse)) == 1


def test_native_text_cache_is_never_relabelled_and_provider_root_is_not_market_root(whitehouse, tmp_path):
    state = whitehouse
    wh._wh_reply_cache_put(wh._wh_prompt_hash(MODEL, "old", "old"), "native plain text", state.cfg)
    market = tmp_path / "market";market.mkdir()
    result = wh.evaluate(ITEM, state.cfg, root=market)
    assert result["activated"] and result["model"] == MODEL
    assert original_path(state).exists() and not (market / "data/whitehouse/reply_cache").exists()
    assert len(state.native.posts) == 1


def test_native_tuple_stub_remains_compatible(whitehouse, monkeypatch):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(wh, "provider_label", lambda cfg: "native label")
    callback = Mock(return_value=(json.dumps(answer()), None))
    monkeypatch.setattr(wh, "_call_model", callback)
    result = call(whitehouse)
    assert result["activated"] and result["model"] == "native label" and len(callback.call_args.args) == 3
    assert whitehouse.native.posts == []


def test_native_to_selected_drift_before_legacy_call_refuses(whitehouse, monkeypatch):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    def backdrop(root): monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric");return "changed mode"
    monkeypatch.setattr(wh, "_macro_backdrop", backdrop)
    monkeypatch.setattr(wh, "provider_label", lambda cfg: "native label")
    callback = Mock(side_effect=AssertionError("must not enter native call"))
    monkeypatch.setattr(wh, "_call_model", callback)
    result = call(whitehouse)
    assert result["degraded_reason"] == "fabric_selection_changed" and not result["activated"]
    callback.assert_not_called()
    assert whitehouse.native.posts == []
