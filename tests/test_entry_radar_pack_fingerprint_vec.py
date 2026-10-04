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


def _neg_zero() -> pd.DataFrame:
    x = _base()
    x.iloc[0, 0] = -0.0
    x.iloc[4, 2] = 0.0
    return x


def _tz_shift() -> pd.DataFrame:
    x = _base()
    x.index = pd.date_range("2026-01-05 23:30", periods=6, freq="D", tz="UTC").tz_convert(
        "Pacific/Kiritimati"
    )
    return x


def _v2_oracle(frame: pd.DataFrame) -> str:
    """Cell-by-cell v2 tokenisation: UTC ISO timestamps, distinct non-finite tokens."""
    return sha16(lp._fingerprint_rows_slow(frame))


FAST = {
    "plain": _base,
    "nonfinite": _nonfinite,
    "int": lambda: _base().round().astype("int64"),
    "float32": lambda: _base().astype("float32"),
    "tz": _tz,
    "extra_col": _extra,
    "neg_zero": _neg_zero,
    "tz_shift": _tz_shift,
}
SLOW = {
    "object": _object,
    "nat": _nat,
    "Int64": lambda: _base().round().astype("Int64"),
    "bool": lambda: _base() > 2,
    "empty": lambda: _base().iloc[:0],
    "empty_no_columns": lambda: pd.DataFrame(index=pd.DatetimeIndex([])),
    "empty_missing_close": lambda: pd.DataFrame({"high": [], "low": []}, index=pd.DatetimeIndex([])),
}
#: Digests the v2 cell-by-cell oracle produces for each fixture.
PINNED = {
    "plain": "9f003a10a4c7cafa",
    "nonfinite": "26705722a8c79245",
    "empty": "4f53cda18c2baa0c",
    "int": "e1b917eac4a8ba12",
    "float32": "078af53dec13ad02",
    "tz": "069e2a4c4b77abca",
    "extra_col": "9f003a10a4c7cafa",
    "object": "8f79633aa5e8fe1f",
    "nat": "0e0019ca425702de",
    "Int64": "e1b917eac4a8ba12",
    "bool": "418c923ef370865d",
    "neg_zero": "69754f96a38c6309",
    "tz_shift": "e629bfb49d953a04",
    "empty_no_columns": "4f53cda18c2baa0c",
    "empty_missing_close": "4f53cda18c2baa0c",
}
#: Legacy v1 digests (date-only index, non-finite as None) — still verified at load.
PINNED_V1 = {
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
    "neg_zero": "769250833a213528",
    "tz_shift": "abbee96a52d6de99",
    "empty_no_columns": "4f53cda18c2baa0c",
    "empty_missing_close": "4f53cda18c2baa0c",
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
def test_digests_are_the_ones_the_v2_oracle_produced(name):
    make = FAST.get(name) or SLOW[name]
    assert lp.substrate_fingerprint(make()) == PINNED[name]


@pytest.mark.parametrize("name", sorted(FAST) + sorted(SLOW))
def test_every_fixture_equals_the_v2_oracle(name):
    frame = (FAST.get(name) or SLOW[name])()
    assert lp.substrate_fingerprint(frame) == _v2_oracle(frame)


@pytest.mark.parametrize("name", sorted(PINNED_V1))
def test_v1_legacy_digests_remain_pinned(name):
    make = FAST.get(name) or SLOW[name]
    assert lp._substrate_fingerprint_v1(make()) == PINNED_V1[name]


def test_neg_zero_and_local_date_are_distinguished():
    neg = _neg_zero()
    assert lp.substrate_fingerprint(neg) != lp.substrate_fingerprint(_base())
    plain_neg = _base()
    plain_neg.iloc[0, 0] = 0.0
    plain_neg.iloc[4, 2] = 0.0
    assert lp.substrate_fingerprint(neg) != lp.substrate_fingerprint(plain_neg)
    tz_frame = _tz_shift()
    utc_frame = tz_frame.copy()
    utc_frame.index = utc_frame.index.tz_convert("UTC")
    assert lp.substrate_fingerprint(tz_frame) == lp.substrate_fingerprint(utc_frame)
    with pytest.raises(lp.LivePackError, match="substrate_index_not_normalized"):
        lp._refuse_substrate_index_not_normalized(_tz_shift(), ticker="X")


def test_nonempty_frame_missing_a_column_raises_like_the_oracle():
    frame = _base().drop(columns=["low"])
    with pytest.raises(KeyError):
        lp.substrate_fingerprint(frame)
    with pytest.raises(KeyError):
        _v2_oracle(frame)


def test_non_finite_cells_use_distinct_tokens_and_the_rest_are_floats():
    rows = lp._fingerprint_rows_fast(_nonfinite())
    assert rows[0][0].startswith("2026-01-05T00:00:00")
    assert rows[1][1] == "nan" and rows[2][2] == "+inf" and rows[3][3] == "-inf"
    cells = [cell for row in rows for cell in row[1:]]
    assert sum(cell in ("nan", "+inf", "-inf") for cell in cells) == 3
    assert all(type(cell) is float for cell in cells if cell not in ("nan", "+inf", "-inf"))


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
        if n == 0:
            assert fast is None
            continue
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
