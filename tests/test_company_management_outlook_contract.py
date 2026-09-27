"""Contract tests for the management-outlook comparison (Company/Earnings).

All inputs are explicitly synthetic: native refs are hand-minted test
objects, never real receipts.  The reference amounts mirror a DDOG-shaped
development oracle only; they are test constants, not production values.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import jsonschema
import pytest

from engine.company_intelligence import management_outlook_contract as moc
from engine.company_intelligence.management_outlook_contract import (
    ComparableRevenueInput,
    ManagementOutlookContractError,
    VerifiedContext,
    compute_input_vector_sha256,
    serialize_comparison,
    validate_comparison_request,
    validate_comparison_result,
)


# ---------------------------------------------------------------- helpers

def nref(owner="earnings_tx", object_id="obj_x", schema="earnings_tx.row.v3",
         generation=None, sha256=None, selector="value.range_millions"):
    generation = generation or ("0000" + sha_text(object_id)[:4] + "0" * 40)
    sha256 = sha256 or sha_text(object_id + generation)
    return {
        "owner": owner, "object_id": object_id, "schema": schema,
        "generation": generation, "sha256": sha256, "selector": selector,
    }


def sha_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


DEF_REF = nref(owner="defs", object_id="def_revenue_millions",
               schema="defs.metric.v2", selector="definition")
PERIM_REF = nref(owner="perimeter", object_id="perim_core_rev",
                 schema="perimeter.decision.v1", selector="perimeter.span")


def period(key, start, end):
    return {"key": key, "start": start, "end_exclusive": end}


def role_row(role, low, high, keys, refs=None, definition_ref=None):
    return {
        "role": role, "low": low, "high": high,
        "period_keys": list(keys),
        "refs": [copy.deepcopy(r) for r in (refs if refs is not None else [nref(object_id=f"src_{role}")])],
        "definition_ref": copy.deepcopy(definition_ref if definition_ref is not None else DEF_REF),
    }


ALL_KEYS = ["2026Q1", "2026Q2", "2026Q3", "2026Q4"]


def base_payload(**over):
    payload = {
        "schema": moc.REQUEST_SCHEMA_ID,
        "kind": "MANAGEMENT_REVENUE_REMAINING_YEAR",
        "subject": {
            "issuer_id": "SYNTH001", "fiscal_year": 2026, "metric_id": "revenue",
            "currency": "USD", "accounting_basis": "GAAP", "scale": "millions",
        },
        "fiscal_partition": {
            "periods": [
                period("2026Q1", "2026-01-01", "2026-04-01"),
                period("2026Q2", "2026-04-01", "2026-07-01"),
                period("2026Q3", "2026-07-01", "2026-10-01"),
                period("2026Q4", "2026-10-01", "2027-01-01"),
            ],
            "completed": ["2026Q1"],
            "newly_completed": ["2026Q2"],
            "remaining": ["2026Q3", "2026Q4"],
        },
        "input_roles": [
            role_row("FY_A", "4300", "4340", ALL_KEYS),
            role_row("FY_B", "4460", "4470", ALL_KEYS, refs=[nref(object_id="src_FY_B"), PERIM_REF]),
            role_row("ACTUAL_C_A", "1006.426", "1006.426", ["2026Q1"]),
            role_row("ACTUAL_C_B", "1006.426", "1006.426", ["2026Q1"]),
            role_row("GUIDE_N_A", "1070", "1080", ["2026Q2"]),
            role_row("ACTUAL_N_B", "1121.454", "1121.454", ["2026Q2"]),
        ],
        "perimeter_receipt": copy.deepcopy(PERIM_REF),
    }
    payload.update(over)
    return payload


def base_context(**over):
    ctx = VerifiedContext(
        definition_receipt=copy.deepcopy(DEF_REF),
        binding_receipt=nref(owner="identity", object_id="bind_SYNTH001",
                             schema="identity.binding.v1", selector="issuer_binding"),
        clock_receipt=nref(owner="clock", object_id="cut_20260715",
                           schema="clock.cut.v1", selector="as_of_cut"),
        rights_receipt=nref(owner="rights", object_id="rights_SYNTH001",
                            schema="rights.decision.v1", selector="usage_rights"),
        issuer_id="SYNTH001",
    )
    return ctx


def refuse(payload, ctx="default", code=None):
    """Assert validation refuses the payload; return the error for inspection."""
    context = base_context() if ctx == "default" else ctx
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_request(payload, verified_context=context)
    if code is not None:
        assert excinfo.value.args[0].startswith(code + ":"), excinfo.value.args[0]
    return excinfo.value.args[0]


# ---------------------------------------------------------------- happy path

def test_valid_reference_payload_seals_to_typed_input():
    sealed = validate_comparison_request(base_payload(), verified_context=base_context())
    assert isinstance(sealed, ComparableRevenueInput)
    assert sealed.issuer_id == "SYNTH001"
    assert sealed.fiscal_year == 2026
    assert sealed.currency == "USD"
    assert sealed.accounting_basis == "GAAP"
    assert sealed.fiscal_periods[0].start == date(2026, 1, 1)
    assert sealed.fiscal_periods[0].end_exclusive == date(2026, 4, 1)
    assert sealed.completed == ("2026Q1",)
    assert sealed.newly_completed == ("2026Q2",)
    assert sealed.remaining == ("2026Q3", "2026Q4")
    assert len(sealed.role_amounts) == 6
    fy_b = [ra for ra in sealed.role_amounts if ra.role == "FY_B"][0]
    assert fy_b.amount.low == Decimal("4460")
    assert fy_b.amount.high == Decimal("4470")
    actual = [ra for ra in sealed.role_amounts if ra.role == "ACTUAL_N_B"][0]
    assert actual.amount.low == actual.amount.high == Decimal("1121.454")
    assert sealed.input_vector_sha256 == compute_input_vector_sha256(base_payload())
    assert sealed.perimeter_receipt.owner == "perimeter"


def test_sealed_input_is_frozen():
    sealed = validate_comparison_request(base_payload(), verified_context=base_context())
    with pytest.raises(FrozenInstanceError):
        sealed.issuer_id = "OTHER"


def test_empty_completed_partition_allowed_when_newly_completed_starts_first():
    payload = base_payload()
    payload["fiscal_partition"]["completed"] = []
    payload["fiscal_partition"]["newly_completed"] = ["2026Q1", "2026Q2"]
    payload["fiscal_partition"]["remaining"] = ["2026Q3", "2026Q4"]
    payload["input_roles"] = [
        role_row("FY_A", "4300", "4340", ALL_KEYS),
        role_row("FY_B", "4460", "4470", ALL_KEYS, refs=[nref(object_id="src_FY_B"), PERIM_REF]),
        role_row("GUIDE_N_A", "1040", "1050", ["2026Q1"]),
        role_row("GUIDE_N_A", "1070", "1080", ["2026Q2"]),
        role_row("ACTUAL_N_B", "987.111", "987.111", ["2026Q1"]),
        role_row("ACTUAL_N_B", "1121.454", "1121.454", ["2026Q2"]),
    ]
    sealed = validate_comparison_request(payload, verified_context=base_context())
    assert sealed.completed == ()


def test_input_digest_sealed_when_omitted_and_order_insensitive():
    payload_a = base_payload()
    sealed = validate_comparison_request(payload_a, verified_context=base_context())
    reordered = base_payload()
    reordered["input_roles"] = list(reversed(reordered["input_roles"]))
    for row in reordered["input_roles"]:
        row["refs"] = list(reversed(row["refs"]))
    sealed_reordered = validate_comparison_request(reordered, verified_context=base_context())
    assert sealed.input_vector_sha256 == sealed_reordered.input_vector_sha256
    assert "input_vector_sha256" not in payload_a


def test_declared_input_digest_must_match_recomputation():
    payload = base_payload()
    payload["input_vector_sha256"] = "0" * 64
    refuse(payload, code="input_vector_mismatch")


# ---------------------------------------------------------------- closed shape

def test_unknown_top_level_key_refused():
    payload = base_payload()
    payload["url"] = "https://example.test/synthetic"
    refuse(payload, code="unknown_key")


def test_second_issuer_field_refused():
    payload = base_payload()
    payload["subject"]["issuers"] = ["SYNTH001", "SYNTH002"]
    refuse(payload, code="unknown_key")


def test_caller_boolean_cannot_self_certify():
    payload = base_payload()
    payload["subject"]["verified"] = True
    refuse(payload, code="unknown_key")


def test_request_schema_const_enforced():
    payload = base_payload()
    payload["schema"] = "management_outlook_comparison.v0"
    refuse(payload, code="schema_mismatch")


def test_only_supported_kind_admitted():
    payload = base_payload()
    payload["kind"] = "MANAGEMENT_EPS_REMAINING_YEAR"
    refuse(payload, code="unsupported_kind")


# ---------------------------------------------------------------- verified context

def test_missing_context_refused():
    payload = base_payload()
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_request(payload, verified_context=None)
    assert excinfo.value.args[0].startswith("source_unverified:")


def test_context_of_wrong_type_refused():
    payload = base_payload()
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_request(payload, verified_context={"rights_receipt": True})
    assert excinfo.value.args[0].startswith("source_unverified:")


def test_missing_rights_receipt_refused():
    payload = base_payload()
    ctx = VerifiedContext(
        definition_receipt=copy.deepcopy(DEF_REF),
        binding_receipt=base_context().binding_receipt,
        clock_receipt=base_context().clock_receipt,
        rights_receipt=None,
        issuer_id="SYNTH001",
    )
    refuse(payload, ctx=ctx, code="rights_blocked")


def test_missing_definition_receipt_refused():
    ctx = VerifiedContext(
        definition_receipt=None,
        binding_receipt=base_context().binding_receipt,
        clock_receipt=base_context().clock_receipt,
        rights_receipt=base_context().rights_receipt,
        issuer_id="SYNTH001",
    )
    refuse(base_payload(), ctx=ctx, code="definition_accounting_fx_mismatch")


def test_missing_binding_receipt_refused():
    ctx = VerifiedContext(
        definition_receipt=copy.deepcopy(DEF_REF),
        binding_receipt=None,
        clock_receipt=base_context().clock_receipt,
        rights_receipt=base_context().rights_receipt,
        issuer_id="SYNTH001",
    )
    refuse(base_payload(), ctx=ctx, code="identity_unresolved")


def test_missing_clock_receipt_refused():
    ctx = VerifiedContext(
        definition_receipt=copy.deepcopy(DEF_REF),
        binding_receipt=base_context().binding_receipt,
        clock_receipt=None,
        rights_receipt=base_context().rights_receipt,
        issuer_id="SYNTH001",
    )
    refuse(base_payload(), ctx=ctx, code="source_not_eligible_at_cut")


def test_context_issuer_disagreement_refused():
    ctx = VerifiedContext(
        definition_receipt=copy.deepcopy(DEF_REF),
        binding_receipt=base_context().binding_receipt,
        clock_receipt=base_context().clock_receipt,
        rights_receipt=base_context().rights_receipt,
        issuer_id="SYNTH999",
    )
    refuse(base_payload(), ctx=ctx, code="identity_unresolved")


def test_row_definition_disagreeing_with_context_refused():
    payload = base_payload()
    payload["input_roles"][0]["definition_ref"] = nref(
        owner="defs", object_id="def_revenue_millions", schema="defs.metric.v2",
        generation="f" * 48, selector="definition")
    refuse(payload, code="definition_accounting_fx_mismatch")


# ---------------------------------------------------------------- metric/scale

def test_non_additive_metric_refused():
    payload = base_payload()
    payload["subject"]["metric_id"] = "gross_margin"
    refuse(payload, code="non_additive_metric")


def test_unsupported_metric_refused():
    payload = base_payload()
    payload["subject"]["metric_id"] = "bookings"
    refuse(payload, code="unsupported_metric")


def test_unknown_currency_refused():
    payload = base_payload()
    payload["subject"]["currency"] = "XYY"
    refuse(payload, code="unknown_currency")


def test_unknown_accounting_basis_refused():
    payload = base_payload()
    payload["subject"]["accounting_basis"] = "CASH"
    refuse(payload, code="unknown_accounting_basis")


def test_unknown_scale_refused():
    payload = base_payload()
    payload["subject"]["scale"] = "parsecs"
    refuse(payload, code="unsupported_scale")


# ---------------------------------------------------------------- fiscal partition

def test_partition_membership_overlap_refused():
    payload = base_payload()
    payload["fiscal_partition"]["completed"] = ["2026Q1", "2026Q2"]
    payload["fiscal_partition"]["newly_completed"] = ["2026Q2"]
    refuse(payload, code="partition_overlap")


def test_partition_membership_gap_refused():
    payload = base_payload()
    payload["fiscal_partition"]["remaining"] = ["2026Q4"]
    refuse(payload, code="partition_gap")


def test_partition_not_chronological_refused():
    payload = base_payload()
    payload["fiscal_partition"]["completed"] = ["2026Q2"]
    payload["fiscal_partition"]["newly_completed"] = ["2026Q1"]
    payload["fiscal_partition"]["remaining"] = ["2026Q3", "2026Q4"]
    payload["input_roles"] = [
        role_row("FY_A", "4300", "4340", ALL_KEYS),
        role_row("FY_B", "4460", "4470", ALL_KEYS, refs=[nref(object_id="src_FY_B"), PERIM_REF]),
        role_row("ACTUAL_C_A", "1006.426", "1006.426", ["2026Q2"]),
        role_row("ACTUAL_C_B", "1006.426", "1006.426", ["2026Q2"]),
        role_row("GUIDE_N_A", "500", "510", ["2026Q1"]),
        role_row("ACTUAL_N_B", "495.5", "495.5", ["2026Q1"]),
    ]
    refuse(payload, code="partition_not_chronological")


def test_duplicate_period_key_refused():
    payload = base_payload()
    payload["fiscal_partition"]["periods"][1] = period("2026Q1", "2026-04-01", "2026-07-01")
    refuse(payload, code="duplicate_period_key")


def test_reversed_period_dates_refused():
    payload = base_payload()
    payload["fiscal_partition"]["periods"][0] = period("2026Q1", "2026-04-01", "2026-01-01")
    refuse(payload, code="reversed_period_dates")


def test_cumulative_period_beside_atomic_refused():
    payload = base_payload()
    payload["fiscal_partition"]["periods"][1] = period("2026H1", "2026-01-01", "2026-07-01")
    refuse(payload, code="period_overlap")


def test_annual_role_not_spanning_selected_fiscal_year_refused():
    payload = base_payload()
    payload["input_roles"][1]["period_keys"] = ["2026Q1", "2026Q2"]
    refuse(payload, code="fiscal_year_mismatch")


def test_role_citing_unknown_period_key_refused():
    payload = base_payload()
    payload["input_roles"][5]["period_keys"] = ["2025Q4"]
    refuse(payload, code="unknown_period_key")


def test_more_than_four_atomic_periods_refused():
    payload = base_payload()
    payload["fiscal_partition"]["periods"].append(period("2026Q5", "2027-01-01", "2027-02-01"))
    payload["fiscal_partition"]["remaining"] = ["2026Q3", "2026Q4", "2026Q5"]
    refuse(payload, code="request_bound_exceeded")


# ---------------------------------------------------------------- role coverage

def test_missing_annual_role_refused():
    payload = base_payload()
    payload["input_roles"] = [row for row in payload["input_roles"] if row["role"] != "FY_B"]
    refuse(payload, code="missing_role")


def test_missing_newly_completed_guide_row_refused():
    payload = base_payload()
    payload["fiscal_partition"]["newly_completed"] = ["2026Q2", "2026Q3"]
    payload["fiscal_partition"]["remaining"] = ["2026Q4"]
    payload["input_roles"] = [
        role_row("FY_A", "4300", "4340", ALL_KEYS),
        role_row("FY_B", "4460", "4470", ALL_KEYS, refs=[nref(object_id="src_FY_B"), PERIM_REF]),
        role_row("ACTUAL_C_A", "1006.426", "1006.426", ["2026Q1"]),
        role_row("ACTUAL_C_B", "1006.426", "1006.426", ["2026Q1"]),
        role_row("GUIDE_N_A", "1070", "1080", ["2026Q2"]),
        role_row("ACTUAL_N_B", "1121.454", "1121.454", ["2026Q2"]),
        role_row("ACTUAL_N_B", "800.25", "800.25", ["2026Q3"]),
    ]
    refuse(payload, code="missing_role_row")


def test_absent_row_in_nonempty_completed_partition_refused():
    payload = base_payload()
    payload["input_roles"] = [row for row in payload["input_roles"] if row["role"] != "ACTUAL_C_B"]
    refuse(payload, code="missing_role_row")


def test_duplicate_role_row_refused():
    payload = base_payload()
    payload["input_roles"].append(role_row("ACTUAL_N_B", "1121.454", "1121.454", ["2026Q2"]))
    refuse(payload, code="duplicate_role_row")


def test_unknown_role_refused():
    payload = base_payload()
    payload["input_roles"].append(role_row("GUIDE_R_A", "900", "910", ["2026Q3"]))
    refuse(payload, code="unknown_role")


def test_role_row_bound_refused_before_semantics():
    payload = base_payload()
    for _ in range(12):
        payload["input_roles"].append(role_row("FY_A", "4300", "4340", ALL_KEYS))
    refuse(payload, code="request_bound_exceeded")


def test_native_ref_bound_refused():
    payload = base_payload()
    many = [nref(object_id=f"bulk_{i}") for i in range(12)]
    for row in payload["input_roles"]:
        row["refs"] = [copy.deepcopy(r) for r in many]
    refuse(payload, code="request_bound_exceeded")


# ---------------------------------------------------------------- amounts

def test_actual_must_be_point_value():
    payload = base_payload()
    payload["input_roles"][5]["low"] = "1121.000"
    refuse(payload, code="actual_not_point")


def test_reversed_guidance_range_refused():
    payload = base_payload()
    payload["input_roles"][4]["low"] = "1080"
    payload["input_roles"][4]["high"] = "1070"
    refuse(payload, code="invalid_range")


@pytest.mark.parametrize("bad", [
    "1e3", "1E3", "NaN", "Infinity", "-Infinity", "nan",
    "1.2345678", "0.0000001", "-0.0000001",
    "1000000000000", "-1000000000000",
    "+4300", "04300", "4300.", ".5", "", " 4300", "4300 ",
    "9999999999999",
])
def test_input_amount_envelope_refused(bad):
    payload = base_payload()
    payload["input_roles"][4]["low"] = bad
    refuse(payload, code="invalid_amount")


@pytest.mark.parametrize("ok", [
    "0", "-0", "0.000001", "999999999999.999999", "-999999999999.999999",
    "1", "4300", "1006.426", "1121.454",
])
def test_input_amount_envelope_boundaries_admitted(ok):
    payload = base_payload()
    payload["input_roles"][0]["low"] = ok
    payload["input_roles"][0]["high"] = "999999999999.999999"
    sealed = validate_comparison_request(payload, verified_context=base_context())
    assert sealed.role_amounts[0].amount.low == Decimal(ok)


def test_non_string_amount_refused():
    payload = base_payload()
    payload["input_roles"][0]["low"] = 4300
    refuse(payload, code="amount_not_string")


def test_boolean_amount_refused():
    payload = base_payload()
    payload["input_roles"][0]["low"] = True
    refuse(payload, code="amount_not_string")


def test_fiscal_year_boolean_refused():
    payload = base_payload()
    payload["subject"]["fiscal_year"] = True
    refuse(payload, code="invalid_request_shape")


def test_fiscal_year_out_of_profile_refused():
    payload = base_payload()
    payload["subject"]["fiscal_year"] = 1975
    refuse(payload, code="fiscal_year_out_of_profile")


def test_real_zero_is_not_missing():
    payload = base_payload()
    payload["input_roles"][5]["low"] = "0"
    payload["input_roles"][5]["high"] = "0"
    sealed = validate_comparison_request(payload, verified_context=base_context())
    xb = [ra for ra in sealed.role_amounts if ra.role == "ACTUAL_N_B"][0]
    assert xb.amount.low == xb.amount.high == Decimal("0")


# ---------------------------------------------------------------- native refs

def test_eval_style_selector_refused():
    payload = base_payload()
    payload["input_roles"][0]["refs"][0] = nref(
        owner="earnings_tx", object_id="src_FY_A", selector="eval(open('/etc/hosts').read())")
    refuse(payload, code="invalid_source_selector")


def test_import_selector_refused():
    payload = base_payload()
    payload["input_roles"][0]["refs"][0] = nref(
        owner="earnings_tx", object_id="src_FY_A", selector="__import__")
    refuse(payload, code="invalid_source_selector")


def test_mixed_generation_for_same_object_refused():
    payload = base_payload()
    payload["input_roles"][2]["refs"][0] = nref(
        owner="earnings_tx", object_id="src_FY_A", generation="a" * 48)
    refuse(payload, code="mixed_generation")


def test_sha_inconsistency_for_same_object_generation_refused():
    payload = base_payload()
    payload["input_roles"][2]["refs"][0] = nref(
        owner="earnings_tx", object_id="src_FY_A", sha256="b" * 64)
    refuse(payload, code="ref_inconsistency")


def test_ungrounded_perimeter_receipt_refused():
    payload = base_payload()
    payload["perimeter_receipt"] = nref(owner="perimeter", object_id="perim_other",
                                        schema="perimeter.decision.v1", selector="perimeter.span")
    refuse(payload, code="perimeter_not_comparable")


def test_amount_without_source_refs_refused():
    payload = base_payload()
    payload["input_roles"][0]["refs"] = []
    refuse(payload, code="missing_source_ref")


def test_native_ref_closed_shape_refused():
    payload = base_payload()
    payload["input_roles"][0]["refs"][0]["bytes"] = "trusted=true"
    refuse(payload, code="unknown_key")


# ---------------------------------------------------------------- schema file

def test_schema_file_is_valid_draft202012_and_closed():
    schema = moc.load_contract_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["properties"]["authority"]["additionalProperties"] is False
    assert set(schema["required"]) == set(moc.RESULT_SECTIONS)


def test_schema_declares_every_result_section_closed():
    schema = moc.load_contract_schema()
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                assert node.get("additionalProperties") is False, node.get("properties", {}).keys()
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(schema)


# ---------------------------------------------------------------- serialization

def valid_calc_result(**over):
    result = {
        "subject": {
            "issuer_id": "SYNTH001", "fiscal_year": 2026, "metric_id": "revenue",
            "currency": "USD", "accounting_basis": "GAAP", "scale": "millions",
        },
        "fiscal_partition": {
            "periods": [period("2026Q1", "2026-01-01", "2026-04-01"),
                        period("2026Q2", "2026-04-01", "2026-07-01"),
                        period("2026Q3", "2026-07-01", "2026-10-01"),
                        period("2026Q4", "2026-10-01", "2027-01-01")],
            "completed": ["2026Q1"],
            "newly_completed": ["2026Q2"],
            "remaining": ["2026Q3", "2026Q4"],
        },
        "input_roles": [
            {"role": "FY_A", "low": "4300", "high": "4340", "period_keys": ALL_KEYS,
             "refs_sha256": [sha_text("a")], "definition_sha256": sha_text("d")},
            {"role": "FY_B", "low": "4460", "high": "4470", "period_keys": ALL_KEYS,
             "refs_sha256": [sha_text("b")], "definition_sha256": sha_text("d")},
        ],
        "input_vector": {
            "input_vector_sha256": sha_text("vector"),
            "definition_receipt_sha256": sha_text("d"),
            "perimeter_receipt_sha256": sha_text("p"),
            "role_generations": [{"role": "FY_A", "generation": "0" * 48}],
        },
        "eligible": True,
        "reasons": [],
        "explanation": "every admitted dimension was checked for this comparison kind",
        "values": {
            "annual_midpoint_change": Decimal("140"),
            "new_period_deviation": Decimal("46.454"),
            "prior_actual_revision": Decimal("0"),
            "earlier_remaining": Decimal("2238.574"),
            "later_remaining": Decimal("2332.120"),
            "remaining_change": Decimal("93.546"),
        },
        "limitations": list(moc.LIMITATIONS),
        "correction": {"corrected": False, "predecessor_id": None, "reason": None},
    }
    result.update(over)
    return result


def test_serialize_valid_result_roundtrips_through_validator():
    envelope = serialize_comparison(valid_calc_result())
    assert set(envelope) == set(moc.RESULT_SECTIONS)
    assert envelope["schema"] == moc.SCHEMA_ID
    assert envelope["result"]["remaining_change"] == "93.546"
    assert envelope["result"]["later_remaining"] == "2332.12"
    assert envelope["result"]["currency"] == "USD"
    assert envelope["result"]["scale"] == "millions"
    assert envelope["result"]["formula_revision"] == moc.FORMULA_REVISION
    assert envelope["authority"] == {flag: False for flag in moc.AUTHORITY_FLAGS}
    validate_comparison_result(envelope)
    assert envelope["comparison_id"].startswith("moc_")


def test_serialized_envelope_carries_no_promotion_or_surprise_key():
    envelope = serialize_comparison(valid_calc_result())
    import json as _json
    blob = _json.dumps(envelope)
    for banned in ("confidence", "probability", "consensus", "beat_the", "miss_the",
                   "expected_value", "surprise"):
        assert banned not in blob


def test_comparison_id_excludes_correction_lineage():
    plain = serialize_comparison(valid_calc_result())
    # A predecessor is a DIFFERENT prior envelope; naming itself is refused (see
    # test_self_referential_correction_link_is_refused). Lineage still never
    # enters the content identity.
    corrected = serialize_comparison(valid_calc_result(correction={
        "corrected": True, "predecessor_id": "moc_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "reason": "source revision superseded the prior result"}))
    assert corrected["correction"]["corrected"] is True
    assert corrected["comparison_id"] == plain["comparison_id"]


def test_comparison_id_tracks_content_not_order():
    a = serialize_comparison(valid_calc_result())
    reordered = valid_calc_result()
    reordered["input_roles"] = list(reversed(reordered["input_roles"]))
    b = serialize_comparison(reordered)
    assert a["comparison_id"] == b["comparison_id"]


def test_comparison_id_changes_when_input_vector_changes():
    a = serialize_comparison(valid_calc_result())
    changed = valid_calc_result()
    changed["input_vector"]["input_vector_sha256"] = sha_text("vector2")
    b = serialize_comparison(changed)
    assert a["comparison_id"] != b["comparison_id"]


def test_serialize_refused_result_has_null_result_and_explanation():
    envelope = serialize_comparison(valid_calc_result(
        eligible=False,
        reasons=["no_remaining_horizon"],
        explanation="the selected fiscal year has no remaining period; this comparison kind does not project a future outlook",
        values=None,
    ))
    assert envelope["result"] is None
    assert envelope["eligibility"]["reasons"] == ["no_remaining_horizon"]
    assert envelope["eligibility"]["explanation"]
    validate_comparison_result(envelope)


def test_serialize_rejects_result_values_when_refused():
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        serialize_comparison(valid_calc_result(eligible=False, reasons=["rights_blocked"],
                                               explanation="rights receipt absent"))
    assert excinfo.value.args[0].startswith("result_present_when_refused:")


def test_serialize_rejects_refusal_without_reasons():
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        serialize_comparison(valid_calc_result(eligible=False, reasons=[],
                                               explanation="x", values=None))
    assert excinfo.value.args[0].startswith("refusal_shape_invalid:")


def test_validate_result_rejects_tampered_authority():
    envelope = serialize_comparison(valid_calc_result())
    envelope["authority"]["rank"] = True
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_result(envelope)
    assert excinfo.value.args[0].startswith("authority_not_sealed:")


def test_validate_result_rejects_promotion_field():
    envelope = serialize_comparison(valid_calc_result())
    envelope["result"]["confidence"] = "0.9"
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_result(envelope)
    assert excinfo.value.args[0].startswith("forbidden_promotion_field:")


def test_validate_result_rejects_unknown_section():
    envelope = serialize_comparison(valid_calc_result())
    envelope["rendered_at"] = "2026-09-24T00:00:00Z"
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_result(envelope)
    assert excinfo.value.args[0].startswith("unknown_section:")


def test_validate_result_recomputes_content_identity():
    envelope = serialize_comparison(valid_calc_result())
    envelope["comparison_id"] = "moc_" + "0" * 64
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_result(envelope)
    assert excinfo.value.args[0].startswith("comparison_id_mismatch:")


def test_validate_result_rejects_out_of_envelope_value():
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        serialize_comparison(valid_calc_result(values={
            "annual_midpoint_change": Decimal("9999999999999999"),
            "new_period_deviation": Decimal("46.454"),
            "prior_actual_revision": Decimal("0"),
            "earlier_remaining": Decimal("2238.574"),
            "later_remaining": Decimal("2332.120"),
            "remaining_change": Decimal("93.546"),
        }))
    assert excinfo.value.args[0].startswith("result_out_of_envelope:")


def test_validate_result_rejects_eighth_fractional_digit():
    envelope = serialize_comparison(valid_calc_result())
    envelope["result"]["remaining_change"] = "93.54600001"
    envelope["comparison_id"] = moc.compute_comparison_id(envelope)
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        validate_comparison_result(envelope)
    assert excinfo.value.args[0].startswith("result_out_of_envelope:")
