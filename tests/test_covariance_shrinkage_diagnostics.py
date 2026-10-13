from __future__ import annotations

# Hermetic tests for engine/covariance_shrinkage_diagnostics.py (Q08).
#
# Synthetic data only (integer indexes, fixed seeds). No repository file is
# opened, walked or globbed.

import importlib
import inspect
import sys

import numpy as np
import pytest

import engine.covariance_shrinkage_diagnostics as csd

LS = "long_short"


def _specs(names, basis=LS, unit="decimal_return", clock="daily_close"):
    return {n: csd.SeriesSpec(n, basis, unit, clock) for n in names}


def _panel(X, names=None):
    names = names or [f"f{j}" for j in range(X.shape[1])]
    return {n: list(X[:, j]) for j, n in enumerate(names)}, names


def _equicorr_sample(n, p, rho, seed):
    rng = np.random.default_rng(seed)
    common = rng.standard_normal((n, 1))
    idio = rng.standard_normal((n, p))
    return math_sqrt(rho) * common + math_sqrt(1 - rho) * idio


def math_sqrt(x):
    return float(np.sqrt(x))


# ---------------------------------------------------------------------------
# req1 — incompatible return definitions cannot silently share one matrix
# ---------------------------------------------------------------------------


def test_req1_incompatible_basis_unit_clock_are_refused_without_a_matrix():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((120, 3)) * 0.01
    values, names = _panel(X, ["size", "value", "quality"])

    mixed_basis = _specs(names)
    mixed_basis["value"] = csd.SeriesSpec("value", "long_only", "decimal_return", "daily_close")
    out = csd.estimate(values, mixed_basis, bootstrap_B=10)
    assert out["status"] == "unavailable"
    assert out["reason"].startswith("incompatible_basis")
    assert "correlation" not in out and "participation_ratio" not in out

    mixed_unit = _specs(names)
    mixed_unit["size"] = csd.SeriesSpec("size", LS, "percent_return", "daily_close")
    assert csd.estimate(values, mixed_unit, bootstrap_B=10)["reason"].startswith("incompatible_unit")

    mixed_clock = _specs(names)
    mixed_clock["quality"] = csd.SeriesSpec("quality", LS, "decimal_return", "month_end")
    assert csd.estimate(values, mixed_clock, bootstrap_B=10)["reason"].startswith("incompatible_clock")

    unknown = _specs(names, basis="spread_or_long")
    assert csd.check_compatible(list(unknown.values()))["reason"].startswith("unknown_basis")

    ok = csd.estimate(values, _specs(names), bootstrap_B=10)
    assert ok["status"] == "ok" and ok["basis"] == LS


def test_req1_spec_columns_must_match_value_columns():
    X = np.random.default_rng(2).standard_normal((80, 2))
    values, names = _panel(X)
    out = csd.prepare_panel(values, _specs(names + ["extra"]))
    assert out == {**out, "status": "unavailable", "reason": "spec_columns_mismatch"}


# ---------------------------------------------------------------------------
# req2 — symmetric / PSD at tolerance; valid zero covariance retained
# ---------------------------------------------------------------------------


def test_req2_every_estimator_is_symmetric_psd_with_unit_diagonal():
    rng = np.random.default_rng(3)
    X = _equicorr_sample(150, 6, 0.4, 3) + 0.0 * rng.standard_normal((150, 6))
    for name, fn in csd.ESTIMATORS.items():
        R, meta = fn(X)
        v = csd.matrix_validity(R)
        assert v["symmetric"] and v["psd"], name
        assert np.allclose(np.diag(R), 1.0), name
        assert np.all(np.abs(R) <= 1.0 + 1e-12), name


def test_req2_exact_zero_covariance_is_retained_by_zero_preserving_estimators():
    # Columns built from +-1 Walsh patterns are exactly orthogonal after demeaning.
    n = 64
    t = np.arange(n)
    a = np.where((t // 1) % 2 == 0, 1.0, -1.0)
    b = np.where((t // 2) % 2 == 0, 1.0, -1.0)
    c = np.where((t // 4) % 2 == 0, 1.0, -1.0)
    d = 0.6 * c + 0.8 * np.where((t // 8) % 2 == 0, 1.0, -1.0)
    X = np.column_stack([a, b, c, d])
    mask = csd.exact_zero_mask(X)
    assert mask[0, 1] and mask[0, 2] and mask[1, 3]
    assert not mask[2, 3]
    for name, fn in csd.ESTIMATORS.items():
        R, meta = fn(X)
        if meta["preserves_zero_structure"]:
            assert np.all(R[mask] == 0.0), name
        assert csd.matrix_validity(R)["psd"], name
    # The constant-correlation target declares that it does not preserve zeros.
    _, meta_cc = csd.constant_correlation_shrinkage(X)
    assert meta_cc["preserves_zero_structure"] is False


def test_req2_matrix_validity_flags_asymmetric_and_indefinite_matrices():
    bad = np.array([[1.0, 0.9, 0.9], [0.9, 1.0, -0.9], [0.9, -0.9, 1.0]])
    v = csd.matrix_validity(bad)
    assert v["symmetric"] and not v["psd"]
    asym = np.array([[1.0, 0.2], [0.1, 1.0]])
    assert not csd.matrix_validity(asym)["symmetric"]
    assert not csd.matrix_validity(np.array([[1.0, np.nan], [np.nan, 1.0]]))["psd"]


# ---------------------------------------------------------------------------
# req3 — sensible uncertainty, no impossible participation ratio
# ---------------------------------------------------------------------------


def test_req3_known_structures_give_expected_participation_ratio():
    p = 8
    assert csd.participation_ratio(np.eye(p)) == pytest.approx(p)
    ones = np.ones((p, p))
    assert csd.participation_ratio(ones) == pytest.approx(1.0)
    rho = 0.5
    eq = np.full((p, p), rho)
    np.fill_diagonal(eq, 1.0)
    assert csd.participation_ratio(eq) == pytest.approx(p / (1 + (p - 1) * rho**2))


def test_req3_incoherent_pairwise_matrix_yields_no_participation_ratio():
    bad = np.array([[1.0, 0.9, 0.9], [0.9, 1.0, -0.9], [0.9, -0.9, 1.0]])
    assert csd.participation_ratio(bad) is None
    assert csd.dominant_share(bad) is None


def test_req3_bootstrap_interval_is_bounded_and_covers_population_value():
    p, rho = 5, 0.3
    true_pr = p / (1 + (p - 1) * rho**2)
    X = _equicorr_sample(400, p, rho, 11)
    for name in csd.ESTIMATORS:
        iv = csd.bootstrap_pr_interval(X, name, B=150, mean_block=8, seed=5, level=0.95)
        assert iv["n_valid"] > 100, name
        assert 1.0 <= iv["lo"] <= iv["hi"] <= p, name
        assert iv["lo"] <= true_pr <= iv["hi"], name
    # Narrower sample -> wider interval for the same structure.
    wide = csd.bootstrap_pr_interval(X[:80], "sample", B=150, mean_block=8, seed=5, level=0.95)
    narrow = csd.bootstrap_pr_interval(X, "sample", B=150, mean_block=8, seed=5, level=0.95)
    assert wide["width"] > narrow["width"]


def test_req3_identity_and_one_factor_samples_land_near_the_extremes():
    rng = np.random.default_rng(13)
    p = 6
    iid = rng.standard_normal((500, p))
    one = rng.standard_normal((500, 1)) + 0.05 * rng.standard_normal((500, p))
    for name, fn in csd.ESTIMATORS.items():
        pr_iid = csd.participation_ratio(fn(iid)[0])
        pr_one = csd.participation_ratio(fn(one)[0])
        assert 1.0 <= pr_one < 1.1, name
        assert p * 0.9 < pr_iid <= p, name


def test_req3_participation_ratio_never_leaves_one_to_n_on_random_inputs():
    # participation_ratio() clamps to [1, N], so asserting bounds on its return
    # value alone could never fail. This test recomputes the RAW, unclamped PR
    # from the eigenvalues (no clip, no clamp), requires the estimator output to
    # be PSD, requires the raw PR itself to lie in [1, N] within a tiny
    # numerical tolerance, and requires the clamp to have been a no-op.
    rng = np.random.default_rng(17)
    tol = 1e-9
    for trial in range(40):
        p = int(rng.integers(2, 9))
        n = int(rng.integers(p + 3, 60))
        X = rng.standard_normal((n, p)) @ rng.standard_normal((p, p))
        for name, fn in csd.ESTIMATORS.items():
            R, _ = fn(X)
            eig = np.linalg.eigvalsh((R + R.T) / 2.0)
            assert eig.min() >= -1e-10, (trial, name, float(eig.min()))
            raw = float(eig.sum()) ** 2 / float(np.sum(eig**2))
            assert 1.0 - tol <= raw <= p + tol, (trial, name, raw)
            pr = csd.participation_ratio(R)
            assert pr is not None, (trial, name)
            assert abs(pr - raw) <= tol, (trial, name, pr, raw)


# ---------------------------------------------------------------------------
# req4 — constant columns and inadequate support give unavailable estimates
# ---------------------------------------------------------------------------


def test_req4_constant_column_is_unavailable_not_an_exception():
    rng = np.random.default_rng(19)
    X = rng.standard_normal((120, 3))
    X[:, 1] = 0.0025
    values, names = _panel(X, ["a", "b", "c"])
    out = csd.estimate(values, _specs(names), bootstrap_B=10)
    assert out["status"] == "unavailable"
    assert out["reason"] == "constant_column:b"


def test_req4_short_or_gappy_support_is_unavailable_with_attrition():
    rng = np.random.default_rng(23)
    X = rng.standard_normal((100, 3))
    values, names = _panel(X)
    short = {k: v[:30] for k, v in values.items()}
    out = csd.estimate(short, _specs(names), bootstrap_B=10)
    assert out["status"] == "unavailable" and out["reason"].startswith("insufficient_support")
    gappy = {k: list(v) for k, v in values.items()}
    for i in range(0, 100, 2):
        gappy[names[0]][i] = None
    out2 = csd.estimate(gappy, _specs(names), min_obs=60, bootstrap_B=10)
    assert out2["status"] == "unavailable"
    assert out2["attrition"]["rows_complete"] == 50
    assert out2["attrition"]["missing_by_column"][names[0]] == 50
    assert csd.estimate({}, {}, bootstrap_B=10)["status"] == "unavailable"
    one = {names[0]: values[names[0]]}
    assert csd.estimate(one, _specs([names[0]]), bootstrap_B=10)["status"] == "unavailable"


def test_req4_rolling_losses_mark_unsupported_blocks_unavailable():
    rng = np.random.default_rng(29)
    X = rng.standard_normal((120, 3))
    X[100:110, 2] = 0.0  # constant inside one evaluation block
    rows = csd.rolling_origin_losses(X, train=60, horizon=10)
    statuses = [r["sample"]["status"] for r in rows]
    assert "unavailable" in statuses and "ok" in statuses
    hit = [r for r in rows if r["eval_rows"][0] == 100][0]
    assert hit["lw_identity"]["reason"] == "eval_block_unsupported"


# ---------------------------------------------------------------------------
# req5 — held-out loss and bootstrap stability vs the original estimator
# ---------------------------------------------------------------------------


def test_req5_shrinkage_beats_sample_on_held_out_loss_when_n_over_t_is_large():
    p, rho = 20, 0.3
    X = _equicorr_sample(30 + 30 * 12, p, rho, 31)
    rows = csd.rolling_origin_losses(X, train=30, horizon=30)
    base = np.array([r["sample"]["stein"] for r in rows])
    for name in ("lw_identity", "lw_constant_corr"):
        ch = np.array([r[name]["stein"] for r in rows])
        d = base - ch
        assert d.mean() > 0, name
        ci = csd.block_bootstrap_mean_ci(d, block_len=2, B=2000, seed=1, level=0.95)
        assert ci["lo"] > 0, name
        assert ci["n_blocks_honest"] == len(rows)


def test_req5_baseline_matches_incumbent_formula_replica():
    X = _equicorr_sample(252, 4, 0.2, 37)
    R, _ = csd.sample_correlation(X)
    inc = csd.incumbent_algorithm_pr(X)
    assert round(csd.participation_ratio(R), 4) == inc["effective_factor_bets_pr"]
    assert round(csd.dominant_share(R), 4) == inc["dominant_factor_pc_share"]


def test_req5_bootstrap_stability_is_reported_for_baseline_and_challengers():
    # Stability is REPORTED for every estimator on identical resamples; its direction
    # is an empirical question (shrinkage intensity is itself re-estimated per
    # resample and can widen the PR interval), so no ordering is asserted here.
    X = _equicorr_sample(60, 10, 0.3, 41)
    ivs = {
        name: csd.bootstrap_pr_interval(X, name, B=120, mean_block=5, seed=2)
        for name in csd.ESTIMATORS
    }
    for name, iv in ivs.items():
        assert iv["width"] is not None and iv["width"] >= 0, name
        assert iv["n_valid"] + iv["n_failed"] == iv["B"], name
        assert 1.0 <= iv["lo"] <= iv["hi"] <= 10.0, name
    # Same seed => same resample sequence => reproducible.
    again = csd.bootstrap_pr_interval(X, "sample", B=120, mean_block=5, seed=2)
    assert again["width"] == ivs["sample"]["width"]


def test_req5_mean_ci_refuses_too_few_blocks():
    out = csd.block_bootstrap_mean_ci([0.1, 0.2, 0.3], block_len=3, B=100)
    assert out["status"] == "insufficient_support" and out["lo"] is None


# ---------------------------------------------------------------------------
# req6 — no new risk/gate/rank/sizing authority; frozen PSS-CD1 untouched
# ---------------------------------------------------------------------------


def test_req6_output_is_context_only_and_never_an_integer_bet_count():
    X = _equicorr_sample(200, 4, 0.3, 43)
    values, names = _panel(X)
    out = csd.estimate(values, _specs(names), bootstrap_B=50)
    assert out["authority"] == "context"
    assert set(out["not_for"]) >= {"risk", "gate", "rank", "sizing"}
    pr = out["participation_ratio"]
    assert isinstance(pr["point"], float) and not isinstance(pr["point"], int)
    assert pr["lo"] is not None and pr["hi"] is not None
    assert pr["bounds"] == [1.0, 4.0]
    for key in out:
        low = key.lower()
        assert not any(w in low for w in ("weight", "size_", "gate", "rank", "score", "alloc"))


def test_req6_module_exposes_no_authority_surfaces_and_no_pss_cd1_reference():
    public = [n for n in dir(csd) if not n.startswith("_")]
    for n in public:
        low = n.lower()
        assert not any(w in low for w in ("gate", "rank", "sizing", "allocate", "promote", "register"))
    src = inspect.getsource(csd)
    assert "personality_crowding_hazard" not in src
    assert "import engine" not in src and "from engine" not in src


# ---------------------------------------------------------------------------
# no silent activation — the module's own contract
# ---------------------------------------------------------------------------


def test_no_silent_activation_contract():
    assert csd.RESEARCH_ONLY is True
    assert csd.AUTHORITY == "context"
    assert csd.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    before = set(sys.modules)
    mod = importlib.reload(csd)
    added = set(sys.modules) - before
    assert not any(m.startswith("engine.") and m != mod.__name__ for m in added)
    src = inspect.getsource(mod)
    # Clock names are assembled so this file itself never spells a wall-clock call.
    clocks = ("datetime" + ".now", "time" + ".time", "date" + ".today")
    for banned in ("open(", "Path(", "requests", "urllib", "subprocess", "os.environ",
                   "logging") + clocks:
        assert banned not in src, banned
