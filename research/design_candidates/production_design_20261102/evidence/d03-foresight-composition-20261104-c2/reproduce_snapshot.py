"""Reconstruct the exact isolated T35/T36/T37 fixture from existing Git objects.

Read-only with respect to supplied repositories. No fetch, builders, live data,
branch writes, worktrees, install, services, or publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("t35", "t36", "t37"):
        ap.add_argument("--" + name + "-repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    proof = json.loads((here / "composition-proof.json").read_text())
    repos = {"T35": args.t35_repo.resolve(), "T36": args.t36_repo.resolve(),
             "T37": args.t37_repo.resolve()}
    refs = proof["source_commits"]
    by_commit = {refs[name]: repos[name] for name in refs}
    out = args.out.resolve()
    if out.exists():
        raise SystemExit("Use a new output directory; refusing to overwrite.")
    payloads = {}
    for item in proof["input_files"]:
        name = Path(item["path"])
        if name.is_absolute() or ".." in name.parts:
            raise SystemExit("Unsafe input path")
        repo = by_commit[item["commit"]]
        spec = item["commit"] + ":" + item["path"]
        blob = git(repo, "rev-parse", "--verify", spec).decode().strip()
        data = git(repo, "show", spec)
        assert blob == item["git_blob"], item["path"]
        assert sha(data) == item["sha256"], item["path"]
        payloads[item["path"]] = data
    template = "templates/foresight.html.j2"
    with tempfile.TemporaryDirectory(prefix="d03-compose-reproduce-") as td:
        d = Path(td)
        for name in refs:
            (d / name).write_bytes(git(repos[name], "show", refs[name] + ":" + template))
        base_spec = proof["base_commit"] + ":" + template
        assert git(repos["T36"], "rev-parse", base_spec).decode().strip() == proof["common_template_git_blob"]
        (d / "base").write_bytes(git(repos["T36"], "show", base_spec))
        first = subprocess.run(["git", "merge-file", "--stdout", "--diff3",
                                str(d/"T36"), str(d/"base"), str(d/"T35")],
                               check=True, capture_output=True).stdout
        (d / "T35_T36").write_bytes(first)
        combined = subprocess.run(["git", "merge-file", "--stdout", "--diff3",
                                   str(d/"T35_T36"), str(d/"base"), str(d/"T37")],
                                  check=True, capture_output=True).stdout
    assert sha(combined) == proof["composed_template_sha256"]
    assert combined == (here / "composed-foresight.html.j2").read_bytes()
    payloads[template] = combined
    out.mkdir(parents=True)
    for path, data in payloads.items():
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(json.dumps({"result":"PASS","input_files":len(proof["input_files"]),
                      "files_materialized":len(payloads),
                      "composed_template_sha256":sha(combined),
                      "repositories_modified":False,"output":str(out)}))

if __name__ == "__main__":
    main()
