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
