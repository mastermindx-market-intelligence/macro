"""Native tool -> same Brain chart wire -> final response -> private history."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from engine.neuralweb import brain_gateway as gw
from engine.neuralweb.brain_visuals import compile_visual
from tests.test_brain_gateway import _MockBlock, _MockClient, _MockResponse, _sse
from tests.test_brain_visuals import spec

TID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def no_external_sources(monkeypatch, tmp_path):
    monkeypatch.setattr(gw, "_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr(gw, "_symbol_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr("lib.ai_costs._write_ledger_path", lambda root=None: tmp_path / "usage.jsonl")


def client_for(request):
    return _MockClient([
        _MockResponse([_MockBlock("tool_use", name="render_inline_visual", input_=request, id_="visual-1")], "tool_use"),
        _MockResponse([_MockBlock("text", "This example compares three observations.")]),
    ])


def test_existing_catalog_and_allowlist_admit_native_visual():
    assert "render_inline_visual" in gw._BRAIN_TOOLS
    assert "render_inline_visual" in gw._BRAIN_ONLY_TOOLS
    assert any(s["name"] == "render_inline_visual" for s in gw._brain_tool_schemas())


@pytest.mark.parametrize("streaming", [False, True])
def test_tool_reaches_existing_chart_channel_after_answer(tmp_path, streaming):
    client = client_for(spec())
    args = ("Draw an illustrative comparison", "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 3)
    if streaming:
        retained = []
        events = _sse(list(gw._run_brain_loop_stream(*args, meta_event={"type": "meta"}, visuals_out=retained)))
        charts = [e for e in events if e["type"] == "chart" and e.get("visual")]
        assert len(charts) == 1
        assert next(i for i,e in enumerate(events) if e["type"] == "delta") < next(i for i,e in enumerate(events) if e.get("visual"))
        assert events[-1]["charts"] == charts == retained
    else:
        charts = gw._run_brain_loop(*args)[-1]
        assert len(charts) == 1 and charts[0]["visual"]["template"] == "bar"
    # The model sees a small receipt, not its own full visual echoed back.
    receipts = [m for call in client.calls for m in call["messages"] if m.get("role") == "user" and isinstance(m.get("content"),list)]
    assert "visual_prepared" in str(receipts)


def test_stream_guard_withholds_visual_for_rejected_answer(tmp_path):
    client = client_for(spec())
    retained = []
    with patch("engine.neuralweb.ask_brain._post_filter_advice", side_effect=lambda t, c: (t, t.startswith("This example"))):
        events = _sse(list(gw._run_brain_loop_stream("Draw an example", "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 3, {"type": "meta"}, visuals_out=retained)))
    assert not [e for e in events if e.get("visual")]
    assert not retained
    assert events[-1]["charts"] == []


def test_history_projects_visuals_only_after_existing_owner_check():
    wire = compile_visual(spec(), [], "1")
    private = {"visuals": [wire], "native_input_manifest": {"secret": "never expose"}, "retained_context": {"private": 1}}
    with patch.object(gw, "_thread_read_rows", side_effect=[[{"id": TID}], [{"role":"assistant", "content":"Example", "created_at":"2026-10-15", "visuals":[wire], "meta":private}]]) as read:
        result = gw.get_thread(TID,"owner")
    assert "user_id=eq.owner" in read.call_args_list[0].args[0]
    assert result["messages"][0]["visuals"] == [wire]
    assert "meta" not in result["messages"][0]
    assert "never expose" not in str(result)
    with patch.object(gw, "_thread_read_rows", return_value=[]) as read:
        assert gw.get_thread(TID,"intruder") is None
        assert read.call_count == 1


def test_get_thread_drops_forged_or_user_visuals():
    wire = compile_visual(spec(), [], "1")
    with patch.object(gw, "_thread_read_rows", side_effect=[[{"id":TID}], [{"role":"user", "content":"Question", "visuals":[wire]}, {"role":"assistant", "content":"Answer", "visuals":[{"svg":"bad"}]}]]):
        result=gw.get_thread(TID,"owner")
    assert all(not m.get("visuals") for m in result["messages"])


def test_widget_and_restart_contract_are_wired():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    js=(root/'templates/mm_brain.js').read_text()
    assert 'renderer.mount(host, wire, {' in js and 'window.MMBrainVisuals' in js
    assert 'window.MMBrain.expand()' in js and 'loadPresentationAssets()' in js
    assert 'm.visuals' in js and 'j.charts' in js
    assert 'mm_brain_visuals.js' in js and 'mm_brain_visuals.css' in js
    assert 'brain_visuals' in (root/'app/deploy/update.sh').read_text()


def test_live_data_request_cannot_be_downgraded_to_numeric_example(tmp_path):
    client = client_for(spec())
    charts = gw._run_brain_loop("Chart the latest Treasury yields", "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 3)[-1]
    assert charts == []


def test_qualitative_explanation_remains_available_without_market_claim(tmp_path):
    request = spec("flow", columns=["Step", "Next"], rows=[["Inflation shock", "Policy repricing"]])
    client = client_for(request)
    charts = gw._run_brain_loop("Explain this transmission mechanism", "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 3)[-1]
    assert len(charts) == 1 and charts[0]["visual"]["basis"] == "illustrative"


@pytest.mark.parametrize("same_batch", [False, True])
def test_binding_uses_exact_completed_call_not_future_parallel_sibling(tmp_path, same_batch):
    request = spec(rows=[["A", 10], ["B", 20]], basis="source", bindings=[
        {"row":0,"column":1,"tool":"get_quote","call_id":"quote-A","pointer":"/price"},
        {"row":1,"column":1,"tool":"get_quote","call_id":"quote-B","pointer":"/price"}])
    quote_a = _MockBlock("tool_use", name="get_quote", input_={"symbol":"A"}, id_="quote-A")
    quote_b = _MockBlock("tool_use", name="get_quote", input_={"symbol":"B"}, id_="quote-B")
    draw = _MockBlock("tool_use", name="render_inline_visual", input_=request, id_="draw-1")
    blocks = [_MockResponse([quote_a,quote_b,draw],"tool_use")] if same_batch else [_MockResponse([quote_a,quote_b],"tool_use"),_MockResponse([draw],"tool_use")]
    client = _MockClient(blocks+[_MockResponse([_MockBlock("text","A comparison based on retrieved quotes.")])])
    dispatch = gw._dispatch_brain_tool
    def fake(name, params, *a, **k):
        if name == 'get_quote':
            return {'price':10 if params['symbol']=='A' else 20}
        return dispatch(name,params,*a,**k)
    with patch.object(gw, '_dispatch_brain_tool', side_effect=fake):
        charts = gw._run_brain_loop("Compare the quoted prices", "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 4)[-1]
    assert len(charts) == (0 if same_batch else 1)


@pytest.mark.parametrize('message', ['Illustrate the latest Treasury yields', 'Give an example with actual live prices', '用示意图展示当前收益率'])
def test_request_to_illustrate_real_data_does_not_authorize_invented_numbers(tmp_path, message):
    client = client_for(spec())
    assert gw._run_brain_loop(message, 'fast', [], {}, tmp_path, tmp_path, '', client, 'test-model', 1000, 3)[-1] == []


def chart_visual_client(request):
    return _MockClient([
        _MockResponse([_MockBlock("tool_use", name="emit_chart_command",
                                 input_={"op": "draw.hline", "args": {"p": 100}}, id_="action-1")], "tool_use"),
        _MockResponse([_MockBlock("tool_use", name="render_inline_visual", input_=request, id_="visual-after-action")], "tool_use"),
        _MockResponse([_MockBlock("text", "The chart action has its own execution receipt.")]),
    ])


def chart_dispatch_fixture(name, params, *args, **kwargs):
    if name == "emit_chart_command":
        return {"client_executed": True, "v": 2, "op": "draw.hline",
                "id": "ai_visual_receipt", "args": {"p": 100}}
    return ORIGINAL_DISPATCH(name, params, *args, **kwargs)


ORIGINAL_DISPATCH = gw._dispatch_brain_tool


def test_nonstream_visual_cannot_source_an_unreceived_chart_command(tmp_path):
    from tests.test_brain_chart_continuation import target
    request = spec(rows=[["Requested level", 100]], basis="source", bindings=[
        {"row": 0, "column": 1, "tool": "emit_chart_command", "call_id": "action-1", "pointer": "/args/p"}])
    client = chart_visual_client(request)
    with patch.object(gw, "_dispatch_brain_tool", side_effect=chart_dispatch_fixture), \
            patch.object(gw, "_chart_command_target_for_result", return_value=target()):
        result = gw._run_brain_loop("Draw the requested chart level and show its result", "fast", [],
                                    {"page": "terminal"}, tmp_path, tmp_path, "", client, "test-model", 1000, 4)
    assert len(result[-2]) == 1  # delivery is prepared; no client ACK can exist yet
    assert result[-1] == []  # requested effect arguments are not observations


def test_stream_visual_sources_the_matching_applied_receipt(tmp_path):
    from tests.test_brain_chart_continuation import ack, state, target
    request = spec("table", columns=["Action", "Outcome"], rows=[["Chart action", "accepted"]],
                   basis="source", bindings=[{"row": 0, "column": 1, "tool": "emit_chart_command",
                                              "call_id": "action-1", "pointer": "/command_outcome"}])
    client = chart_visual_client(request)
    admitted = []

    def acknowledge(user, origin, revision, wires):
        admitted.extend(wires)
        return [gw._verified_chart_command_receipt(wire, ack(wire), state(wire["target"]),
                                                   expected_context_revision=wire["target"]["context_revision"])
                for wire in wires]

    retained = []
    with patch.object(gw, "_dispatch_brain_tool", side_effect=chart_dispatch_fixture), \
            patch.object(gw, "_chart_command_target_for_result", return_value=target()), \
            patch.object(gw, "_wait_for_chart_command_acks", side_effect=acknowledge):
        events = _sse(list(gw._run_brain_loop_stream(
            "Draw the requested chart level and show its execution receipt", "fast", [],
            {"page": "terminal"}, tmp_path, tmp_path, "", client, "test-model", 1000, 4,
            {"type": "meta"}, visuals_out=retained)))
    assert len(admitted) == 1 and admitted[0]["target"] == target()
    charts = [event for event in events if event.get("visual")]
    assert len(charts) == 1 and charts[0]["visual"]["rows"] == [["Chart action", "accepted"]]
    assert events[-1]["charts"] == charts == retained
