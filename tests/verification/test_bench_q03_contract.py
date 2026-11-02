"""Q03-1 contract pins for the frozen matched workload (fast; runs in CI).

Five things are pinned, in order:

1. the two headline bounds the read path promises (imported from the source);
2. every frozen ``MAX_*`` literal in the spec equals the CURRENT source value,
   extracted with ``ast`` (never by importing ``scripts/``), so a legitimate
   future widening must update the spec in the same PR — that is the Q03.03
   "not silently widened" guarantee;
3. the spec schema: R1–R12, the detection rule, the seed;
4. the fixture generator reproduces the CSV/JSONL digests and the parquet
   LOGICAL digest frozen in the spec;
5. a smoke run of ``bench_q03.py`` as a SUBPROCESS (the audit hook never
   enters this pytest process): R1–R9 ok, R10/R11/R12 refusing with the
   frozen codes, zero subprocess/socket audit events, no thread delta.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import bench_q03  # noqa: E402  (the runner module; importing it runs nothing)

SPEC_PATH = REPO / "research" / "data_os_completion" / "2026-10-13" / "q03_baseline.json"


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


# ── 1. the headline bounds, imported from the source under test ──────────────

def test_max_response_bytes_is_131072():
    from lib.dataos.web_workspace import MAX_RESPONSE_BYTES
    assert MAX_RESPONSE_BYTES == 131072


def test_max_request_bytes_is_16384():
    from lib.dataos.web_api import MAX_REQUEST_BYTES
    assert MAX_REQUEST_BYTES == 16384


# ── 2. every frozen MAX_* literal equals the current source value ────────────

@pytest.mark.parametrize("path", bench_q03.LIMITS_PATHS)
def test_frozen_max_literals_match_source(spec, path):
    current = bench_q03.extract_max_literals((REPO / path).read_text("utf-8"))
    frozen = spec["max_limits"].get(path)
    assert frozen is not None, f"{path} missing from the frozen spec"
    assert current == frozen, (
        f"{path}: source {current} != frozen spec {frozen} — a legitimate "
        "change must update the spec in the same PR (Q03.03)")


def test_max_response_bytes_present_in_frozen_table(spec):
    table = spec["max_limits"]["lib/dataos/web_workspace.py"]
    assert table["MAX_RESPONSE_BYTES"] == 131072


# ── 3. the spec schema ────────────────────────────────────────────────────────

def test_spec_has_r1_to_r12(spec):
    for i in range(1, 13):
        assert f"R{i}" in spec["requests"], f"R{i} missing from the spec"
    for rid, request in spec["requests"].items():
        assert isinstance(request, dict) and "action" in request


def test_spec_has_detection_rule_and_seed(spec):
    rule = spec["detection_rule"]
    for key in ("deterministic_counters", "latency_and_memory",
                "q03_04_background", "q03_03_limits", "timeouts", "noise"):
        assert key in rule and rule[key], f"detection rule missing {key}"
    assert isinstance(spec["seed"], int)
    assert spec["commits"]["A"] != spec["commits"]["B"]


def test_spec_expected_refusals_frozen(spec):
    assert spec["expected_refusals"] == {
        "R10": "SOURCE_VERSION_MISMATCH",
        "R11": "SOURCE_NOT_FOUND",
        "R12": "RESULT_TOO_LARGE_REDUCE_COLUMNS_OR_LIMIT",
    }


# ── 4. the fixture regenerates to the frozen digests ─────────────────────────

def test_fixture_regeneration_matches_frozen_digests(spec, tmp_path):
    got = bench_q03.generate_fixture(tmp_path, spec)
    mismatches = []
    for name, expect in spec["fixture"]["files"].items():
        g = got.get(name)
        if g is None:
            mismatches.append(f"{name}: missing")
            continue
        for key in ("sha256", "rows", "logical_sha256"):
            if key in expect and g.get(key) != expect[key]:
                mismatches.append(f"{name}.{key}")
    assert not mismatches, f"fixture drifted: {mismatches}"


# ── 5. the smoke run (subprocess; the audit hook stays out of pytest) ────────

@pytest.fixture(scope="module")
def smoke(spec, tmp_path_factory) -> dict:
    if not Path("/proc/self/io").exists():
        # The bench driver's read counters come from Linux /proc/self/io. CI's ci-pack runs
        # ubuntu-latest and enforces every smoke pin there; a macOS developer run reports this
        # skip with its reason instead of five opaque driver errors.
        pytest.skip("Q03 smoke needs Linux /proc/self/io (bench read counters); CI runs it on ubuntu-latest")
    out = tmp_path_factory.mktemp("q03smoke") / "smoke.json"
    fixture = tmp_path_factory.mktemp("q03smoke") / "fixture"
    proc = subprocess.run(
        [sys.executable, "-B", str(HERE / "bench_q03.py"),
         "--spec", str(SPEC_PATH),
         "--repo-a", str(REPO), "--repo-b", str(REPO),
         "--fixture-dir", str(fixture), "--out", str(out),
         "--smoke", "--arms", "A_inproc", "--rounds", "1"],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"smoke exit {proc.returncode}: {proc.stderr[-800:]}"
    return json.loads(out.read_text(encoding="utf-8"))


def test_smoke_r1_to_r9_ok(smoke):
    for i in range(1, 10):
        rid = f"R{i}"
        for commit in ("A", "B"):
            for phase in ("cold", "warm1", "warm2"):
                samples = smoke["A_inproc"]["per_request"][rid][commit][phase]["all_samples"]
                assert samples, f"{rid}/{commit}/{phase} has no samples"
                for s in samples:
                    assert s["ok"] and s["refusal"] is None and s["error"] is None, s


def test_smoke_refusals_frozen(smoke, spec):
    for rid in ("R10", "R11", "R12"):
        for commit in ("A", "B"):
            for phase in ("cold", "warm1", "warm2"):
                samples = smoke["A_inproc"]["per_request"][rid][commit][phase]["all_samples"]
                for s in samples:
                    assert not s["ok"]
                    assert s["refusal"] == spec["expected_refusals"][rid], s


def test_smoke_zero_subprocess_and_socket_events(smoke):
    for rid_data in smoke["A_inproc"]["per_request"].values():
        for commit in ("A", "B"):
            for phase in ("cold", "warm1", "warm2"):
                for s in rid_data[commit][phase]["all_samples"]:
                    counters = s["counters"]
                    assert counters["subprocess.Popen"] == 0, s
                    assert counters["socket.connect"] == 0, s
                    assert counters["socket.getaddrinfo"] == 0, s


def test_smoke_no_thread_delta(smoke):
    for rid, rid_data in smoke["A_inproc"]["per_request"].items():
        for commit in ("A", "B"):
            for phase in ("cold", "warm1", "warm2"):
                for s in rid_data[commit][phase]["all_samples"]:
                    assert s["threads_after"] == s["threads_before"], (rid, s)
    for end in smoke["A_inproc"]["driver_ends"]:
        assert end["end"]["threads"] >= 1


def test_smoke_no_errors(smoke):
    assert smoke["totals"]["errors"] == 0
    assert smoke["totals"]["timeouts"] == 0
    assert smoke["totals"]["samples"] == 2 * 3 * 12
