"""Six-action dispatcher tests over existing PTSE compilers."""

from __future__ import annotations

import unittest

from research.options_estate.ptse_action_context import (
    PTSEActionContextError,
    build_action_context,
)
from research.options_estate.ptse_new_entry_context import build_new_entry_context
from research.options_estate.ptse_post_entry_context import (
    build_unresolved_post_entry_context,
)
from research.options_estate.ptse_pullback_buy_context import (
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
)
from tests.test_ptse_pullback_buy_context import geometry_ref


def new_entry_inputs(*, with_options=False):
    p = projection()
    a = availability(p)
    kwargs = {
        "candidate_projection": p,
        "entry_availability": a,
        "binding": binding(p, a),
        "market_state": market_state(),
        "market_state_binding": owner_binding("market-state-owner", "market-state"),
    }
    if with_options:
        kwargs.update({
            "options_root_binding": OPTIONS_ROOT_BINDING,
            "options_vol": options_vol(),
            "options_vol_binding": options_binding("vol"),
            "options_gex": options_gex(),
            "options_gex_binding": options_binding("gex"),
        })
    return kwargs


def pullback_inputs(*, with_options=False):
    p = projection()
    a = availability(p, b4_facts(price=43.40))
    kwargs = {
        "candidate_projection": p,
        "entry_availability": a,
        "binding": binding(p, a),
        "geometry_ref": geometry_ref(),
        "market_state": market_state(),
        "market_state_binding": owner_binding("market-state-owner", "market-state"),
    }
    if with_options:
        kwargs.update({
            "options_root_binding": OPTIONS_ROOT_BINDING,
            "options_vol": options_vol(),
            "options_vol_binding": options_binding("vol"),
            "options_gex": options_gex(),
            "options_gex_binding": options_binding("gex"),
        })
    return kwargs


class PTSEActionContextTest(unittest.TestCase):
    def test_new_entry_dispatch_is_byte_identical_to_existing_compiler(self):
        inputs = new_entry_inputs(with_options=True)
        direct = build_new_entry_context(**inputs)
        routed = build_action_context(action="NEW_ENTRY", **inputs)
        self.assertEqual(routed.canonical_bytes, direct.canonical_bytes)

    def test_pullback_dispatch_is_byte_identical_to_existing_compiler(self):
        inputs = pullback_inputs(with_options=True)
        direct = build_pullback_buy_context(**inputs)
        routed = build_action_context(action="PULLBACK_BUY", **inputs)
        self.assertEqual(routed.canonical_bytes, direct.canonical_bytes)

    def test_all_four_blocked_actions_dispatch_to_exact_unknown_adapter(self):
        base = build_new_entry_context(**new_entry_inputs())
        for action in ("CONTINUATION", "ADD", "DERISK", "REENTRY"):
            with self.subTest(action=action):
                direct = build_unresolved_post_entry_context(
                    base_context=base,
                    action=action,
                )
                routed = build_action_context(
                    action=action,
                    base_context=base,
                )
                self.assertEqual(routed.canonical_bytes, direct.canonical_bytes)
                self.assertEqual(
                    routed.to_dict()["assessment"]["applicability"],
                    "UNKNOWN",
                )

    def test_post_entry_dispatch_refuses_candidate_or_geometry_smuggling(self):
        base = build_new_entry_context(**new_entry_inputs())
        for injected in (
            {"candidate_projection": projection()},
            {"geometry_ref": geometry_ref()},
            {"market_state": market_state()},
        ):
            with self.subTest(injected=tuple(injected)):
                with self.assertRaisesRegex(
                    PTSEActionContextError,
                    "POST_ENTRY_OWNER_ARGUMENT_FORBIDDEN",
                ):
                    build_action_context(
                        action="CONTINUATION",
                        base_context=base,
                        **injected,
                    )

    def test_new_entry_does_not_accept_pullback_geometry(self):
        with self.assertRaisesRegex(
            PTSEActionContextError,
            "ACTION_ARGUMENT_FORBIDDEN",
        ):
            build_action_context(
                action="NEW_ENTRY",
                geometry_ref=geometry_ref(),
                **new_entry_inputs(),
            )

    def test_pullback_requires_b3_b4_inputs(self):
        with self.assertRaisesRegex(
            PTSEActionContextError,
            "PULLBACK_INPUT_REQUIRED",
        ):
            build_action_context(
                action="PULLBACK_BUY",
                geometry_ref=geometry_ref(),
            )

    def test_post_entry_requires_base_context(self):
        with self.assertRaisesRegex(
            PTSEActionContextError,
            "POST_ENTRY_BASE_CONTEXT_REQUIRED",
        ):
            build_action_context(action="DERISK")

    def test_unknown_action_is_closed(self):
        with self.assertRaisesRegex(
            PTSEActionContextError,
            "ACTION_NOT_ADMITTED",
        ):
            build_action_context(action="SELL")

    def test_custom_blocker_reason_is_preserved_without_creating_refs(self):
        base = build_new_entry_context(**new_entry_inputs())
        out = build_action_context(
            action="ADD",
            base_context=base,
            unresolved_reason="RELATION_OWNER_PENDING_EXACT_RECEIPT",
        ).to_dict()["assessment"]
        self.assertEqual(
            out["applicability_reason"],
            "RELATION_OWNER_PENDING_EXACT_RECEIPT",
        )
        self.assertIsNone(out["position_ref"])
        self.assertIsNone(out["geometry_ref"])
        self.assertIsNone(out["risk_budget_ref"])
        self.assertFalse(any(out["authority"].values()))


if __name__ == "__main__":
    unittest.main()