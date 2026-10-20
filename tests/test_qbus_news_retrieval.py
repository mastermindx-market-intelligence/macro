"""Qualification tests for the derived candidate-retrieval index.

The pure matcher (``qbus_news_cluster``) is untouched and stays the final
judge. These tests pin what the index owes the assignment path:

* the default 128-candidate budget must still join an older near-duplicate
  after 512/2048 distinct same-security unrelated stories (the incumbent
  recency horizon evicted it), in any arrival order;
* the indexed similarity representation is exactly the incumbent one
  (``qkernel.shingles(unescape(title))``), so HTML entities, CJK/mixed scripts
  and normalized-title truncation behave identically;
* derived-index lifecycle: same-transaction maintenance on anchor mint and
  retained-union expansion, immutability on correction/withdrawal, writer-only
  deterministic recoverable backfill, read-only opens create nothing;
* deliberately saturated postings obey the raw-row and candidate budgets with
  truthful truncation metadata — truncated retrieval is never reported as
  complete just because the matcher received a full budget;
* discriminators (material numbers, fiscal periods, opposite outcomes) still
  keep stories separate through the full indexed stack.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from engine import qbus_news_store as m
from engine.qbus_news_cluster import ClusterItem, ClusterPolicy
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_retrieval import (
    DEFAULT_POSTING_ROWS_PER_PROBE,
    DEFAULT_TOTAL_POSTING_ROWS,
    RETRIEVAL_POLICY_VERSION,
    RetrievalBudgets,
    retrieve_candidates,
)

UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)

ANCHOR_TITLE = "Nvidia launches new AI accelerator"
DUP_TITLE = "Nvidia launches its new AI accelerator"


def _routed(
    item_id,
    title,
    *,
    second=0,
    security_ids=("sec-NVDA",),
):
    updated = T0 + timedelta(seconds=second)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision="sp500-r1",
    )


def _remove(item_id, *, second):
    event = T0 + timedelta(seconds=second)
    revision = normalize_news(
        {
            "id": f"delete-{item_id}",
            "kind": "news",
            "data": {
                "action": "deleted",
                "id": item_id,
                "timestamp": event.isoformat(),
            },
        },
        transport="benzinga_ws",
        received_at=event + timedelta(seconds=1),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=(),
        universe_revision="sp500-r1",
    )


def _rights():
    return m.NewsReadRights.all_internal()


def _noise_rows(count, *, start_second=1, security_ids=("sec-NVDA",)):
    """Distinct same-security stories: unique material numbers keep them apart."""
    return [
        _routed(
            f"n{i}",
            f"Other company announces contract {i} for services {i}",
            second=start_second + i,
            security_ids=security_ids,
        )
        for i in range(count)
    ]


def _commit_chunks(store, rows, size=256):
    for start in range(0, len(rows), size):
        store.commit_observations(rows[start : start + size])


def _evidence(store, source, source_item_id):
    row = store._conn.execute(
        "SELECT retrieval_json FROM news_cluster_members"
        " WHERE source=? AND source_item_id=?",
        (source, source_item_id),
    ).fetchone()
    assert row is not None and row["retrieval_json"] is not None
    return json.loads(str(row["retrieval_json"]))


def _stories(store, security_id="sec-NVDA", limit=500):
    return store.snapshot(
        security_id, limit=limit, cursor=None, rights=_rights()
    ).rows


# --------------------------------------------------------------------------- #
# 1. Default-budget recovery of an older event under same-security bursts.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("total_noise", [128, 512])
def test_default_budget_recovers_older_event_under_same_security_burst(tmp_path, total_noise):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        _commit_chunks(
            store,
            [
                _routed("anchor", ANCHOR_TITLE),
                *_noise_rows(total_noise),
                _routed("dup", DUP_TITLE, second=total_noise + 2),
            ],
        )
        rows = _stories(store)
        evidence = _evidence(store, "benzinga", "dup")
        flooded = [
            json.loads(str(row["retrieval_json"]))
            for row in store._conn.execute(
                "SELECT retrieval_json FROM news_cluster_members"
                " WHERE source_item_id LIKE 'n%'"
            )
        ]

    assert any(r.item_count == 2 for r in rows)
    assert evidence["strategy"] == "indexed"
    assert evidence["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION
    # Raw posting work is bounded even in the burst, and every counter the
    # assignment persisted names what actually happened.
    assert evidence["postings_examined"] <= DEFAULT_TOTAL_POSTING_ROWS
    assert evidence["candidates_returned"] <= 128
    assert evidence["matcher"]["candidates_examined"] <= 128
    assert evidence["matcher"]["action"] == "join"
    # The flooded noise assignments report the saturation honestly.
    assert any(e["retrieval_truncated"] for e in flooded)


def test_default_budget_recovers_older_event_at_2048_same_security_noise(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        _commit_chunks(
            store,
            [
                _routed("anchor", ANCHOR_TITLE),
                *_noise_rows(2048),
                _routed("dup", DUP_TITLE, second=2050),
            ],
        )
        rows = _stories(store)
        evidence = _evidence(store, "benzinga", "dup")
        truncated_assignments = store._conn.execute(
            "SELECT count(*) FROM news_cluster_members"
            ' WHERE retrieval_json LIKE \'%"retrieval_truncated":true%\''
        ).fetchone()[0]

    joined = [r for r in rows if r.item_count == 2]
    assert len(joined) == 1
    assert joined[0].story_id.startswith("ev2_")
    # Every lookup stayed inside the raw budgets...
    assert evidence["postings_examined"] <= DEFAULT_TOTAL_POSTING_ROWS
    assert evidence["candidates_fingerprinted"] <= 128
    assert evidence["candidates_returned"] <= 128
    assert evidence["matcher"]["candidates_examined"] <= 128
    assert evidence["matcher"]["action"] == "join"
    # ...and the flooded assignments did not claim completeness.
    assert truncated_assignments > 0


def test_arrival_order_variation_dup_first_still_renders_one_story(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        _commit_chunks(
            store,
            [
                _routed("dup", DUP_TITLE),
                _routed("anchor", ANCHOR_TITLE, second=1),
                *_noise_rows(512, start_second=2),
            ],
        )
        rows = _stories(store)
        members = store._conn.execute(
            "SELECT count(*) FROM news_cluster_members"
        ).fetchone()[0]
        clusters = store._conn.execute(
            "SELECT count(*) FROM news_clusters"
        ).fetchone()[0]
        paired = store._conn.execute(
            "SELECT count(*) FROM (SELECT cluster_id FROM news_cluster_members"
            " GROUP BY cluster_id HAVING count(*)=2)"
        ).fetchone()[0]

    assert members == 514
    assert clusters == 513
    assert paired == 1
    assert all(r.item_count == 1 for r in rows)


def test_arrival_order_variation_noise_committed_between_pairs(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations([_routed("anchor", ANCHOR_TITLE)])
        for start in range(0, 512, 64):
            store.commit_observations(_noise_rows(64, start_second=1 + start))
        store.commit_observations([_routed("dup", DUP_TITLE, second=514)])
        rows = _stories(store)

    assert any(r.item_count == 2 for r in rows)


def test_discriminators_stay_separate_through_the_indexed_path(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        _commit_chunks(
            store,
            [
                _routed("amt1", "Nvidia guides revenue to $8.2B"),
                _routed("amt2", "Nvidia guides revenue to $9.1B", second=1),
                _routed("q1", "Nvidia reports Q1 revenue growth"),
                _routed("q2", "Nvidia reports Q2 revenue growth", second=2),
                _routed("beat", "Nvidia beats quarterly estimates"),
                _routed("miss", "Nvidia misses quarterly estimates", second=3),
            ],
        )
        rows = _stories(store)

    assert len(rows) == 6
    assert sorted(r.item_count for r in rows) == [1] * 6


def test_custom_policy_budget_recovers_and_custom_threshold_is_respected(tmp_path):
    with m.NewsStore(
        tmp_path / "q.sqlite3",
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(max_candidates=4),
    ) as store:
        _commit_chunks(
            store,
            [
                _routed("anchor", ANCHOR_TITLE),
                *_noise_rows(64),
                _routed("dup", DUP_TITLE, second=70),
            ],
        )
        rows = _stories(store)
        recovered = any(r.item_count == 2 for r in rows)

    assert recovered is True


def test_strict_custom_threshold_keeps_weak_pair_separate(tmp_path):
    with m.NewsStore(
        tmp_path / "q.sqlite3",
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=0.95),
    ) as store:
        store.commit_observations([_routed("anchor", ANCHOR_TITLE)])
        store.commit_observations([_routed("dup", DUP_TITLE, second=1)])
        rows = _stories(store)
        evidence = _evidence(store, "benzinga", "dup")

    assert len(rows) == 2
    assert evidence["matcher"]["action"] == "new"
    assert evidence["title_threshold"] == 0.95


# --------------------------------------------------------------------------- #
# 2. Exact incumbent similarity representation.
# --------------------------------------------------------------------------- #


def test_html_entity_titles_join_through_the_index(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", "Nvidia &amp; partners unveil AI accelerator"),
                _routed("b", "Nvidia & partners unveil AI accelerator", second=1),
            ]
        )
        rows = _stories(store)

    assert len(rows) == 1
    assert rows[0].item_count == 2


def test_cjk_and_mixed_script_titles_join_and_stay_separate(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("c1", "英伟达发布全新AI加速器"),
                _routed("c2", "英伟达发布全新AI加速器", second=1),
                _routed("c3", "英伟达推迟全新AI加速器发布", second=2),
            ]
        )
        rows = _stories(store)

    assert len(rows) == 2
    counts = sorted(r.item_count for r in rows)
    assert counts == [1, 2]


def test_normalized_title_truncation_cap_is_index_compatible(tmp_path):
    shared = "Nvidia unveils a comprehensive accelerator roadmap for the data center platform " * 2
    first = shared + "with extra detail one"
    second = shared + "with extra detail two"
    assert first[:130] == second[:130]
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations([_routed("t1", first), _routed("t2", second, second=1)])
        rows = _stories(store)

    # Both normalize to the same capped title, so the indexed fingerprints are
    # identical and the matcher sees one near-duplicate story.
    assert len(rows) == 1
    assert rows[0].item_count == 2


# --------------------------------------------------------------------------- #
# 3. Derived-index lifecycle.
# --------------------------------------------------------------------------- #


def _index_state(conn):
    return {
        "fingerprints": sorted(
            tuple(row) for row in conn.execute(
                "SELECT cluster_id, shingle_count, shingles_json,"
                " indexed_policy FROM news_cluster_fingerprints"
            )
        ),
        "postings": sorted(
            tuple(row) for row in conn.execute(
                "SELECT security_id, shingle, cluster_id FROM news_cluster_postings"
            )
        ),
        "df": sorted(
            tuple(row) for row in conn.execute(
                "SELECT security_id, shingle, df FROM news_shingle_df"
            )
        ),
    }


def test_retained_union_expansion_makes_cluster_reachable_from_new_security(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", ANCHOR_TITLE, security_ids=("sec-NVDA",)),
                _routed("b", DUP_TITLE, second=1, security_ids=("sec-NVDA", "sec-AMD")),
            ]
        )
        cluster_id = _stories(store)[0].story_id
        before = _index_state(store._conn)
        assert any(
            row[0] == "sec-AMD" for row in before["postings"]
        ), "union expansion must post the cluster for the added security"

        # A later item routed only to the added security reaches the cluster.
        store.commit_observations(
            [_routed("c", "Nvidia launches its new AI accelerator", second=2,
                     security_ids=("sec-AMD",))]
        )
        after = _index_state(store._conn)
        rows = _stories(store, "sec-AMD")

    assert rows[0].story_id == cluster_id
    # item_count is the per-security visible membership: sec-AMD sees the
    # routed member b and the new member c, not the NVDA-only member a.
    assert rows[0].item_count == 2
    # Postings for previously indexed securities are untouched by expansion.
    assert set(before["postings"]) <= set(after["postings"])


def test_correction_keeps_anchor_and_derived_index_immutable(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", ANCHOR_TITLE),
                _routed("b", DUP_TITLE, second=1),
            ]
        )
        story_before = _stories(store)[0].story_id
        index_before = _index_state(store._conn)
        title_before = store._conn.execute(
            "SELECT anchor_title FROM news_clusters WHERE cluster_id=?",
            (story_before,),
        ).fetchone()["anchor_title"]

        store.commit(
            [_routed("b", "Nvidia corrects accelerator launch details", second=2)],
            expected_cursor=None,
            next_cursor=None,
        )
        index_after = _index_state(store._conn)
        title_after = store._conn.execute(
            "SELECT anchor_title FROM news_clusters WHERE cluster_id=?",
            (story_before,),
        ).fetchone()["anchor_title"]

    assert title_before == title_after == ANCHOR_TITLE
    assert index_before == index_after


def test_withdrawn_anchor_cluster_stays_reachable_for_retained_union(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", ANCHOR_TITLE),
                _routed("b", DUP_TITLE, second=1),
            ]
        )
        story_before = _stories(store)[0].story_id
        store.commit([_remove("a", second=2)], expected_cursor=None, next_cursor=None)
        rows_after_withdrawal = _stories(store)
        store.commit_observations(
            [_routed("c", DUP_TITLE, second=3)]
        )
        rows_after_new = _stories(store)

    assert rows_after_withdrawal[0].item_count == 1
    assert rows_after_new[0].story_id == story_before
    assert rows_after_new[0].item_count == 2


def test_mid_batch_failure_rolls_back_index_and_retries_deterministically(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        good = [
            _routed("a", ANCHOR_TITLE),
            _routed("b", DUP_TITLE, second=1),
        ]
        from dataclasses import replace as dc_replace

        broken_revision = dc_replace(good[1].revision, revision_id="deadbeef")
        bad = m.RoutedRevision(
            revision=broken_revision,
            security_ids=("sec-NVDA",),
            universe_revision="sp500-r1",
        )
        with pytest.raises(m.RevisionCollision):
            store.commit_observations([*good, bad])

        counts = store.counts()
        assert counts["revisions"] == 0 and counts["states"] == 0
        assert store._conn.execute(
            "SELECT count(*) FROM news_clusters"
        ).fetchone()[0] == 0
        assert store._conn.execute(
            "SELECT count(*) FROM news_cluster_fingerprints"
        ).fetchone()[0] == 0
        assert store._conn.execute(
            "SELECT count(*) FROM news_cluster_postings"
        ).fetchone()[0] == 0
        assert store._conn.execute(
            "SELECT count(*) FROM news_shingle_df"
        ).fetchone()[0] == 0

        store.commit_observations(good)
        rows = _stories(store)
        assert len(rows) == 1 and rows[0].item_count == 2


def test_backfill_recreates_identical_index_and_is_idempotent(tmp_path):
    path = tmp_path / "q.sqlite3"
    with m.NewsStore(path, source_key="benzinga-rest") as store:
        _commit_chunks(store, [
            _routed("a", ANCHOR_TITLE),
            _routed("b", DUP_TITLE, second=1),
            _routed("c", "Nvidia CFO resigns", second=2),
        ])
    with sqlite3.connect(path) as conn:
        expected = _index_state(conn)
        conn.execute("DROP TABLE news_cluster_postings")
        conn.execute("DROP TABLE news_cluster_fingerprints")
        conn.execute("DROP TABLE news_shingle_df")
    with m.NewsStore(path, source_key="benzinga-rest") as store:
        rebuilt = _index_state(store._conn)
        assert rebuilt == expected
    # Idempotent: an immediate reopen finds nothing pending and changes nothing.
    with m.NewsStore(path, source_key="benzinga-rest") as store:
        assert _index_state(store._conn) == expected


def test_readonly_open_creates_nothing(tmp_path):
    path = tmp_path / "q.sqlite3"
    with m.NewsStore(path, source_key="benzinga-rest") as store:
        store.commit_observations([_routed("a", ANCHOR_TITLE)])
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE news_cluster_postings")
        conn.execute("DROP TABLE news_cluster_fingerprints")
        conn.execute("DROP TABLE news_shingle_df")

    ro = m.NewsStore.open_readonly(path, source_key="benzinga-rest")
    try:
        assert ro._conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='news_cluster_fingerprints'"
        ).fetchone()[0] == 0
        snap = ro.snapshot("sec-NVDA", limit=10, cursor=None, rights=_rights())
        assert len(snap.rows) == 1
    finally:
        ro.close()
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='news_cluster_fingerprints'"
        ).fetchone()[0] == 0

    # A writable open owns the migration.
    with m.NewsStore(path, source_key="benzinga-rest") as store:
        assert store._conn.execute(
            "SELECT count(*) FROM news_cluster_fingerprints"
        ).fetchone()[0] == 1
        assert store._conn.execute(
            "SELECT count(*) FROM news_cluster_postings"
        ).fetchone()[0] > 0


def test_assignment_evidence_names_retrieval_and_matcher_counters(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", ANCHOR_TITLE),
                _routed("b", DUP_TITLE, second=1),
            ]
        )
        evidence = _evidence(store, "benzinga", "b")

    assert evidence["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION
    assert evidence["cluster_policy_version"] == "qbus_news_cluster.v3"
    assert evidence["postings_examined"] > 0
    assert evidence["candidates_qualifying"] >= 1
    assert evidence["retrieval_truncated"] is False
    assert evidence["matcher"] == {
        "action": "join",
        "reason": "anchor_title_match",
        "similarity": evidence["matcher"]["similarity"],
        "candidates_examined": 1,
        "candidate_truncated": False,
    }
    assert 0.72 <= evidence["matcher"]["similarity"] <= 1.0


# --------------------------------------------------------------------------- #
# 4. Budgets and truthful truncation under deliberate saturation.
# --------------------------------------------------------------------------- #


def _flooded_store(tmp_path, count=40):
    """Store where one rare shingle family is shared by `count` clusters."""
    path = tmp_path / "flood.sqlite3"
    store = m.NewsStore(path, source_key="benzinga-rest")
    rows = [
        _routed(f"f{i}", f"Zzqworp systems announce expansion {i}", second=i)
        for i in range(count)
    ]
    store.commit_observations(rows)
    return store


def test_saturated_postings_obey_row_and_candidate_budgets(tmp_path):
    store = _flooded_store(tmp_path)
    try:
        incoming = ClusterItem(
            source="benzinga",
            source_item_id="probe",
            title="Zzqworp systems announce expansion",
            observed_at=T0 + timedelta(seconds=999),
            subject_ids=("sec-NVDA",),
            event_family="",
        )
        budgets = RetrievalBudgets(
            total_posting_rows=6, posting_rows_per_probe=2, candidate_fingerprints=3
        )
        candidates, evidence = retrieve_candidates(
            store._conn, incoming, policy=store.cluster_policy, budgets=budgets
        )
        payload = evidence.payload()
        assert payload["postings_examined"] <= 6
        assert payload["candidates_fingerprinted"] <= 3
        assert payload["candidates_returned"] <= store.cluster_policy.max_candidates
        assert payload["postings_saturated"] >= 1
        assert payload["probe_budget_exhausted"] is True
        assert payload["retrieval_truncated"] is True
    finally:
        store.close()


def test_unsaturated_lookup_reports_complete_retrieval(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [
                _routed("a", ANCHOR_TITLE),
                _routed("b", DUP_TITLE, second=1),
            ]
        )
        incoming = ClusterItem(
            source="benzinga",
            source_item_id="probe",
            title=DUP_TITLE,
            observed_at=T0 + timedelta(seconds=1),
            subject_ids=("sec-NVDA",),
            event_family="",
        )
        candidates, evidence = retrieve_candidates(
            store._conn, incoming, policy=store.cluster_policy
        )
        payload = evidence.payload()
        assert payload["postings_examined"] <= DEFAULT_TOTAL_POSTING_ROWS
        assert payload["postings_saturated"] == 0
        assert payload["probe_budget_exhausted"] is False
        assert payload["probes_executed"] == payload["probes_planned"]
        assert payload["retrieval_truncated"] is False
        assert any(c.anchor_title == ANCHOR_TITLE for c in candidates)


def test_probe_query_uses_the_posting_primary_key(tmp_path):
    store = _flooded_store(tmp_path, count=5)
    try:
        plan = store._conn.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT cluster_id FROM news_cluster_postings
            WHERE security_id=? AND shingle=? LIMIT ?
            """,
            ("sec-NVDA", "zz", 256),
        ).fetchall()
        detail = " ".join(str(row[3]) for row in plan)
        assert "news_cluster_postings" in detail
        assert "USING" in detail and "PRIMARY KEY" in detail
    finally:
        store.close()


# --------------------------------------------------------------------------- #
# 5. Degraded and degenerate policies stay explicit and bounded.
# --------------------------------------------------------------------------- #


def test_no_subject_items_record_no_subjects_strategy(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations(
            [_routed("x", ANCHOR_TITLE, security_ids=())]
        )
        evidence = _evidence(store, "benzinga", "x")
        rows = _stories(store)

    assert evidence["strategy"] == "no_subjects"
    assert evidence["candidates_returned"] == 0
    # No subject routing means no security ever sees the item.
    assert rows == ()


def test_empty_normalized_title_falls_back_to_anchor_only(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations([_routed("x", "!!! ???")])
        evidence = _evidence(store, "benzinga", "x")

    assert evidence["strategy"] == "anchor_only"
    assert evidence["query_shingles"] == 0


def test_zero_threshold_uses_recency_fallback_and_stays_bounded(tmp_path):
    with m.NewsStore(
        tmp_path / "q.sqlite3",
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=0.0, max_candidates=8),
    ) as store:
        rows_in = [
            _routed("a", ANCHOR_TITLE),
            *_noise_rows(16),
            _routed("b", DUP_TITLE, second=20),
        ]
        _commit_chunks(store, rows_in)
        evidence = _evidence(store, "benzinga", "b")

    assert evidence["strategy"] == "recency_fallback"
    assert evidence["fallback_reason"] == "nonpositive_threshold"
    assert evidence["candidates_returned"] <= 8


def test_invalid_threshold_surfaces_matcher_error(tmp_path):
    with m.NewsStore(
        tmp_path / "q.sqlite3",
        source_key="benzinga-rest",
        cluster_policy=ClusterPolicy(title_threshold=1.5),
    ) as store:
        with pytest.raises(ValueError):
            store.commit_observations([_routed("a", ANCHOR_TITLE)])
        counts = store.counts()
        assert counts["revisions"] == 0


def test_extreme_title_length_stays_bounded(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit_observations([_routed("a", "word " * 800)])
        evidence = _evidence(store, "benzinga", "a")

    assert evidence["query_shingles"] <= 120
    assert evidence["postings_examined"] <= DEFAULT_TOTAL_POSTING_ROWS
    assert evidence["probes_planned"] <= 120



def test_old_same_security_history_does_not_spend_the_current_window_budget(tmp_path):
    with m.NewsStore(tmp_path / "history-window.db", source_key="test") as store:
        old = [
            _routed(f"history-{i}", f"Nvidia launches new AI accelerator with capacity {i}", second=i)
            for i in range(1024)
        ]
        _commit_chunks(store, old)
        current = 7 * 86400
        store.commit_observations([
            _routed("current-anchor", ANCHOR_TITLE, second=current),
            _routed("current-duplicate", DUP_TITLE, second=current + 1),
        ])
        rows = store._conn.execute(
            "SELECT cluster_id FROM news_cluster_members WHERE source_item_id IN (?,?)",
            ("current-anchor", "current-duplicate"),
        ).fetchall()
        assert len({row["cluster_id"] for row in rows}) == 1
        evidence = _evidence(store, "benzinga", "current-duplicate")
        assert evidence["retrieval_truncated"] is False
        assert evidence["postings_saturated"] == 0
        assert evidence["postings_examined"] < 128


def test_security_expansion_keeps_the_original_anchor_observation_time(tmp_path):
    with m.NewsStore(tmp_path / "union-clock.db", source_key="test") as store:
        store.commit_observations([_routed("anchor", ANCHOR_TITLE)])
        cluster = store._conn.execute("SELECT cluster_id FROM news_clusters").fetchone()[0]
        original_clocks = {
            row[0] for row in store._conn.execute(
                "SELECT DISTINCT anchor_observed_us FROM news_cluster_postings WHERE cluster_id=?",
                (cluster,),
            )
        }
        later = 7 * 86400
        store.commit_observations([
            _routed("anchor", ANCHOR_TITLE, second=later, security_ids=("sec-NVDA", "sec-AMD")),
        ])
        expanded_clocks = {
            row[0] for row in store._conn.execute(
                "SELECT DISTINCT anchor_observed_us FROM news_cluster_postings WHERE cluster_id=? AND security_id=?",
                (cluster, "sec-AMD"),
            )
        }
        assert expanded_clocks == original_clocks
        store.commit_observations([
            _routed("new-event", DUP_TITLE, second=later + 1, security_ids=("sec-AMD",)),
        ])
        new_cluster = store._conn.execute(
            "SELECT cluster_id FROM news_cluster_members WHERE source_item_id='new-event'"
        ).fetchone()[0]
        assert new_cluster != cluster
        original_cluster = store._conn.execute(
            "SELECT cluster_id FROM news_cluster_members WHERE source_item_id='anchor'"
        ).fetchone()[0]
        assert original_cluster == cluster


@pytest.mark.parametrize("repair", ["missing", "outdated"])
def test_index_repair_preserves_exact_frequencies_and_is_idempotent(tmp_path, repair):
    path = tmp_path / "repair.db"
    with m.NewsStore(path, source_key="test") as store:
        _commit_chunks(store, _noise_rows(4))
        expected = _index_state(store._conn)
        cluster = store._conn.execute(
            "SELECT cluster_id FROM news_cluster_fingerprints ORDER BY cluster_id LIMIT 1"
        ).fetchone()[0]
    with sqlite3.connect(path) as conn:
        if repair == "missing":
            conn.execute("DELETE FROM news_cluster_fingerprints WHERE cluster_id=?", (cluster,))
        else:
            conn.execute(
                "UPDATE news_cluster_fingerprints SET indexed_policy='outdated-fixture' WHERE cluster_id=?",
                (cluster,),
            )
    with m.NewsStore(path, source_key="test") as store:
        assert _index_state(store._conn) == expected
        actual = {
            (row[0], row[1]): row[2] for row in store._conn.execute(
                "SELECT security_id, shingle, COUNT(*) FROM news_cluster_postings GROUP BY security_id, shingle"
            )
        }
        recorded = {
            (row[0], row[1]): row[2] for row in store._conn.execute(
                "SELECT security_id, shingle, df FROM news_shingle_df"
            )
        }
        assert recorded == actual
        plan = " ".join(row[3] for row in store._conn.execute(
            "EXPLAIN QUERY PLAN SELECT security_id, shingle FROM news_cluster_postings WHERE cluster_id=?",
            (cluster,),
        ))
        assert "idx_news_cluster_postings_cluster" in plan
    with m.NewsStore(path, source_key="test") as store:
        assert _index_state(store._conn) == expected


def test_identity_anchor_is_inside_the_fingerprint_budget(tmp_path):
    first = "Nvidia reports Q1 revenue of $8 billion"
    second = "Nvidia reports Q2 revenue of $9 billion"
    with m.NewsStore(tmp_path / "identity-budget.db", source_key="test") as store:
        store.commit_observations([_routed("a", first), _routed("b", second, second=1)])
        anchor = store._conn.execute(
            "SELECT cluster_id, anchor_story_id FROM news_clusters WHERE anchor_title=?", (first,),
        ).fetchone()
        candidates, evidence = retrieve_candidates(
            store._conn,
            ClusterItem(
                source="benzinga", source_item_id="a", title=second,
                observed_at=T0 + timedelta(seconds=3), subject_ids=("sec-NVDA",),
            ),
            policy=ClusterPolicy(), budgets=RetrievalBudgets(candidate_fingerprints=1),
        )
        assert evidence.candidates_surfaced > 1
        assert evidence.candidates_fingerprinted <= 1
        assert evidence.retrieval_truncated is True
        assert [candidate.cluster_id for candidate in candidates] == [anchor["cluster_id"]]


def test_recency_fallback_keeps_the_newest_bounded_horizon(tmp_path):
    with m.NewsStore(tmp_path / "fallback-order.db", source_key="test") as store:
        _commit_chunks(store, _noise_rows(4))
        latest = store._conn.execute(
            "SELECT cluster_id FROM news_clusters ORDER BY anchor_observed_at DESC LIMIT 1"
        ).fetchone()[0]
        candidates, evidence = retrieve_candidates(
            store._conn,
            ClusterItem(
                source="benzinga", source_item_id="fresh-fixture", title="Unrelated fixture",
                observed_at=T0 + timedelta(seconds=10), subject_ids=("sec-NVDA",),
            ),
            policy=ClusterPolicy(title_threshold=0.0, max_candidates=1),
        )
        assert [candidate.cluster_id for candidate in candidates] == [latest]
        assert evidence.retrieval_truncated is True


def test_indexed_window_uses_equal_utc_instants_with_different_offsets(tmp_path):
    with m.NewsStore(tmp_path / "utc-window.db", source_key="test") as store:
        store.commit_observations([_routed("anchor", ANCHOR_TITLE)])
        candidates, evidence = retrieve_candidates(
            store._conn,
            ClusterItem(
                source="benzinga", source_item_id="fresh-fixture", title=DUP_TITLE,
                observed_at=(T0 + timedelta(seconds=3)).astimezone(timezone(timedelta(hours=8))),
                subject_ids=("sec-NVDA",),
            ),
            policy=ClusterPolicy(),
        )
        assert len(candidates) == 1
        assert evidence.retrieval_truncated is False
