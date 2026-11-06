"""The capital-structure handoff receipt over the SHARDED source ledger.

``daily.yml`` stamps a receipt in ``collect`` and verifies it in the
``capital_structure`` job through ONE script, so the newline count and sha256 that
prove "the artifact that landed is tonight's ledger" are computed identically on
both sides and cover every continuation part
(DEC:CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY). These tests run the script the way
the workflow does: as a subprocess with ``GITHUB_OUTPUT`` set.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capital_structure_ledger_receipt.py"
TITLE = "::error title=capital-structure-handoff::"

PART1 = b'{"manifest_id":"manifest:cs:aaaa"}\n{"manifest_id":"manifest:cs:bbbb"}\n'
PART2 = b'{"manifest_id":"manifest:cs:cccc"}\n'
PART3 = b'{"manifest_id":"manifest:cs:dddd"}\n{"manifest_id":"manifest:cs:eeee"}\n'


def _run(args: list[str], tmp_path: Path) -> tuple[subprocess.CompletedProcess, dict[str, str]]:
    output = tmp_path / "github_output"
    env = {**os.environ, "GITHUB_OUTPUT": str(output)}
    done = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT), capture_output=True, text=True, env=env, check=False,
    )
    outputs: dict[str, str] = {}
    if output.exists():
        for line in output.read_text().splitlines():
            key, _sep, value = line.partition("=")
            outputs[key] = value
    return done, outputs


def _sharded_root(tmp_path: Path) -> tuple[Path, bytes]:
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    (root / "source_manifest.jsonl").write_bytes(PART1)
    (root / "source_manifest.part-0002.jsonl").write_bytes(PART2)
    (root / "source_manifest.part-0003.jsonl").write_bytes(PART3)
    (root / "source_manifest.part-0002.tmp.jsonl").write_bytes(b"{interrupted\n")
    (root / "telemetry.json").write_bytes(b"{}")
    return root, PART1 + PART2 + PART3


def _annotations_start_their_line(stdout: str) -> None:
    for line in stdout.splitlines():
        if "::" in line and ("::error" in line or "::warning" in line):
            assert line.startswith("::"), line


def test_stamp_describes_the_logical_ledger_across_every_part(tmp_path):
    root, logical = _sharded_root(tmp_path)
    done, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert outputs == {
        "sha256": hashlib.sha256(logical).hexdigest(),
        "rows": str(logical.count(b"\n")),
    }
    assert outputs["rows"] == "5"
    assert "capital-structure handoff stamped: 5 rows" in done.stdout
    assert "source_manifest.part-0003.jsonl" in done.stdout
    assert "tmp.jsonl" not in done.stdout, "a staged write is never a part"


def test_stamp_is_byte_for_byte_the_old_receipt_while_unsharded(tmp_path):
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    (root / "source_manifest.jsonl").write_bytes(PART1)
    done, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    # exactly `shasum -a 256` and `wc -l` over the one file
    assert outputs == {"sha256": hashlib.sha256(PART1).hexdigest(), "rows": "2"}


def test_stamp_warns_and_exits_zero_when_there_is_no_ledger(tmp_path):
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    done, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    assert done.returncode == 0
    assert outputs == {}, "no receipt may be stamped for an absent ledger"
    assert done.stdout.startswith("::warning::no "), done.stdout
    _annotations_start_their_line(done.stdout)


def test_stamp_stamps_nothing_for_a_corrupt_part_listing(tmp_path):
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    (root / "source_manifest.jsonl").write_bytes(PART1)
    (root / "source_manifest.part-0003.jsonl").write_bytes(PART3)  # 0002 is missing
    done, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    assert done.returncode == 1
    assert outputs == {}
    assert done.stdout.startswith("::warning title=capital-structure-handoff::")
    assert "not contiguous" in done.stdout
    _annotations_start_their_line(done.stdout)


def test_verify_accepts_the_receipt_the_stamp_produced(tmp_path):
    root, logical = _sharded_root(tmp_path)
    _stamp, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    done, _ = _run(
        ["verify", "--root", str(root), "--expect-sha256", outputs["sha256"],
         "--expect-rows", outputs["rows"]],
        tmp_path,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"capital-structure handoff verified: 5 rows, sha256 {outputs['sha256']}" in done.stdout


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: (root / "source_manifest.part-0003.jsonl").unlink(),
        lambda root: (root / "source_manifest.part-0002.jsonl").write_bytes(b'{"manifest_id":"x"}\n'),
        lambda root: (root / "source_manifest.part-0004.jsonl").write_bytes(PART2),
    ],
    ids=["dropped-part", "rewritten-part", "extra-part"],
)
def test_verify_rejects_a_tree_whose_parts_differ_from_the_receipt(tmp_path, mutate):
    root, _logical = _sharded_root(tmp_path)
    _stamp, outputs = _run(["stamp", "--root", str(root)], tmp_path)
    mutate(root)
    done, _ = _run(
        ["verify", "--root", str(root), "--expect-sha256", outputs["sha256"],
         "--expect-rows", outputs["rows"]],
        tmp_path,
    )
    assert done.returncode == 1
    assert done.stdout.startswith(TITLE + "ledger mismatch"), done.stdout
    assert "did not land ON TOP of the checkout" in done.stdout
    _annotations_start_their_line(done.stdout)


def test_verify_rejects_a_missing_receipt(tmp_path):
    root, _logical = _sharded_root(tmp_path)
    done, _ = _run(["verify", "--root", str(root), "--expect-sha256", "", "--expect-rows", ""], tmp_path)
    assert done.returncode == 1
    assert done.stdout.startswith(TITLE + "collect published no ledger receipt"), done.stdout


def test_verify_rejects_an_absent_ledger(tmp_path):
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    done, _ = _run(
        ["verify", "--root", str(root), "--expect-sha256", "f" * 64, "--expect-rows", "1"], tmp_path,
    )
    assert done.returncode == 1
    assert done.stdout.startswith(TITLE), done.stdout
    assert "is absent after the artifact download" in done.stdout


def test_verify_rejects_a_corrupt_part_listing(tmp_path):
    root = tmp_path / "data" / "capital_structure"
    root.mkdir(parents=True)
    (root / "source_manifest.part-0002.jsonl").write_bytes(PART2)  # no part 1
    done, _ = _run(
        ["verify", "--root", str(root), "--expect-sha256", "f" * 64, "--expect-rows", "1"], tmp_path,
    )
    assert done.returncode == 1
    assert done.stdout.startswith(TITLE), done.stdout
    assert "absent but continuation parts exist" in done.stdout
