"""L0 rule-applicability pack: official examples, as-of law and bounds (A12-A14, A20)."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine.capital_structure import reference_qualification as rq
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure.issuer_state_contracts import (
    FORBIDDEN_PROPERTY_PATTERN,
    Quantity,
    RulePack,
)

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / ra.RULE_APPLICABILITY_PACK_RELPATH
PROPOSAL = "sec_release_33_11418_registered_offering_reform"
CDI_22 = "cdi_116_22_capacity_measured_against_amount_offered"
CDI_23 = "cdi_116_23_concurrent_continuous_offerings"
NASDAQ_D2 = "nasdaq_5635_d_2_twenty_percent_below_minimum_price"


@pytest.fixture(scope="module")
def raw():
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack():
    return ra.load_rule_applicability_pack()


def _inputs(pack, example_id, **changes):
    inputs = copy.deepcopy(dict(pack.reference_example(example_id).inputs))
    inputs.update(changes)
    return inputs


def _reparse(pack, raw_pack):
    return ra.parse_rule_applicability_pack(raw_pack, reference_pack=pack.reference)


def _usd(value):
    return Quantity.known(str(value), "usd")


def _shares(value, basis):
    return Quantity.known(str(value), "shares", share_basis=basis)


def _forbidden_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if FORBIDDEN_PROPERTY_PATTERN.match(str(key)):
                yield key
            yield from _forbidden_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _forbidden_keys(item)


# ---- pack identity and E0 pins ----


def test_pack_loads_and_pins_e0(pack):
    assert pack.schema == ra.RULE_APPLICABILITY_PACK_SCHEMA
    assert pack.version == ra.RULE_APPLICABILITY_PACK_VERSION
    assert pack.task == "L0"
    assert set(pack.acceptance_rows) >= {"A12", "A13", "A14", "A20"}
    assert set(pack.examples) == {e.example_id for e in rq.rule_examples(pack.reference)}
    e0 = ROOT / rq.REFERENCE_PACK_RELPATH
    assert rq.file_digest(e0) == json.loads(PACK_PATH.read_text())["reference_pack"]["sha256_at_qualification"]


def test_stored_span_text_hashes_and_same_as_targets(pack):
    stored = [s for s in pack.spans.values() if s.text is not None]
    aliased = [s for s in pack.spans.values() if s.same_as is not None]
    assert stored and aliased
    for span in aliased:
        target = pack.span(span.same_as)
        assert target.text is not None and span.sha256 == target.sha256
        assert pack.span_text(span.span_id) == target.text


def test_s3_and_f3_instructions_stay_distinct(pack):
    """A13: I.B.6 (S-3) and I.B.5 (F-3) are separate rules with separate text."""
    s3, f3 = pack.rule("form_s3.I.B.6"), pack.rule("form_f3.I.B.5")
    assert (s3.form, s3.instruction) == ("S-3", "I.B.6")
    assert (f3.form, f3.instruction) == ("F-3", "I.B.5")
    assert pack.span("form_s3:I.B.6").sha256 != pack.span("form_f3:I.B.5").sha256
    assert "worldwide" in pack.span_text("form_f3:I.B.5")


# ---- the eight official examples (A13) ----


@pytest.mark.parametrize("example_id", sorted(ra._EVALUATORS))
def test_official_example_reproduces_expected(pack, example_id):
    answer = ra.evaluate_example(pack, example_id)
    assert answer.status in ("answered", "conditional")
    assert answer.answer == pack.reference_example(example_id).expected
    assert not list(_forbidden_keys(answer.as_record()))
    assert {ref.rule_id for ref in answer.authority} == set(pack.example(example_id).rule_ids)


def test_negative_examples_answer_no(pack):
    assert ra.evaluate_example(pack, CDI_22).answer["supplement_permitted"] is False
    resale = ra.evaluate_example(pack, "cdi_116_25_ib3_resale_counts_against_ib6_capacity").answer
    assert resale["ib3_resale_permitted_without_sufficient_ib6_capacity_at_filing"] is False
    im = ra.evaluate_example(pack, "nasdaq_im_5635_3_registration_alone_is_not_a_public_offering").answer
    assert im["registration_alone_sufficient"] is False


def test_f3_instruction_is_not_collapsed_into_s3(pack):
    answer = ra.evaluate_example(pack, CDI_22, _inputs(pack, CDI_22, instruction="F-3 I.B.5"))
    assert answer.status == "not_addressed" and answer.answer is None
    assert any("A13" in note for note in answer.scope_notes)


def test_116_22_measures_amount_offered_not_expected_sales(pack):
    for expected_sales in (True, False, "unknown"):
        answer = ra.evaluate_example(
            pack, CDI_22, _inputs(pack, CDI_22, actual_sales_expected_within_capacity=expected_sales)
        )
        assert answer.answer["supplement_permitted"] is False
    within = ra.evaluate_example(
        pack, CDI_22, _inputs(pack, CDI_22, supplement_amount_exceeds_remaining_one_third_capacity=False)
    )
    assert within.answer["supplement_permitted"] is True


def test_116_21_resale_registration_is_outside_the_position(pack):
    eid = "cdi_116_21_equity_line_is_at_the_market"
    assert ra.evaluate_example(pack, eid, _inputs(pack, eid, registration_mode="resale_offering")).status == "inapplicable"
    assert ra.evaluate_example(pack, eid, _inputs(pack, eid, instrument="convertible_note")).status == "not_addressed"


def test_116_23_concurrent_offering_arithmetic(pack):
    sold_more = ra.evaluate_example(pack, CDI_23, _inputs(pack, CDI_23, sold_to_date_usd=4000000))
    assert sold_more.answer["offerable_total_as_of_june_14_usd"] == 6000000
    assert sold_more.answer["max_june_14_supplement_usd"] == 3500000
    cents = ra.evaluate_example(pack, CDI_23, _inputs(pack, CDI_23, sold_to_date_usd="2500000.50"))
    assert cents.answer["max_june_14_supplement_usd"] == "4999999.50"
    exhausted = ra.evaluate_example(pack, CDI_23, _inputs(pack, CDI_23, sold_to_date_usd=9000000))
    assert exhausted.answer["max_june_14_supplement_usd"] == 0
    assert exhausted.scope_notes


@pytest.mark.parametrize(
    "changes",
    [
        {"still_offered_under_june_7_supplement_usd": 6000000},
        {"sold_to_date_usd": True},
        {"sold_to_date_usd": 2.5},
        {"sold_to_date_usd": -1},
    ],
)
def test_116_23_rejects_inconsistent_amounts(pack, changes):
    with pytest.raises(ra.RuleApplicabilityError):
        ra.evaluate_example(pack, CDI_23, _inputs(pack, CDI_23, **changes))


def test_116_24_exercisability_is_irrelevant(pack):
    eid = "cdi_116_24_warrants_not_exercisable_within_12_months"
    flipped = ra.evaluate_example(pack, eid, _inputs(pack, eid, warrants_exercisable_within_12_months=True))
    assert flipped.answer == {"instruction_2_applies_to_warrant_market_value": True}
    no_warrants = ra.evaluate_example(pack, eid, _inputs(pack, eid, offering_components=["common_stock"]))
    assert no_warrants.status == "inapplicable"


def test_116_25_scope_and_unknowns(pack):
    eid = "cdi_116_25_ib3_resale_counts_against_ib6_capacity"
    assert ra.evaluate_example(pack, eid, _inputs(pack, eid, public_float_below_75m_usd=False)).status == "inapplicable"
    assert ra.evaluate_example(pack, eid, _inputs(pack, eid, same_investors=False)).status == "not_addressed"
    unknown = ra.evaluate_example(pack, eid, _inputs(pack, eid, public_float_below_75m_usd="unknown"))
    assert unknown.status == "withheld" and unknown.answer is None
    assert [u.unknown_id for u in unknown.unknowns] == [f"input:{eid}:public_float_below_75m_usd"]


def test_116_26_is_conditional_staff_position(pack):
    eid = "cdi_116_26_atm_supplement_continues_after_transition_to_baby_shelf"
    answer = ra.evaluate_example(pack, eid)
    assert answer.status == "conditional"
    assert "prospectus_supplement_filed_before_the_10a3_update" in answer.conditions
    staff = [ref for ref in answer.authority if ref.binding_class == "staff_interpretation"]
    assert staff and all(ref.enforceable is False for ref in staff)
    stays_large = ra.evaluate_example(pack, eid, _inputs(pack, eid, public_float_below_75m_at_next_10a3_update=False))
    assert stays_large.status == "inapplicable"


def test_nasdaq_twenty_percent_example_variants(pack):
    def run(**changes):
        return ra.evaluate_example(pack, NASDAQ_D2, _inputs(pack, NASDAQ_D2, **changes))

    assert run(listing_venue="nyse").status == "inapplicable"
    assert run(public_offering_per_im_5635_3=True).status == "inapplicable"
    assert run(public_offering_per_im_5635_3="unknown").status == "withheld"
    assert run(price_relative_to_minimum_price="at_or_above").answer["shareholder_approval_required_before_issuance"] is False
    below = run(issuance_percent_of_common_outstanding_before=15)
    assert below.status == "withheld"
    assert below.unknowns[0].unknown_id.endswith("issuance_percent_of_voting_power_outstanding_before")
    votes = run(issuance_percent_of_common_outstanding_before=15, issuance_percent_of_voting_power_outstanding_before=25)
    assert votes.answer["shareholder_approval_required_before_issuance"] is True
    small = run(issuance_percent_of_common_outstanding_before=15, issuance_percent_of_voting_power_outstanding_before=10)
    assert small.answer["shareholder_approval_required_before_issuance"] is False
    assert all(any("A14" in note for note in a.scope_notes) for a in (votes, small))


def test_registration_never_decides_public_offering(pack):
    """A14: registration alone never makes the offering public, whatever the other factors."""
    eid = "nasdaq_im_5635_3_registration_alone_is_not_a_public_offering"
    for factors in ("unknown", "present", None):
        answer = ra.evaluate_example(pack, eid, _inputs(pack, eid, other_public_offering_factors=factors))
        assert answer.answer == {"registration_alone_sufficient": False, "public_offering_status": "undetermined"}
    unregistered = ra.evaluate_example(pack, eid, _inputs(pack, eid, registered_with_sec_before_closing=False))
    assert unregistered.status == "not_addressed"


def test_inputs_replace_defaults_and_unknown_keys_raise(pack):
    empty = ra.evaluate_example(pack, CDI_23, {})
    assert empty.status == "withheld" and len(empty.unknowns) == 4
    with pytest.raises(ra.RuleApplicabilityError):
        ra.evaluate_example(pack, CDI_23, _inputs(pack, CDI_23, extra_key=1))


# ---- as-of law ----


def test_rule_not_yet_adopted_makes_example_inapplicable(pack):
    answer = ra.evaluate_example(pack, "cdi_116_21_equity_line_is_at_the_market", as_of="2005-01-01")
    assert answer.status == "inapplicable"
    assert any("2008-01-28" in note for note in answer.scope_notes)


def test_unverified_form_text_withholds_the_answer(pack):
    answer = ra.evaluate_example(pack, "cdi_116_21_equity_line_is_at_the_market", as_of="2026-10-13")
    assert answer.status == "withheld" and answer.answer is None
    assert "rule_text:form_s3.I.B.1:2026-10-13" in {u.unknown_id for u in answer.unknowns}


def test_bracketed_and_stale_text_is_conditioned_not_hidden(pack):
    mid = ra.evaluate_example(pack, CDI_22, as_of="2015-06-01")
    assert mid.status == "answered"
    assert any("bracketed" in c for c in mid.conditions)
    today = ra.evaluate_example(pack, CDI_22)
    assert any("requalify" in c for c in today.conditions)
    before_cdi = ra.evaluate_example(pack, CDI_22, as_of="2009-01-01")
    assert before_cdi.status == "withheld"


@pytest.mark.parametrize(
    "as_of, state",
    [("2007-06-01", "not_in_force"), ("2010-01-01", "bracketed"), ("2016-11-21", "verified"), ("2026-10-10", "beyond_window")],
)
def test_rule_401_g_3_states(pack, as_of, state):
    assert ra.rule_status_as_of(pack, "cfr.17.230.401.g.3", as_of).state == state


def test_build_rule_pack_excludes_the_proposal(pack):
    """A12: proposed 33-11418 is never part of the law."""
    rule_pack, unknowns, _, excluded = ra.build_rule_pack(pack, "2026-10-14")
    assert isinstance(rule_pack, RulePack) and not unknowns
    assert excluded == (PROPOSAL,)
    assert {r.binding_class for r in rule_pack.rules} <= {"binding_rule", "staff_interpretation"}
    assert all(PROPOSAL not in r.rule_id for r in rule_pack.rules)
    none, early_unknowns, _, _ = ra.build_rule_pack(pack, "2005-01-01")
    assert none is None and early_unknowns


# ---- tamper resistance ----


def _stored_span_index(raw_pack):
    return next(i for i, s in enumerate(raw_pack["spans"]) if s.get("text"))


def test_tampered_span_text_is_refused(pack, raw):
    bad = copy.deepcopy(raw)
    i = _stored_span_index(bad)
    bad["spans"][i]["text"] = bad["spans"][i]["text"].replace("1", "2", 1)
    with pytest.raises(ra.RuleApplicabilityError):
        _reparse(pack, bad)


def test_tampered_window_digest_is_refused(pack, raw):
    bad = copy.deepcopy(raw)
    bad["rules"][0]["windows"][0]["sha256"] = "0" * 64
    with pytest.raises(ra.RuleApplicabilityError, match="digest mismatch"):
        _reparse(pack, bad)


def test_tampered_example_pin_is_refused(pack, raw):
    bad = copy.deepcopy(raw)
    bad["examples"][0]["reference_digest"] = "0" * 64
    with pytest.raises(ra.RuleApplicabilityError):
        _reparse(pack, bad)


def test_forbidden_property_is_refused(pack, raw):
    bad = copy.deepcopy(raw)
    bad["rules"][0]["capacity"] = "10000000"
    with pytest.raises(ra.RuleApplicabilityError, match="A48"):
        _reparse(pack, bad)


def test_proposal_may_not_enter_as_a_rule(pack, raw):
    bad = copy.deepcopy(raw)
    bad["rules"][0]["binding_class"] = "proposed_reform"
    bad["rules"][0]["enforceable"] = False
    with pytest.raises(ra.RuleApplicabilityError, match="A12"):
        _reparse(pack, bad)


def test_dropping_the_exclusion_is_refused(pack, raw):
    bad = copy.deepcopy(raw)
    bad["excluded"] = []
    with pytest.raises(ra.RuleApplicabilityError, match="33-11418"):
        _reparse(pack, bad)


def test_changed_e0_pack_requires_requalification(pack, raw):
    with pytest.raises(ra.RuleApplicabilityError, match="requalify"):
        ra.parse_rule_applicability_pack(raw, reference_pack=pack.reference, reference_file_sha256="0" * 64)


# ---- I.B.6 / I.B.5 one-third pool (A20) ----


def test_baby_shelf_limit(pack):
    assert ra.baby_shelf_limit(_usd(60000000)).value == "20000000.00"
    assert ra.baby_shelf_limit(_usd("74999999.99")).value == "24999999.99"
    assert ra.baby_shelf_limit(_usd(75000000)).status == "not_applicable"
    assert ra.baby_shelf_limit(Quantity.unknown("usd")).status == "unknown"
    with pytest.raises(ra.RuleApplicabilityError):
        ra.baby_shelf_limit(_shares(60000000, "issued_and_outstanding"))


def _pool(pack, sold, *, sale="2026-10-14", window=("2025-10-15", "2026-10-14"), measured="2026-09-01", form="S-3"):
    return ra.baby_shelf_pool(
        pack,
        public_float=_usd(60000000),
        float_measured_on=measured,
        sold_trailing=sold,
        sold_window=window,
        sale_date=sale,
        form=form,
    )


def test_baby_shelf_pool_headroom_and_overrun(pack):
    slack = _pool(pack, _usd(15000000))
    assert slack.constraint.status == "slack"
    assert (slack.headroom.value, slack.overrun.value) == ("5000000.00", "0")
    over = _pool(pack, _usd(25000000))
    assert over.constraint.status == "binding"
    assert (over.headroom.value, over.overrun.value) == ("0", "5000000.00")
    assert {e.span_id for e in over.constraint.evidence} == {"form_s3:I.B.6", "form_s3:I.B.6.instructions"}
    assert not list(_forbidden_keys(over.as_record()))


def test_baby_shelf_pool_unknowns_never_become_zero(pack):
    unknown_sales = _pool(pack, Quantity.unknown("usd"))
    assert unknown_sales.constraint.status == "unknown" and unknown_sales.headroom.status == "unknown"
    stale_float = _pool(pack, _usd(1), measured="2026-07-01")
    assert stale_float.constraint.bound.status == "unknown"
    no_date = _pool(pack, _usd(1), measured=None)
    assert no_date.constraint.status == "unknown"


def test_baby_shelf_pool_refuses_a_mismatched_window(pack):
    with pytest.raises(ra.RuleApplicabilityError, match="A20"):
        _pool(pack, _usd(1), window=("2025-10-14", "2026-10-14"))


def test_baby_shelf_pool_leap_day_and_f3(pack):
    leap = _pool(pack, _usd(1), sale="2028-02-29", window=("2027-03-01", "2028-02-29"), measured="2028-02-01")
    assert (leap.constraint.window_start, leap.constraint.window_end) == ("2027-03-01", "2028-02-29")
    f3 = _pool(pack, _usd(1), form="F-3")
    assert {e.span_id for e in f3.constraint.evidence} == {"form_f3:I.B.5", "form_f3:I.B.5.instructions"}


def test_baby_shelf_pool_before_adoption_is_refused(pack):
    with pytest.raises(ra.RuleApplicabilityError, match="not in force"):
        _pool(pack, _usd(1), sale="2007-06-01", window=("2006-06-02", "2007-06-01"), measured="2007-05-01")


# ---- Nasdaq 20% Issuance arithmetic (A20) ----


def test_nasdaq_threshold_on_issued_and_outstanding_basis():
    outstanding = _shares(10000001, "issued_and_outstanding")
    under = ra.nasdaq_twenty_percent(
        outstanding=outstanding,
        proposed=_shares(2000000, "scenario_incremental_issuance"),
        price_relative_to_minimum_price="below",
    )
    assert under.threshold.value == "2000001"
    assert under.largest_issuance_below_threshold.value == "2000000"
    assert (under.is_twenty_percent_issuance, under.approval_required) == (False, False)
    at = ra.nasdaq_twenty_percent(
        outstanding=outstanding,
        proposed=_shares(2000001, "scenario_incremental_issuance"),
        price_relative_to_minimum_price="below",
    )
    assert (at.is_twenty_percent_issuance, at.approval_required) == (True, True)
    unknown_price = ra.nasdaq_twenty_percent(
        outstanding=outstanding,
        proposed=_shares(2000001, "scenario_incremental_issuance"),
        price_relative_to_minimum_price="unknown",
    )
    assert unknown_price.approval_required is None
    assert not list(_forbidden_keys(at.as_record()))


@pytest.mark.parametrize(
    "outstanding, proposed",
    [
        (Quantity.known("10000000", "shares", share_basis="assumed_as_converted"), None),
        (Quantity.known("10000000", "usd"), None),
        (None, Quantity.known("1", "shares", share_basis="issued_and_outstanding")),
    ],
)
def test_nasdaq_refuses_incompatible_bases(outstanding, proposed):
    outstanding = outstanding or _shares(10000000, "issued_and_outstanding")
    proposed = proposed or _shares(1, "scenario_incremental_issuance")
    with pytest.raises(ra.RuleApplicabilityError, match="A20"):
        ra.nasdaq_twenty_percent(outstanding=outstanding, proposed=proposed, price_relative_to_minimum_price="below")


def test_unknown_outstanding_never_becomes_a_threshold():
    test = ra.nasdaq_twenty_percent(
        outstanding=Quantity.unknown("shares", share_basis="issued_and_outstanding"),
        proposed=_shares(1, "scenario_incremental_issuance"),
        price_relative_to_minimum_price="below",
    )
    assert test.threshold.status == "unknown" and test.approval_required is None


def test_gap_report_names_open_l1_debts(pack):
    report = ra.gap_report(pack)
    assert set(report["open"]) == {"pre_2016_form_editions"}
    assert all(pack.gaps[g]["owed_by"] == "L1" for g in report["open"])
    assert Decimal(ra.BABY_SHELF_FLOAT_THRESHOLD_USD) == Decimal("75000000")


# ---- L1: Rule 415(a)(1)(x)/(a)(4)/(a)(5)/(a)(6), Rule 462(e) and Section 10(a)(3) ----

NEW_RULE_IDS = (
    "cfr.17.230.415.a.1.x",
    "cfr.17.230.415.a.4",
    "cfr.17.230.415.a.5",
    "cfr.17.230.415.a.6",
    "cfr.17.230.462.e",
    "usc.15.77j.a.3",
)
CFR_RULE_IDS = tuple(rule_id for rule_id in NEW_RULE_IDS if rule_id.startswith("cfr."))
# Release 33-8591 item 30.f/30.g ADD (a)(5) and (a)(6) and item 42 ADDS 462(e);
# item 30.b REVISES (a)(1)(x) and item 30.e REVISES (a)(4), which therefore pre-existed.
ADDED_RULE_IDS = ("cfr.17.230.415.a.5", "cfr.17.230.415.a.6", "cfr.17.230.462.e")
REVISED_RULE_IDS = ("cfr.17.230.415.a.1.x", "cfr.17.230.415.a.4")
RELEASE_DATE = "2005-12-01"   # "EFFECTIVE DATE: December 1, 2005", printed in Release 33-8591
BASE_EDITION = "2016-11-21"   # earliest point-in-time edition the eCFR versioner serves
ECFR_EDITION = "2026-10-09"   # title 17 up_to_date_as_of, re-confirmed by the L1 titles.json retrieval
QUALIFIED_ON = "2026-10-14"   # the eCFR refused full/2026-10-14 with HTTP 404, so there is no point at today
DATES_415 = ("2016-11-21", "2020-06-01", "2020-08-01", "2021-12-09", "2022-01-31", "2024-07-24", "2024-09-23", ECFR_EDITION)
DATES_462 = ("2016-11-21", "2020-06-01", "2020-08-01", ECFR_EDITION)
L1_SOURCE_PREFIXES = ("ecfr_230_415", "ecfr_230_462", "release_33_8591", "usc_15_77j")
BASE_SPAN = {
    "cfr.17.230.415.a.1.x": f"ecfr_230_415/{BASE_EDITION}:a_1_x",
    "cfr.17.230.415.a.4": f"ecfr_230_415/{BASE_EDITION}:a_4",
    "cfr.17.230.415.a.5": f"ecfr_230_415/{BASE_EDITION}:a_5",
    "cfr.17.230.415.a.6": f"ecfr_230_415/{BASE_EDITION}:a_6",
    "cfr.17.230.462.e": f"ecfr_230_462/{BASE_EDITION}:e",
}
RELEASE_SPAN = {
    "cfr.17.230.415.a.1.x": "release_33_8591:rule_415_a_1_x",
    "cfr.17.230.415.a.4": "release_33_8591:rule_415_a_4",
    "cfr.17.230.415.a.5": "release_33_8591:rule_415_a_5",
    "cfr.17.230.415.a.6": "release_33_8591:rule_415_a_6",
    "cfr.17.230.462.e": "release_33_8591:rule_462_e",
}


def _l1_spans(pack):
    return [span for span in pack.spans.values() if span.source_id.startswith(L1_SOURCE_PREFIXES)]


def test_l1_pack_version_is_1_1_0_and_still_parses(pack, raw):
    assert raw["version"] == "capital-structure-rule-applicability/1.2.0"
    assert pack.version == ra.RULE_APPLICABILITY_PACK_VERSION == raw["version"]
    assert pack.task == "L0" and pack.qualified_on == QUALIFIED_ON
    assert isinstance(ra.parse_rule_applicability_pack(raw, reference_pack=pack.reference), ra.RuleApplicabilityPack)


def test_l1_proposal_exclusion_survives(pack, raw):
    assert [item["source_id"] for item in raw["excluded"]] == [PROPOSAL]
    assert PROPOSAL not in pack.sources and PROPOSAL not in pack.rules
    for source_id in pack.sources:
        assert not source_id.startswith(L1_SOURCE_PREFIXES) or source_id != PROPOSAL
    _, _, _, excluded = ra.build_rule_pack(pack, QUALIFIED_ON)
    assert excluded == (PROPOSAL,)


@pytest.mark.parametrize("rule_id", NEW_RULE_IDS)
def test_l1_rule_shape(pack, rule_id):
    rule = pack.rule(rule_id)
    assert rule.binding_class == "binding_rule" and rule.enforceable is True
    assert (rule.form, rule.instruction, rule.interpretation_date) == (None, None, None)
    assert rule.reference_span_labels == () and rule.required_issuer_facts == ()
    assert rule.windows and rule.citation and rule.note


def test_l1_rule_415_a_1_x_states(pack):
    rule_id = "cfr.17.230.415.a.1.x"
    assert ra.rule_status_as_of(pack, rule_id, ECFR_EDITION).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, RELEASE_DATE).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2010-06-01").state == "bracketed"
    assert ra.rule_status_as_of(pack, rule_id, "2005-11-30").state == "withheld"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-10").state == "beyond_window"
    before = ra.rule_status_as_of(pack, rule_id, "2020-07-31")
    after = ra.rule_status_as_of(pack, rule_id, "2020-08-01")
    assert (before.state, after.state) == ("verified", "verified")
    assert before.window.span_id == BASE_SPAN[rule_id] != after.window.span_id


def test_l1_rule_415_a_4_states(pack):
    rule_id = "cfr.17.230.415.a.4"
    assert ra.rule_status_as_of(pack, rule_id, ECFR_EDITION).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, RELEASE_DATE).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2016-11-20").state == "bracketed"
    assert ra.rule_status_as_of(pack, rule_id, "2005-11-30").state == "withheld"
    assert ra.rule_status_as_of(pack, rule_id, "1999-01-01").state == "withheld"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-14").state == "beyond_window"


def test_l1_rule_415_a_5_states(pack):
    rule_id = "cfr.17.230.415.a.5"
    assert ra.rule_status_as_of(pack, rule_id, ECFR_EDITION).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, RELEASE_DATE).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2008-02-29").state == "bracketed"
    assert ra.rule_status_as_of(pack, rule_id, "2005-11-30").state == "not_in_force"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-10").state == "beyond_window"
    assert "three years" in pack.span_text(BASE_SPAN[rule_id])


def test_l1_rule_415_a_6_states(pack):
    rule_id = "cfr.17.230.415.a.6"
    assert ra.rule_status_as_of(pack, rule_id, ECFR_EDITION).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, RELEASE_DATE).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2012-05-22").state == "bracketed"
    assert ra.rule_status_as_of(pack, rule_id, "2005-11-30").state == "not_in_force"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-10").state == "beyond_window"
    before = ra.rule_status_as_of(pack, rule_id, "2022-01-30")
    after = ra.rule_status_as_of(pack, rule_id, "2022-01-31")
    assert before.window.span_id == BASE_SPAN[rule_id] != after.window.span_id


def test_l1_rule_462_e_states(pack):
    rule_id = "cfr.17.230.462.e"
    assert ra.rule_status_as_of(pack, rule_id, ECFR_EDITION).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, RELEASE_DATE).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2011-11-11").state == "bracketed"
    assert ra.rule_status_as_of(pack, rule_id, "2005-11-30").state == "not_in_force"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-14").state == "beyond_window"
    assert "effective upon filing with the Commission" in pack.span_text(BASE_SPAN[rule_id])


def test_l1_section_10_a_3_states(pack):
    rule_id = "usc.15.77j.a.3"
    assert ra.rule_status_as_of(pack, rule_id, QUALIFIED_ON).state == "verified"
    assert ra.rule_status_as_of(pack, rule_id, "2026-10-15").state == "beyond_window"
    for as_of in ("2005-11-30", RELEASE_DATE, BASE_EDITION, ECFR_EDITION, "2026-10-13"):
        status = ra.rule_status_as_of(pack, rule_id, as_of)
        assert status.state == "withheld"
        assert "before its first qualified window" in status.condition
    text = pack.span_text("usc_15_77j:a_3")
    assert text.startswith("(3) notwithstanding the provisions of paragraphs (1) and (2) of this subsection")
    assert "more than nine months after the effective date" in text
    assert "not more than sixteen months prior to such use" in text
    source = pack.sources["usc_15_77j_2024"]
    assert (source["source_class"], source["enforceable"]) == ("binding_rule", True)
    assert source["edition_label"] == "United States Code, 2024 Edition"


@pytest.mark.parametrize("rule_id", NEW_RULE_IDS)
def test_l1_windows_are_ordered_and_pinned_to_their_span(pack, rule_id):
    rule = pack.rule(rule_id)
    assert [window.start for window in rule.windows] == sorted(window.start for window in rule.windows)
    for window in rule.windows:
        assert window.start <= window.end
        assert window.span_id in rule.span_ids
        span = pack.span(window.span_id)
        assert window.sha256 == span.sha256 == ra._sha(pack.span_text(window.span_id))
    if rule.before_first_window == "not_in_force":
        assert rule.not_in_force_before == rule.windows[0].start
    else:
        assert rule.before_first_window == "withheld" and rule.not_in_force_before is None


@pytest.mark.parametrize("rule_id", CFR_RULE_IDS)
def test_l1_release_bracket_is_earned_by_a_shared_normalized_digest(pack, rule_id):
    point, bracket = pack.rule(rule_id).windows[:2]
    assert (point.kind, point.start, point.end) == ("point", RELEASE_DATE, RELEASE_DATE)
    assert (bracket.kind, bracket.start, bracket.end) == ("bracket", RELEASE_DATE, BASE_EDITION)
    assert point.span_id == bracket.span_id == RELEASE_SPAN[rule_id]
    adopted = pack.span_text(RELEASE_SPAN[rule_id])
    earliest = pack.span_text(BASE_SPAN[rule_id])
    assert ra.normalized_digest(adopted) == ra.normalized_digest(earliest)
    assert adopted.startswith(("(x)", "(4)", "(5)", "(6)", "(e)"))


def test_l1_release_text_separates_revision_from_addition(pack):
    amend_415 = pack.span_text("release_33_8591:amend_230_415")
    amend_462 = pack.span_text("release_33_8591:amend_230_462")
    assert amend_415.startswith("30. Amend \u00a7230.415 as follows:")
    assert "b. Revise paragraph (a)(1)(x)" in amend_415
    assert "e. Revise paragraph (a)(4) including the undesignated paragraph" in amend_415
    assert "f. Add paragraph (a)(5); and g. Add paragraph (a)(6)" in amend_415
    assert amend_462 == "42. Amend \u00a7230.462 by adding paragraphs (e) and (f) to read as follows:"
    assert pack.span_text("release_33_8591:effective_date") == "EFFECTIVE DATE: December 1, 2005"
    for rule_id in ADDED_RULE_IDS:
        rule = pack.rule(rule_id)
        assert (rule.before_first_window, rule.not_in_force_before) == ("not_in_force", RELEASE_DATE)
    for rule_id in REVISED_RULE_IDS:
        rule = pack.rule(rule_id)
        assert (rule.before_first_window, rule.not_in_force_before) == ("withheld", None)
    release = pack.sources["release_33_8591"]["release"]
    assert (release["status"], release["effective_date"]) == ("final", RELEASE_DATE)
    assert release["file_number"] == "S7-38-04" and release["rin"] == "3235-AI11"
    assert "33-8591" in release["releases"]


def test_l1_span_digests_recompute_from_the_retrieved_bytes(pack):
    spans = _l1_spans(pack)
    stored = [span for span in spans if span.text is not None]
    aliased = [span for span in spans if span.same_as is not None]
    assert (len(stored), len(aliased)) == (17, 31)
    for span in spans:
        text = pack.span_text(span.span_id)
        assert len(text) == span.chars
        assert ra._sha(text) == span.sha256
        assert ra.normalized_digest(text) == span.normalized_sha256
    for span in aliased:
        target = pack.span(span.same_as)
        assert target.text is not None
        assert (span.chars, span.sha256, span.normalized_sha256) == (
            target.chars, target.sha256, target.normalized_sha256
        )


def test_l1_every_served_edition_has_its_own_span(pack):
    for edition in DATES_415:
        for provision in ("a_1_x", "a_4", "a_5", "a_6"):
            assert pack.span_text(f"ecfr_230_415/{edition}:{provision}")
    for edition in DATES_462:
        assert pack.span_text(f"ecfr_230_462/{edition}:e")
    old, new = pack.span(f"ecfr_230_415/{BASE_EDITION}:a_1_x"), pack.span("ecfr_230_415/2020-08-01:a_1_x")
    assert (old.sha256, old.normalized_sha256) != (new.sha256, new.normalized_sha256)
    assert {pack.span(f"ecfr_230_415/{edition}:a_4").sha256 for edition in DATES_415} == {
        pack.span(f"ecfr_230_415/{BASE_EDITION}:a_4").sha256}
    assert len({pack.span(f"ecfr_230_415/{edition}:a_5").sha256 for edition in DATES_415}) == 1
    assert len({pack.span(f"ecfr_230_462/{edition}:e").sha256 for edition in DATES_462}) == 1
    assert {
        pack.span(f"ecfr_230_415/{edition}:a_6").sha256 for edition in DATES_415
    } == {pack.span(f"ecfr_230_415/{BASE_EDITION}:a_6").sha256, pack.span("ecfr_230_415/2022-01-31:a_6").sha256}


def test_l1_version_index_windows_split_only_where_the_text_changed(pack):
    assert [(w.kind, w.start, w.end) for w in pack.rule("cfr.17.230.415.a.1.x").windows[2:]] == [
        ("version_index", BASE_EDITION, "2020-07-31"), ("version_index", "2020-08-01", ECFR_EDITION)]
    assert [(w.kind, w.start, w.end) for w in pack.rule("cfr.17.230.415.a.6").windows[2:]] == [
        ("version_index", BASE_EDITION, "2022-01-30"), ("version_index", "2022-01-31", ECFR_EDITION)]
    for rule_id in ("cfr.17.230.415.a.4", "cfr.17.230.415.a.5", "cfr.17.230.462.e"):
        assert [(w.kind, w.start, w.end) for w in pack.rule(rule_id).windows[2:]] == [
            ("version_index", BASE_EDITION, ECFR_EDITION)]


def test_l1_refused_todays_edition_so_there_is_no_point_at_today(pack, raw):
    refused = [row for row in raw["request_policy"]["l1_requests"]
               if row["http_status"] == 404 and "/full/2026-10-14/" in row["url"]]
    assert len(refused) == 2
    for rule_id in CFR_RULE_IDS:
        rule = pack.rule(rule_id)
        assert max(window.end for window in rule.windows) == ECFR_EDITION
        assert not any(window.kind == "point" and window.start == QUALIFIED_ON for window in rule.windows)
        assert ra.rule_status_as_of(pack, rule_id, QUALIFIED_ON).state == "beyond_window"


def test_l1_request_log_covers_every_request_including_refusals(raw):
    policy = raw["request_policy"]
    rows = policy["l1_requests"]
    fields = {"url", "http_status", "retrieved_at", "wire_bytes", "bytes",
              "content_encoding", "content_type", "sha256"}
    assert len(rows) == 23 and all(fields <= set(row) for row in rows)
    assert sorted(row["http_status"] for row in rows if row["http_status"] != 200) == [301, 404, 404]
    assert (policy["requests_made"], policy["refused_requests"]) == (37 + 23, 15 + 3)
    assert all(row["url"].startswith(("https://www.ecfr.gov/", "https://www.sec.gov/",
                                     "https://www.govinfo.gov/")) for row in rows)
    ecfr = [row for row in rows if "ecfr.gov" in row["url"]]
    assert ecfr and all(row["content_encoding"] == "gzip" for row in ecfr)
    assert all(row["wire_bytes"] < row["bytes"] for row in ecfr)


def test_l1_closes_the_rule_415_and_section_10_a_3_gap(pack):
    report = ra.gap_report(pack)
    assert report["closed"] == ["rule_415_and_section_10_a_3_text"]
    gap = pack.gaps["rule_415_and_section_10_a_3_text"]
    assert (gap["status"], gap["closed_by"], gap["owed_by"]) == ("closed", "L1", "L1")
    assert all(pack.rule(rule_id).windows for rule_id in NEW_RULE_IDS)


def test_l1_pre_2016_form_edition_gap_stays_open_with_its_attempts(pack):
    gap = pack.gaps["pre_2016_form_editions"]
    assert (gap["status"], gap["owed_by"]) == ("open", "L1") and "closed_by" not in gap
    attempts = gap["attempts"]
    assert [attempt["url"] for attempt in attempts] == [
        "https://www.sec.gov/about/forms/forms-3.pdf",
        "https://www.sec.gov/about/forms/formf-3.pdf",
        "https://www.sec.gov/about/forms",
        "https://www.sec.gov/about/forms/",
    ]
    for attempt in attempts:
        assert {"url", "http_status", "retrieved_at", "outcome"} <= set(attempt)
    assert attempts[0]["sha256"] == pack.sources["form_s3_pdf"]["sha256"]
    assert attempts[1]["sha256"] == pack.sources["form_f3_pdf"]["sha256"]
    assert attempts[2]["http_status"] == 301 and attempts[3]["http_status"] == 200
    assert "Directory Browsing Not Allowed" in attempts[3]["outcome"]
    form_labels = [source["edition_label"] for source in pack.sources.values()
                   if source.get("edition_label") and "SEC " in source["edition_label"]]
    assert form_labels == [pack.sources["form_s3_pdf"]["edition_label"],
                           pack.sources["form_f3_pdf"]["edition_label"]]
    assert all("(02-25)" in label for label in form_labels)


def test_l1_rules_enter_the_rule_pack_without_guessing(pack):
    rule_pack, unknowns, conditions, excluded = ra.build_rule_pack(pack, QUALIFIED_ON)
    assert isinstance(rule_pack, RulePack) and not unknowns and excluded == (PROPOSAL,)
    assert set(NEW_RULE_IDS) <= {ref.rule_id for ref in rule_pack.rules}
    assert sum("requalify" in condition for condition in conditions) >= len(CFR_RULE_IDS)
    _, early_unknowns, _, _ = ra.build_rule_pack(pack, "2005-01-01")
    affects = {unknown.affects[0] for unknown in early_unknowns}
    assert set(REVISED_RULE_IDS) | {"usc.15.77j.a.3"} <= affects
    assert not set(ADDED_RULE_IDS) & affects


def test_l1_release_page_break_inside_415_a_5_is_disclosed(raw, pack):
    # Review finding (O2, lane cs-v2-l1b-20261014T1444Z): the release PDF breaks (a)(5) across a page,
    # and pdftotext prints the folio "370" there. The span omits the folio; the omission must be on record.
    noted = [span["span_id"] for span in raw["spans"] if "page_furniture_removed" in span]
    assert noted == ["release_33_8591:rule_415_a_5"]
    text = pack.span_text("release_33_8591:rule_415_a_5")
    assert "370" not in text
    assert "registration statement: (A) Securities covered by the prior registration statement" in text
    assert ra.normalized_digest(text) == pack.span("ecfr_230_415/2016-11-21:a_5").normalized_sha256
