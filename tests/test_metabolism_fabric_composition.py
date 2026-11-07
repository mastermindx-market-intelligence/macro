"""Incumbent Metabolism state/row owners through actual Macro and native A/B.

Only qualified fixture grants/credentials, PostgREST rows and provider responses
are synthetic. Shared factory/auth/client, HTTP, broker, usage and business
writers are real. The existing twelve source pins remain enforced by native.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import pandas.core.arrays.arrow.extension_types  # noqa: F401

from scripts import metabolism_journal as journal, metabolism_dream as dream
from scripts import run_trade_memory as trade_runner
from engine.metabolism import memory
from engine.metabolism import insight_bus  # Loaded before native fixture module cleanup.
from engine.metabolism import propose, adjudicate, agenda, attention, audit
from scripts import metabolism_propose as propose_cli, metabolism_adjudicate as adjudicate_cli
from scripts import metabolism_agenda as agenda_cli, metabolism_attention as attention_cli
from scripts import metabolism_shadow_cycle as shadow
from scripts import preflight_claude_auth, metabolism_budget
from engine.metabolism import standout_auditor as standout
from engine.neuralweb import trade_memory as trade
from engine.neuralweb import trade_memory_store as private
from engine import llm_auth as auth, provider_production_modes as modes
from engine import fabric_inference_client as transport
from engine import provider_health
from lib import ai_costs
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native_fixture, selected, MODEL  # noqa: F401
from tests.test_fabric_exact_scoped_model_composition import NATIVE_PINS
from tests.test_trade_memory import _episode, _autopsy_json

_USAGE_WRITER = ai_costs.record_usage
_CLIENT = transport.FabricInferenceClient
_HEALTH_WRITER = provider_health.record_attempt
OWNER = "123e4567-e89b-42d3-a456-426614174000"
EPISODE = "123e4567-e89b-42d3-a456-426614174001"


def packet(text, *, usage=True, finish="stop"):
    value = {"model": MODEL, "choices": [{"index": 0, "finish_reason": finish,
        "message": {"role": "assistant", "content": text}}]}
    if usage:
        value["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
    return value


def autopsy_json():
    value = json.loads(_autopsy_json())
    for item in value["signal_hypotheses"]:
        item["authority"] = "research_only"
    return json.dumps(value)


@pytest.fixture
def native():
    source_root = os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT")
    if not source_root:
        pytest.skip("paired current Mastermind source required")
    # Reuse the current exact pin owner, retaining the fixed-Go/VPS fixture,
    # purpose-specific grants and actual broker/HTTP/accounting behavior.
    yield from native_fixture(source_root, NATIVE_PINS,
                              module_name="_metabolism_current_native_pair")


@pytest.fixture
def metabolism(selected, request, monkeypatch, tmp_path_factory):
    state = selected
    purpose = getattr(request, "param", "lobe_analysis")
    state.purpose = purpose
    state.native.grant["workloads"] = [purpose]
    state.native.save()
    service = state.native.go.ApplicationServiceBinding("macro", "vps", purpose,
        state.native.service.credential_ref, state.native.service.credential)
    server = state.native.go.make_server(state.native.router, lease_gateway=state.native.gateway,
                                         application_services=(service,))
    state.native.service, state.native.server = service, server
    state.native._serve(server)
    recipe = replace(state.transport, base_url=f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setitem(modes._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", recipe)
    state.row.update({key: getattr(recipe, key) for key in modes._APPLICATION_IDENTITY_FIELDS})
    state.manifest["capabilities"][0]["allowed_lanes"].extend(
        "metabolism-" + kind.replace("_", "-") for kind in journal._PURPOSES)
    state.save()
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", purpose)
    monkeypatch.setenv("AUTONOMY_PAUSED", "false")
    monkeypatch.setattr(auth, "deliberation_model", Mock(side_effect=AssertionError("legacy model discovery")))
    state.usage_root = tmp_path_factory.mktemp("metabolism-usage")
    state.cost_path = state.usage_root / "data/ai_costs/usage.jsonl"
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(state.usage_root))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(state.usage_root/"provider-health.json"))
    monkeypatch.setattr(provider_health, "record_attempt", _HEALTH_WRITER)
    state.native.response = packet("Earlier lessons favor bounded experiments and explicit failure records.")
    state.closes = []
    original_close = _CLIENT.close
    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)
    monkeypatch.setattr(_CLIENT, "close", close)
    return state


def usages(state):
    return [json.loads(line) for line in state.cost_path.read_text().splitlines()] if state.cost_path.exists() else []


def operations(root, owner="journal", unit="dream-resummary"):
    return list(journal._records(journal.read_owner_state(root, owner, unit)).values())


def seed_lessons(root):
    path = root / "data/metabolism/lessons.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"schema": memory.SCHEMA_LESSONS, "cycle_id": "old-"+str(i),
             "what_worked": ("DISCARDED_PREFIX" if i == 0 else "older") + "x"*1100}
            for i in range(65)]
    rows[-1]["what_worked"] = "RETAINED_TAIL_ONLY" + "x"*1100
    path.write_text("".join(json.dumps(row)+"\n" for row in rows))
    return path, path.read_bytes()


def invocation(state, *, unit="unit-a", kind="dream", scope=None):
    return journal.FabricInvocation(state.root, kind, unit, {"source": "fixture-v1"},
        scope or ["lessons"], "Explain this bounded fixture.", "The supplied fixture has one observation.", 800)


def test_dream_public_main_summarizes_actual_discarded_prefix_and_closes(metabolism):
    state = metabolism
    path, before = seed_lessons(state.root)
    seen = []
    def upstream():
        record = operations(state.root)[0]
        assert record["state"] == "claimed"
        assert record["operation_id"] in {row["turn_id"] for row in state.native.pending_at_send[-1]}
        lock = path.parent / "journal/.journal-owner.lock"
        fd = os.open(lock, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
        sent = json.dumps(json.loads(state.native.posts[-1][1]))
        assert "DISCARDED_PREFIX" in sent and "RETAINED_TAIL_ONLY" not in sent
        seen.append(record["operation_id"])
    state.native.on_upstream = upstream
    assert dream.main(["--root", str(state.root)]) == 0
    record = operations(state.root)[0]
    assert record["state"] == "complete" and len(seen) == 1
    assert record["receipt"]["served_model"] == MODEL
    assert record["receipt"]["usage"]["input_tokens"] == 11
    assert record["receipt"]["close"]["closed"] is True
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 1
    after = path.read_bytes()
    summary = json.loads(after.splitlines()[0])
    assert len(after) < len(before) and b"RETAINED_TAIL_ONLY" in after
    assert summary["source_coverage"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert record["business"]["outcome"]["receipt"]["result_sha256"] == hashlib.sha256(after).hexdigest()
    dream.main(["--root", str(state.root)])
    assert len(state.native.posts) == len(usages(state)) == 1


def test_dream_source_append_during_inference_holds_publication(metabolism):
    state = metabolism
    path, before = seed_lessons(state.root)
    def upstream():
        assert memory.append_lesson("new-source", "failed", "", "new fact", "fixture", root=state.root)
    state.native.on_upstream = upstream
    dream._maybe_resummary(state.root, False)
    record = operations(state.root)[0]
    assert record["state"] == "held" and record["text"]
    assert path.read_bytes().startswith(before) and b"new-source" in path.read_bytes()
    assert len(state.native.posts) == 1
    dream._maybe_resummary(state.root, False)
    assert len(state.native.posts) == 1


def test_known_response_is_saved_before_close_unknown_and_selector_removal(metabolism, monkeypatch):
    state = metabolism
    path, before = seed_lessons(state.root)
    def uncertain(_):
        record = operations(state.root)[0]
        assert record["state"] == "observed" and record["text"]
        assert record["receipt"]["observation"]["input_tokens"] == 11
        raise OSError("synthetic close acknowledgment loss")
    monkeypatch.setattr(_CLIENT, "close", uncertain)
    dream._maybe_resummary(state.root, False)
    record = operations(state.root)[0]
    assert record["state"] == "held" and record["text"]
    assert record["receipt"]["usage"]["completed_input_tokens"] == 11
    assert path.read_bytes() == before
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    monkeypatch.setattr(dream, "_request_llm_summary", Mock(side_effect=AssertionError("native fallback")))
    dream._maybe_resummary(state.root, False)
    assert len(state.native.posts) == len(usages(state)) == 1 and path.read_bytes() == before


@pytest.mark.parametrize("failure", ["truncated", "empty", "missing_usage"])
def test_dream_response_and_nullable_usage_contract(metabolism, failure):
    state = metabolism
    path, before = seed_lessons(state.root)
    state.native.response = packet("" if failure == "empty" else "Bounded memory summary.",
        usage=failure != "missing_usage", finish="length" if failure == "truncated" else "stop")
    dream._maybe_resummary(state.root, False)
    record = operations(state.root)[0]
    if failure == "missing_usage":
        assert record["state"] == "complete"
        assert record["receipt"]["usage"]["usage_state"] == "unknown"
        assert record["receipt"]["observation"]["input_tokens"] is None
    else:
        assert record["state"] == "held" and path.read_bytes() == before
    dream._maybe_resummary(state.root, False)
    assert len(state.native.posts) == 1


def test_dream_dry_run_and_oversized_prefix_do_not_bind(metabolism):
    state = metabolism
    path, before = seed_lessons(state.root)
    dream._maybe_resummary(state.root, True)
    assert not state.native.posts and path.read_bytes() == before
    path.write_bytes(before * 3)
    dream._maybe_resummary(state.root, False)
    assert not state.native.posts and path.read_bytes() == before * 3


@pytest.mark.parametrize("bad", [None, [], {"schema": "foreign", "records": {}}])
def test_present_invalid_operation_map_is_never_absence(metabolism, bad):
    state = metabolism
    path = journal.journal_path("unit-a", state.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = journal._default_journal("unit-a")
    value[journal._FABRIC_KEY] = bad
    path.write_text(json.dumps(value))
    original = path.read_bytes()
    with pytest.raises(journal.FabricHeld):
        invocation(state)
    assert not journal._write_journal("unit-a", journal._default_journal("unit-a"), state.root)
    assert not state.native.posts and path.read_bytes() == original


def test_cycle_relabel_cannot_evade_original_claim(metabolism, monkeypatch):
    state = metabolism
    original = invocation(state)
    with pytest.raises(journal.FabricHeld, match="original_held"):
        invocation(state, unit="different-date")
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    with pytest.raises(journal.FabricHeld, match="original_held"):
        journal.guard_saved(state.root, "journal", "third-cycle", "dream", ["lessons"])
    assert operations(state.root, unit="unit-a")[0] == original.record and not state.native.posts


@pytest.mark.parametrize("change", ["corrupt", "nonce", "delete"])
def test_original_claim_is_rechecked_before_bind(metabolism, change):
    state = metabolism
    original = invocation(state)
    path = journal.journal_path("unit-a", state.root)
    if change == "corrupt":
        path.write_text("{")
    elif change == "delete":
        path.unlink()
    else:
        value = json.loads(path.read_text())
        value[journal._FABRIC_KEY]["records"][original.record["operation_id"]]["attempt_nonce"] = "f"*32
        path.write_text(json.dumps(value))
    with pytest.raises(journal.FabricHeld):
        original.call()
    assert not state.native.posts and not usages(state)
    with pytest.raises(journal.FabricHeld, match="send_not_owned"):
        original.call()


def test_legacy_stage_writer_preserves_current_claim_and_completed_reuse(metabolism):
    state = metabolism
    original = invocation(state)
    journal.start_stage("unit-a", "sense", root=state.root)
    assert operations(state.root, unit="unit-a")[0] == original.record
    assert original.call()
    original.publication_intent({"owner": "fixture"})
    original.complete({"status": "fixture"})
    replay = invocation(state)
    assert replay.reused and replay.record == original.record
    with pytest.raises(journal.FabricHeld, match="send_not_owned"):
        replay.call()
    assert len(state.native.posts) == len(usages(state)) == 1


_MISSING = object()


class PostgREST:
    """Stateful row protocol: evaluate filters atomically, then simulate lost ACKs."""
    def __init__(self):
        self.row = {"id": EPISODE, "user_id": OWNER, **trade.normalize_episode(_episode()),
            "autopsy_state": "pending", "evidence_packet": None, "autopsy": None,
            "updated_at": "2026-11-01T00:00:00Z"}
        self.lock = threading.Lock()
        self.calls, self.claims = [], []
        self.loss = set()
        self.read_failure = False
        self.claim_barrier = None
        self.before_claim = None
        self.reply = None
        self.pattern_writes = 0

    @staticmethod
    def response(value, status=200):
        return SimpleNamespace(status_code=status, text=json.dumps(value), json=lambda: copy.deepcopy(value))

    @staticmethod
    def value(row, key):
        parts = re.split(r"->>?", key)
        value = row
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return _MISSING
            value = value[part]
        if value is None and "->" in key and not re.search(r"->>[^>]+$", key):
            return ("json-null",)
        return value

    @classmethod
    def match(cls, row, key, expression):
        value = cls.value(row, key)
        if expression == "is.null":
            return value is _MISSING or value is None
        if expression.startswith("in.("):
            return value in expression[4:-1].split(",")
        if expression.startswith("eq."):
            expected = expression[3:]
            if expected.startswith('"') and expected.endswith('"'):
                expected = re.sub(r'\\(["\\])', r'\1', expected[1:-1])
            elif isinstance(value, (int, float)):
                expected = float(expected)
            if key == "evidence_packet" and isinstance(value, dict):
                expected = json.loads(expected)
            return value == expected
        if expression == "not.is.null":
            return value is not _MISSING and value is not None
        raise AssertionError("unsupported protocol predicate")

    def get(self, url, *, headers, params, timeout):
        self.calls.append(("get", copy.deepcopy(params)))
        assert params["user_id"] == "eq."+OWNER
        if self.read_failure:
            raise TimeoutError("synthetic read loss")
        with self.lock:
            if all(self.match(self.row, key, value) for key, value in params.items()
                   if key not in ("select", "order", "limit")):
                return self.response([copy.deepcopy(self.row)])
            return self.response([])

    def patch(self, url, *, headers, params, data, timeout):
        body = json.loads(data)
        envelope = body.get("evidence_packet", {}).get(private._CLAIM_KEY)
        phase = envelope["record"]["state"] if envelope else "legacy"
        self.calls.append(("patch", copy.deepcopy(params)))
        if phase == "claimed":
            self.claims.append(copy.deepcopy(envelope["record"]))
            if self.claim_barrier is not None:
                self.claim_barrier.wait(5)
        with self.lock:
            if phase == "claimed" and self.before_claim is not None:
                self.before_claim(self.row)
                self.before_claim = None
            if self.reply is not None:
                return self.response(self.reply)
            if not all(self.match(self.row, key, value) for key, value in params.items()):
                return self.response([])
            self.row.update(copy.deepcopy(body))
            if phase in self.loss:
                self.loss.remove(phase)
                raise TimeoutError("synthetic committed acknowledgment loss")
            return self.response([copy.deepcopy(self.row)])

    def delete(self, url, **kwargs):
        self.pattern_writes += 1
        assert kwargs["params"]["user_id"] == "eq."+OWNER
        return self.response([], 204)

    def post(self, url, **kwargs):
        self.pattern_writes += 1
        return self.response([], 201)


def private_store(protocol):
    return private.SupabaseTradeMemoryStore("https://private-fixture.invalid", "fixture-private-key", OWNER, session=protocol)


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_private_public_runner_commits_actual_result_without_leaking(metabolism, capsys):
    state = metabolism
    protocol = PostgREST()
    state.native.response = packet(autopsy_json())
    def upstream():
        saved = private._row_claim(protocol.row)
        assert saved["state"] == "claimed" and protocol.row["autopsy_state"] == "running"
        assert private._CLAIM_KEY not in saved["request"]["user"]
    state.native.on_upstream = upstream
    result = trade_runner.run(private_store(protocol), root=state.root)
    assert result["completed"] == 1 and result["held"] == result["failed"] == 0
    record = private._row_claim(protocol.row)
    assert record["state"] == protocol.row["autopsy_state"] == "complete"
    assert protocol.row["autopsy_model"] == MODEL
    assert record["receipt"]["usage"]["input_tokens"] == 11
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 1
    output = capsys.readouterr()
    assert "JNJ" not in output.out + output.err and "Healthcare" not in output.out + output.err
    trade_runner.run(private_store(protocol), root=state.root)
    assert len(state.native.posts) == len(usages(state)) == 1


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
@pytest.mark.parametrize("phase", ["claimed", "observed", "known", "publishing", "complete"])
def test_private_lost_ack_reconciles_same_nonce_once(metabolism, phase):
    state = metabolism
    protocol = PostgREST()
    protocol.loss.add(phase)
    state.native.response = packet(autopsy_json())
    result = trade_runner.run(private_store(protocol), root=state.root)
    assert result["completed"] == 1 and private._row_claim(protocol.row)["state"] == "complete"
    assert len(state.native.posts) == len(usages(state)) == 1
    assert len([call for call in protocol.calls if call[0] == "patch"]) == 5


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_two_private_claimers_share_original_id_but_only_winning_nonce_sends(metabolism):
    state = metabolism
    protocol = PostgREST()
    protocol.claim_barrier = threading.Barrier(2)
    protocol.loss.add("claimed")
    state.native.response = packet(autopsy_json())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(trade_runner.run, private_store(protocol), root=state.root) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert sum(result["completed"] for result in results) == 1
    assert len({record["operation_id"] for record in protocol.claims}) == 1
    assert len({record["attempt_nonce"] for record in protocol.claims}) == 2
    assert len(state.native.posts) == len(usages(state)) == 1


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_changed_private_fact_with_unchanged_timestamp_cannot_claim(metabolism):
    state = metabolism
    protocol = PostgREST()
    protocol.before_claim = lambda row: row.update(entry_price=999)
    result = trade_runner.run(private_store(protocol), root=state.root)
    assert result["completed"] == 0 and result["held"] == 1
    assert not state.native.posts and protocol.pattern_writes == 0
    assert protocol.row["updated_at"] == "2026-11-01T00:00:00Z"


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_private_unknown_close_keeps_known_response_and_blocks_native_restart(metabolism, monkeypatch):
    state = metabolism
    protocol = PostgREST()
    state.native.response = packet(autopsy_json())
    monkeypatch.setattr(_CLIENT, "close", Mock(side_effect=OSError("synthetic close loss")))
    result = trade_runner.run(private_store(protocol), root=state.root)
    record = private._row_claim(protocol.row)
    assert result["completed"] == 0 and result["held"] == 1
    assert record["state"] == "held" and record["text"]
    assert record["receipt"]["usage"]["completed_input_tokens"] == 11
    assert protocol.row["autopsy"] is None and protocol.pattern_writes == 0
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    trade_runner.run(private_store(protocol), root=state.root)
    assert len(state.native.posts) == 1 and protocol.pattern_writes == 0
    before = copy.deepcopy(protocol.row)
    private_store(protocol).update_episode(EPISODE, {"autopsy_state": "retry", "evidence_packet": {}})
    assert protocol.row == before


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_private_selected_nonpersistent_dry_run_has_no_claim_or_inference(metabolism):
    protocol = PostgREST()
    result = trade_runner.run(private_store(protocol), root=metabolism.root, dry_run=True)
    assert result["completed"] == 0 and result["held"] == 1
    assert not metabolism.native.posts and not [x for x in protocol.calls if x[0] == "patch"]


@pytest.mark.parametrize("owner,unit", [("journal", "unit-a"), ("market", "us"), ("market", "cn"), ("audit", "123")])
def test_owner_corruption_is_preserved(owner, unit, tmp_path):
    _, path = journal._owner_path(tmp_path, owner, unit)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"duplicate":1,"duplicate":2}')
    before = path.read_bytes()
    with pytest.raises(journal.FabricHeld):
        journal.update_owner_state(tmp_path, owner, unit, {"fresh": "field"})
    assert path.read_bytes() == before


def test_lessons_expected_source_compares_inside_shared_append_lock(tmp_path):
    path, before = seed_lessons(tmp_path)
    source, prefix = memory.capture_lessons_for_resummary(tmp_path)
    assert "DISCARDED_PREFIX" in prefix and "RETAINED_TAIL_ONLY" not in prefix
    assert memory.append_lesson("new", "failed", "", "new", "fixture", root=tmp_path)
    changed = path.read_bytes()
    assert changed.startswith(before)
    receipt = {}
    assert not memory.resummary_lessons("Summary.", tmp_path, expected_source=source, receipt=receipt)
    assert path.read_bytes() == changed and receipt == {}


@pytest.mark.parametrize("change", ["selector", "claim", "after_unavailable"])
def test_dream_late_selection_or_original_never_publishes_native_marker(metabolism, monkeypatch, change):
    state = metabolism
    path, before = seed_lessons(state.root)
    mode = os.environ["MM_PROVIDER_APPLICATION_MODE"]
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    original_load = memory.load_recent_lessons
    def load(*args, **kwargs):
        text = original_load(*args, **kwargs)
        if change != "after_unavailable":
            monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", mode)
            if change == "claim":
                invocation(state, unit="late-original")
                monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
        return text
    monkeypatch.setattr(memory, "load_recent_lessons", load)
    if change == "after_unavailable":
        def unavailable(*args, **kwargs):
            monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", mode)
            return []
        monkeypatch.setattr(auth, "build_providers", unavailable)
    dream._maybe_resummary(state.root, False)
    assert path.read_bytes() == before and not state.native.posts and not usages(state)


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
@pytest.mark.parametrize("bad", ["empty", "duplicate", "verdict", "order", "authority", "field", "summary", "array"])
def test_private_invalid_whole_response_is_retained_without_business_publish(metabolism, bad):
    state = metabolism
    protocol = PostgREST()
    value = json.loads(autopsy_json())
    if bad == "empty":
        value = {}
    elif bad == "verdict":
        value["mitigation_verdict"] = "invented"
    elif bad == "order":
        value["causal_chain"][0]["order"] = "1"
    elif bad == "authority":
        value["signal_hypotheses"][0]["authority"] = "live_signal"
    elif bad == "field":
        value["unrequested"] = True
    elif bad == "summary":
        del value["summary"]
    elif bad == "array":
        value = [value]
    text = json.dumps(value)
    if bad == "duplicate":
        text = '{"schema":"foreign",' + text[1:]
    state.native.response = packet(text)
    result = trade_runner.run(private_store(protocol), root=state.root)
    record = private._row_claim(protocol.row)
    assert result["completed"] == 0 and result["held"] == 1
    assert record["state"] == "held" and record["text"] == text
    assert record["receipt"]["usage"]["input_tokens"] == 11
    assert protocol.row["autopsy"] is None and protocol.pattern_writes == 0
    trade_runner.run(private_store(protocol), root=state.root)
    assert len(state.native.posts) == len(usages(state)) == 1


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
@pytest.mark.parametrize("malformed", [[], "foreign-packet", {private._CLAIM_KEY: None}])
def test_private_malformed_packet_cannot_be_erased_by_native_or_claim_race(metabolism, malformed):
    state = metabolism
    protocol = PostgREST()
    protocol.row["evidence_packet"] = copy.deepcopy(malformed)
    before = copy.deepcopy(protocol.row)
    assert not private_store(protocol).update_episode(EPISODE, {"evidence_packet": {}, "autopsy_state": "retry"})
    assert protocol.row == before and not any(call[0] == "patch" for call in protocol.calls)
    protocol.row["evidence_packet"] = None
    protocol.before_claim = lambda row: row.update(evidence_packet=copy.deepcopy(malformed))
    result = trade_runner.run(private_store(protocol), root=state.root)
    assert result["completed"] == 0 and result["held"] == 1
    assert protocol.row["evidence_packet"] == malformed and not state.native.posts


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_private_lost_claim_ack_and_failed_read_remains_original(metabolism):
    state = metabolism
    class LostClaim(PostgREST):
        def patch(self, *args, **kwargs):
            try:
                return super().patch(*args, **kwargs)
            except TimeoutError:
                self.read_failure = True
                raise
    protocol = LostClaim()
    protocol.loss.add("claimed")
    result = trade_runner.run(private_store(protocol), root=state.root)
    original = private._row_claim(protocol.row)
    assert result["held"] == 1 and original["state"] == "claimed" and not state.native.posts
    protocol.read_failure = False
    trade_runner.run(private_store(protocol), root=state.root)
    assert private._row_claim(protocol.row) == original and not state.native.posts
    assert len([call for call in protocol.calls if call[0] == "patch"]) == 1


@pytest.mark.parametrize("metabolism", ["portfolio_analysis"], indirect=True)
def test_private_old_hold_does_not_consume_fresh_cap(metabolism):
    state = metabolism
    class OldHold(PostgREST):
        def get(self, url, *, headers, params, timeout):
            if params.get("autopsy_state") == "eq.running":
                assert params["limit"] == "1" and params["user_id"] == "eq."+OWNER
                return self.response([{"id": "123e4567-e89b-42d3-a456-426614174002",
                    "user_id": OWNER, "outcome": "win", "autopsy_state": "running", "evidence_packet": {}}])
            return super().get(url, headers=headers, params=params, timeout=timeout)
    protocol = OldHold()
    state.native.response = packet(autopsy_json())
    result = trade_runner.run(private_store(protocol), root=state.root, cap=1)
    assert result["completed"] == 1 and result["held"] == 1
    assert private._row_claim(protocol.row)["state"] == "complete" and len(state.native.posts) == 1


def test_original_claim_survives_actual_process_restart_and_shared_lock(metabolism):
    state = metabolism
    original = invocation(state)
    script = '''import json,sys
from pathlib import Path
from scripts import metabolism_journal as j
root=Path(sys.argv[1])
print("entered",flush=True)
with j.owned_bytes(root,"journal","fresh-label"):
 try: j.guard_saved(root,"journal","fresh-label","dream",["lessons"])
 except j.FabricHeld as error: print(str(error),flush=True)
 else: raise AssertionError("original hold lost")
'''
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    env.pop("MM_PROVIDER_APPLICATION_MODE", None)
    with journal.owned_bytes(state.root, "journal", "unit-a"):
        process = subprocess.Popen([sys.executable, "-B", "-c", script, str(state.root)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert process.stdout.readline().strip() == "entered"
        assert process.poll() is None
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr
    assert stdout.strip() == "metabolism_original_held"
    assert operations(state.root, unit="unit-a")[0] == original.record and not state.native.posts


def test_claim_durability_failure_never_reaches_model(metabolism, monkeypatch):
    state = metabolism
    monkeypatch.setattr(journal.os, "fsync", Mock(side_effect=OSError("synthetic durability failure")))
    with pytest.raises(OSError):
        invocation(state)
    assert not state.native.posts and not usages(state)


def seed_standout(state, market="us"):
    import pandas as pd
    from tests.test_pick_autopsy_selection import _row
    root = state.root
    rows = [_row("ONE", 0.2, asof="2026-11-01"), _row("TWO", -0.1, asof="2026-11-02")]
    if market == "cn":
        rows = [{"ticker": "600001.SS", "date": date, "board_definition": "prophet_v2", "horizon": 21,
                 "fwd_excess": value, "process_fault": "clean", "outcome_cause": "momentum"}
                for date, value in (("2026-11-01", 0.2), ("2026-11-02", -0.1))]
    path = root/f"data/standout_audit/{market}_attribution.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    (path.parent/f"{market}_evidence.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    board = root/f"site/factordata/{market}_audit_scoreboard.json"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(json.dumps({"market": market, "n": 2, "coverage_monitor": {"status": "accruing"}}))
    target = root/"config/standout_review.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve().parents[1]/"config/standout_review.yml", target)
    return rows, path


def cohort_reply(market="us", cycle="audit-cycle", *, bus=False):
    from tests.test_metabolism_sa_w3 import TestRunAudit
    value = TestRunAudit()._make_stub_postmortem()
    value.update(market=market, cycle_id=cycle)
    if market == "cn":
        value["hypotheses"] = []
    if bus:
        for index in (2, 3):
            value["hypotheses"].append({"rank": index, "description": "Inspect this bounded source gap.",
                "lane": "code fix", "fitness_contract": {"check_by": "2026-11-20"},
                "falsifiable_claim": "The recorded missing input can be reproduced."})
    return value


def pick_reply(count=2):
    base = json.loads(autopsy_json())
    del base["schema"]
    base["engines_credit"] = "The original attribution owner recorded the outcome."
    return [{**copy.deepcopy(base), "pick_index": i} for i in range(1, count+1)]


@pytest.mark.parametrize("market", ["us", "cn"])
def test_public_cohort_uses_original_cutoff_and_real_business_owners(metabolism, market):
    import pandas as pd
    state = metabolism
    rows, path = seed_standout(state, market)
    state.native.response = packet(json.dumps(cohort_reply(market, bus=market=="us")))
    def upstream():
        saved = operations(state.root, "market", market)[0]
        assert saved["state"] == "claimed"
        later = {**rows[-1], ("as_of" if market=="us" else "date"): "2026-11-03", "ticker": "LATER"}
        pd.DataFrame(rows+[later]).to_parquet(path, index=False)
    state.native.on_upstream = upstream
    result = standout.run_audit(market, "audit-cycle", root=state.root)
    assert result["status"] == "ok", result
    saved = operations(state.root, "market", market)[0]
    owner = journal.read_owner_state(state.root, "market", market)
    assert saved["state"] == "complete" and owner["last_audit_graded_as_of"] == "2026-11-02"
    assert json.loads(Path(result["artifact"]).read_text())["model"] == MODEL
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 1
    if market == "us":
        assert len(saved["business"]["outcome"]["files"]) == 2
        bus = [json.loads(line) for line in (state.root/"data/metabolism/insight_bus.jsonl").read_text().splitlines()]
        assert len(bus) == len({row["insight_id"] for row in bus}) == 2
    # Restore the exact original cohort bytes: completed history is reused across cycle labels.
    pd.DataFrame(rows).to_parquet(path, index=False)
    reused = standout.run_audit(market, "another-cycle", root=state.root)
    assert reused.get("reused") is True, reused
    assert len(state.native.posts) == 1


@pytest.mark.parametrize("bad", ["empty", "wrong_market", "boolean_delta", "duplicate", "missing_contract"])
def test_cohort_invalid_known_output_holds_all_publication(metabolism, bad, monkeypatch):
    state = metabolism
    seed_standout(state)
    value = cohort_reply()
    if bad == "empty":
        value = {}
    elif bad == "wrong_market":
        value["market"] = "cn"
    elif bad == "boolean_delta":
        value["hypotheses"][0]["delta_steps"] = True
    elif bad == "missing_contract":
        value["hypotheses"][0]["fitness_contract"] = {}
    text = json.dumps(value)
    if bad == "duplicate":
        text = '{"market":"foreign",'+text[1:]
    state.native.response = packet(text)
    result = standout.run_audit("us", "audit-cycle", root=state.root)
    assert result["status"] in ("held", "error"), result
    original = operations(state.root, "market", "us")[0]
    assert original["state"] == "held" and original["text"] == text
    assert not list((state.root/"data/standout_audit/postmortems").glob("*.json"))
    assert not (state.root/"data/standout_review/proposals").exists()
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    standout.run_audit("us", "fresh-cycle", root=state.root, model_caller=Mock(side_effect=AssertionError("injected fallback")))
    assert len(state.native.posts) == 1 and operations(state.root, "market", "us")[0] == original


@pytest.mark.parametrize("market", ["us", "cn"])
def test_public_pick_autopsies_preserve_dated_identity_and_served_model(metabolism, market):
    state = metabolism
    seed_standout(state, market)
    state.native.response = packet(json.dumps(pick_reply()))
    result = standout.run_pick_autopsies(market, "pick-cycle", root=state.root)
    assert result["status"] == "ok" and len(result["written"]) == 2, result
    docs = [json.loads(Path(path).read_text()) for path in result["written"]]
    assert len({doc["pick_id"] for doc in docs}) == 2
    assert all(doc["model"] == MODEL and doc["llm"]["summary"] for doc in docs)
    if market == "cn":
        assert {doc["entry_date"] for doc in docs} == {"2026-11-01", "2026-11-02"}
        sent = json.dumps(json.loads(state.native.posts[0][1]))
        assert "fwd_excess=" in sent and "excess_spy=" not in sent
    assert standout.run_pick_autopsies(market, "later-cycle", root=state.root)["status"] == "no_picks"
    assert len(state.native.posts) == len(usages(state)) == len(state.closes) == 1


@pytest.mark.parametrize("bad", ["missing", "duplicate", "boolean", "reordered", "enum", "authority"])
def test_pick_whole_batch_validation_precedes_any_artifact(metabolism, bad):
    state = metabolism
    seed_standout(state)
    value = pick_reply()
    if bad == "missing":
        value.pop()
    elif bad == "duplicate":
        value[1]["pick_index"] = 1
    elif bad == "boolean":
        value[0]["pick_index"] = True
    elif bad == "reordered":
        value.reverse()
    elif bad == "enum":
        value[1]["mitigation_verdict"] = "invented"
    elif bad == "authority":
        value[1]["signal_hypotheses"][0]["authority"] = "live_signal"
    state.native.response = packet(json.dumps(value))
    result = standout.run_pick_autopsies("us", "pick-cycle", root=state.root)
    assert result["status"] in ("held", "error") and result["written"] == [], result
    assert not list((state.root/"data/standout_audit/pick_autopsies").glob("**/*.json"))
    assert operations(state.root, "market", "us")[0]["state"] == "held"
    (state.root/"config.yml").write_text("prophet:\n  autopsy_cap_per_cycle: 1\n")
    standout.run_pick_autopsies("us", "fresh-cycle", root=state.root)
    assert len(state.native.posts) == 1


def test_ambiguous_old_cn_file_is_preserved_without_inference(metabolism):
    state = metabolism
    seed_standout(state, "cn")
    old = state.root/"data/standout_audit/pick_autopsies/cn/600001.SS-unknown-default.json"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(json.dumps({"schema": standout.SCHEMA_PICK_AUTOPSY, "market": "cn", "attribution": {"ticker": "600001.SS"}}))
    before = old.read_bytes()
    result = standout.run_pick_autopsies("cn", "new-date", root=state.root)
    assert result["status"] == "held" and old.read_bytes() == before and not state.native.posts


def test_uncertain_insight_append_retains_original_intent_and_never_reappends(metabolism, monkeypatch):
    from engine.metabolism import insight_bus
    state = metabolism
    seed_standout(state)
    state.native.response = packet(json.dumps(cohort_reply(bus=True)))
    original = insight_bus.append_row
    def lost_ack(row, root=None, **kwargs):
        assert original(row, root=root, **kwargs)
        return False
    monkeypatch.setattr(insight_bus, "append_row", lost_ack)
    result = standout.run_audit("us", "audit-cycle", root=state.root)
    assert result["status"] == "held", result
    row = operations(state.root, "market", "us")[0]
    assert row["state"] == "held" and row["text"] and len(row["business"]["intent"]["bus"]) == 2
    bus = state.root/"data/metabolism/insight_bus.jsonl"
    before = bus.read_bytes()
    standout.run_audit("us", "new-cycle", root=state.root)
    assert bus.read_bytes() == before and len(before.splitlines()) == 1 and len(state.native.posts) == 1


@pytest.mark.parametrize("change", ["delete", "replace_same_bytes"])
def test_completed_pick_original_prevents_repeat_after_artifact_change(metabolism, change):
    state = metabolism
    seed_standout(state)
    state.native.response = packet(json.dumps(pick_reply()))
    first = standout.run_pick_autopsies("us", "original-cycle", root=state.root)
    assert first["status"] == "ok", first
    path = Path(first["written"][0])
    if change == "delete":
        path.unlink()
    else:
        substitute = path.with_suffix(".replacement")
        substitute.write_bytes(path.read_bytes())
        os.replace(substitute, path)
    (state.root/"config.yml").write_text("prophet:\n  autopsy_cap_per_cycle: 1\n")
    result = standout.run_pick_autopsies("us", "fresh-label", root=state.root)
    assert result["status"] == "held" and len(state.native.posts) == 1, result


def test_completed_cohort_cycle_never_resends_after_new_source(metabolism):
    import pandas as pd
    state = metabolism
    rows, path = seed_standout(state)
    state.native.response = packet(json.dumps(cohort_reply()))
    first = standout.run_audit("us", "audit-cycle", root=state.root)
    assert first["status"] == "ok", first
    pd.DataFrame(rows+[{**rows[-1], "as_of": "2026-11-03", "ticker": "NEW"}]).to_parquet(path, index=False)
    reused = standout.run_audit("us", "audit-cycle", root=state.root)
    assert reused.get("reused") is True and reused["cutoff"] == "2026-11-02" and len(state.native.posts) == 1


def test_same_byte_foreign_artifact_between_preflight_and_write_is_held(metabolism, monkeypatch):
    state = metabolism
    seed_standout(state)
    state.native.response = packet(json.dumps(cohort_reply()))
    original = standout._preflight_artifacts
    foreign = []
    def interleave(root, plan):
        original(root, plan)
        path = root/plan["files"][0]["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(standout._artifact_bytes(plan["files"][0]))
        foreign.append((path, path.stat().st_ino, path.read_bytes()))
    monkeypatch.setattr(standout, "_preflight_artifacts", interleave)
    result = standout.run_audit("us", "audit-cycle", root=state.root)
    assert result["status"] == "held", result
    path, inode, raw = foreign[0]
    assert path.stat().st_ino == inode and path.read_bytes() == raw and len(state.native.posts) == 1


def test_incomplete_legacy_pick_artifact_remains_unqualified(metabolism):
    state = metabolism
    rows, _ = seed_standout(state)
    pick = rows[0]
    document = standout._pick_document("us", pick, {}, "old-cycle", "old-requested-model", "2026-11-01", "2026-11-01")
    path = state.root/f"data/standout_audit/pick_autopsies/us/{standout._pick_id(pick)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document))
    before = path.read_bytes()
    result = standout.run_pick_autopsies("us", "fresh-cycle", root=state.root)
    assert result["status"] == "held" and path.read_bytes() == before and not state.native.posts, result


def test_real_bus_compaction_and_append_share_original_owner(tmp_path, monkeypatch):
    from concurrent.futures import TimeoutError as FutureTimeout
    from engine.metabolism import insight_bus as bus
    row = bus.build_row("fixture", "health_transition", "low", ["old"], "Old fixture", ts="2020-01-01T00:00:00Z")
    assert bus.append_row(row, root=tmp_path)
    snapshot, release, append_started = threading.Event(), threading.Event(), threading.Event()
    original = bus._strict_bus_rows
    def held_snapshot(raw):
        result = original(raw)
        if threading.current_thread().name == "fixture-compactor" and not snapshot.is_set():
            snapshot.set()
            assert release.wait(5)
        return result
    monkeypatch.setattr(bus, "_strict_bus_rows", held_snapshot)
    new = bus.build_row("fixture", "health_transition", "low", ["new"], "New fixture")
    receipt = {}
    def compact():
        threading.current_thread().name = "fixture-compactor"
        return bus.compact_bus(root=tmp_path)
    def append():
        append_started.set()
        return bus.append_row(new, root=tmp_path, expected_absent_id=new["insight_id"], receipt=receipt)
    with ThreadPoolExecutor(max_workers=2) as pool:
        compactor = pool.submit(compact)
        assert snapshot.wait(5)
        appender = pool.submit(append)
        assert append_started.wait(5)
        try:
            with pytest.raises(FutureTimeout):
                appender.result(timeout=0.1)
        finally:
            release.set()
        assert compactor.result(timeout=5)["errors"] == []
        assert appender.result(timeout=5)
    rows = original((tmp_path/bus.BUS_PATH).read_bytes())
    assert rows == [new] and receipt["row_digest"] == journal.fabric_digest(new)
    assert not bus.append_row(new, root=tmp_path, expected_absent_id=new["insight_id"], receipt={})


@pytest.mark.parametrize("market", ["us", "cn"])
def test_actual_market_producers_preserve_original_receipt_and_audit_cursor(metabolism, market):
    import pandas as pd
    from engine import standout_audit as us, china_standout_audit as cn, china_regime_store as regime
    state = metabolism
    journal.update_owner_state(state.root, "market", market, {"last_audit_graded_as_of": "2026-10-01", "last_postmortem_cycle_id": "previous"})
    claim = journal.FabricInvocation(state.root, "standout", market, {"source": "producer-fixture"},
        ["market:"+market], "Explain the source.", "One fixture.", 800)
    if market == "us":
        path = us._retro_path(state.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=["as_of", "horizon"]).to_parquet(path, index=False)
        result = us.build_us(root=state.root)
        assert result["status"] == "ok", result
    else:
        cn._update_state_attribution(state.root)
        regime._update_state("2026-11-04", root=state.root)
    owner = journal.read_owner_state(state.root, "market", market)
    assert journal._records(owner)[claim.record["operation_id"]] == claim.record
    assert owner["last_audit_graded_as_of"] == "2026-10-01" and owner["last_postmortem_cycle_id"] == "previous"


def test_business_archive_does_not_inherit_operation_state_size_limit(tmp_path):
    bus = insight_bus
    archive = tmp_path/bus._ARCHIVE_DIR_REL/"2020-01.jsonl"
    archive.parent.mkdir(parents=True)
    rows = [bus.build_row("fixture", "health_transition", "low", [str(i)], "x"*1_000_000,
                         ts="2020-01-01T00:00:00Z") for i in range(9)]
    raw = "".join(json.dumps(row)+"\n" for row in rows).encode()
    assert len(raw) > journal._STATE_LIMIT
    archive.write_bytes(raw)
    next_row = bus.build_row("fixture", "health_transition", "low", ["extra"], "Additional old row",
                             ts="2020-01-01T00:00:00Z")
    assert bus.append_row(next_row, root=tmp_path)
    result = bus.compact_bus(root=tmp_path)
    assert result["errors"] == [] and result["archived"] == 1, result
    assert bus._strict_bus_rows(archive.read_bytes()) == rows+[next_row]
    assert bus.append_row(bus.build_row("fixture", "health_transition", "low", ["fresh"], "Fresh"), root=tmp_path)


def test_selected_lesson_tail_preserves_captured_whitespace_verbatim(tmp_path):
    path = tmp_path/"data/metabolism/lessons.jsonl"
    path.parent.mkdir(parents=True)
    raw = b'{"earlier":"'+b"x"*9000+b'"}\n'+b'  {"retained":"'+b"y"*3000+b'"}\n\n'
    path.write_bytes(raw)
    source, _ = memory.capture_lessons_for_resummary(tmp_path)
    tail = memory._lesson_parts(raw)[1]
    assert tail.startswith(b"  ")
    receipt = {}
    assert memory.resummary_lessons("Observed earlier lessons.", root=tmp_path,
                                   expected_source=source, receipt=receipt)
    final = path.read_bytes()
    assert final.split(b"\n", 1)[1] == tail
    assert json.loads(final.splitlines()[0])["source_coverage"]["tail_sha256"] == hashlib.sha256(tail).hexdigest()


@pytest.mark.parametrize("metabolism,kind", [
    ("lobe_maintenance", "propose"), ("fable_orchestration", "adjudicate"),
    ("fable_orchestration", "agenda"), ("fable_orchestration", "attention"),
    ("development_agent", "audit"),
], indirect=["metabolism"])
def test_native_purpose_engines_consult_actual_policy_before_injection_or_credentials(metabolism, kind, monkeypatch):
    state = metabolism
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("legacy provider discovery")))
    if kind == "audit":
        result = audit.audit_pr(71, {"target_files": []}, "", "a"*40, root=state.root)
        assert result["status"] == "held" and result["deterministic_ok"] is True, result
    else:
        calls = {
            "propose": lambda: propose.propose("native-cycle", root=state.root, injected_proposals=[]),
            "adjudicate": lambda: adjudicate.adjudicate_role("orchestrator", "native-cycle", state.root/"absent.json", root=state.root, injected={}),
            "agenda": lambda: agenda.build_agenda("native-cycle", root=state.root, providers=[{"untrusted": True}]),
            "attention": lambda: attention.build_attention("native-cycle", root=state.root, providers=[{"untrusted": True}]),
        }
        with pytest.raises(journal.FabricHeld, match="metabolism_selected_native_policy_refused"):
            calls[kind]()
    assert not state.native.posts and not state.closes and not usages(state)
    assert not (state.root/"data/metabolism/dockets").exists()
    assert not (state.root/"data/metabolism/attention_allocation.json").exists()
    assert not (state.root/"data/metabolism/audit/71.json").exists()


@pytest.mark.parametrize("metabolism,kind", [("lobe_maintenance", "propose"),
    ("fable_orchestration", "adjudicate"), ("fable_orchestration", "agenda"),
    ("fable_orchestration", "attention")], indirect=["metabolism"])
def test_native_purpose_public_clis_stop_before_preflight_and_estimated_usage(metabolism, kind, monkeypatch):
    from scripts import preflight_claude_auth
    from engine.metabolism import applier
    state = metabolism
    forbidden = Mock(side_effect=AssertionError("legacy selected side effect"))
    monkeypatch.setattr(auth, "build_providers", forbidden)
    monkeypatch.setattr(preflight_claude_auth, "check_auth", forbidden)
    monkeypatch.setattr(applier, "consume_charter_proposals", forbidden)
    args = ["--cycle-id", "native-cycle", "--root", str(state.root)]
    main = {"propose": propose_cli.main, "adjudicate": adjudicate_cli.main,
            "agenda": agenda_cli.main, "attention": attention_cli.main}[kind]
    assert main(args+(["--role", "orchestrator"] if kind == "adjudicate" else [])) == 2
    forbidden.assert_not_called()
    assert not state.native.posts and not usages(state)
    document = journal.read_owner_state(state.root, "journal", "native-cycle")
    assert not any(row.get("status") == "done" for row in document.get("stages", {}).values())


def test_structural_attention_and_explicit_shadow_stubs_keep_zero_model_path(metabolism, monkeypatch, tmp_path):
    state = metabolism
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("structural credential discovery")))
    allocation = attention.build_attention("structural-cycle", root=state.root, providers=None, model=None)
    assert allocation["provider"] is None and allocation["degraded_reason"] == "no_provider"
    assert attention_cli.main(["--cycle-id", "dry-cycle", "--root", str(state.root), "--dry-run"]) == 0
    shadow_root = tmp_path/"shadow-source"
    shadow_root.mkdir()
    agenda_result = shadow._run_agenda(shadow_root, state.root, "stub-cycle", False)
    propose_result = shadow._run_propose(shadow_root, state.root, "stub-cycle", False, "2026-11-01")
    adjudicate_result = shadow._run_adjudicate(shadow_root, state.root, "stub-cycle", False)
    assert all(row["status"] == "ok" for row in (agenda_result, propose_result, adjudicate_result))
    assert not state.native.posts and not state.closes and not usages(state)


def test_selected_shadow_model_stages_cannot_use_ephemeral_custody_or_legacy_provider(metabolism, monkeypatch, tmp_path):
    state = metabolism
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("shadow provider discovery")))
    shadow_root = tmp_path/"shadow-source"
    shadow_root.mkdir()
    results = [shadow._run_agenda(shadow_root, state.root, "shadow-cycle", True),
               shadow._run_propose(shadow_root, state.root, "shadow-cycle", True, "2026-11-01"),
               shadow._run_adjudicate(shadow_root, state.root, "shadow-cycle", True)]
    assert all(row["status"] == "held" for row in results), results
    assert not state.native.posts and not usages(state)


def test_native_propose_rechecks_late_selection_before_model_discovery(metabolism, monkeypatch):
    state = metabolism
    original = propose.build_prompt_context
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    def interleave(*args, **kwargs):
        context = original(*args, **kwargs)
        monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
        return context
    monkeypatch.setattr(propose, "build_prompt_context", interleave)
    with pytest.raises(journal.FabricHeld):
        propose.propose("late-cycle", root=state.root)
    assert not state.native.posts and not usages(state)


@pytest.mark.parametrize("selected_mode", [True, False])
def test_native_guard_preserves_malformed_original_even_without_selector(metabolism, monkeypatch, selected_mode):
    state = metabolism
    path = state.root/"data/metabolism/journal/original-cycle.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema": "metabolism.journal.v1", "cycle_id": "original-cycle", journal._FABRIC_KEY: None}))
    before = path.read_bytes()
    if not selected_mode:
        monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    with pytest.raises(journal.FabricHeld, match="metabolism_operations_invalid"):
        propose.propose("fresh-cycle", root=state.root, injected_proposals=[])
    assert path.read_bytes() == before and not state.native.posts and not usages(state)


@pytest.mark.parametrize("kind", ["propose", "adjudicate"])
def test_late_native_model_selector_never_becomes_degraded_completion(metabolism, monkeypatch, kind):
    from scripts import preflight_claude_auth
    state = metabolism
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    monkeypatch.setattr(preflight_claude_auth, "check_auth", lambda **kw: {"auth_ok": True})
    module = propose if kind == "propose" else adjudicate
    def activate():
        monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
        return "claude-opus-4-8"
    monkeypatch.setattr(module, "_get_deliberation_model", activate)
    args = ["--cycle-id", "late-native", "--root", str(state.root)]
    if kind == "propose":
        code = propose_cli.main(args)
    else:
        code = adjudicate_cli.main(args+["--role", "orchestrator"])
    assert code != 0
    assert not state.native.posts and not state.closes and not usages(state)
    assert not (state.root/"data/metabolism/dockets/late-native.json").exists()
    assert not (state.root/"data/neuralweb/governance.jsonl").exists()
    document = journal.read_owner_state(state.root, "journal", "late-native")
    assert not any(row.get("status") == "done" for row in document.get("stages", {}).values())
    from scripts import metabolism_budget
    budget = metabolism_budget._read_ledger(state.root)
    assert not budget.get("entries")


@pytest.mark.parametrize("selector", ["", "unknown-mode"])
def test_invalid_present_selector_is_held_without_audit_or_model_artifacts(metabolism, monkeypatch, selector):
    state = metabolism
    monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", selector)
    result = audit.audit_pr(72, {"target_files": []}, "", "a"*40, root=state.root)
    assert result["status"] == "held" and result["deterministic_ok"] is True, result
    for function in (agenda.build_agenda, attention.build_attention):
        with pytest.raises(journal.FabricHeld):
            function("invalid-cycle", root=state.root, providers=[{"name": "oauth"}])
    assert not (state.root/"data/metabolism/audit/72.json").exists()
    assert not (state.root/"data/neuralweb/governance.jsonl").exists()
    assert not state.native.posts and not usages(state)


def test_actual_shared_refusal_is_not_legacy_provider_failure(metabolism, monkeypatch):
    state = metabolism
    recipe = auth.build_providers({"provider_order": ["fabric"], "usage_lane": "metabolism-propose"})
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    with pytest.raises(journal.FabricHeld, match="requires_original"):
        journal.native_provider_call(state.root, "propose", "recipe-cycle", ["lobe:til"],
            recipe, lambda *_: pytest.fail("selected recipe invoked"), context="metabolism_propose")
    assert not state.native.posts and not usages(state)


@pytest.mark.parametrize("kind,hook", [("cohort", "callback"), ("picks", "callback"),
                                      ("cohort", "deliberation"), ("picks", "deliberation")])
def test_standout_legacy_path_cannot_publish_after_late_selection(metabolism, monkeypatch, kind, hook):
    state = metabolism
    seed_standout(state)
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    def activate():
        monkeypatch.setenv("MM_PROVIDER_APPLICATION_MODE", "shared_fabric")
        return "claude-opus-4-8"
    def callback(*args):
        activate()
        return json.dumps(cohort_reply() if kind == "cohort" else pick_reply())
    if hook == "deliberation":
        monkeypatch.setattr(standout, "_get_deliberation_model", activate)
    function = standout.run_audit if kind == "cohort" else standout.run_pick_autopsies
    result = function("us", "late-standout", root=state.root,
                      model_caller=callback if hook == "callback" else None)
    assert result["status"] == "held", result
    assert not list((state.root/"data/standout_audit/postmortems").glob("*.json"))
    assert not list((state.root/"data/standout_audit/pick_autopsies/us").glob("*.json"))
    assert not (state.root/"data/standout_audit/us_audit_state.json").exists()
    assert not state.native.posts and not state.closes and not usages(state)


# ── The saved original: lookup before selection, inspection, secret and nonce ──

def _dream_inspection(profile="lobe_analysis"):
    policy = {"schema": "mastermind.provider_workload_decision.v1", "policy_revision": 2,
              "policy_hash": "a" * 64, "profiles": [profile],
              "execution_surface": "inference", "allowed_order": ["fabric"],
              "denied_order": []}
    return {"provider": "fabric", "model": "fixture-model", "cap_id": "metabolism-dream",
            "capability_id": "metabolism_dream", "cost_basis": "fixture",
            "workload_policy": policy, "transport_identity": "b" * 64}


def _receipt(operation_id, inspection, text, *, close, effect_unknown):
    return {"operation_id": operation_id, "provider": inspection["provider"],
            "requested_model": inspection["model"], "served_model": inspection["model"],
            "observation": {"request_id": operation_id + ":brain:0",
                            "serving_model": inspection["model"],
                            "input_tokens": None, "output_tokens": None},
            "usage": {"input_tokens": None, "output_tokens": None,
                      "completed_input_tokens": 0, "completed_output_tokens": 0,
                      "usage_state": "unknown"},
            "close": close, "effect_unknown": effect_unknown}


def _complete_dream(root, unit="unit-a", logical=None, scope=None):
    logical = {"source": "fixture-v1"} if logical is None else logical
    scope = ["lessons"] if scope is None else scope
    inspection = _dream_inspection()
    operation = journal.FabricInvocation(root, "dream", unit, logical, scope,
        "Explain this bounded fixture.", "The supplied fixture has one observation.", 800,
        inspection=inspection, selection={"mode": "fixture", "host_profile": None})
    text = "Bounded fixture summary."
    observed = copy.deepcopy(operation.record)
    observed.update(state="observed", text=text, text_digest=journal.fabric_digest(text),
                    receipt=_receipt(operation.record["operation_id"], inspection, text,
                                     close=None, effect_unknown=True), error=None)
    operation.save(observed)
    known = copy.deepcopy(operation.record)
    known.update(state="known",
                 receipt=_receipt(operation.record["operation_id"], inspection, text,
                                  close={"disposition": "local_only", "closed": False,
                                         "effect_unknown": False, "attempted": False},
                                  effect_unknown=False))
    operation.save(known)
    operation.publication_intent({"owner": "fixture"})
    operation.complete({"status": "fixture"})
    return operation


def test_completed_original_reopens_before_any_selection_inspection_or_nonce(tmp_path):
    """A completed original is found before the factory, the inspection or a nonce."""
    original = _complete_dream(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("a completed original must not reach a factory or a nonce")

    with patch.object(journal, "selected_factory", side_effect=forbidden), \
         patch.object(journal.secrets, "token_hex", side_effect=forbidden):
        reopened = journal.FabricInvocation(tmp_path, "dream", "unit-a",
            {"source": "fixture-v1"}, ["lessons"], "system", "user", 800)
    assert reopened.reused
    assert reopened.record["operation_id"] == original.record["operation_id"]
    assert reopened.record["attempt_nonce"] == original.record["attempt_nonce"]
    assert reopened.record["state"] == "complete"
    with pytest.raises(journal.FabricHeld, match="metabolism_send_not_owned"):
        reopened.call()


def test_incomplete_original_is_never_recoverable_by_sending_again(tmp_path):
    """A claimed original stays claimed; it is never recovered by sending again."""
    inspection = _dream_inspection()
    operation = journal.FabricInvocation(tmp_path, "dream", "unit-a",
        {"source": "fixture-v1"}, ["lessons"], "system", "user", 800,
        inspection=inspection, selection={"mode": "fixture", "host_profile": None})
    assert operation.record["state"] == "claimed"
    with pytest.raises(journal.FabricHeld, match="metabolism_original_held"):
        journal.FabricInvocation(tmp_path, "dream", "unit-a", {"source": "fixture-v1"},
            ["lessons"], "system", "user", 800, inspection=inspection,
            selection={"mode": "fixture", "host_profile": None})
    # A changed scope cannot replace an incomplete overlapping original either.
    with pytest.raises(journal.FabricHeld, match="metabolism_original_held"):
        journal.FabricInvocation(tmp_path, "dream", "unit-a", {"source": "fixture-v1"},
            ["lessons", "other"], "system", "user", 800, inspection=inspection,
            selection={"mode": "fixture", "host_profile": None})
    assert journal.read_owner_state(tmp_path, "journal", "unit-a")[
        journal._FABRIC_KEY]["records"][operation.record["operation_id"]] == operation.record


def test_a_changed_request_cannot_reuse_an_unrelated_completed_original(tmp_path):
    """A changed request is a different original; the old one keeps its evidence."""
    original = _complete_dream(tmp_path)
    reopened = journal.FabricInvocation(tmp_path, "dream", "unit-a",
        {"source": "fixture-v2"}, ["lessons"], "system", "user", 800,
        inspection=_dream_inspection(), selection={"mode": "fixture", "host_profile": None})
    assert not reopened.reused
    records = journal._records(journal.read_owner_state(tmp_path, "journal", "unit-a"))
    assert len(records) == 2
    assert records[original.record["operation_id"]]["state"] == "complete"


def test_native_purpose_receipt_is_accepted_without_an_inference_relabel(tmp_path):
    """A native-purpose decision keeps its own surface and its empty orders."""
    policy = {"schema": "mastermind.provider_workload_decision.v1", "policy_revision": 2,
              "policy_hash": "a" * 64, "profiles": ["development_agent"],
              "execution_surface": "native_agent", "allowed_order": [], "denied_order": []}
    inspection = {"provider": "fabric", "model": "native-model", "cap_id": "metabolism-audit",
                  "capability_id": "metabolism_audit", "cost_basis": "native",
                  "workload_policy": policy, "transport_identity": "b" * 64}
    journal._inspection(inspection, "development_agent")
    record = journal.operation_record(tmp_path, "audit", "42", {"source": "fixture"},
        ["pr:42"], "system", "user", 800, None, {}, inspection=inspection,
        selection={"mode": "fixture", "host_profile": None})
    assert record["inspection"]["workload_policy"]["execution_surface"] == "native_agent"
    # An inference consumer keeps its exact accepted form.
    journal._inspection(_dream_inspection(), "lobe_analysis")
    # Any other surface or order is refused rather than relabeled.
    for broken in ({"execution_surface": "native_cli"}, {"execution_surface": "inference"},
                   {"allowed_order": ["fabric"]}, {"denied_order": ["oauth"]}):
        bad = {**inspection, "workload_policy": {**policy, **broken}}
        with pytest.raises(journal.FabricHeld, match="metabolism_workload_receipt_invalid"):
            journal._inspection(bad, "development_agent")


# ── The owners: the claim authority, the audit grammar and the durable event ───

def test_the_guard_exempts_only_the_callers_own_claim(tmp_path):
    """A caller's own in-flight claim is not a hold against that caller."""
    inspection = _dream_inspection()
    operation = journal.FabricInvocation(tmp_path, "dream", "unit-a",
        {"source": "fixture-v1"}, ["lessons"], "system", "user", 800,
        inspection=inspection, selection={"mode": "fixture", "host_profile": None})
    # The owner's own claim is recognised, with its identity and its nonce.
    journal.guard_saved(tmp_path, "journal", "unit-a", "dream", ["lessons"],
                        owned=operation.record)
    # Any other caller is held by the very same claim.
    with pytest.raises(journal.FabricHeld, match="metabolism_original_held"):
        journal.guard_saved(tmp_path, "journal", "unit-a", "dream", ["lessons"])
    # A claim that is not the stored one is never borrowed.
    with pytest.raises(journal.FabricHeld, match="metabolism_owned_claim_changed"):
        journal.guard_saved(tmp_path, "journal", "unit-a", "dream", ["lessons"],
                            owned={**operation.record, "attempt_nonce": "0" * 32})
    with pytest.raises(journal.FabricHeld, match="metabolism_owned_claim_changed"):
        journal.guard_saved(tmp_path, "journal", "unit-a", "dream", ["lessons"],
                            owned={**operation.record, "operation_id": "metabolism:other"})
    # A claim of another kind, unit or scope is not this caller's claim.
    for broken in ({**operation.record, "owner": "audit"},
                   {**operation.record, "unit": "unit-b"},
                   {**operation.record, "scope": ["other"]},
                   {**operation.record, "state": "known"}):
        with pytest.raises(journal.FabricHeld, match="metabolism_owned_claim_invalid"):
            journal.guard_saved(tmp_path, "journal", "unit-a", "dream", ["lessons"],
                                owned=broken)


def test_the_audit_record_uses_the_audit_grammar_not_an_identifier_label(tmp_path):
    """The audit bounds are the audit grammar: 64 findings, 2048 each, 8192."""
    record = {"schema": "metabolism.audit.v1", "pr_number": 1, "proposal_id": "p1",
              "head_sha": "sha1", "verdict": "approve", "deterministic_ok": True,
              "llm_verdict": "approve", "confidence": 0.9,
              "findings": ["f" * 2048], "rationale": "r" * 8192,
              "ts": "2026-11-07T00:00:00+00:00"}
    assert journal.validate_audit_record(record, 1) is record
    for field, value in (("findings", ["f" * 2049]), ("rationale", "r" * 8193),
                         ("confidence", 1.5), ("confidence", True), ("verdict", "maybe"),
                         ("findings", [42]), ("findings", [""]), ("rationale", ""),
                         ("head_sha", ""), ("pr_number", 0)):
        with pytest.raises(journal.FabricHeld, match="metabolism_audit_record_invalid"):
            journal.validate_audit_record({**record, field: value}, 1)
    # A record for another PR never validates as this PR's record.
    with pytest.raises(journal.FabricHeld, match="metabolism_audit_record_invalid"):
        journal.validate_audit_record(record, 2)


def test_the_governance_append_is_durable_and_never_duplicated(tmp_path):
    """A durable append acknowledges the exact correlated row, once."""
    from engine.neuralweb import governance
    ts = "2026-11-07T00:00:00.000000+00:00"
    event_id = governance.event_identity("metabolism_audit", "metabolism_pr:1", ts)
    ledger = tmp_path / "data/neuralweb/governance.jsonl"
    common = {"event_type": "metabolism_audit", "target": "metabolism_pr:1",
              "authored_by": "metabolism_audit", "root": tmp_path,
              "event_id": event_id, "ts": ts, "durable": True}
    assert governance.append_event(**common, evidence={"verdict": "approve"},
                                   note="ok") is True
    rows = ledger.read_text().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["event_id"] == event_id
    assert json.loads(rows[0])["evidence"] == {"verdict": "approve"}
    # The same event is acknowledged again and never appended twice.
    assert governance.append_event(**common, evidence={"verdict": "approve"},
                                   note="ok") is True
    assert len(ledger.read_text().splitlines()) == 1
    # A different event under the same identity is refused, never appended.
    assert governance.append_event(**common, evidence={"verdict": "reject"},
                                   note="other") is False
    assert len(ledger.read_text().splitlines()) == 1


def test_the_audit_publication_intent_is_owned_before_the_append(tmp_path):
    """The exact request, verdict and intent are owned before any append."""
    record = {
        "schema": "metabolism.audit.v1", "pr_number": 1, "proposal_id": "p1",
        "head_sha": "sha1", "verdict": "reject", "deterministic_ok": False,
        "llm_verdict": None, "confidence": None, "findings": ["foreign_file:other.py"],
        "rationale": "A deterministic containment finding.",
        "ts": "2026-11-07T00:00:00.000000+00:00",
    }
    logical = audit._audit_logical(1, {"proposal_id": "p1"}, "diff", "sha1")
    intent = audit._audit_intent(record, 1)
    owned = journal.audit_publication_intent(
        tmp_path, 1, intent, logical=logical, record=record)
    assert owned["state"] == "pending" and owned["record"] == record
    document = journal.read_owner_state(tmp_path, "audit", "1")
    assert document["publication"]["current"]["intent"] == intent
    later = {**record, "ts": "2026-11-07T01:00:00.000000+00:00"}
    again = journal.audit_publication_intent(
        tmp_path, 1, audit._audit_intent(later, 1), logical=logical, record=later)
    assert again["record"] == record
    other = {**record, "head_sha": "sha2"}
    other_logical = audit._audit_logical(1, {"proposal_id": "p1"}, "different diff", "sha2")
    with pytest.raises(journal.FabricHeld, match="metabolism_audit_publication_held"):
        journal.audit_publication_intent(
            tmp_path, 1, audit._audit_intent(other, 1), logical=other_logical, record=other)
    with pytest.raises(journal.FabricHeld, match="metabolism_audit_publication_missing"):
        journal.audit_publication_commit(
            tmp_path, 1, record, event_id="d" * 16, receipt={"event_id": "d" * 16})
