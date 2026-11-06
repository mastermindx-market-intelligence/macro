"""Compare the expanded compatibility suites with the exact untouched source base."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
assert base == "3667000ca153496d8ff69e8864b159ac1e7b9de0"
paths = [
    "tests/test_p_mp1_shell_nonus_byte_parity.py",
    "tests/test_us_stocks_w8g_table.py",
    "tests/test_stocktable_load_order.py",
    "templates/hk.html.j2", "templates/china.html.j2",
    "templates/canada.html.j2", "templates/intl.html.j2",
    "templates/dashboard.html.j2", "templates/stocktable.js",
    "templates/_prophet_card.html.j2", "templates/_prophet_setup_detail.html.j2",
    "site/us_stocks.html", "site/hk_stocks.html",
    "site/china_stocks.html", "site/canada_stocks.html",
    "site/factordata/us_standouts.json",
]
hashes = {}
with tempfile.TemporaryDirectory(prefix="compat-baseline-", dir=OUT) as folder:
    baseline_root = Path(folder)
    for name in paths:
        content = subprocess.check_output(["git", "show", base + ":" + name], cwd=ROOT)
        path = baseline_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    command = [sys.executable, "-m", "pytest"] + paths[:3] + [
        "-q", "--tb=short", "--basetemp", str(baseline_root / "pytest-tmp")]
    result = subprocess.run(command, cwd=baseline_root, capture_output=True, text=True)
log = result.stdout + result.stderr
(OUT / "compatibility-baseline-tests.txt").write_text(log)
failures = re.findall(r"^FAILED (.+)$", log, re.M)
candidate_log = (OUT / "compatibility-initial-tests.txt").read_text()
candidate_failures = re.findall(r"^FAILED (.+)$", candidate_log, re.M)
receipt = {
    "base_sha": base, "baseline_exit_code": result.returncode,
    "baseline_summary": [line for line in log.splitlines() if re.search(r"\d+ failed, \d+ passed", line)],
    "baseline_failures": failures, "candidate_failures": candidate_failures,
    "identical_failure_nodeids": failures == candidate_failures,
    "base_source_sha256": hashes,
    "candidate_test_source_replaced": False,
}
(OUT / "compatibility-baseline-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
assert result.returncode == 1 and len(failures) == 9, log[-6000:]
assert failures == candidate_failures, receipt
print(json.dumps({key: receipt[key] for key in (
    "base_sha", "baseline_exit_code", "baseline_summary", "identical_failure_nodeids")}, indent=2))
