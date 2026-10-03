"""The column-wise substrate fingerprint returns the digest the cell-by-cell loop returned."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

import engine.entry_radar.live_pack as lp
from engine.entry_radar import challengers as ch
from engine.entry_radar.entry_events import sha16

IDX = pd.date_range("2026-01-05", periods=6, freq="B")


def _base() -> pd.DataFrame:
    return pd.DataFrame({"high": [1.5, 2, 3, 4, 5, 6.25], "low": [1, 1.5, 2, 3, 4, 5],
                         "close": [1.2, 1.7, 2.5, 3.5, 4.5, 5.5]}, index=IDX)


def _nonfinite() -> pd.DataFrame:
    x = _base()
    x.iloc[1, 0] = np.nan
    x.iloc[2, 1] = np.inf
    x.iloc[3, 2] = -np.inf
    return x


def _object() -> pd.DataFrame:
    x = _base().astype(object)
    x.iloc[0, 0] = "7.5"
    x.iloc[1, 1] = None
    x.iloc[2, 2] = "abc"
    return x


def _tz() -> pd.DataFrame:
    x = _base()
    x.index = x.index.tz_localize("America/New_York")
    return x


def _nat() -> pd.DataFrame:
    x = _base()
    x.index = pd.DatetimeIndex(list(IDX[:5]) + [pd.NaT])
    return x


def _extra() -> pd.DataFrame:
    x = _base()
    x["extra"] = 1.0
    return x[["extra", "close", "low", "high"]]


FAST = {
    "plain": _base,
    "nonfinite": _nonfinite,
    "empty": lambda: _base().iloc[:0],
    "int": lambda: _base().round().astype("int64"),
    "float32": lambda: _base().astype("float32"),
    "tz": _tz,
    "extra_col": _extra,
}
SLOW = {
    "object": _object,
    "nat": _nat,
    "Int64": lambda: _base().round().astype("Int64"),
    "bool": lambda: _base() > 2,
}
#: Digests the cell-by-cell loop produced on main before the column-wise builder existed.
PINNED = {
    "plain": "44483a571b3adaeb",
    "nonfinite": "a39b805ea1cf62f2",
    "empty": "4f53cda18c2baa0c",
    "int": "c4270da38bbc1ac8",
    "float32": "a253be7407ce1ffc",
    "tz": "44483a571b3adaeb",
    "extra_col": "44483a571b3adaeb",
    "object": "e54dfeff6e3d8bbd",
    "nat": "4fdddab3296c2ac2",
    "Int64": "c4270da38bbc1ac8",
    "bool": "0c02b53397d1b5d5",
}


@pytest.mark.parametrize("name", sorted(FAST))
def test_fast_rows_equal_reference_rows(name):
    frame = FAST[name]()
    fast = lp._fingerprint_rows_fast(frame)
    assert fast is not None
    assert json.dumps(fast) == json.dumps(lp._fingerprint_rows_slow(frame))


@pytest.mark.parametrize("name", sorted(SLOW))
def test_odd_frames_use_the_reference_rows(name):
    frame = SLOW[name]()
    assert lp._fingerprint_rows_fast(frame) is None
    assert lp.substrate_fingerprint(frame) == sha16(lp._fingerprint_rows_slow(frame))


@pytest.mark.parametrize("name", sorted(PINNED))
def test_digests_are_the_ones_the_old_loop_produced(name):
    make = FAST.get(name) or SLOW[name]
    assert lp.substrate_fingerprint(make()) == PINNED[name]


def test_non_finite_cells_are_none_and_the_rest_are_floats():
    rows = lp._fingerprint_rows_fast(_nonfinite())
    assert rows[0] == ["2026-01-05", 1.5, 1.0, 1.2]
    assert rows[1][1] is None and rows[2][2] is None and rows[3][3] is None
    cells = [cell for row in rows for cell in row[1:]]
    assert sum(cell is None for cell in cells) == 3
    assert all(type(cell) is float for cell in cells if cell is not None)


def test_random_frames_agree():
    rng = np.random.default_rng(20261003)
    for _ in range(40):
        n = int(rng.integers(0, 400))
        values = rng.normal(100.0, 20.0, (n, 3))
        values[rng.random((n, 3)) < 0.03] = np.nan
        values[rng.random((n, 3)) < 0.01] = np.inf
        values[rng.random((n, 3)) < 0.01] = -np.inf
        frame = pd.DataFrame(values, index=pd.bdate_range("2020-01-01", periods=n),
                             columns=["high", "low", "close"])
        fast = lp._fingerprint_rows_fast(frame)
        assert fast is not None
        assert json.dumps(fast) == json.dumps(lp._fingerprint_rows_slow(frame))


def test_frozen_frames_take_the_fast_path():
    frame = _base().round().astype("int64")
    frozen = lp._frozen_frame(frame, ticker="AAA", next_session=date(2026, 1, 20),
                              price_basis=ch.BASIS_ADJUSTED, vintage="")
    assert len(frozen) == 6
    assert lp._fingerprint_rows_fast(frozen) is not None


def test_plain_frames_never_touch_the_reference_builder(monkeypatch):
    def boom(frame):
        raise AssertionError("reference builder used for a plain frame")

    monkeypatch.setattr(lp, "_fingerprint_rows_slow", boom)
    assert lp.substrate_fingerprint(_base()) == PINNED["plain"]
