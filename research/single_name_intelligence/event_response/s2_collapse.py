"""S2 collapse: IL §3 steps 0..4 (A22) — run IN FULL before anything is counted.

Step 0 admission + listed exclusions -> step 1 counter collapse (issuer group)
-> step 2 duplicate/programme dedup -> step 3 same-session bundle (confounded
flags) -> step 4 per-h greedy overlap absorption. Nothing is dropped silently:
every removal is returned as a listed exclusion with its ids and reason.

The collapse consumes ONLY event metadata (ids, families, timestamps, session
dates). Prices are never an input here.

Exclusion ordering (frozen in the seal): rows carrying an inadmissible
TIMESTAMP_QUALITY and rows excluded for a named coverage gap are removed
BEFORE episode formation; they appear in the census and in the visible
exclusion counts, and never open, join or absorb an episode.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from s2_seal import FAMILY_PRECEDENCE, GRADED_ISSUER as GRADED_ISSUER_KEY

ADMISSIBLE_QUALITIES = ("CRAWL_BOUNDED", "PUBLISHER_STATED", "DISCLOSURE_DATE")


@dataclass
class EventRecord:
    """One occurrence that survives step 2, anchored at its earliest t_avail."""
    issuer_key: str
    family: str
    t_avail_utc: str                 # ISO-8601 of the earliest admissible t_avail
    evidence_pointer: str            # opener row pointer
    s_us: str
    s_hk: str
    member_ids: list[str] = field(default_factory=list)
    programme: str | None = None     # programme grouping key (one programme = one event)
    member_families: list[str] = field(default_factory=list)


@dataclass
class ListedExclusion:
    id: str
    issuer_key: str
    family: str | None
    reason: str
    step: str                        # which IL §3 step listed it
    family_scope: str | None = None  # protocol family whose blocks list it


@dataclass
class Episode:
    """The unit of analysis (per h): the opener plus absorbed members."""
    opener: EventRecord
    horizon: int
    absorbed: list[EventRecord] = field(default_factory=list)

    @property
    def confounded(self) -> bool:
        return len(self.opener.member_families) > 1

    @property
    def absorbed_count(self) -> int:
        return len(self.absorbed)


def _session_index_map(dates: list[str]) -> dict[str, int]:
    return {d: i for i, d in enumerate(sorted(dates))}


def step0_admit(rows: list[dict], graded_issuer: str) -> tuple[list[dict], list[ListedExclusion]]:
    """Step 0: admission. A row enters only through an admitted counter with an
    admissible TIMESTAMP_QUALITY; everything else is excluded and listed.
    family_scope names the graded-issuer protocol family whose blocks list the
    exclusion; census-only-issuer exclusions carry no family scope."""
    kept, excluded = [], []
    for r in rows:
        scope = r.get("family") if r["issuer_key"] == graded_issuer else None
        reason = r.get("listed_exclusion_reason")
        if r.get("disposition") == "EXCLUDED_AND_LISTED" and reason:
            excluded.append(ListedExclusion(
                id=r["id"], issuer_key=r["issuer_key"],
                family=r.get("family"), reason=reason, step="step0_admission",
                family_scope=scope))
            continue
        if r.get("t_avail_quality") not in ADMISSIBLE_QUALITIES:
            excluded.append(ListedExclusion(
                id=r["id"], issuer_key=r["issuer_key"],
                family=r.get("family"),
                reason=(f"TIMESTAMP_QUALITY {r.get('t_avail_quality')!r} is not "
                        "admissible (IL §1)"),
                step="step0_admission",
                family_scope=scope))
            continue
        kept.append(r)
    return kept, excluded


def step1_counter_collapse(rows: list[dict]) -> dict[str, list[dict]]:
    """Step 1: every row on any counter of an issuer group joins that group.
    Collapsing without a canonical id is allowed; linking without one is not."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["issuer_key"], []).append(r)
    return groups


def _programme_key(r: dict, programmes: list[dict]) -> str | None:
    """A row belongs to a programme when its id is listed in that programme's
    member ids. One programme = one event (REG P05); execution rows are
    evidence rows of the single programme event."""
    for p in programmes:
        if r["id"] in p["member_ids"]:
            return p["key"]
    return None


def step2_dedup(rows: list[dict],
                programmes: list[dict] | None = None) -> tuple[list[EventRecord], list[ListedExclusion]]:
    """Step 2: repeated reports of one occurrence merge into one event anchored
    at the earliest admissible t_avail; one programme merges into one event."""
    programmes = programmes or []
    by_id = {r["id"]: r for r in rows}
    consumed: set[str] = set()
    events: list[EventRecord] = []
    excluded: list[ListedExclusion] = []

    for p in programmes:
        members = [by_id[i] for i in p["member_ids"] if i in by_id]
        if not members:
            continue
        members_sorted = sorted(members, key=lambda r: (r["t_avail_utc"], r["id"]))
        opener = members_sorted[0]
        families = sorted({m["family"] for m in members})
        rec = EventRecord(
            issuer_key=opener["issuer_key"], family=opener["family"],
            t_avail_utc=opener["t_avail_utc"],
            evidence_pointer=opener["evidence_pointer"],
            s_us=opener["s_us"], s_hk=opener["s_hk"],
            member_ids=[m["id"] for m in members_sorted],
            programme=p["key"], member_families=families)
        events.append(rec)
        consumed.update(m["id"] for m in members)

    # remaining rows: group identical occurrences by (issuer, family, s_us,
    # s_hk) — repeated reports of one occurrence share the opener's sessions
    # and family; the earliest admissible t_avail anchors the event.
    rest = [r for r in rows if r["id"] not in consumed]
    rest.sort(key=lambda r: (r["t_avail_utc"], r["id"]))
    buckets: dict[tuple, list[dict]] = {}
    for r in rest:
        key = (r["issuer_key"], r["family"], r["s_us"], r["s_hk"])
        buckets.setdefault(key, []).append(r)
    for key, members in sorted(buckets.items()):
        opener = members[0]
        events.append(EventRecord(
            issuer_key=opener["issuer_key"], family=opener["family"],
            t_avail_utc=opener["t_avail_utc"],
            evidence_pointer=opener["evidence_pointer"],
            s_us=opener["s_us"], s_hk=opener["s_hk"],
            member_ids=[m["id"] for m in members],
            member_families=[opener["family"]]))
    events.sort(key=lambda e: (e.t_avail_utc, e.evidence_pointer))
    return events, excluded


def step3_bundle(events: list[EventRecord]) -> list[EventRecord]:
    """Step 3 (per issuer group — step 5 keeps groups separate): a bundle is a
    connected component of events of ONE issuer group sharing the same s on
    either clock. The event of record takes the highest-precedence family
    present and the earliest t_avail; more than one family present flags it
    confounded. Returns the events of record (bundle members folded in)."""
    if not events:
        return []
    parent = list(range(len(events)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    keys: dict[str, list[int]] = {}
    for i, e in enumerate(events):
        keys.setdefault(f"{e.issuer_key}|US:{e.s_us}", []).append(i)
        keys.setdefault(f"{e.issuer_key}|HK:{e.s_hk}", []).append(i)
    for idxs in keys.values():
        for j in idxs[1:]:
            union(idxs[0], j)

    comps: dict[int, list[int]] = {}
    for i in range(len(events)):
        comps.setdefault(find(i), []).append(i)

    out: list[EventRecord] = []
    for idxs in comps.values():
        members = [events[i] for i in idxs]
        fams = sorted({f for m in members for f in m.member_families},
                      key=lambda f: -FAMILY_PRECEDENCE.get(f, 0))
        anchor = min(members, key=lambda e: (e.t_avail_utc, e.evidence_pointer))
        merged_ids = sorted({i for m in members for i in m.member_ids})
        rec = EventRecord(
            issuer_key=anchor.issuer_key,
            family=fams[0],
            t_avail_utc=anchor.t_avail_utc,
            evidence_pointer=anchor.evidence_pointer,
            s_us=anchor.s_us, s_hk=anchor.s_hk,
            member_ids=merged_ids,
            programme=anchor.programme)
        rec.member_families = fams  # type: ignore[attr-defined]
        out.append(rec)
    out.sort(key=lambda e: (e.t_avail_utc, e.evidence_pointer))
    return out


def step4_overlap(events: list[EventRecord], h: int,
                  session_dates_us: list[str],
                  session_dates_hk: list[str]) -> tuple[list[Episode], list[EventRecord]]:
    """Step 4: per issuer group, per h, greedy. Order by t_avail; the first
    unassigned event opens an episode; a later event whose s lies inside the
    opener's W_h on EITHER clock is absorbed (recorded, never counted); no
    chaining. Returns (episodes, absorbed events)."""
    idx_us = _session_index_map(session_dates_us)
    idx_hk = _session_index_map(session_dates_hk)
    by_group: dict[str, list[EventRecord]] = {}
    for e in events:
        by_group.setdefault(e.issuer_key, []).append(e)

    episodes: list[Episode] = []
    absorbed: list[EventRecord] = []
    for issuer in sorted(by_group):
        ordered = sorted(by_group[issuer],
                         key=lambda e: (e.t_avail_utc, e.evidence_pointer))
        openers: list[Episode] = []
        for e in ordered:
            placed = False
            for ep in openers:
                if _inside(ep.opener, e, h, idx_us, idx_hk):
                    ep.absorbed.append(e)
                    absorbed.append(e)
                    placed = True
                    break
            if not placed:
                openers.append(Episode(opener=e, horizon=h))
        episodes.extend(openers)
    episodes.sort(key=lambda ep: (ep.opener.t_avail_utc, ep.opener.evidence_pointer))
    return episodes, absorbed


def _inside(opener: EventRecord, other: EventRecord, h: int,
            idx_us: dict[str, int], idx_hk: dict[str, int]) -> bool:
    """other's s lies inside the opener's W_h (sessions s..s+h inclusive) on
    either clock. Unknown dates (outside the modelled calendar span) absorb on
    no clock."""
    i = idx_us.get(opener.s_us)
    j = idx_us.get(other.s_us)
    if i is not None and j is not None and i <= j <= i + h:
        return True
    i = idx_hk.get(opener.s_hk)
    j = idx_hk.get(other.s_hk)
    if i is not None and j is not None and i <= j <= i + h:
        return True
    return False


def run_collapse(rows: list[dict], programmes: list[dict],
                 session_dates_us: list[str], session_dates_hk: list[str],
                 horizons: tuple[int, ...],
                 event_exclusions: list[dict] | None = None) -> dict:
    """IL §3 in full. Returns events of record, per-h episodes, every listed
    exclusion and the step-by-step counts (transparency only).

    event_exclusions: frozen coverage-gap exclusions applied AFTER step 2 and
    BEFORE step 3 (each names its match, ids, reason and family scope). They
    are listed, never silent; an excluded event never opens, joins or absorbs.
    """
    event_exclusions = event_exclusions or []
    kept, excluded = step0_admit(rows, GRADED_ISSUER_KEY)
    groups = step1_counter_collapse(kept)
    events: list[EventRecord] = []
    for issuer in sorted(groups):
        evs, _ = step2_dedup(groups[issuer], programmes)
        events.extend(evs)
    events_after_step2 = len(events)

    remaining: list[EventRecord] = []
    for e in events:
        rule = _matching_exclusion(e, event_exclusions)
        if rule is None:
            remaining.append(e)
            continue
        excluded.append(ListedExclusion(
            id=",".join(e.member_ids), issuer_key=e.issuer_key,
            family=e.family, reason=rule["reason"],
            step="post_step2_coverage_exclusion",
            family_scope=rule.get("family_scope")))
    events = step3_bundle(remaining)
    per_h = {}
    for h in horizons:
        eps, absorbed = step4_overlap(events, h, session_dates_us, session_dates_hk)
        per_h[h] = {"episodes": eps, "absorbed": absorbed}
    counts = {
        "literal_row_count_pre_step0": len(rows),
        "kept_after_step0": len(kept),
        "excluded_and_listed": [_exclusion_dict(e) for e in excluded],
        "events_after_step2": events_after_step2,
        "events_after_step2_and_step3": len(events),
    }
    return {"events": events, "per_h": per_h, "exclusions": excluded,
            "counts": counts}


def _exclusion_dict(e: ListedExclusion) -> dict:
    return {"id": e.id, "issuer_key": e.issuer_key, "family": e.family,
            "reason": e.reason, "step": e.step, "family_scope": e.family_scope}


def _matching_exclusion(event: EventRecord, rules: list[dict]) -> dict | None:
    for rule in rules:
        match = rule.get("match", {})
        if "programme" in match and event.programme == match["programme"]:
            return rule
        if "family" in match and event.family == match["family"]:
            return rule
    return None
