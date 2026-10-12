"""False-positive traps for qbus news clustering.

Each blocked pair is similar enough to join under the default title threshold.
The assertion on similarity is what makes the trap able to fail: deleting the
named discriminator turns the decision into a join.
"""
from __future__ import annotations

from datetime import timedelta
import random

from engine.qkernel import title_similarity
from engine.qbus_news_cluster import ClusterPolicy, cluster_candidates, new_cluster_id
from tests.test_qbus_news_cluster import T0, cand, item


def _blocked(left: str, right: str, **incoming):
    anchor = item("anchor", left)
    incoming_item = item("incoming", right, source="reuters", **incoming)
    assert title_similarity(left, right) >= ClusterPolicy().title_threshold
    decision = cluster_candidates(
        incoming_item, [cand("ev2_anchor", anchor)], policy=ClusterPolicy()
    )
    assert decision.action == "new"
    assert decision.reason == "no_safe_match"
    assert decision.cluster_id == new_cluster_id(incoming_item)
    return decision


def _joined(left: str, right: str):
    anchor = item("anchor", left)
    incoming_item = item("incoming", right, source="reuters")
    decision = cluster_candidates(
        incoming_item, [cand("ev2_anchor", anchor)], policy=ClusterPolicy()
    )
    assert decision.action == "join"
    assert decision.reason == "anchor_title_match"
    assert decision.cluster_id == "ev2_anchor"
    assert decision.matched_story_id == anchor.story_id
    return decision


def test_q2_does_not_join_q3():
    """Dropping the period inequality in _compatible joins these titles."""
    _blocked("Apple reports Q2 revenue growth", "Apple reports Q3 revenue growth")


def test_fy25_does_not_join_fy26():
    """Dropping the period inequality in _compatible joins these titles."""
    _blocked("Apple reports FY25 results", "Apple reports FY26 results")


def test_raises_guidance_does_not_join_cuts_guidance():
    """Dropping the action-overlap check in _compatible joins these titles."""
    _blocked(
        "Apple raises full-year guidance after strong demand",
        "Apple cuts full-year guidance after strong demand",
    )


def test_negation_not_in_talks_does_not_join():
    """Dropping the negation-polarity check in _compatible joins these titles."""
    _blocked(
        "Apple is not in talks to buy Disney",
        "Apple is in talks to buy Disney",
    )


def test_different_analyst_firms_do_not_join():
    """Dropping the analyst-actor check in _compatible joins these titles."""
    _blocked(
        "Goldman Sachs upgrades NVDA to Overweight on sustained AI demand",
        "Morgan Stanley upgrades NVDA to Overweight on sustained AI demand",
    )


def test_same_firm_different_price_targets_do_not_join():
    """Dropping the number-set check in _compatible joins these titles."""
    _blocked(
        "Goldman Sachs raises NVDA price target to $150",
        "Goldman Sachs raises NVDA price target to $175",
    )


def test_different_subject_security_ids_do_not_join():
    """Dropping the shared-subject check joins these identical titles."""
    anchor = item("anchor", "Apple unveils new product line for developers")
    incoming = item(
        "incoming",
        "Apple unveils new product line for developers",
        source="reuters",
        subjects=("sec-MSFT",),
    )
    assert title_similarity(anchor.title, incoming.title) == 1.0
    decision = cluster_candidates(
        incoming, [cand("ev2_anchor", anchor)], policy=ClusterPolicy()
    )
    assert decision.action == "new"
    assert decision.reason == "no_safe_match"


def test_outside_window_seconds_does_not_join():
    """Deleting the window comparison joins these identical titles."""
    anchor = item("anchor", "Apple unveils new product line for developers")
    incoming = item(
        "incoming",
        "Apple unveils new product line for developers",
        source="reuters",
        at=T0 + timedelta(seconds=ClusterPolicy().window_seconds + 1),
    )
    decision = cluster_candidates(
        incoming, [cand("ev2_anchor", anchor)], policy=ClusterPolicy()
    )
    assert decision.action == "new"
    assert decision.reason == "no_safe_match"
    assert decision.candidate_truncated is False


def test_identical_syndicated_headline_joins():
    """Forcing title_similarity to 0, or always returning new, fails this join."""
    decision = _joined(
        "Apple unveils new product line for developers",
        "Apple unveils new product line for developers",
    )
    assert decision.similarity == 1.0
    assert decision.candidate_truncated is False


def test_punctuation_and_case_only_differences_join():
    """Shingling the raw title instead of norm_title drops similarity under 0.72."""
    decision = _joined("NVIDIA Unveils New AI Chip!", "nvidia unveils new ai chip")
    assert decision.similarity == 1.0


def test_over_max_candidates_is_truncated_and_deterministic():
    """Examining every candidate, or keeping input order, selects ev2_trunc."""
    incoming_title = "Apple unveils a new product line for developers"
    weak_title = "Apple shows a new product line for developers"
    assert ClusterPolicy().title_threshold <= title_similarity(
        incoming_title, weak_title
    ) < 1.0
    incoming = item("incoming", incoming_title, source="reuters")
    candidates = []
    for age in range(128):
        if age == 1:
            title = weak_title
            cluster_id = "ev2_kept"
            source_item_id = "kept"
        else:
            title = f"Unrelated copper warehouse note {age} from peru mines"
            cluster_id = f"ev2_fill_{age:04d}"
            source_item_id = f"fill-{age}"
        anchor = item(source_item_id, title, at=T0 - timedelta(seconds=age))
        candidates.append(cand(cluster_id, anchor))
    perfect = item(
        "perfect",
        incoming_title,
        at=T0 - timedelta(seconds=128),
    )
    candidates.append(cand("ev2_trunc", perfect))
    assert len(candidates) == 129

    def choose(order):
        return cluster_candidates(incoming, order, policy=ClusterPolicy())

    first = choose(candidates)
    assert first.candidate_truncated is True
    assert first.candidates_examined == ClusterPolicy().max_candidates
    assert first.action == "join"
    assert first.cluster_id == "ev2_kept"
    rng = random.Random(0)
    for _ in range(20):
        order = candidates[:]
        rng.shuffle(order)
        assert choose(order) == first
    assert choose(list(reversed(candidates))) == first


def test_tie_break_is_deterministic_under_shuffle():
    """Picking the greater cluster_id, or the first examined row, selects ev2_m."""
    title = "Apple unveils new product line for developers"
    newer = item("1", title, source="benzinga", at=T0)
    older = item("2", title, source="reuters", at=T0 - timedelta(seconds=60))
    candidates = [cand("ev2_m", newer), cand("ev2_b", older)]
    incoming = item("3", title, source="wsj")
    rng = random.Random(1)
    seen = []
    for _ in range(20):
        order = candidates[:]
        rng.shuffle(order)
        decision = cluster_candidates(incoming, order, policy=ClusterPolicy())
        seen.append(decision)
    assert len(set(seen)) == 1
    decision = seen[0]
    assert decision.action == "join"
    assert decision.cluster_id == "ev2_b"
    assert decision.matched_story_id == older.story_id
    assert decision.similarity == 1.0
    assert decision.candidate_truncated is False


def test_new_cluster_id_is_stable_for_the_same_item():
    """Mixing the headline or a random salt into new_cluster_id changes the digest."""
    first = item("39046904", "Cava raises guidance")
    renamed = item("39046904", "Cava raises full-year guidance")
    assert new_cluster_id(first) == new_cluster_id(renamed)
    assert new_cluster_id(first) == "ev2_6e154c9be35e1cd8"
    decision = cluster_candidates(first, [], policy=ClusterPolicy())
    assert decision.action == "new"
    assert decision.cluster_id == new_cluster_id(first)
    again = cluster_candidates(first, [], policy=ClusterPolicy())
    assert again.cluster_id == decision.cluster_id


def test_million_does_not_join_billion():
    """Leaving word scales off _NUM_RE compares both titles as {$5, 2027} and joins."""
    _blocked(
        "Company guides 2027 revenue to $5 million",
        "Company guides 2027 revenue to $5 billion",
    )


def test_same_million_magnitude_still_joins():
    """Rejecting every title that contains 'million' fails this same-scale join."""
    _joined(
        "Company guides 2027 revenue to $5 million",
        "Company guides 2027 revenue to $5 million",
    )


def test_stuck_bn_scale_does_not_join_different_amount():
    """A number regex that still misses the bn suffix joins $5bn with $9bn."""
    _blocked(
        "Company guides revenue to $5bn after demand",
        "Company guides revenue to $9bn after demand",
    )


def test_same_stuck_bn_scale_still_joins():
    """Treating bn as an unconditional reject fails this repeated headline."""
    _joined(
        "Company guides revenue to $5bn after demand",
        "Company guides revenue to $5bn after demand",
    )


def test_letter_scale_does_not_collapse_onto_word_or_bn():
    """Canonicalizing $5B, $5bn and $5 billion onto one token joins these pairs."""
    _blocked(
        "Company guides revenue to $5B after strong demand this year",
        "Company guides revenue to $5 billion after strong demand this year",
    )
    _blocked(
        "Company guides revenue to $5B after strong demand this year",
        "Company guides revenue to $5bn after strong demand this year",
    )


def test_quarter_suffix_2q_does_not_join_3q():
    """A period regex without the [1-4]Q form joins 2Q with 3Q."""
    _blocked("Apple reports 2Q revenue growth", "Apple reports 3Q revenue growth")


def test_quarter_suffix_still_joins_canonical_q2():
    """Storing 2Q as a different token from Q2 splits this same quarter."""
    _joined(
        "Apple reports 2Q revenue growth across its devices and services",
        "Apple reports Q2 revenue growth across its devices and services",
    )


def test_compact_2q25_does_not_join_3q25():
    """Ignoring the compact 2Q25 token joins different quarters in the same year."""
    _blocked(
        "Apple reports 2Q25 revenue growth",
        "Apple reports 3Q25 revenue growth",
    )


def test_compact_2q25_does_not_join_2q26():
    """Keeping only the quarter digit from 2Q25 joins different fiscal years."""
    _blocked(
        "Apple reports 2Q25 revenue growth",
        "Apple reports 2Q26 revenue growth",
    )


def test_compact_2q25_still_joins_q2_fy25():
    """A year token other than FY25 splits this same quarter and year."""
    _joined(
        "Apple reports 2Q25 revenue growth across devices",
        "Apple reports Q2 FY25 revenue growth across devices",
    )


def test_spelled_second_quarter_does_not_join_third():
    """A period list without spelled quarters joins second-quarter with third-quarter."""
    _blocked(
        "Apple reports second-quarter revenue growth and updates its outlook for the rest of the year",
        "Apple reports third-quarter revenue growth and updates its outlook for the rest of the year",
    )


def test_spelled_second_quarter_still_joins_q2():
    """Labeling spelled quarters as anything other than Q2 splits this pair."""
    _joined(
        "Apple reports second-quarter revenue growth and updates its outlook for the rest of the year",
        "Apple reports Q2 revenue growth and updates its outlook for the rest of the year",
    )


def test_contraction_isnt_does_not_join():
    """A negation regex that only matches the whole word 'not' joins isn't with is."""
    _blocked(
        "Apple isn't in talks to acquire Disney this year",
        "Apple is in talks to acquire Disney this year",
    )


def test_curly_apostrophe_negation_does_not_join():
    """Skipping the curly-apostrophe fold joins isn’t with is."""
    _blocked(
        "Apple isn’t in talks to acquire Disney this year",
        "Apple is in talks to acquire Disney this year",
    )


def test_cannot_does_not_join_can():
    """A negation list without 'cannot' joins these confirmation headlines."""
    _blocked(
        "Apple cannot confirm merger talks with Disney this year",
        "Apple can confirm merger talks with Disney this year",
    )


def test_same_contraction_still_joins():
    """Treating any contraction as incompatible with every title fails this pair."""
    _joined(
        "Apple isn't in talks to acquire Disney this year",
        "Apple isn't in talks to acquire Disney this year",
    )


def test_beats_estimates_does_not_join_misses_estimates():
    """Dropping the outcome-polarity check in _compatible joins these titles."""
    _blocked(
        "Nvidia beats quarterly estimates on strong demand",
        "Nvidia misses quarterly estimates on strong demand",
    )


def test_upgrades_to_buy_does_not_join_opposite_target():
    """Dropping the rating-target check in _compatible joins these titles."""
    _blocked(
        "Citi upgrades NVDA to Buy on strong AI demand across its business",
        "Citi moves NVDA to Sell on strong AI demand across its business",
    )


def test_ends_talks_does_not_join_ongoing_talks():
    """Dropping the termination check in _compatible joins these titles."""
    _blocked(
        "Apple in talks to acquire Disney this week",
        "Apple ends talks to acquire Disney this week",
    )


def test_tops_estimates_still_joins_beats_estimates():
    """Splitting the beat family by surface verb splits this same-outcome pair."""
    _joined(
        "Nvidia beats quarterly estimates on strong demand",
        "Nvidia tops quarterly estimates on strong demand",
    )


def test_raised_to_buy_still_joins_upgrades_to_buy():
    """Splitting rating moves by verb instead of by target class splits this pair."""
    _joined(
        "Citi upgrades NVDA to Buy on strong AI demand",
        "Citi raised NVDA to Buy on strong AI demand",
    )


def test_two_ongoing_talks_reports_still_join():
    """Treating every talks headline as terminated splits this same-talks pair."""
    _joined(
        "Apple in talks to acquire Disney this week",
        "Apple is in talks to acquire Disney this week",
    )


def test_lifts_outlook_does_not_join_lowers_outlook():
    """Dropping the move-direction check in _compatible joins these titles."""
    _blocked(
        "Nvidia lifts full-year outlook on strong demand",
        "Nvidia lowers full-year outlook on strong demand",
    )


def test_hikes_outlook_does_not_join_lowers_outlook():
    """Dropping the move-direction check in _compatible joins these titles."""
    _blocked(
        "Nvidia hikes full-year outlook on strong demand",
        "Nvidia lowers full-year outlook on strong demand",
    )


def test_raised_outlook_does_not_join_lowered_outlook():
    """Dropping the move-direction check in _compatible joins these titles."""
    _blocked(
        "Citi raised its full-year outlook on demand",
        "Citi lowered its full-year outlook on demand",
    )


def test_lifts_price_target_does_not_join_trims_price_target():
    """Dropping the move-direction check in _compatible joins these titles."""
    _blocked(
        "Citi lifts NVDA price target to $150",
        "Citi trims NVDA price target to $150",
    )


def test_increased_does_not_join_decreased():
    """Dropping the move-direction check in _compatible joins these titles."""
    _blocked(
        "Retail sales increased in September",
        "Retail sales decreased in September",
    )


def test_lifts_outlook_still_joins_raises_outlook():
    """Splitting up-moves by surface verb splits this same-direction pair."""
    _joined(
        "Nvidia lifts full-year outlook on strong demand",
        "Nvidia raises full-year outlook on strong demand",
    )


def test_slashes_jobs_still_joins_cuts_jobs():
    """Splitting down-moves by surface verb splits this same-direction pair."""
    _joined(
        "Company slashes 500 jobs in restructuring",
        "Company cuts 500 jobs in restructuring",
    )


def test_resumes_talks_does_not_join_suspends_talks():
    """Dropping the termination check in _compatible joins these titles."""
    _blocked(
        "Apple resumes talks to acquire Disney this week",
        "Apple suspends talks to acquire Disney this week",
    )


def test_suspends_talks_still_joins_ends_talks():
    """Treating suspends as outside the terminated family splits this pair."""
    _joined(
        "Apple suspends talks to acquire Disney this week",
        "Apple ends talks to acquire Disney this week",
    )


def test_resumes_talks_still_joins_ongoing_talks():
    """Treating resumes as terminated splits this ongoing-talks pair."""
    _joined(
        "Apple resumes talks to acquire Disney this week",
        "Apple is in talks to acquire Disney this week",
    )
