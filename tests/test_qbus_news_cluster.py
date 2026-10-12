from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.qbus_news_cluster import ClusterCandidate, ClusterItem, ClusterPolicy, cluster_candidates, new_cluster_id

UTC = timezone.utc
T0 = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def item(source_item_id: str, title: str, *, source="benzinga", subjects=("sec-NVDA",), at=T0, family="company"):
    return ClusterItem(
        source=source,
        source_item_id=source_item_id,
        title=title,
        observed_at=at,
        subject_ids=tuple(subjects),
        event_family=family,
    )


def cand(cluster_id: str, anchor: ClusterItem):
    return ClusterCandidate(
        cluster_id=cluster_id,
        anchor_story_id=anchor.story_id,
        anchor_title=anchor.title,
        anchor_observed_at=anchor.observed_at,
        subject_ids=anchor.subject_ids,
        event_family=anchor.event_family,
    )


def test_same_upstream_item_across_routes_is_same_story_identity():
    incoming = item("39046904", "Cava raises guidance")
    existing = item("39046904", "Cava raises full-year guidance")
    decision = cluster_candidates(incoming, [cand("ev2_existing", existing)], policy=ClusterPolicy())
    assert incoming.story_id == existing.story_id == "benzinga:39046904"
    assert decision.action == "join"
    assert decision.cluster_id == "ev2_existing"
    assert decision.reason == "same_source_item"


def test_independent_same_event_joins_existing_cluster_without_rekeying():
    anchor = item("1", "Nvidia unveils new AI accelerator for data centers", source="benzinga")
    incoming = item("r-9", "Nvidia unveils new AI accelerator for data centres", source="reuters")
    decision = cluster_candidates(incoming, [cand("ev2_original", anchor)], policy=ClusterPolicy(title_threshold=0.72))
    assert decision.action == "join"
    assert decision.cluster_id == "ev2_original"
    assert decision.matched_story_id == anchor.story_id
    assert new_cluster_id(incoming) != "ev2_original"


def test_material_guidance_numbers_prevent_false_merge():
    anchor = item("1", "Company guides 2027 revenue to $8.2B")
    incoming = item("2", "Company guides 2027 revenue to $9.1B")
    d = cluster_candidates(incoming, [cand("ev2_a", anchor)], policy=ClusterPolicy(title_threshold=0.5))
    assert d.action == "new"
    assert d.reason == "no_safe_match"


def test_negation_and_direction_changes_prevent_false_merge():
    pairs = [
        ("FTC approves Company acquisition", "FTC does not approve Company acquisition"),
        ("Broker upgrades NVDA to Buy", "Broker downgrades NVDA to Sell"),
        ("Company confirms merger talks", "Company denies merger talks"),
        ("Company reportedly explores sale", "Company confirms sale agreement"),
        ("Company reports Q1 revenue growth", "Company reports Q2 revenue growth"),
    ]
    for i, (a, b) in enumerate(pairs):
        d = cluster_candidates(item(f"b{i}", b), [cand(f"ev2_{i}", item(f"a{i}", a))], policy=ClusterPolicy(title_threshold=0.45))
        assert d.action == "new", (a, b, d)


def test_different_analyst_firms_do_not_merge_rating_actions():
    anchor = item("1", "Goldman Sachs upgrades NVDA to Buy")
    incoming = item("2", "Morgan Stanley upgrades NVDA to Buy")
    d = cluster_candidates(incoming, [cand("ev2_a", anchor)], policy=ClusterPolicy(title_threshold=0.45))
    assert d.action == "new"


def test_shared_theme_without_shared_security_is_never_enough():
    anchor = item("1", "AI demand accelerates", subjects=("sec-NVDA",), family="theme")
    incoming = item("2", "AI demand accelerates", subjects=("sec-MSFT",), family="theme")
    d = cluster_candidates(incoming, [cand("ev2_a", anchor)], policy=ClusterPolicy(title_threshold=0.1))
    assert d.action == "new"
    assert d.reason == "no_safe_match"


def test_different_event_families_do_not_merge_even_with_identical_title():
    anchor = item("1", "Nvidia update", family="analyst")
    incoming = item("2", "Nvidia update", family="earnings")
    d = cluster_candidates(incoming, [cand("ev2_a", anchor)], policy=ClusterPolicy(title_threshold=0.1))
    assert d.action == "new"


def test_out_of_window_candidate_is_not_compared_as_same_event():
    anchor = item("1", "Nvidia unveils new AI accelerator", at=T0 - timedelta(days=2))
    incoming = item("2", "Nvidia unveils new AI accelerator", at=T0)
    d = cluster_candidates(incoming, [cand("ev2_a", anchor)], policy=ClusterPolicy(window_seconds=6 * 3600, title_threshold=0.1))
    assert d.action == "new"


def test_anchor_comparison_prevents_transitive_chain_merge():
    anchor = item("1", "Company launches AI chip platform for servers")
    incoming = item("3", "Company launches AI software platform for consumers")
    d = cluster_candidates(incoming, [cand("ev2_anchor", anchor)], policy=ClusterPolicy(title_threshold=0.72))
    assert d.action == "new"


def test_candidate_budget_is_bounded_and_truncation_is_visible():
    candidates = [
        cand(f"ev2_{i}", item(str(i), f"Unrelated headline number {i}", subjects=("sec-NVDA",), at=T0 - timedelta(seconds=i)))
        for i in range(200)
    ]
    incoming = item("new", "Completely different event for Nvidia")
    d = cluster_candidates(incoming, candidates, policy=ClusterPolicy(max_candidates=32, title_threshold=0.95))
    assert d.action == "new"
    assert d.candidates_examined <= 32
    assert d.candidate_truncated is True


def test_new_cluster_id_is_stable_for_story_identity_not_headline_text():
    a = item("123", "First headline")
    b = item("123", "Corrected headline")
    assert new_cluster_id(a) == new_cluster_id(b)
