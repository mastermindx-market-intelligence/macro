"""Hong Kong thematic baskets — the HK analogue of engine.baskets_china.

Loads the HK data plane and delegates the equal-weight/perf compute to
engine.baskets_region: member closes from the hk_search deep cache (the HSI/HSCEI
universe, names like 0700.HK Tencent / 9988.HK Alibaba), benchmarked to the Hang Seng
Index (HSI). Member display name = the English name carried in membership.json. The only
listed sector ETF available for a cross-check is the HS TECH ETF (3033.HK).

Additive — any failure returns None and the page is skipped.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from engine.baskets_region import compute_region_baskets
from lib import config, store

log = logging.getLogger(__name__)

BENCHMARK_DEFAULT = "_HSI"   # Hang Seng Index
SEARCH_START = "2021-06-15"  # trim the 40y deep cache to the ~5y window the other markets use

#: What the HK series actually is. The membership file's own construction line says the
#: baskets are "rebalanced monthly"; engine.baskets._ew_level instead takes the daily
#: arithmetic mean of the members active on each date and compounds it. This is the
#: construction the page must show.
CONSTRUCTION = (
    "Daily arithmetic mean of available active-member returns, compounded; "
    "membership follows the supplied added/removed dates."
)


def _membership() -> dict | None:
    p = config.data_dir() / "baskets_hk" / "membership.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        log.warning("hk baskets membership unreadable: %s", e)
        return None


def _closes() -> pd.DataFrame | None:
    """Wide [Date × ticker] adjusted closes for the HK search universe (hk_search deep cache)."""
    p = config.data_dir() / "hk_search" / "closes_deep.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        df.index = pd.DatetimeIndex(df.index)
        df = df.sort_index()
        return df.loc[df.index >= pd.Timestamp(SEARCH_START)]
    except Exception as e:  # noqa: BLE001
        log.warning("hk_search closes unreadable: %s", e)
        return None


def compute_hk_baskets() -> dict | None:
    """Load the HK data plane (hk_search closes + HSI benchmark + HS-TECH proxy) and delegate
    the compute to engine.baskets_region. The loaders stay here so the tests can patch them."""
    mem = _membership()
    if not mem or not mem.get("baskets"):
        return None
    closes = _closes()
    bench = store.read("hk", mem.get("benchmark", BENCHMARK_DEFAULT))
    out = compute_region_baskets(closes, mem, bench,
                                 lambda s: store.read("hk", s), name_key="name")
    if not out:
        return None
    # The membership file's construction line says "rebalanced monthly"; the series is not
    # that — engine.baskets._ew_level averages the active members' daily returns and
    # compounds them. Restate the construction in the OUTPUT copy only: the membership
    # dict, the rosters and every numeric field are left exactly as computed.
    out = dict(out)
    out["construction"] = CONSTRUCTION
    return out


def member_closes_getter(closes: pd.DataFrame | None):
    """Return a callable(basket_dict) -> wide [Date × member-ticker] closes for the
    sector-ignition layer (engine.sector_ignition). Read-path only; None-safe."""
    def _get(b: dict) -> pd.DataFrame | None:
        if closes is None or closes.empty:
            return None
        tickers = [m.get("ticker") or m.get("symbol") for m in (b.get("members") or [])
                   if (m.get("ticker") or m.get("symbol"))]
        present = [t for t in tickers if t in closes.columns]
        if len(present) < 3:
            return None
        return closes[present]
    return _get
