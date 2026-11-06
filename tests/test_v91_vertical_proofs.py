"""Masterplan §9.1 vertical proofs: run each proof script and pin its verdicts.

Every ``research/news_intelligence_estate_20261021/v91_proofs/v<n>_<slug>.py`` is run
as a subprocess with PYTHONPATH at the tree, sockets refused, credential-shaped and
writer-arming environment variables removed, and a private ``--scratch`` directory as
its working directory. Its output must follow the V91 line format, and its verdicts must
equal the sibling ``.expected`` file exactly. A proven property that regresses, or a
property promoted without updating ``.expected``, fails this module.

The evidence text after each verdict is not pinned, so an unrelated edit that moves a
producer line does not fail here. It must be identical across two runs, and every
``path:line`` it cites outside ``data/`` and ``site/`` must name an existing tracked
file with at least that many lines.

A proof whose committed artifact (its ``REQUIRED_ARTIFACTS`` tuple) is not checked out,
as in a sparse worktree, is skipped rather than failed.

This module is byte-identical in every V91 pull request, so the seven vertical PRs can
merge in any order.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = ROOT / "research" / "news_intelligence_estate_20261021" / "v91_proofs"
PROOFS = sorted(PROOF_DIR.glob("v[1-7]_*.py"))

# The rung each proof reaches without a human (V91_VERTICAL_PROOF_READINESS.md, Summary).
# V6 reaches OFFLINE_FIXTURE for what exists offline; its signed-in step prints HUMAN_GATE.
BEST_RUNG = {
    "1": "COMMITTED_ARTIFACT",
    "2": "OFFLINE_FIXTURE",
    "3": "OFFLINE_FIXTURE",
    "4": "COMMITTED_ARTIFACT",
    "5": "OFFLINE_FIXTURE",
    "6": "OFFLINE_FIXTURE",
    "7": "OFFLINE_FIXTURE",
}
TIME_BUDGET_S = 60.0

LINE_RE = re.compile(
    r"^V(?P<v>[1-7]) P(?P<k>[1-9][0-9]?) "
    r"(?P<verdict>PROVEN|PARTIAL|ABSENT|HUMAN_GATE) (?P<evidence>\S.*)$"
)
SUMMARY_RE = re.compile(
    r"^V(?P<v>[1-7]) SUMMARY proven=(?P<proven>\d+) partial=(?P<partial>\d+) "
    r"absent=(?P<absent>\d+) human_gate=(?P<human_gate>\d+) rung=(?P<rung>[A-Z_]+)$"
)
CITE_RE = re.compile(
    r"(?<![\w/.-])((?:app|collectors|config|contracts|engine|lib|research|scripts|"
    r"templates|tests)/[\w./-]*\w\.\w+):(\d+)"
)
_SECRET_ENV = re.compile(r"(?i)(api_?key|token|secret|passw|credential|auth)")
_WRITER_ENV = ("COLLECT_LANE", "US_LANE")

# Runs the proof in-process after refusing every outbound socket.
_BOOTSTRAP = r"""
import runpy, socket, sys

def _refused(*_a, **_k):
    raise OSError("network disabled for V91 proofs")

socket.create_connection = _refused
socket.getaddrinfo = _refused
socket.socket.connect = _refused
socket.socket.connect_ex = _refused
proof = sys.argv[1]
sys.argv = [proof] + sys.argv[2:]
runpy.run_path(proof, run_name="__main__")
"""


def _required_artifacts(proof: Path) -> tuple[str, ...]:
    tree = ast.parse(proof.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "REQUIRED_ARTIFACTS" for t in node.targets
        ):
            value = ast.literal_eval(node.value)
            return tuple(str(v) for v in value)
    return ()


def _env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not _SECRET_ENV.search(k) and k not in _WRITER_ENV
    }
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TZ"] = "UTC"
    return env


def _run(proof: Path, scratch: Path) -> tuple[list[str], float]:
    scratch.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-c", _BOOTSTRAP, str(proof), "--scratch", str(scratch)],
        cwd=scratch,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=TIME_BUDGET_S * 2,
    )
    elapsed = time.monotonic() - started
    assert done.returncode == 0, (
        f"{proof.name} exited {done.returncode}\n--- stderr ---\n{done.stderr[-4000:]}"
    )
    return [line for line in done.stdout.splitlines() if line.strip()], elapsed


def _parse(lines: list[str], vertical: str) -> tuple[list[re.Match], re.Match]:
    assert lines, "proof printed nothing"
    *body, last = lines
    props = []
    for line in body:
        m = LINE_RE.match(line)
        assert m, f"not a V91 property line: {line!r}"
        assert m["v"] == vertical, f"line for another vertical: {line!r}"
        props.append(m)
    summary = SUMMARY_RE.match(last)
    assert summary, f"last line is not a V91 SUMMARY line: {last!r}"
    assert summary["v"] == vertical
    assert [int(m["k"]) for m in props] == list(range(1, len(props) + 1)), (
        "property lines must be numbered P1..Pn in order"
    )
    return props, summary


def test_every_proof_has_expected_verdicts() -> None:
    expected = sorted(PROOF_DIR.glob("v[1-7]_*.expected"))
    assert [p.stem for p in PROOFS] == [p.stem for p in expected]


@pytest.mark.parametrize("proof", PROOFS, ids=[p.stem for p in PROOFS])
def test_vertical_proof(proof: Path, tmp_path: Path) -> None:
    vertical = proof.name[1]
    missing = [a for a in _required_artifacts(proof) if not (ROOT / a).is_file()]
    if missing:
        pytest.skip(f"committed artifact not checked out: {missing[0]}")

    first, elapsed = _run(proof, tmp_path / "run1")
    assert elapsed < TIME_BUDGET_S, f"{proof.name} took {elapsed:.1f}s"
    second, _ = _run(proof, tmp_path / "run2")
    assert first == second, "proof output is not deterministic"

    props, summary = _parse(first, vertical)

    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for m in props:
        tally[m["verdict"]] += 1
    assert int(summary["proven"]) == tally["PROVEN"]
    assert int(summary["partial"]) == tally["PARTIAL"]
    assert int(summary["absent"]) == tally["ABSENT"]
    assert int(summary["human_gate"]) == tally["HUMAN_GATE"]
    assert summary["rung"] == BEST_RUNG[vertical]

    for m in props:
        for path, line in CITE_RE.findall(m["evidence"]):
            target = ROOT / path
            assert target.is_file(), f"V{vertical} P{m['k']} cites a missing file {path}"
            with target.open("rb") as handle:
                n_lines = sum(1 for _ in handle)
            assert 1 <= int(line) <= n_lines, (
                f"V{vertical} P{m['k']} cites {path}:{line} beyond its {n_lines} lines"
            )

    expected_path = proof.with_suffix(".expected")
    expected = [
        line
        for line in expected_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    observed = [f"V{m['v']} P{m['k']} {m['verdict']}" for m in props] + [first[-1]]
    assert observed == expected
