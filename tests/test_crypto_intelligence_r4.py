"""Contract-focused R4 checks: missing data, temporal honesty, and authority."""
from copy import deepcopy
from datetime import date, timedelta

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
    assert build_view(*args)["headline_en"] == "Market value is falling"


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
    assert (view["headline_en"] == "Market value is rising") is ready
    family = next(f for f in view["families"] if f["id"] == "participation")
    assert (family["quality"] == "observed") is ready
