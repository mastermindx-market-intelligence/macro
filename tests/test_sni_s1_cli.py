"""test_sni_s1_cli.py — missing --trial-ledger-path fails; a path under data/
is refused (exit 2); the seal-mismatch path exits non-zero."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

import pytest  # noqa: E402

import run_s1  # noqa: E402
from s1_prereg import RUNS_REL  # noqa: E402
from s1_synth import synth_frames, write_synthetic_repo  # noqa: E402


def test_missing_trial_ledger_path_fails():
    with pytest.raises(SystemExit) as e:
        run_s1.parse_args(["--input-ref", "X", "--out-dir", "Y"])
    assert e.value.code == 2


def test_no_default_for_trial_ledger_path():
    args = run_s1.parse_args(["--input-ref", "X", "--out-dir", "Y",
                              "--trial-ledger-path", "L"])
    assert args.trial_ledger_path == "L"


def test_ledger_path_under_data_is_refused(tmp_path):
    rc = run_s1.main(["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
                      "--out-dir", str(tmp_path / "out"),
                      "--trial-ledger-path", "data/trial_ledger.jsonl"],
                     store=object())
    assert rc == 2


def test_absolute_ledger_path_under_data_is_refused(tmp_path):
    rc = run_s1.main(["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
                      "--out-dir", str(tmp_path / "out"),
                      "--trial-ledger-path", str(tmp_path / "data" / "t.jsonl")],
                     store=object())
    assert rc == 2


def test_missing_seal_file_exits_nonzero(tmp_path):
    frames = synth_frames()
    store = write_synthetic_repo(tmp_path / "seed", frames)
    rc = run_s1.main(["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path / "empty"),
                      "--out-dir", str(tmp_path / "out"),
                      "--trial-ledger-path", str(tmp_path / "t.jsonl")], store=store)
    assert rc == 3


def test_seal_digest_mismatch_exits_nonzero(tmp_path):
    frames = synth_frames()
    store = write_synthetic_repo(tmp_path, frames)
    seal = tmp_path / RUNS_REL / "SEAL_AND_BUDGET.json"
    import json
    d = json.loads(seal.read_text("utf-8"))
    d["prereg_digest_sha256"] = "0" * 64
    seal.write_text(run_s1.canon(d) + "\n", encoding="utf-8")
    rc = run_s1.main(["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
                      "--out-dir", str(tmp_path / "out"),
                      "--trial-ledger-path", str(tmp_path / "t.jsonl")], store=store)
    assert rc == 3
