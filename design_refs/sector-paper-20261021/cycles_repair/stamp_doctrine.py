#!/usr/bin/env python3
"""Stamp the producer doctrine fields into example_dataset.json (SIC-ADJ-01 / SIC-V3-C01).

The specimen never computes a stance. For every sector `now` block this script writes
doctrine_stance / doctrine_stance_en / doctrine_stance_zh / doctrine_ink exactly as
engine.cycle_ontology.doctrine_for(now.stance) returns them (DOCTRINE_STANCE :147,
doctrine_for :179; the ink is asserted never to contradict the engine tone, :164-176).
A missing stance writes null fields (SIC-V3-C02: the map has no None entry). The edit is
textual (file formatting preserved) and idempotent. It also inserts, once, the labeled
_fixtures.prior_cell shape (SIC-V3-C17; shape per engine/hazard_score.py:432-436).
Run:  python3 stamp_doctrine.py
"""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent))
from engine.cycle_ontology import doctrine_for  # noqa: E402

P = HERE / "example_dataset.json"
lines = P.read_text(encoding="utf-8").split("\n")
out, i, n_st = [], 0, 0
while i < len(lines):
    l = lines[i]; out.append(l)
    m = re.match(r'^(\s*)"stance_zh": (".*?"|null),?$', l)
    if m:
        ind = m.group(1); i += 1
        while i < len(lines) and re.match(r'^\s*"doctrine_', lines[i]):
            i += 1  # idempotent: drop a previous stamp
        st = None
        for b in range(len(out) - 1, max(0, len(out) - 12), -1):
            mm = re.match(r'^\s*"stance": (".*?"|null),?$', out[b])
            if mm:
                st = None if mm.group(1) == "null" else json.loads(mm.group(1)); break
        d = doctrine_for(st) if st else None
        if not out[-1].rstrip().endswith(","): out[-1] = out[-1].rstrip() + ","
        for k in ("doctrine_stance", "doctrine_stance_en", "doctrine_stance_zh", "doctrine_ink"):
            out.append(f'{ind}"{k}": {json.dumps(d[k] if d else None, ensure_ascii=False)},')
        n_st += 1; continue
    i += 1
t = "\n".join(out)
if '"doctrine_stamp"' not in t:
    t = t.replace('  "asOf": "2026-10-20",', '  "asOf": "2026-10-20",\n  "doctrine_stamp": {"engine": "engine/cycle_ontology.py", "map": "DOCTRINE_STANCE (:147)", "fn": "doctrine_for (:179)", "stamped_by": "design_refs/sector-paper-20261021/cycles_repair/stamp_doctrine.py"},', 1)
if '"prior_cell"' not in t:
    fx = '''  "prior_cell": {
   "label": "FIXTURE",
   "note": "Not a live sector. Producer field shape of a hazard horizon that fell back to the KM prior (engine/hazard_score.py:436: source PRIOR, cell_verdict PRIOR); the historical up/3m and up/6m PRIOR cells (W4.2) have this shape. p values are illustrative; the shape is the contract.",
   "shape_source": "engine/hazard_score.py:432-436",
   "name": "Fixture sector",
   "name_zh": "示例板块",
   "ticker": "FIX",
   "hazard": {
    "epoch": "price_c4414dcb",
    "revision_optimistic": true,
    "direction": "up",
    "turn_kind": "peak",
    "1m": {"p": 0.2971, "source": "MODEL", "cell_verdict": "PASS"},
    "3m": {"p": 0.33, "source": "PRIOR", "cell_verdict": "PRIOR"},
    "6m": {"p": 0.5, "source": "PRIOR", "cell_verdict": "PRIOR"}
   }
  },
'''
    t = t.replace(' "_fixtures": {\n', ' "_fixtures": {\n' + fx, 1)
json.loads(t)  # must stay valid JSON
P.write_text(t, encoding="utf-8")
ds = json.loads(t)
print(f"stamped {n_st} sector now blocks; fixtures: {sorted(ds['_fixtures'])}; meta.doctrine_stamp: {'doctrine_stamp' in ds['meta']}")
for s in ds["sectors"]:
    n = s["now"]; print(f'  {s["ticker"]}: {n["stance"]} -> {n["doctrine_stance"]} / {n["doctrine_stance_en"]} / {n["doctrine_stance_zh"]} / ink {n["doctrine_ink"]}')
