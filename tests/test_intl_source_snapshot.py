"""Content identity of supplied closes; no source qualification or data fetching."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import socket
import time

import numpy as np
import pandas as pd
import pytest

from engine import intl_inputs
from lib import store


@pytest.fixture(autouse=True)
def forbid_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("snapshot attempted store, network or wall clock access")
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(store, "upsert", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "time", forbidden)


@pytest.fixture
def small_config(monkeypatch):
    cfg = {"A": {"index": "IDX", "fx": "FX", "indices": {"IDX": "Primary", "OTHER": "Secondary"}},
           "B": {"index": "BIDX", "fx": "FX"}}
    monkeypatch.setattr(intl_inputs, "countries", lambda: deepcopy(cfg))
    return {"IDX": "adjusted", "FX": "spot", "BIDX": "adjusted"}


def snapshot(frame, bases, ref="fixture:closes"):
    return intl_inputs.source_snapshot(frame, source_reference=ref, adjustment_bases=bases)


def frame(values, *, column="IDX", dtype=object):
    return pd.DataFrame({column: pd.Series(values, index=pd.date_range("2026-10-01", periods=len(values)), dtype=dtype)})


def test_literal_digest_large_integer_signed_zero_null_and_nanosecond_timezone(monkeypatch):
    monkeypatch.setattr(intl_inputs, "countries", lambda: {"A": {"index": "IDX", "fx": "FX"}})
    dates = pd.date_range("2026-10-01 09:30:00.000000123", periods=3, tz="Asia/Tokyo")
    supplied = pd.DataFrame({"IDX": pd.Series([9007199254740993, -0.0, None], index=dates, dtype=object)})
    actual = snapshot(supplied, {"IDX": "adjusted", "FX": "spot"})
    # Literal canonical wire vector: independently written, not generated from output.
    wire = b'[["IDX","adjusted",[["2026-10-01T09:30:00.000000123+09:00","i:9007199254740993"],["2026-10-02T09:30:00.000000123+09:00","f:-0x0.0p+0"],["2026-10-03T09:30:00.000000123+09:00",null]]],["FX","spot",[]]]'
    assert hashlib.sha256(wire).hexdigest() == "ecc0682feee575a791e02fd9e72b7e31f5ca65c32d4783e4e1a7abe29a19cb30"
    assert actual["content_sha256"] == hashlib.sha256(wire).hexdigest()
    assert actual["series"][0]["observations"] == [
        {"timestamp": dates[0].isoformat(), "value": 9007199254740993},
        {"timestamp": dates[1].isoformat(), "value": -0.0},
        {"timestamp": dates[2].isoformat(), "value": None},
    ]
    assert actual["series"][1]["observations"] == []


def test_real_seven_market_primary_and_fx_order_excludes_secondary_indices():
    cfg = intl_inputs.countries()
    assert list(cfg) == ["JP", "KR", "TW", "IN", "AU", "GB", "EZ"]
    expected = ["^N225", "USDJPY=X", "^KS11", "USDKRW=X", "^TWII", "USDTWD=X",
                "^NSEI", "USDINR=X", "^AXJO", "AUDUSD=X", "^FTSE", "GBPUSD=X", "^STOXX", "EURUSD=X"]
    actual = snapshot(pd.DataFrame(index=pd.DatetimeIndex([])), {s: "fixture" for s in expected})
    assert [s["series_id"] for s in actual["series"]] == expected
    assert all(s["observations"] == [] for s in actual["series"])


def test_deduplicated_identity_missing_column_and_null_rows(small_config):
    actual = snapshot(frame([None, pd.NA, np.nan, np.float32("nan")]), small_config)
    assert [s["series_id"] for s in actual["series"]] == ["IDX", "FX", "BIDX"]
    assert [o["value"] for o in actual["series"][0]["observations"]] == [None] * 4
    assert actual["series"][1]["observations"] == []


@pytest.mark.parametrize("values,expected", [
    ([np.int64(2**53 + 1), np.uint64(2**64 - 1)], [2**53 + 1, 2**64 - 1]),
    ([np.float32(1.25), np.float64(-2.5)], [1.25, -2.5]),
])
def test_numpy_scalars_become_plain_without_integer_loss(small_config, values, expected):
    actual = snapshot(frame(values), small_config)
    result = [o["value"] for o in actual["series"][0]["observations"]]
    assert result == expected
    assert all(type(v) in (int, float) for v in result)
    json.dumps(actual, allow_nan=False)


def test_nullable_integer_dtype_preserves_large_integer_and_missing(small_config):
    actual = snapshot(frame([2**63 - 1, None], dtype="Int64"), small_config)
    assert [o["value"] for o in actual["series"][0]["observations"]] == [2**63 - 1, None]


@pytest.mark.parametrize("value", [True, np.bool_(False), "1.0", float("inf"), -float("inf"),
                                   complex(1, 2), complex(float("nan"), 0), date(2026, 1, 1),
                                   pd.Timestamp("2026-01-01"), pd.NaT, object(), [1], {"x": 1}])
def test_rejects_non_close_scalar(small_config, value):
    with pytest.raises(ValueError):
        snapshot(frame([value]), small_config)


@pytest.mark.parametrize("index", [pd.Index([1]), pd.DatetimeIndex([pd.NaT]),
                                   pd.DatetimeIndex(["2026-01-01", "2026-01-01"]),
                                   pd.DatetimeIndex(["2026-01-02", "2026-01-01"])])
def test_rejects_bad_chronology(small_config, index):
    with pytest.raises(ValueError):
        snapshot(pd.DataFrame({"IDX": [1] * len(index)}, index=index), small_config)


def test_rejects_duplicate_columns_even_when_unconfigured(small_config):
    supplied = pd.DataFrame([[1, 2]], columns=["OTHER", "OTHER"], index=pd.date_range("2026-01-01", periods=1))
    with pytest.raises(ValueError):
        snapshot(supplied, small_config)


@pytest.mark.parametrize("value", [None, [], {"IDX": "adjusted"},
                                   {"IDX": "adjusted", "FX": "spot", "BIDX": ""},
                                   {"IDX": "adjusted", "FX": "spot", "BIDX": 1},
                                   {"IDX": "adjusted", "FX": "spot", "BIDX": "adjusted", "OTHER": "x"}])
def test_rejects_nonexact_basis_mapping(small_config, value):
    with pytest.raises(ValueError):
        snapshot(frame([1]), value)


@pytest.mark.parametrize("ref", [None, "", "  ", 7, b"source"])
def test_requires_explicit_source_reference(small_config, ref):
    with pytest.raises(ValueError):
        snapshot(frame([1]), small_config, ref=ref)


@pytest.mark.parametrize("supplied", [None, [], {}, pd.Series([1])])
def test_requires_dataframe(small_config, supplied):
    with pytest.raises(ValueError):
        snapshot(supplied, small_config)


def test_content_identity_differs_by_number_kind_zero_sign_basis_time(small_config):
    outputs = [snapshot(frame([v]), small_config) for v in [0, 0.0, -0.0, 1, 1.0]]
    assert len({r["content_sha256"] for r in outputs}) == 5
    base = snapshot(frame([1]), small_config)
    bases = {**small_config, "FX": "revised"}
    assert snapshot(frame([1]), bases)["content_sha256"] != base["content_sha256"]
    shifted = frame([1]); shifted.index += pd.Timedelta(1, "ns")
    assert snapshot(shifted, small_config)["content_sha256"] != base["content_sha256"]


def test_source_label_unconfigured_columns_and_frame_order_do_not_change_digest(small_config):
    supplied = frame([1, 2]); expected = snapshot(supplied, small_config)
    supplied["IGNORED"] = [object(), object()]
    different = snapshot(supplied[["IGNORED", "IDX"]], small_config, ref="other:reference")
    assert different["content_sha256"] == expected["content_sha256"]
    assert different["source_reference"] == "other:reference"


def test_input_nonmutation_and_no_output_alias(small_config):
    supplied = frame([2**53 + 1, None]); before = supplied.copy(deep=True); bases = deepcopy(small_config)
    result = snapshot(supplied, small_config)
    result["series"][0]["observations"][0]["value"] = 0
    pd.testing.assert_frame_equal(supplied, before)
    assert small_config == bases
    assert snapshot(supplied, small_config)["series"][0]["observations"][0]["value"] == 2**53 + 1


def test_dst_repeated_local_hour_is_ordered_by_distinct_instants(small_config):
    dates = pd.date_range("2026-11-01 05:30:00", periods=2, freq="h", tz="UTC").tz_convert("America/New_York")
    actual = snapshot(pd.DataFrame({"IDX": [1, 2]}, index=dates), small_config)
    assert [o["timestamp"] for o in actual["series"][0]["observations"]] == [
        "2026-11-01T01:30:00-04:00", "2026-11-01T01:30:00-05:00"]


def test_structured_extra_column_does_not_partially_match_primary_id(small_config):
    dates = pd.date_range("2026-01-01", periods=1)
    supplied = pd.DataFrame([[99]], index=dates,
                            columns=pd.MultiIndex.from_tuples([("IDX", "secondary")]))
    actual = snapshot(supplied, small_config)
    assert all(row["observations"] == [] for row in actual["series"])
    assert actual["content_sha256"] == snapshot(pd.DataFrame(index=dates), small_config)["content_sha256"]


def test_exact_string_column_is_preserved_beside_structured_extra(small_config):
    dates = pd.date_range("2026-01-01", periods=1)
    supplied = pd.DataFrame([[99, 1.25]], index=dates, columns=[("IDX", "secondary"), "FX"])
    actual = snapshot(supplied, small_config)
    assert actual["series"][0]["observations"] == []
    assert actual["series"][1]["observations"] == [{"timestamp": "2026-01-01T00:00:00", "value": 1.25}]


@pytest.mark.parametrize("sign", [1, -1])
def test_integer_identity_has_no_process_decimal_digit_cap(small_config, sign):
    import sys
    before = sys.get_int_max_str_digits()
    large = sign * 10**5000
    actual = snapshot(frame([large]), small_config)
    token = "i:" + ("-" if sign < 0 else "") + "1" + "0" * 5000
    wire = [["IDX", "adjusted", [["2026-10-01T00:00:00", token]]],
            ["FX", "spot", []], ["BIDX", "adjusted", []]]
    expected = hashlib.sha256(json.dumps(wire, separators=(",", ":")).encode()).hexdigest()
    assert actual["content_sha256"] == expected
    assert actual["series"][0]["observations"][0]["value"] == large
    assert sys.get_int_max_str_digits() == before
