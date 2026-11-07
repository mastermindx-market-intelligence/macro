"""Synthetic COMPLETE custody -> real gateway -> exact saved original sources.

The native selected source/training owner and login are explicit fixture stand-ins.
The real House policies, trusted captures, COMPLETE accounting, native reopen,
evidence join, Brain dispatch and citation consumers are exercised unchanged.
No installed admission, provider request, new study or production proof is claimed.
"""
import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException

from app import market_memory as incumbent
from app import market_memory_fitted as api
from engine.neuralweb import brain_gateway as gateway
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_fitted_brain_citations as wire
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as house
from engine.research_factory import market_memory_fitted_persistence as persistence
from tests.test_market_memory_fitted_persistence import retained_owner
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_e0_installed_control import selection, records
from tests.test_market_memory_retained_context_cohort import capture, owner as native_owner, load

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def complete_query(retained_owner, tmp_path, monkeypatch):
    private, _, template, context, now, subject = retained_owner
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", tmp_path)
    for rel in (house.REGISTRATION, house.AUTHORITY_RECORD):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())
    original = template["binding"]["source_owner"]
    registration_path = tmp_path / house.REGISTRATION
    registration = json.loads(registration_path.read_bytes())
    registration["store_id"] = original["store_id"]
    registration_path.write_text(json.dumps(registration))
    # Explicit synthetic public enrollment, fixed BEFORE the COMPLETE fit.
    # Actual selected source/temporal qualification remains retained_owner's stand-in.
    purpose = json.loads((ROOT / persistence.use.PURPOSE_PATH).read_bytes())
    binding_bytes = cohort.canonical(template["binding"])
    purpose.update(enabled=True, store_id=original["store_id"], selected_study_id="synthetic-study",
        binding_ref={"schema": persistence.use.SCHEMA, "object_id": template["binding"]["binding_id"],
                     "sha256": sha256(binding_bytes).hexdigest(), "bytes": len(binding_bytes)})
    (tmp_path / persistence.use.PURPOSE_PATH).write_text(json.dumps(purpose))
    def login(user):
        if user != "member":
            raise HTTPException(403)
    monkeypatch.setattr(house, "_enforce_current_site_user", login)
    training = house.RetainedHouseUsePolicy(tmp_path, user_id="member", subject_id=subject,
        store_id=original["store_id"], generation_id=original["generation_id"],
        generation_sha256=original["generation_sha256"], query_cutoff=template["binding"]["fit_cutoff"],
        mode=template["binding"]["mode"])
    retained = persistence.persist_registered_fit(policy=training)
    later = capture(tmp_path, monkeypatch, session="2026-10-14", growth=0.7)
    now[0] = "2026-10-14T11:00:00.000000Z"
    reader, pin = native_owner(tmp_path)
    monkeypatch.setenv("MARKET_MEMORY_TRUSTED_STORE_DIR", str(reader.root))
    query_policy = house.RetainedHouseUsePolicy(tmp_path, user_id="member", subject_id=subject,
        store_id=pin.store_id, generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
        query_cutoff=now[0], mode=template["binding"]["mode"])
    population = load(reader, pin, later, cutoff=now[0], policy=query_policy)
    query = features.read_episode_feature_capability(reader, pin,
        query_id=later.capture_receipt["query_id"], subject_id=subject, query_cutoff=now[0], policy=query_policy)
    result = persistence.retain_registered_fitted_query(retained, population, query, policy=query_policy, k=2)
    request = {"reference": {key: result[key] for key in ("operation_id", "intent", "sha256", "bytes")},
               "mode": template["binding"]["mode"]}
    # After setup the consumer may only reopen original COMPLETE custody.
    def forbidden(*args, **kwargs):
        pytest.fail("read attempted to create/refit/reserve/retain")
    for name in ("initialize_registered_fit_accounting", "persist_registered_fit", "retain_registered_fitted_query"):
        monkeypatch.setattr(persistence, name, forbidden)
    monkeypatch.setattr(fitted, "fit_registered_normalizer", forbidden)
    for name in ("initialize", "reserve", "finish"):
        monkeypatch.setattr(persistence.ReservationStore, name, forbidden)
    incumbent._reset_symbol_rate_limit_for_tests()
    before = {str(p.relative_to(private)): p.read_bytes() for p in private.rglob("*") if p.is_file()}
    yield tmp_path, request, result["value"]["result"], reader, pin
    assert {str(p.relative_to(private)): p.read_bytes() for p in private.rglob("*") if p.is_file()} == before


def dispatch(root, request, user="member"):
    return gateway._dispatch_brain_tool(wire.TOOL_NAME, request, root, root, "", user_id=user)


def messages(request, value):
    return [{"role": "assistant", "content": [{"type": "tool_use", "id": "fitted_original",
        "name": wire.TOOL_NAME, "input": request}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "fitted_original",
        "content": json.dumps(value)}]}]


def test_genuine_complete_gateway_to_each_exact_saved_source(complete_query, monkeypatch):
    root, request, native, _reader, _pin = complete_query
    value = dispatch(root, request)
    assert value.get("schema") == wire.SCHEMA, value
    assert value["denominator"]["returned"] == 2
    assert value["selection_sha256"] == native["selection_sha256"]
    assert value["reopen_reference"] == request["reference"]
    assert not any(value["claims"].values())
    links = gateway._extract_citations_brain(messages(request, value))
    assert len(links) == 3, (links, value)
    saved_sources, catalogs = [], []
    for link, card in zip(links, value["source_cards"], strict=True):
        p = {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}
        assert len(p) == 8 and p["mm_mode"] == "saved" and "mm_method" not in p
        assert p["mm_context"] == p["mm_source_context"] == card["context_id"]
        catalog = incumbent.retained_catalog_for_user(root, "member", {
            "mode": request["mode"], "generation_id": p["mm_gen"], "generation_sha256": p["mm_gen_sha"],
            "query_id": p["mm_query"], "context_id": p["mm_context"], "limit": 1})
        catalogs.append(catalog)
        exact = {"query_id": p["mm_query"], "context_id": p["mm_context"],
                 "capture_id": card["capture_id"], "subject_id": p["mm_subject"],
                 "generation_id": p["mm_gen"], "generation_sha256": p["mm_gen_sha"],
                 "query_cutoff": p["mm_cutoff"]}
        try:
            saved = incumbent.retained_saved_for_user(root, "member", exact)
        except HTTPException as exc:
            # Seven immediate reads hit the incumbent six/minute user bucket.
            # Advance this fixture clock past its window, never disable the cap.
            assert exc.status_code == 429 and exc.detail == {"state": "RATE_LIMITED"}
            clock = incumbent.time.monotonic
            monkeypatch.setattr(incumbent.time, "monotonic", lambda: clock() + 61)
            saved = incumbent.retained_saved_for_user(root, "member", exact)
        assert saved["schema"] == "market_memory.retained_saved_output.v1"
        assert card["packet_sha256"] in json.dumps(saved)
        assert card["context_id"] in json.dumps(saved)
        assert saved["source_facts"] == card["facts"]
        saved_sources.append(saved)
    node = subprocess.run(["node", "tests/js/market_memory_fitted_citations.test.cjs"],
        cwd=ROOT, input=json.dumps({"links": links, "saved_sources": saved_sources, "catalogs": catalogs}),
        text=True, capture_output=True)
    assert node.returncode == 0, node.stdout + node.stderr


def test_untrusted_request_and_site_denial_precede_native_read(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid input reached native private reader")
    monkeypatch.setattr(persistence, "reproduce_registered_fitted_query", forbidden)
    monkeypatch.setattr(house, "_enforce_current_site_user", lambda user: None)
    for malformed in ({}, None, {"reference": {}, "mode": "historical_hypothetical"},
                      {"user_id": "admin", "reference": {}, "mode": "current_contextual_support"}):
        assert dispatch(ROOT, malformed)["http_status"] == 400
    def denied(user):
        raise HTTPException(403)
    monkeypatch.setattr(house, "_enforce_current_site_user", denied)
    assert dispatch(ROOT, {})["http_status"] == 403


def test_changed_complete_locator_never_creates_or_discloses(complete_query):
    root, request, _, _, _ = complete_query
    for kind in ("sha256", "bytes", "intent", "extra", "mode"):
        bad = copy.deepcopy(request)
        ref = bad["reference"]
        if kind == "sha256": ref["sha256"] = "f" * 64
        elif kind == "bytes": ref["bytes"] += 1
        elif kind == "intent":
            ref["intent"]["k"] = 1
            ref["operation_id"] = "query_" + sha256(cohort.canonical(ref["intent"])).hexdigest()
        elif kind == "extra": ref["value"] = {"available": True}
        else: bad["mode"] = "current_contextual_support"
        denied = dispatch(root, bad)
        assert denied.get("http_status") in (400, 403, 409), denied
        assert "source_cards" not in denied
        assert gateway._extract_citations_brain(messages(bad, denied)) == []


def test_citations_bind_actual_sdk_call_complete_ref_order_and_clocks(complete_query):
    from engine.codex_provider import _ToolUseBlock
    root, request, _, _, _ = complete_query
    value = dispatch(root, request)
    original = messages(request, value)
    expected = gateway._extract_citations_brain(original)
    assert len(expected) == 3
    sdk = copy.deepcopy(original)
    sdk[0]["content"] = [_ToolUseBlock(**sdk[0]["content"][0])]
    assert gateway._extract_citations_brain(sdk) == expected
    for kind in ("name", "input", "duplicate_use", "replayed_use", "duplicate_result", "result_role", "ref",
                 "ordered_cards", "future_clock", "method", "normalizer", "changed_identity", "size"):
        candidate = copy.deepcopy(original)
        block = candidate[0]["content"][0]
        body = json.loads(candidate[1]["content"][0]["content"])
        if kind == "name": block["name"] = "different_tool"
        elif kind == "input": block["input"]["reference"]["sha256"] = "a" * 64
        elif kind == "duplicate_use": candidate[0]["content"].append(copy.deepcopy(block))
        elif kind == "replayed_use": candidate.extend(copy.deepcopy(original))
        elif kind == "duplicate_result": candidate[1]["content"].append(copy.deepcopy(candidate[1]["content"][0]))
        elif kind == "result_role": candidate[1]["role"] = "assistant"
        elif kind == "ref": body["reopen_reference"]["bytes"] += 1
        elif kind == "ordered_cards": body["source_cards"].reverse()
        elif kind == "future_clock": body["source_cards"][0]["clocks"]["captured_at"] = "2026-11-05T00:00:00Z"
        elif kind == "method": body["method"]["eligibility_method_spec"]["mode"] = "wrong"
        elif kind == "normalizer": body["method"]["normalizer_id"] = "wrong"
        elif kind == "changed_identity": body["method"]["normalizer_id"] = "mmfittednormalizer_" + "f" * 64
        else: body["oversize"] = "x" * 65536
        candidate[1]["content"][0]["content"] = json.dumps(body)
        assert gateway._extract_citations_brain(candidate) == [], kind


@pytest.mark.parametrize("streaming", [False, True])
def test_real_sync_and_stream_loops_reopen_complete_tool_and_emit_same_citations(
        complete_query, monkeypatch, streaming):
    from tests.test_brain_gateway import _MockBlock, _MockResponse, _MockClient
    from app import paywall
    from engine.neuralweb import ask_brain
    root, request, _, _, _ = complete_query
    monkeypatch.setattr(paywall, "enforce_site_full", lambda user, **kwargs: None
        if user.get("id") == "member" else (_ for _ in ()).throw(HTTPException(403)))
    monkeypatch.setattr("lib.ai_costs._write_ledger_path", lambda root=None: root_path / "costs.jsonl")
    root_path = root
    assert api.tool_available(root) is True
    full = gateway._all_brain_tool_schemas(root, user_id="member")
    assert wire.TOOL_NAME in {s["name"] for s in full}
    assert wire.TOOL_NAME in ask_brain._FAST_VISIBLE_TOOL_FAMILIES["macro_rates"]
    assert wire.TOOL_NAME not in {s["name"] for s in gateway._all_brain_tool_schemas(root)}
    client = _MockClient([
        _MockResponse([_MockBlock("tool_use", name=wire.TOOL_NAME, input_=request,
                                 id_="fitted_actual_loop")], "tool_use"),
        _MockResponse([_MockBlock("text", "The saved comparison is contextual evidence.")])])
    args = ("Open the saved fitted macro comparison.", "pro", [], {"page": "marketmemory"},
            root, root, "", client, "synthetic-model", 1024, 2)
    if streaming:
        events = [json.loads(item[6:]) for item in gateway._run_brain_loop_stream(
            *args, meta_event={"type": "meta"}, user_id="member") if item.startswith("data: ")]
        done = [event for event in events if event["type"] == "done"]
        assert len(done) == 1, events
        links = done[0]["citations"]
    else:
        _answer, links, _annotations, _history, _usage, _commands, _charts = gateway._run_brain_loop(
            *args, user_id="member")
    assert len(client.calls) == 2
    assert len(links) == 3
    # Actual dispatcher result is carried into the second model round unchanged.
    tool_messages = client.calls[-1]["messages"]
    assert gateway._extract_citations_brain(tool_messages) == links
    payloads = [json.loads(b["content"]) for m in tool_messages for b in m.get("content", [])
                if isinstance(b, dict) and b.get("type") == "tool_result"]
    assert len(payloads) == 1 and payloads[0]["schema"] == wire.SCHEMA


def test_public_tool_guard_keeps_shipped_disabled_purpose_inactive(monkeypatch):
    monkeypatch.setattr(persistence.owner, "INSTALLED_ROOT", ROOT)
    monkeypatch.setattr(persistence, "_load_context", lambda *args: pytest.fail("private read from schema guard"))
    assert api.tool_available(ROOT) is False


def test_final_site_revocation_drops_entire_fitted_response(complete_query, monkeypatch):
    root, request, _, _, _ = complete_query
    project = api.brain.get_fitted_retained_market_context
    def revoked_after_projection(*args, **kwargs):
        value = project(*args, **kwargs)
        def denied(user):
            raise HTTPException(403)
        monkeypatch.setattr(house, "_enforce_current_site_user", denied)
        return value
    monkeypatch.setattr(api.brain, "get_fitted_retained_market_context", revoked_after_projection)
    denied = dispatch(root, request)
    assert denied["http_status"] == 403
    assert "source_cards" not in denied
