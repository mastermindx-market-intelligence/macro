"""Tests for the zero-authority Prophet subtheme leadership funnel."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import prophet_subtheme_funnel as STF  # noqa: E402


def _write_tree(root: Path, specs: dict[str, list[str]]) -> None:
    path = root / STF.TREE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([
        {
            "key": "Semiconductors",
            "subsectors": [
                {"key": key, "name": key.title(), "members": members}
                for key, members in specs.items()
            ],
        }
    ]), encoding="utf-8")


def _rotation(keys: list[str], asof: str = "2026-09-18") -> dict:
    return {
        "asof": asof,
        "highlights": {"emerging": keys},
        "subsectors": [
            {
                "key": key,
                "name": key.title(),
                "theme": "Semiconductors",
                "rank": i,
                "emerging_score": 10.0 - i,
                "rs_mom": 0.5,
                "accel": 0.2,
                "quadrant": "leading",
                "turn_state": "range",
            }
            for i, key in enumerate(keys, start=1)
        ],
    }


def _standouts(pool_rows: list[dict], asof: str = "2026-09-18") -> dict:
    return {
        "as_of": asof,
        "candidate_pool": {"rows": pool_rows},
        "buy": [],
        "watch": [],
        "leaders": [],
        "ran": [],
    }


def test_emerging_subtheme_funnel_names_each_loss_stage(tmp_path):
    keys = ["admission", "scoring", "featured", "covered"]
    _write_tree(tmp_path, {
        "admission": ["A1"],
        "scoring": ["S1", "S2"],
        "featured": ["F1"],
        "covered": ["C1"],
    })
    standouts = _standouts([
        {
            "ticker": "S1",
            "lane": "more_actionable",
            "lane_reasons": ["sector_cap_overflow"],
            "pool_rank": 26,
            "prophet": None,
        },
        {
            "ticker": "S2",
            "lane": "forming",
            "lane_reasons": ["await_confluence"],
            "pool_rank": 41,
            "prophet": None,
        },
        {
            "ticker": "F1",
            "lane": "more_actionable",
            "lane_reasons": ["featured_cap"],
            "pool_rank": 8,
            "prophet": {"score": 71.2},
        },
        {
            "ticker": "C1",
            "lane": "featured",
            "lane_reasons": ["cleared_admission"],
            "pool_rank": 2,
            "prophet": {"score": 88.4},
        },
    ])
    degraded = []
    out = STF.build(tmp_path, standouts, _rotation(keys), degraded)

    assert out["available"] is True
    assert [row["key"] for row in out["emerging"]] == keys
    rows = {row["key"]: row for row in out["emerging"]}
    assert rows["admission"]["gap_class"] == "ADMISSION_GAP"
    assert rows["scoring"]["gap_class"] == "SCORING_GAP"
    assert rows["featured"]["gap_class"] == "FEATURED_GAP"
    assert rows["covered"]["gap_class"] == "COVERED_FEATURED"

    assert rows["scoring"]["eligible_n"] == 2
    assert rows["scoring"]["scored_n"] == 0
    assert rows["scoring"]["best_pool_rank"] == 26
    assert rows["scoring"]["blocker_hist"] == {
        "await_confluence": 1,
        "sector_cap_overflow": 1,
    }
    assert rows["featured"]["scored_n"] == 1
    assert rows["featured"]["featured_n"] == 0
    assert rows["covered"]["featured_n"] == 1
    assert out["gap_class_hist"] == {
        "ADMISSION_GAP": 1,
        "COVERED_FEATURED": 1,
        "FEATURED_GAP": 1,
        "SCORING_GAP": 1,
    }
    assert out["n_gaps"] == 3
    assert out["featured_coverage_pct"] == 25.0
    assert degraded == []


def test_visible_watch_member_does_not_masquerade_as_featured_coverage(tmp_path):
    _write_tree(tmp_path, {"compute": ["NVDA", "AMD"]})
    standouts = _standouts([
        {
            "ticker": "AMD",
            "lane": "more_actionable",
            "lane_reasons": ["sector_cap_overflow"],
            "pool_rank": 26,
            "prophet": None,
        }
    ])
    standouts["watch"] = [{"ticker": "NVDA"}]

    out = STF.build(tmp_path, standouts, _rotation(["compute"]), [])
    row = out["emerging"][0]

    assert row["visible_n"] == 1
    assert row["members_visible"] == ["NVDA"]
    assert row["eligible_n"] == 1
    assert row["members_eligible"] == ["AMD"]
    assert row["gap_class"] == "SCORING_GAP"
    assert row["gap"] is True
    assert row["blocker_hist"] == {"sector_cap_overflow": 1}


def test_clock_mismatch_fails_closed_before_membership_join(tmp_path):
    degraded = []
    out = STF.build(
        tmp_path,
        _standouts([], asof="2026-09-18"),
        _rotation(["compute"], asof="2026-09-17"),
        degraded,
    )
    assert out["available"] is False
    assert out["emerging"] == []
    assert "same completed session" in out["null_reason"]
    assert any("clock mismatch" in row["reason"] for row in degraded)


def test_missing_candidate_pool_is_unknown_not_zero_eligibility(tmp_path):
    _write_tree(tmp_path, {"compute": ["NVDA", "AMD"]})
    degraded = []
    out = STF.build(
        tmp_path,
        {"as_of": "2026-09-18"},
        _rotation(["compute"]),
        degraded,
    )
    assert out["available"] is False
    assert out["gaps"] == []
    assert "candidate_pool.rows" in out["null_reason"]
    assert any(row["input"] == "site/factordata/us_standouts.json" for row in degraded)


def test_highlight_without_current_membership_is_disclosed_not_classified(tmp_path):
    _write_tree(tmp_path, {"memory": ["MU", "WDC"]})
    degraded = []
    out = STF.build(
        tmp_path,
        _standouts([]),
        _rotation(["compute"]),
        degraded,
    )
    assert out["available"] is True
    assert out["n_measured"] == 0
    assert out["n_gaps"] == 0
    assert out["emerging"][0]["gap_class"] == "UNKNOWN_MEMBERSHIP"
    assert out["emerging"][0]["gap"] is None
    assert any(row["input"] == STF.TREE_REL for row in degraded)


def test_membership_is_explicitly_current_only_and_authority_is_none(tmp_path):
    _write_tree(tmp_path, {"compute": ["AMD", "NVDA"]})
    out = STF.build(tmp_path, _standouts([]), _rotation(["compute"]), [])
    assert out["membership_temporality"] == "current_only — never backdated"
    assert out["rotation_basis"].startswith("subsector_rotation.highlights.emerging")
    assert out["authority"].startswith("none")
