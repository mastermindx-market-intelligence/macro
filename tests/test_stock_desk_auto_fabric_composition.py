"""Stock Desk AUTO custody in its existing notes owner, through real C/B/A.

Only provider output, purpose/grants, input prices and the independent qledger
registrar are synthetic. No production registration or financial action occurs.
"""
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest
from engine import stock_desk as sd, catalyst_tone as cache, llm_auth as auth
from lib import config
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_service_auto_composition import auto_native, auto_services, MODEL, _fixed  # noqa: F401
from tests.test_fabric_workload_auto_composition import auto_workloads  # noqa: F401


def note():
    return {"ticker": "AAA", "lean": "constructive", "conviction": "medium",
        "horizon_d": 20, "thesis": "Public evidence is conditional.",
        "evidence": ["Published source"], "dissent": "Growth could weaken.",
        "falsifier_text": "Relative growth slows."}


@pytest.fixture
def stock_auto(auto_workloads, monkeypatch):
    state = auto_workloads
    state.cfg = {"enabled": True, "max_tokens": 128, "interval_days": 1}
    state.input = {"as_of": "2026-11-06", "picks": [{"ticker": "AAA",
        "identity": {"name": "Alpha", "sector": "Industrials"},
        "conviction": {"verdict": "Leader", "cycle_blocked": False}}], "track_record": None}
    # Find the native batch capability by its actual descriptor, not a guessed id.
    from engine import provider_production_modes as owner
    cap = owner._APPLICATION_FABRIC_TRANSPORTS["native_fabric_macro_batch_auto_v1"].capability_id
    for grant in state.manifest["capabilities"]:
        if grant["capability_id"] == cap and "stock-desk" not in grant["allowed_lanes"]:
            grant["allowed_lanes"].append("stock-desk")
    state.save()
    monkeypatch.setattr(config, "ROOT", state.root)
    monkeypatch.setattr(config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(sd, "_cfg", lambda: state.cfg)
    monkeypatch.setattr(sd, "gather_top_picks", lambda root, cfg: copy.deepcopy(state.input))
    monkeypatch.setattr(sd, "score_ledger", lambda **kwargs: None)
    monkeypatch.setattr(sd, "_close_asof", lambda ticker, asof: 100.0)
    monkeypatch.setattr(sd.master_brain, "_call_model", Mock(side_effect=AssertionError("legacy")))
    state.registrations = []
    def register(rows, picks, root):
        state.registrations.append(copy.deepcopy(rows))
        return {"n_rows": len(rows), "n_accepted": len(rows), "error": None}
    monkeypatch.setattr(sd, "_register_qledger_claims", register)
    state.native.response = _fixed.packet(json.dumps({"notes": [note()]}))
    state.cache = state.root / "data/stock_desk/notes.json"
    return state


def run(state, **kwargs):
    return sd.run(root=state.root, **kwargs)


def saved(state):
    return json.loads(state.cache.read_text())


def own(state):
    return saved(state)[sd._STOCK_FABRIC_KEY]


def counts(state):
    return (len(state.native.posts), len(state.native.rows("application_requests")),
            len(state.costs), len(state.closes), len(state.registrations))


def bytes_after(state):
    return {str(path.relative_to(state.root)): path.read_bytes()
            for dirname in ("data/stock_desk", "site/stockdata")
            for path in (state.root / dirname).glob("*")
            if path.is_file() and not path.name.endswith(".lock")}


def test_public_run_claims_before_provider_and_warm_publication_is_exact(stock_auto):
    state = stock_auto
    def upstream():
        owner = own(state)
        row = owner["cache"]["entries"][0]
        assert row["state"] == "pending" and row["receipt"] is None
        assert set(owner["requests"]) == {row["operation_id"]}
        assert owner["publications"] == {}
    state.native.on_upstream = upstream
    first = run(state)
    assert first["degraded"] is None and first["notes"], first
    assert first["model"] == MODEL and first["served_by"] == "go"
    row = own(state)["cache"]["entries"][0]
    assert row["receipt"]["application_observation"]["routing"]["pool"] == "go"
    assert row["receipt"]["close"]["closed"]
    plan = own(state)["publications"][row["operation_id"]]
    assert plan["state"] == "complete"
    assert plan["steps"][1]["receipt"]["materialization_proven"] is False
    assert state.registrations[0] == plan["ledger_rows"]
    native_turn = state.native.rows("application_turns")[0]
    assert native_turn["principal_id"] == "macro_batch_fabric"
    assert native_turn["workload"] == "site_batch"
    before = bytes_after(state)
    assert run(state, force=True) == first
    assert bytes_after(state) == before and counts(state) == (1, 1, 1, 1, 1)


def test_direct_synthesis_then_nonpersist_then_persist_reuses_original(stock_auto):
    state = stock_auto
    syn = sd.synthesize(copy.deepcopy(state.input), state.cfg, root=state.root)
    assert syn["degraded"] is None
    first = run(state, persist=False)
    assert first["notes"] and not (state.root / "data/stock_desk/theses.jsonl").exists()
    assert counts(state) == (1, 1, 1, 1, 0)
    second = run(state, persist=True)
    assert second == first and counts(state) == (1, 1, 1, 1, 1)
    assert len(own(state)["cache"]["entries"]) == 1


@pytest.mark.parametrize("reply_kind", ["valid", "invalid_json"])
def test_correlated_close_refusal_keeps_original_even_for_failed_parse(stock_auto, monkeypatch, reply_kind):
    state = stock_auto
    if reply_kind == "invalid_json":
        state.native.response = _fixed.packet("not JSON")
    with patch.object(state.native.gateway, "close_application_turn",
                      return_value={"disposition": "refused"}):
        first = run(state)
    row = own(state)["cache"]["entries"][0]
    assert row["state"] == "held"
    assert row["receipt"]["close"]["disposition"] == "refused"
    assert first["degraded"] and own(state)["publications"] == {}
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["enabled"] = False
    state.input["as_of"] = "2026-11-07"
    assert run(state, force=True)["degraded"]
    assert counts(state) == (1, 1, 1, 1, 0)


def test_unknown_close_holds_before_selector_force_and_disabled_gate(stock_auto, monkeypatch):
    state = stock_auto
    original = state.native.gateway.close_application_turn
    def close(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("lost original close ACK")
    with patch.object(state.native.gateway, "close_application_turn", side_effect=close):
        assert run(state)["degraded"]
    before = bytes_after(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["enabled"] = False
    state.input["picks"][0]["ticker"] = "BBB"
    assert run(state)["degraded"] == "application_fabric_original_held"
    assert run(state, force=True)["degraded"] == "application_fabric_original_held"
    assert bytes_after(state) == before and counts(state) == (1, 1, 1, 1, 0)


def test_pending_concurrent_run_never_claims_a_second_original(stock_auto):
    state = stock_auto
    state.native.block = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(run, state)
        try:
            assert state.native.arrived.wait(3)
            assert run(state, force=True)["degraded"]
            assert len(state.native.posts) == 1
        finally:
            state.native.block.set()
        assert future.result(timeout=15)["degraded"] is None
    assert counts(state) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("phase", ["claim", "result", "ledger_ack", "qledger_ack", "site_ack"])
def test_lost_local_ack_preserves_original_without_replay(stock_auto, monkeypatch, phase):
    state = stock_auto
    original = cache._cache_save
    tripped = []
    def save(path, value):
        owner = value.get(sd._STOCK_FABRIC_KEY) if isinstance(value, dict) else None
        rows = owner["cache"]["entries"] if owner else []
        plans = list(owner["publications"].values()) if owner else []
        row = rows[0] if rows else None
        plan = plans[0] if plans else None
        match = ((phase == "claim" and row and row["state"] == "pending")
            or (phase == "result" and row and row["state"] == "terminal" and not plan)
            or (phase == "ledger_ack" and plan and plan["steps"][0]["state"] == "complete"
                and plan["steps"][1]["state"] == "ready")
            or (phase == "qledger_ack" and plan and plan["steps"][1]["state"] == "complete"
                and plan["steps"][2]["state"] == "ready")
            or (phase == "site_ack" and plan and plan["state"] == "complete"))
        if match and not tripped:
            tripped.append(True)
            if phase == "claim":
                original(path, value)
            raise OSError("synthetic lost local acknowledgement")
        return original(path, value)
    with patch.object(cache, "_cache_save", side_effect=save):
        first = run(state)
    assert tripped and first["degraded"]
    before, effects = bytes_after(state), counts(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    state.cfg["enabled"] = False
    assert run(state, force=True)["degraded"]
    assert bytes_after(state) == before and counts(state) == effects
    if phase == "ledger_ack":
        assert state.registrations == []


@pytest.mark.parametrize("field", ["request", "route", "output", "ledger", "publication", "closed"])
def test_corrupt_owner_refuses_before_new_binding(stock_auto, field):
    state = stock_auto
    assert run(state)["degraded"] is None
    document = saved(state)
    owner = document[sd._STOCK_FABRIC_KEY]
    row = owner["cache"]["entries"][0]
    plan = owner["publications"][row["operation_id"]]
    if field == "request":
        owner["requests"][row["operation_id"]]["user"] += " corrupt"
    elif field == "route":
        row["receipt"]["routed_request_digest"] = "a" * 64
        row["receipt"]["application_observation"]["routing"]["routed_request_digest"] = "a" * 64
    elif field == "output":
        plan["output"]["notes"][0]["lean"] = "avoid"
        plan["output_digest"] = cache._cache_hash(plan["output"])
    elif field == "ledger":
        plan["ledger_rows"][0]["lean"] = "avoid"
    elif field == "publication":
        plan["steps"][0]["state"] = "ready"
    else:
        row["receipt"]["close"] = {"disposition": "refused", "closed": False,
                                  "effect_unknown": False, "attempted": True}
    state.cache.write_text(json.dumps(document))
    before, effects = bytes_after(state), counts(state)
    assert run(state, force=True)["degraded"] == "application_fabric_owner_refused"
    assert bytes_after(state) == before and counts(state) == effects


@pytest.mark.parametrize("mode", ["gather", "after_legacy"])
def test_late_auto_selection_cannot_publish_legacy_result(stock_auto, monkeypatch, mode):
    state = stock_auto
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    legacy_calls = []
    def legacy(system, user, cfg):
        legacy_calls.append(True)
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
        return json.dumps({"notes": [note()]}), None
    monkeypatch.setattr(sd.master_brain, "_call_model", legacy)
    if mode == "gather":
        def gather(root, cfg):
            monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "shared_fabric")
            return copy.deepcopy(state.input)
        monkeypatch.setattr(sd, "gather_top_picks", gather)
    result = run(state)
    assert result["degraded"] == "application_fabric_selection_changed"
    assert len(legacy_calls) == (0 if mode == "gather" else 1)
    assert counts(state) == (0, 0, 0, 0, 0)
    assert not (state.root / "data/stock_desk/theses.jsonl").exists()


def test_unknown_usage_remains_nullable_and_native_risk_clamp_survives(stock_auto):
    state = stock_auto
    state.input["picks"][0]["conviction"] = {"cycle_blocked": True, "verdict": "Weak"}
    state.native.response["usage"] = {"prompt_tokens": 11}
    output = run(state)
    assert output["notes"][0]["lean"] == "cautious" and output["degraded"] is None
    row = own(state)["cache"]["entries"][0]
    assert row["receipt"]["usage"]["usage_state"] == "unknown"
    assert row["receipt"]["usage"]["output_tokens"] is None
    assert row["receipt"]["observed_usage"]["input_tokens"] == 11
    assert row["receipt"]["observed_usage"]["output_tokens"] is None
    assert state.costs == []  # no invented complete-token usage event


def test_distinct_input_keeps_original_publication_and_distinct_ids(stock_auto):
    state = stock_auto
    first = run(state)
    original = copy.deepcopy(own(state))
    state.input["as_of"] = "2026-11-07"
    second = run(state, force=True)
    assert second["degraded"] is None
    assert first["notes"][0]["id"] != second["notes"][0]["id"]
    current = own(state)
    assert current["cache"]["entries"][0] == original["cache"]["entries"][0]
    first_id = original["cache"]["entries"][0]["operation_id"]
    assert current["publications"][first_id] == original["publications"][first_id]
    assert counts(state) == (2, 2, 2, 2, 2)


def test_explicit_workload_and_missing_capability_refuse_before_credentials(stock_auto, monkeypatch):
    state = stock_auto
    from engine import provider_production_modes as owner
    credential = Mock(side_effect=AssertionError("credentials"))
    monkeypatch.setattr(owner, "_resolve_credential", credential)
    state.cfg["workload_profile"] = "portfolio_analysis"
    assert run(state)["degraded"]
    assert not credential.called and counts(state) == (0, 0, 0, 0, 0)


def test_publication_obligation_blocks_the_gap_after_terminal_model_result(stock_auto, monkeypatch):
    state = stock_auto
    original = sd._stock_publish
    arrivals = []
    def publish(root, operation_id, persist, claim_id=None):
        claim = own(state)["publication_claim"]
        assert claim["operation_id"] == operation_id
        assert own(state)["cache"]["entries"][0]["state"] == "terminal"
        state.input["as_of"] = "2026-11-07"
        arrivals.append(run(state, force=True))
        return original(root, operation_id, persist, claim_id)
    monkeypatch.setattr(sd, "_stock_publish", publish)
    result = run(state)
    assert result["degraded"] is None
    assert arrivals[0]["degraded"] == "application_fabric_original_held"
    assert counts(state) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("kind", ["unknown", "duplicate"])
def test_invalid_ticker_batch_never_reaches_any_publisher(stock_auto, kind):
    state = stock_auto
    notes = [note()]
    if kind == "unknown":
        notes[0]["ticker"] = "UNSEEN"
    else:
        notes.append(note())
    state.native.response = _fixed.packet(json.dumps({"notes": notes}))
    assert run(state)["degraded"]
    assert own(state)["publications"] == {}
    assert state.registrations == []
    assert not (state.root / "data/stock_desk/theses.jsonl").exists()


def test_foreign_price_root_refuses_before_inference(stock_auto, monkeypatch, tmp_path):
    state = stock_auto
    other = tmp_path / "other-price-owner"
    other.mkdir()
    monkeypatch.setattr(config, "ROOT", other)
    assert run(state)["degraded"]
    assert counts(state) == (0, 0, 0, 0, 0)


def test_registrar_return_is_at_most_once_and_not_claim_materialization(stock_auto, monkeypatch):
    state = stock_auto
    partial = {"n_candidates": 2, "n_accepted": 1, "n_rejected": 0,
               "error": None, "clock_started": True, "clock_record": {"attempted": True}}
    def register(rows, picks, root):
        state.registrations.append(copy.deepcopy(rows))
        return copy.deepcopy(partial)
    monkeypatch.setattr(sd, "_register_qledger_claims", register)
    result = run(state)
    assert result["degraded"] is None
    plan = next(iter(own(state)["publications"].values()))
    assert plan["steps"][1]["receipt"] == {
        "invoked": True, "returned": partial, "materialization_proven": False}
    assert run(state) == result and len(state.registrations) == 1


def test_cancelled_original_retains_custody_before_new_input(stock_auto, monkeypatch):
    state = stock_auto
    from engine import llm_auth
    stop = KeyboardInterrupt("synthetic cancellation before provider delivery")
    with patch.object(llm_auth, "make_call", side_effect=stop):
        with pytest.raises(KeyboardInterrupt) as captured:
            run(state)
    assert captured.value is stop
    before = counts(state)
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    assert run(state, force=True)["degraded"]
    assert counts(state) == before
