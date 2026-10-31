"""EW-P1: the shared QLedger oversize carve, parked/restored around the two
nightly commit paths that were still unprotected (#9556 gave the collect job a
carve; run 40803269874 then rejected `commit engine outputs` and
`commit tail data` with GH001 against a 104,857,394-byte claims.jsonl).

scripts/ci/qledger_oversize_carve.sh is a SOURCED library used by
scripts/ci/daily_engine_commit_outputs.sh and
scripts/ci/daily_collect_tail_commit.sh. These tests drive it exactly the way
the two scripts do: `bash -c` with `set -e` at the top (GitHub runs
`bash -e {0}`), a tiny QLEDGER_CARVE_LIMIT/QLEDGER_CARVE_MARGIN under
QLEDGER_CARVE_TEST_OVERRIDE=1, GITHUB_OUTPUT/GITHUB_STEP_SUMMARY pointed at
real files, and git identity via env so a bare CI runner works. Every scenario
uses a throwaway git repository under tmp_path — no network, no real data,
nothing from data/qledger or site/qledger is read or published.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.workflow_run_source import resolve_run_source  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "ci" / "qledger_oversize_carve.sh"
ENGINE_SCRIPT = ROOT / "scripts" / "ci" / "daily_engine_commit_outputs.sh"
TAIL_SCRIPT = ROOT / "scripts" / "ci" / "daily_collect_tail_commit.sh"
DAILY_YML = ROOT / ".github" / "workflows" / "daily.yml"

# The frozen `commit tail data` block as it lived in daily.yml at f2efb8ba,
# before EW-P1 extracted it to scripts/ci/daily_collect_tail_commit.sh.
PRE_EXTRACTION_SHA256 = (
    "89d7dbfe0798f1b12414deee6096be804c9f1548040ed885597cd5062a921123"
)

# EW-P1 insertion pinned byte-exact in both call sites (spec (b) and (c)).
ENGINE_INSERTION = "\n".join(
    [
        "# EW-P1 (2026-10-31): carve oversize QLedger blobs out of the engine commit, as the",
        "# collect job has since #9556. Run 40803269874 / engine job 123688873047 was rejected with GH001",
        "# (a QLedger blob over GitHub's 100 MB file limit) and the durable mirror",
        "# data/risk_envelope/ has not advanced since 2026-10-21. Helper: scripts/ci/qledger_oversize_carve.sh.",
        '. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_oversize_carve.sh"',
        "qledger_carve_staged engine",
        'if [ "${QLEDGER_WITHHELD:-}" = true ]; then exit 0; fi',
        'if [ "${QLEDGER_CARVED:-}" = true ]; then trap \'qledger_restore\' EXIT; qledger_park; if [ "${QLEDGER_PARKED:-}" != true ]; then exit 0; fi; fi',
    ]
)
TAIL_INSERTION = "\n".join(
    [
        "# EW-P1 (2026-10-31): carve oversize QLedger blobs out of the collect-tail commit, as the",
        "# collect job has since #9556. Run 40803269874 / collect_tail job 123688869633 was rejected for a 146.50 MB",
        "# QLedger blob. Helper: scripts/ci/qledger_oversize_carve.sh.",
        '. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_oversize_carve.sh"',
        "qledger_carve_staged collect-tail",
        'if [ "${QLEDGER_WITHHELD:-}" = true ]; then exit 0; fi',
        'if [ "${QLEDGER_CARVED:-}" = true ]; then trap \'qledger_restore\' EXIT; qledger_park; if [ "${QLEDGER_PARKED:-}" != true ]; then exit 0; fi; fi',
    ]
)

CARVE_SOURCE_LINE = '. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_oversize_carve.sh"'

OVERSIZE = b"q" * 4000  # > 4096 - 1024 under the test override
WITHIN_LIMIT = b"q" * 100


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _env(repo: Path, tmp: Path, **extra: str) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "EW-P1 Test",
            "GIT_AUTHOR_EMAIL": "ew-p1-test@example.com",
            "GIT_COMMITTER_NAME": "EW-P1 Test",
            "GIT_COMMITTER_EMAIL": "ew-p1-test@example.com",
            "GITHUB_OUTPUT": str(tmp / "github_output.txt"),
            "GITHUB_STEP_SUMMARY": str(tmp / "github_step_summary.txt"),
            "QLEDGER_CARVE_TEST_OVERRIDE": "1",
            "QLEDGER_CARVE_LIMIT": "4096",
            "QLEDGER_CARVE_MARGIN": "1024",
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(tmp / "home"),
        }
    )
    env.update(extra)
    (tmp / "home").mkdir(exist_ok=True)
    (tmp / "github_output.txt").touch()
    (tmp / "github_step_summary.txt").touch()
    return env


def _run(script: str, repo: Path, env: dict) -> subprocess.CompletedProcess:
    """Run a driven script the way the nightly scripts run: bash -e, cwd=repo."""
    return subprocess.run(
        ["bash", "-c", f"set -e\n. {HELPER}\n{script}"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def _fresh_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "data").mkdir()
    (repo / "data" / "keep.txt").write_text("spine output\n")
    # Both planes are tracked at HEAD, exactly as in the nightly repo: the
    # park's `git restore -- data/qledger site/qledger` aborts if a pathspec
    # matches nothing, and a fixture without site/qledger would park-fail.
    (repo / "site" / "qledger").mkdir(parents=True)
    (repo / "site" / "qledger" / "track_record.json").write_text("{}\n")
    _commit_all(repo, "base")
    return repo


def _marker(stdout: str, key: str) -> str:
    for line in stdout.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"marker {key!r} not printed; stdout:\n{stdout}")


def test_case1_oversize_staged_blob_is_carved_out_with_custody_snapshot(tmp_path):
    repo = _fresh_repo(tmp_path, "case1")
    claims = repo / "data" / "qledger" / "claims.jsonl"
    claims.parent.mkdir(parents=True)
    claims.write_bytes(OVERSIZE)
    other = repo / "data" / "tape_flow" / "events.jsonl"
    other.parent.mkdir(parents=True)
    other.write_text("{}\n")
    _git(repo, "add", "data/")

    env = _env(repo, tmp_path)
    result = _run(
        "qledger_carve_staged engine\n"
        'echo "CARVED=$QLEDGER_CARVED"\n'
        'echo "SNAPSHOT=$QLEDGER_SNAPSHOT"\n',
        repo,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert _marker(result.stdout, "CARVED") == "true"
    assert "::warning title=qledger carved out of engine commit::" in result.stdout
    assert f"within 1024B of GitHub's 4096B file limit: data/qledger/claims.jsonl={len(OVERSIZE)}B" in result.stdout

    snapshot = _marker(result.stdout, "SNAPSHOT")
    assert _git(repo, "cat-file", "-t", snapshot).stdout.strip() == "commit"
    # The snapshot's tree holds the exact staged oversize blob...
    want = _git(repo, "rev-parse", f"{snapshot}:data/qledger/claims.jsonl").stdout.strip()
    blob_sha = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "--stdin"],
        input=OVERSIZE.decode(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert want == blob_sha

    # ...while the staged index no longer carries either qledger plane.
    assert _git(repo, "diff", "--cached", "--name-only", "--", "data/qledger", "site/qledger").stdout.strip() == ""
    staged = _git(repo, "diff", "--cached", "--name-only").stdout.split()
    assert "data/tape_flow/events.jsonl" in staged
    assert "data/qledger/claims.jsonl" not in staged

    output = (tmp_path / "github_output.txt").read_text()
    assert "qledger_carved=true" in output
    assert f"qledger_snapshot={snapshot}" in output
    # Fail-closed flags stay unset on the success path.
    assert "qledger_withheld" not in output
    assert claims.read_bytes() == OVERSIZE  # unstage only, never revert


def test_case2_within_limit_staged_blob_is_left_staged(tmp_path):
    repo = _fresh_repo(tmp_path, "case2")
    claims = repo / "data" / "qledger" / "claims.jsonl"
    claims.parent.mkdir(parents=True)
    claims.write_bytes(WITHIN_LIMIT)
    _git(repo, "add", "data/")

    env = _env(repo, tmp_path)
    result = _run(
        "qledger_carve_staged engine\n"
        'echo "CARVED=$QLEDGER_CARVED"\n'
        'echo "SNAPSHOT=${QLEDGER_SNAPSHOT:-}"\n',
        repo,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert _marker(result.stdout, "CARVED") == "false"
    assert _marker(result.stdout, "SNAPSHOT") == ""
    assert "::warning" not in result.stdout
    # Index and worktree untouched: still staged, bytes intact.
    staged = _git(repo, "diff", "--cached", "--name-only").stdout.split()
    assert "data/qledger/claims.jsonl" in staged
    assert claims.read_bytes() == WITHIN_LIMIT
    assert (tmp_path / "github_output.txt").read_text() == ""


def test_case3_park_puts_both_planes_back_at_head(tmp_path):
    repo = _fresh_repo(tmp_path, "case3")
    claims = repo / "data" / "qledger" / "claims.jsonl"
    claims.parent.mkdir(parents=True)
    claims.write_bytes(WITHIN_LIMIT)
    _commit_all(repo, "ledger at head")
    claims.write_bytes(OVERSIZE)  # tonight's append, now oversize
    _git(repo, "add", "data/qledger/claims.jsonl")

    env = _env(repo, tmp_path)
    result = _run(
        "qledger_carve_staged engine\n"
        "qledger_park\n"
        'echo "PARKED=$QLEDGER_PARKED"\n',
        repo,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert _marker(result.stdout, "PARKED") == "true"
    # Worktree AND index of both planes equal HEAD after the park.
    assert _git(repo, "diff", "--quiet", "HEAD", "--", "data/qledger", "site/qledger").returncode == 0
    assert _git(repo, "diff", "--cached", "--quiet", "--", "data/qledger", "site/qledger").returncode == 0
    assert claims.read_bytes() == WITHIN_LIMIT  # restored from HEAD, not reverted to nothing


def test_case4_restore_is_byte_identical_idempotent_and_trap_safe(tmp_path):
    repo = _fresh_repo(tmp_path, "case4")
    qdir = repo / "data" / "qledger"
    qdir.mkdir(parents=True)
    (qdir / "claims.jsonl").write_bytes(WITHIN_LIMIT)
    (qdir / "old.json").write_bytes(b"old\n")
    _commit_all(repo, "head with two qledger paths")
    (qdir / "claims.jsonl").write_bytes(OVERSIZE)
    _git(repo, "add", "data/qledger/claims.jsonl")
    # old.json is deleted in the STAGED index only (absent in the snapshot).
    _git(repo, "rm", "-q", "--cached", "data/qledger/old.json")

    env = _env(repo, tmp_path)
    result = _run(
        "qledger_carve_staged engine\n"
        "qledger_park\n"
        'echo "SNAP=$QLEDGER_SNAPSHOT"\n'
        'echo "PARKED=$QLEDGER_PARKED"\n'
        "qledger_restore\n"
        "echo RESTORED_ONCE\n"
        "qledger_restore\n"
        "echo RESTORED_TWICE\n",
        repo,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert _marker(result.stdout, "PARKED") == "true"
    snapshot = _marker(result.stdout, "SNAP")
    assert snapshot
    # Every carved path is byte-identical to the snapshot blob...
    assert (qdir / "claims.jsonl").read_bytes() == OVERSIZE
    # ...and the path the carve recorded as deleted-in-snapshot is removed.
    assert not (qdir / "old.json").exists()
    assert "::warning title=qledger carve-out not published::" in result.stdout
    assert "::error title=qledger carve custody LOST::" not in result.stdout
    assert "RESTORED_ONCE" in result.stdout and "RESTORED_TWICE" in result.stdout

    # EXIT-trap pins (bash 5.3 semantics the helper's guards rely on): a
    # carve+park+trap script preserves its exit status through the trap.
    re_stage = "git add data/qledger/claims.jsonl\n"
    for code, expected in (("0", 0), ("1", 1)):
        pinned = _run(
            re_stage
            + "qledger_carve_staged engine\n"
            + "qledger_park\n"
            + "trap 'qledger_restore' EXIT\n"
            + f"exit {code}\n",
            repo,
            env,
        )
        assert pinned.returncode == expected, (code, pinned.returncode, pinned.stderr)

    # Custody-LOST still preserves the exit status and reports the loss.
    lost = "0000000000000000000000000000000000000000"
    for code, expected in (("0", 0), ("1", 1)):
        pinned = _run(
            f"export QLEDGER_SNAPSHOT={lost}\n"
            + "trap 'qledger_restore' EXIT\n"
            + f"exit {code}\n",
            repo,
            env,
        )
        assert pinned.returncode == expected, (code, pinned.returncode, pinned.stderr)
        assert "::error title=qledger carve custody LOST::" in pinned.stdout


def test_case5_snapshot_failure_fails_closed_and_withholds(tmp_path):
    repo = _fresh_repo(tmp_path, "case5")
    claims = repo / "data" / "qledger" / "claims.jsonl"
    claims.parent.mkdir(parents=True)
    claims.write_bytes(OVERSIZE)
    _git(repo, "add", "data/")

    real_git = shutil.which("git")  # resolve BEFORE changing PATH
    assert real_git
    bin_dir = tmp_path / "case5-bin"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "commit-tree" ]; then exit 1; fi\n'
        f'exec "{real_git}" "$@"\n'
    )
    (bin_dir / "git").chmod(0o755)

    env = _env(repo, tmp_path)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    result = _run(
        "qledger_carve_staged engine\n"
        'echo "WITHHELD=$QLEDGER_WITHHELD"\n'
        'echo "SNAPSHOT=${QLEDGER_SNAPSHOT:-}"\n'
        'echo "CARVED=${QLEDGER_CARVED:-}"\n',
        repo,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert _marker(result.stdout, "WITHHELD") == "true"
    assert (
        "::error title=engine publication withheld (qledger carve snapshot failed)::" in result.stdout
    )
    assert _marker(result.stdout, "SNAPSHOT") == ""
    assert _marker(result.stdout, "CARVED") == ""
    assert "qledger_withheld=true" in (tmp_path / "github_output.txt").read_text()
    # Fail closed = index and worktree left exactly as they were.
    staged = _git(repo, "diff", "--cached", "--name-only").stdout.split()
    assert "data/qledger/claims.jsonl" in staged
    assert claims.read_bytes() == OVERSIZE


def test_case6_call_site_and_helper_text_pins():
    engine = ENGINE_SCRIPT.read_text()
    tail = TAIL_SCRIPT.read_text()
    helper = HELPER.read_text()

    # The frozen insertions appear exactly once in each call site.
    assert engine.count(ENGINE_INSERTION) == 1
    assert tail.count(TAIL_INSERTION) == 1

    def _line_index(text: str, predicate, what: str) -> int:
        for i, line in enumerate(text.splitlines()):
            if predicate(line):
                return i
        raise AssertionError(f"{what} line not found")

    for text, add_line, commit_pred in (
        (engine, "git add data/ site/ reports/", lambda l: "commit-broad-candidate" in l),
        (tail, "git add data/ site/basketdata/", lambda l: l.startswith("git commit -m")),
    ):
        i_add = _line_index(text, lambda l, a=add_line: l.strip() == a, "git add")
        i_source = _line_index(text, lambda l: l.strip() == CARVE_SOURCE_LINE, "carve source")
        i_commit = _line_index(text, commit_pred, "commit")
        assert i_add < i_source < i_commit, (i_add, i_source, i_commit)

    # The frozen constants and provenance live in the helper itself.
    assert "104857600" in helper
    assert "1048576" in helper
    assert "# EXTRACTED-FROM: .github/workflows/daily.yml collect job" in helper


def test_case7_daily_yml_extraction_pins():
    import yaml

    doc = yaml.safe_load(DAILY_YML.read_text())
    steps = doc["jobs"]["collect_tail"]["steps"]
    step = next(s for s in steps if s.get("name") == "commit tail data")
    assert step["run"].strip() == "bash scripts/ci/daily_collect_tail_commit.sh"
    assert step["if"] == "always()"

    # The marker lets the extraction seam see straight through to the script.
    run_value = step["run"].strip()
    resolved = resolve_run_source(run_value, ROOT)
    assert resolved == TAIL_SCRIPT.read_text()

    # Script minus the 5 frozen header lines minus the 7-line carve insertion
    # is byte-identical to the pre-extraction YAML block.
    lines = TAIL_SCRIPT.read_text().splitlines()
    body = lines[5:]
    insertion = TAIL_INSERTION.splitlines()
    occurrences = [i for i in range(len(body) - len(insertion) + 1) if body[i : i + len(insertion)] == insertion]
    assert len(occurrences) == 1
    start = occurrences[0]
    assert body[start - 1] == "git add data/ site/basketdata/"
    stripped = body[:start] + body[start + len(insertion):]
    while stripped and stripped[-1] == "":
        stripped.pop()
    digest = hashlib.sha256(("\n".join(stripped) + "\n").encode()).hexdigest()
    assert digest == PRE_EXTRACTION_SHA256, digest
