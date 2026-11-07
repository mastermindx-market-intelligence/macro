"""Real selected Press writer/stager -> shared owner -> pinned native B/A.

Only qualification, accounts, service credential and upstream are synthetic.
The existing staging checkpoint, prompts, validators and accounting remain real.
"""
import json
import os
import re
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.press import writer
from scripts import run_press
from tests import press_fixtures as F
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
CLIENT = transport.FabricInferenceClient


def packet(text):
    return {"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def press(selected, monkeypatch, tmp_path):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"].append("press-brief")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setattr(writer, "_model_id", Mock(side_effect=AssertionError("legacy model map")))
    state.cfg, state.slot = F.config(), F.slot()
    state.run_state = writer.RunState()
    state.content_root = F.fixture_root(tmp_path / "content")
    state.staging = state.content_root / "data/press/staging"
    state.draft = F.draft_from_slot(state.slot, extra_filler=-3)
    state.native.response = packet(json.dumps(state.draft))
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
    state.write = lambda **kw: writer.write(state.slot, state.cfg, state=state.run_state, **kw)
    state.stage = lambda **kw: run_press._stage_preplanned_slots(state.content_root, state.cfg,
        slots=[state.slot], staging_dir=state.staging, run_date="2026-07-26",
        state=state.run_state, max_regenerations=3, taken_slugs=set(), **kw)
    state.staged = lambda: json.loads((state.staging / (state.slot["id"] + ".json")).read_text())
    return state


def closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def test_selected_success_uses_actual_provider_model_and_one_usage_owner(press):
    state = press
    result = state.write()
    assert result["ok"] and result["provider"] == "go" and result["model"] == MODEL
    assert result["draft"] == state.draft
    receipt = result["fabric_operation"]
    assert receipt["selected"] and not receipt["regeneration_allowed"]
    assert receipt["model"] == MODEL and receipt["usage"]["input_tokens"] == 11
    assert receipt["close"]["closed"] and not receipt["effect_unknown"]
    assert re.fullmatch(r"app:[0-9a-f]{32}", receipt["operation_id"])
    request = json.loads(state.native.posts[0][1])
    system, user = writer.build_prompt(state.slot, state.cfg)
    assert request["messages"] == [{"role": "system", "content": system}, {"role": "user", "content": user}]
    assert request["model"] == MODEL and request["max_tokens"] == 4000
    assert "tools" not in request and request["stream"] is False
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == "press-brief" and state.costs[0]["stage"] == "press_brief"
    assert state.run_state.calls == 1 and state.run_state.tokens_used > 0
    closed(state)


@pytest.mark.parametrize("gate", ["disabled", "circuit", "private-shape", "budget", "admitted-size", "single-shape"])
def test_existing_preflights_precede_binding_or_credentials(press, monkeypatch, gate):
    state = press;kwargs = {}
    if gate == "disabled": state.cfg["llm"]["enabled"] = False
    elif gate == "circuit": state.run_state.consecutive_failures = state.run_state.breaker_threshold
    elif gate == "private-shape": kwargs["private_admission_check"] = lambda: None
    elif gate == "budget": state.run_state.token_budget = 1
    elif gate == "single-shape": kwargs["single_attempt"] = True
    else:
        kwargs.update(single_provider_attempt=True, admitted_token_cap=True)
        monkeypatch.setattr(writer, "build_prompt", lambda *_a, **_k: ("Trusted task", "界" * 5000))
    result = state.write(**kwargs)
    assert not result["ok"] and state.events == state.native.posts == state.operations == []
    assert state.run_state.tokens_used == 0


@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_selection_remains_exclusive_and_nonregenerable(press, monkeypatch, mode):
    state = press
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["llm"][auth.APPLICATION_MODE_CFG_KEY] = mode
    result = state.write()
    assert not result["ok"] and result["fabric_operation"]["selected"]
    assert not result["fabric_operation"]["regeneration_allowed"]
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_denied_profile_is_not_replaced_before_binding(press, profile):
    state = press
    state.cfg["llm"]["workload_profile"] = profile
    result = state.write()
    assert not result["ok"] and result["provider_usage"]["accounting"] == "no_provider_call"
    assert state.events == state.native.posts == state.operations == []
    assert state.run_state.tokens_used == 0


def test_explicit_deadline_uses_existing_owner_narrowing(press):
    state = press
    state.cfg["llm"]["client_timeout_s"] = 2.0
    assert state.write()["ok"]
    assert state.operations[0][1][0]["client"]._client._timeout == 2.0


@pytest.mark.parametrize("cancel_at", [1, 2])
@pytest.mark.parametrize("reason", ["source revoked", "401 source revoked", "429 source revoked"])
def test_private_revocation_after_bind_or_at_request_is_zero_spend(press, cancel_at, reason):
    state = press;checks = []
    def check():
        checks.append(True)
        if len(checks) == cancel_at:
            raise ValueError(reason)
    result = state.write(single_provider_attempt=True, admitted_token_cap=True,
                         private_admission_check=check)
    assert not result["ok"] and result["reason"].startswith("private_admission_refused")
    assert result["provider_usage"] == {"reported": False, "accounting": "no_provider_call", "charged_tokens": 0}
    assert state.events == ["credential", "client"]
    assert len(checks) == cancel_at and state.native.posts == state.costs == state.health == []
    assert state.run_state.calls == state.run_state.failures == state.run_state.tokens_used == 0
    closed(state)


@pytest.mark.parametrize("usage", [(11, 7), (11, None), (None, 7), (11, 4001), (50000, 7)])
def test_admitted_rail_preserves_actual_usage_or_conservative_reservation(press, usage):
    state = press
    state.native.response["usage"] = {"prompt_tokens": usage[0], "completion_tokens": usage[1]}
    result = state.write(single_provider_attempt=True, admitted_token_cap=True)
    assert len(state.native.posts) == 1
    cap = result["token_cap"]
    system, user = writer.build_prompt(state.slot, state.cfg)
    assert cap["reserved_total_tokens"] == len(system.encode()) + len(user.encode()) + 512 + 4000
    assert cap["hard_limit_tokens"] == 12000
    if usage == (11, 7):
        assert result["ok"] and state.run_state.tokens_used == 18
        assert result["provider_usage"]["within_requested_bounds"]
    elif None in usage:
        assert not result["ok"] and result["reason"] == "provider_usage_missing"
        assert state.run_state.tokens_used == cap["reserved_total_tokens"]
        assert result["provider_usage"]["accounting"] == "reserved_upper_bound" and state.costs == []
    else:
        assert not result["ok"] and result["reason"] == "provider_usage_exceeds_admitted_cap"
        assert state.run_state.tokens_used == sum(usage)
    closed(state)


def test_admitted_rail_rejects_malformed_normalized_cache_metadata(press, monkeypatch):
    original = auth._FabricMessages.create
    def invalid(self, **kw):
        response = original(self, **kw)
        return replace(response, usage=SimpleNamespace(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_input_tokens=-1))
    monkeypatch.setattr(auth._FabricMessages, "create", invalid)
    result = press.write(single_provider_attempt=True, admitted_token_cap=True)
    assert not result["ok"] and result["reason"] == "provider_usage_missing"
    assert result["provider_usage"]["accounting"] == "reserved_upper_bound"
    assert len(press.native.posts) == len(press.costs) == 1


def test_terminal_error_retains_observed_usage_without_no_call_claim(press):
    state = press;state.native.response_status = 503
    result = state.write(single_provider_attempt=True, admitted_token_cap=True)
    assert not result["ok"] and result["provider_usage"]["accounting"] == "reserved_upper_bound"
    receipt = result["fabric_operation"]
    assert receipt["disposition"] == "terminal" and receipt["usage"]["input_tokens"] == 11
    assert receipt["observed_usage"]["serving_model"] == MODEL
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == MODEL
    closed(state)


def test_stager_commits_exact_original_id_before_binding_and_retains_result(press, monkeypatch):
    state = press;begin = auth.begin_operation
    def inspect(*args, **kwargs):
        prior = state.staged()
        assert prior["status"] == "in_progress" and prior["progress"]["phase"] == "provider_started"
        assert prior["fabric_operation"]["operation_id"] == kwargs["operation_id"]
        assert prior["fabric_operation"]["schema"] == "mastermind.press_fabric_intent.v1"
        return begin(*args, **kwargs)
    monkeypatch.setattr(auth, "begin_operation", inspect)
    result = state.stage()
    item = state.staged()
    assert result["passed"] == 1 and item["status"] == "passed"
    assert item["provider"] == "go" and item["model"] == MODEL
    assert item["fabric_operation"]["operation_id"] == state.closes[0]
    assert item["attempts"][0]["fabric_operation"] == item["fabric_operation"]
    assert len(state.native.posts) == len(item["attempts"]) == 1


@pytest.mark.parametrize("fault", ["empty", "tools", "refusal", "truncated", "malformed", "validator", "unknown", "http"])
def test_staging_never_regenerates_any_selected_failure(press, monkeypatch, fault):
    state = press;response = state.native.response;choice = response["choices"][0]
    if fault == "empty": choice["message"]["content"] = ""
    elif fault == "tools":
        choice["finish_reason"] = "tool_calls"
        choice["message"]["tool_calls"] = [{"id": "tool1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]
    elif fault == "refusal": choice["finish_reason"] = "content_filter"
    elif fault == "truncated": choice["finish_reason"] = "length"
    elif fault == "malformed": choice["message"]["content"] = "not an envelope"
    elif fault == "validator": choice["message"]["content"] = json.dumps(F.draft("Unsupported invented 999999 measurement."))
    elif fault == "http": state.native.response_status = 503
    else: monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    result = state.stage();item = state.staged()
    assert result["quarantined"] == 1 and len(item["attempts"]) == 1
    assert len(state.native.posts) == len(state.operations) == 1
    assert item["fabric_operation"]["operation_id"] == state.closes[0]
    if fault == "unknown":
        assert item["fabric_operation"]["effect_unknown"]
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    if fault == "validator":
        assert item["draft"] is not None and not item["validator_report"]["ok"]
    with pytest.raises(FileExistsError):
        state.stage()
    assert len(state.native.posts) == 1
    closed(state)


@pytest.mark.parametrize("initial", [True, False])
@pytest.mark.parametrize("admitted", [True, False])
def test_family_change_after_checkpoint_refuses_before_identity_or_provider_discovery(press, monkeypatch, initial, admitted):
    state = press
    if not initial:
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    write = run_press._write_stage_checkpoint
    def change(path, item, **kwargs):
        write(path, item, **kwargs)
        if kwargs.get("create"):
            if initial: monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
            else: monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setattr(run_press, "_write_stage_checkpoint", change)
    state.stage(admitted_token_cap=admitted, single_provider_attempt=admitted);item = state.staged()
    assert item["status"] == "quarantined" and len(item["attempts"]) == 1
    assert item["attempts"][0]["reason"] == "fabric_selection_changed"
    assert state.events == state.native.posts == state.operations == []
    assert state.run_state.tokens_used == 0
    if admitted:
        assert item["attempts"][0]["token_cap"]["hard_limit_tokens"] == 12000
        assert item["attempts"][0]["provider_usage"] == {
            "reported": False, "accounting": "no_provider_call", "charged_tokens": 0}
    if not initial:
        assert item["fabric_operation"]["operation_id"] is None


def test_precheckpoint_storage_failure_prevents_binding(press, monkeypatch):
    monkeypatch.setattr(run_press, "_write_stage_checkpoint", Mock(side_effect=OSError("pre-checkpoint")))
    with pytest.raises(OSError): press.stage()
    assert press.events == press.native.posts == press.operations == []


def test_postresponse_storage_failure_retains_original_intent_and_blocks_replay(press, monkeypatch):
    state = press;write = run_press._write_stage_checkpoint
    def fail_result(path, item, **kwargs):
        if item.get("fabric_operation", {}).get("schema") == "mastermind.press_fabric_operation.v1":
            raise OSError("result checkpoint")
        return write(path, item, **kwargs)
    monkeypatch.setattr(run_press, "_write_stage_checkpoint", fail_result)
    with pytest.raises(OSError): state.stage()
    prior = state.staged()
    assert prior["status"] == "in_progress" and prior["fabric_operation"]["operation_id"] == state.closes[0]
    monkeypatch.setattr(run_press, "_write_stage_checkpoint", write)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    with pytest.raises(FileExistsError): state.stage()
    assert len(state.native.posts) == 1


def test_known_answer_survives_unknown_close_with_original_hold_receipt(press, monkeypatch):
    state = press
    monkeypatch.setattr(CLIENT, "close", Mock(side_effect=OSError("close acknowledgement lost")))
    result = state.write()
    assert result["ok"] and result["model"] == MODEL
    receipt = result["fabric_operation"]
    assert receipt["effect_unknown"] and receipt["close"]["closed"] is False
    assert receipt["usage"]["input_tokens"] == 11
    assert len(state.native.posts) == len(state.costs) == 1
