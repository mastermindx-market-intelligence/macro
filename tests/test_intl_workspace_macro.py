"""Focused contract tests for the supplied-field macro projection."""

import builtins
import copy
import json
import math
import os
import time

import pytest


def measure(**overrides):
    value = {
        "quality": "qualified", "reason": None, "metadata": "allowed",
        "value_permission": "allowed", "value": 0, "unit": "percent",
        "instrument": {"kind": "official_policy", "id": "deposit_facility", "market_id": "EZ"},
        "period": None, "observation_at": "2026-09-10", "calculation_at": None,
        "source_reference": "synthetic:ECBDFR:one", "evidence_key": "ez-policy-1",
    }
    value.update(overrides)
    return value


def components():
    return {
        "asof": "2026-09-10T09:00:00Z",
        "growth": [
            {"key": "gdp_trend", "score": 1.0, "weight": 1.0},
            {"key": "unemployment_trend", "score": 1.0, "weight": 1.0},
            {"key": "index_trend", "score": -1.0, "weight": 1.0},
            {"key": "global_growth", "score": None, "weight": 0.5},
        ],
        "inflation": [
            {"key": "cpi_direction", "score": 1.0, "weight": 1.5},
            {"key": "oil_trend", "score": None, "weight": 0.75},
            {"key": "yield_trend", "score": -1.0, "weight": 0.75},
        ],
        "growth_score": 0.25,
        "inflation_score": 0.0,
        "growth_n_components": 3,
        "inflation_n_components": 2,
    }


def cycle(**overrides):
    value = {
        "quality": "qualified", "reason": None, "metadata": "allowed", "value_permission": "allowed",
        "reported_quad": "Q1", "raw_quad": "Q1", "method_ref": "owner/economic-cycle@1",
        "method_kind": "economic_cycle", "asof": "2026-09-10T09:00:00Z",
        "components": components(), "economic_support": {
            "owner_ref": "owner/1", "decision_ref": "decision/1",
            "method_ref": "owner/economic-cycle@1", "asof": "2026-09-10T09:00:00Z",
            "dependency_keys": ["EZ.gdp_yoy", "EZ.cpi_yoy"],
            "component_keys": ["growth.gdp_trend", "inflation.cpi_direction", "inflation.yield_trend"],
            "heading_key": "goldilocks", "disagreement": False,
        },
    }
    value.update(overrides)
    return value


def inputs(**overrides):
    value = {
        "context": {"selected_market": "EZ", "horizon": "1y", "currency_basis": "local", "return_basis": "price"},
        "registry": {
            "markets": [{"market_id": "EZ", "name_en": "Euro Area", "name_zh": "欧元区"}, {"market_id": "JP", "name_en": "Japan", "name_zh": "日本"}],
            "horizons": ["1y"], "bases": ["local", "usd_unhedged"],
        },
        "measures": {
            "EZ.policy_rate": measure(),
            "EZ.gdp_yoy": measure(value=10**500, instrument={"kind": "macro_yoy", "id": "gdp", "market_id": "EZ"}, source_reference="synthetic:gdp", evidence_key="ez-gdp"),
            "EZ.cpi_yoy": measure(value=2, instrument={"kind": "macro_yoy", "id": "cpi", "market_id": "EZ"}, source_reference="synthetic:cpi", evidence_key="ez-cpi"),
        },
        "cycle_evidence": {"EZ": cycle()},
        "destinations": {
            "economic_cycle": {"key": "economic_cycle", "title_en": "Euro Area research", "title_zh": "欧元区研究", "destination": "/research/euro-area"},
            "realized_policy": {"key": "realized_policy", "title_en": "Policy evidence", "title_zh": "政策证据", "destination": "/research/policy"},
            "market_response": {"key": "market_response", "title_en": "Market response", "title_zh": "市场反应", "destination": None},
        },
    }
    value.update(overrides)
    return value


def build(value):
    from lib.intl_workspace_macro import build_macro_section
    return build_macro_section(**value)


def test_ecb_zero_with_missing_neighbors_detached():
    original = inputs(cycle_evidence={})
    value = copy.deepcopy(original)
    result = build(value)
    assert value == original
    assert result["market_rows"][0]["policy_rate"]["value"] == 0
    assert result["market_rows"][0]["yield_10y"] == {"field": "yield_10y", "quality": "unknown", "reason": "not_supplied"}
    assert result["coverage"]["unclassified"][1]["market_id"] == "JP"
    assert result["selected_reads"]["market_response"]["reason"] == "method_unsupported"


def test_hypothetical_economic_positive_uses_t1_shape():
    result = build(inputs())
    assert result["coverage"] == {"configured_ids": ["EZ", "JP"], "classified_ids": ["EZ"], "unclassified": [{"market_id": "JP", "reason": "not_supplied"}]}
    assert result["cycle_rows"][0]["supported_heading"] == "goldilocks"
    assert result["cycle_rows"][0]["method_kind"] == "economic_cycle"
    assert result["selected_reads"]["economic_cycle"] == {"title_key": "goldilocks", "destination": "/research/euro-area", "reason": None}


def test_incumbent_mixed_composite_withholds_heading():
    result = build(inputs(cycle_evidence={"EZ": cycle(method_ref="owner/mixed@7", method_kind="mixed_composite", economic_support=None)}))
    assert result["cycle_rows"][0]["reported_method_ref"] == "owner/mixed@7"
    assert result["cycle_rows"][0]["method_kind"] == "mixed_composite"
    assert result["cycle_rows"][0]["supported_heading"] is None
    assert result["coverage"]["unclassified"][0]["reason"] == "method_unsupported"


@pytest.mark.parametrize("mutate", [
    {"value": True}, {"value": "0"}, {"value": float("nan")},
    {"reason": "attacker text"}, {"evidence_key": None}, {"metadata": "denied"},
])
def test_invalid_claimed_qualified_shape(mutate):
    value = inputs()
    value["measures"]["EZ.policy_rate"].update(mutate)
    with pytest.raises(ValueError):
        build(value)


def test_identity_restrictions():
    value = inputs()
    value["measures"]["EZ.policy_rate"]["instrument"] = {"kind": "official_policy", "id": "DFF", "market_id": "EZ"}
    with pytest.raises(ValueError):
        build(value)
    value["measures"]["EZ.policy_rate"]["instrument"] = {"kind": "official_policy", "id": "deposit_facility", "market_id": "XM"}
    with pytest.raises(ValueError):
        build(value)


def test_denied_redaction_and_stale_signed_zero():
    value = inputs(cycle_evidence={})
    value["measures"]["EZ.cpi_yoy"] = {
        "quality": "stale", "reason": "source_stale", "metadata": "allowed", "value_permission": "allowed",
        "value": -0.0, "unit": "percent", "instrument": {"kind": "macro_yoy", "id": "cpi", "market_id": "EZ"},
        "period": None, "observation_at": "2026-01-01T00:00:00Z", "calculation_at": None,
        "source_reference": "synthetic:cpi", "evidence_key": "ez-cpi",
    }
    value["measures"]["JP.gdp_yoy"] = {
        "quality": "denied", "reason": "metadata_denied", "metadata": "denied", "value_permission": "denied",
        "value": 123, "unit": None, "instrument": None, "period": None, "observation_at": None,
        "calculation_at": None, "source_reference": None, "evidence_key": None,
    }
    result = build(value)
    assert math.copysign(1, result["market_rows"][0]["cpi_yoy"]["value"]) == -1
    assert result["market_rows"][0]["gdp_yoy"]["value"] == 10**500
    assert result["market_rows"][1]["gdp_yoy"] == {"field": "gdp_yoy", "quality": "denied", "reason": "metadata_denied"}


def test_method_disagreement_and_missing_dependency():
    disagree = cycle(economic_support={**cycle()["economic_support"], "disagreement": True})
    assert build(inputs(cycle_evidence={"EZ": disagree}))["cycle_rows"][0]["supported_heading"] is None
    value = inputs()
    del value["measures"]["EZ.gdp_yoy"]
    result = build(value)
    assert result["coverage"]["unclassified"][0]["reason"] == "cycle_support_missing"


def test_component_admission_requires_finite_native_score():
    value = inputs()
    value["cycle_evidence"]["EZ"]["economic_support"]["component_keys"] = ["growth.unknown"]
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["cycle_evidence"]["EZ"]["components"]["growth"][0]["score"] = float("inf")
    with pytest.raises(ValueError):
        build(value)


def test_period_basis_and_incompatible_timestamps():
    period = {"start": "2026-08-01", "end": "2026-09-01", "count": 20, "count_basis": "observations"}
    value = inputs()
    value["measures"]["EZ.yield_change"] = measure(value=-5, unit="bp", instrument={"kind": "yield_change", "id": "yield", "market_id": "EZ"}, period=period)
    assert build(value)["market_rows"][0]["yield_change"]["period"] == period
    incompatible = {**period, "end": "2026-09-01T00:00:00Z"}
    value["measures"]["EZ.yield_change"]["period"] = incompatible
    with pytest.raises(ValueError):
        build(value)
    value["measures"]["EZ.yield_change"]["period"] = {**period, "count": 20.0}
    with pytest.raises(ValueError):
        build(value)


def test_population_order_unknown_market_and_duplicate_ids():
    value = inputs()
    value["registry"]["markets"][1]["market_id"] = "EZ"
    with pytest.raises(ValueError):
        build(value)
    value = inputs(context={**inputs()["context"], "selected_market": "DE"})
    with pytest.raises(ValueError):
        build(value)
    assert [row["market_id"] for row in build(inputs())["market_rows"]] == ["EZ", "JP"]


def test_hostile_destination_and_extra_keys():
    value = inputs()
    value["context"]["extra"] = "forbidden"
    with pytest.raises(ValueError):
        build(value)
    for destination in ("https://example.test/research", "/research/../admin"):
        value = inputs()
        value["destinations"]["economic_cycle"]["destination"] = destination
        with pytest.raises(ValueError):
            build(value)


def test_no_mutation_io_or_clock_and_strict_json(monkeypatch):
    original = inputs()
    value = copy.deepcopy(original)
    def refuse(*args, **kwargs):
        raise AssertionError("unexpected external call")
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(time, "time", refuse)
    monkeypatch.setattr(os, "read", refuse, raising=False)
    result = build(value)
    assert value == original
    assert "secret" not in json.dumps(result, allow_nan=False)


def test_actual_owner_geometry_and_source_positive_fixture():
    result = build(inputs())
    native = result["cycle_rows"][0]["components"]
    assert [component["key"] for component in native["growth"]] == [
        "gdp_trend", "unemployment_trend", "index_trend", "global_growth"
    ]
    assert [component["weight"] for component in native["growth"]] == [1.0, 1.0, 1.0, 0.5]
    assert [component["key"] for component in native["inflation"]] == [
        "cpi_direction", "oil_trend", "yield_trend"
    ]
    assert [component["weight"] for component in native["inflation"]] == [1.5, 0.75, 0.75]
    assert native["growth_n_components"] == 3
    assert result["market_rows"][0]["policy_rate"] == {
        "field": "policy_rate", "quality": "qualified", "reason": None,
        "unit": "percent", "instrument": {
            "kind": "official_policy", "id": "deposit_facility", "market_id": "EZ"
        }, "period": None, "observation_at": "2026-09-10", "calculation_at": None,
        "source_reference": "synthetic:ECBDFR:one", "evidence_key": "ez-policy-1", "value": 0,
    }


@pytest.mark.parametrize("mutation", [
    "missing_gdp", "stale_gdp", "denied_gdp", "disagreement", "component_mismatch",
    "empty_components", "invented_geometry", "unknown_quad",
])
def test_selected_read_uses_same_heading_predicate(mutation):
    value = inputs()
    cycle = value["cycle_evidence"]["EZ"]
    if mutation == "missing_gdp":
        del value["measures"]["EZ.gdp_yoy"]
    elif mutation == "stale_gdp":
        value["measures"]["EZ.gdp_yoy"]["quality"] = "stale"
        value["measures"]["EZ.gdp_yoy"]["reason"] = "source_stale"
    elif mutation == "denied_gdp":
        value["measures"]["EZ.gdp_yoy"].update(
            quality="denied", reason="metadata_denied", metadata="denied",
            value_permission="denied", value=None, unit=None, instrument=None,
            period=None, observation_at=None, calculation_at=None,
            source_reference=None, evidence_key=None,
        )
    elif mutation == "disagreement":
        cycle["economic_support"]["disagreement"] = True
    elif mutation == "component_mismatch":
        cycle["raw_quad"] = "Q2"
    elif mutation == "empty_components":
        cycle["economic_support"]["component_keys"] = []
    else:
        cycle["components"]["growth"][0]["key"] = "pmi"
        if mutation == "unknown_quad":
            cycle["raw_quad"] = None
    result = build(value)
    assert result["cycle_rows"][0]["supported_heading"] is None
    assert result["selected_reads"]["economic_cycle"]["title_key"] != "goldilocks"
    assert result["coverage"]["classified_ids"] == []


@pytest.mark.parametrize("observation", [
    "2026X09Y10", "0000-01-01", "2026-13-01", "2026-09-10T00:00:00Zextra",
])
def test_strict_real_observation_dates(observation):
    value = inputs(cycle_evidence={})
    value["measures"]["EZ.policy_rate"]["observation_at"] = observation
    with pytest.raises(ValueError):
        build(value)


def test_strict_month_and_nanosecond_interval_chronology():
    value = inputs(cycle_evidence={})
    period = {
        "start": "2026-08-01T00:00:00.000000100Z",
        "end": "2026-08-01T00:00:00.000000200Z",
        "count": 1, "count_basis": "release_periods",
    }
    value["measures"]["EZ.yield_change"] = measure(
        value=1, unit="bp", instrument={"kind": "yield_change", "id": "yield", "market_id": "EZ"},
        period=period,
    )
    assert build(value)["market_rows"][0]["yield_change"]["period"] == period
    for start, end in (
        ("2026-13", "2026-14"),
        ("2026-08-01T00:00:00Z", "2026-08-01T00:00:00+00:00"),
        ("2026-08-01T00:00:00.000000200Z", "2026-08-01T00:00:00.000000100Z"),
    ):
        value["measures"]["EZ.yield_change"]["period"] = {**period, "start": start, "end": end}
        with pytest.raises(ValueError):
            build(value)


def test_cycle_quality_and_nullable_native_counts():
    value = inputs()
    value["cycle_evidence"]["EZ"].update(
        method_kind="mixed_composite", economic_support=None,
        asof="2024-06-28T00:00:00.000000123+00:00",
    )
    value["cycle_evidence"]["EZ"]["components"]["asof"] = value["cycle_evidence"]["EZ"]["asof"]
    value["cycle_evidence"]["EZ"]["components"]["growth_n_components"] = None
    result = build(value)
    assert result["cycle_rows"][0]["components"]["asof"] == "2024-06-28T00:00:00.000000123+00:00"
    assert result["cycle_rows"][0]["components"]["growth_n_components"] is None
    assert result["selected_reads"]["economic_cycle"]["reason"] == "method_unsupported"

    value["cycle_evidence"]["EZ"].update(quality="unknown", reason="source_unknown", economic_support=None)
    result = build(value)
    assert result["cycle_rows"] == []
    assert result["selected_reads"]["economic_cycle"] == {
        "title_key": "source_unknown", "destination": None, "reason": "source_unknown"
    }


def test_partial_safe_destinations_and_exact_entry_keys():
    value = inputs()
    value["destinations"]["economic_cycle"]["destination"] = "#intl-growth-inflation"
    result = build(value)
    assert result["selected_reads"]["economic_cycle"]["destination"] == "#intl-growth-inflation"
    assert result["selected_reads"]["realized_policy"]["reason"] is None
    assert result["deep_research"][0]["destination"] == "#intl-growth-inflation"

    value["destinations"] = {}
    assert build(value)["deep_research"] == []

    value = inputs(destinations={
        "economic_cycle": inputs()["destinations"]["economic_cycle"],
    })
    value["destinations"]["economic_cycle"]["destination"] = None
    result = build(value)
    assert result["selected_reads"]["realized_policy"]["reason"] == "target_unavailable"

    value = inputs()
    value["destinations"]["wrong-map-key"] = value["destinations"]["economic_cycle"]
    with pytest.raises(ValueError):
        build(value)

    for destination in ("//example.test", "/a/%2e%2e", "/a\\b", "#bad fragment"):
        value = inputs()
        value["destinations"]["economic_cycle"]["destination"] = destination
        with pytest.raises(ValueError):
            build(value)


def test_builtin_containers_recursive_exact_shapes():
    value = inputs()
    value["measures"] = []
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["cycle_evidence"] = []
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["destinations"] = []
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["cycle_evidence"]["EZ"]["components"]["growth"] = {}
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["cycle_evidence"]["EZ"]["economic_support"]["dependency_keys"] = (
        "EZ.gdp_yoy", "EZ.cpi_yoy"
    )
    with pytest.raises(ValueError):
        build(value)
    value = inputs()
    value["cycle_evidence"]["EZ"]["components"]["growth"] = iter([])
    with pytest.raises(ValueError):
        build(value)


@pytest.mark.parametrize('offset', ['+24:00', '+00:60', '-99:99'])
def test_parent_invalid_timezone_offset(offset):
    packet = inputs(cycle_evidence={})
    packet['measures']['EZ.policy_rate']['observation_at'] = '2026-09-10T00:00:00' + offset
    with pytest.raises(ValueError):
        build(packet)


def test_parent_native_naive_timestamp_preserved():
    packet = inputs()
    timestamp = '2026-09-10T00:00:00.000000001'
    cycle_value = packet['cycle_evidence']['EZ']
    cycle_value['asof'] = cycle_value['components']['asof'] = cycle_value['economic_support']['asof'] = timestamp
    result = build(packet)
    assert result['cycle_rows'][0]['components']['asof'] == timestamp
    assert result['selected_reads']['economic_cycle']['title_key'] == 'goldilocks'


def test_parent_catalogue_keys_and_matched_destinations():
    packet = inputs(destinations={
        'intl-growth-inflation': {'key': 'intl-growth-inflation', 'title_en': 'Cycle', 'title_zh': '周期', 'destination': '#intl-growth-inflation'}
    })
    assert build(packet)['deep_research'][0]['key'] == 'intl-growth-inflation'
    packet = inputs()
    packet['destinations']['economic_cycle']['key'] = 'realized_policy'
    packet['destinations']['realized_policy']['key'] = 'economic_cycle'
    with pytest.raises(ValueError):
        build(packet)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), True, '2', {'secret': 1}])
def test_parent_stale_value_is_finite_scalar(bad):
    packet = inputs(cycle_evidence={})
    packet['measures']['EZ.policy_rate'].update(quality='stale', reason='source_stale', value=bad)
    with pytest.raises(ValueError):
        build(packet)


def test_parent_denied_metadata_is_projected_safely():
    packet = inputs(cycle_evidence={})
    packet['measures']['EZ.policy_rate'].update(quality='denied', reason='metadata_denied', metadata='denied', value_permission='denied')
    assert build(packet)['market_rows'][0]['policy_rate'] == {'field': 'policy_rate', 'quality': 'denied', 'reason': 'metadata_denied'}


@pytest.mark.parametrize('field,value', [('horizon', []), ('currency_basis', {}), ('return_basis', [])])
def test_parent_bad_context_fails_valueerror(field, value):
    packet = inputs(); packet['context'][field] = value
    with pytest.raises(ValueError):
        build(packet)


def test_parent_qualified_unit_and_change_period_required():
    packet = inputs(cycle_evidence={}); packet['measures']['EZ.policy_rate']['unit'] = None
    with pytest.raises(ValueError):
        build(packet)
    packet = inputs(cycle_evidence={})
    packet['measures']['EZ.yield_change'] = measure(value=1, unit='bp', instrument={'kind': 'yield_change', 'id': '10y', 'market_id': 'EZ'})
    with pytest.raises(ValueError):
        build(packet)


def test_parent_registry_order_does_not_change_dependency_eligibility():
    packet = inputs()
    packet['measures']['JP.gdp_yoy'] = measure(value=1, instrument={'kind': 'macro_yoy', 'id': 'gdp', 'market_id': 'JP'})
    packet['cycle_evidence']['EZ']['economic_support']['dependency_keys'].append('JP.gdp_yoy')
    first = build(packet)
    packet['registry']['markets'].reverse()
    second = build(packet)
    assert first['coverage']['classified_ids'] == second['coverage']['classified_ids'] == ['EZ']
    assert first['selected_reads'] == second['selected_reads']
