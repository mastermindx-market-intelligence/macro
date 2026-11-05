"""Macro composition tests using the accepted projection without mocks."""
from copy import deepcopy
import math

import pytest

from lib.intl_macro_mount import attach_macros
from lib.intl_workspace_macro import build_macro_section


MARKETS = ["EZ", "JP"]
HORIZONS = ["1m", "3m"]
BASES = ["local", "usd_unhedged"]
GENERATION_UUID = "12345678-1234-4123-8123-123456789012"
GENERATION = "im-workspace-generation:" + GENERATION_UUID
NOTICE = {
    "market_id": "EZ",
    "field": "policy_rate",
    "instrument_id": "deposit_facility",
    "origin_url": "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
}
UNKNOWN = {"quality": "unknown", "reason": "not_supplied"}


def measure(value, **overrides):
    result = {
        "quality": "qualified", "reason": None, "metadata": "allowed",
        "value_permission": "allowed", "value": value, "unit": "percent",
        "instrument": {"kind": "official_policy", "id": "deposit_facility", "market_id": "EZ"},
        "period": None, "observation_at": "2026-09-10", "calculation_at": None,
        "source_reference": "synthetic:policy-grant", "evidence_key": "synthetic-policy",
    }
    result.update(overrides)
    return result


def cycle(*, market_id="EZ"):
    return {
        "quality": "qualified", "reason": None, "metadata": "allowed",
        "value_permission": "allowed", "reported_quad": "Q1", "raw_quad": "Q1",
        "method_ref": "synthetic:cycle-method", "method_kind": "economic_cycle",
        "asof": "2026-09-10T09:00:00Z",
        "components": {
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
            "growth_score": 0.25, "inflation_score": 0.0,
            "growth_n_components": 3, "inflation_n_components": 2,
        },
        "economic_support": {
            "owner_ref": "synthetic:owner", "decision_ref": "synthetic:decision",
            "method_ref": "synthetic:cycle-method", "asof": "2026-09-10T09:00:00Z",
            "dependency_keys": [f"{market_id}.gdp_yoy", f"{market_id}.cpi_yoy"],
            "component_keys": ["growth.gdp_trend", "inflation.cpi_direction", "inflation.yield_trend"],
            "heading_key": "goldilocks", "disagreement": False,
        },
    }


def inputs(value=2.5):
    return {
        "registry": {
            "markets": [
                {"market_id": "EZ", "name_en": "Euro Area", "name_zh": "欧元区"},
                {"market_id": "JP", "name_en": "Japan", "name_zh": "日本"},
            ],
            "horizons": list(HORIZONS), "bases": list(BASES),
        },
        "measures": {
            "EZ.policy_rate": measure(value),
            "EZ.gdp_yoy": measure(
                1.0,
                instrument={"kind": "macro_yoy", "id": "gdp", "market_id": "EZ"},
                source_reference="synthetic:gdp-grant", evidence_key="synthetic-gdp",
            ),
            "EZ.cpi_yoy": measure(
                2.0,
                instrument={"kind": "macro_yoy", "id": "cpi", "market_id": "EZ"},
                source_reference="synthetic:cpi-grant", evidence_key="synthetic-cpi",
            ),
            "JP.gdp_yoy": measure(
                0.4,
                instrument={"kind": "macro_yoy", "id": "gdp", "market_id": "JP"},
                source_reference="synthetic:jp-gdp-grant", evidence_key="synthetic-jp-gdp",
            ),
            "JP.cpi_yoy": measure(
                1.1,
                instrument={"kind": "macro_yoy", "id": "cpi", "market_id": "JP"},
                source_reference="synthetic:jp-cpi-grant", evidence_key="synthetic-jp-cpi",
            ),
        },
        "cycle_evidence": {"EZ": cycle(), "JP": cycle(market_id="JP")},
        "destinations": {
            "economic_cycle": {
                "key": "economic_cycle", "title_en": "Euro Area research",
                "title_zh": "欧元区研究", "destination": "/research/euro-area",
            },
            "realized_policy": {
                "key": "realized_policy", "title_en": "Policy evidence",
                "title_zh": "政策证据", "destination": "/research/policy",
            },
            "market_response": {
                "key": "market_response", "title_en": "Market response",
                "title_zh": "市场反应", "destination": None,
            },
        },
    }


def workspace(version=2, *, edit=None):
    panels = []
    for horizon in HORIZONS:
        for basis in BASES:
            panel = {
                "context_id": f"context-{horizon}-{basis}",
                "overview": {
                    "context": {
                        "horizon": horizon, "currency_basis": basis,
                        "return_basis": "price", "source_reference": GENERATION,
                        "source_reference_reason": None,
                    },
                    "rows": [],
                },
            }
            if version == 2:
                panel["generation"] = GENERATION
            panels.append(panel)
    config = {
        "markets": list(MARKETS), "horizons": list(HORIZONS), "bases": list(BASES),
        "default_horizon": "1m", "default_basis": "local", "source_reference": GENERATION,
        "anchor_ids": ["synthetic-anchor"], "library_group_ids": [],
    }
    result = {"config": config, "panels": panels}
    if version == 2:
        result["binding_version"] = 2
        result["library_generation"] = GENERATION
    else:
        for panel in panels:
            panel["overview"]["context"]["source_reference"] = "synthetic:workspace-owner"
        config["source_reference"] = "synthetic:workspace-owner"
    if edit is not None:
        edit(result)
    return result


def invalid(value, **payload):
    if payload.get("mask_message"):
        payload.pop("mask_message")
        with pytest.raises(ValueError):
            attach_macros(value, **({**inputs(), **payload}))
        return
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(value, **({**inputs(), **payload}))


def policy(section):
    return next(row["policy_rate"] for row in section["market_rows"] if row["market_id"] == "EZ")


def field_of(section, market_id, field):
    return next(row[field] for row in section["market_rows"] if row["market_id"] == market_id)


def unknown_field(field):
    return {"field": field, **UNKNOWN}


def assert_v1_unqualified(item):
    section = item["macro_section"]
    assert section["selected_market"] is None
    assert policy(section) == unknown_field("policy_rate")
    assert field_of(section, "EZ", "gdp_yoy") == unknown_field("gdp_yoy")
    assert field_of(section, "EZ", "cpi_yoy") == unknown_field("cpi_yoy")
    assert field_of(section, "JP", "gdp_yoy") == unknown_field("gdp_yoy")
    assert field_of(section, "JP", "cpi_yoy") == unknown_field("cpi_yoy")
    assert section["cycle_rows"] == []
    assert section["coverage"] == {
        "configured_ids": MARKETS,
        "classified_ids": [],
        "unclassified": [
            {"market_id": "EZ", "reason": "not_supplied"},
            {"market_id": "JP", "reason": "not_supplied"},
        ],
    }
    assert [entry["key"] for entry in section["deep_research"]] == [
        "economic_cycle", "realized_policy", "market_response",
    ]
    assert list(item) == ["context_id", "context", "macro_section", "source_notice"]
    assert item["source_notice"] is None


@pytest.mark.parametrize("value", [2.5, 0])
def test_synthetic_positive_and_zero_attach_to_every_context(value):
    before = deepcopy(workspace())
    original = inputs(value)
    result = attach_macros(before, **deepcopy(original), source_notice=NOTICE)
    assert len(result["macros"]) == 4
    assert all(list(item) == [
        "context_id", "context", "macro_section", "source_notice", "generation"
    ] for item in result["macros"])
    assert [item["context_id"] for item in result["macros"]] == [
        panel["context_id"] for panel in before["panels"]
    ]
    assert {tuple(item["context"][key] for key in ("horizon", "currency_basis", "return_basis"))
            for item in result["macros"]} == {
        (horizon, basis, "price") for horizon in HORIZONS for basis in BASES
    }
    assert all(item["source_notice"] == NOTICE for item in result["macros"])
    assert all(policy(item["macro_section"])["value"] == value for item in result["macros"])
    assert all(item["macro_section"]["selected_market"] is None for item in result["macros"])
    assert [row["market_id"] for row in result["macros"][0]["macro_section"]["market_rows"]] == MARKETS
    assert before == workspace()
    assert original == inputs(value)


def test_output_is_actual_accepted_projection_and_detached():
    payload = inputs()
    ws = workspace()
    ws["retained"] = {"nested": [1, 2]}
    before = deepcopy(ws)
    result = attach_macros(ws, **payload, source_notice=NOTICE)
    context = {"selected_market": None, **result["macros"][0]["context"]}
    expected = build_macro_section(
        context=context, registry=payload["registry"], measures=payload["measures"],
        cycle_evidence=payload["cycle_evidence"], destinations=payload["destinations"])
    assert result["macros"][0]["macro_section"] == expected
    result["macros"][0]["macro_section"]["market_rows"][0]["market_id"] = "edited"
    result["macros"][0]["source_notice"]["origin_url"] = "https://example.invalid"
    result["retained"]["nested"].append(3)
    assert ws == before
    assert payload == inputs()
    assert NOTICE["origin_url"] == (
        "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV")


def test_none_is_optional_and_notice_is_still_validated():
    assert attach_macros(None, **inputs(), source_notice=None) is None
    assert attach_macros(None, **inputs(), source_notice=NOTICE) is None
    bad = dict(NOTICE, origin_url="https://example.invalid")
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(None, **inputs(), source_notice=bad)
    assert attach_macros(
        None, registry=object(), measures=object(), cycle_evidence=object(),
        destinations=object(), source_notice=None) is None


@pytest.mark.parametrize("quality,reason,expected_value", [
    ("stale", "source_stale", -0.0),
    ("denied", "metadata_denied", None),
])
def test_notice_follows_projection_qualification_not_grant(quality, reason, expected_value):
    payload = inputs(-0.0 if quality == "stale" else 123)
    payload["measures"]["EZ.policy_rate"].update(
        quality=quality, reason=reason,
        metadata="allowed" if quality == "stale" else "denied",
        value_permission="allowed" if quality == "stale" else "denied",
        **({} if quality == "stale" else {
            "value": None, "unit": None, "instrument": None, "period": None,
            "observation_at": None, "calculation_at": None, "source_reference": None,
            "evidence_key": None,
        }),
    )
    result = attach_macros(workspace(), **payload, source_notice=NOTICE)
    projected = policy(result["macros"][0]["macro_section"])
    expected_notice = NOTICE if quality == "stale" else None
    assert all("source_notice" in item for item in result["macros"])
    assert all(item["source_notice"] == expected_notice for item in result["macros"])
    assert projected["quality"] == quality
    if expected_value is None:
        assert "value" not in projected
    else:
        assert math.copysign(1, projected["value"]) == math.copysign(1, expected_value)


def test_missing_notice_withholds_qualified_policy_but_validates_supply_first():
    payload = inputs(2.5)
    before = deepcopy(payload)
    result = attach_macros(workspace(), **payload, source_notice=None)
    assert all(list(item) == [
        "context_id", "context", "macro_section", "source_notice", "generation"
    ] for item in result["macros"])
    assert all(item["source_notice"] is None for item in result["macros"])
    assert all(policy(item["macro_section"]) == unknown_field("policy_rate")
               for item in result["macros"])
    assert all(field_of(item["macro_section"], "EZ", "gdp_yoy")["value"] == 1.0
               for item in result["macros"])
    assert all(field_of(item["macro_section"], "JP", "cpi_yoy")["value"] == 1.1
               for item in result["macros"])
    assert all(item["macro_section"]["coverage"]["classified_ids"] == MARKETS
               for item in result["macros"])
    assert payload == before
    malformed = inputs()
    malformed["measures"]["EZ.policy_rate"]["value"] = math.inf
    with pytest.raises(ValueError):
        attach_macros(workspace(), **malformed, source_notice=None)


def test_v1_forces_macro_unknown_even_with_positive_supply():
    payload = inputs(2.5)
    before = deepcopy(payload)
    result = attach_macros(workspace(version=1), **payload, source_notice=NOTICE)
    assert len(result["macros"]) == 4
    for item in result["macros"]:
        assert_v1_unqualified(item)
    assert payload == before


def test_v2_generation_mismatch_refuses():
    ws = workspace()
    ws["panels"][1]["generation"] = "im-workspace-generation:87654321-4321-4123-8123-123456789012"
    invalid(ws, mask_message=True)


@pytest.mark.parametrize("change", [
    lambda ws: ws["panels"][1].update(
        context_id=ws["panels"][0]["context_id"]),
    lambda ws: ws["panels"].pop(),
    lambda ws: ws["panels"].append(deepcopy(ws["panels"][0])),
])
def test_duplicate_and_missing_context_refuse(change):
    ws = workspace()
    change(ws)
    invalid(ws)


@pytest.mark.parametrize("change", [
    lambda payload: payload["registry"]["markets"].reverse(),
    lambda payload: payload["registry"]["horizons"].reverse(),
    lambda payload: payload["registry"]["bases"].reverse(),
    lambda payload: payload["registry"]["bases"].__setitem__(1, "usd_hedged"),
    lambda payload: payload["registry"]["markets"].pop(),
])
def test_roster_order_and_basis_drift_refuse(change):
    payload = inputs()
    change(payload)
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(workspace(), **payload)


@pytest.mark.parametrize("mutate", [
    lambda payload: payload["measures"].update(custom={}),
    lambda payload: payload["measures"].__setitem__("custom", []),
    lambda payload: payload["cycle_evidence"].update(custom={}),
    lambda payload: payload["destinations"].update(custom={}),
])
def test_nonplain_input_containers_refuse(mutate):
    class Custom(dict):
        pass
    payload = inputs()
    mutate(payload)
    if "custom" in payload["measures"]:
        payload["measures"]["custom"] = Custom()
    elif "custom" in payload["cycle_evidence"]:
        payload["cycle_evidence"]["custom"] = Custom()
    elif "custom" in payload["destinations"]:
        payload["destinations"]["custom"] = Custom()
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(workspace(), **payload)


def test_custom_and_cyclic_workspace_refuse_before_binding_deepcopy():
    class Custom(dict):
        pass
    ws = Custom(workspace())
    invalid(ws)
    cyclic = workspace()
    cyclic["panels"][0]["overview"]["context"]["self"] = cyclic["panels"][0]["overview"]["context"]
    invalid(cyclic)


@pytest.mark.parametrize("container", ["registry", "measures", "cycle_evidence", "destinations"])
def test_cyclic_supplied_container_refuses(container):
    payload = inputs()
    cyclic = {}
    cyclic["cycle"] = cyclic
    if container == "registry":
        payload[container]["horizons"].append(cyclic)
    else:
        payload[container]["cycle"] = cyclic
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(workspace(), **payload)


def test_config_defaults_context_shape_and_v1_source_refuse_drift():
    ws = workspace()
    ws["config"]["default_horizon"] = {}
    invalid(ws)
    ws = workspace()
    del ws["panels"][0]["overview"]["context"]["source_reference_reason"]
    invalid(ws)
    ws = workspace(version=1)
    ws["panels"][0]["overview"]["context"]["source_reference"] = "synthetic:other"
    invalid(ws)


def test_preexisting_macros_and_default_selection_are_refused():
    ws = workspace()
    ws["macros"] = []
    invalid(ws)
    payload = inputs()
    payload["registry"]["markets"][0]["default"] = True
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(workspace(), **payload)


def test_horizons_do_not_redefine_fact_dates():
    payload = inputs(2.5)
    expected = {
        "period": None, "observation_at": "2026-09-10", "calculation_at": None,
        "source_reference": "synthetic:policy-grant",
    }
    result = attach_macros(workspace(), **payload, source_notice=NOTICE)
    by_horizon = {item["context"]["horizon"]: policy(item["macro_section"]) for item in result["macros"]}
    assert set(by_horizon) == set(HORIZONS)
    assert all({key: value for key, value in item.items() if key in expected} == expected
               for item in by_horizon.values())


def test_canonical_v1_nullable_source_reference():
    ws = workspace(version=1)
    ws["config"]["source_reference"] = None
    for panel in ws["panels"]:
        panel["overview"]["context"]["source_reference"] = None
    result = attach_macros(ws, **inputs(2.5), source_notice=NOTICE)
    assert [item["context_id"] for item in result["macros"]] == [
        panel["context_id"] for panel in ws["panels"]
    ]
    for item in result["macros"]:
        assert_v1_unqualified(item)
    ws = workspace(version=1)
    ws["config"]["source_reference"] = ""
    invalid(ws)


@pytest.mark.parametrize("field,value", [
    ("horizon", ["1m"]),
    ("currency_basis", {"basis": "local"}),
    ("return_basis", ["price"]),
])
def test_unhashable_context_fields_raise_valueerror(field, value):
    ws = workspace()
    ws["panels"][0]["overview"]["context"][field] = value
    invalid(ws)


@pytest.mark.parametrize("key,values", [
    ("markets", ["EZ", ["JP"]]),
    ("markets", ["EZ", "EZ"]),
    ("horizons", ["1m", {"h": "3m"}]),
    ("horizons", ["1m", "1m"]),
    ("bases", ["local", "local"]),
])
def test_config_list_items_and_uniqueness_validated_inside_loop(key, values):
    ws = workspace()
    ws["config"][key] = values
    invalid(ws)


def test_v1_validates_full_positive_supply_before_withholding():
    malformed = inputs()
    malformed["measures"]["JP.gdp_yoy"]["value"] = math.inf
    with pytest.raises(ValueError):
        attach_macros(workspace(version=1), **malformed, source_notice=NOTICE)
    cyclic = inputs()
    cyclic["cycle_evidence"]["loop"] = cyclic["cycle_evidence"]
    cyclic["cycle_evidence"]["loop"]["self"] = cyclic["cycle_evidence"]
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(workspace(version=1), **cyclic, source_notice=NOTICE)


def test_none_workspace_refuses_cyclic_or_custom_notice():
    class Custom(dict):
        pass
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(None, **inputs(), source_notice=Custom(NOTICE))
    cyclic = dict(NOTICE)
    cyclic["origin_url"] = cyclic
    with pytest.raises(ValueError, match="invalid_macro_workspace$"):
        attach_macros(None, **inputs(), source_notice=cyclic)


def test_overdeep_input_is_bounded_valueerror():
    ws = workspace()
    nested = ws
    for _ in range(2000):
        nested["deeper"] = {}
        nested = nested["deeper"]
    invalid(ws)


def test_nonfinite_workspace_values_refused():
    ws = workspace()
    ws["retained"] = math.inf
    invalid(ws)
    ws = workspace()
    ws["retained"] = math.nan
    invalid(ws)
