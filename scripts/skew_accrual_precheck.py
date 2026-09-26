"""Precheck: does scripts.build_options_skew expose --accrue?

WHY THIS EXISTS
───────────────
The skew-accrual runner (ops/launchd/run_skew_accrual.sh) calls
`python -m scripts.build_options_skew --accrue`. The `--accrue` flag is
shipped by the W2-1b sibling branch (a source-stamped canonical-wins
ledger upsert into data/options_skew/snapshots.parquet). On the pre-W2-1b
tree the flag does NOT exist — the runner's call to `--accrue` either
silently runs main() (no argparse means the unknown arg is dropped) and
writes site/options_skew/latest.json (a publish-side artifact the
render-host side is pinned to LEGACY during the migration), or argparse
rejects the unknown flag with exit 2.

Both outcomes corrupt the lane. The first races the render-host side
(W2-1b pinned render to polygon_gex until W2-3); the second fails late
inside the launchd log without a clear operator-actionable name. The
runner MUST detect the missing flag BEFORE running the call, so the
operator sees a one-line named-reason failure rather than a silent
pollution.

DETECTION
─────────
The W2-1b branch adds the `--accrue` argparse option to
scripts/build_options_skew.py. The precheck reads that file's source and
looks for the literal `--accrue` — covers both `add_argument("--accrue",
...)` and any equivalent spelling (`"--accrue"` / `'--accrue'`). Reading
the source is safer than executing `python -m scripts.build_options_skew
--help`: on a pre-W2-1b tree (no argparse), `--help` is silently dropped
and main() runs, which writes site/options_skew/latest.json — exactly the
pollution this helper is meant to prevent.

EXIT CODES (load-bearing — the runner reads them)
  0  EXIT_OK            — `--accrue` is exposed; safe to run.
  4  EXIT_FLAG_MISSING  — pre-W2-1b tree; runner must abort loudly with
                          the named reason. Reversibility: when W2-1b
                          merges, this returns 0 on the next run.

USAGE
  scripts/skew_accrual_precheck.py --repo PATH
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Repo-root pin so `lib.*` / `engine.*` / `scripts.*` would resolve from
# THIS repo under bare `python scripts/skew_accrual_precheck.py --repo ...`
# (the W2-1b audit-style smoke the operator runs from the lane checkout)
# exactly the same way `python -m scripts.skew_accrual_precheck --repo ...`
# resolves them. Mirrors the strong-pin idiom enforced by
# `tests/test_check_script_import_pinning.py` for every scripts/** entry.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

EXIT_OK = 0
EXIT_FLAG_MISSING = 4

# The literal we look for in scripts/build_options_skew.py. W2-1b adds
# argparse.add_argument("--accrue", ...); the regex matches that exact
# argparse spell and any equivalent (e.g. an add_argument_group entry that
# references the same flag). A bare comment that mentions --accrue is
# NOT a positive match — the regex anchors to a string-literal token so
# docstring references don't false-positive on a future revert.
_ACCRUE_TOKEN_RE = re.compile(r"""['"]--accrue['"]""")


def _read_source(repo: Path) -> tuple[str | None, str]:
    """Read scripts/build_options_skew.py from the repo checkout.

    Returns (source_or_None, reason). reason is one of:
      'ok'                — file located and read.
      'missing_file'      — the script is not present.
      'read_error'        — IO error (rare; surfaced as the named reason).
    """
    p = repo / "scripts" / "build_options_skew.py"
    if not p.is_file():
        return None, "missing_file"
    try:
        return p.read_text(encoding="utf-8"), "ok"
    except OSError:
        return None, "read_error"


def check(repo: Path) -> tuple[int, dict]:
    """Run the precheck.

    Returns (exit_code, info_dict). The info_dict's `reason` is the named
    operator-actionable message — the runner prints it verbatim.
    """
    info: dict = {"repo": str(repo)}
    src, read_reason = _read_source(repo)
    if src is None:
        info["read_reason"] = read_reason
        info["reason"] = (f"scripts/build_options_skew.py {read_reason} — "
                         "cannot determine --accrue availability; aborting.")
        return EXIT_FLAG_MISSING, info
    if _ACCRUE_TOKEN_RE.search(src):
        info["reason"] = "--accrue token found in scripts/build_options_skew.py"
        return EXIT_OK, info
    info["reason"] = (
        "--accrue NOT found in scripts/build_options_skew.py — W2-1b has "
        "not landed on origin/main yet. The W2-2 lane requires the --accrue "
        "flag (the source-stamped canonical-wins ledger upsert) from W2-1b. "
        "Falling back to a full run would write site/options_skew/latest.json "
        "and race the render-host side that W2-1b pinned to legacy — DO NOT "
        "do that. Wait for W2-1b to merge, then re-run.")
    return EXIT_FLAG_MISSING, info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scripts.skew_accrual_precheck",
        description=("Detect whether scripts.build_options_skew exposes --accrue "
                     "(W2-1b's source-stamped ledger upsert). Exit 0=ok, 4=missing.")
    )
    ap.add_argument("--repo", required=True,
                    help="Repo checkout carrying scripts/build_options_skew.py")
    args = ap.parse_args(argv)
    code, info = check(Path(args.repo))
    status_word = "OK" if code == EXIT_OK else "FLAG_MISSING"
    # One line on stdout so the runner's `status=$(...)` captures exactly
    # the status word. Verbose info goes to stderr.
    print(status_word)
    for k, v in info.items():
        print(f"  {k}={v}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())