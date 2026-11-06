"""Tests for the append-only period_start enrichment (FIF A44 exact-start binding).

scripts/backfill_edgar_quarterly.py --enrich-period-start appends the
companyfacts duration start to data/edgar/statements_quarterly.parquet
WITHOUT changing any existing value: a stored row receives period_start only
when the recomputed (fiscal_year, fiscal_quarter) key exists AND the
recomputed period_end equals the stored one as an ISO day.

Test coverage (all synthetic — _get_json, _cik_map, _out_path and time.sleep
are monkeypatched; NO network):
  (1) exact key + end match writes the ISO start as a Python str;
  (2) period_end mismatch → None;
  (3) a quarter with only instant (balance) facts → None;
  (4) original columns survive assert_frame_equal(check_exact=True) and the
      new column is appended last;
  (5) rerun is idempotent (second output equals the first);
  (6) pace_s=0.4 raises ValueError before any fetch;
  (7) a fetch failure leaves that ticker's rows untouched while another
      ticker is enriched;
  (8) the sleep recorder shows ≥ 0.5 s after every fetch;
  (9) --enrich-period-start --force exits non-zero;
  (10) a store with no period_start and a ticker-subset rerun keeps the other
       tickers' values.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.backfill_edgar_quarterly as bq   # noqa: E402

UA = "test-ua period-start enrichment"


# ---------------------------------------------------------------------------
# Fixture helpers (synthetic companyfacts only)
# ---------------------------------------------------------------------------

def _flow_entry(fy: int, fq: int, start: str, end: str, val: float = 100.0,
                filed: str = "2024-05-01") -> dict:
    """Minimal XBRL duration entry (90-ish days → passes the quarterly filter)."""
    return {"fp": f"Q{fq}", "form": "10-Q", "fy": fy, "val": val,
            "start": start, "end": end, "filed": filed}


def _instant_entry(fy: int, fq: int, end: str, val: float = 50.0,
                   filed: str = "2024-05-01") -> dict:
    """Minimal XBRL instant entry (balance-sheet concept; no start by nature)."""
    return {"fp": f"Q{fq}", "form": "10-Q", "fy": fy, "val": val,
            "end": end, "filed": filed}


def _facts(flow: list[dict], instant: list[dict]) -> dict:
    return {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": flow}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": instant}},
    }}}


def _store_row(ticker: str, fy: int, fq: int, period_end: str,
               filed: str = "2024-05-01", revenue: float = 100.0) -> dict:
    return {"ticker": ticker, "fiscal_year": fy, "fiscal_quarter": fq,
            "period_end": period_end, "filed": filed, "revenue": revenue,
            "as_of": "2026-08-23T00:00:00+00:00"}


def _write_store(tmp_path: Path, rows: list[dict],
                 period_start: list | None = None) -> pd.DataFrame:
    """Write the synthetic store and read it back (same parquet round trip the
    enrichment itself goes through, so dtypes compare exactly)."""
    df = pd.DataFrame(rows)
    if period_start is not None:
        df["period_start"] = period_start
    p = tmp_path / "statements_quarterly.parquet"
    df.to_parquet(p, index=False)
    return pd.read_parquet(p)


def _starts(df: pd.DataFrame) -> list:
    """period_start values with parquet round-trip nulls normalised to None."""
    return [None if pd.isna(v) else v for v in df["period_start"].tolist()]


def _patch(monkeypatch, tmp_path: Path, by_cik: dict) -> tuple[list, list]:
    """Patch _get_json / _cik_map / _out_path / time.sleep; return recorders."""
    calls: list[str] = []
    slept: list[float] = []

    def fake_get_json(url: str, ua: str, retries: int = 3):
        calls.append(url)
        for cik, payload in by_cik.items():
            if url == bq.FACTS_URL.format(cik):
                return payload
        return None

    def fake_sleep(s: float):
        slept.append(s)

    store_p = tmp_path / "statements_quarterly.parquet"
    monkeypatch.setattr(bq, "_get_json", fake_get_json)
    monkeypatch.setattr(bq, "_cik_map", lambda: {"AAA": 111, "BBB": 222})
    monkeypatch.setattr(bq, "_out_path", lambda: store_p)
    monkeypatch.setattr(bq.time, "sleep", fake_sleep)
    return calls, slept


# ---------------------------------------------------------------------------
# (1) exact key + end match → ISO start as str (+ key-missing row → None)
# ---------------------------------------------------------------------------

def test_exact_match_writes_iso_start_str(tmp_path, monkeypatch):
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31"),
              _flow_entry(2023, 4, "2023-10-01", "2023-12-31")],
        instant=[_instant_entry(2024, 1, "2024-03-31")],
    )
    calls, _ = _patch(monkeypatch, tmp_path, {111: payload})
    baseline = _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("AAA", 2023, 4, "2023-12-31"),
        # key (2022, 3) does not exist in the recomputed view → None
        _store_row("AAA", 2022, 3, "2022-09-30"),
    ])
    out_counts = bq.enrich_period_start(ua=UA)
    assert out_counts["rows_with_start"] == 2
    assert out_counts["rows_key_missing"] == 1
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    starts = _starts(out)
    assert starts[0] == "2024-01-01" and isinstance(starts[0], str)
    assert starts[1] == "2023-10-01" and isinstance(starts[1], str)
    assert starts[2] is None


# ---------------------------------------------------------------------------
# (2) period_end mismatch → None
# ---------------------------------------------------------------------------

def test_end_mismatch_writes_none(tmp_path, monkeypatch):
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")],
        instant=[],
    )
    _patch(monkeypatch, tmp_path, {111: payload})
    _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-30"),   # one day off
    ])
    out_counts = bq.enrich_period_start(ua=UA)
    assert out_counts["rows_end_mismatch"] == 1
    assert out_counts["rows_with_start"] == 0
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    assert _starts(out) == [None]


# ---------------------------------------------------------------------------
# (3) quarter with only instant (balance) facts → None
# ---------------------------------------------------------------------------

def test_instant_only_quarter_is_none(tmp_path, monkeypatch):
    # Flow facts exist only for Q1; Q2 is represented by an instant fact alone.
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")],
        instant=[_instant_entry(2024, 1, "2024-03-31"),
                 _instant_entry(2024, 2, "2024-06-30")],
    )
    _patch(monkeypatch, tmp_path, {111: payload})
    _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("AAA", 2024, 2, "2024-06-30"),
    ])
    out_counts = bq.enrich_period_start(ua=UA)
    assert out_counts["rows_with_start"] == 1
    assert out_counts["rows_no_start"] == 1
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    starts = _starts(out)
    assert starts[0] == "2024-01-01"
    assert starts[1] is None


# ---------------------------------------------------------------------------
# (4) original columns exact-equal; period_start appended last
# ---------------------------------------------------------------------------

def test_original_columns_preserved_and_new_column_last(tmp_path, monkeypatch):
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")],
        instant=[_instant_entry(2024, 1, "2024-03-31")],
    )
    _patch(monkeypatch, tmp_path, {111: payload})
    baseline = _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("AAA", 2023, 4, "2023-12-31"),
    ])
    bq.enrich_period_start(ua=UA)
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    orig_cols = list(baseline.columns)
    assert list(out.columns) == orig_cols + ["period_start"]
    pd.testing.assert_frame_equal(out[orig_cols], baseline[orig_cols],
                                  check_exact=True)
    # row order untouched
    assert out["ticker"].tolist() == baseline["ticker"].tolist()
    assert out["fiscal_year"].tolist() == baseline["fiscal_year"].tolist()


# ---------------------------------------------------------------------------
# (5) rerun is idempotent
# ---------------------------------------------------------------------------

def test_rerun_idempotent(tmp_path, monkeypatch):
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31"),
              _flow_entry(2023, 4, "2023-10-01", "2023-12-31")],
        instant=[_instant_entry(2024, 1, "2024-03-31")],
    )
    _patch(monkeypatch, tmp_path, {111: payload})
    _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("AAA", 2023, 4, "2023-12-31"),
    ])
    first_counts = bq.enrich_period_start(ua=UA)
    first = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    second_counts = bq.enrich_period_start(ua=UA)
    second = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    assert first_counts["rows_with_start"] == second_counts["rows_with_start"] == 2
    pd.testing.assert_frame_equal(first, second, check_exact=True)


# ---------------------------------------------------------------------------
# (6) pace_s=0.4 raises ValueError before any fetch
# ---------------------------------------------------------------------------

def test_pace_below_floor_raises_before_fetch(tmp_path, monkeypatch):
    calls, _ = _patch(monkeypatch, tmp_path, {111: _facts([], [])})
    _write_store(tmp_path, [_store_row("AAA", 2024, 1, "2024-03-31")])
    with pytest.raises(ValueError):
        bq.enrich_period_start(pace_s=0.4, ua=UA)
    assert calls == []


# ---------------------------------------------------------------------------
# (7) fetch failure leaves that ticker's rows untouched; another enriched
# ---------------------------------------------------------------------------

def test_fetch_failure_leaves_rows_untouched(tmp_path, monkeypatch):
    payload_a = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")],
        instant=[],
    )
    # BBB (CIK 222) has no payload → _get_json returns None → fetch failure.
    _patch(monkeypatch, tmp_path, {111: payload_a})
    _write_store(
        tmp_path,
        [_store_row("AAA", 2024, 1, "2024-03-31"),
         _store_row("BBB", 2024, 1, "2024-03-31")],
        period_start=["2024-01-01", "2019-01-01"],   # pre-existing values
    )
    out_counts = bq.enrich_period_start(ua=UA)
    assert out_counts["fetched"] == 1
    assert out_counts["fetch_failed"] == 1
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    starts = _starts(out)
    assert starts[0] == "2024-01-01"     # AAA re-enriched (same value)
    assert starts[1] == "2019-01-01"     # BBB untouched by the failure


# ---------------------------------------------------------------------------
# (8) sleep recorder shows ≥ 0.5 s after every fetch
# ---------------------------------------------------------------------------

def test_sleep_pace_respected_after_every_fetch(tmp_path, monkeypatch):
    payload = _facts(
        flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")],
        instant=[],
    )
    _, slept = _patch(monkeypatch, tmp_path, {111: payload, 222: payload})
    _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("BBB", 2024, 1, "2024-03-31"),
    ])
    out_counts = bq.enrich_period_start(pace_s=0.5, ua=UA)
    assert out_counts["fetched"] == 2
    assert len(slept) == 2                # one paced sleep per fetch
    assert all(s >= 0.5 for s in slept)


# ---------------------------------------------------------------------------
# (9) --enrich-period-start --force exits non-zero
# ---------------------------------------------------------------------------

def test_cli_enrich_with_force_exits_nonzero(tmp_path, monkeypatch):
    calls, _ = _patch(monkeypatch, tmp_path, {})
    _write_store(tmp_path, [_store_row("AAA", 2024, 1, "2024-03-31")])
    monkeypatch.setattr(sys, "argv", ["backfill_edgar_quarterly",
                                      "--enrich-period-start", "--force"])
    rc = bq.main()
    assert rc != 0
    assert calls == []                    # refused before any fetch


# ---------------------------------------------------------------------------
# (10) subset rerun keeps the other tickers' values
# ---------------------------------------------------------------------------

def test_subset_rerun_keeps_other_tickers_values(tmp_path, monkeypatch):
    payload_a = _facts(flow=[_flow_entry(2024, 1, "2024-01-01", "2024-03-31")], instant=[])
    payload_b = _facts(flow=[_flow_entry(2024, 1, "2024-01-02", "2024-03-31")], instant=[])
    _patch(monkeypatch, tmp_path, {111: payload_a, 222: payload_b})
    _write_store(tmp_path, [
        _store_row("AAA", 2024, 1, "2024-03-31"),
        _store_row("BBB", 2024, 1, "2024-03-31"),
    ])   # no period_start column yet
    bq.enrich_period_start(tickers=["AAA"], ua=UA)
    mid = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    assert _starts(mid) == ["2024-01-01", None]
    # Second pass enriches only BBB; AAA's first-pass value must survive.
    bq.enrich_period_start(tickers=["BBB"], ua=UA)
    out = pd.read_parquet(tmp_path / "statements_quarterly.parquet")
    assert _starts(out) == ["2024-01-01", "2024-01-02"]
