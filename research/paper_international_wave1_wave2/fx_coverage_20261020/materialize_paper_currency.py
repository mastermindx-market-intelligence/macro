"""Materialize native Paper responses and verify the exact observed currency nodes."""
import base64
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
source_path = OUT/"paper_native_capture_bundle.json"
source_bytes = source_path.read_bytes()
bundle = json.loads(source_bytes)
artifacts = []
def bind(path):
    data = path.read_bytes()
    return {"path":str(path.relative_to(ROOT)), "sha256":sha256(data).hexdigest(), "bytes":len(data)}
def decode(raw):
    value = raw.get("structuredContent")
    if isinstance(value,dict) and "content" in value:
        value = value["content"]
    if value is None:
        value = "\n".join(c["text"] for c in raw.get("content",[]) if c["type"]=="text")
    return json.loads(value) if isinstance(value,str) else value
def jsx(raw):
    data = decode(raw)
    assert data["state"] == "OBSERVED"
    items = [c["text"] for c in data["result"]["content"] if c["type"]=="text"]
    code = next(text for text in items if text.strip().startswith("("))
    return code
def images(raw, stem):
    assert decode(raw)["state"] == "OBSERVED"
    blocks = [c for c in raw["content"] if c["type"]=="image"]
    assert len(blocks) == 1 and blocks[0]["mimeType"] == "image/jpeg"
    data = base64.b64decode(blocks[0]["data"],validate=True)
    assert data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
    path = OUT/(stem+".jpg")
    path.write_bytes(data)
    artifacts.append({**bind(path),"origin":"original native MCP image bytes; no image transformation"})
all_jsx = {}
for board, values in bundle["boards"].items():
    for state in ("before","readback"):
        code = jsx(values[state])
        path = OUT/(f"paper_{board}"+("_before" if state=="before" else "")+".jsx")
        path.write_text(code)
        artifacts.append(bind(path))
        if state=="readback":
            all_jsx[board]=code
    images(values["screenshot"],"paper_"+board)
for node, raw in bundle["tiles"].items():
    images(raw,"paper_currency_"+node)
combined = "\n".join(all_jsx.values())
def node(node_id):
    matches = re.findall(r'<div id="'+re.escape(node_id)+r'" style=\{\{(.*?)\}\}>\s*(.*?)\s*</div>',combined,re.S)
    assert len(matches)==1, node_id
    return matches[0]
text_checks=[]
for expected in bundle["expected_text"]:
    styles, markup = node(expected["nodeId"])
    actual = re.sub(r"<br\s*/?>","\n",markup).strip()
    text_checks.append({"node_id":expected["nodeId"],"expected":expected["textContent"],
                        "actual":actual,"passed":actual==expected["textContent"]})
style_checks=[]
for node_id, expected in {
    "DSP-0":"var(--mx-dark-up)","E8Y-0":"var(--mx-dark-up)",
    "E05-0":"var(--mx-light-ink-up)","EG0-0":"var(--mx-light-ink-up)",
}.items():
    styles,_=node(node_id)
    style_checks.append({"node_id":node_id,"property":"color","expected":expected,
                         "passed":f"color: '{expected}'" in styles})
for node_id in ("EYX-0","EYY-0","EYZ-0","EZ0-0"):
    styles,_=node(node_id)
    for prop,value in (("fontSize","var(--fs-micro)"),("lineHeight","12px")):
        style_checks.append({"node_id":node_id,"property":prop,"expected_observed":value,
                             "passed":f"{prop}: '{value}'" in styles})
orders=[]
for board, ids in {
    "DMX-0":("DSO-0","DSP-0","EYX-0"), "DW7-0":("E06-0","E05-0","EYY-0"),
    "E4D-0":("E8Z-0","E8Y-0","EYZ-0"), "EC2-0":("EG1-0","EG0-0","EZ0-0"),
}.items():
    offsets=[all_jsx[board].index('id="'+node_id+'"') for node_id in ids]
    orders.append({"board":board,"ids":ids,"passed":offsets==sorted(offsets)})
verification={
    "schema":"mastermind.intl_currency_paper_readback.v1",
    "materialized_at":datetime.now(timezone.utc).isoformat(),
    "text_count":len(text_checks),"text_passed":sum(r["passed"] for r in text_checks),
    "style_count":len(style_checks),"style_passed":sum(r["passed"] for r in style_checks),
    "order_count":len(orders),"order_passed":sum(r["passed"] for r in orders),
    "text_checks":text_checks,"style_checks":style_checks,"order_checks":orders,
    "native_normalization":bundle["note"],
}
assert verification["text_passed"]==20 and verification["style_passed"]==12 and verification["order_passed"]==4
for board,code in all_jsx.items():
    assert "Market observations" not in code and "19 OCT 2026" not in code
    assert "Information through 30 Sep" in code
for name in ("01_duplicate_dates","02_text","03_styles","04_order","05_names","06_finish"):
    effect=json.loads((OUT/("paper_effect_"+name+".json")).read_text())
    assert decode(effect["response"])["state"]=="APPLIED_RESPONSE_OBSERVED"
(OUT/"paper_final_readback_verification.json").write_text(json.dumps(verification,indent=2)+"\n")
archive=source_path.with_suffix(".json.gz")
archive.write_bytes(gzip.compress(source_bytes,mtime=0))
assert gzip.decompress(archive.read_bytes())==source_bytes
materialized={"schema":"mastermind.intl_currency_paper_materialization.v1",
              "materialized_at":datetime.now(timezone.utc).isoformat(),
              "native_bundle":bind(archive),"decompressed_sha256":sha256(source_bytes).hexdigest(),
              "artifacts":artifacts,"readback":bind(OUT/"paper_final_readback_verification.json")}
(OUT/"paper_capture_materialization.json").write_text(json.dumps(materialized,indent=2)+"\n")
source_path.unlink()
print(json.dumps({"artifacts":len(artifacts),"text_passed":20,"style_passed":12,"order_passed":4,
                  "native_bundle":materialized["native_bundle"]}))
