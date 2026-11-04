"""Contract tests for the browser-only Government Revenue research briefcase."""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "templates" / "government-revenue-briefcase.js"
SOURCE = MODULE.read_text(encoding="utf-8")
UI_SOURCE = (ROOT / "templates" / "government-revenue-briefcase-ui.js").read_text(encoding="utf-8")
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")


def _run_node(tmp_path: Path, body: str, initial_state: str | None = None) -> dict:
    """Evaluate the production module inside a tiny browser/localStorage stub."""
    script = textwrap.dedent(
        """
        const fs = require('fs');
        const source = fs.readFileSync(%(module)s, 'utf8');
        const values = {};
        %(initial_state)s
        const localStorage = {
          getItem: (key) => Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null,
          setItem: (key, value) => { values[key] = String(value); },
          removeItem: (key) => { delete values[key]; }
        };
        const window = { localStorage: localStorage };
        global.window = window;
        eval(source);
        const clock = () => '2026-08-02T12:00:00Z';
        const make = () => window.createGovernmentRevenueBriefcase({storage: localStorage, now: clock, ownerId: 'test-user', membershipMode: 'legacy'});
        %(body)s
        """
    ) % {
        "module": json.dumps(str(MODULE)),
        "initial_state": (
            "values['mastermind.government_revenue.briefcase.v1.user.test-user'] = " + json.dumps(initial_state) + ";"
            if initial_state is not None else ""
        ),
        "body": body,
    }
    path = tmp_path / "briefcase_runtime.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"node failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    assert result.stdout.strip(), f"node emitted no result; stderr:\n{result.stderr}"
    return json.loads(result.stdout)


def _workspace(*events: dict, award_status: str = "ok", bundle: str = "grw2-aaaaaaaaaaaaaaaaaaaaaaaa") -> dict:
    return {
        "schema_version": "government_procurement_workspace.v2",
        "event_contract": "government_procurement_event.v2",
        "bundle_id": bundle,
        "as_of": "2026-08-02",
        "known_at": "2026-08-02T09:00:00Z",
        "generated_at": "2026-08-02T09:01:00Z",
        "authority": {
            "tier": "display", "context_only": True, "can_rank": False, "can_size": False,
            "can_gate": False, "can_originate_signal": False, "can_add_candidates": False,
            "can_escalate": False,
        },
        "freshness": {"status": "ok", "award_events": {"status": award_status}},
        "coverage": {"events_visible": len(events), "event_cap": 500, "facet_scope": "visible bounded workspace events"},
        "limitations": ["Bounded governed workspace cut."],
        "events": list(events),
    }


def _event(event_id: str, kind: str, *, title: str = "Visible governed record", ticker: str = "LMT") -> dict:
    return {
        "contract": "government_procurement_event.v2",
        "event_id": event_id,
        "record_id": "record:" + event_id,
        "version": 1,
        "kind": kind,
        "state": "watch" if kind == "recompete" else "updated",
        "title_original": title,
        "title_zh": None,
        "translation_status": "original",
        "agency": {"department_name": "Department of Defense", "private": "must-not-export"},
        "change": {"type": "recompete_watch_entered", "known_at": "2026-08-02T09:00:00Z"},
        "opportunity": None,
        "recompete": {"case_type": "derived_expiry_watch"} if kind == "recompete" else None,
        "award_change": {"event_type": "obligation", "award_key": "A-1"} if kind == "award_change" else None,
        "dates": [{"id": "current_end_date", "value": "2027-01-01", "private": "never"}],
        "amounts": [{"id": "obligation", "value": 1_000_000, "currency": "USD", "private": "never"}],
        "primary_date_id": "current_end_date",
        "primary_amount_id": "obligation",
        "listed_company_impacts": [{"ticker": ticker, "company_name": "Example Co.", "private": "never"}],
        "primary_ticker": ticker,
        "display_priority": {"score": 75, "is_investment_rank": False, "private": "never"},
        "evidence": {
            "source_class": "official_fact",
            "mapping_class": "deterministic_inference" if kind == "recompete" else "official",
            "receipts": [{"publisher": "USAspending", "record_id": "receipt-1", "url": "https://api.usaspending.gov/award/A-1", "private": "secret"}],
            "derivations": [], "conflicts": [], "limitations": ["Visible public receipt only."],
            "private_raw_receipt": "must-not-export",
        },
        "authority": {
            "tier": "display", "context_only": True, "can_rank": False, "can_size": False,
            "can_gate": False, "can_originate_signal": False, "can_add_candidates": False,
            "can_escalate": False, "private": "must-not-export",
        },
        "private_raw_payload": "must-not-export",
    }


def test_module_is_a_hermetic_browser_seam() -> None:
    assert "createGovernmentRevenueBriefcase" in SOURCE
    assert "government_procurement_local_state.v1" in SOURCE
    assert "government_procurement_export.v1" in SOURCE
    for forbidden in (
        "fetch(", "XMLHttpRequest", "Notification(", "setInterval(", "setTimeout(",
        "navigator.serviceWorker", "supabase", "MDXAuth",
    ):
        assert forbidden not in SOURCE

    assert "mountGovernmentRevenueBriefcaseUI" in UI_SOURCE
    assert "checked only when you open or refresh this page" in UI_SOURCE
    assert "first complete-workspace check establishes a baseline" in UI_SOURCE
    for forbidden in (
        "fetch(", "XMLHttpRequest", "Notification(", "setInterval(", "setTimeout(",
        "navigator.serviceWorker", "supabase", "MDXAuth",
    ):
        assert forbidden not in UI_SOURCE


@needs_node
def test_saved_view_crud_round_trips_exact_filter_contract_and_cascades_alerts(tmp_path: Path) -> None:
    out = _run_node(
        tmp_path,
        """
        const first = make();
        const created = first.createView({name:'  Defense tape  ', filters:{
          mode:'awards', truth:'linked', q:'  radar ', agency:'DoD', ticker:'lmt', ignored:'nope'
        }}).view;
        const changed = first.updateView(created.id, {name:'Revised', filters:{mode:'recompetes', truth:'defense', ticker:'bad/ticker'}}).view;
        const alert = first.createAlert({view_id:changed.id, type:'recompete'}).alert;
        const reloaded = make();
        const afterReload = reloaded.state();
        const deleted = reloaded.deleteView(changed.id);
        process.stdout.write(JSON.stringify({created, changed, alert, afterReload, deleted, afterDelete:reloaded.state()}));
        """,
    )

    assert out["created"]["name"] == "Defense tape"
    assert out["created"]["filters"] == {
        "mode": "awards", "truth": "linked", "q": "radar", "agency": "DoD", "ticker": "LMT"
    }
    assert out["changed"]["filters"] == {
        "mode": "recompetes", "truth": "defense", "q": "", "agency": "", "ticker": ""
    }
    assert out["afterReload"]["contract"] == "government_procurement_local_state.v1"
    assert len(out["afterReload"]["alerts"]) == 1
    assert out["deleted"]["deleted"] is True
    assert out["afterDelete"]["saved_views"] == []
    assert out["afterDelete"]["alerts"] == []
    assert out["afterDelete"]["inbox"] == []


@needs_node
def test_typed_alerts_baseline_then_reconcile_only_when_governed_workspace_is_ready(tmp_path: Path) -> None:
    opportunity_one = _event("govws-opp-1", "opportunity")
    opportunity_two = _event("govws-opp-2", "opportunity")
    award_one = _event("govws-awd-1", "award_change")
    award_two = _event("govws-awd-2", "award_change")
    recompete_one = _event("govws-rec-1", "recompete")
    recompete_two = _event("govws-rec-2", "recompete")
    workspace_one = _workspace(opportunity_one, award_one, recompete_one, award_status="unavailable")
    workspace_two = _workspace(opportunity_one, opportunity_two, award_one, award_two, recompete_one, recompete_two)

    out = _run_node(
        tmp_path,
        """
        const app = make();
        const view = app.createView({name:'All governed changes', filters:{mode:'changes', truth:'all'}}).view;
        const opportunity = app.createAlert({view_id:view.id, type:'opportunity'}).alert;
        const award = app.createAlert({view_id:view.id, type:'award_change'}).alert;
        const recompete = app.createAlert({view_id:view.id, type:'recompete'}).alert;
        const notReady = app.reconcile(WORKSPACE_ONE, {complete:false, bundle_matched:true});
        const first = app.reconcile(WORKSPACE_ONE, {complete:true, bundle_matched:true});
        const afterFirst = app.state();
        const second = app.reconcile(WORKSPACE_TWO, {complete:true, bundle_matched:true});
        process.stdout.write(JSON.stringify({notReady, first, afterFirst, second, inbox:app.listInbox()}));
        """.replace("WORKSPACE_ONE", json.dumps(workspace_one)).replace("WORKSPACE_TWO", json.dumps(workspace_two)),
    )

    assert out["notReady"]["reconciled"] is False
    assert out["notReady"]["reason"] == "workspace_not_ready"
    assert out["first"]["alerts"] == []
    assert len(out["first"]["withheld_alert_ids"]) == 1
    # Opportunity/recompete have a safe first-seen baseline; an unavailable award rail does not.
    state_by_type = {item["type"]: item for item in out["afterFirst"]["alerts"]}
    assert state_by_type["opportunity"]["primed"] is True
    assert state_by_type["recompete"]["primed"] is True
    assert state_by_type["award_change"]["primed"] is False
    # The award type becomes healthy only after its first baseline, so it cannot backfill a fake alert.
    assert {item["type"] for item in out["second"]["alerts"]} == {"opportunity", "recompete"}
    assert any(item["type"] == "recompete" and "not an official recompete date" in item["warning"] for item in out["inbox"])


@needs_node
def test_export_is_governed_allowlisted_and_csv_neutralizes_formula_text(tmp_path: Path) -> None:
    malicious = _event("govws-opp-export", "opportunity", title="=HYPERLINK(\"https://evil.example\")")
    workspace = _workspace(malicious)
    out = _run_node(
        tmp_path,
        """
        const app = make();
        const jsonExport = app.buildJsonExport(WORKSPACE, {mode:'changes', truth:'all', q:'', agency:'', ticker:''});
        const csvExport = app.buildCsvExport(WORKSPACE, {mode:'changes', truth:'all'});
        process.stdout.write(JSON.stringify({jsonExport, csvExport}));
        """.replace("WORKSPACE", json.dumps(workspace)),
    )

    payload = out["jsonExport"]
    serialized = json.dumps(payload)
    assert payload["contract"] == "government_procurement_export.v1"
    assert payload["workspace"]["bundle_id"].startswith("grw2-")
    assert payload["workspace"]["event_contract"] == "government_procurement_event.v2"
    assert payload["query"]["result_scope"] == "current visible governed workspace cut"
    assert payload["records"][0]["event_id"] == "govws-opp-export"
    assert "must-not-export" not in serialized
    assert "private_raw_payload" not in serialized
    assert "private_raw_receipt" not in serialized
    assert out["csvExport"]["contract"] == "government_procurement_export.v1"
    assert out["csvExport"]["media_type"] == "text/csv;charset=utf-8"
    assert "\"'=HYPERLINK(" in out["csvExport"]["content"]
    assert "must-not-export" not in out["csvExport"]["content"]


@needs_node
def test_csv_neutralizes_formula_after_leading_whitespace_or_control_bytes(tmp_path: Path) -> None:
    malicious = _event(
        "govws-opp-export-whitespace",
        "opportunity",
        title="\t\r\n\x01 =HYPERLINK(\"https://evil.example\")",
    )
    workspace = _workspace(malicious)
    out = _run_node(
        tmp_path,
        """
        const app = make();
        const csvExport = app.buildCsvExport(WORKSPACE, {mode:'changes', truth:'all'});
        process.stdout.write(JSON.stringify(csvExport));
        """.replace("WORKSPACE", json.dumps(workspace)),
    )

    # The apostrophe is deliberately before the original bytes: Excel/Sheets see
    # text, while the whitespace/control prefix remains represented in the export.
    assert "'\t\r\n\x01 =HYPERLINK(" in out["content"]


@needs_node
def test_malformed_local_storage_fails_closed_to_empty_state(tmp_path: Path) -> None:
    out = _run_node(
        tmp_path,
        """
        const app = make();
        process.stdout.write(JSON.stringify(app.state()));
        """,
        initial_state='{"contract":"wrong","saved_views":[{"id":"x"}]}',
    )
    assert out == {"contract": "government_procurement_local_state.v1", "saved_views": [], "alerts": [], "inbox": []}


@needs_node
def test_ui_mount_wires_saved_view_and_first_local_baseline(tmp_path: Path) -> None:
    workspace = _workspace(_event("govws-opp-ui", "opportunity"))
    script = textwrap.dedent(
        """
        const fs=require('fs'),values={},listeners={},nodes={};
        function node(id){if(!nodes[id])nodes[id]={id:id,value:id==='alertType'?'opportunity':'',innerHTML:'',textContent:'',className:'',disabled:false,
          addEventListener:function(k,f){listeners[id+':'+k]=f},fire:function(k,e){if(listeners[id+':'+k])listeners[id+':'+k](e||{key:'',preventDefault:function(){}})},focus:function(){}};return nodes[id]}
        const localStorage={getItem:k=>Object.prototype.hasOwnProperty.call(values,k)?values[k]:null,setItem:(k,v)=>{values[k]=String(v)}};
        const document={activeElement:null,getElementById:node,body:{appendChild:function(){}},createElement:function(){return{click:function(){},remove:function(){}}}};
        const window={localStorage:localStorage,document:document};global.window=window;
        eval(fs.readFileSync(%(core)s,'utf8'));eval(fs.readFileSync(%(ui)s,'utf8'));
        var filters={mode:'opportunities',truth:'defense',q:'radar',agency:'Department of Defense',ticker:'LMT'},applied=null,ready=true;
        function esc(x){return String(x==null?'':x).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
        var app=window.mountGovernmentRevenueBriefcaseUI({get:node,tr:function(x){return x},esc:esc,text:function(x,fb){return x==null||x===''?(fb||''):String(x)},
          onOwnerChange:function(callback){callback('test-user')},getFilters:function(){return filters},applyFilters:function(value){applied=value},getMatchingEventIds:function(){return []},getVisibleEventIds:function(){return []},getSelectedEventId:function(){return null},getWorkspace:function(){return %(workspace)s},isWorkspaceReady:function(){return ready},openDrawer:function(){}});
        app.bind();node('savedViewName').value='Defense radar';node('saveView').fire('click');
        filters={mode:'changes',truth:'all',q:'',agency:'',ticker:''};node('savedViewSelect').fire('change');
        node('toggleLocalAlert').fire('click');
        var state=JSON.parse(values['mastermind.government_revenue.briefcase.v1.user.test-user']);
        process.stdout.write(JSON.stringify({available:app.available,applied:applied,state:state,status:node('briefcaseStatus').textContent,toggle:node('toggleLocalAlert').textContent}));
        """
    ) % {
        "core": json.dumps(str(MODULE)),
        "ui": json.dumps(str(ROOT / "templates" / "government-revenue-briefcase-ui.js")),
        "workspace": json.dumps(workspace),
    }
    path = tmp_path / "briefcase_ui_mount.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["available"] is True
    assert out["applied"] == {
        "mode": "opportunities", "truth": "defense", "q": "radar",
        "agency": "Department of Defense", "ticker": "LMT",
    }
    assert len(out["state"]["saved_views"]) == 1
    assert out["state"]["alerts"][0]["type"] == "opportunity"
    assert out["state"]["alerts"][0]["primed"] is True
    assert out["state"]["inbox"] == []
    assert "baseline checked" in out["status"]
    assert out["toggle"] == "Disable local alert"


@needs_node
def test_no_local_private_state_reads_before_subject_and_no_legacy_adoption(tmp_path: Path) -> None:
    out = _run_node(tmp_path, """
        const reads=[];
        const scopedStorage={getItem:key=>{reads.push(key);return values[key]||null},setItem:(key,value)=>{values[key]=value}};
        const legacy='mastermind.government_revenue.briefcase.v1';
        values[legacy]=JSON.stringify({contract:'government_procurement_local_state.v1',saved_views:[{id:'old',name:'Unassigned secret',filters:{}}],alerts:[],inbox:[]});
        const anonymous=window.createGovernmentRevenueBriefcase({storage:scopedStorage});
        const anon=anonymous.createView({name:'Ephemeral',filters:{}});
        const a=window.createGovernmentRevenueBriefcase({storage:scopedStorage,ownerId:'user-a'});
        a.createView({name:'A private',filters:{ticker:'LMT'}});
        const b=window.createGovernmentRevenueBriefcase({storage:scopedStorage,ownerId:'user-b'});
        const back=window.createGovernmentRevenueBriefcase({storage:scopedStorage,ownerId:'user-a'});
        process.stdout.write(JSON.stringify({anonPersisted:anon.persisted,reads,a:back.listViews(),b:b.listViews(),legacy:values[legacy]}));
    """)
    assert out['anonPersisted'] is False
    assert out['reads'] == ['mastermind.government_revenue.briefcase.v1.user.user-a', 'mastermind.government_revenue.briefcase.v1.user.user-b', 'mastermind.government_revenue.briefcase.v1.user.user-a']
    assert out['a'][0]['name'] == 'A private'
    assert out['b'] == []
    assert 'Unassigned secret' in out['legacy']


@needs_node
def test_ui_waits_for_subject_and_purges_private_options_on_logout(tmp_path: Path) -> None:
    script = r"""
    const fs=require('fs'),values={},reads=[],nodes={};
    function node(id){return nodes[id]||(nodes[id]={value:'',innerHTML:'',textContent:'',disabled:false,addEventListener(){},focus(){}})}
    const storage={getItem:k=>(reads.push(k),values[k]||null),setItem:(k,v)=>values[k]=v};
    global.window={localStorage:storage};
    eval(fs.readFileSync(CORE,'utf8'));eval(fs.readFileSync(UI,'utf8'));
    let callback,clears=0;
    const controlIds=['savedViewSelect','savedViewName','saveView','deleteView','alertType','toggleLocalAlert','localInbox','exportViewJson','exportViewCsv'];
    const controls=()=>Object.fromEntries(controlIds.map(id=>[id,node(id).disabled]));
    window.createGovernmentRevenueBriefcase({storage:storage,ownerId:'user-a'}).createView({name:'A private',filters:{}});
    window.createGovernmentRevenueBriefcase({storage:storage,ownerId:'user-b'}).createView({name:'B private',filters:{}});
    reads.length=0;
    const api=window.mountGovernmentRevenueBriefcaseUI({get:node,tr:x=>x,esc:String,text:(x,d='')=>x==null?d:String(x),onOwnerChange:cb=>callback=cb,clearPrivatePresentation:()=>clears++,getFilters:()=>({}),isWorkspaceReady:()=>false});
    api.bind();const initial={reads:reads.slice(),available:api.available,controls:controls()};
    callback('user-a');const a=node('savedViewSelect').innerHTML,aControls=controls();
    callback('user-b');const b=node('savedViewSelect').innerHTML;
    callback('');const signedOut={available:api.available,html:node('savedViewSelect').innerHTML,name:node('savedViewName').value,count:node('localInboxCount').textContent,controls:controls()};
    callback('user-b');const resumedB={html:node('savedViewSelect').innerHTML,controls:controls()};
    callback('user-a');const resumedA={html:node('savedViewSelect').innerHTML,controls:controls()};
    process.stdout.write(JSON.stringify({initial,a,b,aControls,signedOut,resumedB,resumedA,clears}));
    """.replace('CORE', json.dumps(str(MODULE))).replace('fs.readFileSync(UI,', 'fs.readFileSync(' + json.dumps(str(ROOT/'templates/government-revenue-briefcase-ui.js')) + ',')
    path=tmp_path/'tenant_ui.js';path.write_text(script)
    result=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr
    out=json.loads(result.stdout)
    assert out['initial']['reads'] == []
    assert out['initial']['available'] is False
    assert all(out['initial']['controls'].values()), out['initial']['controls']
    assert 'A private' in out['a'] and 'B private' not in out['a']
    assert 'B private' in out['b'] and 'A private' not in out['b']
    assert {k:v for k,v in out['signedOut'].items() if k != 'controls'} == {'available':False,'html':'','name':'','count':'0'}
    assert all(out['signedOut']['controls'].values()), out['signedOut']['controls']
    enabled={'savedViewSelect','savedViewName','saveView','alertType','localInbox','exportViewJson','exportViewCsv'}
    for snapshot in (out['aControls'], out['resumedB']['controls'], out['resumedA']['controls']):
        assert all(snapshot[key] is False for key in enabled), snapshot
        # Alert toggling/deletion still require an explicitly selected saved view.
        assert snapshot['deleteView'] is True and snapshot['toggleLocalAlert'] is True
    assert 'B private' in out['resumedB']['html'] and 'A private' not in out['resumedB']['html']
    assert 'A private' in out['resumedA']['html'] and 'B private' not in out['resumedA']['html']
    assert out['clears'] == 5



@needs_node
def test_exports_do_not_substitute_change_feed_for_known_unimplemented_page_modes(tmp_path: Path) -> None:
    workspace = _workspace(_event('govws-export-mode-award', 'award_change'))
    out = _run_node(tmp_path, r'''
        const app = make();
        const WORKSPACE = %s;
        const refused = [];
        for (const mode of ['candidates', 'budget', 'programs', 'fms', ' CANDIDATES ', 'FMS']) {
          for (const method of ['buildJsonExport', 'buildCsvExport']) {
            try { app[method](WORKSPACE, {mode}); refused.push({mode, method, code:null}); }
            catch (error) { refused.push({mode, method, code:error.code}); }
          }
        }
        const preserved = [];
        for (const mode of ['changes', 'awards', 'opportunities', 'recompetes', 'companies', 'AWARDS', ' awards ', '', undefined, 'unknown-old-mode']) {
          const json = app.buildJsonExport(WORKSPACE, {mode});
          const csv = app.buildCsvExport(WORKSPACE, {mode});
          preserved.push({input:mode || '', mode:json.query.filters.mode, count:json.records.length, csv:csv.content});
        }
        console.log(JSON.stringify({refused, preserved}));
    ''' % json.dumps(workspace))
    assert len(out['refused']) == 12
    assert all(row['code'] == 'unsupported_export_mode' for row in out['refused'])
    assert [row['mode'] for row in out['preserved']] == [
        'changes', 'awards', 'opportunities', 'recompetes', 'companies',
        'awards', 'awards', 'changes', 'changes', 'changes',
    ]
    assert [row['count'] for row in out['preserved']] == [1, 1, 0, 0, 0, 1, 1, 1, 1, 1]
    assert all('export_contract' in row['csv'] for row in out['preserved'])


@needs_node
@pytest.mark.parametrize("value", [0, -402073.0, 110000000.0])
def test_export_retains_primary_amount_basis_clocks_and_source(tmp_path: Path, value: float) -> None:
    import csv
    import io
    event = _event("govws-amount-basis", "award_change")
    event["primary_amount_id"] = "federal_action_obligation"
    amount = {"id": "federal_action_obligation", "value": value, "currency": "USD", "semantic": "official", "label_code": "federal_action_obligation", "known_at": "2026-08-02T09:00:00Z", "as_of": "2026-07-13T00:00:00Z", "source_ref": "https://api.usaspending.gov/api/v2/transactions/", "is_lower_bound": False, "private": "must-not-export"}
    event["amounts"] = [{"id": "ceiling", "value": 999999999, "currency": "USD"}, amount]
    out = _run_node(tmp_path, "const app=make(); const workspace=" + json.dumps(_workspace(event)) + "; process.stdout.write(JSON.stringify({json:app.buildJsonExport(workspace,{mode:'changes'}),csv:app.buildCsvExport(workspace,{mode:'changes'})}));")
    row = list(csv.DictReader(io.StringIO(out["csv"]["content"])))[0]
    assert float(row["primary_amount"]) == value
    for key in ["id", "currency", "semantic", "label_code", "known_at", "as_of", "source_ref"]:
        assert row["primary_amount_" + key] == amount[key]
    assert row["primary_amount_is_lower_bound"] == "false"
    assert out["json"]["records"][0]["amounts"][1]["as_of"] == amount["as_of"]
    assert "must-not-export" not in json.dumps(out)


@needs_node
def test_export_never_borrows_unselected_amount_metadata(tmp_path: Path) -> None:
    import csv
    import io
    event = _event("govws-missing-amount", "award_change")
    event["primary_amount_id"] = "absent"
    event["amounts"][0].update({"as_of": {"private": "must-not-export"}, "source_ref": "javascript:alert(1)"})
    out = _run_node(tmp_path, "const app=make(); const workspace=" + json.dumps(_workspace(event)) + "; process.stdout.write(JSON.stringify({json:app.buildJsonExport(workspace,{mode:'changes'}),csv:app.buildCsvExport(workspace,{mode:'changes'})}));")
    row = list(csv.DictReader(io.StringIO(out["csv"]["content"])))[0]
    assert row["primary_amount"] == ""
    assert all(row["primary_amount_"+key] == "" for key in ["id", "currency", "semantic", "label_code", "known_at", "as_of", "source_ref", "is_lower_bound"])
    assert "must-not-export" not in json.dumps(out)
    assert "javascript:" not in json.dumps(out)


@needs_node
@pytest.mark.parametrize("value", ["110000000.00", None, True])
def test_csv_omits_basis_when_primary_value_is_not_numeric(tmp_path: Path, value) -> None:
    import csv
    import io
    event=_event("govws-nonnumeric-amount","award_change")
    event["amounts"][0].update({"value":value,"as_of":"2026-07-13T00:00:00Z","known_at":"2026-08-02T09:00:00Z","is_lower_bound":True})
    out=_run_node(tmp_path,"const app=make(); const workspace="+json.dumps(_workspace(event))+"; process.stdout.write(JSON.stringify({json:app.buildJsonExport(workspace,{mode:'changes'}),csv:app.buildCsvExport(workspace,{mode:'changes'})}));")
    row=list(csv.DictReader(io.StringIO(out["csv"]["content"])))[0]
    assert row["primary_amount"] == ""
    assert all(row["primary_amount_"+key] == "" for key in ["id","currency","semantic","label_code","known_at","as_of","source_ref","is_lower_bound"])
    assert out["json"]["records"][0]["amounts"][0]["value"] == value


@needs_node
@pytest.mark.parametrize("as_of,expected", [("2026-07-13T00:00:00Z","2026-07-13"),(None,"undated"),("unavailable","undated")])
def test_csv_filename_retains_day_or_undated(tmp_path: Path, as_of: str | None, expected: str) -> None:
    workspace=_workspace(_event("govws-filename","award_change"))
    workspace["as_of"]=as_of
    out=_run_node(tmp_path,"const app=make(); process.stdout.write(JSON.stringify(app.buildCsvExport("+json.dumps(workspace)+",{mode:'changes'}))); ")
    assert out["filename"].startswith("government-revenue-"+expected+"-")


@needs_node
def test_local_correction_receipt_keeps_native_event_revision_and_does_not_repeat(tmp_path: Path) -> None:
    original = _event("govws-original", "award_change")
    corrected = _event("govws-corrected", "award_change")
    corrected.update(record_id=original["record_id"], version=2)
    corrected["change"].update(is_correction=True, type="action_corrected", known_at="2026-08-02T10:00:00Z")
    new = _event("govws-new", "award_change")
    out = _run_node(tmp_path, """
      const app=make();
      const view=app.createView({name:'Defense monitor',filters:{mode:'changes',ticker:'LMT'}}).view;
      app.createAlert({view_id:view.id,type:'award_change'});
      app.reconcile(BASE,{complete:true,bundle_matched:true});
      const corrected=app.reconcile(NEXT,{complete:true,bundle_matched:true});
      const repeated=app.reconcile(NEXT,{complete:true,bundle_matched:true});
      const restored=make();
      process.stdout.write(JSON.stringify({corrected,repeated,inbox:restored.listInbox()}));
    """.replace("BASE", json.dumps(_workspace(original))).replace("NEXT", json.dumps(_workspace(original, corrected, new))))
    receipts = {row["event_id"]: row for row in out["corrected"]["alerts"]}
    correction = receipts["govws-corrected"]
    assert correction["notification_kind"] == "correction"
    assert correction["event_contract"] == "government_procurement_event.v2"
    assert correction["record_id"] == original["record_id"]
    assert correction["event_version"] == 2
    assert "correct" in correction["message"].lower()
    assert receipts["govws-new"]["notification_kind"] == "new_observation"
    assert out["repeated"]["alerts"] == []
    restored = {row["event_id"]: row for row in out["inbox"]}
    assert restored["govws-corrected"] == correction


@needs_node
def test_local_alert_inbox_distinguishes_correction_new_and_unclassified_history_in_both_languages(tmp_path: Path) -> None:
    original = _event("govws-old", "award_change")
    correction = _event("govws-fix", "award_change")
    correction["change"]["is_correction"] = True
    script = r"""
      const fs=require('fs'),values={},nodes={},listeners={};
      const storage={getItem:k=>values[k]||null,setItem:(k,v)=>{values[k]=String(v)}};
      const document={activeElement:null};global.window={localStorage:storage,document};
      eval(fs.readFileSync(CORE,'utf8'));
      const stateOwner=window.createGovernmentRevenueBriefcase({storage,ownerId:'test-user',membershipMode:'legacy'});
      const v=stateOwner.createView({name:'Defense',filters:{mode:'changes'}}).view;
      const a=stateOwner.createAlert({view_id:v.id,type:'award_change'}).alert;
      stateOwner.reconcile(BASE,{complete:true,bundle_matched:true});
      stateOwner.reconcile(NEXT,{complete:true,bundle_matched:true});
      const key='mastermind.government_revenue.briefcase.v1.user.test-user';
      const state=JSON.parse(values[key]);
      state.inbox.push({id:'legacy-alert',alert_id:a.id,view_id:v.id,event_id:'legacy',type:'award_change',kind:'award_change',message:'Old stored prose'});
      values[key]=JSON.stringify(state);
      function node(id){return nodes[id]||(nodes[id]={value:'',innerHTML:'',textContent:'',disabled:false,className:'',addEventListener:(kind,fn)=>listeners[id+':'+kind]=fn,focus(){}})}
      function esc(x){return String(x||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
      eval(fs.readFileSync(UI,'utf8'));let lang='en',drawer;
      window.mountGovernmentRevenueBriefcaseUI({get:node,tr:(en,zh)=>lang==='zh'?zh:en,esc,text:x=>String(x||''),onOwnerChange:cb=>cb('test-user'),openDrawer:value=>drawer=value});
      listeners['localInbox:click']();const en=drawer.html;
      lang='zh';listeners['localInbox:click']();
      const restored=window.createGovernmentRevenueBriefcase({storage,ownerId:'test-user'}).listInbox();
      process.stdout.write(JSON.stringify({en,zh:drawer.html,legacy:restored.find(x=>x.event_id==='legacy')}));
    """.replace("CORE", json.dumps(str(MODULE))).replace("fs.readFileSync(UI,", "fs.readFileSync(" + json.dumps(str(ROOT / "templates/government-revenue-briefcase-ui.js")) + ",").replace("BASE", json.dumps(_workspace(original))).replace("NEXT", json.dumps(_workspace(original, correction, _event("govws-new-observation", "award_change"))))
    path = tmp_path / "correction_inbox.js"
    path.write_text(script)
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert "Correction to a previously observed matching record" in out["en"]
    assert "New matching award or action change" in out["en"]
    assert "whether this was new information or a correction was not retained" in out["en"]
    assert "not a new award, obligation or issuer revenue" in out["en"]
    assert "匹配记录发生修正" in out["zh"]
    assert "新的授标或行动变化" in out["zh"]
    assert "未保留其属于新信息还是修正的分类" in out["zh"]
    assert "Correction to a previously observed" not in out["zh"]
    assert "匹配记录发生修正" not in out["en"]
    assert out["legacy"]["notification_kind"] == "unclassified"
    assert out["legacy"]["event_contract"] is None
    assert out["legacy"]["event_version"] is None
    assert out["legacy"]["record_id"] is None


@needs_node
def test_saved_cut_restores_original_public_window_and_selected_revision_after_reload(tmp_path: Path) -> None:
    event = _event("govws-saved-original", "award_change")
    workspace = _workspace(event)
    out = _run_node(tmp_path, """
      const app=make();
      const view=app.createView({name:'Original Defense cut',filters:{mode:'changes',ticker:'LMT'},
        workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true},selected_event_id:'govws-saved-original'}).view;
      app.createAlert({view_id:view.id,type:'award_change'});app.reconcile(SOURCE,{complete:true,bundle_matched:true});
      const restored=make();const cut=restored.getSavedCut(view.id);
      const before=JSON.stringify(cut);
      const live=restored.reconcile(LATER,{complete:true,bundle_matched:true});
      process.stdout.write(JSON.stringify({view,cut,live,unchanged:before===JSON.stringify(restored.getSavedCut(view.id)),stored:JSON.stringify(restored.state())}));
    """.replace("SOURCE", json.dumps(workspace)).replace("LATER", json.dumps(_workspace(_event("govws-later", "award_change"), bundle="grw2-bbbbbbbbbbbbbbbbbbbbbbbb"))))
    assert out["cut"]["ok"] is True
    cut = out["cut"]["cut"]
    assert cut["contract"] == "government_procurement_saved_cut.v1"
    assert cut["selected_event_id"] == event["event_id"]
    assert cut["payload"]["workspace"]["bundle_id"] == workspace["bundle_id"]
    assert cut["payload"]["workspace"]["as_of"] == workspace["as_of"]
    assert cut["payload"]["workspace"]["known_at"] == workspace["known_at"]
    assert cut["payload"]["query"]["filters"]["ticker"] == "LMT"
    assert [r["event_id"] for r in cut["payload"]["records"]] == [event["event_id"]]
    assert cut["payload"]["records"][0]["version"] == 1
    assert "must-not-export" not in out["stored"]
    assert "private_raw_payload" not in out["stored"]
    assert out["unchanged"] is True
    assert [r["event_id"] for r in out["live"]["alerts"]] == ["govws-later"]
    assert out["live"]["alerts"][0]["notification_kind"] == "new_observation"


@needs_node
def test_saved_cut_refuses_partial_or_oversized_window_without_partial_state(tmp_path: Path) -> None:
    workspace = _workspace(*[_event(f"govws-{i}", "award_change") for i in range(101)])
    out = _run_node(tmp_path, """
      const app=make();let partial=null,large=null;
      try{app.createView({name:'Partial',filters:{},workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:false,bundle_matched:true}})}catch(e){partial=e.code}
      try{app.createView({name:'Large',filters:{},workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}})}catch(e){large=e.code}
      process.stdout.write(JSON.stringify({partial,large,views:app.listViews()}));
    """.replace("SOURCE", json.dumps(workspace)))
    assert out == {"partial": "workspace_not_ready", "large": "saved_cut_too_large", "views": []}


@needs_node
def test_invalid_saved_cut_is_preserved_and_refused_without_current_data_substitution(tmp_path: Path) -> None:
    out = _run_node(tmp_path, """
      const app=make();const view=app.createView({name:'Legacy filters',filters:{ticker:'LMT'}}).view;
      const before=app.getSavedCut(view.id);
      const key='mastermind.government_revenue.briefcase.v1.user.test-user';const state=JSON.parse(values[key]);
      state.saved_views[0].cut={contract:'unknown.future',opaque:'preserve-me'};values[key]=JSON.stringify(state);
      const restored=make();const refused=restored.getSavedCut(view.id);
      restored.updateView(view.id,{name:'Renamed'});
      process.stdout.write(JSON.stringify({before,refused,cut:JSON.parse(values[key]).saved_views[0].cut}));
    """)
    assert out["before"] == {"ok": False, "reason": "cut_not_captured"}
    assert out["refused"] == {"ok": False, "reason": "invalid_saved_cut"}
    assert out["cut"] == {"contract": "unknown.future", "opaque": "preserve-me"}


@needs_node
def test_ui_reopens_original_saved_cut_and_clears_it_on_owner_change(tmp_path: Path) -> None:
    old_event = _event("govws-saved-focus", "award_change")
    old = _workspace(old_event)
    later = _workspace(_event("govws-new-live", "award_change"), bundle="grw2-bbbbbbbbbbbbbbbbbbbbbbbb")
    later.update(as_of="2026-08-03", known_at="2026-08-03T09:00:00Z")
    script = r"""
      const fs=require('fs'),values={},nodes={},listeners={};
      const storage={getItem:k=>values[k]||null,setItem:(k,v)=>{values[k]=String(v)}};
      function node(id){return nodes[id]||(nodes[id]={value:'',innerHTML:'',textContent:'',disabled:false,className:'',addEventListener:(k,f)=>listeners[id+':'+k]=f,focus(){}})}
      const document={activeElement:null,getElementById:node};
      global.window={localStorage:storage,document,location:{search:'?item=ws:govws-stale-url'}};
      eval(fs.readFileSync(CORE,'utf8'));eval(fs.readFileSync(UI_PATH,'utf8'));
      let current=OLD_WORKSPACE,drawer=null,ownerCallback,applied=null,clears=0;
      function esc(x){return String(x||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
      const api={get:node,tr:(en,zh)=>en,esc,text:x=>String(x||''),getFilters:()=>({mode:'changes',ticker:'LMT'}),applyFilters:f=>applied=f,
        onOwnerChange:cb=>{ownerCallback=cb;cb('test-user')},clearPrivatePresentation:()=>{clears++;drawer=null},
        getVisibleEventIds:()=>current.events.map(row=>row.event_id),getSelectedEventId:()=>current.events[0].event_id,getWorkspace:()=>current,isWorkspaceReady:()=>true,openDrawer:value=>drawer=value};
      const ui=window.mountGovernmentRevenueBriefcaseUI(api);
      node('savedViewName').value='Original private research';listeners['saveView:click']();
      current=LATER_WORKSPACE;listeners['savedViewSelect:change']();
      const opened=drawer;const status=node('briefcaseStatus').textContent;
      ownerCallback('different-user');
      process.stdout.write(JSON.stringify({opened,status,applied,focusWasSelect:opened.focus===node('savedViewSelect'),after:drawer,options:node('savedViewSelect').innerHTML,clears}));
    """.replace("CORE", json.dumps(str(MODULE))).replace("UI_PATH", json.dumps(str(ROOT / "templates/government-revenue-briefcase-ui.js"))).replace("OLD_WORKSPACE", json.dumps(old)).replace("LATER_WORKSPACE", json.dumps(later))
    path = tmp_path / "saved_cut_ui.js"
    path.write_text(script)
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["opened"] is not None
    assert out["focusWasSelect"] is True
    assert "govws-saved-focus" in out["opened"]["html"]
    assert "2026-08-02T09:00:00Z" in out["opened"]["html"]
    assert "grw2-aaaaaaaaaaaaaaaaaaaaaaaa" in out["opened"]["html"]
    assert "govws-new-live" not in out["opened"]["html"]
    assert "2026-08-03T09:00:00Z" not in out["opened"]["html"]
    assert 'data-saved-cut-selected="true"' in out["opened"]["html"]
    assert "not the current workspace" in out["opened"]["html"]
    assert out["applied"]["ticker"] == "LMT"
    assert out["after"] is None
    assert "Original private research" not in out["options"]
    assert out["clears"] >= 2


@needs_node
def test_saved_cut_replacement_is_atomic_and_unsupported_modes_never_become_changes(tmp_path: Path) -> None:
    workspace = _workspace(_event("govws-cut-atomic", "award_change"))
    out = _run_node(tmp_path, """
      const app=make();const input={name:'Keep original',filters:{mode:'changes'},workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true},selected_event_id:'govws-cut-atomic'};
      const view=app.createView(input).view;const original=JSON.stringify(app.getView(view.id));const errors=[];
      for(const patch of [
        {name:'Do not partly rename',filters:{mode:'awards'}},
        {name:'Do not replace',filters:{mode:'changes'},workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:false,bundle_matched:true}},
        {name:'Unsupported',filters:{mode:'candidates'}},
        {...input,selected_event_id:'not-in-original-window'},
        {...input,selected_event_id:false}
      ]){try{app.updateView(view.id,patch)}catch(e){errors.push(e.code)}}
      let unsupported;try{app.createView({name:'Wrong mode',filters:{mode:'budget'}})}catch(e){unsupported=e.code}
      process.stdout.write(JSON.stringify({errors,unsupported,unchanged:original===JSON.stringify(app.getView(view.id)),count:app.listViews().length}));
    """.replace("SOURCE", json.dumps(workspace)))
    assert out["errors"] == ["saved_cut_required", "workspace_not_ready", "unsupported_view_mode", "invalid_saved_cut", "invalid_saved_cut"]
    assert out["unsupported"] == "unsupported_view_mode"
    assert out["unchanged"] is True
    assert out["count"] == 1


@needs_node
def test_saved_cut_enforces_byte_budget_without_retaining_private_fields(tmp_path: Path) -> None:
    huge_public = _event("govws-large-public", "award_change", title="x" * (260 * 1024))
    private = _event("govws-private-omitted", "award_change")
    private["private_source_body"] = "sensitive-body" * (30 * 1024)
    out = _run_node(tmp_path, """
      const app=make();let error;
      try{app.createView({name:'Too large',filters:{},workspace:LARGE,visible_event_ids:LARGE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}})}catch(e){error=e.code}
      const view=app.createView({name:'Public only',filters:{},workspace:PRIVATE_SOURCE,visible_event_ids:PRIVATE_SOURCE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}}).view;
      process.stdout.write(JSON.stringify({error,count:app.listViews().length,stored:JSON.stringify(app.state()),cut:app.getSavedCut(view.id)}));
    """.replace("LARGE", json.dumps(_workspace(huge_public))).replace("PRIVATE_SOURCE", json.dumps(_workspace(private))))
    assert out["error"] == "saved_cut_too_large"
    assert out["count"] == 1
    assert out["cut"]["ok"] is True
    assert "private_source_body" not in out["stored"]
    assert "sensitive-body" not in out["stored"]


@needs_node
def test_saved_cut_refuses_ambiguous_or_invalid_clocks_but_preserves_native_precision(tmp_path: Path) -> None:
    workspace = _workspace(_event("govws-clock", "award_change"))
    out = _run_node(tmp_path, """
      const app=make(),base=SOURCE,errors=[];
      for(const [field,value] of [['as_of','2026'],['as_of','2026-02-30'],['known_at','2026-08-02'],['known_at',2026],['generated_at','2026-08-02T09:00:00']]){
        try{app.createView({name:'Bad clock',filters:{},workspace:{...base,[field]:value},visible_event_ids:base.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}})}catch(e){errors.push(e.code)}
      }
      const precise='2026-08-02T09:00:00.472913+00:00';
      const view=app.createView({name:'Native clocks',filters:{},workspace:{...base,known_at:precise,generated_at:null},visible_event_ids:base.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}}).view;
      process.stdout.write(JSON.stringify({errors,count:app.listViews().length,cut:app.getSavedCut(view.id)}));
    """.replace("SOURCE", json.dumps(workspace)))
    assert out["errors"] == ["invalid_saved_cut"] * 5
    assert out["count"] == 1
    assert out["cut"]["cut"]["payload"]["workspace"]["known_at"] == "2026-08-02T09:00:00.472913+00:00"
    assert out["cut"]["cut"]["payload"]["workspace"]["generated_at"] is None


@needs_node
def test_saved_cut_refuses_event_authority_escalation_without_erasing_retained_bytes(tmp_path: Path) -> None:
    workspace = _workspace(_event("govws-context-only", "award_change"))
    out = _run_node(tmp_path, """
      const app=make(),view=app.createView({name:'Original context',filters:{},workspace:SOURCE,visible_event_ids:SOURCE.events.map(row=>row.event_id),readiness:{complete:true,bundle_matched:true}}).view;
      const key='mastermind.government_revenue.briefcase.v1.user.test-user';
      const state=JSON.parse(values[key]);state.saved_views[0].cut.payload.records[0].authority.can_size=true;
      values[key]=JSON.stringify(state);const altered=values[key],restored=make();
      process.stdout.write(JSON.stringify({result:restored.getSavedCut(view.id),unchanged:values[key]===altered}));
    """.replace("SOURCE", json.dumps(workspace)))
    assert out["result"] == {"ok": False, "reason": "invalid_saved_cut"}
    assert out["unchanged"] is True


@needs_node
def test_saved_cut_uses_page_membership_instead_of_reinterpreting_filters(tmp_path: Path) -> None:
    issuer_defense = _event('govws-civilian-agency-defense-issuer', 'award_change')
    issuer_defense['agency']['department_name'] = 'Department of Energy'
    hidden_match = _event('govws-hidden-recipient-match', 'award_change')
    hidden_match['listed_company_impacts'][0]['company_name'] = 'HOWMET'
    workspace = _workspace(issuer_defense, hidden_match)
    out = _run_node(tmp_path, """
      const app=make(),workspace=SOURCE,readiness={complete:true,bundle_matched:true};
      const defense=app.createView({name:'Page issuer tags',filters:{truth:'defense'},workspace,readiness,
        visible_event_ids:['govws-civilian-agency-defense-issuer'],selected_event_id:'govws-civilian-agency-defense-issuer'}).view;
      const empty=app.createView({name:'Empty visible query',filters:{q:'HOWMET'},workspace,readiness,visible_event_ids:[],selected_event_id:null}).view;
      const ordered=app.createView({name:'Page order',filters:{},workspace,readiness,
        visible_event_ids:['govws-hidden-recipient-match','govws-civilian-agency-defense-issuer']}).view;
      const restored=make();process.stdout.write(JSON.stringify({defense:restored.getSavedCut(defense.id),empty:restored.getSavedCut(empty.id),ordered:restored.getSavedCut(ordered.id)}));
    """.replace('SOURCE', json.dumps(workspace)))
    assert out['defense']['ok'] is True
    assert [r['event_id'] for r in out['defense']['cut']['payload']['records']] == [issuer_defense['event_id']]
    assert out['empty']['ok'] is True
    assert out['empty']['cut']['payload']['records'] == []
    assert out['empty']['cut']['selected_event_id'] is None
    assert [r['event_id'] for r in out['ordered']['cut']['payload']['records']] == [hidden_match['event_id'], issuer_defense['event_id']]
    assert out['ordered']['cut']['payload']['query']['result_scope'] == 'original visible governed workspace cut'


@needs_node
@pytest.mark.parametrize('ids', [None, ['missing'], ['govws-valid', 'govws-valid'], [False]])
def test_saved_cut_refuses_missing_ambiguous_or_unknown_page_membership(tmp_path: Path, ids: list | None) -> None:
    out = _run_node(tmp_path, """
      const app=make();let error;
      try{app.createView({name:'Invalid membership',filters:{},workspace:SOURCE,readiness:{complete:true,bundle_matched:true},visible_event_ids:IDS})}catch(e){error=e.code}
      process.stdout.write(JSON.stringify({error,views:app.listViews()}));
    """.replace('SOURCE', json.dumps(_workspace(_event('govws-valid', 'award_change')))).replace('IDS', json.dumps(ids)))
    assert out == {'error': 'invalid_saved_cut', 'views': []}


@needs_node
def test_saved_cut_refuses_record_kind_outside_saved_mode(tmp_path: Path) -> None:
    out = _run_node(tmp_path, """
      const app=make();let error;
      try{app.createView({name:'Wrong mode',filters:{mode:'awards'},workspace:SOURCE,readiness:{complete:true,bundle_matched:true},visible_event_ids:['govws-opp']})}catch(e){error=e.code}
      process.stdout.write(JSON.stringify({error,views:app.listViews()}));
    """.replace('SOURCE', json.dumps(_workspace(_event('govws-opp', 'opportunity')))))
    assert out == {'error': 'invalid_saved_cut', 'views': []}


@needs_node
@pytest.mark.parametrize('ready', [True, False])
def test_ui_reports_alert_storage_failure_with_and_without_ready_workspace(tmp_path: Path, ready: bool) -> None:
    out = _run_node(tmp_path, r"""
      eval(require('fs').readFileSync(UI_PATH,'utf8'));
      const nodes={},listeners={};function node(id){return nodes[id]||(nodes[id]={value:id==='alertType'?'opportunity':'',innerHTML:'',textContent:'',disabled:false,className:'',addEventListener:(k,f)=>listeners[id+':'+k]=f,focus(){}})}
      window.document={getElementById:node};
      const api={get:node,tr:x=>x,esc:x=>String(x||''),text:x=>String(x||''),onOwnerChange:cb=>cb('test-user'),getFilters:()=>({mode:'companies'}),applyFilters(){},isWorkspaceReady:()=>READY,getWorkspace:()=>(SOURCE)};
      window.mountGovernmentRevenueBriefcaseUI(api);node('savedViewName').value='Device view';listeners['saveView:click']();
      localStorage.setItem=()=>{throw Error('QuotaExceededError')};listeners['toggleLocalAlert:click']();
      process.stdout.write(JSON.stringify({status:node('briefcaseStatus').textContent,className:node('briefcaseStatus').className}));
    """.replace('UI_PATH', json.dumps(str(ROOT/'templates/government-revenue-briefcase-ui.js'))).replace('READY', json.dumps(ready)).replace('SOURCE', json.dumps(_workspace())))
    assert 'available only in this tab' in out['status']
    assert 'browser storage is unavailable' in out['status']
    assert 'warn' in out['className']


def _page_membership_source() -> str:
    """Run the production row builder/predicate/resolver, not a copied predicate."""
    page = (ROOT / 'templates/government-revenue-page.js.j2').read_text()
    blocks = []
    for name in ('buildRows', 'pageRowMatches', 'matchingWorkspaceEventIds'):
        start = page.index('  function ' + name + '(')
        end = page.index('\n  function ', start + 1)
        blocks.append(page[start:end])
    return '\n'.join(blocks)


def _membership_harness(workspace: dict) -> str:
    return r"""
      let WORKSPACE=WORKSPACE_JSON,WORKSPACE_EVENTS=WORKSPACE.events,HAS_WORKSPACE=true;
      let briefcaseWorkspaceReady=true,rowsByMode={},lang='en';
      const COMPANIES=[],DATA={},arr=x=>Array.isArray(x)?x:[],obj=x=>x&&typeof x==='object';
      const text=(x,fallback='')=>x==null?fallback:String(x);
      const agencyName=a=>a.department_name||'',agencySubName=a=>a.subagency||'';
      const defenseAgency=a=>/Department of Defense/.test(a);
      const company=t=>['LMT','BA'].includes(t)?{tags:['defense']}:null;
      const tr=(en,zh)=>lang==='zh'?zh:en,isOfficial=r=>r.truth==='official';
      const workspaceTitle=e=>lang==='zh'&&e.title_zh?e.title_zh:e.title_original;
      const workspaceSummary=e=>e.display_summary||'',identitySubjectRows=()=>[];
      PAGE_SOURCE
      function load(next){WORKSPACE=next;WORKSPACE_EVENTS=next.events;buildRows();}
      buildRows();
      const app=window.createGovernmentRevenueBriefcase({storage:localStorage,now:clock,ownerId:'test-user',resolveEventIds:matchingWorkspaceEventIds});
    """.replace('WORKSPACE_JSON', json.dumps(workspace)).replace('PAGE_SOURCE', _page_membership_source())


@needs_node
def test_page_membership_drives_export_order_issuer_tags_and_localized_search(tmp_path: Path) -> None:
    nasa = _event('govws-nasa', 'opportunity', title='Space sensor prototype')
    nasa['agency'] = {'department_name': 'NASA'}
    nasa['title_zh'] = '空间传感器原型'
    hidden = _event('govws-hidden', 'award_change', ticker='BA')
    hidden['record_id'] = 'HOWMET-hidden-identifier'
    workspace = _workspace(nasa, hidden)
    out = _run_node(tmp_path, _membership_harness(workspace) + r"""
      const defense=app.buildJsonExport(WORKSPACE,{mode:'changes',truth:'defense',ticker:'LMT'});
      const hidden=app.buildJsonExport(WORKSPACE,{mode:'changes',q:'HOWMET'});
      lang='zh';buildRows();
      const localized=app.buildJsonExport(WORKSPACE,{mode:'changes',q:'传感器'});
      rowsByMode.changes.reverse();
      const ordered=app.buildJsonExport(WORKSPACE,{mode:'changes'}),csv=app.buildCsvExport(WORKSPACE,{mode:'changes'});
      process.stdout.write(JSON.stringify({defense,hidden,localized,ordered,csv}));
    """)
    assert [x['event_id'] for x in out['defense']['records']] == ['govws-nasa']
    assert out['hidden']['records'] == []
    assert [x['event_id'] for x in out['localized']['records']] == ['govws-nasa']
    assert [x['event_id'] for x in out['ordered']['records']] == ['govws-hidden', 'govws-nasa']
    import csv, io
    assert [x['event_id'] for x in csv.DictReader(io.StringIO(out['csv']['content']))] == ['govws-hidden', 'govws-nasa']
    assert 'must-not-export' not in json.dumps(out)


@needs_node
def test_each_saved_alert_uses_own_page_membership_and_preserves_event_semantics(tmp_path: Path) -> None:
    original = _event('govws-lmt-old', 'award_change')
    original['agency'] = {'department_name': 'NASA'}
    ba = _event('govws-ba-old', 'award_change', ticker='BA')
    correction = _event('govws-lmt-correction', 'award_change')
    correction.update(record_id=original['record_id'], version=2)
    correction['agency'] = original['agency']
    correction['change']['is_correction'] = True
    opportunity = _event('govws-opportunity', 'opportunity')
    new_ba = _event('govws-ba-new', 'award_change', ticker='BA')
    base, later = _workspace(original, ba), _workspace(original, ba, correction, opportunity, new_ba)
    out = _run_node(tmp_path, _membership_harness(base) + r"""
      const views=['LMT','BA'].map(ticker=>app.createView({name:ticker,filters:{mode:'changes',truth:'defense',ticker}}).view);
      views.forEach(view=>app.createAlert({view_id:view.id,type:'award_change'}));
      const first=app.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      load(LATER);
      // A different active query must never become either saved view's window.
      const active=app.buildJsonExport(WORKSPACE,{mode:'changes',q:'no-match'});
      const next=app.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      const replay=app.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      const before=JSON.stringify(values);briefcaseWorkspaceReady=false;
      const outage=app.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      process.stdout.write(JSON.stringify({first,active,next,replay,outage,preserved:before===JSON.stringify(values)}));
    """.replace('LATER', json.dumps(later)))
    assert out['first']['reconciled'] and out['first']['alerts'] == []
    assert out['active']['records'] == []
    assert {x['event_id']: x['notification_kind'] for x in out['next']['alerts']} == {
        'govws-lmt-correction': 'correction', 'govws-ba-new': 'new_observation'}
    assert out['replay']['alerts'] == []
    assert out['outage']['reason'] == 'view_membership_unavailable'
    assert out['preserved']


@needs_node
@pytest.mark.parametrize('bad', ['undefined', 'null', "['missing']", "['govws-a','govws-a']", "Array(501).fill('govws-a')", "(()=>{throw Error('unready')})()"])
def test_invalid_second_view_membership_is_atomic_and_export_never_falls_back(tmp_path: Path, bad: str) -> None:
    workspace = _workspace(_event('govws-a', 'opportunity'))
    out = _run_node(tmp_path, r"""
      const ws=WORKSPACE;let fail=false;
      const app=window.createGovernmentRevenueBriefcase({storage:localStorage,ownerId:'test-user',now:clock,resolveEventIds:(w,f)=>{
        if(fail&&f.ticker==='BA')return BAD;
        return ['govws-a'];
      }});
      ['LMT','BA'].forEach(ticker=>{const view=app.createView({name:ticker,filters:{mode:'changes',ticker}}).view;app.createAlert({view_id:view.id,type:'opportunity'});});
      const before=JSON.stringify(values);fail=true;
      const result=app.reconcile(ws,{complete:true,bundle_matched:true});
      let exportCode;try{app.buildJsonExport(ws,{mode:'changes',ticker:'BA'})}catch(e){exportCode=e.code}
      process.stdout.write(JSON.stringify({result,preserved:before===JSON.stringify(values),snapshot:app.state(),exportCode}));
    """.replace('WORKSPACE', json.dumps(workspace)).replace('BAD', bad))
    assert out['result']['reason'] == 'view_membership_unavailable'
    assert out['preserved']
    assert all(not x['primed'] for x in out['snapshot']['alerts'])
    assert out['exportCode'] == 'view_membership_unavailable'


@needs_node
def test_missing_page_resolver_and_wrong_workspace_fail_without_false_empty(tmp_path: Path) -> None:
    workspace = _workspace(_event('govws-a', 'opportunity'))
    out = _run_node(tmp_path, _membership_harness(workspace) + r"""
      const missing=window.createGovernmentRevenueBriefcase({storage:localStorage,ownerId:'no-resolver'});
      let missingCode,wrongCode;
      try{missing.buildJsonExport(WORKSPACE,{mode:'changes'})}catch(e){missingCode=e.code}
      try{app.buildJsonExport(JSON.parse(JSON.stringify(WORKSPACE)),{mode:'changes'})}catch(e){wrongCode=e.code}
      process.stdout.write(JSON.stringify({missingCode,wrongCode}));
    """)
    assert out == {'missingCode': 'view_membership_unavailable', 'wrongCode': 'view_membership_unavailable'}


@needs_node
def test_legacy_alert_upgrade_does_not_backfill_newly_included_old_records(tmp_path: Path) -> None:
    old = _event('govws-old', 'award_change')
    nasa = _event('govws-old-nasa', 'award_change')
    nasa['agency'] = {'department_name': 'NASA'}
    correction = _event('govws-new-correction', 'award_change')
    correction['agency'] = nasa['agency']
    correction['change']['is_correction'] = True
    out = _run_node(tmp_path, _membership_harness(_workspace(old, nasa)) + r"""
      const legacy=make(),view=legacy.createView({name:'Existing LMT monitor',filters:{mode:'changes',truth:'defense',ticker:'LMT'}}).view;
      legacy.createAlert({view_id:view.id,type:'award_change'});
      legacy.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      const oldState=legacy.state();delete oldState.alerts[0].membership_contract;
      const key='mastermind.government_revenue.briefcase.v1.user.test-user';values[key]=JSON.stringify(oldState);
      function reopen(){return window.createGovernmentRevenueBriefcase({storage:localStorage,ownerId:'test-user',resolveEventIds:matchingWorkspaceEventIds,now:clock});}
      const upgraded=reopen();const first=upgraded.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      const afterUpgrade=upgraded.state();const reloaded=reopen();
      const repeat=reloaded.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      load(NEXT);const next=reloaded.reconcile(WORKSPACE,{complete:true,bundle_matched:true});
      process.stdout.write(JSON.stringify({oldState,first,afterUpgrade,repeat,next}));
    """.replace('NEXT', json.dumps(_workspace(old, nasa, correction))))
    assert out['oldState']['alerts'][0]['seen_event_ids'] == ['govws-old']
    assert out['first']['alerts'] == [] and len(out['first']['rebaselined_alert_ids']) == 1
    assert out['afterUpgrade']['alerts'][0]['seen_event_ids'] == ['govws-old', 'govws-old-nasa']
    assert out['afterUpgrade']['alerts'][0]['membership_contract'] == 'page_filter_membership.v1'
    assert out['repeat']['alerts'] == [] and out['repeat']['rebaselined_alert_ids'] == []
    assert [(x['event_id'], x['notification_kind']) for x in out['next']['alerts']] == [('govws-new-correction', 'correction')]
