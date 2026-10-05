"""PTSE shadow outcome projection tests; shared grader only."""
from __future__ import annotations

import unittest

from research.options_estate.ptse_shadow_outcome import (
    AUTHORITY,
    PTSEShadowOutcomeError,
    project_shadow_outcome,
)
from research.options_estate.ptse_shadow_enrollment import build_shadow_enrollment
from tests.test_ptse_shadow_enrollment import candidate, snapshot
from tests.test_ptse_prospective_readiness import prospective_new_entry


def enrollment():
    return build_shadow_enrollment(
        candidate_row=candidate(),
        b1_snapshot=snapshot(),
        context=prospective_new_entry(),
    )


def grade(**changes):
    row={
        "stamp_date":"2026-09-18",
        "ticker":"AAPL",
        "board_definition":"us_prophet_v3",
        "horizon":10,
        "excess_spy":0.035,
        "fill_date":"2026-09-21",
        "mark_date":"2026-10-05",
        "graded_asof":"2026-10-05",
        "bench":"SPY",
        "schema":"us.prophet_grades/v1",
    }
    row.update(changes)
    return row


class PTSEShadowOutcomeTest(unittest.TestCase):
    def test_missing_grade_is_pending_not_zero(self):
        out=project_shadow_outcome(enrollment=enrollment(),grade_rows=[],horizon=10)
        self.assertEqual(out.status,"PENDING")
        self.assertIsNone(out.excess_spy)
        self.assertIsNone(out.fill_date)
        self.assertEqual(out.authority,AUTHORITY)
        self.assertFalse(out.authority["research_pass"])

    def test_matured_grade_is_copied_from_shared_grader(self):
        out=project_shadow_outcome(enrollment=enrollment(),grade_rows=[grade()],horizon=10)
        self.assertEqual(out.status,"MATURED")
        self.assertEqual(out.excess_spy,0.035)
        self.assertEqual(out.fill_date,"2026-09-21")
        self.assertEqual(out.mark_date,"2026-10-05")
        self.assertEqual(out.grade_schema,"us.prophet_grades/v1")
        self.assertFalse(any(out.authority.values()))

    def test_unrelated_grade_does_not_backfill(self):
        out=project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[grade(ticker="MSFT")],
            horizon=10,
        )
        self.assertEqual(out.status,"PENDING")

    def test_duplicate_exact_grade_key_fails_closed(self):
        with self.assertRaisesRegex(PTSEShadowOutcomeError,"GRADE_KEY_AMBIGUOUS"):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(),grade(excess_spy=0.04)],
                horizon=10,
            )

    def test_wrong_grader_schema_or_benchmark_refused(self):
        with self.assertRaisesRegex(PTSEShadowOutcomeError,"GRADE_SCHEMA_INVALID"):
            project_shadow_outcome(
                enrollment=enrollment(),grade_rows=[grade(schema="other/v1")],horizon=10
            )
        with self.assertRaisesRegex(PTSEShadowOutcomeError,"GRADE_BENCH_INVALID"):
            project_shadow_outcome(
                enrollment=enrollment(),grade_rows=[grade(bench="QQQ")],horizon=10
            )

    def test_nonfinite_or_boolean_outcome_refused(self):
        for value in (True,float("nan"),float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(PTSEShadowOutcomeError,"GRADE_EXCESS_INVALID"):
                    project_shadow_outcome(
                        enrollment=enrollment(),grade_rows=[grade(excess_spy=value)],horizon=10
                    )

    def test_grade_clock_order_is_bound(self):
        with self.assertRaisesRegex(PTSEShadowOutcomeError,"GRADE_CLOCK_ORDER_INVALID"):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(fill_date="2026-09-18")],
                horizon=10,
            )

    def test_horizon_is_exact_key_not_nearest_match(self):
        out=project_shadow_outcome(enrollment=enrollment(),grade_rows=[grade(horizon=21)],horizon=10)
        self.assertEqual(out.status,"PENDING")

    def test_projection_identity_changes_on_maturation(self):
        pending=project_shadow_outcome(enrollment=enrollment(),grade_rows=[],horizon=10)
        matured=project_shadow_outcome(enrollment=enrollment(),grade_rows=[grade()],horizon=10)
        self.assertNotEqual(pending.projection_id,matured.projection_id)

    def test_no_comparative_statistic_or_promotion_field(self):
        out=project_shadow_outcome(enrollment=enrollment(),grade_rows=[grade()],horizon=10)
        self.assertFalse(hasattr(out,"p_value"))
        self.assertFalse(hasattr(out,"ic"))
        self.assertFalse(hasattr(out,"winner"))
        self.assertFalse(hasattr(out,"promote"))


if __name__=="__main__":
    unittest.main()