"""Grey Deer W3: synthetic tests for the pullback stage-1 executing script.

Preregistration: ``research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md``
(blob ``49a68b5e9c6543d662044b0aa391c4b6e6e6052e``). §12 requires the dedicated
test file to prove, on synthetic data only: the purge, the fold calendar, the
comparison-set intersection, the reuse of one index draw across configurations
and the crossing-then-clip order. Complete set: tests 1, 2, 3, 4, 5, 6, 7 of
the lane packet plus the recommended checks (logistic gradient, the
negative-control half-length roll, and an undefined-statistic draw taking the
failing extreme).

Synthetic only: fixed-seed geometric random walks and hand-built arrays. No
``data/`` read or write, no network, no Massive store, no trial-ledger write,
no git-state dependence. ``load_ticker`` / ``fetch_r2`` / ``register_trials`` /
``subprocess`` appear ONLY as monkeypatch targets.

Run:
    python -m pytest tests/test_grey_deer_pullback_stage1.py -v
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import types
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────


def _random_walk_closes(n: int = 400, seed: int = 5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 400.0 * np.exp(np.cumsum(rng.normal(0.0, 0.011, n)))


def _raise_assertion(*_a, **_k):
    raise AssertionError("must not be called on this path")


# ── test 1: purge ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("h", stage1.HORIZONS)
def test_purge_excludes_origins_whose_horizon_crosses_fold_start(h):
    s0 = stage1.FIRST_TEST_IDX
    for candidates in (np.arange(0, s0), np.arange(stage1.WARM_IDX, s0)):
        kept = stage1.purged_training_indices(s0, h, candidates)
        assert kept.size
        # Frozen rule (prereg §7): admit training origin t only when idx(t)+h <= idx(s0).
        assert (kept + h <= s0).all()
        # The origin whose window ends exactly at the fold start is KEPT...
        assert (s0 - h) in kept
        # ...and the very next origin (window crossing into the test block) is not.
        assert (s0 - h + 1) not in kept
        assert (kept < s0).all()


# ── test 2: fold calendar ────────────────────────────────────────────────────


def test_fold_calendar_matches_prereg():
    # Synthetic index of 1,321 sessions (the frozen sample size), test region
    # running to the last row: first test idx 315, 8 blocks of 126 with a
    # 124-origin final block (>= 63, so no merge) — prereg §7 geometry.
    cal = stage1.build_fold_calendar(stage1.FIRST_TEST_IDX, 1320)
    assert cal[0][0] == stage1.FIRST_TEST_IDX
    assert len(cal) == 8
    lengths = [e - s + 1 for s, e in cal]
    assert all(l == stage1.BLOCK_LEN for l in lengths[:-1])
    assert lengths[-1] == 124
    assert min(lengths) >= stage1.MIN_FINAL_BLOCK  # no test block shorter than 63
    assert cal[-1][1] == 1320
    # Blocks are consecutive and non-overlapping.
    for (s1, e1), (s2, e2) in zip(cal, cal[1:]):
        assert e1 + 1 == s2
    # Per-horizon mature ends from prereg §7: last block 119 / 114 / 103 origins.
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 5)][-1] == 119
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 10)][-1] == 114
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 21)][-1] == 103
    # A final remainder shorter than 63 merges into its predecessor.
    merged = stage1.build_fold_calendar(315, 1197 + 40 - 1)  # 40-origin remainder
    assert len(merged) == 7
    assert merged[-1] == (1071, 1236)
    assert all(e - s + 1 >= stage1.MIN_FINAL_BLOCK for s, e in merged)


# ── test 5: crossing detected on unclipped predictions, then clip ────────────


def test_quantile_crossing_detected_before_clip():
    crossing = (
        np.array([0.03]),
        np.array([0.02]),
        np.array([0.05]),
    )  # q0.5 > q0.8 on the UNCLIPPED values -> that origin abstains
    issued, clipped, reasons = stage1.quantile_output_policy(*crossing)
    assert issued.tolist() == [False]
    assert reasons[0] == "QUANTILE_CROSSING"

    negative = (np.array([-0.01]), np.array([0.02]), np.array([0.05]))
    issued, clipped, reasons = stage1.quantile_output_policy(*negative)
    assert issued.tolist() == [True]
    assert reasons[0] is None
    q50, q80, q90 = clipped
    assert q50.tolist() == [0.0]  # clipped below at 0 only AFTER the crossing check
    assert q80.tolist() == [0.02]
    assert q90.tolist() == [0.05]


# ── test 6: in-memory identity recipe == the §3 reference recipe ─────────────


def _prereg_reference_sha(path: str) -> str:
    """The prereg §3 identity recipe, copied verbatim.

    Only the ``p = sys.argv[1]`` line becomes the ``path`` parameter and the
    final ``print`` becomes a return; every other line is byte-for-byte the
    frozen recipe from PULLBACK_PREREGISTRATION_2026-10-11.md §3.
    """
    import hashlib
    import pandas as pd  # noqa: F811  (verbatim recipe body)

    p = path
    raw = open(p, "rb").read()  # noqa: F841  (part of the frozen recipe)
    df = pd.read_parquet(p)
    df = df.reset_index(drop=("date" in df.columns))
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cols = ["date", "open", "high", "low", "close", "volume", "transactions"]
    sub = df[df["date"] <= "2026-10-07"][cols].sort_values("date")

    def enc(v):
        if isinstance(v, str):
            return v
        if pd.isna(v):
            return "NA"
        return float(v).hex()

    h = hashlib.sha256()
    h.update(("|".join(cols) + "\n").encode())
    for row in sub.itertuples(index=False):
        h.update(("|".join(enc(v) for v in row) + "\n").encode())
    return h.hexdigest()


def test_identity_recipe_matches_reference_on_synthetic_frame(tmp_path):
    rng = np.random.default_rng(11)
    n = 30
    idx = pd.bdate_range("2026-09-01", periods=n)
    assert (idx > "2026-10-07").any()  # fixture really has rows after AS_OF
    close = _random_walk_closes(n, seed=11)
    frame = pd.DataFrame(
        {
            "open": close * (1 + rng.normal(0, 0.002, n)),
            "high": close * (1 + np.abs(rng.normal(0, 0.004, n))),
            "low": close * (1 - np.abs(rng.normal(0, 0.004, n))),
            "close": close,
            "volume": rng.integers(4_000_000, 9_000_000, n).astype(float),
            "transactions": rng.integers(80_000, 200_000, n).astype(float),
        },
        index=idx.rename("date"),
    )
    frame.loc[frame.index[3], "volume"] = np.nan  # the NA encoding path
    frame.loc[frame.index[7], "volume"] = np.nan
    p = tmp_path / "SPY.parquet"
    frame.to_parquet(p)

    # The in-memory recipe applied to the frame load_ticker would return (never
    # a second read of the file) must equal the §3 reference run on the path.
    loaded = pd.read_parquet(p)
    sub = stage1.normalize_subframe(loaded)
    got = stage1.subframe_sha256(sub)
    want = _prereg_reference_sha(str(p))
    assert got == want
    # Sanity: the hashed subframe drops the post-AS_OF rows and encodes NA.
    n_expected = int((sub["date"] <= stage1.AS_OF).sum())
    assert len(sub) == n_expected < n
    assert "NA" in {stage1._enc(v) for v in frame["volume"].tolist()}


# ── test 7: --dry-run touches no data; empty store blocks without a ledger ───


def test_dry_run_reads_no_data(tmp_path, monkeypatch, capsys):
    canned = {
        "schema": stage1.SCHEMA,
        "prereg": {
            "path": stage1.PREREG_PATH,
            "blob_sha": stage1.PREREG_BLOB,
            "sha256": stage1.PREREG_SHA256,
        },
        "manifest": {
            "path": stage1.MANIFEST_PATH,
            "blob_sha": stage1.MANIFEST_BLOB,
            "version": stage1.MANIFEST_VERSION,
        },
        "run": {
            "utc": "canned",
            "commit_sha": "canned",
            "script_blob_sha": "canned",
            "test_blob_sha": "canned",
        },
    }
    monkeypatch.setattr(stage1, "verify_identities", lambda **kwargs: dict(canned))

    # load_ticker is patched at its home module as the script imports it; a
    # stub module keeps the real collectors chain (requests/yaml) unimported.
    stub = types.ModuleType("collectors.massive_stock_day")
    stub.load_ticker = _raise_assertion
    monkeypatch.setitem(sys.modules, "collectors.massive_stock_day", stub)
    monkeypatch.setattr(stage1.subprocess, "run", _raise_assertion)
    monkeypatch.setattr(stage1.trial_ledger, "register_trials", _raise_assertion)

    assert stage1.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "PULLBACK_PREREGISTRATION_2026-10-11.md" in out
    assert stage1.PREREG_BLOB in out
    assert any(cfg_id in out for cfg_id in ("M3-ALL", "B0"))  # configuration table

    # An empty store frame blocks as SOURCE_UNREADABLE before any ledger entry.
    stub.load_ticker = lambda *_a, **_k: pd.DataFrame()
    assert stage1.main(["--skip-hydrate", "--out-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "BLOCKED / SOURCE_UNREADABLE"
    blocked = json.loads((tmp_path / "PULLBACK_STAGE1_RESULTS_2026-10-11.json").read_text())
    assert blocked["blocked"][0]["type"] == "SOURCE_UNREADABLE"
    assert blocked["run"]["commit_sha"] == "canned"


# ── test 3: comparison set = intersection of issued origins ──────────────────


def test_comparison_set_is_the_intersection_of_issued_origins():
    origin_idx = np.arange(100, 110)
    masks = {
        "A": np.array([1, 1, 1, 0, 1, 1, 1, 1, 1, 1], dtype=bool),
        "B": np.array([1, 1, 0, 1, 1, 1, 0, 1, 1, 1], dtype=bool),
    }
    reasons = {
        "A": np.array([None] * 3 + ["FIT_NONCONVERGENCE"] + [None] * 6, dtype=object),
        "B": np.array(
            [None, None, "QUANTILE_CROSSING", None, None, None, "QUANTILE_CROSSING", None, None, None],
            dtype=object,
        ),
    }
    common = stage1.intersection_of_issued(masks)
    expected = masks["A"] & masks["B"]
    assert common.tolist() == expected.tolist()

    report = stage1.comparison_set_report(origin_idx, masks, reasons)
    # Two configs with different abstention masks compare on the common origins
    # only, and N_common is reported.
    assert report["n_configs"] == 2
    assert report["N_common"] == int(expected.sum()) == 7
    assert report["common_origins"] == origin_idx[expected].tolist()
    # Each configuration's issued / abstained counts by type.
    assert report["configs"]["A"] == {"issued": 9, "abstained": 1, "by_type": {"FIT_NONCONVERGENCE": 1}}
    assert report["configs"]["B"] == {
        "issued": 8,
        "abstained": 2,
        "by_type": {"QUANTILE_CROSSING": 2},
    }
    # A third config shrinks the set further: the set is the intersection over
    # EVERY compared configuration (prereg §7), not a pairwise statistic.
    masks_c = dict(masks, C=np.array([1, 0, 1, 1, 1, 1, 1, 1, 1, 0], dtype=bool))
    common3 = stage1.intersection_of_issued(masks_c)
    assert stage1.comparison_set_report(origin_idx, masks_c, {**reasons, "C": np.full(10, None, dtype=object)})["N_common"] == int(
        (masks["A"] & masks["B"] & masks_c["C"]).sum()
    )
    assert common3.sum() == report["N_common"] - 2


# ── test 4: one bootstrap index draw shared across configurations ────────────


def test_bootstrap_shares_one_index_draw_across_configurations():
    N, n_draws = 40, 25
    matrix = stage1.bootstrap_index_matrix(N, h=5, pop=0, fam=0, variant=0, n_draws=n_draws)
    assert matrix.shape == (n_draws, N)  # n_draws rows of length N
    assert matrix.min() >= 0 and matrix.max() < N  # every index in [0, N)

    # Reproducible from SeedSequence([221011, h, pop, fam, var]) and a different
    # var (the L = h sensitivity rerun) changes it.
    np.testing.assert_array_equal(
        matrix, stage1.bootstrap_index_matrix(N, 5, 0, 0, 0, n_draws=n_draws)
    )
    assert not np.array_equal(matrix, stage1.bootstrap_index_matrix(N, 5, 0, 0, 1, n_draws=n_draws))

    # The frozen algorithm, row by row: starts then (start + arange(L)) % N.
    L = stage1.block_length(5, 0)
    assert L == max(21, 2 * 5) == 21
    rng = np.random.default_rng(np.random.SeedSequence([stage1.SEED_ROOT, 5, 0, 0, 0]))
    starts = rng.integers(0, N, size=math.ceil(N / L))
    want = ((starts[:, None] + np.arange(L)[None, :]) % N).reshape(-1)[:N]
    np.testing.assert_array_equal(matrix[0], want)

    # ONE matrix serves every configuration: the paired draw statistics read
    # every config's forecasts off the same rows.
    gen = np.random.default_rng(7)
    y = gen.random(N) < 0.3
    p = {
        "B0": np.full(N, 0.1),
        "M3-ALL": gen.random(N),
        "B1-20": gen.random(N),
    }
    stats = stage1.binary_draw_statistics(matrix, y, p, stage1.alpha_grid(5))
    row0 = matrix[0]
    assert stats["brier"]["M3-ALL"][0] == pytest.approx(float(np.mean((p["M3-ALL"][row0] - y[row0].astype(float)) ** 2)))
    assert stats["brier"]["B1-20"][0] == pytest.approx(float(np.mean((p["B1-20"][row0] - y[row0].astype(float)) ** 2)))
    # BSS is paired on the same row: 1 - Brier/Brier(B0) with B0 from row0.
    assert stats["bss"]["M3-ALL"][0] == pytest.approx(
        1.0 - stats["brier"]["M3-ALL"][0] / stats["brier"]["B0"][0]
    )


# ── recommended: negative-control shift is the half-length roll ───────────────


def test_negative_control_rolls_training_labels_by_half_length(monkeypatch):
    y = np.arange(10.0)
    np.testing.assert_allclose(stage1.negative_control_shift(y), np.roll(y, len(y) // 2))
    odd = np.arange(9.0)
    np.testing.assert_allclose(stage1.negative_control_shift(odd), np.roll(odd, 4))  # len // 2 floors
    # Deterministic, no seed: two calls are identical and it is a permutation.
    np.testing.assert_array_equal(stage1.negative_control_shift(y), stage1.negative_control_shift(y))
    assert sorted(stage1.negative_control_shift(y).tolist()) == y.tolist()

    # The negative-control refit path fits on the ROLLED labels/targets.
    captured = {}
    real = stage1.fit_logistic

    def spy(X, y_fit, C):
        captured["y"] = np.asarray(y_fit, copy=True)
        return real(X, y_fit, C)

    monkeypatch.setattr(stage1, "fit_logistic", spy)
    rng = np.random.default_rng(4)
    X_tr, X_te = rng.normal(size=(10, 3)), rng.normal(size=(4, 3))
    y_tr = (rng.random(10) < 0.4).astype(float)
    stage1.fit_shifted_binary_block(X_tr, y_tr, X_te)
    np.testing.assert_array_equal(captured["y"], stage1.negative_control_shift(y_tr))

    captured_q = {}
    real_q = stage1.fit_quantile_lp

    def spy_q(X, a_fit, tau):
        captured_q.setdefault("a", []).append(np.asarray(a_fit, copy=True))
        return real_q(X, a_fit, tau)

    monkeypatch.setattr(stage1, "fit_quantile_lp", spy_q)
    a_tr = np.abs(rng.normal(size=10)) * 0.05
    stage1.fit_shifted_quantile_block(X_tr, a_tr, X_te)
    rolled = stage1.negative_control_shift(a_tr)
    for seen in captured_q["a"]:
        np.testing.assert_array_equal(seen, rolled)


# ── recommended: an undefined draw takes the failing extreme ─────────────────


def test_undefined_statistic_draw_takes_failing_extreme():
    # One event origin (index 9); draw 0 repeats a non-event origin ten times,
    # draw 1 takes each origin once.
    y = np.zeros(10, dtype=bool)
    y[9] = True
    idx_matrix = np.vstack([np.zeros(10, dtype=int), np.arange(10)])
    p = {
        "B0": np.full(10, 0.1),
        "M3-ALL": np.linspace(0.05, 0.5, 10),
        "B1-20": np.full(10, 0.2),
    }
    stats = stage1.binary_draw_statistics(idx_matrix, y, p, stage1.alpha_grid(5))
    # Zero events on a draw: V and ΔV undefined -> -inf where the gate needs
    # them large... (BSS stays defined: its denominator Brier(B0) is nonzero
    # with zero events - only a zero denominator makes BSS undefined.)
    assert np.isneginf(stats["v"]["M3-ALL"]["b"][0])
    assert np.isneginf(stats["v"]["B1-20"]["b"][0])
    assert np.isneginf(stats["delta_v"][0])
    assert np.isfinite(stats["bss"]["M3-ALL"][0])
    # ...and WACE (no bin reaches n_b >= 100) undefined -> +inf where the gate
    # needs it small.
    assert np.isposinf(stats["wace"][0])
    assert np.isposinf(stats["wace"][1])  # N = 10 < 100 on every draw here
    # Draw 1 has one event: V and CITL are finite there.
    assert np.isfinite(stats["v"]["M3-ALL"]["b"][1])
    assert np.isfinite(stats["citl"][1])
    # Bounds come from np.quantile over the raw draws (never nanquantile); the
    # -inf draw drives the 0.05/12 lower bound to -inf.
    assert np.isneginf(stage1.gate_lower_bound(stats["delta_v"]))

    # BSS's own undefined case: a ZERO DENOMINATOR (Brier(B0) == 0 when the
    # constant B0 probability equals every draw label) -> -inf.
    y_all = np.ones(10, dtype=bool)
    p_perfect = {"B0": np.ones(10), "M3-ALL": np.linspace(0.1, 0.6, 10), "B1-20": np.full(10, 0.4)}
    stats_perfect = stage1.binary_draw_statistics(
        np.arange(10).reshape(1, 10), y_all, p_perfect, stage1.alpha_grid(5)
    )
    assert stats_perfect["brier"]["B0"][0] == pytest.approx(0.0)
    assert np.isneginf(stats_perfect["bss"]["M3-ALL"][0])
    assert np.isneginf(stats_perfect["v"]["M3-ALL"]["b"][0])  # s = 1 -> V undefined too

    # Quantile side: a zero reference pinball loss makes the skill undefined
    # -> -inf for its gate.
    a = np.linspace(0.0, 0.1, 10)
    q_exact = {"0.5": a.copy(), "0.8": a.copy(), "0.9": a.copy()}  # zero loss at every tau
    q_flat = {k: np.full(10, v) for k, v in (("0.5", 0.02), ("0.8", 0.04), ("0.9", 0.06))}
    q_configs = {"Q0": q_exact, "Q1": q_flat, "Q3-ALL": q_flat}
    qstats = stage1.quantile_draw_statistics(np.arange(10).reshape(1, 10), a, q_configs)
    assert qstats["pl_sum"]["Q0"][0] == pytest.approx(0.0)  # exact predictions -> zero loss
    assert np.isneginf(qstats["skill"][0])


# ── recommended: logistic objective/gradient consistency ─────────────────────


def test_logistic_objective_gradient_matches_finite_differences():
    rng = np.random.default_rng(3)
    n, p = 60, 4
    X = np.column_stack([np.ones(n), rng.normal(size=(n, p - 1))])
    y = (rng.random(n) < 0.3).astype(float)
    for C in (stage1.C_MAIN, stage1.C_SENS):
        beta = rng.normal(size=p)
        val, grad = stage1.logistic_objective_and_gradient(beta, X, y, C)
        assert np.isfinite(val)
        eps = 1e-6
        num = np.empty(p)
        for j in range(p):
            up, dn = beta.copy(), beta.copy()
            up[j] += eps
            dn[j] -= eps
            num[j] = (
                stage1.logistic_objective_and_gradient(up, X, y, C)[0]
                - stage1.logistic_objective_and_gradient(dn, X, y, C)[0]
            ) / (2 * eps)
        np.testing.assert_allclose(grad, num, rtol=1e-5, atol=1e-6)


# ── prereg SS12 deviation INC_LABEL_INDEX: native-label alignment ───────────


def _synthetic_spy_with_drop() -> pd.Series:
    """Business-day SPY-like closes with one 6 % drop on day 30 (synthetic)."""
    idx = pd.bdate_range("2024-01-01", periods=60)
    px = np.full(60, 100.0)
    px[30:] = 94.0
    return pd.Series(px, index=idx)


def test_native_event_on_dates_aligns_index_labels():
    # The real producer: date is the INDEX, never a column.
    from scripts.research.risk_radar_state_ladder_calibration import native_forward_labels

    spy = _synthetic_spy_with_drop()
    dates = pd.DatetimeIndex(
        [spy.index[20], spy.index[25], spy.index[29], spy.index[40], spy.index[57], pd.Timestamp("2023-12-29")]
    )
    labels = native_forward_labels(spy, dates, 5, 0.05)
    assert "date" not in labels.columns and labels.index.name == "date"
    # The first W3 execution's idiom raised exactly this KeyError.
    with pytest.raises(KeyError):
        labels.drop_duplicates(subset="date")

    y = stage1.native_event_on_dates(labels, dates)
    assert y.dtype == float and y.shape == (len(dates),)
    # day 20: window 21..25 stays at 100 -> no event; day 25: window 26..30
    # reaches the 94 close -> event; day 29: next close is 94 -> event;
    # day 40: flat at 94 -> no event; day 57: incomplete window -> NaN;
    # a date outside the series -> NaN.
    np.testing.assert_array_equal(y[:4], [0.0, 1.0, 1.0, 0.0])
    assert np.isnan(y[4]) and np.isnan(y[5])


def test_native_event_on_dates_keeps_first_duplicate_and_handles_empty():
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    dup = pd.DataFrame(
        {"end": dates[[0, 0, 1]], "loss": [-0.06, 0.0, 0.0], "event": [True, False, False]},
        index=pd.DatetimeIndex(dates[[0, 0, 1]], name="date"),
    )
    np.testing.assert_array_equal(stage1.native_event_on_dates(dup, dates), [1.0, 0.0])
    empty = pd.DataFrame(columns=["end", "loss", "event"])
    assert np.isnan(stage1.native_event_on_dates(empty, dates)).all()


def test_run_inc_types_a_code_defect_apart_from_an_absent_source(monkeypatch):
    def raise_key(*_a, **_k):
        raise KeyError("date")

    def raise_import(*_a, **_k):
        raise ImportError("no module")

    monkeypatch.setattr(stage1, "_git", raise_key)
    assert stage1.run_inc({}, pd.Series(dtype=float))["blocked"] == "INC_REPLAY_ERROR"
    monkeypatch.setattr(stage1, "_git", raise_import)
    assert stage1.run_inc({}, pd.Series(dtype=float))["blocked"] == "INC_SOURCE_UNAVAILABLE"


def test_rerun_of_refuses_to_overwrite_the_original_output():
    # SS12: the original output is kept - a rerun may never target the default directory.
    with pytest.raises(SystemExit):
        stage1.main(["--rerun-of", "dd67262e7ab8", "--rerun-defect", "x", "--dry-run"])
    with pytest.raises(SystemExit):
        stage1.main(["--rerun-of", "dd67262e7ab8", "--out-dir", "research/grey_deer/rerun", "--dry-run"])


# ── red-team repairs RT-01 / RT-02 / RT-04 / RT-05 (synthetic only) ──────────


def _labels_frame(n_rows: int) -> dict:
    y = np.zeros(n_rows, dtype=float)
    y[::7] = 1.0
    a = np.full(n_rows, 0.01)
    a[::7] = 0.08
    return {h: {"Y": pd.Series(y), "A": pd.Series(a)} for h in stage1.HORIZONS}


def _one_block_fits(n_rows: int, *, abstain_m3_first_at_h5: bool) -> dict:
    """One contiguous block per horizon. h=5 can abstain M3-ALL at origin 0."""
    fits: dict = {}
    configs = stage1.BINARY_CLAIM_CONFIGS + stage1.QUANTILE_CLAIM_CONFIGS + (stage1.SENSITIVITY_CONFIG,)
    for h in stage1.HORIZONS:
        origin_idx = stage1.evaluation_origin_indices(n_rows, h)
        s0, e0 = int(origin_idx[0]), int(origin_idx[-1])
        n = e0 - s0 + 1
        assert n == len(origin_idx)  # the fold union is one contiguous span
        for cid in configs:
            kind = "quantile" if cid in stage1.QUANTILE_CLAIM_CONFIGS else "binary"
            issued = np.ones(n, dtype=bool)
            reasons = np.full(n, None, dtype=object)
            if abstain_m3_first_at_h5 and h == 5 and cid == "M3-ALL":
                issued[0] = False
                reasons[0] = "FIT_NONCONVERGENCE"
            rec: dict = {"kind": kind, "block": [s0, e0], "issued": issued, "reasons": reasons}
            if kind == "binary":
                if cid == "B0":
                    rec["p"] = np.full(n, 0.05)
                elif cid == stage1.SENSITIVITY_CONFIG:
                    rec["p"] = np.linspace(0.03, 0.35, n)
                else:
                    rec["p"] = np.linspace(0.02, 0.40, n)
            else:
                rec["q"] = {"0.5": np.full(n, 0.01), "0.8": np.full(n, 0.03), "0.9": np.full(n, 0.05)}
            fits[(h, 1, cid)] = rec
    return {"fits": fits}


def _point_metrics_on(fits: dict, n_rows: int):
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2021-07-06", periods=n_rows)]
    rv20 = np.linspace(0.08, 0.30, n_rows)
    comp = stage1.build_comparison_sets(fits, n_rows, _labels_frame(n_rows))
    report = stage1.compute_point_metrics(comp, n_rows, rv20, dates)
    return comp, report


def test_rt01_sensitivity_row_survives_binary_abstention():
    """M3-ALL abstains origin 0 at h=5; M3-ALL-C0.1 issues. The row must return."""
    n_rows = 400
    comp, report = _point_metrics_on(_one_block_fits(n_rows, abstain_m3_first_at_h5=True), n_rows)
    cell = comp[5]["binary"]
    n_eval = len(cell["eval_origin_idx"])
    n_common = len(cell["origin_idx"])
    assert n_eval == 80
    assert n_common == 79
    assert len(cell["sensitivity"]["mask"]) == n_common
    assert len(cell["sensitivity"]["p"]) == n_common
    # The pre-fix mask lived at evaluation length and does not index y.
    common = np.ones(n_eval, dtype=bool)
    common[0] = False
    old_mask = common & np.ones(n_eval, dtype=bool)
    assert len(old_mask) != len(cell["y"])
    with pytest.raises(IndexError):
        cell["y"][old_mask]

    sens = report[5]["binary"]["sensitivity"]
    c01_issued_on_comparison = int(cell["sensitivity"]["mask"].sum())
    assert sens["n"] == c01_issued_on_comparison == n_common
    assert sens["metrics"]["n"] == n_common


def test_rt01_no_abstention_sensitivity_matches_pre_fix_indexing():
    """Where lengths agree, the sensitivity metrics match the old indexing."""
    n_rows = 400
    _comp, report = _point_metrics_on(_one_block_fits(n_rows, abstain_m3_first_at_h5=False), n_rows)
    h = 5
    origin_idx = stage1.evaluation_origin_indices(n_rows, h)
    n_eval = len(origin_idx)
    common = np.ones(n_eval, dtype=bool)
    sens_issued = np.ones(n_eval, dtype=bool)
    sens_p = np.linspace(0.03, 0.35, n_eval)
    p_b0 = np.full(n_eval, 0.05)
    y_full = np.zeros(n_rows, dtype=float)
    y_full[::7] = 1.0
    y_eval = np.isfinite(y_full[origin_idx]) & (y_full[origin_idx] > 0)
    old_mask = common & sens_issued
    expected = stage1.binary_metric_set(
        sens_p[old_mask],
        y_eval[common][old_mask],
        p0=p_b0[common][old_mask],
        alphas=stage1.alpha_grid(h),
    )
    got = report[h]["binary"]["sensitivity"]["metrics"]
    assert json.dumps(got, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert got["n"] == n_eval


def _inc_cells(drop_first: bool) -> tuple[pd.Series, dict]:
    n = 80
    index = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(np.full(n, 100.0), index=index)
    eval_idx = np.arange(0, 30)

    def cell_for() -> dict:
        mask = np.ones(len(eval_idx), dtype=bool)
        if drop_first:
            mask[0] = False
        kept = eval_idx[mask]
        return {
            "eval_origin_idx": eval_idx.copy(),
            "origin_idx": kept.copy(),
            "y": np.zeros(len(kept), dtype=bool),
            "a": np.zeros(len(kept), dtype=float),
            "episodes": [],
        }

    return close, {h: {"binary": cell_for()} for h in stage1.HORIZONS}


def test_rt02_inc_evaluation_origins_follow_the_union(monkeypatch):
    """Binary abstention splits the two counts; no abstention leaves them equal."""

    def _run(drop_first: bool) -> dict:
        close, comp = _inc_cells(drop_first)

        def fake_inputs(_deviations=None):
            return {
                "audit_script_blob": "synthetic",
                "calibration_blob_sha": "synthetic",
                "spy": close,
                "probability_for_h": lambda _h: pd.Series(0.2, index=close.index),
            }

        monkeypatch.setattr(stage1, "_inc_replay_inputs", fake_inputs)
        table = stage1.run_inc(comp, close, deviations=[])
        assert "blocked" not in table, table
        return table

    abstained = _run(True)
    clean = _run(False)
    for h in stage1.HORIZONS:
        row_a = abstained["horizons"][f"h{h}"]
        row_c = clean["horizons"][f"h{h}"]
        assert row_a["evaluation_origins"] == 30
        assert row_a["comparison_set_origins"] == 29
        assert row_a["evaluation_origins"] > row_a["comparison_set_origins"]
        # Native-label metrics use the union INC covers, not the comparison set.
        assert row_a["metrics_vs_native_label"]["n"] == row_a["evaluation_origins"]
        # Early warning stays on the comparison set.
        outside = row_a["early_warning_vs_protocol_episodes"]["false_alarm_time"]["sessions_outside_every_episode"]
        assert outside == row_a["comparison_set_origins"]
        assert row_c["evaluation_origins"] == row_c["comparison_set_origins"] == 30
        assert row_c["metrics_vs_native_label"]["n"] == 30
        assert (
            row_c["early_warning_vs_protocol_episodes"]["false_alarm_time"]["sessions_outside_every_episode"] == 30
        )


def _canned_identities() -> dict:
    return {
        "schema": stage1.SCHEMA,
        "prereg": {
            "path": stage1.PREREG_PATH,
            "blob_sha": stage1.PREREG_BLOB,
            "sha256": stage1.PREREG_SHA256,
        },
        "manifest": {
            "path": stage1.MANIFEST_PATH,
            "blob_sha": stage1.MANIFEST_BLOB,
            "version": stage1.MANIFEST_VERSION,
        },
        "run": {
            "utc": "canned",
            "commit_sha": "canned-commit",
            "script_blob_sha": "canned-script",
            "test_blob_sha": "canned-test",
        },
    }


def _provenance_from_markdown(text: str) -> dict:
    found = {}
    for line in text.splitlines():
        if not line.startswith("- ") or ": `" not in line:
            continue
        key, rest = line[2:].split(": `", 1)
        if key in stage1.PROVENANCE_KEYS and rest.endswith("`"):
            found[key] = rest[:-1]
    return found


def _assert_six_provenance(directory: Path, expected: dict) -> dict:
    payload = json.loads((directory / stage1.RESULTS_JSON_NAME).read_text(encoding="utf-8"))
    prov = payload["provenance"]
    assert set(prov) == set(stage1.PROVENANCE_KEYS)
    for key in stage1.PROVENANCE_KEYS:
        assert isinstance(prov[key], str) and prov[key] == expected[key]
    assert payload["manifest"]["version"] == prov["manifest_version"]
    assert payload["sample"]["subframe_content_sha256"] == prov["subframe_content_sha256"]
    assert payload["prereg"]["blob_sha"] == prov["prereg_git_blob"]
    assert payload["run"]["commit_sha"] == prov["commit_sha"]
    assert payload["run"]["script_blob_sha"] == prov["script_blob_sha"]
    assert payload["run"]["test_blob_sha"] == prov["test_blob_sha"]
    note = (directory / stage1.RESULTS_MD_NAME).read_text(encoding="utf-8")
    assert _provenance_from_markdown(note) == expected
    return payload


def test_rt04_both_artifacts_carry_six_provenance_fields(tmp_path, monkeypatch):
    """A synthetic main() run and the BLOCKED path both write all six fields."""
    canned = _canned_identities()
    monkeypatch.setattr(stage1, "verify_identities", lambda **_kwargs: {
        "schema": canned["schema"],
        "prereg": dict(canned["prereg"]),
        "manifest": dict(canned["manifest"]),
        "run": dict(canned["run"]),
    })
    monkeypatch.setattr(stage1, "trial_ledger_scope", lambda: nullcontext())
    monkeypatch.setattr(stage1.trial_ledger, "register_trials", _raise_assertion)
    monkeypatch.setattr(stage1.subprocess, "run", _raise_assertion)
    stub = types.ModuleType("collectors.massive_stock_day")
    stub.load_ticker = lambda *_a, **_k: pd.DataFrame({"date": ["2024-01-02"], "close": [100.0]})
    monkeypatch.setitem(sys.modules, "collectors.massive_stock_day", stub)

    subframe = "ab" * 32
    sample_info = {
        "subframe_content_sha256": subframe,
        "rows": 2,
        "first_date": "2024-01-02",
        "last_date": "2024-01-03",
        "pre_window_rows_dropped": 0,
    }
    window = pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "close": [100.0, 101.0]})
    monkeypatch.setattr(stage1, "sample_identity", lambda _df: (dict(sample_info), window.copy()))
    monkeypatch.setattr(stage1, "integrity_checks", lambda _window: [])
    monkeypatch.setattr(stage1, "build_labels", lambda _close: {})
    monkeypatch.setattr(stage1, "build_features", lambda _close: pd.DataFrame())
    monkeypatch.setattr(stage1, "run_fits", lambda *_a, **_k: {})

    def fake_eval(*, out_dir, identities, sample_info, **_rest):
        payload = {
            "schema": stage1.SCHEMA,
            "prereg": identities["prereg"],
            "manifest": identities["manifest"],
            "run": identities["run"],
            "sample": dict(sample_info),
            "trial_budget": {
                "family": stage1.TRIAL_FAMILY,
                "budget": stage1.TRIAL_BUDGET,
                "basis": "itemized",
            },
            "gates": [],
            "episodes": {},
            "comparison_sets": {},
            "negative_control": {},
            "inc": {"blocked": "INC_SOURCE_UNAVAILABLE", "detail": "synthetic"},
            "deviations": [],
            "blocked": [],
        }
        stage1.write_artifacts(Path(out_dir), payload)

    monkeypatch.setattr(stage1, "evaluate_and_write", fake_eval)

    known = {
        "manifest_version": stage1.MANIFEST_VERSION,
        "subframe_content_sha256": subframe,
        "prereg_git_blob": stage1.PREREG_BLOB,
        "commit_sha": "canned-commit",
        "script_blob_sha": "canned-script",
        "test_blob_sha": "canned-test",
    }
    ok_dir = tmp_path / "ok"
    assert stage1.main(["--skip-hydrate", "--out-dir", str(ok_dir)]) == 0
    _assert_six_provenance(ok_dir, known)

    stub.load_ticker = lambda *_a, **_k: pd.DataFrame()
    blocked_dir = tmp_path / "blocked"
    assert stage1.main(["--skip-hydrate", "--out-dir", str(blocked_dir)]) == 2
    blocked = json.loads((blocked_dir / stage1.RESULTS_JSON_NAME).read_text(encoding="utf-8"))
    assert blocked["blocked"][0]["type"] == "SOURCE_UNREADABLE"
    unknown_subframe = blocked["provenance"]["subframe_content_sha256"]
    assert unknown_subframe.startswith("UNKNOWN:")
    blocked_expected = dict(known)
    blocked_expected["subframe_content_sha256"] = unknown_subframe
    _assert_six_provenance(blocked_dir, blocked_expected)

    def boom(**_kwargs):
        raise stage1.Blocked("PREREG_IDENTITY_MISMATCH", "synthetic refusal before identity")

    monkeypatch.setattr(stage1, "verify_identities", boom)
    early_dir = tmp_path / "early"
    assert stage1.main(["--out-dir", str(early_dir)]) == 2
    early = json.loads((early_dir / stage1.RESULTS_JSON_NAME).read_text(encoding="utf-8"))
    assert early["blocked"][0]["type"] == "PREREG_IDENTITY_MISMATCH"
    early_expected = {key: early["provenance"][key] for key in stage1.PROVENANCE_KEYS}
    assert all(value.startswith("UNKNOWN:") for value in early_expected.values())
    _assert_six_provenance(early_dir, early_expected)


def test_rt05_census_typed_exclusions_keep_existing_keys():
    rows = stage1.census_populations(1321, 3)
    assert len(rows) == len(stage1.HORIZONS) * 2
    typed_keys = {"PRE_ENTITLEMENT", "WARMUP", "IMMATURE", "TRAINING_FOLD_THIN"}
    old_keys = ("population", "horizon", "pre_entitlement", "warmup", "immature", "eligible")
    for row in rows:
        assert set(row["typed_exclusions"]) == typed_keys
        for key in typed_keys:
            assert type(row["typed_exclusions"][key]) is int
        assert row["typed_exclusions"]["TRAINING_FOLD_THIN"] == 0
        assert row["pre_entitlement"] == 3 == row["typed_exclusions"]["PRE_ENTITLEMENT"]
        assert row["warmup"] == row["typed_exclusions"]["WARMUP"]
        assert row["immature"] == row["typed_exclusions"]["IMMATURE"]
        for key in old_keys:
            assert key in row
    assert {row["population"] for row in rows} == {"P-all", "P-active"}
    assert all(row["blocked"] == "OBSERVER_NOT_ON_MAIN" for row in rows if row["population"] == "P-active")

    fits = {
        "blocks": {
            "h5/b1": {"thin": True},
            "h5/b2": {"thin": False},
            "h10/b1": {"thin": True},
            "h21/b4": {"thin": True},
        }
    }
    merged = stage1.merge_training_fold_thin(rows, fits)
    # The same count as summing len(folds[h]["thin_blocks"]) over horizons.
    thin_total = sum(1 for value in fits["blocks"].values() if value.get("thin"))
    assert thin_total == 3
    for row in merged:
        assert row["typed_exclusions"]["TRAINING_FOLD_THIN"] == thin_total
        assert row["pre_entitlement"] == 3
        assert set(row["typed_exclusions"]) == typed_keys
