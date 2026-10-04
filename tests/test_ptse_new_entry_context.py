"""Synthetic PTSE NEW_ENTRY compiler tests using incumbent B3/B4 contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import copy
import hashlib
import json
import unittest

from engine.prophet_candidate_state import project_candidate_states
from engine.prophet_entry_availability import evaluate_entry_availability
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
)
from research.options_estate.ptse_contract import AUTHORITY_KEYS
from research.options_estate.ptse_new_entry_context import (
    NewEntryContextBinding,
    PTSENewEntryContextError,
    build_new_entry_context,
)
from research.options_estate.ptse_owner_observation import OwnerArtifactBinding


GEN = "peg:" + "a" * 64
SESSION = "2026-09-18"
DECISION = "2026-09-18T19:30:08Z"
EPISODE_ID = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:" + ("31".ljust(24, "0")) + ":1"


@dataclass(frozen=True)
class Generation:
    episodes: tuple


@dataclass(frozen=True)
class Snapshot:
    generation_id: str
    generation: Generation


def ref(name: str, owner: str) -> dict:
    return {
        "owner_ref": owner,
        "artifact_id": "fixture:" + name,
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


def episode(state="ACTIVE", terminal_reason=None) -> dict:
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": EPISODE_ID,
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "episode_state": state,
        "terminal_reason": terminal_reason,
        "superseded_by": None,
        "opened_at": "2026-09-17T20:00:00Z",
        "opened_session": "2026-09-17",
        "correction_state": "current",
    }


def projection(state="ACTIVE", terminal_reason=None) -> dict:
    return project_candidate_states(
        Snapshot(GEN, Generation((episode(state, terminal_reason),))),
        market_session=SESSION,
        generated_at="2026-09-18T19:30:00Z",
    )


def b4_facts(*, price=42.70, freshness="FRESH") -> dict:
    return {
        "decision_at": DECISION,
        "market_session": SESSION,
        "quote": {
            "price": price,
            "asof": "2026-09-18T19:30:00Z",
            "freshness": freshness,
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "1" * 64,
        },
        "geometry": {
            "owner_status": "buy_now",
            "zone_low": 41.80,
            "zone_high": 43.25,
            "chase_above": 43.60,
            "invalidation_price": 40.95,
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "2" * 64,
        },
        "deterministic_gates": {
            "owner_confluence": "PASS",
            "risk_ceiling": "PASS",
            "liquidity_fillability": "PASS",
            "gap_velocity": "PASS",
            "source_health": "PASS",
            "corporate_action_basis": "RESOLVED",
            "session_eligibility": "PASS",
            "event_status": "ACTIVE",
            "structural_invalidation": "CLEAR",
        },
        "metric_inputs": {
            "first_trigger_price": 41.72,
            "anchor_price": 42.10,
            "atr": 1.15,
        },
        "source_receipts": ["b3:source-owner-v1"],
    }


def availability(p=None, facts=None) -> dict:
    return evaluate_entry_availability(
        p or projection(),
        episode_id=EPISODE_ID,
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        facts=facts or b4_facts(),
    )


def owner_binding(owner: str, name: str, *, grade="SYNTHETIC") -> OwnerArtifactBinding:
    return OwnerArtifactBinding(
        owner_ref=owner,
        artifact_ref=ref(name, owner),
        known_at_earliest="2026-09-18T19:29:50Z",
        known_at_latest="2026-09-18T19:29:50Z",
        known_at_precision="EXACT",
        known_at_evidence_ref=ref(name + "-known", owner),
        economic_time="2026-09-18T19:29:45Z",
        valid_until="2026-09-18T20:30:00Z",
        evidence_grade=grade,
        population_ref=ref(name + "-population", owner),
        instrument_id="SEC:US-ARCX-SPY",
        session_scope="REGULAR",
        calculation_version="fixture:" + name + "-v1",
        limitations=("Synthetic fixture; no market or decision authority.",),
    )


def market_state() -> dict:
    return {
        "schema": "market_state.v1",
        "asof": SESSION,
        "market": "us",
        "verdict": "MIXED",
        "raw_score": 57,
        "score": 52,
        "score_source": "blend",
        "capped": False,
        "radar": {"state": "watch"},
        "participation_scope": {
            "state": "selective",
            "participation": "uneven",
        },
        "freshness": {"any_input_stale": False},
        "is_display_only": True,
    }


def regime_vector() -> dict:
    return {
        "schema_version": 1,
        "asof": SESSION,
        "quad_hard_label": "Q2",
        "rate_pressure": "neutral",
        "risk_radar_state": "watch",
        "vol_regime": "normal",
        "liquidity_quality_label": "benign",
        "deescalation_eligible": False,
        "deescalation_trajectory": {
            "phase": "building",
            "intensity": 41.0,
        },
        "dislocation_verdict": "none",
        "dislocation_active": False,
        "breadth_pct_above_50": 55.0,
        "breadth_pct_above_200": 58.0,
        "regime_vector_degraded": False,
        "favor_entries": True,
        "cap_leadership": False,
        "fused_risk_gross": 0.9,
    }


def canonical_ref(payload: dict, artifact_id: str, owner: str) -> dict:
    wire = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return {
        "owner_ref": owner,
        "artifact_id": artifact_id,
        "sha256": hashlib.sha256(wire).hexdigest(),
    }


def binding(p: dict, a: dict, *, reconstructed_at=None) -> NewEntryContextBinding:
    return NewEntryContextBinding(
        market_session=SESSION,
        decision_at=DECISION,
        issued_at="2026-09-18T19:30:10Z",
        valid_until="2026-09-18T20:30:00Z",
        forecast_end_session="2026-09-25",
        calendar_ref=ref("calendar", "calendar-owner"),
        freshness_ref=ref("freshness", "ptse-owner"),
        source_manifest_ref=ref("manifest", "ptse-owner"),
        calculation_receipt_ref=ref("calculation", "ptse-owner"),
        producer_revision="a" * 40,
        feature_version="ptse-owner-context-v1",
        observation_instrument_id="SEC:US-ARCX-SPY",
        cohort_ref=canonical_ref(p, p["projection_id"], "prophet-b3-owner"),
        eligibility_ref=canonical_ref(a, a["availability_id"], "prophet-b4-owner"),
        holding_horizon_ref=ref("independent-holding-horizon", "strategy-owner"),
        target_version="ptse-h5-context-only-v1",
        reconstructed_at=reconstructed_at,
    )


def build(p=None, a=None, b=None, *, ms_grade="SYNTHETIC", rv_grade="SYNTHETIC"):
    p = p or projection()
    a = a or availability(p)
    b = b or binding(p, a)
    return build_new_entry_context(
        candidate_projection=p,
        entry_availability=a,
        binding=b,
        market_state=market_state(),
        market_state_binding=owner_binding(
            "market-state-owner",
            "market-state",
            grade=ms_grade,
        ),
        regime_vector=regime_vector(),
        regime_vector_binding=owner_binding(
            "regime-vector-owner",
            "regime-vector",
            grade=rv_grade,
        ),
    )


def rehash_availability(payload: dict) -> dict:
    changed = copy.deepcopy(payload)
    material = {k: v for k, v in changed.items() if k != "availability_id"}
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    changed["availability_id"] = "pea:" + hashlib.sha256(encoded).hexdigest()
    return changed
class PTSENewEntryContextTest(unittest.TestCase):
    def test_binds_exact_b3_company_and_b4_strategy_without_minting_authority(self):
        artifact = build()
        payload = artifact.to_dict()
        assessment = payload["assessment"]
        self.assertEqual(assessment["episode_id"], EPISODE_ID)
        self.assertEqual(assessment["security_id"], "SEC:US-XNAS-AAPL")
        self.assertEqual(assessment["company_id"], "ISS:US-XNAS-AAPL")
        self.assertEqual(assessment["identity_epoch"], "epoch_0")
        self.assertEqual(assessment["candidate_generation_id"], GEN)
        self.assertEqual(
            assessment["strategy_id"],
            "EARLY_LEADERSHIP_SECTOR_ROTATION",
        )
        self.assertEqual(assessment["action"], "NEW_ENTRY")
        self.assertEqual(
            assessment["authority"],
            {key: False for key in AUTHORITY_KEYS},
        )
        self.assertEqual(assessment["drivers"], [])
        self.assertEqual(assessment["contradictions"], [])

    def test_b4_entry_open_is_reference_only_not_ptse_entry_gate(self):
        p = projection()
        a = availability(p)
        self.assertTrue(a["entry_open"])
        artifact = build(p, a)
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "APPLICABLE")
        self.assertFalse(assessment["authority"]["entry_gating"])
        self.assertEqual(
            assessment["eligibility_ref"]["artifact_id"],
            a["availability_id"],
        )

    def test_b4_tactical_horizon_does_not_replace_h5_or_holding_horizon(self):
        p = projection()
        a = availability(p)
        self.assertEqual(a["horizon"], "2_15_SESSIONS")
        artifact = build(p, a)
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["forecast_horizon_sessions"], 5)
        self.assertEqual(assessment["forecast_end_session"], "2026-09-25")
        self.assertEqual(
            assessment["holding_horizon_ref"]["artifact_id"],
            "fixture:independent-holding-horizon",
        )

    def test_b3_b4_projection_identity_mismatch_is_refused_even_if_b4_rehashes(self):
        p = projection()
        a = availability(p)
        changed = copy.deepcopy(a)
        changed["candidate_state_projection_id"] = "pcs:" + "f" * 64
        changed = rehash_availability(changed)
        b = binding(p, changed)
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "B3_B4_PROJECTION_MISMATCH",
        ):
            build(p, changed, b)

    def test_cohort_receipt_must_bind_exact_b3_projection_bytes(self):
        p = projection()
        a = availability(p)
        b = binding(p, a)
        bad = replace(
            b,
            cohort_ref={
                **b.cohort_ref,
                "sha256": "f" * 64,
            },
        )
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "COHORT_REF_MISMATCH",
        ):
            build(p, a, bad)

    def test_eligibility_receipt_must_bind_exact_b4_bytes(self):
        p = projection()
        a = availability(p)
        b = binding(p, a)
        bad = replace(
            b,
            eligibility_ref={
                **b.eligibility_ref,
                "sha256": "f" * 64,
            },
        )
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "ELIGIBILITY_REF_MISMATCH",
        ):
            build(p, a, bad)

    def test_unavailable_b4_keeps_timing_context_non_authoritative_and_unknown(self):
        p = projection()
        a = availability(p, b4_facts(freshness="STALE"))
        self.assertEqual(a["state"], "UNAVAILABLE_DATA")
        artifact = build(p, a)
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "UNKNOWN")
        self.assertFalse(any(assessment["authority"].values()))

    def test_invalidated_b4_makes_new_entry_not_applicable_without_mutating_owner(self):
        p = projection(state="INVALIDATED", terminal_reason="fixture")
        a = availability(p)
        self.assertEqual(a["state"], "INVALIDATED")
        before = copy.deepcopy(a)
        artifact = build(p, a)
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "NOT_APPLICABLE")
        self.assertEqual(a, before)

    def test_wait_pullback_still_allows_read_only_new_entry_lane_context(self):
        p = projection()
        a = availability(p, b4_facts(price=43.40))
        self.assertEqual(a["state"], "WAIT_PULLBACK")
        assessment = build(p, a).to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "APPLICABLE")
        self.assertFalse(assessment["authority"]["entry_gating"])

    def test_mixed_owner_grades_use_weakest_grade_and_require_reconstruction(self):
        p = projection()
        a = availability(p)
        b = binding(p, a)
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "RECONSTRUCTION_REQUIRED",
        ):
            build(
                p,
                a,
                b,
                ms_grade="PIT_QUALIFIED_REPLAY",
                rv_grade="RETROSPECTIVE_PIT_UNPROVEN",
            )
        rebuilt = replace(b, reconstructed_at="2026-09-18T19:30:09Z")
        artifact = build(
            p,
            a,
            rebuilt,
            ms_grade="PIT_QUALIFIED_REPLAY",
            rv_grade="RETROSPECTIVE_PIT_UNPROVEN",
        )
        self.assertEqual(
            artifact.to_dict()["observation"]["evidence_grade"],
            "RETROSPECTIVE_PIT_UNPROVEN",
        )

    def test_prospective_context_forbids_reconstruction(self):
        p = projection()
        a = availability(p)
        b = replace(
            binding(p, a),
            reconstructed_at="2026-09-18T19:30:09Z",
        )
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "RECONSTRUCTION_FORBIDDEN",
        ):
            build(
                p,
                a,
                b,
                ms_grade="PROSPECTIVE_FIRST_SEEN",
                rv_grade="PROSPECTIVE_FIRST_SEEN",
            )

    def test_owner_instrument_mismatch_is_refused(self):
        p = projection()
        a = availability(p)
        b = binding(p, a)
        bad_market_binding = replace(
            owner_binding("market-state-owner", "market-state"),
            instrument_id="SEC:US-XNAS-QQQ",
        )
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "OBSERVATION_INSTRUMENT_MISMATCH",
        ):
            build_new_entry_context(
                candidate_projection=p,
                entry_availability=a,
                binding=b,
                market_state=market_state(),
                market_state_binding=bad_market_binding,
            )

    def test_no_owner_context_source_is_refused_not_zero_filled(self):
        p = projection()
        a = availability(p)
        b = binding(p, a)
        with self.assertRaisesRegex(
            PTSENewEntryContextError,
            "OWNER_FACT_ADAPTER_INVALID",
        ):
            build_new_entry_context(
                candidate_projection=p,
                entry_availability=a,
                binding=b,
            )

    def test_source_inputs_are_not_mutated(self):
        p = projection()
        a = availability(p)
        ms = market_state()
        rv = regime_vector()
        before = copy.deepcopy((p, a, ms, rv))
        build_new_entry_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            market_state=ms,
            market_state_binding=owner_binding(
                "market-state-owner",
                "market-state",
            ),
            regime_vector=rv,
            regime_vector_binding=owner_binding(
                "regime-vector-owner",
                "regime-vector",
            ),
        )
        self.assertEqual((p, a, ms, rv), before)


if __name__ == "__main__":
    unittest.main()