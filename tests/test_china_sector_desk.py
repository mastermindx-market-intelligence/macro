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


def _render_desk(gate, pathway=None, desk=None):
    import json
    from collections import defaultdict
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    desk = desk or {"as_of": "2026-10-16", "sectors": [], "summary": {}}
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


# --- W27A SPEC 3/4/5 + F14: the board's benchmark strip, cycle cells, turn map and horizon ---
# Synthetic payloads shaped like the committed desk.json / pathway.json records (W27A §2 F3-F7).

_BENCH = {"ticker": "510300.SS", "name": "CSI 300", "name_zh": "沪深300", "level": 4.236,
          "chg_1d": -0.14, "chg_5d": -3.4, "chg_20d": -8.25, "chg_60d": -10.88, "chg_ytd": -8.56}
_BANKS_CYC = {"state": "TURN SIGNALED", "state_zh": "TURN SIGNALED", "score": 45,
              "bottom_confidence": 48.7, "label": "BOTTOMING", "label_zh": "筑底中"}


def _desk_row(position=None, cycle=None):
    pos = {"score": 83.0, "label": "Stretched", "label_zh": "偏高", "dist_200d_pct": 6.5,
           "drawdown_pct": -1.6}
    return {"sw_code": "801780", "name": "Banks", "name_zh": "银行", "history_from": "1999-12",
            "live_sym": "512800.SS", "etf_last": 0.861, "level": 4265.6, "chg_1d": 0.1,
            "chg_5d": 0.2, "chg_20d": 0.3, "chg_ytd": 0.4, "rs": {"mom_60d": 24.45},
            "position": pos if position is None else position, "cycle": cycle,
            "valuation": None, "last_turn": None, "spark": []}


def _desk(rows=(), benchmark=None):
    return {"as_of": "2026-10-16", "sectors": list(rows), "summary": {}, "benchmark": benchmark}


def _tbody(html):
    i = html.index('<table class="board"')
    return html[i:html.index("</tbody>", i)]


def _board_head(html):
    return html[html.index("Live Sector Board"):html.index('<table class="board"')]


def test_benchmark_strip_renders_committed_returns():
    head = _board_head(_render_desk(_gate(), desk=_desk(benchmark=_BENCH)))
    for s in ("-0.14%", "-3.40%", "-8.25%", "-10.88%", "-8.56%", "510300.SS", "沪深300",
              '<span class="l-en">board RS basis</span><span class="l-zh">看板相对强度基准</span>',
              '<span class="l-en">60D</span><span class="l-zh">60日</span>'):
        assert s in head, s
    assert head.count('<span class="chip">') == 5


def test_benchmark_strip_never_prints_the_etf_price_as_an_index_level():
    head = _board_head(_render_desk(_gate(), desk=_desk(benchmark=_BENCH)))
    assert "4.236" not in head and "4.24" not in head
    assert '<span class="l-en">ETF proxy</span><span class="l-zh">ETF代理</span>' in head


def test_benchmark_strip_absent_when_benchmark_missing():
    no_key = _desk([_desk_row(cycle=_BANKS_CYC)])
    no_key.pop("benchmark")
    for desk in (_desk([_desk_row(cycle=_BANKS_CYC)], {}), _desk([_desk_row(cycle=_BANKS_CYC)]),
                 no_key):
        html = _render_desk(_gate(), desk=desk)
        head = _board_head(html)
        assert "board RS basis" not in head and "None" not in head and "chip" not in head
        assert "BOTTOMING" in _tbody(html)
    part = dict(_BENCH, chg_1d=None, chg_ytd=None)
    head = _board_head(_render_desk(_gate(), desk=_desk(benchmark=part)))
    assert head.count('<span class="chip">') == 3 and "None" not in head and "chg na" not in head


def test_benchmark_strip_bilingual():
    head = _board_head(_render_desk(_gate(), desk=_desk(benchmark=_BENCH)))
    assert '<span class="l-en">CSI 300</span><span class="l-zh">沪深300</span>' in head
    assert '<span class="l-en">YTD</span><span class="l-zh">年初至今</span>' in head


def test_ladder_keeps_the_producers_bilingual_label(monkeypatch):
    from engine import china_sector_desk as desk_mod
    from engine import cycles

    lad = {"state": "TURN SIGNALED", "label": "BOTTOMING", "label_zh": "筑底中", "score": 45,
           "bottom_confidence": 48.7}
    monkeypatch.setattr(cycles, "analyze", lambda *a, **k: {"ladder": lad})
    out = desk_mod._ladder(pd.Series([1.0, 2.0]), None)
    assert out == {"state": "TURN SIGNALED", "state_zh": "TURN SIGNALED", "score": 45,
                   "bottom_confidence": 48.7, "label": "BOTTOMING", "label_zh": "筑底中"}
    monkeypatch.setattr(cycles, "analyze", lambda *a, **k: 1 / 0)
    assert desk_mod._ladder(pd.Series([1.0, 2.0]), None) is None


def test_state_cell_renders_zh_label_not_the_raw_token():
    body = _tbody(_render_desk(_gate(), desk=_desk([_desk_row(cycle=_BANKS_CYC)])))
    for s in ('<span class="cyc"><span class="l-en">BOTTOMING</span><span class="l-zh">筑底中</span>',
              "+6.50%", "-1.60%", "较200日均线", "距1年高点", "筑底置信度",
              '<span class="l-en">bottom conf.</span>', " 48.7</small>",
              '<td data-sort="6.5"><span class="pill-pos">', '<td data-sort="48.7">'):
        assert s in body, s
    assert "TURN SIGNALED" not in body


def test_confidence_and_inputs_omitted_when_null():
    import re

    coal = {"state": "RALLY ON", "state_zh": "RALLY ON", "score": 60, "bottom_confidence": None,
            "label": "UPTREND", "label_zh": "上涨趋势"}
    pos = {"score": 40.0, "label": "Neutral", "label_zh": "中性", "dist_200d_pct": 3.2,
           "drawdown_pct": None}
    body = _tbody(_render_desk(_gate(), desk=_desk([_desk_row(position=pos, cycle=coal)])))
    assert re.findall(r'<small class="poslbl">(.*?)</small>', body) == [
        '<span class="chg pos">+3.20%</span> '
        '<span class="l-en">vs 200d avg</span><span class="l-zh">较200日均线</span>']
    assert "上涨趋势" in body and body.count("data-sort") == 1
    for s in ("None", "null", "·%", "bottom conf.", "from 1y high"):
        assert s not in body, s
    bare = {"score": None, "label": "Neutral", "label_zh": "中性", "dist_200d_pct": None,
            "drawdown_pct": None}
    body = _tbody(_render_desk(_gate(), desk=_desk([_desk_row(position=bare)])))
    assert "<small class=\"poslbl\"" not in body and "data-sort" not in body
    assert "None" not in body and '<span class="chg na">·</span></td>' in body


def test_state_falls_back_to_state_when_label_absent():
    old = {"state": "TURN SIGNALED", "state_zh": "TURN SIGNALED", "score": 45,
           "bottom_confidence": 22.4}
    body = _tbody(_render_desk(_gate(), desk=_desk([_desk_row(cycle=old)])))
    assert '<span class="cyc">TURN SIGNALED</span>' in body and " 22.4</small>" in body
    assert "None" not in body


def test_board_sorts_the_cycle_cells_on_their_numbers():
    html = _render_desk(_gate(), desk=_desk([_desk_row(cycle=_BANKS_CYC)]))
    assert "c.getAttribute('data-sort')" in html and "d!==null?d:(c.textContent||'')" in html
    assert "var x=sk(a.cells[ci]), y=sk(b.cells[ci]);" in html


_RE_TURNS = [{"kind": "top", "date": "2001-07-20", "price": 1715.6},
             {"kind": "bottom", "date": "2025-04-07", "price": 1871.0},
             {"kind": "top", "date": "2025-11-17", "price": 2436.2}]


def _turns_pathway(history, n_bottoms, n_tops):
    sec = _pw_sector("real_estate", "China Real Estate", "中国地产", "high")
    sec["turns"] = {"last": {"kind": "top", "date": "2025-11-17", "price": 2436.2},
                    "n_bottoms": n_bottoms, "n_tops": n_tops}
    if history is not None:
        sec["turns"]["history"] = history
    return {"sectors": [sec]}


def _turn_map(html):
    i = html.index("Last major turn")
    return html[html.index("</div>", i) + len("</div>"):html.index('<div class="caveat">', i)]


def test_turn_map_renders_committed_rows():
    tm = _turn_map(_render_desk(_gate(), pathway=_turns_pathway(_RE_TURNS, 1, 2)))
    for s in ("2001-07-20", "1715.6", "2025-04-07", "1871.0", "2025-11-17", "2436.2"):
        assert s in tm, s
    assert tm.count('<span class="leg">') == 3 and "earlier turns" not in tm
    assert tm.index("2025-11-17 · 2436.2") < tm.index("2025-04-07 · 1871.0") < tm.index(
        "2001-07-20 · 1715.6")


def test_turn_map_caps_at_eight_and_reports_the_rest():
    rows = [{"kind": "top" if i % 2 else "bottom", "date": f"{1980 + i}-06-30",
             "price": round(1000.04 + i, 2)} for i in range(39)]
    tm = _turn_map(_render_desk(_gate(), pathway=_turns_pathway(rows, 20, 19)))
    assert tm.count('<span class="leg">') == 8
    assert "2018-06-30 · 1038.0</span>" in tm and "2011-06-30 · 1031.0</span>" in tm
    assert "2010-06-30" not in tm and "1030.0" not in tm
    assert " · +31 <span class=\"l-en\">earlier turns</span>" in tm and "更早拐点" in tm


def test_turn_map_absent_falls_back_to_counts_only():
    for hist in ([], None):
        html = _render_desk(_gate(), pathway=_turns_pathway(hist, 4, 3))
        assert '4<span class="l-en">B</span><span class="l-zh">底</span>/3' in html
        tm = _turn_map(html)
        assert '<span class="leg">' not in tm and '<div class="legs">' not in tm
        assert "earlier turns" not in tm


def test_turn_map_bilingual():
    tm = _turn_map(_render_desk(_gate(), pathway=_turns_pathway(_RE_TURNS, 1, 2)))
    assert tm.count('<span class="l-en">top</span><span class="l-zh">顶</span>') == 2
    assert tm.count('<span class="l-en">bottom</span><span class="l-zh">底</span>') == 1


def test_cohort_horizon_label_follows_the_cohort_shown():
    sec = _pw_sector("banks", "China Banks", "中国银行", "low")
    sec["conditional"] = {"h3": dict(sec["conditional"]["h6"], h=3)}
    html = _render_desk(_gate(), pathway={"sectors": [sec]})
    assert '<span class="l-en">Fwd 3m up-rate</span><span class="l-zh">未来3月上涨率</span>' in html
    assert '<span class="l-en">Median fwd 3m</span><span class="l-zh">未来3月中位</span>' in html
    assert "Fwd 6m" not in html and "未来6月" not in html
    six = _render_desk(_gate())
    assert six.count('<span class="l-en">Fwd 6m up-rate</span>') == 2 and "Fwd 3m" not in six
    sec6 = _pw_sector("banks", "China Banks", "中国银行", "low")
    sec6["conditional"]["h6"].pop("h")
    assert "Fwd 6m up-rate" in _render_desk(_gate(), pathway={"sectors": [sec6]})
