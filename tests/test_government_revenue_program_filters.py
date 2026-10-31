"""D5 Program Dossier filtered-empty copy and control/URL state-sync contracts.

These tests execute the page's real IIFE against a bounded fake DOM. They prove
behavior, not string presence: a verified program row that a ticker filter hides
must read as filtered-empty (never "ontology unverifiable"), the Clear filters
action must restore the actual row while keeping the programs mode and bringing
the URL and the filter controls back into agreement, and the async options
rebuild must keep the selected agency/ticker controls in sync with real state.
Canonical D5 program rows carry ``tickers: []``; nothing here invents a mapping.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "government_revenue.html.j2").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "templates" / "government-revenue-page.js.j2").read_text(encoding="utf-8")
TEMPLATE += "\n<script>" + CONTROLLER + "</script>"
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

FILTERED_EN = "No programs match filters"
FILTERED_ZH = "没有符合筛选的项目"
EXPLAIN_EN = "Clear the filters to see the reviewed programs in this evidence cut."
EXPLAIN_ZH = "清除筛选可查看当前证据截点中的已复核项目。"
ACTION_EN = "Clear filters"
ACTION_ZH = "清除筛选"
UNVERIFIABLE = "The program ontology could not be verified"

ROW_TOKEN = "PHAASE-77"
ROW_ID = "program:PHAASE-77"
DEEP_LINK = "?mode=programs&item=program%3APHAASE-77&ticker=LMT"


def _page_runtime_js() -> str:
    assert '__hydrateGovernmentWorkspace' in CONTROLLER
    return CONTROLLER


def _program_row() -> dict:
    """One canonical D5 row: a reviewed ontology member whose tickers: [] is intentional."""
    return {
        "id": ROW_ID,
        "kind": "program_dossier",
        "truth": "reviewed",
        "linked": False,
        "coverage": False,
        "defense": True,
        "tickers": [],
        "agency": "Department of Test and Evaluation",
        "date": "2026-08-01",
        "title": f"Program {ROW_TOKEN}",
        "subtitle": "Reviewed program ontology row fixture",
    }


_HARNESS = textwrap.dedent(
    """
    (async function(){
    var OPTS = %(opts)s;
    var RUNTIME = %(runtime)s;
    var listeners = {};
    var nodeStore = {};
    function makeEl(id){
      var el = {id:id, textContent:'', innerHTML:'', hidden:false, disabled:false, value:'',
        className:'', dataset:{}, style:{}, attributes:{},
        addEventListener:function(name, fn){(listeners[id]=listeners[id]||{})[name]=(listeners[id][name]||[]).concat([fn])},
        setAttribute:function(k,v){el.attributes[k]=String(v)},
        getAttribute:function(k){return Object.prototype.hasOwnProperty.call(el.attributes,k)?el.attributes[k]:null},
        removeAttribute:function(k){delete el.attributes[k]},
        querySelectorAll:function(){return []}, querySelector:function(){return null},
        closest:function(){return null}, focus:function(){}, blur:function(){},
        classList:{add:function(){},remove:function(){},toggle:function(){},contains:function(){return false}}};
      return el;
    }
    function $(id){if(!nodeStore[id])nodeStore[id]=makeEl(id);return nodeStore[id]}
    function fire(id,name,ev){((listeners[id]||{})[name]||[]).forEach(function(fn){fn.call($(id),ev||{})})}
    $('gov-data').textContent = JSON.stringify(OPTS.payload);
    var urlRecords = [];
    var documentElement = {
      getAttribute:function(name){return name==='data-lang'?OPTS.lang:'en'},
      setAttribute:function(){},
      clientWidth:1440,
      scrollTop:0
    };
    var doc = {
      documentElement:documentElement, activeElement:null, body:{style:{}},
      getElementById:function(id){return $(id)},
      querySelectorAll:function(){return []},
      addEventListener:function(name, fn){(listeners['doc']=listeners['doc']||{})[name]=(listeners['doc'][name]||[]).concat([fn])},
      dispatchEvent:function(){return true}
    };
    var initialUrl = new URL('https://example.test/government_revenue.html'+OPTS.search);
    var location = {href:initialUrl.href, pathname:initialUrl.pathname,
      search:initialUrl.search, hash:initialUrl.hash};
    var historyCalls = [], historyEntries = [{href:location.href,state:null}];
    function writeHistory(method,state,url){
      var next = new URL(url,location.href);
      if(next.origin!==initialUrl.origin)throw new Error('cross-origin history write');
      var path = next.pathname+next.search+next.hash;
      // Record address changes separately from initial same-address state storage.
      if(next.href!==location.href)urlRecords.push(path);
      historyCalls.push({method:method,url:path});
      history.state=structuredClone(state);
      if(method==='push')historyEntries.push({href:next.href,state:history.state});
      else historyEntries[historyEntries.length-1]={href:next.href,state:history.state};
      location.href=next.href;location.pathname=next.pathname;
      location.search=next.search;location.hash=next.hash;
    }
    var history = {state:null,
      replaceState:function(state,_title,url){writeHistory('replace',state,url)},
      pushState:function(state,_title,url){writeHistory('push',state,url)}};
    var navigator = {clipboard:null};
    var window = {MDXAuth:{enabled:function(){return false},onChange:function(){}},location:location, history:history, navigator:navigator, innerWidth:1440,
      addEventListener:function(){}, dispatchEvent:function(){return true}};
    function mountProgramFactory(){
      window.createGovernmentRevenueProgramDossier = function(api){
        function emit(){
          api.onRows(OPTS.rows, {status:OPTS.status});
          global.__programDeliveries = (global.__programDeliveries || 0) + 1;
        }
        global.__emitProgram = emit;
        return {load:function(){emit();return Promise.resolve(OPTS.rows)}, refresh:function(){return OPTS.rows},
          render:function(row){global.__programRendered = row ? row.id : null},
          invalidate:function(){}, state:function(){return OPTS.status}};
      };
    }
    global.document = doc;
    window.createGovernmentRevenueBudget = function(api){return {load:function(){api.onRows([],{status:'unavailable'});return Promise.resolve([])},refresh:function(){return[]},render:function(){},invalidate:function(){},state:function(){return'unavailable'}}};
    window.createGovernmentRevenueFms = function(api){return {load:function(){api.onRows([],{status:'unavailable'});return Promise.resolve([])},refresh:function(){return[]},render:function(){},invalidate:function(){},state:function(){return'unavailable'}}};
    window.createGovernmentRevenueCandidateRadar = function(api){return {load:function(){api.onRows([],{status:'unavailable',total:0,mapping_backlog_total:0,mapping_backlog_tickers:[],mapping_backlog_states:{},freshness:{}});return Promise.resolve([])},refresh:function(){return[]},render:function(){},invalidate:function(){},state:function(){return'unavailable'},crosschecks:function(){return''}}};
    function CustomEvent(name, init){this.type=name;this.detail=init&&init.detail}
    var __timers = [];
    var setTimeout = function(fn, ms){__timers.push({fn:fn, at:Date.now()+(ms||0)});return __timers.length};
    function runDue(){
      var now = Date.now();
      for(;;){
        var idx = -1, best = Infinity;
        for(var i=0;i<__timers.length;i++){if(__timers[i].at<=now && __timers[i].at<best){best=__timers[i].at;idx=i}}
        if(idx<0)break;
        var t = __timers.splice(idx,1)[0];
        try{t.fn()}catch(e){console.error('timer threw',e&&e.stack||e)}
      }
    }
    async function wait(ms){await new Promise(function(resolve){require('timers').setTimeout(resolve,ms)});runDue();}
    function lastUrlParams(){
      return Object.fromEntries(new URL(location.href).searchParams);
    }
    function snapshot(){
      return {
        queueHtml: $('queueList').innerHTML,
        queueSummary: $('queueSummary').textContent,
        selection: window.__governmentRevenueRuntime.currentSelection(),
        urlParams: lastUrlParams(),
        urlRecords: urlRecords.slice(),
        historyCalls: historyCalls.slice(),
        historyLength: historyEntries.length,
        historyState: history.state,
        controls: {ticker: $('tickerFilter').value, agency: $('agencyFilter').value, search: $('deskSearch').value},
        tickerOptionsHtml: $('tickerFilter').innerHTML,
        countPrograms: String($('countPrograms').textContent),
        inspectorHtml: $('inspector').innerHTML,
        deliveries: global.__programDeliveries || 0,
        renderedProgram: global.__programRendered || null
      };
    }
    mountProgramFactory();
    eval(RUNTIME);
    await wait(40);
    var first = snapshot();
    if (OPTS.clickClear) fire('clearProgramFilters', 'click');
    await wait(40);
    var second = snapshot();
    if (OPTS.reEmit) { global.__emitProgram(); await wait(40); }
    process.stdout.write(JSON.stringify({first: first, second: second, third: snapshot()}));
    })().catch(function(error){console.error(error);process.exitCode=1});
    """
)


def _run(tmp_path: Path, *, rows: list[dict], status: str, search: str = "",
         lang: str = "en", click_clear: bool = False, re_emit: bool = False) -> dict:
    opts = {
        "payload": {"companies": [{"ticker": "LMT", "name": "Lockheed Martin"}],
                    "market": {}, "freshness": {"status": "ok"},
                    "opportunity_intelligence": {"market": {}, "opportunities": [], "events": []}},
        "rows": rows,
        "status": status,
        "search": search,
        "lang": lang,
        "clickClear": click_clear,
        "reEmit": re_emit,
    }
    script = _HARNESS % {"opts": json.dumps(opts), "runtime": json.dumps(_page_runtime_js())}
    path = tmp_path / "d5_program_filters.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"node failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    assert result.stdout.strip(), f"runtime emitted no result; stderr:\n{result.stderr}"
    return json.loads(result.stdout)


def test_d5_filtered_empty_is_a_bilingual_actionable_branch_in_source() -> None:
    """The frozen copy pairs and the working tool-btn action ship in the page source."""
    for pair in (
        (FILTERED_EN, FILTERED_ZH),
        (EXPLAIN_EN, EXPLAIN_ZH),
        (ACTION_EN, ACTION_ZH),
    ):
        assert f"tr('{pair[0]}','{pair[1]}')" in TEMPLATE, pair
    assert "programsFilteredEmpty()?tr('Clear the filters to see the reviewed programs in this evidence cut.','清除筛选可查看当前证据截点中的已复核项目。')" in TEMPLATE
    assert 'id="clearProgramFilters"' in TEMPLATE
    assert "clearFilters.addEventListener('click',clearProgramFilters)" in TEMPLATE
    assert "$('agencyFilter').value=state.agency;$('tickerFilter').value=state.ticker" in TEMPLATE
    assert "function programFiltersActive(){" in TEMPLATE
    # Semantic help only: no telemetry/score rides along with the fix.
    assert "filter cleared" not in TEMPLATE.lower()
    for banned in ("falsifier", "refuted", "refutation", "Refutation", "证伪"):
        assert banned not in TEMPLATE, banned


@needs_node
def test_verified_program_hidden_by_ticker_reads_filtered_empty_not_unverifiable(tmp_path: Path) -> None:
    """LMT filmstrip deep link: one verified program row, tickers:[], ticker filter hides it.

    The observed live defect said the ontology could not be verified. The truth is
    that a filter hid rows the ontology vouched for — so the desk must say so and
    offer the way back, without ever claiming or inventing a program-company link.
    """
    out = _run(tmp_path, rows=[_program_row()], status="ok", search=DEEP_LINK)
    before = out["first"]

    assert before["countPrograms"] == "1"
    # The hidden deep link stays pending (never substituted), the visible
    # selection is honestly empty while zero rows pass the filters.
    assert before["selection"] == {"mode": "programs", "ticker": "LMT",
                                   "selected": "", "pending": ROW_ID}
    assert str(before["queueSummary"]).startswith("0 covered records")
    # The filtered-empty branch, not the unverifiable one.
    assert FILTERED_EN in before["queueHtml"]
    assert EXPLAIN_EN in before["queueHtml"]
    assert UNVERIFIABLE not in before["queueHtml"]
    assert "Program ontology unavailable" not in before["queueHtml"]
    # The action is present in the empty state.
    assert 'id="clearProgramFilters"' in before["queueHtml"]
    # Rendered in the active locale (like every other empty-state string here);
    # the zh twin is pinned by the source test and the zh runtime test.
    assert ACTION_EN in before["queueHtml"]
    # No inferred mapping appears anywhere in the empty state.
    assert "LMT" not in before["queueHtml"]
    # The filtered-empty round never rewrites the deep link: state, controls and
    # URL all still agree on ticker=LMT (this agreement is what the defect broke).
    assert before["urlRecords"] == []
    assert before["historyLength"] == 1
    assert all(call["method"] == "replace" for call in before["historyCalls"])
    assert before["historyState"]["governmentRevenue"]["schema"] == 1
    assert before["selection"]["ticker"] == "LMT"
    # Focused regression: the async onRows -> populateFilters rewrite restores the
    # actual selected control instead of leaving it blank while state holds LMT.
    assert before["controls"]["ticker"] == "LMT"
    assert before["renderedProgram"] is None
    assert before["deliveries"] == 1


@needs_node
def test_clear_filters_action_restores_the_row_keeps_mode_and_re_syncs_url_and_controls(tmp_path: Path) -> None:
    out = _run(tmp_path, rows=[_program_row()], status="ok", search=DEEP_LINK, click_clear=True)
    before, after = out["first"], out["second"]

    assert FILTERED_EN in before["queueHtml"]
    # The actual valid row is reintroduced — the same reviewed program, unchanged.
    assert ROW_TOKEN in after["queueHtml"]
    assert f'data-row="{ROW_ID}"' in after["queueHtml"]
    assert after["queueSummary"].startswith("1 covered records")
    assert after["countPrograms"] == "1"
    # Mode is preserved and the four filter facets are cleared together.
    assert after["selection"]["mode"] == "programs"
    assert after["selection"]["ticker"] == ""
    assert after["selection"]["pending"] == ""
    assert after["selection"]["selected"] == ROW_ID
    assert after["renderedProgram"] == ROW_ID
    # URL and controls now agree with state: no stale ticker facet left behind.
    assert after["urlParams"].get("mode") == "programs"
    assert "ticker" not in after["urlParams"]
    assert after["controls"] == {"ticker": "", "agency": "", "search": ""}


@needs_node
def test_async_options_rebuild_keeps_the_current_agency_and_ticker_selection(tmp_path: Path) -> None:
    """A later onRows rebuild of the option lists must not blank the live selection."""
    row = _program_row()
    row["agency"] = "Department of Transportation"
    out = _run(tmp_path, rows=[row], status="ok",
               search="?mode=programs&agency=Department+of+Transportation&ticker=LMT",
               re_emit=True)
    before, after = out["first"], out["third"]
    assert before["controls"]["ticker"] == "LMT"
    assert before["controls"]["agency"] == "Department of Transportation"
    assert ROW_TOKEN not in before["queueHtml"]  # the agency facet really hides the row
    # The second async delivery re-ran populateFilters(); the selection persists.
    assert after["deliveries"] == before["deliveries"] + 1
    assert after["controls"]["ticker"] == "LMT"
    assert after["controls"]["agency"] == "Department of Transportation"
    assert after["selection"]["ticker"] == "LMT"


@needs_node
@pytest.mark.parametrize(
    ("status", "rows", "expected_marker"),
    [
        # Verified rows hidden by the ticker filter must not flip any other arm's
        # verdict into "filter-empty", and vice versa.
        ("loading", [_program_row()], "Verifying the program ontology"),
        ("locked", [_program_row()], "Program Dossier is locked"),
        ("ontology_unavailable", [_program_row()], "Program ontology unavailable"),
        ("invalid", [_program_row()], UNVERIFIABLE),
        ("unavailable", [_program_row()], UNVERIFIABLE),
        ("empty", [_program_row()], "No current program on file"),
        # A genuinely empty verified graph stays valid-empty with no filter.
        ("ok", [], "No current program on file"),
    ],
)
def test_distinct_program_branches_cannot_become_filter_empty(
    tmp_path: Path, status: str, rows: list[dict], expected_marker: str
) -> None:
    """Every other arm keeps its own verdict even while a ticker filter is active."""
    search = DEEP_LINK if rows else "?mode=programs"
    out = _run(tmp_path, rows=rows, status=status, search=search)
    html = out["first"]["queueHtml"]
    assert expected_marker in html, (status, html[:400])
    assert FILTERED_EN not in html
    assert EXPLAIN_EN not in html
    assert 'id="clearProgramFilters"' not in html
    # The locked arm keeps its membership meta untouched; the others keep no CTA.
    if status == "locked":
        assert "plans.html" in html
    else:
        assert "plans.html" not in html


@needs_node
def test_valid_empty_graph_stays_valid_empty_under_a_filter(tmp_path: Path) -> None:
    """A verified ontology with zero programs is valid-empty — never 'no rows match'."""
    out = _run(tmp_path, rows=[], status="ok", search="?mode=programs&ticker=LMT")
    html = out["first"]["queueHtml"]
    assert "No current program on file" in html
    assert "certified program ontology is active, but no current program identity exists" in html
    assert FILTERED_EN not in html
    assert ACTION_EN not in html


@needs_node
def test_filtered_empty_help_is_translated_in_chinese_mode(tmp_path: Path) -> None:
    out = _run(tmp_path, rows=[_program_row()], status="ok", search=DEEP_LINK, lang="zh")
    html = out["first"]["queueHtml"]
    assert FILTERED_ZH in html
    assert EXPLAIN_ZH in html
    assert ACTION_ZH in html
    assert "项目本体无法完成核验" not in html


@needs_node
def test_other_modes_keep_their_own_empty_copy_when_a_filter_hides_every_row(tmp_path: Path) -> None:
    """The D5 branch does not leak: a changes-mode filtered-empty keeps the quiet-tape copy."""
    out = _run(tmp_path, rows=[], status="ok", search="?mode=changes&ticker=LMT")
    html = out["first"]["queueHtml"]
    assert "No qualifying changes" in html
    assert FILTERED_EN not in html
    assert 'id="clearProgramFilters"' not in html
