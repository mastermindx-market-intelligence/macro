"""PTSE shadow outcome projection tests; shared grader only."""
from __future__ import annotations

import hashlib
import json
import unittest

from research.options_estate.ptse_shadow_outcome import (
    AUTHORITY,
    GRADE_BIND_FIELDS,
    OUTCOME_TARGET,
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
    row = {
        "stamp_date": "2026-09-18",
        "ticker": "AAPL",
        "board_definition": "us_prophet_v3",
        "horizon": 10,
        "excess_spy": 0.035,
        "fill_date": "2026-09-21",
        "mark_date": "2026-10-05",
        "graded_asof": "2026-10-05",
        "bench": "SPY",
        "schema": "us.prophet_grades/v1",
    }
    row.update(changes)
    return row


def grade_ref(row):
    material = {field: row.get(field) for field in GRADE_BIND_FIELDS}
    wire = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return {
        "owner_ref": "engine.us_prophet_grades",
        "artifact_id": (
            f"grade:{row.get('stamp_date')}:{row.get('ticker')}:"
            f"{row.get('board_definition')}:{row.get('horizon')}"
        ),
        "sha256": hashlib.sha256(wire).hexdigest(),
    }


class PTSEShadowOutcomeTest(unittest.TestCase):
    def test_missing_grade_is_pending_not_zero(self):
        out = project_shadow_outcome(
            enrollment=enrollment(), grade_rows=[], horizon=10
        )
        self.assertEqual(out.status, "PENDING")
        self.assertIsNone(out.excess_spy)
        self.assertIsNone(out.fill_date)
        self.assertIsNone(out.grade_row_ref)
        self.assertEqual(out.outcome_target, OUTCOME_TARGET)
        self.assertEqual(out.authority, AUTHORITY)
        self.assertFalse(out.authority["research_pass"])

    def test_matured_grade_is_copied_from_shared_grader_with_owner_ref(self):
        row = grade()
        ref = grade_ref(row)
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[row],
            horizon=10,
            grade_row_ref=ref,
        )
        self.assertEqual(out.status, "MATURED")
        self.assertEqual(out.excess_spy, 0.035)
        self.assertEqual(out.fill_date, "2026-09-21")
        self.assertEqual(out.mark_date, "2026-10-05")
        self.assertEqual(out.grade_schema, "us.prophet_grades/v1")
        self.assertEqual(out.grade_row_ref, ref)
        self.assertEqual(out.outcome_target, OUTCOME_TARGET)
        self.assertFalse(any(out.authority.values()))

    def test_unrelated_grade_does_not_backfill(self):
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[grade(ticker="MSFT")],
            horizon=10,
        )
        self.assertEqual(out.status, "PENDING")

    def test_duplicate_exact_grade_key_fails_closed(self):
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_KEY_AMBIGUOUS"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(), grade(excess_spy=0.04)],
                horizon=10,
            )

    def test_wrong_grader_schema_or_benchmark_refused_before_receipt(self):
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_SCHEMA_INVALID"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(schema="other/v1")],
                horizon=10,
            )
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_BENCH_INVALID"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(bench="QQQ")],
                horizon=10,
            )

    def test_nonfinite_or_boolean_outcome_refused_before_receipt(self):
        for value in (True, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    PTSEShadowOutcomeError, "GRADE_EXCESS_INVALID"
                ):
                    project_shadow_outcome(
                        enrollment=enrollment(),
                        grade_rows=[grade(excess_spy=value)],
                        horizon=10,
                    )

    def test_grade_clock_order_is_bound_before_receipt(self):
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_CLOCK_ORDER_INVALID"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[grade(fill_date="2026-09-18")],
                horizon=10,
            )

    def test_horizon_is_exact_key_not_nearest_match(self):
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[grade(horizon=21)],
            horizon=10,
        )
        self.assertEqual(out.status, "PENDING")

    def test_projection_identity_changes_on_maturation(self):
        row = grade()
        pending = project_shadow_outcome(
            enrollment=enrollment(), grade_rows=[], horizon=10
        )
        matured = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[row],
            horizon=10,
            grade_row_ref=grade_ref(row),
        )
        self.assertNotEqual(pending.projection_id, matured.projection_id)

    def test_no_comparative_statistic_or_promotion_field(self):
        row = grade()
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[row],
            horizon=10,
            grade_row_ref=grade_ref(row),
        )
        self.assertFalse(hasattr(out, "p_value"))
        self.assertFalse(hasattr(out, "ic"))
        self.assertFalse(hasattr(out, "winner"))
        self.assertFalse(hasattr(out, "promote"))

    def test_caller_synthesized_grade_without_owner_ref_is_refused(self):
        fake = grade(excess_spy=0.99)
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_ROW_REF_REQUIRED"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[fake],
                horizon=10,
            )

    def test_grade_mutation_under_old_receipt_is_refused(self):
        original = grade()
        ref = grade_ref(original)
        changed = grade(excess_spy=0.99)
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_ROW_REF_MISMATCH"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[changed],
                horizon=10,
                grade_row_ref=ref,
            )

    def test_grade_ref_is_key_order_stable(self):
        row = grade()
        reordered = dict(reversed(list(row.items())))
        ref = grade_ref(row)
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[reordered],
            horizon=10,
            grade_row_ref=ref,
        )
        self.assertEqual(out.grade_row_ref, ref)

    def test_pending_projection_cannot_claim_a_grade_ref(self):
        with self.assertRaisesRegex(
            PTSEShadowOutcomeError, "GRADE_REF_WITHOUT_ROW"
        ):
            project_shadow_outcome(
                enrollment=enrollment(),
                grade_rows=[],
                horizon=10,
                grade_row_ref=grade_ref(grade()),
            )

    def test_shared_return_target_is_explicitly_not_ptse_b0_or_options_vol(self):
        row = grade()
        out = project_shadow_outcome(
            enrollment=enrollment(),
            grade_rows=[row],
            horizon=10,
            grade_row_ref=grade_ref(row),
        )
        self.assertEqual(
            out.outcome_target,
            "prophet.shared_excess_spy_return/v1",
        )
        self.assertNotIn("normalized_h5", out.outcome_target)
        self.assertNotIn("volatility", out.outcome_target)


if __name__ == "__main__":
    unittest.main()
