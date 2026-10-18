"""Expose the actual JavaScript consumer checks to the repository pytest lane."""
from pathlib import Path
import shutil
import subprocess


def test_decision_desk_contract_and_response_lifecycle():
    node = shutil.which("node")
    assert node, "Decision Desk verification requires the repository's Node runtime"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/test_biocatalyst_decision_desk.cjs")],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # Invoke directly: some Node environments summarize --test as one file.
    # Prove the discriminating cases actually ran, rather than just importing.
    assert "late old list response cannot resurrect" in result.stdout
    assert "context change immediately clears" in result.stdout
    assert "fixtures retain exact API response bytes" in result.stdout
