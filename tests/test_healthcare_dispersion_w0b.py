"""W0b infrastructure tests — healthcare dispersion program.

(a) sector_holdings history archiver: appends and is idempotent per (as_of, etf).
(b) EW sector ETF tickers present in config.yml yahoo.tickers.ew_sectors.
(c) PSL-2: the per-fund capture block — what a current capture says about the
    response it came from, and which captures are refused before they can
    touch the stored snapshot.
"""
from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402

# ---------------------------------------------------------------------------
# Expected EW ticker set (RGI stands in for RSPI which Yahoo does not serve)
# ---------------------------------------------------------------------------
EW_TICKERS = {
    "RSPH",  # Health Care
    "RSPT",  # Information Technology
    "RSPD",  # Consumer Discretionary
    "RSPS",  # Consumer Staples
    "RSPG",  # Energy
    "RSPF",  # Financials
    "RSPU",  # Utilities
    "RGI",   # Industrials (legacy; RSPI not served by Yahoo as of 2026-07-05)
    "RSPM",  # Materials
    "RSPC",  # Communication Services
    "RSPR",  # Real Estate
}


# ---------------------------------------------------------------------------
# Helper: build a minimal snap DataFrame matching _fetch_fund output shape
# ---------------------------------------------------------------------------

def _make_snap(as_of: date, n: int = 3) -> pd.DataFrame:
    """Return a snapshot DataFrame as _fetch_fund would produce it."""
    rows = pd.DataFrame({
        "ticker": [f"T{i}" for i in range(n)],
        "name": [f"Name {i}" for i in range(n)],
        "weight_pct": [round(10.0 + i, 2) for i in range(n)],
        "rank": list(range(1, n + 1)),
    })
    rows.index = pd.to_datetime([as_of] * n)
    return rows


# ---------------------------------------------------------------------------
# (a) History archiver tests
# ---------------------------------------------------------------------------

class TestHoldingsHistoryArchiver:
    """Unit tests for SectorHoldingsAdapter._append_history."""

    def _adapter(self, tmp_path: Path):
        """Return a SectorHoldingsAdapter with data_dir monkeypatched to tmp_path."""
        from collectors.sector_holdings import SectorHoldingsAdapter
        import lib.config as cfg_mod

        # Patch config.data_dir() to use tmp_path for this test
        original_data_dir = cfg_mod.data_dir

        def patched_data_dir():
            return tmp_path

        cfg_mod.data_dir = patched_data_dir  # type: ignore[method-assign]
        adapter = SectorHoldingsAdapter.__new__(SectorHoldingsAdapter)
        adapter.group = "sector_holdings"
        yield adapter
        cfg_mod.data_dir = original_data_dir  # type: ignore[method-assign]

    def test_append_creates_history_file(self, tmp_path):
        """_append_history creates history.parquet on first call."""
        from collectors.sector_holdings import SectorHoldingsAdapter
        import lib.config as cfg_mod

        original = cfg_mod.data_dir
        cfg_mod.data_dir = lambda: tmp_path  # type: ignore[method-assign]
        try:
            (tmp_path / "sector_holdings").mkdir()
            adapter = SectorHoldingsAdapter.__new__(SectorHoldingsAdapter)
            adapter.group = "sector_holdings"
            snap = _make_snap(date(2026, 7, 5))
            adapter._append_history("XLV", snap)
            hist_path = tmp_path / "sector_holdings" / "history.parquet"
            assert hist_path.exists()
            df = pd.read_parquet(hist_path)
            assert list(df.columns) == ["as_of", "etf", "ticker", "name", "weight_pct", "rank"]
            assert len(df) == 3
            assert (df["etf"] == "XLV").all()
        finally:
            cfg_mod.data_dir = original  # type: ignore[method-assign]

    def test_append_idempotent_same_day(self, tmp_path):
        """Re-running on the same day replaces rather than duplicates rows."""
        from collectors.sector_holdings import SectorHoldingsAdapter
        import lib.config as cfg_mod

        original = cfg_mod.data_dir
        cfg_mod.data_dir = lambda: tmp_path  # type: ignore[method-assign]
        try:
            (tmp_path / "sector_holdings").mkdir()
            adapter = SectorHoldingsAdapter.__new__(SectorHoldingsAdapter)
            adapter.group = "sector_holdings"
            snap = _make_snap(date(2026, 7, 5))
            adapter._append_history("XLV", snap)
            adapter._append_history("XLV", snap)  # second call — same day
            hist_path = tmp_path / "sector_holdings" / "history.parquet"
            df = pd.read_parquet(hist_path)
            # Should still have exactly 3 rows (not 6)
            xlv = df[df["etf"] == "XLV"]
            as_of_date = pd.Timestamp("2026-07-05").date()
            xlv_today = xlv[pd.to_datetime(xlv["as_of"]).dt.date == as_of_date]
            assert len(xlv_today) == 3, (
                f"Expected 3 rows after idempotent re-run, got {len(xlv_today)}"
            )
        finally:
            cfg_mod.data_dir = original  # type: ignore[method-assign]

    def test_append_accumulates_across_days(self, tmp_path):
        """Two different as_of dates produce separate rows in history."""
        from collectors.sector_holdings import SectorHoldingsAdapter
        import lib.config as cfg_mod

        original = cfg_mod.data_dir
        cfg_mod.data_dir = lambda: tmp_path  # type: ignore[method-assign]
        try:
            (tmp_path / "sector_holdings").mkdir()
            adapter = SectorHoldingsAdapter.__new__(SectorHoldingsAdapter)
            adapter.group = "sector_holdings"
            snap_d1 = _make_snap(date(2026, 7, 4))
            snap_d2 = _make_snap(date(2026, 7, 5))
            adapter._append_history("XLV", snap_d1)
            adapter._append_history("XLV", snap_d2)
            hist_path = tmp_path / "sector_holdings" / "history.parquet"
            df = pd.read_parquet(hist_path)
            dates = pd.to_datetime(df["as_of"]).dt.date.unique()
            assert date(2026, 7, 4) in dates
            assert date(2026, 7, 5) in dates
            assert len(df) == 6  # 3 rows × 2 dates
        finally:
            cfg_mod.data_dir = original  # type: ignore[method-assign]

    def test_multiple_etfs_do_not_cross_contaminate(self, tmp_path):
        """Rows for different ETFs on the same day coexist without collision."""
        from collectors.sector_holdings import SectorHoldingsAdapter
        import lib.config as cfg_mod

        original = cfg_mod.data_dir
        cfg_mod.data_dir = lambda: tmp_path  # type: ignore[method-assign]
        try:
            (tmp_path / "sector_holdings").mkdir()
            adapter = SectorHoldingsAdapter.__new__(SectorHoldingsAdapter)
            adapter.group = "sector_holdings"
            as_of = date(2026, 7, 5)
            adapter._append_history("XLV", _make_snap(as_of))
            adapter._append_history("XLK", _make_snap(as_of))
            hist_path = tmp_path / "sector_holdings" / "history.parquet"
            df = pd.read_parquet(hist_path)
            assert set(df["etf"].unique()) == {"XLV", "XLK"}
            # Idempotency for XLV must not affect XLK rows
            adapter._append_history("XLV", _make_snap(as_of))
            df2 = pd.read_parquet(hist_path)
            assert len(df2[df2["etf"] == "XLK"]) == 3
            assert len(df2[df2["etf"] == "XLV"]) == 3
        finally:
            cfg_mod.data_dir = original  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# (b) EW ticker list presence in config
# ---------------------------------------------------------------------------

def test_ew_tickers_in_config():
    """All expected EW sector tickers must be listed in config.yml yahoo.tickers.ew_sectors."""
    cfg = config.load()
    ew = set(cfg["yahoo"]["tickers"].get("ew_sectors", []))
    missing = EW_TICKERS - ew
    assert not missing, (
        f"EW tickers missing from config.yml yahoo.tickers.ew_sectors: {sorted(missing)}"
    )


def test_ew_tickers_all_known_good():
    """ew_sectors list must not contain any unknown tickers beyond the expected set."""
    cfg = config.load()
    ew = set(cfg["yahoo"]["tickers"].get("ew_sectors", []))
    unknown = ew - EW_TICKERS
    assert not unknown, (
        f"Unexpected tickers in ew_sectors (not in empirically verified set): {sorted(unknown)}"
    )


def test_ew_sectors_key_exists():
    """config.yml must have a yahoo.tickers.ew_sectors key (not silently absent)."""
    cfg = config.load()
    assert "ew_sectors" in cfg["yahoo"]["tickers"], (
        "yahoo.tickers.ew_sectors key is missing from config.yml"
    )


# ---------------------------------------------------------------------------
# (c) PSL-2 — the per-fund capture block
# ---------------------------------------------------------------------------
#
# A current capture records WHERE it came from and WHEN it was fetched, in the
# per-fund parquet that already stores the snapshot. These tests drive the
# collector with FAKE responses and a FAKE clock — no provider is contacted and
# no production data/ or site/ tree is touched.
#
# The fake response body is a real (zip) XLSX-shaped byte stream and the
# reader is a stand-in that RECORDS the exact bytes it was handed, so the
# capture's digest and byte length are checked against the response body
# itself. No spreadsheet engine is needed for the main cases — the CI gates
# that own these files do not install one — and one extra test covers the
# real pandas/openpyxl parse path wherever an engine IS installed.


def _ssga_rows(as_of=None, second_as_of=None, weights=(14.21, 12.05, 6.33)):
    """A fake SSGA-shaped sheet: the fund line, the as-of line(s), the header
    row ("Name" in column 0) and the holding rows below it."""
    rows = [[None, "SPDR S&P 500 ETF Trust (XLK)"]]
    if as_of is not None:
        rows.append([None, f"As of {as_of}"])
    if second_as_of is not None:
        rows.append([None, f"As of {second_as_of}"])
    rows.append(["Name", "Ticker", "Weight", "Shares"])
    for i, (ticker, weight) in enumerate(zip(("NVDA", "AAPL", "MSFT"), weights)):
        rows.append([f"{ticker} INC", ticker, weight, 1000 - i])
    return rows


def _fake_xlsx_bytes(tag: str) -> bytes:
    """A deterministic, engine-free stand-in for an XLSX response body.

    A real zip container (the shape an XLSX has), so the body the collector
    hashes and measures is a genuine byte stream — and distinct per scenario,
    so two captures of the same day differ in digest.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in (("[Content_Types].xml", "<Types/>"),
                              ("xl/workbook.xml", f"<workbook>{tag}</workbook>")):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 6, 0, 0, 0))
            archive.writestr(info, payload)
    return buffer.getvalue()


def _raw_sheet_frame(rows) -> pd.DataFrame:
    """The frame a spreadsheet reader returns for these sheet rows
    (header=None): blank cells decode as NaN, numbers stay numbers."""
    width = max(len(row) for row in rows)
    padded = [[float("nan") if cell is None else cell for cell in row]
              + [float("nan")] * (width - len(row)) for row in rows]
    return pd.DataFrame(padded, dtype=object)


def _fake_reader(rows):
    """A read_excel stand-in that returns the sheet frame and RECORDS the
    exact bytes it was handed."""
    def _read(buffer, **_kwargs):
        _read.calls.append(buffer.getvalue())
        return _raw_sheet_frame(rows)

    _read.calls = []
    return _read


class _FakeResponse:
    """A response carrying only the body the collector hashes."""

    def __init__(self, content: bytes) -> None:
        self.content = content


class TestHoldingsCaptureProvenance:
    """The capture block, and the captures that must be refused."""

    def _adapter(self, tmp_path, monkeypatch, content, *, now, rows=None,
                 funds=("XLK",)):
        import lib.config as cfg_mod
        from collectors import sector_holdings as sh

        monkeypatch.setattr(cfg_mod, "data_dir", lambda: tmp_path)
        monkeypatch.setattr(sh, "_utc_now", lambda: now)
        adapter = sh.SectorHoldingsAdapter.__new__(sh.SectorHoldingsAdapter)
        adapter.group = "sector_holdings"
        adapter.cfg = {"sector_funds": list(funds)}
        adapter.requested_urls = []
        adapter.reader = None
        if rows is not None:
            adapter.reader = _fake_reader(rows)
            monkeypatch.setattr(pd, "read_excel", adapter.reader)

        def _http_get(url, **_kwargs):
            adapter.requested_urls.append(url)
            return _FakeResponse(content)

        monkeypatch.setattr(adapter, "http_get", _http_get)
        return adapter

    # -- the captured fields ------------------------------------------------

    @pytest.mark.parametrize("issuer_date", [
        "11/06/2026", "11/6/2026", "2026-11-06",
        "Nov 6 2026", "Nov 06, 2026", "November 6, 2026",
    ])
    def test_a_valid_issuer_date_captures_the_exact_response_and_clock(
            self, tmp_path, monkeypatch, issuer_date):
        from collectors import sector_holdings as sh

        rows = _ssga_rows(as_of=issuer_date)
        content = _fake_xlsx_bytes("xlk-2026-11-06")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now, rows=rows)

        snap = adapter._fetch_fund("XLK")

        assert adapter.requested_urls == [sh.SSGA_XLSX.format(fund="xlk")]
        # the EXACT response body is what the reader was handed
        assert adapter.reader.calls == [content]
        assert list(snap.index) == [pd.Timestamp("2026-11-06")] * len(snap)
        assert snap["capture_schema_version"].unique().tolist() == [
            sh.CAPTURE_SCHEMA_VERSION]
        assert snap["capture_fund"].unique().tolist() == ["XLK"]
        assert snap["capture_source_url"].unique().tolist() == [
            sh.SSGA_XLSX.format(fund="xlk")]
        assert snap["capture_content_sha256"].unique().tolist() == [
            hashlib.sha256(content).hexdigest()]
        assert snap["capture_content_bytes"].unique().tolist() == [len(content)]
        assert snap["capture_retrieved_at"].unique().tolist() == [now.isoformat()]
        assert snap["capture_issuer_as_of"].unique().tolist() == ["2026-11-06"]
        assert snap["capture_date_origin"].unique().tolist() == [
            sh.DATE_ORIGIN_ISSUER_REPORTED]
        # the SAME block on every incoming row
        assert snap[list(sh.CAPTURE_COLUMNS)].nunique().max() == 1
        assert len(snap) == 3  # the three fake holding rows

    def test_a_missing_issuer_date_falls_back_to_the_retrieval_date_and_says_so(
            self, tmp_path, monkeypatch):
        from collectors import sector_holdings as sh

        rows = _ssga_rows(as_of=None)
        content = _fake_xlsx_bytes("xlk-no-as-of")
        now = datetime(2026, 11, 7, 0, 0, 1, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now, rows=rows)

        snap = adapter._fetch_fund("XLK")

        assert list(snap.index) == [pd.Timestamp("2026-11-07")] * len(snap)
        assert snap["capture_issuer_as_of"].isna().all()
        assert snap["capture_date_origin"].unique().tolist() == [
            sh.DATE_ORIGIN_RETRIEVAL_FALLBACK]
        # the retrieval instant is still recorded
        assert snap["capture_retrieved_at"].unique().tolist() == [now.isoformat()]

    @pytest.mark.parametrize(
        ("now", "expected"),
        [
            (datetime(2026, 11, 6, 23, 59, 59, 999999, tzinfo=timezone.utc),
             "2026-11-06"),
            (datetime(2026, 11, 7, 0, 0, 0, tzinfo=timezone.utc), "2026-11-07"),
        ],
        ids=["last-microsecond-of-the-day", "first-microsecond-of-the-day"],
    )
    def test_the_fallback_index_is_the_retrieval_instant_at_utc_midnight(
            self, tmp_path, monkeypatch, now, expected):
        rows = _ssga_rows(as_of=None)
        content = _fake_xlsx_bytes("xlk-midnight")
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now, rows=rows)

        snap = adapter._fetch_fund("XLK")

        assert snap.index[0] == pd.Timestamp(expected)
        assert snap.index[0] == snap.index[0].normalize()  # midnight, not a clock time
        assert snap["capture_retrieved_at"].iloc[0] == now.isoformat()

    # -- refusals, BEFORE the stored snapshot is touched ---------------------

    def _stored(self, tmp_path, day="2026-11-05"):
        store = tmp_path / "sector_holdings"
        store.mkdir(parents=True, exist_ok=True)
        stored = pd.DataFrame(
            {"ticker": ["NVDA"], "name": ["NVDA INC"], "weight_pct": [1.0],
             "rank": [1]},
            index=pd.to_datetime([day]))
        stored.to_parquet(store / "XLK.parquet")
        return store, (store / "XLK.parquet").read_bytes()

    @pytest.mark.parametrize(
        ("rows", "match"),
        [
            (_ssga_rows(as_of="not a date"), "malformed"),
            (_ssga_rows(as_of="11/06/2026", second_as_of="11/05/2026"), "conflict"),
            (_ssga_rows(as_of="2026"), "malformed"),
            (_ssga_rows(as_of="2026-11"), "malformed"),
            (_ssga_rows(as_of="November 2026"), "malformed"),
            (_ssga_rows(as_of="today"), "malformed"),
            (_ssga_rows(as_of="now"), "malformed"),
            (_ssga_rows(as_of="11/06/26"), "malformed"),
            (_ssga_rows(as_of="31/12/2026"), "malformed"),
            (_ssga_rows(as_of="2026-11-06T00:00:00"), "malformed"),
            (_ssga_rows(as_of="2026-02-29"), "malformed"),
        ],
        ids=["malformed-issuer-date", "conflicting-issuer-dates",
             "year-only", "year-month", "month-year", "relative-today",
             "relative-now", "two-digit-year", "undeclared-day-first",
             "timestamp-not-calendar-date", "invalid-leap-day"],
    )
    def test_a_refused_issuer_date_never_touches_the_stored_snapshot(
            self, tmp_path, monkeypatch, rows, match):
        store, before = self._stored(tmp_path)
        content = _fake_xlsx_bytes(f"refused-{match}")
        adapter = self._adapter(tmp_path, monkeypatch, content, rows=rows,
                                now=datetime(2026, 11, 6, 21, 0, 0, tzinfo=timezone.utc))

        with pytest.raises(RuntimeError, match=match):
            adapter.fetch()

        assert (store / "XLK.parquet").read_bytes() == before
        assert not (store / "history.parquet").exists()

    # -- the store -----------------------------------------------------------

    def test_the_capture_block_survives_the_parquet_round_trip(
            self, tmp_path, monkeypatch):
        from collectors import sector_holdings as sh

        content = _fake_xlsx_bytes("xlk-round-trip")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now,
                                rows=_ssga_rows(as_of="11/06/2026"))

        adapter._merge_write("XLK", adapter._fetch_fund("XLK"))
        stored = pd.read_parquet(tmp_path / "sector_holdings" / "XLK.parquet")

        assert list(stored["capture_schema_version"]) == [
            sh.CAPTURE_SCHEMA_VERSION] * len(stored)
        assert stored["capture_content_sha256"].iloc[0] == hashlib.sha256(
            content).hexdigest()
        assert int(stored["capture_content_bytes"].iloc[0]) == len(content)
        assert stored["capture_retrieved_at"].iloc[0] == now.isoformat()
        assert stored["capture_issuer_as_of"].iloc[0] == "2026-11-06"
        assert stored["capture_date_origin"].iloc[0] == sh.DATE_ORIGIN_ISSUER_REPORTED

    def test_legacy_rows_keep_null_metadata_and_are_never_backfilled(
            self, tmp_path, monkeypatch):
        from collectors import sector_holdings as sh

        store, _ = self._stored(tmp_path, day="2026-11-04")
        content = _fake_xlsx_bytes("xlk-legacy-neighbour")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now,
                                rows=_ssga_rows(as_of="11/06/2026"))

        adapter._merge_write("XLK", adapter._fetch_fund("XLK"))
        stored = pd.read_parquet(store / "XLK.parquet")

        old = stored.loc[[pd.Timestamp("2026-11-04")]]
        new = stored.loc[[pd.Timestamp("2026-11-06")]]
        assert old[list(sh.CAPTURE_COLUMNS)].isna().all().all()
        assert new["capture_content_sha256"].nunique() == 1
        assert new["capture_content_sha256"].iloc[0] == hashlib.sha256(
            content).hexdigest()
        # the legacy rows were NOT relabelled with the latest capture
        assert old["capture_content_sha256"].isna().all()

    def test_a_same_date_replacement_takes_the_new_capture_and_adds_no_lineage(
            self, tmp_path, monkeypatch):
        from collectors import sector_holdings as sh

        first = _fake_xlsx_bytes("xlk-replacement-a")
        second = _fake_xlsx_bytes("xlk-replacement-b")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, first, now=now,
                                rows=_ssga_rows(as_of="11/06/2026"))

        adapter._merge_write("XLK", adapter._fetch_fund("XLK"))
        monkeypatch.setattr(adapter, "http_get",
                            lambda url, **_kw: _FakeResponse(second))
        adapter._merge_write("XLK", adapter._fetch_fund("XLK"))

        store = tmp_path / "sector_holdings"
        stored = pd.read_parquet(store / "XLK.parquet")
        assert stored["capture_content_sha256"].nunique() == 1
        assert stored["capture_content_sha256"].iloc[0] == hashlib.sha256(
            second).hexdigest()
        assert len(stored) == 3  # replaced, not duplicated
        history = pd.read_parquet(store / "history.parquet")
        assert list(history.columns) == list(sh.HISTORY_COLUMNS)
        assert len(history) == 3  # one set of rows, no predecessor/revision rows

    def test_a_regressive_incoming_capture_cannot_masquerade_as_the_latest(
            self, tmp_path, monkeypatch):
        store, before = self._stored(tmp_path, day="2026-11-06")
        content = _fake_xlsx_bytes("xlk-regressive")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now,
                                rows=_ssga_rows(as_of="11/05/2026"))

        snap = adapter._fetch_fund("XLK")
        with pytest.raises(ValueError, match="older than the stored snapshot"):
            adapter._merge_write("XLK", snap)

        assert (store / "XLK.parquet").read_bytes() == before
        assert not (store / "history.parquet").exists()

    def test_the_history_archive_keeps_its_six_columns(self, tmp_path, monkeypatch):
        from collectors import sector_holdings as sh

        content = _fake_xlsx_bytes("xlk-history")
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now,
                                rows=_ssga_rows(as_of="11/06/2026"))

        adapter._merge_write("XLK", adapter._fetch_fund("XLK"))
        history = pd.read_parquet(tmp_path / "sector_holdings" / "history.parquet")

        assert list(history.columns) == ["as_of", "etf", "ticker", "name",
                                         "weight_pct", "rank"]
        assert list(history.columns) == list(sh.HISTORY_COLUMNS)
        assert (history["etf"] == "XLK").all()
        assert len(history) == 3

    def test_the_real_spreadsheet_engine_produces_the_same_capture(
            self, tmp_path, monkeypatch):
        """Where a spreadsheet engine is installed, the REAL pandas parse path
        is checked as well: a genuine XLSX body parsed by pandas itself. The
        main cases above need no engine, because the CI gates that own this
        file do not install one."""
        from collectors import sector_holdings as sh

        pytest.importorskip("openpyxl", reason="needs an excel engine")
        buffer = io.BytesIO()
        pd.DataFrame(_ssga_rows(as_of="11/06/2026")).to_excel(
            buffer, index=False, header=False, engine="openpyxl")
        content = buffer.getvalue()
        now = datetime(2026, 11, 6, 21, 12, 33, 456789, tzinfo=timezone.utc)
        adapter = self._adapter(tmp_path, monkeypatch, content, now=now)

        snap = adapter._fetch_fund("XLK")

        assert list(snap.index) == [pd.Timestamp("2026-11-06")] * len(snap)
        assert snap["capture_content_sha256"].iloc[0] == hashlib.sha256(
            content).hexdigest()
        assert int(snap["capture_content_bytes"].iloc[0]) == len(content)
        assert snap["capture_retrieved_at"].iloc[0] == now.isoformat()
        assert snap["capture_issuer_as_of"].iloc[0] == "2026-11-06"
        assert snap["capture_date_origin"].iloc[0] == sh.DATE_ORIGIN_ISSUER_REPORTED
