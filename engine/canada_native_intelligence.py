"""Typed Canada-native Prophet intelligence for zero-authority shadow races.

The current Branch-B board is intentionally a screen, not a validated official
pick authority.  C7 residual momentum and C1 oil->XEG both remain ACCRUING.
This module therefore provides only narrow typed metadata plus one
same-population Lane-A rank adapter over the incumbent calls' existing edge_z.
It never originates candidates, fuses families, changes entry permission, or
publishes a Canada master score.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from enum import Enum
from types import MappingProxyType
from typing import Any

RESIDUAL_MOMENTUM_FAMILY = "ca_residual_momentum"
RESIDUAL_MOMENTUM_STATUS = "ACCRUING"
RESIDUAL_MOMENTUM_AUTHORITY = "name_intelligence_shadow"
RESIDUAL_MOMENTUM_DEFINITION = "ca_residual_momentum_rank_v1"

C1_OIL_STATUS = "ACCRUING"
C1_OIL_AUTHORITY = "sector_context_only"

class InheritedGateDisposition(str, Enum):
    """Closed Canada disposition vocabulary from masterplan section 11.3."""

    STRUCTURAL_COMMON = "STRUCTURAL_COMMON"
    MARKET_VALIDATED = "MARKET_VALIDATED"
    SCREEN_SHADOW = "SCREEN_SHADOW"
    RETIRE = "RETIRE"


# Actual production consumption sites for the inherited US anticipation gate.
# Both remain display/research context only while Canada-specific evidence accrues.
ANTICIPATION_PROFILE_CONTEXT_USE = "anticipation.forward_cone_profile_context"
ANTICIPATION_POTENTIAL_SCORE_USE = "anticipation.name_score_confidence"
INHERITED_US_GATE_DISPOSITIONS = MappingProxyType({
    ANTICIPATION_PROFILE_CONTEXT_USE: InheritedGateDisposition.SCREEN_SHADOW,
    ANTICIPATION_POTENTIAL_SCORE_USE: InheritedGateDisposition.SCREEN_SHADOW,
})

# Backward-compatible summary used by existing evidence/tests.
ANTICIPATION_US_GATE_DISPOSITION = InheritedGateDisposition.SCREEN_SHADOW.value


def require_inherited_gate_disposition(
    use: str,
    expected: InheritedGateDisposition,
) -> InheritedGateDisposition:
    """Bind an actual call site to its reviewed disposition or fail closed."""
    try:
        actual = INHERITED_US_GATE_DISPOSITIONS[use]
    except KeyError as exc:
        raise KeyError(f"unclassified inherited US gate use: {use}") from exc
    if actual is not expected:
        raise ValueError(
            f"inherited US gate use {use} is {actual.value}; "
            f"expected {expected.value}"
        )
    return actual


def rank_residual_calls(
    calls: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, float | None]]:
    """Rank only the exact incumbent Canada call population by existing edge_z.

    edge_z is the sector-neutral residual-momentum z already stamped by the
    Branch-B board/watch owner.  Missing/non-finite values remain null; they are
    not rewritten to zero.  score_conservative stays null because C7 did not
    preregister or validate a conservative haircut for this family.
    """
    out: dict[str, dict[str, float | None]] = {}
    for call in calls or ():
        if not isinstance(call, Mapping):
            continue
        raw_ticker = call.get("ticker")
        if raw_ticker in (None, ""):
            continue
        ticker = str(raw_ticker)
        if ticker in out:
            continue
        score: float | None = None
        try:
            candidate = float(call.get("edge_z"))
        except (TypeError, ValueError):
            candidate = float("nan")
        if math.isfinite(candidate):
            score = candidate
        out[ticker] = {
            "score_raw": score,
            "score_conservative": None,
        }
    return out
