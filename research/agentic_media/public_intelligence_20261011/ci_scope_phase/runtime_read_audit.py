"""Bounded local diagnostic: record repository file paths opened by one rotation suite."""
import sys
import os
import json
import importlib.util
from pathlib import Path

suite = sys.argv[1]
assert suite in ("tests/test_rotation_evidence_modes.py", "tests/test_leadership_rotation_contract.py")
root = os.getcwd()
reads, writes = set(), set()

def audit(event, args):
    if event != "open" or not isinstance(args[0], (str, bytes)):
        return
    path = os.path.abspath(os.fsdecode(args[0]))
    if not path.startswith(root + "/"):
        return
    rel = os.path.relpath(path, root)
    if "__pycache__/" in rel:
        try:
            rel = importlib.util.source_from_cache(rel)
        except ValueError:
            return
    mode, flags = args[1] or "", args[2]
    target = writes if any(x in mode for x in "wax+") or flags & (os.O_WRONLY | os.O_RDWR) else reads
    target.add(rel)

sys.addaudithook(audit)
sys.path.insert(0, root)
import pytest
rc = pytest.main([suite, "-q", "-p", "no:cacheprovider", "--basetemp=" + sys.argv[3]])
Path(sys.argv[2]).write_text(json.dumps({"suite": suite, "exit_code": rc,
    "repo_reads": sorted(reads), "repo_writes": sorted(writes),
    "limit": "Observed file opens, not exhaustive proof of every possible read. No source contents recorded."}, indent=2) + "\n")
raise SystemExit(rc)
