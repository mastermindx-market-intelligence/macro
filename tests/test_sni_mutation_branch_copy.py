"""Killing tests for MUT3B survivors in ticker_branch_scan and sni_copy_guard.

SNI-local DRAFT contract tests. Fixtures are synthetic. Authority flags stay
false. This file does not mint issuer or security identifiers and does not
feed a rank, gate, size, signal, escalation, or trade path.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
SNI_ROOT = REPO / "research" / "single_name_intelligence"
sys.path.insert(0, str(ACCEPTANCE))

import sni_copy_guard as cg  # noqa: E402
import ticker_branch_scan as tbs  # noqa: E402
from sni_copy_guard import (  # noqa: E402
    AllowlistEntry,
    Finding,
    _first_match,
    check_text,
    is_allowlisted,
    scan_paths,
    unallowlisted,
)


# ---------------------------------------------------------------------------
# ticker_branch_scan survivors
# ---------------------------------------------------------------------------


def test_mut3b_ticker_branch_scan_module_1() -> None:
    """ticker_branch_scan.py:68, False -> True (rank_authority)."""
    assert tbs.AUTHORITY_FLAGS["rank_authority"] is False
    for name, value in tbs.AUTHORITY_FLAGS.items():
        assert value is False, name
    returned = tbs.refuse_authority_override()
    assert returned["rank_authority"] is False


def test_mut3b_ticker_branch_scan__dict_literal_1() -> None:
    """ticker_branch_scan.py:434, node.func.id == 'dict' -> !=."""
    src = (
        '_TABLE = dict({"GOOGL": 1.0})\n'
        "def f(t):\n"
        "    return _TABLE.get(t)\n"
    )
    findings = tbs.scan_source("synthetic_dictcall.py", src)
    assert [(f.kind, f.literal) for f in findings] == [("dispatch", "GOOGL")]


def test_mut3b_ticker_branch_scan__is_test_path_1(tmp_path: Path) -> None:
    """ticker_branch_scan.py:637, return True -> return None (tests/ path)."""
    sni = tmp_path / "research" / "single_name_intelligence"
    (sni / "tests").mkdir(parents=True)
    (sni / "tests" / "test_branch.py").write_text(
        'def f(t):\n    if t == "NVDA":\n        return 1\n',
        encoding="utf-8",
    )
    (sni / "ok.py").write_text("VALUE = 1\n", encoding="utf-8")
    findings = tbs.scan_tree(tmp_path)
    assert findings == []


def test_mut3b_ticker_branch_scan__minimal_yaml_load_1() -> None:
    """ticker_branch_scan.py:284, lines[0][0] -> lines[1][0] (root indent)."""
    obj = tbs._minimal_yaml_load("ticker: NVDA\n")
    assert obj.get("ticker") == "NVDA"


def test_mut3b_ticker_branch_scan__parse_scalar_1() -> None:
    """ticker_branch_scan.py:183, s[0] == s[-1] -> != (quoted scalar)."""
    assert tbs._parse_scalar('"NVDA"') == "NVDA"
    assert tbs._parse_scalar("'BABA'") == "BABA"


def test_mut3b_ticker_branch_scan__sequence_str_constants_1() -> None:
    """ticker_branch_scan.py:424, set/tuple constructor `and` -> `or`."""
    src = (
        "def f(t):\n"
        '    if t in other(("AAPL", "MSFT")):\n'
        "        return 1\n"
        "    return 0\n"
    )
    assert tbs.scan_source("synthetic_other.py", src) == []


def test_mut3b_ticker_branch_scan__snippet_1() -> None:
    """ticker_branch_scan.py:455, lineno > len(lines) -> lineno < len(lines)."""
    src = 'def f(t):\n    if t == "NVDA":\n        return 1\n'
    findings = tbs.scan_source("synthetic_snip.py", src)
    assert findings
    assert "NVDA" in findings[0].snippet


def test_mut3b_ticker_branch_scan__split_key_value_1() -> None:
    """ticker_branch_scan.py:199, ch == \"'\" -> != (colon split)."""
    obj = tbs._minimal_yaml_load("listing: 'FOO:BAR'\n")
    assert obj.get("listing") == "FOO:BAR"


def test_mut3b_ticker_branch_scan__strip_inline_comment_1() -> None:
    """ticker_branch_scan.py:163, in_single = False -> True."""
    obj = tbs._minimal_yaml_load("ticker: NVDA  # note\n")
    assert obj.get("ticker") == "NVDA"


def test_mut3b_ticker_branch_scan_allowlist_matches_1() -> None:
    """ticker_branch_scan.py:715, return False -> return None (path miss)."""
    finding = tbs.Finding("p.py", 1, "compare", "NVDA", "x")
    entry = ("q.py", "compare", "NVDA", "synthetic")
    assert tbs.allowlist_matches(finding, entry) is False


def test_mut3b_ticker_branch_scan_iter_sni_python_files_1(tmp_path: Path) -> None:
    """ticker_branch_scan.py:675, return out -> return None (missing SNI tree)."""
    root = tmp_path / "empty_repo"
    root.mkdir()
    got = tbs.iter_sni_python_files(root)
    assert got == []
    assert isinstance(got, list)


def test_mut3b_ticker_branch_scan_load_profile_ticker_literals_1(
    tmp_path: Path,
) -> None:
    """ticker_branch_scan.py:355, return frozenset() -> return None (no YAML)."""
    n = len(tbs.PROFILE_LOAD_GAPS)
    try:
        got = tbs.load_profile_ticker_literals(tmp_path)
        assert got == frozenset()
        assert isinstance(got, frozenset)
    finally:
        del tbs.PROFILE_LOAD_GAPS[n:]


def test_mut3b_ticker_branch_scan_parse_list_1() -> None:
    """ticker_branch_scan.py:251, i < n -> i > n (nested map after list item)."""
    obj = tbs._minimal_yaml_load(
        "items:\n  - ticker: NVDA\n    listing: NASDAQ\n"
    )
    assert obj["items"][0]["ticker"] == "NVDA"
    assert obj["items"][0]["listing"] == "NASDAQ"


def test_mut3b_ticker_branch_scan_parse_map_1() -> None:
    """ticker_branch_scan.py:262, lines[i][0] -> lines[i][1] (indent slot)."""
    obj = tbs._minimal_yaml_load("ticker: NVDA\n")
    assert obj.get("ticker") == "NVDA"


def test_mut3b_ticker_branch_scan_refresh_ticker_literals_1() -> None:
    """ticker_branch_scan.py:397, return TICKER_LITERALS -> return None."""
    old_t = tbs.TICKER_LITERALS
    old_p = tbs.PROFILE_TICKER_LITERALS
    old_f = tbs._TICKER_FOLDED
    try:
        got = tbs.refresh_ticker_literals()
        assert got is not None
        assert got is tbs.TICKER_LITERALS
        assert isinstance(got, frozenset)
        assert any(token.upper() == "NVDA" for token in got)
    finally:
        tbs.TICKER_LITERALS = old_t
        tbs.PROFILE_TICKER_LITERALS = old_p
        tbs._TICKER_FOLDED = old_f


# ---------------------------------------------------------------------------
# sni_copy_guard survivors
# ---------------------------------------------------------------------------


def test_mut3b_sni_copy_guard_module_1() -> None:
    """sni_copy_guard.py:40, False -> True (AUTHORITY_FLAGS values)."""
    assert cg.AUTHORITY_FLAGS["rank_authority"] is False
    assert all(value is False for value in cg.AUTHORITY_FLAGS.values())


def test_mut3b_sni_copy_guard__is_fence_line_1() -> None:
    """sni_copy_guard.py:263, return fence predicate -> return None."""
    text = (
        "```\n"
        "Southbound holdings show smart money accumulating Tencent.\n"
        "```\n"
    )
    assert check_text(text, "synthetic.md") == []


def test_mut3b_sni_copy_guard_check_text_1() -> None:
    """sni_copy_guard.py:364, Finding(..., a14[0], a14[1]) with 0 -> 1."""
    findings = check_text(
        "Southbound holdings show smart money accumulating Tencent.",
        "synthetic.md",
    )
    a14 = [f for f in findings if f.rule == "A14"]
    assert a14
    assert a14[0].subject_term == "southbound"
    assert a14[0].claim_term == "smart money"


def test_mut3b_sni_copy_guard_is_allowlisted_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """sni_copy_guard.py:379, finding.line == entry.line -> !=."""
    entry = AllowlistEntry(
        "synthetic.md", 1, "A14", "holdings", "synthetic fixture"
    )
    monkeypatch.setattr(cg, "ALLOWLIST", (entry,))
    hit = Finding(
        "synthetic.md",
        1,
        "A14",
        "holdings show smart money",
        "holdings",
        "smart money",
    )
    miss = Finding(
        "synthetic.md",
        2,
        "A14",
        "holdings show smart money",
        "holdings",
        "smart money",
    )
    assert is_allowlisted(hit) is True
    assert is_allowlisted(miss) is False


def test_mut3b_sni_copy_guard_unallowlisted_1() -> None:
    """sni_copy_guard.py:388, return filtered list -> return None."""
    finding = Finding(
        "synthetic.md",
        1,
        "A14",
        "holdings show smart money",
        "holdings",
        "smart money",
    )
    assert unallowlisted([]) == []
    assert unallowlisted([finding]) == [finding]


def test_mut3b_sni_copy_guard__first_match_1() -> None:
    """sni_copy_guard.py:213, cand[1] - cand[0] with 0 -> 1 (longest term)."""
    pairs = (("x", re.compile("x")), ("xy", re.compile("xy")))
    got = _first_match("xy extra", pairs)
    assert got is not None
    assert got[2] == "xy"


def test_mut3b_sni_copy_guard__is_fence_line_2() -> None:
    """sni_copy_guard.py:263, startswith ``` or ~~~ -> and."""
    text = (
        "~~~\n"
        "Southbound holdings show smart money accumulating Tencent.\n"
        "~~~\n"
    )
    assert check_text(text, "synthetic.md") == []


def test_mut3b_sni_copy_guard__require_sni_md_1() -> None:
    """sni_copy_guard.py:400, delete non-markdown suffix raise."""
    inside_py = SNI_ROOT / "acceptance" / "sni_copy_guard.py"
    with pytest.raises(ValueError, match="non-markdown"):
        scan_paths([inside_py])


def test_mut3b_sni_copy_guard_is_allowlisted_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """sni_copy_guard.py:383, return True -> False (allowlist hit)."""
    entry = AllowlistEntry(
        "synthetic.md", 1, "A14", "holdings", "synthetic fixture"
    )
    monkeypatch.setattr(cg, "ALLOWLIST", (entry,))
    hit = Finding(
        "synthetic.md",
        1,
        "A14",
        "holdings show smart money",
        "holdings",
        "smart money",
    )
    assert is_allowlisted(hit) is True
