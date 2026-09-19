"""Reproduce P1 benchmark-pair refusal and compare the frozen legacy producer.

Controlled test fixtures only; no provider calls or production writes.
Run from the repository root with its ordinary test dependencies installed.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import types
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from engine import group_pulse as current
from engine import group_member_observations as observations

BASE = "b81fd9e424a14386645a744af1872d85b6df91f5"
CASES = ["current_missing", "previous_missing", "stale_tail", "future_only",
         "current_nan", "previous_nan", "current_zero", "previous_zero",
         "current_negative", "previous_negative", "current_infinite", "previous_infinite"]

class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)

def main():
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    original = subprocess.run(
        ["git", "show", BASE + ":engine/group_pulse.py"], cwd=ROOT,
        capture_output=True, text=True, check=True, timeout=15, env=env,
    ).stdout
    baseline = types.ModuleType("_p1_frozen_legacy")
    baseline.__file__ = str(ROOT / "engine/group_pulse.py")
    sys.modules[baseline.__name__] = baseline
    exec(compile(original, baseline.__file__, "exec"), baseline.__dict__)
    namespace = runpy.run_path(str(ROOT / "tests/test_group_member_observations.py"))
    helper = namespace["_compute_with_observed_benchmark"]
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="mmx-p1-pair-") as temporary:
            for case in CASES:
                outputs = []
                for module in (baseline, current):
                    helper.__globals__["GP"] = module
                    with pytest.MonkeyPatch.context() as patch:
                        patch.setattr(module, "datetime", FrozenClock)
                        result, *_ = helper(patch, Path(temporary), case)
                        outputs.append(result)
                before, after = outputs
                old_wire = current.site_payload_bytes(before["payload"])
                new_wire = current.site_payload_bytes(after["payload"])
                assert old_wire == new_wire, "legacy output changed: " + case
                assert not after["member_observation_errors"], case
                group = after["member_observation_groups"][namespace["GROUP_ID"]]
                cells = [member["metrics"] for member in group["members"].values()]
                assert all(m["benchmark_relative_daily_change"]["value"] is None for m in cells)
                assert all(m["benchmark_relative_daily_change"]["estimability_reason"] ==
                           "benchmark_unavailable" for m in cells)
                raw_observed = sum(m["raw_daily_change"]["value"] is not None for m in cells)
                assert raw_observed > 0
                bundle = observations.assemble_member_bundle(
                    groups=after["member_observation_groups"], as_of=after["as_of"],
                    generated_at=next(iter(after["payload"].values()))["generated_at"],
                    source_receipts=after["source_receipts"], legacy_pulse_bytes=new_wire,
                )
                assert observations.validate_member_bundle(bundle) == []
                results.append({"case": case, "legacy_wire_unchanged": True,
                                "raw_members_observed": raw_observed,
                                "relative_members_observed": 0,
                                "legacy_sha256": sha256(new_wire).hexdigest()})
    finally:
        helper.__globals__["GP"] = current
        sys.modules.pop(baseline.__name__, None)
    receipt = {"scope": "controlled fixtures; not market or production acceptance",
               "baseline": BASE,
               "candidate_group_pulse_sha256": sha256((ROOT / "engine/group_pulse.py").read_bytes()).hexdigest(),
               "cases": results}
    destination = Path(__file__).with_name("legacy_parity.json")
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": len(results), "legacy_wire_unchanged": len(results),
                      "receipt": str(destination)}, sort_keys=True))

if __name__ == "__main__":
    main()
