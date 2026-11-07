"""AI Brief AUTO through its actual cache/publication owner, C, B and SQLite A.

Only configuration/grants, provider output and deterministic price inputs are
synthetic. Original-operation recovery never sends another provider request.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
from unittest.mock import Mock, patch

import pytest
from engine import master_brain as mb, llm_auth as auth, provider_production_modes as owner
from engine import fabric_inference_client as transport
from lib import config
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL, _fixed  # noqa: F401
from tests.test_fabric_workload_auto_composition import auto_workloads  # noqa: F401

STATE = {"macro": {"date": "2026-11-06", "quad": "Q1"}}
_REAL_CALL_MODEL = mb._call_model


def reply(summary="Growth remains steady.", thesis=True):
    value = {"summary": summary, "regime_read": "Liquidity remains mixed.",
             "tldr": ["Stocks remain resilient.", "What to do: Watch — don't chase"],
             "confidence": "medium"}
    if thesis:
        value["theses"] = [{"subject": "VIX", "lean": "fade-fear", "conviction": "low",
            "horizon_d": 20, "thesis": "Fear may ease.", "falsifier_text": "Fear makes a new high."}]
    return json.dumps(value)


@pytest.fixture
def brief_auto(auto_workloads, monkeypatch):
    state = auto_workloads
    state.cfg = {"enabled": True, "max_tokens": 128, "translate_zh": False, "emit_theses": True}
    state.input = copy.deepcopy(STATE)
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "load", lambda: {"llm_models": {"extraction": "legacy-configured"}})
    monkeypatch.setattr(mb, "_cfg", lambda: state.cfg)
    monkeypatch.setitem(mb.LENSES["macro"], "state_fn", lambda root: copy.deepcopy(state.input))
    monkeypatch.setattr(mb, "_call_model", Mock(side_effect=AssertionError("legacy inference")))
    monkeypatch.setattr(mb, "_mb_entry_levels", lambda check, asof, root: {"_VIX": 20.0})
    state.native.response = _fixed.packet(reply())
    state.cache = mb._mb_auto_path(state.root, "macro")
    (state.root / "site").mkdir()
    return state


def saved(state):
    return json.loads(state.cache.read_text())


def synthesize(state):
    return mb.synthesize(state.input, state.cfg, root=state.root)


def run(state, persist=True, force=True):
    return mb.run(root=state.root, persist=persist, force=force)


def bytes_after(state):
    paths = [state.cache, state.root / "data/regime/master_brief.json",
             state.root / "site/master_brief.json", state.root / "data/master_brain/theses.jsonl"]
    return {str(path): path.read_bytes() if path.exists() else None for path in paths}


def counts(state):
    return (len(state.native.posts), len(state.native.rows("application_requests")),
            len(state.costs), len(state.closes))


def test_durable_claim_actual_attribution_and_warm_publication_have_no_new_effects(brief_auto):
    state = brief_auto
    def before():
        entry = saved(state)["entries"][0]
        assert entry["state"] == "pending" and entry["english_brief"] is None
        assert entry["english"]["steps"][0]["state"] == "intent"
        assert entry["inspection"]["requested_model"] is None
    state.native.on_upstream = before
    first = run(state)
    assert first.get("degraded_reason") is None, first
    assert (first["served_by"], first["model"]) == ("go", MODEL)
    entry = saved(state)["entries"][0]
    assert entry["state"] == "ready" and entry["english"]["close"]["closed"]
    assert entry["english"]["steps"][0]["application_observation"]["routing"]["pool"] == "go"
    assert all(effect["state"] == "done" for effect in entry["publication"].values())
    turn = state.native.rows("application_turns")[0]
    assert (turn["principal_id"], turn["workload"]) == ("macro_batch_fabric", "site_batch")
    assert len(first["theses"]) == 1 and entry["operation_id"].split(":")[1] in first["theses"][0]["id"]
    assert state.costs[0]["model"] == MODEL and state.costs[0]["cost_basis"] == "unknown"
    before_bytes, before_counts = bytes_after(state), counts(state)
    assert run(state) == first
    assert bytes_after(state) == before_bytes and counts(state) == before_counts == (1, 1, 1, 1)
    assert all(row["state"] == "released" for row in state.native.rows("leases"))


def test_direct_english_then_run_translates_and_publishes_the_same_original(brief_auto):
    state = brief_auto
    state.cfg.update(translate_zh=True, zh_batch_size=2)
    first = synthesize(state)
    original = saved(state)["entries"][0]
    assert original["state"] == "ready" and original["translations"] is None, first
    english_id = original["operation_id"]
    def translated():
        request = state.native.posts[-1][1] if isinstance(state.native.posts[-1], tuple) else None
        # The provider receives two scalar/list items in each of the two batches.
        state.native.response = _fixed.packet(json.dumps(["增长保持平稳。", "流动性依然复杂。"]))
    state.native.on_upstream = translated
    second = run(state)
    assert second.get("degraded_reason") is None and second.get("zh"), second
    entry = saved(state)["entries"][0]
    assert entry["operation_id"] == english_id and entry["english"] == original["english"]
    assert first["generated_at"] == second["generated_at"] and first["theses"] == second["theses"]
    assert len(entry["translations"]["batches"]) == 2
    identities = [english_id] + [batch["operation"]["operation_id"] for batch in entry["translations"]["batches"]]
    assert len(set(identities)) == 3 and counts(state) == (3, 3, 3, 3)
    before = bytes_after(state)
    assert run(state) == second and bytes_after(state) == before and counts(state) == (3, 3, 3, 3)


def test_intentional_rewrite_is_two_steps_of_one_operation_and_final_text_is_committed(brief_auto):
    state = brief_auto
    plans = [_fixed.packet(reply("The growth_score is steady.")), _fixed.packet(reply("Growth remains steady."))]
    state.native.on_upstream = lambda: setattr(state.native, "response", plans.pop(0))
    result = run(state)
    assert result.get("degraded_reason") is None, result
    entry = saved(state)["entries"][0]
    steps = entry["english"]["steps"]
    assert len(steps) == 2 and result["raw_text"] == steps[1]["text"] == reply()
    assert steps[0]["request_id"].endswith(":brain:0") and steps[1]["request_id"].endswith(":brain:1")
    assert len(state.native.rows("application_turns")) == 1
    assert counts(state) == (2, 2, 2, 1)
    assert sum(row["input_tokens"] for row in state.costs) == entry["english"]["usage"]["input_tokens"]
    assert sum(row["output_tokens"] for row in state.costs) == entry["english"]["usage"]["output_tokens"]
    assert run(state) == result and counts(state) == (2, 2, 2, 1)


def test_pending_original_wins_over_removed_selection_disabled_cfg_force_and_new_state(brief_auto, monkeypatch):
    state = brief_auto
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(run, state)
        try:
            assert state.native.arrived.wait(5)
            monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
            state.cfg["enabled"] = False
            state.input["changed"] = True
            for force in (False, True):
                result = run(state, force=force)
                assert result["degraded_reason"] == "application_fabric_original_held"
            assert counts(state)[0] == 1
        finally:
            state.native.block.set()
        # The first operation uses its original selected route even if the host
        # selector changes during I/O; it cannot start a legacy translation.
        result = pending.result(timeout=20)
    assert counts(state)[0] == 1


def test_unknown_original_close_holds_known_text_without_translation_or_publication(brief_auto, monkeypatch):
    state = brief_auto
    state.cfg["translate_zh"] = True
    original = state.native.gateway.close_application_turn
    def close(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost original close acknowledgement")
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        result = run(state)
    assert result["degraded_reason"] == "application_fabric_original_held"
    assert result["summary"] == "Growth remains steady."
    entry = saved(state)["entries"][0]
    assert entry["state"] == "held" and entry["english"]["close"]["effect_unknown"]
    assert entry["translations"] is None and entry["publication"] is None
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert run(state)["degraded_reason"] == "application_fabric_original_held"
    assert counts(state) == (1, 1, 1, 1)
    assert not (state.root / "data/master_brain/theses.jsonl").exists()


def test_unknown_translation_close_never_repeats_the_batch_or_publishes(brief_auto):
    state = brief_auto
    state.cfg.update(translate_zh=True, zh_batch_size=2)
    first = synthesize(state)
    assert first.get("degraded_reason") is None
    state.native.response = _fixed.packet(json.dumps(["增长平稳。", "市场复杂。"]))
    original = state.native.gateway.close_application_turn
    def close(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost translation close acknowledgement")
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        result = run(state)
    entry = saved(state)["entries"][0]
    assert result["degraded_reason"] == "application_fabric_original_held"
    assert entry["translations"]["batches"][0]["operation"]["state"] == "held"
    assert entry["translations"]["batches"][1]["operation"]["steps"] == []
    assert entry["publication"] is None and counts(state) == (2, 2, 2, 2)
    assert run(state)["degraded_reason"] == "application_fabric_original_held"
    assert counts(state) == (2, 2, 2, 2)


@pytest.mark.parametrize("boundary", ["claim", "step_intent", "step_observation", "close", "english", "translation_plan"])
def test_failed_cache_ack_latches_without_provider_or_projection_replay(brief_auto, monkeypatch, boundary):
    state = brief_auto
    real = mb._brief_cache._cache_save
    hit = []
    def save(path, document):
        entry = document["entries"][0]
        op = entry["english"]
        match = {
            "claim": not op["steps"],
            "step_intent": bool(op["steps"]) and op["steps"][-1]["state"] == "intent",
            "step_observation": bool(op["steps"]) and op["steps"][-1]["state"] == "observed" and op["close"] is None,
            "close": op["close"] is not None and entry["english_brief"] is None,
            "english": entry["english_brief"] is not None and entry["translations"] is None,
            "translation_plan": entry["translations"] is not None,
        }[boundary]
        real(path, document)
        if match and not hit:
            hit.append(True)
            raise OSError("synthetic lost durable save acknowledgement")
    with monkeypatch.context() as scoped:
        scoped.setattr(mb._brief_cache, "_cache_save", save)
        first = run(state)
    assert hit and first["degraded_reason"], first
    before = counts(state)
    second = run(state)
    # A fully saved English receipt may be extended after its ACK was lost;
    # no inference is repeated, and the saved timestamp/thesis identity survive.
    assert counts(state) == before
    if boundary not in ("english",):
        assert second["degraded_reason"]
        assert not (state.root / "data/master_brain/theses.jsonl").exists()


def test_persist_false_still_appends_once_then_requested_files_use_the_same_brief(brief_auto):
    state = brief_auto
    first = run(state, persist=False)
    assert first.get("degraded_reason") is None, first
    before = (state.root / "data/master_brain/theses.jsonl").read_bytes()
    assert not (state.root / "data/regime/master_brief.json").exists()
    second = run(state, persist=True)
    assert second == first and counts(state) == (1, 1, 1, 1)
    assert (state.root / "data/master_brain/theses.jsonl").read_bytes() == before
    assert json.loads((state.root / "data/regime/master_brief.json").read_text()) == first


def test_lost_ledger_receipt_recovers_by_reading_without_appending_again(brief_auto, monkeypatch):
    state = brief_auto
    real = mb._brief_cache._cache_save
    hit = []
    def save(path, document):
        entry = document["entries"][0]
        publication = entry["publication"]
        if publication and publication["ledger"]["state"] == "done" and not hit:
            hit.append(True)
            raise OSError("receipt not written after actual ledger append")
        return real(path, document)
    with monkeypatch.context() as scoped:
        scoped.setattr(mb._brief_cache, "_cache_save", save)
        result = run(state)
    assert hit and result["degraded_reason"]
    ledger = state.root / "data/master_brain/theses.jsonl"
    raw, before = ledger.read_bytes(), counts(state)
    with patch.object(mb, "_mb_auto_effect_write", side_effect=AssertionError("replayed local effect")):
        recovered = run(state)
    assert recovered.get("degraded_reason") is None, recovered
    assert ledger.read_bytes() == raw and counts(state) == before
    assert saved(state)["entries"][0]["state"] == "ready"


@pytest.mark.parametrize("kind", ["malformed", "conflict", "partial"])
def test_unreadable_conflicting_or_partial_original_ledger_never_becomes_empty(brief_auto, monkeypatch, kind):
    state = brief_auto
    if kind == "partial":
        value = json.loads(reply())
        value["theses"].append({**value["theses"][0], "subject": "Long Treasuries", "lean": "overweight"})
        state.native.response = _fixed.packet(json.dumps(value))
    real = mb._mb_auto_effect_write
    def effect(root, key, plan):
        if key != "ledger":
            return real(root, key, plan)
        path = root / plan["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "malformed":
            path.write_bytes(b'{"truncated":')
        elif kind == "conflict":
            path.write_text(json.dumps({**plan["rows"][0], "lean": "avoid"}) + "\n")
        else:
            path.write_text(json.dumps(plan["rows"][0]) + "\n")
        raise OSError("synthetic partial/conflicting original")
    with patch.object(mb, "_mb_auto_effect_write", side_effect=effect):
        assert run(state)["degraded_reason"]
    before, calls = bytes_after(state), counts(state)
    assert run(state)["degraded_reason"]
    assert bytes_after(state) == before and counts(state) == calls


def test_legacy_run_started_before_auto_cannot_overwrite_completed_auto_publication(brief_auto, monkeypatch):
    state = brief_auto
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    started, release = threading.Event(), threading.Event()
    original_call = mb._call_model
    def legacy(*args, **kwargs):
        started.set()
        assert release.wait(10)
        return reply("Old legacy note."), None
    monkeypatch.setattr(mb, "_call_model", legacy)
    with ThreadPoolExecutor(max_workers=1) as workers:
        old = workers.submit(run, state)
        assert started.wait(5)
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        monkeypatch.setattr(mb, "_call_model", original_call)
        accepted = run(state)
        before = bytes_after(state)
        release.set()
        rejected = old.result(timeout=20)
    assert accepted.get("degraded_reason") is None, accepted
    assert rejected["degraded_reason"] == "application_fabric_publication_superseded"
    assert bytes_after(state) == before and counts(state) == (1, 1, 1, 1)


@pytest.mark.parametrize("field", ["request_digest", "routed_digest", "model", "operation", "translation_layout", "publication", "close_refused"])
def test_corrupt_warm_receipt_refuses_before_any_new_binding(brief_auto, field):
    state = brief_auto
    assert run(state).get("degraded_reason") is None
    document = saved(state)
    entry = document["entries"][0]
    if field == "request_digest":
        entry["english"]["steps"][0]["request_digest"] = "a" * 64
    elif field == "routed_digest":
        step = entry["english"]["steps"][0]
        step["routed_request_digest"] = step["application_observation"]["routing"]["routed_request_digest"] = "b" * 64
    elif field == "model":
        entry["english_brief"]["model"] = "invented-model"
        entry["english_digest"] = mb._brief_cache._cache_hash(entry["english_brief"])
    elif field == "operation":
        entry["operation_id"] = entry["english"]["operation_id"] = "master_brain:" + "a" * 32
    elif field == "translation_layout":
        entry["translations"]["layout"] = [["summary", None]]
    elif field == "close_refused":
        entry["english"]["state"] = "failed"
        entry["english"]["close"] = {"disposition": "refused", "closed": False, "effect_unknown": False, "attempted": True}
    else:
        entry["publication"]["data"]["payload"] = "{}"
        entry["publication"]["data"]["digest"] = hashlib.sha256(b"{}").hexdigest()
    state.cache.write_text(json.dumps(document))
    before, calls = bytes_after(state), counts(state)
    assert run(state)["degraded_reason"] == "application_fabric_owner_invalid"
    assert bytes_after(state) == before and counts(state) == calls


def test_same_second_different_originals_have_distinct_thesis_ids(brief_auto, monkeypatch):
    state = brief_auto
    actual = mb.datetime
    class Clock:
        @staticmethod
        def now(tz):
            return actual(2026, 11, 6, 12, 0, 0, tzinfo=tz)
    monkeypatch.setattr(mb, "datetime", Clock)
    first = run(state)
    state.input["context_change"] = "second-original"
    second = run(state)
    assert first.get("degraded_reason") is None and second.get("degraded_reason") is None, (first, second)
    assert first["generated_at"] == second["generated_at"]
    assert first["theses"][0]["id"] != second["theses"][0]["id"]
    rows = (state.root / "data/master_brain/theses.jsonl").read_text().splitlines()
    assert len(rows) == 2 and counts(state) == (2, 2, 2, 2)


def test_explicit_native_step_limit_is_not_repaired_by_a_new_english_operation(brief_auto):
    state = brief_auto
    state.native.document["application_grants"] = [
        {**row, "max_steps": 1} if row["principal_id"] == "macro_batch_fabric" else row
        for row in state.native.document["application_grants"]]
    state.native.save()
    state.native.response = _fixed.packet(reply("The growth_score is steady."))
    result = run(state)
    assert result.get("degraded_reason"), result
    assert len(state.native.posts) == 1
    before = counts(state)
    again = run(state)
    assert again.get("degraded_reason") and counts(state) == before


@pytest.mark.parametrize("phase", ["english", "translation"])
def test_correlated_close_refusal_keeps_admitted_original_held(brief_auto, monkeypatch, phase):
    state = brief_auto
    state.cfg.update(translate_zh=True, zh_batch_size=2)
    if phase == "translation":
        assert synthesize(state).get("degraded_reason") is None
        state.native.response = _fixed.packet(json.dumps(["增长平稳。", "市场复杂。"]))
    # The actual B handler sends its correlated HTTP409 envelope and the actual
    # client decodes "refused". The lease deliberately remains admitted.
    with patch.object(state.native.gateway, "close_application_turn",
                      return_value={"disposition": "refused"}):
        result = run(state)
    entry = saved(state)["entries"][0]
    op = entry["english"] if phase == "english" else entry["translations"]["batches"][0]["operation"]
    assert op["close"] == {"disposition": "refused", "closed": False, "effect_unknown": False, "attempted": True}
    assert op["state"] == entry["state"] == "held"
    assert result["degraded_reason"] == "application_fabric_original_held"
    assert entry["publication"] is None
    assert any(row["state"] != "released" for row in state.native.rows("leases"))
    before = counts(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert run(state)["degraded_reason"] == "application_fabric_original_held"
    assert counts(state) == before


def test_auto_activated_during_gather_cannot_start_anonymous_translation(brief_auto, monkeypatch):
    state = brief_auto
    state.cfg.update(translate_zh=True, zh_batch_size=2)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.setattr(owner, "__file__", str(state.root / "engine/provider_production_modes.py"))
    monkeypatch.setattr(mb, "_call_model", _REAL_CALL_MODEL)
    def gather(root):
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return copy.deepcopy(state.input)
    monkeypatch.setitem(mb.LENSES["macro"], "state_fn", gather)
    result = run(state)
    assert result["degraded_reason"] == "application_fabric_publication_superseded"
    entry = saved(state)["entries"][0]
    assert entry["english"]["state"] == "complete" and entry["translations"] is None
    assert entry["publication"] is None and counts(state) == (1, 1, 1, 1)
    state.native.response = _fixed.packet(json.dumps(["增长平稳。", "市场复杂。"]))
    final = run(state)
    assert final.get("degraded_reason") is None and final["zh"], final
    assert saved(state)["entries"][0]["operation_id"] == entry["operation_id"]
    assert counts(state) == (3, 3, 3, 3)


@pytest.mark.parametrize("activation", ["after_english", "during_translation"])
def test_late_auto_selection_refuses_contextless_legacy_continuation(brief_auto, monkeypatch, activation):
    state = brief_auto
    state.cfg.update(translate_zh=True, zh_batch_size=2)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    # Make the private legacy helper's default root the same qualified owner;
    # an unavailable/mis-rooted factory would not test the anonymous AUTO gate.
    monkeypatch.setattr(owner, "__file__", str(state.root / "engine/provider_production_modes.py"))
    def legacy(system, user, cfg, served=None):
        if str(cfg.get("usage_stage") or "").endswith("-zh"):
            return _REAL_CALL_MODEL(system, user, cfg, served)
        if activation == "after_english":
            monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return reply(), None
    monkeypatch.setattr(mb, "_call_model", legacy)
    if activation == "during_translation":
        translate = mb._translate_brief
        def late_translate(brief, cfg, lens):
            monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
            return translate(brief, cfg, lens)
        monkeypatch.setattr(mb, "_translate_brief", late_translate)
    result = run(state)
    assert result["degraded_reason"] == "application_fabric_publication_superseded"
    assert counts(state) == (0, 0, 0, 0)
    assert not (state.root / "data/regime/master_brief.json").exists()
    assert not (state.root / "data/master_brain/theses.jsonl").exists()


def test_contextless_model_helper_refuses_qualified_auto_before_binding(brief_auto, monkeypatch):
    state = brief_auto
    monkeypatch.setattr(owner, "__file__", str(state.root / "engine/provider_production_modes.py"))
    result = _REAL_CALL_MODEL("Summarize.", "Synthetic context.", state.cfg)
    assert result == (None, "application_fabric_durable_owner_required")
    assert counts(state) == (0, 0, 0, 0)
