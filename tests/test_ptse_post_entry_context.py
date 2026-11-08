"""Fail-closed post-entry action tests while the relation owner is absent."""

from __future__ import annotations

import unittest

from research.options_estate.ptse_new_entry_context import build_new_entry_context
from research.options_estate.ptse_post_entry_context import (
    PTSEPostEntryContextError,
    build_unresolved_post_entry_context,
)
from tests.test_ptse_new_entry_context import (
    OPTIONS_ROOT_BINDING,
    availability,
    binding,
    market_state,
    options_binding,
    options_gex,
    options_vol,
    owner_binding,
    projection,
)


def base_context(*, with_options=False):
    p = projection()
    a = availability(p)
    kwargs = {}
    if with_options:
        kwargs = {
            "options_root_binding": OPTIONS_ROOT_BINDING,
            "options_vol": options_vol(),
            "options_vol_binding": options_binding("vol"),
            "options_gex": options_gex(),
            "options_gex_binding": options_binding("gex"),
        }
    return build_new_entry_context(
        candidate_projection=p,
        entry_availability=a,
        binding=binding(p, a),
        market_state=market_state(),
        market_state_binding=owner_binding(
            "market-state-owner",
            "market-state",
        ),
        **kwargs,
    )


class PTSEPostEntryContextTest(unittest.TestCase):
    def test_all_four_blocked_actions_are_typed_unknown(self):
        base = base_context()
        for action in ("CONTINUATION", "ADD", "DERISK", "REENTRY"):
            with self.subTest(action=action):
                artifact = build_unresolved_post_entry_context(
                    base_context=base,
                    action=action,
                )
                assessment = artifact.to_dict()["assessment"]
                self.assertEqual(assessment["action"], action)
                self.assertEqual(assessment["applicability"], "UNKNOWN")
                self.assertEqual(
                    assessment["applicability_reason"],
                    "CANONICAL_EPISODE_PLAN_POSITION_RELATION_UNAVAILABLE",
                )
                self.assertFalse(any(assessment["authority"].values()))

    def test_unknown_post_entry_context_mints_no_fake_owner_refs(self):
        artifact = build_unresolved_post_entry_context(
            base_context=base_context(),
            action="ADD",
        )
        assessment = artifact.to_dict()["assessment"]
        for key in (
            "eligibility_ref",
            "position_ref",
            "geometry_ref",
            "risk_budget_ref",
            "prior_exit_episode_ref",
        ):
            self.assertIsNone(assessment[key])

    def test_observation_identity_is_byte_equivalent_across_blocked_actions(self):
        base = base_context(with_options=True)
        base_observation = base.to_dict()["observation"]
        for action in ("CONTINUATION", "ADD", "DERISK", "REENTRY"):
            artifact = build_unresolved_post_entry_context(
                base_context=base,
                action=action,
            )
            self.assertEqual(
                artifact.to_dict()["observation"],
                base_observation,
            )

    def test_b1_strategy_and_h5_identity_are_preserved(self):
        base = base_context()
        prior = base.to_dict()["assessment"]
        artifact = build_unresolved_post_entry_context(
            base_context=base,
            action="CONTINUATION",
        )
        current = artifact.to_dict()["assessment"]
        for key in (
            "episode_id",
            "security_id",
            "company_id",
            "identity_epoch",
            "candidate_generation_id",
            "cohort_ref",
            "strategy_id",
            "strategy_version",
            "holding_horizon_ref",
            "decision_at",
            "forecast_horizon_sessions",
            "forecast_end_session",
            "calendar_ref",
            "target_version",
        ):
            self.assertEqual(current[key], prior[key])

    def test_new_entry_and_pullback_are_not_accepted_by_this_blocked_adapter(self):
        for action in ("NEW_ENTRY", "PULLBACK_BUY"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(
                    PTSEPostEntryContextError,
                    "POST_ENTRY_ACTION_INVALID",
                ):
                    build_unresolved_post_entry_context(
                        base_context=base_context(),
                        action=action,
                    )

    def test_reason_is_explicit_and_cannot_be_blank_or_whitespace(self):
        for reason in ("", " relation unavailable "):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(
                    PTSEPostEntryContextError,
                    "APPLICABILITY_REASON_REQUIRED",
                ):
                    build_unresolved_post_entry_context(
                        base_context=base_context(),
                        action="DERISK",
                        reason=reason,
                    )

    def test_invalid_base_context_is_refused(self):
        with self.assertRaisesRegex(
            PTSEPostEntryContextError,
            "BASE_CONTEXT_INVALID",
        ):
            build_unresolved_post_entry_context(
                base_context=b"{}",
                action="CONTINUATION",
            )


if __name__ == "__main__":
    unittest.main()