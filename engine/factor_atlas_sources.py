"""Invocation-scoped bridge to incumbent basket, identity, calendar and price owners.

No collection, membership write, replacement catalog, network fallback or store is
implemented here. Callers provide the already-admitted membership reader and the
existing price resolver. This bridge preserves unavailable source metadata; it
never fills an adjustment vintage, rights decision or knowledge clock from now().
The calculation remains CANDIDATE_NOT_ADMITTED even when every necessary check passes.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import math
from typing import Any

import pandas as pd

from engine.factor_atlas_read import build_factor_read, canonical_bytes
from engine.price_ladder import Resolved
from lib.dataos.identity import VendorAliasTable
from lib.dataos.temporal import utc
from lib.market_session import _windows, calendar_verified
from lib.us_cash_calendar import ET, sessions_between


def owner_calendar(start: str, end: str, *, code_ref: str) -> dict[str, Any]:
    """Use the existing US cash-calendar owner, including DST and early closes."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (last - first).days > 1850:
        raise ValueError("calendar window must be ascending and at most 1850 days")
    days = sessions_between(first, last)
    strings = [day.isoformat() for day in days]
    if len(days) < 2 or strings[0] != start or strings[-1] != end:
        raise ValueError("request endpoints must be existing completed US calendar sessions")
    rows = []
    for day in days:
        close = datetime.combine(day, _windows("US", day)[-1][1], tzinfo=ET)
        rows.append({"date": day.isoformat(),
                     "close_at": close.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")})
    return {"ref": f"{code_ref}:lib/us_cash_calendar.py+lib/market_session.py",
            "coverage_verified": all(calendar_verified("US", day.year) for day in days),
            "sessions": rows,
            "rebalance_dates": [start] + [a for a, b in zip(strings, strings[1:]) if a[:7] != b[:7]]}


def _alias_projection_digest(aliases: VendorAliasTable) -> str:
    records = []
    for row in aliases.rows:
        record = asdict(row)
        for key in ("valid_from", "valid_to", "known_at"):
            value = record[key]
            if isinstance(value, (date, datetime)):
                record[key] = value.isoformat()
        records.append(record)
    records.sort(key=lambda row: canonical_bytes(row))
    return hashlib.sha256(canonical_bytes(records)).hexdigest()


def _price_projection(result: Resolved, *, store_symbol: str,
                      currency: str | None, corporate_action_ref: str | None) -> dict:
    if not isinstance(result, Resolved):
        raise ValueError("price reader must return the incumbent Resolved type")
    if result.ticker != store_symbol:
        raise ValueError("price owner returned a different requested store symbol")
    evidence = asdict(result.evidence) if result.evidence is not None else {}
    if evidence and evidence.get("ticker") != store_symbol:
        raise ValueError("price evidence and selected store symbol disagree")
    values = {}
    if result.series is not None:
        series = result.series
        if not isinstance(series, pd.Series) or not isinstance(series.index, pd.DatetimeIndex):
            raise ValueError("incumbent price series must carry daily DatetimeIndex labels")
        labels = series.index.strftime("%Y-%m-%d").tolist()
        if len(labels) != len(set(labels)):
            raise ValueError("duplicate daily price label")
        if labels != sorted(labels):
            raise ValueError("price observations must be ordered")
        for day, value in zip(labels, series.tolist(), strict=True):
            if pd.isna(value):
                values[day] = None
            elif isinstance(value, bool):
                values[day] = value  # native numerical gate refuses bool, rather than treating it as 1
            else:
                value = float(value)
                if not math.isfinite(value):
                    raise ValueError("nonfinite price observation")
                values[day] = value
    return {"evidence": evidence, "values": values, "currency": currency,
            "corporate_action_ref": corporate_action_ref}


def build_from_owners(request: Mapping[str, Any], *,
                      membership_reader: Callable[[str], Mapping[str, Any]],
                      aliases: VendorAliasTable, alias_snapshot_ref: str,
                      price_reader: Callable[[str], Resolved],
                      decision_cutoffs: Mapping[str, str], rights: Mapping[str, Any],
                      code_ref: str, input_revision: str, evidence_kind: str,
                      current_roster_asof: str | None = None,
                      currency_by_security: Mapping[str, str] | None = None,
                      corporate_action_refs: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Bind one request without creating identities or silently reducing its population.

    membership_reader returns {value: <incumbent members_asof result>,
    snapshot_ref, source_sha256}. Its native collection receipt supplies precise
    knowledge/completeness when present; legacy/fallback results remain unqualified.
    Current mode freezes one explicitly supplied current_roster_asof observation.

    Alias lookup deliberately separates historical 'membership' names from the
    'store' current-catalog keys. The owner retains both interpretations. This is
    a consumer projection and necessary-condition check, not receipt authentication.
    """
    if not isinstance(aliases, VendorAliasTable) or not alias_snapshot_ref:
        raise ValueError("the incumbent alias table and its exact snapshot reference are required")
    request = dict(request)
    mode = request.get("history_mode")
    if mode not in {"CURRENT_ROSTER", "PIT_AS_KNOWN"}:
        raise ValueError("unsupported history_mode")
    cutoff = utc(request["measurement_cutoff"])
    calendar = owner_calendar(request["start"], request["end"], code_ref=code_ref)
    if mode == "CURRENT_ROSTER":
        if current_roster_asof is None or date.fromisoformat(current_roster_asof) > cutoff.date():
            raise ValueError("an explicit current roster date no later than measurement is required")
        queries = [current_roster_asof]
    else:
        queries = calendar["rebalance_dates"]
    alias_digest = _alias_projection_digest(aliases)
    rosters, identities, binding_rows = {}, {}, []
    unresolved, requested_symbols, all_ids = set(), set(), set()
    for on in queries:
        wrapper = membership_reader(on)
        if not isinstance(wrapper, Mapping) or not isinstance(wrapper.get("value"), Mapping):
            raise ValueError("membership reader must return an explicit incumbent observation")
        raw = dict(wrapper["value"])
        symbols = raw.get("members")
        if not isinstance(symbols, list) or len(symbols) > 512 or not all(isinstance(x, str) for x in symbols):
            raise ValueError("membership owner returned an invalid bounded population")
        if len(symbols) != len(set(symbols)):
            raise ValueError("duplicate member symbol")
        decision = decision_cutoffs.get(on) if mode == "PIT_AS_KNOWN" else request["measurement_cutoff"]
        utc(decision)
        selected, identity = [], {}
        for symbol in sorted(symbols):
            requested_symbols.add(symbol)
            sid = aliases.resolve("membership", symbol, date.fromisoformat(on), decision_at=decision)
            if sid is None:
                unresolved.add(symbol)
                continue
            row = next(r for r in aliases.rows if r.vendor == "membership" and r.vendor_symbol == symbol
                       and r.security_id == sid and r.covers(date.fromisoformat(on), decision_at=decision))
            if sid in selected:
                raise ValueError("duplicate security identity after incumbent alias resolution")
            selected.append(sid)
            identity[sid] = {"owner_ref": f"{alias_snapshot_ref}#projection:{alias_digest}",
                             "known_at": (utc(row.known_at).isoformat() if row.known_at is not None else None),
                             "valid_from": row.valid_from.isoformat() if row.valid_from else None,
                             "valid_to": row.valid_to.isoformat() if row.valid_to else None}
        receipt = raw.get("collection_receipt") or {}
        snapshot_date = raw.get("snapshot_date")
        roster = {"basket_id": raw.get("basket_id"), "members": selected,
                  "pit": raw.get("pit"), "basis": raw.get("basis"),
                  "source_shape": raw.get("source_shape"), "asof": raw.get("asof"),
                  "snapshot_date": snapshot_date, "effective_from": snapshot_date, "effective_to": None,
                  "collection_state": raw.get("collection_state", "UNAVAILABLE"),
                  "known_at": receipt.get("known_at"), "snapshot_ref": wrapper.get("snapshot_ref"),
                  "source_sha256": wrapper.get("source_sha256")}
        rosters[on], identities[on] = roster, identity
        all_ids.update(selected)
        binding_rows.append({"query": on, "member_count": len(symbols), "resolved_count": len(selected),
                             "snapshot_ref": wrapper.get("snapshot_ref"), "collection_id": receipt.get("collection_id")})
    result = {"schema": "factor_atlas_owner_binding.v1", "binding_status": "BOUND",
              "evidence_kind": evidence_kind, "requested_member_count": len(requested_symbols),
              "member_count_basis": "distinct_input_symbols_across_requested_observations",
              "unresolved_symbols": sorted(unresolved), "observations": binding_rows,
              "alias_projection_digest": alias_digest, "reasons": [], "read": None}
    if unresolved:
        result.update(binding_status="UNAVAILABLE", reasons=["UNRESOLVED_SECURITY_IDENTITY"])
        return result
    prices, currency_by_security = {}, currency_by_security or {}
    corporate_action_refs = corporate_action_refs or {}
    for sid in sorted(all_ids):
        symbol = aliases.vendor_symbol_for("store", sid, cutoff.date())
        if symbol is None:
            result.update(binding_status="UNAVAILABLE", reasons=["STORE_ALIAS_UNAVAILABLE"])
            return result
        prices[sid] = _price_projection(price_reader(symbol), store_symbol=symbol,
                                       currency=currency_by_security.get(sid),
                                       corporate_action_ref=corporate_action_refs.get(sid))
    inputs = {"evidence_kind": evidence_kind, "code_ref": code_ref, "input_revision": input_revision,
              "correction_of": None, "calendar": calendar, "decision_cutoffs": dict(decision_cutoffs),
              "current_roster": rosters[queries[0]] if mode == "CURRENT_ROSTER" else None,
              "pit_rosters": rosters if mode == "PIT_AS_KNOWN" else {},
              "identity": identities[queries[0]], "identity_by_date": identities,
              "prices": prices, "rights": dict(rights)}
    result["read"] = build_factor_read(request, owner_inputs=inputs)
    return result
