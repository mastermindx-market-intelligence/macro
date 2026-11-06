"""Existing-store -> non-voting envelope integration; fixtures are not alpha proof."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.multi_asset_daily import UNIVERSE, compose_daily_context
from engine.risk_envelope import EnvelopeContractError, compose_envelope
from scripts.risk_envelope_multi_asset import _read_source, build_multi_asset_context
from scripts.build_risk_envelope import build

START, END = "2026-10-28", "2026-11-04"
NOW = datetime(2026, 11, 5, 15, tzinfo=timezone.utc)


def _context(**kwargs):
    rows = [dict(instrument_id=t, source_digest="a" * 64, currency="USD", listing_market="US",
                 return_basis="total_return", prices={START: 100.0, END: 96.0 if t == "SPY" else 99.0},
                 last_source_session=END) for t, *_ in UNIVERSE]
    options = dict(captured_at=NOW.isoformat(), expected_session=END,
                   start_session=START, end_session=END, horizon_sessions=5)
    options.update(kwargs)
    return compose_daily_context(rows, **options)


def _envelope(context=None, *, produced="2026-11-05T15:01:00Z"):
    return compose_envelope(sources=[], market="US", source_session=END,
                            observed_at=produced, produced_at=produced, multi_asset_context=context)


def _write(root: Path, ticker="SPY", *, index=None, values=None):
    path = root / "data" / "yahoo" / (ticker + ".parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    index = pd.to_datetime([START, END]) if index is None else index
    values = [100.0, 96.0] if values is None else values
    pd.DataFrame({"close": values}, index=index).to_parquet(path)
    return path


def _fill(root: Path):
    return [_write(root, ticker=t, values=[100.0, 96.0 if t == "SPY" else 99.0]) for t, *_ in UNIVERSE]


def test_reader_preserves_exact_source_hash(tmp_path):
    path = _write(tmp_path)
    result = _read_source(tmp_path, "SPY")
    assert result["source_digest"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["return_basis"] == "total_return"
    assert result["prices"][END] == 96.0


def test_reader_missing(tmp_path):
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_missing"


def test_reader_corrupted(tmp_path):
    p = tmp_path / "data/yahoo/SPY.parquet"; p.parent.mkdir(parents=True); p.write_bytes(b"not parquet")
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_unreadable"


def test_reader_symlink_refused(tmp_path):
    _write(tmp_path, "EEM")
    (tmp_path / "data/yahoo/SPY.parquet").symlink_to("EEM.parquet")
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_symlink_refused"


@pytest.mark.parametrize("index", [
    pd.to_datetime([START, START]), pd.to_datetime([END, START]),
    pd.to_datetime([START, END], utc=True),
    pd.to_datetime([START + "T12:00:00", END + "T12:00:00"]),
    pd.RangeIndex(2), pd.DatetimeIndex([pd.NaT, pd.Timestamp(END)]),
])
def test_reader_rejects_ambiguous_session_index(tmp_path, index):
    _write(tmp_path, index=index)
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_shape_invalid"


def test_reader_bool_values_not_prices(tmp_path):
    _write(tmp_path, values=[True, False])
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_shape_invalid"


def test_reader_does_not_use_close_price_as_total_return(tmp_path):
    p = tmp_path / "data/yahoo/SPY.parquet"; p.parent.mkdir(parents=True)
    pd.DataFrame({"close_price": [100.0, 99.0]}, index=pd.to_datetime([START, END])).to_parquet(p)
    assert _read_source(tmp_path, "SPY")["read_error"] == "source_unreadable"


def test_adapter_real_parquet_path(tmp_path):
    _fill(tmp_path)
    result = build_multi_asset_context(tmp_path, now=NOW)
    assert result["status"] == "AVAILABLE"
    assert result["window"]["start_session"] == START
    assert result["window"]["end_session"] == END
    assert result["coverage"]["comparable"] == 10
    assert result["provider_available_at"] is None


def test_adapter_preserves_missing_oil_endpoint(tmp_path):
    _fill(tmp_path)
    _write(tmp_path, "USO", index=pd.to_datetime([START, "2026-11-03"]))
    result = build_multi_asset_context(tmp_path, now=NOW)
    oil = next(r for r in result["rows"] if r["instrument_id"] == "USO")
    assert result["status"] == "PARTIAL" and oil["absolute_return"] is None
    assert "end_session_missing" in oil["reasons"]


def test_adapter_does_not_move_window_to_foreign_candidate(tmp_path):
    _fill(tmp_path)
    _write(tmp_path, "EEM", index=pd.to_datetime(["2026-10-27", "2026-11-03"]))
    result = build_multi_asset_context(tmp_path, now=NOW)
    assert result["window"]["end_session"] == END
    assert next(r for r in result["rows"] if r["instrument_id"] == "EEM")["status"] == "UNAVAILABLE"


def test_adapter_ignores_unsettled_current_day(tmp_path):
    _fill(tmp_path)
    _write(tmp_path, index=pd.to_datetime([START, END, "2026-11-05"]), values=[100.0, 96.0, 90.0])
    result = build_multi_asset_context(tmp_path, now=NOW)
    assert result["window"]["end_session"] == END
    assert result["benchmark_return"] == pytest.approx(-0.04)


def test_adapter_labels_stale_after_settle_boundary(tmp_path):
    _fill(tmp_path)
    result = build_multi_asset_context(tmp_path, now=datetime(2026, 11, 5, 23, tzinfo=timezone.utc))
    assert result["status"] == "STALE"
    assert result["window"]["expected_session"] == "2026-11-05"
    assert result["window"]["end_session"] == END


def test_adapter_no_writes(tmp_path):
    paths = _fill(tmp_path)
    before = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
    build_multi_asset_context(tmp_path, now=NOW)
    after = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
    assert before == after
    assert len(list(tmp_path.rglob("*.*"))) == len(paths)


def test_adapter_missing_all_still_honest(tmp_path):
    result = build_multi_asset_context(tmp_path, now=NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["coverage"]["observed"] == 0
    assert result["benchmark_return"] is None


def test_adapter_rejects_naive_capture(tmp_path):
    with pytest.raises(ValueError): build_multi_asset_context(tmp_path, now=NOW.replace(tzinfo=None))


def test_envelope_legacy_optional_absence():
    original = compose_envelope(sources=[], market="US", source_session=END,
                               observed_at="2026-11-05T15:01:00Z", produced_at="2026-11-05T15:01:00Z")
    assert _envelope() == original
    assert "multi_asset_context" not in original


def test_envelope_context_cannot_vote():
    original, added = _envelope(), _envelope(_context())
    for key in ["measured_state", "hazard_summary", "coherence", "data_state", "policy_summary",
                "policies", "episodes", "authority", "provenance", "coverage"]:
        assert original[key] == added[key]
    assert original["bundle_id"] != added["bundle_id"]


def test_envelope_recapture_does_not_mint_observation():
    a = _envelope(_context())
    b = _envelope(_context(captured_at="2026-11-05T15:00:30Z"))
    assert a["bundle_id"] == b["bundle_id"]
    assert a["multi_asset_context"]["captured_at"] != b["multi_asset_context"]["captured_at"]


def test_envelope_correction_changes_bundle():
    context = _context(); changed = copy.deepcopy(context)
    changed["rows"][0]["source_digest"] = "b" * 64
    from engine.multi_asset_daily import semantic_context
    changed["context_digest"] = hashlib.sha256(json.dumps(semantic_context(changed), sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    assert _envelope(context)["bundle_id"] != _envelope(changed)["bundle_id"]


def test_envelope_no_input_mutation():
    context = _context(); before = copy.deepcopy(context)
    _envelope(context); assert context == before


def test_envelope_refuses_authority_escalation():
    context = _context(); context["authority"]["can_trade"] = True
    with pytest.raises(EnvelopeContractError): _envelope(context)


def test_envelope_refuses_future_capture():
    with pytest.raises(EnvelopeContractError): _envelope(_context(captured_at="2026-11-05T15:02:00Z"))


def test_existing_builder_composes_context_without_writing(tmp_path):
    paths = _fill(tmp_path)
    result = build(root=tmp_path, now=NOW)
    assert result["multi_asset_context"]["coverage"]["comparable"] == 10
    assert not (tmp_path / "data/risk_envelope").exists()
    assert not (tmp_path / "site").exists()
    assert len(list(tmp_path.rglob("*.*"))) == len(paths)
