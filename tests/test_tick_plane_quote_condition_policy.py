"""Original-available quote-policy admission is not naked eligible=True."""

import json
import unittest

from engine.tick_plane.quote_condition_policy import (
    parse_quote_policy, evaluate_quote_condition, FrameContractError,
    POLICY_SCHEMA,
)

BASE=1_791_417_600_000_000_000
CUT=BASE+100_000_000


def policy(**updates):
    row={"schema":POLICY_SCHEMA,"source_reference_sha256":"b"*64,
         "reviewer_receipt":"reviewed:source-ref:original:synthetic",
         "unknown_action":"ABSTAIN","allowed_quote_conditions":[0,1],
         "allowed_nbbo_indicators":[602,604,605]}
    row.update(updates)
    raw=json.dumps(row,separators=(",",":")).encode()
    return parse_quote_policy(original_policy_bytes=raw,
                              policy_received_ns=BASE-1_000_000,
                              policy_receipt_id="original:policy:sha256")


def quote(**updates):
    row={"schema":"equity.tick_plane.stream_event/v0",
         "event_type":"Q","quote_id":"SPY:RTH:Q:1",
         "ticker":"SPY","session":"2026-10-08:RTH",
         "source_frame_sha256":"a"*64,
         "original_frame_received_ns":BASE,
         "quote_condition":0,"quote_indicators":[604],
         "valid_firm_nbbo":True}
    row.update(updates)
    return row


def verdict(q=None,p=None,**overrides):
    args=dict(quote=quote() if q is None else q,
              policy=policy() if p is None else p,
              decision_ns=CUT,original_policy_custody_attested=True)
    args.update(overrides)
    return evaluate_quote_condition(**args)


class QuoteConditionTests(unittest.TestCase):
    def test_regular_nbbo_and_source_receipts_are_bound(self):
        r=verdict()
        self.assertIs(r["eligible"],True)
        self.assertEqual(r["quote_condition"],0)
        self.assertEqual(r["quote_indicators"],[604])
        self.assertEqual(r["source_frame_sha256"],"a"*64)
        self.assertEqual(len(r["policy_rules_sha256"]),64)
        self.assertEqual(r["authority"],"ORIGINAL_QUOTE_POLICY_CONTEXT_ONLY")

    def test_two_sided_regular_quote_has_condition_id_one(self):
        self.assertIs(verdict(q=quote(quote_condition=1))["eligible"],True)

    def test_nonfirm_and_sip_generated_conditions_abstain(self):
        for code in (2,4,15,19,20,43,82,83,84,85):
            with self.subTest(condition=code):
                r=verdict(q=quote(quote_condition=code))
                self.assertIs(r["eligible"],False)

    def test_unrecognized_quote_condition_never_auto_permitted(self):
        self.assertIs(verdict(q=quote(quote_condition=999))["eligible"],False)

    def test_unknown_quote_condition_not_equivalent_to_regular(self):
        self.assertIsNone(verdict(q=quote(quote_condition=None))["eligible"])

    def test_missing_or_unknown_indicator_is_not_silently_ok(self):
        for indicators in ([],[999],[602,999],[601],[603]):
            with self.subTest(indicators=indicators):
                self.assertIsNone(verdict(q=quote(quote_indicators=indicators))["eligible"])

    def test_invalid_top_book_with_regular_code_is_still_not_eligible(self):
        self.assertIs(verdict(q=quote(valid_firm_nbbo=False))["eligible"],False)

    def test_policy_received_later_never_retroactively_qualifies(self):
        p=policy();p["policy_received_ns"]=CUT+1
        self.assertIsNone(verdict(p=p)["eligible"])

    def test_quote_received_later_than_decision_not_admitted(self):
        self.assertIsNone(verdict(q=quote(original_frame_received_ns=CUT+1))["eligible"])

    def test_custody_is_not_granted_by_policy_json(self):
        self.assertIsNone(verdict(original_policy_custody_attested=False)["eligible"])

    def test_quote_source_frame_and_policy_digest_are_not_omitted(self):
        r=verdict()
        self.assertEqual(r["quote_id"],"SPY:RTH:Q:1")
        self.assertEqual(r["policy_available_ns"],BASE-1_000_000)
        self.assertEqual(r["source_reference_sha256"],"b"*64)

    def test_unreviewed_nonfirm_code_in_policy_rejected(self):
        with self.assertRaisesRegex(FrameContractError,"unreviewed"):
            policy(allowed_quote_conditions=[0,20])

    def test_unreviewed_non_nbbo_indicator_in_policy_rejected(self):
        with self.assertRaisesRegex(FrameContractError,"unreviewed"):
            policy(allowed_nbbo_indicators=[602,603])

    def test_policy_requires_reviewed_source_reference_sha(self):
        with self.assertRaisesRegex(FrameContractError,"provenance"):
            policy(source_reference_sha256="")

    def test_duplicate_policy_codes_rejected(self):
        with self.assertRaisesRegex(FrameContractError,"duplicate"):
            policy(allowed_quote_conditions=[0,0])

    def test_source_identity_is_not_a_signing_or_trading_action(self):
        r=verdict()
        self.assertNotIn("signal",r)
        self.assertNotIn("trade_side",r)
        self.assertNotIn("order_replenishment",r)


if __name__=="__main__":
    unittest.main()
