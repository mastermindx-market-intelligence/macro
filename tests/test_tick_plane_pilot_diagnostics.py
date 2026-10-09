"""Source-owned TP-1 numeric soak diagnostics; NEVER production admission."""

import copy
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


if __name__=="__main__":
    unittest.main()
