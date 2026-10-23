"""Evidence-only observer for the incumbent commodity publisher.

The publisher runs normally, including its ordinary data writes and optional
acquisition. This observer records file reads; it replaces no owner function,
input, result, clock, or exception. It is not a production publication route.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    sys.path.insert(0, str(root))
    source = json.loads(Path(args.source_receipt).read_text())
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for path, expected in source["source_sha256"].items():
        if digest(path) != expected:
            raise ValueError(f"Source changed before publisher invocation: {path}")
    receipt, log = Path(args.receipt), Path(args.log)
    if receipt.exists() or log.exists():
        raise ValueError("Preserve earlier evidence; use new receipt and log paths")
    prefix = str(root / "data") + os.sep
    reads = {}
    active, observing = True, False

    def observe(path, reason):
        nonlocal observing
        if not active or observing:
            return
        observing = True
        try:
            value = os.fspath(path)
            if not isinstance(value, str):
                return
            value = os.path.abspath(value)
            if not value.startswith(prefix) or not value.endswith(
                    (".json", ".jsonl", ".parquet", ".csv", ".yaml", ".yml")):
                return
            relative = os.path.relpath(value, root)
            if relative not in reads:
                present = os.path.isfile(value)
                reads[relative] = {
                    "path": relative,
                    "exists_at_first_observation": present,
                    "sha256_at_first_observation": digest(value) if present else None,
                    "observed_by": [],
                }
            if reason not in reads[relative]["observed_by"]:
                reads[relative]["observed_by"].append(reason)
        except (TypeError, ValueError, OSError):
            pass
        finally:
            observing = False

    def profile(frame, event, arg):
        if (event == "call" and frame.f_code.co_name in
                ("exists", "is_file", "read_text", "read_bytes")
                and "pathlib" in frame.f_code.co_filename):
            observe(frame.f_locals.get("self"), "pathlib." + frame.f_code.co_name)

    def audit(event, values):
        if event != "open" or not values:
            return
        mode = values[1] if len(values) > 1 else None
        flags = values[2] if len(values) > 2 else 0
        if isinstance(mode, str) and ("r" in mode or "+" in mode):
            observe(values[0], "open-read")
        elif mode is None and isinstance(flags, int) and not flags & (os.O_WRONLY | os.O_RDWR):
            observe(values[0], "open-read")

    record = {
        "invocation": "runpy.run_module('scripts.build_commodities', run_name='__main__')",
        "observation": "Python file-read observation only; no replaced owner functions or inputs",
        "observer_sha256": digest(__file__),
        "source_sha256": source["source_sha256"],
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "merge_head": subprocess.check_output(["git", "rev-parse", "MERGE_HEAD"], text=True).strip(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "production_acceptance": False,
    }
    print(json.dumps({"starting": record["invocation"], "log": str(log)}), flush=True)
    started, code = time.monotonic(), 0
    with log.open("x") as output:
        previous_out, previous_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = output
        sys.addaudithook(audit)
        sys.setprofile(profile)
        try:
            runpy.run_module("scripts.build_commodities", run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        except BaseException:
            traceback.print_exc()
            code = 1
        finally:
            active = False
            sys.setprofile(None)
            sys.stdout, sys.stderr = previous_out, previous_err
    record.update(
        returncode=code,
        finished_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic() - started, 3),
        source_unchanged=all(digest(p) == h for p, h in source["source_sha256"].items()),
        observed_data_reads=[reads[k] for k in sorted(reads)],
        page_sha256=digest("site/commodities.html"),
        log_sha256=digest(log),
    )
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({
        "returncode": code, "elapsed_seconds": record["elapsed_seconds"],
        "source_unchanged": record["source_unchanged"], "page_sha256": record["page_sha256"],
        "observed_data_files": len(reads),
        "missing_at_first_observation": [x for x in reads.values()
                                          if not x["exists_at_first_observation"]],
    }), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
