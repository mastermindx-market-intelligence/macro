"""Native evidence boundary regressions; authored for the deferred combined pass.

These are protocol fixtures, not indicator strategy or production-data proof.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.neuralweb import brain_gateway as gw

SCHEMA = "chart.native_live_observations.v1"


def native_state() -> dict:
    indicators = [{"name": "rsix", "params": {"eng.len": 14}}]
    groups = {name: {"available": 0, "eligible": 0, "invalid": 0,
                     "returned": 0, "omitted": 0}
              for name in ("series", "events", "geometry", "tables")}
    groups["series"] = {"available": 1, "eligible": 1, "invalid": 0,
                        "returned": 1, "omitted": 0}
    modules = [{"id": "rsix/" + key, "configured_on": True,
                "compute_enabled": True, "locked": False} for key in ("eng", "sig")]
    packet = {
        "schema": SCHEMA, "status": "observed",
        "binding": {"origin_id": "native-origin", "context_revision": 7,
                    "pane_id": 0, "symbol": "NVDA", "tf": "D",
                    "settings_key": json.dumps(indicators, separators=(",", ":")),
                    "replay_on": False, "replay_idx": None, "selected_time": None},
        "context": {"symbol": "NVDA", "timeframe": "D", "pane_id": 0,
                    "bar_count": 3, "first_bar": "2026-09-22", "last_bar": "2026-09-24",
                    "selected_bar": None, "replay": {"active": False, "index": None}},
        "suites": [{"suite": "rsix", "modules": modules,
                    "series": [{"id": "rsi-wave", "kind": "poly",
                                "samples": [{"index": 2, "value": 61.25}]}],
                    "events": [], "geometry": [], "tables": [],
                    "coverage": {**groups, "bundle_counts": {
                        "prims": 1, "events": 0, "tables": 0,
                        "tooltips": 0, "candle_paints": 0},
                        "upstream_invalid_event_timing_count": 0}}],
        "coverage": {"configured_suites": ["rsix"], "observed_suites": ["rsix"],
                     "omitted_suites": []},
    }
    caps = {"native_observations": {"schema": SCHEMA},
            "native_study_context": {
                "schema": "chart.native_study_context.v1", "status": "complete",
                "modules": [{"id": "rsix/" + key, "suite": "rsix", "module": key,
                             "enabled": True} for key in ("eng", "sig")],
                "omitted_modules": []}}
    return {"connected": True, "origin_id": "native-origin", "context_revision": 7,
            "session": {"symbol": "NVDA", "tf": "D", "pane_id": 0,
                        "indicators": indicators, "capabilities": caps,
                        "native_observations": packet}}


def qualify(state: dict) -> dict:
    return gw._qualified_native_live_observations(state)


def test_native_fixture_preserves_facts_without_modifying_source():
    state = native_state()
    before = copy.deepcopy(state)
    result = qualify(state)
    assert result["status"] == "observed"
    assert result["suites"][0]["series"][0]["samples"][0] == {
        "index": 2, "value": 61.25, "age_bars": 0}
    assert result["basis"]["predictive_validation"] is False
    assert state == before


@pytest.mark.parametrize("wire_number,value", [
    ("0.000001", 1e-6), ("1e-7", 1e-7), ("1e+21", 10**21), ("14.0", 14),
])
def test_settings_compare_json_values_not_language_number_spelling(wire_number, value):
    state = native_state()
    # Transport-number cases, not accepted native parameter ranges.
    state["session"]["indicators"][0]["params"]["eng.len"] = value
    state["session"]["native_observations"]["binding"]["settings_key"] = (
        '[{"name":"rsix","params":{"eng.len":' + wire_number + '}}]')
    assert qualify(state)["status"] == "observed"


@pytest.mark.parametrize("wire_value", ['"14"', 'true', 'false', 'null', '15'])
def test_settings_value_or_type_changes_are_not_normalized_away(wire_value):
    state = native_state()
    state["session"]["native_observations"]["binding"]["settings_key"] = (
        '[{"name":"rsix","params":{"eng.len":' + wire_value + '}}]')
    assert qualify(state)["reason"] == "native_observation_settings_mismatch"


@pytest.mark.parametrize("wire_key", [
    '[{"name":"old","name":"rsix","params":{"eng.len":14}}]',
    '[{"name":"rsix","params":{"eng.len":NaN}}]',
    '[{"name":"rsix","params":{"eng.len":Infinity}}]',
    '{"name":"rsix","params":{"eng.len":14}}',
])
def test_ambiguous_or_nonjson_settings_fail_closed(wire_key):
    state = native_state()
    state["session"]["native_observations"]["binding"]["settings_key"] = wire_key
    assert qualify(state)["reason"] == "native_observation_settings_mismatch"


def test_settings_object_order_is_not_semantics_but_indicator_order_is():
    state = native_state()
    state["session"]["native_observations"]["binding"]["settings_key"] = (
        '[{"params":{"eng.len":14},"name":"rsix"}]')
    assert qualify(state)["status"] == "observed"
    state["session"]["indicators"].append({"name": "ema", "params": {"len": 20}})
    key = json.dumps(list(reversed(state["session"]["indicators"])))
    state["session"]["native_observations"]["binding"]["settings_key"] = key
    assert qualify(state)["reason"] == "native_observation_settings_mismatch"


def test_configured_native_suite_cannot_disappear_from_coverage():
    state = native_state()
    session = state["session"]
    session["indicators"].append({"name": "trend", "params": {"te.on": True}})
    session["capabilities"]["native_study_context"]["modules"].append({
        "id": "trend/te", "suite": "trend", "module": "te", "enabled": True})
    session["native_observations"]["binding"]["settings_key"] = json.dumps(
        session["indicators"], separators=(",", ":"))
    assert qualify(state)["reason"] == "native_observation_coverage_invalid"
    packet = session["native_observations"]
    packet["coverage"]["configured_suites"].append("trend")
    packet["coverage"]["omitted_suites"].append({"suite": "trend", "reason": "runtime_pending"})
    result = qualify(state)
    assert result["status"] == "partial"
    assert result["coverage"]["omitted_suites"] == [{"suite": "trend", "reason": "runtime_pending"}]


def test_module_census_includes_ids_omitted_from_compact_config_for_budget():
    state = native_state()
    caps = state["session"]["capabilities"]["native_study_context"]
    caps["modules"] = caps["modules"][:1]
    caps["omitted_modules"] = ["rsix/sig"]
    caps["status"] = "partial"
    assert qualify(state)["status"] == "observed"
    state["session"]["native_observations"]["suites"][0]["modules"].pop()
    assert qualify(state)["reason"] == "native_observation_modules_invalid"


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_status_is_unavailable_not_an_exception(value):
    state = native_state()
    state["session"]["native_observations"]["status"] = value
    assert qualify(state)["status"] == "unavailable"


@pytest.mark.parametrize("group,field,row", [
    ("series", "kind", {"id": "rsi-wave", "samples": [{"index": 2, "value": 60}]}),
    ("events", "direction", {"type": "rsix_sig"}),
    ("geometry", "kind", {"id": "level", "coordinates": {}}),
])
def test_malformed_fact_enum_is_unavailable(group, field, row):
    state = native_state()
    state["session"]["native_observations"]["suites"][0][group] = [{**row, field: []}]
    assert qualify(state)["reason"] == "native_observation_facts_invalid"


def test_oversized_integer_fact_does_not_escape_numeric_guard():
    state = native_state()
    state["session"]["native_observations"]["suites"][0]["series"][0]["samples"][0]["value"] = 10**400
    assert qualify(state)["reason"] == "native_observation_facts_invalid"


def test_omission_reason_container_is_unavailable_not_an_exception():
    state = native_state()
    packet = state["session"]["native_observations"]
    packet["suites"] = []
    packet["coverage"]["observed_suites"] = []
    packet["coverage"]["omitted_suites"] = [{"suite": "rsix", "reason": {}}]
    assert qualify(state)["reason"] == "native_observation_coverage_invalid"


@pytest.mark.parametrize("field,value", [("pane_id", False), ("context_revision", True)])
def test_binding_booleans_are_not_integer_chart_identities(field, value):
    state = native_state()
    if field == "context_revision":
        state["context_revision"] = 1
    state["session"]["native_observations"]["binding"][field] = value
    assert qualify(state)["reason"] == "native_observation_binding_mismatch"
