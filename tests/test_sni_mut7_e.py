"""M7E mutation-sweep killing tests for two SNI DRAFT guard modules.

SNI-local DRAFT contract tests (SNI commission 8659). They consume
owner-supplied opaque identity strings and period/slot records; they never
mint issuer or security ids or evidence refs. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic. No network, no git-history reads (CI is depth-1).

Each test kills one specific surviving mutant found by the M7E sweep
(review: research/single_name_intelligence/reviews/
MUTATION_SWEEP_M7E_2026-10-14.md). The docstring names the mutant
(file:line, original -> mutated); every claim was re-verified by re-running
that mutant against this file.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_kpi_missingness_guard import (  # noqa: E402
    aggregate_sum,
    check_kpi_series,
    kpi_value,
)
from sni_release_evidence_guard import check_release  # noqa: E402

P1 = "SYN-M7E-P1"
P2 = "SYN-M7E-P2"
PAGE_ID = "SYN-M7E-PAGE"
SLOT_ID = "SYN-M7E-SLOT"


def _rec(period_id, state="reported", value=10):
    return {"period_id": period_id, "state": state, "value": value}


def _series():
    return (_rec(P1, value=10), _rec(P2, value=20))


def _positive_page():
    return {
        "page_id": PAGE_ID,
        "slots": (
            {
                "slot_id": SLOT_ID,
                "state": "present",
                "provenance": "owner",
                "evidence_ref": "SYN-M7E-REF-1",
                "required": True,
            },
        ),
    }


# ---------------------------------------------------------------------------
# kpi / sni_kpi_missingness_guard.py
# ---------------------------------------------------------------------------


def test_m7e_kpi_as_records_1():
    """Kill kpi:guard#1@147 — sni_kpi_missingness_guard.py:147
    `if not isinstance(series, (list, tuple)): raise TypeError` deleted.
    The series-level type refusal is observable by message, not only by
    exception class (with the guard deleted a str input falls through to
    the per-record guard; an int input raises "'int' object is not
    iterable" instead).
    """
    with pytest.raises(TypeError, match=r"series must be a list or tuple"):
        check_kpi_series("not-a-series", expected_periods=())
    with pytest.raises(TypeError, match=r"series must be a list or tuple"):
        aggregate_sum(42, periods=(P1,))


def test_m7e_kpi_as_records_2():
    """Kill kpi:guard#6@151 — sni_kpi_missingness_guard.py:151
    `if not isinstance(item, Mapping): raise TypeError` deleted.
    Non-mapping records must be refused with TypeError (mutant lets
    rec.get raise AttributeError instead).
    """
    with pytest.raises(TypeError, match=r"each record must be a Mapping"):
        check_kpi_series([1, 2], expected_periods=())
    with pytest.raises(TypeError, match=r"each record must be a Mapping"):
        aggregate_sum(["not-a-record"], periods=(P1,))


def test_m7e_kpi_as_period_ids_1():
    """Kill kpi:guard#2@158 — sni_kpi_missingness_guard.py:158
    `if not isinstance(periods, (list, tuple)): raise TypeError` deleted.
    A bare-string periods/expected_periods must be refused (mutant silently
    iterates its characters).
    """
    series = _series()
    with pytest.raises(TypeError, match=r"periods must be a list or tuple"):
        aggregate_sum(series, periods=P1)
    with pytest.raises(
        TypeError, match=r"expected_periods must be a list or tuple"
    ):
        check_kpi_series(series, expected_periods=7)


def test_m7e_kpi_kpi_value_1():
    """Kill kpi:guard#3@176 — sni_kpi_missingness_guard.py:176
    `if not isinstance(record, Mapping): raise TypeError` deleted.
    kpi_value must refuse a non-mapping record with TypeError (mutant lets
    record.get raise AttributeError instead).
    """
    with pytest.raises(TypeError, match=r"record must be a Mapping"):
        kpi_value(12345)
    with pytest.raises(TypeError, match=r"record must be a Mapping"):
        kpi_value(["not-a-mapping"])


def test_m7e_kpi_check_kpi_series_1():
    """Kill kpi:boolop#1@264 — sni_kpi_missingness_guard.py:264
    `if not _blank(period_id) and not _contains(reported_acc, period_id)`
    and -> or. reported_periods must exclude blank period ids and
    de-duplicate repeated reported ids (mutant admits both).
    """
    series = (
        _rec(None, value=10),
        _rec(P1, value=10),
        _rec(P1, value=10),
        _rec(P2, value=20),
    )
    verdict = check_kpi_series(series, expected_periods=(P1, P2))
    assert verdict.reported_periods == (P1, P2)
    assert None not in verdict.reported_periods
    assert verdict.reported_periods.count(P1) == 1


# ---------------------------------------------------------------------------
# release / sni_release_evidence_guard.py
# ---------------------------------------------------------------------------


def test_m7e_release_as_slots_1():
    """Kill release:guard#2@138 — sni_release_evidence_guard.py:138
    `if not isinstance(value, (list, tuple)): raise TypeError` deleted.
    A non-sequence slots value must be refused with the named message
    (mutant lets `for item in 5` raise "'int' object is not iterable").
    """
    with pytest.raises(TypeError, match=r"slots must be a sequence of mappings"):
        check_release({"page_id": PAGE_ID, "slots": 5})


def test_m7e_release_as_slots_2():
    """Kill release:guard#6@142 — sni_release_evidence_guard.py:142
    `if not isinstance(item, Mapping): raise TypeError` deleted.
    A non-mapping slot must be refused with TypeError (mutant lets
    slot.get raise AttributeError instead).
    """
    with pytest.raises(TypeError, match=r"slot must be a Mapping"):
        check_release({"page_id": PAGE_ID, "slots": [1]})


def test_m7e_release_release_verdict_1():
    """Kill release:const#8@98 — sni_release_evidence_guard.py:98
    @dataclass(frozen=True) constant True -> False. A ReleaseVerdict is
    immutable: field assignment must raise FrozenInstanceError.
    """
    verdict = check_release(_positive_page())
    assert verdict.allowed is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.allowed = False
    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.reasons = ("PAGE_ID_MISSING",)
    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.present_owner_slots = ()
