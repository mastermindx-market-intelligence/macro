"""Read-only independent-peer context for Leadership Lab.

The only peer computation is the incumbent engine.group_flow public observation.
This adapter supplies recovered Alpha/RS values plus current Prophet episode issuer
identities, preserves unknown identities in the denominator, and adds no score,
stage, forecast, or trading authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from engine.group_flow import independent_peer_observation
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


def _owner_observation(value: Mapping) -> dict:
    return {
        "state": value.get("state"),
        "independence_status": value.get("independence_status"),
        "peer_denominator": value.get("peer_denominator"),
        "observed_independent_peers": value.get("observed_independent_peers"),
        "missing_market_observation": list(value.get("missing_market_observation") or []),
        "unknown_peer_identity": list(value.get("unknown_peer_identity") or []),
        "excluded_same_issuer": list(value.get("excluded_same_issuer") or []),
        "positive_breadth_lower": finite_number(value.get("positive_breadth_lower")),
        "positive_breadth_upper": finite_number(value.get("positive_breadth_upper")),
        "negative_breadth_lower": finite_number(value.get("negative_breadth_lower")),
        "negative_breadth_upper": finite_number(value.get("negative_breadth_upper")),
        "peer_median": finite_number(value.get("peer_median")),
        "focal_value": finite_number(value.get("focal_value")),
        "focal_minus_peer_median": finite_number(value.get("focal_minus_peer_median")),
        "authority": dict(_AUTHORITY),
    }


def _qualified_group(raw: object) -> dict | None:
    if not isinstance(raw, Mapping):
        return None
    group_id = _text(raw.get("id"))
    name = _text(raw.get("name"))
    category = _text(raw.get("category")) or "Other"
    members = raw.get("members")
    if group_id is None or name is None or not isinstance(members, list) or not members:
        return None
    normalized: list[str] = []
    for value in members:
        ticker = _text(value)
        if ticker is None:
            return None
        normalized.append(ticker)
    if len(normalized) != len(set(normalized)):
        return None
    member_count = raw.get("member_count")
    if (
        isinstance(member_count, bool) or not isinstance(member_count, int)
        or member_count != len(normalized)
    ):
        return None
    return {
        "group_id": group_id,
        "name": name,
        "category": category,
        "members": normalized,
        "historical_membership_qualified": raw.get("historical_membership_qualified") is True,
    }


def attach_independent_peer_context(view: Mapping) -> dict:
    """Attach leave-issuer-out Alpha/RS comparisons without changing selection."""
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

    result = deepcopy(dict(view))
    episode_book = view['current_context'].get('episode_book', {})
    proof = episode_book.get('source_validation', {}) if isinstance(episode_book, Mapping) else {}
    native_verified = isinstance(proof, Mapping) and proof.get('status') == 'VALIDATED_CANONICAL_OWNER'
    row_by_ticker: dict[str, Mapping] = {}
    issuer_by_ticker: dict[str, str | None] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ValueError("Leadership Lab row must be a mapping")
        ticker = _text(raw.get("ticker"))
        if ticker is None or ticker in row_by_ticker:
            raise ValueError("Leadership Lab row ticker identity invalid")
        row_by_ticker[ticker] = raw
        current = raw.get("current_context")
        episode = current.get("episode") if isinstance(current, Mapping) else None
        issuer = (
            _text(episode.get("company_id"))
            if native_verified and isinstance(episode, Mapping) and episode.get("status") == "AVAILABLE"
            else None
        )
        issuer_by_ticker[ticker] = issuer

    qualified: list[dict] = []
    skipped = 0
    for raw in groups:
        group = _qualified_group(raw)
        if group is None:
            skipped += 1
            continue
        qualified.append(group)

    observations: dict[tuple[str, str], dict] = {}
    groups_by_member: dict[str, list[dict]] = {}
    for group in qualified:
        members = group["members"]
        values_alpha = {
            ticker: finite_number(row_by_ticker.get(ticker, {}).get("legacy_alpha"))
            for ticker in members
        }
        values_rs = {
            ticker: finite_number(row_by_ticker.get(ticker, {}).get("legacy_rs"))
            for ticker in members
        }
        identity = {ticker: issuer_by_ticker.get(ticker) for ticker in members}
        for ticker in members:
            if ticker not in row_by_ticker:
                continue
            try:
                alpha = independent_peer_observation(
                    values_alpha, focal_ticker=ticker, issuer_by_ticker=identity)
                rs = independent_peer_observation(
                    values_rs, focal_ticker=ticker, issuer_by_ticker=identity)
            except ValueError:
                continue
            projected = {
                "group_id": group["group_id"],
                "name": group["name"],
                "category": group["category"],
                "membership_basis": "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED",
                "historical_membership_qualified": group["historical_membership_qualified"],
                "identity_basis": "CURRENT_PROPHET_EPISODE_COMPANY_ID_NOT_HISTORICAL",
                "legacy_alpha": _owner_observation(alpha),
                "legacy_rs": _owner_observation(rs),
                "authority": dict(_AUTHORITY),
            }
            # RS levels live on a positive percentile scale. Their sign cannot
            # measure whether prices rose, or whether a group beat a benchmark.
            for key in ('positive_breadth_lower', 'positive_breadth_upper',
                        'negative_breadth_lower', 'negative_breadth_upper'):
                projected['legacy_rs'][key] = None
            projected['legacy_rs']['breadth_interpretation'] = 'NOT_APPLICABLE_TO_PERCENTILE_LEVELS'
            observations[(ticker, group["group_id"])] = projected
            groups_by_member.setdefault(ticker, []).append(projected)

    for values in groups_by_member.values():
        values.sort(key=lambda item: (item["category"], item["name"], item["group_id"]))

    def enrich(raw: object) -> dict:
        if not isinstance(raw, Mapping):
            raise ValueError("Leadership Lab row must be a mapping")
        row = deepcopy(dict(raw))
        ticker = _text(row.get("ticker"))
        if ticker is None:
            raise ValueError("Leadership Lab row ticker required")
        current = row.get("current_context")
        if not isinstance(current, Mapping):
            raise ValueError("Leadership Lab row current_context required")
        current = deepcopy(dict(current))
        current["peer_groups"] = deepcopy(groups_by_member.get(ticker, []))
        row["current_context"] = current
        return row

    result["rows"] = [enrich(row) for row in rows]
    result["shortlist"] = [enrich(row) for row in shortlist]
    result["current_context"]["peer_context"] = {
        "schema": "mastermind.leadership_lab.peer_context.v1",
        "mode": "EXISTING_GROUP_FLOW_OBSERVATION_ONLY",
        "qualified_groups": len(qualified),
        "skipped_groups": skipped,
        "rows_with_peer_groups": len(groups_by_member),
        "membership_basis": "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED",
        "identity_basis": "CURRENT_PROPHET_EPISODE_COMPANY_ID_NOT_HISTORICAL",
        "authority": dict(_AUTHORITY),
    }
    return result
