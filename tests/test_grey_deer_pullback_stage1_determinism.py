"""Determinism of the Grey Deer pullback stage-1 runner.

Synthetic data only: a seeded geometric Brownian motion on the runner's NYSE
window, plus small fixed-seed design matrices. No ``data/`` read or write, no
network, no Massive store, no real price series.

The end-to-end pair goes through ``main`` (so the subframe pin and the trial
ledger both run) with these monkeypatches:

* ``collectors.massive_stock_day.load_ticker`` returns the synthetic frame
  (the runner's documented injection seam; the real loader would read the store).
* ``SUBFRAME_SHA256`` is the synthetic subframe hash. The frozen pin would
  refuse the frame as ``SAMPLE_IDENTITY_MISMATCH``. The check still runs.
* ``trial_ledger.register_trials`` records calls into a list and does not
  open ``data/trial_ledger.jsonl``.
* ``N_DRAWS`` is set to 200. ``bootstrap_index_matrix`` binds
  ``n_draws=N_DRAWS`` at import, and ``run_bootstrap_cells`` does not pass
  ``n_draws``, so the function ``__defaults__`` is updated to ``(200, SEED_ROOT)``
  or the draw count stays 10,000.

``--skip-hydrate`` is the runner's own flag: ``hydrate`` would spawn
``scripts.fetch_r2``. Both runs log the same ``HYDRATE_SKIPPED`` deviation.
The only wall-clock field in the JSON is ``run.utc``.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402
from lib import nyse_calendar  # noqa: E402

# ``verify_identities`` writes this one clock field:
# ``dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")``.
_RUN_UTC_LINE = re.compile(br'^[ \t]*"utc": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[^"]*",\n', re.M)

_N = 100
_N_DRAWS = 8


def _independent_index_matrix(n: int, h: int, pop: int, fam: int, var: int, n_draws: int) -> np.ndarray:
    """Prereg §10 recipe, rebuilt without calling the runner.

    ``L = max(21, 2h)`` for ``var == 0`` and ``L = h`` for ``var == 1``.
    ``rng = default_rng(SeedSequence([221011, h, pop, fam, var]))``,
    ``starts = rng.integers(0, N, size=ceil(N / L))``, each block
    ``(start + arange(L)) % N``, concatenated, first ``N`` kept.
    """
    length = h if var == 1 else max(21, 2 * h)
    n_blocks = math.ceil(n / length)
    rng = np.random.default_rng(np.random.SeedSequence([221011, h, pop, fam, var]))
    offsets = np.arange(length)
    rows = np.empty((n_draws, n), dtype=np.int64)
    for draw in range(n_draws):
        starts = rng.integers(0, n, size=n_blocks)
        rows[draw] = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
    return rows


def _synthetic_gbm_frame() -> pd.DataFrame:
    """Seeded GBM daily bars on every NYSE session in the runner's window."""
    sessions = nyse_calendar.sessions_between(
        dt.date.fromisoformat(stage1.WINDOW_START),
        dt.date.fromisoformat(stage1.AS_OF),
    )
    n = len(sessions)
    rng = np.random.default_rng(20261012)
    sigma = 0.02
    mu = 0.0002
    log_r = rng.normal(mu - 0.5 * sigma * sigma, sigma, n)
    close = 400.0 * np.exp(np.cumsum(log_r))
    shock = np.minimum(np.abs(rng.normal(0.0, 0.002, n)), 0.05)
    open_ = close * (1.0 - 0.25 * shock)
    high = np.maximum(open_, close) * (1.0 + shock)
    low = np.minimum(open_, close) * (1.0 - shock)
    frame = pd.DataFrame(
        {
            "date": [d.isoformat() for d in sessions],
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, n).astype(np.float64),
            "transactions": rng.integers(10_000, 80_000, n).astype(np.float64),
        }
    )
    ratio = close[1:] / close[:-1]
    if np.any(low <= 0) or np.any((ratio < 0.75) | (ratio > (1.0 / 0.75))):
        raise AssertionError("synthetic GBM left the price-basis guard; the seed must be changed")
    if frame["date"].tolist() != sorted(frame["date"].tolist()):
        raise AssertionError("session dates are not sorted")
    return frame


def _recording_register(sink: list):
    """Stand-in for ``register_trials``: same constructor, no ledger file."""

    class _RecordingRegisterTrials:
        def __init__(self, family, budget, *, reason=None, basis="itemized", expiry=None, ledger=None):
            sink.append(
                (
                    "register_trials",
                    family,
                    int(budget),
                    basis,
                    reason,
                    expiry,
                    ledger is None,
                )
            )

        def __enter__(self):
            sink.append(("__enter__",))
            return self

        def __exit__(self, exc_type, exc, tb):
            sink.append(("__exit__", None if exc_type is None else exc_type.__name__))
            return False

    return _RecordingRegisterTrials


def _ledger_snapshot() -> dict[str, tuple[int, int] | None]:
    paths = {
        str(Path.cwd() / "data" / "trial_ledger.jsonl"),
        str(stage1.ROOT / "data" / "trial_ledger.jsonl"),
    }
    snap: dict[str, tuple[int, int] | None] = {}
    for text in paths:
        path = Path(text)
        if path.exists():
            stat = path.stat()
            snap[text] = (stat.st_size, stat.st_mtime_ns)
        else:
            snap[text] = None
    return snap


def _strip_run_utc(raw: bytes) -> bytes:
    """Remove the single ``run.utc`` line. Every other byte stays."""
    stripped, count = _RUN_UTC_LINE.subn(b"", raw)
    assert count == 1, f"expected exactly one run.utc line, found {count}"
    return stripped


def _run_evaluation(out_dir: Path, sink: list) -> bytes:
    rc = stage1.main(["--skip-hydrate", "--out-dir", str(out_dir)])
    path = out_dir / stage1.RESULTS_JSON_NAME
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    assert rc == 0, f"main rc={rc}\n{text[:1500]}"
    return path.read_bytes()


@pytest.mark.parametrize("h", (5, 10, 21))
@pytest.mark.parametrize("variant", (0, 1))
@pytest.mark.parametrize("pop,fam", [(0, 0), (1, 0), (0, 1)])
def test_bootstrap_index_matrix_repeats_and_matches_prereg_recipe(h, variant, pop, fam):
    kwargs = {"n_draws": _N_DRAWS}
    first = stage1.bootstrap_index_matrix(_N, h, pop, fam, variant, **kwargs)
    second = stage1.bootstrap_index_matrix(_N, h, pop, fam, variant, **kwargs)
    np.testing.assert_array_equal(first, second)
    assert first.shape == (_N_DRAWS, _N)
    assert first.dtype == np.int64
    assert int(first.min()) >= 0 and int(first.max()) < _N
    # var 0 -> L = max(21, 2h); var 1 -> L = h. A mismatch of block length or
    # of the SeedSequence argument order fails this equality.
    np.testing.assert_array_equal(
        first,
        _independent_index_matrix(_N, h, pop, fam, variant, _N_DRAWS),
    )


def test_distinct_bootstrap_codes_yield_distinct_matrices():
    codes = [
        (h, pop, fam, var)
        for h in (5, 10, 21)
        for pop in (0, 1)
        for fam in (0, 1)
        for var in (0, 1)
    ]
    matrices = [
        stage1.bootstrap_index_matrix(64, h, pop, fam, var, n_draws=4)
        for h, pop, fam, var in codes
    ]
    for i in range(len(matrices)):
        for j in range(i + 1, len(matrices)):
            assert not np.array_equal(matrices[i], matrices[j]), (codes[i], codes[j])


def test_fit_logistic_and_fit_quantile_lp_repeat_on_the_same_sample():
    rng = np.random.default_rng(11)
    n, p = 48, 3
    features = rng.normal(size=(n, p))
    design = np.column_stack([np.ones(n), features])
    true_beta = np.array([0.2, -0.4, 0.7, 0.1])
    y = (rng.random(n) < 1.0 / (1.0 + np.exp(-(design @ true_beta)))).astype(float)
    assert set(np.unique(y).tolist()) == {0.0, 1.0}

    beta_a = stage1.fit_logistic(design, y, stage1.C_MAIN)
    beta_b = stage1.fit_logistic(design, y, stage1.C_MAIN)
    np.testing.assert_array_equal(beta_a, beta_b)
    assert np.all(np.isfinite(beta_a))

    # Quantile LP adds its own intercept, so the design must not contain one.
    target = np.abs(0.02 + features @ np.array([0.01, -0.008, 0.004]) + rng.normal(0.0, 0.002, n))
    for tau in stage1.TAUS:
        intercept_a, coef_a = stage1.fit_quantile_lp(features, target, tau)
        intercept_b, coef_b = stage1.fit_quantile_lp(features, target, tau)
        np.testing.assert_array_equal(
            np.concatenate([[intercept_a], coef_a]),
            np.concatenate([[intercept_b], coef_b]),
        )
        assert math.isfinite(intercept_a)
        assert np.all(np.isfinite(coef_a))


def test_subframe_hash_follows_the_date_sort_and_changes_when_close_changes():
    rng = np.random.default_rng(19)
    n = 16
    dates = pd.bdate_range("2024-03-01", periods=n)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    shock = np.abs(rng.normal(0.0, 0.002, n))
    frame = pd.DataFrame(
        {
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "open": close * (1.0 - 0.25 * shock),
            "high": close * (1.0 + shock),
            "low": close * (1.0 - shock),
            "close": close,
            "volume": rng.integers(1_000_000, 2_000_000, n).astype(np.float64),
            "transactions": rng.integers(10_000, 20_000, n).astype(np.float64),
        }
    )
    order = rng.permutation(n)
    assert not np.array_equal(order, np.arange(n))
    shuffled = frame.iloc[order].reset_index(drop=True)
    assert shuffled["date"].tolist() != frame["date"].tolist()

    norm_input = stage1.normalize_subframe(frame)
    norm_shuffled = stage1.normalize_subframe(shuffled)
    # The runner sorts by date, so a row permutation does not change the hash.
    assert norm_shuffled["date"].is_monotonic_increasing
    pd.testing.assert_frame_equal(norm_shuffled, norm_input)
    base_sha = stage1.subframe_sha256(norm_input)
    assert stage1.subframe_sha256(norm_shuffled) == base_sha

    changed = frame.copy()
    old = float(changed.loc[changed.index[3], "close"])
    new = old * (1.0 + 1e-9)
    assert new != old
    assert float(new).hex() != float(old).hex()
    changed.loc[changed.index[3], "close"] = new
    assert stage1.subframe_sha256(stage1.normalize_subframe(changed)) != base_sha


def test_two_evaluations_match_except_run_utc_and_ledger_calls_match(tmp_path, monkeypatch):
    frame = _synthetic_gbm_frame()
    synthetic_sha = stage1.subframe_sha256(stage1.normalize_subframe(frame))
    assert synthetic_sha != stage1.SUBFRAME_SHA256

    # Production default is bound at import. Patching the global alone does not
    # change ``run_bootstrap_cells``, which omits ``n_draws``.
    assert stage1.N_DRAWS == 10_000
    assert stage1.bootstrap_index_matrix.__defaults__ == (stage1.N_DRAWS, stage1.SEED_ROOT)
    monkeypatch.setattr(stage1, "N_DRAWS", 200)
    monkeypatch.setattr(stage1.bootstrap_index_matrix, "__defaults__", (200, stage1.SEED_ROOT))
    monkeypatch.setattr(stage1, "SUBFRAME_SHA256", synthetic_sha)

    stub = types.ModuleType("collectors.massive_stock_day")
    stub.load_ticker = lambda *_a, **_k: frame.copy()
    monkeypatch.setitem(sys.modules, "collectors.massive_stock_day", stub)

    # The incumbent replay reads the risk-radar store and the SPY closes from
    # data/. Since the RT-02 repair it scores the evaluation-origin union and so
    # no longer refuses a synthetic series by itself; on a full checkout it
    # would score the live store against the synthetic closes. Pin the absent
    # source so the run stays hermetic and its blocked path stays typed.
    def _no_incumbent_store(_deviations=None):
        raise OSError("synthetic run: incumbent store not read")

    monkeypatch.setattr(stage1, "_inc_replay_inputs", _no_incumbent_store)

    ledger_before = _ledger_snapshot()
    calls_a: list = []
    calls_b: list = []
    monkeypatch.setattr(stage1.trial_ledger, "register_trials", _recording_register(calls_a))
    raw_a = _run_evaluation(tmp_path / "run_a", calls_a)
    monkeypatch.setattr(stage1.trial_ledger, "register_trials", _recording_register(calls_b))
    raw_b = _run_evaluation(tmp_path / "run_b", calls_b)
    assert _ledger_snapshot() == ledger_before

    assert _strip_run_utc(raw_a) == _strip_run_utc(raw_b)
    payload = json.loads(raw_a)
    assert "utc" in payload["run"]
    assert payload["run"]["utc"].startswith("20")
    for horizon in ("h5", "h10", "h21"):
        for family in ("binary", "quantile"):
            bootstrap = payload["comparison_sets"][horizon][family]["bootstrap"]
            assert bootstrap["primary"]["n_draws"] == 200
            assert bootstrap["sensitivity_L_h"]["n_draws"] == 200
    # The incumbent replay must refuse, not score a store series.
    assert payload["inc"]["blocked"] == "INC_SOURCE_UNAVAILABLE"
    assert [row["code"] for row in payload["deviations"]] == ["HYDRATE_SKIPPED"]

    assert calls_a == calls_b
    assert calls_a == [
        ("register_trials", stage1.TRIAL_FAMILY, stage1.TRIAL_BUDGET, "itemized", None, None, True),
        ("__enter__",),
        ("__exit__", None),
    ]
