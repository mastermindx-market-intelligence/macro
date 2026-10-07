import copy
import importlib.util
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "intl_workspace_overview", _ROOT / "engine" / "intl_workspace_overview.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
build_overview = _MODULE.build_overview

_WINDOW = {
    "start": "2025-12-18T00:00:00",
    "end": "2026-01-08T00:00:00",
    "calendar_policy": "owner_union_forward_fill",
    "endpoint_observations": {
        "price_start": "2025-12-18T00:00:00",
        "price_end": "2026-01-08T00:00:00",
        "fx_start": "2025-12-18T00:00:00",
        "fx_end": "2026-01-08T00:00:00",
    },
}


def _leg(value, unit="percent", available=True, window=None):
    return {
        "value": value if available else None,
        "unit": unit,
        "numerical_status": "available" if available else "unavailable",
        "reason": None if available else "owner_unavailable",
        "window": copy.deepcopy(_WINDOW if window is None and available else window),
    }


def _record(market_id, value, fx_value=0.0, index_id="^TEST", window=None):
    return {
        "market_id": market_id,
        "index_id": index_id,
        "index_label": f"{market_id} Index",
        "fx_id": f"{market_id}FX",
        "fx_quote_orientation": "USD_per_local",
        "horizon": "1m",
        "requested_observations": 21,
        "return_basis": "price",
        "qualification": "not_evaluated",
        "local": _leg(value),
        "usd": _leg(value, window=window),
        "fx_contribution": _leg(fx_value, unit="percentage_points", window=window),
    }


RAW = {
    "source_reference": "fixture:owner-input",
    "source_reference_reason": None,
    "numerical_status": "partial",
    "reason": "partial_numerical_coverage",
    "records": [
        _record("JP", -12.306610407876228, -31.75105485232067, index_id="^N225"),
        _record("GB", 42.66975308641974, 23.225308641975296, index_id="^FTSE"),
    ],
}
RAW["records"][0]["index_label"] = "Nikkei 225"
RAW["records"][0]["fx_id"] = "USDJPY=X"
RAW["records"][0]["fx_quote_orientation"] = "local_per_USD"
RAW["records"][1]["index_label"] = "FTSE 100"
RAW["records"][1]["fx_id"] = "GBPUSD=X"

ROSTER = [
    {"market_id": market_id, "name_en": f"Market {market_id}", "name_zh": f"市场{market_id}"}
    for market_id in ("JP", "GB")
]
CONTEXT = {
    "horizon": "1m",
    "currency_basis": "usd_unhedged",
    "return_basis": "price",
    "source_reference": RAW["source_reference"],
}


def receipts(data, basis="usd_unhedged", legs=("local", "usd", "fx_contribution"), markets=None):
    output = []
    for record in data["records"]:
        if record["horizon"] != "1m" or (markets is not None and record["market_id"] not in markets):
            continue
        for leg in legs:
            metric = record[leg]
            output.append({
                "binding": {
                    "source_reference": data["source_reference"],
                    "market_id": record["market_id"],
                    "index_id": record["index_id"],
                    "fx_id": record["fx_id"],
                    "horizon": record["horizon"],
                    "currency_basis": basis,
                    "return_basis": "price",
                    "leg": leg,
                    "value": metric["value"],
                    "unit": metric["unit"],
                    "window": copy.deepcopy(metric["window"]),
                },
                "owner_ref": "synthetic:owner",
                "policy_ref": "synthetic:policy",
                "decision_ref": "synthetic:decision",
                "quality": "qualified",
                "reason": None,
                "disclosure": {"metadata": "allowed", "value": "allowed"},
            })
    return output


def project(data=None, qualifications=None, roster=None, context=None):
    return build_overview(
        RAW if data is None else data,
        roster=ROSTER if roster is None else roster,
        context=CONTEXT if context is None else context,
        qualifications=receipts(RAW) if qualifications == "positive" else qualifications,
    )


def expect_error(error, call, message):
    try:
        call()
    except error as exc:
        assert str(exc) == message
    else:
        raise AssertionError(f"expected {message}")


def test_unknown_receipts_preserve_public_rows_and_never_mutate_inputs():
    before = copy.deepcopy(RAW)
    result = project()
    assert RAW == before
    assert result["configured_count"] == 2
    assert result["eligible_count"] == 0
    assert result["ranking_reason"] == "no_qualified_returns"
    assert result["focus_ids"] == []
    assert result["summary"]["fx_eligible_count"] == 0
    assert result["summary"]["fx_detracted_count"] is None
    assert result["context"]["source_reference"] is None
    assert result["context"]["source_reference_reason"] == "not_disclosed_or_unknown"
    assert [row["market_id"] for row in result["rows"]] == ["JP", "GB"]
    assert set(result["rows"][0]) == {
        "slot", "market_id", "name_en", "name_zh", "quality", "reason", "metric"
    }
    assert result["rows"][0]["metric"] == {
        "value": None,
        "unit": "percent",
        "quality": "unknown",
        "reason": "qualification_unknown",
    }
    assert result["rows"][0]["market_id"] == "JP"
    assert result["rows"][0]["reason"] == "qualification_unknown"
    assert set(result["rows"][0]) == {
        "slot", "market_id", "name_en", "name_zh", "quality", "reason", "metric"
    }
    assert set(result["rows"][0]["metric"]) == {"value", "unit", "quality", "reason"}
    assert "fixture:owner-input" not in json.dumps(result)


def test_positive_receipts_disclose_values_exact_identity_and_detachment():
    qualified = receipts(RAW)
    result = project(RAW, qualified)
    assert result["eligible_count"] == 2
    assert result["ranking_count"] == 2
    assert result["focus_ids"] == ["GB", "JP"]
    assert result["rows"][0]["index_id"] == "^N225"
    assert result["rows"][0]["index_label"] == "Nikkei 225"
    assert result["rows"][0]["fx_contribution"]["unit"] == "percentage_points"
    assert result["rows"][0]["metric"]["value"] == RAW["records"][0]["usd"]["value"]
    assert result["summary"]["positive_count"] == 1
    assert result["summary"]["fx_detracted_count"] == 1
    assert result["summary"]["fx_eligible_count"] == 2
    assert result["context"]["source_reference"] == "fixture:owner-input"
    result["rows"][0]["metric"]["window"]["start"] = "1900-01-01T00:00:00"
    assert qualified[0]["binding"]["window"]["start"] == _WINDOW["start"]


def test_empty_no_markets_envelope_is_valid_and_safe():
    data = {
        "source_reference": None,
        "source_reference_reason": None,
        "numerical_status": "unavailable",
        "reason": "no_markets",
        "records": [],
    }
    context = {**CONTEXT, "source_reference": None}
    result = project(data, [], context=context)
    assert result["configured_count"] == 2
    assert result["eligible_count"] == 0
    assert all(row["reason"] == "missing_record" for row in result["rows"])
    assert result["context"]["source_reference"] is None


def test_every_selected_binding_value_must_match_and_foreign_keys_do_not_join():
    for field, replacement in [
        ("source_reference", "synthetic:different"), ("index_id", "^OTHER"),
        ("fx_id", "OTHERFX"), ("currency_basis", "local"), ("value", 1.234),
    ]:
        altered = receipts(RAW)
        receipt = next(q for q in altered if q["binding"]["market_id"] == "JP" and q["binding"]["leg"] == "usd")
        receipt["binding"][field] = replacement
        row = project(RAW, altered)["rows"][0]
        assert row["reason"] == "binding_mismatch"
        assert row["metric"]["value"] is None
        assert set(row) == {"slot", "market_id", "name_en", "name_zh", "quality", "reason", "metric"}
    for field in ("market_id", "horizon"):
        altered = receipts(RAW, legs=("usd",), markets={"JP"})
        altered[0]["binding"][field] = "foreign"
        assert project(RAW, altered)["rows"][0]["reason"] == "qualification_unknown"
    altered = receipts(RAW)
    altered[0]["binding"]["return_basis"] = "total_return"
    expect_error(ValueError, lambda: project(RAW, altered), "invalid_qualification")


def test_null_source_and_unavailable_leg_cannot_be_qualified_numeric():
    data = copy.deepcopy(RAW)
    data["source_reference"] = None
    data["source_reference_reason"] = None
    context = {**CONTEXT, "source_reference": None}
    qualified = receipts(data)
    result = project(data, qualified, context=context)
    assert result["context"]["source_reference"] is None
    assert all(row["metric"]["quality"] == "unknown" for row in result["rows"])
    assert all(row["metric"]["reason"] == "source_unknown" for row in result["rows"])

    unavailable = copy.deepcopy(RAW)
    unavailable["records"][0]["usd"] = {
        "value": None,
        "unit": "percent",
        "numerical_status": "unavailable",
        "reason": "owner_unavailable",
        "window": None,
    }
    qualified = receipts(unavailable)
    row = project(unavailable, qualified)["rows"][0]
    assert row["metric"]["quality"] == "unknown"
    assert row["metric"]["reason"] == "numerical_unavailable"
    assert row["metric"]["window"] is None


def test_rights_denial_shapes_and_recursive_redaction():
    hostile = copy.deepcopy(RAW)
    hostile["private_token"] = "sentinel-secret"
    hostile["records"][0]["private_notes"] = "sentinel-secret"
    qualified = receipts(hostile)
    result = project(hostile, qualified)
    assert "sentinel-secret" not in json.dumps(result, allow_nan=False)

    denied = copy.deepcopy(qualified)
    next(
        item for item in denied
        if item["binding"]["market_id"] == "JP" and item["binding"]["leg"] == "usd"
    )["disclosure"]["metadata"] = "denied"
    assert project(hostile, denied)["rows"][0] == {
        "slot": 0, "quality": "denied", "reason": "metadata_denied"
    }

    denied = copy.deepcopy(qualified)
    for receipt in denied:
        if receipt["binding"]["market_id"] == "JP" and receipt["binding"]["leg"] != "usd":
            receipt["disclosure"]["metadata"] = "denied"
    row = project(hostile, denied)["rows"][0]
    assert row["metric"]["quality"] == "qualified"
    assert row["local"]["reason"] == "not_disclosed"
    assert row["usd"]["quality"] == "qualified"
    assert row["fx_contribution"]["reason"] == "not_disclosed"
    assert all(item["window"] is None for item in (
        row["local"], row["fx_contribution"]
    ))


def test_numeric_schema_and_duplicate_identity_are_deterministic():
    for value in (True, "12", float("inf"), {}, []):
        data = copy.deepcopy(RAW)
        data["records"][0]["usd"]["value"] = value
        expect_error(ValueError, lambda: project(data), "invalid_records")

    duplicate = copy.deepcopy(RAW)
    duplicate["records"][1]["market_id"] = "JP"
    expect_error(ValueError, lambda: project(duplicate), "invalid_records")

    orientation = copy.deepcopy(RAW)
    orientation["records"][0]["fx_quote_orientation"] = "reversed_for_same_market"
    orientation["records"][1]["fx_quote_orientation"] = "USD_per_local"
    expect_error(ValueError, lambda: project(orientation), "invalid_records")

    malformed = copy.deepcopy(receipts(RAW))
    malformed[0]["binding"] = {**malformed[0]["binding"], "unexpected": 1}
    expect_error(ValueError, lambda: project(RAW, malformed), "invalid_qualification")
    malformed = copy.deepcopy(receipts(RAW))
    malformed.append(copy.deepcopy(malformed[0]))
    expect_error(ValueError, lambda: project(RAW, malformed), "invalid_qualification")


def test_exact_near_ties_zero_negative_and_independent_fx_counts():
    near = copy.deepcopy(RAW)
    near["records"][0]["usd"]["value"] = 1.1
    near["records"][1]["usd"]["value"] = 1.0
    assert project(near, receipts(near))["focus_ids"] == ["JP", "GB"]

    zero = copy.deepcopy(RAW)
    zero["records"][0]["usd"]["value"] = 0
    zero["records"][1]["usd"]["value"] = 0
    result = project(zero, receipts(zero))
    assert result["focus_ids"] == ["GB", "JP"]
    assert result["summary"]["positive_count"] == 0
    assert result["summary"]["highest_market_id"] == "GB"
    assert result["summary"]["lowest_market_id"] == "JP"

    negative = copy.deepcopy(RAW)
    negative["records"][0]["usd"]["value"] = -1
    negative["records"][1]["usd"]["value"] = -2
    result = project(negative, receipts(negative))
    assert result["summary"]["positive_count"] == 0
    assert result["summary"]["highest_market_id"] == "JP"
    assert result["summary"]["lowest_market_id"] == "GB"

    data = copy.deepcopy(RAW)
    data["records"][0]["usd"]["value"] = 10
    data["records"][1]["usd"]["value"] = 20
    data["records"][0]["fx_contribution"]["window"]["start"] = "2025-12-19T00:00:00"
    result = project(data, receipts(data))
    assert result["summary"]["fx_eligible_count"] == 1
    assert result["summary"]["fx_detracted_count"] == 0
    assert result["rows"][0]["local"]["quality"] == "qualified"
    assert result["rows"][0]["fx_contribution"]["value"] is not None


def _many(count):
    ids = [f"M{index:02d}" for index in range(count)]
    data = {
        **RAW,
        "records": [
            _record(market_id, -index, fx_value=-index if index % 2 else index)
            for index, market_id in enumerate(ids)
        ],
    }
    roster = [
        {"market_id": market_id, "name_en": market_id, "name_zh": market_id}
        for market_id in ids
    ]
    return data, roster


def test_eligibility_counts_and_focus_boundaries_zero_one_two_four_and_more():
    result = project()
    assert result["eligible_count"] == 0 and result["focus_ids"] == []

    one = receipts(RAW, legs=("usd",), markets={"GB"})
    result = project(RAW, one)
    assert result["eligible_count"] == 1 and result["focus_ids"] == ["GB"]

    assert [project(RAW, receipts(RAW))["focus_ids"][i] for i in (0, 1)] == ["GB", "JP"]

    four, roster = _many(4)
    result = project(four, receipts(four), roster=roster)
    assert result["focus_ids"] == ["M00", "M01", "M02", "M03"]
    assert len(set(result["focus_ids"])) == 4

    six, roster = _many(6)
    result = project(six, receipts(six), roster=roster)
    assert result["focus_ids"] == ["M00", "M01", "M02", "M05"]
    assert len(set(result["focus_ids"])) == 4


def test_unequal_windows_withhold_ranking_but_retain_rows():
    unequal = copy.deepcopy(RAW)
    unequal["records"][1]["usd"]["window"]["start"] = "2025-12-19T00:00:00"
    result = project(unequal, receipts(unequal))
    assert result["eligible_count"] == 2
    assert result["ranking_count"] == 0
    assert result["ranking_reason"] == "unequal_windows"
    assert result["focus_ids"] == []
    assert result["summary"]["positive_count"] is None
    assert result["summary"]["fx_detracted_count"] is None
    assert result["summary"]["fx_eligible_count"] == 0
    assert all(row["metric"]["value"] is not None for row in result["rows"])


def test_local_survives_without_fx_and_context_basis_selects_correct_leg():
    data = copy.deepcopy(RAW)
    for record in data["records"]:
        record["fx_contribution"] = {
            "value": None, "unit": "percentage_points", "numerical_status": "unavailable",
            "reason": "owner_unavailable", "window": None,
        }
    qualified = receipts(data, basis="local", legs=("local",))
    result = project(data, qualified, context={**CONTEXT, "currency_basis": "local"})
    assert result["eligible_count"] == 2
    assert all(row["metric"]["value"] == row["local"]["value"] for row in result["rows"])
    assert all(row["usd"]["reason"] == "qualification_unknown" for row in result["rows"])
    assert result["summary"]["fx_eligible_count"] == 0


# Exact actual-owner synthetic frame output, embedded for portable repository tests.
OWNER_FIXTURE_JSON = '{\n  "source_reference": "fixture:owner-input",\n  "source_reference_reason": null,\n  "numerical_status": "partial",\n  "reason": "partial_numerical_coverage",\n  "records": [\n    {\n      "market_id": "JP",\n      "index_id": "^N225",\n      "index_label": "Nikkei 225",\n      "fx_id": "USDJPY=X",\n      "fx_quote_orientation": "local_per_USD",\n      "horizon": "1m",\n      "requested_observations": 21,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": 19.444444444444443,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "usd": {\n        "value": -12.306610407876228,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "fx_contribution": {\n        "value": -31.75105485232067,\n        "unit": "percentage_points",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      }\n    },\n    {\n      "market_id": "JP",\n      "index_id": "^N225",\n      "index_label": "Nikkei 225",\n      "fx_id": "USDJPY=X",\n      "fx_quote_orientation": "local_per_USD",\n      "horizon": "3m",\n      "requested_observations": 63,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "JP",\n      "index_id": "^N225",\n      "index_label": "Nikkei 225",\n      "fx_id": "USDJPY=X",\n      "fx_quote_orientation": "local_per_USD",\n      "horizon": "6m",\n      "requested_observations": 126,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "JP",\n      "index_id": "^N225",\n      "index_label": "Nikkei 225",\n      "fx_id": "USDJPY=X",\n      "fx_quote_orientation": "local_per_USD",\n      "horizon": "12m",\n      "requested_observations": 252,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "JP",\n      "index_id": "^N225",\n      "index_label": "Nikkei 225",\n      "fx_id": "USDJPY=X",\n      "fx_quote_orientation": "local_per_USD",\n      "horizon": "ytd",\n      "requested_observations": null,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": 6.6115702479338845,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "usd": {\n        "value": -4.184538131603722,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "fx_contribution": {\n        "value": -10.796108379537607,\n        "unit": "percentage_points",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      }\n    },\n    {\n      "market_id": "GB",\n      "index_id": "^FTSE",\n      "index_label": "FTSE 100",\n      "fx_id": "GBPUSD=X",\n      "fx_quote_orientation": "USD_per_local",\n      "horizon": "1m",\n      "requested_observations": 21,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": 19.444444444444443,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "usd": {\n        "value": 42.66975308641974,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "fx_contribution": {\n        "value": 23.225308641975296,\n        "unit": "percentage_points",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-18T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-18T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-18T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      }\n    },\n    {\n      "market_id": "GB",\n      "index_id": "^FTSE",\n      "index_label": "FTSE 100",\n      "fx_id": "GBPUSD=X",\n      "fx_quote_orientation": "USD_per_local",\n      "horizon": "3m",\n      "requested_observations": 63,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "GB",\n      "index_id": "^FTSE",\n      "index_label": "FTSE 100",\n      "fx_id": "GBPUSD=X",\n      "fx_quote_orientation": "USD_per_local",\n      "horizon": "6m",\n      "requested_observations": 126,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "GB",\n      "index_id": "^FTSE",\n      "index_label": "FTSE 100",\n      "fx_id": "GBPUSD=X",\n      "fx_quote_orientation": "USD_per_local",\n      "horizon": "12m",\n      "requested_observations": 252,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "usd": {\n        "value": null,\n        "unit": "percent",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      },\n      "fx_contribution": {\n        "value": null,\n        "unit": "percentage_points",\n        "numerical_status": "unavailable",\n        "reason": "insufficient_history",\n        "window": null\n      }\n    },\n    {\n      "market_id": "GB",\n      "index_id": "^FTSE",\n      "index_label": "FTSE 100",\n      "fx_id": "GBPUSD=X",\n      "fx_quote_orientation": "USD_per_local",\n      "horizon": "ytd",\n      "requested_observations": null,\n      "return_basis": "price",\n      "qualification": "not_evaluated",\n      "local": {\n        "value": 6.6115702479338845,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "usd": {\n        "value": 13.660269107301403,\n        "unit": "percent",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      },\n      "fx_contribution": {\n        "value": 7.048698859367518,\n        "unit": "percentage_points",\n        "numerical_status": "available",\n        "reason": null,\n        "window": {\n          "start": "2025-12-31T00:00:00",\n          "end": "2026-01-08T00:00:00",\n          "calendar_policy": "owner_union_forward_fill",\n          "endpoint_observations": {\n            "price_start": "2025-12-31T00:00:00",\n            "price_end": "2026-01-08T00:00:00",\n            "fx_start": "2025-12-31T00:00:00",\n            "fx_end": "2026-01-08T00:00:00"\n          }\n        }\n      }\n    }\n  ]\n}\n'


def test_actual_owner_fixture_is_compatible_without_external_files():
    data = json.loads(OWNER_FIXTURE_JSON)
    ctx = {**CONTEXT, "source_reference": data["source_reference"]}
    before = copy.deepcopy(data)
    result = project(data, receipts(data), context=ctx)
    assert result["focus_ids"] == ["GB", "JP"]
    assert result["rows"][0]["index_label"] == "Nikkei 225"
    assert result["rows"][0]["metric"]["value"] == data["records"][0]["usd"]["value"]
    assert data == before


def test_selected_mismatch_or_unknown_never_releases_secondary_values():
    for change in ("mismatch", "unknown"):
        q = receipts(RAW)
        selected = next(x for x in q if x["binding"]["market_id"] == "JP" and x["binding"]["leg"] == "usd")
        if change == "mismatch":
            selected["binding"]["currency_basis"] = "local"
        else:
            selected["disclosure"]["metadata"] = "unknown"
        row = project(RAW, q)["rows"][0]
        assert set(row) == {"slot", "market_id", "name_en", "name_zh", "quality", "reason", "metric"}
        assert row["metric"]["value"] is None
        assert row["reason"] == ("binding_mismatch" if change == "mismatch" else "qualification_unknown")


def test_qualification_states_retain_reason_but_never_publish_numeric_values():
    for quality in ("stale", "missing", "denied", "failed", "unsupported", "unknown"):
        q = receipts(RAW)
        for item in q:
            item.update(quality=quality, reason="private upstream text")
        result = project(RAW, q)
        assert result["eligible_count"] == 0
        assert result["rows"][0]["metric"]["quality"] == quality
        assert result["rows"][0]["metric"]["reason"] == "quality_" + quality
        assert "private upstream text" not in json.dumps(result)


def test_bad_enum_containers_and_wrong_observation_counts_refuse_deterministically():
    for value in ([], {}, True, 1, None):
        data = copy.deepcopy(RAW); data["numerical_status"] = value
        expect_error(ValueError, lambda: project(data), "invalid_records")
        q = receipts(RAW); q[0]["quality"] = value
        expect_error(ValueError, lambda: project(RAW, q), "invalid_qualification")
        ctx = {**CONTEXT, "currency_basis": value}
        expect_error(ValueError, lambda: project(context=ctx), "invalid_context")
    for value in (True, 0, -1, 1.5, "21"):
        data = copy.deepcopy(RAW); data["records"][0]["requested_observations"] = value
        expect_error(ValueError, lambda: project(data), "invalid_records")


def test_no_custom_containers_cycles_or_nonfinite_extras():
    class CustomDict(dict): pass
    class CustomList(list): pass
    expect_error(ValueError, lambda: project(CustomDict(RAW)), "invalid_records")
    expect_error(ValueError, lambda: project(roster=CustomList(ROSTER)), "invalid_request")
    expect_error(ValueError, lambda: project(qualifications=CustomList()), "invalid_qualification")
    data = copy.deepcopy(RAW); data["private"] = data
    expect_error(ValueError, lambda: project(data), "invalid_records")
    for value in (float("nan"), float("inf"), float("-inf")):
        data = copy.deepcopy(RAW); data["extra"] = value
        expect_error(ValueError, lambda: project(data), "invalid_records")


def test_large_integer_and_binary64_near_ties_are_sorted_without_decimal_context_rounding():
    for low, high in [(10 ** 35, 10 ** 35 + 1), (1.0, 1.0000000000000002)]:
        data = copy.deepcopy(RAW)
        data["records"][0]["usd"]["value"] = high
        data["records"][1]["usd"]["value"] = low
        assert project(data, receipts(data))["focus_ids"] == ["JP", "GB"]


def _precision_project(start, end, contributor=None):
    raw = copy.deepcopy(RAW)
    for row in raw["records"]:
        for leg in ("local", "usd", "fx_contribution"):
            window = row[leg]["window"]
            window.update(start=start, end=end)
            window["endpoint_observations"] = {key: None for key in window["endpoint_observations"]}
            if contributor is not None:
                window["endpoint_observations"]["price_end"] = contributor
    return project(raw, receipts(raw))


def test_submicrosecond_chronology_and_contributor_order_are_exact():
    for precision in (1, 6, 7, 8, 9):
        earlier = "2026-01-08T00:00:00." + "0" * (precision - 1) + "1"
        later = "2026-01-08T00:00:00." + "0" * (precision - 1) + "2"
        result = _precision_project(earlier, later)
        assert result["ranking_status"] == "available"
        assert result["rows"][0]["metric"]["window"]["start"] == earlier
        assert result["rows"][0]["metric"]["window"]["end"] == later
        expect_error(ValueError, lambda: _precision_project(later, earlier), "invalid_records")
        expect_error(ValueError, lambda: _precision_project(earlier, earlier, later), "invalid_records")


def test_offsets_and_fractional_precision_preserve_exact_chronology():
    pairs = [
        ("2026-01-08T00:00:00.000000001Z", "2026-01-08T01:00:00.000000001+01:00"),
        ("2026-01-07T23:59:59.999999999-01:00", "2026-01-08T00:59:59.999999999Z"),
        ("2026-01-08T01:00:00.5+01.5", "2026-01-08T00:00:00Z"),
        ("2026-01-08T01:00:00.5+0100.5", "2026-01-08T00:00:00Z"),
        ("2026-01-08T01:00:00.000000001+01:00:00.000000001", "2026-01-08T00:00:00Z"),
    ]
    for start, end in pairs:
        assert _precision_project(start, end)["ranking_status"] == "available"
        assert _precision_project(end, start)["ranking_status"] == "available"
    expect_error(ValueError, lambda: _precision_project("2026-01-08T00:00:00.000000002Z", "2026-01-08T01:00:00.000000001+01:00"), "invalid_records")
    expect_error(ValueError, lambda: _precision_project("2026-01-08T00:00:00Z", "2026-01-08T00:00:00"), "invalid_records")


def test_receipt_window_nanosecond_chronology_is_also_validated():
    q = receipts(RAW)
    window = q[0]["binding"]["window"]
    window.update(start="2026-01-08T00:00:00.000000002", end="2026-01-08T00:00:00.000000001")
    window["endpoint_observations"] = {key: None for key in window["endpoint_observations"]}
    expect_error(ValueError, lambda: project(RAW, q), "invalid_qualification")


# Optional production-input composition; the grants below are synthetic only.
import pytest


def _production_fixture():
    from engine import intl_inputs
    from engine.intl_performance_records import build_return_records
    spec = importlib.util.spec_from_file_location(
        'workspace_qualification_fixture', Path(__file__).with_name('test_intl_source_qualification.py'))
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    frame = fixture._frame().drop(columns=['USDJPY=X'])
    bases = {series: 'synthetic-adjusted-close' for series in fixture.SERIES_IDS}
    snapshot = intl_inputs.source_snapshot(frame, source_reference='pending', adjustment_bases=bases)
    ref = 'intl-supplied-close:sha256:' + snapshot['content_sha256']
    snapshot = intl_inputs.source_snapshot(frame, source_reference=ref, adjustment_bases=bases)
    raw = build_return_records(frame, market_ids=list(intl_inputs.countries()), source_reference=ref)
    evidence = fixture._evidence(snapshot)
    evidence = [item for item in evidence if item['series_id'] == '^N225']
    decisions = [item for item in fixture._decisions(raw, snapshot) if item['market_id'] == 'JP']
    for item in evidence + decisions: item['source_reference'] = ref
    inputs = dict(adjustment_bases=bases, source_evidence=evidence,
                  disclosure_decisions=decisions, policy_id=fixture.POLICY_ID)
    return frame, inputs, ref


_GENERATION = 'im-workspace-generation:9e1a5667-47f3-4a69-a784-b971e3ba74ba'


def _production_workspace(frame, inputs, generation=_GENERATION):
    return _MODULE.build_workspace_overviews(frame, production_inputs=inputs,
                                             workspace_generation=generation)


def _production_panel(workspace, basis='local', horizon='1m'):
    return next(p['overview'] for p in workspace['panels']
                if p['overview']['context']['horizon'] == horizon
                and p['overview']['context']['currency_basis'] == basis)


def test_optional_supplied_inputs_preserve_legacy_unknown_mode():
    frame, _, _ = _production_fixture()
    old = _MODULE.build_workspace_overviews(frame)
    assert old == _MODULE.build_workspace_overviews(frame, production_inputs=None, workspace_generation=None)
    assert 'binding_version' not in old and old['config']['source_reference'] is None
    assert all('generation' not in p for p in old['panels'])
    assert all(r['metric']['value'] is None for p in old['panels'] for r in p['overview']['rows'])


def test_supplied_local_only_evidence_keeps_partial_source_disclosure_and_original_inputs(monkeypatch):
    import pandas as pd
    from engine import intl_inputs
    from lib import store
    frame, inputs, ref = _production_fixture(); original = frame.copy(deep=True); before = copy.deepcopy(inputs)
    def forbidden(*args, **kwargs): raise AssertionError('unexpected source I/O')
    monkeypatch.setattr(intl_inputs, '_intl_closes', forbidden); monkeypatch.setattr(store, 'read', forbidden)
    result = _production_workspace(frame, inputs)
    assert result['binding_version'] == 2
    assert result['config']['source_reference'] == _GENERATION
    assert all(p['generation'] == _GENERATION for p in result['panels'])
    local = _production_panel(result); usd = _production_panel(result, 'usd_unhedged')
    jp = next(r for r in local['rows'] if r.get('market_id') == 'JP')
    assert jp['metric']['quality'] == 'qualified' and jp['metric']['value'] is not None
    assert local['context']['source_reference'] == ref
    assert usd['context']['source_reference'] is None
    assert all(r['metric']['value'] is None for r in usd['rows'])
    assert _GENERATION not in json.dumps([p['overview'] for p in result['panels']])
    assert not any(text in json.dumps(result) for text in ['synthetic-owner-decision','synthetic-disclosure-decision','qualification_context','source_evidence','adjustment_bases'])
    pd.testing.assert_frame_equal(frame, original); assert inputs == before


def test_publication_nonce_changes_only_replay_identity_not_source_or_values():
    frame, inputs, _ = _production_fixture()
    first = _production_workspace(frame, inputs)
    second = _production_workspace(frame, inputs, 'im-workspace-generation:920e1ffa-2523-4621-8701-957792b362f0')
    assert first['config']['source_reference'] != second['config']['source_reference']
    assert [p['overview'] for p in first['panels']] == [p['overview'] for p in second['panels']]


@pytest.mark.parametrize('generation', [None, '', 'source:private', 'im-workspace-generation:'+'a'*64,
                                      'im-workspace-generation:9E1A5667-47F3-4A69-A784-B971E3BA74BA',
                                      'im-workspace-generation:9e1a5667-47f3-1a69-a784-b971e3ba74ba'])
def test_supplied_mode_requires_canonical_opaque_v4_publication_generation(generation):
    frame, inputs, _ = _production_fixture()
    with pytest.raises(ValueError): _production_workspace(frame, inputs, generation)


@pytest.mark.parametrize('mutate', [lambda p: [], lambda p: {**p, 'extra': True},
                                   lambda p: {k:v for k,v in p.items() if k != 'policy_id'},
                                   lambda p: {**p, 'source_evidence': tuple(p['source_evidence'])}])
def test_supplied_envelope_is_closed_plain_data(mutate):
    frame, inputs, _ = _production_fixture()
    with pytest.raises(ValueError): _production_workspace(frame, mutate(inputs))


def test_generation_without_supplied_inputs_is_rejected():
    with pytest.raises(ValueError): _production_workspace(None, None)


@pytest.mark.parametrize('change', ['observation','basis','evidence_source','evidence_content','decision_source','decision_content','decision_horizon','decision_basis','decision_leg'])
def test_old_or_mismatched_evidence_is_never_rebound_to_new_material(change):
    frame, inputs, _ = _production_fixture()
    inputs['disclosure_decisions'] = [item for item in inputs['disclosure_decisions'] if item['horizon'] == '1m']
    if change == 'observation': frame.iloc[-1,0] += 1
    elif change == 'basis': inputs['adjustment_bases']['^N225'] = 'synthetic-other-basis'
    elif change.startswith('evidence_'):
        key = 'source_reference' if change.endswith('source') else 'content_sha256'
        inputs['source_evidence'][0][key] = 'wrong-source' if key == 'source_reference' else '0'*64
    else:
        key = {'source':'source_reference','content':'content_sha256','horizon':'horizon','basis':'currency_basis','leg':'leg'}[change.split('_')[1]]
        for item in inputs['disclosure_decisions']:
            item[key] = {'source_reference':'wrong-source','content_sha256':'0'*64,'horizon':'wrong-horizon','currency_basis':'usd_unhedged','leg':'usd'}[key]
    result = _production_workspace(frame, inputs)
    assert all(r.get('metric',{}).get('quality') != 'qualified' for p in result['panels'] for r in p['overview']['rows'])


@pytest.mark.parametrize('state', ['missing_rights','metadata_denied','value_denied','session_unknown','basis_unknown'])
def test_supplied_unknown_or_denied_decisions_remain_honest(state):
    frame, inputs, _ = _production_fixture()
    if state == 'missing_rights': inputs['disclosure_decisions'] = []
    elif state == 'session_unknown': inputs['source_evidence'] = []
    elif state == 'basis_unknown': inputs['source_evidence'][0]['basis_state'] = 'unknown'
    else:
        for item in inputs['disclosure_decisions']: item['metadata' if state == 'metadata_denied' else 'value'] = 'denied'
    result = _production_workspace(frame, inputs); local = _production_panel(result)
    if state == 'metadata_denied':
        assert local['rows'][0] == {'slot':0,'quality':'denied','reason':'metadata_denied'}
        assert local['context']['source_reference'] is None
    else:
        jp = next(r for r in local['rows'] if r.get('market_id') == 'JP')
        assert jp['metric']['value'] is None


def test_one_horizon_grant_does_not_disclose_source_in_other_contexts():
    frame, inputs, ref = _production_fixture()
    inputs['disclosure_decisions'] = [item for item in inputs['disclosure_decisions'] if item['horizon'] == '1m']
    result = _production_workspace(frame, inputs)
    for panel in result['panels']:
        context = panel['overview']['context']
        allowed = context['horizon'] == '1m' and context['currency_basis'] == 'local'
        assert context['source_reference'] == (ref if allowed else None)
        assert panel['generation'] == _GENERATION
