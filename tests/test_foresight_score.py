"""engine.foresight_score — the 7-axis investability rubric. Verifies a confirmed early
theme scores high, the three honesty rules bind (text-only cap, stage/timing cap,
underpricing inverse to breadth), and annotate() re-ranks by score.
"""
from __future__ import annotations

import math

from engine import foresight_score as fs


def _early_confirmed():
    """Tight physical bottleneck, revisions not yet firing, demand accelerating — the
    PRECIPICE state the desk is built to catch."""
    return {"stage": "PRECIPICE", "bottleneck_band": "SOLD_OUT", "tightness": 1.6,
            "bottleneck_regime": True, "demand_band": "ACCELERATING", "capex_yoy": 69,
            "demand_strength": "direct", "revision_breadth": 0.05, "revision_level": "FLAT_LOW",
            "broadening_state": "FLAT_LOW", "est_drift_90d": 5, "glut_band": "STABLE",
            "entry_ready": False}


def test_confirmed_early_scores_high_uncapped():
    s = fs.score_row(_early_confirmed())
    assert s["physical_confirmed"] is True
    assert s["caps"] == []            # physical confirmed + early stage -> nothing caps it
    assert s["score"] >= 70 and s["verdict"] == "high-conviction"


def test_text_only_caps_at_50():
    r = _early_confirmed()
    r["bottleneck_band"] = "AWAITING_DATA"      # no physical read
    s = fs.score_row(r)
    assert s["physical_confirmed"] is False
    assert s["score"] <= 50.0
    assert any("text-only" in c for c in s["caps"])


def test_late_stage_caps_score():
    r = _early_confirmed()
    r["stage"] = "RE-RATING"                     # late: revisions already broad
    r["revision_breadth"] = 0.9
    r["revision_level"] = "POSITIVE"
    s = fs.score_row(r)
    assert s["score"] <= 60.0
    assert any("RE-RATING" in c for c in s["caps"])


def test_underpricing_inverse_to_breadth():
    crowded = dict(_early_confirmed(), revision_breadth=0.95, revision_level="POSITIVE")
    early = _early_confirmed()
    assert fs.score_row(crowded)["axes"]["underpricing"] < fs.score_row(early)["axes"]["underpricing"]


def test_annotate_reranks_by_score():
    cascade = {"themes": [
        {"theme": "late", "stage": "RE-RATING", "bottleneck_band": "AWAITING_DATA",
         "revision_breadth": 0.9, "revision_level": "POSITIVE", "demand_band": None},
        {"theme": "early", "stage": "PRECIPICE", "bottleneck_band": "SOLD_OUT", "tightness": 1.5,
         "bottleneck_regime": True, "demand_band": "ACCELERATING", "capex_yoy": 60,
         "demand_strength": "direct", "revision_breadth": 0.04, "revision_level": "FLAT_LOW"},
    ]}
    out = fs.annotate(cascade)
    assert out["scored"] is True
    assert out["themes"][0]["theme"] == "early"          # higher score sorts first
    assert out["themes"][0]["score"] > out["themes"][1]["score"]


def test_magnitude_none_on_nan_capex():
    """A NaN capex_yoy is a broken feed, not a demand signal — the axis must refuse."""
    assert fs._magnitude({"capex_yoy": float("nan")}) is None


def test_magnitude_none_on_inf_capex():
    assert fs._magnitude({"capex_yoy": float("inf")}) is None


def test_score_row_nan_capex_does_not_max_magnitude():
    """score_row must not publish magnitude=1.0 (or a high-conviction score) off NaN capex;
    a finite capex=69 row still scores exactly as today."""
    nan_s = fs.score_row(dict(_early_confirmed(), capex_yoy=float("nan")))
    ok_s = fs.score_row(_early_confirmed())
    assert nan_s["axes"]["magnitude"] is None          # today 1.0
    assert math.isfinite(nan_s["score"])
    assert nan_s["score"] < ok_s["score"]              # no tie with the real-capex row
    assert ok_s["axes"]["magnitude"] == 1.0            # finite path unchanged


def test_nan_axis_is_dropped_not_propagated_into_the_score():
    """A NaN divergence_share leaks through _magnitude as NaN; the live-axes
    filter must drop that axis so the published score stays finite."""
    s = fs.score_row(dict(_early_confirmed(), divergence_share=float("nan")))
    assert math.isfinite(s["score"])
    assert s["score"] > 0
