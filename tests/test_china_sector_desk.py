"""China Sector Desk + Pathway engine tests.

Pure-function invariants (zigzag turn detection, Wilson CI, leak-free standardization,
composite construction) always run. The data-dependent snapshot / evidence-gate tests
skip cleanly when the china_sectors plane is absent (a bare checkout) and assert the
contract when it is present (CI commits the data).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from collectors.china_sectors import SW_L1
from engine import china_sector_index as csi
from engine import china_sector_pathway as pw
from engine import china_sector_pathway_backtest as bt

HAVE_DATA = csi.sw_close("801780") is not None


# --------------------------------------------------------------- pure functions ----

def test_zigzag_detects_major_top_then_bottom():
    idx = pd.date_range("2020-01-01", periods=240, freq="B")
    vals = np.concatenate([
        np.linspace(100, 200, 80),   # +100% up-leg  -> a top at 200
        np.linspace(200, 90, 80),    # -55% down-leg -> a bottom at 90
        np.linspace(90, 260, 80),    # up-leg (unconfirmed, no trailing reversal)
    ])
    turns = csi.zigzag_turns(pd.Series(vals, index=idx), pct=0.25)
    kinds = [t["kind"] for t in turns]
    assert kinds[:2] == ["top", "bottom"]
    assert abs(turns[0]["price"] - 200) < 1.0
    assert abs(turns[1]["price"] - 90) < 1.0
    # alternation invariant
    assert all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))


def test_zigzag_flat_series_no_turns():
    idx = pd.date_range("2020-01-01", periods=120, freq="B")
    s = pd.Series(100 + np.sin(np.arange(120) / 5) * 2, index=idx)  # <25% wiggle
    assert csi.zigzag_turns(s, pct=0.25) == []


def test_wilson_interval_bounds():
    # W2.6: the bespoke pathway._wilson was ported to the shared grading_stats.wilson_ci and
    # the pathway now uses a date-blocked bootstrap for its conditional CI. Assert the shared
    # primitive still behaves, and that the pathway no longer carries a private copy.
    from engine.grading_stats import wilson_ci
    lo, hi = wilson_ci(8, 10)
    assert 0.0 <= lo <= 0.8 <= hi <= 1.0
    assert wilson_ci(0, 0) is None
    assert not hasattr(pw, "_wilson"), "the bespoke Wilson-on-overlap path must be gone (W2.6)"


def test_expanding_z_is_leak_free():
    s = pd.Series(np.arange(1, 101, dtype=float))
    full = pw._expanding_z(s, min_periods=12)
    # truncating the future must not change a past value (no look-ahead)
    trunc = pw._expanding_z(s.iloc[:60], min_periods=12)
    assert np.isclose(full.iloc[59], trunc.iloc[59], equal_nan=True)
    assert full.iloc[:11].isna().all()  # min_periods respected


def test_composite_index_lies_between_legs(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=120, freq="B")
    a = pd.Series(100 * (1.002 ** np.arange(120)), index=idx)   # strong
    b = pd.Series(100 * (1.000 ** np.arange(120)), index=idx)   # flat
    monkeypatch.setattr(csi, "sw_close", lambda code: {"X": a, "Y": b}.get(code))
    comp = csi.composite_index(["X", "Y"])
    assert comp is not None and len(comp) > 0 and (comp > 0).all()
    # equal-weight composite return sits strictly between the two legs
    assert b.iloc[-1] / b.iloc[0] < comp.iloc[-1] / comp.iloc[0] < a.iloc[-1] / a.iloc[0]


def test_sw_universe_covers_every_gs_basket():
    for key, b in csi.GS_BASKETS.items():
        codes = b.get("sw_composite") or [b["sw"]]
        for c in codes:
            assert c in SW_L1, f"{key} references unknown Shenwan code {c}"


# ------------------------------------------------------------ data-dependent ----

@pytest.mark.skipif(not HAVE_DATA, reason="china_sectors data plane absent")
def test_desk_snapshot_contract():
    from engine.china_sector_desk import snapshot
    snap = snapshot()
    assert snap and snap["sectors"]
    assert len(snap["sectors"]) >= 12
    s = snap["sectors"][0]
    for k in ("name", "sw_code", "level", "position", "live_sym", "spark"):
        assert k in s
    assert 0 <= s["position"]["score"] <= 100
    assert {"leaders", "laggards", "washed_out", "euphoric"} <= set(snap["summary"])


@pytest.mark.skipif(not HAVE_DATA, reason="china_sectors data plane absent")
def test_pathway_snapshot_contract():
    snap = pw.snapshot()
    assert snap and len(snap["sectors"]) == 4
    for s in snap["sectors"]:
        assert s["bbg"].startswith("GSXAC")
        assert s["setup"]["tercile"] in ("low", "mid", "high")
        assert s["caveat_en"] and s["narrative_en"]
        # W2.6 era-stabilization: fixed constituent set disclosed + composite defined only
        # from the all-legs-live month; conditional CI is a block-bootstrap lift band, n_months.
        comp = s.get("composition") or {}
        assert comp.get("version") and comp.get("first_all_legs_live")
        for h, c in s["conditional"].items():
            assert 0.0 <= c["cond_rate"] <= 1.0
            assert c["n_months"] >= 8 and 1.0 <= c["n_eff"] <= c["n_months"]
            assert c["composition_version"] == comp["version"]
            if c.get("lift_ci_lo") is not None:
                assert c["lift_ci_lo"] <= c["lift_ci_hi"]


@pytest.mark.skipif(not HAVE_DATA, reason="china_sectors data plane absent")
def test_evidence_gate_signature_holds():
    rep = bt.run_gate()
    assert rep["passed"], f"signature gate failed: {rep}"
    # every HARD signature check must show bottoms below tops on the washout axis
    for c in rep["checks"]:
        if c["type"] == "signature":
            assert c["bottom_pctile"] < c["top_pctile"]


# ------------------------------------------------ page render: gate row + cohort label ----
# Synthetic fixtures shaped like the committed pathway record and the producer's run_gate()
# return (engine/china_sector_pathway_backtest.py:115-185). The gate is computed at build time
# and never written to JSON, so these renders are the only place its wording is pinned.

_POOLED = [
    {"leg": "dist_p", "n_bottom": 40, "n_top": 42, "median_bottom": 0.013, "median_top": 0.844,
     "gap_ci": [0.2246, 0.4642], "sign_ok": True, "evidence": True},
    {"leg": "dd_p", "n_bottom": 40, "n_top": 42, "median_bottom": 0.022, "median_top": 0.985,
     "gap_ci": [0.229, 0.4811], "sign_ok": True, "evidence": True},
]
_DRIFT = [
    {"sector": "banks", "type": "cluster_sign", "leg": "credit_impulse", "hard": False,
     "ic": -0.086, "expect_sign": 1, "ok": False},
    {"sector": "real_estate", "type": "cluster_sign", "leg": "credit_impulse", "hard": False,
     "ic": -0.088, "expect_sign": 1, "ok": False},
]


def _pw_sector(key, en, zh, tercile):
    h6 = {"h": 6, "base_rate": 0.54, "cond_rate": 0.75, "lift": 0.21, "lift_ci_lo": 0.0427,
          "lift_ci_hi": 0.389, "n_months": 20, "n_eff": 4.4, "n_base_months": 90,
          "med_fwd_pct": 6.1, "base_med_pct": 2.0}
    return {"key": key, "en": en, "zh": zh, "bbg": "GSXACBNK", "level": 1000.0, "span": "2008–",
            "position": {"score": 40.0, "label": "Neutral", "label_zh": "中性"},
            "conditional": {"h6": h6}, "setup": {"tercile": tercile, "legs": []},
            "narrative_en": "N", "narrative_zh": "N", "turns": {}, "caveat_en": "C",
            "caveat_zh": "C"}


def _pathway():
    return {"sectors": [_pw_sector("banks", "China Banks", "中国银行", "low"),
                        _pw_sector("real_estate", "China Real Estate", "中国地产", "high")]}


def _render_desk(gate, pathway=None):
    import json
    from collections import defaultdict
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    desk = {"as_of": "2026-10-16", "sectors": [], "summary": {}}
    return env.get_template("china_sector_desk.html.j2").render(
        C=defaultdict(lambda: "#000"), desk=desk, pathway=pathway or _pathway(), gate=gate,
        desk_json=json.dumps(desk), built="TEST BUILD")


def _gate_row(html):
    import re

    rows = re.findall(r'<div class="gate[^"]*">.*?</div>', html, re.S)
    assert len(rows) == 1, rows
    return rows[0]


def _gate(**kw):
    g = {"available": True, "passed": True, "checks": [], "pooled": _POOLED,
         "evidence_legs": ["dist_p", "dd_p"], "soft_warnings": [], "note": "ok"}
    g.update(kw)
    return g


def test_gate_row_prints_pooled_sample_size_and_band():
    row = _gate_row(_render_desk(_gate()))
    assert row.startswith('<div class="gate ok">✓')
    for s in ("n=40/42", "1→84", "2→98", "22–46pp", "23–48pp", '<span class="l-en">evidence</span>',
              "<span class=\"l-zh\">证据</span>", "pooled bottoms sit below tops"):
        assert s in row, s
    assert "signature checks pass" not in row and "Evidence gate" not in row


def test_gate_row_names_the_drifted_leg_and_sector():
    row = _gate_row(_render_desk(_gate(soft_warnings=_DRIFT)))
    for s in ("China Banks", "中国银行", "China Real Estate", "中国地产",
              '<span class="l-en">credit impulse</span>', "信贷脉冲", "IC -0.09", "+)"):
        assert s in row, s
    assert "credit_impulse" not in row and "sign-drift note" not in row
    six = [dict(_DRIFT[0], ic=-0.01 * i) for i in range(6)]
    row6 = _gate_row(_render_desk(_gate(soft_warnings=six)))
    assert row6.count('<span class="l-en">sign drift</span>') == 4 and " · +2" in row6


def test_gate_does_not_claim_evidence_when_ci_includes_zero():
    weak = [dict(_POOLED[0], gap_ci=[-0.05, 0.3], evidence=False),
            dict(_POOLED[1], gap_ci=None, evidence=False)]
    row = _gate_row(_render_desk(_gate(pooled=weak, evidence_legs=[])))
    assert row.count('<span class="l-en">directional only</span>') == 2
    assert ">evidence<" not in row and ">证据<" not in row and "-5–30pp" in row
    flip = [dict(_POOLED[0], median_bottom=0.9, median_top=0.1, sign_ok=False, evidence=False)]
    frow = _gate_row(_render_desk(_gate(pooled=flip, passed=False, evidence_legs=[])))
    assert frow.startswith('<div class="gate warn">⚠') and "✓" not in frow
    assert '<span class="l-en">flipped</span>' in frow and "需复核" in frow and "90→10" in frow


def test_gate_unavailable_renders_skipped_not_a_tick():
    gate = {"available": False, "passed": True, "checks": [], "pooled": [],
            "note": "china_sectors / benchmark data absent — gate skipped"}
    row = _gate_row(_render_desk(gate))
    assert row.startswith('<div class="gate warn">⚠') and "✓" not in row
    assert "not run" in row and "拐点特征门槛未运行" in row and "pooled bottoms" not in row


def test_cohort_label_names_the_top_third_and_flags_when_today_is_outside_it():
    import re

    ci = r'<div class="ci">((?:(?!</div>).)*?)(?= · )'
    labels = re.findall(ci, _render_desk(_gate()), re.S)
    assert len(labels) == 2, labels
    assert all("when setup is in its top third" in x for x in labels)
    assert "(<span class=\"l-en\">not today</span>" in labels[0] and "今日不在此区间" in labels[0]
    assert "not today" not in labels[1]
    assert "when setup ~ today" not in _render_desk(_gate())
