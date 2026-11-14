"""Versioned source capability, independent of the incumbent access authority.

The fixtures use the real composer, manifest reader, selected GET projection
and baseline owner. They never enable the production publisher or call a
provider, browser, entitlement service or deployed endpoint.
"""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from app import macro_command as mc
from engine.market_os.macro_workspaces import contract, rates_curves as owner
from lib import macro_rates_scenario_contract as wire
from scripts import build_macro_suite_pages as builder
from test_macro_rates_scenario_contract import publication_fixture


OLD = "mastermind.macro_workspace_snapshot.v1@1.0.0"
NEW = "mastermind.macro_workspace_snapshot.v1@1.1.0"
PAGE = next(p for p in builder.SUITE_PAGES if p.workspace_id == "rates_curves")


def republish(root, snapshot, token):
    snapshot = contract.finalize(snapshot)
    body = root / "workspaces/rates_curves/US/latest.json"
    raw = (json.dumps(snapshot, sort_keys=True, allow_nan=False) + "\n").encode()
    body.write_bytes(raw)
    manifest = {
        "schema": "mastermind.macro_workspace_manifest.v1",
        "generated_at": snapshot["generation"]["built_at"], "min_client_contract": token,
        "workspaces": {"rates_curves/US": {
            "path": "workspaces/rates_curves/US/latest.json", "bytes": len(raw),
            "content_sha256": snapshot["generation"]["content_sha256"],
            "generation_id": snapshot["generation"]["generation_id"],
        }},
    }
    raw_manifest = json.dumps(manifest, sort_keys=True).encode()
    (root / "workspaces/manifest.json").write_bytes(raw_manifest)
    return snapshot, raw_manifest


def changed(snapshot, path, value):
    result = copy.deepcopy(snapshot)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return contract.finalize(result)


def test_default_publication_stays_old_and_disabled(tmp_path):
    snapshot, _, _, publication = publication_fixture(tmp_path)
    assert contract.CONTRACT_VERSION == "1.0.0"
    assert builder.MIN_CLIENT_CONTRACT == OLD
    assert snapshot["schema"]["version"] == "1.0.0"
    assert snapshot["scenario_contract"]["execution_available"] is False
    assert len(snapshot["scenario_contract"]["assumptions"]) == 5
    assert wire.rates_scenario_source(snapshot, publication) == {
        "schema": wire.SOURCE_SCHEMA, "source_state": "disabled",
        "reason": "publication_disabled",
        "access": {"required_feature": "site_full", "state": "not_checked"},
    }
    with pytest.raises(wire.RatesScenarioUnavailable, match="^scenario_disabled$"):
        wire.qualify_rates_publication(snapshot, publication)


@pytest.mark.parametrize("minimum,version,accepted", [
    (OLD, "1.0.0", True), (OLD, "1.1.0", False),
    (NEW, "1.0.0", True), (NEW, "1.1.0", True),
    ("mastermind.macro_workspace_snapshot.v1@1.2.0", "1.0.0", False),
    (NEW, "1.2.0", False), (NEW, "1.1", False),
])
def test_exact_manifest_snapshot_compatibility(tmp_path, minimum, version, accepted):
    snapshot, *_ = publication_fixture(tmp_path)
    snapshot["schema"]["version"] = version
    republish(tmp_path, snapshot, minimum)
    if accepted:
        result, artifact = builder.read_workspace(tmp_path, PAGE)
        assert result["schema"]["version"] == version
        assert artifact["min_client_contract"] == minimum
    else:
        with pytest.raises(builder.SnapshotRefused):
            builder.read_workspace(tmp_path, PAGE)


@pytest.mark.parametrize("path,value", [
    (("schema", "version"), "1.0.0"),
    (("workspace", "id"), "growth_real_economy"),
    (("region", "code"), "CN"), (("region", "supported"), False),
    (("scenario_contract", "method"), "rates_curves.other.v1"),
    (("scenario_contract", "request_schema"), "ontology_scenario_request.v1"),
    (("scenario_contract", "result_schema"), "unqualified.result.v1"),
    (("scenario_contract", "status"), "PARTIAL"),
    (("scenario_contract", "assumptions", 0, "assumption_id"), "curve_2s10s_bp"),
    (("scenario_contract", "assumptions", 0, "unit"), "percent"),
    (("scenario_contract", "assumptions", 0, "min"), -305),
    (("scenario_contract", "assumptions", 0, "max"), 305),
    (("scenario_contract", "assumptions", 0, "step"), 1),
    (("scenario_contract", "assumptions", 0, "owner_field"), "fred.DGS10"),
    (("scenario_contract", "assumptions", 1, "assumption_id"), "us2y_bp"),
    (("scenario_contract", "execution_available"), 1),
])
def test_enabled_capability_is_closed_to_exact_supported_method(tmp_path, path, value):
    snapshot, _, _, publication = publication_fixture(tmp_path, scenario_enabled=True)
    invalid = changed(snapshot, path, value)
    with pytest.raises(contract.ContractError):
        contract.validate(invalid)
    result = wire.rates_scenario_source(invalid, publication)
    assert result["source_state"] == "unavailable"
    assert "baseline" not in result and result["access"]["state"] == "not_checked"


@pytest.mark.parametrize("mutation", ["missing", "extra", "unknown", "disabled_with_enabled_fields"])
def test_capability_vocabulary_has_no_partial_or_implicit_enablement(tmp_path, mutation):
    snapshot, *_ = publication_fixture(tmp_path, scenario_enabled=True)
    capability = snapshot["scenario_contract"]
    if mutation == "missing": capability["assumptions"].pop()
    elif mutation == "extra": capability["assumptions"].append(copy.deepcopy(capability["assumptions"][0]))
    elif mutation == "unknown": capability["execute"] = True
    else: capability["execution_available"] = False
    with pytest.raises(contract.ContractError):
        contract.validate(contract.finalize(snapshot))


def test_selected_get_exposes_common_date_source_without_calculation_or_access_claim(tmp_path, monkeypatch):
    root = tmp_path / "site.served"
    frames = {owner.SERIES_US2Y: [("2026-09-01", 3.8), ("2026-09-02", 3.9)],
              owner.SERIES_US10Y: [("2026-09-01", 4.1)]}
    snapshot, baseline, _, publication = publication_fixture(root / "macrodata", frames=frames,
                                                           scenario_enabled=True)
    monkeypatch.setattr(mc, "_served_root", lambda: root)
    monkeypatch.setattr(owner, "evaluate_rates_scenario", lambda *_a, **_k: pytest.fail("GET executed a scenario"))
    read = mc.compose_macro_command("rates_curves")
    selected = read["selected_workspace"]
    assert selected["state"] == "ready"
    source = selected["scenario"]
    assert source["source_state"] == "qualified"
    assert source["snapshot_version"] == "1.1.0"
    assert source["method"] == owner.RATES_SCENARIO_METHOD
    assert source["request_schema"] == wire.REQUEST_SCHEMA and source["result_schema"] == wire.RESULT_SCHEMA
    assert source["access"] == {"required_feature": "site_full", "state": "not_checked"}
    assert set(source) == {"schema", "source_state", "snapshot_version", "method", "request_schema",
                           "result_schema", "access", "assumptions", "publication", "baseline"}
    assert source["publication"] == publication
    assert source["baseline"]["baseline_id"] == baseline.baseline_id
    assert source["baseline"]["observed_at"] == "2026-09-01"
    assert source["baseline"]["us2y"] == {"value": 3.8, "unit": "percent"}
    assert source["baseline"]["us10y"] == {"value": 4.1, "unit": "percent"}
    assert source["baseline"]["curve_2s10s"] == {"value": 30, "unit": "bp"}
    assert source["baseline"]["sources"][0]["latest_observed_at"] == "2026-09-02"
    assert read["source"]["min_client_contract"] == selected["artifact"]["min_client_contract"] == NEW
    source["assumptions"][0]["label"]["en"] = "local edit"
    assert snapshot["scenario_contract"]["assumptions"][0]["label"]["en"] != "local edit"


def test_enabled_source_without_common_observation_keeps_reading_and_refuses_scenario(tmp_path, monkeypatch):
    root = tmp_path / "site.served"
    snapshot, *_ = publication_fixture(root / "macrodata", scenario_enabled=True)
    for row in snapshot["series"]["items"]:
        if row["series_id"] == "us2y":
            row["points"] = []
    republish(root / "macrodata", snapshot, NEW)
    monkeypatch.setattr(mc, "_served_root", lambda: root)
    read = mc.compose_macro_command("rates_curves")
    assert read["selected_workspace"]["state"] == "ready"
    assert read["selected_workspace"]["scenario"]["source_state"] == "unavailable"
    assert "baseline" not in read["selected_workspace"]["scenario"]


def test_valid_disabled_successor_reports_actual_publication_change_first(tmp_path):
    _, _, previous, _ = publication_fixture(tmp_path / "before", scenario_enabled=True)
    snapshot, _, current, publication = publication_fixture(tmp_path / "after")
    assert previous["expected_publication"] != current["expected_publication"]
    with pytest.raises(wire.RatesScenarioContractError, match="^source_changed$"):
        wire.qualify_rates_publication(snapshot, publication,
                                       expected_publication=previous["expected_publication"])
    with pytest.raises(wire.RatesScenarioUnavailable, match="^scenario_disabled$"):
        wire.qualify_rates_publication(snapshot, publication,
                                       expected_publication=current["expected_publication"])


@pytest.mark.parametrize("path,value", [
    (("artifact", "bytes"), True), (("artifact", "path"), "untrusted/latest.json"),
    (("artifact", "min_client_contract"), OLD),
    (("manifest_generated_at",), "2020-01-01T00:00:00Z"),
    (("manifest_sha256",), "not-a-digest"), (("generation_id",), "unqualified"),
])
def test_malformed_metadata_cannot_manufacture_a_source_changed_receipt(tmp_path, path, value):
    snapshot, _, request, publication = publication_fixture(tmp_path, scenario_enabled=True)
    bad = copy.deepcopy(publication)
    target = bad
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    request["expected_publication"]["manifest_sha256"] = "e" * 64
    with pytest.raises(wire.RatesScenarioContractError, match="^invalid_rates_publication$"):
        wire.qualify_rates_publication(snapshot, bad, expected_publication=request["expected_publication"])


def test_zero_baseline_and_negative_assumed_yield_are_preserved(tmp_path):
    snapshot, baseline, request, publication = publication_fixture(tmp_path, scenario_enabled=True, two=0, ten=0)
    qualified, metadata = wire.qualify_rates_publication(snapshot, publication)
    assert qualified == baseline and metadata == publication
    projection = wire.rates_scenario_source(snapshot, publication)
    assert projection["baseline"]["us2y"]["value"] == 0
    assert projection["baseline"]["curve_2s10s"]["value"] == 0
    request["assumptions"] = {"us2y_bp": -300, "us10y_bp": 300}
    result = wire.serialize_rates_result(request, owner.evaluate_rates_scenario(baseline, request["assumptions"]),
                                         publication=publication)
    assert result["assumed"]["us2y"]["value"] == -3
    assert result["assumed"]["spread_change"]["value"] == 600
    assert result["publication"]["artifact"]["min_client_contract"] == NEW


def test_schema_and_capability_change_content_and_baseline_identity(tmp_path):
    old, old_baseline, *_ = publication_fixture(tmp_path / "old")
    new, new_baseline, *_ = publication_fixture(tmp_path / "new", scenario_enabled=True)
    assert old_baseline.us2y_pct == new_baseline.us2y_pct
    assert old_baseline.us10y_pct == new_baseline.us10y_pct
    assert old["generation"]["content_sha256"] != new["generation"]["content_sha256"]
    assert old_baseline.baseline_id != new_baseline.baseline_id
