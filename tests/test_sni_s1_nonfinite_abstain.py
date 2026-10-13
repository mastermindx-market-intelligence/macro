"""MNZ-F3 / MNZ-F1: a non-finite close is unusable; a drop is counted.

Synthetic fixtures only. This file never mints identity ids and never feeds a
rank, gate, size, signal, escalation, or trade path. Authority flags stay
literal false.

s1_decomposition / s1_data are SNI-local DRAFT contract consumers of
caller-supplied closes; identity ids stay owner-supplied opaque strings.
"""
from __future__ import annotations

import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/residual"))

import s1_data  # noqa: E402
import s1_decomposition  # noqa: E402

BAD_KINDS = (
    ("nan", float("nan")),
    ("pinf", float("inf")),
    ("ninf", float("-inf")),
    ("zero", 0.0),
    ("neg", -3.25),
)


def _weekdays(n: int, start: date = date(2020, 1, 6)) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def _canon_map(m: dict) -> bytes:
    payload = [[_iso(d), float(v)] for d, v in sorted(m.items(), key=lambda kv: _iso(kv[0]))]
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _ref_daily_log_returns(closes, dates):
    out = {}
    prev_d = None
    for d in dates:
        c = closes.get(d)
        if c is None or c <= 0:
            prev_d = None
            continue
        if prev_d is not None:
            p = closes.get(prev_d)
            if p is not None and p > 0:
                out[d] = float(np.log(c / p))
        prev_d = d
    return out


def _ref_window_log_ret(closes, fill, coverage):
    a, b = closes.get(fill), closes.get(coverage)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return float(np.log(b / a))


def _ref_closes_from_frame(dates, values):
    out = {}
    for d, v in zip(dates, values):
        if v is None:
            continue
        fv = float(v)
        if fv != fv:
            continue
        out[d] = fv
    return dates, out


def _mutant_keep_inf(dates, values, *, drops=None):
    out = {}
    n_null = 0
    n_nan = 0
    n_nonfinite = 0
    dropped = []
    for d, v in zip(dates, values):
        iso = _iso(d)
        if v is None:
            n_null += 1
            dropped.append(iso)
            continue
        fv = float(v)
        if fv != fv:
            n_nan += 1
            dropped.append(iso)
            continue
        if not math.isfinite(fv):
            n_nonfinite += 1
            out[d] = fv
            continue
        out[d] = fv
    if drops is not None:
        drops["null"] = n_null
        drops["nan"] = n_nan
        drops["nonfinite"] = n_nonfinite
        drops["dates"] = sorted(dropped)
    return dates, out


def _mutant_no_nan_count(dates, values, *, drops=None):
    out = {}
    n_null = 0
    n_nonfinite = 0
    dropped = []
    for d, v in zip(dates, values):
        iso = _iso(d)
        if v is None:
            n_null += 1
            dropped.append(iso)
            continue
        fv = float(v)
        if fv != fv:
            dropped.append(iso)
            continue
        if not math.isfinite(fv):
            n_nonfinite += 1
            dropped.append(iso)
            continue
        out[d] = fv
    if drops is not None:
        drops["null"] = n_null
        drops["nan"] = 0
        drops["nonfinite"] = n_nonfinite
        drops["dates"] = sorted(dropped)
    return dates, out


def _assert_s1nf_01() -> None:
    dates = _weekdays(7)
    hole = dates[3]
    nxt = dates[4]
    for _name, bad in BAD_KINDS:
        closes = {d: 10.0 + i for i, d in enumerate(dates)}
        closes[hole] = bad
        out = s1_decomposition.daily_log_returns(closes, dates)
        assert hole not in out
        assert nxt not in out
        assert all(math.isfinite(v) for v in out.values())
        for v in out.values():
            assert v == v


def _assert_s1nf_02() -> None:
    fill, coverage = date(2020, 1, 6), date(2020, 1, 10)
    good = 12.5
    kinds = list(BAD_KINDS) + [("none", None)]
    for _name, bad in kinds:
        at_fill = s1_decomposition.window_log_ret(
            {fill: bad, coverage: good}, fill, coverage
        )
        at_cov = s1_decomposition.window_log_ret(
            {fill: good, coverage: bad}, fill, coverage
        )
        assert at_fill is None
        assert at_cov is None


def _assert_s1nf_03() -> None:
    for seed in range(50):
        rng = random.Random(seed)
        n = rng.randint(12, 40)
        dates = _weekdays(n, date(2019, 1, 2) + timedelta(days=rng.randint(0, 400)))
        values = []
        exp_null = 0
        exp_nan = 0
        exp_nonfinite = 0
        exp_dates = []
        forced = ["null", "nan", "pinf", "ninf", "good", "zero", "neg"]
        rest = [rng.choice(forced) for _ in range(n - len(forced))]
        kinds = forced + rest
        rng.shuffle(kinds)
        kinds = kinds[:n]
        for d, kind in zip(dates, kinds):
            if kind == "null":
                values.append(None)
                exp_null += 1
                exp_dates.append(_iso(d))
            elif kind == "nan":
                values.append(float("nan"))
                exp_nan += 1
                exp_dates.append(_iso(d))
            elif kind == "pinf":
                values.append(float("inf"))
                exp_nonfinite += 1
                exp_dates.append(_iso(d))
            elif kind == "ninf":
                values.append(float("-inf"))
                exp_nonfinite += 1
                exp_dates.append(_iso(d))
            elif kind == "zero":
                values.append(0.0)
            elif kind == "neg":
                values.append(-abs(rng.uniform(0.1, 9.0)))
            else:
                values.append(float(rng.uniform(1.0, 80.0)))
        drops = {}
        got_dates, cmap = s1_data.closes_from_frame(dates, values, drops=drops)
        assert got_dates is dates or list(got_dates) == list(dates)
        assert drops["null"] == exp_null
        assert drops["nan"] == exp_nan
        assert drops["nonfinite"] == exp_nonfinite
        assert drops["dates"] == sorted(exp_dates)
        assert drops["dates"] == sorted(drops["dates"])
        assert len(drops["dates"]) == exp_null + exp_nan + exp_nonfinite
        for v in cmap.values():
            assert math.isfinite(v)
        _, cmap_plain = s1_data.closes_from_frame(dates, values)
        assert cmap_plain == cmap


def _assert_s1nf_04() -> None:
    rng = random.Random(20261013)
    for _ in range(40):
        n = rng.randint(6, 24)
        dates = _weekdays(n, date(2018, 6, 4) + timedelta(days=rng.randint(0, 300)))
        closes = {}
        values = []
        p = rng.uniform(5.0, 120.0)
        for d in dates:
            p *= math.exp(rng.uniform(-0.03, 0.03))
            p = max(p, 1e-3)
            closes[d] = float(p)
            values.append(float(p))
        got_d = s1_decomposition.daily_log_returns(closes, dates)
        ref_d = _ref_daily_log_returns(closes, dates)
        assert _canon_map(got_d) == _canon_map(ref_d)
        fill, coverage = dates[0], dates[-1]
        got_w = s1_decomposition.window_log_ret(closes, fill, coverage)
        ref_w = _ref_window_log_ret(closes, fill, coverage)
        assert json.dumps(got_w).encode("utf-8") == json.dumps(ref_w).encode("utf-8")
        _, got_c = s1_data.closes_from_frame(dates, values)
        _, ref_c = _ref_closes_from_frame(dates, values)
        assert _canon_map(got_c) == _canon_map(ref_c)


def test_s1nf_01():
    _assert_s1nf_01()


def test_s1nf_02():
    _assert_s1nf_02()


def test_s1nf_03():
    _assert_s1nf_03()


def test_s1nf_04():
    _assert_s1nf_04()


@pytest.mark.parametrize("mutant_id", ["m1", "m2", "m3"])
def test_s1nf_05_mutants_are_caught(mutant_id, monkeypatch):
    if mutant_id == "m1":
        monkeypatch.setattr(
            s1_decomposition,
            "_usable_close",
            lambda c: c is not None and float(c) > 0,
        )
    elif mutant_id == "m2":
        monkeypatch.setattr(s1_data, "closes_from_frame", _mutant_keep_inf)
    elif mutant_id == "m3":
        monkeypatch.setattr(s1_data, "closes_from_frame", _mutant_no_nan_count)
    else:
        raise AssertionError(mutant_id)

    caught = False
    for fn in (_assert_s1nf_01, _assert_s1nf_02, _assert_s1nf_03, _assert_s1nf_04):
        try:
            fn()
        except AssertionError:
            caught = True
            break
    assert caught, "%s did not make any of s1nf_01..04 fail" % mutant_id
