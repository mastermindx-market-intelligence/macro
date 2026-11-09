"""Contract-focused R4 checks: missing data, temporal honesty, and authority."""
from copy import deepcopy
from datetime import date, timedelta
import json

import pytest

from lib.crypto_intelligence_view import build_view, iso_day, price_history, prior_close_range


def inputs(days=91):
    dates = [str(date(2026, 7, 19) + timedelta(days=i)) for i in range(days)]
    as_of = dates[-1]
    prices = [80000.0 + i * 10 for i in range(days)]
    cockpit = {
        "schema": "crypto.cockpit/v1", "as_of": as_of,
        "hero": {"asset": "BTC-USD", "price": prices[-1], "change_24h_pct": 0.1},
        "decision": {"schema": "btc.decision/v1", "status": "ok", "integrity_ok": True,
                     "as_of": as_of, "final_exposure_pct": 41,
                     "authority_source": "btc.decision/v1.final.exposure_pct"},
        "axes": [
            {"id": "macro_backdrop", "primary": {"state_en": "Headwind", "state_zh": "逆风", "tone": "bear"}},
            {"id": "liquidity_flows", "primary": {"state_en": "Expanding", "state_zh": "扩张", "tone": "bull"}},
        ],
    }
    class_state = {
        "schema": "crypto.class_state/v1", "as_of": dates[-3],
        "market": {"total_state": "Rising"},
        "universe_coverage": {"breadth": {"as_of": dates[-3], "available": False, "value": None, "eligible": 3, "required": 10}},
        "flow_kinds": {"etf": {"observation": "stale"}, "stablecoins": {"observation": "stale"}},
    }
    assets = {"schema": "crypto.asset_states/v1", "as_of": dates[-3], "assets": {
        "ETH": {"price": 2400.0, "as_of": dates[-3], "coverage": {"available": True},
                "change_30d_pct": 0.0, "trend": {"state": "Advancing"},
                "risk": {"state": "Stressed"}, "relative": {"state": "Tracking Bitcoin", "change_90d_pct": 0.0}}
    }}
    chart = {"schema": "mastermind.vector_risk_strategy.v2", "valid": True, "dates": dates, "price": prices}
    return cockpit, class_state, assets, chart


def test_current_contracts_preserve_model_and_qualify_conditions():
    view = build_view(*inputs())
    assert view["model"]["exposure_pct"] == 41
    assert view["levels"]["available"]
    assert view["scenarios"]["7"][0]["probability"] is None
    assert all(s["authority"] == "conditional_research_only" for s in view["scenarios"]["7"])
    assert view["limitations"]["source_dates_differ"]


def test_range_excludes_current_close():
    values = inputs()
    values[3]["price"][-1] = 999999.0
    values[0]["hero"]["price"] = 999999.0
    view = build_view(*values)
    assert view["levels"]["high"] == values[3]["price"][-2]
    assert view["levels"]["current"] == 999999.0


@pytest.mark.parametrize("break_type", ["null", "zero", "gap"])
def test_latest_segment_never_bridges_missing_observations(break_type):
    cockpit, _, _, chart = inputs()
    if break_type == "gap":
        del chart["dates"][-11]
        del chart["price"][-11]
    else:
        chart["price"][-11] = None if break_type == "null" else 0
    history = price_history(chart, cockpit["as_of"])
    assert history["gaps"]
    assert len(history["dates"]) == 10
    assert not prior_close_range(history, 20)["available"]


@pytest.mark.parametrize("kind", ["duplicate", "descending", "future", "ragged", "nondate"])
def test_invalid_chart_structure_fails_closed(kind):
    cockpit, _, _, chart = inputs()
    if kind == "duplicate":
        chart["dates"][-1] = chart["dates"][-2]
    elif kind == "descending":
        chart["dates"][-2:] = chart["dates"][-2:][::-1]
    elif kind == "future":
        chart["dates"][-1] = "2099-01-01"
    elif kind == "ragged":
        chart["price"].pop()
    else:
        chart["dates"][-1] = "20261017"
    assert price_history(chart, cockpit["as_of"])["state"] == "unavailable"


def test_stale_chart_is_distinct_and_does_not_create_current_conditions():
    args = inputs()
    args[3]["dates"].pop()
    args[3]["price"].pop()
    view = build_view(*args)
    assert view["history"]["state"] == "stale"
    assert not view["scenarios"]["7"]


def test_short_history_has_chart_but_no_invented_range():
    view = build_view(*inputs(10))
    assert view["history"]["state"] == "ready"
    assert not view["levels"]["available"]
    assert not view["scenarios"]["7"]
    assert view["btc_headline_en"] == "Price evidence incomplete"


def test_price_basis_divergence_is_disclosed_without_destroying_valid_chart():
    args = inputs()
    args[0]["hero"]["price"] += 15.85
    view = build_view(*args)
    assert view["history"]["state"] == "ready"
    assert view["limitations"]["price_basis_divergence"]
    assert view["price"] == args[3]["price"][-1]


def test_stale_flows_and_undated_axes_never_acquire_fresh_source_dates():
    view = build_view(*inputs())
    rows = {r["id"]: r for r in view["families"]}
    assert rows["liquidity_flows"]["quality"] == "stale"
    assert rows["liquidity_flows"]["as_of"] is None
    assert rows["macro_backdrop"]["quality"] == "snapshot_only"
    assert rows["macro_backdrop"]["as_of"] is None
    assert rows["macro_backdrop"]["snapshot_as_of"] == view["as_of"]


def test_missing_class_contract_does_not_confirm_flow_freshness():
    args = inputs()
    args[1]["schema"] = "unexpected/v1"
    view = build_view(*args)
    assert view["contracts"]["class_state"] == "missing_or_schema_mismatch"
    flow = next(r for r in view["families"] if r["id"] == "liquidity_flows")
    assert flow["quality"] == "missing"


def test_zero_is_retained_but_failed_coverage_suppresses_direction():
    args = inputs()
    view = build_view(*args)
    assert view["assets"][0]["relative_90d_pct"] == 0
    assert view["assets"][0]["change_30d_pct"] == 0
    args[2]["assets"]["ETH"]["coverage"]["available"] = False
    view = build_view(*args)
    assert view["assets"][0]["relative_90d_pct"] is None
    assert view["assets"][0]["trend_en"] == "Unavailable"


def test_missing_breadth_denominator_is_not_invented():
    args = inputs()
    args[1]["universe_coverage"]["breadth"] = {"eligible": None, "available": True, "value": None}
    row = next(r for r in build_view(*args)["families"] if r["id"] == "participation")
    assert row["quality"] == "insufficient"
    assert row["members"][0]["state_en"] == "Coverage not supplied"


def test_falling_market_is_not_rewritten_as_no_direction():
    args = inputs()
    args[1]["market"]["total_state"] = "Falling"
    assert build_view(*args)["market_headline_en"] == "Market value is falling"


def test_invalid_date_or_wrong_asset_cannot_emit_bitcoin_conditions():
    args = inputs()
    args[0]["as_of"] = "not a date"
    assert build_view(*args)["scenarios"] == {"7": [], "30": []}
    args = inputs()
    args[0]["hero"]["asset"] = "ETH-USD"
    assert build_view(*args)["history"]["state"] == "asset_unverified"


@pytest.mark.parametrize("date_string", ["20261017", "2026-10-17T00:00:00", None, "2026-02-30"])
def test_iso_day_has_one_explicit_format(date_string):
    assert iso_day(date_string) is None


@pytest.mark.parametrize("damage", ["integrity", "scope", "nonfinite", "out_of_range"])
def test_model_authority_rejects_invalid_projection(damage):
    args = inputs()
    decision = args[0]["decision"]
    if damage == "integrity":
        decision["integrity_ok"] = False
    elif damage == "scope":
        decision["authority_source"] = "a different model"
    elif damage == "nonfinite":
        decision["final_exposure_pct"] = float("nan")
    else:
        decision["final_exposure_pct"] = 101
    assert build_view(*args)["model"]["exposure_pct"] is None


def test_projection_does_not_mutate_source_contracts():
    args = inputs()
    original = deepcopy(args)
    build_view(*args)
    assert args == original


@pytest.mark.parametrize("value,ready", [(None, False), (float("nan"), False), (0.0, True)])
def test_breadth_flag_without_measurement_does_not_confirm_participation(value, ready):
    values = inputs()
    values[1]["universe_coverage"]["breadth"].update(available=True, value=value)
    view = build_view(*values)
    assert view["limitations"]["broad_participation"] is (not ready)
    assert (view["market_headline_en"] == "Market value is rising") is ready
    family = next(f for f in view["families"] if f["id"] == "participation")
    assert (family["quality"] == "observed") is ready


@pytest.mark.parametrize("position,last,key", [
    ("below", 1.0, "failure"), ("above", 999999.0, "continuation"),
])
def test_visible_progress_matches_current_price_without_confirming_demand(position, last, key):
    args = inputs()
    args[3]["price"][-1] = last
    args[0]["hero"]["price"] = last
    view = build_view(*args)
    assert view["levels"]["position"] == position
    for horizon in ("7", "30"):
        cases = {s["id"]: s for s in view["scenarios"][horizon]}
        assert cases[key]["progress_state"] == "price_met"
        assert "demand unconfirmed" in cases[key]["progress_en"]
        assert cases["range"]["progress_state"] == "challenged"
        assert "between" in cases["range"]["next_check_en"]
        assert f'{cases["range"]["levels"]["low"]:,.2f}' in cases["range"]["next_check_en"]
        assert f'{cases["range"]["levels"]["high"]:,.2f}' in cases["range"]["next_check_en"]
        assert all(s["probability"] is None for s in cases.values())
    assert view["headline_en"] != view["market_headline_en"]


@pytest.mark.parametrize("boundary", ["low", "high"])
def test_equal_range_boundary_is_inside_not_a_directional_break(boundary):
    args = inputs()
    prior = args[3]["price"][-21:-1]
    args[3]["price"][-1] = min(prior) if boundary == "low" else max(prior)
    args[0]["hero"]["price"] = args[3]["price"][-1]
    cases = {s["id"]: s for s in build_view(*args)["scenarios"]["7"]}
    assert cases["range"]["progress_state"] == "inside"
    assert "persistence unproven" in cases["range"]["progress_en"]
    assert cases["failure"]["progress_state"] == "waiting"
    assert cases["continuation"]["progress_state"] == "waiting"


def test_shorter_and_longer_outlook_can_have_different_observed_positions():
    args = inputs()
    args[3]["price"][-1] = args[3]["price"][-21] - 1
    args[0]["hero"]["price"] = args[3]["price"][-1]
    view = build_view(*args)
    short = {s["id"]: s for s in view["scenarios"]["7"]}
    long = {s["id"]: s for s in view["scenarios"]["30"]}
    assert short["failure"]["progress_state"] == "price_met"
    assert long["range"]["progress_state"] == "inside"
    assert short["failure"]["levels"]["lookback_days"] == 20
    assert long["range"]["levels"]["lookback_days"] == 60


def test_r4_preview_builder_never_overwrites_legacy_routes(tmp_path):
    import json
    from scripts.build_crypto_intelligence_r4 import INPUTS, build as build_candidate

    for name, payload in zip(INPUTS, inputs()):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    for name in ("crypto.html", "vector.html"):
        (tmp_path / name).write_text("LEGACY_ROUTE_SENTINEL", encoding="utf-8")
    result = build_candidate(tmp_path, tmp_path)
    assert result["production_routes_replaced"] is False
    assert (tmp_path / "crypto-r4.html").exists()
    assert (tmp_path / "vector-r4.html").exists()
    assert (tmp_path / "crypto_intelligence_r4.json").exists()
    for name in ("crypto.html", "vector.html"):
        assert (tmp_path / name).read_text(encoding="utf-8") == "LEGACY_ROUTE_SENTINEL"


def test_shadow_hook_refreshes_preview_after_legacy_build(tmp_path, monkeypatch):
    from scripts import build_crypto as legacy, build_crypto_intelligence_r4 as candidate

    calls = []
    monkeypatch.setattr(candidate, "build", lambda site, source: (
        calls.append((site, source)) or
        {"as_of": "2026-10-17", "market_as_of": "2026-10-15", "production_routes_replaced": False}
    ))
    legacy._build_r4_shadow(tmp_path)
    assert calls == [(tmp_path, tmp_path)]


def test_shadow_failure_does_not_break_existing_crypto_render(tmp_path, monkeypatch, caplog):
    from scripts import build_crypto as legacy, build_crypto_intelligence_r4 as candidate

    def fail(_site, _source):
        raise RuntimeError("preview-only failure")

    monkeypatch.setattr(candidate, "build", fail)
    legacy._build_r4_shadow(tmp_path)
    assert "existing production routes preserved" in caplog.text


# Projection integrity: these are synthetic contracts, not observed market inputs.
def relative_integrity_inputs():
    args = inputs()
    base = deepcopy(args[2]["assets"]["ETH"])
    base["trend"]["state_zh"] = "上行"
    base["risk"]["state_zh"] = "承压"
    states = [
        ("ETH", float("inf"), "Leading Bitcoin", "领先比特币"),
        ("SOL", 0.0, "Tracking Bitcoin", "跟随比特币"),
        ("BTC", None, "Building history", "领先比特币"),
        ("XRP", 10.0, "Leading Bitcoin", "领先比特币"),
    ]
    args[2]["assets"] = {}
    for symbol, value, state, state_zh in states:
        item = deepcopy(base)
        item["relative"] = {"change_90d_pct": value, "state": state, "state_zh": state_zh}
        args[2]["assets"][symbol] = item
    return args


@pytest.mark.parametrize("kind,state,state_zh", [
    ("missing", "Leading Bitcoin", "领先比特币"),
    ("null", "Lagging Bitcoin", "落后比特币"),
    ("true", "Tracking Bitcoin", "跟随比特币"),
    ("false", "Leading Bitcoin", "积累历史中"),
    ("nan", "Tracking Bitcoin", "领先比特币"),
    ("positive_infinity", "Leading Bitcoin", "领先比特币"),
    ("negative_infinity", "Lagging Bitcoin", "落后比特币"),
    ("numeric_string", "Leading Bitcoin", "领先比特币"),
])
def test_relative_integrity_unavailable_value_cannot_retain_direction(kind, state, state_zh):
    args = inputs()
    baseline = build_view(*args)
    relative = {"state": state, "state_zh": state_zh}
    values = {"null": None, "true": True, "false": False, "nan": float("nan"),
              "positive_infinity": float("inf"), "negative_infinity": float("-inf"), "numeric_string": "0"}
    if kind != "missing":
        relative["change_90d_pct"] = values[kind]
    args[2]["assets"]["ETH"]["relative"] = relative
    view = build_view(*args)
    asset = view["assets"][0]
    assert asset["relative_90d_pct"] is None
    assert (asset["relative_en"], asset["relative_zh"]) == ("Unavailable", "暂无")
    # Relative qualification does not remove the asset or its independent evidence.
    keys = {"relative_90d_pct", "relative_en", "relative_zh"}
    assert {k: v for k, v in asset.items() if k not in keys} == {
        k: v for k, v in baseline["assets"][0].items() if k not in keys
    }
    assert {k: v for k, v in view.items() if k != "assets"} == {
        k: v for k, v in baseline.items() if k != "assets"
    }
    assert relative["state"] == state and relative["state_zh"] == state_zh


@pytest.mark.parametrize("value,state,state_zh", [
    (0, "Tracking Bitcoin", "跟随比特币"),
    (0.0, "Tracking Bitcoin", "跟随比特币"),
    (-0.0, "Tracking Bitcoin", "跟随比特币"),
    (8.5, "Leading Bitcoin", "领先比特币"),
    (-8.5, "Lagging Bitcoin", "落后比特币"),
])
def test_relative_integrity_finite_readings_keep_supplied_value_and_state(value, state, state_zh):
    args = inputs()
    args[2]["assets"]["ETH"]["relative"] = {
        "change_90d_pct": value, "state": state, "state_zh": state_zh
    }
    source = deepcopy(args)
    asset = build_view(*args)["assets"][0]
    assert asset["relative_90d_pct"] == value and asset["relative_90d_pct"] is not None
    assert (asset["relative_en"], asset["relative_zh"]) == (state, state_zh)
    assert asset["change_30d_pct"] == 0.0 and asset["available"] is True
    assert args == source


@pytest.mark.parametrize("state,state_zh,expected", [
    ("Building history", "积累历史中", ("Building history", "积累历史中")),
    ("Building history", None, ("Building history", "积累历史中")),
    ("Building history", "领先比特币", ("Building history", "积累历史中")),
    ("Leading Bitcoin", "积累历史中", ("Unavailable", "暂无")),
    ("building history", "积累历史中", ("Unavailable", "暂无")),
])
def test_relative_integrity_null_history_has_one_bilingual_meaning(state, state_zh, expected):
    args = inputs()
    args[2]["assets"]["ETH"]["relative"] = {"state": state, "state_zh": state_zh}
    source = deepcopy(args)
    asset = build_view(*args)["assets"][0]
    assert asset["relative_90d_pct"] is None
    assert (asset["relative_en"], asset["relative_zh"]) == expected
    assert asset["available"] is True and args == source


@pytest.mark.parametrize("damage", ["coverage", "invalid_date", "future_date"])
@pytest.mark.parametrize("value,state", [(None, "Building history"), (0.0, "Tracking Bitcoin")])
def test_relative_integrity_existing_eligibility_precedes_history_or_zero(damage, value, state):
    args = inputs()
    item = args[2]["assets"]["ETH"]
    item["relative"] = {"change_90d_pct": value, "state": state, "state_zh": "积累历史中"}
    if damage == "coverage":
        item["coverage"]["available"] = False
    elif damage == "invalid_date":
        item["as_of"] = "2026-02-30"
    else:
        item["as_of"] = "2099-01-01"
    source = deepcopy(args)
    asset = build_view(*args)["assets"][0]
    assert asset["available"] is False
    assert asset["relative_90d_pct"] is None
    assert (asset["relative_en"], asset["relative_zh"]) == ("Unavailable", "暂无")
    assert asset["symbol"] == "ETH" and args == source


@pytest.mark.parametrize("relative", [None, [], "Leading Bitcoin", True])
def test_relative_integrity_malformed_optional_container_preserves_asset(relative):
    args = inputs()
    args[2]["assets"]["ETH"]["relative"] = relative
    source = deepcopy(args)
    asset = build_view(*args)["assets"][0]
    assert asset["relative_90d_pct"] is None
    assert (asset["relative_en"], asset["relative_zh"]) == ("Unavailable", "暂无")
    assert asset["available"] is True and asset["price"] == 2400.0
    assert args == source


# Quote validity is independent of comparison/risk availability.
@pytest.mark.parametrize("kind", [
    "missing", "null", "zero", "negative_zero", "negative", "true", "false",
    "nan", "positive_infinity", "negative_infinity", "numeric_string", "mapping", "list",
])
def test_quote_clarity_invalid_price_preserves_other_asset_evidence(kind):
    args = inputs()
    baseline = build_view(*args)
    item = args[2]["assets"]["ETH"]
    values = {"null": None, "zero": 0, "negative_zero": -0.0, "negative": -1.0,
              "true": True, "false": False, "nan": float("nan"),
              "positive_infinity": float("inf"), "negative_infinity": float("-inf"),
              "numeric_string": "0.001", "mapping": {}, "list": []}
    if kind == "missing":
        item.pop("price")
    else:
        item["price"] = values[kind]
    view = build_view(*args)
    asset = view["assets"][0]
    assert asset["price"] is None
    assert {k: v for k, v in asset.items() if k != "price"} == {
        k: v for k, v in baseline["assets"][0].items() if k != "price"
    }
    assert {k: v for k, v in view.items() if k != "assets"} == {
        k: v for k, v in baseline.items() if k != "assets"
    }
    assert asset["relative_90d_pct"] == 0.0 and asset["change_30d_pct"] == 0.0
    assert ("price" not in item) if kind == "missing" else item["price"] is values[kind]


@pytest.mark.parametrize("value", [5e-324, 0.00000001, 0.001, 104.19, 2413.2])
def test_quote_clarity_positive_price_remains_a_supplied_number(value):
    args = inputs()
    args[2]["assets"]["ETH"]["price"] = value
    source = deepcopy(args)
    asset = build_view(*args)["assets"][0]
    assert asset["price"] == value and asset["price"] > 0
    assert asset["available"] is True and args == source


@pytest.mark.parametrize("value,expected", [
    (None, "Unavailable暂无"), (0, "Unavailable暂无"), (-1, "Unavailable暂无"),
    (5e-324, "<$0.00000001"), (0.000000009, "<$0.00000001"),
    (0.00000001, "$0.00000001"), (0.000000015, "$0.00000002"),
    (0.000000025, "$0.00000003"), (0.000123455, "$0.00012346"),
    (0.001, "$0.001"), (0.009999994, "$0.00999999"),
    (0.009999995, "$0.01"), (0.01, "$0.01"),
    (104.19, "$104.19"), (2413.2, "$2,413"),
])
def test_quote_clarity_server_price_cell_is_explicit_and_never_false_zero(tmp_path, value, expected):
    from html.parser import HTMLParser
    from scripts.build_crypto_intelligence_r4 import render_view

    class PriceCells(HTMLParser):
        def __init__(self):
            super().__init__()
            self.active = False
            self.parts = []
            self.cells = []

        def handle_starttag(self, tag, attrs):
            if tag == "td" and dict(attrs).get("data-label") == "Price":
                self.active = True
                self.parts = []

        def handle_data(self, data):
            if self.active:
                self.parts.append(data)

        def handle_endtag(self, tag):
            if tag == "td" and self.active:
                self.cells.append("".join(self.parts))
                self.active = False

    view = build_view(*inputs())
    # Exercise the server consumer of a retained view as well as projection output.
    view["assets"][0]["price"] = value
    view["history"]["state"] = "unavailable"
    render_view(view, tmp_path)
    markup = (tmp_path / "crypto-r4.html").read_text()
    parser = PriceCells()
    parser.feed(markup)
    assert parser.cells == [expected]
    if expected.startswith("<"):
        assert "&lt;$0.00000001" in markup
    assert json.loads((tmp_path / "crypto_intelligence_r4.json").read_text())["assets"][0]["price"] == value


def quote_clarity_inputs(variant):
    args = relative_integrity_inputs()
    if variant == "quote-invalid":
        prices = {"ETH": 0, "SOL": 104.19, "BTC": -1, "XRP": 2413.2}
    elif variant == "quote-small":
        prices = {"ETH": 0.001, "SOL": 0.000000009, "BTC": 0.000000015,
                  "XRP": 0.000000025, "EDGE": 0.009999995}
        args[2]["assets"]["EDGE"] = deepcopy(args[2]["assets"]["XRP"])
    else:
        raise AssertionError(variant)
    for symbol, price in prices.items():
        args[2]["assets"][symbol]["price"] = price
    return args


@pytest.mark.parametrize("precision,trap_rounding", [(2, True), (28, False)])
def test_quote_clarity_formatting_is_independent_of_caller_decimal_context(precision, trap_rounding):
    from decimal import Inexact, Rounded, ROUND_DOWN, localcontext
    from scripts.build_crypto_intelligence_r4 import asset_money

    with localcontext() as context:
        context.prec = precision
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = trap_rounding
        context.traps[Rounded] = trap_rounding
        context.clear_flags()
        before = (context.prec, context.rounding, dict(context.traps), dict(context.flags))
        assert asset_money(0.000123455) == "$0.00012346"
        assert (context.prec, context.rounding, dict(context.traps), dict(context.flags)) == before
