"""Launchd lane for the options payoff lab. Sibling of the skew lane.

The git stub answers `rev-parse` with a literal short sha. It must not call
`git` again: the stub directory is first on PATH, and a nested git call
recurses until the process table fills. Probes of tracked files use HEAD,
never origin/main, because a depth-1 CI checkout has no remote-tracking
branch.
"""
from __future__ import annotations

import importlib.util
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PLIST = ROOT / "ops" / "launchd" / "com.macro.payofflab.plist"
RUNNER = ROOT / "ops" / "launchd" / "run_options_payoff_lab.sh"
PUBLISH = ROOT / "scripts" / "publish_r2.py"
FETCH = ROOT / "scripts" / "fetch_r2.py"
SESSION = "2026-09-18"

FAKE_FETCH_OK = '''import sys
sys.exit(0)
'''
FAKE_FETCH_ZERO = '''import sys
sys.stderr.write("options_payoff_lab: ZERO objects under options_payoff_lab/ on R2\\n")
sys.exit(1)
'''
FAKE_PUBLISH_OK = '''import sys
sys.exit(0)
'''
FAKE_PUBLISH_FAIL = '''import sys
sys.exit(1)
'''
FAKE_ACCRUE_OK = '''import json, os
from pathlib import Path
repo = Path(os.environ["PAYOFF_OPS_ROOT"])
out = repo / "data" / "options_payoff_lab"
(out / "history").mkdir(parents=True, exist_ok=True)
payload = {
    "schema": "mastermind.options_payoff_lab/v1",
    "asof": "2026-09-18",
    "source": "thetadata",
    "roots": [],
    "counts": {"roots_priced": 0, "structures_built": 0, "structures_null": 0},
    "states": [],
}
text = json.dumps(payload)
(out / "latest.json").write_text(text)
(out / "history" / "2026-09-18.json").write_text(text)
'''
FAKE_ACCRUE_FAIL = '''import sys
sys.exit(7)
'''


def _load_plist() -> dict:
    with PLIST.open("rb") as handle:
        return plistlib.load(handle)


def test_plist_parses_with_python_plistlib():
    assert isinstance(_load_plist(), dict)


def test_plist_pins_label_program_and_schedule():
    plist = _load_plist()
    assert plist["Label"] == "com.macro.payofflab"
    assert plist["WorkingDirectory"] == "/Users/chriswong/skew-ops-wt"
    assert plist["ProgramArguments"] == [
        "/Users/chriswong/skew-ops-wt/ops/launchd/run_with_env.sh",
        "/Users/chriswong/skew-ops-wt/.env",
        "/Users/chriswong/skew-ops-wt/ops/launchd/run_options_payoff_lab.sh",
    ]
    intervals = plist["StartCalendarInterval"]
    assert [item["Weekday"] for item in intervals] == [1, 2, 3, 4, 5]
    for item in intervals:
        assert item["Hour"] == 8
        assert item["Minute"] == 0
    assert plist["KeepAlive"] is False
    assert plist["ThrottleInterval"] == 60
    assert plist.get("LimitLoadToSessionType") == "Aqua"


def test_plist_log_paths_live_outside_the_repo():
    plist = _load_plist()
    out_path = plist["StandardOutPath"]
    err_path = plist["StandardErrorPath"]
    assert out_path == "/Users/chriswong/skew-ops-state/logs/payofflab.stdout.log"
    assert err_path == "/Users/chriswong/skew-ops-state/logs/payofflab.stderr.log"
    repo = "/Users/chriswong/skew-ops-wt"
    for path in (out_path, err_path):
        assert not path.startswith(repo + "/")
        assert path != repo
    env = plist["EnvironmentVariables"]
    assert env["THETADATA_STORE"].startswith("/Users/")
    for key, value in env.items():
        for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"):
            assert marker not in key.upper()
            assert marker not in str(value).upper()


def test_run_with_env_wrapper_is_tracked_at_head():
    out = subprocess.run(
        ["git", "ls-tree", "HEAD", "ops/launchd/run_with_env.sh"],
        capture_output=True, text=True, check=True, cwd=str(ROOT),
    ).stdout.strip()
    assert out
    assert "100755" in out


def test_runner_script_passes_sh_n():
    rc = subprocess.run(
        ["/bin/sh", "-n", str(RUNNER)],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 0, rc.stderr


def test_runner_does_not_push_to_git():
    src = RUNNER.read_text(encoding="utf-8")
    assert "git push" not in src
    assert "git commit" not in src
    assert "sleep 300" in src
    assert "run_skew_accrual.sh" in src
    assert "PAYOFF_DRY_RUN" in src
    assert "ZERO objects" in src


def _write_store(path: Path) -> None:
    greeks = path / "greeks" / "SPY"
    greeks.mkdir(parents=True)
    pd.DataFrame({"date": [SESSION]}).to_parquet(greeks / "2026.parquet")


def _build_fake_repo(tmp_path: Path, *, accrue: str, fetch: str, publish: str) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    (repo / ".git").mkdir(parents=True)
    scripts.mkdir(parents=True)
    (repo / "data" / "options_payoff_lab").mkdir(parents=True)
    (scripts / "fetch_r2.py").write_text(fetch, encoding="utf-8")
    (scripts / "publish_r2.py").write_text(publish, encoding="utf-8")
    (scripts / "build_options_payoff_lab.py").write_text(accrue, encoding="utf-8")
    stub = tmp_path / "stub_bin"
    stub.mkdir()
    # rev-parse prints a literal. Calling git here would recurse: this
    # directory is first on PATH.
    (stub / "git").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  status) exit 0 ;;\n"
        "  fetch) exit 0 ;;\n"
        "  checkout) exit 0 ;;\n"
        "  rev-parse) echo 0000000 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (stub / "git").chmod(0o755)
    (stub / "pgrep").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (stub / "pgrep").chmod(0o755)
    shim = f'''#!{sys.executable}
import os, runpy, sys
args = sys.argv[1:]
if args and args[0] == "-c":
    real = os.environ.get("PAYOFF_ENGINE_ROOT")
    if real:
        sys.path.insert(0, real)
    code = args[1] if len(args) > 1 else ""
    exec(compile(code, "<payoff-runner>", "exec"))
    raise SystemExit(0)
mod = None
i = 0
while i < len(args):
    if args[i] == "-m" and i + 1 < len(args):
        mod = args[i + 1]
        del args[i:i + 2]
        break
    i += 1
if mod is None:
    sys.stderr.write("fake-python: -m required\\n")
    raise SystemExit(2)
short = mod.rsplit(".", 1)[-1]
repo = os.environ.get("PAYOFF_OPS_ROOT")
if not repo:
    sys.stderr.write("fake-python: PAYOFF_OPS_ROOT not set\\n")
    raise SystemExit(2)
path = os.path.join(repo, "scripts", short + ".py")
if not os.path.isfile(path):
    sys.stderr.write("fake-python: %s not found\\n" % path)
    raise SystemExit(2)
sys.argv = [path] + args
runpy.run_path(path, run_name="__main__")
'''
    (stub / "python").write_text(shim, encoding="utf-8")
    (stub / "python").chmod(0o755)
    return repo, stub


def _run(tmp_path: Path, repo: Path, stub: Path, *, dry_run: bool, store: Path) -> subprocess.CompletedProcess:
    state = tmp_path / "payoff-state"
    env = os.environ.copy()
    env["PATH"] = f"{stub}:{env.get('PATH', '')}"
    env["PAYOFF_OPS_ROOT"] = str(repo)
    env["PAYOFF_STATE_DIR"] = str(state)
    env["PAYOFF_PYTHON"] = str(stub / "python")
    env["PAYOFF_ENGINE_ROOT"] = str(ROOT)
    env["THETADATA_STORE"] = str(store)
    if dry_run:
        env["PAYOFF_DRY_RUN"] = "1"
    else:
        env.pop("PAYOFF_DRY_RUN", None)
    return subprocess.run(
        ["/bin/sh", str(RUNNER)],
        capture_output=True, text=True, env=env, check=False, timeout=60,
    )


def test_runner_fails_loud_when_accrue_returns_nonzero(tmp_path):
    repo, stub = _build_fake_repo(
        tmp_path, accrue=FAKE_ACCRUE_FAIL, fetch=FAKE_FETCH_OK, publish=FAKE_PUBLISH_OK,
    )
    store = tmp_path / "store"
    _write_store(store)
    rc = _run(tmp_path, repo, stub, dry_run=True, store=store)
    assert rc.returncode == 1, (rc.stdout, rc.stderr)
    assert "exit 7" in rc.stdout
    assert "ABORT at step_accrue" in rc.stdout


def test_runner_fails_loud_when_publish_returns_nonzero(tmp_path):
    repo, stub = _build_fake_repo(
        tmp_path, accrue=FAKE_ACCRUE_OK, fetch=FAKE_FETCH_OK, publish=FAKE_PUBLISH_FAIL,
    )
    store = tmp_path / "store"
    _write_store(store)
    rc = _run(tmp_path, repo, stub, dry_run=False, store=store)
    assert rc.returncode == 1, (rc.stdout, rc.stderr)
    assert "publish" in rc.stdout.lower()
    assert "ABORT at step_publish" in rc.stdout


def test_runner_happy_path_exits_zero_with_state_dir_pinned(tmp_path):
    repo, stub = _build_fake_repo(
        tmp_path, accrue=FAKE_ACCRUE_OK, fetch=FAKE_FETCH_OK, publish=FAKE_PUBLISH_OK,
    )
    store = tmp_path / "store"
    _write_store(store)
    rc = _run(tmp_path, repo, stub, dry_run=True, store=store)
    assert rc.returncode == 0, (rc.stdout, rc.stderr)
    state = tmp_path / "payoff-state"
    assert f"state_dir={state}" in rc.stdout
    assert "HEAD=0000000" in rc.stdout
    assert "no live skew runner" in rc.stdout
    assert "PAYOFF_DRY_RUN=1" in rc.stdout
    assert "done" in rc.stdout
    assert (state / "logs").is_dir()
    assert "/Users/chriswong/skew-ops-state" not in rc.stdout


def test_zero_objects_hydrate_does_not_fail_the_first_run(tmp_path):
    repo, stub = _build_fake_repo(
        tmp_path, accrue=FAKE_ACCRUE_OK, fetch=FAKE_FETCH_ZERO, publish=FAKE_PUBLISH_OK,
    )
    store = tmp_path / "store"
    _write_store(store)
    rc = _run(tmp_path, repo, stub, dry_run=True, store=store)
    assert rc.returncode == 0, (rc.stdout, rc.stderr)
    assert "zero options_payoff_lab objects" in rc.stdout
    assert "accrue completed" in rc.stdout


def test_git_stub_rev_parse_is_a_literal():
    text = Path(__file__).read_text(encoding="utf-8")
    assert "rev-parse) echo 0000000 ;;" in text


def _load_publish():
    spec = importlib.util.spec_from_file_location("publish_r2_payoff_under_test", PUBLISH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_publish_r2_registers_options_payoff_lab():
    mod = _load_publish()
    assert "options_payoff_lab" in mod._DATA_DIRS
    assert "options_payoff_lab" not in mod.DEFAULT_DIRS
    assert "options_payoff_lab" not in mod._APPEND_ONLY_DIRS
    assert mod._DATA_DIR_MIN_FILES_OVERRIDE["options_payoff_lab"] == 2
    floor = mod._DATA_DIR_MIN_BYTES["options_payoff_lab"]
    assert 1_000 <= floor <= 1_000_000
    docstring = FETCH.read_text(encoding="utf-8").split('"""', 2)[1]
    assert "publish_r2._DATA_DIRS" in docstring
    assert "data/<dir>" in docstring or "data/" in docstring
