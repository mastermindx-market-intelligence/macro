"""Conservative bounded event clustering for current ticker-news items.

Cross-source clustering is intentionally asymmetric toward false negatives: source
identity is exact; fuzzy joining requires a shared canonical security, compatible
event family, a bounded time window, compatible material discriminators, and an
immutable-anchor title match.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import re

from engine import qkernel


@dataclass(frozen=True, slots=True)
class ClusterItem:
    source: str
    source_item_id: str
    title: str
    observed_at: datetime
    subject_ids: tuple[str, ...]
    event_family: str = ""

    @property
    def story_id(self) -> str:
        return f"{self.source}:{self.source_item_id}"


@dataclass(frozen=True, slots=True)
class ClusterCandidate:
    cluster_id: str
    anchor_story_id: str
    anchor_title: str
    anchor_observed_at: datetime
    subject_ids: tuple[str, ...]
    event_family: str = ""


@dataclass(frozen=True, slots=True)
class ClusterPolicy:
    title_threshold: float = 0.72
    window_seconds: int = 6 * 3600
    max_candidates: int = 128


@dataclass(frozen=True, slots=True)
class ClusterDecision:
    action: str
    cluster_id: str
    matched_story_id: str | None
    similarity: float
    reason: str
    candidates_examined: int
    candidate_truncated: bool


_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[$€£])?\d+(?:[.,]\d+)*(?:\s?(?:%|[KMBT]))?\b",
    re.I,
)
_PERIOD_RE = re.compile(r"\b(?:Q[1-4]|H[12]|FY\s*\d{2,4}|CY\s*\d{2,4})\b", re.I)
_NEG_RE = re.compile(
    r"\b(?:not|no|denies?|rejects?|fails?|without|won't|will not)\b", re.I
)
_ACTIONS = (
    (
        "upgrade",
        re.compile(
            r"\b(?:upgrade[sd]?|raises?\s+(?:its\s+)?(?:price\s+)?target)\b",
            re.I,
        ),
    ),
    (
        "downgrade",
        re.compile(
            r"\b(?:downgrade[sd]?|cuts?\s+(?:its\s+)?(?:price\s+)?target)\b",
            re.I,
        ),
    ),
    ("approve", re.compile(r"\bapprove[sd]?\b", re.I)),
    ("deny", re.compile(r"\b(?:den(?:y|ies|ied)|reject(?:s|ed)?)\b", re.I)),
    ("confirm", re.compile(r"\bconfirm(?:s|ed)?\b", re.I)),
    (
        "rumor",
        re.compile(
            r"\b(?:reportedly|rumou?r(?:ed)?|explor(?:e|es|ing)|consider(?:s|ing)?)\b",
            re.I,
        ),
    ),
    ("raise", re.compile(r"\b(?:raises?|increases?|boosts?)\b", re.I)),
    ("cut", re.compile(r"\b(?:cuts?|lowers?|reduces?)\b", re.I)),
)
_RATING_VERB_RE = re.compile(
    r"\b(?:upgrade[sd]?|downgrade[sd]?|raises?|cuts?)\b", re.I
)
_GENERIC_ACTORS = {"broker", "analyst", "company", "firm", "bank"}


def new_cluster_id(item: ClusterItem) -> str:
    digest = hashlib.sha256(item.story_id.encode("utf-8")).hexdigest()[:16]
    return "ev2_" + digest


def _numbers(title: str) -> frozenset[str]:
    return frozenset(
        re.sub(r"[\s,]", "", x).lower() for x in _NUM_RE.findall(title)
    )


def _periods(title: str) -> frozenset[str]:
    return frozenset(
        re.sub(r"\s+", "", x).upper() for x in _PERIOD_RE.findall(title)
    )


def _actions(title: str) -> frozenset[str]:
    return frozenset(name for name, rx in _ACTIONS if rx.search(title))


def _analyst_actor(title: str) -> str | None:
    match = _RATING_VERB_RE.search(title)
    if not match:
        return None
    prefix = qkernel.norm_title(title[: match.start()])
    if not prefix or prefix in _GENERIC_ACTORS:
        return None
    return prefix


def _compatible(a: str, b: str) -> bool:
    na, nb = _numbers(a), _numbers(b)
    if na and nb and na != nb:
        return False
    pa, pb = _periods(a), _periods(b)
    if pa and pb and pa != pb:
        return False
    if bool(_NEG_RE.search(a)) != bool(_NEG_RE.search(b)):
        return False
    aa, ab = _actions(a), _actions(b)
    if aa and ab and not (aa & ab):
        return False
    actor_a, actor_b = _analyst_actor(a), _analyst_actor(b)
    rating_a = bool(_RATING_VERB_RE.search(a))
    rating_b = bool(_RATING_VERB_RE.search(b))
    if rating_a and rating_b and actor_a and actor_b and actor_a != actor_b:
        return False
    return True


def _seconds(a: datetime, b: datetime) -> float:
    if (
        a.tzinfo is None
        or b.tzinfo is None
        or a.utcoffset() is None
        or b.utcoffset() is None
    ):
        raise ValueError("cluster times must be timezone-aware")
    return abs((a - b).total_seconds())


def cluster_candidates(
    incoming: ClusterItem,
    candidates: list[ClusterCandidate] | tuple[ClusterCandidate, ...],
    *,
    policy: ClusterPolicy,
) -> ClusterDecision:
    if policy.max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if not 0.0 <= policy.title_threshold <= 1.0:
        raise ValueError("title_threshold out of range")
    if policy.window_seconds < 0:
        raise ValueError("window_seconds must be nonnegative")
    _seconds(incoming.observed_at, incoming.observed_at)

    ordered = sorted(
        candidates,
        key=lambda c: (-c.anchor_observed_at.timestamp(), c.cluster_id),
    )
    truncated = len(ordered) > policy.max_candidates
    bounded = ordered[: policy.max_candidates]
    examined = 0
    best: tuple[float, ClusterCandidate] | None = None
    for candidate in bounded:
        examined += 1
        if incoming.story_id == candidate.anchor_story_id:
            return ClusterDecision(
                "join",
                candidate.cluster_id,
                candidate.anchor_story_id,
                1.0,
                "same_source_item",
                examined,
                truncated,
            )
        if not (set(incoming.subject_ids) & set(candidate.subject_ids)):
            continue
        if (
            incoming.event_family
            and candidate.event_family
            and incoming.event_family != candidate.event_family
        ):
            continue
        if (
            _seconds(incoming.observed_at, candidate.anchor_observed_at)
            > policy.window_seconds
        ):
            continue
        if not _compatible(incoming.title, candidate.anchor_title):
            continue
        similarity = qkernel.title_similarity(
            incoming.title, candidate.anchor_title
        )
        if similarity < policy.title_threshold:
            continue
        if (
            best is None
            or similarity > best[0]
            or (
                similarity == best[0]
                and candidate.cluster_id < best[1].cluster_id
            )
        ):
            best = (similarity, candidate)

    if best is not None:
        similarity, candidate = best
        return ClusterDecision(
            "join",
            candidate.cluster_id,
            candidate.anchor_story_id,
            similarity,
            "anchor_title_match",
            examined,
            truncated,
        )

    return ClusterDecision(
        "new",
        new_cluster_id(incoming),
        None,
        0.0,
        "no_safe_match",
        examined,
        truncated,
    )
