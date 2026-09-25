"""Regression tests for the production deploy disk headroom gate."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "app" / "deploy" / "disk-headroom.sh"
UPDATE = ROOT / "app" / "deploy" / "update.sh"


def _run_guard(tmp_path: Path, *, free_kib: int, minimum_kib: int):
    app = tmp_path / "macro"
    app.mkdir()
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    (fakebin / "df").write_text(
        "#!/bin/sh\nprintf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n'\n"
        f"printf '/dev/test 999999 1 {free_kib} 1%% /\\n'\n"
    )
    (fakebin / "git").write_text(
        "#!/bin/sh\nprintf 'count: 0\\npacks: 209\\nsize-pack: 31580\\n'\n"
    )
    for path in (fakebin / "df", fakebin / "git"):
        path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fakebin}:{env['PATH']}"
    env["MACRO_APP_DIR"] = str(app)
    env["MACRO_UPDATE_MIN_FREE_KIB"] = str(minimum_kib)
    return subprocess.run([str(GUARD)], text=True, capture_output=True, env=env)


def test_low_disk_refuses_repository_mutation(tmp_path: Path) -> None:
    run = _run_guard(tmp_path, free_kib=1024, minimum_kib=2048)
    assert run.returncode == 75
    assert "LOW_DISK_HOLD" in run.stderr
    assert "git_packs=209" in run.stderr


def test_sufficient_headroom_passes_silently(tmp_path: Path) -> None:
    run = _run_guard(tmp_path, free_kib=4096, minimum_kib=2048)
    assert run.returncode == 0
    assert run.stdout == ""
    assert run.stderr == ""


def test_guard_runs_before_fetch_and_runtime_mutation() -> None:
    text = UPDATE.read_text()
    gate = text.index('"$APP_DIR/app/deploy/disk-headroom.sh"')
    assert gate < text.index('git -C "$APP_DIR" fetch --depth 1 -q origin main')
    assert gate < text.index('rm -f "$OPTIONS_API_FENCE_MARKER"')
