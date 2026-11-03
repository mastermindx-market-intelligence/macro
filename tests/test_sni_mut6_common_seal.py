"""test_sni_mut6_common_seal.py — MUT6F killing tests for common/sni_seal.py.

Sweep: research/single_name_intelligence/reviews/
MUTATION_SWEEP_COMMON_SEAL_2026-10-14.md (lane M6F, seed 20261014).
Each test kills one mutation-sweep survivor of `verify_seal` or a helper it
calls. DRAFT-GUARD only: nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path; all fixtures are synthetic.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "research/single_name_intelligence/common"
    ),
)

import sni_seal  # noqa: E402
from sni_seal import (  # noqa: E402
    _parse_cell,
    _validate_sealed_at_utc,
    build_seal,
    verify_seal,
)

_HEX64 = "a" * 64


def _valid_seal() -> dict:
    """Synthetic valid seal (baseline for verify_seal is zero violations)."""
    return build_seal(
        lane="lane-m6f-fixture",
        protocol_ids=["proto-alpha"],
        cells=[
            {"protocol": "proto-alpha", "version": 1, "split": "TRAIN", "h": 1},
            {"protocol": "proto-beta", "version": "v2", "split": "TEST", "h": 2},
        ],
        budgets={"proto-alpha": 3, "proto-beta": 5, "audit_extra_family": 7},
        input_manifest=[
            {"path": "synthetic/one.bin", "sha256": _HEX64},
            {"path": "synthetic/two.bin", "sha256": "b" * 64},
        ],
        prereg_digest=_HEX64,
        identity_facts={"issuer_id": None, "note": "synthetic fixture"},
        sealed_at_utc="2026-10-14T00:00:00Z",
        repo_ref="0000000000000000000000000000000000000000",
    )


def test_m6f_sni_seal__validate_sealed_at_utc_1():
    """Kill M27: common/sni_seal.py:122 'or' -> 'and' in
    _validate_sealed_at_utc's non-Z guard. A naive-looking timestamp string
    without the trailing 'Z' must still be refused; with 'and' the guard only
    fires for values that are simultaneously non-str AND non-Z, so a plain
    non-Z string slips through verify_seal unflagged.
    """
    with pytest.raises(ValueError):
        _validate_sealed_at_utc("2026-01-01T00:00:00")
    seal = _valid_seal()
    assert verify_seal(seal) == []
    tampered = dict(seal)
    tampered["sealed_at_utc"] = "2026-01-01T00:00:00"
    violations = verify_seal(tampered)
    assert any(
        "sealed_at_utc must be an ISO-8601 Z string" in v for v in violations
    )


def test_m6f_sni_seal__parse_cell_1():
    """Kill M35: common/sni_seal.py:187 'or' -> 'and' in _parse_cell's shape
    guard. A non-dict cell must raise ValueError (verify_seal records it as a
    malformed cell); with 'and' the guard short-circuits into
    set(cell.keys()) and blows up with TypeError/AttributeError instead, so
    verify_seal crashes rather than returning violations.
    """
    with pytest.raises(ValueError):
        _parse_cell("not-a-dict")
    with pytest.raises(ValueError):
        _parse_cell(["not-a-dict-either"])
    seal = _valid_seal()
    tampered = dict(seal)
    tampered["cells"] = ["not-a-dict"]
    violations = verify_seal(tampered)
    assert isinstance(violations, list)
    assert violations  # malformed cell must yield some violation, not silence


def test_m6f_sni_seal_verify_seal_1():
    """Kill M38: common/sni_seal.py:426 'or' -> 'and' in verify_seal's
    per-family budget check. A non-positive budget for a NON-protocol family
    must be reported; with 'and' the check only fires when the value is both
    non-int and non-positive, so budgets[family] = 0 passes unflagged.
    """
    seal = _valid_seal()
    assert verify_seal(seal) == []
    tampered = dict(seal)
    tampered["budgets"] = dict(seal["budgets"])
    tampered["budgets"]["audit_extra_family"] = 0
    violations = verify_seal(tampered)
    assert "non-positive budget for audit_extra_family" in violations
