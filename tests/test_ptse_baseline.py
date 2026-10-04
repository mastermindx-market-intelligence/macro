from __future__ import annotations

from dataclasses import replace
import math
import unittest

from research.options_estate.ptse_baseline import (
    B0ContractError,
    B0Protocol,
    B0Row,
    FEATURE_NAMES,
    FoldSpec,
    TARGET_VERSION,
    _fit_predict_ridge,
    run_b0,
    validate_protocol,
)


def digest(label: str) -> str:
    import hashlib
    return hashlib.sha256(label.encode()).hexdigest()


def cohort_digest(origin_ids: tuple[str, ...]) -> str:
    import hashlib
    import json
    raw = json.dumps(list(origin_ids), separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def protocol(mode="SYNTHETIC"):
    return B0Protocol(
        experiment_id="PTSE-B0-H5-v1",
        target_version=TARGET_VERSION,
        feature_names=FEATURE_NAMES,
        transform="TRAIN_ZSCORE",
        ridge_alpha=1.0,
        min_train_rows=4,
        mode=mode,
        market="US",
        cadence="DAILY",
        session_scope="REGULAR",
        instrument_id="fixture:SEC:US-ARCX-SPY",
        forecast_horizon_sessions=5,
        owner_ratification_ref="fixture:owner-ratification:ptse-b0-h5-v1",
        source_manifest_sha256=digest("fixture-source-manifest"),
        outcome_manifest_sha256=digest("fixture-outcome-manifest"),
        calendar_sha256=digest("fixture-calendar"),
        feature_version="fixture:ptse-b0-features-v1",
        evaluation_partition_ref="fixture:development-partition-v1",
        prior_history_exposure_ref="fixture:prior-history-exposure-v1",
        trial_family_ref="fixture:trial-family-b0-v1",
        embargo_policy_ref="fixture:embargo-policy-v1",
    )


def row(
    day,
    end_day,
    mature,
    y,
    *,
    grade="SYNTHETIC",
    shift=0.0,
):
    return B0Row(
        origin_id=f"fixture:{day}",
        market_session=day,
        decision_at=f"{day}T20:00:00Z",
        source_available_at=f"{day}T19:59:59Z",
        label_end_session=end_day,
        label_matured_at=mature,
        source_grade=grade,
        source_artifact_sha256=digest("source:" + day),
        outcome_artifact_sha256=digest("outcome:" + day),
        log_v20=0.1 + shift,
        trend63=0.2 + shift,
        momentum5=-0.1 + shift,
        positive_trend_negative_momentum=(
            1.0 if -0.1 + shift < 0 and 0.2 + shift > 0 else 0.0
        ),
        y5=y,
    )


ROWS = [
    row("2026-01-02", "2026-01-09", "2026-01-09T21:00:00Z", 2.0, shift=-0.3),
    row("2026-01-05", "2026-01-12", "2026-01-12T21:00:00Z", 1.6, shift=-0.2),
    row("2026-01-06", "2026-01-13", "2026-01-13T21:00:00Z", 1.2, shift=-0.1),
    row("2026-01-07", "2026-01-14", "2026-01-14T21:00:00Z", 0.8, shift=0.0),
    row("2026-01-08", "2026-01-15", "2026-01-15T21:00:00Z", 0.5, shift=0.1),
    row("2026-01-09", "2026-01-16", "2026-01-16T21:00:00Z", 0.4, shift=0.2),
    row("2026-01-20", "2026-01-27", "2026-01-27T21:00:00Z", 0.2, shift=0.3),
    row("2026-01-21", "2026-01-28", "2026-01-28T21:00:00Z", 0.1, shift=0.4),
]


FOLD_ORIGINS = ("fixture:2026-01-20", "fixture:2026-01-21")
FOLD = FoldSpec(
    fold_id="fixture-fold-1",
    fit_cutoff_session="2026-01-15",
    fit_cutoff_at="2026-01-15T23:00:00Z",
    embargo_end_session="2026-01-16",
    test_start_session="2026-01-20",
    test_end_session="2026-01-21",
    evaluation_at="2026-01-29T23:00:00Z",
    cohort_sha256=cohort_digest(FOLD_ORIGINS),
    expected_test_rows=2,
    expected_test_origin_ids=FOLD_ORIGINS,
)


class PTSEB0Test(unittest.TestCase):
    def test_protocol_has_no_defaults_and_requires_owner_ratification(self):
        p = protocol()
        self.assertEqual(len(validate_protocol(p)), 64)
        with self.assertRaisesRegex(B0ContractError, "REFERENCE_REQUIRED"):
            validate_protocol(replace(p, owner_ratification_ref=""))
        with self.assertRaisesRegex(B0ContractError, "RIDGE_ALPHA_REQUIRED"):
            validate_protocol(replace(p, ridge_alpha=0.0))
        with self.assertRaisesRegex(B0ContractError, "DIGEST_REQUIRED"):
            validate_protocol(replace(p, source_manifest_sha256="unknown"))

    def test_feature_and_target_identity_are_frozen(self):
        p = protocol()
        with self.assertRaisesRegex(B0ContractError, "FEATURE_IDENTITY_MISMATCH"):
            validate_protocol(
                replace(p, feature_names=tuple(reversed(FEATURE_NAMES)))
            )
        with self.assertRaisesRegex(B0ContractError, "TARGET_VERSION_MISMATCH"):
            validate_protocol(replace(p, target_version="return.v1"))

    def test_scope_and_outcome_manifest_are_explicit(self):
        p = protocol()
        for field, value in (
            ("market", "OTHER"),
            ("cadence", "INTRADAY"),
            ("session_scope", "EXTENDED"),
            ("forecast_horizon_sessions", 21),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(B0ContractError, "SCOPE_NOT_REGISTERED"):
                    validate_protocol(replace(p, **{field: value}))
        with self.assertRaisesRegex(B0ContractError, "DIGEST_REQUIRED"):
            validate_protocol(replace(p, outcome_manifest_sha256="unknown"))

    def test_event_data_is_not_a_dependency(self):
        result = run_b0(protocol(), [FOLD], ROWS)
        self.assertEqual(
            result.attempted_arms,
            ("mean_reference", "p_vector_ridge"),
        )
        self.assertEqual(result.fold_results[0].train_rows, 5)
        self.assertEqual(
            result.fold_results[0].purged_unmatured_or_overlapping_train_rows,
            1,
        )
        self.assertEqual(result.fold_results[0].test_rows, 2)

    def test_train_only_transform_does_not_refit_on_test_batch(self):
        train = ROWS[:5]
        first = ROWS[-2]
        second = ROWS[-1]
        solo = _fit_predict_ridge(train, [first], 1.0)[0]
        batched = _fit_predict_ridge(train, [first, second], 1.0)[0]
        self.assertAlmostEqual(float(solo), float(batched), places=12)

    def test_injected_relationship_discriminates_from_mean_reference(self):
        result = run_b0(protocol(), [FOLD], ROWS)
        fold = result.fold_results[0]
        self.assertLess(fold.p_vector_mse, fold.mean_reference_mse)
        self.assertLess(fold.p_vector_mae, fold.mean_reference_mae)

    def test_confirmatory_rejects_pit_unproven_history(self):
        realish = [
            replace(r, source_grade="RETROSPECTIVE_PIT_UNPROVEN")
            for r in ROWS
        ]
        with self.assertRaisesRegex(B0ContractError, "SOURCE_GRADE_NOT_ADMITTED"):
            run_b0(protocol("CONFIRMATORY"), [FOLD], realish)

    def test_exploratory_allows_pit_unproven_but_grants_no_authority(self):
        realish = [
            replace(r, source_grade="RETROSPECTIVE_PIT_UNPROVEN")
            for r in ROWS
        ]
        result = run_b0(protocol("EXPLORATORY"), [FOLD], realish)
        self.assertEqual(
            result.source_grades,
            ("RETROSPECTIVE_PIT_UNPROVEN",),
        )
        self.assertTrue(
            all(value is False for value in result.authority.values())
        )

    def test_confirmatory_allows_pit_qualified_replay(self):
        qualified = [
            replace(r, source_grade="PIT_QUALIFIED_REPLAY")
            for r in ROWS
        ]
        result = run_b0(protocol("CONFIRMATORY"), [FOLD], qualified)
        self.assertEqual(
            result.source_grades,
            ("PIT_QUALIFIED_REPLAY",),
        )

    def test_source_must_be_available_at_decision(self):
        rows = list(ROWS)
        rows[0] = replace(
            rows[0],
            source_available_at="2026-01-02T20:00:01Z",
        )
        with self.assertRaisesRegex(
            B0ContractError,
            "SOURCE_NOT_AVAILABLE_AT_DECISION",
        ):
            run_b0(protocol(), [FOLD], rows)

    def test_decision_clock_must_match_market_session(self):
        rows = list(ROWS)
        rows[0] = replace(rows[0], decision_at="2026-01-03T20:00:00Z")
        with self.assertRaisesRegex(B0ContractError, "DECISION_SESSION_MISMATCH"):
            run_b0(protocol(), [FOLD], rows)

    def test_label_maturity_cannot_precede_label_end(self):
        rows = list(ROWS)
        rows[0] = replace(
            rows[0],
            label_matured_at="2026-01-08T21:00:00Z",
        )
        with self.assertRaisesRegex(B0ContractError, "LABEL_MATURITY_INVALID"):
            run_b0(protocol(), [FOLD], rows)

    def test_immature_test_label_is_not_zero_filled(self):
        rows = list(ROWS)
        rows[-1] = replace(
            rows[-1],
            label_matured_at="2026-02-01T21:00:00Z",
        )
        result = run_b0(protocol(), [FOLD], rows)
        self.assertEqual(result.fold_results[0].expected_test_rows, 2)
        self.assertEqual(result.fold_results[0].test_rows, 1)
        self.assertEqual(result.fold_results[0].unevaluable_test_rows, 1)

    def test_missing_or_replaced_test_origin_breaks_frozen_cohort(self):
        with self.assertRaisesRegex(B0ContractError, "COHORT_IDENTITY_MISMATCH"):
            run_b0(protocol(), [FOLD], ROWS[:-1])

        replacement = row(
            "2026-01-22",
            "2026-01-29",
            "2026-01-29T21:00:00Z",
            0.05,
            shift=0.5,
        )
        widened = replace(
            FOLD,
            test_end_session="2026-01-22",
        )
        with self.assertRaisesRegex(B0ContractError, "COHORT_IDENTITY_MISMATCH"):
            run_b0(protocol(), [widened], ROWS[:-1] + [replacement])

    def test_cohort_manifest_hash_and_order_are_enforced(self):
        with self.assertRaisesRegex(B0ContractError, "COHORT_DIGEST_MISMATCH"):
            run_b0(protocol(), [replace(FOLD, cohort_sha256=digest("wrong"))], ROWS)
        with self.assertRaisesRegex(B0ContractError, "COHORT_IDENTITY_REQUIRED"):
            run_b0(
                protocol(),
                [
                    replace(
                        FOLD,
                        expected_test_origin_ids=tuple(reversed(FOLD_ORIGINS)),
                    )
                ],
                ROWS,
            )

    def test_explicit_embargo_end_must_precede_test_window(self):
        with self.assertRaisesRegex(B0ContractError, "FOLD_ORDER_INVALID"):
            run_b0(
                protocol(),
                [replace(FOLD, embargo_end_session="2026-01-20")],
                ROWS,
            )

    def test_no_mature_test_rows_is_non_evaluable(self):
        rows = [
            (
                replace(r, label_matured_at="2026-02-01T21:00:00Z")
                if r.market_session >= "2026-01-20"
                else r
            )
            for r in ROWS
        ]
        with self.assertRaisesRegex(
            B0ContractError,
            "TEST_SUPPORT_INSUFFICIENT",
        ):
            run_b0(protocol(), [FOLD], rows)

    def test_duplicate_origins_and_sessions_are_rejected(self):
        with self.assertRaisesRegex(B0ContractError, "DUPLICATE_ORIGIN_ID"):
            run_b0(
                protocol(),
                [FOLD],
                ROWS
                + [
                    replace(
                        ROWS[-1],
                        market_session="2026-01-22",
                        decision_at="2026-01-22T20:00:00Z",
                        source_available_at="2026-01-22T19:59:59Z",
                        label_end_session="2026-01-29",
                        label_matured_at="2026-01-29T21:00:00Z",
                    )
                ],
            )
        duplicate_session = replace(
            ROWS[-1],
            origin_id="fixture:other",
            source_artifact_sha256=digest("other-source"),
            outcome_artifact_sha256=digest("other-outcome"),
        )
        with self.assertRaisesRegex(
            B0ContractError,
            "DUPLICATE_MARKET_SESSION",
        ):
            run_b0(protocol(), [FOLD], ROWS + [duplicate_session])

    def test_bad_indicator_or_negative_target_is_rejected(self):
        bad = list(ROWS)
        bad[0] = replace(
            bad[0],
            positive_trend_negative_momentum=0.5,
        )
        with self.assertRaisesRegex(B0ContractError, "INDICATOR_INVALID"):
            run_b0(protocol(), [FOLD], bad)

        bad = list(ROWS)
        bad[0] = replace(bad[0], y5=-0.1)
        with self.assertRaisesRegex(B0ContractError, "TARGET_NEGATIVE"):
            run_b0(protocol(), [FOLD], bad)

    def test_fold_overlap_and_order_are_fail_closed(self):
        bad_fold = replace(
            FOLD,
            test_start_session="2026-01-15",
        )
        with self.assertRaisesRegex(B0ContractError, "FOLD_ORDER_INVALID"):
            run_b0(protocol(), [bad_fold], ROWS)

        second_origins = ("fixture:2026-01-21",)
        second = replace(
            FOLD,
            fold_id="fixture-fold-2",
            fit_cutoff_session="2026-01-19",
            fit_cutoff_at="2026-01-19T23:00:00Z",
            embargo_end_session="2026-01-20",
            test_start_session="2026-01-21",
            test_end_session="2026-01-21",
            cohort_sha256=cohort_digest(second_origins),
            expected_test_rows=1,
            expected_test_origin_ids=second_origins,
        )
        with self.assertRaisesRegex(B0ContractError, "TEST_FOLD_OVERLAP"):
            run_b0(protocol(), [FOLD, second], ROWS)

    def test_result_is_deterministic_and_does_not_emit_pass_or_probability(self):
        left = run_b0(protocol(), [FOLD], ROWS)
        right = run_b0(protocol(), [FOLD], reversed(ROWS))
        self.assertEqual(left, right)
        self.assertEqual(len(left.result_digest), 64)
        self.assertFalse(hasattr(left, "research_pass"))
        self.assertFalse(hasattr(left, "probability"))
        for value in (
            left.fold_results[0].mean_reference_mse,
            left.fold_results[0].p_vector_mse,
        ):
            self.assertTrue(math.isfinite(value))

    def test_result_digest_binds_outcome_artifact_identity(self):
        left = run_b0(protocol(), [FOLD], ROWS)
        changed = list(ROWS)
        changed[-1] = replace(
            changed[-1],
            outcome_artifact_sha256=digest("different-outcome-artifact"),
        )
        right = run_b0(protocol(), [FOLD], changed)
        self.assertNotEqual(left.result_digest, right.result_digest)

    def test_fold_result_binds_frozen_fold_definition(self):
        result = run_b0(protocol(), [FOLD], ROWS)
        fold = result.fold_results[0]
        self.assertEqual(fold.cohort_sha256, FOLD.cohort_sha256)
        self.assertEqual(len(fold.fold_spec_digest), 64)


if __name__ == "__main__":
    unittest.main()