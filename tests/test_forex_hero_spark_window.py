"""Hero sparkline common-window contract (R26, #8315 comment 6198660401).

dollar_vm cuts the COMMON 126-row window FIRST and reads both series at exactly
those row slots.  Previously each series was dropna().tail(126) independently,
so the sparser risk-off series pulled observations from OUTSIDE the dollar
window, and _spark_pts re-spread the survivors so distinct dates landed on the
same x (apparent synchrony).

Display-only (no signal/risk semantics): out-of-window risk renders NO trace;
missing/non-finite slots keep x and split the polyline (no bridging, forward
fill or fabrication; measured zeros stay); singletons render as dots; broad is
rebased to the first finite positive value IN the window; last_rebased is
unavailable when the last slot is missing; hero_spark carries window metadata;
the real template renders the segments via Jinja and stays legacy-fixture safe.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_forex as BF  # noqa: E402

_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "forex.html.j2"


def dollar_vm(dol):
    return BF.dollar_vm(dol)


@pytest.fixture(autouse=True)
def _stub_chart(monkeypatch):
    """Keep the heavy plotly chart out of the unit under test."""
    monkeypatch.setattr(BF, "chart_dollar", lambda dol, years=8: "")


def _dol(n: int = 300, broad=None, risk=None) -> pd.DataFrame:
    """Synthetic frame; broad/risk callables map row position -> value."""
    idx = pd.bdate_range("2025-04-01", periods=n)
    b = [broad(i) for i in range(n)] if broad else np.linspace(90.0, 130.0, n)
    r = [risk(i) for i in range(n)] if risk else np.full(n, np.nan)
    return pd.DataFrame({"broad": b, "risk_off": r}, index=idx)


def _pts(seg: str) -> list[tuple[float, float]]:
    return [tuple(float(c) for c in p.split(",")) for p in seg.split()]


_DOLLAR_STUB = {
    "hero_spark": None, "dollar_day": False, "zone_en": "x", "zone_zh": "x",
    "regime": "Neutral", "regime_zh": "x", "dollar_dir": "flat",
    "dollar_dir_zh": "x", "roc": 0.0, "risk_off": 0.0, "risk_word": "risk-on",
    "risk_word_zh": "x", "broad": 100.0, "dxy": 100.0, "afe": 1.0, "eme": 1.0,
    "dollar_day_z": 0.0, "favored": [], "favored_zh": [], "color": "#000",
    "chart": "",
}


def _render(dollar: dict) -> str:
    """Render the REAL forex template with a minimal stub context."""
    from jinja2 import Environment, FileSystemLoader
    dollar = dict(_DOLLAR_STUB, **dollar)
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE.parent)), autoescape=True)
    return env.get_template(_TEMPLATE.name).render(
        C=BF.C, as_of="2026-10-20", built="2026-10-20 00:00 UTC", cal_span="1y",
        dollar=dollar, desk={}, real_rate_chart="", transmission={}, strength={},
        scorecards=[], regime={}, kinematics={}, kinematics_view={}, pairs=[],
        sections=[], carry_table=[], cot_ok=False, timeline=[], timeline_days=20,
        n_alerts=0, hero=None, why_tiles=None, trans_rows=None, stress=None,
        scoreboard=None, recent=None, footer_en=None, footer_zh=None, stance={})


def _spark_region(html: str) -> str:
    """Just the hero spark svg — the smile arc before it also uses circles."""
    start = html.index('class="spark-wrap"')
    return html[start:html.index("</svg>", start)]


def _gapped_risk(i) -> float:
    """Slots: 0-9 filled, 10-19 gap, 20-29 filled, 30-124 gap, 125 singleton."""
    w = i - 174  # window slot for rows 174..299
    if 0 <= w <= 9:
        return 1.0 + 0.1 * w
    if 20 <= w <= 29:
        return 2.0 + 0.1 * w
    if w == 125:
        return 3.0
    return np.nan


def test_risk_only_before_window_has_no_trace_in_last_126():
    """300 rows, risk_off only in the FIRST 20 rows -> no trace in last 126
    (the old dropna-tail bug drew this outside-the-window data)."""
    hs = dollar_vm(_dol(risk=lambda i: float(i) if i < 20 else np.nan))["hero_spark"]
    assert hs["riskoff_segments"] == [] and hs["riskoff_pts"] == ""
    assert hs["count"] == 126 and hs["n"] == 126


def test_sparse_same_window_keeps_fixed_x_slots_and_splits_segments():
    hs = dollar_vm(_dol(risk=_gapped_risk))["hero_spark"]
    segs = hs["riskoff_segments"]
    assert len(segs) == 3, segs                       # gap splits, nothing bridges
    assert len(hs["dollar_segments"]) == 1
    assert hs["dollar_pts"] != ""                     # dollar window is gap-free
    s0, s1, s2 = (_pts(s) for s in segs)
    assert len(s0) == 10 and len(s1) == 10 and len(s2) == 1
    # fixed x grid over 126 slots: x_i = round(i/125*440, 1)
    assert [p[0] for p in s0] == [round(i / 125 * 440, 1) for i in range(10)]
    assert [p[0] for p in s1] == [round(i / 125 * 440, 1) for i in range(20, 30)]
    assert s2[0][0] == 440.0                          # singleton keeps its slot
    assert hs["riskoff_pts"] == ""   # legacy field unsafe when gapped


def test_singleton_run_and_gap_edge_slots_are_exact():
    segs = BF._window_segments([np.nan, 1.0, 2.0, np.nan, 3.0], 100, 20)
    assert len(segs) == 2
    a, b = _pts(segs[0]), _pts(segs[1])
    assert [p[0] for p in a] == [25.0, 50.0]          # slots 1,2 of 5
    assert [p[0] for p in b] == [100.0]               # slot 4 of 5, no line drawn


def test_measured_zero_stays_finite_and_visible():
    dol = _dol(broad=lambda i: 100.0, risk=lambda i: 0.0 if i < 6 + 174 else np.nan)
    hs = dollar_vm(dol)["hero_spark"]
    assert len(hs["riskoff_segments"]) == 1
    flat = _pts(hs["riskoff_segments"][0])
    assert len(flat) == 6 and all(p[1] == pytest.approx(30.0, abs=0.2) for p in flat)
    # a measured 0.0 in broad is a real observation: plotted, and never a base
    hs2 = dollar_vm(_dol(broad=lambda i: 0.0 if i == 5 + 174 else 100.0))["hero_spark"]
    assert hs2["last_rebased"] == pytest.approx(100.0, abs=0.1)   # base=100, not 0
    allpts = [p for s in hs2["dollar_segments"] for p in _pts(s)]
    assert len(allpts) == 126                                     # nothing dropped
    assert any(p[1] == pytest.approx(58.0, abs=0.2) for p in allpts)  # 0 at bottom


def test_malformed_and_nonfinite_slots_are_not_coerced():
    bad = {40 + 174: "oops", 41 + 174: None, 42 + 174: np.inf, 43 + 174: -np.inf}
    dol = _dol(broad=lambda i: bad.get(i, 100.0 + i))    # object dtype via string
    hs = dollar_vm(dol)["hero_spark"]
    allpts = [p for s in hs["dollar_segments"] for p in _pts(s)]
    finite_slots = 126 - 4
    assert len(allpts) == finite_slots            # no point fabricated
    assert len(hs["dollar_segments"]) >= 2        # the 4-slot hole splits the line
    assert hs["n"] == finite_slots


def test_populated_control_keeps_both_traces_and_window_dates():
    idx = pd.bdate_range("2025-04-01", periods=300)
    dol = pd.DataFrame({"broad": np.linspace(90.0, 130.0, 300),
                        "risk_off": np.sin(np.arange(300) / 7.0)}, index=idx)
    hs = dollar_vm(dol)["hero_spark"]
    assert len(hs["dollar_segments"]) == 1 and len(hs["riskoff_segments"]) == 1
    assert len(_pts(hs["dollar_segments"][0])) == 126
    assert len(_pts(hs["riskoff_segments"][0])) == 126
    # legacy fields carry the same (gap-free) polylines
    assert hs["dollar_pts"] == hs["dollar_segments"][0]
    assert hs["riskoff_pts"] == hs["riskoff_segments"][0]
    # rebased to first finite positive value IN window (row 174); display-rounded
    assert hs["last_rebased"] == pytest.approx(
        100.0 * dol["broad"].iloc[-1] / dol["broad"].iloc[174], abs=0.05)
    assert hs["n"] == 126 and hs["count"] == 126
    assert hs["window_start"] == str(idx[-126].date())
    assert hs["window_end"] == str(idx[-1].date())


def test_rebase_base_comes_from_inside_the_window_not_earlier_rows():
    # rows 0..173 huge (outside window), window values 100..225 -> base=100
    hs = dollar_vm(_dol(broad=lambda i: 1e6 if i < 174 else 100.0 + (i - 174)))["hero_spark"]
    assert hs["last_rebased"] == pytest.approx(225.0, rel=1e-6)  # 100*225/100


def test_last_slot_missing_makes_last_rebased_unavailable():
    hs = dollar_vm(_dol(broad=lambda i: np.nan if i == 299 else 100.0))["hero_spark"]
    assert hs["last_rebased"] is None
    last_seg = _pts(hs["dollar_segments"][-1])
    assert last_seg[-1][0] == 436.5              # ends at slot 124, not bridged to 125


def test_missing_columns_degrade_cleanly():
    hs = dollar_vm(pd.DataFrame({"close": [1.0, 2.0]}))["hero_spark"]
    assert hs["dollar_segments"] == [] and hs["riskoff_segments"] == []
    assert hs["last_rebased"] is None and hs["n"] == 0
    assert hs["window_start"] == "0" and hs["window_end"] == "1" and hs["count"] == 2


def test_spark_pts_semantics_unchanged():
    pts = BF._spark_pts([float("nan"), 1.0, 2.0, 3.0], 300, 36)
    assert len(pts.split()) == 3                       # NaN dropped, rest re-spread
    assert _pts(pts)[0][0] == 0.0 and _pts(pts)[-1][0] == 300.0
    assert BF._spark_pts([1.0], 300, 36) == ""
    assert BF._window_segments([1.0], 300, 36) == ["0.0,18.0"]  # new helper differs


def test_template_renders_segments_dots_and_window_label():
    hs = dollar_vm(_dol(risk=_gapped_risk))["hero_spark"]
    html = _render(dict(_DOLLAR_STUB, hero_spark=hs))
    region = _spark_region(html)
    # 2 multi-point riskoff segments + 1 dollar polyline; singleton -> dot
    assert region.count("<polyline") == 3, region.count("<polyline")
    assert region.count("<circle") == 1
    # no polyline spans a gap: every emitted polyline is one builder segment
    for seg in hs["riskoff_segments"] + hs["dollar_segments"]:
        if len(_pts(seg)) > 1:
            assert f'points="{seg}"' in region
    # concise same-dates / separate-scales label with the actual window dates
    assert "Same dates, separate scales" in html
    assert f'{hs["window_start"]} → {hs["window_end"]} · 126 ' in html
    assert "observations" in html and "次观测" in html


def test_template_legacy_fixture_context_still_renders():
    """Old hero_spark dicts (pts fields, no segments) must not crash or blank."""
    legacy = {"hero_spark": {"w": 440, "h": 60, "dollar_pts": "0.0,58.0 440.0,2.0",
                             "riskoff_pts": "0.0,30.0 440.0,31.0",
                             "last_rebased": 100.0, "n": 2}}
    region = _spark_region(_render(legacy))
    assert region.count("<polyline") == 2
    assert "Same dates, separate scales" not in region  # no window metadata in legacy


def test_template_empty_hero_spark_renders_no_spark_block():
    assert '<div class="spark-wrap"' not in _render({"hero_spark": {}})


def test_no_positive_base_never_claims_a_rebased_value():
    hs = dollar_vm(_dol(broad=lambda i: 0.0, risk=lambda i: 0.0))["hero_spark"]
    assert hs["rebase_available"] is False
    assert hs["last_rebased"] is None
    assert hs["dollar_scale"] == "reported_index"
    assert len(_pts(hs["dollar_segments"][0])) == 126
    html = _render(dict(_DOLLAR_STUB, hero_spark=hs))
    assert "Broad USD (unrebased)" in html and "广义美元（原始值）" in html


def test_risk_only_window_remains_visible_without_a_dollar_trace():
    hs = dollar_vm(_dol(broad=lambda i: np.nan, risk=lambda i: 0.0))["hero_spark"]
    html = _render(dict(_DOLLAR_STUB, hero_spark=hs))
    assert _spark_region(html).count("<polyline") == 1
    legend = html.split('class="spark-legend"', 1)[1].split("</div>", 1)[0]
    assert "Risk-off" in legend
    assert "Broad USD" not in legend


def test_absent_risk_trace_has_no_risk_legend():
    hs = dollar_vm(_dol())["hero_spark"]
    html = _render(dict(_DOLLAR_STUB, hero_spark=hs))
    legend = html.split('class="spark-legend"', 1)[1].split("</div>", 1)[0]
    assert "Broad USD" in legend
    assert "Risk-off" not in legend


@pytest.mark.parametrize("case", ["constant_tail", "invalid_tail", "late", "complete"])
def test_actual_dollar_producer_retains_common_observation_window(case):
    from engine import forex_signals as FS
    cfg = BF.config.load()["forex"]
    assert cfg["dollar"]["risk"]["z_lookback_d"] == 252
    assert cfg["dollar"]["risk"]["components"]["vix"] == 1.0
    idx = pd.bdate_range("2023-01-02", periods=700)
    drivers = {
        "dxy": pd.Series(104.0, index=idx),
        "broad_dollar": pd.Series(np.linspace(100.0, 110.0, 700), index=idx),
    }
    if case in {"constant_tail", "invalid_tail"}:
        vix = np.r_[np.tile([10.0, 20.0], 150), np.full(400, 15.0 if case == "constant_tail" else np.inf)]
        drivers["vix"] = pd.Series(vix, index=idx)
    elif case == "late":
        drivers["vix"] = pd.Series(np.tile([10.0, 20.0], 25), index=idx[-50:])
    else:
        drivers["vix"] = pd.Series(np.tile([10.0, 20.0], 350), index=idx)
    dol = FS.dollar_master(drivers, cfg)
    dollar = BF.dollar_vm(dol)
    hs = dollar["hero_spark"]
    html = _render(dollar)
    legend = html.split('class="spark-legend"', 1)[1].split("</div>", 1)[0]
    assert hs["window_start"] == str(idx[574].date())
    assert hs["window_end"] == str(idx[699].date())
    assert hs["count"] == 126
    assert len(_pts(hs["dollar_segments"][0])) == 126
    if case == "invalid_tail":
        assert dol["risk_off"].last_valid_index() < idx[574]
        assert hs["riskoff_segments"] == []
        assert "Risk-off" not in legend
    elif case == "constant_tail":
        # Rolling variance can retain floating-point residue on a constant
        # tail in some pandas builds. Honor the actual producer: its finite
        # zero is not missing. This visual repair does not change that owner.
        finite = dol["risk_off"].tail(126).dropna()
        if finite.empty:
            assert hs["riskoff_segments"] == [] and "Risk-off" not in legend
        else:
            assert len(finite) == 126 and (finite == 0.0).all()
            assert len(_pts(hs["riskoff_segments"][0])) == 126
            assert "Risk-off" in legend
    elif case == "late":
        points = _pts(hs["riskoff_segments"][0])
        assert len(points) == 9
        assert [p[0] for p in points] == [round(i / 125 * 440, 1) for i in range(117, 126)]
        assert "Risk-off" in legend
    else:
        points = _pts(hs["riskoff_segments"][0])
        assert len(points) == 126
        assert (points[0][0], points[-1][0]) == (0.0, 440.0)
        assert "Risk-off" in legend


def test_explicit_null_input_slot_never_compresses_or_bridges():
    runs = BF._window_segments([0.0, 1.0, np.nan, 2.0, 3.0], 440, 60)
    assert [[p[0] for p in _pts(run)] for run in runs] == [[0.0, 110.0], [330.0, 440.0]]
