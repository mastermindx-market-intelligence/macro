"""Contract tests for Finviz theme/subtheme repricing context.

The slice is descriptive only: it separates one-name bursts from broad cohort
participation without inventing alpha, fundamental durability, or trade authority.
"""
from engine import theme_repricing_context as rc
from engine import themes_heatmap as th


def _sub(members, group_1w, group_1m, rows):
    perf = {
        ticker: {"1W": w1, "1M": m1, "3M": m3}
        for ticker, w1, m1, m3 in rows
    }
    return rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=members,
        group_perf={"1W": group_1w, "1M": group_1m, "3M": 1.0},
        member_perf=perf,
    )


def test_single_name_impulse_is_not_broad_rerating():
    row = _sub(
        ["A", "B", "C", "D"], 3.0, 1.0,
        [
            ("A", 12.0, 6.0, 3.0),
            ("B", -1.0, -2.0, -1.0),
            ("C", -1.0, -1.0, -2.0),
            ("D", -1.0, -1.0, -1.0),
        ],
    )
    assert row["shape"] == "single_name_impulse"
    assert row["horizons"]["1W"]["up_share"] == 0.25
    assert row["horizons"]["1W"]["top_positive_move_share"] == 1.0
    assert row["price_leader"]["ticker"] == "A"
    assert row["durability_evidence"]["status"] == "fragile"
    assert row["durability_evidence"]["can_support_buy_decision"] is False


def test_broad_price_repricing_requires_cross_member_confirmation():
    row = _sub(
        ["A", "B", "C", "D"], 3.5, 7.0,
        [
            ("A", 5.0, 10.0, 12.0),
            ("B", 4.0, 8.0, 9.0),
            ("C", 3.0, 6.0, 7.0),
            ("D", 2.0, 4.0, 5.0),
        ],
    )
    assert row["shape"] == "broad_price_repricing"
    assert row["horizons"]["1W"]["up_share"] == 1.0
    assert row["horizons"]["1M"]["up_share"] == 1.0
    assert row["horizons"]["1W"]["top_positive_move_share"] < 0.45
    assert row["durability_evidence"]["status"] == "confirming"
    assert row["durability_evidence"]["fundamental_confirmation"] == "not_in_this_contract"


def test_fresh_broadening_is_separate_from_mature_confirmation():
    row = _sub(
        ["A", "B", "C", "D"], 4.0, -2.0,
        [
            ("A", 6.0, -3.0, -4.0),
            ("B", 5.0, -2.0, -3.0),
            ("C", 4.0, -1.0, -2.0),
            ("D", 3.0, -4.0, -5.0),
        ],
    )
    assert row["shape"] == "early_diffusion"
    assert row["durability_evidence"]["status"] == "forming"


def test_leadership_break_surfaces_as_exit_watch_not_exit_order():
    row = _sub(
        ["A", "B", "C", "D"], -2.0, 8.0,
        [
            ("A", -5.0, 9.0, 12.0),
            ("B", -2.0, 8.0, 10.0),
            ("C", -1.0, 7.0, 9.0),
            ("D", 1.0, 6.0, 8.0),
        ],
    )
    assert row["shape"] == "leadership_break"
    assert row["exit_watch"]["leadership_break"] is True
    assert row["durability_evidence"]["status"] == "weakening"
    assert row["durability_evidence"]["can_support_exit_decision"] is False


def test_missing_member_coverage_refuses_shape_instead_of_zero_filling():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C", "D", "E"],
        group_perf={"1W": 4.0, "1M": 5.0},
        member_perf={
            "A": {"1W": 10.0, "1M": 11.0},
            "B": {"1W": 8.0, "1M": 9.0},
        },
    )
    assert row["horizons"]["1W"]["coverage"] == 0.4
    assert row["shape"] == "insufficient_data"


def test_theme_rollup_distinguishes_diffusion_from_isolated_subtheme_move():
    tree = [{"theme": "Theme X", "subsectors": [
        {"key": "broad", "name": "Broad", "members": ["A", "B", "C", "D"]},
        {"key": "early", "name": "Early", "members": ["E", "F", "G", "H"]},
    ]}]
    group = {
        "broad": {"1W": 4.0, "1M": 6.0, "3M": 8.0},
        "early": {"1W": 3.8, "1M": -1.0, "3M": -4.0},
    }
    member = {
        "A": {"1W": 5.0, "1M": 8.0, "3M": 10.0},
        "B": {"1W": 4.0, "1M": 7.0, "3M": 9.0},
        "C": {"1W": 3.0, "1M": 6.0, "3M": 8.0},
        "D": {"1W": 2.0, "1M": 5.0, "3M": 7.0},
        "E": {"1W": 4.0, "1M": -1.0, "3M": -3.0},
        "F": {"1W": 3.5, "1M": -2.0, "3M": -4.0},
        "G": {"1W": 3.0, "1M": -3.0, "3M": -5.0},
        "H": {"1W": 2.5, "1M": -4.0, "3M": -6.0},
    }
    out = rc.build_context(tree, group, member)
    assert out["themes"][0]["state"] == "broad_subtheme_diffusion"
    assert out["themes"][0]["advancing_subtheme_share_1w"] == 1.0


def test_existing_heatmap_projection_carries_context_without_new_authority():
    tree = [{"theme": "Semiconductors", "subsectors": [
        {"key": "semiscompute", "name": "Compute", "description": "Compute",
         "members": ["A", "B", "C", "D"]},
    ]}]
    group = {"semiscompute": {"1D": 1.0, "1W": 4.0, "1M": 7.0, "3M": 9.0}}
    member = {
        "A": {"1D": 1.0, "1W": 5.0, "1M": 10.0, "3M": 12.0},
        "B": {"1D": 1.0, "1W": 4.0, "1M": 8.0, "3M": 9.0},
        "C": {"1D": 1.0, "1W": 3.0, "1M": 6.0, "3M": 7.0},
        "D": {"1D": 1.0, "1W": 2.0, "1M": 4.0, "3M": 5.0},
    }
    payload = th.build_themes_heatmap(tree, group, member, asof="2026-09-24")
    assert payload["tiles"][0]["repricing"]["shape"] == "broad_price_repricing"
    assert payload["repricing"]["schema"] == rc.SCHEMA
    assert payload["repricing"]["authority"]["may_rank"] is False
    assert payload["repricing"]["authority"]["may_trade"] is False
    assert (
        payload["repricing"]["scope"]["leader_semantics"]
        == "price_leader_not_validated_alpha_leader"
    )
    assert (
        payload["repricing"]["scope"]["move_concentration_basis"]
        == "equal_member_positive_return_magnitude_not_market_cap_contribution"
    )
    assert payload["repricing"]["n_subthemes"] == 1


def test_group_residual_leader_candidate_rewards_persistent_group_excess_not_one_spike():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C", "D"],
        group_perf={"1W": 5.0, "1M": 5.0, "3M": 5.0},
        member_perf={
            "A": {"1W": 6.0, "1M": 7.0, "3M": 8.0},
            "B": {"1W": 12.0, "1M": 4.0, "3M": 4.0},
            "C": {"1W": 4.0, "1M": 4.0, "3M": 4.0},
            "D": {"1W": 3.0, "1M": 3.0, "3M": 3.0},
        },
    )
    candidate = row["group_residual_leader_candidate"]
    assert candidate["ticker"] == "A"
    assert candidate["positive_residual_horizons"] == 3
    assert candidate["residual"] == {"1W": 1.0, "1M": 2.0, "3M": 3.0}
    assert candidate["semantics"] == "group_relative_leader_candidate_not_alpha"
    assert "not market sector or factor neutral" in candidate["limitations"]


def test_group_residual_leader_abstains_without_two_comparable_horizons():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C"],
        group_perf={"1W": 2.0},
        member_perf={
            "A": {"1W": 3.0},
            "B": {"1W": 2.0},
            "C": {"1W": 1.0},
        },
    )
    assert row["group_residual_leader_candidate"] is None


def test_leadership_handoff_requires_new_leader_up_and_former_leader_not_beating_group():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C", "D"],
        group_perf={"1W": 4.0, "1M": 8.0, "3M": 10.0},
        member_perf={
            "A": {"1W": 3.0, "1M": 12.0, "3M": 15.0},
            "B": {"1W": 8.0, "1M": 10.0, "3M": 12.0},
            "C": {"1W": 2.0, "1M": 6.0, "3M": 8.0},
            "D": {"1W": 1.0, "1M": 5.0, "3M": 7.0},
        },
    )
    lead = row["leadership"]
    assert lead["state"] == "handoff_candidate"
    assert lead["recent_leader"] == "B"
    assert lead["medium_horizon_leader"] == "A"
    assert lead["long_horizon_leader"] == "A"
    assert lead["recent_leader_1w_vs_group"] == 4.0
    assert lead["former_medium_leader_1w_vs_group"] == -1.0
    assert lead["semantics"] == "price_leadership_continuity_not_capital_flow"
    assert lead["can_support_rotate_decision"] is False
    assert row["exit_watch"]["leader_handoff_candidate"] is True


def test_same_recent_and_medium_leader_is_stable_recent_not_handoff():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C"],
        group_perf={"1W": 2.0, "1M": 4.0, "3M": 6.0},
        member_perf={
            "A": {"1W": 5.0, "1M": 8.0, "3M": 7.0},
            "B": {"1W": 4.0, "1M": 6.0, "3M": 9.0},
            "C": {"1W": 1.0, "1M": 3.0, "3M": 5.0},
        },
    )
    assert row["leadership"]["state"] == "stable_recent_leader"
    assert row["leadership"]["recent_leader"] == "A"
    assert row["leadership"]["medium_horizon_leader"] == "A"
    assert row["leadership"]["long_horizon_leader"] == "B"
    assert row["exit_watch"]["leader_handoff_candidate"] is False


def test_three_different_horizon_leaders_surface_fragmentation_without_flow_claim():
    row = rc.analyze_subtheme(
        key="x",
        theme="Theme X",
        name="Subtheme X",
        members=["A", "B", "C", "D"],
        group_perf={"1W": 2.0, "1M": 4.0, "3M": 6.0},
        member_perf={
            "A": {"1W": 5.0, "1M": 5.0, "3M": 6.0},
            "B": {"1W": 3.0, "1M": 9.0, "3M": 7.0},
            "C": {"1W": 2.5, "1M": 7.0, "3M": 12.0},
            "D": {"1W": 1.0, "1M": 2.0, "3M": 3.0},
        },
    )
    assert row["leadership"]["state"] == "fragmented"
    assert row["leadership"]["n_unique_leaders"] == 3
    assert row["exit_watch"]["leadership_fragmented"] is True


def test_theme_summary_counts_handoffs_and_fragmented_leadership():
    tree = [{"theme": "Theme X", "subsectors": [
        {"key": "handoff", "name": "Handoff", "members": ["A", "B", "C", "D"]},
        {"key": "stable", "name": "Stable", "members": ["E", "F", "G", "H"]},
    ]}]
    group = {
        "handoff": {"1W": 4.0, "1M": 8.0, "3M": 10.0},
        "stable": {"1W": 3.0, "1M": 5.0, "3M": 7.0},
    }
    member = {
        "A": {"1W": 3.0, "1M": 12.0, "3M": 15.0},
        "B": {"1W": 8.0, "1M": 10.0, "3M": 12.0},
        "C": {"1W": 2.0, "1M": 6.0, "3M": 8.0},
        "D": {"1W": 1.0, "1M": 5.0, "3M": 7.0},
        "E": {"1W": 6.0, "1M": 9.0, "3M": 11.0},
        "F": {"1W": 4.0, "1M": 7.0, "3M": 9.0},
        "G": {"1W": 3.0, "1M": 5.0, "3M": 7.0},
        "H": {"1W": 2.0, "1M": 4.0, "3M": 6.0},
    }
    out = rc.build_context(tree, group, member)
    theme = out["themes"][0]
    assert theme["leader_handoff_candidate_subthemes"] == 1
    assert theme["fragmented_leadership_subthemes"] == 0
