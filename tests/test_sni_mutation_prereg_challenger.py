"""Killing tests for MUT3C survivors in s1_prereg.py and s1_challenger.py.

SNI-local DRAFT contract tests. Fixtures are synthetic. Authority flags stay
false. This file does not mint issuer or security identifiers and does not
feed a rank, gate, size, signal, escalation, or trade path. s1_prereg /
s1_challenger consume owner-supplied identity strings and sealed pins;
Stock Identity / Data OS remain the owners of those values.
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"),
)

from s1_challenger import (  # noqa: E402
    MIN_LAST_DATE,
    MIN_TRAIN_MONTHS,
    UNIVERSE_END,
    UNIVERSE_START,
    build_universe,
    characteristics_at,
    estimability,
    month_key,
)
from s1_data import InjectableStore  # noqa: E402


def _days(n: int, start: date = date(2020, 1, 1)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


# ---------------------------------------------------------------------------
# s1_challenger survivors
# ---------------------------------------------------------------------------


def test_mut3c_s1_challenger_module_1():
    """s1_challenger.py:27, UNIVERSE_START month 1 -> 2 (date(2012, 1, 3))."""
    assert UNIVERSE_START == date(2012, 1, 3)


def test_mut3c_s1_challenger_module_2():
    """s1_challenger.py:27, UNIVERSE_START day 3 -> 4 (date(2012, 1, 3))."""
    assert UNIVERSE_START.day == 3
    assert UNIVERSE_START == date(2012, 1, 3)


def test_mut3c_s1_challenger_module_3():
    """s1_challenger.py:28, UNIVERSE_END month 9 -> 10 (date(2026, 9, 30))."""
    assert UNIVERSE_END == date(2026, 9, 30)


def test_mut3c_s1_challenger_characteristics_at_1():
    """s1_challenger.py:137, vol != vol or mom != mom -> and (NaN vol only)."""
    dates = _days(260)
    t = dates[-1]
    j = 259
    closes = [2.0] * 260
    closes[j - 2] = float("nan")
    assert characteristics_at(dates, closes, t) is None


def test_mut3c_s1_challenger_characteristics_at_2():
    """s1_challenger.py:130, p1 <= 0 -> p1 <= 1 (last close 0.5)."""
    dates = _days(260)
    t = dates[-1]
    j = 259
    closes = [2.0] * 260
    closes[j - 1] = 0.5
    got = characteristics_at(dates, closes, t)
    assert got is not None
    assert got["rev_21"] == math.log(0.5 / 2.0)
    assert got["mom_12_1"] == math.log(2.0 / 2.0)


def test_mut3c_s1_challenger_estimability_1():
    """s1_challenger.py:180, n_char == 3 -> != 3 (characteristics_eq_3)."""
    months = {f"m{i:02d}": 1 for i in range(MIN_TRAIN_MONTHS)}
    est = estimability({"admitted_count": 30}, months)
    assert est["checks"]["characteristics_eq_3"] is True
    assert est["estimable"] is True


def test_mut3c_s1_challenger_estimability_2():
    """s1_challenger.py:181, n_months >= MIN_TRAIN_MONTHS -> > (exactly 60)."""
    months = {f"m{i:02d}": 1 for i in range(MIN_TRAIN_MONTHS)}
    est = estimability({"admitted_count": 30}, months)
    assert est["train_months_with_valid_cross_section"] == 60
    assert est["checks"]["train_months_ge_60"] is True
    assert est["estimable"] is True


def test_mut3c_s1_challenger_estimability_3():
    """s1_challenger.py:180, n_char == 3 with literal 3 -> 4."""
    months = {f"m{i:02d}": 1 for i in range(MIN_TRAIN_MONTHS)}
    est = estimability({"admitted_count": 30}, months)
    assert est["characteristics"] == 3
    assert est["checks"]["characteristics_eq_3"] is True
    assert est["thresholds"]["n_characteristics"] == 3


def test_mut3c_s1_challenger_month_key_1():
    """s1_challenger.py:169, return f'{d.year:04d}-{d.month:02d}' -> return None."""
    assert month_key(date(2024, 3, 5)) == "2024-03"
    assert month_key(date(2012, 1, 31)) == "2012-01"


def test_mut3c_s1_challenger_build_universe_1():
    """s1_challenger.py:52, rejected no_adjusted_close_column 0 -> 1."""
    store = InjectableStore({})
    u = build_universe(store, lambda p: "blob", [date(2012, 1, 3)])
    assert u["rejected_by_reason"]["no_adjusted_close_column"] == 0
    assert u["admitted_count"] == 0
    assert u["files_examined"] == 0


def test_mut3c_s1_challenger_build_universe_2():
    """s1_challenger.py:80, coverage intersection / n_sessions -> *."""
    first = date(2012, 1, 3)
    last = MIN_LAST_DATE
    file_dates = [first, last]
    sessions = [first] + [date(2020, 1, 1) + timedelta(days=i) for i in range(40)] + [last]
    store = InjectableStore({
        "data/yahoo/SPARSE.parquet": {"Date": file_dates, "close": [1.0, 1.0]},
    })
    u = build_universe(store, lambda p: "blob", sessions)
    assert u["admitted_count"] == 0
    assert u["rejected_by_reason"]["low_session_coverage"] == 1


def test_mut3c_s1_challenger_build_universe_3():
    """s1_challenger.py:77, dates[-1] < MIN_LAST_DATE -> <= (last == boundary)."""
    first = date(2012, 1, 3)
    last = MIN_LAST_DATE
    dates = [first, last]
    store = InjectableStore({
        "data/yahoo/EDGE.parquet": {"Date": dates, "close": [1.0, 1.0]},
    })
    u = build_universe(store, lambda p: "blob", dates)
    assert u["admitted_count"] == 1
    assert u["rejected_by_reason"]["stale_last_date"] == 0
    assert u["admitted"][0]["last_index_date"] == last.isoformat()


def test_mut3c_s1_challenger_build_universe_4():
    """s1_challenger.py:61, examined += 1 -> += 2 (one skipped SPY file)."""
    store = InjectableStore({
        "data/yahoo/SPY.parquet": {"Date": [date(2012, 1, 3)], "close": [1.0]},
    })
    u = build_universe(store, lambda p: "blob", [date(2012, 1, 3)])
    assert u["files_examined"] == 1
    assert u["rejected_by_reason"]["skipped_benchmark_or_subject"] == 1
    assert u["admitted_count"] == 0
