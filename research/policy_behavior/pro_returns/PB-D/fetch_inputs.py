#!/usr/bin/env python3
"""Explicit, pinned public-GitHub input download; never executes downloaded code.

python fetch_inputs.py --output-dir ./inputs
Uses Python standard library. Existing matching files are reused, never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def validate(raw, source):
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if blob != source["git_blob"]:
        raise ValueError(f"Git blob mismatch for {source['id']}")
    sha = hashlib.sha256(raw).hexdigest()
    if source.get("sha256") and sha != source["sha256"]:
        raise ValueError(f"SHA256 mismatch for {source['id']}")
    return {"id": source["id"], "bytes": len(raw), "git_blob": blob, "sha256": sha}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads(Path(__file__).with_name("PB_D_PINNED_SOURCES.json").read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for source in manifest["sources"]:
        dest = args.output_dir / source["filename"]
        if dest.exists():
            raw = dest.read_bytes()
        else:
            with urllib.request.urlopen(source["url"], timeout=60) as response:
                raw = response.read()
            validate(raw, source)
            # Exclusive create also refuses a concurrent writer.
            with dest.open("xb") as output:
                output.write(raw)
        receipts.append(validate(raw, source))
    print(json.dumps({"status": "PINNED_INPUTS_VERIFIED", "receipts": receipts}, indent=2))


if __name__ == "__main__":
    main()
