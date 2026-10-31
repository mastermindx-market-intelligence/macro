"""Tests for engine.news_impact.eval_grade (A3 §4.1-§4.7 grading core).

Acceptance fixtures are the A3_eval design worked cases 1-5 (section 5), graded
through the §4.7 pseudocode order. Also proves: totality over every enum value
of every graded-field component of the frozen news_impact_event.v1 contract
(sha256 prefix 3edc7139), currency NA vs ISO, exact absence-reason matching,
W3-R3 ingest stripping, permutation invariance (W3-R6), and every CODES string
(W3-R5). Hermetic: no network, no repo data files (frozen contract is loaded
from contracts/news_impact and the test fails closed if absent), tmp_path
unused because the module does no file I/O.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from engine.news_impact import eval_grade as eg

# ---------------------------------------------------------------- fixtures


def field_absence(reason: str, subject: str = "slot") -> dict:
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": "test fixture",
        "missing_fields": [subject],
    }


def owner_absence(reason: str, subject: str = "period") -> dict:
    return {
        "schema": "typed_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": "test fixture",
        "missing_fields": [subject],
        "event_id": None,
        "document_id": None,
    }


def span_evidence(quote: str) -> dict:
    return {
        "claimed_quote": quote,
        "span": {"schema": "source_span.v1", "span_id": "span_" + "0" * 20},
    }


def point_qty(
    value,
    *,
    quote="a stated amount",
    unit="USD",
    currency="USD",
    basis="incremental",
    period=None,
    negated=False,
    bound="exact",
    evidence=True,
):
    if period is None:
        period = {"year": 2026, "quarter": 3, "calendar_end": None, "period_kind": "quarter"}
    q = {
        "form": "point",
        "value": value,
        "bound": bound,
        "unit": unit,
        "currency": currency,
        "basis": basis,
        "period": period,
        "negated": negated,
    }
    if evidence:
        q["evidence"] = span_evidence(quote)
    return q


def range_qty(low, high, **kw):
    q = point_qty(low, **kw)
    q.pop("value")
    q.pop("bound", None)
    q["form"] = "range"
    q["low"] = low
    q["high"] = high
    return q


def absent_qty(reason="not_stated"):
    return {"form": "absent", "absence": field_absence(reason)}


OK_SPAN = lambda evidence: True  # noqa: E731  (injected owner-verify_span wrapper)
BAD_SPAN = lambda evidence: False  # noqa: E731


T1 = "capital_allocation_event.v1"
T2 = "demand_guidance_contract_event.v1"
T3 = "strategic_product_partnership_event.v1"


def grade(gold, cand, *, verifier=None, field="stated_amount", template=T2, case_id="case_aaaaaaaaaaaaaaaaaaaaaaaa", fold="f3"):
    return eg.grade_critical_numeric_field(
        case_id=case_id,
        fold=fold,
        template=template,
        field=field,
        gold_quantity=gold,
        candidate_quantity=cand,
        span_verifier=verifier,
    )


# ------------------------------------------------- design worked cases 1-5


class TestCase1T1Correction:
    """Case 1 — T1 fully graded; all three slots correct (gold == candidate)."""

    def test_outcome_table(self):
        gold = {
            "incremental_amount": point_qty(
                165000000000,
                quote="an increase of $165 billion to its share repurchase authorization",
                basis="incremental",
            ),
            "remaining_authorization": absent_qty("not_stated"),
            "executed_amount": absent_qty("not_stated"),
        }
        cand = {
            "incremental_amount": point_qty(
                165000000000,
                quote="an increase of $165 billion to its share repurchase authorization",
                basis="incremental",
            ),
            "remaining_authorization": absent_qty("not_stated"),
            "executed_amount": absent_qty("not_stated"),
        }
        items = eg.grade_case(
            case_id="case_aaaaaaaaaaaaaaaaaaaaaaaa",
            fold="f3",
            template=T1,
            gold_packet=gold,
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )
        got = {i.field: i.outcome for i in items}
        assert got == {
            "incremental_amount": "correct",
            "remaining_authorization": "correct",
            "executed_amount": "correct",
        }
        assert all(isinstance(i, eg.GradedItem) for i in items)
        assert eg.graded_items_to_dicts(items)[0]["case_id"] == "case_aaaaaaaaaaaaaaaaaaaaaaaa"


class TestCase2T2BasisConst:
    """Case 2 — bookings must be incremental (F3); equal value with basis=total mismatches."""

    GOLD = {
        "stated_amount": point_qty(
            400000000,
            quote="booked $400 million of incremental orders in the quarter",
            basis="incremental",
        )
    }

    def test_valid_cheap_extractor_is_correct(self):
        cand = {
            "stated_amount": point_qty(
                400000000,
                quote="booked $400 million of incremental orders",
                basis="incremental",
            )
        }
        item = eg.grade_case(
            case_id="case_bbbbbbbbbbbbbbbbbbbbbbbb",
            fold="f2",
            template=T2,
            gold_packet=dict(self.GOLD),
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )[0]
        assert item.outcome == "correct"

    def test_basis_total_is_wrong_value_even_when_value_equals(self):
        cand = {
            "stated_amount": point_qty(
                400000000,
                quote="$400 million of orders",
                basis="total",
            )
        }
        item = eg.grade_case(
            case_id="case_bbbbbbbbbbbbbbbbbbbbbbbb",
            fold="f2",
            template=T2,
            gold_packet=dict(self.GOLD),
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )[0]
        assert item.outcome == "wrong_value"
        assert "mismatch:basis" in item.notes


class TestCase3T2TamRoutingMiss:
    """Case 3 — TAM treated as company guidance: critical numeric is wrong_value.

    The §4.7 pseudocode (frozen spec) drives the outcome. With gold present
    (metric=other TAM figure) vs candidate guidance semantics, the canon
    comparison mismatches on period/basis -> wrong_value, matching the case-3
    grade table. The gold-absent variant (stated_without_number) grades
    wrong_absence per the pseudocode branch 2 — recorded in the lane return
    packet as a text-vs-pseudocode divergence; pseudocode wins (W3-R1).
    """

    def test_tam_as_guidance_is_wrong_value(self):
        gold = {
            "stated_amount": point_qty(
                500000000,
                quote="addressable market remains about $500 million later this decade",
                basis="total",
                period={
                    "year": 2030,
                    "quarter": None,
                    "calendar_end": None,
                    "period_kind": "multi_year",
                    "end_year": 2030,
                },
            )
        }
        cand = {
            "stated_amount": point_qty(
                500000000,
                quote="management guided to about $500 million",
                basis="total",
                period={"year": 2026, "quarter": 4, "calendar_end": None, "period_kind": "quarter"},
            )
        }
        item = eg.grade_case(
            case_id="case_cccccccccccccccccccccccc",
            fold="f1",
            template=T2,
            gold_packet=gold,
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )[0]
        assert item.outcome == "wrong_value"
        assert "mismatch:period" in item.notes

    def test_tam_gold_absent_variant_is_wrong_absence_per_pseudocode(self):
        gold = {"stated_amount": absent_qty("stated_without_number")}
        cand = {"stated_amount": point_qty(500000000, quote="$500 million", basis="total")}
        item = eg.grade_case(
            case_id="case_cccccccccccccccccccccccc",
            fold="f1",
            template=T2,
            gold_packet=gold,
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )[0]
        assert item.outcome == "wrong_absence"
        assert "candidate_present_where_gold_absent" in item.notes


class TestCase4T3AbsenceBothSides:
    """Case 4 — stated_quantity absent on both sides with the same reason -> correct."""

    def test_correct_absence(self):
        gold = {"stated_quantity": absent_qty("not_stated")}
        cand = {"stated_quantity": absent_qty("not_stated")}
        item = eg.grade_case(
            case_id="case_dddddddddddddddddddddddd",
            fold="f4",
            template=T3,
            gold_packet=gold,
            candidate_packet=cand,
        )[0]
        assert item.outcome == "correct"
        assert item.gold_value == {"form": "absent", "schema": "field_absence.v1", "reason": "not_stated"}


class TestCase5T1Abstention:
    """Case 5 — defer with null gold packet and null candidate packet."""

    ROW = dict(
        case_id="case_eeeeeeeeeeeeeeeeeeeeeeee",
        fold="f5",
        template=T1,
        disposition="deferred",
        gold_packet=None,
        candidate_packet=None,
    )

    def test_out_of_denom_for_auto_published_metric(self):
        items = eg.grade_batch([self.ROW], dispositions={"auto_published"})
        assert items == ()

    def test_skipped_in_all_disposition_fold_too(self):
        assert eg.grade_batch([self.ROW]) == ()

    def test_grade_case_direct_raises_gold_packet_absent(self):
        with pytest.raises(eg.EvalGradeError) as exc:
            eg.grade_case(case_id="c", fold="f5", template=T1, gold_packet=None)
        assert exc.value.code == "GOLD_PACKET_ABSENT"

    def test_second_absence_path_invented_number_is_wrong_absence(self):
        gold = {
            "incremental_amount": point_qty(1, quote="x"),
            "remaining_authorization": absent_qty("not_stated"),
            "executed_amount": absent_qty("not_stated"),
        }
        cand = {
            "incremental_amount": point_qty(1, quote="x"),
            "remaining_authorization": point_qty(150000000000, quote="$150 billion"),
            "executed_amount": absent_qty("not_stated"),
        }
        items = eg.grade_case(
            case_id="case_eeeeeeeeeeeeeeeeeeeeeeee",
            fold="f5",
            template=T1,
            gold_packet=gold,
            candidate_packet=cand,
            span_verifier=OK_SPAN,
        )
        got = {i.field: i.outcome for i in items}
        assert got["remaining_authorization"] == "wrong_absence"
        assert got["incremental_amount"] == "correct"


# ------------------------------------------------------------- normalisation


class TestNormalisation:
    def test_scale_word_reconciles_165_billion_with_expanded(self):
        gold = point_qty(165, quote="an increase of $165 billion")
        cand = point_qty(165000000000, quote="an increase of $165,000,000,000")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "correct"

    def test_scale_word_note_recorded(self):
        gold = point_qty(165, quote="$165 billion")
        item = grade(gold, gold, verifier=OK_SPAN)
        assert "scale_word:billion" in item.notes

    def test_percent_never_converts_to_fraction(self):
        gold = point_qty(15, quote="grew 15 percent", unit="%", basis="percent", currency="NA")
        cand = point_qty(0.15, quote="grew 0.15", unit="pct", basis="percent", currency="NA")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "wrong_value"

    def test_range_bounds_order_sensitive(self):
        gold = range_qty(100, 200)
        cand = range_qty(200, 100)
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "wrong_value"

    def test_grouping_separators_stripped_exactly(self):
        gold = point_qty(1_000_000, quote="about one million")
        cand = point_qty("1,000,000", quote="about one million")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "correct"

    def test_currency_na_vs_iso_is_mismatch(self):
        gold = point_qty(5, quote="five", currency="USD")
        cand = point_qty(5, quote="five", currency="NA")
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "mismatch:currency" in item.notes

    def test_currency_na_vs_na_is_correct(self):
        gold = point_qty(5, quote="five", unit="shares", currency="NA")
        cand = point_qty(5, quote="five", unit="share", currency="NA")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "correct"

    def test_unit_aliases_map_to_same_token(self):
        gold = point_qty(5, quote="x", unit="usd")
        cand = point_qty(5, quote="x", unit="$")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "correct"

    def test_unknown_unit_never_equals_even_itself(self):
        gold = point_qty(5, quote="x", unit="loaves")
        cand = point_qty(5, quote="x", unit="loaves")
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "unit_unknown:loaves" in item.notes
        assert "mismatch:unit" in item.notes

    def test_fy_is_not_q4(self):
        gold = point_qty(5, quote="x", period={"year": 2026, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"})
        cand = point_qty(5, quote="x", period={"year": 2026, "quarter": 4, "calendar_end": None, "period_kind": "quarter"})
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "mismatch:period" in item.notes

    def test_multi_year_compares_end_year(self):
        base = {"year": 2026, "quarter": None, "calendar_end": None, "period_kind": "multi_year", "end_year": 2030}
        no_end = {"year": 2026, "quarter": None, "calendar_end": None, "period_kind": "multi_year"}
        gold = point_qty(5, quote="x", period=base)
        assert grade(gold, point_qty(5, quote="x", period=dict(base)), verifier=OK_SPAN).outcome == "correct"
        assert grade(gold, point_qty(5, quote="x", period=no_end), verifier=OK_SPAN).outcome == "wrong_value"

    def test_period_absence_exact_schema_and_reason(self):
        gold = point_qty(5, quote="x", period=field_absence("not_stated", "period"))
        same = point_qty(5, quote="x", period=field_absence("not_stated", "period"))
        other_reason = point_qty(5, quote="x", period=field_absence("parse_failed", "period"))
        other_schema = point_qty(5, quote="x", period=owner_absence("missing_period"))
        present = point_qty(5, quote="x")
        assert grade(gold, same, verifier=OK_SPAN).outcome == "correct"
        assert grade(gold, other_reason, verifier=OK_SPAN).outcome == "wrong_value"
        assert grade(gold, other_schema, verifier=OK_SPAN).outcome == "wrong_value"
        assert grade(gold, present, verifier=OK_SPAN).outcome == "wrong_value"

    def test_bound_is_not_compared_spec_46(self):
        gold = point_qty(5, quote="x", bound="exact")
        cand = point_qty(5, quote="x", bound="approximately")
        assert grade(gold, cand, verifier=OK_SPAN).outcome == "correct"

    def test_negation_boolean_equality(self):
        gold = point_qty(5, quote="x", negated=True)
        cand = point_qty(5, quote="x", negated=False)
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "mismatch:negated" in item.notes

    def test_form_point_vs_range_mismatches(self):
        gold = point_qty(5, quote="x")
        cand = range_qty(5, 5)
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "mismatch:form" in item.notes


class TestAbsenceExactness:
    def test_same_reason_correct(self):
        assert grade(absent_qty("not_stated"), absent_qty("not_stated")).outcome == "correct"

    def test_reasons_never_collapsed(self):
        for gold_r, cand_r in [
            ("not_stated", "stated_without_number"),
            ("stated_without_number", "range_only"),
            ("range_only", "redacted_rights"),
            ("redacted_rights", "parse_failed"),
            ("parse_failed", "not_stated"),
        ]:
            item = grade(absent_qty(gold_r), absent_qty(cand_r))
            assert item.outcome == "wrong_absence", (gold_r, cand_r)
            assert "mismatch:absence_reason" in item.notes

    def test_candidate_absent_without_reason_never_matches(self):
        item = grade(absent_qty("not_stated"), {"form": "absent"})
        assert item.outcome == "wrong_absence"
        assert any(n.startswith("candidate_quantity_malformed:") for n in item.notes)


# ------------------------------------------------------------- unevidenced


class TestUnevidenced:
    def test_missing_evidence_is_unevidenced(self):
        gold = point_qty(5, quote="x")
        cand = point_qty(5, quote="x", evidence=False)
        item = grade(gold, cand, verifier=OK_SPAN)
        assert item.outcome == "unevidenced"
        assert "evidence_missing" in item.notes

    def test_failed_verifier_is_unevidenced(self):
        gold = point_qty(5, quote="x")
        item = grade(gold, point_qty(5, quote="x"), verifier=BAD_SPAN)
        assert item.outcome == "unevidenced"
        assert "span_verify_failed" in item.notes

    def test_raising_verifier_is_unevidenced(self):
        def boom(evidence):
            raise RuntimeError("replay failed")
        item = grade(point_qty(5, quote="x"), point_qty(5, quote="x"), verifier=boom)
        assert item.outcome == "unevidenced"
        assert "span_verifier_error" in item.notes

    def test_no_verifier_assumes_ok_with_note(self):
        item = grade(point_qty(5, quote="x"), point_qty(5, quote="x"))
        assert item.outcome == "correct"
        assert "span_unverified" in item.notes

    def test_unevidenced_precedence_over_gold_absent(self):
        """§4.7 order: present-but-unevidenced fires before the gold-absent branch."""
        item = grade(absent_qty("not_stated"), point_qty(5, quote="x", evidence=False))
        assert item.outcome == "unevidenced"

    def test_evidence_without_span_key_is_missing(self):
        cand = point_qty(5, quote="x")
        cand["evidence"] = {"claimed_quote": "x"}
        item = grade(point_qty(5, quote="x"), cand, verifier=OK_SPAN)
        assert item.outcome == "unevidenced"


# ---------------------------------------------------- candidate totality gap


class TestCandidateTotality:
    def test_missing_candidate_field_gold_present(self):
        item = eg.grade_critical_numeric_field(
            case_id="c", fold="f1", template=T2, field="stated_amount",
            gold_quantity=point_qty(5, quote="x"), candidate_quantity=None,
        )
        assert item.outcome == "wrong_value"
        assert "candidate_field_missing" in item.notes
        assert item.candidate_value == {"form": "missing"}

    def test_missing_candidate_field_gold_absent(self):
        item = eg.grade_critical_numeric_field(
            case_id="c", fold="f1", template=T2, field="stated_amount",
            gold_quantity=absent_qty(), candidate_quantity=None,
        )
        assert item.outcome == "wrong_absence"

    def test_non_dict_candidate_quantity(self):
        item = grade(point_qty(5, quote="x"), "bogus")
        assert item.outcome == "wrong_value"
        assert "candidate_field_malformed" in item.notes

    def test_candidate_form_outside_enum(self):
        item = grade(point_qty(5, quote="x"), {"form": "guess"})
        assert item.outcome == "wrong_value"
        assert "candidate_quantity_form_unknown:'guess'" in item.notes

    def test_candidate_unparsable_number(self):
        cand = point_qty(5, quote="x")
        cand["value"] = "not-a-number"
        item = grade(point_qty(5, quote="x"), cand, verifier=OK_SPAN)
        assert item.outcome == "wrong_value"
        assert "candidate_quantity_malformed:NUMBER_UNPARSABLE" in item.notes

    def test_candidate_packet_none_all_slots_graded(self):
        """A3 §4.9 current_news_stack: no packet -> every slot wrong_*.

        Pseudocode-strict: a gold-absent slot needs a typed absence with the
        matching reason to be correct; no packet means no absence object, so
        gold-absent slots grade wrong_absence and gold-present slots wrong_value.
        """
        gold = {
            "incremental_amount": point_qty(1, quote="x"),
            "remaining_authorization": absent_qty(),
            "executed_amount": absent_qty(),
        }
        items = eg.grade_case(
            case_id="c", fold="f1", template=T1,
            gold_packet=gold, candidate_packet=None,
        )
        assert [i.outcome for i in items] == ["wrong_value", "wrong_absence", "wrong_absence"]
        assert all("candidate_packet_absent" in i.notes for i in items)

    def test_auto_published_packetless_row_is_in_denominator(self):
        row = dict(
            case_id="case_ffffffffffffffffffffffff", fold="f1", template=T2,
            disposition="auto_published",
            gold_packet={"stated_amount": point_qty(4, quote="x")},
            candidate_packet=None,
        )
        items = eg.grade_batch([row], dispositions={"auto_published"})
        assert len(items) == 1
        assert items[0].outcome == "wrong_value"


# --------------------------------------------------------------- W3-R3 strip


class TestIngestStrips:
    def test_confidence_recorded_and_stripped(self):
        packet = {
            "stated_amount": point_qty(4, quote="x"),
            "confidence": 0.9,
            "probability": "high",
        }
        ing = eg.ingest_candidate(packet)
        assert ing.stripped_fields == ("confidence", "probability")
        assert "confidence" not in ing.packet and "probability" not in ing.packet
        item = eg.grade_case(
            case_id="c", fold="f1", template=T2,
            gold_packet={"stated_amount": point_qty(4, quote="x")},
            candidate_packet=packet, span_verifier=OK_SPAN,
        )[0]
        assert item.outcome == "correct"
        assert "ingest_stripped:confidence|probability" in item.notes

    def test_nested_forbidden_keys_stripped_with_paths(self):
        packet = {
            "stated_amount": point_qty(4, quote="x"),
            "baseline_raw": {"confidence": "high", "score": 3, "kept": 1},
            "price_target": 100,
        }
        ing = eg.ingest_candidate(packet)
        assert ing.stripped_fields == (
            "baseline_raw.confidence", "baseline_raw.score", "price_target",
        )
        assert ing.packet["baseline_raw"] == {"kept": 1}

    def test_clean_packet_untouched(self):
        packet = {"stated_amount": point_qty(4, quote="x")}
        ing = eg.ingest_candidate(packet)
        assert ing.stripped_fields == ()
        assert ing.packet == packet

    def test_none_passes_through(self):
        assert eg.ingest_candidate(None) == eg.CandidatePacket(None, ())


# ------------------------------------------------------- permutation / canon


def _batch_rows():
    return [
        dict(case_id="case_111111111111111111111111", fold="f1", template=T1,
             disposition="auto_published",
             gold_packet={"incremental_amount": point_qty(1, quote="x"),
                          "remaining_authorization": absent_qty(),
                          "executed_amount": absent_qty()},
             candidate_packet={"incremental_amount": point_qty(1, quote="x"),
                               "remaining_authorization": absent_qty(),
                               "executed_amount": absent_qty()}),
        dict(case_id="case_222222222222222222222222", fold="f2", template=T2,
             disposition="auto_published",
             gold_packet={"stated_amount": absent_qty("range_only")},
             candidate_packet={"stated_amount": point_qty(9, quote="x", evidence=False)}),
        dict(case_id="case_333333333333333333333333", fold="f3", template=T3,
             disposition="reviewed_published",
             gold_packet={"stated_quantity": absent_qty()},
             candidate_packet=None),
        dict(case_id="case_444444444444444444444444", fold="f4", template=T2,
             disposition="deferred",
             gold_packet={"stated_amount": point_qty(2, quote="x")},
             candidate_packet=None),
        dict(case_id="case_555555555555555555555555", fold="f5", template=T1,
             disposition="abstained", gold_packet=None, candidate_packet=None),
        dict(case_id="case_666666666666666666666666", fold="f2", template=T3,
             disposition="auto_published",
             gold_packet={"stated_quantity": range_qty(1, 2)},
             candidate_packet={"stated_quantity": range_qty(2, 1), "confidence": 1}),
    ]


class TestDeterminism:
    def test_permutation_invariance(self):
        baseline = eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)
        first = eg.canonical_json(eg.graded_items_to_dicts(baseline))
        rng = random.Random(20261012)
        for _ in range(5):
            rows = list(_batch_rows())
            rng.shuffle(rows)
            items = eg.grade_batch(rows, span_verifier=OK_SPAN)
            assert eg.canonical_json(eg.graded_items_to_dicts(items)) == first
        assert first == eg.canonical_json(eg.graded_items_to_dicts(eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)))

    def test_disposition_filter_changes_denominator_only(self):
        all_items = eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)
        auto_items = eg.grade_batch(_batch_rows(), dispositions={"auto_published"}, span_verifier=OK_SPAN)
        assert len(all_items) == 7  # 3 + 1 + 1 + 1 (deferred graded too) + 0 (skipped) + 1
        assert len(auto_items) == 5  # case_111 (3) + case_222 (1) + case_666 (1)
        assert {i.case_id for i in auto_items} == {
            "case_111111111111111111111111",
            "case_222222222222222222222222",
            "case_666666666666666666666666",
        }

    def test_sorted_output_order(self):
        items = eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)
        keys = [(i.case_id, i.template, i.field) for i in items]
        assert keys == sorted(keys)

    def test_canonical_json_shape(self):
        items = eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)
        blob = eg.canonical_json(eg.graded_items_to_dicts(items))
        assert blob == json.dumps(json.loads(blob), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def test_no_forbidden_key_anywhere_emitted(self):
        items = eg.grade_batch(_batch_rows(), span_verifier=OK_SPAN)
        blob = eg.canonical_json(eg.graded_items_to_dicts(items))
        for key in eg.strip_forbidden_keys(json.loads(blob))[1]:
            pytest.fail(f"forbidden key emitted: {key}")


# ------------------------------------------------------------- error codes


class TestErrorCodes:
    """W3-R5: every CODES entry asserted by exact string."""

    def test_template_not_graded(self):
        with pytest.raises(eg.EvalGradeError, match="^TEMPLATE_NOT_GRADED: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template="other.v1", gold_packet={})
        assert exc.value.code == "TEMPLATE_NOT_GRADED"

    def test_gold_packet_absent(self):
        with pytest.raises(eg.EvalGradeError, match="^GOLD_PACKET_ABSENT: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template=T2, gold_packet=None)
        assert exc.value.code == "GOLD_PACKET_ABSENT"

    def test_gold_packet_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^GOLD_PACKET_MALFORMED: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template=T2, gold_packet="x")
        assert exc.value.code == "GOLD_PACKET_MALFORMED"

    def test_gold_field_missing(self):
        with pytest.raises(eg.EvalGradeError, match="^GOLD_FIELD_MISSING: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template=T2, gold_packet={})
        assert exc.value.code == "GOLD_FIELD_MISSING"

    def test_gold_field_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^GOLD_FIELD_MALFORMED: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template=T2,
                          gold_packet={"stated_amount": {"form": "guess"}})
        assert exc.value.code == "GOLD_FIELD_MALFORMED"

    def test_gold_absence_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^GOLD_ABSENCE_MALFORMED: ") as exc:
            eg.grade_case(case_id="c", fold="f1", template=T2,
                          gold_packet={"stated_amount": {"form": "absent"}})
        assert exc.value.code == "GOLD_ABSENCE_MALFORMED"

    def test_number_unparsable(self):
        with pytest.raises(eg.EvalGradeError, match="^NUMBER_UNPARSABLE: ") as exc:
            eg.parse_number("abc")
        assert exc.value.code == "NUMBER_UNPARSABLE"
        with pytest.raises(eg.EvalGradeError):
            eg.parse_number("NaN")

    def test_quantity_form_unknown(self):
        with pytest.raises(eg.EvalGradeError, match="^QUANTITY_FORM_UNKNOWN: ") as exc:
            eg.normalise_quantity({"form": "guess"})
        assert exc.value.code == "QUANTITY_FORM_UNKNOWN"

    def test_period_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^PERIOD_MALFORMED: ") as exc:
            eg.canon_period("2026")
        assert exc.value.code == "PERIOD_MALFORMED"
        with pytest.raises(eg.EvalGradeError):
            eg.canon_period({"year": 2026})

    def test_candidate_packet_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^CANDIDATE_PACKET_MALFORMED: ") as exc:
            eg.ingest_candidate("x")
        assert exc.value.code == "CANDIDATE_PACKET_MALFORMED"

    def test_row_malformed(self):
        with pytest.raises(eg.EvalGradeError, match="^ROW_MALFORMED: ") as exc:
            eg.CaseForGrading.from_dict({"template": T2})
        assert exc.value.code == "ROW_MALFORMED"

    def test_every_code_has_a_test_and_vice_versa(self):
        tested = {
            "TEMPLATE_NOT_GRADED", "GOLD_PACKET_ABSENT", "GOLD_PACKET_MALFORMED",
            "GOLD_FIELD_MISSING", "GOLD_FIELD_MALFORMED", "GOLD_ABSENCE_MALFORMED",
            "NUMBER_UNPARSABLE", "QUANTITY_FORM_UNKNOWN", "PERIOD_MALFORMED",
            "CANDIDATE_PACKET_MALFORMED", "ROW_MALFORMED",
        }
        assert tested == set(eg.CODES)


# ------------------------------------------------------------------ totality

#: Every enum value of every graded-field component of the frozen contract.
#: form {point,range} present values; absent handled through absence_reason.
#: currency is a pattern (^([A-Z]{3}|NA)$) — a closed representative list is
#: graded (NA plus three ISO majors) and NA equality has dedicated tests.
QUANTITY_ENUM_VALUES = [
    ("form", "point"),
    ("form", "range"),
] + [
    ("bound", v) for v in ("exact", "approximately", "up_to", "at_least")
] + [
    ("basis", v) for v in ("total", "incremental", "run_rate", "per_share", "percent")
] + [
    ("period_kind", v) for v in ("quarter", "half_year", "nine_months", "fiscal_year", "multi_year")
] + [
    ("quarter", v) for v in (1, 2, 3, 4, None)
] + [
    ("negated", v) for v in (True, False)
] + [
    ("absence_reason", v) for v in (
        "not_stated", "stated_without_number", "range_only", "redacted_rights", "parse_failed"
    )
] + [
    ("period_owner_absence_reason", v) for v in (
        "no_source_document", "no_transcript", "no_primary_release",
        "no_span_addressable_evidence", "document_bytes_not_held",
        "scanned_image_no_text_layer", "unjoinable_filing_identity",
        "speaker_unresolvable", "slide_family_discontinued", "superseded_by_duplicate",
        "missing_basis", "missing_units", "unit_mismatch", "cross_check_conflict",
        "missing_period", "missing_source",
    )
] + [
    ("unit_token", v) for v in sorted(eg.UNIT_MAP) + ["loaves", "barrels"]
] + [
    ("currency", v) for v in ("USD", "EUR", "GBP", "NA")
] + [
    ("scale_word", v) for v in [w for w, _ in eg.SCALE_WORDS] + [None]
]


def _quantity_for(component: str, value):
    if component == "absence_reason":
        return absent_qty(value)
    kw = {}
    if component == "form":
        return point_qty(5, quote="x") if value == "point" else range_qty(1, 2)
    if component == "bound":
        kw["bound"] = value
    elif component == "basis":
        kw["basis"] = value
    elif component == "negated":
        kw["negated"] = value
    elif component == "unit_token":
        kw["unit"] = value
    elif component == "currency":
        kw["currency"] = value
    elif component == "scale_word":
        kw["quote"] = f"five {value} dollars" if value else "five"
    elif component == "quarter":
        kw["period"] = {"year": 2026, "quarter": value, "calendar_end": None, "period_kind": "quarter"} if value else {
            "year": 2026, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"}
    elif component == "period_kind":
        kw["period"] = {"year": 2026, "quarter": 3 if value == "quarter" else None,
                        "calendar_end": None, "period_kind": value,
                        **({"end_year": 2030} if value == "multi_year" else {})}
    elif component == "period_owner_absence_reason":
        kw["period"] = owner_absence(value)
    return point_qty(5, **kw)


@pytest.mark.parametrize("component,value", QUANTITY_ENUM_VALUES, ids=[f"{c}={v}" for c, v in QUANTITY_ENUM_VALUES])
def test_totality_over_closed_enums(component, value):
    """Every enum value of every graded field yields a defined outcome.

    Reflexive gold==candidate grades correct (except unknown-unit tokens, which
    mismatch by A7); cross scenarios stay inside the §4.7 closed outcome set and
    never raise.
    """
    gold = _quantity_for(component, value)
    same = _quantity_for(component, value)
    reflexive = grade(gold, same, verifier=OK_SPAN)
    if component == "unit_token" and value not in eg.UNIT_MAP:
        assert reflexive.outcome == "wrong_value"  # A7: unknown tokens mismatch
    else:
        assert reflexive.outcome == "correct", reflexive.notes
    assert reflexive.outcome in eg.OUTCOMES

    if component == "absence_reason":
        other = grade(absent_qty(value), point_qty(5, quote="x"), verifier=OK_SPAN)
        assert other.outcome == "wrong_absence"
        mismatch = grade(absent_qty(value), absent_qty("range_only" if value != "range_only" else "not_stated"))
        assert mismatch.outcome == "wrong_absence"
    else:
        hid = grade(gold, absent_qty(), verifier=OK_SPAN)
        assert hid.outcome == "wrong_value"
        noev = grade(gold, _no_evidence(same), verifier=OK_SPAN)
        assert noev.outcome == "unevidenced"


def _no_evidence(qty):
    clone = dict(qty)
    clone.pop("evidence", None)
    return clone


def test_totality_count():
    """Printed totality bound: every listed enum value is covered above."""
    # 2 form + 4 bound + 5 basis + 5 period_kind + 5 quarter + 2 negated
    # + 5 absence_reason + 16 owner absence reasons + 19 unit tokens
    # (17 UNIT_MAP keys + 2 unknown) + 4 currency + 9 scale words = 76 pairs.
    assert len(QUANTITY_ENUM_VALUES) == 76
    assert len({(c, v) for c, v in QUANTITY_ENUM_VALUES}) == len(QUANTITY_ENUM_VALUES)


# ------------------------------------------------- frozen contract coupling


class TestFrozenContractCoupling:
    """W3-R2: shapes that have a contracts_w3 schema validate against it.

    GradedItem/CandidatePacket have no contracts_w3 schema (none exists); the
    quantity shapes the grader consumes DO — fixtures here validate against the
    frozen contract's $defs.quantity with Draft202012Validator, and the frozen
    critical-numeric field names are cross-checked against each template's
    required list. Fails closed when the frozen contract is absent.
    """

    CONTRACT = (
        Path(__file__).resolve().parents[1] / "contracts" / "news_impact"
        / "news_impact_event.v1.schema.json"
    )

    def test_critical_fields_match_frozen_contract(self):
        import jsonschema
        assert self.CONTRACT.is_file(), f"frozen contract missing (fail closed): {self.CONTRACT}"
        root = json.loads(self.CONTRACT.read_text(encoding="utf-8"))
        for template, fields in eg.CRITICAL_NUMERIC_FIELDS.items():
            required = root["$defs"][template]["required"]
            for f in fields:
                assert f in required, (template, f)

    def test_fixture_quantities_validate_against_frozen_quantity(self):
        import jsonschema
        assert self.CONTRACT.is_file(), f"frozen contract missing (fail closed): {self.CONTRACT}"
        root = json.loads(self.CONTRACT.read_text(encoding="utf-8"))
        sub = dict(root["$defs"]["quantity"])
        sub["$defs"] = root["$defs"]
        validator = jsonschema.Draft202012Validator(sub)
        full_period = {"year": 2026, "quarter": 3, "calendar_end": None, "period_kind": "quarter"}
        ok_point = {
            "form": "point", "value": 400000000, "bound": "exact", "unit": "USD",
            "currency": "USD", "basis": "incremental", "period": full_period,
            "negated": False, "evidence": {
                "claimed_quote": "booked $400 million of incremental orders",
                "span": {
                    "schema": "source_span.v1", "authority": "context_only",
                    "span_id": "span_" + "0" * 20, "document_id": "doc_x",
                    "document_version": 1,
                    "locator": {"kind": "text_span", "sub_kind": "body",
                                "segment_index": 0, "span_start_byte": 0, "span_end_byte": 10},
                    "text_sha256": None, "display_excerpt": "booked $400 million",
                    "rights_profile": "licensed", "receipt_state": "address_only",
                    "receipt": None, "unreplayable_reason": "body bytes not held for fixture",
                },
            },
        }
        validator.validate(ok_point)
        ok_absent = {"form": "absent", "absence": field_absence("not_stated", "stated_amount")}
        validator.validate(ok_absent)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"form": "absent", "absence": field_absence("not_a_reason", "s")})
