"""Research public mains through the actual shared client and pinned native A/B.

Only provider responses, qualified grants and local fixture credentials are
synthetic. Pack, ingest, screen, gates, SQLite and global usage writers are real.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from unittest.mock import Mock, patch

import pytest

from scripts import run_causal_brainstorm as causal, run_signal_foundry_brainstorm as foundry
from engine import llm_auth as auth, provider_production_modes as owner
from engine import fabric_inference_client as transport
from engine.signal_foundry import spec as sf_spec
from lib import ai_costs
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="exact paired native source required")
SOURCE = Path(__file__).resolve().parents[1]
_USAGE_WRITER = ai_costs.record_usage
_CLIENT = transport.FabricInferenceClient
LANES = ("causal-brainstorm", "signal-foundry")


def card():
    from engine.neuralweb.causal_schema import _compute_env_hash
    environment = {"should_hold": ["risk_on"], "should_break": ["risk_off"]}
    environment["frozen_hash"] = _compute_env_hash(environment)
    return {"mechanism_id": "research-original-card", "family": "macro_transmission",
        "claim_en": "When liquidity expands, equities tend to follow within 10 days.",
        "claim_zh": "流动性扩张后股票广度可能变化。",
        "causal_graph": {"cause": "fed_balance_sheet_growth", "target": "equity_breadth_index",
                         "mediators": [], "confounders": ["growth_surprise"], "colliders_to_avoid": []},
        "environment_map": environment,
        "falsifiers": ["Lagged placebo predicts cause.", "Effect disappears in the hold environment."],
        "test_spec": {"exit_path": "a", "claim_shape": "lead_lag", "horizon_d": 21,
                      "metric": "forward_breadth_21d", "threshold": 0.55, "min_n": 50,
                      "environment": "risk_on"},
        "lineage": {"source": "llm_proposed", "pack_id": "fixture-research-pack", "model": MODEL},
        "status": "inbox"}


def signal():
    return {"id": "SF-0001", "name": "Research fixture lag", "market": "US",
        "thesis": "A lagged synthetic context measurement can be tested against a declared target.",
        "data": [{"path": "data/fred/research_fixture.csv", "column": "value", "pit": "lagged"}],
        "feature": {"pipeline": [["lag", {"n": 1}]]},
        "target": {"path": "data/yahoo/research_target.csv", "kind": "excess_return", "horizon_d": 21},
        "gates": {"min_t_hac": 2.0, "fdr_q": 0.1, "dsr": 0.9},
        "registered_at": "2026-11-01", "baseline": "buy_and_hold",
        "orthogonality_note": "A distinct synthetic lagged fixture, with no prior corpus entry.",
        "evidence_note": "Synthetic tracked date/value sources; no performance claim.",
        "seed_id": "research-fixture-seed"}


def packet(value, *, finish="stop", model=MODEL, usage=True):
    row = {"model": model, "choices": [{"index": 0, "finish_reason": finish,
        "message": {"role": "assistant", "content": value if isinstance(value, str) else json.dumps(value)}}]}
    if usage:
        row["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
    return row


def load_real_copy(root, relative, name, monkeypatch):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / relative, target)
    assert target.read_bytes() == (SOURCE / relative).read_bytes()
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    parent, attr = name.rsplit(".", 1)
    monkeypatch.setattr(importlib.import_module(parent), attr, module, raising=False)
    return module


@pytest.fixture(params=LANES)
def research(selected, request, tmp_path_factory, monkeypatch):
    state = selected
    state.lane = request.param
    state.runner = causal if state.lane == LANES[0] else foundry
    state.native.grant["workloads"] = ["portfolio_analysis"]
    state.native.save()
    service = state.native.go.ApplicationServiceBinding(
        "macro", "vps", "portfolio_analysis",
        state.native.service.credential_ref, state.native.service.credential)
    server = state.native.go.make_server(state.native.router, lease_gateway=state.native.gateway,
                                         application_services=(service,))
    state.native.service, state.native.server = service, server
    state.native._serve(server)
    recipe = replace(state.transport, base_url=f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", recipe)
    state.row.update({key: getattr(recipe, key) for key in owner._APPLICATION_IDENTITY_FIELDS})
    state.manifest["capabilities"][0]["allowed_lanes"].extend(LANES)
    state.save()
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "portfolio_analysis")
    monkeypatch.setenv("SIGNAL_FOUNDRY_PAUSED", "false")
    monkeypatch.setattr(sys, "path", list(sys.path))
    for relative in ("scripts/__init__.py", "config/causal_priors.yml", "config/signal_blocklist.yml"):
        source = SOURCE / relative
        if source.is_file():
            target = state.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    state.ingest = load_real_copy(state.root, "scripts/causal_ingest_brainstorm.py",
                                  "scripts.causal_ingest_brainstorm", monkeypatch)
    state.pack_module = load_real_copy(state.root, "scripts/causal_brainstorm_pack.py",
                                      "scripts.causal_brainstorm_pack", monkeypatch)
    assert state.ingest.ROOT == state.pack_module.ROOT == state.root
    state.cfg = {"auto_loop": True, "workload_profile": "portfolio_analysis",
        "weekly_budget_cards": 3, "budgets": {"filed_per_week": 5},
        "model_roles": {"generator": "requested-generator", "skeptic": "requested-skeptic",
                        "compiler": "requested-compiler"},
        "models": {"generator": "requested-generator", "skeptic": "requested-skeptic",
                   "compiler": "requested-compiler"}}
    state.cfg_path = state.root / "config" / ("causal_llm.yml" if state.lane == LANES[0]
                                              else "signal_foundry.yml")
    state.cfg_path.write_text(json.dumps(state.cfg))
    for relative, offset in (("data/fred/research_fixture.csv", 0), ("data/yahoo/research_target.csv", 100)):
        target = state.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("date,value\n" + "".join(
            f"{year}-{month:02d}-01,{offset+(year-2018)*12+month}\n"
            for year in range(2018, 2026) for month in range(1, 13)))
    subprocess.run(["git", "init", "-q", str(state.root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(state.root), "add", "--",
                    "data/fred/research_fixture.csv", "data/yahoo/research_target.csv"],
                   check=True, capture_output=True)
    state.usage_root = tmp_path_factory.mktemp("research-usage")
    state.cost_path = state.usage_root / "data/ai_costs/usage.jsonl"
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(state.usage_root))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setattr(auth, "build_providers", Mock(side_effect=AssertionError("native discovery")))
    state.closes = []
    original_close = _CLIENT.close
    def close(client):
        state.closes.append(client.operation_id)
        return original_close(client)
    monkeypatch.setattr(_CLIENT, "close", close)
    state.proposal = card() if state.lane == LANES[0] else signal()
    state.responses = [packet([state.proposal]), packet([]), packet([state.proposal])]
    def upstream():
        run = original(state)
        assert run["state"] == "active" and run["stages"][-1]["state"] == "pending"
        assert run["stages"][-1]["operation_id"] in {
            row["turn_id"] for row in state.native.pending_at_send[-1] if row["state"] == "pending"}
        # The actual network call must not hold the journal's cross-process lock.
        with causal._r_lock(journal(state), state.root):
            assert causal._r_history(journal(state), state.root, state.lane)[1]
        state.native.response = state.responses[len(state.native.posts) - 1]
    state.native.on_upstream = upstream
    return state


def journal(state):
    return causal._r_path(state.root, state.lane)


def original(state):
    rows = [json.loads(line) for line in journal(state).read_text().splitlines()]
    return [row["run"] for row in rows if row.get("event") == causal._RESEARCH_EVENT][-1]


def invoke(state, *args):
    return state.runner.main(["--root", str(state.root), *args])


def usages(state):
    return [json.loads(line) for line in state.cost_path.read_text().splitlines()] if state.cost_path.exists() else []


def lane_status(state):
    path = state.root / ("data/neuralweb/causal_llm_lane.json" if state.lane == LANES[0]
                         else "data/signal_foundry/lane_status.json")
    return json.loads(path.read_text())


@pytest.mark.parametrize("dry", [False, True])
def test_public_three_roles_actual_native_workload_usage_and_real_filing(research, dry):
    state = research
    assert invoke(state, *(["--dry-run"] if dry else [])) == 0
    assert journal(state).is_file(), lane_status(state)
    run = original(state)
    assert run["state"] == "complete", lane_status(state)
    assert [stage["role"] for stage in run["stages"]] == list(causal._RESEARCH_ROLES)
    assert [stage["request"]["max_tokens"] for stage in run["stages"]] == list(causal._RESEARCH_BOUNDS[state.lane])
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 3
    assert len(set(state.closes)) == 3
    assert all(stage["receipt"]["served_model"] == MODEL for stage in run["stages"])
    assert all(stage["request"]["requested_model"].startswith("requested-") for stage in run["stages"])
    assert all(row["model"] == MODEL and row["lane"] == state.lane
               and (row["input_tokens"], row["output_tokens"]) == (11, 7) for row in usages(state))
    turns = state.native.rows("application_turns")
    assert {row["workload"] for row in turns} == {"portfolio_analysis"}
    assert {row["principal_id"] for row in turns} == {"macro"}
    assert all(row["state"] == "released" for row in state.native.rows("leases"))
    assert run["filing"]["state"] == "closed"
    receipt = run["filing"]["receipt"]
    assert receipt["n_filed"] == (0 if dry else 1)
    if state.lane == LANES[0]:
        rows = receipt["files"]["cards"]["rows"]
        assert (not rows) if dry else rows[0]["status"] == "inbox"
        assert len(receipt["files"]["budget"]["rows"]) == len(rows)
        assert not (state.root / "data/trial_ledger.jsonl").exists()
    else:
        screened = receipt["screened_rows"]
        assert len(screened) == 1 and screened[0]["status"] == "proposed", screened
        assert screened[0]["gates_hash"] == sf_spec.stamp_gates_hash(screened[0])["gates_hash"]
        assert screened[0]["construction_hash"] == sf_spec.construction_hash(screened[0])
        assert screened[0]["fabric_run_id"] == run["run_id"]
        assert not (state.root / "data/neuralweb/governance.jsonl").exists()


def freeze_real_pack(state, monkeypatch):
    name = "_build_fresh_pack" if state.lane == LANES[0] else "_build_sf_pack"
    original_builder = getattr(state.runner, name)
    pack = original_builder(state.root)
    monkeypatch.setattr(state.runner, name, lambda *a, **k: pack)
    return pack


def all_artifacts(state):
    paths = ("data/neuralweb/causal_mechanisms.jsonl", "data/neuralweb/causal_filing_budget.jsonl",
             "data/neuralweb/governance.jsonl", "data/signal_foundry/candidates.jsonl")
    return {p: (state.root / p).read_bytes() if (state.root / p).exists() else None for p in paths}


def test_historical_original_reuse_across_intervening_completed_run(research, monkeypatch):
    state = research
    freeze_real_pack(state, monkeypatch)
    state.responses *= 2
    assert invoke(state, "--dry-run") == 0
    assert original(state)["state"] == "complete"
    first = original(state)["run_id"]
    config = state.cfg_path.read_bytes()
    state.cfg_path.write_text(json.dumps({**state.cfg, "research_case": "B"}))
    assert invoke(state, "--dry-run") == 0
    assert original(state)["state"] == "complete" and original(state)["run_id"] != first
    before = journal(state).read_bytes(), all_artifacts(state), state.cost_path.read_bytes()
    state.cfg_path.write_bytes(config)
    assert invoke(state, "--dry-run") == 0
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 6
    assert before == (journal(state).read_bytes(), all_artifacts(state), state.cost_path.read_bytes())
    assert "already complete" in lane_status(state)["reason"]


@pytest.mark.parametrize("finish,answer", [
    ("length", "[{}]"), ("stop", ""), ("stop", "   "),
])
def test_incomplete_or_empty_answer_holds_original_and_never_replays(research, finish, answer, monkeypatch):
    state = research
    state.responses[0] = packet(answer, finish=finish)
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "held" and len(run["stages"]) == 1
    assert run["filing"] is None
    counts = len(state.native.posts), len(state.closes), len(usages(state))
    assert counts[0] == counts[1] == 1
    before = journal(state).read_bytes(), all_artifacts(state)
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE")
    state.cfg_path.unlink()
    assert invoke(state, "--dry-run") == 0
    assert "research_original_held" in lane_status(state)["reason"]
    assert counts == (len(state.native.posts), len(state.closes), len(usages(state)))
    assert before == (journal(state).read_bytes(), all_artifacts(state))


def test_known_answer_unknown_close_retains_usage_and_stops_chain(research, monkeypatch):
    state = research
    real_close = _CLIENT.close
    def lose_close(client):
        real_close(client)
        raise OSError("lost close acknowledgement")
    monkeypatch.setattr(_CLIENT, "close", lose_close)
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "held" and run["filing"] is None
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 1
    receipt = run["stages"][0]["receipt"]
    assert receipt["usage"]["usage_state"] == "known"
    assert receipt["usage"]["input_tokens"] == 11
    assert receipt["close"]["effect_unknown"] and receipt["effect_unknown"]
    assert invoke(state) == 0
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 1


@pytest.mark.parametrize("partial", [False, True])
def test_unknown_usage_remains_nullable_with_completed_filing(research, partial):
    state = research
    for response in state.responses:
        response.pop("usage")
        if partial:
            response["usage"] = {"prompt_tokens": 11}
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "complete" and run["filing"]["receipt"]["n_filed"] == 1
    assert not usages(state)
    for stage in run["stages"]:
        receipt = stage["receipt"]
        assert receipt["usage"] == {"input_tokens": None, "output_tokens": None,
            "usage_state": "unknown", "completed_input_tokens": 0, "completed_output_tokens": 0}
        assert receipt["observation"]["input_tokens"] == (11 if partial else None)
        assert receipt["close"]["disposition"] == "closed"


@pytest.mark.parametrize("role", ["generator", "skeptic", "compiler"])
def test_complete_malformed_optional_output_has_known_zero_or_filing_outcome(research, role):
    state = research
    index = causal._RESEARCH_ROLES.index(role)
    state.responses[index] = packet("complete but not JSON")
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "complete"
    expected = 1 if role == "generator" else 3
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == expected
    assert (run["filing"] is None) if role == "generator" else run["filing"]["receipt"]["n_filed"] == 1


def test_all_dropped_is_two_closed_stages_with_no_filing(research):
    state = research
    key = "card_id" if state.lane == LANES[0] else "spec_id"
    identity = state.proposal["mechanism_id" if state.lane == LANES[0] else "id"]
    state.responses[1] = packet([{key: identity, "recommendation": "ADVISORY_DROP",
                                  "blockers": ["synthetic declared blocker"]}])
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "complete" and run["filing"] is None
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 2


def rewrite_chain(state, transform):
    previous = None
    rows = [json.loads(line) for line in journal(state).read_text().splitlines()]
    for row in rows:
        if row.get("event") != causal._RESEARCH_EVENT:
            continue
        transform(row["run"])
        row["previous"] = previous
        row["digest"] = causal._r_hash({k: v for k, v in row.items() if k != "digest"})
        previous = row["digest"]
    journal(state).write_text("".join(causal._r_json(row) + "\n" for row in rows))


@pytest.mark.parametrize("corruption", [
    "observation_id", "observation_model", "receipt_provider", "binding_model",
    "usage_bool", "usage_negative", "usage_known_null", "close_false", "close_unattempted",
    "filing_kind", "filing_path", "filing_count", "filing_model", "filing_empty", "outcome_count",
    "outcome_kind", "outcome_total",
])
def test_rehashed_nested_corruption_refuses_before_any_model_or_filing(research, corruption, monkeypatch):
    state = research
    assert invoke(state) == 0
    assert original(state)["state"] == "complete"
    def corrupt(run):
        for stage in run["stages"]:
            receipt = stage["receipt"]
            if stage["state"] != "closed":
                continue
            if corruption == "observation_id": receipt["observation"]["request_id"] = "foreign:brain:0"
            if corruption == "observation_model": receipt["observation"]["serving_model"] = "foreign-model"
            if corruption == "receipt_provider": receipt["provider"] = "foreign-provider"
            if corruption == "binding_model": receipt["requested_model"] = "foreign-model"
            if corruption == "usage_bool": receipt["usage"]["input_tokens"] = True
            if corruption == "usage_negative": receipt["usage"]["completed_input_tokens"] = -1
            if corruption == "usage_known_null": receipt["usage"]["input_tokens"] = None
            if corruption == "close_false": receipt["close"]["closed"] = False
            if corruption == "close_unattempted": receipt["close"]["attempted"] = False
        filing = run["filing"]
        if filing is not None and filing["state"] == "closed":
            receipt = filing["receipt"]
            if corruption == "filing_kind": receipt["kind"] = "other-lane"
            if corruption == "filing_path":
                receipt["files"]["cards" if state.lane == LANES[0] else "candidates"]["path"] = "data/foreign.jsonl"
            if corruption == "filing_count": receipt["n_filed"] += 1
            if corruption == "filing_model": receipt["governance"]["models"]["generator"] = "foreign-model"
            if corruption == "filing_empty": filing["receipt"] = {}
        if run["state"] == "complete" and corruption == "outcome_count":
            run["outcome"]["stages"]["ingest" if state.lane == LANES[0] else "screen"]["n_filed"] += 1
        if run["state"] == "complete" and corruption == "outcome_kind":
            run["outcome"]["result"] = "unqualified-success"
        if run["state"] == "complete" and corruption == "outcome_total":
            run["outcome"]["n_filed"] = 0
    rewrite_chain(state, corrupt)
    before = journal(state).read_bytes(), all_artifacts(state), state.cost_path.read_bytes()
    monkeypatch.setattr(owner, "_resolve_credential", Mock(side_effect=AssertionError("credential read")))
    monkeypatch.setattr(causal, "_build_fresh_pack", Mock(side_effect=AssertionError("pack rebuilt")))
    monkeypatch.setattr(foundry, "_build_sf_pack", Mock(side_effect=AssertionError("pack rebuilt")))
    assert invoke(state) == 0
    assert "research_" in lane_status(state)["reason"]
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 3
    assert before == (journal(state).read_bytes(), all_artifacts(state), state.cost_path.read_bytes())


@pytest.mark.parametrize("boundary", ["intent", "result"])
def test_actual_append_with_lost_ack_stays_original_after_new_process(research, boundary, monkeypatch):
    state = research
    real_append = causal._r_append
    injected = []
    def lose_ack(path, root, lane, run, expected):
        result = real_append(path, root, lane, run, expected)
        if not injected and run["stages"] and run["stages"][-1]["state"] == (
                "pending" if boundary == "intent" else "closed"):
            injected.append(run["run_id"])
            raise OSError("synthetic lost durable append acknowledgement")
        return result
    monkeypatch.setattr(causal, "_r_append", lose_ack)
    assert invoke(state) == 0
    run = original(state)
    assert injected and run["state"] == "active"
    expected = 0 if boundary == "intent" else 1
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == expected
    before = journal(state).read_bytes(), all_artifacts(state)
    env = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1")
    env.pop("MM_PROVIDER_APPLICATION_MODE", None)
    env.pop("MM_PROVIDER_WORKLOAD_PROFILE", None)
    cp = subprocess.run([sys.executable, str(SOURCE / "scripts" / (
        "run_causal_brainstorm.py" if state.lane == LANES[0] else "run_signal_foundry_brainstorm.py")),
        "--root", str(state.root), "--dry-run"], cwd=SOURCE, env=env, capture_output=True, text=True, timeout=30)
    assert cp.returncode == 0, cp.stderr
    assert "research_original_held" in lane_status(state)["reason"]
    assert before == (journal(state).read_bytes(), all_artifacts(state))
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == expected


def test_real_filing_then_lost_governance_ack_never_refiles(research, monkeypatch):
    state = research
    if state.lane == LANES[0]:
        from engine.neuralweb import governance
        writer = governance.append_event
        def lose_ack(*args, **kwargs):
            assert writer(*args, **kwargs) is True
            return False
        monkeypatch.setattr(governance, "append_event", lose_ack)
    else:
        writer = foundry._append_governance_event
        def lose_ack(*args, **kwargs):
            writer(*args, **kwargs)
            raise OSError("lost governance acknowledgement")
        monkeypatch.setattr(foundry, "_append_governance_event", lose_ack)
    assert invoke(state) == 0
    run = original(state)
    assert run["state"] == "held" and run["filing"]["state"] == "pending"
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 3
    path = state.root / ("data/neuralweb/causal_mechanisms.jsonl" if state.lane == LANES[0]
                         else "data/signal_foundry/candidates.jsonl")
    assert len(path.read_text().splitlines()) == 1
    before = journal(state).read_bytes(), all_artifacts(state)
    state.cfg_path.write_text("{}")
    monkeypatch.delenv("MM_PROVIDER_APPLICATION_MODE")
    assert invoke(state, "--dry-run") == 0
    assert "research_original_held" in lane_status(state)["reason"]
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 3
    assert before == (journal(state).read_bytes(), all_artifacts(state))


def test_concurrent_entry_has_one_original_and_no_network_lock(research):
    state = research
    entered, release = threading.Event(), threading.Event()
    actual_upstream = state.native.on_upstream
    def pause():
        actual_upstream()
        if len(state.native.posts) == 1:
            entered.set()
            assert release.wait(20)
    state.native.on_upstream = pause
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(invoke, state)
        try:
            assert entered.wait(10)
            assert pool.submit(invoke, state).result(timeout=10) == 0
            assert len(state.native.posts) == 1
            assert "research_original_held" in lane_status(state)["reason"]
        finally:
            release.set()
        assert first.result(timeout=20) == 0
    assert original(state)["state"] == "complete"
    assert len(state.native.posts) == len(state.closes) == len(usages(state)) == 3


def test_scheduled_unknown_cost_refuses_before_claim_credentials_or_provider(research, monkeypatch):
    state = research
    assert state.transport.cost_basis == "unknown"
    monkeypatch.setattr(owner, "_resolve_credential", Mock(side_effect=AssertionError("credential read")))
    assert invoke(state, "--trigger", "scheduled") == 0
    assert "research_scheduled_nonmetered_qualification_required" in lane_status(state)["reason"]
    assert not journal(state).exists()
    assert not state.native.posts and not state.closes and not usages(state)
