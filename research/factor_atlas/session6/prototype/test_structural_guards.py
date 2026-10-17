"""Independent, hand-constructed adversarial synthetic fixtures for S6 guards."""

from dataclasses import replace
from decimal import Decimal as D
import unittest

from structural_guards import (
    NOT_ADMITTED, BLOCKED, MinuteClaim, BaselineObservation, PrintQuoteClaim,
    LossRow, aggregate_synthetic, assess_minute, assess_quote_reference,
    brier_diagnostic_only, check_prior_baseline,
)


MIN = 60_000_000_000


def valid(**edits):
    base = MinuteClaim(
        factor_id="AI", security_id="SEC:NVDA", minute_start_ns=10*MIN,
        minute_end_ns=11*MIN, cutoff_ns=12*MIN,
        source_known_ns=11*MIN+100, reader_complete_ns=11*MIN+200,
        membership_known_ns=1, revision_id="r0", monetary_basis_id="raw-2026",
        corporate_action_vintage="ca-v1", rights_claim="PERMITTED_BY_OWNER",
        finality_claim="FINAL_AS_KNOWN", gross_notional=D("250"),
        signed_pressure=D("45"), weight=D(".50"),
        label_start_ns=13*MIN, label_end_ns=18*MIN,
    )
    return replace(base, **edits)


class StructuralGuardsTest(unittest.TestCase):
    def reasons(self, claim):
        return assess_minute(claim).reasons

    def test_full_metadata_never_source_admits_or_releases(self):
        result = assess_minute(valid())
        self.assertEqual(result.status, NOT_ADMITTED)
        self.assertFalse(result.rights_approved)
        self.assertFalse(result.source_authenticated)
        self.assertFalse(result.prediction_authorized)
        self.assertFalse(result.publication_authorized)

    def test_future_reader_blocked(self):
        self.assertIn("FEATURE_AFTER_CUTOFF", self.reasons(valid(reader_complete_ns=13*MIN)))

    def test_future_member_blocked(self):
        self.assertIn("FUTURE_MEMBERSHIP", self.reasons(valid(membership_known_ns=13*MIN)))

    def test_source_pre_bar_end_blocked(self):
        self.assertIn("SOURCE_BEFORE_BAR_END", self.reasons(valid(source_known_ns=10*MIN)))

    def test_invalid_source_reader_order(self):
        self.assertIn("READER_BEFORE_SOURCE", self.reasons(valid(reader_complete_ns=11*MIN)))

    def test_correction_later_than_cutoff_not_earlier_truth(self):
        self.assertIn("CORRECTION_AFTER_CUTOFF", self.reasons(valid(last_correction_known_ns=14*MIN)))

    def test_restricted_and_unknown_rights_fail(self):
        for state in ("DENIED", "UNKNOWN", ""):
            with self.subTest(state=state):
                self.assertIn("RIGHTS_NOT_CLAIMED", self.reasons(valid(rights_claim=state)))

    def test_corporate_action_basis_missing(self):
        self.assertIn("UNPROVEN_MONETARY_BASIS", self.reasons(valid(corporate_action_vintage=None)))

    def test_missing_flow_is_not_zero(self):
        self.assertIn("MISSING_GROSS_NOTIONAL", self.reasons(valid(gross_notional=None)))
        self.assertEqual(assess_minute(valid(gross_notional=D(0),signed_pressure=D(0))).status, NOT_ADMITTED)

    def test_sign_exceeding_gross_invalid(self):
        self.assertIn("SIGN_EXCEEDS_GROSS", self.reasons(valid(signed_pressure=D("251"))))

    def test_nonfinite_decimal_and_float_rejected(self):
        self.assertIn("INVALID_GROSS_NOTIONAL", self.reasons(valid(gross_notional=D("NaN"))))
        self.assertIn("INVALID_GROSS_NOTIONAL", self.reasons(valid(gross_notional=1.1)))

    def test_bad_weights_rejected(self):
        self.assertIn("INVALID_MEMBERSHIP_WEIGHT", self.reasons(valid(weight=D("1.05"))))

    def test_label_before_decision_rejected(self):
        self.assertIn("OUTCOME_NOT_FUTURE", self.reasons(valid(label_start_ns=12*MIN)))

    def test_early_label_end_rejected(self):
        self.assertIn("INVALID_LABEL_WINDOW", self.reasons(valid(label_end_ns=13*MIN-1)))

    def test_one_minute_exactness(self):
        self.assertIn("INVALID_MINUTE_SPAN", self.reasons(valid(minute_end_ns=11*MIN+1)))

    def test_shared_security_overlapping_themes_unique_dollars(self):
        a = valid()
        b = valid(factor_id="SEMIS", weight=D(".25"))
        result = aggregate_synthetic([a,b])
        self.assertEqual(result.status, NOT_ADMITTED)
        self.assertEqual(result.unique_raw_gross, D("250"))
        self.assertEqual(result.duplicated_raw_gross, D("250"))
        self.assertEqual(dict(result.per_factor_allocated), {"AI":D("125"),"SEMIS":D("62.50")})
        self.assertFalse(result.prediction_authorized)

    def test_duplicate_factor_security_minute_rejected(self):
        r = aggregate_synthetic([valid(),valid()])
        self.assertEqual(r.status, BLOCKED)
        self.assertIn("DUPLICATE_FACTOR_SECURITY_MINUTE", r.reasons)

    def test_overlap_with_conflicting_source_revision_rejected(self):
        r = aggregate_synthetic([valid(),valid(factor_id="SEMIS",revision_id="r1")])
        self.assertIn("CONFLICTING_SHARED_MEMBER_SOURCE", r.reasons)

    def test_missing_member_invalidates_entire_union(self):
        r = aggregate_synthetic([valid(),valid(factor_id="SEMIS",gross_notional=None)])
        self.assertEqual(r.unique_raw_gross, None)
        self.assertEqual(r.status, BLOCKED)

    def baseline(self, **kwargs):
        return [BaselineObservation(f"old-{i}", i, D(i*i+1)) for i in range(20)]

    def test_valid_past_baseline_is_still_unadmitted(self):
        a = check_prior_baseline("current",1000,self.baseline())
        self.assertEqual(a.status, NOT_ADMITTED)
        self.assertGreater(a.mad, 0)
        self.assertFalse(a.source_authenticated)

    def test_baseline_same_minute_guard(self):
        rows = self.baseline()
        rows[3] = replace(rows[3],source_row_id="current")
        a = check_prior_baseline("current",1000,rows)
        self.assertIn("SAME_MINUTE_SELF_CONTAMINATION", a.reasons)

    def test_baseline_future_vintage_guard(self):
        rows = self.baseline()
        rows[-1] = replace(rows[-1],known_ns=1001)
        self.assertIn("BASELINE_FUTURE_KNOWLEDGE",check_prior_baseline("current",1000,rows).reasons)

    def test_baseline_zero_mad_withheld(self):
        rows = [BaselineObservation(str(i), i, D("2")) for i in range(20)]
        a = check_prior_baseline("current",1000,rows)
        self.assertIn("ZERO_MAD_UNDEFINED_Z",a.reasons)
        self.assertEqual(a.status, BLOCKED)

    def test_baseline_short_history_and_duplicate(self):
        rows = self.baseline()
        self.assertIn("INSUFFICIENT_HISTORY",check_prior_baseline("cur",1000,rows[:19]).reasons)
        rows[0] = replace(rows[0],source_row_id=rows[1].source_row_id)
        self.assertIn("DUPLICATE_BASELINE_MEMBER",check_prior_baseline("cur",1000,rows).reasons)

    def quote(self, **kwargs):
        base=PrintQuoteClaim(
            print_time_ns=100_000,quote_time_ns=99_000,source_receipt_ns=100_500,
            cutoff_ns=101_000,quote_age_limit_ns=10_000,
            print_condition="ELIGIBLE_REGULAR",correction_state="FINAL_UNCORRECTED",
            signed_notional=D("22"),
        )
        return replace(base,**kwargs)

    def test_quote_signed_heuristic_never_authoritative(self):
        a=assess_quote_reference(self.quote())
        self.assertEqual(a.status,NOT_ADMITTED)
        self.assertFalse(a.source_authenticated)

    def test_quote_after_print_and_equal_clock_rejected(self):
        for ts in (100_000,100_010):
            self.assertIn("QUOTE_NOT_STRICTLY_PRIOR", assess_quote_reference(self.quote(quote_time_ns=ts)).reasons)

    def test_quote_stale_and_undelivered_rejected(self):
        self.assertIn("STALE_QUOTE",assess_quote_reference(self.quote(quote_time_ns=0)).reasons)
        self.assertIn("SOURCE_RECEIPT_AFTER_CUTOFF",assess_quote_reference(self.quote(source_receipt_ns=102_000)).reasons)

    def test_quote_future_print_rejected(self):
        result=assess_quote_reference(self.quote(print_time_ns=101_500,source_receipt_ns=101_600))
        self.assertIn("PRINT_AFTER_CUTOFF",result.reasons)

    def test_quote_receipt_before_print_rejected(self):
        self.assertIn("RECEIPT_BEFORE_PRINT",assess_quote_reference(self.quote(source_receipt_ns=99_999)).reasons)

    def test_cancelled_print_not_signed(self):
        self.assertIn("UNKNOWN_OR_CORRECTED_PRINT",assess_quote_reference(self.quote(correction_state="CANCELLED")).reasons)

    def test_missing_quote_unknown_not_zero(self):
        self.assertIn("UNKNOWN_QUOTE_OR_RECEIPT",assess_quote_reference(self.quote(quote_time_ns=None)).reasons)

    def test_null_estimator_baseline_has_zero_increment(self):
        rows=[LossRow(str(i),i%2,D(".5"),D(".5")) for i in range(20)]
        out=brier_diagnostic_only(rows)
        self.assertEqual(out.average_paired_brier_gain,D(0))
        self.assertEqual(out.status,NOT_ADMITTED)
        self.assertFalse(out.prediction_authorized)
        self.assertEqual(out.inference_status,"NO_P_VALUE_NO_CI_NOT_A_VALIDATION")

    def test_perfect_looking_in_sample_does_not_validate(self):
        rows=[LossRow(str(i),i%2,D(".5"),D(i%2)) for i in range(20)]
        out=brier_diagnostic_only(rows)
        self.assertGreater(out.average_paired_brier_gain,D(0))
        self.assertFalse(out.prediction_authorized)

    def test_duplicate_pseudo_independent_episode_refused(self):
        rows=[LossRow("same",1,D(".5"),D(".6"))]*500
        self.assertEqual(brier_diagnostic_only(rows).status,BLOCKED)

    def test_brier_invalid_probability_refused(self):
        rows=[LossRow("a",1,D(".5"),D("1.01"))]
        self.assertEqual(brier_diagnostic_only(rows).status,BLOCKED)

    def test_brier_invalid_label_refused(self):
        self.assertEqual(brier_diagnostic_only([LossRow("a",2,D(".5"),D(".6"))]).status,BLOCKED)


if __name__ == "__main__":
    unittest.main()
