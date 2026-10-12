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


@pytest.mark.parametrize("stamp", ["9999-12-31T23:00:00-02:00", "0001-01-01T00:00:00+02:00"])
def test_out_of_range_clock_is_unavailable_across_source_and_consumers(stamp):
    from scripts import build_risk_envelope as settled
    from scripts import build_live_risk_envelope as live

    native = envelope(); native["observed_at"] = stamp
    result = rc.compact_context(native, now=NOW)
    assert result["usable"] is False and result["reason"] == "unqualified_observed_at"
    assert settled._instant(stamp) is None
    assert settled._clock_reason({"produced_at": stamp}, "2026-10-06", "2026-10-06", NOW) == "malformed_source_clock"
    assert live._normalize_event_time(stamp, NOW) is None


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


_LIVE_NOW = datetime(2026, 10, 7, 14, 1, tzinfo=timezone.utc)
_LIVE_SESSION = "2026-10-07"
_SETTLED_SESSION = "2026-10-06"


def _live_turn_fixture(tmp_path, monkeypatch):
    """Actual composer and live builder, exclusively over this synthetic root."""
    from engine.risk_envelope import SourceRead, compose_envelope
    from scripts import build_live_risk_envelope as live
    anchor = compose_envelope(sources=[
        SourceRead(source_id="market-state-latest", role="measured_state",
                   state="RISK_ON", score=75, as_of=_SETTLED_SESSION, required=True),
        SourceRead(source_id="leadership-crack-latest", role="hazard_evidence",
                   state="HEALTHY", hazard_stage="NONE", as_of=_SETTLED_SESSION, required=True),
    ], market="US", source_session=_SETTLED_SESSION,
       observed_at="2026-10-07T12:00:00Z", produced_at="2026-10-07T12:00:00Z")
    write(tmp_path, "data/risk_envelope/latest.json", anchor)
    write(tmp_path, "data/market_state/latest.json", {"asof": _SETTLED_SESSION})
    write(tmp_path, "site/live/risk_state.json", {
        "built": "2026-10-07 14:00:00 UTC", "live_active": True,
        "live": {"verdict": "RISK_OFF", "score": 40, "raw_score": 40,
                 "radar": {"state": "warning"}, "source_event_time": "2026-10-07T13:59:50Z"},
    })
    write(tmp_path, "data/leadership_crack/latest.json", {"asof": _SETTLED_SESSION, "state": "BROKEN"})
    write(tmp_path, "site/marketdata/rotation_events.json", {
        "schema": "rotation_events.v1", "as_of": _LIVE_SESSION, "active": [],
        "generated_utc": "2026-10-07 14:00 UTC",
        "early_context": {"schema": "rotation_early_context/v1", "definition_id": "synthetic-only",
                          "as_of": _LIVE_SESSION, "display_only": True,
                          "state": "DEFENSIVE_RELATIVE_STRENGTH", "pairs": [], "coverage": {},
                          "availability": {"status": "UNKNOWN", "available_at": None}},
    })
    monkeypatch.setattr(live, "_risk_envelope_cfg", lambda: {"debounce_ticks": 3, "stale_after_min": 5.0})
    monkeypatch.setattr(live, "_emit_materiality_firing", lambda **kw: pytest.fail("synthetic reader fixture fired"))
    current = live.build(tmp_path, now=_LIVE_NOW, produced_now=_LIVE_NOW)
    write(tmp_path, "site/live/risk_envelope.json", current)
    return anchor, current


def _set_live_field(payload, path, value):
    node = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def test_real_live_projection_prefers_risk_and_dwell_without_promoting_unknown_rotation(tmp_path, monkeypatch):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    before = deepcopy(current)
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["usable"] is True and result["selection"]["plane"] == "live"
    assert result["source_session"] == _LIVE_SESSION
    assert result["selection"]["settled_bundle_id"] == anchor["bundle_id"]
    assert result["measured_state"]["verdict"] == "RISK_OFF"
    assert result["live_transition"]["stable_stage"] == "NONE"
    assert result["live_transition"]["candidate_stage"] == "FRAGILE"
    assert result["live_transition"]["pending"] == {"stage": "FRAGILE", "ticks": 1, "needs": 3}
    assert result["rotation_at_turn"] == {"current_at_turn": False, "reason": "original_availability_unknown",
                                         "availability": "UNKNOWN", "expiry": "UNKNOWN",
                                         "independent_evidence_vote": False}
    for key in ("bundle_id", "measured_state", "hazard_summary", "policy_summary", "rotation_context",
                "confluence", "authority", "live_transition", "clocks"):
        assert result[key] == current[key]
    for lang in ("en", "zh"):
        text = rc.render_context(result, lang=lang)
        assert len(text) <= 1800 and "NONE" in text and "FRAGILE" in text and "1/3" in text
        assert "UNKNOWN" in text
    text = rc.render_context(result)
    assert "Live provisional; settled anchor 2026-10-06" in text
    assert "Hazard stage: accepted NONE; candidate FRAGILE; pending FRAGILE 1/3." in text
    assert "This rotation child is not qualified as current evidence." in text
    assert "Defensive groups gaining relative strength" not in text
    assert current == before
    result["live_transition"]["pending"]["ticks"] = 99
    assert current == before


@pytest.mark.parametrize("path,value,reason", [
    (("live_active",), 1, "live_owner_not_active"),
    (("precedence",), "settled", "live_owner_not_active"),
    (("revision",), "corrected", "live_revision_unqualified"),
    (("overlays", "settled_bundle_id"), "different", "settled_anchor_mismatch"),
    (("overlays", "settled_source_session"), "2026-10-03", "settled_anchor_mismatch"),
    (("observed_at",), "2026-10-07T14:01:01Z", "unqualified_observed_at"),
    (("produced_at",), "2026-10-07T14:00:59Z", "source_clock_order_invalid"),
    (("stale_after",), "2026-10-07T14:01:00Z", "expired_or_invalid_source_clock"),
    (("clocks", "observed_at"), None, "live_clock_alias_mismatch"),
    (("clocks", "upstream_built"), "2026-10-07T14:03:01Z", "upstream_clock_future"),
    (("clocks", "upstream_built"), "9999-12-31T23:00:00-02:00", "upstream_clock_unqualified"),
    (("clocks", "event_time"), "2026-10-07T14:03:01Z", "source_event_clock_unqualified"),
    (("live_transition", "session"), "2026-10-06", "live_transition_unqualified"),
    (("live_transition", "stable_stage"), "ARMED", "live_transition_unqualified"),
    (("live_transition", "candidate_stage"), "NONE", "live_candidate_mismatch"),
    (("live_transition", "pending"), {"stage": "FRAGILE", "ticks": True, "needs": 3}, "live_pending_unqualified"),
    (("live_transition", "last_observed_built"), "2026-10-07 14:03:01 UTC", "live_observation_unqualified"),
])
def test_live_reader_rejects_invalid_owner_receipts_and_uses_actual_settled(tmp_path, monkeypatch, path, value, reason):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    _set_live_field(current, path, value)
    write(tmp_path, "site/live/risk_envelope.json", current)
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["usable"] is True and result["selection"] == {"plane": "settled", "live_reason": reason}
    assert result["bundle_id"] == anchor["bundle_id"]
    assert result["measured_state"]["verdict"] == "RISK_ON"


@pytest.mark.parametrize("ttl", [True, False, None, "5", 0, -1, float("nan"), float("inf"), 1e308, 1e12])
def test_live_reader_rejects_invalid_or_unrepresentable_ttl(tmp_path, monkeypatch, ttl):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    current["stale_after_min"] = ttl
    assert rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)["reason"] == "live_ttl_unqualified"


def test_live_ttl_uses_upstream_clock_with_inclusive_owner_boundary(tmp_path, monkeypatch):
    from datetime import timedelta
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    boundary = datetime(2026, 10, 7, 14, 5, tzinfo=timezone.utc)
    out = rc.qualify_live_context(current, settled=anchor, now=boundary)
    assert out["usable"] is True
    assert out["selection"]["fresh_through"] == "2026-10-07T14:05:00+00:00"
    assert out["selection"]["ttl_boundary"] == "inclusive"
    later = boundary + timedelta(microseconds=1)
    assert rc.qualify_live_context(current, settled=anchor, now=later)["reason"] == "upstream_clock_expired"
    # Re-publication changes neither the upstream observation nor its deadline.
    current["observed_at"] = current["produced_at"] = later.isoformat()
    current["clocks"]["observed_at"] = current["clocks"]["produced_at"] = later.isoformat()
    current["built"] = "2026-10-07 14:05:00 UTC"
    assert rc.qualify_live_context(current, settled=anchor, now=later)["reason"] == "upstream_clock_expired"
    # The upstream carrying-clock tolerance is the producer's existing 120s,
    # independent from strict child availability and outer publication clocks.
    current["observed_at"] = current["produced_at"] = _LIVE_NOW.isoformat()
    current["clocks"]["observed_at"] = current["clocks"]["produced_at"] = _LIVE_NOW.isoformat()
    current["clocks"]["upstream_built"] = "2026-10-07T14:03:00Z"
    assert rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)["usable"] is True


@pytest.mark.parametrize("session", ["2026-10-06", "2026-10-05"])
def test_live_not_ahead_of_settled_cannot_win(tmp_path, monkeypatch, session):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    current["source_session"] = current["as_of"] = session
    current["measured_state"]["as_of"] = session
    current["rotation_context"]["as_of"] = session
    current["live_transition"]["session"] = session
    assert rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)["reason"] == "live_not_ahead_of_settled"


def test_live_reader_checks_the_anchor_actually_read_and_keeps_settled_default(tmp_path, monkeypatch):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    settled = rc.read_context(tmp_path, now=_LIVE_NOW)
    assert settled["bundle_id"] == anchor["bundle_id"] and settled["source_session"] == _SETTLED_SESSION
    assert settled["derived_from"] == "risk-envelope-settled" and "selection" not in settled
    assert rc.read_context(tmp_path, now=_LIVE_NOW, expected_session=_SETTLED_SESSION) == settled
    # A separately published settled generation invalidates an older overlay.
    anchor["bundle_id"] = "new-settled-generation"
    write(tmp_path, "data/risk_envelope/latest.json", anchor)
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["bundle_id"] == "new-settled-generation"
    assert result["selection"] == {"plane": "settled", "live_reason": "settled_anchor_mismatch"}
    # A market-session mismatch makes even a matching overlay unavailable.
    current["overlays"]["settled_bundle_id"] = anchor["bundle_id"]
    write(tmp_path, "site/live/risk_envelope.json", current)
    write(tmp_path, "data/market_state/latest.json", {"asof": _LIVE_SESSION})
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["usable"] is False and result["selection"]["plane"] == "unavailable"
    assert result["selection"]["live_reason"] == "settled_anchor_unqualified"


@pytest.mark.parametrize("raw", [None, "{", "[]"])
def test_missing_or_malformed_live_artifact_falls_back_without_inventing_context(tmp_path, monkeypatch, raw):
    anchor, _ = _live_turn_fixture(tmp_path, monkeypatch)
    path = tmp_path / "site/live/risk_envelope.json"
    if raw is None:
        path.unlink()
    else:
        path.write_text(raw)
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["usable"] is True and result["bundle_id"] == anchor["bundle_id"]
    assert result["selection"]["plane"] == "settled"
    (tmp_path / "data/risk_envelope/latest.json").unlink()
    unavailable = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert unavailable["usable"] is False and unavailable["selection"]["plane"] == "unavailable"
    assert "absence is not evidence of calm" in rc.render_context(unavailable)


def _recorded_child_clocks(current):
    early = current["rotation_context"]["early_context"]
    early.update(available_at="2026-10-07T14:00:00Z",
                 availability={"status": "RECORDED", "available_at": "2026-10-07T14:00:00Z"},
                 stale_after="2026-10-07T14:04:00Z")
    return early


def test_original_child_clock_positive_control_preserves_state_and_no_extra_vote(tmp_path, monkeypatch):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    _recorded_child_clocks(current)
    before = deepcopy(current)
    result = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    assert result["rotation_at_turn"] == {"current_at_turn": True, "reason": None,
                                         "availability": "RECORDED", "expiry": "UNEXPIRED",
                                         "independent_evidence_vote": False}
    assert "Defensive groups gaining relative strength" in rc.render_context(result)
    for key in ("bundle_id", "rotation_context", "confluence", "measured_state", "hazard_summary", "authority"):
        assert result[key] == before[key]
    assert current == before


@pytest.mark.parametrize("target", ["child", "parent"])
@pytest.mark.parametrize("path,value,reason", [
    (("produced_at",), "2026-10-07T14:01:01Z", "future_production_clock"),
    (("generated_utc",), "2026-10-07 14:02 UTC", "future_production_clock"),
    (("available_at",), "2026-10-07T14:01:01Z", "source_not_available"),
    (("availability", "available_at"), "2026-10-07T14:01:01Z", "source_not_available"),
    (("stale_after",), "2026-10-07T14:01:00Z", "source_expired"),
    (("produced_at",), "9999-12-31T23:00:00-02:00", "malformed_source_clock"),
    (("stale_after",), "2026-10-07T14:04:00", "malformed_source_expiry"),
    (("freshness",), {"stale": True}, "source_stale"),
    (("freshness",), {"stale": "false"}, "malformed_freshness"),
])
def test_all_original_child_and_parent_clock_aliases_constrain_live_rotation(
        tmp_path, monkeypatch, target, path, value, reason):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    early = _recorded_child_clocks(current)
    receipt = early if target == "child" else current["rotation_context"]["source_clock_receipt"]
    receipt.setdefault("availability", {"status": "RECORDED", "available_at": "2026-10-07T14:00:00Z"})
    _set_live_field(receipt, path, value)
    before = deepcopy(current)
    result = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    assert result["usable"] is True and result["selection"]["plane"] == "live"
    assert result["rotation_at_turn"]["current_at_turn"] is False
    assert result["rotation_at_turn"]["reason"] == reason
    assert result["rotation_at_turn"]["independent_evidence_vote"] is False
    if reason == "source_expired":
        assert result["rotation_at_turn"]["expiry"] == "EXPIRED"
    assert "Defensive groups gaining relative strength" not in rc.render_context(result)
    assert current == before and result["rotation_context"] == current["rotation_context"]


@pytest.mark.parametrize("unknown", ["availability", "expiry"])
def test_parent_or_wrapper_receipt_cannot_supply_missing_original_child_clock(tmp_path, monkeypatch, unknown):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    early = _recorded_child_clocks(current)
    current["rotation_context"]["source_clock_receipt"].update(
        available_at="2026-10-07T14:00:00Z", stale_after="2026-10-07T14:10:00Z")
    if unknown == "availability":
        early.pop("available_at")
        early["availability"] = {"status": "UNKNOWN", "available_at": None}
        early["produced_at"] = "2026-10-07T14:00:00Z"
        early["generated_utc"] = "2026-10-07 14:00 UTC"
    else:
        early.pop("stale_after")
    result = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    timing = result["rotation_at_turn"]
    assert timing[unknown] == "UNKNOWN" and timing["current_at_turn"] is False
    assert timing["reason"] == ("original_availability_unknown" if unknown == "availability"
                                else "source_expiry_unknown")
    assert "UNKNOWN" in rc.render_context(result)


def test_repeated_read_cannot_tick_or_recompose_and_frozen_pending_can_differ(tmp_path, monkeypatch):
    from scripts import build_live_risk_envelope as live
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    # The actual producer freezes pending on the repeated upstream observation,
    # while carrying this read's changed candidate. The reader must not "repair" it.
    write(tmp_path, "data/leadership_crack/latest.json", {"asof": _SETTLED_SESSION, "state": "INTACT"})
    write(tmp_path, "site/live/risk_state.json", {
        "built": "2026-10-07 14:00:00 UTC", "live_active": True,
        "live": {"verdict": "RISK_OFF", "score": 40, "radar": {"state": "quiet"}},
    })
    current = live.build(tmp_path, now=_LIVE_NOW, produced_now=_LIVE_NOW)
    write(tmp_path, "site/live/risk_envelope.json", current)
    assert current["live_transition"]["candidate_stage"] == "NONE"
    assert current["live_transition"]["pending"]["stage"] == "FRAGILE"
    before = (tmp_path / "site/live/risk_envelope.json").read_bytes()
    for name in ("build", "_advance_transition", "_emit_materiality_firing", "compose_envelope"):
        monkeypatch.setattr(live, name, lambda *a, **k: pytest.fail("reader invoked live producer effects"))
    first = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    second = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert first == second and first["usable"] is True
    assert first["live_transition"] == current["live_transition"]
    assert "accepted NONE; candidate NONE; pending FRAGILE 1/3" in rc.render_context(first)
    assert (tmp_path / "site/live/risk_envelope.json").read_bytes() == before
    # An explicitly unavailable candidate does not become a calm stage.
    current["hazard_summary"]["stage"] = None
    current["live_transition"]["candidate_stage"] = None
    result = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    assert result["usable"] is True
    assert "accepted NONE; candidate unavailable; pending FRAGILE 1/3" in rc.render_context(result)


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("allowed", [False, True])
def test_real_chat_loops_receive_qualified_live_context_at_one_frozen_turn_clock(
        stream, allowed, tmp_path, monkeypatch):
    from engine.neuralweb import brain_gateway as gw
    from tests.test_brain_gateway import _CaptureClient
    _live_turn_fixture(tmp_path, monkeypatch)

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return _LIVE_NOW if tz is not None else _LIVE_NOW.replace(tzinfo=None)

    monkeypatch.setattr(gw, "datetime", Frozen)
    monkeypatch.setattr(gw, "_ontology_evidence_allowed", lambda uid, root: allowed)
    monkeypatch.setattr(gw, "_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda *a, **k: True)
    calls_at = []
    original = rc.read_preferred_context

    def tracked(root, *, now):
        assert allowed, "unentitled envelope read"
        calls_at.append(now)
        return original(root, now=now)

    monkeypatch.setattr(rc, "read_preferred_context", tracked)
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
    assert calls_at == ([_LIVE_NOW] if allowed else [])
    if allowed:
        assert "Live provisional; settled anchor 2026-10-06" in prompt
        assert "Risk-off" in prompt and "accepted NONE; candidate FRAGILE; pending FRAGILE 1/3" in prompt
        assert "UNKNOWN" in prompt and "not qualified as current evidence" in prompt


@pytest.mark.parametrize("case", [
    "future_event_within_skew",
    "future_top_availability", "future_nested_availability", "malformed_availability",
    "older_live_session", "weekend_live_session",
    "old_upstream_session",
])
def test_live_clock_aliases_and_session_cannot_borrow_wrapper_freshness(tmp_path, monkeypatch, case):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    now = _LIVE_NOW
    expected = "source_event_clock_unqualified"
    if case == "future_event_within_skew":
        current["clocks"]["upstream_built"] = "2026-10-07T14:03:00Z"
        current["clocks"]["event_time"] = "2026-10-07T14:01:01Z"
    elif case in ("future_top_availability", "future_nested_availability", "malformed_availability"):
        target = current["clocks"] if case == "future_nested_availability" else current
        target["available_at"] = ({"bad": "clock"} if case == "malformed_availability"
                                  else "2026-10-07T14:01:01Z")
        expected = "live_availability_unqualified"
    elif case == "old_upstream_session":
        current["clocks"]["upstream_built"] = "2026-10-06T14:00:00Z"
        current["clocks"]["event_time"] = None
        current["stale_after_min"] = 3000.0
        expected = "live_session_unqualified"
    else:
        anchor["source_session"] = anchor["as_of"] = "2026-10-05" if case == "older_live_session" else "2026-10-08"
        anchor["measured_state"]["as_of"] = anchor["source_session"]
        current["overlays"]["settled_source_session"] = anchor["source_session"]
        session = "2026-10-06" if case == "older_live_session" else "2026-10-09"
        current["source_session"] = current["as_of"] = session
        current["measured_state"]["as_of"] = session
        current["rotation_context"]["as_of"] = current["rotation_context"]["early_context"]["as_of"] = session
        current["live_transition"]["session"] = session
        if case == "weekend_live_session":
            now = datetime(2026, 10, 10, 14, 1, tzinfo=timezone.utc)
            current["observed_at"] = current["produced_at"] = now.isoformat()
            current["clocks"]["observed_at"] = current["clocks"]["produced_at"] = now.isoformat()
            current["clocks"]["upstream_built"] = "2026-10-10T14:00:00Z"
        expected = "live_session_unqualified"
    before = deepcopy(current)
    out = rc.qualify_live_context(current, settled=anchor, now=now)
    assert out["usable"] is False and out["reason"] == expected
    assert current == before


@pytest.mark.parametrize("path,value,reason", [
    (("live_transition", "stable_stage"), [], "live_transition_unqualified"),
    (("live_transition", "candidate_stage"), {}, "live_transition_unqualified"),
    (("live_transition", "pending", "stage"), [], "live_pending_unqualified"),
    (("live_transition", "pending", "ticks"), "1", "live_pending_unqualified"),
])
def test_malformed_optional_live_state_returns_settled_instead_of_aborting(tmp_path, monkeypatch, path, value, reason):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    _set_live_field(current, path, value)
    write(tmp_path, "site/live/risk_envelope.json", current)
    result = rc.read_preferred_context(tmp_path, now=_LIVE_NOW)
    assert result["bundle_id"] == anchor["bundle_id"] and result["selection"] == {
        "plane": "settled", "live_reason": reason}


@pytest.mark.parametrize("available_at", ["2026-10-07T14:00:59Z", "2026-10-07T14:01:00Z"])
def test_original_live_availability_may_precede_wrapper_republication_without_new_child_time(
        tmp_path, monkeypatch, available_at):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    current["available_at"] = current["clocks"]["available_at"] = available_at
    out = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    assert out["usable"] is True and out["available_at"] == available_at
    assert out["rotation_at_turn"]["availability"] == "UNKNOWN"
    assert out["rotation_at_turn"]["current_at_turn"] is False


def test_actual_live_owner_current_et_session_survives_utc_midnight(tmp_path, monkeypatch):
    from scripts import build_live_risk_envelope as live
    _live_turn_fixture(tmp_path, monkeypatch)
    now = datetime(2026, 10, 8, 0, 30, tzinfo=timezone.utc)  # still Oct 7 ET
    write(tmp_path, "site/live/risk_state.json", {
        "built": "2026-10-08 00:29:00 UTC", "live_active": True,
        "live": {"verdict": "RISK_OFF", "score": 40, "radar": {"state": "warning"},
                 "source_event_time": "2026-10-08T00:28:59Z"},
    })
    current = live.build(tmp_path, now=now, produced_now=now)
    write(tmp_path, "site/live/risk_envelope.json", current)
    out = rc.read_preferred_context(tmp_path, now=now)
    assert current["source_session"] == _LIVE_SESSION
    assert out["usable"] is True and out["selection"]["plane"] == "live"


@pytest.mark.parametrize("event,carrying,observed", [
    ("2026-10-07T14:00:00.750Z", "2026-10-07T14:00:00Z", "2026-10-07T14:01:00Z"),
    ("2026-10-07T14:00:45Z", "2026-10-07T14:01:00Z", "2026-10-07T14:00:30Z"),
])
def test_nonfuture_event_retains_native_precision_without_invented_cross_clock_order(
        tmp_path, monkeypatch, event, carrying, observed):
    anchor, current = _live_turn_fixture(tmp_path, monkeypatch)
    current["observed_at"] = current["produced_at"] = observed
    current["clocks"]["observed_at"] = current["clocks"]["produced_at"] = observed
    current["clocks"]["upstream_built"] = carrying
    current["clocks"]["event_time"] = event
    out = rc.qualify_live_context(current, settled=anchor, now=_LIVE_NOW)
    assert out["usable"] is True and out["clocks"] == current["clocks"]
    assert out["rotation_at_turn"]["current_at_turn"] is False
