"""Exercise the real Program consumer with synthetic reviewed oversight only."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from engine.government_revenue import program_dossier as pd, program_ontology as po
from tests.test_government_program_oversight import oversight_graph, assertion, capacity_claim, dossier

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node unavailable")


def bundle():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    g["public_capacity_assertions"] = [capacity_claim(g)]
    value = dossier(g)
    assert pd.is_valid_program_dossier_payload(value)
    return value


def run(value, lang="en", crypto=True):
    script = r"""
const fs=require('fs'),vm=require('vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const host={innerHTML:''},win={URL,TextEncoder,crypto:input.crypto?require('crypto').webcrypto:null,
fetch:async()=>({ok:true,status:200,json:async()=>input.value})};
vm.runInNewContext(fs.readFileSync(input.js,'utf8'),{window:win,Promise,Error,Number,Date,Set,Uint8Array});
let rows=[],states=[];
const ui=win.createGovernmentRevenueProgramDossier({
obj:v=>v!==null&&typeof v==='object'&&!Array.isArray(v),arr:v=>Array.isArray(v)?v:[],
text:(v,f='')=>v==null?f:String(v),esc:v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
tr:(en,zh)=>input.lang==='zh'?zh:en,host:()=>host,onRows:(r,s)=>{rows=r;states.push(s.status)}});
ui.load().then(()=>{if(rows.length)ui.render(rows[0]);process.stdout.write(JSON.stringify({state:ui.state(),rows:rows.length,html:host.innerHTML,states}))}).catch(e=>{console.error(e);process.exit(1)});
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps(dict(value=value,lang=lang,crypto=crypto,js=str(ROOT/"templates/government-revenue-dossiers.js"))), text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_valid_oversight_and_capacity_render_in_existing_six_question_factory(lang):
    out=run(bundle(),lang)
    assert out["state"]=="ok" and out["rows"]==1
    html=out["html"]
    for token in ["SYN-2026-100", "First edition", "2026-07-15", "Fiscal year 2026 site observations", "2026-08-22T08:00:00+00:00", "Page 14", "2000", "Reported program cost grew"]:
        assert token in html
    for token in (["Public oversight", "Original source text", "Published", "Observed period", "Known at", "Open report", "legal verdict"] if lang=="en" else ["公开监督", "来源原文", "发布日期", "观测期间", "已知时间", "打开报告", "法律裁决"]):
        assert token in html
    assert "#page=14" in html and "<details" in html
    assert html.count('class="inspect-section"')==8
    assert "assessment: not yet on file" not in html


@pytest.mark.parametrize("kind", sorted(po.PUBLIC_OVERSIGHT_FINDING_KINDS))
@pytest.mark.parametrize("reporter", sorted(po.PUBLIC_OVERSIGHT_REPORTER_ENUM))
def test_each_kind_and_reporter_uses_the_actual_contract(kind,reporter):
    g=oversight_graph();g["public_oversight_assertions"]=[assertion(g,finding_kind=kind,reported_by=reporter)]
    assert run(dossier(g))["state"]=="ok"


@pytest.mark.parametrize("field,value", [("page",0),("page",True),("revision",0),("finding_kind","readiness"),("reported_by","model"),
("source_url","javascript:alert(1)"),("source_url","https://user:secret@example.com"),("source_url",None),("sha256",None),
("sha256","x"*64),("excerpt_sha256","0"*64),("excerpt","Altered excerpt"),("program_id","acq-program:foreign"),
("known_at","2030-01-01T00:00:00+00:00"),("valid_from","2030-01-01T00:00:00+00:00"),("valid_to","2026-08-22T00:00:00+00:00"),
("published_on","2026-02-31"),("known_at","2026-08-22T24:00:00+00:00"),("evidence_refs",[]),("summary",""),("predecessor_id","wrong"),
("verification_state","proposed"),("id","prog-oversight:"+"f"*24)])
def test_invalid_or_rehashed_payload_fails_before_rows(field,value):
    x=bundle();x["dossiers"][0]["public_oversight"]["rows"][0][field]=value
    x["content_id"]=pd.dossier_content_id(x)
    out=run(x);assert out["state"]=="invalid" and out["rows"]==0 and not out["html"]


@pytest.mark.parametrize("change", ["unknown_row", "unknown_rail", "missing_rail", "duplicate", "false_reviewed", "legacy_rail", "old_capacity", "future_review", "rows_conflicted", "identity_unreviewed"])
def test_bundle_cross_field_failures(change):
    x=bundle();d=x["dossiers"][0];r=d["public_oversight"]
    if change=="unknown_row":r["rows"][0]["readiness_score"]=1
    elif change=="unknown_rail":r["legal_verdict"]="favorable"
    elif change=="missing_rail":del d["public_oversight"]
    elif change=="duplicate":r["rows"].append(deepcopy(r["rows"][0]))
    elif change=="false_reviewed":r["rows"]=[]
    elif change=="legacy_rail":x["schema_version"]="1.1.0"
    elif change=="old_capacity":del d["public_capacity"]
    elif change=="future_review":r.update(state="reviewed_none",rows=[],reviewed_at="2030-01-01T00:00:00+00:00")
    elif change=="rows_conflicted":r["state"]="conflicted"
    else:d["program_identity"]["state"]="not_reviewed"
    assert run(x)["state"]=="invalid"


@pytest.mark.parametrize("state", ["not_reviewed","reviewed_none","conflicted"])
@pytest.mark.parametrize("lang", ["en","zh"])
def test_typed_empty_states_are_not_no_issues(state,lang):
    x=bundle();r=x["dossiers"][0]["public_oversight"];r.update(state=state,rows=[],reviewed_at="2026-08-22T08:00:00+00:00" if state=="reviewed_none" else None)
    out=run(x,lang);assert out["state"]=="ok" and "Reported program cost grew" not in out["html"]
    expected=({"not_reviewed":"not yet reviewed","reviewed_none":"no admissible","conflicted":"Conflicting"} if lang=="en" else {"not_reviewed":"尚未复核","reviewed_none":"无可采信","conflicted":"冲突"})
    assert expected[state] in out["html"]


def test_crypto_absence_fails_closed_only_for_new_quoted_rail():
    assert run(bundle(),crypto=False)["state"]=="invalid"
    old=json.loads((ROOT/"tests/defense_o2_source_contracts/fixtures/program_dossier.json").read_text())
    assert run(old,crypto=False)["state"]=="ok"


def test_escaped_source_text_retains_unicode_digest():
    g=oversight_graph();g["public_oversight_assertions"]=[assertion(g,summary='<img src=x onerror="alert(1)">',excerpt='原文 “quoted” <script>alert(2)</script>')]
    out=run(dossier(g),"zh");assert out["state"]=="ok"
    assert "<img" not in out["html"] and "<script>" not in out["html"]
    assert "&lt;img" in out["html"] and "&lt;script&gt;" in out["html"]


@pytest.mark.parametrize("field,value", [("known_at","2030-01-01T00:00:00+00:00"),("valid_from","2030-01-01T00:00:00+00:00"),("valid_to","2026-08-22T00:00:00+00:00"),("published_on","2030-01-01"),("finding_kind","readiness"),("page",0),("program_id","acq-program:foreign"),("verification_state","proposed")])
def test_semantic_refusal_survives_recomputed_assertion_and_bundle_ids(field,value):
    x=bundle();row=x["dossiers"][0]["public_oversight"]["rows"][0];row[field]=value
    row["id"]=po.public_oversight_assertion_id(row);x["content_id"]=pd.dossier_content_id(x)
    out=run(x);assert out["state"]=="invalid" and out["rows"]==0
