"""Synthetic mechanism proofs for the frozen PB-D quality adapter.

No fixture is historical or enrolled evidence. ``synthetic_quality_request`` is
also a reusable, directly unpackable request for the offline PB-D CLI tests.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from engine.company_intelligence.documents import SourceDocument, text_span
from engine.company_intelligence.events import FiscalPeriod, canonical_event_id
from engine.company_intelligence.pb_d_quality import (
    AUTHORITY_FLAGS, TAGS, QualityContractError, UnknownReason,
    append_source_correction, build_quality_receipt, coverage_packet_sha256,
    review_packet_sha256, verify_quality_receipt,
)


ISSUER = "cik:0000320193"
CUT = "2026-10-07T13:15:00Z"
START = "2026-10-02T13:15:00Z"
EVENT = canonical_event_id(ISSUER, FiscalPeriod(2026, 3), "corporate_action")


def _claim(name):
    return "claim_" + sha256(name.encode()).hexdigest()[:32]


def _header(reviewer, completed):
    return {
        "reviewer_id": reviewer, "review_receipt_id": "synthetic-review/" + reviewer,
        "completed_at": completed, "independent": True, "outcome_blind": True,
        "packet_sha256": "unbound",
    }


def rebind_reviews(request):
    """Synthetic fixture helper: model both raters reviewing the edited packet."""
    scope = {key: request[key] for key in ("issuer_id", "decision_cut", "freshness_start")}
    for event in request["events"]:
        digest = review_packet_sha256(**scope, event=event, source_documents=request["source_documents"])
        for review in event.get("reviews", []):
            review["packet_sha256"] = digest
        if event.get("adjudication") is not None:
            event["adjudication"]["packet_sha256"] = digest
    digest = coverage_packet_sha256(**scope, coverage=request["coverage"])
    for review in request["coverage"].get("reviews", []):
        review["packet_sha256"] = digest
    return request


def synthetic_quality_request():
    """One synthetic material event, two independently reviewed fresh roots.

    This fixture makes no claim about Apple or any actual issuer announcement.
    The issuer is merely an existing-format identity for contract tests.
    """
    bodies = {
        "synthetic-doc-issuer": "Synthetic issuer confirms a funded, 36-month supply contract for 200 units, conditional on site qualification.",
        "synthetic-doc-counterparty": "Synthetic counterparty independently confirms its executed purchase obligation and committed funding for those 200 units.",
    }
    documents, evidence, roots = {}, [], []
    names = list(bodies)
    claim_ids = [_claim(name) for name in names]
    for index, (document_id, body) in enumerate(bodies.items()):
        public = f"2026-10-06T{15 + index:02d}:00:00Z"
        observed = f"2026-10-06T{15 + index:02d}:05:00Z"
        document = SourceDocument(
            document_id=document_id, event_id=EVENT, document_kind="release",
            source_class="issuer_release" if index == 0 else "third_party",
            content_sha256=sha256(body.encode()).hexdigest(), content_bytes=len(body.encode()),
            fetched_at=observed, published_at=public, available_at=public,
            rights_state="public_primary" if index == 0 else "licensed",
            rights_profile="synthetic_rights_v1",
        )
        documents[document_id] = document.to_payload()
        span = text_span(
            document_id=document_id, document_version=1, body_sha256=document.content_sha256,
            segment_index=0, segment_text=body, start_byte=0, end_byte=len(body.encode()),
            text=body, rights_profile=document.rights_profile,
        )
        evidence.append({
            "claim_id": claim_ids[index], "issuer_id": ISSUER, "issuer_relevance": "direct",
            "source_span": span.to_payload(), "public_time_precision": "second",
            "clock_status": "verified", "new_information": True,
        })
        roots.append({
            "root_family_id": "synthetic-root-" + str(index),
            "origin_id": "synthetic-origin-" + str(index),
            "origin_document_id": document_id, "origin_claim_id": claim_ids[index],
            "supports_proposition_id": claim_ids[0], "support_kind": "proposition",
            "mechanism_link": None, "claim_ids": [claim_ids[index]],
            "dependencies": [], "lineage_complete": True,
        })
    event = {
        "event_id": EVENT, "event_version": 1, "owner_receipt_id": "synthetic-ci-generation/event-1",
        "issuer_id": ISSUER, "focal_proposition_id": claim_ids[0],
        "focal_proposition_text": "Synthetic funded supply obligation changes issuer revenue capacity.",
        "evidence": evidence, "roots": roots,
        "materiality": {
            "what_changed": "An executed funded obligation became public.",
            "mechanism": "Committed orders create revenue capacity subject to qualification.",
            "dimension": "revenue", "direction": "positive", "significance_basis": "duration",
            "significance_rationale": "The three-year obligation matters to the issuer's stated capacity plan.",
            "horizon": "36 months", "contingency": "Site qualification is required.",
            "alternative_explanation": "Orders may displace other committed capacity.",
            "falsifier": "Failure to qualify the site terminates the obligation.",
            "new_information_document_id": names[0],
        },
        "tag_details": {}, "reviews": [], "adjudication": None,
        "evidence_references": [], "correction_links": [], "occurred_at": None,
    }
    for index in range(2):
        review = _header("event-rater-" + str(index), f"2026-10-06T17:0{index}:00Z")
        review["labels"] = {
            tag: {"value": "TRUE" if tag in {"VERIFIED_MATERIAL_EVENT", "INDEPENDENT_EVIDENCE_2PLUS"} else "UNKNOWN" if tag == "EXPECTATION_CHANGE" else "FALSE",
                  "reason": "Independent synthetic packet review; no actual issuer inference.",
                  "evidence_refs": claim_ids if tag in {"VERIFIED_MATERIAL_EVENT", "INDEPENDENT_EVIDENCE_2PLUS"} else []}
            for tag in TAGS
        }
        review["root_pairs"] = [{
            "root_family_ids": [root["root_family_id"] for root in roots],
            "independent_generation": "TRUE", "shared_evidentiary_failure": "FALSE",
            "reason": "The synthetic packet records separately generated issuer and counterparty obligations, with no common originating source.",
            "evidence_refs": claim_ids,
        }]
        event["reviews"].append(review)
    coverage = {
        "issuer_id": ISSUER, "covered_from": START, "covered_through": CUT,
        "available_at": CUT, "observed_at": CUT,
        "status": "complete", "candidate_event_ids": [EVENT],
        "provider_receipt_ids": ["synthetic-provider-coverage/2026-10-07"],
        "missing_sources": [], "source_version": "synthetic-source/v1",
        "classifier_version": "synthetic-blinded-review/v1", "reviews": [],
    }
    for index in range(2):
        coverage["reviews"].append({**_header("coverage-rater-" + str(index), CUT), "candidate_set_complete": True})
    return rebind_reviews({
        "issuer_id": ISSUER, "ticker_at_cut": "SYNTHETIC", "decision_cut": CUT,
        "freshness_start": START, "events": [event], "coverage": coverage,
        "source_documents": documents, "source_bodies": bodies, "source_segments": {},
        "raw_attention": True, "synthetic": True,
    })


def _set_label(request, tag, value, *, event_index=0, reviewer_index=None):
    event = request["events"][event_index]
    rows = event["reviews"] if reviewer_index is None else [event["reviews"][reviewer_index]]
    for row in rows:
        row["labels"][tag]["value"] = value
        row["labels"][tag]["evidence_refs"] = [item["claim_id"] for item in event["evidence"]] if value == "TRUE" else []


class TestQualityReceipts(unittest.TestCase):
    def build(self, request):
        return build_quality_receipt(**rebind_reviews(request))

    def test_true_is_all_false_authority_and_unknown_baseline_does_not_block_q(self):
        request = synthetic_quality_request()
        receipt = build_quality_receipt(**request)
        self.assertEqual(receipt["q"], "TRUE")
        self.assertEqual(receipt["tags"]["EXPECTATION_CHANGE"]["value"], "UNKNOWN")
        self.assertTrue(receipt["tags"]["EXPECTATION_CHANGE"]["reasons"])
        self.assertEqual(set(receipt["tags"]), set(TAGS))
        self.assertEqual(receipt["authority_flags"], AUTHORITY_FLAGS)
        self.assertIs(receipt["enrolled"], False)
        self.assertEqual(receipt["evidence_mode"], "synthetic_mechanics_only")
        self.assertEqual(receipt["positive_event_ids"], [EVENT])
        self.assertEqual(receipt["display_anchor_event_id"], EVENT)
        self.assertEqual(receipt["completed_at"], CUT)
        self.assertEqual(receipt["decision_cut_new_york"], "2026-10-07T09:15:00-04:00")
        self.assertTrue(verify_quality_receipt(receipt))

    def test_roundtrip_determinism_and_caller_mutation_do_not_rewrite_receipt(self):
        request = synthetic_quality_request()
        original = deepcopy(request)
        receipt = build_quality_receipt(**request)
        self.assertEqual(request, original)
        self.assertEqual(receipt, build_quality_receipt(**json.loads(json.dumps(request))))
        request["events"][0]["roots"][0]["origin_id"] = "rewritten"
        self.assertNotEqual(receipt["input_packet"]["events"][0]["roots"][0]["origin_id"], "rewritten")
        self.assertTrue(verify_quality_receipt(json.loads(json.dumps(receipt))))
        self.assertNotIn("source_bodies", receipt["input_packet"])

    def test_late_ingestion_of_old_source_does_not_renew_freshness(self):
        request = synthetic_quality_request()
        for doc in request["source_documents"].values():
            doc["published_at"] = doc["available_at"] = "2026-09-01T15:00:00Z"
        _set_label(request, "VERIFIED_MATERIAL_EVENT", "FALSE")
        _set_label(request, "NO_MATERIAL_EVENT", "TRUE")
        _set_label(request, "ATTENTION_ONLY", "TRUE")
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(receipt["event_receipts"][0]["fresh_independent_evidence_2plus"]["value"], "FALSE")
        self.assertEqual(receipt["tags"]["ATTENTION_ONLY"]["value"], "TRUE")

    def test_stale_material_context_cannot_leave_contradictory_window_tags(self):
        request = synthetic_quality_request()
        for doc in request["source_documents"].values():
            doc["published_at"] = doc["available_at"] = "2026-09-01T15:00:00Z"
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(receipt["tags"]["VERIFIED_MATERIAL_EVENT"]["value"], "FALSE")
        self.assertEqual(receipt["tags"]["NO_MATERIAL_EVENT"]["value"], "TRUE")
        self.assertEqual(receipt["input_packet"]["events"][0]["reviews"][0]["labels"]["VERIFIED_MATERIAL_EVENT"]["value"], "TRUE")

    def test_first_usable_qualifying_pair_is_not_shifted_by_later_old_context(self):
        request = synthetic_quality_request()
        event = request["events"][0]
        body = "Synthetic older funding context, locally retained later than the qualifying pair."
        doc = SourceDocument(
            document_id="synthetic-older-context", event_id=EVENT,
            document_kind="supplement", source_class="third_party",
            content_sha256=sha256(body.encode()).hexdigest(), content_bytes=len(body.encode()),
            published_at="2026-09-01T15:00:00Z", available_at="2026-09-01T15:00:00Z",
            fetched_at="2026-10-07T12:00:00Z", rights_state="licensed", rights_profile="synthetic_rights_v1",
        )
        span = text_span(document_id=doc.document_id, document_version=1, body_sha256=doc.content_sha256,
                         segment_index=0, segment_text=body, start_byte=0, end_byte=len(body.encode()),
                         text=body, rights_profile=doc.rights_profile)
        claim = _claim(doc.document_id)
        request["source_documents"][doc.document_id] = doc.to_payload()
        request["source_bodies"][doc.document_id] = body
        event["evidence"].append({"claim_id": claim, "issuer_id": ISSUER, "issuer_relevance": "direct",
                                  "source_span": span.to_payload(), "public_time_precision": "second",
                                  "clock_status": "verified", "new_information": False})
        event["roots"].append({"root_family_id": "synthetic-old-root", "origin_id": "synthetic-old-origin",
                               "origin_document_id": doc.document_id, "origin_claim_id": claim,
                               "supports_proposition_id": event["focal_proposition_id"], "support_kind": "mechanism_link",
                               "mechanism_link": "Prior funding context", "claim_ids": [claim],
                               "dependencies": [], "lineage_complete": True})
        for index, review in enumerate(event["reviews"]):
            review["completed_at"] = f"2026-10-07T12:0{5 + index}:00Z"
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "TRUE")
        self.assertEqual(receipt["event_receipts"][0]["first_usable_at"], "2026-10-06T16:05:00Z")
        self.assertEqual(receipt["event_receipts"][0]["completed_at"], "2026-10-07T12:06:00Z")
        self.assertEqual(receipt["completed_at"], CUT)

    def test_freshness_start_excluded_and_cut_included(self):
        request = synthetic_quality_request()
        doc = next(iter(request["source_documents"].values()))
        doc["published_at"] = doc["available_at"] = START
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(
            tuple(receipt["tags"][tag]["value"] for tag in ("VERIFIED_MATERIAL_EVENT", "NO_MATERIAL_EVENT", "ATTENTION_ONLY")),
            ("FALSE", "TRUE", "TRUE"),
        )
        request = synthetic_quality_request()
        for doc in request["source_documents"].values():
            doc["published_at"] = doc["available_at"] = doc["fetched_at"] = CUT
        for review in request["events"][0]["reviews"] + request["coverage"]["reviews"]:
            review["completed_at"] = CUT
        self.assertEqual(self.build(request)["q"], "TRUE")

    def test_date_only_missing_and_suspicious_public_clocks_remain_unknown(self):
        for mutation, reason in (
            (lambda q: q["source_documents"]["synthetic-doc-issuer"].update(published_at=None), UnknownReason.CLOCK_MISSING),
            (lambda q: q["source_documents"]["synthetic-doc-issuer"].update(published_at="2026-10-06"), UnknownReason.CLOCK_MISSING),
            (lambda q: q["events"][0]["evidence"][0].update(public_time_precision="day"), UnknownReason.PUBLIC_CLOCK_UNVERIFIED),
            (lambda q: q["events"][0]["evidence"][0].update(clock_status="backdated"), UnknownReason.PUBLIC_CLOCK_UNVERIFIED),
            (lambda q: q["source_documents"]["synthetic-doc-issuer"].update(fetched_at="2026-10-06T14:00:00Z"), UnknownReason.CLOCK_CONTRADICTION),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])

    def test_missing_body_tampered_span_and_unknown_rights_are_not_evidence(self):
        for mutation, reason in (
            (lambda q: q["source_bodies"].pop("synthetic-doc-issuer"), UnknownReason.SOURCE_BYTES_MISSING),
            (lambda q: q["source_bodies"].update({"synthetic-doc-issuer": "tampered source"}), UnknownReason.SOURCE_RECEIPT_INVALID),
            (lambda q: q["events"][0]["evidence"][0]["source_span"]["receipt"].update(span_start_byte=10), UnknownReason.SOURCE_RECEIPT_INVALID),
            (lambda q: q["source_documents"]["synthetic-doc-issuer"].update(rights_state="unknown"), UnknownReason.RIGHTS_UNVERIFIED),
            (lambda q: q["source_documents"]["synthetic-doc-issuer"].update(fetched_at=None), UnknownReason.CLOCK_MISSING),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])

    def test_forged_segment_cannot_borrow_a_real_document_digest(self):
        request = synthetic_quality_request()
        entry = request["events"][0]["evidence"][0]
        document_id = entry["source_span"]["document_id"]
        document = request["source_documents"][document_id]
        fabricated = "This sentence is invented and does not occur in the original source body."
        # Native span minting checks the supplied segment, but cannot establish
        # that a caller extracted that segment from the separately hashed body.
        forged = text_span(
            document_id=document_id, document_version=1,
            body_sha256=document["content_sha256"], segment_index=0,
            segment_text=fabricated, start_byte=0, end_byte=len(fabricated.encode()),
            text=fabricated, rights_profile=document["rights_profile"],
        )
        entry["source_span"] = forged.to_payload()
        request["source_segments"][forged.span_id] = fabricated
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.SOURCE_SEGMENT_UNVERIFIED.value, receipt["q_reasons"])
        request["source_segments"] = {}
        self.assertEqual(self.build(request)["q"], "UNKNOWN")

    def test_incidental_wrong_issuer_and_non_native_event_identity_fail_closed(self):
        for mutation, reason in (
            (lambda q: q["events"][0]["evidence"][0].update(issuer_relevance="incidental"), UnknownReason.INCIDENTAL_ISSUER),
            (lambda q: q["events"][0]["evidence"][0].update(issuer_id="cik:0000789019"), UnknownReason.ISSUER_MISMATCH),
            (lambda q: q["events"][0].update(event_id="invented-new-event"), UnknownReason.EVENT_IDENTITY_UNVERIFIED),
            (lambda q: q["events"][0].update(owner_receipt_id=None), UnknownReason.EVENT_IDENTITY_UNVERIFIED),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                request["coverage"]["candidate_event_ids"] = [request["events"][0]["event_id"]]
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])

    def test_syndicated_manifestations_are_one_root(self):
        request = synthetic_quality_request()
        event = request["events"][0]
        event["roots"][0]["claim_ids"] = [item["claim_id"] for item in event["evidence"]]
        event["roots"] = event["roots"][:1]
        for review in event["reviews"]:
            review["root_pairs"] = []
        _set_label(request, "INDEPENDENT_EVIDENCE_2PLUS", "FALSE")
        _set_label(request, "SYNDICATED_SINGLE_ROOT", "TRUE")
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(receipt["tags"]["SYNDICATED_SINGLE_ROOT"]["value"], "TRUE")
        self.assertEqual(receipt["tags"]["VERIFIED_MATERIAL_EVENT"]["value"], "TRUE")

    def test_distinct_root_names_cannot_override_shared_upstream_or_missing_lineage(self):
        request = synthetic_quality_request()
        request["events"][0]["roots"][1]["dependencies"] = [request["events"][0]["roots"][0]["root_family_id"]]
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.LABEL_CONFLICT.value, receipt["q_reasons"])
        request = synthetic_quality_request()
        request["events"][0]["roots"] = []
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.ROOT_LINEAGE_UNVERIFIED.value, receipt["q_reasons"])

    def test_renaming_the_same_origin_claim_or_document_does_not_make_it_independent(self):
        for same_claim in (True, False):
            request = synthetic_quality_request()
            event = request["events"][0]
            if same_claim:
                event["roots"][1]["origin_claim_id"] = event["roots"][0]["origin_claim_id"]
                event["roots"][1]["origin_document_id"] = event["roots"][0]["origin_document_id"]
                event["roots"][1]["claim_ids"].append(event["roots"][0]["origin_claim_id"])
            else:
                event["evidence"][1]["source_span"] = deepcopy(event["evidence"][0]["source_span"])
                event["roots"][1]["origin_document_id"] = event["roots"][0]["origin_document_id"]
                request["source_documents"].pop("synthetic-doc-counterparty")
                request["source_bodies"].pop("synthetic-doc-counterparty")
            receipt = self.build(request)
            self.assertEqual(receipt["q"], "UNKNOWN")
            self.assertIn(UnknownReason.LABEL_CONFLICT.value, receipt["q_reasons"])

    def test_other_proposition_roots_and_unreviewed_pairs_are_unknown(self):
        for mutation, reason in (
            (lambda q: q["events"][0]["roots"][1].update(supports_proposition_id="unrelated-holdings-claim"), UnknownReason.ROOT_SCOPE_MISMATCH),
            (lambda q: q["events"][0]["reviews"][1].update(root_pairs=[]), UnknownReason.ROOT_PAIR_UNREVIEWED),
            (lambda q: q["events"][0]["roots"][1].update(lineage_complete=False), UnknownReason.ROOT_LINEAGE_UNVERIFIED),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])

    def test_incomplete_candidate_coverage_overrides_a_positive_event(self):
        for mutation in (
            lambda q: q["coverage"].update(status="partial"),
            lambda q: q["coverage"].update(missing_sources=["rights-blocked-provider"]),
            lambda q: q["coverage"].update(candidate_event_ids=[EVENT, "unretrieved-existing-owner-event"]),
        ):
            request = synthetic_quality_request()
            mutation(request)
            receipt = self.build(request)
            self.assertEqual(receipt["q"], "UNKNOWN")
            self.assertEqual(receipt["positive_event_ids"], [])
            self.assertIsNone(receipt["display_anchor_event_id"])

    def test_final_candidate_coverage_requires_matching_scope_and_by_cut_watermark(self):
        for mutation, reason in (
            (lambda q: q["coverage"].pop("observed_at"), UnknownReason.COVERAGE_CLOCK_MISSING),
            (lambda q: q["coverage"].update(covered_through="2026-10-07T13:14:59Z"), UnknownReason.COVERAGE_SCOPE_MISMATCH),
            (lambda q: q["coverage"].update(covered_from="2026-10-05T13:15:00Z"), UnknownReason.COVERAGE_SCOPE_MISMATCH),
            (lambda q: q["coverage"].update(issuer_id="cik:0000789019"), UnknownReason.COVERAGE_SCOPE_MISMATCH),
            (lambda q: q["coverage"].update(available_at="2026-10-06T14:00:00Z", observed_at="2026-10-06T14:00:00Z"), UnknownReason.CLOCK_CONTRADICTION),
            (lambda q: q["coverage"]["reviews"][0].update(completed_at="2026-10-06T14:00:00Z"), UnknownReason.REVIEW_BEFORE_EVIDENCE),
            (lambda q: q["coverage"].update(observed_at="2026-10-07T13:15:00.000001Z"), UnknownReason.EVIDENCE_AFTER_CUT),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])
                self.assertEqual(receipt["positive_event_ids"], [])

    def test_any_unresolved_candidate_overrides_another_positive_event(self):
        request = synthetic_quality_request()
        other = deepcopy(request["events"][0])
        other["event_id"] = canonical_event_id(ISSUER, FiscalPeriod(2026, 3), "guidance_update")
        other["evidence"], other["roots"] = [], []
        other["owner_receipt_id"] = "synthetic-ci-generation/second-candidate"
        request["events"].append(other)
        request["coverage"]["candidate_event_ids"].append(other["event_id"])
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertEqual({row["q"] for row in receipt["event_receipts"]}, {"TRUE", "UNKNOWN"})

    def test_reviewed_empty_set_is_q0_while_missing_coverage_is_unknown(self):
        request = synthetic_quality_request()
        request["events"] = []
        request["source_documents"] = request["source_bodies"] = {}
        request["coverage"]["candidate_event_ids"] = []
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(receipt["tags"]["NO_MATERIAL_EVENT"]["value"], "TRUE")
        self.assertEqual(receipt["tags"]["ATTENTION_ONLY"]["value"], "TRUE")
        request["coverage"]["reviews"] = []
        self.assertEqual(self.build(request)["q"], "UNKNOWN")

    def test_two_blinded_independent_reviews_must_exist_by_cut(self):
        for mutation, reason in (
            (lambda q: q["events"][0].update(reviews=q["events"][0]["reviews"][:1]), UnknownReason.REVIEW_MISSING),
            (lambda q: q["events"][0]["reviews"][1].update(reviewer_id="event-rater-0"), UnknownReason.REVIEW_NOT_INDEPENDENT),
            (lambda q: q["events"][0]["reviews"][1].update(outcome_blind=False), UnknownReason.REVIEW_NOT_BLIND),
            (lambda q: q["events"][0]["reviews"][1].update(completed_at="2026-10-07T13:15:01Z"), UnknownReason.REVIEW_AFTER_CUT),
            (lambda q: q["events"][0]["reviews"][1].update(completed_at="2026-10-06T15:30:00Z"), UnknownReason.REVIEW_BEFORE_EVIDENCE),
        ):
            with self.subTest(reason=reason):
                request = synthetic_quality_request()
                mutation(request)
                receipt = self.build(request)
                self.assertEqual(receipt["q"], "UNKNOWN")
                self.assertIn(reason.value, receipt["q_reasons"])

    def test_edit_after_review_breaks_packet_binding(self):
        request = synthetic_quality_request()
        request["events"][0]["materiality"]["horizon"] = "A different unreviewed horizon"
        receipt = build_quality_receipt(**request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.REVIEW_PACKET_MISMATCH.value, receipt["q_reasons"])

    def test_third_adjudicator_resolves_only_with_original_receipts_and_by_cut_clock(self):
        request = synthetic_quality_request()
        _set_label(request, "VERIFIED_MATERIAL_EVENT", "FALSE", reviewer_index=1)
        self.assertEqual(self.build(request)["q"], "UNKNOWN")
        event = request["events"][0]
        adjudicator = deepcopy(event["reviews"][0])
        adjudicator.update(_header("third-adjudicator", "2026-10-07T12:10:00Z"))
        adjudicator["resolves_review_receipt_ids"] = [row["review_receipt_id"] for row in event["reviews"]]
        event["adjudication"] = adjudicator
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "TRUE")
        self.assertTrue(receipt["event_receipts"][0]["adjudicated"])
        self.assertEqual(receipt["event_receipts"][0]["completed_at"], "2026-10-07T12:10:00Z")
        self.assertEqual(receipt["completed_at"], CUT)
        adjudicator["completed_at"] = "2026-10-08T12:10:00Z"
        self.assertEqual(self.build(request)["q"], "UNKNOWN")
        adjudicator["completed_at"] = "2026-10-06T17:00:30Z"
        # This is after all source evidence but before the second rater finishes.
        self.assertEqual(self.build(request)["q"], "UNKNOWN")

    def test_unknown_expectation_and_supported_immaterial_change_are_orthogonal(self):
        request = synthetic_quality_request()
        _set_label(request, "EXPECTATION_CHANGE", "TRUE")
        missing = self.build(request)
        self.assertEqual(missing["q"], "TRUE")
        self.assertEqual(missing["tags"]["EXPECTATION_CHANGE"]["value"], "UNKNOWN")
        common = {
            "issuer_id": ISSUER, "period": "2027FY", "basis": "GAAP",
            "units": "million", "currency": "USD", "rights_state": "licensed",
            "rights_profile": "synthetic-license/v1", "owner_receipt_id": "synthetic-baseline/v1",
        }
        detail = {
            "baseline_id": "synthetic-baseline-1", "baseline_type": "guidance",
            "prior": {**common, "value": "100", "available_at": "2026-10-01T15:00:00Z", "observed_at": "2026-10-01T15:05:00Z"},
            "current": {**common, "value": "100.1", "available_at": "2026-10-06T15:00:00Z", "observed_at": "2026-10-06T15:05:00Z"},
        }
        request["events"][0]["tag_details"]["EXPECTATION_CHANGE"] = detail
        _set_label(request, "VERIFIED_MATERIAL_EVENT", "FALSE")
        _set_label(request, "ATTENTION_ONLY", "TRUE")
        _set_label(request, "NO_MATERIAL_EVENT", "TRUE")
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "FALSE")
        self.assertEqual(receipt["tags"]["EXPECTATION_CHANGE"]["value"], "TRUE")
        self.assertEqual(receipt["tags"]["ATTENTION_ONLY"]["value"], "TRUE")
        detail["current"]["basis"] = "non-GAAP"
        receipt = self.build(request)
        self.assertEqual(receipt["tags"]["EXPECTATION_CHANGE"]["value"], "UNKNOWN")
        self.assertEqual(receipt["q"], "FALSE")

    def test_unsupported_materiality_is_unknown_without_a_universal_dollar_threshold(self):
        request = synthetic_quality_request()
        request["events"][0]["materiality"].pop("significance_rationale")
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.MATERIALITY_UNSUPPORTED.value, receipt["q_reasons"])

    def test_orthogonal_strategic_government_and_financing_tags_can_coexist(self):
        request = synthetic_quality_request()
        refs = [entry["claim_id"] for entry in request["events"][0]["evidence"]]
        details = request["events"][0]["tag_details"]
        details["STRATEGIC_OPTION"] = {
            "resources": "Committed synthetic capacity", "funding_basis": "Source-backed financing",
            "continuing_validity": "Funding remains available through the stated milestone",
            "causal_path": "Qualification enables a new product", "milestone": "Site qualification",
            "falsifier": "Qualification fails", "evidence_refs": refs,
        }
        details["GOVERNMENT_LINKED"] = {"action": "Synthetic procurement decision", "causal_role": "Provides the funded order", "status": "approved", "evidence_refs": refs}
        details["FINANCING_LINKED"] = {"terms": "Committed synthetic credit", "causal_role": "Funds qualifying capacity", "covenants": "Qualification requirement", "commitment": "conditional", "evidence_refs": refs}
        for tag in details:
            _set_label(request, tag, "TRUE")
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "TRUE")
        for tag in details:
            self.assertEqual(receipt["tags"][tag]["value"], "TRUE")
        self.assertEqual(receipt["tags"]["EXPECTATION_CHANGE"]["value"], "UNKNOWN")

    def test_strict_tristate_and_no_outcome_fields(self):
        request = synthetic_quality_request()
        request["events"][0]["reviews"][0]["labels"]["VERIFIED_MATERIAL_EVENT"]["value"] = True
        with self.assertRaises(QualityContractError):
            self.build(request)
        request = synthetic_quality_request()
        request["events"][0]["future_return"] = 0.3
        with self.assertRaises(QualityContractError):
            self.build(request)

    def test_every_retained_annotation_mapping_refuses_structured_outcome_fields(self):
        def add_outcome(value):
            value["h5_spy_excess_pp"] = 99
        paths = (
            lambda q: q["events"][0]["evidence"][0],
            lambda q: q["events"][0]["roots"][0],
            lambda q: q["events"][0]["materiality"],
            lambda q: q["events"][0]["reviews"][0],
            lambda q: q["events"][0]["reviews"][0]["labels"]["VERIFIED_MATERIAL_EVENT"],
            lambda q: q["events"][0]["reviews"][0]["root_pairs"][0],
            lambda q: q["events"][0]["evidence"][0]["source_span"],
            lambda q: q["events"][0]["evidence"][0]["source_span"]["locator"],
            lambda q: q["events"][0]["evidence"][0]["source_span"]["receipt"],
            lambda q: q["source_documents"]["synthetic-doc-issuer"],
            lambda q: q["coverage"],
            lambda q: q["coverage"]["reviews"][0],
        )
        for index, path in enumerate(paths):
            with self.subTest(mapping=index):
                request = synthetic_quality_request()
                add_outcome(path(request))
                # Both direct build and attempted re-review must refuse the
                # malformed packet, not merely report a stale review digest.
                with self.assertRaisesRegex(QualityContractError, "unsupported fields"):
                    build_quality_receipt(**request)
                with self.assertRaisesRegex(QualityContractError, "unsupported fields"):
                    rebind_reviews(request)
        request = synthetic_quality_request()
        request["events"][0]["reviews"][0]["reason"] = {"outcome": 99}
        with self.assertRaises(QualityContractError):
            self.build(request)
        request = synthetic_quality_request()
        request["events"][0]["reviews"][0]["labels"]["VERIFIED_MATERIAL_EVENT"]["reason"] = {"outcome": 99}
        with self.assertRaisesRegex(QualityContractError, "scalar type"):
            self.build(request)

    def test_unused_source_document_body_and_segment_maps_are_refused(self):
        request = synthetic_quality_request()
        request["source_documents"]["unused-future-context"] = {
            "outcome_h5_pp": 99, "fetched_at": "2026-10-20T12:00:00Z",
        }
        with self.assertRaisesRegex(QualityContractError, "unsupported fields"):
            self.build(request)
        request = synthetic_quality_request()
        future = deepcopy(request["source_documents"]["synthetic-doc-issuer"])
        future.update(document_id="unused-native-shaped-future", fetched_at="2026-10-20T12:00:00Z")
        request["source_documents"][future["document_id"]] = future
        with self.assertRaisesRegex(QualityContractError, "unreferenced owner ID"):
            self.build(request)
        for key in ("source_bodies", "source_segments"):
            request = synthetic_quality_request()
            request[key]["unused-future-context"] = "future outcome context"
            with self.assertRaisesRegex(QualityContractError, "unreferenced owner ID"):
                self.build(request)

    def test_missing_secondary_is_only_its_own_unknown_and_extra_tag_is_refused(self):
        request = synthetic_quality_request()
        for review in request["events"][0]["reviews"]:
            del review["labels"]["EXPECTATION_CHANGE"]
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "TRUE")
        self.assertEqual(receipt["tags"]["EXPECTATION_CHANGE"]["value"], "UNKNOWN")
        self.assertEqual(set(receipt["tags"]), set(TAGS))
        request["events"][0]["reviews"][0]["labels"]["OUTCOME_WINNER"] = {"value": "TRUE", "reason": "future result", "evidence_refs": []}
        with self.assertRaisesRegex(QualityContractError, "unsupported fields"):
            self.build(request)
        request = synthetic_quality_request()
        for review in request["events"][0]["reviews"]:
            del review["labels"]["VERIFIED_MATERIAL_EVENT"]
        self.assertEqual(self.build(request)["q"], "UNKNOWN")

    def test_retained_optional_context_is_clock_gated_even_if_secondary_is_unknown(self):
        request = synthetic_quality_request()
        request["events"][0]["tag_details"]["EXPECTATION_CHANGE"] = {
            "baseline_id": "later-baseline", "baseline_type": "guidance",
            "current": {"value": 99, "available_at": "2026-10-20T12:00:00Z", "observed_at": "2026-10-20T12:00:01Z"},
        }
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.EVIDENCE_AFTER_CUT.value, receipt["q_reasons"])
        request["events"][0]["tag_details"]["EXPECTATION_CHANGE"]["current"] = {"value": None}
        self.assertEqual(self.build(request)["q"], "TRUE")
        request = synthetic_quality_request()
        request["events"][0]["occurred_at"] = "2026-10-20T12:00:00Z"
        self.assertEqual(self.build(request)["q"], "UNKNOWN")
        request = synthetic_quality_request()
        request["events"][0]["correction_links"] = [{
            "correction_receipt_id": "future-correction", "available_at": "2026-10-20T12:00:00Z",
            "observed_at": "2026-10-20T12:00:01Z",
        }]
        self.assertEqual(self.build(request)["q"], "UNKNOWN")

    def test_rehashed_poisoned_stored_packet_does_not_pass_verifier(self):
        receipt = build_quality_receipt(**synthetic_quality_request())
        receipt["input_packet"]["events"][0]["evidence"][0]["h5_spy_excess_pp"] = 99
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        self.assertFalse(verify_quality_receipt(receipt))

    def test_display_excerpt_must_come_from_the_authenticated_span(self):
        request = synthetic_quality_request()
        request["events"][0]["evidence"][0]["source_span"]["display_excerpt"] = "An invented future result, unrelated to the actual source bytes."
        receipt = self.build(request)
        self.assertEqual(receipt["q"], "UNKNOWN")
        self.assertIn(UnknownReason.SOURCE_RECEIPT_INVALID.value, receipt["q_reasons"])

    def test_receipt_tampering_and_numeric_false_authority_are_refused(self):
        receipt = build_quality_receipt(**synthetic_quality_request())
        receipt["q"] = "FALSE"
        self.assertFalse(verify_quality_receipt(receipt))
        receipt = build_quality_receipt(**synthetic_quality_request())
        receipt["authority_flags"]["can_rank"] = 0
        self.assertFalse(verify_quality_receipt(receipt))
        receipt = build_quality_receipt(**synthetic_quality_request())
        receipt["tags"] = list(TAGS)
        self.assertFalse(verify_quality_receipt(receipt))

    def test_source_correction_preserves_original_primary_and_requests_mapping_quarantine(self):
        request = synthetic_quality_request()
        original = build_quality_receipt(**request)
        frozen = deepcopy(original)
        old_id = request["events"][0]["evidence"][0]["source_span"]["document_id"]
        new = deepcopy(request["source_documents"][old_id])
        new.update({
            "document_id": old_id + "-r2", "revision": 2, "supersedes_document_id": old_id,
            "document_kind": "release_amendment", "content_sha256": sha256(b"corrected source").hexdigest(),
            "content_bytes": len(b"corrected source"), "published_at": "2026-10-08T15:00:00Z",
            "available_at": "2026-10-08T15:00:00Z", "fetched_at": "2026-10-08T15:05:00Z",
        })
        link = {
            "original_claim_id": request["events"][0]["focal_proposition_id"],
            "corrected_claim_id": _claim("synthetic-corrected-owner-claim"),
            "reason": "Synthetic source issuer revises the funded commitment.",
            "correction_kind": "source_correction", "corrected_document": new,
        }
        appended = append_source_correction(original, correction=link)
        self.assertEqual(original, frozen)
        self.assertEqual(appended["original_receipt"], frozen)
        self.assertEqual(appended["primary_q"], "TRUE")
        self.assertEqual(appended["original_receipt_sha256"], frozen["receipt_sha256"])
        self.assertEqual(appended["corrected_truth_state"], "not_evaluated")
        self.assertFalse(appended["quarantine_required"])
        self.assertTrue(verify_quality_receipt(appended["original_receipt"]))
        link["correction_kind"] = "mapping_error"
        self.assertTrue(append_source_correction(original, correction=link)["quarantine_required"])
        link["corrected_document"]["event_id"] = "invented-corrected-event"
        with self.assertRaises(QualityContractError):
            append_source_correction(original, correction=link)


if __name__ == "__main__":
    unittest.main()
