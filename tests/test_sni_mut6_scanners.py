"""MUT6 killing tests for M6J survivors in ticker_branch_scan and sni_copy_guard.

SNI-local DRAFT contract tests (M6J, 2026-10-14). Fixtures are synthetic.
Authority flags stay literal False; nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path. No issuer or security identity
is minted, derived, or guessed: ticker-shaped strings below are scanner
tokens consumed from the modules' own hand-typed literal sets, and unknown
identity stays UNRESOLVED / null (Stock Identity / Data OS own ids).
No git history is read and no network is used (CI is depth-1).

Every test kills one named survivor of the M6J sweep
(research/single_name_intelligence/reviews/MUTATION_SWEEP_SCANNERS_2026-10-14.md).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
if str(ACCEPTANCE) not in sys.path:
    sys.path.insert(0, str(ACCEPTANCE))

import sni_copy_guard as cg  # noqa: E402
import ticker_branch_scan as tbs  # noqa: E402


# ---------------------------------------------------------------------------
# ticker_branch_scan survivors
# ---------------------------------------------------------------------------


def test_m6j_ticker_branch_scan_refuse_authority_override_1() -> None:
    """ticker_branch_scan.py:84, key != canonical -> key == canonical (M02).

    An exactly-spelled authority flag passed as literal False must be
    accepted and returned in the all-false map; the mutant raises.
    """
    returned = tbs.refuse_authority_override(rank_authority=False, trade_authority=False)
    assert returned == dict(tbs.AUTHORITY_FLAGS)
    assert set(returned.values()) == {False}


def test_m6j_ticker_branch_scan__split_key_value_1() -> None:
    """ticker_branch_scan.py:204, content[i + 1 :] -> content[i + 2 :] (M07).

    A value with no space after the YAML colon must keep its first byte.
    """
    assert tbs._split_key_value("ticker:NVDA") == ("ticker", "NVDA")
    assert tbs._split_key_value("sector_etf:KWEB") == ("sector_etf", "KWEB")


def test_m6j_ticker_branch_scan_parse_map_1() -> None:
    """ticker_branch_scan.py:269, i + 1 < n -> i + 2 < n (M10).

    The last key of a minimal-YAML document can have a nested block; the
    mutant turns the child map into None (or indexes past the end).
    """
    got = tbs._minimal_yaml_load("issuer:\n  ticker: BABA\n")
    assert got == {"issuer": {"ticker": "BABA"}}


def test_m6j_ticker_branch_scan__load_yaml_text_1() -> None:
    """ticker_branch_scan.py:298, return _minimal_yaml_load(text) -> return None (M11).

    Text PyYAML rejects must still parse with the indent-based fallback.
    """
    got = tbs._load_yaml_text("a: [unclosed")
    assert got == {"a": "[unclosed"}


def test_m6j_ticker_branch_scan__collect_profile_fields_1() -> None:
    """ticker_branch_scan.py:306, isinstance(value, str) and value.strip() -> or (M12).

    A non-string profile value is skipped silently; the mutant calls
    .strip() on it and crashes. Synthetic fixture, no profile file read.
    """
    out: set = set()
    tbs._collect_profile_fields({"field": "ticker", "value": 700}, out)
    assert out == set()
    tbs._collect_profile_fields({"field": "ticker", "value": "BABA"}, out)
    assert out == {"BABA"}


def test_m6j_ticker_branch_scan__folded_set_1() -> None:
    """ticker_branch_scan.py:385, isinstance(token, str) and token -> or (M16).

    Non-string truthy tokens are dropped, not casefolded; the mutant
    raises AttributeError on 9988.
    """
    assert tbs._folded_set(["BABA", 9988, None, ""]) == frozenset({"baba"})


def test_m6j_ticker_branch_scan__snippet_1() -> None:
    """ticker_branch_scan.py:453, limit: int = 160 -> 161 (M23).

    The snippet cap is 160 characters.
    """
    assert len(tbs._snippet("x" * 200, 1)) == 160


def test_m6j_ticker_branch_scan__rel_matches_1() -> None:
    """ticker_branch_scan.py:656, return True -> return False (M31).

    A glob with two '**' segments still matches any .py under its prefix
    even when fnmatch cannot express it (the '/**/' collapse replaces
    all segments at once).
    """
    assert tbs._rel_matches("pkg/anything.py", ("pkg/**/b/**/c.py",)) is True


def test_m6j_ticker_branch_scan_allowlist_matches_1() -> None:
    """ticker_branch_scan.py:717, return False -> return True (M34).

    An allowlist entry with the right path and literal but the wrong kind
    must NOT match; otherwise a kind-mismatched entry silently suppresses
    a finding and hides from stale-entry detection.
    """
    finding = tbs.Finding(path="synthetic.py", line=3, kind="compare", literal="BABA", snippet="s")
    wrong_kind = ("synthetic.py", "dispatch", "BABA", "synthetic justification")
    right_kind = ("synthetic.py", "compare", "BABA", "synthetic justification")
    assert tbs.allowlist_matches(finding, wrong_kind) is False
    assert tbs.allowlist_matches(finding, right_kind) is True


def test_m6j_ticker_branch_scan_partition_allowlist_1() -> None:
    """ticker_branch_scan.py:734, used[i] = True -> used[i] = False (M35).

    A consumed allowlist entry is not stale; the mutant reports every
    entry stale and makes check_allowlist raise on a live allowlist.
    """
    finding = tbs.Finding(path="synthetic.py", line=3, kind="compare", literal="BABA", snippet="s")
    table = (("synthetic.py", "compare", "BABA", "synthetic justification"),)
    kept, allowed, stale = tbs.partition_allowlist([finding], table)
    assert kept == []
    assert allowed == [finding]
    assert stale == []
    assert tbs.check_allowlist([finding], table) == []


# ---------------------------------------------------------------------------
# sni_copy_guard survivors
# ---------------------------------------------------------------------------


def test_m6j_sni_copy_guard__first_match_1() -> None:
    """sni_copy_guard.py:213, (best[1] - best[0]) -> (best[1] + best[0]) (M45).

    On a tied start the strictly longer candidate wins and an equal-length
    candidate does not: inflating either side of the comparison breaks one
    of the two cases.
    """
    tie = (
        ("first-term", re.compile(r"\bfoo bar\b")),
        ("second-term", re.compile(r"\bfoo\s+bar\b")),
    )
    assert cg._first_match("lead foo bar tail", tie) == (5, 12, "first-term")
    longer = (
        ("short", re.compile(r"\bfoo\b")),
        ("longer", re.compile(r"\bfoo bar\b")),
    )
    assert cg._first_match("say foo bar now", longer) == (4, 11, "longer")


def test_m6j_sni_copy_guard_split_sentences_1() -> None:
    """sni_copy_guard.py:310, i += 1 -> i += 2 after a table-cell '|' (M49).

    Only the '|' separator is consumed; the first character of the next
    cell must survive.
    """
    assert cg.split_sentences("cell one|cell two") == [(1, "cell one"), (1, "cell two")]


def test_m6j_sni_copy_guard_check_text_1() -> None:
    """sni_copy_guard.py:369, a30[0] -> a30[1] (M53).

    An A30 finding records the failed-state term as subject_term and the
    forecast-success term as claim_term; the mutant duplicates the
    success term into both slots.
    """
    findings = cg.check_text("The NO-GO model still predicts returns.", "synthetic.md")
    a30 = [f for f in findings if f.rule == "A30"]
    assert len(a30) == 1
    assert a30[0].subject_term == "NO-GO"
    assert a30[0].claim_term == "predicts"
