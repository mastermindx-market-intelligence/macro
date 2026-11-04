"""Bind currency design, final rendering and the incumbent local UI verification gates."""
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PYTHON = "/tmp/intl-country-cockpit-testenv-20261018/bin/python"
FROZEN_HEAD = "11c83bb5dfb0c8199a0fb0cb2c6e70452c724984"
def now():
    return datetime.now(timezone.utc).isoformat()
def bind(path):
    data=path.read_bytes()
    return {"path":str(path.relative_to(ROOT)),"sha256":sha256(data).hexdigest(),"bytes":len(data)}
def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
def decode(raw):
    value=raw.get("structuredContent")
    if isinstance(value,dict) and "content" in value:
        value=value["content"]
    if value is None:
        value="\n".join(c["text"] for c in raw["content"] if c["type"]=="text")
    return json.loads(value) if isinstance(value,str) else value

assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==FROZEN_HEAD
readback=json.loads((OUT/"paper_final_readback_verification.json").read_text())
assert readback["text_passed"]==20 and readback["style_passed"]==12 and readback["order_passed"]==4
effects=[]
for name in ("01_duplicate_dates","02_text","03_styles","04_order","05_names","06_finish"):
    path=OUT/("paper_effect_"+name+".json")
    record=json.loads(path.read_text())
    assert decode(record["response"])["state"]=="APPLIED_RESPONSE_OBSERVED"
    effects.append({**bind(path),"operation_id":record["request"]["operation_id"],"tool":record["request"]["tool"]})
parent=OUT.parent/"fiscal_coverage_20261019/paper_fiscal_coverage_receipt.json"
assert bind(parent)["sha256"]=="d2ddabaad3798809af2daccf0fc3beffa92422060d3741024dd9e6aa5a496231"
capture=json.loads((OUT/"paper_capture_materialization.json").read_text())
paper={
    "schema":"mastermind.intl_currency_paper_coverage_receipt.v1","recorded_at":now(),
    "file_id":"01M3P1TW5Y3XWQC37ADDS8K5AG","page_id":"p-G-0",
    "url":"https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0",
    "updated_boards":["DMX-0","DW7-0","E4D-0","EC2-0"],
    "unchanged_detail_boards_in_parent":["ER4-0","ER5-0"],"parent":bind(parent),
    "scope":"Korea currency value and dollar basis, separate FX/equity dates, and October20 overview reference date in both themes and widths.",
    "effects":effects,"effect_count_including_finish":6,"original_response_retained_count":6,
    "verification":{"text_nodes":20,"style_properties":12,"orders":4,"finished_boards":4,
                    "readback":bind(OUT/"paper_final_readback_verification.json")},
    "capture_materialization":bind(OUT/"paper_capture_materialization.json"),"artifacts":capture["artifacts"],
    "visual_review":{"reviewed":"Four focused native currency tiles, desktop-light and mobile-dark overviews; final HTML desktop and narrow/mobile market sections.",
                     "native_metrics":readback["native_normalization"],
                     "html_repair":"Market caption selectors now target direct labels, so translated trend values inherit their intended size and state color."},
    "limitations":["Native Paper screenshots are static design references; source links and interactions are verified separately in real Chrome.",
                   "Tall native boards are downscaled by Paper; original returned JPEG bytes are retained alongside JSX and focused captures.",
                   "Local and Paper proof do not establish canonical-store availability, hosted CI or production adoption."]
}
paper_path=OUT/"paper_currency_coverage_receipt.json"
if paper_path.exists():
    previous=json.loads(paper_path.read_text())
    assert {k:v for k,v in previous.items() if k!="recorded_at"} == {k:v for k,v in paper.items() if k!="recorded_at"}
else:
    write_json(paper_path,paper)
manifest_path=OUT/"preview/manifest.json"
manifest=json.loads(manifest_path.read_text())
original=OUT/"preview/manifest.render-original.json"
if not original.exists():
    original.write_bytes(manifest_path.read_bytes())
manifest["paper_design"].update({
    "receipt":"../paper_currency_coverage_receipt.json","receipt_sha256":bind(paper_path)["sha256"],
    "applied":True,"scope":"R12, policy and fiscal parents plus the bound currency increment. Real interactions are separately browser-tested."})
archives={}
for name,expected in manifest["html_sha256"].items():
    path=OUT/"preview"/name
    data=path.read_bytes()
    assert sha256(data).hexdigest()==expected
    archive=path.with_suffix(path.suffix+".gz")
    archive.write_bytes(gzip.compress(data,mtime=0))
    assert gzip.decompress(archive.read_bytes())==data
    archives[name]={**bind(archive),"decompressed_sha256":expected}
manifest["html_archives"]=archives
write_json(manifest_path,manifest)
browser=json.loads((OUT/"browser_verification.json").read_text())
assert browser["passed"]==browser["country_checks"]==84
assert browser["ageing_passed"]==len(browser["ageing_controls"])==8 and not browser["page_errors"]
assert browser["html_sha256"]==manifest["html_sha256"]["intl_integrated_preview.html"]
gates=OUT/"gates"; gates.mkdir(exist_ok=True)
diff=subprocess.check_output(["git","diff",FROZEN_HEAD,"--",
                              "templates/intl_country_cockpit.css","templates/intl_country_cockpit.html.j2"],cwd=ROOT)
diff_path=gates/"final_ui_delta.diff";diff_path.write_bytes(diff)
(gates/"final_ui_delta.diff.gz").write_bytes(gzip.compress(diff,mtime=0))
runs=[]
for name,command in [
    ("design",[PYTHON,"scripts/check_design_system.py","--mode","enforce-added","--diff-file",str(diff_path)]),
    ("visual",[PYTHON,"scripts/check_ui_visual_evidence.py","--diff-file",str(diff_path)]),
    ("tracked_whitespace",["git","diff","--check"]),
]:
    started=now();result=subprocess.run(command,cwd=ROOT,capture_output=True)
    path=gates/(name+".log");path.write_bytes(result.stdout+result.stderr)
    runs.append({"name":name,"command":command,"started_at":started,"finished_at":now(),
                 "exit_code":result.returncode,"log":bind(path)})
    print(json.dumps({"gate":name,"exit_code":result.returncode,"log":str(path.relative_to(ROOT))}),flush=True)
result={"recorded_at":now(),"frozen_head":FROZEN_HEAD,"paper_receipt":bind(paper_path),
        "preview_manifest":bind(manifest_path),"browser":bind(OUT/"browser_verification.json"),"gates":runs,
        "passed":all(r["exit_code"]==0 for r in runs)}
write_json(gates/"verification.json",result)
print(json.dumps({"passed":result["passed"],"paper_receipt":result["paper_receipt"],
                  "html_sha256":manifest["html_sha256"]}),flush=True)
raise SystemExit(0 if result["passed"] else 1)
