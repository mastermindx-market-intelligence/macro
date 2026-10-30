"""Synthetic stage identity contracts; no portfolios, artifacts or delivery I/O."""
import sys
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
