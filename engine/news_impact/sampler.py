"""Deterministic stratified sampler for the Phase 1 news-impact benchmark (600 cases).

Implements mastermindx-market-intelligence/macro masterplan sections 6-7 (the worked
examples that define the three template families: capital allocation, demand/guidance/
contract, strategic product/partnership) and section 11 (research and evaluation plan:
the stratified 600-case benchmark), per program upgrade 2, and the Phase 0 freeze record
PHASE0_FREEZE_2026-10-11.md section 6 "Benchmark sampling plan" (population, strata,
counts, caps, grouping/holdout, provenance, rights) and section 8 "Tape fit" (seendate is
the sampling clock; families are a recall net, never a label).

Laws this module obeys:
- No case is selected after reading its outcome: cells are PRE-LABEL proxies
  (``Candidate.proxy_cell``), never labels; the manifest reports them under
  ``proxy_cell`` naming via the ``cells`` table.
- The draw replays byte-identically from (tape sha, date bounds, seed, sampler
  version): no clock reads, no random module, no network; ordering is
  sha256(f"{seed}:{item_id}") within each (template, proxy_cell) bucket.
- Short cells are reported (``short = target - drawn``), never padded, never
  duplicated, never borrowed from another cell (freeze section 6).
- A cell the pool cannot fill is a fact about the pool, not an error.
- No confidence / probability / score / price_target / fair_value field exists
  anywhere in this module (standing kills KILL-LLM-CONFIDENCE et al.).

Input accounting (freeze section 6 "counted, never silently dropped"): the manifest's
``counters`` block always carries outside_window / low_value / unresolved_issuer /
rights_refused. ``draw_sample`` itself can observe outside_window and unresolved_issuer;
``low_value`` is applied upstream by ``engine.news_common.is_low_value`` (the freeze
population definition) and is reported as 0 by ``draw_sample`` — callers that measured
it rebuild the manifest through the public ``build_manifest`` with the real count, as
the dry run does. ``rights_refused`` is 0 in any completed manifest because a refused
source RAISES ``RightsRefused`` instead of being skipped (freeze section 6 "Rights":
the registry is the authority, never skip silently).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Callable, Iterable, Mapping

__all__ = [
    "SAMPLER_VERSION",
    "TEMPLATES",
    "CELLS",
    "CELL_TARGETS",
    "MEGACAPS",
    "TAG_NAMES",
    "MANIFEST_SCHEMA",
    "RightsRefused",
    "SamplerError",
    "Candidate",
    "SamplePlan",
    "Case",
    "Draw",
    "group_ids",
    "assign_folds",
    "draw_sample",
    "build_manifest",
    "load_tape",
]

# --- frozen constants (PHASE0_FREEZE_2026-10-11.md section 6) -----------------

SAMPLER_VERSION = "ni-sampler-1"
TEMPLATES = ("T1", "T2", "T3")
CELLS = ("positive", "negative", "ambiguous", "no_change")
CELL_TARGETS = {"positive": 90, "negative": 50, "ambiguous": 30, "no_change": 30}
#: The seven megacaps capped at 10% of each template's draw (freeze section 6).
MEGACAPS = frozenset({"NVDA", "MSFT", "AAPL", "GOOGL", "TSLA", "AMZN", "META"})
#: Closed tag vocabulary for the misleading-quota mechanism (freeze section 6).
TAG_NAMES = frozenset({"near_duplicate", "indirect_transfer"})

_CIK_RE = re.compile(r"^cik:[0-9]{10}$")
_WINDOW_H = timedelta(hours=72)  # issuer+title join window (freeze section 6 grouping)
_SHARE_SCALE = 1_000_000  # integer cross-multiply scale for share caps

# The D12 resolution of MEGACAPS (ticker -> EDGAR CIK identity). Used ONLY to derive
# the manifest's per-template megacap share from already-drawn cases (which carry
# issuer but not ticker) when build_manifest is called without draw-time stats.
# The draw-time cap itself uses Candidate.ticker, per the frozen spec.
_MEGACAP_CIKS = frozenset(
    {
        "cik:0000320193",  # AAPL
        "cik:0000789019",  # MSFT
        "cik:0001045810",  # NVDA
        "cik:0001652044",  # GOOGL
        "cik:0001318605",  # TSLA
        "cik:0001018724",  # AMZN
        "cik:0001326801",  # META
    }
)


class RightsRefused(Exception):
    """A candidate's source is not admitted by the rights registry (freeze section 6)."""


class SamplerError(Exception):
    """Invalid sampler input or environment (never a short cell — that is reported)."""


# --- value objects -------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One tape row eligible for the draw. ``proxy_cell`` is a PRE-LABEL proxy."""

    item_id: str
    issuer: str  # "cik:" + 10 digits when resolved; anything else is counted unresolved
    ticker: str | None
    template: str
    proxy_cell: str
    seendate: datetime  # tz-aware UTC publisher time (freeze section 8: the sampling clock)
    source: str
    source_sha256: str
    event_key: str | None
    tags: frozenset[str]
    # Trailing defaulted field (deviation recorded in the lane return): the frozen
    # field list above carries no title, yet the group rule joins on "issuer and a
    # normalised title within 72 h" — a defaulted title keeps every constructor
    # call written against the frozen list working while making that join real.
    title: str = ""

    def __post_init__(self) -> None:
        if not self.item_id:
            raise SamplerError(f"candidate item_id must be non-empty: {self.item_id!r}")
        if not isinstance(self.title, str):
            raise SamplerError(f"candidate title must be a str: {self.title!r}")
        if self.template not in TEMPLATES:
            raise SamplerError(
                f"candidate template not in TEMPLATES {list(TEMPLATES)}: {self.template!r}"
            )
        if self.proxy_cell not in CELLS:
            raise SamplerError(
                f"candidate proxy_cell not in CELLS {list(CELLS)}: {self.proxy_cell!r}"
            )
        bad = set(self.tags) - set(TAG_NAMES)
        if bad:
            raise SamplerError(f"candidate tags outside {sorted(TAG_NAMES)}: {sorted(bad)}")
        if not isinstance(self.seendate, datetime) or self.seendate.tzinfo is None:
            raise SamplerError(
                f"candidate seendate must be a timezone-aware datetime: {self.item_id!r}"
            )
        if not self.source:
            raise SamplerError(f"candidate source must be non-empty: {self.item_id!r}")


@dataclass(frozen=True)
class SamplePlan:
    """Frozen draw parameters; (tape_sha256, window, seed, SAMPLER_VERSION) replay the draw."""

    seed: int
    window_start: date
    window_end: date
    tape_sha256: str
    per_template: int = 200
    # dataclasses forbid mutable defaults, and mappingproxy is unhashable, so the
    # frozen default is supplied by factory with the frozen CELL_TARGETS content.
    cell_targets: Mapping[str, int] = field(default_factory=lambda: CELL_TARGETS)
    issuer_cap: int = 6
    megacap_share_cap: float = 0.10
    economic_cluster_cap: float = 0.25
    near_duplicate_min: int = 20
    indirect_transfer_min: int = 10
    folds: int = 5
    prospective_from: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise SamplerError(f"plan.seed must be an int: {self.seed!r}")
        if self.window_start > self.window_end:
            raise SamplerError(
                f"plan.window_start after plan.window_end: "
                f"{self.window_start.isoformat()} > {self.window_end.isoformat()}"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", self.tape_sha256 or ""):
            raise SamplerError(
                f"plan.tape_sha256 must be 64 lowercase hex: {self.tape_sha256!r}"
            )
        for cell in CELLS:
            if cell not in self.cell_targets:
                raise SamplerError(f"plan.cell_targets missing cell: {cell}")
        for cell in CELLS:
            t = self.cell_targets[cell]
            if not isinstance(t, int) or isinstance(t, bool) or t < 0:
                raise SamplerError(
                    f"plan.cell_targets[{cell!r}] must be a non-negative int: {t!r}"
                )
        if not isinstance(self.issuer_cap, int) or self.issuer_cap < 1:
            raise SamplerError(f"plan.issuer_cap must be an int >= 1: {self.issuer_cap!r}")
        for name, cap in (
            ("megacap_share_cap", self.megacap_share_cap),
            ("economic_cluster_cap", self.economic_cluster_cap),
        ):
            if not 0.0 <= float(cap) <= 1.0:
                raise SamplerError(f"plan.{name} must be within [0, 1]: {cap!r}")
        for name, q in (
            ("near_duplicate_min", self.near_duplicate_min),
            ("indirect_transfer_min", self.indirect_transfer_min),
        ):
            if not isinstance(q, int) or q < 0:
                raise SamplerError(f"plan.{name} must be an int >= 0: {q!r}")
        if not isinstance(self.folds, int) or self.folds < 1:
            raise SamplerError(f"plan.folds must be an int >= 1: {self.folds!r}")
        if self.prospective_from is not None and not isinstance(self.prospective_from, date):
            raise SamplerError(
                f"plan.prospective_from must be a date or None: {self.prospective_from!r}"
            )


@dataclass(frozen=True)
class Case:
    """One drawn benchmark case (provenance per freeze section 6)."""

    item_id: str
    issuer: str
    template: str
    proxy_cell: str
    group_id: str
    fold: str
    source_sha256: str
    seendate: str  # ISO-8601 UTC with trailing Z
    tags: tuple[str, ...]  # sorted

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "issuer": self.issuer,
            "template": self.template,
            "proxy_cell": self.proxy_cell,
            "group_id": self.group_id,
            "fold": self.fold,
            "source_sha256": self.source_sha256,
            "seendate": self.seendate,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class Draw:
    """The drawn cases plus their manifest."""

    cases: tuple[Case, ...]
    manifest: dict[str, Any]


# --- helpers (pure, deterministic) --------------------------------------------


def _normalize_title(title: str) -> str:
    """Casefold and collapse whitespace — the title join key for near-duplicate groups."""
    return " ".join((title or "").casefold().split())


def _iso_z(dt: datetime) -> str:
    """ISO-8601 UTC string with a trailing Z."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(obj: Any) -> str:
    """The frozen canonical JSON encoding (byte-identical replay)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_key(seed: int, item_id: str) -> str:
    """Draw order inside a bucket: sha256(f\"{seed}:{item_id}\") — no random module."""
    return sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest()


def _share_ok(used: int, total: int, cap: float) -> bool:
    """True when admitting one more counted item keeps the share <= cap.

    Integer cross-multiplication at a fixed 1e6 scale so 20/200 <= 0.10 is exact
    at the boundary regardless of binary float noise.
    """
    num = round(float(cap) * _SHARE_SCALE)
    return (used + 1) * _SHARE_SCALE <= num * (total + 1)


def _utc_date(dt: datetime) -> date:
    return dt.astimezone(timezone.utc).date()


# --- grouping and folds --------------------------------------------------------


def group_ids(candidates: Iterable[Candidate]) -> dict[str, str]:
    """Map every item_id to its group id (freeze section 6: grouping and holdout).

    Candidates sharing an ``event_key``, or sharing an issuer and a normalised title
    within 72 h, are one group; the join is closed (union-find). Group id =
    "grp:" + first 16 hex of sha256 over the sorted member item ids joined by newline.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression
            parent[x], x = root, parent[x]
        return root

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            # deterministic root choice: lexicographically smaller id wins
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    cand_list = list(candidates)
    for c in cand_list:
        if c.item_id in parent:
            raise SamplerError(f"duplicate item_id in candidates: {c.item_id!r}")
        parent[c.item_id] = c.item_id

    by_event: dict[str, list[str]] = {}
    by_title: dict[tuple[str, str], list[Candidate]] = {}
    for c in cand_list:
        if c.event_key:
            by_event.setdefault(c.event_key, []).append(c.item_id)
        by_title.setdefault((c.issuer, _normalize_title(c.title)), []).append(c)

    for ids in by_event.values():
        for other in ids[1:]:
            union(ids[0], other)

    # issuer + normalised title within 72 h: sort each bucket by (seendate, item_id)
    # and join consecutive rows whose gap <= 72 h — equivalent to all pairwise joins
    # under union-find, and O(n log n).
    for members in by_title.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda c: (c.seendate, c.item_id))
        for prev, cur in zip(members, members[1:]):
            if cur.seendate - prev.seendate <= _WINDOW_H:
                union(prev.item_id, cur.item_id)

    components: dict[str, list[str]] = {}
    for item_id in parent:
        components.setdefault(find(item_id), []).append(item_id)
    out: dict[str, str] = {}
    for members in components.values():
        gid = "grp:" + sha256("\n".join(sorted(members)).encode("utf-8")).hexdigest()[:16]
        for item_id in members:
            out[item_id] = gid
    return out


def assign_folds(
    candidates: Iterable[Candidate],
    groups: Mapping[str, str],
    plan: SamplePlan,
) -> dict[str, str]:
    """Map every item_id to its fold: "f1".."fN" chronological, or "prospective".

    A group lands in "prospective" when its earliest seendate falls on or after
    ``plan.prospective_from`` (None disables the prospective cohort). Otherwise
    groups ordered by (earliest seendate, group id) are cut into ``plan.folds``
    contiguous chronological folds of near-equal group count; every member of a
    group gets the group fold.
    """
    cand_list = list(candidates)
    earliest: dict[str, datetime] = {}
    for c in cand_list:
        if c.item_id not in groups:
            raise SamplerError(f"groups map missing item_id: {c.item_id!r}")
        gid = groups[c.item_id]
        if gid not in earliest or c.seendate < earliest[gid]:
            earliest[gid] = c.seendate

    fold_of_group: dict[str, str] = {}
    ordered: list[tuple[datetime, str]] = []
    for gid, first in earliest.items():
        if plan.prospective_from is not None and _utc_date(first) >= plan.prospective_from:
            fold_of_group[gid] = "prospective"
        else:
            ordered.append((first, gid))
    ordered.sort()
    n = len(ordered)
    for i, (_, gid) in enumerate(ordered):
        fold_of_group[gid] = f"f{(i * plan.folds // n) + 1}"
    return {c.item_id: fold_of_group[groups[c.item_id]] for c in cand_list}


# --- the draw ------------------------------------------------------------------


def draw_sample(
    candidates: Iterable[Candidate],
    plan: SamplePlan,
    *,
    rights_allow: Callable[[str], bool],
    economic_cluster: Callable[[str], str | None] | None = None,
) -> Draw:
    """Draw the benchmark deterministically from ``candidates`` under ``plan``.

    Ordering inside each (template, proxy_cell): tagged candidates first (tag
    quotas are filled FIRST inside their cells, freeze section 6), then by
    sha256(f"{seed}:{item_id}"). Greedy fill honours, per template: at most one
    case per group, ``issuer_cap`` groups per issuer, megacap share of the draw
    <= ``megacap_share_cap`` (a megacap is skipped once the cap would be
    exceeded), and economic-cluster share <= ``economic_cluster_cap`` when
    ``economic_cluster`` is given. Cells that cannot be filled are reported
    short; nothing is padded, duplicated or borrowed.
    """
    cand_list = sorted(candidates, key=lambda c: c.item_id)
    counters = {
        "outside_window": 0,
        "low_value": 0,
        "unresolved_issuer": 0,
        "rights_refused": 0,
    }

    pool: list[Candidate] = []
    for c in cand_list:
        d = _utc_date(c.seendate)
        if d < plan.window_start or d > plan.window_end:
            counters["outside_window"] += 1
            continue
        pool.append(c)

    # Rights: the registry is the authority — refuse loudly, never skip silently.
    for source in sorted({c.source for c in pool}):
        if not rights_allow(source):
            raise RightsRefused(f"rights registry does not admit source: {source!r}")

    resolved: list[Candidate] = []
    for c in pool:
        if _CIK_RE.fullmatch(c.issuer):
            resolved.append(c)
        else:
            counters["unresolved_issuer"] += 1

    groups = group_ids(resolved)
    fold_of = assign_folds(resolved, groups, plan)

    buckets: dict[tuple[str, str], list[Candidate]] = {(t, cell): [] for t in TEMPLATES for cell in CELLS}
    for c in resolved:
        buckets[(c.template, c.proxy_cell)].append(c)
    for key in buckets:
        buckets[key].sort(
            key=lambda c: (0 if c.tags else 1, _hash_key(plan.seed, c.item_id), c.item_id)
        )

    cases: list[Case] = []
    cell_drawn: dict[tuple[str, str], int] = {}
    megacap_share: dict[str, float] = {}
    max_issuer_groups: dict[str, int] = {}
    economic_report: dict[str, Any]
    econ_checked = economic_cluster is not None

    for t in TEMPLATES:
        used_groups: set[str] = set()
        issuer_groups: dict[str, set[str]] = {}
        cluster_counts: dict[str, int] = {}
        mega = 0
        total = 0
        for cell in CELLS:
            target = plan.cell_targets[cell]
            drawn = 0
            for cand in buckets[(t, cell)]:
                if drawn >= target:
                    break
                gid = groups[cand.item_id]
                if gid in used_groups:
                    continue  # at most one case per group per template
                if len(issuer_groups.get(cand.issuer, ())) >= plan.issuer_cap:
                    continue  # issuer_cap groups per issuer per template
                is_mega = cand.ticker in MEGACAPS
                if is_mega and not _share_ok(mega, total, plan.megacap_share_cap):
                    continue  # skipped once the cap would be exceeded
                cluster = economic_cluster(cand.item_id) if econ_checked else None
                if cluster is not None and not _share_ok(
                    cluster_counts.get(cluster, 0), total, plan.economic_cluster_cap
                ):
                    continue
                used_groups.add(gid)
                issuer_groups.setdefault(cand.issuer, set()).add(gid)
                if is_mega:
                    mega += 1
                if cluster is not None:
                    cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
                total += 1
                drawn += 1
                cases.append(
                    Case(
                        item_id=cand.item_id,
                        issuer=cand.issuer,
                        template=cand.template,
                        proxy_cell=cand.proxy_cell,
                        group_id=gid,
                        fold=fold_of[cand.item_id],
                        source_sha256=cand.source_sha256,
                        seendate=_iso_z(cand.seendate),
                        tags=tuple(sorted(cand.tags)),
                    )
                )
            cell_drawn[(t, cell)] = drawn
        megacap_share[t] = (mega / total) if total else 0.0
        max_issuer_groups[t] = max((len(s) for s in issuer_groups.values()), default=0)

    if econ_checked:
        per_template_total = {t: sum(cell_drawn[(t, cell)] for cell in CELLS) for t in TEMPLATES}
        # max cluster share over all (template, cluster) pairs, from draw-time counts
        shares: list[float] = []
        t_cluster: dict[tuple[str, str], int] = {}
        for case in cases:
            cl = economic_cluster(case.item_id)
            if cl is not None:
                t_cluster[(case.template, cl)] = t_cluster.get((case.template, cl), 0) + 1
        for (t, _cl), n in t_cluster.items():
            tot = per_template_total[t]
            if tot:
                shares.append(n / tot)
        economic_report = {"status": "checked", "max_share": max(shares, default=0.0)}
    else:
        economic_report = {
            "status": "unchecked",
            "reason": "economic_cluster callable not provided",
        }

    manifest = build_manifest(
        plan,
        tuple(cases),
        counters,
        stats={"megacap_share": megacap_share, "economic_cluster": economic_report},
    )
    return Draw(cases=tuple(cases), manifest=manifest)


# --- manifest -------------------------------------------------------------------


def build_manifest(
    plan: SamplePlan,
    cases: Iterable[Case],
    counters: Mapping[str, int],
    *,
    stats: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the frozen sampling manifest (freeze section 6: provenance + short-cell report).

    ``stats`` carries the two aggregates the case list cannot express:
    ``megacap_share`` (per template; cases carry issuer but not ticker) and
    ``economic_cluster``. Without ``stats``, megacap_share is derived from the
    cases' issuers via the frozen _MEGACAP_CIKS table and economic_cluster is
    reported unchecked with its reason.
    """
    case_list = list(cases)
    required = ("outside_window", "low_value", "unresolved_issuer", "rights_refused")
    if set(counters) != set(required):
        raise SamplerError(
            f"counters must have exactly the keys {list(required)}: {sorted(counters)!r}"
        )

    cells_report: dict[str, dict[str, dict[str, int]]] = {}
    tag_quotas: dict[str, dict[str, dict[str, int]]] = {}
    drawn_per: dict[tuple[str, str], int] = {(t, cell): 0 for t in TEMPLATES for cell in CELLS}
    tags_per: dict[tuple[str, str], int] = {
        (t, tag): 0 for t in TEMPLATES for tag in sorted(TAG_NAMES)
    }
    folds_report: dict[str, int] = {f"f{i + 1}": 0 for i in range(plan.folds)}
    folds_report["prospective"] = 0
    issuer_groups: dict[tuple[str, str], set[str]] = {}
    for case in case_list:
        drawn_per[(case.template, case.proxy_cell)] += 1
        for tag in case.tags:
            tags_per[(case.template, tag)] += 1
        folds_report[case.fold] = folds_report.get(case.fold, 0) + 1
        issuer_groups.setdefault((case.template, case.issuer), set()).add(case.group_id)
    for t in TEMPLATES:
        cells_report[t] = {
            cell: {
                "target": plan.cell_targets[cell],
                "drawn": drawn_per[(t, cell)],
                "short": max(0, plan.cell_targets[cell] - drawn_per[(t, cell)]),
            }
            for cell in CELLS
        }
        tag_quotas[t] = {
            "near_duplicate": {
                "target": plan.near_duplicate_min,
                "drawn": tags_per[(t, "near_duplicate")],
                "short": max(0, plan.near_duplicate_min - tags_per[(t, "near_duplicate")]),
            },
            "indirect_transfer": {
                "target": plan.indirect_transfer_min,
                "drawn": tags_per[(t, "indirect_transfer")],
                "short": max(0, plan.indirect_transfer_min - tags_per[(t, "indirect_transfer")]),
            },
        }

    if stats is not None and "megacap_share" in stats:
        megacap_share = {t: float(stats["megacap_share"][t]) for t in TEMPLATES}
    else:
        mega_cases = {
            t: sum(
                1
                for case in case_list
                if case.template == t and case.issuer in _MEGACAP_CIKS
            )
            for t in TEMPLATES
        }
        totals = {t: sum(drawn_per[(t, cell)] for cell in CELLS) for t in TEMPLATES}
        megacap_share = {
            t: (mega_cases[t] / totals[t]) if totals[t] else 0.0 for t in TEMPLATES
        }
    if stats is not None and "economic_cluster" in stats:
        economic_report = dict(stats["economic_cluster"])
    else:
        economic_report = {"status": "unchecked", "reason": "economic_cluster callable not provided"}

    max_issuer_groups = {
        t: max(
            (len(g) for (tt, _issuer), g in issuer_groups.items() if tt == t),
            default=0,
        )
        for t in TEMPLATES
    }

    manifest: dict[str, Any] = {
        "sampler_version": SAMPLER_VERSION,
        "seed": plan.seed,
        "tape_sha256": plan.tape_sha256,
        "window": {"start": plan.window_start.isoformat(), "end": plan.window_end.isoformat()},
        "plan": {
            "per_template": plan.per_template,
            "cell_targets": dict(plan.cell_targets),
            "issuer_cap": plan.issuer_cap,
            "megacap_share_cap": plan.megacap_share_cap,
            "economic_cluster_cap": plan.economic_cluster_cap,
            "near_duplicate_min": plan.near_duplicate_min,
            "indirect_transfer_min": plan.indirect_transfer_min,
            "folds": plan.folds,
            "prospective_from": plan.prospective_from.isoformat()
            if plan.prospective_from is not None
            else None,
        },
        "cells": cells_report,
        "tag_quotas": tag_quotas,
        "megacap_share": megacap_share,
        "max_issuer_groups": max_issuer_groups,
        "economic_cluster": economic_report,
        "counters": dict(counters),
        "folds": folds_report,
        "cases_sha256": sha256(
            _canonical_json([case.to_dict() for case in case_list]).encode("utf-8")
        ).hexdigest(),
    }
    manifest["manifest_sha256"] = sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
    return manifest


# --- manifest schema -------------------------------------------------------------


def _tds_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["target", "drawn", "short"],
        "properties": {
            "target": {"type": "integer", "minimum": 0},
            "drawn": {"type": "integer", "minimum": 0},
            "short": {"type": "integer", "minimum": 0},
        },
    }


def _sha_schema() -> dict[str, Any]:
    return {"type": "string", "pattern": "^[0-9a-f]{64}$"}


def _date_schema() -> dict[str, Any]:
    return {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}


MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://mastermind-x.com/contracts/news_impact/sample_manifest.v1.schema.json",
    "title": "News impact sampling manifest v1",
    "description": (
        "Manifest of the deterministic Phase 1 benchmark draw (freeze section 6): "
        "replays from (tape sha, date bounds, seed, sampler version); reports every "
        "short cell instead of padding; counts every input class. Proxy cells are "
        "pre-label proxies, never outcomes."
    ),
    "type": "object",
    "additionalProperties": False,
    "required": [
        "sampler_version",
        "seed",
        "tape_sha256",
        "window",
        "plan",
        "cells",
        "tag_quotas",
        "megacap_share",
        "max_issuer_groups",
        "economic_cluster",
        "counters",
        "folds",
        "cases_sha256",
        "manifest_sha256",
    ],
    "properties": {
        "sampler_version": {"type": "string", "const": "ni-sampler-1"},
        "seed": {"type": "integer"},
        "tape_sha256": _sha_schema(),
        "window": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start", "end"],
            "properties": {"start": _date_schema(), "end": _date_schema()},
        },
        "plan": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "per_template",
                "cell_targets",
                "issuer_cap",
                "megacap_share_cap",
                "economic_cluster_cap",
                "near_duplicate_min",
                "indirect_transfer_min",
                "folds",
                "prospective_from",
            ],
            "properties": {
                "per_template": {"type": "integer", "minimum": 0},
                "cell_targets": {
                    "type": "object",
                    "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,31}$"},
                    "additionalProperties": {"type": "integer", "minimum": 0},
                },
                "issuer_cap": {"type": "integer", "minimum": 1},
                "megacap_share_cap": {"type": "number", "minimum": 0, "maximum": 1},
                "economic_cluster_cap": {"type": "number", "minimum": 0, "maximum": 1},
                "near_duplicate_min": {"type": "integer", "minimum": 0},
                "indirect_transfer_min": {"type": "integer", "minimum": 0},
                "folds": {"type": "integer", "minimum": 1},
                "prospective_from": {"anyOf": [_date_schema(), {"type": "null"}]},
            },
        },
        "cells": {
            "type": "object",
            "additionalProperties": False,
            "required": list(TEMPLATES),
            "properties": {
                t: {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(CELLS),
                    "properties": {cell: _tds_schema() for cell in CELLS},
                }
                for t in TEMPLATES
            },
        },
        "tag_quotas": {
            "type": "object",
            "additionalProperties": False,
            "required": list(TEMPLATES),
            "properties": {
                t: {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["near_duplicate", "indirect_transfer"],
                    "properties": {
                        "near_duplicate": _tds_schema(),
                        "indirect_transfer": _tds_schema(),
                    },
                }
                for t in TEMPLATES
            },
        },
        "megacap_share": {
            "type": "object",
            "additionalProperties": False,
            "required": list(TEMPLATES),
            "properties": {t: {"type": "number", "minimum": 0, "maximum": 1} for t in TEMPLATES},
        },
        "max_issuer_groups": {
            "type": "object",
            "additionalProperties": False,
            "required": list(TEMPLATES),
            "properties": {t: {"type": "integer", "minimum": 0} for t in TEMPLATES},
        },
        "economic_cluster": {
            "oneOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["status", "max_share"],
                    "properties": {
                        "status": {"const": "checked"},
                        "max_share": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["status", "reason"],
                    "properties": {
                        "status": {"const": "unchecked"},
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            ]
        },
        "counters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["outside_window", "low_value", "unresolved_issuer", "rights_refused"],
            "properties": {
                "outside_window": {"type": "integer", "minimum": 0},
                "low_value": {"type": "integer", "minimum": 0},
                "unresolved_issuer": {"type": "integer", "minimum": 0},
                "rights_refused": {"type": "integer", "minimum": 0},
            },
        },
        # folds keys are plan-parameterised (f1..fN plus "prospective"), so the key
        # SPACE is closed by pattern instead of by enumeration.
        "folds": {
            "type": "object",
            "minProperties": 1,
            "propertyNames": {"pattern": "^(prospective|f[1-9][0-9]*)$"},
            "additionalProperties": {"type": "integer", "minimum": 0},
        },
        "cases_sha256": _sha_schema(),
        "manifest_sha256": _sha_schema(),
    },
}


# --- optional tape loader ---------------------------------------------------------


def _tape_seendate(raw: Any, pd: Any) -> tuple[datetime | None, str | None]:
    """One tape seendate -> (aware datetime, None) or (None, drop reason).

    The qbus tape carries blank seendates (1,311 of 53,481 rows on the
    2026-10-12 tape).  An undated row cannot be placed in any window, so it is
    dropped and COUNTED by reason, never guessed onto a date.  Naive values
    are read as UTC, the rule this helper inherited.
    """
    if raw is None:
        return None, "seendate_blank"
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None, "seendate_blank"
        try:
            seen = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None, "seendate_unparseable"
    else:
        if pd.isna(raw):
            return None, "seendate_blank"
        seen = raw if isinstance(raw, datetime) else pd.Timestamp(raw).to_pydatetime()
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return seen, None


def load_tape(
    path: str,
    *,
    window_start: date,
    window_end: date,
    dropped: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Read a qbus parquet tape and return in-window rows as deterministic dicts.

    Optional helper: imports pandas inside the function so environments without
    pandas can still import and use the sampler. Raises SamplerError when pandas
    (or pyarrow) is absent — the tape cannot be read there.
    Rows whose seendate is blank or unparseable are dropped and, when
    ``dropped`` is given, counted into it by reason (see _tape_seendate).
    """
    try:
        import pandas as pd  # noqa: PLC0415 — deliberate lazy import
    except ImportError as exc:
        raise SamplerError(
            f"pandas is not installed; the parquet tape at {path!r} cannot be read: {exc}"
        ) from exc
    frame = pd.read_parquet(path)
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        seen, reason = _tape_seendate(record.get("seendate"), pd)
        if seen is None:
            if dropped is not None:
                dropped[reason] = dropped.get(reason, 0) + 1
            continue
        d = _utc_date(seen)
        if window_start <= d <= window_end:
            rows.append({str(k): v for k, v in record.items()} | {"seendate": seen})
    rows.sort(key=lambda r: (r["seendate"], str(r.get("item_id", ""))))
    return rows
