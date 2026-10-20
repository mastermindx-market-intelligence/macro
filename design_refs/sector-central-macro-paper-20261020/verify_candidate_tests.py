"""Record the exact selected-suite invocation and source binding for this candidate."""
from __future__ import annotations
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SUITES = [
    "tests/test_sector_central_paper.py",
    "tests/test_sector_central_gate.py",
    "tests/test_sector_central_data_is_sync.py",
    "tests/test_si_workspace_shell.py",
    "tests/test_sector_intelligence_page.py",
    "tests/test_sector_central_measured_panel.py",
    "tests/test_leadership_rotation_countercases.py",
    "tests/test_p_mp1_shell_nonus_byte_parity.py",
    "tests/test_us_stocks_w8g_table.py",
    "tests/test_stocktable_load_order.py",
    "tests/test_rlt_sector_stance_enrich.py",
    "tests/test_prophet_options_context.py",
    "tests/test_stock_personality_w4_surfaces.py",
]
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).splitlines()
def source_hashes():
    names = set(git("diff", "--name-only")) | set(git("ls-files", "--others", "--exclude-standard"))
    names |= set(SUITES)
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in sorted(names)
            if p.startswith(("templates/", "site/", "scripts/", "tests/", ".github/"))
            and (ROOT / p).is_file()}
before = source_hashes()
started = datetime.now(timezone.utc).isoformat()
argv = ["python3", "-m", "pytest", *SUITES, "-q", "--tb=short",
        "--basetemp=" + str(OUT / "pytest-tmp")]
prior = OUT / "macro-tests.txt"
if prior.exists() and not (OUT / "screener-combined-tests.txt").exists():
    (OUT / "screener-combined-tests.txt").write_bytes(prior.read_bytes())
with prior.open("w") as log:
    result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = source_hashes()
receipt = {
    "scope": "Thirteen named local suites on the unchanged candidate source; not repository-wide or hosted CI",
    "base_sha": git("rev-parse", "HEAD")[0], "started_utc": started,
    "completed_utc": datetime.now(timezone.utc).isoformat(),
    "argv": argv, "suite_count": len(SUITES), "exit_code": result.returncode,
    "result_line": prior.read_text().splitlines()[-1],
    "source_sha256": before, "source_unchanged_during_run": before == after,
    "source_set_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
    "log_sha256": hashlib.sha256(prior.read_bytes()).hexdigest(),
}
(OUT / "candidate-test-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k:v for k,v in receipt.items() if k != "source_sha256"}, indent=2))
assert before == after, "Candidate source changed during verification"
assert result.returncode == 0, "Selected candidate suites failed"
