"""Review exact protected shared JS bytes without advancing a release carrier."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import tempfile

REPO = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True).strip())
OUT = Path(__file__).resolve().parent
REF = "7f1dbbd1bddb4480b68f79e257a26ab92fea5597"
PATHS = [
    "tests/js/market_memory_auth_return.test.cjs",
    "tests/js/market_memory_retained.test.cjs",
    "tests/js/market_memory_retained_state.test.cjs",
    "tests/fixtures/market_memory_retained_owner_wire.json",
    "templates/market_memory_intent.js",
    "templates/market_memory.js",
    "templates/market_memory_retained.js",
    "templates/onboard.js",
    "templates/theme.js",
]


def main():
    before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO)
    hashes, runs = {}, []
    # Only this short-lived, isolated proof fixture is removed on exit. No worktree
    # or tracked file is modified; all input bytes come from the named Git commit.
    with tempfile.TemporaryDirectory(prefix=".mmx-shared-proof-", dir=REPO) as d:
        fixture = Path(d)
        for path in PATHS:
            data = subprocess.check_output(["git", "show", f"{REF}:{path}"], cwd=REPO)
            hashes[path] = hashlib.sha256(data).hexdigest()
            target = fixture / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        commands = [
            ["node", "--test", "--test-reporter=tap", "tests/js/market_memory_auth_return.test.cjs",
             "tests/js/market_memory_retained.test.cjs"],
            ["node", "tests/js/market_memory_retained_state.test.cjs",
             "templates/market_memory_retained.js",
             "tests/fixtures/market_memory_retained_owner_wire.json"],
        ]
        for index, command in enumerate(commands):
            result = subprocess.run(command, cwd=fixture, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log_name = f"shared_dependency_checks_{index + 1}.txt"
            (OUT / log_name).write_text(result.stdout)
            match = re.search(r"# tests (\d+)", result.stdout) if index == 0 else re.search(
                r"RESULT passed=(\d+) failed=0", result.stdout)
            assert result.returncode == 0 and match, result.stdout
            runs.append({"command": command, "exit_code": result.returncode,
                         "passed": int(match.group(1)), "output": log_name})
        for path in PATHS:
            assert hashlib.sha256((fixture / path).read_bytes()).hexdigest() == hashes[path]
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO) == before
    receipt = {
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_ref": REF, "source_fix": "51c844305071 (protected PR 9300)",
        "input_sha256": hashes, "runs": runs,
        "passed": sum(r["passed"] for r in runs), "failed": 0,
        "input_bytes_unchanged": True, "release_carrier_unchanged": True,
        "fixture_network_calls": False, "browser_or_install_acceptance": False,
    }
    (OUT / "shared_dependency_checks.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "failed": 0, "source_ref": REF}))


if __name__ == "__main__":
    main()
