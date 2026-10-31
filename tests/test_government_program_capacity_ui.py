"""Execute the real dossier consumer: literal disclosures, no invented capacity."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from engine.government_revenue import program_dossier as pd
from engine.government_revenue import program_ontology as po

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "templates/government-revenue-dossiers.js"
FIXTURE = ROOT / "tests/defense_o2_source_contracts/fixtures/program_dossier.json"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node runtime unavailable")


def bundle():
    out = json.loads(FIXTURE.read_text())
    out["schema_version"] = "1.1.0"
    out["dossiers"] = out["dossiers"][:1]
    d = out["dossiers"][0]
    rows = []
    for kind, quantity, unit, scope, label, period in [
        ("announced_target", 2000, "units_per_year", "whole_program", "Whole product", "Target within seven years"),
        ("installed_capacity", 600, "units_per_year", "whole_program", "Whole product", "Disclosed installed annual capacity"),
        ("demonstrated_throughput", 620, "units", "whole_program", "Whole product", "Delivered during 2025"),
        ("announced_target", 3, "relative_multiplier", "component", "Example seeker", "Target within seven years"),
    ]:
        row = dict(revision=1, program_id=d["program_id"], product_scope=scope, product_label=label,
            entity_id="legal:example:manufacturer", kind=kind, quantity=quantity, unit=unit,
            comparator="approximately", period_label=period, known_at="2026-08-22T08:00:00+00:00",
            valid_from="2026-08-22T00:00:00+00:00", valid_to=None, verification_state="reviewed",
            evidence_refs=["ev:0c5a1e7e1772"], predecessor_id=None, succession_reason=None)
        row["id"] = po.public_capacity_assertion_id(row)
        rows.append(row)
    d["public_capacity"] = dict(state="reviewed", reviewed_at=None,
        **{kind:[r for r in rows if r["kind"] == kind] for kind in po.PUBLIC_CAPACITY_KINDS})
    out["content_id"] = pd.dossier_content_id(out)
    assert pd.is_valid_program_dossier_payload(out)
    return out


def run(payload, lang="en", status=200):
    script = r'''
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),host={innerHTML:'',className:''};
const win={fetch:async()=>({ok:input.status===200,status:input.status,json:async()=>input.payload})};
vm.runInNewContext(fs.readFileSync(input.js,'utf8'),{window:win,Promise,Error,Number,Date,Set});
const states=[];let rows=[],mobile=[];
const ui=win.createGovernmentRevenueProgramDossier({
 obj:v=>v!==null&&typeof v==='object'&&!Array.isArray(v),arr:v=>Array.isArray(v)?v:[],
 text:(v,f='')=>v===null||v===undefined?f:String(v),
 esc:v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 tr:(en,zh)=>input.lang==='zh'?zh:en,host:()=>host,
 onRows:(r,s)=>{rows=r;states.push(s.status)},setMobile:(...args)=>{mobile=args}
});
ui.load().then(()=>{if(rows.length)ui.render(rows[0]);process.stdout.write(JSON.stringify({state:ui.state(),rows:rows.length,html:host.innerHTML,states,mobile}))}).catch(e=>{console.error(e);process.exit(1)});
'''
    proc = subprocess.run(["node", "-e", script], input=json.dumps(dict(payload=payload, lang=lang, status=status, js=str(JS))).replace(": Infinity", ": 1e400"),
                          text=True, capture_output=True, check=True)
    return json.loads(proc.stdout)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_real_factory_renders_literal_native_units_and_separate_observations(lang):
    out = run(bundle(), lang)
    assert out["state"] == "ok" and out["rows"] == 1
    html = out["html"]
    for value in ("2000", "600", "620", "Example seeker", "Delivered during 2025", "2026-08-22T08:00:00+00:00", "ev:0c5a1e7e1772"):
        assert value in html
    labels = ["Announced target", "Installed capacity", "Demonstrated throughput", "Component", "relative multiple", "cannot be added together"] if lang == "en" else ["公布目标", "已建产能", "已实现产出", "零部件", "相对倍数", "不能相加"]
    assert all(label in html for label in labels)
    assert "6600" not in html and "2620" not in html
    assert html.count('class="inspect-section"') == 8  # six questions + identity + existing limitations
    assert out["mobile"]


def test_legacy_bundle_keeps_the_six_questions_and_no_capacity_rail():
    out = run(json.loads(FIXTURE.read_text()))
    assert out["state"] == "ok"
    assert "Public production disclosures" not in out["html"]
    assert "Quantity is not representable from the award tape" in out["html"]
    assert "not a share of revenue" in out["html"]


@pytest.mark.parametrize("state,copy", [("not_reviewed", "not yet reviewed"), ("reviewed_none", "no admissible public production disclosures"), ("conflicted", "quantities withheld")])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_explicit_degraded_states_do_not_show_zero_or_stale_quantities(state, copy, lang):
    value = bundle(); rail = value["dossiers"][0]["public_capacity"]
    rail.update(state=state, **{kind:[] for kind in po.PUBLIC_CAPACITY_KINDS})
    if state == "reviewed_none": rail["reviewed_at"] = "2026-08-23T08:00:00+00:00"
    out = run(value, lang)
    assert out["state"] == "ok"
    if lang == "en": assert copy in out["html"]
    else: assert {"not_reviewed":"尚未复核", "reviewed_none":"无可采信", "conflicted":"暂不显示数量"}[state] in out["html"]
    assert "2000" not in out["html"] and "0 units" not in out["html"]


def test_empty_category_is_not_inferred_from_other_category():
    value = bundle(); value["dossiers"][0]["public_capacity"]["installed_capacity"] = []
    out = run(value)
    assert out["state"] == "ok" and "No reviewed observation in this category" in out["html"]
    assert "600 units per year" not in out["html"]


def test_source_labels_are_escaped():
    value = bundle(); row = value["dossiers"][0]["public_capacity"]["announced_target"][0]
    row.update(product_label='<img src=x onerror="alert(1)">', period_label='<script>alert(2)</script>', entity_id='<svg onload="alert(3)">')
    out = run(value)
    assert out["state"] == "ok"
    assert "<img" not in out["html"] and "<script>" not in out["html"] and "<svg" not in out["html"]
    assert "&lt;img" in out["html"] and "&lt;script&gt;" in out["html"]


@pytest.mark.parametrize("field,value", [("quantity",0),("quantity",-1),("quantity",True),("quantity","2000"),
    ("unit","USD"),("verification_state","proposed"),("program_id","acq-program:other"),
    ("known_at","2030-01-01T00:00:00+00:00"),("valid_from","2030-01-01T00:00:00+00:00"),
    ("valid_to","2026-08-23T00:00:00+00:00"),("known_at","2026-02-31T00:00:00+00:00"),
    ("product_scope","inferred"),("evidence_refs",[]),("period_label",None),("kind","installed_capacity"),
    ("known_at","2026-08-22T24:00:00+00:00"),("known_at","2026-08-22T08:00:00Z"),("revision",True),("id","__proto__"),("comparator","at_least"),("predecessor_id",[]),
    ("valid_to","2026-08-21T00:00:00+00:00")])
def test_malformed_or_temporally_invalid_observations_refuse(field, value):
    payload = bundle(); payload["dossiers"][0]["public_capacity"]["announced_target"][0][field] = value
    out = run(payload)
    assert out["state"] == "invalid" and out["rows"] == 0 and not out["html"]


@pytest.mark.parametrize("mutation", ["missing_rail", "missing_bucket", "false_reviewed", "conflicted_rows", "duplicate", "unknown_version", "old_version_capacity", "foreign_field", "bad_kind_unit", "future_review", "array_rail", "nonfinite"])
def test_bundle_and_cross_bucket_controls_refuse(mutation):
    value = bundle(); d = value["dossiers"][0]; rail = d["public_capacity"]
    if mutation == "missing_rail": del d["public_capacity"]
    elif mutation == "missing_bucket": del rail["installed_capacity"]
    elif mutation == "false_reviewed": rail.update(**{kind:[] for kind in po.PUBLIC_CAPACITY_KINDS})
    elif mutation == "conflicted_rows": rail["state"] = "conflicted"
    elif mutation == "duplicate": rail["announced_target"].append(deepcopy(rail["announced_target"][0]))
    elif mutation == "unknown_version": value["schema_version"] = "1.9.0"
    elif mutation == "old_version_capacity": value["schema_version"] = "1.0.0"
    elif mutation == "foreign_field": rail["announced_target"][0]["revenue"] = 100
    elif mutation == "bad_kind_unit": rail["installed_capacity"][0]["unit"] = "relative_multiplier"
    elif mutation == "future_review":
        rail.update(state="reviewed_none", reviewed_at="2030-01-01T00:00:00+00:00", **{kind:[] for kind in po.PUBLIC_CAPACITY_KINDS})
    elif mutation == "array_rail": d["public_capacity"] = []
    elif mutation == "nonfinite": rail["announced_target"][0]["quantity"] = float("inf")
    out = run(value)
    assert out["state"] == "invalid" and out["rows"] == 0


@pytest.mark.parametrize("status,state", [(401,"locked"),(403,"locked"),(500,"unavailable")])
def test_existing_auth_and_error_states_are_preserved(status,state):
    out = run(bundle(), status=status)
    assert out["state"] == state and not out["html"]
