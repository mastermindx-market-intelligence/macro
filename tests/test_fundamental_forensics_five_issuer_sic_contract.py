"""FIF G0 (item h): every shipped five_issuer_v1 member carries a SIC.

G0's class gate reads an issuer's SIC through the shipped coverage contract
(``engine.fundamental_forensics.issuer_sic.resolve_issuer_sic``); a member
row without a ``sic`` silently reads NOT_EVALUABLE(issuer_class_unknown) on
all 16 class-restricted metrics with no artifact surfacing why (the P1-F
gap).  This test asserts the contract-level invariant directly — the
incidental ``issuer_class_for_sic(issuer["sic"])`` lookup in
tests/test_fundamental_forensics_coverage_contract.py only fails with a
KeyError, which names nothing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from engine.fundamental_forensics.coverage_proof import THRESHOLDS_SCHEMA
from engine.fundamental_forensics.detectors import issuer_class_for_sic
from engine.fundamental_forensics.issuer_sic import _NON_MEMBER_SCHEMAS, resolve_issuer_sic

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_DIR = ROOT / "config" / "fundamental_forensics" / "coverage"
CONTRACT_PATH = COVERAGE_DIR / "five_issuer_v1.json"
CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
SHIPPED_DOCUMENTS = sorted(COVERAGE_DIR.glob("*.json"))
# Every shipped member contract feeds the resolver's index, so every one is
# held to the same invariant, not only the five-issuer contract.
SHIPPED_CONTRACTS = [
    path
    for path in SHIPPED_DOCUMENTS
    if json.loads(path.read_text(encoding="utf-8")).get("schema") not in _NON_MEMBER_SCHEMAS
]


def test_the_five_issuer_contract_is_among_the_shipped_contracts() -> None:
    assert CONTRACT_PATH in SHIPPED_CONTRACTS


def test_the_resolver_skips_only_the_frozen_thresholds_schema() -> None:
    # The skip set is exactly the C2 thresholds document's schema, read from
    # its owner; widening it would let a real contract fall out of the index.
    assert _NON_MEMBER_SCHEMAS == frozenset({THRESHOLDS_SCHEMA})


@pytest.mark.parametrize("document_path", SHIPPED_DOCUMENTS, ids=lambda path: path.name)
def test_every_shipped_coverage_document_is_a_contract_or_a_declared_non_member(
    document_path: Path,
) -> None:
    schema = json.loads(document_path.read_text(encoding="utf-8")).get("schema")
    assert schema == CONTRACT_SCHEMA or schema in _NON_MEMBER_SCHEMAS, (document_path.name, schema)


def test_a_thresholds_document_beside_a_contract_does_not_break_resolution(tmp_path: Path) -> None:
    root = _write_contract(tmp_path, [{"cik": "0000000001", "sic": "3571"}])
    coverage = root / "config" / "fundamental_forensics" / "coverage"
    (coverage / "c2_thresholds_v1.json").write_text(
        json.dumps({"schema": THRESHOLDS_SCHEMA, "thresholds_id": "synthetic"}), encoding="utf-8"
    )
    assert resolve_issuer_sic("0000000001", repo_root=root) == "3571"


@pytest.mark.parametrize(
    "document",
    [
        {"schema": "fundamental_forensics.coverage_thresholds/v2"},
        {"schema": ["fundamental_forensics.coverage_thresholds/v1"]},
        {"thresholds_id": "no-schema"},
        {"schema": THRESHOLDS_SCHEMA + " "},
    ],
    ids=repr,
)
def test_an_undeclared_document_without_issuers_still_fails_closed(
    tmp_path: Path, document: dict
) -> None:
    root = _write_contract(tmp_path, [{"cik": "0000000001", "sic": "3571"}])
    coverage = root / "config" / "fundamental_forensics" / "coverage"
    (coverage / "stray.json").write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="carries no issuers list: stray.json"):
        resolve_issuer_sic("0000000001", repo_root=root)


@pytest.mark.parametrize("contract_path", SHIPPED_CONTRACTS, ids=lambda path: path.name)
def test_every_shipped_coverage_member_carries_a_resolvable_sic(contract_path: Path) -> None:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert contract["schema"] == CONTRACT_SCHEMA
    issuers = contract["issuers"]
    assert issuers, "a shipped coverage contract must not be empty"
    for issuer in issuers:
        ticker = issuer.get("ticker")
        sic = issuer.get("sic")
        # The `sic` field itself: present, non-null, digit-normalised — the
        # classification basis the contract declares (issuer_class_basis: sic).
        assert isinstance(sic, str) and re.fullmatch(r"\d+", sic), (ticker, sic)
        # The resolver agrees: an exact CIK match resolves this same SIC.
        assert resolve_issuer_sic(issuer["cik"]) == sic, (ticker, issuer["cik"])
        # And the SIC maps to a known issuer class, so no restricted metric
        # can silently read issuer_class_unknown for a shipped member.
        assert issuer_class_for_sic(sic) != "unknown", (ticker, sic)
        if "issuer_class" in issuer:
            assert issuer["issuer_class"] == issuer_class_for_sic(sic), (ticker, sic)


def _write_contract(root: Path, members: list[dict]) -> Path:
    coverage = root / "config" / "fundamental_forensics" / "coverage"
    coverage.mkdir(parents=True)
    (coverage / "synthetic.json").write_text(
        json.dumps({"schema": "fundamental_forensics.coverage_contract/v1", "issuers": members}),
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize(
    "raw_sic",
    ["abc", "35 71", "3571x", "-3571", "\u00b2", "", "   ", None, True, -3571, 3.5],
    ids=repr,
)
def test_a_malformed_sic_resolves_to_none_never_to_class_unknown(tmp_path: Path, raw_sic) -> None:
    # issuer_class_for_sic maps unparseable text to "unknown", which every
    # exclusion-only policy admits; the resolver must answer None instead so
    # class-restricted metrics stay NOT_EVALUABLE (issuer_class_unknown).
    root = _write_contract(tmp_path, [{"cik": "0000000001", "sic": raw_sic}])
    assert resolve_issuer_sic("0000000001", repo_root=root) is None


@pytest.mark.parametrize("raw_sic, expected", [("3571", "3571"), (" 6021 ", "6021"), (7372, "7372")])
def test_a_digit_sic_resolves_to_its_digit_string(tmp_path: Path, raw_sic, expected: str) -> None:
    root = _write_contract(tmp_path, [{"cik": 1, "sic": raw_sic}])
    assert resolve_issuer_sic("1", repo_root=root) == expected
