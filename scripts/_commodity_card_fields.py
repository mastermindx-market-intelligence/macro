"""Display fields for the commodity active-strategy grid cards (no I/O, no pandas)."""
from __future__ import annotations

_HALVES = {
    (True, True): ("Split-half: CAGR ahead of holding in both halves",
                   "分段检验：前后两段年化均高于持有"),
    (True, False): ("Split-half: CAGR ahead of holding in the first half only",
                    "分段检验：仅前半段年化高于持有"),
    (False, True): ("Split-half: CAGR ahead of holding in the second half only",
                    "分段检验：仅后半段年化高于持有"),
    (False, False): ("Split-half: CAGR not ahead of holding in either half",
                     "分段检验：两段年化均未高于持有"),
}


def card_fields(sc: dict, oos: dict | None) -> dict:
    """Return the grid fields for one active card from its scorecard and split-half record."""
    lev = (sc or {}).get("avg_leverage")
    num = isinstance(lev, (int, float)) and not isinstance(lev, bool)
    out = {"income": None, "avg_lev": lev if num else None, "oos_en": None, "oos_zh": None}
    first = (oos or {}).get("first")
    second = (oos or {}).get("second")
    if isinstance(first, dict) and isinstance(second, dict):
        key = (bool(first.get("beats_cagr")), bool(second.get("beats_cagr")))
        out["oos_en"], out["oos_zh"] = _HALVES[key]
    return out
