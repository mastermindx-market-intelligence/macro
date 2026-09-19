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
from typing import Any

RESIDUAL_MOMENTUM_FAMILY = "ca_residual_momentum"
RESIDUAL_MOMENTUM_STATUS = "ACCRUING"
RESIDUAL_MOMENTUM_AUTHORITY = "name_intelligence_shadow"
RESIDUAL_MOMENTUM_DEFINITION = "ca_residual_momentum_rank_v1"

C1_OIL_STATUS = "ACCRUING"
C1_OIL_AUTHORITY = "sector_context_only"

# Masterplan section 11.3: the inherited US anticipation calibration is not a
# Canada-validated authority component.  It may remain as display/profile
# context while the Canada-specific measurement accrues, but it cannot become
# a binding input to a new Canada selection/rank/entry definition.
ANTICIPATION_US_GATE_DISPOSITION = "SCREEN_SHADOW"


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
