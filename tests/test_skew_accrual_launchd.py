"""Behavioural tests for the MO-PAID-013 W2-2 skew-accrual launchd lane.

The previous test file relied on source-string assertions (literal grep on
the runner's text), which all 45 tests passed despite the measured
`if ! cmd; then rc=$?` capture bug. Those source-string tests are kept
ONLY where they pin a contract a behavioural test cannot reach (the
literal `SKEW_FRESHNESS_BYPASS`/`SKEW_DRY_RUN` env-var names, the
`git push` prohibition). The load-bearing steps — precheck, accrue,
verify-ledger, publish — are exercised END-TO-END against a fake checkout
under tmp_path.

The fake checkout has:
  - `.git/` (so the runner sees it as a worktree)
  - `scripts/skew_accrual_gate.py`, `scripts/skew_accrual_precheck.py`,
    `scripts/skew_accrual_verify_ledger.py`, `scripts/build_options_skew.py`,
    `scripts/publish_r2.py` (FAKE: each one exits a chosen code on demand)
  - `data/options_skew/` (so the ledger verify has somewhere to look)

`git` is intercepted via a stub in PATH (everything succeeds; porcelain
clean; no network). The runner reads `SKEW_OPS_ROOT` for the repo path,
so each test sets that env var and runs the real runner script against
the fake tree.
"""
from __future__ import annotations

import importlib.util
import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLIST = ROOT / "ops" / "launchd" / "com.macro.skewaccrual.plist"
RUNNER = ROOT / "ops" / "launchd" / "run_skew_accrual.sh"
PUBLISH = ROOT / "scripts" / "publish_r2.py"


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Plist parses and pins the runner path / env keys / schedule.             #
# ─────────────────────────────────────────────────────────────────────────── #


def _load_plist() -> dict:
    with PLIST.open("rb") as f:
        return plistlib.load(f)


def test_plist_parses_with_python_plistlib():
    """XML well-formedness — expat is stricter than plutil's lenient mode.
    Earlier revisions contained `--` inside XML comments (illegal per the XML
    spec); pinning this test means future comment edits surface at PR time
    rather than as a launchd bootstrap failure on the seat's M1 host."""
    p = _load_plist()
    assert isinstance(p, dict)


def test_plist_pins_label_working_directory_and_program_arguments():
    p = _load_plist()
    assert p["Label"] == "com.macro.skewaccrual"
    assert p["WorkingDirectory"] == "/Users/chriswong/skew-ops-wt"
    assert p["ProgramArguments"] == [
        "/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh",
        "/Users/chriswong/skew-ops-wt/.env",
        "/Users/chriswong/skew-ops-wt/ops/launchd/run_skew_accrual.sh",
    ]


def test_plist_pins_schedule_weekdays_local_wall_clock():
    """BLOCKER-4: the schedule is the tightest safe local wall-clock that
    stays AFTER the 11:30Z ThetaData EOD refresh year-round.
        PST (UTC-8): 05:30 local = 13:30Z
        PDT (UTC-7): 05:30 local = 12:30Z
    The previous 04:30 value raced the 11:30Z refresh during PDT; the
    fix moves to 05:30. Pin both the weekday list AND that Hour is
    exclusively in {5} — any future edit that reverts to 04:30 (or
    picks another value < 5) fails this test rather than racing the
    refresh on the M1 ops host.
    """
    p = _load_plist()
    intervals = p["StartCalendarInterval"]
    assert [d["Weekday"] for d in intervals] == [1, 2, 3, 4, 5]
    for d in intervals:
        assert d["Hour"] == 5, (
            f"plist schedule is {d['Hour']:02d}:{d['Minute']:02d} local; "
            "the BLOCKER-4 fix pins 05:30 (>= 12:30Z year-round).")
        assert d["Minute"] == 30


def test_plist_pins_thetadata_store_env_var_without_secrets():
    """THETADATA_STORE is the only env var we set; the .env wrapper supplies
    the R2 / THETA creds. The plist itself never carries a secret — a test
    here means a future edit that accidentally adds one is caught at PR time."""
    p = _load_plist()
    env = p["EnvironmentVariables"]
    assert "THETADATA_STORE" in env
    assert env["THETADATA_STORE"].startswith("/Users/")
    for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"):
        for k, v in env.items():
            assert marker not in k.upper(), f"secret-shaped key: {k}"
            assert marker not in v.upper(), f"secret-shaped value: {k}={v}"


def test_plist_pins_keepalive_throttle_session_type():
    p = _load_plist()
    assert p["KeepAlive"] is False
    assert p["ThrottleInterval"] == 60
    assert p.get("LimitLoadToSessionType") == "Aqua"
    assert p["StandardOutPath"] == "/Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log"
    assert p["StandardErrorPath"] == "/Users/chriswong/skew-ops-state/logs/skewaccrual.stderr.log"


def test_plist_log_paths_live_outside_repo_in_sibling_state_dir():
    """MAJOR-1 (round-5 reviewer): all run-state files (.skew_pre_rows,
    receipts, locks, logs) live OUTSIDE the checkout under a sibling state
    directory. The launchd-managed stdout/stderr pair is part of that
    contract — the round-1 /tmp/skewaccrual.*.log pair sat in /tmp (still
    outside $REPO) but broke the spirit of the contract: every run-state
    file lives under ONE sibling state directory, the one the runner's
    $SKEW_STATE_DIR defaults to. Pin both destinations and prove neither
    one lives inside the dedicated lane checkout (/Users/chriswong/skew-ops-wt).
    """
    p = _load_plist()
    out_path = p["StandardOutPath"]
    err_path = p["StandardErrorPath"]
    # 1. The default state directory — the same /Users/chriswong/skew-ops-state
    #    the runner defaults to (STATE_DIR_DEFAULT in run_skew_accrual.sh).
    #    Hardcoded because launchd paths are literal (no env-var expansion);
    #    an operator override of SKEW_STATE_DIR must update these two keys.
    assert out_path == (
        "/Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log"
    ), (
        f"plist StandardOutPath is {out_path!r}; the round-5 contract pins it "
        "to /Users/chriswong/skew-ops-state/logs/skewaccrual.stdout.log (the "
        "same $SKEW_STATE_DIR default the runner uses). /tmp/skewaccrual.* "
        "is no longer compliant — every run-state file lives under ONE "
        "sibling state directory, never /tmp."
    )
    assert err_path == (
        "/Users/chriswong/skew-ops-state/logs/skewaccrual.stderr.log"
    ), (
        f"plist StandardErrorPath is {err_path!r}; the round-5 contract "
        "pins it to /Users/chriswong/skew-ops-state/logs/skewaccrual.stderr.log."
    )
    # 2. NOT inside the dedicated lane checkout — the install runbook creates
    #    /Users/chriswong/skew-ops-wt as a sparse clone of origin/main, so a
    #    log path that starts with that prefix would land inside the very
    #    checkout the runner's `git reset --hard && git clean -fd` wipes
    #    on every run.
    repo_prefix = "/Users/chriswong/skew-ops-wt"
    for label, path in (("StandardOutPath", out_path), ("StandardErrorPath", err_path)):
        assert not path.startswith(repo_prefix + "/") and path != repo_prefix, (
            f"{label}={path!r} lives INSIDE /Users/chriswong/skew-ops-wt; "
            "the round-5 contract requires it under the sibling state "
            "directory /Users/chriswong/skew-ops-state, never inside the "
            "lane checkout the runner wipes on every run."
        )


def test_run_with_env_wrapper_is_tracked_and_executable_at_head():
    """MINOR-1 (round-5 reviewer): the plist's ProgramArguments chain
    (/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh) references a
    wrapper that lives outside this PR's diff. A future revert on main that
    drops the wrapper would silently break the launchd bootstrap on the M1
    ops host — `launchctl bootstrap` would fail with a non-existent-program
    error and the lane would go dark without the operator seeing why. Pin
    the wrapper's existence on origin/main so that future edits surface at
    PR time.
    """
    out = subprocess.run(
        # HEAD, not origin/main: the ci-pack checkout is the PR merge ref at
        # depth 1 with NO remote-tracking branch, so `origin/main` is
        # "unknown revision" there (run 35790557450, exit 128). HEAD carries
        # main's files in CI (merge ref) and the branch in a lane worktree.
        ["git", "ls-tree", "HEAD", "ops/launchd/run_with_env.sh"],
        capture_output=True, text=True, check=True, cwd=str(ROOT),
    ).stdout.strip()
    assert out, (
        "ops/launchd/run_with_env.sh is referenced by the plist's "
        "ProgramArguments (line 113) but is NOT present on origin/main — "
        "the launchd bootstrap will fail with a non-existent-program error "
        "on the M1 ops host. The wrapper has been in the repo since 2026 "
        "(sha 02bd7387); a drop on main is a deployment-breaking event "
        "and must be a deliberate, separately-reviewed change."
    )
    # The wrapper is mode 100755 — a non-executable wrapper cannot be
    # exec'd by launchd. Pin the mode so a future chmod regression
    # surfaces at PR time too.
    assert "100755" in out, (
        f"ops/launchd/run_with_env.sh on origin/main is not mode 100755: "
        f"{out!r}. launchd requires the wrapper to be executable or the "
        "ProgramArguments exec call returns ENOEXEC."
    )


# ─────────────────────────────────────────────────────────────────────────── #
# 2. Runner script — `sh -n` clean and forbids git-push.                       #
# ─────────────────────────────────────────────────────────────────────────── #


def test_runner_script_passes_sh_n():
    """A single sh -n is enough to catch syntax errors; the launchd job
    runs this script daily, so a syntax drift would surface as a silent
    non-zero exit on every run."""
    rc = subprocess.run(["/bin/sh", "-n", str(RUNNER)],
                        capture_output=True, text=True, check=False)
    assert rc.returncode == 0, rc.stderr


def test_runner_does_not_push_to_git():
    """The lane NEVER pushes; the only outbound is publish_r2. A future
    edit that adds a `git push` (e.g. mirroring the dead
    `theta_surface_accrual.sh` precedent) is caught here at PR time."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "git push" not in src
    assert "git commit" not in src


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Behavioural: runner end-to-end against a fake checkout.                  #
# ─────────────────────────────────────────────────────────────────────────── #
#
# These tests are the BLOCKER-1/2/3 RED-first coverage: they actually run
# the runner script and assert exit codes / log shapes that the prior
# source-string tests could not pin. The fake checkout pattern:

# Helper: write a Python script that prints a status word and exits a code.
FAKE_PRECHECK_OK = '''"""Fake precheck — OK."""
import sys
print("OK")
sys.exit(0)
'''
FAKE_PRECHECK_MISSING = '''"""Fake precheck — FLAG_MISSING."""
import sys
print("FLAG_MISSING")
sys.exit(4)
'''
FAKE_VERIFY_OK = '''"""Fake verify — self-contained BLOCKER-2 check (no recursive import).

BLOCKER-2 fix: the runner now passes --pre-rows to verify_ledger so a
no-op accrue (chain=None, no rows, dedup-only, byte-equal rewrite) is
refused. The fake mirrors the real verify_ledger's contract: load the
ledger, read pre_rows from --pre-rows, refuse any post-state that has
not strictly grown.
"""
import os, sys
import pandas as pd

argv = sys.argv[1:]
ledger = None
pre_rows = None
i = 0
while i < len(argv):
    if argv[i] == "--ledger" and i + 1 < len(argv):
        ledger = argv[i + 1]
        i += 2
        continue
    if argv[i] == "--pre-rows" and i + 1 < len(argv):
        try:
            pre_rows = int(argv[i + 1])
        except ValueError:
            pre_rows = None
        i += 2
        continue
    i += 1

if not ledger or not os.path.isfile(ledger):
    print("NO_LEDGER")
    print(f"  reason=ledger file does not exist: {ledger}", file=sys.stderr)
    sys.exit(5)

df = pd.read_parquet(ledger)
n = int(len(df))
if n == 0:
    print("NO_LEDGER")
    print("  reason=ledger has 0 rows after accrue", file=sys.stderr)
    sys.exit(5)
if pre_rows is not None and n <= pre_rows:
    print("NO_LEDGER")
    print(f"  reason=ledger did not grow under accrue — pre_rows={pre_rows}, post_rows={n}",
          file=sys.stderr)
    sys.exit(5)

print("OK")
print(f"  rows={n}", file=sys.stderr)
if pre_rows is not None:
    print(f"  pre_rows={pre_rows}", file=sys.stderr)
sys.exit(0)
'''
FAKE_VERIFY_NO_LEDGER = '''"""Fake verify — NO_LEDGER."""
import sys
print("NO_LEDGER")
sys.exit(5)
'''
FAKE_PUBLISH_OK = '''"""Fake publish — exit 0."""
import sys
sys.exit(0)
'''
FAKE_PUBLISH_MARKER = '''"""Fake publish — exit 0 AND writes a marker file the test can read.

A-F03-W2-8 (2026-09-23) caught-up no-op test: the runner must SKIP
step_publish entirely on rc 3, so we cannot trust the absence of an
`SKEW_DRY_RUN` log line to prove the step was skipped (the dry-run
leg drops the R2 call but logs the skip — its absence under rc 3 IS
the proof, but only when dry-run=1). The marker file is the
ground-truth proof: a publish call writes it, the rc-3 path skips the
publish call, the marker is therefore absent.
"""
import os, sys
marker = os.path.join(os.environ["SKEW_STATE_DIR"], ".publish_called")
with open(marker, "w", encoding="utf-8") as f:
    f.write("called\\n")
sys.exit(0)
'''
FAKE_VERIFY_MARKER = '''"""Fake verify — exit 0 AND writes a marker file the test can read.

Same idea as FAKE_PUBLISH_MARKER: a verify call writes the marker,
the rc-3 path skips the verify call, the marker is therefore absent."""
import os, sys
marker = os.path.join(os.environ["SKEW_STATE_DIR"], ".verify_called")
with open(marker, "w", encoding="utf-8") as f:
    f.write("called\\n")
print("OK")
sys.exit(0)
'''
FAKE_FETCH_R2_OK = '''"""Fake fetch_r2 — exits 0 (no actual R2 I/O).

The runner's step_hydrate_ledger (B2 cure, 2026-09-22) calls
`python -m scripts.fetch_r2 --dirs options_skew` to restore the durable
options_skew bytes from R2 BEFORE the accrue. The fake MUST restore (or
in the test, simply succeed) so the runner can proceed to accrue + verify
+ publish. A no-op fake fetch is acceptable here because the test only
proves the step ordering — it does not exercise the live R2 plane.
"""
import sys
sys.exit(0)
'''
FAKE_PUBLISH_FAIL = '''"""Fake publish — exit 1."""
import sys
sys.exit(1)
'''
FAKE_ACCRUE_OK = '''"""Fake accrue — exit 0 AND appends one row to the ledger.

BLOCKER-2 fix: the runner now records pre-accrue rows and refuses a
no-op accrue. The fake must grow the ledger (write >= 1 new row) for
the verify step to pass.
"""
import os, sys
import pandas as pd

ledger = os.path.join(os.environ["SKEW_OPS_ROOT"], "data",
                      "options_skew", "snapshots.parquet")
if os.path.exists(ledger):
    df = pd.read_parquet(ledger)
else:
    df = pd.DataFrame(columns=["date", "underlying", "skew"])
new_row = pd.DataFrame([{"date": "2099-01-01", "underlying": "FAKE_NEW",
                          "skew": 0.99}])
df = pd.concat([df, new_row], ignore_index=True)
df.to_parquet(ledger, index=False)
sys.exit(0)
'''
FAKE_ACCRUE_NOOP = '''"""Fake accrue — A-F03-W2-8 caught-up no-op (rc 3).

The builder exits 3 when the store's complete session S is already on
the ledger byte-for-byte (the receipt reports
`dates_backfilled == len(dates)` AND `rows_added + rows_replaced == 0`;
the spec's "`catch_up_sessions` returns `[]`" line is misleading — the
helper always returns at least the target itself). The fake mirrors
that contract at the runner level: exit 3 AND append no row to the
ledger (a real caught-up accrue writes nothing). The runner is the
unit under test — it must treat rc 3 as a one-line receipt + skip
verify + skip publish + exit 0.
"""
import sys
sys.exit(3)
'''
FAKE_ACCRUE_NO_GROWTH = '''"""Fake accrue — exits 0 but writes zero rows (real no-op under a fresh session).

BLOCKER-2 stays intact: a zero-row accrue on a day with a NEW complete
session still aborts at step_verify_ledger. The fake mirrors that
contract: exit 0 AND append no row to the ledger, so the verify step's
post_rows <= pre_rows check refuses the publish.
"""
import sys
sys.exit(0)
'''
FAKE_GATE_FRESH = '''"""Fake gate — FRESH."""
import sys
print("FRESH")
sys.exit(0)
'''
FAKE_GATE_BYPASS_BYPASSED = '''"""Bypass: do not invoke the gate at all."""'''


def _build_fake_repo(tmp_path: Path, *,
                     precheck: str = FAKE_PRECHECK_OK,
                     verify: str = FAKE_VERIFY_OK,
                     publish: str = FAKE_PUBLISH_OK,
                     accrue: str = FAKE_ACCRUE_OK,
                     gate: str = FAKE_GATE_FRESH,
                     fetch_r2: str = FAKE_FETCH_R2_OK,
                     write_ledger: bool = True) -> tuple[Path, Path]:
    """Construct a fake checkout the runner can drive end-to-end.

    Returns (repo_path, stub_bin_path). Sets up:
      - `.git/` (so the runner sees a worktree)
      - `scripts/` carrying fake `skew_accrual_gate`,
        `skew_accrual_precheck`, `skew_accrual_verify_ledger`,
        `build_options_skew`, `publish_r2`
      - `data/options_skew/snapshots.parquet` (so verify-ledger has a path)
      - `ops/launchd/run_skew_accrual.sh` (a copy of the real runner, since
        the test runs it from the fake tree's perspective)
      - `stub_bin/git` (everything succeeds; porcelain clean)
      - `stub_bin/python` (a shim that translates `-m scripts.foo` into a
        runpy call on `$SKEW_OPS_ROOT/scripts/foo.py` so the fake modules
        are exercised end-to-end)
    """
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    ops_dir = repo / "ops" / "launchd"
    data_dir = repo / "data" / "options_skew"
    repo.mkdir()
    (repo / ".git").mkdir()
    scripts_dir.mkdir(parents=True)
    ops_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (scripts_dir / "skew_accrual_gate.py").write_text(gate, encoding="utf-8")
    (scripts_dir / "skew_accrual_precheck.py").write_text(precheck, encoding="utf-8")
    (scripts_dir / "skew_accrual_verify_ledger.py").write_text(verify, encoding="utf-8")
    (scripts_dir / "build_options_skew.py").write_text(accrue, encoding="utf-8")
    (scripts_dir / "publish_r2.py").write_text(publish, encoding="utf-8")
    # B2 cure (2026-09-22): the new step_hydrate_ledger calls
    # `scripts.fetch_r2 --dirs options_skew`. A fetch_r2 stub is always
    # written now — defaults to a no-op OK so the existing tests keep
    # passing; an individual test can override the kwarg to drive the
    # R2-failure branch.
    (scripts_dir / "fetch_r2.py").write_text(fetch_r2, encoding="utf-8")
    # A copy of the real runner — keeps the test hermetic: edits to the
    # real runner flow through immediately.
    shutil.copyfile(RUNNER, ops_dir / "run_skew_accrual.sh")
    (ops_dir / "run_skew_accrual.sh").chmod(0o755)
    if write_ledger:
        # Even with verify=OK we need a file so `wc -c` and the parquet
        # read don't blow up. The runner now records pre-accrue rows and
        # the BLOCKER-2 fix expects a grow under the accrue; seed the
        # file with one row so the fake accrue's new FAKE_NEW row is
        # detected as growth (pre=1, post=2). Tests that exercise the
        # no-op path inject a different verify that returns NO_LEDGER.
        try:
            import pandas as pd
            pd.DataFrame([
                {"date": "2026-09-15", "underlying": "BOOTSTRAP",
                 "skew": 0.05},
            ]).to_parquet(data_dir / "snapshots.parquet")
        except Exception:
            # pandas unavailable in the test env — leave the path empty;
            # tests that need a ledger pass write_ledger=True with verify=OK.
            pass
    # Stub bin: every common git subcommand the runner invokes exits 0
    # and reports a clean status (porcelain empty).
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    (stub_bin / "git").write_text(
        "#!/bin/sh\n"
        "# Stub — fake 'git' for the skew-accrual runner's hermetic test.\n"
        "case \"$1\" in\n"
        "  status) exit 0 ;;\n"
        "  fetch) exit 0 ;;\n"
        "  checkout) exit 0 ;;\n"
        # rev-parse must NOT call `git` again: stub_bin is first on PATH, so the
        # original `$(git rev-parse --short HEAD ...)` recursed into this very
        # stub until the process table filled — 60s TimeoutExpired on every
        # test that reached the refresh receipt (measured 2026-09-22 on the M2;
        # on hosts where fork fails fast the `|| echo` branch hid it).
        "  rev-parse) echo 0000000 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (stub_bin / "git").chmod(0o755)
    # Python shim: translate `python -m scripts.<name> <args>` into
    # `runpy.run_path("$SKEW_OPS_ROOT/scripts/<name>.py")` with the same
    # args. This is what the runner actually executes when it calls
    # `$PYTHON -m scripts.<name>` — without this shim the fake modules
    # would never run and every assertion would fail with empty status.
    #
    # A-F03-W2-8 (2026-09-23): the shim also executes `python -c "<code>"`
    # inline (NOT by re-spawning `sys.executable`, which would loop back
    # into this very shim) so the runner's pre-accrue row-count read
    # actually sees the ledger's real row count. Without this, `pre_rows`
    # is always 0 in tests because the shim only handles `-m`, and
    # BLOCKER-2 (`post_rows <= pre_rows`) never fires — every
    # FAKE_ACCRUE that appends 1 row sees `1 > 0` and passes. The
    # caught-up / zero-growth tests therefore had to use the `n == 0`
    # rule (a different failure mode) to drive the abort. With `-c`
    # executing inline here, BLOCKER-2 itself is reachable.
    py_shim = '''#!/usr/bin/env python3
"""Hermetic test shim: dispatches `python -m scripts.<name>` to the
fake module under $SKEW_OPS_ROOT/scripts/<name>.py`. `python -c "…"`
executes inline in this process (NOT via sys.executable — that would
recurse into this shim) so inline ledger-row reads see real counts."""
import os, runpy, sys

args = sys.argv[1:]
# `python -c "<code>"` → execute inline. The runner's pre_rows read
# needs the real ledger row count; BLOCKER-2 is only exercisable when
# pre_rows is accurate. Recursing via sys.executable would loop, since
# the shim IS the executable the runner resolved `$PYTHON` to.
if args and args[0] == "-c":
    code = args[1]
    sys.argv = ["-c"] + args[2:]
    exec(compile(code, "<shim -c>", "exec"), {"__name__": "__main__"})
    sys.exit(0)

mod = None
i = 0
while i < len(args):
    if args[i] == "-m" and i + 1 < len(args):
        mod = args[i + 1]
        del args[i:i + 2]
        break
    i += 1

if mod is None:
    sys.stderr.write("fake-python: -m <module> required\\n")
    sys.exit(2)

short = mod.rsplit(".", 1)[-1]
fake_repo = os.environ.get("SKEW_OPS_ROOT")
if fake_repo is None:
    sys.stderr.write("fake-python: SKEW_OPS_ROOT not set\\n")
    sys.exit(2)
path = os.path.join(fake_repo, "scripts", short + ".py")
if not os.path.isfile(path):
    sys.stderr.write(f"fake-python: {path} not found\\n")
    sys.exit(2)
sys.argv = [path] + args
runpy.run_path(path, run_name="__main__")
'''
    (stub_bin / "python").write_text(py_shim, encoding="utf-8")
    (stub_bin / "python").chmod(0o755)
    return repo, stub_bin


def _run_runner(tmp_path: Path, repo: Path, stub_bin: Path,
                *, freshness_bypass: bool = True,
                dry_run: bool = False,
                env_extra: dict | None = None,
                timeout: int = 60) -> subprocess.CompletedProcess:
    """Run the runner end-to-end against the fake checkout."""
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    env["SKEW_OPS_ROOT"] = str(repo)
    # Never let a test fall through to the runner's production default
    # (/Users/chriswong/skew-ops-state): on ubuntu-latest `mkdir -p /Users/...`
    # is "Permission denied" (measured ci-pack-6 run 35782263306, 6 runner
    # tests red) and on a sandboxed Mac session it is refused too. The
    # sibling-state contract itself is proven by _run_runner_with_state_dir.
    env["SKEW_STATE_DIR"] = str(tmp_path / "skew-state")
    env["PYTHON"] = str(stub_bin / "python")
    env["SKEW_PYTHON"] = str(stub_bin / "python")
    if freshness_bypass:
        env["SKEW_FRESHNESS_BYPASS"] = "1"
    if dry_run:
        env["SKEW_DRY_RUN"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["/bin/sh", str(repo / "ops" / "launchd" / "run_skew_accrual.sh")],
        capture_output=True, text=True, env=env, check=False, timeout=timeout,
    )


def test_runner_fails_loud_when_w21b_precheck_reports_flag_missing(tmp_path):
    """BLOCKER-1 RED-first regression: a pre-W2-1b tree (--accrue flag
    missing) MUST cause the runner to abort with exit 4 (FLAG_MISSING)
    and a named reason — NEVER silently run main() and race the
    render-host side W2-1b pinned to legacy."""
    repo, stub_bin = _build_fake_repo(tmp_path, precheck=FAKE_PRECHECK_MISSING)
    rc = _run_runner(tmp_path, repo, stub_bin)
    assert rc.returncode == 4, (rc.stdout, rc.stderr)
    assert "precheck" in rc.stdout.lower()
    assert "--accrue" in (rc.stdout + rc.stderr)


def test_runner_fails_loud_when_accrue_step_returns_nonzero(tmp_path):
    """BLOCKER-2 RED-first regression: the runner's step_accrue MUST
    propagate the accrue-step's failure, not silently return 0. The
    prior shell pattern `if ! cmd; then rc=$?` always reported rc=0
    (POSIX resets $? inside the then-block of `if !`). The new pattern
    captures rc BEFORE the if and exits 1 on any non-zero — and the
    log line carries the underlying rc so the operator can see it.

    The runner collapses step failures to a small set of exit codes
    (1 = generic step failure, 4 = precheck, 5 = verify). For accrue
    and publish the runner exits 1; the underlying rc is in the log.
    The RED-first assertion here is rc.returncode != 0 AND the log
    carries the underlying rc — together these prove the failure was
    propagated (not silently swallowed)."""
    repo, stub_bin = _build_fake_repo(tmp_path, accrue="""import sys
sys.exit(7)
""")
    rc = _run_runner(tmp_path, repo, stub_bin)
    assert rc.returncode == 1, (rc.stdout, rc.stderr)
    assert "accrue" in rc.stdout.lower()
    assert "exit 7" in rc.stdout  # underlying rc IS reported in the log
    assert "ABORT at step_accrue" in rc.stdout


def test_runner_fails_loud_when_verify_ledger_reports_no_ledger(tmp_path):
    """BLOCKER-3 RED-first regression: W2-1b's snapshot() can return 0
    without writing rows. A zero-row accrue must NOT publish. The runner
    must abort with exit 5 (NO_LEDGER) when the verify helper reports
    that, rather than publishing an unchanged ledger to R2."""
    repo, stub_bin = _build_fake_repo(tmp_path, verify=FAKE_VERIFY_NO_LEDGER)
    rc = _run_runner(tmp_path, repo, stub_bin)
    assert rc.returncode == 5, (rc.stdout, rc.stderr)
    assert "verify" in rc.stdout.lower() or "ledger" in rc.stdout.lower()


def test_runner_fails_loud_when_publish_returns_nonzero(tmp_path):
    """BLOCKER-2 RED-first regression for the publish step: a non-zero
    publish rc must reach the runner's exit, not be silently swallowed
    by the prior `if ! cmd; then rc=$?` capture bug. The publish-step
    exit code is whatever the failing publish returns."""
    repo, stub_bin = _build_fake_repo(tmp_path, publish=FAKE_PUBLISH_FAIL)
    # With SKEW_DRY_RUN=1 we skip publish; force it OFF and watch the rc.
    rc = _run_runner(tmp_path, repo, stub_bin, dry_run=False)
    assert rc.returncode == 1, (rc.stdout, rc.stderr)
    assert "publish" in rc.stdout.lower()


def test_runner_full_happy_path_exits_zero(tmp_path):
    """When every step succeeds, the runner exits 0 and emits the
    line-start receipts the runbook documents."""
    repo, stub_bin = _build_fake_repo(tmp_path)
    rc = _run_runner(tmp_path, repo, stub_bin, dry_run=True)
    assert rc.returncode == 0, (rc.stdout, rc.stderr)
    # Line-start receipts the runbook pins
    for marker in ("skew_accrual: starting skew_accrual",
                   "skew_accrual: checkout refreshed",
                   "skew_accrual: W2-1b precheck passed",
                   "skew_accrual: accrue completed",
                   "skew_accrual: ledger verified",
                   "skew_accrual: SKEW_DRY_RUN=1",
                   "skew_accrual: done"):
        assert marker in rc.stdout, f"missing line-start receipt: {marker}"


def test_runner_aborts_loud_when_checkout_is_dirty(tmp_path):
    """Stub `git status` reports a dirty tree; runner must abort before
    any downstream step runs."""
    repo, stub_bin = _build_fake_repo(tmp_path)
    # Override the stub git: `status` exits 0 but emits porcelain lines.
    (stub_bin / "git").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  status) printf ' M scripts/x\\n' ; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (stub_bin / "git").chmod(0o755)
    rc = _run_runner(tmp_path, repo, stub_bin)
    assert rc.returncode == 1, (rc.stdout, rc.stderr)
    assert "dirty" in rc.stdout.lower()


# ────────────────────────────────────────────────────────────────────────────── #
# 3b. B2 cure (2026-09-22): producer repeatability through step ordering.        #
# ────────────────────────────────────────────────────────────────────────────── #
# The round-1 review flagged that the runner wrote an untracked .skew_pre_rows
# file inside $REPO and immediately refused the NEXT run as dirty. The B2 cure
# moves every run-state artifact to a sibling state directory OUTSIDE $REPO
# (default /Users/chriswong/skew-ops-state, override SKEW_STATE_DIR) AND splits
# the previously-bundled `step_refresh_checkout` into separate `step_refresh`
# and `step_assert_clean_tree` functions so the destructive refresh
# (`git reset --hard && git clean -fd`) runs BEFORE the clean-tree assertion.
# These two tests prove the cycle:
#   - two_run_cycle_is_admitted_via_real_git: real `git init` repo, two
#     back-to-back dry-runs both exit 0 (B2 cure works);
#   - runstate_files_live_outside_repo: state files appear in $SKEW_STATE_DIR,
#     never in $REPO, between step_accrue and step_verify_ledger.


def _build_real_git_repo(tmp_path: Path,
                         *,
                         precheck: str = FAKE_PRECHECK_OK,
                         verify: str = FAKE_VERIFY_OK,
                         publish: str = FAKE_PUBLISH_OK,
                         accrue: str = FAKE_ACCRUE_OK,
                         gate: str = FAKE_GATE_FRESH,
                         fetch_r2: str = FAKE_FETCH_R2_OK,
                         write_ledger: bool = True) -> tuple[Path, Path]:
    """Like _build_fake_repo, but `.git/` is a REAL git repo with a
    LOCAL bare 'origin' remote so `git fetch origin` succeeds offline.

    The runner's `step_refresh` (B2 cure, 2026-09-22) calls `git fetch`,
    `git checkout --detach origin/main`, `git reset --hard`, `git clean -fd`
    in the wild, all of which require a real git binary the existing stubs
    cannot satisfy (a stub `git checkout --detach origin/main` would not
    create a real detached HEAD, and origin is required to exist for `git
    fetch origin` to return 0). This helper builds a bare repo as origin,
    clones it into the working tree, and sets origin's URL to the bare path
    so network is never touched."""
    repo = tmp_path / "real_repo"
    scripts_dir = repo / "scripts"
    ops_dir = repo / "ops" / "launchd"
    data_dir = repo / "data" / "options_skew"
    repo.mkdir()
    scripts_dir.mkdir(parents=True)
    ops_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    # Seed the bootstrap ledger the W2-1b sibling would commit in production.
    if write_ledger:
        try:
            import pandas as pd
            pd.DataFrame([
                {"date": "2026-09-15", "underlying": "BOOTSTRAP",
                 "skew": 0.05},
            ]).to_parquet(data_dir / "snapshots.parquet")
        except Exception:
            pass
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "T"
    env["GIT_AUTHOR_EMAIL"] = "t@example.com"
    env["GIT_COMMITTER_NAME"] = "T"
    env["GIT_COMMITTER_EMAIL"] = "t@example.com"
    # 1. Stub python modules FIRST (tracked into the bootstrap commit so
    #    `git reset --hard` later does NOT wipe them — that is the very
    #    point of the B2 cure: destructive refresh must leave the
    #    production helpers in place while still wiping any new state).
    (scripts_dir / "skew_accrual_gate.py").write_text(gate, encoding="utf-8")
    (scripts_dir / "skew_accrual_precheck.py").write_text(precheck, encoding="utf-8")
    (scripts_dir / "skew_accrual_verify_ledger.py").write_text(verify, encoding="utf-8")
    (scripts_dir / "build_options_skew.py").write_text(accrue, encoding="utf-8")
    (scripts_dir / "publish_r2.py").write_text(publish, encoding="utf-8")
    (scripts_dir / "fetch_r2.py").write_text(fetch_r2, encoding="utf-8")
    shutil.copyfile(RUNNER, ops_dir / "run_skew_accrual.sh")
    (ops_dir / "run_skew_accrual.sh").chmod(0o755)
    # 2. Bare origin
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)],
                   check=True, env=env)
    # 3. Seed repo on main, commit (carrying the fake scripts), push.
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo,
                   check=True, env=env)
    subprocess.run(["git", "config", "user.email", "t@example.com"],
                   cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo,
                   check=True, env=env)
    subprocess.run(["git", "remote", "add", "origin", str(bare)],
                   cwd=repo, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "W2-2 fake bootstrap"],
                   cwd=repo, check=True, env=env)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=repo,
                   check=True, env=env)
    # python shim only — system git is unmolested.
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    # Use a separate file so the Python-source escapes are unambiguous.
    # Writing the shim through Python's write_text breaks \\\\n in heredocs
    # (the outer file_write decodes one level: a literal "\\n" becomes
    # the two chars `\n` then a `\n` is interpreted at runpy time as
    # newline + n + ...; the right escape is to write the shim from a
    # raw bytes blob).
    py_shim_text = (
        "#!/usr/bin/env python3\n"
        "import os, runpy, sys\n"
        "args = sys.argv[1:]\n"
        "if args and args[0] == '-c':\n"
        "    code = args[1]\n"
        "    sys.argv = ['-c'] + args[2:]\n"
        "    exec(compile(code, '<shim -c>', 'exec'), {'__name__': '__main__'})\n"
        "    sys.exit(0)\n"
        "mod = None; i = 0\n"
        "while i < len(args):\n"
        "    if args[i] == '-m' and i + 1 < len(args):\n"
        "        mod = args[i + 1]; del args[i:i + 2]; break\n"
        "    i += 1\n"
        "if mod is None:\n"
        "    sys.stderr.write('fake-python: -m <module> required\\n'); sys.exit(2)\n"
        "short = mod.rsplit('.', 1)[-1]\n"
        "fake_repo = os.environ.get('SKEW_OPS_ROOT')\n"
        "if fake_repo is None:\n"
        "    sys.stderr.write('fake-python: SKEW_OPS_ROOT not set\\n'); sys.exit(2)\n"
        "path = os.path.join(fake_repo, 'scripts', short + '.py')\n"
        "if not os.path.isfile(path):\n"
        "    sys.stderr.write('fake-python: ' + path + ' not found\\n'); sys.exit(2)\n"
        "sys.argv = [path] + args\n"
        "runpy.run_path(path, run_name='__main__')\n"
    )
    (stub_bin / "python").write_text(py_shim_text, encoding="utf-8")
    (stub_bin / "python").chmod(0o755)
    return repo, stub_bin


def _run_runner_with_state(tmp_path: Path, repo: Path, stub_bin: Path,
                           *, state_dir: Path,
                           freshness_bypass: bool = True,
                           dry_run: bool = True,
                           env_extra: dict | None = None,
                           timeout: int = 60
                           ) -> subprocess.CompletedProcess:
    """Same as _run_runner, but also sets SKEW_STATE_DIR explicitly.

    The B2 cure is the default run-state home; the test sets it explicitly
    so the assertion can prove post-run files landed in the right dir."""
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    env["SKEW_OPS_ROOT"] = str(repo)
    env["SKEW_STATE_DIR"] = str(state_dir)
    env["PYTHON"] = str(stub_bin / "python")
    env["SKEW_PYTHON"] = str(stub_bin / "python")
    if freshness_bypass:
        env["SKEW_FRESHNESS_BYPASS"] = "1"
    if dry_run:
        env["SKEW_DRY_RUN"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["/bin/sh", str(repo / "ops" / "launchd" / "run_skew_accrual.sh")],
        capture_output=True, text=True, env=env, check=False, timeout=timeout,
    )


def test_two_run_cycle_is_admitted_via_real_git(tmp_path):
    """B2 RED-first regression: a runner that wrote an untracked
    .skew_pre_rows file inside $REPO and refused the NEXT run as dirty
    is un-repeatable. The B2 cure (state dir + step_split) must let two
    back-to-back runs against a real `git init`'d repo BOTH succeed.

    The test:
      1. Builds a real `git init`'d repo under tmp_path with a single
         bootstrap commit (snapshots.parquet seeded with 1 row).
      2. Sets SKEW_STATE_DIR to a sibling state directory.
      3. Runs the runner end-to-end (SKEW_DRY_RUN=1, SKEW_FRESHNESS_BYPASS=1).
      4. Confirms first run exits 0.
      5. Runs the runner again with the SAME state directory.
      6. Confirms the second run ALSO exits 0 — the prior run's pre_rows
         file is in $SKEW_STATE_DIR (not $REPO) so the prior ledger state
         is wiped by `git reset --hard && git clean -fd` on the next
         step_refresh, and step_assert_clean_tree passes."""
    repo, stub_bin = _build_real_git_repo(tmp_path)
    state_dir = tmp_path / "skew_state"
    state_dir.mkdir()
    first = _run_runner_with_state(
        tmp_path, repo, stub_bin, state_dir=state_dir,
    )
    assert first.returncode == 0, (first.stdout, first.stderr)
    # Receipt that every B2 step ran in order: refresh → assert clean →
    # hydrate (fetch_r2) → freshness (bypassed) → precheck → accrue →
    # verify → publish (skipped, dry-run).
    for marker in (
        "checkout refreshed",
        "checkout clean — proceeding to hydrate",
        "options_skew hydrated from R2",
        "W2-1b precheck passed",
        "accrue completed",
        "ledger verified",
        "SKEW_DRY_RUN=1 — skipping publish_r2",
        "done",
    ):
        assert marker in first.stdout, f"first run missing: {marker}\n{first.stdout}"
    # Second run — the B2 cure's whole point is that this exits 0 too.
    second = _run_runner_with_state(
        tmp_path, repo, stub_bin, state_dir=state_dir,
    )
    assert second.returncode == 0, (second.stdout, second.stderr)
    assert "checkout refreshed" in second.stdout
    assert "checkout clean" in second.stdout
    assert "done" in second.stdout


def test_runstate_files_live_outside_repo(tmp_path):
    """B2 cure: every run-state artifact — gate status, precheck status,
    verify status, pre_rows snapshot — lives in $SKEW_STATE_DIR, never
    inside $REPO. Pins the design boundary that the next refresh+assert
    tick relies on: if any of these files drifted into $REPO they would
    dirty the post-refresh checkout and fail step_assert_clean_tree."""
    repo, stub_bin = _build_real_git_repo(tmp_path)
    state_dir = tmp_path / "skew_state"
    state_dir.mkdir()
    rc = _run_runner_with_state(
        tmp_path, repo, stub_bin, state_dir=state_dir,
    )
    assert rc.returncode == 0, (rc.stdout, rc.stderr)
    # After run: NO .skew_* artifacts remain in $REPO at all. (The runner
    # deletes the pre_rows file in step_verify_ledger on success; the
    # status files are intentionally left around for the operator log but
    # sit OUTSIDE the checkout.)
    repo_run_state = list(repo.glob("**/.skew_*"))
    assert repo_run_state == [], (
        f"runner leaked run-state files into $REPO: {repo_run_state}"
    )
    # The state dir has at least the pre_rows file written and then
    # removed; we sample what survives, which is the per-pid gate /
    # precheck / verify status files. The point is: they are in the
    # state dir, not the repo.
    state_files = list(state_dir.glob("*"))
    assert state_files, "state dir is empty — run-state files missing entirely"


# ─────────────────────────────────────────────────────────────────────────── #
# 4. scripts/publish_r2._DATA_DIRS registers `options_skew` correctly.        #
# ─────────────────────────────────────────────────────────────────────────── #


def _load_publish():
    spec = importlib.util.spec_from_file_location("publish_r2_under_test", PUBLISH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_publish_r2_registers_options_skew_in_data_dirs():
    """The audit / restore legs both branch on `_DATA_DIRS` membership —
    an entry missing here would mean fetch_r2 routed the dir to site/
    instead of data/, and the W2-3 cutover's restore step would write
    into the wrong tree."""
    mod = _load_publish()
    assert "options_skew" in mod._DATA_DIRS


def test_publish_r2_options_skew_bytes_floor_is_sane():
    """A floor too low admits a sparse-CI sidecars-only tree (would publish
    700B over the deep store); a floor too high blocks the first legitimate
    nightly run. 10 KB sits safely above the bare sidecars size and below
    one session of real accruals across ~380 roots."""
    mod = _load_publish()
    floor = mod._DATA_DIR_MIN_BYTES["options_skew"]
    assert 1_000 <= floor <= 1_000_000


def test_publish_r2_options_skew_floor_clears_actual_bootstrap():
    """MAJOR-3 measurement regression: the floor must clear the actual
    bootstrap ledger committed on origin/main (not a hypothetical
    'one session of ~380 roots' guess). Read the tracked blob via git,
    confirm the floor admits it with a sane margin, AND that the bare
    tracked sidecars (validation_gate.json only) are still refused."""
    import subprocess
    mod = _load_publish()
    floor = mod._DATA_DIR_MIN_BYTES["options_skew"]
    # Pull the tracked bootstrap parquet bytes via git.
    blob = subprocess.run(
        # HEAD, not origin/main — see test_run_with_env_wrapper_is_tracked_and_executable_at_head.
        ["git", "cat-file", "-s", "HEAD:data/options_skew/snapshots.parquet"],
        capture_output=True, text=True, check=True, cwd=ROOT,
    ).stdout.strip()
    bootstrap_bytes = int(blob)
    # Floor admits the bootstrap with a sane margin (>= 4x margin means
    # any first-run store trivially clears).
    assert bootstrap_bytes > floor, (
        f"floor={floor} but bootstrap parquet is {bootstrap_bytes}B — "
        "first legitimate run would be refused.")
    margin = bootstrap_bytes // floor
    assert margin >= 4, (
        f"margin {margin}x between floor and bootstrap is too thin — "
        "any first-run store smaller than the bootstrap would fail.")


def test_publish_r2_options_skew_floor_refuses_sidecars_only():
    """MAJOR-3 measurement regression: the floor must still refuse a
    sparse-CI sidecars-only tree (just the tracked
    validation_gate.json sidecar, ~700 bytes)."""
    mod = _load_publish()
    floor = mod._DATA_DIR_MIN_BYTES["options_skew"]
    sidecar_bytes = 700  # measured against the tracked validation_gate.json
    assert sidecar_bytes < floor, (
        f"floor={floor} admits a {sidecar_bytes}B sidecars-only tree — "
        "a sparse-CI checkout would publish 700B over the deep store.")


def test_publish_r2_options_skew_min_files_override_is_set():
    mod = _load_publish()
    override = mod._DATA_DIR_MIN_FILES_OVERRIDE.get("options_skew")
    assert override is not None
    # snapshots.parquet + the tracked validation_gate.json sidecar = 2
    assert override == 2


def test_publish_r2_options_skew_is_not_append_only():
    """snapshots.parquet is rewritten whole on every accrue (dedup + concat);
    a per-file shrink refusal would block honest nights, so the
    directory must NOT be in _APPEND_ONLY_DIRS. The append-only contract
    lives in snapshot()'s idempotent (date, underlying) key-set instead."""
    mod = _load_publish()
    assert "options_skew" not in mod._APPEND_ONLY_DIRS


def test_fetch_r2_docstring_routes_data_dir_to_data_subtree():
    """fetch_r2's docstring (per scripts/fetch_r2.py:12) states: 'R2 key
    `attention/AAPL.parquet` maps to data/<dir>/ for data-dir stores
    (publish_r2._DATA_DIRS) and site/<dir>/ otherwise.' Pin the routing
    rule so the W2-3 cutover knows exactly where the restored ledger
    lands: data/options_skew/ (NOT site/options_skew/)."""
    fetch_r2 = ROOT / "scripts" / "fetch_r2.py"
    docstring = fetch_r2.read_text(encoding="utf-8").split('"""', 2)[1]
    assert "data/<dir>" in docstring or "data/" in docstring
    assert "publish_r2._DATA_DIRS" in docstring


# ─────────────────────────────────────────────────────────────────────────── #
# 5. A-F03-W2-8 (2026-09-23): caught-up no-op exits clean (no verify, no publish). #
# ─────────────────────────────────────────────────────────────────────────── #
# The skew-accrual lane resolves the COMPLETE store session S via
# engine.options_skew.complete_store_session (W2-6, PR #7832) and backfills
# every missed session on the path from the ledger's newest complete
# thetadata row. When S is already on the ledger byte-for-byte, the
# backfill receipt reports `dates_backfilled == len(dates)` AND
# `rows_added + rows_replaced == 0` (the spec's "`catch_up_sessions`
# returns `[]`" line is misleading — the helper always returns at least
# the target itself; the discriminator lives in the receipt), and the
# builder exits 3. The launchd runner treats that rc as a one-line
# receipt + SKIP verify AND publish + exit 0 — a caught-up ledger is
# exactly what the verify step's BLOCKER-2 rule was written to refuse
# (post_rows <= pre_rows), but refusing the publish under "nothing to
# accrue" is the wrong outcome: the daily maintainer's session has already
# landed, the lane did its job, and the operator wants a clean rc-0 exit,
# not a launchd failure for every weekday-after-holiday tick.
#
# These two tests pin the two-case contract:
#   - rc 3 → receipt + skip verify + skip publish + exit 0 (caught-up no-op)
#   - rc 0 with zero growth → BLOCKER-2 still aborts loud at verify (the
#     real failure path stays intact).


def test_runner_caught_up_noop_exits_zero_and_skips_verify_and_publish(tmp_path):
    """A-F03-W2-8 (2026-09-23): caught-up no-op must exit 0, log the
    one-line receipt, AND skip verify AND publish.

    The fake accrue exits 3 (FAKE_ACCRUE_NOOP) and appends no row. The
    fake verify and fake publish are the *-MARKER variants — both write
    a marker file in $SKEW_STATE_DIR when invoked. The runner must NOT
    call the fake verify (marker absent), must NOT call the fake
    publish (marker absent), must remove the `.skew_pre_rows.<run_tag>`
    sidecar so it does not contaminate the next tick, and must exit 0.

    The receipt `NOOP_CAUGHT_UP run_tag=… ledger=…` is the line-start
    line the runbook points operators at; its absence is a regression
    on the seat ruling."""
    repo, stub_bin = _build_fake_repo(tmp_path, accrue=FAKE_ACCRUE_NOOP,
                                       verify=FAKE_VERIFY_MARKER,
                                       publish=FAKE_PUBLISH_MARKER)
    state_dir = tmp_path / "skew_state"
    # MINOR-10 (round-3 reviewer): the default `dry_run=True` short-circuits
    # step_publish inside the runner (`ops/launchd/run_skew_accrual.sh:498`)
    # before it ever invokes `python -m scripts.publish_r2`, so the publish-
    # marker absence under rc 3 only proves the dry-run skip — not the
    # rc-3 branch. Force `dry_run=False` so the live launchd path is the
    # one the marker file proves against. Re-proven by the reviewer with
    # `dry_run=False` on the mutant runner (`accrue_rc=0`): the marker files
    # ARE written when rc 3 is bypassed, so the assertion is falsifiable.
    rc = _run_runner_with_state(
        tmp_path, repo, stub_bin, state_dir=state_dir, dry_run=False,
    )
    assert rc.returncode == 0, (rc.stdout, rc.stderr)
    # The seat-ruled one-line receipt is at line start.
    assert "NOOP_CAUGHT_UP" in rc.stdout, rc.stdout
    # The step_accrue NOOP log line — the runner's own evidence the
    # rc-3 was a caught-up no-op, distinct from a generic accrual pass.
    assert "caught-up no-op" in rc.stdout or "nothing to accrue" in rc.stdout
    # The runner did NOT reach step_verify_ledger — marker file absent.
    verify_marker = state_dir / ".verify_called"
    assert not verify_marker.exists(), (
        f"runner called step_verify_ledger on rc 3: {verify_marker}"
    )
    # The runner did NOT reach step_publish — marker file absent.
    publish_marker = state_dir / ".publish_called"
    assert not publish_marker.exists(), (
        f"runner called step_publish on rc 3: {publish_marker}"
    )
    # Pre_rows sidecar gone (step_accrue removes it on rc 3 — the rc-3
    # receipt is the durable evidence; the sidecar would only leak into
    # the next tick if it survived).
    pre_rows_markers = list(state_dir.glob(".skew_pre_rows.*"))
    assert pre_rows_markers == [], (
        f"runner left .skew_pre_rows.* sidecar on rc 3: {pre_rows_markers}"
    )
    # Final-state log line: the runner closes with the "done" receipt
    # the runbook points operators at.
    assert "done" in rc.stdout


def test_runner_zero_growth_under_a_real_accrue_still_aborts_at_verify(tmp_path):
    """A-F03-W2-8 (2026-09-23): a zero-row accrue on a day with a NEW
    complete session MUST still abort at step_verify_ledger (BLOCKER-2).

    This pins the BLOCKER-2 rule survives the W2-8 change — the runner
    treats rc 0 + zero growth as a real no-op, NOT as a caught-up no-op.
    The fake accrue exits 0 AND writes no row; the fake verify would
    pass on OK rows but the real verify (FAKE_VERIFY_OK mirrors the real
    BLOCKER-2 contract) refuses post_rows <= pre_rows → runner logs
    `ABORT at step_verify_ledger` and exits 5.

    Without this pin, a future refactor that drops BLOCKER-2 in favour
    of "every zero-row accrue is a no-op" would publish a no-op ledger
    to R2 and pollute audit_r2's freshness anchor (the measured fallout
    that BLOCKER-2 was written to prevent)."""
    repo, stub_bin = _build_fake_repo(tmp_path, accrue=FAKE_ACCRUE_NO_GROWTH,
                                       verify=FAKE_VERIFY_OK,
                                       publish=FAKE_PUBLISH_OK)
    rc = _run_runner(tmp_path, repo, stub_bin, dry_run=True)
    # FAKE_VERIFY_OK is the BLOCKER-2-mirror fake: post_rows <= pre_rows
    # → NO_LEDGER → rc 5. The runner collapses that to exit 5.
    assert rc.returncode == 5, (rc.stdout, rc.stderr)
    assert "ABORT at step_verify_ledger" in rc.stdout, rc.stdout
    # The receipt log explicitly names the failure surface.
    assert "ledger" in rc.stdout.lower()
    # The rc-3 receipt from the caught-up branch MUST NOT appear here —
    # a real no-op is not a caught-up no-op.
    assert "NOOP_CAUGHT_UP" not in rc.stdout, (
        f"zero-growth under a real accrue was mis-classified as caught-up: "
        f"{rc.stdout}"
    )
