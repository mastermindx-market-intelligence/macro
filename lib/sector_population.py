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
import hashlib
import hmac
import json
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
_QUERY = re.compile(r"[\w .&'\-]{1,64}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_\-]+\.[0-9a-f]{64}\Z")
_ACTION_LANES = ("buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid")
UNAVAILABLE_NOT_PRODUCED = {"status": "unavailable", "reason": "not_produced"}


class PopulationError(ValueError):
    """A closed population-contract failure; never embeds private data."""


@dataclass(frozen=True)
class Population:
    groups: tuple[Mapping[str, Any], ...]
    rows: tuple[Mapping[str, Any], ...]
    content_sha256: str
    expected_members: int
    admitted_members: int
    missing_members: int


def _text(value: Any, limit: int = 160) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= limit:
        return value
    return None


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
    symbol_groups: Counter[str] = Counter()
    for group in groups_in:
        for member in (group.get("members") if isinstance(group, Mapping) else None) or ():
            if isinstance(member, Mapping) and isinstance(member.get("symbol"), str):
                symbol_groups[member["symbol"]] += 1
    groups: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    missing_total = 0
    expected_total = 0
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
            rows.append({
                "ordinal": len(rows), "group_id": gid, "symbol": symbol,
                "name": _text(member.get("name")),
                "membership": {"status": "listed",
                               "effective_on": added if isinstance(added, str) and len(added) <= 10 else None},
                "also_in_groups": symbol_groups[symbol] - 1,
                "in_handoff_member_set": None if handoff_set is None else symbol in handoff_set,
                "prophet_eligibility": dict(UNAVAILABLE_NOT_PRODUCED),
                "visibility": {"scope": "entitled_full"},
            })
            if len(rows) > MAX_ROWS:
                raise PopulationError("population_too_large")
        declared = group.get("n_members")
        missing = group.get("missing") if isinstance(group.get("missing"), list) else []
        if isinstance(declared, int) and not isinstance(declared, bool):
            expected_total += declared
        else:
            declared = None
        missing_total += len(missing)
        groups.append({
            "group_id": gid, "kind": "basket", "name": _text(group.get("name")),
            "name_zh": _text(group.get("name_zh")), "category": _text(group.get("category")),
            "weighting": _text(group.get("weighting"), 40),
            "n_members_declared": declared, "n_members_listed": len(seen_symbols),
            "n_missing": len(missing),
            "membership_coverage": coverage.get("b-" + gid, dict(UNAVAILABLE_NOT_PRODUCED)),
            "action": actions.get(gid, {"status": "unavailable", "reason": "no_action_row"}),
            "native_sector_ref": dict(UNAVAILABLE_NOT_PRODUCED),
        })
    canonical = json.dumps({"groups": groups, "rows": rows}, allow_nan=False, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return Population(tuple(groups), tuple(rows), hashlib.sha256(canonical).hexdigest(),
                      expected_total, len(rows), missing_total)


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


def actor_digest(actor: str | None) -> str:
    return hashlib.sha256(("sector-actor:" + (actor or "anonymous")).encode("utf-8")).hexdigest()


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
    groups = [g for g in population.groups if g["group_id"] in wanted]
    next_offset = offset + len(page) if offset + len(page) < total else None
    return page, groups, total, next_offset


# --- signed continuation tokens ------------------------------------------------

_PROCESS_KEY = os.urandom(32)
_KEY_DOMAIN = b"macro.sector_population.cursor.v1"


def _key() -> bytes:
    configured = os.environ.get("SECTOR_GENERATION_CURSOR_SECRET")
    if configured is None:
        return _PROCESS_KEY
    raw = configured.encode("utf-8")
    if len(raw) < 32:
        raise PopulationError("cursor_secret_invalid")
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


def compatibility_tuple(*, generation_id: str, content_id: str, published_at: str,
                        source_session: str, qualification: str, read_captured_at: str,
                        member_sha256: Mapping[str, str], population: Population,
                        ref: str, currentness: str) -> dict[str, Any]:
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
        },
        "identity": {
            "market_profile": "us", "group_kind": "basket",
            "taxonomy_revision": dict(UNAVAILABLE_NOT_PRODUCED),
            "membership_effective_time": "per_row_effective_on",
            "membership_first_known": dict(UNAVAILABLE_NOT_PRODUCED),
            "original_affiliation_set": dict(UNAVAILABLE_NOT_PRODUCED),
        },
        "basis": {"benchmark": "SPY", "price_basis": "not_declared_by_generation",
                  "weighting": "per_group", "currency": dict(UNAVAILABLE_NOT_PRODUCED)},
        "clocks": {"source_session": source_session, "published_at": published_at,
                   "read_captured_at": read_captured_at,
                   "decision_cutoff": dict(UNAVAILABLE_NOT_PRODUCED),
                   "qualification": qualification},
        "population": {
            "expected": population.expected_members, "admitted": population.admitted_members,
            "missing": population.missing_members, "eligible": dict(UNAVAILABLE_NOT_PRODUCED),
            "measured": dict(UNAVAILABLE_NOT_PRODUCED),
            "entitled_visibility_scope": "entitled_full", "groups": len(population.groups),
            # The LISTING is complete when the owner's own declared member counts
            # equal the listed rows. ``missing`` counts listed members the owner
            # reports without a usable measurement; they stay listed, never dropped.
            "complete": population.expected_members == population.admitted_members,
            "missing_reason": ("owner_reported_missing_members"
                               if population.missing_members else None),
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
