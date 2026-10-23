#!/usr/bin/env python3
"""Artifact-only verifier for the fixed 18 raw cross-sectional IC expectations."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path

PROTOCOL="67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68"
MANIFEST="6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc"
RAW_WITNESS="4997a67e0b9ad64f303faa187500ffc40b2639879fe580633c5917d6af06218b"
RESULT="7af1b1ae1c871892384388695d17977cea1a6b6aa4fd21fc1625b5dad55073f3"
RAW_SCRIPT="44c007947405ef7b0fd0cd5a94a76aefa667af20d148a8bdcfe8643a1274579a"
ARITH_SCRIPT="8b4cec9743c8562c51d634d004d87457e3d9617ca0db3d65ad1ddb16a5f381ba"

def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def era(day: str) -> str: return "Era1" if day < "2020-01-01" else "Era2" if day < "2023-01-01" else "Era3"
def main():
 p=argparse.ArgumentParser(); p.add_argument("--result",type=Path,required=True);p.add_argument("--witness",type=Path,required=True);p.add_argument("--raw-script",type=Path,required=True);p.add_argument("--arithmetic-script",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
 if a.out.exists(): raise FileExistsError(a.out)
 hs={"result_sha256":sha(a.result),"raw_ic_witness_sha256":sha(a.witness),"raw_ic_script_sha256":sha(a.raw_script),"arithmetic_witness_script_sha256":sha(a.arithmetic_script)}
 if hs["raw_ic_witness_sha256"]!=RAW_WITNESS or hs["result_sha256"]!=RESULT or hs["raw_ic_script_sha256"]!=RAW_SCRIPT or hs["arithmetic_witness_script_sha256"]!=ARITH_SCRIPT: raise ValueError("unexpected bound artifact")
 r=json.loads(a.result.read_text()); w=json.loads(a.witness.read_text())
 if r.get("protocol_sha256")!=PROTOCOL or r.get("manifest_sha256")!=MANIFEST or w.get("frozen_manifest_sha256")!=MANIFEST: raise ValueError("protocol/manifest mismatch")
 if len(r.get("cells",[]))!=60 or len(w.get("expected_ic_cells",[]))!=18: raise ValueError("unexpected registered or witness cell count")
 by={(c["contrast"],c["era"],c["horizon"]):c for c in r["cells"]}; checks=[]
 for e in w["expected_ic_cells"]:
  cell=by.get((e["contrast"],era(e["date"]),e["horizon"])); row=next((x for x in (cell or {}).get("ic_series",[]) if x["date"]==e["date"]),None)
  ok=bool(cell and row and e["reason"] is None and row["n_roots"]==e["n_roots"] and math.isclose(row["ic"],e["expected_ic"],rel_tol=0.0,abs_tol=1e-12))
  checks.append({"date":e["date"],"contrast":e["contrast"],"horizon":e["horizon"],"match":ok,"n_roots_match":bool(row and row["n_roots"]==e["n_roots"])})
 out={**hs,"comparison_script_sha256":sha(Path(__file__)),"result_protocol_sha256":r["protocol_sha256"],"result_manifest_sha256":r["manifest_sha256"],"witness_manifest_sha256":w["frozen_manifest_sha256"],"witness_source_head":w.get("source_head"),"checked_cells":checks,"all_18_ic_and_nroots_match":all(x["match"] for x in checks)}
 if not out["all_18_ic_and_nroots_match"]: raise ValueError("raw IC mismatch")
 a.out.write_text(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__": main()
