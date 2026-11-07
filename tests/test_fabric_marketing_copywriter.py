"""Public writers through the real selected owner, native B/A and loopback HTTP.

Only qualification, credentials, upstream answers and editorial test inputs are
synthetic. Operations, parsing, accounting, SQLite admission and close are real.
"""
import copy
import json
import os
import re
import threading
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.marketing import copy_critic as critic, copywriter as cw
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
_COLD_READ = cw._cold_read
BODY = "$ARES dipped back to 122 and held. Buyers keep showing up there."
PASS = {"verdict": "pass", "reasons": []}


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unexpected-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


def answer(version, text=BODY):
    value = [{"headline": "", "body": text}] if version == "v1" else {"text": text}
    return packet(json.dumps(value))


def context():
    result = cw.build_context({"ticker": "ARES", "type": "chart", "account": "testdesk"},
        persona={"name": "Test", "voice_notes": "Emoji budget: 0", "example_lines": []},
        facts={"facts": [{"id": "poc_retest_hold", "text": "ARES dipped back to 121.66 and held.",
                          "salience": 7, "numbers": ["121.66"]}],
               "numbers_whitelist": ["121.66"]})
    result.update(type="chart", voice="authoritative desk", shape="one_liner", angle="level_watch")
    return result


@pytest.fixture
def writer(selected, monkeypatch):
    state = selected
    cw.reset_writer_stats()
    critic.reset_critic_stats()
    state.manifest["capabilities"][0]["allowed_lanes"] += ["marketing-copywriter", "marketing-critic"]
    state.save()
    # Synthetic grant explicitly admits the writer's six bounded steps. The
    # inherited fixture's two-step grant remains covered below as a refusal.
    state.native.grant["max_steps"] = 6
    state.native.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    monkeypatch.setattr(cw, "_v2_model_id", Mock(side_effect=AssertionError("native model prerequisite")))
    monkeypatch.setattr(critic, "_model_id", Mock(side_effect=AssertionError("native critic model prerequisite")))
    monkeypatch.setattr("lib.config.load", Mock(side_effect=AssertionError("native model map prerequisite")))
    monkeypatch.setattr(cw, "_codex_cards", lambda _accounts: {})
    monkeypatch.setattr(cw, "memory_recent_seed", lambda _accounts: {})
    monkeypatch.setattr(cw, "_cold_read", lambda *_args: dict(PASS))
    state.contexts = [context()]
    state.cfg = {"copy_laws": [], "llm": {"enabled": True, "model_key": "missing_legacy_model",
        "per_post_max_tokens": 400, "max_workers": 1, "critic": {"enabled": True}}}
    state.operations, state.closes = [], []
    original_begin, original_close = auth.begin_operation, _CLIENT.close

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(_CLIENT, "close", close)

    def plans(*responses):
        pending = list(responses)
        def upstream():
            assert pending, "unexpected extra provider request"
            state.native.response_status, state.native.response = pending.pop(0)
        state.native.on_upstream = upstream
    state.plans = plans
    state.run = lambda version="v2": (cw.write_posts_llm(state.contexts, state.cfg)
        if version == "v1" else cw.write_posts_llm_v2(state.contexts, state.cfg, root=state.root))
    yield state
    cw.reset_writer_stats()
    critic.reset_critic_stats()


def closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def useful(result, version="v2"):
    return bool(result) and result[0]["mode"] in ("llm", "llm_repair", "llm_fallback")


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_public_writer_uses_selected_model_without_legacy_model_map(writer, monkeypatch, version):
    state = writer
    if version == "v1":
        monkeypatch.setattr(cw, "validate_copy", lambda *_args, **_kwargs: [])
    state.plans((200, answer(version)))
    result = state.run(version)
    assert useful(result, version), result
    assert result[0]["mode"] == "llm" and result[0]["body"] == BODY
    assert len(state.native.posts) == len(state.native.rows("leases")) == len(state.costs) == 1
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == (6000 if version == "v1" else 400)
    assert state.costs[0]["model"] == MODEL and state.costs[0]["input_tokens"] == 11
    assert state.costs[0]["lane"] == "marketing-copywriter"
    assert state.operations[0][1][0]["client"]._client._timeout == 90.0
    assert state.native.rows("leases")[0]["state"] == "released"
    closed(state)


def test_v1_preserves_batch_order_and_per_post_deterministic_fallback(writer, monkeypatch):
    state = writer
    state.contexts *= 2
    monkeypatch.setattr(cw, "validate_copy", lambda hl, *_a, **_kw: ["fixture_invalid"] if hl == "Bad" else [])
    monkeypatch.setattr(cw, "write_posts_deterministic", lambda *_a, **_kw:
        [{"headline": "Fallback one", "body": "First"}, {"headline": "Fallback two", "body": "Second"}])
    outputs = [{"headline": "Good", "body": BODY}, {"headline": "Bad", "body": "Unsupported draft"}]
    state.plans((200, packet(json.dumps(outputs))))
    result = state.run("v1")
    assert [post["mode"] for post in result] == ["llm", "llm_fallback"]
    assert result[0]["headline"] == "Good" and result[1]["headline"] == "Fallback two"
    assert len(state.native.posts) == 1
    closed(state)


@pytest.mark.parametrize("malformed", ["not JSON", "{}", "[]", '[{"body":"one"},{"body":"two"}]'])
def test_v1_bad_batch_shape_never_reasks(writer, malformed):
    writer.plans((200, packet(malformed)))
    assert writer.run("v1") is None
    assert len(writer.native.posts) == len(writer.costs) == 1
    closed(writer)


@pytest.mark.parametrize("format_repairs", [False, True])
def test_v2_combined_validator_and_critic_repairs_keep_one_operation(writer, monkeypatch, format_repairs):
    state = writer
    checks, critiques = [], []
    def validate(*args, **kwargs):
        checks.append(args[0])
        return ["fixture_validator_repair"] if len(checks) == 1 else []
    def critique(*args):
        critiques.append(args[0])
        return {"verdict": "reject", "reasons": ["fixture_critic_repair"]} if len(critiques) == 1 else dict(PASS)
    monkeypatch.setattr(cw, "validate_copy_v2", validate)
    monkeypatch.setattr(cw, "_cold_read", critique)
    responses = []
    for _ in range(3):
        if format_repairs: responses.append((200, packet("A complete answer outside the contracted object.")))
        responses.append((200, answer("v2")))
    state.plans(*responses)
    result = state.run()
    assert result[0]["mode"] == "llm_repair" and result[0]["text"] == BODY
    expected = 6 if format_repairs else 3
    rows = state.native.rows("application_requests")
    assert len(rows) == len(state.native.posts) == len(state.costs) == expected
    assert len({row["turn_id"] for row in rows}) == len(state.native.rows("leases")) == 1
    turn = rows[0]["turn_id"]
    assert [row["request_id"] for row in rows] == [f"{turn}:brain:{i}" for i in range(expected)]
    assert len({post[2] for post in state.native.posts}) == 1
    requests = [json.loads(post[1]) for post in state.native.posts]
    assert all(req["model"] == MODEL and req["max_tokens"] == 400 for req in requests)
    if format_repairs:
        assert all(cw._OUTPUT_SHAPE_REMINDER in requests[i]["messages"][-1]["content"] for i in (1, 3, 5))
    stats = cw.writer_stats()
    assert stats["repairs"] == 2 and stats["provider_retries"] == stats["provider_failovers"] == 0
    assert stats["unreadable_reasks"] == stats["provider_recovered"] == (3 if format_repairs else 0)
    assert sum(cost["input_tokens"] for cost in state.costs) == expected * 11
    closed(state)


def test_v2_only_one_format_reask_per_editorial_turn(writer):
    writer.plans((200, packet("Complete but not the contracted object.")),
                 (200, packet("Still no contracted object.")))
    result = writer.run()
    assert result[0]["mode"] == "dropped" and result[0]["stage"] == "provider"
    assert result[0]["reasons"][0].startswith("unreadable_reply:fabric")
    assert len(writer.native.posts) == len(writer.costs) == 2
    stats = cw.writer_stats()
    assert stats["unreadable_replies"] == 2 and stats["unreadable_reasks"] == 1
    assert stats["provider_retries"] == stats["provider_failovers"] == 0
    closed(writer)


def test_narrower_owner_step_grant_stops_repairs_without_rebinding(writer, monkeypatch):
    writer.native.grant["max_steps"] = 2
    writer.native.save()
    calls = []
    def validate(*args, **kwargs):
        calls.append(args[0])
        return ["validator_repair"] if len(calls) == 1 else []
    monkeypatch.setattr(cw, "validate_copy_v2", validate)
    monkeypatch.setattr(cw, "_cold_read", lambda *_a: {"verdict": "reject", "reasons": ["critic_repair"]})
    writer.plans((200, answer("v2")), (200, answer("v2")))
    assert not useful(writer.run())
    assert len(writer.native.posts) == len(writer.costs) == 2
    assert len(writer.native.rows("leases")) == 1
    closed(writer)


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
def test_terminal_or_uncertain_fault_never_enters_native_recovery(writer, monkeypatch, version, failure):
    state = writer
    response = answer(version)
    choice = response["choices"][0]
    if failure == "empty": choice["message"]["content"] = ""
    elif failure == "blank": choice["message"]["content"] = "   "
    elif failure == "tools": choice.update(packet(None, tool=True)["choices"][0])
    elif failure == "refusal": choice["finish_reason"] = "content_filter"
    elif failure == "truncated": choice["finish_reason"] = "length"
    elif failure == "mismatch": response["model"] = "different-observed-model"
    if failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("before commit")))
    for method in ("empty_text_retry_plan", "providers_after", "first_usable"):
        monkeypatch.setattr(auth, method, Mock(side_effect=AssertionError("legacy recovery reached")))
    state.plans((503 if failure == "http" else 200, response))
    assert not useful(state.run(version), version)
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    assert state.costs[0]["input_tokens"] == 11
    assert cw.writer_stats()["provider_retries"] == cw.writer_stats()["provider_failovers"] == 0
    if failure == "unknown":
        assert state.native.rows("application_requests")[0]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    else:
        assert state.native.rows("application_requests")[0]["state"] == "terminal"
        assert state.native.rows("leases")[0]["state"] == "released"
    closed(state)


def test_complete_format_miss_then_unknown_keeps_known_usage_and_original_hold(writer, monkeypatch):
    state = writer
    original = state.native.gateway.complete_application
    count = 0
    def complete(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2: raise OSError("second completion not committed")
        return original(*args, **kwargs)
    monkeypatch.setattr(state.native.gateway, "complete_application", complete)
    state.plans((200, packet("Complete but not an object.")), (200, answer("v2")))
    assert not useful(state.run())
    assert len(state.native.posts) == len(state.costs) == 2
    assert len(state.native.rows("leases")) == 1
    assert [row["state"] for row in state.native.rows("application_requests")] == ["terminal", "unknown"]
    usage = auth.fabric_usage(state.operations[0][1][0])
    assert usage["input_tokens"] is None and usage["completed_input_tokens"] == 22
    assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    closed(state)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_nullable_usage_does_not_become_zero_or_invalidate_complete_copy(writer, monkeypatch, version):
    state = writer
    if version == "v1": monkeypatch.setattr(cw, "validate_copy", lambda *_a, **_k: [])
    response = answer(version)
    response["usage"]["prompt_tokens"] = None
    state.plans((200, response))
    assert useful(state.run(version), version)
    assert len(state.native.posts) == 1 and state.costs == []
    usage = auth.fabric_usage(state.operations[0][1][0])
    assert usage["input_tokens"] is None and usage["output_tokens"] is None
    closed(state)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_receipt_only_repeat_is_not_another_draft_or_usage_row(writer, monkeypatch, version):
    state = writer
    if version == "v1": monkeypatch.setattr(cw, "validate_copy", lambda *_a, **_k: [])
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "e" * 32)
    state.plans((200, answer(version)))
    assert useful(state.run(version), version)
    assert not useful(state.run(version), version)
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    closed(state, 2)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_uncertain_close_preserves_known_completed_copy(writer, monkeypatch, version):
    state = writer
    if version == "v1": monkeypatch.setattr(cw, "validate_copy", lambda *_a, **_k: [])
    monkeypatch.setattr(state.native.gateway, "close_application_turn", Mock(side_effect=OSError("close uncommitted")))
    state.plans((200, answer(version)))
    assert useful(state.run(version), version)
    assert len(state.native.posts) == len(state.costs) == 1
    assert not state.operations[0][1][0]["_fabric_close"]["closed"]
    assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
    closed(state)


def test_concurrent_items_have_distinct_clients_turns_and_account_custody(writer, monkeypatch):
    state = writer
    state.contexts *= 2
    state.cfg["llm"]["max_workers"] = 2
    barrier = threading.Barrier(2)
    state.native.response = answer("v2")
    state.native.on_upstream = lambda: barrier.wait(timeout=3)
    # This test isolates operation concurrency; the next test retains the
    # actual sequential duplicate gates for identical completed drafts.
    monkeypatch.setattr(cw, "batch_stem_violations", lambda *_a: [])
    monkeypatch.setattr(cw, "batch_body_duplicate_violations", lambda *_a: [])
    result = state.run()
    assert [post["mode"] for post in result] == ["llm", "llm"]
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 2
    rows = state.native.rows("application_requests")
    assert len({row["turn_id"] for row in rows}) == 2
    assert len({id(providers[0]["client"]) for _, providers in state.operations}) == 2
    assert len(set(state.closes)) == 2
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    closed(state, 2)


def test_sequential_collision_gate_preserves_input_order_and_truthful_counters(writer):
    writer.contexts *= 2
    writer.plans((200, answer("v2")), (200, answer("v2")))
    result = writer.run()
    assert [post["mode"] for post in result] == ["llm", "dropped"]
    assert result[1]["stage"] == "validate"
    assert cw.writer_stats()["llm"] == 1 and cw.writer_stats()["dropped_validate"] == 1
    assert len(writer.native.posts) == 2
    closed(writer, 2)


def test_poisoned_item_does_not_bind_or_poison_the_next_item(writer, monkeypatch):
    state = writer
    state.contexts = [{**context(), "fixture_poison": True}, context()]
    original = cw._v2_item_payload
    def payload(ctx, **kwargs):
        if ctx.get("fixture_poison"): raise ValueError("poisoned input")
        return original(ctx, **kwargs)
    monkeypatch.setattr(cw, "_v2_item_payload", payload)
    state.plans((200, answer("v2")))
    result = state.run()
    assert [post["mode"] for post in result] == ["dropped", "llm"]
    assert len(state.native.posts) == len(state.native.rows("leases")) == 1
    closed(state)


def test_writer_and_real_critic_use_separate_lanes_and_operations(writer, monkeypatch):
    state = writer
    monkeypatch.setattr(cw, "_cold_read", _COLD_READ)
    state.plans((200, answer("v2")), (200, packet(json.dumps(PASS))))
    result = state.run()
    assert result[0]["mode"] == "llm" and result[0]["critic"] == PASS
    assert {cost["lane"] for cost in state.costs} == {"marketing-copywriter", "marketing-critic"}
    assert len({row["turn_id"] for row in state.native.rows("application_requests")}) == 2
    assert state.closes[0] != state.operations[0][0].operation_id  # critic closes before writer
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    closed(state, 2)


def test_real_critic_unavailable_keeps_existing_deterministic_acceptance(writer, monkeypatch):
    state = writer
    monkeypatch.setattr(cw, "_cold_read", _COLD_READ)
    state.plans((200, answer("v2")), (503, packet("Known critic error.")))
    result = state.run()
    assert result[0]["mode"] == "llm"
    assert result[0]["critic"]["verdict"] == "pass"
    assert result[0]["critic"]["reasons"] == [critic.UNAVAILABLE_REASON]
    assert result[0]["critic"]["detail"] == "call:FabricProviderError"
    assert len(state.native.posts) == len(state.costs) == 2
    closed(state, 2)


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_explicit_denied_profile_refuses_before_credential_resolution(writer, version, profile):
    writer.cfg["llm"]["workload_profile"] = profile
    assert not useful(writer.run(version), version)
    assert writer.events == writer.operations == writer.closes == writer.native.posts == writer.costs == []


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("mode", [None, "", "missing_mode"])
def test_invalid_explicit_mode_never_discovers_native_credentials(writer, monkeypatch, version, mode):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    writer.cfg["llm"][auth.APPLICATION_MODE_CFG_KEY] = mode
    assert not useful(writer.run(version), version)
    assert writer.events == writer.closes == writer.native.posts == writer.costs == []


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("mode", ["", "UNKNOWN", "missing_mode"])
def test_invalid_host_mode_never_falls_through_to_native(writer, monkeypatch, version, mode):
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, mode)
    assert not useful(writer.run(version), version)
    assert writer.events == writer.closes == writer.native.posts == writer.costs == []


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_selected_mode_disappearing_before_build_never_changes_family(writer, monkeypatch, version):
    original = auth.build_providers
    def build(cfg, **kwargs):
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert not useful(writer.run(version), version)
    assert writer.events == writer.operations == writer.closes == writer.native.posts == writer.costs == []


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_late_selected_mode_cannot_execute_under_native_branch(writer, monkeypatch, version):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(cw, "_v2_model_id", lambda _cfg: "native-model")
    monkeypatch.setattr("lib.config.load", lambda: {"llm_models": {"missing_legacy_model": "native-model"}})
    original = auth.build_providers
    def build(cfg, **kwargs):
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return original(cfg, **kwargs)
    monkeypatch.setattr(auth, "build_providers", build)
    assert not useful(writer.run(version), version)
    assert writer.events == writer.operations == writer.closes == writer.native.posts == writer.costs == []


def test_each_item_revalidates_the_inert_recipe_before_binding(writer, monkeypatch):
    writer.contexts *= 2
    original = auth.begin_operation
    binds = 0
    def begin(*args, **kwargs):
        nonlocal binds
        binds += 1
        if binds == 2: monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
        return original(*args, **kwargs)
    monkeypatch.setattr(auth, "begin_operation", begin)
    writer.plans((200, answer("v2")))
    result = writer.run()
    assert [post["mode"] for post in result] == ["llm", "dropped"]
    assert len(writer.native.posts) == 1
    closed(writer)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_feature_env_empty_and_capped_input_gates_do_not_bind(writer, monkeypatch, version):
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("gated provider build")))
    writer.contexts = []
    assert writer.run(version) == []
    writer.contexts = [context()]
    if version == "v1":
        writer.cfg["llm"]["max_posts_per_run"] = 0
        assert writer.run(version) == []
        writer.cfg["llm"]["max_posts_per_run"] = 1
    writer.cfg["llm"]["enabled"] = False
    assert not useful(writer.run(version), version)
    writer.cfg["llm"]["enabled"] = True
    monkeypatch.delenv("MARKETING_LLM_ENABLED")
    assert not useful(writer.run(version), version)
    assert writer.events == writer.operations == writer.native.posts == writer.costs == []


def test_selected_mute_and_fault_annotations_do_not_claim_keys_retry_or_failover(writer, monkeypatch, capsys):
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    assert not useful(writer.run())
    output = capsys.readouterr().out
    assert "marketing_copywriter_mute" in output
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in output and "DEEPSEEK_API_KEY" not in output
    results = [{"mode": "dropped", "stage": "provider", "reasons": ["provider_error:FabricProviderError"]}] * 3
    cw._provider_fault_alarm(results, results, fabric_selected=True)
    output = capsys.readouterr().out
    assert output.startswith("::error title=marketing_copy_provider_faults::")
    assert "do not trigger retries or provider failover" in output
    assert "already spent its same-provider retry" not in output
