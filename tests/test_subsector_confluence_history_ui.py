from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates" / "subsectors.js"
SITE = ROOT / "site" / "subsectors.js"
BUILDER = ROOT / "scripts" / "build_subsector_confluence.py"
HISTORY = ROOT / "site" / "marketdata" / "subsector_confluence_history.json"


def test_confluence_renderer_mirror_is_exact() -> None:
    assert TPL.read_bytes() == SITE.read_bytes()


def test_signal_and_entry_condition_are_presented_as_orthogonal_reads() -> None:
    js = TPL.read_text(encoding="utf-8")
    assert "Fresh signals — just triggered" in js
    assert "Fresh entry signal" in js
    assert "Entry condition: " in js
    assert "Stretched — wait for pullback" in js
    assert "Freshest cross — but extended, confirm" not in js
    assert "Buy-ready — just turned" not in js

    # Regression guard: payload.forming is a list of keys, never a list of group dicts.
    assert "var formingKeys = payload.forming || [];" in js
    assert "formingKeys.indexOf(g.key) >= 0" in js


def test_history_contract_and_disclosures_are_present() -> None:
    js = TPL.read_text(encoding="utf-8")
    assert "var HISTORY = null;" in js
    assert "subsector_confluence_history.json" in js
    assert "historySection(ds)" in js
    assert "Earlier dates are not reconstructed from today" in js


def test_archival_seed_keeps_both_dimensions_without_inventing_observation_time() -> None:
    payload = json.loads(HISTORY.read_text(encoding="utf-8"))
    assert payload["schema"] == "subsector_confluence.history_projection.v1"
    assert payload["history_start"] == "2026-09-18"
    assert payload["pit_only_since"] is None
    assert "No retrospective recomputation" in payload["methodology"]
    assert payload["accuracy"]["status"] == "accruing"

    day = payload["days"][0]
    recs = day["desks"]["subsectors"]["recommendations"]
    semi = next(r for r in recs if r["key"] == "semiconductors")
    assert semi["entry_tier"] == "T1"
    assert semi["entry_condition"] == "stretched"
    assert semi["regime_state"] == "EXTENDED"


def test_history_append_is_nightly_only_and_china_is_not_recorded() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    assert 'os.environ.get("COLLECT_LANE", "").strip().lower() != "nightly"' in source
    assert '_record_history(site, ("subsectors", subs), ("baskets", baskets))' in source
    assert '_record_history(site, (ns, out))' in source

    china_start = source.index("def main_china()")
    china_end = source.index("def render_china_pages", china_start)
    assert "_record_history(" not in source[china_start:china_end]


# Execute the complete shipped module with controlled asynchronous transports.
# This small DOM port checks rendered claims and first-paint sequencing; real
# browser layout/interaction qualification is kept in the source repair receipt.
import subprocess

import pytest


_UI_HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const errors = [];
process.on('unhandledRejection', e => errors.push(String(e && e.message || e)));
function element(id) {
  return {id, innerHTML:'', textContent:'', listeners:{},
    addEventListener(type, fn) {this.listeners[type]=fn;},
    querySelectorAll() {return [];}, querySelector() {return null;},
    getAttribute(name) {return name==='data-tab' ? id : null;},
    classList:{toggle(){return false;}}, appendChild(){}, focus(){}};
}
const elements = {};
['sc-app','sc-asof','sc-history','tabn-sub','tabn-bas','tabn-ndx','tabn-rut'].forEach(id=>elements[id]=element(id));
const tabs = ['subsectors','baskets','nasdaq','russell'].map(element);
const document = {
  readyState:'complete', documentElement:{getAttribute:()=>input.locale || 'en'},
  getElementById(id) {
    if(id==='sc-history' && !elements['sc-app'].innerHTML.includes('id="sc-history"')) return null;
    return elements[id] || null;
  },
  querySelectorAll(selector) {return selector==='.sc-tab' ? tabs : [];},
  querySelector(){return null;}, createElement:()=>element('created'),
  addEventListener(){}
};
const groups = [{
  key:'semiconductors',label:'Semiconductors',sector:'Technology',class:'entry_now',
  chart_key:'semiconductors',n_members:14,n_priced:14,reliability:'high',
  entry:{tier:'T1',ticks:1,buyable:true},
  regime:{state:input.regime===undefined?'EXTENDED':input.regime,side:input.side || 'avoid',rs_60d:12}
}];
const payload = {
  ok:true,as_of:'2026-09-18',subsectors:groups,baskets:groups,
  coverage:input.coverage || {n_gateable:1,n_subsectors:2},
  double_gated:{double_buy:[]},forming:[],sectors:[]
};
let historyResolve;
const delayedHistory = new Promise(resolve=>historyResolve=resolve);
const requests = [];
function response(value) {return {ok:true,json:()=>Promise.resolve(value)};}
function fetch(url) {
  requests.push(url);
  if(url.includes('subsector_confluence_history')) {
    if(input.reject) return Promise.reject(new Error('controlled history unavailable'));
    return input.delay ? delayedHistory : Promise.resolve(response(input.history));
  }
  if(url.includes('index_leadership') || url.includes('nasdaq_internals')) return Promise.resolve(response(null));
  return Promise.resolve(response(payload));
}
const context = {document,fetch,console,window:{},setTimeout,clearTimeout};
vm.runInNewContext(input.source, context, {timeout:2000,filename:'subsectors.js'});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await tick(); await tick();
  const before=elements['sc-app'].innerHTML;
  const firstRequests=requests.slice();
  if(input.tab) tabs.find(t=>t.id===input.tab).listeners.click({});
  if(input.delay) {historyResolve(response(input.history));await tick();await tick();}
  await tick();
  process.stdout.write(JSON.stringify({
    before,app:elements['sc-app'].innerHTML,history:elements['sc-history'].innerHTML,
    requests,firstRequests,errors
  }));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""


def _run_ui_case(history, **options):
    payload = {"history": history, "source": TPL.read_text(encoding="utf-8"), **options}
    result = subprocess.run(
        ["node", "-e", _UI_HARNESS], input=json.dumps(payload), text=True,
        capture_output=True, timeout=15, check=True,
    )
    return json.loads(result.stdout)


def _history(desk):
    return {"history_start": "2026-09-18", "days": [{"date": "2026-09-18", "desks": {"subsectors": desk}}]}


def _recommendation(**overrides):
    return {"key": "historic-semis", "label": "Historic semis", "entry_tier": "T1",
            "regime_state": "EXTENDED", "regime_side": "avoid", **overrides}


@pytest.mark.parametrize("desk", [None, {}, [], {"recommendations": None}, {"recommendations": [None]}])
def test_repair_missing_history_evidence_is_not_a_zero_signal_day(desk):
    result = _run_ui_case(_history(desk))
    assert result["errors"] == []
    html = result["app"] + result["history"]
    assert "Semiconductors" in html
    assert "Publication record unavailable for this desk." in html
    assert "该栏目当日发布记录不可用。" in html
    assert "No fresh entry signal published." not in html


def test_repair_explicit_recorded_zero_is_preserved():
    result = _run_ui_case(_history({"recommendations": []}))
    assert result["errors"] == []
    assert "No fresh entry signal published." in result["app"] + result["history"]
    assert "Publication record unavailable" not in result["app"] + result["history"]


@pytest.mark.parametrize("history", [
    None, {}, {"days": []}, {"days": "invalid"}, {"days": [None]},
    {"days": [None, {"date": "2026-09-18", "desks": {"subsectors": {"recommendations": [_recommendation(), None]}}}]},
])
def test_repair_malformed_optional_history_cannot_blank_the_current_board(history):
    result = _run_ui_case(history)
    assert result["errors"] == []
    assert "Semiconductors" in result["app"]
    assert "Stock picks" in result["app"]


def test_repair_pending_history_does_not_block_first_paint_or_replace_current_board():
    result = _run_ui_case(_history({"recommendations": [_recommendation()]}), delay=True)
    assert result["errors"] == []
    assert "Semiconductors" in result["before"]
    assert "Stock picks" in result["before"]
    first = result["firstRequests"]
    assert len([url for url in first if "confluence" in url]) == 5
    assert "Historic semis" in result["history"]
    assert result["app"] == result["before"]


def test_repair_rejected_history_keeps_current_board_usable():
    result = _run_ui_case(None, reject=True)
    assert result["errors"] == []
    assert "Semiconductors" in result["app"]


@pytest.mark.parametrize("state", ["", "MYSTERY"])
def test_repair_unknown_condition_does_not_become_clear_enough_to_act(state):
    result = _run_ui_case(None, regime=state, side="buy")
    assert result["errors"] == []
    assert "Entry condition unavailable" in result["app"]
    assert "Clear enough to act" not in result["app"]


def test_repair_history_tier_cannot_inject_markup():
    record = _recommendation(entry_tier='<img src=x onerror="bad()">', label="<Historic semis>")
    result = _run_ui_case(_history({"recommendations": [record]}))
    assert result["errors"] == []
    html = result["app"] + result["history"]
    assert "&lt;Historic semis&gt;" in html
    assert 'onerror=' not in html


@pytest.mark.parametrize("tab,coverage", [
    ("subsectors", {"n_gateable": 1, "n_subsectors": 2}),
    ("baskets", {"n_gateable": 1, "n_listed": 2}),
    ("nasdaq", {"n_gateable": 1, "n_subsectors": 2}),
    ("russell", {"n_gateable": 1, "n_subsectors": 2}),
])
def test_repair_preserves_current_main_coverage_and_four_desk_routing(tab, coverage):
    # The producer keeps fresh signal eligibility separate from regime condition.
    regime = "EXTENDED" if tab in {"subsectors", "nasdaq"} else "BELOW_TREND"
    result = _run_ui_case(None, tab=tab, coverage=coverage, regime=regime)
    assert result["errors"] == []
    assert "Fresh entry signals" in result["app"]
    assert "新入场信号" in result["app"]
    assert '<div class="big">1</div>' in result["app"]
    assert "Buyable now" not in result["app"]
    assert "现可买" not in result["app"]
    assert "现可入场" not in result["app"]
    assert "Entries have the wind at their back" not in result["app"]
    assert '<span class="accent-up">buyable</span>' not in result["app"]
    condition = "Stretched — wait for pullback" if regime == "EXTENDED" else "Below trend — require confirmation"
    assert condition in result["app"]
    assert "undefined" not in result["app"]
    assert "live coverage" not in result["app"]
    expected = {"subsectors": "subsector/semiconductors.html", "baskets": "subsector/b-semiconductors.html",
                "nasdaq": "subsector_nasdaq/semiconductors.html", "russell": "subsector_russell/semiconductors.html"}[tab]
    assert expected in result["app"]
    assert 'of <span class="num">2</span>' in result["app"]
