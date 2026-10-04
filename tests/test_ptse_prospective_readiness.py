"""Synthetic prospective-readiness tests; no publication or natural-run claim."""

from __future__ import annotations

from dataclasses import replace
import copy
import unittest

from research.options_estate.ptse_new_entry_context import build_new_entry_context
from research.options_estate.ptse_prospective_readiness import (
    PTSEProspectiveReadinessError,
    qualify_prospective_observation,
)
from research.options_estate.ptse_pullback_buy_context import build_pullback_buy_context
from tests.test_ptse_new_entry_context import (
    OPTIONS_ROOT_BINDING,
    availability,
    b4_facts,
    binding,
    market_state,
    options_binding,
    options_gex,
    options_vol,
    owner_binding,
    projection,
    regime_vector,
)
from tests.test_ptse_pullback_buy_context import geometry_ref


def prospective_new_entry(*, with_options=False):
    p = projection()
    a = availability(p)
    b = binding(p, a)
    kwargs = {}
    if with_options:
        kwargs = {
            "options_root_binding": OPTIONS_ROOT_BINDING,
            "options_vol": options_vol(),
            "options_vol_binding": options_binding(
                "vol", grade="PROSPECTIVE_FIRST_SEEN"
            ),
            "options_gex": options_gex(),
            "options_gex_binding": options_binding(
                "gex", grade="PROSPECTIVE_FIRST_SEEN"
            ),
        }
    return build_new_entry_context(
        candidate_projection=p,
        entry_availability=a,
        binding=b,
        market_state=market_state(),
        market_state_binding=owner_binding(
            "market-state-owner",
            "market-state",
            grade="PROSPECTIVE_FIRST_SEEN",
        ),
        regime_vector=regime_vector(),
        regime_vector_binding=owner_binding(
            "regime-vector-owner",
            "regime-vector",
            grade="PROSPECTIVE_FIRST_SEEN",
        ),
        **kwargs,
    )


class PTSEProspectiveReadinessTest(unittest.TestCase):
    def test_new_entry_prospective_context_is_ready_without_granting_authority(self):
        artifact = prospective_new_entry()
        result = qualify_prospective_observation(artifact)
        self.assertEqual(result.status, "READY_FOR_EXISTING_PUBLICATION_OWNER")
        self.assertEqual(result.evidence_grade, "PROSPECTIVE_FIRST_SEEN")
        self.assertEqual(result.action, "NEW_ENTRY")
        self.assertFalse(result.publication_authority)
        self.assertFalse(result.decision_authority)
        self.assertEqual(len(result.artifact_sha256), 64)

    def test_optional_options_must_also_be_prospective(self):
        result = qualify_prospective_observation(
            prospective_new_entry(with_options=True)
        )
        self.assertEqual(result.action, "NEW_ENTRY")

        p = projection()
        a = availability(p)
        artifact = build_new_entry_context(
            candidate_projection=p,
            entry_availability=a,
            binding=replace(
                binding(p, a),
                reconstructed_at="2026-09-18T19:30:09Z",
            ),
            market_state=market_state(),
            market_state_binding=owner_binding(
                "market-state-owner",
                "market-state",
                grade="PIT_QUALIFIED_REPLAY",
            ),
            options_root_binding=OPTIONS_ROOT_BINDING,
            options_vol=options_vol(),
            options_vol_binding=options_binding(
                "vol", grade="RETROSPECTIVE_PIT_UNPROVEN"
            ),
        )
        with self.assertRaisesRegex(
            PTSEProspectiveReadinessError,
            "OBSERVATION_NOT_PROSPECTIVE",
        ):
            qualify_prospective_observation(artifact)

    def test_synthetic_context_is_not_prospective_readiness(self):
        p = projection()
        a = availability(p)
        synthetic = build_new_entry_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        with self.assertRaisesRegex(
            PTSEProspectiveReadinessError,
            "OBSERVATION_NOT_PROSPECTIVE",
        ):
            qualify_prospective_observation(synthetic)

    def test_pullback_buy_can_be_prospectively_ready_without_entry_permission(self):
        p = projection()
        a = availability(p, b4_facts(price=43.40))
        artifact = build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=geometry_ref(),
            market_state=market_state(),
            market_state_binding=owner_binding(
                "market-state-owner",
                "market-state",
                grade="PROSPECTIVE_FIRST_SEEN",
            ),
        )
        result = qualify_prospective_observation(artifact)
        self.assertEqual(result.action, "PULLBACK_BUY")
        self.assertFalse(result.decision_authority)

    def test_late_known_fact_is_refused_even_if_wire_is_rehashed(self):
        artifact = prospective_new_entry()
        payload = artifact.to_dict()
        payload["observation"]["facts"][0]["known_at"]["latest"] = "2026-09-18T19:30:09Z"
        # Rebuild through context factory so the semantic violation, not an old digest,
        # is the thing readiness sees.
        from research.options_estate.ptse_contract import build_context
        with self.assertRaises(Exception):
            build_context(payload["observation"], payload["assessment"])

    def test_mutation_of_input_artifact_is_not_performed(self):
        artifact = prospective_new_entry(with_options=True)
        before = artifact.canonical_bytes
        qualify_prospective_observation(artifact)
        self.assertEqual(artifact.canonical_bytes, before)

    def test_estimate_and_authority_must_remain_closed(self):
        artifact = prospective_new_entry()
        payload = artifact.to_dict()
        payload["assessment"]["authority"]["rank"] = True
        from research.options_estate.ptse_contract import canonical_json
        raw = canonical_json(payload)
        with self.assertRaisesRegex(
            PTSEProspectiveReadinessError,
            "CONTEXT_INVALID",
        ):
            qualify_prospective_observation(raw)


if __name__ == "__main__":
    unittest.main()