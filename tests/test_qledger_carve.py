"""GH001 qledger carve-out shared helper — scripts/ci/qledger_carve.sh.

GitHub rejects any push that introduces a blob > 104,857,600 B (GH001).
data/qledger/claims.jsonl sits at that limit on main and grows on every nightly
runner. From 2026-10-21 every wholesale `git add data/` committer was rejected
WHOLE (run 40803269874: engine "commit engine outputs", collect_tail "commit
tail data", stock_briefs — "File data/qledger/claims.jsonl is 146.50 MB; this
exceeds GitHub's file size limit of 100.00 MB"), which is how the curated US
candidate tier, the regime update and the rendered site stopped reaching main.
PR #9556 carved the ledger out of the `collect` market commit only; the helper
under test extends the same accepted semantics (custody snapshot, unstage,
verified park, restore on exit) to the other committers.

These tests run the helper in real git repositories, including a rebase + push
against a bare origin whose pre-receive hook enforces the GH001 blob limit, so
the carve is proven against the exact rejection it exists to prevent.
"""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "ci" / "qledger_carve.sh"
ENGINE = ROOT / "scripts" / "ci" / "daily_engine_commit_outputs.sh"
DAILY = ROOT / ".github" / "workflows" / "daily.yml"

LIMIT = 104857600
MARGIN = 1048576
SOURCE_LINE = '. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_carve.sh"'

# GitHub GH001 emulation for a bare origin: refuse a push introducing a blob
# larger than the limit. Quarantined objects are visible to pre-receive.
PRE_RECEIVE = textwrap.dedent(
    r"""#!/usr/bin/env bash
    limit=104857600
    bad=0
    zero=0000000000000000000000000000000000000000
    while read -r old new ref; do
      [ "$new" = "$zero" ] && continue
      if [ "$old" = "$zero" ]; then range="$new"; else range="$old..$new"; fi
      while read -r type size rest; do
        if [ "$type" = blob ] && [ "$size" -gt "$limit" ]; then
          echo "remote: error: File $rest is $size bytes; this exceeds the file size limit of $limit" >&2
          bad=1
        fi
      done < <(git rev-list --objects "$range" | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)')
    done
    if [ "$bad" -ne 0 ]; then echo "remote: error: GH001: Large files detected." >&2; exit 1; fi
    exit 0
    """
)


def _env(tmp_path: Path) -> dict[str, str]:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "GITHUB_WORKSPACE": str(ROOT),
    }
    for k, v in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }.items():
        env.setdefault(k, v)
    return env


def _git(repo: Path, *args: str, env: dict[str, str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=env, check=check, capture_output=True, text=True,
    )
    return proc.stdout.strip()


def _bash(repo: Path, script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=repo, env=env, capture_output=True, text=True, timeout=300,
    )


def _grow(path: Path, size: int) -> None:
    """Make `path` exactly `size` bytes — sparse, so no real MB lands on disk."""
    with open(path, "r+b") as f:
        f.seek(0, 2)
        f.write(b'{"claim_id":"c1"}\n')
        f.truncate(size)


def _size(path: Path) -> int:
    return path.stat().st_size


def _seed(tmp_path: Path, env: dict[str, str]) -> tuple[Path, Path]:
    """A bare origin with the GH001 hook and a lane clone holding the base tree."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(PRE_RECEIVE)
    hook.chmod(0o755)
    repo = tmp_path / "lane"
    subprocess.run(["git", "clone", "-q", str(bare), str(repo)], check=True, env=env)
    _git(repo, "config", "user.name", "t", env=env)
    _git(repo, "config", "user.email", "t@t", env=env)
    for rel, body in {
        "data/qledger/claims.jsonl": b'{"claim_id":"c0"}\n',
        "data/qledger/grades.jsonl": b'{"grade_id":"g0"}\n',
        "site/qledger/track_record.json": b"{}",
        "data/us_prophet_rank/candidates/2026-10.parquet": b"curated-v1",
        "site/index.html": b"<html>v1</html>",
    }.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    _git(repo, "add", "data", "site", env=env)
    _git(repo, "commit", "-q", "-m", "base", env=env)
    _git(repo, "push", "-q", "origin", "main", env=env)
    return repo, bare


def _staged(repo: Path, env: dict[str, str]) -> list[str]:
    return [l for l in _git(repo, "diff", "--cached", "--name-only", env=env).splitlines() if l]


# ── helper unit behaviour ─────────────────────────────────────────────────────

def test_helper_is_sourceable_and_declares_the_github_limit():
    text = HELPER.read_text()
    assert "QLEDGER_CARVE_LIMIT=104857600" in text
    assert "QLEDGER_CARVE_MARGIN=1048576" in text
    assert "set -e" not in text.splitlines()[0:5], "a sourced helper must not change the caller's shell options"
    assert subprocess.run(["bash", "-n", str(HELPER)], capture_output=True).returncode == 0


@pytest.mark.parametrize("size,carved", [(LIMIT - MARGIN + 1, True), (LIMIT - MARGIN, False)])
def test_carve_threshold_matches_the_collect_carve(tmp_path, size, carved):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", size)
    (repo / "data" / "us_prophet_rank" / "candidates" / "2026-10.parquet").write_bytes(b"curated-v2")
    _git(repo, "add", "data/", "site/", env=env)
    proc = _bash(repo, f'. "{HELPER}"; qledger_carve_staged; echo "rc=$? carved=$QLEDGER_CARVED"', env)
    assert proc.returncode == 0, proc.stderr
    assert f"carved={'true' if carved else 'false'}" in proc.stdout
    staged = _staged(repo, env)
    assert "data/us_prophet_rank/candidates/2026-10.parquet" in staged
    assert ("data/qledger/claims.jsonl" in staged) is (not carved)


def test_carve_unstages_parks_restores_and_keeps_a_custody_snapshot(tmp_path):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    claims = repo / "data" / "qledger" / "claims.jsonl"
    head_size = _size(claims)
    _grow(claims, LIMIT + 4096)
    (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
    (repo / "site" / "index.html").write_bytes(b"<html>v2</html>")
    _git(repo, "add", "data/", "site/", env=env)
    script = f'''
        . "{HELPER}"
        qledger_carve_staged; rc=$?
        echo "rc=$rc carved=$QLEDGER_CARVED snapshot=$QLEDGER_SNAPSHOT"
        echo "staged=$(git diff --cached --name-only | tr '\\n' ' ')"
        echo "parked_size=$(wc -c < data/qledger/claims.jsonl | tr -d ' ')"
        echo "parked_track=$(cat site/qledger/track_record.json)"
    '''
    proc = _bash(repo, script, env)
    assert proc.returncode == 0, proc.stderr
    out = dict(kv.split("=", 1) for kv in proc.stdout.replace("\n", " ").split() if "=" in kv)
    assert out["rc"] == "0" and out["carved"] == "true"
    snapshot = out["snapshot"]
    assert len(snapshot) >= 40
    # (2) unstaged — the site change still publishes, neither qledger plane does
    assert "site/index.html" in out["staged"]
    assert "qledger" not in out["staged"]
    # (3) parked at HEAD during the push window
    assert int(out["parked_size"]) == head_size
    assert out["parked_track"] == "{}"
    # (5) restored byte-identical by the EXIT trap after the step ends
    assert _size(claims) == LIMIT + 4096
    assert (repo / "site" / "qledger" / "track_record.json").read_bytes() == b'{"n":1}'
    assert "restored byte-identical from snapshot" in proc.stdout
    assert "qledger carved out of this commit" in proc.stdout
    # (1) custody snapshot: unreachable from every ref, parent = HEAD, carries the bytes
    assert _git(repo, "rev-parse", f"{snapshot}^", env=env) == _git(repo, "rev-parse", "HEAD", env=env)
    assert snapshot not in _git(repo, "rev-list", "--all", env=env).split()
    assert int(_git(repo, "cat-file", "-s", f"{snapshot}:data/qledger/claims.jsonl", env=env)) == LIMIT + 4096
    # the restored worktree is dirty-unstaged for qledger, exactly as before the carve
    unstaged = _git(repo, "diff", "--name-only", "--", "data/qledger", "site/qledger", env=env).split()
    assert unstaged == ["data/qledger/claims.jsonl", "site/qledger/track_record.json"]


def test_only_the_ledger_changed_leaves_nothing_staged(tmp_path):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", LIMIT + 4096)
    _git(repo, "add", "data/", env=env)
    proc = _bash(repo, f'. "{HELPER}"; qledger_carve_staged; echo "carved=$QLEDGER_CARVED"', env)
    assert proc.returncode == 0 and "carved=true" in proc.stdout
    assert _staged(repo, env) == []
    assert _git(repo, "diff", "--cached", "--quiet", env=env, check=False) == ""


@pytest.mark.parametrize(
    "prior",
    [
        "trap 'echo PRIOR_TRAP_RAN' EXIT",
        "trap $'echo PRIOR_TRAP_RAN\\necho PRIOR_SECOND_LINE' EXIT",   # multi-line prior trap
        "trap 'echo \"PRIOR_TRAP_RAN it'\\''s quoted\"' EXIT",           # a quote inside the prior trap
    ],
    ids=["one-line", "multi-line", "quoted"],
)
def test_restore_chains_a_pre_existing_exit_trap(tmp_path, prior):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", LIMIT + 4096)
    _git(repo, "add", "data/", env=env)
    proc = _bash(repo, f'''{prior}; . "{HELPER}"; qledger_carve_staged''', env)
    assert proc.returncode == 0, proc.stderr
    assert "PRIOR_TRAP_RAN" in proc.stdout
    if "SECOND_LINE" in prior:
        assert "PRIOR_SECOND_LINE" in proc.stdout, "a multi-line prior trap must be chained whole"
    assert "restored byte-identical from snapshot" in proc.stdout
    assert _size(repo / "data" / "qledger" / "claims.jsonl") == LIMIT + 4096


def test_snapshot_failure_withholds_and_leaves_index_untouched(tmp_path):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", LIMIT + 4096)
    _git(repo, "add", "data/", env=env)
    shim = tmp_path / "shim"
    shim.mkdir()
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True, text=True).stdout.strip()
    (shim / "git").write_text(f'#!/usr/bin/env bash\nif [ "$1" = commit-tree ]; then exit 1; fi\nexec "{real_git}" "$@"\n')
    (shim / "git").chmod(0o755)
    env2 = {**env, "PATH": f"{shim}:{env['PATH']}"}
    proc = _bash(repo, f'. "{HELPER}"; rc=0; qledger_carve_staged || rc=$?; echo "rc=$rc"', env2)
    assert "rc=2" in proc.stdout
    assert "qledger carve snapshot failed" in proc.stdout
    assert "data/qledger/claims.jsonl" in _staged(repo, env), "withhold must not unstage without custody"


# ── the rejection it prevents: rebase + push against a GH001-enforcing origin ──

def _push_script(carve: bool) -> str:
    carve_line = f'. "{HELPER}"; qledger_carve_staged || exit 0' if carve else ""
    return f'''
        git add data/ site/
        {carve_line}
        if git diff --cached --quiet; then echo "nothing to commit"; exit 0; fi
        git commit -q -m "data: nightly"
        git pull -q --rebase --autostash -X theirs origin main
        git push -q origin HEAD:refs/heads/main
        echo PUSHED
    '''


def test_without_the_carve_the_origin_rejects_the_whole_commit(tmp_path):
    env = _env(tmp_path)
    repo, bare = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", LIMIT + 4096)
    (repo / "data" / "us_prophet_rank" / "candidates" / "2026-10.parquet").write_bytes(b"curated-v2")
    proc = _bash(repo, _push_script(carve=False), env)
    assert proc.returncode != 0
    assert "GH001" in proc.stderr
    assert "PUSHED" not in proc.stdout
    assert _git(bare, "cat-file", "-p", "main:data/us_prophet_rank/candidates/2026-10.parquet", env=env) == "curated-v1"


def test_with_the_carve_the_market_commit_lands_and_the_bytes_come_back(tmp_path):
    env = _env(tmp_path)
    repo, bare = _seed(tmp_path, env)
    # a concurrent writer moves origin/main so the lane must really rebase
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True, env=env)
    (other / "site" / "index.html").write_bytes(b"<html>concurrent</html>")
    _git(other, "commit", "-q", "-am", "concurrent", env=env)
    _git(other, "push", "-q", "origin", "main", env=env)

    claims = repo / "data" / "qledger" / "claims.jsonl"
    _grow(claims, LIMIT + 4096)
    (repo / "data" / "us_prophet_rank" / "candidates" / "2026-10.parquet").write_bytes(b"curated-v2")
    proc = _bash(repo, _push_script(carve=True), env)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PUSHED" in proc.stdout
    # the market plane landed on top of the concurrent commit, without the ledger
    assert _git(bare, "cat-file", "-p", "main:data/us_prophet_rank/candidates/2026-10.parquet", env=env) == "curated-v2"
    assert _git(bare, "cat-file", "-p", "main:site/index.html", env=env) == "<html>concurrent</html>"
    assert int(_git(bare, "cat-file", "-s", "main:data/qledger/claims.jsonl", env=env)) < LIMIT
    # the runner keeps its grown ledger, dirty and unstaged, exactly as before
    assert _size(claims) == LIMIT + 4096
    assert _git(repo, "diff", "--name-only", "--", "data/qledger", env=env) == "data/qledger/claims.jsonl"
    assert _git(repo, "diff", "--cached", "--name-only", env=env) == ""


# ── wiring: every wholesale committer sources the helper before it commits ───

def test_engine_commit_script_carves_between_staging_and_the_locked_commit():
    text = ENGINE.read_text()
    assert SOURCE_LINE in text
    assert "qledger_carve_staged || exit 1" in text, "a lost engine commit must red the run"
    broad_add = text.index("git add data/ site/ reports/")
    carve = text.index("qledger_carve_staged || exit 1")
    empty_check = text.index('echo "no engine output changes"')
    locked_commit = text.index("commit-broad-candidate")
    assert broad_add < carve < empty_check < locked_commit


def _job_steps(job: str) -> list[dict]:
    return yaml.safe_load(DAILY.read_text())["jobs"][job]["steps"]


def _run_of(job: str, name_fragment: str) -> str:
    for step in _job_steps(job):
        if name_fragment in (step.get("name") or ""):
            return str(step.get("run") or "")
    raise AssertionError(f"{job}: no step named like {name_fragment!r}")


@pytest.mark.parametrize(
    "job,step,stage_line,commit_prefix",
    [
        ("collect_tail", "commit tail data", "git add data/ site/basketdata/", 'git commit -m "data: collect-tail accrual'),
        ("stock_briefs", "commit stock briefs", "git add data/qledger 2>/dev/null || true", 'git commit -m "stock-briefs:'),
    ],
)
def test_inline_wholesale_committers_carve_before_committing(job, step, stage_line, commit_prefix):
    run = _run_of(job, step)
    assert "${{" not in run
    call = f"{SOURCE_LINE}; qledger_carve_staged || exit 0"
    assert call in run, f"{job}: the carve must withhold-and-stay-green on a custody failure"
    assert run.index(stage_line) < run.index(call) < run.index(commit_prefix)


def test_collect_market_commit_keeps_its_own_accepted_carve():
    """#9556's inline carve in `collect` is accepted work; this change does not touch it."""
    run = _run_of("collect", "commit market data")
    assert 'echo "qledger_carved=true" >> "$GITHUB_OUTPUT"' in run
    assert "qledger_carve_staged" not in run


# ── custody after the push-loop rebase, a hard kill, a park failure, a new file ──

def test_restore_after_rebase_leaves_mains_qledger_changes_alone(tmp_path):
    """Reviewer finding (PR #10255 round 1): after the push loop's rebase HEAD is
    origin/main's tip; a whole-plane restore from the snapshot would delete a
    qledger file main added and revert one main changed. #9556's restore only
    writes back the paths THIS run's snapshot changed; the helper must match."""
    env = _env(tmp_path)
    repo, bare = _seed(tmp_path, env)
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True, env=env)
    (other / "data" / "qledger" / "upstream_added.json").write_bytes(b'{"from":"main"}')
    (other / "data" / "qledger" / "grades.jsonl").write_bytes(b'{"grade_id":"g1-from-main"}\n')
    _git(other, "add", "data/", env=env)
    _git(other, "commit", "-q", "-m", "main moved qledger", env=env)
    _git(other, "push", "-q", "origin", "main", env=env)

    claims = repo / "data" / "qledger" / "claims.jsonl"
    _grow(claims, LIMIT + 4096)
    (repo / "data" / "us_prophet_rank" / "candidates" / "2026-10.parquet").write_bytes(b"curated-v2")
    proc = _bash(repo, _push_script(carve=True), env)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PUSHED" in proc.stdout
    assert "custody LOST" not in proc.stdout
    # main's additions/changes survive the restore exactly as main has them ...
    assert (repo / "data" / "qledger" / "upstream_added.json").read_bytes() == b'{"from":"main"}'
    assert (repo / "data" / "qledger" / "grades.jsonl").read_bytes() == b'{"grade_id":"g1-from-main"}\n'
    # ... and only this run's grown ledger is dirty-unstaged
    assert _size(claims) == LIMIT + 4096
    assert _git(repo, "diff", "--name-only", "--", "data/qledger", "site/qledger", env=env).split() == ["data/qledger/claims.jsonl"]
    assert _git(repo, "diff", "--cached", "--name-only", env=env) == ""
    # the always() step afterwards has nothing to do: the trap's restore cleared the record
    after = _bash(repo, f'. "{HELPER}"; qledger_carve_restore_from_file', env)
    assert "no runner-local snapshot recorded" in after.stdout


def test_a_hard_kill_skips_the_trap_and_the_always_step_restores_from_the_record(tmp_path):
    """Reviewer finding (round 1): the EXIT trap never runs under SIGKILL (step
    timeout / job cancel). The carve records the snapshot id; the workflow's
    always() step restores from it in a fresh process."""
    env = {**_env(tmp_path), "RUNNER_TEMP": str(tmp_path / "runner_temp"), "GITHUB_RUN_ID": "424242"}
    (tmp_path / "runner_temp").mkdir()
    repo, _ = _seed(tmp_path, env)
    claims = repo / "data" / "qledger" / "claims.jsonl"
    head_size = _size(claims)
    _grow(claims, LIMIT + 4096)
    _git(repo, "add", "data/", env=env)
    killed = _bash(repo, f'. "{HELPER}"; qledger_carve_staged; kill -9 $$', env)
    assert killed.returncode == -9 or killed.returncode == 137
    assert "restored byte-identical" not in killed.stdout
    # parked at HEAD, bytes only in the unreachable snapshot + the record
    assert _size(claims) == head_size
    record = tmp_path / "runner_temp" / "qledger_carve_snapshot.424242"
    assert record.is_file() and len(record.read_text().strip()) >= 40
    restored = _bash(repo, f'. "{HELPER}"; qledger_carve_restore_from_file', env)
    assert restored.returncode == 0, restored.stderr
    assert "restored byte-identical from snapshot" in restored.stdout
    assert _size(claims) == LIMIT + 4096
    assert not record.exists(), "a complete restore clears the record so the step stays quiet"
    again = _bash(repo, f'. "{HELPER}"; qledger_carve_restore_from_file', env)
    assert "no runner-local snapshot recorded" in again.stdout and _size(claims) == LIMIT + 4096


def test_park_failure_withholds_and_still_puts_the_bytes_back(tmp_path):
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    claims = repo / "data" / "qledger" / "claims.jsonl"
    _grow(claims, LIMIT + 4096)
    _git(repo, "add", "data/", "site/", env=env)
    shim = tmp_path / "shim"
    shim.mkdir()
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True, text=True).stdout.strip()
    (shim / "git").write_text(f'#!/usr/bin/env bash\nif [ "$1" = restore ]; then exit 1; fi\nexec "{real_git}" "$@"\n')
    (shim / "git").chmod(0o755)
    env2 = {**env, "PATH": f"{shim}:{env['PATH']}"}
    proc = _bash(repo, f'. "{HELPER}"; rc=0; qledger_carve_staged || rc=$?; echo "rc=$rc carved=$QLEDGER_CARVED"; echo "staged=$(git diff --cached --name-only | tr \'\\n\' \' \')"', env2)
    assert "rc=2 carved=false" in proc.stdout
    assert "qledger park failed" in proc.stdout
    assert "qledger" not in proc.stdout.split("staged=")[1].splitlines()[0]
    # the EXIT trap was armed on the failure path: the grown bytes are back
    assert "restored byte-identical from snapshot" in proc.stdout
    assert _size(claims) == LIMIT + 4096


def test_a_new_qledger_file_is_carved_out_and_comes_back_untracked(tmp_path):
    env = _env(tmp_path)
    repo, bare = _seed(tmp_path, env)
    _grow(repo / "data" / "qledger" / "claims.jsonl", LIMIT + 4096)
    new = repo / "site" / "qledger" / "new_part.json"
    new.write_bytes(b'{"new":1}')
    (repo / "site" / "index.html").write_bytes(b"<html>v2</html>")
    proc = _bash(repo, _push_script(carve=True), env)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PUSHED" in proc.stdout
    assert _git(bare, "cat-file", "-p", "main:site/index.html", env=env) == "<html>v2</html>"
    assert _git(bare, "ls-tree", "--name-only", "main", "site/qledger/", env=env).split() == ["site/qledger/track_record.json"]
    assert new.read_bytes() == b'{"new":1}'
    assert "?? site/qledger/new_part.json" in _git(repo, "status", "--porcelain", "--", "site/qledger", env=env)


# ── wiring: the always() restore steps and the render-sync re-add ─────────────

def test_engine_job_restores_after_each_committer_step_even_when_killed():
    steps = _job_steps("engine")
    names = [s.get("name") or "" for s in steps]
    for committer in ("checkpoint core engine outputs to main", "commit engine outputs"):
        i = next(i for i, n in enumerate(names) if n.startswith(committer))
        assert steps[i]["run"] == "bash scripts/ci/daily_engine_commit_outputs.sh"
        nxt = steps[i + 1]
        assert nxt["name"].startswith("restore carved qledger bytes"), f"no always() restore after {committer!r}"
        assert str(nxt.get("if")).strip() == "always()"
        assert nxt["run"].strip() == ". scripts/ci/qledger_carve.sh; qledger_carve_restore_from_file"


def test_engine_render_sync_readd_keeps_the_carved_planes_out():
    text = ENGINE.read_text()
    readd = text.index("      git add site/\n      git add templates/ 2>/dev/null || true\n")
    guard = text.index('if [ "${QLEDGER_CARVED:-false}" = true ]; then git reset -q -- site/qledger data/qledger')
    clean = text.index("if push_staged_clean site/ templates/; then")
    assert readd < guard < clean
