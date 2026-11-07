"""Delegated desk AUTO runs through the real factory, HTTP B and SQLite A.

Only provider output, qualification/grants, input prices/passports and the
independent QLedger registrar are synthetic. No production call or trade occurs.
"""
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from engine import ai_desk as ai, thematic_desk as thematic
from engine import policy_intent_desk as policy, regime_snap_veto as regime
from engine import desk_ledger as owner, catalyst_tone as cache, llm_auth as auth
from lib import config
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL, _fixed  # noqa: F401
from tests.test_fabric_workload_auto_composition import auto_workloads  # noqa: F401

KEYS = ("ai-desk", "policy-intent", "thematic-us", "thematic-china",
        "thematic-hk", "thematic-canada", "regime-snap")


def reply(key):
    if key == "regime-snap":
        return {"lean": "unclear", "confidence": "low", "checks": {}, "read": "Public context is mixed."}
    return {"regime_context": "Public context is conditional.", "confidence": "low",
            "emerging_watch": None, "theses": [{"subject": "XLK" if key == "policy-intent" else "Technology",
                "lean": "overweight", "conviction": "low", "actor": "admin",
                "horizon_d": 20, "thesis": "A conditional public observation.",
                "evidence": ["Published detector state"], "dissent": "Breadth could weaken.",
                "falsifier_text": "The benchmark outperforms."}]}


@pytest.fixture
def desks(auto_workloads, monkeypatch):
    state = auto_workloads
    state.cfg = {"enabled": True, "max_tokens": 128, "interval_days": 1,
                 "panel": {"enabled": False}, "model": "configured-placeholder", "headlines_n": 12}
    state.input = {"as_of": "2026-11-06", "region": "us",
                  "flow": {"sectors": [{"name": "Technology"}]},
                  "narrative_rotation": {"ranks": [{"name": "Technology", "id": "tech", "etf_proxy": "XLK"}]},
                  "track_record": None}
    from engine import provider_production_modes as modes
    cap = modes._APPLICATION_FABRIC_TRANSPORTS["native_fabric_macro_batch_auto_v1"].capability_id
    for grant in state.manifest["capabilities"]:
        if grant["capability_id"] == cap:
            grant["allowed_lanes"].extend(["ai-desk", "thematic-desk", "policy-desk", "regime-snap"])
    state.save()
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "data_dir", lambda: state.root / "data")
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(ai, "_desk_passport", lambda name: {"state": "accruing", "n": 0})
    monkeypatch.setattr(ai, "_regime_label", lambda root: "synthetic")
    monkeypatch.setattr(ai, "_level_asof", lambda *args: 100.0)
    monkeypatch.setattr(thematic, "_close_asof", lambda *args: 100.0)
    monkeypatch.setattr(policy, "quad_label", lambda root: "synthetic")
    for module in (ai, thematic, policy, regime):
        monkeypatch.setattr(module, "_cfg", lambda: copy.deepcopy(state.cfg))
    monkeypatch.setattr(ai, "gather_desk_state", lambda root: copy.deepcopy(state.input))
    monkeypatch.setattr(policy, "gather_state", lambda root: copy.deepcopy(state.input))
    monkeypatch.setattr(thematic, "gather_thematic_state",
                        lambda region, root: {**copy.deepcopy(state.input), "region": region})
    monkeypatch.setattr(ai._mb, "_call_model", Mock(side_effect=AssertionError("legacy provider")))
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    state.registrations = []
    def register(rows, root):
        state.registrations.append(copy.deepcopy(rows))
        return {"n_candidates": len(rows), "n_accepted": len(rows), "error": None}
    monkeypatch.setattr(thematic, "_register_qledger_claims", register)
    (state.root / "site").mkdir()
    return state


def invoke(state, key, **kwargs):
    if key == "ai-desk":
        return ai.run(root=state.root, **kwargs)
    if key == "policy-intent":
        return policy.run(root=state.root, **kwargs)
    if key.startswith("thematic-"):
        return thematic.run(key[9:], root=state.root, **kwargs)
    return regime.assess({"status": "firing", "score": 3}, headlines=[], **kwargs)


def document(state, key):
    return json.loads(owner._fabric_path(key, state.root).read_text())


def entries(state, key):
    return document(state, key)["entries"]


def counts(state):
    return len(state.native.posts), len(state.native.rows("application_requests")), len(state.costs), len(state.closes)


def held(result, key):
    return result is None if key == "regime-snap" else str(result.get("degraded_reason") or "").startswith("application_fabric_")


def snapshot(state):
    return {str(path.relative_to(state.root)): path.read_bytes()
            for parent in ("data/ai_desk", "data/policy_intent", "data/thematic_desk",
                           "data/regime_snap", "data/regime", "site")
            for path in (state.root / parent).rglob("*")
            if path.is_file() and not path.name.endswith(".lock")}


@pytest.mark.parametrize("key", KEYS)
def test_public_consumers_use_native_batch_and_warm_original_once(desks, key):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    def upstream():
        row = entries(state, key)[0]
        assert row["state"] == "pending" and row["publication_requested"]
        assert any(step["cache"]["entries"] for step in row["steps"].values())
    state.native.on_upstream = upstream
    first = invoke(state, key)
    assert first is not None and not first["degraded_reason"], first
    assert (first["model"], first["served_by"]) == (MODEL, "go")
    if key != "regime-snap":
        assert len(first["theses"]) == 1
    row = entries(state, key)[0]
    assert row["state"] == "complete" and row["publication"]["state"] == "complete"
    turn = state.native.rows("application_turns")[0]
    assert (turn["principal_id"], turn["workload"]) == ("macro_batch_fabric", "site_batch")
    before = snapshot(state)
    assert invoke(state, key) == first
    assert snapshot(state) == before and counts(state) == (1, 1, 1, 1)
    assert len(state.registrations) == (1 if key == "thematic-us" else 0)


@pytest.mark.parametrize("key", ("ai-desk", "policy-intent", "thematic-us"))
def test_direct_synthesis_nonpersist_then_publication_keeps_original(desks, key):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    module = {"ai-desk": ai, "policy-intent": policy, "thematic-us": thematic}[key]
    first = module.synthesize(copy.deepcopy(state.input), copy.deepcopy(state.cfg), root=state.root)
    assert first and not first["degraded_reason"]
    assert invoke(state, key, persist=False) == first
    assert snapshot(state) == {}
    assert invoke(state, key, persist=True) == first
    assert counts(state) == (1, 1, 1, 1)
    assert len(entries(state, key)) == 1


@pytest.mark.parametrize("key", ("ai-desk", "policy-intent", "thematic-us", "regime-snap"))
@pytest.mark.parametrize("valid", (True, False))
def test_refused_close_holds_before_changed_selection_and_gates(desks, monkeypatch, key, valid):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply(key)) if valid else "not JSON")
    with patch.object(state.native.gateway, "close_application_turn", return_value={"disposition": "refused"}):
        assert held(invoke(state, key), key)
    row = entries(state, key)[0]
    assert row["state"] == "held"
    before = snapshot(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["enabled"] = False
    state.input["as_of"] = "2026-11-07"
    assert held(invoke(state, key), key)
    assert counts(state) == (1, 1, 1, 1) and snapshot(state) == before


@pytest.mark.parametrize("key", ("ai-desk", "thematic-us"))
def test_panel_keeps_stable_roles_and_final_author(desks, key):
    state = desks
    state.cfg["panel"]["enabled"] = True
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    result = invoke(state, key)
    assert result and not result["degraded_reason"], result
    row = entries(state, key)[0]
    assert row["steps"]["single"]["cache"]["entries"] == []
    assert len(row["steps"]["adjudicator"]["cache"]["entries"]) == 1
    assert len(row["result"]["panel"]) == 4
    assert counts(state) == (5, 5, 5, 5)
    assert invoke(state, key) == result and counts(state) == (5, 5, 5, 5)


def test_concurrent_call_observes_pending_without_new_dispatch(desks):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply("ai-desk")))
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(invoke, state, "ai-desk")
        try:
            assert state.native.arrived.wait(3)
            assert held(invoke(state, "ai-desk", force=True), "ai-desk")
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert not future.result(timeout=20)["degraded_reason"]
    assert counts(state) == (1, 1, 1, 1)


def test_shared_thematic_ledger_preserves_both_regions_and_us_only_handoff(desks):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply("thematic-us")))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda key: invoke(state, key), ("thematic-us", "thematic-china")))
    assert all(r and not r["degraded_reason"] for r in results), results
    ledger = [json.loads(line) for line in (state.root / "data/thematic_desk/theses.jsonl").read_text().splitlines()]
    assert {row["market"] for row in ledger} == {"us", "china"}
    assert len(ledger) == 2 and len({row["id"] for row in ledger}) == 2
    assert len(state.registrations) == 1 and state.registrations[0][0]["market"] == "us"


def test_policy_off_lane_is_known_no_write_and_not_historical_debt(desks, monkeypatch):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply("policy-intent")))
    monkeypatch.setenv("COLLECT_LANE", "express")
    with patch.object(policy, "quad_label", side_effect=AssertionError("off-lane regime read")):
        first = invoke(state, "policy-intent")
    assert first and not first["degraded_reason"]
    effect = entries(state, "policy-intent")[0]["publication"]["effects"][0]
    assert effect["receipt"] == {"disposition": "gated_out", "written": []}
    assert not (state.root / "data/policy_intent/theses.jsonl").exists()
    assert (state.root / "site/policy_intent.json").is_file()
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    assert invoke(state, "policy-intent") == first
    assert not (state.root / "data/policy_intent/theses.jsonl").exists()
    assert counts(state) == (1, 1, 1, 1)


def test_policy_nonpersist_can_publish_original_in_actual_nightly_lane(desks, monkeypatch):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply("policy-intent")))
    monkeypatch.setenv("COLLECT_LANE", "express")
    first = invoke(state, "policy-intent", persist=False)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    assert invoke(state, "policy-intent") == first
    assert (state.root / "data/policy_intent/theses.jsonl").exists()
    assert counts(state) == (1, 1, 1, 1)


def test_regime_day_rollover_and_legacy_first_verdict_remain_original(desks, monkeypatch):
    state = desks
    state.native.response = _fixed.packet(json.dumps(reply("regime-snap")))
    day = [6]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, day[0], 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(regime, "datetime", Clock)
    path = state.root / "data/regime_snap/veto_log.jsonl"
    path.parent.mkdir(parents=True)
    prior = {"generated_at": "2026-11-06T01:00:00+00:00", "lean": "durable"}
    path.write_text(json.dumps(prior) + "\n" + json.dumps(prior) + "\n")
    first = invoke(state, "regime-snap")
    assert first and first["lean"] == "unclear"
    assert path.read_text().count("\n") == 2
    receipt = entries(state, "regime-snap")[0]["publication"]["effects"][0]["receipt"]
    assert receipt == {"disposition": "existing_first", "written": []}
    day[0] = 7
    second = invoke(state, "regime-snap")
    assert second and second["generated_at"].startswith("2026-11-07")
    assert len(entries(state, "regime-snap")) == 2 and counts(state) == (2, 2, 2, 2)
    assert json.loads(path.read_text().splitlines()[-1])["date"] == "2026-11-07"


@pytest.mark.parametrize("field", ("response", "author", "clock", "no_steps", "projection", "ledger", "receipt"))
def test_corrupt_completed_owner_refuses_before_new_model_or_publication(desks, field):
    state = desks
    key = "ai-desk"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    assert not invoke(state, key)["degraded_reason"]
    data = document(state, key)
    row = data["entries"][0]
    if field == "response":
        row["result"]["theses"][0]["lean"] = "avoid"
        row["result_digest"] = cache._cache_hash(row["result"])
    elif field == "author":
        row["result"]["model"] = "unobserved"
        row["result_digest"] = cache._cache_hash(row["result"])
    elif field == "clock":
        row["result"]["generated_at"] = "2099-01-01T00:00:00+00:00"
        row["result_digest"] = cache._cache_hash(row["result"])
    elif field == "no_steps":
        for step in row["steps"].values():
            step["cache"]["entries"] = []
    elif field == "projection":
        row["publication"]["effects"][1]["effect"]["value"]["confidence"] = "high"
        row["publication"]["digest"] = cache._cache_hash([s["effect"] for s in row["publication"]["effects"]])
    elif field == "ledger":
        row["publication"]["effects"][0]["effect"]["rows"][0]["lean"] = "avoid"
        row["publication"]["digest"] = cache._cache_hash([s["effect"] for s in row["publication"]["effects"]])
    else:
        row["publication"]["effects"][0]["receipt"]["written"] = []
    owner._fabric_path(key, state.root).write_text(json.dumps(data))
    before = snapshot(state)
    assert held(invoke(state, key, force=True), key)
    assert counts(state) == (1, 1, 1, 1) and snapshot(state) == before


@pytest.mark.parametrize("phase", ("claim", "result", "ledger_ack", "handoff_ack", "site_ack"))
def test_lost_local_ack_keeps_original_and_never_replays(desks, monkeypatch, phase):
    state, key = desks, "thematic-us"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    original, tripped = cache._cache_save, []
    def save(path, value):
        data = value if isinstance(value, dict) and value.get("schema") == "macro.delegated_brain_fabric.v1" else None
        row = data["entries"][0] if data and data["entries"] else None
        plan = row["publication"] if row else None
        match = (row and ((phase == "claim" and row["state"] == "pending"
                          and all(not s["cache"]["entries"] for s in row["steps"].values()))
            or (phase == "result" and row["state"] == "ready" and plan is None)
            or (phase == "ledger_ack" and plan and plan["effects"][0]["state"] == "complete"
                and plan["effects"][1]["state"] == "ready")
            or (phase == "handoff_ack" and plan and plan["effects"][1]["state"] == "complete"
                and plan["effects"][2]["state"] == "ready")
            or (phase == "site_ack" and plan and plan["state"] == "complete")))
        if match and not tripped:
            tripped.append(True)
            if phase == "claim":
                original(path, value)
            raise OSError("synthetic lost local acknowledgement")
        return original(path, value)
    with patch.object(cache, "_cache_save", side_effect=save):
        assert held(invoke(state, key), key)
    assert tripped
    before, effects, registered = snapshot(state), counts(state), len(state.registrations)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["enabled"] = False
    assert held(invoke(state, key), key)
    assert snapshot(state) == before and counts(state) == effects
    assert len(state.registrations) == registered
    if phase == "ledger_ack":
        assert not state.registrations


def test_explicit_foreign_workload_refuses_before_claim_and_credentials(desks, monkeypatch):
    state = desks
    from engine import provider_production_modes as modes
    credential = Mock(side_effect=AssertionError("credentials"))
    monkeypatch.setattr(modes, "_resolve_credential", credential)
    state.cfg["workload_profile"] = "portfolio_analysis"
    assert held(invoke(state, "ai-desk"), "ai-desk")
    assert not credential.called and counts(state) == (0, 0, 0, 0)
    assert not owner._fabric_path("ai-desk", state.root).exists()


def test_actual_enable_gate_is_not_bypassed_by_internal_callback(desks):
    state = desks
    state.cfg["enabled"] = False
    legacy = Mock(side_effect=AssertionError("injected bypass"))
    assert invoke(state, "thematic-us", call=legacy) is None
    assert not legacy.called and counts(state) == (0, 0, 0, 0)


def test_cancelled_call_preserves_original_and_propagates_same_exception(desks):
    state = desks
    stop = KeyboardInterrupt("synthetic cancellation")
    with patch.object(auth, "make_call", side_effect=stop):
        with pytest.raises(KeyboardInterrupt) as caught:
            invoke(state, "ai-desk")
    assert caught.value is stop
    before = counts(state)
    assert held(invoke(state, "ai-desk", force=True), "ai-desk")
    assert counts(state) == before


@pytest.mark.parametrize("key", ("ai-desk", "thematic-us"))
def test_unknown_panel_role_blocks_every_final_author_and_settles_siblings(desks, key):
    state = desks
    state.cfg["panel"]["enabled"] = True
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    original = state.native.gateway.close_application_turn
    closes, mutex = [], threading.Lock()
    def close(*args, **kwargs):
        with mutex:
            first = not closes
            closes.append(True)
        return {"disposition": "refused"} if first else original(*args, **kwargs)
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        assert held(invoke(state, key), key)
    row = entries(state, key)[0]
    assert row["state"] == "held" and row["publication"] is None
    assert not row["steps"]["single"]["cache"]["entries"]
    assert not row["steps"]["adjudicator"]["cache"]["entries"]
    started = [r for step in row["steps"].values() for r in step["cache"]["entries"]]
    assert started and all(r["state"] in ("held", "terminal") for r in started)
    assert sum(r["state"] == "held" for r in started) >= 1
    assert 1 <= len(state.native.posts) <= 4 and snapshot(state) == {}


@pytest.mark.parametrize("key", ("ai-desk", "thematic-us"))
def test_executor_fallback_reuses_already_completed_role(desks, key):
    state = desks
    state.cfg["panel"]["enabled"] = True
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    class InterruptedExecutor:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def map(self, fn, keys):
            yield fn(keys[0])
            raise RuntimeError("synthetic executor delivery interruption")
    with patch("concurrent.futures.ThreadPoolExecutor", InterruptedExecutor):
        result = invoke(state, key)
    assert result and not result["degraded_reason"], result
    assert len(result["panel"]) == 4 and counts(state) == (5, 5, 5, 5)


@pytest.mark.parametrize("phase", ("gather", "legacy_answer"))
def test_late_auto_selection_cannot_publish_legacy_desk_result(desks, monkeypatch, phase):
    state, key = desks, "ai-desk"
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    calls = []
    def legacy(system, user, cfg, **kwargs):
        calls.append(True)
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return json.dumps(reply(key)), None
    if phase == "gather":
        def gather(root):
            monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
            return copy.deepcopy(state.input)
        monkeypatch.setattr(ai, "gather_desk_state", gather)
    assert held(invoke(state, key, call=legacy), key)
    assert len(calls) == (0 if phase == "gather" else 1)
    assert counts(state) == (0, 0, 0, 0) and snapshot(state) == {}


@pytest.mark.parametrize("present", (False, True))
def test_ledger_replacement_between_read_and_open_refuses_before_append(desks, present):
    state, key = desks, "thematic-us"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    path = state.root / "data/thematic_desk/theses.jsonl"
    path.parent.mkdir(parents=True)
    if present:
        path.write_text('{"id":"prior","lean":"avoid"}\n')
    original, changed = owner._fabric_rows, []
    replacement = b'{"id":"concurrent-other-writer","lean":"avoid"}\n'
    def read(target, field):
        result = original(target, field)
        if target == path and not changed:
            changed.append(True)
            temp = path.with_suffix(".replacement")
            temp.write_bytes(replacement)
            temp.replace(path)
        return result
    with patch.object(owner, "_fabric_rows", side_effect=read):
        assert held(invoke(state, key), key)
    assert changed and path.read_bytes() == replacement
    assert not state.registrations
    before = counts(state)
    assert held(invoke(state, key), key) and counts(state) == before


def test_nightly_authority_is_rechecked_at_actual_write(desks, monkeypatch):
    state, key = desks, "policy-intent"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    original = policy._fabric_prepare
    def prepare(*args):
        effects = original(*args)
        assert effects[0]["eligible"] and effects[0]["rows"]
        monkeypatch.setenv("COLLECT_LANE", "express")
        return effects
    with patch.object(policy, "_fabric_prepare", side_effect=prepare):
        result = invoke(state, key)
    assert result and not result["degraded_reason"]
    step = entries(state, key)[0]["publication"]["effects"][0]
    assert step["receipt"] == {"disposition": "gated_out", "written": []}
    assert not (state.root / "data/policy_intent/theses.jsonl").exists()


def test_ready_result_publication_obligation_blocks_new_generation(desks, monkeypatch):
    state, key = desks, "ai-desk"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    original, arrived = owner.fabric_publish, []
    def publish(*args, **kwargs):
        row = entries(state, key)[0]
        assert row["state"] == "ready" and row["publication_requested"]
        state.input["as_of"] = "2026-11-07"
        arrived.append(invoke(state, key, force=True))
        return original(*args, **kwargs)
    with patch.object(owner, "fabric_publish", side_effect=publish):
        result = invoke(state, key)
    assert result and not result["degraded_reason"]
    assert held(arrived[0], key) and counts(state) == (1, 1, 1, 1)


def test_foreign_price_owner_and_external_journal_refuse_before_binding(desks, monkeypatch, tmp_path):
    state = desks
    other = tmp_path.parent / (tmp_path.name + "-external")
    other.mkdir()
    state.native.response = _fixed.packet(json.dumps(reply("regime-snap")))
    monkeypatch.setattr(config, "ROOT", other)
    assert held(invoke(state, "ai-desk"), "ai-desk")
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "data_dir", lambda: other)
    assert invoke(state, "regime-snap") is None
    assert counts(state) == (0, 0, 0, 0)


def test_partial_observed_usage_stays_nullable(desks):
    state, key = desks, "ai-desk"
    state.native.response = _fixed.packet(json.dumps(reply(key)))
    state.native.response["usage"] = {"prompt_tokens": 11}
    result = invoke(state, key)
    assert result and not result["degraded_reason"]
    receipt = entries(state, key)[0]["steps"]["single"]["cache"]["entries"][0]["receipt"]
    assert receipt["usage"]["usage_state"] == "unknown" and receipt["usage"]["output_tokens"] is None
    assert receipt["observed_usage"]["input_tokens"] == 11 and state.costs == []


def test_configured_regime_journal_inside_owner_is_preserved(desks, monkeypatch):
    state = desks
    custom = state.root / "custom-data"
    monkeypatch.setattr(config, "data_dir", lambda: custom)
    state.native.response = _fixed.packet(json.dumps(reply("regime-snap")))
    result = invoke(state, "regime-snap")
    assert result and not result["degraded_reason"]
    assert (custom / "regime_snap/veto_log.jsonl").is_file()
    assert not (state.root / "data/regime_snap/veto_log.jsonl").exists()
    assert counts(state) == (1, 1, 1, 1)
