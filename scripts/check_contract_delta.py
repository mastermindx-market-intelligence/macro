#!/usr/bin/env python3
"""Differential PR-vs-base merge-train contract gate.

Incident (2026-08-19, ~12:00Z): #5872 and #5932 each grew a curated
`scope: exclusive` job's import closure without widening its declared `paths:`
in `.github/ci/legacy-jobs.yml`. Because `ci-pack` is path-scoped, neither PR's
own pack ran `tests/test_ci_pack.py::
test_curated_exclusive_scopes_cover_their_own_import_closure` — that test lives
under `tests/`, which neither PR touched — so both merged green. Main's
`integration-baseline` lane (which DOES run the full manifest unconditionally)
caught it 5+ hours later, and by then 21 armed PRs sat baseline-blocked behind a
red main. Same class, same blind spot: `scripts/audit_unrun_tests.py`'s gate
only ever ran post-merge too (the workflow-yaml legacy job that owns it is
`gate: data`, off the merge gate — a suite can ship wired to nothing and nobody
finds out until the next audit run).

This script re-derives both finding classes — curated-exclusive import-closure
misses, and unwired pytest suites — UNCONDITIONALLY of `ci-pack`'s path
scoping, on every PR (see the `contract-delta` job in `.github/workflows/ci.yml`,
`if: github.event_name == 'pull_request'`). Both finding classes are computed
by the SAME functions the two existing guards already use for their own
verdicts:

    scripts.run_ci_pack.curated_exclusive_closure_findings   (import-closure misses)
    scripts.audit_unrun_tests.gated_unrun_suites              (unwired suites)

DIFFERENTIAL, NEVER ABSOLUTE — this is the whole design, not an implementation
detail. `tests/test_ci_pack.py` and `scripts/audit_unrun_tests.py`'s own gate
are ABSOLUTE: they red on every finding, whatever caused it. Folding that same
absolute check into an always-on PR gate would re-create exactly the failure
mode this repo's house law already names: "Validator in an ALWAYS-ON job = fleet
control plane" — the moment main itself carries ONE inherited finding (which is
precisely what happened 2026-08-19), every open PR would go red simultaneously,
none of them able to fix a defect that is not in their own diff, and the merge
train would jam at PR level instead of (as today) only at the main-baseline
circuit breaker. So this gate computes findings on the PR's head AND on its
base, and reds ONLY on `head - base`: a finding this PR's own tree introduces
that its base did not already carry. A finding that is identical on both sides
is printed as `::notice` (visible, never silently dropped) and never fails the
job. A finding present on base but absent on head (the PR fixed it) is not
printed at all — it is not this PR's problem to report.

Finding identity for the delta:
    closure   (job_id, uncovered_path) tuples — narrower than job_id alone, so a
              PR that adds ONE new uncovered path to an already-broken curated
              job still reds on that one new path, even though the job already
              had an inherited finding.
    suites    the suite's repo-relative path string.

BASE-TREE MATERIALIZATION. The base commit is checked out into a throwaway
`git worktree add --detach` (works under this repo's `blob:none` partial clone —
missing blobs fetch lazily over the network). Since 2026-09-14 the throwaway
tree MIRRORS the calling checkout's sparse cone (`materialize_base_tree`): a
sparse session worktree gets a sparse base (~0.4 GiB instead of 3.8 GiB, the
dominant disk burn on the shared dev Macs), a full checkout still gets a full
base, and either way both censuses walk the same directory set. It is minted
under `$CONTRACT_DELTA_TMP_ROOT`, else the host's external-volume policy root,
else the system temp dir (`base_tree_temp_root`), and never under
`.claude/worktrees/` or any other fleet worktree-GC root — see
`scripts/prophet_pit_replay.py`'s `resolve_or_create_vintage_worktree` for the
same rule applied to a similar throwaway-worktree need.

WHY A SUBPROCESS PER TREE, NOT TWO IN-PROCESS CALLS. Both
`scripts/run_ci_pack.py` and `scripts/audit_unrun_tests.py` pin module-level
globals (`ROOT`, and the modules they import from each other, e.g.
`infer_job_scopes`'s `from scripts.audit_unrun_tests import discover_suites`) to
wherever their OWN `__file__` resolves at import time. Python caches a module by
NAME, not by path, so importing "scripts.audit_unrun_tests" a second time for a
different tree in the same process would hand back the FIRST tree's cached
module — silently answering with the wrong tree's data. A fresh interpreter per
tree, launched with `cwd=<that tree>`, is the only reliable way to get two
independent, correct answers in one run. The head side still runs IN-PROCESS
(see `_head_findings` below) because head IS this process's own tree — no
cross-tree collision is possible there, and using the real imported functions
directly is what keeps this script and `tests/test_ci_pack.py` sharing one
implementation rather than a copy that can drift (see
`tests/test_contract_delta.py::
test_curated_exclusive_closure_findings_is_the_shared_implementation`).

BOOTSTRAP FALLBACK. `_WORKER_SOURCE` tries the canonical functions above first;
that succeeds for every base commit ONCE this gate itself has merged. It falls
back to rebuilding the identical computation from the pre-existing, unrenamed
primitives (`load_legacy_jobs` / `infer_job_scopes` / `_matches_any` / `replace`;
`census` / `_load_baseline` / `_load_waivers` / `_validate_waivers`) when the
base tree predates this refactor — true only while THIS gate's own PR is open,
since `origin/main` today had neither convenience function at the time this
script first merged. Kept permanently rather than deleted post-merge: a
`--base` far enough back to predate this gate is rare but not impossible, and
refusing outright there is worse than paying the fallback's cost.

CONCURRENT HEAD/BASE (2026-08-19, post-merge fix). The head and base
computations are two INDEPENDENT whole-repo censuses with no data dependency
between them, so running them serially pays their cost twice. PR #6013's
`contract-delta` job was CANCELLED at exactly its 25-minute `timeout-minutes`
ceiling — checkout/setup/fetch all green, the gate step itself killed mid-run
— because the two ~6-8-minute censuses (measured on a faster 24-core
development Mac) run noticeably slower on `ci.yml`'s 2-core hosted runner, and
serial execution left no margin. `run()` now materializes the base worktree,
launches its worker via `subprocess.Popen` (non-blocking), computes head
findings IN-PROCESS while that subprocess runs, then joins it — overlapping
the two dominant costs instead of paying for them back to back. Semantics and
output are unchanged; only wall time moves. `.github/workflows/ci.yml` also
raised `contract-delta`'s `timeout-minutes` 25 -> 45 as a second, independent
margin (the job is off the critical path — packs run ~30 min regardless).

SPARSE TRACKED-PATH ORACLE (2026-09-16). The hosted checkout intentionally
omits generated-heavy `site/` and `data/`, but a test can still add a literal
read of a tracked non-Python leaf there. PR #7228 did exactly that with
`site/theme.css`; physical-only existence checks erased the dependency and this
gate reported `0 introduced`, allowing current main to inherit an absolute
closure red. Both the head census and detached-base worker now bind the tested
commit to `ci.tracked_paths.v1` before deriving scope. The oracle supplies only
Git-tree existence; source bytes are never fabricated, and an omitted Python
file whose content is required still fails closed.

CONTROL-PLANE CLASSES (2026-09-27). #8033 put the CI control plane's own
contract suites on the PR code gate as `ci-control-plane-contracts`, an
exclusive job that runs only when a PR touches its declared `paths:`. Three of
the verdicts it runs depend on the WHOLE tree, so a PR can move them without
selecting it: the #8033 review measured a suite edited to read
templates/index.html taking that packing probe from 134 selected jobs to 135,
past its ceiling, on a PR that never ran the probe. Those shapes surfaced only
after merge, on integration-baseline.yml, which pauses merge-on-green. They are
now three more differential classes here, each computed by the function its
absolute guard fails on:

    probes        scripts.run_ci_pack.packing_probe_measurements and
                  packing_probe_breaches (tests/test_ci_pack.py::
                  test_exclusive_curation_narrows_ordinary_code_prs)
    skip_only     scripts.check_skip_only_suites.skip_only_findings
    trigger_gaps  scripts.check_ci_trigger_closure.trigger_gap_findings

Finding identity for these:
    skip_only     (suite, gate)
    trigger_gaps  (suite, subject), one per unreachable subject, so a suite
                  that already carried a gap still reds on a new one.
    probes        (probe, axis) for the jobs, weight and packs axes, compared
                  by MAGNITUDE: introduced when the head is over the ceiling
                  and the base was not, or the head is further over than the
                  base; inherited when the head is over but no further than
                  the base. Same reason as the (job_id, path) closure pair: an
                  already-breached probe gives no amnesty to a PR that pushes
                  it further.

ONE SET OF CEILINGS. The ceilings live in tests/test_ci_pack.py as two plain
module-level literals (`PACKING_PROBES`, `PACKING_PROBE_MAX_PACKS`). This gate
reads them from the head with `ast.literal_eval` (importing the test module
would drag pytest in) and hands the same values to the base worker, so both
trees are measured against the head's ceilings and the delta isolates what the
planner selects. A PR that moves a ceiling edits tests/test_ci_pack.py, which
selects ci-control-plane-contracts, whose absolute test judges the ceiling
itself; this gate never re-bases or loosens one.

ONE PROJECTION. The base worker ships the guards' raw finding rows and the
head payload is JSON round-tripped, so the projection onto finding identity
happens once, in `compute_delta`, identically for both sides. A base that
predates a class's shared function rebuilds the same rows from the primitives
it is built on (the BOOTSTRAP rule above). A base that predates the guard
module itself ships `null` for that class: nothing can be inherited from a
tree without the guard, so every head finding in the class counts as
introduced, and a notice says so.

COST. Measured on a 24-core development Mac, per tree, after the closure census
has warmed the planner's per-file analysis caches: probes ~28 s, skip_only
~16 s, trigger_gaps ~21 s, against ~119 s for closure + suites, so roughly +55%
on each side. The head and the base still overlap, so the wall-clock cost is
about the same fraction. `run()` prints every census's seconds on both sides so
each CI log carries the real hosted-runner figure.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, NamedTuple

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = ".github/ci/legacy-jobs.yml"
# Where the packing-probe ceilings live; read, never imported (`packing_probe_spec`).
PACKING_PROBE_SUITE_REL = "tests/test_ci_pack.py"
CONTROL_PLANE_CLASSES = ("probes", "skip_only", "trigger_gaps")

sys.path.insert(0, str(ROOT))

from scripts.run_ci_pack import (  # noqa: E402
    curated_exclusive_closure_findings,
    packing_probe_breaches,
    packing_probe_measurements,
)
from scripts.audit_unrun_tests import gated_unrun_suites  # noqa: E402
from scripts.check_ci_trigger_closure import trigger_gap_findings  # noqa: E402
from scripts.check_skip_only_suites import skip_only_findings  # noqa: E402
from scripts.ci_scope_dependencies import (  # noqa: E402
    TrackedPathInventoryError,
    planner_tracked_path_inventory,
    write_tracked_path_inventory,
)


class ContractDeltaError(RuntimeError):
    """A script-level failure — refused to compute, not a contract-delta finding."""


# ─────────────────────────────────────────────────────────────────────────────
# finding computation — head in-process, base via a subprocess worker
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def _tracked_tree_inventory(repo_root: Path):
    """Expose omitted tracked leaves to one immutable-tree scope census.

    `contract-delta` deliberately excludes generated-heavy `site/` and `data/`
    directories from its hosted checkout. Static dependency analysis still has
    to know that a literal non-Python leaf exists there: otherwise a new
    `Path("site/theme.css").read_text()` edge disappears before the differential
    can report it. The inventory is an existence oracle only; any omitted Python
    source whose bytes are needed still fails closed through
    `ScopeMaterializationError`.
    """
    tested_tree_sha = _git("rev-parse", "HEAD", cwd=repo_root).strip()
    with tempfile.TemporaryDirectory(prefix="contract-delta-inventory-") as tmp:
        inventory = Path(tmp) / "tracked-paths.v1"
        try:
            write_tracked_path_inventory(
                inventory, tested_tree_sha, root=repo_root
            )
            with planner_tracked_path_inventory(
                inventory, tested_tree_sha, root=repo_root
            ):
                yield tested_tree_sha
        except TrackedPathInventoryError as exc:
            raise ContractDeltaError(
                f"exact-tree inventory refused for {repo_root}: {exc}"
            ) from exc


def _head_findings() -> dict[str, Any]:
    """Findings for THIS process's own tree, via the canonical shared functions.

    Not a copy: `curated_exclusive_closure_findings` / `gated_unrun_suites` are
    the exact functions `tests/test_ci_pack.py` and
    `scripts/audit_unrun_tests.py`'s own gate use for their absolute verdicts.
    """
    manifest = ROOT / MANIFEST_REL
    with _tracked_tree_inventory(ROOT):
        closure = curated_exclusive_closure_findings(manifest)
        return {
            "closure": {job_id: sorted(paths) for job_id, paths in closure.items()},
            "suites": sorted(gated_unrun_suites()),
        }


_PROBE_SPEC_NAMES = ("PACKING_PROBES", "PACKING_PROBE_MAX_PACKS")


def _is_ceiling(value: Any) -> bool:
    return type(value) is int and value > 0  # `type(...) is int` refuses bool


def packing_probe_spec(suite: Path) -> dict[str, Any]:
    """The packing-probe ceilings, read from `suite` without importing it.

    tests/test_ci_pack.py owns them as plain module-level literals. The result
    is JSON-safe because it is handed to the base worker on its command line.
    A missing, computed, or malformed value is a refusal, never an empty probe
    set: an empty set would pass every PR without measuring anything.
    """
    try:
        tree = ast.parse(suite.read_text(encoding="utf-8"), filename=str(suite))
    except (OSError, SyntaxError, ValueError) as exc:
        raise ContractDeltaError(f"cannot read the packing probes from {suite}: {exc}") from exc
    values: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in _PROBE_SPEC_NAMES:
                try:
                    values[target.id] = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError) as exc:
                    raise ContractDeltaError(
                        f"{suite}: {target.id} must be a plain literal: {exc}"
                    ) from exc
    probes = values.get("PACKING_PROBES")
    max_packs = values.get("PACKING_PROBE_MAX_PACKS")
    well_formed = (
        isinstance(probes, (tuple, list))
        and len(probes) > 0
        and all(
            isinstance(probe, (tuple, list))
            and len(probe) == 3
            and isinstance(probe[0], str)
            and probe[0] != ""
            and _is_ceiling(probe[1])
            and _is_ceiling(probe[2])
            for probe in probes
        )
        and len({probe[0] for probe in probes}) == len(probes)
        and _is_ceiling(max_packs)
    )
    if not well_formed:
        raise ContractDeltaError(
            f"{suite} must define PACKING_PROBES as a non-empty tuple of unique "
            f"(path, max_jobs, max_weight) rows with positive int ceilings, and "
            f"PACKING_PROBE_MAX_PACKS as a positive int; found "
            f"PACKING_PROBES={probes!r}, PACKING_PROBE_MAX_PACKS={max_packs!r}"
        )
    return {"probes": [list(probe) for probe in probes], "max_packs": max_packs}


def _head_control_plane_findings(spec: dict[str, Any]) -> dict[str, Any]:
    """The three control-plane classes for THIS process's tree.

    Same shared functions the absolute guards fail on, under the same exact-tree
    inventory `_head_findings` binds. The result is JSON round-tripped so the
    head's rows reach `compute_delta` in exactly the form the base worker's do.
    """
    manifest = ROOT / MANIFEST_REL
    probes = [tuple(probe) for probe in spec["probes"]]
    censuses = (
        ("probes", lambda: packing_probe_measurements(
            manifest, probes, max_packs=spec["max_packs"]
        )),
        ("skip_only", skip_only_findings),
        ("trigger_gaps", trigger_gap_findings),
    )
    payload: dict[str, Any] = {"timings": {}}
    with _tracked_tree_inventory(ROOT):
        for name, census in censuses:
            started = time.monotonic()
            payload[name] = census()
            payload["timings"][name] = round(time.monotonic() - started, 1)
    return json.loads(json.dumps(payload))


# The base worker's control-plane censuses, kept as their own source string so
# tests/test_contract_delta.py can exec them against fake guard modules and
# prove the bootstrap rows equal the shared functions' rows. They read the
# worker's `importlib`, `time`, `MANIFEST` and `SPEC` globals. Each returns the
# guard's RAW finding rows; the projection onto finding identity happens once,
# in `compute_delta`, for both sides alike.
_WORKER_CONTROL_PLANE_SOURCE = r'''
def _guard_module(name):
    """The guard module, or None when this base predates it entirely."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise  # the guard exists but one of its own imports is broken
        return None


def _probe_rows():
    """tests/test_ci_pack.py's packing-probe measurement, at the HEAD's ceilings."""
    probes = [tuple(probe) for probe in SPEC["probes"]]
    pack = importlib.import_module("scripts.run_ci_pack")
    measure = getattr(pack, "packing_probe_measurements", None)
    if measure is not None:
        return measure(MANIFEST, probes, max_packs=SPEC["max_packs"])
    # BOOTSTRAP: a base that predates packing_probe_measurements. The same
    # measurement from the primitives it is built on.
    jobs, _note = pack.infer_job_scopes(pack.load_legacy_jobs(MANIFEST))
    rows = []
    for probe, max_jobs, max_weight in probes:
        selected, reason = pack.select_jobs(jobs, [probe])
        weight = sum(job.weight for job in selected)
        rows.append({
            "probe": probe,
            "jobs": len(selected),
            "weight": weight,
            "packs": max(1, min(12, -(-weight // pack.PACK_TARGET_SECONDS))),
            "max_jobs": max_jobs,
            "max_weight": max_weight,
            "max_packs": SPEC["max_packs"],
            "job_ids": sorted(job.job_id for job in selected),
            "reason": reason,
        })
    return rows


def _skip_only_rows():
    guard = _guard_module("scripts.check_skip_only_suites")
    if guard is None:
        return None
    findings = getattr(guard, "skip_only_findings", None)
    if findings is not None:
        return findings()
    # BOOTSTRAP: a base that predates skip_only_findings.
    return [row for row in guard.census() if row["status"] == "SKIP-ONLY"]


def _trigger_gap_rows():
    guard = _guard_module("scripts.check_ci_trigger_closure")
    if guard is None:
        return None
    findings = getattr(guard, "trigger_gap_findings", None)
    if findings is not None:
        return findings()
    # BOOTSTRAP: a base that predates trigger_gap_findings. Depth 1 is the gate.
    return [row for row in guard.census(depth=1) if row["status"] == "GAP"]


def _control_plane_findings():
    """probes, skip_only and trigger_gaps rows for this tree, with their seconds."""
    payload = {"timings": {}}
    for name, census in (
        ("probes", _probe_rows),
        ("skip_only", _skip_only_rows),
        ("trigger_gaps", _trigger_gap_rows),
    ):
        started = time.monotonic()
        payload[name] = census()
        payload["timings"][name] = round(time.monotonic() - started, 1)
    return payload
'''

# Deliberately references the pre-existing (pre-this-PR) primitive names in its
# fallback branch — see the module docstring's "BOOTSTRAP FALLBACK" section for
# why this cannot instead just import scripts.check_contract_delta itself (this
# file does not exist on a base tree that predates this gate).
_WORKER_SOURCE = r'''
from contextlib import contextmanager
import importlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, ".")
MANIFEST = Path(".github/ci/legacy-jobs.yml")
# The head's packing-probe ceilings (check_contract_delta.packing_probe_spec).
SPEC = json.loads(sys.argv[1])


def _fail(message: str) -> None:
    print(json.dumps({"error": message}))
    sys.exit(1)
''' + _WORKER_CONTROL_PLANE_SOURCE + r'''

@contextmanager
def _tracked_tree_inventory():
    """Bind exact tracked-path existence when this base supports the v1 oracle."""
    try:
        deps = importlib.import_module("scripts.ci_scope_dependencies")
    except ModuleNotFoundError as exc:
        if exc.name != "scripts.ci_scope_dependencies":
            raise
        # Bootstrap compatibility only: a deliberately old base can predate the
        # inventory module. Any nested missing import still fails the worker.
        yield
        return
    planner_tracked_path_inventory = getattr(
        deps, "planner_tracked_path_inventory", None
    )
    write_tracked_path_inventory = getattr(
        deps, "write_tracked_path_inventory", None
    )
    if planner_tracked_path_inventory is None or write_tracked_path_inventory is None:
        # A base between the dependency module's birth and the v1 inventory API.
        yield
        return

    tested_tree_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout.strip()
    root = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="contract-delta-inventory-") as tmp:
        inventory = Path(tmp) / "tracked-paths.v1"
        write_tracked_path_inventory(inventory, tested_tree_sha, root=root)
        with planner_tracked_path_inventory(
            inventory, tested_tree_sha, root=root
        ):
            yield


try:
    from scripts.run_ci_pack import curated_exclusive_closure_findings as _closure_fn
    from scripts.audit_unrun_tests import gated_unrun_suites as _suites_fn
except ImportError:
    _closure_fn = None
    _suites_fn = None

if _closure_fn is not None and _suites_fn is not None:
    try:
        with _tracked_tree_inventory():
            started = time.monotonic()
            closure = {
                jid: sorted(paths) for jid, paths in _closure_fn(MANIFEST).items()
            }
            suites = sorted(_suites_fn())
            legacy_seconds = round(time.monotonic() - started, 1)
            control = _control_plane_findings()
    except Exception as exc:  # noqa: BLE001 — surfaced as a script-level refusal
        _fail(f"{type(exc).__name__}: {exc}")
    control["timings"]["closure_and_suites"] = legacy_seconds
    print(json.dumps({"closure": closure, "suites": suites, **control}))
    sys.exit(0)

# BOOTSTRAP: base tree predates scripts.run_ci_pack.curated_exclusive_closure_findings
# / scripts.audit_unrun_tests.gated_unrun_suites. Rebuild the identical computation
# from the primitives both are built on -- unchanged, pre-existing names.
try:
    from scripts.run_ci_pack import (
        load_legacy_jobs, infer_job_scopes, replace, _matches_any,
    )
    from scripts.audit_unrun_tests import (
        census, _load_baseline, _load_waivers, _validate_waivers,
    )
except Exception as exc:  # noqa: BLE001
    _fail(f"cannot import CI-contract primitives: {type(exc).__name__}: {exc}")

try:
    with _tracked_tree_inventory():
        started = time.monotonic()
        jobs = [replace(j, exclusive=False) for j in load_legacy_jobs(MANIFEST)]
        inferred, _note = infer_job_scopes(jobs)
        would_infer = {j.job_id: j for j in inferred}
        declared = {j.job_id: j for j in load_legacy_jobs(MANIFEST) if j.exclusive}
        closure = {}
        for job_id, job in sorted(declared.items()):
            own_closure = [p for p in would_infer[job_id].paths if "*" not in p]
            if not own_closure:
                _fail(f"{job_id} derives no closure — curation cannot be checked")
            uncovered = sorted(p for p in own_closure if not _matches_any(job.paths, p))
            if uncovered:
                closure[job_id] = uncovered

        rows = census()
        unrun = sorted(r["test"] for r in rows)
        baseline = _load_baseline()
        normalized, malformed = _validate_waivers(_load_waivers())
        if malformed:
            _fail("malformed waivers: " + "; ".join(malformed))
        suites = sorted(r for r in unrun if r not in baseline and r not in normalized)
        legacy_seconds = round(time.monotonic() - started, 1)
        control = _control_plane_findings()
except SystemExit:
    raise
except Exception as exc:  # noqa: BLE001
    _fail(f"{type(exc).__name__}: {exc}")

control["timings"]["closure_and_suites"] = legacy_seconds
print(json.dumps({"closure": closure, "suites": suites, **control}))
'''


def _start_worker(repo_root: Path, spec: dict[str, Any]) -> subprocess.Popen:
    """Launch the whole-repo census for `repo_root` WITHOUT waiting for it.

    Paired with `_finish_worker`. Split out of the pre-2026-08-19 single
    blocking call so a caller can overlap this subprocess's wall time with
    other work (`run()` overlaps it with the in-process head computation —
    see "CONCURRENT HEAD/BASE" in the module docstring) instead of paying for
    them one after another. `spec` is the head's packing-probe ceilings
    (`packing_probe_spec`), so the base is measured against the same ones.
    """
    return subprocess.Popen(
        [sys.executable, "-c", _WORKER_SOURCE, json.dumps(spec)],
        cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


# 600 -> 1800 (2026-09-27): the worker now also runs the three control-plane
# censuses, about +55% on top of the ~6 minutes closure + suites already took
# on the hosted 2-core runner, which put 600 s inside the normal run time. The
# job's own 45-minute timeout stays the outer bound.
WORKER_TIMEOUT_SECONDS = 1800


def _finish_worker(
    proc: subprocess.Popen, repo_root: Path, *, timeout: int = WORKER_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """Join a `_start_worker` process and parse its result.

    Same error handling the old single-shot `_run_worker` had: a nonzero exit,
    unparseable stdout, or an explicit ``{"error": ...}`` payload all raise
    `ContractDeltaError` rather than handing the caller a malformed result.
    """
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise ContractDeltaError(
            f"finding computation timed out after {timeout}s in {repo_root}"
        )
    stdout = stdout.strip()
    if proc.returncode != 0:
        detail = stdout or stderr.strip() or "(no output)"
        raise ContractDeltaError(f"finding computation failed in {repo_root}: {detail}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ContractDeltaError(
            f"finding computation produced unparseable output in {repo_root}: {exc}\n{stdout}"
        ) from exc
    if "error" in payload:
        raise ContractDeltaError(f"finding computation refused in {repo_root}: {payload['error']}")
    return payload


def _run_worker(repo_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Findings for an ARBITRARY tree, run and awaited synchronously.

    Thin blocking wrapper over `_start_worker`/`_finish_worker` for callers
    (and the `repo_root != ROOT` branch of `run()` below) that have no other
    work to overlap it with.
    """
    return _finish_worker(_start_worker(repo_root, spec), repo_root)


def _kill_quietly(proc: subprocess.Popen) -> None:
    """Best-effort cleanup for a worker `run()` is abandoning on another error.

    Never raises: this runs from an `except` block, and a cleanup failure must
    not shadow the real error already being propagated.
    """
    try:
        proc.kill()
        proc.communicate(timeout=30)
    except Exception:  # noqa: BLE001 — best-effort only, see docstring
        pass


# ─────────────────────────────────────────────────────────────────────────────
# base-tree materialization
# ─────────────────────────────────────────────────────────────────────────────

def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300,
    )
    if completed.returncode != 0:
        raise ContractDeltaError(
            f"git {' '.join(args)} failed in {cwd}: {completed.stderr.strip()}"
        )
    return completed.stdout


TEMP_ROOT_ENV = "CONTRACT_DELTA_TMP_ROOT"
STORAGE_POLICY = Path.home() / ".config" / "mastermind" / "worktree-storage.json"


def base_tree_temp_root() -> Path | None:
    """Where the throwaway base worktree is minted; None means `tempfile`'s default.

    Precedence: `$CONTRACT_DELTA_TMP_ROOT` (an existing directory) > the host's
    external-volume policy (`~/.config/mastermind/worktree-storage.json`, whose
    `root` is used only while its `mount_point` is actually mounted) > None.
    Fail-open by design: this is a throwaway tree, not a session worktree, so an
    absent volume must never block the gate — it just costs internal disk.
    """
    override = os.environ.get(TEMP_ROOT_ENV)
    if override:
        candidate = Path(override)
        return candidate if candidate.is_dir() else None
    try:
        policy = json.loads(STORAGE_POLICY.read_text())
        mount, root = Path(policy["mount_point"]), Path(policy["root"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not (mount.is_dir() and os.path.ismount(mount) and root.is_dir()):
        return None
    candidate = root / "tmp" / "contract-delta"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return candidate


def caller_sparse_cone(repo_root: Path) -> list[str] | None:
    """The calling checkout's cone-mode sparse include set, or None when it is a
    full checkout (or uses non-cone patterns, which we do not try to mirror)."""
    try:
        enabled = _git("config", "--get", "core.sparseCheckout", cwd=repo_root).strip()
        cone = _git("config", "--get", "core.sparseCheckoutCone", cwd=repo_root).strip()
    except ContractDeltaError:
        return None
    if enabled != "true" or cone != "true":
        return None
    listed = _git("sparse-checkout", "list", cwd=repo_root).split()
    return listed or None


def materialize_base_tree(base_ref: str, *, repo_root: Path = ROOT):
    """A throwaway detached worktree at `base_ref`, plus its cleanup callable.

    Never under any fleet worktree-GC root (`.claude/worktrees/` and siblings) —
    `tempfile.mkdtemp()` is outside every one of them, matching
    `scripts/prophet_pit_replay.py`'s `resolve_or_create_vintage_worktree`.

    MIRRORS THE CALLER'S SPARSE CONE (2026-09-14). A session worktree on this
    fleet is sparse (config/sparse_worktree.json: data/, site/, mockups/,
    verify_shots/ omitted — 87% of a 3.8 GiB tree), yet the base tree used to be
    a FULL checkout every time: 3-6 GB written per gate run, ~20 GB/h across the
    Studio's concurrent sessions, and every SIGKILLed run left the half-built
    tree behind (wave-2 freed 184 GB of them; it was gone again in ~9 h). The base
    tree now takes exactly the caller's `git sparse-checkout list` cone, so both
    censuses see the SAME set of directories — which is also the only way the
    delta is well-defined: a full base against a sparse head reports every suite
    under an omitted directory as "fixed on head" and hides it. A full caller (CI
    runners, the operator root) still gets a full base tree, unchanged.
    Placement follows `base_tree_temp_root()` (external volume when the host has
    one); the `contract-delta-base-` prefix is what the fleet sweeper keys on.
    """
    base_sha = _git("rev-parse", f"{base_ref}^{{commit}}", cwd=repo_root).strip()
    cone = caller_sparse_cone(repo_root)
    tmpdir = Path(tempfile.mkdtemp(prefix="contract-delta-base-", dir=base_tree_temp_root()))
    tmpdir.rmdir()  # `git worktree add` refuses a pre-existing non-empty target

    def cleanup() -> None:
        try:
            _git("worktree", "remove", "--force", str(tmpdir), cwd=repo_root)
        except ContractDeltaError:
            shutil.rmtree(tmpdir, ignore_errors=True)
            try:
                _git("worktree", "prune", cwd=repo_root)
            except ContractDeltaError:
                pass

    if cone is None:
        _git("worktree", "add", "--detach", str(tmpdir), base_sha, cwd=repo_root)
        return tmpdir, base_sha, cleanup
    try:
        _git("worktree", "add", "--detach", "--no-checkout", str(tmpdir), base_sha, cwd=repo_root)
        _git("sparse-checkout", "set", "--cone", "--", *cone, cwd=tmpdir)
        _git("read-tree", "-mu", "HEAD", cwd=tmpdir)
    except BaseException:
        cleanup()
        raise
    return tmpdir, base_sha, cleanup


# ─────────────────────────────────────────────────────────────────────────────
# delta semantics — pure, unit-testable independent of git/subprocess
# ─────────────────────────────────────────────────────────────────────────────

def _closure_pairs(closure: dict[str, list[str]]) -> set[tuple[str, str]]:
    return {(job_id, path) for job_id, paths in closure.items() for path in paths}


class ProbeFinding(NamedTuple):
    """A packing probe over one ceiling on the head."""

    probe: str
    axis: str  # "jobs" | "weight" | "packs"
    measured: int
    ceiling: int
    base: int | None  # the base tree's value on this axis; None = base has no row
    entrants: tuple[str, ...]  # jobs the head selects for this probe that the base does not


class SkipOnlyFinding(NamedTuple):
    """A skip gate that no job naming its suite satisfies."""

    test: str
    gate: str
    needs: tuple[str, ...]
    naming_jobs: tuple[str, ...]


class TriggerGapFinding(NamedTuple):
    """One subject a suite reads that no path filter of a gate running it matches."""

    test: str
    subject: str
    why: str
    filters: tuple[str, ...]
    run_by: tuple[str, ...]


def _probe_delta(
    head_rows: list[dict] | None, base_rows: list[dict] | None
) -> tuple[list[ProbeFinding], list[ProbeFinding]]:
    """Breaches of the head's probe rows, split by the base's value on the same axis.

    Both sides were measured against the head's ceilings (see "ONE SET OF
    CEILINGS"), so a base value above the ceiling is a base breach of that same
    ceiling. Inherited: the head is no further over than the base. Introduced:
    everything else, including a head pushed further over an inherited breach.
    """
    head_rows = head_rows or []
    base_by_probe = {row["probe"]: row for row in base_rows or []}
    head_by_probe = {row["probe"]: row for row in head_rows}
    introduced: list[ProbeFinding] = []
    inherited: list[ProbeFinding] = []
    for probe, axis, measured, ceiling in packing_probe_breaches(head_rows):
        base_row = base_by_probe.get(probe)
        base_value = None if base_row is None else base_row[axis]
        entrants: tuple[str, ...] = ()
        if base_row is not None:
            entrants = tuple(sorted(
                set(head_by_probe[probe]["job_ids"]) - set(base_row["job_ids"])
            ))
        finding = ProbeFinding(probe, axis, measured, ceiling, base_value, entrants)
        if base_value is not None and measured <= base_value:
            inherited.append(finding)
        else:
            introduced.append(finding)
    return sorted(introduced), sorted(inherited)


def _skip_only_index(rows: list[dict] | None) -> dict[tuple[str, str], SkipOnlyFinding]:
    return {
        (row["test"], row["gate"]): SkipOnlyFinding(
            row["test"],
            row["gate"],
            tuple(row.get("needs") or ()),
            tuple(sorted(row.get("naming_jobs") or ())),
        )
        for row in rows or []
    }


def _trigger_gap_index(rows: list[dict] | None) -> dict[tuple[str, str], TriggerGapFinding]:
    return {
        (row["test"], subject): TriggerGapFinding(
            row["test"],
            subject,
            str((row.get("why") or {}).get(subject, "?")),
            tuple(row.get("filters") or ()),
            tuple(row.get("run_by") or ()),
        )
        for row in rows or []
        for subject in row.get("gaps") or ()
    }


def _keyed_delta(head: dict, base: dict) -> tuple[list, list]:
    """Head findings whose identity the base lacks (introduced) and shares (inherited)."""
    return (
        [head[key] for key in sorted(head.keys() - base.keys())],
        [head[key] for key in sorted(head.keys() & base.keys())],
    )


def compute_delta(head: dict[str, Any], base: dict[str, Any]) -> dict[str, list]:
    """``head - base`` (introduced) and ``head & base`` (inherited), every class.

    Finding identity: ``(job_id, path)`` pairs for closure misses, bare suite
    path strings for unwired suites, and the control-plane identities in the
    module docstring. A control-plane class appears in the delta only when one
    of the payloads carries it.
    """
    head_pairs = _closure_pairs(head.get("closure", {}))
    base_pairs = _closure_pairs(base.get("closure", {}))
    head_suites = set(head.get("suites", []))
    base_suites = set(base.get("suites", []))
    delta: dict[str, list] = {
        "introduced_closure": sorted(head_pairs - base_pairs),
        "inherited_closure": sorted(head_pairs & base_pairs),
        "introduced_suites": sorted(head_suites - base_suites),
        "inherited_suites": sorted(head_suites & base_suites),
    }
    carried = {name for name in CONTROL_PLANE_CLASSES if name in head or name in base}
    if "probes" in carried:
        delta["introduced_probes"], delta["inherited_probes"] = _probe_delta(
            head.get("probes"), base.get("probes")
        )
    if "skip_only" in carried:
        delta["introduced_skip_only"], delta["inherited_skip_only"] = _keyed_delta(
            _skip_only_index(head.get("skip_only")),
            _skip_only_index(base.get("skip_only")),
        )
    if "trigger_gaps" in carried:
        delta["introduced_trigger_gaps"], delta["inherited_trigger_gaps"] = _keyed_delta(
            _trigger_gap_index(head.get("trigger_gaps")),
            _trigger_gap_index(base.get("trigger_gaps")),
        )
    return delta


def has_introduced_findings(delta: dict[str, list]) -> bool:
    return any(found for key, found in delta.items() if key.startswith("introduced_"))


def _count(delta: dict[str, list], prefix: str) -> int:
    return sum(len(found) for key, found in delta.items() if key.startswith(prefix))


# ─────────────────────────────────────────────────────────────────────────────
# reporting — every line a bare, line-starting print (house GitHub-annotation law)
# ─────────────────────────────────────────────────────────────────────────────

def format_report(delta: dict[str, list]) -> list[str]:
    """Annotation lines for `delta` — ::error for introduced, ::notice for inherited.

    Returned as a list (not printed directly) so the unit tests can assert on
    exact lines without capturing stdout.
    """
    lines: list[str] = []
    for job_id, path in delta["introduced_closure"]:
        lines.append(
            f"::error title=contract-delta::{job_id}: import closure now reaches "
            f"{path}, which {MANIFEST_REL}'s declared `paths:` for {job_id} does "
            f"not cover — widen {job_id}'s `paths:` to include {path} "
            f"(widening is always the safe direction)"
        )
    for suite in delta["introduced_suites"]:
        lines.append(
            f"::error title=contract-delta::{suite} is a new pytest suite named "
            f"by no run: step in any workflow — wire it into the job that owns "
            f"its subject in {MANIFEST_REL}, or add a reasoned row to "
            f"config/unrun_test_waivers.yml"
        )
    for probe in delta.get("introduced_probes", []):
        base = "no base row" if probe.base is None else f"base {probe.base:,}"
        lines.append(
            f"::error title=contract-delta::packing probe {probe.probe}: an "
            f"ordinary code PR touching it now selects {probe.measured:,} "
            f"{PROBE_AXIS_UNITS[probe.axis]}, over the ceiling {probe.ceiling:,} "
            f"({base}); newly selected: {_listing(probe.entrants, 'none')}. "
            f"{PACKING_PROBE_SUITE_REL}::"
            f"test_exclusive_curation_narrows_ordinary_code_prs reds on this after "
            f"merge — narrow the selection (curate the entrant with `scope: "
            f"exclusive` and exact `paths:` in {MANIFEST_REL}, or drop the edge "
            f"that pulled it in), or, if the wider selection is intended, re-base "
            f"that ceiling in {PACKING_PROBE_SUITE_REL} PACKING_PROBES with the "
            f"measurement recorded in the test's docstring"
        )
    for gate in delta.get("introduced_skip_only", []):
        lines.append(
            f"::error title=contract-delta::{gate.test}: its skip gate "
            f"`{gate.gate}` needs {_listing(gate.needs, gate.gate)}, which no job "
            f"that runs the suite installs (run by: "
            f"{_listing(gate.naming_jobs, 'no job')}), so on the merge gate it "
            f"only ever SKIPS — install it in a job that runs the suite, or run "
            f"the suite in a job that already has it "
            f"(python3 scripts/check_skip_only_suites.py --report)"
        )
    for gap in delta.get("introduced_trigger_gaps", []):
        lines.append(
            f"::error title=contract-delta::{gap.test} reads {gap.subject} "
            f"({gap.why}), but no `on.pull_request.paths` entry in "
            f"{_listing(gap.filters, 'the workflow path filter')} matches it — a "
            f"PR touching only {gap.subject} never starts the job that runs the "
            f"suite ({_listing(gap.run_by, 'none recorded', limit=2)}). "
            f"Add - \"{gap.subject}\" to that paths list; if the "
            f"literal is data (a file NAME the suite never opens), mark the "
            f"statement `# ci-trigger-closure: data` instead"
        )
    for job_id, path in delta["inherited_closure"]:
        lines.append(
            f"::notice title=contract-delta::{job_id}: {path} is already "
            f"uncovered on this PR's base — pre-existing, not introduced by "
            f"this PR; heal separately"
        )
    for suite in delta["inherited_suites"]:
        lines.append(
            f"::notice title=contract-delta::{suite} is already unwired on "
            f"this PR's base — pre-existing, not introduced by this PR"
        )
    for probe in delta.get("inherited_probes", []):
        lines.append(
            f"::notice title=contract-delta::packing probe {probe.probe}: "
            f"{probe.measured:,} {PROBE_AXIS_UNITS[probe.axis]} is over the "
            f"ceiling {probe.ceiling:,}, and this PR's base is already at "
            f"{probe.base:,} — pre-existing, not introduced by this PR; heal "
            f"separately"
        )
    for gate in delta.get("inherited_skip_only", []):
        lines.append(
            f"::notice title=contract-delta::{gate.test}: skip gate "
            f"`{gate.gate}` is already skip-only on this PR's base — "
            f"pre-existing, not introduced by this PR"
        )
    for gap in delta.get("inherited_trigger_gaps", []):
        lines.append(
            f"::notice title=contract-delta::{gap.test}: {gap.subject} is "
            f"already an unreachable subject on this PR's base — pre-existing, "
            f"not introduced by this PR"
        )
    return lines


PROBE_AXIS_UNITS = {"jobs": "jobs", "weight": "weight-seconds", "packs": "packs"}


def _listing(items: Iterable[str], empty: str, *, limit: int = 8) -> str:
    items = list(items)
    if not items:
        return empty
    shown = ", ".join(items[:limit])
    return shown if len(items) <= limit else f"{shown} (+{len(items) - limit} more)"


def measurement_lines(head: dict[str, Any], base: dict[str, Any]) -> list[str]:
    """What the control-plane classes measured on each side, for the CI log.

    Plain lines except one ::notice per class the base predates (see "ONE
    PROJECTION" in the module docstring): that class has nothing to inherit, so
    every head finding in it counts as introduced, and the log must say why.
    """
    lines: list[str] = []
    base_rows = {row["probe"]: row for row in base.get("probes") or []}

    def shape(row: dict[str, Any]) -> str:
        return f"{row['jobs']} jobs / {row['weight']:,} s / {row['packs']} packs"

    for row in head.get("probes") or []:
        base_row = base_rows.get(row["probe"])
        lines.append(
            f"contract-delta: probe {row['probe']}: head {shape(row)}; base "
            f"{shape(base_row) if base_row else 'not measured'}; ceilings "
            f"{row['max_jobs']} / {row['max_weight']:,} / {row['max_packs']}"
        )
    for side, payload in (("head", head), ("base", base)):
        timings = payload.get("timings") or {}
        if timings:
            lines.append(
                f"contract-delta: {side} census seconds: "
                + ", ".join(f"{name} {seconds:.1f}" for name, seconds in sorted(timings.items()))
            )
    for name in CONTROL_PLANE_CLASSES:
        if name in base and base[name] is None:
            lines.append(
                f"::notice title=contract-delta::this PR's base predates the "
                f"{name} guard, so it has nothing to inherit — every {name} "
                f"finding on this head counts as introduced"
            )
    return lines


def _require_control_plane_classes(payload: dict[str, Any], side: str) -> None:
    """Refuse a payload that did not run every class: absence is not a pass."""
    missing = [name for name in CONTROL_PLANE_CLASSES if name not in payload]
    malformed = [
        name for name in CONTROL_PLANE_CLASSES
        if name in payload and payload[name] is not None and not isinstance(payload[name], list)
    ]
    if missing or malformed:
        raise ContractDeltaError(
            f"{side} census is incomplete (missing: {missing or 'none'}; "
            f"malformed: {malformed or 'none'}) — refusing to diff it"
        )
    if side == "head" and any(payload[name] is None for name in CONTROL_PLANE_CLASSES):
        raise ContractDeltaError("head census ran without a control-plane guard module")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def run(base_ref: str, *, repo_root: Path = ROOT) -> int:
    # CONCURRENT HEAD/BASE (see module docstring): materialize the base tree,
    # launch its worker WITHOUT waiting, then do the head computation while
    # that subprocess runs, then join. Both sides are an independent
    # whole-repo census, so this overlaps the two dominant costs instead of
    # paying for them serially.
    run_started = time.monotonic()
    # Read before any tree is minted: a malformed ceiling is a refusal, and the
    # base worker needs these exact values (see "ONE SET OF CEILINGS").
    spec = packing_probe_spec(repo_root / PACKING_PROBE_SUITE_REL)
    base_tree, base_sha, cleanup = materialize_base_tree(base_ref, repo_root=repo_root)
    try:
        base_proc = _start_worker(base_tree, spec)
        try:
            if repo_root == ROOT:
                started = time.monotonic()
                head = _head_findings()
                legacy_seconds = round(time.monotonic() - started, 1)
                head.update(_head_control_plane_findings(spec))
                head["timings"]["closure_and_suites"] = legacy_seconds
            else:
                head = _run_worker(repo_root, spec)
        except ValueError as exc:
            # curated_exclusive_closure_findings's own hard-fail (a curated job
            # derives no closure at all) -- a script refusal, not a diffable
            # finding. The base worker is still running; it would otherwise
            # leak past this function's return.
            _kill_quietly(base_proc)
            raise ContractDeltaError(f"finding computation refused on this PR's head: {exc}") from exc
        except BaseException:
            _kill_quietly(base_proc)
            raise
        base = _finish_worker(base_proc, base_tree)
    finally:
        cleanup()

    _require_control_plane_classes(head, "head")
    _require_control_plane_classes(base, f"base {base_sha[:12]}")
    delta = compute_delta(head, base)
    for line in measurement_lines(head, base) + format_report(delta):
        print(line, flush=True)

    print(
        f"contract-delta: {_count(delta, 'introduced_')} introduced, "
        f"{_count(delta, 'inherited_')} inherited (base {base_sha[:12]})",
        flush=True,
    )
    print(
        f"contract-delta: wall {time.monotonic() - run_started:.1f} s",
        flush=True,
    )
    return 1 if has_introduced_findings(delta) else 0


def _raise_on_sigterm(signum: int, frame: Any) -> None:
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True,
                    help="ref or SHA to diff against (e.g. origin/main, or a PR's base SHA)")
    args = ap.parse_args(argv)
    # A cancelled CI job (timeout-minutes, workflow cancel) delivers SIGTERM; the
    # default disposition kills the interpreter without unwinding, so `run()`'s
    # `finally: cleanup()` never ran and the base worktree stayed on disk. Turn
    # it into a normal exception so the throwaway tree is removed on the way out.
    signal.signal(signal.SIGTERM, _raise_on_sigterm)
    try:
        return run(args.base)
    except ContractDeltaError as exc:
        print(f"::error title=contract-delta::{exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
