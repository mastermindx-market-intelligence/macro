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
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = ".github/ci/legacy-jobs.yml"

sys.path.insert(0, str(ROOT))

from scripts.run_ci_pack import curated_exclusive_closure_findings  # noqa: E402
from scripts.audit_unrun_tests import gated_unrun_suites  # noqa: E402
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
from pathlib import Path

sys.path.insert(0, ".")
MANIFEST = Path(".github/ci/legacy-jobs.yml")


def _fail(message: str) -> None:
    print(json.dumps({"error": message}))
    sys.exit(1)


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
            closure = {
                jid: sorted(paths) for jid, paths in _closure_fn(MANIFEST).items()
            }
            suites = sorted(_suites_fn())
    except Exception as exc:  # noqa: BLE001 — surfaced as a script-level refusal
        _fail(f"{type(exc).__name__}: {exc}")
    print(json.dumps({"closure": closure, "suites": suites}))
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
except SystemExit:
    raise
except Exception as exc:  # noqa: BLE001
    _fail(f"{type(exc).__name__}: {exc}")

print(json.dumps({"closure": closure, "suites": suites}))
'''


def _start_worker(repo_root: Path) -> subprocess.Popen:
    """Launch the whole-repo census for `repo_root` WITHOUT waiting for it.

    Paired with `_finish_worker`. Split out of the pre-2026-08-19 single
    blocking call so a caller can overlap this subprocess's wall time with
    other work (`run()` overlaps it with the in-process head computation —
    see "CONCURRENT HEAD/BASE" in the module docstring) instead of paying for
    them one after another.
    """
    return subprocess.Popen(
        [sys.executable, "-c", _WORKER_SOURCE],
        cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _finish_worker(proc: subprocess.Popen, repo_root: Path, *, timeout: int = 600) -> dict[str, Any]:
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


def _run_worker(repo_root: Path) -> dict[str, Any]:
    """Findings for an ARBITRARY tree, run and awaited synchronously.

    Thin blocking wrapper over `_start_worker`/`_finish_worker` for callers
    (and the `repo_root != ROOT` branch of `run()` below) that have no other
    work to overlap it with.
    """
    return _finish_worker(_start_worker(repo_root), repo_root)


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


def compute_delta(head: dict[str, Any], base: dict[str, Any]) -> dict[str, list]:
    """``head - base`` (introduced) and ``head & base`` (inherited), both axes.

    Finding identity: ``(job_id, path)`` pairs for closure misses, bare suite
    path strings for unwired suites — see the module docstring.
    """
    head_pairs = _closure_pairs(head.get("closure", {}))
    base_pairs = _closure_pairs(base.get("closure", {}))
    head_suites = set(head.get("suites", []))
    base_suites = set(base.get("suites", []))
    return {
        "introduced_closure": sorted(head_pairs - base_pairs),
        "inherited_closure": sorted(head_pairs & base_pairs),
        "introduced_suites": sorted(head_suites - base_suites),
        "inherited_suites": sorted(head_suites & base_suites),
    }


def has_introduced_findings(delta: dict[str, list]) -> bool:
    return bool(delta["introduced_closure"] or delta["introduced_suites"])


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
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def run(base_ref: str, *, repo_root: Path = ROOT) -> int:
    # CONCURRENT HEAD/BASE (see module docstring): materialize the base tree,
    # launch its worker WITHOUT waiting, then do the head computation while
    # that subprocess runs, then join. Both sides are an independent
    # whole-repo census, so this overlaps the two dominant costs instead of
    # paying for them serially.
    base_tree, base_sha, cleanup = materialize_base_tree(base_ref, repo_root=repo_root)
    try:
        base_proc = _start_worker(base_tree)
        try:
            head = _head_findings() if repo_root == ROOT else _run_worker(repo_root)
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

    delta = compute_delta(head, base)
    for line in format_report(delta):
        print(line, flush=True)

    n_introduced = len(delta["introduced_closure"]) + len(delta["introduced_suites"])
    n_inherited = len(delta["inherited_closure"]) + len(delta["inherited_suites"])
    print(
        f"contract-delta: {n_introduced} introduced, {n_inherited} inherited "
        f"(base {base_sha[:12]})",
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
