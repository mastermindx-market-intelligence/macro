"""Strict sponsor capture through the real workbook transform; no provider calls."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
from types import SimpleNamespace
import zipfile

import pandas as pd
import pytest
import requests
from openpyxl import Workbook

from collectors import base, sector_holdings as owner
from tests.fixtures.base_sector_holdings_4eddd import OriginalSectorHoldingsAdapter


EVALUATED = datetime(2026, 11, 7, 18, tzinfo=timezone.utc)


def workbook(rows=None, *, document_date="2026-11-06", header=None, extra_preamble=None):
    book = Workbook()
    sheet = book.active
    sheet.append(["Fund", None if document_date is None else "As of " + document_date])
    for row in extra_preamble or []:
        sheet.append(row)
    sheet.append(header or ["Name", "Ticker", "Weight"])
    for row in rows if rows is not None else [["Alpha", "AAA", 4.125], ["Nano", "NA", 0]]:
        sheet.append(row)
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def capture(monkeypatch, documents, *, evaluated_at=EVALUATED, sponsors=None, clock=None):
    calls = []

    def http(self, url, **kwargs):
        fund = url.rsplit("-", 1)[1].split(".")[0].upper()
        calls.append((fund, kwargs))
        value = documents[fund]
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(content=value)

    monkeypatch.setattr(owner.SectorHoldingsAdapter, "http_get", http)
    sponsors = {"sector_funds": list(documents)} if sponsors is None else sponsors
    if clock is None:
        clock = lambda: evaluated_at + timedelta(seconds=1)
    result = owner.SectorHoldingsAdapter.capture_from_inputs(
        sponsors=sponsors, evaluated_at=evaluated_at, clock=clock)
    return result, calls


def test_same_actual_parser_preserves_legacy_top20_ties_na_names_and_rounding(monkeypatch):
    rows = [[f" Company {i} ", f" T{i:02d} ", 2.345 if i < 23 else 0]
            for i in range(27)]
    rows += [["National Bank", "NA", 3.125], ["Berkshire", "BRK.B", 3.125],
             ["Cash", "-", 50], ["Footer", None, None]]
    raw = workbook(rows)
    old = object.__new__(OriginalSectorHoldingsAdapter)
    old.http_get = lambda *a, **k: SimpleNamespace(content=raw)
    expected = old._fetch_fund("XLK")
    current = object.__new__(owner.SectorHoldingsAdapter)
    current.http_get = old.http_get
    live = current._fetch_fund("XLK")
    # The live path runs the SAME parser: identical base snapshot, plus the
    # reserved capture block the composed live acquisition stamps on every row.
    pd.testing.assert_frame_equal(
        live.drop(columns=list(owner.CAPTURE_COLUMNS)), expected)
    assert set(owner.CAPTURE_COLUMNS) <= set(live.columns)
    assert (live["capture_schema_version"] == owner.CAPTURE_SCHEMA_VERSION).all()
    assert (live["capture_fund"] == "XLK").all()
    assert (live["capture_source_url"] == owner.SSGA_XLSX.format(fund="xlk")).all()
    assert (live["capture_content_sha256"] == hashlib.sha256(raw).hexdigest()).all()
    assert (live["capture_content_bytes"] == len(raw)).all()
    assert live["capture_issuer_as_of"].eq("2026-11-06").all()
    assert (live["capture_date_origin"] == owner.DATE_ORIGIN_ISSUER_REPORTED).all()
    result, calls = capture(monkeypatch, {"XLK": raw})
    pd.testing.assert_frame_equal(result.snapshots["XLK"], expected)
    assert len(expected) == 20
    assert list(expected["rank"]) == list(range(1, 21))
    assert list(expected["ticker"][:2]) == ["NA", "BRK.B"]
    assert calls == [("XLK", {"retries": 3, "timeout": 60,
                            "headers": {"User-Agent": "Mozilla/5.0 (research)"}})]
    fact = result.evidence["XLK"]
    assert fact["document_date"] == "2026-11-06"
    assert fact["sha256"] == hashlib.sha256(raw).hexdigest()
    assert fact["byte_length"] == len(raw)
    assert result.workbooks["XLK"] == raw
    assert fact["published_at"] is None
    assert result.available


@pytest.mark.parametrize(("document_date", "reason"), [
    (None, "date_missing"), ("not a date", "date_invalid"),
    ("2026-11-08", "date_future"), ("2026-11-06 12:00:00", "date_invalid"),
])
def test_missing_invalid_future_and_timed_document_dates_never_fallback(monkeypatch, document_date, reason):
    class NoToday(date):
        @classmethod
        def today(cls):
            raise AssertionError("wall-clock fallback")
    monkeypatch.setattr(owner, "date", NoToday)
    raw = workbook(document_date=document_date)
    result, _ = capture(monkeypatch, {"XLK": raw})
    assert not result.available
    assert result.snapshots == {"XLK": None}
    assert result.evidence["XLK"]["outcome"] == "malformed"
    assert reason in result.evidence["XLK"]["reason"]
    assert result.evidence["XLK"]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_document_date_uses_us_local_day_and_older_funds_stay_older(monkeypatch):
    evaluation = datetime(2026, 11, 7, 1, tzinfo=timezone.utc)
    result, _ = capture(monkeypatch, {
        "XLK": workbook(document_date="2026-11-05"),
        "XLF": workbook(document_date="2026-11-06"),
        "XLY": workbook(document_date="2026-11-07"),
    }, evaluated_at=evaluation)
    assert result.evidence["XLK"]["document_date"] == "2026-11-05"
    assert result.evidence["XLF"]["document_date"] == "2026-11-06"
    assert result.evidence["XLY"]["outcome"] == "malformed"
    assert all(x["evaluated_at"] == evaluation.isoformat() for x in result.evidence.values())
    assert result.snapshots["XLK"].index[0] == pd.Timestamp("2026-11-05")


def test_live_missing_date_uses_labelled_retrieval_fallback(monkeypatch):
    raw = workbook(document_date=None)
    adapter = object.__new__(owner.SectorHoldingsAdapter)
    adapter.http_get = lambda *a, **k: SimpleNamespace(content=raw)
    retrieved = datetime(2026, 11, 7, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(owner, "_utc_now", lambda: retrieved)
    snap = adapter._fetch_fund("XLK")
    # No issuer date stated: the index date is the retrieval date and is
    # LABELLED as a fallback so it is never read as issuer-effective.
    assert snap.index[0] == pd.Timestamp("2026-11-07")
    assert (snap["capture_date_origin"] == owner.DATE_ORIGIN_RETRIEVAL_FALLBACK).all()
    assert snap["capture_issuer_as_of"].isna().all()
    assert snap["capture_retrieved_at"].eq(retrieved.isoformat()).all()


@pytest.mark.parametrize("rows", [
    [["A", "AAA", -0.1]], [["A", "AAA", 100.01]],
    [["A", "AAA", "inf"]], [["A", "AAA", "-inf"]],
    [["A", "AAA", "nan"]], [["A", "AAA", "bad"]],
    [["A", "AAA", None]], [["A", "AAA", True]],
    [["A", "AAA", 1], ["B", " AAA ", 2]],
    [["A", "   ", 1]], [["A", 123, 1]],
    [["A", "X" * 33, 1]],
])
def test_invalid_or_duplicate_actual_holding_rows_refuse(monkeypatch, rows):
    result, _ = capture(monkeypatch, {"XLK": workbook(rows)})
    assert not result.available
    assert result.evidence["XLK"]["outcome"] == "malformed"


@pytest.mark.parametrize("rows", [[], [["Cash", "-", 100]], [["Footer", None, None]]])
def test_empty_effective_snapshot_remains_unavailable(monkeypatch, rows):
    result, _ = capture(monkeypatch, {"XLK": workbook(rows)})
    assert not result.available
    assert result.evidence["XLK"]["reason"] == "holdings_snapshot_empty"


def test_zero_weight_is_present_and_not_missing(monkeypatch):
    result, _ = capture(monkeypatch, {"XLK": workbook([["Nano", "NA", 0]])})
    assert result.available
    assert result.snapshots["XLK"].iloc[0]["weight_pct"] == 0


@pytest.mark.parametrize("header", [
    ["Name", "Ticker", "Weight", "Weight %"],
    ["Name", "Ticker", "Weight", "Ticker"],
    ["Name", "Symbol", "Weight"],
])
def test_ambiguous_or_unusable_columns_refuse(monkeypatch, header):
    result, _ = capture(monkeypatch, {"XLK": workbook(header=header)})
    assert not result.available
    assert result.evidence["XLK"]["outcome"] == "malformed"


def test_multiple_headers_and_document_dates_refuse(monkeypatch):
    for raw in (
        workbook([["Name", "Ticker", "Weight"], ["A", "AAA", 1]]),
        workbook(extra_preamble=[["Again", "As of 2026-11-06"]]),
    ):
        result, _ = capture(monkeypatch, {"XLK": raw})
        assert not result.available
        assert "ambiguous" in result.evidence["XLK"]["reason"]


def test_partial_all_failed_and_404_outcomes_are_named(monkeypatch):
    missing = requests.HTTPError("missing", response=SimpleNamespace(status_code=404))
    result, _ = capture(monkeypatch, {
        "XLK": workbook(), "XLF": b"not a workbook",
        "XLY": requests.Timeout("private diagnostic"), "XLE": missing,
    })
    assert result.available
    assert {f: x["outcome"] for f, x in result.evidence.items()} == {
        "XLK": "present", "XLF": "malformed", "XLY": "unreadable", "XLE": "absent"}
    assert result.evidence["XLY"]["reason"] == "http_Timeout"
    assert all(result.snapshots[f] is None for f in ("XLF", "XLY", "XLE"))
    failed, _ = capture(monkeypatch, {"XLK": b"bad", "XLF": missing})
    assert not failed.available
    assert set(failed.evidence) == {"XLK", "XLF"}
    assert all(value is None for value in failed.snapshots.values())


def test_explicit_inputs_and_returned_objects_are_detached(monkeypatch):
    config = {"sector_funds": ["XLK", "XLF"], "unused": {"nested": [1]}}
    raw = workbook()
    called = []
    def http(self, url, **kwargs):
        called.append(url)
        config["sector_funds"][:] = ["XLY"]
        config["unused"]["nested"].append(2)
        return SimpleNamespace(content=raw)
    monkeypatch.setattr(owner.SectorHoldingsAdapter, "http_get", http)
    result = owner.SectorHoldingsAdapter.capture_from_inputs(
        sponsors=config, evaluated_at=EVALUATED,
        clock=lambda: EVALUATED + timedelta(seconds=1))
    assert len(called) == 2 and "xlf.xlsx" in called[1]
    assert set(result.snapshots) == {"XLK", "XLF"}
    snap = result.snapshots
    snap["XLK"].iloc[0, 0] = "changed"
    facts = result.evidence
    facts["XLK"]["document_date"] = "changed"
    documents = result.workbooks
    documents["XLK"] = b"changed"
    assert result.snapshots["XLK"].iloc[0]["ticker"] == "AAA"
    assert result.evidence["XLK"]["document_date"] == "2026-11-06"
    assert result.workbooks["XLK"] == raw
    arguments = result.assembly_arguments()
    arguments["holdings"]["XLF"].iloc[0, 0] = "changed"
    assert result.snapshots["XLF"].iloc[0]["ticker"] == "AAA"


def test_actual_http_owner_retains_retry_boundary_without_ambient_reads_or_writers(monkeypatch):
    raw = workbook()
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient configuration/store/history/clock touched")
    for obj, name in (
        (owner.SectorHoldingsAdapter, "__init__"),
        (owner.SectorHoldingsAdapter, "_merge_write"),
        (owner.SectorHoldingsAdapter, "_append_history"),
        (owner.config, "load"), (owner.config, "data_dir"),
        (owner.store, "read"), (pd, "read_parquet"),
    ):
        monkeypatch.setattr(obj, name, forbidden)
    calls, sleeps = [], []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        response = requests.Response()
        response.url = url
        response.status_code = 503 if len(calls) == 1 else 200
        response._content = raw
        return response
    monkeypatch.setattr(base.requests, "get", get)
    monkeypatch.setattr(base.time, "sleep", sleeps.append)
    result = owner.SectorHoldingsAdapter.capture_from_inputs(
        sponsors={"sector_funds": ["XLK"]}, evaluated_at=EVALUATED,
        clock=lambda: EVALUATED + timedelta(seconds=1))
    assert result.available
    assert len(calls) == 2 and sleeps == [3.0]
    assert all(c[1] == {"timeout": 60,
                       "headers": {"User-Agent": "Mozilla/5.0 (research)"}} for c in calls)


def test_shared_http_default_header_still_uses_existing_sponsor_config(monkeypatch):
    loaded, seen = [], []
    def config():
        loaded.append(True)
        return {"sponsors": {"user_agent": "existing-default"}}
    response = requests.Response()
    response.status_code = 200
    monkeypatch.setattr(base.config, "load", config)
    monkeypatch.setattr(base.requests, "get", lambda url, **kwargs:
                        seen.append(kwargs) or response)
    assert base.Adapter().http_get("https://fixture.invalid") is response
    assert loaded == [True]
    assert seen[0]["headers"]["User-Agent"] == "existing-default"


@pytest.mark.parametrize("sponsors", [
    None, {}, {"sector_funds": []}, {"sector_funds": ["XLK", "XLK"]},
    {"sector_funds": ["xlk"]}, {"sector_funds": ["../XLK"]},
    {"sector_funds": ["X" + str(i) for i in range(12)]},
])
def test_invalid_captured_choices_refuse_before_http(monkeypatch, sponsors):
    monkeypatch.setattr(owner.SectorHoldingsAdapter, "_fetch_workbook",
                        lambda *a: pytest.fail("HTTP before input validation"))
    with pytest.raises(owner.HoldingsCaptureError):
        owner.SectorHoldingsAdapter.capture_from_inputs(
            sponsors=sponsors, evaluated_at=EVALUATED, clock=lambda: EVALUATED)


@pytest.mark.parametrize("instant", [date(2026, 11, 7), datetime(2026, 11, 7), pd.NaT])
def test_unaware_or_invalid_evaluation_refuses_before_http(monkeypatch, instant):
    monkeypatch.setattr(owner.SectorHoldingsAdapter, "_fetch_workbook",
                        lambda *a: pytest.fail("HTTP before clock validation"))
    with pytest.raises(owner.HoldingsCaptureError):
        owner.SectorHoldingsAdapter.capture_from_inputs(
            sponsors={"sector_funds": ["XLK"]}, evaluated_at=instant, clock=lambda: EVALUATED)


def test_observation_clock_regression_or_naive_return_refuses(monkeypatch):
    raw = workbook()
    for clock in (lambda: EVALUATED - timedelta(seconds=1),
                  lambda: datetime(2026, 11, 7)):
        with pytest.raises(owner.HoldingsCaptureError):
            capture(monkeypatch, {"XLK": raw}, clock=clock)
    times = iter([EVALUATED + timedelta(seconds=2), EVALUATED + timedelta(seconds=1)])
    with pytest.raises(owner.HoldingsCaptureError, match="clock_regressed"):
        capture(monkeypatch, {"XLK": raw, "XLF": raw}, clock=lambda: next(times))


def repack(raw, changes):
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as old, zipfile.ZipFile(output, "w") as new:
        for item in old.infolist():
            new.writestr(item, changes.get(item.filename, old.read(item)))
    return output.getvalue()


def test_workbook_encoded_and_expanded_bounds_are_checked_before_pandas(monkeypatch):
    raw = workbook()
    monkeypatch.setattr(pd, "read_excel", lambda *a, **k: pytest.fail("parser reached"))
    monkeypatch.setattr(owner, "MAX_HOLDINGS_WORKBOOK_BYTES", len(raw) - 1)
    result, _ = capture(monkeypatch, {"XLK": raw})
    assert result.evidence["XLK"]["reason"] == "holdings_workbook_encoded_bound"
    monkeypatch.setattr(owner, "MAX_HOLDINGS_WORKBOOK_BYTES", len(raw) + 1)
    monkeypatch.setattr(owner, "MAX_HOLDINGS_XML_BYTES", 1)
    result, _ = capture(monkeypatch, {"XLK": raw})
    assert result.evidence["XLK"]["reason"] == "holdings_workbook_archive_bound"


@pytest.mark.parametrize(("xml", "reason"), [
    (b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:XFD1048576"/></worksheet>',
     "geometry_bound"),
    (b'<!DOCTYPE worksheet [<!ENTITY x "x">]><worksheet/>', "xml_invalid"),
])
def test_unsafe_xml_or_geometry_refuses_before_pandas(monkeypatch, xml, reason):
    raw = repack(workbook(), {"xl/worksheets/sheet1.xml": xml})
    monkeypatch.setattr(pd, "read_excel", lambda *a, **k: pytest.fail("parser reached"))
    result, _ = capture(monkeypatch, {"XLK": raw})
    assert reason in result.evidence["XLK"]["reason"]


def test_duplicate_archive_members_refuse_before_pandas(monkeypatch):
    output = io.BytesIO(workbook())
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr("xl/workbook.xml", b"duplicate")
    monkeypatch.setattr(pd, "read_excel", lambda *a, **k: pytest.fail("parser reached"))
    result, _ = capture(monkeypatch, {"XLK": output.getvalue()})
    assert result.evidence["XLK"]["reason"] == "holdings_workbook_archive_bound"


@pytest.mark.parametrize("document_date", ["2026", "2026-11", "Nov 2026", "11/2026", "11/6"])
def test_incomplete_document_date_cannot_invent_missing_calendar_components(monkeypatch, document_date):
    result, _ = capture(monkeypatch, {"XLK": workbook(document_date=document_date)})
    assert not result.available
    assert result.evidence["XLK"]["outcome"] == "malformed"


@pytest.mark.parametrize("document_date", [
    "2026-11-06", "2026/11/06", "11/06/2026", "06-Nov-2026",
    "6 November 2026", "November 6, 2026", "Nov 6 2026",
])
def test_complete_document_date_forms_keep_actual_calendar_date(monkeypatch, document_date):
    result, _ = capture(monkeypatch, {"XLK": workbook(document_date=document_date)})
    assert result.available
    assert result.evidence["XLK"]["document_date"] == "2026-11-06"
