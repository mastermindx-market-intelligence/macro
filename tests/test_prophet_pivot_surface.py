"""Execute the shipped timing renderer's freshness and non-admission boundary."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "templates" / "_prophet_pivot_checklist.js.j2"


def js(expression: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the shipped renderer")
    code = """
const vm=require('vm'),fs=require('fs');
const context={module:{exports:{}},Number,Date,setTimeout,clearTimeout};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const api=context.module.exports;
const now=Date.parse('2026-11-03T20:45:00Z');
const row={state:'confirmed',live:true,assessed_at:'2026-11-03T20:45:00Z',
  trigger:100,structure_3h:{state:'confirmed',checks:[{id:'h3_reclaim',status:'pass'}]}};
const payload={schema:'prophet.pivot_checklist/v1',input_kind:'OBSERVED_MARKET',
  source_admitted:true,assessed_at:row.assessed_at,valid_until:'2026-11-03T20:51:00Z'};
"""
    return json.loads(subprocess.check_output(
        [node, "-e", code + "\nconsole.log(JSON.stringify(" + expression + "));", str(SOURCE)],
        text=True,
    ))


@pytest.mark.parametrize(("expression", "expected"), [
    ("api.stateOf(row,payload,now)", "confirmed"),
    ("api.stateOf(row,{...payload,valid_until:'2026-11-03T20:44:59Z'},now)", "stale"),
    ("api.stateOf({...row,assessed_at:'2026-11-03T20:46:00Z'},payload,now)", "stale"),
    ("api.stateOf(row,{...payload,valid_until:'2026-11-04'},now)", "stale"),
    ("api.stateOf(row,{...payload,source_admitted:false},now)", "unavailable"),
    ("api.stateOf(row,{...payload,input_kind:'SYNTHETIC_CONFORMANCE'},now)", "unavailable"),
    ("api.stateOf(row,{...payload,schema:'unsupported'},now)", "unavailable"),
    ("api.stateOf({...row,state:'invalidated'},payload,now)", "invalidated"),
    ("api.stateOf({...row,state:'__proto__'},payload,now)", "unavailable"),
])
def test_current_state_requires_qualified_fresh_evidence(expression, expected):
    assert js(expression) == expected


def test_unqualified_values_do_not_paint_passed_checks_or_levels():
    html = js("api.cellHtml('DEMO',row,{...payload,source_admitted:false},now)")
    assert "pvt-check-pass" not in html
    assert ">100.00<" not in html
    assert "Awaiting evidence" in html


def test_parent_unavailable_does_not_erase_qualified_bar_observations():
    html = js("api.cellHtml('DEMO',{...row,state:'unavailable'},payload,now)")
    assert "pvt-check-pass" in html
    assert "Awaiting evidence" in html
    assert "does not approve a trade" in html


def test_escape_untrusted_roster_names_and_keep_stale_evidence_historical():
    html = js("api.cellHtml('<img src=x onerror=alert(1)>',row,{...payload,valid_until:'2026-11-03T20:44:00Z'},now)")
    assert "<img" not in html
    assert "evidence below is historical" in html.lower()
    assert "pvt-state-confirmed" not in html


def test_same_live_client_and_no_extra_transport():
    source = SOURCE.read_text()
    dashboard = (ROOT / "templates" / "dashboard.html.j2").read_text()
    assert "fetch(" not in source
    assert "setInterval(" not in source
    assert "prophet:live-update" in dashboard
    assert "prophet:turn-setups-rendered" in dashboard
    assert '_prophet_pivot_checklist.js.j2' in dashboard
    assert '_prophet_pivot_checklist.css.j2' in dashboard
    assert "syncDialog" in source
    assert "doc.createElement('tr')" not in source


def test_history_is_bounded_ticker_specific_and_causal():
    html = js("""api.cellHtml('DEMO', {...row,pivot_id:'current'}, {...payload,recent_events:[
      {event_id:'a',ticker:'DEMO',state:'testing',at:'2026-11-03T20:30:00Z'},
      {event_id:'b',ticker:'DEMO',state:'invalidated',corrected:true,at:'2026-11-03T20:40:00Z'},
      {event_id:'b',ticker:'DEMO',state:'invalidated',corrected:true,at:'2026-11-03T20:40:00Z'},
      {event_id:'future',ticker:'DEMO',state:'extended',at:'2026-11-03T21:00:00Z'},
      {event_id:'other',ticker:'OTHER',state:'retest_held',at:'2026-11-03T20:35:00Z'}
    ]},now)""")
    assert "Recent observations" in html
    assert html.count("Evidence corrected") == 1
    assert "2026-11-03 21:00:00 UTC" not in html
    assert "Retest held" not in html
    assert html.index("20:40:00 UTC") < html.index("20:30:00 UTC")
