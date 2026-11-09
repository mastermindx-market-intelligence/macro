"""Lane C1 orchestrator.

Pipeline order (E3 round-2 + G7 round-3):
  1. run.py builds rotation_state_daily.parquet, rotation_cuts_daily.parquet (sidecar),
     result.json (with tests counts = 0), and RESULT.md with the "tests" field unset
     and a "PENDING" placeholder.
  2. pytest runs the test suite; this orchestrator captures its summary line.
  3. Orchestrator parses the summary to pass/skip/fail counts (no wall time — G7).
  4. Orchestrator re-stamps result.json["tests_pass"/"tests_skip"/"tests_fail"] and
     RESULT.md "## Tests" with the captured summary.
  5. Orchestrator writes code/_test_summary.txt LAST among the three so
     the sidecar's mtime is >= result.json's mtime.
  6. Orchestrator writes hashes.txt LAST with REPO-RELATIVE paths (G7).
  7. Orchestrator asserts the sidecar and result.json["tests_pass"/"tests_skip"/"tests_fail"]
     (joined back together) and RESULT.md "## Tests" all carry the same summary line.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run as R


def main():
    # ─── Step 1: build (run.py) ─────────────────────────────────────────────
    print("=== Step 1: build (run.py) ===", flush=True)
    if os.environ.get("C1_SKIP_REBUILD") == "1":
        print("[orchestrator] C1_SKIP_REBUILD=1 — not calling run.main(); "
              "result.json/RESULT.md must already be written", flush=True)
        if not R.OUT_RESULT_JSON.exists() or not R.OUT_RESULT_MD.exists():
            sys.exit("C1_SKIP_REBUILD set but result.json/RESULT.md missing")
    else:
        R.main()

    # ─── Step 2: pytest ─────────────────────────────────────────────────────
    print("=== Step 2: pytest ===", flush=True)
    code_dir = Path(__file__).parent
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(code_dir), "-q", "-p", "no:cacheprovider",
         "--tb=short", "--no-header"],
        capture_output=True, text=True, cwd=code_dir.parent.parent.parent.parent.parent,
    )
    output = proc.stdout + "\n" + proc.stderr
    print(output, flush=True)
    if proc.returncode != 0:
        sys.exit(f"pytest failed with returncode {proc.returncode}; aborting orchestration")

    summary = _parse_summary(output)
    if summary is None:
        sys.exit("Could not find pytest summary line in output; aborting orchestration")
    counts = _parse_counts(output)
    if counts is None:
        sys.exit("Could not parse pytest counts from output; aborting orchestration")
    print(f"[orchestrator] summary = {summary!r}  counts = {counts}", flush=True)

    # ─── Step 3: re-stamp result.json and RESULT.md ────────────────────────
    print("=== Step 3: re-stamp result.json and RESULT.md ===", flush=True)
    res = json.loads(R.OUT_RESULT_JSON.read_text())
    res["tests_pass"] = counts["passed"]
    res["tests_skip"] = counts["skipped"]
    res["tests_fail"] = counts["failed"]
    # G7: no wall time in result.json
    R.OUT_RESULT_JSON.write_text(json.dumps(res, indent=2, default=str))

    md_text = R.OUT_RESULT_MD.read_text()
    if "```\nPENDING\n```" not in md_text:
        sys.exit("RESULT.md was not updated — PENDING fence not found; aborting")
    new_md = md_text.replace("```\nPENDING\n```", f"```\n{summary}\n```", 1)
    R.OUT_RESULT_MD.write_text(new_md)

    # ─── Step 4: write sidecar LAST so its mtime is the freshest ───────────
    print("=== Step 4: write sidecar (LAST so mtime >= result.json) ===", flush=True)
    R.OUT_TEST_SUMMARY.write_text(summary + "\n")
    time.sleep(0.01)

    # ─── Step 5: write hashes.txt LAST with REPO-RELATIVE paths (G7) ───────
    print("=== Step 5: write hashes.txt (LAST, repo-relative) ===", flush=True)
    write_hashes()

    # ─── Step 6: verify ─────────────────────────────────────────────────────
    print("=== Step 6: verify ===", flush=True)
    sidecar_text = R.OUT_TEST_SUMMARY.read_text().strip()
    res2 = json.loads(R.OUT_RESULT_JSON.read_text())
    md_text2 = R.OUT_RESULT_MD.read_text()
    tests_section = md_text2.split("## Tests", 1)[1] if "## Tests" in md_text2 else md_text2
    md_match = re.search(r"```\s*\n(.+?)\n```", tests_section)
    md_summary = md_match.group(1).strip() if md_match else None
    assert sidecar_text == md_summary, (
        f"sidecar ({sidecar_text!r}) != md ({md_summary!r})"
    )
    # result.json now stores counts only (no wall time per spec G7). The sidecar
    # and RESULT.md carry the full pytest summary line. Verify they agree on
    # counts (the only part stored in result.json).
    counts_summary = _summary_from_counts(res2["tests_pass"], res2["tests_skip"],
                                         res2["tests_fail"])
    # sidecar and md carry the full line (with wall time); verify the prefix
    # containing the counts matches.
    assert sidecar_text.startswith(counts_summary), (
        f"sidecar ({sidecar_text!r}) does not start with counts_summary ({counts_summary!r})"
    )
    assert md_summary.startswith(counts_summary), (
        f"md ({md_summary!r}) does not start with counts_summary ({counts_summary!r})"
    )
    # sidecar and md must be byte-identical (both carry the full pytest line)
    assert sidecar_text == md_summary, (
        f"sidecar ({sidecar_text!r}) != md ({md_summary!r})"
    )
    sidecar_mtime = R.OUT_TEST_SUMMARY.stat().st_mtime
    json_mtime = R.OUT_RESULT_JSON.stat().st_mtime
    md_mtime = R.OUT_RESULT_MD.stat().st_mtime
    assert sidecar_mtime >= json_mtime, (
        f"sidecar mtime {sidecar_mtime} < result.json mtime {json_mtime}"
    )
    assert R.OUT_HASHES.stat().st_mtime >= sidecar_mtime, "hashes.txt mtime not the newest"
    print(f"[orchestrator] all three copies match: {sidecar_text!r}", flush=True)
    print(f"[orchestrator] mtime order: result.json={json_mtime} "
          f"<= RESULT.md={md_mtime} <= sidecar={sidecar_mtime} "
          f"<= hashes.txt={R.OUT_HASHES.stat().st_mtime}", flush=True)
    print("=== Pipeline complete ===", flush=True)


def _parse_summary(output: str) -> str | None:
    """Pull the pytest summary line, e.g. '11 passed, 1 skipped in 17.07s'."""
    for line in reversed(output.splitlines()):
        line = line.strip()
        m = re.match(r"^(\d+ passed(?:, \d+ \w+)*)( in [\d.]+s)?$", line)
        if m:
            return m.group(0)
    return None


def _parse_counts(output: str) -> dict | None:
    """Parse {'passed': N, 'skipped': M, 'failed': K} from the summary line."""
    summary = _parse_summary(output)
    if summary is None:
        return None
    counts = {"passed": 0, "skipped": 0, "failed": 0}
    parts = summary.split(" in ")[0]
    for token in [t.strip() for t in parts.split(",")]:
        m = re.match(r"^(\d+)\s+(\w+)$", token)
        if not m:
            continue
        n = int(m.group(1))
        word = m.group(2)
        if word in counts:
            counts[word] = n
    return counts


def _summary_from_counts(passed: int, skipped: int, failed: int) -> str:
    parts = [f"{passed} passed"]
    if skipped:
        parts.append(f"{skipped} skipped")
    if failed:
        parts.append(f"{failed} failed")
    return ", ".join(parts)


def _append_g1_mutant_doc() -> None:
    """Append the G1 round-3 "failing mutant test names" section to RESULT.md.

    The two named tests below were each shown to FAIL under their respective
    planted leak (run.py:113 → min(i+1, n) instead of i, and the
    monkeypatched include-t variant); clean code passes them with the rest of
    the suite.
    """
    md_text = R.OUT_RESULT_MD.read_text()
    block = (
        "\n## Failing mutant test names (G1 round-3 power verification)\n\n"
        "Two tests below were each shown to FAIL under their respective planted leak; "
        "clean code passes them with the rest of the suite.\n\n"
        "- `test_pipeline_cuts_match_tercile_cuts` — under the run.py:113 mutant "
        "`tercile_cuts(v_arr, min(i + 1, n), ...)`, this test fails at the first "
        "sampled date with the assertion `assert actual_lo == pytest.approx(expected_lo, abs=0, rel=0)` "
        "(pipeline value uses v_arr[:i+1]; clean expected uses v_arr[:i]).\n"
        "- `test_planted_include_t_leak_caught_by_cuts` — under the "
        "monkeypatched include-t variant, this test fails at the assertion "
        "`assert leak_detected` because the pipeline's cuts deviate from the "
        "CLEAN pre-monkeypatch expected (the test captures `clean_tercile_cuts = R.tercile_cuts` "
        "before the monkeypatch and compares against THAT).\n"
    )
    if "## Failing mutant test names" in md_text:
        return
    # Insert the block right before the "## Tests" section
    if "## Tests" in md_text:
        md_text = md_text.replace("\n## Tests", block + "\n## Tests", 1)
    else:
        md_text = md_text + "\n" + block
    R.OUT_RESULT_MD.write_text(md_text)
    # Re-stamp hashes since RESULT.md changed
    write_hashes()


def write_hashes() -> None:
    """Write repo-RELATIVE hashes for every input file read and every output file written
    (G7 round-3). Writes LAST so the hashes reflect the post-orchestration file state.
    """
    repo = R.REPO
    paths = [
        "data/yahoo/SPY.parquet",
        "data/yahoo/RSP.parquet",
    ] + [f"data/yahoo/{t}.parquet" for t in R.SECTOR_ETFS] + [
        "data/fred/DFII10.parquet",
        "data/regime/regime_v2_pit.parquet",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/rotation_state_daily.parquet",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/rotation_cuts_daily.parquet",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/result.json",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/RESULT.md",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/code/run.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/code/test_C1.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/code/run_all.py",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/code/_test_summary.txt",
    ]
    lines = []
    for p in paths:
        full = repo / p
        if not full.exists():
            continue
        h = subprocess.run(["shasum", "-a", "256", str(full)],
                           capture_output=True, text=True, check=True)
        # Format: `<hex>  <relative-path>` so `shasum -a 256 -c hashes.txt` from the
        # repo root works without `sed`.
        hex_hash = h.stdout.strip().split()[0]
        lines.append(f"{hex_hash}  {p}")
    R.OUT_HASHES.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()