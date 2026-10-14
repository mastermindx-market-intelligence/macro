"""Exercise the updater's actual Caddy phase without services or network.

These are refusal/continuation tests. They do not prove live generation
comparison, response-loss recovery, or exclusion of an older updater inode.
"""
from pathlib import Path
import shlex
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("comparison", "reconciled", "diagnostic"),
    [
        ("equal", 0, ""),
        ("different", 0, "whole-config preservation/custody is not qualified"),
        ("different", 1, "whole-config preservation/custody is not qualified"),
        ("missing_saved", 0, "comparison failed (rc=2)"),
        ("missing_candidate", 0, "comparison failed (rc=2)"),
        ("saved_is_directory", 0, "comparison failed (rc=2)"),
        ("unexpected_error", 0, "comparison failed (rc=7)"),
    ],
)
def test_caddy_phase_defers_without_effect_and_continues(
    tmp_path: Path, comparison: str, reconciled: int, diagnostic: str
) -> None:
    source = (ROOT / "app/deploy/update.sh").read_text()
    start = source.index("# Caddyfile:")
    end = source.index("# BEGIN CONTROL_ROOM_ACTIVE_BUILDS_PUBLISH", start)
    block = source[start:end]
    app = tmp_path / "app"
    candidate = app / "app/deploy/Caddyfile"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("candidate config\n")
    saved = tmp_path / "saved Caddyfile"
    saved.write_text("candidate config\n" if comparison == "equal" else "saved config\n")
    if comparison == "missing_saved":
        saved.unlink()
    elif comparison == "missing_candidate":
        candidate.unlink()
    elif comparison == "saved_is_directory":
        saved.unlink()
        saved.mkdir()

    # Preserve live-only routes and TLS independently from both disk inputs.
    live = tmp_path / "live-config"
    live.write_bytes(b"live-only-route; live-only-TLS; different generation\n")
    originals = {
        path: path.read_bytes()
        for path in (saved, candidate, live)
        if path.is_file()
    }
    events = tmp_path / "effects"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("install", "caddy", "systemctl", "curl", "wget"):
        stub = bin_dir / name
        stub.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$EVENTS"\nexit 1\n'
        )
        stub.chmod(0o700)
    if comparison == "unexpected_error":
        compare = bin_dir / "cmp"
        compare.write_text("#!/bin/sh\nexit 7\n")
        compare.chmod(0o700)

    # Map the one production saved-file path into the contained fixture.
    block = block.replace("/etc/caddy/Caddyfile", shlex.quote(str(saved)))
    harness = (
        "set -euo pipefail\n"
        f"APP_DIR={shlex.quote(str(app))}\nRECONCILED={reconciled}\n"
        + block
        + '\nprintf "next-independent-phase;reconciled=%s\\n" "$RECONCILED"\n'
    )
    result = subprocess.run(
        ["/bin/bash", "-c", harness],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "EVENTS": str(events), "LC_ALL": "C"},
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"next-independent-phase;reconciled={reconciled}\n"
    assert not events.exists(), events.read_text() if events.exists() else ""
    for path, before in originals.items():
        assert path.read_bytes() == before
    if comparison == "missing_saved":
        assert not saved.exists()
    if comparison == "missing_candidate":
        assert not candidate.exists()
    if diagnostic:
        assert "Caddy phase deferred" in result.stderr
        assert diagnostic in result.stderr
        if comparison not in ("different", "equal"):
            assert "preservation/custody" not in result.stderr
    else:
        assert result.stderr == ""
