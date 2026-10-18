"""E3 — regime outlook subset in the rates block and the OUTLOOK digest line."""
import copy as _copy
import json
import re

from engine.neuralweb._law import assert_no_authority
from engine.neuralweb.market_packet import (
    OUTLOOK_LINE_BUDGET,
    _rates_block,
    _render_rates,
    _render_regime_outlook,
)


def _fixtures():
    raw_without = {
        "asof": "2026-09-30",
        "board": {
            "rate_path_row": {
                "asof": "2026-09-30",
                "policy_rate": 3.88,
                "implied_path": {"m3": 4.17},
            },
            "inflation_row": {"breakeven_10y": 2.36},
            "risk_row": {
                "curve_regime_key": "bear_flattener",
                "curve_regime_label_zh": "熊市变平",
                "term_premium_dir": "rising",
            },
        },
    }
    projection = {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
        "built_at": "2026-10-01T02:00:00+00:00",
        "mapping_version": "VERDICT_MAPPING_V2",
        "evidence_clock_range": {
            "oldest": "2026-09-25",
            "newest": "2026-09-30",
            "by_clock_semantics": {"owner_snapshot_date": 2},
        },
        "conditional_paths": [
            {
                "path_id": "orderly_disinflation",
                "family": "rates",
                "conditions": [],
                "watch": [],
                "family_readings": [
                    {"evidence_family_id": "core_pce", "reading": "fits"},
                    {"evidence_family_id": "treasury_curve", "reading": "does_not_fit"},
                    {"evidence_family_id": "labour", "reading": "fits"},
                    {"evidence_family_id": "credit_and_funding", "reading": "mixed"},
                    {"evidence_family_id": "policy_pricing", "reading": "unknown"},
                ],
            },
            {
                "path_id": "growth_deterioration",
                "family": "rates",
                "conditions": [],
                "watch": [],
                "family_readings": [
                    {"evidence_family_id": "treasury_curve", "reading": "does_not_fit"},
                    {"evidence_family_id": "labour", "reading": "not_discriminating"},
                ],
            },
        ],
        "authority": {
            "can_add_candidates": False,
            "can_raise_size": False,
            "can_lower_size": False,
            "can_block_entry": False,
            "can_force_exit": False,
            "scored_path_surfaces": [],
        },
        "tier": "display_research",
        "notes": [],
    }
    raw_with = {**raw_without, "regime_outlook": projection}
    return raw_without, projection, raw_with


def test_block_carries_projection_subset():
    raw_without, projection, raw_with = _fixtures()
    b = _rates_block(raw_with)
    assert set(b["regime_outlook"]) == {
        "analysis_cutoff",
        "mapping_version",
        "scope",
        "evidence_clock_range",
        "paths",
        "source",
    }
    assert b["regime_outlook"]["analysis_cutoff"] == projection["analysis_cutoff"]
    assert [p["path_id"] for p in b["regime_outlook"]["paths"]] == [
        "orderly_disinflation",
        "growth_deterioration",
    ]
    for path in b["regime_outlook"]["paths"]:
        assert set(path) == {"path_id", "family", "family_readings"}
    assert (
        b["regime_outlook"]["paths"][0]["family_readings"]
        == projection["conditional_paths"][0]["family_readings"]
    )
    assert (
        b["regime_outlook"]["source"]
        == "data/rates_command/latest.json#regime_outlook"
    )
    assert "built_at" not in b["regime_outlook"]


def test_block_existing_keys_unchanged():
    raw_without, _, raw_with = _fixtures()
    a = _rates_block(raw_without)
    b = _rates_block(raw_with)
    assert {k: b[k] for k in a} == a
    assert set(b) - set(a) == {"regime_outlook"}
    assert a == {
        "asof": "2026-09-30",
        "policy_rate": 3.88,
        "implied_m3": 4.17,
        "curve_regime": "bear flattener",
        "curve_regime_zh": "熊市变平",
        "breakeven_10y": 2.36,
        "term_premium_dir": "rising",
    }


def test_none_guard_precedes_projection():
    _, projection, _ = _fixtures()
    assert _rates_block({"asof": "2026-09-30", "regime_outlook": projection}) is None
    assert _rates_block(None) is None
    assert _rates_block([]) is None


def test_malformed_projection_ignored():
    raw_without, projection, _ = _fixtures()
    a = _rates_block(raw_without)
    for ro in (
        None,
        [],
        "x",
        {},
        {"schema_version": "regime_outlook.v0"},
        {"scope": "US"},
    ):
        assert _rates_block({**raw_without, "regime_outlook": ro}) == a


def test_deep_copy_independence():
    _, projection, raw_with = _fixtures()
    b = _rates_block(raw_with)
    b["regime_outlook"]["paths"][0]["family_readings"][0]["reading"] = "mixed"
    assert (
        projection["conditional_paths"][0]["family_readings"][0]["reading"] == "fits"
    )


def test_render_appends_outlook_after_rates_line():
    raw_without, _, raw_with = _fixtures()
    a = _rates_block(raw_without)
    b = _rates_block(raw_with)
    base = _render_rates({"rates": a})
    assert "\n" not in base
    assert "OUTLOOK" not in base
    assert base.startswith("RATES DESK (2026-09-30): ")
    out = _render_rates({"rates": b})
    assert out.split("\n")[0] == base
    assert len(out.split("\n")) == 2
    assert out.split("\n")[1] == _render_regime_outlook(b["regime_outlook"])


def test_outlook_line_exact_grammar():
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    assert _render_regime_outlook(b["regime_outlook"]) == (
        "OUTLOOK (read prepared 09-30 09:43Z; overlapping paths, unordered; "
        "+fits -does-not-fit ~mixed): orderly_disinflation +core_pce +labour "
        "-treasury_curve ~credit_and_funding | growth_deterioration "
        "-treasury_curve; full readings: world_state.rates_command.regime_outlook"
    )


def test_zh_renders_the_same_outlook_line():
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    en_out = _render_rates({"rates": b}).split("\n")[1]
    zh_out = _render_rates({"rates": b, "_render_lang": "zh"}).split("\n")[1]
    assert zh_out == en_out
    zh_first = _render_rates({"rates": b, "_render_lang": "zh"}).split("\n")[0]
    assert "熊市变平" in zh_first


def test_gate3_analysis_cutoff_not_built_at():
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    line = _render_regime_outlook(b["regime_outlook"])
    assert "09-30 09:43Z" in line
    assert "10-01" not in line
    assert "built_at" not in b["regime_outlook"]


def test_gate4_no_numbers_after_header():
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    line = _render_regime_outlook(b["regime_outlook"])
    body = line.split("): ", 1)[1]
    assert re.search(r"\d", body) is None
    assert "%" not in body


def test_budget_tiers():
    # 9 paths with fits + does_not_fit + mixed readings — tier 2 fits-only line still over budget.
    big_proj = {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
        "mapping_version": "VERDICT_MAPPING_V2",
        "evidence_clock_range": {
            "oldest": "2026-09-25",
            "newest": "2026-09-30",
            "by_clock_semantics": {"owner_snapshot_date": 2},
        },
        "conditional_paths": [
            {
                "path_id": f"path_{c}",
                "family": "rates",
                "conditions": [],
                "watch": [],
                "family_readings": [
                    {"evidence_family_id": "fam_alpha_one", "reading": "fits"},
                    {"evidence_family_id": "fam_beta_two", "reading": "does_not_fit"},
                    {"evidence_family_id": "fam_gamma_three", "reading": "mixed"},
                    {"evidence_family_id": "fam_delta_four", "reading": "fits"},
                    {"evidence_family_id": "fam_epsilon_five", "reading": "mixed"},
                ],
            }
            for c in "abcdefghi"
        ],
    }
    result = _render_regime_outlook({"paths": big_proj["conditional_paths"], "analysis_cutoff": big_proj["analysis_cutoff"]})
    # 9 paths * (full 5-reading) > 380 AND 9 paths * (fits only) > 380 (both overflow),
    # so tier 3 partial kicks in. The head fits 5 entries plus "; partial; ...".
    assert result.endswith(
        "; partial; full readings: world_state.rates_command.regime_outlook"
    )
    assert len(result) <= OUTLOOK_LINE_BUDGET
    # Confirm tier-1 with a much larger budget overflows the default.
    huge = _render_regime_outlook(
        {
            "paths": big_proj["conditional_paths"],
            "analysis_cutoff": big_proj["analysis_cutoff"],
        },
        budget=10_000,
    )
    assert len(huge) > OUTLOOK_LINE_BUDGET
    # Five fits-only entries fit before partial kicks in (96 + 5*37 + 4*3 + 66 = 359).
    assert result.count("path_") == 5

    # 30 paths with long fits-only family ids — even tier-2 overflows, tier-3 partial kicks in.
    big2_proj = {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
        "mapping_version": "VERDICT_MAPPING_V2",
        "evidence_clock_range": {
            "oldest": "2026-09-25",
            "newest": "2026-09-30",
            "by_clock_semantics": {"owner_snapshot_date": 2},
        },
        "conditional_paths": [
            {
                "path_id": f"path_{i:02d}",
                "family": "rates",
                "conditions": [],
                "watch": [],
                "family_readings": [
                    {"evidence_family_id": "fam_long_aaaaaaaaaaaaaaaaaaaaaaaaa", "reading": "fits"},
                    {"evidence_family_id": "fam_long_bbbbbbbbbbbbbbbbbbbbbbbbb", "reading": "fits"},
                    {"evidence_family_id": "fam_long_ccccccccccccccccccccccccc", "reading": "fits"},
                    {"evidence_family_id": "fam_long_ddddddddddddddddddddddddd", "reading": "fits"},
                ],
            }
            for i in range(30)
        ],
    }
    res2 = _render_regime_outlook(
        {
            "paths": big2_proj["conditional_paths"],
            "analysis_cutoff": big2_proj["analysis_cutoff"],
        }
    )
    assert res2.endswith(
        "; partial; full readings: world_state.rates_command.regime_outlook"
    )
    assert len(res2) <= OUTLOOK_LINE_BUDGET
    assert res2.startswith(
        "OUTLOOK (read prepared 09-30 09:43Z; overlapping paths, unordered; "
        "+fits -does-not-fit ~mixed): "
    )

    # budget=60 with the small fixture — even the header exceeds it; result is empty.
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    assert _render_regime_outlook(b["regime_outlook"], budget=60) == ""
    rates_out = _render_rates({"rates": b})
    # When the outlook renders "", _render_rates must not introduce a "\n".
    # Force that condition directly with a budget that yields "":
    b_for_render = _copy.deepcopy(b)
    b_for_render["regime_outlook"] = _copy.deepcopy(b["regime_outlook"])
    # Patch: monkey-patch the render to use a tiny budget via wrapping is too clever;
    # instead build a block whose outlook renders "" by passing the budget below.
    # We assert by direct call:
    assert "\n" not in _render_rates({"rates": _rates_block({
        **_copy.deepcopy({k: v for k, v in _fixtures()[0].items()}),
        # No projection here at all — the existing keys alone render normally without "\n".
    })})
    # A projection whose readings are all 'unknown' yields "" from _render_regime_outlook
    # and a single-line _render_rates.
    all_unknown = {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
        "mapping_version": "VERDICT_MAPPING_V2",
        "evidence_clock_range": {"oldest": "2026-09-25", "newest": "2026-09-30", "by_clock_semantics": {"owner_snapshot_date": 2}},
        "conditional_paths": [
            {
                "path_id": "orderly_disinflation",
                "family": "rates",
                "conditions": [],
                "watch": [],
                "family_readings": [
                    {"evidence_family_id": "core_pce", "reading": "unknown"},
                    {"evidence_family_id": "treasury_curve", "reading": "unknown"},
                ],
            }
        ],
    }
    raw_unknown = {**_copy.deepcopy(_fixtures()[0]), "regime_outlook": all_unknown}
    b_unknown = _rates_block(raw_unknown)
    assert _render_regime_outlook(b_unknown["regime_outlook"]) == ""
    out_unknown = _render_rates({"rates": b_unknown})
    assert "\n" not in out_unknown


def test_authority_law_holds():
    _, _, raw_with = _fixtures()
    b = _rates_block(raw_with)
    assert assert_no_authority(b) == []
    assert assert_no_authority({"rates": b}) == []


def test_paths_keep_projection_order_and_are_not_ranked():
    _, _, raw_with = _fixtures()
    # Flip the per-path fits counts so growth_deterioration outranks orderly_disinflation.
    raw = _copy.deepcopy(raw_with)
    raw["regime_outlook"]["conditional_paths"][1]["family_readings"] = [
        {"evidence_family_id": "treasury_curve", "reading": "fits"},
        {"evidence_family_id": "credit_spreads", "reading": "fits"},
        {"evidence_family_id": "labour", "reading": "fits"},
    ]
    raw["regime_outlook"]["conditional_paths"][0]["family_readings"] = [
        {"evidence_family_id": "core_pce", "reading": "fits"},
    ]
    b = _rates_block(raw)
    assert [p["path_id"] for p in b["regime_outlook"]["paths"]] == [
        "orderly_disinflation",
        "growth_deterioration",
    ]
    line = _render_regime_outlook(b["regime_outlook"])
    # Same order in the rendered line: orderly_disinflation comes first.
    assert line.index("orderly_disinflation") < line.index("growth_deterioration")