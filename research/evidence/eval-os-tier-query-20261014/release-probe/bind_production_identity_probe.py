"""Bind the existing read-only probe to explicit Git bytes; never grant acceptance.

Run locally after independently qualifying the final source revision. This creates
a new probe and receipt, and neither connects to nor changes production.
"""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=30)


def bind(repo, revision, destination):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source revision must be an exact full commit SHA")
    resolved = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    if resolved != revision:
        raise ValueError("source revision does not identify that commit")
    template_path = Path(__file__).with_name("production_identity_probe.py")
    template = template_path.read_text()
    syntax = ast.parse(template)
    expected_node = next(n for n in syntax.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "EXPECTED"
                                 for t in n.targets))
    old_expected = ast.literal_eval(expected_node.value)
    if len(old_expected) != 17:
        raise ValueError("original 17-file probe contract changed; review required")
    expected = {}
    for name in old_expected:
        entry = git(repo, "ls-tree", revision, "--", name).decode().strip()
        metadata, actual_name = entry.split("\t", 1)
        mode, kind, oid = metadata.split()
        if actual_name != name or mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("expected source is not a regular Git blob")
        size = int(git(repo, "cat-file", "-s", oid))
        if not 0 < size <= 16 * 1024 * 1024:
            raise ValueError("source blob outside the probe size bound")
        data = git(repo, "cat-file", "blob", oid)
        if len(data) != size:
            raise ValueError("source blob size mismatch")
        expected[name] = hashlib.sha256(data).hexdigest()
    lines = template.splitlines(keepends=True)
    lines[expected_node.lineno - 1:expected_node.end_lineno] = ["EXPECTED = " + repr(expected) + "\n"]
    output = "".join(lines)
    old_identity = "'candidate':'05a75a4131f5e695a1d31616ac9e2ecca6059c67'"
    if output.count(old_identity) != 1:
        raise ValueError("original probe identity changed; review required")
    output = output.replace(old_identity, "'candidate':" + repr(revision))
    compile(output, "bound-production-identity-probe.py", "exec")
    receipt = {
        "schema": "eval_os.production_probe_source_binding.v1",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": revision,
        "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
        "probe_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "expected_source_hashes": expected,
        "changed_from_05a": [name for name in expected if expected[name] != old_expected[name]],
        "scope": "Source-byte binding only. Independent final-source qualification, merge, installation, API/render and owner-progression proofs remain required.",
    }
    destination.mkdir(exist_ok=False)
    (destination / "production_identity_probe.py").write_text(output)
    (destination / "source-binding.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = bind(args.repo, args.source_commit, args.destination)
    print(json.dumps({"source_commit": result["source_commit"],
                      "probe_sha256": result["probe_sha256"],
                      "changed_from_05a": result["changed_from_05a"],
                      "scope": result["scope"]}, indent=2))
