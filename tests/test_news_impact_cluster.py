"""Hermetic tests for engine/news_impact/cluster.py (lane B3_cluster).

Stdlib + owner only; no network, no repo data files, no clock, no randomness.
Owner surface under test is imported from engine.qbus_news_cluster; the
wrapper's own module is imported as `cl` so error-path tests can substitute
its `cluster_candidates` binding with crafted owner decisions and restore it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import engine.news_impact.cluster as cl
from engine.news_impact.cluster import (
    CLUSTERER_VERSION,
    CLUSTER_GRAINS,
    NOVELTY_RULES,
    NOVELTY_VALUES,
    Article,
    FactObservation,
    NoveltyError,
    ReplayMismatch,
    assign_novelty,
    cluster_articles,
    cluster_grain_for,
    replay,
)
from engine.qbus_news_cluster import ClusterDecision, ClusterPolicy

UTC = timezone.utc
CIK = "cik:0000320193"


def art(
    source: str,
    item_id: str,
    title: str,
    at: datetime,
    subjects: tuple[str, ...] = (CIK,),
    family: str = "",
    sha: str = "",
) -> Article:
    return Article(
        source=source,
        source_item_id=item_id,
        title=title,
        observed_at=at,
        subject_ids=subjects,
        event_family=family,
        source_sha256=sha,
    )


T0 = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
GUIDANCE = "Acme raises full-year revenue guidance for FY26"


# --------------------------------------------------------------------------
# clustering over the owner
# --------------------------------------------------------------------------


def test_two_outlets_same_story_within_window_one_cluster() -> None:
    articles = [
        art("wire_a", "1", GUIDANCE, T0),
        art("daily_b", "77", GUIDANCE, T0 + timedelta(hours=1)),
    ]
    run = cluster_articles(articles)
    assert len(run.clusters) == 1
    cluster = run.clusters[0]
    assert cluster.member_story_ids == ("wire_a:1", "daily_b:77")
    assert cluster.sources == ("daily_b", "wire_a")
    assert cluster.subject_ids == (CIK,)
    assert run.receipts[0].action == "new"
    assert run.receipts[1].action == "join"
    assert run.receipts[1].reason == "anchor_title_match"
    assert run.receipts[1].matched_story_id == "wire_a:1"
    assert run.receipts[1].similarity == pytest.approx(1.0)


def test_same_title_outside_window_two_clusters() -> None:
    articles = [
        art("wire_a", "1", GUIDANCE, T0),
        art("daily_b", "77", GUIDANCE, T0 + timedelta(hours=7)),
    ]
    run = cluster_articles(articles)
    assert len(run.clusters) == 2
    assert [r.action for r in run.receipts] == ["new", "new"]
    assert run.receipts[1].reason == "no_safe_match"


def test_differing_numbers_two_clusters() -> None:
    articles = [
        art("wire_a", "1", "Acme guides FY26 revenue of $2.5 billion", T0),
        art("daily_b", "77", "Acme guides FY26 revenue of $3.1 billion", T0 + timedelta(hours=1)),
    ]
    run = cluster_articles(articles)
    assert len(run.clusters) == 2
    assert run.receipts[1].reason == "no_safe_match"


def _shuffle_corpus() -> list[Article]:
    return [
        art("wire_a", "1", GUIDANCE, T0),
        art("daily_b", "77", GUIDANCE, T0 + timedelta(minutes=10)),
        art("site_c", "x9", GUIDANCE, T0 + timedelta(minutes=20)),
        art("wire_a", "2", "Acme names new chief financial officer", T0 + timedelta(minutes=5)),
        art("tv_d", "5k", "Acme names new chief financial officer", T0 + timedelta(minutes=30)),
        art("radio_e", "q", "Acme opens new packaging plant in Ohio", T0 + timedelta(minutes=2)),
    ]


def test_shuffle_invariance_of_run_sha256() -> None:
    corpus = _shuffle_corpus()
    baseline = cluster_articles(corpus)
    permutations = [
        list(reversed(corpus)),
        corpus[3:] + corpus[:3],
        sorted(corpus, key=lambda a: a.title),
    ]
    assert len(permutations) == 3
    for permuted in permutations:
        run = cluster_articles(permuted)
        assert run.run_sha256 == baseline.run_sha256
        assert run.clusters == baseline.clusters
        assert run.receipts == baseline.receipts
    assert len(baseline.clusters) == 3


def test_replay_identity_same_run_sha256() -> None:
    corpus = _shuffle_corpus()
    run = cluster_articles(corpus)
    rerun = replay(corpus, run.receipts, policy=ClusterPolicy())
    assert rerun.run_sha256 == run.run_sha256
    assert rerun == run


def test_replay_tampered_receipt_raises_naming_story() -> None:
    corpus = _shuffle_corpus()
    run = cluster_articles(corpus)
    tampered = list(run.receipts)
    tampered[2] = cl.JoinReceipt(
        story_id=tampered[2].story_id,
        action=tampered[2].action,
        cluster_id=tampered[2].cluster_id,
        matched_story_id=tampered[2].matched_story_id,
        similarity=0.123456,
        reason=tampered[2].reason,
        candidates_examined=tampered[2].candidates_examined,
        candidate_truncated=tampered[2].candidate_truncated,
    )
    with pytest.raises(ReplayMismatch) as excinfo:
        replay(corpus, tampered, policy=ClusterPolicy())
    assert "story_id=" in str(excinfo.value)
    assert tampered[2].story_id in str(excinfo.value)


def test_replay_truncated_receipts_raise_on_count() -> None:
    corpus = _shuffle_corpus()
    run = cluster_articles(corpus)
    with pytest.raises(ReplayMismatch) as excinfo:
        replay(corpus, run.receipts[:-2], policy=ClusterPolicy())
    assert "count divergence" in str(excinfo.value)


def test_naive_datetime_raises_value_error() -> None:
    naive = art("wire_a", "1", GUIDANCE, datetime(2026, 10, 12, 9, 0))
    assert naive.observed_at.tzinfo is None
    with pytest.raises(ValueError, match="cluster times must be timezone-aware"):
        cluster_articles([naive])


def test_two_runs_deterministic() -> None:
    corpus = _shuffle_corpus()
    assert cluster_articles(corpus) == cluster_articles(corpus)
    assert cluster_articles(corpus).run_sha256 == cluster_articles(corpus).run_sha256


def test_empty_input_empty_run() -> None:
    run = cluster_articles([])
    assert run.clusters == ()
    assert run.receipts == ()
    assert run.clusterer_version == CLUSTERER_VERSION == "ni-cluster-1"
    assert len(run.run_sha256) == 64


def test_duplicate_story_id_rejoins_same_source_item() -> None:
    articles = [
        art("wire_a", "1", GUIDANCE, T0),
        art("wire_a", "1", GUIDANCE, T0 + timedelta(minutes=5)),
    ]
    run = cluster_articles(articles)
    assert len(run.clusters) == 1
    assert run.receipts[1].reason == "same_source_item"
    assert run.receipts[1].similarity == 1.0


# --------------------------------------------------------------------------
# error paths around the owner decision (substituted decisions, restored)
# --------------------------------------------------------------------------


def _with_stub_decision(decision: ClusterDecision, articles: list[Article]) -> None:
    real = cl.cluster_candidates
    cl.cluster_candidates = lambda incoming, candidates, *, policy: decision
    try:
        cluster_articles(articles, policy=ClusterPolicy())
    finally:
        cl.cluster_candidates = real


def test_unknown_decision_action_raises_exact_code() -> None:
    decision = ClusterDecision("merge", "ev2_0", None, 0.0, "stub", 0, False)
    with pytest.raises(ValueError, match="unknown cluster decision action: 'merge'"):
        _with_stub_decision(decision, [art("wire_a", "1", GUIDANCE, T0)])


def test_join_unknown_cluster_raises_exact_code() -> None:
    decision = ClusterDecision("join", "ev2_missing", "wire_a:1", 1.0, "stub", 1, False)
    with pytest.raises(ValueError, match="join decision names unknown cluster: ev2_missing"):
        _with_stub_decision(decision, [art("wire_a", "1", GUIDANCE, T0)])


def test_cluster_id_collision_raises_exact_code() -> None:
    first = art("wire_a", "1", GUIDANCE, T0)
    second = art("daily_b", "77", GUIDANCE, T0 + timedelta(hours=1))
    real = cl.cluster_candidates
    try:
        # Mint the real first cluster id, then force the second "new" onto it.
        collide_id = cluster_articles([first], policy=ClusterPolicy()).clusters[0].cluster_id
        decision = ClusterDecision("new", collide_id, None, 0.0, "stub", 0, False)
        cl.cluster_candidates = lambda incoming, candidates, *, policy: decision
        with pytest.raises(ValueError, match="cluster id collision: " + collide_id):
            cluster_articles([first, second], policy=ClusterPolicy())
    finally:
        cl.cluster_candidates = real


# --------------------------------------------------------------------------
# cluster grain
# --------------------------------------------------------------------------


def test_cluster_grain_article_manifestation_multi_outlet() -> None:
    run = cluster_articles(
        [
            art("wire_a", "1", GUIDANCE, T0),
            art("daily_b", "77", GUIDANCE, T0 + timedelta(hours=1)),
        ]
    )
    grain = cluster_grain_for(run.clusters[0], same_fact=True)
    assert grain == "article_manifestation"
    assert grain in CLUSTER_GRAINS


def test_cluster_grain_article_manifestation_single_article() -> None:
    run = cluster_articles([art("wire_a", "1", GUIDANCE, T0)])
    assert cluster_grain_for(run.clusters[0], same_fact=True) == "article_manifestation"


def test_cluster_grain_fact_revision_same_outlet_twice() -> None:
    run = cluster_articles(
        [
            art("wire_a", "1", GUIDANCE, T0),
            art("wire_a", "2", GUIDANCE, T0 + timedelta(hours=1)),
        ]
    )
    cluster = run.clusters[0]
    assert cluster.member_story_ids == ("wire_a:1", "wire_a:2")
    assert cluster.sources == ("wire_a",)
    assert cluster_grain_for(cluster, same_fact=True) == "fact_revision"


def test_cluster_grain_thesis_link_only_when_cross_fact() -> None:
    run = cluster_articles([art("wire_a", "1", GUIDANCE, T0)])
    assert cluster_grain_for(run.clusters[0], same_fact=False) == "thesis_link"


# --------------------------------------------------------------------------
# novelty rule table
# --------------------------------------------------------------------------


KEY = ("cik:0000320193", "revenue", "FY26", "reported")
STAGE_KEY = ("cik:0001045810", "deployment stage 2", "FY27", "reported")
WHEN = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)


def obs(
    fact_key: tuple[str, str, str, str] = KEY,
    quantity: str | None = None,
    counterparty: str | None = None,
    commitment: str | None = None,
    source_family: str = "wire",
    is_correction: bool = False,
    supersedes_fact_id: str | None = None,
    fact_id: str = "fact_" + "0" * 24,
) -> FactObservation:
    return FactObservation(
        fact_key=fact_key,
        quantity=quantity,
        counterparty=counterparty,
        commitment=commitment,
        observed_at=WHEN,
        source_family=source_family,
        is_correction=is_correction,
        supersedes_fact_id=supersedes_fact_id,
        fact_id=fact_id,
    )


def test_novelty_rule_table_shape_and_order() -> None:
    ids = [row.split(":", 1)[0] for row in NOVELTY_RULES]
    # Execution order: N5 is checked before N3 by commission.
    assert ids == ["N1", "N2", "N5", "N3", "N4"]
    assert len(NOVELTY_RULES) == 5


def test_n1_correction_routes_and_echoes_supersedes() -> None:
    decision = assign_novelty(
        [obs(quantity="5.0")], obs(quantity="4.5", is_correction=True, supersedes_fact_id="fact_" + "a" * 24)
    )
    assert decision.value == "corrected_fact"
    assert decision.rule == NOVELTY_RULES[0]
    assert decision.rule.startswith("N1")
    assert decision.supersedes_fact_id == "fact_" + "a" * 24


def test_n1_without_supersedes_raises_novelty_error_exact_code() -> None:
    with pytest.raises(NoveltyError) as excinfo:
        assign_novelty([], obs(is_correction=True, supersedes_fact_id=None))
    assert (
        str(excinfo.value)
        == "supersedes_required: corrected_fact requires supersedes_fact_id"
    )


def test_n2_first_observation_quantified() -> None:
    decision = assign_novelty([], obs(quantity="5.0"))
    assert decision.value == "new_magnitude_timing_commitment_counterparty"
    assert decision.rule.startswith("N2")
    assert decision.supersedes_fact_id is None


def test_n2_first_observation_commentary() -> None:
    decision = assign_novelty([], obs())
    assert decision.value == "commentary"
    assert decision.rule.startswith("N2")


def test_n3_same_values_rereported() -> None:
    decision = assign_novelty([obs(quantity="5.0")], obs(quantity="5.0"))
    assert decision.value == "new_reporting_of_old_fact"
    assert decision.rule.startswith("N3")


def test_n4_changed_quantity() -> None:
    decision = assign_novelty([obs(quantity="5.0")], obs(quantity="6.0"))
    assert decision.value == "new_magnitude_timing_commitment_counterparty"
    assert decision.rule.startswith("N4")


def test_n4_changed_counterparty_or_commitment() -> None:
    prior = obs(quantity="5.0", counterparty="cik:0001018723")
    for changed in (
        obs(quantity="5.0", counterparty="cik:0001652044"),
        obs(quantity="5.0", commitment="binding"),
    ):
        decision = assign_novelty([prior], changed)
        assert decision.value == "new_magnitude_timing_commitment_counterparty"
        assert decision.rule.startswith("N4")


def test_n5_independent_milestone_beats_n3() -> None:
    prior = obs(fact_key=STAGE_KEY, quantity="100", source_family="wire")
    new = obs(fact_key=STAGE_KEY, quantity="100", source_family="vendor_blog")
    # Both N3 (same values) and N5 match; N5 is checked first.
    decision = assign_novelty([prior], new)
    assert decision.value == "independently_observed_milestone"
    assert decision.rule.startswith("N5")


def test_n5_blocked_when_metric_is_not_a_stage_or_milestone() -> None:
    prior = obs(quantity="100", source_family="wire")
    new = obs(quantity="100", source_family="vendor_blog")
    decision = assign_novelty([prior], new)
    assert decision.value == "new_reporting_of_old_fact"  # falls through to N3
    assert decision.rule.startswith("N3")


def test_n5_blocked_when_source_family_already_observed() -> None:
    prior = obs(fact_key=STAGE_KEY, quantity="100", source_family="wire")
    new = obs(fact_key=STAGE_KEY, quantity="100", source_family="wire")
    decision = assign_novelty([prior], new)
    assert decision.value == "new_reporting_of_old_fact"
    assert decision.rule.startswith("N3")


def test_n5_blocked_when_values_differ() -> None:
    prior = obs(fact_key=STAGE_KEY, quantity="100", source_family="wire")
    new = obs(fact_key=STAGE_KEY, quantity="200", source_family="vendor_blog")
    decision = assign_novelty([prior], new)
    assert decision.value == "new_magnitude_timing_commitment_counterparty"
    assert decision.rule.startswith("N4")


def test_novelty_values_are_the_frozen_enum() -> None:
    assert set(NOVELTY_VALUES) == {
        "new_reporting_of_old_fact",
        "corrected_fact",
        "new_magnitude_timing_commitment_counterparty",
        "independently_observed_milestone",
        "commentary",
    }


def test_assign_novelty_deterministic_and_history_order_free() -> None:
    history = [
        obs(quantity="5.0", source_family="wire"),
        obs(quantity="5.0", source_family="tv"),
    ]
    new = obs(quantity="6.0")
    assert assign_novelty(history, new) == assign_novelty(list(reversed(history)), new)
    assert assign_novelty(history, new) == assign_novelty(history, new)
