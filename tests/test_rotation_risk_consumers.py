"""Canonical risk/rotation context reaches real consumers without new authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from engine.neuralweb import rotation_risk_context as rc
from engine.neuralweb import world_state as ws

NOW = datetime(2026, 10, 8, 22, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "risk_envelope" / "rotation_context_synthetic.json"


def envelope():
    return json.loads(FIXTURE.read_text())


def write(root, path, payload):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload))


def test_canonical_context_preserves_native_values_and_clocks_without_mutation():
    native = envelope()
    before = deepcopy(native)
    out = rc.compact_context(native, now=NOW, expected_session="2026-10-06")
    assert out["usable"] is True
    for key in ("source_session", "observed_at", "produced_at", "stale_after", "bundle_id",
                "measured_state", "hazard_summary", "policy_summary", "rotation_context",
                "confluence", "market_transition", "authority"):
        assert out[key] == native[key]
    out["measured_state"]["score"] = 999
    assert native == before


@pytest.mark.parametrize("key,value,reason", [
    ("source_session", "2026-10-09", "source_session_unqualified"),
    ("observed_at", "2026-10-09T00:00:00Z", "unqualified_observed_at"),
    ("produced_at", "2026-10-09T00:00:00Z", "unqualified_produced_at"),
    ("observed_at", "2026-10-07T12:00:00", "unqualified_observed_at"),
    ("produced_at", "2026-10-07T11:00:00Z", "source_clock_order_invalid"),
    ("stale_after", "2026-10-08T21:59:59Z", "expired_or_invalid_source_clock"),
    ("data_state", "STALE", "stale_source_coverage"),
    ("rotation_context", ["bad"], "invalid_rotation_context"),
])
def test_unqualified_context_cannot_appear_current(key, value, reason):
    native = envelope(); native[key] = value
    out = rc.compact_context(native, now=NOW)
    assert out["usable"] is False and out["reason"] == reason
    assert "measured_state" not in out


def test_future_economic_session_rejected_even_with_current_build_clocks():
    native = envelope(); native["source_session"] = native["as_of"] = "2026-10-09"
    assert rc.compact_context(native, now=NOW)["reason"] == "future_source_session"


def test_new_consumer_build_cannot_refresh_old_source(tmp_path):
    write(tmp_path, "data/risk_envelope/latest.json", envelope())
    write(tmp_path, "data/market_state/latest.json", {"asof": "2026-10-07"})
    assert rc.read_context(tmp_path, now=NOW)["reason"] == "source_session_mismatch"


def test_authority_escalation_fails_closed():
    native = envelope(); native["authority"]["envelope_may_size"] = True
    assert rc.compact_context(native, now=NOW)["reason"] == "authority_contract_unqualified"


def test_context_code_changes_reach_the_running_api_through_existing_restart_owner():
    from tests.test_deploy_update_self_heal import _triggers_restart

    assert _triggers_restart("engine/neuralweb/rotation_risk_context.py")
    assert not _triggers_restart("engine/neuralweb/rotation_risk_context.py.bak")
    assert not _triggers_restart("data/risk_envelope/latest.json")


@pytest.mark.parametrize("field,reason", [("measured_state", "measured_source_session_mismatch"),
                                        ("rotation_context", "rotation_source_session_mismatch")])
def test_nested_usable_source_cannot_borrow_the_envelope_date(field, reason):
    native = envelope(); native[field].update(usable=True, as_of="2026-10-05")
    assert rc.compact_context(native, now=NOW)["reason"] == reason


def test_optional_old_input_does_not_discard_a_qualified_backdrop():
    native = envelope(); native["freshness"] = {"all_on_session": False}
    out = rc.compact_context(native, now=NOW)
    assert out["usable"] is True and out["measured_state"]["usable"] is True


def test_grounding_is_bounded_and_preserves_the_actual_prior_transition():
    context = rc.compact_context(envelope(), now=NOW)
    text = rc.render_context(context)
    assert len(text) <= 1800
    assert "2026-10-06" in text and "Mixed" in text
    assert "extra votes" in text and "ownership transfers" in text
    assert "2026-09-30" in text
    assert "capital policy is separate" in text.lower()
    assert "independence_established\":false" in text
    assert len(rc.render_context(context, lang="zh", char_budget=900)) <= 900


def test_unusable_rotation_does_not_borrow_its_native_state():
    native = envelope(); native["rotation_context"]["usable"] = False
    text = rc.render_context(rc.compact_context(native, now=NOW))
    assert "Rotation coverage unavailable" in text
    assert "Defensive groups gaining" not in text


def test_both_down_broad_proxy_strength_is_not_claimed_as_constituent_breadth():
    native = envelope(); native["rotation_context"]["state"] = "BROADENING"
    native["rotation_context"]["early_context"]["state"] = "BROADENING"
    text = rc.render_context(rc.compact_context(native, now=NOW))
    assert "proxies gaining relative strength" in text
    assert "Broader market participation" not in text
    assert "constituent breadth" in text


def test_recorded_rotation_clock_is_independent_from_confirmed_events(tmp_path):
    native = envelope()["rotation_context"]["early_context"]
    write(tmp_path, "site/marketdata/rotation_events.json", {
        "as_of": "2026-10-05", "active": [], "early_context": native,
    })
    out = ws._compose_rotation_events(tmp_path, expected_session="2026-10-06", now=NOW)
    assert out["as_of"] == "2026-10-05"
    assert out["early_context"]["as_of"] == "2026-10-06"
    assert out["n_active"] == 0
    assert "pairs" not in out["early_context"]  # receipts have one canonical owner
    stale = ws._compose_rotation_events(tmp_path, expected_session="2026-10-07", now=NOW)
    assert stale["early_context"] is None and stale["n_active"] == 0


def test_market_projection_preserves_caps_and_source_cause():
    native = {"verdict": "MIXED", "score": 51, "raw_score": 61, "asof": "2026-10-06",
              "score_source": "native-cap", "score_caps": [{"key": "credit", "cap": 51}],
              "overrides": ["native reason"], "freshness": {"stale": True}}
    out = ws._compose_verdict(native)
    assert out["score"] == 51 and out["raw_score"] == 61
    assert out["score_source"] == "native-cap"
    assert out["score_caps"] == native["score_caps"]
    assert out["freshness"] == native["freshness"]


def test_cortex_keeps_full_context_and_guest_chat_redacts_both_tool_paths(tmp_path):
    from engine.neuralweb import ask_brain, cortex
    native = {"verdict": {"verdict": "MIXED"}, "risk_envelope": envelope(),
              "rotation_events": {"as_of": "2026-10-05", "early_context": envelope()["rotation_context"]["early_context"]}}
    write(tmp_path, "data/neuralweb/world_state.json", native)
    assert cortex._tool_read_world_state(tmp_path, {}) == native
    for tool, args in (("read_world_state", {}), ("read_artifact", {"path": "data/neuralweb/world_state.json"})):
        out = ask_brain._dispatch_read_tool(tool, args, tmp_path)
        wire = json.dumps(out)
        assert "risk_envelope" not in wire and "early_context" not in wire
    assert json.loads((tmp_path / "data/neuralweb/world_state.json").read_text()) == native


def test_model_argument_cannot_authorize_direct_protected_read(tmp_path, monkeypatch):
    from engine.neuralweb import ask_brain
    def forbidden(*args, **kwargs):
        raise AssertionError("protected artifact read before authorization")
    monkeypatch.setattr(ask_brain, "_dispatch_read_tool_raw", forbidden)
    for path in ("data/risk_envelope/latest.json", "data/../data/risk_envelope/latest.json",
                 "site/riskdata/risk_envelope.json", "site/live/risk_envelope.json"):
        out = ask_brain._dispatch_read_tool("read_artifact", {"path": path, "include_risk_context": True}, tmp_path)
        assert "membership" in out["error"]


@pytest.mark.parametrize("allowed", [False, True])
def test_gateway_dispatch_uses_server_membership_for_context(tmp_path, monkeypatch, allowed):
    from engine.neuralweb import brain_gateway as gw
    write(tmp_path, "data/neuralweb/world_state.json", {"risk_envelope": envelope(), "verdict": {"verdict": "MIXED"}})
    monkeypatch.setattr(gw, "_ontology_evidence_allowed", lambda uid, root: allowed)
    out = gw._dispatch_brain_tool("read_world_state", {}, tmp_path, tmp_path, "", user_id="u")
    assert ("risk_envelope" in out) is allowed


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("allowed", [False, True])
def test_real_chat_loops_receive_same_qualified_context(stream, allowed, tmp_path, monkeypatch):
    from engine.neuralweb import brain_gateway as gw
    from tests.test_brain_gateway import _CaptureClient
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)
    monkeypatch.setattr(gw, "datetime", Frozen)
    monkeypatch.setattr(gw, "_ontology_evidence_allowed", lambda uid, root: allowed)
    monkeypatch.setattr(gw, "_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda *a, **k: True)
    write(tmp_path, "data/risk_envelope/latest.json", envelope())
    if not allowed:
        monkeypatch.setattr(rc, "read_context", lambda *a, **k: pytest.fail("guest envelope read"))
    client = _CaptureClient(answer="A sourced answer.")
    args = ("Explain rotation and market risk", "fast", [], {}, tmp_path, tmp_path,
            "", client, "deepseek-chat", 500, 1)
    if stream:
        list(gw._run_brain_loop_stream(*args, {"type": "meta"}, user_id="u"))
        calls = client.stream_kwargs
    else:
        gw._run_brain_loop(*args, user_id="u")
        calls = client.create_kwargs
    assert calls
    prompt = json.dumps(calls[0]["messages"][0]["content"], ensure_ascii=False)
    assert ("RISK AND ROTATION" in prompt) is allowed
    if allowed:
        assert "2026-10-06" in prompt and "Shared price/breadth inputs" in prompt


def test_new_product_context_stays_inside_existing_settled_evidence():
    from tests.test_risk_envelope_radar_integration import render
    from tests.test_macro_risk_dialog import _dlg, _default_visible
    native = envelope(); before = deepcopy(native)
    html = _dlg(render(native))
    assert html.count('id="gde-rotation-context"') == 1
    assert html.index('<details class="gde-disc">') < html.index('id="gde-rotation-context"')
    assert "2026-09-30" in html and "Last recorded backdrop change" in html
    assert "independent confirmation" in html and "独立确认" in html
    assert "Leadership and risk" not in _default_visible(html)
    assert native == before


def test_missing_rotation_is_not_rendered_as_no_rotation():
    from tests.test_risk_envelope_radar_integration import render
    native = envelope(); native["rotation_context"].update(usable=False, state=None)
    html = render(native)
    assert "Rotation evidence is unavailable" in html
    assert "No short-term relative shift measured" not in html


def test_portfolio_export_carries_same_context_without_recomputing(tmp_path):
    from engine.neuralweb.mastermind_context import _summarize_market
    native = rc.compact_context(envelope(), now=NOW)
    write(tmp_path, "data/neuralweb/world_state.json", {
        "verdict": {"verdict": "MIXED"}, "risk_envelope": native,
        "regime": {"asof": "2026-10-06"},
    })
    lobe, gap = _summarize_market(tmp_path)
    assert gap is None and lobe["risk_envelope"] == native
    assert "risk_score" not in lobe and "rotation_score" not in lobe


def test_real_cli_refreshes_existing_envelope_before_blackboard(tmp_path, monkeypatch):
    from scripts import build_world_state as cli, build_risk_envelope as producer
    calls = []
    def publish(*, root):
        assert root == tmp_path
        calls.append("canonical-envelope")
        write(root, "data/risk_envelope/latest.json", envelope())
    def blackboard(*, root, out_path):
        calls.append("world-state")
        assert rc.read_context(root, now=NOW)["usable"] is True
        return {"verdict": {"verdict": "MIXED"}, "gaps": []}
    monkeypatch.setattr(producer, "write", publish)
    monkeypatch.setattr(cli, "build_and_write", blackboard)
    assert cli.main(["--root", str(tmp_path)]) == 0
    assert calls == ["canonical-envelope", "world-state"]


def test_cli_refresh_failure_does_not_launder_old_source(tmp_path, monkeypatch):
    from scripts import build_world_state as cli, build_risk_envelope as producer
    write(tmp_path, "data/risk_envelope/latest.json", envelope())
    write(tmp_path, "data/market_state/latest.json", {"asof": "2026-10-07"})
    def broken(**kwargs):
        raise OSError("synthetic write failure")
    def blackboard(*, root, out_path):
        assert rc.read_context(root, now=NOW)["reason"] == "source_session_mismatch"
        return {"gaps": ["unavailable context"]}
    monkeypatch.setattr(producer, "write", broken)
    monkeypatch.setattr(cli, "build_and_write", blackboard)
    assert cli.main(["--root", str(tmp_path)]) == 0


def test_custom_output_diagnostic_never_refreshes_canonical_sources(tmp_path, monkeypatch):
    from scripts import build_world_state as cli, build_risk_envelope as producer
    monkeypatch.setattr(producer, "write", lambda **k: pytest.fail("diagnostic canonical write"))
    monkeypatch.setattr(cli, "build_and_write", lambda **k: {"gaps": []})
    assert cli.main(["--root", str(tmp_path), "--out", str(tmp_path / "preview.json")]) == 0


@pytest.mark.parametrize("target,key,value", [
    ("child", "available_at", "2026-10-09T01:00:00Z"),
    ("child", "display_only", False),
    ("parent", "produced_at", "2026-10-09T01:00:00Z"),
])
def test_alternate_rotation_summary_cannot_reopen_excluded_evidence(tmp_path, target, key, value):
    payload = {"as_of": "2026-10-06", "active": [],
               "early_context": envelope()["rotation_context"]["early_context"]}
    (payload["early_context"] if target == "child" else payload)[key] = value
    write(tmp_path, "site/marketdata/rotation_events.json", payload)
    out = ws._compose_rotation_events(tmp_path, expected_session="2026-10-06", now=NOW)
    assert out["early_context"] is None and out["n_active"] == 0
