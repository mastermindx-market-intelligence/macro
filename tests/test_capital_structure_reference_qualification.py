"""E0 reference qualification pack: masterplan §15 rows A07 and A09.

A07: gold references bind exact issuer/security, document, span, date and
allowed source; old ticker/sector labels are not silently reused.
A09: LLM-proposed spans or interpretations cannot mint canonical facts without
the accepted extraction/adjudication procedure.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from engine.capital_structure import reference_qualification as rq
from engine.capital_structure.document_terms import REGISTRATION_FEE_FORMS
from engine.capital_structure.legacy import LEGACY_FORMS

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / rq.REFERENCE_PACK_RELPATH


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack() -> rq.ReferencePack:
    return rq.load_reference_pack(PACK_PATH)


def test_pack_is_frozen_to_its_schema_and_version(pack):
    assert pack.schema == rq.REFERENCE_PACK_SCHEMA == "capital_structure.reference_pack.v1"
    assert pack.version == rq.REFERENCE_PACK_VERSION == "capital-structure-reference-qualification/1.1.0"
    assert pack.task == "G0-S"
    assert set(pack.acceptance_rows) == {"A07", "A09", "A13", "A33", "A42"}
    assert pack.masterplan["commit"] == "93c82c9058eed8c39e34046753c5274ad5d80eb7"
    assert pack.qualified_on == "2026-10-19"


# --------------------------------------------------------------------------- gold (A07)

def test_every_gold_fixture_hash_matches_the_repository_bytes(pack):
    assert rq.verify_gold_fixtures(pack, ROOT) == {}


def test_every_gold_case_names_an_existing_consuming_test(pack):
    for gold in pack.gold_cases:
        assert gold.path.startswith(rq.GOLD_FIXTURE_PREFIX)
        assert (ROOT / gold.path).is_file()
        for consumer in gold.consumers:
            assert (ROOT / "tests" / consumer).is_file(), (gold.gold_id, consumer)
        for expectation in gold.expectations:
            test_file = expectation["test"].split("::")[0]
            assert (ROOT / test_file).is_file(), (gold.gold_id, test_file)
            assert expectation["claim"].strip()


def test_real_edgar_gold_binds_exact_accession_cik_form_and_filing_date(pack):
    real = [g for g in pack.gold_cases if g.provenance == "real_edgar"]
    assert len(real) == 2
    for gold in real:
        assert gold.allowed_source == "sec_edgar_public_filing"
        assert re.fullmatch(r"\d{10}-\d{2}-\d{6}", gold.details["accession"])
        assert re.fullmatch(r"\d{10}", gold.details["cik"])
        assert gold.details["form"] in {"S-1/A", "S-3ASR"}
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", gold.details["filed"])
    multi = next(g for g in real if g.details["form"] == "S-3ASR")
    assert len(multi.details["co_registrant_ciks"]) == 6
    assert multi.details["cik"] in multi.details["co_registrant_ciks"]


def test_share_count_gold_pins_a_json_pointer_and_distinguishes_float_from_shares(pack):
    gold = next(g for g in pack.gold_cases if g.gold_id == "gold:share_count_truth:companyfacts_0000320193")
    claim = gold.expectations[0]["claim"]
    assert "/facts/us-gaap/CommonStockSharesOutstanding/units/shares/0" in claim
    assert "150000000 shares" in claim
    assert "2580000000000 USD" in claim
    assert "ambiguous" in claim
    assert gold.details["cik"] == "0000320193"


def test_tampered_gold_hash_is_reported_not_silently_accepted(pack):
    tampered = copy.deepcopy(json.loads(PACK_PATH.read_text(encoding="utf-8")))
    tampered["gold_cases"][0]["sha256"] = "0" * 64
    bad = rq.parse_reference_pack(tampered)
    problems = rq.verify_gold_fixtures(bad, ROOT)
    assert list(problems) == [bad.gold_cases[0].gold_id]
    assert problems[bad.gold_cases[0].gold_id].startswith("sha256 mismatch: ")


# --------------------------------------------------------------------------- identities (A07)

def test_every_archetype_identity_binds_cik_and_two_sec_registry_hashes(pack):
    # G0-S appends EDRY and RPID after the six E0 archetypes; QNCX drifted to
    # IRulya Therapeutics Inc. in the 2026-10-19 requalification and is pinned
    # by the G0 tests, so the E0-pinned fields below cover the five archetypes
    # whose labels and tickers did not change.
    assert [i.archetype for i in pack.identities[:6]] == ["AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL"]
    for archetype in ("AIR", "CLNN", "WHK", "LPTH", "EDBL"):
        identity = rq.identity_for(pack, archetype)
        assert re.fullmatch(r"\d{10}", identity.cik)
        assert identity.issuer_id == f"sec:cik:{identity.cik}"
        assert identity.ticker == identity.archetype
        assert identity.ticker_as_of == "2026-10-13"
        assert set(identity.source_ids) == {"sec_company_tickers", f"sec_submissions_cik_{identity.cik}"}
        for sid in identity.source_ids:
            source = pack.source(sid)
            assert source.source_class == "identity_registry"
            assert source.qualification == "qualified"
            assert re.fullmatch(r"[0-9a-f]{64}", source.sha256)
            assert source.retrieved_at.startswith("2026-10-13T")
        assert rq.normalize_label(identity.registry_name) == rq.normalize_label(identity.submissions_name) \
            or identity.registry_name.casefold().startswith(identity.submissions_name.casefold()[:10])


def test_whk_label_drift_is_recorded_and_the_old_label_is_not_reused(pack):
    whk = rq.identity_for(pack, "WHK")
    assert whk.label_drift is True
    assert whk.prior_label == "WhiteHawk Income Corp"
    assert whk.registry_name == "WhiteHawk Minerals Corp."
    assert whk.current_label != whk.prior_label
    former = {n["name"] for n in whk.former_names}
    assert "WhiteHawk Income Corp" in former
    assert any(n["to"] == "2026-06-09" for n in whk.former_names)
    assert "former" in whk.reason.casefold()
    assert whk.case_supply == "unsupplied"
    assert whk.replacement_owed is True
    assert whk.replacement is None  # preserved old witness; replacement not guessed
    assert "no S-3-family registration" in whk.case_supply_reason
    assert whk.prior_reference["section"] == "§16.4"


def test_non_drifting_identities_keep_their_prior_labels(pack):
    # QNCX left this tuple: the 2026-10-19 requalification recorded its rename
    # to IRulya Therapeutics Inc. as label drift (pinned by the G0 tests).
    for arch in ("AIR", "CLNN", "LPTH", "EDBL"):
        identity = rq.identity_for(pack, arch)
        assert identity.label_drift is False, arch
        assert rq.normalize_label(identity.registry_name).startswith(rq.normalize_label(identity.prior_label))
        assert identity.case_supply == "supplied"
        assert identity.replacement_owed is False
        assert identity.details["latest_in_policy_anchor"], arch


def test_identity_drift_flag_cannot_disagree_with_the_registry_name(raw):
    tampered = copy.deepcopy(raw)
    whk = next(i for i in tampered["identities"] if i["archetype"] == "WHK")
    whk["label_drift"] = False
    with pytest.raises(rq.ReferencePackError, match="label_drift flag disagrees"):
        rq.parse_reference_pack(tampered)


def test_unsupplied_archetype_cannot_carry_a_guessed_replacement(raw):
    tampered = copy.deepcopy(raw)
    whk = next(i for i in tampered["identities"] if i["archetype"] == "WHK")
    whk["replacement"] = {"ticker": "XYZ", "note": "looks similar"}
    with pytest.raises(rq.ReferencePackError, match="may not be guessed"):
        rq.parse_reference_pack(tampered)


# --------------------------------------------------------------------------- sources and spans (A07/A09)

def test_every_span_digest_matches_its_exact_text(pack):
    seen = set()
    for source in pack.sources:
        for span in source.spans:
            assert span.sha256 == rq.span_digest(span.text)
            assert span.chars == len(span.text)
            assert span.label not in seen
            seen.add(span.label)
    assert len(seen) == 13


def test_cdi_section_116_spans_are_exact_dated_staff_interpretations(pack):
    cdi = pack.source("sec_cdi_securities_act_forms")
    assert cdi.source_class == "staff_interpretation"
    assert cdi.enforceable is False
    assert cdi.edition_date == "2026-09-25"
    assert cdi.rights == "us_government_work_public_domain"
    dates = {s.details["question"]: s.interpretation_date for s in cdi.spans}
    assert dates == {"116.21": "2008-11-26", "116.22": "2010-08-11", "116.23": "2010-08-11",
                     "116.24": "2013-05-16", "116.25": "2016-11-02", "116.26": "2026-03-19"}
    q23 = cdi.span("cdi_securities_act_forms_q116_23").text
    assert "$10 million" in q23 and "$7.5 million" in q23 and "$5 million" in q23
    q26 = cdi.span("cdi_securities_act_forms_q116_26").text
    assert "I.B.6" in q26 and "10(a)(3)" in q26
    update = pack.source("sec_cdi_update_2026_03_19")
    assert update.edition_date == "2026-03-19"


def test_nasdaq_rule_keeps_the_refused_fetch_receipt_beside_the_browser_qualification(pack):
    nasdaq = pack.source("nasdaq_rule_5600_series")
    assert nasdaq.source_class == "exchange_rule"
    assert nasdaq.qualification == "browser_qualified"
    assert nasdaq.enforceable is True
    assert nasdaq.rights == "excerpt_limited"
    assert nasdaq.details["fetch_receipt"]["http_status"] == 403
    assert re.fullmatch(r"[0-9a-f]{64}", nasdaq.details["fetch_receipt"]["sha256"])
    rendered = nasdaq.details["rendered_receipt"]
    assert nasdaq.sha256 == rendered["page_text_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", rendered["section_5635_sha256"])
    assert rendered["section_5635_chars"] == 45650
    for span in nasdaq.spans:
        assert span.chars <= rq.EXCERPT_CAP_CHARS
    labels = {s.label for s in nasdaq.spans}
    assert {"nasdaq_5615_a_3_A_fpi_home_country_practice", "nasdaq_5615_a_3_B_i_annual_report_disclosure",
            "nasdaq_5635_d_1_A_minimum_price", "nasdaq_5635_d_1_B_twenty_percent_issuance",
            "nasdaq_5635_d_2_approval_trigger", "nasdaq_im_5635_3_registration_alone_not_public_offering",
            "nasdaq_5635_e_1_outstanding_shares_basis"} == labels
    assert pack.source_policy["http_403_is_never_missing_index_evidence"] is True


def test_excerpt_cap_is_enforced_for_rights_limited_sources(raw):
    tampered = copy.deepcopy(raw)
    nasdaq = next(s for s in tampered["sources"] if s["source_id"] == "nasdaq_rule_5600_series")
    text = "x" * (rq.EXCERPT_CAP_CHARS + 1)
    nasdaq["spans"].append({"label": "too_long", "text": text, "chars": len(text),
                            "sha256": rq.span_digest(text), "interpretation_date": None})
    with pytest.raises(rq.ReferencePackError, match="excerpt cap"):
        rq.parse_reference_pack(tampered)


def test_span_text_cannot_change_without_its_digest(raw):
    tampered = copy.deepcopy(raw)
    cdi = next(s for s in tampered["sources"] if s["source_id"] == "sec_cdi_securities_act_forms")
    cdi["spans"][0]["text"] = cdi["spans"][0]["text"] + " (model paraphrase)"
    with pytest.raises(rq.ReferencePackError, match="chars does not match|sha256 does not match"):
        rq.parse_reference_pack(tampered)


def test_release_33_11418_is_proposed_and_never_enforceable(pack):
    reform = pack.source("sec_release_33_11418_registered_offering_reform")
    assert reform.source_class == "proposed_reform"
    assert reform.enforceable is False
    assert reform.details["status"] == "proposed"
    assert reform.details["final_rule_evidence"] is None
    assert "33-11418" in reform.details["release_numbers"]
    assert reform.details["file_number"] == "S7-2026-17"
    assert reform.details["comments_due"] == "2026-07-27"
    assert reform.source_id not in {s.source_id for s in rq.enforceable_sources(pack)}
    assert reform.source_id not in {s.source_id for s in rq.rule_sources(pack)}
    assert rq.rule_examples(pack, reform.source_id) == ()
    index = pack.source("sec_rulemaking_activity_2026")
    assert "Proposed Rule" in index.reason


def test_a_proposed_reform_cannot_be_flipped_to_enforceable(raw):
    tampered = copy.deepcopy(raw)
    reform = next(s for s in tampered["sources"] if s["source_class"] == "proposed_reform")
    reform["enforceable"] = True
    with pytest.raises(rq.ReferencePackError, match="can never be enforceable"):
        rq.parse_reference_pack(tampered)
    tampered = copy.deepcopy(raw)
    reform = next(s for s in tampered["sources"] if s["source_class"] == "proposed_reform")
    reform["source_class"] = "binding_rule"
    reform["enforceable"] = True
    tampered["rule_examples"].append({
        "example_id": "reform_as_law", "source_id": reform["source_id"], "span_label": "none",
        "interpretation_date": "2026-05-19", "negative": False, "rule_refs": ["33-11418"],
        "inputs": {"x": 1}, "expected": {"y": 2}})
    with pytest.raises(rq.ReferencePackError, match="is not in"):
        rq.parse_reference_pack(tampered)


def test_enforceable_sources_are_only_the_exchange_rule_today(pack):
    assert [s.source_id for s in rq.enforceable_sources(pack)] == ["nasdaq_rule_5600_series"]
    rule_ids = {s.source_id for s in rq.rule_sources(pack)}
    assert rule_ids == {"nasdaq_rule_5600_series", "sec_cdi_securities_act_forms", "sec_cdi_update_2026_03_19"}
    # foreign_issuer_f3_witness and held_out_pattern_witness were closed by
    # G0-S and moved to the pack's closed_gaps; whk_replacement_issuer stays
    # open with its failure summary.
    assert {g["gap_id"] for g in pack.gaps} >= {"binding_form_instruction_text", "whk_replacement_issuer"}
    for gap in pack.gaps:
        assert gap["owed_by"]


# --------------------------------------------------------------------------- rule examples (A09 / §6)

def test_rule_examples_bind_a_qualified_span_and_an_interpretation_date(pack):
    assert len(pack.rule_examples) == 8
    for example in pack.rule_examples:
        source = pack.source(example.source_id)
        assert source.is_rule_authority
        span = source.span(example.span_label)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", example.interpretation_date)
        if span.interpretation_date is not None:
            assert span.interpretation_date == example.interpretation_date
        assert example.rule_refs and example.inputs and example.expected
    assert sum(1 for e in pack.rule_examples if e.negative) == 3


def test_cdi_116_23_official_numeric_example_is_preserved_as_a_rule_test(pack):
    example = next(e for e in pack.rule_examples if e.example_id == "cdi_116_23_concurrent_continuous_offerings")
    limit = example.inputs["one_third_limit_usd"]
    sold = example.inputs["sold_to_date_usd"]
    still_offered = example.inputs["still_offered_under_june_7_supplement_usd"]
    assert (limit, sold, still_offered) == (10_000_000, 2_500_000, 2_500_000)
    assert example.expected["offerable_total_as_of_june_14_usd"] == limit - sold == 7_500_000
    assert example.expected["max_june_14_supplement_usd"] == limit - sold - still_offered == 5_000_000
    assert example.interpretation_date == "2010-08-11"


def test_cdi_116_26_continuing_atm_is_a_dated_staff_position_not_a_rule(pack):
    example = next(e for e in pack.rule_examples if e.example_id.startswith("cdi_116_26"))
    assert example.interpretation_date == "2026-03-19"
    assert example.expected["authority_kind"] == "staff_position_not_rule"
    assert example.expected["staff_objects_to_continuing_full_supplement_amount"] is False
    assert example.inputs["supplement_filed_under"] == "S-3 I.B.1"
    assert example.inputs["remains_s3_eligible_under"] == "S-3 I.B.6"


def test_s3_and_f3_instruction_numbering_is_not_assumed_identical(pack):
    example = next(e for e in pack.rule_examples if e.example_id.startswith("cdi_116_21"))
    assert example.expected["instruction_numbering_differs_between_s3_and_f3"] is True
    assert "F-3 I.B.5" in example.expected["eligible_instructions"]
    assert "S-3 I.B.6" in example.expected["eligible_instructions"]


def test_nasdaq_examples_require_transaction_context_and_reject_registration_alone(pack):
    approval = next(e for e in pack.rule_examples if e.example_id == "nasdaq_5635_d_2_twenty_percent_below_minimum_price")
    assert approval.expected["shareholder_approval_required_before_issuance"] is True
    assert set(approval.expected["required_issuer_facts"]) >= {"transaction_type", "price", "quantity", "voting_power"}
    registration = next(e for e in pack.rule_examples if e.example_id.startswith("nasdaq_im_5635_3"))
    assert registration.negative is True
    assert registration.expected["registration_alone_sufficient"] is False
    assert registration.expected["public_offering_status"] == "undetermined"


# --------------------------------------------------------------------------- source policy, rights, budget (§7)

def test_source_policy_matches_the_engine_form_constants(pack):
    policy = pack.source_policy
    assert policy["legacy_forms"] == sorted(LEGACY_FORMS)
    assert policy["registration_fee_forms"] == sorted(REGISTRATION_FEE_FORMS)
    assert set(policy["in_policy_anchor_forms"]) <= REGISTRATION_FEE_FORMS
    out = set(policy["out_of_policy_forms"])
    assert out >= {"S-8", "S-4", "F-4", "N-2", "S-11", "F-6"}
    assert not (out & LEGACY_FORMS)
    assert not (out & REGISTRATION_FEE_FORMS)
    assert policy["contract_doc"] == "docs/CAPITAL_STRUCTURE_INTELLIGENCE_CONTRACT.md"
    assert (ROOT / policy["contract_doc"]).is_file()


def test_request_reserves_and_collector_are_untouched(pack):
    reserves = pack.source_policy["request_class_reserves"]
    assert reserves == {"LIVE_TAIL": 500, "RECOVERY": 20, "HISTORICAL_BACKFILL": 20, "global_ceiling": 540}
    assert pack.source_policy["reserves_changed_by_e0"] is False
    assert pack.source_policy["collector_added_by_e0"] is False
    fair = pack.source("sec_developer_resources_fair_access").details["fair_access"]
    assert fair == {"max_requests_per_second": 10, "declared_user_agent_required": True}
    assert pack.request_policy["max_requests_per_second"] <= fair["max_requests_per_second"]
    assert pack.request_policy["user_agent"].startswith("MastermindMarketIntelligence-ResearchSeat/")
    assert pack.request_policy["requests_made"] >= len(pack.sources)
    assert pack.requalification_procedure["steps"]


def test_reserve_edits_and_new_collectors_are_refused_by_the_pack(raw):
    tampered = copy.deepcopy(raw)
    tampered["source_policy"]["collector_added_by_e0"] = True
    with pytest.raises(rq.ReferencePackError, match="may not add a collector"):
        rq.parse_reference_pack(tampered)


def test_rights_keep_public_domain_text_separate_from_capped_excerpts(pack):
    rights = pack.rights
    assert rights["us_government_work_public_domain"]["full_text_spans_allowed"] is True
    assert rights["excerpt_limited"]["full_text_spans_allowed"] is False
    assert rights["excerpt_limited"]["excerpt_cap_chars"] == rq.EXCERPT_CAP_CHARS
    assert rights["sec_edgar_public_filing"]["personal_data_redaction_required"] is True
    assert rights["contains_personal_data"] is False
    for source in pack.sources:
        assert source.rights in rights


# --------------------------------------------------------------------------- fact origins (A09)

def test_only_canonical_extraction_and_adjudicated_gold_may_mint_facts(pack):
    assert pack.fact_origins == {
        "canonical_extraction": True, "adjudicated_gold": True,
        "llm_proposed_span": False, "llm_interpretation": False, "issuer_assertion": False, "model_prose": False,
    }
    for origin in rq.NON_CANONICAL_FACT_ORIGINS:
        assert rq.fact_origin_is_canonical(origin) is False
    for origin in rq.CANONICAL_FACT_ORIGINS:
        assert rq.fact_origin_is_canonical(origin) is True


def test_llm_origins_cannot_be_promoted_in_the_pack(raw):
    tampered = copy.deepcopy(raw)
    tampered["fact_origins"]["llm_interpretation"] = True
    with pytest.raises(rq.ReferencePackError, match="fact_origins.llm_interpretation must be false"):
        rq.parse_reference_pack(tampered)


# --------------------------------------------------------------------------- hygiene

def test_module_never_fetches_or_writes_under_data():
    source = (ROOT / "engine" / "capital_structure" / "reference_qualification.py").read_text(encoding="utf-8")
    for forbidden in ("import requests", "urllib", "urlopen", "http.client", "socket", "\"data/", "'data/"):
        assert forbidden not in source, forbidden


def test_qualification_report_is_complete_and_clean(pack):
    report = rq.qualification_report(pack, ROOT)
    assert report["gold_problems"] == {}
    assert report["sources"]["qualified"] == 14
    assert report["sources"]["browser_qualified"] == 1
    assert report["sources"]["blocked"] == 0 and report["sources"]["unqualified"] == 0
    assert report["source_classes"]["proposed_reform"] == 1
    assert report["source_classes"]["binding_rule"] == 0
    assert report["enforceable_source_ids"] == ["nasdaq_rule_5600_series"]
    assert report["rule_examples"] == 8 and report["negative_examples"] == 3
    assert report["identities"]["WHK"] == {"cik": "0001921603", "label_drift": True, "case_supply": "unsupplied"}
    assert report["gold_cases"] == 13
    assert "binding_form_instruction_text" in report["gaps"]
