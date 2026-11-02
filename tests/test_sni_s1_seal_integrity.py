"""test_sni_s1_seal_integrity.py — a tampered manifest (or membership table, or
prereg digest) makes the runner exit non-zero before anything is computed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

import pytest  # noqa: E402

import run_s1  # noqa: E402
from s1_prereg import RUNS_REL  # noqa: E402
from s1_synth import synth_frames, write_synthetic_repo  # noqa: E402


def _setup(tmp_path):
    frames = synth_frames()
    return write_synthetic_repo(tmp_path, frames)


def _run(tmp_path, store):
    return run_s1.main(["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
                        "--out-dir", str(tmp_path / "out"),
                        "--trial-ledger-path", str(tmp_path / "t.jsonl")], store=store)


def test_tampered_manifest_bytes_exit_nonzero(tmp_path):
    store = _setup(tmp_path)
    m = tmp_path / RUNS_REL / "manifests" / "P01_adr_baba_5.jsonl"
    lines = m.read_text("utf-8").splitlines()
    row = __import__("json").loads(lines[0])
    row["split"] = "TUNE"                       # relabel a sealed unit
    lines[0] = run_s1.canon(row)
    m.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _run(tmp_path, store) == 3


def test_tampered_membership_count_exits_nonzero(tmp_path):
    store = _setup(tmp_path)
    seal_path = tmp_path / RUNS_REL / "SEAL_AND_BUDGET.json"
    import json
    d = json.loads(seal_path.read_text("utf-8"))
    d["membership_table"][0]["count"] += 1
    seal_path.write_text(run_s1.canon(d) + "\n", encoding="utf-8")
    assert _run(tmp_path, store) == 3


def test_deleted_manifest_exits_nonzero(tmp_path):
    store = _setup(tmp_path)
    (tmp_path / RUNS_REL / "manifests" / "P02_hkd_0700_21.jsonl").unlink()
    assert _run(tmp_path, store) == 3


def test_wrong_input_ref_exits_nonzero(tmp_path):
    store = _setup(tmp_path)
    store.input_ref = "OTHER-REF"          # the seal was cut for SYNTHETIC
    assert run_s1.main(["--input-ref", "OTHER-REF", "--repo-root", str(tmp_path),
                        "--out-dir", str(tmp_path / "out"),
                        "--trial-ledger-path", str(tmp_path / "t.jsonl")],
                       store=store) == 3


def test_intact_tree_passes_verification(tmp_path):
    store = _setup(tmp_path)
    rc = _run(tmp_path, store)
    assert rc == 0
    assert (tmp_path / "out" / "REPORT.md").exists()
