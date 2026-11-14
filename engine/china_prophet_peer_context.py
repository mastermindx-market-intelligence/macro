"""A-share peer participation for Prophet. Explanatory evidence and shadow cohorts only.

All observed returns are in percentage points. Compare two adjacent five-session
windows on one fixed set of peers, with the candidate removed from both. The
current bake captures the receipt; this is not an as-known historical backfiller.
"""
from __future__ import annotations

from datetime import date
import json
import logging

import numpy as np
import pandas as pd

from engine.flow_observatory.groups import COVERAGE_FLOOR_PCT, resolve_active_membership
from lib.cn_calendar import session_n_back

log = logging.getLogger(__name__)
VERSION = "cn_peer_context.v1"
MIN_PEERS = 5


def _read_json(path):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as exc:
        log.warning("China peer context: %s unavailable (%s)", path.name, exc)
        return {}


def load_sources(data_dir, site_dir, as_of):
    """Read independent sources once. An unavailable sector leg preserves themes."""
    try:
        membership = pd.read_parquet(data_dir / "china_sectors" / "membership.parquet")
        observed = pd.to_datetime(membership["collected_at"], errors="coerce")
        start = pd.to_datetime(membership["start_date"], errors="coerce")
        known = observed.le(pd.Timestamp(as_of)) & start.notna()
        sectors, _ = resolve_active_membership(membership.loc[known], as_of)
    except (OSError, ValueError, KeyError) as exc:
        log.warning("China peer context: industry membership unavailable (%s)", exc)
        sectors = {}
    groups = {("sector", str(k)): members for k, members in sectors.items()}
    curated = _read_json(data_dir / "baskets_china" / "membership.json")
    for key, basket in curated.get("baskets", {}).items():
        groups["theme", key] = [
            m["ticker"] for m in basket.get("members", [])
            if m.get("ticker") and m.get("added") and m["added"] <= as_of
            and (not m.get("removed") or m["removed"] > as_of)
        ]
    central = _read_json(site_dir / "chinasectordata" / "sector_central.json")
    return groups, central


def _price_features(closes, bench, as_of):
    day = date.fromisoformat(as_of)
    sessions = [session_n_back(day, n) for n in range(20, -1, -1)]
    if None in sessions or closes is None:
        return {}, None
    dates = pd.DatetimeIndex(sessions)

    def aligned(frame):
        frame = frame.reindex(dates)
        return frame.where(np.isfinite(frame) & (frame > 0))

    market_returns = None
    if bench is not None and pd.api.types.is_numeric_dtype(bench) and not pd.api.types.is_bool_dtype(bench):
        market = aligned(bench)
        if market.notna().all():
            market_returns = (100 * (market.iloc[-1] / market.iloc[-6] - 1),
                              100 * (market.iloc[-1] / market.iloc[0] - 1),
                              100 * (market.iloc[-6] / market.iloc[-11] - 1))
    p = aligned(closes.select_dtypes(include="number")).dropna(axis=1)
    features = pd.DataFrame({
        "r5": 100 * (p.iloc[-1] / p.iloc[-6] - 1),
        "prior5": 100 * (p.iloc[-6] / p.iloc[-11] - 1),
        "r20": 100 * (p.iloc[-1] / p.iloc[0] - 1),
        "new_low": p.iloc[-1] < p.iloc[:-1].min(),
    })
    return features.to_dict("index"), market_returns


def _stock_state(own):
    if own is None:
        return "unavailable"
    if own["new_low"] or (own["r5"] < 0 and own["r20"] < 0):
        return "falling"
    if own["r5"] > 0 and own["r20"] > 0:
        return "positive"
    return "mixed"


def _stance(own, peer5, peer20, prior_peer5, market, breadth, change):
    if own is None:
        return "stock_unavailable"
    if _stock_state(own) == "falling":
        return "stock_falling"
    if market is None:
        return "benchmark_unavailable"
    stock_leads = (own["r5"] > max(0, market[0], peer5)
                   and own["r20"] > max(0, market[1], peer20))
    broad = breadth > 50 and peer5 > max(0, market[0])
    if stock_leads and broad and peer20 > market[1]:
        return "group_leader"
    if (stock_leads and own["prior5"] > max(0, prior_peer5, market[2])
            and breadth < 50 and peer20 <= market[1]):
        return "isolated_leader"
    if broad and change > 0 and peer20 <= market[1] and prior_peer5 <= market[2]:
        return "emerging_rotation"
    if breadth < 50 and change < 0 and peer5 <= market[0]:
        return "peers_weakening"
    return "mixed"


def _interpretation(row):
    """Freeze hypotheses for paired evaluation. All overlapping lenses stay visible."""
    if row["stock_state"] == "unavailable":
        return "unavailable"
    if row["stock_state"] == "falling":
        return "falling_watch"
    sector = next((g for g in row["groups"] if g["kind"] == "sector"), None)
    comparable = [g for g in row["groups"] if g["state"] not in
                  {"insufficient_coverage", "stock_unavailable", "benchmark_unavailable"}]
    if not comparable:
        return "unavailable"
    states = {g["state"] for g in comparable}
    if sector is None or sector not in comparable:
        return "theme_only"
    if states == {"isolated_leader"} and len(comparable) == len(row["groups"]):
        return "isolated_leader"
    if "group_leader" in states and states <= {"group_leader", "emerging_rotation"}:
        if sector["state"] == "group_leader" and len(comparable) == len(row["groups"]):
            return "risk_off_leader" if row["market_tone"] == "off" else "group_leader"
    if "emerging_rotation" in states and states <= {"emerging_rotation", "mixed"}:
        return "rotation_watch"
    if states == {"peers_weakening"}:
        return "weak_peers"
    return "mixed"


def build_context(tickers, closes, bench, as_of, groups, central):
    features, market = _price_features(closes, bench, as_of)
    # Sector Central publishes after the stock build on asia-close. A known prior
    # session can supply dated context; a future or older reading cannot.
    previous = session_n_back(date.fromisoformat(as_of), 1)
    accepted_dates = {as_of, previous.isoformat()} if previous else {as_of}
    snapshot = central if central.get("as_of") in accepted_dates else {}
    backdrop = snapshot.get("market") or {}
    tone = (backdrop.get("tone") if backdrop.get("validated") is True
            and backdrop.get("any_stale") is False else None)
    names = {}
    for kind, collection, id_field in (("sector", "sectors", "shenwan_code"),
                                        ("theme", "baskets", "basket_id")):
        for item in snapshot.get(collection) or []:
            names[kind, str(item.get(id_field))] = item
    result = {}
    for ticker in tickers:
        own = features.get(ticker)
        result[ticker] = {
            "version": VERSION, "as_of": as_of, "market_tone": tone, "central_as_of": snapshot.get("as_of"), "groups": [],
            "stock_state": _stock_state(own),
            "stock_5d_pct": round(own["r5"], 3) if own else None,
            "stock_20d_pct": round(own["r20"], 3) if own else None,
            "stock_vs_csi300_20d_pp": round(own["r20"] - market[1], 3) if own and market else None,
        }
    for key, member_list in sorted(groups.items()):
        members = set(member_list)
        measured = {t: features[t] for t in members if t in features}
        sums = {k: sum(v[k] for v in measured.values()) for k in ("r5", "r20", "prior5")}
        adv = sum(v["r5"] > 0 for v in measured.values())
        prior_adv = sum(v["prior5"] > 0 for v in measured.values())
        info = names.get(key, {})
        for ticker in members.intersection(result):
            own = measured.get(ticker)
            total = len(members) - 1
            n = len(measured) - int(own is not None)
            entry = {"kind": key[0], "id": key[1], "name": info.get("name") or key[1],
                     "name_zh": info.get("name_zh"), "cycle": (info.get("cycle") or {}).get("phase"),
                     "index_lead": (info.get("momentum") or {}).get("lead"),
                     "observed": n, "total": total, "state": "insufficient_coverage"}
            result[ticker]["groups"].append(entry)
            if n < MIN_PEERS or 100 * n < COVERAGE_FLOOR_PCT * total:
                continue
            up = adv - int(own is not None and own["r5"] > 0)
            prior_up = prior_adv - int(own is not None and own["prior5"] > 0)
            breadth = 100 * up / n
            change = 100 * (up - prior_up) / n
            peer5 = (sums["r5"] - (own["r5"] if own else 0)) / n
            peer20 = (sums["r20"] - (own["r20"] if own else 0)) / n
            prior_peer5 = (sums["prior5"] - (own["prior5"] if own else 0)) / n
            entry.update(state=_stance(own, peer5, peer20, prior_peer5, market, breadth, change),
                         advancing=up, breadth_pct=round(breadth, 2),
                         breadth_change_5d_pp=round(change, 2),
                         peer_vs_csi300_5d_pp=round(peer5 - market[0], 3) if market else None,
                         peer_vs_csi300_20d_pp=round(peer20 - market[1], 3) if market else None,
                         stock_vs_peer_20d_pp=round(own["r20"] - peer20, 3) if own else None)
    for row in result.values():
        row["interpretation"] = _interpretation(row)
    return result
