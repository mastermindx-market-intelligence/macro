"""Retain request-specific server context in the canonical Brain message store.

These receipts describe context resolution, not a complete research artifact or
model input census. No source bytes, extra store, provider call or read exposure.
"""
from __future__ import annotations

import copy
import json

import pytest

from engine.intelligence_workspace import context_compiler as cc
from engine.neuralweb import brain_gateway as gw


def receipt(request_id="request-one"):
    return cc.compile_receipt(cc.compile_envelope(
        "AAPL price", {"symbol": "MSFT"}, request_id=request_id,
    ))


def test_context_receipt_is_detached_and_keeps_system_event_metadata():
    context = receipt()
    original = copy.deepcopy(context)
    memory_meta = {"tools": ["get_quote"], "symbols": ["AAPL"]}
    result = gw._with_retained_context(memory_meta, context)
    assert result["tools"] == memory_meta["tools"]
    record = result["retained_context"]
    assert record == {
        "schema": "brain.retained_context.v1",
        "scope": "context_resolution_only",
        "status": "retained",
        "used_inputs_status": "not_recorded",
        "receipt": original,
    }
    context["effective_context"]["entities"].clear()
    assert record["receipt"] == original
    assert "retained_context" not in memory_meta


def test_same_context_revision_never_deduplicates_distinct_requests():
    a = gw._with_retained_context({}, receipt("request-a"))
    b = gw._with_retained_context({}, receipt("request-b"))
    assert a["retained_context"]["receipt"]["request_id"] == "request-a"
    assert b["retained_context"]["receipt"]["request_id"] == "request-b"


@pytest.mark.parametrize("invalid", [None, [], {}, {"schema": "future"},
    {"schema": "ai_context_receipt.v1", "request_id": ""}])
def test_invalid_receipt_never_loses_existing_assistant_metadata(invalid):
    result = gw._with_retained_context({"symbols": ["AAPL"]}, invalid)
    assert result["symbols"] == ["AAPL"]
    assert result["retained_context"]["status"] == "unavailable"
    assert "receipt" not in result["retained_context"]


def test_oversized_receipt_is_explicitly_unavailable_and_never_truncated():
    context = receipt()
    context["test_padding"] = "界" * 65536
    result = gw._with_retained_context({}, context)
    assert result["retained_context"]["status"] == "unavailable"
    assert result["retained_context"]["reason"] == "receipt_too_large"
    assert "receipt" not in result["retained_context"]
    assert len(json.dumps(result).encode()) < 1024


def test_unserializable_receipt_cannot_break_answer_persistence():
    context = receipt()
    context["cycle"] = context
    result = gw._with_retained_context({"tools": []}, context)
    assert result["retained_context"]["status"] == "unavailable"
    assert result["retained_context"]["reason"] == "invalid_receipt"


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("route", ["deep", "native", "instant"])
def test_gateway_persists_the_exact_returned_server_receipt(tmp_path, monkeypatch, stream, route):
    # Reuse the incumbent provider protocol fixture; no real model/network call.
    from tests.test_brain_gateway import _MockBlock, _MockClient, _MockResponse, _MockUsage
    response = _MockResponse([_MockBlock("text", "A retained answer.")], "end_turn",
                             usage=_MockUsage(input_tokens=3, output_tokens=4))
    monkeypatch.setattr(gw, "_brain_quota_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gw, "_build_lane_providers", lambda *a: [{"client": _MockClient([response]), "model": "test-model"}])
    monkeypatch.setattr(gw, "_resolve_tier", lambda *a, **k: {"tier": "pro", "status": "active", "current_period_end": None})
    monkeypatch.setattr(gw, "_ensure_thread", lambda *a, **k: "11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(gw, "_load_thread_history", lambda *a: [])
    monkeypatch.setattr(gw, "_log_brain_response", lambda **k: None)
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **k: True)
    message = "Explain this business"
    if route == "native":
        from tests.test_brain_instant_lane import _gateway_native_execution
        message = "INOD Stage"
        monkeypatch.setattr(gw._native_facts, "execute_native_fact_plan", lambda *a, **k: _gateway_native_execution())
        def no_provider(*a, **k):
            raise AssertionError("native answer must work with no model provider")
        monkeypatch.setattr(gw, "_build_lane_providers", no_provider)
    elif route == "instant":
        from tests.test_brain_instant_lane import _Client, _GOOD_QUOTE
        message = "AAPL price"
        monkeypatch.setattr(gw._native_facts, "plan_native_facts", lambda *a, **k: None)
        monkeypatch.setattr(gw, "_build_lane_providers", lambda *a: [{"client": _Client(), "model": "test-model"}])
        monkeypatch.setattr(gw, "_tool_get_quote", lambda *a, **k: dict(_GOOD_QUOTE))
        monkeypatch.setattr(gw, "_instant_tape_line", lambda *a: "")
    writes = []
    monkeypatch.setattr(gw, "_sb_post", lambda path, payload: writes.append((path, copy.deepcopy(payload))) or [payload])
    if stream:
        events = [json.loads(x[5:]) for x in gw.chat_stream(
            message, "test-owner", root=tmp_path,
        ) if x.startswith("data:")]
        expected = next({k: v for k, v in e.items() if k != "type"}
                        for e in events if e["type"] == "context_receipt")
        expected_reply = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    else:
        result = gw.chat(message, "test-owner", root=tmp_path)
        expected = result["context_receipt"]
        expected_reply = result["reply"]
    assistant = [payload for path, payload in writes
                 if path == "brain_messages" and payload["role"] == "assistant"]
    assert len(assistant) == 1
    assert assistant[0]["meta"]["retained_context"]["receipt"] == expected
    assert expected_reply
    assert assistant[0]["content"] == expected_reply
    assert all("retained_context" not in p["meta"] for path, p in writes
               if path == "brain_messages" and p["role"] == "user")
