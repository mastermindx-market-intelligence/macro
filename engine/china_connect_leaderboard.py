"""Read archived most-active Connect disclosures; no render-time HTTP or fake net flow.

Rows stay VENUE-SPECIFIC. A stock missing from one venue's top ten is unknown,
not zero, so cross-venue net buying is never silently invented by aggregation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import re
from zoneinfo import ZoneInfo

import pandas as pd

from engine.china_macro_evidence import finite

VENUES = {"001": ("northbound", "Shanghai", "CNY"), "003": ("northbound", "Shenzhen", "CNY"),
          "002": ("southbound", "Shanghai", "HKD"), "004": ("southbound", "Shenzhen", "HKD")}


def normalize(raw: dict[str, list], as_of: date) -> dict:
    out = {"date": None, "northbound_date": None, "southbound_date": None,
           "northbound_turnover": [], "southbound_buy": [], "southbound_sell": [],
           "warnings": [], "status": "unavailable", "scope": "venue_specific_disclosed_top10_not_full_universe",
           "source": "https://data.eastmoney.com/hsgt/hsgtV2.html", "venues": {}}
    directional = {"northbound": [], "southbound": []}
    for leg, (direction, venue, currency) in VENUES.items():
        rows = raw.get(leg) or []
        good = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            d = str(r.get("TRADE_DATE", ""))[:10]
            try:
                stamp = date.fromisoformat(d)
            except ValueError:
                continue
            if stamp > as_of or str(r.get("MUTUAL_TYPE", leg)) != leg:
                continue
            code = str(r.get("SECURITY_CODE", ""))
            if not re.fullmatch(r"\d{5,6}", code):
                continue
            good.append((d, r))
        latest = max((d for d, _ in good), default=None)
        selected = [r for d, r in good if d == latest]
        # Duplicate rows in the same venue are an integrity failure, not volume.
        codes = [str(r["SECURITY_CODE"]) for r in selected]
        if len(codes) != len(set(codes)):
            out["warnings"].append(f"{direction}/{venue}: duplicate security rows withheld")
            selected = []
        out["venues"][leg] = {"date": latest, "rows": len(selected), "currency": currency,
                               "status": "recent" if latest and (as_of-date.fromisoformat(latest)).days <= 7 and selected else "aged_or_unavailable"}
        if not selected:
            out["warnings"].append(f"{direction}/{venue}: snapshot unavailable")
        for r in selected:
            key = "turnover" if direction == "northbound" else "net"
            amount = finite(r.get("DEAL_AMT" if direction == "northbound" else "NET_BUY_AMT"))
            if amount is None or key == "turnover" and amount < 0:
                continue
            name = r.get("SECURITY_NAME") if isinstance(r.get("SECURITY_NAME"), str) else None
            directional[direction].append({"ticker": str(r["SECURITY_CODE"]), "name": name, "name_zh": name,
                "venue": venue, "venue_code": leg, "currency": currency, "reference_date": latest,
                "chg": finite(r.get("CHANGE_RATE")), key: amount/1e8,
                "age_days": (as_of-date.fromisoformat(latest)).days})
    for direction, rows in directional.items():
        dates = {r["reference_date"] for r in rows}
        if len(dates) == 1:
            out[direction+"_date"] = next(iter(dates))
        elif len(dates) > 1:
            out["warnings"].append(f"{direction}: mixed venue dates; separate rows, no combined ranking")
            # Do not rank one stale route against another route's current prints.
            newest = max(dates)
            directional[direction] = [r for r in rows if r["reference_date"] == newest]
            out[direction+"_date"] = newest
    nb, sb = directional["northbound"], directional["southbound"]
    out["northbound_turnover"] = sorted(nb, key=lambda r: -r["turnover"])[:10]
    out["southbound_buy"] = sorted([r for r in sb if r["net"] > 0], key=lambda r: -r["net"])[:6]
    out["southbound_sell"] = sorted([r for r in sb if r["net"] < 0], key=lambda r: r["net"])[:6]
    all_dates = {r["reference_date"] for rows in directional.values() for r in rows}
    out["date"] = next(iter(all_dates)) if len(all_dates) == 1 else None
    if len(all_dates) > 1:
        out["warnings"].append("Northbound and southbound use different reference dates")
    if nb or sb:
        out["status"] = "partial" if out["warnings"] else "recent" if all(r["age_days"]<=7 for r in nb+sb) else "aged"
    return out


def build_leaderboard(read=None, as_of: date | None = None) -> dict:
    if read is None:
        from lib import store
        read = store.read
    as_of = as_of or datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai")).date()
    raw = {}
    errors = []
    for leg in VENUES:
        try:
            df = read("china_connect", "top_active_" + leg)
            if df is None or df.empty or "rows_json" not in df:
                continue
            x = df.copy()
            x.index = pd.to_datetime(x.index, errors="coerce")
            if x.index.isna().any() or x.index.has_duplicates:
                raise ValueError("invalid_or_duplicate_cache_dates")
            if x.index.tz is not None:
                x.index = x.index.tz_convert("Asia/Shanghai").tz_localize(None)
            x = x.sort_index().loc[lambda d: d.index.normalize() <= pd.Timestamp(as_of)]
            if x.empty:
                continue
            rows = json.loads(x.iloc[-1]["rows_json"])
            if not isinstance(rows, list):
                raise ValueError("rows_json_is_not_a_list")
            cache_date = x.index[-1].date().isoformat()
            if any(not isinstance(r, dict) or str(r.get("TRADE_DATE", ""))[:10] != cache_date for r in rows):
                raise ValueError("cache_index_does_not_match_disclosed_date")
            raw[leg] = rows
        except Exception as e:  # one unreadable venue must not erase the other disclosures
            errors.append(f"{leg}: {type(e).__name__}")
    result = normalize(raw, as_of)
    result["cache_errors"] = errors
    result["transport"] = "canonical_store_no_render_network"
    return result
