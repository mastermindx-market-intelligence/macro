"""Synthetic owner-adapter tests; no live source or outcome admission."""

from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import json
import unittest

from research.options_estate.ptse_contract import (
    AUTHORITY_KEYS,
    build_context,
)
from research.options_estate.ptse_owner_observation import (
    OwnerArtifactBinding,
    PTSEOwnerAdapterError,
    adapt_market_state,
    adapt_regime_vector,
    compose_owner_facts,
)


DECISION = "2026-10-02T21:00:00Z"
SESSION = "2026-10-02"


def ref(name: str, owner: str) -> dict:
    return {
        "owner_ref": owner,
        "artifact_id": "fixture:" + name,
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


def payload_sha(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def binding(owner: str, name: str, *, grade="SYNTHETIC", payload=None) -> OwnerArtifactBinding:
    payload = ({"market-state": market_state, "regime-vector": regime_vector}[name]()
               if payload is None else payload)
    return OwnerArtifactBinding(
        owner_ref=owner,
        artifact_ref={**ref(name, owner), "sha256": payload_sha(payload)},
        known_at_earliest="2026-10-02T20:05:00Z",
        known_at_latest="2026-10-02T20:05:00Z",
        known_at_precision="EXACT",
        known_at_evidence_ref=ref(name + "-known", owner),
        economic_time="2026-10-02T20:00:00Z",
        valid_until="2026-10-03T20:00:00Z",
        evidence_grade=grade,
        population_ref=ref(name + "-population", owner),
        instrument_id="fixture:SPY",
        session_scope="REGULAR",
        calculation_version="fixture:" + name + "-v1",
        limitations=("Synthetic owner fixture; no market or authority claim.",),
    )


def market_state() -> dict:
    return {
        "schema": "market_state.v1",
        "asof": SESSION,
        "market": "us",
        "verdict": "MIXED",
        "raw_score": 57,
        "score": 52,
        "score_source": "radar_ceiling",
        "capped": True,
        "radar": {"state": "caution"},
        "participation_scope": {
            "state": "selective",
            "participation": "uneven",
        },
        "freshness": {
            "data_asof": SESSION,
            "expected_asof": SESSION,
            "stale": False,
            "any_input_stale": False,
        },
        "degraded_components": [],
        "is_display_only": True,
    }


def regime_vector() -> dict:
    return {
        "schema_version": 1,
        "asof": SESSION,
        "quad_hard_label": "Q2",
        "rate_pressure": "neutral",
        "risk_radar_state": "caution",
        "vol_regime": "normal",
        "liquidity_quality_label": "benign",
        "deescalation_eligible": True,
        "deescalation_trajectory": {
            "phase": "receding",
            "intensity": 61.2,
            "velocity": -3.1,
        },
        "dislocation_verdict": "watch",
        "dislocation_active": False,
        "breadth_pct_above_50": 48.5,
        "breadth_pct_above_200": 54.0,
        "regime_vector_degraded": False,
        "degraded_axes": [],
        # Explicitly present incumbent directives. Adapter must not carry them.
        "favor_entries": True,
        "cap_leadership": False,
        "fused_risk_gross": 0.8,
    }


def assessment(driver: str) -> dict:
    return {
        "episode_id": "fixture:episode-1",
        "security_id": "fixture:AMD",
        "company_id": "fixture:company-AMD",
        "identity_epoch": "fixture:epoch-1",
        "candidate_generation_id": "fixture:generation-1",
        "cohort_ref": ref("cohort", "fixture-prophet-owner"),
        "strategy_id": "fixture:swing",
        "strategy_version": "fixture:strategy-v1",
        "holding_horizon_ref": ref("holding", "fixture-strategy-owner"),
        "action": "NEW_ENTRY",
        "decision_at": DECISION,
        "issued_at": "2026-10-02T21:02:00Z",
        "forecast_horizon_sessions": 5,
        "forecast_end_session": "2026-10-09",
        "calendar_ref": ref("calendar", "fixture-calendar-owner"),
        "target_version": "fixture:target-v1",
        "applicability": "APPLICABLE",
        "applicability_reason": "Synthetic fixture only.",
        "eligibility_ref": ref("eligibility", "fixture-prophet-owner"),
        "position_ref": None,
        "geometry_ref": None,
        "risk_budget_ref": None,
        "prior_exit_episode_ref": None,
        "evidence_status": "OBSERVED_CONTEXT_ONLY",
        "estimate_status": "NOT_FITTED",
        "estimate": None,
        "drivers": [driver],
        "contradictions": [],
        "authority": {key: False for key in AUTHORITY_KEYS},
    }


def observation(facts: list[dict]) -> dict:
    return {
        "market": "US",
        "instrument_id": "fixture:SPY",
        "market_session": SESSION,
        "cadence": "DAILY",
        "session_scope": "REGULAR",
        "decision_at": DECISION,
        "issued_at": "2026-10-02T21:01:00Z",
        "valid_until": "2026-10-03T20:00:00Z",
        "calendar_ref": ref("calendar", "fixture-calendar-owner"),
        "freshness_ref": ref("freshness", "fixture-observation-owner"),
        "source_manifest_ref": ref("manifest", "fixture-observation-owner"),
        "calculation_receipt_ref": ref("receipt", "fixture-observation-owner"),
        "producer_revision": "a" * 40,
        "feature_version": "fixture:ptse-owner-facts-v1",
        "evidence_grade": "SYNTHETIC",
        "reconstructed_at": None,
        "supersedes_ref": None,
        "correction_reason": None,
        "facts": facts,
    }


class PTSEOwnerObservationTest(unittest.TestCase):
    def test_market_and_regime_payload_changes_cannot_reuse_original_receipt(self):
        for factory, adapter, owner, name, field, value in (
            (market_state, adapt_market_state, "market-state-owner", "market-state", "raw_score", 99),
            (regime_vector, adapt_regime_vector, "regime-vector-owner", "regime-vector", "breadth_pct_above_50", 99),
        ):
            with self.subTest(source=name):
                original = factory()
                receipt = binding(owner, name, payload=original)
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_ARTIFACT_REF_MISMATCH"):
                    adapter(changed, receipt, market_session=SESSION, decision_at=DECISION)
                # Bind the changed content explicitly: normal value validation
                # and fact projection still operate under a new source digest.
                facts = adapter(changed, binding(owner, name, payload=changed),
                                market_session=SESSION, decision_at=DECISION)
                self.assertEqual(receipt.artifact_ref["sha256"], payload_sha(original))
                self.assertEqual(facts[0]["source_artifact_ref"]["sha256"], payload_sha(changed))

    def test_whole_payload_receipt_includes_unprojected_fields(self):
        for factory, adapter, owner, name in (
            (market_state, adapt_market_state, "market-state-owner", "market-state"),
            (regime_vector, adapt_regime_vector, "regime-vector-owner", "regime-vector"),
        ):
            payload = factory()
            original_binding = binding(owner, name, payload=payload)
            payload["unprojected_owner_metadata"] = "changed"
            with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_ARTIFACT_REF_MISMATCH"):
                adapter(payload, original_binding, market_session=SESSION, decision_at=DECISION)

    def test_owner_payload_key_order_does_not_change_content_binding(self):
        for factory, adapter, owner, name in (
            (market_state, adapt_market_state, "market-state-owner", "market-state"),
            (regime_vector, adapt_regime_vector, "regime-vector-owner", "regime-vector"),
        ):
            payload = factory()
            receipt = binding(owner, name, payload=payload)
            reordered = {k: payload[k] for k in reversed(payload)}
            self.assertEqual(adapter(payload, receipt, market_session=SESSION, decision_at=DECISION),
                             adapter(reordered, receipt, market_session=SESSION, decision_at=DECISION))

    def test_noncanonical_owner_payload_is_typed_refusal(self):
        for value in (float("nan"), object()):
            payload = market_state()
            payload["unprojected_owner_metadata"] = value
            with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_PAYLOAD_NOT_CANONICAL"):
                adapt_market_state(payload, binding("market-state-owner", "market-state"),
                                   market_session=SESSION, decision_at=DECISION)

    def test_market_state_maps_only_passive_owner_fields(self):
        facts = adapt_market_state(
            market_state(),
            binding("market-state-owner", "market-state"),
            market_session=SESSION,
            decision_at=DECISION,
        )
        ids = [fact["feature_id"] for fact in facts]
        self.assertEqual(
            ids,
            [
                "market_state.verdict",
                "market_state.raw_score",
                "market_state.score_source",
                "market_state.capped",
                "market_state.radar_state",
                "market_state.participation_state",
                "market_state.participation_strength",
                "market_state.any_input_stale",
            ],
        )
        self.assertTrue(all(fact["status"] == "OBSERVED" for fact in facts))
        by_id = {fact["feature_id"]: fact for fact in facts}
        self.assertEqual(by_id["market_state.verdict"]["value"], "MIXED")
        self.assertEqual(by_id["market_state.raw_score"]["value"], 57)
        self.assertIn("is_display_only=true", " ".join(by_id["market_state.verdict"]["limitations"]))

    def test_market_state_requires_display_only_us_schema_and_exact_session(self):
        cases = (
            ("schema", "other.v1", "MARKET_STATE_SCHEMA_INVALID"),
            ("market", "cn", "MARKET_STATE_AUTHORITY_INVALID"),
            ("is_display_only", False, "MARKET_STATE_AUTHORITY_INVALID"),
            ("asof", "2026-10-01", "MARKET_STATE_SESSION_MISMATCH"),
        )
        for key, value, code in cases:
            with self.subTest(key=key):
                payload = market_state()
                payload[key] = value
                with self.assertRaisesRegex(PTSEOwnerAdapterError, code):
                    adapt_market_state(
                        payload,
                        binding("market-state-owner", "market-state", payload=payload),
                        market_session=SESSION,
                        decision_at=DECISION,
                    )

    def test_missing_optional_owner_field_is_unavailable_not_zero(self):
        payload = market_state()
        del payload["participation_scope"]
        facts = adapt_market_state(
            payload,
            binding("market-state-owner", "market-state", payload=payload),
            market_session=SESSION,
            decision_at=DECISION,
        )
        by_id = {fact["feature_id"]: fact for fact in facts}
        missing = by_id["market_state.participation_state"]
        self.assertEqual(missing["status"], "UNAVAILABLE")
        self.assertIsNone(missing["value"])
        self.assertEqual(missing["null_reason"], "OWNER_FIELD_UNAVAILABLE")
        self.assertEqual(missing["coverage"]["numerator"], 0)
        self.assertEqual(missing["coverage"]["missing_count"], 1)

    def test_regime_vector_directives_never_enter_fact_set(self):
        facts = adapt_regime_vector(
            regime_vector(),
            binding("regime-vector-owner", "regime-vector"),
            market_session=SESSION,
            decision_at=DECISION,
        )
        ids = {fact["feature_id"] for fact in facts}
        self.assertFalse(any("favor_entries" in x for x in ids))
        self.assertFalse(any("cap_leadership" in x for x in ids))
        self.assertFalse(any("fused_risk_gross" in x for x in ids))
        self.assertIn("regime_vector.rate_pressure", ids)
        self.assertIn("regime_vector.degraded", ids)
        self.assertIn("regime_vector.deescalation_phase", ids)
        self.assertIn("regime_vector.deescalation_intensity", ids)
        self.assertNotIn("regime_vector.deescalation_trajectory", ids)

    def test_regime_vector_preserves_statistical_vs_deterministic_method_kind(self):
        facts = adapt_regime_vector(
            regime_vector(),
            binding("regime-vector-owner", "regime-vector"),
            market_session=SESSION,
            decision_at=DECISION,
        )
        by_id = {fact["feature_id"]: fact for fact in facts}
        self.assertEqual(
            by_id["regime_vector.quad_hard_label"]["method_kind"],
            "STATISTICAL_ESTIMATE",
        )
        self.assertEqual(
            by_id["regime_vector.rate_pressure"]["method_kind"],
            "DETERMINISTIC_COMPUTATION",
        )

    def test_regime_vector_schema_and_session_are_closed(self):
        payload = regime_vector()
        payload["schema_version"] = 2
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "REGIME_VECTOR_SCHEMA_INVALID"):
            adapt_regime_vector(
                payload,
                binding("regime-vector-owner", "regime-vector", payload=payload),
                market_session=SESSION,
                decision_at=DECISION,
            )
        payload = regime_vector()
        payload["asof"] = "2026-10-01"
        with self.assertRaisesRegex(
            PTSEOwnerAdapterError,
            "REGIME_VECTOR_SESSION_MISMATCH",
        ):
            adapt_regime_vector(
                payload,
                binding("regime-vector-owner", "regime-vector", payload=payload),
                market_session=SESSION,
                decision_at=DECISION,
            )

    def test_bad_owner_value_is_fail_closed(self):
        payload = market_state()
        payload["raw_score"] = 101
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_VALUE_RANGE_INVALID"):
            adapt_market_state(
                payload,
                binding("market-state-owner", "market-state", payload=payload),
                market_session=SESSION,
                decision_at=DECISION,
            )
        payload = regime_vector()
        payload["dislocation_active"] = 1
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_VALUE_TYPE_INVALID"):
            adapt_regime_vector(
                payload,
                binding("regime-vector-owner", "regime-vector", payload=payload),
                market_session=SESSION,
                decision_at=DECISION,
            )

    def test_availability_is_explicit_and_cannot_arrive_after_decision(self):
        late = replace(
            binding("market-state-owner", "market-state"),
            known_at_earliest="2026-10-02T21:00:01Z",
            known_at_latest="2026-10-02T21:00:01Z",
        )
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "NOT_KNOWN_AT_DECISION"):
            adapt_market_state(
                market_state(),
                late,
                market_session=SESSION,
                decision_at=DECISION,
            )

    def test_expired_owner_artifact_surfaces_as_stale_not_rejected(self):
        stale = replace(
            binding("market-state-owner", "market-state"),
            valid_until="2026-10-02T20:30:00Z",
        )
        facts = adapt_market_state(
            market_state(),
            stale,
            market_session=SESSION,
            decision_at=DECISION,
        )
        self.assertTrue(all(fact["status"] == "STALE" for fact in facts))
        self.assertTrue(
            all(fact["null_reason"] == "SOURCE_EXPIRED_AT_DECISION" for fact in facts)
        )
        artifact = build_context(
            observation(copy.deepcopy(facts)),
            assessment("market_state.verdict"),
        )
        by_id = {
            fact["feature_id"]: fact
            for fact in artifact.to_dict()["observation"]["facts"]
        }
        self.assertEqual(by_id["market_state.verdict"]["status"], "STALE")

    def test_compose_requires_payload_binding_pairs_and_at_least_one_owner(self):
        with self.assertRaisesRegex(PTSEOwnerAdapterError, "OWNER_SOURCE_REQUIRED"):
            compose_owner_facts(
                market_session=SESSION,
                decision_at=DECISION,
            )
        with self.assertRaisesRegex(
            PTSEOwnerAdapterError,
            "MARKET_STATE_BINDING_REQUIRED",
        ):
            compose_owner_facts(
                market_session=SESSION,
                decision_at=DECISION,
                market_state=market_state(),
            )

    def test_combined_fact_set_round_trips_through_ptse_contract(self):
        facts = compose_owner_facts(
            market_session=SESSION,
            decision_at=DECISION,
            market_state=market_state(),
            market_state_binding=binding(
                "market-state-owner",
                "market-state",
            ),
            regime_vector=regime_vector(),
            regime_vector_binding=binding(
                "regime-vector-owner",
                "regime-vector",
            ),
        )
        self.assertEqual(
            [fact["feature_id"] for fact in facts],
            sorted(fact["feature_id"] for fact in facts),
        )
        driver = "market_state.verdict"
        artifact = build_context(
            observation(copy.deepcopy(facts)),
            assessment(driver),
        )
        payload = artifact.to_dict()
        self.assertEqual(payload["assessment"]["authority"], {key: False for key in AUTHORITY_KEYS})
        self.assertEqual(
            payload["assessment"]["evidence_status"],
            "OBSERVED_CONTEXT_ONLY",
        )
        self.assertEqual(
            payload["observation"]["facts"][0]["feature_id"],
            sorted(fact["feature_id"] for fact in facts)[0],
        )

    def test_source_grade_remains_attached_per_fact(self):
        facts = compose_owner_facts(
            market_session=SESSION,
            decision_at=DECISION,
            market_state=market_state(),
            market_state_binding=binding(
                "market-state-owner",
                "market-state",
                grade="PIT_QUALIFIED_REPLAY",
            ),
        )
        self.assertEqual(
            {fact["evidence_grade"] for fact in facts},
            {"PIT_QUALIFIED_REPLAY"},
        )


if __name__ == "__main__":
    unittest.main()
