"""Compute hashes.txt: sha256 for every input file read + every output file written.

Run by run_all.py AFTER everything else, so the file hashes are stable.

F5: plain `<sha256>  <repo-relative path>` lines only. `repo_head` lives in result.json
(D5: it is not a file, so it has no hash). Manifest annotations stay in
`code/universe_manifest.json` (which is itself hashed); we do NOT duplicate them into
hashes.txt because the bare `shasum -c hashes.txt` MUST pass on the host.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out_lines = []

    # ---- INPUTS (read-only files we depend on) ----
    inputs = [
        REPO / "engine/canon.py",
        REPO / "engine/session_anchor.py",
        REPO / "engine/bar_derive.py",
        REPO / "data/yahoo/SPY.parquet",
    ]
    for p in inputs:
        if p.exists():
            out_lines.append(f"{sha256_path(p)}  {p.relative_to(REPO)}")

    # ---- OUTPUTS (files we wrote) ----
    outputs = [
        RESULTS_DIR / "events_panel.parquet",
        RESULTS_DIR / "confirmation_pairs.parquet",
        RESULTS_DIR / "result.json",
        RESULTS_DIR / "RESULT.md",
        RESULTS_DIR / "summary.json",
        RESULTS_DIR / "result_partial.json",
        RESULTS_DIR / "B1_RETURN.md",
        CODE_DIR / "run.py",
        CODE_DIR / "stats.py",
        CODE_DIR / "finalize.py",
        CODE_DIR / "cascade_lib.py",
        CODE_DIR / "test_B1.py",
        CODE_DIR / "hashes.py",
        CODE_DIR / "smoke.py",
        CODE_DIR / "run_all.py",
        CODE_DIR / "universe_manifest.json",
        CODE_DIR / "mutant_results.json",
        CODE_DIR / "_test_summary.txt",
    ]
    for p in outputs:
        if p.exists():
            out_lines.append(f"{sha256_path(p)}  {p.relative_to(REPO)}")

    text = "\n".join(out_lines) + "\n"
    (RESULTS_DIR / "hashes.txt").write_text(text)
    print(f"wrote hashes.txt ({len(out_lines)} entries)")


if __name__ == "__main__":
    main()