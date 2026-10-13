"""Durable Git history preservation for the Macro updater acquisition lane.

Source-repair proof for run mo-a-f04-updater-history-preservation-v1. The named
consumer is the F04 native gate ``accepts_revision(published_source,
installed_HEAD)``; that gate is UNCHANGED here and is never imported, edited or
reimplemented. What changed (history-preservation.patch) is only how the
protected branch is ACQUIRED:

* ``app/deploy/update.sh`` fetches the protected branch WITHOUT a depth limit;
* ``app/deploy/bootstrap_repo.sh`` converges an existing checkout without a
  depth limit and bootstraps fresh checkouts with ``--single-branch`` (no
  depth, no partial-clone/filter/promisor policy);
* ``app/deploy/setup.sh``'s header recipe and acquisition description match.

What this suite proves, using REAL local Git repositories over ``file://``
remotes (no network, no SSH transport, no cron, no updater service, no systemd,
no production path, no writes outside ``tmp_path``):

1. The acquisition stanza EXTRACTED FROM THE REVIEWED SCRIPTS keeps a published
   revision an ancestor of the installed HEAD across TWO successive updates
   plus one unchanged tick, keeps historical source bytes readable, and never
   trips the protected-closure fence for benign updates.
2. The depth-one defect is REAL and these tests are sensitive to it:
   TestDepthOneDefectReproduction re-severs a fixture graph with an explicit
   depth-one fetch and shows the native ancestry predicate refusing the pair,
   so the fixed expectations cannot pass vacuously. Reinstating depth-limited
   acquisition in the reviewed scripts turns the extraction-based tests red.
3. A fresh bootstrap lands CONNECTED selected-branch history (whole
   single-branch graph, deploy-key ``core.sshCommand`` persisted, no anonymous
   leg, no widening to all branches).
4. An EXISTING shallow checkout is left explicitly UNCONVERTED by the converge
   path — it stays shallow and its pre-existing truncation boundary stays cut —
   while future fetches stop truncating. This patch performs no conversion and
   supplies no F04 readiness by itself.
5. A failed fetch stays fail-closed BEFORE the reset (HEAD, work tree and
   reflog untouched), exactly as the strict-mode contract requires.
6. The native Git predicate inputs — object identity, ancestry, protected-main
   membership — admit the protected tip and refuse unrelated, missing, and
   graph-severed revisions.

The ``--unshallow`` inside TestFixtureOnlyConversionIsSeparateFromPrevention is
FIXTURE-ONLY evidence that a separate, explicit conversion composes with the
prevention repair. It is not part of the patch and is NOT a host recipe: this
suite never touches ``.git/shallow`` of anything but its own temporary
fixtures.

Run: python -m pytest tests/test_deploy_git_history.py -q
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UPDATE_SH = ROOT / "app" / "deploy" / "update.sh"
BOOTSTRAP_SH = ROOT / "app" / "deploy" / "bootstrap_repo.sh"
SETUP_SH = ROOT / "app" / "deploy" / "setup.sh"

UPDATE_TEXT = UPDATE_SH.read_text(encoding="utf-8")
BOOTSTRAP_TEXT = BOOTSTRAP_SH.read_text(encoding="utf-8")
SETUP_TEXT = SETUP_SH.read_text(encoding="utf-8")

SCRIPTS = (
    ("app/deploy/update.sh", UPDATE_TEXT),
    ("app/deploy/bootstrap_repo.sh", BOOTSTRAP_TEXT),
    ("app/deploy/setup.sh", SETUP_TEXT),
)

GENESIS_INDEX = "<html>macro fixture genesis</html>\n"
MISSING_REVISION = "f" * 40
PROTECTED_BRANCH = "main"


# ---------------------------------------------------------------------------
# Hermetic Git plumbing
# ---------------------------------------------------------------------------


def git_env(home: Path) -> dict:
    """Isolated Git environment: no host, user or system config can leak in."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_", "MACRO_"))
           and k not in {"BASH_ENV", "ENV", "CDPATH", "SHELLOPTS", "BASHOPTS",
                         "XDG_CONFIG_HOME"}}
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / "xdg"),
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_ALLOW_PROTOCOL="file:ssh",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_AUTHOR_NAME="F04 Fixture",
        GIT_AUTHOR_EMAIL="f04-fixture@example.invalid",
        GIT_COMMITTER_NAME="F04 Fixture",
        GIT_COMMITTER_EMAIL="f04-fixture@example.invalid",
    )
    for leak in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
        env.pop(leak, None)
    return env


def git(repo, *args, env, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        check=False,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"git -C {repo} {' '.join(args)} failed rc={proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc


class HistoryFixture:
    """origin (bare, protected main) + publisher work tree + install helpers.

    Commit topology on main: G (genesis) -> P (published) -> C1 -> C2 -> ...
    ``P`` plays the revision a production publish installs; every later commit
    plays a routine upstream advance that the updater ticks pull.
    """

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.env = git_env(self.home)
        self.origin = tmp_path / "origin.git"
        self.publisher = tmp_path / "publisher"
        self.deploy_key = tmp_path / "deploy-key"
        fd = os.open(self.deploy_key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, b"# fixture-only stand-in for a read-only deploy key\n")
        os.close(fd)

        init = git(tmp_path, "init", "-q", "-b", PROTECTED_BRANCH,
                   str(self.publisher), env=self.env, check=False)
        if init.returncode != 0:  # older git without `init -b`
            git(tmp_path, "init", "-q", str(self.publisher), env=self.env)
            git(self.publisher, "checkout", "-q", "-b", PROTECTED_BRANCH, env=self.env)
        self.write_publisher_file("site/index.html", GENESIS_INDEX)
        self.commit("genesis: fixture site skeleton")
        git(tmp_path, "init", "-q", "--bare", str(self.origin), env=self.env)
        git(self.origin, "symbolic-ref", "HEAD", "refs/heads/main", env=self.env)
        git(self.publisher, "remote", "add", "origin", self.origin_url, env=self.env)
        git(self.publisher, "push", "-q", "-u", "origin", PROTECTED_BRANCH, env=self.env)
        self.genesis = self.rev(PROTECTED_BRANCH)
        self.published = self.publish("generation P\n", "publish P")

    @property
    def origin_url(self) -> str:
        return self.root.joinpath("origin.git").as_uri()

    # -- publisher ----------------------------------------------------------

    def write_publisher_file(self, rel: str, content: str) -> None:
        target = self.publisher / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self, message: str) -> str:
        git(self.publisher, "add", "-A", env=self.env)
        git(self.publisher, "commit", "-q", "-m", message, env=self.env)
        return self.rev(PROTECTED_BRANCH)

    def rev(self, rev: str, repo=None) -> str:
        return git(repo or self.publisher, "rev-parse", rev,
                   env=self.env).stdout.strip()

    def publish(self, history_bytes: str, message: str) -> str:
        """Advance main by one commit to the historical source file and push."""
        self.write_publisher_file("site/history.txt", history_bytes)
        sha = self.commit(message)
        git(self.publisher, "push", "-q", "origin", PROTECTED_BRANCH, env=self.env)
        return sha

    def advance(self, label: str) -> str:
        """Push a new protected-main generation; returns the new tip sha."""
        sha = self.publish(f"generation {label}\n", f"advance main to {label}")
        return sha

    # -- installs -----------------------------------------------------------

    def shallow_install(self, name="installed") -> Path:
        """A legacy depth-one install parked at the published revision P."""
        target = self.root / name
        git(self.root, "clone", "-q", "--depth", "1", "--branch", PROTECTED_BRANCH,
            self.origin_url, str(target), env=self.env)
        return target

    def connected_install(self, name="installed") -> Path:
        target = self.root / name
        git(self.root, "clone", "-q", "--single-branch", "--branch", PROTECTED_BRANCH,
            self.origin_url, str(target), env=self.env)
        return target

    # -- queries ------------------------------------------------------------

    @staticmethod
    def is_shallow(repo) -> bool:
        return (Path(repo) / ".git" / "shallow").exists()

    def ancestor(self, repo, old: str, new: str) -> bool:
        """Native Git ancestry query (the input the F04 gate requires)."""
        return git(repo, "merge-base", "--is-ancestor", old, new,
                   env=self.env, check=False).returncode == 0

    def blob(self, repo, rev: str, path: str) -> str:
        return git(repo, "show", f"{rev}:{path}", env=self.env).stdout

    def object_exists(self, repo, rev: str) -> bool:
        return git(repo, "cat-file", "-e", f"{rev}^{{commit}}",
                   env=self.env, check=False).returncode == 0

    def reflog(self, repo) -> str:
        return git(repo, "reflog", "show", "HEAD", env=self.env).stdout


@pytest.fixture
def fixture(tmp_path: Path) -> HistoryFixture:
    return HistoryFixture(tmp_path)


# ---------------------------------------------------------------------------
# Reviewed-source extraction (keeps the proof sensitive to the real scripts)
# ---------------------------------------------------------------------------


def _matching_lines(text: str, pattern: str, label: str, source: str,
                    expected: int = 1) -> str:
    lines = [m.group(0) for m in re.finditer(pattern, text, re.M)]
    assert len(lines) == expected, (
        f"expected exactly {expected} {label} in {source}, found {len(lines)}: {lines}"
    )
    return lines[0]


def updater_acquisition_fragment(text: str = UPDATE_TEXT,
                                 source: str = "app/deploy/update.sh") -> str:
    """Extract the REAL acquisition stanza: fetch -> OLD/NEW -> guarded reset.

    Extracting from the reviewed source keeps the behavioral proof sensitive to
    it: reinstating a depth-limited fetch in update.sh changes what these tests
    actually execute, not just what they assert.
    """
    fetch = _matching_lines(
        text, r'^git -C "\$APP_DIR" fetch [^\n]*origin main$',
        "acquisition fetch line", source)
    old = _matching_lines(
        text, r'^OLD=\$\(git -C "\$APP_DIR" rev-parse HEAD\)$',
        "installed-HEAD capture", source)
    new = _matching_lines(
        text, r'^NEW=\$\(git -C "\$APP_DIR" rev-parse FETCH_HEAD\)$',
        "published-revision capture", source)
    changed = _matching_lines(
        text, r'^\tCHANGED=\$\(git -C "\$APP_DIR" diff --name-only "\$OLD" "\$NEW"\)$',
        "changed-path capture", source)
    reset = _matching_lines(
        text, r'^\tgit -C "\$APP_DIR" reset --hard -q FETCH_HEAD$',
        "protected reset", source)
    begin = text.index("# BEGIN W1B5_PRE_RESET_GUARD\n")
    end = text.index("# END W1B5_PRE_RESET_GUARD", begin) + len("# END W1B5_PRE_RESET_GUARD")
    guard = text[begin:end]
    return "\n".join([
        fetch,
        old,
        new,
        'CHANGED=""',
        'if [ "$OLD" != "$NEW" ]; then',
        changed,
        guard,
        reset,
        "fi",
    ])


def run_updater_acquisition(fixture: HistoryFixture, app_dir, text=UPDATE_TEXT):
    """Run the extracted acquisition stanza under the script's strict mode.

    Only the acquisition stanza is executed — never the whole updater, which
    owns service/fence/runtime effects no test may touch. The two protected-
    closure fences the stanza can reach are instrumented stubs that RECORD any
    call, so the tests can also prove benign updates never trip them.
    """
    fragment = updater_acquisition_fragment(text)
    events = Path(app_dir).parent / "fence-events.log"
    if events.exists():
        events.unlink()
    harness = "\n".join([
        "set -euo pipefail",
        f"APP_DIR={shlex.quote(str(app_dir))}",
        f"EVENTS={shlex.quote(str(events))}",
        f"OPTIONS_API_FENCE_MARKER={shlex.quote(str(fixture.root / 'fence-marker'))}",
        f"OPTIONS_RECIPROCAL_FENCE_MARKER={shlex.quote(str(fixture.root / 'reciprocal-marker'))}",
        "OPTIONS_RUNTIME_CLOSURE_REGEX='^f04/fixture/no-protected-path$'",
        "OPTIONS_RECIPROCAL_CLOSURE_REGEX='^f04/fixture/no-protected-path$'",
        "OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=0",
        "fence_event() { printf '%s\\n' \"$1\" >> \"$EVENTS\"; }",
        "disarm_options_timer() { fence_event disarm_options_timer; }",
        "stop_reciprocal_market_memory_writers() { fence_event stop_reciprocal_market_memory_writers; }",
        fragment,
        "",
    ])
    proc = subprocess.run(
        ["bash", "-c", harness],
        capture_output=True, text=True, env=fixture.env, timeout=300, check=False,
    )
    return proc, events


def bootstrap_converge_fragment(text: str = BOOTSTRAP_TEXT,
                                source: str = "app/deploy/bootstrap_repo.sh") -> str:
    """Extract the REAL converge stanza for an existing checkout."""
    log_fn = _matching_lines(
        text, r'^log\(\) \{ echo "\[bootstrap\] \$\*"; \}$',
        "log helper definition", source)
    ssh = _matching_lines(
        text, r'^MACRO_SSH_COMMAND="ssh -i \$\{MACRO_DEPLOY_KEY\}[^\n]*$',
        "deploy-key ssh command construction", source)
    set_url = _matching_lines(
        text, r'^\tgit -C "\$TARGET" remote set-url origin "\$MACRO_REPO_URL"$',
        "converge remote pinning", source)
    config = _matching_lines(
        text, r'^\tgit -C "\$TARGET" config core\.sshCommand "\$MACRO_SSH_COMMAND"$',
        "converge credential persistence", source, expected=2)
    log = _matching_lines(
        text, r'^\tlog "fetching \$MACRO_REPO_BRANCH[^\n]*$',
        "converge fetch log", source)
    fetch = _matching_lines(
        text, r'^\tgit -C "\$TARGET" fetch [^\n]*"\$MACRO_REPO_BRANCH"$',
        "converge fetch", source)
    reset = _matching_lines(
        text, r'^\tgit -C "\$TARGET" reset --hard FETCH_HEAD$',
        "converge reset", source)
    return "\n".join([log_fn, ssh, set_url, config, log, fetch, reset])


def run_bootstrap_converge(fixture: HistoryFixture, target, repo_url: str):
    fragment = bootstrap_converge_fragment()
    harness = "\n".join([
        "set -euo pipefail",
        f"TARGET={shlex.quote(str(target))}",
        f"MACRO_REPO_URL={shlex.quote(repo_url)}",
        f"MACRO_REPO_BRANCH={PROTECTED_BRANCH}",
        f"MACRO_DEPLOY_KEY={shlex.quote(str(fixture.deploy_key))}",
        fragment,
        "",
    ])
    return subprocess.run(
        ["bash", "-c", harness],
        capture_output=True, text=True, env=fixture.env, timeout=300, check=False,
    )


def run_bootstrap(fixture: HistoryFixture, target, repo_url: str, extra_env=None):
    """Run the real bootstrap_repo.sh end to end against a file:// origin."""
    env = dict(fixture.env)
    env["MACRO_REPO_URL"] = repo_url
    env["MACRO_REPO_BRANCH"] = PROTECTED_BRANCH
    env["MACRO_DEPLOY_KEY"] = str(fixture.deploy_key)
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(BOOTSTRAP_SH), str(target)],
        capture_output=True, text=True, env=env, timeout=300, check=False,
    )


def git_revision_inputs_hold(fixture: HistoryFixture, repo, published_source: str,
                     installed_head: str) -> bool:
    """Fixture-level stand-in for the F04 gate's REQUIRED native inputs.

    This is deliberately NOT the native gate and not a reimplementation of it:
    it runs only the unchanged native Git queries the documented gate is built
    on — both revisions resolve as commit objects, the published source is an
    ancestor of the installed HEAD, and the installed HEAD is a member of
    the protected branch as observed from this checkout. It exists to prove
    the acquisition repair keeps supplying exactly those inputs.
    """
    env = fixture.env
    if git(repo, "cat-file", "-e", f"{published_source}^{{commit}}",
           env=env, check=False).returncode != 0:
        return False
    if git(repo, "cat-file", "-e", f"{installed_head}^{{commit}}",
           env=env, check=False).returncode != 0:
        return False
    if git(repo, "merge-base", "--is-ancestor", published_source, installed_head,
           env=env, check=False).returncode != 0:
        return False
    protected = git(repo, "rev-parse", f"refs/remotes/origin/{PROTECTED_BRANCH}",
                    env=env).stdout.strip()
    if git(repo, "merge-base", "--is-ancestor", installed_head, protected,
           env=env, check=False).returncode != 0:
        return False
    return True


def fence_events(events: Path) -> list:
    if not events.exists():
        return []
    return [ln for ln in events.read_text(encoding="utf-8").splitlines() if ln]


# ---------------------------------------------------------------------------
# Reviewed-source shape guards
# ---------------------------------------------------------------------------


def test_updater_acquisition_fetch_has_no_depth_limit():
    line = _matching_lines(
        UPDATE_TEXT, r'^git -C "\$APP_DIR" fetch [^\n]*origin main$',
        "acquisition fetch line", "app/deploy/update.sh")
    assert "--depth" not in line, (
        "the updater acquisition must not truncate protected-branch history"
    )
    assert " -q " in line, "quiet fail-closed fetch preserved"


def test_bootstrap_converge_fetch_has_no_depth_limit():
    line = _matching_lines(
        BOOTSTRAP_TEXT, r'^\tgit -C "\$TARGET" fetch [^\n]*"\$MACRO_REPO_BRANCH"$',
        "converge fetch line", "app/deploy/bootstrap_repo.sh")
    assert "--depth" not in line


def test_bootstrap_fresh_clone_is_connected_single_branch_without_partial_clone():
    line = _matching_lines(
        BOOTSTRAP_TEXT, r'^\t\tclone [^\n]*"\$MACRO_REPO_URL" "\$TARGET"$',
        "fresh clone line", "app/deploy/bootstrap_repo.sh")
    assert "--single-branch" in line, "fresh bootstrap must stay on one branch"
    assert "--branch \"$MACRO_REPO_BRANCH\"" in line
    assert "--depth" not in line
    assert "--filter" not in line and "promisor" not in line, (
        "no partial-clone/filter/promisor policy may be introduced"
    )


def test_setup_sh_header_recipe_and_description_match_acquisition():
    assert (
        "clone --single-branch --branch main git@github.com:"
        "mastermindx-market-intelligence/macro.git /opt/macro" in SETUP_TEXT
    ), "setup.sh header recipe must install connected single-branch history"
    assert "depth-1," not in SETUP_TEXT
    assert "accepts_revision" in SETUP_TEXT


def test_no_command_line_requests_depth_truncation_anywhere():
    for rel, text in SCRIPTS:
        offenders = [
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "--depth" in line
        ]
        assert not offenders, f"{rel} still carries depth-limited acquisition: {offenders}"


def test_updater_keeps_lock_and_fail_closed_reset_shape():
    """Preservation: the depth change must not disturb the updater's fences."""
    assert "set -euo pipefail" in UPDATE_TEXT
    assert 'exec 9>/var/lock/macro-update.lock' in UPDATE_TEXT
    assert 'flock -n 9 || exit 0' in UPDATE_TEXT
    assert UPDATE_TEXT.count('git -C "$APP_DIR" reset --hard -q FETCH_HEAD') == 1


def test_bootstrap_keeps_deploy_key_plumbing_and_no_anonymous_fallback():
    assert "set -euo pipefail" in BOOTSTRAP_TEXT
    assert "IdentitiesOnly=yes" in BOOTSTRAP_TEXT
    assert 'https://github.com' not in BOOTSTRAP_TEXT
    assert 'case "$MACRO_REPO_URL" in' in BOOTSTRAP_TEXT
    assert "git@*|ssh://*" in BOOTSTRAP_TEXT
    assert '[ ! -f "$MACRO_DEPLOY_KEY" ]' in BOOTSTRAP_TEXT
    assert "exit 1" in BOOTSTRAP_TEXT
    assert BOOTSTRAP_TEXT.count(
        'git -C "$TARGET" config core.sshCommand "$MACRO_SSH_COMMAND"'
    ) == 2


# ---------------------------------------------------------------------------
# The defect itself: depth-one acquisition severs the installed HEAD
# ---------------------------------------------------------------------------


class TestDepthOneDefectReproduction:
    """Fixture-only reproduction of the pre-repair production failure.

    Nothing here executes reviewed code: the depth-one fetch below is the
    HISTORICAL stanza, replayed against local fixtures so the fixed
    expectations elsewhere in this suite are demonstrably non-vacuous.
    """

    def test_depth_one_fetch_severs_installed_head_despite_present_object(
        self, fixture: HistoryFixture
    ):
        installed = fixture.shallow_install()
        assert fixture.is_shallow(installed)
        c1 = fixture.advance("C1")
        c2 = fixture.advance("C2")

        # The historical (pre-repair) acquisition: depth-one fetch + reset.
        git(installed, "fetch", "--depth", "1", "-q", "origin", PROTECTED_BRANCH,
            env=fixture.env)
        git(installed, "reset", "--hard", "-q", "FETCH_HEAD", env=fixture.env)

        assert fixture.rev("HEAD", repo=installed) == c2
        # The previously published revision survives as an OBJECT ...
        assert fixture.object_exists(installed, fixture.published), (
            "P must exist as a commit object for this reproduction to be honest"
        )
        # ... but is no longer part of HEAD's graph: the native ancestry query
        # fails, exactly as merge-base a139 -> 82c failed in production.
        assert not fixture.ancestor(installed, fixture.published, c2), (
            "depth-one acquisition must sever P from the new tip for this "
            "reproduction to be valid"
        )
        assert not fixture.ancestor(installed, c1, c2)
        assert fixture.genesis and not fixture.object_exists(installed, fixture.genesis)

    def test_git_inputs_refuse_severed_pair(self, fixture: HistoryFixture):
        installed = fixture.shallow_install()
        fixture.advance("C1")
        c2 = fixture.advance("C2")
        git(installed, "fetch", "--depth", "1", "-q", "origin", PROTECTED_BRANCH,
            env=fixture.env)
        git(installed, "reset", "--hard", "-q", "FETCH_HEAD", env=fixture.env)
        # Published P is present but no longer an ancestor of installed C2.
        # This checks native Git inputs, not the full application gate.
        assert not git_revision_inputs_hold(fixture, installed, fixture.published, c2)


# ---------------------------------------------------------------------------
# Revised acquisition: two updates + unchanged tick keep history connected
# ---------------------------------------------------------------------------


def test_two_updates_keep_published_revision_ancestor_and_history_readable(
    fixture: HistoryFixture,
):
    """The reviewed acquisition fragment, executed for real, twice, then idle."""
    installed = fixture.shallow_install()
    assert fixture.is_shallow(installed)

    c1 = fixture.advance("C1")
    proc, events = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr
    assert fixture.rev("HEAD", repo=installed) == c1
    assert fixture.ancestor(installed, fixture.published, c1), (
        "after update one the published revision must remain an ancestor"
    )
    assert fixture.blob(installed, c1, "site/history.txt") == "generation C1\n"
    assert fixture.blob(installed, fixture.published, "site/history.txt") == "generation P\n"
    assert not fence_events(events), "benign updates must not trip the closure fences"

    c2 = fixture.advance("C2")
    proc, events = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr
    assert fixture.rev("HEAD", repo=installed) == c2
    assert fixture.ancestor(installed, fixture.published, c2)
    assert fixture.ancestor(installed, c1, c2)
    for rev, expected in (
        (fixture.published, "generation P\n"),
        (c1, "generation C1\n"),
        (c2, "generation C2\n"),
    ):
        assert fixture.blob(installed, rev, "site/history.txt") == expected, (
            f"historical source bytes at {rev[:12]} must stay readable"
        )
    assert git(installed, "rev-parse", "refs/remotes/origin/main",
               env=fixture.env).stdout.strip() == c2
    assert not fence_events(events)

    # Still shallow, still cut below the pre-existing boundary: prevention is
    # not conversion.
    assert fixture.is_shallow(installed)
    assert not fixture.object_exists(installed, fixture.genesis)


def test_unchanged_tick_is_a_no_op_and_leaves_the_work_tree_alone(
    fixture: HistoryFixture,
):
    installed = fixture.shallow_install()
    fixture.advance("C1")
    proc, _ = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr

    # An operator scratch edit that no commit carries: a reset --hard would
    # wipe it, an idle tick must not.
    scratch = installed / "site" / "index.html"
    scratch.write_text(scratch.read_text(encoding="utf-8") + "operator scratch\n",
                       encoding="utf-8")
    head_before = fixture.rev("HEAD", repo=installed)
    reflog_before = fixture.reflog(installed)

    proc, events = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr
    assert fixture.rev("HEAD", repo=installed) == head_before
    assert fixture.reflog(installed) == reflog_before, "no reset may run on an idle tick"
    assert "operator scratch" in scratch.read_text(encoding="utf-8")
    assert not fence_events(events)


def test_updater_fetch_failure_stays_fail_closed_before_reset(
    fixture: HistoryFixture,
):
    installed = fixture.shallow_install()
    c1 = fixture.advance("C1")
    proc, _ = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr
    head_before = fixture.rev("HEAD", repo=installed)
    reflog_before = fixture.reflog(installed)

    # Break acquisition exactly where the reviewed script reads it from: the
    # protected remote. Strict mode must abort BEFORE the reset.
    scratch = installed / "site" / "index.html"
    scratch.write_text(scratch.read_text(encoding="utf-8") + "operator scratch\n",
                       encoding="utf-8")
    git(installed, "remote", "set-url", "origin",
        str(fixture.root / "missing-origin.git"), env=fixture.env)

    proc, events = run_updater_acquisition(fixture, installed)
    assert proc.returncode != 0, "a failed fetch must fail the run"
    assert fixture.rev("HEAD", repo=installed) == head_before
    assert fixture.reflog(installed) == reflog_before, "reset must not run after fetch failure"
    assert "operator scratch" in scratch.read_text(encoding="utf-8")
    assert not fence_events(events)


# ---------------------------------------------------------------------------
# Bootstrap: fresh clone connects history; converge leaves shallow as found
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("remote_default", [PROTECTED_BRANCH, "unselected", "unborn"])
def test_bootstrap_fresh_clone_acquires_connected_selected_branch_history(
    fixture: HistoryFixture, remote_default: str,
):
    fixture.advance("C1")
    fixture.advance("C2")
    expected_tip = fixture.rev(PROTECTED_BRANCH)
    expected_count = int(
        git(fixture.publisher, "rev-list", "--count", PROTECTED_BRANCH,
            env=fixture.env).stdout.strip()
    )

    # A real second remote branch makes the single-branch check discriminating.
    git(fixture.publisher, "branch", "unselected", fixture.genesis, env=fixture.env)
    git(fixture.publisher, "push", "-q", "origin", "unselected", env=fixture.env)
    # --branch must select main even if the remote's default names another
    # branch or an unborn ref. The remote-tracking HEAD alias is advisory;
    # Git versions need not create it for an explicitly selected branch.
    git(fixture.origin, "symbolic-ref", "HEAD", f"refs/heads/{remote_default}",
        env=fixture.env)
    target = fixture.root / "fresh"
    proc = run_bootstrap(fixture, target, fixture.origin_url)
    assert proc.returncode == 0, proc.stderr
    assert not fixture.is_shallow(target), "fresh bootstrap must not be shallow"
    assert fixture.rev("HEAD", repo=target) == expected_tip
    assert int(git(target, "rev-list", "--count", "HEAD",
                   env=fixture.env).stdout.strip()) == expected_count
    assert fixture.ancestor(target, fixture.genesis, "HEAD"), (
        "the whole selected-branch history must be connected from the tip"
    )
    # Selected branch only — the clone must not broaden to all branches.
    assert git(target, "config", "--get", "remote.origin.fetch",
               env=fixture.env).stdout.strip() == (
        f"+refs/heads/{PROTECTED_BRANCH}:refs/remotes/origin/{PROTECTED_BRANCH}"
    )
    refs = git(target, "for-each-ref", "refs/remotes/origin",
               "--format=%(refname)", env=fixture.env).stdout.split()
    selected_ref = f"refs/remotes/origin/{PROTECTED_BRANCH}"
    assert set(refs) - {"refs/remotes/origin/HEAD"} == {selected_ref}
    assert fixture.rev(selected_ref, repo=target) == expected_tip
    if "refs/remotes/origin/HEAD" in refs:
        assert git(target, "symbolic-ref", "refs/remotes/origin/HEAD",
                   env=fixture.env).stdout.strip() == selected_ref
    # Deploy-key plumbing persisted into the new checkout, exactly as before.
    ssh_command = git(target, "config", "--get", "core.sshCommand",
                      env=fixture.env).stdout.strip()
    assert "IdentitiesOnly=yes" in ssh_command
    assert f"-i {fixture.deploy_key}" in ssh_command
    # bootstrap_repo.sh's own postcondition still runs.
    assert (target / "site" / "index.html").read_text(encoding="utf-8") == GENESIS_INDEX


def test_bootstrap_converge_keeps_existing_shallow_unconverted_but_stops_truncation(
    fixture: HistoryFixture,
):
    installed = fixture.shallow_install()
    assert fixture.is_shallow(installed)
    c1 = fixture.advance("C1")
    c2 = fixture.advance("C2")

    proc = run_bootstrap_converge(fixture, installed, fixture.origin_url)
    assert proc.returncode == 0, proc.stderr
    assert fixture.rev("HEAD", repo=installed) == c2
    # Future truncation stopped: the new tip connects back to the old one.
    assert fixture.ancestor(installed, fixture.published, c2)
    assert fixture.ancestor(installed, c1, c2)
    # ...but an existing shallow checkout is explicitly NOT converted: no
    # unshallow, no deepen, no graft, no shallow-file edit.
    assert fixture.is_shallow(installed), (
        "converge must leave an existing shallow boundary exactly as found"
    )
    assert not fixture.object_exists(installed, fixture.genesis), (
        "the pre-existing truncation boundary must stay cut; conversion is a "
        "separate repair this patch does not perform"
    )
    assert int(git(installed, "rev-list", "--count", "HEAD",
                   env=fixture.env).stdout.strip()) == 3


def test_bootstrap_uses_deploy_key_without_anonymous_fallback(
    fixture: HistoryFixture, tmp_path: Path
):
    """Hermetic auth proof: git@ remotes go out through the deploy-key ssh
    command only. A stub `ssh` records every invocation and fails, so the run
    is guaranteed offline; no anonymous HTTPS leg may exist to fall back to."""
    stub_dir = tmp_path / "stub-bin"
    stub_dir.mkdir()
    stub = stub_dir / "ssh"
    stub.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" >> "$SSH_ARGS_LOG"\nexit 127\n',
        encoding="utf-8",
    )
    os.chmod(stub, 0o755)
    ssh_log = tmp_path / "ssh-invocations.log"

    target = tmp_path / "fresh-auth"
    proc = run_bootstrap(
        fixture, target,
        "git@github.com:mastermindx-market-intelligence/macro.git",
        extra_env={
            "PATH": f"{stub_dir}:{os.environ.get('PATH', '')}",
            "SSH_ARGS_LOG": str(ssh_log),
        },
    )
    assert proc.returncode != 0, "a refused transport must fail the bootstrap"
    assert not (target / ".git").exists(), "no checkout may appear without auth"
    invocations = ssh_log.read_text(encoding="utf-8")
    assert str(fixture.deploy_key) in invocations, (
        "the exact deploy key must be handed to ssh"
    )
    assert "-i" in invocations.split()
    assert "IdentitiesOnly=yes" in invocations, (
        "IdentitiesOnly deploy-key authentication must be preserved"
    )
    assert "https://" not in proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# Unchanged native predicate inputs after the repair
# ---------------------------------------------------------------------------


def test_git_inputs_accept_published_ancestor_and_refuse_future_unrelated_missing(
    fixture: HistoryFixture,
):
    installed = fixture.connected_install()
    fixture.advance("C1")
    c2 = fixture.advance("C2")
    published_source = fixture.published
    # Apply the real acquisition stanza so installed HEAD advances to C2.
    proc, _ = run_updater_acquisition(fixture, installed)
    assert proc.returncode == 0, proc.stderr
    installed_head = fixture.rev("HEAD", repo=installed)
    assert installed_head == c2

    # Published source P remains valid under installed C2: object identity,
    # source-to-installed ancestry and protected-main membership all hold.
    assert git_revision_inputs_hold(fixture, installed, published_source, installed_head)
    # A protected source newer than installed HEAD must be refused.
    future = fixture.advance("future")
    git(installed, "fetch", "-q", "origin", PROTECTED_BRANCH, env=fixture.env)
    assert not git_revision_inputs_hold(fixture, installed, future, installed_head)

    # An UNRELATED revision: present in the object store, genuinely committed,
    # but not a member of the protected branch.
    git(fixture.publisher, "checkout", "-q", "-b", "side", fixture.published,
        env=fixture.env)
    fixture.write_publisher_file("site/unrelated.txt", "unrelated work\n")
    unrelated = fixture.commit("unrelated side-branch work")
    git(fixture.publisher, "push", "-q", "origin", "side", env=fixture.env)
    git(fixture.publisher, "checkout", "-q", PROTECTED_BRANCH, env=fixture.env)
    git(installed, "fetch", "-q", "origin", "side", env=fixture.env)
    unrelated_observed = fixture.rev("FETCH_HEAD", repo=installed)
    assert fixture.object_exists(installed, unrelated_observed), (
        "the unrelated revision must be locally present so the refusal is a "
        "predicate refusal, not a missing object"
    )
    assert not git_revision_inputs_hold(fixture, installed, unrelated_observed, installed_head)
    # A side-branch installed revision descends from P but is not protected.
    assert fixture.ancestor(installed, published_source, unrelated_observed)
    assert not git_revision_inputs_hold(fixture, installed, published_source, unrelated_observed)

    # A MISSING revision: a well-formed but nonexistent object id.
    assert not fixture.object_exists(installed, MISSING_REVISION)
    assert not git_revision_inputs_hold(fixture, installed, MISSING_REVISION, installed_head)


# ---------------------------------------------------------------------------
# Fixture-only conversion composes with prevention (NOT a host recipe)
# ---------------------------------------------------------------------------


class TestFixtureOnlyConversionIsSeparateFromPrevention:
    """A separate, explicit conversion, then two repaired updates.

    FIXTURE-ONLY: the ``--unshallow`` below runs against this test's own
    temporary clone to show that the separately-owned recovery lane (explicit
    conversion) and this patch (prevention) compose. The patch itself never
    converts, deepens, grafts or edits .git/shallow, and nothing here is a
    recipe for the host checkout.
    """

    def test_conversion_then_two_updates_stay_connected(self, fixture: HistoryFixture):
        installed = fixture.shallow_install()
        fixture.advance("C1")
        fixture.advance("C2")

        # Explicit, fixture-only conversion of the old boundary.
        git(installed, "fetch", "--unshallow", "-q", "origin", PROTECTED_BRANCH,
            env=fixture.env)
        assert not fixture.is_shallow(installed)
        assert fixture.object_exists(installed, fixture.genesis)
        assert fixture.ancestor(installed, fixture.genesis, "HEAD")

        # Prevention takes over: two successive reviewed updates.
        c3 = fixture.advance("C3")
        proc, events = run_updater_acquisition(fixture, installed)
        assert proc.returncode == 0, proc.stderr
        assert fixture.rev("HEAD", repo=installed) == c3
        assert fixture.ancestor(installed, fixture.published, c3)

        c4 = fixture.advance("C4")
        proc, events = run_updater_acquisition(fixture, installed)
        assert proc.returncode == 0, proc.stderr
        assert fixture.rev("HEAD", repo=installed) == c4
        for rev, expected in (
            (fixture.published, "generation P\n"),
            (c3, "generation C3\n"),
            (c4, "generation C4\n"),
        ):
            assert fixture.blob(installed, rev, "site/history.txt") == expected
        assert not fixture.is_shallow(installed)
        assert not fence_events(events)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
