"""W11 r1 — coverage-true feed words, bilingual tape chips, 8-of-N board, one-line stamp.

Packet: packet_intraday_flow.md (P0 M1 + P1 C1/C2/C3+C4/M2/M3). Both language
lanes are probed at the same mechanism. Template-only: this page is a .j2
producer; the site copy is the render lane's job.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _region(src: str, start: str, end: str) -> str:
    i = src.index(start)
    return src[i : src.index(end, i)]


def _run_node(script: str) -> dict:
    res = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"
    assert res.stdout.strip(), f"no stdout; stderr:\n{res.stderr}"
    return json.loads(res.stdout)


# ── M1 / C3+C4 stamp ─────────────────────────────────────────────────────────

DELAYED_TAG = "{{ t('≈15-min delayed','≈15分钟延迟') }}"

ABSENT_EN = "Board can't load right now — the plain-word calls below are from the last build"
ABSENT_ZH = "看板暂时无法加载——下方结论来自上一次构建"


def test_delayed_tag_is_byte_identical():
    assert DELAYED_TAG in _src()


def test_stamp_static_has_no_iso_or_base_or_live_vocab():
    src = _src()
    stamp = _region(src, 'id="ift-stamp"', "</header>")
    assert "live" not in stamp
    assert "实时" not in stamp
    assert "BASE" not in stamp
    assert "2026-" not in stamp
    assert "T23:" not in stamp
    assert ABSENT_EN in src
    assert ABSENT_ZH in src
    assert "Board built " in src
    assert "看板构建于" in src


def test_feedword_source_is_coverage_vocab_both_lanes():
    src = _src()
    fn = _region(src, "function feedWord", "function computeStance")
    assert "carrying prices" in fn
    assert "prices not coming through" in fn
    assert "still connecting" in fn
    assert "行情已送达" in fn
    assert "行情未送达" in fn
    assert "连接中" in fn
    assert "carrying flow" in fn
    assert "流数据已送达" in fn
    assert "'live'" not in fn or "status === 'live'" in fn
    assert "已接入" not in fn
    assert "不可用" not in fn


@needs_node
def test_stamp_at_full_quotes_coverage_prints_no_live_or_realtime():
    """M1 acceptance: quotes forced to 100% coverage → #ift-stamp never says live/实时."""
    src = _src()
    js = "\n".join((
        _region(src, "function feedWord", "function computeStance"),
        _region(src, "function updateFlowStamp", "// ══ compute-once"),
    ))
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var BASE_DATA = {{as_of_display: {{en: 'today 11:34pm UTC', zh: '今天 23:34 UTC'}}}};
    var leaders = [{{ticker: 'NVDA'}}];
    var quotesStatus = 'live', pulseStatus = 'live', flowStatus = 'live';
    var stamp = {{ innerHTML: '' }};
    var document = {{ getElementById: function(id){{ return id === 'ift-stamp' ? stamp : null; }} }};
    {js}
    updateFlowStamp(null, null);
    var html = stamp.innerHTML;
    var en = (html.match(/class="l-en">([^<]*)</g) || []).map(function(s){{ return s.replace(/.*">/,'').replace('<',''); }}).join(' ');
    var zh = (html.match(/class="l-zh">([^<]*)</g) || []).map(function(s){{ return s.replace(/.*">/,'').replace('<',''); }}).join(' ');
    process.stdout.write(JSON.stringify({{ html: html, en: en, zh: zh }}));
    """
    out = _run_node(script)
    html, en, zh = out["html"], out["en"], out["zh"]
    assert "live" not in html.lower() or "live" not in re.sub(
        r"status === 'live'|quotesStatus === 'live'", "", html.lower()
    )
    assert "live" not in en.lower()
    assert "实时" not in html
    assert "实时" not in zh
    assert "BASE" not in html
    assert "Board built today 11:34pm UTC · tape carrying prices" in en
    assert "看板构建于今天 23:34 UTC · 行情已送达" in zh
    assert "carrying flow" in en  # options lane, in the tip
    assert "流数据已送达" in zh
    assert "quotes carrying prices" in en
    assert "?" in html


@needs_node
def test_stamp_absent_payload_is_the_packet_error_form_both_lanes():
    src = _src()
    js = "\n".join((
        _region(src, "function feedWord", "function computeStance"),
        _region(src, "function updateFlowStamp", "// ══ compute-once"),
    ))
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var BASE_DATA = {{}};
    var leaders = [];
    var quotesStatus = 'live', pulseStatus = 'live', flowStatus = 'live';
    var stamp = {{ innerHTML: '' }};
    var document = {{ getElementById: function(id){{ return id === 'ift-stamp' ? stamp : null; }} }};
    {js}
    updateFlowStamp(null, null);
    process.stdout.write(JSON.stringify({{ html: stamp.innerHTML }}));
    """
    html = _run_node(script)["html"]
    assert ABSENT_EN in html
    assert ABSENT_ZH in html
    assert "live" not in html.lower()
    assert "实时" not in html
    assert "BASE" not in html


def test_builder_humanizes_as_of_at_the_builder():
    from scripts.build_intraday_flow import _as_of_display

    now = datetime(2026, 9, 10, 23, 40, tzinfo=timezone.utc)
    got = _as_of_display("2026-09-10T23:34:28.190939+00:00", now=now)
    assert got == {"en": "today 11:34pm UTC", "zh": "今天 23:34 UTC"}
    yest = _as_of_display("2026-09-09T23:34:00+00:00", now=now)
    assert yest == {"en": "yesterday 11:34pm UTC", "zh": "昨天 23:34 UTC"}
    am = _as_of_display("2026-09-10T00:05:00Z", now=now)
    assert am == {"en": "today 12:05am UTC", "zh": "今天 00:05 UTC"}
    assert _as_of_display(None) == {}
    assert _as_of_display("not-a-date") == {}
    assert "T23:" not in got["en"]
    assert "+00:00" not in got["en"]
    assert "190939" not in got["en"]


# ── C1 tape chips ────────────────────────────────────────────────────────────

@needs_node
def test_tape_chips_are_bilingual_at_construction_both_lanes():
    src = _src()
    js = "\n".join((
        "function lz(en, zh){ return '<span class=\"l-en\">'+en+'</span><span class=\"l-zh\">'+(zh||en)+'</span>'; }",
        "function esc(s){ return String(s==null?'':s); }",
        _region(src, "function prettyBasket", "// ── Dealer compact"),
    ))
    script = f"""
    {js}
    var bc = {{WHALE:3, FRESH:4, Z_OUTLIER:2, SIZE_VS_OI:1, REPEAT_HITTER:2}};
    var badges = [];
    ['WHALE','FRESH','Z_OUTLIER','SIZE_VS_OI','REPEAT_HITTER'].forEach(function(b){{
      if (bc[b]>0) badges.push(tapeChip(b, bc[b]));
    }});
    var shown = badges.slice(0,3);
    var html = shown.map(function(b){{ return '<span class="badge badge-blue">'+b+'</span>'; }}).join('');
    process.stdout.write(JSON.stringify({{
      n: badges.length,
      shown: shown.length,
      html: html,
      hasWhaleSlug: /WHALE/.test(html),
      en: shown.map(function(s){{ var m=s.match(/class="l-en">([^<]+)/); return m?m[1]:''; }}),
      zh: shown.map(function(s){{ var m=s.match(/class="l-zh">([^<]+)/); return m?m[1]:''; }})
    }}));
    """
    out = _run_node(script)
    assert out["n"] == 5
    assert out["shown"] == 3
    assert out["hasWhaleSlug"] is False
    assert out["en"] == ["big block×3", "new position×4", "unusual size×2"]
    assert out["zh"] == ["大单×3", "新建仓×4", "异常规模×2"]
    # The two that lose the .slice(0,3) cap still map, they just don't render.
    assert "size vs open interest" in _src()
    assert "规模对比未平仓" in _src()
    assert "repeat buyer" in _src()
    assert "重复买入" in _src()


# ── M2 prettyBasket ──────────────────────────────────────────────────────────

@needs_node
def test_pretty_basket_reuses_filter_chip_zh_through_lz():
    src = _src()
    js = "\n".join((
        "function lz(en, zh){ return '<span class=\"l-en\">'+en+'</span><span class=\"l-zh\">'+(zh||en)+'</span>'; }",
        "function esc(s){ return String(s==null?'':s); }",
        _region(src, "function prettyBasket", "// ── Dealer compact"),
    ))
    script = f"""
    {js}
    var keys = ['mag7','ai_infra','ai_software','ai_semiconductors','semicap_equipment','reshoring','defense','power_grid'];
    var out = {{}};
    keys.forEach(function(k){{
      var h = prettyBasket(k);
      out[k] = {{
        en: (h.match(/class="l-en">([^<]+)/)||[])[1],
        zh: (h.match(/class="l-zh">([^<]+)/)||[])[1]
      }};
    }});
    process.stdout.write(JSON.stringify(out));
    """
    out = _run_node(script)
    assert out["mag7"] == {"en": "Mag7", "zh": "Mag7"}
    assert out["ai_infra"]["zh"] == "AI基础"
    assert out["ai_software"]["zh"] == "AI软件"
    assert out["ai_semiconductors"]["zh"] == "AI芯片"
    assert out["semicap_equipment"]["zh"] == "设备"
    assert out["reshoring"]["zh"] == "回流"
    assert out["defense"]["zh"] == "国防"
    assert out["power_grid"]["zh"] == "电网"
    src = _src()
    # Filter chips keep the same ZH strings; Mag7 stays untranslated in the chip.
    assert '<span class="chip" data-basket="mag7">Mag7</span>' in src
    assert "{{ t('AI Infra', 'AI基础') }}" in src
    assert "{{ t('Power Grid', '电网') }}" in src


# ── M3 hero legend ───────────────────────────────────────────────────────────

def test_hero_legend_drops_integers_hs_count_untouched():
    src = _src()
    legend = _region(src, "leg += ", "var comp = document.getElementById")
    assert "lz(meta.en,meta.zh)+'</span>'" in legend
    assert "lz(meta.en,meta.zh)+' '+v" not in src
    assert "id=\"hs-count\"" in src
    assert "animateCount(num, actionable)" in src


# ── C2 counted control ───────────────────────────────────────────────────────

_DOM_SHIM = r"""
function Node() {
  this.childNodes = [];
  this.style = {display: ''};
  this.className = '';
  this.innerHTML = '';
  this.attrs = {};
  this.parentNode = null;
  this.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs,k) ? this.attrs[k] : null; };
  this.setAttribute = function(k,v){ this.attrs[k] = String(v); };
  this.appendChild = function(c){
    if (c._isFrag) {
      var kids = c.childNodes.slice();
      for (var i=0;i<kids.length;i++) this.appendChild(kids[i]);
      c.childNodes = [];
      return c;
    }
    if (c.parentNode && c.parentNode.removeChild) {
      var arr = c.parentNode.childNodes, ix = arr.indexOf(c);
      if (ix>=0) arr.splice(ix,1);
    }
    c.parentNode = this;
    this.childNodes.push(c);
    return c;
  };
  this.removeChild = function(c){
    var ix = this.childNodes.indexOf(c);
    if (ix>=0) this.childNodes.splice(ix,1);
    c.parentNode = null;
    return c;
  };
  this.querySelectorAll = function(sel){
    var out = [];
    (this.childNodes||[]).forEach(function(ch){
      if (sel==='tr.group-head' && /\bgroup-head\b/.test(ch.className)) out.push(ch);
      else if (sel==='tr.lead-row' && /\blead-row\b/.test(ch.className)) out.push(ch);
      else if (sel==='tr.detail-row' && /\bdetail-row\b/.test(ch.className)) out.push(ch);
    });
    return out;
  };
}
function visibleLeads(tbody){
  return tbody.querySelectorAll('tr.lead-row').filter(function(r){ return r.style.display !== 'none'; });
}
function makeLead(tk, rvol){
  var r = new Node();
  r.className = 'lead-row';
  r.attrs = {
    'data-ticker': tk, 'data-stance': 'watch', 'data-rvol': String(rvol),
    'data-stance-order': '4', 'data-k': '0', 'data-baskets': 'all', 'data-last': '0'
  };
  return r;
}
"""


@needs_node
def test_board_defaults_to_8_and_see_all_n_equals_rendered_rows():
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch — don't chase", zh:'观望——勿追', lane:'lane-watch', order:4}} }};
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
      var tk = 'T' + (i<10?'0':'') + i;
      tbody.appendChild(makeLead(tk, 12-i));
    }}
    applyView();
    var defVis = visibleLeads(tbody).map(function(r){{ return r.getAttribute('data-ticker'); }});
    var en = lbl.innerHTML;
    var see = (en.match(/class="l-en">See all (\\d+)/)||[])[1];
    var showing = (en.match(/class="l-en">Showing (\\d+) of (\\d+)/)||[]);
    var controlN = Number(see);
    boardExpanded = true;
    applyView();
    var expVis = visibleLeads(tbody).map(function(r){{ return r.getAttribute('data-ticker'); }});
    process.stdout.write(JSON.stringify({{
      defaultVisible: defVis.length,
      defaultTickers: defVis,
      showingShown: showing[1] ? Number(showing[1]) : null,
      showingTotal: showing[2] ? Number(showing[2]) : null,
      controlN: controlN,
      expandedVisible: expVis.length,
      expandedTickers: expVis,
      labelAfterExpand: lbl.innerHTML,
      zhSee: (en.match(/class="l-zh">查看全部 (\\d+) 只/)||[])[1],
      zhShow: (en.match(/class="l-zh">显示 (\\d+) \\/ (\\d+) 只/)||[]).slice(1)
    }}));
    """
    out = _run_node(script)
    assert out["defaultVisible"] == 8
    assert out["showingShown"] == 8
    assert out["showingTotal"] == 12
    assert out["controlN"] == 12
    assert out["controlN"] == out["expandedVisible"]
    assert out["expandedVisible"] == 12
    assert out["zhSee"] == "12"
    assert out["zhShow"] == ["8", "12"]
    assert out["labelAfterExpand"] == ""
    # Top 8 by current sort (rvol desc): T00..T07
    assert out["defaultTickers"] == [f"T0{i}" for i in range(8)]


@needs_node
def test_filter_narrowing_below_8_shows_the_set_with_no_control():
    src = _src()
    apply_js = _region(src, "var COL_ATTR", "// ── Full render")
    script = f"""
    function lz(en, zh){{ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh||en)+'</span>'; }}
    var STANCE_META = {{ watch: {{en:"Watch", zh:'观望', lane:'lane-watch', order:4}} }};
    var sortCol = 'rvol', sortDir = -1;
    var activeBasket = 'all', activeStance = 'all', searchQ = 'T11', groupByStance = true;
    var BOARD_CAP = 8, boardExpanded = false;
    {_DOM_SHIM}
    var tbody = new Node();
    var lbl = {{ innerHTML: 'stale' }};
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
      var tk = 'T' + (i<10?'0':'') + i;
      tbody.appendChild(makeLead(tk, 12-i));
    }}
    applyView();
    var vis = visibleLeads(tbody).map(function(r){{ return r.getAttribute('data-ticker'); }});
    process.stdout.write(JSON.stringify({{ visible: vis, label: lbl.innerHTML }}));
    """
    out = _run_node(script)
    assert out["visible"] == ["T11"]
    assert out["label"] == ""
    assert "See all" not in out["label"]
    assert "查看全部" not in out["label"]


def test_counted_control_copy_is_the_packet_form_in_source():
    src = _src()
    assert "Showing '+showN+' of '+total+' leaders · " in src
    assert "显示 '+showN+' / '+total+' 只 · " in src
    assert "See all '+total" in src
    assert "查看全部 '+total+' 只" in src
    assert "var BOARD_CAP = 8" in src


def test_mag7_chip_and_honesty_chips_untouched():
    src = _src()
    assert '<span class="chip" data-basket="mag7">Mag7</span>' in src
    assert DELAYED_TAG in src
    assert "~call buying" in src
    assert "~买入看涨" in src
    assert "id=\"hs-count\"" in src
