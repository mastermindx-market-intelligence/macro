"""Display contract tests; fixtures do not attest live market facts."""
from copy import deepcopy
import ast
from pathlib import Path
import pytest
from engine.prophet_opportunity_presentation import present_us_candidate


def row():
    return {"ticker": "DEMO", "name": "Example", "sector": "Technology", "industry": "Components",
            "price": 101.5, "price_as_of": "2026-09-28T16:00:00-04:00", "signal_asof": "2026-09-25",
            "lane": "continuation", "prophet": {"score": 0},
            "entry_signal": {"status": "buy_now", "headline": "Review concentration.", "buy_zone": {"low": 99, "high": 101}},
            "spark_svg": '<svg class="nch" viewBox="0 0 240 42"><polyline fill="none" points="0,42 120,21 240,0"/></svg>'}


def present(data, **kwargs):
    return present_us_candidate(data, occurrence_id="today-DEMO-0", **kwargs)


def test_preserves_independent_dates_and_missing_fields_without_renewal():
    v = present(row(), board_asof="2026-09-29", setup_href="#setup-DEMO")
    assert v["assessment_asof"] == "2026-09-25"
    assert v["quote"]["asof"] == "2026-09-28T16:00:00-04:00"
    assert v["terms"]["asof"] == "2026-09-29"
    assert v["chart"]["asof"] is None
    assert v["strategy"] is v["horizon"] is v["quote"]["change"] is None
    assert v["priority"]["value"] == "0"


def test_does_not_infer_entry_from_direction_or_price_in_zone():
    source = row(); source["entry_signal"] = {}; source["dir"] = "up"
    v = present(source)
    assert v["stance"] == "unknown" and v["terms"]["value"] is None
    assert v["quote"]["direction"] == v["chart"]["direction"] == "neutral"


def test_unknown_status_is_not_silently_wait_or_buy():
    source = row(); source["entry_signal"]["status"] = "future_state"
    assert present(source)["stance"] == "unknown"


def test_no_mutation_alias_or_ticker_only_plan_join():
    source = row(); original = deepcopy(source)
    v = present(source, folded_cautions=[("Existing caution", "原有提醒")], marks=[{"en": "Featured", "zh": "精选"}])
    v["identity"]["name"]["en"] = "Changed"
    assert source == original
    assert "plan" not in v and "receipt" not in v
    assert v["cautions"] == [{"en": "Existing caution", "zh": "原有提醒"}]


def test_score_fallback_keeps_label_and_meaning_together():
    source = row(); source["prophet"]["score"] = float("nan"); source["conviction"] = {"score_edge": 42}
    v = present(source)
    assert v["priority"]["label"]["en"] == "Edge"
    assert v["source_fields"]["priority"] == "conviction.score_edge"


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "99", 10 ** 400])
def test_non_numbers_do_not_become_prices_or_zones(value):
    source = row(); source["price"] = value; source["entry_signal"]["buy_zone"]["low"] = value
    v = present(source, board_asof="2026-09-29")
    assert v["quote"]["price"] is None and v["terms"]["value"] is None and v["terms"]["asof"] is None


def test_chart_preserves_geometry_without_importing_markup():
    v = present(row())
    assert v["chart"]["points"] == [{"x": 0., "y": 100.}, {"x": 50., "y": 50.}, {"x": 100., "y": 0.}]
    assert "<svg" not in str(v)


@pytest.mark.parametrize("count", [2, 8, 64])
@pytest.mark.parametrize("zone_state", [None, "active", "pending"])
def test_accepts_the_existing_native_spark_renderer(count, zone_state):
    # Exercise the exact pure renderer without importing the full data pipeline.
    path = Path(__file__).resolve().parents[1] / "scripts/build_stock_library.py"
    tree = ast.parse(path.read_text())
    definition = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_spark_svg")
    scope = {}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(path), "exec"), scope)
    values = [100 + (i % 5) for i in range(count)]
    svg = scope["_spark_svg"](values, zone_lo=101, zone_hi=103, zone_state=zone_state)
    source = row(); source["spark_svg"] = svg
    points = present(source)["chart"]["points"]
    assert len(points) == count
    assert points[0]["x"] == 0 and points[-1]["x"] == 100
    assert all(0 <= p["y"] <= 100 for p in points)


@pytest.mark.parametrize("svg", [
    '<svg class="nch" viewBox="0 0 240 42"><script>bad()</script></svg>',
    '<!DOCTYPE svg [<!ENTITY x "hello">]><svg/>',
    '<svg class="nch" viewBox="0 0 240 42"><polyline fill="none" points="0,NaN 240,1"/></svg>',
    '<svg class="nch" viewBox="0 0 240 42"><polyline fill="none" points="240,1 0,2"/></svg>',
    '<svg class="nch" viewBox="0 0 0 42"><polyline fill="none" points="0,1 0,2"/></svg>',
    '<svg class="nch" viewBox="0 0 240 42" onload="bad()"><polyline fill="none" points="0,1 240,2"/></svg>',
])
def test_bad_chart_becomes_unavailable_without_fake_geometry(svg):
    source = row(); source["spark_svg"] = svg
    assert present(source)["chart"]["points"] == []


@pytest.mark.parametrize("href", ["javascript:bad()", "//evil.example/", "/\\evil.example", "https://example.com", "/\nevil"])
def test_actions_do_not_accept_external_or_unsafe_destinations(href):
    assert present(row(), setup_href=href)["setup_href"] is None


def test_minimal_row_has_no_stage_or_comparison_identity():
    v = present({}, compare_enabled=True)
    assert not v["compare_enabled"] and v["stages"] == []
    assert v["observation"] is None and v["priority"] is None
    assert present({"lane": ["continuation"]})["stages"] == []


def test_ids_are_supplied_occurrences_not_ticker_deduplication():
    a = present_us_candidate(row(), occurrence_id="today-DEMO-0")
    b = present_us_candidate(row(), occurrence_id="screener-DEMO-0")
    assert a["id"] != b["id"]
    with pytest.raises(ValueError):
        present_us_candidate(row(), occurrence_id='bad" onclick="x')
