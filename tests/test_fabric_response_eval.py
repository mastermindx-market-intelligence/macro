"""Fail-closed selected-Fabric response evaluator regression cases.

No real model/provider/network; these tests guard application-selection custody
through the original engine.llm_auth owner.  A refused binding must never be
turned into a native waterfall or a second request.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport
from engine import llm_auth as auth
from engine.neuralweb import response_eval as ev
from tests.test_fabric_application_binding import binding  # noqa: F401


@pytest.mark.parametrize("consumer", ["one_shot", "judge", "answer"])
def test_selected_binding_refusal_never_retries_or_uses_legacy(consumer, monkeypatch):
    calls = []

    class RefusingOwner:
        def application_mode_id(self, cfg):
            calls.append("selection")
            return "shared_fabric"

        def build_providers(self, cfg, **kwargs):
            calls.append("recipe")
            return [{"model": "fixture-model"}]

        def begin_operation(self, providers, *, context):
            calls.append("bind")
            raise RuntimeError("synthetic pre-dispatch binding denial")

        def make_call(self, *args, **kwargs):
            pytest.fail("denied selected Fabric binding reached legacy waterfall")

    monkeypatch.setattr(ev, "_owner", lambda: RefusingOwner())
    monkeypatch.setattr(ev, "_llm_cfg", lambda *args, **kwargs: {"selected": True})

    if consumer == "one_shot":
        result = ev._one_shot({}, "", "prompt", max_tokens=10, context="test")
        assert result is None
    elif consumer == "judge":
        judge = ev.judge_via_llm_auth()
        assert judge.model_id is None
        assert judge("grade a row") is None
        assert judge.model_id is None
    else:
        answer = ev.answer_via_llm_auth()
        assert answer.model_id is None
        assert answer("system", "user") is None
        assert answer.model_id is None

    assert calls.count("recipe") == 1, calls
    assert calls.count("bind") == 1, calls


@pytest.fixture
def selected_owner(binding, monkeypatch):
    """The real shared policy/operation owner; outbound transport is synthetic."""
    root, _row, _doc, manifest, _events, save, _make, _identity = binding
    # The existing binder resolves the lane from usage_lane, or "application".
    manifest["capabilities"][0]["allowed_lanes"].extend(
        ["application", "response_eval_benchmark", "response_eval_judge"])
    save()
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "site_batch")
    monkeypatch.setattr(auth, "_repo_root", lambda: root)
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: None)
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: None)
    monkeypatch.setattr(
        auth, "_oauth_pool_candidates",
        Mock(side_effect=AssertionError("legacy credential discovery")))
    monkeypatch.setattr(
        "lib.config.secret",
        Mock(side_effect=AssertionError("legacy credential discovery")))

    state = SimpleNamespace(root=root, calls=[], closes=0, replies=[])

    class Client:
        def __init__(self, **kwargs):
            self.messages = self

        def create(self, **kwargs):
            state.calls.append(kwargs)
            reply = state.replies.pop(0)
            return SimpleNamespace(
                model="fixture-model", stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text=reply)],
                usage=SimpleNamespace(input_tokens=11, output_tokens=7))

        def close(self):
            state.closes += 1

    monkeypatch.setattr(transport, "FabricInferenceClient", Client)
    return state


def test_selected_answer_real_owner_one_served_model_and_close(selected_owner):
    state = selected_owner
    state.replies = ["Actionable, conditional result."]
    answer = ev.answer_via_llm_auth(root=state.root, model="request-label")
    assert answer.model_id is None
    assert answer("system", "question") == "Actionable, conditional result."
    assert answer.model_id == "fixture-model"
    assert state.closes == 1 and len(state.calls) == 1
    assert state.calls[0]["model"] == "fixture-model"
    assert state.calls[0]["messages"] == [{"role": "user", "content": "question"}]


def test_selected_judge_real_owner_one_binding_deliberate_parse_reask(selected_owner):
    state = selected_owner
    verdict = json.dumps({
        "scores": {axis: 0 for axis in ev.RUBRIC}, "tags": [], "note": "ok"})
    state.replies = ["not-json", verdict]
    judge = ev.judge_via_llm_auth(root=state.root, model="request-label")
    assert judge.model_id is None
    assert judge("grade this row") == verdict
    assert judge.model_id == "fixture-model"
    assert state.closes == 1 and len(state.calls) == 2
    assert state.calls[0]["model"] == state.calls[1]["model"] == "fixture-model"
    assert state.calls[0]["messages"][0]["content"] != state.calls[1]["messages"][0]["content"]
