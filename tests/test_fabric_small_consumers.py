"""Public research callers through the actual Macro client and paired native A/B.

Credentials, qualification, source documents and provider responses are synthetic.
The real operation, usage, close, selector and persistence owners remain in use.
"""
import copy
import json
import os
import re
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.press import research_veto as veto
from engine.research_intelligence import extractor, selection, vault_head
from engine.research_vault.r2_store import LocalStore
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_research_intelligence_selection_contract import DOC, BODY, payload
from tests.test_research_intelligence_vault_head import (
    BODY as VAULT_BODY, _candidate, _provider, _seed_pdf,
)


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
REQUESTED = "requested-claude-model"


def packet(text, *, model=MODEL, finish="stop", tool=False):
    message = {"role": "assistant", "content": text}
    if tool:
        message["tool_calls"] = [{"id": "unsolicited-1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
        finish = "tool_calls"
    return {"model": model, "choices": [{"index": 0, "message": message,
        "finish_reason": finish}], "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


def selector_packet(request):
    user = request["messages"][-1]["content"]
    identity = json.loads(user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\n", 1)[0])
    catalog = json.loads(user.split("EVIDENCE CATALOG:\n", 1)[1].split("\n\n", 1)[0])
    return packet(json.dumps(payload(identity, catalog)))


def rows(*ids):
    return {"rows": [{"report_id": rid, "status": "ranked", "title": rid,
                       "institution": "Fixture", "w_score": 0.8} for rid in ids]}


@pytest.fixture
def research(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"] += [
        "press-research-triage-veto", "research-intelligence"]
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setattr(veto, "_model_id", lambda _key: REQUESTED)
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
            assert pending, "unexpected extra provider request"
            status, response = pending.pop(0)
            if callable(response):
                response = response(json.loads(state.native.posts[-1][1]))
            state.native.response_status, state.native.response = status, response

        state.native.on_upstream = upstream

    state.plans = plans
    state.veto = lambda *ids, **cfg: veto.run(rows(*(ids or ("a",))),
        cfg={"veto": {"enabled": True, "head_size": 20, "batch_size": 1, **cfg}})
    state.extract = lambda **kw: extractor.analyze_document(
        kw.pop("document", DOC), kw.pop("body", BODY), model_id=REQUESTED, **kw)
    return state


def assert_closed(state, count):
    assert len(state.closes) == len(state.operations) == count
    assert all(re.fullmatch(r"app:[0-9a-f]{32}", value) for value in state.closes)
    assert all(operation.providers == [] for operation, _providers in state.operations)
    assert all(providers[0]["_fabric_closed"] is True for _, providers in state.operations)


def test_public_veto_batches_use_actual_model_original_usage_and_demote_allowlist(research):
    state = research
    first = [{"id": "a", "demote": True, "reason": "thin"},
             {"id": "b", "demote": True, "reason": "thin"},
             {"id": "invented", "demote": True, "reason": "thin"}]
    second = [{"id": "b", "demote": True, "reason": "excellent"}]
    state.plans((200, packet(json.dumps(first))), (200, packet(json.dumps(second))))
    original = rows("a", "b")
    original["rows"].append({"report_id": "junk", "status": "garbage_dropped"})
    snapshot = copy.deepcopy(original)
    result = veto.run(original, cfg={"veto": {"enabled": True, "batch_size": 1}})
    assert original == snapshot
    assert result["state"] == "ok" and result["batches"] == 2 and result["failed_batches"] == 0
    assert result["model"] == REQUESTED
    assert result["vetoes"] == {"a": {"reason": "thin", "model": MODEL, "provider": "fabric"}}
    assert len(state.native.posts) == len(state.costs) == 2
    assert len(set(state.closes)) == 2
    assert_closed(state, 2)
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    assert all(row["lane"] == "press-research-triage-veto" and row["stage"] == "press_research_veto"
               and row["model"] == MODEL and row["input_tokens"] == 11 for row in state.costs)
    assert all("junk" not in post[1].decode() for post in state.native.posts)


def test_public_documents_preserve_requested_and_observed_models_and_grounding(research):
    state = research
    state.plans((200, selector_packet), (200, selector_packet))
    results = [state.extract(document={**DOC, "id": "document-" + suffix}) for suffix in ("a", "b")]
    assert all(result["state"] == "ok" and result["rio"] for result in results)
    assert all(result["requested_model"] == REQUESTED and result["model"] == MODEL
               and result["provider"] == "fabric" for result in results)
    assert len(set(state.closes)) == 2
    assert_closed(state, 2)
    assert len(state.native.posts) == len(state.costs) == 2
    assert all(row["lane"] == "research-intelligence" and row["stage"] == "research_intelligence"
               and row["model"] == MODEL and row["input_tokens"] == 11 for row in state.costs)


@pytest.mark.parametrize("caller", ["veto", "extract"])
@pytest.mark.parametrize("failure", ["empty", "blank", "tools", "refusal", "truncated", "http", "mismatch", "unknown"])
def test_public_selected_failure_never_retries_or_accepts_business_output(research, monkeypatch, caller, failure):
    state = research
    response = selector_packet if caller == "extract" else packet('[{"id":"a","reason":"thin"}]')

    def bad(request):
        value = response(request) if callable(response) else copy.deepcopy(response)
        choice = value["choices"][0]
        if failure == "empty": choice["message"]["content"] = ""
        elif failure == "blank": choice["message"]["content"] = "  "
        elif failure == "tools":
            choice.update(packet(None, tool=True)["choices"][0])
        elif failure == "refusal": choice["finish_reason"] = "content_filter"
        elif failure == "truncated": choice["finish_reason"] = "length"
        elif failure == "mismatch": value["model"] = "different-observed-model"
        return value

    state.plans((503 if failure == "http" else 200, bad))
    if failure == "unknown":
        monkeypatch.setattr(state.native.gateway, "complete_application",
                            Mock(side_effect=OSError("fixture before commit")))
    result = getattr(state, caller)()
    assert result["state"] == "call_failed"
    assert (result["vetoes"] == {} and result["failed_batches"] == 1) if caller == "veto" else result["rio"] is None
    assert len(state.native.posts) == 1
    assert_closed(state, 1)
    assert len(state.costs) == 1 and state.costs[0]["input_tokens"] == 11
    assert state.costs[0]["model"] == ("different-observed-model" if failure == "mismatch" else MODEL)
    if failure == "unknown":
        assert state.native.rows("application_requests")[0]["state"] == "unknown"
        assert state.native.rows("leases")[0]["state"] in {"held", "rented"}
        retained = state.operations[0][1][0]
        assert auth.fabric_usage(retained)["input_tokens"] is None
        assert not retained["_fabric_close"]["closed"]
    else:
        assert state.native.rows("application_requests")[0]["state"] == "terminal"
        assert state.native.rows("leases")[0]["state"] == "released"


@pytest.mark.parametrize("caller", ["veto", "extract"])
def test_unknown_usage_is_not_zero_filled(research, caller):
    state = research
    def incomplete(request):
        value = selector_packet(request) if caller == "extract" else packet("[]")
        value["usage"]["prompt_tokens"] = None
        return value
    state.plans((200, incomplete))
    result = getattr(state, caller)()
    assert result["state"] == "ok"
    assert state.costs == []
    assert len(state.native.posts) == 1
    assert_closed(state, 1)
    assert auth.fabric_usage(state.operations[0][1][0])["input_tokens"] is None


@pytest.mark.parametrize("caller", ["veto", "extract"])
def test_receipt_only_recovery_never_becomes_a_second_answer(research, monkeypatch, caller):
    state = research
    monkeypatch.setattr(auth.secrets, "token_hex", lambda _length: "a" * 32)
    state.plans((200, selector_packet if caller == "extract" else packet("[]")))
    assert getattr(state, caller)()["state"] == "ok"
    result = getattr(state, caller)()
    assert result["state"] == "call_failed"
    assert len(state.native.posts) == len(state.costs) == len(state.native.rows("leases")) == 1
    assert_closed(state, 2)


@pytest.mark.parametrize("caller", ["veto", "extract"])
@pytest.mark.parametrize("mode", ["", "UNKNOWN", "missing_mode"])
def test_invalid_host_mode_fails_before_credentials(research, monkeypatch, caller, mode):
    state = research
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, mode)
    result = getattr(state, caller)()
    assert result["state"] == "call_failed"
    assert state.events == state.closes == state.native.posts == state.costs == []
    assert state.native.rows("leases") == []


@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_veto_explicit_profile_is_preserved_and_denied_before_credentials(research, profile):
    state = research
    result = state.veto(workload_profile=profile)
    assert result["state"] == "call_failed"
    assert state.events == state.closes == state.native.posts == state.costs == []


@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_caller_selection_cannot_discover_legacy_credentials(research, monkeypatch, mode):
    state = research
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    result = state.veto(**{auth.APPLICATION_MODE_CFG_KEY: mode})
    assert result["state"] == "call_failed"
    assert state.events == state.closes == state.native.posts == state.costs == []


def test_failed_batch_keeps_ranking_then_next_independent_batch_can_complete(research):
    state = research
    state.plans((503, packet("unavailable")), (200, packet('[{"id":"b","reason":"duplicate"}]')))
    result = state.veto("a", "b")
    assert result["state"] == "ok" and result["batches"] == 2 and result["failed_batches"] == 1
    assert result["vetoes"] == {"b": {"reason": "duplicate", "model": MODEL, "provider": "fabric"}}
    assert len(state.native.posts) == len(state.costs) == 2
    assert len(set(state.closes)) == 2
    assert_closed(state, 2)


def test_extractor_preflight_spends_nothing_and_bad_selection_cannot_create_rio(research, monkeypatch):
    state = research
    assert state.extract(body="")["state"] == "selection_unavailable"
    with monkeypatch.context() as context:
        context.setattr(selection, "MAX_VERIFIER_WORK_BYTES", 1)
        assert state.extract()["state"] == "selection_unavailable"
    assert state.events == state.native.posts == state.costs == state.closes == []
    state.plans((200, packet('{"invented_claim":"unsupported"}')))
    result = state.extract()
    assert result["state"] == "invalid_model_output" and result["rio"] is None
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state, 1)


def test_warm_vault_receipt_keeps_historical_provenance_without_new_binding(research, tmp_path, monkeypatch):
    state = research
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    state.plans((200, selector_packet))
    kwargs = {"store": store, "model_id": REQUESTED,
              "text_provider": _provider(lambda _pdf: VAULT_BODY)}
    first = vault_head.deep_read_candidate(_candidate(), **kwargs)
    assert first["state"] == "persisted"
    assert first["model"] == MODEL and first["requested_model"] == REQUESTED
    state.events.clear()
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "now_unqualified")
    second = vault_head.deep_read_candidate(_candidate(), **kwargs)
    assert second["state"] == "already_current"
    assert second["artifact_sha256"] == first["artifact_sha256"]
    assert second["provider"] == "fabric" and second["model"] == MODEL
    assert state.events == []
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state, 1)
