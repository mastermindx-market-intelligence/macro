"""Original-reference condition eligibility: unknown ≠ false and volume ≠ pressure."""

import json
import unittest

from engine.tick_plane.stream_events import FrameContractError
from engine.tick_plane.condition_policy import (
    parse_condition_reference, evaluate_trade_conditions, MAX_REFERENCE_BYTES,
)

R=1_791_417_600_000_000_000


def row(i=2,*,name="Normal",vol=True,hl=True,oc=True,typ="condition"):
    return {"asset_class":"stocks","data_types":["trade"],"type":typ,
            "id":i,"name":name,
            "update_rules":{"consolidated":{"updates_volume":vol,
                "updates_high_low":hl,"updates_open_close":oc},
                "market_center":{"updates_volume":vol,
                "updates_high_low":hl,"updates_open_close":oc}}}


def packet(*rows, **fields):
    o={"status":"OK","request_id":"reference-r0-conditions",
       "results":list(rows)}
    o.update(fields)
    return json.dumps(o,separators=(",",":")).encode()


def parsed(*rows,when=R,**fields):
    return parse_condition_reference(raw_response_bytes=packet(*rows,**fields),
       reference_received_ns=when,source_receipt_id="original-reference:sha256")


def assess(codes,ref=None,decision=R+10,attested=True):
    ref=parsed(row(1),row(2,vol=True,hl=False,oc=False),
               row(3,vol=False,hl=True,oc=True)) if ref is None else ref
    return evaluate_trade_conditions(
        trade_conditions=codes, reference=ref, decision_ns=decision,
        original_reference_custody_attested=attested)


class ConditionAdmissionTests(unittest.TestCase):
    def test_ordinary_price_and_volume_eligible_is_only_proxy_candidate(self):
        r=assess([1])
        self.assertIs(r["eligible_for_pressure"],True)
        self.assertTrue(r["volume_eligible"])
        self.assertTrue(r["price_stat_eligible"])
        self.assertEqual(r["reason"],"CONSERVATIVE_PRICE_FORMING_CANDIDATE")
        self.assertEqual(r["authority"],"OBSERVATIONAL_ONLY")

    def test_average_price_volume_only_trade_excluded_from_pressure(self):
        r=assess([2])
        self.assertIs(r["eligible_for_pressure"],False)
        self.assertTrue(r["volume_eligible"])
        self.assertFalse(r["price_stat_eligible"])
        self.assertEqual(r["reason"],"VOLUME_ONLY_OR_NON_PRICE_FORMING")

    def test_volume_excluded_even_when_price_true(self):
        r=assess([3])
        self.assertIs(r["eligible_for_pressure"],False)
        self.assertFalse(r["volume_eligible"])
        self.assertEqual(r["reason"],"CONSOLIDATED_VOLUME_NOT_ELIGIBLE")

    def test_multiple_conditions_no_update_takes_precedence(self):
        self.assertIs(assess([1,2])["eligible_for_pressure"],False)
        self.assertIs(assess([2,1])["eligible_for_pressure"],False)
        self.assertIs(assess([1,3])["volume_eligible"],False)

    def test_future_reference_is_unavailable_for_original_decision(self):
        ref=parsed(row(1),when=R+100)
        r=assess([1],ref=ref,decision=R+10)
        self.assertIsNone(r["eligible_for_pressure"])
        self.assertEqual(r["reason"],"REFERENCE_NOT_YET_AVAILABLE")

    def test_custody_is_not_proved_by_seemingly_valid_source(self):
        r=assess([1],attested=False)
        self.assertIsNone(r["eligible_for_pressure"])
        self.assertEqual(r["reason"],"ORIGINAL_REFERENCE_CUSTODY_UNATTESTED")

    def test_empty_conditions_must_have_separate_native_default_rule(self):
        r=assess([])
        self.assertIsNone(r["eligible_for_pressure"])
        self.assertEqual(r["reason"],"EMPTY_ARRAY_NEEDS_NATIVE_DEFAULT_POLICY")

    def test_unknown_source_condition_abstains_not_volume_zero(self):
        r=assess([9999])
        self.assertIsNone(r["eligible_for_pressure"])
        self.assertEqual(r["reason"],"UNKNOWN_OR_INVALID_CONDITION_CODE")
        self.assertIsNone(r["volume_eligible"])

    def test_unknown_in_combination_does_not_accept_known_volume(self):
        self.assertIsNone(assess([1,9999])["eligible_for_pressure"])

    def test_reference_original_sha_binding(self):
        r=parsed(row(1))
        self.assertEqual(len(r["reference_sha256"]),64)
        self.assertEqual(r["source_request_id"],"reference-r0-conditions")
        self.assertEqual(r["rule_count"],1)
        self.assertEqual(r["reference_vintage"],
                         "RECEIVED_AT_ONLY_NOT_HISTORICAL_VALIDITY")

    def test_quote_and_foreign_asset_codes_not_in_stocks_trade_rules(self):
        foreign=row(9)
        foreign["asset_class"]="options"
        q=row(10)
        q["data_types"]=["quote"]
        r=parsed(row(1),foreign,q)
        self.assertEqual(r["rule_count"],1)
        self.assertIsNone(assess([9],ref=r)["eligible_for_pressure"])

    def test_missing_or_unknown_rule_fields_block_entire_reference(self):
        x=row(1)
        del x["update_rules"]["consolidated"]["updates_high_low"]
        with self.assertRaisesRegex(FrameContractError,"incomplete"):
            parsed(x)
        y=row(1)
        y["update_rules"]["consolidated"]["updates_volume"]="maybe"
        with self.assertRaisesRegex(FrameContractError,"incomplete"):
            parsed(y)

    def test_identical_condition_duplicate_is_idempotent(self):
        r=parsed(row(1),row(1))
        self.assertEqual(r["rule_count"],1)

    def test_conflicting_condition_id_refused(self):
        with self.assertRaisesRegex(FrameContractError,"conflicting"):
            parsed(row(1),row(1,hl=False))

    def test_missing_rest_pagination_blocks_rule_usage(self):
        with self.assertRaisesRegex(FrameContractError,"pagination"):
            parsed(row(1),next_url="https://api.massive.com/page2")

    def test_malformed_reference_refused(self):
        for payload in [b"invalid",b"[]",b"{}",b'{"status":"OK","results":[]}']:
            with self.subTest(payload=payload),self.assertRaises(FrameContractError):
                parse_condition_reference(raw_response_bytes=payload,
                    reference_received_ns=R,source_receipt_id="receipted")

    def test_missing_trade_code_type_is_not_safe(self):
        x=row(1)
        x["type"]=None
        with self.assertRaisesRegex(FrameContractError,"trade-condition type"):
            parsed(x)

    def test_noninteger_condition_array_never_coerced(self):
        for bad in ([True],[1.0],["1"],[-1]):
            with self.subTest(bad=bad):
                r=assess(bad)
                self.assertIsNone(r["eligible_for_pressure"])
                self.assertEqual(r["reason"],"INVALID_CONDITION_ARRAY")

    def test_no_condition_array_differs_from_empty(self):
        self.assertEqual(assess(None)["reason"],"UNKNOWN_CONDITION_ARRAY")

    def test_reference_not_visible_at_decision_is_unknown_not_backfilled(self):
        ref=parsed(row(1),when=R+100)
        self.assertEqual(assess([1],ref=ref,decision=R-1)["reason"],
                         "REFERENCE_NOT_YET_AVAILABLE")

    def test_source_policy_does_not_identify_initiator(self):
        r=assess([1])
        self.assertNotIn("customer_side",r)
        self.assertNotIn("aggressor_identity",r)
        self.assertEqual(r["method"],
                         "CONSOLIDATED_UPDATES_V0_CONSERVATIVE_PROXY")

    def test_bounded_ref_bytes_are_required(self):
        with self.assertRaisesRegex(FrameContractError,"oversized"):
            parse_condition_reference(raw_response_bytes=b" "* (MAX_REFERENCE_BYTES+1),
                reference_received_ns=R,source_receipt_id="c")

    def test_invalid_decision_time_abstains(self):
        self.assertEqual(assess([1],decision=-1)["reason"],
                         "INVALID_DECISION_CLOCK")


if __name__=="__main__":
    unittest.main()
