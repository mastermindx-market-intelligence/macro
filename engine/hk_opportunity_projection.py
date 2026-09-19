"""Pure HK Opportunities projection.

This module composes existing authorities into a zero-authority presentation
view model. It does not originate candidates, alter entry permission, rank the
live board, publish, persist state, or write another store.

The incumbent HK board is the only source allowed to create the ENTRY_OPEN
lane. Existing discovery plus the frozen no-gate Pick-Lab screen can only add
PREPARING or MONITOR rows, with Pick-Lab order explicitly labelled as an
attention rank rather than a trade rank.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

SCHEMA = "mastermind.hk_opportunities_projection.v1"
DISCOVERY_DEFINITION = "hk_discovery_v1"

ENTRY_OPEN = "ENTRY_OPEN"
PREPARING = "PREPARING"
MONITOR = "MONITOR"

WAIT_CONFLUENCE = "WAIT_CONFLUENCE"
WAIT_PULLBACK = "WAIT_PULLBACK"
RAN_DONT_CHASE = "RAN_DONT_CHASE"
BLOCKED = "BLOCKED"
UNAVAILABLE_DATA = "UNAVAILABLE_DATA"
MONITOR_ONLY = "MONITOR_ONLY"

_OFFICIAL_OPEN = frozenset({"buy_now", "partial"})
_OFFICIAL_PREPARING = frozenset(
    {"buy_soon", "wait_pullback", "watch", "await_confluence"}
)
_OFFICIAL_MONITOR = frozenset({"hold", "extended"})
_DISCOVERY_PREPARING = frozenset(
    {ENTRY_OPEN, WAIT_CONFLUENCE, WAIT_PULLBACK}
)
_DISCOVERY_MONITOR = frozenset({RAN_DONT_CHASE})
_OWNER_CONTEXT_LANES = {
    "ripening": (PREPARING, WAIT_CONFLUENCE),
    "ran": (MONITOR, RAN_DONT_CHASE),
    "leaders": (MONITOR, MONITOR_ONLY),
    "watch": (MONITOR, MONITOR_ONLY),
}


def _blank(*, incumbent_asof: Any, discovery_asof: Any, attention_asof: Any, reason: str) -> dict:
    return {
        "schema": SCHEMA,
        "market": "HK",
        "available": False,
        "reason": reason,
        "source_asof": {
            "incumbent": incumbent_asof,
            "discovery": discovery_asof,
            "attention": attention_asof,
        },
        "lanes": {
            ENTRY_OPEN: [],
            PREPARING: [],
            MONITOR: [],
        },
        "diagnostics": {},
    }


def _ticker(row: Mapping[str, Any] | None, *keys: str) -> str | None:
    if not isinstance(row, Mapping):
        return None
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _official_lane(status: str | None) -> str | None:
    if status in _OFFICIAL_OPEN:
        return ENTRY_OPEN
    if status in _OFFICIAL_PREPARING:
        return PREPARING
    if status in _OFFICIAL_MONITOR:
        return MONITOR
    return None


def _official_row(
    source: Mapping[str, Any],
    *,
    lane: str,
    owner_position: int,
) -> dict[str, Any]:
    entry = source.get("entry_signal") or {}
    row = {
        "ticker": str(source.get("ticker")),
        "lane": lane,
        "source_lane": "incumbent_buy",
        "permission_status": entry.get("status"),
        "permission_source": "entry_signal",
        "permission_authority": "official_board",
        "owner_position": int(owner_position),
    }
    for key in ("name", "name_zh", "sector", "sector_zh", "price"):
        if source.get(key) is not None:
            row[key] = deepcopy(source.get(key))
    headline = entry.get("headline")
    if headline is not None:
        row["permission_headline"] = deepcopy(headline)
    return row


def _discovery_index(
    rows: Iterable[Mapping[str, Any]],
    *,
    asof: str,
) -> dict[str, dict[str, Any]]:
    """Keep the first exact raw listing for the governed discovery definition."""
    out: dict[str, dict[str, Any]] = {}
    for source in rows or ():
        if not isinstance(source, Mapping):
            continue
        if str(source.get("challenger_definition") or "") != DISCOVERY_DEFINITION:
            continue
        if str(source.get("session_date") or "") != str(asof):
            continue
        ticker = _ticker(source, "security_ref_raw")
        if not ticker or ticker in out:
            continue
        out[ticker] = dict(source)
    return out


def _owner_context_index(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index only the existing incumbent display lanes, first identity wins."""
    out: dict[str, dict[str, Any]] = {}
    for source in rows or ():
        if not isinstance(source, Mapping):
            continue
        context_lane = str(source.get("owner_context_lane") or "")
        if context_lane not in _OWNER_CONTEXT_LANES:
            continue
        ticker = _ticker(source, "ticker")
        if not ticker or ticker in out:
            continue
        out[ticker] = dict(source)
    return out


def _owner_context_row(
    context: Mapping[str, Any],
    attention: Mapping[str, Any],
) -> dict[str, Any]:
    context_lane = str(context.get("owner_context_lane"))
    lane, permission_status = _OWNER_CONTEXT_LANES[context_lane]
    row = {
        "ticker": str(context.get("ticker")),
        "lane": lane,
        "source_lane": f"incumbent_{context_lane}",
        "permission_status": permission_status,
        "permission_source": "owner_stance",
        "permission_authority": "official_display",
        "owner_context_lane": context_lane,
        "attention_rank": attention.get("rank"),
        "attention_authority": "display_only_screen",
    }
    for key in ("name", "name_zh", "sector", "sector_zh", "stance", "stance_zh"):
        if context.get(key) is not None:
            row[key] = deepcopy(context.get(key))
    why = attention.get("why")
    if isinstance(why, (list, tuple)):
        row["attention_reasons"] = deepcopy(list(why))
    features = attention.get("features")
    if isinstance(features, Mapping):
        row["attention_features"] = deepcopy(dict(features))
    return row


def _attention_row(
    discovery: Mapping[str, Any],
    attention: Mapping[str, Any],
    *,
    lane: str,
) -> dict[str, Any]:
    features = attention.get("features")
    row = {
        "ticker": str(discovery.get("security_ref_raw")),
        "lane": lane,
        "source_lane": "discovery_attention",
        "permission_status": discovery.get("availability_status"),
        "permission_source": discovery.get("availability_source"),
        "permission_authority": "discovery_shadow",
        "candidate_origin": discovery.get("candidate_origin"),
        "attention_rank": attention.get("rank"),
        "attention_authority": "display_only_screen",
    }
    why = attention.get("why")
    if isinstance(why, (list, tuple)):
        row["attention_reasons"] = deepcopy(list(why))
    if isinstance(features, Mapping):
        row["attention_features"] = deepcopy(dict(features))
    return row


def project_opportunities(
    *,
    incumbent_asof: str | None,
    discovery_asof: str | None,
    attention_asof: str | None,
    incumbent_buy: Iterable[Mapping[str, Any]],
    discovery_rows: Iterable[Mapping[str, Any]],
    attention_picks: Iterable[Mapping[str, Any]],
    owner_context_rows: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compose official HK permission with zero-authority discovery attention.

    Source epochs must match exactly. Official board rows are emitted first and
    keep their owner order. Attention rows may only reuse a same-session
    hk_discovery_v1 observation and can never create an ENTRY_OPEN lane.
    """
    source_asof = {
        "incumbent": incumbent_asof,
        "discovery": discovery_asof,
        "attention": attention_asof,
    }
    values = [str(v) for v in source_asof.values() if v not in (None, "")]
    if len(values) != 3 or len(set(values)) != 1:
        return _blank(
            incumbent_asof=incumbent_asof,
            discovery_asof=discovery_asof,
            attention_asof=attention_asof,
            reason="source_asof_mismatch",
        )
    asof = values[0]

    lanes: dict[str, list[dict[str, Any]]] = {
        ENTRY_OPEN: [],
        PREPARING: [],
        MONITOR: [],
    }
    diagnostics = {
        "official_excluded_by_permission": 0,
        "attention_not_in_discovery": 0,
        "attention_excluded_by_permission": 0,
        "attention_duplicate": 0,
        "attention_shadowed_by_official": 0,
        "attention_recovered_by_owner_context": 0,
        "attention_without_context": 0,
    }

    official_seen: set[str] = set()
    for owner_position, source in enumerate(incumbent_buy or (), 1):
        ticker = _ticker(source, "ticker")
        if not ticker or ticker in official_seen:
            continue
        official_seen.add(ticker)
        entry = source.get("entry_signal") if isinstance(source, Mapping) else None
        status = (entry or {}).get("status") if isinstance(entry, Mapping) else None
        lane = _official_lane(str(status) if status is not None else None)
        if lane is None:
            diagnostics["official_excluded_by_permission"] += 1
            continue
        lanes[lane].append(
            _official_row(source, lane=lane, owner_position=owner_position)
        )

    discovery = _discovery_index(discovery_rows or (), asof=asof)
    owner_context = _owner_context_index(owner_context_rows or ())
    attention_seen: set[str] = set()
    for source in attention_picks or ():
        ticker = _ticker(source, "ticker")
        if not ticker:
            continue
        if ticker in attention_seen:
            diagnostics["attention_duplicate"] += 1
            continue
        attention_seen.add(ticker)

        if ticker in official_seen:
            diagnostics["attention_shadowed_by_official"] += 1
            continue
        drow = discovery.get(ticker)
        if drow is None:
            diagnostics["attention_not_in_discovery"] += 1
            context = owner_context.get(ticker)
            if context is None:
                diagnostics["attention_without_context"] += 1
                continue
            row = _owner_context_row(context, source)
            lanes[row["lane"]].append(row)
            diagnostics["attention_recovered_by_owner_context"] += 1
            continue

        status = str(drow.get("availability_status") or "")
        if status in _DISCOVERY_PREPARING:
            lane = PREPARING
        elif status in _DISCOVERY_MONITOR:
            lane = MONITOR
        else:
            diagnostics["attention_excluded_by_permission"] += 1
            continue
        lanes[lane].append(_attention_row(drow, source, lane=lane))

    diagnostics["lane_counts"] = {
        key: len(value) for key, value in lanes.items()
    }
    diagnostics["official_population"] = len(official_seen)
    diagnostics["discovery_population"] = len(discovery)
    diagnostics["attention_population"] = len(attention_seen)
    diagnostics["owner_context_population"] = len(owner_context)

    return {
        "schema": SCHEMA,
        "market": "HK",
        "available": True,
        "reason": None,
        "source_asof": source_asof,
        "lanes": lanes,
        "diagnostics": diagnostics,
    }