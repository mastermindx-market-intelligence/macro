"""A14/A30 SNI copy-guard tests.

SNI-local DRAFT contract tests. They consume owner-supplied markdown
under research/single_name_intelligence/ and never mint issuer or
security ids (Stock Identity / Data OS owns those opaque strings).
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and
trade_authority stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path. The scanner is a lexical copy check.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
SNI_ROOT = REPO / "research" / "single_name_intelligence"
sys.path.insert(0, str(ACCEPTANCE))

from sni_copy_guard import (  # noqa: E402
    ALLOWLIST,
    Finding,
    check_text,
    is_allowlisted,
    refuse_nonfalse_authority,
    scan_paths,
)

# True lexical A30 collocations on sealed S1 residual REPORT dump lines.
# This lane does not edit those reports and does not allowlist them.
# A new violation still fails; a fix of a listed line forces this tuple
# to shrink. Expected empty once the reports drop the collocation.
KNOWN_FINDINGS: tuple[tuple[str, int, str, str], ...] = (
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 962, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 975, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 988, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1001, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1066, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1079, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1144, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1196, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1209, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1248, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1261, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1300, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1352, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1365, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1404, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1417, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1456, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual/REPORT.md", 1469, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md", 1186, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md", 1214, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
    ("research/single_name_intelligence/runs/s1_residual_v1_1/REPORT.md", 1631, "A30", "test: {'name': 'S0 pre-registered incremental-explanation criterion', 'sidedness': 'one-sided via the pre-registered rule delta_R2 > 0 AND CI lower bound > 0 (a"),
)


def _sni_md_paths() -> list[Path]:
    return sorted(p for p in SNI_ROOT.rglob("*.md") if p.is_file())


def _scan_tree() -> list[Finding]:
    return scan_paths(_sni_md_paths())


def _projected(findings: list[Finding], rule: str) -> list[tuple[str, int, str, str]]:
    out: list[tuple[str, int, str, str]] = []
    for finding in findings:
        if finding.rule != rule:
            continue
        if is_allowlisted(finding):
            continue
        out.append(
            (finding.path, finding.line, finding.rule, finding.sentence_excerpt)
        )
    return out


def test_cg_01_scan_covers_the_sni_tree() -> None:
    paths = _sni_md_paths()
    n = len(paths)
    print(f"SNI markdown files scanned: {n}", flush=True)
    assert n >= 40, n
    names = {p.name for p in paths}
    assert "SNI_U0_REFERENCE_JOURNEY_AND_WIRE_CONTRACT_DRAFT.md" in names
    review_dir = SNI_ROOT / "reviews"
    review_files = [p for p in paths if p.parent == review_dir]
    assert review_files, "reviews/ markdown must be included"


def test_cg_02_a14_no_flow_or_intent_labels() -> None:
    got = _projected(_scan_tree(), "A14")
    expected = [row for row in KNOWN_FINDINGS if row[2] == "A14"]
    assert got == expected


def test_cg_03_a30_no_forecast_success_on_failed_models() -> None:
    got = _projected(_scan_tree(), "A30")
    expected = [row for row in KNOWN_FINDINGS if row[2] == "A30"]
    assert got == list(expected)


def test_cg_04_allowlist_is_live_and_exact() -> None:
    findings = _scan_tree()
    assert isinstance(ALLOWLIST, tuple)
    for entry in ALLOWLIST:
        path, line, rule, substring, justification = entry
        assert justification and str(justification).strip(), entry
        abs_path = REPO / path
        assert abs_path.is_file(), path
        matches = [
            f
            for f in findings
            if f.path == path
            and f.line == line
            and f.rule == rule
            and substring in f.sentence_excerpt
        ]
        assert len(matches) == 1, (entry, matches)


@pytest.mark.parametrize(
    "text, rule",
    [
        ("Southbound holdings show smart money accumulating Tencent.", "A14"),
        ("CCASS data reveals net buying by whales.", "A14"),
        ("Options OI signals intent to buy.", "A14"),
        ("Short interest shows bears positioning for a drop.", "A14"),
        ("The NO-GO model still predicts returns.", "A30"),
        ("P03 was retired but outperforms the baseline.", "A30"),
        ("The failed variant has an edge.", "A30"),
        ("The DESCRIPTIVE_ONLY study proves forecast skill.", "A30"),
    ],
)
def test_cg_05_positive_controls(text: str, rule: str) -> None:
    findings = check_text(text, "synthetic.md")
    rules = [f.rule for f in findings]
    assert rule in rules, findings
    assert len(findings) >= 1


@pytest.mark.parametrize(
    "text",
    [
        "Holdings are not live flow or intent.",
        "Never describe a NO-GO model as having an edge.",
        'The draft said "smart money accumulating in southbound holdings" and was rejected.',
        # Word-boundary control: "works" is a substring of "workspace" and
        # "retired" is a failed-state term. The original sentence "The
        # workspace works for the retired protocol registry." still fires
        # A30 because "works" is a whole word there; that sentence was
        # replaced rather than weakening the rule.
        "The workspace for the retired protocol registry.",
        "Options / positioning | engine/options_*.py",
    ],
)
def test_cg_06_negative_controls(text: str) -> None:
    findings = check_text(text, "synthetic.md")
    assert findings == [], findings


def test_cg_07_guard_never_reads_outside_sni_md() -> None:
    outside = Path("/tmp/sni_copy_guard_outside.md")
    with pytest.raises(ValueError, match="outside"):
        scan_paths([outside])
    with pytest.raises(ValueError, match="outside"):
        scan_paths([REPO / "README.md"])
    with pytest.raises(ValueError):
        scan_paths([Path(__file__)])


def test_cg_08_findings_are_deterministic() -> None:
    first = _scan_tree()
    second = _scan_tree()
    assert first == second


def test_cg_authority_flags_stay_false() -> None:
    refuse_nonfalse_authority({"rank_authority": False})
    with pytest.raises(ValueError, match="rank_authority"):
        check_text("ok", "synthetic.md", rank_authority=True)
    with pytest.raises(ValueError, match="trade_authority"):
        scan_paths([], trade_authority=True)
