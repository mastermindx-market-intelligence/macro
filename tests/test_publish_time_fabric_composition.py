"""PublishTime public owner -> real factory/client -> pinned native B/A.

The paired native owners, durable outbox and shared usage path are real. Grants,
credentials, upstream responses and the separate process-race model boundary
are synthetic; no test publishes content or contacts a provider.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import threading
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine.marketing import outbox, publish_time_content as pt
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_publish_time_llm_phrase import NOW, TEMPLATE, FACTS, CLEAN_PHRASE, _seed_tape, _lane_cfg

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
CLIENT = transport.FabricInferenceClient
IDENTITY = {"lane": "publish_time_wire", "session": "2026-07-23", "kind": "mover", "subject": "NVDA"}


@pytest.fixture
def armed(selected, monkeypatch, tmp_path):
    state = selected
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("legacy discovery")))
    monkeypatch.setattr(pt, "_resolve_wire_model", Mock(side_effect=AssertionError("legacy model")))
    state.content_root = tmp_path / "publish"
    state.content_root.mkdir()
    state.cfg = {"enabled": True, "budget_s": 3.0, "client_timeout_s": 4.0}
    state.identity = deepcopy(IDENTITY)
    state.context = {"slot": "AM", "account": "flagship"}
    state.operations, state.closes = [], []
    state.worker_done = threading.Event()
    state.native.response = {"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": CLEAN_PHRASE}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    original_begin, original_close, original_worker = auth.begin_operation, CLIENT.close, pt._pt_fabric_worker

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    def worker(*args, **kwargs):
        try:
            return original_worker(*args, **kwargs)
        finally:
            state.worker_done.set()

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(CLIENT, "close", close)
    monkeypatch.setattr(pt, "_pt_fabric_worker", worker)
    state.phrase = lambda **kw: pt.phrase_or_template(kw.pop("template", TEMPLATE),
        facts=kw.pop("facts", FACTS), kind=kw.pop("kind", "mover"), now=kw.pop("now", NOW),
        cfg=kw.pop("cfg", state.cfg), root=kw.pop("root", state.content_root),
        operation_identity=kw.pop("operation_identity", state.identity),
        operation_context=kw.pop("operation_context", state.context), **kw)
    state.entry = lambda: outbox.read_publish_time_operation(state.content_root, state.identity)
    pt.reset_phrase_stats()
    yield state
    if getattr(state.native, "block", None) is not None:
        state.native.block.set()
    pt.reset_phrase_stats()


def assert_closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def test_claim_and_dispatch_are_durable_before_actual_send(armed, monkeypatch):
    state = armed
    bind = auth.build_fabric_provider
    create = CLIENT.create

    def claimed(*args, **kwargs):
        entry = state.entry()
        assert entry["state"] == "pending" and not entry["dispatch_possible"]
        assert entry["operation_id"] == kwargs["request_id"]
        assert 0 < kwargs["workload_cfg"]["client_timeout_s"] <= 3.0
        assert kwargs["workload_cfg"]["client_max_retries"] == 0
        assert entry["input"]["facts"] == FACTS
        return bind(*args, **kwargs)

    def dispatched(client, **kwargs):
        assert state.entry()["dispatch_possible"] is True
        return create(client, **kwargs)

    monkeypatch.setattr(auth, "build_fabric_provider", claimed)
    monkeypatch.setattr(CLIENT, "create", dispatched)
    result = state.phrase()
    assert result["mode"] == "llm" and result["text"] == CLEAN_PHRASE
    entry = state.entry()
    assert entry["state"] == "terminal" and entry["delivery"]["mode"] == "llm"
    assert entry["receipt"]["model"] == entry["receipt"]["requested_model"] == MODEL
    assert entry["receipt"]["usage"]["input_tokens"] == 11
    assert entry["receipt"]["usage"]["output_tokens"] == 7
    assert entry["receipt"]["response_observed"] and entry["receipt"]["close"]["closed"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["stage"] == "publish_time_wire"
    request = json.loads(state.native.posts[0][1])
    assert request["max_tokens"] == 220 and request["model"] == MODEL
    assert request["stream"] is False and "tools" not in request
    result["fabric_operation"]["receipt"]["usage"]["input_tokens"] = 999
    assert state.entry()["receipt"]["usage"]["input_tokens"] == 11
    assert_closed(state)


def test_completed_replay_has_no_second_usage_or_binding(armed):
    state = armed
    first = state.phrase()
    saved = state.entry()
    second = state.phrase()
    assert first["text"] == second["text"] == CLEAN_PHRASE
    assert second["fabric_reason"] == "fabric_original_completed"
    assert state.entry() == saved
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state)


@pytest.mark.parametrize("change", ["facts", "template", "timestamp", "slot", "account"])
def test_input_churn_retains_daily_original_without_regeneration(armed, change):
    state = armed
    assert state.phrase()["mode"] == "llm"
    kwargs = {}
    if change == "facts": kwargs["facts"] = {**FACTS, "pct": 7.3}
    elif change == "template": kwargs["template"] = TEMPLATE + " Tape check."
    elif change == "timestamp": kwargs["now"] = NOW + timedelta(minutes=1)
    elif change == "slot": kwargs["operation_context"] = {**state.context, "slot": "PM"}
    else: kwargs["operation_context"] = {**state.context, "account": "second"}
    result = state.phrase(**kwargs)
    assert result["mode"] == "fallback_provider"
    assert result["fabric_reason"] == "fabric_original_input_conflict"
    assert result["fabric_operation"]["operation_id"] == state.entry()["operation_id"]
    assert len(state.native.posts) == len(state.costs) == 1


def test_real_deadline_does_not_close_inflight_worker_or_upgrade_template(armed, monkeypatch):
    state = armed
    state.cfg["budget_s"] = 0.7
    response_ready, release = threading.Event(), threading.Event()
    create = CLIENT.create
    def delayed(client, **kwargs):
        response = create(client, **kwargs)
        response_ready.set()
        assert release.wait(3)
        return response
    monkeypatch.setattr(CLIENT, "create", delayed)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(state.phrase)
            assert response_ready.wait(3)
            result = future.result(timeout=3)
        assert result["text"] == TEMPLATE and result["mode"] == "fallback_timeout"
        snapshot = deepcopy(result)
        assert not state.worker_done.is_set() and state.closes == []
        assert state.entry()["state"] == "pending"
        assert state.entry()["delivery"]["mode"] == "fallback_timeout"
    finally:
        release.set()
    assert state.worker_done.wait(3)
    assert state.entry()["result"]["mode"] == "llm"
    assert state.entry()["delivery"]["mode"] == "fallback_timeout"
    assert result == snapshot
    assert state.phrase()["text"] == TEMPLATE
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state)


def test_deadline_before_worker_entry_prevents_binding_and_send(armed, monkeypatch):
    state = armed
    state.cfg["budget_s"] = 0.15
    entered, release = threading.Event(), threading.Event()
    worker = pt._pt_fabric_worker
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return worker(*args, **kwargs)
    monkeypatch.setattr(pt, "_pt_fabric_worker", delayed)
    try:
        result = state.phrase()
        assert entered.is_set() and result["mode"] == "fallback_timeout"
        assert state.operations == state.closes == state.native.posts == []
    finally:
        release.set()
    assert state.worker_done.wait(3)
    entry = state.entry()
    assert entry["state"] == "terminal" and not entry["dispatch_possible"]
    assert entry["receipt"]["native_disposition"] == "not_dispatched"
    assert not entry["receipt"]["send_attempted"]
    assert state.phrase()["text"] == TEMPLATE
    assert state.operations == state.closes == state.native.posts == state.costs == []


def test_deadline_after_binding_before_dispatch_suppresses_send(armed, monkeypatch):
    state = armed
    state.cfg["budget_s"] = 0.15
    release, bound = threading.Event(), threading.Event()
    begin = auth.begin_operation
    def delayed(*args, **kwargs):
        operation = begin(*args, **kwargs)
        bound.set()
        assert release.wait(3)
        return operation
    monkeypatch.setattr(auth, "begin_operation", delayed)
    try:
        result = state.phrase()
        assert bound.is_set() and result["mode"] == "fallback_timeout"
        assert state.closes == state.native.posts == []
    finally:
        release.set()
    assert state.worker_done.wait(3)
    assert not state.entry()["receipt"]["send_attempted"]
    assert state.native.posts == state.costs == []
    assert_closed(state)


def test_known_response_with_slow_close_remains_worker_owned(armed, monkeypatch):
    state = armed
    state.cfg["budget_s"] = 0.7
    closing, release = threading.Event(), threading.Event()
    close = CLIENT.close
    def delayed(client):
        closing.set()
        assert release.wait(3)
        return close(client)
    monkeypatch.setattr(CLIENT, "close", delayed)
    try:
        result = state.phrase()
        assert closing.is_set() and result["mode"] == "fallback_timeout"
        assert len(state.costs) == 1 and state.closes == []
        assert not state.worker_done.is_set()
    finally:
        release.set()
    assert state.worker_done.wait(3)
    assert state.entry()["receipt"]["usage"]["input_tokens"] == 11
    assert state.entry()["delivery"]["mode"] == "fallback_timeout"
    assert state.phrase()["text"] == TEMPLATE and len(state.costs) == 1
    assert_closed(state)


def test_concurrent_callers_do_not_bind_original_pending_again(armed):
    state = armed
    state.native.block = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(state.phrase)
            assert state.native.arrived.wait(3)
            second = state.phrase()
            assert second["fabric_operation"]["state"] == "pending"
            assert second["fabric_operation"]["operation_id"] == state.entry()["operation_id"]
            state.native.block.set()
            assert first.result(timeout=3)["text"] == TEMPLATE
    finally:
        state.native.block.set()
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state)


def test_two_processes_share_existing_activity_claim(armed, tmp_path):
    state = armed
    seed = tmp_path / "request.json"
    seed.write_text(json.dumps([str(state.content_root), state.identity, state.context, TEMPLATE, FACTS]))
    script = r'''
import json,sys
from datetime import datetime
from engine.marketing import publish_time_content as p,outbox
root,identity,context,template,facts=json.loads(open(sys.argv[1]).read())
p._pt_fabric_route=lambda *_a,**_k:(None,{"client_timeout_s":4.0},{"fixture":"synthetic"})
def worker(root,entry,*args):
    print("PREPARED",flush=True)
    sys.stdin.readline()
    return outbox.update_publish_time_operation(root,entry["identity"],entry["operation_id"],outcome={
      "state":"terminal","receipt":{"operation_id":entry["operation_id"],"effect_unknown":False,
       "send_attempted":False,"response_observed":False,"close":{}},
      "result":{"text":None,"mode":"fallback_provider","provider":None,"violations":[],"reason":"synthetic"}})
p._pt_fabric_worker=worker
result=p.phrase_or_template(template,facts=facts,now=datetime.fromisoformat("2026-07-23T14:05:00+00:00"),
 cfg={"enabled":True,"budget_s":5.0},root=root,operation_identity=identity,operation_context=context)
print(json.dumps(result),flush=True)
'''
    environment = {**os.environ, "MARKETING_LLM_ENABLED": "1"}
    cwd = Path(pt.__file__).resolve().parents[2]
    first = subprocess.Popen([sys.executable, "-c", script, str(seed)], cwd=cwd, env=environment,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([first.stdout], [], [], 5)[0]
        assert first.stdout.readline().strip() == "PREPARED"
        original = state.entry()
        second = subprocess.run([sys.executable, "-c", script, str(seed)], cwd=cwd,
            env=environment, input="", capture_output=True, text=True, timeout=5)
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout)["fabric_operation"]["operation_id"] == original["operation_id"]
        stdout, stderr = first.communicate("\n", timeout=5)
        assert first.returncode == 0, stderr
        assert json.loads(stdout)["fabric_operation"]["operation_id"] == original["operation_id"]
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate(timeout=5)
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("fault", ["empty", "blank", "tools", "truncated", "refusal", "http", "model", "wire"])
def test_known_rejected_outcome_cannot_regenerate_or_fall_back_to_native(armed, fault):
    state = armed
    choice = state.native.response["choices"][0]
    if fault == "empty": choice["message"]["content"] = ""
    elif fault == "blank": choice["message"]["content"] = "   "
    elif fault == "tools":
        choice["finish_reason"] = "tool_calls"
        choice["message"]["tool_calls"] = [{"id": "tool1", "type": "function",
            "function": {"name": "read", "arguments": "{}"}}]
    elif fault == "truncated": choice["finish_reason"] = "length"
    elif fault == "refusal": choice["finish_reason"] = "content_filter"
    elif fault == "http": state.native.response_status = 503
    elif fault == "model": state.native.response["model"] = "unexpected"
    else: choice["message"]["content"] = "$NVDA up 99.1% today!!!"
    for _ in range(2):
        assert state.phrase()["text"] == TEMPLATE
    assert state.entry()["state"] == "terminal"
    assert state.entry()["result"]["text"] is None
    assert len(state.native.posts) == 1
    assert_closed(state)


@pytest.mark.parametrize("known_usage", [True, False])
def test_lost_close_retains_known_answer_and_explicit_usage_uncertainty(armed, monkeypatch, known_usage):
    state = armed
    if not known_usage:
        state.native.response["usage"]["completion_tokens"] = None
    monkeypatch.setattr(CLIENT, "close", Mock(side_effect=OSError("close lost")))
    assert state.phrase()["mode"] == "llm"
    entry = state.entry()
    assert entry["state"] == "held" and entry["receipt"]["close"]["effect_unknown"]
    assert entry["receipt"]["usage"]["input_tokens"] == (11 if known_usage else None)
    assert state.phrase()["mode"] == "llm"
    assert len(state.native.posts) == 1 and len(state.costs) == (1 if known_usage else 0)


@pytest.mark.parametrize("selection", [None, "invalid mode", "another_mode"])
def test_original_hold_survives_selector_removal_change_and_restart(armed, monkeypatch, selection):
    state = armed
    monkeypatch.setattr(state.native.gateway, "complete_application", Mock(side_effect=OSError("settlement lost")))
    assert state.phrase()["text"] == TEMPLATE
    entry = state.entry()
    assert entry["state"] == "held"
    environment = dict(os.environ)
    if selection is None: environment.pop(auth.APPLICATION_MODE_ENV, None)
    else: environment[auth.APPLICATION_MODE_ENV] = selection
    script = '''import json,sys
from datetime import datetime
from engine.marketing import publish_time_content as p
root,identity,context,template,facts,cfg=json.loads(sys.stdin.read())
print(json.dumps(p.phrase_or_template(template,facts=facts,now=datetime.fromisoformat("2026-07-23T14:05:00+00:00"),
cfg=cfg,root=root,operation_identity=identity,operation_context=context)))'''
    completed = subprocess.run([sys.executable, "-c", script], input=json.dumps([
        str(state.content_root), state.identity, state.context, TEMPLATE, FACTS, state.cfg]),
        cwd=Path(pt.__file__).resolve().parents[2], env=environment, capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["text"] == TEMPLATE
    assert result["fabric_operation"]["operation_id"] == entry["operation_id"]
    assert len(state.native.posts) == 1


@pytest.mark.parametrize("fault", ["lock", "read", "write", "fsync", "readback"])
def test_unconfirmed_claim_never_binds(armed, monkeypatch, fault):
    state = armed
    if fault == "lock":
        @contextmanager
        def unlocked(*_a, **_k): yield False
        monkeypatch.setattr(outbox, "_outbox_lock", unlocked)
    elif fault == "read": monkeypatch.setattr(outbox, "_pt_ai_read_all", Mock(side_effect=OSError("read failed")))
    elif fault == "write": monkeypatch.setattr(outbox, "_pt_ai_append", Mock(side_effect=OSError("write failed")))
    elif fault == "fsync": monkeypatch.setattr(outbox.os, "fsync", Mock(side_effect=OSError("fsync failed")))
    else:
        read = outbox._pt_ai_read_all
        def mismatch(root):
            found = read(root)
            if found: raise OSError("readback lost")
            return found
        monkeypatch.setattr(outbox, "_pt_ai_read_all", mismatch)
    assert state.phrase()["text"] == TEMPLATE
    assert state.native.posts == state.operations == state.costs == []


@pytest.mark.parametrize("raw", [b'{', b'{"type":"one","type":"two"}\n', b'{"a":NaN}\n', b'[]\n', b'\n'])
def test_corrupt_activity_is_not_absence(armed, raw):
    state = armed
    path = outbox._activity_path(state.content_root)
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    result = state.phrase()
    assert result["fabric_reason"] == "fabric_original_state_unreadable"
    assert state.native.posts == state.operations == state.costs == []
    assert path.read_bytes() == raw


@pytest.mark.parametrize("fault", ["dispatch", "outcome", "delivery"])
def test_failed_transition_cannot_send_or_emit_unconfirmed_model_copy(armed, monkeypatch, fault):
    state = armed
    update = outbox.update_publish_time_operation
    def fail(*args, **kwargs):
        if kwargs.get(fault) is not None and (fault != "dispatch" or kwargs["dispatch"]):
            raise OSError("transition lost")
        return update(*args, **kwargs)
    monkeypatch.setattr(outbox, "update_publish_time_operation", fail)
    result = state.phrase()
    assert result["text"] == TEMPLATE
    assert len(state.native.posts) == (0 if fault == "dispatch" else 1)
    assert state.phrase()["text"] == TEMPLATE
    assert len(state.native.posts) <= 1


@pytest.mark.parametrize("gate", ["disabled", "env", "cap", "dry", "root", "identity", "profile"])
def test_gates_do_not_claim_bind_or_write(armed, monkeypatch, gate):
    state = armed
    kwargs = {}
    if gate == "disabled": state.cfg["enabled"] = False
    elif gate == "env": monkeypatch.delenv("MARKETING_LLM_ENABLED")
    elif gate == "cap": state.cfg["max_calls_per_run"] = 0
    elif gate == "dry": kwargs["live"] = False
    elif gate == "root": kwargs["root"] = None
    elif gate == "identity": kwargs["operation_identity"] = None
    else: state.cfg["workload_profile"] = None
    assert state.phrase(**kwargs)["text"] == TEMPLATE
    assert state.native.posts == state.operations == state.costs == []
    assert not (state.content_root / "data").exists()


def _generate(state, monkeypatch, *, live=True):
    _seed_tape(state.content_root)
    cfg = _lane_cfg({"enabled": True, "budget_s": 3.0})
    cfg["publish"]["publish_time_movers"]["require_card"] = False
    state.native.response["choices"][0]["message"]["content"] = "$AMD tape check."
    return pt.generate_slot_items(state.content_root, cfg=cfg, now=NOW,
        state=outbox.fold_state(state.content_root), approved_due=[], posted_counts={},
        cap=2, live=live, account_filter=None)


def test_public_generator_retains_receipt_in_report_and_item(armed, monkeypatch):
    state = armed
    captured = []
    monkeypatch.setattr(outbox, "enqueue", lambda item, *_a, **_k: captured.append(deepcopy(item)) or "queued")
    report = _generate(state, monkeypatch)
    assert report["generated"] and report["llm_phrase_modes"] == {"llm": 1}
    receipt = report["llm_phrase_operations"][0]
    assert captured[0]["source"]["fabric_phrase"] == receipt
    assert receipt["operation"]["identity"]["subject"] == "AMD"
    assert len(state.native.posts) == len(state.costs) == 1


@pytest.mark.parametrize("failure", ["session", "make_item", "enqueue"])
def test_post_phrase_drops_and_outer_error_preserve_durable_receipt(armed, monkeypatch, failure):
    state = armed
    if failure == "session": monkeypatch.setattr(pt, "_session_conflict", lambda *_a, **_k: "forced")
    elif failure == "make_item": monkeypatch.setattr(outbox, "make_item", Mock(side_effect=ValueError("forced")))
    else: monkeypatch.setattr(outbox, "enqueue", Mock(side_effect=OSError("forced")))
    report = _generate(state, monkeypatch)
    assert not report["generated"] and report["dropped"]
    assert len(report["llm_phrase_operations"]) == 1
    original = report["llm_phrase_operations"][0]["operation"]
    saved = outbox.read_publish_time_operation(state.content_root, original["identity"])
    assert saved["operation_id"] == original["operation_id"]
    _generate(state, monkeypatch)
    assert len(state.native.posts) == len(state.costs) == 1


def test_selected_generator_dry_run_has_no_activity_or_model(armed, monkeypatch):
    state = armed
    report = _generate(state, monkeypatch, live=False)
    assert report["would_generate"]
    assert report["llm_phrase_operations"][0]["reason"] == "fabric_dry_run_no_claim"
    assert not outbox._activity_path(state.content_root).exists()
    assert not outbox.outbox_dir(state.content_root).exists()
    assert state.native.posts == state.operations == state.costs == []


def test_saved_result_validation_cannot_promote_previously_rejected_text(armed, monkeypatch):
    state = armed
    state.native.response["choices"][0]["message"]["content"] = "$NVDA up 99.1% today!!!"
    assert state.phrase()["mode"] == "fallback_validation"
    monkeypatch.setattr(pt, "wire_violations", lambda *_a, **_k: [])
    assert state.phrase()["text"] == TEMPLATE
    assert len(state.native.posts) == 1


def test_result_replay_must_pass_current_validator(armed, monkeypatch):
    state = armed
    assert state.phrase()["mode"] == "llm"
    monkeypatch.setattr(pt, "wire_violations", lambda *_a, **_k: ["new_wire_rule"])
    result = state.phrase()
    assert result["text"] == TEMPLATE and result["mode"] == "fallback_validation"
    assert len(state.native.posts) == len(state.costs) == 1


def test_activity_chain_refuses_changed_original_or_replaced_delivery(armed):
    state = armed
    assert state.phrase()["mode"] == "llm"
    path = outbox._activity_path(state.content_root)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    bad = deepcopy(rows[-1])
    bad["revision"] += 1
    bad["operation"]["input"]["facts"]["pct"] = 7.3
    bad["operation"]["input_sha256"] = hashlib.sha256(outbox._pt_ai_json(bad["operation"]["input"])).hexdigest()
    with path.open("a") as handle: handle.write(json.dumps(bad) + "\n")
    assert state.phrase()["fabric_reason"] == "fabric_original_state_unreadable"
    assert len(state.native.posts) == 1


def test_normal_activity_records_coexist_and_original_is_not_tail_limited(armed):
    state = armed
    outbox._append_activity(state.content_root, {"kind": "ordinary", "count": 1})
    assert state.phrase()["mode"] == "llm"
    original = state.entry()
    for number in range(25):
        outbox._append_activity(state.content_root, {"kind": "ordinary", "count": number})
    assert state.phrase()["mode"] == "llm"
    assert state.entry() == original and len(state.native.posts) == 1


def test_theme_lead_and_account_change_do_not_create_new_daily_operation(armed):
    state = armed
    state.identity.update(kind="theme_list", subject="Semiconductors")
    assert state.phrase(kind="theme_list")["mode"] == "llm"
    original = state.entry()
    result = state.phrase(kind="theme_list", facts={**FACTS, "ticker": "AMD"},
        operation_context={"slot": "PM", "account": "another"})
    assert result["fabric_operation"]["operation_id"] == original["operation_id"]
    assert result["text"] == TEMPLATE and len(state.native.posts) == 1


def test_new_session_retains_prior_original_and_has_distinct_identity(armed):
    state = armed
    assert state.phrase()["mode"] == "llm"
    original = state.entry()
    tomorrow = {**state.identity, "session": "2026-07-24"}
    result = state.phrase(operation_identity=tomorrow, now=NOW + timedelta(days=1))
    assert result["fabric_operation"]["operation_id"] != original["operation_id"]
    assert state.entry() == original and len(state.native.posts) == 2


def test_deadline_during_dispatch_persistence_prevents_send_without_blocking_caller(armed, monkeypatch):
    state = armed
    state.cfg["budget_s"] = 0.15
    persisting, release = threading.Event(), threading.Event()
    update = outbox.update_publish_time_operation
    def delayed(*args, **kwargs):
        if kwargs.get("dispatch"):
            persisting.set()
            assert release.wait(3)
        return update(*args, **kwargs)
    monkeypatch.setattr(outbox, "update_publish_time_operation", delayed)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(state.phrase)
            assert persisting.wait(2)
            result = future.result(timeout=1)
        assert result["mode"] == "fallback_timeout" and state.native.posts == []
        assert not state.worker_done.is_set()
    finally:
        release.set()
    assert state.worker_done.wait(3)
    entry = state.entry()
    assert entry["dispatch_possible"] and not entry["receipt"]["send_attempted"]
    assert entry["receipt"]["native_disposition"] == "not_dispatched"
    assert state.native.posts == state.costs == []
    assert_closed(state)


def test_two_public_generators_keep_first_template_choice(armed, monkeypatch):
    state = armed
    state.native.block = threading.Event()
    captured = []
    monkeypatch.setattr(outbox, "enqueue", lambda item, *_a, **_k: captured.append(deepcopy(item)) or "queued")
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(_generate, state, monkeypatch)
            assert state.native.arrived.wait(3)
            second = _generate(state, monkeypatch)
            assert second["generated"] and second["llm_phrase_modes"] == {"fallback_provider": 1}
            state.native.block.set()
            original = first.result(timeout=3)
            assert original["llm_phrase_modes"] == {"fallback_provider": 1}
    finally:
        state.native.block.set()
    assert len(captured) == 2 and captured[0]["text"] == captured[1]["text"]
    identities = [row["source"]["fabric_phrase"]["operation"]["operation_id"] for row in captured]
    assert len(set(identities)) == 1 and len(state.native.posts) == len(state.costs) == 1


@pytest.mark.parametrize("location", ["outer", "publish", "lane"])
def test_full_config_caller_selection_cannot_disappear(armed, monkeypatch, location):
    state = armed
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    cfg = _lane_cfg({"enabled": True, "budget_s": 3.0})
    level = cfg if location == "outer" else cfg["publish"] if location == "publish" else cfg["publish"]["publish_time_movers"]
    level["application_fabric_mode"] = "shared_fabric"
    assert state.phrase(cfg=cfg)["mode"] == "llm"
    assert len(state.native.posts) == 1


@pytest.mark.parametrize("location", ["outer", "publish", "lane"])
def test_explicit_outer_invalid_profile_cannot_be_defaulted(armed, location):
    state = armed
    cfg = _lane_cfg({"enabled": True})
    level = cfg if location == "outer" else cfg["publish"] if location == "publish" else cfg["publish"]["publish_time_movers"]
    level["workload_profile"] = None
    assert state.phrase(cfg=cfg)["text"] == TEMPLATE
    assert state.native.posts == state.operations == []


def test_conflicting_outer_and_inner_selection_refuses(armed):
    state = armed
    cfg = _lane_cfg({"enabled": True, "application_fabric_mode": "shared_fabric"})
    cfg["application_fabric_mode"] = "another_mode"
    assert state.phrase(cfg=cfg)["text"] == TEMPLATE
    assert state.native.posts == state.operations == []


def test_ambiguous_delivery_append_reconciles_original_without_another_append(armed, monkeypatch):
    state = armed
    append = outbox._pt_ai_append
    calls = []
    def lose_confirmation(root, key, revision, entry):
        result = append(root, key, revision, entry)
        if entry["delivery"] and entry["delivery"]["mode"] == "llm":
            calls.append(entry["operation_id"])
            raise OSError("append confirmed but return lost")
        return result
    monkeypatch.setattr(outbox, "_pt_ai_append", lose_confirmation)
    result = state.phrase()
    assert result["text"] == CLEAN_PHRASE and result["fabric_emit_allowed"]
    assert state.phrase()["text"] == CLEAN_PHRASE
    assert len(calls) == len(state.native.posts) == len(state.costs) == 1


def test_unreconciled_delivery_is_explicitly_non_emitting_at_public_boundary(armed, monkeypatch):
    state = armed
    append = outbox._pt_ai_append
    def lose_confirmation(root, key, revision, entry):
        result = append(root, key, revision, entry)
        if entry["delivery"]:
            raise OSError("confirmation lost")
        return result
    monkeypatch.setattr(outbox, "_pt_ai_append", lose_confirmation)
    monkeypatch.setattr(outbox, "confirm_publish_time_delivery", Mock(side_effect=OSError("unreadable")))
    enqueue = Mock(side_effect=AssertionError("unconfirmed copy emitted"))
    monkeypatch.setattr(outbox, "enqueue", enqueue)
    report = _generate(state, monkeypatch)
    assert not report["generated"]
    receipt = report["llm_phrase_operations"][0]
    assert receipt["emit_allowed"] is False
    assert report["dropped"][0]["reason"] == "fabric_delivery_unconfirmed"
    assert len(state.native.posts) == len(state.costs) == 1
    enqueue.assert_not_called()


def test_post_claim_thread_failure_retains_original_receipt_without_rebinding(armed, monkeypatch):
    state = armed
    monkeypatch.setattr(pt, "_run_with_deadline", Mock(side_effect=RuntimeError("start unconfirmed")))
    first = state.phrase()
    assert first["fabric_reason"] == "fabric_worker_start_unconfirmed"
    assert first["fabric_operation"]["operation_id"] == state.entry()["operation_id"]
    assert state.entry()["state"] == "pending"
    assert state.phrase()["text"] == TEMPLATE
    assert state.native.posts == state.operations == []


@pytest.mark.parametrize("contradiction", ["close", "close_disposition", "native", "usage"])
def test_saved_outcome_contradictions_are_refused(armed, contradiction):
    state = armed
    assert state.phrase()["mode"] == "llm"
    path = outbox._activity_path(state.content_root)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        entry = row.get("operation") or {}
        if entry.get("state") != "terminal": continue
        receipt = entry["receipt"]
        if contradiction == "close": receipt["close"]["effect_unknown"] = True
        elif contradiction == "close_disposition": receipt["close"]["disposition"] = "pending"
        elif contradiction == "native": receipt["native_disposition"] = "effect_unknown"
        else: receipt["usage"]["usage_state"] = "unknown"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert state.phrase()["fabric_reason"] == "fabric_original_state_unreadable"
    assert len(state.native.posts) == 1


def test_invalid_selector_during_original_pending_cannot_emit_competing_copy(armed, monkeypatch):
    state = armed
    state.native.block = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(state.phrase)
            assert state.native.arrived.wait(3)
            monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "invalid mode")
            second = state.phrase()
            assert second["fabric_operation"]["state"] == "pending"
            assert second["fabric_emit_allowed"] is False
            state.native.block.set()
            assert first.result(timeout=3)["mode"] == "llm"
    finally:
        state.native.block.set()
    assert len(state.native.posts) == len(state.costs) == 1
