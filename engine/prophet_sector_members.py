"""Prophet × Sector Intelligence member join — ``prophet.sector_members/v1``.

Scope
-----
A PURE projection joining exactly two captured owners, plus one optional third:

* the Sector generation's full member population (``lib.sector_population``'s
  :class:`~lib.sector_population.Population` over one captured generation);
* the Prophet index (``site/prophet/index.json``, plans keyed by ``asset``);
* optional early observations (the B03 turn-watch projection digested to one
  ``{kind, asof}`` per ticker by the route).

No I/O, no clock, no auth, no ranking, no gating, no scoring and no writing.
The join key is the US listing ticker, normalised identically on both sides.
Descriptive only: nothing here is a trade permission, a rank input or a gate
on any Prophet plan (the P3 non-interference law; ``tests/test_prophet_sector_members.py``
pins that the parsed index is never mutated).

Shape tolerance
---------------
The Sector population shape is lane 1's ``lib/sector_population.py``.  Later
population revisions may carry point-in-time membership facts
(``first_known`` / ``membership_snapshot``) that earlier shapes do not; this
module reads them with :func:`getattr` and degrades to the current-roster
shape when absent, stating which basis is actually true in
``disclosure.membership_basis`` — never a guessed point-in-time date.

Honesty law
-----------
A measure no owner produces is ``null`` plus a reason, never a default number.
Membership is the owner's CURRENT roster unless the carried PIT block says
otherwise.  Resolved-plan ``outcome``/``resolved_on`` live in the forward
ledger (``data/prophet/ledger.jsonl``), which this join deliberately does not
read; both fields stay ``null`` with that reason rather than being recomputed
from display copy.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "prophet.sector_members/v1"

#: Sort rank of each member Prophet state (contract order).
STATE_RANK = {"open_plan": 0, "early_observation": 1, "resolved_plan": 2,
              "none": 3, "unavailable": 4}
STATES = tuple(STATE_RANK)
DEFAULT_LIMIT = 100
MAX_LIMIT = 200

#: The perf window used for group context.  ``baskets.json``'s owner (``engine/baskets.py``)
#: states returns at 1d/5d/10d/20d/60d/mtd/ytd/full — TRADING-DAY windows, so the
#: 20-session window is the owner's ``"20d"`` block, verbatim, never a recompute.
PERF_WINDOW = "20d"
PERF_WINDOW_SESSIONS = 20

#: Direction vocabulary: the index states BULL/BEAR; the wire contract states
#: long/short.  This is the whole closed mapping — anything else reads ``null``.
_DIRECTION = {"BULL": "long", "BEAR": "short"}

#: Closed reason vocabulary for null context measures.
REASON_NOT_PRODUCED = "not_produced"
REASON_OWNER_REFUSED = "owner_refused_by_owner_observation"
REASON_NOT_CARRIED = "not_carried_on_population_capture"
REASON_NO_PLAN = "no_plan_in_index"
REASON_PROPHET_UNAVAILABLE = "prophet_unavailable"

MEMBERSHIP_BASIS_CURRENT = "current_roster_not_point_in_time"
MEMBERSHIP_BASIS_PIT = "current_roster_with_pit_first_known"

_OBSERVATION_KIND = "turn_watch"


class SectorMembersError(ValueError):
    """A closed join-contract failure (bad query shapes), never owner data."""


def _text(value: Any, limit: int = 200) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= limit:
        return value
    return None


def _day(value: Any) -> str | None:
    return value if isinstance(value, str) and len(value) == 10 \
        and value[:4].isdigit() and value[4] == "-" and value[7] == "-" else None


def normalize_ticker(value: Any) -> str:
    """The join key: a US listing ticker, upper-cased and trimmed.

    Prophet ``asset`` and Sector ``symbol`` are both plain US listing tickers;
    ``=``/``^``-style library stems (``engine.prophet_board_read.safe_ticker``)
    do not occur in either population today, so the normalisation is the
    minimal shared one and any collision would surface as a reported duplicate,
    never a silent merge.
    """
    return str(value or "").strip().upper()


def _finite_pct(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and math.isfinite(value):
        return round(float(value) * 100.0, 4)
    return None


# --- Prophet index digest -----------------------------------------------------


def digest_index(index: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """One structured read of the parsed index, or ``None`` when unusable.

    A plan row without a usable ``asset`` is counted and skipped (never guessed
    onto another ticker); ``plan_count`` is the number of rows actually joined,
    which is the population this contract speaks about.
    """
    if not isinstance(index, Mapping) or not isinstance(index.get("plans"), list):
        return None
    plans: dict[str, list[dict[str, Any]]] = {}
    skipped = 0
    open_count = 0
    for row in index["plans"]:
        if not isinstance(row, Mapping):
            skipped += 1
            continue
        asset = normalize_ticker(row.get("asset"))
        if not asset:
            skipped += 1
            continue
        plans.setdefault(asset, []).append(dict(row))
        if row.get("closed") is False:
            open_count += 1
    return {
        "schema": _text(index.get("schema"), 40),
        "asof": _day(index.get("asof")),
        "generated_at": _text(index.get("computed_at"), 40),
        "mixed_vintage": bool(index.get("source_mixed_vintage")),
        "plans": plans,
        "plan_count": sum(len(v) for v in plans.values()),
        "open_plan_count": open_count,
        "skipped_rows": skipped,
    }


def _recent(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """The most recent plan of a set by the owner's own clocks (signal, then id)."""
    if not rows:
        return None
    return max(rows, key=lambda p: (str(p.get("signal_date") or ""), str(p.get("id") or "")))


def _plan_block(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(plan.get("id"), 64),
        "direction": _DIRECTION.get(str(plan.get("direction") or "")) ,
        "strategy": _text(plan.get("strategy"), 40) if plan.get("strategy") else None,
        "phase": _text(plan.get("phase"), 40),
        "opened_on": _day(plan.get("signal_date")) or _day(plan.get("formation_date")),
        # The outcome owner is the forward ledger (data/prophet/ledger.jsonl),
        # deliberately not read by this join: both stay null, never recomputed.
        "resolved_on": None,
        "outcome": None,
    }


def prophet_state(asset: str, book: Mapping[str, Any] | None,
                  observations: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    """One member's Prophet state under the contract precedence
    ``open_plan > early_observation > resolved_plan > none``."""
    if book is None:
        # The wire types both plan counts as integers (contract MemberProphet;
        # the Terminal decoder refuses null). With no index read there is no
        # plan to count, and ``state:"unavailable"`` + reason says why — the
        # zeros are only ever read beside that state (amendment A3-1).
        return {"state": "unavailable", "reason": REASON_PROPHET_UNAVAILABLE,
                "plan": None, "open_plan_count": 0, "resolved_plan_count": 0,
                "observation": None}
    rows = book["plans"].get(asset) or []
    open_rows = [p for p in rows if p.get("closed") is False]
    resolved_rows = [p for p in rows if p.get("closed") is True]
    observation = observations.get(asset) if observations is not None else None
    if open_rows:
        state, plan = "open_plan", _plan_block(_recent(open_rows))
    elif observation is not None:
        state, plan = "early_observation", None
    elif resolved_rows:
        state, plan = "resolved_plan", _plan_block(_recent(resolved_rows))
    else:
        state, plan = "none", None
    return {
        "state": state,
        "reason": None if state != "none" else REASON_NO_PLAN,
        "plan": plan,
        "open_plan_count": len(open_rows),
        "resolved_plan_count": len(resolved_rows),
        "observation": dict(observation) if observation is not None else None,
    }


# --- Group context (from the same captured generation bytes) -------------------


def _group_context(group: Mapping[str, Any], *, baskets: Mapping[str, Any] | None,
                   central: Mapping[str, Any] | None) -> dict[str, Any]:
    """Nullable per-group measures; every null carries a sibling reason.

    ``baskets``/``central`` are the SAME generation's parsed member bytes the
    population was built from (the route captures them once with everything
    else).  GroupContext is the contract's one ``open`` object: the extra
    ``window``/``basis`` fields keep the measure provenance readable.
    """
    reasons: dict[str, str] = {}
    gid = group["group_id"]

    def absent(reason: str) -> dict[str, Any]:
        for field in ("group_return_pct", "market_return_pct", "relative_pp", "breadth"):
            reasons[field] = reason
        return {"window_sessions": None, "group_return_pct": None,
                "market_return_pct": None, "relative_pp": None, "breadth": None,
                "state_label": None, "reasons": reasons,
                "window": None, "basis": None}

    if group.get("refused_by_owner"):
        reasons["window_sessions"] = REASON_OWNER_REFUSED
        return absent(REASON_OWNER_REFUSED)
    entry = None
    if isinstance(baskets, Mapping) and isinstance(baskets.get("baskets"), list):
        for candidate in baskets["baskets"]:
            if isinstance(candidate, Mapping) and candidate.get("id") == gid:
                entry = candidate
                break
    row = None
    if isinstance(central, Mapping) and isinstance(central.get("baskets"), list):
        for candidate in central["baskets"]:
            if isinstance(candidate, Mapping) and candidate.get("id") == "b-" + gid:
                row = candidate
                break
    if entry is None:
        reasons["window_sessions"] = REASON_NOT_CARRIED
        return absent(REASON_NOT_CARRIED)
    perf = entry.get("perf")
    window = perf.get(PERF_WINDOW) if isinstance(perf, Mapping) else None
    ret = rel = None
    if isinstance(window, Mapping):
        ret, rel = _finite_pct(window.get("ret")), _finite_pct(window.get("rel"))
    state = row.get("state") if isinstance(row, Mapping) else None
    state_label = _text(state.get("phase"), 40) if isinstance(state, Mapping) else None
    context = {
        "window_sessions": PERF_WINDOW_SESSIONS,
        "group_return_pct": ret,
        # market = ret − rel: the owner's own additive definition of ``rel``
        # (engine/baskets.py: ``rel = ret − bench_ret`` over SPY), so the
        # benchmark return is recovered, not invented.
        "market_return_pct": round(ret - rel, 4) if ret is not None and rel is not None else None,
        "relative_pp": rel,
        "breadth": None,
        "state_label": state_label,
        "reasons": reasons,
        "window": PERF_WINDOW,
        "basis": "baskets.json perf." + PERF_WINDOW
                 + " (owner trading-day window); market_return = ret - rel",
    }
    if ret is None:
        reasons["group_return_pct"] = REASON_NOT_PRODUCED
    if rel is None:
        reasons["relative_pp"] = REASON_NOT_PRODUCED
    if context["market_return_pct"] is None:
        reasons["market_return_pct"] = REASON_NOT_PRODUCED
    reasons["breadth"] = REASON_NOT_PRODUCED  # no per-member breadth owner today
    if state_label is None:
        reasons["state_label"] = REASON_NOT_PRODUCED
    return context


# --- Counts --------------------------------------------------------------------


def _group_counts(population: Any, group: Mapping[str, Any],
                  rows_by_group: Mapping[str, Sequence[Mapping[str, Any]]],
                  unserved_by_group: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    served = len(rows_by_group.get(group["group_id"]) or ())
    accounted = sum(1 for u in unserved_by_group.get(group["group_id"]) or ()
                    if u.get("reason") != "unaccounted_by_owner")
    unaccounted = sum(1 for u in unserved_by_group.get(group["group_id"]) or ()
                      if u.get("reason") == "unaccounted_by_owner")
    configured = group.get("n_configured_current")
    if isinstance(configured, int) and not isinstance(configured, bool):
        residual = configured - served - accounted - unaccounted
        if residual > 0:
            # A configured member the owner neither served nor explained: an
            # unaccounted gap, reported — never silently dropped.
            unaccounted += residual
    else:
        configured = None
    return {"configured": configured, "served": served,
            "accounted_unserved": accounted, "unaccounted": unaccounted,
            "open_plan": 0, "resolved_plan": 0, "early_observation": 0,
            "none": 0, "unavailable": 0}


def _state_counts(members: Sequence[Mapping[str, Any]], counts: dict[str, Any]) -> dict[str, Any]:
    for member in members:
        counts[member["prophet"]["state"]] += 1
    return counts


# --- The join -------------------------------------------------------------------


class SectorMembersJoin:
    """One captured population joined to one Prophet index digest."""

    def __init__(self, *, population: Any, capture: Mapping[str, Any],
                 index: Mapping[str, Any] | None, index_sha256: str | None,
                 baskets: Mapping[str, Any] | None = None,
                 central: Mapping[str, Any] | None = None,
                 observations: Mapping[str, Mapping[str, Any]] | None = None,
                 captured_at: str = "") -> None:
        self.population = population
        self.capture = dict(capture)
        self.book = digest_index(index)
        self.index_sha256 = index_sha256
        self._baskets = baskets
        self._central = central
        self._observations = observations
        self.captured_at = _text(captured_at, 40) or ""
        self._rows = list(getattr(population, "rows", ()) or ())
        self._groups = list(getattr(population, "groups", ()) or ())
        self._unserved = list(getattr(population, "unserved", ()) or ())
        self._rows_by_group: dict[str, list[Mapping[str, Any]]] = {}
        for row in self._rows:
            self._rows_by_group.setdefault(row["group_id"], []).append(row)
        self._unserved_by_group: dict[str, list[Mapping[str, Any]]] = {}
        for entry in self._unserved:
            self._unserved_by_group.setdefault(entry["group_id"], []).append(entry)
        # PIT first-known (later population shapes only): degrade when absent.
        first_known = getattr(population, "first_known", None)
        self._first_known = (first_known.get("groups")
                             if isinstance(first_known, Mapping)
                             and first_known.get("status") == "available"
                             and isinstance(first_known.get("groups"), Mapping) else None)
        self._symbol_groups: dict[str, list[str]] = {}
        for row in self._rows:
            self._symbol_groups.setdefault(normalize_ticker(row["symbol"]), [])
        for row in self._rows:
            key = normalize_ticker(row["symbol"])
            if row["group_id"] not in self._symbol_groups[key]:
                self._symbol_groups[key].append(row["group_id"])

    # -- disclosure ----------------------------------------------------------

    def membership_basis(self) -> str:
        return MEMBERSHIP_BASIS_PIT if self._first_known is not None else MEMBERSHIP_BASIS_CURRENT

    def taxonomy_basis(self) -> str:
        meta = getattr(self.population, "industry_classification", None)
        if isinstance(meta, Mapping) and meta.get("status") == "available":
            return _text(meta.get("basis"), 160) or _text(meta.get("taxonomy"), 40) \
                or "current_basis_industry_labels"
        return "unavailable: " + str(meta.get("reason") or "not_produced") \
            if isinstance(meta, Mapping) else "unavailable: not_produced"

    def _first_known_for(self, group_id: str, symbol: str) -> str | None:
        if self._first_known is None:
            return None
        bucket = self._first_known.get(group_id)
        if not isinstance(bucket, Mapping):
            return None
        day = bucket.get(symbol)
        return _day(day)

    # -- envelope ------------------------------------------------------------

    def sector_ref(self) -> dict[str, Any] | None:
        if not self.capture.get("generation_id"):
            return None
        member_sha = None
        if isinstance(self.capture.get("member_sha256"), Mapping):
            # One combined digest over the exact captured member bytes (name→sha
            # pairs, sorted) — the single-string form this wire carries.
            import hashlib
            import json
            material = json.dumps(dict(sorted(self.capture["member_sha256"].items())),
                                  sort_keys=True, separators=(",", ":")).encode()
            member_sha = hashlib.sha256(material).hexdigest()
        return {"owner": "sector_generation",
                "generation_id": self.capture.get("generation_id"),
                "content_id": self.capture.get("content_id"),
                "source_session": self.capture.get("source_session"),
                "published_at": self.capture.get("published_at"),
                "member_sha256": member_sha,
                "qualification": self.capture.get("qualification")}

    def prophet_ref(self) -> dict[str, Any] | None:
        if self.book is None:
            return None
        return {"owner": "prophet_index", "schema": self.book["schema"],
                "asof": self.book["asof"], "generated_at": self.book["generated_at"],
                "index_sha256": self.index_sha256,
                "plan_count": self.book["plan_count"],
                "open_plan_count": self.book["open_plan_count"]}

    def compatibility(self) -> dict[str, Any]:
        sector = self.sector_ref()
        prophet = self.prophet_ref()
        if sector is None:
            return {"status": "sector_unavailable", "sector_session": None,
                    "prophet_asof": prophet["asof"] if prophet else None,
                    "session_gap": None,
                    "reason": "sector_generation_unavailable"}
        if prophet is None:
            return {"status": "prophet_unavailable",
                    "sector_session": sector["source_session"], "prophet_asof": None,
                    "session_gap": None, "reason": "prophet_index_unavailable"}
        sector_day, prophet_day = sector["source_session"], prophet["asof"]
        if not _day(sector_day) or not _day(prophet_day):
            return {"status": "mixed_basis", "sector_session": sector_day,
                    "prophet_asof": prophet_day, "session_gap": None,
                    "reason": "session_clock_not_readable"}
        from datetime import date
        gap = (date.fromisoformat(prophet_day) - date.fromisoformat(sector_day)).days
        qualification = sector.get("qualification")
        if gap == 0:
            status, reason = "compatible", None
        elif qualification in ("stale", "degraded") or self.book["mixed_vintage"]:
            status = "mixed_basis"
            reason = (f"sessions differ by {abs(gap)} calendar days and an owner flags "
                      f"a non-accepted basis (sector qualification {qualification!r}"
                      + (", prophet source_mixed_vintage" if self.book["mixed_vintage"] else "")
                      + ")")
        elif gap > 0:
            status = "stale_sector"
            reason = f"sector_session {gap} calendar days behind prophet_asof"
        else:
            status = "stale_prophet"
            reason = f"prophet_asof {-gap} calendar days behind sector_session"
        return {"status": status, "sector_session": sector_day,
                "prophet_asof": prophet_day, "session_gap": gap, "reason": reason}

    def disclosure(self) -> dict[str, Any]:
        return {"membership_basis": self.membership_basis(),
                "taxonomy_basis": self.taxonomy_basis(),
                "join_key": "us_listing_ticker", "descriptive_only": True}

    def envelope(self, mode: str) -> dict[str, Any]:
        return {"schema": SCHEMA, "mode": mode, "captured_at": self.captured_at,
                "sector_ref": self.sector_ref(), "prophet_ref": self.prophet_ref(),
                "compatibility": self.compatibility(), "disclosure": self.disclosure()}

    # -- members ----------------------------------------------------------------

    def member(self, row: Mapping[str, Any]) -> dict[str, Any]:
        key = normalize_ticker(row["symbol"])
        groups = self._symbol_groups.get(key) or []
        gid = row["group_id"]
        return {
            "symbol": row["symbol"],
            "name": _text(row.get("name")),
            "industry": (row.get("industry") or {}).get("label")
            if isinstance(row.get("industry"), Mapping)
            and (row.get("industry") or {}).get("status") == "available" else None,
            "sub_industry": (row.get("sub_industry") or {}).get("label")
            if isinstance(row.get("sub_industry"), Mapping)
            and (row.get("sub_industry") or {}).get("status") == "available" else None,
            "member_since": _day((row.get("membership") or {}).get("effective_on"))
            if isinstance(row.get("membership"), Mapping) else None,
            "first_known": self._first_known_for(gid, row["symbol"]),
            "also_in_groups": [g for g in groups if g != gid],
            "prophet": prophet_state(key, self.book, self._observations),
        }

    def group_descriptor(self, group: Mapping[str, Any]) -> dict[str, Any]:
        central = self._central if isinstance(self._central, Mapping) else {}
        measured = central.get("measured_read") if isinstance(central.get("measured_read"), Mapping) else {}
        generation = measured.get("generation") if isinstance(measured.get("generation"), Mapping) else {}
        benchmark = _text(generation.get("benchmark"), 16) if generation else None
        return {"id": group["group_id"], "kind": "basket",
                "name": _text(group.get("name")), "name_zh": _text(group.get("name_zh")),
                "benchmark": benchmark,
                "context": _group_context(group, baskets=self._baskets, central=self._central)}

    def known_group(self, group_id: str) -> Mapping[str, Any] | None:
        for group in self._groups:
            if group["group_id"] == group_id:
                return group
        return None

    # -- modes ----------------------------------------------------------------

    def index_view(self) -> dict[str, Any]:
        groups = []
        for group in sorted(self._groups, key=lambda g: str(g["group_id"])):
            counts = _state_counts(
                [self.member(r) for r in self._rows_by_group.get(group["group_id"]) or ()],
                _group_counts(self.population, group, self._rows_by_group, self._unserved_by_group))
            descriptor = self.group_descriptor(group)
            groups.append({**descriptor, "counts": counts})
        # Totals de-duplicate by symbol across groups (contract).
        symbols = sorted({normalize_ticker(r["symbol"]) for r in self._rows})
        accounted = {normalize_ticker(u["symbol"]) for u in self._unserved
                     if u.get("reason") != "unaccounted_by_owner"} - set(symbols)
        unaccounted = {normalize_ticker(u["symbol"]) for u in self._unserved
                       if u.get("reason") == "unaccounted_by_owner"} - set(symbols)
        totals = {"configured": (len(symbols) + len(accounted) + len(unaccounted))
                  if symbols or accounted or unaccounted else None,
                  "served": len(symbols), "accounted_unserved": len(accounted),
                  "unaccounted": len(unaccounted),
                  "open_plan": 0, "resolved_plan": 0, "early_observation": 0,
                  "none": 0, "unavailable": 0}
        if self.book is None:
            totals["unavailable"] = len(symbols)
        else:
            states = {}
            for symbol in symbols:
                state = prophet_state(symbol, self.book, self._observations)["state"]
                states[state] = states.get(state, 0) + 1
            for state, count in states.items():
                totals[state] = count
        return {**self.envelope("index"), "groups": groups, "totals": totals}

    def group_view(self, group_id: str, *, offset: int = 0, limit: int = DEFAULT_LIMIT,
                   query: str | None = None, state: str | None = None) -> dict[str, Any] | None:
        """``None`` when the capture does not know this group (route answers 404).

        The one exception is the fail-closed sector-unavailable shape (amendment
        A1-9): with no capture there is no roster to know a group against, so the
        answer is the honest 200 envelope — ``group:null``, empty members,
        ``counts.configured:null`` — never a 404 that would imply the group does
        not exist.
        """
        group = self.known_group(group_id)
        if group is None:
            if not self._groups and not self.capture:
                return {**self.envelope("group"), "group": None,
                        "counts": {"configured": None, "served": 0,
                                   "accounted_unserved": 0, "unaccounted": 0,
                                   "open_plan": 0, "resolved_plan": 0,
                                   "early_observation": 0, "none": 0, "unavailable": 0},
                        "members": [], "unserved": [],
                        "page": {"offset": offset, "limit": limit, "total_matching": 0,
                                 "next_offset": None, "q": query or None, "state": state}}
            return None
        rows = self._rows_by_group.get(group_id) or ()
        members = [self.member(r) for r in rows]
        if self.book is None:
            for member in members:
                member["prophet"] = prophet_state(normalize_ticker(member["symbol"]),
                                                  None, None)
        needle = query.strip().casefold() if query else None
        if needle:
            # Search BEFORE paging, over symbol and name.
            members = [m for m in members if needle in m["symbol"].casefold()
                       or needle in (m["name"] or "").casefold()]
        if state is not None:
            if state not in STATE_RANK:
                raise SectorMembersError("invalid_state")
            members = [m for m in members if m["prophet"]["state"] == state]
        members.sort(key=lambda m: (STATE_RANK[m["prophet"]["state"]],
                                    normalize_ticker(m["symbol"]), str(m["symbol"])))
        total = len(members)
        page = members[offset:offset + limit]
        counts = _state_counts([self.member(r) for r in rows],
                               _group_counts(self.population, group,
                                             self._rows_by_group, self._unserved_by_group))
        unserved = [{"symbol": u["symbol"], "reason": u.get("reason")}
                    for u in self._unserved_by_group.get(group_id) or ()]
        next_offset = offset + len(page) if offset + len(page) < total else None
        return {**self.envelope("group"),
                "group": self.group_descriptor(group),
                "counts": counts, "members": page, "unserved": unserved,
                "page": {"offset": offset, "limit": limit, "total_matching": total,
                         "next_offset": next_offset,
                         "q": query or None, "state": state}}

    def symbol_view(self, symbol: str) -> dict[str, Any]:
        key = normalize_ticker(symbol)
        member_of = []
        for row in self._rows:
            if normalize_ticker(row["symbol"]) != key:
                continue
            group = self.known_group(row["group_id"])
            if group is None:
                continue
            member_of.append({"group": self.group_descriptor(group),
                              "member": self.member(row)})
        member_of.sort(key=lambda m: m["group"]["id"])
        return {**self.envelope("symbol"), "symbol": key, "member_of": member_of,
                "prophet": prophet_state(key, self.book, self._observations)}
