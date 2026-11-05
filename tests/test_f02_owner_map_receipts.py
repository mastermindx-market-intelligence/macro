"""Pin the F02 owner-map receipts that PR #6913's Opus review found false.

These are record-text + live-measurement assertions, not schema tautologies.
A receipt that names a warning count, a nav line, or a ledger row number must
match the tree — or the number must be absent.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HANDOFF = REPO / "agentos" / "handoffs" / "MARKET-ONTOLOGY-F02-POLICY-GEO-2026-09-05.md"
DEC = REPO / "agentos" / "decisions" / "DEC-F02-POLICY-GEO-OWNER-MAP.md"
MEMO = (
    REPO
    / "research"
    / "market_intelligence_productization"
    / "MARKET_ONTOLOGY_F02_OWNER_SOURCE_RIGHTS_MAP_2026-09-05.md"
)
LEDGER = (
    REPO
    / "research"
    / "market_intelligence_productization"
    / "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
)
NAV = REPO / "templates" / "_navlinks.html.j2"
CLI = REPO / "scripts" / "agentos.py"
STORE = REPO / "agentos"

_SUMMARY = re.compile(
    r"agentos: (\d+) records \(.*?\) — (\d+) error\(s\), (\d+) warning\(s\)"
)
_SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
_PAID_IDS = ("MO-PAID-006", "MO-PAID-023", "MO-PAID-034")

pytestmark = [
    pytest.mark.skipif(
        not STORE.exists(),
        reason="agentos/ outside this sparse checkout — run: git sparse-checkout add agentos",
    ),
    pytest.mark.skipif(not HANDOFF.is_file(), reason="F02 handoff missing"),
    pytest.mark.skipif(not MEMO.is_file(), reason="F02 owner-map memo missing"),
]


def _summary_from(proc: subprocess.CompletedProcess[str]) -> tuple[int, int, int]:
    blob = f"{proc.stdout}\n{proc.stderr}"
    matches = _SUMMARY.findall(blob)
    assert matches, f"no agentos summary in validate output:\n{blob[-800:]}"
    records, errors, warnings = (int(x) for x in matches[-1])
    return records, errors, warnings


def test_major1_handoff_drops_absolute_warning_count_and_delta_is_zero(
    tmp_path: Path,
) -> None:
    """MAJOR 1: no '56 warnings' durable, and the two records add no findings."""
    text = HANDOFF.read_text(encoding="utf-8")
    assert "56 warnings" not in text
    assert re.search(r"\b56\s+warning", text) is None
    assert "zero new errors" in text
    assert "zero new warnings" in text
    assert "checkout-" in text and "dependent" in text

    work = tmp_path / "agentos"
    shutil.copytree(STORE, work)
    env = dict(os.environ)
    with_files = subprocess.run(
        [sys.executable, str(CLI), "validate", "--root", str(work)],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=env,
    )
    (work / "handoffs" / HANDOFF.name).unlink()
    (work / "decisions" / DEC.name).unlink()
    without_files = subprocess.run(
        [sys.executable, str(CLI), "validate", "--root", str(work)],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=env,
    )

    assert with_files.returncode == 0, with_files.stderr[-400:]
    assert without_files.returncode == 0, without_files.stderr[-400:]
    rec_w, err_w, warn_w = _summary_from(with_files)
    rec_wo, err_wo, warn_wo = _summary_from(without_files)
    assert err_w == 0
    assert err_wo == 0
    assert warn_w == warn_wo
    assert rec_w == rec_wo + 2
    assert rec_w >= 2


def test_major2_committed_records_do_not_name_parent_as_head() -> None:
    """MAJOR 2 (committed half): parent d24cba5172c7 is not claimed as this head."""
    for path in (HANDOFF, DEC, MEMO):
        text = path.read_text(encoding="utf-8")
        assert "d24cba5172c7" not in text, f"{path.name} still names the parent as head"


def test_minor3_nav_coordinate_matches_template() -> None:
    """MINOR 3: the memo names the baskets_intl nav row by content, not by line.

    The receipt used to pin `_navlinks.html.j2:194` as the row and 195 as its
    closing `</div>`; a later nav edit on main moved those rows and the pin went
    stale. The durable receipt is the content: the memo pins no line number of
    its own against this tree, and the live template carries exactly one
    `baskets_intl.html` row whose nav group closes with a `</div>`.
    """
    memo = MEMO.read_text(encoding="utf-8")
    assert "195 is an unrelated existing nav row, `baskets_intl.html`" not in memo
    assert (
        re.search(r"`templates/_navlinks\.html\.j2:\d+`", memo) is None
    ), "memo must not pin a _navlinks.html.j2 line number against this tree"
    assert (
        "`templates/_navlinks.html.j2` carries exactly one `baskets_intl.html` row"
        in memo
    ), "memo §2.5 must name the baskets_intl row by content"
    assert "the receipt is by content, not by line number" in memo

    lines = NAV.read_text(encoding="utf-8").splitlines()
    rows = [i for i, line in enumerate(lines) if "baskets_intl.html" in line]
    assert len(rows) == 1, f"expected exactly one baskets_intl.html row, got {rows}"
    assert lines[rows[0]].lstrip().startswith("<a href="), lines[rows[0]].strip()

    for line in lines[rows[0] + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("<a "):
            continue
        assert stripped == "</div>", (
            f"the baskets_intl.html row's nav group must close with </div>, "
            f"got: {stripped!r}"
        )
        break
    else:  # pragma: no cover - the template always closes its groups
        pytest.fail("no closing </div> after the baskets_intl.html row")


def test_minor4_ledger_cited_by_stable_id_not_row_number() -> None:
    """MINOR 4: §1 names MO-PAID-* IDs and does not pin csv:16,19,20."""
    memo = MEMO.read_text(encoding="utf-8")
    purpose = memo.split("## 2.", 1)[0]
    assert "csv:16,19,20" not in purpose
    assert not re.search(
        r"F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02\.csv:\d",
        purpose,
    )
    for paid_id in _PAID_IDS:
        assert paid_id in purpose

    ledger = LEDGER.read_text(encoding="utf-8")
    found = {paid_id: False for paid_id in _PAID_IDS}
    for raw in ledger.splitlines():
        key = raw.split(",", 1)[0]
        if key in found:
            found[key] = True
    assert found == {paid_id: True for paid_id in _PAID_IDS}


def test_minor6_verified_at_names_a_commit_sha() -> None:
    """MINOR 6: Verified-at names a hex sha, not 'origin/main (this branch's base)'."""
    header = MEMO.read_text(encoding="utf-8").split("## 1.", 1)[0]
    verified_lines = [ln for ln in header.splitlines() if "Verified at" in ln]
    assert verified_lines, "memo header must carry a Verified at line"
    verified = verified_lines[0]
    shas = _SHA.findall(verified)
    assert shas, f"Verified at must name a commit sha, got: {verified!r}"
    assert "3b2c85da45fb" in shas or "3b2c85da45fb" in verified
    assert "16b3734c9d87" in verified
    assert verified != "**Verified at:** macro `origin/main` (this branch's base)."
    assert "origin/main` (this branch's base)" not in verified
