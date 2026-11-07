"""Public specialty consumers, real shared owner/client and pinned native A/B.

Only source documents, qualification, credentials and loopback provider output
are synthetic. Existing cache/parquet, SQLite, usage and close owners are real.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
import threading
from unittest.mock import Mock, patch

import pandas as pd
import pandas.core.arrays.arrow.extension_types  # noqa: F401 -- register before native module snapshot
import pytest

from lib import config
from engine import catalyst_tone as tone, catalyst_stock as stock, qual_extraction as qual, translate
from engine import fabric_inference_client as transport, provider_production_modes as owner
from collectors import special_situations as situations
from engine.trumpflow import extract as trump
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
_CLIENT = transport.FabricInferenceClient
SOURCE = "The board approved the merger. Rates remain unchanged."


def packet(value, *, finish="stop", model=MODEL):
    return {"model": model, "choices": [{"index": 0, "finish_reason": finish,
        "message": {"role": "assistant", "content": value if isinstance(value, str) else json.dumps(value)}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


def tone_value():
    return {"tone_score": 0, "guidance_direction": "on_hold", "risk_delta": 0,
        "shock_reversible": "unknown", "confidence": "high",
        "evidence": [{"field": "guidance_direction", "quote_span": "Rates remain unchanged."}]}


def qual_value():
    return {"direction": "up", "magnitude": "medium", "horizon": "short_term",
        "reversibility": "persistent", "importance_raw": 60, "confidence": "high",
        "evidence": [{"field": k, "quote_span": "The board approved the merger."}
                     for k in ("direction", "magnitude", "horizon", "reversibility")]}


@pytest.fixture
def specialty(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"] += ["catalyst-tone", "catalyst-stock", "translate-profiles", "qual-extraction", "special-situations", "trumpflow-extract"]
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    state.tone_cfg = {"enabled": True, "max_tokens": 128, "llm_min_confidence": "low"}
    state.qual_cfg = {"enabled": True, "max_tokens": 128, "confidence_floor": "low"}
    state.ss_cfg = {"enabled": True, "llm_brief": True}
    state.trump_cfg = {"max_tokens": 128}
    state.stock_cfg = {"enabled": True, "max_tokens": 128, "news_enabled": False, "translate_zh": False}
    state.trump_items = [{"text": SOURCE, "url": "https://fixture.invalid/source", "time": "2026-11-01",
                          "source_id": "news:document-1", "source_type": "news"}]
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "data_dir", lambda: state.root / "data")
    monkeypatch.setattr(config, "load", lambda: {"llm_models": {"extraction": "native-requested"}, "storage": {"site_dir": "site"}})
    monkeypatch.setattr(tone, "_cfg", lambda: state.tone_cfg)
    monkeypatch.setattr(qual, "_cfg", lambda: state.qual_cfg)
    monkeypatch.setattr(situations, "_cfg", lambda: state.ss_cfg)
    monkeypatch.setattr(trump, "_cfg", lambda: state.trump_cfg)
    monkeypatch.setattr(stock, "_cfg", lambda: state.stock_cfg)
    monkeypatch.setattr(trump, "enabled", lambda: True)
    monkeypatch.setattr(trump, "_news_items", lambda *a, **k: state.trump_items)
    monkeypatch.setattr(trump, "_filing_items", lambda *a, **k: [])
    for module, name in ((tone, "_client"), (stock, "_client"), (translate, "_client"), (qual, "_client"), (situations, "_llm_client")):
        monkeypatch.setattr(module, name, Mock(side_effect=AssertionError("native client touched")))
    monkeypatch.setattr(situations, "_fetch_filing_text", lambda *a, **k: SOURCE)
    state.closes = []
    original_close = _CLIENT.close
    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)
    monkeypatch.setattr(_CLIENT, "close", close)
    state.native.response = packet(tone_value())
    return state


def tone_call(**kwargs):
    return tone.digest_document(kwargs.pop("source", SOURCE), doc_id="document-1", **kwargs)


def tone_cache(state):
    return tone._fabric_cache_path(state.root / "data/catalyst/reply_cache",
        {"task": "catalyst-tone", "kind": "macro", "source_id": "document-1"})


def assert_one_effect(state):
    assert len(state.native.posts) == len(state.native.rows("application_requests")) == 1
    assert len(state.costs) == len(state.closes) == 1
    assert state.costs[0]["model"] == MODEL
    assert state.native.rows("leases")[0]["state"] == "released"


def test_tone_public_claim_precedes_send_and_warm_result_has_original_model_usage(specialty):
    state = specialty
    def observed():
        row = json.loads(tone_cache(state).read_text())["entries"][0]
        assert row["state"] == "pending"
        assert len(state.native.pending_at_send[0]) == 1
        assert row["operation_id"] == state.native.pending_at_send[0][0]["turn_id"]
    state.native.on_upstream = observed
    first = tone_call()
    assert first["model"] == MODEL and first["requested_model"] == "native-requested"
    assert first["guidance_direction"] == "on_hold" and not first["degraded_reason"]
    assert_one_effect(state)
    events = list(state.events)
    assert tone_call() == first
    assert state.events == events
    assert_one_effect(state)


def test_qual_public_cached_result_keeps_citations_confidence_and_observed_model(specialty):
    state = specialty
    state.native.response = packet(qual_value())
    first = qual.extract(SOURCE)
    assert first["model_id"] == MODEL and first["requested_model_id"] == "native-requested"
    assert first["brain_usable"] and first["fields"]["direction"] == "up"
    assert first["is_context_only"]
    assert qual.extract(SOURCE) == first
    assert_one_effect(state)


def test_qual_false_citations_remain_context_only_unusable_without_resend(specialty):
    value = qual_value()
    value["evidence"] = [{"field": "direction", "quote_span": "Invented unsupported statement"}]
    specialty.native.response = packet(value)
    result = qual.extract(SOURCE)
    assert not result["brain_usable"] and result["fields"]["direction"] == "unknown"
    assert result["dropped_fields"]
    qual.extract(SOURCE)
    assert_one_effect(specialty)


def test_concurrent_same_document_and_removed_selector_cannot_replace_pending(specialty, monkeypatch):
    state = specialty
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(tone_call)
        try:
            assert state.native.arrived.wait(2)
            monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
            duplicate = tone_call(source=SOURCE + " New revision.", context="changed context")
            assert duplicate["degraded_reason"] == "fabric_original_held"
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert first.result(timeout=5)["model"] == MODEL
    assert_one_effect(state)


def test_unknown_settlement_retains_observed_usage_and_original_hold(specialty, monkeypatch):
    state = specialty
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture lost settlement")):
        first = tone_call()
    assert first["degraded_reason"]
    row = json.loads(tone_cache(state).read_text())["entries"][0]
    assert row["state"] == "held"
    assert row["receipt"]["observed_usage"]["serving_model"] == MODEL
    assert row["receipt"]["observed_usage"]["input_tokens"] == 11
    assert state.native.rows("application_requests")[0]["state"] == "unknown"
    assert state.native.rows("leases")[0]["state"] in ("held", "rented")
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert tone_call()["degraded_reason"] == "fabric_original_held"
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1


@pytest.mark.parametrize("case", ["protocol", "length", "tools", "empty", "invalid_json"])
def test_unaccepted_response_is_not_repaired_or_cached_as_success(specialty, case):
    state = specialty
    if case == "protocol":
        state.native.response = b'{"model":'
    elif case == "tools":
        state.native.response = packet(None, finish="tool_calls")
        state.native.response["choices"][0]["message"].update(content=None,
            tool_calls=[{"id": "unexpected", "type": "function", "function": {"name": "read", "arguments": "{}"}}])
    else:
        state.native.response = packet("" if case == "empty" else "not JSON" if case == "invalid_json" else tone_value(),
                                       finish="length" if case == "length" else "stop")
    assert tone_call()["degraded_reason"]
    record = json.loads(tone_cache(state).read_text())["entries"][0]
    assert record["result"] is None
    tone_call()
    assert len(state.native.posts) == len(state.closes) == 1
    assert len(state.costs) <= 1


def change_transport(state, monkeypatch):
    updated = replace(state.transport, cap_id="fabric:changed-fixture")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", updated)
    state.row["cap_id"] = updated.cap_id
    state.save()


def test_inspection_to_bind_race_refuses_before_credentials(specialty, monkeypatch):
    original = owner.ApplicationFabricFactory.inspect
    def inspect(factory, *args, **kwargs):
        value = original(factory, *args, **kwargs)
        change_transport(specialty, monkeypatch)
        return value
    monkeypatch.setattr(owner.ApplicationFabricFactory, "inspect", inspect)
    assert tone_call()["degraded_reason"]
    assert specialty.events == specialty.native.posts == specialty.costs == []


def test_same_input_new_transport_cannot_relabel_or_mint_another_cache_fill(specialty, monkeypatch):
    assert tone_call()["model"] == MODEL
    change_transport(specialty, monkeypatch)
    assert tone_call()["degraded_reason"]
    assert_one_effect(specialty)


@pytest.mark.parametrize("corruption", ["null", "duplicate", "contradictory", "duplicate_id", "observation", "usage"])
def test_corrupt_original_is_not_absence_even_after_selector_removal(specialty, monkeypatch, corruption):
    assert tone_call()["model"] == MODEL
    path = tone_cache(specialty)
    value = json.loads(path.read_text())
    if corruption == "null":
        path.write_text("null")
    elif corruption == "duplicate":
        path.write_text('{"schema":1,"schema":2}')
    else:
        if corruption == "contradictory":
            value["entries"][0]["receipt"]["effect_unknown"] = True
        elif corruption == "duplicate_id":
            row = copy.deepcopy(value["entries"][0])
            row["input_digest"] = "a" * 64
            value["entries"].append(row)
        elif corruption == "observation":
            value["entries"][0]["receipt"]["observed_usage"]["request_id"] = "other:brain:0"
        else:
            value["entries"][0]["receipt"]["usage"]["input_tokens"] = None
        path.write_text(json.dumps(value))
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert tone_call(source=SOURCE + " Changed.")["degraded_reason"] == "fabric_cache_refused"
    assert_one_effect(specialty)


def test_lost_claim_save_ack_holds_original_before_any_bind(specialty, monkeypatch):
    original = tone._cache_save
    def save(path, value):
        original(path, value)
        raise OSError("fixture lost durable save acknowledgement")
    monkeypatch.setattr(tone, "_cache_save", save)
    assert tone_call()["degraded_reason"]
    monkeypatch.setattr(tone, "_cache_save", original)
    assert tone_call()["degraded_reason"] == "fabric_original_held"
    assert specialty.events == specialty.native.posts == specialty.costs == []


@pytest.mark.parametrize("profile", [None, ""])
def test_present_invalid_profile_does_not_default_to_batch(specialty, profile):
    specialty.tone_cfg["workload_profile"] = profile
    assert tone_call()["degraded_reason"]
    assert specialty.events == specialty.native.posts == []


def test_no_input_and_disabled_preserve_no_model_gate(specialty):
    assert tone_call(source="")["degraded_reason"] == "empty_source"
    assert qual.extract("") is None
    specialty.tone_cfg["enabled"] = False
    assert tone_call() is None
    assert specialty.events == specialty.native.posts == []


def test_cache_traversal_refuses_before_outside_directory_or_binding(specialty):
    specialty.tone_cfg["reply_cache_dir"] = "data/../../outside-fixture"
    assert tone_call()["degraded_reason"]
    assert not (specialty.root.parent / "outside-fixture").exists()
    assert specialty.events == specialty.native.posts == []


def seed_situations(*rows):
    base = {"company": "Fixture Corp", "ticker": "TEST", "cik": "1", "accession": "0001",
        "date_filed": "2026-11-01", "source_url": "https://fixture.invalid/public", "form_type": "8-K",
        "items": "1.03", "category": "Restructuring", "summary": None, "llm_category": None}
    return situations._save_events([{**base, **row} for row in rows])


def test_special_summaries_isolate_documents_and_preserve_concurrent_ingestion(specialty):
    state = specialty
    seed_situations({"id": "a"}, {"id": "b", "accession": "0002"})
    state.native.response = packet({"summary": "The board approved the merger.", "filer": "Fixture LLC", "deal_terms": {}})
    def ingest():
        seed_situations({"id": "new", "accession": "0003"})
    state.native.on_upstream = ingest
    result = situations.enrich_summaries(limit=2)
    assert set(result.id) == {"a", "b", "new"}
    assert result[result.id.isin(["a", "b"])].summary.notna().all()
    assert set(result[result.id.isin(["a", "b"])].llm_summary_model) == {MODEL}
    assert len(set(state.closes)) == len(state.native.posts) == len(state.costs) == 2
    assert all(row["state"] == "released" for row in state.native.rows("leases"))


def test_special_classification_keeps_vocabulary_and_reuses_saved_delivery(specialty, monkeypatch):
    state = specialty
    seed_situations({"id": "c", "items": "1.01"})
    state.native.response = packet({"category": "Acquisitions", "role": "target", "confidence": "high",
        "summary": "The board approved the merger.", "deal_terms": {}})
    original = situations._merge_event_updates
    monkeypatch.setattr(situations, "_merge_event_updates", Mock(side_effect=OSError("fixture parquet unavailable")))
    with pytest.raises(OSError):
        situations.enrich_classify()
    monkeypatch.setattr(situations, "_merge_event_updates", original)
    result = situations.enrich_classify()
    assert result.iloc[0].llm_category == "Acquisitions"
    assert result.iloc[0].llm_classify_model == MODEL
    assert_one_effect(state)


def test_special_invalid_partial_category_never_promotes(specialty):
    seed_situations({"id": "d", "items": "1.01"})
    specialty.native.response = packet({"category": "Acquis", "role": "target", "confidence": "high",
        "summary": "The board approved the merger.", "deal_terms": {}})
    result = situations.enrich_classify()
    assert pd.isna(result.iloc[0].llm_category)
    situations.enrich_classify()
    assert_one_effect(specialty)


def trump_reply():
    return {"edges": [{"src": "Fixture Family", "rel": "INVESTS_IN", "dst": "Fixture Company",
        "citation": "The board approved the merger.", "asset_hint": "Public source only"}]}


def test_trump_public_claim_delivery_and_watermark_use_one_original(specialty):
    state = specialty
    state.native.response = packet(trump_reply())
    def observed():
        record = json.loads(trump._seen_path().read_text())["selected"]["news:document-1"]
        row = record["cache"]["entries"][0]
        assert row["state"] == "pending" and not record["delivered"]
        assert row["operation_id"] == state.native.pending_at_send[0][0]["turn_id"]
        assert not trump._path().exists()
    state.native.on_upstream = observed
    assert trump.run() == {"extracted": 1, "processed": 1, "reason": "ok"}
    result = trump.load_candidates()
    assert len(result) == 1
    assert (result[0]["status"], result[0]["confidence"], result[0]["provenance"]) == ("candidate", 0.5, "INFERRED")
    assert result[0]["llm_model"] == MODEL
    assert trump.run() == {"extracted": 0, "processed": 0, "reason": "ok"}
    assert_one_effect(state)


def test_trump_pending_survives_stale_native_pruning_input_and_selector_changes(specialty, monkeypatch):
    state = specialty
    state.native.response = packet(trump_reply())
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(trump.run)
        try:
            assert state.native.arrived.wait(2)
            original = json.loads(trump._seen_path().read_text())["selected"]
            trump._save_seen({f"old-{i:05d}" for i in range(5010)})
            saved = json.loads(trump._seen_path().read_text())
            assert len(saved["seen"]) == 5000 and saved["selected"] == original
            state.trump_items[0] = {**state.trump_items[0], "text": "Changed input"}
            monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
            monkeypatch.setattr(trump, "_news_items", Mock(side_effect=AssertionError("new input read before original")))
            assert trump.run()["reason"] == "fabric_original_held"
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert first.result(timeout=5)["extracted"] == 1
    assert_one_effect(state)


def test_trump_crash_after_candidate_commit_recovers_without_inference_or_duplicate(specialty, monkeypatch):
    state = specialty
    state.native.response = packet(trump_reply())
    original = trump._write_seen
    def lose_delivery_ack(document, root=None):
        if any(record["delivered"] for record in document["selected"].values()):
            raise OSError("fixture lost seen delivery commit")
        return original(document, root)
    monkeypatch.setattr(trump, "_write_seen", lose_delivery_ack)
    assert trump.run()["reason"] == "fabric_delivery_refused"
    assert len(trump.load_candidates()) == 1
    record = json.loads(trump._seen_path().read_text())["selected"]["news:document-1"]
    assert record["cache"]["entries"][0]["state"] == "terminal" and not record["delivered"]
    monkeypatch.setattr(trump, "_write_seen", original)
    assert trump.run() == {"extracted": 0, "processed": 0, "reason": "ok"}
    assert len(trump.load_candidates()) == 1
    assert_one_effect(state)


@pytest.mark.parametrize("value,valid", [("not JSON", False), ({"edges": []}, True),
    ({"edges": [{"src": "Fake", "rel": "INVESTS_IN", "dst": "Other", "citation": "unsupported"}]}, True)])
def test_trump_bad_reply_and_valid_zero_edges_have_distinct_terminal_records(specialty, value, valid):
    specialty.native.response = packet(value)
    first = trump.run()
    assert (first["reason"] == "ok") is valid
    assert first["extracted"] == 0
    record = json.loads(trump._seen_path().read_text())["selected"]["news:document-1"]
    row = record["cache"]["entries"][0]
    assert record["delivered"] and row["state"] == "terminal"
    assert (row["result"] == []) is valid
    trump.run()
    assert_one_effect(specialty)


def test_trump_unknown_close_is_held_before_later_source_or_native_fallback(specialty, monkeypatch):
    specialty.native.response = packet(trump_reply())
    with patch.object(specialty.native.gateway, "complete_application", side_effect=OSError("fixture unknown settlement")):
        assert trump.run()["reason"] != "ok"
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert trump.run()["reason"] == "fabric_original_held"
    assert trump.load_candidates() == []
    assert len(specialty.native.posts) == 1


@pytest.mark.parametrize("target", ["seen", "candidates"])
def test_trump_corrupt_existing_owner_refuses_before_model(specialty, target):
    path = trump._seen_path() if target == "seen" else trump._path()
    path.parent.mkdir(parents=True)
    path.write_text('{"schema":"trumpflow.extract_seen.v2","seen":[],"selected":null}'
                    if target == "seen" else "not valid candidate JSON\n")
    assert trump.run()["reason"] == "fabric_state_refused"
    assert specialty.events == specialty.native.posts == []


def test_trump_native_watermark_format_and_disabled_empty_gates(specialty, monkeypatch):
    trump._save_seen({"legacy-source"})
    assert json.loads(trump._seen_path().read_text()) == ["legacy-source"]
    specialty.trump_items = []
    assert trump.run()["processed"] == 0
    assert trump._call(SOURCE, specialty.trump_cfg) is None
    monkeypatch.setattr(trump, "enabled", lambda: False)
    assert trump.run()["reason"] == "disabled"
    assert specialty.events == specialty.native.posts == []


def test_trump_completed_selected_id_survives_pruning_and_selector_removal(specialty, monkeypatch):
    specialty.native.response = packet(trump_reply())
    assert trump.run()["extracted"] == 1
    trump._save_seen({f"old-{i:05d}" for i in range(5010)})
    saved = json.loads(trump._seen_path().read_text())
    assert "news:document-1" not in saved["seen"]
    assert "news:document-1" in trump._load_seen()
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert trump.run() == {"extracted": 0, "processed": 0, "reason": "ok"}
    assert_one_effect(specialty)


def test_trump_changed_bound_cannot_add_second_claim_after_terminal_before_delivery(specialty, monkeypatch):
    specialty.native.response = packet(trump_reply())
    original = trump._write_seen
    def lose_delivery_ack(document, root=None):
        if any(record["delivered"] for record in document["selected"].values()):
            raise OSError("fixture lost delivery acknowledgement")
        return original(document, root)
    monkeypatch.setattr(trump, "_write_seen", lose_delivery_ack)
    assert trump.run()["reason"] == "fabric_delivery_refused"
    before = trump._seen_path().read_bytes()
    changed = {**specialty.trump_cfg, "max_tokens": 256}
    assert trump._selected_call(specialty.trump_items[0], changed)["error"] == "fabric_cache_refused"
    assert trump._seen_path().read_bytes() == before
    assert_one_effect(specialty)


def test_trump_explicit_root_data_symlink_cannot_change_original_lookup(specialty, tmp_path):
    caller = tmp_path / "caller"
    caller.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (caller / "data").symlink_to(outside, target_is_directory=True)
    assert trump.run(root=caller)["reason"] == "fabric_state_refused"
    assert not list(outside.iterdir())
    assert specialty.events == specialty.native.posts == []


def stock_source(state, ticker="FIX", *, root=None):
    destination = (root or state.root) / "site/stockdata"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / (stock.safe_name(ticker) + ".json")).write_text(json.dumps({
        "ticker": ticker, "name": "Fixture Company", "asof": "2026-11-01",
        "tech": {"price": 42}, "ladder": {"state": "WATCH"},
        "holdings": [{"ticker": "PRIVATE", "weight_pct": 50}]}))


def stock_value():
    return {"summary": "The public price is 42.", "drivers": ["Public source context."],
        "risks": [], "catalysts": [], "confidence": "medium"}


def stock_state(state, ticker="FIX"):
    return json.loads(stock._stock_path(state.root, state.stock_cfg, ticker).read_text())


def test_stock_public_original_precedes_send_and_direct_precompute_warm_reuse(specialty):
    state = specialty
    stock_source(state)
    state.native.response = packet(stock_value())
    def observed():
        row = stock_state(state)["entries"][0]
        english = row["english"]["entries"][0]
        assert row["state"] == english["state"] == "pending"
        assert english["operation_id"] == state.native.pending_at_send[0][0]["turn_id"]
        prompt = json.loads(state.native.posts[-1][1])["messages"][-1]["content"]
        context = prompt.split("<context>", 1)[1].split("</context>", 1)[0]
        assert "PRIVATE" not in context and "holdings" not in context
    state.native.on_upstream = observed
    result = stock.brief_for_ticker("FIX")
    assert result["summary"] == stock_value()["summary"] and result["model"] == MODEL
    assert result["is_context_only"] and result["degraded_reason"] is None
    assert stock.brief_for_ticker("FIX") == result
    assert stock.precompute_briefs(["FIX", "FIX"], root=state.root, site=state.root/"site") == [
        {"ticker": "FIX", "degraded_reason": None}]
    assert json.loads((state.root/"site/stockbrief/FIX.json").read_text()) == result
    assert len(stock_state(state)["entries"]) == 1
    assert_one_effect(state)


def test_stock_pending_survives_force_day_context_options_and_selector(specialty, monkeypatch):
    state = specialty
    stock_source(state)
    state.native.response = packet(stock_value())
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(stock.brief_for_ticker, "FIX")
        try:
            assert state.native.arrived.wait(2)
            monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
            state.stock_cfg.update(enabled=False, max_tokens=256)
            monkeypatch.setattr(stock, "assemble_context", Mock(side_effect=AssertionError("original must precede new context")))
            cfg_owner = stock._cfg
            result = stock.precompute_briefs(["FIX"], root=state.root, site=state.root/"site", force=True)
            assert result == [{"ticker": "FIX", "degraded_reason": "fabric_original_held"}]
            assert stock._cfg is cfg_owner and state.stock_cfg["enabled"] is False
            assert stock._brief_for_ticker("FIX", {**state.stock_cfg, "enabled": True}, state.root, False)["degraded_reason"] == "fabric_original_held"
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert first.result(timeout=5)["summary"] == stock_value()["summary"]
    assert_one_effect(state)


def test_stock_selected_ignores_native_daily_cache_and_preserves_precompute_order_cap(specialty):
    state = specialty
    for ticker in ("FIX", "ALT", "EXCESS"):
        stock_source(state, ticker)
    state.stock_cfg.update(precompute_max=2, brief_workers=2)
    path = stock._cache_path(state.root, state.stock_cfg, "FIX", stock.date.today().isoformat())
    path.write_text(json.dumps({"ticker": "FIX", "summary": "legacy unlabelled result"}))
    old = path.read_bytes()
    state.native.response = packet(stock_value())
    result = stock.precompute_briefs(["ALT", "FIX", "ALT", "EXCESS"], root=state.root)
    assert [r["ticker"] for r in result] == ["ALT", "FIX"]
    assert len(state.native.posts) == len(state.costs) == 2
    assert path.read_bytes() == old
    assert not stock._stock_path(state.root, state.stock_cfg, "EXCESS").exists()


def test_stock_news_and_synthesis_have_distinct_originals_and_no_receipt_in_prompt(specialty, monkeypatch):
    state = specialty
    stock_source(state)
    state.stock_cfg["news_enabled"] = True
    monkeypatch.setattr(stock, "_fetch_stock_headlines", lambda *a: [SOURCE])
    def answer():
        row = stock_state(state)["entries"][0]
        if len(state.native.posts) == 1:
            assert row["news"]["state"] == "pending" and row["news"]["headlines"] == [SOURCE]
            assert row["english"] is None
            state.native.response = packet(tone_value())
        else:
            assert row["news"]["state"] == "terminal" and row["news"]["result"]["fabric"]["close"]["closed"]
            content = json.loads(state.native.posts[-1][1])["messages"][-1]["content"]
            assert "operation_id" not in content and "observed_usage" not in content
            state.native.response = packet(stock_value())
    state.native.on_upstream = answer
    result = stock.brief_for_ticker("FIX")
    assert result["summary"] and result["news_fabric"]["served_model"] == MODEL
    ids = [row["turn_id"] for row in state.native.rows("application_turns")]
    assert len(ids) == len(set(ids)) == len(state.costs) == len(state.closes) == 2
    assert stock.brief_for_ticker("FIX") == result
    assert len(state.native.posts) == 2


def test_stock_unknown_news_stops_english_and_translation(specialty, monkeypatch):
    stock_source(specialty)
    specialty.stock_cfg.update(news_enabled=True, translate_zh=True)
    monkeypatch.setattr(stock, "_fetch_stock_headlines", lambda *a: [SOURCE])
    specialty.native.response = packet(tone_value())
    with patch.object(specialty.native.gateway, "complete_application", side_effect=OSError("fixture unknown news settlement")):
        result = stock.brief_for_ticker("FIX")
    assert result["summary"] is None and result["degraded_reason"] == "fabric_news_original_held"
    row = stock_state(specialty)["entries"][0]
    assert row["state"] == "held" and row["english"] is row["translation"] is None
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert stock.brief_for_ticker("FIX", include_news=False)["degraded_reason"] == "fabric_original_held"
    assert len(specialty.native.posts) == 1


@pytest.mark.parametrize("translations", [["公开价格是四十二。", "公开信息。"], ["公开价格是四十二。", None], [None, None]])
def test_stock_chinese_output_keeps_english_and_unknown_settlement_without_replay(specialty, monkeypatch, translations):
    state = specialty
    stock_source(state)
    state.stock_cfg["translate_zh"] = True
    def answer():
        row = stock_state(state)["entries"][0]
        if len(state.native.posts) == 1:
            state.native.response = packet(stock_value())
        else:
            leg = row["translation"]
            assert leg["state"] == "pending" and leg["input"]["texts"] == [stock_value()["summary"], stock_value()["drivers"][0]]
            assert leg["operation_id"] in [r["turn_id"] for r in state.native.pending_at_send[-1]]
            assert row["english"]["entries"][0]["state"] == "terminal"
            state.native.response = packet(translations)
    state.native.on_upstream = answer
    result = stock.brief_for_ticker("FIX")
    assert result["summary"] == stock_value()["summary"] and result["model"] == MODEL
    assert result["translation"]["effect_unknown"] is True
    assert all(result["translation"][k] is None for k in ("served_model", "usage", "close"))
    assert result.get("zh", {}).get("summary") == translations[0]
    row = stock_state(state)["entries"][0]
    assert row["state"] == "held" and row["translation"]["output"] == translations
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 2
    assert all(r["state"] == "released" for r in state.native.rows("leases"))
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    result2 = stock.brief_for_ticker("FIX", include_news=False)
    assert result2["summary"] == result["summary"] and result2["degraded_reason"] == "fabric_original_held"
    assert result2.get("zh") == result.get("zh") and len(state.native.posts) == 2


def test_stock_chinese_unknown_close_cannot_be_inferred_from_complete_text(specialty):
    state = specialty
    stock_source(state)
    state.stock_cfg["translate_zh"] = True
    original = state.native.gateway.close_application_turn
    def close(*args, **kwargs):
        if len(state.native.posts) > 1:
            raise OSError("fixture translation close acknowledgement lost")
        return original(*args, **kwargs)
    state.native.on_upstream = lambda: setattr(state.native, "response", packet(
        stock_value() if len(state.native.posts) == 1 else ["公开价格是四十二。", "公开信息。"] ))
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        result = stock.brief_for_ticker("FIX")
    assert result["zh"]["summary"] and result["translation"]["close"] is None
    assert stock_state(state)["entries"][0]["state"] == "held"
    stock.brief_for_ticker("FIX")
    assert len(state.native.posts) == 2


def test_stock_custom_root_keeps_english_without_translator_binding(specialty, monkeypatch, tmp_path):
    state = specialty
    stock_source(state)
    state.stock_cfg["translate_zh"] = True
    other = tmp_path / "other-root"
    other.mkdir()
    monkeypatch.setattr(config, "ROOT", other)
    state.native.response = packet(stock_value())
    result = stock.brief_for_ticker("FIX", root=state.root)
    assert result["summary"] and result["translation_error"] == "fabric_translation_root_mismatch"
    assert stock_state(state)["entries"][0]["translation"] is None
    assert stock_state(state)["entries"][0]["state"] == "terminal"
    assert_one_effect(state)


def test_stock_saved_english_survives_lost_outer_save_without_next_leg(specialty, monkeypatch):
    state = specialty
    stock_source(state)
    state.stock_cfg["translate_zh"] = True
    state.native.response = packet(stock_value())
    original = stock._stock_commit
    def lose_outer_save(path, root, ticker, digest, change):
        if change.__name__ == "save_english":
            raise OSError("fixture lost outer save")
        return original(path, root, ticker, digest, change)
    monkeypatch.setattr(stock, "_stock_commit", lose_outer_save)
    stock.brief_for_ticker("FIX")
    monkeypatch.setattr(stock, "_stock_commit", original)
    result = stock.brief_for_ticker("FIX")
    assert result["summary"] == stock_value()["summary"] and result["model"] == MODEL
    assert result["degraded_reason"] == "fabric_original_held"
    assert stock_state(state)["entries"][0]["translation"] is None
    assert_one_effect(state)


@pytest.mark.parametrize("value,finish", [("not JSON", "stop"), ({}, "stop"), (stock_value(), "length")])
def test_stock_terminal_bad_reply_and_valid_truncation_never_retry(specialty, value, finish):
    stock_source(specialty)
    specialty.native.response = packet(value, finish=finish)
    result = stock.brief_for_ticker("FIX")
    if finish == "length":
        assert result["summary"] == stock_value()["summary"] and result["degraded_reason"] == "truncated"
    else:
        assert result["summary"] is None and result["degraded_reason"]
    assert stock.brief_for_ticker("FIX") == result
    assert stock_state(specialty)["entries"][0]["state"] == "terminal"
    assert_one_effect(specialty)


def test_stock_feature_no_context_invalid_selector_and_corrupt_state_are_zero_effect(specialty, monkeypatch):
    specialty.stock_cfg["enabled"] = False
    assert stock.brief_for_ticker("FIX") is None
    specialty.stock_cfg["enabled"] = True
    assert stock.brief_for_ticker("FIX")["degraded_reason"] == "no_context"
    assert specialty.events == specialty.native.posts == []
    stock_source(specialty)
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "")
    assert stock.brief_for_ticker("FIX")["degraded_reason"] == "fabric_stock_refused"
    path = stock._stock_path(specialty.root, specialty.stock_cfg, "FIX")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema":"macro.stockbrief_fabric_cache.v1","ticker":"FIX","entries":null}')
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert stock.brief_for_ticker("FIX")["degraded_reason"] == "fabric_stock_refused"
    assert specialty.events == specialty.native.posts == []


def test_stock_warm_rechecks_full_identity_and_usage_sink_none(specialty):
    state = specialty
    stock_source(state)
    state.stock_cfg["usage_sink"] = "none"
    state.native.response = packet(stock_value())
    assert stock.brief_for_ticker("FIX")["summary"]
    assert state.costs == [] and len(state.native.posts) == 1
    before = list(state.events)
    state.row["enabled"] = False
    state.save()
    assert stock.brief_for_ticker("FIX")["degraded_reason"] == "fabric_stock_refused"
    assert state.events == before and len(state.native.posts) == 1


@pytest.mark.parametrize("metadata", [
    {"fabric_operation_id": "translate-profiles:" + "a"*32},
    {"fabric_inspection": {}},
    {"fabric_operation_id": "bad/id", "fabric_inspection": {}},
    {"fabric_operation_id": "translate-profiles:" + "a"*32, "fabric_inspection": None},
])
def test_translation_companion_invalid_original_metadata_is_local_refusal(specialty, metadata):
    assert translate.translate_to_zh(["Public text"], {"enabled": True}, **metadata) == [None]
    assert specialty.events == specialty.native.posts == []


def test_translation_companion_exact_id_and_changed_inspection(specialty):
    state = specialty
    cfg = {"enabled": True, "workload_profile": "site_batch", "max_tokens": 128}
    factory = owner.make_application_fabric_factory(mode_id="shared_fabric", lane="translate-profiles",
        root=state.root, workload_cfg={**cfg, "provider_order": ["fabric"]})
    inspection = factory.inspect(cfg)
    identifier = "translate-profiles:" + "a"*32
    state.native.response = packet(["公开文本"])
    assert translate.translate_to_zh(["Public text"], cfg, fabric_operation_id=identifier,
        fabric_inspection=inspection) == ["公开文本"]
    assert state.native.rows("application_turns")[0]["turn_id"] == identifier
    assert_one_effect(state)
    changed = {**inspection, "policy_hash": "0"*64}
    before = list(state.events)
    assert translate.translate_to_zh(["Other text"], cfg,
        fabric_operation_id="translate-profiles:" + "b"*32, fabric_inspection=changed) == [None]
    assert state.events == before and len(state.native.posts) == 1


def test_stock_terminal_marker_without_english_cannot_clear_original(specialty, monkeypatch):
    state = specialty
    stock_source(state)
    original = tone._cache_save
    def lose_ack(path, value):
        original(path, value)
        if value.get("schema") == "macro.stockbrief_fabric_cache.v1":
            raise OSError("fixture lost initial claim acknowledgement")
    monkeypatch.setattr(tone, "_cache_save", lose_ack)
    first = stock.brief_for_ticker("FIX")
    assert first["model"] is None and first["requested_model"] == "deepseek-v4-pro"
    path = stock._stock_path(state.root, state.stock_cfg, "FIX")
    value = json.loads(path.read_text())
    assert value["entries"][0]["english"] is None
    value["entries"][0]["state"] = "terminal"
    path.write_text(json.dumps(value))
    monkeypatch.setattr(tone, "_cache_save", original)
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert stock.brief_for_ticker("FIX", include_news=False)["degraded_reason"] == "fabric_stock_refused"
    assert state.events == state.native.posts == []


def test_stock_news_terminal_marker_cannot_relabel_unknown_receipt(specialty, monkeypatch):
    state = specialty
    stock_source(state)
    state.stock_cfg["news_enabled"] = True
    monkeypatch.setattr(stock, "_fetch_stock_headlines", lambda *a: [SOURCE])
    state.native.response = packet(tone_value())
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture unknown news")):
        assert stock.brief_for_ticker("FIX")["degraded_reason"] == "fabric_news_original_held"
    path = stock._stock_path(state.root, state.stock_cfg, "FIX")
    value = json.loads(path.read_text())
    value["entries"][0]["news"]["state"] = "terminal"
    path.write_text(json.dumps(value))
    assert stock.brief_for_ticker("FIX")["degraded_reason"] == "fabric_stock_refused"
    assert len(state.native.posts) == 1


def test_stock_explicit_allowed_profile_intersects_actual_batch_purpose_through_chinese(specialty):
    state = specialty
    stock_source(state)
    state.stock_cfg.update(workload_profile="portfolio_analysis", translate_zh=True, usage_sink="none")
    state.native.on_upstream = lambda: setattr(state.native, "response", packet(
        stock_value() if len(state.native.posts) == 1 else ["公开价格是四十二。", "公开信息。"] ))
    result = stock.brief_for_ticker("FIX")
    assert result["zh"]["summary"] and result["summary"] == stock_value()["summary"]
    row = stock_state(state)["entries"][0]
    assert len(state.native.posts) == len(state.closes) == 2 and state.costs == []
    assert row["translation"]["operation_id"] != row["english"]["entries"][0]["operation_id"]
    assert row["translation"]["operation_id"].startswith("translate-profiles:")
    serialized = json.dumps(row["translation"]["inspection"])
    assert "site_batch" in serialized and "portfolio_analysis" in serialized


def test_tone_daily_public_path_bypasses_native_typed_cache_and_keeps_original(specialty, monkeypatch):
    state = specialty
    meeting = tone.date(2026, 10, 28)
    native_cache = tone._cache_path("fomc_2026-10-28", state.tone_cfg)
    native_cache.write_text(json.dumps({"guidance_direction": "legacy"}))
    monkeypatch.setattr(tone, "fetch_fomc_statement", lambda *a: (SOURCE, None))
    state.native.response = packet(tone_value())
    result = tone.daily_snapshot(meeting)
    assert result["guidance_direction"] == "on_hold" and result["is_context_only"]
    assert tone.daily_snapshot(meeting) == result
    assert_one_effect(state)


def test_tone_event_public_snapshot_commits_source_before_model_and_reuses_it(specialty, monkeypatch):
    state = specialty
    today = tone.date(2026, 11, 1)
    fetch = Mock(return_value=[SOURCE])
    monkeypatch.setattr(tone, "_fetch_event_headlines", fetch)
    state.native.response = packet(tone_value())
    def observed():
        assert tone._gdelt_snapshot_get(today, state.tone_cfg) == [SOURCE]
    state.native.on_upstream = observed
    result = tone.event_snapshot(today, context="Public event")
    assert result["guidance_direction"] == "on_hold" and result["is_context_only"]
    assert tone.event_snapshot(today, context="Public event") == result
    assert fetch.call_count == 1
    assert_one_effect(state)
