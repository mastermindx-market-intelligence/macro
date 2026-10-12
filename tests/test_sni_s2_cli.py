"""S2 CLI contract (E11/E13): --trial-ledger-path is REQUIRED with no default;
a path resolving inside <repo>/data/ is refused with exit 2; --check is wired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNNER = (ROOT / "research" / "single_name_intelligence" / "event_response"
          / "run_s2.py")
INPUT_REF = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"


def _ensure_input_ref() -> None:
    """Depth-1 CI checkouts lack BASE: one bounded fetch, else skip (never ERROR)."""
    def present() -> bool:
        return subprocess.run(["git", "cat-file", "-e", f"{INPUT_REF}^{{commit}}"],
                              cwd=ROOT, capture_output=True).returncode == 0
    if present():
        return
    try:
        subprocess.run(["git", "fetch", "--no-tags", "--depth=1", "origin", INPUT_REF],
                       cwd=ROOT, capture_output=True, timeout=90)
    except Exception:
        pass
    if not present():
        pytest.skip("input ref 5ef7a7f39f99 not present in this checkout (depth-1 CI)")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--input-ref", INPUT_REF, *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def test_missing_trial_ledger_path_fails(tmp_path: Path) -> None:
    proc = _run("--out-dir", str(tmp_path / "o"), "--repo-root", str(ROOT))
    assert proc.returncode != 0
    assert "trial-ledger-path" in proc.stderr


def test_data_path_is_refused_with_exit_2(tmp_path: Path) -> None:
    ledger = ROOT / "data" / "trial_ledger.jsonl"
    proc = _run("--out-dir", str(tmp_path / "o"),
                "--trial-ledger-path", str(ledger),
                "--repo-root", str(ROOT))
    assert proc.returncode == 2, proc.stderr
    assert "REFUSED" in proc.stderr
    # nothing was written anywhere
    assert not (tmp_path / "o").exists() or not any((tmp_path / "o").iterdir())


def test_data_relative_path_is_refused_too(tmp_path: Path) -> None:
    proc = _run("--out-dir", str(tmp_path / "o"),
                "--trial-ledger-path", "data/trial_ledger.jsonl",
                "--repo-root", str(ROOT))
    assert proc.returncode == 2, proc.stderr


def test_run_local_ledger_outside_data_is_accepted(tmp_path: Path) -> None:
    """A tmp_path ledger (never data/) runs the full pipeline against the
    committed seal and produces the evidence files at the EXACT
    --trial-ledger-path given."""
    _ensure_input_ref()
    out = tmp_path / "o"
    ledger = tmp_path / "trial_ledger.jsonl"
    proc = _run("--out-dir", str(out), "--trial-ledger-path", str(ledger),
                "--repo-root", str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    for rel in ("REPORT.md", "LANE_MANIFEST.json", "results/P04.json",
                "results/P05.json", "results/P06.json",
                "observations/episodes.jsonl"):
        assert (out / rel).exists(), rel
    assert ledger.exists(), "the ledger must be written at the given path"
