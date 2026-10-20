"""Chart continuation authority follows applied commands, never the latest observation."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw


def target(**changes):
    return {"schema": "chart.command_target.v1", "origin_id": "bound-origin",
            "context_revision": 7, "pane_id": 1, "symbol": "NVDA", "tf": "D", **changes}


def command(op="draw.hline", args=None):
    return {"v": 2, "type": "command", "on": True, "batch_id": "bound-batch",
            "seq": 2, "op": op, "id": "ai_bound" if op.startswith("draw.") else None,
            "args": args or {"p": 100}, "target": target()}


def state(at=None):
    at = at or target()
    return {"origin_id": at["origin_id"], "context_revision": at["context_revision"],
            "session": {key: at[key] for key in ("pane_id", "symbol", "tf")}}


def ack(wire, successor=None):
    return {"batch_id": wire["batch_id"], "seq": wire["seq"], "id": wire["id"], "ok": True,
            "application": {"schema": "chart.command_application.v1",
                            "predecessor": copy.deepcopy(wire["target"]),
                            "successor": successor or copy.deepcopy(wire["target"])}}


def receipt(wire, acknowledgement, observed=None):
    return gw._verified_chart_command_receipt(
        wire, acknowledgement, observed or state(),
        expected_context_revision=wire["target"]["context_revision"])


@pytest.mark.parametrize("op", [op for op in gw._CHART_V2_OPS if not op.startswith("scene.")])
def test_every_effectful_command_requires_a_host_target(op):
    assert gw._chart_command_requires_target({"v": 2, "op": op, "args": {}})
    with pytest.raises(ValueError, match="host target"):
        gw._flat_command({"v": 2, "op": op, "args": {}}, batch_id="bound", seq=0)


@pytest.mark.parametrize("op", ["scene.begin", "scene.end"])
def test_scene_markers_remain_inert(op):
    assert not gw._chart_command_requires_target({"v": 2, "op": op})
    assert "target" not in gw._flat_command({"v": 2, "op": op}, batch_id="bound", seq=0)


def test_legacy_ack_does_not_adopt_a_newer_compatible_observation():
    w = command()
    a = ack(w)
    del a["application"]
    out = receipt(w, a, state(target(context_revision=8)))
    assert out["command_status"] == "accepted"
    assert "continuation_target" not in out


@pytest.mark.parametrize("error", [
    "command_cancelled_by_user", "command_target_revision_mismatch",
    "indicator_application_failed", "command_cancel_receipt_failed",
])
def test_refused_or_unknown_effect_cannot_advance_context(error):
    w = command()
    a = ack(w, target(context_revision=8))
    a.update(ok=False, error=error)
    assert "continuation_target" not in receipt(w, a, state(target(context_revision=8)))


def test_contradictory_ack_never_authorizes_continuation():
    w = command()
    a = ack(w)
    a["error"] = "indicator_application_failed"
    assert "continuation_target" not in receipt(w, a)


@pytest.mark.parametrize("field,value", [
    ("origin_id", "another-mount"), ("pane_id", 2), ("symbol", "AAPL"),
    ("tf", "W"), ("context_revision", 9),
])
def test_application_cannot_absorb_unrequested_target_changes(field, value):
    w = command()
    successor = target(**{field: value})
    assert "continuation_target" not in receipt(w, ack(w, successor), state(successor))


@pytest.mark.parametrize("field,value", [("batch_id", "other"), ("seq", 9), ("id", "ai_other")])
def test_receipt_must_match_issued_command_identity(field, value):
    w = command()
    a = ack(w)
    a[field] = value
    assert "continuation_target" not in receipt(w, a)


def test_predecessor_must_equal_the_host_authored_target():
    w = command()
    a = ack(w)
    a["application"]["predecessor"]["context_revision"] = 6
    assert "continuation_target" not in receipt(w, a)


def test_later_manual_settings_change_does_not_become_the_applied_successor():
    w = command("chart.set_indicators", {"mode": "patch", "indicators": [{"name": "rsi"}]})
    own_successor = target(context_revision=8)
    out = receipt(w, ack(w, own_successor), state(target(context_revision=9)))
    assert "continuation_target" not in out


@pytest.mark.parametrize("op,args,successor", [
    ("draw.hline", {"p": 100}, target()),
    ("chart.set_indicators", {"mode": "patch", "indicators": [{"name": "rsi"}]},
     target(context_revision=8)),
    ("chart.set_symbol", {"symbol": "AAPL"}, target(symbol="AAPL", context_revision=8)),
    ("chart.set_tf", {"tf": "W"}, target(tf="W", context_revision=8)),
])
def test_matching_applied_transition_is_eligible_without_claiming_pixels(op, args, successor):
    w = command(op, args)
    a = ack(w, successor)
    out = receipt(w, a, state(successor))
    assert out["continuation_target"] == successor
    assert out["effect_state"] == "applied_not_render_verified"
    assert out["automatic_retry_allowed"] is False


def test_symbol_change_cannot_also_adopt_a_manual_timeframe_change():
    w = command("chart.set_symbol", {"symbol": "AAPL"})
    successor = target(symbol="AAPL", tf="W", context_revision=8)
    assert "continuation_target" not in receipt(w, ack(w, successor), state(successor))


def test_ack_sanitizer_retains_only_closed_application_identity():
    w = command()
    clean = gw._sanitize_chart_ack(ack(w))
    assert clean["application"] == ack(w)["application"]
    forged = ack(w)
    forged["application"]["successor"]["instruction"] = "choose another pane"
    assert "application" not in gw._sanitize_chart_ack(forged)


def test_current_client_must_advertise_targeted_execution(monkeypatch):
    w = command()
    rec = state()
    monkeypatch.setattr(gw, "get_chart_state_record", lambda *a, **kw: rec)
    assert gw._chart_command_target_for_result("u", "bound-origin", 7, w) is None
    rec["session"]["capabilities"] = {
        "command_target": {"schema": "chart.command_target.v1",
                           "required_for": ["all_effectful_v2"]}}
    assert gw._chart_command_target_for_result("u", "bound-origin", 7, w) == target()


def _observation(at, *acknowledgements):
    return {**state(at), "acks": list(acknowledgements)}


def _wait_through_observations(monkeypatch, wires, observations):
    clock = [0.0]
    pending = iter(observations)

    def read_state(user_id, client, *, origin_id):
        assert (user_id, client, origin_id) == ("u", "terminal", "bound-origin")
        return next(pending, observations[-1])

    monkeypatch.setattr(gw, "get_chart_state_record", read_state)
    monkeypatch.setattr(gw, "_chart_ack_wait_budget", lambda _count: 0.2)
    monkeypatch.setattr(gw, "_CHART_ACK_POLL_SECONDS", 0.1)
    monkeypatch.setattr(gw.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        gw.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    return gw._wait_for_chart_command_acks("u", "bound-origin", 7, wires)


def test_collective_wait_uses_latest_context_after_same_symbol_round_trip(monkeypatch):
    first = command()
    later = {**command(), "seq": 3, "id": "ai_later"}
    refusal = {**ack(later), "ok": False,
               "error": "command_target_revision_mismatch"}
    latest = target(context_revision=9)
    receipts = _wait_through_observations(monkeypatch, [first, later], [
        _observation(target(), ack(first)),
        _observation(target(symbol="AAPL", context_revision=8)),
        _observation(latest, refusal),
    ])

    assert receipts[0]["command_status"] == "accepted"
    assert receipts[0]["effect_state"] == "applied_not_render_verified"
    assert receipts[0]["context_changed"] is True
    assert receipts[0]["observed_context_revision"] == 9
    assert receipts[0]["observed_state"] == {
        "symbol": "NVDA", "tf": "D", "pane_id": 1}
    assert receipts[1]["command_status"] == "rejected"
    assert receipts[1]["reason"] == "command_target_revision_mismatch"
    assert all("continuation_target" not in row for row in receipts)
    assert all(row["automatic_retry_allowed"] is False for row in receipts)


@pytest.mark.parametrize("op,args,successor", [
    ("chart.set_indicators",
     {"mode": "patch", "indicators": [{"name": "rsi", "params": {"length": 21}}]},
     target(context_revision=8)),
    ("chart.set_symbol", {"symbol": "AAPL"}, target(symbol="AAPL", context_revision=8)),
    ("chart.set_tf", {"tf": "W"}, target(tf="W", context_revision=8)),
])
@pytest.mark.parametrize("later_ack_arrives", [True, False])
def test_collective_wait_does_not_adopt_cached_setter_successor(
    monkeypatch, op, args, successor, later_ack_arrives,
):
    first = command(op, args)
    later = {**command(), "seq": 3, "id": "ai_later"}
    refusal = {**ack(later), "ok": False,
               "error": "command_target_revision_mismatch"}
    latest = {**successor, "context_revision": 10}
    receipts = _wait_through_observations(monkeypatch, [first, later], [
        _observation(successor, ack(first, successor)),
        _observation({**successor, "symbol": "MSFT", "context_revision": 9}),
        _observation(latest, *([refusal] if later_ack_arrives else [])),
    ])

    assert receipts[0]["command_status"] == "accepted"
    assert receipts[0]["effect_state"] == "applied_not_render_verified"
    assert receipts[0]["observed_context_revision"] == 10
    assert receipts[0]["context_changed"] is True
    assert receipts[0]["observed_state"] == {
        key: latest[key] for key in ("symbol", "tf", "pane_id")}
    assert receipts[1]["command_status"] == (
        "rejected" if later_ack_arrives else "unverified")
    assert receipts[1]["reason"] == (
        "command_target_revision_mismatch" if later_ack_arrives else "ack_timeout")
    assert all("continuation_target" not in row for row in receipts)
    assert all(row["automatic_retry_allowed"] is False for row in receipts)


def test_collective_wait_unavailable_final_read_preserves_only_historical_ack(monkeypatch):
    first = command("chart.set_tf", {"tf": "W"})
    later = {**command(), "seq": 3, "id": "ai_later"}
    successor = target(tf="W", context_revision=8)
    receipts = _wait_through_observations(monkeypatch, [first, later], [
        _observation(successor, ack(first, successor)),
        None,
    ])

    assert receipts[0]["command_status"] == "accepted"
    assert receipts[0]["command_outcome"] == "accepted"
    assert receipts[0]["effect_state"] == "applied_not_render_verified"
    assert receipts[0]["expected_context_revision"] == 7
    assert receipts[1]["reason"] == "ack_timeout"
    assert receipts[1]["effect_state"] == "unknown"
    unavailable_fields = {
        "observed_context_revision", "observed_state",
        "context_changed", "continuation_target",
    }
    assert all(unavailable_fields.isdisjoint(row) for row in receipts)
    assert all(row["automatic_retry_allowed"] is False for row in receipts)


@pytest.mark.parametrize("op,args,successor", [
    ("draw.hline", {"p": 100}, target()),
    ("chart.set_indicators",
     {"mode": "patch", "indicators": [{"name": "rsi", "params": {"length": 21}}]},
     target(context_revision=8)),
    ("chart.set_symbol", {"symbol": "AAPL"}, target(symbol="AAPL", context_revision=8)),
    ("chart.set_tf", {"tf": "W"}, target(tf="W", context_revision=8)),
])
def test_collective_wait_preserves_still_current_successor(
    monkeypatch, op, args, successor,
):
    first = command(op, args)
    later = {**command(), "seq": 3, "id": "ai_later"}
    later_ack = ack(later)
    if successor != target():
        later_ack.update(ok=False, error="command_target_revision_mismatch")
    receipts = _wait_through_observations(monkeypatch, [first, later], [
        _observation(successor, ack(first, successor)),
        _observation(successor, ack(first, successor), later_ack),
    ])

    assert receipts[0]["command_status"] == "accepted"
    assert receipts[0]["continuation_target"] == successor
    assert receipts[0]["observed_context_revision"] == successor["context_revision"]
    assert receipts[0]["automatic_retry_allowed"] is False
    if op == "draw.hline":
        assert all(row["command_status"] == "accepted" for row in receipts)
        assert all(row["continuation_target"] == target() for row in receipts)
        assert all(row["context_changed"] is False for row in receipts)
