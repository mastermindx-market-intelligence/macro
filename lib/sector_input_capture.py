"""Current Sector price-pair binding through the existing private read owners.

This is the price dependency of the full capture adapter, not a complete Sector
input set. Genuine member OHLCV, holdings, context and histories remain required.
No provider, bootstrap, clock acquisition or publication occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lib.yahoo_generation_contract import (
    VerifiedYahooGeneration, _instant, read_verified_yahoo_cohort,
)
from lib.breadth_member_generation_contract import (
    VerifiedBreadthMemberGeneration, read_verified_breadth_member_inputs,
)


@dataclass(frozen=True)
class SectorPriceCaptures:
    yahoo: VerifiedYahooGeneration
    breadth: VerifiedBreadthMemberGeneration
    captured_at: datetime

    def input_lineage(self) -> dict:
        """Describe these captured bytes; never resolve a pointer a second time."""
        return {
            "yahoo": self.yahoo.prior_identity(captured_at=self.captured_at),
            "breadth_members": self.breadth.prior_identity(captured_at=self.captured_at),
        }


def read_sector_price_captures(*, generations_root: Path, now: datetime) -> SectorPriceCaptures:
    """Capture both current selections once and require their exact dependency.

    If Yahoo advanced before breadth, the existing breadth validator refuses the
    pair. It does not fall back to a retained dependency or reread either pointer.
    Existing direct readers retain their explicit historical-recovery semantics.
    """
    captured_at = _instant(now)
    yahoo = read_verified_yahoo_cohort(generations_root=generations_root,
        now=captured_at, require_current=True)
    breadth = read_verified_breadth_member_inputs(generations_root=generations_root,
        now=captured_at, yahoo=yahoo, require_current=True)
    return SectorPriceCaptures(yahoo, breadth, captured_at)


def read_sector_member_ohlcv_capture(*, prices: SectorPriceCaptures, generations_root: Path, now: datetime):
    """Bind genuine member candles to this price pair without resolving it again."""
    from lib.member_ohlcv_generation_contract import read_verified_member_ohlcv_inputs
    if not isinstance(prices, SectorPriceCaptures) or _instant(now) < _instant(prices.captured_at):
        raise ValueError("captured_sector_price_pair_required")
    return read_verified_member_ohlcv_inputs(generations_root=generations_root, now=_instant(now),
        breadth=prices.breadth, yahoo=prices.yahoo, require_current=True)
