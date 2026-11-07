"""Request budgets through the existing immutable factory and actual native B/A.

No new timer/transport is under test: the owner must pass the caller's bound to
the incumbent client before secrets, while normal uncertainty custody remains.
"""
from dataclasses import FrozenInstanceError
import hashlib
import math
import os
from pathlib import Path
import threading
import time

import pytest
import yaml

from engine import llm_auth as auth, provider_production_modes as owner
from engine.marketing import copy_auditor as auditor
from engine.neuralweb import brain_gateway as brain
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL, invoke  # noqa: F401
from tests.test_fabric_gateway_composition import public_brain  # noqa: F401
from tests.test_fabric_brain_buffered_delivery import turn, packet, event, assistant_turns  # noqa: F401


def cfg(**changes):
    return {"workload_profile": "site_interactive", "provider_order": ["fabric"], **changes}


@pytest.mark.parametrize("budget,expected", [(None, 60.0), (0.1, 0.1), (5, 5.0), (45, 45.0),
                                            (90, 90.0), (150, 150.0), (900, 900.0)])
def test_factory_passes_numeric_budget_and_keeps_legacy_default(binding, budget, expected):
    _, _, _, _, events, _, make, _ = binding
    factory = make(cfg(client_timeout_s=budget))
    assert events == []
    actual = factory()
    assert actual["client"]._timeout == expected
    assert events == ["credential", "client"]
    actual["client"].close()


def test_absent_and_none_preserve_protocol_default_and_inspection_identity(binding):
    _, _, _, _, events, _, make, _ = binding
    absent, explicit_none = make(cfg()), make(cfg(client_timeout_s=None))
    assert absent.inspect() == explicit_none.inspect()
    assert events == []
    for factory in (absent, explicit_none):
        client = factory()["client"]
        assert client._timeout == 60.0
        client.close()


@pytest.mark.parametrize("budget", [True, False, 0, -1, 901, 10**400, math.inf, -math.inf, math.nan,
                                  "5", "", [], {}])
def test_bad_startup_budget_refuses_before_inspection_or_credentials(binding, budget):
    _, _, _, _, events, _, make, _ = binding
    with pytest.raises(owner.ApplicationFabricBindingError, match="timeout_invalid"):
        make(cfg(client_timeout_s=budget))
    assert events == []


@pytest.mark.parametrize("budget", [True, False, 0, -1, 901, 10**400, math.inf, math.nan, "5", [], {}])
@pytest.mark.parametrize("action", ["inspect", "bind"])
def test_bad_later_budget_refuses_before_secrets(binding, budget, action):
    _, _, _, _, events, _, make, _ = binding
    factory = make(cfg(client_timeout_s=45))
    with pytest.raises(owner.ApplicationFabricBindingError, match="timeout_invalid"):
        if action == "inspect": factory.inspect(cfg(client_timeout_s=budget))
        else: factory._bind_with_workload(cfg(client_timeout_s=budget))
    assert events == []


@pytest.mark.parametrize("startup,caller,expected", [
    (None, None, 60), (None, 5, 5), (None, 150, 150),
    (45, None, 45), (45, 5, 5), (45, 90, 45),
    (5, None, 5), (5, 2, 2), (5, 45, 5), (150, 900, 150),
])
def test_later_caller_can_narrow_but_cannot_widen_startup_cap(binding, startup, caller, expected):
    _, _, _, _, events, _, make, _ = binding
    factory = make(cfg(client_timeout_s=startup))
    identity = factory.inspect(cfg(client_timeout_s=caller))
    assert events == []
    pinned = factory.with_inspection(identity)
    result, decision = pinned._bind_with_workload(cfg(client_timeout_s=caller))
    assert result["client"]._timeout == expected
    assert decision.allowed_order == ("fabric",)
    result["client"].close()


def test_timeout_snapshot_is_immutable_and_with_inspection_preserves_it(binding):
    _, _, _, _, events, _, make, _ = binding
    source = cfg(client_timeout_s=5)
    factory = make(source)
    source["client_timeout_s"] = 900
    with pytest.raises(FrozenInstanceError): factory._timeout_cap = 900
    pinned = factory.with_inspection(factory.inspect())
    assert events == []
    result, _ = pinned._bind_with_workload(source)
    assert result["client"]._timeout == 5
    result["client"].close()


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
@pytest.mark.parametrize("budget,expected", [(None, 90), (5, 5), (45, 45), (150, 150), (900, 900)])
def test_native_shared_owner_forwards_budget_without_changing_identity_or_usage(selected, budget, expected):
    operation = selected.operation(client_timeout_s=budget)
    provider = operation.providers[0]
    assert provider["client"]._client._timeout == expected
    result = auth.make_call(operation.providers, invoke)
    assert result == ("Fixture answer.", None, "fabric")
    assert len(selected.native.posts) == len(selected.costs) == 1
    assert selected.costs[0]["model"] == MODEL
    operation.close()
    assert provider["_fabric_close"]["closed"]
    assert selected.native.rows("leases")[0]["state"] == "released"


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
def test_short_deadline_is_one_post_and_preserves_unknown_until_original_settlement(selected, monkeypatch):
    native = selected.native
    native.block = threading.Event()
    settled = threading.Event()
    original = native.gateway.complete_application
    def complete(*args, **kwargs):
        result = original(*args, **kwargs)
        settled.set()
        return result
    monkeypatch.setattr(native.gateway, "complete_application", complete)
    operation = selected.operation(client_timeout_s=1.0)
    provider = operation.providers[0]
    started = time.monotonic()
    try:
        with pytest.raises(auth.FabricProviderError) as caught:
            auth.make_call(operation.providers, invoke)
        assert caught.value.effect_unknown
        assert time.monotonic() - started < 2.8
        assert native.arrived.is_set() and len(native.posts) == 1
        assert selected.costs == []  # the downstream did not observe billed usage
        assert auth.fabric_usage(provider)["input_tokens"] is None
        operation.close()
        assert not provider["_fabric_close"]["closed"]
        assert native.rows("leases")[0]["state"] in {"held", "rented"}
        assert len(native.posts) == 1
    finally:
        native.block.set()
        assert settled.wait(3), "original synthetic provider completion did not settle"
    assert native.rows("application_requests")[0]["state"] == "terminal"
    assert len(native.posts) == 1


def brain_config():
    path = Path(brain.__file__).resolve().parents[2] / "config/brain.yml"
    raw = path.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == \
        "1890db7cb2ed4617dcb8923a91e5c9967220a8c2"
    return yaml.safe_load(raw)


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
@pytest.mark.parametrize("lane,budget", [("fast", 120), ("pro", 600)])
@pytest.mark.parametrize("streaming", [False, True])
def test_public_brain_adopts_existing_trusted_lane_budget(turn, monkeypatch, lane, budget, streaming):
    configuration = brain_config()
    assert configuration["lanes"][lane]["client_timeout_s"] == budget
    monkeypatch.setattr(brain, "_load_brain_config", lambda *_a: configuration)
    turn.kwargs["lane"] = lane
    turn.plans((200, packet()))
    if streaming:
        events = [event(line) for line in brain.chat_stream(**turn.kwargs)]
        result = events[-1]
    else:
        result = brain.chat(**turn.kwargs)
    assert not result["degraded"]
    assert turn.providers[0]["client"]._client._timeout == budget
    assert len(turn.native.posts) == len(turn.costs) == len(turn.closes) == 1
    assert turn.native.rows("leases")[0]["state"] == "released"


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
@pytest.mark.parametrize("lane", ["fast", "pro"])
@pytest.mark.parametrize("stop", [False, True])
def test_configured_brain_budget_preserves_producer_on_subscriber_detach_or_stop(turn, monkeypatch, lane, stop):
    from app import brain_runs
    configuration = brain_config()
    monkeypatch.setattr(brain, "_load_brain_config", lambda *_a: configuration)
    turn.kwargs["lane"] = lane
    turn.plans((200, packet()))
    turn.native.block = threading.Event()
    run = brain_runs.start(brain.chat_stream(**turn.kwargs), user_id=turn.kwargs["user_id"], lane=lane)
    try:
        follower = brain_runs.follow(run, interval=0.05)
        next(follower)
        follower.close()
        assert turn.native.arrived.wait(2)
        if stop: assert brain_runs.cancel(run.run_id, turn.kwargs["user_id"])
        assert not run.done and not turn.closes
        assert turn.providers[0]["client"]._client._timeout == configuration["lanes"][lane]["client_timeout_s"]
        turn.native.block.set()
        with run._cv: assert run._cv.wait_for(lambda: run.done, timeout=3)
        assert len(turn.native.posts) == len(turn.costs) == len(turn.closes) == 1
        assert assistant_turns(turn) == ["Grounded final response."]
        assert sum(event(line).get("type") == "done" for line in run.events) == 1
        assert turn.native.rows("leases")[0]["state"] == "released"
    finally:
        turn.native.block.set()
        with run._cv: run._cv.wait_for(lambda: run.done, timeout=3)
        with brain_runs._runs_lock: brain_runs._runs.pop(run.run_id, None)


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
@pytest.mark.parametrize("completed_first", [False, True])
def test_public_brain_expiry_preserves_known_usage_and_never_persists_unfinished_answer(turn, monkeypatch, completed_first):
    configuration = brain_config()
    configuration["lanes"]["pro"].update(client_timeout_s=1.0, tool_budget=1)
    monkeypatch.setattr(brain, "_load_brain_config", lambda *_a: configuration)
    responses = [(200, packet("Earlier narration is not a final answer.", tool=True))] if completed_first else []
    responses.append((200, packet("Late answer is not yet observed downstream.")))
    turn.plans(*responses)
    original_reply = turn.native.on_upstream
    gate, settled = threading.Event(), threading.Event()
    def reply():
        original_reply()
        if len(turn.native.posts) == len(responses): turn.native.block = gate
    turn.native.on_upstream = reply
    original_complete = turn.native.gateway.complete_application
    def complete(*args, **kwargs):
        result = original_complete(*args, **kwargs)
        if len(turn.native.posts) == len(responses): settled.set()
        return result
    monkeypatch.setattr(turn.native.gateway, "complete_application", complete)
    try:
        events = [event(line) for line in brain.chat_stream(**turn.kwargs)]
        assert events[-1]["degraded"]
        assert not assistant_turns(turn)
        assert all("Earlier narration" not in item.get("text", "") for item in events)
        assert len(turn.native.posts) == len(responses) and len(turn.closes) == 1
        assert turn.tool.call_count == int(completed_first)
        assert not turn.providers[0]["_fabric_close"]["closed"]
        assert turn.native.rows("leases")[0]["state"] in {"held", "rented"}
        usage = auth.fabric_usage(turn.providers[0])
        assert usage["input_tokens"] is None
        if completed_first:
            assert usage["completed_input_tokens"] == 11
            assert sum(cost["input_tokens"] for cost in turn.costs) == 11
        else:
            assert not turn.costs
        assert all(log["answer"] == "" for log in turn.logs)
    finally:
        gate.set()
        assert settled.wait(3), "original delayed response did not settle"
    assert len(turn.native.posts) == len(responses)


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
def test_auditor_cache_rebuilds_inert_recipe_after_budget_change(selected, monkeypatch):
    selected.manifest["capabilities"][0]["allowed_lanes"].append("marketing-auditor")
    selected.save()
    monkeypatch.setattr(auditor, "_PROVIDER_CACHE", {})
    configuration = {"usage_lane": "marketing-auditor", "oauth_pool_lane": "marketing-auditor",
        "provider_order": ["oauth"], "workload_profile": "site_interactive", "client_timeout_s": 90}
    initial = auditor._providers(configuration)
    assert auditor._providers(configuration) is initial
    configuration["client_timeout_s"] = 5
    narrowed = auditor._providers(configuration)
    assert narrowed is not initial and selected.events == []
    for recipe, expected in ((initial, 90), (narrowed, 5)):
        with auth.begin_operation(recipe, context="marketing_auditor") as operation:
            assert operation.providers[0]["client"]._client._timeout == expected
            assert auth.make_call(operation.providers, invoke)[0] == "Fixture answer."
    assert len(selected.native.posts) == len(selected.costs) == 2
    assert all(row["state"] == "released" for row in selected.native.rows("leases"))


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired native source required")
def test_bad_auditor_budget_cannot_reuse_a_valid_cached_recipe(selected, monkeypatch):
    selected.manifest["capabilities"][0]["allowed_lanes"].append("marketing-auditor")
    selected.save()
    monkeypatch.setattr(auditor, "_PROVIDER_CACHE", {})
    configuration = {"usage_lane": "marketing-auditor", "oauth_pool_lane": "marketing-auditor",
        "provider_order": ["oauth"], "workload_profile": "site_interactive", "client_timeout_s": 5}
    original = auditor._providers(configuration)
    configuration["client_timeout_s"] = True
    invalid = auditor._providers(configuration)
    assert invalid is not original
    with pytest.raises(auth.FabricProviderError): auth.begin_operation(invalid)
    assert selected.events == selected.native.posts == selected.costs == []
