"""Grey Deer W4: synthetic tests for the stage-1b pooled 14-ticker panel runner.

Seat decisions D1–D13. Synthetic frames only: no price download, no read of
``data/``, no write under ``research/`` or ``data/``. Every ``main`` call
receives an explicit ``--out-dir`` under ``tmp_path``.

Run:
    ~/lanes/venv/bin/python -m pytest -q tests/test_grey_deer_pullback_stage1b.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402
import scripts.research.grey_deer_pullback_stage1b as s1b  # noqa: E402


WINDOW_ENDS = ["2021-07-06", "2026-10-07"]
_BANNED_WORD = "vali" + "dated"


def _frame(dates, closes) -> pd.DataFrame:
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "date": list(dates),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": np.full(len(closes), 1_000_000.0),
            "transactions": np.full(len(closes), 1000.0),
        }
    )


def _write(directory: Path, ticker: str, dates, closes) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _frame(dates, closes).to_parquet(directory / f"{ticker}.parquet", index=False)


def _write_panel(directory: Path, dates_for, closes_for) -> None:
    for ticker in s1b.PANEL_TICKERS:
        _write(directory, ticker, dates_for(ticker), closes_for(ticker))


def _mild(_ticker: str):
    return [100.0, 110.0]


def _run(panel_dir: Path, out_dir: Path, extra: list[str] | None = None) -> int:
    argv = ["--out-dir", str(out_dir), "--panel-dir", str(panel_dir), *(extra or [])]
    return s1b.main(argv)


def _blocked(out_dir: Path) -> dict:
    payload = json.loads((out_dir / s1b.RESULTS_JSON_NAME).read_text(encoding="utf-8"))
    assert payload["schema"] == s1b.SCHEMA
    assert payload["status"] == "BLOCKED"
    assert payload["claims"] == []
    return payload["blocked"][0]


# ── 1. load refusals ─────────────────────────────────────────────────────────


def test_missing_ticker_is_panel_coverage(tmp_path, capsys):
    panel = tmp_path / "panel"
    for ticker in s1b.PANEL_TICKERS:
        if ticker == "QQQ":
            continue
        _write(panel, ticker, WINDOW_ENDS, _mild(ticker))
    out = tmp_path / "out"
    rc = _run(panel, out)
    assert rc == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / PANEL_COVERAGE"
    row = _blocked(out)
    assert row["type"] == "PANEL_COVERAGE"
    assert "QQQ" in row["tickers"]
    assert not (s1b.ROOT / s1b.DEFAULT_OUT_DIR).exists()


def test_late_first_row_refuses_without_trimming(tmp_path, capsys):
    panel = tmp_path / "panel"

    def dates_for(ticker: str):
        if ticker == "IWM":
            return ["2021-07-07", "2026-10-07"]
        return WINDOW_ENDS

    _write_panel(panel, dates_for, _mild)
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / PANEL_COVERAGE"
    row = _blocked(out)
    assert row["type"] == "PANEL_COVERAGE"
    assert row["ticker"] == "IWM"
    assert row["date"] == "2021-07-07"
    assert "not trimming" in row["detail"]


def test_calendar_misalignment_lists_symmetric_difference(tmp_path, capsys):
    panel = tmp_path / "panel"
    shared = ["2021-07-06", "2024-06-03", "2026-10-07"]
    odd = ["2021-07-06", "2024-06-04", "2026-10-07"]

    def dates_for(ticker: str):
        return odd if ticker == "XLY" else shared

    _write_panel(panel, dates_for, lambda _t: [100.0, 105.0, 110.0])
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / CALENDAR_MISALIGNED"
    row = _blocked(out)
    assert row["type"] == "CALENDAR_MISALIGNED"
    assert row["symmetric_difference"] == ["2024-06-03", "2024-06-04"]


def test_split_discontinuity_names_ticker_and_date(tmp_path, capsys):
    panel = tmp_path / "panel"

    def closes_for(ticker: str):
        if ticker == "DIA":
            return [100.0, 50.0]
        return [100.0, 110.0]

    _write_panel(panel, lambda _t: WINDOW_ENDS, closes_for)
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / SPLIT_DISCONTINUITY"
    row = _blocked(out)
    assert row["type"] == "SPLIT_DISCONTINUITY"
    assert row["ticker"] == "DIA"
    assert row["date"] == "2026-10-07"


def test_ratio_of_exactly_one_point_two_five_is_not_a_split(tmp_path):
    """D5 comparison is strict. 125/100 == 1.25 does not refuse as a split."""
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: WINDOW_ENDS, lambda _t: [100.0, 125.0])
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    row = _blocked(out)
    assert row["type"] == "PREREG_V11_PENDING"


def test_declared_corporate_action_refuses_unadjusted(tmp_path, capsys):
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: WINDOW_ENDS, _mild)
    out = tmp_path / "out"
    rc = _run(panel, out, ["--corporate-action", "XLF:2026-10-07"])
    assert rc == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / SPLIT_UNADJUSTED"
    row = _blocked(out)
    assert row["ticker"] == "XLF"
    assert row["date"] == "2026-10-07"


def test_pending_pin_refuses_before_features_or_labels(tmp_path, monkeypatch):
    called = {"n": 0}

    def _boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("feature or label construction ran")

    monkeypatch.setattr(stage1, "build_features", _boom)
    monkeypatch.setattr(stage1, "build_labels", _boom)
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: WINDOW_ENDS, _mild)
    out = tmp_path / "out"
    rc = _run(panel, out)
    assert rc == 2
    assert called["n"] == 0
    assert _blocked(out)["type"] == "PREREG_V11_PENDING"

    frames = {
        ticker: pd.DataFrame({"date": WINDOW_ENDS, "close": [100.0, 110.0]})
        for ticker in s1b.PANEL_TICKERS
    }
    with pytest.raises(stage1.Blocked) as caught:
        s1b.execute_panel(frames)
    assert caught.value.type == "PREREG_V11_PENDING"
    assert called["n"] == 0


# ── 2. pooled fits and the common-date purge ─────────────────────────────────


def test_purge_drops_every_ticker_inside_the_gap_and_fits_are_pooled():
    n_dates = 120
    s0 = 100
    h = 5
    tickers = ["QQQ", "IWM"]
    train_idx = s1b.training_date_indices(n_dates, s0, h)
    candidates = np.arange(n_dates)
    candidates = candidates[
        (candidates >= stage1.WARM_IDX) & (candidates < s0) & (candidates <= n_dates - 1 - h)
    ]
    np.testing.assert_array_equal(train_idx, stage1.purged_training_indices(s0, h, candidates))
    assert 95 in train_idx  # idx + h == s0, kept
    assert 96 not in train_idx  # idx + h == s0 + 1, the purge gap
    union = s1b.training_union(n_dates, tickers, s0, h)
    assert ("QQQ", 95) in union and ("IWM", 95) in union
    assert ("QQQ", 96) not in union and ("IWM", 96) not in union
    assert len(union) == len(train_idx) * len(tickers) == 66

    rng = np.random.default_rng(7)
    columns = {name: rng.normal(0.0, 1.0, n_dates) for name in stage1.FEATURE_COLUMNS}
    columns["rv20"] = np.abs(columns["rv20"]) + 0.05
    feat = pd.DataFrame(columns)
    features = {ticker: feat.copy() for ticker in tickers}
    y = np.zeros(n_dates)
    y[70:74] = 1.0
    y[96] = 1.0  # inside the purge gap; must not enter either ticker's training rows
    a = np.full(n_dates, 0.02)
    a[70:74] = 0.08
    a[96] = 0.40
    test_idx = np.arange(s0, s0 + 4)
    fitted = s1b.fit_configurations_on_block(
        features,
        {ticker: y.copy() for ticker in tickers},
        {ticker: a.copy() for ticker in tickers},
        train_idx,
        test_idx,
        tickers,
    )
    assert fitted["train"]["origins"] == 66
    assert fitted["train"]["events"] == 8
    assert fitted["train"]["thin"] is False
    # (8 + 0.5) / (66 + 1). Counting the gap row for one ticker would be 9/68;
    # counting it for both would be 10/69.
    p0 = (8 + 0.5) / (66 + 1)
    b0 = fitted["by_config"]["B0"]
    np.testing.assert_allclose(b0["p"]["QQQ"], p0)
    np.testing.assert_allclose(b0["p"]["IWM"], p0)

    b1 = fitted["by_config"]["B1-20"]
    m3 = fitted["by_config"]["M3-ALL"]
    assert b1["feature_names"] == ("log_rv20",)
    assert m3["feature_names"] == ("dd63", "r5", "r10", "log_rv20")
    assert "ticker" not in b1["feature_names"]
    assert "ticker" not in m3["feature_names"]
    assert set(m3["p"]) == {"QQQ", "IWM"}
    assert len(m3["p"]["QQQ"]) == len(test_idx)
    np.testing.assert_allclose(b1["p"]["QQQ"], b1["p"]["IWM"])
    np.testing.assert_allclose(m3["p"]["QQQ"], m3["p"]["IWM"])
    kept_a = np.concatenate([a[train_idx], a[train_idx]])
    q0 = stage1.fit_q0(kept_a)
    for tau in stage1.TAUS:
        np.testing.assert_allclose(fitted["by_config"]["Q0"]["q"]["QQQ"][str(tau)], q0[tau])
        np.testing.assert_allclose(fitted["by_config"]["Q0"]["q"]["IWM"][str(tau)], q0[tau])


def test_label_conversion_preserves_immature_nan():
    close = pd.Series(100.0 * np.exp(np.cumsum(np.random.default_rng(3).normal(0.0, 0.01, 40))))
    labels = stage1.build_labels(close)
    y = s1b._y_array(labels[5]["Y"])
    assert y.shape == (40,)
    assert np.isnan(y[-5:]).all()
    mature = y[:-5]
    assert np.isin(mature, [0.0, 1.0]).all()


# ── 3. comparison intersection on (ticker, date) ─────────────────────────────


def test_intersection_keeps_the_other_ticker_on_an_abstained_date():
    # Date-major, ticker-minor: (QQQ, d0), (IWM, d0), (QQQ, d1), (IWM, d1).
    masks = {
        "B0": np.array([True, True, True, True]),
        "M3-ALL": np.array([False, True, True, True]),
    }
    common = s1b.intersect_issued(masks)
    assert common.tolist() == [False, True, True, True]
    kept = [(ticker, date) for date in (0, 1) for ticker in ("QQQ", "IWM") if common[date * 2 + ("QQQ", "IWM").index(ticker)]]
    assert ("QQQ", 0) not in kept
    assert ("IWM", 0) in kept
    assert ("QQQ", 1) in kept and ("IWM", 1) in kept


# ── 4. date-index bootstrap ──────────────────────────────────────────────────


def _expected_date_matrix(n_dates: int, h: int, pop: int, fam: int, var: int, n_draws: int) -> np.ndarray:
    length = stage1.block_length(h, var)
    n_blocks = math.ceil(n_dates / length)
    rng = np.random.default_rng(np.random.SeedSequence([s1b.SEED_ROOT, h, pop, fam, var]))
    offsets = np.arange(length)
    rows = np.empty((n_draws, n_dates), dtype=np.int64)
    for draw in range(n_draws):
        starts = rng.integers(0, n_dates, size=n_blocks)
        rows[draw] = ((starts[:, None] + offsets[None, :]) % n_dates).reshape(-1)[:n_dates]
    return rows


def test_bootstrap_seed_and_cross_section_of_fourteen():
    h, pop, fam, var = 5, stage1.SEED_CODES["pop"]["P-all"], stage1.SEED_CODES["fam"]["binary"], 0
    n_dates = 8
    n_draws = 4
    got = s1b.bootstrap_date_matrix(n_dates, h, pop, fam, var, n_draws=n_draws)
    np.testing.assert_array_equal(got, _expected_date_matrix(n_dates, h, pop, fam, var, n_draws))
    sens = s1b.bootstrap_date_matrix(n_dates, 10, pop, fam, 1, n_draws=2)
    np.testing.assert_array_equal(sens, _expected_date_matrix(n_dates, 10, pop, fam, 1, 2))
    assert stage1.block_length(5, 0) == max(21, 10)
    assert stage1.block_length(10, 1) == 10

    width = len(s1b.PANEL_TICKERS)
    assert width == 14
    rows_for_date = [np.arange(j * width, (j + 1) * width, dtype=np.int64) for j in range(n_dates)]
    expanded = s1b.expand_date_draws(got, rows_for_date)
    assert expanded.shape == (n_draws, n_dates * width)
    for draw in range(n_draws):
        for slot, date_pos in enumerate(got[draw]):
            block = expanded[draw, slot * width : (slot + 1) * width]
            np.testing.assert_array_equal(block, np.arange(int(date_pos) * width, (int(date_pos) + 1) * width))

    rng = np.random.default_rng(11)
    n = n_dates * width
    y = rng.random(n) < 0.25
    probs = {cfg: rng.random(n) for cfg in stage1.BINARY_CLAIM_CONFIGS}
    stats = s1b.panel_family_draws(rows_for_date, y, probs, h, pop, fam, var, n_draws, "binary")
    manual = stage1.binary_draw_statistics(expanded, y, probs, stage1.alpha_grid(h))
    np.testing.assert_array_equal(stats["delta_v"], manual["delta_v"])
    np.testing.assert_array_equal(stats["wace"], manual["wace"])
    np.testing.assert_array_equal(stats["v"]["M3-ALL"]["b"], manual["v"]["M3-ALL"]["b"])


def test_undefined_statistics_take_the_failing_extreme(monkeypatch):
    def _refuse_nan_quantile(*_a, **_k):
        raise AssertionError("nan-skipping quantile was called")

    monkeypatch.setattr(np, "nanquantile", _refuse_nan_quantile)
    monkeypatch.setattr(stage1.np, "nanquantile", _refuse_nan_quantile)

    width = 14
    n_dates = 4  # 56 rows: no WACE bin can reach the coverage floor of 100
    n = width * n_dates
    rows_for_date = [np.arange(j * width, (j + 1) * width) for j in range(n_dates)]
    y = np.zeros(n, dtype=bool)
    probs = {cfg: np.full(n, 0.2) for cfg in stage1.BINARY_CLAIM_CONFIGS}
    probs["B0"] = np.zeros(n)
    binary = s1b.panel_family_draws(
        rows_for_date, y, probs, 5, 0, 0, 0, n_draws=6, kind="binary"
    )
    assert np.isneginf(binary["v"]["M3-ALL"]["b"]).all()
    assert np.isneginf(binary["delta_v"]).all()
    assert np.isneginf(binary["bss"]["M3-ALL"]).all()
    assert np.isposinf(binary["wace"]).all()
    assert stage1.gate_lower_bound(binary["v"]["M3-ALL"]["b"]) == -np.inf
    assert stage1._quantile_all_draws(binary["wace"], 0.05) == np.inf

    a = np.zeros(n)
    q = {cfg: {key: np.zeros(n) for key in stage1.TAU_KEYS} for cfg in stage1.QUANTILE_CLAIM_CONFIGS}
    quantile = s1b.panel_family_draws(
        rows_for_date, a, q, 5, 0, 1, 0, n_draws=6, kind="quantile"
    )
    assert np.isneginf(quantile["skill"]).all()
    assert stage1.gate_lower_bound(quantile["skill"]) == -np.inf

    source = Path(s1b.__file__).read_text(encoding="utf-8")
    assert "nanquantile" not in source
    assert _BANNED_WORD not in source


# ── 5. honest-N and leave-one-episode-out ────────────────────────────────────


def test_honest_n_uses_event_dates_and_ignores_per_ticker_counts():
    h = 5
    n_names = 12
    base = 40
    step = 60
    n_dates = base + (n_names - 1) * step + 5
    session = ["2019-01-15"] * n_dates
    names = [f"T{i:02d}" for i in range(n_names)]
    date_index: list[int] = []
    outcome: list[bool] = []
    ticker_col: list[str] = []
    for i, name in enumerate(names):
        event = base + i * step
        session[event] = f"{2020 + i // 12:04d}-{(i % 12) + 1:02d}-15"
        date_index.append(event)
        outcome.append(True)
        ticker_col.append(name)
        date_index.append(0)
        outcome.append(False)
        ticker_col.append(name)
    report = s1b.panel_honest_n(
        np.asarray(date_index), np.asarray(outcome), session, h, tickers=ticker_col
    )
    assert report["events"] == n_names
    assert report["ticker_events"] == n_names
    assert report["episodes"] == n_names
    assert report["event_months"] == n_names
    assert report["power_floor"]["met"] is True
    assert report["per_ticker_episodes"] == {name: 1 for name in names}
    assert report["power_floor"]["met"] == (
        report["episodes"] >= stage1.POWER_MIN_EPISODES
        and report["event_months"] >= stage1.POWER_MIN_MONTHS
    )

    same_day = s1b.panel_honest_n(
        np.array([10, 10]),
        np.array([True, True]),
        ["2021-06-15"] * 12,
        h,
        tickers=["QQQ", "IWM"],
    )
    assert same_day["events"] == 1
    assert same_day["ticker_events"] == 2

    merged = s1b.panel_honest_n(
        np.array([10, 12]),
        np.array([True, True]),
        [f"2021-06-{day + 1:02d}" for day in range(20)],
        h,
    )
    assert merged["clusters"] == 1
    assert merged["episodes"] == 1
    assert merged["episode_windows"] == [[10 - stage1.EPISODE_PRE, 12 + h]]


def test_loeo_removes_the_episode_dates_from_all_tickers():
    n_dates = 40
    names = ["QQQ", "IWM"]
    date_index = np.array([day for day in range(n_dates) for _name in names], dtype=int)
    y = np.zeros(n_dates * len(names), dtype=bool)
    y[30 * len(names) + 0] = True
    ticker_col = [name for _day in range(n_dates) for name in names]
    session = [f"2021-03-{(day % 28) + 1:02d}" for day in range(n_dates)]
    honest = s1b.panel_honest_n(date_index, y, session, 5, tickers=ticker_col)
    assert honest["episode_windows"] == [[9, 35]]
    probs = {cfg: np.full(len(y), 0.2) for cfg in stage1.BINARY_CLAIM_CONFIGS}
    report = s1b.loeo_report(
        date_index, y, np.zeros(len(y)), probs, {}, honest["episodes_detail"], 5, "binary"
    )
    # Dates 9..35 inclusive are 27 sessions. Both tickers leave: 80 - 54 = 26.
    assert report["n_episodes"] == 1
    assert report["per_episode"][0]["window"] == [9, 35]
    assert report["per_episode"][0]["n_kept"] == 26


# ── 6–8. claims, trial family, output location ───────────────────────────────


def test_constants_match_the_seat_decisions():
    assert s1b.TRIAL_FAMILY == "grey_deer_pullback_v11"
    assert s1b.TRIAL_BUDGET == "PREREG_V11_PENDING"
    assert isinstance(s1b.TRIAL_BUDGET, str)
    assert s1b.TRIALS_PER_HORIZON == 22
    assert s1b.TRIALS_TOTAL == 66
    assert s1b.SCHEMA == "grey_deer_pullback_stage1b/v1"
    assert s1b.DEFAULT_OUT_DIR == "research/grey_deer/pullback_stage1b"
    assert s1b.build_parser().get_default("out_dir") == s1b.DEFAULT_OUT_DIR
    assert s1b.SEED_ROOT == 221012
    assert s1b.N_DRAWS == 10_000
    assert s1b.DIVIDEND_BASIS == "unadjusted"
    assert len(s1b.PANEL_TICKERS) == 14
    assert "SPY" not in s1b.PANEL_TICKERS
    assert s1b.PANEL_TICKERS == (
        "QQQ", "IWM", "DIA", "XLB", "XLC", "XLE", "XLF",
        "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
    )
    assert [cfg["id"] for cfg in stage1.CONFIGURATIONS] == [
        "B0", "B1-20", "B1-63", "B2-21", "B2-63", "M3-ALL", "M3-ALL-C0.1",
        "Q0", "Q1", "Q3-ALL",
    ]
    assert s1b.panel_fold_calendar(1321, 5)[0][0] == stage1.FIRST_TEST_IDX
    assert s1b.panel_fold_calendar(1321, 5) == stage1.fold_calendar_for_population(1321, 5)
    assert stage1.GATE_Q == pytest.approx(0.05 / 12)
    assert stage1.HORIZONS == (5, 10, 21)
    assert stage1.TAUS == (0.5, 0.8, 0.9)
    assert s1b.inc_row()["status"] == "NOT_APPLICABLE"
    assert s1b.inc_row()["id"] == "INC"
    assert s1b.freeze_block_reason() is not None
    assert "PREREG_V11_PENDING" in s1b.freeze_block_reason()


# ── 9. end-to-end synthetic panel ────────────────────────────────────────────


def _plant_crash(close: np.ndarray, index: int, ratio: float = 0.90) -> None:
    target = close[index - 1] * ratio
    close[index:] *= target / close[index]


def test_synthetic_panel_claims_are_byte_identical(tmp_path, monkeypatch):
    n = 340
    dates = pd.bdate_range("2021-07-06", periods=n)
    date_str = [day.strftime("%Y-%m-%d") for day in dates]
    assert date_str[0] == s1b.WINDOW_START
    panel_dir = tmp_path / "panel"
    panel_dir.mkdir()
    pins: dict[str, dict] = {}
    for i, ticker in enumerate(s1b.PANEL_TICKERS):
        rng = np.random.default_rng(221012 + i * 17)
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
        for index in (120, 200, 280, 320):
            _plant_crash(close, index)
        path = panel_dir / f"{ticker}.parquet"
        _frame(date_str, close).to_parquet(path, index=False)
        sub = stage1.normalize_subframe(pd.read_parquet(path))
        pins[ticker] = {
            "subframe_sha256": stage1.subframe_sha256(sub),
            "rows": int(len(sub)),
            "first_date": str(sub["date"].iloc[0]),
            "last_date": str(sub["date"].iloc[-1]),
        }
        assert pins[ticker]["rows"] == n
        assert "PREREG_V11_PENDING" not in pins[ticker].values()

    # The frozen window end is 2026-10-07. A 340-session synthetic calendar
    # cannot reach it inside the quantile-LP time budget, so this test points
    # the coverage predicate at the synthetic last session. The pending budget
    # string refuses a real run; a completed synthetic execution clears it.
    # Identity pins are the read-back hashes. Draw count is the packet's 100.
    monkeypatch.setattr(s1b, "AS_OF", date_str[-1])
    monkeypatch.setattr(s1b, "N_DRAWS", 100)
    monkeypatch.setattr(s1b, "TRIAL_BUDGET", 66)
    monkeypatch.setattr(s1b, "IDENTITY_PINS", pins)

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    rc1 = _run(panel_dir, out1)
    if rc1 != 0:
        detail = (out1 / s1b.RESULTS_JSON_NAME).read_text(encoding="utf-8")
        raise AssertionError(detail[:2000])
    rc2 = _run(panel_dir, out2)
    assert rc2 == 0

    json1 = (out1 / s1b.RESULTS_JSON_NAME).read_bytes()
    json2 = (out2 / s1b.RESULTS_JSON_NAME).read_bytes()
    md1 = (out1 / s1b.RESULTS_MD_NAME).read_bytes()
    md2 = (out2 / s1b.RESULTS_MD_NAME).read_bytes()
    assert json1 == json2
    assert md1 == md2

    payload = json.loads(json1)
    assert payload["schema"] == "grey_deer_pullback_stage1b/v1"
    assert payload["status"] == "OK"
    assert payload["trial_family"] == "grey_deer_pullback_v11"
    assert payload["seed_root"] == 221012
    assert payload["n_draws"] == 100
    assert payload["dividend_basis"] == "unadjusted"
    assert payload["panel"]["tickers"] == list(s1b.PANEL_TICKERS)
    assert payload["panel"]["spy_excluded"] is True
    assert len(payload["claims"]) == 12
    assert sum(1 for row in payload["claims"] if row["pop"] == "P-all") == 6
    active = [row for row in payload["claims"] if row["pop"] == "P-active"]
    assert len(active) == 6
    assert all(row["blocked_type"] == "OBSERVER_NOT_ON_MAIN" for row in active)
    assert {row["h"] for row in payload["claims"]} == {5, 10, 21}
    assert {row["claim"] for row in payload["claims"]} == {"binary", "quantile"}
    assert payload["inc"]["status"] == "NOT_APPLICABLE"
    assert payload["inc"]["id"] == "INC"
    assert payload["blocked"] == []
    assert not (s1b.ROOT / s1b.DEFAULT_OUT_DIR).exists()
    # The two artifact files live only under the directories this test passed.
    assert {path.name for path in out1.iterdir()} == {
        s1b.RESULTS_JSON_NAME,
        s1b.RESULTS_MD_NAME,
    }
