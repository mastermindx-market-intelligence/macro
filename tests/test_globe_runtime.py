"""Run the deterministic globe lifecycle tests with the repository's Node runtime."""
from pathlib import Path
import subprocess


def test_globe_runtime_behaviors():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["node", "--test", "tests/js/globe_deck_runtime.test.cjs"],
        cwd=root, check=True, capture_output=True, text=True,
    )
