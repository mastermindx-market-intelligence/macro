"""Intelligence Desk public owner -> real shared Fabric/native owners.

Native grants, credentials, answers and the separate process-race model boundary
are synthetic. These tests do not contact a provider or publish a desk draft.
"""
from concurrent.futures import ThreadPoolExecutor
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
from engine.marketing import intelligence_llm as desk
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401
from tests.test_marketing_intelligence_desk import _confirmed_packet, _GOOD_REPLY, _llm_cfg, NOW

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="paired native Mastermind source required")
CLIENT = transport.FabricInferenceClient


@pytest.fixture
def armed(selected, monkeypatch, tmp_path):
    state = selected
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    monkeypatch.setenv("MARKETING_LLM_ENABLED", "1")
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("legacy discovery")))
    monkeypatch.setattr(desk, "_resolve_model_id", Mock(side_effect=AssertionError("legacy model")))
    state.content_root = tmp_path / "desk"
    state.content_root.mkdir()
    state.block = _llm_cfg()["llm"]
    state.packet = _confirmed_packet()
    state.operations, state.closes = [], []
    state.native.response = {"model": MODEL, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": _GOOD_REPLY}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    original_begin, original_close = auth.begin_operation, CLIENT.close

    def begin(*args, **kwargs):
        operation = original_begin(*args, **kwargs)
        state.operations.append((operation, tuple(operation.providers)))
        return operation

    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)

    monkeypatch.setattr(auth, "begin_operation", begin)
    monkeypatch.setattr(CLIENT, "close", close)
    state.phrase = lambda packet=None, **kw: desk.phrase_packet(
        state.packet if packet is None else packet,
        block=kw.pop("block", state.block), now=kw.pop("now", NOW),
        shapes=kw.pop("shapes", ("wire", "analysis")),
        root=kw.pop("root", state.content_root), **kw)
    state.cache = lambda: desk._read_cache_strict(state.content_root)
    state.entry = lambda: state.cache()[state.packet["id"]]["fabric_operation"]
    desk.reset_stats()
    return state


def assert_closed(state, count=1):
    assert len(state.operations) == len(state.closes) == count
    assert all(operation.providers == [] and providers[0]["_fabric_closed"]
               for operation, providers in state.operations)


def test_public_success_claim_precedes_binding_and_retains_model_usage_and_review(armed, monkeypatch):
    state = armed
    state.block.update(client_timeout_s=75, client_max_retries=5)
    bind = auth.build_fabric_provider

    def claimed(*args, **kwargs):
        entry = state.entry()
        assert kwargs["workload_cfg"]["client_timeout_s"] == 12
        assert kwargs["workload_cfg"]["client_max_retries"] == 0
        assert entry["state"] == "pending" and entry["receipt"] is None
        assert entry["operation_id"] == kwargs["request_id"]
        assert entry["input"]["facts"] == desk.build_fact_packet(state.packet)
        return bind(*args, **kwargs)

    monkeypatch.setattr(auth, "build_fabric_provider", claimed)
    result = state.phrase()
    assert all(result[key] for key in ("analysis", "why", "wire", "replied"))
    entry = state.entry()
    assert entry["state"] == "terminal"
    assert entry["receipt"]["model"] == MODEL
    assert entry["receipt"]["usage"]["input_tokens"] == 11
    assert entry["receipt"]["usage"]["output_tokens"] == 7
    assert entry["receipt"]["close"]["closed"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert state.costs[0]["model"] == MODEL and state.costs[0]["stage"] == "intelligence_desk"
    provider = state.operations[0][1][0]
    assert provider["client"]._client._timeout == 12.0
    request = json.loads(state.native.posts[0][1])
    assert request["model"] == MODEL and request["max_tokens"] == 500
    assert request["stream"] is False and "tools" not in request
    assert entry["input"]["max_tokens"] == 500
    assert set(entry["result"]["accepted"]) == {"analysis", "wire", "why"}
    for draft in entry["result"]["drafts"]:
        assert draft["requires_review"] is True and draft["origin"] == "llm"
        assert draft["status"] == "review" and draft["updated_at"] == desk._iso(NOW)
        assert draft["characters"] == len(draft["text"])
    assert_closed(state)


def test_replay_preserves_original_timestamp_and_requested_shapes_without_spend(armed):
    state = armed
    original = deepcopy(state.packet)
    assert state.phrase()["analysis"]
    frozen = state.entry()
    again = deepcopy(original)
    again["updated_at"] = desk._iso(NOW + timedelta(hours=1))
    result = state.phrase(again, now=NOW + timedelta(hours=1), shapes=("analysis",))
    assert result["analysis"] and result["why"] and not result["wire"]
    assert [d for d in again["drafts"] if d["shape"] == "analysis"] == [
        d for d in frozen["result"]["drafts"] if d["shape"] == "analysis"]
    assert [d for d in again["drafts"] if d["shape"] == "wire"] == [
        d for d in original["drafts"] if d["shape"] == "wire"]
    assert state.entry() == frozen
    assert len(state.native.posts) == len(state.costs) == 1


def test_fact_time_change_is_original_conflict_without_regeneration(armed):
    state = armed
    state.packet["market"] = {"label": "steady", "basis": "observed", "as_of": desk._iso(NOW)}
    original = deepcopy(state.packet)
    assert state.phrase()["why"]
    changed = deepcopy(original)
    changed["market"]["as_of"] = desk._iso(NOW + timedelta(minutes=1))
    before = deepcopy(changed)
    result = state.phrase(changed)
    assert result["fabric_reason"] == "fabric_original_input_conflict"
    assert changed == before and len(state.native.posts) == 1


def test_rejected_field_cannot_become_accepted_on_replay(armed, monkeypatch):
    state = armed
    reply = json.loads(_GOOD_REPLY)
    reply["why"] = "Borrowing costs stay at 4.25% into the autumn."
    state.native.response["choices"][0]["message"]["content"] = json.dumps(reply)
    original = deepcopy(state.packet)
    first = state.phrase()
    assert first["analysis"] and not first["why"]
    assert "why" not in state.entry()["result"]["accepted"]
    monkeypatch.setattr(desk, "validate_desk_copy", lambda *_a, **_k: [])
    again = deepcopy(original)
    result = state.phrase(again)
    assert not result["why"] and again["why_it_matters_en"] == original["why_it_matters_en"]
    assert len(state.native.posts) == 1


@pytest.mark.parametrize("mode", [None, "", "UNKNOWN"])
def test_invalid_selection_is_exclusive_before_native_credentials(armed, monkeypatch, mode):
    state = armed
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.block[auth.APPLICATION_MODE_CFG_KEY] = mode
    result = state.phrase()
    assert result["fabric_selected"] and not result["replied"]
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("profile", [None, "", "development_agent"])
def test_invalid_explicit_workload_is_not_replaced_by_default(armed, profile):
    armed.block["workload_profile"] = profile
    assert not armed.phrase()["replied"]
    assert armed.events == armed.native.posts == armed.operations == []


def test_selected_public_root_and_private_helper_cannot_bypass_durable_owner(armed):
    state = armed
    assert state.phrase(root=None)["fabric_reason"] == "fabric_durable_root_required"
    absent = state.content_root / "missing"
    assert not state.phrase(root=absent)["replied"] and not absent.exists()
    assert desk._call_model(desk.build_fact_packet(state.packet), state.block,
                            shapes=("wire", "analysis")) == {}
    assert state.events == state.native.posts == state.operations == []


@pytest.mark.parametrize("gate", ["config", "environment", "eligibility"])
def test_cached_public_replay_obeys_current_gates_without_erasing_original(armed, monkeypatch, gate):
    state = armed
    original = deepcopy(state.packet)
    assert state.phrase()["wire"]
    entry = state.entry()
    again = deepcopy(original)
    if gate == "config":
        state.block["enabled"] = False
    elif gate == "environment":
        monkeypatch.delenv("MARKETING_LLM_ENABLED")
    else:
        again["stage"] = "watch"
    before = deepcopy(again)
    result = state.phrase(again)
    assert result["fabric_reason"] == "fabric_original_not_armed_or_eligible"
    assert again == before and state.entry() == entry and len(state.native.posts) == 1


@pytest.mark.parametrize("fault", ["write", "fsync", "directory", "readback"])
def test_claim_failure_prevents_provider_effects(armed, monkeypatch, fault):
    state = armed
    if fault == "write":
        monkeypatch.setattr(desk, "_write_cache_strict", Mock(side_effect=OSError("write failed")))
    elif fault == "fsync":
        monkeypatch.setattr(desk.os, "fsync", Mock(side_effect=OSError("fsync failed")))
    elif fault == "directory":
        monkeypatch.setattr(desk, "_fsync_cache_directory", Mock(side_effect=OSError("directory failed")))
    else:
        read = desk._read_cache_strict
        def readback(root):
            result = read(root)
            if any("fabric_operation" in row for row in result.values()):
                raise OSError("readback unconfirmed")
            return result
        monkeypatch.setattr(desk, "_read_cache_strict", readback)
    before = deepcopy(state.packet)
    assert not state.phrase()["replied"]
    assert state.packet == before
    assert state.events == state.native.posts == state.operations == state.costs == []


@pytest.mark.parametrize("index", range(4))
def test_each_ancestor_is_resynchronized_after_visible_mkdir_failure(armed, monkeypatch, index):
    state = armed
    directories = [state.content_root, state.content_root / "data",
                   state.content_root / "data/marketing", state.content_root / "data/marketing/press"]
    sync = desk._fsync_cache_directory
    visits, fail = [], [True]
    def observed(path):
        visits.append(Path(path))
        if fail[0] and Path(path) == directories[index]:
            raise OSError("ancestor not confirmed")
        return sync(path)
    monkeypatch.setattr(desk, "_fsync_cache_directory", observed)
    for _ in range(2):
        assert not state.phrase()["replied"]
    assert state.native.posts == state.operations == []
    fail[0] = False
    visits.clear()
    bind = auth.build_fabric_provider
    def verified(*args, **kwargs):
        assert visits[:4] == directories
        return bind(*args, **kwargs)
    monkeypatch.setattr(auth, "build_fabric_provider", verified)
    assert state.phrase()["wire"] and len(state.native.posts) == 1


def test_two_threads_share_one_durable_claim_and_one_native_request(armed):
    state = armed
    original = deepcopy(state.packet)
    state.native.block = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(state.phrase)
            assert state.native.arrived.wait(3)
            other = state.phrase(deepcopy(original))
            assert other["fabric_operation"]["state"] == "pending"
            assert other["fabric_operation"]["operation_id"] == state.entry()["operation_id"]
            state.native.block.set()
            assert first.result(timeout=5)["wire"]
    finally:
        state.native.block.set()
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state)


def test_two_real_processes_share_the_same_public_claim(armed, tmp_path):
    """Only the model boundary is synthetic; cache/lock/public path are real."""
    state = armed
    seed = tmp_path / "input.json"
    seed.write_text(json.dumps([state.packet, state.block, str(state.content_root)]))
    script = r"""
import json,sys
from datetime import datetime
from engine.marketing import intelligence_llm as d
packet,block,root=json.loads(open(sys.argv[1]).read())
d._application_mode=lambda _block:"synthetic"
d._selected_route=lambda *_args:(None, {}, {"fixture":"synthetic"}, 500)
def complete(block,mode,route,entry):
    print("PREPARED",flush=True)
    sys.stdin.readline()
    return {**entry,"state":"terminal",
      "result":{**d._empty_outcome(),"accepted":{},"drafts":[]},
      "receipt":{"operation_id":entry["operation_id"],"effect_unknown":False,
                 "native_disposition":"not_started","close":{}}}
d._complete_selected=complete
result=d.phrase_packet(packet,block=block,now=datetime.fromisoformat("2026-07-29T18:00:00+00:00"),
                      shapes=("wire","analysis"),root=root)
print(json.dumps(result),flush=True)
"""
    environment = {**os.environ, "MARKETING_LLM_ENABLED": "1"}
    cwd = Path(desk.__file__).resolve().parents[2]
    first = subprocess.Popen([sys.executable, "-c", script, str(seed)], cwd=cwd,
        env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([first.stdout], [], [], 5)[0], "first claim did not complete"
        assert first.stdout.readline().strip() == "PREPARED"
        original = state.entry()
        second = subprocess.run([sys.executable, "-c", script, str(seed)], cwd=cwd,
            env=environment, input="", capture_output=True, text=True, timeout=5)
        assert second.returncode == 0, second.stderr
        result = json.loads(second.stdout)
        assert result["fabric_operation"]["operation_id"] == original["operation_id"]
        assert result["fabric_operation"]["state"] == "pending"
        stdout, stderr = first.communicate("\n", timeout=5)
        assert first.returncode == 0, stderr
        assert json.loads(stdout)["fabric_operation"]["operation_id"] == original["operation_id"]
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate(timeout=5)
    assert state.events == state.native.posts == state.operations == []


def test_unknown_survives_restart_selector_removal_and_changed_headline(armed, monkeypatch):
    state = armed
    monkeypatch.setattr(state.native.gateway, "complete_application",
                        Mock(side_effect=OSError("settlement lost")))
    assert not state.phrase()["wire"]
    entry = state.entry()
    assert entry["state"] == "held" and entry["receipt"]["effect_unknown"]
    assert entry["receipt"]["usage"]["input_tokens"] is None
    assert entry["receipt"]["usage"]["completed_input_tokens"] == 11
    child = """import json,sys
from datetime import datetime
from engine.marketing import intelligence_llm as d
packet,block,root=json.loads(sys.stdin.read())
print(json.dumps(d.phrase_packet(packet,block=block,root=root,shapes=("wire","analysis"),
                               now=datetime.fromisoformat("2026-07-29T18:00:00+00:00"))))
"""
    process = subprocess.run([sys.executable, "-c", child],
        input=json.dumps([state.packet, state.block, str(state.content_root)]),
        env={**os.environ, auth.APPLICATION_MODE_ENV: "invalid mode"},
        cwd=Path(desk.__file__).resolve().parents[2], capture_output=True, text=True, timeout=10)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["fabric_operation"]["operation_id"] == entry["operation_id"]
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.packet["headline"] += " Updated"
    assert state.phrase()["fabric_operation"]["operation_id"] == entry["operation_id"]
    assert len(state.native.posts) == len(state.costs) == 1
    assert_closed(state)


@pytest.mark.parametrize("fault", ["empty", "blank", "tools", "truncated", "refusal",
                                   "http", "mismatch", "malformed", "list", "scalar", "duplicate"])
def test_terminal_failure_has_no_native_fallback_or_regeneration(armed, fault):
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
    elif fault == "mismatch": state.native.response["model"] = "unexpected-model"
    elif fault == "malformed": choice["message"]["content"] = "not JSON"
    elif fault == "list": choice["message"]["content"] = "[]"
    elif fault == "scalar": choice["message"]["content"] = "1"
    else: choice["message"]["content"] = '{"why":"first","why":"second"}'
    before = deepcopy(state.packet)
    for _ in range(3):
        result = state.phrase()
        assert not any(result[key] for key in ("analysis", "why", "wire"))
    assert state.packet == before and state.entry()["state"] == "terminal"
    assert len(state.native.posts) == len(state.operations) == 1
    assert_closed(state)


@pytest.mark.parametrize("known_usage", [True, False])
def test_valid_answer_with_lost_close_preserves_artifact_and_original_hold(armed, monkeypatch, known_usage):
    state = armed
    if not known_usage:
        state.native.response["usage"]["completion_tokens"] = None
    monkeypatch.setattr(CLIENT, "close", Mock(side_effect=OSError("close lost")))
    original = deepcopy(state.packet)
    assert state.phrase()["wire"]
    entry = state.entry()
    assert entry["state"] == "held" and entry["receipt"]["close"]["effect_unknown"]
    assert entry["receipt"]["usage"]["input_tokens"] == (11 if known_usage else None)
    assert state.phrase(deepcopy(original))["wire"]
    assert len(state.native.posts) == 1 and len(state.costs) == (1 if known_usage else 0)


def test_unconfirmed_result_write_leaves_original_pending_and_no_draft(armed, monkeypatch):
    state = armed
    write = desk._write_cache_strict
    def fail(root, cache):
        if any(row.get("fabric_operation", {}).get("state") in {"held", "terminal"}
               for row in cache.values()):
            raise OSError("result not durable")
        return write(root, cache)
    monkeypatch.setattr(desk, "_write_cache_strict", fail)
    before = deepcopy(state.packet)
    first = state.phrase()
    assert first["fabric_reason"] == "fabric_result_persistence_unconfirmed"
    assert state.packet == before and state.entry()["state"] == "pending"
    assert state.phrase()["fabric_operation"]["state"] == "pending"
    assert len(state.native.posts) == len(state.costs) == 1


def test_post_response_validator_fault_is_fail_soft_and_never_recalled(armed, monkeypatch):
    state = armed
    monkeypatch.setattr(desk, "validate_desk_copy", Mock(side_effect=RuntimeError("validator unavailable")))
    before = deepcopy(state.packet)
    for _ in range(2):
        assert not state.phrase()["wire"]
    assert state.packet == before and state.entry()["state"] == "terminal"
    assert state.entry()["result"]["violations"] == ["fabric:output_validation_failed"]
    assert len(state.native.posts) == len(state.costs) == 1


def test_crash_after_durable_result_reapplies_original_without_model(armed, monkeypatch):
    state = armed
    apply = desk._apply_selected
    original = deepcopy(state.packet)
    monkeypatch.setattr(desk, "_apply_selected", Mock(side_effect=RuntimeError("caller lost")))
    first = state.phrase()
    assert first["fabric_reason"] == "fabric_original_application_unavailable"
    assert state.packet == original and state.entry()["state"] == "terminal"
    monkeypatch.setattr(desk, "_apply_selected", apply)
    assert state.phrase()["wire"] and len(state.native.posts) == 1


def test_duplicate_shapes_cannot_replace_valid_cache_or_poison_next_story(armed):
    state = armed
    desk.save_cache(state.content_root, {"legacy": {"headline_sha1": "legacy", "ts": desk._iso(NOW)}})
    path = desk._cache_path(state.content_root)
    before = path.read_bytes()
    assert not state.phrase(shapes=("wire", "wire"))["replied"]
    assert path.read_bytes() == before and state.native.posts == state.operations == []
    assert state.phrase()["wire"] and len(state.native.posts) == 1


@pytest.mark.parametrize("damage", ["draft", "accepted", "violations", "pending-receipt"])
def test_malformed_saved_result_never_partially_applies_or_reissues(armed, damage):
    state = armed
    original = deepcopy(state.packet)
    assert state.phrase()["wire"]
    cache = state.cache()
    entry = cache[state.packet["id"]]["fabric_operation"]
    if damage == "draft": entry["result"]["drafts"][0]["updated_at"] = desk._iso(NOW + timedelta(days=1))
    elif damage == "accepted": entry["result"]["accepted"] = ["analysis"]
    elif damage == "violations": entry["result"]["violations"] = 42
    else: entry["state"] = "pending"
    path = desk._cache_path(state.content_root)
    path.write_text(json.dumps(cache))
    before = path.read_bytes()
    assert not state.phrase(original)["wire"]
    assert original == _confirmed_packet() and path.read_bytes() == before
    assert len(state.native.posts) == 1


@pytest.mark.parametrize("damage", ["native", "close-unknown", "close-pending"])
def test_contradictory_uncertainty_is_never_pruned_or_replaced(armed, damage):
    state = armed
    assert state.phrase()["wire"]
    cache = state.cache()
    row = cache[state.packet["id"]]
    receipt = row["fabric_operation"]["receipt"]
    if damage == "native": receipt["native_disposition"] = "pending"
    elif damage == "close-unknown": receipt["close"]["effect_unknown"] = True
    else: receipt["close"]["disposition"] = "pending"
    assert desk._row_unresolved(row)
    assert state.packet["id"] in desk.prune_cache(cache, now=NOW + timedelta(days=365))
    path = desk._cache_path(state.content_root)
    path.write_text(json.dumps(cache))
    before = path.read_bytes()
    changed = _confirmed_packet(headline="Federal Reserve decision updated")
    assert not state.phrase(changed, now=NOW + timedelta(days=365))["wire"]
    assert path.read_bytes() == before and len(state.native.posts) == 1


def test_stale_native_save_preserves_fabric_original(armed):
    state = armed
    assert state.phrase()["wire"]
    entry = state.entry()
    desk.save_cache(state.content_root, {state.packet["id"]: {
        "headline_sha1": "stale-native", "ts": desk._iso(NOW)},
        "other": {"headline_sha1": "other", "ts": desk._iso(NOW)}}, now=NOW)
    assert state.entry() == entry and "other" in state.cache()


def test_full_unknown_cache_does_not_evict_a_claim_to_make_room(armed, monkeypatch):
    state = armed
    monkeypatch.setattr(desk, "_complete_selected", Mock(side_effect=KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        state.phrase()
    original = state.entry()
    cache = {}
    for number in range(desk.CACHE_MAX_ENTRIES):
        sid = "held-story-" + str(number)
        entry = deepcopy(original)
        entry["identity"]["story_id"] = sid
        entry["input"]["seed"]["id"] = sid
        entry["input_sha256"] = hashlib.sha256(desk._canonical(entry["input"])).hexdigest()
        entry["operation_id"] = "app:" + format(number, "032x")
        cache[sid] = {"headline_sha1": entry["identity"]["headline_sha1"],
                      "ts": desk._iso(NOW), "fabric_operation": entry}
    with desk._cache_lock(state.content_root):
        desk._write_cache_strict(state.content_root, cache)
    assert len(desk.prune_cache(cache, now=NOW + timedelta(days=365))) == desk.CACHE_MAX_ENTRIES
    before = desk._cache_path(state.content_root).read_bytes()
    assert not state.phrase(now=NOW + timedelta(days=365))["wire"]
    assert desk._cache_path(state.content_root).read_bytes() == before
    assert state.events == state.native.posts == state.operations == []


def test_analysis_over_platform_limit_stays_needs_edit(armed):
    state = armed
    reply = json.loads(_GOOD_REPLY)
    reply["analysis"] = ("The Federal Reserve held its policy rate steady, " * 6).rstrip(", ") + "."
    assert 280 < len(reply["analysis"]) <= 400
    state.native.response["choices"][0]["message"]["content"] = json.dumps(reply)
    assert state.phrase()["analysis"]
    draft = next(row for row in state.packet["drafts"] if row["shape"] == "analysis")
    assert draft["status"] == "needs_edit" and draft["requires_review"] is True


def test_daemon_public_attachment_reuses_saved_result(armed):
    state = armed
    first = deepcopy(state.packet)
    desk.attach_llm_drafts([first], {"llm": state.block}, root=state.content_root, now=NOW)
    again = deepcopy(state.packet)
    desk.attach_llm_drafts([again], {"llm": state.block}, root=state.content_root,
                           now=NOW + timedelta(minutes=1))
    assert first["drafts"] == again["drafts"]
    assert first["why_it_matters_en"] == again["why_it_matters_en"]
    assert len(state.native.posts) == len(state.costs) == 1
