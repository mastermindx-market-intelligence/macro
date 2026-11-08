"""Literal original owner at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
import pandas as pd
from lib import config
_BREADTH_DIR = {"us": "breadth", "china": "china_breadth", "hk": "hk_breadth", "canada": "canada_breadth", "intl": "intl_breadth"}

def market_concentration(region: str = "us") -> dict:
    """Broad-market narrowness from the region's breadth tape (the user's 'market is narrow now').

    Daily + 3-day + weekly + monthly advance-decline ratio, % above 50/200d, new-hi/lo, and a
    broad/narrowing/narrow verdict. Read-only over data/<region>_breadth/breadth.parquet; {} on
    miss (the section then hides)."""
    try:
        b = pd.read_parquet(config.data_dir() / _BREADTH_DIR.get(region, "breadth") / "breadth.parquet")
    except Exception:  # noqa: BLE001
        return {}
    if b.empty:
        return {}
    last = b.iloc[-1]
    def f(c):
        try:
            return float(last[c])
        except Exception:  # noqa: BLE001
            return None
    adv, dec = f("adv"), f("dec")
    # guard dec>0 explicitly — a falsy-but-negative dec would pass `and dec` and yield a
    # nonsensical negative advance/decline ratio.
    ad = round(adv / dec, 2) if (adv is not None and dec is not None and dec > 0) else None
    out = {"adv": int(adv) if adv is not None else None,
           "dec": int(dec) if dec is not None else None, "ad_ratio": ad,
           "pct_above_50": round(f("pct_above_50"), 1) if f("pct_above_50") is not None else None,
           "pct_above_200": round(f("pct_above_200"), 1) if f("pct_above_200") is not None else None,
           "nh": int(f("nh")) if f("nh") is not None else None,
           "nl": int(f("nl")) if f("nl") is not None else None,
           "directional": False}
    for lbl, n in (("ad_3d", 3), ("ad_w", 5), ("ad_m", 21)):
        seg = b.iloc[-n:]
        sa, sd = seg["adv"].sum(), seg["dec"].sum()
        out[lbl] = round(float(sa / sd), 2) if sd else None
    p50 = out["pct_above_50"]
    if ad is not None and p50 is not None:
        if ad < 0.95 and p50 < 45:
            out["verdict"], out["verdict_zh"] = "narrow", "狭窄"
        elif ad > 1.3 and p50 > 58:
            out["verdict"], out["verdict_zh"] = "broad", "广泛"
        else:
            out["verdict"], out["verdict_zh"] = "mixed", "中性"
    return out
