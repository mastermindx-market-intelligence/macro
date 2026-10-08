"""Focused source casebook and adversarial receipt-time lifecycle tests."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import treasury_auction_lifecycle as lifecycle

FIXTURES = Path(__file__).parent / "fixtures" / "treasury_auction_lifecycle"
NOW = "2026-10-08T23:00:00+00:00"
OBSERVED = "2026-10-08T22:12:22.414829+00:00"


def row(name="bill_future_nonstandard_deadline"):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def receipt(rows=None, observed=OBSERVED, raw=None, kind="treasurydirect_json", schema=None):
    return lifecycle.make_observation(raw if raw is not None else json.dumps(rows if rows is not None else [row()]),
        source_kind=kind, source_url="https://www.treasurydirect.gov/TA_WS/securities/announced?format=json",
        observed_at=observed, schema_id=schema)


def context(rows=None, observed=OBSERVED, as_of=NOW, **kwargs):
    return lifecycle.build_context([receipt(rows, observed)], as_of, **kwargs)


class TreasuryAuctionLifecycleTests(unittest.TestCase):
    def test_genuine_casebook_classes_deadlines_and_money(self):
        cases = json.loads((FIXTURES / "casebook_expectations.json").read_text())["cases"]
        for case in cases:
            with self.subTest(case=case["case_id"]):
                # A latest API record is known only at this modern receipt. Use a
                # long horizon for past cases only by inspecting normalization
                # via a target-day receipt (synthetic clock, genuine row values).
                record = row(case["case_id"])
                day = case["expected"]["auction_date"]
                obs = f"{day}T23:59:00+00:00"
                out = context([record], observed=obs, as_of=obs)
                event = out["episodes"][0]
                for field in ("normalized_class", "issued_cusip", "announced_cusip", "auction_date", "issue_date", "competitive_deadline_utc", "offering_amount_usd"):
                    self.assertEqual(event[field], case["expected"][field], field)
                self.assertEqual(event["known_at"], obs)
                self.assertIsNone(event["publication_time"])
                self.assertEqual(hashlib.sha256((FIXTURES / Path(case["fixture"]).name).read_bytes()).hexdigest(), case["fixture_sha256"])

    def test_nonstandard_bill_and_frn_semantics(self):
        event = context()["events"][0]
        self.assertEqual(event["time_et"], "13:00")
        self.assertEqual(event["physical_state"], "ANNOUNCED")
        self.assertIsNone(event["result"])
        event = context([row("frn_reopening")], observed="2026-09-23T20:00:00Z", as_of="2026-09-23T20:00:00Z")["events"][0]
        self.assertEqual(event["time_et"], "11:30")
        self.assertEqual(event["result"]["high_discount_margin_pct"], "0.040000")
        self.assertIsNone(event["result"]["nominal_yield_pct"])

    def test_asof_excludes_entire_later_receipt(self):
        out = context(as_of="2026-10-08T21:00:00Z")
        self.assertEqual(out["episodes"], [])
        self.assertEqual(out["source_states"], [])
        self.assertEqual(out["observation_receipts"], [])
        self.assertEqual(out["coverage"]["excluded_after_as_of_count"], 1)
        self.assertIsNone(out["coverage"]["known_upcoming_count"])

    def test_offset_aware_clocks_required(self):
        for value in ("2026-10-08", "2026-10-08T23:00:00", datetime(2026, 10, 8)):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    receipt(observed=value)
                with self.assertRaises(ValueError):
                    lifecycle.build_context([], value)
        bad = receipt()
        bad["observed_at"] = "2026-10-08"
        self.assertEqual(lifecycle.build_context([bad], NOW)["quarantine"][0]["reason"], "invalid_observed_at")

    def test_future_clock_does_not_override_asof(self):
        out = context(observed="2026-10-20T00:00:00Z")
        self.assertEqual(out["episodes"], [])
        self.assertEqual(out["coverage"]["excluded_after_as_of_count"], 1)

    def test_missing_and_invalid_deadline_never_default(self):
        for value, reason in (("", "missing_competitive_deadline"), ("25:30", "invalid_competitive_deadline")):
            record = row(); record["closingTimeCompetitive"] = value
            event = context([record])["episodes"][0]
            self.assertIsNone(event["competitive_deadline_utc"])
            self.assertIn(reason, event["null_reasons"])
            self.assertIsNone(context([record])["events"][0]["time_et"])

    def test_amended_deadline_is_not_backdated(self):
        current = row("tips_amended_latest_record")
        out = context([current], as_of="2025-04-11T23:00:00Z")
        self.assertEqual(out["episodes"], [])
        # Current row announcementDate Apr10 cannot override Oct2026 receipt.
        self.assertEqual(out["coverage"]["excluded_after_as_of_count"], 1)

    def test_correction_versions_and_prior_asof(self):
        original = row(); original["closingTimeCompetitive"] = "11:30 AM"
        a = receipt([original], observed="2026-10-08T20:00:00Z")
        b = receipt([row()], observed="2026-10-08T22:00:00Z")
        old = lifecycle.build_context([b, a], "2026-10-08T21:00:00Z")["episodes"][0]
        new = lifecycle.build_context([a, b], NOW)["episodes"][0]
        self.assertEqual(old["competitive_deadline_utc"], "2026-10-13T15:30:00+00:00")
        self.assertEqual(new["competitive_deadline_utc"], "2026-10-13T17:00:00+00:00")
        self.assertEqual(len(old["observation_versions"]), 1)
        self.assertEqual(len(new["observation_versions"]), 2)

    def test_class_conflict_quarantine_keeps_good_neighbors(self):
        bad = row("frn_reopening"); bad["tips"] = "Yes"
        out = context([bad, row()])
        self.assertEqual(len(out["episodes"]), 1)
        self.assertEqual(out["quarantine"][0]["reason"], "instrument_type_flag_conflict")
        self.assertEqual(out["status"], "degraded")
        bad = row(); bad["type"] = "CMB"; bad["cashManagementBillCMB"] = "No"
        self.assertEqual(context([bad])["episodes"], [])

    def test_unsupported_migration_is_visible(self):
        for raw in ('{"data":[{"auction_date":"2026-10-13"}]}', '[{"auctionDate":"2026-10-13","security_type":"Bill"}]'):
            out = lifecycle.build_context([receipt(raw=raw)], NOW)
            self.assertEqual(out["source_states"][0]["status"], "unsupported")
            self.assertIsNone(out["coverage"]["known_upcoming_count"])
        out = lifecycle.build_context([receipt(schema="treasury_json_migrated_v2")], NOW)
        self.assertEqual(out["status"], "unsupported")

    def test_digest_and_decoded_payload_tampering(self):
        for field, value in (("raw_text", "[]"), ("payload", [])):
            bad = receipt(); bad[field] = value
            out = lifecycle.build_context([bad], NOW)
            self.assertEqual(out["episodes"], [])
            self.assertEqual(out["source_states"][0]["status"], "degraded")

    def test_raw_bytes_digest_preserves_newlines(self):
        raw = (json.dumps([row()]) + "\r\n").encode()
        env = receipt(raw=raw)
        self.assertEqual(env["payload_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(env["raw_text"].encode(), raw)

    def test_malformed_source_does_not_kill_good_neighbor(self):
        out = lifecycle.build_context([receipt(raw="bad json"), receipt()], NOW)
        self.assertEqual(len(out["episodes"]), 1)
        self.assertEqual(out["status"], "degraded")
        out = context([None, {"cusip": "broken"}, row()])
        self.assertEqual(len(out["quarantine"]), 2)
        self.assertEqual(len(out["episodes"]), 1)

    def test_tentative_xml_holiday_and_unique_merge(self):
        env = receipt(raw=(FIXTURES / "tentative_schedule_subset.xml").read_bytes(), kind="quarterly_tentative_xml")
        out = lifecycle.build_context([env, receipt()], NOW)
        self.assertEqual(out["coverage"]["holiday_nodes_skipped"], 1)
        self.assertEqual(out["coverage"]["unresolved_tentative_count"], 10)
        bill = next(e for e in out["episodes"] if e["issued_cusip"] == "912797SU2")
        self.assertEqual(len(bill["tentative_slot_ids"]), 1)
        self.assertEqual(len(bill["observation_versions"]), 2)
        self.assertEqual(bill["source_state"], "ANNOUNCED")
        tentative = next(e for e in out["episodes"] if e["normalized_class"] == "FRN")
        self.assertIsNone(tentative["competitive_deadline_utc"])
        self.assertIsNone(tentative["offering_amount_usd"])

    def test_tentative_ambiguous_match_never_guessed(self):
        env = receipt(raw=(FIXTURES / "tentative_schedule_subset.xml").read_bytes(), kind="quarterly_tentative_xml")
        a, b = row(), row(); b["cusip"] = "912797XXX"
        out = lifecycle.build_context([env, receipt([a,b])], NOW)
        self.assertTrue(any(c["reason"] == "ambiguous_tentative_join" for c in out["conflicts"]))
        self.assertEqual(out["coverage"]["unresolved_tentative_count"], 11)

    def test_pending_after_result_does_not_regress(self):
        finished = row(); finished["auctionDate"] = "2026-10-07T00:00:00"; finished["competitiveAccepted"] = "95000000000"
        env = receipt(raw=(FIXTURES / "pending_auctions.xml").read_bytes(), kind="pending_auctions_xml", observed="2026-10-09T20:00:00Z")
        # Same episode pending row keeps Oct13; inject genuine result on exact
        # pending schedule auction date with a later asof and prior receipt.
        result = row(); result["competitiveAccepted"] = "95000000000"
        done = receipt([result], observed="2026-10-13T20:00:00Z")
        env["observed_at"] = "2026-10-14T20:00:00+00:00"
        out = lifecycle.build_context([done, env], "2026-10-14T23:00:00Z")
        bill = next(e for e in out["episodes"] if e["issued_cusip"] == "912797SU2")
        self.assertEqual(bill["source_state"], "RESULT_OBSERVED")
        self.assertEqual(bill["physical_state"], "RESULT_OBSERVED")

    def test_future_result_bearing_contradiction_withheld(self):
        record = row(); record["pdfFilenameCompetitiveResults"] = "R_future.pdf"
        out = context([record])
        self.assertEqual(out["episodes"], [])
        self.assertEqual(out["quarantine"][0]["reason"], "future_result_bearing_contradiction")
        out = context([row("bond_reopening")], observed="2026-10-08T16:00:00Z")
        self.assertEqual(out["episodes"], [])

    def test_endpoint_name_does_not_establish_result(self):
        env = receipt(); env["source_url"] = "https://www.treasurydirect.gov/TA_WS/securities/auctioned"
        self.assertEqual(lifecycle.build_context([env], NOW)["episodes"][0]["source_state"], "ANNOUNCED")

    def test_awaiting_result_and_issue_calendar_not_payment(self):
        record = row()
        out = context([record], as_of="2026-10-13T17:00:01Z")
        self.assertEqual(out["episodes"][0]["physical_state"], "AWAITING_RESULT")
        finished = context([row("bill_october_completed")])["episodes"][0]
        self.assertEqual(finished["issue_calendar_state"], "ISSUE_DATE_PASSED")
        self.assertIsNone(finished["settled_payment_observed"])
        note = context([row("note_reopening")])["episodes"][0]
        self.assertEqual(note["issue_calendar_state"], "ISSUE_DATE_NOT_PASSED")

    def test_same_cusip_distinct_auction_episodes(self):
        records = row("same_cusip_multiple_auctions")
        out = context(records, observed="2026-10-01T23:00:00Z", as_of="2026-10-01T23:00:00Z", horizon_days=120)
        self.assertEqual(len(out["episodes"]), 3)
        self.assertEqual(len({e["episode_id"] for e in out["episodes"]}), 3)

    def test_unscheduled_announced_alias_and_original_fallback(self):
        record = row("unscheduled_reopening_result")
        obs = "2025-02-25T23:00:00Z"
        event = context([record], observed=obs, as_of=obs)["episodes"][0]
        self.assertEqual(event["episode_id"], "auction:91282CMQ1:2025-02-25")
        self.assertEqual(event["issued_cusip"], "91282CGQ8")
        record["announcedCusip"] = ""
        self.assertEqual(context([record], observed=obs, as_of=obs)["episodes"][0]["episode_id"], "auction:91282CMQ1:2025-02-25")
        record["pdfFilenameSpecialAnnouncement"] = ""
        self.assertEqual(context([record], observed=obs, as_of=obs)["episodes"][0]["episode_id"], "auction:91282CGQ8:2025-02-25")

    def test_same_time_conflicting_facts_are_withheld(self):
        a, b = row(), row(); b["offeringAmount"] = "96000000000"
        first = lifecycle.build_context([receipt([a]), receipt([b])], NOW)
        reverse = lifecycle.build_context([receipt([b]), receipt([a])], NOW)
        self.assertEqual(first["episodes"], [])
        self.assertEqual(first["conflicts"], reverse["conflicts"])
        self.assertEqual(first["conflicts"][0]["reason"], "same_time_conflicting_facts")

    def test_missing_number_is_not_zero(self):
        for missing in ("", "null", "NaN", None):
            record = row(); record["offeringAmount"] = missing
            self.assertIsNone(context([record])["episodes"][0]["offering_amount_usd"])
        record = row(); record["offeringAmount"] = "0"
        self.assertEqual(context([record])["episodes"][0]["offering_amount_usd"], "0")

    def test_empty_unavailable_and_unsupported_have_different_coverage(self):
        empty = context([])
        self.assertEqual(empty["source_states"][0]["status"], "empty")
        self.assertEqual(empty["coverage"]["known_upcoming_count"], 0)
        failure = receipt(); failure.update(status="unavailable", error="HTTP 503")
        unavailable = lifecycle.build_context([failure], NOW)
        self.assertEqual(unavailable["source_states"][0]["status"], "unavailable")
        self.assertIsNone(unavailable["coverage"]["known_upcoming_count"])
        self.assertIsNone(lifecycle.build_context([], NOW)["coverage"]["known_upcoming_count"])

    def test_horizon_exact_date_bounds_and_not_complete_cmb_universe(self):
        a, b, c = row(), row(), row()
        for record, ds, cusip in ((a,"2026-10-08","912797AAA"),(b,"2026-10-22","912797BBB"),(c,"2026-10-23","912797CCC")):
            record.update(auctionDate=ds, issueDate="2026-10-27", cusip=cusip)
        out = context([a,b,c], horizon_days=14)
        self.assertEqual(len(out["episodes"]), 2)
        self.assertEqual(out["coverage"]["upcoming_end_date_inclusive"], "2026-10-22")
        self.assertTrue(out["coverage"]["counts_are_observed_not_complete_universe"])

    def test_immutable_input_and_no_forecast_or_impact(self):
        env = receipt(); before = copy.deepcopy(env)
        out = lifecycle.build_context([env], NOW)
        self.assertEqual(env, before)
        self.assertTrue(out["is_context_only"])
        self.assertEqual(out["forecast_authority"], "RESEARCH_ONLY")
        self.assertIsNone(out["probabilities"])
        self.assertEqual(out["events"][0]["importance"], "NOT_SCORED")
        self.assertIsNone(out["events"][0]["impact"])

    def test_size_limits_and_snapshot_local_bad_neighbor(self):
        with self.assertRaises(ValueError):
            receipt(raw=" " * (lifecycle.MAX_PAYLOAD_BYTES+1))
        with patch.object(lifecycle, "MAX_ROWS", 1):
            out = context([row(), row()])
            self.assertTrue(out["coverage"]["truncated"])
            self.assertIsNone(out["coverage"]["known_upcoming_count"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            absent = lifecycle.snapshot(root, NOW)
            self.assertEqual(absent["status"], "unavailable")
            self.assertIsNone(absent["coverage"]["known_upcoming_count"])
            d = root / "treasury_auctions" / "observations"; d.mkdir(parents=True)
            (d / "good.json").write_text(json.dumps(receipt()))
            (d / "bad.json").write_text("broken")
            out = lifecycle.snapshot(root, NOW)
            self.assertEqual(out["status"], "degraded")
            self.assertEqual(len(out["episodes"]), 1)
            self.assertEqual(out["coverage"]["receipt_files_quarantined"], 1)

    def test_explicit_current_rows_envelope(self):
        env = receipt(raw=json.dumps({"schema_id": lifecycle.JSON_SCHEMA,"rows":[row()]}))
        self.assertEqual(len(lifecycle.build_context([env], NOW)["episodes"]), 1)
        bad = receipt(raw=json.dumps({"rows":[row()]}))
        self.assertEqual(lifecycle.build_context([bad], NOW)["status"], "unsupported")

    def test_failure_health_preserves_source_age_and_clock_roles(self):
        env = receipt(observed="2026-10-08T20:00:00Z")
        failure = {"receipt_version": 1, "status": "unavailable", "source_kind": env["source_kind"],
                   "schema_id": env["schema_id"], "source_url": env["source_url"],
                   "observed_at": "2026-10-08T22:00:00Z", "error": "HTTP 503"}
        out = lifecycle.build_context([failure, env], NOW)
        health = out["source_health"][0]
        self.assertEqual(out["status"], "degraded")
        self.assertEqual(health["latest_attempt_status"], "unavailable")
        self.assertEqual(health["latest_failure_reasons"], ["HTTP 503"])
        self.assertEqual(health["last_valid_observation_age_seconds"], 10800)
        self.assertEqual(out["source_observed_at"], "2026-10-08T20:00:00+00:00")
        self.assertEqual(out["decision_cutoff_utc"], NOW)
        self.assertEqual(out["asof"], "2026-10-08")
        later = lifecycle.build_context([env, failure], "2026-10-09T23:00:00Z")
        self.assertEqual(later["asof"], "2026-10-08")
        self.assertEqual(later["source_health"][0]["last_valid_observation_age_seconds"], 97200)
        malformed = receipt(raw="broken", observed="2026-10-08T22:30:00Z")
        health = lifecycle.build_context([env, failure, malformed], NOW)["source_health"][0]
        self.assertIsNone(health["last_successful_body_receipt_at"])
        self.assertEqual(health["last_valid_observation_at"], "2026-10-08T20:00:00+00:00")

    def test_body_arrival_is_measured_separately_from_knowledge(self):
        env = receipt(observed="2026-10-08T20:00:00Z")
        env["metadata"] = {"body_received_at": "2026-10-08T19:59:59.998123Z"}
        health = lifecycle.build_context([env], NOW)["source_health"][0]
        self.assertEqual(health["last_successful_body_receipt_at"], "2026-10-08T19:59:59.998123+00:00")
        self.assertEqual(health["last_valid_observation_at"], "2026-10-08T20:00:00+00:00")
        malformed = receipt(raw="broken", observed="2026-10-08T22:30:00Z")
        malformed["metadata"] = {"body_received_at": "2026-10-08T22:29:59.997Z"}
        health = lifecycle.build_context([env, malformed], NOW)["source_health"][0]
        self.assertEqual(health["last_successful_body_receipt_at"], "2026-10-08T22:29:59.997000+00:00")
        self.assertEqual(health["last_valid_observation_at"], "2026-10-08T20:00:00+00:00")

    def test_invalid_or_future_body_clock_is_quarantined(self):
        for body in ("2026-10-08T20:00:00.000001Z", "2026-10-08T19:00:00", 123):
            with self.subTest(body=body):
                env = receipt(observed="2026-10-08T20:00:00Z")
                env["metadata"] = {"body_received_at": body}
                out = lifecycle.build_context([env], NOW)
                self.assertFalse(out["events"])
                self.assertIsNone(out["source_observed_at"])
                self.assertIsNone(out["source_health"][0]["last_successful_body_receipt_at"])

    def test_equal_clock_announcement_result_core_conflict_withheld(self):
        announcement, result = row(), row()
        result["competitiveAccepted"] = "95000000000"
        result["offeringAmount"] = "96000000000"
        obs = "2026-10-13T20:00:00Z"
        out = lifecycle.build_context([receipt([announcement], observed=obs),receipt([result], observed=obs)], obs)
        self.assertEqual(out["episodes"], [])
        self.assertIn("offering_amount_usd", out["conflicts"][0]["conflicting_fields"])
        result["offeringAmount"] = announcement["offeringAmount"]
        out = lifecycle.build_context([receipt([announcement], observed=obs),receipt([result], observed=obs)], obs)
        self.assertEqual(out["episodes"][0]["source_state"], "RESULT_OBSERVED")

    def test_exact_original_coupon_cohort_join_not_nearest_tenor(self):
        quarterly = (FIXTURES / "tentative_schedule_subset.xml").read_text()
        # Replace its genuine first slot with genuine Oct8 bond schedule fields;
        # preserve schema, then test cohort semantics using genuine result row.
        quarterly = quarterly.replace("6-Week", "30-Year", 1).replace("<SecurityType>BILL</SecurityType>", "<SecurityType>BOND</SecurityType>", 1)
        quarterly = quarterly.replace("<AuctionDate>2026-10-13</AuctionDate>", "<AuctionDate>2026-10-08</AuctionDate>", 1)
        env = receipt(raw=quarterly, kind="quarterly_tentative_xml")
        out = lifecycle.build_context([env,receipt([row("bond_reopening")])], NOW)
        bond = next(e for e in out["episodes"] if e["issued_cusip"] == "912810UW6")
        self.assertEqual(bond["security_term"], "29-Year 10-Month")
        self.assertEqual(bond["schedule_match_term"], "30-Year")
        self.assertEqual(bond["schedule_match_basis"], "official_original_security_term")
        self.assertEqual(len(bond["tentative_slot_ids"]), 1)
        unrelated = row("bond_reopening"); unrelated["originalSecurityTerm"] = "29-Year"
        out = lifecycle.build_context([env,receipt([unrelated])], NOW)
        bond = next(e for e in out["episodes"] if e["issued_cusip"] == "912810UW6")
        self.assertEqual(bond["tentative_slot_ids"], [])

    def test_duplicate_tentative_slots_preserve_ambiguity(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring((FIXTURES / "tentative_schedule_subset.xml").read_text())
        root.append(copy.deepcopy(root.findall("AuctionCalendarDate")[0]))
        env = receipt(raw=ET.tostring(root, encoding="unicode"), kind="quarterly_tentative_xml")
        out = lifecycle.build_context([env,receipt()], NOW)
        bill = next(e for e in out["episodes"] if e["issued_cusip"] == "912797SU2")
        self.assertEqual(bill["tentative_slot_ids"], [])
        self.assertEqual(sum(c["reason"] == "ambiguous_tentative_join" for c in out["conflicts"]), 2)

    def test_snapshot_newest_files_survive_bounded_capture_retention(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = root / "treasury_auctions" / "observations"; d.mkdir(parents=True)
            # More than the real bound, with misleading lexical filenames. The
            # recently written receipt is retained; filename is not eligibility.
            for index in range(lifecycle.MAX_FILES + 1):
                record = row(); record["offeringAmount"] = str(95000000000 + index)
                observed = f"2026-10-08T20:{index // 60:02d}:{index % 60:02d}+00:00"
                path = d / f"receipt_{lifecycle.MAX_FILES-index:04d}.json"
                path.write_text(json.dumps(receipt([record],observed=observed)))
                os.utime(path, (1000000 + index, 1000000 + index))
            out = lifecycle.snapshot(root, NOW)
            self.assertTrue(out["coverage"]["truncated"])
            self.assertEqual(out["status"], "degraded")
            self.assertEqual(out["coverage"]["receipt_files_read"], lifecycle.MAX_FILES)
            self.assertIsNone(out["coverage"]["known_upcoming_count"])
            self.assertEqual(out["episodes"][0]["offering_amount_usd"], str(95000000000 + lifecycle.MAX_FILES))
            earlier = lifecycle.snapshot(root, "2026-10-08T20:00:00Z")
            self.assertTrue(earlier["coverage"]["truncated"])
            self.assertIsNone(earlier["coverage"]["known_upcoming_count"])
            self.assertEqual(earlier["episodes"], [])

    def test_first_observed_semantic_vintage_does_not_claim_publication(self):
        early = receipt(observed="2026-10-08T20:00:00Z")
        repeat = receipt(observed="2026-10-08T21:00:00Z")
        altered = row(); altered["offeringAmount"] = "96000000000"
        amended = receipt([altered], observed="2026-10-08T22:00:00Z")
        repeated = lifecycle.build_context([repeat,early], NOW)["episodes"][0]
        self.assertEqual(repeated["known_at"], "2026-10-08T21:00:00+00:00")
        self.assertEqual(repeated["first_observed_at"], "2026-10-08T20:00:00+00:00")
        corrected = lifecycle.build_context([early,amended,repeat], NOW)["episodes"][0]
        self.assertEqual(corrected["first_observed_at"], "2026-10-08T22:00:00+00:00")
        self.assertIsNone(corrected["publication_time"])

    def test_xml_future_shape_and_entity_rejected(self):
        out = lifecycle.build_context([receipt(raw="<AuctionCalendarV2/>", kind="quarterly_tentative_xml")], NOW)
        self.assertEqual(out["status"], "unsupported")
        out = lifecycle.build_context([receipt(raw='<!DOCTYPE AuctionCalendar [<!ENTITY x "hi">]><AuctionCalendar/>', kind="quarterly_tentative_xml")], NOW)
        self.assertEqual(out["source_states"][0]["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
