"""Synthetic tests for the PTSE current-tip breadth adapter."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest

from research.options_estate.ptse_breadth_observation import (
    BreadthSnapshotBinding,
    PTSEBreadthAdapterError,
    adapt_breadth_snapshot,
)
from research.options_estate.ptse_contract import build_context
from research.options_estate.ptse_prospective_readiness import (
    qualify_prospective_observation,
)
from tests.test_ptse_contract import inputs


DECISION = "2026-10-02T20:00:00Z"
OWNER = "market-memory-breadth-owner"
MM_SPY = "mmsecurity_" + "6" * 64
UNIVERSE = "mmuniverse_" + "5" * 64


def canonical_sha(payload: dict) -> str:
    wire = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode()
    return hashlib.sha256(wire).hexdigest()


def ref(name: str, owner: str = OWNER, *, artifact_id=None, sha=None) -> dict:
    return {
        "owner_ref": owner,
        "artifact_id": artifact_id or "fixture:" + name,
        "sha256": sha or hashlib.sha256(name.encode()).hexdigest(),
    }


def snapshot(*, members=502, count=503) -> dict:
    payload = {
        "schema": "market_memory.breadth_factors_snapshot.v1",
        "snapshot_id": "mmsnap_" + "1" * 64,
        "source_observation_id": "mmbreadthsrc_" + "2" * 64,
        "session": "2026-10-02",
        "transform_version": "market_memory.breadth_factors_transform.v1",
        "subject": {
            "symbol": "SPY",
            "subject_id": "mmsecurity_" + "3" * 64,
            "instrument_id": MM_SPY,
            "identity_version": "mmidentityv_" + "4" * 64,
            "mic": "ARCX",
            "currency": "USD",
            "universe_id": UNIVERSE,
            "calendar_id": "mmcalendar_" + "7" * 64,
            "market_session": "XNYS_REGULAR",
        },
        "state": {
            "n_members": members,
            "constituent_count": count,
            "priced_member_coverage": members / count,
            "pct_above_50": 24.25,
            "pct_above_200": 43.38,
            "new_highs": 9,
            "new_lows": 21,
            "advancers": 296 if members >= 499 else max(0, members - 3),
            "decliners": 203 if members >= 499 else 3,
        },
        "quality": {
            "status": "degraded",
            "flags": ["partial_coverage"],
            "actual_output_source": True,
            "current_tip_only": True,
            "imputed": False,
            "training_eligible": False,
            "promotion_eligible": False,
        },
        "limitations": {
            "current_membership_only": True,
            "current_membership_survivor_bias": True,
            "historical_constituent_point_in_time": False,
            "calendar_coverage": "full_day_closures_only",
            "calendar_partial_coverage": True,
            "ad_line_excluded": True,
        },
        "authority": {
            "tier": "display",
            "horizon_role": "context",
            "context_only": True,
            "proposal_weight": 0,
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_escalate": False,
            "may_trade": False,
            "may_originate": False,
            "may_select_options_candidate": False,
            "may_execute": False,
            "may_write_options_episode": False,
            "may_append_outcome": False,
            "may_train_prophet": False,
        },
    }
    return payload


def binding(payload: dict, *, grade="SYNTHETIC",
            latest="2026-10-02T19:58:00Z") -> BreadthSnapshotBinding:
    return BreadthSnapshotBinding(
        owner_ref=OWNER,
        artifact_ref=ref(
            "snapshot", artifact_id=payload["snapshot_id"],
            sha=canonical_sha(payload),
        ),
        known_at_earliest=latest,
        known_at_latest=latest,
        known_at_precision="EXACT",
        known_at_evidence_ref=ref("first-durable-write"),
        economic_time="2026-10-02T19:57:00Z",
        valid_until="2026-10-03T00:00:00Z",
        evidence_grade=grade,
        population_ref=ref(
            "universe", artifact_id=UNIVERSE,
        ),
        calculation_version="ptse-breadth-adapter-v1",
        limitations=("Synthetic fixture; not source qualification.",),
    )


def by_id(facts):
    return {fact["feature_id"]: fact for fact in facts}


class PTSEBreadthObservationTest(unittest.TestCase):
    def test_partial_coverage_is_explicit_on_every_breadth_fact(self):
        p = snapshot()
        facts = adapt_breadth_snapshot(
            p, binding(p), market_session="2026-10-02", decision_at=DECISION
        )
        self.assertEqual(len(facts), 9)
        self.assertTrue(all(f["status"] == "PARTIAL" for f in facts))
        self.assertTrue(all(f["coverage"]["numerator"] == 502 for f in facts))
        self.assertTrue(all(f["coverage"]["denominator"] == 503 for f in facts))
        self.assertTrue(all(f["coverage"]["missing_count"] == 1 for f in facts))
        self.assertEqual(
            by_id(facts)["breadth.priced_member_coverage"]["unit"], "FRACTION"
        )

    def test_full_priced_population_becomes_observed(self):
        p = snapshot(members=503, count=503)
        p["state"]["advancers"] = 300
        p["state"]["decliners"] = 203
        facts = adapt_breadth_snapshot(
            p, binding(p), market_session="2026-10-02", decision_at=DECISION
        )
        self.assertTrue(all(f["status"] == "OBSERVED" for f in facts))
        self.assertTrue(all(f["coverage"]["missing_count"] == 0 for f in facts))

    def test_market_memory_identity_is_preserved_not_minted_as_dataos(self):
        p = snapshot()
        facts = adapt_breadth_snapshot(
            p, binding(p), market_session="2026-10-02", decision_at=DECISION
        )
        self.assertTrue(all(
            f["source_scope"]["instrument_id"] == MM_SPY for f in facts
        ))
        self.assertTrue(any(
            "does not mint a Data OS SEC mapping" in text
            for text in facts[0]["limitations"]
        ))

    def test_artifact_digest_mismatch_is_refused(self):
        p = snapshot()
        b = binding(p)
        bad = BreadthSnapshotBinding(
            **{**b.__dict__, "artifact_ref": ref(
                "snapshot", artifact_id=p["snapshot_id"], sha="f" * 64
            )}
        )
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_ARTIFACT_REF_MISMATCH"
        ):
            adapt_breadth_snapshot(
                p, bad, market_session="2026-10-02", decision_at=DECISION
            )

    def test_positive_authority_is_refused(self):
        p = snapshot()
        p["authority"]["may_gate"] = True
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_AUTHORITY_INVALID"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_historical_pit_upgrade_or_quality_upgrade_is_not_silent(self):
        p = snapshot()
        p["limitations"]["historical_constituent_point_in_time"] = True
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_LIMITATIONS_INVALID"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )
        p = snapshot()
        p["quality"]["training_eligible"] = True
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_QUALITY_INVALID"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_population_and_session_identity_are_bound(self):
        p = snapshot()
        b = binding(p)
        bad = BreadthSnapshotBinding(
            **{**b.__dict__, "population_ref": ref(
                "wrong-universe", artifact_id="mmuniverse_" + "9" * 64
            )}
        )
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_POPULATION_REF_MISMATCH"
        ):
            adapt_breadth_snapshot(
                p, bad, market_session="2026-10-02", decision_at=DECISION
            )
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_SESSION_MISMATCH"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-01", decision_at=DECISION
            )

    def test_late_known_snapshot_is_refused(self):
        p = snapshot()
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "NOT_KNOWN_AT_DECISION"
        ):
            adapt_breadth_snapshot(
                p, binding(p, latest="2026-10-02T20:00:01Z"),
                market_session="2026-10-02", decision_at=DECISION,
            )

    def test_owner_state_arithmetic_is_rechecked(self):
        p = snapshot()
        p["state"]["priced_member_coverage"] = 1.0
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_COVERAGE_INVALID"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )
        p = snapshot()
        p["state"]["advancers"] = 400
        p["state"]["decliners"] = 200
        with self.assertRaisesRegex(
            PTSEBreadthAdapterError, "BREADTH_STATE_INVALID"
        ):
            adapt_breadth_snapshot(
                p, binding(p), market_session="2026-10-02", decision_at=DECISION
            )

    def test_facts_validate_and_prospective_readiness_needs_external_clock_binding(self):
        p = snapshot()
        facts = adapt_breadth_snapshot(
            p, binding(p, grade="PROSPECTIVE_FIRST_SEEN"),
            market_session="2026-10-02", decision_at=DECISION,
        )
        observation, assessment = inputs()
        observation["instrument_id"] = MM_SPY
        observation["facts"] = facts
        observation["evidence_grade"] = "PROSPECTIVE_FIRST_SEEN"
        assessment["drivers"] = []
        artifact = build_context(observation, assessment)
        ready = qualify_prospective_observation(artifact)
        self.assertEqual(ready.status, "READY_FOR_EXISTING_PUBLICATION_OWNER")
        self.assertFalse(ready.publication_authority)
        self.assertFalse(ready.decision_authority)


if __name__ == "__main__":
    unittest.main()