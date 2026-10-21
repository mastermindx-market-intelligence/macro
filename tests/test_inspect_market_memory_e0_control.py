"""The real administrator entry must refuse development invocation safely."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inspect_market_memory_e0_control.py"


@pytest.mark.parametrize("arguments", [
    ["--study-id", "inert-not-admitted"],
    ["--root", "/private/do-not-disclose", "--allow", "yes"],
])
def test_uninstalled_process_refuses_without_echo_or_product_import(arguments):
    completed = subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments],
                               capture_output=True, timeout=5)
    assert completed.returncode == 78
    assert completed.stderr == b""
    assert json.loads(completed.stdout) == {
        "schema": "research_factory.market_memory_e0_control_inspection_failure.v1",
        "failure": "installed_administrator_entry_required", "operational_admission": False,
    }
    assert b"/private" not in completed.stdout


def test_module_mode_is_not_an_installed_administrator_entry():
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.inspect_market_memory_e0_control"],
        cwd=SCRIPT.parents[1], capture_output=True, timeout=5)
    assert completed.returncode == 78 and completed.stderr == b""
    assert json.loads(completed.stdout)["failure"] == "installed_administrator_entry_required"
