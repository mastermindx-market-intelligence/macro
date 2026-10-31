"""Behavior tests for the three-stage physical petroleum-flow CONTEXT helper
(engine.commodity_supply_context.petroleum_flow_context, MO-PAID-040 / MO-DELTA-027).

These tests exercise BEHAVIOR — status selection, common-period math, exclusion of
non-observations, staleness boundaries, input immutability — not string presence.
Fixtures use the native EIA weekly snapshot: period 2026-10-02 values
13979 / 16480 / 8769 / 3650 kbbl/d, evaluated as_of 2026-10-20 (18 days → stale).
"""
from __future__ import annotations

import copy
import datetime
import json

import numpy as np
import pandas as pd
import pytest

from engine.commodity_supply_context import petroleum_flow_context

PERIOD = "2026-10-02"
SNAPSHOT = {  # native thousand barrels per day (kbbl/d)
    "crude_production": 13979,
    "refinery_inputs": 16480,
    "gasoline_supplied": 8769,
    "distillate_supplied": 3650,
}
AS_OF = "2026-10-20"


def _series(values, dates):
    return pd.Series(list(values), index=pd.to_datetime(list(dates)), dtype="float64")


def _snapshot(**overrides):
    """Four series with a week of history ending at the 2026-10-02 snapshot period."""
    history = {
        "crude_production": ([13850, 13979], ["2026-09-25", PERIOD]),
        "refinery_inputs": ([16310, 16480], ["2026-09-25", PERIOD]),
        "gasoline_supplied": ([8902, 8769], ["2026-09-25", PERIOD]),
        "distillate_supplied": ([3712, 3650], ["2026-09-25", PERIOD]),
    }
    history.update(overrides)
    return {name: _series(vals, dates) for name, (vals, dates) in history.items()}


def _assert_series_unchanged(before, after):
    assert list(after.index) == list(before.index)
    assert [float(v) for v in after.values] == [float(v) for v in before.values]
    assert after.dtype == before.dtype


# --- the native 18-day stale snapshot -------------------------------------


def test_stale_native_snapshot_18_days():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    assert result["status"] == "stale"
    assert result["state"] == "stale"
    assert result["period"] == PERIOD
    assert result["as_of"] == AS_OF
    assert result["evaluated_on"] == AS_OF
    assert result["age_days"] == 18
    assert result["stale_after_days"] == 9
    assert result["unavailable_inputs"] == []
    for name, native in SNAPSHOT.items():
        entry = result["series"][name]
        assert entry["latest_value_kbbl_d"] == float(native)     # native kbbl/d
        assert entry["display_value_mbbl_d"] == native / 1000.0  # display mbbl/d
        assert entry["latest_period"] == PERIOD
        assert entry["status"] == "observed"
        assert entry["at_selected_common_period"] is True


def test_fresh_boundary_9_vs_10_days():
    at_9 = petroleum_flow_context(_snapshot(), as_of="2026-10-11")
    assert at_9["status"] == "available"
    assert at_9["age_days"] == 9
    at_10 = petroleum_flow_context(_snapshot(), as_of="2026-10-12")
    assert at_10["status"] == "stale"
    assert at_10["age_days"] == 10


def test_stale_value_stays_visible_not_promoted_current():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    # Explicitly stale, and the historical value is still visible with its date.
    assert result["status"] == "stale"
    entry = result["series"]["crude_production"]
    assert entry["latest_period"] == PERIOD
    assert entry["latest_value_kbbl_d"] == 13979.0
    assert entry["status"] == "observed"
    # Nothing in the payload claims the stale print is current.
    assert result["status"] != "available"


# --- common-period selection ----------------------------------------------


def test_mixed_periods_select_latest_common_date():
    series = _snapshot(gasoline_supplied=([8902, 8769, 8801],
                                          ["2026-09-25", PERIOD, "2026-10-09"]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "stale"
    # Latest date present in ALL FOUR series, not the overall latest observation.
    assert result["period"] == PERIOD
    gas = result["series"]["gasoline_supplied"]
    assert gas["latest_period"] == "2026-10-09"        # per-series latest still reported
    assert gas["latest_value_kbbl_d"] == 8801.0
    assert gas["at_selected_common_period"] is False
    assert result["series"]["crude_production"]["at_selected_common_period"] is True


def test_no_common_period_is_unavailable():
    series = _snapshot(distillate_supplied=([3790, 3740],
                                            ["2026-09-11", "2026-09-18"]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["period"] is None
    assert result["age_days"] is None
    assert result["reason"] and "common" in result["reason"]
    # No series is itself broken — each still reports its own latest observation.
    assert result["unavailable_inputs"] == []
    assert result["series"]["distillate_supplied"]["latest_period"] == "2026-09-18"


# --- missing / empty / invalid series --------------------------------------


@pytest.mark.parametrize("drop", ["crude_production", "refinery_inputs",
                                  "gasoline_supplied", "distillate_supplied"])
def test_missing_series_is_unavailable_and_retained(drop):
    series = _snapshot()
    series.pop(drop)
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["period"] is None
    assert result["unavailable_inputs"] == [drop]
    assert drop in result["reason"]
    # Surviving series keep their real observations; nothing is invented for the gap.
    for name, native in SNAPSHOT.items():
        if name != drop:
            assert result["series"][name]["latest_value_kbbl_d"] == float(native)
    assert result["series"][drop]["latest_value_kbbl_d"] is None


@pytest.mark.parametrize("broken", [None, pd.Series(dtype="float64"), []])
def test_none_and_empty_series_unavailable(broken):
    series = _snapshot()
    series["refinery_inputs"] = broken
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["unavailable_inputs"] == ["refinery_inputs"]
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] is None


# --- non-observations: NaN / inf / negative / bool / zero --------------------


def test_nan_latest_falls_back_and_never_becomes_zero():
    series = _snapshot(refinery_inputs=([16310, np.nan], ["2026-09-25", PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    # NaN is not an observation: the previous real week is used, never 0.
    assert result["period"] == "2026-09-25"
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] == 16310.0
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] != 0


def test_infinite_values_are_not_observations():
    for bad in (np.inf, -np.inf):
        series = _snapshot(gasoline_supplied=([8902, bad], ["2026-09-25", PERIOD]))
        result = petroleum_flow_context(series, as_of=AS_OF)
        assert result["period"] == "2026-09-25"
        assert result["series"]["gasoline_supplied"]["latest_value_kbbl_d"] == 8902.0


def test_all_invalid_observations_leaves_series_unavailable():
    series = _snapshot()
    series["crude_production"] = _series([np.nan, np.inf], ["2026-09-25", PERIOD])
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["unavailable_inputs"] == ["crude_production"]
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] is None


def test_zero_stays_zero():
    series = _snapshot(distillate_supplied=([3712, 0], ["2026-09-25", PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "stale"
    assert result["period"] == PERIOD
    entry = result["series"]["distillate_supplied"]
    assert entry["latest_value_kbbl_d"] == 0.0
    assert entry["display_value_mbbl_d"] == 0.0
    assert entry["latest_value_kbbl_d"] is not None


def test_negative_quantity_is_not_used():
    series = _snapshot(crude_production=([13850, -5.0], ["2026-09-25", PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    # A negative quantity is not a valid flow observation — no negative value may
    # surface, and the last valid week carries the stage instead.
    assert result["period"] == "2026-09-25"
    values = [e["latest_value_kbbl_d"] for e in result["series"].values()]
    assert all(v is not None and v >= 0 for v in values)
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] == 13850.0


def test_all_negative_series_unavailable():
    series = _snapshot()
    series["distillate_supplied"] = _series([-1.0, -2.0], ["2026-09-25", PERIOD])
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["unavailable_inputs"] == ["distillate_supplied"]


def test_bool_is_not_a_numeric_observation():
    series = _snapshot()
    # object dtype so the bool reaches the helper as a real bool, not 1.0
    series["crude_production"] = pd.Series(
        [13850, True], index=pd.to_datetime(["2026-09-25", PERIOD]), dtype=object)
    result = petroleum_flow_context(series, as_of=AS_OF)
    # A bool must never be read as 1 kbbl/d.
    assert result["period"] == "2026-09-25"
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] == 13850.0


def test_all_bool_series_unavailable():
    series = _snapshot()
    series["gasoline_supplied"] = pd.Series([True, True],
                                            index=pd.to_datetime(["2026-09-25", PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["unavailable_inputs"] == ["gasoline_supplied"]


# --- duplicate periods -------------------------------------------------------


def test_conflicting_duplicates_fail_series_closed():
    series = _snapshot(refinery_inputs=([16310, 16480, 17000],
                                        ["2026-09-25", PERIOD, PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["unavailable_inputs"] == ["refinery_inputs"]
    entry = result["series"]["refinery_inputs"]
    assert entry["status"] == "unavailable"
    assert entry["latest_value_kbbl_d"] is None
    assert PERIOD in entry["reason"]
    # The other three series still show their honest observations.
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] == 13979.0


def test_identical_duplicates_collapse():
    series = _snapshot(refinery_inputs=([16310, 16480, 16480],
                                        ["2026-09-25", PERIOD, PERIOD]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "stale"
    assert result["period"] == PERIOD
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] == 16480.0
    assert result["unavailable_inputs"] == []


# --- future observations -----------------------------------------------------


def test_future_observations_excluded():
    series = _snapshot(crude_production=([13850, 13979, 14100],
                                         ["2026-09-25", PERIOD, "2026-10-23"]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["period"] == PERIOD
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] == 13979.0


def test_future_conflicting_duplicate_does_not_poison():
    series = _snapshot(refinery_inputs=([16310, 16480, 17000, 16999],
                                        ["2026-09-25", PERIOD, "2026-10-23", "2026-10-23"]))
    result = petroleum_flow_context(series, as_of=AS_OF)
    # Exclusion of post-as_of observations happens first, so a future conflict
    # cannot close the series.
    assert result["status"] == "stale"
    assert result["period"] == PERIOD
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] == 16480.0


def test_future_only_observations_unavailable():
    future = "2026-10-23"
    series = {name: _series([native + 10], [future]) for name, native in SNAPSHOT.items()}
    result = petroleum_flow_context(series, as_of=AS_OF)
    assert result["status"] == "unavailable"
    assert result["period"] is None
    assert result["reason"] and "as_of" in result["reason"]
    assert sorted(result["unavailable_inputs"]) == sorted(SNAPSHOT)
    for entry in result["series"].values():
        assert entry["latest_period"] is None
        assert entry["latest_value_kbbl_d"] is None   # never surfaced, never zeroed


# --- immutability, clocks, metadata -----------------------------------------


def test_inputs_not_mutated():
    series = _snapshot()
    series["refinery_inputs"] = _series([16310, 16480, 17000],
                                        ["2026-09-25", PERIOD, "2026-10-23"])
    frozen = {name: s.copy(deep=True) for name, s in series.items()}
    petroleum_flow_context(series, as_of=AS_OF)
    for name in series:
        _assert_series_unchanged(frozen[name], series[name])


def test_clocks_unknown_and_no_ambient_now():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    # A stored period series establishes no release/knowledge time.
    assert result["known_at"] is None
    assert result["published_at"] is None
    assert result["retrieved_at"] is None
    # evaluated_on is exactly the explicit as_of — never an ambient now.
    assert result["evaluated_on"] == AS_OF
    assert result["as_of"] == AS_OF
    # Same explicit instant via datetime object and ISO string agree completely.
    via_dt = petroleum_flow_context(_snapshot(), as_of=datetime.datetime(2026, 10, 20))
    via_iso = petroleum_flow_context(_snapshot(), as_of="2026-10-20")
    assert via_dt == via_iso


def test_source_codes_and_units():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    expected = {
        "crude_production": "WCRFPUS2",
        "refinery_inputs": "WCRRIUS2",
        "gasoline_supplied": "WGFUPUS2",
        "distillate_supplied": "WDIUPUS2",
    }
    for name, code in expected.items():
        entry = result["series"][name]
        assert entry["eia_series_code"] == code
        assert entry["source_url"].startswith("https://www.eia.gov/dnav/")
        assert code in entry["source_url"]                # official dnav series link
        assert entry["units"].startswith("thousand barrels per day")
        native = entry["latest_value_kbbl_d"]
        assert entry["display_value_mbbl_d"] == native / 1000.0
    assert result["units"]["display"].startswith("million barrels per day")


def test_invalid_as_of_fails_explicitly():
    for bad in ("not-a-date", None, True, False, 12345, 20261020.0, pd.NaT, [AS_OF]):
        with pytest.raises(ValueError):
            petroleum_flow_context(_snapshot(), as_of=bad)


# --- semantics: aggregate stages, not a mass balance -------------------------


def test_no_total_and_no_mass_balance_arithmetic():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)

    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert "total" not in key.lower()
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(result)
    # Each stage value is exactly the reported observation — no derived deltas,
    # ratios or balance arithmetic between stages.
    assert result["series"]["crude_production"]["latest_value_kbbl_d"] == 13979.0
    assert result["series"]["refinery_inputs"]["latest_value_kbbl_d"] == 16480.0
    assert result["series"]["gasoline_supplied"]["latest_value_kbbl_d"] == 8769.0
    assert result["series"]["distillate_supplied"]["latest_value_kbbl_d"] == 3650.0
    # Gasoline and distillate stay SEPARATE quantities.
    assert set(result["series"]) == set(SNAPSHOT)


def test_context_authority_and_caveat_present():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    assert result["authority"] == "context_only"
    caveat = result["caveat"]["en"]
    assert "NOT a traced barrel flow" in caveat
    assert "imported crude" in caveat


def test_output_is_json_serializable():
    result = petroleum_flow_context(_snapshot(), as_of=AS_OF)
    payload = json.loads(json.dumps(result))
    assert payload["status"] == result["status"]
    assert payload["period"] == PERIOD


def test_unavailable_payload_is_json_serializable():
    result = petroleum_flow_context({}, as_of=AS_OF)
    payload = json.loads(json.dumps(result))
    assert payload["status"] == "unavailable"
    assert sorted(payload["unavailable_inputs"]) == sorted(SNAPSHOT)
