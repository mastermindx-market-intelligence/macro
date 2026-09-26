"""Deterministic Canada theme-action projection for the stock dashboard.

This module is intentionally bounded: existing Canada basket/theme artifacts own
rotation, rank, leadership and membership; the canonical Prophet buy/watch board
owns stock selection. The projection performs only validation and deterministic
joins, and optional owner failures never abort the Canada build.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _canada_theme_action_map(setups: dict | None, site: Path) -> dict | None:
    """Project existing Canada theme action into the Canada Stocks journey.

    Authority remains with ``canadabasketdata/baskets.json``: ``theme_intel.act_now``
    owns theme action lanes; ``theme_intel.themes`` owns rank/leadership; ``baskets``
    owns membership. This helper performs only deterministic joins to the canonical
    Prophet board/watch populations and never scores, ranks, or originates an action.
    """
    path = site / "canadabasketdata" / "baskets.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001 -- optional projection, never fatal
        log.warning("canada theme action artifact unreadable (%s); skipping", exc)
        return None
    intel = payload.get("theme_intel") if isinstance(payload, dict) else None
    act = intel.get("act_now") if isinstance(intel, dict) else None
    themes = intel.get("themes") if isinstance(intel, dict) else None
    baskets = payload.get("baskets") if isinstance(payload, dict) else None
    if not isinstance(act, dict) or not isinstance(themes, list) or not isinstance(baskets, list):
        return None

    def native_id(row: object) -> str | None:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            return None
        value = row["id"].strip()
        return value or None

    def unique_rows(rows: list) -> tuple[dict[str, dict], set[str]]:
        indexed: dict[str, dict] = {}
        ambiguous: set[str] = set()
        for row in rows:
            rid = native_id(row)
            if rid is None or rid in ambiguous:
                continue
            if rid in indexed:
                indexed.pop(rid)
                ambiguous.add(rid)
                continue
            indexed[rid] = row
        return indexed, ambiguous

    theme_by, ambiguous_theme_ids = unique_rows(themes)
    basket_by, ambiguous_basket_ids = unique_rows(baskets)
    cats = payload.get("categories") if isinstance(payload.get("categories"), list) else []
    cats_zh = payload.get("categories_zh") if isinstance(payload.get("categories_zh"), list) else []
    cat_zh = {str(cat): cats_zh[i] for i, cat in enumerate(cats) if i < len(cats_zh)}

    def owner_tickers(key: str) -> set[str] | None:
        rows = (setups or {}).get(key)
        if not isinstance(rows, list):
            return None
        out: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("ticker"), str):
                return None
            ticker = row["ticker"].strip().upper()
            if not ticker or ticker in out:
                return None
            out.add(ticker)
        return out

    def clean_symbol(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        symbol = value.strip().upper()
        return symbol or None

    def member_symbol(member: object) -> str | None:
        if isinstance(member, str):
            return clean_symbol(member)
        if not isinstance(member, dict):
            return None
        for key in ("symbol", "ticker"):
            symbol = clean_symbol(member.get(key))
            if symbol is not None:
                return symbol
        return None

    def membership_for(tid: str) -> tuple[bool, set[str]]:
        if tid in ambiguous_theme_ids or tid in ambiguous_basket_ids:
            return False, set()
        if tid not in theme_by:
            return False, set()
        basket = basket_by.get(tid)
        raw_members = basket.get("members") if isinstance(basket, dict) else None
        if not isinstance(raw_members, list):
            return False, set()
        members: set[str] = set()
        for member in raw_members:
            symbol = member_symbol(member)
            if symbol is None:
                return False, set()
            members.add(symbol)
        return True, members

    board = owner_tickers("buy")
    watch = owner_tickers("watch")
    prophet = (board | watch) if board is not None and watch is not None else None
    membership_by: dict[str, tuple[bool, set[str]]] = {}
    distinct_members: set[str] = set()
    for tid in theme_by:
        known, members = membership_for(tid)
        membership_by[tid] = (known, members)
        if known:
            distinct_members.update(members)

    def optional_reason(row: dict, value_key: str, list_key: str) -> str | None:
        explicit = row.get(value_key)
        if explicit is not None:
            if not isinstance(explicit, str):
                return None
            explicit = explicit.strip()
            if explicit:
                return explicit
        reasons = row.get(list_key)
        if reasons is None:
            return None
        if not isinstance(reasons, list):
            return None
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            return None
        return "; ".join(reason.strip() for reason in reasons) or None

    def project(row: object) -> dict | None:
        tid = native_id(row)
        if tid is None or not isinstance(row, dict):
            return None
        join_ambiguous = tid in ambiguous_theme_ids or tid in ambiguous_basket_ids
        th = {} if join_ambiguous else theme_by.get(tid, {})
        basket = None if join_ambiguous else basket_by.get(tid)
        membership_known, members = membership_by.get(tid, (False, set()))
        leaders: list[str] = []
        leadership = th.get("leadership") if isinstance(th, dict) else None
        top = leadership.get("top") if isinstance(leadership, dict) else None
        if isinstance(top, list):
            for leader in top[:3]:
                if not isinstance(leader, dict):
                    continue
                for key in ("ticker", "symbol", "t"):
                    symbol = clean_symbol(leader.get(key))
                    if symbol is not None:
                        leaders.append(symbol)
                        break
        category = basket.get("category") if isinstance(basket, dict) else None
        return {
            "id": tid,
            "name": row.get("name") or th.get("name") or tid,
            "name_zh": row.get("name_zh") or th.get("name_zh") or row.get("name") or tid,
            "category": category,
            "category_zh": cat_zh.get(str(category)) if category is not None else None,
            "rank": th.get("rank"),
            "score": row.get("score"),
            "action": row.get("action"),
            "action_en": row.get("action_en") or row.get("action"),
            "action_zh": row.get("action_zh") or row.get("action_en") or row.get("action"),
            "label": row.get("label"),
            "reason_en": optional_reason(row, "reason_en", "reasons"),
            "reason_zh": optional_reason(row, "reason_zh", "reasons_zh"),
            "leaders": leaders,
            "membership_known": membership_known,
            "members": sorted(members) if membership_known else None,
            "n_members": len(members) if membership_known else None,
            "prophet_count": len(members & prophet) if membership_known and prophet is not None else None,
            "href": "baskets_canada.html#theme-" + tid,
        }

    lane_defs = (("buy", "buy_now"), ("add_on_pullback", "in_favour"),
                 ("conflicted", "watch"), ("reduce", "reduce"))
    lanes = {}
    for source_key, out_key in lane_defs:
        rows = act.get(source_key)
        if not isinstance(rows, list):
            return None
        lanes[out_key] = [item for item in (project(row) for row in rows) if item is not None]
    return {
        "as_of": intel.get("as_of") or payload.get("as_of"),
        "n_themes": len(theme_by),
        "n_distinct_members": len(distinct_members),
        "n_prophet_current": len(prophet) if prophet is not None else None,
        "lanes": lanes,
        "authority": "descriptive_rotation",
    }


def _safe_canada_theme_action_map(setups: dict | None, site: Path) -> dict | None:
    """Keep optional Canada theme projection failures out of the canonical build."""
    try:
        return _canada_theme_action_map(setups, site)
    except Exception as exc:  # noqa: BLE001 -- optional projection, never fatal
        log.warning("canada theme action projection failed (%s); skipping", exc)
        return None


__all__ = ["_canada_theme_action_map", "_safe_canada_theme_action_map"]
