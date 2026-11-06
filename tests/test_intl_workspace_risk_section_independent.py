"""Independent C2 exact-source review tests for build_risk_section.

Calls the production assembler. Does not copy the author suite's assertions.
"""
from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import json
import os
import pathlib
import time
from types import MappingProxyType

import pytest

from lib.intl_workspace_risk_section import build_risk_section
import lib.intl_workspace_risk_section as section_mod


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/intl_workspace/risk_currency_overview.json"
BUILT = "2026-01-02T03:04:05+00:00"
LEG_KEYS = ("us_hy_oas_vel", "kre_spy_rs", "move_pctile", "sofr_iorb_corridor")
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




def receipt(reported_value, *, evidence_key="origin-evidence", **changes):
    value = {
        "quality": "qualified",
        "metadata": "allowed",
        "value_permission": "allowed",
        "reported_value": reported_value,
        "evidence_key": evidence_key,
        "source_reference": f"public/{evidence_key}",
        "observation_at": "2026-01-02",
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


def expect_invalid(payload):
    with pytest.raises(ValueError, match="^invalid_risk_section_input$") as raised:
        build_risk_section(**payload)
    assert raised.value.args == ("invalid_risk_section_input",)
    assert raised.value.__cause__ is None




def test_positive_kr_arithmetic_pressure_and_summary():
    result = build_risk_section(**inputs())
    assert tuple(result) == OUTPUT_KEYS
    channel = result["currency_channel"]
    local = channel["local_return"]["value"]
    usd = channel["usd_return"]["value"]
    derived = ((1 + usd / 100) / (1 + local / 100) - 1) * 100
    assert local == -1.8
    assert usd == -2.5856
    assert channel["fx_return_usd_per_local"]["value"] == pytest.approx(derived)
    assert channel["fx_return_usd_per_local"]["value"] == pytest.approx(-0.8)
    assert channel["fx_return_usd_per_local"]["unit"] == "percent"
    assert channel["fx_contribution_pp"]["value"] == pytest.approx(usd - local)
    assert channel["fx_contribution_pp"]["unit"] == "percentage_points"
    kr_row = result["pressure_rows"][0]
    assert kr_row["market_id"] == "KR"
    assert kr_row["currency_return"]["value"] == pytest.approx(derived)
    assert kr_row["currency_return"]["unit"] == "percent"
    assert kr_row["country_credit_change"]["value"] == 0
    assert kr_row["constituent_breadth_50d"]["value"] == 61
    assert kr_row["annual_current_account"]["value"] == 3.4
    summary = result["domain_panels"]["us_transmission"]["summary"]
    assert summary["quality"] == "qualified"
    assert summary["state"] == "contained"
    assert summary["diagnostic"] == {"reported_state": "contained"}
    gb = result["currency_channels"][1]
    gb_derived = ((1 + gb["usd_return"]["value"] / 100) / (1 + gb["local_return"]["value"] / 100) - 1) * 100
    assert gb["market"]["market_id"] == "GB"
    assert result["pressure_rows"][1]["currency_return"]["value"] == pytest.approx(gb_derived)
    assert result["pressure_rows"][1]["currency_return"]["value"] != gb["fx_contribution_pp"]["value"]


def test_denied_slot_omits_identity_and_keeps_registry_roster():
    payload = inputs()
    payload["overview"]["rows"][0] = {"slot": 0, "quality": "denied", "reason": "metadata_denied"}
    payload["overview"]["focus_ids"] = ["GB"]
    result = build_risk_section(**payload)
    denied = result["currency_channels"][0]
    blob = json.dumps(denied)
    assert denied["market"] is None
    assert denied["arithmetic_quality"] == "unavailable"
    assert "KR" not in blob
    assert "GB" not in blob
    assert "South Korea" not in blob
    assert "United Kingdom" not in blob
    assert "KOSPI" not in blob
    assert "FTSE" not in blob
    assert result["currency_channels"][1]["market"]["market_id"] == "GB"
    assert result["pressure_rows"][0]["market_id"] == "KR"
    assert result["pressure_rows"][0]["currency_return"]["value"] is None
    assert result["pressure_rows"][1]["currency_return"]["value"] == pytest.approx(
        result["currency_channels"][1]["fx_return_usd_per_local"]["value"]
    )
    assert result["selected_market"] == "KR"
    assert result["currency_channel"]["market"] is None


def test_denied_row_cannot_carry_neighbor_payload():
    payload = inputs()
    stolen = copy.deepcopy(payload["overview"]["rows"][1])
    stolen["slot"] = 0
    stolen["quality"] = "denied"
    stolen["reason"] = "metadata_denied"
    payload["overview"]["rows"][0] = stolen
    payload["overview"]["focus_ids"] = ["GB"]
    expect_invalid(payload)


def test_disclosed_identity_from_another_slot_is_fixed_error(monkeypatch):
    original = section_mod.build_currency_channel

    def borrow(overview, *, selected_slot):
        channel = original(overview, selected_slot=selected_slot)
        if selected_slot == 0:
            channel = copy.deepcopy(channel)
            channel["market"] = {
                "slot": 0,
                "market_id": "GB",
                "name_en": "United Kingdom",
                "name_zh": "英国",
            }
        return channel

    monkeypatch.setattr(section_mod, "build_currency_channel", borrow)
    expect_invalid(inputs())


def test_wrong_horizon_basis_and_return_basis_fail_closed():
    for mutate in ({"horizon": "1y"}, {"currency_basis": "local"}, {"return_basis": "total"}):
        payload = inputs()
        payload["context"].update(mutate)
        expect_invalid(payload)


def test_ambiguous_duplicate_and_missing_slots_fail_closed():
    payload = inputs()
    payload["overview"]["rows"][1] = copy.deepcopy(payload["overview"]["rows"][0])
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"] = [payload["overview"]["rows"][0]]
    expect_invalid(payload)

    payload = inputs()
    payload["overview"]["rows"][0]["market_id"] = "GB"
    payload["overview"]["rows"][1]["market_id"] = "KR"
    expect_invalid(payload)


def test_selected_null_and_unknown_selected_fail_closed_or_withhold():
    payload = inputs()
    payload["context"]["selected_market"] = None
    result = build_risk_section(**payload)
    assert result["selected_market"] is None
    assert result["currency_channel"] is None
    assert [row["market"]["market_id"] for row in result["currency_channels"]] == ["KR", "GB"]

    payload = inputs()
    payload["context"]["selected_market"] = "JP"
    expect_invalid(payload)
    expect_invalid(inputs(context={
        "selected_market": "",
        "horizon": "1m",
        "currency_basis": "usd_unhedged",
        "return_basis": "price",
    }))


def test_raw_desk_cgl_and_inferred_metrics_do_not_leak():
    result = build_risk_section(**inputs())
    blob = json.dumps(result)
    for token in (
        "RISK-DESK-SENTINEL",
        "RAW-CGL-SENTINEL",
        "hidden-matrix",
        "RAW-TIER-VALUE",
        "RAW-TIER-THRESHOLD",
        "inferred_calm",
        "ignored-secret",
        "synthetic:inspector-source",
    ):
        if token == "synthetic:inspector-source":
            assert token in blob
            continue
        assert token not in blob
    assert "matrix" not in blob
    assert "cgl" not in result
    assert "risk_desk" not in result
    for key in DOMAIN_KEYS:
        panel = result["domain_panels"][key]
        assert "score" not in panel
        assert "rank" not in panel
        assert "calm" not in panel
        assert "matrix" not in panel
        assert "two_tier" not in panel


def test_domain_panels_are_ordered_dict_of_navigation_descriptors():
    result = build_risk_section(**inputs())
    panels = result["domain_panels"]
    assert type(panels) is dict
    assert tuple(panels) == DOMAIN_KEYS
    for key in DOMAIN_KEYS:
        panel = panels[key]
        if key == "us_transmission":
            assert panel["kind"] == "transmission_summary"
            assert set(panel) == {"key", "kind", "destination", "summary"}
        else:
            assert panel["kind"] == "retained_research"
            assert set(panel) == {"key", "kind", "destination"}
            assert "summary" not in panel
            assert "value" not in panel
            assert "state" not in panel
        assert panel["key"] == key
    assert [entry["key"] for entry in result["deep_research"]] == ["origin_stress", "us_transmission"]
    assert result["exposure_boundary"] == {
        "quality": "unsupported",
        "reason": "issuer_exposure_not_supplied",
        "missing_evidence": [
            "issuer_identity",
            "revenue_currency",
            "cost_currency",
            "debt_currency",
            "hedges",
            "effective_date",
        ],
        "destination": catalogue()["company_research"],
    }


def test_missing_and_malformed_summary_stay_unknown():
    payload = inputs()
    payload["risk_desk"] = None
    payload["summary_eligibility"] = None
    summary = build_risk_section(**payload)["domain_panels"]["us_transmission"]["summary"]
    assert summary["quality"] == "unknown"
    assert summary["state"] is None

    payload = inputs()
    payload["summary_eligibility"] = {}
    assert build_risk_section(**payload)["domain_panels"]["us_transmission"]["summary"]["state"] is None

    payload = inputs()
    payload["risk_desk"] = {"two_tier": "contained"}
    assert build_risk_section(**payload)["domain_panels"]["us_transmission"]["summary"]["state"] is None

    payload = inputs()
    payload["summary_eligibility"] = {"us_transmission": {"quality": "qualified"}}
    assert build_risk_section(**payload)["domain_panels"]["us_transmission"]["summary"]["quality"] == "unknown"


def test_cgl_and_other_invalid_containers_fail_closed():
    for raw in ([], "raw-private-CGL", 17, True):
        expect_invalid(inputs(cgl=raw))
    expect_invalid(inputs(risk_desk=[]))
    expect_invalid(inputs(destinations=[]))
    expect_invalid(inputs(summary_eligibility=[]))
    expect_invalid(inputs(measures=[]))
    expect_invalid(inputs(field_support=[]))
    expect_invalid(inputs(destinations=MappingProxyType(catalogue())))


def test_unconfigured_keys_fail_closed():
    payload = inputs()
    payload["destinations"]["economic_cycle"] = {
        "key": "economic_cycle",
        "title_en": "Cycle",
        "title_zh": "周期",
        "destination": "/research/cycle",
    }
    expect_invalid(payload)
    payload = inputs()
    payload["summary_eligibility"]["origin"] = {"quality": "qualified"}
    expect_invalid(payload)
    payload = inputs()
    payload["measures"]["CN.country_credit_change"] = payload["measures"]["KR.country_credit_change"]
    expect_invalid(payload)
    payload = inputs()
    payload["context"]["source_reference"] = "synthetic:inspector-source"
    expect_invalid(payload)


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
def test_malicious_destination_is_fixed_error(destination):
    payload = inputs()
    payload["destinations"]["origin_stress"]["destination"] = destination
    expect_invalid(payload)


def test_hostile_cyclic_and_nonfinite_fail_closed():
    class Hostile(dict):
        def get(self, *args, **kwargs):
            raise AssertionError("hostile conversion executed")

    payload = inputs()
    payload["overview"] = Hostile(payload["overview"])
    expect_invalid(payload)
    payload = inputs()
    payload["measures"]["self"] = payload["measures"]
    expect_invalid(payload)
    payload = inputs()
    payload["cgl"]["score"] = float("nan")
    expect_invalid(payload)
    payload = inputs()
    payload["measures"]["KR.country_credit_change"]["value"] = float("inf")
    expect_invalid(payload)


def test_unknown_pressure_keeps_neighbors_and_currency():
    payload = inputs()
    payload["measures"]["KR.country_credit_change"] = {"secret": "SECRET-FIELD"}
    result = build_risk_section(**payload)
    assert result["pressure_rows"][0]["country_credit_change"]["quality"] == "unknown"
    assert result["pressure_rows"][0]["annual_current_account"]["value"] == 3.4
    assert result["pressure_rows"][0]["currency_return"]["value"] == pytest.approx(-0.8)
    assert "SECRET-FIELD" not in json.dumps(result)


def test_inputs_detached_and_production_helper_has_no_io(monkeypatch, capsys):
    payload = inputs()
    before = copy.deepcopy(payload)

    def refuse(*args, **kwargs):
        raise AssertionError("unexpected external call")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(time, "time", refuse)
    monkeypatch.setattr(os, "read", refuse, raising=False)
    result = build_risk_section(**payload)
    assert payload == before
    result["currency_channels"][0]["market"]["name_en"] = "changed"
    result["pressure_rows"][0]["currency_return"]["value"] = 0
    result["domain_panels"]["us_transmission"]["summary"]["state"] = "transmitting"
    result["exposure_boundary"]["missing_evidence"].clear()
    assert payload == before
    assert result["currency_channel"] is not result["currency_channels"][0]
    assert result["pressure_rows"][0]["currency_return"] is not result["currency_channels"][0]["fx_return_usd_per_local"]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
