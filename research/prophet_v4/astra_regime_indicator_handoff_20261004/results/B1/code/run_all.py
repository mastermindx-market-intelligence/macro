"""Orchestrate the B1 lane end-to-end.

Order (D5: hashes.txt MUST be written LAST so it doesn't include itself):
  1. run.py        — builds events_panel.parquet + confirmation_pairs.parquet + summary.json
  2. stats.py      — builds result_partial.json (per-cell RNGs via SeedSequence)
  3. finalize.py   — generates universe_manifest.json, then result.json + RESULT.md
  4. hashes.py     — builds hashes.txt LAST

Run with:
  cd ~/lanes/repos/macro && python3 research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/code/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent


def _run(label: str, script: str) -> None:
    print(f"\n=== {label}: python3 {script} ===", flush=True)
    proc = subprocess.run(
        [sys.executable, str(CODE_DIR / script)],
        cwd=str(REPO), check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{label} failed with returncode={proc.returncode}")


def main():
    _run("STAGE 1 / 4 — run", "run.py")
    _run("STAGE 2 / 4 — stats", "stats.py")
    _run("STAGE 3 / 4 — finalize", "finalize.py")
    _run("STAGE 4 / 4 — hashes (LAST)", "hashes.py")
    print("\nALL DONE", flush=True)


if __name__ == "__main__":
    main()