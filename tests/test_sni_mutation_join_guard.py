"""JGMUT killing tests for sni_join_guard.py survivors (2026-10-13).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic fact
dicts with opaque identity strings; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation, or
trade path. Authority flags stay false. Fixtures are synthetic.

Each test_jgmut_* docstring names one non-equivalent mutant that survived
the pre-existing suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_join_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    JoinVerdict,
    _as_datetime,
    _known_at_later_than_as_of,
    check_join,
    refuse_nonfalse_authority,
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


class _Omit:
    pass


_OMIT = _Omit()


def _base_fact(**overrides):
    fact = {
        "issuer_id": "SYN-ISSUER-1",
        "level": "issuer",
        "metric": "net_income",
        "period_type": "annual",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "basis": "reported",
        "currency": "CNY",
        "source_reported_currency": "CNY",
        "scale": 0,
        "share_denominator": "NOT_PER_SHARE",
        "version": "v1",
        "known_at": "2026-05-13T17:30:00",
        "source_owner": "SYN-OWNER-A",
        "value": 100,
    }
    fact.update(overrides)
    drop = [key for key, val in fact.items() if val is _OMIT]
    for key in drop:
        del fact[key]
    return fact


def _codes(verdict: JoinVerdict) -> set[str]:
    out = set()
    for reason in verdict.reasons:
        if reason.startswith("LEFT:"):
            reason = reason[5:]
        elif reason.startswith("RIGHT:"):
            reason = reason[6:]
        if reason.startswith("SCHEMA_UNKNOWN_FIELD"):
            out.add("SCHEMA_UNKNOWN_FIELD")
        else:
            out.add(reason)
    return out


def test_jgmut_sni_join_guard___post_init___1() -> None:
    """sni_join_guard.py:166, delete `if self.authority.get(key) is not False: raise`."""
    missing = {name: False for name in FLAG_NAMES if name != "rank_authority"}
    with pytest.raises(ValueError, match="authority"):
        JoinVerdict(
            status="ALLOWED",
            reasons=(),
            join_kind="same_fact",
            authority=missing,
        )


def test_jgmut_sni_join_guard__as_datetime_1() -> None:
    """sni_join_guard.py:210, `text == \"\"` -> `text != \"\"`."""
    parsed = _as_datetime("2026-08-12T16:31:00")
    assert parsed is not None
    assert parsed == datetime(2026, 8, 12, 16, 31, 0)
    assert _as_datetime("") is None


def test_jgmut_sni_join_guard_check_join_1() -> None:
    """sni_join_guard.py:436, `and` -> `or` (ads_ratio mismatch requires both ADS)."""
    left = _base_fact(share_denominator="ADS", ads_ratio=5)
    right = _base_fact(
        share_denominator="NOT_PER_SHARE",
        ads_ratio=10,
        source_owner="SYN-OWNER-B",
    )
    verdict = check_join(left, right, join_kind="same_fact")
    codes = _codes(verdict)
    assert verdict.status == "REFUSED"
    assert "DENOMINATOR_MISMATCH" in codes
    assert "ADS_RATIO_MISMATCH" not in codes
    for name in FLAG_NAMES:
        assert verdict.authority[name] is False


def test_jgmut_sni_join_guard_refuse_nonfalse_authority_1() -> None:
    """sni_join_guard.py:144, delete `if not isinstance(flags, Mapping): raise`."""
    with pytest.raises(ValueError, match="not a mapping"):
        refuse_nonfalse_authority(["not-a-mapping"])


def test_jgmut_sni_join_guard___post_init___2() -> None:
    """sni_join_guard.py:176, delete `if not self.reasons: raise` (REFUSED)."""
    with pytest.raises(ValueError, match="REFUSED verdict must carry reasons"):
        JoinVerdict(
            status="REFUSED",
            reasons=(),
            join_kind="same_fact",
        )


def test_jgmut_sni_join_guard__add_version_rule_1() -> None:
    """sni_join_guard.py:359, `or` -> `and` (skip version rule if either version blank)."""
    left = _base_fact(version="v1", supersedes="v0")
    right = _base_fact(version=_OMIT, source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    codes = _codes(verdict)
    assert verdict.status == "REFUSED"
    assert "VERSION_UNKNOWN" in codes
    assert "VERSION_CONFLICT" not in codes
    for name in FLAG_NAMES:
        assert verdict.authority[name] is False


def test_jgmut_sni_join_guard__as_datetime_2() -> None:
    """sni_join_guard.py:212, `len(text) == 10` -> `len(text) != 10`."""
    parsed = _as_datetime("2026-08-12T16:31:00")
    assert parsed == datetime(2026, 8, 12, 16, 31, 0)
    date_only = _as_datetime("2026-08-12")
    assert date_only == datetime(2026, 8, 12, 0, 0, 0)


def test_jgmut_sni_join_guard__known_at_later_than_as_of_1() -> None:
    """sni_join_guard.py:238, `return False` -> `return True` (unparseable as_of)."""
    assert (
        _known_at_later_than_as_of("2026-08-12T16:31:00", "not-a-timestamp")
        is False
    )
    left = _base_fact(known_at="2026-08-12T16:31:00")
    right = _base_fact(known_at="2026-08-12T16:31:00", source_owner="SYN-OWNER-B")
    verdict = check_join(
        left, right, join_kind="same_fact", as_of="not-a-timestamp"
    )
    assert verdict.status == "ALLOWED"
    assert verdict.reasons == ()
    for name in FLAG_NAMES:
        assert verdict.authority[name] is False


def test_jgmut_sni_join_guard_module_1() -> None:
    """sni_join_guard.py:154, `frozen=True` -> `False` (JoinVerdict)."""
    verdict = JoinVerdict(
        status="ALLOWED",
        reasons=(),
        join_kind="same_fact",
    )
    with pytest.raises(FrozenInstanceError):
        verdict.status = "REFUSED"  # type: ignore[misc]


def test_jgmut_sni_join_guard__add_segment_rules_1() -> None:
    """sni_join_guard.py:343, `and` -> `or` (scheme mismatch needs both schemes)."""
    left = _base_fact(segment_scheme_version="sch-1")
    right = _base_fact(source_owner="SYN-OWNER-B")
    verdict = check_join(left, right, join_kind="same_fact")
    assert verdict.status == "ALLOWED"
    assert verdict.reasons == ()
    assert "SEGMENT_SCHEME_MISMATCH" not in _codes(verdict)
    for name in FLAG_NAMES:
        assert verdict.authority[name] is False
