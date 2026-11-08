#!/usr/bin/env python3
"""Design comparison from the incumbent semantic plan, or ordinary standalone Git.

The parent pack runner retains full load_authoritative_plan admission. This small
consumer rechecks that SAME workflow-advertised hash with the shared canonical
semantic validator and binds run/head/base/changed-file input and tested source
OFFLINE. It does not schedule, reselect, execute a pack or decide a design verdict.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.ci_semantic_proof import authoritative_plan_sha256, parse_semantic_json, SemanticProofError
MANIFEST = ".github/ci/legacy-jobs.yml"
class ComparisonError(ValueError):
    pass


def admitted_plan(args, context):
    """Recheck the existing external expectations, never trust CI_BASE_SHA alone."""
    expected = {"plan_sha256": args.expect_plan_sha,
                "tested_tree_sha": args.expect_tested_tree_sha,
                "subject_head_sha": args.expect_subject_head_sha,
                "base_sha": args.expect_base_sha}
    if not all(expected.values()) or not args.plan_json or not args.changed_files_file:
        raise ComparisonError("complete authoritative plan expectations and changed-file handle required")
    if args.plan_json.stat().st_size > 5_000_000:
        raise ComparisonError("authoritative design plan exceeds incumbent size limit")
    plan = parse_semantic_json(args.plan_json.read_bytes())
    digest = authoritative_plan_sha256(plan)
    for k, v in expected.items():
        if plan.get(k) != v:
            raise ComparisonError("design comparison expected " + k + " mismatch")
    if digest != args.expect_plan_sha:
        raise ComparisonError("design comparison authoritative plan digest mismatch")
    changed = json.loads(Path(args.changed_files_file).read_text())
    if changed is not None:
        if not isinstance(changed, list) or not all(isinstance(p, str) for p in changed):
            raise ComparisonError("malformed changed-file handle")
        # Same normalization and ordered JSON encoding as the incumbent runner.
        changed = [p for p in changed if p] if changed else []
        if not changed and json.loads(Path(args.changed_files_file).read_text()):
            changed = None
    digest = "" if changed is None else hashlib.sha256(json.dumps(changed, separators=(",", ":")).encode()).hexdigest()
    if digest != plan["changed_files_sha256"] or len(changed or []) != plan["changed_files_count"]:
        raise ComparisonError("design comparison changed-file binding mismatch")
    if args.workflow.resolve() != (Path.cwd() / MANIFEST).resolve() or args.gate != "code":
        raise ComparisonError("design comparison requires the current code-gate manifest")
    return plan


def write_authoritative_design_diff(
    plan: Mapping[str, object], *, root: Path, output: Path, kind: str,
    context: Mapping[str, str],
) -> None:
    """Compare the verified plan's immutable base offline, never moving main.

    The parent uses load_authoritative_plan; admitted_plan rechecks all four
    externally expected bindings with its shared canonical plan validator.
    This additionally binds its run/event/workflow and real checkout/source. An
    inherited CI_BASE_SHA alone is not a plan or comparison authority. This is a
    diff producer only; the existing design/visual checkers still own verdicts.
    """
    if kind not in {"style", "visual"}:
        raise ComparisonError("design comparison kind must be style or visual")
    for name, expected in (
        ("GITHUB_RUN_ID", plan["workflow_run_id"]),
        ("GITHUB_EVENT_NAME", plan["event"]),
        ("GITHUB_WORKFLOW", plan["workflow"]),
        ("GITHUB_SHA", plan["tested_tree_sha"]),
    ):
        if context.get(name) != expected:
            raise ComparisonError(f"design comparison {name} disagrees with verified plan")
    root = root.resolve()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="", GIT_NO_REPLACE_OBJECTS="1")

    def git(*args: str) -> bytes:
        result = subprocess.run(["git", *args], cwd=root, env=env,
                                capture_output=True, check=False)
        if result.returncode:
            raise ComparisonError("offline design comparison cannot verify Git source: " +
                                result.stderr.decode(errors="replace")[:1024])
        return result.stdout

    if git("rev-parse", "HEAD").decode().strip() != plan["tested_tree_sha"]:
        raise ComparisonError("design comparison checkout HEAD disagrees with verified plan")
    graft_path = Path(git("rev-parse", "--git-path", "info/grafts").decode().strip())
    if not graft_path.is_absolute():
        graft_path = root / graft_path
    if git("for-each-ref", "--format=%(refname)", "refs/replace/").strip() or graft_path.exists():
        raise ComparisonError("design comparison refuses rewritten Git ancestry")
    git("cat-file", "-e", plan["base_sha"] + "^{commit}")
    # A normal depth-one tested merge can mark HEAD shallow while all exact
    # base objects are already present. Its raw, hash-bound parent is sufficient
    # ancestry evidence; do not fetch or rewrite shallow metadata to prove it.
    parents = {line.split()[1].decode() for line in
               git("cat-file", "-p", plan["tested_tree_sha"]).split(b"\n\n", 1)[0].splitlines()
               if line.startswith(b"parent ")}
    if plan["base_sha"] != plan["tested_tree_sha"] and plan["base_sha"] not in parents:
        git("merge-base", "--is-ancestor", plan["base_sha"], plan["tested_tree_sha"])
    # The manifest and both checker implementations are real tested source;
    # there is no alternate checker or narrowed template/site path selection.
    for source in (MANIFEST, "scripts/design_semantic_comparison.py", "scripts/ci_semantic_proof.py",
                   "scripts/check_design_system.py", "scripts/check_ui_visual_evidence.py"):
        if (root / source).read_bytes() != git("show", plan["tested_tree_sha"] + ":" + source):
            raise ComparisonError("design comparison dirty or missing tested source: " + source)
    paths = ("templates",) if kind == "style" else ("templates", "site")
    git("diff", "--no-ext-diff", "--no-textconv", "--quiet", plan["tested_tree_sha"], "--", *paths)
    if git("ls-files", "--others", "--", *paths).strip():
        raise ComparisonError("design comparison has untracked scan inputs")
    diff = git("diff", "--no-ext-diff", "--no-textconv", "--unified=0",
               plan["base_sha"], plan["tested_tree_sha"], "--", *paths)
    # Write only after every binding and offline object read succeeds. A failed
    # invocation must exit nonzero; the manifest never falls through to checker.
    output.write_bytes(diff)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write-design-diff", required=True, type=Path)
    ap.add_argument("--design-diff-kind", required=True, choices=("style", "visual"))
    ap.add_argument("--base-ref", default="main")
    ap.add_argument("--workflow", type=Path, default=Path(MANIFEST))
    ap.add_argument("--gate", default="code")
    temp = os.environ.get("RUNNER_TEMP")
    ap.add_argument("--plan-json", type=Path, default=None)
    ap.add_argument("--changed-files-file", default=os.environ.get("CI_CHANGED_FILES_FILE"))
    for flag, env in (("plan-sha", "EXPECTED_PLAN_SHA"), ("tested-tree-sha", "TESTED_TREE_SHA"),
                      ("subject-head-sha", "SUBJECT_HEAD_SHA"), ("base-sha", "TESTED_BASE_SHA")):
        ap.add_argument("--expect-" + flag, default=os.environ.get(env))
    args = ap.parse_args(argv)
    semantic = os.environ.get("GITHUB_EVENT_NAME") != "base_replay" and (
        args.plan_json is not None or any(os.environ.get(k) for k in
            ("EXPECTED_PLAN_SHA", "CI_BASE_SHA", "TESTED_TREE_SHA")))
    try:
        if semantic:
            if args.plan_json is None and temp:
                args.plan_json = Path(temp)/"ci-semantic-plan/ci-plan.json"
            plan = admitted_plan(args, os.environ)
            write_authoritative_design_diff(plan, root=Path.cwd(), output=args.write_design_diff,
                                            kind=args.design_diff_kind, context=os.environ)
        else:
            # Ordinary standalone and exact-base replay keep the original fetch
            # and merge-base contract. No fallback from a failed semantic binding.
            base = args.base_ref
            label = "forward-only design ratchet" if args.design_diff_kind == "style" else "visual-evidence gate"
            if subprocess.run(["git", "fetch", "origin", base]).returncode:
                print(f"::error title=design-governance::could not fetch origin/{base}; the {label} has NO canonical comparison base and cannot run. Failing closed — an unresolvable base is an absent gate, not a degraded pass.")
                return 1
            mb = subprocess.run(["git", "merge-base", "origin/" + base, "HEAD"], capture_output=True, text=True)
            if mb.returncode:
                print(f"::error title=design-governance::no merge base with {base}; the {label} has NO canonical comparison base and cannot run. Failing closed — an unresolvable base is an absent gate, not a degraded pass.")
                return 1
            paths = ["templates"] if args.design_diff_kind == "style" else ["templates", "site"]
            diff = subprocess.run(["git", "diff", "--unified=0", mb.stdout.strip(), "HEAD", "--", *paths], capture_output=True, check=True)
            args.write_design_diff.write_bytes(diff.stdout)
        return 0
    except (ComparisonError, SemanticProofError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("::error title=design-governance::immutable design comparison refused: " + str(exc)[:1024], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
