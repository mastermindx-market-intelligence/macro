"""Pure W7 shadow-enrollment tests; no persistence or grader effects."""
from __future__ import annotations

from dataclasses import dataclass
import unittest

from research.options_estate.ptse_shadow_enrollment import (
    AUTHORITY,
    PTSEShadowEnrollmentError,
    build_shadow_enrollment,
    validate_shadow_enrollment,
)
from tests.test_ptse_prospective_readiness import prospective_new_entry
from tests.test_ptse_action_context import new_entry_inputs
from research.options_estate.ptse_new_entry_context import build_new_entry_context


@dataclass(frozen=True)
class Generation:
    episodes: tuple


@dataclass(frozen=True)
class Snapshot:
    generation_id: str
    generation: Generation


def candidate(**changes):
    row = {
        "stamp_date": "2026-09-18",
        "ticker": "AAPL",
        "board_definition": "us_prophet_v3",
        "score_rank": 7,
        "prophet_score": 62.5,
    }
    row.update(changes)
    return row


def snapshot(*, episode_id=None, generation_id=None, source_ids=None, **changes):
    art = prospective_new_entry()
    a = art.to_dict()["assessment"]
    episode_id = episode_id or a["episode_id"]
    generation_id = generation_id or a["candidate_generation_id"]
    source_ids = source_ids or ["candidate:2026-09-18:AAPL:us_prophet_v3"]
    row = {
        "episode_id": episode_id,
        "security_id": a["security_id"],
        "company_id": a["company_id"],
        "identity_epoch": a["identity_epoch"],
        "source_event_ids": list(source_ids),
    }
    row.update(changes)
    return Snapshot(generation_id, Generation((row,)))


class PTSEShadowEnrollmentTest(unittest.TestCase):
    def test_prospective_new_entry_enrolls_with_exact_b1_identity(self):
        art = prospective_new_entry()
        row = build_shadow_enrollment(
            candidate_row=candidate(), b1_snapshot=snapshot(), context=art
        )
        validate_shadow_enrollment(row)
        a = art.to_dict()["assessment"]
        self.assertEqual(row["context_status"], "AVAILABLE")
        self.assertEqual(row["context_sha256"], art.sha256)
        self.assertEqual(row["episode_id"], a["episode_id"])
        self.assertEqual(row["candidate_generation_id"], a["candidate_generation_id"])
        self.assertEqual(row["authority"], AUTHORITY)
        self.assertTrue(row["enrollment_id"].startswith("ptse-shadow:"))

    def test_missing_optional_context_preserves_candidate_population(self):
        row = build_shadow_enrollment(
            candidate_row=candidate(), b1_snapshot=snapshot(), context=None
        )
        validate_shadow_enrollment(row)
        self.assertEqual(row["context_status"], "UNAVAILABLE")
        self.assertEqual(row["context_reason"], "CONTEXT_MISSING")
        self.assertIsNone(row["context_sha256"])
        self.assertIsNone(row["observation_id"])
        self.assertIsNone(row["assessment_id"])
        self.assertEqual(row["authority"], AUTHORITY)

    def test_rank_and_score_changes_do_not_change_relation_but_do_change_no_identity_field(self):
        art = prospective_new_entry()
        a = build_shadow_enrollment(candidate_row=candidate(), b1_snapshot=snapshot(), context=art)
        b = build_shadow_enrollment(
            candidate_row=candidate(score_rank=99, prophet_score=1.0),
            b1_snapshot=snapshot(),
            context=art,
        )
        self.assertEqual(a, b)

    def test_no_ticker_fallback(self):
        with self.assertRaisesRegex(
            Exception, "CANDIDATE_B1_RELATION_UNAVAILABLE"
        ):
            build_shadow_enrollment(
                candidate_row=candidate(stamp_date="2026-09-19"),
                b1_snapshot=snapshot(),
                context=prospective_new_entry(),
            )

    def test_ptse_episode_must_match_b1_relation(self):
        art = prospective_new_entry()
        with self.assertRaisesRegex(
            Exception, "CANDIDATE_PTSE_EPISODE_MISMATCH"
        ):
            build_shadow_enrollment(
                candidate_row=candidate(),
                b1_snapshot=snapshot(
                    episode_id="pe:SEC:US-XNAS-AAPL:epoch_0:sa:" + "f" * 24 + ":2"
                ),
                context=art,
            )

    def test_generation_must_match_context(self):
        with self.assertRaisesRegex(
            PTSEShadowEnrollmentError, "SHADOW_B1_IDENTITY_MISMATCH"
        ):
            build_shadow_enrollment(
                candidate_row=candidate(),
                b1_snapshot=snapshot(generation_id="peg:" + "f" * 64),
                context=prospective_new_entry(),
            )

    def test_nonprospective_context_is_not_admitted(self):
        inputs = new_entry_inputs()
        synthetic = build_new_entry_context(**inputs)
        with self.assertRaisesRegex(
            PTSEShadowEnrollmentError, "SHADOW_SOURCE_GRADE_NOT_ADMITTED"
        ):
            build_shadow_enrollment(
                candidate_row=candidate(), b1_snapshot=snapshot(), context=synthetic
            )

    def test_non_new_entry_action_is_not_admitted(self):
        art = prospective_new_entry()
        payload = art.to_dict()
        payload["assessment"]["action"] = "PULLBACK_BUY"
        # Re-sealing would need the corresponding geometry owner. The enrollment
        # validator must not accept an unvalidated caller-edited wrapper either.
        from research.options_estate.ptse_contract import ContextArtifact, canonical_json
        forged = ContextArtifact(canonical_json(payload))
        with self.assertRaises(Exception):
            build_shadow_enrollment(
                candidate_row=candidate(), b1_snapshot=snapshot(), context=forged
            )

    def test_enrollment_identity_detects_mutation(self):
        row = build_shadow_enrollment(
            candidate_row=candidate(), b1_snapshot=snapshot(), context=prospective_new_entry()
        )
        row["context_reason"] = "tampered"
        with self.assertRaisesRegex(
            PTSEShadowEnrollmentError, "SHADOW_IDENTITY_MISMATCH"
        ):
            validate_shadow_enrollment(row)

    def test_unavailable_row_cannot_claim_grade(self):
        row = build_shadow_enrollment(
            candidate_row=candidate(), b1_snapshot=snapshot(), context=None
        )
        row["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        with self.assertRaisesRegex(
            PTSEShadowEnrollmentError, "SHADOW_GRADE_WITHOUT_CONTEXT"
        ):
            validate_shadow_enrollment(row)


if __name__ == "__main__":
    unittest.main()
