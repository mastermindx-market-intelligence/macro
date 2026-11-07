"""scripts/ci/push_retry.sh — the shared lane push-retry policy.

Replays the 2026-07-25 failure that motivated it: render.yml run 30167139398 built a
correct scope=all render (1121 locked special-situations rows) and then lost all five
push attempts to

    ! [remote rejected] main -> main (cannot lock ref 'refs/heads/main':
      is at <X> but expected <Y>)

~95 minutes of render discarded. That rejection is a lost RACE for the ref, not a
conflict — the old loop applied the conflict remedy (`git rebase --abort` + a growing
deterministic sleep, 70s of budget across 5 attempts) to a race that only ever needed
one more re-sync-and-push.

The assertions that matter here:
  * a ref-lock loss and a non-fast-forward classify as `contention`, NOT as a conflict
  * an interrupted rebase classifies as `rebase-conflict` and gets the SLOW ladder
  * contention backs off strictly faster than a conflict at the same attempt number
  * the backoff is jittered (the old deterministic ladder made colliding lanes collide
    again on every retry)
  * the wall-clock deadline is a hard ceiling, so no loop outlives its job timeout
  * a real two-clone race is won on a later attempt instead of being thrown away
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from scripts.check_dag_conformance import _extract_steps_from_run
from scripts.workflow_run_source import resolve_run_source

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "scripts" / "ci" / "push_retry.sh"


def run_sh(body: str, *, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Source the library into a `bash -e` shell (GitHub's shell) and run `body`."""
    script = f'. "{LIB}"\n' + textwrap.dedent(body)
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(cwd or REPO_ROOT),
    )


def test_library_exists_and_is_sourceable():
    assert LIB.is_file(), f"{LIB} missing — the workflows source it by path"
    r = run_sh('push_retry_init "smoke"; echo "attempt=$PUSH_ATTEMPT max=$PUSH_MAX_ATTEMPTS"')
    assert r.returncode == 0, r.stderr
    assert "attempt=0 max=10" in r.stdout


# ---------------------------------------------------------------------------
# 1. Classification — the load-bearing table
# ---------------------------------------------------------------------------

CONTENTION_OUTPUTS = [
    # the exact 2026-07-25 render.yml run 30167139398 rejection
    "To github.com:user/repo.git\n ! [remote rejected] main -> main "
    "(cannot lock ref 'refs/heads/main': is at 0f2a1b3 but expected 9c8d7e6)\n"
    "error: failed to push some refs",
    "error: cannot lock ref 'refs/heads/main': unable to resolve reference",
    "error: Unable to create '/repo/.git/refs/heads/main.lock': File exists.",
    " ! [rejected]        main -> main (fetch first)\nerror: failed to push some refs",
    " ! [rejected]        main -> main (non-fast-forward)",
    "hint: Updates were rejected because the remote contains work that you do not have",
    " ! [rejected]        main -> main (stale info)",
]

NON_CONTENTION_OUTPUTS = [
    "remote: Permission to user/repo.git denied to dashboard-bot.\nfatal: unable to access",
    "remote: error: GH006: Protected branch update failed for refs/heads/main.",
    "remote: error: hook declined to update refs/heads/main",
]


@pytest.mark.parametrize("out", CONTENTION_OUTPUTS)
def test_ref_lock_and_non_ff_classify_as_contention(out):
    """A lost ref race must NOT be treated as a conflict — that was the whole bug."""
    r = run_sh(f'push_retry_init "t"; push_classify 1 {out!r}; echo "$PUSH_FAIL_CLASS"')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "contention", f"misclassified: {out!r}"


@pytest.mark.parametrize("out", NON_CONTENTION_OUTPUTS)
def test_auth_and_hook_rejections_are_not_contention(out):
    """Retrying faster never fixes a permission or hook rejection — don't call it a race."""
    r = run_sh(f'push_retry_init "t"; push_classify 1 {out!r}; echo "$PUSH_FAIL_CLASS"')
    assert r.stdout.strip() == "push-error", f"misclassified: {out!r}"


def test_signal_death_classifies_as_push_timeout():
    """The lanes alarm-bound git ops (macOS runners have no GNU timeout); a SIGALRM kill
    exits >=128 with no output and must not be read as a race."""
    r = run_sh('push_retry_init "t"; push_classify 142 ""; echo "$PUSH_FAIL_CLASS"')
    assert r.stdout.strip() == "push-timeout"


def test_git_exit_128_without_sigalrm_is_not_misclassified_as_timeout():
    out = "fatal: could not read Username for 'https://github.com': No such device or address"
    r = run_sh(f'push_retry_init "t"; push_classify 128 {out!r}; echo "$PUSH_FAIL_CLASS"')
    assert r.stdout.strip() == "push-error"


def test_every_class_has_a_plain_word_reason():
    r = run_sh(
        """
        push_retry_init "t"
        for c in contention rebase-conflict push-timeout push-error sync; do
          PUSH_FAIL_CLASS="$c"; printf '%s: %s\\n' "$c" "$(push_why)"
        done
        """
    )
    assert r.returncode == 0, r.stderr
    for line in r.stdout.strip().splitlines():
        cls, _, why = line.partition(": ")
        assert why.strip(), f"{cls} has no reason text"
    assert "no conflict, just retry" in r.stdout  # contention says so in plain words


# ---------------------------------------------------------------------------
# 2. Budgets — attempts and the hard wall-clock ceiling
# ---------------------------------------------------------------------------


def test_attempt_budget_is_ten_by_default_not_five():
    r = run_sh(
        """
        push_retry_init "t"
        n=0; while push_attempt; do n=$((n+1)); done
        echo "attempts=$n stop=$PUSH_STOP"
        """
    )
    assert "attempts=10" in r.stdout
    assert "attempt budget exhausted" in r.stdout


def test_attempt_budget_is_tunable():
    r = run_sh(
        """
        PUSH_MAX_ATTEMPTS=3
        push_retry_init "t"
        n=0; while push_attempt; do n=$((n+1)); done
        echo "attempts=$n"
        """
    )
    assert "attempts=3" in r.stdout


def test_deadline_is_a_hard_ceiling_that_stops_the_loop_early():
    """A job must never hang past its timeout-minutes waiting for a ref."""
    r = run_sh(
        """
        PUSH_BUDGET_SECS=0
        push_retry_init "t"
        n=0; while push_attempt; do n=$((n+1)); done
        echo "attempts=$n stop=$PUSH_STOP"
        """
    )
    # the first attempt is always allowed; the deadline stops everything after it
    assert "attempts=1" in r.stdout
    assert "time budget exhausted" in r.stdout


def test_backoff_never_sleeps_past_the_deadline():
    r = run_sh(
        """
        sleep() { echo "SLEPT $1"; }
        PUSH_BUDGET_SECS=3
        push_retry_init "t"
        push_attempt
        PUSH_FAIL_CLASS=rebase-conflict   # slow ladder, would want far more than 3s
        push_backoff
        """
    )
    slept = [int(l.split()[1]) for l in r.stdout.splitlines() if l.startswith("SLEPT")]
    assert slept and slept[0] <= 3, r.stdout


# ---------------------------------------------------------------------------
# 3. Backoff shape — the right remedy per class, and jitter
# ---------------------------------------------------------------------------


def _backoff_samples(cls: str, attempt: int, n: int = 30) -> list[int]:
    r = run_sh(
        f"""
        sleep() {{ echo "SLEPT $1"; }}
        for _ in $(seq {n}); do
          push_retry_init "t"
          PUSH_ATTEMPT={attempt}
          PUSH_FAIL_CLASS={cls}
          push_backoff
        done
        """
    )
    assert r.returncode == 0, r.stderr
    return [int(l.split()[1]) for l in r.stdout.splitlines() if l.startswith("SLEPT")]


def _backoff_complete_jitter_cycle(cls: str, attempt: int, period: int) -> list[int]:
    """Exercise every residue in the declared jitter support, not a lucky sample.

    RANDOM is made an ordinary variable only in this disposable test subprocess.
    The production policy is sourced unmodified. A fixed test clock prevents the
    independent deadline cap from censoring the distribution under test.
    """
    r = run_sh(
        f"""
        sleep() {{ echo "SLEPT $1"; }}
        date() {{ echo 100; }}
        unset RANDOM
        for ((draw=0; draw<{period}; draw++)); do
          RANDOM=$draw
          push_retry_init "complete-jitter-cycle"
          PUSH_ATTEMPT={attempt}
          PUSH_FAIL_CLASS={cls}
          push_backoff
        done
        """
    )
    assert r.returncode == 0, r.stderr
    samples = [int(line.split()[1]) for line in r.stdout.splitlines() if line.startswith("SLEPT")]
    assert len(samples) == period, r.stdout
    return samples


def test_contention_backs_off_faster_than_a_real_conflict():
    """Compare complete jitter-support means; runtime jitter remains enabled.

    Sixty independent random samples can violate this expectation inequality on
    a correct policy (actual Bash seeds 57/7976 give sums 308/462 at attempt 1).
    Enumerating the complete residues makes the same 1.5x policy test decisive
    without retrying until green or weakening its threshold. The support sizes
    below pin the intended uncapped/capped ladders; endpoint tests verify them.
    """
    for attempt, contention_period, conflict_period in ((1, 6, 9), (3, 12, 25), (5, 18, 41), (8, 21, 61)):
        contention = _backoff_complete_jitter_cycle("contention", attempt, contention_period)
        conflict = _backoff_complete_jitter_cycle("rebase-conflict", attempt, conflict_period)
        mean_c = sum(contention) / len(contention)
        mean_x = sum(conflict) / len(conflict)
        assert mean_c * 1.5 < mean_x, (
            f"attempt {attempt}: contention mean {mean_c:.1f} is not decisively faster "
            f"than conflict mean {mean_x:.1f}"
        )


def test_backoff_is_jittered_not_a_deterministic_ladder():
    """Load-bearing: the old `sleep $((i * 7))` was identical in every lane, so two
    lanes that collided once collided again on every retry."""
    for cls in ("contention", "rebase-conflict"):
        samples = _backoff_samples(cls, 4, n=40)
        assert len(set(samples)) > 1, f"{cls} backoff is deterministic: {samples}"


def test_backoff_is_capped_so_attempts_stay_inside_the_budget():
    # contention cap 20 -> jitter tops out at 20 + 20/2 = 30
    assert max(_backoff_samples("contention", 20)) <= 30
    # rebase-conflict cap 60 -> jitter tops out at 60 + 60/2 = 90
    assert max(_backoff_samples("rebase-conflict", 20)) <= 90


def test_backoff_logs_the_class_and_the_attempt_number():
    """`grep` on a failed run must show WHICH remedy was spent, and how often."""
    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "rendered site"
        push_attempt
        PUSH_FAIL_CLASS=contention
        push_backoff
        """
    )
    assert "rendered site push attempt 1/10 failed [contention]" in r.stdout
    assert "budget left" in r.stdout


def test_class_counters_census_the_two_failure_modes_separately():
    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "t"
        for c in contention contention rebase-conflict push-error; do
          push_attempt; PUSH_FAIL_CLASS="$c"; push_backoff
        done
        echo "contention=$PUSH_N_CONTENTION conflict=$PUSH_N_CONFLICT other=$PUSH_N_OTHER"
        """
    )
    assert "contention=2 conflict=1 other=1" in r.stdout


# ---------------------------------------------------------------------------
# 4. push_abort_rebase — only an interrupted rebase is a conflict
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _git_output(repo: Path, *args: str, input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        input=input_text,
    ).stdout.strip()


def _logging_git(tmp_path: Path, log: Path) -> Path:
    """Put a transparent git wrapper on PATH and record one command name per call."""
    fakebin = tmp_path / "logging-bin"
    fakebin.mkdir(exist_ok=True)
    real_git = subprocess.run(
        ["which", "git"], capture_output=True, text=True, check=True
    ).stdout.strip()
    wrapper = fakebin / "git"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$1\" >> {str(log)!r}\n"
        f'exec {real_git!r} "$@"\n'
    )
    wrapper.chmod(0o755)
    return fakebin


def _untracked_collision_fixture(tmp_path: Path, *, collision: bool) -> tuple[Path, str]:
    """A lane behind origin/main with either an exact local collision or a no-op."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    seed = tmp_path / "seed"
    _init_repo(seed)
    (seed / "README").write_text("seed")
    _git_output(seed, "add", ".")
    _git_output(seed, "commit", "-m", "seed")
    _git_output(seed, "push", "-q", str(bare), "main")
    lane, other = tmp_path / "lane", tmp_path / "other"
    for repo in (lane, other):
        subprocess.run(["git", "clone", "-q", str(bare), str(repo)], check=True)
        _git_output(repo, "config", "user.email", "t@t")
        _git_output(repo, "config", "user.name", "t")
    path = "data/generated/cache name.json"
    if collision:
        target = other / path
        target.parent.mkdir(parents=True)
        target.write_text("main")
        _git_output(other, "add", path)
        _git_output(other, "commit", "-m", "track cache")
        _git_output(other, "push", "-q", "origin", "main")
        target = lane / path
        target.parent.mkdir(parents=True)
        target.write_text("local")
    else:
        (lane / "untracked only.txt").write_text("keep")
    (lane / "site").mkdir()
    (lane / "site" / "staged.html").write_text("staged render")
    _git_output(lane, "add", "site/staged.html")
    _git_output(lane, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
    return lane, path


def test_untracked_collision_helper_is_local_noop_without_a_collision(tmp_path):
    lane, _ = _untracked_collision_fixture(tmp_path, collision=False)
    runner_temp = tmp_path / "runner-temp"; runner_temp.mkdir()
    r = run_sh(
        'push_quarantine_untracked_collisions origin/main; echo "count=$PUSH_QUARANTINE_COUNT"',
        env={"RUNNER_TEMP": str(runner_temp)},
        cwd=lane,
    )
    assert r.returncode == 0, r.stderr
    assert "count=0" in r.stdout
    assert (lane / "untracked only.txt").read_text() == "keep"
    assert _git_output(lane, "diff", "--cached", "--name-only") == "site/staged.html"
    assert list(runner_temp.iterdir()) == []


def test_untracked_collision_helper_fails_closed_outside_actions(tmp_path):
    lane, path = _untracked_collision_fixture(tmp_path, collision=True)
    runner_temp = tmp_path / "runner-temp"; runner_temp.mkdir()
    r = run_sh(
        "push_quarantine_untracked_collisions origin/main",
        # GitHub Actions exports this in the outer process running CI; make this
        # fixture explicitly emulate a local checkout instead.
        env={"GITHUB_ACTIONS": "false", "RUNNER_TEMP": str(runner_temp)},
        cwd=lane,
    )
    assert r.returncode != 0
    assert "refusing to relocate local work outside GitHub Actions" in r.stdout
    assert (lane / path).read_text() == "local"
    assert _git_output(lane, "diff", "--cached", "--name-only") == "site/staged.html"
    assert list(runner_temp.iterdir()) == []


def test_ignored_collision_reproduces_detach_failure_then_quarantines_safely(tmp_path):
    lane, path = _untracked_collision_fixture(tmp_path, collision=True)
    runner_only = lane / "data/generated/runner-only.json"
    runner_only.write_text("keep")
    info_exclude = lane / ".git" / "info" / "exclude"
    info_exclude.write_text("data/generated/runner-only.json\n")
    _git_output(lane, "commit", "-m", "engine outputs")
    (lane / "README").write_text("runner dirt")

    raw_rebase = subprocess.run(
        ["git", "rebase", "--autostash", "origin/main"],
        cwd=lane,
        text=True,
        capture_output=True,
        check=False,
    )
    raw_output = raw_rebase.stdout + raw_rebase.stderr
    assert raw_rebase.returncode != 0
    assert "untracked working tree files would be overwritten by checkout" in raw_output
    assert "could not detach HEAD" in raw_output
    assert (lane / path).read_text() == "local"

    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    result = run_sh(
        """
        push_retry_init "engine outputs"
        push_quarantine_untracked_collisions origin/main
        git rebase --autostash origin/main
        push_autostash_ok
        """,
        env={
            "GITHUB_ACTIONS": "true",
            "RUNNER_TEMP": str(runner_temp),
        },
        cwd=lane,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    quarantines = sorted(runner_temp.glob("push-untracked-collision.*"))
    assert len(quarantines) == 1
    quarantined_collision = quarantines[0] / "files" / path
    assert quarantined_collision.read_text() == "local"
    assert (lane / path).read_text() == "main"
    assert runner_only.read_text() == "keep"
    assert (lane / "README").read_text() == "runner dirt"


def test_untracked_collision_scan_uses_one_target_tree_process_for_many_paths(tmp_path):
    """Regression for the four-minute render retry setup measured on 2026-08-13.

    The retained runner had about 15k ignored outputs. The old helper launched
    `git ls-tree` once per path, then repeated the loop while moving collisions.
    The target tree must be enumerated once regardless of candidate count.
    """
    lane, collision_path = _untracked_collision_fixture(tmp_path, collision=True)
    noise_dir = lane / "data/generated/noise"
    noise_dir.mkdir(parents=True)
    for i in range(400):
        (noise_dir / f"ignored-{i:04d}.json").write_text("runner-only")
    info_exclude = lane / ".git" / "info" / "exclude"
    with info_exclude.open("a") as f:
        f.write("data/generated/noise/\n")

    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    command_log = tmp_path / "git-commands.log"
    fakebin = _logging_git(tmp_path, command_log)
    result = run_sh(
        "push_quarantine_untracked_collisions origin/main",
        env={
            "GITHUB_ACTIONS": "true",
            "RUNNER_TEMP": str(runner_temp),
            "PATH": f"{fakebin}:{os.environ['PATH']}",
        },
        cwd=lane,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    commands = command_log.read_text().splitlines()
    assert commands.count("ls-tree") == 1, commands
    assert not (lane / collision_path).exists()
    assert (noise_dir / "ignored-0399.json").read_text() == "runner-only"


def _daily_engine_commit_step() -> tuple[dict, dict]:
    workflow = REPO_ROOT / ".github" / "workflows" / "daily.yml"
    doc = yaml.safe_load(workflow.read_text())
    step = next(
        item
        for item in doc["jobs"]["engine"]["steps"]
        if item.get("name") == "commit engine outputs"
    )
    # 512KB-cap diet: the body lives in scripts/ci/ — resolve the effective
    # source so these assertions keep reading what the step actually runs.
    step["run"] = resolve_run_source(step["run"], REPO_ROOT)
    return doc, step


CORE_ENGINE_CHECKPOINT_NAME = (
    "checkpoint core engine outputs to main (durable before tail desks)"
)


def _daily_engine_steps() -> list[dict]:
    workflow = REPO_ROOT / ".github" / "workflows" / "daily.yml"
    return yaml.safe_load(workflow.read_text())["jobs"]["engine"]["steps"]


def test_daily_engine_checkpoints_core_outputs_before_tail_desks():
    steps = _daily_engine_steps()
    names = [step.get("name") for step in steps]
    checkpoint_index = names.index(CORE_ENGINE_CHECKPOINT_NAME)
    regional_index = next(
        index
        for index, name in enumerate(names)
        if str(name).startswith("regional + desk builders")
    )
    membership_index = names.index(
        "membership snapshot freshness tripwire (advisory)"
    )
    tail_index = names.index("timings band — tail-desks (W2)")

    assert regional_index < checkpoint_index < membership_index < tail_index

    checkpoint = steps[checkpoint_index]
    assert checkpoint["if"] == "always()"
    assert checkpoint["timeout-minutes"] == 25
    assert checkpoint["continue-on-error"] is True
    assert checkpoint["run"] == "bash scripts/ci/daily_engine_commit_outputs.sh"


def test_daily_engine_keeps_final_commit_after_core_checkpoint():
    steps = _daily_engine_steps()
    publisher_steps = [
        step
        for step in steps
        if step.get("run") == "bash scripts/ci/daily_engine_commit_outputs.sh"
    ]

    assert [step.get("name") for step in publisher_steps] == [
        CORE_ENGINE_CHECKPOINT_NAME,
        "commit engine outputs",
    ]
    assert publisher_steps[0]["continue-on-error"] is True
    assert publisher_steps[1]["if"] == "always()"


def test_daily_engine_core_checkpoint_is_fully_declared_in_dag():
    dag = yaml.safe_load((REPO_ROOT / "config" / "dag.yml").read_text())
    engine = next(
        lane
        for lane in dag["lanes"]
        if lane["workflow"] == ".github/workflows/daily.yml"
        and lane["job"] == "engine"
    )
    steps = engine["steps"]
    ids = [step.get("id") for step in steps]
    start = ids.index("checkpoint_core_precommit_inject_data_base")
    expected = [
        ("checkpoint_core_precommit_inject_data_base", "scripts.inject_data_base", None),
        ("checkpoint_core_precommit_externalize_css", "scripts.externalize_css", None),
        ("checkpoint_core_precommit_optimize_assets", "scripts.optimize_assets", None),
        (
            "checkpoint_core_precommit_check_template_site_sync",
            "scripts.check_template_site_sync",
            ["--fix"],
        ),
        (
            "checkpoint_core_gold_render_audit",
            "scripts.audit_china_gold_premium",
            ["--strict-render"],
        ),
        (
            "checkpoint_core_commodity_recovery",
            "scripts.check_commodity_publication",
            ["--heal-from", "$COMMODITY_ACCEPTED"],
        ),
        ("checkpoint_core_postrebase_inject_data_base", "scripts.inject_data_base", None),
        ("checkpoint_core_postrebase_externalize_css", "scripts.externalize_css", None),
        ("checkpoint_core_postrebase_optimize_assets", "scripts.optimize_assets", None),
        (
            "checkpoint_core_postrebase_check_template_site_sync",
            "scripts.check_template_site_sync",
            ["--fix"],
        ),
        (
            "checkpoint_core_commodity_candidate",
            "scripts.check_commodity_publication",
            ["--accepted-ref", "$COMMODITY_ACCEPTED", "--candidate-ref", "$qledger_push_candidate"],
        ),
    ]

    declared = steps[start : start + len(expected)]
    assert [
        (step.get("id"), step.get("module"), step.get("args"))
        for step in declared
    ] == expected

    publisher_source = resolve_run_source(
        "bash scripts/ci/daily_engine_commit_outputs.sh", REPO_ROOT
    )
    actual_modules = [
        step.module for step in _extract_steps_from_run(publisher_source)
    ]
    assert [step.get("module") for step in declared] == actual_modules
    assert steps[start + len(expected)]["id"] == "check_builder_failstreaks"



@pytest.mark.parametrize(
    ("workflow", "job", "expected_count"),
    [
        ("daily.yml", "engine", 4),
        ("engine-render.yml", "engine-render", 2),
        ("render.yml", "render", 3),
    ],
)
def test_each_commodity_publication_guard_is_declared(workflow, job, expected_count):
    """The general DAG parser caps repeated modules; these guards must be exact."""
    dag = yaml.safe_load((REPO_ROOT / "config" / "dag.yml").read_text())
    lane = next(
        lane for lane in dag["lanes"]
        if lane["workflow"] == f".github/workflows/{workflow}" and lane["job"] == job
    )
    declared = [
        step for step in lane["steps"]
        if step.get("module") == "scripts.check_commodity_publication"
    ]
    workflow_doc = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / workflow).read_text()
    )
    actual = [
        call for step in workflow_doc["jobs"][job]["steps"]
        for call in _extract_steps_from_run(resolve_run_source(step.get("run", ""), REPO_ROOT))
        if call.module == "scripts.check_commodity_publication"
    ]
    assert len(declared) == len(actual) == expected_count
    assert len({step["id"] for step in declared}) == expected_count


def test_daily_engine_lane_uses_quarantine_helper_for_fast_main_retries():
    _doc, step = _daily_engine_commit_step()
    run = step["run"]
    loop = run[run.index('push_retry_init "engine outputs"') :]
    assert "while push_attempt; do" in loop
    assert "push_fetch_main_for_rebase" in loop
    assert "git rebase --autostash -X theirs origin/main" in loop
    assert loop.index("push_fetch_main_for_rebase") < loop.index(
        "git rebase --autostash"
    )
    assert "push_do" in loop
    assert "push_backoff" in loop
    assert "git pull --rebase --autostash -X theirs origin main" not in loop
    assert "git ls-files --others --exclude-standard |" not in loop
    assert 'rm -f -- "$f"' not in loop


def test_daily_engine_push_loss_is_red_without_suppressing_delivery_tail():
    doc, step = _daily_engine_commit_step()
    run = step["run"]
    lost_tail = run[run.index("push_lost") :]
    assert "::error title=nightly engine outputs NOT pushed" in lost_tail
    assert lost_tail.rstrip().endswith("exit 1")

    steps = doc["jobs"]["engine"]["steps"]
    commit_index = steps.index(step)
    for delivery_step in steps[commit_index + 1 :]:
        assert delivery_step.get("if") == "always()", delivery_step.get("name")

    for job_name, job in doc["jobs"].items():
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        if "engine" in needs:
            assert str(job.get("if", "")).strip().startswith("always()"), job_name


def _object_is_local(repo: Path, oid: str) -> bool:
    loose = repo / ".git" / "objects" / oid[:2] / oid[2:]
    if loose.exists():
        return True
    for index in (repo / ".git" / "objects" / "pack").glob("*.idx"):
        packed = subprocess.run(
            ["git", "verify-pack", "-v", index],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if any(line.startswith(f"{oid} ") for line in packed.splitlines()):
            return True
    return False


def test_metadata_replay_preserves_new_main_without_fetching_promised_blobs(tmp_path):
    """The render's common race path is a tree merge, not a checkout/rebase.

    A concurrent data commit must survive, the generated site must land, and an
    unchanged 1 MiB promised blob must remain absent from the blobless lane clone.
    """
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git_output(bare, "config", "uploadpack.allowFilter", "true")

    seed = tmp_path / "seed"
    _init_repo(seed)
    (seed / "site").mkdir()
    (seed / "data").mkdir()
    (seed / "site" / "index.html").write_text("<html>old</html>\n")
    (seed / "site" / "unchanged.bin").write_bytes(b"x" * 1024 * 1024)
    (seed / "data" / "live.txt").write_text("base\n")
    _git_output(seed, "add", ".")
    _git_output(seed, "commit", "-m", "seed")
    _git_output(seed, "push", "-q", str(bare), "main")

    lane = tmp_path / "lane"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--no-checkout",
            "--filter=blob:none",
            "--depth=1",
            "--branch",
            "main",
            f"file://{bare}",
            str(lane),
        ],
        check=True,
    )
    _git_output(lane, "config", "user.email", "render@example.test")
    _git_output(lane, "config", "user.name", "render-test")
    render_parent = _git_output(lane, "rev-parse", "HEAD")
    stable_blob = _git_output(lane, "rev-parse", "HEAD:site/unchanged.bin")
    assert not _object_is_local(lane, stable_blob)

    # Build a site-only render commit directly from the index. No checkout is needed.
    _git_output(lane, "read-tree", "HEAD")
    rendered_blob = _git_output(
        lane,
        "hash-object",
        "-w",
        "--stdin",
        input_text="<html>fresh render</html>\n",
    )
    _git_output(
        lane,
        "update-index",
        "--add",
        "--cacheinfo",
        "100644",
        rendered_blob,
        "site/index.html",
    )
    rendered_tree = _git_output(lane, "write-tree", "--missing-ok")
    render_commit = _git_output(
        lane,
        "commit-tree",
        rendered_tree,
        "-p",
        render_parent,
        input_text="render: site re-render\n",
    )
    assert not _object_is_local(lane, stable_blob)

    # Main advances while the render is running, but only outside generated outputs.
    (seed / "data" / "live.txt").write_text("concurrent main\n")
    (seed / "code.txt").write_text("new code\n")
    _git_output(seed, "add", "data/live.txt", "code.txt")
    _git_output(seed, "commit", "-m", "advance main")
    _git_output(seed, "push", "-q", str(bare), "main")
    _git_output(lane, "fetch", "-q", "--depth=2", "origin", "main")
    concurrent_main = _git_output(lane, "rev-parse", "origin/main")
    assert not _object_is_local(lane, stable_blob)

    index_path = tmp_path / "publish.index"
    r = run_sh(
        """
        replay=$(push_metadata_replay_commit \
          "$RENDER_PARENT" origin/main "$RENDER_COMMIT" \
          "render: site re-render" "$PUBLISH_INDEX")
        echo "replay=$replay"
        """,
        env={
            "RENDER_PARENT": render_parent,
            "RENDER_COMMIT": render_commit,
            "PUBLISH_INDEX": str(index_path),
        },
        cwd=lane,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    replay = next(line.removeprefix("replay=") for line in r.stdout.splitlines() if line.startswith("replay="))
    assert not _object_is_local(lane, stable_blob)
    _git_output(lane, "update-ref", "refs/heads/render-publish-test", replay)
    assert not _object_is_local(lane, stable_blob)
    _git_output(
        lane,
        "push",
        "-q",
        "origin",
        "refs/heads/render-publish-test:refs/heads/main",
    )
    published = _git_output(bare, "rev-parse", "refs/heads/main")
    assert _git_output(bare, "rev-parse", f"{published}^") == concurrent_main
    assert _git_output(bare, "show", f"{published}:site/index.html") == (
        "<html>fresh render</html>"
    )
    assert _git_output(bare, "show", f"{published}:data/live.txt") == "concurrent main"
    assert _git_output(bare, "show", f"{published}:code.txt") == "new code"
    assert not index_path.exists()
    assert not _object_is_local(lane, stable_blob)


def test_metadata_replay_batches_git_processes_for_large_render_delta(tmp_path):
    """A large render delta must not translate into per-path Git processes.

    Run 31728157679 changed 2,817 paths; the old helper launched three ls-tree
    calls and one update-index call for every path, so each metadata retry took
    about four minutes and repeatedly lost to the five-minute hot-tape writer.
    """
    repo = tmp_path / "repo"
    _init_repo(repo)
    site = repo / "site"
    site.mkdir()
    for i in range(400):
        (site / f"page {i:04d}.html").write_text(f"base {i}\n")
    odd_paths = ["space name.html", "tab\tname.html", "line\nname.html"]
    for path in odd_paths:
        (site / path).write_text("base odd\n")
    _git_output(repo, "add", "site")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")

    for i in range(400):
        (site / f"page {i:04d}.html").write_text(f"render {i}\n")
    for path in odd_paths:
        (site / path).write_text("render odd\n")
    _git_output(repo, "commit", "-am", "render")
    render_commit = _git_output(repo, "rev-parse", "HEAD")

    _git_output(repo, "checkout", "-q", "-b", "onto", base)
    (repo / "concurrent.txt").write_text("main survives\n")
    _git_output(repo, "add", "concurrent.txt")
    _git_output(repo, "commit", "-m", "advance main")
    onto = _git_output(repo, "rev-parse", "HEAD")

    command_log = tmp_path / "git-commands.log"
    fakebin = _logging_git(tmp_path, command_log)
    result = run_sh(
        """
        replay=$(push_metadata_replay_commit "$BASE" "$ONTO" "$RENDER" \
          "render: batched metadata replay" "$INDEX")
        echo "replay=$replay"
        """,
        env={
            "BASE": base,
            "ONTO": onto,
            "RENDER": render_commit,
            "INDEX": str(tmp_path / "publish.index"),
            "RUNNER_TEMP": str(tmp_path),
            "PATH": f"{fakebin}:{os.environ['PATH']}",
        },
        cwd=repo,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    replay = next(
        line.removeprefix("replay=")
        for line in result.stdout.splitlines()
        if line.startswith("replay=")
    )
    commands = command_log.read_text().splitlines()
    assert commands.count("diff-tree") == 2, commands
    assert commands.count("ls-tree") == 0, commands
    assert commands.count("update-index") == 1, commands
    assert _git_output(repo, "rev-parse", f"{replay}^") == onto
    assert _git_output(repo, "show", f"{replay}:site/page 0399.html") == "render 399"
    for path in odd_paths:
        assert _git_output(repo, "show", f"{replay}:site/{path}") == "render odd"
    assert _git_output(repo, "show", f"{replay}:concurrent.txt") == "main survives"


def test_metadata_replay_reports_a_real_same_path_conflict(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "site").mkdir()
    (repo / "site" / "index.html").write_text("base\n")
    _git_output(repo, "add", ".")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")

    (repo / "site" / "index.html").write_text("render\n")
    _git_output(repo, "commit", "-am", "render")
    render_commit = _git_output(repo, "rev-parse", "HEAD")
    _git_output(repo, "checkout", "-q", "-b", "new-main", base)
    (repo / "site" / "index.html").write_text("new main\n")
    _git_output(repo, "commit", "-am", "new main")
    new_main = _git_output(repo, "rev-parse", "HEAD")

    r = run_sh(
        """
        if push_metadata_replay_commit "$BASE" "$ONTO" "$RENDER" \
             "should conflict" "$INDEX"; then
          echo "unexpected success"
          exit 1
        fi
        echo "fallback required"
        """,
        env={
            "BASE": base,
            "ONTO": new_main,
            "RENDER": render_commit,
            "INDEX": str(tmp_path / "conflict.index"),
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "fallback required" in r.stdout


@pytest.mark.parametrize("partial", [False, True])
def test_metadata_replay_rejects_failed_diff_enumeration_even_with_prefix(
    tmp_path, partial
):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a").write_text("a0\n")
    (repo / "b").write_text("b0\n")
    _git_output(repo, "add", ".")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")
    (repo / "a").write_text("a1\n")
    (repo / "b").write_text("b1\n")
    _git_output(repo, "commit", "-am", "candidate")
    candidate = _git_output(repo, "rev-parse", "HEAD")

    r = run_sh(
        """
        git() {
          if [ "${1:-}" = diff-tree ]; then
            if [ "$PARTIAL" = 1 ]; then printf 'M\\0a\\0'; fi
            return 86
          fi
          command git "$@"
        }
        if push_metadata_replay_commit "$BASE" "$BASE" "$CANDIDATE" \
             "must fail" "$INDEX"; then
          echo unexpected-success
          exit 1
        fi
        test ! -e "$INDEX"
        """,
        env={
            "BASE": base,
            "CANDIDATE": candidate,
            "INDEX": str(tmp_path / "failed.index"),
            "PARTIAL": "1" if partial else "0",
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "cannot enumerate" in r.stderr


def test_exact_path_replay_rejects_mixed_checkpoint_generations(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a").write_text("a0\n")
    (repo / "b").write_text("b0\n")
    _git_output(repo, "add", ".")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")

    # Candidate changes only b, but its complete checkpoint still binds a=a0.
    (repo / "b").write_text("b1\n")
    _git_output(repo, "commit", "-am", "candidate")
    candidate = _git_output(repo, "rev-parse", "HEAD")
    _git_output(repo, "checkout", "-q", "-b", "onto", base)
    (repo / "a").write_text("a2\n")
    _git_output(repo, "commit", "-am", "onto")
    onto = _git_output(repo, "rev-parse", "HEAD")

    r = run_sh(
        """
        if push_exact_paths_replay_commit "$BASE" "$ONTO" "$CANDIDATE" \
             "must refuse mixed generations" "$INDEX" a b; then
          echo unexpected-success
          exit 1
        fi
        """,
        env={
            "BASE": base,
            "ONTO": onto,
            "CANDIDATE": candidate,
            "INDEX": str(tmp_path / "exact.index"),
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "exact metadata replay conflict" in r.stderr


def test_abort_rebase_flags_a_conflict_only_when_a_rebase_is_in_progress(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a").write_text("a")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c"], check=True)

    # no rebase in progress: a contention verdict must survive untouched
    r = run_sh(
        'push_retry_init "t"; PUSH_FAIL_CLASS=contention; push_abort_rebase; echo "$PUSH_FAIL_CLASS"',
        cwd=repo,
    )
    assert r.stdout.strip() == "contention", r.stderr

    # a stopped rebase IS a conflict, and gets the slow ladder
    (repo / ".git" / "rebase-merge").mkdir()
    r = run_sh(
        'push_retry_init "t"; PUSH_FAIL_CLASS=contention; push_abort_rebase; echo "$PUSH_FAIL_CLASS"',
        cwd=repo,
    )
    assert r.stdout.strip() == "rebase-conflict", r.stderr


def test_abort_rebase_quits_malformed_stale_state_when_abort_cannot(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a").write_text("a")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c"], check=True)

    # A cancelled self-hosted job can leave only the rebase directory behind.
    # `git rebase --abort` cannot parse this state; the helper must still clear it
    # so every retry does not die with "already a rebase-merge directory".
    stale = repo / ".git" / "rebase-merge"
    stale.mkdir()
    r = run_sh(
        'push_retry_init "t"; PUSH_FAIL_CLASS=contention; push_abort_rebase; echo "$PUSH_FAIL_CLASS"',
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "rebase-conflict", r.stderr
    assert not stale.exists(), "malformed stale rebase metadata survived cleanup"


def test_abort_rebase_fails_closed_when_quit_exposes_partial_rebase_state(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "file").write_text("base\n")
    _git_output(repo, "add", "file")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")

    _git_output(repo, "checkout", "-b", "upstream")
    (repo / "file").write_text("upstream\n")
    _git_output(repo, "commit", "-am", "upstream")

    _git_output(repo, "checkout", "-b", "topic", base)
    (repo / "file").write_text("topic\n")
    _git_output(repo, "commit", "-am", "topic")
    conflict = subprocess.run(
        ["git", "-C", str(repo), "rebase", "upstream"],
        check=False, capture_output=True, text=True,
    )
    assert conflict.returncode != 0

    # Corrupt a genuine stopped rebase the same way a cancelled shared runner can:
    # abort can no longer restore the original branch, while quit can only remove
    # metadata and necessarily leaves the detached HEAD + unmerged index behind.
    stale = repo / ".git" / "rebase-merge"
    (stale / "head-name").unlink()
    (stale / "orig-head").unlink()
    r = run_sh(
        'push_retry_init "t"; PUSH_FAIL_CLASS=contention; push_abort_rebase',
        cwd=repo,
    )
    assert r.returncode != 0, (
        "cleanup returned success even though quit left a partial rebase state "
        f"that a bash -e caller could mistake for a retryable clean workspace:\n{r.stdout}\n{r.stderr}"
    )
    assert "partial rebase state survived cleanup" in r.stderr
    assert not stale.exists(), "quit did not remove malformed rebase metadata"
    assert _git_output(repo, "diff", "--name-only", "--diff-filter=U") == "file"
    branch = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "-q", "HEAD"],
        check=False, capture_output=True, text=True,
    )
    assert branch.returncode != 0, "fixture no longer represents a detached partial rebase"


def _current_attempt_conflict_repo(tmp_path: Path, *, dirty: bool = False) -> tuple[Path, str]:
    repo = tmp_path / ("repo-dirty" if dirty else "repo-clean")
    bare = tmp_path / ("origin-dirty.git" if dirty else "origin-clean.git")
    _init_repo(repo)
    for name, body in (
        ("file", "base\n"),
        ("staged.txt", "base staged\n"),
        ("unstaged.txt", "base unstaged\n"),
    ):
        (repo / name).write_text(body)
    _git_output(repo, "add", ".")
    _git_output(repo, "commit", "-m", "base")
    base = _git_output(repo, "rev-parse", "HEAD")

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git_output(repo, "remote", "add", "origin", str(bare))
    _git_output(repo, "push", "-u", "origin", "main")

    # origin/main is the exact upstream target used by production retry callers.
    (repo / "file").write_text("upstream\n")
    _git_output(repo, "commit", "-am", "upstream")
    _git_output(repo, "push", "origin", "main")

    _git_output(repo, "checkout", "-b", "topic", base)
    (repo / "file").write_text("topic\n")
    _git_output(repo, "commit", "-am", "topic")
    topic_head = _git_output(repo, "rev-parse", "HEAD")
    if dirty:
        (repo / "staged.txt").write_text("current attempt staged\n")
        _git_output(repo, "add", "staged.txt")
        (repo / "unstaged.txt").write_text("current attempt unstaged\n")
    return repo, topic_head

def _install_inherited_complete_rebase(repo: Path, tmp_path: Path) -> Path:
    """Park a prior invocation's complete stopped rebase over a clean attached topic."""
    conflict = subprocess.run(
        ["git", "-C", str(repo), "rebase", "origin/main"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert conflict.returncode != 0
    git_dir = Path(_git_output(repo, "rev-parse", "--absolute-git-dir"))
    state = git_dir / "rebase-merge"
    assert state.is_dir()
    saved = tmp_path / "inherited-rebase-merge"
    shutil.copytree(state, saved)
    _git_output(repo, "rebase", "--abort")
    assert _git_output(repo, "symbolic-ref", "--short", "HEAD") == "topic"
    assert _git_output(repo, "diff", "--name-only", "--diff-filter=U") == ""
    shutil.copytree(saved, state)
    return git_dir

def test_fetch_rebase_discards_inherited_complete_state_before_binding_current_attempt(tmp_path):
    """A retained runner must not normal-abort using a previous invocation's orig-head."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    git_dir = _install_inherited_complete_rebase(repo, tmp_path)

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 1
        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test -z "$(git ls-files -u)"
        test "$(cat file)" = topic
        test ! -d "$GIT_DIR/rebase-merge"
        test ! -d "$GIT_DIR/rebase-apply"

        rc=0
        out=$(git rebase origin/main 2>&1) || rc=$?
        test "$rc" -ne 0
        case "$out" in
          *"already a rebase-merge directory"*|*"index contains uncommitted changes"*|*"unstaged changes"*)
            echo "$out" >&2
            exit 71
            ;;
        esac
        test -d "$GIT_DIR/rebase-merge"
        git rebase --abort
        """,
        env={"TOPIC_HEAD": topic_head, "GIT_DIR": str(git_dir)},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"



def test_inherited_cleanup_uses_quit_and_never_normal_abort(tmp_path):
    """Inherited orig-head/autostash metadata is never accepted as this retry's authority."""
    repo, _ = _current_attempt_conflict_repo(tmp_path)
    _install_inherited_complete_rebase(repo, tmp_path)
    real_git = subprocess.run(
        ["which", "git"], capture_output=True, text=True, check=True
    ).stdout.strip()
    log = tmp_path / "git-args.log"
    fakebin = tmp_path / "logging-args-bin"
    fakebin.mkdir()
    wrapper = fakebin / "git"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {str(log)!r}\n"
        f'exec {real_git!r} "$@"\n'
    )
    wrapper.chmod(0o755)

    r = run_sh(
        'push_retry_init "t"; push_attempt; push_fetch_main_for_rebase',
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    calls = log.read_text().splitlines()
    assert "rebase --quit" in calls, calls
    assert "rebase --abort" not in calls, calls


def test_inherited_cleanup_never_overwrites_concurrent_branch_ref_movement(tmp_path):
    """The current-attempt anchor fences local branch movement during inherited cleanup."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    git_dir = _install_inherited_complete_rebase(repo, tmp_path)
    moved_head = _git_output(repo, "rev-parse", "origin/main")
    real_git = subprocess.run(
        ["which", "git"], capture_output=True, text=True, check=True
    ).stdout.strip()
    fakebin = tmp_path / "move-branch-bin"
    fakebin.mkdir()
    wrapper = fakebin / "git"
    wrapper.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        if [ "$1" = rebase ] && [ "$2" = --quit ]; then
          {real_git!r} "$@"
          rc=$?
          if [ "$rc" -eq 0 ]; then
            {real_git!r} update-ref refs/heads/topic "$MOVED_HEAD" "$TOPIC_HEAD"
          fi
          exit "$rc"
        fi
        exec {real_git!r} "$@"
        """))
    wrapper.chmod(0o755)

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        if push_fetch_main_for_rebase; then
          echo "concurrent branch movement was overwritten" >&2
          exit 74
        fi
        test "$(git rev-parse refs/heads/topic)" = "$MOVED_HEAD"
        test "$(git rev-parse HEAD)" = "$MOVED_HEAD"
        test "$PUSH_ATTEMPT_INHERITED_REBASE" -eq 1
        test ! -d "$GIT_DIR/rebase-merge"
        """,
        env={
            "PATH": f"{fakebin}:{os.environ['PATH']}",
            "TOPIC_HEAD": topic_head,
            "MOVED_HEAD": moved_head,
            "GIT_DIR": str(git_dir),
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"



def test_failed_inherited_recovery_is_sticky_across_retry_attempts(tmp_path):
    """A failed inherited-state recovery cannot be recaptured as fresh authority."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    _install_inherited_complete_rebase(repo, tmp_path)
    moved_head = _git_output(repo, "rev-parse", "origin/main")
    real_git = subprocess.run(
        ["which", "git"], capture_output=True, text=True, check=True
    ).stdout.strip()
    fakebin = tmp_path / "sticky-failure-bin"
    fakebin.mkdir()
    wrapper = fakebin / "git"
    wrapper.write_text(textwrap.dedent(f"""\\
        #!/usr/bin/env bash
        if [ "$1" = rebase ] && [ "$2" = --quit ]; then
          {real_git!r} "$@"
          rc=$?
          if [ "$rc" -eq 0 ]; then
            {real_git!r} update-ref refs/heads/topic "$MOVED_HEAD" "$TOPIC_HEAD"
          fi
          exit "$rc"
        fi
        exec {real_git!r} "$@"
        """))
    wrapper.chmod(0o755)

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        if push_fetch_main_for_rebase; then
          echo "first inherited recovery unexpectedly succeeded" >&2
          exit 81
        fi
        test "$PUSH_RECOVERY_FAILED" -eq 1
        if push_attempt; then
          echo "failed recovery was forgotten by the next retry" >&2
          exit 82
        fi
        test "$PUSH_RECOVERY_FAILED" -eq 1
        case "$PUSH_STOP" in
          *"recovery failed"*) ;;
          *) echo "missing sticky recovery stop: $PUSH_STOP" >&2; exit 83 ;;
        esac
        """,
        env={
            "PATH": f"{fakebin}:{os.environ['PATH']}",
            "TOPIC_HEAD": topic_head,
            "MOVED_HEAD": moved_head,
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"


def test_inherited_cleanup_preserves_untracked_child_without_destructive_restore(tmp_path):
    """Cleanup-only quit must not reset away current-job untracked output."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    git_dir = _install_inherited_complete_rebase(repo, tmp_path)
    tracked = repo / "staged.txt"
    tracked.unlink()
    tracked.mkdir()
    child = tracked / "untracked-child.txt"
    child.write_text("current-job-untracked\n")
    before = _git_output(repo, "status", "--porcelain")
    assert "staged.txt" in before

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 1
        test "$PUSH_RECOVERY_FAILED" -eq 0
        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test -f staged.txt/untracked-child.txt
        test "$(cat staged.txt/untracked-child.txt)" = current-job-untracked
        test -z "$(git ls-files -u)"
        test ! -d "$GIT_DIR/rebase-merge"
        test ! -d "$GIT_DIR/rebase-apply"
        """,
        env={"TOPIC_HEAD": topic_head, "GIT_DIR": str(git_dir)},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert child.read_text() == "current-job-untracked\n"

def test_fetch_rebase_preserves_current_tracked_dirt_while_removing_inherited_state(tmp_path):
    """Inherited control metadata cannot erase the current job's staged/unstaged bytes."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    git_dir = _install_inherited_complete_rebase(repo, tmp_path)
    (repo / "staged.txt").write_text("current job staged\n")
    _git_output(repo, "add", "staged.txt")
    (repo / "unstaged.txt").write_text("current job unstaged\n")

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 1
        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test "$(cat staged.txt)" = "current job staged"
        test "$(cat unstaged.txt)" = "current job unstaged"
        test "$(git diff --cached --name-only)" = staged.txt
        test "$(git diff --name-only)" = unstaged.txt
        test -z "$(git ls-files -u)"
        test ! -d "$GIT_DIR/rebase-merge"
        test ! -d "$GIT_DIR/rebase-apply"
        """,
        env={"TOPIC_HEAD": topic_head, "GIT_DIR": str(git_dir)},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"



def test_inherited_autostash_is_never_applied_over_current_job_bytes(tmp_path):
    """A prior invocation's autostash may be retained as evidence, never applied as state."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    (repo / "staged.txt").write_text("prior invocation staged\n")
    _git_output(repo, "add", "staged.txt")
    (repo / "unstaged.txt").write_text("prior invocation unstaged\n")
    conflict = subprocess.run(
        ["git", "-C", str(repo), "rebase", "--autostash", "origin/main"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert conflict.returncode != 0
    git_dir = Path(_git_output(repo, "rev-parse", "--absolute-git-dir"))
    state = git_dir / "rebase-merge"
    assert (state / "autostash").is_file()
    saved = tmp_path / "inherited-autostash-rebase-merge"
    shutil.copytree(state, saved)
    _git_output(repo, "rebase", "--abort")
    _git_output(repo, "reset", "--hard", topic_head)
    shutil.copytree(saved, state)

    (repo / "staged.txt").write_text("current job staged\n")
    _git_output(repo, "add", "staged.txt")
    (repo / "unstaged.txt").write_text("current job unstaged\n")
    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test "$(cat staged.txt)" = "current job staged"
        test "$(cat unstaged.txt)" = "current job unstaged"
        test "$(git diff --cached --name-only)" = staged.txt
        test "$(git diff --name-only)" = unstaged.txt
        test -z "$(git ls-files -u)"
        test ! -d "$GIT_DIR/rebase-merge"
        """,
        env={"TOPIC_HEAD": topic_head, "GIT_DIR": str(git_dir)},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"

def test_fetch_rebase_refuses_inherited_detached_conflict_without_trusting_old_abort(tmp_path):
    """No current-job anchor means inherited detached/unmerged state stays fail-closed."""
    repo, _ = _current_attempt_conflict_repo(tmp_path)
    conflict = subprocess.run(
        ["git", "-C", str(repo), "rebase", "origin/main"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert conflict.returncode != 0
    pre_head = _git_output(repo, "rev-parse", "HEAD")
    pre_unmerged = _git_output(repo, "ls-files", "-u")
    assert pre_unmerged
    git_dir = Path(_git_output(repo, "rev-parse", "--absolute-git-dir"))

    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        if push_fetch_main_for_rebase; then
          echo "inherited partial rebase was accepted" >&2
          exit 72
        fi
        if push_abort_rebase; then
          echo "inherited rebase metadata was trusted by abort" >&2
          exit 73
        fi
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 0
        test "$(git rev-parse HEAD)" = "$PRE_HEAD"
        test -z "$(git symbolic-ref -q HEAD || true)"
        test "$(git ls-files -u)" = "$PRE_UNMERGED"
        test -d "$GIT_DIR/rebase-merge"
        """,
        env={
            "PRE_HEAD": pre_head,
            "PRE_UNMERGED": pre_unmerged,
            "GIT_DIR": str(git_dir),
        },
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"


def test_abort_rebase_restores_exact_current_attempt_after_malformed_real_conflict(tmp_path):
    """A damaged conflict created by THIS retry may recover from its pre-rebase anchor."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path)
    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 1
        git rebase --autostash origin/main >/tmp/push-retry-current-attempt-first.log 2>&1 || true
        gd=$(git rev-parse --git-dir)
        rm -f "$gd/rebase-merge/head-name" "$gd/rebase-merge/orig-head"
        push_abort_rebase

        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test -z "$(git ls-files -u)"
        test "$(cat file)" = topic
        test ! -d "$gd/rebase-merge"
        test ! -d "$gd/rebase-apply"

        rc=0
        out=$(git rebase origin/main 2>&1) || rc=$?
        test "$rc" -ne 0
        case "$out" in
          *"already a rebase-merge directory"*|*"index contains uncommitted changes"*|*"unstaged changes"*)
            echo "$out" >&2
            exit 71
            ;;
        esac
        test -d "$gd/rebase-merge"
        git rebase --abort
        """,
        env={"TOPIC_HEAD": topic_head},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"


def test_abort_rebase_current_attempt_anchor_restores_staged_and_unstaged_bytes(tmp_path):
    """Fallback uses this attempt's snapshot; an abandoned Git autostash is not authority."""
    repo, topic_head = _current_attempt_conflict_repo(tmp_path, dirty=True)
    r = run_sh(
        r"""
        push_retry_init "t"
        push_attempt
        push_fetch_main_for_rebase
        test "$PUSH_ATTEMPT_ANCHOR_VALID" -eq 1
        git rebase --autostash origin/main >/tmp/push-retry-current-attempt-dirty.log 2>&1 || true
        gd=$(git rev-parse --git-dir)
        rm -f "$gd/rebase-merge/head-name" "$gd/rebase-merge/orig-head"
        push_abort_rebase

        test "$(git symbolic-ref -q --short HEAD)" = topic
        test "$(git rev-parse HEAD)" = "$TOPIC_HEAD"
        test -z "$(git ls-files -u)"
        test "$(cat file)" = topic
        test "$(cat staged.txt)" = "current attempt staged"
        test "$(cat unstaged.txt)" = "current attempt unstaged"
        test "$(git diff --cached --name-only)" = staged.txt
        test "$(git diff --name-only)" = unstaged.txt
        test ! -d "$gd/rebase-merge"
        test ! -d "$gd/rebase-apply"
        git stash list >/dev/null
        """,
        env={"TOPIC_HEAD": topic_head},
        cwd=repo,
    )
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"


def test_metadata_only_push_attempt_does_not_capture_rebase_anchor(tmp_path):
    """Retry accounting alone must not scan/stash a dirty repository."""
    repo = tmp_path / "repo-metadata-only"
    _init_repo(repo)
    (repo / "a").write_text("base\n")
    _git_output(repo, "add", ".")
    _git_output(repo, "commit", "-m", "base")
    (repo / "a").write_text("dirty current output\n")

    log = tmp_path / "git-calls.log"
    fakebin = _logging_git(tmp_path, log)
    r = run_sh(
        'push_retry_init "metadata-only"; push_attempt; echo "anchor=$PUSH_ATTEMPT_ANCHOR_VALID"',
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    assert "anchor=0" in r.stdout
    calls = log.read_text().splitlines() if log.exists() else []
    assert "diff" not in calls, calls
    assert "stash" not in calls, calls
    assert "write-tree" not in calls, calls


# ---------------------------------------------------------------------------
# 5. Step summary — contention becomes visible instead of silent
# ---------------------------------------------------------------------------


def test_summary_reports_attempts_used_and_the_contention_census(tmp_path):
    summary = tmp_path / "summary.md"
    summary.touch()
    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "rendered site"
        for _ in 1 2 3; do push_attempt; PUSH_FAIL_CLASS=contention; push_backoff; done
        push_attempt
        push_won
        """,
        env={"GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert r.returncode == 0, r.stderr
    text = summary.read_text()
    assert "push-retry" in text and "rendered site" in text
    assert "attempts=4/10" in text
    assert "ref-lock losses=3" in text


def test_summary_is_quiet_on_a_clean_first_attempt_win(tmp_path):
    """20 loops across the lanes — a summary line per successful push would be noise."""
    summary = tmp_path / "summary.md"
    summary.touch()
    run_sh(
        'push_retry_init "t"; push_attempt; push_won',
        env={"GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert summary.read_text() == ""


def test_give_up_always_reports_why(tmp_path):
    summary = tmp_path / "summary.md"
    summary.touch()
    run_sh(
        """
        PUSH_MAX_ATTEMPTS=2
        push_retry_init "engine outputs"
        sleep() { :; }
        while push_attempt; do PUSH_FAIL_CLASS=contention; push_backoff; done
        push_lost
        """,
        env={"GITHUB_STEP_SUMMARY": str(summary)},
    )
    text = summary.read_text()
    assert "NOT pushed" in text and "attempt budget exhausted" in text


def test_give_up_is_silent_when_the_loop_left_on_a_win(tmp_path):
    """asia-close's data commit sits inside an if/else, so its loop exits with `break`
    and falls through to the give-up tail even after a successful push. push_lost must
    not claim a loss there."""
    summary = tmp_path / "summary.md"
    summary.touch()
    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "asia data"
        while push_attempt; do
          echo "pushed asia data (attempt $PUSH_ATTEMPT)"; push_won; break
        done
        push_lost
        """,
        env={"GITHUB_STEP_SUMMARY": str(summary)},
    )
    assert r.returncode == 0, r.stderr
    assert "pushed asia data (attempt 1)" in r.stdout
    assert "NOT pushed" not in summary.read_text(), summary.read_text()


def test_summary_is_a_no_op_outside_actions():
    """Sourcing the library locally (or in a test) must never blow up on a missing
    GITHUB_STEP_SUMMARY."""
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"}
    r = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", f'. "{LIB}"\npush_retry_init "t"; push_attempt; push_lost; echo done'],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, r.stderr
    assert "done" in r.stdout


# ---------------------------------------------------------------------------
# 6. End-to-end — a real lost race is WON on a later attempt, not thrown away
# ---------------------------------------------------------------------------


def test_real_race_against_a_moving_main_is_won_on_a_retry(tmp_path):
    """Two clones of one main, exactly the lanes' situation. Clone B commits, clone A
    lands first, so B's push is rejected non-fast-forward. Under the old loop that
    burned an attempt on the conflict remedy; here it must classify as contention and
    the very next rebase+push must land B's work.
    """
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)

    seed = tmp_path / "seed"
    _init_repo(seed)
    (seed / "base").write_text("base")
    subprocess.run(["git", "-C", str(seed), "add", "."], check=True)
    subprocess.run(["git", "-C", str(seed), "commit", "-qm", "seed"], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q", str(bare), "main"], check=True)

    def clone(name: str) -> Path:
        p = tmp_path / name
        subprocess.run(["git", "clone", "-q", str(bare), str(p)], check=True)
        subprocess.run(["git", "-C", str(p), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(p), "config", "user.name", "t"], check=True)
        return p

    a, b = clone("a"), clone("b")

    # B renders its work and commits it locally...
    (b / "rendered.txt").write_text("1121 locked rows")
    subprocess.run(["git", "-C", str(b), "add", "."], check=True)
    subprocess.run(["git", "-C", str(b), "commit", "-qm", "render: site re-render"], check=True)

    # ...and A lands on main first, so B's push is now stale.
    (a / "other.txt").write_text("marketing-publish outbox run")
    subprocess.run(["git", "-C", str(a), "add", "."], check=True)
    subprocess.run(["git", "-C", str(a), "commit", "-qm", "other lane"], check=True)
    subprocess.run(["git", "-C", str(a), "push", "-q", "origin", "main"], check=True)

    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "rendered site"
        while push_attempt; do
          git fetch origin main >/dev/null 2>&1 || true
          if git pull --rebase --autostash -X theirs origin main >/dev/null 2>&1; then
            if push_do; then echo "PUSHED on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
          fi
          push_abort_rebase
          push_backoff
        done
        push_lost
        echo "GAVE UP after $PUSH_ATTEMPT"
        exit 1
        """,
        cwd=b,
    )
    assert r.returncode == 0, f"the render was discarded:\n{r.stdout}\n{r.stderr}"
    assert "PUSHED on attempt 1" in r.stdout or "PUSHED on attempt 2" in r.stdout, r.stdout

    # both lanes' work is on main
    files = subprocess.run(
        ["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "main"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert "rendered.txt" in files, "the render never landed"
    assert "other.txt" in files, "the racing lane's commit was clobbered"


def test_repeated_ref_lock_losses_are_retried_far_past_the_old_five(tmp_path):
    """The 2026-07-25 replay: main rejects with a ref-lock loss over and over. The old
    loop gave up after 5; this one must keep going and still land the render."""
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    counter = tmp_path / "n"
    counter.write_text("0")
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
    (fakebin / "git").write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            if [ "$1" = "push" ]; then
              n=$(cat {counter}); n=$((n+1)); echo "$n" > {counter}
              if [ "$n" -le 7 ]; then
                echo "To github.com:user/repo.git" >&2
                echo " ! [remote rejected] main -> main (cannot lock ref 'refs/heads/main': is at aaa but expected bbb)" >&2
                exit 1
              fi
              echo "pushed for real"; exit 0
            fi
            exec {real_git} "$@"
            """
        )
    )
    (fakebin / "git").chmod(0o755)

    r = run_sh(
        """
        sleep() { :; }
        push_retry_init "rendered site"
        while push_attempt; do
          if push_do; then echo "PUSHED on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
          push_abort_rebase
          push_backoff
        done
        push_lost
        echo "GAVE UP after $PUSH_ATTEMPT"; exit 1
        """,
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=tmp_path,
    )
    assert r.returncode == 0, f"gave up on a pure ref-lock race:\n{r.stdout}"
    assert "PUSHED on attempt 8" in r.stdout, r.stdout
    assert "[contention]" in r.stdout
    assert "[rebase-conflict]" not in r.stdout, "a ref-lock loss was miscalled a conflict"


# ---------------------------------------------------------------------------
# 7. PUSH_ALARM — 15 of the 21 loops alarm-bound their push
# ---------------------------------------------------------------------------


def _fake_git(tmp_path: Path, push_body: str) -> Path:
    """A `git` earlier on PATH whose `push` runs push_body; everything else is real."""
    fakebin = tmp_path / "bin"
    fakebin.mkdir(exist_ok=True)
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
    (fakebin / "git").write_text(
        f'#!/usr/bin/env bash\nif [ "$1" = "push" ]; then\n{push_body}\nfi\nexec {real_git} "$@"\n'
    )
    (fakebin / "git").chmod(0o755)
    return fakebin


def test_alarm_bounded_push_still_pushes(tmp_path):
    """daily.yml (×14) and closing-bell set PUSH_ALARM=420 because macOS runners have no
    GNU timeout. If the perl wrapper were malformed, every one of those pushes would
    break — so pin the happy path, not just the timeout."""
    fakebin = _fake_git(tmp_path, '  echo "PUSHED args=[$*]"; exit 0')
    r = run_sh(
        """
        PUSH_ALARM=420
        push_retry_init "alarm"
        push_attempt
        if push_do; then echo "OK class=[$PUSH_FAIL_CLASS]"; else echo "BROKEN rc=$?"; fi
        """,
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert "PUSHED args=[push]" in r.stdout, r.stdout
    assert "OK class=[]" in r.stdout, r.stdout


def test_alarm_actually_kills_a_hung_push_and_classifies_it(tmp_path):
    """The 2026-07-17 incident behind the alarm: a hung push ate 57 minutes. The alarm
    must fire, and a SIGALRM kill must not be miscalled a race."""
    fakebin = _fake_git(tmp_path, "  sleep 30")
    r = run_sh(
        """
        PUSH_ALARM=1
        push_retry_init "alarm"
        push_attempt
        if push_do; then echo "NOT KILLED"; else echo "killed class=$PUSH_FAIL_CLASS"; fi
        """,
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=tmp_path,
    )
    assert "killed class=push-timeout" in r.stdout, r.stdout


def test_push_do_passes_extra_args_through(tmp_path):
    fakebin = _fake_git(tmp_path, '  echo "ARGS=[$*]"; exit 0')
    r = run_sh(
        'push_retry_init "t"; push_attempt; push_do origin HEAD:main',
        env={"PATH": f"{fakebin}:{os.environ['PATH']}"},
        cwd=tmp_path,
    )
    assert "ARGS=[push origin HEAD:main]" in r.stdout, r.stdout


# ---------------------------------------------------------------------------
# 8. End-to-end — render.yml's REAL run: block, executed against real git repos
#
# The rest of this file proves the library and the lane FILE CONTENTS. Neither
# catches a lane whose surrounding shell mis-wires the policy — a stray `fi`, a
# push_won that never runs, a give-up path that swallows the error. So run the
# shipped block itself, verbatim, with the python guards stubbed and the GitHub
# ${{ }} expressions substituted.
# ---------------------------------------------------------------------------

RENDER_STEP = "commit rendered site (site/ ONLY — never data/, so ledgers stay pristine)"


def _lane_block(lane: str, step_name: str, subs: dict) -> str:
    doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / lane).read_text())
    for job in doc["jobs"].values():
        for s in job.get("steps") or []:
            if s.get("name") == step_name:
                body = s["run"]
                return re.sub(r"\$\{\{([^}]*)\}\}", lambda m: subs.get(m.group(1).strip(), ""), body)
    raise AssertionError(f"{lane}: step {step_name!r} not found")


def _lane_fixture(tmp_path: Path, rejects: int = 0, collision: bool = False):
    """A bare origin + a lane clone holding a fresh render + a racing lane that has
    already landed on main, so the lane's first push is stale."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)

    def git(repo, *a):
        return subprocess.run(["git", "-C", str(repo), *a], check=True,
                              capture_output=True, text=True)

    seed = tmp_path / "seed"
    _init_repo(seed)
    (seed / "site").mkdir()
    (seed / "site" / "index.html").write_text("<html>old</html>")
    if collision:
        (seed / "site" / "upstream.html").write_text("<html>upstream old</html>")
    (seed / "data").mkdir()
    (seed / "data" / "ledger.json").write_text('{"canonical": true}')
    git(seed, "add", "."); git(seed, "commit", "-qm", "seed")
    git(seed, "push", "-q", str(bare), "main")

    lane = tmp_path / "lane"
    subprocess.run(["git", "clone", "-q", str(bare), str(lane)], check=True)
    git(lane, "config", "user.email", "t@t"); git(lane, "config", "user.name", "t")
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True)
    git(other, "config", "user.email", "t@t"); git(other, "config", "user.name", "t")

    # the render this run must not lose
    (lane / "site" / "index.html").write_text("<html>FRESH RENDER</html>")
    (lane / "site" / "premiumdata").mkdir(parents=True, exist_ok=True)
    (lane / "site" / "premiumdata" / "special_situations.json").write_text('{"rows": 1121}')
    # a tracked dirty ledger write — the step commits site/ ONLY, and the rebase must
    # preserve it through autostash without ever staging it.
    (lane / "data" / "ledger.json").write_text('{"lane": "throwaway"}')
    collision_paths = (
        "data/news_translation/cache/6f6c96a40e19f66dde08026f960ff729b5aeef1a.json",
        "data/news_translation/cache/name with spaces.json",
    )
    if collision:
        for path in collision_paths:
            target = lane / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"render-local:{path}")

    # a racing lane lands on main first
    (other / "other.txt").write_text("marketing-publish outbox run")
    if collision:
        (other / "site" / "upstream.html").write_text("<html>upstream newer</html>")
        for path in collision_paths:
            target = other / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"main-authoritative:{path}")
    git(other, "add", "."); git(other, "commit", "-qm", "other lane")
    git(other, "push", "-q", "origin", "main")

    stub = tmp_path / "bin"
    stub.mkdir()
    for name in ("python", "python3"):
        (stub / name).write_text('#!/usr/bin/env bash\nexit 0\n')
        (stub / name).chmod(0o755)
    if rejects:
        counter = tmp_path / "n"
        counter.write_text("0")
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        (stub / "git").write_text(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            if [ "$1" = "push" ]; then
              n=$(cat {counter}); n=$((n+1)); echo "$n" > {counter}
              if [ "$n" -le {rejects} ]; then
                echo " ! [remote rejected] main -> main (cannot lock ref 'refs/heads/main': is at aaa but expected bbb)" >&2
                exit 1
              fi
            fi
            exec {real_git} "$@"
            """))
        (stub / "git").chmod(0o755)
    return bare, lane, stub, collision_paths


def _run_lane(
    block: str,
    lane: Path,
    stub: Path,
    summary: Path,
    render_ok: bool,
    admin_token: str | None = "test-admin-token",
):
    runner_temp = summary.parent / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    env = {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}",
           "GITHUB_WORKSPACE": str(REPO_ROOT), "GITHUB_STEP_SUMMARY": str(summary),
           "GITHUB_ACTIONS": "true",
           "RUNNER_TEMP": str(runner_temp), "GITHUB_RUN_ID": "123",
           "GITHUB_RUN_ATTEMPT": "1"}
    if admin_token:
        env["ADMIN_GH_TOKEN"] = admin_token
    else:
        env.pop("ADMIN_GH_TOKEN", None)
    if render_ok:
        env["RENDER_OK"] = "1"
    else:
        env.pop("RENDER_OK", None)
    # no real sleeping: the backoff ladder is unit-tested above
    return subprocess.run(["bash", "-eo", "pipefail", "-c", "sleep() { :; }\n" + block],
                          cwd=str(lane), capture_output=True, text=True, env=env)


@pytest.mark.parametrize("rejects, expected_attempts, succeeds", [(0, 1, True), (1, 2, True), (5, 2, False)])
def test_options_intel_publication_result(tmp_path, rejects, expected_attempts, succeeds):
    """Execute the shipped shell: an unpublished brief must not produce a green job."""
    block = _lane_block(
        "options-intel.yml", "commit the options intelligence brief + workspace", {}
    )
    bare, lane, stub, _ = _lane_fixture(tmp_path, rejects=rejects)
    brief = '{"as_of_session": "2026-10-14"}'
    (lane / "site/options_intel_brief.json").write_text(brief)
    (lane / "site/options.html").write_text("<html>fresh options workspace</html>")
    before = _git_output(bare, "rev-parse", "main")
    summary = tmp_path / "summary.md"
    summary.touch()
    # The shared retry helper and actual fetch/rebase/push remain in use. Only
    # contention and Python publication preflights use the existing fixture seams.
    r = _run_lane("PUSH_MAX_ATTEMPTS=2\n" + block, lane, stub, summary, render_ok=True)
    output = r.stdout + r.stderr
    assert (r.returncode == 0) is succeeds, output
    if rejects:
        assert int((tmp_path / "n").read_text()) == expected_attempts
    if succeeds:
        assert f"pushed options intelligence brief on attempt {expected_attempts}" in output
        assert _git_output(bare, "show", "main:site/options_intel_brief.json") == brief
        assert _git_output(bare, "show", "main:site/options.html") == "<html>fresh options workspace</html>"
        assert "other.txt" in _git_output(bare, "ls-tree", "--name-only", "main")
    else:
        assert "::error title=options intelligence brief NOT pushed::" in output
        assert "attempt budget exhausted (2 attempts)" in output
        assert "NOT pushed" in summary.read_text()
        assert _git_output(bare, "rev-parse", "main") == before
    assert _git_output(bare, "show", "main:data/ledger.json") == '{"canonical": true}'


def test_options_intel_semantic_noop_does_not_push(tmp_path):
    block = _lane_block(
        "options-intel.yml", "commit the options intelligence brief + workspace", {}
    )
    bare, lane, stub, _ = _lane_fixture(tmp_path, rejects=5)
    (lane / "site/options_intel_brief.json").write_text("{}")
    (lane / "site/options.html").write_text("<html>unchanged</html>")
    _git_output(lane, "add", "site/options_intel_brief.json", "site/options.html")
    _git_output(lane, "commit", "-m", "fixture already contains brief")
    before = _git_output(bare, "rev-parse", "main")
    summary = tmp_path / "summary.md"
    summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "semantic no-op" in r.stdout
    assert (tmp_path / "n").read_text() == "0"
    assert _git_output(bare, "rev-parse", "main") == before


def test_render_lane_block_lands_the_render_over_a_racing_commit(tmp_path):
    block = _lane_block("render.yml", RENDER_STEP,
                        {"steps.pick.outputs.scope": "all",
                         "steps.pick.outputs.rendered_from": "deadbeef"})
    bare, lane, stub, _ = _lane_fixture(tmp_path)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"

    files = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "main"],
                           capture_output=True, text=True, check=True).stdout.split()
    log = subprocess.run(["git", "-C", str(bare), "log", "--oneline", "-5", "main"],
                         capture_output=True, text=True, check=True).stdout

    assert "site/premiumdata/special_situations.json" in files, "the render never landed"
    assert "other.txt" in files, "the racing lane's commit was clobbered"
    assert _git_output(bare, "show", "main:data/ledger.json") == '{"canonical": true}', (
        "the step committed its dirty ledger write — only the pre-existing canonical data may remain"
    )
    assert "from=deadbeef" in log, "RENDER_OK=1 run did not stamp the from= watermark"
    assert summary.read_text() == ""
    extraheader = subprocess.run(
        ["git", "-C", str(lane), "config", "--local", "--get",
         "http.https://github.com/.extraheader"],
        capture_output=True, text=True,
    )
    assert extraheader.returncode != 0, extraheader.stdout + extraheader.stderr


def test_render_lane_fails_closed_without_admin_token(tmp_path):
    """Protected main cannot be published with an empty admin PAT; do not fall back."""
    block = _lane_block("render.yml", RENDER_STEP,
                        {"steps.pick.outputs.scope": "all",
                         "steps.pick.outputs.rendered_from": "deadbeef"})
    bare, lane, stub, _ = _lane_fixture(tmp_path)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True, admin_token=None)
    assert r.returncode == 1, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "ADMIN_GH_TOKEN is required to publish through the main freeze" in combined
    log = subprocess.run(
        ["git", "-C", str(bare), "log", "--oneline", "-5", "main"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "render:" not in log
    extraheader = subprocess.run(
        ["git", "-C", str(lane), "config", "--local", "--get",
         "http.https://github.com/.extraheader"],
        capture_output=True, text=True,
    )
    assert extraheader.returncode != 0, extraheader.stdout + extraheader.stderr


def test_render_lane_fails_immediately_on_ruleset_denial(tmp_path):
    """GH013 is a deterministic identity rejection, not contention. Do not retry 20 times."""
    block = _lane_block("render.yml", RENDER_STEP,
                        {"steps.pick.outputs.scope": "all",
                         "steps.pick.outputs.rendered_from": "deadbeef"})
    bare, lane, stub, _ = _lane_fixture(tmp_path)
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
    (stub / "git").write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        if [ "$1" = "push" ]; then
          echo "remote: error: GH013: Repository rule violations found for refs/heads/main." >&2
          echo " ! [remote rejected] main -> main (push declined due to repository rule violations)" >&2
          exit 1
        fi
        exec {real_git} "$@"
        """))
    (stub / "git").chmod(0o755)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True)
    assert r.returncode == 1, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "typically GH013 repository rules" in combined
    assert "attempt 2/" not in combined
    extraheader = subprocess.run(
        ["git", "-C", str(lane), "config", "--local", "--get",
         "http.https://github.com/.extraheader"],
        capture_output=True, text=True,
    )
    assert extraheader.returncode != 0, extraheader.stdout + extraheader.stderr


def test_render_lane_block_survives_seven_ref_lock_losses(tmp_path):
    """The 2026-07-25 incident, replayed against the shipped lane shell. The old loop
    gave up at 5 and discarded ~95 minutes of render."""
    block = _lane_block("render.yml", RENDER_STEP,
                        {"steps.pick.outputs.scope": "all",
                         "steps.pick.outputs.rendered_from": "deadbeef"})
    bare, lane, stub, _ = _lane_fixture(tmp_path, rejects=7)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "pushed rendered site on attempt 8" in r.stdout, r.stdout
    assert "[contention]" in r.stdout
    assert "[rebase-conflict]" not in r.stdout, "a ref-lock loss was miscalled a conflict"

    files = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "main"],
                           capture_output=True, text=True, check=True).stdout.split()
    assert "site/premiumdata/special_situations.json" in files, "the render was discarded"

    text = summary.read_text()
    assert "attempts=8/20" in text and "ref-lock losses=7" in text, text
    assert "rebase conflicts=0" in text, text


def test_render_lane_quarantines_exact_untracked_collisions_before_porcelain_rebase(tmp_path):
    """Regression for run 30727439896: fetched main must be the tree both the
    quarantine and rebase use.  Two generated files (including a space) move to
    RUNNER_TEMP, current main wins, the render lands, and a dirty ledger stays
    local/unstaged."""
    block = _lane_block("render.yml", RENDER_STEP,
                        {"steps.pick.outputs.scope": "all",
                         "steps.pick.outputs.rendered_from": "deadbeef"})
    bare, lane, stub, collision_paths = _lane_fixture(tmp_path, collision=True)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_lane(block, lane, stub, summary, render_ok=True)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert "untracked checkout collision quarantined" in r.stdout

    for path in collision_paths:
        remote = _git_output(bare, "show", f"main:{path}")
        assert remote == f"main-authoritative:{path}"
        assert (lane / path).read_text() == f"main-authoritative:{path}"
    quarantines = list((tmp_path / "runner-temp").glob("push-untracked-collision.*"))
    assert len(quarantines) == 1
    for path in collision_paths:
        assert (quarantines[0] / "files" / path).read_text() == f"render-local:{path}"
    assert (quarantines[0] / "paths.nul").read_bytes() == (
        "\0".join(collision_paths).encode() + b"\0"
    )

    assert _git_output(bare, "show", "main:data/ledger.json") == '{"canonical": true}'
    assert (lane / "data" / "ledger.json").read_text() == '{"lane": "throwaway"}'
    assert _git_output(lane, "diff", "--cached", "--name-only") == ""
    assert _git_output(lane, "status", "--porcelain") == "M data/ledger.json"
    assert _git_output(bare, "show", "main:site/index.html") == "<html>FRESH RENDER</html>"


def test_render_lane_never_invokes_publish_on_a_partial_render():
    """A cancelled, timed-out, or guard-failed render must keep last-good main live."""
    doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "render.yml").read_text())
    steps = doc["jobs"]["render"]["steps"]
    publish = next(step for step in steps if step.get("name") == RENDER_STEP)

    assert publish["if"] == "${{ success() && steps.render_pages.outputs.complete == 'true' }}"
    assert "(scope=$SCOPE, from=$FROM)" in publish["run"]
    assert '(scope=$SCOPE)"' not in publish["run"]


# ---------------------------------------------------------------------------
# 9. The lanes actually use it
# ---------------------------------------------------------------------------

LANES = [
    "render.yml",
    "engine-render.yml",
    "daily.yml",
    "closing-bell.yml",
    "asia-close.yml",
    "weekly.yml",
    "earlyclose.yml",
]


def test_no_lane_still_carries_the_old_five_attempt_ladder():
    stale = []
    for lane in LANES:
        text = (REPO_ROOT / ".github" / "workflows" / lane).read_text()
        for pattern in ("for i in 1 2 3 4 5", "sleep $((i * 7))"):
            if pattern in text:
                stale.append(f"{lane}: {pattern}")
    assert not stale, "lanes still on the old deterministic ladder: " + ", ".join(stale)


def test_a_raised_time_budget_is_never_decorative():
    """A lane that raises PUSH_BUDGET_SECS must raise PUSH_MAX_ATTEMPTS with it.

    Measured 2026-07-25 against render.yml's real run block: ten contention retries
    spend only ~2 min of backoff, so the default attempt cap stops the loop with most
    of a raised 600s budget untouched — the budget reads as "we'll wait 10 minutes for
    the ref" while the loop actually gives up in two. On these lanes the DEADLINE is
    meant to be the governor; the attempt count is not doing the safety work.
    """
    for lane in LANES:
        text = (REPO_ROOT / ".github" / "workflows" / lane).read_text()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not re.match(r"\s*PUSH_BUDGET_SECS=(\d+)", line):
                continue
            budget = int(re.match(r"\s*PUSH_BUDGET_SECS=(\d+)", line).group(1))
            if budget <= 420:
                continue
            window = "\n".join(lines[max(0, i - 4): i + 6])
            m = re.search(r"PUSH_MAX_ATTEMPTS=(\d+)", window)
            assert m, (
                f"{lane}:{i + 1} raises PUSH_BUDGET_SECS to {budget} but leaves the "
                f"attempt cap at the default — the extra budget can never be spent"
            )
            assert int(m.group(1)) > 10, (
                f"{lane}:{i + 1} raises the budget to {budget} but caps attempts at "
                f"{m.group(1)}"
            )


def test_every_lane_loop_sources_the_shared_policy():
    for lane in LANES:
        text = (REPO_ROOT / ".github" / "workflows" / lane).read_text()
        n_loops = text.count("while push_attempt")
        assert n_loops, f"{lane} carries no push_attempt loop"
        assert text.count("push_retry_init") == n_loops, f"{lane}: init/loop count mismatch"
        assert text.count('scripts/ci/push_retry.sh"') >= 1, f"{lane} never sources the policy"


# ---------------------------------------------------------------------------
# 10. push_on_main_ok — never publish a dispatch ref to main
#
# 2026-08-02: every lane below ends its commit step with some form of
# `git push origin HEAD:main`, and every one of them also carries
# workflow_dispatch, which accepts ANY ref. Dispatching seo-director on
# claude/gsc-index-diagnostics to read its GSC diagnostics would therefore have
# rebased that branch onto main and PUSHED IT TO MAIN — unreviewed commits
# landing with no PR, no review and no CI, under a green audit run.
#
# The guard tests the CHECKED-OUT ref, never `github.ref`, because the two come
# apart in both directions: government-revenue-live.yml pins `ref: main` (safe
# on any trigger ref), while metabolism-{propose,adjudicate,build}.yml are
# DESIGNED to be dispatched over a propose branch and re-anchor onto
# _journal_main before publishing their journal snapshot.
# ---------------------------------------------------------------------------


def _repo_on_branch(tmp_path: Path, branch: str) -> Path:
    repo = tmp_path / f"repo-{branch.replace('/', '-')}"
    repo.mkdir()
    _init_repo(repo)
    (repo / "f.txt").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "c0"], check=True)
    if branch != "main":
        subprocess.run(["git", "-C", str(repo), "checkout", "-qb", branch], check=True)
    return repo


def test_guard_allows_a_run_on_main(tmp_path):
    repo = _repo_on_branch(tmp_path, "main")
    r = run_sh("push_on_main_ok && echo ALLOWED", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "ALLOWED" in r.stdout
    assert "::notice" not in r.stdout, "a run on main must stand down silently"


def test_guard_refuses_the_dispatch_branch_that_found_this(tmp_path):
    """The exact 2026-08-02 case: seo-director dispatched on a diagnostics branch."""
    repo = _repo_on_branch(tmp_path, "claude/gsc-index-diagnostics")
    r = run_sh(
        'PUSH_LABEL="seo-director"\n'
        "if push_on_main_ok; then echo PUSHED; else echo WITHHELD; fi",
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    assert "WITHHELD" in r.stdout and "PUSHED" not in r.stdout
    assert "claude/gsc-index-diagnostics" in r.stdout, "the notice must name the ref it refused"


def test_guard_notice_starts_the_line_and_is_plain_word(tmp_path):
    """GitHub drops an annotation that does not START the line (repo law, #3587)."""
    repo = _repo_on_branch(tmp_path, "feature/x")
    r = run_sh("push_on_main_ok || true", cwd=repo)
    notices = [ln for ln in r.stdout.splitlines() if "::notice" in ln]
    assert len(notices) == 1, f"expected exactly one annotation, got {notices}"
    assert notices[0].startswith("::notice"), (
        f"annotation must start the line or GitHub silently drops it: {notices[0]!r}"
    )
    # The operator has to be able to tell "withheld" from "crashed".
    low = notices[0].lower()
    assert "not" in low and "push" in low


@pytest.mark.parametrize("state", ["detached", "not-a-repo"])
def test_guard_fails_closed_when_head_is_unreadable(tmp_path, state):
    """Fail-closed: anything the guard cannot positively identify as main is refused."""
    if state == "detached":
        repo = _repo_on_branch(tmp_path, "main")
        sha = _git_output(repo, "rev-parse", "HEAD")
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--detach", sha], check=True)
    else:
        repo = tmp_path / "bare-dir"
        repo.mkdir()
    r = run_sh("if push_on_main_ok; then echo PUSHED; else echo WITHHELD; fi", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "WITHHELD" in r.stdout, f"{state} must not be treated as main"


def test_re_anchor_lanes_accept_only_the_re_anchor_branch(tmp_path):
    """metabolism-{propose,adjudicate,build} publish from _journal_main, not main.

    Their `git checkout -B _journal_main origin/main` is suffixed `|| true`, so a
    FAILED re-anchor used to leave HEAD on metabolism/propose-<id> and push the
    whole unreviewed proposal to main. Naming the re-anchor branch as the only
    acceptable publish target makes that failure fail closed.
    """
    ok = _repo_on_branch(tmp_path, "_journal_main")
    r = run_sh('PUSH_MAIN_BRANCHES="_journal_main"; push_on_main_ok && echo ALLOWED', cwd=ok)
    assert r.returncode == 0 and "ALLOWED" in r.stdout, r.stderr

    # The re-anchor did not happen — HEAD is still the propose branch.
    bad = _repo_on_branch(tmp_path, "metabolism/propose-c42")
    r = run_sh(
        'PUSH_MAIN_BRANCHES="_journal_main"\n'
        "if push_on_main_ok; then echo PUSHED; else echo WITHHELD; fi",
        cwd=bad,
    )
    assert "WITHHELD" in r.stdout, "a failed re-anchor must never publish the propose branch"


# ---------------------------------------------------------------------------
# 10b. Workflow wiring — DERIVED, so a NEW lane that publishes to main is caught
#      too. Nothing here is an allow-list of known-good files.
# ---------------------------------------------------------------------------

WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

# `git push origin HEAD:main` / `push_do origin HEAD:main`: publishes whatever
# HEAD happens to be, which on a workflow_dispatch is whatever ref was chosen.
_PUBLISH_HEAD_RE = re.compile(r"(?:git push|push_do)\s+[^\n;&|]*\bHEAD:(?:main|refs/heads/main)\b")
# `push_do origin "$REF:refs/heads/main"`: publishes a named ref to main.
_PUBLISH_REF_RE = re.compile(r"(?:git push|push_do)\s+[^\n;&|]*:refs/heads/main\b")


def _shell_code(run: str) -> str:
    """Drop whole-line shell comments.

    These blocks carry long prose rationales that quote the very command they are
    explaining, so matching raw text finds pushes inside comments and mis-orders
    the guard against them. A commented-out push is not a push.
    """
    return "\n".join("" if ln.lstrip().startswith("#") else ln for ln in run.splitlines())


def _publishing_steps():
    """Yield (workflow, job, step_name, code, triggers) for every step that writes main."""
    for wf in sorted(WORKFLOW_DIR.glob("*.yml")):
        doc = yaml.safe_load(wf.read_text())
        triggers = doc.get(True) or doc.get("on") or {}
        triggers = set(triggers) if isinstance(triggers, (dict, list)) else {triggers}
        for job_name, job in (doc.get("jobs") or {}).items():
            for step in (job.get("steps") or []):
                code = _shell_code(step.get("run") or "")
                if _PUBLISH_HEAD_RE.search(code) or _PUBLISH_REF_RE.search(code):
                    yield wf.name, job_name, step.get("name", "?"), code, triggers


def test_the_estate_still_has_publishing_steps_to_check():
    """Fail-closed: a broken detector must not read as a clean audit."""
    found = list(_publishing_steps())
    assert len(found) >= 18, f"detector found only {len(found)} publishing steps — it is broken"


def test_every_head_to_main_push_is_guarded_first():
    """A step that publishes HEAD to main must call push_on_main_ok BEFORE it.

    This is the mutation-check anchor: delete the guard from any lane's commit
    step (or from scripts/ci/push_retry.sh) and this goes red.
    """
    unguarded = []
    for wf, job, step_name, run, _triggers in _publishing_steps():
        m = _PUBLISH_HEAD_RE.search(run)
        if not m:
            continue
        guard = run.find("push_on_main_ok")
        if guard == -1:
            unguarded.append(f"{wf} :: {job}/{step_name} — never calls push_on_main_ok")
        elif guard > m.start():
            unguarded.append(f"{wf} :: {job}/{step_name} — guard runs AFTER the push")
    assert not unguarded, (
        "these steps push HEAD to refs/heads/main from whatever ref the run was "
        "dispatched on, landing unreviewed commits with no PR and no CI:\n  "
        + "\n  ".join(unguarded)
    )


def test_named_ref_publishes_are_replay_built_or_guarded():
    """`push_do origin "$REF:refs/heads/main"` must not publish the dispatch branch.

    render.yml and daily.yml publish a ref built by push_metadata_replay_commit:
    the commit is parented on origin/main and carries only that lane's own path
    diff, so it structurally cannot smuggle a feature branch's commits onto main.
    Any OTHER named-ref publish must carry the explicit guard instead.
    """
    bad = []
    for wf, job, step_name, run, _triggers in _publishing_steps():
        if not _PUBLISH_REF_RE.search(run) or _PUBLISH_HEAD_RE.search(run):
            continue
        if "push_metadata_replay_commit" in run or "push_on_main_ok" in run:
            continue
        bad.append(f"{wf} :: {job}/{step_name}")
    assert not bad, (
        "these steps push a named ref to refs/heads/main without either the "
        "origin/main-parented metadata replay or push_on_main_ok:\n  " + "\n  ".join(bad)
    )


def test_the_guard_is_not_wired_as_a_github_ref_check():
    """A `github.ref` guard would be the WRONG fix and would break two lane families.

    government-revenue-live.yml pins `ref: main` at checkout (safe on any trigger
    ref), and metabolism-{propose,adjudicate,build}.yml are dispatched over a
    propose branch on purpose. Both are correct today precisely because the guard
    reads the checked-out ref instead.
    """
    for wf, job, step_name, run, _t in _publishing_steps():
        assert "github.ref" not in run, (
            f"{wf} :: {job}/{step_name} guards the publish on github.ref; the "
            f"checked-out ref is the one that gets pushed and the two differ here"
        )


_REANCHOR_RE = re.compile(r"git checkout -B (\S+) origin/main")


def test_re_anchoring_lanes_declare_their_publish_target():
    """A lane that re-anchors onto origin/main must NAME that branch as the target.

    The quiet half of this guard. metabolism-{propose,adjudicate,build} publish
    from _journal_main, so if the PUSH_MAIN_BRANCHES declaration is ever dropped
    the allow-list falls back to "main", the re-anchored HEAD never matches, and
    the step stands down on EVERY run — safe, silent, and permanently dark, while
    publishing that journal to main is the entire reason the step exists. Caught
    by mutation-checking the guard: removing the declaration left the suite green.
    """
    missing, checked = [], 0
    for wf, job, step_name, code, _t in _publishing_steps():
        m = _REANCHOR_RE.search(code)
        if not m:
            continue
        checked += 1
        branch = m.group(1)
        decl = re.search(r'PUSH_MAIN_BRANCHES="?([^"\n]+)"?', code)
        if not decl:
            missing.append(f"{wf} :: {job}/{step_name} re-anchors onto {branch} but declares no PUSH_MAIN_BRANCHES")
        elif branch not in decl.group(1).split():
            missing.append(
                f"{wf} :: {job}/{step_name} re-anchors onto {branch} but allows only "
                f"'{decl.group(1)}' — the step can never publish"
            )
    assert not missing, "re-anchored lanes that can never publish:\n  " + "\n  ".join(missing)
    # Fail-closed: a broken detector must not read as a clean audit.
    assert checked >= 3, f"expected the 3 metabolism journal lanes, detected {checked}"


# ---------------------------------------------------------------------------
# 9. backfill.yml — the staging gap that made a silent no-publish look GREEN
#
# Measured 2026-08-19, runs 32227070347 and 32227948390 (both `only=symbol_directory`):
# the step staged `data/` only, but a --full-history collect also rewrites three TRACKED
# files OUTSIDE data/ — docs/CLAIM_ACCOUNTABILITY.md, docs/GRADING_CLOSURE.md and
# site/qledger/track_record.json. All five `git pull --rebase -X theirs origin main`
# attempts died on
#
#     error: cannot pull with rebase: You have unstaged changes.
#
# and the loop ended on a ::warning + exit 0, so the job concluded SUCCESS while
# publishing nothing and the 19-file commit stayed on the runner. Same sentinel
# staging-gap that lost daily's 07-03/07-04 collections; daily was fixed, backfill was not.
# ---------------------------------------------------------------------------

BACKFILL_STEP = "commit"


def _backfill_commit_step() -> dict:
    doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "backfill.yml").read_text())
    return next(
        s for s in doc["jobs"]["backfill"]["steps"] if s.get("name") == BACKFILL_STEP
    )


def test_backfill_lane_stages_qledger_and_autostashes_the_rest():
    run = _backfill_commit_step()["run"]
    assert "git add data/ site/qledger/" in run, (
        "the qledger grader rewrites the tracked site/qledger/track_record.json on every "
        "collect — staging data/ alone strands it and blocks the rebase"
    )
    loop = run[run.index('push_retry_init "backfill data"') :]
    assert "while push_attempt; do" in loop
    assert "git pull --rebase --autostash -X theirs origin main" in loop, (
        "--autostash is the durable half: collect also rewrites docs/CLAIM_ACCOUNTABILITY.md "
        "and docs/GRADING_CLOSURE.md, which no lane stages"
    )
    # the conflicted-autostash containment must guard the success branch (#4167)
    assert "&& push_autostash_ok" in loop
    # the fence must survive, and must still run between the fetch and the rebase
    assert "push_append_only_fence origin/main" in loop
    assert loop.index("push_append_only_fence") < loop.index("git pull --rebase")
    assert "push_do" in loop and "push_abort_rebase" in loop and "push_backoff" in loop


def test_backfill_push_loss_is_red_not_a_warning():
    """A backfill that publishes nothing must not conclude SUCCESS."""
    run = _backfill_commit_step()["run"]
    tail = run[run.index("push_lost") :]
    assert "::error title=backfill NOT pushed" in tail
    assert "::warning::could not push backfill" not in run
    assert tail.rstrip().endswith("exit 1")


def _backfill_fixture(tmp_path: Path, always_reject: bool = False):
    """A bare origin + a lane clone holding a fresh backfill collection, the three
    tracked non-data/ files the collect step rewrites, and a racing commit on main."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)

    def git(repo, *a):
        return subprocess.run(["git", "-C", str(repo), *a], check=True,
                              capture_output=True, text=True)

    seed = tmp_path / "seed"
    _init_repo(seed)
    for rel, body in (
        ("data/symbol_directory/directory.json", '{"rows": 1}'),
        ("data/government_revenue/receipts.jsonl", '{"id": "nightly-1"}\n'),
        ("docs/CLAIM_ACCOUNTABILITY.md", "# committed accountability\n"),
        ("docs/GRADING_CLOSURE.md", "# committed closure\n"),
        ("site/qledger/track_record.json", '{"as_of": "old"}'),
    ):
        target = seed / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    git(seed, "add", "."); git(seed, "commit", "-qm", "seed")
    git(seed, "push", "-q", str(bare), "main")

    lane = tmp_path / "lane"
    subprocess.run(["git", "clone", "-q", str(bare), str(lane)], check=True)
    git(lane, "config", "user.email", "t@t"); git(lane, "config", "user.name", "t")

    # what the --full-history collect wrote: the data this run exists to publish ...
    (lane / "data" / "symbol_directory" / "directory.json").write_text('{"rows": 4213}')
    # ... plus the three tracked side-effects outside data/ that wedged the rebase.
    (lane / "docs" / "CLAIM_ACCOUNTABILITY.md").write_text("# regenerated accountability\n")
    (lane / "docs" / "GRADING_CLOSURE.md").write_text("# regenerated closure\n")
    (lane / "site" / "qledger" / "track_record.json").write_text('{"as_of": "fresh"}')

    # a racing lane lands on main first, so the first push is stale
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True)
    git(other, "config", "user.email", "t@t"); git(other, "config", "user.name", "t")
    (other / "other.txt").write_text("marketing-publish outbox run")
    git(other, "add", "."); git(other, "commit", "-qm", "other lane")
    git(other, "push", "-q", "origin", "main")

    stub = tmp_path / "bin"
    stub.mkdir()
    for name in ("python", "python3"):
        (stub / name).write_text("#!/usr/bin/env bash\nexit 0\n")
        (stub / name).chmod(0o755)
    if always_reject:
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        (stub / "git").write_text(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            if [ "$1" = "push" ]; then
              echo " ! [remote rejected] main -> main (cannot lock ref 'refs/heads/main')" >&2
              exit 1
            fi
            exec {real_git} "$@"
            """))
        (stub / "git").chmod(0o755)
    return bare, lane, stub


def _run_backfill(block: str, lane: Path, stub: Path, summary: Path):
    env = {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}",
           "GITHUB_WORKSPACE": str(REPO_ROOT), "GITHUB_STEP_SUMMARY": str(summary),
           "GITHUB_ACTIONS": "true"}
    return subprocess.run(["bash", "-eo", "pipefail", "-c", "sleep() { :; }\n" + block],
                          cwd=str(lane), capture_output=True, text=True, env=env)


def test_backfill_lane_block_publishes_over_a_racing_commit(tmp_path):
    """The shipped block, verbatim: the pre-fix version died five times on 'cannot pull
    with rebase: You have unstaged changes' and still exited 0."""
    block = _lane_block("backfill.yml", BACKFILL_STEP, {})
    bare, lane, stub = _backfill_fixture(tmp_path)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_backfill(block, lane, stub, summary)
    combined = r.stdout + r.stderr
    assert "cannot pull with rebase" not in combined, combined
    assert r.returncode == 0, combined

    assert _git_output(bare, "show", "main:data/symbol_directory/directory.json") == '{"rows": 4213}', (
        "the backfill never landed — this is the silent no-publish the fix exists to stop"
    )
    assert _git_output(bare, "show", "main:site/qledger/track_record.json") == '{"as_of": "fresh"}'
    assert "other.txt" in _git_output(bare, "ls-tree", "-r", "--name-only", "main"), (
        "the racing lane's commit was clobbered"
    )
    # the two docs the nightly deliberately never stages must stay unpublished; --autostash
    # carries them past the rebase without ever entering the commit.
    assert _git_output(bare, "show", "main:docs/CLAIM_ACCOUNTABILITY.md") == "# committed accountability"
    assert _git_output(bare, "show", "main:docs/GRADING_CLOSURE.md") == "# committed closure"


def test_backfill_lane_block_fails_the_job_when_the_push_never_lands(tmp_path):
    """The measured failure mode: nothing published, job concluded SUCCESS, loss invisible."""
    block = _lane_block("backfill.yml", BACKFILL_STEP, {})
    bare, lane, stub = _backfill_fixture(tmp_path, always_reject=True)
    summary = tmp_path / "summary.md"; summary.touch()
    r = _run_backfill(block, lane, stub, summary)
    combined = r.stdout + r.stderr
    assert r.returncode == 1, f"a backfill that published nothing concluded green:\n{combined}"
    assert "::error title=backfill NOT pushed" in combined
    assert "data/symbol_directory" not in _git_output(bare, "show", "--stat", "main")

@pytest.mark.parametrize("kind,attempt,period,lo,hi", [
    ("contention", 1, 6, 2, 7), ("rebase-conflict", 1, 9, 4, 12),
    ("contention", 3, 12, 5, 16), ("rebase-conflict", 3, 25, 12, 36),
    ("contention", 5, 18, 8, 25), ("rebase-conflict", 5, 41, 20, 60),
    ("contention", 8, 21, 10, 30), ("rebase-conflict", 8, 61, 30, 90),
])
def test_complete_jitter_cycle_covers_policy_support(kind, attempt, period, lo, hi):
    assert "_backoff_complete_jitter_cycle" in globals(), "exact jitter-domain proof is absent"
    samples = _backoff_complete_jitter_cycle(kind, attempt, period)
    assert samples == list(range(lo, hi + 1))
    assert len(samples) == period


def test_complete_jitter_cycle_is_reproducible_without_disabling_runtime_jitter():
    assert "_backoff_complete_jitter_cycle" in globals(), "exact jitter-domain proof is absent"
    first = _backoff_complete_jitter_cycle("contention", 1, 6)
    assert first == _backoff_complete_jitter_cycle("contention", 1, 6)
    assert len(set(first)) == 6



# ---------------------------------------------------------------------------
# GH001 is terminal for the current retry operation, with no cleanup authority.
# All Git state below belongs to temporary synthetic repositories.
# ---------------------------------------------------------------------------

_GH001_ERROR = (
    "remote: error: GH001: Large files detected.\n"
    "error: failed to push some refs to 'synthetic-remote'"
)


def _gh001_env(tmp_path: Path, root: Path, *, rc: int = 42) -> dict[str, str]:
    """Permit a fake rejected push only; any other Git call or sleep is a tripwire."""
    bindir = tmp_path / "gh001-bin"
    bindir.mkdir()
    (bindir / "git").write_text(
        r"""#!/bin/bash
if [ "$(pwd -P)" != "$GH001_FIXTURE_ROOT" ]; then
  echo "fixture Git escaped its temporary root" >&2
  exit 97
fi
printf '%s\0' "$@" >> "$GH001_GIT_LOG"
printf '\n' >> "$GH001_GIT_LOG"
if [ "$1" = push ]; then
  printf '%s\n' "$GH001_ERROR" >&2
  exit "$GH001_RC"
fi
echo "unexpected Git call after terminal rejection" >&2
exit 97
"""
    )
    (bindir / "sleep").write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$GH001_SLEEP_LOG"\n'
        'echo "unexpected sleep after terminal rejection" >&2\nexit 96\n'
    )
    for name in ("git", "sleep"):
        (bindir / name).chmod(0o755)
    return {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "GH001_FIXTURE_ROOT": str(root.resolve()),
        "GH001_GIT_LOG": str(tmp_path / "gh001-git.log"),
        "GH001_SLEEP_LOG": str(tmp_path / "gh001-sleep.log"),
        "GH001_ERROR": _GH001_ERROR,
        "GH001_RC": str(rc),
        "GITHUB_ACTIONS": "true",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "gh001-summary.md"),
    }


def _gh001_repository(tmp_path: Path, monkeypatch, *, rebase_kind: str) -> Path:
    """Retain real index/stash objects and opaque interrupted-rebase bytes."""
    root = tmp_path / "repo"
    assert REPO_ROOT.resolve() not in root.resolve().parents
    # Keep synthetic Git independent of the caller's repository, hooks and config.
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    _init_repo(root)
    _git_output(root, "config", "core.hooksPath", os.devnull)
    _git_output(root, "config", "commit.gpgsign", "false")
    for name in ("staged.txt", "unstaged.txt", "mixed.txt"):
        (root / name).write_text("base\n")
    _git_output(root, "add", ".")
    _git_output(root, "commit", "-qm", "synthetic base")
    (root / "mixed.txt").write_text("retained autostash bytes\n")
    _git_output(root, "stash", "push", "-qm", "autostash", "--", "mixed.txt")
    stash = _git_output(root, "rev-parse", "refs/stash")
    head = _git_output(root, "rev-parse", "HEAD")

    (root / "staged.txt").write_text("staged suffix\n")
    (root / "mixed.txt").write_text("staged mixed suffix\n")
    _git_output(root, "add", "staged.txt", "mixed.txt")
    (root / "mixed.txt").write_text("unstaged mixed suffix\n")
    (root / "unstaged.txt").write_text("unstaged suffix\n")
    (root / "untracked.bin").write_bytes(b"unpublished\x00suffix\n")
    assert _git_output(root, "diff", "--cached", "--name-only")
    assert _git_output(root, "diff", "--name-only")

    metadata = root / ".git" / rebase_kind
    metadata.mkdir()
    for name, value in {
        "head-name": "refs/heads/main\n",
        "orig-head": head + "\n",
        "onto": head + "\n",
        "autostash": stash + "\n",
        "git-rebase-todo": "opaque pending owner work\n",
    }.items():
        (metadata / name).write_text(value)
    (metadata / "retained.bin").write_bytes(b"unknown\x00rebase\xffbytes")
    return root


def _gh001_tree_bytes(root: Path) -> dict[str, tuple]:
    """Include every fixture file, mode and directory, including Git control state."""
    return {
        p.relative_to(root).as_posix(): (
            p.stat().st_mode,
            p.read_bytes() if p.is_file() else None,
        )
        for p in root.rglob("*")
    }


def _assert_gh001_one_push_and_no_sleep(tmp_path: Path) -> None:
    assert (tmp_path / "gh001-git.log").read_bytes() == (
        b"push\0origin\0synthetic-candidate:refs/heads/main\0\n"
    )
    assert not (tmp_path / "gh001-sleep.log").exists()


@pytest.mark.parametrize("rc", [1, 128, 142])
@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "\nhint: Updates were rejected (non-fast-forward; fetch first)",
        "\nremote: cannot lock ref 'refs/heads/main'",
    ],
)
def test_gh001_retains_first_failure_and_outranks_contention_and_alarm(tmp_path, rc, suffix):
    error = _GH001_ERROR + suffix
    r = run_sh(
        r"""
        push_retry_init "synthetic rejection"
        push_classify "$GH001_RC" "$GH001_ERROR"
        push_classify 1 "remote: cannot lock ref 'refs/heads/main'"
        printf '%s\0' "$PUSH_FAIL_CLASS" "${PUSH_TERMINAL_RC:-0}" \
          "${PUSH_TERMINAL_OUTPUT:-}" "$PUSH_STOP" "$PUSH_N_OTHER"
        """,
        env={"GH001_RC": str(rc), "GH001_ERROR": error},
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    fields = r.stdout.split("\0")
    assert fields[:3] == ["push-size-rejected", str(rc), error]
    assert "GH001" in fields[3] and "automatic retry stopped" in fields[3]
    assert fields[4:] == ["1", ""]


@pytest.mark.parametrize(
    "message",
    ["fatal: missing GH001-report.txt", "GH001 appears in a local diagnostic"],
)
def test_gh001_word_without_server_error_does_not_latch(tmp_path, message):
    r = run_sh(
        r"""
        push_retry_init "ordinary error"
        push_classify 1 "$GH001_ERROR"
        printf '%s\n' "$PUSH_FAIL_CLASS" "${PUSH_TERMINAL_RC:-0}"
        """,
        env={"GH001_ERROR": message},
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["push-error", "0"]


def test_gh001_successful_push_output_is_not_a_rejection(tmp_path):
    env = _gh001_env(tmp_path, tmp_path, rc=0)
    r = run_sh(
        """
        push_retry_init "successful synthetic push"
        push_attempt
        push_do origin synthetic-candidate:refs/heads/main
        push_won
        push_lost
        echo "terminal=${PUSH_TERMINAL_RC:-0}"
        """,
        env=env,
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert "terminal=0" in r.stdout
    assert "::error" not in r.stderr
    _assert_gh001_one_push_and_no_sleep(tmp_path)


@pytest.mark.parametrize("rebase_kind", ["rebase-merge", "rebase-apply"])
def test_gh001_standalone_loop_preserves_all_git_and_worktree_bytes(
    tmp_path, monkeypatch, rebase_kind
):
    root = _gh001_repository(tmp_path, monkeypatch, rebase_kind=rebase_kind)
    before = _gh001_tree_bytes(root)
    env = _gh001_env(tmp_path, root)
    r = run_sh(
        """
        push_retry_init "synthetic retained suffix"
        while push_attempt; do
          if push_do origin synthetic-candidate:refs/heads/main; then
            push_won
            exit 0
          fi
          # Neither a wider budget nor a later recovery marker permits cleanup.
          PUSH_MAX_ATTEMPTS=99
          PUSH_DEADLINE=$((PUSH_DEADLINE + 999))
          PUSH_ATTEMPT_INHERITED_REBASE=1
          push_abort_rebase
          push_backoff
        done
        echo "attempts=$PUSH_ATTEMPT recovery=$PUSH_RECOVERY_FAILED"
        push_lost
        echo "MASKED TERMINAL FAILURE"
        """,
        env=env,
        cwd=root,
    )
    assert r.returncode == 42, (r.stdout, r.stderr)
    assert "attempts=1 recovery=0" in r.stdout
    assert "MASKED TERMINAL FAILURE" not in r.stdout
    assert any(line.startswith("::error") and "GH001" in line for line in r.stderr.splitlines())
    summary = (tmp_path / "gh001-summary.md").read_text()
    assert "NOT pushed" in summary and "GH001" in summary and "attempts=1/99" in summary
    assert "other=1" in summary
    _assert_gh001_one_push_and_no_sleep(tmp_path)
    assert _gh001_tree_bytes(root) == before


@pytest.mark.parametrize(
    ("helper", "expected_rc"),
    [
        ("push_abort_rebase", 0),
        ("push_backoff", 0),
        ("push_autostash_ok", 42),
        ("push_fetch_main_for_rebase", 42),
        ("push_prepare_inherited_rebase", 42),
    ],
)
def test_gh001_terminal_helpers_do_not_inspect_or_mutate_retained_state(
    tmp_path, monkeypatch, helper, expected_rc
):
    root = _gh001_repository(tmp_path, monkeypatch, rebase_kind="rebase-merge")
    before = _gh001_tree_bytes(root)
    env = _gh001_env(tmp_path, root)
    r = run_sh(
        f"""
        push_retry_init "retained state"
        push_attempt
        if push_do origin synthetic-candidate:refs/heads/main; then exit 95; fi
        PUSH_ATTEMPT_INHERITED_REBASE=1
        if {helper}; then result=0; else result=$?; fi
        echo "helper=$result terminal=$PUSH_TERMINAL_RC recovery=$PUSH_RECOVERY_FAILED"
        if push_do origin different-candidate:refs/heads/main; then exit 95; else
          echo "second_push=$?"
        fi
        """,
        env=env,
        cwd=root,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert f"helper={expected_rc} terminal=42 recovery=0" in r.stdout
    assert "second_push=42" in r.stdout
    _assert_gh001_one_push_and_no_sleep(tmp_path)
    assert _gh001_tree_bytes(root) == before


def test_gh001_conditional_function_returns_terminal_failure_without_errexit(tmp_path):
    env = _gh001_env(tmp_path, tmp_path)
    r = run_sh(
        """
        synthetic_publish() {
          push_retry_init "conditional synthetic caller"
          while push_attempt; do
            if push_do origin synthetic-candidate:refs/heads/main; then return 0; fi
            push_abort_rebase
            push_backoff
          done
          push_lost
        }
        # Bash suppresses errexit inside a function tested by if. Its explicit
        # final nonzero result still has to reach the caller.
        if synthetic_publish; then
          echo "MASKED TERMINAL FAILURE"
          exit 95
        else
          result=$?
          echo "conditional_result=$result"
          exit "$result"
        fi
        """,
        env=env,
        cwd=tmp_path,
    )
    assert r.returncode == 42, (r.stdout, r.stderr)
    assert "conditional_result=42" in r.stdout
    assert "MASKED TERMINAL FAILURE" not in r.stdout
    _assert_gh001_one_push_and_no_sleep(tmp_path)


def test_gh001_new_explicit_retry_operation_clears_terminal_receipt(tmp_path):
    r = run_sh(
        r"""
        push_retry_init "first operation"
        push_classify 42 "$GH001_ERROR"
        push_retry_init "new explicit operation"
        push_attempt
        printf '%s\0' "$PUSH_TERMINAL_RC" "$PUSH_TERMINAL_OUTPUT" \
          "$PUSH_STOP" "$PUSH_N_OTHER" "$PUSH_ATTEMPT"
        """,
        env={"GH001_ERROR": _GH001_ERROR},
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\0") == ["0", "", "", "0", "1", ""]


def _ohlc_delivery_step():
    document = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "daily.yml").read_text()
    )
    return next(
        step for step in document["jobs"]["engine"]["steps"]
        if "python -m scripts.publish_ohlc publish" in step.get("run", "")
    )


@pytest.mark.parametrize("publisher_status", [0, 31])
def test_ohlc_delivery_workflow_cleans_key_and_preserves_publisher_status(
    tmp_path, publisher_status
):
    """Execute the actual step with a local publisher stub; never contact a host."""
    import json
    import sys

    step = _ohlc_delivery_step()
    assert step["if"] == "always()"
    assert step["timeout-minutes"] == 20
    assert step["env"] == {"OHLC_DEPLOY_KEY": "${{ secrets.VPS_DEPLOY_KEY }}"}
    package = tmp_path / "scripts"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "publish_ohlc.py").write_text(
        "import json, os, pathlib, stat, sys\n"
        "args = sys.argv[1:]\n"
        "assert args[0] == 'publish'\n"
        "key = pathlib.Path(args[args.index('--ssh-key') + 1])\n"
        "assert stat.S_IMODE(key.stat().st_mode) == 0o600\n"
        "assert key.read_text() == 'synthetic-key-canary\\n'\n"
        "assert 'OHLC_DEPLOY_KEY' not in os.environ\n"
        "pathlib.Path('publisher-call.json').write_text(json.dumps(args))\n"
        f"sys.exit({publisher_status})\n"
    )
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    # Use this test's interpreter; the remainder is the unmodified workflow shell.
    body = step["run"].replace(
        "python -m scripts.publish_ohlc", f"{shlex.quote(sys.executable)} -m scripts.publish_ohlc"
    )
    result = subprocess.run(
        ["bash", "-c", body], cwd=tmp_path, capture_output=True, text=True,
        env={
            **os.environ,
            "OHLC_DEPLOY_KEY": "synthetic-key-canary",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
        },
        check=False,
    )
    assert result.returncode == publisher_status, result.stderr
    args = json.loads((tmp_path / "publisher-call.json").read_text())
    assert args[args.index("--manifest") + 1] == "site/_tmp/ohlc-complete.json"
    assert args[args.index("--payload-dir") + 1] == "site/ohlc"
    assert args[args.index("--evidence-dir") + 1].endswith("/macro-ohlc-delivery/123-2")
    assert not list(runner_temp.iterdir())
    assert "synthetic-key-canary" not in result.stdout + result.stderr


def test_ohlc_delivery_workflow_missing_key_is_visible_before_publish(tmp_path):
    step = _ohlc_delivery_step()
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path,
        env={**os.environ, "OHLC_DEPLOY_KEY": "", "RUNNER_TEMP": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert "::error::OHLC origin delivery" in result.stdout
    assert not list(tmp_path.iterdir())


def _us_board_clone(tmp_path: Path) -> tuple[Path, Path]:
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    seed = tmp_path / "seed"
    _init_repo(seed)
    for rel in ("data/us_board_ledger/snapshots.jsonl", "data/us_sector_rotation/latest.json", "data/other.jsonl"):
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text("old\n")
    subprocess.run(["git", "-C", str(seed), "add", "."], check=True)
    subprocess.run(["git", "-C", str(seed), "commit", "-q", "-m", "seed"], check=True)
    _git_output(seed, "push", "-q", str(bare), "main")
    repo = tmp_path / "lane"
    subprocess.run(["git", "clone", "-q", str(bare), str(repo)], check=True)
    return bare, repo


def _run_us_board_commit(repo: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "ci" / "us_board_commit.sh"), *args],
        capture_output=True,
        text=True,
        cwd=str(repo),
        env={**os.environ, "GITHUB_WORKSPACE": str(REPO_ROOT), **env},
    )


def test_us_board_commit_lands_its_own_paths_and_nothing_else(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_text("new\n")
    (repo / "data/us_sector_rotation/latest.json").write_text("new\n")
    (repo / "site/factordata").mkdir(parents=True)
    (repo / "site/factordata/us_board_track.json").write_text("{}\n")
    (repo / "data/other.jsonl").write_text("not ours\n")

    result = _run_us_board_commit(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _git_output(bare, "diff", "--name-only", "main~1", "main").split() == [
        "data/us_board_ledger/snapshots.jsonl",
        "data/us_sector_rotation/latest.json",
        "site/factordata/us_board_track.json",
    ]


def test_us_board_commit_with_nothing_to_land_is_green_and_pushes_nothing(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    before = _git_output(bare, "rev-parse", "main")

    result = _run_us_board_commit(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _git_output(bare, "rev-parse", "main") == before


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    ).stdout


def _hold_env(tmp_path: Path, run_id: str, **extra: str) -> dict[str, str]:
    rt = tmp_path / "rt"
    rt.mkdir(exist_ok=True)
    env = {
        "PUSH_BLOB_LIMIT": "50",
        "PUSH_HOLD_PART": "20",
        "RUNNER_TEMP": str(rt),
        "GITHUB_RUN_ID": run_id,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_JOB": "us_board_ledgers",
        "GITHUB_STEP_SUMMARY": str(tmp_path / f"summary-{run_id}.md"),
        "PUSH_MAX_ATTEMPTS": "1",
        "PUSH_BUDGET_SECS": "0",
    }
    env.update(extra)
    return env


def _hold_refs(bare: Path) -> list[str]:
    out = _git_output(
        bare, "for-each-ref", "--format=%(refname)", "refs/heads/push-hold/us_board_ledgers"
    )
    return [line for line in out.splitlines() if line]


def _manifest(bare: Path, ref: str) -> tuple[list[dict[str, str]], list[str]]:
    text = _git_bytes(bare, "cat-file", "blob", f"{ref}:MANIFEST").decode()
    entries: list[dict[str, str]] = []
    froms: list[str] = []
    assert text.startswith("push-hold/v1\n")
    for line in text.splitlines():
        parts = line.split("\t")
        if parts[0] == "entry":
            entries.append(
                {
                    "i": parts[1],
                    "path": parts[2],
                    "blob": parts[3],
                    "size": parts[4],
                    "head": parts[5],
                    "layout": parts[6],
                }
            )
        elif parts[0] == "from":
            froms.append(parts[1])
    return entries, froms


def _rebuild(bare: Path, ref: str, entry: dict[str, str]) -> bytes:
    index = entry["i"]
    layout = entry["layout"]
    if layout == "blob":
        return _git_bytes(bare, "cat-file", "blob", f"{ref}:blobs/{index}")
    data = b""
    if layout == "prefix":
        data = _git_bytes(bare, "cat-file", "blob", f"{ref}:parts/{index}/base")
    names = _git_output(bare, "ls-tree", "--name-only", f"{ref}:parts/{index}").splitlines()
    for name in sorted(n for n in names if n and n != "base"):
        data += _git_bytes(bare, "cat-file", "blob", f"{ref}:parts/{index}/{name}")
    return data


def _clone_of(bare: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(bare), str(dest)], check=True)
    return dest


def _reject_ref(bare: Path, pattern: str) -> None:
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\n"
        "while read old new ref; do\n"
        "  case \"$ref\" in\n"
        f"    {pattern})\n"
        "      echo reject >&2\n"
        "      exit 1\n"
        "      ;;\n"
        "  esac\n"
        "done\n"
        "exit 0\n"
    )
    hook.chmod(0o755)


def test_us_board_hold_keeps_oversize_ledger_rows_and_lands_rotation(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    new = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(new)
    (repo / "data/us_sector_rotation/latest.json").write_text("rotated\n")
    env = _hold_env(tmp_path, "101")

    result = _run_us_board_commit(repo, **env)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "::error title=withheld, not lost::" in result.stdout
    assert _git_output(bare, "diff", "--name-only", "main~1", "main").split() == [
        "data/us_sector_rotation/latest.json",
    ]
    refs = _hold_refs(bare)
    assert len(refs) == 1
    ref = refs[0]
    assert ref.startswith("refs/heads/push-hold/us_board_ledgers/")
    entries, _froms = _manifest(bare, ref)
    assert len(entries) == 1
    assert entries[0]["path"] == "data/us_board_ledger/snapshots.jsonl"
    assert entries[0]["layout"] == "prefix"
    assert _rebuild(bare, ref, entries[0]) == new
    assert ref in Path(env["GITHUB_STEP_SUMMARY"]).read_text()


def test_us_board_hold_keeps_a_new_oversize_ledger_file_on_disk_and_in_custody(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    payload = b"N" * 60
    path = repo / "data/us_board_ledger/brand_new.jsonl"
    path.write_bytes(payload)
    (repo / "data/us_sector_rotation/latest.json").write_text("rotated\n")

    result = _run_us_board_commit(repo, **_hold_env(tmp_path, "102"))

    assert result.returncode == 1, result.stdout + result.stderr
    assert path.read_bytes() == payload
    assert _git_output(bare, "diff", "--name-only", "main~1", "main").split() == [
        "data/us_sector_rotation/latest.json",
    ]
    refs = _hold_refs(bare)
    assert len(refs) == 1
    entries, _froms = _manifest(bare, refs[0])
    match = [entry for entry in entries if entry["path"] == "data/us_board_ledger/brand_new.jsonl"]
    assert len(match) == 1
    assert match[0]["layout"] == "whole"
    assert _rebuild(bare, refs[0], match[0]) == payload


def test_us_board_recover_lands_held_rows_plus_the_next_row_and_retires_the_ref(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "301"))
    assert first.returncode == 1, first.stdout + first.stderr
    old_refs = _hold_refs(bare)
    assert len(old_refs) == 1

    lane2 = _clone_of(bare, tmp_path / "lane2")
    env2 = _hold_env(tmp_path, "302", PUSH_BLOB_LIMIT="1000000")
    recovered = _run_us_board_commit(lane2, "--recover", **env2)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    snap = lane2 / "data/us_board_ledger/snapshots.jsonl"
    assert snap.read_bytes() == held
    row = b"row-2\n"
    snap.write_bytes(held + row)
    second = _run_us_board_commit(lane2, **env2)

    assert second.returncode == 0, second.stdout + second.stderr
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == held + row
    assert _hold_refs(bare) == []


def test_us_board_settle_keeps_a_ref_whose_held_path_did_not_land(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "351"))
    assert first.returncode == 1, first.stdout + first.stderr
    old_refs = _hold_refs(bare)
    assert len(old_refs) == 1

    lane2 = _clone_of(bare, tmp_path / "lane2")
    env2 = _hold_env(tmp_path, "352", PUSH_BLOB_LIMIT="1000000")
    recovered = _run_us_board_commit(lane2, "--recover", **env2)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    snap = lane2 / "data/us_board_ledger/snapshots.jsonl"
    assert snap.read_bytes() == held
    # A writer puts the ledger back to main's bytes: the push that wins carries only rotation,
    # so the held rows are neither landed nor held again and their ref must stay.
    snap.write_bytes(b"old\n")
    (lane2 / "data/us_sector_rotation/latest.json").write_text("rotated\n")
    second = _run_us_board_commit(lane2, **env2)

    out = second.stdout + second.stderr
    assert _git_output(bare, "diff", "--name-only", "main~1", "main").split() == [
        "data/us_sector_rotation/latest.json",
    ], out
    assert _hold_refs(bare) == old_refs, out
    assert "::warning title=hold ref kept::" in out
    entries, _froms = _manifest(bare, old_refs[0])
    assert _rebuild(bare, old_refs[0], entries[0]) == held


def test_us_board_rehold_records_from_the_old_ref_and_retires_it(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "401"))
    assert first.returncode == 1, first.stdout + first.stderr
    old_ref = _hold_refs(bare)[0]

    lane2 = _clone_of(bare, tmp_path / "lane2")
    env2 = _hold_env(tmp_path, "402")
    recovered = _run_us_board_commit(lane2, "--recover", **env2)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    snap = lane2 / "data/us_board_ledger/snapshots.jsonl"
    assert snap.read_bytes() == held
    longer = held + b"X"
    snap.write_bytes(longer)
    second = _run_us_board_commit(lane2, **env2)

    assert second.returncode == 1, second.stdout + second.stderr
    refs = _hold_refs(bare)
    assert old_ref not in refs
    assert len(refs) == 1
    entries, froms = _manifest(bare, refs[0])
    assert old_ref in froms
    assert _rebuild(bare, refs[0], entries[0]) == longer


def test_us_board_main_push_rejection_keeps_custody_bytes_and_goes_red(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    before = _git_output(bare, "rev-parse", "main")
    new = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(new)
    (repo / "data/us_sector_rotation/latest.json").write_text("rotated\n")
    _reject_ref(bare, "refs/heads/main")

    result = _run_us_board_commit(repo, **_hold_env(tmp_path, "501"))

    assert result.returncode == 1, result.stdout + result.stderr
    assert _git_output(bare, "rev-parse", "main") == before
    refs = _hold_refs(bare)
    assert len(refs) == 1
    entries, _froms = _manifest(bare, refs[0])
    assert _rebuild(bare, refs[0], entries[0]) == new


def test_us_board_custody_push_rejection_reverts_nothing(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    before = _git_output(bare, "rev-parse", "main")
    new = b"old\n" + (b"R" * 60)
    path = repo / "data/us_board_ledger/snapshots.jsonl"
    path.write_bytes(new)
    (repo / "data/us_sector_rotation/latest.json").write_text("rotated\n")
    _reject_ref(bare, "refs/heads/push-hold/*")

    result = _run_us_board_commit(repo, **_hold_env(tmp_path, "502"))

    assert result.returncode == 1, result.stdout + result.stderr
    assert "::error title=hold custody failed::" in result.stdout + result.stderr
    assert _git_output(bare, "rev-parse", "main") == before
    assert path.read_bytes() == new
    assert "data/us_board_ledger/snapshots.jsonl" in _git_output(
        repo, "diff", "--cached", "--name-only"
    )
    assert _hold_refs(bare) == []


def test_us_board_hold_keeps_the_whole_board_group_and_lands_rotation(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    new = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(new)
    track = repo / "site/factordata/us_board_track.json"
    track.parent.mkdir(parents=True)
    track_bytes = b'{"k":1}\n'
    track.write_bytes(track_bytes)
    (repo / "data/us_sector_rotation/latest.json").write_text("rotated\n")

    result = _run_us_board_commit(repo, **_hold_env(tmp_path, "601"))

    assert result.returncode == 1, result.stdout + result.stderr
    assert _git_output(bare, "diff", "--name-only", "main~1", "main").split() == [
        "data/us_sector_rotation/latest.json",
    ]
    refs = _hold_refs(bare)
    assert len(refs) == 1
    entries, _froms = _manifest(bare, refs[0])
    by_path = {entry["path"]: entry for entry in entries}
    assert sorted(by_path) == [
        "data/us_board_ledger/snapshots.jsonl",
        "site/factordata/us_board_track.json",
    ]
    assert by_path["data/us_board_ledger/snapshots.jsonl"]["layout"] == "prefix"
    assert _rebuild(bare, refs[0], by_path["data/us_board_ledger/snapshots.jsonl"]) == new
    assert by_path["site/factordata/us_board_track.json"]["layout"] == "blob"
    assert _rebuild(bare, refs[0], by_path["site/factordata/us_board_track.json"]) == track_bytes


def test_hold_membership_not_proved_holds_every_staged_path(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    other = b"Z" * 60
    (repo / "data/other.jsonl").write_bytes(other)
    (repo / "data/us_sector_rotation/latest.json").write_text("small-change\n")
    subprocess.run(
        ["git", "-C", str(repo), "add", "data/other.jsonl", "data/us_sector_rotation/latest.json"],
        check=True,
    )
    env = _hold_env(tmp_path, "701")

    result = run_sh(
        f'''
        . "{REPO_ROOT}/scripts/ci/push_hold.sh"
        push_hold_oversize_staged "data/us_board_ledger" "data/us_sector_rotation"
        ''',
        env=env,
        cwd=repo,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "hold membership not proved" in result.stdout
    assert "data/other.jsonl belongs to no declared group" in result.stdout
    refs = _hold_refs(bare)
    assert len(refs) == 1
    entries, _froms = _manifest(bare, refs[0])
    by_path = {entry["path"]: entry for entry in entries}
    assert sorted(by_path) == ["data/other.jsonl", "data/us_sector_rotation/latest.json"]
    assert _rebuild(bare, refs[0], by_path["data/other.jsonl"]) == other
    assert _rebuild(bare, refs[0], by_path["data/us_sector_rotation/latest.json"]) == b"small-change\n"
    assert _git_output(repo, "diff", "--cached", "--name-only") == ""


def test_us_board_recover_when_base_moved_keeps_the_ref_and_the_commit_step_is_red(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "801"))
    assert first.returncode == 1, first.stdout + first.stderr
    old_refs = _hold_refs(bare)
    assert len(old_refs) == 1

    seed = tmp_path / "seed"
    (seed / "data/us_board_ledger/snapshots.jsonl").write_text("advanced\n")
    subprocess.run(
        ["git", "-C", str(seed), "add", "data/us_board_ledger/snapshots.jsonl"], check=True
    )
    subprocess.run(["git", "-C", str(seed), "commit", "-q", "-m", "advance"], check=True)
    _git_output(seed, "push", str(bare), "main")

    lane2 = _clone_of(bare, tmp_path / "lane2")
    env2 = _hold_env(tmp_path, "802")
    recovered = _run_us_board_commit(lane2, "--recover", **env2)
    assert recovered.returncode == 1, recovered.stdout + recovered.stderr
    assert "held rows not restored" in recovered.stdout + recovered.stderr
    assert (lane2 / "data/us_board_ledger/snapshots.jsonl").read_text() == "advanced\n"
    assert _hold_refs(bare) == old_refs

    before = _git_output(bare, "rev-parse", "main")
    board = lane2 / "data/us_board_ledger/snapshots.jsonl"
    rotation = lane2 / "data/us_sector_rotation/latest.json"
    board.write_text("staged next row\n")
    _git_output(lane2, "add", "data/us_board_ledger/snapshots.jsonl")
    board.write_text("unstaged next row\n")
    rotation.write_text("small next rotation\n")
    index_before = _git_output(lane2, "write-tree")

    commit = _run_us_board_commit(lane2, **env2)
    assert commit.returncode == 1, commit.stdout + commit.stderr
    assert _git_output(bare, "rev-parse", "main") == before
    assert _hold_refs(bare) == old_refs
    assert _git_output(lane2, "write-tree") == index_before
    assert board.read_text() == "unstaged next row\n"
    assert rotation.read_text() == "small next rotation\n"
    entries, _ = _manifest(bare, old_refs[0])
    assert _rebuild(bare, old_refs[0], entries[0]) == held


def test_us_board_lineage_applies_only_the_successor_and_a_winning_push_retires_both(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "901"))
    assert first.returncode == 1, first.stdout + first.stderr
    ref1 = _hold_refs(bare)[0]

    _reject_ref(bare, "refs/heads/main")
    lane2 = _clone_of(bare, tmp_path / "lane2")
    env2 = _hold_env(tmp_path, "902")
    recovered = _run_us_board_commit(lane2, "--recover", **env2)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    longer = held + (b"S" * 30)
    (lane2 / "data/us_board_ledger/snapshots.jsonl").write_bytes(longer)
    (lane2 / "data/us_sector_rotation/latest.json").write_text("rot2\n")
    second = _run_us_board_commit(lane2, **env2)
    assert second.returncode == 1, second.stdout + second.stderr
    refs = _hold_refs(bare)
    assert ref1 in refs
    assert len(refs) == 2
    ref2 = next(ref for ref in refs if ref != ref1)
    entries2, froms2 = _manifest(bare, ref2)
    assert ref1 in froms2
    assert _rebuild(bare, ref2, entries2[0]) == longer

    (bare / "hooks" / "pre-receive").unlink()
    lane3 = _clone_of(bare, tmp_path / "lane3")
    env3 = _hold_env(tmp_path, "903", PUSH_BLOB_LIMIT="1000000")
    recovered3 = _run_us_board_commit(lane3, "--recover", **env3)
    assert recovered3.returncode == 0, recovered3.stdout + recovered3.stderr
    assert (lane3 / "data/us_board_ledger/snapshots.jsonl").read_bytes() == longer
    third = _run_us_board_commit(lane3, **env3)
    assert third.returncode == 0, third.stdout + third.stderr
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == longer
    assert _hold_refs(bare) == []


def _custody_git_interceptor(tmp_path: Path, body: str) -> Path:
    """Inject a client result while every real Git operation remains local."""
    fakebin = tmp_path / "custody-bin"
    fakebin.mkdir()
    real_git = shutil.which("git")
    assert real_git
    script = fakebin / "git"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f"REAL_GIT={shlex.quote(real_git)}\n"
        + textwrap.dedent(body)
        + '\nexec "$REAL_GIT" "$@"\n'
    )
    script.chmod(0o755)
    return fakebin


@pytest.mark.parametrize(
    "mode,attempts,confirmed",
    [
        ("accepted_client_failure", 1, True),
        ("unreadable_after_success", 1, False),
        ("unreadable_after_failure", 1, False),
        ("collision", 1, False),
        ("confirmed_absence", 3, False),
        ("permission_denied", 1, False),
        ("malformed_readback", 1, False),
    ],
)
def test_us_board_custody_push_reconciles_every_result_before_retry(
    tmp_path, mode, attempts, confirmed
):
    bare, repo = _us_board_clone(tmp_path)
    before = _git_output(bare, "rev-parse", "main")
    held = b"old\n" + (b"R" * 60)
    path = repo / "data/us_board_ledger/snapshots.jsonl"
    path.write_bytes(held)
    log = tmp_path / "custody-commands.log"
    fakebin = _custody_git_interceptor(
        tmp_path,
        r"""
        if [ "$1" = push ]; then
          case "$3" in
            *:refs/heads/push-hold/*)
              printf 'push\t%s\n' "$3" >> "$CUSTODY_LOG"
              case "$CUSTODY_MODE" in
                accepted_client_failure)
                  "$REAL_GIT" "$@" || exit $?
                  exit 75 ;;
                unreadable_after_success)
                  "$REAL_GIT" "$@"
                  exit $? ;;
                collision)
                  "$REAL_GIT" -C "$CUSTODY_BARE" update-ref "${3#*:}" "$CUSTODY_BEFORE"
                  exit 1 ;;
                permission_denied)
                  echo "remote: Permission to fixture/repo denied" >&2
                  exit 128 ;;
                *) echo "injected transport failure" >&2; exit 75 ;;
              esac
              ;;
          esac
        fi
        if [ "$1" = ls-remote ]; then
          case "$*" in
            *refs/heads/push-hold/*)
              printf 'read\t%s\n' "$*" >> "$CUSTODY_LOG"
              case "$CUSTODY_MODE" in
                unreadable_after_success|unreadable_after_failure) exit 73 ;;
                malformed_readback) printf 'unparseable-status\n'; exit 0 ;;
              esac
              ;;
          esac
        fi
        """,
    )
    env = _hold_env(
        tmp_path, "1001", PUSH_HOLD_TRIES="3",
        PATH=f"{fakebin}:{os.environ['PATH']}",
        CUSTODY_MODE=mode, CUSTODY_LOG=str(log),
        CUSTODY_BARE=str(bare), CUSTODY_BEFORE=before,
    )
    result = _run_us_board_commit(repo, **env)
    # A verified current-run hold is still red; helper success is not publication.
    assert result.returncode == 1, result.stdout + result.stderr
    events = log.read_text().splitlines()
    assert [event.split("\t", 1)[0] for event in events] == ["push", "read"] * attempts
    targets = {event.split("\t", 1)[1] for event in events if event.startswith("push\t")}
    assert len(targets) == 1
    intended, ref = next(iter(targets)).split(":", 1)
    assert all(event.endswith(ref) for event in events if event.startswith("read\t"))
    assert _git_output(bare, "rev-parse", "main") == before
    if confirmed:
        assert _git_output(bare, "rev-parse", ref) == intended
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held
        assert path.read_bytes() == b"old\n"
        assert not _git_output(repo, "diff", "--cached", "--name-only")
    else:
        assert path.read_bytes() == held
        assert "data/us_board_ledger/snapshots.jsonl" in _git_output(
            repo, "diff", "--cached", "--name-only"
        )
        if mode == "collision":
            assert _git_output(bare, "rev-parse", ref) == before
            assert "collision" in result.stdout
        elif mode == "unreadable_after_success":
            assert _git_output(bare, "rev-parse", ref) == intended
            entries, _ = _manifest(bare, ref)
            assert _rebuild(bare, ref, entries[0]) == held
        else:
            assert _hold_refs(bare) == []
        # A later same-run checkpoint must not mint another ref past this failure.
        index_before = _git_output(repo, "write-tree")
        blocked = _run_us_board_commit(repo, **env)
        assert blocked.returncode == 1, blocked.stdout + blocked.stderr
        assert log.read_text().splitlines() == events
        assert path.read_bytes() == held
        assert _git_output(repo, "write-tree") == index_before
        assert _git_output(bare, "rev-parse", "main") == before
        if mode.startswith("unreadable") or mode == "malformed_readback":
            assert "EFFECT_UNKNOWN" in result.stdout
        elif mode == "permission_denied":
            assert "terminal push rejection" in result.stdout


@pytest.mark.parametrize(
    "failure",
    ["discovery", "fetch", "manifest", "overlap", "recovery_record", "state"],
)
def test_us_board_failed_recovery_blocks_small_new_inputs_and_preserves_custody(
    tmp_path, failure
):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + (b"R" * 60)
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "1101"))
    assert first.returncode == 1, first.stdout + first.stderr
    original_ref = _hold_refs(bare)[0]
    before = _git_output(bare, "rev-parse", "main")
    if failure in {"manifest", "overlap"}:
        target = before if failure == "manifest" else _git_output(bare, "rev-parse", original_ref)
        _git_output(bare, "update-ref", original_ref + "-extra", target)
    refs_before = _git_output(bare, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/push-hold/")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1102")
    if failure in {"discovery", "fetch"}:
        command = "ls-remote" if failure == "discovery" else "fetch"
        fakebin = _custody_git_interceptor(
            tmp_path,
            f'if [ "$1" = {command} ]; then exit 73; fi\n',
        )
        env["PATH"] = f"{fakebin}:{os.environ['PATH']}"
    elif failure == "recovery_record":
        state = Path(env["RUNNER_TEMP"]) / "push_hold.1102.us_board_ledgers"
        (state / "recovered").mkdir(parents=True)
    elif failure == "state":
        unavailable = tmp_path / "not-a-directory"
        unavailable.write_text("keep this preimage\n")
        env["RUNNER_TEMP"] = str(unavailable)

    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 1, recovery.stdout + recovery.stderr
    board = lane / "data/us_board_ledger/snapshots.jsonl"
    rotation = lane / "data/us_sector_rotation/latest.json"
    board.write_text("staged later row\n")
    _git_output(lane, "add", "data/us_board_ledger/snapshots.jsonl")
    board.write_text("unstaged later row\n")
    rotation.write_text("small later rotation\n")
    index_before = _git_output(lane, "write-tree")

    result = _run_us_board_commit(lane, **env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert _git_output(bare, "rev-parse", "main") == before
    assert _git_output(bare, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/push-hold/") == refs_before
    assert _git_output(lane, "write-tree") == index_before
    assert board.read_text() == "unstaged later row\n"
    assert rotation.read_text() == "small later rotation\n"
    entries, _ = _manifest(bare, original_ref)
    assert _rebuild(bare, original_ref, entries[0]) == held


@pytest.mark.parametrize("errexit", [False, True])
def test_hold_recovery_preserves_the_callers_errexit_and_reports_failure(tmp_path, errexit):
    bare, repo = _us_board_clone(tmp_path)
    fakebin = _custody_git_interceptor(
        tmp_path, 'if [ "$1" = ls-remote ]; then exit 73; fi\n'
    )
    env = _hold_env(tmp_path, "1201", PATH=f"{fakebin}:{os.environ['PATH']}")
    helper = REPO_ROOT / "scripts/ci/push_hold.sh"
    result = run_sh(
        f'. {shlex.quote(str(helper))}\n'
        + ("set -e\n" if errexit else "set +e\n")
        + 'if push_hold_recover data/us_board_ledger; then exit 99; else rc=$?; fi\n'
        + 'printf "rc=%s flags=%s\\n" "$rc" "$-"\n',
        cwd=repo, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = next(line for line in result.stdout.splitlines() if line.startswith("rc="))
    assert report.startswith("rc=1 ")
    assert ("e" in report.split("flags=", 1)[1]) is errexit


@pytest.mark.parametrize("blocked_state", ["directory", "empty_marker"])
def test_us_board_unreadable_state_cannot_hide_an_unreconciled_ref(tmp_path, blocked_state):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"R" * 60
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "1301"))
    assert first.returncode == 1, first.stdout + first.stderr
    refs = _hold_refs(bare)
    assert len(refs) == 1
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1302")
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1302.us_board_ledgers"
    state.mkdir()
    marker = state / "unreconciled"
    marker.write_text(refs[0] + "\n" if blocked_state == "directory" else "")
    board = lane / "data/us_board_ledger/snapshots.jsonl"
    rotation = lane / "data/us_sector_rotation/latest.json"
    board.write_text("small later source\n")
    rotation.write_text("small later projection\n")
    _git_output(lane, "add", "data/us_board_ledger/snapshots.jsonl")
    index_before = _git_output(lane, "write-tree")
    before = _git_output(bare, "rev-parse", "main")
    if blocked_state == "directory":
        state.chmod(0)
    else:
        marker.chmod(0o400)
    try:
        if blocked_state == "directory":
            assert not os.access(state, os.R_OK | os.W_OK | os.X_OK)
        else:
            assert not os.access(marker, os.W_OK)
        recovery = _run_us_board_commit(lane, "--recover", **env)
        assert recovery.returncode == 1, recovery.stdout + recovery.stderr
        result = _run_us_board_commit(lane, **env)
        assert result.returncode == 1, result.stdout + result.stderr
        assert _git_output(bare, "rev-parse", "main") == before
        assert _git_output(lane, "write-tree") == index_before
        assert board.read_text() == "small later source\n"
        assert rotation.read_text() == "small later projection\n"
        assert _hold_refs(bare) == refs
        entries, _ = _manifest(bare, refs[0])
        assert _rebuild(bare, refs[0], entries[0]) == held
    finally:
        state.chmod(0o700)
        marker.chmod(0o600)


@pytest.mark.parametrize("record_failure", ["append", "input_read"])
def test_us_board_failed_held_record_keeps_custody_and_blocks_publication(tmp_path, record_failure):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"R" * 60
    board = repo / "data/us_board_ledger/snapshots.jsonl"
    rotation = repo / "data/us_sector_rotation/latest.json"
    board.write_bytes(held)
    rotation.write_text("small later projection\n")
    _git_output(repo, "add", "data/us_board_ledger", "data/us_sector_rotation")
    before_index = _git_output(repo, "write-tree")
    before_main = _git_output(bare, "rev-parse", "main")
    env = _hold_env(tmp_path, "1303")
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1303.us_board_ledgers"
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "push-calls"
    wrapper = fake_bin / "git"
    wrapper.write_text(
        "#!/bin/bash\n"
        'if [ "${1:-}" = "push" ]; then printf "%s\\n" push >> "$PUSH_CALLS"; fi\n'
        'if [ "${1:-}" = "ls-remote" ] && [ "${2:-}" = "--refs" ]; then\n'
        '  "$REAL_GIT" "$@" || exit "$?"\n'
        '  if [ "$RECORD_FAILURE" = "append" ]; then\n'
        '    : > "$FAULT_STATE/held"\n'
        '    chmod 400 "$FAULT_STATE/held"\n'
        '  else\n'
        '    fault="$FAULT_STATE/work/hold_paths"\n'
        '    if [ ! -f "$fault" ]; then fault="$FAULT_STATE/work/take"; fi\n'
        '    chmod 000 "$fault"\n'
        '  fi\n'
        '  exit 0\n'
        'fi\n'
        'exec "$REAL_GIT" "$@"\n'
    )
    wrapper.chmod(0o755)
    env.update({
        "PATH": f"{fake_bin}:{os.environ['PATH']}", "REAL_GIT": real_git,
        "PUSH_CALLS": str(calls), "FAULT_STATE": str(state), "RECORD_FAILURE": record_failure,
    })
    try:
        result = _run_us_board_commit(repo, **env)
        assert result.returncode == 1, result.stdout + result.stderr
        if record_failure == "append":
            fault_record = state / "held"
            assert not os.access(fault_record, os.W_OK)
        else:
            fault_record = state / "work/hold_paths"
            if not fault_record.exists():
                fault_record = state / "work/take"
            assert not os.access(fault_record, os.R_OK)
        [ref] = _hold_refs(bare)
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held
        assert _git_output(bare, "rev-parse", "main") == before_main
        assert _git_output(repo, "write-tree") == before_index
        assert board.read_bytes() == held
        assert rotation.read_text() == "small later projection\n"
        assert calls.read_text().splitlines() == ["push"]

        fault_record.chmod(0o600)
        board.write_text("short\n")
        _git_output(repo, "add", "data/us_board_ledger")
        later_index = _git_output(repo, "write-tree")
        second = _run_us_board_commit(repo, **env)
        assert second.returncode == 1, second.stdout + second.stderr
        assert "unreconciled recovery state blocks" in second.stdout
        assert "could not record verified hold" in result.stdout
        assert ref in (state / "unreconciled").read_text()
        assert _git_output(repo, "write-tree") == later_index
        assert _git_output(bare, "rev-parse", "main") == before_main
        assert _hold_refs(bare) == [ref]
        assert calls.read_text().splitlines() == ["push"]
    finally:
        if state.exists():
            state.chmod(0o700)
            for name in ("held", "unreconciled", "work/hold_paths", "work/take"):
                if (state / name).exists():
                    (state / name).chmod(0o600)


def test_us_board_manifest_read_failure_preserves_index_and_creates_no_custody(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    _git_output(repo, "config", "user.name", "fixture")
    _git_output(repo, "config", "user.email", "fixture@example.invalid")
    held = b"old\n" + b"R" * 60
    board = repo / "data/us_board_ledger/snapshots.jsonl"
    board.write_bytes(held)
    projection = repo / "data/us_board_ledger/projection.json"
    projection.write_text("{}\n")
    _git_output(repo, "add", "data/us_board_ledger")
    before_index = _git_output(repo, "write-tree")
    before_main = _git_output(bare, "rev-parse", "main")
    env = _hold_env(tmp_path, "1304")
    result = subprocess.run(
        ["bash", "-c",
         '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\n'
         'cat() { case "${1:-}" in */work/entries) command head -n 1 "$1"; return 61 ;; esac; command cat "$@"; }\n'
         'rc=0\npush_hold_oversize_staged "data/us_board_ledger" || rc=$?\nexit "$rc"\n'],
        cwd=repo, env={**os.environ, "GITHUB_WORKSPACE": str(REPO_ROOT), **env},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert _hold_refs(bare) == []
    assert _git_output(repo, "write-tree") == before_index
    assert _git_output(bare, "rev-parse", "main") == before_main
    assert board.read_bytes() == held
    assert projection.read_text() == "{}\n"


def test_us_board_settlement_cannot_delete_custody_using_stale_unwriteable_evidence(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"R" * 60
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "1305"))
    assert first.returncode == 1, first.stdout + first.stderr
    [ref] = _hold_refs(bare)
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1306")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1306.us_board_ledgers"
    stale = state / "pushed_names"
    stale.write_text("data/us_board_ledger/snapshots.jsonl\n")
    stale.chmod(0o400)
    before_main = _git_output(bare, "rev-parse", "main")
    before_index = _git_output(lane, "write-tree")
    try:
        assert not os.access(stale, os.W_OK)
        result = subprocess.run(
            ["bash", "-c",
             '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\n'
             'rc=0\npush_hold_settle || rc=$?\nexit "$rc"\n'],
            cwd=lane, env={**os.environ, "GITHUB_WORKSPACE": str(REPO_ROOT), **env},
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 2, result.stdout + result.stderr
        assert "fresh custody retirement evidence" in result.stdout
        assert _hold_refs(bare) == [ref]
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held
        assert _git_output(bare, "rev-parse", "main") == before_main
        assert _git_output(lane, "write-tree") == before_index
        assert (lane / "data/us_board_ledger/snapshots.jsonl").read_bytes() == held
        assert "settlement" in (state / "unreconciled").read_text()
    finally:
        stale.chmod(0o600)


def test_us_board_recovery_unreadable_entries_cannot_retire_custody(tmp_path):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"R" * 60
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "1307"))
    assert first.returncode == 1, first.stdout + first.stderr
    [ref] = _hold_refs(bare)
    lane = _clone_of(bare, tmp_path / "next-lane")
    before_main = _git_output(bare, "rev-parse", "main")
    before_index = _git_output(lane, "write-tree")
    env = _hold_env(tmp_path, "1308")
    real_mkdir = subprocess.run(["which", "mkdir"], capture_output=True, text=True, check=True).stdout.strip()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    wrapper = fake_bin / "mkdir"
    wrapper.write_text(
        "#!/bin/bash\n"
        '"$REAL_MKDIR" "$@" || exit "$?"\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in */work/rb.*)\n'
        '    n=${arg##*.}; chmod 000 "$(dirname "$arg")/ent.$n" ;;\n'
        '  esac\n'
        'done\n'
    )
    wrapper.chmod(0o755)
    env.update({"PATH": f"{fake_bin}:{os.environ['PATH']}", "REAL_MKDIR": real_mkdir})
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1308.us_board_ledgers"
    try:
        result = _run_us_board_commit(lane, "--recover", **env)
        assert result.returncode == 1, result.stdout + result.stderr
        assert _hold_refs(bare) == [ref]
        assert _git_output(bare, "rev-parse", "main") == before_main
        assert _git_output(lane, "write-tree") == before_index
        assert (lane / "data/us_board_ledger/snapshots.jsonl").read_text() == "old\n"
        assert (state / "unreconciled").read_text().strip()
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held
    finally:
        for path in (state / "work").glob("ent.*"):
            path.chmod(0o600)


def _q1_existing_hold(tmp_path, run_id, extra=None):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"R" * 60
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    if extra:
        for rel, payload in extra.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_bytes(payload)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, run_id))
    assert first.returncode == 1, first.stdout + first.stderr
    [ref] = _hold_refs(bare)
    return bare, ref, held


def test_us_board_q1_changed_filename_does_not_prove_held_rows_landed(tmp_path):
    bare, ref, held = _q1_existing_hold(tmp_path, "1401")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1402", PUSH_BLOB_LIMIT="1000000")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    replacement = b"old\ndifferent_new_row\n"
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(replacement)

    result = _run_us_board_commit(lane, **env)

    assert _hold_refs(bare) == [ref], result.stdout + result.stderr
    assert result.returncode != 0
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == replacement


def test_us_board_q1_reheld_filename_does_not_prove_prior_bytes_preserved(tmp_path):
    bare, ref, held = _q1_existing_hold(tmp_path, "1411")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1412")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    replacement = b"old\n" + b"S" * 60
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(replacement)

    result = _run_us_board_commit(lane, **env)

    refs = _hold_refs(bare)
    assert ref in refs, result.stdout + result.stderr
    assert result.returncode != 0
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held


def test_us_board_q1_false_lineage_cannot_skip_the_only_copy_of_prior_rows(tmp_path):
    bare, ref, held = _q1_existing_hold(tmp_path, "1421")
    _reject_ref(bare, "refs/heads/main")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1422")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    replacement = b"old\n" + b"S" * 60
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(replacement)
    (lane / "data/us_sector_rotation/latest.json").write_text("rotation\n")
    result = _run_us_board_commit(lane, **env)
    assert result.returncode != 0
    refs = _hold_refs(bare)
    assert len(refs) == 2 and ref in refs
    (bare / "hooks/pre-receive").unlink()
    next_lane = _clone_of(bare, tmp_path / "fresh-recovery")
    next_env = _hold_env(tmp_path, "1423", PUSH_BLOB_LIMIT="1000000")

    recovered = _run_us_board_commit(next_lane, "--recover", **next_env)

    assert recovered.returncode != 0, recovered.stdout + recovered.stderr
    assert _hold_refs(bare) == refs
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held
    blocked = _run_us_board_commit(next_lane, **next_env)
    assert blocked.returncode != 0
    assert _hold_refs(bare) == refs


def test_us_board_q1_successor_must_preserve_every_predecessor_entry(tmp_path):
    projection = "site/factordata/us_board_track.json"
    projection_bytes = b'{"frozen_value":17}\n'
    bare, ref, held = _q1_existing_hold(tmp_path, "1431", {projection: projection_bytes})
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1432")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    assert (lane / projection).read_bytes() == projection_bytes
    (lane / projection).unlink()
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(held + b"next-row\n")

    result = _run_us_board_commit(lane, **env)

    assert ref in _hold_refs(bare), result.stdout + result.stderr
    assert result.returncode != 0
    entries, _ = _manifest(bare, ref)
    by_path = {entry["path"]: entry for entry in entries}
    assert _rebuild(bare, ref, by_path[projection]) == projection_bytes
    assert _rebuild(bare, ref, by_path["data/us_board_ledger/snapshots.jsonl"]) == held


def test_us_board_q1_changed_projection_values_cannot_retire_original_custody(tmp_path):
    projection = "site/factordata/us_board_track.json"
    frozen = b'{"frozen_value":17}\n'
    bare, ref, held = _q1_existing_hold(tmp_path, "1441", {projection: frozen})
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1442", PUSH_BLOB_LIMIT="1000000")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(held + b"next-row\n")
    (lane / projection).write_bytes(b'{"frozen_value":99}\n')

    result = _run_us_board_commit(lane, **env)

    assert _hold_refs(bare) == [ref], result.stdout + result.stderr
    assert result.returncode != 0
    entries, _ = _manifest(bare, ref)
    by_path = {entry["path"]: entry for entry in entries}
    assert _rebuild(bare, ref, by_path[projection]) == frozen


def _q1_seed_lineage_ref(bare, source_ref, target_ref, from_refs):
    manifest = _git_bytes(bare, "cat-file", "blob", f"{source_ref}:MANIFEST").decode()
    lines = [line for line in manifest.splitlines() if not line.startswith("from\t")]
    manifest = "\n".join(lines + [f"from\t{ref}" for ref in from_refs]) + "\n"
    sha = subprocess.run(
        ["git", "-C", str(bare), "hash-object", "-w", "--stdin"],
        input=manifest.encode(), capture_output=True, check=True,
    ).stdout.decode().strip()
    entries = _git_output(bare, "ls-tree", source_ref).splitlines()
    entries = [f"100644 blob {sha}\tMANIFEST" if line.endswith("\tMANIFEST") else line for line in entries]
    tree = subprocess.run(
        ["git", "-C", str(bare), "mktree"],
        input=("\n".join(entries) + "\n").encode(), capture_output=True, check=True,
    ).stdout.decode().strip()
    _git_output(bare, "config", "user.name", "custody-fixture")
    _git_output(bare, "config", "user.email", "fixture@example.invalid")
    commit = _git_output(bare, "commit-tree", tree, "-m", "local lineage fixture")
    _git_output(bare, "update-ref", target_ref, commit)
    return commit


@pytest.mark.parametrize("cycle", ["self", "mutual"])
def test_us_board_q1_lineage_cycles_cannot_claim_success_without_a_terminal(tmp_path, cycle):
    bare, original_ref, held = _q1_existing_hold(tmp_path, "1451")
    a = "refs/heads/push-hold/us_board_ledgers/cycle-a"
    b = "refs/heads/push-hold/us_board_ledgers/cycle-b"
    _q1_seed_lineage_ref(bare, original_ref, a, [a if cycle == "self" else b])
    if cycle == "mutual":
        _q1_seed_lineage_ref(bare, original_ref, b, [a])
    _git_output(bare, "update-ref", "-d", original_ref)
    refs = _hold_refs(bare)
    lane = _clone_of(bare, tmp_path / "next-lane")
    before_main = _git_output(bare, "rev-parse", "main")
    env = _hold_env(tmp_path, "1452")

    result = _run_us_board_commit(lane, "--recover", **env)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "lineage cycle" in result.stdout
    assert _hold_refs(bare) == refs
    assert _git_output(bare, "rev-parse", "main") == before_main
    assert (lane / "data/us_board_ledger/snapshots.jsonl").read_bytes() == b"old\n"
    for ref in refs:
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held


def test_us_board_q1_three_generation_lineage_recovers_terminal_and_retires_all(tmp_path):
    bare, original_ref, held = _q1_existing_hold(tmp_path, "1461")
    _reject_ref(bare, "refs/heads/main")
    payload = held
    for number, run_id in enumerate(["1462", "1463"], start=2):
        lane = _clone_of(bare, tmp_path / f"lane-{number}")
        env = _hold_env(tmp_path, run_id)
        recovery = _run_us_board_commit(lane, "--recover", **env)
        assert recovery.returncode == 0, recovery.stdout + recovery.stderr
        assert (lane / "data/us_board_ledger/snapshots.jsonl").read_bytes() == payload
        payload += f"\nrow-{number}\n".encode()
        (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(payload)
        (lane / "data/us_sector_rotation/latest.json").write_text(f"rotation-{number}\n")
        attempt = _run_us_board_commit(lane, **env)
        assert attempt.returncode != 0
    refs = _hold_refs(bare)
    assert len(refs) == 3 and original_ref in refs
    (bare / "hooks/pre-receive").unlink()
    final = _clone_of(bare, tmp_path / "final-lane")
    env = _hold_env(tmp_path, "1464", PUSH_BLOB_LIMIT="1000000")

    recovery = _run_us_board_commit(final, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    assert (final / "data/us_board_ledger/snapshots.jsonl").read_bytes() == payload
    landed = _run_us_board_commit(final, **env)

    assert landed.returncode == 0, landed.stdout + landed.stderr
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == payload
    assert _hold_refs(bare) == []


@pytest.mark.parametrize("record_fault", ["unbound", "conflicting"])
def test_us_board_q1_retirement_rejects_unbound_or_conflicting_state_identity(tmp_path, record_fault):
    bare, ref, held = _q1_existing_hold(tmp_path, "1471")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1472")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1472.us_board_ledgers"
    record = state / "recovered"
    original = record.read_text()
    fields = original.splitlines()[0].split("\t")
    assert len(fields) == 3
    if record_fault == "unbound":
        record.write_text("\t".join(fields[:2]) + "\n")
    else:
        conflicting = fields[:2] + [_git_output(bare, "rev-parse", "main")]
        record.write_text(original + "\t".join(conflicting) + "\n")
    before_main = _git_output(bare, "rev-parse", "main")

    result = run_sh(
        f'. "{REPO_ROOT}/scripts/ci/push_hold.sh"\n'
        'push_hold_settle "data/us_board_ledger" "data/us_sector_rotation"\n',
        env=env, cwd=lane,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert _hold_refs(bare) == [ref]
    assert _git_output(bare, "rev-parse", "main") == before_main
    assert (state / "unreconciled").read_text().strip()
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held


def test_us_board_q1_settlement_rebuilds_proof_after_transient_work_is_removed(tmp_path):
    import shutil
    bare, ref, held = _q1_existing_hold(tmp_path, "1481")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1482", PUSH_BLOB_LIMIT="1000000")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1482.us_board_ledgers"
    shutil.rmtree(state / "work")
    payload = held + b"\nnext-row\n"
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(payload)

    result = _run_us_board_commit(lane, **env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _hold_refs(bare) == []
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == payload


def test_us_board_q1_an_unpublished_local_commit_is_not_retirement_evidence(tmp_path):
    bare, ref, held = _q1_existing_hold(tmp_path, "1491")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1492")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    before_main = _git_output(bare, "rev-parse", "main")
    _git_output(lane, "add", "data/us_board_ledger/snapshots.jsonl")
    _git_output(lane, "commit", "-q", "-m", "local-only recovered bytes")

    result = run_sh(
        f'. "{REPO_ROOT}/scripts/ci/push_hold.sh"\n'
        'push_hold_settle "data/us_board_ledger" "data/us_sector_rotation"\n',
        env=env, cwd=lane,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert _hold_refs(bare) == [ref]
    assert _git_output(bare, "rev-parse", "main") == before_main
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held


@pytest.mark.parametrize("change", ["drop_duplicate", "reorder"])
def test_us_board_q1_prefix_proof_preserves_duplicate_multiplicity_and_order(tmp_path, change):
    bare, repo = _us_board_clone(tmp_path)
    held = b"old\n" + b"A\n" * 30 + b"B\n"
    (repo / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    first = _run_us_board_commit(repo, **_hold_env(tmp_path, "1501"))
    assert first.returncode == 1, first.stdout + first.stderr
    [ref] = _hold_refs(bare)
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1502", PUSH_BLOB_LIMIT="1000000")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    replacement = b"old\n" + b"A\n" * 29 + b"B\n" if change == "drop_duplicate" else b"old\nB\n" + b"A\n" * 30
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(replacement)

    result = _run_us_board_commit(lane, **env)

    assert result.returncode != 0
    assert _hold_refs(bare) == [ref]
    entries, _ = _manifest(bare, ref)
    assert _rebuild(bare, ref, entries[0]) == held


def test_us_board_q1_retirement_lease_preserves_a_concurrently_moved_ref(tmp_path):
    bare, ref, held = _q1_existing_hold(tmp_path, "1511")
    original_commit = _git_output(bare, "rev-parse", ref)
    collision_commit = _git_output(bare, "rev-parse", "main")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1512", PUSH_BLOB_LIMIT="1000000")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    hook = lane / ".git/hooks/pre-push"
    hook.write_text(
        "#!/bin/bash\n"
        "while read local_ref local_sha remote_ref remote_sha; do\n"
        f'  if [ "$remote_ref" = "{ref}" ] && [ "$local_sha" = "{"0" * 40}" ]; then\n'
        f'    git --git-dir="{bare}" update-ref "{ref}" "{collision_commit}" "{original_commit}" || exit 1\n'
        "  fi\n"
        "done\n"
    )
    hook.chmod(0o755)
    payload = held + b"\nnext-row\n"
    (lane / "data/us_board_ledger/snapshots.jsonl").write_bytes(payload)

    result = _run_us_board_commit(lane, **env)

    assert result.returncode != 0
    assert _git_output(bare, "rev-parse", ref) == collision_commit
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == payload
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1512.us_board_ledgers"
    assert original_commit in (state / "recovered").read_text()
    assert (state / "unreconciled").read_text().strip()


@pytest.mark.parametrize("destinations", ["self", "mutual", "surviving", "conflicting"])
def test_us_board_q1_retirement_requires_a_surviving_custody_destination(tmp_path, destinations):
    bare, ref, held = _q1_existing_hold(tmp_path, "1521")
    lane = _clone_of(bare, tmp_path / "next-lane")
    env = _hold_env(tmp_path, "1522")
    recovery = _run_us_board_commit(lane, "--recover", **env)
    assert recovery.returncode == 0, recovery.stdout + recovery.stderr
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1522.us_board_ledgers"
    original = (state / "recovered").read_text()
    ref2 = "refs/heads/push-hold/us_board_ledgers/independent-successor"
    if destinations in ("mutual", "surviving"):
        commit2 = _q1_seed_lineage_ref(bare, ref, ref2, [])
        _git_output(lane, "fetch", "-q", "origin", commit2)
        successor = "".join(
            f"{ref2}\t{line.split(chr(9))[1]}\t{commit2}\n"
            for line in original.splitlines()
        )
        (state / "held").write_text(original + successor)
        if destinations == "mutual":
            (state / "recovered").write_text(original + successor)
    elif destinations == "conflicting":
        fields = original.splitlines()[0].split("\t")
        fields[2] = _git_output(bare, "rev-parse", "main")
        (state / "held").write_text("\t".join(fields) + "\n")
    else:
        (state / "held").write_text(original)
    before_main = _git_output(bare, "rev-parse", "main")
    before_refs = _hold_refs(bare)

    result = run_sh(
        f'. "{REPO_ROOT}/scripts/ci/push_hold.sh"\n'
        'push_hold_settle "data/us_board_ledger" "data/us_sector_rotation"\n',
        env=env, cwd=lane,
    )

    assert _git_output(bare, "rev-parse", "main") == before_main
    if destinations == "surviving":
        assert result.returncode == 0, result.stdout + result.stderr
        assert _hold_refs(bare) == [ref2]
        entries, _ = _manifest(bare, ref2)
        assert _rebuild(bare, ref2, entries[0]) == held
    else:
        assert result.returncode == 2, result.stdout + result.stderr
        assert _hold_refs(bare) == before_refs
        assert (state / "unreconciled").read_text().strip()
        entries, _ = _manifest(bare, ref)
        assert _rebuild(bare, ref, entries[0]) == held


def test_us_board_q1_topology_read_failure_cannot_count_a_terminal_repeatedly(tmp_path):
    bare, original_ref, held = _q1_existing_hold(tmp_path, "1531")
    a = "refs/heads/push-hold/us_board_ledgers/cycle-a"
    b = "refs/heads/push-hold/us_board_ledgers/cycle-b"
    c = "refs/heads/push-hold/us_board_ledgers/terminal-c"
    _q1_seed_lineage_ref(bare, original_ref, a, [b])
    _q1_seed_lineage_ref(bare, original_ref, b, [a])
    _q1_seed_lineage_ref(bare, original_ref, c, [])
    _git_output(bare, "update-ref", "-d", original_ref)
    lane = _clone_of(bare, tmp_path / "next-lane")
    fakebin = tmp_path / "grep-bin"
    fakebin.mkdir()
    real_grep = shutil.which("grep")
    assert real_grep
    log = tmp_path / "topology-reads.log"
    interceptor = fakebin / "grep"
    interceptor.write_text(
        "#!/bin/bash\n"
        'case "$*" in\n'
        f'  */topo_done) printf "injected-read-error\\n" >> {shlex.quote(str(log))}; exit 2 ;;\n'
        "esac\n"
        f'exec {shlex.quote(real_grep)} "$@"\n'
    )
    interceptor.chmod(0o755)
    env = _hold_env(tmp_path, "1532", PATH=f"{fakebin}:{os.environ['PATH']}")
    before_refs = _hold_refs(bare)

    result = _run_us_board_commit(lane, "--recover", **env)

    assert log.read_text().splitlines()
    assert result.returncode != 0, result.stdout + result.stderr
    assert _hold_refs(bare) == before_refs
    assert (lane / "data/us_board_ledger/snapshots.jsonl").read_bytes() == b"old\n"
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1532.us_board_ledgers"
    assert (state / "unreconciled").read_text().strip()


@pytest.mark.parametrize(
    "mode,admitted",
    [
        ("accepted_client_failure", True),
        ("confirmed_unchanged", True),
        ("moved_ref", False),
        ("unreadable_after_success", False),
        ("unreadable_after_failure", False),
        ("malformed_readback", False),
    ],
)
def test_us_board_q1_retirement_reconciles_every_delete_outcome(tmp_path, mode, admitted):
    bare, ref, held = _q1_existing_hold(tmp_path, "1541")
    original_commit = _git_output(bare, "rev-parse", ref)
    old_main = _git_output(bare, "rev-parse", "main")
    publisher = _clone_of(bare, tmp_path / "published-lane")
    _git_output(publisher, "config", "user.name", "custody-fixture")
    _git_output(publisher, "config", "user.email", "fixture@example.invalid")
    (publisher / "data/us_board_ledger/snapshots.jsonl").write_bytes(held)
    _git_output(publisher, "add", "data/us_board_ledger/snapshots.jsonl")
    _git_output(publisher, "commit", "-q", "-m", "publish exact held bytes")
    _git_output(publisher, "push", "-q", "origin", "HEAD:main")
    lane = _clone_of(bare, tmp_path / "next-lane")
    log = tmp_path / "retirement-commands.log"
    marker = tmp_path / "retirement-attempted"
    fakebin = _custody_git_interceptor(
        tmp_path,
        r"""
        if [ "$1" = push ]; then
          for arg in "$@"; do
            if [ "$arg" = ":$RETIRE_REF" ]; then
              printf 'push\n' >> "$RETIRE_LOG"
              : > "$RETIRE_MARK"
              case "$RETIRE_MODE" in
                accepted_client_failure)
                  "$REAL_GIT" "$@" || exit $?
                  exit 75 ;;
                unreadable_after_success)
                  "$REAL_GIT" "$@"
                  exit $? ;;
                moved_ref)
                  "$REAL_GIT" -C "$RETIRE_BARE" update-ref "$RETIRE_REF" "$RETIRE_OLD_MAIN" "$RETIRE_COMMIT"
                  exit 75 ;;
                *) exit 75 ;;
              esac
            fi
          done
        fi
        if [ "$1" = ls-remote ] && [ -f "$RETIRE_MARK" ]; then
          for arg in "$@"; do
            if [ "$arg" = "$RETIRE_REF" ]; then
              printf 'read\n' >> "$RETIRE_LOG"
              case "$RETIRE_MODE" in
                unreadable_after_success|unreadable_after_failure) exit 73 ;;
                malformed_readback) printf 'not-a-ref-receipt\n'; exit 0 ;;
              esac
            fi
          done
        fi
        """,
    )
    env = _hold_env(
        tmp_path, "1542", PATH=f"{fakebin}:{os.environ['PATH']}",
        RETIRE_REF=ref, RETIRE_COMMIT=original_commit, RETIRE_OLD_MAIN=old_main,
        RETIRE_BARE=str(bare), RETIRE_LOG=str(log), RETIRE_MARK=str(marker),
        RETIRE_MODE=mode,
    )

    result = _run_us_board_commit(lane, "--recover", **env)

    assert log.read_text().splitlines() == ["push", "read"]
    assert (result.returncode == 0) is admitted, result.stdout + result.stderr
    assert _git_bytes(bare, "cat-file", "blob", "main:data/us_board_ledger/snapshots.jsonl") == held
    if mode in ("accepted_client_failure", "unreadable_after_success"):
        assert _hold_refs(bare) == []
    elif mode == "moved_ref":
        assert _git_output(bare, "rev-parse", ref) == old_main
    else:
        assert _git_output(bare, "rev-parse", ref) == original_commit
    state = Path(env["RUNNER_TEMP"]) / "push_hold.1542.us_board_ledgers"
    if not admitted:
        assert (state / "unreconciled").read_text().strip()
