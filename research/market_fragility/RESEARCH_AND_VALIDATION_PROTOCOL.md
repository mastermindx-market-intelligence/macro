# Market fragility: mechanism, evidence, contract and validation

Status: descriptive implementation; predictive usefulness NOT ESTABLISHED. This document does not authorize trades, ranking changes, position sizing or a replacement risk engine.

## 1. What is supported, and what is not

A negative dealer-gamma position can create hedging in the direction of an existing price move. That is a conditional two-sided amplification mechanism, not a negative expected-return forecast. Long gamma can provide counter-move hedging, but cannot guarantee a quiet market. The mechanism depends on net inventory, hedge implementation, competing flows and executable liquidity. Gross options volume alone does not identify the required net hedge [S1].

The supplied VolSignals image is in Gamma mode. Its documentation describes red as short gamma and green as long gamma, and claims the platform displays actual market-maker positions. That is the vendor's stated basis; this implementation has not acquired or independently verified that inventory feed. Charm-mode colors have a different interpretation. Do not copy a heatmap, its apparent contour trajectories, or its proprietary inference into an unsupported numerical signal [S2].

The strongest useful counterevidence is Cboe's own 0DTE work: its May 2025 report describes balanced customer flow and relatively small net gamma hedging despite very large gross volume [S3]. This concerns that product and period, not all expiries, all dealers or November 2026. It rejects the shortcut "large options volume proves an impending crash," not every gamma-feedback mechanism.

Amaya, Garcia-Ares, Pearson and Vasquez study intraday SPX option positions using proprietary transaction data. Their empirical setting supports testing inventory-dependent volatility effects, but is not validation of Mastermind's daily open-interest proxy or of directional alpha [S4].

VVIX is a volatility-of-volatility index associated with VIX options. It is a separate observation, not evidence supplied by a red gamma chart and not a literal measured third derivative merely because a post says "vol of vol of vol" [S5].

**Conclusion:** test market structure as conditional fragility. Do not encode the author's rhetoric about an unprecedented prolonged regime as a data fact or a sell rule. News, realized volatility, liquidity withdrawal and price-driven changes in positioning are competing explanations and can also be common causes.

## 2. Exact internal data basis

The incumbent producer is `engine/gex_engine.py`, specifically `compute_gex`, `_gamma_flip` and `_gamma_regime_passport`. It assigns signs using an unobserved dealer long-call/short-put assumption. Its passport explicitly says assumption-basis and display-only. That limitation is now carried to every new observation and the Brain consumer.

`net_gex_bn` is the signed modeled dollar-gamma amount per a 1% underlying move, divided by one billion, with the upstream filtered chain and contract multiplier. It is not contracts, gross notional, a known actual futures order, or an amount directly comparable to a different vendor/product/expiry universe. We retain the upstream direct `gamma_regime` field; neither the coarse dollar-GEX sign nor distance to a gamma flip is substituted for it. In particular, a missing zero crossing does not imply a missing direct gamma sign.

Do not compare current SPX dollar magnitudes with percentiles from reconstructed SPY history. Do not call a day-to-day GEX difference the sensitivity to spot while holding inventory constant: inventory, expiry, IV and source coverage also change. The daily summary does not provide a fixed-inventory scenario surface, so `gamma_spot_sensitivity` is explicitly unavailable. A macro balance-sheet liquidity label is not executable order-book depth; `market_depth` is also unavailable.

The existing `engine.vol_regime` producer already publishes VIX, VVIX and the canonical VIX/VIX3M ratio. `engine.conditions` publishes realized volatility; `engine.regime.liquidity_quality` publishes macro liquidity. The new context reuses those observations, without their scores, sizing scalars, risk thresholds or unverified narrative forecasts. Each retains its own publication session. Frame dates are not upgraded to raw-input availability clocks. Shared inputs are not counted as independent votes.

## 3. Implemented source-to-consumer contract

`engine.market_fragility.observe` is a pure function returning `market_fragility/v1`. The scope is `gamma_structure_observation`. Its current state is `amplifying`, `damping` or `unknown`. The first two describe the assumed hedge-response sign, never expected price direction.

- The calendar is the incumbent `lib.nyse_calendar`, including its completed-session settlement boundary. No second calendar or scheduler exists.
- Current data must cover the latest expected completed session. An old reported sign is retained with its source date, but cannot classify today's state. Today's partial source observation is kept separate from completed-history metrics.
- A malformed latest label, future row, duplicate latest session, unusable source tier, invalid sign or inconsistent supplied clock cannot silently select an older favorable observation.
- Missing, invalid and duplicate sessions break history runs and adjacent-session transitions. The denominator is a fixed trailing 20 completed-session grid, not the last 20 non-null rows. Counts include observed short/long/unknown sessions, valid adjacent pairs, sign changes, terminal run, maximum positive run and observed regime runs. A full-window terminal run is left-censored, not an exact lifetime duration.
- A source session label, source observation clock, source availability clock and computation time are different fields. No missing availability clock is invented. A supplied clock cannot be future-dated, predate its source session, or put availability before observation.
- Numeric output is finite or null. Unknown does not become zero, calm, long gamma or an authorized risk-on state.
- Every output carries `display_only=true`, with directional signal, ranking, sizing, risk override and execution authority false. PIT qualification is false and predictive validation is `not_established`.

The existing `engine.market_gamma.fragility_snapshot` adapter reads `cboe/gex_SPX`. `engine.run` publishes `latest.market_fragility`, then adds separately dated sibling context after the existing vol-regime mirror. `scripts/build_market_structure.py` uses one coherent raw SPX read for the legacy gamma block and the added strict observation at `gamma.fragility`. Existing `market_gamma.view`, risk scores, validation gates and trading controllers are unchanged.

The paired Mastermind adapter `brain.market_fragility_context` validates this contract and rechecks age when `get_regime` is called. A snapshot does not stay fresh forever because its saved `age_sessions` was zero. The adapter rejects unsupported source/units/authority/validation claims. The MCP transport preserves the compact observation's qualifiers instead of truncating away the restrictions. Missing or malformed optional context does not replace the core macro regime.

## 4. Measured source audit, 2026-11-13

`PRODUCTION_SOURCE_AUDIT_2026-11-13.json` is generated by `scripts.audit_market_fragility`, not hand-authored. It binds the parsed data to the SHA-256 of the exact bounded byte snapshot. The retained source had 95 rows and SHA-256 `39a0ea3a33dabde22aefa65bcb5aa465e916bcdc95898773aea3410b46edda1c`. The last source session was November 12, current against the completed-session calendar at audit time. It reported short gamma, with `tier=full`, hence an assumption-based amplifying observation.

For October 16 through November 12, the 20-session grid has 15 observed sessions: 12 short and 3 long, with 5 unknown sessions. There are 13 observed adjacent pairs and 6 sign changes. These counts do not reproduce or verify an outside vendor's figures; differing inventory bases, coverage and products can disagree. The missing sessions must remain visible.

The same existing validation owner's read-only diagnostic reported:

- 5-session horizon: long bucket 50, short bucket 26; still building history against its 30-per-bucket floor.
- 10-session horizon: long bucket 50, short bucket 22; also building history.

Those are daily observations, not independent episodes, and the floor is not proof of statistical power. The source has no `available_at` or `observed_at` columns. A historical as-of argument cannot recreate missing vintages or establish an executable point-in-time backtest.

A separate M2 working mirror ended November 6 and was four sessions stale. It correctly produced `unknown`; it was not mistaken for production. Production's then-published VIX/VVIX mirror was dated November 10 while the regime core was November 12. The context contract exposes this mismatch rather than giving old volatility numbers the new gamma date.

## 5. Preregistered research protocol before any new policy influence

This is a specification for the incumbent research/validation owners, not a new promotion gate. `scripts/validate_gex.py` retains the existing GEX promotion decision. The audit command only calls its pure diagnostic, never its writer or gate publisher.

**Question.** Does the assumed gamma state, persistence or sign-switch history improve a specified forecast of future realized variation or path instability beyond what is already explained by volatility, momentum and liquidity context? A favorable result for realized variation is not directional alpha.

**Data admission.** Bind every observation to its actual immutable availability evidence, instrument, source revision, expiry filter, unit and correction history. Use the existing nightly market-structure ledger and source-publication owners where they preserve these facts; never write that ledger from an off-lane experiment. Reconstructed or subsequently revised snapshots may support explicitly labeled descriptive analysis, not an as-traded claim. Stop a predictive promotion when availability or universe lineage is missing.

**Endpoints, frozen before fitting.** Primary: next-session absolute log return and forward five-session realized volatility, with exactly named estimators and session completeness. Secondary: downside and upside excursions, and ten-session drawdown. Intraday reversal/whipsaw claims require admitted timestamped intraday bars; daily closes cannot answer that question. Preserve the initiating examples and evaluate the current regime as well as historical aggregate metrics.

**Comparators.** An unconditional baseline, a volatility-only baseline using trailing realized volatility and available implied-volatility observations, then gamma-only and volatility-plus-gamma ablations. Add persistence and sign transitions incrementally, not as many fitted thresholds selected on the full sample. Treat absent depth as absent, not a manufactured liquidity factor. Normalize magnitudes only within a compatible source history using training-period parameters.

**Splits and uncertainty.** Use chronological train/calibration/untouched test eras and walk-forward evaluation. Purge overlapping outcome windows at boundaries; do not randomly shuffle adjacent market days. Report observed dates and distinct contiguous episodes separately. Use episode/block-aware uncertainty and disclose effective sample limits, missingness by regime, unstable coefficients and overlap. Freeze and account for endpoint/feature/threshold multiplicity. A few large crisis days must not be silently allowed to dominate a supposedly general result.

**Falsifiers.** A volatility-only model matching the augmented model, inversion across held-out eras, gains disappearing after availability correction, dependence on gap-filling, no positive/negative state variation, or failure on the motivating live examples all prevent promotion. A result that only explains contemporaneous volatility is not a leading signal. Model estimates of hedge feedback do not establish that those hedges caused an observed selloff.

**Decision.** No new numerical confidence multiplier, portfolio weight, stop or execution rule is implemented by this release. A later policy-specific change needs the incumbent owner's required validation and acceptance, including costs, calibration, tail behavior and prospective evidence. Negative/null results remain useful and must be retained rather than retuned away.

## 6. Operations and proof

Read-only audit:

```sh
python3 -m scripts.audit_market_fragility --input <retained-SPX-summary.parquet> --require-current
python3 -m scripts.audit_market_fragility --input <retained-SPX-summary.parquet> --run-existing-gex-diagnostic --output <new-audit.json>
```

An output path is exclusive-create: an existing evidence file is not overwritten. Input size is bounded. `--as-of` needs a timezone and remains a snapshot diagnostic, never PIT proof. The audit never collects data, advances a ledger, modifies a validation gate or starts a worker.

Source delivery, CI, merge, installed producer, published artifact and real Brain response are separate acceptance states. Consult the implementation plan and delivery receipt for exact heads and remaining acceptance; this research note does not claim deployment merely because tests passed.

## Primary sources

[S1] Cboe, Mandy Xu, *Evaluating the Market Impact of SPX 0DTE Options*, September 8, 2023. https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options

[S2] VolSignals, *Getting Started with VS3D*, Gamma/Charm mode and platform-basis sections, accessed November 13, 2026. https://vs3d.volsignals.com/home/getting-started

[S3] Cboe, Mandy Xu, *0DTEs Decoded: Positioning, Trends, and Market Impact*, May 2, 2025. https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact

[S4] Diego Amaya, Pedro A. Garcia-Ares, Neil D. Pearson and Aurelio Vasquez, *0DTE Index Options and Market Volatility: How Large is Their Impact?*, January 25, 2025 version. https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf

[S5] Cboe, VVIX Index Dashboard and definition. https://www.cboe.com/us/indices/dashboard/vvix/
