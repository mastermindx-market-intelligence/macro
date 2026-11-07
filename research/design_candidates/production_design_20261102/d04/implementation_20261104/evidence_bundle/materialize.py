#!/usr/bin/env python3
"""Reconstruct the exact D04 packet from its pinned baseline and committed bundle."""
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import json

def stop(message):
    raise SystemExit(message)

def relative(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts or "\\" in value or str(p) != value:
        stop("Unsafe artifact path: " + repr(value))
    return p

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def validate(data, item, label):
    if len(data) != item["bytes"]:
        stop(label + ": byte length mismatch")
    if "sha256" in item and hashlib.sha256(data).hexdigest() != item["sha256"]:
        stop(label + ": SHA256 mismatch")
    expected = item.get("git_blob_sha", item.get("git_blob"))
    if expected and blob_sha(data) != expected:
        stop(label + ": Git blob mismatch")

def read_inside(root, rel):
    p = root / relative(rel)
    if p.is_symlink() or not p.is_file():
        stop(rel + ": missing regular file")
    if not p.resolve().is_relative_to(root.resolve()):
        stop(rel + ": path escapes source")
    return p.read_bytes()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path, help="Exact D04 directory exported from the manifest's base commit")
    parser.add_argument("--output", required=True, type=Path, help="New empty output directory; never overwrite an existing packet")
    parser.add_argument("--bundle-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.output.exists():
        stop("Output already exists; choose a new directory")
    manifest = json.loads((args.bundle_dir / "manifest.json").read_text())
    if manifest["format"] != "d04-artifact-bundle-v1":
        stop("Unsupported bundle format")
    base_expected = {f["path"]: f for f in manifest["base_files"]}
    actual_base = {str(p.relative_to(args.base)) for p in args.base.rglob("*") if p.is_file()}
    if actual_base != set(base_expected):
        stop("Baseline file set differs from the pinned export")
    packet = {}
    for rel, item in base_expected.items():
        data = read_inside(args.base, rel)
        validate(data, item, rel)
        packet[rel] = data
    changed = set()
    for index, part in enumerate(manifest["parts"], 1):
        raw = read_inside(args.bundle_dir, part["path"])
        validate(raw, part, part["path"])
        obj = json.loads(raw)
        if obj["format"] != "d04-artifact-bundle-part-v1" or obj["part"] != index:
            stop("Part identity/order mismatch")
        if len(obj["records"]) != part["records"]:
            stop("Part record count mismatch")
        for item in obj["records"]:
            rel = str(relative(item["path"]))
            if rel in changed:
                stop("Duplicate changed path: " + rel)
            changed.add(rel)
            if item["encoding"] == "utf-8":
                data = item["content"].encode("utf-8")
            elif item["encoding"] == "base64":
                data = base64.b64decode(item["content"], validate=True)
            else:
                stop("Unsupported encoding for " + rel)
            validate(data, item, rel)
            packet[rel] = data
    final_expected = {f["path"]: f for f in manifest["packet_files"]}
    if len(changed) != manifest["changed_artifacts"] or set(packet) != set(final_expected):
        stop("Final packet identity/count mismatch")
    for rel, data in packet.items():
        validate(data, final_expected[rel], rel)
    args.output.mkdir(parents=True)
    for rel, data in packet.items():
        p = args.output / relative(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    print(json.dumps({"status":"PASS","base_commit":manifest["base_commit"],
        "restored_files":len(packet),"changed_artifacts":len(changed),
        "verified_parts":len(manifest["parts"]),"output":str(args.output.resolve()),
        "qualification":"Byte-verified reconstruction; product tests and programme acceptance are separate."}))

if __name__ == "__main__":
    main()
