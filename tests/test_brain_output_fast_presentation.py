"""Fast presentation uses admitted schemas without widening the evidence surface."""
from __future__ import annotations

import pytest
from engine.neuralweb import brain_gateway as gw
from engine.neuralweb.ask_brain import _fast_visible_tool_names, _question_profile
from tests.test_brain_gateway import _MockBlock, _MockClient, _MockResponse, _sse
from tests.test_brain_visuals import spec

EXACT_PROMPT = (
    "UI capability audit: Show one native bar chart for a fictional company with revenue "
    "of 10, 20, and 30 in Year 1, Year 2, and Year 3. Clearly label it illustrative, "
    "not market data. Explain it in one sentence."
)

def visible(schemas, message=EXACT_PROMPT, mode="chat"):
    return gw._fast_visible_tool_schemas(
        schemas, message, None, lane="fast", mode=mode, page="macro", internals_allowed=False,
    )

def test_exact_failed_prompt_gets_presentation_without_external_data():
    assert _question_profile(EXACT_PROMPT, None).name == "self_contained_financial"
    schemas = [{"name": n} for n in (
        "get_quote", "get_fundamentals", "render_inline_visual",
        "render_inline_chart", "render_financial_widget",
    )]
    assert [s["name"] for s in visible(schemas)] == ["render_inline_visual"]
    assert visible([{"name": "get_quote"}]) == []
    assert visible([]) == []

def test_ordinary_fast_data_family_is_unchanged(tmp_path):
    message = "Why did NVDA move today?"
    full = gw._all_brain_tool_schemas(tmp_path, page="macro", user_id="")
    profile = _question_profile(message, None)
    expected = set(_fast_visible_tool_names(profile) or ())
    assert expected
    assert {s["name"] for s in visible(full, message)} == expected.intersection(
        {s["name"] for s in full}
    )

def test_presentation_never_invents_an_upstream_withheld_tool():
    schemas = [{"name": "get_quote"}, {"name": "get_fundamentals"}]
    assert all(s in schemas for s in visible(schemas, "Show AAPL financial statements"))
    assert not any(s["name"].startswith("render") for s in visible(schemas))

def test_closed_research_stays_zero_tools_and_no_presentation_instruction():
    assert visible([], mode="research") == []
    prompt = gw._presentation_prompt_for_tools(gw._build_grounded_system_prompt(), [])
    assert "use render_inline_visual." not in prompt
    assert "render_inline_chart IS" not in prompt
    assert "native tool-call channel" not in prompt

def test_prompt_uses_only_offered_presentation_capabilities():
    original = gw._build_system_prompt("chat", "macro", lane="fast")
    none = gw._presentation_prompt_for_tools(original, [])
    assert "use render_inline_visual." not in none
    assert "render_inline_chart IS" not in none
    visual = gw._presentation_prompt_for_tools(original, [{"name": "render_inline_visual"}])
    assert "use render_inline_visual." in visual
    assert "render_inline_chart IS" not in visual
    assert "native tool-call channel" in visual

@pytest.mark.parametrize("streaming", [False, True])
def test_exact_request_offers_tool_and_delivers_real_visual(tmp_path, monkeypatch, streaming):
    monkeypatch.setattr(gw, "_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr(gw, "_symbol_grounding_digest", lambda *a, **k: "")
    monkeypatch.setattr("lib.ai_costs._write_ledger_path", lambda root=None: tmp_path / "usage.jsonl")
    request = spec()
    request["rows"] = [["Year 1", 10], ["Year 2", 20], ["Year 3", 30]]
    client = _MockClient([
        _MockResponse([_MockBlock("tool_use", name="render_inline_visual", input_=request, id_="visual-regression")], "tool_use"),
        _MockResponse([_MockBlock("text", "Illustrative revenue rises from 10 to 30.")]),
    ])
    args = (EXACT_PROMPT, "fast", [], {}, tmp_path, tmp_path, "", client, "test-model", 1000, 3)
    if streaming:
        events = _sse(list(gw._run_brain_loop_stream(*args, meta_event={"type": "meta"})))
        charts = [e for e in events if e.get("visual")]
    else:
        charts = gw._run_brain_loop(*args)[-1]
    assert len(charts) == 1
    assert charts[0]["visual"]["rows"] == request["rows"]
    assert {s["name"] for s in client.calls[0]["tools"]} == {"render_inline_visual"}

@pytest.mark.parametrize("text", [
    '<tool_calls><invoke name="render_inline_visual">bad</invoke></tool_calls>',
    '<INVOKE name="render_inline_visual">bad</INVOKE>',
    "图表 <tool_calls>invalid</tool_calls>",
])
def test_invalid_tool_prose_is_not_displayed_or_executed(text):
    screened = gw._leak_screen(text)
    assert "<" not in screened
    assert screened != text
    assert gw._leak_screen("Revenue rose by 10% in this illustrative example.") == (
        "Revenue rose by 10% in this illustrative example."
    )


def test_stream_gate_never_flushes_invalid_tool_xml_before_fallback():
    gate = gw._StreamGate(1, 0, 256)
    chunks = ["<tool_", "calls><invoke name=\"render_inline_visual\">", "x" * 800, "</invoke></tool_calls>"]
    assert "".join(gate.feed(chunk) for chunk in chunks) == ""
    assert "couldn’t prepare" in gw._leak_screen(gate.text)


def test_offered_macro_inflation_reader_is_dispatch_admitted(tmp_path):
    full = gw._all_brain_tool_schemas(tmp_path, page="macro", user_id="")
    offered = {t["name"] for t in full}
    assert "read_inflation_intelligence" in offered
    assert "read_inflation_intelligence" in gw._BRAIN_TOOLS
    assert "read_inflation_intelligence" not in gw._BRAIN_ONLY_TOOLS
