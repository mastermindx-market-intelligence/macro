"""Executable client contract for the Eval OS A1 evidence view.

The page is vanilla JavaScript.  These tests execute the exact pure rendering block from
``admin/static/app.js`` under Node rather than grepping for labels: the assertions cover
the HTML an authenticated operator actually receives from the view helpers.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
APP = REPO / "admin" / "static" / "app.js"
START = "/* IOS_EVIDENCE_CONTRACT_START */"
END = "/* IOS_EVIDENCE_CONTRACT_END */"


def _contract() -> str:
    source = APP.read_text(encoding="utf-8")
    assert START in source and END in source, (
        "the existing Intelligence OS page must expose its pure evidence rendering "
        "contract for executable client tests"
    )
    copy = source.split("/* Display only: canonical status/filter/owner data remain unchanged. */", 1)[1].split("const IOS_STATE_CLS", 1)[0]
    return copy + source.split(START, 1)[1].split(END, 1)[0]


def _run(cases: list[dict]) -> list[dict]:
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            raise AssertionError("Node is required for the Intelligence OS client contract")
        pytest.skip("node not available to execute the client contract")
    harness = f"""
const esc = (s) => String(s == null ? "" : s).replace(/[&<>\"']/g, c => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '\"': "&quot;", "'": "&#39;" }}[c]));
const document = {{ documentElement: {{ dataset: {{ lang: "en" }} }}, addEventListener() {{}} }};
const $ = () => null;
const fmtNum = (n) => n == null ? "—" : Number(n).toLocaleString("en-US");
{_contract()}
const cases = JSON.parse(process.argv[2]);
const out = cases.map(c => ({{
  classes: c.statuses.map(iosEvidenceStatusCls),
  bands: iosNormalizeCeoBands(c.bands),
  cell: iosEvidenceCell(c.engine),
  detail: iosEvidenceDetailCard(c.engine),
}}));
console.log(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "intelligence_os_contract.mjs"
        path.write_text(harness, encoding="utf-8")
        run = subprocess.run(
            [node, str(path), json.dumps(cases)],
            capture_output=True,
            text=True,
            check=False,
        )
    assert run.returncode == 0, run.stdout + run.stderr
    return json.loads(run.stdout)


def test_evidence_bands_are_complete_ordered_and_visually_distinct():
    result = _run(
        [
            {
                "statuses": [
                    "Validated",
                    "Accruing",
                    "Ungraded by design",
                    "Degraded",
                    "Disproven",
                ],
                # Deliberately omit the empty Validated band. The client must still
                # render it: zero is evidence here, not an absent answer.
                "bands": [
                    {"evidence_status": "Disproven", "n_engines": 1},
                    {"evidence_status": "Accruing", "n_engines": 7},
                ],
                "engine": {},
            }
        ]
    )[0]

    assert result["classes"] == ["s-ok", "s-warn", "s-mut", "s-bad", "s-bad"]
    assert [row["evidence_status"] for row in result["bands"]] == [
        "Validated",
        "Accruing",
        "Ungraded by design",
        "Degraded",
        "Disproven",
    ]
    assert result["bands"][0]["n_engines"] == 0
    assert result["bands"][1]["n_engines"] == 7


def test_detail_card_renders_lawful_evidence_without_a_score():
    engine = {
        "evidence_status": "Accruing",
        "evidence_reason_codes": ["immature_evidence", "mixed_explicit_bases"],
        "evidence_refs": ["qledger:stock_desk:horizon:21"],
        "evidence_provider": {
            "kind": "qledger",
            "binding": "adapter:stock_desk",
            "family": "stock_desk",
            "read_status": "ok",
        },
        "evidence_ruler": {
            "declared_horizon": {"horizon_d": [21], "horizon_unit": "trading_days"},
            "selected_qledger_rung": "21",
            "qledger_clock": {"git_sha": "abc123"},
        },
        "evidence_basis": {
            "clock_basis_by_horizon": {"21": "explicit"},
            "evidence_basis_by_horizon": {"21": "forward_return"},
            "pooling_refused": True,
        },
        "evidence_maturity": {
            "validation_state": "phase0",
            "rungs": {"21": {"n_dates": 7, "needed": 25}},
        },
        "validation_state": "phase0",
        "validation_state_evidence": {"reason": "no_species_bound"},
        "output_class": None,
        "graded_by_design": "yes",
        "graded_by_design_source": "derived: owner ledger",
    }
    html = _run([{"statuses": [], "bands": [], "engine": engine}])[0]["detail"]

    for visible in (
        "Accruing",
        "adapter:stock_desk",
        "trading_days",
        "pooling_refused",
        "immature_evidence",
        "mixed_explicit_bases",
        "qledger:stock_desk:horizon:21",
        "phase0",
        "output class",
        "null",
    ):
        assert visible in html
    assert "evidence_score" not in html
    assert "Evidence score" not in html


def test_noncanonical_detail_renders_registry_gap_not_an_evidence_disposition():
    rendered = _run(
        [
            {
                "statuses": [],
                "bands": [],
                "engine": {
                    "canonical_t1": False,
                    "evidence_status": None,
                    "evidence_reason_codes": ["not_canonical_t1"],
                },
            }
        ]
    )[0]
    html = rendered["detail"]

    assert "Registry gap" in html
    assert "No T1 evidence disposition" in html
    assert "Accruing" not in html
    assert "Registry gap" in rendered["cell"]
    assert "Accruing" not in rendered["cell"]


# Append to existing tests/test_admin_intelligence_os_ui.py under its owner's custody.
def _preferences_run(case: dict) -> dict:
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            raise AssertionError("Node is required for the admin preference contract")
        pytest.skip("node not available")
    source = (REPO / "admin/static/preferences.js").read_text(encoding="utf-8")
    harness = r"""
const vm = require('node:vm');
const c = JSON.parse(process.argv[2]);
const attrs = {}, events = [], stored = Object.assign({}, c.stored || {});
const root = { style: {}, setAttribute(k,v) { attrs[k]=v; } };
function element(attrs = {}) {
  return { attrs, value: '', textContent: '', listeners: {},
    getAttribute(k){return this.attrs[k];}, setAttribute(k,v){this.attrs[k]=v;},
    addEventListener(k,fn){this.listeners[k]=fn;},
    get innerHTML(){throw Error('innerHTML read forbidden');},
    set innerHTML(v){throw Error('innerHTML rewrite forbidden');} };
}
const theme=element(), lang=element();
const label=element({'data-admin-en':'Theme','data-admin-zh':'主题'});
const placeholder=element({'data-admin-placeholder-en':'Password','data-admin-placeholder-zh':'密码'});
const aria=element({'data-admin-aria-en':'Open navigation','data-admin-aria-zh':'打开导航'});
const docListeners={};
const document={documentElement:root,readyState:'loading',
 getElementById(id){return c.absent ? null : ({adminTheme:theme,adminLanguage:lang}[id] || null);},
 querySelectorAll(selector){return selector.includes('placeholder')?[placeholder]:selector.includes('aria')?[aria]:[label];},
 addEventListener(k,fn){docListeners[k]=fn;}, dispatchEvent(e){events.push({type:e.type,detail:e.detail});}
};
const storage={getItem(k){if(c.deny)throw Error('denied');return stored[k] || null;},
 setItem(k,v){if(c.deny)throw Error('denied');stored[k]=v;}, removeItem(k){if(c.deny)throw Error('denied');delete stored[k];}};
const ctx={document,window:{matchMedia(){return {matches:c.deviceDark !== false};}},localStorage:storage,
 CustomEvent:function(type,opts){this.type=type;this.detail=opts.detail;}};
vm.runInNewContext(SOURCE,ctx);
const beforeDOMContentLoaded={...attrs,lang:root.lang};
docListeners.DOMContentLoaded();
if(c.change){const control=c.change.control==='theme'?theme:lang;control.value=c.change.value;control.listeners.change({target:control});}
console.log(JSON.stringify({attrs,lang:root.lang,colorScheme:root.style.colorScheme,stored,events,
 beforeDOMContentLoaded,label:label.textContent,placeholder:placeholder.placeholder,aria:aria.attrs['aria-label'],themeValue:theme.value,languageValue:lang.value}));
""".replace("SOURCE", json.dumps(source))
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "admin_preferences.cjs"
        path.write_text(harness, encoding="utf-8")
        run = subprocess.run([node, str(path), json.dumps(case)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stdout + run.stderr
    return json.loads(run.stdout)


def test_preferences_validate_and_apply_before_dom_ready():
    valid = _preferences_run({"stored": {"theme": "light", "lang": "zh"}})
    assert valid["beforeDOMContentLoaded"] == {"data-theme": "light", "data-lang": "zh", "lang": "zh-CN"}
    assert valid["colorScheme"] == "light"
    assert valid["label"] == "主题"
    assert valid["placeholder"] == "密码"
    assert valid["aria"] == "打开导航"
    invalid = _preferences_run({"stored": {"theme": "arbitrary", "lang": "zh-CN"}})
    assert invalid["attrs"] == {"data-theme": "dark", "data-lang": "en"}
    assert invalid["lang"] == "en"


def test_preferences_survive_storage_denial_and_emit_shared_contract():
    changed = _preferences_run({"deny": True, "deviceDark": False, "change": {"control": "language", "value": "zh"}})
    assert changed["attrs"] == {"data-theme": "light", "data-lang": "zh"}
    assert changed["lang"] == "zh-CN"
    assert changed["events"] == [{"type": "langchange", "detail": "zh"}]
    theme = _preferences_run({"stored": {"themeAuto": "1"}, "change": {"control": "theme", "value": "light"}})
    assert theme["stored"]["theme"] == "light"
    assert "themeAuto" not in theme["stored"]
    assert theme["events"] == [{"type": "themechange", "detail": "light"}]


def test_preferences_reject_unknown_control_values_and_tolerate_absent_controls():
    rejected = _preferences_run({"change": {"control": "language", "value": "<img onerror=1>"}})
    assert rejected["attrs"]["data-lang"] == "en"
    assert rejected["events"] == []
    assert rejected["languageValue"] == "en"
    absent = _preferences_run({"absent": True, "stored": {"theme": "light", "lang": "zh"}})
    assert absent["attrs"] == {"data-theme": "light", "data-lang": "zh"}


def test_detail_plain_support_preserves_zero_partial_horizon_and_technical_scope():
    rendered=_run([{"statuses":[],"bands":[],"engine":{
        "evidence_status":"Accruing","validation_state":"validated",
        "evidence_reason_codes":["owner_validation_scope_unqualified"],
        "evidence_ruler":{"declared_horizon":{"horizon_d":[126]},"selected_qledger_rung":"63",
          "qledger_clock":{"horizon_unit":"trading_days","clock_market":"US"}},
        "evidence_maturity":{"rungs":{"63":{"n_dates":0,"needed":25}}},
        "evidence_coverage":{"by_horizon":{"63":{"control_coverage":0,"n_cohort_rows":10,
          "n_controlled_rows":0,"n_control_refused_rows":10}}},
        "evidence_owner_scope":{"bound_species":[{"species_id":"<fixture>","owner_scope":{"version":"1"}}]}
    }}])[0]
    html=rendered["detail"]
    assert "Declared horizon" in html and "Graded horizon" in html and "Market calendar" in html
    assert "Partial horizon evidence" in html and "仅完成部分窗口" in html
    assert "Observed dates" in html and ">0<" in html
    assert "<details" in html and "Technical details" in html
    assert "&lt;fixture&gt;" in html and "<fixture>" not in html
    assert "No evidence references declared." in html
    assert "owner_validation_scope_unqualified" in html and "任务" in html


def test_refresh_uses_accepted_generation_and_restores_rejected_read_without_raw_error():
    node=shutil.which("node")
    if node is None:pytest.skip("node unavailable")
    source=APP.read_text(encoding="utf-8")
    renderer=source[source.index("RENDER.intelligence_os = async"):source.index("/* ---- Intelligence OS · engine detail")]
    harness=r'''
const vm=require('node:vm');
const renderer=JSON.parse(process.argv[2]);
async function run(reject) {
 const v={innerHTML:''},b={disabled:false,textContent:''},status={textContent:'',dataset:{}};
 let cache={ok:true,marker:'old',generated:{observed_at:'fixture-old'},engines:[],census:{}};
 const calls=[],toasts=[];let wrapped=false;
 const c={RENDER:{},IOS:{},Date,$:s=>s==='#view'?v:s==='#ios-refresh'?b:s==='#iosRefreshStatus'?status:null,
 api:async p=>{calls.push(p);if(p.includes('force=1')){if(reject)throw Error('SECRET_CANARY');return{ok:true,marker:'fresh',generated:{observed_at:'fixture-fresh'},engines:[],census:{}}}return cache},
 clearApiCache:()=>{cache=null},apiCacheStore:(p,e)=>{cache=e.value},apiCacheTtl:()=>300000,
 iosText:s=>s,iosCopy:s=>s,iosHero:d=>d.generated.observed_at,iosReasonCard:()=>'',iosCeoView:()=>'',iosTypedFindings:()=>'',
 iosRenderChips:()=>{},iosRenderTable:()=>{},fmtNum:String,nwEmpty:()=>'',toast:s=>toasts.push(s),
 wrapViewTables:()=>{wrapped=true},iosRestoreFocus:()=>{if(!wrapped)throw Error('focus before synchronous table wrapping')},iosLanguageAttributes:()=>{status.textContent='Refresh failed '+status.dataset.assessed},go:()=>{}};
 vm.createContext(c);vm.runInContext(renderer,c);await c.RENDER.intelligence_os();await b.onclick();await Promise.resolve();await Promise.resolve();
 return{marker:c.IOS.data.marker,calls,disabled:b.disabled,status:status.textContent,toasts,html:v.innerHTML};
}
(async()=>console.log(JSON.stringify({fresh:await run(false),failed:await run(true)})))();
'''
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"refresh.cjs";path.write_text(harness)
        result=subprocess.run([node,str(path),json.dumps(renderer)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    assert data["fresh"]["marker"]=="fresh" and len(data["fresh"]["calls"])==2
    assert "fixture-fresh" in data["fresh"]["html"]
    assert data["failed"]["marker"]=="old" and data["failed"]["disabled"] is False
    assert "fixture-old" in data["failed"]["status"] and "Refresh failed" in data["failed"]["status"]
    assert "SECRET_CANARY" not in json.dumps(data)


def test_translated_filter_copy_retains_canonical_values_and_counts():
    node=shutil.which("node")
    if node is None:pytest.skip("node unavailable")
    source=APP.read_text(encoding="utf-8")
    copy=source.split("/* Display only: canonical status/filter/owner data remain unchanged. */",1)[1].split("const IOS_STATE_CLS",1)[0]
    chip=source[source.index("function iosChip("):source.index("function iosMatches")]
    harness="""
const esc=s=>String(s==null?'':s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
const dataAttrs=o=>Object.entries(o).map(([k,v])=>' data-'+k+'="'+esc(v)+'"').join('');
const document={documentElement:{dataset:{lang:'zh'}},addEventListener(){}};
const $=()=>null;
"""+copy+chip+"\nconsole.log(JSON.stringify({e:iosCountsToChips({Accruing:2},'evidence_status',null),c:iosCountsToChips({classification_state:1},'output_class',null)}));"
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"chips.js";p.write_text(harness)
        result=subprocess.run([node,str(p)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    rendered=json.loads(result.stdout)
    assert 'data-val="Accruing"' in rendered["e"] and "证据积累中" in rendered["e"] and "(2)" in rendered["e"]
    assert 'data-val="classification_state"' in rendered["c"] and "状态分类" in rendered["c"]


def test_detail_return_restores_same_engine_focus_or_search_without_fetch():
    node=shutil.which("node")
    if node is None:pytest.skip("node unavailable")
    source=APP.read_text(encoding="utf-8")
    function=source[source.index("function iosRestoreFocus("):source.index("function iosLanguageAttributes")]
    harness='''let focused=''; const IOS={restoreFocus:true,returnFocusId:'fixture-engine'};
const link={dataset:{iosEngine:'fixture-engine'},focus(){focused='engine'}};
const search={focus(){focused='search'}};
'''+function+'''
const root={querySelectorAll:()=>[link],querySelector:()=>search};
iosRestoreFocus(root); if(focused!=='engine'||IOS.restoreFocus)throw Error('same engine not restored');
IOS.restoreFocus=true;root.querySelectorAll=()=>[];iosRestoreFocus(root);
if(focused!=='search')throw Error('missing link fallback');
console.log('PASS');'''
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"focus.js";p.write_text(harness)
        result=subprocess.run([node,str(p)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=="PASS"


def test_mobile_drawer_aria_keeps_current_state_in_both_languages():
    node=shutil.which("node")
    if node is None:pytest.skip("node unavailable")
    source=APP.read_text(encoding="utf-8")
    function=source[source.index("function setSidebarOpen("):source.index("function wireSidebarDrawer")]
    harness='''function classes(){return{values:new Set(),contains(v){return this.values.has(v)},toggle(v,on){if(on)this.values.add(v);else this.values.delete(v)}}}
const sidebar={classList:classes(),setAttribute(){},removeAttribute(){},contains(){return false}};
const scrim={classList:classes()}, toggle={attrs:{},setAttribute(k,v){this.attrs[k]=v},focus(){}};
const document={body:{classList:classes()},activeElement:null};
const window={matchMedia:()=>({matches:true})};const $=s=>({'#sidebar':sidebar,'#sidebarScrim':scrim,'#sidebarToggle':toggle}[s]||null);
let language='zh'; const iosText=s=>language==='zh'?({'Close navigation':'关闭导航','Open navigation':'打开导航'}[s]||s):s;
'''+function+'''
setSidebarOpen(true); if(toggle.attrs['aria-label']!=='关闭导航'||toggle.attrs['data-admin-aria-en']!=='Close navigation')throw Error('open label');
setSidebarOpen(false); if(toggle.attrs['aria-label']!=='打开导航'||toggle.attrs['data-admin-aria-zh']!=='打开导航')throw Error('closed label');
language='en';setSidebarOpen(true);if(toggle.attrs['aria-label']!=='Close navigation')throw Error('English label');console.log('PASS');'''
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"drawer.js";p.write_text(harness)
        result=subprocess.run([node,str(p)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_measurement_detail_separates_populations_null_zero_and_clock_bases():
    row={'evidence_basis':'matched_control','clock_basis':'explicit_unit_v1:trading_days:US','wilson_ci_low':0,'n_dates':30,'n_controlled_dates':30,'hit_rate':None,'excess_mean':None,'benchmark_baseline_hit_rate':30/70,'benchmark_baseline_excess_mean':None,'benchmark_baseline_excess_basis':'mixed_direction_refused','benchmark_baseline_excess_mean_by_direction':{'-1':-.1,'1':.1},'reason':'owner_fixture'}
    engine={'evidence_status':'Accruing','evidence_ruler':{'selected_qledger_rung':'21'},'evidence_measurement':{'by_horizon':{'21':row}},'evidence_refs':['data/qledger/grades.jsonl','research/FIXTURE_PREREG.md'],'evidence_source_links':[{'reference':'research/FIXTURE_PREREG.md','revision':'a'*40,'url':'https://github.com/mastermindx-market-intelligence/macro/blob/'+'a'*40+'/research/FIXTURE_PREREG.md'}]}
    rendered=_run([{'engine':engine,'statuses':[],'bands':[]}])[0]['detail']
    assert 'Whole-family benchmark baseline' in rendered and '全系列基准参照' in rendered
    assert 'Matched control' in rendered and '匹配对照' in rendered
    assert 'Wilson lower bound' in rendered and '>0</code>' in rendered
    assert 'Baseline denominator' in rendered and 'Unknown (not projected by owner)' in rendered
    assert 'compatible task, version and cohort qualification is not established' in rendered
    assert 'Repository source declaration' in rendered and 'noopener noreferrer' in rendered
    assert 'href="data/' not in rendered and 'No browser link is declared for this reference.' in rendered
    assert 'mixed_direction_refused' in rendered and '&quot;-1&quot;:-0.1' in rendered
    mixed=dict(engine,evidence_measurement={'by_horizon':{'21':dict(row,by_clock_basis={'basis-A':row,'basis-B':dict(row,wilson_ci_low=None)})}})
    html=_run([{'engine':mixed,'statuses':[],'bands':[]}])[0]['detail']
    assert 'basis-A' in html and 'basis-B' in html and 'no pooled estimate' in html


def test_actual_evidence_filter_row_translates_status_before_count():
    node=shutil.which('node')
    if node is None:pytest.skip('node unavailable')
    source=APP.read_text(encoding='utf-8')
    chips=source[source.index('function iosChip('):source.index('function iosMatches')]
    renderer=source[source.index('function iosRenderChips()'):source.index('function iosCeoView(')]
    harness='''const esc=s=>String(s==null?'':s);const dataAttrs=o=>Object.entries(o).map(([k,v])=>' data-'+k+'="'+esc(v)+'"').join('');
const el={innerHTML:''};const document={documentElement:{dataset:{lang:'zh'}},addEventListener(){}};const $=s=>s==='#iosChips'?el:null;
'''+_contract()+chips+renderer+'''
const IOS={data:{census:{},ceo_view:[{evidence_status:'Accruing',n_engines:3}]},rows:[],filter:{}};
iosRenderChips();console.log(el.innerHTML);'''
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'evidence-chips.js';p.write_text(harness)
        result=subprocess.run([node,str(p)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'data-val="Accruing"' in result.stdout and '证据积累中' in result.stdout and '(3)' in result.stdout
    assert 'Accruing (3)</span>' not in result.stdout


def test_class_and_authority_chip_counts_match_the_rows_they_filter():
    """Artifact multiplicity must not change the number promised by a row filter."""
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            raise AssertionError("Node is required for the Intelligence OS client contract")
        pytest.skip("node unavailable")
    source = APP.read_text(encoding="utf-8")
    state = source[source.index("const IOS_STATE_CLS"):source.index(START)]
    controls = source[source.index("const IOS ="):source.index("function iosHero(")]
    harness = r"""
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dataAttrs = o => Object.entries(o).map(([k,v]) => ' data-'+k+'="'+esc(v)+'"').join('');
const document = {documentElement:{dataset:{lang:process.argv[2]}},addEventListener(){}};
const elements = Object.fromEntries(['#iosChips','#iosTbl','#iosCnt','#iosPager'].map(k => [k,{innerHTML:'',textContent:''}]));
const $ = selector => elements[selector] || null;
const fmtNum = String;
""" + _contract() + state + controls + r"""
const rows = [
  {engine_id:'null-many',canonical_t1:true,output_class:null,authority:null,n_artifacts:7,worst_state:null,evidence_status:'Degraded'},
  {engine_id:'ranking-many',canonical_t1:true,output_class:'ranking',authority:'display',n_artifacts:3,worst_state:'healthy',evidence_status:'Accruing'},
  {engine_id:'ranking-zero',canonical_t1:true,output_class:'ranking',authority:'engine_input',n_artifacts:0,worst_state:null,evidence_status:'Degraded'},
  {engine_id:'registry-gap',canonical_t1:false,output_class:null,authority:'display',n_artifacts:4,worst_state:'unavailable',evidence_status:null},
  {engine_id:'missing-values',canonical_t1:true,n_artifacts:2,worst_state:null,evidence_status:'Degraded'},
];
const data = {
  census:{engines:5,canonical_engines:4,noncanonical_output_groups:1,artifacts:16,
    by_output_class:{null:13,ranking:3},by_authority:{null:9,display:7}},
  ceo_view:[{evidence_status:'Degraded',n_engines:3},{evidence_status:'Accruing',n_engines:1}],
};
IOS.rows = rows; IOS.data = data;
const original = JSON.stringify({rows,data});
const decode = s => s.replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
function chips() {
  const result = {};
  for (const match of elements['#iosChips'].innerHTML.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
    const attrs = match[1], action = attrs.match(/onclick="([^"]*)"/), value = attrs.match(/data-val="([^"]*)"/);
    if (!action || !value) continue;
    const on = decode(action[1]), kind = on.match(/iosSetFilter\('([^']+)'/);
    if (!kind) continue;
    const label = decode(match[2].replace(/<[^>]*>/g,''));
    (result[kind[1]] ||= {})[decode(value[1])] = {count:Number(label.match(/\((\d+)\)$/)[1]),label,on};
  }
  return result;
}
function snapshot() {
  return {count:Number(elements['#iosCnt'].textContent),
    ids:Array.from(elements['#iosTbl'].innerHTML.matchAll(/data-ios-engine="([^"]*)"/g), m => decode(m[1])),
    chips:chips()};
}
function click(chip, value) {
  Function('iosSetFilter',chip.on).call({dataset:{val:value}},iosSetFilter);
}
iosRenderChips(); iosRenderTable();
const initial = snapshot(), selections = {};
for (const [kind,value] of [['output_class','null'],['output_class','ranking'],['authority','null'],['authority','display'],['authority','engine_input'],['evidence_status','Degraded']]) {
  IOS.filter = {}; IOS.q = ''; IOS.page = 1;
  if (!initial.chips[kind][value]) { selections[kind+':'+value] = {missing_chip:true}; continue; }
  click(initial.chips[kind][value],value);
  selections[kind+':'+value] = snapshot();
}
IOS.filter = {};
click(initial.chips.output_class.null,'null');
click(initial.chips.output_class.null,'null');
const cleared = snapshot();
IOS.filter = {};
click(initial.chips.output_class.ranking,'ranking');
click(initial.chips.authority.display,'display');
console.log(JSON.stringify({initial,selections,cleared,combined:snapshot(),unchanged:original === JSON.stringify({rows,data})}));
"""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "row-filter-contract.js"
        path.write_text(harness, encoding="utf-8")
        for language in ("en", "zh"):
            run = subprocess.run(
                [node, str(path), language], capture_output=True, text=True, check=False
            )
            assert run.returncode == 0, run.stdout + run.stderr
            result = json.loads(run.stdout)
            initial, selected = result["initial"], result["selections"]
            assert initial["count"] == 5
            expected = {
                "output_class": {"null": 3, "ranking": 2},
                "authority": {"null": 2, "display": 2, "engine_input": 1},
                "state": {"null": 3, "healthy": 1, "unavailable": 1},
            }
            for kind, counts in expected.items():
                assert {value: chip["count"] for value, chip in initial["chips"][kind].items()} == counts
            expected_rows = {
                "output_class:null": ["null-many", "registry-gap", "missing-values"],
                "output_class:ranking": ["ranking-many", "ranking-zero"],
                "authority:null": ["null-many", "missing-values"],
                "authority:display": ["ranking-many", "registry-gap"],
                "authority:engine_input": ["ranking-zero"],
                "evidence_status:Degraded": ["null-many", "ranking-zero", "missing-values"],
            }
            for selection, ids in expected_rows.items():
                assert selected[selection]["ids"] == ids
                assert selected[selection]["count"] == len(ids)
            assert sum(chip["count"] for chip in initial["chips"]["evidence_status"].values()) == 4
            assert result["cleared"]["count"] == 5
            assert result["combined"]["ids"] == ["ranking-many"]
            # Like state/evidence chips, class/authority counts describe all rows
            # before combined filters, not a new intersection-specific census.
            assert result["combined"]["chips"]["authority"]["display"]["count"] == 2
            assert result["combined"]["chips"]["output_class"]["ranking"]["count"] == 2
            assert result["unchanged"] is True
            # iosCopy emits both language spans; existing CSS chooses visibility.
            label = initial["chips"]["output_class"]["null"]["label"]
            assert "Not determined" in label and "尚未确定" in label
            assert label.endswith(" (3)")


def test_recorded_owner_disclosure_keeps_asof_and_unknown_separate_from_freshness():
    engine={'evidence_status':'Degraded','evidence_provider':{'recorded_snapshot':{'available':True,'recorded_at':'2026-01-01T00:00:00+00:00','evaluation_date':None,'named_generation_match':False,'current_source_qualification':'unavailable'}},'evidence_ruler':{'selected_qledger_rung':'21'},'evidence_measurement':{'by_horizon':{'21':{'evidence_basis':'matched_control','n_dates':0,'wilson_ci_low':None,'n_controlled_dates':0,'benchmark_baseline_hit_rate':0}}}}
    html=_run([{'engine':engine,'statuses':[],'bands':[]}])[0]['detail']
    assert 'Recorded owner support' in html and '原所有者记录的证据支持' in html
    assert 'Recorded by owner at' in html and '所有者记录时间' in html and '2026-01-01T00:00:00+00:00' in html
    assert 'Current source qualification' in html and '当前来源验证范围' in html
    assert 'Unavailable' in html and '不可确认' in html
    assert 'price, calendar freshness or task qualification' in html and '当前价格、交易日历新鲜度或任务验证范围' in html
    assert '>0</code>' in html and 'Unknown (not projected by owner)' in html


def test_intelligence_browser_reads_observe_server_snapshot_identity():
    node=shutil.which('node')
    if node is None:pytest.skip('node unavailable')
    source=APP.read_text(encoding='utf-8')
    section=source[source.index('const API_CACHE_BYPASS ='):source.index('function apiCacheStore')]
    harness=section+"\nconsole.log(JSON.stringify({panel:apiCacheable('/api/intelligence_os'),detail:apiCacheable('/api/intelligence_os/engine?id=fixture'),other:apiCacheable('/api/summary')}));"
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'cache-bypass.js';p.write_text(harness)
        result=subprocess.run([node,str(p)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)=={'panel':False,'detail':False,'other':True}
