"""Actual cached callbacks bind one owner operation per invocation.

Only outbound responses are doubled; product clamps and the owner/policy/
capability chain run unchanged. These fixtures do not qualify any live pool.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine import altdata_brain, narrative_brain, risk_brain, risk_radar_review
from engine import llm_auth as auth
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_shared_default import MODEL, args, response, selected  # noqa: F401

CASES = [(risk_brain, "risk-brain"), (narrative_brain, "narrative-brain"),
         (altdata_brain, "altdata-brain"), (risk_radar_review, "risk-radar-review")]


def invoke(module, call):
    if module in (risk_brain, narrative_brain):
        return call("claude-requested-preference", "Grounded system.", "Evidence E1.")
    return call("Grounded system.", "Evidence E1.")


def risk_evidence():
    return {"as_of": "2026-11-05", "engine_state": "elevated", "engine_score": 70,
            "evidence": [{"id": "E1", "text": "Measured breadth decline."}]}


RISK_REPLY = json.dumps({"brain_state": "neutral", "risk_read": "Evidence [E1].",
    "directive": {"posture": "risk-on", "gross_tilt": 0.5}, "evidence_ids": ["E1"]})
THEME_REPLY = json.dumps({"strength": 80, "durability": 75, "continuity": 70,
    "composite": 75, "verdict": "ENTER", "confidence": "MED", "rationale": "Evidence [P2].",
    "evidence_ids": ["P2"], "falsifiable_check": {"disconfirm": "Relative decline."}})
ROTATION_REPLY = json.dumps({"summary": "Grounded rotation.", "accumulate": ["a"]})
ALTDATA_REPLY = json.dumps({"regime_read": "Measured context.", "theses": [],
    "model": "model-generated-spoof", "provider": "spoof"})
RADAR_REPLY = json.dumps({"analysis": "Measured calibration proposal.",
    "deltas": {"bands": {"caution": -999}}, "rationale": "Evidence."})


def narrative_evidence():
    return {"as_of": "2026-11-05", "region": "us", "themes": [
        {"basket": name, "name": name, "state": "NEGATIVE_DIVERGENCE",
         "lifecycle": "fading", "evidence": [{"id": "P2", "text": "Measured weakness."}]}
        for name in ("a", "b")]}


@pytest.fixture
def callbacks(selected, monkeypatch):
    selected.manifest["capabilities"][0]["allowed_lanes"] += [lane for _, lane in CASES]
    selected.save()
    selected.closed = []
    original = auth.close_fabric_provider

    def close(provider):
        original(provider)
        selected.closed.append(provider)

    monkeypatch.setattr(auth, "close_fabric_provider", close)
    return selected


@pytest.mark.parametrize("module,lane", CASES)
def test_cached_factory_is_inert_and_each_call_binds_fresh_and_closes(callbacks, module, lane):
    call = module._make_call({"usage_cycle_id": "original-cycle", "usage_stage": "analysis"})
    assert callable(call) and not callbacks.clients and not callbacks.events
    for _ in range(2):
        result = invoke(module, call)
        assert result == ("Grounded context." if module is risk_radar_review else ("Grounded context.", None))
    assert len(callbacks.calls) == len(callbacks.clients) == len(callbacks.costs) == 2
    assert callbacks.calls[0]["request_id"] != callbacks.calls[1]["request_id"]
    assert all(row["model"] == MODEL for row in callbacks.calls)
    assert all(row["lane"] == lane and row["cycle_id"] == "original-cycle"
               and row["stage"] == "analysis" for row in callbacks.costs)
    assert len(callbacks.closed) == 2 and all(p["_fabric_closed"] for p in callbacks.closed)
    for provider in callbacks.closed:
        with pytest.raises(auth.FabricProviderError):
            provider["client"].messages.create(**args())
    assert len(callbacks.calls) == 2


@pytest.mark.parametrize("module,lane", CASES)
@pytest.mark.parametrize("failure", ["timeout", "type_error", "empty", "tools", "truncated"])
def test_failed_callback_never_retries_or_rebinds_but_next_invocation_is_independent(callbacks, module, lane, failure):
    plan = {"timeout": TimeoutError("synthetic upstream loss"),
            "type_error": TypeError("synthetic malformed response"),
            "empty": response(text=""), "tools": response(tools=True),
            "truncated": response()}[failure]
    if failure == "truncated":
        plan.stop_reason = "max_tokens"
    callbacks.plans = [plan]
    call = module._make_call({})
    if module is risk_radar_review:
        with pytest.raises(auth.FabricProviderError):
            invoke(module, call)
    else:
        text, reason = invoke(module, call)
        assert text is None and reason.startswith("fabric_")
    assert len(callbacks.calls) == len(callbacks.clients) == len(callbacks.closed) == 1
    assert len(callbacks.costs) == (0 if failure in {"timeout", "type_error"} else 1)
    invoke(module, call)
    assert len(callbacks.calls) == len(callbacks.clients) == len(callbacks.closed) == 2
    assert callbacks.calls[0]["request_id"] != callbacks.calls[1]["request_id"]


@pytest.mark.parametrize("module,lane", CASES)
@pytest.mark.parametrize("profile", [None, "", "unknown", "development_agent"])
def test_explicit_invalid_profile_cannot_take_default(callbacks, module, lane, profile):
    call = module._make_call({"workload_profile": profile})
    if module is risk_radar_review:
        with pytest.raises(auth.FabricProviderError):
            invoke(module, call)
    else:
        assert invoke(module, call)[0] is None
    assert not callbacks.events and not callbacks.calls


@pytest.mark.parametrize("module,lane", CASES)
@pytest.mark.parametrize("change", ["removed", "different", "revoked"])
def test_cached_selection_rechecks_owner_before_dispatch(callbacks, monkeypatch, module, lane, change):
    call = module._make_call({})
    if change == "removed":
        monkeypatch.delenv(auth.APPLICATION_MODE_ENV)
    elif change == "different":
        monkeypatch.setenv(auth.APPLICATION_MODE_ENV, "different")
    else:
        callbacks.row["enabled"] = False
        callbacks.save()
    if module is risk_radar_review:
        with pytest.raises(auth.FabricProviderError):
            invoke(module, call)
    else:
        assert invoke(module, call)[0] is None
    assert not callbacks.events and not callbacks.calls


@pytest.mark.parametrize("module,lane", CASES)
def test_native_claude_override_never_relabels_other_provider_models(monkeypatch, module, lane):
    monkeypatch.delenv(auth.APPLICATION_MODE_ENV, raising=False)
    monkeypatch.delenv("MM_PROVIDER_WORKLOAD_PROFILE", raising=False)
    providers = [{"name": name, "model": name + "-model"} for name in
                 ("oauth", "anthropic", "deepseek", "codex", "ollama")]
    monkeypatch.setattr(auth, "build_providers", lambda *a, **kw: providers)
    observed = []

    def make_call(rows, *a, **kw):
        observed.append(rows)
        return "answer", None, "deepseek"

    monkeypatch.setattr(auth, "make_call", make_call)
    invoke(module, module._make_call({"model": "claude-requested-preference"}))
    rows = observed[0]
    for row in rows:
        if module is not altdata_brain and row["name"] in ("oauth", "anthropic"):
            assert row["model"] == "claude-requested-preference"
        else:
            assert row["model"] == row["name"] + "-model"
    assert all(row["model"] == row["name"] + "-model" for row in providers)


def test_real_risk_synthesis_keeps_subtract_only_caution_clamps(callbacks):
    callbacks.plans = [response(RISK_REPLY)]
    out = risk_brain.synthesize(risk_evidence(), cfg={"max_gross_tilt": 0.5})
    assert out["is_context_only"] and out["directive"]["gross_tilt"] < 0
    assert out["directive"]["posture"] == "de-gross"
    assert len(callbacks.calls) == len(callbacks.costs) == 1


def test_real_narrative_themes_and_rotation_use_three_operations_and_keep_clamps(callbacks):
    callbacks.plans = [response(THEME_REPLY), response(THEME_REPLY), response(ROTATION_REPLY)]
    out = narrative_brain.synthesize(narrative_evidence(), cfg={"max_themes": 2})
    assert len(out["assessments"]) == 2 and out["rotation"]
    assert all(row["verdict"] == "MONITOR" for row in out["assessments"])
    assert len(callbacks.calls) == len(callbacks.closed) == len(callbacks.costs) == 3
    assert len({row["request_id"] for row in callbacks.calls}) == 3


def test_narrative_partial_unknown_is_visible_without_retry(callbacks):
    callbacks.plans = [TimeoutError("first theme unknown"), response(THEME_REPLY), response(ROTATION_REPLY)]
    out = narrative_brain.synthesize(narrative_evidence(), cfg={"max_themes": 2})
    assert out["degraded_reason"] == "partial_reply"
    assert len(out["assessments"]) == 1 and out["incomplete_calls"][0]["reason"] == "fabric_effect_unknown"
    assert len(callbacks.calls) == 3 and len(callbacks.costs) == 2


def test_real_altdata_provenance_uses_execution_and_clears_before_failed_reuse(callbacks):
    state = {"as_of": "2026-11-05", "clusters": [], "n_clusters": 0}
    call = altdata_brain._make_call({"model": "claude-requested-preference"})
    callbacks.plans = [response(ALTDATA_REPLY), TimeoutError("next invocation unknown")]
    first = altdata_brain.synthesize(state, cfg={"max_clusters": 12}, call=call, root=callbacks.root)
    assert first["model"] == MODEL and first["provider"] == "fixture-provider"
    assert first["requested_model"] != MODEL and first["is_context_only"] and not first["actionable"]
    second = altdata_brain.synthesize(state, cfg={"max_clusters": 12}, call=call, root=callbacks.root)
    assert second["model"] is None and second["provider"] is None and not call._served_identity
    assert second["degraded_reason"] == "fabric_effect_unknown"
    assert len(callbacks.calls) == 2


def test_real_radar_gates_and_unknown_never_reach_calibration_apply(callbacks, monkeypatch):
    cfg = {**risk_radar_review._DEFAULTS, "enabled": True}
    monkeypatch.setattr(risk_radar_review, "_cfg", lambda: cfg)
    compare = Mock(return_value={"improves": False, "legs_ok": True})
    out = risk_radar_review.run(persist=False, root=callbacks.root, scorecard={"n_graded": 2}, compare=compare)
    assert out["degraded_reason"] == "insufficient_graded" and not callbacks.clients
    callbacks.plans = [TimeoutError("proposal unknown")]
    out = risk_radar_review.run(persist=False, root=callbacks.root, scorecard={"n_graded": 30}, compare=compare)
    assert out["degraded_reason"] == "fabric_effect_unknown" and not out["applied"]
    compare.assert_not_called()
    callbacks.plans = [response(RADAR_REPLY)]
    out = risk_radar_review.run(persist=False, root=callbacks.root, scorecard={"n_graded": 30}, compare=compare)
    assert out["degraded_reason"] == "rejected_by_do_no_harm" and not out["applied"]
    assert len(callbacks.calls) == 2 and compare.call_count == 1


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"), reason="paired gateway required")
def test_all_public_callbacks_reach_real_owner_and_paired_gateway(monkeypatch, tmp_path):
    import hashlib
    import importlib.util
    from pathlib import Path

    import yaml
    from tests.test_fabric_gateway_composition import (
        GATEWAY_BLOB, MODEL as WIRE_MODEL, configure_owned_application,
        owner_gateway, packet, status,
    )

    path = Path(os.environ["MM_FABRIC_GATEWAY_SOURCE_ROOT"]) / "ops/native_fabric/experiential_proxy/gateway.py"
    raw = path.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == GATEWAY_BLOB
    spec = importlib.util.spec_from_file_location("_cached_callback_paired_gateway", path)
    gateway = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, gateway)
    spec.loader.exec_module(gateway)
    costs = []
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda **kw: costs.append(kw))
    monkeypatch.setattr("engine.provider_health.record_attempt", lambda **kw: None)
    monkeypatch.setattr("lib.config.secret", Mock(side_effect=AssertionError("legacy credential")))
    replies = [RISK_REPLY, THEME_REPLY, THEME_REPLY, ROTATION_REPLY, ALTDATA_REPLY, RADAR_REPLY]
    plans = []
    for text in replies:
        item = packet()
        item["choices"][0]["message"]["content"] = text
        plans.append(item)
    with owner_gateway(gateway, tmp_path, plans) as (url, calls, wire, app):
        manifest_path, manifest = configure_owned_application(monkeypatch, tmp_path, url)
        manifest["capabilities"][0]["allowed_lanes"] += [lane for _, lane in CASES]
        manifest_path.write_text(yaml.safe_dump(manifest))
        monkeypatch.setattr(auth, "_repo_root", lambda: tmp_path)
        assert risk_brain.synthesize(risk_evidence(), cfg={"max_gross_tilt": 0.5})["directive"]["gross_tilt"] < 0
        assert len(narrative_brain.synthesize(narrative_evidence(), cfg={"max_themes": 2})["assessments"]) == 2
        alt = altdata_brain.synthesize({"clusters": [], "n_clusters": 0}, cfg={"max_clusters": 12}, root=tmp_path)
        assert alt["model"] == WIRE_MODEL
        monkeypatch.setattr(risk_radar_review, "_cfg", lambda: {**risk_radar_review._DEFAULTS, "enabled": True})
        radar = risk_radar_review.run(persist=False, root=tmp_path, scorecard={"n_graded": 30},
                                      compare=lambda p: {"improves": False, "legs_ok": True})
        assert radar["degraded_reason"] == "rejected_by_do_no_harm"
        snapshot = status(app)
    assert len(calls) == len(wire) == len(costs) == 6
    assert len({row["headers"]["idempotency-key"] for row in calls}) == 6
    assert all(row["model"] == WIRE_MODEL and row["provider"] == "fixture-provider" for row in costs)
    assert snapshot["pending"] == 0
