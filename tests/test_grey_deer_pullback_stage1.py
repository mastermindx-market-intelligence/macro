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
