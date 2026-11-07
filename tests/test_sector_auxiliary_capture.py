"""Actual-format captured byte tests; no provider, path selection or runtime."""
from dataclasses import replace
from datetime import date, datetime, timezone, timedelta
from io import BytesIO
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lib import sector_auxiliary_capture as capture

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def observed(raw, *, key="config", outcome="present", reason=None, origin=None):
    return capture.CapturedAuxiliarySource(
        origin or "captured:/" + key, "observed-vintage-1", NOW - timedelta(minutes=2),
        outcome, reason or {"present": "observed", "malformed": "source_malformed"}[outcome],
        raw, len(raw), hashlib.sha256(raw).hexdigest())


def observations(**values):
    result = {key: capture.CapturedAuxiliarySource(
        "captured:/" + key, None, NOW - timedelta(minutes=2), "absent", "not_found",
        None, None, None) for key in capture.SOURCE_KEYS}
    for key, raw in values.items():
        result[key] = observed(raw, key=key)
    return result


def decoded(**values):
    return capture.decode_sector_auxiliary_capture(observations(**values), captured_at=NOW)


def parquet(frame, *, index=None):
    table = pa.Table.from_pandas(frame, preserve_index=index)
    sink = BytesIO()
    pq.write_table(table, sink, compression="snappy")
    return sink.getvalue()


def financial_frames():
    return {
        "short_interest": pd.DataFrame({
            "short_shares": [120, 0], "prev_short_shares": [110, None],
            "avg_daily_vol": [20.5, 0], "days_to_cover": [5.85, None],
            "si_change_pct": [9.09, None], "settlement_date": ["2026-10-30", None],
            "asof": ["2026-11-02", "2026-10-16"], "dtc_capped": [False, None],
        }, index=pd.Index(["NVDA", "BRK-B"], name="ticker")),
        "earnings": pd.DataFrame({
            "next_date": ["2026-11-10", "tomorrow"], "as_of": ["2026-11-05", "2026-10-01"],
            "next_time": ["amc", None], "eps_forecast": [1.2, None],
            "surprises_json": ["[]", None], "surprises_as_of": ["2026-11-01", None],
        }, index=pd.Index(["NVDA", "MSFT"], name="ticker")),
        "breadth_tape": pd.DataFrame({
            "adv": [12, 15], "dec": [6, 3], "pct_above_50": [60.5, 65],
            "pct_above_200": [70, 72], "nh": [2, 3], "nl": [1, 0],
        }, index=pd.DatetimeIndex(["2026-11-05", "2026-11-04"], name="session")),
        "basket_frozen": pd.DataFrame({
            "us_sector_tech__level_price": [100.0, 102.0],
            "us_sector_tech__level_tr": [100.0, 103.0],
            "us_sector_tech__n_members": [2, 2],
            "us_sector_tech__mhash": ["abc", "def"],
            "us_sector_tech__anchor": ["2026-10-30", "2026-10-30"],
            "__freeze_schema": [2, 2],
        }, index=pd.DatetimeIndex(["2026-11-04", "2026-11-05"], name=None)),
        "basket_archive": pd.DataFrame({
            "asof": ["2026-11-04", "2026-11-05"],
            "snapshot_json": ['{"asof":"2026-11-04","themes":[]}', '{"asof":"2026-11-05","themes":[]}'],
            "logged_at": ["2026-11-04T22:00:00Z", "2026-11-05T22:00:00Z"],
            "unused_flattened": [1.0, 2.0],
        }),
        "cycle_forward_log": pd.DataFrame({
            "date": ["2026-11-04", "2026-11-05"], "id": ["xlk", "xlf"],
            "phase_v2": ["Recovery", "Leading"], "phase": ["up", "up"],
            "pos": [25.0, 55.0], "osc_slope": [1.0, 2.0],
            "above200d": [True, False], "signal": ["go", "wait"],
            "timing_state": ["early", "late"], "kind": ["sector", "sector"],
            "name": ["Technology", "Financials"],
        }),
        "central_calls": pd.DataFrame({
            "date": ["2026-11-04", "2026-11-05"], "id": ["xlk", "xlf"],
            "kind": ["sector", "sector"], "ticker": ["XLK", "XLF"],
            "basket_id": [None, None], "name": ["Tech", "Financials"],
            "label": ["Leading", "Lagging"], "score": [72.0, None],
            "dir": [1, -1], "level": [100.0, 102.0], "score_version": [None, 2],
            "trend_pass": [True, None],
        }),
    }


@pytest.mark.parametrize("raw,outcome", [(b'{"schema":"mastermind.risk_envelope/v1"}', "present"),
                                          (b'{broken', "malformed"), (None, "absent")])
def test_published_risk_context_uses_the_existing_optional_byte_capture(raw, outcome):
    assert capture.SOURCE_SPECS["public_risk_envelope"] == ("json", "S/riskdata/risk_envelope.json")
    sources = observations(config=b"{}", market_state=b'{"schema":"market_state.v1"}',
                           alpha=b'{"per_ticker":{}}')
    if raw is not None:
        sources["public_risk_envelope"] = observed(raw, key="public_risk_envelope")
    result = capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)
    fact = result.observation("public_risk_envelope")
    assert fact.decode_outcome == outcome
    assert fact.sha256 == (hashlib.sha256(raw).hexdigest() if raw is not None else None)
    assert not any("risk" in reason for reason in result.unresolved)
    if outcome == "present":
        detached = result.document("public_risk_envelope")
        detached["schema"] = "changed"
        assert result.document("public_risk_envelope")["schema"] == "mastermind.risk_envelope/v1"
    else:
        assert result.document("public_risk_envelope") is None


def test_complete_binding_distinguishes_all_observation_outcomes():
    sources = observations(config=b"{}", risk_calibration=b"{}")
    sources["market_state"] = replace(sources["market_state"], outcome="unreadable", reason="io_error")
    sources["alpha"] = observed(b"{broken", key="alpha", outcome="malformed")
    result = capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)
    assert len(result.evidence) == 35
    assert result.observation("config").decode_outcome == "present"
    assert result.document("config") == {}
    assert result.observation("cycle_bands").observation == "absent"
    assert result.observation("market_state").decode_outcome == "unreadable"
    assert result.observation("alpha").observation == "malformed"
    assert "market_state_resolution_required" in result.unresolved
    assert "alpha_producer_result_required" in result.unresolved
    assert result.input_lineage()["sources"]["config"]["captured_at"] == (NOW - timedelta(minutes=2)).isoformat()
    with pytest.raises(KeyError):
        result.observation("not-a-source")


@pytest.mark.parametrize("alter", ["omitted", "extra", "none", "future", "naive", "length", "hash", "bytes_type", "bad_outcome", "failed_bytes"])
def test_unbound_or_contradictory_facts_refuse_whole_capture(alter):
    sources = observations(config=b"{}")
    if alter == "omitted":
        del sources["alpha"]
    elif alter == "extra":
        sources["invented"] = sources["config"]
    elif alter == "none":
        sources["config"] = None
    else:
        updates = {
            "future": {"captured_at": NOW + timedelta(seconds=1)},
            "naive": {"captured_at": NOW.replace(tzinfo=None)},
            "length": {"byte_length": 999}, "hash": {"sha256": "0" * 64},
            "bytes_type": {"raw_bytes": bytearray(b"{}")},
            "bad_outcome": {"outcome": {"present": True}},
            "failed_bytes": {"outcome": "absent", "reason": "not_found"},
        }
        sources["config"] = replace(sources["config"], **updates[alter])
    with pytest.raises(capture.AuxiliaryCaptureError):
        capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)


@pytest.mark.parametrize("raw,reason", [
    (b'{"x":1,"x":2}', "duplicate_key"),
    (b'{"x":NaN}', "nonfinite_value"),
    (b'{"x":Infinity}', "nonfinite_value"),
    (b'{broken', "invalid_json"),
    (b'\xff', "invalid_json"),
])
def test_malformed_json_is_evidence_not_empty_success(raw, reason):
    result = decoded(risk_calibration=raw)
    item = result.observation("risk_calibration")
    assert (item.observation, item.decode_outcome, item.decode_reason) == ("present", "malformed", reason)
    assert result.document("risk_calibration") is None
    assert item.sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("raw", [b"x: 1\nx: 2\n", b"x: !!python/object:builtins.object {}\n", b"x: .inf\n"])
def test_yaml_rejects_duplicate_unsafe_and_nonfinite_values(raw):
    assert decoded(config=raw).observation("config").decode_outcome == "malformed"


def test_yaml_safe_merge_and_original_scalars():
    result = decoded(config=b'defaults: &defaults {a: 1}\nsettings: {<<: *defaults, b: 2}\nday: 2026-11-05\nword: tomorrow\n')
    assert result.document("config")["settings"] == {"a": 1, "b": 2}
    assert str(result.document("config")["day"]) == "2026-11-05"
    assert result.document("config")["word"] == "tomorrow"


@pytest.mark.parametrize("raw", [
    b"[" * 40 + b"0" + b"]" * 40,
    b'{"x":"' + b"x" * (capture.MAX_SCALAR_BYTES + 1) + b'"}',
    b"x: &loop [*loop]\n",
])
def test_structure_resource_violations_refuse_set(raw):
    key = "config" if raw.startswith(b"x:") else "cycle_bands"
    with pytest.raises(capture.AuxiliaryCaptureError):
        decoded(**{key: raw})


def test_encoded_and_aggregate_bounds(monkeypatch):
    monkeypatch.setattr(capture, "MAX_CAPTURE_BYTES", 3)
    with pytest.raises(capture.AuxiliaryCaptureError, match="capture_encoded_bound"):
        decoded(config=b"{}", cycle_bands=b"{}")


def test_jsonl_order_empty_history_and_corruption_are_explicit():
    assert decoded(theme_context_history=b"").document("theme_context_history") == []
    result = decoded(theme_context_history=b'{"asof":"2026-11-05"}\n{"asof":"2026-11-04"}\n')
    assert [r["asof"] for r in result.document("theme_context_history")] == ["2026-11-05", "2026-11-04"]
    broken = decoded(theme_context_history=b'{"asof":"2026-11-05"}\nnope\n')
    assert broken.observation("theme_context_history").decode_outcome == "malformed"
    assert broken.document("theme_context_history") is None


def test_all_actual_table_shapes_preserve_required_values_indices_and_row_order():
    inputs = financial_frames()
    inputs["theme_seed_archive"] = inputs["basket_archive"].copy()
    result = decoded(**{key: parquet(frame) for key, frame in inputs.items()})
    for key in inputs:
        assert result.observation(key).decode_outcome == "present", (key, result.observation(key))
    short = result.table("short_interest")
    assert list(short.index) == ["NVDA", "BRK-B"]
    assert short.index.name == "ticker"
    assert pd.isna(short.loc["BRK-B", "days_to_cover"])
    assert short.loc["NVDA", "settlement_date"] == "2026-10-30"
    assert result.table("earnings").loc["MSFT", "next_date"] == "tomorrow"
    assert list(result.table("breadth_tape").index) == list(inputs["breadth_tape"].index)
    frozen = result.table("basket_frozen")
    assert frozen["us_sector_tech__mhash"].tolist() == ["abc", "def"]
    assert frozen["us_sector_tech__anchor"].tolist() == ["2026-10-30"] * 2
    assert frozen["__freeze_schema"].tolist() == [2, 2]
    forward = result.table("cycle_forward_log")
    assert list(forward.columns) == list(inputs["cycle_forward_log"].columns)
    assert forward["timing_state"].tolist() == ["early", "late"]
    assert "unused_flattened" not in result.table("basket_archive").columns
    assert pd.isna(result.table("central_calls").iloc[0]["score_version"])


@pytest.mark.parametrize("key", ["earnings", "short_interest", "breadth_tape", "basket_frozen", "basket_archive", "cycle_forward_log", "central_calls"])
def test_empty_tables_remain_present_empty(key):
    frame = financial_frames()[key].iloc[0:0]
    result = decoded(**{key: parquet(frame)})
    assert result.observation(key).decode_outcome == "present", result.observation(key)
    assert result.table(key).empty


@pytest.mark.parametrize("unit", ["ms", "us", "ns"])
def test_timestamp_index_precision_is_preserved(unit):
    frame = financial_frames()["breadth_tape"]
    frame.index = frame.index.as_unit(unit)
    result = decoded(breadth_tape=parquet(frame))
    assert result.table("breadth_tape").index.unit == unit


def test_missing_required_column_is_malformed_not_an_empty_table():
    frame = financial_frames()["earnings"].drop(columns=["next_date"])
    result = decoded(earnings=parquet(frame))
    assert result.table("earnings") is None
    assert result.observation("earnings").decode_reason == "required_columns_missing"


def test_string_measurement_nested_fields_and_undeclared_ticker_index_are_rejected():
    frame = financial_frames()["short_interest"]
    frame["days_to_cover"] = ["five", "six"]
    assert decoded(short_interest=parquet(frame)).observation("short_interest").decode_reason == "parquet_field_type_invalid"
    frame = financial_frames()["earnings"]
    frame["nested"] = [{"private": 1}, {"private": 2}]
    assert decoded(earnings=parquet(frame)).observation("earnings").decode_reason == "parquet_primitive_schema_required"
    frame = financial_frames()["earnings"].reset_index()
    assert decoded(earnings=parquet(frame, index=False)).observation("earnings").decode_reason == "physical_index_required"


def test_footer_bound_and_whole_set_preflight_precede_any_table_read(monkeypatch):
    raw = parquet(financial_frames()["earnings"])
    called = []
    original = capture._arrow_table
    monkeypatch.setattr(capture, "_arrow_table", lambda plan: (called.append(plan.key), original(plan))[1])
    footer_bomb = raw[:-8] + (capture.MAX_FOOTER_BYTES + 1).to_bytes(4, "little") + b"PAR1"
    with pytest.raises(capture.AuxiliaryCaptureError, match="parquet_footer_bound"):
        decoded(earnings=raw, central_calls=footer_bomb)
    assert called == []
    monkeypatch.setattr(capture, "MAX_DECODE_BYTES", 1)
    with pytest.raises(capture.AuxiliaryCaptureError, match="capture_prospective_allocation_bound"):
        decoded(earnings=raw)
    assert called == []


def test_dictionary_string_expansion_is_bounded_before_python_frame(monkeypatch):
    frame = pd.DataFrame({"asof": ["2026-11-05"] * 2000,
                          "snapshot_json": [json.dumps({"text": "x" * 10000})] * 2000})
    raw = parquet(frame)
    assert len(raw) < 100_000
    monkeypatch.setattr(capture, "MAX_DECODE_BYTES", 4 * capture.MIB)
    called = []
    monkeypatch.setattr(capture, "_frame", lambda plan: called.append(plan.key))
    with pytest.raises(capture.AuxiliaryCaptureError, match="capture_decoded_allocation_bound"):
        decoded(basket_archive=raw)
    assert called == []


@pytest.mark.parametrize("raw", [b'{"x":NaN}', b'{"x":1,"x":2}', b'nope'])
def test_nested_archive_json_is_validated_without_silently_dropping_rows(raw):
    frame = pd.DataFrame({"asof": ["2026-11-05"], "snapshot_json": [raw.decode()]})
    result = decoded(basket_archive=parquet(frame))
    assert result.table("basket_archive") is None
    assert result.observation("basket_archive").decode_outcome == "malformed"


def test_capture_origin_alias_must_reuse_identical_observation():
    raw = parquet(financial_frames()["basket_archive"])
    sources = observations()
    sources["basket_archive"] = observed(raw, key="basket_archive", origin="captured:/same-file")
    sources["theme_seed_archive"] = sources["basket_archive"]
    result = capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)
    assert result.table("basket_archive").equals(result.table("theme_seed_archive"))
    sources["theme_seed_archive"] = replace(sources["basket_archive"], captured_at=NOW)
    with pytest.raises(capture.AuxiliaryCaptureError, match="conflicting_origin"):
        capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)


def test_capture_and_consumer_mutation_are_isolated_without_loading_any_source(monkeypatch):
    sources = observations(config=b'{"group_flow":{"span":21}}', earnings=parquet(financial_frames()["earnings"]))
    def forbidden(*args, **kwargs):
        raise AssertionError("Decoder attempted source IO")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    result = capture.decode_sector_auxiliary_capture(sources, captured_at=NOW)
    sources["config"] = None
    document = result.document("config")
    document["group_flow"]["span"] = 999
    assert result.document("config")["group_flow"]["span"] == 21
    frame = result.table("earnings")
    frame.iloc[0, 0] = "changed"
    assert result.table("earnings").iloc[0, 0] == "2026-11-10"
    lineage = result.input_lineage()
    lineage["sources"]["config"]["origin"] = "modified"
    assert result.observation("config").origin == "captured:/config"


@pytest.mark.parametrize("raw", [b"null", b"{}", b"[]"])
def test_market_state_empty_or_nonmapping_does_not_resolve_legacy_fallback(raw):
    assert "market_state_resolution_required" in decoded(market_state=raw).unresolved


def test_published_clocks_and_alpha_vintage_are_never_promoted():
    result = decoded(config=b"{}", market_state=b'{"as_of":"2026-10-30","state":"risk_on"}',
                     alpha=b'{"as_of":"2026-10-29","per_ticker":{"NVDA":1.2}}')
    assert set(result.unresolved) == {"market_state_owner_qualification_required", "alpha_owner_qualification_required"}
    assert result.document("market_state")["as_of"] == "2026-10-30"
    assert result.document("alpha")["as_of"] == "2026-10-29"


def test_earnings_value_feeds_incumbent_owner_projection():
    from engine.theme_scoring import earnings_calendar_from_inputs
    result = decoded(earnings=parquet(financial_frames()["earnings"]))
    calendar = earnings_calendar_from_inputs(result.table("earnings"), panel_session=date(2026, 11, 5))
    assert isinstance(calendar, dict)
    assert "NVDA" in calendar


def test_yaml_merge_expansion_is_refused_before_any_flattening(monkeypatch):
    import yaml
    calls = []
    original = yaml.SafeLoader.flatten_mapping
    def tracked(self, node):
        calls.append(node)
        return original(self, node)
    monkeypatch.setattr(yaml.SafeLoader, "flatten_mapping", tracked)
    lines = ["a0: &a0 {x: 1}"]
    for i in range(1, 24):
        lines.append(f"a{i}: &a{i} {{<<: [*a{i-1}, *a{i-1}]}}")
    with pytest.raises(capture.AuxiliaryCaptureError, match="yaml_expansion_bound"):
        decoded(config=("\n".join(lines) + "\n").encode())
    assert calls == []


def test_incumbent_optional_breadth_and_finra_columns_remain_optional():
    frames = financial_frames()
    breadth = frames["breadth_tape"][["adv", "dec"]]
    short = frames["short_interest"][["days_to_cover"]]
    result = decoded(breadth_tape=parquet(breadth), short_interest=parquet(short))
    assert result.observation("breadth_tape").decode_outcome == "present"
    assert result.observation("short_interest").decode_outcome == "present"
    assert list(result.table("breadth_tape").columns) == ["adv", "dec"]
    assert list(result.table("short_interest").columns) == ["days_to_cover"]


def test_physical_index_cannot_consume_a_semantic_data_column():
    frame = pd.DataFrame({"as_of": ["2026-11-05"]},
                         index=pd.Index(["2026-11-10"], name="next_date"))
    result = decoded(earnings=parquet(frame))
    assert result.table("earnings") is None
    assert result.observation("earnings").decode_reason == "index_data_column_collision"


def test_document_decoding_never_claims_market_state_or_alpha_business_admission():
    result = decoded(config=b"{}", market_state=b'{"unrelated":1}',
                     alpha=b'{"per_ticker":{}}')
    assert "market_state_owner_qualification_required" in result.unresolved
    assert "alpha_owner_qualification_required" in result.unresolved


def test_oversized_source_is_rejected_before_hashing(monkeypatch):
    raw = b"x" * (capture.MIB + 1)
    items = observations()
    items["config"] = capture.CapturedAuxiliarySource(
        "captured:/config", "oversize-v1", NOW, "present", "observed",
        raw, len(raw), "0" * 64)
    def forbidden(*args, **kwargs):
        raise AssertionError("oversized source reached digest work")
    monkeypatch.setattr(capture.hashlib, "sha256", forbidden)
    with pytest.raises(capture.AuxiliaryCaptureError, match="source_encoded_bound"):
        capture.decode_sector_auxiliary_capture(items, captured_at=NOW)
