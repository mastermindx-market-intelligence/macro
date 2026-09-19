from __future__ import annotations

import os
import plistlib
import signal
import subprocess
import time
from pathlib import Path


FEED_SCRIPT = Path(__file__).resolve().parents[2] / "feed.sh"
FEED_PLIST = Path(__file__).resolve().parents[1] / "deploy" / "ai.marketdesk.feed.plist"


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def _base_layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    home = tmp_path / "home"
    dest = home / "mastermind-research"
    app = dest / "marketdesk_paper_extractor"
    (app / ".venv" / "bin").mkdir(parents=True)
    return home, dest, app


def _run_feed(home: Path, fake_bin: Path, **extra_env: str):
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        **extra_env,
    }
    return subprocess.run(
        ["/bin/bash", str(FEED_SCRIPT)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=3,
    )


def test_feed_uses_single_bounded_canonical_probe(tmp_path: Path) -> None:
    home, _, app = _base_layout(tmp_path)
    fake_bin = tmp_path / "bin"
    python_log = tmp_path / "python.log"
    sqlite_log = tmp_path / "sqlite.log"
    external_db = tmp_path / "storage" / "marketdesk.sqlite"

    _write_executable(
        app / ".venv" / "bin" / "python",
        """#!/bin/sh
printf '%s\n' "$*" > "$PYTHON_LOG"
printf '%s|%s|%s\n' "$CONFIGURED_DB" '2026-09-09T21:20:21+00:00' '0'
""",
    )
    _write_executable(
        fake_bin / "sqlite3",
        "#!/bin/sh\necho called > \"$SQLITE_LOG\"\nexit 99\n",
    )

    result = _run_feed(
        home,
        fake_bin,
        PYTHON_LOG=str(python_log),
        CONFIGURED_DB=str(external_db),
        SQLITE_LOG=str(sqlite_log),
    )

    assert result.returncode == 0, result.stderr
    args = python_log.read_text()
    assert "-m marketdesk_extractor.feed_probe" in args
    assert "--timeout 10" in args
    assert not sqlite_log.exists()


def test_feed_fails_closed_and_releases_lock_when_probe_fails(tmp_path: Path) -> None:
    home, dest, app = _base_layout(tmp_path)
    fake_bin = tmp_path / "bin"
    _write_executable(app / ".venv" / "bin" / "python", "#!/bin/sh\nexit 7\n")

    result = _run_feed(home, fake_bin)

    assert result.returncode == 0, result.stderr
    assert "vault-state probe failed" in (dest / "feed.log").read_text()
    assert not (dest / ".feed.lock").exists()


def test_feed_treats_an_empty_vault_as_nothing_new(tmp_path: Path) -> None:
    home, dest, app = _base_layout(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_db = tmp_path / "empty.sqlite"
    body = "#!/bin/sh\nprintf '%s|%s|%s\\n' \"$FAKE_DB\" '' '0'\n"
    _write_executable(app / ".venv" / "bin" / "python", body)

    result = _run_feed(home, fake_bin, FAKE_DB=str(fake_db))

    assert result.returncode == 0, result.stderr
    log = (dest / "feed.log").read_text()
    assert "nothing new" in log
    assert "malformed" not in log



def test_feed_releases_lock_when_launchd_terminates_it(tmp_path: Path) -> None:
    home, dest, app = _base_layout(tmp_path)
    fake_bin = tmp_path / "bin"
    _write_executable(
        app / ".venv" / "bin" / "python",
        "#!/bin/sh\ntrap 'exit 143' TERM INT HUP\nsleep 30\n",
    )
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
    }
    proc = subprocess.Popen(
        ["/bin/bash", str(FEED_SCRIPT)],
        env=env,
        start_new_session=True,
    )
    lock = dest / ".feed.lock"
    try:
        deadline = time.monotonic() + 2
        while not lock.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert lock.exists()
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=3)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=3)

    assert not lock.exists()


def test_feed_dispatches_to_canonical_macro_repository(tmp_path: Path) -> None:
    home, dest, app = _base_layout(tmp_path)
    fake_bin = tmp_path / "bin"
    gh_log = tmp_path / "gh.log"
    fake_db = tmp_path / "storage" / "marketdesk.sqlite"
    newest = "2026-09-14T18:40:00+00:00"

    _write_executable(
        app / ".venv" / "bin" / "python",
        "#!/bin/sh\nprintf '%s|%s|%s\\n' \"$FAKE_DB\" \"$FAKE_NEWEST\" '1'\n",
    )
    _write_executable(
        fake_bin / "gh",
        "#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$GH_LOG\"\n",
    )

    result = _run_feed(
        home,
        fake_bin,
        FAKE_DB=str(fake_db),
        FAKE_NEWEST=newest,
        GH_LOG=str(gh_log),
    )

    assert result.returncode == 0, result.stderr
    assert gh_log.read_text().strip() == (
        "workflow run research-ingest.yml "
        "-R mastermindx-market-intelligence/macro"
    )
    assert (dest / ".feed_vault_watermark").read_text().strip() == newest


def test_feed_launchd_template_uses_standard_qos() -> None:
    payload = plistlib.loads(FEED_PLIST.read_bytes())

    assert payload["Label"] == "ai.marketdesk.feed"
    assert payload["ProcessType"] == "Standard"
    assert payload["StartInterval"] == 900
    assert payload["ProgramArguments"] == [
        "/bin/bash",
        "__HOME__/mastermind-research/feed.sh",
    ]

