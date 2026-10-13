from __future__ import annotations

"""Hermetic tests for the Q10 research reference (synthetic integer-indexed data only)."""

import math

import numpy as np
import pandas as pd
import pytest

import engine.offexchange_conditional_residual as m


def _panel(n_issuers=50, n_days=400, seed=0, market_shock_days=(), issuer_shock=None,
           shock=0.8, noise=0.10, train_shocks=True):
    rng = np.random.default_rng(seed)
    mkt = np.cumsum(rng.normal(0, 0.01, n_days))
    if train_shocks:
        for k in range(30, int(n_days * 0.7), 23):
            mkt[k] += rng.choice([-0.5, 0.5])
    for k in market_shock_days:
        mkt[k] += shock
    rows = []
    for i in range(n_issuers):
        base = rng.normal(-0.4, 0.4)
        for t in range(n_days):
            lv = rng.normal(0, 0.3)
            V = float(np.round(np.exp(13 + lv)))
            z = base + mkt[t] + 0.15 * lv + rng.normal(0, noise)
            if issuer_shock is not None and issuer_shock == (i, t):
                z += shock
            p = 1.0 / (1.0 + math.exp(-z))
            rows.append((t, f"I{i:03d}", float(np.round(p * V)), V))
    return pd.DataFrame(rows, columns=["date", "issuer", "offex_shares", "cons_shares"])


@pytest.fixture(scope="module")
def shocked():
    df = _panel(market_shock_days=(350,), issuer_shock=(0, 360))
    params = m.fit_conditional_model(df[df["date"] < 280])
    return df, params, m.score_panel(df, params)


# ── requirement 1: valid 0/1 supported; ratios outside [0,1] are bad measurement ─────

def test_req1_zero_and_one_are_valid_and_finite():
    p, st = m.classify_participation([0.0, 500.0, 250.0], [500.0, 500.0, 500.0])
    assert list(st) == [m.VALID, m.VALID, m.VALID]
    assert p[0] == 0.0 and p[1] == 1.0
    z = m.empirical_logit([0.0, 500.0], [500.0, 500.0])
    assert np.all(np.isfinite(z)) and z[0] < 0 < z[1]


def test_req1_out_of_range_ratios_are_invalid_never_clipped():
    p, st = m.classify_participation([600.0, -1.0, 10.0, np.nan], [500.0, 500.0, 0.0, 10.0])
    assert list(st) == [m.INVALID_RATIO, m.INVALID_RATIO, m.INVALID_DENOMINATOR, m.MISSING]
    assert np.all(np.isnan(p))  # not clipped to 1.0 / 0.0
    assert np.all(np.isnan(m.empirical_logit([600.0], [500.0])))


def test_req1_invalid_rows_never_enter_history():
    df = _panel(n_issuers=40, n_days=200, seed=3)
    df2 = df.copy()
    hit = (df2["issuer"] == "I000") & (df2["date"] == 150)
    df2.loc[hit, "offex_shares"] = df2.loc[hit, "cons_shares"] * 3.0  # ratio 3 → invalid
    params = m.fit_conditional_model(df[df["date"] < 140])
    a = m.score_panel(df, params)
    b = m.score_panel(df2, params)
    rb = b[(b["issuer"] == "I000") & (b["date"] == 150)].iloc[0]
    assert rb["status"] == m.INVALID_RATIO and np.isnan(rb["p"]) and np.isnan(rb["lo90"])
    # the next session's issuer level ignores the invalid row (one fewer observation)
    na = a[(a["issuer"] == "I000") & (a["date"] == 151)].iloc[0]
    nb = b[(b["issuer"] == "I000") & (b["date"] == 151)].iloc[0]
    assert nb["n_level"] == na["n_level"] - 1


def test_req1_bounds_map_back_inside_unit_interval():
    v = np.array([10.0, 1000.0, 1e7])
    lo = m.inverse_empirical_logit(np.array([-50.0, -50.0, -50.0]), v)
    hi = m.inverse_empirical_logit(np.array([50.0, 50.0, 50.0]), v)
    assert np.all(lo == 0.0) and np.all(hi == 1.0)
    x = np.array([3.0, 400.0, 2e6])
    back = m.inverse_empirical_logit(m.empirical_logit(x, v), v)
    assert np.allclose(back, x / v)


# ── requirement 2: a common market-wide shift is not called issuer-specific ──────────

def test_req2_market_shift_is_absorbed_but_issuer_shift_is_not(shocked):
    df, params, out = shocked
    assert 0.7 < params.coef[1] < 1.3  # market loading learned in training
    day = out[(out["date"] == 350) & (out["status"] == m.SCORED_FULL)]
    assert len(day) >= 40
    assert (day["pit"] >= 0.95).mean() < 0.25
    # the incumbent own-history construction flags most issuers on the same session
    zs = []
    for _, g in df.groupby("issuer"):
        g = g.sort_values("date")
        p = (g["offex_shares"] / g["cons_shares"]).to_numpy()
        c, s, _ = m.incumbent_baseline(p)
        zs.append((p[350] - c[350]) / s[350])
    assert np.mean(np.asarray(zs) >= 1.5) > 0.75
    own = out[(out["date"] == 360) & (out["issuer"] == "I000")].iloc[0]
    assert own["status"] == m.SCORED_FULL and own["pit"] >= 0.95


def test_req2_leave_one_out_median_matches_brute_force():
    rng = np.random.default_rng(7)
    for n in (2, 3, 4, 7, 10, 31):
        v = rng.normal(size=n)
        c = rng.random(n) < 0.8
        c[:2] = True
        got, used = m.loo_median(v, c)
        idx = np.flatnonzero(c)
        for j in range(n):
            if c[j]:
                ref = np.median(v[[k for k in idx if k != j]]) if idx.size > 1 else np.nan
                assert (np.isnan(ref) and np.isnan(got[j])) or abs(got[j] - ref) < 1e-12
                assert used[j] == idx.size - 1
            else:
                assert abs(got[j] - np.median(v[idx])) < 1e-12


# ── requirement 3: split / denominator changes excluded ─────────────────────────────

def test_req3_unit_break_truncates_pre_break_history():
    rng = np.random.default_rng(1)
    p = np.r_[rng.normal(0.04, 0.003, 120), rng.normal(0.40, 0.03, 120)]
    b = m.last_level_break(p)
    # incumbent arithmetic: last flagged comparison + window → conservative (≤ ~2 windows late)
    assert b is not None and 120 <= b <= 120 + 2 * m.BREAK_WINDOW
    mask = m.unit_consistent_mask(p)
    assert not mask[:120].any() and mask[-60:].all()
    assert m.last_level_break(rng.normal(0.4, 0.03, 240)) is None


def test_req3_split_rows_are_excluded_in_scoring_and_event_mask_overrides():
    df = _panel(n_issuers=40, n_days=320, seed=5)
    sel = (df["issuer"] == "I001") & (df["date"] < 150)
    df.loc[sel, "offex_shares"] = np.round(df.loc[sel, "offex_shares"] / 10.0)  # ÷10 history
    params = m.fit_conditional_model(df[df["date"] < 250])
    out = m.score_panel(df, params)
    g = out[out["issuer"] == "I001"].sort_values("date")
    assert (g["status"].to_numpy()[:140] == m.EXCLUDED_SPLIT).all()
    later = g[g["date"] == 300].iloc[0]
    assert later["n_level"] <= 300 - 140
    ev = m.known_event_mask(10, [4])
    assert list(ev) == [False] * 4 + [True] * 6
    assert m.known_event_mask(5, []).all()


# ── requirement 4: thin/unseen issuers pooled or abstain with disclosed support ──────

def test_req4_thin_issuers_pool_and_unseen_abstain():
    df = _panel(n_issuers=45, n_days=300, seed=9)
    keep = ~((df["issuer"] == "I000") & (df["date"] < 280))  # 20 sessions of history at end
    keep &= ~((df["issuer"] == "I001") & (df["date"] < 295))  # 5 sessions
    keep &= ~((df["issuer"] == "I003") & (df["date"] < 289))  # 10 prior obs at session 299
    keep &= ~((df["issuer"] == "I004") & (df["date"] < 288))  # 11 prior obs at session 299
    df = df[keep].reset_index(drop=True)
    params = m.fit_conditional_model(df[df["date"] < 250])
    out = m.score_panel(df, params)
    thin = out[(out["issuer"] == "I000") & (out["date"] == 299)].iloc[0]
    assert thin["status"] == m.SCORED_POOLED
    assert thin["n_level"] == 19 and 0.0 < thin["pool_weight"] <= 1.0
    fresh = out[(out["issuer"] == "I001") & (out["date"] == 299)].iloc[0]
    assert fresh["status"] == m.ABSTAIN_NO_SUPPORT and np.isnan(fresh["lo90"])
    full = out[(out["issuer"] == "I002") & (out["date"] == 299)].iloc[0]
    assert full["status"] == m.SCORED_FULL and full["pool_weight"] < thin["pool_weight"]
    assert thin["scale"] > 0 and full["scale"] > 0
    # location inflation, discriminated at matched dispersion: I003/I004 have too few residuals
    # for an own scale (pool_weight == 1), so both carry exactly the session's pooled scale and
    # their scales differ only by sqrt(1 + pi / (2 n_level)).
    a = out[(out["issuer"] == "I003") & (out["date"] == 299)].iloc[0]
    b = out[(out["issuer"] == "I004") & (out["date"] == 299)].iloc[0]
    assert a["status"] == b["status"] == m.SCORED_POOLED
    assert a["n_level"] == 10 and b["n_level"] == 11
    assert a["pool_weight"] == 1.0 and b["pool_weight"] == 1.0
    infl = lambda n: math.sqrt(1.0 + math.pi / (2.0 * n))  # noqa: E731
    assert abs(b["scale"] / a["scale"] - infl(11) / infl(10)) < 1e-9
    assert a["scale"] > b["scale"]
    # all synthetic issuers share one dispersion, so the fully pooled thin interval is wider
    # on the logit scale than the typical FULL issuer's on the same session
    day_full = out[(out["date"] == 299) & (out["status"] == m.SCORED_FULL)]
    assert len(day_full) >= 30
    assert a["scale"] > 1.03 * float(day_full["scale"].median())


def test_req4_market_factor_abstains_without_enough_contributors():
    df = _panel(n_issuers=45, n_days=260, seed=11)
    params = m.fit_conditional_model(df[df["date"] < 230])
    small = df[df["issuer"].isin([f"I{i:03d}" for i in range(10)])].reset_index(drop=True)
    out = m.score_panel(small, params)
    late = out[out["date"] > 100]
    assert (late["status"] == m.ABSTAIN_NO_MARKET).all()


# ── requirement 5: held-out calibration measured against the robust baseline ─────────

def test_req5_incumbent_baseline_formula():
    p = np.r_[np.linspace(0.30, 0.50, 41), 0.6]
    c, s, n = m.incumbent_baseline(p)
    hist = p[:41]
    med = np.median(hist)
    mad = np.median(np.abs(hist - med)) * 1.4826
    assert abs(c[41] - med) < 1e-12 and abs(s[41] - mad) < 1e-12 and n[41] == 41
    assert np.isnan(c[39]) and np.isnan(s[39])  # below min_obs → honest null
    flat = np.r_[np.full(30, 0.4), np.full(15, 0.41), 0.5]
    c2, s2, _ = m.incumbent_baseline(flat)
    assert abs(s2[45] - np.std(flat[:45])) < 1e-12  # MAD = 0 → σ fallback


def test_req5_heldout_coverage_near_nominal_and_scoring_rule():
    df = _panel(n_issuers=50, n_days=420, seed=2)
    params = m.fit_conditional_model(df[df["date"] < 300])
    out = m.score_panel(df, params)
    te = out[(out["date"] >= 300) & (out["status"] == m.SCORED_FULL)]
    cov90 = ((te["p"] >= te["lo90"]) & (te["p"] <= te["hi90"])).mean()
    cov50 = ((te["p"] >= te["lo50"]) & (te["p"] <= te["hi50"])).mean()
    assert abs(cov90 - 0.90) < 0.04 and abs(cov50 - 0.50) < 0.06
    s = m.interval_score(np.array([0.2]), np.array([0.4]), np.array([0.5]), 0.1)
    assert abs(s[0] - (0.2 + 20 * 0.1)) < 1e-12


def test_req5_block_bootstrap_is_deterministic_and_dependence_aware():
    x = np.arange(100, dtype=float)
    a = m.moving_block_bootstrap([x], block=10, reps=50, seed=4, stat=lambda s: s[0].mean())
    b = m.moving_block_bootstrap([x], block=10, reps=50, seed=4, stat=lambda s: s[0].mean())
    assert np.array_equal(a, b) and a.shape == (50,)
    # dependence-aware: every replicate is built from contiguous runs of length `block`
    # (an iid bootstrap would break these runs)
    seen = []

    def grab(s):
        seen.append(s[0].copy())
        return 0.0

    m.moving_block_bootstrap([x], block=10, reps=20, seed=4, stat=grab)
    assert len(seen) == 20
    for res in seen:
        runs = res.reshape(10, 10)
        assert np.all(np.diff(runs, axis=1) == 1.0)
        assert np.all((runs[:, 0] >= 0) & (runs[:, 0] <= 90))
    seen.clear()
    m.moving_block_bootstrap([np.arange(95, dtype=float)], block=10, reps=10, seed=1, stat=grab)
    for res in seen:
        assert res.size == 95
        for k in range(0, 95, 10):
            assert np.all(np.diff(res[k:k + 10]) == 1.0)
    with pytest.raises(ValueError):
        m.moving_block_bootstrap([x, x[:5]], block=10, reps=5, seed=0, stat=lambda s: 0.0)


# ── requirement 6: no direction, owner inference or fusion ───────────────────────────

FORBIDDEN = ("buy", "sell", "direction", "bull", "bear", "owner", "intent", "inventory",
             "signal", "alpha", "rank", "fused", "composite", "short_interest")


def test_req6_outputs_carry_no_direction_owner_or_fusion_fields(shocked):
    _, _, out = shocked
    cols = [c.lower() for c in out.columns]
    assert tuple(out.columns) == m.OUTPUT_COLUMNS
    for c in cols:
        assert not any(f in c for f in FORBIDDEN), c
    public = [n.lower() for n in dir(m) if not n.startswith("_")]
    for n in public:
        assert not any(f in n for f in FORBIDDEN), n


# ── contract: no silent activation ───────────────────────────────────────────────────

def test_no_silent_activation_contract():
    assert m.RESEARCH_ONLY is True
    assert m.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "VERDICT" in m.__doc__
    ns = vars(m)
    for banned in ("os", "subprocess", "requests", "urllib", "socket", "Path", "open_file",
                   "register", "main", "schedule", "promote", "activate"):
        assert banned not in ns, banned
    mods = {getattr(v, "__name__", "") for v in ns.values() if type(v).__name__ == "module"}
    assert mods <= {"math", "warnings", "numpy", "pandas"}, mods
