"""Offline same-data evaluator comparison; writes only a new private pytest-cache tree.

This is a reproducibility artifact, not a Foundry job, admission command or new holdout.
Run from the owning repository with Python 3.12 and its existing numerical dependencies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
SOURCE_REF = "9579caf3f950f1a2e7b959a9b3b68d26e42e5d06"
IDS = frozenset({"SF-0013", "SF-0014", "SF-0020", "SF-0021", "SF-0022"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True,
                        help="A NEW directory under this checkout's .pytest_cache")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    allowed = (ROOT / ".pytest_cache").resolve()
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        parser.error("output must be a new child of this checkout's .pytest_cache")
    sys.path.insert(0, str(ROOT))
    from engine.signal_foundry import harness
    from engine.signal_foundry.spec import construction_hash
    from engine.trial_ledger import TrialLedger

    def source(path: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(ROOT), "show",
                                        SOURCE_REF + ":" + path], timeout=30)

    candidates = [json.loads(line) for line in
                  source("data/signal_foundry/candidates.jsonl").decode().splitlines() if line.strip()]
    assert len(candidates) == 22, "Pinned candidate corpus differs from the reviewed snapshot"
    selected = [spec for spec in candidates if spec.get("id") in IDS]
    assert {spec["id"] for spec in selected} == IDS
    paths = sorted({entry["path"] for spec in selected for entry in spec["data"]}
                   | {spec["target"]["path"] for spec in selected})
    for path in paths:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or pure.parts[0] != "data":
            raise ValueError("Unexpected pinned input path")
    blobs = {path: source(path) for path in paths}
    original = types.ModuleType("signal_foundry_reviewed_original")
    exec(compile(source("engine/signal_foundry/harness.py"),
                 "<reviewed pinned original evaluator>", "exec"), original.__dict__)
    report = {"source_commit": SOURCE_REF, "authority": "research_only", "pit_certified": False,
              "note": "Same pinned inputs and 22 filed constructions per isolated trial family. Not a new holdout, promotion or production result.",
              "candidate_source_sha256": hashlib.sha256((ROOT / "engine/signal_foundry/harness.py").read_bytes()).hexdigest(),
              "input_hashes": {path: hashlib.sha256(blob).hexdigest() for path, blob in blobs.items()},
              "results": []}
    output.mkdir(parents=True)
    for label, module in (("original", original), ("clock_repair", harness)):
        target = output / label
        target.mkdir()
        for path, blob in blobs.items():
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
        ledger_path = target / "data/trial_ledger.jsonl"
        ledger = TrialLedger(path=ledger_path, family="signal_foundry")
        for spec in candidates:
            ledger.log_trial(config={"id": spec["id"], "construction_hash": construction_hash(spec),
                                     "gates": spec.get("gates", {}), "registered_at": spec.get("registered_at")},
                             family="signal_foundry", source=spec["id"])
        for spec in selected:
            result = module.run_spec(spec, repo_root=target, ledger_path=ledger_path, asof="2026-09-15")
            stats = result.get("stats", {})
            row = {"evaluator": label, "id": spec["id"], "battery": result["battery_version"],
                   "n_obs": stats.get("n_obs"), "hac": stats.get("hac"), "sampling": stats.get("sampling"),
                   "full_ic": stats.get("full_ic"), "verdict": result["verdict"],
                   "reasons": result.get("verdict_reasons"), "backtest": result.get("backtest", {}),
                   "ledger_n": result.get("ledger_n_at_run")}
            report["results"].append(row)
            print(label, spec["id"], row["verdict"], "HAC windows", (row["hac"] or {}).get("n"), flush=True)
    (output / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("COMPARISON_RECEIPT", output / "comparison.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
