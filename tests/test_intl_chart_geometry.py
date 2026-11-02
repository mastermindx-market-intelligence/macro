"""Geometry for qualified, gap-aware IM02 charts; no UI or source decisions."""
from copy import deepcopy
import json
import math
import re

import pytest

from tests.test_intl_chart_publication import inputs, _case, _project
from lib.intl_chart_geometry import build_chart_geometry


def test_same_start_qualified_lines_have_shared_scales_and_no_rebase_drift(inputs):
    view, raw, evidence = _case(inputs)
    admitted = _project(view, raw, evidence)
    result = build_chart_geometry(admitted, width=640, height=220)
    assert result["schema"] == "intl-chart-geometry.v1"
    assert result["status"] == "available"
    assert len(result["cohorts"]) == 1
    group = result["cohorts"][0]
    assert {p["market_id"] for p in group["paths"]} == {"JP", "GB"}
    assert group["min_value"] < 100 < group["max_value"]
    assert group["width"] == 640 and group["height"] == 220
    assert 0 <= group["baseline_y"] <= 220
    for p in group["paths"]:
        assert len(p["segments"]) == 1
        line = p["segments"][0]
        assert line["count"] >= 2
        assert line["first_x"] == pytest.approx(0.0)
        assert line["last_x"] == pytest.approx(640.0)
        assert line["d"].startswith("M")
        assert "nan" not in line["d"].lower()
        assert "inf" not in line["d"].lower()
    json.dumps(result, allow_nan=False)


def test_no_path_is_drawn_across_missing_fx_observation(inputs):
    _, frame = inputs
    frame = frame.copy()
    gap_date = frame.index[12].isoformat()
    frame.loc[frame.index[12], "USDJPY=X"] = float("nan")
    view, raw, evidence = _case(inputs, data=frame)
    model = _project(view, raw, evidence)
    out = build_chart_geometry(model, width=640, height=220)
    japan = next(p for p in out["cohorts"][0]["paths"] if p["market_id"] == "JP")
    assert japan["gaps"] == 1
    assert len(japan["segments"]) == 2
    assert all(s["last_timestamp"] < gap_date or s["first_timestamp"] > gap_date
               for s in japan["segments"])
    assert all(gap_date not in seg["d"] for seg in japan["segments"])


def test_unqualified_market_is_not_in_geometry_even_if_raw_exists(inputs):
    view, raw, evidence = _case(inputs, drop_fx=True)
    model = _project(view, raw, evidence)
    out = build_chart_geometry(model)
    assert out["status"] == "unavailable" and out["cohorts"] == []
    assert out["benchmark"]["reason"] == "benchmark_source_not_qualified"


@pytest.mark.parametrize("width,height", [(0,220), (-5,220), (640,0), (640,float("inf")), (True,200)])
def test_unbounded_or_non_numeric_canvas_arguments_are_refused(inputs, width, height):
    view, raw, evidence = _case(inputs)
    with pytest.raises(ValueError, match="invalid_chart_geometry"):
        build_chart_geometry(_project(view, raw, evidence), width=width, height=height)


def test_publication_model_is_not_mutated_by_geometry(inputs):
    view, raw, evidence = _case(inputs)
    model = _project(view, raw, evidence)
    copy = deepcopy(model)
    build_chart_geometry(model)
    assert model == copy
