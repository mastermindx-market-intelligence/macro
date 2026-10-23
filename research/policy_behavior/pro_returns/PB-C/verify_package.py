#!/usr/bin/env python3
"""Check the frozen package file inventory; no network or production effects."""
import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
manifest=json.loads((p/'PACKAGE_SHA256.json').read_text())
bad=[]
for name,want in manifest['files'].items():
 f=p/name
 if not f.is_file():bad.append({'file':name,'error':'missing'});continue
 got=hashlib.sha256(f.read_bytes()).hexdigest()
 if got!=want:bad.append({'file':name,'error':'digest_mismatch','expected':want,'actual':got})
print(json.dumps({'files_checked':len(manifest['files']),'passed':not bad,'errors':bad},indent=2))
raise SystemExit(1 if bad else 0)
