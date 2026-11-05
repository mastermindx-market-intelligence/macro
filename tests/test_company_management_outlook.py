"""Calculator tests for the management-outlook comparison kernel.

The reference vector is a synthetic, DDOG-shaped DEVELOPMENT ORACLE ONLY —
never a production constant.  Every input is synthetic; no native bytes,
URLs, filings or real receipts are read anywhere.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from engine.company_intelligence import management_outlook_contract as moc
from engine.company_intelligence.management_outlook_contract import (
    ComparableRevenueInput,
    ManagementOutlookContractError,
    VerifiedContext,
    compute_input_vector_sha256,
    validate_comparison_request,
    validate_comparison_result,
)
from engine.company_intelligence.management_outlook import compare_management_outlook


# ---------------------------------------------------------------- helpers

def sha_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def nref(owner="earnings_tx", object_id="obj_x", schema="earnings_tx.row.v3",
         generation=None, sha256=None, selector="value.range_millions"):
    generation = generation or ("0000" + sha_text(object_id)[:4] + "0" * 40)
    sha256 = sha256 or sha_text(object_id + generation)
    return {"owner": owner, "object_id": object_id, "schema": schema,
            "generation": generation, "sha256": sha256, "selector": selector}


DEF_REF = nref(owner="defs", object_id="def_revenue_millions",
               schema="defs.metric.v2", selector="definition")
PERIM_REF = nref(owner="perimeter", object_id="perim_core_rev",
                 schema="perimeter.decision.v1", selector="perimeter.span")
FY_A_REF = nref(object_id="src_FY_A")
FY_B_REF = nref(object_id="src_FY_B")

ALL_KEYS = ["2026Q1", "2026Q2", "2026Q3", "2026Q4"]


def role_row(role, low, high, keys, refs=None):
    return {
        "role": role, "low": low, "high": high, "period_keys": list(keys),
        "refs": [copy.deepcopy(r) for r in (refs if refs is not None else [nref(object_id=f"src_{role}_{keys[0]}")])],
        "definition_ref": copy.deepcopy(DEF_REF),
    }


def base_payload(fy_a=("4300", "4340"), fy_b=("4450", "4470"),
                 pa="1006.426", pb="1006.426",
                 ga=("1070", "1080"), xb="1121.454",
                 completed=("2026Q1",), newly_completed=("2026Q2",),
                 guide_n=None, actual_n=None):
    if guide_n is None:
        guide_n = [("2026Q2", ga)]
    if actual_n is None:
        actual_n = [("2026Q2", xb)]
    remaining = tuple(k for k in ALL_KEYS if k not in completed and k not in newly_completed)
    rows = [
        role_row("FY_A", fy_a[0], fy_a[1], ALL_KEYS, refs=[FY_A_REF]),
        role_row("FY_B", fy_b[0], fy_b[1], ALL_KEYS, refs=[FY_B_REF, PERIM_REF]),
    ]
    for key in completed:
        rows.append(role_row("ACTUAL_C_A", pa, pa, [key]))
        rows.append(role_row("ACTUAL_C_B", pb, pb, [key]))
    for key, span in guide_n:
        rows.append(role_row("GUIDE_N_A", span[0], span[1], [key]))
    for key, value in actual_n:
        rows.append(role_row("ACTUAL_N_B", value, value, [key]))
    return {
        "schema": moc.REQUEST_SCHEMA_ID,
        "kind": "MANAGEMENT_REVENUE_REMAINING_YEAR",
        "subject": {
            "issuer_id": "SYNTH001", "fiscal_year": 2026, "metric_id": "revenue",
            "currency": "USD", "accounting_basis": "GAAP", "scale": "millions",
        },
        "fiscal_partition": {
            "periods": [
                {"key": "2026Q1", "start": "2026-01-01", "end_exclusive": "2026-04-01"},
                {"key": "2026Q2", "start": "2026-04-01", "end_exclusive": "2026-07-01"},
                {"key": "2026Q3", "start": "2026-07-01", "end_exclusive": "2026-10-01"},
                {"key": "2026Q4", "start": "2026-10-01", "end_exclusive": "2027-01-01"},
            ],
            "completed": list(completed),
            "newly_completed": list(newly_completed),
            "remaining": list(remaining),
        },
        "input_roles": rows,
        "perimeter_receipt": copy.deepcopy(PERIM_REF),
    }


def base_context(definition_ref=None, issuer_id="SYNTH001"):
    return VerifiedContext(
        definition_receipt=copy.deepcopy(definition_ref if definition_ref is not None else DEF_REF),
        binding_receipt=nref(owner="identity", object_id="bind_SYNTH001",
                             schema="identity.binding.v1", selector="issuer_binding"),
        clock_receipt=nref(owner="clock", object_id="cut_20260715",
                           schema="clock.cut.v1", selector="as_of_cut"),
        rights_receipt=nref(owner="rights", object_id="rights_SYNTH001",
                            schema="rights.decision.v1", selector="usage_rights"),
        issuer_id=issuer_id,
    )


def seal(payload, context=None):
    return validate_comparison_request(payload, verified_context=context or base_context())


def compare(**kwargs):
    return compare_management_outlook(seal(base_payload(**kwargs)))


def result_of(envelope):
    assert envelope["result"] is not None
    return envelope["result"]


# ---------------------------------------------------------------- reference vector

def test_reference_vector_synthetic_ddog_shaped():
    # Synthetic development oracle (DDOG-shaped, USD millions): never production.
    envelope = compare()
    validate_comparison_result(envelope)
    values = result_of(envelope)
    assert values["annual_midpoint_change"] == "140"
    assert values["new_period_deviation"] == "46.454"
    assert values["prior_actual_revision"] == "0"
    assert values["earlier_remaining"] == "2238.574"
    assert values["later_remaining"] == "2332.12"
    assert values["remaining_change"] == "93.546"
    assert values["currency"] == "USD"
    assert values["scale"] == "millions"
    assert values["formula_revision"] == moc.FORMULA_REVISION


def test_prior_actual_revision_subtracts_ten():
    envelope = compare(pb="1016.426")
    values = result_of(envelope)
    assert values["prior_actual_revision"] == "10"
    assert values["remaining_change"] == "83.546"
    assert values["earlier_remaining"] == "2238.574"
    assert values["later_remaining"] == "2322.12"


def test_unchanged_inputs_yield_zero_residual():
    envelope = compare(fy_b=("4300", "4340"), xb="1075")
    values = result_of(envelope)
    assert values["annual_midpoint_change"] == "0"
    assert values["new_period_deviation"] == "0"
    assert values["prior_actual_revision"] == "0"
    assert values["remaining_change"] == "0"


def test_ten_increase_in_fy_b_raises_residual_by_ten():
    values = result_of(compare(fy_b=("4450", "4490")))
    assert values["annual_midpoint_change"] == "150"
    assert values["remaining_change"] == "103.546"


def test_ten_increase_in_x_b_n_lowers_residual_by_ten():
    values = result_of(compare(xb="1131.454"))
    assert values["new_period_deviation"] == "56.454"
    assert values["remaining_change"] == "83.546"


def test_equal_shift_of_both_actuals_moves_levels_not_difference():
    values = result_of(compare(pa="1016.426", pb="1016.426"))
    assert values["prior_actual_revision"] == "0"
    assert values["earlier_remaining"] == "2228.574"
    assert values["later_remaining"] == "2322.12"
    assert values["remaining_change"] == "93.546"


def test_consistent_positive_unit_scaling_scales_all_six():
    values = result_of(compare(
        fy_a=("43000", "43400"), fy_b=("44500", "44700"),
        pa="10064.26", pb="10064.26", ga=("10700", "10800"), xb="11214.54"))
    assert values["annual_midpoint_change"] == "1400"
    assert values["new_period_deviation"] == "464.54"
    assert values["prior_actual_revision"] == "0"
    assert values["earlier_remaining"] == "22385.74"
    assert values["later_remaining"] == "23321.2"
    assert values["remaining_change"] == "935.46"


def test_negative_residual_is_valid():
    values = result_of(compare(fy_b=("4290", "4310")))
    assert values["annual_midpoint_change"] == "-20"
    assert values["later_remaining"] == "2172.12"
    assert values["remaining_change"] == "-66.454"


# ---------------------------------------------------------------- partitions

def test_genuine_empty_c_partition_with_two_newly_completed_periods():
    envelope = compare(
        completed=(),
        newly_completed=("2026Q1", "2026Q2"),
        guide_n=[("2026Q1", ("1040", "1050")), ("2026Q2", ("1070", "1080"))],
        actual_n=[("2026Q1", "987.111"), ("2026Q2", "1121.454")])
    values = result_of(envelope)
    assert values["prior_actual_revision"] == "0"
    assert values["new_period_deviation"] == "-11.435"
    assert values["earlier_remaining"] == "2200"
    assert values["later_remaining"] == "2351.435"
    assert values["remaining_change"] == "151.435"


def test_missing_earlier_n_guide_refused_before_calculation():
    payload = base_payload(newly_completed=("2026Q2", "2026Q3"),
                           guide_n=[("2026Q2", ("1070", "1080"))],
                           actual_n=[("2026Q2", "1121.454"), ("2026Q3", "800.25")])
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        seal(payload)
    assert excinfo.value.args[0].startswith("missing_role_row:")


def test_kernel_rejects_unsealed_row_gap_on_typed_input():
    sealed = seal(base_payload())
    gutted = replace(sealed, role_amounts=tuple(
        row for row in sealed.role_amounts if row.role != "ACTUAL_N_B"))
    with pytest.raises(ManagementOutlookContractError) as excinfo:
        compare_management_outlook(gutted)
    assert excinfo.value.args[0].startswith("missing_role_row:")


def test_final_year_without_remaining_period_refuses_this_kind():
    envelope = compare(
        completed=("2026Q1", "2026Q2"), newly_completed=("2026Q3", "2026Q4"),
        guide_n=[("2026Q3", ("800", "810")), ("2026Q4", ("900", "910"))],
        actual_n=[("2026Q3", "805.5"), ("2026Q4", "905.25")])
    assert envelope["result"] is None
    assert envelope["eligibility"]["eligible"] is False
    assert envelope["eligibility"]["reasons"] == ["no_remaining_horizon"]
    assert "no remaining period" in envelope["eligibility"]["explanation"]
    assert envelope["input_roles"], "refusal must retain permitted input references"
    validate_comparison_result(envelope)


# ---------------------------------------------------------------- identity

def test_source_reordering_leaves_result_identity_unchanged():
    straight = compare()
    payload = base_payload()
    payload["input_roles"] = list(reversed(payload["input_roles"]))
    for row in payload["input_roles"]:
        row["refs"] = list(reversed(row["refs"]))
    reordered = compare_management_outlook(seal(payload))
    assert reordered["comparison_id"] == straight["comparison_id"]
    assert reordered["result"] == straight["result"]


def _same_numbers_different_identity(mutate):
    straight = compare()
    payload = base_payload()
    context = mutate(payload) or base_context()
    divergent = compare_management_outlook(seal(payload, context))
    assert divergent["result"] == straight["result"]
    assert divergent["comparison_id"] != straight["comparison_id"]


def test_source_generation_change_changes_identity_despite_equal_numbers():
    def mutate(payload):
        bumped = nref(owner="earnings_tx", object_id="src_ACTUAL_N_B_2026Q2",
                      schema="earnings_tx.row.v3", generation="c" * 48)
        for row in payload["input_roles"]:
            if row["role"] == "ACTUAL_N_B":
                row["refs"] = [bumped]
    _same_numbers_different_identity(mutate)


def test_definition_change_changes_identity_despite_equal_numbers():
    def mutate(payload):
        new_definition = nref(owner="defs", object_id="def_revenue_millions",
                              schema="defs.metric.v2", generation="d" * 48,
                              selector="definition")
        for row in payload["input_roles"]:
            row["definition_ref"] = copy.deepcopy(new_definition)
        return base_context(definition_ref=new_definition)
    _same_numbers_different_identity(mutate)


def test_perimeter_decision_change_changes_identity_despite_equal_numbers():
    def mutate(payload):
        payload["perimeter_receipt"] = copy.deepcopy(FY_A_REF)
    _same_numbers_different_identity(mutate)


def test_formula_revision_change_changes_identity_despite_equal_numbers(monkeypatch):
    straight = compare()
    monkeypatch.setattr(moc, "FORMULA_REVISION", "management_outlook_remaining_year/v2")
    revised = compare()
    assert revised["result"]["remaining_change"] == straight["result"]["remaining_change"]
    assert revised["comparison_id"] != straight["comparison_id"]


# ---------------------------------------------------------------- arithmetic quality

def test_boundary_mathematics_against_100_digit_oracle():
    envelope = compare(pb="1016.426")
    values = result_of(envelope)
    with localcontext() as oracle:
        oracle.prec = 100
        fa = (Decimal("4300") + Decimal("4340")) / 2
        fb = (Decimal("4450") + Decimal("4470")) / 2
        ga = (Decimal("1070") + Decimal("1080")) / 2
        pa, pb_, xb = Decimal("1006.426"), Decimal("1016.426"), Decimal("1121.454")
        expected = {
            "annual_midpoint_change": fb - fa,
            "new_period_deviation": xb - ga,
            "prior_actual_revision": pb_ - pa,
            "earlier_remaining": fa - pa - ga,
            "later_remaining": fb - pb_ - xb,
            "remaining_change": (fb - fa) - (xb - ga) - (pb_ - pa),
        }
    for key, oracle_value in expected.items():
        assert Decimal(values[key]) == oracle_value, key


def test_envelope_is_closed_and_authority_all_false():
    envelope = compare()
    assert set(envelope) == set(moc.RESULT_SECTIONS)
    assert envelope["authority"] == {flag: False for flag in moc.AUTHORITY_FLAGS}
    assert set(envelope["result"]) == {
        "annual_midpoint_change", "new_period_deviation", "prior_actual_revision",
        "earlier_remaining", "later_remaining", "remaining_change",
        "currency", "scale", "formula_revision"}


def test_no_distribution_or_band_is_inferred_from_endpoints():
    envelope = compare(fy_a=("4300", "4340"))
    import json as _json
    blob = _json.dumps(envelope)
    for banned in ("distribution", "probability", "band", "confidence",
                   "consensus", "upper_bound", "lower_bound"):
        assert banned not in blob


# ---------------------------------------------------------------- review pins (T2/T3 independent review, 2026-09-24)


def test_precision_pin_at_input_ceiling_matches_100_digit_oracle():
    """Near-ceiling inputs (12 integer + 6 fractional digits) must come out exact.

    A kernel context below ~19 significant digits would round these; equality
    with a 100-digit oracle pins the Decimal precision law by execution.
    """
    fy_a = ("999999999999.999998", "999999999999.999999")
    fy_b = ("999999999999.999997", "999999999999.999999")
    pa, pb = "123456789012.123456", "123456789012.123457"
    ga = ("111111111111.111111", "111111111111.111113")
    xb = "222222222222.222222"
    values = result_of(compare(fy_a=fy_a, fy_b=fy_b, pa=pa, pb=pb, ga=ga, xb=xb))
    with localcontext() as oracle:
        oracle.prec = 100
        fa = (Decimal(fy_a[0]) + Decimal(fy_a[1])) / 2
        fb = (Decimal(fy_b[0]) + Decimal(fy_b[1])) / 2
        g = (Decimal(ga[0]) + Decimal(ga[1])) / 2
        p_a, p_b, x = Decimal(pa), Decimal(pb), Decimal(xb)
        expected = {
            "annual_midpoint_change": fb - fa,
            "new_period_deviation": x - g,
            "prior_actual_revision": p_b - p_a,
            "earlier_remaining": fa - p_a - g,
            "later_remaining": fb - p_b - x,
            "remaining_change": (fb - fa) - (x - g) - (p_b - p_a),
        }
    for key, oracle_value in expected.items():
        assert Decimal(values[key]) == oracle_value, key
    assert len(values["earlier_remaining"].replace("-", "").replace(".", "")) >= 18


def test_input_vector_digest_is_by_value_not_spelling():
    canonical = seal(base_payload())
    respelled = seal(base_payload(pa="1006.4260", pb="1006.4260", xb="1121.45400"))
    assert respelled.input_vector_sha256 == canonical.input_vector_sha256
    assert compare()["comparison_id"] == compare(pa="1006.4260", pb="1006.4260", xb="1121.45400")["comparison_id"]


def test_role_generations_echo_is_deduplicated_and_bounded():
    envelope = compare()
    pairs = [(g["role"], g["generation"]) for g in envelope["input_vector"]["role_generations"]]
    assert len(pairs) == len(set(pairs))
    assert len(pairs) <= 16


def test_self_referential_correction_link_is_refused():
    envelope = compare()
    looped = copy.deepcopy(envelope)
    looped["correction"] = {"corrected": True, "predecessor_id": envelope["comparison_id"], "reason": "re-issue"}
    with pytest.raises(ValueError, match="correction_shape_invalid"):
        moc.validate_comparison_result(looped)


def test_distinct_refs_per_role_row_are_bounded_at_the_request_layer():
    # The contract caps input_roles[].refs_sha256 at 8 items; the request layer must own
    # that bound so an admitted request can never die at serialize with an untyped
    # schema failure. Nine distinct refs on one row stay under the other bounds
    # (15 role-generation tuples, well under 64 native refs) and are refused typed.
    payload = base_payload()
    fy_a = next(row for row in payload["input_roles"] if row["role"] == "FY_A")
    fy_a["refs"] = [nref(object_id=f"src_FY_A_{i}") for i in range(9)]
    with pytest.raises(ValueError, match="request_bound_exceeded"):
        seal(payload)
    fy_a["refs"] = [nref(object_id=f"src_FY_A_{i}") for i in range(8)]
    envelope = compare_management_outlook(seal(payload))
    echoed = next(row for row in envelope["input_roles"] if row["role"] == "FY_A")["refs_sha256"]
    assert len(echoed) == 8 and len(set(echoed)) == 8
    moc.validate_comparison_result(envelope)


def test_duplicate_refs_on_a_role_row_are_echoed_once():
    payload = base_payload()
    fy_a = next(row for row in payload["input_roles"] if row["role"] == "FY_A")
    fy_a["refs"] = [copy.deepcopy(FY_A_REF) for _ in range(3)]
    envelope = compare_management_outlook(seal(payload))
    echoed = next(row for row in envelope["input_roles"] if row["role"] == "FY_A")["refs_sha256"]
    assert echoed == [FY_A_REF["sha256"]]
    moc.validate_comparison_result(envelope)
    # Identity agrees with the echo: a verbatim-repeated citation is the same sealed request.
    single = compare()
    assert envelope["comparison_id"] == single["comparison_id"]
    assert envelope["input_vector"]["input_vector_sha256"] == single["input_vector"]["input_vector_sha256"]
