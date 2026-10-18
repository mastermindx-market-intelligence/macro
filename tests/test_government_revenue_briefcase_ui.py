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
        const make = () => window.createGovernmentRevenueBriefcase({storage: localStorage, now: clock, ownerId: 'test-user'});
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
          onOwnerChange:function(callback){callback('test-user')},getFilters:function(){return filters},applyFilters:function(value){applied=value},getWorkspace:function(){return %(workspace)s},isWorkspaceReady:function(){return ready},openDrawer:function(){}});
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
      const stateOwner=window.createGovernmentRevenueBriefcase({storage,ownerId:'test-user'});
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
