"""Synthetic tests for the PTSE prospective event-calendar adapter."""

from __future__ import annotations

import copy
import hashlib
import unittest

from research.options_estate.ptse_contract import build_context
from research.options_estate.ptse_event_observation import (
    EventCalendarBinding,
    PTSEEventAdapterError,
    adapt_event_calendar,
)
from research.options_estate.ptse_prospective_readiness import (
    qualify_prospective_observation,
)
from tests.test_ptse_contract import inputs

DECISION = "2026-10-02T20:00:00Z"


def ref(name: str, owner: str = "event-calendar-owner") -> dict:
    return {
        "owner_ref": owner,
        "artifact_id": "fixture:" + name,
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


def canonical_sha(payload: dict) -> str:
    import json
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def binding(p=None, *, grade="SYNTHETIC", latest="2026-10-02T19:58:00Z",
            valid_until="2026-10-03T00:00:00Z") -> EventCalendarBinding:
    p = payload() if p is None else p
    return EventCalendarBinding(
        owner_ref="event-calendar-owner",
        artifact_ref={**ref("event-calendar"), "sha256": canonical_sha(p)},
        known_at_earliest=latest,
        known_at_latest=latest,
        known_at_precision="EXACT",
        known_at_evidence_ref=ref("event-calendar-known-at"),
        valid_until=valid_until,
        evidence_grade=grade,
        population_ref=ref("event-calendar-window"),
        instrument_id="fixture:SPY",
        session_scope="REGULAR",
        calculation_version="event-calendar-adapter-v1",
        limitations=("Synthetic adapter fixture; not source qualification.",),
    )


def payload() -> dict:
    return {
        "schema_version": 1,
        "asof": "2026-10-02",
        "horizon_days": 21,
        "is_context_only": True,
        "us_macro": [
            {
                "type": "NFP", "date": "2026-10-02", "time_et": "08:30",
                "label": "Jobs report", "impact": "high", "source": "static",
                "is_context_only": True,
            },
            {
                "type": "CPI", "date": "2026-10-14", "time_et": "08:30",
                "label": "CPI", "impact": "high", "source": "fred",
                "is_context_only": True,
            },
            {
                "type": "FOMC", "date": "2026-10-16", "time_et": "14:00",
                "label": "FOMC", "impact": "high", "source": "static",
                "is_context_only": True,
            },
            {
                "type": "CLAIMS", "date": "2026-10-08", "time_et": "08:30",
                "label": "Claims", "impact": "med", "source": "computed",
                "is_context_only": True,
            },
        ],
        "high_impact": [],
        "commodity": [],
    }


def by_id(facts):
    return {fact["feature_id"]: fact for fact in facts}


class PTSEEventObservationTest(unittest.TestCase):
    def test_only_future_cpi_nfp_fomc_are_adapted_and_no_score_is_created(self):
        facts = adapt_event_calendar(
            payload(), binding(), market_session="2026-10-02", decision_at=DECISION
        )
        self.assertEqual(len(facts), 6)
        got = by_id(facts)
        self.assertEqual(got["event_calendar.next_nfp_at"]["status"], "UNAVAILABLE")
        self.assertIsNone(got["event_calendar.next_nfp_at"]["value"])
        self.assertIn(
            "NO_NEGATIVE_INFERENCE",
            got["event_calendar.next_nfp_at"]["null_reason"],
        )
        self.assertIsNone(got["event_calendar.next_nfp_at"]["known_at"])
        cpi = got["event_calendar.next_cpi_at"]
        self.assertEqual(cpi["status"], "OBSERVED")
        self.assertEqual(cpi["economic_time_role"], "SCHEDULED_EVENT")
        self.assertEqual(cpi["unit"], "TIMESTAMP")
        self.assertEqual(cpi["value"], "2026-10-14T12:30:00Z")
        self.assertEqual(got["event_calendar.next_cpi_source"]["value"], "fred")
        self.assertTrue(all("authority" not in fact for fact in facts))
        self.assertTrue(all("impact" not in fact["feature_id"] for fact in facts))

    def test_static_fomc_is_preserved_as_source_not_promoted_to_pit(self):
        got = by_id(adapt_event_calendar(
            payload(), binding(), market_session="2026-10-02", decision_at=DECISION
        ))
        src = got["event_calendar.next_fomc_source"]
        self.assertEqual(src["value"], "static")
        self.assertTrue(any(
            "not historical publication-vintage evidence" in text
            for text in src["limitations"]
        ))

    def test_absent_rows_do_not_become_zero_or_not_applicable(self):
        p = payload()
        p["us_macro"] = []
        facts = adapt_event_calendar(
            p, binding(p), market_session="2026-10-02", decision_at=DECISION
        )
        for fact in facts:
            self.assertEqual(fact["status"], "UNAVAILABLE")
            self.assertIsNone(fact["value"])
            self.assertEqual(fact["coverage"]["numerator"], 0)
            self.assertEqual(fact["coverage"]["missing_count"], 1)

    def test_late_owner_availability_is_refused(self):
        with self.assertRaisesRegex(PTSEEventAdapterError, "NOT_KNOWN_AT_DECISION"):
            adapt_event_calendar(
                payload(), binding(latest="2026-10-02T20:00:01Z"),
                market_session="2026-10-02", decision_at=DECISION,
            )

    def test_context_only_and_future_snapshot_are_hard_gates(self):
        p = payload()
        p["is_context_only"] = False
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_CALENDAR_SCHEMA_INVALID"
        ):
            adapt_event_calendar(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_CALENDAR_FUTURE_SNAPSHOT"
        ):
            adapt_event_calendar(
                payload(), binding(), market_session="2026-10-01",
                decision_at=DECISION,
            )

    def test_prior_day_owner_snapshot_can_feed_next_market_session(self):
        p = payload()
        p["asof"] = "2026-10-01"
        facts = adapt_event_calendar(
            p, binding(p),
            market_session="2026-10-02",
            decision_at=DECISION,
        )
        got = by_id(facts)
        self.assertEqual(
            got["event_calendar.next_cpi_at"]["value"],
            "2026-10-14T12:30:00Z",
        )

    def test_owner_horizon_is_anchored_to_snapshot_not_shifted_by_market_session(self):
        p = payload()
        p["asof"] = "2026-10-01"
        p["horizon_days"] = 13
        p["us_macro"] = [copy.deepcopy(p["us_macro"][1])]
        # CPI on Oct 14 is exactly 13 days after the owner snapshot and remains valid.
        facts = adapt_event_calendar(
            p, binding(p),
            market_session="2026-10-02",
            decision_at=DECISION,
        )
        self.assertEqual(
            by_id(facts)["event_calendar.next_cpi_at"]["status"],
            "OBSERVED",
        )
        # Oct 15 is 14 days after the owner snapshot. A market-session-anchored
        # implementation would wrongly admit it because it is only 13 days from Oct 2.
        p["us_macro"][0]["date"] = "2026-10-15"
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_OUTSIDE_OWNER_WINDOW"
        ):
            adapt_event_calendar(
                p, binding(p),
                market_session="2026-10-02",
                decision_at=DECISION,
            )

    def test_non_context_event_row_is_refused(self):
        p = payload()
        p["us_macro"][1]["is_context_only"] = False
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_AUTHORITY_INVALID"
        ):
            adapt_event_calendar(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_event_outside_declared_owner_window_is_refused(self):
        p = payload()
        p["us_macro"][1]["date"] = "2026-11-01"
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_OUTSIDE_OWNER_WINDOW"
        ):
            adapt_event_calendar(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_same_timestamp_conflicting_sources_fail_closed(self):
        p = payload()
        cpi = copy.deepcopy(p["us_macro"][1])
        cpi["source"] = "static"
        p["us_macro"].append(cpi)
        with self.assertRaisesRegex(
            PTSEEventAdapterError, "EVENT_SOURCE_CONFLICT"
        ):
            adapt_event_calendar(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_facts_validate_inside_existing_ptse_contract(self):
        facts = adapt_event_calendar(
            payload(), binding(), market_session="2026-10-02", decision_at=DECISION
        )
        observation, assessment = inputs()
        observation["facts"] = facts
        assessment["drivers"] = []
        artifact = build_context(observation, assessment)
        self.assertTrue(artifact.sha256)

    def test_prospective_first_seen_event_context_is_readiness_eligible(self):
        facts = adapt_event_calendar(
            payload(), binding(grade="PROSPECTIVE_FIRST_SEEN"),
            market_session="2026-10-02", decision_at=DECISION,
        )
        observation, assessment = inputs()
        observation["facts"] = facts
        observation["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        assessment["drivers"] = []
        artifact = build_context(observation, assessment)
        ready = qualify_prospective_observation(artifact)
        self.assertEqual(ready.status, "READY_FOR_EXISTING_PUBLICATION_OWNER")
        self.assertFalse(ready.publication_authority)
        self.assertFalse(ready.decision_authority)

    def test_payload_receipt_is_content_bound_and_key_order_canonical(self):
        p = payload()
        facts = adapt_event_calendar(p, binding(p), market_session="2026-10-02", decision_at=DECISION)
        self.assertTrue(facts)
        reordered = dict(reversed(list(p.items())))
        facts2 = adapt_event_calendar(reordered, binding(p), market_session="2026-10-02", decision_at=DECISION)
        self.assertEqual(facts, facts2)

        mutated = copy.deepcopy(p)
        mutated["us_macro"][1]["date"] = "2026-10-15"
        with self.assertRaisesRegex(PTSEEventAdapterError, "EVENT_CALENDAR_ARTIFACT_REF_MISMATCH"):
            adapt_event_calendar(mutated, binding(p), market_session="2026-10-02", decision_at=DECISION)

    def test_source_mutation_with_old_receipt_is_refused(self):
        p = payload()
        mutated = copy.deepcopy(p)
        mutated["us_macro"][1]["source"] = "static"
        with self.assertRaisesRegex(PTSEEventAdapterError, "EVENT_CALENDAR_ARTIFACT_REF_MISMATCH"):
            adapt_event_calendar(mutated, binding(p), market_session="2026-10-02", decision_at=DECISION)


if __name__ == "__main__":
    unittest.main()
