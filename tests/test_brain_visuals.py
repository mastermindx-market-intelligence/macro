"""Hermetic checks for native chat illustrations; no provider, account or data writes."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import math

import pytest


@pytest.fixture
def visual():
    assert importlib.util.find_spec("engine.neuralweb.brain_visuals"), "native illustration compiler is missing"
    return importlib.import_module("engine.neuralweb.brain_visuals")


def spec(template="bar", **overrides):
    return {"version": 1, "template": template, "title": "Example comparison",
            "columns": ["Period", "Series"], "rows": [["A", 0], ["B", -2], ["C", None]],
            "basis": "illustrative", **overrides}


def test_native_compiler_is_available():
    assert importlib.util.find_spec("engine.neuralweb.brain_visuals"), "native illustration compiler is missing"


@pytest.mark.parametrize("template", ["bar", "line", "area", "table", "metrics", "status", "scenarios", "timeline", "flow"])
def test_templates_have_bounded_native_wire(visual, template):
    request = spec(template)
    if template in {"status", "scenarios", "timeline", "flow"}:
        request.update(columns=["Subject", "Description", "Detail"], rows=[["A", "Watch", "Explanation"]])
    result = visual.compile_visual(request, [], "tool-1")
    assert result["type"] == "chart"
    assert result["visual"]["template"] == template
    assert result["visual"]["basis"] == "illustrative"
    assert result["visual_id"]
    assert "svg" not in result


def test_source_values_require_exact_prior_binding(visual):
    request = spec(rows=[["A", 2]], basis="source", bindings=[{"row": 0, "column": 1, "tool": "get_data", "pointer": "/series/0/value"}])
    observations = [("get_data", {"series": [{"value": 2}], "as_of": "2026-10-14"})]
    result = visual.compile_visual(request, observations, "tool-1")
    assert result["visual"]["basis"] == "source"
    assert result["visual"]["provenance"]["numeric_cells_matched"] == 1
    assert result["visual"]["provenance"]["semantic_verification"] is False
    assert "bindings" not in result["visual"]
    assert "error" in visual.compile_visual(request, [("get_data", {"series": [{"value": 3}]})], "tool-1")


@pytest.mark.parametrize("observations", [[], [("other", {"v": 2})], [("get_data", {"v": True})], [("get_data", {"error": "unavailable", "v": 2})], [("get_data", {"ok": False, "v": 2})], [("get_data", {"v": "2"})], [("get_data", {"v": math.inf})]])
def test_absent_failed_or_type_confused_source_is_rejected(visual, observations):
    request = spec(rows=[["A", 2]], basis="source", bindings=[{"row": 0, "column": 1, "tool": "get_data", "pointer": "/v"}])
    assert "error" in visual.compile_visual(request, observations, "tool-1")


def test_no_source_promotion_without_numeric_bindings(visual):
    assert "error" in visual.compile_visual(spec(basis="source"), [], "tool-1")
    assert "error" in visual.compile_visual(spec(basis="source", rows=[["A", "2"]]), [], "tool-1")


def test_duplicate_and_out_of_bounds_bindings_rejected(visual):
    binding = {"row": 0, "column": 1, "tool": "get_data", "pointer": "/v"}
    request = spec(rows=[["A", 2]], basis="source", bindings=[binding, binding])
    assert "error" in visual.compile_visual(request, [("get_data", {"v": 2})], "tool-1")
    request["bindings"] = [{**binding, "row": 4}]
    assert "error" in visual.compile_visual(request, [("get_data", {"v": 2})], "tool-1")


def test_last_observation_wins_without_fallback_to_stale_success(visual):
    request = spec(rows=[["A", 2]], basis="source", bindings=[{"row": 0, "column": 1, "tool": "get_data", "pointer": "/v"}])
    assert "error" in visual.compile_visual(request, [("get_data", {"v": 2}), ("get_data", {"error": "failed"})], "tool-1")


def test_json_pointer_escaping_and_array_bounds(visual):
    request = spec(rows=[["A", 2]], basis="source", bindings=[{"row": 0, "column": 1, "tool": "get_data", "pointer": "/a~1b/~0v/0"}])
    assert "visual" in visual.compile_visual(request, [("get_data", {"a/b": {"~v": [2]}})], "tool-1")
    request["bindings"][0]["pointer"] = "/a~1b/~0v/-1"
    assert "error" in visual.compile_visual(request, [("get_data", {"a/b": {"~v": [2]}})], "tool-1")


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"template": "html"}, {"html": "<script>"},
    {"title": "<img src=x onerror=alert(1)>"}, {"title": "javascript:alert(1)"},
    {"rows": [["A", True]]}, {"rows": [["A", math.nan]]}, {"rows": [["A", math.inf]]},
    {"rows": [["A", 1e100]]}, {"rows": [["A", 2, 3]]}, {"rows": []},
    {"rows": [["A", 1]] * 81}, {"columns": ["A"] * 7}, {"title": "x" * 501},
    {"rows": [["A", "=HYPERLINK(\"bad\")"]]}, {"basis": "verified"},
])
def test_malformed_input_is_small_error_not_exception_or_execution(visual, change):
    result = visual.compile_visual(spec(**change), [], "tool-1")
    assert "error" in result and len(str(result)) < 300
    assert "visual" not in result


def test_nulls_zeros_precision_and_inputs_are_preserved(visual):
    request = spec(rows=[["A", 0], ["B", None], ["C", -0.00012]])
    original = copy.deepcopy(request)
    result = visual.compile_visual(request, [], "call-1")
    assert result["visual"]["rows"] == original["rows"]
    assert request == original
    assert visual.compile_visual(request, [], "call-1")["visual_id"] == result["visual_id"]
    assert visual.compile_visual(request, [], "call-2")["visual_id"] != result["visual_id"]


def test_scatter_and_donut_cardinality(visual):
    assert "visual" in visual.compile_visual(spec("scatter", columns=["X", "Y"], rows=[[1, 2], [2, None]]), [], "1")
    assert "error" in visual.compile_visual(spec("scatter"), [], "1")
    assert "visual" in visual.compile_visual(spec("donut", rows=[["A", 3], ["B", 2]]), [], "1")
    assert "error" in visual.compile_visual(spec("donut", rows=[["A", -3]]), [], "1")
    assert "error" in visual.compile_visual(spec("donut", rows=[["A", 0]]), [], "1")


def test_retained_projection_is_closed_and_revalidated(visual):
    result = visual.compile_visual(spec(), [], "1")
    assert visual.public_visuals({"visuals": [result], "retained_context": {"secret": "hidden"}}) == [result]
    assert visual.public_visuals({"visuals": [{**result, "svg": "<script>bad</script>"}]}) == []
    assert visual.public_visuals({"visuals": [{**result, "visual": {**result["visual"], "rows": [["A", True]]}}]}) == []
    assert visual.public_visuals({"visuals": "malformed"}) == []


def test_copy_is_subject_to_existing_output_screen(visual):
    result = visual.compile_visual(spec(takeaway="private prompt"), [], "1", screen=lambda text: "private prompt" not in text)
    assert "error" in result


def test_two_symbols_from_same_tool_require_exact_call_identity(visual):
    observations = [("get_quote", {"price": 10}, "call-A"), ("get_quote", {"price": 20}, "call-B")]
    request = spec(rows=[["A", 10], ["B", 20]], basis="source", bindings=[
        {"row": 0, "column": 1, "tool": "get_quote", "call_id": "call-A", "pointer": "/price"},
        {"row": 1, "column": 1, "tool": "get_quote", "call_id": "call-B", "pointer": "/price"}])
    assert "visual" in visual.compile_visual(request, observations, "draw-1")
    request["bindings"][0]["call_id"] = "call-B"
    assert "error" in visual.compile_visual(request, observations, "draw-1")
    for binding in request["bindings"]:
        binding.pop("call_id")
    assert "error" in visual.compile_visual(request, observations, "draw-1")


def test_source_numeric_strings_do_not_launder_an_unbound_value(visual):
    request = spec("table", rows=[["A", 2], ["B", "25bp"]], basis="source", bindings=[{"row": 0, "column": 1, "tool": "get_data", "pointer": "/v"}])
    assert "error" in visual.compile_visual(request, [("get_data", {"v": 2})], "1")


# Candlestick is a 12th native visual preset, not a separate OHLC market-data owner.
def candle_spec(**changes):
    fields = {"title": "Illustrative bullish 30-minute pivot",
              "subtitle": "30-minute synthetic candles",
              "columns": ["Candle", "Open", "High", "Low", "Close"],
              "rows": [
                  ["1", 110, 114, 105, 106],
                  ["2", 106, 109, 101, 102],
                  ["Pivot", 102, 107, 101, 106],
                  ["Breakout", 106, 111, 104, 110],
              ]}
    fields.update(changes)
    return spec("candlestick", **fields)


def test_candle_compiler_preserves_ohlc_and_history_provenance(visual):
    args = candle_spec()
    wire = visual.compile_visual(args, [], "illustration-1")
    assert wire["type"] == "chart"
    assert wire["visual"]["template"] == "candlestick"
    assert wire["visual"]["basis"] == "illustrative"
    assert wire["visual"]["rows"] == args["rows"]
    assert visual.validate_view(wire)
    assert visual.public_visuals({"visuals": [wire]}) == [wire]
    assert "bindings" not in wire["visual"]
    assert wire["visual"]["provenance"]["sources"] == []


@pytest.mark.parametrize("changes", [
    {"columns": ["Candle", "Open", "Low", "High", "Close"]},
    {"columns": ["Candle", "Open", "High", "Low"]},
    {"rows": [["1", 1, 2, 0, 1]] * 3},
    {"rows": [["1", 1, 2, 0, 1]] * 49},
    {"rows": [["1", 1, 2, 0, 1], ["2", 1, 0.5, 0.75, 1], ["3", 1, 2, 0, 1], ["4", 1, 2, 0, 1]]},
    {"rows": [["1", 1, 2, 0, -1], ["2", 1, 2, 0, 1], ["3", 1, 2, 0, 1], ["4", 1, 2, 0, 1]]},
    {"rows": [[2, 1, 2, 0, 1]] * 4},
    {"rows": [["1", 1, math.inf, 0, 1]] * 4},
    {"rows": [["<script>", 1, 2, 0, 1]] * 4},
])
def test_candle_rejects_invalid_price_geometry_and_labels(visual, changes):
    assert "error" in visual.compile_visual(candle_spec(**changes), [], "bad-candle")


def test_candle_source_requires_exact_observation_for_every_ohlc_cell(visual):
    args = candle_spec()
    rows = args["rows"]
    bars = [{"open": row[1], "high": row[2], "low": row[3], "close": row[4]} for row in rows]
    args["basis"] = "source"
    args["bindings"] = [
        {"row": i, "column": j + 1, "tool": "get_ohlc", "pointer": f"/bars/{i}/{k}", "call_id": "source-1"}
        for i in range(len(rows)) for j, k in enumerate(["open", "high", "low", "close"])
    ]
    observed = [("get_ohlc", {"bars": bars}, "source-1")]
    wire = visual.compile_visual(args, observed, "source-chart")
    assert wire["visual"]["provenance"]["numeric_cells_matched"] == 16
    assert wire["visual"]["provenance"]["freshness_verified"] is False
    assert visual.validate_view(wire)
    args["bindings"].pop()
    assert "error" in visual.compile_visual(args, observed, "unbound")
    args["bindings"].append(
        {"row": 3, "column": 4, "tool": "get_ohlc", "pointer": "/bars/3/close", "call_id": "source-1"}
    )
    assert "error" in visual.compile_visual(args, [("get_ohlc", {"bars": bars, "ok": False}, "source-1")], "failed")
