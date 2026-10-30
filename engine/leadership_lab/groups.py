"""Descriptive group leadership projection over recovered Alpha/RS values.

This is presentation over existing measurements and peer-coverage receipts. It creates
no composite score, emerging-leader rule, probability, or decision authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from engine.leadership_lab.measurement import finite_number


_AUTHORITY = {
    "rank": False,
    "entry": False,
    "size": False,
    "execution": False,
    "trade": False,
}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _top(
    members: list[str], rows: Mapping[str, Mapping], field: str, *, limit: int = 5,
) -> list[dict]:
    values = []
    for ticker in members:
        row = rows.get(ticker)
        value = finite_number(row.get(field)) if isinstance(row, Mapping) else None
        if value is not None:
            values.append((ticker, value))
    values.sort(key=lambda item: (-item[1], item[0]))
    return [{"ticker": ticker, "value": value} for ticker, value in values[:limit]]


def _peer_ready(row: Mapping, group_id: str) -> bool:
    current = row.get("current_context")
    peer_groups = current.get("peer_groups") if isinstance(current, Mapping) else None
    if not isinstance(peer_groups, list):
        return False
    for peer in peer_groups:
        if not isinstance(peer, Mapping) or peer.get("group_id") != group_id:
            continue
        alpha = peer.get("legacy_alpha")
        return isinstance(alpha, Mapping) and alpha.get("independence_status") == "AVAILABLE"
    return False


def attach_group_leadership(view: Mapping) -> dict:
    """Add group-level descriptive ordering without touching row selection/order."""
    if (
        not isinstance(view, Mapping)
        or view.get("schema") != "mastermind.leadership_lab.recovery.v1"
        or not isinstance(view.get("current_context"), Mapping)
    ):
        raise ValueError("Leadership Lab current-context view required")
    rows = view.get("rows")
    shortlist = view.get("shortlist")
    groups = view.get("groups")
    if not isinstance(rows, list) or not isinstance(shortlist, list) or not isinstance(groups, list):
        raise ValueError("Leadership Lab rows, shortlist, and groups required")

    row_by_ticker: dict[str, Mapping] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("Leadership Lab row must be a mapping")
        ticker = _text(row.get("ticker"))
        if ticker is None or ticker in row_by_ticker:
            raise ValueError("Leadership Lab ticker identity invalid")
        row_by_ticker[ticker] = row

    projected = []
    skipped = 0
    for raw in groups:
        if not isinstance(raw, Mapping):
            skipped += 1
            continue
        group_id = _text(raw.get("id"))
        name = _text(raw.get("name"))
        category = _text(raw.get("category")) or "Other"
        members_raw = raw.get("members")
        if group_id is None or name is None or not isinstance(members_raw, list) or not members_raw:
            skipped += 1
            continue
        members = []
        invalid = False
        for member in members_raw:
            ticker = _text(member)
            if ticker is None:
                invalid = True
                break
            members.append(ticker)
        if invalid or len(members) != len(set(members)):
            skipped += 1
            continue

        member_count = raw.get("member_count")
        if isinstance(member_count, bool) or not isinstance(member_count, int) or member_count < len(members):
            skipped += 1
            continue
        alpha_top = _top(members, row_by_ticker, "legacy_alpha")
        rs_top = _top(members, row_by_ticker, "legacy_rs")
        observed_alpha = sum(
            finite_number(row_by_ticker.get(ticker, {}).get("legacy_alpha")) is not None
            for ticker in members
        )
        observed_rs = sum(
            finite_number(row_by_ticker.get(ticker, {}).get("legacy_rs")) is not None
            for ticker in members
        )
        recovered_members = [ticker for ticker in members if ticker in row_by_ticker]
        peer_ready = sum(_peer_ready(row_by_ticker[ticker], group_id) for ticker in recovered_members)
        coverage = finite_number(raw.get("coverage"))
        projected.append({
            "group_id": group_id,
            "name": name,
            "category": category,
            "member_count": member_count,
            "observed_alpha_count": observed_alpha,
            "observed_rs_count": observed_rs,
            "coverage": coverage,
            "top_legacy_alpha": alpha_top,
            "top_legacy_rs": rs_top,
            "independent_peer_ready_count": peer_ready,
            "independent_peer_total_recovered_members": len(recovered_members),
            "independent_confirmation_count": None,
            "membership_basis": "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED",
            "historical_membership_qualified": raw.get("historical_membership_qualified") is True,
            "interpretation": "descriptive recovered ordering; not a forecast or candidate rank",
            "authority": dict(_AUTHORITY),
        })

    projected.sort(key=lambda item: (item["category"], item["name"], item["group_id"]))
    result = deepcopy(dict(view))
    result["current_context"] = deepcopy(dict(result["current_context"]))
    result["current_context"]["group_leadership"] = projected
    result["current_context"]["group_leadership_skipped"] = skipped
    result["current_context"]["group_leadership_authority"] = dict(_AUTHORITY)
    return result
