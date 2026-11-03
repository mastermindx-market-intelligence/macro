"""C19 WP24 DQ2 — superseded generations are witnessed, never silently lost.

Three collectors overwrite a same-key row when a source is re-read:
FINRA daily short volume (date, ticker), FINRA short interest history
(settlement_date, ticker) and the IBKR borrow same-day capture file. Each now
preserves the displaced generation in a sidecar before the overwrite, and only
when the values actually changed. The FINRA short-volume parsers also stop
letting a case-variant preferred symbol (BCpC) overwrite the common (BCPC).

Every test is hermetic: config.data_dir points at tmp_path and the network
entry points are monkeypatched, so nothing touches the real data/ tree.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from collectors import finra
from collectors import finra_short_volume as fsv
from collectors import ibkr_borrow
from lib import config
from scripts import backfill_finra_short_volume as bf

SV_HEADER = "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"


def _sv_text(short_aaa: int) -> str:
    return "\n".join([
        SV_HEADER,
        f"20261009|AAA|{short_aaa}|0|400|B,Q,N",
        "20261009|BBB|50|0|200|B,Q,N",
        "Total Records: 2",
    ])


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# FINRA daily short volume — data/finra_short_volume/superseded.parquet
# ---------------------------------------------------------------------------

def _run_sv_fetch(monkeypatch, text: str) -> None:
    monkeypatch.setattr(fsv, "_business_days", lambda n: [date(2026, 10, 9)])
    monkeypatch.setattr(fsv, "_universe_tickers", lambda: set())
    monkeypatch.setattr(fsv.FinraShortVolumeAdapter, "http_get",
                        lambda self, url, **kw: SimpleNamespace(text=text))
    fsv.FinraShortVolumeAdapter().fetch()


def test_short_volume_restatement_preserves_original_row(data_root, monkeypatch):
    _run_sv_fetch(monkeypatch, _sv_text(100))
    _run_sv_fetch(monkeypatch, _sv_text(150))

    side = data_root / "finra_short_volume" / "superseded.parquet"
    assert side.exists(), "a changed re-read must write the superseded sidecar"
    gone = pd.read_parquet(side)
    assert len(gone) == 1
    row = gone.iloc[0]
    assert row["ticker"] == "AAA"
    assert row["short_vol"] == 100.0
    assert "superseded_at_utc" in gone.columns

    panel = pd.read_parquet(data_root / "finra_short_volume" / "panel.parquet")
    assert panel.set_index("ticker").loc["AAA", "short_vol"] == 150.0
    assert len(panel) == 2

    # An identical third read appends nothing.
    _run_sv_fetch(monkeypatch, _sv_text(150))
    assert len(pd.read_parquet(side)) == 1


def test_short_volume_witness_appends_and_identical_is_noop(data_root):
    gen1 = fsv._parse(_sv_text(100))
    gen2 = fsv._parse(_sv_text(150))
    gen3 = fsv._parse(_sv_text(175))
    # fetch() only witnesses when a prior panel exists, so its directory does too.
    fsv._superseded_path().parent.mkdir(parents=True)

    assert fsv._witness_superseded(gen1, gen1.copy()) == 0
    assert not fsv._superseded_path().exists(), "identical re-read must not create the sidecar"

    assert fsv._witness_superseded(gen1, gen2) == 1
    assert fsv._witness_superseded(gen2, gen3) == 1
    gone = pd.read_parquet(fsv._superseded_path())
    assert list(gone["short_vol"]) == [100.0, 150.0], "restatements append, never overwrite"


# ---------------------------------------------------------------------------
# FINRA short interest history — data/finra/short_interest_superseded.parquet
# ---------------------------------------------------------------------------

def _si_snapshot(short_shares: float):
    def _snap(settlement: str) -> pd.DataFrame:
        df = pd.DataFrame({
            "ticker": ["AAA", "BBB"],
            "short_shares": [short_shares, 5000.0],
            "prev_short_shares": [900.0, 4800.0],
            "avg_daily_vol": [200.0, 1000.0],
            "days_to_cover": [short_shares / 200.0, 5.0],
            "si_change_pct": [11.1, 4.2],
        })
        df["settlement_date"] = settlement
        return df.set_index("ticker")
    return _snap


def _run_si_fetch(monkeypatch, short_shares: float) -> None:
    monkeypatch.setattr(finra, "_latest_settlement", lambda: "2026-09-30")
    monkeypatch.setattr(finra, "_snapshot", _si_snapshot(short_shares))
    monkeypatch.setattr(finra, "_universe_tickers", lambda: set())
    finra.fetch_short_interest(force=True)


def test_short_interest_restatement_preserves_original_capture(data_root, monkeypatch):
    _run_si_fetch(monkeypatch, 1000.0)
    hist_p = data_root / "finra" / "short_interest_history.parquet"
    first_capture = pd.read_parquet(hist_p).set_index("ticker").loc["AAA", "capture_date"]

    _run_si_fetch(monkeypatch, 1200.0)

    side = data_root / "finra" / "short_interest_superseded.parquet"
    assert side.exists(), "a restated settlement must write the superseded sidecar"
    gone = pd.read_parquet(side)
    assert len(gone) == 1
    row = gone.iloc[0]
    assert row["ticker"] == "AAA"
    assert row["settlement_date"] == "2026-09-30"
    assert row["short_shares"] == 1000.0
    assert row["capture_date"] == first_capture, "the original capture_date travels with the row"
    assert "superseded_at_utc" in gone.columns

    hist = pd.read_parquet(hist_p).set_index("ticker")
    assert hist.loc["AAA", "short_shares"] == 1200.0
    assert len(hist) == 2

    # An identical re-capture appends nothing.
    _run_si_fetch(monkeypatch, 1200.0)
    assert len(pd.read_parquet(side)) == 1


# ---------------------------------------------------------------------------
# IBKR borrow — data/ibkr_borrow/daily/superseded/<date>__<snapshot_et>.parquet
# ---------------------------------------------------------------------------

def _ibkr_text(stamp: str, fee_aaa: str) -> str:
    return "\n".join([
        f"#BOF|2026.10.13|{stamp}",
        "#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|",
        f"AAA|USD|AAA CORP|1234|US0000000001|4.5|{fee_aaa}|100000|FIGI1|",
        "BBB|USD|BBB INC|5678|US0000000002|4.2|0.30|>10000000|FIGI2|",
        "#EOF|2",
    ])


def _run_ibkr_fetch(monkeypatch, text: str) -> None:
    monkeypatch.setattr(ibkr_borrow, "_fetch_text", lambda: text)
    monkeypatch.setattr(ibkr_borrow, "_universe_tickers", lambda: set())
    ibkr_borrow.IbkrBorrowAdapter().fetch()


def test_ibkr_same_day_recapture_preserves_earlier_snapshot(data_root, monkeypatch):
    _run_ibkr_fetch(monkeypatch, _ibkr_text("09:15:02", "0.25"))
    rows_before = len(ibkr_borrow.load_panel())
    assert rows_before == 2

    _run_ibkr_fetch(monkeypatch, _ibkr_text("15:45:00", "0.75"))

    daily = data_root / "ibkr_borrow" / "daily"
    moved = daily / "superseded" / "2026-10-13__091502.parquet"
    assert moved.exists(), "a different #BOF snapshot must move the old file aside"
    old = pd.read_parquet(moved).set_index("ticker")
    assert old.loc["AAA", "fee_pct"] == 0.25
    assert (old["snapshot_et"] == "09:15:02").all()

    cur = pd.read_parquet(daily / "2026-10-13.parquet").set_index("ticker")
    assert cur.loc["AAA", "fee_pct"] == 0.75

    # The superseded/ subdirectory never enters the panel.
    assert len(ibkr_borrow.load_panel()) == rows_before

    # Re-reading the same #BOF snapshot moves nothing.
    _run_ibkr_fetch(monkeypatch, _ibkr_text("15:45:00", "0.75"))
    assert sorted(p.name for p in (daily / "superseded").iterdir()) == [moved.name]


# ---------------------------------------------------------------------------
# Case-fold collision — BCPC (common) must beat BCpC (preferred) in any order
# ---------------------------------------------------------------------------

_COMMON = "20261009|BCPC|1000|0|4000|B,Q,N"
_PREFERRED = "20261009|BCpC|7|0|9|N"


@pytest.mark.parametrize("parse", [fsv._parse, bf._parse], ids=["collector", "backfill"])
@pytest.mark.parametrize("order", ["preferred_last", "preferred_first"])
def test_case_variant_preferred_never_overwrites_common(parse, order):
    lines = [_COMMON, _PREFERRED] if order == "preferred_last" else [_PREFERRED, _COMMON]
    df = parse("\n".join([SV_HEADER, *lines, "Total Records: 2"]))
    bcpc = df[df["ticker"] == "BCPC"]
    assert len(bcpc) == 1
    assert bcpc.iloc[0]["short_vol"] == 1000.0
    assert bcpc.iloc[0]["total_vol"] == 4000.0
    assert "_upper" not in df.columns


@pytest.mark.parametrize("parse", [fsv._parse, bf._parse], ids=["collector", "backfill"])
def test_parse_without_collisions_is_unchanged(parse):
    df = parse(_sv_text(100))
    assert list(df["ticker"]) == ["AAA", "BBB"]
    assert list(df.columns) == ["date", "ticker", "short_vol", "short_exempt",
                                "total_vol", "short_ratio"]
    assert parse("nonsense\nno pipes here").empty
