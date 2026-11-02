"""Conservative bounded event clustering for current ticker-news items.

Cross-source clustering is intentionally asymmetric toward false negatives: source
identity is exact; fuzzy joining requires a shared canonical security, compatible
event family, a bounded time window, compatible material discriminators, and an
immutable-anchor title match.

v2 keeps that bias and stops merging different amount scales (million versus
billion, 5bn versus 9bn), compact or spelled fiscal periods (2Q, 2Q25, second
quarter), and contraction negation (isn't, cannot).

Under the same v2 id (seat ruling 2026-10-12) it also stops merging opposite
earnings outcomes (beats versus misses), rating moves to opposite target
classes (to Buy versus to Sell), terminated versus ongoing actions (ends
talks versus in talks), and opposite move directions (raises versus cuts,
lifts versus lowers, including past forms).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
import hashlib
from html import unescape
import re

from engine import qkernel

# v3 also bounds fuzzy joins by both known immutable publication clocks.
# Receipt-time retrieval and the source/item identity digest stay unchanged.
CLUSTER_POLICY_VERSION = "qbus_news_cluster.v3"
# Label for a cluster row minted before the column existed (NULL), or a
# member whose cluster row is missing.
UNKNOWN_CLUSTER_POLICY_VERSION = "unknown (pre-column)"


@dataclass(frozen=True, slots=True)
class ClusterItem:
    source: str
    source_item_id: str
    title: str
    observed_at: datetime
    subject_ids: tuple[str, ...]
    event_family: str = ""
    published_at: datetime | None = None

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
    anchor_published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ClusterPolicy:
    title_threshold: float = 0.72
    window_seconds: int = 6 * 3600
    max_candidates: int = 128


def cluster_policy_version(policy: ClusterPolicy) -> str:
    """Return the provenance stamp naming exactly the policy in force.

    A default-constructed ClusterPolicy is stamped with the bare
    CLUSTER_POLICY_VERSION constant.
    A non-default policy is stamped with that constant plus every field as
    ``name=repr(value)`` in declaration order, which never contains the
    `` + `` provenance join separator.
    """
    if policy == ClusterPolicy():
        return CLUSTER_POLICY_VERSION
    return f"{CLUSTER_POLICY_VERSION} (" + ", ".join(
        f"{f.name}={getattr(policy, f.name)!r}"
        for f in dataclasses.fields(policy)
    ) + ")"


@dataclass(frozen=True, slots=True)
class ClusterDecision:
    action: str
    cluster_id: str
    matched_story_id: str | None
    similarity: float
    reason: str
    candidates_examined: int
    candidate_truncated: bool


# Single-letter scales stay on their own alternative so "$5B" is not rewritten
# onto "$5 billion" / "$5bn" (that collapse would start joining pairs the prior
# tokens kept apart). Stuck forms (5bn, 5mm) and words (5 million) are captured
# only so two different scales stop comparing as the same digits.
_NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[$€£])?\d+(?:[.,]\d+)*"
    r"(?:"
    r"(?:\s?(?:%|[KMBT]))(?=\b)"
    r"|"
    r"\s*(?:million|billion|trillion|thousand|bln|mln|trn|bn|mn|mm|tn)"
    r")?\b",
    re.I,
)
_PERIOD_RE = re.compile(
    r"\b(?:Q[1-4]|[1-4]Q(?:\d{2,4})?|H[12]|FY\s*\d{2,4}|CY\s*\d{2,4})\b",
    re.I,
)
_COMPACT_QUARTER_RE = re.compile(r"([1-4])Q(\d{2,4})?")
_SPELLED_QUARTER_RE = (
    ("Q1", re.compile(r"\b(?:first|1st)[\s-]+quarters?\b", re.I)),
    ("Q2", re.compile(r"\b(?:second|2nd)[\s-]+quarters?\b", re.I)),
    ("Q3", re.compile(r"\b(?:third|3rd)[\s-]+quarters?\b", re.I)),
    ("Q4", re.compile(r"\b(?:fourth|4th)[\s-]+quarters?\b", re.I)),
)
# "n't" has no leading word boundary: in "isn't" the n is still inside the stem.
_NEG_RE = re.compile(
    r"\b(?:not|no|denies?|rejects?|fails?|without|won't|will not|cannot)\b|n't\b",
    re.I,
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
# Earnings-outcome polarity: a beat-family-only title never merges with a
# miss-family-only one. Two titles from the same family stay compatible.
_BEAT_RE = re.compile(
    r"\b(?:beat|beats|tops|topped|exceeds|exceeded|surpasses|surpassed)\b"
    r"|\babove\s+(?:estimates?|expectations?)\b",
    re.I,
)
_MISS_RE = re.compile(
    r"\b(?:miss|misses|missed)\b"
    r"|\b(?:falls|fell)\s+short\b"
    r"|\bbelow\s+(?:estimates?|expectations?)\b",
    re.I,
)
# Rating moves are compared by the class of the target they name, not by the
# surface verb, so "upgraded to Buy" still merges with "raised to Buy". The
# neutral spellings accept hyphen, space and the Mkt abbreviation, so
# "Equal Weight", "Equal-Weight", "In Line", "Mkt Perform" and "Market
# Perform" all land in the same class. An optional opening quote is read
# past, so "to 'Buy'" and "to ‘Buy’" classify too.
_RATING_TARGET_RE = re.compile(
    r"\bto\s+['\"‘“]?(strong\s+buy|outperform|overweight|accumulate|buy|add|"
    r"strong\s+sell|underperform|underweight|sell|reduce|hold|neutral|"
    r"equal[-\s]+weight|(?:market|mkt)\s+perform|sector\s+perform|"
    r"in[-\s]+line|peer\s+perform)\b",
    re.I,
)
_BULLISH_TARGETS = frozenset(
    {"strong buy", "buy", "outperform", "overweight", "accumulate", "add"}
)
_BEARISH_TARGETS = frozenset(
    {"strong sell", "sell", "underperform", "underweight", "reduce"}
)
# Terminated versus ongoing actions compare like negation: an ended deal never
# merges with a live one. Only inflected forms are listed; bare "end"/"halt"
# stay free ("end of year", "halt" alone are not termination signals).
_TERMINATED_RE = re.compile(
    r"\b(?:ends|ended|terminates|terminated|calls\s+off|called\s+off|"
    r"abandons|abandoned|scraps|scrapped|walks\s+away|walked\s+away|"
    r"breaks\s+off|broke\s+off|halts|halted|suspends|suspended|"
    r"collapses|collapsed)\b",
    re.I,
)
# Move directions compare like outcome polarity: an up-move headline never
# merges with a down-move one, whatever surface verb (or past form) carries
# the direction. Bare "ups" stays off the list ("UPS" the ticker).
_MOVE_UP_RE = re.compile(
    r"\b(?:raise[sd]?|hike[sd]?|lift(?:s|ed)?|boost(?:s|ed)?|"
    r"increase[sd]?|upgrade[sd]?)\b",
    re.I,
)
_MOVE_DOWN_RE = re.compile(
    r"\b(?:cuts?|lower(?:s|ed)?|trim(?:s|med)?|slash(?:es|ed)?|"
    r"decrease[sd]?|reduce[sd]?|downgrade[sd]?)\b",
    re.I,
)


def new_cluster_id(item: ClusterItem) -> str:
    digest = hashlib.sha256(item.story_id.encode("utf-8")).hexdigest()[:16]
    return "ev2_" + digest


def _numbers(title: str) -> frozenset[str]:
    return frozenset(
        re.sub(r"[\s,]", "", x).lower() for x in _NUM_RE.findall(title)
    )


def _periods(title: str) -> frozenset[str]:
    found: list[str] = []
    for raw in _PERIOD_RE.findall(title):
        token = re.sub(r"\s+", "", raw).upper()
        compact = _COMPACT_QUARTER_RE.fullmatch(token)
        if compact:
            found.append("Q" + compact.group(1))
            if compact.group(2):
                found.append("FY" + compact.group(2))
        else:
            found.append(token)
    for label, rx in _SPELLED_QUARTER_RE:
        if rx.search(title):
            found.append(label)
    return frozenset(found)


def _negated(title: str) -> bool:
    folded = (
        title.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u02bc", "'")
    )
    return bool(_NEG_RE.search(folded))


def _actions(title: str) -> frozenset[str]:
    return frozenset(name for name, rx in _ACTIONS if rx.search(title))


def _outcome_polarity(title: str) -> frozenset[str]:
    """Beat/miss families found in the title ("beat", "miss", both, or none)."""
    found: set[str] = set()
    if _BEAT_RE.search(title):
        found.add("beat")
    if _MISS_RE.search(title):
        found.add("miss")
    return frozenset(found)


def _rating_target_classes(title: str) -> frozenset[str]:
    """Classes of the rating targets a title moves to (bullish/bearish/neutral)."""
    classes: set[str] = set()
    for match in _RATING_TARGET_RE.finditer(title):
        rating = re.sub(r"\s+", " ", match.group(1).lower())
        if rating in _BULLISH_TARGETS:
            classes.add("bullish")
        elif rating in _BEARISH_TARGETS:
            classes.add("bearish")
        else:
            classes.add("neutral")
    return frozenset(classes)


def _terminated(title: str) -> bool:
    return bool(_TERMINATED_RE.search(title))


def _move_polarity(title: str) -> frozenset[str]:
    """Move directions found in the title ("up", "down", both, or none)."""
    found: set[str] = set()
    if _MOVE_UP_RE.search(title):
        found.add("up")
    if _MOVE_DOWN_RE.search(title):
        found.add("down")
    return frozenset(found)


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
    if _negated(a) != _negated(b):
        return False
    aa, ab = _actions(a), _actions(b)
    if aa and ab and not (aa & ab):
        return False
    actor_a, actor_b = _analyst_actor(a), _analyst_actor(b)
    rating_a = bool(_RATING_VERB_RE.search(a))
    rating_b = bool(_RATING_VERB_RE.search(b))
    if rating_a and rating_b and actor_a and actor_b and actor_a != actor_b:
        return False
    da, db = _move_polarity(a), _move_polarity(b)
    if da and db and not (da & db):
        return False
    oa, ob = _outcome_polarity(a), _outcome_polarity(b)
    if oa and ob and not (oa & ob):
        return False
    ta, tb = _rating_target_classes(a), _rating_target_classes(b)
    if ta and tb and not (ta & tb):
        return False
    if _terminated(a) != _terminated(b):
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
        # A historical polling batch can receive unrelated old reports at once.
        # Publication is an additional guard, never a substitute arrival clock.
        if (
            incoming.published_at is not None
            and candidate.anchor_published_at is not None
            and _seconds(incoming.published_at, candidate.anchor_published_at)
            > policy.window_seconds
        ):
            continue
        if not _compatible(unescape(incoming.title), unescape(candidate.anchor_title)):
            continue
        similarity = qkernel.title_similarity(
            unescape(incoming.title), unescape(candidate.anchor_title)
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
