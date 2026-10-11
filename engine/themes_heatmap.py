"""Finviz *themes* treemap — pure compute layer.

Builds the JSON contract consumed by ``site/sector_heatmap.html`` (the themes
map-type of the shared ``heatmap.js`` renderer): the Finviz narrative-basket
treemap rendered **Theme → Subsector tile**, each tile coloured by the
subsector's % move over the selected timeframe, with the member tickers (and
their own moves) surfaced on hover — exactly the themes map, in our theme.

Contract mirrors ``engine/sp500_heatmap.py`` so the same renderer draws it; the
only differences are ``map_type="themes"`` (two levels: theme → subsector-leaf,
no third stock level) and that each tile is a *subsector* carrying a ``members``
list rather than a single stock.

Pure: takes already-loaded dicts (the committed Finviz snapshot) and returns a
JSON-serialisable dict. All network/disk I/O lives in
``scripts/fetch_finviz_themes.py`` (the only networked piece) and
``scripts/build_themes_heatmap.py`` (the offline build wrapper).
"""
from __future__ import annotations

from typing import Mapping, Sequence
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re

from engine import theme_repricing_context as trc

# Eight daily-group timeframes, same keys/labels as the sp500 heatmap so the
# renderer's tabs/legend/strip are identical. Finviz serves all eight, so every
# one is ``available``.
TIMEFRAMES: list[dict] = [
    {"key": "1D",  "en": "1 day",         "zh": "1天"},
    {"key": "1W",  "en": "1 week",        "zh": "1周"},
    {"key": "MTD", "en": "Month to date", "zh": "本月至今"},
    {"key": "1M",  "en": "1 month",       "zh": "1月"},
    {"key": "3M",  "en": "3 month",       "zh": "3月"},
    {"key": "6M",  "en": "6 month",       "zh": "6月"},
    {"key": "YTD", "en": "Year to date",  "zh": "年初至今"},
    {"key": "1Y",  "en": "1 year",        "zh": "1年"},
]
DEFAULT_TIMEFRAME = "1D"

# Theme (top-level group) → Chinese label. Theme names are the "sector" level of
# the contract, which the renderer shows bilingually; subsector + member labels
# stay English, matching the sp500 map's sub-industry convention.
THEME_ZH: dict[str, str] = {
    "Artificial Intelligence": "人工智能",
    "Cloud Computing": "云计算",
    "Semiconductors": "半导体",
    "Cybersecurity": "网络安全",
    "Software": "软件",
    "Hardware": "硬件",
    "Quantum Computing": "量子计算",
    "Virtual & Augmented Reality": "虚拟与增强现实",
    "Biometrics": "生物识别",
    "Big Data": "大数据",
    "Electric Vehicles": "电动汽车",
    "Industrial Automation": "工业自动化",
    "Defense & Aerospace": "国防与航天",
    "Transportation & Logistics": "运输与物流",
    "Space Tech": "太空科技",
    "Robotics": "机器人",
    "Telecommunications": "电信",
    "Nanotechnology": "纳米技术",
    "Internet of Things": "物联网",
    "Autonomous Systems": "自动驾驶系统",
    "E-commerce": "电子商务",
    "Social Media": "社交媒体",
    "Digital Entertainment": "数字娱乐",
    "Real Estate & REITs": "房地产与REITs",
    "Consumer Goods": "消费品",
    "Smart Home": "智能家居",
    "Wearables": "可穿戴设备",
    "Education Technology": "教育科技",
    "Energy Renewable": "可再生能源",
    "Energy Traditional": "传统能源",
    "Commodities Energy": "能源商品",
    "Commodities Metals": "金属商品",
    "Commodities Agriculture": "农业商品",
    "Agriculture & FoodTech": "农业与食品科技",
    "Environmental Sustainability": "环境可持续",
    "Healthcare & Biotech": "医疗与生物科技",
    "Aging Population & Longevity": "老龄化与长寿",
    "Healthy Food & Nutrition": "健康食品与营养",
    "FinTech": "金融科技",
    "Crypto & Blockchain": "加密与区块链",
}


def _input_roster(tree):
    """Account from the input, including identities the legacy renderer skips."""
    parents, groups, rows, members, reasons = [], [], [], set(), set()
    appearances = 0
    if not tree:
        reasons.add("empty_tree")
    for theme in tree:
        parent = theme.get("theme") or theme.get("key")
        if not isinstance(parent, str) or not parent.strip() or parent != parent.strip():
            reasons.add("invalid_theme_identity")
        parents.append(str(parent or ""))
        if not theme.get("subsectors"):
            reasons.add("empty_theme")
        for sub in theme.get("subsectors", []):
            key = sub.get("key")
            if not isinstance(key, str) or not key.strip() or key != key.strip():
                reasons.add("invalid_subtheme_identity")
            key = str(key or "")
            groups.append((str(parent or ""), key))
            raw_roster = sub.get("members")
            if not isinstance(raw_roster, list):
                reasons.add("invalid_member_collection")
            roster = raw_roster or []
            if not roster:
                reasons.add("empty_subtheme")
            appearances += len(roster)
            seen = set()
            for member in roster:
                if not isinstance(member, str) or not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", member):
                    reasons.add("invalid_member_identity")
                member = str(member)
                if member in seen:
                    reasons.add("duplicate_member")
                seen.add(member)
                members.add(member)
                rows.append((str(parent or ""), key, member))
    if len(set(parents)) != len(parents):
        reasons.add("duplicate_theme")
    if len({key for _, key in groups}) != len(groups):
        reasons.add("duplicate_subtheme")
    counts = dict(themes=len(parents), subthemes=len(groups), appearances=appearances,
                  distinct_tickers=len(members))
    return counts, parents, groups, rows, members, reasons


def _instant(value, *, generated=False):
    if not isinstance(value, str):
        raise ValueError("clock_not_string")
    if generated and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value):
        value = value.replace(" ", "T") + "+00:00"
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("clock_timezone_missing")
    return result.astimezone(timezone.utc)


def qualify_membership_receipt(tree, receipt, generated_utc):
    """Bind a promoted snapshot, never infer current identity/correction acceptance."""
    unknown = {"status": "unknown", "reason": "receipt_unavailable", "asof": None,
               "refreshed_at_utc": None, "parser_version": None}
    if not isinstance(receipt, Mapping):
        return unknown
    counts, *_, reasons = _input_roster(tree)
    expected_hash = hashlib.sha256(json.dumps(tree, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    pairs = {"themes": "themes", "subthemes": "subthemes",
             "appearances": "memberships", "distinct_tickers": "unique_tickers"}
    declared = receipt.get("counts")
    if (reasons or receipt.get("parser_version") != "finviz_tree_refresh.v1"
            or receipt.get("promoted") is not True or receipt.get("mode") != "refresh"
            or receipt.get("error") is not None or receipt.get("refusal_reasons") != []
            or receipt.get("new_tree_sha256") != expected_hash
            or not isinstance(declared, Mapping)
            or any(type(declared.get(target)) is not int or declared[target] != counts[key]
                   for key, target in pairs.items())):
        return {**unknown, "reason": "receipt_identity_or_promotion_mismatch"}
    try:
        asof = receipt["asof"]
        day = date.fromisoformat(asof)
        observed = _instant(receipt["refreshed_at_utc"])
        ceiling = _instant(generated_utc, generated=True)
        if day.isoformat() != asof or day > observed.date() or observed > ceiling:
            raise ValueError("receipt_clock_outside_context")
    except (KeyError, ValueError, TypeError, OverflowError):
        return {**unknown, "reason": "receipt_clock_unqualified"}
    return {"status": "bound", "reason": None, "asof": asof,
            "refreshed_at_utc": receipt["refreshed_at_utc"],
            "parser_version": receipt["parser_version"]}


def _membership_manifest(tree, sectors, tiles, subsector_perf, member_perf, receipt, generated_utc):
    counts, parents, groups, rows, members, reasons = _input_roster(tree)
    emitted_groups = [(t["sector"], t["t"]) for t in tiles]
    emitted_rows = [(t["sector"], t["t"], m["t"]) for t in tiles for m in t["members"]]
    if (Counter(parents) != Counter(s["key"] for s in sectors)
            or Counter(groups) != Counter(emitted_groups) or Counter(rows) != Counter(emitted_rows)):
        reasons.add("input_output_population_mismatch")
    def measured(mapping, key, tf):
        row = mapping.get(key)
        value = row.get(tf) if isinstance(row, Mapping) else None
        try:
            return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            return False
    coverage = {tf["key"]: {
        "measured_members": sum(measured(member_perf, m, tf["key"]) for m in members),
        "total_members": len(members),
        "measured_groups": sum(measured(subsector_perf, k, tf["key"]) for _, k in groups),
        "total_groups": len(groups),
    } for tf in TIMEFRAMES}
    membership = qualify_membership_receipt(tree, receipt, generated_utc)
    return {"schema": "finviz.membership_manifest.v1", "counts": counts,
            "tree_sha256": hashlib.sha256(json.dumps(tree, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "reconciliation": {"status": "invalid" if reasons else "conserved", "reasons": sorted(reasons)},
            "coverage": coverage,
            "unpriced_members": sum(not any(measured(member_perf, m, tf["key"]) for tf in TIMEFRAMES) for m in members),
            "unresolved_identity_count": None, "source_declared_partial_groups": None,
            "source_declared_missing_groups": None, "unknown_reason": "not_provided_by_source",
            "membership": membership,
            "corrections": {"status": "snapshot_promoted" if membership["status"] == "bound" else "unknown",
                            "scope": "bound_snapshot_only", "current_proposal_adjudication": None}}


def build_themes_heatmap(
    tree: Sequence[Mapping],
    subsector_perf: Mapping[str, Mapping[str, float]],
    member_perf: Mapping[str, Mapping[str, float]] | None = None,
    *,
    generated_utc: str | None = None,
    asof: str | None = None,
    source: str = "finviz-themes",
    membership_receipt: Mapping | None = None,
) -> dict:
    """Assemble the themes heatmap payload.

    Parameters
    ----------
    tree           : ``[{theme, key, subsectors:[{key, name, description,
                     members:[ticker,...]}]}]`` — the committed structure.
    subsector_perf : ``{subsector_key: {tf: pct}}`` — colours each tile.
    member_perf    : ``{ticker: {tf: pct}}`` — colours each member row on hover.
    """
    member_perf = member_perf or {}
    repricing = trc.build_context(
        tree, subsector_perf, member_perf, asof=asof or "", source=source,
    )
    repricing_by_key = {row["key"]: row for row in repricing["subthemes"]}
    repricing_summary = {k: v for k, v in repricing.items() if k != "subthemes"}
    tiles: list[dict] = []
    sectors: list[dict] = []
    seen_theme: set[str] = set()

    for theme in tree:
        tname = str(theme.get("theme") or theme.get("key") or "").strip()
        if not tname:
            continue
        if tname not in seen_theme:
            seen_theme.add(tname)
            sectors.append({"key": tname, "en": tname, "zh": THEME_ZH.get(tname, tname)})

        for sub in theme.get("subsectors", []):
            key = str(sub.get("key") or "").strip()
            name = str(sub.get("name") or key).strip()
            if not key:
                continue
            members = [str(m).strip() for m in (sub.get("members") or []) if str(m).strip()]
            sperf = {k: v for k, v in (subsector_perf.get(key) or {}).items() if v is not None}
            mem_rows = []
            for m in members:
                mp = {k: v for k, v in (member_perf.get(m) or {}).items() if v is not None}
                mem_rows.append({"t": m, "perf": mp})
            tiles.append({
                "t": key,
                "name": name,
                "sector": tname,
                "desc": str(sub.get("description") or "").strip(),
                # Size = member count (honest, dependency-free proxy; the map's
                # signal is colour, not area). Floor at 1 so empty baskets draw.
                "size": max(1, len(members)),
                "perf": sperf,
                "members": mem_rows,
                "repricing": repricing_by_key.get(key),
            })

    timeframes = [{**tf, "group": "daily", "available": True} for tf in TIMEFRAMES]
    uniq_members = {m["t"] for t in tiles for m in t["members"]}

    return {
        "map_type": "themes",
        "asof": asof or "",
        "generated_utc": generated_utc or "",
        "source": source,
        "delay_min": 15,
        "currency": "USD",
        "default_tf": DEFAULT_TIMEFRAME,
        "timeframes": timeframes,
        "sectors": sectors,
        "tiles": tiles,
        "n_tiles": len(tiles),
        "n_members": len(uniq_members),
        "size_basis": "count",
        "repricing": repricing_summary,


        "membership_manifest": _membership_manifest(tree, sectors, tiles, subsector_perf,
                                                     member_perf, membership_receipt, generated_utc),
    }
