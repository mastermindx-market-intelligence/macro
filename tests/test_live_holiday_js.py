"""Behavioral holiday/client contract: run the real browser asset in Node."""
from pathlib import Path
import shutil
import subprocess


def test_live_holiday_client_behavior():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    assert node, "Node is required for the live holiday client behavior contract"
    result = subprocess.run(
        [node, "--test", str(root / "tests/live_holiday.test.mjs")],
        cwd=root, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
