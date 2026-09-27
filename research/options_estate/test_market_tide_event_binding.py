"""Behavioral checks for the research-only event contract consumer."""
import copy
import json
import unittest
from pathlib import Path
try:
    import market_tide_event_binding as subject
except ModuleNotFoundError:
    subject = None


def notice(**changes):
    row = {
        "notice_id": "synthetic-notice-1", "event_ref": "synthetic-CPI-2017-02",
        "type": "CPI", "reference_period": "2017-02",
        "published_at": "2017-02-15T13:30:00+00:00", "ingested_at": None,
        "event_date": "2017-03-15", "event_at": "2017-03-15T12:30:00+00:00",
        "precision": "instant", "evidence_role": "advance_schedule", "plan_status": "scheduled",
        "source_ref": "https://www.bls.gov/news.release/archives/cpi_02152017.htm",
        "source_locator": "synthetic test using actual source URL", "retrieved_on": "2026-09-24",
        "raw_document_sha256": None,
    }
    row.update(changes)
    return row


class EventBindingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(subject, "research event-binding feature is not implemented")

    def run_packet(self, rows=None, **kw):
        return subject.bind_notices(
            [notice()] if rows is None else rows,
            decision_at=kw.pop("decision_at", "2017-03-14T20:15:00+00:00"),
            window_end=kw.pop("window_end", "2017-03-15T20:00:00+00:00"), **kw)

    def test_unknown_coverage_never_becomes_no_event(self):
        out = self.run_packet([])
        self.assertEqual(out["c1_event_features"], {"E_CPI": None, "E_NFP": None, "E_FOMC": None})
        self.assertFalse(out["primary_cohort_eligible"])

    def test_real_owner_event_shape_and_documented_clock(self):
        ev = self.run_packet()["events"][0]
        self.assertEqual((ev["type"], ev["date"], ev["time_et"]), ("CPI", "2017-03-15", "08:30"))
        self.assertTrue(ev["is_context_only"])
        self.assertTrue(ev["research_evidence"]["documented_plan_in_window"])
        self.assertEqual(ev["research_evidence"]["event_at"], "2017-03-15T12:30:00+00:00")
        self.assertIsNone(ev["research_evidence"]["ingested_at"])

    def test_future_notice_cannot_leak(self):
        out = self.run_packet([notice(published_at="2017-03-15T10:00:00+00:00")])
        self.assertEqual(out["events"], [])
        self.assertEqual(out["excluded"][0]["reason"], "not_public_at_decision")

    def test_ingestion_is_not_backdated(self):
        ev = self.run_packet([notice(ingested_at="2026-09-24T12:00:00+00:00")])["events"][0]
        self.assertEqual(ev["research_evidence"]["ingested_at"], "2026-09-24T12:00:00+00:00")
        self.assertFalse(self.run_packet()["system_replay"])

    def test_missing_publication_cannot_use_retrieval_as_history(self):
        out = self.run_packet([notice(published_at=None, ingested_at="2017-03-01T12:00:00+00:00")])
        self.assertEqual(out["excluded"][0]["reason"], "publication_clock_unavailable")

    def test_naive_notice_timestamp_is_rejected(self):
        self.assertEqual(self.run_packet([notice(published_at="2017-02-15T13:30:00")])["excluded"][0]["reason"], "invalid_notice")

    def test_naive_decision_is_rejected(self):
        with self.assertRaises(ValueError): self.run_packet(decision_at="2017-03-14T20:15:00")

    def test_reversed_window_is_rejected(self):
        with self.assertRaises(ValueError): self.run_packet(window_end="2017-03-14T19:00:00Z")

    def test_date_only_never_borrows_default_fomc_time(self):
        row = notice(type="FOMC", precision="date", event_at=None, reference_period=None)
        ev = self.run_packet([row])["events"][0]
        self.assertEqual(ev["time_et"], "")
        self.assertIsNone(ev["research_evidence"]["event_at"])
        self.assertIsNone(ev["research_evidence"]["documented_plan_in_window"])

    def test_date_only_with_timestamp_is_contradictory(self):
        out = self.run_packet([notice(precision="date")])
        self.assertEqual(out["events"], [])
        self.assertEqual(out["excluded"][0]["reason"], "invalid_notice")

    def test_exact_time_must_agree_with_local_event_date(self):
        self.assertEqual(self.run_packet([notice(event_date="2017-03-16")])["events"], [])

    def test_occurrence_document_not_an_advance_schedule(self):
        out = self.run_packet([notice(evidence_role="occurrence")])
        self.assertEqual(out["excluded"][0]["reason"], "not_advance_schedule")

    def test_same_instant_publication_not_advance_knowledge(self):
        out = self.run_packet([notice(published_at="2017-03-15T12:30:00Z")], decision_at="2017-03-15T12:30:00Z")
        self.assertEqual(out["events"], [])

    def test_prior_event_is_outside_future_window(self):
        out = self.run_packet([notice(event_date="2017-03-10", event_at="2017-03-10T13:30:00Z")])
        self.assertEqual(out["excluded"][0]["reason"], "outside_window")

    def test_end_boundary_included(self):
        ev = self.run_packet([notice(event_at="2017-03-15T20:00:00Z")])["events"][0]
        self.assertTrue(ev["research_evidence"]["documented_plan_in_window"])

    def test_future_revision_does_not_replace_known_notice(self):
        old = notice()
        new = notice(notice_id="future-revision", published_at="2017-03-15T10:00:00Z", event_at="2017-03-16T12:30:00Z", event_date="2017-03-16")
        out = self.run_packet([old, new])
        self.assertEqual(len(out["events"]), 1)
        self.assertEqual(out["events"][0]["date"], "2017-03-15")

    def test_visible_conflicting_versions_require_incumbent_resolution(self):
        new = notice(notice_id="visible-revision", published_at="2017-03-14T12:00:00Z", event_at="2017-03-16T12:30:00Z", event_date="2017-03-16")
        out = self.run_packet([notice(), new])
        self.assertEqual(out["events"], [])
        self.assertTrue(any(x["reason"] == "unresolved_notice_versions" for x in out["excluded"]))

    def test_duplicate_is_not_independent_evidence(self):
        out = self.run_packet([notice(), notice()])
        self.assertEqual(len(out["events"]), 1)
        self.assertEqual(out["duplicate_rows"], 1)

    def test_conflicting_reuse_of_notice_id_rejected(self):
        out = self.run_packet([notice(), notice(type="NFP")])
        self.assertEqual(out["events"], [])
        self.assertTrue(any(x["reason"] == "conflicting_notice_id" for x in out["excluded"]))

    def test_no_input_mutation(self):
        rows = [notice()]; before = copy.deepcopy(rows); self.run_packet(rows)
        self.assertEqual(rows, before)

    def test_no_actual_or_forecast_value_enters_projection(self):
        ev = self.run_packet([notice(actual=99, consensus=1, surprise=98, can_trade=True)])["events"][0]
        self.assertNotIn("actual", ev); self.assertNotIn("actual", ev["research_evidence"])
        self.assertNotIn("can_trade", ev)

    def test_reference_period_preserved_separately(self):
        ev = self.run_packet()["events"][0]
        self.assertEqual(ev["research_evidence"]["reference_period"], "2017-02")
        self.assertEqual(ev["date"], "2017-03-15")

    def test_no_primary_eligibility_even_with_documented_positive(self):
        out = self.run_packet()
        self.assertFalse(out["primary_cohort_eligible"])
        self.assertIsNone(out["c1_event_features"]["E_CPI"])
        self.assertFalse(out["can_publish_forecast"])

    def test_unknown_type_rejected(self):
        self.assertEqual(self.run_packet([notice(type="NOT_AN_EVENT")])["events"], [])

    def test_est_edt_offsets_follow_event_date(self):
        row = notice(event_date="2017-02-15", event_at="2017-02-15T13:30:00Z", published_at="2017-01-18T13:30:00Z")
        ev = self.run_packet([row], decision_at="2017-02-14T21:15:00Z", window_end="2017-02-15T21:00:00Z")["events"][0]
        self.assertEqual(ev["time_et"], "08:30")
        self.assertEqual(self.run_packet()["events"][0]["time_et"], "08:30")

    def test_unknown_event_time_is_not_sorted_as_midnight(self):
        row = notice(notice_id="date-only", event_ref="FOMC-2017-03-15", type="FOMC", event_at=None, precision="date")
        out = self.run_packet([notice(), row])
        self.assertEqual(out["events"][0]["type"], "CPI")
        self.assertEqual(out["ordering"], "date_then_known_time_unknown_times_last_not_actual_event_sequence")

    def test_cancelled_plan_not_projected_as_scheduled(self):
        out = self.run_packet([notice(plan_status="cancelled")])
        self.assertEqual(out["events"], [])
        self.assertEqual(out["excluded"][0]["reason"], "not_active_plan")

    def test_unknown_plan_status_not_assumed_active(self):
        out = self.run_packet([notice(plan_status=None)])
        self.assertEqual(out["events"], [])

    def test_tentative_status_stays_tentative(self):
        ev = self.run_packet([notice(plan_status="tentative")])["events"][0]
        self.assertEqual(ev["research_evidence"]["plan_status"], "tentative")

    def test_visible_cancellation_prevents_old_plan_reappearing(self):
        cancelled = notice(notice_id="cancelled-version", plan_status="cancelled", published_at="2017-03-14T12:00:00Z")
        out = self.run_packet([notice(), cancelled])
        self.assertEqual(out["events"], [])
        self.assertTrue(any(x["reason"] == "unresolved_notice_versions" for x in out["excluded"]))

    def test_order_independent_projection(self):
        a = notice(); b = notice(notice_id="date-only", event_ref="FOMC-2017-03-15", type="FOMC", event_at=None, precision="date")
        self.assertEqual(self.run_packet([a,b]), self.run_packet([b,a]))


    def test_conflicting_revision_id_must_not_resurrect_old_plan(self):
        out = self.run_packet([
            notice(notice_id="old"),
            notice(notice_id="revision"),
            notice(notice_id="revision", plan_status="cancelled"),
        ])
        self.assertEqual(out["events"], [])
        self.assertTrue(any(x["reason"] == "unresolved_notice_versions" for x in out["excluded"]))

    def test_reused_id_quarantines_every_referenced_event(self):
        out = self.run_packet([
            notice(notice_id="old-A"),
            notice(notice_id="old-B", event_ref="event-B", type="NFP"),
            notice(notice_id="revision"),
            notice(notice_id="revision", event_ref="event-B", type="NFP", plan_status="cancelled"),
        ])
        self.assertEqual(out["events"], [])

    def test_future_id_conflict_does_not_change_past(self):
        out = self.run_packet([
            notice(),
            notice(plan_status="cancelled", published_at="2017-03-15T10:00:00Z"),
        ])
        self.assertEqual(len(out["events"]), 1)

    def test_unrelated_event_survives_conflict(self):
        out = self.run_packet([
            notice(notice_id="revision"),
            notice(notice_id="revision", plan_status="cancelled"),
            notice(notice_id="other", event_ref="other-event", type="NFP"),
        ])
        self.assertEqual([row["type"] for row in out["events"]], ["NFP"])


if __name__ == "__main__": unittest.main(verbosity=2)
