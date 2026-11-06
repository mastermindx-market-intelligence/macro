"""Real Earnings entries -> shared factory/client -> pinned synthetic native A/B.

Only source inputs, qualification, credentials, provider responses and R2 are
fixtures. Intake files, locks, parquet, native HTTP/SQLite and close are real.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import Mock, patch

import pandas as pd
import pandas.core.arrays.arrow.extension_types  # noqa: F401
import pytest

from engine import earnings_qual as eq, earnings_transcript_intake as intake
from engine import fabric_inference_client as transport, llm_auth as auth
from engine import provider_production_modes as owner
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_earnings_worker_terminal import worker, _write_terminal_archive


pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired Mastermind8af source required")
SOURCE = "Revenue increased 12%. Gross margin expanded 180 basis points."
_CLIENT = transport.FabricInferenceClient


def score_value():
    return {"sentiment": 0.5, "performance": 7.0, "confidence": 0.8,
            "tone_word": "steady", "summary": "Revenue increased 12%. Gross margin expanded 180 basis points.",
            "positive_highlights": ["Revenue increased 12%."], "negative_highlights": [],
            "tags": ["margin_expansion"]}


def packet(value=None, *, finish="stop", model=MODEL):
    value = score_value() if value is None else value
    return {"model": model, "choices": [{"index": 0, "finish_reason": finish,
        "message": {"role": "assistant", "content": value if type(value) is str else json.dumps(value)}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}


@pytest.fixture
def earnings(selected, monkeypatch):
    state = selected
    state.manifest["capabilities"][0]["allowed_lanes"].append("earnings-qual")
    state.save()
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    state.cfg = {**copy.deepcopy(eq._DEFAULT_CFG), "max_tokens": 128, "daily_cap": 8}
    state.path = eq.earnings_state_path(state.root)
    state.origin = "local:" + str((state.root / "transcripts").resolve())
    state.closes = []
    state.publications = []
    monkeypatch.setattr(eq, "_dispatch", Mock(side_effect=AssertionError("native dispatch")))
    monkeypatch.setattr(eq, "load_config", lambda *a, **kw: state.cfg)
    monkeypatch.setattr(worker, "_fetch_remote_first", lambda *a, **kw: "fixture-etag")
    monkeypatch.setattr(worker, "_publish", lambda *a, **kw: state.publications.append(kw))
    original_close = _CLIENT.close
    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)
    monkeypatch.setattr(_CLIENT, "close", close)
    state.native.response = packet()
    return state


def call(state, **changes):
    values = {"text": SOURCE, "ticker": "FIX", "quarter": "Q3", "year": 2026,
        "cfg": state.cfg, "provider_cfg": {}, "call_date": "2026-08-01", "source": "transcript",
        "source_record_id": "source:FIX:2026Q3", "source_updated_at": "2026-08-02T00:00:00Z",
        "source_url": "https://fixture.invalid/tx/FIX/2026Q3.json.gz", "source_revision_sha256": "a" * 64,
        "root": state.root, "state_path": state.path, "source_origin": state.origin}
    values.update(changes)
    return eq.score_text(**values)


def document(state):
    return json.loads(state.path.read_text())


def entries(state):
    return [entry for record in document(state)["fabric_operations"]["records"].values()
            for entry in record["entries"]]


def assert_one(state, *, calls=1):
    assert len(state.native.posts) == len(state.native.rows("application_requests")) == calls
    assert len(state.native.rows("leases")) == len(state.closes) == 1
    assert len(state.costs) == calls
    assert all(row["model"] == MODEL for row in state.costs)
    assert state.native.rows("leases")[0]["state"] == "released"


def test_public_score_freezes_intent_before_bind_and_preserves_original_result(earnings):
    state = earnings
    def observed():
        entry = entries(state)[0]
        assert entry["state"] == "pending" and entry["steps"][0]["phase"] == "intent"
        assert entry["operation_id"] == state.native.pending_at_send[0][0]["turn_id"]
        assert entry["base_row"]["source_url"].startswith("https://fixture.invalid/")
    state.native.on_upstream = observed
    first = call(state)
    assert not first["degraded_reason"] and first["model"] == MODEL
    assert first["is_context_only"] and first["prompt_version"] == eq.resolve_prompt_version(state.cfg)
    assert not document(state)["initialized"] and document(state)["source"] == ""
    assert document(state)["known"] == {} and document(state)["pending"] == []
    assert entries(state)[0]["receipt"]["usage"]["input_tokens"] == 11
    assert_one(state)
    effects = list(state.events)
    assert call(state, source_updated_at="2026-11-01T00:00:00Z") == first
    assert state.events == effects
    assert_one(state)


def test_one_deliberate_json_repair_keeps_account_turn_and_two_original_steps(earnings):
    state = earnings
    def observed():
        number = len(state.native.posts)
        entry = entries(state)[0]
        assert len(entry["steps"]) == number and entry["steps"][-1]["phase"] == "intent"
        if number == 2:
            assert entry["steps"][0]["phase"] == "complete"
        state.native.response = packet("not JSON" if number == 1 else score_value())
    state.native.on_upstream = observed
    row = call(state)
    assert not row["degraded_reason"]
    entry = entries(state)[0]
    assert [step["request_id"] for step in entry["steps"]] == [entry["operation_id"] + ":brain:0", entry["operation_id"] + ":brain:1"]
    assert entry["receipt"]["usage"]["input_tokens"] == 22
    sent = [json.loads(p[1]) for p in state.native.posts]
    assert sent[1]["messages"][-1]["content"] == sent[0]["messages"][-1]["content"] + eq._RETRY_SUFFIX
    assert {p[2] for p in state.native.posts} == {"Bearer fixture-provider-a"}
    assert_one(state, calls=2)
    assert call(state) == row
    assert_one(state, calls=2)


@pytest.mark.parametrize("invalid", ["missing", "bool", "nan", "infinity", "range", "tone", "tags", "contradiction", "highlights", "summary", "extra", "duplicate"])
def test_whole_score_schema_gets_only_one_repair_then_terminal_failure(earnings, invalid):
    value = score_value()
    if invalid == "missing": value.pop("summary")
    elif invalid == "bool": value["confidence"] = True
    elif invalid == "nan": value["performance"] = float("nan")
    elif invalid == "infinity": value["performance"] = float("inf")
    elif invalid == "range": value["performance"] = 10.1
    elif invalid == "tone": value["tone_word"] = "invented"
    elif invalid == "tags": value["tags"] = ["invented"]
    elif invalid == "contradiction": value["tags"] = ["guidance_raised", "guidance_lowered"]
    elif invalid == "highlights": value["positive_highlights"] = ["one"] * 4
    elif invalid == "summary": value["summary"] = ""
    elif invalid == "extra": value["trade"] = "invented"
    elif invalid == "duplicate": value = json.dumps(value).replace('"sentiment": 0.5', '"sentiment": 0.5, "sentiment": 0.2')
    earnings.native.response = packet(value)
    row = call(earnings)
    assert row["degraded_reason"] == "invalid_json_or_score_schema"
    assert entries(earnings)[0]["state"] == "terminal" and entries(earnings)[0]["result"] is None
    assert call(earnings) == row
    assert_one(earnings, calls=2)


@pytest.mark.parametrize("outcome", ["429", "503", "mismatch", "protocol", "empty", "refusal", "tools", "truncated", "receipt_only", "timeout", "local_typeerror"])
def test_protocol_or_transport_failure_never_repairs_or_falls_back(earnings, monkeypatch, outcome):
    state = earnings
    if outcome in ("429", "503"):
        state.native.response_status = int(outcome)
    elif outcome == "mismatch": state.native.response = packet(model="observed-other-model")
    elif outcome == "protocol": state.native.response = b'{"model":'
    elif outcome == "empty": state.native.response = packet("")
    elif outcome == "refusal": state.native.response["choices"][0]["message"]["refusal"] = "fixture refusal"
    elif outcome == "tools":
        state.native.response["choices"][0].update(finish_reason="tool_calls", message={"role": "assistant", "content": None,
            "tool_calls": [{"id": "tool-1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]})
    elif outcome == "truncated": state.native.response = packet(finish="length")
    elif outcome in ("receipt_only", "timeout", "local_typeerror"):
        def fail(client, *a, **kw):
            if outcome == "local_typeerror": raise TypeError("fixture local error")
            if outcome == "timeout": raise TimeoutError("fixture original timeout")
            raise transport.FabricInferenceError("fabric_terminal_receipt_only", effect_unknown=False,
                disposition="terminal_receipt_only", request_id=kw.get("request_id"))
        monkeypatch.setattr(_CLIENT, "create", fail)
    row = call(state)
    assert row["degraded_reason"]
    original_posts = len(state.native.posts)
    assert original_posts <= 1 and len(entries(state)[0]["steps"]) == 1
    call(state)
    assert len(state.native.posts) == original_posts and len(state.closes) == 1
    assert len(state.events) == 2
    if outcome in ("429", "503", "mismatch"):
        assert len(state.costs) == 1 and entries(state)[0]["receipt"]["usage"]["input_tokens"] == 11
        assert row["model"] == ("observed-other-model" if outcome == "mismatch" else MODEL)


def test_unknown_settlement_holds_original_before_selector_or_corrected_input(earnings, monkeypatch):
    state = earnings
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture lost settlement")):
        row = call(state)
    assert row["degraded_reason"] and entries(state)[0]["state"] == "held"
    receipt = entries(state)[0]["receipt"]
    assert receipt["usage"]["input_tokens"] is None and receipt["usage"]["completed_input_tokens"] == 11
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    repeated = call(state, text=SOURCE + " Correction.", source_revision_sha256="b" * 64,
                    cfg={**state.cfg, "workload_profile": None, "max_chars": 1})
    assert repeated["degraded_reason"] == "fabric_original_held"
    assert repeated["source_revision_sha256"] == "a" * 64
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1


def test_concurrent_processes_use_one_actual_provider_invocation(earnings):
    state = earnings
    state.native.block = threading.Event()
    program = '''import json,sys
from pathlib import Path
from engine import earnings_qual as eq, provider_production_modes as owner, llm_auth as auth, provider_health
from lib import ai_costs,config
settings=json.loads(sys.argv[1]); costs=[]
owner._APPLICATION_FABRIC_TRANSPORTS["fixture_v1"]=owner._ApplicationFabricTransport(**settings["transport"])
ai_costs.record_usage=lambda **kw:costs.append(kw)
provider_health.record_attempt=lambda **kw:None
def denied(*a,**kw): raise AssertionError("native discovery")
auth._oauth_pool_candidates=denied;config.secret=denied;eq._dispatch=denied
v=settings["call"];v["root"]=Path(v["root"]);v["state_path"]=Path(v["state_path"])
row=eq.score_text(**v)
print(json.dumps({"row":row,"costs":len(costs)}))
'''
    settings = {"transport": asdict(state.transport), "call": {"text": SOURCE, "ticker": "FIX", "quarter": "Q3",
        "year": 2026, "cfg": state.cfg, "root": str(state.root), "state_path": str(state.path),
        "source_origin": state.origin, "source_record_id": "source:FIX:2026Q3", "source_revision_sha256": "a" * 64}}
    command = [sys.executable, "-B", "-c", program, json.dumps(settings)]
    first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    second = None
    try:
        assert state.native.arrived.wait(10)
        second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = second.communicate(timeout=10)
        assert second.returncode == 0, err
        duplicate = json.loads(out)
        assert duplicate["row"]["degraded_reason"] == "fabric_original_held" and duplicate["costs"] == 0
        state.native.block.set()
        out, err = first.communicate(timeout=10)
        assert first.returncode == 0, err
        original = json.loads(out)
        assert not original["row"]["degraded_reason"] and original["costs"] == 1
    finally:
        state.native.block.set()
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill(); process.communicate(timeout=5)
    assert len(state.native.posts) == len(state.native.rows("leases")) == 1
    assert len(entries(state)) == 1 and entries(state)[0]["state"] == "terminal"


@pytest.mark.parametrize("boundary", ["claim", "observe", "repair", "result", "finish"])
def test_lost_persistence_ack_never_rebinds_original(earnings, monkeypatch, boundary):
    state = earnings
    real_save = intake._atomic_write_json
    def save(path, value, **kw):
        real_save(path, value, **kw)
        records = value.get("fabric_operations", {}).get("records", {})
        if not records: return
        entry = next(iter(records.values()))["entries"][0]
        hit = ((boundary == "claim" and len(entry["steps"]) == 1 and entry["steps"][0]["phase"] == "intent")
            or (boundary == "observe" and entry["steps"][0]["phase"] == "complete" and entry["result"] is None)
            or (boundary == "repair" and len(entry["steps"]) == 2 and entry["steps"][-1]["phase"] == "intent")
            or (boundary == "result" and entry["result"] is not None and entry["receipt"] is None)
            or (boundary == "finish" and entry["receipt"] is not None))
        if hit: raise OSError("fixture lost original save ACK")
    monkeypatch.setattr(intake, "_atomic_write_json", save)
    if boundary == "repair": state.native.response = packet("bad JSON")
    row = call(state)
    assert row["degraded_reason"]
    prior_effects = (len(state.events), len(state.native.posts), len(state.costs), len(state.closes))
    monkeypatch.setattr(intake, "_atomic_write_json", real_save)
    repeated = call(state)
    if boundary == "finish": assert not repeated["degraded_reason"]
    else: assert repeated["degraded_reason"] == "fabric_original_held"
    assert (len(state.events), len(state.native.posts), len(state.costs), len(state.closes)) == prior_effects
    assert len(state.native.posts) <= 1


def test_stale_native_snapshot_cannot_erase_or_rewind_original(earnings):
    state = earnings
    stale = intake.new_state("")
    assert not call(state)["degraded_reason"]
    original = document(state)["fabric_operations"]
    intake.save_state(state.path, stale)
    assert document(state)["fabric_operations"] == original
    stale = intake.load_state(state.path, source="")
    call(state, source_revision_sha256="b" * 64, source_url="https://fixture.invalid/corrected")
    current = document(state)["fabric_operations"]
    intake.save_state(state.path, stale)
    assert document(state)["fabric_operations"] == current
    assert len(entries(state)) == 2


@pytest.mark.parametrize("corruption", ["null", "duplicate", "nonfinite", "block", "result", "result_digest", "receipt_model", "receipt_usage", "close", "step", "source"])
def test_corrupt_nested_original_refuses_before_parquet_or_another_model(earnings, monkeypatch, corruption):
    state = earnings
    assert not call(state)["degraded_reason"]
    value = document(state)
    entry = next(iter(value["fabric_operations"]["records"].values()))["entries"][0]
    if corruption == "null": raw = "null"
    elif corruption == "duplicate": raw = json.dumps(value)[:-1] + ',"schema":"changed"}'
    elif corruption == "nonfinite": raw = json.dumps(value)[:-1] + ',"bad":NaN}'
    else:
        if corruption == "block": value["fabric_operations"] = None
        elif corruption == "result":
            entry["result"]["performance"] = True
            entry["result_digest"] = intake.fabric_digest(entry["result"])
        elif corruption == "result_digest": entry["result_digest"] = "0" * 64
        elif corruption == "receipt_model": entry["receipt"]["served_model"] = "invented"
        elif corruption == "receipt_usage": entry["receipt"]["usage"]["completed_input_tokens"] = 0
        elif corruption == "close": entry["receipt"]["close"]["closed"] = False
        elif corruption == "step": entry["steps"][0]["request_id"] = "different:brain:0"
        elif corruption == "source": entry["result"]["source_url"] = "https://invented.invalid"
        raw = json.dumps(value)
    state.path.write_text(raw)
    monkeypatch.setattr(eq, "upsert_scores", Mock(side_effect=AssertionError("corrupt result promoted")))
    row = call(state)
    assert row["degraded_reason"]
    assert len(state.native.posts) == 1
    with pytest.raises(ValueError): intake.save_state(state.path, intake.new_state(""))


@pytest.mark.parametrize("profile", [None, "", "development_agent", "unknown"])
def test_invalid_explicit_profile_is_not_replaced_by_batch(earnings, profile):
    row = call(earnings, cfg={**earnings.cfg, "workload_profile": profile})
    assert row["degraded_reason"] and earnings.events == earnings.native.posts == []


@pytest.mark.parametrize("change", ["caller_null", "caller_conflict", "two_configs", "profile_conflict", "sink_conflict", "missing_context", "bad_bound", "empty"])
def test_selected_preintent_gates_have_zero_effects(earnings, change):
    changes = {}
    if change == "caller_null": changes["cfg"] = {**earnings.cfg, "application_fabric_mode": None}
    elif change == "caller_conflict": changes["cfg"] = {**earnings.cfg, "application_fabric_mode": "other_mode"}
    elif change == "two_configs": changes.update(cfg={**earnings.cfg, "application_fabric_mode": "shared_fabric"}, provider_cfg={"application_fabric_mode": None})
    elif change == "profile_conflict": changes.update(cfg={**earnings.cfg, "workload_profile": "site_batch"}, provider_cfg={"workload_profile": "site_interactive"})
    elif change == "sink_conflict": changes.update(cfg={**earnings.cfg, "usage_sink": "none"}, provider_cfg={"usage_sink": None})
    elif change == "missing_context": changes["root"] = None
    elif change == "bad_bound": changes["cfg"] = {**earnings.cfg, "max_tokens": True}
    elif change == "empty": changes["text"] = ""
    assert call(earnings, **changes)["degraded_reason"]
    assert earnings.events == earnings.native.posts == earnings.costs == []


def test_actual_caller_profile_intersects_batch_startup_and_usage_sink(earnings):
    cfg = {**earnings.cfg, "workload_profile": "site_interactive", "usage_sink": "none"}
    row = call(earnings, cfg=cfg)
    assert not row["degraded_reason"] and earnings.costs == []
    policy = entries(earnings)[0]["inspection"]["workload_policy"]
    assert "site_batch" in json.dumps(policy) and "site_interactive" in json.dumps(policy)
    assert len(earnings.native.posts) == 1


def test_changed_inspection_between_inspect_and_bind_refuses_without_credential(earnings, monkeypatch):
    original = owner.ApplicationFabricFactory.inspect
    def inspect(factory, *a, **kw):
        identity = original(factory, *a, **kw)
        changed = replace(earnings.transport, cap_id="fixture:changed")
        monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", changed)
        earnings.row["cap_id"] = changed.cap_id
        earnings.save()
        return identity
    monkeypatch.setattr(owner.ApplicationFabricFactory, "inspect", inspect)
    assert call(earnings)["degraded_reason"]
    assert earnings.events == earnings.native.posts == []


def test_unsupported_strict_persistence_refuses_claim_and_preserves_existing_block(earnings, monkeypatch):
    real_sync = intake._sync_state_directory
    def unsupported(path, *, strict):
        if strict: raise OSError("fixture unsupported strict directory sync")
        return real_sync(path, strict=False)
    monkeypatch.setattr(intake, "_sync_state_directory", unsupported)
    assert call(earnings)["degraded_reason"] and earnings.events == []
    intake.save_state(earnings.path, intake.new_state(""))
    assert "fabric_operations" not in document(earnings)
    monkeypatch.setattr(intake, "_sync_state_directory", real_sync)
    assert not call(earnings)["degraded_reason"]
    prior = earnings.path.read_bytes()
    monkeypatch.setattr(intake, "_sync_state_directory", unsupported)
    with pytest.raises(OSError): intake.save_state(earnings.path, intake.new_state(""))
    assert earnings.path.read_bytes() == prior


def test_state_parent_symlink_does_not_hide_original_or_enable_native_fallback(earnings, monkeypatch, tmp_path):
    state = earnings
    assert not call(state)["degraded_reason"]
    data = state.root / "data"
    saved = state.root / "saved-data"
    data.rename(saved)
    outside = tmp_path / "outside"
    outside.mkdir()
    data.symlink_to(outside, target_is_directory=True)
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert call(state)["degraded_reason"]
    assert len(state.native.posts) == 1 and list(outside.iterdir()) == []


def flat_source(state, *, directory=None, ticker="FIX", revision="a" * 64):
    directory = directory or state.root / "data/earnings_calls/transcripts"
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"ticker": ticker, "quarter": "Q3", "year": 2026, "text": SOURCE,
        "source_record_id": "source:" + ticker + ":2026Q3", "source_updated_at": "2026-08-02T00:00:00Z",
        "call_date": "2026-08-01", "source_revision_sha256": revision,
        "terminal_url": "https://fixture.invalid/tx/" + ticker + "/2026Q3.json.gz"}
    (directory / (ticker + ".json")).write_text(json.dumps(payload))
    return directory, payload


@pytest.mark.parametrize("route", ["score_new", "worker_default", "worker_custom", "worker_ticker", "eight_k"])
def test_all_flat_public_entries_forward_root_state_origin_and_revision(earnings, monkeypatch, route):
    state = earnings
    directory, payload = flat_source(state, directory=state.root / "custom" if route in ("worker_custom", "worker_ticker") else None)
    state.path = state.root / "custom-intake.json"
    if route == "eight_k":
        payload["source"] = "8k"
        payload["source_url"] = "https://fixture.invalid/edgar/filing"
        monkeypatch.setattr(eq, "_iter_8k_inputs", lambda *a, **kw: iter([(payload, SOURCE)]))
    def run():
        if route in ("score_new", "eight_k"):
            return eq.score_new(root=state.root, source="8k" if route == "eight_k" else "transcript",
                limit=1, cfg=state.cfg, state_path=state.path)
        return worker.run(tickers=["FIX"], transcripts_dir=directory, repo_root=state.root,
            provider_cfg={"openai_compat": {"base_url": "http://invalid.invalid", "model": "native"}},
            limit=1, do_publish=True, auto=route != "worker_ticker", state_path=state.path)
    assert run() == 1
    rows = eq.load_scores(state.root)
    assert len(rows) == 1 and rows.iloc[0]["model"] == MODEL
    assert rows.iloc[0]["source_revision_sha256"] == "a" * 64
    record = next(iter(document(state)["fabric_operations"]["records"].values()))
    expected = "edgar:earnings-8k:" + str(state.root.resolve()) if route == "eight_k" else "local:" + str(directory.resolve())
    assert record["source"]["origin"] == expected
    assert record["entries"][0]["result"]["source_url"] == (payload.get("source_url") if route == "eight_k" else payload["terminal_url"])
    assert run() == 0
    assert_one(state)


def terminal_source(state):
    tx = state.root / "tx"
    _write_terminal_archive(tx, text=SOURCE)
    state.origin = "local:" + str(tx.resolve())
    return tx


def terminal_run(state, tx, **changes):
    kwargs = {"repo_root": state.root, "provider_cfg": {}, "limit": 8, "do_publish": True,
        "base_url": "unused", "tx_root": tx, "state_path": state.path,
        "bootstrap_since": "2026-07-24", "seed_existing": False}
    kwargs.update(changes)
    return worker.run_terminal(**kwargs)


def test_terminal_public_path_persists_model_citations_and_original_before_ack(earnings):
    state = earnings
    tx = terminal_source(state)
    assert terminal_run(state, tx) == 1
    saved = document(state)
    assert saved["pending"] == [] and saved["source"] == state.origin
    score = eq.load_scores(state.root).iloc[0]
    assert score["source_record_id"] == "defeatbeta:AAPL:2026Q3" and score["model"] == MODEL
    assert score["source_url"] == "https://app.mastermind-x.com/data/tx/AAPL/2026Q3.json.gz"
    assert entries(state)[0]["result"]["source_revision_sha256"] == score["source_revision_sha256"]
    assert state.publications[-1] == {"expected_manifest_etag": "fixture-etag"}
    assert terminal_run(state, tx) == 0
    assert_one(state)


@pytest.mark.parametrize("boundary", ["parquet", "mark_completed"])
def test_saved_result_recovers_delivery_with_zero_model_or_usage(earnings, monkeypatch, boundary):
    state = earnings
    tx = terminal_source(state)
    target, name = (eq, "upsert_scores") if boundary == "parquet" else (intake, "mark_completed")
    original = getattr(target, name)
    monkeypatch.setattr(target, name, Mock(side_effect=OSError("fixture delivery interruption")))
    with pytest.raises(OSError): terminal_run(state, tx)
    row = copy.deepcopy(entries(state)[0]["result"])
    assert row and entries(state)[0]["state"] == "terminal"
    effects = list(state.events)
    monkeypatch.setattr(target, name, original)
    assert terminal_run(state, tx) == (1 if boundary == "parquet" else 0)
    saved = eq.load_scores(state.root).iloc[0]
    assert saved["scored_at"] == row["scored_at"] and saved["source_url"] == row["source_url"]
    assert document(state)["pending"] == [] and state.events == effects
    assert_one(state)


def test_terminal_same_text_metadata_correction_cannot_clear_prior_uncertainty(earnings, monkeypatch):
    state = earnings
    tx = terminal_source(state)
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture ambiguous settlement")):
        assert terminal_run(state, tx) == 0
    original = copy.deepcopy(entries(state)[0])
    _write_terminal_archive(tx, text=SOURCE, call_date="2026-07-31")
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert terminal_run(state, tx) == 0
    assert entries(state) == [original]
    pending = document(state)["pending"]
    assert len(pending) == 1 and pending[0]["body_sha256"] != original["revision"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert eq.load_scores(state.root).empty


def test_terminal_stale_completion_cannot_erase_concurrently_corrected_pending(earnings, monkeypatch):
    state = earnings
    tx = terminal_source(state)
    real_upsert = eq.upsert_scores
    corrected = None
    def upsert(rows, **kw):
        nonlocal corrected
        result = real_upsert(rows, **kw)
        _write_terminal_archive(tx, text=SOURCE, call_date="2026-07-31")
        refs, metadata = intake.parse_global_index(json.loads((tx / "index.json").read_text()))
        corrected = refs[0].body_sha256
        intake.transact_state(state.path, source=state.origin,
            change=lambda current: intake.plan_index(refs, current, metadata=metadata))
        return result
    monkeypatch.setattr(eq, "upsert_scores", upsert)
    assert terminal_run(state, tx) == 1
    assert document(state)["pending"][0]["body_sha256"] == corrected
    assert len(entries(state)) == 1


@pytest.mark.parametrize("gate", ["seed", "future", "bad_hash", "cap", "hydrate"])
def test_terminal_and_batch_pre_model_gates_remain_zero_effect(earnings, monkeypatch, gate):
    state = earnings
    tx = terminal_source(state)
    changes = {}
    if gate == "seed": changes["bootstrap_since"] = None
    elif gate == "future": _write_terminal_archive(tx, call_date="2099-01-01")
    elif gate == "bad_hash":
        index = json.loads((tx / "index.json").read_text())
        index["revisions"]["AAPL/2026Q3"] = "f" * 64
        (tx / "index.json").write_text(json.dumps(index))
    elif gate == "cap": changes["limit"] = 0
    elif gate == "hydrate": monkeypatch.setattr(worker, "_fetch_remote_first", lambda *a, **kw: False)
    assert terminal_run(state, tx, **changes) == (-1 if gate == "hydrate" else 0)
    assert state.events == state.native.posts == state.costs == []
    if gate == "hydrate": assert not state.path.exists()
    elif state.path.exists(): assert "fabric_operations" not in document(state)


def test_strict_state_duplicate_keys_and_nonfinite_are_not_absence(tmp_path):
    path = tmp_path / "state.json"
    for content in ('{"schema":"x","schema":"y"}', '{"value":NaN}', "null", "[]"):
        path.write_text(content)
        with pytest.raises(ValueError): intake.load_state(path, source="test")


def test_local_cleaner_typeerror_after_valid_json_cannot_authorize_repair(earnings, monkeypatch):
    monkeypatch.setattr(eq, "_clean_highlights", Mock(side_effect=TypeError("fixture local formatter failure")))
    row = call(earnings)
    assert row["degraded_reason"]
    assert len(entries(earnings)[0]["steps"]) == 1
    assert len(earnings.native.posts) == len(earnings.costs) == len(earnings.closes) == 1
    assert entries(earnings)[0]["state"] == "terminal"


def test_failed_repair_uses_its_actual_observed_model_not_first_response(earnings):
    def observed():
        earnings.native.response = (packet("invalid JSON") if len(earnings.native.posts) == 1
                                    else packet(model="observed-repair-model"))
    earnings.native.on_upstream = observed
    row = call(earnings)
    assert row["degraded_reason"] and row["model"] == "observed-repair-model"
    record = entries(earnings)[0]
    assert record["receipt"]["served_model"] == "observed-repair-model"
    assert [step["observation"]["serving_model"] for step in record["steps"]] == [MODEL, "observed-repair-model"]
    assert [cost["model"] for cost in earnings.costs] == [MODEL, "observed-repair-model"]
    assert record["receipt"]["usage"]["input_tokens"] == 22 and record["state"] == "terminal"
    call(earnings)
    assert len(earnings.native.posts) == 2 and len(earnings.closes) == 1


@pytest.mark.parametrize("route", ["flat", "terminal"])
@pytest.mark.parametrize("custom_state", [False, True])
def test_main_relative_root_and_state_resolve_one_existing_owner(earnings, monkeypatch, route, custom_state):
    state = earnings
    if route == "flat": flat_source(state)
    else: tx = terminal_source(state)
    monkeypatch.chdir(state.root.parent)
    arguments = ["--repo-root", state.root.name, "--no-publish", "--limit", "1"]
    if route == "flat": arguments += ["--auto"]
    else: arguments += ["--terminal-auto", "--terminal-tx-root", str(tx), "--bootstrap-since", "2026-07-24"]
    if custom_state:
        state.path = state.root.parent / (state.root.name + "-intake.json")
        arguments += ["--terminal-state", state.path.name]
    assert worker.main(arguments) == 0
    saved = document(state)
    assert len(entries(state)) == 1
    assert saved["initialized"] == (route == "terminal")
    assert not (state.root / state.root.name).exists()
    assert_one(state)


def test_unknown_close_keeps_saved_answer_separate_from_release(earnings, monkeypatch):
    state = earnings
    def close(client):
        state.closes.append(client.operation_id)
        return {"disposition": "effect_unknown", "closed": False, "effect_unknown": True, "attempted": True}
    monkeypatch.setattr(_CLIENT, "close", close)
    row = call(state)
    record = entries(state)[0]
    assert row["degraded_reason"] and record["state"] == "held"
    assert record["result"]["model"] == MODEL and record["result"]["performance"] == 7
    assert record["receipt"]["usage"]["input_tokens"] == 11
    call(state)
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 1


def test_partial_usage_retains_unknown_total_and_actual_answer_without_extra_cost(earnings):
    earnings.native.response["usage"] = {"prompt_tokens": 11}
    row = call(earnings)
    assert not row["degraded_reason"] and row["model"] == MODEL
    record = entries(earnings)[0]
    assert record["receipt"]["usage"]["usage_state"] == "unknown"
    assert record["receipt"]["usage"]["input_tokens"] is None
    assert record["steps"][0]["observation"]["input_tokens"] == 11
    assert record["steps"][0]["observation"]["output_tokens"] is None
    call(earnings)
    assert len(earnings.native.posts) == len(earnings.closes) == 1
    assert earnings.costs == []
    value = document(earnings)
    original = next(iter(value["fabric_operations"]["records"].values()))["entries"][0]
    original["receipt"]["usage"].update(usage_state="known", input_tokens=0, output_tokens=0)
    earnings.path.write_text(json.dumps(value))
    before = (len(earnings.events), len(earnings.native.posts), len(earnings.closes))
    assert call(earnings)["degraded_reason"] == "fabric_original_refused"
    assert (len(earnings.events), len(earnings.native.posts), len(earnings.closes)) == before
    assert earnings.costs == []


@pytest.mark.parametrize("change", ["source_record_id", "origin"])
def test_rekeyed_held_record_is_corruption_not_absent_original(earnings, change):
    state = earnings
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture ambiguous settlement")):
        assert call(state)["degraded_reason"]
    value = document(state)
    record = next(iter(value["fabric_operations"]["records"].values()))
    record["source"][change] = "different-original-source"
    value["fabric_operations"]["records"] = {intake.fabric_digest(record["source"]): record}
    state.path.write_text(json.dumps(value))
    before = len(state.events)
    assert call(state)["degraded_reason"] == "fabric_original_refused"
    assert len(state.events) == before and len(state.native.posts) == 1


def test_matching_healthy_parquet_cannot_ack_a_held_corrected_original(earnings, monkeypatch):
    state = earnings
    tx = terminal_source(state)
    assert terminal_run(state, tx) == 1
    old = copy.deepcopy(entries(state)[0]["result"])
    _write_terminal_archive(tx, text=SOURCE, call_date="2026-07-31")
    with patch.object(state.native.gateway, "complete_application", side_effect=OSError("fixture ambiguous correction")):
        assert terminal_run(state, tx) == 0
    held = copy.deepcopy(entries(state)[1])
    assert held["state"] == "held"
    # An independently existing healthy product row is not settlement evidence.
    old["source_revision_sha256"] = held["revision"]
    old["call_date"] = "2026-07-31"
    eq.upsert_scores([old], root=state.root)
    assert eq._completed_record_shas(state.root)[old["source_record_id"]] == held["revision"]
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert terminal_run(state, tx) == 0
    assert entries(state)[1] == held and len(document(state)["pending"]) == 1
    assert len(state.native.posts) == len(state.costs) == len(state.closes) == 2
