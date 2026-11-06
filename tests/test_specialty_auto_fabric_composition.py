"""AUTO specialty cache custody through actual owner/client/native HTTP/SQLite.

Uses explicit synthetic site_batch service authority. Fixed historical fixtures
and their grant/source pins remain separate.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import threading
from unittest.mock import Mock, patch

import pytest
from engine import catalyst_tone as tone, llm_auth as auth
from engine import provider_production_modes as owner
from lib import config
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL, _fixed  # noqa: F401
from tests.test_fabric_workload_auto_composition import auto_workloads  # noqa: F401

SOURCE = "The board approved the merger. Rates remain unchanged."


def packet():
    value = {"tone_score": 0, "guidance_direction": "on_hold", "risk_delta": 0,
        "shock_reversible": "unknown", "confidence": "high",
        "evidence": [{"field": "guidance_direction", "quote_span": "Rates remain unchanged."}]}
    return _fixed.packet(json.dumps(value))


@pytest.fixture
def cached_auto(auto_workloads, monkeypatch):
    state = auto_workloads
    state.cfg = {"enabled": True, "max_tokens": 128, "llm_min_confidence": "low"}
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "load", lambda: {"llm_models": {"extraction": "legacy-configured"}})
    monkeypatch.setattr(tone, "_cfg", lambda: state.cfg)
    monkeypatch.setattr(tone, "_client", Mock(side_effect=AssertionError("legacy")))
    state.native.response = packet()
    state.logical = {"task": "catalyst-tone", "kind": "macro", "source_id": "document-1"}
    state.cache = tone._fabric_cache_path(state.root / "data/catalyst/reply_cache", state.logical)
    return state


def call(**kwargs):
    return tone.digest_document(kwargs.pop("source", SOURCE), doc_id="document-1", **kwargs)


def saved(state):
    return json.loads(state.cache.read_text())


def assert_once(state):
    assert len(state.native.posts) == len(state.native.rows("application_requests")) == 1
    assert len(state.costs) == len(state.closes) == 1


def test_public_auto_claim_precedes_provider_and_warm_result_retains_original_receipt(cached_auto):
    state = cached_auto
    def observed():
        row = saved(state)["entries"][0]
        assert row["state"] == "pending" and row["receipt"] is None
        assert row["request"]["request_id"] == row["operation_id"] + ":brain:0"
        assert row["inspection"]["requested_model"] is None
    state.native.on_upstream = observed
    first = call()
    assert first["model"] == MODEL and first["requested_model"] is None, first
    assert first["guidance_direction"] == "on_hold" and first["degraded_reason"] is None
    assert first["is_context_only"]
    row = saved(state)["entries"][0]
    assert row["schema"] == tone._AUTO_CACHE_ENTRY and row["state"] == "terminal"
    receipt = row["receipt"]
    assert receipt["requested_model"] is None and receipt["served_model"] == MODEL
    assert receipt["provider"] == "go" and receipt["close"]["closed"] is True
    assert receipt["application_observation"]["routing"]["request_digest"] == row["request"]["digest"]
    turn = state.native.rows("application_turns")[0]
    assert turn["principal_id"] == "macro_batch_fabric" and turn["workload"] == "site_batch"
    events = list(state.events)
    assert call() == first
    assert state.events == events
    assert_once(state)
    assert state.costs[0]["model"] == MODEL and state.costs[0]["cost_basis"] == "unknown"
    assert all(row["state"] == "released" for row in state.native.rows("leases"))


def change_identity(state, monkeypatch):
    ident = "native_fabric_macro_batch_auto_v1"
    changed = replace(owner._APPLICATION_FABRIC_TRANSPORTS[ident], cap_id="fabric:macro_batch_changed")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, ident, changed)
    state.records["macro_batch_fabric"]["cap_id"] = changed.cap_id
    state.save()


def test_completed_changed_inspection_creates_new_entry_without_relabeling_old(cached_auto, monkeypatch):
    state = cached_auto
    first = call()
    original = copy.deepcopy(saved(state)["entries"][0])
    change_identity(state, monkeypatch)
    second = call()
    assert first["model"] == second["model"] == MODEL and second["degraded_reason"] is None
    rows = saved(state)["entries"]
    assert rows[0] == original and rows[1]["input_digest"] != original["input_digest"]
    assert rows[1]["operation_id"] != original["operation_id"]
    assert rows[1]["inspection"] != original["inspection"]
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 2
    assert call() == second and len(state.native.posts) == 2


def test_pending_original_survives_changed_input_inspection_and_removed_selector(cached_auto, monkeypatch):
    state = cached_auto
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(call)
        try:
            assert state.native.arrived.wait(3)
            change_identity(state, monkeypatch)
            monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
            refused = call(source=SOURCE + " Later.", context="new context")
            assert refused["degraded_reason"] == "fabric_original_held"
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert pending.result(timeout=10)["model"] == MODEL
    assert_once(state)


def test_lost_original_close_ack_holds_known_result_and_never_replays(cached_auto, monkeypatch):
    state = cached_auto
    original = state.native.gateway.close_application_turn
    def close(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("synthetic lost original close acknowledgement")
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        first = call()
    assert first["degraded_reason"] == "fabric_close_unknown", first
    assert first["guidance_direction"] == "unknown"
    row = saved(state)["entries"][0]
    assert row["state"] == "held" and row["result"]["guidance_direction"] == "on_hold"
    assert row["receipt"]["served_model"] == MODEL
    assert row["receipt"]["application_observation"]["disposition"] == "terminal"
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert call(source=SOURCE + " New.")["degraded_reason"] == "fabric_original_held"
    assert_once(state)


def test_lost_settlement_retains_actual_observation_and_usage(cached_auto, monkeypatch):
    state = cached_auto
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("synthetic lost settlement")):
        result = call()
    assert result["degraded_reason"]
    row = saved(state)["entries"][0]
    assert row["state"] == "held"
    assert row["receipt"]["application_observation"]["serving_model"] == MODEL
    assert row["receipt"]["observed_usage"]["input_tokens"] == 11
    assert row["receipt"]["usage"]["completed_input_tokens"] == 11
    assert_once(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert call()["degraded_reason"] == "fabric_original_held"
    assert_once(state)


def test_malformed_route_keeps_known_usage_but_never_caches_or_attributes_pool(cached_auto, monkeypatch):
    state = cached_auto
    handler = state.native.server.RequestHandlerClass
    original = handler._application_routed_result
    def corrupt(handler, outcome):
        result = original(handler, outcome)
        body = json.loads(result.body)
        body["application"]["routing"]["protocol"] = []
        raw = json.dumps(body, separators=(",", ":")).encode()
        return replace(result, body=raw, delivery_digest=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(handler, "_application_routed_result", corrupt)
    assert call()["degraded_reason"]
    row = saved(state)["entries"][0]
    assert row["state"] == "held" and row["result"] is None
    assert row["receipt"]["application_observation"] is None
    assert row["receipt"]["provider"] == "unknown"
    assert row["receipt"]["observed_usage"]["serving_model"] == MODEL
    assert state.costs[0]["provider"] == "unknown" and state.costs[0]["input_tokens"] == 11
    assert_once(state)


@pytest.mark.parametrize("kind", ["served_mismatch", "partial_usage", "invalid_json", "unearned_quote"])
def test_unaccepted_or_partial_outputs_preserve_existing_document_rules(cached_auto, kind):
    state = cached_auto
    if kind == "served_mismatch":
        state.native.response["model"] = "other-observed"
    elif kind == "partial_usage":
        state.native.response["usage"] = {"prompt_tokens": 11}
    elif kind == "invalid_json":
        state.native.response["choices"][0]["message"]["content"] = "not JSON"
    else:
        value = json.loads(state.native.response["choices"][0]["message"]["content"])
        value["evidence"][0]["quote_span"] = "Unstated promise about interest rates."
        state.native.response["choices"][0]["message"]["content"] = json.dumps(value)
    result = call()
    row = saved(state)["entries"][0]
    if kind == "unearned_quote":
        assert result["guidance_direction"] == "unknown" and result["dropped_fields"]
        assert row["state"] == "terminal" and row["result"] is not None
    elif kind == "partial_usage":
        assert row["receipt"]["observed_usage"]["output_tokens"] is None
        assert row["receipt"]["usage"]["usage_state"] == "unknown"
        assert row["receipt"]["usage"]["completed_input_tokens"] == 0
        assert not state.costs
    else:
        assert result["degraded_reason"] and row["result"] is None
    call()
    assert len(state.native.posts) == len(state.closes) == 1


@pytest.mark.parametrize("corruption", ["missing_schema", "request_commitment", "routed_commitment",
    "foreign_pool", "response_identity", "raw_usage", "total_usage", "close", "unknown_disposition"])
def test_corrupt_receipt_or_self_consistent_forged_digest_is_not_cache_success(cached_auto, corruption):
    state = cached_auto
    assert call()["model"] == MODEL
    data = saved(state)
    row = data["entries"][0]
    receipt = row["receipt"]
    doc = receipt["application_observation"]
    if corruption == "missing_schema":
        del row["schema"]
    elif corruption == "request_commitment":
        row["request"]["digest"] = doc["routing"]["request_digest"] = "a" * 64
    elif corruption == "routed_commitment":
        receipt["routed_request_digest"] = doc["routing"]["routed_request_digest"] = "b" * 64
    elif corruption == "foreign_pool":
        doc["routing"]["pool"] = "codex"
    elif corruption == "response_identity":
        doc["serving_model"] = receipt["served_model"] = "other-observed"
        receipt["observed_usage"]["serving_model"] = "other-observed"
    elif corruption == "raw_usage":
        receipt["observed_usage"]["input_tokens"] += 1
    elif corruption == "total_usage":
        receipt["usage"]["completed_input_tokens"] += 1
        receipt["usage"]["input_tokens"] += 1
    elif corruption == "unknown_disposition":
        doc["disposition"], doc["effect_unknown"] = "effect_unknown", True
        row["result"], row["result_digest"], row["error"] = None, None, "original_error"
    else:
        receipt["close"] = {"disposition": "local_only", "closed": False,
                            "effect_unknown": False, "attempted": False}
    state.cache.write_text(json.dumps(data))
    assert call()["degraded_reason"] == "fabric_cache_refused"
    assert_once(state)


def test_final_save_ack_loss_retains_original_pending_and_prevents_second_binding(cached_auto, monkeypatch):
    state = cached_auto
    original = tone._cache_save
    def save(path, value):
        if value["entries"][0]["state"] != "pending":
            raise OSError("synthetic final save failure before replace")
        return original(path, value)
    monkeypatch.setattr(tone, "_cache_save", save)
    assert call()["degraded_reason"] == "fabric_cache_refused"
    assert saved(state)["entries"][0]["state"] == "pending"
    monkeypatch.setattr(tone, "_cache_save", original)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert call()["degraded_reason"] == "fabric_original_held"
    assert_once(state)
