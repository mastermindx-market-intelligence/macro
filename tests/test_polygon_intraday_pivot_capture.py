"""Source-owner capture support for the incumbent intraday collector.

The hourly Polygon/Massive collector is the incumbent source owner for US intraday
aggregates. These tests pin the guarantees that make it REUSABLE at another cadence
(30-minute) and able to RETAIN the real first-observation/revision bytes, without
becoming a second collector, timer or store: a non-default cadence needs its own
out_dir and is REFUSED before any vendor call when the target store holds another
cadence; the default path is unchanged (hourly, legacy receipt shape, no capture); a
retained capture is the EXACT vendor response, content-addressed, immutable and bound
by the receipt to the bytes actually written; and the observation clock is the real
post-fetch wall clock — never the bar timestamp, never ``as_of``, never an inferred
bar_end+delay.

No network, no market key: the vendor client is stubbed in every test. Capture-plumbing
proofs only — nothing here claims admission, liveness or realtime, and a retained
observation is a vendor-native aggregate (not a claim that every minute traded).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from scripts import build_polygon_intraday as bpi

OBSERVED = datetime(2026, 11, 3, 18, 45, 12, 345678, tzinfo=timezone.utc)
OBSERVED_ISO = "2026-11-03T18:45:12.345678Z"
HISTORICAL_AS_OF = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
HISTORICAL_AS_OF_ISO = "2020-01-02T03:04:05Z"

LEGACY_RECEIPT_KEYS = {
    "schema", "ticker", "source_file", "source_file_sha256", "source_available_at",
    "bar_seconds", "vendor_delay_minutes", "adjusted", "price_basis", "timestamp_basis",
    "row_count", "first_time", "last_time",
}
CAPTURE_RECEIPT_KEYS = {"observation_file", "observation_sha256", "observation_available_at"}


def _bars(*ms_close):
    """Synthetic Polygon /v2/aggs rows: (timestamp_ms, close) -> aggregate dicts."""
    return [{"t": t, "o": c, "h": c, "l": c, "c": c, "v": 100, "n": 1} for t, c in ms_close]


def _stub_vendor(monkeypatch, responses, calls=None):
    """Stub the entitled client; ``responses`` holds one row-list per call."""
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: True)
    queue = list(responses)

    def _get(self, path, params=None):
        if calls is not None:
            calls.append((path, params))
        return queue.pop(0) if queue else []

    monkeypatch.setattr(bpi.PolygonOptions, "_get", _get)


def _pin_clock(monkeypatch, moment=OBSERVED):
    monkeypatch.setattr(bpi, "_utc_now", lambda: moment)


def _capture_dir(outdir):
    return outdir / bpi.OBSERVATION_DIRNAME


# --------------------------------------------------------------------------- #
# Default contract: unchanged, hourly, no capture.
# --------------------------------------------------------------------------- #

def test_default_run_keeps_the_legacy_hourly_contract(monkeypatch, tmp_path):
    """No override -> configured hourly cadence, legacy receipt shape, no capture."""
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    _pin_clock(monkeypatch)

    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path)

    assert out == {"status": "ok", "rows": 1, "appended": 1, "delayed_min": 15}
    assert "/range/1/hour/" in calls[0][0]
    receipt = json.loads((tmp_path / "AAPL.parquet.receipt.json").read_text())
    assert set(receipt) == LEGACY_RECEIPT_KEYS          # no capture fields on the default path
    assert receipt["bar_seconds"] == 3600
    assert receipt["vendor_delay_minutes"] == 15
    assert receipt["price_basis"] == bpi.PRICE_BASIS
    assert receipt["timestamp_basis"] == bpi.TIMESTAMP_BASIS
    meta = json.loads((tmp_path / "_meta.json").read_text())
    assert meta["bar"] == "1hour"
    assert meta["delayed_min"] == 15
    assert meta["realtime"] is False
    assert not _capture_dir(tmp_path).exists()            # nothing retained by default


# --------------------------------------------------------------------------- #
# Cadence reuse: separate outbound mult/span, separate store, refused on mismatch.
# --------------------------------------------------------------------------- #

def test_nondefault_cadence_requires_an_explicit_out_dir(monkeypatch, tmp_path):
    """A non-default cadence may not fall back to the default store."""
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    monkeypatch.setattr(bpi.config, "data_dir", lambda: tmp_path / "data")

    with pytest.raises(bpi.IntradayRefusal):
        bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"])

    assert calls == []                                    # refused before any vendor call
    assert not (tmp_path / "data" / "intraday").exists()  # and before any store mutation


def test_cadence_mismatch_is_refused_before_any_vendor_call(monkeypatch, tmp_path):
    """An hourly store must never be overwritten with 30-minute bars."""
    store = tmp_path / "intraday"
    store.mkdir()
    existing_receipt = store / "AAPL.parquet.receipt.json"
    original = {
        "schema": bpi.PRICE_RECEIPT_SCHEMA,
        "ticker": "AAPL",
        "source_file": "AAPL.parquet",
        "source_file_sha256": "0" * 64,
        "source_available_at": OBSERVED_ISO,
        "bar_seconds": 3600,
        "vendor_delay_minutes": 15,
        "adjusted": True,
        "price_basis": bpi.PRICE_BASIS,
        "timestamp_basis": bpi.TIMESTAMP_BASIS,
        "row_count": 1,
        "first_time": OBSERVED_ISO,
        "last_time": OBSERVED_ISO,
    }
    existing_receipt.write_text(json.dumps(original))
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)

    with pytest.raises(bpi.IntradayRefusal) as excinfo:
        bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"], out_dir=store)

    assert "3600" in str(excinfo.value) or "cadence" in str(excinfo.value)
    assert calls == []                                    # refused before the network
    assert json.loads(existing_receipt.read_text()) == original   # hourly receipt untouched
    assert not (store / "AAPL.parquet").exists()


def test_cadence_mismatch_is_refused_from_the_store_sidecar_too(monkeypatch, tmp_path):
    """The sidecar is cadence metadata too: 30-minute into an hourly store."""
    store = tmp_path / "intraday"
    store.mkdir()
    (store / "_meta.json").write_text(json.dumps({"store": "polygon_intraday", "bar": "1hour"}))
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)

    with pytest.raises(bpi.IntradayRefusal):
        bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"], out_dir=store)
    assert calls == []


def test_nondefault_cadence_separates_outbound_mult_span_and_outdir(monkeypatch, tmp_path):
    """30-minute bars go out as 30/minute into their own store, not the hourly one."""
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    _pin_clock(monkeypatch)
    default_root = tmp_path / "default-data"
    monkeypatch.setattr(bpi.config, "data_dir", lambda: default_root)
    store = tmp_path / "intraday_30m"

    out = bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"], out_dir=store)

    assert out["status"] == "ok" and out["rows"] == 1
    assert "/range/30/minute/" in calls[0][0]
    assert calls[0][1]["adjusted"] == "true"              # the existing query contract is kept
    assert (store / "AAPL.parquet").exists()
    assert not (default_root / "intraday").exists()       # the hourly store is untouched
    receipt = json.loads((store / "AAPL.parquet.receipt.json").read_text())
    assert receipt["bar_seconds"] == 1800
    assert json.loads((store / "_meta.json").read_text())["bar"] == "30minute"


def test_a_second_nondefault_run_into_its_own_store_is_allowed(monkeypatch, tmp_path):
    """The guard is not a blanket refusal: the 30-minute store accepts 30-minute bars."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((2_000, 11.0))])
    _pin_clock(monkeypatch)
    store = tmp_path / "intraday_30m"

    first = bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"], out_dir=store)
    second = bpi.accrue(multiplier=30, timespan="minute", only=["AAPL"], out_dir=store)

    assert first["status"] == "ok" and second["status"] == "ok"
    assert second["rows"] == 1
    receipt = json.loads((store / "AAPL.parquet.receipt.json").read_text())
    assert receipt["bar_seconds"] == 1800


def test_the_default_cadence_is_refused_into_a_nondefault_store(monkeypatch, tmp_path):
    """Symmetric protection: hourly bars must not land in a 30-minute store."""
    store = tmp_path / "intraday_30m"
    store.mkdir()
    (store / "AAPL.parquet.receipt.json").write_text(json.dumps({
        "schema": bpi.PRICE_RECEIPT_SCHEMA, "ticker": "AAPL",
        "source_file": "AAPL.parquet", "source_file_sha256": "0" * 64,
        "source_available_at": OBSERVED_ISO, "bar_seconds": 1800,
        "vendor_delay_minutes": 15, "adjusted": True,
        "price_basis": bpi.PRICE_BASIS, "timestamp_basis": bpi.TIMESTAMP_BASIS,
        "row_count": 1, "first_time": OBSERVED_ISO, "last_time": OBSERVED_ISO,
    }))
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)

    with pytest.raises(bpi.IntradayRefusal):
        bpi.accrue(only=["AAPL"], out_dir=store)

    assert calls == []


def test_explicit_empty_universe_never_falls_back_to_the_full_universe(monkeypatch, tmp_path):
    """only=[] means ZERO symbols — it must not become a default full-universe fetch."""
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    monkeypatch.setattr(bpi, "_universe", lambda: ["AAPL", "MSFT"])

    out = bpi.accrue(only=[], out_dir=tmp_path)

    assert out["status"] == "stale" and out["rows"] == 0
    assert calls == []
    assert not list(tmp_path.glob("*.parquet"))
    assert not _capture_dir(tmp_path).exists()


def test_no_key_is_a_clean_noop_and_mutates_nothing(monkeypatch, tmp_path):
    """No key -> no store, no capture, no network: the nightly collect must not break."""
    monkeypatch.setattr(bpi.PolygonOptions, "enabled", lambda self: False)
    store = tmp_path / "intraday"

    out = bpi.accrue(only=["AAPL"], out_dir=store, retain_observations=True)

    assert out == {"status": "skipped", "rows": 0}
    assert not store.exists()


# --------------------------------------------------------------------------- #
# The observation itself: exact vendor bytes, honest clock, immutable capture.
# --------------------------------------------------------------------------- #

def test_observation_clock_is_the_post_fetch_wall_clock_not_as_of_or_bar_time(
        monkeypatch, tmp_path):
    """source_observed_at is the real post-response clock — not the bar time, not as_of."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    _pin_clock(monkeypatch)

    bpi.accrue(as_of=HISTORICAL_AS_OF, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)

    capture = next(_capture_dir(tmp_path).glob("AAPL/*.json"))
    doc = json.loads(capture.read_text())
    assert doc["source_observed_at"] == OBSERVED_ISO
    assert doc["source_observed_at"] != HISTORICAL_AS_OF_ISO
    receipt = json.loads((tmp_path / "AAPL.parquet.receipt.json").read_text())
    # the bar the vendor returned is 1970-01-01T00:00:01Z; the receipt must not use it
    assert receipt["first_time"] == "1970-01-01T00:00:01Z"
    assert receipt["source_available_at"] != "1970-01-01T00:00:01Z"
    assert doc["query_to"] == HISTORICAL_AS_OF.date().isoformat()


def test_observation_document_carries_the_exact_vendor_records(monkeypatch, tmp_path):
    """The capture IS the vendor response — exact records, exact schema, no credentials."""
    rows = _bars((1_000, 10.0), (2_000, 11.0))
    _stub_vendor(monkeypatch, [rows])
    _pin_clock(monkeypatch)

    bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)

    capture = next(_capture_dir(tmp_path).glob("AAPL/*.json"))
    doc = json.loads(capture.read_text())
    assert doc["schema"] == "polygon.intraday_observation/v1"
    assert doc["ticker"] == "AAPL"
    assert doc["multiplier"] == 1
    assert doc["timespan"] == "hour"
    assert doc["adjusted"] is True
    assert doc["price_basis"] == bpi.PRICE_BASIS
    assert doc["timestamp_basis"] == bpi.TIMESTAMP_BASIS
    assert doc["vendor_delay_minutes"] == 15
    assert doc["results"] == rows                       # the exact returned aggregates
    assert doc["query_from"] and doc["query_to"]
    raw = capture.read_text()
    assert "apikey" not in raw.lower() and "api_key" not in raw.lower()


def test_capture_is_content_addressed_and_a_correction_yields_a_distinct_capture(
        monkeypatch, tmp_path):
    """Two revisions over the SAME query window -> two captures; the first is kept."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((1_000, 99.0))])
    _pin_clock(monkeypatch)

    # full=True keeps the query window identical across both runs, so the captures differ
    # ONLY because the vendor revised the aggregate.
    bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)
    first = sorted(_capture_dir(tmp_path).glob("AAPL/*.json"))
    assert len(first) == 1

    bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)
    captures = sorted(_capture_dir(tmp_path).glob("AAPL/*.json"))
    assert len(captures) == 2                            # the earlier capture is kept
    digests = {p.stem for p in captures}
    assert len(digests) == 2
    for path in captures:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem  # content-addressed
    contents = {json.loads(p.read_text())["results"][0]["c"] for p in captures}
    assert contents == {10.0, 99.0}                      # both revisions are on disk


def test_two_receipts_bind_their_own_exact_parquet_and_capture_bytes(monkeypatch, tmp_path):
    """Each receipt names the exact parquet bytes AND the exact capture it names."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((1_000, 99.0))])
    _pin_clock(monkeypatch)

    bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)
    receipt_one = json.loads((tmp_path / "AAPL.parquet.receipt.json").read_text())
    parquet_one = hashlib.sha256((tmp_path / "AAPL.parquet").read_bytes()).hexdigest()
    assert set(receipt_one) == LEGACY_RECEIPT_KEYS | CAPTURE_RECEIPT_KEYS
    assert receipt_one["source_file_sha256"] == parquet_one
    capture_one = tmp_path / receipt_one["observation_file"]
    assert capture_one.exists()
    assert receipt_one["observation_sha256"] == hashlib.sha256(capture_one.read_bytes()).hexdigest()
    assert receipt_one["observation_available_at"] == OBSERVED_ISO
    first_digest = receipt_one["observation_sha256"]

    bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)
    receipt_two = json.loads((tmp_path / "AAPL.parquet.receipt.json").read_text())
    parquet_two = hashlib.sha256((tmp_path / "AAPL.parquet").read_bytes()).hexdigest()
    assert receipt_two["source_file_sha256"] == parquet_two
    assert receipt_two["observation_sha256"] != first_digest      # a correction, a new capture
    capture_two = tmp_path / receipt_two["observation_file"]
    assert capture_two.exists() and capture_one.exists()          # the first capture is kept
    assert receipt_two["observation_sha256"] == hashlib.sha256(capture_two.read_bytes()).hexdigest()


def test_unequal_bytes_at_a_capture_path_are_refused_and_never_overwritten(
        monkeypatch, tmp_path):
    """A content-addressed path holding different bytes is a collision: refuse, keep it."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((1_000, 10.0))])
    _pin_clock(monkeypatch)

    bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
               retain_observations=True)
    capture = next(_capture_dir(tmp_path).glob("AAPL/*.json"))
    capture.write_bytes(b"tampered-not-the-retained-bytes\n")
    receipt_before = (tmp_path / "AAPL.parquet.receipt.json").read_bytes()

    out = bpi.accrue(as_of=HISTORICAL_AS_OF, full=True, only=["AAPL"], out_dir=tmp_path,
                     retain_observations=True)

    assert out["status"] == "stale" and out["rows"] == 0       # the ticker was refused
    assert capture.read_bytes() == b"tampered-not-the-retained-bytes\n"   # never overwritten
    assert (tmp_path / "AAPL.parquet.receipt.json").read_bytes() == receipt_before


def test_credentials_in_a_vendor_row_are_refused_not_scrubbed(monkeypatch, tmp_path):
    """A response carrying credential material is refused, never retained."""
    rows = _bars((1_000, 10.0))
    rows[0]["apiKey"] = "secret-value"
    _stub_vendor(monkeypatch, [rows])
    _pin_clock(monkeypatch)

    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)

    assert out["status"] == "stale" and out["rows"] == 0
    captures = list(_capture_dir(tmp_path).glob("AAPL/*.json")) if _capture_dir(tmp_path).exists() else []
    assert captures == []                                  # nothing retained, so no secret on disk
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()


def test_a_naive_observation_clock_is_refused(monkeypatch, tmp_path):
    """An unaware clock attests nothing: the capture is refused, nothing is written."""
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    monkeypatch.setattr(bpi, "_utc_now", lambda: datetime(2026, 11, 3, 18, 45, 12))

    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)

    assert out["status"] == "stale" and out["rows"] == 0
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()
    assert not (tmp_path / "AAPL.parquet").exists()
    captures = list(_capture_dir(tmp_path).glob("AAPL/*.json")) if _capture_dir(tmp_path).exists() else []
    assert captures == []


def test_capture_failure_never_yields_a_receipt_pointing_at_missing_bytes(monkeypatch, tmp_path):
    """If the capture cannot be retained, no receipt may advertise it."""
    def _boom(*args, **kwargs):
        raise bpi.ObservationCaptureError("capture refused")

    monkeypatch.setattr(bpi, "_retain_observation", _boom)
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    _pin_clock(monkeypatch)

    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)

    assert out["status"] == "stale" and out["rows"] == 0
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()
    assert not (tmp_path / "AAPL.parquet").exists()


def test_a_capture_that_vanishes_cannot_be_advertised(monkeypatch, tmp_path):
    """The receipt re-verifies the capture bytes; a missing file blocks it."""
    real_retain = bpi._retain_observation

    def _retain_then_delete(*args, **kwargs):
        binding = real_retain(*args, **kwargs)
        binding["observation_path"].unlink()          # the capture disappears before the receipt
        return binding

    monkeypatch.setattr(bpi, "_retain_observation", _retain_then_delete)
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    _pin_clock(monkeypatch)

    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)

    assert out["status"] == "stale" and out["rows"] == 0
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()


# Parent review: clock integrity, immutable publication, and schema compatibility.
def test_capture_receipt_has_its_own_version_and_default_receipt_stays_v1(monkeypatch, tmp_path):
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((1_000, 10.0))])
    _pin_clock(monkeypatch)
    captured = tmp_path / "captured"
    legacy = tmp_path / "legacy"
    bpi.accrue(only=["AAPL"], out_dir=captured, retain_observations=True)
    bpi.accrue(only=["AAPL"], out_dir=legacy)
    assert json.loads((captured / "AAPL.parquet.receipt.json").read_text())["schema"] == "polygon.intraday_price_receipt/v2"
    assert json.loads((legacy / "AAPL.parquet.receipt.json").read_text())["schema"] == "polygon.intraday_price_receipt/v1"


def test_capture_availability_clock_regression_is_not_clamped(monkeypatch, tmp_path):
    from datetime import timedelta
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    clocks = iter([OBSERVED, OBSERVED - timedelta(seconds=1)])
    monkeypatch.setattr(bpi, "_utc_now", lambda: next(clocks))
    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)
    assert out["status"] == "stale"
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()
    # The response was observed and retained, but cannot acquire a false availability.
    assert len(list(_capture_dir(tmp_path).glob("AAPL/*.json"))) == 1


def test_receipt_clock_cannot_precede_capture_availability(monkeypatch, tmp_path):
    from datetime import timedelta
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))])
    clocks = iter([OBSERVED, OBSERVED + timedelta(seconds=2), OBSERVED + timedelta(seconds=1)])
    monkeypatch.setattr(bpi, "_utc_now", lambda: next(clocks))
    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)
    assert out["status"] == "stale"
    assert not (tmp_path / "AAPL.parquet.receipt.json").exists()


def test_concurrent_publication_cannot_overwrite_unequal_capture(monkeypatch, tmp_path):
    # A competing writer creates the destination after the first existence check.
    path = tmp_path / "capture.json"
    real_link = bpi.os.link

    def race(source, destination):
        destination.write_bytes(b"other retained observation\n")
        real_link(source, destination)

    monkeypatch.setattr(bpi.os, "link", race)
    with pytest.raises(bpi.ObservationCaptureError, match="collision"):
        bpi._atomic_write_bytes(path, b"our retained observation\n", exclusive=True)
    assert path.read_bytes() == b"other retained observation\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["capture.json"]


@pytest.mark.parametrize("symbol", ["../AAPL", "AAPL/../../x", "/tmp/AAPL", "", "A" * 33])
def test_capture_symbol_cannot_escape_its_store(monkeypatch, tmp_path, symbol):
    _pin_clock(monkeypatch)
    with pytest.raises(bpi.ObservationCaptureError, match="symbol"):
        bpi._retain_observation(tmp_path, ticker=symbol, multiplier=30, timespan="minute",
                                query_from="2026-11-03", query_to="2026-11-03",
                                records=_bars((1_000, 10.0)))
    assert list(tmp_path.iterdir()) == []


def test_empty_response_does_not_refresh_last_good_receipt(monkeypatch, tmp_path):
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), []])
    _pin_clock(monkeypatch)
    bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)
    before = (tmp_path / "AAPL.parquet.receipt.json").read_bytes()
    out = bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)
    assert out["status"] == "stale"
    assert out["observations_retained"] == 0
    assert (tmp_path / "AAPL.parquet.receipt.json").read_bytes() == before


def test_retention_requires_explicit_directory_even_at_default_cadence(monkeypatch, tmp_path):
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    monkeypatch.setattr(bpi.config, "data_dir", lambda: tmp_path / "default")
    with pytest.raises(bpi.IntradayRefusal, match="explicit"):
        bpi.accrue(only=["AAPL"], retain_observations=True)
    assert calls == []
    assert not (tmp_path / "default").exists()


@pytest.mark.parametrize("first_retention", [False, True])
def test_store_receipt_contract_cannot_migrate_or_downgrade(monkeypatch, tmp_path, first_retention):
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0)), _bars((2_000, 20.0))], calls)
    _pin_clock(monkeypatch)
    bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=first_retention)
    before = {str(p.relative_to(tmp_path)): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(bpi.IntradayRefusal, match="contract"):
        bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=not first_retention)
    assert len(calls) == 1
    assert before == {str(p.relative_to(tmp_path)): p.read_bytes()
                      for p in tmp_path.rglob("*") if p.is_file()}


def test_retention_refuses_unreceipted_existing_store(monkeypatch, tmp_path):
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    (tmp_path / "AAPL.parquet").write_bytes(b"existing opaque store")
    with pytest.raises(bpi.IntradayRefusal, match="contract"):
        bpi.accrue(only=["AAPL"], out_dir=tmp_path, retain_observations=True)
    assert calls == []
    assert (tmp_path / "AAPL.parquet").read_bytes() == b"existing opaque store"


def test_capture_without_receipt_still_cannot_be_downgraded(monkeypatch, tmp_path):
    calls = []
    _stub_vendor(monkeypatch, [_bars((1_000, 10.0))], calls)
    (tmp_path / bpi.OBSERVATION_DIRNAME).mkdir()
    with pytest.raises(bpi.IntradayRefusal, match="weaken"):
        bpi.accrue(only=["AAPL"], out_dir=tmp_path)
    assert calls == []
