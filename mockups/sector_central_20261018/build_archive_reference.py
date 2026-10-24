#!/usr/bin/env python3
"""Review-only field projection of the immutable R3 archive; no computation."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FIX=ROOT/"research/reference_integrity/mastermind-xpv2-sector-r3/fixture"
CAPTURE="4c55fe433490adfd75fd901ef25f5793db2202db"
manifest_path=FIX/"receipts.json"
manifest_raw=manifest_path.read_bytes()
manifest=json.loads(manifest_raw)
if manifest["captured_commit"] != CAPTURE:
    raise ValueError("Archive capture no longer matches this reference contract.")
manifest_entries={entry["path"]:entry for entry in manifest["entries"]}
receipts=[]
def read(name):
    path=FIX/name
    raw=path.read_bytes()
    actual_hash=hashlib.sha256(raw).hexdigest()
    receipt=manifest_entries.get(name)
    if receipt is None or actual_hash != receipt["sha256"] or len(raw) != receipt["size_bytes"]:
        raise ValueError(f"Retained archive receipt mismatch: {name}")
    receipts.append({"path":str(path.relative_to(ROOT)),"sha256":actual_hash,"capture_commit":CAPTURE})
    return json.loads(raw)
def pick(row,keys):
    return {key:row[key] for key in keys if key in row}
rotation=read("marketdata/subsector_rotation.json")
fields=["key","name","name_zh","theme","theme_zh","quadrant","rs_ratio","rs_mom","rs","perf","turn_state","turn_label","turn_label_zh","turn_since","turn_age","turn_say","turn_say_zh"]
rot=pick(rotation,["asof","generated_utc","source","timeframes","mom_horizons","n_subsectors","n_themes","n_sectors","themes_unit"])
for universe in ["sectors","subsectors","themes"]:
    rot[universe]=[pick(row,fields) for row in rotation[universe]]
handoff=read("basketdata/si_handoff.json")
baskets=read("basketdata/baskets.json")
confluence={}
for namespace,filename,key in [
    ("sp500","subsector_confluence.json","subsectors"),
    ("nasdaq","subsector_confluence_nasdaq.json","subsectors"),
    ("russell","subsector_confluence_russell.json","subsectors"),
    ("baskets","basket_confluence.json","baskets")
]:
    original=read("marketdata/"+filename)
    projected=pick(original,["universe","as_of","generated_utc","coverage","weighting","notes"])
    projected["groups_key"]=key
    projected["groups"]=[pick(row,["key","basket_id","kind","label","label_zh","sector","sector_zh","n_members","n_priced","reliability","class","entry","regime","chart_key"]) for row in original[key]]
    confluence[namespace]=projected
bundle={
    "reference_only":True,"live":False,
    "capture_commit":CAPTURE,"capture_date":"2026-08-20",
    "projection_rule":"Field selection only. Original array order, values, nulls and source clocks preserved. No membership, new scores or admission state.",
    "rotation":rot,
    "money":{"flow":handoff.get("flow"),"generated_utc":handoff.get("generated_utc"),"as_of":baskets.get("as_of"),"market_concentration":baskets.get("theme_intel",{}).get("market_concentration")},
    "confluence":confluence,
    "sources":receipts,
    "source_manifest":{"path":str(manifest_path.relative_to(ROOT)),"sha256":hashlib.sha256(manifest_raw).hexdigest(),"all_projected_sources_verified":True}
}
target=HERE/"archive_sources.json"
target.write_text(json.dumps(bundle,ensure_ascii=False,separators=(",",":"))+"\n")
print(json.dumps({"artifact":str(target.relative_to(ROOT)),"bytes":target.stat().st_size,"capture_commit":CAPTURE,"rotation_counts":{k:len(rot[k]) for k in ["sectors","subsectors","themes"]},"confluence_counts":{k:len(v["groups"]) for k,v in confluence.items()},"source_count":len(receipts),"live":False}))
