"""Fail-closed Options index-lock identity + macOS heredoc-hang regression."""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "ci" / "options_index_lock_identity.py"
SHELL = ROOT / "scripts" / "ci" / "options_signal_nightly.sh"


def helper(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), *map(str, args)],
        capture_output=True, text=True, timeout=8, check=False,
    )


def test_exclusive_lock_roundtrip(tmp_path):
    lock = tmp_path / "index.lock"
    got = helper("acquire", str(lock))
    assert got.returncode == 0 and re.fullmatch(r"\d+:\d+\n", got.stdout)
    assert lock.is_file() and lock.stat().st_size == 0
    assert got.stdout.strip() == f"{lock.stat().st_dev}:{lock.stat().st_ino}"
    released = helper("release", str(lock), got.stdout.strip())
    assert released.returncode == 0 and released.stdout == ""
    assert not lock.exists()


def test_existing_lock_never_overwritten(tmp_path):
    lock = tmp_path / "index.lock"
    lock.write_bytes(b"foreign index")
    assert helper("acquire", str(lock)).returncode != 0
    assert lock.read_bytes() == b"foreign index"


@pytest.mark.parametrize("identity", ["", "bogus", "1:2:3", "-1:-2"])
def test_wrong_or_malformed_owner_never_removes_lock(tmp_path, identity):
    lock = tmp_path / "index.lock"
    ok = helper("acquire", str(lock))
    assert ok.returncode == 0
    assert helper("release", str(lock), identity).returncode != 0
    assert lock.exists() and lock.stat().st_size == 0


def test_dirty_same_inode_refuses_release(tmp_path):
    lock = tmp_path / "index.lock"
    ok = helper("acquire", str(lock))
    assert ok.returncode == 0
    lock.write_bytes(b"staged index")
    assert helper("release", str(lock), ok.stdout.strip()).returncode != 0
    assert lock.read_bytes() == b"staged index"


def test_replaced_inode_is_not_owned(tmp_path):
    lock = tmp_path / "index.lock"
    ok = helper("acquire", str(lock))
    assert ok.returncode == 0
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"foreign index")
    os.replace(replacement, lock)
    assert helper("release", str(lock), ok.stdout.strip()).returncode != 0
    assert lock.read_bytes() == b"foreign index"


def test_hardlinked_lock_refused(tmp_path):
    lock = tmp_path / "index.lock"
    ok = helper("acquire", str(lock))
    assert ok.returncode == 0
    sibling = tmp_path / "other-hardlink"
    os.link(lock, sibling)
    assert helper("release", str(lock), ok.stdout.strip()).returncode != 0
    assert lock.exists() and sibling.exists()


def test_symlink_and_missing_identity_refused(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"unchanged")
    link = tmp_path / "index.lock"
    link.symlink_to(target)
    assert helper("acquire", str(link)).returncode != 0
    assert helper("release", str(link), "1:2").returncode != 0
    assert target.read_bytes() == b"unchanged"
    assert helper("release", str(tmp_path / "missing.lock"), "1:2").returncode != 0


def test_unsupported_arguments_do_not_mutate(tmp_path):
    lock = tmp_path / "index.lock"
    assert helper("acquire", str(lock), "extra").returncode != 0
    assert helper("unknown", str(lock)).returncode != 0
    assert not lock.exists()


@pytest.mark.skipif(os.name != "posix", reason="macOS/Linux bash subprocess test")
def test_sourced_bash_lock_substitution_does_not_hang(tmp_path):
    """Fails by timeout on the original inlined here-doc on affected M2 bash."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash unavailable")
    cmd = (
        'set -euo pipefail\n'
        'source "$GITHUB_WORKSPACE/scripts/ci/options_signal_nightly.sh"\n'
        'owner=$(oip_acquire_owned_empty_lock_identity "$TEST_LOCK")\n'
        'oip_release_owned_empty_lock "$TEST_LOCK" "$owner"\n'
        'test ! -e "$TEST_LOCK"\n'
        'printf "LOCK_ROUNDTRIP_PASS\\n"\n'
    )
    env = {**os.environ, "GITHUB_WORKSPACE": str(ROOT),
           "TEST_LOCK": str(tmp_path / "index.lock")}
    proc = subprocess.Popen(
        [bash, "-c", cmd], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        # Kill only our new isolated test session, never a live Actions job.
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate(timeout=2)
        pytest.fail("Bash here-doc lock-identity command substitution stalled")
    assert proc.returncode == 0, err[-700:]
    assert out == "LOCK_ROUNDTRIP_PASS\n"


def test_fill_refuses_a_changed_source_fingerprint(tmp_path):
    lock = tmp_path / "index.lock"
    identity = helper("acquire", lock).stdout.strip()
    source = tmp_path / "snapshot"
    source.write_bytes(b"validated snapshot")
    expected = helper("fingerprint", source).stdout.strip()
    source.write_bytes(b"later different snapshot")
    result = helper("fill", lock, identity, "empty", source, expected)
    assert result.returncode == 1 and result.stdout == "NOT_APPLIED\n"
    assert lock.read_bytes() == b""
    assert source.read_bytes() == b"later different snapshot"


def test_partial_descriptor_fill_has_unknown_outcome(tmp_path, monkeypatch, capsys):
    from scripts.ci import options_index_lock_identity as identity_helper

    lock = tmp_path / "index.lock"
    identity = helper("acquire", lock).stdout.strip()
    source = tmp_path / "snapshot"
    source.write_bytes(b"prepared index bytes")
    expected = helper("fingerprint", source).stdout.strip()
    real_write = identity_helper.os.write

    def partial_write(fd, data):
        real_write(fd, data[:4])
        raise OSError("injected partial descriptor write")

    monkeypatch.setattr(identity_helper.os, "write", partial_write)
    assert identity_helper.fill(str(lock), identity, "empty", str(source), expected) == 2
    assert capsys.readouterr().out == "UNKNOWN\n"
    assert lock.read_bytes() == b"prep"


def test_replacement_error_cannot_claim_non_application(tmp_path, monkeypatch, capsys):
    from scripts.ci import options_index_lock_identity as identity_helper

    lock = tmp_path / "index.lock"
    identity = helper("acquire", lock).stdout.strip()
    source = tmp_path / "snapshot"
    source.write_bytes(b"prepared index bytes")
    expected = helper("fingerprint", source).stdout.strip()
    assert helper("fill", lock, identity, "empty", source, expected).returncode == 0
    index = tmp_path / "index"
    index.write_bytes(b"old index")
    real_replace = identity_helper.os.replace

    def applied_then_error(src, dst):
        real_replace(src, dst)
        raise OSError("injected lost replacement acknowledgement")

    monkeypatch.setattr(identity_helper.os, "replace", applied_then_error)
    assert identity_helper.install(str(lock), identity, expected, str(index)) == 2
    assert capsys.readouterr().out == "UNKNOWN\n"
    assert index.read_bytes() == b"prepared index bytes"
    assert not lock.exists()
