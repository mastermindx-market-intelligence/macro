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
import re
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "ci" / "qledger_carve.sh"
ENGINE = ROOT / "scripts" / "ci" / "daily_engine_commit_outputs.sh"
DAILY = ROOT / ".github" / "workflows" / "daily.yml"
WORKFLOWS = ROOT / ".github" / "workflows"

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


# ── R-33 hold: the engine's staged set is one publication group ───────────────
#
# The engine stages thousands of outputs and cannot prove which source file and
# which site/ projection belong together, so everything it stages is one group:
# one blob over the limit holds all of it, in custody on origin, and the step is
# red. These tests run the committer's own lines against real repositories.

ENGINE_GROUP = "data site reports templates"
HOLD_PREFIX = "refs/heads/push-hold/engine/"
SOURCE_BYTES = b"old\n" + b"R" * 60  # 64 B: over the 50 B test limit, extends HEAD's "old\n"
DERIVED_BYTES = b'{"v":2}\n'  # 8 B: under it


def test_engine_commit_holds_after_the_heal_and_reds_every_clean_exit():
    """push_hold.sh is sourced, the hold runs after the carve and the conflict
    heal and before the locked commit, a blob over the limit after the rebase
    holds the whole candidate, and no clean exit can hide a hold."""
    text = ENGINE.read_text()
    retry_src = text.index('. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"')
    hold_src = text.index('. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_hold.sh"')
    assert retry_src < hold_src < text.index("engine_hold() {")
    assert f'ENGINE_GROUP="{ENGINE_GROUP}"' in text
    assert "PUSH_HOLD_KEEP_WORKTREE=1" in text
    carve = text.index("qledger_carve_staged || exit 1")
    empty = text.index('echo "no engine output changes"')
    heal = text.index("push_staged_heal data/ site/ reports/ templates/")
    hold = text.index("\nengine_hold\n")
    commit = text.index("commit-broad-candidate")
    assert carve < empty < heal < hold < commit, "marker bytes must never reach custody"
    accepted = text.index("COMMODITY_ACCEPTED=$(")
    post = text.index('if push_hold_staged_over "$COMMODITY_ACCEPTED"; then')
    candidate = text.index("qledger_push_candidate=$(")
    assert accepted < post < candidate
    assert 'git reset -q --soft "$COMMODITY_ACCEPTED" || exit 1\n      engine_hold\n' in text[post:candidate]
    red = "if push_hold_red; then exit 1; fi; exit 0"
    clean_exits = 0
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        if "exit 0" in line:
            assert red in line, f"a held file must not read as a clean run: {line}"
            clean_exits += 1
    assert clean_exits == 3
    assert f'push_won; push_hold_settle "$COMMODITY_ACCEPTED"; {red}' in text


def test_engine_commit_stages_only_paths_inside_its_hold_group():
    """A path staged outside the group is a membership the hold cannot prove:
    it would hold every staged path. Keep every `git add` inside the group."""
    members = ENGINE_GROUP.split()
    operands = []
    for line in ENGINE.read_text().splitlines():
        code = line.strip()
        if code.startswith("#") or "git add" not in code:
            continue
        for tok in code.split("git add", 1)[1].split():
            if tok.startswith(("2>", "||", "&&", ";")):
                break
            if not tok.startswith("-"):
                operands.append(tok)
    assert len(operands) >= 10
    outside = [tok for tok in operands if tok.split("/", 1)[0] not in members]
    assert outside == [], f"staged outside {ENGINE_GROUP}: {outside}"


def test_engine_job_recovers_its_held_group_before_any_engine_commit():
    steps = _job_steps("engine")
    runs = [str(step.get("run") or "") for step in steps]
    recover = [i for i, run in enumerate(runs) if "scripts/ci/push_hold.sh recover" in run]
    commits = [i for i, run in enumerate(runs) if "daily_engine_commit_outputs.sh" in run]
    assert len(recover) == 1 and len(commits) == 2
    assert recover[0] < commits[0]
    step = steps[recover[0]]
    assert "if" not in step and not step.get("continue-on-error")
    assert runs[recover[0]].startswith("git pull origin main && ")
    group = re.search(r'push_hold\.sh recover "([^"]+)"', runs[recover[0]]).group(1)
    assert group == ENGINE_GROUP
    assert re.search(r'^ENGINE_GROUP="([^"]+)"$', ENGINE.read_text(), re.M).group(1) == group


def _engine_hold_defs() -> str:
    text = ENGINE.read_text()
    start = text.index("ENGINE_GROUP=")
    end = text.index("\n}\n", text.index("engine_hold() {")) + 3
    return text[start:end]


def _hold_script(body: str) -> str:
    return (
        '. "$GITHUB_WORKSPACE/scripts/ci/push_retry.sh"\n'
        '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\n'
        f"{_engine_hold_defs()}\n{body}\n"
    )


def _hold_env(tmp_path: Path, run_id: str = "501", **extra: str) -> dict[str, str]:
    env = {k: v for k, v in _env(tmp_path).items() if not k.startswith("PUSH_")}
    rt = tmp_path / "rt"
    rt.mkdir(exist_ok=True)
    env.update({
        "PUSH_BLOB_LIMIT": "50",
        "PUSH_HOLD_PART": "20",
        "RUNNER_TEMP": str(rt),
        "GITHUB_RUN_ID": run_id,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_JOB": "engine",
        "GITHUB_STEP_SUMMARY": str(tmp_path / f"summary-{run_id}.md"),
    })
    env.update(extra)
    return env


def _pair_seed(tmp_path: Path, env: dict[str, str]) -> tuple[Path, Path]:
    repo, bare = _seed(tmp_path, env)
    for rel, body in {
        "data/x.jsonl": b"old\n",
        "site/x.json": b'{"v":1}\n',
        "data/gone.jsonl": b"bye\n",
    }.items():
        (repo / rel).write_bytes(body)
    _git(repo, "add", "data", "site", env=env)
    _git(repo, "commit", "-q", "-m", "pair base", env=env)
    _git(repo, "push", "-q", "origin", "main", env=env)
    return repo, bare


def _stage_pair(repo: Path, env: dict[str, str]) -> None:
    """A source row over the limit, its projection under it, and a deletion."""
    (repo / "data/x.jsonl").write_bytes(SOURCE_BYTES)
    (repo / "site/x.json").write_bytes(DERIVED_BYTES)
    (repo / "data/gone.jsonl").unlink()
    _git(repo, "add", "data", "site", env=env)


def _git_in(repo: Path, *args: str, data: bytes, env: dict[str, str]) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=env, input=data, check=True, capture_output=True,
    )
    return proc.stdout.decode().strip()


def _blob(repo: Path, spec: str, env: dict[str, str]) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", spec], cwd=repo, env=env, check=True, capture_output=True,
    ).stdout


def _custody_refs(bare: Path, env: dict[str, str]) -> list[str]:
    out = _git(bare, "for-each-ref", "--format=%(refname)", HOLD_PREFIX.rstrip("/"), env=env)
    return [line for line in out.splitlines() if line]


def _custody(bare: Path, ref: str, env: dict[str, str]) -> tuple[dict[str, bytes], list[str]]:
    """Each MANIFEST path with its bytes rebuilt from the custody tree, and the `from` refs."""
    manifest = _blob(bare, f"{ref}:MANIFEST", env).decode()
    assert manifest.startswith("push-hold/v1\n")
    rows: dict[str, bytes] = {}
    froms: list[str] = []
    for line in manifest.splitlines():
        parts = line.split("\t")
        if parts[0] == "from":
            froms.append(parts[1])
        if parts[0] != "entry":
            continue
        i, path, layout = parts[1], parts[2], parts[6]
        if layout == "blob":
            data = _blob(bare, f"{ref}:blobs/{i}", env)
        else:
            data = _blob(bare, f"{ref}:parts/{i}/base", env) if layout == "prefix" else b""
            names = _git(bare, "ls-tree", "--name-only", f"{ref}:parts/{i}", env=env).splitlines()
            for name in sorted(n for n in names if n and n != "base"):
                data += _blob(bare, f"{ref}:parts/{i}/{name}", env)
        rows[path] = data
    return rows, froms


def test_engine_hold_keeps_a_source_and_its_projection_together_when_only_the_source_is_over(tmp_path):
    """R-33(4): data/x.jsonl is over the limit, its site/ projection is not.
    Both are withheld with their exact bytes in custody on origin, the deletion
    in the group is not published either, nothing of the group stays staged,
    the step is red, the worktree keeps the bytes for the always() steps, and a
    carved file that is not staged is left alone."""
    env = _hold_env(tmp_path)
    repo, bare = _pair_seed(tmp_path, env)
    main_before = _git(bare, "rev-parse", "main", env=env)
    carved = repo / "reports" / "carved.jsonl"
    carved.parent.mkdir()
    carved.write_bytes(b"x" * 51)
    _stage_pair(repo, env)
    assert sorted(_staged(repo, env)) == ["data/gone.jsonl", "data/x.jsonl", "site/x.json"]

    done = _bash(repo, _hold_script('engine_hold\necho "engine_hold returned"'), env)

    assert done.returncode == 1, done.stdout + done.stderr
    assert "engine_hold returned" not in done.stdout
    assert "::error title=engine outputs withheld::" in done.stdout
    assert "::error title=withheld, not lost::data/x.jsonl is 64 B, over 50 B." in done.stdout
    assert (
        "::error title=withheld, not lost::site/x.json is 8 B, under the limit. "
        "Withheld with its group because data/x.jsonl is over the limit"
    ) in done.stdout
    assert "::error title=deletion withheld::data/gone.jsonl is deleted in a held group" in done.stdout
    assert _staged(repo, env) == []
    assert _git(bare, "rev-parse", "main", env=env) == main_before
    refs = _custody_refs(bare, env)
    assert len(refs) == 1 and refs[0].startswith(HOLD_PREFIX + "501-1-")
    rows, froms = _custody(bare, refs[0], env)
    assert rows == {"data/x.jsonl": SOURCE_BYTES, "site/x.json": DERIVED_BYTES}
    assert froms == []
    assert (repo / "data/x.jsonl").read_bytes() == SOURCE_BYTES
    assert (repo / "site/x.json").read_bytes() == DERIVED_BYTES
    assert not (repo / "data/gone.jsonl").exists()
    assert carved.read_bytes() == b"x" * 51
    summary = Path(env["GITHUB_STEP_SUMMARY"]).read_text()
    assert f"### Withheld, not lost: 3 staged paths held at `{refs[0]}`" in summary


def test_engine_hold_at_the_default_limit_leaves_every_staged_output_to_land(tmp_path):
    """No knob set: the limit is GitHub's 100 MiB, so a small run holds nothing."""
    env = _hold_env(tmp_path)
    del env["PUSH_BLOB_LIMIT"]
    repo, bare = _pair_seed(tmp_path, env)
    _stage_pair(repo, env)

    done = _bash(repo, _hold_script('engine_hold\necho "engine_hold returned"'), env)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "engine_hold returned" in done.stdout
    assert "::error" not in done.stdout
    assert sorted(_staged(repo, env)) == ["data/gone.jsonl", "data/x.jsonl", "site/x.json"]
    assert _custody_refs(bare, env) == []


def test_engine_second_checkpoint_holds_the_group_again_even_after_the_big_file_shrank(tmp_path):
    """The engine committer runs twice per job. Whatever the first run held, the
    second holds again in full, names the first ref in `from`, and publishes
    nothing of the group, even when no staged blob is over the limit any more."""
    env = _hold_env(tmp_path)
    repo, bare = _pair_seed(tmp_path, env)
    main_before = _git(bare, "rev-parse", "main", env=env)
    _stage_pair(repo, env)
    first = _bash(repo, _hold_script("engine_hold"), env)
    assert first.returncode == 1, first.stdout + first.stderr
    [ref1] = _custody_refs(bare, env)

    (repo / "data/x.jsonl").write_bytes(b"old\nshort\n")
    (repo / "site/late.json").write_bytes(b"{}\n")
    _git(repo, "add", "data", "site", env=env)
    second = _bash(repo, _hold_script('engine_hold\necho "engine_hold returned"'), env)

    assert second.returncode == 1, second.stdout + second.stderr
    assert "engine_hold returned" not in second.stdout
    assert "::error title=engine outputs withheld::" in second.stdout
    assert "site/late.json is 3 B, under the limit. Withheld with its group because" in second.stdout
    assert "was withheld earlier in this run" in second.stdout
    assert _staged(repo, env) == []
    assert _git(bare, "rev-parse", "main", env=env) == main_before
    refs = _custody_refs(bare, env)
    assert len(refs) == 2 and ref1 in refs
    [ref2] = [ref for ref in refs if ref != ref1]
    rows, froms = _custody(bare, ref2, env)
    assert rows == {
        "data/x.jsonl": b"old\nshort\n",
        "site/x.json": DERIVED_BYTES,
        "site/late.json": b"{}\n",
    }
    assert froms == [ref1]


@pytest.mark.parametrize("over", [True, False])
def test_engine_post_rebase_check_holds_the_whole_candidate_against_accepted_main(tmp_path, over):
    """After the rebase the candidate is committed. A blob over the limit in it
    moves HEAD back to the accepted main and holds every change of the run, the
    render-sync commit included. Under the limit, the candidate goes on."""
    text = ENGINE.read_text()
    start = text.index('    if push_hold_staged_over "$COMMODITY_ACCEPTED"; then')
    block = textwrap.dedent(text[start : text.index("    # This is the actual final candidate")])
    env = _hold_env(tmp_path)
    repo, bare = _pair_seed(tmp_path, env)
    accepted = _git(repo, "rev-parse", "HEAD", env=env)
    source = SOURCE_BYTES if over else b"old\nnew\n"
    (repo / "data/x.jsonl").write_bytes(source)
    (repo / "site/x.json").write_bytes(DERIVED_BYTES)
    _git(repo, "add", "data", "site", env=env)
    _git(repo, "commit", "-q", "-m", "engine: regime update", env=env)
    (repo / "site/index.html").write_bytes(b"<html>v2</html>")
    _git(repo, "add", "site", env=env)
    _git(repo, "commit", "-q", "-m", "render-sync", env=env)
    candidate = _git(repo, "rev-parse", "HEAD", env=env)

    done = _bash(repo, _hold_script(f'COMMODITY_ACCEPTED={accepted}\n{block}\necho "candidate goes on"'), env)

    if not over:
        assert done.returncode == 0, done.stdout + done.stderr
        assert "candidate goes on" in done.stdout
        assert _git(repo, "rev-parse", "HEAD", env=env) == candidate
        assert _custody_refs(bare, env) == []
        return
    assert done.returncode == 1, done.stdout + done.stderr
    assert "candidate goes on" not in done.stdout
    assert "::error title=engine outputs withheld::" in done.stdout
    assert "the hold did not take it" not in done.stdout
    assert _git(repo, "rev-parse", "HEAD", env=env) == accepted
    assert _staged(repo, env) == []
    [ref] = _custody_refs(bare, env)
    rows, _froms = _custody(bare, ref, env)
    assert rows == {
        "data/x.jsonl": SOURCE_BYTES,
        "site/x.json": DERIVED_BYTES,
        "site/index.html": b"<html>v2</html>",
    }
    assert (repo / "site/index.html").read_bytes() == b"<html>v2</html>"


def _recover(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return _bash(repo, f'bash "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh" recover "{ENGINE_GROUP}"', env)


@pytest.mark.parametrize("landed", [["data", "site"], ["data/x.jsonl"]])
def test_engine_recover_restores_the_pair_and_only_a_push_of_both_settles_the_ref(tmp_path, landed):
    env = _hold_env(tmp_path, run_id="601")
    repo, bare = _pair_seed(tmp_path, env)
    _stage_pair(repo, env)
    assert _bash(repo, _hold_script("engine_hold"), env).returncode == 1
    [ref] = _custody_refs(bare, env)

    nxt = tmp_path / "next"
    subprocess.run(["git", "clone", "-q", str(bare), str(nxt)], check=True, env=env)
    env2 = _hold_env(tmp_path, run_id="602")
    recovered = _recover(nxt, env2)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert "::error" not in recovered.stdout
    assert (nxt / "data/x.jsonl").read_bytes() == SOURCE_BYTES
    assert (nxt / "site/x.json").read_bytes() == DERIVED_BYTES
    assert (nxt / "data/gone.jsonl").read_bytes() == b"bye\n", "a deletion is not custody"
    paths = " ".join(landed)
    land = _bash(
        nxt,
        '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\n'
        'base=$(git rev-parse HEAD)\n'
        f"git add {paths}\n"
        'git commit -q -m land\n'
        'git push -q origin HEAD:main\n'
        'push_hold_settle "$base"\n'
        'if push_hold_red; then echo RED; fi\n',
        env2,
    )
    assert land.returncode == 0, land.stdout + land.stderr
    assert "RED" not in land.stdout
    if landed == ["data", "site"]:
        assert f"hold settled {ref}" in land.stdout
        assert _custody_refs(bare, env) == []
    else:
        assert f"::warning title=hold ref kept::{ref} has a path that is neither in the pushed commit nor held again" in land.stdout
        assert _custody_refs(bare, env) == [ref]


@pytest.mark.parametrize(
    "path, header, reason",
    [
        ("../escape.json", "push-hold/v1", "entry ../escape.json is not a plain repository path"),
        (".git/hooks/post-checkout", "push-hold/v1", "entry .git/hooks/post-checkout is not a plain repository path"),
        ("elsewhere/x.json", "push-hold/v1", "entry elsewhere/x.json belongs to no declared group"),
        ("site/x.json", "push-hold/v9", "manifest is not push-hold/v1"),
    ],
)
def test_engine_recover_refuses_a_custody_ref_it_cannot_trust_and_reds_the_committer(tmp_path, path, header, reason):
    env = _hold_env(tmp_path, run_id="701")
    repo, bare = _pair_seed(tmp_path, env)
    payload = b"planted\n"
    blob = _git_in(repo, "hash-object", "-w", "--stdin", data=payload, env=env)
    manifest = f"{header}\nentry\t0\t{path}\t{blob}\t{len(payload)}\t-\tblob\n".encode()
    mblob = _git_in(repo, "hash-object", "-w", "--stdin", data=manifest, env=env)
    sub = _git_in(repo, "mktree", data=f"100644 blob {blob}\t0\n".encode(), env=env)
    tree = _git_in(repo, "mktree", data=f"100644 blob {mblob}\tMANIFEST\n040000 tree {sub}\tblobs\n".encode(), env=env)
    commit = _git_in(repo, "commit-tree", tree, "-m", "custody", data=b"", env=env)
    ref = HOLD_PREFIX + "700-1-planted00000"
    _git(repo, "push", "-q", "origin", f"{commit}:{ref}", env=env)

    nxt = tmp_path / "next"
    subprocess.run(["git", "clone", "-q", str(bare), str(nxt)], check=True, env=env)
    recovered = _recover(nxt, env)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert f"::error title=held rows not restored::{ref}: {reason}. The ref is kept." in recovered.stdout
    assert _custody_refs(bare, env) == [ref]
    assert not (tmp_path / "escape.json").exists()
    assert not (nxt / ".git/hooks/post-checkout").exists()
    assert not (nxt / "elsewhere").exists()
    assert (nxt / "site/x.json").read_bytes() == b'{"v":1}\n'
    assert _git(nxt, "status", "--porcelain", env=env) == ""
    red = _bash(nxt, '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\nif push_hold_red; then echo RED; fi', env)
    assert "RED" in red.stdout


@pytest.mark.parametrize("how", ["edited", "staged", "symlink"])
def test_engine_recover_writes_nothing_over_a_dirty_second_member_and_keeps_the_ref(tmp_path, how):
    env = _hold_env(tmp_path, run_id="801")
    repo, bare = _pair_seed(tmp_path, env)
    _stage_pair(repo, env)
    assert _bash(repo, _hold_script("engine_hold"), env).returncode == 1
    [ref] = _custody_refs(bare, env)

    nxt = tmp_path / "next"
    subprocess.run(["git", "clone", "-q", str(bare), str(nxt)], check=True, env=env)
    member = nxt / "site/x.json"
    outside = tmp_path / "outside.json"
    if how == "edited":
        member.write_bytes(b'{"v":"local"}\n')
    elif how == "staged":
        member.write_bytes(b'{"v":"index"}\n')
        _git(nxt, "add", "site/x.json", env=env)
        member.write_bytes(b'{"v":1}\n')
    else:
        outside.write_bytes(b'{"v":1}\n')
        member.unlink()
        member.symlink_to(outside)
    before = member.read_bytes()
    env2 = _hold_env(tmp_path, run_id="802")
    recovered = _recover(nxt, env2)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert f"::error title=held rows not restored::{ref}: worktree is dirty for site/x.json. The ref is kept." in recovered.stdout
    assert (nxt / "data/x.jsonl").read_bytes() == b"old\n", "the clean first member is not written either"
    assert member.read_bytes() == before
    if how == "symlink":
        assert member.is_symlink() and outside.read_bytes() == b'{"v":1}\n'
    assert _custody_refs(bare, env) == [ref]
    red = _bash(nxt, '. "$GITHUB_WORKSPACE/scripts/ci/push_hold.sh"\nif push_hold_red; then echo RED; fi', env2)
    assert "RED" in red.stdout


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


@pytest.mark.parametrize(
    "workflow,commit_prefix",
    [
        ("whitehouse-sentinel.yml", 'git commit -m "whitehouse: alert update'),
        ("weekly.yml", 'git commit -m "weekly: deep-dive'),
        ("backfill.yml", 'git commit -m "data: backfill'),
    ],
)
def test_committers_outside_daily_carve_after_their_last_add(workflow, commit_prefix):
    wf = yaml.safe_load((WORKFLOWS / workflow).read_text())
    runs = [
        str(step.get("run") or "")
        for job in wf["jobs"].values()
        for step in job.get("steps", [])
        if commit_prefix in str(step.get("run") or "")
    ]
    assert len(runs) == 1, f"{workflow}: expected one committer step, found {len(runs)}"
    run = runs[0]
    commit = run.index(commit_prefix)
    call = f"{SOURCE_LINE}; qledger_carve_staged || exit 1"
    assert call in run, f"{workflow}: a withheld commit must red the run"
    last_add = [m.start() for m in re.finditer(r"(?m)^\s*git add\b", run[:commit])][-1]
    assert last_add < run.index(call) < commit
    assert run.index(call) < run.index("git diff --cached --quiet")


_LEDGER_PATHSPECS = {".", "data", "data/", "data/qledger", "data/qledger/", "site/qledger", "site/qledger/"}


def _stages_the_ledger(line: str) -> bool:
    """True for a real `git add` whose pathspec covers data/qledger or site/qledger."""
    line = line.strip()
    if not line.startswith("git add"):
        return False
    words = re.split(r"\s*(?:2>|&&|\|\||;|#)", line, maxsplit=1)[0].split()[2:]
    paths = [w for w in words if not w.startswith("-")]
    if not paths:
        return bool(set(words) & {"-A", "--all"})
    return bool(_LEDGER_PATHSPECS & set(paths))


def test_every_committer_that_can_stage_the_ledger_is_carve_aware():
    """Run 41285198348: the sentinel staged the ledger with no carve and lost every alert."""
    sources = [*WORKFLOWS.glob("*.yml"), *(ROOT / "scripts" / "ci").glob("*.sh")]
    stagers = {
        path.relative_to(ROOT).as_posix(): path.read_text()
        for path in sources
        if any(_stages_the_ledger(line) for line in path.read_text().splitlines())
    }
    assert ".github/workflows/daily.yml" in stagers, "the census no longer sees the known committers"
    assert ".github/workflows/whitehouse-sentinel.yml" in stagers
    blind = sorted(name for name, text in stagers.items() if "qledger_carve" not in text)
    assert not blind, f"these stage the ledger with no GH001 carve: {blind}"


@pytest.mark.parametrize(
    "line,expected",
    [
        ("git add data/ site/qledger/", True),
        ("git add data/ reports/ site/", True),
        ("git add data/ai_costs/usage.d data/whitehouse data/qledger site/wh_banner.json 2>/dev/null || true", True),
        ("git add -A", True),
        ("git add -A -- data/smart_money data/openfigi/cusip_ticker.parquet", False),
        ("git add --ignore-removal site/assets/css 2>/dev/null || true", False),
        ("git add site/", False),
        ("# the commit step below (git add data/ site/) lands both", False),
    ],
)
def test_ledger_stage_census_reads_pathspecs(line, expected):
    assert _stages_the_ledger(line) is expected


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


def _fault_shim(tmp_path: Path, env: dict[str, str], mode: str) -> tuple[dict[str, str], Path]:
    """A `git` on PATH that, once the arm file exists, fails the restore's
    object reads like an unreadable object store: `lookup` → `ls-tree` and
    `cat-file -e` exit 128; `blob` → `cat-file blob` exits 128 with no stdout.
    Armed only after the carve, so `qledger_carve_staged` itself runs clean."""
    shim = tmp_path / "shim"
    shim.mkdir()
    arm = tmp_path / "shim.arm"
    # blob mode also witnesses the live claims file's size at the instant the
    # blob read runs: a restore that redirects onto the live file has already
    # truncated it to 0 by then.
    watch = tmp_path / "lane" / "data" / "qledger" / "claims.jsonl"
    witness = tmp_path / "shim.witness"
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True, text=True).stdout.strip()
    (shim / "git").write_text(
        "#!/usr/bin/env bash\n"
        f'if [ -e "{arm}" ]; then\n'
        '  sub=""; has_e=0; has_blob=0; is_watch=0\n'
        '  for a in "$@"; do case "$a" in ls-tree|cat-file) [ -n "$sub" ] || sub="$a" ;; -e) has_e=1 ;; blob) has_blob=1 ;; *:data/qledger/claims.jsonl) is_watch=1 ;; esac; done\n'
        f'  if [ "{mode}" = lookup ] && {{ [ "$sub" = ls-tree ] || {{ [ "$sub" = cat-file ] && [ "$has_e" = 1 ]; }}; }}; then echo "fatal: shim: object lookup unavailable" >&2; exit 128; fi\n'
        f'  if [ "{mode}" = blob ] && [ "$sub" = cat-file ] && [ "$has_blob" = 1 ]; then if [ "$is_watch" = 1 ]; then wc -c < "{watch}" > "{witness}" 2>/dev/null || echo missing > "{witness}"; fi; echo "fatal: shim: blob read failed" >&2; exit 128; fi\n'
        "fi\n"
        f'exec "{real_git}" "$@"\n'
    )
    (shim / "git").chmod(0o755)
    return {**env, "PATH": f"{shim}:{env['PATH']}"}, arm


@pytest.mark.parametrize("mode", ["lookup", "blob"])
def test_restore_never_destroys_the_surviving_bytes_when_a_snapshot_read_fails(tmp_path, mode):
    """#9556 post-merge findings 6285214966 + 6290288707, cloned into this helper
    by #10255: the restore classified a path by the exit code of `cat-file -e`
    and wrote the blob straight over the live file. An unreadable object store
    therefore read as a deferred deletion (`rm -f` of the parked claims); a
    failed blob read truncated them to 0 bytes — and both were reported as
    restored. A failed read must leave the parked HEAD bytes exactly in place,
    leave no temp file behind, and report the path LOST."""
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    claims = repo / "data" / "qledger" / "claims.jsonl"
    head_bytes = claims.read_bytes()
    _grow(claims, LIMIT + 4096)
    _git(repo, "add", "data/", "site/", env=env)
    env2, arm = _fault_shim(tmp_path, env, mode)
    proc = _bash(
        repo,
        f'. "{HELPER}"; qledger_carve_staged; echo "carved=$QLEDGER_CARVED snap=$QLEDGER_SNAPSHOT"; '
        f'[ "$(wc -c < data/qledger/claims.jsonl)" -eq {len(head_bytes)} ] || {{ echo "park did not leave HEAD bytes" >&2; exit 9; }}; '
        f'touch "{arm}"; qledger_carve_restore; echo "rc=$?"',
        env2,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "carved=true" in proc.stdout
    assert claims.exists(), f"restore DELETED the parked claims on a failed {mode} read:\n{proc.stdout}{proc.stderr}"
    assert claims.read_bytes() == head_bytes, (
        f"restore rewrote the parked claims on a failed {mode} read (size now {_size(claims)}):\n{proc.stdout}{proc.stderr}"
    )
    assert not list(claims.parent.glob("claims.jsonl.restore.*")), "restore left a temp file behind"
    if mode == "blob":
        witness = (tmp_path / "shim.witness").read_text().strip()
        assert witness == str(len(head_bytes)), (
            f"live claims file was {witness!r} bytes while the blob read ran (no intermediate write allowed)"
        )
    assert "::error title=qledger carve custody LOST::" in proc.stdout, proc.stdout
    assert "data/qledger/claims.jsonl" in proc.stdout.split("custody LOST::", 1)[1].splitlines()[0]
    assert "claims.jsonl(deleted)" not in proc.stdout, proc.stdout
    assert "restored byte-identical" not in proc.stdout, proc.stdout
    assert "rc=0" in proc.stdout


def test_restore_never_moves_the_blob_into_a_directory_at_the_path(tmp_path):
    """#10481 review (fabric rs-leader-10481-review-r1): when the worktree path
    has become a DIRECTORY, POSIX `mv -f tmp dir` moves the verified temp INTO
    the directory and the swap leaks the snapshot blob there. A non-file at
    the path is LOST `(not-a-file)`: nothing is written, moved or removed."""
    env = _env(tmp_path)
    repo, _ = _seed(tmp_path, env)
    claims = repo / "data" / "qledger" / "claims.jsonl"
    _grow(claims, LIMIT + 4096)
    _git(repo, "add", "data/", "site/", env=env)
    proc = _bash(
        repo,
        f'. "{HELPER}"; qledger_carve_staged; echo "carved=$QLEDGER_CARVED"; '
        'rm -f data/qledger/claims.jsonl; mkdir data/qledger/claims.jsonl; echo sentinel > data/qledger/claims.jsonl/sentinel; '
        'qledger_carve_restore; echo "rc=$?"',
        env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "carved=true" in proc.stdout
    assert claims.is_dir(), "restore replaced or removed the directory at the path"
    assert sorted(p.name for p in claims.iterdir()) == ["sentinel"], (
        f"restore wrote into the directory at the path: {sorted(p.name for p in claims.iterdir())}"
    )
    assert (claims / "sentinel").read_text() == "sentinel\n"
    assert not list(claims.parent.glob("claims.jsonl.restore.*")), "restore left a temp file behind"
    assert "::error title=qledger carve custody LOST::" in proc.stdout, proc.stdout
    assert "data/qledger/claims.jsonl(not-a-file)" in proc.stdout, proc.stdout
    assert "restored byte-identical" not in proc.stdout, proc.stdout
    assert "rc=0" in proc.stdout


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
