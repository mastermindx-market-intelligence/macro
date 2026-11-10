"""Full Sector group membership over ONE captured generation; no access or storage owner.

Scope
-----
This module is a pure projection of the already-verified generation bytes (the
existing five-member Sector bundle) into the FULL group-membership population
that the bounded five-member classification example could never represent, and
into the signed, versioned continuation tokens that page it. It reads no file,
resolves no path, takes no clock, performs no authorization and writes nothing.

Three independent concepts (never fused)
----------------------------------------
* ``membership``          - the group lists this symbol (owner: baskets.json);
* ``prophet_eligibility`` - whether a downstream engine may consume it. Nothing
  produces this today, so it reads ``unavailable`` rather than a guessed value;
* ``visibility``          - what this audience may inspect. The population route
  serves the ENTITLED audience only and never serves a partial list as "full".

``group_id`` is a basket's own native id. It is NOT a sector id and no crosswalk
to a native sector (``xlf`` vs ``us_sector_financials``) is invented here: the
``native_sector_ref`` of every group reads ``unavailable``.

Cursor law
----------
A token binds, under an HMAC the caller cannot forge: the capture (generation id +
content id), the basis version, the audience, the filter digest, the page size and
the actor digest. Any difference is an explicit RESET, never a mixed page. The
capture named inside a token is a server-issued fact, not a caller selector.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

POPULATION_SCHEMA = "sector_population.page/v1"
CAPTURE_SCHEMA = "sector_population.capture/v1"
BASIS_VERSION = "sector_population.basis/v1:baskets.members"
TOKEN_VERSION = 1
#: ``c`` page cursor (binds filter + page size + offset); ``x`` captured-context
#: reference, the closed original-ref: it names ONE retained capture for one actor
#: and audience and is usable with any filter, from offset 0.
TOKEN_KINDS = ("c", "x")
DEFAULT_LIMIT = 100
MAX_LIMIT = 200
MAX_QUERY = 64
MAX_GROUPS = 256
MAX_ROWS = 50_000
MAX_TOKEN = 1024

_GROUP_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
_SYMBOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,15}\Z")
#: The owner's own content-digest shape, as stamped on stored PIT rows (S3): a
#: carried ``members_sha`` that is not null and not exactly this is malformed.
_SNAPSHOT_SHA = re.compile(r"[0-9a-f]{64}\Z")
_QUERY = re.compile(r"[\w .&'\-]{1,64}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_\-]+\.[0-9a-f]{64}\Z")
_ACTION_LANES = ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid")
UNAVAILABLE_NOT_PRODUCED = {"status": "unavailable", "reason": "not_produced"}
#: A carried DATED block that arrives without a non-empty string ``as_of`` (R4-N3).
#: The builder's dated-block filter already refuses to carry such a block, so a
#: block reaching this reader undated is malformed; it is served as unavailable
#: with this closed reason, never as ``available`` with ``as_of: None``.
REASON_UNDATED = "carried_block_undated"


class PopulationError(ValueError):
    """A closed population-contract failure; never embeds private data."""


class CursorSecretInvalid(PopulationError):
    """``SECTOR_GENERATION_CURSOR_SECRET`` is set but unusable: the route fails closed."""


#: Closed reasons a configured current member has no served row. Every reason except
#: ``unaccounted_by_owner`` is OWNER evidence captured in the generation; the last one
#: marks a member the owner observed (or never explained) that is nevertheless absent
#: from the served list - a row lost after the owner's observation - and it is never
#: counted as explained.
REASON_UNACCOUNTED = "unaccounted_by_owner"
REASON_GROUP_REFUSED = "group_refused_by_owner_observation"
UNSERVED_REASONS = ("absent_from_price_panel", "not_observed_at_effective_as_of",
                    REASON_GROUP_REFUSED, REASON_UNACCOUNTED)
MAX_UNSERVED = 500


@dataclass(frozen=True)
class Population:
    groups: tuple[Mapping[str, Any], ...]
    rows: tuple[Mapping[str, Any], ...]
    content_sha256: str
    #: Owner's configured CURRENT roster (configured minus removed), summed over groups
    #: from each group's captured ``observation.configured_members``; ``None`` when any
    #: group's roster is not in the capture OR the carried owner-roster block
    #: (``roster_baskets``, R3-S1) is missing/malformed (then completeness is unknown,
    #: never true).
    configured_current: int | None
    served: int
    #: Configured current members with no row, each identified with a closed reason.
    unserved: tuple[Mapping[str, str], ...]
    #: ``unaccounted_by_owner`` entries, served-but-unconfigured rows and removed members
    #: that also appear as configured or served. Any of these makes ``complete`` false.
    #: ``None`` when the roster clock does not agree (S1): the roster then contributes
    #: nothing, so no count is guessed - null, never a zero that would read as checked.
    unaccounted: int | None
    removed: Mapping[str, Any]
    industry_classification: Mapping[str, Any]
    sub_industry_classification: Mapping[str, Any]
    #: The roster-clock check (R4-N4): whether the carried roster's ``as_of`` equals
    #: the capture's own single ``observation.effective_as_of``. Any disagreement or
    #: indeterminacy makes ``configured_current``/``complete`` null (never true) and
    #: is disclosed here with a closed status/reason.
    roster_clock: Mapping[str, Any]
    #: Point-in-time first-known membership per roster pair (Part B), read from the
    #: carried ``membership_first_known`` block; unavailable with a closed reason
    #: when the block is absent, malformed or states its own failure.
    first_known: Mapping[str, Any]
    #: The stored PIT snapshot each group held at/before the effective session
    #: (Part B), from the carried ``membership_snapshots`` block - same fail-closed
    #: read rule as ``first_known``.
    membership_snapshot: Mapping[str, Any]

    @property
    def accounted_unserved(self) -> int:
        """Unserved members the OWNER explained (everything but ``unaccounted_by_owner``)."""
        return sum(1 for u in self.unserved if u["reason"] != REASON_UNACCOUNTED)

    @property
    def complete(self) -> bool | None:
        """served + owner-explained == configured current, computed - never asserted."""
        if self.configured_current is None:
            return None
        return (self.unaccounted == 0
                and self.served + self.accounted_unserved == self.configured_current)


def _text(value: Any, limit: int = 160) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= limit:
        return value
    return None


def _refusal_field(value: Any) -> Any:
    """One ``owner_observation_refusal`` field: numbers pass, strings take the same
    ``_text`` bound the live groups use (R3-N1 - a 200,000-char ``status`` is not
    carried verbatim), booleans and anything else are dropped. A NaN or infinite
    float is dropped like any other inadmissible value (R4-N6): it is not a number
    the finite wire can carry, and it is never a refusal fact."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if isinstance(value, (int, float)) else None


def _action_lookup(action_board: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    board = action_board.get("action_board") if isinstance(action_board, Mapping) else None
    found: dict[str, dict[str, Any]] = {}
    if not isinstance(board, Mapping):
        return found
    for lane in _ACTION_LANES:
        for row in board.get(lane) or ():
            if not isinstance(row, Mapping) or row.get("kind") != "theme":
                continue
            slug = row.get("ticker")
            if isinstance(slug, str) and slug not in found:
                found[slug] = {"status": "available", "lane": lane,
                               "reco": _text(row.get("reco"), 40),
                               "label": _text(row.get("label"), 40),
                               "score": row.get("score") if isinstance(row.get("score"), (int, float))
                               and not isinstance(row.get("score"), bool) else None}
    return found


_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _day_or_none(value: Any) -> str | None:
    """A day string that is also a REAL calendar date. ``2026-02-30`` matches the
    ``_DAY`` pattern but is not a date: it reads exactly like a pattern mismatch at
    every site that day-checks a carried fact (N6) - the same closed reason, never
    a new one."""
    if not (isinstance(value, str) and _DAY.fullmatch(value)):
        return None
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _carried_status_fact(doc: Any) -> dict[str, Any] | None:
    """A carried block that states its own ``unavailable`` status and reason."""
    if (isinstance(doc, Mapping) and doc.get("status") == "unavailable"
            and isinstance(doc.get("reason"), str) and doc.get("reason")):
        return {"status": "unavailable", "reason": _text(doc["reason"], 64)}
    return None


def _first_known_fact(doc: Any) -> dict[str, Any]:
    """Closed-shape read of the carried ``membership_first_known`` block (Part B 1).

    Every malformation degrades to unavailable/``not_produced``; an undated block to
    unavailable/``carried_block_undated`` (R4-N3's rule reads here too). Nothing is
    repaired: a pair the block does not cover simply stays outside ``groups``.
    """
    stated = _carried_status_fact(doc)
    if stated is not None:
        return stated
    if not isinstance(doc, Mapping):
        return dict(UNAVAILABLE_NOT_PRODUCED)
    if not (isinstance(doc.get("as_of"), str) and doc["as_of"]):
        return {"status": "unavailable", "reason": REASON_UNDATED}
    basis, first = _text(doc.get("basis"), 80), doc.get("first_known")
    if not basis or not isinstance(first, Mapping) or not first:
        return dict(UNAVAILABLE_NOT_PRODUCED)
    groups: dict[str, dict[str, str | None]] = {}
    for gid, bucket in first.items():
        if not isinstance(gid, str) or not _GROUP_ID.fullmatch(gid) \
                or not isinstance(bucket, Mapping):
            return dict(UNAVAILABLE_NOT_PRODUCED)
        out: dict[str, str | None] = {}
        for symbol, day in bucket.items():
            if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
                return dict(UNAVAILABLE_NOT_PRODUCED)
            if day is not None and _day_or_none(day) is None:
                return dict(UNAVAILABLE_NOT_PRODUCED)
            out[symbol] = day
        groups[gid] = out
    return {"status": "available", "source": _text(doc.get("source"), 120),
            "as_of": _text(doc.get("as_of"), 40), "basis": basis,
            "basis_note": _text(doc.get("basis_note"), 200),
            "store_first": _day_or_none(doc.get("store_first")),
            "store_last": _day_or_none(doc.get("store_last")),
            "absent_pair_reason": _text(doc.get("absent_pair_reason"), 64),
            "groups": groups}


def _snapshot_fact(doc: Any) -> dict[str, Any]:
    """Closed-shape read of the carried ``membership_snapshots`` block (Part B 2).

    Per group: an available entry (stored snapshot date, the owner's stamped
    ``members_sha``, member count, ``equals_current_roster`` bool-or-null) or the
    owner's own unavailable basis. Any malformation degrades the WHOLE fact - never
    a partially repaired group set.
    """
    stated = _carried_status_fact(doc)
    if stated is not None:
        return stated
    if not isinstance(doc, Mapping):
        return dict(UNAVAILABLE_NOT_PRODUCED)
    if not (isinstance(doc.get("as_of"), str) and doc["as_of"]):
        return {"status": "unavailable", "reason": REASON_UNDATED}
    # S3: the fact is only readable when it states the owner's own suite (the literal
    # ``baskets``) - anything else is malformed as a WHOLE, never partially trusted.
    if doc.get("suite") != "baskets":
        return {"status": "unavailable", "reason": "carried_fact_malformed"}
    groups_in = doc.get("groups")
    if not isinstance(groups_in, Mapping) or not groups_in:
        return dict(UNAVAILABLE_NOT_PRODUCED)
    groups: dict[str, dict[str, Any]] = {}
    for gid, entry in groups_in.items():
        if not isinstance(gid, str) or not _GROUP_ID.fullmatch(gid) \
                or not isinstance(entry, Mapping):
            return dict(UNAVAILABLE_NOT_PRODUCED)
        if entry.get("status") == "unavailable":
            if not isinstance(entry.get("reason"), str) or not entry["reason"]:
                return dict(UNAVAILABLE_NOT_PRODUCED)
            groups[gid] = {"status": "unavailable", "reason": _text(entry["reason"], 64)}
            continue
        if entry.get("status") != "available":
            return dict(UNAVAILABLE_NOT_PRODUCED)
        day, count, equals = entry.get("snapshot_date"), entry.get("member_count"), \
            entry.get("equals_current_roster")
        sha = entry.get("members_sha")
        # S3: a stamped sha that is not null and not the owner's own 64-hex lowercase
        # digest shape degrades the WHOLE fact with the closed malformed reason.
        if not (sha is None or (isinstance(sha, str) and _SNAPSHOT_SHA.fullmatch(sha))):
            return {"status": "unavailable", "reason": "carried_fact_malformed"}
        if (_day_or_none(day) is None
                or not isinstance(count, int) or isinstance(count, bool) or count < 0
                or not (equals is None or isinstance(equals, bool))):
            return dict(UNAVAILABLE_NOT_PRODUCED)
        groups[gid] = {"status": "available", "snapshot_date": day,
                       "members_sha": sha, "member_count": count,
                       "equals_current_roster": equals}
    return {"status": "available", "source": _text(doc.get("source"), 120),
            "as_of": _text(doc.get("as_of"), 40), "suite": _text(doc.get("suite"), 40),
            "groups": groups}


def build_population(*, baskets: Mapping[str, Any], handoff: Mapping[str, Any],
                     action_board: Mapping[str, Any],
                     central: Mapping[str, Any]) -> Population:
    """Project every listed member of every group; refuse rather than truncate."""
    groups_in = baskets.get("baskets") if isinstance(baskets, Mapping) else None
    if not isinstance(groups_in, list) or not groups_in or len(groups_in) > MAX_GROUPS:
        raise PopulationError("invalid_population_groups")
    handoff_syms = handoff.get("basket_member_syms") if isinstance(handoff, Mapping) else None
    handoff_set = (frozenset(s for s in handoff_syms if isinstance(s, str))
                   if isinstance(handoff_syms, list) else None)
    actions = _action_lookup(action_board)
    coverage = {}
    for row in (central.get("baskets") if isinstance(central, Mapping) else None) or ():
        if isinstance(row, Mapping) and isinstance(row.get("id"), str) \
                and isinstance(row.get("membership_coverage"), Mapping):
            cov = row["membership_coverage"]
            coverage[row["id"]] = {
                "status": _text(cov.get("status"), 40),
                "n_listed": cov.get("n_listed") if isinstance(cov.get("n_listed"), int) else None,
                "n_effective": cov.get("n_effective") if isinstance(cov.get("n_effective"), int) else None,
                "source_version": _text(cov.get("source_version"), 40),
            }
    carried = central.get("carried") if isinstance(central, Mapping) else None
    carried = carried if isinstance(carried, Mapping) else {}

    def classification(name: str, *, labelled: bool):
        """(symbols, labels, meta) for one CURRENT-basis taxonomy, never point-in-time."""
        doc = carried.get(name)
        meta: dict[str, Any] = dict(UNAVAILABLE_NOT_PRODUCED)
        # R4-N3: the dated rule is enforced on the READ side too - a block with no
        # string ``as_of`` is served as unavailable (below), never available undated.
        if not (isinstance(doc, Mapping) and isinstance(doc.get("symbols"), Mapping)
                and doc.get("point_in_time") is False
                and (not labelled or isinstance(doc.get("subsectors"), Mapping))):
            return None, None, meta
        if not (isinstance(doc.get("as_of"), str) and doc["as_of"]):
            return None, None, {"status": "unavailable", "reason": REASON_UNDATED}
        meta = {"status": "available", "taxonomy": _text(doc.get("taxonomy"), 40),
                "basis": _text(doc.get("basis"), 80), "point_in_time": False,
                "source": _text(doc.get("source"), 120), "as_of": _text(doc.get("as_of"), 40),
                "universe": _text(doc.get("universe"), 80)}
        return doc["symbols"], (doc.get("subsectors") if labelled else None), meta

    industry_symbols, _unused, industry_meta = classification("member_industry", labelled=False)
    sub_symbols, sub_labels, sub_meta = classification("member_sub_industry", labelled=True)
    removed_doc = carried.get("removed_members")
    removed_meta: dict[str, Any] = dict(UNAVAILABLE_NOT_PRODUCED)
    if isinstance(removed_doc, Mapping) and isinstance(removed_doc.get("removed"), list):
        if not (isinstance(removed_doc.get("as_of"), str) and removed_doc["as_of"]):
            removed_meta = {"status": "unavailable", "reason": REASON_UNDATED}  # R4-N3
        else:
            removed_meta = {"status": "available", "n": len(removed_doc["removed"]),
                            "source": _text(removed_doc.get("source"), 120),
                            "version": _text(removed_doc.get("version"), 40),
                            "as_of": _text(removed_doc.get("as_of"), 40),
                            "members": [dict(r) for r in removed_doc["removed"]
                                        if isinstance(r, Mapping)]}
    symbol_groups: Counter[str] = Counter()
    for group in groups_in:
        for member in (group.get("members") if isinstance(group, Mapping) else None) or ():
            if isinstance(member, Mapping) and isinstance(member.get("symbol"), str):
                symbol_groups[member["symbol"]] += 1
    groups: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    unserved: list[dict[str, str]] = []
    unaccounted = 0
    configured_total: int | None = None
    roster_unknown = False
    for group in groups_in:
        gid = group.get("id") if isinstance(group, Mapping) else None
        if not isinstance(gid, str) or not _GROUP_ID.fullmatch(gid) or gid in seen_groups:
            raise PopulationError("invalid_population_group_id")
        seen_groups.add(gid)
        members = group.get("members")
        if not isinstance(members, list):
            raise PopulationError("invalid_population_members")
        seen_symbols: set[str] = set()
        for member in members:
            symbol = member.get("symbol") if isinstance(member, Mapping) else None
            if (not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol)
                    or symbol in seen_symbols):
                raise PopulationError("invalid_population_member")
            seen_symbols.add(symbol)
            added = member.get("added")
            # Two SEPARATE current-basis taxonomies; never merged into one field.
            if industry_symbols is None:
                industry = dict(UNAVAILABLE_NOT_PRODUCED)
            elif isinstance(industry_symbols.get(symbol), str):
                industry = {"status": "available", "label": _text(industry_symbols[symbol])}
            else:
                industry = {"status": "unavailable", "reason": "not_in_current_classification"}
            if sub_symbols is None:
                sub_industry = dict(UNAVAILABLE_NOT_PRODUCED)
            elif isinstance(sub_symbols.get(symbol), str) \
                    and isinstance(sub_labels.get(sub_symbols[symbol]), Mapping):
                label = sub_labels[sub_symbols[symbol]]
                sub_industry = {"status": "available", "key": sub_symbols[symbol],
                                "label": _text(label.get("label")),
                                "label_zh": _text(label.get("label_zh")),
                                "sector": _text(label.get("sector"))}
            else:
                sub_industry = {"status": "unavailable", "reason": "not_in_current_classification"}
            rows.append({
                "ordinal": len(rows), "group_id": gid, "symbol": symbol,
                "name": _text(member.get("name")),
                "membership": {"status": "listed",
                               "effective_on": added if isinstance(added, str) and len(added) <= 10 else None},
                "also_in_groups": symbol_groups[symbol] - 1,
                "in_handoff_member_set": None if handoff_set is None else symbol in handoff_set,
                "industry": industry, "sub_industry": sub_industry,
                "prophet_eligibility": dict(UNAVAILABLE_NOT_PRODUCED),
                "visibility": {"scope": "entitled_full"},
            })
            if len(rows) > MAX_ROWS:
                raise PopulationError("population_too_large")
        # ACCOUNTING against the owner's configured CURRENT roster, captured in the
        # group's own ``observation`` (configured minus removed). Counts are computed.
        configured_n = None
        unserved_here = 0
        observation = group.get("observation")
        configured = observation.get("configured_members") if isinstance(observation, Mapping) else None
        if isinstance(configured, list) and all(isinstance(s, str) for s in configured) \
                and len(set(configured)) == len(configured):
            configured_n = len(configured)
            panel_missing = set(observation.get("missing_columns") or ())
            asof_missing = set(observation.get("missing_at_asof") or ())
            observed = set(observation.get("observed_members") or ())
            for symbol in configured:
                if symbol in seen_symbols:
                    continue
                if symbol in panel_missing:
                    reason = "absent_from_price_panel"
                elif symbol in asof_missing:
                    reason = "not_observed_at_effective_as_of"
                else:
                    # Observed with a price at the as-of date (the producer keeps every
                    # such member) yet not served, or never explained: the row was lost
                    # after the owner's observation. NOT an explained state (R2-B1).
                    reason = REASON_UNACCOUNTED
                unserved.append({"group_id": gid, "symbol": symbol, "reason": reason})
                unserved_here += 1
                if reason == REASON_UNACCOUNTED:
                    unaccounted += 1
            extra = seen_symbols - set(configured)
            unaccounted += len(extra)  # a served row the roster does not list is never "complete"
            configured_total = (configured_total or 0) + configured_n
        else:
            roster_unknown = True
        groups.append({
            "group_id": gid, "kind": "basket", "name": _text(group.get("name")),
            "name_zh": _text(group.get("name_zh")), "category": _text(group.get("category")),
            "weighting": _text(group.get("weighting"), 40),
            "n_configured_current": configured_n, "n_members_listed": len(seen_symbols),
            "n_unserved": unserved_here if configured_n is not None else None,
            "refused_by_owner": False, "owner_observation_refusal": None,
            "membership_coverage": coverage.get("b-" + gid, dict(UNAVAILABLE_NOT_PRODUCED)),
            "action": actions.get(gid, {"status": "unavailable", "reason": "no_action_row"}),
            "native_sector_ref": dict(UNAVAILABLE_NOT_PRODUCED),
        })
    # R2-B2: baskets the OWNER refused (coverage floor) are absent from ``baskets`` but
    # their configured roster is in the same capture (``observation_refusals``). Their
    # members stay in the denominator, each listed unserved under a reason that names the
    # owner's refusal, and the refusal is visible per group. A missing or malformed list
    # makes completeness UNKNOWN (null), never true.
    refusals = baskets.get("observation_refusals")
    if not isinstance(refusals, list):
        roster_unknown = True
        refusals = []
    for refusal in refusals:
        rid = refusal.get("basket_id") if isinstance(refusal, Mapping) else None
        obs = refusal.get("observation") if isinstance(refusal, Mapping) else None
        configured = obs.get("configured_members") if isinstance(obs, Mapping) else None
        if (not isinstance(rid, str) or not _GROUP_ID.fullmatch(rid) or rid in seen_groups
                or not isinstance(configured, list)
                or not all(isinstance(s, str) and _SYMBOL.fullmatch(s) for s in configured)
                or len(set(configured)) != len(configured)):
            roster_unknown = True
            continue
        seen_groups.add(rid)
        for symbol in configured:
            unserved.append({"group_id": rid, "symbol": symbol, "reason": REASON_GROUP_REFUSED})
        configured_total = (configured_total or 0) + len(configured)
        groups.append({
            "group_id": rid, "kind": "basket", "name": None, "name_zh": None,
            "category": None, "weighting": None,
            "n_configured_current": len(configured), "n_members_listed": 0,
            "n_unserved": len(configured), "refused_by_owner": True,
            "owner_observation_refusal": {
                k: v for k, v in ((k, _refusal_field(obs.get(k))) for k in (
                    "status", "coverage", "observed_n", "configured_n",
                    "min_members", "min_coverage", "effective_as_of")) if v is not None},
            "membership_coverage": dict(UNAVAILABLE_NOT_PRODUCED),
            "action": {"status": "unavailable", "reason": "no_action_row"},
            "native_sector_ref": dict(UNAVAILABLE_NOT_PRODUCED),
        })
    # R3-S1: the owner's ROSTER (carried by the central builder from
    # data/baskets/membership.json, cut at the owner's effective session) names every
    # basket that owes members to this capture. A roster basket in NEITHER the live
    # ``baskets`` list NOR ``observation_refusals`` left by an unexplained producer
    # exit; its configured members are UNACCOUNTED - never silently absent from the
    # denominator - so ``complete`` cannot be true over the hole. A capture with no
    # readable roster block cannot be verified complete at all (null, never true).
    roster_doc = carried.get("roster_baskets")
    roster: dict[str, list[str]] | None = None
    roster_malformed = False
    entries = roster_doc.get("baskets") if isinstance(roster_doc, Mapping) else None
    roster_as_of = roster_doc.get("as_of") if isinstance(roster_doc, Mapping) else None
    roster_as_of = roster_as_of if isinstance(roster_as_of, str) and roster_as_of else None
    if isinstance(entries, Mapping) and entries and roster_as_of:
        if all(isinstance(gid, str) and _GROUP_ID.fullmatch(gid)
               and isinstance(syms, list)
               and all(isinstance(s, str) and _SYMBOL.fullmatch(s) for s in syms)
               and len(set(syms)) == len(syms)
               for gid, syms in entries.items()):
            roster = dict(entries)
        else:
            roster_malformed = True
            roster_unknown = True
    else:
        roster_unknown = True
    # R4-N4: the capture's OWN clock - the single ``observation.effective_as_of``
    # stated across the capture's observations, live groups and owner refusals alike
    # (the same stamp ``owner_effective_as_of`` cuts the roster at). The carried
    # roster must agree with it: a roster cut at a different session cannot vouch
    # for this capture's membership, so completeness reads null - never true - and
    # the disagreement is disclosed below with a closed status/reason.
    # S2/N1: an observation mapping PRESENT with an ``effective_as_of`` that is a
    # value of the wrong type or shape (a list, a number, an empty string, a nested
    # object) makes the clock INDETERMINATE even beside good stamps - it is
    # malformed, never silently treated as unstated. A NULL or absent stamp is
    # different: it is the producer's legitimate "no clock" value
    # (``population_observation`` stamps ``_date_text(when)``, which is None when the
    # producer has no clock) and reads the clock UNAVAILABLE - fail-closed alike,
    # but labelled unavailable, never malformed (N1).
    stamps: set[str] = set()
    capture_malformed = False
    capture_unstated = False
    for source in (groups_in, refusals):
        for entry in source:
            obs = entry.get("observation") if isinstance(entry, Mapping) else None
            if not isinstance(obs, Mapping):
                continue
            stamp = obs.get("effective_as_of")
            if isinstance(stamp, str) and stamp:
                stamps.add(stamp)
            elif stamp is None:
                capture_unstated = True
            else:
                capture_malformed = True
    capture_effective = next(iter(stamps)) if len(stamps) == 1 else None
    if roster is None:
        roster_clock = {"status": "unavailable",
                        "reason": "roster_block_malformed" if roster_malformed or entries
                        else "roster_block_absent"}
    elif capture_malformed:
        roster_unknown = True  # an unreadable stamp: the clock cannot be verified at all
        roster_clock = {"status": "unavailable",
                        "reason": "capture_effective_as_of_malformed",
                        "roster_as_of": roster_as_of}
    elif capture_unstated or not stamps:
        roster_unknown = True  # no verifiable single stated session (N1: a null or
        # absent stamp states no clock, even beside a stated one): cannot be verified
        roster_clock = {"status": "unavailable",
                        "reason": "capture_effective_as_of_unavailable",
                        "roster_as_of": roster_as_of}
    elif capture_effective is None:
        roster_unknown = True  # more than one stated session: the clock cannot be verified
        roster_clock = {"status": "mismatch", "reason": "capture_effective_as_of_not_single",
                        "roster_as_of": roster_as_of,
                        "capture_effective_as_of": sorted(stamps)}
    elif roster_as_of != capture_effective:
        # exact STRING equality: a form-only difference (the same session with an ISO
        # time suffix) is a mismatch, never a normalized agreement
        roster_unknown = True  # the roster was cut at a different session than the capture
        roster_clock = {"status": "mismatch", "reason": "roster_as_of_mismatch",
                        "roster_as_of": roster_as_of,
                        "capture_effective_as_of": capture_effective}
    else:
        roster_clock = {"status": "agree", "roster_as_of": roster_as_of,
                        "capture_effective_as_of": capture_effective}
    # S1: a roster whose clock does not agree with the capture vouches for NOTHING -
    # its unexplained baskets contribute no ``unaccounted_by_owner`` entries, and the
    # served ``unaccounted`` is null (below), never a guessed 0. Owner-explained
    # evidence from the capture itself (live-group and refusal observations) is
    # unaffected: it never came from the roster.
    if roster is not None and roster_clock.get("status") == "agree":
        for rid, syms in sorted(roster.items()):
            if rid in seen_groups:  # live baskets and valid refusals are already accounted
                continue
            for symbol in syms:
                unserved.append({"group_id": rid, "symbol": symbol, "reason": REASON_UNACCOUNTED})
                unaccounted += 1
            configured_total = (configured_total or 0) + len(syms)
    # A removed member must never also be configured, served or unserved: that is a
    # contradiction between the owner's roster and its captured observation.
    if removed_meta.get("status") == "available":
        removed_pairs = {(r.get("group_id"), r.get("symbol")) for r in removed_meta["members"]}
        present = {(r["group_id"], r["symbol"]) for r in rows} | {
            (u["group_id"], u["symbol"]) for u in unserved}
        unaccounted += len(removed_pairs & present)
    if len(unserved) > MAX_UNSERVED:
        raise PopulationError("population_unserved_too_large")  # refuse, never truncate
    first_known = _first_known_fact(carried.get("membership_first_known"))
    membership_snapshot = _snapshot_fact(carried.get("membership_snapshots"))
    canonical = json.dumps({"groups": groups, "rows": rows, "unserved": unserved,
                            "removed": removed_meta}, allow_nan=False, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return Population(
        tuple(groups), tuple(rows), hashlib.sha256(canonical).hexdigest(),
        None if roster_unknown else configured_total, len(rows), tuple(unserved),
        unaccounted if roster_clock.get("status") == "agree" else None,
        removed_meta, industry_meta, sub_meta, roster_clock, first_known,
        membership_snapshot)


def normalize_filter(group: str | None, query: str | None) -> dict[str, str | None]:
    if group is not None and not _GROUP_ID.fullmatch(group):
        raise PopulationError("invalid_group_filter")
    if query is not None:
        query = query.strip()
        if not _QUERY.fullmatch(query):
            raise PopulationError("invalid_query_filter")
    return {"group": group, "q": query or None}


def filter_digest(flt: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(flt), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def actor_digest(actor: str) -> str:
    """Digest of a VERIFIED user id. There is no shared anonymous actor: an empty id is
    refused so no two callers can hold mutually replayable tokens."""
    if not isinstance(actor, str) or not actor.strip():
        raise PopulationError("actor_unverified")
    return hashlib.sha256(("sector-actor:" + actor).encode("utf-8")).hexdigest()


def select_page(population: Population, flt: Mapping[str, Any], *, offset: int, limit: int):
    """Filter over the FULL population first, then page. Returns (rows, groups, total, next)."""
    if not (isinstance(offset, int) and not isinstance(offset, bool) and offset >= 0):
        raise PopulationError("invalid_offset")
    if not (isinstance(limit, int) and not isinstance(limit, bool) and 1 <= limit <= MAX_LIMIT):
        raise PopulationError("invalid_limit")
    group, query = flt.get("group"), flt.get("q")
    needle = query.casefold() if query else None
    matched = [r for r in population.rows
               if (group is None or r["group_id"] == group)
               and (needle is None or needle in r["symbol"].casefold()
                    or needle in (r["name"] or "").casefold())]
    total = len(matched)
    page = matched[offset:offset + limit]
    wanted = {r["group_id"] for r in page}
    if group is not None:
        wanted.add(group)  # a filtered group keeps its descriptor even with no served row
    groups = []
    for g in population.groups:
        if g["group_id"] in wanted:
            groups.append({**g, "unserved": [
                {"symbol": u["symbol"], "reason": u["reason"]}
                for u in population.unserved if u["group_id"] == g["group_id"]]})
    next_offset = offset + len(page) if offset + len(page) < total else None
    # ``q`` / ``group`` also search the UNSERVED members, so a search UI that finds no
    # served row still sees an accounted member (e.g. q=KVUE). Not paged: bounded by
    # MAX_UNSERVED and identical on every page of a filter.
    unserved_matching = [
        dict(u) for u in population.unserved
        if (group is None or u["group_id"] == group)
        and (needle is None or needle in u["symbol"].casefold())]
    return page, groups, total, next_offset, unserved_matching


# --- signed continuation tokens ------------------------------------------------

_PROCESS_KEY = os.urandom(32)
_KEY_DOMAIN = b"macro.sector_population.cursor.v1"


def key_is_durable() -> bool:
    """True only when a deployment-provisioned secret (>=32 bytes) signs the tokens."""
    configured = os.environ.get("SECTOR_GENERATION_CURSOR_SECRET")
    return configured is not None and len(configured.encode("utf-8")) >= 32


def _key() -> bytes:
    configured = os.environ.get("SECTOR_GENERATION_CURSOR_SECRET")
    if configured is None:
        return _PROCESS_KEY
    raw = configured.encode("utf-8")
    if len(raw) < 32:
        raise CursorSecretInvalid("cursor_secret_invalid")
    return hmac.new(raw, _KEY_DOMAIN, hashlib.sha256).digest()


def mint_token(kind: str, *, offset: int, generation_id: str, content_id: str,
               audience: str, filter_sha: str, limit: int, actor_sha: str,
               key: bytes | None = None) -> str:
    if kind not in TOKEN_KINDS:
        raise PopulationError("invalid_token_kind")
    body = {"v": TOKEN_VERSION, "k": kind, "o": offset, "g": generation_id, "c": content_id,
            "a": audience, "f": filter_sha, "l": limit, "u": actor_sha, "b": BASIS_VERSION}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("ascii")
    sig = hmac.new(key or _key(), raw, hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") + "." + sig


def open_token(token: str, *, key: bytes | None = None) -> dict[str, Any] | None:
    """Return the verified claims, ``None`` for a forged/foreign signature.

    Raises :class:`PopulationError` for a token that is not even well formed.
    """
    if not isinstance(token, str) or len(token) > MAX_TOKEN or not _TOKEN.fullmatch(token):
        raise PopulationError("malformed_token")
    encoded, sig = token.split(".")
    try:
        raw = base64.urlsafe_b64decode((encoded + "=" * (-len(encoded) % 4)).encode("ascii"))
        body = json.loads(raw.decode("ascii"))
    except (ValueError, UnicodeError):
        raise PopulationError("malformed_token") from None
    if not hmac.compare_digest(sig, hmac.new(key or _key(), raw, hashlib.sha256).hexdigest()):
        return None
    required = {"v", "k", "o", "g", "c", "a", "f", "l", "u", "b"}
    if (not isinstance(body, dict) or set(body) != required or body["v"] != TOKEN_VERSION
            or body["k"] not in TOKEN_KINDS or not isinstance(body["o"], int)
            or isinstance(body["o"], bool) or body["o"] < 0
            or not all(isinstance(body[n], str) for n in ("g", "c", "a", "f", "u", "b"))
            or not isinstance(body["l"], int) or isinstance(body["l"], bool)):
        raise PopulationError("malformed_token")
    return body


def unverified_kind(token: str) -> str | None:
    """The kind claimed by a well-formed token whose signature was NOT recognised.

    Used ONLY to choose between the page-cursor and original-reference answers for a
    stale/forged token; it grants nothing and discloses nothing (same body either way).
    """
    try:
        encoded = token.split(".")[0]
        body = json.loads(base64.urlsafe_b64decode(
            (encoded + "=" * (-len(encoded) % 4)).encode("ascii")).decode("ascii"))
    except (ValueError, UnicodeError, AttributeError):
        return None
    kind = body.get("k") if isinstance(body, dict) else None
    return kind if kind in TOKEN_KINDS else None


def compatibility_tuple(*, generation_id: str, content_id: str, published_at: str,
                        source_session: str, qualification: str, read_captured_at: str,
                        member_sha256: Mapping[str, str], population: Population,
                        ref: str, currentness: str,
                        ref_durable: bool = False) -> dict[str, Any]:
    """The captured Sector context a downstream engine binds as a TUPLE.

    Coherence is this tuple, not equal generation strings: the owner reference,
    identity, basis, clocks, population, claims and correction/rights groups below
    are retained semantic groups. A group no producer emits reads ``unavailable``;
    nothing here is inferred or defaulted into a fact.
    """
    return {
        "schema": CAPTURE_SCHEMA,
        "owner_ref": {
            "owner": "sector_generation", "contract": "sector_generation.read/v1",
            "population_schema": POPULATION_SCHEMA, "basis_version": BASIS_VERSION,
            "domain": "sector", "generation_id": generation_id, "content_id": content_id,
            "member_sha256": dict(member_sha256),
            "consumer_content_sha256": population.content_sha256,
            "retained_resolver_ref": ref,
            # ``durable`` only when SECTOR_GENERATION_CURSOR_SECRET is configured (the
            # signing key survives a restart / other worker). Otherwise the reference
            # is valid for THIS process only and must not be persisted as durable.
            "retained_resolver_ref_durability": ("durable" if ref_durable
                                                 else "process_lifetime_only"),
        },
        "identity": {
            "market_profile": "us", "group_kind": "basket",
            # ONE taxonomy stamp for the whole response (Part B 3): the carried
            # industry/sub-industry labels are CURRENT-basis, and the historical
            # revision is unavailable because no point-in-time classification
            # source exists on this base - stated, never guessed.
            "taxonomy_revision": {
                "status": "unavailable",
                "reason": "no_point_in_time_classification_source",
                "labels_basis": "current_not_point_in_time",
                "labels": ["industry", "sub_industry"],
            },
            # Current-basis only: a label from today's classification, NEVER the
            # member's point-in-time or original classification.
            "industry_classification": dict(population.industry_classification),
            "sub_industry_classification": dict(population.sub_industry_classification),
            "membership_effective_time": "per_row_effective_on",
            # Point-in-time membership facts (Part B), captured in the generation
            # from the owner's PIT store - never read at request time.
            "membership_first_known": dict(population.first_known),
            "membership_snapshot": dict(population.membership_snapshot),
            "original_affiliation_set": dict(UNAVAILABLE_NOT_PRODUCED),
        },
        "basis": {"benchmark": "SPY", "price_basis": "not_declared_by_generation",
                  "weighting": "per_group", "currency": dict(UNAVAILABLE_NOT_PRODUCED)},
        "clocks": {"source_session": source_session, "published_at": published_at,
                   "read_captured_at": read_captured_at,
                   "decision_cutoff": dict(UNAVAILABLE_NOT_PRODUCED),
                   "qualification": qualification},
        "population": {
            # Denominator = the owner's configured CURRENT roster (configured minus
            # removed), captured per group in baskets.json ``observation``. Every
            # configured current member is either a served row or an identified
            # ``unserved`` entry with a closed reason. All counts are computed.
            "configured_current": population.configured_current,
            "served": population.served,
            "accounted_unserved": population.accounted_unserved,
            "unaccounted": population.unaccounted,
            "unserved_members": [dict(u) for u in population.unserved],
            "unserved_reasons": list(UNSERVED_REASONS),
            "unserved_reason_note": ("every reason except unaccounted_by_owner is owner "
                                     "evidence from the captured observation; "
                                     "unaccounted_by_owner entries are NOT explained"),
            "removed_members": dict(population.removed),
            "complete": population.complete,
            "complete_rule": "served + accounted_unserved == configured_current and unaccounted == 0",
            # R4-N4: whether the carried roster's as_of equals the capture's own
            # single effective session; any disagreement also nulls complete above.
            "roster_clock": dict(population.roster_clock),
            "eligible": dict(UNAVAILABLE_NOT_PRODUCED),
            "measured": dict(UNAVAILABLE_NOT_PRODUCED),
            "entitled_visibility_scope": "entitled_full", "groups": len(population.groups),
        },
        "claims": {"class": "observed_membership_listing", "forecast": "none",
                   "authority": {"may_rank": False, "may_gate": False, "may_size": False,
                                 "may_trade": False}},
        "correction_rights": {"original_identity": {"generation_id": generation_id,
                                                    "content_id": content_id},
                              "correction_lineage": dict(UNAVAILABLE_NOT_PRODUCED),
                              "current_access": "entitled"},
        "currentness": currentness,
    }
