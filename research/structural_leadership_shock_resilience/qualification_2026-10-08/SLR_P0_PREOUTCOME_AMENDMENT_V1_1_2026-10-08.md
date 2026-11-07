# SLR-P0 — versioned pre-outcome methodology amendment v1.1

Date: 2026-10-08. Scope: **historical development design only**. Existing research carrier: Macro PR #8645, branch `sol/slr-p0-deep-research-20261007-c3`.

**PRE_OUTCOME_AMENDMENT_FROZEN / DATA_NOT_ADMITTED / HYPOTHESES_NOT_TESTED / INDEPENDENT_REVIEW_OWED**.

## 1. Provenance, identity and authority

- The original immutable protocol v1.0.1 remains recoverable in `SLR_P0_DEVELOPMENT_PREREG_2026-10-07.md`, derived from its pre-outcome wording correction at `4136eebc1d57b6d6c682403f1735849c5f9589f4`; original protected source was `Mastermind@c7e47c859eb2925c5626931fd511800773ba09ac`.
- This is a **versioned supplementary amendment**, not a silent rewrite of v1.0.1, not protected repository law, not a Data OS/CI/Executive admission control, and not a new experiment after seeing outcomes. The operative research rule is *v1.0.1 plus this explicitly dated v1.1 delta*, subject to independent pre-run methods review.
- The SLR owner has inspected **no historical SLR forward returns, no CR1/AF1/RH1 forward outcomes or forbidden prospective state payloads**, and no H7 conditional-result tables. The change was prompted by source-inspection logic, not observed effect sign, p-value, model performance, or subgroup outcome.
- **UNCHANGED:** research population for the registered primary, first sector common challenge after D+21..D+63, C−1 `continuation`, issuer-excluded >=20 peers, ex-self z severity <=−1, 60% negative breadth, past-only factor residual, coefficient-free 21-session stock-minus-peers total-return primary Y, 0.50pp/unit-Z relevance, fixed-effects estimator, 14-test Holm family, calendar-block/issuer clustering, forward embargo, kill/prospective rules and all protected outcome fences.
- **CHANGED:** clarify the prespecified **H7 scheduled-landmark negative-control population and clocks** so it cannot select prior rows by later common-shock eligibility; add explicit **input-admission prohibitions** implied by already-frozen causal clocks. Changes are pre-outcome safety hardening, not signal/threshold optimization.

## 2. H7 ambiguity and specific future-selection risk

v1.0.1 §9 says: “H7 uses one independent scheduled landmark D+21 per eligible onset, assessed at D+20, whether or not that day is a shock.”

If “eligible onset” is interpreted as **only an onset with a subsequently selected primary C during D+21..D+63 and `continuation` at C−1**, then enrollment for the earlier H7 landmark D+21 conditions on *future* information. That future C selection can occur during H7’s D+22..D+42 outcome horizon, creating collider/selection distortion and making the quiet-day arm falsely comparable to the primary cohort. This is a **conditional methodological hazard**, not an observed bug in deployed code (none exists) or proof that v1.0.1 was already run incorrectly.

### The binding v1.1 disambiguation for secondary H7 only

1. Construct an **H7-specific landmark risk set** independently of whether an onset ever develops a primary SLR common shock. The unit is every retained original canonical Detector-D onset D meeting historical source/type/security identity, observer-clock and available-lookback requirements **through the end of D+20**, with the incumbent `continuation` watch state at D+20. Require the unchanged $25m lagged median ADV and $5 lagged close by D+20. Inability to establish a prior-day state or required inputs is `UNOBSERVABLE`, not “quiet.”
2. At the **scheduled** landmark L=D+21, freeze other-issuer ex-self same-sector eligible peers from L−1. Require >=20 peers and exactly the historical and calendar coverage rules of v1.0.1; determine common-shock status `S_L` from p_L<0, lagged peer z<=−1.0 and breadth>=0.60. The status may be “shock”, “observed nonshock” or “unobservable”; never infer nonshock from missing data. L is selected **before knowing S_L or future outcomes** and regardless of subsequent first-shock C.
3. Fit the same two-stage expected-move ruler using sessions strictly ending L−1. Define `R_L = (r_i,L − expected_i,L) / lagged_RMSE`. Only after L closes is `R_L` recorded; labels begin **L+1**, not L. Carry the full frozen contemporaneous control vector at L and all lagged controls.
4. Fixed secondary target: the **coefficient-free stock minus L-frozen equal-initial-weight issuer-excluded peers' 21-session buy-and-hold total return**, starting at close L and ending at L+21; risk-set inclusion must **not** depend on whether this return later exists or is positive. Report terminal payoffs/censoring and missingness.
5. Fixed H7 interaction: `Y_L,21 ~ R_L + S_L + R_L*S_L + same_registered_controls + L-date×historical-sector fixed effects`. A cell must satisfy the identifiability and nonempty residual-variation requirements of v1.0.1. Since `S_L` will often be constant within a sector-date cell, its main effect may be absorbed by fixed effects; its **interaction** is estimable only with within-cell `R_L` variation and adequate shocked/nonshocked cell diversity. No unidentified coefficient may be replaced with a pooled no-FE proxy.
6. H7 remains **one of the 14 prespecified secondaries**, with its original Holm adjustment and no extra search. Use all source-qualified onsets in the H7 risk set whether or not they qualify for the primary sample. Explicitly report overlap with primary rows, plus H7-only, primary-only, no-rebound, unobservable, and future-C-excluded-vs-included counts for transparency; these counts cannot select a best subset.
7. H7's estimand is a **scheduled-landmark stress-specificity test in the broader continuing-Detector-D population**, not the exact conditional primary-C population. If H7 is null, the special **general shock** mechanism is unsupported, but this alone is not a mathematically identical direct null test for the selected primary-C cohort. Preserve the original decision law (a failed H7 restricts mechanism claims rather than retroactively deciding primary alpha).

**Examples** (conceptual only): D+21 is quiet and the first sector shock is at D+40. The H7 event must be enrolled at D+20 before knowing D+40 will occur. It must remain in the H7 risk set if no D+40 shock occurs. An unobservable D+21 must not be labeled “quiet” or replaced with a better-observed D+22.

## 3. Explicit historical-source and parent parity admission gates

These are **source-math acceptance tests implied by v1.0.1**, not additional selection criteria optimized on returns. All are evaluated on outcome-blind inputs.

**A. Detector-D parent**: the frozen original Winner Autopsy builder reads an undated `ticker_sectors.parquet` dictionary and passes it into historical `detect_episodes`; the detector uses one sector ETF with date-index intersection and 21/42-session relative breakaway rules. Before admitting v1.0.1's “canonical Detector-D onset D,” qualify a **complete-prefix mechanical parity** at D (including 63-session cooldown and relevant prior path). Do not merely relabel D after the fact, repair only challenge C, or search alternate onset dates without a separate changed-population protocol. Pin source-retention and selection digest. Benchmark ETF listing dates, gaps, date compression and price basis must be explicit.

**B. Original watch state C−1**: require prefix replay tied to the same original parent D, with validity/knowledge-time sector benchmark and correct 150-session watch-window behavior. A re-derived latest watch onset not identical to D does **not** satisfy “continuation for this onset.” Record the difference, do not silently infer D's status from another onset.

**C. Historical issuer / type / vendor aliases**: use the canonical Data OS owner and source-approved historical validity; current-only IssuerMaster or undated alias lookup is not historical proof. Exclude all same-economic-issuer share classes from subject's peers. Unknown is abstention. Neither SEC CIK nor FIGI alone proves every issuer/ADR continuation, merger, or ticker reuse.

**D. Total-return basis**: enforce homogeneous split/dividend/terminal-payoff adjusted **economic total returns** for subject, SPY and all peers in both feature and label windows, with explicit corporate-action identity. Massive documents split-adjusted (not dividend-adjusted) aggregate prices; its historical dividend endpoint can supply dividends **only if the actual historical records, entitlement and adjustment join are separately qualified**. Mixed Yahoo/other vendor sources cannot be blended on label dates without a dividend/split/basis transition witness. The existing Prophet price-basis vocabulary is a reuse candidate; do not create a new production adjustment owner.

**E. Event-size and earnings controls**: market-capitalization and earnings/material-release flags must each be causally known by the decision cutoff. Massive's historical ticker-details API can index SEC fields by *report period*, which precedes filing acceptance; `date=C−1` alone does not prove the returned size/issuer/fundamental data were public by C−1. Read the native source clock and filing/acceptance metadata. An unrecoverable mandatory C−1 market-cap/earnings flag makes the **complete registered primary specification unadmitted**, as v1.0.1 already requires. Unknown is not zero or false. The 504-session ex-ante market-state control means historical source evaluation must reach earlier than 2014 where necessary; a 2014 start-date claim is insufficient.

**F. No missing-session compression**: the Winner Autopsy `compute_excess` helper intersects available dates and computes `pct_change(n_td)`. A 21-row return after gaps is not always a 21-*exchange-session* return. The frozen SLR event and factor calendars explicitly require master-session alignment. Record gaps, no-future synthetic fills and exact onset-parity effects separately before claiming parent reproduction.

**G. Statistical identification**: the date×sector fixed effects and >=2 issuers/cell rule may eliminate many sparse cohort cells even if initial parent onsets are numerous. An outcome-blind census must count exact eligible cells, within-cell residual-Z variance, shock-date clusters and effective occupied 63-session blocks **before** assuming the numerical or power floors can be met. Headline 1,837 broad parent onsets do not establish study event N. Do not relax FEs, change the primary endpoint or select another shock threshold after viewing outcomes.

## 4. Provenance for new acceptance details

Pinned Macro source at `7e6ce338a9f88aaa60834bdeaf5ee2fe90dab477`:
- `scripts/research/build_winner_autopsy.py`: blob `6d33934bef3ab5f4dc6ce24e060045cfe4220cee`, `_load_yahoo_bars`, `_load_massive_bars`, `_merge_bars`, `_load_sector_of` and `--backfill`; see lines 108–242, 256–268, 998–1022, 1030–1043.
- `engine/winner_autopsy.py`: blob `32ae63b2a91e26f3aebff08e2badd8c566acd088`, `_GICS_ETF`, `compute_excess`, `_resolve_benchmark`, `detect_episodes`, `compute_watch_states` (lines 73–148, 185–315, 587–785); `WATCH_WINDOW_TD=150`, `EPISODE_COOLDOWN=63`.
- `engine/prophet_live/interval.py`: blob `e92bd6c49ac3f02c4e81c733ce1b59135e236cc8`, price-basis vocabulary and documented 0.649% raw/adjusted mismatch on CFG (lines 39–80). This historical production defect is illustrative, **not** an SLR return result.

Public first-party vendor docs, verified during the no-credential research lane:
- Massive aggregates split-adjusted, not dividend-adjusted: https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends
- Massive dividend endpoint with historical cash/adjustment factors and ex-dates: https://massive.com/docs/rest/stocks/corporate-actions/dividends
- Massive dated ticker details and report-period versus filing-time caveat: https://massive.com/docs/rest/stocks/tickers/ticker-overview
- Massive 2021 PIT ticker details/mkt cap methodology: https://www.massive.com/blog/announcing-our-new-point-in-time-company-details-api
- Source-historical GICS/identity diagnostics: `qualification_2026-10-08/HISTORICAL_REFERENCE_RECOVERY_PATH_2026-10-08.md`, `UPSTREAM_ONSET_PIT_GATE_2026-10-08.md`.

No vendor API authenticated requests, no historical source-row joins and no SLR forward-outcome reads occurred in this amendment phase. Official document capabilities do not establish current Mastermind dataset permission, response coverage or science readiness.

## 5. Verification, effect state, exact frontier

**Proof of freeze:** the Git commit containing this document and its blob digest are the amendment identity; do not use current time, a new chat, CI or PR merge as proof of source/data admission. The immutable v1.0.1 text remains unchanged. This amendment is frozen before outcomes. Independent mathematical/source review is still required for an actual empirical run; pending review is not a green light.

**Do not redo:** no new version of the original deep-literature report, no primary-threshold grid, no data-ownership side system, no user-access workaround. Earlier refused host alias/issuer row audit and refused evidence-checker code publication remain refused and are not replayed by this amendment. Existing protected CR1/AF1/RH1 forward states remain closed.

**Next action:** the incumbent reference-data owner provides a positively permitted, historically valid sector+issuer+instrument+return-adjustment and lagged control package, then a fully outcome-blind Detector-D/continuation parity and risk-set/cell-power audit is independently verified. If that fails, preserve `NOT_ADMITTED` with missing requirements; do not treat this versioned clarification or a successful CI job as permission to open outcomes.
