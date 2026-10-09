"""Minute projection preserves provisional and point-in-time source semantics."""
import copy
import unittest
from decimal import Decimal

from engine.tick_plane.minute_projection import (
    MINUTE_NS, MinuteProjectionRefusal, project_provisional_minute,
)

M=1_791_417_600_000_000_000
M-=M%MINUTE_NS
CUT=M+90_000_000_000
WM="combined-tq:proven-by-owner"
RULE="a"*64

def row(key="t1", *,t=None,state="MEASURED_SOURCE_PROXY",side="buy",
        gross="100.50",venue="LIT",reason=None,available=None):
    value={"schema":"equity.tick_plane.provisional_print_observation/v0",
           "state":state,"reason":reason,"ticker":"SPY","session":"2026-10-08:RTH",
           "trade_id":key,"dedup_key":key,
           "original_available_ns":M+31_000_000_000 if available is None else available,
           "trade_sip_timestamp_ns":M+30_000_000_000 if t is None else t,
           "decision_ns":CUT,"source_watermark_receipt":WM,
           "trade_conditions_rules_ref":RULE,
           "trade_condition_policy_reason":"CONSERVATIVE_PRICE_FORMING_CANDIDATE",
           "quote_conditions_rules_ref":"c"*64,
           "quote_source_receipt_id":"quote-ref","matched_quote_id":"Q1",
           "quote_age_ns":500_000,"quote_age_limit_ns":50_000_000,
           "source_trade_conditions":[0],
           "venue_class":venue,
           "venue_reference_sha256":"b"*64,
           "venue_admission_reason":"SOURCE_REFERENCE_EXCHANGE_CANDIDATE",
           "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
           "gross_observed_notional_usd":gross,
           "gross_source_shares":"1.00", "trade_volume_eligible":True,
           "side_proxy":side,
           "signed_notional_usd":gross if side=="buy" else
                                 "-"+gross if side=="sell" else None,
           "authority":"OBSERVATIONAL_PROVISIONAL_ONLY",
           "forward_response_label":None,"absorption_signal":None}
    if state!="MEASURED_SOURCE_PROXY":
        value["side_proxy"]="unclassified"
        value["signed_notional_usd"]=None
        value["reason"]=reason or "SOURCE_UNKNOWN"
    return value

def kwargs(observations=None,**rest):
    d=dict(ticker="SPY",session="2026-10-08:RTH",start_ns=M,
           decision_ns=CUT,source_complete_through_ns=M+MINUTE_NS,
           watermark_available_ns=M+75_000_000_000,
           watermark_receipt_id=WM,source_completeness_attested=True,
           observations=[row()] if observations is None else observations)
    d.update(rest)
    return d

def run(observations=None,**rest):
    return project_provisional_minute(**kwargs(observations,**rest))

class ProjectionTests(unittest.TestCase):
    def test_qualified_buy_sell_mid_and_unknown_are_separate(self):
        rows=[row("buy",gross="100.50"),row("sell",side="sell",gross="30.25"),
              row("mid",side="mid",gross="20.00"),
              row("unknown",state="UNKNOWN",reason="INVALID_OR_ONE_SIDED_NBBO",gross="5.00"),
              row("off",state="UNKNOWN",reason="TRF_OR_VENUE_CLOCK_UNQUALIFIED",
                  venue="TRF",gross="1000.00"),
              row("excluded",state="INELIGIBLE",reason="TRADE_CONDITION_EXCLUDED",
                  gross="200.00")]
        result=run(rows)
        self.assertEqual(result["state"],"PROVISIONAL_MEASURED_CONTEXT")
        self.assertEqual(result["n_sampled_prints"],6)
        self.assertEqual(result["n_trf"],1)
        self.assertEqual(result["buy_proxy_notional_usd"],"100.50")
        self.assertEqual(result["sell_proxy_notional_usd"],"30.25")
        self.assertEqual(result["midpoint_notional_usd"],"20.00")
        self.assertEqual(result["unknown_notional_usd"],"1005.00")
        self.assertEqual(result["ineligible_notional_usd"],"200.00")
        self.assertEqual(result["trf_gross_notional_usd"],"1000.00")
        self.assertEqual(Decimal(result["lit_quoted_notional_coverage"]),
                         Decimal("150.75") / Decimal("155.75"))
        self.assertIsNone(result["absorption_signal"])
        self.assertIsNone(result["market_capture_coverage"])
        self.assertNotIn("trade_id",result)

    def test_unattested_source_makes_no_zero_activity_claim(self):
        v=run(source_completeness_attested=False)
        self.assertEqual(v["state"],"SOURCE_NOT_QUALIFIED")
        self.assertNotIn("gross_sampled_notional_usd",v)

    def test_unmatured_window_does_not_emit_finalized_notional(self):
        v=run(source_complete_through_ns=M+MINUTE_NS-1)
        self.assertEqual(v["state"],"NOT_MATURE")
        self.assertNotIn("n_sampled_prints",v)

    def test_empty_source_sample_is_not_zero_market_volume(self):
        v=run([])
        self.assertEqual(v["state"],"NO_SAMPLED_PRINTS")
        self.assertNotIn("gross_sampled_notional_usd",v)

    def test_event_beyond_minute_is_rejected(self):
        with self.assertRaisesRegex(MinuteProjectionRefusal,"outside minute"):
            run([row(t=M+MINUTE_NS)])

    def test_future_receipt_cannot_be_backfilled(self):
        with self.assertRaisesRegex(MinuteProjectionRefusal,"unavailable"):
            run([row(available=CUT+1)])

    def test_native_source_identity_cannot_change_between_records(self):
        bad=row("other")
        bad["session"]="2026-10-07:RTH"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"identity"):
            run([bad])

    def test_source_watermark_receipt_mismatch_is_refused(self):
        bad=row()
        bad["source_watermark_receipt"]="replacement"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"cutoff"):
            run([bad])

    def test_duplicate_observed_print_is_idempotent(self):
        obs=row()
        a=run([obs])
        b=run([copy.deepcopy(obs),obs])
        self.assertEqual(a["source_observation_sha256"],b["source_observation_sha256"])
        self.assertEqual(b["n_sampled_prints"],1)

    def test_conflicting_duplicate_print_never_collapses_to_mean(self):
        a=row()
        b=row(gross="200.00")
        with self.assertRaisesRegex(MinuteProjectionRefusal,"conflicting duplicate"):
            run([a,b])

    def test_off_exchange_qualifying_signed_print_is_rejected(self):
        with self.assertRaisesRegex(MinuteProjectionRefusal,"off-exchange"):
            run([row(venue="TRF")])

    def test_tampered_sign_notional_is_rejected(self):
        bad=row()
        bad["signed_notional_usd"]="1000000000"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"disagrees"):
            run([bad])

    def test_fractional_notional_exact(self):
        obs=row(gross="37.5750")
        x=run([obs])
        self.assertEqual(x["gross_sampled_notional_usd"],"37.5750")

    def test_raw_trade_and_quote_additions_rejected(self):
        x=row()
        x["raw_websocket_payload"]="UNLICENSED"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"exact incumbent"):
            run([x])

    def test_premature_decision_or_watermark_is_null(self):
        self.assertEqual(run(decision_ns=M+MINUTE_NS-1)["state"],"NOT_MATURE")
        self.assertEqual(run(watermark_available_ns=CUT+1)["state"],"NOT_MATURE")

    def test_retroactively_final_correction_state_refused(self):
        r=row()
        r["correction_status"]="FINAL"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"correction"):
            run([r])

    def test_mixed_condition_generations_refused(self):
        bad=row("second")
        bad["trade_conditions_rules_ref"]="b"*64
        with self.assertRaisesRegex(MinuteProjectionRefusal,"mixed condition"):
            run([row(),bad])

    def test_source_observation_digest_order_invariant(self):
        a=row("a",t=M+1_000_000_000)
        b=row("b",t=M+2_000_000_000)
        self.assertEqual(run([a,b])["source_observation_sha256"],
                         run([b,a])["source_observation_sha256"])

    def test_midpoint_signed_notional_must_stay_null(self):
        r=row(side="mid")
        r["signed_notional_usd"]="2"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"midpoint"):
            run([r])

    def test_absolute_ns_minute_alignment_required(self):
        with self.assertRaisesRegex(MinuteProjectionRefusal,"align"):
            run(start_ns=M+1)


    def test_malformed_signed_print_is_a_typed_refusal(self):
        record=row()
        record["signed_notional_usd"]="not-a-number"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"malformed signed"):
            run([record])

    def test_infinite_signed_notional_is_not_accepted(self):
        record=row()
        record["signed_notional_usd"]="Infinity"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"disagrees"):
            run([record])


    def test_mixed_exchange_reference_generations_refused(self):
        other=row("other")
        other["venue_reference_sha256"]="c"*64
        with self.assertRaisesRegex(MinuteProjectionRefusal,"mixed exchange"):
            run([row(),other])

    def test_exchange_reference_receipt_retained_in_minute_projection(self):
        output=run()
        self.assertEqual(output["exchange_reference_sha256"],"b"*64)


    def test_quote_policy_generation_is_required_for_signed_print(self):
        r=row()
        r["quote_conditions_rules_ref"]=None
        with self.assertRaisesRegex(MinuteProjectionRefusal,"measured print missing"):
            run([r])

    def test_mixed_quote_condition_policy_generations_refused(self):
        a=row("a")
        b=row("b")
        b["quote_conditions_rules_ref"]="d"*64
        with self.assertRaisesRegex(MinuteProjectionRefusal,"mixed quote condition"):
            run([a,b])

    def test_quote_policy_digest_is_preserved_in_minute(self):
        result=run()
        self.assertEqual(result["quote_condition_rules_sha256"],"c"*64)

    def test_unknown_print_without_qualified_quote_policy_stays_unknown(self):
        value=row(state="UNKNOWN",reason="QUOTE_CONDITION_POLICY_UNQUALIFIED")
        value["quote_conditions_rules_ref"]=None
        result=run([value])
        self.assertEqual(result["state"],"PROVISIONAL_MEASURED_CONTEXT")
        self.assertIsNone(result["quote_condition_rules_sha256"])
        self.assertEqual(result["unknown_notional_usd"],"100.50")


    def test_minute_retains_actual_source_quote_age_policy(self):
        result=run()
        self.assertEqual(result["max_quote_age_ns"],50_000_000)

    def test_two_prints_with_mixed_quote_age_policy_fail_closed(self):
        first=row("first")
        second=row("second")
        second["quote_age_limit_ns"]=1_000_000_000
        with self.assertRaisesRegex(MinuteProjectionRefusal,"mixed quote-age"):
            run([first,second])

    def test_unqualified_quote_age_policy_never_promotes_signed_print(self):
        first=row()
        first["quote_age_limit_ns"]=None
        with self.assertRaisesRegex(MinuteProjectionRefusal,"nonnegative integer"):
            run([first])


    def test_lit_eligible_5s_coverage_uses_observed_quote_age_not_policy_limit(self):
        actual=run()
        self.assertEqual(actual["n_lit_eligible_prints"],1)
        self.assertEqual(actual["n_lit_classified_quote_le5s_prints"],1)
        self.assertEqual(actual["n_lit_classified_quote_gt5s_prints"],0)
        self.assertEqual(actual["n_lit_unclassified_prints"],0)
        self.assertEqual(actual["lit_unknown_reason_counts"],{})

    def test_exact_5s_quote_age_is_on_eligible_side_of_boundary(self):
        value=row()
        value["quote_age_ns"]=5_000_000_000
        value["quote_age_limit_ns"]=6_000_000_000
        outcome=run([value])
        self.assertEqual(outcome["n_lit_classified_quote_le5s_prints"],1)
        self.assertEqual(outcome["n_lit_classified_quote_gt5s_prints"],0)

    def test_above_5s_classified_quote_does_not_count_for_soak_floor(self):
        value=row()
        value["quote_age_ns"]=5_000_000_001
        value["quote_age_limit_ns"]=6_000_000_000
        outcome=run([value])
        self.assertEqual(outcome["n_lit_classified_quote_le5s_prints"],0)
        self.assertEqual(outcome["n_lit_classified_quote_gt5s_prints"],1)

    def test_abstained_lit_quote_is_in_unknown_denominator(self):
        value=row(state="UNKNOWN",reason="QUOTE_NOT_AVAILABLE_AT_TRADE_RECEIPT")
        outcome=run([value])
        self.assertEqual(outcome["n_lit_eligible_prints"],1)
        self.assertEqual(outcome["n_lit_unclassified_prints"],1)
        self.assertEqual(outcome["n_lit_classified_quote_le5s_prints"],0)
        self.assertEqual(outcome["lit_unknown_reason_counts"],
                         {"QUOTE_NOT_AVAILABLE_AT_TRADE_RECEIPT":1})

    def test_unknown_sale_condition_not_silent_eligible_lit_trade(self):
        value=row(state="UNKNOWN",reason="TRADE_CONDITION_POLICY_UNQUALIFIED")
        value["trade_condition_policy_reason"]="UNKNOWN_OR_INVALID_CONDITION_CODE"
        outcome=run([value])
        self.assertEqual(outcome["n_lit_eligible_prints"],0)
        self.assertEqual(outcome["n_lit_source_unqualified_prints"],1)

    def test_measured_print_must_have_source_sale_and_venue_admission(self):
        for key in ("trade_condition_policy_reason","venue_admission_reason"):
            with self.subTest(field=key):
                value=row()
                value[key]="UNQUALIFIED_SOURCE"
                with self.assertRaisesRegex(MinuteProjectionRefusal,"sale/venue admission"):
                    run([value])

    def test_quote_age_exceeding_source_policy_is_a_integrity_failure(self):
        value=row()
        value["quote_age_limit_ns"]=20
        value["quote_age_ns"]=21
        with self.assertRaisesRegex(MinuteProjectionRefusal,"exceeds its declared limit"):
            run([value])

    def test_lit_quote_age_requires_native_integer_clock(self):
        value=row()
        value["quote_age_ns"]=5_000_000_000.0
        with self.assertRaisesRegex(MinuteProjectionRefusal,"qualified quote age"):
            run([value])

    def test_trf_volume_not_folded_into_lit_quote_coverage(self):
        lit=row("lit")
        trf=row("off",state="UNKNOWN",reason="TRF_OR_VENUE_CLOCK_UNQUALIFIED",venue="TRF")
        result=run([lit,trf])
        self.assertEqual(result["n_trf"],1)
        self.assertEqual(result["n_lit_eligible_prints"],1)
        self.assertEqual(result["n_lit_classified_quote_le5s_prints"],1)


    def test_exact_fractional_source_share_volume_is_separate_from_dollar_flow(self):
        sample=row(gross="3750.00")
        sample["gross_source_shares"]="0.375"
        result=run([sample])
        self.assertEqual(result["gross_sampled_notional_usd"],"3750.00")
        self.assertEqual(result["source_volume_included_shares"],"0.375")
        self.assertEqual(result["source_all_printed_shares"],"0.375")

    def test_volume_only_print_is_excluded_from_pressure_but_included_in_share_reconciliation(self):
        volume_only=row("special",state="INELIGIBLE",
                        reason="VOLUME_ONLY_OR_NON_PRICE_FORMING",gross="400.00")
        volume_only["gross_source_shares"]="12.375"
        volume_only["trade_volume_eligible"]=True
        reported=run([row("regular"),volume_only])
        self.assertEqual(reported["source_volume_included_shares"],"13.375")
        self.assertEqual(reported["ineligible_notional_usd"],"400.00")
        self.assertEqual(reported["n_source_volume_included_prints"],2)
        self.assertEqual(reported["n_buy_proxy"],1)

    def test_trade_excluded_from_consolidated_volume_does_not_enter_volume_reconciliation(self):
        excluded=row(state="INELIGIBLE",reason="CONSOLIDATED_VOLUME_NOT_ELIGIBLE")
        excluded["gross_source_shares"]="8"
        excluded["trade_volume_eligible"]=False
        report=run([excluded])
        self.assertEqual(report["source_volume_included_shares"],"0")
        self.assertEqual(report["source_volume_excluded_shares"],"8")
        self.assertEqual(report["n_source_volume_excluded_prints"],1)

    def test_unknown_trade_conditions_remain_unknown_share_volume(self):
        unknown=row(state="UNKNOWN",reason="TRADE_CONDITION_POLICY_UNQUALIFIED")
        unknown["trade_volume_eligible"]=None
        unknown["gross_source_shares"]="2.5"
        summary=run([unknown])
        self.assertEqual(summary["source_volume_unknown_shares"],"2.5")
        self.assertEqual(summary["source_volume_included_shares"],"0")
        self.assertEqual(summary["n_source_volume_unknown_prints"],1)

    def test_unknown_quote_condition_does_not_remove_trade_from_known_volume(self):
        unknown=row(state="UNKNOWN",reason="QUOTE_CONDITION_NOT_FIRM_OR_UNKNOWN")
        unknown["gross_source_shares"]="6.75"
        summary=run([unknown])
        self.assertEqual(summary["unknown_notional_usd"],"100.50")
        self.assertEqual(summary["source_volume_included_shares"],"6.75")

    def test_classified_trade_must_have_volume_source_policy(self):
        sample=row()
        sample["trade_volume_eligible"]=False
        with self.assertRaisesRegex(MinuteProjectionRefusal,"lacks volume-eligible"):
            run([sample])

    def test_malformed_or_nonfinite_share_volume_fails_closed(self):
        for bad in (None,"NaN","Infinity","-2","garbage"):
            with self.subTest(value=bad):
                sample=row()
                sample["gross_source_shares"]=bad
                with self.assertRaises(MinuteProjectionRefusal):
                    run([sample])

    def test_boolean_source_volume_eligibility_must_be_exact(self):
        sample=row()
        sample["trade_volume_eligible"]="yes"
        with self.assertRaisesRegex(MinuteProjectionRefusal,"boolean or unknown"):
            run([sample])

    def test_missing_native_share_field_fails_exact_source_contract(self):
        sample=row()
        del sample["gross_source_shares"]
        with self.assertRaisesRegex(MinuteProjectionRefusal,"exact incumbent"):
            run([sample])

if __name__=="__main__":
    unittest.main()
