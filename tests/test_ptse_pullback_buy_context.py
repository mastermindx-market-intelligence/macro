"""Synthetic PULLBACK_BUY context tests over exact B3/B4 fixtures."""

from __future__ import annotations

import hashlib
import unittest

from research.options_estate.ptse_pullback_buy_context import (
    PTSEPullbackContextError,
    build_pullback_buy_context,
)
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


def geometry_ref() -> dict:
    digest = "2" * 64
    return {
        "owner_ref": "fixture-entry-geometry-owner",
        "artifact_id": "sha256:" + digest,
        "sha256": digest,
    }


def build_pullback(*, a=None, gref=None, with_options=False):
    p = projection()
    a = a or availability(p, b4_facts(price=43.40))
    kwargs = {}
    if with_options:
        kwargs = {
            "options_root_binding": OPTIONS_ROOT_BINDING,
            "options_vol": options_vol(),
            "options_vol_binding": options_binding("vol"),
            "options_gex": options_gex(),
            "options_gex_binding": options_binding("gex"),
        }
    return build_pullback_buy_context(
        candidate_projection=p,
        entry_availability=a,
        binding=binding(p, a),
        geometry_ref=gref if gref is not None else geometry_ref(),
        market_state=market_state(),
        market_state_binding=owner_binding("market-state-owner", "market-state"),
        regime_vector=regime_vector(),
        regime_vector_binding=owner_binding("regime-vector-owner", "regime-vector"),
        **kwargs,
    )


class PTSEPullbackBuyContextTest(unittest.TestCase):
    def test_wait_pullback_is_applicable_context_not_entry_permission(self):
        artifact = build_pullback()
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["action"], "PULLBACK_BUY")
        self.assertEqual(assessment["applicability"], "APPLICABLE")
        self.assertIn("CONTEXT_ONLY", assessment["applicability_reason"])
        self.assertFalse(any(assessment["authority"].values()))
        self.assertIsNotNone(assessment["geometry_ref"])

    def test_ran_dont_chase_can_carry_pullback_context_without_permission(self):
        p = projection()
        a = availability(p, b4_facts(price=44.10))
        self.assertEqual(a["state"], "RAN_DONT_CHASE")
        artifact = build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=geometry_ref(),
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "APPLICABLE")
        self.assertFalse(assessment["authority"]["entry_gating"])

    def test_entry_open_is_not_pullback_applicable(self):
        p = projection()
        a = availability(p)
        self.assertEqual(a["state"], "ENTRY_OPEN")
        artifact = build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=None,
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        assessment = artifact.to_dict()["assessment"]
        self.assertEqual(assessment["applicability"], "NOT_APPLICABLE")
        self.assertIsNone(assessment["geometry_ref"])
        self.assertFalse(any(assessment["authority"].values()))

    def test_unavailable_b4_is_unknown_and_does_not_require_geometry(self):
        p = projection()
        a = availability(p, b4_facts(freshness="STALE"))
        self.assertEqual(a["state"], "UNAVAILABLE_DATA")
        artifact = build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=None,
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        self.assertEqual(
            artifact.to_dict()["assessment"]["applicability"],
            "UNKNOWN",
        )

    def test_invalidated_b4_is_not_applicable(self):
        p = projection(state="INVALIDATED", terminal_reason="fixture")
        a = availability(p)
        artifact = build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=None,
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        self.assertEqual(
            artifact.to_dict()["assessment"]["applicability"],
            "NOT_APPLICABLE",
        )

    def test_applicable_pullback_requires_geometry_receipt(self):
        p = projection()
        a = availability(p, b4_facts(price=43.40))
        with self.assertRaisesRegex(
            PTSEPullbackContextError,
            "GEOMETRY_REF_REQUIRED",
        ):
            build_pullback_buy_context(
                candidate_projection=p,
                entry_availability=a,
                binding=binding(p, a),
                geometry_ref=None,
                market_state=market_state(),
                market_state_binding=owner_binding("market-state-owner", "market-state"),
            )

    def test_geometry_receipt_must_have_participated_in_b4(self):
        bad = {
            "owner_ref": "fixture-entry-geometry-owner",
            "artifact_id": "sha256:" + "9" * 64,
            "sha256": "9" * 64,
        }
        with self.assertRaisesRegex(
            PTSEPullbackContextError,
            "GEOMETRY_REF_NOT_IN_B4_RECEIPTS",
        ):
            build_pullback(gref=bad)

    def test_options_context_remains_optional_and_zero_authority(self):
        without = build_pullback()
        with_opts = build_pullback(with_options=True)
        no_ids = {f["feature_id"] for f in without.to_dict()["observation"]["facts"]}
        yes_ids = {f["feature_id"] for f in with_opts.to_dict()["observation"]["facts"]}
        self.assertFalse(any(x.startswith("options.") for x in no_ids))
        self.assertTrue(any(x.startswith("options.") for x in yes_ids))
        self.assertFalse(any(with_opts.to_dict()["assessment"]["authority"].values()))

    def test_new_entry_owner_artifacts_are_not_mutated(self):
        p = projection()
        a = availability(p, b4_facts(price=43.40))
        before_p = repr(p)
        before_a = repr(a)
        build_pullback_buy_context(
            candidate_projection=p,
            entry_availability=a,
            binding=binding(p, a),
            geometry_ref=geometry_ref(),
            market_state=market_state(),
            market_state_binding=owner_binding("market-state-owner", "market-state"),
        )
        self.assertEqual(repr(p), before_p)
        self.assertEqual(repr(a), before_a)


if __name__ == "__main__":
    unittest.main()