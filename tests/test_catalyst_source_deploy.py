"""Regression guards for the Marketing X Catalyst SEC source writer deploy path (A3)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "app" / "deploy"
UPDATE_PATH = DEPLOY / "update.sh"
SERVICE_PATH = DEPLOY / "macro-catalyst-source-cycle.service"
TIMER_PATH = DEPLOY / "macro-catalyst-source-cycle.timer"
UNITS = ("macro-catalyst-source-cycle.service", "macro-catalyst-source-cycle.timer")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _catalyst_update_block() -> str:
    update = _text(UPDATE_PATH)
    start = update.index("# Marketing X Catalyst SEC source writer (A3).")
    end = update.index("macro-catalyst-source-cycle.timer could not be enabled", start)
    return update[start:end]


def _directives(path: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in _text(path).splitlines():
        if "=" in line and not line.lstrip().startswith(("#", ";", "[")):
            key, _, value = line.partition("=")
            found.setdefault(key.strip(), []).append(value.strip())
    return found


def test_update_script_still_parses():
    subprocess.run(["bash", "-n", str(UPDATE_PATH)], check=True)


def test_update_block_verifies_and_installs_only_the_two_named_units():
    block = _catalyst_update_block()
    assert "systemd-analyze verify" in block
    assert "unit_repair_inputs_safe" in block
    assert "refusing symlinked unit" in block
    installed = set(re.findall(r"macro-[a-z0-9-]+\.(?:service|timer)", block))
    assert installed == set(UNITS)
    assert 'install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"' in block


def test_update_block_restarts_nothing_but_its_own_timer():
    block = _catalyst_update_block()
    restarts = re.findall(r"systemctl\s+(?:restart|reload|start|try-restart)\s+(\S+)", block)
    assert restarts == ["macro-catalyst-source-cycle.timer"]
    assert "macro-api" not in re.sub(r"/etc/macro-api\.env|/opt/macro-api/", "", block)
    assert "CATALYST_PUBLIC_ENABLED" in block  # documented as the operator's switch, never set
    assert not re.search(r"CATALYST_[A-Z_]*ENABLED\s*=", block)


def test_update_enables_the_timer_after_the_block():
    update = _text(UPDATE_PATH)
    assert "systemctl enable --now macro-catalyst-source-cycle.timer" in update


def test_service_is_a_hardened_unprivileged_oneshot():
    service = _directives(SERVICE_PATH)
    assert service["Type"] == ["oneshot"]
    assert service["DynamicUser"][0] in {"yes", "true"}
    assert service["ProtectSystem"] == ["strict"]
    assert service["NoNewPrivileges"] == ["true"]
    assert service["PrivateTmp"] == ["true"]
    assert service["CapabilityBoundingSet"] == [""]
    assert service["EnvironmentFile"] == ["-/etc/macro-api.env"]
    assert service["ExecStart"] == [
        "/opt/macro-api/.venv/bin/python -m scripts.run_catalyst_source_cycle"
    ]
    assert "ReadWritePaths" not in service
    assert int(service["TimeoutStartSec"][0]) <= 290  # finishes inside one 5-min period


def test_timer_runs_every_five_minutes_and_targets_the_service():
    timer = _directives(TIMER_PATH)
    assert timer["OnUnitActiveSec"] == ["5min"]
    assert timer["Unit"] == ["macro-catalyst-source-cycle.service"]
