"""W11 r2 — absolute stamp, lane-true feed words, resettable board cap, degraded stance.

Packet: packet_intraday_flow.md (P2 M4/M5/P2-RISK) plus review_pr7070.md B1/M-a/M-b/M-c/M-d
and the r2 minors. Both language lanes are probed at the same mechanism.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.test_intraday_flow_w11_r1 import (
    _DOM_SHIM,
    _region,
    _run_node,
    _src,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

ESC_LZ = r"""
function lz(en, zh){ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
"""

RELATIVE_DAY = ("today", "yesterday", "tomorrow", "今天", "昨天", "明天")


def _stamp_js() -> str:
    src = _src()
    return "\n".join((
        _region(src, "function feedWord", "function computeStance"),
        _region(src, "function updateFlowStamp", "// ══ compute-once"),
    ))


def _stamp(q: str, p: str, f: str, *, disp: bool = True, leaders: int = 1) -> dict:
    d = "{en:'10 Sep 11:34pm UTC', zh:'9月10日 23:34 UTC'}" if disp else "undefined"
    script = f"""
    {ESC_LZ}
    var BASE_DATA = {{as_of_display: {d}}};
    var leaders = {'[{ticker:"NVDA"}]' if leaders else '[]'};
    var quotesStatus = '{q}', pulseStatus = '{p}', flowStatus = '{f}';
    var stamp = {{ innerHTML: '' }};
    var document = {{ getElementById: function(id){{ return id === 'ift-stamp' ? stamp : null; }} }};
    {_stamp_js()}
    updateFlowStamp(null, null);
    var h = stamp.innerHTML;
    function pick(tag){{
      var o=[], re=new RegExp('class="l-'+tag+'">([^<]*)','g'), m;
      while ((m=re.exec(h))) o.push(m[1]);
      return o;
    }}
    var tipRowsEn = [], tipRowsZh = [];
    var re = /class="ift-feed-row"><span class="l-en">([^<]*)<\\/span><span class="l-zh">([^<]*)<\\/span><\\/div>/g;
    var m;
    while ((m = re.exec(h))) {{ tipRowsEn.push(m[1]); tipRowsZh.push(m[2]); }}
    process.stdout.write(JSON.stringify({{
      en: pick('en'), zh: pick('zh'), raw: h,
      tipEn: tipRowsEn.join('\\n'), tipZh: tipRowsZh.join('\\n'),
      tipRowsEn: tipRowsEn, tipRowsZh: tipRowsZh
    }}));
    """
    return _run_node(script)


def _apply_board(*, n: int, expanded: bool = False, search: str = "",
                 extra: str = "") -> dict:
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch", zh:'观望', lane:'lane-watch', order:4}} }};
    var sortCol = 'rvol', sortDir = -1;
    var activeBasket = 'all', activeStance = 'all', searchQ = '{search}', groupByStance = true;
    var BOARD_CAP = 8, boardExpanded = {str(expanded).lower()};
    {_DOM_SHIM}
    var tbody = new Node();
    var lbl = {{ innerHTML: '' }};
    var document = {{
      getElementById: function(id){{
        if (id==='leaders-body') return tbody;
        if (id==='count-label') return lbl;
        return null;
      }},
      querySelectorAll: function(){{ return []; }},
      createElement: function(){{ return new Node(); }},
      createDocumentFragment: function(){{ var n = new Node(); n._isFrag = true; return n; }}
    }};
    {apply_js}
    for (var i=0;i<{n};i++){{
      var tk = 'T' + (i<10?'0':'') + i;
      tbody.appendChild(makeLead(tk, {n}-i));
    }}
    applyView();
    {extra}
    process.stdout.write(JSON.stringify({{
      visible: visibleLeads(tbody).length,
      label: lbl.innerHTML,
      boardExpanded: boardExpanded
    }}));
    """
    return _run_node(script)


# ── B1 absolute stamp ────────────────────────────────────────────────────────

def test_builder_absolute_form_has_no_relative_day_words():
    from scripts.build_intraday_flow import _as_of_display

    now = datetime(2026, 9, 11, 14, 0, tzinfo=timezone.utc)
    got = _as_of_display("2026-09-10T23:34:28.190939+00:00", now=now)
    assert got == {"en": "10 Sep 11:34pm UTC", "zh": "9月10日 23:34 UTC"}
    src = (ROOT / "scripts" / "build_intraday_flow.py").read_text(encoding="utf-8")
    fn = src[src.index("def _as_of_display") : src.index("def _ledger_enabled")]
    body = fn.split('"""', 2)[-1]  # skip the docstring; payload + stamp are the contract
    for word in RELATIVE_DAY:
        assert word not in body
        assert word not in got["en"]
        assert word not in got["zh"]


def test_static_stamp_and_payload_have_no_relative_day_words():
    src = _src()
    stamp = _region(src, 'id="ift-stamp"', "</header>")
    for word in RELATIVE_DAY:
        assert word not in stamp
    assert "still connecting" not in stamp
    assert "连接中" not in stamp
    assert "skel" in stamp
    assert "lens-q" not in stamp  # LENS is mounted after the first fetch attempt


# ── M-a/M-b/M-c feed-word composition ────────────────────────────────────────

LANES = ("quotes", "tape", "options")
STATES = ("live", "unavailable", "connecting")

FEED_MATRIX = {
    ("quotes", "live"): ("carrying prices", "报价已送达"),
    ("quotes", "unavailable"): ("prices not coming through", "报价未送达"),
    ("quotes", "connecting"): ("still connecting", "连接中"),
    ("tape", "live"): ("carrying trades", "成交已送达"),
    ("tape", "unavailable"): ("trades not coming through", "成交未送达"),
    ("tape", "connecting"): ("still connecting", "连接中"),
    ("options", "live"): ("carrying flow", "流数据已送达"),
    ("options", "unavailable"): ("flow not coming through", "流数据未送达"),
    ("options", "connecting"): ("still connecting", "连接中"),
}

TIP_LABEL = {
    "quotes": ("quotes", "行情"),
    "tape": ("tape", "资金带"),
    "options": ("options", "期权流"),
}


@needs_node
def test_feedword_matrix_3_lanes_x_4_states_x_2_languages():
    """Bare phrases: 3 lanes × live/unavailable/connecting (connecting covers the 4th 'all-lanes' state)."""
    src = _src()
    js = _region(src, "function feedWord", "function computeStance")
    script = f"""
    {js}
    var lanes = ['quotes','tape','options'];
    var states = ['live','unavailable','connecting'];
    var out = {{}};
    lanes.forEach(function(lane){{
      states.forEach(function(st){{
        var w = feedWord(st, lane);
        out[lane+'|'+st] = w;
      }});
    }});
    process.stdout.write(JSON.stringify(out));
    """
    out = _run_node(script)
    for lane in LANES:
        for state in STATES:
            got = out[f"{lane}|{state}"]
            en, zh = FEED_MATRIX[(lane, state)]
            assert got["en"] == en, (lane, state, got)
            assert got["zh"] == zh, (lane, state, got)
            assert lane not in got["en"], (lane, state, got)
            # Phrase never contains the lane noun in either language.
            for noun in ("行情", "资金带", "期权流"):
                assert noun not in got["zh"]


@needs_node
def test_mixed_state_headline_names_the_true_worst_lane():
    """Reviewer P2: quotes=live, tape=connecting, options=unavailable."""
    r = _stamp("live", "connecting", "unavailable")
    en = " ".join(r["en"])
    zh = " ".join(r["zh"])
    assert "options flow not coming through" in en
    assert "期权流数据未送达" in zh
    assert "tape carrying" not in en
    assert "all feeds carrying" not in en
    assert "some feeds" not in en
    # tip rows each true, no noun stutter; rows are block elements, not one ' · ' string
    assert r["tipRowsEn"] == [
        "quotes · carrying prices",
        "tape · still connecting",
        "options · flow not coming through",
    ]
    assert r["tipRowsZh"] == [
        "行情 · 报价已送达",
        "资金带 · 连接中",
        "期权流 · 流数据未送达",
    ]
    assert "quotes · carrying prices · tape" not in r["raw"]
    assert "行情 · 报价已送达 · 资金带" not in r["raw"]
    assert "tape · carrying the tape" not in r["raw"]
    assert "行情 行情" not in r["raw"]
    assert "行情 行情" not in r["tipZh"]


@needs_node
def test_headline_all_carrying_all_unavailable_and_each_single_degraded():
    all_live = _stamp("live", "live", "live")
    assert "all feeds carrying" in " ".join(all_live["en"])
    assert "各路数据已送达" in " ".join(all_live["zh"])

    all_down = _stamp("unavailable", "unavailable", "unavailable")
    assert "some feeds not coming through" in " ".join(all_down["en"])
    assert "部分数据未送达" in " ".join(all_down["zh"])

    cases = [
        ("unavailable", "live", "live", "prices not coming through", "行情数据未送达"),
        ("live", "unavailable", "live", "trades not coming through", "资金带数据未送达"),
        ("live", "live", "unavailable", "options flow not coming through", "期权流数据未送达"),
        ("connecting", "live", "live", "feeds still connecting", "数据连接中"),
        ("live", "connecting", "live", "feeds still connecting", "数据连接中"),
        ("live", "live", "connecting", "feeds still connecting", "数据连接中"),
    ]
    for q, p, f, en, zh in cases:
        r = _stamp(q, p, f)
        joined_en = " ".join(r["en"])
        joined_zh = " ".join(r["zh"])
        assert en in joined_en, (q, p, f, joined_en)
        assert zh in joined_zh, (q, p, f, joined_zh)
        assert "tape carrying prices" not in joined_en


# ── M-d latch + m1 count ─────────────────────────────────────────────────────

@needs_node
def test_expand_then_filter_resets_cap_and_restores_control():
    extra = """
    boardExpanded = true;
    applyView();
    var afterExpand = {visible: visibleLeads(tbody).length, label: lbl.innerHTML};
    searchQ = 'T11';
    boardExpanded = false;
    applyView();
    var afterFilter = {visible: visibleLeads(tbody).map(function(r){return r.getAttribute('data-ticker');}), label: lbl.innerHTML};
    """
    # Drive the sequence inside one VM so boardExpanded is the same binding applyView closes over.
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch", zh:'观望', lane:'lane-watch', order:4}} }};
    var sortCol = 'rvol', sortDir = -1;
    var activeBasket = 'all', activeStance = 'all', searchQ = '', groupByStance = true;
    var BOARD_CAP = 8, boardExpanded = false;
    {_DOM_SHIM}
    var tbody = new Node();
    var lbl = {{ innerHTML: '' }};
    var document = {{
      getElementById: function(id){{
        if (id==='leaders-body') return tbody;
        if (id==='count-label') return lbl;
        return null;
      }},
      querySelectorAll: function(){{ return []; }},
      createElement: function(){{ return new Node(); }},
      createDocumentFragment: function(){{ var n = new Node(); n._isFrag = true; return n; }}
    }};
    {apply_js}
    for (var i=0;i<12;i++){{
      tbody.appendChild(makeLead('T'+(i<10?'0':'')+i, 12-i));
    }}
    applyView();
    var defVis = visibleLeads(tbody).length;
    boardExpanded = true;
    applyView();
    var expVis = visibleLeads(tbody).length;
    var expLabel = lbl.innerHTML;
    searchQ = 'T11';
    boardExpanded = false;  // the search handler's contract
    applyView();
    var filt = {{
      visible: visibleLeads(tbody).map(function(r){{ return r.getAttribute('data-ticker'); }}),
      label: lbl.innerHTML
    }};
    process.stdout.write(JSON.stringify({{
      defVis: defVis, expVis: expVis, expLabel: expLabel, filt: filt
    }}));
    """
    out = _run_node(script)
    assert out["defVis"] == 8
    assert out["expVis"] == 12
    assert "Show top 8" in out["expLabel"]
    assert "只看前 8 只" in out["expLabel"]
    assert out["filt"]["visible"] == ["T11"]
    assert "1 leader" in out["filt"]["label"]
    assert "See all" not in out["filt"]["label"]


@needs_node
def test_collapse_control_returns_capped_view():
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch", zh:'观望', lane:'lane-watch', order:4}} }};
    var sortCol = 'rvol', sortDir = -1;
    var activeBasket = 'all', activeStance = 'all', searchQ = '', groupByStance = true;
    var BOARD_CAP = 8, boardExpanded = true;
    {_DOM_SHIM}
    var tbody = new Node();
    var lbl = {{ innerHTML: '' }};
    var document = {{
      getElementById: function(id){{
        if (id==='leaders-body') return tbody;
        if (id==='count-label') return lbl;
        return null;
      }},
      querySelectorAll: function(){{ return []; }},
      createElement: function(){{ return new Node(); }},
      createDocumentFragment: function(){{ var n = new Node(); n._isFrag = true; return n; }}
    }};
    {apply_js}
    for (var i=0;i<12;i++) tbody.appendChild(makeLead('T'+(i<10?'0':'')+i, 12-i));
    applyView();
    var expanded = {{visible: visibleLeads(tbody).length, label: lbl.innerHTML}};
    boardExpanded = false;
    applyView();
    var collapsed = {{visible: visibleLeads(tbody).length, label: lbl.innerHTML}};
    process.stdout.write(JSON.stringify({{expanded: expanded, collapsed: collapsed}}));
    """
    out = _run_node(script)
    assert out["expanded"]["visible"] == 12
    assert "Show top 8" in out["expanded"]["label"]
    assert out["collapsed"]["visible"] == 8
    assert "See all 12" in out["collapsed"]["label"]
    assert "查看全部 12 只" in out["collapsed"]["label"]


@needs_node
def test_at_rest_count_when_population_is_at_or_below_cap():
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch", zh:'观望', lane:'lane-watch', order:4}} }};
    var sortCol = 'rvol', sortDir = -1;
    var activeBasket = 'all', activeStance = 'all', searchQ = '', groupByStance = true;
    var BOARD_CAP = 8, boardExpanded = false;
    {_DOM_SHIM}
    var tbody = new Node();
    var lbl = {{ innerHTML: '' }};
    var document = {{
      getElementById: function(id){{
        if (id==='leaders-body') return tbody;
        if (id==='count-label') return lbl;
        return null;
      }},
      querySelectorAll: function(){{ return []; }},
      createElement: function(){{ return new Node(); }},
      createDocumentFragment: function(){{ var n = new Node(); n._isFrag = true; return n; }}
    }};
    {apply_js}
    for (var i=0;i<5;i++) tbody.appendChild(makeLead('T0'+i, 5-i));
    applyView();
    process.stdout.write(JSON.stringify({{visible: visibleLeads(tbody).length, label: lbl.innerHTML}}));
    """
    out = _run_node(script)
    assert out["visible"] == 5
    assert "5 leaders" in out["label"]
    assert "共 5 只" in out["label"]
    assert "See all" not in out["label"]


def test_view_changing_inputs_reset_board_expanded():
    src = _src()
    events = _region(src, "// ── Events", "// ── Polling")
    assert "boardExpanded = false" in events
    assert events.count("boardExpanded = false") >= 4  # sort, basket, stance, search (group too)
    assert "data-ift-collapse" in src
    assert "Show top '+BOARD_CAP" in src
    assert "只看前 '+BOARD_CAP+' 只" in src


# ── m2 tapeChip esc, m3 LENS, n1, copy nits ─────────────────────────────────

@needs_node
def test_tapechip_unknown_slug_goes_through_esc():
    src = _src()
    js = "\n".join((
        ESC_LZ,
        _region(src, "function prettyBasket", "// ── Dealer compact"),
    ))
    script = js + """
    var out = {};
    out.known = tapeChip('WHALE', 2);
    out.unknown = tapeChip('SWEEP', 2);
    out.xss = tapeChip('<img src=x onerror=alert(1)>', 1);
    process.stdout.write(JSON.stringify(out));
    """
    out = _run_node(script)
    assert "big block×2" in out["known"]
    assert "SWEEP×2" in out["unknown"]
    assert "&lt;img" in out["xss"]
    assert "<img" not in out["xss"]


def test_stamp_tip_is_canonical_lens_not_page_local_help():
    src = _src()
    stamp_js = _region(src, "function updateFlowStamp", "// ══ compute-once")
    assert "lens-q" in stamp_js
    assert "lens-src" in stamp_js
    assert "ift-feed-row" in stamp_js
    assert "data-tip-en" not in stamp_js
    assert '<span class="help">' not in stamp_js
    assert "class=\"tip\"" not in stamp_js
    # other sanctioned help() tips on the page remain
    assert "{{ help(" in src


def test_copy_nits_drop_realtime_overclaim():
    src = _src()
    assert "Counts update as the tape refreshes." in src
    assert "计数随资金带刷新而更新。" in src
    assert "Counts update live as the tape moves." not in src
    assert "计数随资金带实时更新。" not in src
    assert "tape not flowing yet" in src
    assert "资金带尚未流动" in src
    assert "live tape not flowing yet" not in src
    assert "实时资金带尚未流动" not in src


# ── M4 ~soft, M5 skeletons, P2-RISK ──────────────────────────────────────────

def test_per_row_soft_chip_removed_footnote_and_tilde_kept():
    src = _src()
    row = _region(src, "function spotCard", "function buildRow")
    board = _region(src, "function buildRow", "function prettyBasket")
    assert 'soft-tag">~soft' not in row
    assert 'soft-tag">~soft' not in board
    assert "~call buying" in src
    assert "~买入看涨" in src
    assert "~soft — a tape rule" in src
    assert "~软性" in src


def test_loading_is_skeleton_geometry_not_empty_copy():
    src = _src()
    hero = _region(src, 'id="hero-thesis"', 'id="hero-sub"')
    assert "skel" in hero
    assert "Reading the tape" not in hero
    spot = _region(src, 'id="spot-grid"', "</section>")
    assert "spot-skel" in spot
    assert "spot-empty" not in spot  # loading must not reuse empty
    assert "Reading the tape" not in spot
    # empty structural still exists for the live empty branch
    assert "spot-empty" in src
    assert "ift-skel-row" in src
    assert "Loading leaders" not in src


@needs_node
def test_quotes_outage_during_rth_is_degraded_not_stand_aside():
    src = _src()
    stance_js = _region(src, "function computeStance", "function fmtNum")
    script = f"""
    function isMarketHours(){{ return true; }}
    function quotePx(q){{ return (q && q.price != null) ? Number(q.price) : null; }}
    function computeVwapDelta(){{ return null; }}
    function dealerOf(){{ return null; }}
    var quotesStatus = 'unavailable';
    {stance_js}
    var conf = {{legs:[null,false,false,false,null,false,null]}};
    var outage = computeStance({{ticker:'NVDA'}}, null, null, null, conf);
    quotesStatus = 'live';
    var aside = computeStance({{ticker:'NVDA'}}, {{price:100, changePct:0}}, {{bars_today:10, vwap:99}}, null, conf);
    quotesStatus = 'connecting';
    var connecting = computeStance({{ticker:'NVDA'}}, null, null, null, conf);
    process.stdout.write(JSON.stringify({{outage: outage, aside: aside, connecting: connecting}}));
    """
    out = _run_node(script)
    assert out["outage"]["key"] == "degraded"
    assert out["outage"]["reason_en"] == "Prices aren't coming through — no read on this name right now"
    assert out["outage"]["reason_zh"] == "行情未送达——该标的暂无判断"
    assert out["aside"]["key"] == "stand_aside"
    assert out["aside"]["reason_en"] == "Quiet tape, no setup right now."
    assert out["connecting"]["key"] != "degraded"


def test_light_rules_cover_the_three_new_surfaces():
    src = _src()
    assert "post-stack: consolidate" in src
    light = src[src.index("post-stack: consolidate") :]
    assert ".ift-see-all" in light
    assert ".ctx-stamp" in light
    assert ".skel" in light
    assert "html[data-theme=\"light\"]" in light
