"""Hermetic qualification tests; use synthetic receipts and zero network."""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile

import pytest

from collectors.options_free_samples import (
    CBOE_REQUIRED, SAMPLE_CSV, SAMPLE_INNER_ZIP, SAMPLE_DAY,
    SourceRejected, qualify_cboe_c1_sample, qualify_occ_volume_csv,
)


def _zip_member(name: str, data: bytes) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, data)
    return b.getvalue()


def _source(*, date: str = SAMPLE_DAY, volume: str = "7", series: str = "S"):
    names = sorted(CBOE_REQUIRED)
    row = {n: "0" for n in names}
    row.update({
        "quote_date": date, "underlying_symbol": "XLK",
        "option_symbol": "XLK", "expiration_date": "2025-04-17",
        "strike_price": "200", "call_put_flag": "P", "series_type": series,
        "total_exchange_vol": "24", "open_interest": "100",
        "cust_lt_100_open_buy_vol": volume,
        "cust_lt_100_close_buy_vol": "2",
        "procust_lt_100_open_sell_vol": "3",
    })
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=names)
    w.writeheader()
    w.writerow(row)
    inner = _zip_member(SAMPLE_CSV, buf.getvalue().encode())
    outer = _zip_member("nested/" + SAMPLE_INNER_ZIP, inner)
    return outer, {
        "file_sha256": hashlib.sha256(outer).hexdigest(),
        "sample_session": SAMPLE_DAY,
        "downloaded_at_utc": "2026-10-08T22:00:00+00:00",
    }


def test_cboe_observed_open_close_only():
    blob, receipt = _source()
    report = qualify_cboe_c1_sample(blob, receipt)
    item = report["observed_sample_only"]["XLK"]["P"]
    assert item["cust_open_buy_vol"] == 7
    assert item["cust_close_buy_vol"] == 2
    assert item["procust_open_sell_vol"] == 3
    assert report["rows_total"] == 1
    assert report["source_event_available_at"] is None
    assert report["publish"] is False
    assert report["signal_authority"] is False
    assert report["delta_matching_performed"] is False


@pytest.mark.parametrize("change", ["digest", "effective_day", "missing_clock"])
def test_cboe_refuses_uncertified_receipt(change):
    blob, receipt = _source()
    if change == "digest":
        receipt["file_sha256"] = "0" * 64
    elif change == "effective_day":
        receipt["sample_session"] = "2026-10-08"
    else:
        receipt["downloaded_at_utc"] = "2026-10-08T14:00:00"
    with pytest.raises(SourceRejected):
        qualify_cboe_c1_sample(blob, receipt)


def test_cboe_rejects_mixed_session_and_invalid_ints():
    for kwargs in ({"date": "2025-03-27"}, {"volume": "-7"}):
        blob, receipt = _source(**kwargs)
        with pytest.raises(SourceRejected):
            qualify_cboe_c1_sample(blob, receipt)


def test_cboe_rejects_nonstandard_only():
    blob, receipt = _source(series="N")
    with pytest.raises(SourceRejected):
        qualify_cboe_c1_sample(blob, receipt)


def test_occ_preserves_account_side_without_double_count():
    b = ("quantity,underlying,symbol,actype,porc,exchange,actdate,contractDate\n"
         "100,SPY,SPY,C,C,CBOE,10/07/2026,10/07/2026\n"
         "100,SPY,SPY,M,C,CBOE,10/07/2026,10/07/2026\n").encode()
    r = qualify_occ_volume_csv(b, "2026-10-07", "SPY")
    assert r["account_side_quantity_by_venue"] == {"CBOE:C:C": 100, "CBOE:M:C": 100}
    assert r["nationwide_unique_contracts_computed"] is False
    assert r["opening_closing_observed"] is False
    assert r["commercial_use_authorized"] is False


def test_occ_wrong_session_does_not_create_zero():
    b = ("quantity,underlying,symbol,actype,porc,exchange,actdate,contractDate\n"
         "10,SPY,SPY,C,P,CBOE,10/06/2026,10/06/2026\n").encode()
    with pytest.raises(SourceRejected):
        qualify_occ_volume_csv(b, "2026-10-07", "SPY")

def test_external_private_root_refuses_internal_fallback(tmp_path):
    from scripts.qualify_options_free_samples import _checked_root

    with pytest.raises(SourceRejected, match="external private Cboe root"):
        _checked_root(tmp_path)


@pytest.mark.parametrize("bad_field,bad_value", [
    ("VolumeUUID", "not-the-enrolled-volume"),
    ("MountPoint", "/Volumes/Imposter"),
    ("TotalSize", 100_000),
])
def test_external_volume_identity_pinned(bad_field, bad_value):
    from scripts.qualify_options_free_samples import (
        _check_volume, EXTERNAL_VOLUME, EXTERNAL_VOLUME_BYTES, EXTERNAL_VOLUME_UUID,
    )

    info = {
        "VolumeUUID": EXTERNAL_VOLUME_UUID,
        "MountPoint": str(EXTERNAL_VOLUME),
        "TotalSize": EXTERNAL_VOLUME_BYTES,
    }
    info[bad_field] = bad_value
    with pytest.raises(SourceRejected, match="not mounted/identical"):
        _check_volume(info, mounted_device=3, system_device=2)


def test_external_disk_cannot_be_main_ssd():
    from scripts.qualify_options_free_samples import (
        _check_volume, EXTERNAL_VOLUME, EXTERNAL_VOLUME_BYTES, EXTERNAL_VOLUME_UUID,
    )

    with pytest.raises(SourceRejected, match="not mounted/identical"):
        _check_volume({
            "VolumeUUID": EXTERNAL_VOLUME_UUID,
            "MountPoint": str(EXTERNAL_VOLUME),
            "TotalSize": EXTERNAL_VOLUME_BYTES,
        }, mounted_device=2, system_device=2)
