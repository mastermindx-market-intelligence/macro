"""Synthetic stage identity contracts; no portfolios, artifacts or delivery I/O."""
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.portfolio_changes import diff_snapshots, snapshot_state


def snap(stage):
    return {"names": {"SYNTH": {"stage": stage}}}


INVALID = [True, False, 1.9, 2.9, float("inf"), -float("inf"), float("nan"),
           None, "", "2.5", "bad", [], {}, 0, 5, 999]


@pytest.mark.parametrize("stage", INVALID)
def test_invalid_producer_stage_is_omitted(stage):
    ctx = {"tickers": {"SYNTH": {"stage": {"n": stage}}}}
    result = snapshot_state(ctx, ["SYNTH"])
    assert "stage" not in result["names"]["SYNTH"]


@pytest.mark.parametrize("stage", INVALID)
@pytest.mark.parametrize("invalid_side", ["previous", "current"])
def test_invalid_stage_cannot_generate_a_transition(stage, invalid_side):
    previous, current = (snap(stage), snap(3)) if invalid_side == "previous" else (snap(1), snap(stage))
    assert diff_snapshots(previous, current) == []


@pytest.mark.parametrize("stage", [2, 2.0, "2", "02", "+2", " 2 "])
def test_equivalent_stage_representations_do_not_claim_change(stage):
    assert diff_snapshots(snap(stage), snap(2)) == []
    assert diff_snapshots(snap(2), snap(stage)) == []
    result = snapshot_state({"tickers": {"SYNTH": {"stage": {"n": stage}}}}, ["SYNTH"])
    assert result["names"]["SYNTH"]["stage"] == 2
    assert type(result["names"]["SYNTH"]["stage"]) is int


def test_valid_transition_keeps_bilingual_desk_vocabulary():
    assert diff_snapshots(snap("2"), snap(3.0)) == [{
        "kind": "stage", "ticker": "SYNTH",
        "en": "SYNTH moved from Stage 2 uptrend to Stage 3 topping.",
        "zh": "SYNTH 从第 2 阶段上升转为第 3 阶段见顶。",
    }]


@pytest.mark.parametrize("stage", [True, 1.9, float("inf"), float("nan"), "bad", 999])
def test_brief_keeps_stage_earnings_and_weight_truth_together(stage):
    from engine.portfolio_brief import compose_brief

    ctx = {"asof": "2026-10-30", "sectors": {}, "tickers": {
        "AAA": {"sector": "Technology", "stage": {"n": stage, "fresh": True},
                "earnings": {"next": "2026-11-01", "days_to": 10.9}},
        "BBB": {"sector": "Energy", "stage": {"n": 2, "fresh": False},
                "earnings": {"next": "2026-11-01", "days_to": 2}},
    }}
    previous = snapshot_state({"tickers": {
        "AAA": {"stage": {"n": 2}, "earnings": {"next": "2026-11-01", "days_to": 5}},
        "BBB": ctx["tickers"]["BBB"],
    }}, ["AAA", "BBB"])
    result = compose_brief(ctx, [
        {"ticker": "AAA", "shares": float("inf"), "entry_price": 1},
        {"ticker": "BBB", "shares": 1, "entry_price": 1},
    ], "2026-10-30", "2026-10-30T00:00:00Z", population="positions", previous=previous)
    json.dumps(result, allow_nan=False)
    assert result["book"]["n"] == 2
    assert result["data"]["concentration"]["top_name_pct"] == 100
    assert "Energy 100%" in result["headline"]["en"]
    assert "stage" not in result["data"]["state_digest"]["names"]["AAA"]
    assert "earnings_soon" not in result["data"]["state_digest"]["names"]["AAA"]
    assert result["data"]["events"]["earnings_10d"] == [
        {"ticker": "BBB", "date": "2026-11-01", "days_to": 2}]
    assert all(section["key"] != "since" for section in result["sections"])
    signals = next(section for section in result["sections"] if section["key"] == "signals")
    assert signals["lines"][0] == {
        "en": "1 of your 1 covered names are in Stage 2 uptrends.",
        "zh": "你 1 只有覆盖的个股中，有 1 只处于第 2 阶段上升趋势。",
    }
