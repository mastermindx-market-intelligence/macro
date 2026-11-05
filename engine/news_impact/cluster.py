"""Deterministic cross-outlet news clustering and rule-table novelty assignment.

Implements the Prophet news-to-business-impact Phase 1 clusterer (program
upgrades 3 and 4): masterplan section 3.3 ("Identify the real change" - dedup
through qbus first, then separate new reporting of an old fact / a corrected
fact / a new magnitude-timing-commitment-counterparty / an independently
observed implementation milestone / commentary) and masterplan section 5 (the
three cluster grains: article/source manifestations of an event; distinct
facts and revisions within that event; a thesis view linking multiple events),
under the Phase 0 freeze of 2026-10-11 (PHASE0_FREEZE_2026-10-11.md D16:
``novelty = corrected_fact`` requires a non-null ``supersedes_fact_id``; D11:
the program mints no second novelty score - the rule table below assigns a
frozen enum VALUE, never a score, probability or confidence).

The clustering wraps the owner ``engine.qbus_news_cluster.cluster_candidates``
and consumes the cluster id it mints via ``new_cluster_id``; no owner logic is
copied or forked (see RESULT in the lane packet for the check). The novelty and
cluster_grain enums are the frozen ``contracts/news_impact/
news_impact_event.v1.schema.json`` ``$defs/novelty`` and ``$defs/cluster_grain``
(schema sha256 prefix 3edc7139).

Why this module exists: the qbus tape's ``event_key`` is 91% singletons
(C1_tape.md Q5) - a near-identity key that de-duplicates exact mirrors but does
not group same-story coverage across outlets - so novelty must come from a
replayable rule over observed history, never from a model opinion
(DNR:KILL-LLM-ORIGINATION).

Determinism: no clock reads (``as_of`` is always a parameter elsewhere; nothing
here needs it), no randomness, no network, no module-level I/O. Processing
order is the canonical sort ``(observed_at, story_id, title, source_sha256)``
so input order never affects a run; every set-derived collection is emitted
sorted; the owner itself re-sorts candidates and breaks similarity ties on
``cluster_id`` (engine/qbus_news_cluster.py:178-225), so candidate order cannot
affect a decision either.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import re
from typing import Iterable, Sequence

from engine.qbus_news_cluster import (
    ClusterCandidate,
    ClusterItem,
    ClusterPolicy,
    cluster_candidates,
)

CLUSTERER_VERSION = "ni-cluster-1"

#: Frozen ``$defs/cluster_grain`` enum (news_impact_event.v1.schema.json).
CLUSTER_GRAINS: tuple[str, ...] = (
    "article_manifestation",
    "fact_revision",
    "thesis_link",
)

#: Frozen ``$defs/novelty`` enum (news_impact_event.v1.schema.json).
NOVELTY_VALUES: tuple[str, ...] = (
    "new_reporting_of_old_fact",
    "corrected_fact",
    "new_magnitude_timing_commitment_counterparty",
    "independently_observed_milestone",
    "commentary",
)

#: Closed novelty rule table, FIRST MATCH WINS, listed in execution order.
#: N5 precedes N3 by commission (an independent same-value observation of a
#: stage/milestone metric is more specific than a mere re-report). Deleting or
#: reordering a row changes behavior and fails the table-shape test.
NOVELTY_RULES: tuple[str, ...] = (
    "N1:is_correction->corrected_fact(supersedes_required)",
    "N2:no_prior_fact_key->new_magnitude_timing_commitment_counterparty|commentary",
    "N5:prior_same_values+distinct_source_family+stage_or_milestone_metric"
    "->independently_observed_milestone",
    "N3:prior_same_values->new_reporting_of_old_fact",
    "N4:prior_changed_values_no_correction"
    "->new_magnitude_timing_commitment_counterparty",
)

_STAGE_MILESTONE_RE = re.compile(r"\b(?:stage|phase|milestone)\b", re.I)

_RULE_N1, _RULE_N2, _RULE_N5, _RULE_N3, _RULE_N4 = NOVELTY_RULES


@dataclass(frozen=True)
class Article:
    """One observed news item at the clusterer boundary.

    ``subject_ids`` are ``cik:`` + 10 digits as resolution.py mints them; they
    may be empty, in which case the owner permits no fuzzy join (only an exact
    ``same_source_item`` re-arrival). ``source_sha256`` is the caller's content
    hash for the observed payload, used only as a final canonical-order
    tiebreak for duplicate ``(observed_at, story_id)`` pairs.
    """

    source: str
    source_item_id: str
    title: str
    observed_at: datetime
    subject_ids: tuple[str, ...]
    event_family: str = ""
    source_sha256: str = ""

    @property
    def story_id(self) -> str:
        return f"{self.source}:{self.source_item_id}"


@dataclass(frozen=True)
class JoinReceipt:
    """Replayable per-article decision receipt (owner decision, verbatim)."""

    story_id: str
    action: str
    cluster_id: str
    matched_story_id: str | None
    similarity: float
    reason: str
    candidates_examined: int
    candidate_truncated: bool


@dataclass(frozen=True)
class Cluster:
    """A closed cross-outlet cluster as of the end of the run."""

    cluster_id: str
    anchor_story_id: str
    member_story_ids: tuple[str, ...]
    sources: tuple[str, ...]
    subject_ids: tuple[str, ...]
    first_observed_at: datetime
    last_observed_at: datetime


@dataclass(frozen=True)
class ClusterRun:
    """Full deterministic output of one clustering pass."""

    clusters: tuple[Cluster, ...]
    receipts: tuple[JoinReceipt, ...]
    policy: dict
    clusterer_version: str
    run_sha256: str


@dataclass(frozen=True)
class FactObservation:
    """One extracted fact observation offered to the novelty rule table.

    ``fact_key`` is ``(issuer, metric, fiscal_period, basis)`` - four strings;
    the issuer is a ``cik:`` id. ``quantity`` is a canonical decimal string or
    None. ``source_family`` groups outlets into provenance families (the
    correlated-provenance concern of masterplan section 5).
    """

    fact_key: tuple[str, str, str, str]
    quantity: str | None
    counterparty: str | None
    commitment: str | None
    observed_at: datetime
    source_family: str
    is_correction: bool = False
    supersedes_fact_id: str | None = None
    fact_id: str = field(kw_only=True)


@dataclass(frozen=True)
class NoveltyDecision:
    """Which novelty rule fired and what the frozen enum value is."""

    value: str
    rule: str
    supersedes_fact_id: str | None = None


class NoveltyError(Exception):
    """A novelty assignment is structurally impossible (e.g. N1 without a
    ``supersedes_fact_id``; the schema validator rejects that payload as
    ``supersedes_required`` - freeze D16)."""


class ReplayMismatch(Exception):
    """A replay of recorded receipts diverged from a fresh run."""


# --------------------------------------------------------------------------
# clustering (wrapper over the owner)
# --------------------------------------------------------------------------


@dataclass
class _OpenCluster:
    """Mutable accumulator; frozen Cluster values are derived at the end."""

    cluster_id: str
    members: list[ClusterItem]  # arrival order; members[0] is the anchor


def _require_tz_aware(observed_at: datetime) -> None:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("cluster times must be timezone-aware")


def _to_owner_item(article: Article) -> ClusterItem:
    return ClusterItem(
        source=article.source,
        source_item_id=article.source_item_id,
        title=article.title,
        observed_at=article.observed_at,
        subject_ids=tuple(article.subject_ids),
        event_family=article.event_family,
    )


def _candidate_for(open_cluster: _OpenCluster) -> ClusterCandidate:
    """One candidate per open cluster, built from its immutable anchor only."""
    anchor = open_cluster.members[0]
    return ClusterCandidate(
        cluster_id=open_cluster.cluster_id,
        anchor_story_id=anchor.story_id,
        anchor_title=anchor.title,
        anchor_observed_at=anchor.observed_at,
        subject_ids=anchor.subject_ids,
        event_family=anchor.event_family,
    )


def _finalize(open_cluster: _OpenCluster) -> Cluster:
    members = tuple(open_cluster.members)
    subjects: set[str] = set()
    for member in members:
        subjects.update(member.subject_ids)
    return Cluster(
        cluster_id=open_cluster.cluster_id,
        anchor_story_id=members[0].story_id,
        member_story_ids=tuple(m.story_id for m in members),
        sources=tuple(sorted({m.source for m in members})),
        subject_ids=tuple(sorted(subjects)),
        first_observed_at=min(m.observed_at for m in members),
        last_observed_at=max(m.observed_at for m in members),
    )


def _cluster_json(cluster: Cluster) -> dict:
    return {
        "cluster_id": cluster.cluster_id,
        "anchor_story_id": cluster.anchor_story_id,
        "member_story_ids": list(cluster.member_story_ids),
        "sources": list(cluster.sources),
        "subject_ids": list(cluster.subject_ids),
        "first_observed_at": cluster.first_observed_at.isoformat(),
        "last_observed_at": cluster.last_observed_at.isoformat(),
    }


def _receipt_json(receipt: JoinReceipt) -> dict:
    return {
        "story_id": receipt.story_id,
        "action": receipt.action,
        "cluster_id": receipt.cluster_id,
        "matched_story_id": receipt.matched_story_id,
        "similarity": receipt.similarity,
        "reason": receipt.reason,
        "candidates_examined": receipt.candidates_examined,
        "candidate_truncated": receipt.candidate_truncated,
    }


def _run_sha256(
    clusters: tuple[Cluster, ...],
    receipts: tuple[JoinReceipt, ...],
    policy_dict: dict,
) -> str:
    payload = {
        "clusterer_version": CLUSTERER_VERSION,
        "policy": policy_dict,
        "clusters": [_cluster_json(c) for c in clusters],
        "receipts": [_receipt_json(r) for r in receipts],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cluster_articles(
    articles: Iterable[Article], *, policy: ClusterPolicy | None = None
) -> ClusterRun:
    """Cluster articles across outlets by wrapping the owner decider.

    Articles are processed in the canonical order ``(observed_at, story_id,
    title, source_sha256)`` - the primary key is the commissioned
    ``(observed_at, story_id)``; the trailing fields only break ties between
    duplicate story ids so that input order can never matter. For each article
    one :class:`ClusterCandidate` is built per currently open cluster from its
    immutable anchor and handed to the owner ``cluster_candidates``; a
    ``join`` appends to the matched cluster, anything else opens a new cluster
    under the id the owner minted (``new_cluster_id``).
    """
    effective_policy = ClusterPolicy() if policy is None else policy
    materialized = list(articles)
    for article in materialized:
        _require_tz_aware(article.observed_at)
    ordered = sorted(
        materialized,
        key=lambda a: (a.observed_at, a.story_id, a.title, a.source_sha256),
    )

    open_by_id: dict[str, _OpenCluster] = {}
    receipts: list[JoinReceipt] = []
    for article in ordered:
        item = _to_owner_item(article)
        candidates = [
            _candidate_for(open_by_id[cid])
            for cid in sorted(open_by_id)  # owner re-sorts; this is for our receipts
        ]
        decision = cluster_candidates(item, candidates, policy=effective_policy)
        if decision.action == "join":
            target = open_by_id.get(decision.cluster_id)
            if target is None:
                raise ValueError(
                    f"join decision names unknown cluster: {decision.cluster_id}"
                )
            target.members.append(item)
        elif decision.action == "new":
            if decision.cluster_id in open_by_id:
                raise ValueError(f"cluster id collision: {decision.cluster_id}")
            open_by_id[decision.cluster_id] = _OpenCluster(
                decision.cluster_id, [item]
            )
        else:
            raise ValueError(
                f"unknown cluster decision action: {decision.action!r}"
            )
        receipts.append(
            JoinReceipt(
                story_id=article.story_id,
                action=decision.action,
                cluster_id=decision.cluster_id,
                matched_story_id=decision.matched_story_id,
                similarity=round(decision.similarity, 6),
                reason=decision.reason,
                candidates_examined=decision.candidates_examined,
                candidate_truncated=decision.candidate_truncated,
            )
        )

    clusters = tuple(
        _finalize(open_by_id[cid]) for cid in sorted(open_by_id)
    )
    receipts_tuple = tuple(receipts)
    policy_dict = asdict(effective_policy)
    return ClusterRun(
        clusters=clusters,
        receipts=receipts_tuple,
        policy=policy_dict,
        clusterer_version=CLUSTERER_VERSION,
        run_sha256=_run_sha256(clusters, receipts_tuple, policy_dict),
    )


def replay(
    articles: Iterable[Article],
    receipts: Iterable[JoinReceipt],
    *,
    policy: ClusterPolicy,
) -> ClusterRun:
    """Re-run the clusterer and assert every recorded receipt still holds.

    Raises :class:`ReplayMismatch` naming the first diverging ``story_id``
    (field divergence at the shared prefix, or the first receipt present on
    only one side when the counts differ). Returns the fresh run, whose
    ``run_sha256`` equals the original's for any untampered recording.
    """
    rerun = cluster_articles(articles, policy=policy)
    expected = tuple(receipts)
    got = rerun.receipts
    shared = min(len(expected), len(got))
    for index in range(shared):
        if expected[index] != got[index]:
            differing = [
                name
                for name in (
                    "story_id",
                    "action",
                    "cluster_id",
                    "matched_story_id",
                    "similarity",
                    "reason",
                    "candidates_examined",
                    "candidate_truncated",
                )
                if getattr(expected[index], name) != getattr(got[index], name)
            ]
            raise ReplayMismatch(
                f"receipt divergence at index {index} "
                f"story_id={expected[index].story_id} fields={differing}"
            )
    if len(expected) != len(got):
        if shared < len(got):
            story_id = got[shared].story_id
        else:
            story_id = expected[shared].story_id
        raise ReplayMismatch(
            f"receipt count divergence at index {shared} story_id={story_id} "
            f"(recorded={len(expected)} replayed={len(got)})"
        )
    return rerun


# --------------------------------------------------------------------------
# cluster grain
# --------------------------------------------------------------------------


def cluster_grain_for(cluster: Cluster, *, same_fact: bool) -> str:
    """Map a cluster onto the frozen ``cluster_grain`` enum (masterplan §5).

    ``thesis_link`` is returned only when the caller states it is linking
    across clusters / fact keys (``same_fact=False``). Within one fact key:
    a cluster in which every member comes from a distinct outlet is several
    article-level manifestations of one story (``len(members) ==
    len(sources)``); a cluster where some outlet contributed more than one
    member re-published the fact key inside the cluster
    (``len(members) > len(sources)``, exact by pigeonhole over the distinct
    source set - no story_id parsing). The frozen schema carries no prose
    descriptions for these enum values (checked: zero ``description`` keys
    mentioning them), so the masterplan section 5 taxonomy governs.
    """
    if not same_fact:
        return "thesis_link"
    if len(cluster.member_story_ids) > len(cluster.sources):
        return "fact_revision"
    return "article_manifestation"


# --------------------------------------------------------------------------
# novelty rule table
# --------------------------------------------------------------------------


def _values(observation: FactObservation) -> tuple[str | None, str | None, str | None]:
    return (observation.quantity, observation.counterparty, observation.commitment)


def _names_stage_or_milestone(metric: str) -> bool:
    return bool(_STAGE_MILESTONE_RE.search(metric))


def assign_novelty(
    history: Sequence[FactObservation], new: FactObservation
) -> NoveltyDecision:
    """Assign the frozen novelty enum value for ``new`` against ``history``.

    Pure function of its arguments; row order is :data:`NOVELTY_RULES`
    (N1, N2, N5, N3, N4 - first match wins). No score, probability or
    confidence is produced at any point (DNR:KILL-LLM-CONFIDENCE).
    """
    if new.is_correction:
        if not new.supersedes_fact_id:
            raise NoveltyError(
                "supersedes_required: corrected_fact requires supersedes_fact_id"
            )
        return NoveltyDecision(
            "corrected_fact", _RULE_N1, new.supersedes_fact_id
        )

    priors = [obs for obs in history if obs.fact_key == new.fact_key]
    if not priors:
        if new.quantity is not None or new.counterparty is not None or new.commitment is not None:
            return NoveltyDecision(
                "new_magnitude_timing_commitment_counterparty", _RULE_N2
            )
        return NoveltyDecision("commentary", _RULE_N2)

    same_values = [obs for obs in priors if _values(obs) == _values(new)]
    if (
        same_values
        and new.source_family not in {obs.source_family for obs in priors}
        and _names_stage_or_milestone(new.fact_key[1])
    ):
        return NoveltyDecision("independently_observed_milestone", _RULE_N5)
    if same_values:
        return NoveltyDecision("new_reporting_of_old_fact", _RULE_N3)
    return NoveltyDecision(
        "new_magnitude_timing_commitment_counterparty", _RULE_N4
    )
