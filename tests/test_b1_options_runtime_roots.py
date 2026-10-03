"""Focused proof for Options Alpha B1 runtime roots.

Shell runs use a copy of the production script. The copy changes only the
Python interpreter, and for the index lane also the machine-git helper and
the push-repo path. Production source keeps the absolute defaults. The fake
interpreter executes the index manifest gate from the script itself. Nothing
here calls a live API, reads a secret, publishes, or starts launchd.
"""
from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INDEX_SRC = ROOT / "ops" / "launchd" / "run_index_gex_history.sh"
MATRIX_SRC = ROOT / "ops" / "launchd" / "run_options_matrix.sh"
HUB_SRC = ROOT / "scripts" / "build_options_hub_nightly.py"
RUNBOOK = ROOT / "ops" / "LIVE_FLOW_RUNBOOK.md"
ENGINE = ROOT / "engine" / "gex_engine.py"

REAL_DEFAULT = "/Users/chriswong/flow-ops-wt"
REAL_PUSH = "/Users/chriswong/indexgex-push-repo-private"
REAL_RUNTIME = "/Users/chriswong/macro-publisher-runtime"
REAL_PYTHON = "/opt/homebrew/Caskroom/miniconda/base/bin/python"
ENGINE_SHA = "f307223722e9ff10c62865d5c92bb7385970ec1da94c6477d19cd9269d768e5c"
BASIS_COMMIT = "7084e176a8d510f96082d4195ee4117e08002890"

_REAL_DEFAULT_EXISTED = Path(REAL_DEFAULT).exists()
_REAL_PUSH_EXISTED = Path(REAL_PUSH).exists()
_REAL_RUNTIME_EXISTED = Path(REAL_RUNTIME).exists()

FAKE_PYTHON = textwrap.dedent(
    """\
    #!/usr/bin/python3
    import json, os, sys
    from pathlib import Path

    log = Path(os.environ["B1_LOG"])
    argv = sys.argv[1:]

    def record(kind):
        row = {
            "kind": kind,
            "argv": argv,
            "cwd": os.getcwd(),
            "pythonpath": os.environ.get("PYTHONPATH"),
        }
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\\n")

    if argv and argv[0] == "-":
        record("gate")
        src = sys.stdin.read()
        sys.argv = ["gate", *argv[1:]]
        exec(compile(src, "<index-gate>", "exec"), {"__name__": "__main__"})
        sys.exit(0)

    if argv[:2] == ["-m", "scripts.build_index_gex_history"]:
        record("build")
        rc = int(os.environ.get("B1_ENGINE_RC", "0"))
        if rc != 0:
            sys.exit(rc)
        mode = os.environ.get("B1_MANIFEST", "ok")
        art = Path("data") / "index_gex_history"
        art.mkdir(parents=True, exist_ok=True)
        roots = {"SPY": [2017], "QQQ": [2017], "IWM": [2017], "DIA": [2017]}
        refused = {}
        if mode == "partial":
            roots.pop("DIA")
        elif mode == "shrink":
            refused = {"DIA": "shrunk"}
        names = ["SPY.parquet", "QQQ.parquet", "IWM.parquet", "DIA.parquet"]
        skip = os.environ.get("B1_SKIP_FILE", "")
        for name in names:
            if name != skip:
                (art / name).write_text("x", encoding="utf-8")
        (art / "_manifest.json").write_text(
            json.dumps({"roots_read": roots, "roots_refused_shrink": refused}),
            encoding="utf-8",
        )
        sys.exit(0)

    if argv[:2] == ["-m", "scripts.publish_r2"]:
        record("r2")
        sys.exit(int(os.environ.get("B1_R2_RC", "0")))

    if argv[:2] == ["-m", "scripts.build_options_matrix"]:
        record("matrix")
        sys.exit(int(os.environ.get("B1_MATRIX_RC", "0")))

    record("other")
    sys.exit(99)
    """
)

FAKE_GIT = textwrap.dedent(
    """\
    import json, os, sys
    from pathlib import Path

    log = Path(os.environ["B1_LOG"])
    argv = sys.argv[1:]
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "git", "argv": argv}) + "\\n")

    def repo():
        if "-C" in argv:
            return argv[argv.index("-C") + 1]
        return ""

    if argv and argv[0] == "clone":
        dest = Path(argv[-1])
        (dest / ".git").mkdir(parents=True, exist_ok=True)
        (dest / "data" / "index_gex_history").mkdir(parents=True, exist_ok=True)
        sys.exit(0)
    if "rev-parse" in argv:
        chosen = repo()
        if "--show-toplevel" in argv:
            print(chosen)
        if "--absolute-git-dir" in argv:
            print(str(Path(chosen) / ".git"))
        sys.exit(0)
    if "diff" in argv and "--quiet" in argv:
        sys.exit(1)
    sys.exit(0)
    """
)


def _plain(path: Path) -> str:
    text = str(path)
    if any(ch in text for ch in " \n'\"\\$"):
        raise RuntimeError(f"fixture path is not shell-safe: {text}")
    return text


def _rows(log: Path) -> list[dict]:
    if not log.exists() or not log.read_text(encoding="utf-8").strip():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_fakes(tmp: Path) -> tuple[Path, Path, Path]:
    fake_py = tmp / "fake-python"
    fake_py.write_text(FAKE_PYTHON, encoding="utf-8")
    fake_py.chmod(0o755)
    fake_git = tmp / "fake-machine-git.py"
    fake_git.write_text(FAKE_GIT, encoding="utf-8")
    log = tmp / "invocations.jsonl"
    return fake_py, fake_git, log


def _code_repo(path: Path, script_name: str) -> Path:
    scripts = path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / script_name).write_text("# fixture\\n", encoding="utf-8")
    return path


def _live_paths_unchanged() -> None:
    assert Path(REAL_PUSH).exists() == _REAL_PUSH_EXISTED
    assert Path(REAL_DEFAULT).exists() == _REAL_DEFAULT_EXISTED
    assert Path(REAL_RUNTIME).exists() == _REAL_RUNTIME_EXISTED


def _run(script: Path, env: dict, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", str(script)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _index_copy(tmp: Path, fake_py: Path, fake_git: Path, push_repo: Path, default_root: str | None = None) -> Path:
    text = INDEX_SRC.read_text(encoding="utf-8")
    text = text.replace(
        f'PYTHON="{REAL_PYTHON}"',
        f'PYTHON="{_plain(fake_py)}"',
        1,
    )
    text = text.replace(
        'MACHINE_GIT="$RUNTIME/scripts/macro_machine_git.py"',
        f'MACHINE_GIT="{_plain(fake_git)}"',
        1,
    )
    text = text.replace(
        f'PUSH_REPO="{REAL_PUSH}"',
        f'PUSH_REPO="{_plain(push_repo)}"',
        1,
    )
    if default_root is not None:
        text = text.replace(
            'REPO="${MACRO_INDEX_GEX_HISTORY_ROOT:-/Users/chriswong/flow-ops-wt}"',
            f'REPO="${{MACRO_INDEX_GEX_HISTORY_ROOT:-{default_root}}}"',
            1,
        )
    dest = tmp / "run_index_gex_history.sh"
    dest.write_text(text, encoding="utf-8")
    return dest


def _matrix_copy(tmp: Path, fake_py: Path, default_root: str | None = None) -> Path:
    text = MATRIX_SRC.read_text(encoding="utf-8")
    text = text.replace(
        f'PYTHON="{REAL_PYTHON}"',
        f'PYTHON="{_plain(fake_py)}"',
        1,
    )
    if default_root is not None:
        text = text.replace(
            'REPO="${MACRO_OPTIONS_MATRIX_ROOT:-/Users/chriswong/flow-ops-wt}"',
            f'REPO="${{MACRO_OPTIONS_MATRIX_ROOT:-{default_root}}}"',
            1,
        )
    dest = tmp / "run_options_matrix.sh"
    dest.write_text(text, encoding="utf-8")
    return dest


def _base_env(log: Path, **extra: str) -> dict[str, str]:
    env = {
        "PATH": "/bin:/usr/bin",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "B1_LOG": _plain(log),
        "MACRO_PUBLISH_GIT_SSH_KEY": "/tmp/b1-not-a-key",
    }
    env.update(extra)
    return env


def _plist(name: str) -> dict:
    text = (ROOT / "ops" / "launchd" / name).read_text(encoding="utf-8")
    stripped = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return plistlib.loads(stripped.encode("utf-8"))


def test_engine_hash_and_production_pins_are_unchanged() -> None:
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest() == ENGINE_SHA
    index = INDEX_SRC.read_text(encoding="utf-8")
    matrix = MATRIX_SRC.read_text(encoding="utf-8")
    assert 'REPO="${MACRO_INDEX_GEX_HISTORY_ROOT:-/Users/chriswong/flow-ops-wt}"' in index
    assert 'RUNTIME="/Users/chriswong/macro-publisher-runtime"' in index
    assert f'PUSH_REPO="{REAL_PUSH}"' in index
    assert 'MACHINE_GIT="$RUNTIME/scripts/macro_machine_git.py"' in index
    assert 'REMOTE_URL="git@github.com:mastermindx-market-intelligence/macro.git"' in index
    assert 'ART_DIR="data/index_gex_history"' in index
    assert f'PYTHON="{REAL_PYTHON}"' in index
    assert 'export PYTHONPATH="$REPO"' in index
    assert "SPY.parquet QQQ.parquet IWM.parquet DIA.parquet _manifest.json" in index
    assert '-m scripts.publish_r2 --dirs index_gex_history --no-manifest' in index
    assert "macro-publisher-runtime/ops/launchd/run_index_gex_history.sh" in index
    assert 'REPO="${MACRO_OPTIONS_MATRIX_ROOT:-/Users/chriswong/flow-ops-wt}"' in matrix
    assert 'STORE="${THETADATA_STORE:-/Users/chriswong/theta-ops-wt/data/thetadata_eod}"' in matrix
    assert "MAX_ATTEMPTS=6" in matrix
    assert "SLEEP_SECS=1200" in matrix
    assert "MATRIX_FRESHNESS_BYPASS" in matrix
    assert "MATRIX_NO_PUBLISH" in matrix
    assert "GEX_STATE_PUBLICATION_OWNER=com.mastermind.gexstate-mirror" in matrix
    assert "options_structure/gex_state/" not in matrix
    assert "s3.upload_file" not in matrix
    assert 'export PYTHONPATH="$REPO"' in matrix
    assert "-m scripts.build_options_matrix --publish" in matrix


def test_index_explicit_root_publishes_r2_before_git(tmp_path: Path) -> None:
    fake_py, fake_git, log = _write_fakes(tmp_path)
    repo = _code_repo(tmp_path / "explicit-root", "build_index_gex_history.py")
    push = tmp_path / "push-repo"
    script = _index_copy(tmp_path, fake_py, fake_git, push)
    wrong = tmp_path / "wrong-cwd"
    wrong.mkdir()
    result = _run(
        script,
        _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT=_plain(repo)),
        wrong,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "manifest gate OK" in result.stdout
    rows = _rows(log)
    kinds = [row["kind"] for row in rows]
    assert kinds[0] == "build"
    assert "gate" in kinds
    assert "r2" in kinds
    build_at = kinds.index("build")
    gate_at = kinds.index("gate")
    r2_at = kinds.index("r2")
    push_at = next(i for i, row in enumerate(rows) if row["kind"] == "git" and "push" in row["argv"])
    assert build_at < gate_at < r2_at < push_at
    assert rows[r2_at]["argv"] == ["-m", "scripts.publish_r2", "--dirs", "index_gex_history", "--no-manifest"]
    assert rows[build_at]["cwd"] == _plain(repo)
    assert rows[build_at]["pythonpath"] == _plain(repo)
    assert rows[gate_at]["pythonpath"] == _plain(repo)
    assert list(wrong.iterdir()) == []
    _live_paths_unchanged()


def test_index_empty_and_unset_select_the_default_expression(tmp_path: Path) -> None:
    fake_py, fake_git, log = _write_fakes(tmp_path)
    default_repo = _code_repo(tmp_path / "default-root", "build_index_gex_history.py")
    other = _code_repo(tmp_path / "other-root", "build_index_gex_history.py")
    push = tmp_path / "push-repo"
    script = _index_copy(tmp_path, fake_py, fake_git, push, default_root=_plain(default_repo))
    wrong = tmp_path / "wrong-cwd"
    wrong.mkdir()
    for label, env in (
        ("unset", _base_env(log)),
        ("empty", _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT="")),
    ):
        log.write_text("", encoding="utf-8")
        result = _run(script, env, wrong)
        assert result.returncode == 0, label + result.stdout + result.stderr
        rows = _rows(log)
        assert rows[0]["cwd"] == _plain(default_repo)
        assert rows[0]["pythonpath"] == _plain(default_repo)
        assert rows[0]["cwd"] != _plain(other)
        assert rows[0]["cwd"] != _plain(wrong)
    _live_paths_unchanged()


def test_index_missing_real_default_stops_before_python(tmp_path: Path) -> None:
    assert not _REAL_DEFAULT_EXISTED
    fake_py, fake_git, log = _write_fakes(tmp_path)
    script = _index_copy(tmp_path, fake_py, fake_git, tmp_path / "push-repo")
    wrong = tmp_path / "wrong-cwd"
    wrong.mkdir()
    for env in (_base_env(log), _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT="")):
        log.write_text("", encoding="utf-8")
        result = _run(script, env, wrong)
        assert result.returncode == 1
        assert REAL_DEFAULT in result.stdout + result.stderr
        assert _rows(log) == []
        assert list(wrong.iterdir()) == []
    _live_paths_unchanged()


@pytest.mark.parametrize(
    "value",
    ["relative/path", "./relative", "   ", "\t"],
)
def test_index_relative_or_blank_root_is_refused_before_python(tmp_path: Path, value: str) -> None:
    fake_py, fake_git, log = _write_fakes(tmp_path)
    present = tmp_path / "relative"
    _code_repo(present, "build_index_gex_history.py")
    script = _index_copy(tmp_path, fake_py, fake_git, tmp_path / "push-repo")
    result = _run(
        script,
        _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT=value),
        tmp_path,
    )
    assert result.returncode == 1
    assert "absolute existing directory" in result.stdout + result.stderr
    assert _rows(log) == []
    _live_paths_unchanged()


def test_index_missing_directory_and_non_code_directory_stop_before_python(tmp_path: Path) -> None:
    fake_py, fake_git, log = _write_fakes(tmp_path)
    script = _index_copy(tmp_path, fake_py, fake_git, tmp_path / "push-repo")
    missing = tmp_path / "does-not-exist"
    bare = tmp_path / "bare-dir"
    bare.mkdir()
    missing_result = _run(
        script,
        _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT=_plain(missing)),
        tmp_path,
    )
    assert missing_result.returncode == 1
    assert "not an existing directory" in missing_result.stdout + missing_result.stderr
    assert _rows(log) == []
    log.write_text("", encoding="utf-8")
    bare_env = _base_env(log, MACRO_INDEX_GEX_HISTORY_ROOT=_plain(bare))
    bare_env.pop("MACRO_PUBLISH_GIT_SSH_KEY")
    bare_result = _run(script, bare_env, tmp_path)
    assert bare_result.returncode == 1
    assert "build_index_gex_history.py" in bare_result.stdout + bare_result.stderr
    assert "MACRO_PUBLISH_GIT_SSH_KEY is required" not in bare_result.stdout + bare_result.stderr
    assert _rows(log) == []
    _live_paths_unchanged()


@pytest.mark.parametrize(
    ("mode", "skip", "engine_rc", "r2_rc", "fragment", "expect_r2", "expect_push", "exit_code"),
    [
        ("partial", "", "0", "0", "partial rebuild", False, False, 1),
        ("shrink", "", "0", "0", "shrink guard refused", False, False, 1),
        ("ok", "DIA.parquet", "0", "0", "DIA.parquet missing", False, False, 1),
        ("ok", "", "1", "0", "rebuild failed", False, False, 1),
        ("ok", "", "0", "1", "R2 sync failed", True, True, 0),
    ],
)
def test_index_gate_stops_a_bad_rebuild_and_r2_failure_still_pushes(
    tmp_path: Path,
    mode: str,
    skip: str,
    engine_rc: str,
    r2_rc: str,
    fragment: str,
    expect_r2: bool,
    expect_push: bool,
    exit_code: int,
) -> None:
    fake_py, fake_git, log = _write_fakes(tmp_path)
    repo = _code_repo(tmp_path / "repo", "build_index_gex_history.py")
    script = _index_copy(tmp_path, fake_py, fake_git, tmp_path / "push-repo")
    env = _base_env(
        log,
        MACRO_INDEX_GEX_HISTORY_ROOT=_plain(repo),
        B1_MANIFEST=mode,
        B1_SKIP_FILE=skip,
        B1_ENGINE_RC=engine_rc,
        B1_R2_RC=r2_rc,
    )
    result = _run(script, env, tmp_path)
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert fragment in result.stdout + result.stderr
    rows = _rows(log)
    kinds = [row["kind"] for row in rows]
    assert ("r2" in kinds) is expect_r2
    assert any(row["kind"] == "git" and "push" in row["argv"] for row in rows) is expect_push
    if engine_rc == "1":
        assert "gate" not in kinds
    else:
        assert "gate" in kinds
    _live_paths_unchanged()


def test_matrix_explicit_default_and_publish_flag(tmp_path: Path) -> None:
    fake_py, _, log = _write_fakes(tmp_path)
    explicit = _code_repo(tmp_path / "explicit", "build_options_matrix.py")
    default_repo = _code_repo(tmp_path / "default", "build_options_matrix.py")
    store = tmp_path / "theta"
    store.mkdir()
    wrong = tmp_path / "wrong-cwd"
    wrong.mkdir()
    explicit_script = _matrix_copy(tmp_path, fake_py)
    explicit_result = _run(
        explicit_script,
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT=_plain(explicit),
            MATRIX_FRESHNESS_BYPASS="1",
            THETADATA_STORE=_plain(store),
        ),
        wrong,
    )
    assert explicit_result.returncode == 0, explicit_result.stdout + explicit_result.stderr
    rows = _rows(log)
    assert len(rows) == 1
    assert rows[0]["kind"] == "matrix"
    assert rows[0]["argv"] == ["-m", "scripts.build_options_matrix", "--publish"]
    assert rows[0]["cwd"] == _plain(explicit)
    assert rows[0]["pythonpath"] == _plain(explicit)
    log.write_text("", encoding="utf-8")
    dry = _run(
        explicit_script,
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT=_plain(explicit),
            MATRIX_FRESHNESS_BYPASS="1",
            MATRIX_NO_PUBLISH="1",
            THETADATA_STORE=_plain(store),
            B1_MATRIX_RC="4",
        ),
        wrong,
    )
    assert dry.returncode == 4
    assert _rows(log)[0]["argv"] == ["-m", "scripts.build_options_matrix"]
    default_script = _matrix_copy(tmp_path, fake_py, default_root=_plain(default_repo))
    for env in (
        _base_env(log, MATRIX_FRESHNESS_BYPASS="1", THETADATA_STORE=_plain(store)),
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT="",
            MATRIX_FRESHNESS_BYPASS="1",
            THETADATA_STORE=_plain(store),
        ),
    ):
        log.write_text("", encoding="utf-8")
        result = _run(default_script, env, wrong)
        assert result.returncode == 0, result.stdout + result.stderr
        assert _rows(log)[0]["cwd"] == _plain(default_repo)
        assert _rows(log)[0]["pythonpath"] == _plain(default_repo)
        assert list(wrong.iterdir()) == []
    _live_paths_unchanged()


@pytest.mark.parametrize("value", ["relative/path", "./relative", "   "])
def test_matrix_bad_root_does_not_call_python(tmp_path: Path, value: str) -> None:
    fake_py, _, log = _write_fakes(tmp_path)
    _code_repo(tmp_path / "relative", "build_options_matrix.py")
    script = _matrix_copy(tmp_path, fake_py)
    store = tmp_path / "theta"
    store.mkdir()
    result = _run(
        script,
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT=value,
            MATRIX_FRESHNESS_BYPASS="1",
            THETADATA_STORE=_plain(store),
        ),
        tmp_path,
    )
    assert result.returncode == 1
    assert "absolute existing directory" in result.stdout + result.stderr
    assert _rows(log) == []


def test_matrix_missing_and_non_code_roots_stop_before_python(tmp_path: Path) -> None:
    fake_py, _, log = _write_fakes(tmp_path)
    script = _matrix_copy(tmp_path, fake_py)
    store = tmp_path / "theta"
    store.mkdir()
    missing = tmp_path / "missing-matrix-root"
    bare = tmp_path / "bare-matrix"
    bare.mkdir()
    missing_result = _run(
        script,
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT=_plain(missing),
            MATRIX_FRESHNESS_BYPASS="1",
            THETADATA_STORE=_plain(store),
        ),
        tmp_path,
    )
    assert missing_result.returncode == 1
    assert _rows(log) == []
    log.write_text("", encoding="utf-8")
    bare_result = _run(
        script,
        _base_env(
            log,
            MACRO_OPTIONS_MATRIX_ROOT=_plain(bare),
            MATRIX_FRESHNESS_BYPASS="1",
            THETADATA_STORE=_plain(store),
        ),
        tmp_path,
    )
    assert bare_result.returncode == 1
    assert "build_options_matrix.py" in bare_result.stdout + bare_result.stderr
    assert _rows(log) == []


def test_matrix_real_default_missing_stops_before_python(tmp_path: Path) -> None:
    assert not _REAL_DEFAULT_EXISTED
    fake_py, _, log = _write_fakes(tmp_path)
    script = _matrix_copy(tmp_path, fake_py)
    store = tmp_path / "theta"
    store.mkdir()
    result = _run(
        script,
        _base_env(log, MATRIX_FRESHNESS_BYPASS="1", THETADATA_STORE=_plain(store), MACRO_OPTIONS_MATRIX_ROOT=""),
        tmp_path,
    )
    assert result.returncode == 1
    assert REAL_DEFAULT in result.stdout + result.stderr
    assert _rows(log) == []


def test_plist_semantics_change_only_the_designated_roots() -> None:
    index = _plist("com.macro.indexgexhistory.plist")
    matrix = _plist("com.macro.optionsmatrix.plist")
    hub = _plist("com.mastermind.optionshub.plist")

    assert index["Label"] == "com.macro.indexgexhistory"
    assert index["StartCalendarInterval"] == {"Weekday": 0, "Hour": 20, "Minute": 0}
    assert index["StandardOutPath"] == "/tmp/index_gex_history.stdout.log"
    assert index["StandardErrorPath"] == "/tmp/index_gex_history.stderr.log"
    assert index["KeepAlive"] is False
    assert index["ThrottleInterval"] == 300
    assert index["Nice"] == 5
    assert index["SoftResourceLimits"] == {"NumberOfFiles": 4096}
    assert "EnvironmentVariables" not in index
    assert index["ProgramArguments"] == [
        "/Users/chriswong/macro-publisher-runtime/ops/launchd/run_with_env.sh",
        "/Users/chriswong/flow-ops-wt/.env",
        "/usr/bin/env",
        "MACRO_PUBLISH_GIT_SSH_KEY=/Users/chriswong/.ssh/macro_dashboard_deploy",
        "MACRO_INDEX_GEX_HISTORY_ROOT=/Users/chriswong/indexgex-ops-wt",
        "PYTHONPATH=/Users/chriswong/indexgex-ops-wt",
        "/bin/sh",
        "/Users/chriswong/indexgex-ops-wt/ops/launchd/run_index_gex_history.sh",
    ]
    assert index["WorkingDirectory"] == "/Users/chriswong/indexgex-ops-wt"

    assert matrix["Label"] == "com.macro.optionsmatrix"
    assert matrix["StartCalendarInterval"] == [
        {"Weekday": day, "Hour": 16, "Minute": 0} for day in range(1, 6)
    ]
    assert matrix["StandardOutPath"] == "/tmp/optionsmatrix.stdout.log"
    assert matrix["StandardErrorPath"] == "/tmp/optionsmatrix.stderr.log"
    assert matrix["KeepAlive"] is False
    assert matrix["ThrottleInterval"] == 60
    assert "Nice" not in matrix
    assert "SoftResourceLimits" not in matrix
    assert matrix["ProgramArguments"] == [
        "/Users/chriswong/optionsmatrix-ops-wt/ops/launchd/run_with_env.sh",
        "/Users/chriswong/flow-ops-wt/.env",
        "/Users/chriswong/optionsmatrix-ops-wt/ops/launchd/run_options_matrix.sh",
    ]
    assert matrix["WorkingDirectory"] == "/Users/chriswong/optionsmatrix-ops-wt"
    assert matrix["EnvironmentVariables"] == {
        "PYTHONPATH": "/Users/chriswong/optionsmatrix-ops-wt",
        "MACRO_OPTIONS_MATRIX_ROOT": "/Users/chriswong/optionsmatrix-ops-wt",
        "THETADATA_STORE": "/Users/chriswong/theta-ops-wt/data/thetadata_eod",
    }

    assert hub["Label"] == "com.mastermind.optionshub"
    assert hub["StartCalendarInterval"] == [
        {"Weekday": 1, "Hour": 16, "Minute": 45},
        {"Weekday": 2, "Hour": 16, "Minute": 45},
        {"Weekday": 3, "Hour": 16, "Minute": 45},
        {"Weekday": 4, "Hour": 16, "Minute": 45},
        {"Weekday": 5, "Hour": 16, "Minute": 45},
        {"Weekday": 6, "Hour": 17, "Minute": 30},
        {"Weekday": 0, "Hour": 17, "Minute": 30},
    ]
    assert hub["StandardOutPath"] == "/tmp/optionshub.stdout.log"
    assert hub["StandardErrorPath"] == "/tmp/optionshub.stderr.log"
    assert hub["KeepAlive"] is False
    assert hub["ThrottleInterval"] == 60
    assert "Nice" not in hub
    assert "SoftResourceLimits" not in hub
    assert hub["ProgramArguments"] == [
        "/Users/chriswong/optionshub-ops-wt/ops/launchd/run_with_env.sh",
        "/Users/chriswong/Documents/Cluade/Macro Dashboard/.env",
        REAL_PYTHON,
        "-m",
        "scripts.build_options_hub_nightly",
        "--publish",
    ]
    assert hub["WorkingDirectory"] == "/Users/chriswong/optionshub-ops-wt"
    assert hub["EnvironmentVariables"] == {
        "HUB_ROOT_BUDGET_S": "420",
        "PYTHONPATH": "/Users/chriswong/optionshub-ops-wt",
        "OPTIONS_HUB_INPUT_ROOT": "/Users/chriswong/hub-ops-wt",
    }
    assert "THETADATA_STORE" not in hub["EnvironmentVariables"]
    assert "R2_" not in json.dumps(index) + json.dumps(matrix) + json.dumps(hub)


def test_runbook_records_the_three_symlinks_and_hub_input_authority() -> None:
    text = " ".join(RUNBOOK.read_text(encoding="utf-8").split())
    assert "The table above is the installed measurement." in text
    assert "/Users/chriswong/indexgex-ops-wt" in text
    assert "/Users/chriswong/flow-ops-wt/data/index_gex_history" in text
    assert "/Users/chriswong/optionsmatrix-ops-wt" in text
    assert "/Users/chriswong/flow-ops-wt/data/live_flow_out/options_matrix" in text
    assert "/Users/chriswong/optionshub-ops-wt" in text
    assert "/Users/chriswong/hub-ops-wt/data/live_flow_out/options_hub" in text
    assert "OPTIONS_HUB_INPUT_ROOT=/Users/chriswong/hub-ops-wt" in text
    assert "data/polygon_gex" in text
    assert "data/gex/latest.json" in text
    assert "site/basketdata/fear_greed.json" in text
    assert "data/tape_flow/daily" in text
    assert "data/live_flow_out" in text
    assert "An empty value is not the current directory." in text
    assert BASIS_COMMIT in text
    assert ENGINE_SHA in text
    assert "200 GiB" in text
    assert "macro_machine_git.py" in text
    assert "A later scheduled run, owned by the runtime operator, is the only live proof." in text
    assert "Do not clone a tree, create a symlink, copy an environment file" in text


def _hub():
    import scripts.build_options_hub_nightly as mod
    return mod


def _install_hub_fakes(mod, monkeypatch, data_root: Path, seen: dict) -> None:
    import engine.thetadata_store as td
    import lib

    fake_config = types.ModuleType("lib.config")
    fake_config.data_dir = lambda: data_root
    fake_store = types.ModuleType("lib.store")

    def _blocked(*_a, **_k):
        raise RuntimeError("run_status blocked in this test")

    fake_store.read_status = _blocked
    fake_store.write_status = _blocked
    monkeypatch.setitem(sys.modules, "lib.config", fake_config)
    monkeypatch.setitem(sys.modules, "lib.store", fake_store)
    monkeypatch.setattr(lib, "config", fake_config, raising=False)
    monkeypatch.setattr(lib, "store", fake_store, raising=False)
    monkeypatch.setattr(td, "_has_store_content", lambda *_a, **_k: True)
    monkeypatch.setattr(td, "universe", lambda *_a, **_k: ["SPY"])

    def _explode(*_a, **_k):
        raise AssertionError("ThetaData resolution must not run when --theta-store is set")

    monkeypatch.setattr(td, "resolve_thetadata_store", _explode)
    monkeypatch.setattr(mod, "_arm_stall_watchdog", lambda *_a, **_k: seen.setdefault("order", []).append("watchdog"))
    monkeypatch.setattr(mod, "preflight_store", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "OI_SUITE_ENABLED", False)
    monkeypatch.setattr(mod, "levels_payload_from_gex", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "moves_payload", lambda *_a, **_k: {"expected_move": None})
    monkeypatch.setattr(mod, "build_cross_root", lambda *_a, **_k: ({"rows": []}, {"rows": []}))
    monkeypatch.setattr(mod, "compute_oi_change_cross", lambda *_a, **_k: {"rows": []})

    def build_root(root, asof, theta_store, polygon_gex_dir=None):
        seen["polygon"] = Path(polygon_gex_dir)
        seen["theta"] = Path(theta_store)
        seen["built_root"] = root
        seen["asof"] = asof
        return ({"atm_iv": None}, {"spot_ref": 1, "by_strike": [{"k": 1}]}, None)

    def build_tickers_ctx(root, asof, tape_flow_dir):
        seen["tape"] = Path(tape_flow_dir)
        return {"root": root, "asof": asof}

    def build_context_payload(*_a, **kwargs):
        seen["gex"] = Path(kwargs["gex_latest_path"])
        seen["fear"] = Path(kwargs["fear_greed_path"])
        return {"asof": "recorded"}

    def build_oi_confirmed(*_a, **kwargs):
        seen["live"] = Path(kwargs["live_flow_out_dir"])
        return []

    monkeypatch.setattr(mod, "build_root", build_root)
    monkeypatch.setattr(mod, "build_tickers_ctx", build_tickers_ctx)
    monkeypatch.setattr(mod, "build_context_payload", build_context_payload)
    monkeypatch.setattr(mod, "build_oi_confirmed", build_oi_confirmed)
    monkeypatch.setattr(mod, "_r2_client", _explode)


def _files_under(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(str(item.relative_to(path)) for item in path.rglob("*") if item.is_file())


def test_hub_resolver_keeps_legacy_paths_until_an_absolute_root_is_set(tmp_path: Path, monkeypatch) -> None:
    mod = _hub()
    monkeypatch.delenv("OPTIONS_HUB_INPUT_ROOT", raising=False)
    assert mod._options_hub_input_root_or_none() is None
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", "")
    assert mod._options_hub_input_root_or_none() is None
    data_root = tmp_path / "legacy-data"
    repo_root = tmp_path / "repo"
    legacy = mod.resolve_options_hub_read_inputs(data_root, repo_root)
    assert legacy == {
        "polygon_gex_dir": data_root / "polygon_gex",
        "gex_latest_path": data_root / "gex" / "latest.json",
        "fear_greed_path": repo_root / "site" / "basketdata" / "fear_greed.json",
        "tape_flow_dir": data_root / "tape_flow" / "daily",
        "live_flow_out_dir": data_root / "live_flow_out",
    }
    chosen = tmp_path / "hub-inputs"
    chosen.mkdir()
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", _plain(chosen))
    redirected = mod.resolve_options_hub_read_inputs(data_root, repo_root)
    assert redirected == {
        "polygon_gex_dir": chosen / "data" / "polygon_gex",
        "gex_latest_path": chosen / "data" / "gex" / "latest.json",
        "fear_greed_path": chosen / "site" / "basketdata" / "fear_greed.json",
        "tape_flow_dir": chosen / "data" / "tape_flow" / "daily",
        "live_flow_out_dir": chosen / "data" / "live_flow_out",
    }
    assert _files_under(chosen) == []
    assert mod.R2_PREFIX == "options_hub/"
    source = HUB_SRC.read_text(encoding="utf-8")
    main_src = source.split("def main()", 1)[1]
    assert main_src.index("_options_hub_input_root_or_none()") < main_src.index("_arm_stall_watchdog()")
    assert main_src.index("resolve_options_hub_read_inputs") < main_src.index("out_dir.mkdir")


@pytest.mark.parametrize("value", ["relative/hub", "   ", "/tmp/b1-hub-root-missing"])
def test_hub_invalid_root_fails_before_watchdog_or_writes(tmp_path: Path, monkeypatch, value: str) -> None:
    mod = _hub()
    if value.startswith("/tmp/"):
        value = _plain(tmp_path / "missing-hub-root")
    seen: dict = {}
    data_root = tmp_path / "legacy-data"
    out = tmp_path / "out-must-not-be-created"

    def _boom(name):
        def _inner(*_a, **_k):
            seen[name] = True
            raise AssertionError(name)
        return _inner

    monkeypatch.setattr(mod, "_arm_stall_watchdog", _boom("watchdog"))
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", value)
    monkeypatch.setattr(
        sys,
        "argv",
        ["build", "--no-publish", "--date", "2026-01-02", "--out", str(out), "--roots", "SPY"],
    )
    with pytest.raises(SystemExit) as caught:
        mod.main()
    assert "absolute directory" in str(caught.value)
    assert seen == {}
    assert not out.exists()
    assert not data_root.exists()


def test_hub_file_root_is_refused(tmp_path: Path, monkeypatch) -> None:
    mod = _hub()
    marker = tmp_path / "not-a-directory"
    marker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", _plain(marker))
    with pytest.raises(SystemExit):
        mod._options_hub_input_root_or_none()


def test_hub_main_sends_each_producer_the_input_root_and_writes_only_to_data_root(tmp_path: Path, monkeypatch) -> None:
    mod = _hub()
    data_root = tmp_path / "legacy-data"
    inputs = tmp_path / "hub-inputs"
    inputs.mkdir()
    theta = tmp_path / "theta"
    theta.mkdir()
    seen: dict = {}
    _install_hub_fakes(mod, monkeypatch, data_root, seen)
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", _plain(inputs))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build",
            "--no-publish",
            "--date",
            "2026-01-02",
            "--theta-store",
            _plain(theta),
        ],
    )
    mod.main()
    out = data_root / "live_flow_out" / "options_hub"
    assert seen["polygon"] == inputs / "data" / "polygon_gex"
    assert seen["gex"] == inputs / "data" / "gex" / "latest.json"
    assert seen["fear"] == inputs / "site" / "basketdata" / "fear_greed.json"
    assert seen["tape"] == inputs / "data" / "tape_flow" / "daily"
    assert seen["live"] == inputs / "data" / "live_flow_out"
    assert seen["theta"] == theta
    assert seen["order"] == ["watchdog"]
    assert (out / "vol" / "SPY.json").is_file()
    assert (out / "context.json").is_file()
    assert _files_under(inputs) == []
    assert all(path == out or out in path.parents for path in data_root.rglob("*") if path.is_file() or path == out)
    written = [path for path in data_root.rglob("*") if path.is_file()]
    assert written
    assert all(out in path.parents for path in written)


def test_hub_main_unset_and_empty_keep_legacy_producer_paths(tmp_path: Path, monkeypatch) -> None:
    mod = _hub()
    data_root = tmp_path / "legacy-data"
    theta = tmp_path / "theta"
    theta.mkdir()
    seen: dict = {}
    _install_hub_fakes(mod, monkeypatch, data_root, seen)
    monkeypatch.delenv("OPTIONS_HUB_INPUT_ROOT", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["build", "--no-publish", "--date", "2026-01-02", "--theta-store", _plain(theta)],
    )
    mod.main()
    assert seen["polygon"] == data_root / "polygon_gex"
    assert seen["gex"] == data_root / "gex" / "latest.json"
    assert seen["fear"] == ROOT / "site" / "basketdata" / "fear_greed.json"
    assert seen["tape"] == data_root / "tape_flow" / "daily"
    assert seen["live"] == data_root / "live_flow_out"
    out = data_root / "live_flow_out" / "options_hub"
    assert (out / "gex" / "SPY.json").is_file()
    assert seen["live"] != out

    seen.clear()
    monkeypatch.setenv("OPTIONS_HUB_INPUT_ROOT", "")
    mod.main()
    assert seen["polygon"] == data_root / "polygon_gex"
    assert seen["fear"] == ROOT / "site" / "basketdata" / "fear_greed.json"
    assert seen["live"] == data_root / "live_flow_out"


def test_shells_parse_and_hub_script_compiles() -> None:
    for script in (INDEX_SRC, MATRIX_SRC):
        result = subprocess.run(["/bin/bash", "-n", str(script)], check=False, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    for name in (
        "com.macro.indexgexhistory.plist",
        "com.macro.optionsmatrix.plist",
        "com.mastermind.optionshub.plist",
    ):
        _plist(name)
    compile(HUB_SRC.read_text(encoding="utf-8"), str(HUB_SRC), "exec")


def test_ci_names_this_suite() -> None:
    text = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert "tests/test_b1_options_runtime_roots.py" in text
