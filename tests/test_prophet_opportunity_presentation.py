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
    assert v["assessment_asof"] is None
    assert v["signal_asof"] == "2026-09-25"
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


def test_original_missing_reason_is_retained_without_becoming_bearish():
    source = row(); source["entry_signal"] = None
    source["entry_signal_null_reason"] = "lane_not_stamped"
    v = present(source)
    assert v["assessment_missing_reason"] == "lane_not_stamped"
    assert v["stance"] == "unknown"


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


def test_v3_score_explains_actual_family_basis_without_recomputing_it():
    source = row(); source['prophet'] = {'version': 'us_prophet_v3', 'score': 41.7,
        'fusion': {'definition': 'us_prophet_v3', 'families_active': ['F1_TECHNICAL_CONFLUENCE', 'F4_CATALYST_EVENT'],
                   'family_contribution': {'F1_TECHNICAL_CONFLUENCE': 0, 'F4_CATALYST_EVENT': 83.4},
                   'families_abstaining': ['F7_QUALITY_FUNDAMENTAL']}}
    original = deepcopy(source)
    v = present(source)
    assert 'evidence-family' in v['priority']['meaning']['en']
    assert v['priority']['value'] == '42'
    assert [f['value'] for f in v['evidence_profile']['scores']] == [0, 83.4]
    assert v['evidence_profile']['abstaining'][0]['en'] == 'Business quality'
    assert source == original
    for bad in (True, -1, 101, float('nan')):
        source['prophet']['fusion']['family_contribution']['F4_CATALYST_EVENT'] = bad
        assert present(source)['evidence_profile'] is None
    source = original; source['prophet']['version'] = 'us_prophet_v2_fallback'
    assert present(source)['evidence_profile'] is None
    assert 'evidence-family' not in present(source)['priority']['meaning']['en']


def test_published_assessment_is_preserved_as_text_not_regenerated_from_price():
    source = row(); source['entry_signal'].update(action='Wait for weekly confirmation.', action_zh='等待周线确认。')
    v = present(source)
    assert v['assessment_detail'] == {'en': 'Wait for weekly confirmation.', 'zh': '等待周线确认。'}
    assert v['assessment_asof'] is None


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
    chart = present(source)["chart"]
    points = chart["points"]
    assert len(points) == count
    assert points[0]["x"] == 0 and points[-1]["x"] == 100
    assert all(0 <= p["y"] <= 100 for p in points)
    if count > 2:
        assert len(chart["zone_edges"]) == 2
        assert (chart["zone_fill"] is not None) == (zone_state == "active")
        assert chart["zone_edges"][0]["x1"] == 60


def test_chart_color_is_published_tape_not_assessment_color():
    source = row()
    source["spark_svg"] = source["spark_svg"].replace('fill="none"', 'fill="none" stroke="var(--down)"')
    v = present(source)
    assert v["stance"] == "buy" and v["chart"]["direction"] == "down"


def test_mark_explanation_and_membership_date_survive_display():
    source = row(); source["added_date"] = "2026-09-01"
    v = present(source, marks=[{"en": "Blow-off risk", "zh": "冲顶风险",
                              "tip_en": "Measured context, not a sell signal."}])
    assert v["marks"][0]["explanation"]["en"] == "Measured context, not a sell signal."
    assert v["added_date"] == "2026-09-01"


@pytest.mark.parametrize("bad", ["2026-9-1", "2026-02-30", "2026-10-01T12:00:00Z", "not-a-date", 1])
def test_membership_date_cannot_be_a_malformed_or_different_clock(bad):
    source = row(); source["added_date"] = bad
    assert present(source)["added_date"] is None


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


def test_context_uses_bound_theme_and_existing_resolver_without_changing_assessment():
    source = row()
    before = present(source)
    source['theme'] = {'id': 'ai_infra', 'name': 'AI infrastructure', 'name_zh': '人工智能基础设施'}
    original = deepcopy(source)
    after = present(source)
    assert after['context'] == {'href': '/baskets.html#theme-ai_infra',
        'label': {'en': 'AI infrastructure · Explore context', 'zh': '人工智能基础设施 · 探索背景'}}
    assert {k: v for k, v in after.items() if k != 'context'} == {k: v for k, v in before.items() if k != 'context'}
    assert source == original
    assert present(source, context={})['context'] is None
    assert present(source, context={'href': '//external.test', 'en': 'Bad'})['context'] is None


@pytest.mark.parametrize('theme', [None, 'ai_infra', {}, {'name': 'Name only'},
    {'id': 'ai_infra'}, {'id': '../ai_infra', 'name': 'Unsafe'},
    {'id': 'ai_infra?x=y', 'name': 'Unsafe'}, {'id': 'ai_infra#x', 'name': 'Unsafe'}])
def test_missing_or_unsafe_bound_theme_does_not_gain_a_context_link(theme):
    source = row(); source['theme'] = theme
    assert present(source)['context'] is None


@pytest.mark.parametrize("status", ["watch", "wait_pullback", "bounce_wait"])
def test_native_wait_states_are_named_without_becoming_unknown(status):
    source = row(); source["entry_signal"]["status"] = status
    v = present(source)
    assert v["stance"] == "wait"
    assert v["stance_label"]["en"] != "Assessment unavailable"
