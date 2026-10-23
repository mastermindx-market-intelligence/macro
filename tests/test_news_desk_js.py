"""Run the news query and protected company protocol contracts in CI."""
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("suite", [
    "test_news_desk_client.cjs",
    "test_news_company_protocol.cjs",
])
def test_news_client_contract(suite: str) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for news client protocol verification"
    result = subprocess.run(
        [node, "--test", str(ROOT / "tests" / suite)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
