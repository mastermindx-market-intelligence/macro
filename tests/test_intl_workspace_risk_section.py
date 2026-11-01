"""Composition tests for the pure Risk section assembler."""
import ast
import builtins
import copy
import json
import os
import pathlib
import time
from types import MappingProxyType

import pytest

from lib.intl_workspace_risk_section import build_risk_section


FIXTURE = pathlib.Path(__file__).parent / "fixtures/intl_workspace/risk_currency_overview.json"
BUILT = "2026-01-02T03:04:05+00:00"
LEG_KEYS = (
    "us_hy_oas_vel",
    "kre_spy_rs",
    "move_pctile",
    "sofr_iorb_corridor",
)
DOMAIN_KEYS = (
    "origin_stress",
    "us_transmission",
    "statistical_connectedness",
    "return_correlation",
    "directed_pressure",
    "structural_fragility",
)
OUTPUT_KEYS = (
    "context",
    "selected_market",
    "currency_channel",
    "currency_channels",
    "pressure_rows",
    "domain_panels",
    "exposure_boundary",
    "deep_research",
)
EXPOSURE_MISSING = [
    "issuer_identity",
    "revenue_currency",
    "cost_currency",
    "debt_currency",
    "hedges",
    "effective_date",
]


def receipt(reported_value, *, evidence_key="origin-evidence", observation_at="2026-01-02", **changes):
    value = {
        "quality": "qualified",
        "metadata": "allowed",
        "value_permission": "allowed",
        "reported_value": reported_value,
        "evidence_key": evidence_key,
        "source_reference": f"public/{evidence_key}",
        "observation_at": observation_at,
    }
    value.update(changes)
    return value


def two_tier(state="contained", origin_state="stressed", hot_values=None):
    if hot_values is None:
        hot_values = [False, False, False, False]
    return {
        "state": state,
        "tier1": {"em_stress_state": origin_state, "raw-secret": "RISK-DESK-SENTINEL"},
        "tier2": {
            "hot_count": sum(value is True for value in hot_values),
            "legs": {
                key: {"value": "RAW-TIER-VALUE", "hot": hot, "threshold": "RAW-TIER-THRESHOLD"}
                for key, hot in zip(LEG_KEYS, hot_values)
            },
        },
        "safety_bid_flag": "ignored-secret",
        "built": BUILT,
    }


def eligibility(origin_state="stressed", hot_values=None):
    if hot_values is None:
        hot_values = [False, False, False, False]
    return {
        "quality": "qualified",
        "metadata": "allowed",
        "value_permission": "allowed",
        "owner_ref": "public/owner",
        "method_ref": "public/method",
        "source_reference": "public/overall",
        "asof": BUILT,
        "origin": receipt(origin_state, evidence_key="origin-evidence", source_reference="public/origin"),
        "legs": {
            key: receipt(hot, evidence_key=f"{key}-evidence", source_reference=f"public/{key}")
            for key, hot in zip(LEG_KEYS, hot_values)
        },
        "diagnostic_permission": "allowed",
    }


def kr_overview():
    obj = json.loads(FIXTURE.read_text())
    row = obj["rows"][0]
    row.update(market_id="KR", name_en="South Korea", name_zh="韩国", index_id="^KS11", index_label="KOSPI")
    for leg, value in (("local", -1.8), ("usd", -2.5856), ("fx_contribution", -0.7856)):
        row[leg]["value"] = value
    row["metric"] = copy.deepcopy(row["usd"])
    obj["focus_ids"] = ["KR", "GB"]
    obj["summary"]["lowest_market_id"] = "KR"
    return obj


def pressure_maps():
    measures = {}
    support = {}
    specs = (
        ("country_credit_change", "bp", "country_credit_spread", 0),
        ("constituent_breadth_50d", "percent", "constituent_breadth", 61),
        ("annual_current_account", "percent_gdp", "current_account", 3.4),
    )
    for field, unit, kind, value in specs:
        measures["KR." + field] = {
            "quality": "qualified",
            "reason": None,
            "metadata": "allowed",
            "value_permission": "allowed",
            "value": value,
            "unit": unit,
            "instrument": {"kind": kind, "id": "native-" + field, "market_id": "KR"},
            "period": None,
            "observation_at": "2026-10-07",
            "calculation_at": None,
            "source_reference": "public-source",
            "evidence_key": "public-" + field,
        }
    measures["KR.country_credit_change"]["period"] = {
        "start": "2026-09-09",
        "end": "2026-10-07",
        "count": 20,
        "count_basis": "sessions",
    }
    support["KR.country_credit_change"] = {
        "method_ref": "credit-owner",
        "scope": "country",
        "instrument_id": "native-country_credit_change",
        "market_id": "KR",
        "change_start": "2026-09-09",
        "change_end": "2026-10-07",
    }
    support["KR.constituent_breadth_50d"] = {
        "method_ref": "breadth-owner",
        "market_id": "KR",
        "index_id": "native-constituent_breadth_50d",
        "membership_asof": "2026-10-07",
        "membership_ref": "public-members",
        "eligible_count": 100,
        "above_count": 61,
        "lookback_sessions": 50,
    }
    measures["KR.annual_current_account"]["period"] = {
        "start": "2024-01-01",
        "end": "2025-01-01",
        "count": 1,
        "count_basis": "release_periods",
    }
    support["KR.annual_current_account"] = {
        "method_ref": "annual-owner",
        "market_id": "KR",
        "field_year": 2024,
        "vintage": "2026-10-01",
        "observation_type": "actual",
    }
    return measures, support


def catalogue():
    return {
        "origin_stress": {
            "key": "origin_stress",
            "title_en": "Origin stress",
            "title_zh": "起源压力",
            "destination": "/research/origin",
        },
        "us_transmission": {
            "key": "us_transmission",
            "title_en": "US transmission",
            "title_zh": "美国传导",
            "destination": "#us-transmission",
        },
        "statistical_connectedness": {
            "key": "statistical_connectedness",
            "title_en": "Connectedness",
            "title_zh": "关联",
            "destination": None,
        },
        "company_research": {
            "key": "company_research",
            "title_en": "Company research",
            "title_zh": "公司研究",
            "destination": "/research/company",
        },
    }


def inputs(**overrides):
    measures, support = pressure_maps()
    value = {
        "context": {
            "selected_market": "KR",
            "horizon": "1m",
            "currency_basis": "usd_unhedged",
            "return_basis": "price",
        },
        "registry": {
            "markets": [
                {"market_id": "KR", "name_en": "South Korea", "name_zh": "韩国"},
                {"market_id": "GB", "name_en": "United Kingdom", "name_zh": "英国"},
            ],
            "horizons": ["1m", "1y"],
            "bases": ["local", "usd_unhedged"],
        },
        "overview": kr_overview(),
        "risk_desk": {"two_tier": two_tier(), "raw-secret": "RISK-DESK-SENTINEL", "inferred_calm": "quiet"},
        "cgl": {
            "matrix": {"kr": {"jp": 0.42}},
            "RAW-CGL-SENTINEL": "hidden-matrix",
            "rank": 3,
            "score": 99,
            "calm": True,
        },
        "measures": measures,
        "field_support": support,
        "summary_eligibility": {"us_transmission": eligibility()},
        "destinations": catalogue(),
    }
    value.update(overrides)
    return value


def build(value=None, **overrides):
    payload = inputs() if value is None else value
    payload.update(overrides)
    return build_risk_section(**payload)


def expect_invalid(payload):
    with pytest.raises(ValueError, match="^invalid_risk_section_input$"):
        build_risk_section(**payload)


def test_korean_currency_fixture_and_valid_pressure_summary():
    result = build()
    assert tuple(result) == OUTPUT_KEYS
    assert result["selected_market"] == "KR"
    channel = result["currency_channel"]
    assert channel == result["currency_channels"][0]
    assert channel is not result["currency_channels"][0]
    assert channel["slot"] == 0
    assert channel["market"]["market_id"] == "KR"
    assert channel["arithmetic_quality"] == "qualified"
    assert channel["local_return"]["value"] == -1.8
    assert channel["usd_return"]["value"] == -2.5856
    assert channel["fx_contribution_pp"]["value"] == -0.7856
    assert channel["fx_contribution_pp"]["unit"] == "percentage_points"
    assert channel["fx_return_usd_per_local"]["value"] == pytest.approx(-0.8)
    assert channel["fx_return_usd_per_local"]["unit"] == "percent"
    assert channel["fx_return_usd_per_local"]["derivation"] == "derived_from_disclosed_returns"
    kr_row = result["pressure_rows"][0]
    assert kr_row["market_id"] == "KR"
    assert kr_row["currency_return"]["value"] == pytest.approx(-0.8)
    assert kr_row["currency_return"]["unit"] == "percent"
    assert kr_row["currency_return"] != kr_row.get("fx_contribution_pp")
    assert kr_row["country_credit_change"]["value"] == 0
    assert kr_row["constituent_breadth_50d"]["value"] == 61
    assert kr_row["annual_current_account"]["value"] == 3.4
    summary = result["domain_panels"]["us_transmission"]["summary"]
    assert summary["quality"] == "qualified"
    assert summary["state"] == "contained"
    assert summary["diagnostic"] == {"reported_state": "contained"}


def test_registry_rows_keep_independent_fields_and_clocks():
    result = build()
    assert [row["market_id"] for row in result["pressure_rows"]] == ["KR", "GB"]
    kr_row, gb_row = result["pressure_rows"]
    assert kr_row["country_credit_change"]["period"]["count"] == 20
    assert kr_row["annual_current_account"]["support"]["field_year"] == 2024
    assert kr_row["constituent_breadth_50d"]["support"]["lookback_sessions"] == 50
    assert kr_row["currency_return"]["window"]["start"] == "2025-12-18T00:00:00"
    assert kr_row["currency_return"]["window"]["start"] != kr_row["country_credit_change"]["period"]["start"]
    assert gb_row["annual_current_account"] == {
        "field": "annual_current_account",
        "quality": "unknown",
        "reason": "not_supplied",
    }
    gb_fx = result["currency_channels"][1]["fx_return_usd_per_local"]
    assert gb_row["currency_return"] == gb_fx
    assert gb_row["currency_return"] is not gb_fx
    assert gb_fx["unit"] == "percent"
    assert result["currency_channels"][1]["fx_contribution_pp"]["unit"] == "percentage_points"
    assert gb_row["currency_return"]["value"] != result["currency_channels"][1]["fx_contribution_pp"]["value"]


def test_selected_null_withholds_selected_channel_and_keeps_roster():
    payload = inputs()
    payload["context"]["selected_market"] = None
    result = build_risk_section(**payload)
    assert result["selected_market"] is None
    assert result["currency_channel"] is None
    assert len(result["currency_channels"]) == 2
    assert [row["market_id"] for row in result["pressure_rows"]] == ["KR", "GB"]
    assert result["currency_channels"][0]["market"]["market_id"] == "KR"


@pytest.mark.parametrize(
    "mutate",
    [
        {"horizon": "1y"},
        {"currency_basis": "local"},
        {"return_basis": "total"},
    ],
)
def test_wrong_context_is_fixed_error(mutate):
    payload = inputs()
    payload["context"].update(mutate)
    expect_invalid(payload)


def test_duplicate_missing_and_wrong_slots_are_fixed_errors():
    payload = inputs()
    payload["overview"]["rows"][1] = copy.deepcopy(payload["overview"]["rows"][0])
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"] = [payload["overview"]["rows"][0]]
    payload["overview"]["configured_count"] = 1
    payload["overview"]["focus_ids"] = ["KR"]
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"][0]["slot"] = 2
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"][0]["market_id"] = "GB"
    payload["overview"]["rows"][1]["market_id"] = "KR"
    payload["overview"]["focus_ids"] = ["KR", "GB"]
    expect_invalid(payload)


def test_denied_slot_does_not_borrow_currency_identity():
    payload = inputs()
    payload["overview"]["rows"][0] = {"slot": 0, "quality": "denied", "reason": "metadata_denied"}
    payload["overview"]["focus_ids"] = ["GB"]
    result = build_risk_section(**payload)
    denied = result["currency_channels"][0]
    assert denied["market"] is None
    assert denied["arithmetic_quality"] == "unavailable"
    serialized = json.dumps(denied)
    assert "KR" not in serialized
    assert "GB" not in serialized
    assert "South Korea" not in serialized
    assert "United Kingdom" not in serialized
    assert "synthetic" not in serialized
    assert result["currency_channels"][1]["market"]["market_id"] == "GB"
    assert result["pressure_rows"][0]["market_id"] == "KR"
    assert result["currency_channel"]["market"] is None
    assert result["selected_market"] == "KR"


def test_unknown_or_missing_pressure_keeps_neighbors():
    payload = inputs()
    payload["measures"]["KR.country_credit_change"] = {"secret": "SECRET-FIELD"}
    result = build_risk_section(**payload)
    assert result["pressure_rows"][0]["country_credit_change"]["quality"] == "unknown"
    assert result["pressure_rows"][0]["annual_current_account"]["value"] == 3.4
    assert result["pressure_rows"][0]["currency_return"]["value"] == pytest.approx(-0.8)
    assert result["pressure_rows"][1]["market_id"] == "GB"
    assert "SECRET-FIELD" not in json.dumps(result)

    payload = inputs()
    del payload["measures"]["KR.constituent_breadth_50d"]
    result = build_risk_section(**payload)
    assert result["pressure_rows"][0]["constituent_breadth_50d"]["reason"] == "not_supplied"
    assert result["pressure_rows"][0]["country_credit_change"]["value"] == 0


@pytest.mark.parametrize(
    "destination",
    [
        "https://example.test/research",
        "javascript:alert(1)",
        "/research/../admin",
        "//example.test",
        "/a/%2e%2e",
        "/a\\b",
        "#bad fragment",
    ],
)
def test_malicious_destination_scheme_is_fixed_error(destination):
    payload = inputs()
    payload["destinations"]["origin_stress"]["destination"] = destination
    expect_invalid(payload)


@pytest.mark.parametrize(
    "mutate",
    [
        "extra_destination",
        "extra_eligibility",
        "unknown_measure",
        "extra_context",
        "unknown_selected",
    ],
)
def test_unconfigured_keys_and_unknown_selected_are_fixed_errors(mutate):
    payload = inputs()
    if mutate == "extra_destination":
        payload["destinations"]["economic_cycle"] = {
            "key": "economic_cycle",
            "title_en": "Cycle",
            "title_zh": "周期",
            "destination": "/research/cycle",
        }
    elif mutate == "extra_eligibility":
        payload["summary_eligibility"]["origin"] = {"quality": "qualified"}
    elif mutate == "unknown_measure":
        payload["measures"]["CN.country_credit_change"] = payload["measures"]["KR.country_credit_change"]
    elif mutate == "extra_context":
        payload["context"]["source_reference"] = "synthetic:inspector-source"
    else:
        payload["context"]["selected_market"] = "JP"
    expect_invalid(payload)


def test_hostile_and_cyclic_inputs_do_not_execute_hooks():
    class Hostile(dict):
        def get(self, *args, **kwargs):
            raise AssertionError("hostile conversion executed")

        def keys(self):
            raise AssertionError("hostile conversion executed")

    payload = inputs()
    payload["overview"] = Hostile(payload["overview"])
    expect_invalid(payload)

    payload = inputs()
    payload["measures"] = Hostile(payload["measures"])
    expect_invalid(payload)

    payload = inputs()
    payload["risk_desk"] = Hostile(payload["risk_desk"])
    expect_invalid(payload)

    payload = inputs()
    payload["measures"]["self"] = payload["measures"]
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"].append(payload["overview"]["rows"])
    expect_invalid(payload)

    expect_invalid(inputs(destinations=MappingProxyType(catalogue())))


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_input_is_fixed_error(bad):
    payload = inputs()
    payload["cgl"]["score"] = bad
    expect_invalid(payload)
    payload = inputs()
    payload["measures"]["KR.country_credit_change"]["value"] = bad
    expect_invalid(payload)


def test_risk_desk_and_cgl_sentinels_never_leak():
    result = build()
    serialized = json.dumps(result)
    for token in (
        "RISK-DESK-SENTINEL",
        "RAW-CGL-SENTINEL",
        "hidden-matrix",
        "RAW-TIER-VALUE",
        "RAW-TIER-THRESHOLD",
        "inferred_calm",
        "ignored-secret",
    ):
        assert token not in serialized
    assert "matrix" not in serialized
    assert result["domain_panels"]["origin_stress"] == {
        "key": "origin_stress",
        "kind": "retained_research",
        "destination": catalogue()["origin_stress"],
    }
    assert "value" not in result["domain_panels"]["origin_stress"]
    assert "state" not in result["domain_panels"]["origin_stress"]
    assert "score" not in result["domain_panels"]["structural_fragility"]
    assert "cgl" not in result
    assert "risk_desk" not in result


def test_missing_or_malformed_support_does_not_invent_summary():
    payload = inputs()
    payload["risk_desk"] = None
    payload["summary_eligibility"] = None
    result = build_risk_section(**payload)
    summary = result["domain_panels"]["us_transmission"]["summary"]
    assert summary["quality"] == "unknown"
    assert summary["state"] is None
    assert summary["evidence_refs"] == []

    payload = inputs()
    payload["risk_desk"] = {"two_tier": two_tier()}
    payload["summary_eligibility"] = {}
    result = build_risk_section(**payload)
    assert result["domain_panels"]["us_transmission"]["summary"]["state"] is None

    payload = inputs()
    payload["risk_desk"] = {"two_tier": "contained"}
    result = build_risk_section(**payload)
    assert result["domain_panels"]["us_transmission"]["summary"]["quality"] == "unknown"
    assert result["domain_panels"]["us_transmission"]["summary"]["state"] is None

    payload = inputs()
    payload["cgl"] = None
    result = build_risk_section(**payload)
    assert result["exposure_boundary"]["quality"] == "unsupported"
    assert result["exposure_boundary"]["reason"] == "issuer_exposure_not_supplied"


def test_domain_panels_and_deep_research_are_descriptors_only():
    result = build()
    assert tuple(result["domain_panels"]) == DOMAIN_KEYS
    for key in DOMAIN_KEYS:
        panel = result["domain_panels"][key]
        if key == "us_transmission":
            assert panel["kind"] == "transmission_summary"
            assert set(panel) == {"key", "kind", "destination", "summary"}
        else:
            assert panel["kind"] == "retained_research"
            assert set(panel) == {"key", "kind", "destination"}
        assert panel["key"] == key
    assert result["domain_panels"]["statistical_connectedness"]["destination"]["destination"] is None
    assert result["domain_panels"]["return_correlation"]["destination"] is None
    assert [entry["key"] for entry in result["deep_research"]] == ["origin_stress", "us_transmission"]
    assert "company_research" not in [entry["key"] for entry in result["deep_research"]]
    assert result["exposure_boundary"] == {
        "quality": "unsupported",
        "reason": "issuer_exposure_not_supplied",
        "missing_evidence": EXPOSURE_MISSING,
        "destination": catalogue()["company_research"],
    }


def test_inputs_are_never_mutated_and_outputs_are_deep_detached():
    payload = inputs()
    before = copy.deepcopy(payload)
    result = build_risk_section(**payload)
    assert payload == before
    result["context"]["horizon"] = "changed"
    result["currency_channels"][0]["market"]["name_en"] = "changed"
    result["pressure_rows"][0]["currency_return"]["value"] = 0
    result["pressure_rows"][0]["annual_current_account"]["support"]["field_year"] = 1
    result["domain_panels"]["origin_stress"]["destination"]["destination"] = "/changed"
    result["deep_research"][0]["title_en"] = "changed"
    result["exposure_boundary"]["missing_evidence"].clear()
    result["domain_panels"]["us_transmission"]["summary"]["state"] = "transmitting"
    assert payload == before
    assert result["currency_channel"] is not result["currency_channels"][0]
    result["currency_channel"]["fx_return_usd_per_local"]["value"] = 12
    assert result["currency_channels"][0]["fx_return_usd_per_local"]["value"] == pytest.approx(-0.8)
    assert result["pressure_rows"][0]["currency_return"] is not result["currency_channels"][0]["fx_return_usd_per_local"]


def test_no_stdout_file_or_provider_effects(monkeypatch, capsys):
    payload = inputs()

    def refuse(*args, **kwargs):
        raise AssertionError("unexpected external call")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(time, "time", refuse)
    monkeypatch.setattr(os, "read", refuse, raising=False)
    result = build_risk_section(**payload)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert result["selected_market"] == "KR"


def test_source_has_no_engine_io_or_unexpected_imports():
    source = pathlib.Path("lib/intl_workspace_risk_section.py").read_text()
    tree = ast.parse(source)
    allowed_modules = {
        "copy",
        "math",
        "lib.intl_workspace_macro",
        "lib.intl_workspace_risk",
        "lib.intl_workspace_risk_currency",
        "lib.intl_workspace_risk_pressure",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in allowed_modules
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module in allowed_modules
        if isinstance(node, ast.Name) and node.id in {"open", "exec", "eval", "__import__"}:
            assert False, "implementation must not perform I/O or dynamic execution"
    assert "engine." not in source
    assert ".__class__" not in source


def test_mismatched_destination_key_and_invalid_containers_fail():
    payload = inputs()
    payload["destinations"]["origin_stress"]["key"] = "us_transmission"
    expect_invalid(payload)
    expect_invalid(inputs(destinations=[]))
    expect_invalid(inputs(summary_eligibility=[]))
    expect_invalid(inputs(risk_desk=[]))
    expect_invalid(inputs(measures=[]))
    expect_invalid(inputs(field_support=[]))
    payload = inputs()
    payload["context"]["selected_market"] = ""
    expect_invalid(payload)


@pytest.mark.parametrize("raw", [[], "raw-private-CGL", 17, True])
def test_cgl_requires_its_declared_packet_container(raw):
    expect_invalid(inputs(cgl=raw))
