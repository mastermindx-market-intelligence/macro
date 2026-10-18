"""Drawing-plan transport and capability admission, with a scripted model.

The native manifest fixture is exported from Terminal's
lib/chartDrawingTools.ts describeAiDrawingCapabilities(); it is a receiver
contract specimen, never a second runtime tool catalog. Protocol tests do not
attest rendered pixels, real-model composition quality, or technical validity.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw


MANIFEST = json.loads((Path(__file__).parent / "fixtures/chart_native_drawing_tools_v1.json").read_text())
T0 = 1721606400
USER = "chart-plan-user"


def point(index=0):
    return {"t": T0 + index * 86400, "p": 100 + index * 5}


def native(kind, identity="ai_native"):
    contract = next(row for row in MANIFEST["tools"] if row["kind"] == kind)
    args = {"kind": kind, "points": [point(i) for i in range(contract["min_points"])]}
    if contract["text"] == "required":
        args["text"] = "Prior swing; confirm at the marked boundary"
    return {"op": "draw.tool", "id": identity, "args": args}


def composition(prefix="a"):
    return [native(kind, f"ai_{prefix}_{index}") for index, kind in
            enumerate(("channel", "fibtrend", "pricerange", "callout"))]


@pytest.fixture
def chart(tmp_path, monkeypatch):
    origin = "plan-" + uuid4().hex[:16]
    session = {
        "symbol": "NVDA", "tf": "D", "pane_id": 1,
        "indicators": [{"name": "rsi", "params": {"period": 21}}, {"name": "ema"}],
        "indicator_visibility": {"schema": "chart.indicator_visibility.v1", "hidden": ["rsi"]},
        "drawings": [],
        "capabilities": {
            "command_target": {"schema": "chart.command_target.v1", "required_for": ["all_effectful_v2"]},
            "indicator_edit": {"op": "chart.set_indicators", "modes": ["replace", "patch"], "visibility": ["show", "hide"]},
            "drawing_plan": {"schema": "chart.drawing_plan.v1", "operations": "draw_only",
                             "max_commands": 24, "max_objects": 60, "atomic": False},
            "drawing_tools": copy.deepcopy(MANIFEST),
        },
    }
    gw.put_chart_state(USER, "terminal", session, origin_id=origin, context_revision=7)
    root = tmp_path / "root"
    (root / "data/neuralweb/cortex").mkdir(parents=True)
    (root / "data/neuralweb/world_state.json").write_text(json.dumps({"verdict": "RISK_OFF", "regime": "Q1", "score": 34}))
    (root / "data/neuralweb/cortex/memo.json").write_text(json.dumps({"summary": "Test context.", "what_fired": []}))
    monkeypatch.setattr("lib.ai_costs._write_ledger_path", lambda root=None: tmp_path / "usage.jsonl")
    monkeypatch.setattr("lib.ai_costs.record_usage", lambda *a, **kw: True)
    monkeypatch.setattr(gw, "_brain_quota_dir", lambda *a, **kw: tmp_path)
    monkeypatch.setattr(gw, "_resolve_tier", lambda *a, **kw: {"tier": "pro", "status": "active", "current_period_end": None})
    monkeypatch.setattr(gw, "_ensure_thread", lambda *a, **kw: None)
    # Missing ACK tests must be immediate; the normal-pace test below owns its clock.
    monkeypatch.setattr(gw, "_CHART_ACK_WAIT_SECONDS", 0)
    return {"root": root, "origin": origin, "session": session, "revision": 7}


def dispatch(chart, name, params):
    return gw._dispatch_brain_tool(
        name, params, chart["root"], None, None, user_id=USER,
        chart_client="terminal", chart_origin_id=chart["origin"],
        chart_context_revision=chart["revision"])


def context(chart):
    return {"page": "terminal", "ai_context": {
        "schema": "ai_context_client.v1", "origin_id": chart["origin"],
        "context_revision": chart["revision"], "captured_at": "2026-10-18T09:00:00Z",
        "pinned": [], "active": {"type": "security", "id": "NVDA"},
        "ambient": {"symbol": "NVDA", "timeframe": "D", "page": "terminal", "panel": None}}}


def block(name, params, identity):
    return SimpleNamespace(type="tool_use", name=name, input=params, id=identity)


class ScriptedClient:
    def __init__(self, rounds):
        self.rounds = iter(rounds)
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        blocks = next(self.rounds, None)
        return SimpleNamespace(
            content=blocks if blocks is not None else [SimpleNamespace(type="text", text="Analysis completed from the available chart evidence.")],
            stop_reason="tool_use" if blocks is not None else "end_turn",
            usage=SimpleNamespace(input_tokens=10, output_tokens=20))


def result_for(client, identity):
    for call in reversed(client.calls):
        for message in reversed(call["messages"]):
            rows = message.get("content")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict) and row.get("type") == "tool_result" and row.get("tool_use_id") == identity:
                    return json.loads(row["content"])
    raise AssertionError(f"Missing model receipt for {identity}")


def acknowledge(chart, wire, outcome="accepted", successor=None):
    if outcome == "missing":
        return
    successor = successor or wire["target"]
    session = copy.deepcopy(chart["session"])
    for key in ("symbol", "tf", "pane_id"):
        session[key] = successor[key]
    if outcome == "accepted" and wire["op"].startswith("draw."):
        session["drawings"].append({"id": wire["id"], "by": "ai", "op": wire["op"]})
    if outcome == "accepted" and wire["op"] == "chart.set_indicators":
        session["indicator_visibility"]["hidden"] = []
    acknowledgement = {"batch_id": wire["batch_id"], "seq": wire["seq"], "id": wire.get("id"),
                       "ok": outcome == "accepted"}
    if outcome == "accepted":
        acknowledgement["application"] = {"schema": "chart.command_application.v1",
                                           "predecessor": wire["target"], "successor": successor}
    else:
        acknowledgement["error"] = {
            "rejected": "bad_drawing_anchor", "cancelled": "command_cancelled_by_user",
            "uncertain": "indicator_application_failed"}[outcome]
    chart["session"] = session
    gw.put_chart_state(USER, "terminal", session, origin_id=chart["origin"],
                       context_revision=successor["context_revision"], acks=[acknowledgement])


def run_model(chart, monkeypatch, rounds, *, stream=True, ack=None, lane="fast"):
    client = ScriptedClient(rounds)
    monkeypatch.setattr(gw, "_build_lane_providers",
                        lambda *a, **kw: [{"client": client, "model": "deepseek-chat"}])
    if not stream:
        return client, gw.chat("Showcase a complete technical drawing analysis", USER, lane=lane,
                               context=context(chart), root=chart["root"])
    events = []
    for raw in gw.chat_stream("Showcase a complete technical drawing analysis", USER, lane=lane,
                              context=context(chart), root=chart["root"]):
        if raw.startswith("data: "):
            event = json.loads(raw[6:])
            events.append(event)
            if event.get("type") == "command" and event.get("v") == 2 and ack:
                ack(event)
    return client, events


@pytest.mark.parametrize("kind", [row["kind"] for row in MANIFEST["tools"]])
def test_every_reviewed_receiver_kind_is_admitted_without_a_server_tool_catalog(chart, kind):
    out = dispatch(chart, "emit_chart_command", native(kind))
    assert out.get("client_executed") is True, out


@pytest.mark.parametrize("change", [
    {"kind": "longposition"}, {"points": [point(0)]}, {"points": [point(0)] * 3},
    {"points": [point(2), point(1), point(0)]}, {"style": {"width": 0}},
    {"style": {"color": "red"}}, {"style": {"account_size": 10000}},
    {"fibonacci": {"levels": [0, 1, 1]}}, {"fibonacci": {"levels": [float("nan")]}},
    {"fibonacci": {"reverse": "yes"}}, {"probability": 0.9}, {"text": "unsupported"},
])
def test_native_capability_preflight_rejects_unsupported_or_malformed_values(chart, change):
    cmd = native("fibtrend")
    cmd["args"].update(change)
    out = dispatch(chart, "emit_chart_command", cmd)
    assert "error" in out and not out.get("client_executed")


def test_native_annotation_requires_visible_plain_text(chart):
    cmd = native("callout")
    cmd["args"]["text"] = "\x00\x01\x7f"
    assert dispatch(chart, "emit_chart_command", cmd)["error"] == "drawing_text_required"


def test_zero_price_pattern_leg_is_refused_before_emission(chart):
    cmd = native("xabcd")
    cmd["args"]["points"][1]["p"] = cmd["args"]["points"][0]["p"]
    assert dispatch(chart, "emit_chart_command", cmd)["error"] == "degenerate_pattern_leg"


def test_plan_preflights_every_child_before_producing_one_validated_wrapper(chart):
    commands = composition()
    original = copy.deepcopy(commands)
    out = dispatch(chart, "emit_chart_plan", {"title": "Structure and confirmation", "commands": commands})
    assert out["type"] == "command_plan" and out["client_executed"] is True
    assert [child["id"] for child in out["commands"]] == [child["id"] for child in commands]
    assert all("target" not in child and "seq" not in child for child in out["commands"])
    assert commands == original


@pytest.mark.parametrize("commands", [
    None, [], [native("fibtrend")] * 25, [native("fibtrend"), native("channel")],
    [native("channel"), {"op": "chart.set_indicators", "args": {"indicators": []}}],
    [native("channel"), {"op": "draw.fib", "id": "ai_bad", "args": {"p1": point(0)}}],
    [native("channel"), {"op": "draw.path", "id": "ai_bad", "args": {"points": []}}],
    [native("channel"), {"op": "draw.risk_box", "id": "ai_bad", "args": {"entry": 100}}],
    [native("channel"), {"op": "draw.tool", "id": "ai_bad", "args": {"kind": "unknown", "points": [point()]}}],
])
def test_invalid_plan_rejects_whole_preflight_with_no_emission(chart, commands):
    out = dispatch(chart, "emit_chart_plan", {"commands": commands})
    assert "error" in out and out["emitted"] == 0
    assert not out.get("client_executed")


def test_old_receiver_cannot_silently_accept_a_plan_or_claim_indicator_visibility(chart):
    chart["session"]["capabilities"].pop("drawing_plan")
    chart["session"]["capabilities"]["indicator_edit"].pop("visibility")
    gw.put_chart_state(USER, "terminal", chart["session"], origin_id=chart["origin"], context_revision=7)
    assert dispatch(chart, "emit_chart_plan", {"commands": composition()})["error"] == "drawing_plan_not_supported"
    assert dispatch(chart, "toggle_chart_indicator", {"indicator": "rsi", "on": True})["error"] == "indicator_visibility_not_supported"


def test_enable_reveals_an_attached_hidden_indicator_and_disable_has_a_valid_patch_shape(chart):
    enabled = dispatch(chart, "toggle_chart_indicator", {"indicator": "rsi", "on": True})
    assert enabled["args"] == {"mode": "patch", "indicators": [{"name": "rsi"}], "show": ["rsi"]}
    disabled = dispatch(chart, "toggle_chart_indicator", {"indicator": "rsi", "on": False})
    assert disabled["args"] == {"mode": "patch", "indicators": [], "remove": ["rsi"]}


def test_reservation_freezes_one_target_and_refuses_capacity_before_any_wire(chart):
    validated = dispatch(chart, "emit_chart_plan", {"commands": composition()})
    wires, error = gw._prepare_chart_command_wires(validated, USER, chart["origin"], 7, "brain_plan", 20)
    assert error is None and [wire["seq"] for wire in wires] == [20, 21, 22, 23]
    assert all(wire["target"] == wires[0]["target"] for wire in wires)
    assert wires[0]["target"]["pane_id"] == 1
    wires, error = gw._prepare_chart_command_wires(validated, USER, chart["origin"], 7, "brain_plan", 21)
    assert wires == [] and error["emitted"] == 0 and error["available_commands"] == 3
    gw.put_chart_state(USER, "terminal", chart["session"], origin_id=chart["origin"], context_revision=8)
    wires, error = gw._prepare_chart_command_wires(validated, USER, chart["origin"], 7, "brain_plan", 0)
    assert wires == [] and error["error"] == "command_target_unavailable"
    assert error["automatic_retry_allowed"] is False


@pytest.mark.parametrize("lane", ["fast", "pro"])
def test_stream_preserves_multiple_plan_results_and_an_interleaved_single_command(chart, monkeypatch, lane):
    first, second = composition("first"), composition("second")
    single = {"op": "draw.hline", "id": "ai_level", "args": {"p": 110}}
    rounds = [[block("emit_chart_plan", {"commands": first}, "plan-first"),
               block("emit_chart_command", single, "level"),
               block("emit_chart_plan", {"commands": second}, "plan-second")]]
    client, events = run_model(chart, monkeypatch, rounds, lane=lane,
                                ack=lambda wire: acknowledge(chart, wire))
    wires = [event for event in events if event.get("type") == "command"]
    assert [wire["seq"] for wire in wires] == list(range(9))
    assert len({wire["batch_id"] for wire in wires}) == 1
    assert {tool["name"] for tool in client.calls[0]["tools"]} >= {"emit_chart_plan", "emit_chart_command"}
    for identity, commands in (("plan-first", first), ("plan-second", second)):
        receipt = result_for(client, identity)
        assert receipt["plan_status"] == "accepted" and receipt["counts"]["accepted"] == 4
        assert [row["id"] for row in receipt["commands"]] == [cmd["id"] for cmd in commands]
        assert [row["index"] for row in receipt["commands"]] == [0, 1, 2, 3]
        assert all(row["effect_state"] == "applied_not_render_verified" for row in receipt["commands"])
        assert all("observed_state" not in row for row in receipt["commands"])
    assert result_for(client, "level")["id"] == "ai_level"


def test_stream_reports_partial_cancellation_and_uncertainty_without_rolling_back_or_resending(chart, monkeypatch):
    commands = composition()
    outcomes = ["accepted", "cancelled", "uncertain", "missing"]
    client, events = run_model(chart, monkeypatch, [[block("emit_chart_plan", {"commands": commands}, "mixed")]],
        ack=lambda wire: acknowledge(chart, wire, outcomes[wire["seq"]]))
    receipt = result_for(client, "mixed")
    assert receipt["plan_status"] == "partial"
    assert receipt["counts"] == {"accepted": 1, "rejected": 0, "cancelled": 1, "unverified": 2}
    assert [row["command_outcome"] for row in receipt["commands"]] == ["accepted", "cancelled", "unconfirmed", "unverified"]
    assert all(row["automatic_retry_allowed"] is False for row in receipt["commands"])
    assert len([row for row in events if row.get("type") == "command"]) == 4
    assert [row["id"] for row in chart["session"]["drawings"]] == [commands[0]["id"]]


def test_nonstream_returns_every_wire_and_marks_every_child_unverified(chart, monkeypatch):
    commands = composition()
    client, response = run_model(chart, monkeypatch,
        [[block("emit_chart_plan", {"commands": commands}, "nonstream")]], stream=False)
    assert [wire["id"] for wire in response["commands"]] == [cmd["id"] for cmd in commands]
    receipt = result_for(client, "nonstream")
    assert receipt["plan_status"] == "unverified" and receipt["counts"]["unverified"] == 4
    assert all(row["reason"] == "nonstream_client_not_yet_received" for row in receipt["commands"])
    assert all(row["effect_state"] == "unknown" for row in receipt["commands"])


def test_actual_stream_boundary_respects_remaining_turn_budget(chart, monkeypatch):
    many = [{"op": "draw.hline", "id": f"ai_level_{i}", "args": {"p": 100 + i}} for i in range(22)]
    client, events = run_model(chart, monkeypatch, [
        [block("emit_chart_plan", {"commands": many}, "first22")],
        [block("emit_chart_plan", {"commands": composition()}, "overcap")]],
        ack=lambda wire: acknowledge(chart, wire))
    assert len([event for event in events if event.get("type") == "command"]) == 22
    error = result_for(client, "overcap")
    assert error["error"] == "chart_batch_capacity_exceeded" and error["emitted"] == 0


def test_indicator_successor_is_reread_before_a_new_plan_targets_the_updated_chart(chart, monkeypatch):
    rounds = [
        [block("toggle_chart_indicator", {"indicator": "rsi", "on": True}, "enable")],
        [block("read_chart_state", {}, "reread")],
        [block("emit_chart_plan", {"commands": composition()}, "updated")]]
    def accept(wire):
        successor = {**wire["target"], "context_revision": 8} if wire["op"] == "chart.set_indicators" else None
        acknowledge(chart, wire, successor=successor)
    client, events = run_model(chart, monkeypatch, rounds, ack=accept)
    wires = [event for event in events if event.get("type") == "command"]
    assert len(wires) == 5 and wires[0]["target"]["context_revision"] == 7
    assert all(wire["target"]["context_revision"] == 8 for wire in wires[1:])
    reread = result_for(client, "reread")
    assert reread["connected"] is True and reread["context_revision"] == 8
    assert reread["session"]["indicator_visibility"]["hidden"] == []
    assert result_for(client, "updated")["plan_status"] == "accepted"


def test_normal_motion_24_commands_fit_one_collective_bounded_ack_wait(monkeypatch):
    clock = [0.0]
    target = {"schema": "chart.command_target.v1", "origin_id": "paced", "context_revision": 7,
              "symbol": "NVDA", "tf": "D", "pane_id": 1}
    wires = [{"v": 2, "on": True, "batch_id": "brain_paced", "seq": i,
              "op": "draw.hline", "id": f"ai_{i}", "args": {"p": 100 + i}, "target": target} for i in range(24)]
    def paced_record(*args, **kwargs):
        count = min(24, int(clock[0] / 0.65))
        return {"origin_id": "paced", "context_revision": 7,
                "session": {"symbol": "NVDA", "tf": "D", "pane_id": 1},
                "acks": [{"batch_id": wire["batch_id"], "seq": wire["seq"], "id": wire["id"], "ok": True}
                         for wire in wires[:count]]}
    monkeypatch.setattr(gw, "_CHART_ACK_WAIT_SECONDS", 2.0)
    monkeypatch.setattr(gw.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(gw.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(gw, "get_chart_state_record", paced_record)
    receipts = gw._wait_for_chart_command_acks(USER, "paced", 7, wires)
    assert len(receipts) == 24 and all(row["command_status"] == "accepted" for row in receipts)
    assert 15.6 <= clock[0] < 15.66
    assert gw._chart_ack_wait_budget(24) == pytest.approx(17.6)
    assert gw._chart_ack_wait_budget(10000) <= 20


@pytest.mark.parametrize("outcomes,status", [
    (["accepted", "rejected"], "partial"), (["cancelled", "cancelled"], "cancelled"),
    (["rejected", "rejected"], "rejected"), (["missing", "missing"], "unverified")])
def test_plan_summary_never_promotes_partial_or_unknown_application(outcomes, status):
    receipts = [{"command_outcome": "unverified" if outcome == "missing" else outcome} for outcome in outcomes]
    result = gw._chart_plan_receipt(receipts)
    assert result["plan_status"] == status and result["total"] == 2
    assert result["automatic_retry_allowed"] is False


def test_wrong_object_ack_cannot_become_an_accepted_plan_child_or_continuation(chart, monkeypatch):
    def ack(wire):
        acknowledge(chart, wire)
        if wire["id"].endswith("_0"):
            record = gw.get_chart_state_record(USER, "terminal", origin_id=chart["origin"])
            rows = copy.deepcopy(record["acks"])
            for row in rows:
                if row["batch_id"] == wire["batch_id"] and row["seq"] == wire["seq"]:
                    row["id"] = "ai_different_drawing"
            gw.put_chart_state(USER, "terminal", chart["session"], origin_id=chart["origin"],
                               context_revision=7, acks=rows)

    client, _ = run_model(chart, monkeypatch, [[block("emit_chart_plan", {"commands": composition()[:2]}, "plan")]], ack=ack)
    receipt = result_for(client, "plan")
    assert receipt["plan_status"] == "partial"
    assert receipt["counts"] == {"accepted": 1, "unverified": 1, "rejected": 0, "cancelled": 0}
    child = receipt["commands"][0]
    assert child["reason"] == "ack_drawing_id_mismatch" and child["effect_state"] == "unknown"
    assert child["id"] == "ai_a_0" and child["automatic_retry_allowed"] is False
    assert "continuation_target" not in child


def test_thinking_limit_after_applied_plan_preserves_receipts_without_redispatch(chart, monkeypatch):
    from tests.test_brain_gateway import _CaptureClient, _MockResponse, _MockUsage, _ThinkBlock

    commands = composition("recovery")
    client = _CaptureClient([
        _MockResponse([block("emit_chart_plan", {"commands": commands}, "recovery-plan")], "tool_use"),
        _MockResponse([_ThinkBlock("UNFINISHED_CHART_THINKING")], "max_tokens", _MockUsage(1399, 4000)),
    ])
    monkeypatch.setattr(gw, "_build_lane_providers",
                        lambda *a, **kw: [{"client": client, "model": "deepseek-chat"}])
    events = []
    for raw in gw.chat_stream("Showcase a complete technical drawing analysis", USER, lane="fast",
                              context=context(chart), root=chart["root"]):
        if not raw.startswith("data: "):
            continue
        event = json.loads(raw[6:])
        events.append(event)
        if event.get("type") == "command" and event.get("v") == 2:
            acknowledge(chart, event)

    wires = [event for event in events if event.get("type") == "command"]
    assert [wire["id"] for wire in wires] == [command["id"] for command in commands]
    assert [row["id"] for row in chart["session"]["drawings"]] == [command["id"] for command in commands]
    tool_rounds = [kwargs for kwargs in client.stream_kwargs if "tools" in kwargs]
    synthesis = [kwargs for kwargs in client.stream_kwargs if "tools" not in kwargs]
    assert len(tool_rounds) == 2 and len(synthesis) == 1
    assert [kwargs["max_tokens"] for kwargs in tool_rounds] == [4000, 4000]
    assert synthesis[0]["max_tokens"] == 8000
    assert client.create_kwargs == []
    results = [
        row for message in synthesis[0]["messages"] if isinstance(message.get("content"), list)
        for row in message["content"] if isinstance(row, dict)
        and row.get("type") == "tool_result" and row.get("tool_use_id") == "recovery-plan"
    ]
    assert len(results) == 1
    receipt = json.loads(results[0]["content"])
    assert receipt["plan_status"] == "accepted"
    assert receipt["counts"]["accepted"] == len(commands)
    assert [row["id"] for row in receipt["commands"]] == [command["id"] for command in commands]
    assert all(row["effect_state"] == "applied_not_render_verified" for row in receipt["commands"])
    assert not any(
        (row.get("type") if isinstance(row, dict) else getattr(row, "type", "")) == "thinking"
        for message in synthesis[0]["messages"] if isinstance(message.get("content"), list)
        for row in message["content"]
    )
    done = next(event for event in events if event.get("type") == "done")
    assert done["degraded"] is False
    assert done["usage"]["output_tokens"] == 4020
