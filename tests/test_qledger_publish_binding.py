"""Actual publisher function boundaries exercised only in synthetic repositories."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shlex
import stat
import subprocess

import pytest


REPO = Path(__file__).resolve().parents[1]
PUSH = REPO / "scripts/ci/push_retry.sh"
OPTIONS = REPO / "scripts/ci/options_signal_nightly.sh"


def environment():
    result = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
              "GIT_TERMINAL_PROMPT": "0", "GITHUB_WORKSPACE": str(REPO)}
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GITHUB_STEP_SUMMARY"):
        result.pop(key, None)
    return result


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], env=environment(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.decode().strip()


def shell(root, body, *, timeout=20):
    # /bin/bash also exercises the system shell used by the existing wrappers.
    return subprocess.run(["/bin/bash", "-c", body], cwd=root, env=environment(),
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout)


def fixture_repo(tmp_path):
    root = tmp_path / "publisher-fixture"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    git(root, "config", "user.name", "Synthetic Publisher")
    git(root, "config", "user.email", "synthetic@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / "data").mkdir()
    (root / "data/fixture.txt").write_bytes(b"accepted baseline\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic accepted baseline")
    baseline = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/main", baseline)
    (root / "data/fixture.txt").write_bytes(b"staged candidate\n")
    git(root, "add", "data/fixture.txt")
    (root / "data/fixture.txt").write_bytes(b"staged candidate\nunstaged suffix\n")
    (root / "untracked.txt").write_bytes(b"keep this untracked file\n")
    return root, baseline


def snapshot(root):
    return {"head": git(root, "rev-parse", "HEAD"),
            "index": (root / ".git/index").read_bytes(),
            "working": (root / "data/fixture.txt").read_bytes(),
            "untracked": (root / "untracked.txt").read_bytes()}


def test_frozen_candidate_rejection_preserves_index_worktree_ref_and_no_parent_restore(tmp_path):
    root, baseline = fixture_repo(tmp_path)
    before = snapshot(root)
    body = f'''set -e
. {shlex.quote(str(OPTIONS))}
push_qledger_preflight() {{ printf '%s\\n' 'synthetic integrity rejection'; return 77; }}
oip_restore_locked_index() {{ printf '%s\\n' 'UNEXPECTED_PARENT_RESTORE'; return 99; }}
if oip_commit_locked_roots 'synthetic rejected candidate' true data site reports templates; then
  exit 90
else
  rc=$?
fi
printf 'REJECTION_RC=%s\\n' "$rc"
'''
    result = shell(root, body)
    assert result.returncode == 0, result.stderr
    assert "REJECTION_RC=77" in result.stdout
    assert "UNEXPECTED_PARENT_RESTORE" not in result.stdout + result.stderr
    assert snapshot(root) == before and before["head"] == baseline
    assert not (root / ".git/index.lock").exists()


@pytest.mark.parametrize("kind", ["different-empty-inode", "modified", "symlink", "fifo"])
def test_rejection_keeps_a_replaced_or_changed_index_lock(kind, tmp_path):
    root, _ = fixture_repo(tmp_path)
    before = snapshot(root)
    if kind == "modified":
        mutation = "printf 'changed lock' > .git/index.lock"
    else:
        mutation = "mv .git/index.lock .git/retained-original-lock\n"
        if kind == "different-empty-inode":
            mutation += ": > .git/index.lock"
        elif kind == "symlink":
            mutation += "ln -s ../untracked.txt .git/index.lock"
        else:
            mutation += "mkfifo .git/index.lock"
    body = f'''set -e
. {shlex.quote(str(OPTIONS))}
oip_after_locked_tree_snapshot() {{
{mutation}
}}
push_qledger_preflight() {{ return 77; }}
oip_restore_locked_index() {{ printf 'UNEXPECTED_PARENT_RESTORE\\n'; return 99; }}
if oip_commit_locked_roots 'synthetic rejected candidate' true data; then exit 90; else rc=$?; fi
printf 'REJECTION_RC=%s\\n' "$rc"
'''
    result = shell(root, body, timeout=10)
    assert result.returncode == 0 and "REJECTION_RC=77" in result.stdout, result.stderr
    assert "UNEXPECTED_PARENT_RESTORE" not in result.stdout + result.stderr
    assert snapshot(root) == before
    lock = root / ".git/index.lock"
    info = lock.lstat()
    if kind == "modified":
        assert lock.read_bytes() == b"changed lock"
    elif kind == "symlink":
        assert stat.S_ISLNK(info.st_mode)
        assert (root / "untracked.txt").read_bytes() == before["untracked"]
    elif kind == "fifo":
        assert stat.S_ISFIFO(info.st_mode)
    else:
        assert stat.S_ISREG(info.st_mode) and info.st_size == 0
        assert info.st_ino != (root / ".git/retained-original-lock").stat().st_ino


def test_frozen_gate_receives_remote_tracking_baseline_not_unpublished_parent(tmp_path):
    root, baseline = fixture_repo(tmp_path)
    git(root, "commit", "-qm", "unpublished parent fixture")
    parent = git(root, "rev-parse", "HEAD")
    git(root, "add", "data/fixture.txt")
    record = root / "received-arguments.bin"
    body = f'''set -e
. {shlex.quote(str(OPTIONS))}
push_qledger_preflight() {{ printf '%s\\0' "$@" > {shlex.quote(str(record))}; return 77; }}
if oip_commit_locked_roots 'synthetic rejection' true data; then exit 90; else rc=$?; fi
test "$rc" = 77
'''
    result = shell(root, body)
    assert result.returncode == 0, result.stderr
    args = record.read_bytes().split(b"\0")[:-1]
    assert args[0] == b"frozen-tree"
    assert args[args.index(b"--parent") + 1].decode() == parent
    assert args[args.index(b"--accepted-baseline") + 1].decode() == baseline
    assert parent != baseline
    tree = args[args.index(b"--tree") + 1].decode()
    assert git(root, "cat-file", "-t", tree) == "tree"


@pytest.mark.parametrize("entry", ["push_prepare_inherited_rebase", "push_fetch_main_for_rebase", "push_autostash_ok"])
def test_unknown_native_pending_stops_before_git_cleanup_and_all_later_retry_actions(entry, tmp_path):
    trace = tmp_path / "unexpected-effects.txt"
    body = f'''set -e
. {shlex.quote(str(PUSH))}
push_retry_init 'synthetic retry'
push_qledger_preflight() {{ printf 'unknown native pending\\n'; return 79; }}
git() {{ printf 'git %s\\n' "$*" >> {shlex.quote(str(trace))}; return 99; }}
sleep() {{ printf 'sleep\\n' >> {shlex.quote(str(trace))}; return 99; }}
if {entry}; then exit 90; else first_rc=$?; fi
push_abort_rebase
push_backoff
if push_do origin abc:refs/heads/main; then exit 91; else later_rc=$?; fi
if push_attempt; then exit 92; fi
if push_lost; then exit 93; else lost_rc=$?; fi
printf 'RESULT=%s,%s,%s,%s,%s\\n' "$first_rc" "$later_rc" "$lost_rc" "$PUSH_N_OTHER" "$PUSH_FAIL_CLASS"
'''
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert "RESULT=79,79,79,1,qledger-integrity" in result.stdout
    assert not trace.exists()
    assert "QLedger publication stopped" in result.stderr


@pytest.mark.parametrize("args", [[], ["origin", "a" * 40 + ":refs/heads/main"],
                                    ["origin", "literal $(touch never-created)", ""]])
def test_guard_and_git_receive_the_exact_original_push_arguments(args, tmp_path):
    guard = tmp_path / "guard-args.bin"
    forwarded = tmp_path / "git-args.bin"
    quoted = " ".join(shlex.quote(value) for value in args)
    body = f'''set -eu
. {shlex.quote(str(PUSH))}
push_retry_init 'synthetic exact arguments'
push_qledger_preflight() {{ printf '%s\\0' "$@" > {shlex.quote(str(guard))}; return 0; }}
git() {{ printf '%s\\0' "$@" > {shlex.quote(str(forwarded))}; return 0; }}
push_do {quoted}
'''
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert forwarded.read_bytes().split(b"\0")[:-1] == [b"push", *(a.encode() for a in args)]
    assert guard.read_bytes().split(b"\0")[:-1] == [b"publish-candidate", *(b"--push-arg=" + a.encode() for a in args)]
    assert not (tmp_path / "never-created").exists()


def test_legacy_preflight_uses_the_real_selector_and_does_not_call_git(tmp_path):
    trace = tmp_path / "unexpected-git.txt"
    body = f'''set -eu
. {shlex.quote(str(PUSH))}
git() {{ printf 'unexpected git\\n' > {shlex.quote(str(trace))}; return 99; }}
push_qledger_preflight pre-rebase
'''
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert '"status": "LEGACY_SELECTED"' in result.stdout
    assert not trace.exists()


def test_real_legacy_frozen_commit_keeps_unstaged_and_untracked_bytes(tmp_path):
    root, baseline = fixture_repo(tmp_path)
    before = snapshot(root)
    body = f'''set -e
. {shlex.quote(str(OPTIONS))}
oip_commit_locked_roots 'synthetic accepted candidate' true data
'''
    result = shell(root, body)
    assert result.returncode == 0, result.stderr
    current = git(root, "rev-parse", "HEAD")
    assert current != baseline and current in result.stdout
    assert git(root, "show", "HEAD:data/fixture.txt") == "staged candidate"
    assert (root / "data/fixture.txt").read_bytes() == before["working"]
    assert (root / "untracked.txt").read_bytes() == before["untracked"]
    assert not (root / ".git/index.lock").exists()


def test_gh001_receipt_is_not_replaced_by_a_later_integrity_check(tmp_path):
    body = f'''set -e
. {shlex.quote(str(PUSH))}
push_retry_init 'synthetic GH001 precedence'
push_classify 5 'remote: error: GH001: Large files detected'
push_qledger_preflight() {{ printf 'UNEXPECTED_SECOND_CHECK\\n'; return 79; }}
if push_qledger_guard pre-rebase; then exit 90; else rc=$?; fi
printf 'RESULT=%s,%s,%s\\n' "$rc" "$PUSH_FAIL_CLASS" "$PUSH_TERMINAL_OUTPUT"
'''
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert "RESULT=5,push-size-rejected,remote: error: GH001: Large files detected" in result.stdout
    assert "UNEXPECTED_SECOND_CHECK" not in result.stdout + result.stderr


def test_preflight_prefers_python3_when_legacy_python_is_on_path(tmp_path):
    import sys
    bindir = tmp_path / "synthetic-bin"
    bindir.mkdir()
    trace = tmp_path / "unexpected-legacy-python.txt"
    legacy = bindir / "python"
    legacy.write_text("#!/bin/sh\nprintf 'unexpected legacy python\\n' > " + shlex.quote(str(trace)) + "\nexit 97\n")
    legacy.chmod(0o755)
    modern = bindir / "python3"
    modern.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
    modern.chmod(0o755)
    body = f"""set -eu
. {shlex.quote(str(PUSH))}
PATH={shlex.quote(str(bindir))}:"$PATH"
export PATH
push_qledger_preflight pre-rebase
"""
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert '"status": "LEGACY_SELECTED"' in result.stdout
    assert not trace.exists()


def test_lock_replacement_at_initial_identity_capture_is_never_adopted(tmp_path):
    root, _ = fixture_repo(tmp_path)
    before = snapshot(root)
    trace = root / "unexpected-gate.txt"
    # Execute the actual helper's stdin source in the real Python interpreter.
    # Replace only this synthetic lock at the create/open boundary: after an
    # exclusive create, or before a later reopening of an already-created lock.
    wrapper = r'''
import os, sys
source = sys.stdin.read()
target = sys.argv[1]
real_open = os.open
fired = False
def swap():
    os.rename(target, target + '.original')
    fd = real_open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
def intercepted(path, flags, *args, **kwargs):
    global fired
    if os.fspath(path) != target or fired:
        return real_open(path, flags, *args, **kwargs)
    fired = True
    if flags & os.O_EXCL:
        fd = real_open(path, flags, *args, **kwargs)
        swap()
        return fd
    swap()
    return real_open(path, flags, *args, **kwargs)
os.open = intercepted
sys.argv = ['-', target]
exec(compile(source, '<actual-lock-helper>', 'exec'))
'''
    body = f'''set -e
. {shlex.quote(str(OPTIONS))}
python3() {{
  if [ "$#" -eq 2 ] && [ "$1" = - ]; then
    command python3 -c {shlex.quote(wrapper)} "$2"
  else
    command python3 "$@"
  fi
}}
push_qledger_preflight() {{ printf 'unexpected gate\\n' > {shlex.quote(str(trace))}; return 77; }}
oip_restore_locked_index() {{ printf 'UNEXPECTED_PARENT_RESTORE\\n'; return 99; }}
if oip_commit_locked_roots 'synthetic identity race' true data; then exit 90; else rc=$?; fi
printf 'RESULT=%s\\n' "$rc"
'''
    result = shell(root, body)
    assert result.returncode == 0, result.stderr
    assert "RESULT=1" in result.stdout
    assert not trace.exists()
    assert "UNEXPECTED_PARENT_RESTORE" not in result.stdout + result.stderr
    assert snapshot(root) == before
    lock = root / ".git/index.lock"
    original = root / ".git/index.lock.original"
    assert lock.is_file() and lock.read_bytes() == b""
    assert original.is_file() and original.read_bytes() == b""
    assert lock.stat().st_ino != original.stat().st_ino


def test_nested_prepare_rejection_preserves_first_terminal_class_and_status(tmp_path):
    count = tmp_path / "guard-count.txt"
    trace = tmp_path / "unexpected-git.txt"
    body = f'''set -e
. {shlex.quote(str(PUSH))}
push_retry_init 'synthetic nested preflight'
push_qledger_preflight() {{
  local n=0
  [ ! -f {shlex.quote(str(count))} ] || n=$(cat {shlex.quote(str(count))})
  n=$(( n + 1 ))
  printf '%s\\n' "$n" > {shlex.quote(str(count))}
  if [ "$n" -eq 1 ]; then return 0; fi
  printf 'nested native rejection\\n'
  return 79
}}
git() {{ printf 'unexpected git\\n' >> {shlex.quote(str(trace))}; return 99; }}
if push_fetch_main_for_rebase; then exit 90; else rc=$?; fi
printf 'RESULT=%s,%s,%s,%s\\n' "$rc" "$PUSH_FAIL_CLASS" "$PUSH_TERMINAL_RC" "$PUSH_N_OTHER"
'''
    result = shell(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert "RESULT=79,qledger-integrity,79,1" in result.stdout
    assert count.read_text().strip() == "2"
    assert not trace.exists()
