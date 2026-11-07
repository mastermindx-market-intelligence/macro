"""Public editorial reviewers through the actual shared owner and native B/A.

Inputs, qualification, credentials and upstream replies are synthetic. The
parsers, counters, deterministic findings, operation and settlement stay real.
"""
import copy
import json
import os
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.marketing import copy_critic as critic, copy_review as review
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
REQUESTED = "requested-native-model"
POSTS = [{"id": str(i), "headline": "Measured context for the session",
          "body": "The same supplied fact is repeated."} for i in range(3)]
CONTEXT = {"type": "watchlist", "cashtag": "$TEST", "numbers_whitelist": ["122"]}
CRITIQUE = {"verdict": "reject", "reasons": ["The reference has no antecedent."]}
REVIEWS = [{"i": 0, "verdict": "weak", "issues": ["The reference has no antecedent."]}]


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unsolicited-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def editorial(selected, monkeypatch):
    state = selected
    critic.reset_critic_stats()
    state.manifest["capabilities"][0]["allowed_lanes"] += ["marketing-critic", "marketing-copy-review"]
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(critic, "_model_id", Mock(side_effect=AssertionError("native model prerequisite")))
    monkeypatch.setattr("lib.config.load", Mock(side_effect=AssertionError("native model map prerequisite")))
    monkeypatch.setattr(review, "lessons_from_rejections", lambda _root: ["Name the reference."])
    state.critic_cfg = {"enabled": True, "model": REQUESTED, "max_tokens": 500}
    state.review_cfg = {"copywriter": {"llm": {"enabled": True, "model_key": "absent_legacy_model"}}}
    state.closes, state.operations = [], []
    original_close, original_begin = _CLIENT.close, auth.begin_operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    monkeypatch.setattr(_CLIENT, "close", close)
    monkeypatch.setattr(auth, "begin_operation", begin)

    def plans(*responses):
        pending = list(responses)
        def upstream():
            assert pending, "unexpected additional provider request"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = upstream
    state.plans = plans
    state.critic = lambda: critic.cold_read_verdict("$TEST held 122.", CONTEXT, state.critic_cfg)
    state.review = lambda: review.review_batch(copy.deepcopy(POSTS), state.review_cfg, root=state.root)
    yield state
    critic.reset_critic_stats()


def cfg_for(state, caller):
    return state.critic_cfg if caller == "critic" else state.review_cfg["copywriter"]["llm"]


def accepted(state, caller):
    result = getattr(state, caller)()
    useful = (critic.UNAVAILABLE_REASON not in result["reasons"] if caller == "critic"
              else result["mode"] == "llm")
    return result, useful


def response_for(caller):
    return packet(json.dumps(CRITIQUE if caller == "critic" else REVIEWS))


def closed(state, count):
    assert len(state.operations) == len(state.closes) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


@pytest.mark.parametrize("verdict", ["pass", "reject"])
def test_public_critic_verdict_counters_budget_and_actual_usage(editorial, verdict):
    state = editorial
    expected = {"verdict": verdict, "reasons": CRITIQUE["reasons"] if verdict == "reject" else []}
    state.plans((200, packet(json.dumps({**expected, "rewrite": "discard this"}))))
    assert state.critic() == expected
    stats = critic.critic_stats()
    assert stats["calls"] == stats[verdict] == 1 and stats["unavailable"] == 0
    assert critic._PROVIDER_CACHE == {}
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL != REQUESTED and request["max_tokens"] == 200
    assert request["messages"][0]["content"] == critic.SYSTEM_PROMPT
    assert request["messages"][1]["content"] == critic._build_user_message("$TEST held 122.", CONTEXT)
    assert "tools" not in request and request["stream"] is False
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == "marketing-critic" and state.costs[0]["stage"] == "marketing_critic"
    assert state.costs[0]["model"] == MODEL and state.costs[0]["input_tokens"] == 11
    assert state.operations[0][1][0]["client"]._client._timeout == 90.0
    closed(state, 1)


def test_public_review_works_without_legacy_model_map_and_preserves_mechanics(editorial):
    state = editorial
    state.plans((200, response_for("review")))
    result = state.review()
    # Existing high-severity mechanical findings still escalate the advisory
    # per-post label after the model's weak verdict; neither finding is lost.
    assert result["mode"] == "llm" and result["posts"][0]["verdict"] == "bad"
    assert CRITIQUE["reasons"][0] in result["posts"][0]["issues"]
    assert any(row["kind"] == "repeated_headline" for row in result["batch"])
    assert any(row["kind"] == "identical_body" for row in result["batch"])
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == 2000
    assert "Name the reference." in request["messages"][0]["content"]
    assert json.loads(request["messages"][1]["content"]) == [
        {"i": i, "headline": post["headline"], "body": post["body"]} for i, post in enumerate(POSTS)]
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["lane"] == "marketing-copy-review"
    assert state.costs[0]["stage"] == "marketing_copy_review" and state.costs[0]["model"] == MODEL
    closed(state, 1)


def test_each_critic_invocation_owns_a_fresh_recipe_client_and_operation(editorial):
    state = editorial
    first, second = critic._providers(state.critic_cfg), critic._providers(state.critic_cfg)
    assert first is not second and first[0] is not second[0]
    assert first[0]["_fabric_recipe"] and first[0]["client"] is None
    assert state.events == state.operations == state.native.posts == []
    assert critic._PROVIDER_CACHE == {}
    state.plans((200, response_for("critic")), (200, response_for("critic")))
    assert state.critic() == state.critic() == CRITIQUE
    assert len(set(state.closes)) == 2
    assert len({id(providers[0]["client"]) for _, providers in state.operations}) == 2
    assert critic._PROVIDER_CACHE == {} and len(state.native.rows("leases")) == 2
    closed(state, 2)


def test_host_selection_precedes_an_existing_native_provider_cache(editorial, monkeypatch):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(critic, "_model_id", lambda _cfg: REQUESTED)
    real_build = auth.build_providers
    native_provider = {"name": "anthropic", "cred": "fixture", "model": REQUESTED, "client": object()}
    monkeypatch.setattr(auth, "build_providers", lambda *_args, **_kwargs: [native_provider])
    assert critic._providers(state.critic_cfg) == [native_provider]
    assert len(critic._PROVIDER_CACHE) == 1
    monkeypatch.setattr(auth, "build_providers", real_build)
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
    state.plans((200, response_for("critic")))
    assert state.critic() == CRITIQUE
    assert all(providers == [native_provider] for providers in critic._PROVIDER_CACHE.values())
    assert len(state.native.posts) == 1
    closed(state, 1)


@pytest.mark.parametrize("shape", ["direct", "llm", "copywriter", "full"])
def test_all_existing_critic_config_shapes_keep_selected_key_only_blocks(editorial, monkeypatch, shape):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    cfg = {auth.APPLICATION_MODE_CFG_KEY: "shared_fabric", "workload_profile": "site_batch"}
    if shape in {"llm", "copywriter", "full"}: cfg = {"critic": cfg}
    if shape in {"copywriter", "full"}: cfg = {"llm": cfg}
    if shape == "full": cfg = {"copywriter": cfg}
    state.critic_cfg = cfg
    before = copy.deepcopy(cfg)
    state.plans((200, response_for("critic")))
    assert state.critic() == CRITIQUE and cfg == before
    closed(state, 1)


@pytest.mark.parametrize("caller", ["critic", "review"])
@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_explicit_invalid_caller_mode_never_discovers_native_credentials(editorial, monkeypatch, caller, mode):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    if caller == "critic": state.critic_cfg = {auth.APPLICATION_MODE_CFG_KEY: mode}
    else: cfg_for(state, caller)[auth.APPLICATION_MODE_CFG_KEY] = mode
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["critic", "review"])
@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_denied_profile_is_preserved_before_credential_resolution(editorial, caller, profile):
    state = editorial
    cfg_for(state, caller)["workload_profile"] = profile
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["critic", "review"])
@pytest.mark.parametrize("mode", ["", "UNKNOWN", "missing_mode"])
def test_invalid_host_mode_never_falls_into_a_native_provider(editorial, monkeypatch, caller, mode):
    state = editorial
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, mode)
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []
    assert state.native.rows("leases") == []


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_revoked_capability_does_not_send_charge_or_succeed(editorial, caller):
    state = editorial
    state.manifest["capabilities"][0]["kill_state"] = "killed"
    state.save()
    assert not accepted(state, caller)[1]
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["critic", "review"])
@pytest.mark.parametrize("failure", ["malformed", "empty", "blank", "tools", "refusal",
                                     "truncated", "http", "mismatch", "unknown"])
def test_selected_failures_keep_advisory_fallback_without_retries(editorial, monkeypatch, caller, failure):
    state = editorial
    response = response_for(caller)
    choice = response["choices"][0]
    if failure == "malformed": choice["message"]["content"] = "Complete but not JSON."
    elif failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "  "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    if failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    state.plans((503 if failure == "http" else 200, response))
    result, useful = accepted(state, caller)
    assert not useful
    if caller == "critic":
        assert result["verdict"] == "pass" and result["reasons"] == [critic.UNAVAILABLE_REASON]
        stats = critic.critic_stats()
        assert stats["unavailable"] == 1 and stats["pass"] == stats["reject"] == 0
    else:
        assert result["mode"] == "mechanical" and result["batch"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    assert state.costs[0]["input_tokens"] == 11
    closed(state, 1)
    if failure == "unknown":
        assert state.native.rows("application_requests")[0]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    else:
        assert state.native.rows("application_requests")[0]["state"] == "terminal"
        assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_nullable_usage_stays_unknown_without_preventing_complete_text(editorial, caller):
    state = editorial
    response = response_for(caller)
    response["usage"]["prompt_tokens"] = None
    state.plans((200, response))
    assert accepted(state, caller)[1]
    assert len(state.native.posts) == 1 and state.costs == []
    usage = auth.fabric_usage(state.operations[0][1][0])
    assert usage["input_tokens"] is None and usage["output_tokens"] is None
    closed(state, 1)


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_receipt_only_repeat_cannot_become_a_second_review_or_ledger_row(editorial, monkeypatch, caller):
    state = editorial
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "c" * 32)
    state.plans((200, response_for(caller)))
    assert accepted(state, caller)[1]
    assert not accepted(state, caller)[1]
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_uncertain_close_does_not_erase_a_known_completed_result(editorial, monkeypatch, caller):
    state = editorial
    state.plans((200, response_for(caller)))
    monkeypatch.setattr(state.native.gateway, "close_application_turn", Mock(side_effect=OSError("close not committed")))
    assert accepted(state, caller)[1]
    assert len(state.native.posts) == len(state.costs) == 1
    provider = state.operations[0][1][0]
    assert not provider["_fabric_close"]["closed"]
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    assert auth.fabric_usage(provider)["input_tokens"] == 11
    closed(state, 1)


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_selected_branch_cannot_turn_native_if_host_selection_disappears(editorial, monkeypatch, caller):
    state = editorial
    original = auth.build_providers
    def build(cfg, **kwargs):
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert not accepted(state, caller)[1]
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("caller", ["critic", "review"])
def test_native_branch_cannot_hide_a_new_selected_binding(editorial, monkeypatch, caller):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(critic, "_model_id", lambda _cfg: REQUESTED)
    monkeypatch.setattr("lib.config.load", lambda: {"llm_models": {"absent_legacy_model": REQUESTED}})
    original = auth.build_providers
    def build(cfg, **kwargs):
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert not accepted(state, caller)[1]
    assert state.events == state.operations == state.closes == state.native.posts == state.costs == []
    assert critic._PROVIDER_CACHE == {}


def test_existing_feature_and_input_gates_do_not_bind(editorial, monkeypatch):
    state = editorial
    monkeypatch.setattr(auth, "begin_operation", Mock(side_effect=AssertionError("gated call bound")))
    state.critic_cfg["enabled"] = False
    assert state.critic()["reasons"] == ["critic_disabled"]
    state.critic_cfg["enabled"] = True
    monkeypatch.delenv("MARKETING_LLM_ENABLED")
    assert state.critic()["reasons"] == ["critic_off"] and state.review()["mode"] == "mechanical"
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    assert critic.cold_read_verdict(" ", {}, state.critic_cfg)["reasons"] == ["critic_skipped:empty"]
    cfg_for(state, "review")["enabled"] = False
    assert state.review()["mode"] == "mechanical"
    cfg_for(state, "review")["enabled"] = True
    assert review.review_posts_llm([], state.review_cfg["copywriter"]) == []
    assert review.review_batch([], state.review_cfg)["mode"] == "mechanical"
    assert state.events == state.closes == state.native.posts == state.costs == []


def test_unselected_critic_keeps_native_cache_order_and_transport_tuning(editorial, monkeypatch):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(critic, "_model_id", lambda _cfg: REQUESTED)
    builds = []
    provider = {"name": "anthropic", "model": REQUESTED, "client": object(), "cred": "fixture"}
    def build(cfg, **kwargs):
        builds.append((cfg, kwargs))
        return [provider]
    monkeypatch.setattr(auth, "build_providers", build)
    assert critic._providers(state.critic_cfg) is critic._providers(state.critic_cfg)
    assert len(builds) == 1
    cfg, kwargs = builds[0]
    assert cfg["provider_order"] == ["codex", "oauth", "anthropic", "deepseek"]
    assert cfg["codex_source_model"] == "gpt-5.6-terra" and cfg["codex_reasoning_effort"] == "medium"
    assert cfg["client_max_retries"] == 0 and cfg["client_timeout_s"] == 30.0
    assert cfg["codex_timeout_s"] == 150.0 and kwargs == {"opus_model": REQUESTED}
    assert "workload_profile" not in cfg
    assert state.events == state.closes == state.native.posts == []


def test_unselected_review_keeps_legacy_model_gate_and_request_contract(editorial, monkeypatch):
    state = editorial
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr("lib.config.load", lambda: {})
    build = Mock(side_effect=AssertionError("missing model must not build"))
    monkeypatch.setattr(auth, "build_providers", build)
    assert review.review_posts_llm(POSTS, state.review_cfg["copywriter"]) is None
    build.assert_not_called()
    monkeypatch.setattr("lib.config.load", lambda: {"llm_models": {"absent_legacy_model": REQUESTED}})
    calls, builds = [], []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(model=REQUESTED, stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(REVIEWS))], usage=None)
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider = {"name": "anthropic", "model": REQUESTED, "client": client, "cred": "fixture"}
    def build(cfg, **kwargs):
        builds.append((cfg, kwargs))
        return [provider]
    monkeypatch.setattr(auth, "build_providers", build)
    auth.clear_dead()
    result = review.review_posts_llm(POSTS, state.review_cfg["copywriter"])
    assert result[0] == {"verdict": "weak", "issues": CRITIQUE["reasons"]}
    assert builds[0][0]["provider_order"] == ["codex", "oauth", "anthropic", "deepseek"]
    assert builds[0][0]["codex_source_model"] == "gpt-5.6-sol"
    assert builds[0][1] == {"opus_model": REQUESTED}
    assert calls[0]["model"] == REQUESTED and calls[0]["max_tokens"] == 2000
    assert state.closes == state.native.posts == []
