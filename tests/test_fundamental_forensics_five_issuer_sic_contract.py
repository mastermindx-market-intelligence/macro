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

from engine.fundamental_forensics.detectors import issuer_class_for_sic
from engine.fundamental_forensics.issuer_sic import resolve_issuer_sic

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"


def test_every_shipped_five_issuer_member_carries_a_resolvable_sic() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["schema"] == "fundamental_forensics.coverage_contract/v1"
    issuers = contract["issuers"]
    assert issuers, "the shipped coverage contract must not be empty"
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
        assert issuer_class_for_sic(sic) not in (None,), (ticker, sic)
        if "issuer_class" in issuer:
            assert issuer["issuer_class"] == issuer_class_for_sic(sic), (ticker, sic)
