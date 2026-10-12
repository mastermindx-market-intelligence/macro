"""S2 seal integrity (E13): the runner recomputes every membership_sha256 and
the prereg digest and exits non-zero on ANY mismatch with the seal — a
tampered manifest, a tampered membership table or a drifted spec must all be
refused before any outcome is computed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_loaders import GitBlobLoader  # noqa: E402
from run_s2 import verify_seal  # noqa: E402
from s2_state import compute_state  # noqa: E402

INPUT_REF = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"
COMMITTED_SEAL = (ROOT / "research" / "single_name_intelligence" / "runs"
                  / "s2_event_response")


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


@pytest.fixture(scope="module")
def state():
    _ensure_input_ref()
    loader = GitBlobLoader(ROOT, INPUT_REF)
    return compute_state(loader)


def test_build_seal_runs_standalone_from_repo_root() -> None:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    builder = ROOT / "research" / "single_name_intelligence" / "event_response" / "build_seal.py"
    r = subprocess.run([sys.executable, str(builder), "--help"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "--out-dir" in r.stdout


def test_committed_seal_verifies(state) -> None:
    verify_seal(COMMITTED_SEAL, state)  # must not raise


def test_tampered_manifest_is_refused(state, tmp_path: Path) -> None:
    seal_dir = tmp_path / "seal"
    shutil.copytree(COMMITTED_SEAL, seal_dir)
    manifest = seal_dir / "manifests" / "P04_h5.jsonl"
    lines = manifest.read_text(encoding="utf-8").splitlines(keepends=True)
    obj = json.loads(lines[0])
    obj["cluster_key"] = "1999-01-01"  # any byte-level drift
    lines[0] = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False) + "\n"
    manifest.write_text("".join(lines), encoding="utf-8")
    with pytest.raises(SystemExit, match="manifest bytes differ"):
        verify_seal(seal_dir, state)


def test_tampered_membership_table_is_refused(state, tmp_path: Path) -> None:
    seal_dir = tmp_path / "seal"
    shutil.copytree(COMMITTED_SEAL, seal_dir)
    seal_path = seal_dir / "SEAL_AND_BUDGET.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    for row in seal["membership_table"]:
        if row["protocol_id"] == "P04" and row["split"] == "TUNE":
            row["count"] = 99
    seal_path.write_text(json.dumps(seal, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    with pytest.raises(SystemExit, match="membership table"):
        verify_seal(seal_dir, state)


def test_tampered_prereg_digest_is_refused(state, tmp_path: Path) -> None:
    seal_dir = tmp_path / "seal"
    shutil.copytree(COMMITTED_SEAL, seal_dir)
    seal_path = seal_dir / "SEAL_AND_BUDGET.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["prereg_digest_sha256"] = "0" * 64
    seal_path.write_text(json.dumps(seal, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    with pytest.raises(SystemExit, match="prereg digest"):
        verify_seal(seal_dir, state)


def test_missing_seal_is_refused(state, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="seal not found"):
        verify_seal(tmp_path / "nope", state)
