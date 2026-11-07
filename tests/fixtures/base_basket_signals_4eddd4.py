"""Literal original signal decision from Macro4eddd4; tests provide acquisition."""
from __future__ import annotations
import logging
import pandas as pd
from engine import basket_index, basket_mtf, basket_tape
log = logging.getLogger(__name__)
_SIG_CACHE = {}
MIN_CANDLE_MEMBER_COVERAGE = 0.6
_REGION_MARKET = {"us": "US", "ca": "CA", "hk": "HK", "cn": "CN"}

def _basket_signals(members: list[dict], level: pd.Series | None = None,
                    region: str = "us", conv_map: dict | None = None,
                    *, use_cache: bool = True) -> dict:
    """Run MTF/tape on a consolidated member candle, with an all-region close-only fallback.

    The preferred path uses member OHLCV and can publish tape/flow. When that store cannot
    resolve a region, the already-computed equal-weight close level still supports the MTF
    engine's D/3D/W/M structure. The fallback is explicitly stamped and never fabricates
    volume, whale or flow fields. Cached by region/membership/as-of for detail-page reuse.

    `use_cache=False` bypasses the process-wide `_SIG_CACHE` for one call. The cache key
    carries the session date and the membership but NOT the price values, so two distinct
    snapshots that end on the same session would otherwise share one candle read. The
    explicit-input acquisition path sets it to False so distinct contexts stay isolated;
    the default keeps the incumbent behaviour for every existing caller.
    """
    level_last = None
    if level is not None and not level.dropna().empty:
        level_last = str(level.dropna().index[-1])
    key = (region, level_last, tuple(sorted(m.get("ticker", "") for m in members)))
    if use_cache and key in _SIG_CACHE:
        return _SIG_CACHE[key]
    out: dict = {}
    try:
        idx = basket_index.deep_calendar(members)
        if len(idx) >= 60:
            cand, meta = basket_index.consolidated_candle(members, idx, "equal", conv_map, pit=False)
            if cand is not None:
                n_total = int(meta.get("n_total") or len(members) or 0)
                n_live = int(meta.get("n_live") or 0)
                member_cov = n_live / n_total if n_total else 0.0
                meta["member_coverage_pct"] = round(member_cov, 3)
                if member_cov >= MIN_CANDLE_MEMBER_COVERAGE:
                    mtf = basket_mtf.basket_mtf(cand, _REGION_MARKET.get(region, "US"))
                    if mtf:
                        mtf["source"] = "member_ohlcv"
                    out = {"mtf": mtf,
                           "tape": basket_tape.basket_tape(cand, meta),
                           "meta": meta}
                else:
                    log.info("basket candle coverage %.0f%% below %.0f%% floor; "
                             "using full-basket close-only MTF",
                             member_cov * 100, MIN_CANDLE_MEMBER_COVERAGE * 100)
    except Exception as e:  # noqa: BLE001 — additive overlay
        log.warning("basket signals failed: %s", e)
        out = {}
    if not out.get("mtf") and level is not None:
        try:
            close = pd.to_numeric(level, errors="coerce").dropna()
            if len(close) >= 60:
                mtf = basket_mtf.basket_mtf(pd.DataFrame({"close": close}),
                                            _REGION_MARKET.get(region, "US"))
                if mtf:
                    mtf["source"] = "equal_weight_close"
                    out = {"mtf": mtf, "tape": None,
                           "meta": {"basis": "equal_weight_close",
                                    "flow_available": False, "n_bars": int(len(close))}}
        except Exception as e:  # noqa: BLE001 — additive overlay
            log.warning("basket close-only MTF fallback failed: %s", e)
    if use_cache:
        _SIG_CACHE[key] = out
    return out
