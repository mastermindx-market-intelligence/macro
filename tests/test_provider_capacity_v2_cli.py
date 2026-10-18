"""The dormant capacity entrypoint must resolve its own Macro producer."""
from pathlib import Path
import os
import subprocess
import sys


def test_entrypoint_import_uses_own_repo_against_foreign_engine(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    foreign = tmp_path / "engine"
    foreign.mkdir()
    (foreign / "__init__.py").write_text("")
    (foreign / "provider_capacity_v2.py").write_text(
        "raise AssertionError('FOREIGN_CAPACITY_PRODUCER')\n"
    )
    # Import only: do not invoke the parameterless live Control acquisition.
    code = (
        "import runpy, sys; "
        "runpy.run_path(sys.argv[1], run_name='capacity_import_check'); "
        "print(sys.modules['engine.provider_capacity_v2'].__file__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code,
         str(repo / "scripts" / "build_provider_capacity_v2.py")],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == repo / "engine" / "provider_capacity_v2.py"
