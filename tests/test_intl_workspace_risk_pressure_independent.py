"""Independent C2 countertests for IM05 pressure projection. Does not import author tests."""
from copy import deepcopy
import json

import pytest

from lib.intl_workspace_risk_pressure import build_pressure_rows


_FIELDS = ("country_credit_change", "constituent_breadth_50d", "annual_current_account")




def _registry(*ids):
    names = {
        "JP": ("Japan", "日本"),
        "TW": ("Taiwan", "台湾"),
        "EZ": ("Eurozone", "欧元区"),
        "DE": ("Germany", "德国"),
        "US": ("United States", "美国"),
        "CN": ("China", "中国"),
    }
    markets = []
    for market_id in ids:
        en, zh = names[market_id]
        markets.append({"market_id": market_id, "name_en": en, "name_zh": zh})
    return {"markets": markets, "horizons": ["1m", "3m"], "bases": ["local", "usd_unhedged"]}


def _measure(field, market_id, value, *, quality="qualified", reason=None, metadata="allowed",
             value_permission="allowed", observation_at="2026-10-07", calculation_at=None,
             source_reference="public-source", evidence_key=None, period="auto",
             instrument_id=None, instrument_market=None, kind=None, unit=None):
    spec = {
        "country_credit_change": ("bp", "country_credit_spread"),
        "constituent_breadth_50d": ("percent", "constituent_breadth"),
        "annual_current_account": ("percent_gdp", "current_account"),
    }
    default_unit, default_kind = spec[field]
    if period == "auto":
        if field == "country_credit_change":
            period = {"start": "2026-09-09", "end": "2026-10-07", "count": 20, "count_basis": "sessions"}
        elif field == "annual_current_account":
            period = {"start": "2024-01-01", "end": "2025-01-01", "count": 1, "count_basis": "release_periods"}
        else:
            period = None
    return {
        "quality": quality,
        "reason": reason,
        "metadata": metadata,
        "value_permission": value_permission,
        "value": value,
        "unit": default_unit if unit is None else unit,
        "instrument": {
            "kind": default_kind if kind is None else kind,
            "id": instrument_id or f"native-{market_id}-{field}",
            "market_id": market_id if instrument_market is None else instrument_market,
        },
        "period": deepcopy(period),
        "observation_at": observation_at,
        "calculation_at": calculation_at,
        "source_reference": source_reference,
        "evidence_key": evidence_key or f"evidence-{market_id}-{field}",
    }


def _support(field, market_id, **overrides):
    instrument_id = overrides.pop("instrument_id", f"native-{market_id}-{field}")
    if field == "country_credit_change":
        body = {
            "method_ref": "credit-owner",
            "scope": "country",
            "instrument_id": instrument_id,
            "market_id": market_id,
            "change_start": "2026-09-09",
            "change_end": "2026-10-07",
        }
    elif field == "constituent_breadth_50d":
        body = {
            "method_ref": "breadth-owner",
            "market_id": market_id,
            "index_id": instrument_id,
            "membership_asof": "2026-10-07",
            "membership_ref": "public-members",
            "eligible_count": 100,
            "above_count": 61,
            "lookback_sessions": 50,
        }
    else:
        body = {
            "method_ref": "annual-owner",
            "market_id": market_id,
            "field_year": 2024,
            "vintage": "2026-10-01",
            "observation_type": "actual",
        }
    body.update(overrides)
    return body


def _pack(markets=("JP", "TW"), values=None, supports=None, measures=None, field_support=None):
    values = values or {}
    supports = supports or {}
    measures = {} if measures is None else dict(measures)
    field_support = {} if field_support is None else dict(field_support)
    defaults = {
        "country_credit_change": 0,
        "constituent_breadth_50d": 61,
        "annual_current_account": 3.4,
    }
    primary = markets[0]
    for field, default in defaults.items():
        key = f"{primary}.{field}"
        if key not in measures:
            measures[key] = _measure(field, primary, values.get(field, default))
        if key not in field_support:
            field_support[key] = _support(field, primary, **supports.get(field, {}))
    return dict(registry=_registry(*markets), measures=measures, field_support=field_support)


def _row(obj, market_id="JP"):
    rows = build_pressure_rows(**obj)
    found = [row for row in rows if row["market_id"] == market_id]
    assert len(found) == 1
    return found[0]


def _cell(obj, field, market_id="JP"):
    return _row(obj, market_id)[field]






def test_positive_path_all_three_fields_signed_zero_and_independent_clocks():
    obj = _pack(
        values={"country_credit_change": 0, "constituent_breadth_50d": 61, "annual_current_account": -2.5},
        supports={"annual_current_account": {"field_year": 2023, "vintage": "2026-09-15T08:00:00Z", "observation_type": "actual"}},
    )
    obj["measures"]["JP.annual_current_account"]["period"] = {
        "start": "2023-01-01", "end": "2024-01-01", "count": 1, "count_basis": "release_periods",
    }
    obj["measures"]["JP.annual_current_account"]["observation_at"] = "2024-03-01"
    obj["measures"]["JP.country_credit_change"]["calculation_at"] = "2026-10-07T12:00:00Z"
    out = build_pressure_rows(**obj)
    assert [row["market_id"] for row in out] == ["JP", "TW"]
    assert out[0]["name_en"] == "Japan" and out[0]["name_zh"] == "日本"
    credit, breadth, annual = (out[0][name] for name in _FIELDS)
    assert credit["quality"] == "qualified" and credit["reason"] is None and credit["value"] == 0
    assert credit["unit"] == "bp" and credit["period"]["count"] == 20
    assert credit["support"]["scope"] == "country"
    assert credit["calculation_at"] == "2026-10-07T12:00:00Z"
    assert breadth["quality"] == "qualified" and breadth["value"] == 61
    assert breadth["support"]["eligible_count"] == 100 and breadth["support"]["lookback_sessions"] == 50
    assert annual["quality"] == "qualified" and annual["value"] == -2.5
    assert annual["support"]["field_year"] == 2023
    assert annual["support"]["observation_type"] == "actual"
    assert annual["support"]["vintage"] == "2026-09-15T08:00:00Z"
    assert annual["period"]["start"] == "2023-01-01"
    assert out[1]["country_credit_change"] == {"field": "country_credit_change", "quality": "unknown", "reason": "not_supplied"}
    assert out[1]["annual_current_account"]["reason"] == "not_supplied"


def test_second_market_positive_all_three_with_distinct_years():
    obj = _pack(markets=("JP", "TW"))
    obj["measures"]["TW.country_credit_change"] = _measure(
        "country_credit_change", "TW", 7,
        period={"start": "2021-01-04", "end": "2021-02-01", "count": 20, "count_basis": "sessions"},
        observation_at="2021-02-01",
    )
    obj["field_support"]["TW.country_credit_change"] = _support(
        "country_credit_change", "TW", change_start="2021-01-04", change_end="2021-02-01",
    )
    obj["measures"]["TW.constituent_breadth_50d"] = _measure(
        "constituent_breadth_50d", "TW", 25.0, observation_at="2022-05-05",
    )
    obj["field_support"]["TW.constituent_breadth_50d"] = _support(
        "constituent_breadth_50d", "TW", membership_asof="2022-05-05",
        eligible_count=4, above_count=1,
    )
    obj["measures"]["TW.annual_current_account"] = _measure(
        "annual_current_account", "TW", 0,
        period={"start": "2020-01-01", "end": "2021-01-01", "count": 1, "count_basis": "release_periods"},
        observation_at="2021-03-01",
    )
    obj["field_support"]["TW.annual_current_account"] = _support(
        "annual_current_account", "TW", field_year=2020, vintage="2021-03-01", observation_type="estimate",
    )
    tw = _row(obj, "TW")
    assert tw["country_credit_change"]["value"] == 7
    assert tw["constituent_breadth_50d"]["value"] == 25.0
    assert tw["annual_current_account"]["value"] == 0
    assert tw["annual_current_account"]["support"]["field_year"] == 2020
    assert tw["annual_current_account"]["support"]["observation_type"] == "estimate"
    assert _cell(obj, "annual_current_account")["support"]["field_year"] == 2024


@pytest.mark.parametrize("kind,value", [("actual", 1.25), ("estimate", 0), ("projection", -8)])
def test_annual_observation_types_are_preserved_not_relabeled(kind, value):
    obj = _pack(values={"annual_current_account": value}, supports={"annual_current_account": {"observation_type": kind}})
    if kind == "actual":
        obj["measures"]["JP.annual_current_account"]["observation_at"] = "2025-01-01"
    else:
        obj["measures"]["JP.annual_current_account"]["observation_at"] = "2024-06-01"
    out = _cell(obj, "annual_current_account")
    assert out["quality"] == "qualified"
    assert out["value"] == value
    assert out["support"]["observation_type"] == kind
    blob = json.dumps(out)
    assert "observed" not in blob


def test_future_year_actual_is_rejected_projection_is_kept():
    obj = _pack(supports={"annual_current_account": {"field_year": 2027, "observation_type": "actual"}})
    obj["measures"]["JP.annual_current_account"]["period"] = {
        "start": "2027-01-01", "end": "2028-01-01", "count": 1, "count_basis": "release_periods",
    }
    assert _cell(obj, "annual_current_account")["quality"] == "unknown"
    obj["field_support"]["JP.annual_current_account"]["observation_type"] = "projection"
    out = _cell(obj, "annual_current_account")
    assert out["quality"] == "qualified" and out["support"]["observation_type"] == "projection"


def test_annual_actual_requires_native_date_on_or_after_period_end():
    obj = _pack()
    obj["measures"]["JP.annual_current_account"]["observation_at"] = "2024-12-31"
    assert _cell(obj, "annual_current_account") == {
        "field": "annual_current_account", "quality": "unknown", "reason": "support_unavailable",
    }
    obj["measures"]["JP.annual_current_account"]["observation_at"] = "2025-01-01"
    assert _cell(obj, "annual_current_account")["quality"] == "qualified"
    obj["measures"]["JP.annual_current_account"]["observation_at"] = "2023-12-31T22:00:00-12:00"
    assert _cell(obj, "annual_current_account")["quality"] == "unknown"


@pytest.mark.parametrize("part,value", [
    ("field_year", 2025),
    ("field_year", 9999),
    ("field_year", 0),
    ("field_year", True),
    ("field_year", 2024.0),
    ("market_id", "CN"),
    ("vintage", "2026-02-30"),
    ("vintage", "2026-10"),
    ("vintage", None),
    ("observation_type", "max_asof_year"),
    ("observation_type", "observed"),
    ("observation_type", "Actual"),
])
def test_annual_year_vintage_and_type_are_field_specific(part, value):
    obj = _pack()
    obj["field_support"]["JP.annual_current_account"][part] = value
    out = _cell(obj, "annual_current_account")
    assert out["quality"] == "unknown" and out.get("value") is None
    assert _cell(obj, "country_credit_change")["value"] == 0


@pytest.mark.parametrize("scope", ["regional", "EM", "Asia", "LatAm", "EMEA", "global", "country "])
def test_regional_scope_never_substitutes_country_credit(scope):
    obj = _pack()
    obj["field_support"]["JP.country_credit_change"]["scope"] = scope
    out = _cell(obj, "country_credit_change")
    assert out == {"field": "country_credit_change", "quality": "unknown", "reason": "support_unavailable"}
    assert _cell(obj, "annual_current_account")["value"] == 3.4


def test_wrong_country_ids_do_not_fill_target_market():
    obj = _pack(markets=("JP", "TW", "EZ", "DE"))
    obj["measures"]["TW.annual_current_account"] = _measure(
        "annual_current_account", "TW", 8.8, instrument_market="CN", instrument_id="CN-ca",
    )
    obj["field_support"]["TW.annual_current_account"] = _support(
        "annual_current_account", "CN", instrument_id="CN-ca",
    )
    obj["measures"]["EZ.country_credit_change"] = _measure(
        "country_credit_change", "EZ", 5, instrument_market="DE", instrument_id="DE-bund",
    )
    obj["field_support"]["EZ.country_credit_change"] = _support(
        "country_credit_change", "DE", instrument_id="DE-bund",
    )
    obj["measures"]["JP.country_credit_change"]["instrument"]["id"] = "EM-OAS"
    assert _cell(obj, "annual_current_account", "TW")["quality"] == "unknown"
    assert _cell(obj, "country_credit_change", "EZ")["quality"] == "unknown"
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
    assert _cell(obj, "constituent_breadth_50d")["value"] == 61


@pytest.mark.parametrize("part,value", [
    ("eligible_count", 0),
    ("eligible_count", True),
    ("eligible_count", 100.0),
    ("above_count", 101),
    ("above_count", True),
    ("above_count", -1),
    ("lookback_sessions", 200),
    ("lookback_sessions", 50.0),
    ("lookback_sessions", True),
    ("membership_asof", "2026-10-08"),
    ("membership_asof", "2026-10-07T00:00:00Z"),
    ("index_id", "bellwether-sample"),
    ("market_id", "TW"),
    ("membership_ref", ""),
    ("membership_ref", "  members"),
])
def test_breadth_denominator_membership_clock_and_identity(part, value):
    obj = _pack()
    obj["field_support"]["JP.constituent_breadth_50d"][part] = value
    out = _cell(obj, "constituent_breadth_50d")
    assert out["quality"] == "unknown" and out.get("value") is None
    assert _cell(obj, "country_credit_change")["quality"] == "qualified"


def test_zero_breadth_is_a_real_reading_not_missing():
    obj = _pack(values={"constituent_breadth_50d": 0}, supports={"constituent_breadth_50d": {"above_count": 0}})
    out = _cell(obj, "constituent_breadth_50d")
    assert out["quality"] == "qualified" and out["value"] == 0
    assert out["support"]["above_count"] == 0


def test_breadth_does_not_rewrite_owner_percent_and_equal_clocks_pass():
    obj = _pack(values={"constituent_breadth_50d": 60})
    assert _cell(obj, "constituent_breadth_50d")["quality"] == "unknown"
    obj = _pack()
    obj["measures"]["JP.constituent_breadth_50d"]["observation_at"] = "2026-10-07T12:00:00Z"
    obj["field_support"]["JP.constituent_breadth_50d"]["membership_asof"] = "2026-10-07T12:00:00Z"
    assert _cell(obj, "constituent_breadth_50d")["value"] == 61
    obj["field_support"]["JP.constituent_breadth_50d"]["membership_asof"] = "2026-10-07T12:00:01Z"
    assert _cell(obj, "constituent_breadth_50d")["quality"] == "unknown"


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("metadata", ["denied", "unknown"])
def test_metadata_denial_strips_raw_details_and_false_qualified_label(field, metadata):
    obj = _pack()
    obj["measures"][f"JP.{field}"].update(
        metadata=metadata, quality="qualified", reason="SECRET", source_reference="SECRET",
        evidence_key="SECRET", value=123456,
    )
    out = _cell(obj, field)
    assert set(out) == {"field", "quality", "reason"}
    assert out["quality"] == ("denied" if metadata == "denied" else "unknown")
    assert out["reason"] == ("metadata_denied" if metadata == "denied" else "disclosure_unknown")
    blob = json.dumps(out)
    assert "SECRET" not in blob and "123456" not in blob and "qualified" not in blob
    for neighbor in _FIELDS:
        if neighbor != field:
            assert _cell(obj, neighbor)["quality"] == "qualified"


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("permission,quality,reason", [
    ("denied", "denied", "value_denied"),
    ("unknown", "unknown", "disclosure_unknown"),
])
def test_value_permission_cannot_keep_qualified_or_raw_number(field, permission, quality, reason):
    obj = _pack()
    obj["measures"][f"JP.{field}"]["value_permission"] = permission
    obj["measures"][f"JP.{field}"]["reason"] = "SECRET"
    out = _cell(obj, field)
    assert out["quality"] == quality and out["reason"] == reason
    assert out.get("value") is None
    assert "SECRET" not in json.dumps(out)
    assert out.get("unit") is not None


def test_stale_keeps_value_only_with_complete_support_and_allowed_permissions():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["quality"] = "stale"
    out = _cell(obj, "country_credit_change")
    assert out["quality"] == "stale" and out["value"] == 0 and out["reason"] == "source_stale"
    obj["measures"]["JP.country_credit_change"]["value_permission"] = "denied"
    denied = _cell(obj, "country_credit_change")
    assert denied["quality"] == "denied" and denied["value"] is None
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["quality"] = "stale"
    obj["measures"]["JP.country_credit_change"]["evidence_key"] = None
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"


def test_raw_reason_never_crosses_and_noncurrent_statuses_withhold_numbers():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["reason"] = "SECRET_REASON"
    qualified = _cell(obj, "country_credit_change")
    assert qualified["reason"] is None and "SECRET" not in json.dumps(qualified)
    for quality, reason in (
        ("failed", "source_failed"),
        ("unsupported", "method_unsupported"),
        ("missing", "not_supplied"),
        ("unknown", "disclosure_unknown"),
        ("denied", "value_denied"),
    ):
        obj = _pack()
        obj["measures"]["JP.constituent_breadth_50d"]["quality"] = quality
        obj["measures"]["JP.constituent_breadth_50d"]["reason"] = "SECRET"
        obj["measures"]["JP.constituent_breadth_50d"]["value"] = 61
        out = _cell(obj, "constituent_breadth_50d")
        assert out["quality"] == quality and out["reason"] == reason
        assert out["value"] is None and "support" not in out
        assert "SECRET" not in json.dumps(out)


@pytest.mark.parametrize("period", [
    {"start": "2024-01-01", "end": "2024-12-31", "count": 1, "count_basis": "release_periods"},
    {"start": "2024-01-01", "end": "2025-01-01", "count": 12, "count_basis": "release_periods"},
    {"start": "2024-01-01", "end": "2025-01-01", "count": 1, "count_basis": "sessions"},
    {"start": "2024-01-02", "end": "2025-01-01", "count": 1, "count_basis": "release_periods"},
    {"start": "2024-01-01T00:00:00", "end": "2025-01-01T00:00:00", "count": 1, "count_basis": "release_periods"},
])
def test_wrong_annual_interval_is_unsupported(period):
    obj = _pack()
    obj["measures"]["JP.annual_current_account"]["period"] = period
    out = _cell(obj, "annual_current_account")
    assert out["quality"] == "unknown" and out.get("value") is None
    assert _cell(obj, "country_credit_change")["quality"] == "qualified"


@pytest.mark.parametrize("mutator", [
    lambda o: o["field_support"]["JP.country_credit_change"].__setitem__("change_start", "2026-09-08"),
    lambda o: o["field_support"]["JP.country_credit_change"].__setitem__("change_end", "2026-10-06"),
    lambda o: o["measures"]["JP.country_credit_change"].__setitem__("period", None),
    lambda o: o["measures"]["JP.country_credit_change"]["period"].__setitem__("end", "2026-10-06"),
])
def test_wrong_credit_interval_or_missing_period_is_unsupported(mutator):
    obj = _pack()
    mutator(obj)
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
    assert _cell(obj, "annual_current_account")["value"] == 3.4


def test_nonstandard_credit_count_is_retained_not_forced_to_twenty():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["period"]["count"] = 19
    out = _cell(obj, "country_credit_change")
    assert out["quality"] == "qualified" and out["period"]["count"] == 19
    obj["measures"]["JP.country_credit_change"]["period"]["count"] = 10 ** 12
    assert _cell(obj, "country_credit_change")["period"]["count"] == 10 ** 12


def test_huge_finite_integers_are_preserved_without_float_coercion():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["value"] = 10 ** 400
    credit = _cell(obj, "country_credit_change")
    assert credit["quality"] == "qualified" and credit["value"] == 10 ** 400 and type(credit["value"]) is int
    obj["measures"]["JP.annual_current_account"]["value"] = -10 ** 400
    annual = _cell(obj, "annual_current_account")
    assert annual["quality"] == "qualified" and annual["value"] == -10 ** 400 and type(annual["value"]) is int
    obj["measures"]["JP.country_credit_change"]["value"] = 1.7976931348623157e+308
    assert _cell(obj, "country_credit_change")["value"] == 1.7976931348623157e+308


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), float("-inf"), "1", None])
def test_non_finite_or_non_numeric_claims_are_withheld(value):
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["value"] = value
    out = _cell(obj, "country_credit_change")
    assert out["quality"] == "unknown" and out.get("value") is None


def test_output_is_detached_and_inputs_are_not_mutated():
    obj = _pack()
    original = deepcopy(obj)
    out = build_pressure_rows(**obj)
    assert out[0]["country_credit_change"]["instrument"] is not obj["measures"]["JP.country_credit_change"]["instrument"]
    assert out[0]["country_credit_change"]["support"] is not obj["field_support"]["JP.country_credit_change"]
    assert out[0]["country_credit_change"]["period"] is not obj["measures"]["JP.country_credit_change"]["period"]
    out[0]["country_credit_change"]["support"]["method_ref"] = "MUTATED"
    out[0]["country_credit_change"]["instrument"]["id"] = "MUTATED"
    out[0]["country_credit_change"]["period"]["count"] = 1
    out[0]["annual_current_account"]["support"]["field_year"] = 1
    out[0]["name_en"] = "MUTATED"
    assert obj == original
    again = build_pressure_rows(**obj)
    assert again[0]["country_credit_change"]["support"]["method_ref"] == "credit-owner"
    assert again == build_pressure_rows(**obj)


def test_qualified_reason_and_denied_payloads_do_not_leak_sentinels():
    obj = _pack()
    for field in _FIELDS:
        obj["measures"][f"JP.{field}"]["reason"] = "SECRET"
    blob = json.dumps(build_pressure_rows(**obj))
    assert "SECRET" not in blob
    obj["measures"]["JP.country_credit_change"].update(metadata="denied", value=999, source_reference="SECRET")
    blob = json.dumps(build_pressure_rows(**obj))
    assert "SECRET" not in blob and "999" not in blob


class Hostile(dict):
    def get(self, *args, **kwargs):
        raise AssertionError("custom get hook ran")

    def __getitem__(self, key):
        raise AssertionError("custom getitem hook ran")

    def keys(self):
        raise AssertionError("custom keys hook ran")


@pytest.mark.parametrize("target", ["registry", "measures", "field_support"])
def test_hostile_subclasses_are_rejected_before_hooks(target):
    obj = _pack()
    obj[target] = Hostile(obj[target])
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)


def test_cyclic_inputs_are_fixed_invalid_error():
    obj = _pack()
    obj["measures"]["self"] = obj["measures"]
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)
    obj = _pack()
    obj["field_support"]["loop"] = obj["field_support"]
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)
    obj = _pack()
    obj["registry"]["markets"].append(obj["registry"])
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)


@pytest.mark.parametrize("key", ["unknown.field", "CN.country_credit_change", "JP.bad_field", "US.annual_current_account"])
def test_unknown_map_keys_are_fixed_error(key):
    obj = _pack()
    obj["measures"][key] = {}
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)
    obj = _pack()
    obj["field_support"][key] = {}
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)


@pytest.mark.parametrize("bad", [None, [], "x", 1, {"markets": []}])
def test_invalid_whole_containers_are_fixed_error(bad):
    obj = _pack()
    obj["registry"] = bad
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)
    obj = _pack()
    obj["measures"] = []
    with pytest.raises(ValueError, match="^invalid_risk_pressure_input$"):
        build_pressure_rows(**obj)


def test_malformed_cell_does_not_erase_neighbor_or_roster():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"] = {"secret": "SECRET"}
    out = build_pressure_rows(**obj)
    assert [row["market_id"] for row in out] == ["JP", "TW"]
    assert out[0]["country_credit_change"]["quality"] == "unknown"
    assert "SECRET" not in json.dumps(out[0]["country_credit_change"])
    assert out[0]["annual_current_account"]["value"] == 3.4
    assert out[0]["constituent_breadth_50d"]["value"] == 61


@pytest.mark.parametrize("field,kind,unit", [
    ("country_credit_change", "yield_change", "bp"),
    ("constituent_breadth_50d", "country_credit_spread", "percent"),
    ("annual_current_account", "current_account", "percent"),
])
def test_wrong_instrument_or_unit_is_field_unknown(field, kind, unit):
    obj = _pack()
    obj["measures"][f"JP.{field}"]["instrument"]["kind"] = kind
    obj["measures"][f"JP.{field}"]["unit"] = unit
    assert _cell(obj, field)["quality"] == "unknown"


def test_missing_support_or_empty_identity_never_upgrades_raw_value():
    obj = _pack()
    del obj["field_support"]["JP.country_credit_change"]
    assert _cell(obj, "country_credit_change") == {
        "field": "country_credit_change", "quality": "unknown", "reason": "support_unavailable",
    }
    obj = _pack()
    obj["field_support"]["JP.country_credit_change"] = None
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["instrument"]["id"] = ""
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
    obj = _pack()
    obj["field_support"]["JP.country_credit_change"]["method_ref"] = " "
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"


def test_malformed_observation_and_bool_period_count_are_unsupported():
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["observation_at"] = "2026-10-32"
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
    assert _cell(obj, "annual_current_account")["quality"] == "qualified"
    obj = _pack()
    obj["measures"]["JP.country_credit_change"]["period"]["count"] = True
    assert _cell(obj, "country_credit_change")["quality"] == "unknown"
