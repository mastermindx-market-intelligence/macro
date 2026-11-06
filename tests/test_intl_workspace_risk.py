import ast
import copy
import json
import pathlib
from types import MappingProxyType

import pytest

from lib.intl_workspace_risk import qualify_us_transmission


BUILT = "2026-01-02T03:04:05+00:00"
LEG_KEYS = (
    "us_hy_oas_vel",
    "kre_spy_rs",
    "move_pctile",
    "sofr_iorb_corridor",
)
OUTPUT_KEYS = {"quality", "state", "reason_codes", "evidence_refs", "diagnostic"}


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


def eligibility(**changes):
    value = {
        "quality": "qualified",
        "metadata": "allowed",
        "value_permission": "allowed",
        "owner_ref": "public/owner",
        "method_ref": "public/method",
        "source_reference": "public/overall",
        "asof": BUILT,
        "origin": "public/origin",
        "legs": "public/legs",
        "diagnostic_permission": "allowed",
    }
    value.update(changes)
    return value


def two_tier(state, origin_state="stressed", hot_values=None):
    if hot_values is None:
        hot_values = [False, False, False, False]
    return {
        "state": state,
        "tier1": {"em_stress_state": origin_state, "raw-secret": "sentinel"},
        "tier2": {
            "hot_count": sum(value is True for value in hot_values),
            "legs": {
                key: {"value": "secret", "hot": hot, "threshold": "secret"}
                for key, hot in zip(LEG_KEYS, hot_values)
            },
        },
        "safety_bid_flag": "ignored-secret",
        "built": BUILT,
    }


def supported_eligibility(origin_state="stressed", hot_values=None):
    if hot_values is None:
        hot_values = [False, False, False, False]
    return eligibility(
        origin=receipt(
            origin_state,
            evidence_key="origin-evidence",
            source_reference="public/origin",
        ),
        legs={
                key: receipt(
                    reported_hot,
                    evidence_key=f"{key}-evidence",
                    source_reference=f"public/{key}",
                )
            for key, reported_hot in zip(LEG_KEYS, hot_values)
        },
    )


def valid_call(state="contained", hot_values=None):
    origin_state = "calm" if state == "quiet" else "stressed"
    return two_tier(state, origin_state, hot_values), supported_eligibility(origin_state, hot_values)


def assert_unknown(result):
    assert result["quality"] == "unknown"
    assert result["state"] is None
    assert result["evidence_refs"] == []
    assert isinstance(result["reason_codes"], list) and result["reason_codes"]


@pytest.mark.parametrize(
    ("state", "origin_state", "hot_values"),
    [
        ("quiet", "calm", [False, False, False, False]),
        ("contained", "stressed", [False, False, False, False]),
        ("watching", "strained", [True, False, False, False]),
        ("transmitting", "stressed", [True, False, True, False]),
    ],
)
def test_positive_control_for_every_reported_state(state, origin_state, hot_values):
    result = qualify_us_transmission(
        two_tier=two_tier(state, origin_state, hot_values),
        eligibility=supported_eligibility(origin_state, hot_values),
    )

    assert result == {
        "quality": "qualified",
        "state": state,
        "reason_codes": [],
        "evidence_refs": [
            "public/overall",
            "origin-evidence",
            "public/origin",
            "us_hy_oas_vel-evidence",
            "public/us_hy_oas_vel",
            "kre_spy_rs-evidence",
            "public/kre_spy_rs",
            "move_pctile-evidence",
            "public/move_pctile",
            "sofr_iorb_corridor-evidence",
            "public/sofr_iorb_corridor",
        ],
        "diagnostic": {"reported_state": state},
    }


def test_legitimate_all_false_zero_is_contained_not_false_calm():
    raw, elig = valid_call("contained", [False, False, False, False])
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == "qualified"
    assert result["state"] == "contained"


def test_insufficient_origin_raw_quiet_is_withheld():
    raw, elig = valid_call("quiet", [False, False, False, False])
    del elig["origin"]

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    # Explicit diagnostic allow is independent of missing origin support.
    assert result["diagnostic"] == {"reported_state": "quiet"}


def test_missing_leg_raw_contained_is_withheld():
    raw, elig = valid_call("contained", [False, False, False, False])
    del elig["legs"]["move_pctile"]

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    # Unqualified dependencies withhold current state only.
    assert result["diagnostic"] == {"reported_state": "contained"}


@pytest.mark.parametrize("quality", ["unknown", "denied", "qualified"])
@pytest.mark.parametrize("metadata", ["unknown", "denied", "allowed"])
@pytest.mark.parametrize("diagnostic_permission", ["unknown", "denied", "allowed"])
def test_every_eligibility_permission_and_metadata_combination(quality, metadata, diagnostic_permission):
    raw, elig = valid_call("contained")
    elig.update(quality=quality, metadata=metadata, diagnostic_permission=diagnostic_permission)

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    if quality == "qualified" and metadata == "allowed":
        assert result["quality"] == "qualified"
        assert result["state"] == "contained"
    else:
        assert_unknown(result)
    assert result["diagnostic"] == (
        {"reported_state": "contained"}
        if quality == "qualified" and metadata == "allowed" and diagnostic_permission == "allowed"
        else None
    )


def test_diagnostic_is_allowed_for_valid_enum_even_when_origin_receipt_is_inconsistent():
    raw, elig = valid_call("contained")
    raw["state"] = "transmitting"
    elig["origin"] = receipt(
        "calm",
        evidence_key="origin-evidence",
        source_reference="public/origin",
    )

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    # Reported enum is transmitting; origin mismatch withholds current state only.
    assert result["diagnostic"] == {"reported_state": "transmitting"}


def test_origin_receipt_mismatch_is_withheld_without_leaking_value():
    raw, elig = valid_call("transmitting", [True, False, True, False])
    elig["legs"] = {
        key: receipt(hot, evidence_key=f"{key}-evidence", source_reference=f"public/{key}")
        for key, hot in zip(LEG_KEYS, (True, False, True, False))
    }
    elig["origin"] = receipt(
        "calm",
        evidence_key="origin-evidence",
        source_reference="public/origin",
    )

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "transmitting"}


def test_invalid_diagnostic_enum_is_never_exposed():
    raw, elig = valid_call("contained")
    elig["origin"] = receipt("panicked", evidence_key="origin-evidence")

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    # Origin reported_value is invalid; raw state remains the permitted enum contained.
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_asof_must_equal_built_timestamp():
    raw, elig = valid_call("contained")
    elig["asof"] = "2026-01-02T03:04:06+00:00"

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)


def test_extra_missing_or_invalid_raw_structure_is_unknown():
    bad_raw_values = (
        None,
        [],
        "contained",
        {"state": "contained"},
        {"state": "unknown", "tier1": {}, "tier2": {}, "built": BUILT},
        {"state": "contained", "tier1": {"em_stress_state": "stressed"}, "tier2": {}, "built": BUILT},
        two_tier("contained", hot_values=[False, False, False, "false"]),
    )
    for bad_raw in bad_raw_values:
        result = qualify_us_transmission(two_tier=bad_raw, eligibility=supported_eligibility())
        assert_unknown(result)


@pytest.mark.parametrize("safety_value", [None, True, False, "secret", {"nested": "secret"}])
def test_informational_safety_bid_all_variants_do_not_affect_count_or_output(safety_value):
    raw, elig = valid_call("contained")
    raw["safety_bid_flag"] = safety_value

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == "qualified"
    assert result["state"] == "contained"
    assert "secret" not in json.dumps(result)


def test_raw_sentinel_cannot_leak_in_unknown_output():
    raw, elig = valid_call("contained")
    raw["tier2"]["legs"]["us_hy_oas_vel"]["value"] = "RAW-SENTINEL-VALUE"
    raw["tier2"]["legs"]["us_hy_oas_vel"]["threshold"] = "RAW-SENTINEL-THRESHOLD"
    elig["origin"] = receipt("calm", evidence_key="origin-evidence")

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    serialized = json.dumps(result)
    assert "RAW-SENTINEL" not in serialized


def test_inputs_are_never_mutated_and_outputs_are_deep_detached():
    raw, elig = valid_call("watching", [True, False, False, False])
    raw_before = copy.deepcopy(raw)
    elig_before = copy.deepcopy(elig)

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert raw == raw_before
    assert elig == elig_before
    result["evidence_refs"].clear()
    result["diagnostic"]["reported_state"] = "transmitting"
    assert raw == raw_before
    assert elig == elig_before


def test_hostile_builtin_subclasses_do_not_execute_conversion():
    class HostileDict(dict):
        def __getitem__(self, key):
            raise AssertionError("hostile conversion executed")

        def get(self, key, default=None):
            raise AssertionError("hostile conversion executed")

        def keys(self):
            raise AssertionError("hostile conversion executed")

    class HostileStr(str):
        def __eq__(self, other):
            raise AssertionError("hostile conversion executed")

    for value in (
        HostileDict(),
        HostileStr("contained"),
        {"state": HostileStr("contained")},
        MappingProxyType({}),
    ):
        result = qualify_us_transmission(two_tier=value, eligibility=supported_eligibility())
        assert_unknown(result)
        result = qualify_us_transmission(two_tier=two_tier("contained"), eligibility=value)
        assert_unknown(result)


def test_nested_hostile_strings_do_not_execute_conversion():
    class HostileStr(str):
        def __eq__(self, other):
            raise AssertionError("hostile conversion executed")

    for key in ("quality", "metadata", "value_permission", "diagnostic_permission"):
        raw, elig = valid_call("contained")
        elig[key] = HostileStr("allowed")
        result = qualify_us_transmission(two_tier=raw, eligibility=elig)
        assert_unknown(result)

    raw, elig = valid_call("contained")
    elig["origin"]["quality"] = HostileStr("qualified")
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)
    assert_unknown(result)


def test_reason_codes_are_bounded_and_output_schema_is_exact():
    result = qualify_us_transmission(two_tier=None, eligibility=None)

    assert set(result) == OUTPUT_KEYS
    assert result["reason_codes"] == ["input_unavailable"]
    assert result["diagnostic"] is None


def _fixture_case(case):
    if case["two_tier"] == "valid":
        raw = two_tier("contained")
    elif isinstance(case["two_tier"], dict):
        raw = two_tier("contained")
        raw.update(case["two_tier"])
        if case["two_tier"].get("tier2") == "all_true":
            raw["tier2"] = {
                "hot_count": 4,
                "legs": {key: {"hot": True} for key in LEG_KEYS},
            }
        elif isinstance(case["two_tier"].get("tier2"), dict):
            raw["tier2"].update(case["two_tier"]["tier2"])
            if case["two_tier"]["tier2"].get("legs") == "all_true":
                raw["tier2"]["legs"] = {key: {"hot": True} for key in LEG_KEYS}
            elif isinstance(case["two_tier"]["tier2"].get("legs"), dict):
                raw["tier2"]["legs"].update(case["two_tier"]["tier2"]["legs"])
    else:
        raw = case["two_tier"]

    elig = supported_eligibility()
    if case["eligibility"] == "valid":
        pass
    elif isinstance(case["eligibility"], dict):
        elig.update(case["eligibility"])
    else:
        elig = case["eligibility"]

    if "origin" in case:
        if case["origin"] is None:
            del elig["origin"]
        else:
            elig["origin"].update(case["origin"])
    if "legs" in case:
        for key, changes in case["legs"].items():
            if changes is None:
                del elig["legs"][key]
            else:
                elig["legs"][key].update(changes)
    return raw, elig


@pytest.mark.parametrize("case", json.loads(pathlib.Path("tests/fixtures/intl_workspace/risk_cases.json").read_text())["hostile_cases"])
def test_hostile_fixture_cases_withhold_current_state(case):
    raw, elig = _fixture_case(case)
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == case["expected_quality"]
    assert result["state"] == case["expected_state"]
    assert result["evidence_refs"] == []
    assert result["diagnostic"] == case["expected_diagnostic"]


def test_nested_safety_bid_hot_true_is_not_counted():
    raw, elig = valid_call("contained")
    raw["tier2"]["legs"]["safety_bid_flag"] = {"safety_bid": True, "hot": True}

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == "qualified"
    assert result["state"] == "contained"
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_nested_safety_bid_value_is_never_read():
    class Boom:
        def __getattribute__(self, name):
            raise AssertionError("safety_bid_flag accessed")

        def __iter__(self):
            raise AssertionError("safety_bid_flag accessed")

    raw, elig = valid_call("contained")
    raw["tier2"]["legs"]["safety_bid_flag"] = Boom()

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == "qualified"
    assert result["state"] == "contained"


def test_extra_leg_family_beyond_optional_safety_bid_is_unknown():
    raw, elig = valid_call("contained")
    raw["tier2"]["legs"]["safety_bid_flag"] = {"hot": False}
    raw["tier2"]["legs"]["other_family"] = {"hot": True}

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_safety_bid_without_all_four_families_is_unknown():
    raw, elig = valid_call("contained")
    del raw["tier2"]["legs"]["move_pctile"]
    raw["tier2"]["legs"]["safety_bid_flag"] = {"hot": False}

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_hostile_str_keys_do_not_execute_eq_or_hash():
    class HostileStr(str):
        def __eq__(self, other):
            if type(other) is str:
                raise AssertionError("executed external eq")
            return str.__eq__(self, other)

        def __hash__(self):
            return str.__hash__(self)

    raw, elig = valid_call("contained")
    raw["tier2"]["legs"] = {HostileStr(key): value for key, value in raw["tier2"]["legs"].items()}
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)
    assert_unknown(result)

    raw, elig = valid_call("contained")
    stolen = elig.pop("quality")
    elig[HostileStr("quality")] = stolen
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)
    assert_unknown(result)
    assert result["diagnostic"] is None


def test_nested_hostile_values_do_not_execute_conversion():
    class HostileStr(str):
        def __eq__(self, other):
            raise AssertionError("executed external eq")

    class HostileDict(dict):
        def get(self, key, default=None):
            raise AssertionError("executed external get")

    raw, elig = valid_call("contained")
    raw["tier1"]["em_stress_state"] = HostileStr("stressed")
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)
    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}

    raw, elig = valid_call("contained")
    raw["tier2"]["legs"]["us_hy_oas_vel"] = HostileDict({"hot": False})
    result = qualify_us_transmission(two_tier=raw, eligibility=elig)
    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_denied_value_permission_keeps_permitted_diagnostic():
    raw, elig = valid_call("contained")
    elig["value_permission"] = "denied"

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}


def test_malformed_reported_state_enum_emits_no_diagnostic():
    raw, elig = valid_call("contained")
    raw["state"] = "panicked"

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] is None


def test_diagnostic_survives_extra_eligibility_keys():
    raw, elig = valid_call("contained")
    elig["extra"] = "secret"

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert_unknown(result)
    assert result["diagnostic"] == {"reported_state": "contained"}
    assert "secret" not in json.dumps(result)


def test_output_does_not_alias_or_leak_raw_support():
    raw, elig = valid_call("contained")
    raw["gaps"] = ["secret-gap"]
    raw["diagnostic"] = {"reported_state": "transmitting", "secret": "raw-diag"}
    elig["origin"]["evidence_key"] = "origin-evidence"

    result = qualify_us_transmission(two_tier=raw, eligibility=elig)

    assert result["quality"] == "qualified"
    assert result is not raw and result is not elig
    assert result["diagnostic"] is not raw["diagnostic"]
    assert result["diagnostic"] == {"reported_state": "contained"}
    serialized = json.dumps(result)
    assert "secret-gap" not in serialized
    assert "raw-diag" not in serialized


def test_source_does_not_read_dunder_class():
    source = pathlib.Path("lib/intl_workspace_risk.py").read_text()
    assert ".__class__" not in source


def test_source_has_no_engine_io_or_non_stdlib_imports():
    source = pathlib.Path("lib/intl_workspace_risk.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            module = getattr(node, "module", None)
            imported_names = names if module is None else [module]
            assert imported_names == ["datetime"]
            assert node.level == 0
        if isinstance(node, ast.Name) and node.id in {"open", "exec", "eval", "__import__"}:
            assert False, "implementation must not perform I/O or dynamic execution"
    assert "engine." not in source
