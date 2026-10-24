"""Execute the real account condition transport against adversarial owner responses.

No credentials, database, account rows or external requests are used here.
Database enforcement is owned and tested in the Terminal companion change.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "templates" / "forex_watch_client.js"
HARNESS = ROOT / "tests" / "js" / "forex_watch_client.test.cjs"


def test_account_condition_transport_contract():
    node = shutil.which("node")
    assert node, "Node is required for the Forex account transport contract"
    result = subprocess.run([node, "--test", str(HARNESS)], cwd=ROOT,
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert CLIENT.read_bytes() == (ROOT / "site" / "forex_watch_client.js").read_bytes()
