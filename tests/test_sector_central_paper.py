"""Macro Paper migration: data truth and the actual page boundary."""
from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "templates"


def _node(js: str):
    result = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _chart():
    return {
        "dates": [f"2026-09-{day:02d}" for day in range(1, 22)],
        "bench": [100 + i for i in range(21)],
        "baskets": {"group": [100 + 2 * i for i in range(21)]},
    }


def _series(chart, subject="group"):
    src = (TPL / "_sector_central_brief.js.j2").read_text()
    return _node(src + "\nprocess.stdout.write(JSON.stringify(buildSectorBriefSeries("
                 + json.dumps(subject) + "," + json.dumps(chart) + ")));")


def test_relative_wealth_uses_gross_ratio_and_twenty_intervals():
    read = _series(_chart())
    assert read["sessions"] == 20
    assert len(read["points"]) == 21
    assert read["start"] == "2026-09-01" and read["end"] == "2026-09-21"
    assert read["points"][0]["value"] == 0
    assert read["value"] == pytest.approx((1.4 / 1.2 - 1) * 100)
    assert read["value"] != pytest.approx(40 - 20)  # not percentage-point subtraction


def test_rebasing_does_not_change_relative_wealth():
    chart = _chart()
    expected = _series(chart)
    chart["bench"] = [v * 7 for v in chart["bench"]]
    chart["baskets"]["group"] = [v * 11 for v in chart["baskets"]["group"]]
    assert _series(chart)["value"] == pytest.approx(expected["value"])


@pytest.mark.parametrize("damage", [
    "short", "missing_end", "missing_middle", "zero_benchmark", "negative_group",
    "string_value", "different_length", "repeated_date", "invalid_date", "reverse_dates",
])
def test_incomplete_or_invalid_window_is_not_backfilled_or_zeroed(damage):
    chart = copy.deepcopy(_chart())
    if damage == "short":
        chart = {**chart, "dates": chart["dates"][1:], "bench": chart["bench"][1:],
                 "baskets": {"group": chart["baskets"]["group"][1:]}}
    elif damage == "missing_end":
        chart["baskets"]["group"][-1] = None
    elif damage == "missing_middle":
        chart["bench"][10] = None
    elif damage == "zero_benchmark":
        chart["bench"][0] = 0
    elif damage == "negative_group":
        chart["baskets"]["group"][10] = -1
    elif damage == "string_value":
        chart["baskets"]["group"][10] = "120"
    elif damage == "different_length":
        chart["bench"].append(130)
    elif damage == "repeated_date":
        chart["dates"][10] = chart["dates"][9]
    elif damage == "invalid_date":
        chart["dates"][10] = "2026-02-30"
    elif damage == "reverse_dates":
        chart["dates"] = list(reversed(chart["dates"]))
    assert _series(chart) is None


def test_unmeasured_subject_is_not_replaced_by_a_different_group():
    assert _series(_chart(), "missing") is None
    assert _series(_chart(), None) is None


@pytest.mark.parametrize("verdict", [None, "unavailable", "__proto__", "constructor"])
def test_missing_breadth_never_becomes_a_mixed_verdict(verdict):
    page = (TPL / "sector_central.html.j2").read_text()
    match = re.search(r"function renderInternals\(\)\{.*?\n\}", page, re.S)
    assert match
    result = _node(
        "const els={}; const document={getElementById:id=>(els[id] ||= {style:{}})};"
        "const THEME={market_concentration:{verdict:" + json.dumps(verdict) + "}};"
        "function isZh(){return false;} function rvxSet(id,value){els[id]=value;}"
        "function rvxBar(){}\n" + match.group() +
        "\nrenderInternals();process.stdout.write(JSON.stringify(els));"
    )
    assert result["mkt-breadth"]["textContent"] == "Not measured"
    assert "unavailable" in result["mkt-breadth-sub"]
    assert "Leadership is narrow" not in result["mkt-breadth-sub"]


def _render(context=None):
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=True)
    env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env.get_template("sector_central.html.j2").render(
        theme_context=context, basket_member_syms=[], action_board=None,
        flows_html=None, bottoming=None, factor_season=None, flow=None,
        source_as_of="2026-09-21", baskets_sha256="b" * 64,
        action_board_sha256="a" * 64,
    )


def test_actual_macro_render_retains_nav_routes_source_identity_and_empty_state():
    html = _render()
    assert '<nav class="site-nav">' in html
    assert '<h1 class="si-page-title">' in html
    assert "/discover?tab=sectors" not in html
    for route in ("overview", "map", "moving", "money", "explore", "confluence"):
        assert f'data-view="{route}" href="#{route}"' in html
    for target in ("tm-mount", "accumulation-section"):
        assert f'href="#{target}"' in html and f'id="{target}"' in html
    assert 'data-si-baskets-sha256="' + "b" * 64 + '"' in html
    assert "Leadership not measured." in html
    assert 'id="si-brief-series" aria-live="polite"' in html
    assert 'data-sync' in html and 'sector_central_data.js' in html


def test_actual_macro_render_uses_source_identity_and_escapes_it():
    name = 'Group <script>alert("x")</script>'
    context = {"leadership": {
        "state": "steady", "strength": [{"id": 'group"unsafe', "name": name, "name_zh": "行业"}],
        "trailing_leader": {"id": "prior", "name": "Prior", "name_zh": "前期"},
        "stance_en": "Watch the leaders", "stance_zh": "观察领涨", "days_in_state": 3,
    }, "state_changes": {}}
    html = _render(context)
    assert "Leadership is holding." in html
    assert 'data-id="group&#34;unsafe"' in html
    assert "<script>alert" not in html
    assert "Group &lt;script&gt;" in html


def _measured_sector_doc():
    ids = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
    return {
        "as_of": "2026-10-16",
        "measured_read": {
            "schema": "leadership_rotation_context.measured_group_read/v1",
            "status": "available",
            "authority": {"tier": "display", "may_rank": False, "may_gate": False,
                          "may_size": False, "may_trade": False},
            "generation": {"cohort_id": "us_sectors_11", "session_end": "2026-10-16",
                           "benchmark": "SPY", "price_basis": "total_return"},
            "cohort": {"horizon": "rs_63d", "window_sessions": 63,
                       "expected_n": 11, "measured_n": 11, "missing": []},
            "groups": [{"group_id": key, "group_kind": "sector",
                        "current": {"status": "measured", "metric": "relative_wealth_pct",
                                    "units": "pct", "rs_63d": i - 5.0}}
                       for i, key in enumerate(ids)],
        },
    }


def _coverage(doc, language="en"):
    """Execute the shipped receipt independently of the basket initializer."""
    src = (TPL / "_sector_central_coverage.js.j2").read_text()
    return _node(
        "const input=" + json.dumps(doc) + "; const before=JSON.stringify(input);"
        "const els={}; const handlers={}; let lang='en';"
        "const document={documentElement:{getAttribute:()=>lang},"
        "getElementById:id=>(els[id] ||= {textContent:'',attrs:{},"
        "setAttribute(k,v){this.attrs[k]=v;}}),"
        "addEventListener:(event,fn)=>{handlers[event]=fn;}};"
        "const window={SECTOR_CENTRAL:input};\n" + src +
        "\nlang=" + json.dumps(language) + "; handlers.langchange();"
        "process.stdout.write(JSON.stringify({"
        "status:els['si-brief-coverage'].attrs['data-status'],"
        "title:els['si-brief-coverage-title'].textContent,"
        "note:els['si-brief-coverage-note'].textContent,"
        "sourceUnchanged:before===JSON.stringify(input)}));"
    )


def test_coverage_receipt_uses_sector_cohort_and_its_own_clock():
    result = _coverage(_measured_sector_doc())
    assert result["status"] == "available"
    assert result["title"] == "11 of 11 sectors have qualified measurements"
    assert "Sector ETFs" in result["note"] and "63-session" in result["note"]
    assert "Evidence date 2026-10-16" in result["note"]
    assert result["sourceUnchanged"]


@pytest.mark.parametrize("measured", [9, 0])
def test_partial_coverage_preserves_unmeasured_sectors_and_measured_zero(measured):
    doc = _measured_sector_doc()
    read = doc["measured_read"]
    read["status"] = "partial"
    read["cohort"]["measured_n"] = measured
    for group in read["groups"][measured:]:
        group["current"] = {"status": "unmeasured", "reason": "thin_history"}
        read["cohort"]["missing"].append(group["group_id"])
    result = _coverage(doc)
    assert result["status"] == "partial"
    assert result["title"].startswith(f"{measured} of 11")
    assert "Unmeasured sectors remain" in result["note"]
    assert result["sourceUnchanged"]


@pytest.mark.parametrize("damage", [
    "count_float", "count_mismatch", "duplicate_group", "basket_identity",
    "wrong_cohort", "wrong_metric", "wrong_horizon", "missing_set",
    "nonfinite_value", "status_mismatch", "authority_escalated", "unknown_status",
])
def test_coverage_does_not_launder_malformed_or_foreign_evidence(damage):
    doc = _measured_sector_doc()
    read = doc["measured_read"]
    if damage == "count_float":
        read["cohort"]["measured_n"] = 10.5
    elif damage == "count_mismatch":
        read["cohort"]["measured_n"] = 10
    elif damage == "duplicate_group":
        read["groups"][-1] = copy.deepcopy(read["groups"][0])
    elif damage == "basket_identity":
        read["groups"][0]["group_kind"] = "basket"
    elif damage == "wrong_cohort":
        read["generation"]["cohort_id"] = "other_11"
    elif damage == "wrong_metric":
        read["groups"][0]["current"]["metric"] = "return_difference_pp"
    elif damage == "wrong_horizon":
        read["cohort"]["horizon"] = "rs_21d"
    elif damage == "missing_set":
        read["cohort"]["missing"] = ["XLK"]
    elif damage == "nonfinite_value":
        read["groups"][0]["current"]["rs_63d"] = float("inf")
    elif damage == "status_mismatch":
        read["status"] = "partial"
    elif damage == "authority_escalated":
        read["authority"]["may_rank"] = True
    elif damage == "unknown_status":
        read["status"] = "ready"
    result = _coverage(doc)
    assert result["status"] == "invalid"
    assert "unavailable" in result["title"]
    assert "11 of 11" not in result["title"]
    assert result["sourceUnchanged"]


@pytest.mark.parametrize("clock, expected", [
    (None, "clock_unavailable"), ("2026-02-30", "clock_unavailable"),
    ("2026-10-17", "clock_mismatch"),
])
def test_coverage_missing_or_incompatible_clock_is_not_current(clock, expected):
    doc = _measured_sector_doc()
    doc["measured_read"]["generation"]["session_end"] = clock
    result = _coverage(doc)
    assert result["status"] == expected
    assert "11 of 11" not in result["title"]


def test_older_sector_evidence_keeps_its_date_and_labels_the_difference():
    doc = _measured_sector_doc()
    doc["as_of"] = "2026-10-19"
    result = _coverage(doc)
    assert result["status"] == "available"
    assert "Evidence date 2026-10-16" in result["note"]
    assert "Older than source page 2026-10-19" in result["note"]


@pytest.mark.parametrize("doc, expected", [
    (None, "missing"),
    ({"measured_read": {"status": "unavailable"}}, "unavailable"),
])
def test_absent_coverage_does_not_become_zero(doc, expected):
    result = _coverage(doc)
    assert result["status"] == expected
    assert "0 of" not in result["title"]


def test_coverage_updates_with_the_existing_language_event():
    result = _coverage(_measured_sector_doc(), "zh")
    assert result["title"] == "11 / 11 个板块具备实测数据"
    assert "证据日期 2026-10-16" in result["note"]
    assert result["sourceUnchanged"]


# The shared context contract serves the actual Macro Sector and Prophet pages.
def _prophet_protocol(expression):
    src = (TPL / "_sector_prophet_context.js.j2").read_text()
    return _node("const document={getElementById:()=>null};\n" + src
                 + "\nprocess.stdout.write(JSON.stringify(" + expression + "));")


@pytest.mark.parametrize("ticker", ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"])
def test_selected_sector_prophet_identity_roundtrip(ticker):
    href = _prophet_protocol("sectorProphetHref(" + json.dumps(
        {"group_kind": "sector", "group_id": ticker}) + ")")
    assert href == f"us_stocks.html?si_sector={ticker}#sector-prophet-context"
    read = _prophet_protocol("sectorProphetSelection(new URL("
                             + json.dumps(href) + ",'https://macro.test/').search)")
    assert read["status"] == "selected" and read["id"] == ticker
    assert read["return_href"] == f"sector_central.html?g={ticker}#map"


@pytest.mark.parametrize("group", [
    None, {}, {"group_kind": "basket", "group_id": "XLK"},
    {"group_kind": "sector", "group_id": "SMH"},
    {"group_kind": "sector", "group_id": "__proto__"},
    {"group_kind": "sector", "group_id": "constructor"},
])
def test_only_canonical_sector_records_can_create_the_handoff(group):
    assert _prophet_protocol("sectorProphetHref(" + json.dumps(group) + ")") is None


@pytest.mark.parametrize("search", [
    "?si_sector=", "?si_sector=xlk", "?si_sector=SMH",
    "?si_sector=XLK&si_sector=XLF", "?si_sector=__proto__",
    "?si_sector=%3Cscript%3E", "?si_sector=constructor",
])
def test_invalid_or_ambiguous_sector_context_is_explicit(search):
    assert _prophet_protocol("sectorProphetSelection(" + json.dumps(search) + ")") == {"status": "invalid"}


def test_context_url_cannot_supply_measurements_dates_or_return_destinations():
    read = _prophet_protocol("sectorProphetSelection('?si_sector=XLK&as_of=2099-01-01&score=100&return_to=https://elsewhere.test')")
    assert set(read) == {"status", "id", "name_en", "name_zh", "return_href"}
    assert read["return_href"] == "sector_central.html?g=XLK#map"


def _prophet_receiver(search, events=None, fragment="#sector-prophet-context", ready=False, apply=True, source_ready=True):
    src = (TPL / "_sector_prophet_context.js.j2").read_text()
    config = json.dumps({"search": search, "events": events or [], "fragment": fragment,
                         "ready": ready, "apply": apply, "sourceReady": source_ready})
    return _node("const cfg=" + config + ";" + r"""
const els={};let lang='en';const dh={},wh={},calls=[];
['sector-prophet-context','si-prophet-subject','si-prophet-note',
 'si-prophet-return','si-prophet-clear','si-prophet-screener'].forEach(id=>{
  els[id]={hidden:true,textContent:'',attrs:{},handlers:{},
    setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){this.handlers[k]=fn;}};
});
const document={getElementById:id=>els[id],documentElement:{getAttribute:()=>lang},
  addEventListener:(name,fn)=>{dh[name]=fn;}};
const board={rows:[{ticker:'A',rank:1,entry:'wait'},{ticker:'B',rank:2,entry:'open'}]};
const before=JSON.stringify(board);
const owner={_selectSector(value){calls.push(value);return cfg.apply;}};
const sourceOwner={set(){throw Error('receiver cannot select a board directly');}};
const window={location:{search:cfg.search,hash:cfg.fragment},
  addEventListener:(name,fn)=>{wh[name]=fn;},USStockTable:cfg.ready?owner:null,
  USProphetSource:cfg.sourceReady?sourceOwner:null,board};
const history={pushState(){throw Error('context cannot write history');},
  replaceState(){throw Error('context cannot write history');}};
function fetch(){throw Error('context cannot request another population');}
""" + src + r"""
function snapshot(){return {hidden:els['sector-prophet-context'].hidden,
  status:els['sector-prophet-context'].attrs['data-status'],
  subject:els['si-prophet-subject'].textContent,note:els['si-prophet-note'].textContent,
  back:els['si-prophet-return'].attrs.href,clear:els['si-prophet-clear'].attrs.href,
  actionHidden:els['si-prophet-screener'].hidden,disabled:els['si-prophet-screener'].disabled};}
const states=[snapshot()];cfg.events.forEach(event=>{
  if(event.search!==undefined)window.location.search=event.search;
  if(event.lang)lang=event.lang;
  if(event.ready!==undefined)window.USStockTable=event.ready?owner:null;
  if(event.sourceReady!==undefined)window.USProphetSource=event.sourceReady?sourceOwner:null;
  if(event.type==='click')els['si-prophet-screener'].handlers.click();
  else if(event.type==='langchange')dh.langchange();else wh[event.type]();
  states.push(snapshot());
});
process.stdout.write(JSON.stringify({states,calls,boardUnchanged:before===JSON.stringify(board)}));
""")


def test_prophet_context_preserves_existing_query_and_native_board_decisions():
    result = _prophet_receiver("?si_sector=XLK&life=ready&tag=a&tag=b")
    state = result["states"][0]
    assert state["subject"] == "Information Technology · XLK"
    assert state["back"] == "sector_central.html?g=XLK#map"
    assert state["clear"] == "us_stocks.html?life=ready&tag=a&tag=b#us-standouts"
    assert result["boardUnchanged"]


def test_context_clear_preserves_an_unrelated_native_fragment():
    result = _prophet_receiver("?si_sector=XLV&life=entered", fragment="#plan-existing")
    assert result["states"][0]["clear"] == "us_stocks.html?life=entered#plan-existing"


def test_context_updates_on_language_back_forward_and_shared_shell_acceptance():
    result = _prophet_receiver("?si_sector=XLK", events=[
        {"type": "langchange", "lang": "zh"},
        {"type": "popstate", "search": "?si_sector=XLE"},
        {"type": "mmx:shell-location", "search": "?life=ready"},
        {"type": "mmx:shell-location", "search": "?si_sector=XLK&si_sector=XLF"},
    ])
    states = result["states"]
    assert states[1]["subject"] == "信息技术 · XLK"
    assert states[2]["subject"] == "能源 · XLE"
    assert states[3]["status"] == "absent" and states[3]["hidden"]
    assert states[4]["status"] == "invalid" and not states[4]["hidden"]
    assert states[4]["back"] == "sector_central.html#map"
    assert result["boardUnchanged"]


def test_canonical_macro_stocks_template_owns_the_context_before_board_bodies():
    page = (TPL / "dashboard.html.j2").read_text()
    guard = '{% if mode == "stocks" %}{% include "_sector_prophet_context.html.j2" %}{% endif %}'
    assert page.count(guard) == 1
    assert page.index(guard) < page.index('id="us-standouts"')
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=True)
    env.globals["t"] = lambda en, zh="": en
    snippet = env.from_string(guard)
    rendered = snippet.render(mode="stocks")
    assert 'id="sector-prophet-context"' in rendered
    assert rendered.index('id="si-prophet-clear"') < rendered.index("function sectorProphetIdentity")
    assert snippet.render(mode="macro") == ""
    sector_html = _render()
    assert sector_html.index("function sectorProphetIdentity") < sector_html.index("/* mr-panel:start */")


def test_screener_handoff_waits_for_owner_and_requires_an_explicit_click():
    result = _prophet_receiver("?si_sector=XLK", events=[
        {"type": "us-screener:availability", "ready": True},
        {"type": "click"},
        {"type": "popstate", "search": "?si_sector=XLV"},
        {"type": "click"},
        {"type": "mmx:shell-location", "search": "?si_sector=XLK&si_sector=XLF"},
        {"type": "click"},
    ])
    assert result["states"][0]["disabled"]
    assert not result["states"][1]["disabled"]
    assert result["calls"] == ["Information Technology", "Health Care"]
    assert result["states"][-1]["actionHidden"]
    assert result["boardUnchanged"]


def test_screener_rejection_retains_the_selected_sector_return():
    result = _prophet_receiver("?si_sector=XLV", ready=True, apply=False,
                               events=[{"type": "click"}])
    assert "Screener is unavailable" in result["states"][-1]["note"]
    assert result["states"][-1]["back"] == "sector_central.html?g=XLV#map"
    assert result["calls"] == ["Health Care"]


def _native_sector_factory():
    """Execute shipped selection and filtering; simulate rendering and DOM."""
    src = (TPL / "stocktable.js").read_text()

    def between(start, end):
        assert src.count(start) == 1
        return src.split(start, 1)[1].split(end, 1)[0]

    unique = "function _uniq(arr)" + between("    function _uniq(arr)", "\n    return {\n      getSectorFilter:")
    fresh = "function _isFresh(row)" + between("  function _isFresh(row)", "\n  }\n") + "\n  }\n"
    filters = "var filters =" + between("    var filters =", "\n\n")
    options = "var sectors  =" + between("      var sectors  =", "      var capBkts")
    predicate = "function applyFilters(rows)" + between("    function applyFilters(rows)", "    function sortRows")
    sorting = "function sortRows(rows)" + between("    function sortRows(rows)", "    function renderRows")
    rendering = "function renderRows()" + between("    function renderRows()", "    function _renderPageBar")
    select = "function _selectDDValue(name, value, focus)" + between(
        "    function _selectDDValue(name, value, focus)", "    // Keyboard navigation inside a menu.")
    api_start = "    return {\n      getSectorFilter:"
    assert src.count(api_start) == 1
    api = api_start + src.split(api_start, 1)[1].split("\n  }\n", 1)[0]
    return r"""
const tables=[];
function makeNativeTable(rows,cfg){
 const original=JSON.stringify(rows);
 let renderCount=0,focusCount=0,counts=null;
 var allRows=rows,sortKey=null,sortDir=null,pageSize=0,shown=Infinity,_keepPage=false,FRESH_DAYS=2;
 var tbody=document.createElement('tbody');
 function orderedCols(){return cfg.columns||[{key:'ticker'}];}
 function _renderPageBar(){renderCount++;}
 function _updateCountChips(all,filtered){counts={loaded:all.length,matched:filtered.length};}
""" + unique + "\n" + fresh + "\n" + filters + "\n" + options + r"""
 const nativeOptions=['all'].concat(sectors).map(value=>({
   value,attrs:{},getAttribute(k){return k==='data-value'?value:this.attrs[k];},
   setAttribute(k,v){this.attrs[k]=v;}
 }));
 const _ddNodes=sectors.length?{sector:{
   menu:{querySelectorAll:()=>nativeOptions},btn:{focus(){focusCount++;}},
   dd:{classList:{add(){},remove(){}}},valSpan:{innerHTML:''}
 }}:{};
 function bi(en){return en;} function esc(v){return v;}
 function _optPair(name,value){return [value,value];}
 function _closeDD(){} function _syncClearBtn(){}
""" + predicate + "\n" + sorting + "\n" + rendering + "\n" + select + r"""
 renderRows();
 tables.push({
  snapshot(){return {sector:filters.sector,options:sectors.slice(),renderCount,focusCount,counts,
    emptyMessage:tbody.children.filter(r=>r.children.some(c=>c.colSpan!==undefined)).map(r=>r.children[0].innerHTML).join(''),
    visible:applyFilters(rows).map(r=>r.ticker),inputUnchanged:original===JSON.stringify(rows),
    selected:nativeOptions.filter(o=>o.attrs['aria-selected']==='true').map(o=>o.value)};},
  manual(value){_selectDDValue('sector',value);},
  otherFilter(name,value){filters[name]=value;}
 });
""" + api + "\n}\n"


def _screener_flow(rows, actions=(), *, wrapper=True, options=None, source_owner=True):
    config = json.dumps({"rows": rows, "actions": list(actions), "wrapper": wrapper,
                         "options": options, "sourceOwner": source_owner})
    page = (TPL / "dashboard.html.j2").read_text()
    marker = "/* W8-R6: USStockTable init"
    assert page.count(marker) == 1
    owner = marker + page.split(marker, 1)[1].split("</script>", 1)[0]
    assert "{%" not in owner and "{{" not in owner
    mode_owner = "function setSrc(mode)" + page.split("  function setSrc(mode)", 1)[1].split(
        "  tog.addEventListener('click'", 1)[0]
    return _node("const cfg=" + config + ";\n" + _native_sector_factory() + r"""
const els={},events=[],storage={},sourceCalls=[];let focused=null,scrolled=null;
function element(id){
 const classes=new Set(),attrs={};
 return {style:{},textContent:'',setAttribute(k,v){attrs[k]=v;},
  getAttribute(k){return attrs[k];},focus(){focused=id;},scrollIntoView(){scrolled=id;},
  classList:{add(k){classes.add(k);},remove(k){classes.delete(k);},contains(k){return classes.has(k);}},
  children:[],addEventListener(){},appendChild(child){
    if(child.kind==='fragment')this.children.push(...child.children);else this.children.push(child);
  },kind:id,_html:'',get innerHTML(){return this._html;},set innerHTML(v){this._html=v;this.children=[];},
  querySelectorAll(){return [];}
 };
}
['us-stocktable-data','us-standouts','st-count-chips','us-st-btn-grid',
 'us-st-btn-table','us-stocktable-wrap','us-src-toggle'].forEach(id=>els[id]=element(id));
els['us-stocktable-data'].textContent=JSON.stringify({rows:cfg.rows});
els['us-standouts'].setAttribute('data-prophet-src','plans');
const document={readyState:'complete',getElementById:id=>els[id]||null,addEventListener(){},
 createElement:tag=>element(tag),createDocumentFragment:()=>element('fragment')};
const localStorage={getItem:k=>storage[k]||null,setItem(k,v){storage[k]=v;}};
const StockTable={_bi:String,_esc:String,_fmtPct:String,_fmtNum:String,
 init(options){return makeNativeTable(JSON.parse(els[options.dataId].textContent).rows,options);}};
const window={StockTable,dispatchEvent(event){events.push(event.type);}};
const panel=els['us-standouts'],tog=els['us-src-toggle'];
function fetch(){throw Error('filter cannot fetch rows');}
""" + mode_owner + r"""
if(cfg.sourceOwner)window.USProphetSource={set(mode){sourceCalls.push(mode);setSrc(mode);}};
let nativeApi;
""" + (owner if wrapper else r"""
nativeApi=makeNativeTable(cfg.rows,cfg.options===null?{}:{sectorOptions:cfg.options});
""") + r"""
function snapshot(){return Object.assign(tables[tables.length-1].snapshot(),{
 view:window.USStockTable?window.USStockTable._getView():null,
 mode:panel.getAttribute('data-prophet-src'),focused,scrolled,sourceCalls:sourceCalls.slice(),
 tableCount:tables.length,dataRows:JSON.parse(els['us-stocktable-data'].textContent).rows
});}
const states=[snapshot()],results=[];
cfg.actions.forEach(action=>{
 if(action.type==='select')results.push(window.USStockTable._selectSector(action.value));
 else if(action.type==='native')results.push(nativeApi.setSectorFilter(action.value));
 else if(action.type==='manual')tables[tables.length-1].manual(action.value);
 else if(action.type==='other')tables[tables.length-1].otherFilter(action.name,action.value);
 else if(action.type==='hydrate')window.USStockTable._mergeRows(action.rows);
 states.push(snapshot());
});
process.stdout.write(JSON.stringify({states,results,events,previous:tables[0].snapshot()}));
""")


@pytest.mark.parametrize("sector", [
    "Materials", "Communication Services", "Energy", "Financials", "Industrials",
    "Information Technology", "Consumer Staples", "Real Estate", "Utilities",
    "Health Care", "Consumer Discretionary",
])
def test_native_screener_handoff_uses_canonical_sector_and_existing_view_owners(sector):
    rows = [{"ticker": "FIRST", "sector": sector, "rank": 2, "entry_status": "wait"},
            {"ticker": "UNKNOWN", "sector": "", "rank": 1, "entry_status": "buy_now"}]
    result = _screener_flow(rows, [{"type": "select", "value": sector}])
    before, after = result["states"]
    assert before["sector"] == "all" and before["sourceCalls"] == []
    assert result["results"] == [True]
    assert after["sector"] == sector and after["visible"] == ["FIRST"]
    assert after["mode"] == "candidates" and after["view"] == "table"
    assert after["focused"] == "us-st-btn-table" and after["scrolled"] == "us-stocktable-wrap"
    assert after["dataRows"] == rows and after["inputUnchanged"]
    assert after["selected"] == [sector] and after["focusCount"] == 0


@pytest.mark.parametrize("value", [None, "", "XLK", "Technology", "__proto__", "constructor", []])
def test_us_adapter_rejects_noncanonical_filter_input_without_navigation(value):
    result = _screener_flow([{"ticker": "A", "sector": "Energy"}],
                            [{"type": "select", "value": value}])
    assert result["results"] == [False]
    assert result["states"][0] == result["states"][1]


def test_zero_row_preview_keeps_registered_sector_selection_through_hydration():
    result = _screener_flow([], [
        {"type": "select", "value": "Materials"},
        {"type": "hydrate", "rows": [{"ticker": "M", "sector": "Materials"},
                                   {"ticker": "E", "sector": "Energy"}]},
    ])
    selected, hydrated = result["states"][1:]
    assert len(selected["options"]) == 11
    assert selected["sector"] == "Materials" and selected["visible"] == []
    assert selected["counts"] == {"loaded": 0, "matched": 0}
    assert "No matching stocks in the loaded table" in selected["emptyMessage"]
    assert hydrated["sector"] == "Materials" and hydrated["visible"] == ["M"]
    assert hydrated["counts"] == {"loaded": 2, "matched": 1} and not hydrated["emptyMessage"]
    assert hydrated["mode"] == "candidates" and hydrated["view"] == "table"
    assert hydrated["focusCount"] == 0
    assert result["events"] == ["us-screener:availability", "us-screener:availability"]


@pytest.mark.parametrize("manual, visible", [("all", ["E", "U", "M"]), ("Materials", ["M"])])
def test_hydration_reads_the_users_actual_filter_including_native_clear(manual, visible):
    result = _screener_flow([{"ticker": "E", "sector": "Energy"}, {"ticker": "U", "sector": ""}], [
        {"type": "select", "value": "Energy"},
        {"type": "manual", "value": manual},
        {"type": "hydrate", "rows": [{"ticker": "M", "sector": "Materials"}]},
    ])
    hydrated = result["states"][-1]
    assert hydrated["sector"] == manual and hydrated["visible"] == visible
    assert hydrated["focusCount"] == 0
    assert result["previous"]["focusCount"] == 1


def test_sector_selection_keeps_other_active_filters_and_source_order():
    result = _screener_flow([{"ticker": "B", "sector": "Energy", "name": "Beta"},
                            {"ticker": "A", "sector": "Energy", "name": "Alpha"}], [
        {"type": "other", "name": "theme", "value": "Alpha"},
        {"type": "select", "value": "Energy"},
    ])
    assert result["states"][-1]["visible"] == ["A"]
    assert result["states"][-1]["dataRows"][0]["ticker"] == "B"


def test_absent_source_owner_cannot_change_filters_or_view():
    result = _screener_flow([{"ticker": "E", "sector": "Energy"}],
                            [{"type": "select", "value": "Energy"}], source_owner=False)
    assert result["results"] == [False]
    assert result["states"][0] == result["states"][1]


def test_non_us_sector_options_and_exact_equality_remain_native():
    result = _screener_flow([{"ticker": "A", "sector": "Technology"},
                            {"ticker": "B", "sector": "Energy"},
                            {"ticker": "U", "sector": ""}], [
        {"type": "native", "value": "Information Technology"},
        {"type": "native", "value": "Technology"},
        {"type": "native", "value": "all"},
    ], wrapper=False)
    assert result["states"][0]["options"] == ["Energy", "Technology"]
    assert result["results"] == [False, True, True]
    assert result["states"][0] == result["states"][1]
    assert result["states"][2]["visible"] == ["A"]
    assert result["states"][3]["visible"] == ["A", "B", "U"]


def test_empty_native_table_accepts_clear_without_inventing_a_dropdown():
    result = _screener_flow([], [{"type": "native", "value": "all"},
                                {"type": "native", "value": "Energy"}], wrapper=False)
    assert result["results"] == [True, False]
    assert all(state["options"] == [] and state["sector"] == "all" for state in result["states"])


def test_screener_action_requires_both_owners_and_refreshes_when_source_arrives():
    result = _prophet_receiver("?si_sector=XLK", ready=True, source_ready=False, events=[
        {"type": "us-screener:availability", "sourceReady": True},
        {"type": "click"},
    ])
    assert result["states"][0]["disabled"]
    assert not result["states"][1]["disabled"]
    assert result["calls"] == ["Information Technology"]
    page = (TPL / "dashboard.html.j2").read_text()
    assert page.count("window.dispatchEvent(new Event('us-screener:availability'))") == 2
