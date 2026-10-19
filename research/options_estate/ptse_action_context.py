"""Single PTSE action-conditioned adapter surface.

This module is a thin dispatcher over the existing action compilers. It creates
no source, lifecycle, eligibility, plan/position relation, publisher, cache,
scheduler, model, rank, sizing, execution or trade authority.

- NEW_ENTRY delegates to the exact B3/B4 compiler.
- PULLBACK_BUY delegates to the exact B3/B4 + owner-geometry compiler.
- CONTINUATION / ADD / DERISK / REENTRY delegate only to the fail-closed
  UNKNOWN adapter until the incumbent relation owner exists.

The point is one consumer-facing composition surface without collapsing action
semantics or granting a blocked action a fake join.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from research.options_estate.ptse_contract import ContextArtifact, EvidenceRef
from research.options_estate.ptse_new_entry_context import (
    NewEntryContextBinding,
    build_new_entry_context,
)
from research.options_estate.ptse_options_observation import OptionsRootBinding
from research.options_estate.ptse_owner_observation import OwnerArtifactBinding
from research.options_estate.ptse_post_entry_context import (
    POST_ENTRY_ACTIONS,
    build_unresolved_post_entry_context,
)
from research.options_estate.ptse_pullback_buy_context import (
    build_pullback_buy_context,
)


class PTSEActionContextError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEActionContextError(code)


def build_action_context(
    *,
    action: str,
    base_context: ContextArtifact | bytes | str | None = None,
    candidate_projection: Mapping[str, Any] | None = None,
    entry_availability: Mapping[str, Any] | None = None,
    binding: NewEntryContextBinding | None = None,
    geometry_ref: EvidenceRef | None = None,
    unresolved_reason: str = "CANONICAL_EPISODE_PLAN_POSITION_RELATION_UNAVAILABLE",
    market_state: Mapping[str, Any] | None = None,
    market_state_binding: OwnerArtifactBinding | None = None,
    regime_vector: Mapping[str, Any] | None = None,
    regime_vector_binding: OwnerArtifactBinding | None = None,
    options_root_binding: OptionsRootBinding | None = None,
    options_vol: Mapping[str, Any] | None = None,
    options_vol_binding: OwnerArtifactBinding | None = None,
    options_gex: Mapping[str, Any] | None = None,
    options_gex_binding: OwnerArtifactBinding | None = None,
) -> ContextArtifact:
    """Build one action context while preserving per-action owner gates."""

    if action == "NEW_ENTRY":
        if base_context is not None or geometry_ref is not None:
            _fail("ACTION_ARGUMENT_FORBIDDEN")
        if (
            candidate_projection is None
            or entry_availability is None
            or binding is None
        ):
            _fail("NEW_ENTRY_INPUT_REQUIRED")
        return build_new_entry_context(
            candidate_projection=candidate_projection,
            entry_availability=entry_availability,
            binding=binding,
            market_state=market_state,
            market_state_binding=market_state_binding,
            regime_vector=regime_vector,
            regime_vector_binding=regime_vector_binding,
            options_root_binding=options_root_binding,
            options_vol=options_vol,
            options_vol_binding=options_vol_binding,
            options_gex=options_gex,
            options_gex_binding=options_gex_binding,
        )

    if action == "PULLBACK_BUY":
        if base_context is not None:
            _fail("ACTION_ARGUMENT_FORBIDDEN")
        if (
            candidate_projection is None
            or entry_availability is None
            or binding is None
        ):
            _fail("PULLBACK_INPUT_REQUIRED")
        return build_pullback_buy_context(
            candidate_projection=candidate_projection,
            entry_availability=entry_availability,
            binding=binding,
            geometry_ref=geometry_ref,
            market_state=market_state,
            market_state_binding=market_state_binding,
            regime_vector=regime_vector,
            regime_vector_binding=regime_vector_binding,
            options_root_binding=options_root_binding,
            options_vol=options_vol,
            options_vol_binding=options_vol_binding,
            options_gex=options_gex,
            options_gex_binding=options_gex_binding,
        )

    if action in POST_ENTRY_ACTIONS:
        # Post-entry actions cannot use candidate/B4/geometry inputs through
        # this dispatcher while the canonical episode-plan-position relation is absent.
        if base_context is None:
            _fail("POST_ENTRY_BASE_CONTEXT_REQUIRED")
        if any(
            value is not None
            for value in (
                candidate_projection,
                entry_availability,
                binding,
                geometry_ref,
                market_state,
                market_state_binding,
                regime_vector,
                regime_vector_binding,
                options_root_binding,
                options_vol,
                options_vol_binding,
                options_gex,
                options_gex_binding,
            )
        ):
            _fail("POST_ENTRY_OWNER_ARGUMENT_FORBIDDEN")
        return build_unresolved_post_entry_context(
            base_context=base_context,
            action=action,
            reason=unresolved_reason,
        )

    _fail("ACTION_NOT_ADMITTED")


__all__ = ["PTSEActionContextError", "build_action_context"]