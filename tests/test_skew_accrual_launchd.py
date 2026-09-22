"""Tests for the MO-PAID-013 W2-2 skew-accrual launchd lane.

Covers three surfaces:
  1. The plist parses and pins the runner path / env keys / schedule.
  2. The runner script is sh-clean and contains the required steps (refresh,
     freshness gate, accrue, publish) with the right env-var names.
  3. scripts/publish_r2._DATA_DIRS registers `options_skew` with a sane
     bytes floor and a sane min-files override.

The audit-tool tests live in tests/test_audit_options_skew_overlap.py.
All tests here use in-process fixtures — no real store, no network,
no launchd.
"""
from __future__ import annotations

import importlib.util
import plistlib
import subprocess
from pathlib import Path

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
    """StartCalendarInterval fires Mon–Fri at 04:30 or 05:30 local wall-clock
    (PDT/PST — launchd has no UTC mode; the runbook documents the choice).
    We pin the weekdays + that the schedule exists + that Hour/Minute are
    ints in the post-midnight band so the lane fires AFTER the
    ~11:30Z ThetaData EOD refresh observed on the M1 host."""
    p = _load_plist()
    intervals = p["StartCalendarInterval"]
    assert [d["Weekday"] for d in intervals] == [1, 2, 3, 4, 5]
    for d in intervals:
        assert d["Hour"] in (4, 5)
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
# 2. Runner script is sh-clean and contains the required steps.               #
# ─────────────────────────────────────────────────────────────────────────── #

def test_runner_script_passes_sh_n():
    """A single bash -n is enough to catch syntax errors; the launchd job
    runs this script daily, so a syntax drift would surface as a silent
    non-zero exit on every run."""
    rc = subprocess.run(["/bin/sh", "-n", str(RUNNER)],
                        capture_output=True, text=True, check=False)
    assert rc.returncode == 0, rc.stderr


def test_runner_invokes_the_freshness_gate():
    """The runner calls scripts/skew_accrual_gate.py via the Python `-m`
    form (so the helper lane owns its copy on the dedicated checkout,
    matching the seat's install runbook)."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "scripts.skew_accrual_gate" in src or "skew_accrual_gate.py" in src


def test_runner_invokes_build_options_skew_with_accrue():
    """W2-1b owns the --accrue flag on scripts/build_options_skew.py; the
    runner MUST pass the flag and refuse to fall back to a full run. Pin
    the literal in the runner so a future "simplification" that drops the
    flag fails here rather than at runtime on the M1."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "scripts.build_options_skew" in src
    assert "--accrue" in src


def test_runner_invokes_publish_r2_with_options_skew():
    src = RUNNER.read_text(encoding="utf-8")
    assert "scripts.publish_r2" in src
    assert "options_skew" in src


def test_runner_supports_bypass_and_dry_run_env_vars():
    """Both flags are the public escape hatches — the runbook documents
    `SKEW_FRESHNESS_BYPASS=1 SKEW_DRY_RUN=1` as the smoke command."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "SKEW_FRESHNESS_BYPASS" in src
    assert "SKEW_DRY_RUN" in src


def test_runner_refresh_step_refuses_dirty_checkout():
    """`git status --porcelain` is the gate. Pin the literal so the lane
    refuses to publish on a dirty tree even if the rest of the script
    drifts."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "git status --porcelain" in src
    assert "git fetch origin" in src
    assert "git checkout --detach origin/main" in src


def test_runner_does_not_push_to_git():
    """The lane NEVER pushes; the only outbound is publish_r2. A future
    edit that adds a `git push` (e.g. mirroring the dead
    `theta_surface_accrual.sh` precedent) is caught here at PR time."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "git push" not in src
    assert "git commit" not in src


def test_runner_log_receipts_use_line_start_format():
    """Every receipt line must start `[<UTC>] skew_accrual:` so the
    runbook's `grep -E '^\\[[^]]+\\] skew_accrual:'` narrow-tail works."""
    src = RUNNER.read_text(encoding="utf-8")
    # At least one match on the receipt prefix (log() / printf format)
    assert "skew_accrual:" in src
    assert "date -u" in src  # UTC stamp format


# ─────────────────────────────────────────────────────────────────────────── #
# 3. scripts/publish_r2._DATA_DIRS registers `options_skew` correctly.        #
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