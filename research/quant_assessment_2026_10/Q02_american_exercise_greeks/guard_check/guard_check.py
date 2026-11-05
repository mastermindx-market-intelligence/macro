from __future__ import annotations

"""Synthetic-root exercise of evaluate.py's stage-0 guard (amendment A2, audit finding M2).

A1 reports that its amendment-aware guard was exercised on a synthetic data root, but those
runs were not retained. This harness re-exercises the same guard decisions and keeps a
transcript. It never touches the real RUNS.log, results/ or data root:

- ``here`` is a fresh synthetic directory under WORK_DIR holding byte copies of PREREG.md and
  FREEZE.log plus a synthetic amendment and its own freeze log and RUNS.log;
- the data root is an empty synthetic directory, so a run the guard admits stops at the
  stage-1 inventory (exit 4) and reads no data at all.

An admitted run therefore shows up as exit 4 rather than the exit 0 a real data root would
give. The one-run rule counts only COMPLETED/BLOCKED/FAILED blocks, which an empty data root
cannot produce, so the "second run refused" step seeds one synthetic COMPLETED block for the
(PREREG hash, amendment hash) pair with evaluate.append_run and labels it as seeded.

Usage: python3.12 guard_check.py WORK_DIR TRANSCRIPT_JSON   (both absolute paths; WORK_DIR
must not exist yet). Exit 0 when every step matches its expected outcome, 1 otherwise.
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
Q02_ROOT = RESEARCH.parents[2]
EVALUATE = RESEARCH / "evaluate.py"


def _load_evaluate():
    spec = importlib.util.spec_from_file_location("q02_evaluate_guard_check", EVALUATE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {EVALUATE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    if len(argv) != 3:
        print("usage: python3.12 guard_check.py WORK_DIR TRANSCRIPT_JSON (absolute paths)")
        return 2
    work = Path(argv[1])
    transcript_path = Path(argv[2])
    if not work.is_absolute() or not transcript_path.is_absolute():
        print("WORK_DIR and TRANSCRIPT_JSON must be absolute paths")
        return 2
    if work.exists():
        print(f"WORK_DIR already exists: {work}")
        return 2
    ev = _load_evaluate()
    here = work / "here"
    here_no_amend = work / "here_freeze_log_without_amendment"
    data_root = work / "empty_data_root"
    for d in (here, here_no_amend, data_root):
        d.mkdir(parents=True)
    for d in (here, here_no_amend):
        shutil.copyfile(RESEARCH / "PREREG.md", d / "PREREG.md")
        shutil.copyfile(RESEARCH / "FREEZE.log", d / "FREEZE.log")
    prereg_hash = ev.sha256_file(here / "PREREG.md")
    amend = here / ev.AMENDMENT_NAME
    amend_freeze = here / ev.AMENDMENT_FREEZE_NAME
    argv_cmd = [str(EVALUATE), "--synthetic-guard-check"]
    steps = []
    freeze_count = [0]

    def freeze(path_here: Path, target: Path) -> str:
        h = ev.sha256_file(target)
        freeze_count[0] += 1
        with open(path_here / ev.AMENDMENT_FREEZE_NAME, "a") as fh:
            fh.write(f"synthetic-freeze-line-{freeze_count[0]}\n{h}  {target}\n")
        return h

    def step(name: str, expected_exit: int, path_here: Path, expect_status_prefix: str) -> None:
        code = ev.run(path_here, Q02_ROOT, data_root, argv_cmd)
        blocks = ev.parse_runs_log(path_here / "RUNS.log")
        status = str(blocks[-1].get("status")) if blocks else None
        ok = code == expected_exit and status is not None and status.startswith(expect_status_prefix)
        steps.append({"step": name, "expected_exit": expected_exit, "exit": code,
                      "status": status, "pass": ok})

    # 1. An amendment with no freeze log is refused.
    amend.write_text("# synthetic amendment v1 (guard check only)\n")
    step("unfrozen_amendment_refused", 2, here, "REFUSED amendment_hash_differs")
    # 2. Once frozen, the guard admits the run; the empty data root stops it at inventory.
    v1 = freeze(here, amend)
    step("frozen_amendment_admitted", 4, here, "REFUSED inventory_mismatch")
    # 3. A guard-passing run already logged for this (PREREG, amendment) pair blocks a second.
    ev.append_run(here / "RUNS.log", kind="evaluate", command="seeded synthetic block (guard check)",
                  exit_code=0, status="COMPLETED seeded_synthetic_block", prereg_hash=prereg_hash,
                  recorded_hash=prereg_hash, inputs=[], outputs=[],
                  notes=["seeded by guard_check.py to exercise the one-run rule; not a real run"],
                  elapsed=None, amendment_hash=v1, amendment_recorded=v1)
    step("second_run_same_amendment_refused", 3, here, "REFUSED one_run_per_frozen_hash")
    # 4. Appending to the amendment without re-freezing is refused.
    with open(amend, "a") as fh:
        fh.write("# synthetic amendment v2 appended (guard check only)\n")
    step("appended_unfrozen_amendment_refused", 2, here, "REFUSED amendment_hash_differs")
    # 5. Re-freezing admits exactly the new pair.
    v2 = freeze(here, amend)
    step("refrozen_amendment_admitted", 4, here, "REFUSED inventory_mismatch")
    # 6. A freeze log with no amendment file is refused.
    freeze(here_no_amend, here / ev.AMENDMENT_NAME)
    step("freeze_log_without_amendment_refused", 2, here_no_amend, "REFUSED amendment_hash_differs")
    # 7. A legacy FAILED block without an amendment field counts under "none" only.
    legacy_log = work / "legacy_RUNS.log"
    ev.append_run(legacy_log, kind="evaluate", command="seeded legacy block (guard check)",
                  exit_code=1, status="FAILED KeyError: 'date'", prereg_hash=prereg_hash,
                  recorded_hash=prereg_hash, inputs=[], outputs=[], notes=["seeded legacy block"],
                  elapsed=None)
    under_none = ev.prior_evaluate_runs(legacy_log, prereg_hash, "none")
    under_v1 = ev.prior_evaluate_runs(legacy_log, prereg_hash, v1)
    steps.append({"step": "legacy_failed_block_counts_under_none_only",
                  "prior_under_none": under_none, "prior_under_amendment": under_v1,
                  "pass": under_none == ["FAILED KeyError: 'date'"] and under_v1 == []})
    # 8. The pair rule: v2 had no guard-passing block before step 5, v1 had the seeded one.
    steps.append({"step": "one_run_rule_is_per_amendment_hash",
                  "prior_v1": ev.prior_evaluate_runs(here / "RUNS.log", prereg_hash, v1),
                  "prior_v2": ev.prior_evaluate_runs(here / "RUNS.log", prereg_hash, v2),
                  "pass": ev.prior_evaluate_runs(here / "RUNS.log", prereg_hash, v1)
                  == ["COMPLETED seeded_synthetic_block"]
                  and ev.prior_evaluate_runs(here / "RUNS.log", prereg_hash, v2) == []})

    runs_text = (here / "RUNS.log").read_text()
    transcript = {
        "purpose": "A2 / audit M2: retained synthetic-root exercise of the evaluate.py stage-0 guard",
        "evaluate_py_sha256": ev.sha256_file(EVALUATE),
        "guard_check_py_sha256": ev.sha256_file(Path(__file__).resolve()),
        "prereg_sha256": prereg_hash,
        "synthetic_amendment_sha256": {"v1": v1, "v2": v2},
        "data_root": "empty synthetic directory (no file read)",
        "steps": steps,
        "all_pass": all(s["pass"] for s in steps),
        "synthetic_runs_log_sha256": ev.sha256_text(runs_text),
        "synthetic_runs_log": runs_text.splitlines(),
        "freeze_log_without_amendment_runs_log": (here_no_amend / "RUNS.log").read_text().splitlines(),
    }
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(json.dumps(transcript, indent=1, sort_keys=True) + "\n")
    for s in steps:
        print(s["step"], "PASS" if s["pass"] else "FAIL")
    print("all_pass", transcript["all_pass"])
    return 0 if transcript["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
