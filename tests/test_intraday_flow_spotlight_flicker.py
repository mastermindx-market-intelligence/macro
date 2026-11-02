"""Intraday scan stability and display contracts.

The duplicate spotlight was deliberately retired in the 2026-11 redesign.
Its obsolete entrance/breathing assertions are replaced with the single-scan
contract, executed render coalescing, truthful source clocks, and ordering.
The classifier and real-payload options tests remain independent and unchanged.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/intraday_flow.html.j2"
SITE = ROOT / "site/intraday_flow.html"
PAGES = pytest.mark.parametrize("path", [TEMPLATE, SITE], ids=["template","site"])
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="Node is required for executed JS contracts")

def region(src, start, end):
    i = src.index(start)
    return src[i:src.index(end,i)]

def run_js(code):
    p = subprocess.run(["node","-e",code],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)

@PAGES
def test_single_scan_retires_the_duplicate_animated_spotlight(path):
    src = path.read_text()
    assert src.count('id="leaders-body"') == 1
    assert 'id="spot-grid"' not in src
    assert "function buildSpotlight" not in src
    assert "function spotCard" not in src
    assert len(re.findall(r'class="stance-card [^"]+" data-stance=',src)) == 6
    assert len(re.findall(r'<button[^>]+data-basket=',src)) == 9
    assert '<details class="ift-theme-menu"' in src
    assert 'aria-pressed="false"' in src

@pytest.mark.parametrize("relative",["templates/intraday-flow.css","site/intraday-flow.css"])
def test_rebuilt_scan_has_no_entrance_or_breathing_animation(relative):
    css = (ROOT/relative).read_text()
    assert ".lead-row" in css
    assert "iftRise" not in css and "iftBreathe" not in css
    assert "prefers-reduced-motion" in css
    for block in re.findall(r'([^{}]+)\{([^{}]+)\}',css):
        if ".lead-row" in block[0]:
            assert "animation:" not in block[1]
    # The future spacing/radius scales have not landed in theme.css; declared
    # canonical fallbacks are essential, otherwise layouts collapse silently.
    for match in re.finditer(r'var\(--(?:sp-\d|r-(?:ctl|btn|card|panel|pill))',css):
        assert css[match.end()] == ","

@PAGES
def test_fetch_success_and_failure_handlers_use_the_coalescer(path):
    src = path.read_text()
    body = region(src,"function fetchQuotes","function updateFlowStamp")
    assert "\n    render();" not in body
    assert body.count("scheduleRender();") == 7  # 4 success + 3 failed source requests
    for name,next_name in [("fetchQuotes","fetchPulse"),("fetchPulse","fetchFlow")]:
        part = region(src,"function "+name,"function "+next_name)
        catch = part[part.index(".catch("):]
        assert "scheduleRender();" in catch  # failed feed status must repaint, too
    sched = region(src,"function scheduleRender","function render()")
    assert "setTimeout" in sched and "requestAnimationFrame" not in sched

@needs_node
@PAGES
def test_async_render_burst_coalesces_and_can_schedule_again(path):
    src=path.read_text()
    schedule=region(src,"var _rendering = false","function render()")
    out=run_js("var timers=[],runs=0;function setTimeout(fn,ms){timers.push({fn,ms});}function render(){runs++;}\n"+schedule+
        "\nscheduleRender();scheduleRender();scheduleRender();var first=timers.length;var delay=timers[0].ms;timers.shift().fn();scheduleRender();var next=timers.length;timers.shift().fn();console.log(JSON.stringify({first,delay,next,runs}));")
    assert out == {"first":1,"delay":50,"next":1,"runs":2}

@needs_node
@PAGES
def test_sort_direction_and_group_order_match_controls(path):
    src=path.read_text()
    sorting=region(src,"var COL_ATTR =","function applyView()")
    code=r"""
var groupByStance=false,sortCol='rvol',sortDir=-1;
function row(tk,volume,order){var attrs={'data-ticker':tk,'data-rvol':String(volume),'data-stance-order':String(order)};
return {getAttribute:function(k){return attrs[k]}};}
function values(rows){return rows.map(function(r){return r.getAttribute('data-ticker')});}
var rows=[row('LOW',0,0),row('HIGH',4.2,1),row('MID',1.1,0)];
"""
    out=run_js(code+sorting+r"""
var descending=values(sortRows(rows.slice()));
sortDir=1;var ascending=values(sortRows(rows.slice()));
groupByStance=true;var grouped=values(sortRows(rows.slice()));
console.log(JSON.stringify({descending,ascending,grouped}));
""")
    assert out["descending"] == ["HIGH","MID","LOW"]
    assert out["ascending"] == ["LOW","MID","HIGH"]
    assert out["grouped"] == ["MID","LOW","HIGH"]

@needs_node
@PAGES
def test_source_clocks_are_separate_and_missing_never_becomes_now(path):
    src=path.read_text()
    helpers=region(src,"function displaySourceTime","// ══ compute-once pipeline")
    out=run_js(r"""
var el={innerHTML:''};var document={getElementById:function(){return el;}};
var BASE_DATA={as_of_display:{en:'31 Oct 12:54am UTC',zh:'10月31日 00:54 UTC'}};
var quotesSourceAsof=null,pulseSourceAsof='2026-07-27T22:32:07Z';
function lz(en,zh){return en;}function esc(s){return String(s);}
"""+helpers+r"""
updateSourceTimes();var absent=el.innerHTML;
quotesSourceAsof='2026-11-02T14:31:00Z';updateSourceTimes();
console.log(JSON.stringify({absent,present:el.innerHTML,invalid:displaySourceTime('bad')}));
""")
    assert "Price source time unavailable" in out["absent"]
    assert "Volume source 2026-07-27 22:32 UTC" in out["absent"]
    assert "Price source 2026-11-02 14:31 UTC" in out["present"]
    assert out["invalid"] == "time unavailable"

@needs_node
@PAGES
@pytest.mark.parametrize("quotes,pulse,stale,phase,expected",[
    ("unavailable","live",False,"live","Current prices are unavailable."),
    ("live","live",True,"live","Confirmation is incomplete."),
    ("live","unavailable",None,"live","Confirmation is incomplete."),
    ("live","live",False,"closed","Review the recorded scan."),
    ("connecting","connecting",None,"live","Checking the latest observations."),
])
def test_summary_qualifies_incomplete_and_off_session_data(path,quotes,pulse,stale,phase,expected):
    src=path.read_text()
    hero=region(src,"function buildHero","function iftSkelDone")
    setup={"quotesStatus":quotes,"pulseStatus":pulse,"pulseSourceStale":stale,"phase":phase}
    code="var cfg="+json.dumps(setup)+r""";
var quotesStatus=cfg.quotesStatus,pulseStatus=cfg.pulseStatus,pulseSourceStale=cfg.pulseSourceStale;
var leaders=[{}],flowAsof=null,flowMeta=null,els={};
var document={getElementById:function(id){return els[id]||(els[id]={innerHTML:'',className:''});}};
function sessionPhase(){return cfg.phase;}
function lz(en,zh){return en+'|'+zh;}
function iftSkelDone(){}function updateFlowStamp(){}function updateSourceTimes(){}
"""
    out=run_js(code+hero+"\nbuildHero([],{});console.log(JSON.stringify(els));")
    assert expected in out["hero-thesis"]["innerHTML"]
    assert "Recorded classifications" in out["ift-record-mode"]["innerHTML"]
    assert "setups live" not in out["hero-thesis"]["innerHTML"]
