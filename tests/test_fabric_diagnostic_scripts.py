"""Operator diagnostic public paths through the exact shared/native owners."""
from dataclasses import replace
import copy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import fabric_inference_client as transport, llm_auth as auth
from engine import provider_production_modes as owner, provider_health
from lib import ai_costs
from scripts import check_extraction_drift as drift, key_pool_probe as probe
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_native_application_composition import native, selected, MODEL  # noqa: F401

pytestmark = pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                               reason="exact paired native source required")
_CLIENT = transport.FabricInferenceClient
_USAGE_WRITER = ai_costs.record_usage
_HEALTH_WRITER = provider_health.record_attempt


def packet(text='{"direction":"bullish","magnitude":2,"confidence":"medium","reversibility":"permanent","quote_span":"Company agreed"}', *, model=MODEL, usage=True):
    result = {"model": model, "choices": [{"index": 0, "finish_reason": "stop",
        "message": {"role": "assistant", "content": text}}]}
    if usage: result["usage"] = {"prompt_tokens": 11, "completion_tokens": 7}
    return result


def anchors(n=3):
    return [{"anchor_id": f"anchor-{i}", "source_lane": "fixture", "source_id": f"source-{i}",
        "body": f"Company agreed to acquire Acme. Original anchor {i}.", "gold_source": "synthetic",
        "gold": {"direction": "bullish", "magnitude": 2, "confidence": "medium", "reversibility": "permanent"}}
        for i in range(n)]


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@pytest.fixture
def diagnostic(selected, tmp_path_factory, monkeypatch):
    state = selected
    state.native.grant.update(workloads=["portfolio_analysis"], max_steps=8)
    state.native.save()
    service = replace(state.native.service, workload="portfolio_analysis")
    state.server = state.native.go.make_server(state.native.router, lease_gateway=state.native.gateway,
        application_services=(service,))
    state.native._serve(state.server)
    state.transport = replace(state.transport, base_url=f"http://127.0.0.1:{state.server.server_port}/v1")
    monkeypatch.setitem(owner._APPLICATION_FABRIC_TRANSPORTS, "fixture_v1", state.transport)
    state.row.update({k: getattr(state.transport, k) for k in owner._APPLICATION_IDENTITY_FIELDS})
    state.manifest["capabilities"][0]["allowed_lanes"] = ["extraction-drift", "key-pool-probe"]
    state.save()
    monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "portfolio_analysis")
    monkeypatch.setattr(drift, "ROOT", state.root)
    monkeypatch.setattr(probe, "_ROOT", state.root)
    monkeypatch.setattr(auth, "_repo_root", lambda: state.root / "wrong-default-root")
    state.cfg = {"qual_extraction": {"workload_profile": "portfolio_analysis"}}
    monkeypatch.setattr(drift, "_live_config", lambda: state.cfg)
    state.status = state.root / "data/qledger/run_status.json"
    monkeypatch.setattr(drift, "STATUS_FILE", state.status)
    state.input = state.root / "anchors.jsonl"
    state.anchors = anchors()
    state.input.write_text("".join(json.dumps(a) + "\n" for a in state.anchors))
    telemetry = tmp_path_factory.mktemp("diagnostic-telemetry")
    state.cost_path = telemetry / "data/ai_costs/usage.jsonl"
    state.health_path = telemetry / "health.jsonl"
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(telemetry))
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    monkeypatch.setenv("PROVIDER_HEALTH_PATH", str(state.health_path))
    monkeypatch.delenv("PROVIDER_HEALTH_DISABLED", raising=False)
    monkeypatch.setattr(ai_costs, "record_usage", _USAGE_WRITER)
    monkeypatch.setattr(provider_health, "record_attempt", _HEALTH_WRITER)
    state.native_builder = Mock(side_effect=AssertionError("native discovery"))
    monkeypatch.setattr(auth, "build_providers", state.native_builder)
    state.closes = []
    close = _CLIENT.close
    def recorded_close(client):
        state.closes.append(client.operation_id)
        return close(client)
    monkeypatch.setattr(_CLIENT, "close", recorded_close)
    state.responses = [packet()]
    def respond():
        state.native.response = state.responses[min(len(state.native.posts) - 1, len(state.responses) - 1)]
    state.native.on_upstream = respond
    return state


def test_selected_key_main_is_one_service_probe_with_real_usage(diagnostic, monkeypatch, capsys):
    state = diagnostic
    clear = Mock(side_effect=AssertionError("native health reset"))
    monkeypatch.setattr(auth, "clear_dead", clear)
    for name in probe._PROBE_ENVS: monkeypatch.setenv(name, "synthetic-unused")
    assert probe.main(["--fabric-operation-id", "diagnostic:key-one"]) == 0
    output = capsys.readouterr().out
    assert "FABRIC_SERVICE" in output and "OAuth key pool" not in output and "key(s) serving" not in output
    report = json.loads(output.splitlines()[-1])
    assert report["bound_model"] == report["observed_model"] == MODEL and report["close"]["closed"]
    assert len(state.native.posts) == len(state.native.rows("leases")) == len(state.closes) == 1
    costs = rows(state.cost_path)
    assert len(costs) == 1 and costs[0]["model"] == MODEL and costs[0]["lane"] == "key-pool-probe"
    assert probe.probe_env(probe._PROBE_ENVS[0], "ignored") == "NOT_APPLICABLE:FABRIC_SERVICE"
    clear.assert_not_called(); state.native_builder.assert_not_called()


@pytest.mark.parametrize("change", ["identity", "invalid-identity", "model", "profile", "empty-profile", "mode", "capability"])
def test_key_preflight_refuses_before_credentials(diagnostic, monkeypatch, change):
    argv = ["--fabric-operation-id", "diagnostic:key-one"]
    if change == "identity": argv = []
    elif change == "invalid-identity": argv = ["--fabric-operation-id", "bad id"]
    elif change == "model": argv += ["--model", "wrong-requested-model"]
    elif change == "profile": monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE")
    elif change == "empty-profile": monkeypatch.setenv("MM_PROVIDER_WORKLOAD_PROFILE", "")
    elif change == "mode": monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    else:
        diagnostic.manifest["capabilities"][0]["allowed_lanes"] = ["unrelated"]; diagnostic.save()
    assert probe.main(argv) == 1
    assert not diagnostic.events and not diagnostic.native.posts
    diagnostic.native_builder.assert_not_called()


def test_native_probe_executes_only_the_requested_oauth_key(diagnostic, monkeypatch):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE")
    right = Mock(return_value=SimpleNamespace(content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=1)))
    wrong = Mock(side_effect=AssertionError("wrong key or Codex"))
    target = "CLAUDE_CODE_OAUTH_TOKEN_3"
    providers = [{"name": name, "env_var": env, "cred": "synthetic", "model": "native-fixture",
        "client": SimpleNamespace(messages=SimpleNamespace(create=callback))}
        for name, env, callback in [("oauth", "CLAUDE_CODE_OAUTH_TOKEN_2", wrong),
                                   ("codex", target, wrong), ("oauth", target, right)]]
    build = Mock(return_value=providers); monkeypatch.setattr(auth, "build_providers", build)
    assert probe.probe_env(target, "native-fixture") == "OK"
    assert build.call_args.args[0]["codex_provider"] is False
    assert build.call_args.args[0]["client_max_retries"] == 0
    assert right.call_count == 1; wrong.assert_not_called()
    build.return_value = providers[:2]
    assert probe.probe_env(target, "native-fixture") == "ABSENT"
    assert right.call_count == 1


def test_full_cli_one_binding_all_anchors_and_truthful_projection(diagnostic):
    state = diagnostic
    state.cfg["qual_extraction"]["model_id"] = "requested-native-model"
    state.status.parent.mkdir(parents=True); state.status.write_text('{"other_lane":{"ok":true}}')
    assert drift.main(["--anchor-file", str(state.input), "--fabric-operation-id", "diagnostic:full"]) == 0
    report = json.loads(state.status.read_text())
    assert report["other_lane"] == {"ok": True}
    result = report["extraction_drift"]; f = result["fabric"]
    assert result["gate_pass"] and result["model_id"] == f["bound_model"] == f["observed_model"] == MODEL
    assert f["requested_model"] == "requested-native-model"
    assert (f["expected"], f["attempted"], f["completed"], f["predicted"], f["missing"], f["unknown"]) == (3, 3, 3, 3, 0, 0)
    assert len(state.native.rows("application_turns")) == len(state.native.rows("leases")) == len(state.closes) == 1
    assert len(state.native.posts) == len(rows(state.cost_path)) == len(rows(state.health_path)) == 3
    assert {row["cycle_id"] for row in rows(state.cost_path)} == {"diagnostic:full"}
    for index, post in enumerate(state.native.posts):
        request = json.loads(post[1]); assert request["messages"][-1]["content"] == "TEXT:\n" + state.anchors[index]["body"]
        assert request["max_tokens"] == 400
    state.native_builder.assert_not_called()


def test_light_sample_is_frozen_before_callbacks_and_bound_once(diagnostic):
    original = copy.deepcopy(diagnostic.anchors)
    chosen = random.Random(9).sample(original, 2)
    respond = diagnostic.native.on_upstream
    def mutate():
        respond(); diagnostic.anchors[0]["body"] = "late mutated body"
    diagnostic.native.on_upstream = mutate
    result = drift.light_check(diagnostic.anchors, n=2, seed=9, fabric_operation_id="diagnostic:light")
    assert result["n_sample"] == 2 and result["gate_pass"]
    assert result["fabric"]["sample_ids"] == [a["anchor_id"] for a in chosen]
    assert [json.loads(p[1])["messages"][-1]["content"] for p in diagnostic.native.posts] == ["TEXT:\n" + a["body"] for a in chosen]
    assert len(diagnostic.native.rows("application_turns")) == 1


def test_known_bad_json_is_missing_without_repair_or_subset_pass(diagnostic):
    diagnostic.responses = [packet(), packet("not-json"), packet()]
    result = drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:bad-json")
    assert result["field_agree_rate"] == 1.0 and not result["gate_pass"]
    assert result["fabric"]["completed"] == 3 and result["fabric"]["predicted"] == 2
    assert result["fabric"]["missing"] == 1 and len(diagnostic.native.posts) == 3


@pytest.mark.parametrize("text", ['{"direction":[]}', '{"direction":"bullish","magnitude":Infinity}',
    '{"direction":"bullish","magnitude":true,"confidence":"medium","reversibility":"permanent","quote_span":[]}'])
def test_malformed_prediction_fields_do_not_erase_the_final_receipt(diagnostic, capsys, text):
    diagnostic.responses = [packet(), packet(text), packet()]
    result = drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:bad-fields")
    assert not result["gate_pass"] and result["fabric"]["missing"] == 1
    assert result["fabric"]["usage"]["completed_input_tokens"] == 33
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["phase"] == "result"
    assert len(diagnostic.native.posts) == 3 and len(diagnostic.closes) == 1


def test_key_close_interruption_still_reports_paid_usage_once(diagnostic, monkeypatch, capsys):
    calls = []
    def close(client):
        calls.append(client.operation_id)
        raise KeyboardInterrupt("synthetic close interruption")
    monkeypatch.setattr(_CLIENT, "close", close)
    with pytest.raises(KeyboardInterrupt, match="close interruption"):
        probe.main(["--fabric-operation-id", "diagnostic:key-close"])
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert not report["ok"] and report["error"] == "fabric_close_unsettled"
    assert report["usage"]["completed_input_tokens"] == 11 and report["observed_model"] == MODEL
    assert len(calls) == 1 and len(diagnostic.native.posts) == 1


def test_key_preserves_original_interruption_when_close_also_interrupts(diagnostic, monkeypatch, capsys):
    def invoke(*a, **kw): raise KeyboardInterrupt("original call")
    def close(*a, **kw): raise SystemExit("later close")
    monkeypatch.setattr(_CLIENT, "create", invoke)
    monkeypatch.setattr(_CLIENT, "close", close)
    with pytest.raises(KeyboardInterrupt, match="original call"):
        probe.main(["--fabric-operation-id", "diagnostic:key-interrupted"])
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["error"] == "fabric_probe_interrupted"
    assert not diagnostic.native.posts


@pytest.mark.parametrize("failure", ["503", "model", "empty", "disconnect", "timeout", "receipt-only"])
def test_uncertain_or_invalid_original_stops_remaining_anchors(diagnostic, monkeypatch, failure):
    if failure == "503": diagnostic.native.response_status = 503
    elif failure == "model": diagnostic.responses = [packet(model="observed-other")]
    elif failure == "empty": diagnostic.responses = [packet("")]
    elif failure == "disconnect": diagnostic.native.reset = True
    else:
        from engine.fabric_inference_client import FabricInferenceError
        def fail(*a, **kw):
            if failure == "timeout": raise TimeoutError("synthetic")
            raise FabricInferenceError("fixture", effect_unknown=False, disposition="terminal_receipt_only")
        monkeypatch.setattr(_CLIENT, "create", fail)
    result = drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:failed")
    assert not result["gate_pass"] and result["fabric"]["attempted"] == 1
    assert len(diagnostic.native.posts) <= 1 and len(diagnostic.closes) == 1
    if failure in ("503", "model", "empty"):
        assert len(rows(diagnostic.cost_path)) == 1
        assert result["fabric"]["usage"]["completed_input_tokens"] == 11
    if failure == "model": assert result["fabric"]["observed_model"] == "observed-other"
    diagnostic.native_builder.assert_not_called()


def test_native_step_limit_cannot_be_evaded_by_another_turn(diagnostic):
    result = drift.full_check(anchors(10), fabric_operation_id="diagnostic:bounded")
    assert not result["gate_pass"] and result["fabric"]["predicted"] == 8
    assert len(diagnostic.native.posts) == 8 and len(diagnostic.native.rows("application_turns")) == 1


def test_missing_usage_remains_nullable_but_answer_coverage_is_real(diagnostic):
    diagnostic.responses = [packet(usage=False)]
    result = drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:nullable")
    assert result["gate_pass"] and result["fabric"]["usage"]["input_tokens"] is None
    assert result["fabric"]["usage"]["usage_state"] == "unknown" and not rows(diagnostic.cost_path)


def test_unknown_close_keeps_answers_and_usage_without_passing(diagnostic, monkeypatch):
    calls = []
    def close(client):
        calls.append(client.operation_id)
        return {"disposition": "effect_unknown", "closed": False, "effect_unknown": True, "attempted": True}
    monkeypatch.setattr(_CLIENT, "close", close)
    result = drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:unknown-close")
    assert not result["gate_pass"] and result["fabric"]["predicted"] == 3
    assert result["fabric"]["usage"]["completed_input_tokens"] == 33
    assert len(calls) == 1 and len(rows(diagnostic.cost_path)) == 3


@pytest.mark.parametrize("kind", ["identity", "profile", "mode", "binding-drift"])
def test_drift_preflight_or_inspection_change_never_discovers_native(diagnostic, monkeypatch, kind):
    op = "diagnostic:refused"
    if kind == "identity": op = None
    elif kind == "profile": diagnostic.cfg["qual_extraction"]["workload_profile"] = None
    elif kind == "mode": monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    else:
        original = owner.ApplicationFabricFactory.with_inspection
        def drift_binding(factory, inspection):
            result = original(factory, inspection)
            diagnostic.row["enabled"] = False; diagnostic.save()
            return result
        monkeypatch.setattr(owner.ApplicationFabricFactory, "with_inspection", drift_binding)
    if kind == "binding-drift":
        assert not drift.full_check(diagnostic.anchors, fabric_operation_id=op)["gate_pass"]
    else:
        with pytest.raises((ValueError, auth.FabricProviderError)):
            drift.full_check(diagnostic.anchors, fabric_operation_id=op)
    assert not diagnostic.events and not diagnostic.native.posts
    diagnostic.native_builder.assert_not_called()


def test_dry_run_ignores_invalid_selected_mode_without_any_live_effect(diagnostic, monkeypatch):
    monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "")
    live = Mock(side_effect=AssertionError("dry run loaded live config"))
    monkeypatch.setattr(drift, "_live_config", live)
    assert drift.main(["--dry-run", "--anchor-file", str(diagnostic.input)]) == 0
    assert not diagnostic.events and not diagnostic.native.posts and not diagnostic.status.exists()
    assert not rows(diagnostic.cost_path) and not rows(diagnostic.health_path)
    live.assert_not_called()


def test_baseexception_closes_original_once_and_never_sends_later_anchors(diagnostic):
    def interrupt(): raise KeyboardInterrupt("synthetic operator interruption")
    # Raise in the caller's request boundary, not a server thread.
    with pytest.MonkeyPatch.context() as m:
        m.setattr(_CLIENT, "create", lambda *a, **kw: interrupt())
        with pytest.raises(KeyboardInterrupt):
            drift.full_check(diagnostic.anchors, fabric_operation_id="diagnostic:interrupt")
    assert len(diagnostic.closes) == 1 and not diagnostic.native.posts


def test_status_failure_occurs_after_close_and_cannot_recall(diagnostic, monkeypatch):
    monkeypatch.setattr(drift, "_write_status", Mock(side_effect=OSError("synthetic status failure")))
    with pytest.raises(OSError):
        drift.main(["--anchor-file", str(diagnostic.input), "--fabric-operation-id", "diagnostic:status"])
    assert len(diagnostic.closes) == 1 and len(diagnostic.native.posts) == 3
    assert len(rows(diagnostic.cost_path)) == 3
