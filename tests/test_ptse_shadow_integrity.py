"""Adversarial shadow-row integrity regressions, using synthetic owner fixtures."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

from research.options_estate.ptse_contract import build_context
from research.options_estate.ptse_shadow_enrollment import (
    PTSEShadowEnrollmentError,
    build_shadow_enrollment,
    validate_shadow_enrollment,
)
from research.options_estate.ptse_shadow_outcome import (
    PTSEShadowOutcomeError,
    project_shadow_outcome,
)
from tests.test_ptse_prospective_readiness import prospective_new_entry
from tests.test_ptse_shadow_enrollment import candidate, snapshot
from tests.test_ptse_shadow_outcome import grade, grade_ref


def reseal(row):
    """An untrusted caller can calculate a checksum; it is not authentication."""
    semantic = {key: value for key, value in row.items() if key != "enrollment_id"}
    raw = json.dumps(semantic, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    row["enrollment_id"] = "ptse-shadow:" + hashlib.sha256(raw).hexdigest()
    return row


def valid_row(*, present=True):
    return build_shadow_enrollment(
        candidate_row=candidate(), b1_snapshot=snapshot(),
        context=prospective_new_entry() if present else None,
    )


class PTSEShadowIntegrityTest(unittest.TestCase):
    def test_false_is_a_boolean_contract_not_numeric_equality(self):
        for value in (0, 0.0, None, "false", True):
            with self.subTest(value=value):
                row = valid_row()
                row["authority"]["trade"] = value
                with self.assertRaises(PTSEShadowEnrollmentError):
                    validate_shadow_enrollment(reseal(row))

    def test_resealed_inconsistent_context_presence_and_status_is_refused(self):
        changes = (
            (False, {"context_status": "AVAILABLE", "context_reason": "OBSERVED_CONTEXT_ONLY"}),
            (False, {"context_status": "PARTIAL", "context_reason": "SOME_FACTS_NOT_OBSERVED"}),
            (False, {"context_status": "ABSTAINED", "context_reason": "ACTION_ABSTAINED"}),
            (True, {"context_reason": "CONTEXT_MISSING"}),
            (True, {"context_status": "PARTIAL", "context_reason": "OBSERVED_CONTEXT_ONLY"}),
            (True, {"context_status": "AVAILABLE", "context_reason": "ACTION_ABSTAINED"}),
        )
        for present, update in changes:
            with self.subTest(present=present, update=update):
                row = valid_row(present=present)
                row.update(update)
                with self.assertRaises(PTSEShadowEnrollmentError):
                    validate_shadow_enrollment(reseal(row))

    def test_resealed_invalid_keys_dates_and_artifact_ids_are_refused(self):
        changes = (
            ("stamp_date", "2026-02-31"), ("stamp_date", "20260918"),
            ("stamp_date", "2026-09-18T00:00:00Z"),
            ("ticker", "MSFT"), ("board_definition", "another_board"),
            ("candidate_source_event_id", "candidate:2026-09-18:MSFT:us_prophet_v3"),
            ("episode_id", None), ("episode_id", ""), ("security_id", 4),
            ("company_id", {}), ("identity_epoch", "\n"),
            ("candidate_generation_id", False),
            ("context_sha256", "f" * 63), ("context_sha256", "G" * 64),
            ("observation_id", "not-an-observation"),
            ("assessment_id", "assessment:" + "z" * 64),
        )
        for field, value in changes:
            with self.subTest(field=field, value=value):
                row = valid_row()
                row[field] = value
                with self.assertRaises(PTSEShadowEnrollmentError):
                    validate_shadow_enrollment(reseal(row))

    def test_relabelled_ticker_cannot_reach_another_shared_grader_row(self):
        row = valid_row()
        row["ticker"] = "MSFT"
        matched_grade = grade(ticker="MSFT")
        with self.assertRaisesRegex(PTSEShadowOutcomeError, "ENROLLMENT_INVALID"):
            project_shadow_outcome(
                enrollment=reseal(row), grade_rows=[matched_grade], horizon=10,
                grade_row_ref=grade_ref(matched_grade),
            )

    def test_context_is_bound_to_the_candidate_observation_session(self):
        for stamp in ("2026-09-17", "2026-09-19"):
            with self.subTest(stamp=stamp):
                source_id = f"candidate:{stamp}:AAPL:us_prophet_v3"
                with self.assertRaisesRegex(
                    PTSEShadowEnrollmentError, "SHADOW_MARKET_SESSION_MISMATCH"
                ):
                    build_shadow_enrollment(
                        candidate_row=candidate(stamp_date=stamp),
                        b1_snapshot=snapshot(source_ids=[source_id]),
                        context=prospective_new_entry(),
                    )

    def test_prospective_enrollment_reuses_readiness_expiry_guard(self):
        payload = prospective_new_entry().to_dict()
        payload["observation"]["issued_at"] = "2026-09-18T21:00:00Z"
        payload["observation"]["valid_until"] = "2026-09-18T20:30:00Z"
        payload["assessment"]["issued_at"] = "2026-09-18T21:00:00Z"
        payload["observation"].pop("observation_id")
        payload["assessment"].pop("observation_id")
        payload["assessment"].pop("assessment_id")
        art = build_context(payload["observation"], payload["assessment"])
        with self.assertRaisesRegex(
            PTSEShadowEnrollmentError, "SHADOW_PROSPECTIVE_NOT_READY"
        ):
            build_shadow_enrollment(
                candidate_row=candidate(), b1_snapshot=snapshot(), context=art,
            )

    def test_builder_refuses_impossible_candidate_stamp_even_without_context(self):
        stamp = "2026-02-31"
        with self.assertRaisesRegex(PTSEShadowEnrollmentError, "SHADOW_STAMP_INVALID"):
            build_shadow_enrollment(
                candidate_row=candidate(stamp_date=stamp),
                b1_snapshot=snapshot(source_ids=[f"candidate:{stamp}:AAPL:us_prophet_v3"]),
                context=None,
            )

    def test_valid_prospective_and_unavailable_outputs_stay_deterministic(self):
        for present in (True, False):
            row = valid_row(present=present)
            original = copy.deepcopy(row)
            validate_shadow_enrollment(row)
            self.assertEqual(row, original)
            self.assertEqual(row, valid_row(present=present))

    def test_invalid_grade_collection_cannot_masquerade_as_pending(self):
        for rows in ([None], [7], [[]], [{}], [None, grade()], bytearray(b"abc")):
            with self.subTest(rows=rows):
                with self.assertRaises(PTSEShadowOutcomeError):
                    project_shadow_outcome(enrollment=valid_row(), grade_rows=rows, horizon=10)

    def test_source_grade_horizon_is_a_registered_literal_integer(self):
        for horizon in (10.0, "10", None, True, 10.5, 5):
            with self.subTest(horizon=horizon):
                source_grade = grade(horizon=horizon)
                ref = grade_ref(source_grade)
                ref["artifact_id"] = "grade:2026-09-18:AAPL:us_prophet_v3:10"
                with self.assertRaisesRegex(PTSEShadowOutcomeError, "GRADE_HORIZON"):
                    project_shadow_outcome(
                        enrollment=valid_row(), grade_rows=[source_grade], horizon=10,
                        grade_row_ref=ref,
                    )

    def test_oversized_numeric_grade_has_typed_refusal(self):
        source_grade = grade(excess_spy=10 ** 1000)
        with self.assertRaisesRegex(PTSEShadowOutcomeError, "GRADE_EXCESS_INVALID"):
            project_shadow_outcome(
                enrollment=valid_row(), grade_rows=[source_grade], horizon=10,
                grade_row_ref=grade_ref(source_grade),
            )

    def test_absent_context_can_still_have_a_genuine_shared_outcome(self):
        source_grade = grade(excess_spy=0.0)
        result = project_shadow_outcome(
            enrollment=valid_row(present=False), grade_rows=[source_grade], horizon=10,
            grade_row_ref=grade_ref(source_grade),
        )
        self.assertEqual(result.status, "MATURED")
        self.assertEqual(result.excess_spy, 0.0)


if __name__ == "__main__":
    unittest.main()
