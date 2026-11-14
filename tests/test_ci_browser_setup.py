"""Chromium installs in the packed legacy manifest survive an apt outage.

Since ~13:45Z 2026-11-11 GitHub-hosted runners intermittently cannot resolve
any Ubuntu archive, so ``playwright install --with-deps`` — whose apt stage
shells out to the archive — killed whole packs before a single test ran
(PR #11041 run 43039248114: packs 1-5). The hosted ubuntu-24.04 image already
ships Chromium's system libraries, and no suite in this repo compares pixels
against visual baselines, so a bounded browser-only fallback keeps the job
alive and a genuinely missing library still fails the browser launch visibly.

Precedent: mastermind-terminal PR #1469 added the same bounded fallback; its
CI showed the fallback firing 42 times on hosted runners with every e2e test
still passing.

The three ``phase: browser_setup`` + ``acquisition: native_parallel`` steps
(bea-gvc-current-descriptive-consumer, ontology-explorer, unrun-brain-gateway)
are deliberately EXCLUDED from this shell-level pattern: their ``run`` string
is a validated contract token consumed by scripts/ci_browser_native_setup.py
(the pack runner never executes it as a shell command), and
scripts/run_ci_pack.py rejects any other text with "browser setup must be the
exact standalone installer". The native adapter performs the equivalent
bounded fallback in Python: after a SETTLED apt failure that provably applied
no packages, it attempts the same browser-only chromium install under the
remaining original deadline; unsettled native children stay fail-closed.
"""

import os
import re
import subprocess
from itertools import product
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"

# The native acquisition contract steps; mirrors the admitted-owner closure in
# scripts/run_ci_pack.py (NATIVE_*_LOGICAL_JOB_ID).
NATIVE_CONTRACT_JOBS = {
    "bea-gvc-current-descriptive-consumer",
    "ontology-explorer",
    "unrun-brain-gateway",
}

# Every plain (shell-executed) install must be bounded like the terminal PR:
# a 240s --with-deps first attempt then a 60s browser-only fallback, TERM
# first with a 15s kill-after, inside the step's existing job budget. The
# fallback fires only when the first attempt fails, and the step still fails
# when both attempts fail.
BOUNDED_INSTALL = re.compile(
    r"^timeout --signal=TERM --kill-after=15s 240s (python -m|npx) "
    r"playwright install --with-deps chromium +\|\| \{ echo \"::warning::[^\"]*\"; +"
    r"timeout --signal=TERM --kill-after=15s 60s (python -m|npx) "
    r"playwright install chromium;? \}$",
    re.MULTILINE,
)


def _install_steps():
    workflow = yaml.safe_load(MANIFEST.read_bytes())
    found = []
    for job_id, body in workflow["jobs"].items():
        for step in body.get("steps", []):
            if "playwright install --with-deps" in str(step.get("run", "")):
                found.append((job_id, step))
    return sorted(found)


def _plain_install_steps():
    return [(job, step) for job, step in _install_steps()
            if step.get("phase") != "browser_setup"]


def _one_line(run: str) -> str:
    """Join shell line continuations so the pattern is matched as bash sees it."""
    return re.sub(r"\\\s*\n\s*", " ", run)


def test_install_census_is_exact():
    steps = _install_steps()
    native = {job for job, step in steps if step.get("phase") == "browser_setup"}
    assert native == NATIVE_CONTRACT_JOBS
    # Every contract step stays the exact validated token the pack runner
    # admits; the shell fallback must never be smuggled into that surface.
    for job, step in steps:
        if step.get("phase") == "browser_setup":
            assert step["run"].strip() == "python -m playwright install --with-deps chromium", job
    assert len(_plain_install_steps()) == 7


def test_every_plain_with_deps_install_has_the_bounded_fallback():
    plain = _plain_install_steps()
    assert plain, "manifest lost every plain playwright install"
    for job, step in plain:
        run = step["run"]
        assert BOUNDED_INSTALL.search(_one_line(run)), job
        # No unbounded install survives: every line invoking playwright
        # install carries its own bounded timeout wrapper.
        for line in run.splitlines():
            if "playwright install" in line:
                assert "timeout --signal=TERM --kill-after=15s" in line, (job, line)


# The two real step shapes (python -m standalone, npm+npx block) executed as
# the pack runner executes every legacy step: `bash -eo pipefail -c`. The
# npm bootstrap stays un-timed exactly as before; only a direct, un-timed
# `playwright install` is the hazard the mocks flag.
MOCKS = r'''
npm() { echo "NPM $*"; return 0; }
python() { case " $* " in *" playwright install "*) echo "UNBOUNDED_INSTALL python $*";; esac; return "${UNBOUNDED_EXIT:-0}"; }
npx() { case " $* " in *" playwright install "*) echo "UNBOUNDED_INSTALL npx $*";; esac; return "${UNBOUNDED_EXIT:-0}"; }
timeout() {
  printf 'TIMEOUT %s\n' "$*"
  [ "$1" = "--signal=TERM" ] && [ "$2" = "--kill-after=15s" ] || return 98
  duration=$3
  shift 3
  case " $* " in
    *" playwright install --with-deps chromium "*) [ "$duration" = "240s" ] && return "$FULL_EXIT" || return 96;;
    *" playwright install chromium "*) [ "$duration" = "60s" ] && return "$BROWSER_EXIT" || return 96;;
  esac
  return 97
}
'''


def _real_step_runs():
    by_flavor = {}
    for _job, step in _plain_install_steps():
        run = step["run"]
        if "-m playwright install --with-deps" in run:
            by_flavor.setdefault("python-m", run)
        if "npx playwright install --with-deps" in run:
            by_flavor.setdefault("npx", run)
    assert set(by_flavor) == {"python-m", "npx"}
    return by_flavor


@pytest.mark.parametrize(("full_exit", "browser_exit"), list(product((0, 1, 124, 137), (0, 1))))
def test_real_install_steps_fall_back_once_and_preserve_failure(full_exit, browser_exit):
    for _flavor, run in _real_step_runs().items():
        script = MOCKS + "\n" + run + "\necho REACHED_TESTS\n"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "FULL_EXIT": str(full_exit),
            "BROWSER_EXIT": str(browser_exit),
        }
        result = subprocess.run(
            ["bash", "-eo", "pipefail", "-c", script], env=env,
            capture_output=True, text=True, timeout=5)
        should_pass = full_exit == 0 or browser_exit == 0
        assert (result.returncode == 0) is should_pass, result.stdout + result.stderr
        assert ("REACHED_TESTS" in result.stdout) is should_pass
        assert "UNBOUNDED_INSTALL" not in result.stdout
        assert result.stdout.count("TIMEOUT ") == (1 if full_exit == 0 else 2)
        assert ("::warning::" in result.stdout) is (full_exit != 0)
