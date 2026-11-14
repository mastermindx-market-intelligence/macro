"""Contract fixtures consume the real composer, reader and pure Rates owner.

These local temporary publications are not served/authenticated production
receipts. Transport admission, before/after publication recheck and HTTP409 are
deliberately outside this pure phase.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
import pytest

from engine.market_os.macro_workspaces import contract, rates_curves as owner
from lib import macro_rates_scenario_contract as wire
from scripts import build_macro_suite_pages as builder

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def schemas():
    result = {}
    for kind, version in (("request", "v2"), ("result", "v1")):
        path = ROOT / "contracts" / "market_os" / f"macro_workspace_scenario_{kind}.{version}.schema.json"
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        result[kind] = Draft202012Validator(schema, format_checker=FormatChecker())
    return result


def publication_fixture(tmp_path, *, built_at="2026-09-04T12:00:00Z", two=3.8, ten=4.1, frames=None):
    frames = frames if frames is not None else {
        owner.SERIES_US2Y: [("2026-09-02", two)],
        owner.SERIES_US10Y: [("2026-09-02", ten)],
    }
    snapshot = contract.finalize(owner.compose(frames, built_at=built_at, code_version="test-fixture"))
    contract.validate(snapshot)
    body_path = tmp_path / "workspaces/rates_curves/US/latest.json"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(snapshot, sort_keys=True, allow_nan=False) + "\n").encode()
    body_path.write_bytes(raw)
    manifest = {
        "schema": "mastermind.macro_workspace_manifest.v1", "generated_at": built_at,
        "min_client_contract": builder.MIN_CLIENT_CONTRACT,
        "workspaces": {"rates_curves/US": {
            "path": "workspaces/rates_curves/US/latest.json", "bytes": len(raw),
            "content_sha256": snapshot["generation"]["content_sha256"],
            "generation_id": snapshot["generation"]["generation_id"],
        }},
    }
    manifest_raw = json.dumps(manifest, sort_keys=True).encode()
    (tmp_path / "workspaces/manifest.json").write_bytes(manifest_raw)
    page = next(page for page in builder.SUITE_PAGES if page.workspace_id == "rates_curves")
    selected, artifact = builder.read_workspace(tmp_path, page)
    baseline = owner.rates_scenario_baseline(selected)
    publication = {
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "manifest_generated_at": manifest["generated_at"],
        "generation_id": selected["generation"]["generation_id"],
        "artifact": artifact,
    }
    request = {
        "schema": "ontology_scenario_request.v2", "method": owner.RATES_SCENARIO_METHOD,
        "expected_publication": {
            "manifest_sha256": publication["manifest_sha256"],
            "snapshot_content_sha256": selected["generation"]["content_sha256"],
        },
        "assumptions": {"us2y_bp": 100, "us10y_bp": 25},
    }
    return selected, baseline, request, publication


@pytest.fixture
def reading(tmp_path):
    return publication_fixture(tmp_path)


def render(reading, *, assumptions=None):
    _, baseline, request, publication = reading
    request = copy.deepcopy(request)
    if assumptions is not None:
        request["assumptions"] = assumptions
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    return wire.serialize_rates_result(request, calculation, publication=publication)


def test_observed_to_assumed_round_trip_through_actual_owner_and_reader(reading, schemas):
    snapshot, baseline, request, publication = reading
    schemas["request"].validate(wire.normalize_rates_request(request))
    result = render(reading)
    schemas["result"].validate(result)
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["baseline"]["baseline_id"] == baseline.baseline_id
    assert result["baseline"]["us2y"] == {"value": 3.8, "unit": "percent"}
    assert result["baseline"]["us10y"] == {"value": 4.1, "unit": "percent"}
    assert result["baseline"]["curve_2s10s"] == {"value": 30.0, "unit": "bp"}
    assert result["assumed"] == {
        "us2y": {"value": 4.8, "unit": "percent"}, "us10y": {"value": 4.35, "unit": "percent"},
        "curve_2s10s": {"value": -45.0, "unit": "bp"}, "spread_change": {"value": -75, "unit": "bp"},
    }
    assert result["publication"] == publication
    assert result["publication"]["artifact"]["sha256"] == baseline.snapshot_content_sha256
    assert result["baseline"]["sources"][0]["source_ref"] == "FRED:DGS2"
    assert result["baseline"]["sources"][1]["source_ref"] == "FRED:DGS10"
    assert snapshot["scenario_contract"]["execution_available"] is False
    assert snapshot["schema"]["version"] == "1.0.0"
    assert all(value is False for key, value in result["authority"].items() if key != "display_only")
    assert result["authority"]["display_only"] is True
    assert set(result["effects"].values()) == {0}


def test_request_normalization_is_detached(reading):
    _, _, request, _ = reading
    normalized = wire.normalize_rates_request(request)
    request["assumptions"]["us2y_bp"] = -300
    request["expected_publication"]["manifest_sha256"] = "f" * 64
    assert normalized["assumptions"]["us2y_bp"] == 100
    assert normalized["expected_publication"]["manifest_sha256"] != "f" * 64


def test_integral_float_and_zero_result_identity(reading, schemas):
    integer = render(reading, assumptions={"us2y_bp": 0, "us10y_bp": -5})
    integral = render(reading, assumptions={"us2y_bp": -0.0, "us10y_bp": -5.0})
    assert integral == integer
    assert type(integral["assumptions"]["us2y_bp"]) is int
    schemas["result"].validate(integral)


@pytest.mark.parametrize("two,ten,delta", [(-300, 300, 600), (300, -300, -600)])
def test_opposing_shocks_keep_six_hundred_bp_derived_range(reading, schemas, two, ten, delta):
    result = render(reading, assumptions={"us2y_bp": two, "us10y_bp": ten})
    assert result["assumed"]["spread_change"] == {"value": delta, "unit": "bp"}
    schemas["result"].validate(result)


def test_negative_assumed_yields_and_stale_observations_are_not_relabelled(tmp_path, schemas):
    reading = publication_fixture(tmp_path, built_at="2026-09-20T12:00:00Z", two=0.1, ten=0.2)
    result = render(reading, assumptions={"us2y_bp": -300, "us10y_bp": -300})
    assert result["assumed"]["us2y"]["value"] == -2.9
    assert result["assumed"]["us10y"]["value"] == -2.8
    assert {s["freshness"] for s in result["baseline"]["sources"]} == {"STALE_SOURCE"}
    schemas["result"].validate(result)


@pytest.mark.parametrize("location,key,value", [
    ((), "schema", "ontology_scenario_request.v1"),
    ((), "method", "ontology_scenario.rates_adapter.v1"),
    ((), "workspace", "rates_curves"), ((), "region", "US"),
    ((), "baseline", {"us2y_pct": 4.0}), ((), "served_root_qualified", True),
    (("assumptions",), "curve_2s10s_bp", 5), (("assumptions",), "unit", "bp"),
    (("expected_publication",), "baseline_id", "rates-baseline:" + "f" * 64),
    (("expected_publication",), "path", "workspaces/rates_curves/US/latest.json"),
    (("expected_publication",), "manifest_sha256", "sha256:" + "f" * 64),
    (("expected_publication",), "snapshot_content_sha256", "0" * 64),
    (("expected_publication",), "manifest_sha256", "F" * 64),
    (("expected_publication",), "manifest_sha256", None),
])
def test_request_is_closed_at_every_object(reading, schemas, location, key, value):
    request = copy.deepcopy(reading[2])
    target = request
    for part in location:
        target = target[part]
    target[key] = value
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_request$"):
        wire.normalize_rates_request(request)
    with pytest.raises(ValidationError):
        schemas["request"].validate(request)


@pytest.mark.parametrize("bad", [True, False, "5", None, 1, 301, -301, 2.5, float("nan"), float("inf"), 10**400])
def test_nonfinite_boolean_or_out_of_vocabulary_assumptions_are_rejected(reading, bad):
    request = copy.deepcopy(reading[2])
    request["assumptions"]["us2y_bp"] = bad
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_request$"):
        wire.normalize_rates_request(request)


@pytest.mark.parametrize("key", ["schema", "method", "assumptions", "expected_publication"])
def test_missing_request_fields_are_not_defaulted(reading, key):
    request = copy.deepcopy(reading[2])
    del request[key]
    with pytest.raises(wire.RatesScenarioContractError):
        wire.normalize_rates_request(request)


@pytest.mark.parametrize("key", ["manifest_sha256", "snapshot_content_sha256"])
def test_stale_client_expectation_is_a_named_source_change(reading, key):
    _, baseline, request, publication = reading
    request = copy.deepcopy(request)
    request["expected_publication"][key] = "f" * 64
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    with pytest.raises(wire.RatesScenarioContractError, match="^source_changed$"):
        wire.serialize_rates_result(request, calculation, publication=publication)


def test_two_actual_fixture_publications_cannot_be_crossed(tmp_path):
    first = publication_fixture(tmp_path / "first", two=3.8)
    second = publication_fixture(tmp_path / "second", two=4.0)
    old = owner.evaluate_rates_scenario(first[1], first[2]["assumptions"])
    new = owner.evaluate_rates_scenario(second[1], second[2]["assumptions"])
    assert old.baseline.baseline_id != new.baseline.baseline_id
    with pytest.raises(wire.RatesScenarioContractError, match="^source_changed$"):
        wire.serialize_rates_result(first[2], new, publication=second[3])
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_publication$"):
        wire.serialize_rates_result(first[2], old, publication=second[3])


def test_republication_requires_new_expectation_but_keeps_mathematical_identity(tmp_path):
    first = publication_fixture(tmp_path / "first")
    second = publication_fixture(tmp_path / "second", built_at="2026-09-04T13:00:00Z")
    old = render(first)
    new = render(second)
    assert old["calculation_id"] == new["calculation_id"]
    assert old["publication"]["manifest_sha256"] != new["publication"]["manifest_sha256"]
    calculation = owner.evaluate_rates_scenario(second[1], second[2]["assumptions"])
    with pytest.raises(wire.RatesScenarioContractError, match="^source_changed$"):
        wire.serialize_rates_result(first[2], calculation, publication=second[3])


def test_manifest_clock_cannot_predate_a_newer_source_leg(tmp_path):
    reading = publication_fixture(tmp_path, built_at="2026-09-09T12:00:00Z", frames={
        owner.SERIES_US2Y: [("2026-09-02", 3.8), ("2026-09-07", 3.9)],
        owner.SERIES_US10Y: [("2026-09-02", 4.1)],
    })
    _, baseline, request, publication = reading
    assert baseline.observed_at == "2026-09-02"
    assert baseline.sources[0].latest_observed_at == "2026-09-07"
    render(reading)  # The real fixture publication qualifies.
    publication["manifest_generated_at"] = "2026-09-03T12:00:00Z"
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_publication$"):
        wire.serialize_rates_result(request, calculation, publication=publication)


@pytest.mark.parametrize("publication", [None, {}, {"served_root_qualified": True}, {"manifest_sha256": "f" * 64}])
def test_absent_publication_context_cannot_be_manufactured_from_calculation(reading, publication):
    _, baseline, request, _ = reading
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_publication$"):
        wire.serialize_rates_result(request, calculation, publication=publication)


@pytest.mark.parametrize("location,key,value", [
    ((), "manifest_sha256", "0" * 64), ((), "generation_id", "rates_curves-US-" + "f" * 16),
    ((), "manifest_generated_at", "2026-09-01T12:00:00Z"),
    ((), "manifest_generated_at", "2026-09-04"),
    ((), "manifest_generated_at", "2026-02-30T12:00:00Z"),
    ((), "manifest_generated_at", "2026-09-04T12:00:00"),
    ((), "manifest_generated_at", "2026-09-04T12:00:00+00:60"),
    ((), "manifest_generated_at", "2026-09-04T12:00:00+01:99"),
    ((), "historical_vintage_claim", True),
    (("artifact",), "path", "macrodata/workspaces/rates_curves/CN/latest.json"),
    (("artifact",), "path", "../../arbitrary.json"),
    (("artifact",), "manifest_path", "macrodata/other/manifest.json"),
    (("artifact",), "sha256", "f" * 64),
    (("artifact",), "raw_sha256", "f" * 64),
    (("artifact",), "bytes", True), (("artifact",), "bytes", 1.5),
    (("artifact",), "bytes", 0), (("artifact",), "bytes", 2097153),
    (("artifact",), "min_client_contract", "mastermind.macro_workspace_snapshot.v1@1.1.0"),
])
def test_crossed_or_malformed_reader_metadata_is_refused(reading, location, key, value):
    _, baseline, request, original = reading
    publication = copy.deepcopy(original)
    target = publication
    for part in location:
        target = target[part]
    target[key] = value
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_publication$"):
        wire.serialize_rates_result(request, calculation, publication=publication)


@pytest.mark.parametrize("field,bad", [
    ("method_version", "new-method"), ("calculation_id", "rates-scenario:" + "f" * 64),
    ("assumed_us2y_pct", 99.0), ("assumed_us10y_pct", True),
    ("observed_spread_bp", 31.0), ("assumed_spread_bp", float("nan")),
    ("spread_change_bp", -75.0), ("unsupported_effects", ()),
    ("display_only", False), ("display_only", 1),
    ("can_rank", True), ("can_gate", 0), ("can_size", True),
    ("can_originate_signal", True), ("can_execute", True),
    ("canonical_writes", 1), ("alert_writes", False),
    ("portfolio_writes", 0.0), ("calibration_writes", 1),
])
def test_edited_calculation_is_rejected_instead_of_sanitized(reading, field, bad):
    _, baseline, request, publication = reading
    original = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    calculation = replace(original, **{field: bad})
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_calculation$"):
        wire.serialize_rates_result(request, calculation, publication=publication)


def test_crossed_request_baseline_and_assumptions_are_not_accepted(reading):
    _, baseline, request, publication = reading
    calculation = owner.evaluate_rates_scenario(baseline, {"us2y_bp": 0, "us10y_bp": 0})
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_calculation$"):
        wire.serialize_rates_result(request, calculation, publication=publication)
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    edited = replace(calculation, baseline=replace(baseline, us2y_pct=9.0))
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_calculation$"):
        wire.serialize_rates_result(request, edited, publication=publication)
    edited = replace(calculation, assumptions=owner.RatesYieldShifts(100.0, 25.0))
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_calculation$"):
        wire.serialize_rates_result(request, edited, publication=publication)


@pytest.mark.parametrize("location,key,value", [
    ((), "schema", "ontology_scenario_eval.v1"), ((), "region", "CN"),
    ((), "forecast", 1.0), ((), "status", "FORECAST"),
    (("baseline", "us2y"), "unit", "bp"),
    (("assumed", "curve_2s10s"), "unit", "percent"),
    (("assumed",), "portfolio_pnl", 5.0),
    (("assumed", "us10y"), "value", True),
    (("authority",), "can_execute", True), (("effects",), "alert_writes", 1),
    (("effects",), "canonical_writes", False),
    (("baseline", "sources", 0), "source_ref", "FRED:DGS10"),
    (("baseline", "sources", 1), "freshness", "SIMULATED"),
    (("publication",), "rights_grant", "site_full"),
])
def test_public_schema_rejects_wrong_units_evidence_and_new_effects(reading, schemas, location, key, value):
    result = render(reading)
    target = result
    for part in location:
        target = target[part]
    target[key] = value
    with pytest.raises(ValidationError):
        schemas["result"].validate(result)


def test_serializer_detaches_nested_metadata_and_does_not_invent_evaluation_clock(reading):
    _, baseline, request, publication = reading
    calculation = owner.evaluate_rates_scenario(baseline, request["assumptions"])
    first = wire.serialize_rates_result(request, calculation, publication=publication)
    second = wire.serialize_rates_result(request, calculation, publication=publication)
    assert first == second
    request["assumptions"]["us2y_bp"] = -300
    publication["artifact"]["sha256"] = "f" * 64
    assert first["assumptions"]["us2y_bp"] == 100
    assert first["publication"]["artifact"]["sha256"] == baseline.snapshot_content_sha256
    assert "evaluated_at" not in first
    assert "historical_vintage_claim" not in first
