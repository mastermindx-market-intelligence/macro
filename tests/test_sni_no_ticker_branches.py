"""A36 ticker-branch scan: US/Mag-7 packs must not special-case a ticker.

SNI-local DRAFT tests. They import the scanner only (never the scanned
S1/S2 modules). Authority flags stay false; identity ids are not minted.
"""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_ACCEPT = REPO_ROOT / "research" / "single_name_intelligence" / "acceptance"
if str(_ACCEPT) not in sys.path:
    sys.path.insert(0, str(_ACCEPT))

import ticker_branch_scan as tbs  # noqa: E402

US_COMMON_SCOPE = (
    "research/single_name_intelligence/us_stress/**/*.py",
    "research/single_name_intelligence/us_transfer/**/*.py",
    "research/single_name_intelligence/common/**/*.py",
    "research/single_name_intelligence/evaluation/**/*.py",
)

MAG7 = frozenset({"AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"})

# S1/S2 HK reference-product study code names Alibaba/Tencent (and the
# KWEB overnight proxy). These are expected, pinned, and never ALLOWLIST.
# Update this tuple together with any new or disappeared finding.
REFERENCE_STUDY_EXPECTED: tuple[tuple[str, int, str, str, str], ...] = (
    (
        "research/single_name_intelligence/event_response/s2_seal.py",
        153,
        "dispatch",
        "alibaba",
        "S2 seal dispatch of the graded US ADS leg for the Alibaba issuer group.",
    ),
    (
        "research/single_name_intelligence/event_response/s2_seal.py",
        154,
        "dispatch",
        "tencent",
        "S2 seal dispatch marking the Tencent issuer group census-only.",
    ),
    (
        "research/single_name_intelligence/event_response/s2_selection.py",
        156,
        "compare",
        "BABA",
        "S2 earnings census selects Alibaba ADS rows; HK study, not a US pack branch.",
    ),
    (
        "research/single_name_intelligence/event_response/s2_selection.py",
        240,
        "compare",
        "alibaba",
        "S2 coverage-census report label E1 vs E2 for the Alibaba issuer group.",
    ),
    (
        "research/single_name_intelligence/residual/run_s1.py",
        448,
        "dispatch",
        "KWEB",
        "S1 P03 factor-path table keys the KWEB sector series for the HK study.",
    ),
    (
        "research/single_name_intelligence/residual/s1_report.py",
        425,
        "compare",
        "TCEHY",
        "S1 exemplar table prints the UNRESOLVED TCEHY row of the HK study.",
    ),
    (
        "research/single_name_intelligence/residual/s1_synth.py",
        31,
        "dispatch",
        "KWEB",
        "S1 synthetic-frame builder maps KWEB onto a fixture path for tests.",
    ),
    (
        "research/single_name_intelligence/residual/s1_synth.py",
        77,
        "compare",
        "KWEB",
        "S1 synthetic frames attach a US close_price column on the KWEB series.",
    ),
)


def _key(finding: tbs.Finding) -> tuple[str, int, str, str]:
    return (finding.path, finding.line, finding.kind, finding.literal)


def test_tbs_01_us_and_common_have_no_ticker_branches() -> None:
    findings = tbs.scan_tree(REPO_ROOT, US_COMMON_SCOPE)
    kept = tbs.check_allowlist(findings)
    assert kept == [], (
        "ticker strategy branches in us_stress/us_transfer/common/evaluation:\n"
        + "\n".join(
            f"{f.path}:{f.line} {f.kind} {f.literal!r} {f.snippet}" for f in kept
        )
    )


def test_tbs_02_whole_tree_report() -> None:
    findings = tbs.scan_tree(REPO_ROOT)
    kept = tbs.check_allowlist(findings)
    got = {_key(f) for f in kept}
    expected = {(path, line, kind, literal) for path, line, kind, literal, _r in REFERENCE_STUDY_EXPECTED}
    extra = sorted(got - expected)
    missing = sorted(expected - got)
    assert extra == [], "new ticker-branch findings not in REFERENCE_STUDY_EXPECTED: %r" % extra
    assert missing == [], "REFERENCE_STUDY_EXPECTED entries disappeared: %r" % missing
    for path, line, kind, literal, reason in REFERENCE_STUDY_EXPECTED:
        assert isinstance(reason, str) and reason.strip(), (
            f"{path}:{line} {kind} {literal} has no reason"
        )


def test_tbs_03_detector_catches_each_kind() -> None:
    compare_src = (
        "def f(ticker):\n"
        '    if ticker == "NVDA":\n'
        "        return 1\n"
        "    return 0\n"
    )
    in_tuple_src = (
        "def f(ticker):\n"
        '    if ticker in ("AAPL", "MSFT"):\n'
        "        return 1\n"
        "    return 0\n"
    )
    match_src = (
        "def f(ticker):\n"
        "    match ticker:\n"
        '        case "META":\n'
        "            return 1\n"
        "        case _:\n"
        "            return 0\n"
    )
    dispatch_src = (
        '_TABLE = {"GOOGL": 1.0}\n'
        "def f(t):\n"
        "    return _TABLE.get(t)\n"
    )
    call_src = (
        "def f(ticker):\n"
        '    if ticker.startswith("TSLA"):\n'
        "        return 1\n"
        "    return 0\n"
    )
    endswith_src = (
        "def f(ticker):\n"
        '    return ticker.endswith("BABA")\n'
    )
    upper_src = (
        "def f(ticker):\n"
        '    return ticker.upper() == "AMZN"\n'
    )
    negative_src = (
        '"""Docstring mentioning NVDA and Alibaba and AAPL."""\n'
        "# comment with MSFT\n"
        'PATH = "data/yahoo/NVDA.parquet"\n'
        'UNUSED = "NVDA"\n'
        "def f(ticker):\n"
        '    log = f"failed for {ticker} name=NVDA"\n'
        "    return PATH\n"
    )

    compare = tbs.scan_source("synthetic_compare.py", compare_src)
    assert [(f.kind, f.literal) for f in compare] == [("compare", "NVDA")]

    in_tuple = tbs.scan_source("synthetic_in.py", in_tuple_src)
    assert {f.kind for f in in_tuple} == {"compare"}
    assert {f.literal for f in in_tuple} == {"AAPL", "MSFT"}

    match = tbs.scan_source("synthetic_match.py", match_src)
    assert [(f.kind, f.literal) for f in match] == [("match", "META")]

    dispatch = tbs.scan_source("synthetic_dispatch.py", dispatch_src)
    assert [(f.kind, f.literal) for f in dispatch] == [("dispatch", "GOOGL")]

    call_branch = tbs.scan_source("synthetic_call.py", call_src)
    assert [(f.kind, f.literal) for f in call_branch] == [("call_branch", "TSLA")]

    endswith = tbs.scan_source("synthetic_endswith.py", endswith_src)
    assert [(f.kind, f.literal) for f in endswith] == [("call_branch", "BABA")]

    upper = tbs.scan_source("synthetic_upper.py", upper_src)
    assert [(f.kind, f.literal) for f in upper] == [("call_branch", "AMZN")]

    negative = tbs.scan_source("synthetic_neg.py", negative_src)
    assert negative == [], negative


def test_tbs_04_profile_literals_loaded() -> None:
    profile = {token.upper() for token in tbs.PROFILE_TICKER_LITERALS}
    missing = MAG7 - profile
    assert not missing, (
        "Mag-7 tickers missing from profile-loaded literals (list is only "
        "hand-typed?): %s" % sorted(missing)
    )
    union = {token.upper() for token in tbs.TICKER_LITERALS}
    assert MAG7 <= union
    # listing / sector_etf values exist only in the YAMLs, not the hand list
    extras = {token.upper() for token in tbs.PROFILE_TICKER_LITERALS} - {
        token.upper() for token in tbs._HAND_TYPED
    }
    assert "NASDAQ" in extras
    assert {"XLK", "XLC", "XLY"} <= extras


def test_tbs_05_stale_allowlist_refused() -> None:
    findings = tbs.scan_tree(REPO_ROOT)
    fake = (
        (
            "research/single_name_intelligence/us_stress/no_such_fixture.py",
            "compare",
            "NVDA",
            "fabricated stale allowlist entry",
        ),
    )
    with pytest.raises(tbs.StaleAllowlistError):
        tbs.check_allowlist(findings, fake)
    # the live allowlist (empty) is current against this tree
    tbs.check_allowlist(findings, tbs.ALLOWLIST)


def test_tbs_06_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("scanner must only read files")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(socket, "socket", boom)
    findings = tbs.scan_tree(REPO_ROOT)
    assert isinstance(findings, list)
    kept = tbs.check_allowlist(findings)
    assert len(kept) == len(REFERENCE_STUDY_EXPECTED)
