"""Synthetic tests for Grey Deer panel input preparation (D14, D15).

No market data, no network, no file written by the module under test.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_panel_adjust as adj  # noqa: E402

PANEL = (
    "QQQ",
    "IWM",
    "DIA",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
)
SPLIT_TICKERS = ("XLB", "XLE", "XLK", "XLU", "XLY")
# 2026-08-18 is absent on these nine and present on the other five.
GAP_TICKERS = ("QQQ", "IWM", "XLE", "XLF", "XLI", "XLP", "XLRE", "XLU", "XLY")
WINDOW_START = "2021-07-06"
AS_OF = "2026-10-07"
SPLIT_DATE = "2025-12-05"
GAP_DATE = "2026-08-18"
_SOURCE_URLS = (
    "https://www.businesswire.com/news/home/20251120957218/en/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs",
    "https://www.ssga.com/library-content/products/fund-docs/etfs/us/information-schedules/select-sector-spdr-fund-share-splits-faq.pdf",
)


def _business_days() -> list[str]:
    return [stamp.strftime("%Y-%m-%d") for stamp in pd.bdate_range(WINDOW_START, AS_OF)]


def _make_frames(
    seed: int = 221012,
    *,
    split: bool = True,
    drop_gap: bool = True,
    extra_drop: dict[str, list[str]] | None = None,
) -> dict[str, pd.DataFrame]:
    """14 synthetic GBM identities. Five carry an unadjusted 2-for-1; nine miss the gap date."""
    rng = np.random.default_rng(seed)
    dates = _business_days()
    frames: dict[str, pd.DataFrame] = {}
    for _ticker in PANEL:
        n = len(dates)
        rets = rng.normal(0.0002, 0.01, size=n)
        close = 100.0 * np.exp(np.cumsum(rets))
        noise = rng.normal(0.0, 0.001, size=n)
        open_ = close * np.exp(noise)
        span = np.abs(rng.normal(0.0, 0.002, size=n))
        high = np.maximum(open_, close) * np.exp(span)
        low = np.minimum(open_, close) * np.exp(-span)
        volume = rng.uniform(1.0e6, 5.0e6, size=n)
        transactions = rng.integers(1000, 5000, size=n)
        frame = pd.DataFrame(
            {
                "date": dates,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "transactions": transactions,
            }
        )
        if split and _ticker in SPLIT_TICKERS:
            mask = frame["date"] >= SPLIT_DATE
            for column in ("open", "high", "low", "close"):
                frame.loc[mask, column] = frame.loc[mask, column] / 2.0
            frame.loc[mask, "volume"] = frame.loc[mask, "volume"] * 2.0
        if drop_gap and _ticker in GAP_TICKERS:
            frame = frame.loc[frame["date"] != GAP_DATE].reset_index(drop=True)
        if extra_drop and _ticker in extra_drop:
            drop = set(extra_drop[_ticker])
            frame = frame.loc[~frame["date"].isin(drop)].reset_index(drop=True)
        frames[_ticker] = frame.reset_index(drop=True)
    return frames


def _snapshot(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {ticker: frame.copy(deep=True) for ticker, frame in frames.items()}


def _assert_unmodified(frames: dict[str, pd.DataFrame], snapshot: dict[str, pd.DataFrame]) -> None:
    assert set(frames) == set(snapshot)
    for ticker, frame in frames.items():
        assert frame.equals(snapshot[ticker])


def _union_in_window(frames: dict[str, pd.DataFrame]) -> set[str]:
    union: set[str] = set()
    for frame in frames.values():
        dates = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
        keep = (dates >= WINDOW_START) & (dates <= AS_OF)
        union.update(dates[keep].tolist())
    return union


def _assert_detail_json(detail: dict) -> None:
    encoded = json.dumps(detail, allow_nan=False)
    assert json.loads(encoded) == detail


# ── pinned table ─────────────────────────────────────────────────────────────


def test_pinned_table_matches_seat_amendment():
    assert adj.PINNED_SPLITS == {
        ("XLB", SPLIT_DATE): 2.0,
        ("XLE", SPLIT_DATE): 2.0,
        ("XLK", SPLIT_DATE): 2.0,
        ("XLU", SPLIT_DATE): 2.0,
        ("XLY", SPLIT_DATE): 2.0,
    }
    assert adj.SPLIT_SOURCES == _SOURCE_URLS
    assert adj.PINNED_CALENDAR_EXCLUSIONS == frozenset({GAP_DATE})
    assert adj.SPLIT_CONFIRM_TOL == 0.10
    assert adj.BREAK_LOG_THRESHOLD == math.log(1.25)


# ── prepare_panel success ────────────────────────────────────────────────────


def test_prepare_panel_ok_on_synthetic_unadjusted_splits():
    frames = _make_frames()
    snapshot = _snapshot(frames)
    direct = adj.apply_pinned_splits(frames)
    _assert_unmodified(frames, snapshot)
    assert direct.status == "OK"
    assert direct.frames is not None

    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    _assert_unmodified(frames, snapshot)
    assert result.status == "OK"
    assert result.reason is None
    assert result.frames is not None
    assert result.calendar is not None
    assert result.confirmations is not None
    assert set(result.frames) == set(PANEL)

    union = _union_in_window(snapshot)
    assert len(result.calendar) == len(union) - 1
    assert set(union) - set(result.calendar) == {GAP_DATE}
    for frame in result.frames.values():
        assert frame["date"].tolist() == result.calendar
        assert GAP_DATE not in set(frame["date"])

    assert len(result.confirmations) == 5
    assert [row["ticker"] for row in result.confirmations] == sorted(SPLIT_TICKERS)
    for row in result.confirmations:
        assert row["date"] == SPLIT_DATE
        assert row["ratio"] == 2.0
        raw = snapshot[row["ticker"]]
        position = raw["date"].tolist().index(SPLIT_DATE)
        observed = float(raw["close"].iloc[position - 1]) / float(raw["close"].iloc[position])
        assert row["observed"] == float(f"{observed:.6f}")
        low = (1.0 - adj.SPLIT_CONFIRM_TOL) * row["ratio"]
        high = (1.0 + adj.SPLIT_CONFIRM_TOL) * row["ratio"]
        assert low <= row["observed"] <= high

    for ticker in SPLIT_TICKERS:
        raw = snapshot[ticker].set_index("date")
        adjusted = result.frames[ticker].set_index("date")
        pre = [date for date in adjusted.index if date < SPLIT_DATE]
        post = [date for date in adjusted.index if date >= SPLIT_DATE]
        for column in ("open", "high", "low", "close"):
            np.testing.assert_array_equal(
                adjusted.loc[pre, column].to_numpy(dtype=float),
                raw.loc[pre, column].to_numpy(dtype=float) / 2.0,
            )
            np.testing.assert_array_equal(
                adjusted.loc[post, column].to_numpy(dtype=float),
                raw.loc[post, column].to_numpy(dtype=float),
            )
        np.testing.assert_array_equal(
            adjusted.loc[pre, "volume"].to_numpy(dtype=float),
            raw.loc[pre, "volume"].to_numpy(dtype=float) * 2.0,
        )
        np.testing.assert_array_equal(
            adjusted.loc[post, "volume"].to_numpy(dtype=float),
            raw.loc[post, "volume"].to_numpy(dtype=float),
        )
        np.testing.assert_array_equal(
            adjusted["transactions"].to_numpy(),
            raw.loc[adjusted.index, "transactions"].to_numpy(),
        )
        assert adjusted["volume"].dtype == np.float64

    for frame in result.frames.values():
        assert adj.detect_split_breaks(frame) == []

    assert result.detail["skipped_pins"] == []
    _assert_detail_json(result.detail)


def test_prepare_panel_is_deterministic():
    frames = _make_frames()
    first = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    second = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert first.status == "OK" and second.status == "OK"
    assert first.detail == second.detail
    assert first.confirmations == second.confirmations
    assert first.calendar == second.calendar
    assert first.frames is not None and second.frames is not None
    for ticker in first.frames:
        pd.testing.assert_frame_equal(first.frames[ticker], second.frames[ticker])
    _assert_detail_json(first.detail)


# ── refusals ─────────────────────────────────────────────────────────────────


def test_ratio_mismatch_names_ticker():
    frames = _make_frames()
    snapshot = _snapshot(frames)
    splits = dict(adj.PINNED_SPLITS)
    splits[("XLB", SPLIT_DATE)] = 3.0
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF, splits=splits)
    _assert_unmodified(frames, snapshot)
    assert result.status == "BLOCKED"
    assert result.reason == "SPLIT_TABLE_MISMATCH"
    assert result.frames is None
    assert result.calendar is None
    assert result.confirmations is None
    assert [row["ticker"] for row in result.detail["mismatches"]] == ["XLB"]
    mismatch = result.detail["mismatches"][0]
    assert mismatch["date"] == SPLIT_DATE
    assert mismatch["ratio"] == 3.0
    assert mismatch["why"] == "ratio_out_of_tolerance"
    raw = snapshot["XLB"]
    position = raw["date"].tolist().index(SPLIT_DATE)
    observed = float(raw["close"].iloc[position - 1]) / float(raw["close"].iloc[position])
    assert mismatch["observed"] == float(f"{observed:.6f}")
    assert result.detail["why"] == "ratio_out_of_tolerance"
    _assert_detail_json(result.detail)


def test_effective_date_missing():
    frames = _make_frames()
    frames["XLK"] = frames["XLK"].loc[frames["XLK"]["date"] != SPLIT_DATE].reset_index(drop=True)
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert result.status == "BLOCKED"
    assert result.reason == "SPLIT_TABLE_MISMATCH"
    assert result.detail["why"] == "effective_date_missing"
    assert result.detail["mismatches"] == [
        {
            "ticker": "XLK",
            "date": SPLIT_DATE,
            "ratio": 2.0,
            "why": "effective_date_missing",
        }
    ]


def test_no_prior_session():
    only = pd.DataFrame(
        {
            "date": [SPLIT_DATE],
            "open": [50.0],
            "high": [51.0],
            "low": [49.0],
            "close": [50.0],
            "volume": [1000.0],
            "transactions": [10],
        }
    )
    result = adj.apply_pinned_splits({"XLB": only}, splits={("XLB", SPLIT_DATE): 2.0})
    assert result.status == "BLOCKED"
    assert result.reason == "SPLIT_TABLE_MISMATCH"
    assert result.detail["why"] == "no_prior_session"
    assert result.detail["mismatches"][0]["why"] == "no_prior_session"
    assert "observed" not in result.detail["mismatches"][0]


def test_unpinned_split_is_discontinuity():
    frames = _make_frames()
    jump = "2024-06-03"
    dia = frames["DIA"]
    mask = dia["date"] >= jump
    for column in ("open", "high", "low", "close"):
        dia.loc[mask, column] = dia.loc[mask, column] / 3.0
    dia.loc[mask, "volume"] = dia.loc[mask, "volume"] * 3.0
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert result.status == "BLOCKED"
    assert result.reason == "SPLIT_DISCONTINUITY"
    assert result.frames is None
    assert {"ticker": "DIA", "date": jump} in result.detail["breaks"]
    assert result.detail["breaks"][0]["ticker"] == "DIA"
    _assert_detail_json(result.detail)


def test_extra_missing_date_is_calendar_misaligned():
    extra = "2024-03-15"
    frames = _make_frames(extra_drop={"DIA": [extra]})
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert result.status == "BLOCKED"
    assert result.reason == "CALENDAR_MISALIGNED"
    assert extra in result.detail["unexpected"]
    assert result.detail["pinned_absent"] == []
    assert extra in result.detail["missing_by_ticker"]["DIA"]
    assert set(result.detail) == {"unexpected", "pinned_absent", "missing_by_ticker"}
    _assert_detail_json(result.detail)


def test_restored_exclusion_is_pinned_absent():
    frames = _make_frames(drop_gap=False)
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert result.status == "BLOCKED"
    assert result.reason == "CALENDAR_MISALIGNED"
    assert result.detail["pinned_absent"] == [GAP_DATE]
    assert result.detail["unexpected"] == []
    assert result.detail["missing_by_ticker"] == {}


def test_mismatch_blocks_before_intersect(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("intersect_calendar must not run")

    monkeypatch.setattr(adj, "intersect_calendar", _boom)
    frames = _make_frames()
    frames["XLB"] = frames["XLB"].loc[frames["XLB"]["date"] != SPLIT_DATE].reset_index(drop=True)
    result = adj.prepare_panel(frames, WINDOW_START, AS_OF)
    assert result.status == "BLOCKED"
    assert result.reason == "SPLIT_TABLE_MISMATCH"
    assert result.detail["why"] == "effective_date_missing"
    assert result.detail["mismatches"][0]["ticker"] == "XLB"


# ── adjustment arithmetic ────────────────────────────────────────────────────


def test_splits_apply_cumulatively_and_do_not_mutate_inputs():
    frame = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-06-03", "2025-12-04", "2025-12-05"],
            "open": [200.0, 100.0, 100.0, 50.0],
            "high": [210.0, 110.0, 110.0, 55.0],
            "low": [190.0, 90.0, 90.0, 45.0],
            "close": [200.0, 100.0, 100.0, 50.0],
            "volume": [10.0, 20.0, 30.0, 40.0],
            "transactions": [1, 2, 3, 4],
        }
    )
    snapshot = frame.copy(deep=True)
    splits = {
        ("DIA", "2025-12-05"): 2.0,  # ticker not in frames: skipped, not an error
        ("XLB", "2025-12-05"): 2.0,
        ("XLB", "2024-06-03"): 2.0,
    }
    result = adj.apply_pinned_splits({"XLB": frame}, splits=splits)
    assert frame.equals(snapshot)
    assert result.status == "OK"
    assert result.frames is not None
    assert result.detail["skipped_pins"] == [{"ticker": "DIA", "date": SPLIT_DATE, "ratio": 2.0}]
    adjusted = result.frames["XLB"]
    np.testing.assert_array_equal(adjusted["close"].to_numpy(), np.array([50.0, 50.0, 50.0, 50.0]))
    np.testing.assert_array_equal(adjusted["open"].to_numpy(), np.array([50.0, 50.0, 50.0, 50.0]))
    np.testing.assert_array_equal(adjusted["high"].to_numpy(), np.array([52.5, 55.0, 55.0, 55.0]))
    np.testing.assert_array_equal(adjusted["low"].to_numpy(), np.array([47.5, 45.0, 45.0, 45.0]))
    np.testing.assert_array_equal(adjusted["volume"].to_numpy(), np.array([40.0, 40.0, 60.0, 40.0]))
    np.testing.assert_array_equal(adjusted["transactions"].to_numpy(), np.array([1, 2, 3, 4]))
    assert [row["date"] for row in result.confirmations or []] == ["2024-06-03", "2025-12-05"]
    assert adj.detect_split_breaks(adjusted) == []


def test_confirmation_band_is_inclusive():
    def _row(close_prev: float, close_eff: float) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": ["2025-12-04", SPLIT_DATE],
                "open": [close_prev, close_eff],
                "high": [close_prev, close_eff],
                "low": [close_prev, close_eff],
                "close": [close_prev, close_eff],
                "volume": [1.0, 2.0],
                "transactions": [1, 1],
            }
        )

    on_edge = adj.apply_pinned_splits({"XLB": _row(2.2, 1.0)}, splits={("XLB", SPLIT_DATE): 2.0}, tol=0.10)
    assert on_edge.status == "OK"
    assert on_edge.confirmations is not None
    assert on_edge.confirmations[0]["observed"] == 2.2

    outside = adj.apply_pinned_splits({"XLB": _row(2.2 + 1.0e-4, 1.0)}, splits={("XLB", SPLIT_DATE): 2.0}, tol=0.10)
    assert outside.status == "BLOCKED"
    assert outside.reason == "SPLIT_TABLE_MISMATCH"
    assert outside.detail["why"] == "ratio_out_of_tolerance"


def test_detect_split_breaks_reports_dates_in_order():
    frame = pd.DataFrame(
        {
            "date": ["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06"],
            "open": [100.0, 110.0, 40.0, 42.0],
            "high": [100.0, 110.0, 40.0, 42.0],
            "low": [100.0, 110.0, 40.0, 42.0],
            "close": [100.0, 110.0, 40.0, 42.0],
            "volume": [1.0, 1.0, 1.0, 1.0],
            "transactions": [1, 1, 1, 1],
        }
    )
    # |log(110/100)| < log(1.25); |log(40/110)| > log(1.25); |log(42/40)| is not.
    assert adj.detect_split_breaks(frame) == ["2024-06-05"]
    assert adj.detect_split_breaks(frame, threshold=math.log(3.0)) == []


def test_bad_frame_type_raises():
    with pytest.raises(TypeError):
        adj.apply_pinned_splits({"XLB": []})  # type: ignore[dict-item]


# ── import hygiene ───────────────────────────────────────────────────────────


def test_import_hygiene():
    source_path = Path(__file__).resolve().parent.parent / "scripts" / "research" / "grey_deer_panel_adjust.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_roots = set(sys.stdlib_module_names) | {"numpy", "pandas"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError("relative import is not allowed")
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            root = module.split(".", 1)[0]
            if root == "scripts":
                assert module == "scripts.research.grey_deer_pullback_stage1"
                continue
            assert root in allowed_roots, module
    for banned in ("open(", "to_parquet", "to_csv", "write_text"):
        assert banned not in source
    # The module prepares inputs only.
    defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for forbidden in ("build_labels", "build_features", "run_fits", "evaluate_and_write"):
        assert forbidden not in defined
