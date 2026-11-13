"""Read-only recovery of legacy context; no canonical investment authority.

The historical alpha and RS formulae are NOT silently recomputed or relabeled.
The optional Top Picks blend uses the incumbent function on the available factor
legs; its separate insider overlay is not recovered here, so parity is unclaimed.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from engine.leadership_lab.measurement import finite_number, session_date
from engine.top_picks import TILT_LEGS, compute_scores


def _text(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) and value.strip() else fallback


def _rs(value: object) -> float | None:
    result = finite_number(value)
    return result if result is not None and 1 <= result <= 99 else None


def recover_snapshot(
    alpha: Mapping, factors: Mapping | None, baskets: Mapping | None, *,
    source_ref: str, reference_session: str, limit: int = 40,
    sort_by: str = "legacy_alpha",
) -> dict:
    """Recover an immutable-reference view without upgrading data to PIT truth.

    ``reference_session`` is explicit, supplied by an owner/caller; this function
    never infers a market session from wall time. Sorting is a research display
    preference over a preserved population, not a production candidate ranker.
    """
    if not isinstance(source_ref, str) or not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("source_ref must be an exact lowercase Git commit SHA")
    session_date(reference_session)
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("limit must be an integer from 1 to 200")
    if sort_by not in ("legacy_alpha", "legacy_rs"):
        raise ValueError("unknown descriptive sort")
    result = {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "status": "UNAVAILABLE", "source_ref": source_ref,
        "source_session": None, "reference_session": reference_session,
        "pit_qualification": "UNATTESTED_ROW_CLOCKS", "recovered_count": 0,
        "rows": [], "shortlist": [], "groups": [], "sort_by": sort_by,
        "shortlist_limit": limit, "forecast_probability": None,
        "authority": {"prophet_rank": False, "entry": False, "sizing": False,
                      "trade": False, "production_publish": False},
        "gaps": ["ROW_CLOCKS_UNATTESTED", "PRICE_ADJUSTMENTS_UNATTESTED",
                 "LEGACY_FORMULA_NOT_REVALIDATED", "CALIBRATION_NOT_CONNECTED",
                 "ENTRY_OWNER_NOT_CONNECTED", "EARNINGS_EVIDENCE_NOT_CONNECTED",
                 "INSIDER_OVERLAY_NOT_JOINED"],
        "sources": {},
    }
    try:
        source_session = session_date(alpha.get("as_of"))
        per_ticker = alpha.get("per_ticker")
        if not isinstance(per_ticker, Mapping) or not per_ticker:
            raise ValueError("missing per_ticker")
    except (AttributeError, TypeError, ValueError):
        result["gaps"].append("INVALID_ALPHA_SOURCE")
        return result
    result["source_session"] = source_session
    result["sources"]["alpha"] = {"source_session": source_session, "included": True}
    if source_session > reference_session:
        result["gaps"].append("FUTURE_ALPHA_SOURCE")
        result["sources"]["alpha"]["included"] = False
        return result
    result["status"] = ("RECOVERED_SNAPSHOT" if source_session == reference_session
                        else "STALE_RECOVERED_SNAPSHOT")
    matched = {}
    for label, payload in (("factors", factors), ("baskets", baskets)):
        observed = payload.get("as_of") if isinstance(payload, Mapping) else None
        good = observed == source_session
        result["sources"][label] = {"source_session": _text(observed) or None, "included": good}
        matched[label] = good
        if not good:
            result["gaps"].append(f"{label.upper()}_DATE_MISMATCH")

    factor_by_ticker = {}
    duplicates = set()
    table = factors.get("table") if matched["factors"] else None
    if isinstance(table, list):
        for row in table:
            if not isinstance(row, Mapping):
                continue
            ticker = _text(row.get("ticker"))
            if not ticker:
                continue
            if ticker in factor_by_ticker:
                duplicates.add(ticker)
            factor_by_ticker[ticker] = row
    else:
        result["gaps"].append("FACTORS_TABLE_UNAVAILABLE")
    for ticker in duplicates:
        factor_by_ticker.pop(ticker, None)
    if duplicates:
        result["gaps"].append("DUPLICATE_FACTOR_IDENTITIES_EXCLUDED")

    scoring_rows = []
    for ticker, legacy in per_ticker.items():
        if not isinstance(ticker, str) or not ticker or not isinstance(legacy, Mapping):
            result["gaps"].append("MALFORMED_ALPHA_ROW")
            continue
        factor = factor_by_ticker.get(ticker, {})
        alpha_value = finite_number(legacy.get("alpha"))
        legs = {leg: finite_number(factor.get(leg)) for leg in TILT_LEGS}
        n_legs = sum(v is not None for v in legs.values())
        row = {
            "ticker": ticker, "name": _text(factor.get("name"), ticker),
            "sector": _text(factor.get("sector"), "Unmapped"),
            "legacy_alpha": alpha_value, "legacy_rs": _rs(legacy.get("rs")),
            "legacy_rs3m": _rs(legacy.get("rs3m")),
            "legacy_rs6m": _rs(legacy.get("rs6m")),
            "legacy_rs12m": _rs(legacy.get("rs12m")),
            "legacy_entry_context": (legacy.get("entry") if legacy.get("entry") in
                                     ("extended", "pullback", "intact", "laggard", "neutral") else None),
            "legacy_top_score": None, "available_factor_legs": n_legs,
            "blend_parity": "UNCLAIMED_INSIDER_OVERLAY_ABSENT", "themes": [],
            "entry_status": "NOT_CONNECTED", "research_stance": "Investigate",
        }
        result["rows"].append(row)
        if alpha_value is not None and factor:
            scoring_rows.append({"ticker": ticker, "sector": row["sector"],
                                 "alpha": alpha_value, **legs})
    scores = compute_scores(scoring_rows) if scoring_rows else {}
    for row in result["rows"]:
        # Fewer than two legs is missing corroboration, not a known-neutral view.
        if row["available_factor_legs"] >= 2:
            row["legacy_top_score"] = finite_number(scores.get(row["ticker"], {}).get("top_score"))
    by_ticker = {row["ticker"]: row for row in result["rows"]}
    group_rows = baskets.get("baskets") if matched["baskets"] else None
    if isinstance(group_rows, list):
        ids = [group.get("id") for group in group_rows if isinstance(group, Mapping)]
        for group in group_rows:
            if not isinstance(group, Mapping):
                continue
            group_id = _text(group.get("id"))
            if not group_id or ids.count(group_id) != 1:
                result["gaps"].append("INVALID_OR_DUPLICATE_GROUP_ID")
                continue
            raw_members = group.get("members")
            if not isinstance(raw_members, list):
                continue
            members = sorted({_text(m.get("symbol")) for m in raw_members if isinstance(m, Mapping)} - {""})
            unknown_members = sum(not isinstance(m, Mapping) or not _text(m.get("symbol")) for m in raw_members)
            member_count = len(members) + unknown_members
            if not member_count:
                continue
            name = _text(group.get("name"), group_id)
            observed = [t for t in members if t in by_ticker and by_ticker[t]["legacy_alpha"] is not None]
            for ticker in members:
                if ticker in by_ticker:
                    by_ticker[ticker]["themes"].append({"id": group_id, "name": name})
            result["groups"].append({
                "id": group_id, "name": name, "category": _text(group.get("category"), "Other"),
                "member_count": member_count, "unknown_member_count": unknown_members,
                "observed_count": len(observed), "coverage": len(observed) / member_count,
                "members": members,
                "independence_status": "NOT_QUALIFIED", "historical_membership_qualified": False,
            })
    for row in result["rows"]:
        row["themes"].sort(key=lambda x: x["id"])
    result["rows"].sort(key=lambda r: (r[sort_by] is None, -(r[sort_by] or 0), r["ticker"]))
    result["groups"].sort(key=lambda g: (g["category"], g["name"], g["id"]))
    result["recovered_count"] = len(result["rows"])
    result["shortlist"] = [dict(row) for row in result["rows"] if row[sort_by] is not None][:limit]
    result["gaps"] = sorted(set(result["gaps"]))
    return result
