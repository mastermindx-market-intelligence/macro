"""Grey Deer W4: synthetic tests for the stage-1b pooled 14-ticker panel runner.

Seat decisions D1–D13. Synthetic frames only: no price download, no read of
``data/``, no write under ``research/`` or ``data/``. Every ``main`` call
receives an explicit ``--out-dir`` under ``tmp_path``.

The shipped module is frozen with prereg v1.1. The autouse fixture
``_pending_by_default`` puts every pin back to ``PREREG_V11_PENDING`` and
replaces the trial-ledger scope with a probe, so the refusal tests keep their
meaning and no test can append to the checkout's ``data/trial_ledger.jsonl``.
The frozen values are tested through the ``SHIPPED_*`` and ``REAL_*`` names.

Run:
    ~/lanes/venv/bin/python -m pytest -q tests/test_grey_deer_pullback_stage1b.py
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402
import scripts.research.grey_deer_pullback_stage1b as s1b  # noqa: E402
from scripts.research.grey_deer_panel_adjust import AdjustResult  # noqa: E402
from engine import trial_ledger  # noqa: E402

# The frozen (prereg v1.1) values, captured before any fixture patches them.
SHIPPED_TRIAL_BUDGET = s1b.TRIAL_BUDGET
SHIPPED_IDENTITY_PINS = {ticker: dict(pin) for ticker, pin in s1b.IDENTITY_PINS.items()}
SHIPPED_MANIFEST_BLOB_SHA = s1b.MANIFEST_BLOB_SHA
SHIPPED_PREREG_BLOB_SHA = s1b.PREREG_BLOB_SHA
REAL_LEDGER_SCOPE = s1b.trial_ledger_scope
REAL_REGISTER = trial_ledger.register_trials


@pytest.fixture(autouse=True)
def _pending_by_default(monkeypatch):
    """Start every test from the pending pins and a probe ledger scope.

    Returns the probe's event list: ``"enter"`` and ``"exit"`` around the
    scope. The real registrar raises if any test reaches it unpatched.
    """
    monkeypatch.setattr(
        s1b, "IDENTITY_PINS", {ticker: s1b._pending_pin() for ticker in s1b.PANEL_TICKERS}
    )
    monkeypatch.setattr(s1b, "TRIAL_BUDGET", s1b.PIN_PENDING)
    monkeypatch.setattr(s1b, "MANIFEST_BLOB_SHA", s1b.PIN_PENDING)
    monkeypatch.setattr(s1b, "PREREG_BLOB_SHA", s1b.PIN_PENDING)
    events: list[str] = []

    @contextlib.contextmanager
    def _probe_scope(ledger_path=None):
        events.append("enter")
        try:
            yield
        finally:
            events.append("exit")

    def _no_register(*_args, **_kwargs):
        raise AssertionError("a test reached the real trial-ledger registrar")

    monkeypatch.setattr(s1b, "trial_ledger_scope", _probe_scope)
    monkeypatch.setattr(trial_ledger, "register_trials", _no_register)
    return events


def _ship_frozen(monkeypatch) -> None:
    monkeypatch.setattr(s1b, "IDENTITY_PINS", {t: dict(p) for t, p in SHIPPED_IDENTITY_PINS.items()})
    monkeypatch.setattr(s1b, "TRIAL_BUDGET", SHIPPED_TRIAL_BUDGET)
    monkeypatch.setattr(s1b, "MANIFEST_BLOB_SHA", SHIPPED_MANIFEST_BLOB_SHA)
    monkeypatch.setattr(s1b, "PREREG_BLOB_SHA", SHIPPED_PREREG_BLOB_SHA)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


WINDOW_ENDS = ["2021-07-06", "2026-10-07"]
_BANNED_WORD = "vali" + "dated"
_SPLIT_TICKERS = {"XLB", "XLE", "XLK", "XLU", "XLY"}
_HAVE_0818 = {"DIA", "XLB", "XLC", "XLK", "XLV"}
_COMMON = ["2021-07-06", "2025-12-04", "2025-12-05", "2026-10-07"]


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


def _governed_dates(ticker: str, extra: dict[str, list[str]] | None = None) -> list[str]:
    dates = list(_COMMON)
    if ticker in _HAVE_0818:
        dates.append("2026-08-18")
    if extra:
        dates.extend(extra.get(ticker, ()))
    return sorted(set(dates))


def _governed_closes(ticker: str, dates: list[str]) -> list[float]:
    if ticker in _SPLIT_TICKERS:
        return [200.0 if day < "2025-12-05" else 100.0 for day in dates]
    return [100.0 for _day in dates]


def _write_governed(
    directory: Path,
    *,
    extra: dict[str, list[str]] | None = None,
    mutate=None,
) -> None:
    def dates_for(ticker: str) -> list[str]:
        return _governed_dates(ticker, extra)

    def closes_for(ticker: str) -> list[float]:
        dates = dates_for(ticker)
        closes = _governed_closes(ticker, dates)
        if mutate is not None:
            mutate(ticker, dates, closes)
        return closes

    _write_panel(directory, dates_for, closes_for)


def _pins_from_dir(panel_dir: Path) -> dict[str, dict]:
    pins: dict[str, dict] = {}
    for ticker in s1b.PANEL_TICKERS:
        sub = stage1.normalize_subframe(pd.read_parquet(panel_dir / f"{ticker}.parquet"))
        pins[ticker] = {
            "subframe_sha256": stage1.subframe_sha256(sub),
            "rows": int(len(sub)),
            "first_date": str(sub["date"].iloc[0]),
            "last_date": str(sub["date"].iloc[-1]),
        }
    return pins


def _freeze_runtime(monkeypatch, pins: dict[str, dict]) -> None:
    monkeypatch.setattr(s1b, "IDENTITY_PINS", pins)
    monkeypatch.setattr(s1b, "TRIAL_BUDGET", s1b.TRIALS_TOTAL)
    monkeypatch.setattr(s1b, "MANIFEST_BLOB_SHA", "f" * 64)
    monkeypatch.setattr(s1b, "PREREG_BLOB_SHA", "e" * 64)


def _arm_calendar(monkeypatch, intersection: list[str]) -> None:
    """Let a short synthetic intersection pass the D15 length and NYSE checks."""
    monkeypatch.setattr(s1b, "EXPECTED_COMMON_SESSIONS", len(intersection))
    union = sorted(set(intersection) | set(s1b.PINNED_CALENDAR_EXCLUSIONS))
    monkeypatch.setattr(s1b, "nyse_sessions", lambda _start, _end, union=union: list(union))


def _paths(panel: Path) -> dict[str, Path]:
    return {ticker: panel / f"{ticker}.parquet" for ticker in s1b.PANEL_TICKERS}


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
    payload = json.loads((out / s1b.RESULTS_JSON_NAME).read_text(encoding="utf-8"))
    assert payload["manifest_path"] == s1b.MANIFEST_PATH
    assert payload["manifest_version"] == s1b.MANIFEST_VERSION
    assert payload["manifest_blob_sha"] == s1b.PIN_PENDING
    assert payload["prereg_path"] == s1b.PREREG_PATH
    assert payload["prereg_blob_sha"] == s1b.PIN_PENDING
    assert payload["bootstrap"]["n_draws"] == s1b.N_DRAWS
    assert payload["subframe_sha256"]["QQQ"].startswith("UNKNOWN:")
    assert len(payload["adjust_module_blob_sha"]) == 40
    note = (out / s1b.RESULTS_MD_NAME).read_text(encoding="utf-8")
    assert f"n_draws={s1b.N_DRAWS}" in note
    assert s1b.MANIFEST_PATH in note
    assert "seed_root=221012" in note


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


def test_calendar_misalignment_lists_the_unpinned_difference(tmp_path, capsys):
    """A date outside the pinned exclusion is CALENDAR_MISALIGNED (D15)."""
    panel = tmp_path / "panel"
    _write_governed(panel, extra={"XLY": ["2024-06-04"]})
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / CALENDAR_MISALIGNED"
    row = _blocked(out)
    assert row["type"] == "CALENDAR_MISALIGNED"
    assert row["unexpected"] == ["2024-06-04"]
    assert "2024-06-04" in row["detail"]


def test_split_discontinuity_names_ticker_and_date(tmp_path, capsys):
    """An unpinned jump on adjusted closes refuses and names the first break."""
    panel = tmp_path / "panel"

    def mutate(ticker, _dates, closes):
        if ticker == "DIA":
            closes[-1] = 40.0

    _write_governed(panel, mutate=mutate)
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / SPLIT_DISCONTINUITY"
    row = _blocked(out)
    assert row["type"] == "SPLIT_DISCONTINUITY"
    assert "DIA" in row["detail"]
    assert "2026-10-07" in row["detail"]
    assert row["breaks"][0] == {"ticker": "DIA", "date": "2026-10-07"}


def test_ratio_of_exactly_one_point_two_five_is_not_a_split(tmp_path, monkeypatch):
    """The break check is strict. 125/100 == 1.25 is not a discontinuity."""
    panel = tmp_path / "panel"

    def mutate(ticker, _dates, closes):
        if ticker == "DIA":
            closes[-1] = 125.0

    _write_governed(panel, mutate=mutate)
    _arm_calendar(monkeypatch, _COMMON)
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    row = _blocked(out)
    assert row["type"] == "PREREG_V11_PENDING"


def test_unpinned_jump_is_not_silently_adjusted(tmp_path, capsys):
    """No declared-action flag. An unpinned 2-for-1 refuses as a discontinuity."""
    option_strings = [opt for action in s1b.build_parser()._actions for opt in action.option_strings]
    assert "--corporate-action" not in option_strings
    panel = tmp_path / "panel"

    def mutate(ticker, _dates, closes):
        if ticker == "XLF":
            closes[-1] = 50.0

    _write_governed(panel, mutate=mutate)
    out = tmp_path / "out"
    assert _run(panel, out) == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / SPLIT_DISCONTINUITY"
    row = _blocked(out)
    assert "XLF" in row["detail"]
    assert "2026-10-07" in row["detail"]
    source = Path(s1b.__file__).read_text(encoding="utf-8")
    assert "SPLIT_UNADJUSTED" not in source


def test_pending_pin_refuses_before_features_or_labels(tmp_path, monkeypatch):
    called = {"n": 0}

    def _boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("feature or label construction ran")

    monkeypatch.setattr(stage1, "build_features", _boom)
    monkeypatch.setattr(stage1, "build_labels", _boom)
    panel = tmp_path / "panel"
    _write_governed(panel)
    _arm_calendar(monkeypatch, _COMMON)
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
    assert SHIPPED_TRIAL_BUDGET == 66 == s1b.TRIALS_TOTAL
    assert isinstance(SHIPPED_TRIAL_BUDGET, int)
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
    assert s1b.EXPECTED_COMMON_SESSIONS == 1320
    assert s1b.MANIFEST_VERSION == "1.1.0"
    assert SHIPPED_MANIFEST_BLOB_SHA != s1b.PIN_PENDING
    assert SHIPPED_PREREG_BLOB_SHA != s1b.PIN_PENDING
    assert "grey_deer_panel_adjust.PINNED_SPLITS" in s1b.DIVIDEND_DISCLOSURE
    assert "2026-08-18" in s1b.DIVIDEND_DISCLOSURE
    assert s1b.build_parser().get_default("blocks_only") is False


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
    monkeypatch.setattr(s1b, "MANIFEST_BLOB_SHA", "f" * 64)
    monkeypatch.setattr(s1b, "PREREG_BLOB_SHA", "e" * 64)
    # The 340-session synthetic calendar is not the frozen NYSE intersection
    # and contains no pinned split. Point the input gates at this fixture.
    monkeypatch.setattr(s1b, "PINNED_SPLITS", {})
    monkeypatch.setattr(s1b, "PINNED_CALENDAR_EXCLUSIONS", frozenset())
    monkeypatch.setattr(s1b, "EXPECTED_COMMON_SESSIONS", n)
    monkeypatch.setattr(s1b, "nyse_sessions", lambda _start, _end, dates=list(date_str): list(dates))

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
    assert payload["bootstrap"]["n_draws"] == s1b.N_DRAWS == 100
    assert payload["bootstrap"]["seed_root"] == 221012
    assert payload["bootstrap"]["axis"] == "date"
    assert payload["bootstrap"]["block_length_rule"] == "stage-1 block_length(h, variant)"
    assert payload["fold_block_table"]
    assert payload["fold_block_table"][0]["start_date"]
    assert payload["manifest_blob_sha"] == "f" * 64
    assert payload["prereg_blob_sha"] == "e" * 64
    assert payload["adjust_module_blob_sha"]
    assert len(payload["subframe_sha256"]) == 14
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


# ── D14 / D15 repair ─────────────────────────────────────────────────────────


def test_prepare_panel_is_called_once_with_seat_pins(tmp_path, monkeypatch):
    calls = []
    real = s1b.prepare_panel

    def spy(frames, window_start, as_of, splits=None, excluded=None):
        calls.append((window_start, as_of, splits, excluded, len(frames)))
        return real(frames, window_start, as_of, splits=splits, excluded=excluded)

    monkeypatch.setattr(s1b, "prepare_panel", spy)
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: WINDOW_ENDS, _mild)
    with pytest.raises(stage1.Blocked):
        s1b.load_panel(_paths(panel))
    assert len(calls) == 1
    window_start, as_of, splits, excluded, n_frames = calls[0]
    assert window_start == s1b.WINDOW_START
    assert as_of == s1b.AS_OF
    assert splits is s1b.PINNED_SPLITS
    assert excluded is s1b.PINNED_CALENDAR_EXCLUSIONS
    assert n_frames == 14


@pytest.mark.parametrize(
    ("reason", "detail", "needle"),
    [
        (
            "SPLIT_TABLE_MISMATCH",
            {
                "mismatches": [
                    {
                        "ticker": "XLB",
                        "date": "2025-12-05",
                        "ratio": 2.0,
                        "why": "ratio_out_of_tolerance",
                    }
                ]
            },
            "XLB 2025-12-05",
        ),
        (
            "SPLIT_DISCONTINUITY",
            {"breaks": [{"ticker": "DIA", "date": "2026-10-07"}]},
            "DIA 2026-10-07",
        ),
        (
            "CALENDAR_MISALIGNED",
            {
                "unexpected": ["2024-06-04"],
                "pinned_absent": [],
                "missing_by_ticker": {"XLY": ["2024-06-03"]},
            },
            "XLY 2024-06-03",
        ),
    ],
)
def test_prepare_panel_blocked_reasons_surface(tmp_path, monkeypatch, reason, detail, needle):
    def fake(*_args, **_kwargs):
        return AdjustResult(
            status="BLOCKED",
            reason=reason,
            detail=detail,
            frames=None,
            calendar=None,
            confirmations=None,
        )

    monkeypatch.setattr(s1b, "prepare_panel", fake)
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: WINDOW_ENDS, _mild)
    with pytest.raises(stage1.Blocked) as caught:
        s1b.load_panel(_paths(panel))
    assert caught.value.type == reason
    assert needle in caught.value.detail


def test_pinned_split_and_exclusion_adjust_the_loaded_closes(tmp_path, monkeypatch):
    panel = tmp_path / "panel"
    _write_governed(panel)
    _arm_calendar(monkeypatch, _COMMON)
    _freeze_runtime(monkeypatch, _pins_from_dir(panel))
    loaded = s1b.load_panel(_paths(panel))
    assert loaded.calendar == _COMMON
    assert "2026-08-18" not in loaded.calendar
    raw = stage1.normalize_subframe(pd.read_parquet(panel / "XLB.parquet"))
    assert loaded.subframe_sha256["XLB"] == stage1.subframe_sha256(raw)
    raw_close = float(raw.loc[raw["date"] == "2021-07-06", "close"].iloc[0])
    assert raw_close == pytest.approx(200.0)
    adjusted = loaded.frames["XLB"]
    assert float(adjusted.loc[adjusted["date"] == "2021-07-06", "close"].iloc[0]) == pytest.approx(100.0)
    assert float(adjusted.loc[adjusted["date"] == "2025-12-05", "close"].iloc[0]) == pytest.approx(100.0)
    assert float(adjusted.loc[adjusted["date"] == "2021-07-06", "volume"].iloc[0]) == pytest.approx(2_000_000.0)
    assert float(adjusted.loc[adjusted["date"] == "2025-12-05", "volume"].iloc[0]) == pytest.approx(1_000_000.0)
    assert float(adjusted.loc[adjusted["date"] == "2021-07-06", "transactions"].iloc[0]) == pytest.approx(1000.0)
    qqq = loaded.frames["QQQ"]
    assert float(qqq.loc[qqq["date"] == "2021-07-06", "close"].iloc[0]) == pytest.approx(100.0)
    assert float(qqq.loc[qqq["date"] == "2021-07-06", "volume"].iloc[0]) == pytest.approx(1_000_000.0)


def test_wrong_common_session_count_and_nyse_mismatch(tmp_path, monkeypatch):
    panel = tmp_path / "panel"
    _write_governed(panel)
    paths = _paths(panel)
    with pytest.raises(stage1.Blocked) as count_refusal:
        s1b.load_panel(paths)
    assert count_refusal.value.type == "CALENDAR_MISALIGNED"
    assert count_refusal.value.expected == 1320
    assert count_refusal.value.got == 4

    monkeypatch.setattr(s1b, "EXPECTED_COMMON_SESSIONS", 4)
    monkeypatch.setattr(s1b, "nyse_sessions", lambda _start, _end: ["1999-01-04"])
    with pytest.raises(stage1.Blocked) as nyse_refusal:
        s1b.load_panel(paths)
    assert nyse_refusal.value.type == "CALENDAR_MISALIGNED"
    assert nyse_refusal.value.missing == ["1999-01-04"]
    assert "2021-07-06" in nyse_refusal.value.unexpected
    assert "2026-08-18" in nyse_refusal.value.unexpected


def test_strict_maps_nonfinite_to_none_and_json_rejects_constants(tmp_path):
    payload = {
        "nan": float("nan"),
        "pos": float("inf"),
        "neg": float("-inf"),
        "npnan": np.float64("nan"),
        "arr": np.array([1.0, np.inf, np.nan]),
        "ok": np.float64(1.5),
        "i": np.int64(3),
    }
    ready = s1b._strict(payload)
    assert ready["nan"] is None
    assert ready["pos"] is None
    assert ready["neg"] is None
    assert ready["npnan"] is None
    assert ready["arr"] == [1.0, None, None]
    assert ready["ok"] == 1.5
    assert ready["i"] == 3
    text = json.dumps(ready, allow_nan=False)
    json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    s1b.write_payload(
        tmp_path,
        {"schema": s1b.SCHEMA, "status": "BLOCKED", "leap": float("nan"), "claims": [], "blocked": []},
    )
    written = (tmp_path / s1b.RESULTS_JSON_NAME).read_text(encoding="utf-8")
    json.loads(written, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert "NaN" not in written
    assert "Infinity" not in written


def test_payload_bootstrap_record_and_fold_block_table():
    record = s1b._bootstrap_record()
    assert record == {
        "n_draws": s1b.N_DRAWS,
        "seed_root": s1b.SEED_ROOT,
        "axis": "date",
        "block_length_rule": "stage-1 block_length(h, variant)",
    }
    calendar = ["2022-01-03"] * 1000 + ["2026-09-01"] * 400
    rows = s1b.block_table(calendar)
    assert rows
    seen_after = set()
    for row in rows:
        assert row["start_date"] == calendar[row["start_index"]]
        assert row["end_date"] == calendar[row["end_index"]]
        assert row["after_excluded_session"] is (row["start_date"] > "2026-08-18")
        seen_after.add(row["after_excluded_session"])
    assert seen_after == {False, True}
    for h in stage1.HORIZONS:
        folds = s1b.panel_fold_calendar(len(calendar), h)
        got = [row for row in rows if row["h"] == h]
        assert [(row["start_index"], row["end_index"]) for row in got] == list(folds)
        assert [row["fold"] for row in got] == list(range(1, len(folds) + 1))
    note = s1b.render_markdown(
        {
            "schema": s1b.SCHEMA,
            "status": "OK",
            "trial_family": s1b.TRIAL_FAMILY,
            "trial_budget": s1b.TRIAL_BUDGET,
            "dividend_basis": s1b.DIVIDEND_BASIS,
            "bootstrap": record,
            "claims": [],
            "inc": s1b.inc_row(),
            "episodes": {},
            "dividend_disclosure": s1b.DIVIDEND_DISCLOSURE,
        }
    )
    assert f"n_draws={s1b.N_DRAWS}" in note
    assert "seed_root=221012" in note
    assert "axis=date" in note
    assert "block_length_rule=stage-1 block_length(h, variant)" in note


def test_blocks_only_prints_table_and_pins_without_a_fit(
    tmp_path, monkeypatch, capsys, _pending_by_default
):
    n = 340
    dates = [day.strftime("%Y-%m-%d") for day in pd.bdate_range("2021-07-06", periods=n)]
    panel = tmp_path / "panel"
    _write_panel(panel, lambda _t: dates, lambda _t: [100.0] * n)
    monkeypatch.setattr(s1b, "AS_OF", dates[-1])
    monkeypatch.setattr(s1b, "PINNED_SPLITS", {})
    monkeypatch.setattr(s1b, "PINNED_CALENDAR_EXCLUSIONS", frozenset())
    monkeypatch.setattr(s1b, "EXPECTED_COMMON_SESSIONS", n)
    monkeypatch.setattr(s1b, "nyse_sessions", lambda _start, _end, dates=list(dates): list(dates))

    def _boom(*_args, **_kwargs):
        raise AssertionError("fit or label ran")

    monkeypatch.setattr(s1b, "run_pooled_fits", _boom)
    monkeypatch.setattr(stage1, "build_labels", _boom)
    out = tmp_path / "out"
    assert _run(panel, out, ["--blocks-only"]) == 0
    assert not out.exists()
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith("BLOCK ") for line in lines)
    pin_lines = [line for line in lines if line.startswith("PIN ")]
    assert len(pin_lines) == 14
    for line in pin_lines:
        _prefix, ticker, sha = line.split()
        raw = stage1.normalize_subframe(pd.read_parquet(panel / f"{ticker}.parquet"))
        assert sha == stage1.subframe_sha256(raw)
        assert ticker in s1b.PANEL_TICKERS
    assert _pending_by_default == []


def test_pending_manifest_and_prereg_blob_pins_are_in_the_freeze_reason():
    reason = s1b.freeze_block_reason()
    assert reason is not None
    assert "MANIFEST_BLOB_SHA" in reason
    assert s1b.MANIFEST_PATH in reason
    assert "PREREG_BLOB_SHA" in reason
    assert s1b.PREREG_PATH in reason
    assert s1b.PIN_PENDING in reason
    assert s1b.MANIFEST_BLOB_SHA == s1b.PIN_PENDING
    assert s1b.PREREG_BLOB_SHA == s1b.PIN_PENDING


# ── 10. prereg v1.1 freeze: shipped pins, blob pins, ledger registration ─────


_PIN_ROW = re.compile(
    r"^\| (?P<ticker>[A-Z]+) \| `(?P<sha>[0-9a-f]{64})` \| (?P<rows>\d+) \| "
    r"(?P<first>\d{4}-\d{2}-\d{2}) \| (?P<last>\d{4}-\d{2}-\d{2}) \|$"
)
_BLOCK_ROW = re.compile(
    r"^\| (?P<block>[1-8]) \| (?P<s>\d+) \| (?P<sd>\d{4}-\d{2}-\d{2}) \| "
    r"(?P<e>[\d /]+) \| (?P<ed>[\d /-]+) \|$"
)


def test_shipped_constants_clear_the_freeze_gate(monkeypatch):
    assert s1b.freeze_block_reason() is not None
    _ship_frozen(monkeypatch)
    assert s1b.freeze_block_reason() is None
    assert set(SHIPPED_IDENTITY_PINS) == set(s1b.PANEL_TICKERS)
    for ticker, pin in SHIPPED_IDENTITY_PINS.items():
        assert set(pin) == {"subframe_sha256", "rows", "first_date", "last_date"}, ticker
        assert re.fullmatch(r"[0-9a-f]{64}", pin["subframe_sha256"]), ticker
        assert pin["rows"] in (1320, 1321), ticker
        assert pin["first_date"] == s1b.WINDOW_START, ticker
        assert pin["last_date"] == s1b.AS_OF == "2026-10-07", ticker
    with_0818 = {t for t, p in SHIPPED_IDENTITY_PINS.items() if p["rows"] == 1321}
    assert with_0818 == _HAVE_0818
    assert len({pin["subframe_sha256"] for pin in SHIPPED_IDENTITY_PINS.values()}) == 14


def test_prereg_pin_table_equals_the_shipped_pins():
    text = (s1b.ROOT / s1b.PREREG_PATH).read_text(encoding="utf-8")
    section = text.split("## 4.")[0].split("## 3.")[1]
    pending_rows = [
        line for line in section.splitlines() if line.startswith("| ") and s1b.PIN_PENDING in line
    ]
    assert pending_rows == []
    table: dict[str, dict] = {}
    for line in text.splitlines():
        match = _PIN_ROW.match(line)
        if match:
            assert match["ticker"] not in table
            table[match["ticker"]] = {
                "subframe_sha256": match["sha"],
                "rows": int(match["rows"]),
                "first_date": match["first"],
                "last_date": match["last"],
            }
    assert table == SHIPPED_IDENTITY_PINS


def test_prereg_block_table_equals_the_fold_calendar():
    text = (s1b.ROOT / s1b.PREREG_PATH).read_text(encoding="utf-8")
    rows = [m for m in map(_BLOCK_ROW.match, text.splitlines()) if m]
    assert [int(m["block"]) for m in rows] == list(range(1, 9))
    for h_pos, h in enumerate(stage1.HORIZONS):
        calendar = s1b.panel_fold_calendar(s1b.EXPECTED_COMMON_SESSIONS, h)
        assert len(calendar) == 8
        for match, (start, end) in zip(rows, calendar):
            assert int(match["s"]) == start
            ends = [int(part) for part in match["e"].split("/")]
            assert ends[h_pos if len(ends) == 3 else 0] == end


def test_blob_pins_are_the_frozen_manifest_and_prereg_blobs():
    assert SHIPPED_MANIFEST_BLOB_SHA == _git_blob_sha(s1b.ROOT / s1b.MANIFEST_PATH)
    assert SHIPPED_PREREG_BLOB_SHA == _git_blob_sha(s1b.ROOT / s1b.PREREG_PATH)
    for rel in (s1b.MANIFEST_PATH, s1b.PREREG_PATH):
        head = (s1b.ROOT / rel).read_text(encoding="utf-8").splitlines()[:12]
        assert any("FROZEN" in line for line in head), rel
        assert not any("NOT FROZEN" in line or "DRAFT" in line for line in head), rel


def test_main_registers_the_family_before_outcomes(tmp_path, monkeypatch, _pending_by_default):
    events = _pending_by_default
    panel = tmp_path / "panel"
    _write_governed(panel)
    _arm_calendar(monkeypatch, _COMMON)
    _freeze_runtime(monkeypatch, _pins_from_dir(panel))
    monkeypatch.setattr(s1b, "block_table", lambda _calendar: [])
    monkeypatch.setattr(s1b, "_print_block_table", lambda _table: None)

    def _execute(*_args, **_kwargs):
        events.append("execute")
        return {"status": "OK"}

    monkeypatch.setattr(s1b, "execute_panel", _execute)
    monkeypatch.setattr(s1b, "write_payload", lambda _out, _payload: events.append("write"))
    assert _run(panel, tmp_path / "out") == 0
    assert events == ["enter", "execute", "exit", "write"]


def test_pending_refusal_never_enters_the_ledger_scope(tmp_path, monkeypatch, _pending_by_default):
    panel = tmp_path / "panel"
    _write_governed(panel)
    _arm_calendar(monkeypatch, _COMMON)
    assert _run(panel, tmp_path / "out") == 2
    assert _blocked(tmp_path / "out")["type"] == "PREREG_V11_PENDING"
    assert _pending_by_default == []


def test_real_scope_registers_one_v11_row(tmp_path, monkeypatch):
    _ship_frozen(monkeypatch)
    monkeypatch.setattr(trial_ledger, "register_trials", REAL_REGISTER)
    ledger = tmp_path / "trial_ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    with REAL_LEDGER_SCOPE(ledger):
        pass
    with REAL_LEDGER_SCOPE(ledger):
        pass
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == 1
    row = rows[0]
    assert row["family"] == "grey_deer_pullback_v11"
    assert row["kind"] == "declared_budget"
    assert row["n"] == 66


def test_real_scope_refuses_a_checkout_without_the_ledger(tmp_path, monkeypatch):
    _ship_frozen(monkeypatch)
    monkeypatch.setattr(trial_ledger, "register_trials", REAL_REGISTER)
    ledger = tmp_path / "data" / "trial_ledger.jsonl"
    with pytest.raises(RuntimeError, match="worktree_sparse.py add data"):
        REAL_LEDGER_SCOPE(ledger)
    assert not ledger.exists()
    assert not ledger.parent.exists()


def test_real_scope_refuses_while_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(trial_ledger, "register_trials", REAL_REGISTER)
    ledger = tmp_path / "trial_ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    with pytest.raises(stage1.Blocked) as caught:
        REAL_LEDGER_SCOPE(ledger)
    assert caught.value.type == "PREREG_V11_PENDING"
    assert ledger.read_text(encoding="utf-8") == ""


def test_shipped_pins_refuse_a_synthetic_panel(tmp_path, monkeypatch, capsys, _pending_by_default):
    called = {"n": 0}

    def _boom(*_args, **_kwargs):
        called["n"] += 1
        raise AssertionError("feature or label construction ran")

    monkeypatch.setattr(stage1, "build_features", _boom)
    monkeypatch.setattr(stage1, "build_labels", _boom)
    _ship_frozen(monkeypatch)
    panel = tmp_path / "panel"
    _write_governed(panel)
    _arm_calendar(monkeypatch, _COMMON)
    assert _run(panel, tmp_path / "out") == 2
    assert capsys.readouterr().out.splitlines()[0] == "BLOCKED / SAMPLE_IDENTITY_MISMATCH"
    assert _blocked(tmp_path / "out")["type"] == "SAMPLE_IDENTITY_MISMATCH"
    assert called["n"] == 0
    assert _pending_by_default == []
