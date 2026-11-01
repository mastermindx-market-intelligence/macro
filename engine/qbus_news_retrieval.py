"""Bounded indexed candidate retrieval for qbus news cluster assignment.

The pure matcher (``qbus_news_cluster.cluster_candidates``) stays the final judge
of time, security family, discriminators and title similarity. This module only
decides WHICH immutable cluster anchors the matcher gets to see, inside fixed
work budgets, so an older matching anchor is not selected solely by its recency.
Saturated retrieval remains explicitly incomplete.

Why an inverted index: the incumbent store query bounded candidates by recency
(``ORDER BY anchor_observed_at DESC LIMIT max_candidates``), so the 129th-newest
same-security anchor was never examined even when it was the only safe match. A
full scan with per-pair scoring was measured and rejected (median 370.6 ms at
2048 eligible anchors). The index here inverts the EXACT incumbent similarity
representation — ``qkernel.shingles(unescape(anchor_title))`` character-bigram
sets — so candidate discovery is proportional to shared rare text, not to burst
size, while the semantic join itself is unchanged.

Probe guarantee. For a query of ``n`` shingles and threshold ``t > 0``, every
candidate with Jaccard >= t shares at least ``ceil(t * n)`` query shingles (its
overlap i satisfies ``i / (|x| + n - i) <= i / n``). Probing
``s = n - ceil(t * n) + 1`` distinct query shingles therefore intersects every
qualifying candidate — but ONLY if all ``s`` postings are fully examined. Any
per-posting cap, fingerprint cap, index mismatch or budget exhaustion voids
the guarantee for that lookup;
``retrieval_truncated`` is set truthfully in every such case, and the caller
must not treat the matcher receiving ``max_candidates`` items as completeness.

Lifecycle. Fingerprints and postings are derived state for immutable anchors:
they are written in the SAME transaction that mints a cluster or expands its
retained subject union, and they are never rewritten when a member's headline is
corrected (anchors are immutable). Writer-only backfill at writable open is
deterministic (cluster_id order), transaction-safe and recoverable (a cluster is
indexed iff it has a fingerprint row). Read-only constructors create nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from html import unescape
import json
import math
import sqlite3

from engine import qkernel
from engine.qbus_news_cluster import (
    ClusterCandidate,
    ClusterItem,
    ClusterPolicy,
    cluster_policy_version,
)

# Distinct provenance label for the RETRIEVAL policy (budgets and probe rule).
# The semantic cluster policy keeps its own stamp; this version records which
# candidate-selection contract produced an assignment's evidence.
RETRIEVAL_POLICY_VERSION = "qbus_news_retrieval.v1"

# Raw posting-row budget for ONE candidate lookup: the total number of posting
# rows the probes may read, and the per-probe cap (which includes the overflow
# observation itself — a probe that returns its cap is counted as saturated).
DEFAULT_TOTAL_POSTING_ROWS = 1024
DEFAULT_POSTING_ROWS_PER_PROBE = 256
# Upper bound on distinct candidate anchors whose stored fingerprints are
# materialized for one lookup, including identity anchors. Probe-hit ordering
# is a heuristic under saturation, not a guarantee that the best match wins.
DEFAULT_CANDIDATE_FINGERPRINT_CAP = 128

# Strategies recorded in assignment evidence.
STRATEGY_INDEXED = "indexed"
STRATEGY_ANCHOR_ONLY = "anchor_only"
STRATEGY_NO_SUBJECTS = "no_subjects"
STRATEGY_RECENCY_FALLBACK = "recency_fallback"

_FALLBACK_NONPOSITIVE_THRESHOLD = "nonpositive_threshold"
_FALLBACK_INVALID_THRESHOLD = "invalid_threshold"
_FALLBACK_INDEX_UNAVAILABLE = "index_unavailable"

# Float noise guard for ceil(t * n): thresholds are floats; 0.72 * 25 must
# count as 18, not 19, so the probe count stays exactly the safe minimum.
_CEIL_EPS = 1e-9


@dataclass(frozen=True)
class RetrievalBudgets:
    """Fixed work budgets for one candidate lookup. Tuning, not policy."""

    total_posting_rows: int = DEFAULT_TOTAL_POSTING_ROWS
    posting_rows_per_probe: int = DEFAULT_POSTING_ROWS_PER_PROBE
    candidate_fingerprints: int = DEFAULT_CANDIDATE_FINGERPRINT_CAP

    def as_dict(self) -> dict:
        return {
            "total_posting_rows": self.total_posting_rows,
            "posting_rows_per_probe": self.posting_rows_per_probe,
            "candidate_fingerprints": self.candidate_fingerprints,
        }


@dataclass(frozen=True)
class RetrievalEvidence:
    """What one candidate lookup actually did. Persisted with the assignment."""

    retrieval_policy_version: str
    strategy: str
    fallback_reason: str | None
    cluster_policy_version: str
    title_threshold: float
    window_seconds: int
    max_candidates: int
    budgets: RetrievalBudgets
    securities_probed: int
    query_shingles: int
    probes_planned: int
    probes_executed: int
    postings_examined: int
    postings_saturated: int
    probe_budget_exhausted: bool
    frequency_rows_read: int
    candidates_surfaced: int
    candidates_fingerprinted: int
    fingerprint_mismatches: int
    candidates_qualifying: int
    anchor_probe_hits: int
    candidates_returned: int
    retrieval_truncated: bool

    def payload(self, *, decision=None) -> dict:
        """JSON-ready assignment evidence, optionally with matcher counters."""
        out = {
            "retrieval_policy_version": self.retrieval_policy_version,
            "strategy": self.strategy,
            "fallback_reason": self.fallback_reason,
            "cluster_policy_version": self.cluster_policy_version,
            "title_threshold": self.title_threshold,
            "window_seconds": self.window_seconds,
            "max_candidates": self.max_candidates,
            "budgets": self.budgets.as_dict(),
            "securities_probed": self.securities_probed,
            "query_shingles": self.query_shingles,
            "probes_planned": self.probes_planned,
            "probes_executed": self.probes_executed,
            "postings_examined": self.postings_examined,
            "postings_saturated": self.postings_saturated,
            "probe_budget_exhausted": self.probe_budget_exhausted,
            "frequency_rows_read": self.frequency_rows_read,
            "candidates_surfaced": self.candidates_surfaced,
            "candidates_fingerprinted": self.candidates_fingerprinted,
            "fingerprint_mismatches": self.fingerprint_mismatches,
            "candidates_qualifying": self.candidates_qualifying,
            "anchor_probe_hits": self.anchor_probe_hits,
            "candidates_returned": self.candidates_returned,
            "retrieval_truncated": self.retrieval_truncated,
        }
        if decision is not None:
            out["matcher"] = {
                "action": decision.action,
                "reason": decision.reason,
                "similarity": decision.similarity,
                "candidates_examined": decision.candidates_examined,
                "candidate_truncated": decision.candidate_truncated,
            }
        return out


def shingles_for_title(title: str):
    """The EXACT incumbent similarity representation for an anchor title.

    ``qkernel.shingles(unescape(title))`` — character bigrams of the normalized
    title. Both the pure matcher's ``title_similarity`` and this index are built
    on this one representation, so indexed relevance and matcher relevance are
    the same computation over the same inputs.
    """
    return qkernel.shingles(unescape(title))


# --------------------------------------------------------------------------- #
# Derived-index maintenance (writer-only; runs inside the caller's transaction).
# --------------------------------------------------------------------------- #


def _observation_microseconds(value: datetime) -> int:
    """A sortable, exact UTC clock for the incumbent observation-time window."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("anchor observation time must be timezone aware")
    delta = value.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds)


def _register_postings(
    conn: sqlite3.Connection,
    *,
    cluster_id: str,
    shingle_set,
    security_ids,
    anchor_observed_at: datetime,
) -> None:
    """Insert posting rows and maintained per-security shingle frequencies."""
    anchor_us = _observation_microseconds(anchor_observed_at)
    rows = [
        (security_id, shingle, anchor_us, cluster_id)
        for security_id in sorted(set(security_ids))
        for shingle in sorted(shingle_set)
    ]
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO news_cluster_postings(security_id, shingle, anchor_observed_us, cluster_id)
        VALUES(?,?,?,?)
        """,
        rows,
    )
    conn.executemany(
        """
        INSERT INTO news_shingle_df(security_id, shingle, df) VALUES(?,?,1)
        ON CONFLICT(security_id, shingle) DO UPDATE SET df=df+1
        """,
        [(security_id, shingle) for security_id, shingle, _, _ in rows],
    )


def index_new_anchor(
    conn: sqlite3.Connection,
    *,
    cluster_id: str,
    title: str,
    security_ids,
    anchor_observed_at: datetime,
    retrieval_policy_version: str = RETRIEVAL_POLICY_VERSION,
) -> int:
    """Fingerprint + postings for a freshly minted immutable cluster anchor.

    Same transaction as the cluster INSERT. Titles are never re-indexed after
    the fact: the anchor is immutable, and a member correction mints its own
    story rather than rewriting this one.
    """
    shingle_set = shingles_for_title(title)
    conn.execute(
        """
        INSERT INTO news_cluster_fingerprints(
            cluster_id, shingle_count, shingles_json, indexed_policy
        ) VALUES(?,?,?,?)
        """,
        (
            cluster_id,
            len(shingle_set),
            json.dumps(sorted(shingle_set), ensure_ascii=False),
            retrieval_policy_version,
        ),
    )
    _register_postings(
        conn,
        cluster_id=cluster_id,
        shingle_set=shingle_set,
        security_ids=security_ids,
        anchor_observed_at=anchor_observed_at,
    )
    return len(shingle_set)


def index_subject_expansion(
    conn: sqlite3.Connection,
    *,
    cluster_id: str,
    title: str,
    added_security_ids,
    anchor_observed_at: datetime,
) -> int:
    """Postings for securities newly retained by an existing cluster's union.

    Runs in the same transaction as the union update. Only NEW securities get
    rows (a union never shrinks, so postings are append-only); the fingerprint
    is untouched.
    """
    added = sorted(set(added_security_ids))
    if not added:
        return 0
    shingle_set = shingles_for_title(title)
    _register_postings(
        conn,
        cluster_id=cluster_id,
        shingle_set=shingle_set,
        security_ids=added,
        anchor_observed_at=anchor_observed_at,
    )
    return len(shingle_set) * len(added)


def index_cluster_backfill(
    conn: sqlite3.Connection,
    *,
    retrieval_policy_version: str = RETRIEVAL_POLICY_VERSION,
) -> int:
    """Deterministically index clusters that have no fingerprint row yet.

    Writer-only. A cluster is considered indexed iff its fingerprint row
    exists, so this is exactly the recoverable migration (and self-heal)
    path: it can be re-run after any interruption, in cluster_id order, and
    rebuilding a cluster's postings from its immutable anchor is idempotent.
    The caller owns the transaction (or the writable open's own one).

    Repair removes the old posting contributions before rebuilding, so a
    repeated repair does not inflate frequency metadata. These frequencies
    cover retained history, not only the queried time window; they remain a
    probe-order heuristic whose ordering can affect recall under saturation.
    """
    rows = conn.execute(
        """
        SELECT c.cluster_id, c.anchor_title, c.anchor_observed_at, c.subject_ids_json
        FROM news_clusters c
        LEFT JOIN news_cluster_fingerprints f ON f.cluster_id = c.cluster_id
        WHERE f.cluster_id IS NULL OR f.indexed_policy <> ?
        ORDER BY c.cluster_id
        """,
        (retrieval_policy_version,),
    ).fetchall()
    if not rows:
        return 0
    for row in rows:
        cluster_id = str(row["cluster_id"])
        # The reverse index bounds repair to this cluster's own postings.
        old_postings = conn.execute(
            "SELECT security_id, shingle FROM news_cluster_postings WHERE cluster_id=?",
            (cluster_id,),
        ).fetchall()
        keys = [(str(item["security_id"]), str(item["shingle"])) for item in old_postings]
        conn.executemany(
            "UPDATE news_shingle_df SET df=df-1 WHERE security_id=? AND shingle=?",
            keys,
        )
        conn.executemany(
            "DELETE FROM news_shingle_df WHERE security_id=? AND shingle=? AND df<=0",
            keys,
        )
        conn.execute("DELETE FROM news_cluster_postings WHERE cluster_id=?", (cluster_id,))
        conn.execute("DELETE FROM news_cluster_fingerprints WHERE cluster_id=?", (cluster_id,))
        index_new_anchor(
            conn,
            cluster_id=cluster_id,
            title=str(row["anchor_title"]),
            security_ids=tuple(json.loads(str(row["subject_ids_json"]))),
            anchor_observed_at=datetime.fromisoformat(str(row["anchor_observed_at"])),
            retrieval_policy_version=retrieval_policy_version,
        )
    return len(rows)


# --------------------------------------------------------------------------- #
# Bounded candidate retrieval.
# --------------------------------------------------------------------------- #

_CANDIDATE_COLUMNS = """
    cluster_id, anchor_story_id, anchor_title, anchor_observed_at,
    subject_ids_json, event_family
"""

# Candidate ordering before the final budget cut. The pure matcher re-sorts by
# recency itself; retain its newest-first horizon when a fallback observes
# an overflow row. Normalize only the derived ordering clock.
_CANDIDATE_ORDER_KEY = lambda c: (-_observation_microseconds(c.anchor_observed_at), c.cluster_id)  # noqa: E731


def _candidate_from_row(row) -> ClusterCandidate:
    return ClusterCandidate(
        cluster_id=str(row["cluster_id"]),
        anchor_story_id=str(row["anchor_story_id"]),
        anchor_title=str(row["anchor_title"]),
        anchor_observed_at=datetime.fromisoformat(str(row["anchor_observed_at"])),
        subject_ids=tuple(json.loads(str(row["subject_ids_json"]))),
        event_family=str(row["event_family"]),
    )


def _anchor_probe_candidates(
    conn: sqlite3.Connection,
    *,
    incoming: ClusterItem,
    window: timedelta,
    subjects: set[str],
    limit: int,
) -> list[ClusterCandidate]:
    """Clusters anchored by THIS story id, inside the incumbent horizon.

    The matcher joins a same-source-item anchor on identity before similarity,
    so such a candidate must be surfaced even when title shingles no longer
    overlap (corrected headline). Window and subject filters match the
    incumbent store query exactly, so this only restores a join the incumbent
    horizon could otherwise evict by recency; it never adds a new matching
    policy.
    """
    rows = conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        FROM news_clusters
        WHERE anchor_story_id = ?
          AND anchor_observed_at BETWEEN ? AND ?
        LIMIT ?
        """,
        (
            incoming.story_id,
            (incoming.observed_at - window).isoformat(),
            (incoming.observed_at + window).isoformat(),
            limit,
        ),
    ).fetchall()
    out = []
    for row in rows:
        if not (set(json.loads(str(row["subject_ids_json"]))) & subjects):
            continue
        out.append(_candidate_from_row(row))
    return out


def _recency_fallback_candidates(
    conn: sqlite3.Connection,
    *,
    incoming: ClusterItem,
    policy: ClusterPolicy,
) -> tuple[ClusterCandidate, ...]:
    """The incumbent recency-bounded store query, unchanged.

    Used only where the inverted index cannot bound the candidate set at all
    (non-positive or invalid threshold, or the derived index being absent).
    One extra row is fetched to observe truncation truthfully, but at most
    ``max_candidates`` rows are returned: the matcher re-sorts by recency and
    would discard a 129th sentinel anyway.
    """
    window = timedelta(seconds=policy.window_seconds)
    rows = conn.execute(
        f"""
        SELECT {_CANDIDATE_COLUMNS}
        FROM news_clusters
        WHERE anchor_observed_at BETWEEN ? AND ?
          AND EXISTS (
              SELECT 1 FROM json_each(news_clusters.subject_ids_json) subjects
              WHERE subjects.value IN (SELECT value FROM json_each(?))
          )
        ORDER BY anchor_observed_at DESC, cluster_id
        LIMIT ?
        """,
        (
            (incoming.observed_at - window).isoformat(),
            (incoming.observed_at + window).isoformat(),
            json.dumps(sorted(set(incoming.subject_ids))),
            policy.max_candidates + 1,
        ),
    ).fetchall()
    return tuple(_candidate_from_row(row) for row in rows)


def _probe_postings(
    conn: sqlite3.Connection,
    *,
    security_id: str,
    probes: list[str],
    budgets: RetrievalBudgets,
    remaining: int,
    hits: dict[str, int],
    window_start_us: int,
    window_end_us: int,
) -> tuple[int, int, int, bool]:
    """Read posting lists for one security's probes within the shared budget.

    Returns (rows_read, saturated_probes, probes_executed, budget_exhausted).
    A probe that returns its cap is counted as saturated: more rows may exist
    beyond the cap, so the full-examination guarantee is void from that probe
    on.
    """
    rows_read = 0
    saturated = 0
    executed = 0
    exhausted = False
    for shingle in probes:
        limit = min(budgets.posting_rows_per_probe, remaining)
        if limit <= 0:
            exhausted = True
            break
        rows = conn.execute(
            """
            SELECT cluster_id FROM news_cluster_postings
            WHERE security_id=? AND shingle=?
              AND anchor_observed_us BETWEEN ? AND ?
            LIMIT ?
            """,
            (security_id, shingle, window_start_us, window_end_us, limit),
        ).fetchall()
        executed += 1
        rows_read += len(rows)
        remaining -= len(rows)
        if len(rows) >= limit:
            # The cap (per-probe, or the budget tail) stopped this posting
            # list: candidates beyond it were not observed.
            saturated += 1
        for row in rows:
            cluster_id = str(row[0])
            hits[cluster_id] = hits.get(cluster_id, 0) + 1
    return rows_read, saturated, executed, exhausted


def retrieve_candidates(
    conn: sqlite3.Connection,
    incoming: ClusterItem,
    *,
    policy: ClusterPolicy,
    budgets: RetrievalBudgets = RetrievalBudgets(),
) -> tuple[tuple[ClusterCandidate, ...], RetrievalEvidence]:
    """Bounded candidate anchors for one incoming item.

    Returns at most ``policy.max_candidates`` semantic candidates — never a
    129th sentinel, because the matcher re-sorts by recency and would drop the
    oldest (the very anchor this index exists to recover). Every limit hit is
    recorded in the evidence; the pure matcher remains the final judge of
    everything it examined.
    """
    window = timedelta(seconds=policy.window_seconds)
    subjects = set(incoming.subject_ids)
    base = RetrievalEvidence(
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        strategy=STRATEGY_INDEXED,
        fallback_reason=None,
        cluster_policy_version=cluster_policy_version(policy),
        title_threshold=policy.title_threshold,
        window_seconds=policy.window_seconds,
        max_candidates=policy.max_candidates,
        budgets=budgets,
        securities_probed=0,
        query_shingles=0,
        probes_planned=0,
        probes_executed=0,
        postings_examined=0,
        postings_saturated=0,
        probe_budget_exhausted=False,
        frequency_rows_read=0,
        candidates_surfaced=0,
        candidates_fingerprinted=0,
        fingerprint_mismatches=0,
        candidates_qualifying=0,
        anchor_probe_hits=0,
        candidates_returned=0,
        retrieval_truncated=False,
    )

    def finish(
        candidates: tuple[ClusterCandidate, ...],
        evidence: RetrievalEvidence,
    ) -> tuple[tuple[ClusterCandidate, ...], RetrievalEvidence]:
        ordered = tuple(sorted(candidates, key=lambda candidate: (
            candidate.anchor_story_id != incoming.story_id, *_CANDIDATE_ORDER_KEY(candidate),
        )))
        truncated = evidence.retrieval_truncated or len(ordered) > policy.max_candidates
        bounded = ordered[: max(policy.max_candidates, 0)]
        return bounded, replace(
            evidence,
            candidates_returned=len(bounded),
            retrieval_truncated=truncated,
        )

    # The incumbent store query returns nothing without a subject filter, and
    # the matcher rejects every candidate without subject overlap, so an empty
    # subject union has no retrievable horizon at all.
    if not subjects:
        return ((), replace(base, strategy=STRATEGY_NO_SUBJECTS))

    t = policy.title_threshold
    query_shingles = shingles_for_title(incoming.title)
    n = len(query_shingles)

    # Thresholds where the index cannot bound anything: t <= 0 admits every
    # candidate regardless of overlap, and t > 1 is rejected by the matcher
    # anyway (surfaced here only to avoid wasted index work first).
    if not 0.0 < t <= 1.0:
        fallback_reason = (
            _FALLBACK_NONPOSITIVE_THRESHOLD if t <= 0 else _FALLBACK_INVALID_THRESHOLD
        )
        rows = _recency_fallback_candidates(conn, incoming=incoming, policy=policy)
        evidence = replace(
            base,
            strategy=STRATEGY_RECENCY_FALLBACK,
            fallback_reason=fallback_reason,
            query_shingles=n,
            candidates_surfaced=len(rows),
            candidates_fingerprinted=0,
            candidates_qualifying=len(rows),
            retrieval_truncated=len(rows) > policy.max_candidates,
        )
        return finish(rows, evidence)

    if n == 0:
        # An empty query shingle set cannot reach any positive Jaccard, so the
        # only examineable candidate is a same-source-item anchor.
        anchors = _anchor_probe_candidates(
            conn, incoming=incoming, window=window, subjects=subjects,
            limit=budgets.candidate_fingerprints,
        )
        evidence = replace(
            base,
            strategy=STRATEGY_ANCHOR_ONLY,
            candidates_surfaced=len(anchors),
            candidates_fingerprinted=len(anchors),
            candidates_qualifying=len(anchors),
            anchor_probe_hits=len(anchors),
            retrieval_truncated=len(anchors) >= budgets.candidate_fingerprints,
        )
        return finish(tuple(anchors), evidence)

    needed = max(1, int(math.ceil(t * n - _CEIL_EPS)))
    probe_count = n - needed + 1

    def _indexed():
        hits: dict[str, int] = {}
        rows_read = 0
        saturated = 0
        executed = 0
        exhausted = False
        frequency_rows = 0
        securities_probed = 0
        for security_id in sorted(subjects):
            securities_probed += 1
            df_rows = conn.execute(
                """
                SELECT shingle, df FROM news_shingle_df
                WHERE security_id=? AND shingle IN
                    (%s)
                """
                % ",".join("?" for _ in query_shingles),
                (security_id, *sorted(query_shingles)),
            ).fetchall()
            frequency_rows += len(df_rows)
            df_map = {str(row[0]): int(row[1]) for row in df_rows}
            # Rarest first; shingles absent from the frequency table have no
            # postings for this security and are probed for free. Deterministic
            # order (df, shingle) keeps the probe set stable for a given store.
            ordered_probes = sorted(
                query_shingles, key=lambda sh: (df_map.get(sh, 0), sh)
            )[:probe_count]
            if not ordered_probes:
                continue
            read, sat, ran, was_exhausted = _probe_postings(
                conn,
                security_id=security_id,
                probes=ordered_probes,
                budgets=budgets,
                remaining=budgets.total_posting_rows - rows_read,
                hits=hits,
                window_start_us=_observation_microseconds(incoming.observed_at - window),
                window_end_us=_observation_microseconds(incoming.observed_at + window),
            )
            rows_read += read
            saturated += sat
            executed += ran
            exhausted = exhausted or was_exhausted
            if was_exhausted:
                break

        # Same-source-item anchors are surfaced regardless of shingle overlap.
        anchors = _anchor_probe_candidates(
            conn, incoming=incoming, window=window, subjects=subjects,
            limit=budgets.candidate_fingerprints,
        )
        anchor_ids = {c.cluster_id for c in anchors}

        surfaced = set(hits) - anchor_ids
        # Probe hits are a bounded relevance heuristic, not a completeness
        # guarantee under saturation. The scoring stage — metadata plus
        # stored fingerprint per candidate, then the incumbent Jaccard — is
        # bounded by candidate_fingerprints, NOT by the surfaced count: a
        # saturated lookup must not turn into an unbounded scoring pass.
        ranked = sorted(
            surfaced, key=lambda cid: (-hits.get(cid, 0), cid)
        )[: max(0, budgets.candidate_fingerprints - len(anchors))]
        truncated = (bool(exhausted) or saturated > 0 or len(surfaced) > len(ranked)
                     or len(anchors) >= budgets.candidate_fingerprints)

        candidates: dict[str, ClusterCandidate] = {c.cluster_id: c for c in anchors}
        qualifying = len(anchors)
        mismatches = 0
        fingerprinted = len(anchors)
        for chunk_start in range(0, len(ranked), 128):
            chunk = ranked[chunk_start : chunk_start + 128]
            rows = conn.execute(
                f"""
                SELECT c.cluster_id,
                       c.anchor_story_id, c.anchor_title,
                       c.anchor_observed_at, c.subject_ids_json, c.event_family,
                       f.shingle_count AS fp_shingle_count,
                       f.shingles_json AS fp_shingles_json,
                       f.indexed_policy AS fp_policy
                FROM news_clusters c
                LEFT JOIN news_cluster_fingerprints f
                  ON f.cluster_id = c.cluster_id
                WHERE c.cluster_id IN ({",".join("?" for _ in chunk)})
                """,
                tuple(chunk),
            ).fetchall()
            chunk_rows: dict[str, object] = {}
            for row in rows:
                chunk_rows[str(row["cluster_id"])] = row
            for cluster_id, row in chunk_rows.items():
                fingerprinted += 1
                raw_count = row["fp_shingle_count"]
                if raw_count is None or row["fp_policy"] != RETRIEVAL_POLICY_VERSION:
                    # Surfaced, in-window candidate with no fingerprint row:
                    # score from the immutable anchor title (the same
                    # representation the matcher will use) and flag the
                    # incomplete index state.
                    stored = shingles_for_title(str(row["anchor_title"]))
                    mismatches += 1
                else:
                    try:
                        stored = set(json.loads(str(row["fp_shingles_json"])))
                    except (TypeError, ValueError):
                        stored = set()
                    if len(stored) != int(raw_count):
                        # Torn fingerprint: score from the immutable anchor
                        # title and flag the state.
                        stored = shingles_for_title(str(row["anchor_title"]))
                        mismatches += 1
                if qkernel.jaccard(query_shingles, stored) >= t:
                    qualifying += 1
                    candidates[cluster_id] = _candidate_from_row(row)

        evidence = replace(
            base,
            securities_probed=securities_probed,
            query_shingles=n,
            probes_planned=probe_count * len(subjects),
            probes_executed=executed,
            postings_examined=rows_read,
            postings_saturated=saturated,
            probe_budget_exhausted=exhausted,
            frequency_rows_read=frequency_rows,
            candidates_surfaced=len(surfaced) + len(anchors),
            candidates_fingerprinted=fingerprinted,
            fingerprint_mismatches=mismatches,
            candidates_qualifying=qualifying,
            anchor_probe_hits=len(anchors),
            retrieval_truncated=truncated or mismatches > 0,
        )
        return tuple(candidates.values()), evidence

    try:
        candidates, evidence = _indexed()
    except sqlite3.Error:
        # Derived index absent/unreadable: degrade to the incumbent recency
        # horizon and say so, rather than failing the assignment. The
        # degradation is carried by strategy/fallback_reason; the truncation
        # flag still reports only an actually-cut horizon.
        rows = _recency_fallback_candidates(conn, incoming=incoming, policy=policy)
        evidence = replace(
            base,
            strategy=STRATEGY_RECENCY_FALLBACK,
            fallback_reason=_FALLBACK_INDEX_UNAVAILABLE,
            query_shingles=n,
            probes_planned=probe_count * len(subjects),
            candidates_surfaced=len(rows),
            candidates_fingerprinted=0,
            candidates_qualifying=len(rows),
            retrieval_truncated=len(rows) > policy.max_candidates,
        )
        return finish(rows, evidence)
    return finish(candidates, evidence)
