"""Emit twelve direct file hashes from an explicitly qualified follow-on commit.

This offline binding neither qualifies source nor connects to production.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from followon_adoption_probe import FILES, LIMIT


def bind(repo, revision):
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("explicit full source commit required")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], timeout=30,
                                       stderr=subprocess.DEVNULL)

    if git("rev-parse", "--verify", revision + "^{commit}").decode().strip() != revision:
        raise ValueError("source commit mismatch")
    files = {}
    for name in FILES:
        metadata, actual_name = git("ls-tree", revision, "--", name).decode().strip().split("\t", 1)
        mode, kind, oid = metadata.split()
        if actual_name != name or mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("source must be a regular Git blob")
        size = int(git("cat-file", "-s", oid))
        if not 0 < size <= LIMIT:
            raise ValueError("source exceeds read bound")
        data = git("cat-file", "blob", oid)
        if len(data) != size:
            raise ValueError("source size mismatch")
        files[name] = hashlib.sha256(data).hexdigest()
    return {"schema": "eval_os.followon_probe_binding.v1", "source_commit": revision, "files": files}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = bind(args.repo, args.source_commit)
    with args.destination.open("x") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
