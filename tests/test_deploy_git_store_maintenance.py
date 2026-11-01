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
import re
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

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
    # PROMOTE_KIB=0 would freeze every pack: a deferred run must freeze none, so
    # the memory gate has to come before the kept tier and the space fallback.
    before = packs(store.app)
    store.meminfo.write_text("MemTotal: 4000000 kB\nMemAvailable: 1000 kB\n")
    done = store.run(MACRO_GIT_MAINT_PROMOTE_KIB="0")
    assert done.returncode == 75
    assert "DEFERRED: MemAvailable" in done.stdout
    assert packs(store.app) == before
    assert _kept(store.app) == {}, "a deferred run froze packs"


@needs_linux_tools
def test_memory_deferral_assertion_fails_when_promotion_runs_first(store: Store, tmp_path: Path):
    """Negative control: promoting before the memory gate freezes packs on a deferred run."""
    mutated = tmp_path / "mutated.sh"
    anchor = 'MEMAVAIL_KIB=$(awk'
    assert SCRIPT_TEXT.count(anchor) == 1
    mutated.write_text(SCRIPT_TEXT.replace(anchor, "promote_large_packs\n" + anchor))
    store.meminfo.write_text("MemTotal: 4000000 kB\nMemAvailable: 1000 kB\n")
    done = store.run(script=mutated, MACRO_GIT_MAINT_PROMOTE_KIB="0")
    assert done.returncode == 75
    assert _kept(store.app), "mutation should have frozen packs before deferring"


# ---------------------------------------------------------------------------
# Kept tier (2026-11-01 second refill): large consolidated packs freeze, so a
# night rewrites only what arrived since the last promotion.
# ---------------------------------------------------------------------------


def _kept(app: Path) -> dict[str, str]:
    """pack file name -> .keep content, for every kept pack."""
    pack_dir = app / ".git" / "objects" / "pack"
    return {k.with_suffix(".pack").name: k.read_text() for k in pack_dir.glob("pack-*.keep")}


def _big_commit(store: Store, name: str, random_kib: int = 48) -> None:
    # Hex of random bytes packs to roughly random_kib KiB, so a pack's size is
    # predictable: 48 clears PROMOTE_SMALL on its own, 18 does not.
    _commit_file(store.origin, name, os.urandom(random_kib * 1024).hex() + "\n", f"big {name}")
    store.pull()


def _small_pulls(store: Store, first: int, count: int = 3) -> None:
    for n in range(first, first + count):
        store.commit(n)
        store.pull()


def _stub_df(tmp: Path, avail_kib: int | str) -> str:
    bin_dir = tmp / "stub-df"
    bin_dir.mkdir(exist_ok=True)
    df = bin_dir / "df"
    df.write_text(f"#!/bin/sh\necho '    Avail'\necho '  {avail_kib}'\n")
    df.chmod(0o755)
    return f"{bin_dir}:{os.environ['PATH']}"


def _kib(path: Path) -> int:
    return path.stat().st_size // 1024


PROMOTE_SMALL = "32"  # KiB: above any fixture fetch pack, below a big commit's pack


@needs_linux_tools
def test_large_consolidated_pack_joins_the_kept_tier_and_is_never_rewritten(store: Store):
    pack_dir = store.app / ".git" / "objects" / "pack"
    _big_commit(store, "blob-a.txt")
    # Night 1 (default threshold): one consolidated pack, nothing frozen yet.
    done = store.run()
    assert done.returncode == 0, done.stdout + done.stderr
    assert len(packs(store.app)) == 1 and _kept(store.app) == {}
    (base,) = packs(store.app)
    assert _kib(pack_dir / base) >= int(PROMOTE_SMALL)

    # Night 2: the base pack is frozen before the repack and survives it
    # byte-for-byte; only the day's small fetch packs are rewritten.
    _small_pulls(store, 7)
    base_stat = (pack_dir / base).stat()
    base_objects = _pack_contents(store.app, (pack_dir / base).with_suffix(".idx"))
    done = store.run(MACRO_GIT_MAINT_PROMOTE_KIB=PROMOTE_SMALL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "kept tier: " + base[:-5] in done.stdout
    assert list(_kept(store.app)) == [base]
    after = (pack_dir / base).stat()
    assert (after.st_ino, after.st_mtime, after.st_size) == (
        base_stat.st_ino, base_stat.st_mtime, base_stat.st_size)
    rest = packs(store.app) - {base}
    assert len(rest) == 1, packs(store.app)
    (day,) = rest
    day_objects = _pack_contents(store.app, (pack_dir / day).with_suffix(".idx"))
    assert day_objects and not (day_objects & base_objects), "kept objects were repacked"
    assert _kib(pack_dir / day) < int(PROMOTE_SMALL)
    assert ok(store.app, "fsck", "--connectivity-only")
    assert ok(store.app, "merge-base", "--is-ancestor", store.commits[3], "HEAD")

    # Night 3: three fetch packs, each below the threshold, consolidate into
    # one that clears it, so it is frozen AFTER the repack; the first base
    # pack is still untouched.
    for i in range(3):
        _big_commit(store, f"blob-b{i}.txt", random_kib=18)
    assert all(_kib(pack_dir / n) < int(PROMOTE_SMALL) for n in packs(store.app) - {base})
    done = store.run(MACRO_GIT_MAINT_PROMOTE_KIB=PROMOTE_SMALL)
    assert done.returncode == 0, done.stdout + done.stderr
    kept = _kept(store.app)
    assert base in kept and len(kept) == 2 and set(kept) == packs(store.app), kept
    assert all("macro-git-store-maintenance kept tier" in v for v in kept.values())
    assert (pack_dir / base).stat().st_ino == base_stat.st_ino
    assert ok(store.app, "fsck", "--connectivity-only")
    store.commit(20)
    store.pull()
    assert git(store.app, "rev-parse", "HEAD") == store.commits[-1]


@needs_linux_tools
def test_kept_tier_assertion_fails_without_promotion(store: Store, tmp_path: Path):
    """Negative control: without promotion the base pack is rewritten, so the test bites."""
    pack_dir = store.app / ".git" / "objects" / "pack"
    _big_commit(store, "blob-a.txt")
    assert store.run().returncode == 0
    (base,) = packs(store.app)
    _small_pulls(store, 7)
    mutated = tmp_path / "mutated.sh"
    text = SCRIPT_TEXT.replace("\npromote_large_packs\n", "\n:\n")
    assert text.count("promote_large_packs") == SCRIPT_TEXT.count("promote_large_packs") - 2
    mutated.write_text(text)
    done = store.run(script=mutated, MACRO_GIT_MAINT_PROMOTE_KIB=PROMOTE_SMALL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert _kept(store.app) == {}
    assert base not in packs(store.app) and len(packs(store.app)) == 1, "base pack survived"


@needs_linux_tools
def test_cruft_pack_is_never_frozen(store: Store):
    fresh = store.packed_unreachable_blob("fresh packed garbage\n")
    assert store.run().returncode == 0
    done = store.run(MACRO_GIT_MAINT_PROMOTE_KIB="0")
    assert done.returncode == 0, done.stdout + done.stderr
    pack_dir = store.app / ".git" / "objects" / "pack"
    cruft = list(pack_dir.glob("pack-*.mtimes"))
    assert len(cruft) == 1, "cruft pack must stay rewritable"
    assert not cruft[0].with_suffix(".keep").exists()
    assert len(_kept(store.app)) == 1
    assert ok(store.app, "cat-file", "-e", fresh), "grace period not honoured"


@needs_linux_tools
def test_a_keep_file_it_did_not_write_is_left_alone(store: Store):
    pack_dir = store.app / ".git" / "objects" / "pack"
    foreign = sorted(packs(store.app))[0]
    keep = (pack_dir / foreign).with_suffix(".keep")
    keep.write_text("fetch-pack 4242 on prod\n")
    done = store.run(MACRO_GIT_MAINT_PROMOTE_KIB="0")
    assert done.returncode == 0, done.stdout + done.stderr
    assert keep.read_text() == "fetch-pack 4242 on prod\n"
    assert (pack_dir / foreign).exists()


def _loose_kib(store: Store) -> int:
    return int(re.search(r"^size: (\d+)$", git(store.app, "count-objects", "-v"), re.M).group(1))


def _gate_fixture(store: Store) -> SimpleNamespace:
    """A frozen base pack plus measurable non-kept packs; the gate's own numbers."""
    pack_dir = store.app / ".git" / "objects" / "pack"
    _big_commit(store, "blob-a.txt")
    assert store.run().returncode == 0
    (base,) = packs(store.app)
    # Two measurable non-kept packs of different sizes (the small pulls' packs are
    # under 1 KiB each, so they count 0 KiB here and in the script alike).
    _big_commit(store, "blob-c.txt", random_kib=8)
    _big_commit(store, "blob-d.txt", random_kib=4)
    _small_pulls(store, 7)
    rest = packs(store.app) - {base}
    unkept = sum(_kib(pack_dir / n) for n in rest)
    assert 0 < unkept < int(PROMOTE_SMALL)
    margin = 10
    need = unkept + _loose_kib(store) + margin
    assert need < _kib(pack_dir / base) + unkept, "fixture must separate the two formulas"
    sizes = sorted((_kib(pack_dir / n) for n in rest), reverse=True)
    largest, second = sizes[0], sizes[1]
    assert 0 < second < largest < unkept, "fixture needs two measurable non-kept packs"
    return SimpleNamespace(pack_dir=pack_dir, base=base, rest=rest, unkept=unkept, need=need,
                           margin=margin, largest=largest, second=second,
                           loose=_loose_kib(store))


def _gate_run(store: Store, fx: SimpleNamespace, avail_kib: int, script: Path = SCRIPT,
              **overrides: str) -> subprocess.CompletedProcess:
    return store.run(script=script, MACRO_GIT_MAINT_PROMOTE_KIB=PROMOTE_SMALL,
                     MACRO_GIT_MAINT_MARGIN_KIB=str(fx.margin),
                     PATH=_stub_df(store.tmp, avail_kib), **overrides)


FALLBACK_LINE = re.compile(
    r"kept tier fallback: (pack-[0-9a-f]+) \((\d+) KiB\) frozen so the repack fits in (\d+) KiB")


def _fallback_frozen(stdout: str) -> list[tuple[str, int, int]]:
    """(pack file name, KiB, available KiB) for every fallback freeze, in log order."""
    return [(m.group(1) + ".pack", int(m.group(2)), int(m.group(3)))
            for m in FALLBACK_LINE.finditer(stdout)]


def _assert_refused_unchanged(done: subprocess.CompletedProcess, fx: SimpleNamespace,
                              before: set[str], need: int) -> None:
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"REFUSED: repack needs {need} KiB" in done.stdout
    assert "would not make the repack fit; nothing frozen" in done.stdout
    assert not _fallback_frozen(done.stdout)
    assert packs(done_store_app(fx)) == before
    assert list(_kept(done_store_app(fx))) == [fx.base]


def done_store_app(fx: SimpleNamespace) -> Path:
    return fx.pack_dir.parents[2]


def _mutate(tmp_path: Path, old: str, new: str) -> Path:
    assert SCRIPT_TEXT.count(old) == 1, old
    mutated = tmp_path / "mutated.sh"
    mutated.write_text(SCRIPT_TEXT.replace(old, new))
    return mutated


FALLBACK_STOP = '\t\tif [ "$PLAN_NEED_KIB" -le "$AVAIL_KIB" ]; then break; fi\n'
FALLBACK_CAP = '\t\tif [ "${#FALLBACK_PLAN[@]}" -ge "$FALLBACK_MAX" ]; then break; fi\n'
FALLBACK_PLAN_ADD = '\t\tFALLBACK_PLAN+=("$kib $base")\n'
FALLBACK_SOURCE = "\tdone < <(fallback_candidates)\n"


@needs_linux_tools
def test_space_gate_counts_only_what_the_repack_rewrites(store: Store):
    """Need = non-kept packs + loose + margin. Kept bytes never count."""
    fx = _gate_fixture(store)
    enough = _gate_run(store, fx, fx.need)
    assert enough.returncode == 0, enough.stdout + enough.stderr
    assert "kept tier fallback" not in enough.stdout
    assert list(_kept(store.app)) == [fx.base]
    assert fx.base in packs(store.app) and len(packs(store.app)) == 2


@needs_linux_tools
def test_space_fallback_freezes_only_the_largest_pack_when_that_is_enough(store: Store):
    # 1 KiB short: freezing the largest non-kept pack is enough, so only it is
    # frozen, the rest is repacked, and the frozen pack survives byte-for-byte.
    fx = _gate_fixture(store)
    fits = _gate_run(store, fx, fx.need - 1)
    assert fits.returncode == 0, fits.stdout + fits.stderr
    frozen = _fallback_frozen(fits.stdout)
    assert len(frozen) == 1, fits.stdout
    ((name, kib, avail),) = frozen
    assert name in fx.rest and kib == fx.largest == _kib(fx.pack_dir / name)
    assert avail == fx.need - 1
    kept = _kept(store.app)
    assert set(kept) == {fx.base, name}, kept
    assert kept[name].startswith("macro-git-store-maintenance kept tier (space fallback)")
    assert f"rewriting {fx.unkept - fx.largest} KiB of non-kept packs" in fits.stdout
    after = packs(store.app)
    assert {fx.base, name} < after and len(after) == 3, after
    assert ok(store.app, "fsck", "--connectivity-only")
    store.commit(30)
    store.pull()
    assert git(store.app, "rev-parse", "HEAD") == store.commits[-1]


@needs_linux_tools
def test_space_fallback_freezes_packs_largest_first_until_the_repack_fits(store: Store):
    # Freezing the largest leaves it 1 KiB short; the second-largest closes it.
    fx = _gate_fixture(store)
    fits = _gate_run(store, fx, fx.need - fx.largest - 1)
    assert fits.returncode == 0, fits.stdout + fits.stderr
    frozen = _fallback_frozen(fits.stdout)
    assert [kib for _, kib, _ in frozen] == [fx.largest, fx.second], fits.stdout
    names = {name for name, _, _ in frozen}
    assert names < fx.rest
    kept = _kept(store.app)
    assert set(kept) == {fx.base} | names, kept
    assert all(kept[n].startswith("macro-git-store-maintenance kept tier (space fallback)")
               for n in names)
    assert f"rewriting {fx.unkept - fx.largest - fx.second} KiB of non-kept packs" in fits.stdout
    assert ok(store.app, "fsck", "--connectivity-only")
    store.commit(31)
    store.pull()
    assert git(store.app, "rev-parse", "HEAD") == store.commits[-1]


@needs_linux_tools
def test_space_fallback_freezes_nothing_when_it_cannot_make_the_repack_fit(store: Store):
    fx = _gate_fixture(store)
    before = packs(store.app)
    # Freezing every eligible pack still leaves loose + margin 1 KiB short.
    _assert_refused_unchanged(_gate_run(store, fx, fx.loose + fx.margin - 1), fx, before, fx.need)
    # The cap: one pack may be frozen, which is not enough at this space...
    capped = _gate_run(store, fx, fx.need - fx.largest - 1, MACRO_GIT_MAINT_FALLBACK_MAX="1")
    _assert_refused_unchanged(capped, fx, before, fx.need)
    assert "freezing up to 1 packs would not make the repack fit" in capped.stdout
    # ...and the same space fits once two may be frozen.
    fits = _gate_run(store, fx, fx.need - fx.largest - 1, MACRO_GIT_MAINT_FALLBACK_MAX="2")
    assert fits.returncode == 0, fits.stdout + fits.stderr
    assert len(_fallback_frozen(fits.stdout)) == 2


@needs_linux_tools
def test_space_fallback_is_off_when_its_cap_is_zero(store: Store):
    fx = _gate_fixture(store)
    before = packs(store.app)
    done = _gate_run(store, fx, fx.need - 1, MACRO_GIT_MAINT_FALLBACK_MAX="0")
    _assert_refused_unchanged(done, fx, before, fx.need)
    assert "freezing up to 0 packs would not make the repack fit" in done.stdout


@needs_linux_tools
def test_space_fallback_assertions_fail_on_mutated_fallbacks(store: Store, tmp_path: Path):
    """Negative controls: each fallback test above bites on the behaviour it pins."""
    fx = _gate_fixture(store)
    before = packs(store.app)
    # No fallback at all: 1 KiB short refuses.
    none = _gate_run(store, fx, fx.need - 1,
                     script=_mutate(tmp_path, FALLBACK_SOURCE, "\tdone </dev/null\n"))
    assert none.returncode == 1 and "REFUSED: repack needs" in none.stdout
    # One pack only (no greedy continuation): largest-plus-1 short refuses.
    single = _gate_run(store, fx, fx.need - fx.largest - 1,
                       script=_mutate(tmp_path, FALLBACK_STOP, "\t\tbreak\n"))
    assert single.returncode == 1 and "REFUSED: repack needs" in single.stdout
    assert packs(store.app) == before and list(_kept(store.app)) == [fx.base]
    # Freezing while planning (not all-or-nothing): a plan that does not fit
    # still leaves .keep files behind.
    eager = _gate_run(store, fx, fx.loose + fx.margin - 1, script=_mutate(
        tmp_path, FALLBACK_PLAN_ADD, FALLBACK_PLAN_ADD + '\t\t: >"$base.keep"\n'))
    assert eager.returncode == 1
    assert len(_kept(store.app)) > 1, "mutation should have left planned packs frozen"
    for keep in fx.pack_dir.glob("pack-*.keep"):
        if keep.with_suffix(".pack").name != fx.base:
            keep.unlink()
    # No cap: FALLBACK_MAX=1 no longer stops it.
    uncapped = _gate_run(store, fx, fx.need - fx.largest - 1, MACRO_GIT_MAINT_FALLBACK_MAX="1",
                         script=_mutate(tmp_path, FALLBACK_CAP, ""))
    assert uncapped.returncode == 0, uncapped.stdout + uncapped.stderr
    assert len(_fallback_frozen(uncapped.stdout)) == 2


def _orphan(pack_dir: Path, source: Path, tag: str, age_hours: float, size_kib: int = 0) -> Path:
    """A .pack (+ .rev) with no .idx, as an interrupted pack write leaves it."""
    pack = pack_dir / f"pack-{tag * 40}.pack"
    pack.write_bytes(source.read_bytes() + os.urandom(size_kib * 1024))
    pack.with_suffix(".rev").write_bytes(b"RIDX")
    then = time.time() - age_hours * 3600
    for f in (pack, pack.with_suffix(".rev")):
        os.utime(f, (then, then))
    return pack


@needs_linux_tools
def test_orphan_packs_are_removed_after_six_hours_and_never_counted(store: Store, tmp_path: Path):
    pack_dir = store.app / ".git" / "objects" / "pack"
    source = pack_dir / sorted(packs(store.app))[0]
    old = _orphan(pack_dir, source, "a", age_hours=7)
    fresh = _orphan(pack_dir, source, "b", age_hours=1, size_kib=200)
    owned = _orphan(pack_dir, source, "c", age_hours=7)
    owned.with_suffix(".keep").write_text("fetch-pack 4242 on prod\n")
    indexed = {n for n in packs(store.app) if (pack_dir / n).with_suffix(".idx").exists()}
    need = sum(_kib(pack_dir / n) for n in indexed) + _loose_kib(store)

    # Exactly the indexed packs' worth of space: the 200 KiB fresh orphan must not count.
    done = store.run(PATH=_stub_df(store.tmp, need))
    assert done.returncode == 0, done.stdout + done.stderr
    assert not old.exists() and not old.with_suffix(".rev").exists()
    assert f"removed orphan {old.stem}.pack (no .idx, older than 6 h)" in done.stdout
    assert f"removed orphan {old.stem}.rev (no .idx, older than 6 h)" in done.stdout
    assert fresh.exists() and fresh.with_suffix(".rev").exists(), "a write in progress was removed"
    assert owned.exists() and owned.with_suffix(".keep").read_text() == "fetch-pack 4242 on prod\n"
    assert "removed orphan " + fresh.stem not in done.stdout
    assert "removed orphan " + owned.stem not in done.stdout
    assert ok(store.app, "fsck", "--connectivity-only")

    # Negative control: counting idx-less packs (the old formula) refuses at that space.
    mutated = tmp_path / "mutated.sh"
    text = SCRIPT_TEXT.replace('[ -e "${p%.pack}.idx" ] || continue\n\t\tsum=', "sum=")
    assert text != SCRIPT_TEXT
    mutated.write_text(text)
    indexed = {n for n in packs(store.app) if (pack_dir / n).with_suffix(".idx").exists()}
    need = sum(_kib(pack_dir / n) for n in indexed) + _loose_kib(store)
    counted = store.run(script=mutated, PATH=_stub_df(store.tmp, need))
    assert counted.returncode == 1, counted.stdout + counted.stderr
    assert "REFUSED: repack needs" in counted.stdout


@needs_linux_tools
@pytest.mark.parametrize(
    "setting", ["LOCK_WAIT", "MARGIN_KIB", "MIN_MEMAVAIL_KIB", "PROMOTE_KIB", "FALLBACK_MAX"])
def test_a_non_numeric_setting_refuses_before_anything_is_written(store: Store, setting: str):
    before = packs(store.app)
    refs = git(store.app, "for-each-ref")
    done = store.run(**{f"MACRO_GIT_MAINT_{setting}": "3G"})
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"REFUSED: {setting}='3G' is not a whole number; nothing written" in done.stdout
    assert packs(store.app) == before and git(store.app, "for-each-ref") == refs
    assert (store.app / ".git" / "gc.log").exists()


@needs_linux_tools
@pytest.mark.parametrize("reading", ["n/a", "", "12.5"])
def test_unreadable_free_space_refuses(store: Store, reading: str):
    before = packs(store.app)
    done = store.run(PATH=_stub_df(store.tmp, reading))
    assert done.returncode == 1, done.stdout + done.stderr
    assert "REFUSED: could not read free space" in done.stdout
    assert packs(store.app) == before


@needs_linux_tools
def test_missing_memavailable_refuses(store: Store):
    before = packs(store.app)
    store.meminfo.write_text("MemTotal: 4000000 kB\nMemFree: 3000000 kB\n")
    done = store.run()
    assert done.returncode == 1, done.stdout + done.stderr
    assert "REFUSED: could not read MemAvailable" in done.stdout
    assert packs(store.app) == before


# ---------------------------------------------------------------------------
# update.sh root-disk floor (refuses the pull before it writes)
# ---------------------------------------------------------------------------

GUARD_BEGIN = "# BEGIN MACRO_UPDATE_FREE_SPACE_GUARD\n"
GUARD_END = "# END MACRO_UPDATE_FREE_SPACE_GUARD\n"
SELECT_BEGIN = "# BEGIN MACRO_UPDATE_PULL_SELECT\n"
SELECT_END = "# END MACRO_UPDATE_PULL_SELECT\n"
# FETCH_HEAD is read only on the branch that fetched.
SELECT_NEW = ('if [ "$DISK_REFUSED" -eq 1 ]; then\n\tNEW=$OLD\nelse\n'
              '\tNEW=$(git -C "$APP_DIR" rev-parse FETCH_HEAD)\nfi\n')
# The pre-2026-11-01 order: read FETCH_HEAD, then override it on a refused tick.
SELECT_NEW_OLD_ORDER = ('NEW=$(git -C "$APP_DIR" rev-parse FETCH_HEAD)\n'
                        'if [ "$DISK_REFUSED" -eq 1 ]; then NEW=$OLD; fi\n')
PRINT_SELECT = 'echo "PASSED_SELECT OLD=$OLD NEW=$NEW"'


def _select_stanza() -> str:
    start = UPDATE_TEXT.index(SELECT_BEGIN)
    return UPDATE_TEXT[start:UPDATE_TEXT.index(SELECT_END, start)]


def _run_free_space_guard(
    tmp: Path, avail_kib: int | str, floor: str | None = None, df_rc: int = 0,
    app: Path | None = None, after: str = "",
) -> tuple[subprocess.CompletedProcess, Path]:
    start = UPDATE_TEXT.index(GUARD_BEGIN)
    stanza = UPDATE_TEXT[start:UPDATE_TEXT.index(GUARD_END, start)]
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "df").write_text(
        f"#!/bin/sh\necho \"$@\" >> '{tmp}/df.args'\necho '    Avail'\necho '  {avail_kib}'\n"
        f"exit {df_rc}\n")
    (bin_dir / "logger").write_text(f"#!/bin/sh\necho \"$@\" >> '{tmp}/logger.log'\n")
    for tool in ("df", "logger"):
        (bin_dir / tool).chmod(0o755)
    if app is None:
        app = tmp / "app"
        (app / ".git" / "objects").mkdir(parents=True, exist_ok=True)
    marker = tmp / "disk-refused"
    harness = "\n".join([
        "set -euo pipefail",
        f"APP_DIR='{app}'",
        stanza,
        'echo "PASSED_GUARD DISK_REFUSED=$DISK_REFUSED"',
        after,
    ])
    env = git_env()
    env.pop("MACRO_UPDATE_MIN_FREE_KIB", None)
    if floor is not None:
        env["MACRO_UPDATE_MIN_FREE_KIB"] = floor
    env.update({"PATH": f"{bin_dir}:{env['PATH']}", "MACRO_UPDATE_DISK_MARKER": str(marker)})
    done = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, env=env,
                          check=False, timeout=60)
    return done, marker


FLOOR_KIB = 7 * 1024 * 1024


def test_update_refuses_the_pull_below_the_root_disk_floor(tmp_path: Path):
    # The guard never exits on its own: the tick goes on to reconcile the current
    # checkout (timers, units) and the exit-status block fails it at the end.
    done, marker = _run_free_space_guard(tmp_path, FLOOR_KIB - 1)
    assert done.returncode == 0, done.stderr
    assert "PASSED_GUARD DISK_REFUSED=1" in done.stdout
    assert f"macro-update: REFUSED pull: {FLOOR_KIB - 1} KiB free" in done.stderr
    assert f"floor {FLOOR_KIB} KiB; nothing pulled" in done.stderr
    assert "-p user.err -t macro-update" in (tmp_path / "logger.log").read_text()
    assert "REFUSED pull" in marker.read_text()
    assert ".git/objects" in (tmp_path / "df.args").read_text()


def test_update_pulls_at_the_floor_and_clears_the_refusal_marker(tmp_path: Path):
    (tmp_path / "disk-refused").write_text("stale refusal\n")
    done, marker = _run_free_space_guard(tmp_path, FLOOR_KIB)
    assert done.returncode == 0, done.stderr
    assert "PASSED_GUARD DISK_REFUSED=0" in done.stdout
    assert not marker.exists()
    assert not (tmp_path / "logger.log").exists()


@pytest.mark.parametrize(("reading", "df_rc", "shown"), [
    ("n/a", 0, "n/a"), ("", 0, "unreadable"), ("99999999", 1, "unreadable"),
    ("12.5", 0, "12.5"),
])
def test_update_refuses_when_free_space_is_unreadable(
    tmp_path: Path, reading: str, df_rc: int, shown: str,
):
    done, marker = _run_free_space_guard(tmp_path, reading, df_rc=df_rc)
    assert done.returncode == 0, done.stderr
    assert "PASSED_GUARD DISK_REFUSED=1" in done.stdout
    assert f"REFUSED pull: {shown} KiB free" in done.stderr
    assert "REFUSED pull" in marker.read_text()


def test_update_refuses_when_the_floor_setting_is_not_a_number(tmp_path: Path):
    done, marker = _run_free_space_guard(tmp_path, 10 * FLOOR_KIB, floor="7G")
    assert done.returncode == 0, done.stderr
    assert "PASSED_GUARD DISK_REFUSED=1" in done.stdout
    assert "floor 7G KiB; nothing pulled" in done.stderr
    assert marker.exists()


def test_free_space_guard_runs_under_the_lock_and_before_the_pull():
    lock = UPDATE_TEXT.index("flock -n 9 || exit 0")
    guard = UPDATE_TEXT.index(GUARD_BEGIN)
    select = UPDATE_TEXT.index(SELECT_BEGIN)
    pull = UPDATE_TEXT.index('git -C "$APP_DIR" fetch -q origin main')
    select_end = UPDATE_TEXT.index(SELECT_END)
    reset = UPDATE_TEXT.index('git -C "$APP_DIR" reset --hard -q FETCH_HEAD')
    assert lock < guard < select < pull < select_end < reset
    between = UPDATE_TEXT[UPDATE_TEXT.index(GUARD_END, guard):select]
    assert "# Do not add --depth here" in between
    assert UPDATE_TEXT.count(GUARD_BEGIN) == 1 and UPDATE_TEXT.count(SELECT_BEGIN) == 1
    stanza = UPDATE_TEXT[guard:UPDATE_TEXT.index(GUARD_END, guard)]
    assert not [c for c in _commands(stanza) if re.search(r"\bexit\b", c)], (
        "the guard must not end the tick: reconciliation still has to run")
    # A refused tick fetches nothing and never reads FETCH_HEAD, so it can
    # neither abort on an empty one nor deploy a stale one.
    block = _select_stanza()
    assert 'if [ "$DISK_REFUSED" -eq 0 ]; then\n\tgit -C "$APP_DIR" fetch -q origin main\nfi' in block
    assert SELECT_NEW in block
    assert UPDATE_TEXT.count("rev-parse FETCH_HEAD") == 1


def test_a_refused_tick_is_a_no_change_tick_until_its_exit_status():
    # Below the pull selection a refused tick must look exactly like a
    # no-change tick: nothing there may branch on the refusal.
    rest = UPDATE_TEXT[UPDATE_TEXT.index(SELECT_END):
                       UPDATE_TEXT.index("# BEGIN DISK_REFUSAL_EXIT_STATUS\n")]
    assert "DISK_REFUSED" not in rest


def _update_pull_fixture(tmp: Path) -> SimpleNamespace:
    """origin with one commit the app checkout has not pulled yet."""
    origin, app = tmp / "origin", tmp / "app"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    _commit_file(origin, "index.html", "v1\n", "c1")
    _commit_file(origin, "index.html", "v2\n", "c2")
    git(tmp, "clone", "-q", "--single-branch", "--branch", "main", f"file://{origin}", str(app))
    _commit_file(origin, "index.html", "v3\n", "c3")
    return SimpleNamespace(app=app, head=git(app, "rev-parse", "HEAD"),
                           tip=git(origin, "rev-parse", "HEAD"))


def _refused_select_run(tmp: Path, fetch_head: str, block: str) -> tuple[
        subprocess.CompletedProcess, SimpleNamespace]:
    fx = _update_pull_fixture(tmp)
    fetch_head_file = fx.app / ".git" / "FETCH_HEAD"
    if fetch_head == "stale":
        git(fx.app, "fetch", "-q", "origin", "main")
        assert git(fx.app, "rev-parse", "FETCH_HEAD") == fx.tip != fx.head
    elif fetch_head == "empty":
        fetch_head_file.write_text("")  # what a fetch that failed part-way leaves
    else:
        fetch_head_file.unlink(missing_ok=True)
    # Any fetch on a refused tick would now fail the harness.
    git(fx.app, "remote", "set-url", "origin", str(tmp / "no-such-origin"))
    done, _ = _run_free_space_guard(tmp, FLOOR_KIB - 1, app=fx.app,
                                    after=block + "\n" + PRINT_SELECT)
    return done, fx


@pytest.mark.parametrize("fetch_head", ["empty", "missing", "stale"])
def test_a_refused_tick_gets_past_the_pull_selection_with_no_change(tmp_path: Path, fetch_head: str):
    done, fx = _refused_select_run(tmp_path, fetch_head, _select_stanza())
    assert done.returncode == 0, done.stdout + done.stderr
    assert "PASSED_GUARD DISK_REFUSED=1" in done.stdout
    assert f"PASSED_SELECT OLD={fx.head} NEW={fx.head}" in done.stdout
    assert git(fx.app, "rev-parse", "HEAD") == fx.head
    assert git(fx.app, "status", "--porcelain") == ""


@pytest.mark.parametrize("fetch_head", ["empty", "missing"])
def test_refused_tick_assertion_fails_with_the_old_fetch_head_read(tmp_path: Path, fetch_head: str):
    """Negative control: reading FETCH_HEAD before the refusal check aborts the tick."""
    block = _select_stanza()
    assert SELECT_NEW in block
    done, _ = _refused_select_run(tmp_path, fetch_head,
                                  block.replace(SELECT_NEW, SELECT_NEW_OLD_ORDER))
    assert done.returncode != 0, done.stdout
    assert "PASSED_GUARD DISK_REFUSED=1" in done.stdout
    assert "PASSED_SELECT" not in done.stdout


def test_a_tick_above_the_floor_fetches_and_selects_the_new_tip(tmp_path: Path):
    fx = _update_pull_fixture(tmp_path)
    done, marker = _run_free_space_guard(tmp_path, FLOOR_KIB, app=fx.app,
                                         after=_select_stanza() + "\n" + PRINT_SELECT)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "PASSED_GUARD DISK_REFUSED=0" in done.stdout
    assert f"PASSED_SELECT OLD={fx.head} NEW={fx.tip}" in done.stdout
    assert not marker.exists()


def test_a_refused_pull_fails_the_tick_after_reconciliation():
    begin = UPDATE_TEXT.index("# BEGIN DISK_REFUSAL_EXIT_STATUS\n")
    end = UPDATE_TEXT.index("# END DISK_REFUSAL_EXIT_STATUS\n")
    block = UPDATE_TEXT[begin:end]
    assert 'if [ "${DISK_REFUSED:-0}" -eq 1 ]; then' in block
    assert "DEPLOY_EXIT_STATUS=1" in block
    assert UPDATE_TEXT.index("# END OHLC_DELIVERY_EXIT_STATUS\n") < begin
    assert end < UPDATE_TEXT.index("# BEGIN DEPLOY_EXIT_STATUS\n")
    assert end < UPDATE_TEXT.rindex('exit "${DEPLOY_EXIT_STATUS:-0}"')


def _pack_contents(repo: Path, idx: Path) -> set[str]:
    with idx.open("rb") as fh:
        done = subprocess.run(
            ["git", "-C", str(repo), "show-index"], stdin=fh, capture_output=True,
            text=True, env=git_env(), check=True,
        )
    return {line.split()[1] for line in done.stdout.splitlines()}


def _commit_file(repo: Path, name: str, text: str, message: str) -> None:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-qm", message)


def _rescue_fixture(tmp_path: Path) -> SimpleNamespace:
    # A fetch below transfer.unpackLimit is unpacked loose and SKIPS objects that are
    # already packed (on the droplet 2026-10-19 a 07:39 pull re-freshened two 2026-10-18
    # packs instead of writing loose copies). An object unreachable at the snapshot is not
    # in the consolidated pack, so retiring the old packs loses it unless the recipe's
    # rescue step packs it first. Runs the README's own rescue command.
    readme = (DEPLOY / "README.md").read_text(encoding="utf-8")
    section = readme.split("Recovery when it REFUSES for space", 1)[1].split("\n### ", 1)[0]
    found = re.search(r"`(sed 's/\^/\^/' [^`]+)`", section)
    assert found, "recipe lost its rescue step"
    rescue = " ".join(found.group(1).split())
    assert "--local" in rescue and "--honor-pack-keep" in rescue, rescue

    src, origin, prod, maint = (tmp_path / n for n in ("src", "origin.git", "prod", "maint"))
    src.mkdir()
    git(src, "init", "-q", "-b", "main")
    for n in range(4):
        _commit_file(src, f"f{n}", f"v{n}\n", f"c{n}")
    git(tmp_path, "clone", "-q", "--bare", str(src), str(origin))
    git(tmp_path, "clone", "-q", "--depth", "2", f"file://{origin}", str(prod))
    # Old pack 2 holds blob X from a side commit that is then made unreachable.
    git(prod, "checkout", "-q", "-b", "side")
    _commit_file(prod, "x", "rescue-me\n", "side")
    x = git(prod, "rev-parse", "HEAD:x")
    git(prod, "repack", "-q", "-d")
    git(prod, "checkout", "-q", "main")
    git(prod, "branch", "-q", "-D", "side")
    git(prod, "reflog", "expire", "--expire=now", "--expire-unreachable=now", "--all")
    pack_dir = prod / ".git" / "objects" / "pack"
    old_packs = sorted(pack_dir.glob("pack-*.pack"))
    tips = maint / "old-tips.txt"
    (maint / "objects" / "pack").mkdir(parents=True)
    tips.write_text(git(prod, "for-each-ref", "--format=%(objectname)") + "\n")
    env = {**git_env(), "GIT_OBJECT_DIRECTORY": str(maint / "objects"),
           "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(prod / ".git" / "objects")}
    subprocess.run(
        ["git", "-C", str(prod), "pack-objects", "-q", "--all", "--reflog",
         "--indexed-objects", str(maint / "objects" / "pack" / "pack")],
        stdin=subprocess.DEVNULL, capture_output=True, env=env, check=True,
    )
    new_idx = next((maint / "objects" / "pack").glob("pack-*.idx"))
    assert x not in _pack_contents(prod, new_idx)
    # Post-snapshot small fetch reusing X: unpacked loose, X skipped as already packed.
    _commit_file(src, "x", "rescue-me\n", "c-reuse")
    git(origin, "fetch", "-q", str(src), "main:main")
    git(prod, "-c", "transfer.unpackLimit=1000", "fetch", "-q", "origin", "main")
    git(prod, "reset", "-q", "--hard", "FETCH_HEAD")
    assert not (prod / ".git" / "objects" / x[:2] / x[2:]).exists()
    # Post-snapshot large fetch, kept as its own pack.
    for n in range(30):
        (src / f"b{n}").write_text(f"big{n}\n")
    git(src, "add", ".")
    git(src, "commit", "-qm", "c-big")
    git(origin, "fetch", "-q", str(src), "main:main")
    git(prod, "-c", "transfer.unpackLimit=1", "fetch", "-q", "origin", "main")
    git(prod, "reset", "-q", "--hard", "FETCH_HEAD")
    post_packs = sorted(set(pack_dir.glob("pack-*.pack")) - set(old_packs))
    assert len(post_packs) == 1
    post_objects = _pack_contents(prod, post_packs[0].with_suffix(".idx"))
    (prod / ".git" / "objects" / "info" / "alternates").write_text(f"{maint / 'objects'}\n")
    retired = tmp_path / "retired"

    def retire_old_packs() -> None:
        retired.mkdir()
        for pack in old_packs:
            for ext in (".pack", ".idx", ".rev"):
                if pack.with_suffix(ext).exists():
                    pack.with_suffix(ext).rename(retired / pack.with_suffix(ext).name)

    def restore_old_packs() -> None:
        for f in sorted(retired.iterdir(), key=lambda f: f.suffix != ".pack"):
            f.rename(pack_dir / f.name)
        retired.rmdir()

    def run_rescue() -> set[Path]:
        """The README's rescue step: keep post-snapshot packs, rescue, unkeep them."""
        before = set(pack_dir.glob("pack-*.pack"))
        touched = [p for p in post_packs if not p.with_suffix(".keep").exists()]
        for pack in touched:
            pack.with_suffix(".keep").touch()
        command = rescue.replace('"$M/old-tips.txt"', f"'{tips}'").replace("/opt/macro", str(prod))
        subprocess.run(["bash", "-c", command], capture_output=True, env=git_env(), check=True)
        for pack in touched:
            pack.with_suffix(".keep").unlink()
        return set(pack_dir.glob("pack-*.pack")) - before

    return SimpleNamespace(prod=prod, x=x, pack_dir=pack_dir, old_packs=old_packs,
                           post_objects=post_objects, new_idx=new_idx, retire=retire_old_packs,
                           restore=restore_old_packs, run_rescue=run_rescue)


def test_readme_recovery_rescues_old_objects_that_a_small_fetch_reused(tmp_path: Path):
    fx = _rescue_fixture(tmp_path)
    # Falsifier: without the rescue the swap's fsck must fail on this fixture.
    fx.retire()
    assert not ok(fx.prod, "fsck", "--connectivity-only", "--no-dangling")
    fx.restore()

    (rescued,) = fx.run_rescue()
    rescued_objects = _pack_contents(fx.prod, rescued.with_suffix(".idx"))
    assert fx.x in rescued_objects
    assert not rescued_objects & fx.post_objects, "rescue duplicated a kept post-snapshot pack"
    assert not rescued_objects & _pack_contents(fx.prod, fx.new_idx), "rescue duplicated the new pack"

    fx.retire()
    assert ok(fx.prod, "fsck", "--connectivity-only", "--no-dangling")
    assert ok(fx.prod, "cat-file", "-e", fx.x)


def test_readme_recovery_moves_kept_tier_keeps_aside_before_the_rescue(tmp_path: Path):
    # The nightly job freezes large old packs with a .keep. The rescue honors .keep
    # files, so a kept-tier .keep on an old pack hides that pack's objects from the
    # rescue, and retiring the old packs then loses them. The recipe moves those
    # .keep files aside first; this proves both the loss and the step that avoids it.
    readme = " ".join((DEPLOY / "README.md").read_text(encoding="utf-8").split())
    assert "Move the `.keep` of every pack in `old-packs.txt` aside first" in readme
    fx = _rescue_fixture(tmp_path)
    (holder,) = [p for p in fx.old_packs
                 if fx.x in _pack_contents(fx.prod, p.with_suffix(".idx"))]
    keep = holder.with_suffix(".keep")
    keep.write_text("macro-git-store-maintenance kept tier 2026-11-01T03:40:00Z\n")

    # Rescue with the kept-tier .keep still in place: X is skipped and then lost.
    skipped = fx.run_rescue()
    for pack in skipped:
        assert fx.x not in _pack_contents(fx.prod, pack.with_suffix(".idx"))
    fx.retire()
    assert not ok(fx.prod, "fsck", "--connectivity-only", "--no-dangling")
    fx.restore()
    for pack in skipped:
        for ext in (".pack", ".idx", ".rev"):
            pack.with_suffix(ext).unlink(missing_ok=True)

    # The recipe: move the old packs' .keep files aside, then rescue.
    aside = tmp_path / "keep-aside"
    aside.mkdir()
    keep.rename(aside / keep.name)
    (rescued,) = fx.run_rescue()
    assert fx.x in _pack_contents(fx.prod, rescued.with_suffix(".idx"))
    fx.retire()
    assert ok(fx.prod, "fsck", "--connectivity-only", "--no-dangling")
    assert ok(fx.prod, "cat-file", "-e", fx.x)
