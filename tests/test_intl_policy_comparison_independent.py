"""Independent C2 numerical oracle and boundary tests for compare_policy_points.

Oracle arithmetic follows SHARED_CONTRACT Policy preview and the parent API freeze:
normalize each observation to bp with Fraction, then
gap = A - B, signed_change = end - start, absolute_change = abs(end) - abs(start).
Does not import parent tests or replace engine arithmetic with stubs.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest

from engine import intl_compare, intl_inputs, intl_rates as owner
from lib import config, store

SLOTS = ("a_start", "a_end", "b_start", "b_end")
INVALID = dict(
    state="invalid",
    identity=None,
    reasons=["invalid_policy_comparison"],
    missing_refs=[],
)
QUALIFIED_KEYS = {
    "state",
    "identity",
    "signed_start_bp",
    "signed_end_bp",
    "signed_change_bp",
    "absolute_change_bp",
    "direction",
    "crosses_zero",
    "evidence_refs",
}
UNAVAILABLE_KEYS = {"state", "identity", "reasons", "missing_refs"}
UNREP = object()
ROOT = Path(__file__).resolve().parent
FLOAT_MIN = 2.2250738585072014e-308


def fixture(values=(0.5, 0.5, 3.5, 3.0), *, units=None, period=None, economies=("JP", "US")):
    start, end = ("2026-08-31", "2026-09-30") if period is None else (period["start"], period["end"])
    intent = dict(
        economy_a=economies[0],
        economy_b=economies[1],
        lens="nominal_policy_point_gap",
        definition="absolute_gap_change_bp",
        method_version="nominal-point/v1",
        period=dict(mode="fixed_dates", start=start, end=end) if period is None else dict(period),
        vintage_policy="latest_vintage",
        identity=dict(
            principal_partition=None,
            saved_id=None,
            saved_revision=None,
            source_generation="generation-1",
        ),
    )
    units = units or {}
    obs = {}
    for slot, value in zip(SLOTS, values):
        economy = intent["economy_" + slot[0]]
        cutoff = intent["period"][slot.split("_")[1]]
        obs[slot] = dict(
            economy=economy,
            instrument_id=economy + "-point",
            instrument_kind="nominal_policy_point",
            observation_at=cutoff,
            unit=units.get(slot, "percent"),
            value=value,
            quality="qualified",
            metadata="allowed",
            value_permission="allowed",
            source_reference="public/" + slot,
            qualification_ref="qualified/" + slot,
        )
    mapping = dict(
        status="qualified",
        method_version=intent["method_version"],
        instruments={
            side: {
                key: obs[side + "_start"][key]
                for key in ("economy", "instrument_id", "instrument_kind")
            }
            for side in ("a", "b")
        },
    )
    return intent, obs, mapping


def to_bp(value, unit):
    quantity = Fraction(value)
    if unit == "percent":
        return quantity * 100
    if unit == "bp":
        return quantity
    raise AssertionError("oracle received a unit outside percent/bp")


def emit(quantity):
    if quantity.denominator == 1:
        return quantity.numerator
    try:
        out = float(quantity)
    except OverflowError:
        return UNREP
    if not math.isfinite(out) or (out == 0 and quantity != 0):
        return UNREP
    return out


def oracle(values, units=("percent",) * 4):
    bp = [to_bp(value, unit) for value, unit in zip(values, units)]
    start = bp[0] - bp[2]
    end = bp[1] - bp[3]
    signed_change = end - start
    absolute_change = abs(end) - abs(start)
    emitted = [emit(item) for item in (start, end, signed_change, absolute_change)]
    if any(item is UNREP for item in emitted):
        return dict(state="unavailable", reasons=["arithmetic_unrepresentable"])
    if absolute_change < 0:
        direction = "narrowed"
    elif absolute_change > 0:
        direction = "widened"
    else:
        direction = "unchanged_at_endpoints"
    return dict(
        state="qualified",
        signed_start_bp=emitted[0],
        signed_end_bp=emitted[1],
        signed_change_bp=emitted[2],
        absolute_change_bp=emitted[3],
        direction=direction,
        crosses_zero=(start < 0 < end or end < 0 < start),
    )


def compare(*triple):
    return owner.compare_policy_points(*triple)


def assert_json_safe(result):
    json.dumps(result, allow_nan=False)
    assert result == json.loads(json.dumps(result, allow_nan=False))


def assert_qualified_matches_oracle(result, values, units=("percent",) * 4, identity=None):
    expected = oracle(values, units)
    assert result["state"] == "qualified"
    assert set(result) == QUALIFIED_KEYS
    if expected["state"] != "qualified":
        raise AssertionError("oracle unrepresentable but helper qualified")
    for key in (
        "signed_start_bp",
        "signed_end_bp",
        "signed_change_bp",
        "absolute_change_bp",
        "direction",
        "crosses_zero",
    ):
        assert result[key] == expected[key]
    assert result["crosses_zero"] is True or result["crosses_zero"] is False
    assert [row["slot"] for row in result["evidence_refs"]] == list(SLOTS)
    for row in result["evidence_refs"]:
        assert set(row) == {"slot", "source_reference", "qualification_ref", "observation_at"}
    if identity is not None:
        assert result["identity"] == identity
        assert result["identity"] is not identity
    assert_json_safe(result)




def test_native_sample_matches_contract_and_oracle():
    intent, obs, mapping = fixture()
    result = compare(intent, obs, mapping)
    assert [result[key] for key in (
        "signed_start_bp", "signed_end_bp", "signed_change_bp", "absolute_change_bp"
    )] == [-300, -250, 50, -50]
    assert result["direction"] == "narrowed"
    assert result["crosses_zero"] is False
    assert_qualified_matches_oracle(result, (0.5, 0.5, 3.5, 3.0), identity=intent)


def test_swapped_pair_reverses_signed_gap_not_absolute_distance():
    forward = compare(*fixture((0.5, 0.5, 3.5, 3.0)))
    swapped = compare(*fixture((3.5, 3.0, 0.5, 0.5)))
    for key in ("signed_start_bp", "signed_end_bp", "signed_change_bp"):
        assert swapped[key] == -forward[key]
    assert swapped["absolute_change_bp"] == forward["absolute_change_bp"] == -50
    assert swapped["direction"] == forward["direction"] == "narrowed"
    assert swapped["crosses_zero"] is False


@pytest.mark.parametrize(
    "values,units",
    [
        ((0.5, 0.5, 3.5, 4.0), ("percent",) * 4),
        ((0, 0, 0, 0), ("percent",) * 4),
        ((0, 0, 0, 0), ("bp",) * 4),
        ((-3.0, -2.0, -1.0, -1.0), ("percent",) * 4),
        ((-2, -3, -1, -1), ("percent",) * 4),
        ((2.0, -0.5, 0.0, 0.0), ("percent",) * 4),
        ((0.5, -2.0, 0.0, 0.0), ("percent",) * 4),
        ((-1, 1, 0, 0), ("percent",) * 4),
        ((0, 1, 0, 0), ("percent",) * 4),
        ((1, 0, 0, 0), ("percent",) * 4),
        ((0, -1, 0, 0), ("percent",) * 4),
        ((1, 1, 1, 1), ("percent",) * 4),
        ((50, 50, 350, 300), ("bp",) * 4),
        ((50, 50, 3.5, 3.0), ("bp", "bp", "percent", "percent")),
        ((0.5, 50, 350, 3.0), ("percent", "bp", "bp", "percent")),
        ((1, 1.0, 0, 0.0), ("percent",) * 4),
        ((-50, -50, -50, -50), ("bp",) * 4),
        ((10**50, 10**50, 0, 0), ("percent",) * 4),
        ((10**400, 10**400 + 1, 10**400, 10**400), ("percent",) * 4),
        ((1e308, 1e308, 1e308, 1e308), ("percent",) * 4),
        ((5e-324, 5e-324, 0.0, 0.0), ("bp",) * 4),
        ((5e-324, 5e-324, 0.0, 0.0), ("percent",) * 4),
        ((FLOAT_MIN, FLOAT_MIN, 0.0, 0.0), ("percent",) * 4),
        ((1.0, math.nextafter(1.0, 2.0), 1.0, 1.0), ("percent",) * 4),
        ((1.0, 1.0000000000000002, 1.0, 1.0), ("percent",) * 4),
    ],
)
def test_oracle_vectors_sign_scale_cancellation_and_subnormals(values, units):
    intent, obs, mapping = fixture(values, units={slot: unit for slot, unit in zip(SLOTS, units)})
    result = compare(intent, obs, mapping)
    expected = oracle(values, units)
    if expected["state"] == "unavailable":
        assert result["state"] == "unavailable"
        assert result["reasons"] == ["arithmetic_unrepresentable"]
        assert set(result) == UNAVAILABLE_KEYS
        return
    assert_qualified_matches_oracle(result, values, units, identity=intent)


def test_non_integral_overflow_is_unrepresentable_not_inf():
    values = (1e308, 1e308, 0.1, 0.1)
    result = compare(*fixture(values))
    assert oracle(values)["state"] == "unavailable"
    assert result["state"] == "unavailable"
    assert result["reasons"] == ["arithmetic_unrepresentable"]
    assert "signed_start_bp" not in result
    assert_json_safe(result)


def test_huge_integer_output_is_not_capped_until_json_identity_breaks():
    representable = compare(*fixture((10**80, 10**80, 0, 0)))
    assert representable["state"] == "qualified"
    assert representable["signed_start_bp"] == 10**82
    assert isinstance(representable["signed_start_bp"], int)
    assert_json_safe(representable)
    huge = compare(*fixture((10**5000, 10**5000, 0, 0)))
    assert huge["state"] == "unavailable"
    assert huge["reasons"] == ["arithmetic_unrepresentable"]
    assert_json_safe(huge)


def test_same_date_conflict_identifies_only_offending_pairs():
    def same_date(values):
        intent, obs, mapping = fixture(values)
        intent["period"]["end"] = intent["period"]["start"]
        for slot in SLOTS:
            obs[slot]["observation_at"] = intent["period"]["start"]
        return intent, obs, mapping

    a_only = compare(*same_date((0.5, 0.6, 3.0, 3.0)))
    assert a_only["state"] == "unavailable"
    assert a_only["reasons"] == ["observation_conflict"]
    assert a_only["missing_refs"] == ["a_start", "a_end"]

    b_only = compare(*same_date((0.5, 0.5, 3.5, 3.0)))
    assert b_only["missing_refs"] == ["b_start", "b_end"]

    both = compare(*same_date((0.5, 0.6, 3.5, 3.0)))
    assert both["missing_refs"] == ["a_start", "a_end", "b_start", "b_end"]

    mixed = fixture((0.5, 0.5, 3.0, 3.0))
    intent, obs, mapping = mixed
    intent["period"]["end"] = intent["period"]["start"]
    for slot in SLOTS:
        obs[slot]["observation_at"] = intent["period"]["start"]
    obs["a_end"].update(value=50, unit="bp")
    obs["b_end"].update(value=300, unit="bp")
    result = compare(intent, obs, mapping)
    assert result["state"] == "qualified"
    assert result["signed_change_bp"] == 0
    assert result["direction"] == "unchanged_at_endpoints"


def test_missing_stale_denied_unknown_and_wrong_identity_do_not_answer():
    cases = [
        ("a_start", dict(), None, "observation_missing", ["a_start"]),
        ("a_end", dict(quality="stale"), "keep", "observation_unqualified", ["a_end"]),
        ("b_start", dict(quality="denied"), "keep", "observation_unqualified", ["b_start"]),
        ("b_end", dict(quality="unknown"), "keep", "observation_unqualified", ["b_end"]),
        ("a_start", dict(metadata="denied"), "keep", "observation_not_disclosed", ["a_start"]),
        ("a_end", dict(metadata="unknown"), "keep", "observation_not_disclosed", ["a_end"]),
        ("b_start", dict(value_permission="denied"), "keep", "observation_not_disclosed", ["b_start"]),
        ("b_end", dict(value_permission="unknown"), "keep", "observation_not_disclosed", ["b_end"]),
        ("a_start", dict(instrument_kind="effective_rate"), "keep", "observation_identity_mismatch", ["a_start"]),
        ("a_end", dict(instrument_kind="target_range"), "keep", "observation_identity_mismatch", ["a_end"]),
        ("b_start", dict(economy="GB"), "keep", "observation_identity_mismatch", ["b_start"]),
        ("b_end", dict(instrument_id="wrong-point"), "keep", "observation_identity_mismatch", ["b_end"]),
        ("a_end", dict(observation_at="2026-09-29"), "keep", "observation_cutoff_mismatch", ["a_end"]),
        ("a_start", dict(observation_at="2026-08-30"), "keep", "observation_cutoff_mismatch", ["a_start"]),
    ]
    for slot, fields, sentinel, reason, missing in cases:
        intent, obs, mapping = fixture()
        if sentinel is None:
            obs[slot] = None
        else:
            obs[slot].update(fields)
            obs[slot]["source_reference"] = "PRIVATE-SENTINEL"
            obs[slot]["qualification_ref"] = "PRIVATE-Q"
            obs[slot]["value"] = 987654321
        result = compare(intent, obs, mapping)
        assert result["state"] == "unavailable"
        assert result["reasons"] == [reason]
        assert result["missing_refs"] == missing
        assert set(result) == UNAVAILABLE_KEYS
        blob = json.dumps(result)
        assert "PRIVATE-SENTINEL" not in blob
        assert "PRIVATE-Q" not in blob
        assert "987654321" not in blob
        assert result["identity"] == intent


def test_mixed_slot_reasons_are_unique_and_ordered():
    intent, obs, mapping = fixture()
    obs["a_start"] = None
    obs["a_end"]["quality"] = "stale"
    obs["b_start"]["metadata"] = "denied"
    obs["b_start"]["source_reference"] = "PRIVATE-META"
    obs["b_end"]["observation_at"] = "2026-08-30"
    result = compare(intent, obs, mapping)
    assert result["reasons"] == [
        "observation_missing",
        "observation_unqualified",
        "observation_not_disclosed",
        "observation_cutoff_mismatch",
    ]
    assert result["missing_refs"] == list(SLOTS)
    assert "PRIVATE-META" not in json.dumps(result)


def test_mapping_method_instrument_and_economy_relation():
    intent, obs, mapping = fixture()
    assert compare(intent, obs, None)["reasons"] == ["mapping_not_supplied"]

    denied = deepcopy(mapping)
    denied["status"] = "denied"
    assert compare(intent, obs, denied)["reasons"] == ["mapping_unqualified"]
    unknown = deepcopy(mapping)
    unknown["status"] = "unknown"
    assert compare(intent, obs, unknown)["reasons"] == ["mapping_unqualified"]

    wrong_method = deepcopy(mapping)
    wrong_method["method_version"] = "nominal-point/v0"
    assert compare(intent, obs, wrong_method)["reasons"] == ["mapping_incompatible"]

    wrong_economy = deepcopy(mapping)
    wrong_economy["instruments"]["b"]["economy"] = "GB"
    assert compare(intent, obs, wrong_economy)["reasons"] == ["mapping_incompatible"]

    wrong_kind = deepcopy(mapping)
    wrong_kind["instruments"]["a"]["instrument_kind"] = "target_midpoint"
    assert compare(intent, obs, wrong_kind)["reasons"] == ["mapping_incompatible"]

    swapped_pair = deepcopy(mapping)
    swapped_pair["instruments"]["a"], swapped_pair["instruments"]["b"] = (
        swapped_pair["instruments"]["b"],
        swapped_pair["instruments"]["a"],
    )
    assert compare(intent, obs, swapped_pair)["reasons"] == ["mapping_incompatible"]

    id_mismatch = deepcopy(mapping)
    id_mismatch["instruments"]["a"]["instrument_id"] = "other-id"
    result = compare(intent, obs, id_mismatch)
    assert result["reasons"] == ["observation_identity_mismatch"]
    assert result["missing_refs"] == ["a_start", "a_end"]

    custom = fixture()
    intent, obs, mapping = custom
    for slot in ("a_start", "a_end"):
        obs[slot]["instrument_id"] = "JP-custom"
    for slot in ("b_start", "b_end"):
        obs[slot]["instrument_id"] = "US-custom"
    mapping["instruments"]["a"]["instrument_id"] = "JP-custom"
    mapping["instruments"]["b"]["instrument_id"] = "US-custom"
    result = compare(intent, obs, mapping)
    assert result["state"] == "qualified"


def test_kr_ez_pair_is_not_hard_coded_to_jp_us():
    values = (0.5, 0.5, 3.5, 3.0)
    result = compare(*fixture(values, economies=("KR", "EZ")))
    assert_qualified_matches_oracle(result, values)


def test_unsupported_period_and_vintage_are_unavailable_not_reinterpreted():
    intent, obs, mapping = fixture()
    intent["period"] = dict(mode="owner_horizon", key="1m")
    result = compare(intent, obs, mapping)
    assert result["state"] == "unavailable"
    assert result["reasons"] == ["unsupported_period_mode"]
    assert result["identity"]["period"] == dict(mode="owner_horizon", key="1m")

    intent, obs, mapping = fixture()
    intent["vintage_policy"] = "original_known"
    result = compare(intent, obs, mapping)
    assert result["reasons"] == ["original_known_unavailable"]
    assert compare(intent, obs, None)["reasons"] == ["original_known_unavailable"]


def test_malformed_bool_nan_inf_cycle_and_unknown_fields_are_fixed_invalid():
    intent, obs, mapping = fixture()
    for bad in (True, False, float("nan"), float("inf"), -float("inf"), "1", None, [], {}):
        mutated = deepcopy(obs)
        mutated["a_start"]["value"] = bad
        assert compare(intent, mutated, mapping) == INVALID

    for field, bad in (
        ("economy_a", "US"),
        ("economy_a", "us"),
        ("economy_a", "USA"),
        ("economy_b", "jp"),
        ("lens", "real_rate"),
        ("definition", "signed"),
        ("method_version", ""),
        ("method_version", " v1"),
        ("vintage_policy", "latest"),
    ):
        mutated = deepcopy(intent)
        mutated[field] = bad
        assert compare(mutated, obs, mapping) == INVALID

    for date in (
        "2026-02-29",
        "2026-13-01",
        "2026-8-31",
        "2026-08-31T00:00:00Z",
        "2026-08-31 ",
        "2024-02-30",
        "2026-04-31",
        20260831,
    ):
        mutated = deepcopy(intent)
        mutated["period"]["start"] = date
        assert compare(mutated, obs, mapping) == INVALID

    end_before = deepcopy(intent)
    end_before["period"]["end"] = "2026-08-30"
    assert compare(end_before, obs, mapping) == INVALID

    extra = deepcopy(intent)
    extra["extra"] = "PRIVATE-ECHO"
    result = compare(extra, obs, mapping)
    assert result == INVALID
    assert "PRIVATE-ECHO" not in json.dumps(result)

    cyclic = deepcopy(intent)
    cyclic["economy_a"] = cyclic
    assert compare(cyclic, obs, mapping) == INVALID

    deep = {}
    cursor = deep
    for _ in range(34):
        nxt = {}
        cursor["k"] = nxt
        cursor = nxt
    assert compare(deep, obs, mapping) == INVALID

    long_text = deepcopy(intent)
    long_text["method_version"] = "x" * 4097
    assert compare(long_text, obs, mapping) == INVALID

    bool_revision = deepcopy(intent)
    bool_revision["identity"]["saved_revision"] = True
    assert compare(bool_revision, obs, mapping) == INVALID
    zero_revision = deepcopy(intent)
    zero_revision["identity"]["saved_revision"] = 0
    assert compare(zero_revision, obs, mapping) == INVALID
    huge_revision = deepcopy(intent)
    huge_revision["identity"]["saved_revision"] = 10**5000
    result = compare(huge_revision, obs, mapping)
    assert result == INVALID
    assert_json_safe(result)

    assert compare(intent, [None] * 4, mapping) == INVALID
    assert compare(intent, obs, ["qualified"]) == INVALID
    empty_quality = deepcopy(obs)
    empty_quality["a_start"]["quality"] = ""
    assert compare(intent, empty_quality, mapping) == INVALID
    bool_quality = deepcopy(obs)
    bool_quality["a_start"]["quality"] = True
    assert compare(intent, bool_quality, mapping) == INVALID
    usd = deepcopy(obs)
    usd["a_start"]["unit"] = "USD"
    assert compare(intent, usd, mapping) == INVALID


def test_leap_day_and_same_date_matching_endpoints_qualify():
    period = dict(mode="fixed_dates", start="2024-02-29", end="2024-02-29")
    result = compare(*fixture((1.0, 1.0, 1.0, 1.0), period=period))
    assert result["state"] == "qualified"
    assert result["signed_change_bp"] == 0

    bound = fixture()
    intent, obs, mapping = bound
    intent["method_version"] = "x" * 4096
    mapping["method_version"] = "x" * 4096
    result = compare(intent, obs, mapping)
    assert result["state"] == "qualified"


def test_detached_json_safe_output_does_not_alias_inputs():
    intent, obs, mapping = fixture()
    before = deepcopy((intent, obs, mapping))
    result = compare(intent, obs, mapping)
    assert (intent, obs, mapping) == before
    assert result["identity"] == intent
    assert result["identity"] is not intent
    assert result["identity"]["period"] is not intent["period"]
    result["identity"]["period"]["start"] = "changed"
    result["evidence_refs"][0]["source_reference"] = "changed"
    assert (intent, obs, mapping) == before
    again = compare(*deepcopy(before))
    assert json.dumps(compare(*fixture()), allow_nan=False, sort_keys=True) == json.dumps(
        again, allow_nan=False, sort_keys=True
    )


def test_purity_against_io_owners(monkeypatch):
    def fail(name):
        def inner(*args, **kwargs):
            raise AssertionError("pure helper called " + name)
        return inner

    monkeypatch.setattr(config, "load", fail("config.load"))
    monkeypatch.setattr(config, "data_dir", fail("config.data_dir"))
    monkeypatch.setattr(store, "read", fail("store.read"))
    monkeypatch.setattr(store, "upsert", fail("store.upsert"))
    monkeypatch.setattr(intl_inputs, "countries", fail("countries"))
    monkeypatch.setattr(intl_inputs, "read_intl_macro_col", fail("read_intl_macro_col"))
    monkeypatch.setattr(intl_compare, "periphery_panel", fail("periphery_panel"))
    monkeypatch.setattr(owner, "_series", fail("_series"))
    monkeypatch.setattr(owner, "_us_series", fail("_us_series"))
    monkeypatch.setattr(owner, "_rcfg", fail("_rcfg"))
    monkeypatch.setattr(os, "getcwd", fail("getcwd"))
    monkeypatch.setattr(time, "time", fail("time"))
    result = compare(*fixture())
    assert result["state"] == "qualified"
    assert result["absolute_change_bp"] == -50


def test_real_owner_is_not_a_stub():
    src = Path(owner.__file__).read_text()
    assert "def compare_policy_points" in src
    assert "from fractions import Fraction" in src
    assert "store.read" not in src[src.index("def compare_policy_points"):]
    assert owner.compare_policy_points.__code__.co_argcount == 3
