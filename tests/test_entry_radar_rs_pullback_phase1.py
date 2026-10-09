"""SYNTHETIC_CONFORMANCE tests for the frozen offline Phase-1 input adapter.

These fixtures exercise input coverage and temporal contracts only. Scenario
names are coverage tags, never market evidence or validated detector outcomes.
No detector or launch/failure outcome is implemented or assessed here.
"""
from __future__ import annotations

import copy
import json
import math
import unittest
from datetime import datetime, timedelta, timezone

from engine.entry_radar.replay.rs_pullback_launch_data import (
    CENSUS_SCHEMA,
    INPUT_SCHEMA,
    SOURCE_REQUIREMENTS,
    InputContractError,
    assess_source_census,
    build_input_panel,
)


SHA = "a" * 64
SESSION = "2026-10-06"
PREVIOUS_SESSION = "2026-10-05"
ROLES = ("stock", "spy", "qqq", "sector")
# Input coverage labels only; every case retains NOT_COMPUTED_PHASE1 labels.
SCENARIO_TAGS = (
    "anticipated_launch_success", "valid_nonlaunch", "armed_without_30m_pivot",
    "pivot_formed_never_confirms", "pivot_confirms_then_fails", "stale_daily_context",
    "missing_intraday_interval", "catalyst_coverage_unknown",
    "same_bar_target_stop_ambiguity", "early_close_session_boundary",
)


def iso(instant):
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clock(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def receipt(**values):
    return {"source_ref": "SYNTHETIC_CONFORMANCE:fixture", "receipt_sha256": SHA,
            **values}


def candidate(identifier="earlier", decision="2026-10-06T14:00:00Z", session=SESSION):
    return {"candidate_id": identifier, "decision_at": decision, "session": session,
            "streams": {role: role for role in ROLES}}


def fixture(candidates=None, session=SESSION, previous=PREVIOUS_SESSION,
            opening="2026-10-06T13:30:00Z", closing="2026-10-06T20:00:00Z"):
    """Build recoverable synthetic minute receipts, never qualify market data."""
    start, end = clock(opening), clock(closing)
    first_known = iso(start - timedelta(days=1))
    streams = {}
    minutes = []
    for offset, role in enumerate(ROLES):
        identity = "SYNTHETIC:" + role
        streams[role] = {
            "security_id": identity,
            "availability_basis": "observed_first_seen",
            "identity": receipt(security_id=identity, known_at=first_known, valid_from=previous),
            "basis": receipt(known_at=first_known, basis_id="fixture-unadjusted",
                             price_adjustment="unadjusted", volume_adjustment="unadjusted",
                             corporate_actions_sha256=SHA),
        }
        for index in range(int((end - start).total_seconds() // 60)):
            instant = start + timedelta(minutes=index)
            price = 100 + offset * 10 + index / 100
            minutes.append(receipt(
                stream=role, security_id=identity, basis_id="fixture-unadjusted",
                revision_id=f"synthetic-{role}-{index}-v1", start=iso(instant),
                end=iso(instant + timedelta(minutes=1)),
                known_at=iso(instant + timedelta(minutes=1)),
                open=price, high=price + .5, low=price - .5, close=price + .1,
                volume=index + 1,
            ))
    prior_close = clock(previous + "T20:00:00Z")
    contexts = [
        receipt(kind="daily", security_id="SYNTHETIC:stock",
                known_at=iso(prior_close + timedelta(minutes=1)),
                asof_session=previous,
                payload={"is_leader": True, "controlled_pullback": True}),
        receipt(kind="incumbent", security_id="SYNTHETIC:stock", known_at=opening,
                asof_session=session, valid_until=closing,
                payload={"owner": "engine.entry_signal.assess", "buyable_input": True,
                         "inputs_sha256": SHA, "code_sha": "b" * 40,
                         "assessment": {"synthetic_conformance_only": True}}),
        receipt(kind="catalyst", security_id="SYNTHETIC:stock", known_at=opening,
                asof_session=session, valid_until=closing,
                payload={"coverage_state": "UNKNOWN"}),
    ]
    return {
        "schema": INPUT_SCHEMA, "input_kind": "SYNTHETIC_CONFORMANCE",
        "calendar": receipt(known_at=first_known,
                            sessions={previous: {"open": previous + "T13:30:00Z",
                                                 "close": iso(prior_close)},
                                      session: {"open": opening, "close": closing,
                                                "previous_session": previous}}),
        "streams": streams, "minutes": minutes, "contexts": contexts,
        "candidates": candidates if candidates is not None else [candidate()],
    }


def census():
    return {
        "schema": CENSUS_SCHEMA,
        "terminal_qualifier_args": {"from_date": "2026-10-01", "to_date": "2026-10-06",
                                    "cutoff_utc": 1791295200,
                                    "mode": "as_observed"},
        "required_symbols": {"stock": "SYNTHETIC_STOCK", "spy": "SPY",
                             "qqq": "QQQ", "sector": "SYNTHETIC_SECTOR"},
        "terminal_qualifier_reports": [
            {"symbol": symbol, "timeframe": "1m", "status": "available", "valid_rows": 30,
             "cutoff": {"mode": "as_observed", "pit_proven": True, "count": 30,
                        "utc": 1791295200},
             "qualification_window": {"from_date": "2026-10-01", "to_date": "2026-10-06"},
             "price_adjustment": "unadjusted", "volume_adjustment": "unadjusted",
             "sha256": SHA, "coverage": {"window_complete_grid": True}}
            for symbol in ("SYNTHETIC_STOCK", "SPY", "QQQ", "SYNTHETIC_SECTOR")
        ],
        "requirements": {requirement: {"status": "PROVEN",
                                       "evidence_refs": ["SYNTHETIC_CONFORMANCE:owner-proof"]}
                         for requirement in SOURCE_REQUIREMENTS},
    }


def frame_bytes(frame):
    """Compare the complete visible frame, including its own snapshot digest."""
    return json.dumps(frame, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def frame(bundle, index=0):
    return build_input_panel(bundle)["frames"][index]


def minute(bundle, start, role="stock"):
    return next(row for row in bundle["minutes"]
                if row["stream"] == role and row["start"] == start)


class Phase1InputConformanceTests(unittest.TestCase):
    def assert_same_earlier_frame(self, before, after):
        original, changed = build_input_panel(before), build_input_panel(after)
        self.assertEqual(original["frames"][0]["availability"], "available")
        self.assertEqual(frame_bytes(original["frames"][0]), frame_bytes(changed["frames"][0]))
        self.assertNotEqual(original["input_bundle_sha256"], changed["input_bundle_sha256"])
        return original, changed

    def test_complete_exact_15m_and_30m_ohlcv(self):
        panel = build_input_panel(fixture())
        result = panel["frames"][0]
        self.assertEqual(result["availability"], "available")
        self.assertIs(result["eligible"], True)
        for role_index, role in enumerate(ROLES):
            for width, first, expected_volume in ((15, 15, 345), (30, 0, 465)):
                bar = result["bars"][role][str(width)]
                self.assertEqual(bar["expected_minutes"], width)
                self.assertEqual(bar["observed_minutes"], width)
                self.assertEqual(bar["missing_starts"], [])
                self.assertEqual(bar["refusals"], [])
                self.assertEqual(bar["availability"], "available")
                values = bar["ohlcv"]
                self.assertAlmostEqual(values["open"], 100 + role_index * 10 + first / 100)
                self.assertAlmostEqual(values["high"], 100 + role_index * 10 + .29 + .5)
                self.assertAlmostEqual(values["low"], 100 + role_index * 10 + first / 100 - .5)
                self.assertAlmostEqual(values["close"], 100 + role_index * 10 + .29 + .1)
                self.assertEqual(values["volume"], expected_volume)
                self.assertEqual(bar["known_at"], "2026-10-06T14:00:00Z")
        self.assertEqual(panel["status"], "SYNTHETIC_CONFORMANCE_ONLY")
        self.assertFalse(panel["detector_registered"])
        self.assertFalse(panel["outcomes_computed"])
        self.assertIsNone(result["condition_met"])
        self.assertEqual(result["label_status"], "NOT_COMPUTED_PHASE1")

    def test_later_one_minute_values_do_not_change_full_earlier_frame(self):
        original = fixture()
        changed = copy.deepcopy(original)
        for row in changed["minutes"]:
            if clock(row["start"]) >= clock("2026-10-06T14:00:00Z"):
                for key in ("open", "high", "low", "close"):
                    row[key] += 50
                row["volume"] *= 10
        self.assert_same_earlier_frame(original, changed)

    def test_malformed_future_event_is_invisible_until_its_receipt_is_eligible(self):
        original = fixture()
        changed = copy.deepcopy(original)
        future = copy.deepcopy(minute(changed, "2026-10-06T13:59:00Z"))
        future.update(start="malformed-future-event", known_at="2026-10-06T15:11:00Z",
                      revision_id="synthetic-future-malformed-event")
        changed["minutes"].append(future)
        self.assert_same_earlier_frame(original, changed)
        future["known_at"] = "2026-10-06T14:00:00Z"
        with self.assertRaises(InputContractError):
            build_input_panel(changed)

    def test_later_half_of_unfinished_30m_does_not_change_full_earlier_frame(self):
        original = fixture([candidate(decision="2026-10-06T14:15:00Z")])
        changed = copy.deepcopy(original)
        for row in changed["minutes"]:
            if "2026-10-06T14:15:00Z" <= row["start"] < "2026-10-06T14:30:00Z":
                for key in ("open", "high", "low", "close"):
                    row[key] += 75
                row["volume"] += 5000
        before, _ = self.assert_same_earlier_frame(original, changed)
        self.assertEqual(before["frames"][0]["bars"]["stock"]["30"]["end"],
                         "2026-10-06T14:00:00Z")
        self.assertEqual(before["frames"][0]["bars"]["stock"]["15"]["end"],
                         "2026-10-06T14:15:00Z")

    def test_later_daily_close_and_backdated_same_day_final_cannot_change_earlier_frame(self):
        original = fixture()
        changed = copy.deepcopy(original)
        changed["contexts"].extend([
            receipt(kind="daily", security_id="SYNTHETIC:stock",
                    asof_session=PREVIOUS_SESSION, known_at="2026-10-06T14:01:00Z",
                    payload={"is_leader": False, "controlled_pullback": False, "close": 1}),
            receipt(kind="daily", security_id="SYNTHETIC:stock",
                    asof_session=SESSION, known_at="2026-10-06T13:00:00Z",
                    payload={"is_leader": False, "controlled_pullback": False, "close": 999}),
        ])
        self.assert_same_earlier_frame(original, changed)
        # Mutating final closes and flags is also invisible; neither record can
        # participate in the earlier daily snapshot.
        changed["contexts"][-2]["payload"]["close"] = 2000
        changed["contexts"][-1]["payload"]["close"] = 3000
        self.assert_same_earlier_frame(original, changed)

    def test_historical_correction_is_visible_only_to_later_eligible_snapshot(self):
        original = fixture([candidate(), candidate("later", "2026-10-06T14:15:00Z")])
        changed = copy.deepcopy(original)
        correction = copy.deepcopy(minute(changed, "2026-10-06T13:50:00Z"))
        correction.update(known_at="2026-10-06T14:10:00Z", revision_id="synthetic-correction-v2",
                          open=180, high=182, low=179, close=181, volume=9000,
                          receipt_sha256="c" * 64)
        changed["minutes"].append(correction)
        before, after = self.assert_same_earlier_frame(original, changed)
        self.assertIs(after["frames"][1]["eligible"], True)
        self.assertEqual(after["frames"][1]["availability"], "available")
        self.assertNotEqual(frame_bytes(before["frames"][1]), frame_bytes(after["frames"][1]))
        self.assertEqual(after["frames"][1]["bars"]["stock"]["30"]["ohlcv"]["high"], 182)
        self.assertEqual(after["frames"][1]["bars"]["stock"]["30"]["ohlcv"]["volume"],
                         465 - 21 + 9000)

    def test_two_second_delayed_receipt_is_unavailable_at_exact_bar_boundary(self):
        bundle = fixture([candidate(), candidate("received", "2026-10-06T14:00:02Z")])
        minute(bundle, "2026-10-06T13:59:00Z")["known_at"] = "2026-10-06T14:00:02Z"
        before, after = build_input_panel(bundle)["frames"]
        self.assertEqual(before["availability"], "unavailable")
        self.assertIsNone(before["eligible"])
        for width in ("15", "30"):
            self.assertIsNone(before["bars"]["stock"][width]["ohlcv"])
            self.assertIn("stock:" + width + "m:MISSING_OR_NOT_YET_KNOWN_MINUTE", before["refusals"])
        self.assertEqual(after["availability"], "available")

    def test_missing_minute_and_uncompleted_interval_remain_null_never_false(self):
        bundle = fixture()
        bundle["minutes"].remove(minute(bundle, "2026-10-06T13:59:00Z"))
        result = frame(bundle)
        self.assertIsNone(result["eligible"])
        self.assertIsNone(result["condition_met"])
        self.assertIsNone(result["bars"]["stock"]["15"]["ohlcv"])
        self.assertEqual(result["bars"]["stock"]["15"]["missing_starts"],
                         ["2026-10-06T13:59:00Z"])
        early = frame(fixture([candidate(decision="2026-10-06T13:40:00Z")]))
        self.assertIsNone(early["eligible"])
        self.assertIsNone(early["bars"]["stock"]["15"])
        self.assertIsNone(early["bars"]["stock"]["30"])

    def test_stale_individual_daily_row_cannot_be_refreshed_by_parent(self):
        bundle = fixture()
        bundle["known_at"] = "2026-10-06T13:59:00Z"
        bundle["contexts"][0]["asof_session"] = "2026-10-02"
        bundle["contexts"][0]["known_at"] = "2026-10-06T13:59:00Z"
        result = frame(bundle)
        self.assertEqual(result["availability"], "stale")
        self.assertEqual(result["refusals"], ["daily:STALE_ROW"])
        self.assertIsNone(result["daily_context"])
        self.assertIsNone(result["eligible"])

    def test_missing_incumbent_buyable_input_refuses_faithful_owner_receipt(self):
        bundle = fixture()
        del bundle["contexts"][1]["payload"]["buyable_input"]
        result = frame(bundle)
        self.assertEqual(result["availability"], "unavailable")
        self.assertIn("incumbent:FAITHFUL_OWNER_RECEIPT_MISSING", result["refusals"])
        self.assertIsNone(result["incumbent_assessment"])
        self.assertIsNone(result["eligible"])

    def test_unknown_absent_and_unrecognized_catalyst_do_not_become_no_event(self):
        for state in ("UNKNOWN", "NOT_RECORDED", None):
            with self.subTest(state=state):
                bundle = fixture()
                bundle["contexts"][2]["payload"]["coverage_state"] = state
                result = frame(bundle)
                self.assertEqual(result["availability"], "available")
                self.assertEqual(result["catalyst_state"], "UNKNOWN")
        bundle = fixture()
        bundle["contexts"].pop()
        self.assertEqual(frame(bundle)["catalyst_state"], "UNKNOWN")

    def test_identity_and_adjustment_basis_mismatch_refuse_input(self):
        for key, value, refusal in (
            ("security_id", "SYNTHETIC:wrong", "MINUTE_IDENTITY_MISMATCH"),
            ("basis_id", "other-adjustment-basis", "MINUTE_BASIS_MISMATCH"),
        ):
            with self.subTest(key=key):
                bundle = fixture()
                minute(bundle, "2026-10-06T13:59:00Z")[key] = value
                result = frame(bundle)
                self.assertIsNone(result["eligible"])
                self.assertIsNone(result["bars"]["stock"]["15"]["ohlcv"])
                self.assertIn("stock:15m:" + refusal, result["refusals"])
        bundle = fixture()
        bundle["streams"]["stock"]["identity"]["valid_until"] = SESSION
        self.assertIn("stock:IDENTITY_NOT_BOUND_AT_DECISION", frame(bundle)["refusals"])
        bundle = fixture()
        bundle["streams"]["stock"]["basis"]["price_adjustment"] = "unknown"
        self.assertIn("stock:BASIS_NOT_BOUND_AT_DECISION", frame(bundle)["refusals"])

    def test_exact_duplicate_is_idempotent_but_conflicting_revision_is_refused(self):
        original = fixture()
        duplicate = copy.deepcopy(original)
        duplicate["minutes"].append(copy.deepcopy(minute(duplicate, "2026-10-06T13:59:00Z")))
        self.assert_same_earlier_frame(original, duplicate)
        duplicate["minutes"][-1]["volume"] += 1
        result = frame(duplicate)
        self.assertIn("stock:15m:CONFLICTING_MINUTE_REVISION", result["refusals"])
        self.assertIsNone(result["bars"]["stock"]["15"]["ohlcv"])
        self.assertIsNone(result["eligible"])
        daily_conflict = fixture()
        context = copy.deepcopy(daily_conflict["contexts"][0])
        context["payload"]["is_leader"] = False
        daily_conflict["contexts"].append(context)
        self.assertIn("daily:CONFLICTING_REVISION", frame(daily_conflict)["refusals"])

    def test_invalid_numeric_values_and_ohlcv_geometry_cannot_be_available(self):
        for key, value, code in (
            ("open", 0, "INVALID_OHLCV"), ("open", True, "INVALID_OHLCV"),
            ("volume", -1, "INVALID_OHLCV"), ("volume", True, "INVALID_OHLCV"),
            ("high", 50, "INVALID_OHLCV_GEOMETRY"),
            ("low", 200, "INVALID_OHLCV_GEOMETRY"),
        ):
            with self.subTest(key=key, value=value):
                bundle = fixture()
                minute(bundle, "2026-10-06T13:59:00Z")[key] = value
                result = frame(bundle)
                self.assertIn("stock:15m:" + code, result["refusals"])
                self.assertIsNone(result["bars"]["stock"]["15"]["ohlcv"])
                self.assertIsNone(result["eligible"])
        # Nonfinite input is rejected by canonical JSON serialization as well
        # as the aggregate's safety check; no usable frame may escape.
        for key in ("open", "volume"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(key=key, value=value):
                    bundle = fixture()
                    minute(bundle, "2026-10-06T13:59:00Z")[key] = value
                    with self.assertRaises(ValueError):
                        build_input_panel(bundle)

    def test_early_close_and_end_of_rth_censor_exact_owner_calendar_without_rollover(self):
        session = "2026-07-02"
        opening, closing = "2026-07-02T13:30:00Z", "2026-07-02T17:00:00Z"
        candidates = [candidate("early-close", "2026-07-02T16:30:00Z", session),
                      candidate("close", closing, session),
                      candidate("after-close", "2026-07-02T17:00:01Z", session)]
        bundle = fixture(candidates, session, "2026-07-01", opening, closing)
        early, end, after = build_input_panel(bundle)["frames"]
        for result in (early, end):
            self.assertEqual(result["availability"], "available")
            self.assertEqual(result["label_status"], "CENSORED_SESSION_END")
            self.assertEqual(result["label_endpoint"], closing)
            for role in ROLES:
                self.assertLessEqual(result["bars"][role]["30"]["end"], closing)
        self.assertEqual(end["bars"]["stock"]["15"]["end"], closing)
        self.assertEqual(end["bars"]["stock"]["30"]["end"], closing)
        self.assertEqual(after["refusals"], ["DECISION_OUTSIDE_RTH"])
        self.assertIsNone(after["label_endpoint"])
        self.assertEqual(after["bars"], {})

    def test_holiday_and_before_open_never_use_adjacent_session_bars(self):
        bundle = fixture([candidate("holiday", "2026-07-03T14:00:00Z", "2026-07-03"),
                          candidate("before-open", "2026-07-02T13:29:59Z", "2026-07-02")],
                         "2026-07-02", "2026-07-01", "2026-07-02T13:30:00Z",
                         "2026-07-02T17:00:00Z")
        holiday, before_open = build_input_panel(bundle)["frames"]
        self.assertEqual(holiday["refusals"], ["SESSION_NOT_IN_OWNER_CALENDAR"])
        self.assertEqual(before_open["refusals"], ["DECISION_OUTSIDE_RTH"])
        for result in (holiday, before_open):
            self.assertIsNone(result["eligible"])
            self.assertEqual(result["bars"], {})
            self.assertIsNone(result["label_endpoint"])

    def test_all_predeclared_ids_and_ten_synthetic_coverage_tags_survive_without_future_pivot_filter(self):
        candidates = []
        for index, tag in enumerate(SCENARIO_TAGS):
            value = candidate("synthetic-coverage-" + tag)
            value["scenario_tag"] = tag
            value["future_pivot"] = index % 2 == 0
            candidates.append(value)
        # One honestly unavailable row and one observed but ineligible row must
        # survive alongside every tag and both future-pivot flags.
        candidates[0]["decision_at"] = "2026-10-06T13:40:00Z"
        bundle = fixture(candidates)
        bundle["contexts"][0]["payload"]["is_leader"] = False
        panel = build_input_panel(bundle)
        self.assertEqual(len(set(SCENARIO_TAGS)), 10)
        self.assertEqual(panel["population_count"], 10)
        self.assertEqual(panel["retained_count"], 10)
        self.assertEqual([item["candidate_id"] for item in panel["frames"]],
                         [item["candidate_id"] for item in candidates])
        self.assertIsNone(panel["frames"][0]["eligible"])
        self.assertIs(panel["frames"][1]["eligible"], False)
        for result in panel["frames"]:
            self.assertIsNone(result["condition_met"])
            self.assertEqual(result["label_status"], "NOT_COMPUTED_PHASE1")
        self.assertFalse(panel["detector_registered"])
        self.assertFalse(panel["outcomes_computed"])

    def test_ten_named_coverage_cases_construct_inputs_without_claiming_detector_results(self):
        expected_ids = []
        retained_ids = []
        for tag in SCENARIO_TAGS:
            with self.subTest(synthetic_coverage=tag):
                item = candidate("synthetic-case-" + tag)
                item["scenario_tag"] = tag
                # Eventual pivot metadata is deliberately extraneous input;
                # neither its absence nor false value can filter a candidate.
                if tag in {"armed_without_30m_pivot", "valid_nonlaunch"}:
                    item["future_pivot"] = False
                bundle = fixture([item])
                if tag == "stale_daily_context":
                    bundle["contexts"][0]["asof_session"] = "2026-10-02"
                elif tag == "missing_intraday_interval":
                    bundle["minutes"].remove(minute(bundle, "2026-10-06T13:59:00Z"))
                elif tag == "catalyst_coverage_unknown":
                    bundle["contexts"].pop()
                elif tag == "early_close_session_boundary":
                    early_session = "2026-07-02"
                    item = candidate("synthetic-case-" + tag, "2026-07-02T16:30:00Z", early_session)
                    item["scenario_tag"] = tag
                    bundle = fixture([item], early_session, "2026-07-01",
                                     "2026-07-02T13:30:00Z", "2026-07-02T17:00:00Z")
                panel = build_input_panel(bundle)
                result = panel["frames"][0]
                expected_ids.append(item["candidate_id"])
                retained_ids.append(result["candidate_id"])
                self.assertEqual(panel["retained_count"], 1)
                self.assertEqual(panel["input_kind"], "SYNTHETIC_CONFORMANCE")
                self.assertFalse(panel["detector_registered"])
                self.assertFalse(panel["outcomes_computed"])
                self.assertIsNone(result["condition_met"])
                if tag == "stale_daily_context":
                    self.assertEqual(result["availability"], "stale")
                    self.assertIsNone(result["eligible"])
                elif tag == "missing_intraday_interval":
                    self.assertEqual(result["availability"], "unavailable")
                    self.assertIsNone(result["eligible"])
                else:
                    self.assertEqual(result["availability"], "available")
                if tag == "catalyst_coverage_unknown":
                    self.assertEqual(result["catalyst_state"], "UNKNOWN")
                if tag == "early_close_session_boundary":
                    self.assertEqual(result["label_status"], "CENSORED_SESSION_END")
                    self.assertEqual(result["label_endpoint"], "2026-07-02T17:00:00Z")
                else:
                    self.assertEqual(result["label_status"], "NOT_COMPUTED_PHASE1")
        self.assertEqual(retained_ids, expected_ids)

    def test_identity_receipt_must_explicitly_bind_the_stream_security_id(self):
        for bound_id in (None, "SYNTHETIC:other-security"):
            with self.subTest(identity_security_id=bound_id):
                bundle = fixture()
                if bound_id is None:
                    del bundle["streams"]["stock"]["identity"]["security_id"]
                else:
                    bundle["streams"]["stock"]["identity"]["security_id"] = bound_id
                result = frame(bundle)
                self.assertEqual(result["availability"], "unavailable")
                self.assertIn("stock:IDENTITY_NOT_BOUND_AT_DECISION", result["refusals"])
                self.assertIsNone(result["eligible"])

    def test_daily_completion_requires_valid_prior_owner_session_clock(self):
        for prior_law in (None, {}, {"close": "2026-10-06T13:30:00Z"},
                          {"close": "2026-10-06T14:00:00Z"}):
            with self.subTest(prior_calendar_law=prior_law):
                bundle = fixture()
                if prior_law is None:
                    del bundle["calendar"]["sessions"][PREVIOUS_SESSION]
                else:
                    bundle["calendar"]["sessions"][PREVIOUS_SESSION] = prior_law
                result = frame(bundle)
                self.assertIn("daily:COMPLETION_CLOCK_UNPROVEN", result["refusals"])
                self.assertEqual(result["availability"], "unavailable")
                self.assertIsNone(result["daily_context"])
                self.assertIsNone(result["eligible"])
        # A stale individual asof is refused for staleness before consulting
        # the prior completion clock; parent freshness does not repair it.
        bundle = fixture()
        bundle["contexts"][0]["asof_session"] = "2026-10-02"
        del bundle["calendar"]["sessions"][PREVIOUS_SESSION]
        result = frame(bundle)
        self.assertEqual(result["refusals"], ["daily:STALE_ROW"])
        self.assertEqual(result["availability"], "stale")

    def test_daily_receipt_cannot_precede_prior_close_but_boundary_is_allowed(self):
        prior_close = fixture()["calendar"]["sessions"][PREVIOUS_SESSION]["close"]
        for instant in ("2026-10-05T13:00:00Z", "2026-10-05T19:59:59Z"):
            with self.subTest(daily_known_at=instant):
                bundle = fixture()
                bundle["contexts"][0]["known_at"] = instant
                result = frame(bundle)
                self.assertIn("daily:RECEIPT_BEFORE_SESSION_CLOSE", result["refusals"])
                self.assertEqual(result["availability"], "unavailable")
                self.assertIsNone(result["daily_context"])
                self.assertIsNone(result["eligible"])
        bundle = fixture()
        bundle["contexts"][0]["known_at"] = prior_close
        self.assertEqual(frame(bundle)["availability"], "available")

    def test_incumbent_requires_nonempty_mapping_and_bool_or_explicit_null_buyable(self):
        for assessment in ({}, [], ["assessment"], "assessment", False, None):
            with self.subTest(assessment=assessment):
                bundle = fixture()
                bundle["contexts"][1]["payload"]["assessment"] = assessment
                result = frame(bundle)
                self.assertIn("incumbent:FAITHFUL_OWNER_RECEIPT_MISSING", result["refusals"])
                self.assertIsNone(result["incumbent_assessment"])
                self.assertIsNone(result["eligible"])
        for buyable in ("yes", "False", 0, 1, {}, []):
            with self.subTest(buyable_input=buyable):
                bundle = fixture()
                bundle["contexts"][1]["payload"]["buyable_input"] = buyable
                self.assertIn("incumbent:FAITHFUL_OWNER_RECEIPT_MISSING", frame(bundle)["refusals"])
        for buyable in (True, False, None):
            with self.subTest(valid_buyable_input=buyable):
                bundle = fixture()
                bundle["contexts"][1]["payload"]["buyable_input"] = buyable
                result = frame(bundle)
                self.assertEqual(result["availability"], "available")
                self.assertIs(result["incumbent_assessment"]["payload"]["buyable_input"], buyable)
                self.assertIs(result["eligible"], True)

    def test_adjustment_labels_are_known_nonempty_strings_in_stream_and_census(self):
        for value in (False, True, 0, 17, "", "   ", "UNKNOWN", "unknown"):
            for key in ("price_adjustment", "volume_adjustment"):
                with self.subTest(adjustment=key, value=value):
                    bundle = fixture()
                    bundle["streams"]["stock"]["basis"][key] = value
                    result = frame(bundle)
                    self.assertIn("stock:BASIS_NOT_BOUND_AT_DECISION", result["refusals"])
                    self.assertIsNone(result["eligible"])
                    value_census = census()
                    value_census["terminal_qualifier_reports"][0][key] = value
                    admission = assess_source_census(value_census)
                    self.assertEqual(admission["verdict"], "NOT_ADMITTED")
                    self.assertIn("stock:ADJUSTMENT_BASIS_UNRECORDED", admission["refusals"])

    def test_malformed_population_and_calendar_are_contract_errors(self):
        for candidates in ([], [candidate(), candidate()]):
            with self.subTest(candidates=candidates):
                with self.assertRaises(InputContractError):
                    build_input_panel(fixture(candidates))
        bundle = fixture()
        del bundle["calendar"]["receipt_sha256"]
        with self.assertRaises(InputContractError):
            build_input_panel(bundle)
        bundle = fixture()
        bundle["candidates"][0]["decision_at"] = "2026-10-06T14:00:00"
        with self.assertRaises(InputContractError):
            build_input_panel(bundle)


class Phase1SourceCensusTests(unittest.TestCase):
    def test_failed_source_report_cannot_admit_nominal_history(self):
        value = census()
        report = value["terminal_qualifier_reports"][0]
        report.update(status="unavailable", valid_rows=0,
                      cutoff={"mode": "not_recorded", "pit_proven": False, "count": 0},
                      price_adjustment="unknown", volume_adjustment="unknown", sha256=None,
                      coverage={"window_complete_grid": False})
        result = assess_source_census(value)
        self.assertEqual(result["verdict"], "NOT_ADMITTED")
        self.assertFalse(result["technical_requirements_met"])
        for refusal in ("NO_1M_HISTORY", "AS_OBSERVED_AVAILABILITY_UNPROVEN",
                        "ADJUSTMENT_BASIS_UNRECORDED", "IMMUTABLE_INPUT_UNIDENTIFIED",
                        "INCOMPLETE_NOMINAL_GRID"):
            self.assertIn("stock:" + refusal, result["refusals"])

    def test_positive_five_minute_control_never_substitutes_required_one_minute(self):
        value = census()
        value["terminal_qualifier_reports"][0]["timeframe"] = "5m"
        result = assess_source_census(value)
        self.assertEqual(result["verdict"], "NOT_ADMITTED")
        self.assertIn("stock:MISSING_OR_DUPLICATE_1M_OWNER_REPORT", result["refusals"])

    def test_available_status_with_missing_requirement_never_becomes_fresh_or_admitted(self):
        for requirement in SOURCE_REQUIREMENTS:
            with self.subTest(requirement=requirement):
                value = census()
                del value["requirements"][requirement]
                result = assess_source_census(value)
                self.assertEqual(result["verdict"], "NOT_ADMITTED")
                self.assertFalse(result["technical_requirements_met"])
                self.assertIn(requirement + ":NOT_PROVEN", result["refusals"])
        value = census()
        value["requirements"][SOURCE_REQUIREMENTS[0]]["evidence_refs"] = []
        self.assertEqual(assess_source_census(value)["verdict"], "NOT_ADMITTED")

    def test_all_owner_proofs_require_owner_review_and_never_grant_admission(self):
        result = assess_source_census(census())
        self.assertEqual(result["verdict"], "OWNER_REVIEW_REQUIRED")
        self.assertTrue(result["technical_requirements_met"])
        self.assertEqual(result["refusals"], [])
        self.assertTrue(result["admission_owner_decision_required"])
        self.assertFalse(result["market_outcomes_read"])
        self.assertEqual(result["scientific_claims"],
                         {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"})

    def test_qualifier_report_is_bound_to_requested_cutoff_and_window(self):
        for report_cutoff in (None, 1791295201, 1791208800, "2026-10-06T14:00:00Z"):
            with self.subTest(report_cutoff=report_cutoff):
                value = census()
                cutoff = value["terminal_qualifier_reports"][0]["cutoff"]
                if report_cutoff is None:
                    del cutoff["utc"]
                else:
                    cutoff["utc"] = report_cutoff
                result = assess_source_census(value)
                self.assertEqual(result["verdict"], "NOT_ADMITTED")
                self.assertIn("stock:QUALIFICATION_CUTOFF_MISMATCH", result["refusals"])
        for window in (None, {"from_date": "2026-09-01", "to_date": "2026-10-06"},
                       {"from_date": "2026-10-01", "to_date": "2026-10-05"}, {}):
            with self.subTest(qualification_window=window):
                value = census()
                if window is None:
                    del value["terminal_qualifier_reports"][0]["qualification_window"]
                else:
                    value["terminal_qualifier_reports"][0]["qualification_window"] = window
                result = assess_source_census(value)
                self.assertEqual(result["verdict"], "NOT_ADMITTED")
                self.assertIn("stock:QUALIFICATION_WINDOW_MISMATCH", result["refusals"])
        result = assess_source_census(census())
        self.assertEqual(result["verdict"], "OWNER_REVIEW_REQUIRED")
        self.assertEqual(result["refusals"], [])

    def test_duplicate_required_owner_report_and_missing_role_are_rejected(self):
        value = census()
        value["terminal_qualifier_reports"].append(copy.deepcopy(value["terminal_qualifier_reports"][0]))
        self.assertIn("stock:MISSING_OR_DUPLICATE_1M_OWNER_REPORT",
                      assess_source_census(value)["refusals"])
        value = census()
        del value["required_symbols"]["sector"]
        with self.assertRaises(InputContractError):
            assess_source_census(value)


class Phase1LeaderPivotConsumerSuiteTests(unittest.TestCase):
    """Execute the previously unowned pivot cases under the existing Phase-1 CI owner.

    Research-price-panel already selects this Phase-1 source suite. This
    integrity assertion runs the original test classes by normal module import,
    instead of adding another CI job, changing selection manifests or masking a
    failure. Its result is still synthetic conformance, never market admission.
    """

    def test_pivot_consumer_65_case_conformance(self):
        from tests.test_entry_radar_leader_pivot_descriptor import LeaderPivotDescriptorTests
        from tests.test_entry_radar_leader_pivot_progress import LeaderPivotProgressTests
        from tests.test_entry_radar_leader_pivot_progress_edges import LeaderPivotProgressEdgeTests

        classes = (
            LeaderPivotDescriptorTests,
            LeaderPivotProgressTests,
            LeaderPivotProgressEdgeTests,
        )
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes
        )
        result = unittest.TestResult()
        suite.run(result)

        failures = [(case.id(), traceback) for case, traceback in result.failures]
        errors = [(case.id(), traceback) for case, traceback in result.errors]
        self.assertEqual(result.testsRun, 65, "pivot consumer test count drift")
        self.assertEqual(result.skipped, [], "pivot consumer tests cannot silently skip")
        self.assertEqual(failures, [], "pivot consumer failures: " + repr(failures[:2]))
        self.assertEqual(errors, [], "pivot consumer errors: " + repr(errors[:2]))


    def test_first_green_comparator_21_case_conformance(self):
        """Run the separate first-green research comparator under the existing CI owner."""
        from tests.test_entry_radar_first_green_descriptor import (
            FirstGreenFormationTests, FirstGreenProgressTests,
        )
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(cls)
            for cls in (FirstGreenFormationTests, FirstGreenProgressTests)
        )
        result = unittest.TestResult()
        suite.run(result)
        failures = [(case.id(), tb) for case, tb in result.failures]
        errors = [(case.id(), tb) for case, tb in result.errors]
        self.assertEqual(result.testsRun, 21, "first-green comparator case count drift")
        self.assertEqual(result.skipped, [], "first-green comparator cases cannot skip")
        self.assertEqual(failures, [], "first-green comparator failures: " + repr(failures[:2]))
        self.assertEqual(errors, [], "first-green comparator errors: " + repr(errors[:2]))



if __name__ == "__main__":
    unittest.main()
