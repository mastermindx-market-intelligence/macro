"""Independent C2 projector tests. Product sources are imported, never edited."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import international_macro_dashboard as owner
from lib.intl_workspace_history import build_history_section, _validate as validate_history


ERROR = "invalid_history_read_projection"
FIXED = ValueError(ERROR)
READ_AT = "2026-10-08T01:02:03.000456789+05:30"


def receipt(status="ready", frame=None, **overrides):
    values = {
        "status": status,
        "market_id": "JP" if status != "unsupported" else None,
        "artifact_ref": "intl_regime/JP_history.parquet",
        "read_at": "2026-10-08T01:02:03+05:30",
        "method_ref": "method-v1",
        "frame": frame,
    }
    values.update(overrides)
    return values


def utc_index(*stamps):
    return pd.DatetimeIndex(list(stamps), tz="UTC")


def frame_of(growth, inflation, index=None):
    if index is None:
        index = utc_index("2026-01-01T00:00:00+00:00")
    return pd.DataFrame({"growth_score": growth, "inflation_score": inflation}, index=index)


def history_args(history_read):
    return dict(
        context={
            "selected_market": "JP",
            "horizon": "3m",
            "currency_basis": "local",
            "return_basis": "price",
        },
        history_read=history_read,
        turn_events=[],
        track_record=None,
        capabilities={
            "history_source": {"metadata": "allowed", "value": "allowed"},
            "events": {"metadata": "denied", "value": "unknown"},
            "track_record": {"metadata": "denied", "value": "unknown"},
            "snapshot_compare": {
                "left_observation_at": None,
                "right_observation_at": None,
            },
        },
        destinations={},
    )


def project(frame=None, **overrides):
    return owner.project_history_read(receipt(frame=frame, **overrides))


def assert_fixed(call):
    with pytest.raises(ValueError) as caught:
        call()
    assert caught.value.args == (ERROR,)
    assert caught.value.__cause__ is None


def test_object_true_is_mapping_failure_not_one():
    frame = frame_of(np.array([True], dtype=object), np.array([0], dtype=object))
    assert_fixed(lambda: project(frame))


def test_numpy_bool_column_is_mapping_failure():
    frame = frame_of(np.array([np.bool_(False)]), np.array([0.0]))
    assert_fixed(lambda: project(frame))


def test_status_empty_list_is_fixed_valueerror():
    frame = frame_of([], [], index=pd.DatetimeIndex([], tz="UTC"))
    assert_fixed(lambda: project(frame, status=[]))


def test_list_score_and_dict_score_use_fixed_error():
    index = utc_index("2026-01-01T00:00:00+00:00")
    for value in ([1, 2], {"private": 5}):
        frame = pd.DataFrame(
            {
                "growth_score": pd.array([value], dtype=object),
                "inflation_score": pd.array([0], dtype=object),
            },
            index=index,
        )
        assert_fixed(lambda frame=frame: project(frame))


def test_int64_with_float_companion_keeps_exact_integer():
    value = 9007199254740993
    frame = pd.DataFrame(
        {"growth_score": pd.array([value], dtype="int64"), "inflation_score": [0.5]},
        index=utc_index("2026-01-01T00:00:00+00:00"),
    )
    row = frame.iloc[0]["growth_score"]
    assert type(row) is np.float64 and row == 9007199254740992.0
    out = project(frame)
    point = out["points"][0]
    assert type(point["growth_score"]) is int
    assert point["growth_score"] == value
    assert point["inflation_score"] == 0.5
    view = build_history_section(**history_args(out))
    assert view["points"][0]["growth_score"] == value


def test_custom_int_and_float_subclasses_do_not_run_conversions():
    calls = []

    class EvilInt(int):
        def __int__(self):
            calls.append("int")
            return 77

        def __index__(self):
            calls.append("index")
            return 77

    class EvilFloat(float):
        def __float__(self):
            calls.append("float")
            return 77.0

    for value in (EvilInt(5), EvilFloat(5.0)):
        frame = frame_of(np.array([value], dtype=object), np.array([0], dtype=object))
        assert_fixed(lambda frame=frame: project(frame))
    assert calls == []


def test_nanosecond_timestamp_and_offset_reach_helper_unchanged():
    stamp = pd.Timestamp("2026-01-01T00:00:00.123456789+05:30").as_unit("ns")
    frame = frame_of([1], [None], index=pd.DatetimeIndex([stamp]))
    out = project(frame, read_at=READ_AT)
    assert out["points"][0]["observation_at"] == "2026-01-01T00:00:00.123456789+05:30"
    assert out["read_at"] == READ_AT
    view = build_history_section(**history_args(out))
    assert view["acquisition_at"] == READ_AT
    assert view["points"][0]["observation_at"] == "2026-01-01T00:00:00.123456789+05:30"


def test_all_rows_kept_in_index_order_without_sorting():
    index = pd.date_range("2026-01-01", periods=80, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {
            "growth_score": np.arange(80, dtype="int64"),
            "inflation_score": np.linspace(-1.0, 1.0, 80),
            "ignored": np.arange(80)[::-1],
        },
        index=index,
    )
    out = project(frame)
    assert len(out["points"]) == 80
    assert [p["growth_score"] for p in out["points"]] == list(range(80))
    assert out["points"][0]["observation_at"] == index[0].isoformat()
    assert out["points"][-1]["observation_at"] == index[-1].isoformat()


def test_unsorted_index_is_mapping_failure():
    frame = frame_of(
        [1, 2],
        [0, 0],
        index=pd.DatetimeIndex(
            ["2026-01-02T00:00:00+00:00", "2026-01-01T00:00:00+00:00"]
        ),
    )
    assert_fixed(lambda: project(frame))


def test_duplicate_index_and_nat_and_range_index_fail():
    good = utc_index("2026-01-01T00:00:00+00:00")
    cases = [
        frame_of([1, 2], [0, 0], index=pd.DatetimeIndex([good[0], good[0]])),
        frame_of([1], [0], index=pd.DatetimeIndex([pd.NaT], dtype="datetime64[ns, UTC]")),
        pd.DataFrame({"growth_score": [1], "inflation_score": [0]}),
    ]
    for frame in cases:
        assert_fixed(lambda frame=frame: project(frame))


def test_output_omits_frame_and_ignores_extra_columns():
    stamp = pd.Timestamp("2026-01-01T12:34:56.789123456+00:00").as_unit("ns")
    frame = pd.DataFrame(
        {
            "secret": ["do-not-copy"],
            "growth_score": [np.int64(1)],
            "inflation_score": [np.float64(2.0)],
            "last": [object()],
        },
        index=pd.DatetimeIndex([stamp]),
    )
    original = frame.copy(deep=True)
    out = project(frame)
    assert "frame" not in out
    assert set(out) == {
        "status",
        "market_id",
        "artifact_ref",
        "read_at",
        "method_ref",
        "identity",
        "points",
    }
    assert set(out["points"][0]) == {"observation_at", "growth_score", "inflation_score"}
    out["points"][0]["growth_score"] = 999
    out["market_id"] = "KR"
    pd.testing.assert_frame_equal(frame, original)
    assert json.dumps(project(frame), allow_nan=False)


def test_typed_receipt_rejects_custom_dict_and_dataframe_subclass():
    class CustomDict(dict):
        pass

    class AccessorFrame(pd.DataFrame):
        @property
        def iterrows(self):
            return lambda: pytest.fail("custom accessor invoked")

    frame = AccessorFrame(
        {"growth_score": [1], "inflation_score": [2]},
        index=utc_index("2026-01-01T00:00:00+00:00"),
    )
    assert_fixed(lambda: owner.project_history_read(CustomDict(receipt(frame=frame_of([1], [0])))))
    assert_fixed(lambda: project(frame))


def test_nullable_pandas_na_becomes_null_and_values_stay_python_scalars():
    index = utc_index("2026-01-01T00:00:00+00:00")
    frame = pd.DataFrame(
        {
            "growth_score": pd.array([1], dtype="Int64"),
            "inflation_score": pd.array([pd.NA], dtype="Float64"),
        },
        index=index,
    )
    out = project(frame)
    assert out["points"][0]["growth_score"] == 1
    assert type(out["points"][0]["growth_score"]) is int
    assert out["points"][0]["inflation_score"] is None


def test_nan_is_null_inf_and_string_are_mapping_failure():
    index = utc_index("2026-01-01T00:00:00+00:00")
    nan_frame = frame_of([np.nan], [0.0], index=index)
    out = project(nan_frame)
    assert out["points"][0]["growth_score"] is None
    for growth in (np.inf, float("-inf"), "1", pd.NaT):
        frame = frame_of(np.array([growth], dtype=object), np.array([0], dtype=object), index=index)
        assert_fixed(lambda frame=frame: project(frame))


def test_metadata_and_paths_delegate_to_helper_validate():
    empty = pd.DataFrame(
        {"growth_score": [], "inflation_score": []},
        index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"),
    )
    for overrides in (
        {"read_at": "2026-01-01T00:00:00"},
        {"read_at": "invalid"},
        {"artifact_ref": "/absolute/x.parquet"},
        {"artifact_ref": "a/../b"},
        {"artifact_ref": "x\\y"},
        {"market_id": " JP"},
        {"method_ref": "\tmethod"},
    ):
        values = receipt("empty", frame=empty)
        values.update(overrides)
        assert_fixed(lambda values=values: owner.project_history_read(values))
    ok = project(empty, status="empty", read_at=READ_AT)
    validate_history(
        {
            "selected_market": "JP",
            "horizon": "1m",
            "currency_basis": "local",
            "return_basis": "price",
        },
        ok,
        [],
        None,
        {
            **{
                key: {"metadata": "unknown", "value": "unknown"}
                for key in ("history_source", "events", "track_record")
            },
            "snapshot_compare": {
                "left_observation_at": None,
                "right_observation_at": None,
            },
        },
        {},
    )


def test_reader_shaped_empty_and_missing_receipts_are_distinct():
    empty_frame = pd.DataFrame(
        {"growth_score": [], "inflation_score": []},
        index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"),
    )
    empty = project(empty_frame, status="empty", method_ref=None)
    assert empty["status"] == "empty" and empty["points"] == []
    assert empty["identity"]["method_ref"] is None
    missing = owner.project_history_read(receipt("missing", frame=None, method_ref=None))
    assert missing["status"] == "missing" and missing["identity"] is None
    assert missing["points"] == []
    assert "frame" not in missing


def test_nonready_status_rejects_a_frame():
    frame = pd.DataFrame()
    for status in ("missing", "failed", "invalid", "unsupported"):
        assert_fixed(lambda status=status: project(frame, status=status))


def test_uint64_numpy_max_converts_to_python_int():
    frame = frame_of(
        np.array([np.uint64(18446744073709551615)], dtype="uint64"),
        np.array([np.uint64(0)], dtype="uint64"),
    )
    out = project(frame)
    assert out["points"][0]["growth_score"] == 18446744073709551615
    assert type(out["points"][0]["growth_score"]) is int


def test_numpy_longlong_column_stays_python_int():
    """Contract: integer scalars convert with int(); longlong is np.integer."""
    arr = np.array([5], dtype=np.longlong)
    frame = pd.DataFrame(
        {"growth_score": arr, "inflation_score": np.array([0], dtype=np.longlong)},
        index=utc_index("2026-01-01T00:00:00+00:00"),
    )
    assert type(frame["growth_score"].iloc[0]) is np.longlong
    out = project(frame)
    assert out["points"][0]["growth_score"] == 5
    assert type(out["points"][0]["growth_score"]) is int


def test_nullable_uint64_above_int64_max_stays_python_int():
    value = 2**63
    frame = pd.DataFrame(
        {
            "growth_score": pd.array([value], dtype="UInt64"),
            "inflation_score": pd.array([0], dtype="UInt64"),
        },
        index=utc_index("2026-01-01T00:00:00+00:00"),
    )
    raw = frame["growth_score"].iloc[0]
    assert isinstance(raw, np.unsignedinteger)
    out = project(frame)
    assert out["points"][0]["growth_score"] == value
    assert type(out["points"][0]["growth_score"]) is int


def test_no_clock_config_or_reader_side_effects(monkeypatch, tmp_path):
    frame = frame_of(np.array([1], dtype=object), np.array([None], dtype=object))
    forbidden = lambda *args, **kwargs: pytest.fail("unexpected side effect")
    monkeypatch.setattr(owner.config, "load", forbidden)
    monkeypatch.setattr(owner.config, "data_dir", forbidden)
    monkeypatch.setattr(owner, "load_history_result", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    monkeypatch.chdir(tmp_path)
    assert project(frame)["points"][0]["growth_score"] == 1


def test_explicit_unsigned_longlong_stays_exact():
    value = 2**64 - 1
    frame = frame_of(np.array([np.ulonglong(value)], dtype=object), np.array([0], dtype=object))
    out = project(frame)
    assert type(out["points"][0]["growth_score"]) is int
    assert out["points"][0]["growth_score"] == value


# Additional exact R2 reviewer challenge cases.
def _receipt(frame):
    return {
        "status": "ready",
        "market_id": "JP",
        "artifact_ref": "intl_regime/JP_history.parquet",
        "read_at": "2026-10-08T01:02:03+05:30",
        "method_ref": "method-v1",
        "frame": frame,
    }


def _blank():
    index = pd.DatetimeIndex(["2026-01-01T00:00:00+00:00"], tz="UTC")
    return pd.DataFrame(
        {
            "growth_score": np.array([object()], dtype=object),
            "inflation_score": np.array([0], dtype=object),
        },
        index=index,
    )


def test_numpy_integer_subclasses_do_not_run_conversions():
    calls = []

    class EvilInt64(np.int64):
        def __int__(self):
            calls.append("int64")
            return 77

        def __index__(self):
            calls.append("index64")
            return 77

    class EvilLong(np.longlong):
        def __int__(self):
            calls.append("longlong")
            return 77

        def __index__(self):
            calls.append("indexll")
            return 77

    class EvilULong(np.ulonglong):
        def __int__(self):
            calls.append("ulonglong")
            return 77

        def __index__(self):
            calls.append("indexull")
            return 77

    class EvilFloat(np.float64):
        def __float__(self):
            calls.append("float64")
            return 77.0

    for cls in (EvilInt64, EvilLong, EvilULong, EvilFloat):
        frame = _blank()
        frame.iloc[0, 0] = cls(5)
        assert type(frame.iloc[0, 0]) is cls
        calls.clear()
        with pytest.raises(ValueError) as caught:
            owner.project_history_read(_receipt(frame))
        assert caught.value.args == (ERROR,)
        assert caught.value.__cause__ is None
        assert calls == []


def test_exact_longlong_and_ulonglong_keep_full_integer_precision():
    index = pd.DatetimeIndex(["2026-01-01T00:00:00+00:00"], tz="UTC")
    cases = [
        (np.array([np.longlong(-2**63)], dtype=object), -2**63),
        (np.array([5], dtype=np.longlong), 5),
        (np.array([np.ulonglong(2**64 - 1)], dtype=object), 2**64 - 1),
        (np.array([np.ulonglong(2**64 - 1)], dtype=np.ulonglong), 2**64 - 1),
    ]
    for growth, expected in cases:
        frame = pd.DataFrame(
            {"growth_score": growth, "inflation_score": np.array([0], dtype=object)},
            index=index,
        )
        out = owner.project_history_read(_receipt(frame))
        value = out["points"][0]["growth_score"]
        assert type(value) is int
        assert value == expected


def test_bool_still_rejected_after_longlong_allowlist():
    index = pd.DatetimeIndex(["2026-01-01T00:00:00+00:00"], tz="UTC")
    frames = [
        pd.DataFrame(
            {
                "growth_score": np.array([True], dtype=object),
                "inflation_score": np.array([0], dtype=object),
            },
            index=index,
        ),
        pd.DataFrame(
            {
                "growth_score": np.array([np.bool_(False)]),
                "inflation_score": np.array([0.0]),
            },
            index=index,
        ),
    ]
    for frame in frames:
        with pytest.raises(ValueError) as caught:
            owner.project_history_read(_receipt(frame))
        assert caught.value.args == (ERROR,)
        assert caught.value.__cause__ is None
