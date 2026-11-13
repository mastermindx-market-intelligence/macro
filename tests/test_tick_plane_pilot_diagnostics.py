"""Source-owned TP-1 numeric soak diagnostics; NEVER production admission."""

import copy
import json
import unittest

from engine.tick_plane.pilot_diagnostics import (
    PilotEvidenceRefusal, summarize_tp1_soak_evidence,
)

CUTOFF=1_791_417_600_000_000_000
SOURCE_SHA="a"*64


def symbol(ticker="SPY", **overrides):
    rec=dict(
        ticker=ticker, state="ELIGIBLE", session_scope="RTH",
        reference_scope="RTH", lit_eligible_prints=1000,
        lit_classified_quote_le5s_prints=960,
        lit_classified_quote_gt5s_prints=20,
        lit_unclassified_prints=20,
        trf_prints=100,unknown_venue_prints=10,
        lit_unknown_reason_counts={
            "NO_PRIOR_NBBO":5,"QUOTE_NOT_AVAILABLE_AT_TRADE_RECEIPT":15},
        source_volume_shares="1000",reference_volume_shares="1010",
        carveout_reason=None,source_receipt="source:original:tq:SPY",
        reference_receipt="reference:original:grouped:SPY",
    )
    rec.update(overrides)
    return rec


def diag(cohort=None, **kwargs):
    values=dict(session="2026-10-08:RTH",
                expected_session_seconds=23400,
                connected_seconds=23200,
                measurement_cutoff_ns=CUTOFF+1000000,
                source_manifest_sha256=SOURCE_SHA,
                source_manifest_known_ns=CUTOFF,
                cohort=[symbol()] if cohort is None else cohort)
    values.update(kwargs)
    return summarize_tp1_soak_evidence(**values)


class PilotEvidenceTests(unittest.TestCase):
    def test_eligible_name_ratios_but_never_admission(self):
        out=diag()
        self.assertEqual(out["provisional_numeric_state"],"NUMERIC_THRESHOLDS_MET")
        self.assertEqual(out["numeric_checks"],
                         {"connected_seconds":"NUMERIC_MET",
                          "qualified_lit_quote_le5s":"NUMERIC_MET",
                          "eligible_volume_names_le2pct":"NUMERIC_MET"})
        self.assertEqual(out["n_volume_within_2pct"],1)
        self.assertEqual(out["lit_5s_classification_coverage"],"0.96")
        self.assertIsNone(out["production_source_acceptance"])
        self.assertFalse(out["enabled_to_trade_or_rank"])
        self.assertIsNone(out["absorption_signal"])
        self.assertEqual(out["source_quality_receipts_authenticity"],
                         "REQUIRES_EXTERNAL_INCUMBENT_SOURCE_PROOF")

    def test_connected_seconds_lower_than_99pct_is_numeric_failure(self):
        v=diag(connected_seconds=23000)
        self.assertEqual(v["numeric_checks"]["connected_seconds"],"NUMERIC_NOT_MET")
        self.assertEqual(v["provisional_numeric_state"],"NUMERIC_THRESHOLDS_NOT_MET")

    def test_connected_seconds_cannot_exceed_measured_session(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"exceed"):
            diag(connected_seconds=23401)

    def test_95pct_lit_quote_age_gate_measures_exact_denominator(self):
        rec=symbol(lit_classified_quote_le5s_prints=949,
                   lit_classified_quote_gt5s_prints=21,
                   lit_unclassified_prints=30,
                   lit_unknown_reason_counts={"stale":30})
        v=diag([rec])
        self.assertEqual(v["numeric_checks"]["qualified_lit_quote_le5s"],
                         "NUMERIC_NOT_MET")

    def test_known_old_classifications_cannot_count_under_5s(self):
        rec=symbol(lit_classified_quote_le5s_prints=950,
                   lit_classified_quote_gt5s_prints=50,
                   lit_unclassified_prints=0,lit_unknown_reason_counts={})
        self.assertEqual(diag([rec])["lit_5s_classification_coverage"],"0.95")

    def test_mismatch_lit_known_unknown_denominator_refused(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"denominator"):
            diag([symbol(lit_eligible_prints=999)])

    def test_missing_unknown_reasons_never_silently_counted(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"typed reasons"):
            diag([symbol(lit_unknown_reason_counts={})])

    def test_trf_stratum_not_in_lit_coverage(self):
        changed=symbol(trf_prints=5000,unknown_venue_prints=10000)
        observed=diag([changed])
        self.assertEqual(observed["lit_eligible_prints"],1000)
        self.assertEqual(observed["per_symbol_metrics"][0]["trf_prints"],5000)

    def test_grouped_full_day_reference_cannot_reconcile_rth(self):
        out=diag([symbol(reference_scope="FULL_DAY")])
        self.assertEqual(out["provisional_numeric_state"],"INSUFFICIENT_COMPARABLE_EVIDENCE")
        self.assertEqual(out["n_mismatched_reference_scope"],1)
        self.assertEqual(out["n_volume_comparable_symbols"],0)
        self.assertEqual(out["numeric_checks"]["eligible_volume_names_le2pct"],
                         "NOT_MEASURABLE")

    def test_missing_or_zero_grouped_daily_reference_is_not_volume_zero(self):
        a=diag([symbol(reference_volume_shares=None,reference_receipt=None)])
        self.assertEqual(a["n_missing_grouped_reference"],1)
        b=diag([symbol(reference_volume_shares="0")])
        self.assertEqual(b["n_zero_reference_denominator"],1)
        self.assertEqual(b["provisional_numeric_state"],"INSUFFICIENT_COMPARABLE_EVIDENCE")

    def test_halted_name_carveout_is_disclosed_not_denominator_laundered(self):
        halted=symbol("HALT",state="HALT_REOPEN_CARVEOUT",
                      carveout_reason="REAL_HALTED_SESSION")
        report=diag([symbol(),halted])
        self.assertEqual(report["n_halt_reopen_carveouts"],1)
        self.assertEqual(report["n_eligible_symbols"],1)
        self.assertEqual(report["n_volume_comparable_symbols"],1)

    def test_missing_halt_reason_refused(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"carveout reason"):
            diag([symbol(state="HALT_REOPEN_CARVEOUT")])

    def test_unqualified_name_prevents_numeric_overclaim(self):
        bad=symbol("QQQ",state="SOURCE_UNQUALIFIED",
                   carveout_reason="RAW_Q_CAPTURE_MISSING",
                   reference_volume_shares=None,reference_receipt=None)
        out=diag([symbol(),bad])
        self.assertEqual(out["n_unqualified_symbols"],1)
        self.assertEqual(out["provisional_numeric_state"],
                         "INSUFFICIENT_COMPARABLE_EVIDENCE")

    def test_per_name_90_percent_volume_success_floor(self):
        nine=[symbol("S"+str(i),source_volume_shares="1000",
                     reference_volume_shares="1000") for i in range(9)]
        failing=symbol("SF",source_volume_shares="1030",reference_volume_shares="1000")
        out=diag(nine+[failing])
        self.assertEqual(out["n_volume_comparable_symbols"],10)
        self.assertEqual(out["n_volume_within_2pct"],9)
        self.assertEqual(out["numeric_checks"]["eligible_volume_names_le2pct"],
                         "NUMERIC_MET")

    def test_volume_2pct_boundary_does_not_round_strictly_over_to_pass(self):
        # 2% + a nonzero fractional increment beyond Decimal default precision
        # must be rejected even if the displayed ratio rounds to 0.02.
        rec = symbol(source_volume_shares="102.00000000000000000000000000000001",
                     reference_volume_shares="100")
        report = diag([rec])
        self.assertEqual(report["n_volume_within_2pct"], 0)
        self.assertEqual(report["numeric_checks"]["eligible_volume_names_le2pct"],
                         "NUMERIC_NOT_MET")

    def test_volume_source_exponents_cannot_expand_at_render(self):
        for field in ("source_volume_shares", "reference_volume_shares"):
            for exponent in ("1e+999999999", "1e-999999999"):
                with self.subTest(field=field, exponent=exponent):
                    with self.assertRaisesRegex(PilotEvidenceRefusal, "bounded source decimal"):
                        diag([symbol(**{field: exponent})])

    def test_volume_2pct_inclusive_boundary(self):
        rec=symbol(source_volume_shares="102",reference_volume_shares="100")
        out=diag([rec])
        self.assertEqual(out["n_volume_within_2pct"],1)
        rec["source_volume_shares"]="102.01"
        out=diag([rec])
        self.assertEqual(out["n_volume_within_2pct"],0)

    def test_deterministic_cohort_digest_order_invariant(self):
        a=symbol("SPY");b=symbol("QQQ")
        self.assertEqual(diag([a,b])["cohort_metrics_sha256"],
                         diag([b,a])["cohort_metrics_sha256"])

    def test_repeated_symbol_rejected(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"duplicate"):
            diag([symbol("SPY"),symbol("SPY")])

    def test_wrong_source_session_cannot_masquerade_as_rth(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"source scope"):
            diag([symbol(session_scope="FULL_DAY")])

    def test_non_rth_evaluation_is_not_admitted(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"RTH only"):
            diag(session="2026-10-08:POST")

    def test_bounded_600_symbol_source_cohort(self):
        cohort=[symbol("S"+str(i),lit_eligible_prints=0,
                       lit_classified_quote_le5s_prints=0,
                       lit_classified_quote_gt5s_prints=0,
                       lit_unclassified_prints=0,lit_unknown_reason_counts={})
                for i in range(601)]
        with self.assertRaisesRegex(PilotEvidenceRefusal,"bounded"):
            diag(cohort)

    def test_malformed_future_source_evidence_is_not_accepted(self):
        with self.assertRaisesRegex(PilotEvidenceRefusal,"future source snapshot"):
            diag(source_manifest_known_ns=CUTOFF+1000001)

    def test_fractional_share_volume_is_exact(self):
        rec=symbol(source_volume_shares="100.125",reference_volume_shares="100.125")
        self.assertEqual(diag([rec])["per_symbol_metrics"][0]["volume_discrepancy"],"0")

    def test_nonfinite_or_negative_share_volume_refused(self):
        for bad in ("NaN","Infinity","-10"):
            with self.subTest(value=bad),self.assertRaisesRegex(PilotEvidenceRefusal,"invalid nonnegative"):
                diag([symbol(source_volume_shares=bad)])

    def test_zero_lit_population_cannot_claim_95pct(self):
        rec=symbol(lit_eligible_prints=0,lit_classified_quote_le5s_prints=0,
                   lit_classified_quote_gt5s_prints=0,lit_unclassified_prints=0,
                   lit_unknown_reason_counts={})
        out=diag([rec])
        self.assertEqual(out["numeric_checks"]["qualified_lit_quote_le5s"],
                         "NOT_MEASURABLE")
        self.assertEqual(out["provisional_numeric_state"],
                         "INSUFFICIENT_COMPARABLE_EVIDENCE")



from engine.tick_plane.rth_minute_reference import (
    normalize_rth_minute_volume_reference, FrameContractError as RTHReferenceError,
    MINUTE_NS,
)

RTH_START=1_791_417_600_000_000_000
RTH_START-=RTH_START%MINUTE_NS


def mock_minute_original(*, rows=None, **changes):
    if rows is None:
        rows=[
            {"t":RTH_START//1_000_000,"v":12.375,"n":4},
            {"t":(RTH_START+MINUTE_NS)//1_000_000,"v":7.625,"n":2},
        ]
    body={"status":"OK","ticker":"SPY","request_id":"original-rest-response",
          "results":rows,"resultsCount":len(rows),"adjusted":False}
    body.update(changes)
    return json.dumps(body,separators=(",",":")).encode()


def reference(rows=None, **changes):
    packet=mock_minute_original(rows=rows)
    opts=dict(
        original_response_bytes=packet,
        ticker="SPY",session="2026-10-08:RTH",
        rth_start_ns=RTH_START,
        rth_end_ns=RTH_START+2*MINUTE_NS,
        expected_rth_minutes=2,
        source_received_ns=RTH_START+3*MINUTE_NS,
        source_receipt_id="synthetic-original-rest-bytes",
        source_query_receipt="synthetic-original-exact-rth-query",
        calendar_receipt="reviewed-existing-calendar",
        volume_semantics_receipt="reviewed-source-volume-update-parity",
        calendar_scope_reviewed=True,
        exact_query_range_reviewed=True,
        complete_pagination_reviewed=True,
        minute_volume_semantics_reviewed=True,
    )
    opts.update(changes)
    return normalize_rth_minute_volume_reference(**opts)


class SameScopeRTHMinuteReferenceTests(unittest.TestCase):
    def test_rest_minute_json_numeric_parser_failure_is_typed(self):
        raw = mock_minute_original()
        for packet in [
            raw.replace(b"12.375", b"1e999999999999999999999999999"),
            raw.replace(b'"n":4', b'"n":' + b"9" * 5000),
        ]:
            with self.subTest(raw_size=len(packet)):
                with self.assertRaisesRegex(RTHReferenceError, "malformed original REST minute response"):
                    reference(original_response_bytes=packet)

    def test_extreme_source_volume_exponent_never_expands(self):
        for exponent in ("1e+999999999", "1e-999999999"):
            with self.subTest(exponent=exponent):
                with self.assertRaisesRegex(RTHReferenceError, "fixed decimal exceeds"):
                    reference(rows=[{"t": RTH_START // 1_000_000, "v": exponent}])

    def test_exact_native_decimals_sum_over_reviewed_rth_only(self):
        r=reference()
        self.assertEqual(r["reference_scope"],"RTH")
        self.assertEqual(r["reference_volume_shares"],"20.000")
        self.assertEqual(r["reference_state"],
                         "CANDIDATE_SAME_SCOPE_EXTERNAL_PROOF_REQUIRED")
        self.assertFalse(r["reference_source_available_at_original_decision"])
        self.assertIsNone(r["acceptance_authority"])
        self.assertEqual(r["original_vendor_receipt_authenticity"],
                         "REQUIRES_INCUMBENT_OWNER_VERIFICATION")

    def test_missing_native_query_review_does_not_generate_comparable_volume(self):
        r=reference(exact_query_range_reviewed=False)
        self.assertIsNone(r["reference_volume_shares"])
        self.assertEqual(r["reference_state"],"UNQUALIFIED_MISSING_SOURCE_REVIEW")
        self.assertEqual(r["observed_unadmitted_volume_shares_private_only"],"20.000")

    def test_native_minute_volume_rule_parity_review_must_be_explicit(self):
        r=reference(minute_volume_semantics_reviewed=False)
        self.assertIsNone(r["reference_volume_shares"])

    def test_sparse_source_does_not_silently_fake_bars(self):
        r=reference(rows=[{"t":RTH_START//1_000_000,"v":"5.25"}])
        self.assertEqual(r["actual_minute_records"],1)
        self.assertEqual(r["missing_minute_rows"],1)
        self.assertEqual(r["reference_volume_shares"],"5.25")

    def test_empty_complete_minute_response_can_sum_zero_but_never_proves_source(self):
        r=reference(rows=[])
        self.assertEqual(r["reference_volume_shares"],"0")
        self.assertEqual(r["missing_minute_rows"],2)
        self.assertFalse(r["native_volume_eligibility_automatically_validated"])

    def test_full_day_outside_rth_bar_refused(self):
        outside={"t":(RTH_START-10*MINUTE_NS)//1_000_000,"v":500}
        with self.assertRaisesRegex(RTHReferenceError,"does not match exact RTH"):
            reference(rows=[outside])

    def test_unadjusted_daily_aggregate_is_not_minute_reference(self):
        daily={"status":"OK","ticker":"SPY","adjusted":False,
               "results":[{"T":RTH_START//1_000_000,"v":1000}],
               "resultsCount":1}
        with self.assertRaisesRegex(RTHReferenceError,"native integer"):
            reference(original_response_bytes=json.dumps(daily).encode())

    def test_duplicate_source_minute_not_double_counted(self):
        dup={"t":RTH_START//1_000_000,"v":"10"}
        with self.assertRaisesRegex(RTHReferenceError,"duplicate source minute"):
            reference(rows=[dup,dup])

    def test_fractional_non_integer_source_volume_is_exact(self):
        rows=[{"t":RTH_START//1_000_000,"v":0.125},
              {"t":(RTH_START+MINUTE_NS)//1_000_000,"v":"0.375"}]
        self.assertEqual(reference(rows=rows)["reference_volume_shares"],"0.500")

    def test_incomplete_rest_query_pagination_cannot_be_promoted(self):
        packet=mock_minute_original(next_url="https://api.massive.com/next")
        with self.assertRaisesRegex(RTHReferenceError,"pagination incomplete"):
            reference(original_response_bytes=packet)

    def test_inconsistent_results_count_refused(self):
        packet=mock_minute_original(resultsCount=3)
        with self.assertRaisesRegex(RTHReferenceError,"returned-count"):
            reference(original_response_bytes=packet)

    def test_foreign_ticker_cannot_supply_spy_reference(self):
        packet=mock_minute_original(ticker="QQQ")
        with self.assertRaisesRegex(RTHReferenceError,"ticker differs"):
            reference(original_response_bytes=packet)

    def test_post_session_venue_rest_receipt_never_becomes_original_intraday(self):
        r=reference(source_received_ns=RTH_START+10*MINUTE_NS)
        self.assertGreater(r["source_received_ns"],r["rth_end_ns"])
        self.assertFalse(r["reference_source_available_at_original_decision"])

    def test_reference_cannot_predate_source_session_end(self):
        with self.assertRaisesRegex(RTHReferenceError,"calendar disagree"):
            reference(source_received_ns=RTH_START+MINUTE_NS)

    def test_unknown_requested_calendar_wont_admit_numeric_reference(self):
        r=reference(calendar_scope_reviewed=False)
        self.assertIsNone(r["reference_volume_shares"])

    def test_external_referenced_volume_works_only_with_explicit_rth_scope(self):
        native=reference()
        row=symbol(reference_scope=native["reference_scope"],
                   source_volume_shares=native["reference_volume_shares"],
                   reference_volume_shares=native["reference_volume_shares"],
                   reference_receipt=native["source_receipt_id"])
        out=diag([row])
        self.assertEqual(out["n_volume_within_2pct"],1)
        self.assertIsNone(out["production_source_acceptance"])


    def test_rth_session_requires_exact_day_and_label(self):
        for invalid in ("2026-10-08:EXT:RTH","not-a-date:RTH","2026-10-08:POST"):
            with self.subTest(session=invalid),self.assertRaises(RTHReferenceError):
                reference(session=invalid)

    def test_original_adjusted_flag_must_be_unadjusted_boolean(self):
        with self.assertRaisesRegex(RTHReferenceError,"adjusted aggregate volume"):
            reference(original_response_bytes=mock_minute_original(adjusted=True))
        with self.assertRaisesRegex(RTHReferenceError,"ambiguous native adjusted"):
            reference(original_response_bytes=mock_minute_original(adjusted="false"))

    def test_missing_native_adjustment_field_cannot_be_silently_unadjusted(self):
        body=json.loads(mock_minute_original())
        del body["adjusted"]
        with self.assertRaisesRegex(RTHReferenceError,"missing or ambiguous native adjusted"):
            reference(original_response_bytes=json.dumps(body).encode())

    def test_even_empty_pagination_cursor_is_unreviewed_incomplete(self):
        packet=mock_minute_original(next_url="")
        with self.assertRaisesRegex(RTHReferenceError,"pagination incomplete"):
            reference(original_response_bytes=packet)

    def test_reference_cannot_synthesize_receive_time_from_event_timestamp(self):
        with self.assertRaisesRegex(RTHReferenceError,"calendar disagree"):
            reference(source_received_ns=RTH_START-1)
    def test_full_day_daily_volume_still_cannot_masquerade_as_rth(self):
        annual=symbol(reference_scope="FULL_DAY",
                      reference_volume_shares="30",
                      source_volume_shares="20")
        out=diag([annual])
        self.assertEqual(out["n_mismatched_reference_scope"],1)
        self.assertEqual(out["provisional_numeric_state"],
                         "INSUFFICIENT_COMPARABLE_EVIDENCE")

if __name__=="__main__":
    unittest.main()
