"""Evidence shown by the US macro dialog comes from one dated market-state snapshot."""
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)


def render(**snapshot):
    html = ENV.get_template("_macro_evidence_dialog.html.j2").render(MS2=snapshot)
    return BeautifulSoup(html, "html.parser")


def factor(score, weight, **updates):
    return {"label_en": "Risk appetite", "key": "risk", "score": score, "weight": weight, **updates}


def test_points_use_only_resolved_weight_and_preserve_zero():
    page = render(score=16, components=[factor(0, 0.24), factor(40, 0.16), factor(None, 0.6)])
    assert [row.get_text(strip=True) for row in page.select(".ev-impact b")] == ["-30.00", "-4.00"]
    assert "2 / 6" in page.select_one(".ev-meta").get_text()
    assert page.select_one(".ev-score").string == "16"
    assert "Partial coverage" in page.get_text()


def test_unknown_weight_withholds_attribution_for_every_row():
    page = render(components=[factor(0, None), factor(99, 0.5)])
    assert [v.string for v in page.select(".ev-impact b")] == ["—", "—"]
    assert page.select_one(".ev-score").string == "—"


def test_caps_require_a_binding_adjustment_and_flip_comes_from_producer():
    cap = {"kind": "verdict_cap", "limit": 59, "note_en": "cap from source", "note_zh": "来自源数据的上限"}
    args = dict(score=59, raw_score=73, score_ceiling=59, score_caps=[cap], flip_en="Wait for the cap to clear.")
    page = render(**args, capped=True)
    assert "73 → 59" in page.select_one(".ev-cap").get_text()
    assert "cap from source" in page.select_one(".ev-cap").get_text()
    assert "Wait for the cap to clear." in page.select_one(".ev-condition").get_text()
    assert render(**args, capped=False).select_one(".ev-cap") is None


def test_stale_and_missing_inputs_are_visible_and_escaped():
    page = render(asof="2026-10-30", components=[factor(0, 1, degraded=True,
                  degraded_note_en="Credit print missing", read_en="<script>bad()</script>")],
                  freshness={"stale": True, "expected_asof": "2026-11-02"},
                  input_vintages={"credit": {"asof": "2026-10-15", "stale": True}})
    assert not page.select("script")
    assert "<script>bad()</script>" in page.select_one(".ev-read").get_text()
    assert "Credit print missing" in page.select_one(".ev-detail").get_text()
    assert "2026-10-30" in page.select_one(".ev-meta").get_text()
    assert "2026-11-02" in page.select_one(".ev-meta").get_text()
    assert "credit" in page.select_one(".ev-meta").get_text()
    assert "2026-10-15" in page.select_one(".ev-sources").get_text()


def test_tape_and_snapshot_can_survive_missing_factors():
    page = render(components=[], mtf={"indices": [{"label_en": "S&P", "cells": {
        "D": {"rsi": 0, "arrow": "▼"}, "3D": {"rsi": "missing"}, "W": None, "M": {"rsi": 101}}}]})
    assert [c["data-sort"] for c in page.select("td[data-sort]")] == ["0", "", "", ""]
    assert not page.select(".ev-factor")
    assert "Factor readings are unavailable" in page.get_text()
    assert "Individual input dates were not supplied" in page.get_text()

def test_largest_drag_uses_weight_and_preserves_ties():
    page = render(components=[
        factor(0, 0.05, label_en="Lowest reading"),
        factor(30, 0.30, label_en="First drag"),
        factor(20, 0.20, label_en="Second drag"),
        factor(70, 0.45, label_en="Offset"),
    ])
    drag = page.select_one(".ev-drivers .ev-neg").get_text(" ", strip=True)
    assert "First drag" in drag and "Second drag" in drag and "-6.00" in drag
    assert "Lowest reading" not in drag
    assert "+9.00" in page.select_one(".ev-drivers .ev-pos").get_text()


def test_malformed_leg_does_not_break_the_normal_dashboard_entry():
    from tests.test_macro_risk_dialog import _render, _vm

    vm = _vm()
    vm["market_state"]["components"] = [factor(0, 0.4), None, {}, factor("missing", 0.3)]
    page = BeautifulSoup(_render(vm), "html.parser")
    assert page.select_one("#sx-evidence [aria-haspopup=dialog]")
    assert len(page.select("#dlg-evidence .ev-factor")) == 1
    assert page.select_one("#dlg-evidence .ev-factor-value b").string == "0"

def test_score_trace_reconciles_the_october_30_example():
    observations = [(39, 0.24), (14, 0.18), (48, 0.16), (68, 0.16), (48, 0.14), (80, 0.12)]
    page = render(score=47, raw_score=47, capped=False, components=[factor(s, w) for s, w in observations])
    assert [node.string for node in page.select(".ev-equation b")] == ["50", "−9.72", "+6.48", "= 46.76"]
    assert [node.string for node in page.select(".ev-factor .ev-impact b")] == [
        "-6.48", "-2.64", "-0.32", "-0.28", "+2.88", "+3.60",
    ]
    assert page.select_one('input[value="impact"][checked]') is not None
    assert "Rounded blend" in page.select_one(".ev-trace").get_text()
    assert not page.select_one(".ev-trace").has_attr("open")


def test_missing_weights_leave_raw_scores_available_but_no_trace():
    page = render(score=51, components=[factor(50, None), factor(90, 0.3)])
    assert page.select_one('input[value="impact"][disabled]') is not None
    assert page.select_one('input[value="score"][checked]') is not None
    assert page.select_one(".ev-equation") is None
    assert "Weights unavailable" in page.get_text()


def test_published_blend_disagreement_is_explicit():
    page = render(score=47, raw_score=75, capped=True, components=[factor(40, 1)])
    assert "75 → 47" in page.select_one(".ev-cap").get_text()
    assert "do not reconcile" in page.select_one(".ev-trace .ev-flag").get_text()
    assert page.select_one(".ev-drivers") is None


def test_neutral_blend_keeps_zero_distinct_from_unavailable():
    page = render(score=50, raw_score=50, components=[factor(50, 1)])
    assert page.select_one(".ev-impact b").string == "+0.00"
    assert page.select_one(".ev-equation b:last-of-type") is not None
    assert "= 50.00" in page.select_one(".ev-equation").get_text()
    assert "balanced at neutral" in page.select_one(".ev-drivers").get_text()
    assert all("nan" not in el.get("style", "").lower() for el in page.select("[style]"))
