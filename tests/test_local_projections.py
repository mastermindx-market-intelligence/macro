"""Tests for engine/local_projections.py.

A results table cannot show whether an estimator's guards actually bind - only a
test that perturbs the embargoed bars, forces a degenerate design, or measures
the naive/HAC gap on a known DGP can. Synthetic-only (no store, no data/ reads),
so this file runs in a sparse worktree with no `needs_full_checkout` marker,
mirroring tests/test_synthetic_control.py.
"""
import inspect
import math
import os
import re
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402

import engine.local_projections as lp  # noqa: E402
from engine.validation import newey_west_tstat  # noqa: E402


# --------------------------------------------------------------------------- #
# 1-2: recovery on a known-truth DGP
# --------------------------------------------------------------------------- #
# h=0..8 is where true_irf (0.01 * 0.75**h) still sits well above this DGP's
# noise floor; a fixed 0.003 tolerance was vacuous well before h=8 (already 2x
# the true effect there) and became meaningless by h=20 (94x). Past h=8 the
# true effect is smaller than the estimator's own noise floor, so no numeric
# tolerance on beta itself is honest - what MUST hold instead is that a
# rejecting horizon never reports the wrong sign. Plain BH let a sign-wrong
# h=13 read as a discovery (beta=-0.00131 vs true=+0.00024, q=0.0462); BY
# (the shipped correction) is what makes that assertion bind.
_NEAR_HORIZONS = 9
_NEAR_TOL = 0.001


def _assert_recovers_near_horizons_and_never_rejects_with_wrong_sign(result, true_irf):
    """Near-horizon recovery AND no wrong-sign BH/BY-surviving discovery.

    Under plain BH the demo fixture (seed=11) produced a sign-wrong reject at
    h=13 (beta=-0.00131 vs true=+0.00024). BY (dependence-robust) is what
    makes the no-wrong-sign half of this name an honest guarantee rather than
    a comment that deliberately skips the check.
    """
    betas = np.array([row["beta"] for row in result["irf"]])
    near = slice(0, _NEAR_HORIZONS)
    assert np.all(np.abs(betas[near] - true_irf[near]) < _NEAR_TOL)
    assert int(np.argmax(betas)) == 0
    rejecting = set(result["null"]["rejecting_horizons"])
    for h in rejecting:
        beta = float(result["irf"][h]["beta"])
        true_h = float(true_irf[h])
        if abs(true_h) < 1e-12:
            continue
        assert np.sign(beta) == np.sign(true_h), (
            f"horizon h={h} rejected with wrong sign: beta={beta}, true={true_h}"
        )


def test_recovers_a_known_geometric_irf():
    y, shock, true_irf = lp.demo_series(true_beta=0.010, decay=0.75, seed=11)
    result = lp.impulse_response(y, shock)
    _assert_recovers_near_horizons_and_never_rejects_with_wrong_sign(result, true_irf)


def test_recovers_a_hump_shaped_irf():
    rng = np.random.default_rng(23)
    n, horizons = 900, lp.HORIZONS
    shock = rng.standard_normal(n)
    # hump-shaped psi peaking at h=3, not a monotone decay
    j = np.arange(horizons + 1)
    psi = 0.012 * j * (0.7 ** j)
    y = np.convolve(shock, psi)[:n] + 0.008 * rng.standard_normal(n)
    result = lp.impulse_response(y, shock, horizons=horizons)
    betas = np.array([row["beta"] for row in result["irf"]])
    assert int(np.argmax(betas)) == 3


def test_no_shock_gives_a_null_at_every_horizon():
    # Single-seed sanity (words + method disclosure). The calibrated rate is
    # pinned by test_global_null_family_wise_rate_stays_at_or_below_fdr_alpha.
    rng = np.random.default_rng(0)
    n = 500
    shock = rng.standard_normal(n)
    y = rng.standard_normal(n) * 0.01  # independent of shock
    result = lp.impulse_response(y, shock)
    assert result["multiple_testing"]["method"] == lp.FDR_METHOD
    assert "yekutieli" in result["multiple_testing"]["note"].lower()
    words = result["null"]["plain_words"].lower()
    if result["null"]["any_horizon_rejects"]:
        # A lone seed may still reject under BY (~6% rate); that is not a
        # failure of this smoke test. The multi-seed calibration test owns
        # the rate.
        assert "measurable effect" in words
    else:
        assert "no time-step" in words


def test_global_null_family_wise_rate_stays_at_or_below_fdr_alpha():
    """Calibration pin for acceptance line 2 / MAJOR 1.

    Under a complete null, BY's FDR equals P(any rejection). 80 fixed seeds keep
    the suite fast. This is a BY rate ceiling, not a high-power BH discriminator:
    at the one-off 300-seed BH rate 0.153, P(≤10 of 80) ≈ 0.29, so a return to
    plain BH fails this bound only ~70% of the time on these seeds. The method
    string assert below is the hard BH-regression guard; the rate bound catches
    gross overshoot.
    """
    n_sims = 80
    rejects = 0
    for seed in range(n_sims):
        rng = np.random.default_rng(20000 + seed)
        n = 800
        shock = rng.standard_normal(n)
        y = rng.standard_normal(n) * 0.01
        result = lp.impulse_response(y, shock)
        if result["null"]["any_horizon_rejects"]:
            rejects += 1
    rate = rejects / n_sims
    # FDR_ALPHA=0.10; allow binomial sampling slack (80 trials, calibrated BY ~0.06).
    # Bound is a BY ceiling, not a proof that BH (~0.153 on 300 seeds) always fails
    # on these exact 80 seeds (~0.71 discrimination power at that rate).
    assert rate <= 0.125, (
        f"global-null any-reject rate {rate:.3f} ({rejects}/{n_sims}) exceeds "
        f"FDR_ALPHA={lp.FDR_ALPHA} + sampling slack; dependence-robust BY may "
        f"have been replaced by independence-assuming BH"
    )
    assert result["multiple_testing"]["method"] == "benjamini_yekutieli"


# --------------------------------------------------------------------------- #
# 4-7: the HAC guard
# --------------------------------------------------------------------------- #
def test_hac_matches_validation_helper_on_an_intercept_only_regression():
    rng = np.random.default_rng(3)
    n = 300
    # build an MA(4)-overlapping series so the HAC correction actually engages
    eps = rng.standard_normal(n)
    y = eps.copy()
    for j in range(1, 5):
        y[j:] += 0.5 * eps[:-j]

    X = np.ones((n, 1))
    beta, resid, _ = lp._ols(X, y)
    V = lp._hac_sandwich(X, resid, lags=4)
    se_sandwich = float(np.sqrt(V[0, 0]))

    helper = newey_west_tstat(y, lags=4)
    assert helper["se"] is not None
    assert round(se_sandwich, 5) == round(helper["se"], 5)
    assert helper["lags"] == 4


def test_hac_lag_is_h_plus_one_and_reports_the_effective_clamp():
    rng = np.random.default_rng(5)
    n = 17  # yields 6 usable rows against 4 design columns (lags=1) -> dof=2,
    # enough real residual degrees of freedom to exercise the lag clamp without
    # tripping the insufficient_dof guard (n == n_columns would abstain).
    y = rng.standard_normal(n) * 0.01
    shock = rng.standard_normal(n)
    h = 10
    row = lp.estimate_horizon(y, shock, h, lags=1, embargo=1, min_obs=5)
    assert not row.get("abstained")
    assert row["hac_lags_requested"] == h + 1
    assert row["hac_lags"] < row["hac_lags_requested"]
    assert row["hac_lags"] <= max(row["n"] - 1, 0)


def _ma_correlated_design(rng, n, lags_ma, ma_coef=0.6):
    """A hand-built (intercept, shock) design whose residual is MA(lags_ma) by
    construction - the exact structure an LP horizon target has (its residual
    at horizon h is MA(h) because adjacent targets share h-1 future periods).
    Used to test the HAC guard directly, decoupled from whether a particular
    fitted LP specification's own controls happen to absorb the persistence."""
    eps = rng.standard_normal(n)
    resid_true = eps.copy()
    for j in range(1, lags_ma + 1):
        resid_true[j:] += ma_coef * eps[:-j]
    shock = rng.standard_normal(n)
    X = np.column_stack([np.ones(n), shock])
    y = resid_true  # under the null, y is pure MA(lags_ma) noise, unrelated to shock
    return X, y


def test_overlapping_targets_inflate_the_naive_standard_error():
    # The intercept column is constant across t, so its coefficient's sandwich
    # variance isolates the effect of the MA(lags_ma) residual correlation
    # itself - exactly engine.validation.newey_west_tstat's own justification
    # ("overlapping windows serially-correlate a signal's per-date stats, so a
    # plain t-stat overstates significance"), which this module inherits
    # unmodified for the horizon-panel se.
    rng = np.random.default_rng(41)
    lags_ma = 6
    X, y = _ma_correlated_design(rng, n=300, lags_ma=lags_ma)
    beta, resid, xtx_pinv = lp._ols(X, y)
    sigma2 = float(np.dot(resid, resid) / (len(y) - 2))
    se_naive = math.sqrt(sigma2 * xtx_pinv[0, 0])
    V = lp._hac_sandwich(X, resid, lags_ma)
    se_hac = math.sqrt(V[0, 0])
    assert se_hac > se_naive
    assert se_hac / se_naive > 1.3


def test_naive_t_over_rejects_on_the_null_dgp():
    # Overlapping horizon targets make the LP residual MA(h) by construction
    # (target y[t+h] and y[t+h+1] share h-1 future periods) - a naive OLS se
    # assumes iid errors and understates the true variance under exactly that
    # structure, so it over-rejects a true null far more than the HAC se does.
    n_sims = 200
    lags_ma = 6
    naive_rejects = 0
    hac_rejects = 0
    for seed in range(n_sims):
        rng = np.random.default_rng(5000 + seed)
        X, y = _ma_correlated_design(rng, n=150, lags_ma=lags_ma)
        beta, resid, xtx_pinv = lp._ols(X, y)
        sigma2 = float(np.dot(resid, resid) / (len(y) - 2))
        se_naive = math.sqrt(sigma2 * xtx_pinv[0, 0])
        V = lp._hac_sandwich(X, resid, lags_ma)
        se_hac = math.sqrt(max(V[0, 0], 0.0))
        naive_t = beta[0] / se_naive if se_naive else 0.0
        hac_t = beta[0] / se_hac if se_hac else 0.0
        if abs(naive_t) > 1.96:
            naive_rejects += 1
        if abs(hac_t) > 1.96:
            hac_rejects += 1
    naive_rate = naive_rejects / n_sims
    hac_rate = hac_rejects / n_sims
    assert naive_rate > 0.15
    assert naive_rate > hac_rate


# --------------------------------------------------------------------------- #
# 8-9: lookahead guard
# --------------------------------------------------------------------------- #
def test_control_block_never_reads_the_embargoed_bars():
    rng = np.random.default_rng(9)
    n = 60
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    lags, embargo = 2, 3
    dm1 = lp.design_matrix(y, shock, lags=lags, embargo=embargo)

    t_ref = 40
    control_hi = t_ref - embargo
    gap = range(control_hi + 1, t_ref)  # bars strictly between control_hi and t_ref
    assert len(list(gap)) > 0

    y2 = y.copy()
    shock2 = shock.copy()
    for idx in gap:
        y2[idx] = 999.0
        shock2[idx] = -999.0

    dm2 = lp.design_matrix(y2, shock2, lags=lags, embargo=embargo)
    assert np.array_equal(dm1["X"][t_ref], dm2["X"][t_ref])


def test_targets_never_exceed_the_sample():
    rng = np.random.default_rng(15)
    n = 200
    y = rng.standard_normal(n) * 0.01
    shock = rng.standard_normal(n)
    result = lp.impulse_response(y, shock, horizons=10)
    ns = [result["diagnostics"]["n_by_horizon"][str(h)] for h in range(11)]
    assert all(ns[i] >= ns[i + 1] for i in range(len(ns) - 1))

    y_ext = np.concatenate([y, rng.standard_normal(20) * 0.01])
    shock_ext = np.concatenate([shock, rng.standard_normal(20)])
    result2 = lp.impulse_response(y_ext, shock_ext, horizons=10)
    for h in range(11):
        assert result2["diagnostics"]["n_by_horizon"][str(h)] >= result["diagnostics"]["n_by_horizon"][str(h)]


# --------------------------------------------------------------------------- #
# 10-12: typed refusals
# --------------------------------------------------------------------------- #
def test_abstains_below_min_obs():
    rng = np.random.default_rng(21)
    n = 30
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    row = lp.estimate_horizon(y, shock, 0, min_obs=1000)
    assert row["abstained"] is True
    assert row["schema"] == lp.ABSTENTION_SCHEMA
    assert row["reason"] == "insufficient_observations"
    assert not isinstance(row.get("beta"), float)


def test_degenerate_shock_abstains():
    rng = np.random.default_rng(22)
    n = 200
    y = rng.standard_normal(n)
    shock = np.ones(n) * 5.0  # constant
    row = lp.estimate_horizon(y, shock, 0, min_obs=10)
    assert row["abstained"] is True
    assert row["reason"] == "degenerate_shock"
    assert "t" not in row


def test_rank_deficient_design_abstains():
    rng = np.random.default_rng(24)
    n = 200
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    # controls=y duplicates the y_lag1 control column exactly -> rank deficient
    row = lp.estimate_horizon(y, shock, 0, controls=y, min_obs=10)
    assert row["abstained"] is True
    assert row["reason"] == "rank_deficient_design"


# --------------------------------------------------------------------------- #
# 13: BY correction (dependence-robust; not plain BH)
# --------------------------------------------------------------------------- #
def test_by_correction_is_applied_and_reject_reads_q():
    y, shock, _ = lp.demo_series(seed=11)
    result = lp.impulse_response(y, shock)
    assert result["multiple_testing"]["method"] == "benjamini_yekutieli"
    assert result["multiple_testing"]["n_horizons_declared"] == lp.HORIZONS + 1
    assert result["multiple_testing"]["n_horizons_tested"] == len(result["fdr"])
    assert "understates" not in result["inference"]["why"].lower()
    assert "hac_inflation" in result["inference"]["why"]
    for h_str, row in result["fdr"].items():
        assert row["q"] >= row["p"] - 1e-9
        # reject reads q against FDR_ALPHA (0.10), never a hard-coded 0.05.
        if row["q"] > lp.FDR_ALPHA:
            assert row["reject"] is False
        if row["reject"] is True:
            assert row["q"] <= lp.FDR_ALPHA + 1e-12
    # q must be monotone non-decreasing when sorted by ascending p (BY walk-up)
    sorted_by_p = sorted(result["fdr"].items(), key=lambda kv: kv[1]["p"])
    q_seq = [v["q"] for _, v in sorted_by_p]
    assert all(q_seq[i] <= q_seq[i + 1] + 1e-9 for i in range(len(q_seq) - 1))


def test_n_horizons_tested_counts_only_non_abstained():
    # Force every horizon to abstain via min_obs > sample so tested=0 while
    # declared stays at horizons+1.
    rng = np.random.default_rng(0)
    n = 40
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    result = lp.impulse_response(y, shock, horizons=5, min_obs=100)
    assert result["multiple_testing"]["n_horizons_declared"] == 6
    assert result["multiple_testing"]["n_horizons_tested"] == 0
    assert result["fdr"] == {}


# --------------------------------------------------------------------------- #
# 14-15: trial ledger integration
# --------------------------------------------------------------------------- #
def test_named_family_without_registration_raises():
    from engine.seasonality.event_study import UnregisteredSearchFamily

    y, shock, _ = lp.demo_series(seed=11, n=200)
    with pytest.raises(UnregisteredSearchFamily):
        lp.impulse_response(y, shock, family="lp.demo.unregistered", ledger=None)


def test_registered_family_reports_effective_n(tmp_path):
    from engine.trial_ledger import TrialLedger

    led = TrialLedger(path=tmp_path / "lp_ledger.jsonl", family="lp.test.registered")
    if hasattr(led, "log_declared_budget"):
        led.log_declared_budget(5, family="lp.test.registered")
    else:
        led.log_grid({"cfg": [1]}, info_cutoff="2026-09-05")

    y, shock, _ = lp.demo_series(seed=11, n=200)
    result = lp.impulse_response(y, shock, family="lp.test.registered", ledger=led)
    assert isinstance(result["multiple_testing"]["effective_n"], int)
    assert result["multiple_testing"]["effective_n"] >= 1


# --------------------------------------------------------------------------- #
# 16-19: frozen constants, plain words, CLI, purity
# --------------------------------------------------------------------------- #
def test_pre_registered_constants_are_frozen():
    assert lp.HORIZONS == 20
    assert lp.LAGS == 4
    assert lp.EMBARGO == 1
    assert lp.MIN_OBS_PER_H == 60
    assert lp.FDR_ALPHA == 0.10
    assert lp.FDR_METHOD == "benjamini_yekutieli"
    assert lp.CI_LEVEL == 0.95
    assert lp.SCHEMA == "engine.local_projections.irf.v1"
    assert lp.ABSTENTION_SCHEMA == "engine.local_projections.abstention.v1"
    assert lp.HAC_LAG_RULE == "h + 1"
    assert lp.GLOBAL_NULL_FWER_VINTAGE == "historical_pre_finite_sample_66f414ac2b3"


_PLAIN_WORDS_BANNED = [
    "p-value", "p =", "beta", "hac", "newey", "horizon h", "schema", "engine.", "q =",
    "rank deficient", "insufficient dof", "misaligned lengths", "non finite",
    "degenerate shock", "insufficient observations", "horizon exceeds",
    "rank_deficient", "insufficient_dof", "misaligned_lengths", "non_finite",
    "degenerate_shock", "insufficient_observations", "horizon_exceeds_sample",
]


def _assert_plain_words_customer_facing(words, *, max_words=30):
    assert len(words.split()) <= max_words, words
    low = words.lower()
    for banned in _PLAIN_WORDS_BANNED:
        assert banned not in low, f"{banned!r} leaked into {words!r}"


def test_plain_words_has_no_jargon_and_fits_the_budget():
    for rejecting in ([], [1, 4, 7]):
        fake = {"null": {"rejecting_horizons": rejecting}}
        _assert_plain_words_customer_facing(lp.plain_words(fake))

    # Drive every typed abstention through the real estimator, then through
    # impulse_response so the reason branch (irf + n_horizons_tested=0) runs.
    rng = np.random.default_rng(0)
    cases = {
        "insufficient_observations": lp.estimate_horizon(
            rng.standard_normal(30), rng.standard_normal(30), 0, min_obs=1000,
        ),
        "degenerate_shock": lp.estimate_horizon(
            rng.standard_normal(200), np.ones(200) * 5.0, 0, min_obs=10,
        ),
        "rank_deficient_design": None,  # filled below with the y-as-control fixture
        "insufficient_dof": lp.estimate_horizon(
            rng.standard_normal(3), rng.standard_normal(3), 0,
            lags=0, embargo=1, min_obs=1,
        ),
        "misaligned_lengths": lp.estimate_horizon(
            rng.standard_normal(50), rng.standard_normal(30), 0, min_obs=1,
        ),
        "non_finite_input": lp.estimate_horizon(
            np.full(80, np.nan), rng.standard_normal(80), 0, min_obs=10,
        ),
        "horizon_exceeds_sample": lp.estimate_horizon(
            rng.standard_normal(8), rng.standard_normal(8), 20, min_obs=1,
        ),
    }
    # controls=y is the rank-deficiency fixture used elsewhere; rebuild it.
    y_rank = rng.standard_normal(200)
    cases["rank_deficient_design"] = lp.estimate_horizon(
        y_rank, rng.standard_normal(200), 0, controls=y_rank, min_obs=10,
    )
    expected_phrase = {
        "insufficient_observations": "enough history",
        "degenerate_shock": "never actually varied",
        "rank_deficient_design": "inputs repeat each other",
        "insufficient_dof": "inputs repeat each other",
        "misaligned_lengths": "do not line up",
        "non_finite_input": "gaps we could not fill",
        "horizon_exceeds_sample": "past the end of the data",
    }
    for reason, row in cases.items():
        assert row.get("abstained") is True, reason
        assert row["reason"] == reason
        payload = {
            "null": {"rejecting_horizons": []},
            "multiple_testing": {"n_horizons_tested": 0, "n_horizons_declared": 1},
            "irf": [row],
        }
        words = lp.plain_words(payload)
        _assert_plain_words_customer_facing(words)
        assert expected_phrase[reason] in words.lower(), (reason, words)
        assert reason not in words
        assert reason.replace("_", " ") not in words.lower()

    # Two distinct reasons must both appear; sorted()[0] used to hide the rest.
    multi = {
        "null": {"rejecting_horizons": []},
        "multiple_testing": {"n_horizons_tested": 0, "n_horizons_declared": 2},
        "irf": [cases["degenerate_shock"], cases["rank_deficient_design"]],
    }
    words = lp.plain_words(multi)
    _assert_plain_words_customer_facing(words, max_words=50)
    assert "never actually varied" in words
    assert "inputs repeat each other" in words


def test_cli_demo_runs_in_process_and_reports_recovery(capsys):
    rc = lp.main(["--demo", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    import json
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["schema"] == lp.SCHEMA
    _, _, true_irf = lp.demo_series()
    _assert_recovers_near_horizons_and_never_rejects_with_wrong_sign(payload, true_irf)


def test_saturated_regression_abstains_instead_of_faking_zero_residual_dof():
    # n == n_columns fits every point exactly: rank is full (passes the rank
    # guard) but residual dof is zero. dof = max(n - n_columns, 1) used to mask
    # that and mint a fake se from a near-zero sigma2 - a non-abstained row
    # with se~1e-16, |t|~1e14, p=0.0, a zero-width CI, and (through
    # impulse_response) a BH-rejecting horizon out of a regression with no
    # honest inference left in it.
    rng = np.random.default_rng(2)
    n = 3  # lags=0 -> n_columns=2 (const, shock_t); embargo=1 leaves exactly 2
    # usable rows (t=1,2) -> n == n_columns, dof=0.
    lags = 0
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    row = lp.estimate_horizon(y, shock, 0, lags=lags, embargo=1, min_obs=1)
    assert row.get("abstained") is True
    assert row["reason"] == "insufficient_dof"
    assert "t" not in row
    assert "se" not in row


def test_misaligned_controls_length_abstains_instead_of_silently_shrinking_sample():
    # controls shorter than y used to silently drop ~75% of rows (n=97 of 396)
    # and still return a non-abstained fit above MIN_OBS_PER_H. Longer controls
    # were accepted with no flag. Both must be typed misaligned_lengths.
    rng = np.random.default_rng(7)
    n = 400
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    short_ctrl = np.arange(100.0)
    long_ctrl = rng.standard_normal(1000)

    row_short = lp.estimate_horizon(y, shock, 0, controls=short_ctrl, min_obs=60)
    assert row_short.get("abstained") is True
    assert row_short["reason"] == "misaligned_lengths"
    assert row_short.get("n_controls") == 100

    row_long = lp.estimate_horizon(y, shock, 0, controls=long_ctrl, min_obs=60)
    assert row_long.get("abstained") is True
    assert row_long["reason"] == "misaligned_lengths"

    with pytest.raises(ValueError):
        lp.design_matrix(y, shock, controls=short_ctrl)

    result = lp.impulse_response(y, shock, controls=short_ctrl, horizons=3, min_obs=60)
    assert all(row.get("abstained") and row["reason"] == "misaligned_lengths"
               for row in result["irf"])


def test_misaligned_shock_length_abstains_instead_of_crashing():
    # shock shorter than y used to IndexError inside design_matrix; shock
    # longer than y used to IndexError on the boolean-mask index. Both must be
    # a typed abstention, per the module's own typed-refusal contract.
    rng = np.random.default_rng(6)
    y = rng.standard_normal(50)
    short_shock = rng.standard_normal(30)
    long_shock = rng.standard_normal(80)

    row_short = lp.estimate_horizon(y, short_shock, 0, min_obs=1)
    assert row_short.get("abstained") is True
    assert row_short["reason"] == "misaligned_lengths"

    row_long = lp.estimate_horizon(y, long_shock, 0, min_obs=1)
    assert row_long.get("abstained") is True
    assert row_long["reason"] == "misaligned_lengths"

    with pytest.raises(ValueError):
        lp.design_matrix(y, short_shock)

    # impulse_response must not crash either - every horizon abstains the same way.
    result = lp.impulse_response(y, short_shock, horizons=3, min_obs=1)
    assert all(row.get("abstained") and row["reason"] == "misaligned_lengths"
               for row in result["irf"])


def test_hac_inflation_measured_through_the_real_estimate_horizon_path():
    # tests/test_local_projections.py's other HAC tests all drive
    # _hac_sandwich against hand-built matrices, decoupled from whether a
    # fitted LP specification's own lag controls happen to absorb the
    # overlap-induced persistence. This test reads hac_inflation off actual
    # impulse_response rows on the module's own demo DGP - the path the
    # docstring's inflation claim must be measured against, not a fixed
    # multiplier.
    y, shock, _ = lp.demo_series(seed=11)
    result = lp.impulse_response(y, shock)
    inflations = [row["hac_inflation"] for row in result["irf"]
                  if not row.get("abstained") and np.isfinite(row["hac_inflation"])]
    assert len(inflations) >= lp.HORIZONS // 2
    # HAC/naive on the real LP path is not a fixed >1 multiplier - it varies
    # by horizon and can sit below 1.0. Bound it to a sane finite range rather
    # than asserting a specific inflation factor the docstring no longer claims.
    assert all(0.3 < v < 5.0 for v in inflations)




def test_targets_dropped_at_tail_is_measured_not_identity():
    rng = np.random.default_rng(15)
    n = 200
    y = rng.standard_normal(n) * 0.01
    shock = rng.standard_normal(n)
    result = lp.impulse_response(y, shock, horizons=10)
    dropped = result["pit"]["targets_dropped_at_tail"]
    n_by = result["diagnostics"]["n_by_horizon"]
    # Property: drop[h] == max_panel_n - n_h, not first-nonzero-n - n_h and
    # not a hardcoded identity map {h: h}.
    base_n = max(n_by.get(str(h), 0) for h in range(11))
    for h in range(11):
        assert dropped[str(h)] == max(0, base_n - n_by.get(str(h), 0))
    # Fully-abstained path must report zeros, never the identity map {h: h}.
    short_y = rng.standard_normal(10)
    short_shock = rng.standard_normal(5)  # misaligned -> every horizon abstains
    empty = lp.impulse_response(short_y, short_shock, horizons=5, min_obs=1)
    assert empty["pit"]["targets_dropped_at_tail"] == {str(h): 0 for h in range(6)}


def test_targets_dropped_at_tail_uses_largest_panel_not_first_nonzero():
    # Early horizon n=10, later n=80 then n=60: the old first-nonzero formula
    # reported drop[1]=0 and drop[2]=0 (max(0, 10-80), max(0, 10-60)).
    n_by = {"0": 10, "1": 80, "2": 60}
    dropped = lp._targets_dropped_at_tail(n_by, 2)
    assert dropped == {"0": 70, "1": 0, "2": 20}
    assert dropped["2"] == 20


def test_shock_variance_ignores_nan_and_survives_finite_input():
    rng = np.random.default_rng(19)
    n = 120
    y = rng.standard_normal(n)
    shock = rng.standard_normal(n)
    shock[5] = np.nan
    result = lp.impulse_response(y, shock, horizons=2, min_obs=10)
    assert np.isfinite(result["diagnostics"]["shock_variance"])

def test_module_does_no_io():
    src = inspect.getsource(lp)
    assert "open(" not in src
    assert "requests" not in src
    assert "pathlib.Path(" not in src
    assert "from engine.store" not in src
    assert "from data" not in src
    assert "import engine.store" not in src


def test_plain_words_distinguishes_abstention_from_tested_null():
    # MAJOR 1 regression: a fully-abstained impulse_response (nothing could be
    # measured) must not publish the same sentence as an honest tested null
    # (every horizon measured, none survived correction). Drive the real
    # all-abstained path (misaligned shock), not a hand-built fake dict, since
    # the hand-built fake in test_plain_words_has_no_jargon_and_fits_the_budget
    # cannot exercise the multiple_testing/irf fields this branches on.
    y, shock, _ = lp.demo_series(seed=11)
    result = lp.impulse_response(y, shock[:10], horizons=5, min_obs=100)
    assert result["multiple_testing"]["n_horizons_tested"] == 0
    words = result["null"]["plain_words"]
    assert "not available" in words.lower()
    assert "do not line up" in words.lower()
    assert "misaligned" not in words.lower()
    assert "no time-step after the shock showed an effect" not in words.lower()


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_BANNED_FRONT_TOKENS = ("falsif", "证伪", "validated")


def _assert_en_zh_parity(en: str, zh: str) -> None:
    assert _CJK_RE.search(zh), zh
    assert zh != en
    assert re.findall(r"\d+", en) == re.findall(r"\d+", zh), (en, zh)
    blob = f"{en}\n{zh}".lower()
    for banned in _BANNED_FRONT_TOKENS:
        assert banned not in blob, (banned, en, zh)
    assert not re.search(r"[A-Za-z]", zh), zh


def test_plain_words_zh_parity_on_every_branch():
    # MINOR 5: each customer sentence has a ZH counterpart. Same numbers,
    # CJK present, no English inside ZH, no front-facing banned tokens.
    branches = {
        "rejecting": {
            "null": {"rejecting_horizons": [0, 3, 7]},
            "multiple_testing": {"n_horizons_tested": 21, "n_horizons_declared": 21},
        },
        "none_tested": {
            "null": {"rejecting_horizons": []},
            "multiple_testing": {"n_horizons_tested": 0, "n_horizons_declared": 6},
            "irf": [{"abstained": True, "reason": "insufficient_observations"}],
        },
        "partial": {
            "null": {"rejecting_horizons": []},
            "multiple_testing": {"n_horizons_tested": 12, "n_horizons_declared": 21},
        },
        "honest_null": {
            "null": {"rejecting_horizons": []},
            "multiple_testing": {"n_horizons_tested": 21, "n_horizons_declared": 21},
        },
    }
    expected_zh = {
        "rejecting": "冲击后有 3 个时点出现了可测量的影响，并通过了对多时点同时检验的校正。",
        "none_tested": "暂无结果——冲击后没有任何时点可以测量（历史数据不足）。",
        "partial": "在可测量的 12 个时点中，没有影响通过校正；另有 9 个时点暂时无法测量。",
        "honest_null": "冲击后没有任何时点出现通过校正的影响，该校正针对多时点同时检验。",
    }
    for name, payload in branches.items():
        en = lp.plain_words(payload, lang="en")
        zh = lp.plain_words(payload, lang="zh")
        _assert_en_zh_parity(en, zh)
        assert zh == expected_zh[name], (name, zh)


def test_every_plain_reason_key_has_en_and_zh():
    # MINOR 5: every slug `_plain_reason_texts` can emit has both languages.
    assert set(lp._REASON_PLAIN) == set(lp._REASON_PLAIN_ZH)
    assert set(lp._REASON_FALLBACK) == {"en", "zh"}
    assert _CJK_RE.search(lp._REASON_FALLBACK["zh"])
    assert not re.search(r"[A-Za-z]", lp._REASON_FALLBACK["zh"])
    for key, en in lp._REASON_PLAIN.items():
        zh = lp._REASON_PLAIN_ZH[key]
        _assert_en_zh_parity(en, zh)
        payload = {
            "null": {"rejecting_horizons": []},
            "multiple_testing": {"n_horizons_tested": 0, "n_horizons_declared": 1},
            "irf": [{"abstained": True, "reason": key}],
        }
        en_line = lp.plain_words(payload, lang="en")
        zh_line = lp.plain_words(payload, lang="zh")
        _assert_en_zh_parity(en_line, zh_line)
        assert en in en_line
        assert zh in zh_line
        assert key not in en_line and key not in zh_line
    unknown = lp._plain_reason_texts(["not_a_real_slug"], lang="zh")
    assert unknown == [lp._REASON_FALLBACK["zh"]]


def test_single_nan_target_does_not_abstain_the_whole_horizon():
    # MAJOR 2 regression: one non-finite value in y used to abstain every
    # horizon with reason non_finite_input even when hundreds of other rows
    # were perfectly usable. A gapped macro series must still yield an
    # estimate from its finite rows, with the drop counted, not hidden.
    y, shock, _ = lp.demo_series(seed=11, n=800)
    y = y.copy()
    y[400] = np.nan
    result = lp.impulse_response(y, shock, horizons=5, min_obs=100)
    assert result["multiple_testing"]["n_horizons_tested"] > 0
    non_finite_abstentions = [
        row for row in result["irf"]
        if row.get("abstained") and row.get("reason") == "non_finite_input"
    ]
    assert non_finite_abstentions == []
    measured = [row for row in result["irf"] if not row.get("abstained")]
    assert measured
    assert any(row.get("n_dropped_non_finite", 0) > 0 for row in measured)


def _horizon_arrays(y, shock, h, *, lags=lp.LAGS, embargo=lp.EMBARGO):
    """Same row selection as estimate_horizon, so tests can swap HAC kernels."""
    y = np.asarray(y, dtype=float)
    shock = np.asarray(shock, dtype=float)
    T = len(y)
    dm = lp.design_matrix(y, shock, lags=lags, embargo=embargo)
    t_idx = np.arange(T)
    mask = dm["valid"] & (t_idx + h < T) & (t_idx - 1 >= 0)
    mask_idx = t_idx[mask]
    yv = y[mask_idx + h] - y[mask_idx - 1]
    finite = np.isfinite(yv)
    mask_idx = mask_idx[finite]
    yv = yv[finite]
    X = dm["X"][mask_idx]
    return X, yv, mask_idx


def test_gapped_panel_hac_se_differs_from_positional_contiguous_assumption():
    # MAJOR 1: dropping interior NaN rows leaves gaps in original time. A
    # positional Bartlett kernel treats those survivors as adjacent and
    # attenuates the HAC se. Time-indexed Gamma_j must disagree with that
    # contiguous-assumption se, and the published row must use the time
    # kernel and disclose the gap.
    y, shock, _ = lp.demo_series(seed=11, n=800)
    y = y.copy()
    y[300:340] = np.nan
    h = 5
    X, yv, idx = _horizon_arrays(y, shock, h)
    assert not lp._rows_contiguous(idx)
    assert int(np.max(np.diff(idx))) > 1
    beta, resid, _ = lp._ols(X, yv)
    n, k = X.shape
    dof = n - k
    lags = h + 1
    V_time = lp._hac_sandwich(X, resid, lags, time_index=idx)
    V_pos = lp._hac_sandwich(X, resid, lags)
    se_time = math.sqrt(max(V_time[1, 1] * n / dof, 0.0))
    se_pos = math.sqrt(max(V_pos[1, 1] * n / dof, 0.0))
    assert abs(se_time - se_pos) > 1e-8
    row = lp.estimate_horizon(y, shock, h, min_obs=100)
    assert row.get("abstained") is not True
    assert row["hac_rows_contiguous"] is False
    assert row["n_dropped_non_finite"] > 0
    assert abs(row["se"] - se_time) < 1e-12
    assert abs(row["se"] - se_pos) > 1e-8


def test_contiguous_panel_time_indexed_hac_matches_positional():
    y, shock, _ = lp.demo_series(seed=11, n=800)
    h = 5
    X, yv, idx = _horizon_arrays(y, shock, h)
    assert lp._rows_contiguous(idx)
    beta, resid, _ = lp._ols(X, yv)
    n, k = X.shape
    dof = n - k
    lags = h + 1
    V_time = lp._hac_sandwich(X, resid, lags, time_index=idx)
    V_pos = lp._hac_sandwich(X, resid, lags)
    se_time = math.sqrt(max(V_time[1, 1] * n / dof, 0.0))
    se_pos = math.sqrt(max(V_pos[1, 1] * n / dof, 0.0))
    assert abs(se_time - se_pos) < 1e-12
    row = lp.estimate_horizon(y, shock, h)
    assert row["hac_rows_contiguous"] is True
    assert abs(row["se"] - se_time) < 1e-12


def test_inference_discloses_normal_reference_and_ci_level():
    y, shock, _ = lp.demo_series(seed=11)
    result = lp.impulse_response(y, shock, horizons=2)
    inf = result["inference"]
    assert inf["reference_distribution"] == "normal"
    assert inf["ci_level"] == lp.CI_LEVEL
    row = result["irf"][0]
    z = 1.959963984540054
    width = row["ci_high"] - row["ci_low"]
    assert abs(width - 2.0 * z * row["se"]) < 1e-12


def test_multiple_testing_note_caveats_fwer_vintage_and_tested_denominator():
    y, shock, _ = lp.demo_series(seed=11)
    result = lp.impulse_response(y, shock, horizons=2)
    mt = result["multiple_testing"]
    note = mt["note"]
    assert mt["global_null_fwer_vintage"] == lp.GLOBAL_NULL_FWER_VINTAGE
    assert "historical" in note.lower()
    assert "not live-recomputed" in note
    assert "n_horizons_tested" in note
    assert "n_horizons_declared" in note
    assert mt["n_horizons_declared"] == 3
    assert mt["n_horizons_tested"] == 3
    # The note must name the tested-not-declared choice, not just echo keys.
    assert "shrink the multiplicity penalty" in note


# Registered CSV ingestion is a harness capability; these remain fixtures only.
def _registered_panel_bytes(n=90):
    from datetime import date, timedelta
    y, shock, _ = lp.demo_series(n=n, horizons=2, seed=91)
    rows = ["period,y,shock,known_at"]
    for i, (outcome, event) in enumerate(zip(y, shock)):
        day = date(2026, 1, 1) + timedelta(days=i)
        rows.append(f"{day.isoformat()},{float(outcome)!r},{float(event)!r},{day.isoformat()}T23:00:00Z")
    return ("\n".join(rows) + "\n").encode()


def test_registered_panel_parser_preserves_exact_bytes_and_clocks():
    import hashlib
    from datetime import datetime, timezone
    from scripts.run_local_projections import parse_panel
    raw = b"period,y,shock,known_at\r\n2026-01-01,1.25,-2,2026-01-02T07:00:00+08:00\r\n"
    panel = parse_panel(raw, datetime(2026, 1, 3, tzinfo=timezone.utc))
    assert panel == {"period": ["2026-01-01"], "y": [1.25], "shock": [-2.0],
                     "known_at": ["2026-01-01T23:00:00+00:00"],
                     "cutoff": "2026-01-03T00:00:00+00:00",
                     "input_sha256": hashlib.sha256(raw).hexdigest()}


@pytest.mark.parametrize("raw", [
    b"period,y,y,known_at\n2026-01-01,1,2,2026-01-02T00:00:00Z\n",
    b"period,y,shock,known_at\n2026-01-01,nan,2,2026-01-02T00:00:00Z\n",
    b"period,y,shock,known_at\n2026-01-01,1,inf,2026-01-02T00:00:00Z\n",
    b"period,y,shock,known_at\n2026-01-01,1,2,2026-01-02T00:00:00\n",
    b"period,y,shock,known_at\n2026-01-01,1,2,2026-02-02T00:00:00Z\n",
    b"period,y,shock,known_at\n2026-01-01,1,2,2025-12-31T23:59:59Z\n",
    b"period,y,shock,known_at\n2026-01-02,1,2,2026-01-02T23:00:00Z\n2026-01-01,2,3,2026-01-02T00:00:00Z\n",
    b"period,y,shock,known_at\n2026-01-01,1,2,2026-01-02T00:00:00Z\n2026-01-01,2,3,2026-01-02T00:00:00Z\n",
    b'period,y,shock,known_at\n2026-01-01,"1,2,2026-01-02T00:00:00Z\n',
    b"period,y,shock,known_at\n2026-01-01,1,2,2026-01-02T00:00:00Z,extra\n",
    b"period,y,shock,known_at\n\n",
    b"period,y,shock,known_at\n",
    b"\xff", b"period,y,shock,known_at\n\x00", b"x" * (8 * 1024 * 1024 + 1),
], ids=["duplicate-header", "nan", "infinity", "naive-clock", "future-clock",
         "clock-before-period", "unordered", "duplicate-period", "malformed-csv",
         "extra-field", "blank-row", "empty", "encoding", "nul", "oversize"])
def test_registered_panel_refuses_invalid_input_before_registration(raw):
    from datetime import datetime, timezone
    from scripts.run_local_projections import PanelInputError, run_panel
    class NoWrites:
        def log_trial(self, *args, **kwargs):
            pytest.fail("invalid input spent a trial")
    with pytest.raises(PanelInputError):
        run_panel(raw, cutoff=datetime(2026, 1, 4, tzinfo=timezone.utc),
                  family="fixture-only", ledger=NoWrites(), horizons=2, lags=1)


def test_registered_panel_registers_exact_config_before_estimator(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from engine.trial_ledger import TrialLedger
    import scripts.run_local_projections as harness
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("")
    ledger = TrialLedger(path)
    actual = lp.impulse_response
    observed = []
    def estimate(y, shock, **kwargs):
        cold = TrialLedger(path)
        assert cold.literal_n("fixture-only") == 1
        assert kwargs["family"] == "fixture-only" and kwargs["ledger"] is ledger
        observed.append(True)
        return actual(y, shock, **kwargs)
    monkeypatch.setattr(harness.lp, "impulse_response", estimate)
    raw = _registered_panel_bytes()
    envelope = harness.run_panel(raw, cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                                 family="fixture-only", ledger=ledger, horizons=2, lags=1)
    assert observed == [True]
    assert envelope["schema"] == "mastermind.local_projection_run/v1"
    assert envelope["input"]["input_sha256"] == __import__("hashlib").sha256(raw).hexdigest()
    assert envelope["result"]["multiple_testing"]["effective_n"] == 1
    assert envelope["authority"] == {"research_only": True, "causal": False,
                                     "signal": False, "sizing": False, "execution": False,
                                     "publication": False}
    assert "source-supplied" in envelope["limitations"]
    before = path.read_bytes()
    harness.run_panel(raw, cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                      family="fixture-only", ledger=ledger, horizons=2, lags=1)
    assert path.read_bytes() == before  # identical configuration does not spend twice


def test_registered_panel_registration_failure_never_estimates(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    import scripts.run_local_projections as harness
    from engine.trial_ledger import TrialLedger
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("")
    ledger = TrialLedger(path)
    def failed_registration(*args, **kwargs):
        raise OSError("retained storage failure")
    monkeypatch.setattr(ledger, "log_trial", failed_registration)
    monkeypatch.setattr(harness.lp, "impulse_response", lambda *a, **k: pytest.fail("estimated after failed registration"))
    with pytest.raises(OSError, match="retained storage failure"):
        harness.run_panel(_registered_panel_bytes(), cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                          family="fixture-only", ledger=ledger, horizons=2, lags=1)


@pytest.mark.parametrize("setting,value", [("horizons", True), ("horizons", -1),
    ("horizons", 61), ("lags", 0), ("embargo", 0), ("min_obs", 2)])
def test_registered_panel_invalid_settings_spend_no_trial(tmp_path, setting, value):
    from datetime import datetime, timezone
    from engine.trial_ledger import TrialLedger
    from scripts.run_local_projections import PanelInputError, run_panel
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("")
    with pytest.raises(PanelInputError):
        run_panel(_registered_panel_bytes(), cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                  family="fixture-only", ledger=TrialLedger(path), **{setting: value})
    assert path.read_bytes() == b""


def test_registered_panel_cli_requires_explicit_existing_store(tmp_path, capsys):
    from scripts.run_local_projections import main
    source = tmp_path / "panel.csv"
    source.write_bytes(_registered_panel_bytes())
    missing = tmp_path / "unapproved-new-ledger.jsonl"
    assert main(["--input", str(source), "--cutoff", "2026-05-01T00:00:00Z",
                 "--family", "fixture-only", "--ledger", str(missing)]) == 2
    assert not missing.exists()
    captured = capsys.readouterr()
    assert captured.out == "" and "existing approved trial ledger" in captured.err


def test_registered_panel_naive_cutoff_and_corrupt_ledger_refuse(tmp_path):
    from datetime import datetime, timezone
    from engine.trial_ledger import TrialLedger
    from scripts.run_local_projections import PanelInputError, run_panel
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("not-json\n")
    original = path.read_bytes()
    for cutoff in (datetime(2026, 5, 1), datetime(2026, 5, 1, tzinfo=timezone.utc)):
        with pytest.raises(PanelInputError):
            run_panel(_registered_panel_bytes(), cutoff=cutoff, family="fixture-only",
                      ledger=TrialLedger(path), horizons=2, lags=1)
    assert path.read_bytes() == original


def test_registered_panel_cli_consumes_fixture_without_publishing(tmp_path, capsys):
    import json
    from scripts.run_local_projections import main
    source = tmp_path / "fixture-panel.csv"
    source.write_bytes(_registered_panel_bytes())
    ledger = tmp_path / "fixture-ledger.jsonl"
    ledger.write_text("")
    assert main(["--input", str(source), "--cutoff", "2026-05-01T00:00:00Z",
                 "--family", "fixture-only", "--ledger", str(ledger),
                 "--horizons", "2", "--lags", "1"]) == 0
    capture = capsys.readouterr()
    envelope = json.loads(capture.out)
    assert capture.err == ""
    assert len(envelope["result"]["irf"]) == 3
    assert envelope["registration"]["effective_n"] == 1
    assert envelope["authority"]["publication"] is False
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        ".fixture-ledger.jsonl.lock", "fixture-ledger.jsonl", "fixture-panel.csv"]


def test_registered_panel_preserves_typed_abstention(tmp_path):
    from datetime import datetime, timezone
    from engine.trial_ledger import TrialLedger
    from scripts.run_local_projections import run_panel
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("")
    envelope = run_panel(_registered_panel_bytes(), cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                         family="fixture-only", ledger=TrialLedger(path), horizons=2,
                         lags=1, min_obs=200)
    result = envelope["result"]
    assert all(row["abstained"] and row["reason"] for row in result["irf"])
    assert result["null"]["any_horizon_rejects"] is False
    assert result["null"]["rejecting_horizons"] == []
    assert envelope["authority"]["signal"] is False


def test_registered_panel_configuration_changes_accumulate_search_count(tmp_path):
    from datetime import datetime, timezone
    from engine.trial_ledger import TrialLedger
    from scripts.run_local_projections import run_panel
    path = tmp_path / "fixture-ledger.jsonl"
    path.write_text("")
    ledger = TrialLedger(path)
    raw = _registered_panel_bytes()
    for lags in (1, 2):
        envelope = run_panel(raw, cutoff=datetime(2026, 5, 1, tzinfo=timezone.utc),
                             family="fixture-only", ledger=ledger, horizons=2, lags=lags)
    assert TrialLedger(path).literal_n("fixture-only") == 2
    assert envelope["result"]["multiple_testing"]["effective_n"] == 2
    assert envelope["registration"]["new_trial_logged"] is True


@pytest.mark.parametrize("period,known", [
    ("２０２６-０１-０１", "2026-01-02T00:00:00Z"),
    ("2026-01-01", "２０２６-０１-０２T00:00:00Z"),
    ("2026-01-01", "9999-12-31T23:00:00-23:00"),
])
def test_registered_panel_invalid_iso_and_utc_overflow_are_typed(period, known):
    from datetime import datetime, timezone
    from scripts.run_local_projections import PanelInputError, parse_panel
    raw = f"period,y,shock,known_at\n{period},1,2,{known}\n".encode()
    with pytest.raises(PanelInputError):
        parse_panel(raw, datetime(2026, 5, 1, tzinfo=timezone.utc))


def test_registered_panel_row_limit_does_not_filter(monkeypatch):
    from datetime import datetime, timezone
    import scripts.run_local_projections as harness
    monkeypatch.setattr(harness, "_MAX_ROWS", 2)
    with pytest.raises(harness.PanelInputError, match="more than 2 data rows"):
        harness.parse_panel(_registered_panel_bytes(3), datetime(2026, 5, 1, tzinfo=timezone.utc))


def test_registered_panel_requires_immutable_source_bytes():
    from datetime import datetime, timezone
    from scripts.run_local_projections import PanelInputError, parse_panel
    with pytest.raises(PanelInputError, match="raw must be bytes"):
        parse_panel(bytearray(_registered_panel_bytes()),
                    datetime(2026, 5, 1, tzinfo=timezone.utc))


# Frozen ALFRED source-panel custody and asof guards (no estimator in these cases).
import math
import pandas as pd
import pytest
from scripts.local_projection_alfred_panel import assemble_panel


def _alfred_frames():
    cpi = pd.DataFrame([
        ("1997-12-01", "1998-01-14", 100.),
        ("1998-01-01", "1998-02-13", 101.),
        ("1998-01-01", "1998-03-13", 900.),
        ("1998-02-01", "1998-03-13", 102.),
        ("1998-02-01", "1998-04-13", 999.),
    ], columns=["period", "realtime_start", "value"])
    payroll = pd.DataFrame([
        ("1998-01-01", "1998-02-06", 1000.),
        ("1998-01-01", "1998-03-06", 9000.),
        ("1998-02-01", "1998-03-06", 1005.),
        ("1998-02-01", "1998-04-03", 9000.),
    ], columns=cpi.columns)
    return cpi, payroll


def _alfred_run(cpi, payroll):
    return assemble_panel(cpi, payroll, "1998-01-01", "1998-02-01")


def test_alfred_asof_excludes_later_revisions_and_preserves_input():
    cpi, payroll = _alfred_frames()
    before = (cpi.copy(deep=True), payroll.copy(deep=True))
    raw, meta = _alfred_run(cpi, payroll)
    rows = raw.decode().splitlines()
    assert len(rows) == 3
    first = rows[1].split(",")
    assert first[0] == "1998-02-13"
    assert float(first[1]) == pytest.approx(math.log(1000))
    assert float(first[2]) == pytest.approx(100*math.log(101/100))
    assert first[3] == "1998-02-15T00:00:00+00:00"
    assert meta["rows"][0]["payroll_vintage"] == "1998-02-06"
    pd.testing.assert_frame_equal(cpi, before[0])
    pd.testing.assert_frame_equal(payroll, before[1])


@pytest.mark.parametrize("change", ["missing", "late", "duplicate", "nan", "zero", "future_payroll"])
def test_alfred_invalid_prerequisite_refuses_whole_panel(change):
    cpi, payroll = _alfred_frames()
    if change == "missing": cpi = cpi[cpi.period != "1998-02-01"]
    elif change == "late": cpi.loc[cpi.period == "1998-01-01", "realtime_start"] = "1998-05-13"
    elif change == "duplicate": cpi = pd.concat([cpi,cpi.iloc[[0]]])
    elif change == "nan": cpi.loc[1,"value"] = float("nan")
    elif change == "zero": payroll.loc[0,"value"] = 0.
    elif change == "future_payroll": payroll.loc[payroll.period == "1998-01-01","realtime_start"] = "1998-05-01"
    with pytest.raises(ValueError): _alfred_run(cpi,payroll)


def test_alfred_intraday_source_precision_is_not_silently_invented():
    cpi,payroll = _alfred_frames()
    cpi.loc[1,"realtime_start"] = "1998-02-13T08:30:00"
    with pytest.raises(ValueError): _alfred_run(cpi,payroll)


def test_alfred_every_frozen_month_is_required():
    cpi,payroll = _alfred_frames()
    with pytest.raises(ValueError): assemble_panel(cpi,payroll,"1998-01-01","1998-03-01")
