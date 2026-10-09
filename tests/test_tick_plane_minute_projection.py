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
           "quote_conditions_rules_ref":"policy-ref",
           "quote_source_receipt_id":"quote-ref","matched_quote_id":"Q1",
           "quote_age_ns":500_000,"source_trade_conditions":[0],
           "venue_class":venue,
           "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
           "gross_observed_notional_usd":gross,
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

if __name__=="__main__":
    unittest.main()
