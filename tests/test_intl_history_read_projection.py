import copy
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import international_macro_dashboard as owner
from lib.intl_workspace_history import build_history_section


ERROR = ValueError("invalid_history_read_projection")
READ_AT = "2026-10-08T01:02:03.000456789+05:30"


def receipt(status="ready", frame=None, **overrides):
    values = {
        "status": status,
        "market_id": "JP" if status not in {"unsupported"} else None,
        "artifact_ref": "intl_regime/JP_history.parquet",
        "read_at": "2026-10-08T01:02:03+05:30",
        "method_ref": "method-v1",
        "frame": frame,
    }
    values.update(overrides)
    return values


def history_arguments(history_read):
    return dict(
        context={"selected_market": "JP", "horizon": "3m", "currency_basis": "local",
                 "return_basis": "price"},
        history_read=history_read,
        turn_events=[],
        track_record=None,
        capabilities={
            "history_source": {"metadata": "allowed", "value": "allowed"},
            "events": {"metadata": "denied", "value": "unknown"},
            "track_record": {"metadata": "denied", "value": "unknown"},
            "snapshot_compare": {"left_observation_at": None,
                                 "right_observation_at": None},
        },
        destinations={},
    )


def test_ready_projection_preserves_mixed_scalars_precision_and_75_rows():
    index = pd.DatetimeIndex([pd.Timestamp("2026-01-01T00:00:00+09:00").as_unit("ns")])
    index = index.append(pd.DatetimeIndex(
        [pd.Timestamp("2026-03-05T09:10:11.123456789+09:00").as_unit("ns")]
    ))
    index = index.append(pd.DatetimeIndex(
        [pd.Timestamp(year, month, 1, tz="+09:00").as_unit("ns")
         for year, month in ((2026, 5), (2026, 8), (2027, 1))]
    ))
    index = index.append(pd.DatetimeIndex(
        [pd.Timestamp(1830000000123456789, unit="ns", tz="+09:00")]
    ))
    index = index.append(pd.DatetimeIndex(
        [pd.Timestamp(f"2028-{month:02d}-03T13:05:06.000000789+09:00").as_unit("ns")
         for month in range(3, 13)]
    ))
    length = 75
    index = index.append(pd.DatetimeIndex(
        [pd.Timestamp(1900000000000000000 + position * 86400000000000,
                      unit="ns", tz="+09:00").as_unit("ns")
         for position in range(length - len(index))]
    ))
    index = index.sort_values()
    growth_values = ([np.int64(1), np.uint8(0), -2.5, np.float32(0.5)] +
                     [np.int16(3), np.float64(7.25), np.float32(-0.0)] * 3 +
                     [None, 0.0] * 2 + [np.int64(9), np.float64(-11.0)])
    growth_values.extend([0.0] * (length - len(growth_values)))
    inflation_values = ([0.0, np.nan, np.float32(1.25), np.int64(0)] +
                        [2.5, None, np.int32(-4)] * 3 +
                        [pd.NA, np.float64(0.0)] * 2 +
                        [np.uint64(5), np.float32(6.5)])
    inflation_values.extend([np.nan] * (length - len(inflation_values)))
    frame = pd.DataFrame({
        "growth_score": np.array(growth_values, dtype=object),
        "inflation_score": np.array(inflation_values, dtype=object),
        "ignored": range(length),
    }, index=index)
    before = frame.copy(deep=True)
    projected = owner.project_history_read(
        receipt(frame=frame), universe="intl_regime.classifier_history")
    assert len(projected["points"]) == 75
    assert projected["points"][0] == {
        "observation_at": "2026-01-01T00:00:00+09:00",
        "growth_score": 1, "inflation_score": 0.0,
    }
    assert projected["points"][1]["observation_at"] == "2026-03-05T09:10:11.123456789+09:00"
    assert projected["points"][1]["growth_score"] == 0
    assert projected["points"][1]["inflation_score"] is None
    assert projected["points"][2]["growth_score"] == -2.5
    assert projected["points"][2]["inflation_score"] == 1.25
    assert projected["points"][-1]["observation_at"] == "2030-05-15T02:46:40+09:00"
    zero = projected["points"][9]["growth_score"]
    assert type(zero) is float and str(zero) == "-0.0"
    missing = projected["points"][13]["growth_score"]
    assert missing is None and projected["points"][14]["growth_score"] == 0.0
    assert projected["identity"] == {
        "market_id": "JP", "unit": "score", "return_basis": "price",
        "universe": "intl_regime.classifier_history", "method_ref": "method-v1",
    }
    pd.testing.assert_frame_equal(frame, before)


def test_empty_missing_failed_and_null_metadata_are_distinct():
    frame = pd.DataFrame({"growth_score": [], "inflation_score": []},
                         index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"))
    empty = owner.project_history_read(receipt("empty", frame=frame), universe="owned")
    assert empty["status"] == "empty" and empty["points"] == []
    assert empty["identity"]["universe"] == "owned"
    missing = owner.project_history_read(receipt("missing"), universe=None)
    assert missing["status"] == "missing" and missing["identity"] is None
    failed = owner.project_history_read(
        receipt("failed", artifact_ref=None, read_at=None, method_ref=None))
    assert failed["status"] == "failed" and failed["points"] == []
    assert failed["artifact_ref"] is None and failed["read_at"] is None
    assert failed["method_ref"] is None and failed["identity"] is None
    no_method = owner.project_history_read(
        receipt("empty", frame=frame, method_ref=None), universe=None)
    assert no_method["method_ref"] is None and no_method["identity"]["method_ref"] is None


@pytest.mark.parametrize("universe", ["owned-universe", None])
def test_independent_history_helper_consumes_valid_projection(universe):
    index = pd.DatetimeIndex([
        pd.Timestamp("2026-01-01T00:00:00+00:00").as_unit("ns"),
        pd.Timestamp("2026-02-01T00:00:00+00:00").as_unit("ns"),
    ])
    frame = pd.DataFrame({"growth_score": np.array([np.int64(1), 2.5], dtype=object),
                          "inflation_score": np.array([None, np.float32(-0.5)], dtype=object)}, index=index)
    history_read = owner.project_history_read(
        receipt(frame=frame), universe=universe)
    before = copy.deepcopy(history_read)
    result = build_history_section(**history_arguments(history_read))
    assert result["source_read_status"] == "ready"
    assert result["acquisition_at"] == "2026-10-08T01:02:03+05:30"
    assert len(result["points"]) == 2
    assert result["points"][1]["inflation_score"] == -0.5
    assert result["identity"] == history_read["identity"]
    assert history_read == before


def test_no_io_write_or_clock_access(monkeypatch, tmp_path):
    frame = pd.DataFrame({"growth_score": np.array([1], dtype=object),
                          "inflation_score": np.array([None], dtype=object)},
                         index=pd.DatetimeIndex([pd.Timestamp("2026-01-01", tz="UTC")]))
    receipt_value = receipt(frame=frame)
    forbidden = lambda *args, **kwargs: pytest.fail("unexpected side effect")
    monkeypatch.setattr(owner.config, "load", forbidden)
    monkeypatch.setattr(owner.config, "data_dir", forbidden)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", forbidden)
    monkeypatch.setattr(pd.DataFrame, "to_json", forbidden)
    monkeypatch.setattr(pd.DataFrame, "to_csv", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    monkeypatch.setattr(owner, "load_history_result", forbidden)
    monkeypatch.chdir(tmp_path)
    assert owner.project_history_read(receipt_value)["points"][0]["growth_score"] == 1


@pytest.mark.parametrize("overrides", [
    {"status": "unknown"}, {"status": None}, {"market_id": object()},
    {"artifact_ref": "/absolute/x.parquet"}, {"artifact_ref": "../x.parquet"},
    {"artifact_ref": "file:///x.parquet"}, {"artifact_ref": ""},
    {"read_at": object()}, {"method_ref": object()},
    {"market_id": ""},
])
def test_invalid_metadata_and_basis_fail_without_details(overrides):
    frame = pd.DataFrame({"growth_score": [], "inflation_score": []},
                         index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"))
    values = receipt("empty", frame=frame)
    values.update(overrides)
    with pytest.raises(ValueError) as caught:
        owner.project_history_read(values)
    assert caught.value.args == ERROR.args


@pytest.mark.parametrize("return_basis,universe", [
    ("total_return", None), (object(), None), (None, None),
    ("price", object()), ("price", ""), ("price", 1),
])
def test_invalid_context_arguments(return_basis, universe):
    frame = pd.DataFrame({"growth_score": [], "inflation_score": []},
                         index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"))
    with pytest.raises(ValueError) as caught:
        owner.project_history_read(receipt("empty", frame=frame),
                                   return_basis=return_basis, universe=universe)
    assert caught.value.args == ERROR.args


def test_invalid_frame_geometry_and_scalar_types():
    valid = pd.DataFrame({"growth_score": [1], "inflation_score": [None]},
                         index=pd.DatetimeIndex([pd.Timestamp("2026-01-01", tz="UTC")]))
    two_rows = pd.DataFrame({"growth_score": [1, 2], "inflation_score": [None, 2]},
                            index=pd.DatetimeIndex([
                                pd.Timestamp("2026-01-01", tz="UTC"),
                                pd.Timestamp("2026-01-02", tz="UTC")]))
    cases = []
    for kind in ("not_frame", "range", "nat", "duplicate_date", "unsorted",
                 "duplicate_column", "missing_column", "empty_ready", "nonempty_empty",
                 "bool", "inf", "positive_inf", "string", "object", "datetime_missing"):
        frame = valid.copy(deep=True)
        if kind == "not_frame":
            frame = {"growth_score": []}
        elif kind == "range":
            frame = frame.reset_index(drop=True)
        elif kind == "nat":
            frame.index = pd.DatetimeIndex([pd.NaT], dtype="datetime64[ns, UTC]")
        elif kind == "duplicate_date":
            frame = two_rows.copy(deep=True)
            frame.index = pd.DatetimeIndex([frame.index[0], frame.index[0]])
        elif kind == "unsorted":
            frame = two_rows.iloc[::-1].copy(deep=True)
        elif kind == "duplicate_column":
            frame = pd.concat([frame, frame[["growth_score"]]], axis=1)
        elif kind == "missing_column":
            frame = frame.drop(columns="growth_score")
        elif kind == "empty_ready":
            frame = frame.iloc[:0]
        elif kind == "nonempty_empty":
            frame = pd.DataFrame({"growth_score": [], "inflation_score": []})
        elif kind == "bool":
            frame["growth_score"] = True
        elif kind == "inf":
            frame["growth_score"] = float("-inf")
        elif kind == "positive_inf":
            frame["growth_score"] = np.inf
        elif kind == "string":
            frame["growth_score"] = "1"
        elif kind == "object":
            frame["growth_score"] = object()
        elif kind == "datetime_missing":
            frame["growth_score"] = pd.NaT
            frame["inflation_score"] = pd.NaT
        cases.append((kind, frame))
    for kind, frame in cases:
        with pytest.raises(ValueError) as caught:
            owner.project_history_read(receipt(frame=frame))
        assert caught.value.args == ERROR.args


def test_nonready_frame_must_be_none():
    frame = pd.DataFrame()
    for status in ("missing", "failed", "invalid", "unsupported"):
        with pytest.raises(ValueError) as caught:
            owner.project_history_read(receipt(status, frame=frame))
        assert caught.value.args == ERROR.args


def test_reject_custom_dict_and_accessor_like_frame():
    class CustomDict(dict):
        pass

    class AccessorFrame(pd.DataFrame):
        @property
        def iterrows(self):
            return lambda: pytest.fail("custom accessor invoked")

    frame = AccessorFrame({"growth_score": [1], "inflation_score": [2]},
                          index=pd.DatetimeIndex([pd.Timestamp("2026-01-01", tz="UTC")]))
    for value in (CustomDict(receipt()), receipt(frame=CustomDict({"frame": frame}))):
        with pytest.raises(ValueError) as caught:
            owner.project_history_read(value)
        assert caught.value.args == ERROR.args
    with pytest.raises(ValueError) as caught:
        owner.project_history_read(receipt(frame=frame))
    assert caught.value.args == ERROR.args


def test_output_is_detached_and_extra_columns_are_ignored():
    timestamp = pd.Timestamp("2026-01-01T12:34:56.789123456+00:00").as_unit("ns")
    frame = pd.DataFrame({
        "first": ["changed"], "growth_score": [np.int64(1)],
        "inflation_score": [np.float64(2.0)], "last": [object()],
    }, index=pd.DatetimeIndex([timestamp], name="source index"))
    original = frame.copy(deep=True)
    projected = owner.project_history_read(
        receipt(frame=frame), universe="intl_regime.classifier_history")
    projected["market_id"] = "KR"
    projected["identity"]["universe"] = "changed"
    projected["points"][0]["growth_score"] = 999
    projected["points"][0]["observation_at"] = "2027-01-01T00:00:00+00:00"
    assert frame.iloc[0]["growth_score"] == 1
    assert frame.iloc[0]["inflation_score"] == 2.0
    assert frame.index[0] == timestamp
    assert frame.iloc[0]["first"] == "changed"
    again = owner.project_history_read(
        receipt(frame=frame), universe="intl_regime.classifier_history")
    assert again["points"][0] == {
        "observation_at": "2026-01-01T12:34:56.789123456+00:00",
        "growth_score": 1, "inflation_score": 2.0,
    }
    pd.testing.assert_frame_equal(frame, original)


def test_exact_receipt_shape_and_default_universe():
    frame = pd.DataFrame({"growth_score": [], "inflation_score": []},
                         index=pd.DatetimeIndex([], dtype="datetime64[ns, UTC]"))
    values = receipt("empty", frame=frame)
    projected = owner.project_history_read(values)
    assert set(projected) == {"status", "market_id", "artifact_ref", "read_at",
                              "method_ref", "identity", "points"}
    assert projected["identity"]["universe"] is None
    assert "frame" not in projected
