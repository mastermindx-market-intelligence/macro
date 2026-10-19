"""Bounded Git store maintenance for the /opt/macro production checkout.

2026-10-19 root-disk incident: every 3-minute pull landed a fetch pack, nothing
consolidated them (``gc.auto=0``), and ``/opt/macro/.git`` reached 41G in 263
packs. ``app/deploy/macro-git-store-maintenance.sh`` replaces auto-gc with a
nightly, fail-closed repack; ``update.sh`` self-arms its units and a journald
size cap.

Static contracts run everywhere. The functional tests run the REAL script
against hermetic local repositories (``file://`` origin, temp lock, temp
meminfo; no network, no systemd, no production path) and need the Linux tools
it calls (``flock``, ``ionice``, GNU ``df --output``), so they skip elsewhere.

Run: python -m pytest tests/test_deploy_git_store_maintenance.py -q
"""
from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "app" / "deploy"
SCRIPT = DEPLOY / "macro-git-store-maintenance.sh"
SERVICE = DEPLOY / "macro-git-store-maintenance.service"
TIMER = DEPLOY / "macro-git-store-maintenance.timer"
JOURNALD = DEPLOY / "journald-macro-vps.conf"

SCRIPT_TEXT = SCRIPT.read_text(encoding="utf-8")
UPDATE_TEXT = (DEPLOY / "update.sh").read_text(encoding="utf-8")
SETUP_TEXT = (DEPLOY / "setup.sh").read_text(encoding="utf-8")

DAY = 86400


def _commands(text: str) -> list[str]:
    return [
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


# ---------------------------------------------------------------------------
# Static contracts
# ---------------------------------------------------------------------------


def test_units_are_a_bounded_nightly_oneshot():
    service = SERVICE.read_text(encoding="utf-8")
    timer = TIMER.read_text(encoding="utf-8")
    assert "Type=oneshot" in service
    assert "ExecStart=/usr/local/sbin/macro-git-store-maintenance" in service
    # 75 = deferred (lock or memory busy): not a failed unit, retried next night.
    assert "SuccessExitStatus=75" in service
    assert "RuntimeMaxSec=" in service and "TimeoutStartSec=" in service
    assert "MemoryMax=" in service and "MemoryHigh=" in service
    assert "Nice=19" in service and "IOSchedulingClass=idle" in service
    assert "OnCalendar=*-*-* 02:40:00 UTC" in timer
    assert "Persistent=true" in timer
    assert "Unit=macro-git-store-maintenance.service" in timer


def test_update_sh_self_arms_the_maintenance_timer():
    assert "[ ! -f /usr/local/sbin/macro-git-store-maintenance ]" in UPDATE_TEXT
    assert "[ ! -f /etc/systemd/system/macro-git-store-maintenance.timer ]" in UPDATE_TEXT
    assert 'bash -n "$GIT_MAINT_SOURCE"' in UPDATE_TEXT
    assert 'systemd-analyze verify "${GIT_MAINT_UNIT_SOURCES[@]}"' in UPDATE_TEXT
    assert "systemctl enable --now macro-git-store-maintenance.timer" in UPDATE_TEXT
    assert "systemctl restart macro-git-store-maintenance.timer" in UPDATE_TEXT
    # The pull tick must never run the repack itself.
    assert "systemctl restart macro-git-store-maintenance.service" not in UPDATE_TEXT
    assert "systemctl start macro-git-store-maintenance.service" not in UPDATE_TEXT
    # systemd-analyze verify needs ExecStart's binary: install the script first.
    assert UPDATE_TEXT.index('install -m 0755 "$GIT_MAINT_SOURCE" "$GIT_MAINT_BIN"') < (
        UPDATE_TEXT.index('systemd-analyze verify "${GIT_MAINT_UNIT_SOURCES[@]}"')
    )


def test_journald_cap_is_installed_by_update_and_setup():
    conf = JOURNALD.read_text(encoding="utf-8")
    assert "[Journal]" in conf
    assert "SystemMaxUse=" in conf and "SystemKeepFree=" in conf
    dest = "/etc/systemd/journald.conf.d/10-macro-vps-cap.conf"
    assert f"JOURNALD_CAP={dest}" in UPDATE_TEXT
    assert f"[ ! -f {dest} ]" in UPDATE_TEXT
    assert dest in SETUP_TEXT and "journald-macro-vps.conf" in SETUP_TEXT


def test_script_never_alters_history_or_reenables_auto_gc():
    commands = _commands(SCRIPT_TEXT)
    for forbidden in (
        "--depth", "fetch", "unshallow", "deepen", "shallow", "git gc",
        "--filter", "filter-branch", "replace", "config gc.auto",
    ):
        offenders = [line for line in commands if forbidden in line]
        assert not offenders, f"maintenance script must not use {forbidden!r}: {offenders}"
    assert "set -euo pipefail" in SCRIPT_TEXT
    assert "--cruft" in SCRIPT_TEXT and "--cruft-expiration" in SCRIPT_TEXT
    assert "-c gc.auto=0" in SCRIPT_TEXT
    assert 'flock -w "$LOCK_WAIT" 9' in SCRIPT_TEXT


def test_no_deploy_script_turns_auto_gc_back_on():
    for path in sorted(DEPLOY.glob("*.sh")):
        for line in _commands(path.read_text(encoding="utf-8")):
            if "gc.auto" in line:
                assert "gc.auto=0" in line, f"{path.name} touches gc.auto: {line}"


def test_readme_recovery_pack_objects_writes_off_root():
    # pack-objects creates its temporary pack in the repository's own objects/pack and
    # renames it to the base name afterwards; across filesystems that rename fails with
    # EXDEV (seen on the droplet 2026-10-19). The off-root recipe must move the object
    # directory itself and read the old store through an alternate.
    readme = (DEPLOY / "README.md").read_text(encoding="utf-8")
    section = readme.split("Recovery when it REFUSES for space", 1)[1]
    block = section.split("```bash", 1)[1].split("```", 1)[0]
    assert "M=/mnt/terminal_storage/" in block
    command = next(
        line for line in _commands(block.replace("\\\n", " ")) if " pack-objects " in line
    )
    before, _, after = command.partition(" pack-objects ")
    assert 'GIT_OBJECT_DIRECTORY="$M/objects"' in before.split(), command
    assert "GIT_ALTERNATE_OBJECT_DIRECTORIES=/opt/macro/.git/objects" in before.split(), command
    assert '"$M/objects/pack/pack"' in after.split(), command


# ---------------------------------------------------------------------------
# Functional: the real script on hermetic repositories
# ---------------------------------------------------------------------------


def _gnu_df() -> bool:
    if not shutil.which("df"):
        return False
    probe = subprocess.run(
        ["df", "--output=avail", "-k", "."], capture_output=True, text=True, check=False,
    )
    return probe.returncode == 0


needs_linux_tools = pytest.mark.skipif(
    not (shutil.which("flock") and shutil.which("ionice") and _gnu_df()),
    reason="maintenance script needs flock, ionice and GNU df (Linux)",
)


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("GIT_"):
            env.pop(key)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_TERMINAL_PROMPT": "0",
    })
    return env


def git(repo: Path, *args: str, input_text: str | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        input=input_text, env=git_env(), check=False,
    )
    assert done.returncode == 0, f"git {' '.join(args)} failed: {done.stderr}"
    return done.stdout.strip()


def ok(repo: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=git_env(), check=False,
    ).returncode == 0


def packs(app: Path) -> set[str]:
    return {p.name for p in (app / ".git" / "objects" / "pack").glob("pack-*.pack")}


class Store:
    """origin (working repo) + a shallow production-like app checkout of it."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.origin = tmp / "origin"
        self.app = tmp / "app"
        self.lock = tmp / "macro-update.lock"
        self.meminfo = tmp / "meminfo"
        self.meminfo.write_text("MemTotal: 4000000 kB\nMemAvailable: 3000000 kB\n")
        self.origin.mkdir()
        git(self.origin, "init", "-q", "-b", "main")
        self.commits: list[str] = []
        for n in range(3):
            self.commit(n)
        subprocess.run(
            ["git", "clone", "-q", "--depth", "2", "--single-branch", "--branch", "main",
             f"file://{self.origin}", str(self.app)],
            capture_output=True, env=git_env(), check=True,
        )
        git(self.app, "config", "gc.auto", "0")
        # Production fetches are large enough to land as packs; mirror that.
        git(self.app, "config", "fetch.unpackLimit", "1")
        for n in range(3, 7):
            self.commit(n)
            self.pull()
        (self.app / ".git" / "gc.log").write_text("fatal: failed to run repack\n")

    def commit(self, n: int) -> None:
        (self.origin / "index.html").write_text(f"<html>revision {n}</html>\n" * 50)
        (self.origin / f"data-{n}.json").write_text(f'{{"n": {n}}}\n' * 200)
        git(self.origin, "add", "-A")
        git(self.origin, "commit", "-q", "-m", f"revision {n}")
        self.commits.append(git(self.origin, "rev-parse", "HEAD"))

    def pull(self) -> None:
        # update.sh's acquisition: connected fetch of main, then reset.
        git(self.app, "fetch", "-q", "origin", "main")
        git(self.app, "reset", "--hard", "-q", "FETCH_HEAD")

    def packed_unreachable_blob(self, text: str, age_days: float = 0) -> str:
        """An unreachable blob that exists ONLY inside its own pack."""
        sha = git(self.app, "hash-object", "-w", "--stdin", input_text=text)
        base = self.app / ".git" / "objects" / "pack" / "pack"
        name = git(self.app, "pack-objects", "-q", str(base), input_text=sha + "\n")
        git(self.app, "prune-packed")
        if age_days:
            then = time.time() - age_days * DAY
            for suffix in (".pack", ".idx"):
                os.utime(f"{base}-{name}{suffix}", (then, then))
        return sha

    def loose_unreachable_blob(self, text: str, age_days: float) -> str:
        sha = git(self.app, "hash-object", "-w", "--stdin", input_text=text)
        then = time.time() - age_days * DAY
        path = self.app / ".git" / "objects" / sha[:2] / sha[2:]
        os.utime(path, (then, then))
        return sha

    def run(self, script: Path = SCRIPT, **overrides: str) -> subprocess.CompletedProcess:
        env = git_env()
        env.update({
            "MACRO_GIT_MAINT_APP_DIR": str(self.app),
            "MACRO_GIT_MAINT_LOCK": str(self.lock),
            "MACRO_GIT_MAINT_LOCK_WAIT": "5",
            "MACRO_GIT_MAINT_MARGIN_KIB": "0",
            "MACRO_GIT_MAINT_MEMINFO": str(self.meminfo),
        })
        env.update(overrides)
        return subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=env, check=False,
            timeout=300,
        )


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    return Store(tmp_path)


@needs_linux_tools
def test_consolidates_packs_and_preserves_connected_history(store: Store):
    shallow_before = (store.app / ".git" / "shallow").read_bytes()
    head_before = git(store.app, "rev-parse", "HEAD")
    assert len(packs(store.app)) >= 4

    done = store.run()
    assert done.returncode == 0, done.stdout + done.stderr
    assert "store after:" in done.stdout

    assert len(packs(store.app)) == 1
    assert git(store.app, "rev-parse", "HEAD") == head_before
    assert (store.app / ".git" / "shallow").read_bytes() == shallow_before
    assert git(store.app, "config", "gc.auto") == "0"
    assert not (store.app / ".git" / "gc.log").exists()
    assert ok(store.app, "fsck", "--connectivity-only")
    # F04: an earlier published revision stays an ancestor; its bytes stay readable.
    assert ok(store.app, "merge-base", "--is-ancestor", store.commits[3], "HEAD")
    assert git(store.app, "show", f"{store.commits[3]}:data-3.json").startswith('{"n": 3}')

    # The next pull still works on the consolidated store.
    store.commit(7)
    store.pull()
    assert git(store.app, "rev-parse", "HEAD") == store.commits[7]
    assert ok(store.app, "merge-base", "--is-ancestor", head_before, "HEAD")


@needs_linux_tools
def test_unreachable_objects_keep_a_grace_period_then_go(store: Store):
    fresh_packed = store.packed_unreachable_blob("fresh packed garbage\n")
    old_packed = store.packed_unreachable_blob("old packed garbage\n", age_days=30)
    old_loose = store.loose_unreachable_blob("old loose garbage\n", age_days=30)

    done = store.run()
    assert done.returncode == 0, done.stdout + done.stderr

    assert ok(store.app, "cat-file", "-e", fresh_packed), "grace period not honoured"
    assert not ok(store.app, "cat-file", "-e", old_packed), "expired packed garbage kept"
    assert not ok(store.app, "cat-file", "-e", old_loose), "expired loose garbage kept"
    # Main pack + one cruft pack holding the fresh garbage.
    assert len(packs(store.app)) == 2
    assert len(list((store.app / ".git" / "objects" / "pack").glob("*.mtimes"))) == 1


@needs_linux_tools
def test_grace_assertion_fails_without_cruft(store: Store, tmp_path: Path):
    """Negative control: plain `repack -a -d` drops fresh garbage, so the grace test bites."""
    fresh_packed = store.packed_unreachable_blob("fresh packed garbage\n")
    mutated = tmp_path / "mutated.sh"
    text = SCRIPT_TEXT.replace('repack -d -l --cruft --cruft-expiration="$GRACE"', "repack -a -d -l")
    assert text != SCRIPT_TEXT
    mutated.write_text(text)

    done = store.run(script=mutated)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not ok(store.app, "cat-file", "-e", fresh_packed)


@needs_linux_tools
def test_stale_temporary_packs_are_removed_and_fresh_ones_kept(store: Store):
    pack_dir = store.app / ".git" / "objects" / "pack"
    stale = pack_dir / "tmp_pack_stale"
    fresh = pack_dir / "tmp_pack_fresh"
    stale.write_bytes(b"x" * 1024)
    fresh.write_bytes(b"x" * 1024)
    then = time.time() - 7 * 3600
    os.utime(stale, (then, then))

    done = store.run()
    assert done.returncode == 0, done.stdout + done.stderr
    assert not stale.exists()
    assert fresh.exists()


@needs_linux_tools
def test_refuses_without_space_and_writes_nothing(store: Store):
    before = packs(store.app)
    done = store.run(MACRO_GIT_MAINT_MARGIN_KIB=str(10**12))
    assert done.returncode == 1
    assert "REFUSED" in done.stdout
    assert packs(store.app) == before
    assert (store.app / ".git" / "gc.log").exists()


@needs_linux_tools
def test_defers_while_the_updater_holds_the_lock(store: Store):
    before = packs(store.app)
    with open(store.lock, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        done = store.run(MACRO_GIT_MAINT_LOCK_WAIT="1")
    assert done.returncode == 75
    assert "DEFERRED" in done.stdout
    assert packs(store.app) == before


@needs_linux_tools
def test_defers_when_memory_is_short(store: Store):
    before = packs(store.app)
    store.meminfo.write_text("MemTotal: 4000000 kB\nMemAvailable: 1000 kB\n")
    done = store.run()
    assert done.returncode == 75
    assert "DEFERRED: MemAvailable" in done.stdout
    assert packs(store.app) == before
