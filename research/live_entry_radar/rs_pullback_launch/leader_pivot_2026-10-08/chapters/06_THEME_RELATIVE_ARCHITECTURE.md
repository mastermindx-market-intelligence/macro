# 06 | Theme-relative architecture

## Separate identity, state and performance

GMI owns theme/subtheme identity, membership vintages and ThemeState. The research consumer owns neither a second graph nor an alternative authoritative theme state. It consumes source references and computes only approved, reproducible research measurements. Membership, group leadership, the subject's own leadership and the subject's residual response are four different objects. [I20]

Maintain the hierarchy `market → sector → industry → theme → subtheme → security`, but do not assume it is a strict tree. A security can participate in several overlapping themes. Use canonical primary membership when available, or one globally frozen weighting rule; never select whichever theme later makes the stock look strongest. Print overlap, concentration and membership support.

## Ex-self benchmark: an exact construction requirement

For simple interval returns and weights fixed at the interval's start:

```text
R_group,-i(t) = Σ[j≠i] w_j(t−1) r_j(t) / Σ[j≠i] w_j(t−1)
```

With normalized inclusive subject weight `w_i`:

```text
r_i − R_group = (1 − w_i) × (r_i − R_group,-i)
```

The inclusive comparison mechanically attenuates the subject's relative move. In the executed example, a 40% member's true ex-self relative outperformance of 1.0 percentage point appears as only 0.6 point against the inclusive group. This is algebra, not an estimated market effect. Self-inclusion also complicates interpretation when the same basket is a regression factor. [M01]

Remove the subject from **every relevant group-return and group-breadth construction**, including a parent used for shrinkage. In a tested toy example, a 50% shrink toward a parent with 40% subject weight reintroduced a 20% loading on the subject's own return. Excluding it from the immediate subtheme alone was insufficient. [M01]

Market ETFs can remain named primitive market controls. That is not a claim that they are ex-self. A theme benchmark shrunk toward an inclusive sector ETF must be labeled as such and excluded from the primary fully-ex-self contrast unless a qualified ex-self parent basket can be supplied. Do not silently manufacture a new index to remove this limitation.

## Small and concentrated groups

Report effective support, not just headcount:

```text
N_eff = (Σw)^2 / Σ(w^2)
```

Three names weighted 90%/5%/5% have effective support about 1.227, not three independent peer observations. There are no independent votes merely because the members have different tickers. [M01]

Proposed, outcome-unseen research rule: fewer than two eligible ex-self members means no direct group estimate. Otherwise use a fixed support shrinkage `λ = N_eff / (N_eff + 5)` toward a qualified ex-self parent; display `DIRECT_THIN` when `N_eff < 3`. The value 5 and the thin-support threshold are **engineering priors**, not learned truths. Compare the frozen shrinkage once against a parent-only control; do not tune them to rescue returns. An unavailable parent yields an explicit thin/unresolved state, not a manufactured zero residual.

Lag weights and memberships. Stale or absent prices are missing, not zero returns. Primary group intervals require the entire predeclared eligible-weight set to be accounted for by valid observations or owner-qualified no-trade semantics. Renormalizing over the convenient observed survivors is a different estimand and may be reported only as a separate coverage sensitivity. Never use future delisting knowledge to clean the original universe.

For canonical ThemeState that includes the subject, retain that original state and disclose self-weight/dependency. Do not privately replace it with a second ex-self authoritative state. A state-contribution or ex-self research projection needs the GMI owner's accepted interface.

## Trailing residual model

Use synchronized, completed five-minute **simple returns** as the initial residual measurement lattice, reconstructed from the same admitted minute plane:

```text
r_i,t = α_(t−1) + β_m,(t−1) r_market,t
                 + β_s,(t−1) r_sector,t
                 + β_g,(t−1) R_group,-i,t + ε_i,t
```

The first registered exposure recipe should fit once before the current session on the preceding 20 complete RTH sessions, require at least 10 supported sessions and 500 synchronized observations, and freeze its parameters for that session. These support values are proposed safeguards, not empirical optimality claims. A later intraday-update variant would be a separately counted challenger.

Use one global ridge recipe: standardize using that trailing window only; minimize the sum of squared standardized residuals plus `10 × Σβ²`, leaving the intercept unpenalized; transform coefficients back to return units. No ticker-specific choice of window, penalty or factors. Diagnose collinearity, unstable loadings and source gaps; abstain when the required support fails. Market, sector and group factors overlap economically, so coefficient signs must not be sold as causal attributions.

The simple-return basket identity above is exact under its stated weights. A sum of fitted residual returns is a statistical cumulative residual measurement, not the return of an executable self-financing portfolio. A relative wealth curve, when needed, should explicitly compound its stock and benchmark legs rather than conflating them with that residual sum.

Candidate measurements are cumulative residual damage since the episode origin, residual drawdown, 30/60-minute residual slope and repair relative to a fixed causal stock-price anchor. Every anchor and fitted exposure must have been knowable before the current observation. Compare residual values at those fixed stock anchors; do not independently choose favorable future residual troughs and line them up afterward.

## Do not give deterministic transformations fake information credit

When B0 already contains the complete primitive history, a ratio, residual or multi-timeframe transformation cannot add new underlying information. It can still improve finite-sample representation, regularization, stability, interpretability or computation. That is the claim to test.

Use two separate comparisons:

**Representation increment:** B0 already has the same stock/group returns, exposure estimates and relevant interaction primitives. Compare an explicitly derived residual/repair representation at matched model capacity.

**Source increment:** remove the dynamic theme source and all of its descendants together, then compare against the stable-group baseline. This tests new source value rather than giving every derived theme field independent credit. Preserve both DROP_REPRESENTATION and DROP_SOURCE_CLOSURE views. [I07]

## Historical versus prospective theme evidence

Historical development may use only admitted sector/industry history or frozen peer constructions with demonstrable known-at membership. An annually updated or current industry map is not automatically PIT. Dynamic GMI themes/subthemes belong in recent or prospective comparisons wherever their original memberships and state receipts actually exist. Use a common cohort and matched source coverage when comparing stable versus dynamic groups. [I20, E08]

Do not backfill current GMI membership onto old winners. Do not compare a recent dynamic-theme model to a historical sector model on a different era and call the difference theme skill. Preserve explicit `HISTORICAL_STABLE_GROUP`, `RECENT_PIT_THEME` and `PROSPECTIVE_THEME` evidence scopes.

## Resilience versus laggard weakness

Constructive evidence would combine an independently qualified leader, common adverse group shock, smaller-than-expected subject damage, residual repair and still-supported group structure. The rival pattern is peers recovering while the subject returns to its own low with worsening residuals. These descriptions are measurements, not proven outcome classes. The PSS peer studies prohibit relabeling the inspected laggard negatives into a new trade without genuinely new preregistered evidence. [I19]

A stock's positive residual while its whole theme deteriorates is also not automatically a good long entry. Relative resilience and absolute path risk must remain distinct heads. This is why the product should not collapse theme permission, residual repair and pivot structure into a single score.
