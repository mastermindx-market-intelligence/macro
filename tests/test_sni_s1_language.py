"""test_sni_s1_language.py — the A24 language rule and the "validated" ban.

Scans (1) every lane module (never vacuous) and (2) the committed evidence
tree runs/s1_residual (REPORT.md, results/, observations/, LANE_MANIFEST.json)
once the evidence run exists.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))

import pytest  # noqa: E402

BANNED = ["impact", "caused", "because of", "driven by", "due to",
          "reaction to the news", "predicts", "abnormal because", "validated"]

RESIDUAL = REPO / "research/single_name_intelligence/residual"
RUNS = REPO / "research/single_name_intelligence/runs/s1_residual"


def _hits(text: str) -> list:
    low = text.lower()
    return [tok for tok in BANNED if tok in low]


def test_lane_modules_are_clean():
    offenders = []
    for py in sorted(RESIDUAL.glob("*.py")):
        found = _hits(py.read_text("utf-8"))
        if found:
            offenders.append((py.name, found))
    assert offenders == [], offenders


def test_committed_evidence_is_clean():
    targets = []
    if (RUNS / "REPORT.md").exists():
        targets.append(RUNS / "REPORT.md")
    results = RUNS / "results"
    if results.exists():
        targets.extend(sorted(results.glob("*.json")))
    manifest = RUNS / "LANE_MANIFEST.json"
    if manifest.exists():
        targets.append(manifest)
    if not targets:
        pytest.fail("committed evidence tree is missing — run the evidence pass "
                    "(run_s1.py into runs/s1_residual) before this check can bind")
    offenders = []
    for t in targets:
        found = _hits(t.read_text("utf-8"))
        if found:
            offenders.append((t.name, found))
    assert offenders == [], offenders
