from __future__ import annotations

"""Q17 stable factor whitening — hermetic synthetic tests named after the six
acceptance requirements. No network, no repo data, no wall clock."""

import copy
import types

import numpy as np
import pandas as pd

import engine.factor_stable_whitening as fsw


def _frame(n: int = 400, seed: int = 0, dup_eps: float | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=n)
    a = latent + 0.5 * rng.normal(size=n)
    b = (a + dup_eps * rng.normal(size=n)) if dup_eps is not None else latent + 0.6 * rng.normal(size=n)
    return pd.DataFrame({
        "a": a,
        "b": b,
        "c": latent + 0.8 * rng.normal(size=n),
        "d": rng.normal(size=n),
    })


def _cholesky_whiten(Z: np.ndarray) -> np.ndarray:
    C = np.corrcoef(Z, rowvar=False)
    L = np.linalg.cholesky(C)
    return np.linalg.solve(L, Z.T).T


# ---------------------------------------------------------------- requirement 1
def test_req1_near_duplicate_columns_bounded_amplification_and_flagged_unstable():
    F = _frame(dup_eps=1e-4)
    res = fsw.stable_whiten(F)
    d = res.diagnostics
    # the raw estimate is near-singular: the incumbent floor would amplify ~1000x
    assert d["raw_min_eig"] < 1e-6
    assert d["incumbent_floor_amplification"] > 100.0
    # the challenger bounds amplification and flags the state
    assert d["unstable"] is True
    assert res.status == fsw.STATUS_REGULARIZED
    assert d["applied_max_amplification"] <= fsw.MAX_AMPLIFICATION + 1e-9
    assert np.linalg.eigvalsh(res.W).max() <= fsw.MAX_AMPLIFICATION + 1e-9
    # red control: the incumbent-style sample inverse square root is uncontrolled
    Zc = fsw.standardize(F).to_numpy()
    assert np.linalg.eigvalsh(fsw.incumbent_weights(Zc)).max() > 100.0


def test_req1_well_conditioned_control_is_not_flagged():
    res = fsw.stable_whiten(_frame())
    assert res.diagnostics["unstable"] is False
    assert res.diagnostics["floor_binding"] == 0
    assert fsw.mean_abs_offdiag(res.values.to_numpy()) < 0.05


# ---------------------------------------------------------------- requirement 2
def test_req2_partially_missing_rows_keep_missing_indicators():
    F = _frame()
    F.loc[0, "b"] = np.nan
    F.loc[1, ["a", "b", "c"]] = np.nan
    F.loc[2, :] = np.nan
    res = fsw.stable_whiten(F)
    assert res.row_status.iloc[0] == fsw.ROW_PARTIAL
    assert res.row_status.iloc[1] == fsw.ROW_PARTIAL
    assert res.row_status.iloc[2] == fsw.ROW_UNMEASURED
    assert res.row_status.iloc[3] == fsw.ROW_FULL
    assert int(res.n_measured.iloc[0]) == 3 and int(res.n_measured.iloc[1]) == 1
    assert bool(res.measured.loc[0, "b"]) is False
    assert res.values.iloc[2].isna().all()
    assert res.diagnostics["n_partial_rows"] == 2
    # red control: the incumbent formula emits complete-looking rows, no indicator
    inc = fsw.incumbent_reference_transform(F)
    assert inc.iloc[0].notna().all() and inc.iloc[1].notna().all()


def test_req2_missing_leg_is_filled_by_conditional_expectation_not_zero():
    C = np.array([[1.0, 0.9], [0.9, 1.0]])
    Z = np.array([[2.0, np.nan], [np.nan, np.nan], [1.0, -1.0]])
    out = fsw.conditional_fill(Z, C)
    assert abs(out[0, 1] - 1.8) < 1e-12
    assert out[1, 0] == 0.0 and out[1, 1] == 0.0
    assert out[2, 1] == -1.0


# ---------------------------------------------------------------- requirement 3
def test_req3_permuting_factor_order_does_not_privilege_first_factor():
    F = _frame()
    F.loc[5, "c"] = np.nan
    perm = ["d", "c", "a", "b"]
    r0 = fsw.stable_whiten(F)
    r1 = fsw.stable_whiten(F[perm])
    np.testing.assert_allclose(r1.values[perm].to_numpy(), r0.values[perm].to_numpy(), atol=1e-9)
    assert abs(r0.diagnostics["shrinkage"] - r1.diagnostics["shrinkage"]) < 1e-12
    # red control: Cholesky (Gram-Schmidt) whitening keeps the first factor untouched
    Z = fsw.standardize(_frame()).to_numpy()
    Y = _cholesky_whiten(Z)
    np.testing.assert_allclose(Y[:, 0], Z[:, 0], atol=1e-9)
    Yp = _cholesky_whiten(Z[:, [3, 2, 0, 1]])
    assert not np.allclose(Yp[:, 2], Y[:, 0], atol=1e-3)


# ---------------------------------------------------------------- requirement 4
def _heavy_pairs(n: int = 40, p: int = 8, eps: float = 0.2, seed: int = 0, df: int = 3) -> pd.DataFrame:
    """Small-n, heavy-tailed panel of near-duplicate factor pairs."""
    rng = np.random.default_rng(seed)
    lat = rng.standard_t(df, size=(n, 2))
    cols = {}
    for j in range(p // 2):
        base = lat[:, j % 2] + 0.7 * rng.standard_t(df, size=n)
        cols[f"x{j}a"] = base
        cols[f"x{j}b"] = base + eps * rng.standard_t(df, size=n)
    return pd.DataFrame(cols)


def test_req4_resampling_reports_subspace_and_output_instability():
    F = _heavy_pairs()
    inc = fsw.bootstrap_instability(F, method="incumbent", n_boot=40, seed=1)
    stb = fsw.bootstrap_instability(F, method="stable", n_boot=40, seed=1)
    for rep in (inc, stb):
        for key in ("transform_rel_change_median", "output_rel_change_median",
                    "max_amplified_direction_sine_median", "fitted_offdiag_median",
                    "output_unstable"):
            assert key in rep
    # the fitted correlation looks perfect while the sample transform is unstable
    assert inc["fitted_offdiag_median"] < 0.02
    assert inc["output_rel_change_median"] > fsw.OUTPUT_INSTABILITY_BAR
    assert inc["output_unstable"] is True
    assert stb["output_rel_change_median"] < inc["output_rel_change_median"]
    # the challenger's in-sample residual correlation is reported, not hidden
    assert stb["fitted_offdiag_median"] > inc["fitted_offdiag_median"]
    # where the challenger's floor does not bind, shrinkage toward I and flooring
    # keep eigenvectors, so the amplified-direction sine is identical: the
    # challenger's gain there is bounded output change, not direction stability
    assert stb["amplified_subspace_degenerate"] is False
    assert abs(stb["max_amplified_direction_sine_median"]
               - inc["max_amplified_direction_sine_median"]) < 1e-9
    assert inc["max_amplified_direction_sine_median"] > 0.3
    ctrl = fsw.bootstrap_instability(_frame(n=300), method="incumbent", n_boot=30, seed=1)
    assert ctrl["output_unstable"] is False
    assert ctrl["max_amplified_direction_sine_median"] < 0.2
    assert ctrl["max_amplified_direction_sine_median"] < inc["max_amplified_direction_sine_median"]


def test_req4_amplified_direction_sine_discriminates_when_the_floor_binds():
    # near-exact duplicate pairs: the challenger's floor binds the duplicate block
    F = _heavy_pairs(n=200, eps=0.01, df=30)
    inc = fsw.bootstrap_instability(F, method="incumbent", n_boot=20, seed=1)
    stb = fsw.bootstrap_instability(F, method="stable", n_boot=20, seed=1)
    # the incumbent's single most-amplified direction swings between resamples
    assert inc["amplified_subspace_degenerate"] is False
    assert inc["max_amplified_direction_sine_median"] > 0.3
    # the challenger's floored block is compared as a subspace, and it is stable
    assert stb["amplified_subspace_degenerate"] is True
    assert stb["amplified_subspace_dim_base"] >= 2
    assert stb["max_amplified_direction_sine_median"] < 0.05
    assert inc["max_amplified_direction_sine_median"] > 10 * stb["max_amplified_direction_sine_median"]


def test_req4_degenerate_amplified_block_is_a_subspace_not_an_arbitrary_vector():
    W = np.diag([2.0, 2.0, 1.0])
    U = fsw.amplified_subspace(W)
    assert U.shape == (3, 2)
    t = 0.3
    R = np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])
    U_rot = fsw.amplified_subspace(R @ W @ R.T)
    # a rotation inside the tied block leaves the subspace unchanged
    assert fsw.subspace_sine(U, U_rot) < 1e-12
    # the one-dimensional case reduces to the vector formula sqrt(1 - (u.w)^2)
    u = np.array([[1.0], [0.0], [0.0]])
    w = np.array([[np.cos(t)], [np.sin(t)], [0.0]])
    assert abs(fsw.subspace_sine(u, w) - np.sin(t)) < 1e-12
    # a subspace contained in a larger one has sine 0; an orthogonal one has sine 1
    assert fsw.subspace_sine(u, U) < 1e-12
    assert abs(fsw.subspace_sine(np.array([[0.0], [0.0], [1.0]]), U) - 1.0) < 1e-12


def test_req4_bootstrap_support_follows_each_methods_own_rule():
    rng = np.random.default_rng(3)
    F = _frame(n=200)
    for c in F.columns:
        F.loc[rng.random(200) < 0.45, c] = np.nan
    n_complete = int(F.notna().all(axis=1).sum())
    assert n_complete < fsw.support_rule(F.shape[1])
    # the challenger whitens this panel on pairwise support, so its bootstrap must too
    assert fsw.stable_whiten(F).status != fsw.STATUS_FALLBACK
    stb = fsw.bootstrap_instability(F, method="stable", n_boot=10, seed=1)
    assert stb["status"] == "ok"
    assert stb["output_rows"] == n_complete
    # the incumbent needs complete cases and falls back explicitly
    inc = fsw.bootstrap_instability(F, method="incumbent", n_boot=10, seed=1)
    assert inc["status"] == fsw.STATUS_FALLBACK and inc["n_boot"] == 0


# ---------------------------------------------------------------- requirement 5
def test_req5_sparse_fallback_is_identified_as_untransformed():
    F = _frame(n=10)
    res = fsw.stable_whiten(F)
    assert res.status == fsw.STATUS_FALLBACK
    assert res.whitened is False and res.W is None
    assert "support" in res.diagnostics["fallback_reason"]
    pd.testing.assert_frame_equal(res.values, F)
    one = fsw.stable_whiten(pd.DataFrame({"only": [1.0, 2.0, 3.0]}))
    assert one.status == fsw.STATUS_FALLBACK and one.whitened is False
    # red control: the incumbent formula returns the same bytes with no status at all
    pd.testing.assert_frame_equal(fsw.incumbent_reference_transform(F), F)
    assert isinstance(fsw.incumbent_reference_transform(F), pd.DataFrame)


# ---------------------------------------------------------------- requirement 6
def test_req6_live_ranks_atlas_ownership_and_trial_budget_preserved():
    F = _frame()
    F.loc[7, "a"] = np.nan
    # a non-monotone index: any internal sort or re-ranking would reorder the output
    F.index = np.random.default_rng(11).permutation(len(F)) + 1000
    before = copy.deepcopy(F)
    res = fsw.stable_whiten(F)
    pd.testing.assert_frame_equal(F, before)                       # input untouched
    assert list(res.values.columns) == list(F.columns)
    assert res.values.index.equals(F.index)                         # order preserved, not sorted
    assert res.row_status.index.equals(F.index)
    # the outputs never alias the caller's data: mutating them cannot reach live ranks
    for out in (res.values, res.raw_z):
        assert not np.shares_memory(out.to_numpy(), F.to_numpy())
    res.values.iloc[:, :] = 0.0
    res.raw_z.iloc[:, :] = 0.0
    pd.testing.assert_frame_equal(F, before)
    # no ranking, scoring, compositing, persistence or registration surface
    public = {n for n in dir(fsw) if not n.startswith("_") and callable(getattr(fsw, n))}
    banned = ("rank", "score", "composite", "write", "save", "persist", "register", "publish")
    assert not [n for n in public if any(b in n.lower() for b in banned)]
    assert fsw.TRIAL_BUDGET_CHARGE == 0
    assert fsw.CONSUMERS == ()


def test_no_silent_activation_module_contract():
    assert fsw.RESEARCH_ONLY is True
    assert fsw.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    for name in ("register", "REGISTRY", "main", "run", "activate", "publish"):
        assert not hasattr(fsw, name)
    imported = {k for k, v in vars(fsw).items() if isinstance(v, types.ModuleType)}
    assert imported <= {"math", "np", "pd"}
    with np.errstate(all="ignore"):
        try:
            fsw.stable_whiten(pd.DataFrame({"a": [np.inf, 1.0], "b": [1.0, 2.0]}))
        except ValueError:
            pass
        else:
            raise AssertionError("inf input must be refused")
