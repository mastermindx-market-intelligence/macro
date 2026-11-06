"""Execute GovRev's real mint boundaries, without running its publisher."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/ci/govrev_native_publish.sh"
LIBRARY = ROOT / "scripts/ci/push_retry.sh"


def git(root, *args, env=None):
    return subprocess.check_output(["git", "-C", str(root), *args], env=env)


def boundary(amend):
    pattern = r'^\s*(?:git commit|push_native_commit) ' + (
        r'--amend --no-edit$' if amend else r'-m "govrev: SAM opportunity evidence .*"$'
    )
    commands = re.findall(pattern, SOURCE.read_text(), re.M)
    assert len(commands) == 1
    return commands[0].strip()


def execute(root, command, env):
    return subprocess.run(
        ["bash", "-e", "-c", '. "$GOVREV_TEST_LIBRARY"\n' + command],
        cwd=root, env={**env, "GOVREV_TEST_LIBRARY": str(LIBRARY)},
        capture_output=True,
    )


def initialize(root, env):
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Original Author")
    git(root, "config", "user.email", "original@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / "output").write_text("source")
    git(root, "add", ".")
    git(root, "commit", "-qm", "parent", env=env)


def identity(raw, role):
    match = re.search(rb'^' + role.encode() + rb' (.+) (-?\d+) ([+-]\d{4})$', raw, re.M)
    assert match
    return match[1], int(match[2]), match[3]


@pytest.mark.parametrize("amend", [False, True], ids=["initial", "amend"])
@pytest.mark.parametrize("explicit", [False, True], ids=["ambient", "explicit"])
def test_actual_govrev_native_mint_preserves_instants_and_reconstructs_api_bytes(tmp_path, amend, explicit):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(TZ="America/Vancouver", GITHUB_REPOSITORY="mastermindx-market-intelligence/macro")
    initialize(tmp_path, env)
    parent = git(tmp_path, "rev-parse", "HEAD").strip()
    env.update(GIT_AUTHOR_NAME="Distinct Author", GIT_AUTHOR_EMAIL="author@example.invalid",
               GIT_COMMITTER_NAME="Distinct Committer", GIT_COMMITTER_EMAIL="committer@example.invalid")
    if explicit:
        env.update(GIT_AUTHOR_DATE="2026-11-05T11:23:34-08:00",
                   GIT_COMMITTER_DATE="2026-11-05T21:45:56+09:00")
    before = int(time.time())
    (tmp_path / "output").write_text("original generation")
    git(tmp_path, "add", ".")
    result = execute(tmp_path, boundary(False), env)
    assert result.returncode == 0, result.stderr
    initial = git(tmp_path, "cat-file", "commit", "HEAD")
    initial_author = identity(initial, "author")
    initial_message = initial.split(b"\n\n", 1)[1]
    if amend:
        # Actual amend keeps the original author, even when ambient author/date
        # overrides differ. The committer remains the intended current identity.
        env.update(GIT_AUTHOR_NAME="Ignored Amend Author", GIT_AUTHOR_EMAIL="ignored@example.invalid")
        if explicit:
            env.update(GIT_AUTHOR_DATE="2026-11-04T08:12:13+05:30",
                       GIT_COMMITTER_DATE="2026-11-06T09:10:11+09:00")
        (tmp_path / "output").write_text("rebuilt exact generation")
        git(tmp_path, "add", ".")
        result = execute(tmp_path, boundary(True), env)
        assert result.returncode == 0, result.stderr
    after = int(time.time())
    head = git(tmp_path, "rev-parse", "HEAD").strip()
    raw = git(tmp_path, "cat-file", "commit", "HEAD")
    tree = git(tmp_path, "write-tree").strip()
    assert git(tmp_path, "rev-parse", "HEAD^{tree}").strip() == tree
    assert git(tmp_path, "rev-parse", "HEAD^").strip() == parent
    assert raw.split(b"\n\n", 1)[1] == initial_message
    author, committer = identity(raw, "author"), identity(raw, "committer")
    assert author[0] == b"Distinct Author <author@example.invalid>"
    assert committer[0] == b"Distinct Committer <committer@example.invalid>"
    assert author[2] == committer[2] == b"+0000"
    assert author == initial_author
    if explicit:
        assert author[1] == int(datetime.fromisoformat("2026-11-05T11:23:34-08:00").timestamp())
        assert committer[1] == int(datetime.fromisoformat(env["GIT_COMMITTER_DATE"]).timestamp())
    else:
        assert before <= author[1] <= after and before <= committer[1] <= after
    # Git REST's unsigned ISO UTC representation must reconstruct every byte.
    def api_header(role, row):
        api_date = datetime.fromtimestamp(row[1], timezone.utc).isoformat().replace("+00:00", "Z")
        epoch = int(datetime.fromisoformat(api_date.replace("Z", "+00:00")).timestamp())
        return role.encode() + b" " + row[0] + b" " + str(epoch).encode() + b" +0000"
    reconstructed = (b"tree " + tree + b"\nparent " + parent + b"\n" +
                     api_header("author", author) + b"\n" + api_header("committer", committer) +
                     b"\n\n" + initial_message)
    assert reconstructed == raw
    assert hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest().encode() == head
    assert env["TZ"] == "America/Vancouver"


@pytest.mark.parametrize("amend", [False, True], ids=["initial", "amend"])
def test_actual_govrev_legacy_mint_retains_original_git_offsets(tmp_path, amend):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(TZ="America/Vancouver", GITHUB_REPOSITORY="other/repository",
               GIT_AUTHOR_DATE="2026-11-05T11:23:34-08:00",
               GIT_COMMITTER_DATE="2026-11-05T21:45:56+09:00")
    initialize(tmp_path, env)
    (tmp_path / "output").write_text("legacy generation")
    git(tmp_path, "add", ".")
    result = execute(tmp_path, boundary(amend), env)
    assert result.returncode == 0, result.stderr
    raw = git(tmp_path, "cat-file", "commit", "HEAD")
    assert identity(raw, "author")[2] == b"-0800"
    assert identity(raw, "committer")[2] == b"+0900"


@pytest.mark.parametrize("amend", [False, True], ids=["initial", "amend"])
@pytest.mark.parametrize("control", ["hook", "signer"])
def test_actual_govrev_mint_preserves_hook_and_signing_failures(tmp_path, amend, control):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(TZ="America/Vancouver", GITHUB_REPOSITORY="mastermindx-market-intelligence/macro")
    initialize(tmp_path, env)
    head = git(tmp_path, "rev-parse", "HEAD")
    marker = tmp_path / "control-called"
    program = tmp_path / (".git/hooks/pre-commit" if control == "hook" else "signer")
    program.write_text('#!/bin/sh\nprintf called > "' + str(marker) + '"\nexit 1\n')
    program.chmod(0o700)
    if control == "signer":
        git(tmp_path, "config", "commit.gpgsign", "true")
        git(tmp_path, "config", "gpg.program", str(program))
    (tmp_path / "output").write_text("pending generation")
    git(tmp_path, "add", "output")
    result = execute(tmp_path, boundary(amend), env)
    assert result.returncode != 0 and marker.read_text() == "called"
    assert git(tmp_path, "rev-parse", "HEAD") == head
    assert git(tmp_path, "diff", "--cached", "--name-only").strip() == b"output"
