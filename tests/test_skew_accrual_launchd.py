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
    assert p["StandardOutPath"] == "/tmp/skewaccrual.stdout.log"
    assert p["StandardErrorPath"] == "/tmp/skewaccrual.stderr.log"


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
FAKE_VERIFY_OK = '''"""Fake verify — OK."""
import sys
print("OK")
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
FAKE_PUBLISH_FAIL = '''"""Fake publish — exit 1."""
import sys
sys.exit(1)
'''
FAKE_ACCRUE_OK = '''"""Fake accrue — exit 0 (writes no parquet)."""
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
    # A copy of the real runner — keeps the test hermetic: edits to the
    # real runner flow through immediately.
    shutil.copyfile(RUNNER, ops_dir / "run_skew_accrual.sh")
    (ops_dir / "run_skew_accrual.sh").chmod(0o755)
    if write_ledger:
        # Even with verify=OK we need a file so `wc -c` and the parquet
        # read don't blow up. A 0-row parquet satisfies both.
        try:
            import pandas as pd
            pd.DataFrame(columns=["date", "underlying", "skew"]).to_parquet(
                data_dir / "snapshots.parquet")
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
        "  rev-parse) echo \"$(git rev-parse --short HEAD 2>/dev/null || echo 0000000)\" ;;\n"
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
    py_shim = '''#!/usr/bin/env python3
"""Hermetic test shim: dispatches `python -m scripts.<name>` to the
fake module under $SKEW_OPS_ROOT/scripts/<name>.py."""
import os
import runpy
import sys

args = sys.argv[1:]
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