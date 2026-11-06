"""Tests for scripts/skew_accrual_precheck.py — the W2-1b --accrue detector.

This helper is the BLOCKER-1 fix for the skew-accrual lane: it gates the
runner against silently running main() on a pre-W2-1b tree (where
--accrue is dropped by the no-argparse call site, and main() writes
site/options_skew/latest.json — racing the render-host side that W2-1b
pinned to legacy). All tests use tmp_path fixtures (no real repo, no
network, no W2-1b branch dependency).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRECHECK = ROOT / "scripts" / "skew_accrual_precheck.py"


def _import_precheck():
    """Import scripts/skew_accrual_precheck as a module under a unique name."""
    spec = importlib.util.spec_from_file_location(
        "skew_accrual_precheck_under_test", PRECHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_build_options_skew(repo: Path, body: str) -> Path:
    """Write a synthetic scripts/build_options_skew.py and return the path."""
    p = repo / "scripts" / "build_options_skew.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ── behavioural unit tests ───────────────────────────────────────────────── #


def test_check_returns_ok_when_accrue_token_in_source(tmp_path):
    """W2-1b branch shape: argparse.add_argument('--accrue', ...) — exit 0."""
    mod = _import_precheck()
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""W2-1b shape."""
import argparse

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accrue", action="store_true")
    ap.add_argument("--emit", action="store_true")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
''')
    code, info = mod.check(repo)
    assert code == mod.EXIT_OK
    assert "--accrue" in info["reason"]
    assert info["repo"] == str(repo)


def test_check_returns_flag_missing_when_no_accrue_token(tmp_path):
    """Pre-W2-1b shape: NO --accrue anywhere in source → exit 4.

    This is the BLOCKER-1 fix: the runner MUST detect the missing flag
    BEFORE running --accrue, so a pre-W2-1b tree fails loud with the
    named reason instead of silently running main() and writing
    site/options_skew/latest.json.
    """
    mod = _import_precheck()
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""No argparse, no --accrue — pre-W2-1b."""
import json, logging
from engine import options_skew as S

def main() -> int:
    added = S.snapshot()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
''')
    code, info = mod.check(repo)
    assert code == mod.EXIT_FLAG_MISSING
    assert "W2-1b" in info["reason"]
    assert "race the render-host side" in info["reason"]


def test_check_returns_flag_missing_when_script_missing(tmp_path):
    """No scripts/build_options_skew.py in repo → exit 4 (cannot read source)."""
    mod = _import_precheck()
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    code, info = mod.check(repo)
    assert code == mod.EXIT_FLAG_MISSING
    assert info["read_reason"] == "missing_file"


def test_check_treats_docstring_reference_as_missing(tmp_path):
    """A docstring that mentions --accrue is NOT a positive match.

    The precheck anchors on the string-literal token `'--accrue'` or
    `"--accrue"`; a bare prose mention in a docstring does not count.
    This is the regex's load-bearing property — it would otherwise
    false-positive on a future revert where the docstring outlives the
    argparse declaration.
    """
    mod = _import_precheck()
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""W2-1b used to ship --accrue but was reverted."""
def main() -> int:
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
''')
    code, _ = mod.check(repo)
    assert code == mod.EXIT_FLAG_MISSING


def test_check_accepts_single_quoted_accrue_token(tmp_path):
    """The argparse-equivalent spelling `add_argument('--accrue', ...)`
    also matches — covers implementations that prefer single quotes."""
    mod = _import_precheck()
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""Single-quoted variant."""
import argparse
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--accrue', action='store_true')
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
''')
    code, _ = mod.check(repo)
    assert code == mod.EXIT_OK


# ── CLI subprocess surface ────────────────────────────────────────────────── #


def test_main_prints_status_word_on_stdout(tmp_path):
    """The runner reads stdout for the status word; verify the shape."""
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""Pre-W2-1b shape."""
def main():
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
''')
    rc = subprocess.run(
        [sys.executable, str(PRECHECK), "--repo", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == 4
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "FLAG_MISSING"
    # The named reason lands on stderr so the runner can log it
    # line-by-line without polluting the status word capture.
    assert "W2-1b" in rc.stderr


def test_main_exit_code_is_part_of_contract(tmp_path):
    """Exit codes are load-bearing — the runner's precheck step reads them."""
    mod = _import_precheck()
    repo = tmp_path / "repo"
    _write_build_options_skew(repo, '''"""W2-1b shape."""
import argparse
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accrue", action="store_true")
    ap.add_argument("--emit", action="store_true")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
''')
    rc = subprocess.run(
        [sys.executable, str(PRECHECK), "--repo", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert rc.returncode == mod.EXIT_OK
    first = next((l for l in rc.stdout.splitlines() if l.strip()), "")
    assert first == "OK"