"""PTSE Prophet plan -> canonical B1 relation tests."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unittest

from research.options_estate.ptse_plan_relation import (
    PTSEPlanRelationError,
    resolve_plan_episode_relation,
)

SOURCE = "candidate:2026-10-02:DOV:us_prophet_v3"
EPISODE = "pe:SEC:US-XNYS-DOV:epoch_0:sa:" + "a" * 24 + ":1"
GEN = "peg:" + "b" * 64
PLAN = "DOV-BULL-20260930"


@dataclass(frozen=True)
class Generation:
    episodes: tuple


@dataclass(frozen=True)
class Snapshot:
    generation_id: str
    generation: Generation


def snapshot(source_ids=(SOURCE,), **changes):
    row = {
        "episode_id": EPISODE,
        "security_id": "SEC:US-XNYS-DOV",
        "company_id": "ISS:US-XNYS-DOV",
        "identity_epoch": "epoch_0",
        "source_event_ids": list(source_ids),
    }
    row.update(changes)
    return Snapshot(GEN, Generation((row,)))


def board_row(**changes):
    row = {
        "ticker": "DOV",
        "prophet": {
            "version": "us_prophet_v3",
            "fusion": {"definition": "us_prophet_v3"},
            "score": 45.2,
        },
        "entry_signal": {"status": "bounce_wait"},
        "hold": {"anchor": "2026-09-30"},
    }
    row.update(changes)
    return row


def canonical_row_sha(row):
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def receipt(*, row=None, source_board_asof="2026-10-02", plan_id=PLAN, asset="DOV",
            source_sha="1" * 64, row_sha=None, plan_sha="2" * 64,
            origins=None, originated_ids=None):
    row = board_row() if row is None else row
    origin = {
        "plan_id": plan_id,
        "asset": asset,
        "formation_date": "2026-09-30",
        "plan_path": f"site/prophet/plans/{plan_id}.json",
        "plan_sha256": plan_sha,
        "admission_rank": 41,
        "board_row_sha256": row_sha or canonical_row_sha(row),
        "board_row": row,
    }
    doc = {
        "schema": "prophet.origination_receipt/v1",
        "receipt_id": "fixture-run-1-1111111111111111",
        "recorded_utc": "2026-10-04T08:15:00Z",
        "run": {"id": "fixture"},
        "source": {
            "path": "site/factordata/us_standouts.json",
            "sha256": source_sha,
            "board_asof": source_board_asof,
        },
        "selection": {
            "rule": "engine.prophet_bridge.select_candidates(n=None)",
            "admitted_count": 55,
            "originated_count": 1,
        },
        "originated_plan_ids": originated_ids if originated_ids is not None else [plan_id],
        "originations": origins if origins is not None else [origin],
    }
    return (json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


class PTSEPlanRelationTest(unittest.TestCase):
    def test_resolves_plan_through_frozen_board_row_to_b1(self):
        raw = receipt()
        out = resolve_plan_episode_relation(
            plan_id=PLAN,
            origination_receipt=raw,
            b1_snapshot=snapshot(),
            expected_episode_id=EPISODE,
        )
        self.assertEqual(out.plan_id, PLAN)
        self.assertEqual(out.plan_asset, "DOV")
        self.assertEqual(out.plan_sha256, "2" * 64)
        self.assertEqual(out.origination_receipt_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(out.candidate_source_event_id, SOURCE)
        self.assertEqual(out.candidate_generation_id, GEN)
        self.assertEqual(out.episode_id, EPISODE)
        self.assertEqual(out.security_id, "SEC:US-XNYS-DOV")
        self.assertTrue(out.relation_id.startswith("ptse-plan-rel:"))

    def test_board_row_digest_is_rechecked(self):
        raw = receipt(row_sha="f" * 64)
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "ORIGINATION_BOARD_ROW_DIGEST_MISMATCH"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_no_ticker_fallback_when_source_session_has_no_b1_relation(self):
        raw = receipt(source_board_asof="2026-10-03")
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "CANDIDATE_B1_RELATION_UNAVAILABLE"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_asset_must_match_frozen_board_ticker(self):
        raw = receipt(asset="CAT")
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "ORIGINATION_ASSET_TICKER_MISMATCH"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_board_definition_conflict_fails_closed(self):
        row = board_row()
        row["prophet"]["fusion"]["definition"] = "us_prophet_v2"
        raw = receipt(row=row)
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "ORIGINATION_BOARD_DEFINITION_CONFLICT"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_plan_must_be_named_by_receipt(self):
        raw = receipt(originated_ids=["OTHER-BULL-20261002"])
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "PLAN_ORIGINATION_RECEIPT_UNAVAILABLE"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_duplicate_plan_origin_is_ambiguous(self):
        base = json.loads(receipt())
        first = base["originations"][0]
        raw = receipt(origins=[first, dict(first)])
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "PLAN_ORIGINATION_RELATION_AMBIGUOUS"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_source_digest_must_be_real_sha256(self):
        raw = receipt(source_sha="not-a-digest")
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "ORIGINATION_SOURCE_DIGEST_INVALID"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
            )

    def test_expected_ptse_episode_must_match_b1(self):
        with self.assertRaisesRegex(
            PTSEPlanRelationError, "CANDIDATE_PTSE_EPISODE_MISMATCH"
        ):
            resolve_plan_episode_relation(
                plan_id=PLAN,
                origination_receipt=receipt(),
                b1_snapshot=snapshot(),
                expected_episode_id=EPISODE + "-other",
            )

    def test_exact_receipt_bytes_participate_in_relation_identity(self):
        raw = receipt()
        compact = json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":")).encode()
        a = resolve_plan_episode_relation(
            plan_id=PLAN, origination_receipt=raw, b1_snapshot=snapshot()
        )
        b = resolve_plan_episode_relation(
            plan_id=PLAN, origination_receipt=compact, b1_snapshot=snapshot()
        )
        self.assertNotEqual(a.origination_receipt_sha256, b.origination_receipt_sha256)
        self.assertNotEqual(a.relation_id, b.relation_id)
        self.assertEqual(a.candidate_source_event_id, b.candidate_source_event_id)

    def test_relation_mints_no_position_or_geometry_authority(self):
        out = resolve_plan_episode_relation(
            plan_id=PLAN, origination_receipt=receipt(), b1_snapshot=snapshot()
        )
        self.assertFalse(hasattr(out, "position_ref"))
        self.assertFalse(hasattr(out, "geometry_ref"))
        self.assertFalse(hasattr(out, "risk_budget_ref"))


if __name__ == "__main__":
    unittest.main()
