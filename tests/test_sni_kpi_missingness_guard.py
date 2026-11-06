"""A10 KPI-missingness-guard tests: missing KPIs are not zero or carried.

SNI-local DRAFT contract tests. They consume owner-supplied FIF /
Company Event/Earnings KPI disclosure records and never mint issuer or
security ids. HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_kpi_missingness_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    KPI_STATES,
    REASONS,
    KpiSeriesVerdict,
    aggregate_sum,
    check_kpi_series,
    kpi_value,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_kpi_missingness_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

PERIODS = ("SYN-P-1", "SYN-P-2", "SYN-P-3", "SYN-P-4")


def _record(period_id, state="reported", value=10, **overrides):
    rec = {
        "period_id": period_id,
        "state": state,
        "value": value,
    }
    rec.update(overrides)
    drop = [key for key, val in rec.items() if val is _OMIT]
    for key in drop:
        del rec[key]
    return rec


class _Omit:
    pass


_OMIT = _Omit()


def _positive_series():
    values = (10, 20, 30, 40)
    return tuple(
        _record(period_id, value=value)
        for period_id, value in zip(PERIODS, values)
    )


def _assert_contract(verdict: KpiSeriesVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert verdict.reasons == tuple(
        code for code in REASONS if code in set(verdict.reasons)
    )
    assert len(verdict.reasons) == len(set(verdict.reasons))
    if verdict.allowed:
        assert verdict.reasons == ()
    else:
        assert verdict.reasons
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False


def _assert_allowed(verdict: KpiSeriesVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_refused(verdict: KpiSeriesVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _flip_first(**overrides):
    series = list(_positive_series())
    body = {
        "period_id": PERIODS[0],
        "state": "reported",
        "value": 10,
    }
    body.update(overrides)
    period_id = body.pop("period_id")
    series[0] = _record(period_id, **body)
    return tuple(series)


# ---------------------------------------------------------------------------
# T1 / positive control
# ---------------------------------------------------------------------------


def test_a10_positive_four_reported_quarters():
    series = _positive_series()
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_allowed(verdict)
    assert verdict.reported_periods == PERIODS
    assert aggregate_sum(series, periods=PERIODS) == 100
    assert kpi_value(series[0]) == 10


def test_a10_positive_reported_negative_finite():
    series = list(_positive_series())
    series[0] = _record(PERIODS[0], value=-7)
    series = tuple(series)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_allowed(verdict)
    assert kpi_value(series[0]) == -7
    assert aggregate_sum(series, periods=PERIODS) == 83


# ---------------------------------------------------------------------------
# T2 / one single-flip test per REASON
# ---------------------------------------------------------------------------


def test_a10_period_id_missing():
    series = _flip_first(period_id=None)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "PERIOD_ID_MISSING")


def test_a10_duplicate_period():
    series = list(_positive_series())
    series[1] = _record(PERIODS[0], value=20)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    _assert_refused(verdict, "DUPLICATE_PERIOD")


def test_a10_state_unknown():
    series = _flip_first(state="pending")
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "STATE_UNKNOWN")
    assert "MISSING_CARRIES_VALUE" not in verdict.reasons


def test_a10_reported_value_invalid():
    series = _flip_first(value=None)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "REPORTED_VALUE_INVALID")


def test_a10_missing_carries_value():
    series = _flip_first(state="not_reported")
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "MISSING_CARRIES_VALUE")


def test_a10_period_absent():
    series = _positive_series()
    expected = PERIODS + ("SYN-P-5",)
    verdict = check_kpi_series(series, expected_periods=expected)
    _assert_refused(verdict, "PERIOD_ABSENT")
    assert verdict.reasons == ("PERIOD_ABSENT",)


def test_a10_unexpected_period():
    series = list(_positive_series())
    series[0] = _record("SYN-P-X", value=10)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    _assert_refused(verdict, "UNEXPECTED_PERIOD")


def test_a10_carry_forward_declared():
    series = _flip_first(carry_forward=True)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "CARRY_FORWARD_DECLARED")
    assert verdict.reasons == ("CARRY_FORWARD_DECLARED",)


def test_a10_imputation_declared():
    series = _flip_first(imputed=True)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "IMPUTATION_DECLARED")
    assert verdict.reasons == ("IMPUTATION_DECLARED",)


# ---------------------------------------------------------------------------
# not_reported carrying 0 / 0.0
# ---------------------------------------------------------------------------


def test_a10_not_reported_value_zero():
    series = _flip_first(state="not_reported", value=0)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "MISSING_CARRIES_VALUE")
    assert kpi_value(series[0]) is None


def test_a10_not_reported_value_zero_float():
    series = _flip_first(state="not_reported", value=0.0)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "MISSING_CARRIES_VALUE")
    assert kpi_value(series[0]) is None


def test_a10_not_applicable_carries_value():
    series = _flip_first(state="not_applicable", value=0)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "MISSING_CARRIES_VALUE")


def test_a10_withheld_carries_value():
    series = _flip_first(state="withheld", value=12)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "MISSING_CARRIES_VALUE")


# ---------------------------------------------------------------------------
# kpi_value
# ---------------------------------------------------------------------------


def test_a10_kpi_value_not_reported_is_none():
    rec = _record(PERIODS[0], state="not_reported", value=None)
    got = kpi_value(rec)
    assert got is None
    rec_zero = _record(PERIODS[0], state="not_reported", value=0)
    assert kpi_value(rec_zero) is None


def test_a10_kpi_value_not_applicable_is_none():
    rec = _record(PERIODS[0], state="not_applicable", value=None)
    assert kpi_value(rec) is None
    rec_zero = _record(PERIODS[0], state="not_applicable", value=0)
    assert kpi_value(rec_zero) is None


def test_a10_kpi_value_withheld_is_none():
    rec = _record(PERIODS[0], state="withheld", value=None)
    assert kpi_value(rec) is None
    rec_zero = _record(PERIODS[0], state="withheld", value=0.0)
    assert kpi_value(rec_zero) is None


def test_a10_kpi_value_reported_returns_value():
    rec = _record(PERIODS[0], value=10)
    assert kpi_value(rec) == 10
    assert kpi_value(rec) is not None


def test_a10_kpi_value_reported_zero_is_zero():
    rec = _record(PERIODS[0], value=0)
    assert kpi_value(rec) == 0
    assert kpi_value(rec) is not None
    rec_f = _record(PERIODS[0], value=0.0)
    assert kpi_value(rec_f) == 0.0
    assert kpi_value(rec_f) is not None


def test_a10_kpi_value_invalid_reported_is_none():
    assert kpi_value(_record(PERIODS[0], value=None)) is None
    assert kpi_value(_record(PERIODS[0], value="12")) is None
    assert kpi_value(_record(PERIODS[0], value=True)) is None
    assert kpi_value(_record(PERIODS[0], value=math.nan)) is None
    assert kpi_value(_record(PERIODS[0], value=math.inf)) is None


# ---------------------------------------------------------------------------
# aggregate_sum
# ---------------------------------------------------------------------------


def test_a10_aggregate_sum_not_reported_none():
    series = _flip_first(state="not_reported", value=None)
    assert aggregate_sum(series, periods=PERIODS) is None


def test_a10_aggregate_sum_absent_none():
    series = _positive_series()
    assert aggregate_sum(series, periods=PERIODS + ("SYN-P-5",)) is None
    truncated = series[:-1]
    assert aggregate_sum(truncated, periods=PERIODS) is None


def test_a10_aggregate_sum_complete():
    series = _positive_series()
    assert aggregate_sum(series, periods=PERIODS) == 100
    assert aggregate_sum(series, periods=PERIODS[:2]) == 30


def test_a10_aggregate_sum_empty_periods_none():
    series = _positive_series()
    assert aggregate_sum(series, periods=()) is None


def test_a10_aggregate_sum_never_partial():
    series = _flip_first(state="not_reported", value=None)
    got = aggregate_sum(series, periods=PERIODS)
    assert got is None
    assert got != 90
    assert got != 0


def test_a10_aggregate_sum_duplicate_named_period_none():
    series = _positive_series()
    assert aggregate_sum(series, periods=(PERIODS[0], PERIODS[0])) is None


# ---------------------------------------------------------------------------
# T3 / authority
# ---------------------------------------------------------------------------


def test_a10_authority_refuse_true_zero_none_empty():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    for name in FLAG_NAMES:
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: True})
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: 0})
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: None})
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: ""})


def test_a10_authority_flags_item_assignment_raises():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["trade_authority"] = False


def test_a10_authority_flags_literal_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
        assert AUTHORITY_FLAGS[name] is not 0  # noqa: F632
        assert AUTHORITY_FLAGS[name] is not None


def test_a10_verdict_authority_flags_identity():
    allowed = check_kpi_series(_positive_series(), expected_periods=PERIODS)
    refused = check_kpi_series(_flip_first(imputed=True), expected_periods=PERIODS)
    assert allowed.authority_flags is AUTHORITY_FLAGS
    assert refused.authority_flags is AUTHORITY_FLAGS
    built = KpiSeriesVerdict(allowed=True, reasons=(), reported_periods=PERIODS)
    assert built.authority_flags is AUTHORITY_FLAGS
    assert built.allowed is True


def test_a10_allowed_true_iff_reasons_empty():
    forced = KpiSeriesVerdict(
        allowed=True,
        reasons=("PERIOD_ABSENT",),
        reported_periods=(),
    )
    assert forced.allowed is False
    assert forced.reasons == ("PERIOD_ABSENT",)
    empty = KpiSeriesVerdict(
        allowed=False,
        reasons=(),
        reported_periods=PERIODS,
    )
    assert empty.allowed is True
    assert empty.reasons == ()


# ---------------------------------------------------------------------------
# T4 / static scan
# ---------------------------------------------------------------------------


def test_a10_static_scan_module_source():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    for ticker in (
        "BABA",
        "TCEHY",
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
    ):
        assert ticker not in source
    for needle in ("datetime.now", "utcnow", "date.today", "time.time", "open("):
        assert needle not in source


def test_a10_reasons_frozen_contract():
    assert REASONS == (
        "PERIOD_ID_MISSING",
        "DUPLICATE_PERIOD",
        "STATE_UNKNOWN",
        "REPORTED_VALUE_INVALID",
        "MISSING_CARRIES_VALUE",
        "PERIOD_ABSENT",
        "UNEXPECTED_PERIOD",
        "CARRY_FORWARD_DECLARED",
        "IMPUTATION_DECLARED",
    )
    assert len(REASONS) == len(set(REASONS))
    assert KPI_STATES == (
        "reported",
        "not_reported",
        "not_applicable",
        "withheld",
    )


# ---------------------------------------------------------------------------
# T5 / de-dup and order
# ---------------------------------------------------------------------------


def test_a10_reasons_dedup_and_order():
    series = (
        _record("", state="pending", value=None, carry_forward=True, imputed=True),
        _record(PERIODS[1], value=20),
        _record(PERIODS[1], value=20, carry_forward=True, imputed=True),
        _record(PERIODS[2], value=None),
        _record(PERIODS[3], state="not_reported", value=0),
        _record("SYN-P-X", value=1, carry_forward=True),
    )
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(
        verdict,
        "PERIOD_ID_MISSING",
        "DUPLICATE_PERIOD",
        "STATE_UNKNOWN",
        "REPORTED_VALUE_INVALID",
        "MISSING_CARRIES_VALUE",
        "PERIOD_ABSENT",
        "UNEXPECTED_PERIOD",
        "CARRY_FORWARD_DECLARED",
        "IMPUTATION_DECLARED",
    )
    assert verdict.reasons == REASONS
    assert len(verdict.reasons) == len(set(verdict.reasons))


# ---------------------------------------------------------------------------
# T6 / adversarial period_id
# ---------------------------------------------------------------------------


def test_a10_adversarial_period_id_trailing_space():
    series = list(_positive_series())
    series[0] = _record(PERIODS[0] + " ", value=10)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    # FAMILY TEXT RULE v2: a padded period_id is ABSENT, never a different valid id.
    _assert_refused(verdict, "PERIOD_ID_MISSING", "PERIOD_ABSENT")
    assert aggregate_sum(tuple(series), periods=PERIODS) is None


def test_a10_adversarial_period_id_case_change():
    series = list(_positive_series())
    series[0] = _record("syn-p-1", value=10)
    verdict = check_kpi_series(tuple(series), expected_periods=PERIODS)
    _assert_refused(verdict, "PERIOD_ABSENT", "UNEXPECTED_PERIOD")
    assert series[0]["period_id"] != PERIODS[0]


def test_a10_adversarial_period_id_cyrillic_lookalike():
    # Latin "a" in expected vs Cyrillic U+0430 in the record.
    expected = ("SYN-Pa-1", "SYN-P-2", "SYN-P-3", "SYN-P-4")
    series = (
        _record("SYN-Pа-1", value=10),
        _record("SYN-P-2", value=20),
        _record("SYN-P-3", value=30),
        _record("SYN-P-4", value=40),
    )
    assert series[0]["period_id"] != expected[0]
    verdict = check_kpi_series(series, expected_periods=expected)
    _assert_refused(verdict, "PERIOD_ABSENT", "UNEXPECTED_PERIOD")


# ---------------------------------------------------------------------------
# extra reported-value refusals and optional-flag negatives
# ---------------------------------------------------------------------------


def test_a10_reported_value_invalid_nan():
    series = _flip_first(value=math.nan)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "REPORTED_VALUE_INVALID")


def test_a10_reported_value_invalid_inf():
    series = _flip_first(value=math.inf)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "REPORTED_VALUE_INVALID")
    series_neg = _flip_first(value=-math.inf)
    _assert_refused(
        check_kpi_series(series_neg, expected_periods=PERIODS),
        "REPORTED_VALUE_INVALID",
    )


def test_a10_reported_value_invalid_bool():
    series = _flip_first(value=True)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "REPORTED_VALUE_INVALID")
    series_f = _flip_first(value=False)
    _assert_refused(
        check_kpi_series(series_f, expected_periods=PERIODS),
        "REPORTED_VALUE_INVALID",
    )


def test_a10_reported_value_invalid_str():
    series = _flip_first(value="10")
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "REPORTED_VALUE_INVALID")


def test_a10_carry_forward_false_allowed():
    series = _flip_first(carry_forward=False)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_allowed(verdict)


def test_a10_imputed_false_allowed():
    series = _flip_first(imputed=False)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_allowed(verdict)


def test_a10_blank_period_id_empty_string():
    series = _flip_first(period_id="")
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_refused(verdict, "PERIOD_ID_MISSING")


def test_a10_well_formed_not_reported_none_value_allowed():
    series = _flip_first(state="not_reported", value=None)
    verdict = check_kpi_series(series, expected_periods=PERIODS)
    _assert_allowed(verdict)
    assert aggregate_sum(series, periods=PERIODS) is None
    assert kpi_value(series[0]) is None
