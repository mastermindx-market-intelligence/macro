"""M6A killing tests for run_s2.py S2 CLI functions.

SNI-local DRAFT contract tests for the M6A mutation sweep of
`event_response/run_s2.py` functions `main`, `run_check`, `refuse_data_path`,
and `_fmt` (the 2026-10-13 coverage census marked these as UNTESTED).

Each test_m6a_run_s2_<function>_<n> docstring names one non-equivalent
mutant from the 2026-10-14 sweep (seed 20261014) that survived the
importer suite.

Authority flags stay false everywhere: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority, trade_authority.
Identity ids remain caller-supplied opaque strings. No issuer or security
identifiers are minted. Fixtures are synthetic. Residuals and event-study
numbers are descriptive, never causal, never a news-impact claim (A24).
An unestimable family ABSTAINS (A25).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

import run_s2  # noqa: E402
from run_s2 import (  # noqa: E402
    _fmt,
    main,
    refuse_data_path,
    run_check,
)


# ---------------------------------------------------------------------------
# main — required=True for --out-dir (L1092)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_1(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1092, required=True -> False (--out-dir argparse required)."""
    # When --out-dir is missing, the original required=True causes argparse
    # to exit 2. With required=False, args.out_dir is None, and main()
    # calls Path(None), which raises TypeError — not SystemExit(2).
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
        "--repo-root", str(tmp_path),
    ])
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 2


# ---------------------------------------------------------------------------
# main — required=True for --trial-ledger-path (L1093)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_2(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1093, required=True -> False (--trial-ledger-path argparse required)."""
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(tmp_path / "o"),
        "--repo-root", str(tmp_path),
    ])
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 2


# ---------------------------------------------------------------------------
# main — return 2 -> return None (L1105, return path)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_3(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1105, return 2 -> return None (git rev-parse failure exit code)."""
    # Simulate `git rev-parse` failing by patching subprocess.run to return
    # a non-zero exit. The original returns 2; the mutant returns None.
    def _fake_rev_parse(*_a, **_k):
        return subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

    def _fake_run(cmd, *a, **k):
        if isinstance(cmd, list) and "rev-parse" in cmd:
            return _fake_rev_parse()
        return subprocess.run(cmd, *a, **k)

    monkeypatch.setattr(run_s2.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(tmp_path / "o"),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
    ])
    rc = main()
    assert rc == 2


# ---------------------------------------------------------------------------
# main — 2 -> 3 (L1105, exit code value)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_4(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1105, 2 -> 3 (git rev-parse failure exit code literal)."""

    def _fake_rev_parse(*_a, **_k):
        return subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

    def _fake_run(cmd, *a, **k):
        if isinstance(cmd, list) and "rev-parse" in cmd:
            return _fake_rev_parse()
        return subprocess.run(cmd, *a, **k)

    monkeypatch.setattr(run_s2.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(tmp_path / "o"),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
    ])
    rc = main()
    assert rc != 3


# ---------------------------------------------------------------------------
# main — exist_ok=True -> False (L1117)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_5(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1117, exist_ok=True -> False (out_dir.mkdir pre-existing dir)."""
    out_dir = tmp_path / "o"
    out_dir.mkdir()  # pre-existing — original exist_ok=True would no-op
    monkeypatch.setattr(run_s2, "generate_outputs", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(out_dir),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
        "--repo-root", str(tmp_path),
    ])
    rc = main()
    assert rc == 0


# ---------------------------------------------------------------------------
# main — parents=True -> False (L1117, the other True constant on the line)
# ---------------------------------------------------------------------------


def test_m6a_run_s2_main_6(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1117, parents=True -> False (mkdir needs the parent path).

    The other True constant on line 1117 is `parents=True`. With a
    pre-existing out_dir the mutation is silent (the parent exists), so
    the previous test would not catch it. A nested out_dir whose
    intermediate parent does not yet exist exercises the parents
    branch: `parents=False` raises FileNotFoundError.
    """
    # out_dir's parent does not exist yet — only the parent's parent does.
    out_dir = tmp_path / "newparent" / "o"
    assert not out_dir.parent.exists()
    monkeypatch.setattr(run_s2, "generate_outputs", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(out_dir),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
        "--repo-root", str(tmp_path),
    ])
    rc = main()
    assert rc == 0


# ---------------------------------------------------------------------------
# run_check — sort_keys=True (L1078, both True constants)
# ---------------------------------------------------------------------------


def _write_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_m6a_run_s2_run_check_1(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1078, sort_keys=True -> False (canonical comparison off).

    Two ledgers with the same logical content but different key insertion
    orders. With sort_keys=True (original) the json.dumps canonical form
    matches, run_check returns 0. With sort_keys=False (mutant) the raw
    byte-form differs and run_check returns 1.
    """
    seal = tmp_path / "seal"
    (seal / "results").mkdir(parents=True)
    (seal / "observations").mkdir(parents=True)
    # minimal files for the run_check path
    for rel in ("REPORT.md", "LANE_MANIFEST.json", "VERSION_RECORD.json",
                "results/P04.json", "results/P05.json", "results/P06.json",
                "observations/episodes.jsonl"):
        p = seal / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".json"):
            p.write_text(json.dumps({"synthetic": rel}) + "\n", encoding="utf-8")
        elif rel.endswith(".jsonl"):
            p.write_text('{"synthetic": true}\n', encoding="utf-8")
        else:
            p.write_text("synthetic-report\n", encoding="utf-8")

    # seal ledger: keys in order A, B
    _write_ledger(seal / "trial_ledger.jsonl",
                  {"ts": "2024-01-02T00:00:00+00:00", "a": 1, "b": 2})

    def _gen(_repo, _ref, out_dir, ledger_path, _seal):
        # copy REPORT/MANIFEST/etc verbatim
        for rel in ("REPORT.md", "LANE_MANIFEST.json", "VERSION_RECORD.json",
                    "results/P04.json", "results/P05.json", "results/P06.json",
                    "observations/episodes.jsonl"):
            src = seal / rel
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        # tmp ledger: same content, different key insertion order
        _write_ledger(ledger_path,
                      {"ts": "2024-01-02T00:00:00+00:00", "b": 2, "a": 1})

    monkeypatch.setattr(run_s2, "generate_outputs", _gen)
    rc = run_check(tmp_path, "synthetic-ref", seal)
    # With sort_keys=True: la and lb canonicalize to same string -> 0
    # With sort_keys=False: raw forms differ -> 1
    assert rc == 0


def test_m6a_run_s2_run_check_2(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1078, sort_keys=True -> False (other side, lb).

    Mirror of test_m6a_run_s2_run_check_1: the seal row is in B,A
    insertion order and the tmp row is in A,B insertion order. With
    sort_keys=True (original) both serialise to the same canonical form
    and run_check returns 0. With sort_keys=False (mutant) only one side
    canonicalises, so the comparison differs and run_check returns 1.
    """
    seal = tmp_path / "seal"
    (seal / "results").mkdir(parents=True)
    (seal / "observations").mkdir(parents=True)
    for rel in ("REPORT.md", "LANE_MANIFEST.json", "VERSION_RECORD.json",
                "results/P04.json", "results/P05.json", "results/P06.json",
                "observations/episodes.jsonl"):
        p = seal / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".json"):
            p.write_text(json.dumps({"synthetic": rel}) + "\n", encoding="utf-8")
        elif rel.endswith(".jsonl"):
            p.write_text('{"synthetic": true}\n', encoding="utf-8")
        else:
            p.write_text("synthetic-report\n", encoding="utf-8")

    # seal ledger: keys in order B, A
    _write_ledger(seal / "trial_ledger.jsonl",
                  {"ts": "2024-01-02T00:00:00+00:00", "b": 2, "a": 1})

    def _gen(_repo, _ref, out_dir, ledger_path, _seal):
        for rel in ("REPORT.md", "LANE_MANIFEST.json", "VERSION_RECORD.json",
                    "results/P04.json", "results/P05.json", "results/P06.json",
                    "observations/episodes.jsonl"):
            src = seal / rel
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        # tmp ledger: same content, different key insertion order
        _write_ledger(ledger_path,
                      {"ts": "2024-01-02T00:00:00+00:00", "a": 1, "b": 2})

    monkeypatch.setattr(run_s2, "generate_outputs", _gen)
    rc = run_check(tmp_path, "synthetic-ref", seal)
    assert rc == 0
