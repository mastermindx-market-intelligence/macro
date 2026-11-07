"""Synthetic 3%-sample tests: no external redistribution or vendor network."""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile

import pytest

from collectors.options_free_samples import SourceRejected
from collectors.options_free_tbt import INNER_CSV, INNER_ZIP, REQUIRED, DAY, qualify_cboe_tbt_sample


def _pack(name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, content)
    return output.getvalue()


def _sample(*, side="B", oc="O", capacity="Customer", day=DAY, complex_id="", right="P"):
    names = sorted(REQUIRED)
    row = {k: "" for k in names}
    row.update({
        "trading_dt": day, "transact_time": "2025-03-27 22:30:00.123",
        "underlying": "XLK", "osi_root": "XLK", "expire_date": "2025-04-17",
        "strike_price": "200", "call_put_flag": right, "size": "3",
        "price": "1.25", "nbbo_bid": "1.20", "nbbo_ask": "1.30",
        "side": side, "open_close": oc, "capacity": capacity,
        "trade_type": "Complex Add", "exec_id": "X1",
        "complex_exec_id": complex_id, "session": "GTH", "trading_segment": "1",
    })
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=names)
    w.writeheader()
    w.writerow(row)
    data = _pack("nested/" + INNER_ZIP, _pack(INNER_CSV, buf.getvalue().encode()))
    receipt = {
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "sample_session": DAY, "downloaded_at_utc": "2026-10-08T22:00:00+00:00",
        "columns": names,
    }
    return data, receipt


def test_tbt_qualified_side_is_not_aggressor_or_pit():
    blob, receipt = _sample(complex_id="CMP")
    x = qualify_cboe_tbt_sample(blob, receipt)
    assert x["rows_total"] == 1
    assert x["rows_fully_classified_with_economics"] == 1
    assert x["rows_with_complex_exec_id"] == 1
    assert x["participant_side_by_underlying"]["XLK"]["classifiable_contracts"] == {
        "P:Customer:buy:open": 3
    }
    assert x["source_event_clock_timezone_qualified"] is False
    assert x["historical_original_available_at"] is None
    assert x["quote_age_ms"] is None
    assert x["unique_executions_from_two_sided_rows"] is None
    assert x["signal_authority"] is False and x["publish"] is False


@pytest.mark.parametrize("side,oc,capacity", [
    ("T", "O", "Customer"), ("B", " ", "Customer"), ("S", "C", ""),
])
def test_incomplete_participant_classification_is_omitted(side, oc, capacity):
    blob, receipt = _sample(side=side, oc=oc, capacity=capacity)
    x = qualify_cboe_tbt_sample(blob, receipt)
    assert x["rows_total"] == 1
    assert x["rows_fully_classified_with_economics"] == 0
    assert x["rows_fully_classified_with_economics"] < x["rows_total"]


def test_tbt_fails_closed_on_hash_mismatch():
    blob, receipt = _sample()
    receipt["file_sha256"] = "0" * 64
    with pytest.raises(SourceRejected):
        qualify_cboe_tbt_sample(blob, receipt)


def test_tbt_rejects_mismatched_trade_date():
    blob, receipt = _sample(day="2025-03-27")
    with pytest.raises(SourceRejected):
        qualify_cboe_tbt_sample(blob, receipt)


def test_tbt_rejects_schema_drift_without_silent_zero():
    blob, receipt = _sample()
    receipt["columns"] = ["other"]
    with pytest.raises(SourceRejected):
        qualify_cboe_tbt_sample(blob, receipt)


def test_unknown_right_preserved_but_not_classified():
    blob, receipt = _sample(right="")
    report = qualify_cboe_tbt_sample(blob, receipt)
    assert report["rows_total"] == 1
    assert report["unknown_reasons"] == {"right_unknown": 1}
    assert report["rows_fully_classified_with_economics"] == 0
