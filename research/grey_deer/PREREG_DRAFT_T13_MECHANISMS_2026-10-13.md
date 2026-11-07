# T13 mechanisms — preregistration DRAFT (not frozen)

Program: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258. Lane GD-W7-T13PRE. Draft date 2026-10-13.
Seat `da1ad7ad` freezes a later revision. This file is not that freeze. It authorises no fit, no score and no promotion.

Status of this file: **DRAFT**. Outcome-blind. No label, feature value, hit rate, return, skill score or episode count was computed to write it. No price store and no vintage store was opened. `data/` is not in this worktree and was not created.

Question, stated before any outcome: conditional on a state that was already published at the SPY close of session `t`, does that state change the probability or the depth of the frozen 5/10/21-session pullback, relative to an unconditional baseline and a volatility-matched baseline?

One mechanism per hypothesis. Directions below are pre-committed. A wrong-way sign kills that cell. It is not re-read as a different story after the fit.

## 1. Target and horizons

Reused, not redefined. Frozen target of `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md` §4, which carries v1 (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`):

For ticker `i`, origin date `t`, close `P_i,t`, horizon `h ∈ {5, 10, 21}` sessions:

`A_i(t, h) = max(0, 1 − min(P_i,{t+1}, …, P_i,{t+h}) / P_i,t)`

- Event row: `Y_i(t, h) = 1` iff `A_i(t, h) ≥ 0.05`, once the label is mature. Otherwise `0`. An immature label is absent, never zero.
- Quantile target: `A_i(t, h)` at `τ ∈ {0.5, 0.8, 0.9}`. This draft's depth claim uses `τ = 0.8` only. `τ = 0.5` and `τ = 0.9` are printed and are not trials.
- Maturity: origin `(i, t)` is mature for `h` only when session `t+h` is inside the window.
- Basis: the frozen §4 basis disclosure stands (D14-adjusted close on the D15 intersection when the panel rule is in force; dividends unadjusted). This draft does not change it.
- `D_total` stays uncomputed. P-active stays `BLOCKED / OBSERVER_NOT_ON_MAIN` under frozen §5. Population for every cell here is **P-all**.

Horizons are three claims, not one claim with a chosen horizon.

## 2. Cohort

**SPY only.**

The packet allows the panel only if the seat's v1.2 episode rule exists. A search of `research/grey_deer/` found no v1.2 episode rule. The panel is not in this draft. A later panel is a new revision, not an extension of these trials.

## 3. Sample construction

The origin set is the one built by `scripts/research/grey_deer_episode_samples.py` (T12, in parallel with this draft). That file is not on this branch. This draft does not invent its seed, its episode id, or its sample hash, and it does not construct a substitute sample.

Execution rule, before any label or fit:

1. Refuse unless that module exposes a frozen seed and a frozen sample hash. Missing either is `BLOCKED / SAMPLE_NOT_FROZEN`. No outcome is computed.
2. The results artifact, when a later freeze runs, copies both strings. A different hash is `BLOCKED / SAMPLE_IDENTITY_MISMATCH`. It is not re-hashed into agreement.
3. The window cannot silently expand past the frozen SPY window in v1 §3: `EARLIEST_ENTITLED` 2021-07-06 through 2026-10-07 inclusive. Rows after 2026-10-07 are dropped before any feature or label. A T12 sample that is a subset of that window is allowed. A sample that leaves that window is `BLOCKED / WINDOW`.
4. Warmth and maturity are the frozen rules: warm when the session index is at least 63; mature per §1. This draft does not re-measure the calendar.
5. The dependence unit for uncertainty is the episode id the T12 builder emits. This draft defines no third episode rule. If the builder emits no episode id, the run is `BLOCKED / EPISODE_ID_ABSENT`.
6. Feature join is the PIT rule in §5. A missing lawful value is an abstention, never a fill from the latest-revised store.

The seed and the hash are frozen before any outcome on this hypothesis family is seen. This draft does not look at them.

## 4. Census

A row is **eligible** only when both are true:

- the repo states when a value for day `t` is actually available (a publication clock, not merely the observation date the live frame stamps); and
- a first-published vintage is in the program's PIT macro store, which the pullback source-rights manifest names as `data/fred_vintage/vintages.parquet` via `collectors/fred.py` (`research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md` §4 row 5). Disposition there: `recorded` for internal fitting. That file's other rows are cited only as dispositions. This draft does not restate them.

The live feature frame (`engine/inputs.py` `put`, default `ffill_limit=5` at line 192) stamps FRED series on the reference date and forward-fills. That path is **not** the confirmatory read. `engine/risk_radar.py` `leading_signals` (line 665) does the same forward-fill and is not the confirmatory read either.

Confirmatory read, eligible rows only: initial release, `collectors/fred.py` `as_of_series` (line 239) and `engine/pit.py` `release_availability` (line 243). This draft is stricter than both: see §5. If the vintage row is absent, the origin abstains. The modelled `lag_bd` fallback in `engine/pit.py` `_modelled_release` is refused. Latest-revised `data/fred/*.parquet` is refused.

`collectors/fred.py` lines 36–38 say market series (rates, OAS, VIX, FX, dollar) are never revised and are left out of `DEFAULT_VINTAGE_SERIES` on purpose. A "never revised" claim without a first-published timestamp still has no `available_at`. GD-1C already recorded that DGS10, DGS30 and DFII10 have no first-available vintage clock in this checkout (`research/grey_deer/gd1c/GD1C_SOURCE_RIGHTS_AND_GAPS.md`, "Additional temporal gaps"). This draft follows that ruling.

### 4.1 Eligible

| Feature | Producer (file:line) | Source | Publication clock | Revision and history start | PIT vintage |
|---|---|---|---|---|---|
| Kim-Wright 10y term premium, level. Column `term_premium_10y`. Series `THREEFYTP10`. | Alias `config.yml:252`. Fetch `collectors/fred.py:79` (`_fetch_one` :102). Vintage fetch `collectors/fred.py:176` and `:197`. Map `engine/pit.py:70`. Live stamp, not used here, `engine/inputs.py:346`. | FRED `THREEFYTP10`. | Primary clock is the ALFRED initial-release `realtime_start` (`collectors/fred.py:143–148`, `as_of_series` :239–249). The prose lag at `engine/pit.py:140` (`lag_bd` 3, note "ACM term premium, ~2–3 bd") is a **mislabel**: the series id on that row is Kim-Wright `THREEFYTP10`, and `engine/rates_inflation_command.py:890–905` says ACM is pending. The prose lag is not the clock. §5 says how `realtime_start` maps onto the equity close. | Revised model series. The store keeps the initial release only (`output_type=4`); later revisions are stripped (`collectors/fred.py:143–148`). `fetch_all_vintages` (`collectors/fred.py:270`) can pull the full matrix and is not the accessor this draft uses. History start is not stated in the producer. The vintage request floor is `vintage_realtime_start` 1997-01-01 (`config.yml:106`). That floor is not an economic start. This lane did not open the store. | Yes. In `DEFAULT_VINTAGE_SERIES` (`collectors/fred.py:44`) and in `config.yml` `vintage_series` (:124). |
| St. Louis Fed Financial Stress Index, level. Column `stlfsi`. Series `STLFSI4`. | Alias `config.yml:245`. Same FRED fetch and vintage fetch as the row above. Map `engine/pit.py:84`. Live stamp, not used here, `engine/inputs.py:322` (`ffill_limit=10`). Label `engine/conditions.py:558`. | FRED `STLFSI4`. | Primary clock is ALFRED `realtime_start`, same accessor as the row above. Prose clocks disagree and are not used: `engine/inputs.py:312–314` says STLFSI4 publishes Thursdays; `engine/pit.py:141` says weekly Thursday for the prior week, `lag_bd` 6; `engine/conditions.py:550–551` groups STLFSI with NFCI as a Friday observation published the following Wednesday. Because those sentences disagree, the modelled lag is refused. | Inside the bounded initial-release set (`collectors/fred.py:52`), unlike the NFCI family which is deferred. History start is not stated in the producer. Store not opened. | Yes. `DEFAULT_VINTAGE_SERIES` and `config.yml:126`. |

`curve_tp_adj` (`engine/inputs.py:398–401`) adds `spread_2s10s` to the term premium. The curve leg is ineligible (§4.2). The sum is ineligible. H1 uses the term-premium level alone.

### 4.2 Ineligible

Each row has a producer, where one exists. "INELIGIBLE" means the feature is not in the trial budget. The direction, if stated in §6, is pre-committed and is not estimated here.

| Feature | Producer (file:line) | What the repo actually says about time | Why INELIGIBLE |
|---|---|---|---|
| 10y real yield `DFII10` → `us10y_real`. 5y real yield `DFII5` → `us5y_real`. | `config.yml:175`, `config.yml:313`. Live stamp `engine/inputs.py:275–277` and `:394–396`. Radar transform `engine/risk_radar.py:691–693` (`rates_realrate` = 5-session difference, then a trailing percentile). | `collectors/fred.py:36–38`: market rates are treated as never revised and are excluded from the vintage list. `engine/conditions.py:565` gives the 10y nominal a 5-calendar-day staleness disclosure, and line 549 says those ages are disclosure thresholds, not gates. No sentence states the H.15 publication hour versus the equity close. | No first-available clock. GD-1C: DFII10 is a latest-revised file without a first-known vintage. Not in `vintage_series`. |
| Curve slope `T10Y2Y` → `spread_2s10s`, fallback `us10y − us2y`. `T10Y3M` → `spread_10y3m`, fallback `us10y − us3m`. | `config.yml:174`, `config.yml:310`. `engine/inputs.py:295` and `:397`. Carried into `engine/bonds.py:252–260`. | Same market-rate treatment as DFII10. No publication hour. | No first-available clock. Not vintaged. The nominal DGS legs have the same GD-1C gap. |
| HY OAS `BAMLH0A0HYM2` → `hy_oas`. IG OAS `BAMLC0A0CM` → `ig_oas`. Rating ladder and `hy_ig_ratio`. Moody's Baa−Aaa. | `config.yml:180–181` and `:337–344`. Live stamp plus archive splice `engine/inputs.py:275–283`. Ratio `engine/bonds.py:269–276`. Baa−Aaa `engine/bonds.py:277–281`. Radar `engine/risk_radar.py:681–683` (`credit_oas_roc` = 21-session difference). | `collectors/fred.py:8–12`: since April 2026 FRED serves a rolling ~3-year window for the ICE BofA OAS ids; older rows live in `data/archive/` with no `published_at` in the collector. `engine/conditions.py:559` staleness age 5 calendar days, disclosure only. | No publication hour versus the equity close. Not vintaged. The archive splice has no first-published timestamp. |
| Excess bond premium (Gilchrist–Zakrajšek), column `ebp`. | `collectors/fedboard.py:21` `fetch` :29; header :9 "history from 1973. Updated ~4th business day each month"; `stale_after_days = 45` at :24. Live stamp `engine/inputs.py:406–408` (`ffill_limit=45`). | `engine/conditions.py:552–554`: an observation dated the 1st routinely arrives about eight weeks later, hence a 70-day staleness age. | The two clocks disagree (~4th business day versus ~8 weeks). No vintage. The value knowable at `t` is not identified. |
| NFCI, ANFCI, NFCIRISK, NFCICREDIT, NFCILEVERAGE. | `config.yml:240–244`. Live stamp `engine/inputs.py:320–321` (`ffill_limit=9`). | Clock is stated: Friday-dated observations, published mid-next-week, NFCI family Wednesdays 08:30 ET (`engine/inputs.py:312–319`). `engine/conditions.py:550–551` agrees. | The family re-revises its whole weekly history every release. The initial-release vintage is explicitly deferred because the matrix times out (`collectors/fred.py:58–61`, `config.yml:110`). The publication weekday is known and the knowable value is not stored. |
| OFR Financial Stress Index and its credit, equity, safe-asset, funding, volatility, US, other-advanced and EM legs. | `collectors/ofr_fsi.py:30` `fetch` :51. Header :4 says a daily index back to 2000. `stale_after_days = 6` at :33 ("~2 business-day publication lag"). Live stamp `engine/inputs.py:323–333` (`ffill_limit=7`). Freshness age 6 at `engine/conditions.py:561`. | The ~2-business-day lag is a clock. | Revision behavior is not stated. There is no as-first-published vintage. The pullback PIT macro store is the FRED vintage matrix only. A latest CSV pull is not the print that was available at `t`. |
| SOFR−IORB, SOFR−EFFR, EFFR−IORB, SOFR 99th−SOFR (`repo_spike_bp`), OFR BGCR and TGCR. | FRED aliases: `SOFR` `config.yml:403`, `IORB` `config.yml:326`, `SOFR99` `config.yml:327`. Spread `engine/bonds.py:298–307` (`sofr_iorb_bp`, `repo_spike_bp`). Same spreads `engine/neuralweb/liquidity_plumbing.py:140` and `:943–968`. Corridor pair `engine/market_os/macro_workspaces/rates_curves.py:865–868`. SOFR−EFFR `engine/funding_stress.py:54–63`. OFR fetch `collectors/ofr.py:62`. Mnemonics `config.yml:4075–4081`. | OFR collector: `stale_after_days = 7`, comment "daily series, ~1-day publication lag" (`collectors/ofr.py:57`). FRED SOFR/IORB themselves have no publication-hour sentence. | The engine spreads are reindexed onto the price calendar with `ffill(limit=5)` and no release shift (`engine/bonds.py:301–307`), so the reference date is treated as known on that date. The OFR ~1-day comment is not applied there. No first-published vintage for FRED SOFR, IORB or SOFR99, and none for the OFR mnemonics. Revision of the OFR pull is not stated. |
| FRA−OIS. | No producer. Search of `*.py` and `*.yml` found no `FRA-OIS`, `fra_ois` or OIS-spread feature. | None. | INELIGIBLE. No series, no clock. |
| Commercial paper, AA and A2/P2 90-day. | `config.yml` `funding_stress` group (`RIFSPPNAAD90NB`, `RIFSPPNA2P2D90NB`). Live stamp `engine/inputs.py:334–340` (`ffill_limit=7`). | Daily, forward-filled. No publication hour. | No first-available clock. Not vintaged. |
| Discount-window primary credit and SRF take-up. | `engine/neuralweb/liquidity_plumbing.py:957–961` states they are not collected. | None. | INELIGIBLE. No series. |
| DXY, Yahoo `DX-Y.NYB`, column `dxy`. Broad dollar `DTWEXBGS` → `broad_dollar`, plus AFE and EME legs. Spliced level `build_broad_dollar`. | DXY stamp `engine/inputs.py:238`. Broad alias `config.yml:219` (comment says 2006→). Splice `engine/flow_regime.py:65–66` and `:144`. Shared load described at `engine/forex_inputs.py:6–13`. | DXY is an exchange daily close. The repo does not state its settlement minute versus the SPY close. `DTWEXBGS` has a history-start comment and no publication clock. Source-rights §4 row 11 disposes `DX-Y.NYB` as `source_unavailable` (CURRENT_VINTAGE). | No first-available clock for the broad index. The Yahoo close has no vintage and is not a recorded pullback input. The splice across 2006-01-01 mixes two unclocked series. |
| ACM term premium (NY Fed). | Not collected. `config.yml:252` says "collected separately later". `engine/rates_inflation_command.py:905` says "ACM pending". | None. | INELIGIBLE. No producer. Do not relabel `THREEFYTP10` as ACM. |
| Spot vol term structure. Ratio `VIX / VIX3M`. Columns `vix_ratio`, `vix_term`, `ts_slope`. Radar `vol_term` prefers `VIX9D / VIX3M`, else `VIX / VIX3M`. | Definition `engine/canon.py:211`. Frame `engine/inputs.py:244–259`. Conditions `engine/conditions.py:385–390`. Regime `engine/vol_regime.py:145–150`. Radar `engine/risk_radar.py:707–715`. Yahoo load `scripts/build_vol_regime.py:3` (comment "VIX 1990+"; VIX3M start year not stated). | `engine/conditions.py:562–563` staleness age 5 calendar days, disclosure only. `engine/vol_regime.py:227–229` notes that a VIX print can exist before VIX3M settles on the same date. That is a same-day cadence guard, not a publication timestamp on the stored daily close. | Yahoo `_VIX`, `_VIX3M`, `_VIX9D` are CURRENT_VINTAGE closes. Source-rights §4 row 2 disposes that class `source_unavailable` for this program's historical sample. No first-published vintage. |
| VIX futures curve, M1..M6 slope and carry. | `collectors/cboe_vix_futures.py:14–25`. | The collector states there is no bulk settlement history. Slope and carry accrue forward only, from a short CSV seed. | INELIGIBLE for this historical sample. A prospective accrual is a different revision, after a publication clock for each settlement file is written down. |
| HYG/TLT credit-price ratio. Radar `credit_hyg_tlt`. MOVE index. Radar `rates_move`. | `engine/risk_radar.py:684–690`. | US-listed closes. | Source-rights §4 row 3 disposes HYG, TLT and `_MOVE` as `source_unavailable`. Not used. |

## 5. PIT rule for the two eligible features

Let session `t` be the SPY close that is the origin. The issue time is that close. A date-only `realtime_start` has no hour. This draft therefore does **not** treat a print stamped on calendar date `t` as known at the close of `t`.

`tp10_pit(t)` is the initial-release value of `THREEFYTP10` whose `realtime_start` is the latest calendar date strictly before the calendar date of session `t`. `stlfsi_pit(t)` is the same function of `STLFSI4`.

Consequences, all pre-committed:

- `as_of_series` (`collectors/fred.py:249`) and `release_availability` keep a row when `realtime_start <= asof`. This draft drops same-calendar-day stamps. The next session may use them.
- No modelled lag is substituted when the vintage is missing. The origin abstains. Typed reason `VINTAGE_ABSENT`.
- The carried value is the last print already visible under the rule above. It is not a revision published later, and it is not the live frame's reference-dated forward-fill.
- The feature in the model is the level, not a change, a z-score or a percentile. Any standardisation uses only the training complement of that fit (the frozen v1 §6 training-prefix rule: mean and standard deviation with `ddof = 0`). It is never fit on the held-out episode and never fit on the full sample.
- One feature per hypothesis. H1 does not include STLFSI. H2 does not include the term premium.

## 6. Hypotheses

Estimable cells are H1 and H2. H3–H9 are direction-registered and budget 0. They are not fit. They enter a budget only in a later revision that adds a lawful clock and a first-published vintage, and that revision has to be written before any outcome for that hypothesis is computed. If an outcome for an ineligible hypothesis is computed before that revision, the hypothesis is burned and cannot be promoted.

| Id | Mechanism | Direction, stated now | Estimable |
|---|---|---|---|
| H1 | Kim-Wright 10y term premium, `tp10_pit(t)` | Higher level → higher `P(Y=1)` and higher `τ=0.8` quantile of `A`, at each of 5, 10 and 21. Reading used: a larger term premium is a higher price of duration risk, a tighter rates state. The opposite reading (a higher premium as a higher expected excess return) is why a negative coefficient kills the cell instead of being adopted after the fact. | Yes |
| H2 | STLFSI4, `stlfsi_pit(t)` | Higher level → higher `P(Y=1)` and higher `τ=0.8` quantile of `A`, at each horizon. The producer label is a stress index (`engine/conditions.py:558`): higher means more stress. | Yes |
| H3 | 10y real yield, the radar's 5-session change of `DFII10` | A rise → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. | No |
| H4 | 2s10s slope, `T10Y2Y` | A lower (flatter or more inverted) slope → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. | No |
| H5 | HY OAS, 21-session change of `BAMLH0A0HYM2` | A widening → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. | No |
| H6 | Funding stress, SOFR minus IORB, in basis points | A higher spread → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. FRA−OIS is not a stand-in; it has no producer. | No |
| H7 | Dollar, broad `DTWEXBGS` level | A higher dollar → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. DXY is not a silent substitute. | No |
| H8 | Equity vol term structure, `VIX / VIX3M` | A higher ratio (toward backwardation) → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. | No |
| H9 | NFCI level | A higher index (the producer's sign: `+=tight`, `config.yml:240`) → higher `P(Y=1)` and a higher `τ=0.8` quantile of `A`. | No |

H3–H9 each inherit the kill rules in §10 if a later revision makes them estimable. Until then they have no result, including no "not significant".

## 7. Baselines

Two baselines, both already frozen. This draft does not re-derive them and does not copy their math.

- **Unconditional.** Frozen v1 configuration `B0` (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md` §6): the training-prefix event rate, applied inside whatever training complement the T13 fit uses.
- **Volatility-matched.** Frozen v1 configuration `B1-20`: L2-logistic on `log rv_20`, with `rv_20` from `engine.vol_forecast.realized_vol` as that section already specifies. Same training complement. Quantile baseline for the depth cell is the frozen `Q1` construction restricted to the `rv_20` terciles, at `τ = 0.8` only.

The mechanism model is that baseline plus the single PIT feature. It is not the frozen `M3-ALL` feature set, and it is not a stack of H1 with H2.

Comparison set: origins where the mechanism model and both baselines issue. Abstentions are reported, not imputed. An abstention does not become `Y = 0`.

## 8. Statistics and uncertainty

Scores are the ones already named in v1.1 §9. This draft does not rewrite them.

- Binary claim, per horizon: Brier skill (`BSS` in v1.1 §9) of the mechanism model against `B0` and, separately, against `B1-20`. Logarithmic score skill is printed beside `BSS` from the same fit and is not a second trial.
- Depth claim, per horizon: pinball skill at `τ = 0.8` against the unconditional quantile baseline and against the volatility-matched quantile baseline. `τ = 0.5` and `τ = 0.9` are printed from the same fit and are not trials.
- The frozen `b_h` scale is not an input, not a threshold and not a baseline.

Uncertainty, primary: **leave-one-episode-out**. For each T12 episode, refit on the complementary episodes only, then score the held-out episode's origins. Purge: drop every training origin whose horizon window of length `h` overlaps the held-out episode. Embargo stays 0, because §5 makes the feature known before the close of `t`. The printed interval is the 10th and the 90th percentile of the episode-level skill contributions. If a held-out fit has an empty training complement, that cell is `BLOCKED / LOEO_UNDEFINED`. It is not filled.

Uncertainty, display only, not a trial and not a gate: the frozen v1.1 §10 date-block bootstrap (`L = max(21, 2h)`). It is printed. It cannot overturn a kill and it cannot create a display candidate the LOEO interval does not support.

No full-sample coefficient is the claim. The reported coefficient sign is the sign in the pooled LOEO training fits, and a single contradictory held-out fit does not flip it. The kill rule for sign is in §10.

## 9. Multiplicity

- Trial family: `grey_deer_t13_mechanisms`.
- Basis: itemized.
- Budget: **12**. Arithmetic: 2 estimable hypotheses (H1, H2) × 3 horizons (5, 10, 21) × 2 endpoints (binary `BSS`, pinball skill at `τ = 0.8`).
- H3–H9 consume 0. The negative control consumes 0. Log loss, the other two quantile levels, and the block bootstrap consume 0.
- All 12 cells are printed. None is selected because it was the best of the 12. There is no "any horizon" claim and no family-wise threshold chosen after looking.
- A later revision that makes one ineligible hypothesis estimable adds its own budget in that revision. It does not draw on these 12.

## 10. What kills a hypothesis

Applied per cell (one hypothesis, one horizon, one endpoint). A kill on one cell does not kill the other horizon. A kill is printed and is not repaired by a new transform, a new lag, a new τ or a new baseline.

The cell is **killed** if any of these is true:

1. **Wrong sign.** For H1 and H2 the pre-committed sign is positive (higher level → higher probability, higher `τ=0.8` quantile). A negative or zero coefficient on that cell kills it. For H4 the pre-committed sign is negative on the slope (a lower slope → higher probability and depth); a positive coefficient kills H4 if it is ever estimated.
2. **Fails a baseline.** Binary: `BSS` against `B0` ≤ 0, or `BSS` against `B1-20` ≤ 0. Depth: pinball skill against either quantile baseline ≤ 0. Both baselines have to be beaten. Beating only the unconditional rate is a volatility restatement and is a kill.
3. **Stale control wins.** On that horizon, the negative control's `BSS` against `B0` is greater than or equal to the timely model's `BSS` against `B0`. Defined in §11. Applies to H1 and to H2 (H2 is judged against the same stale term-premium control, so a slow common factor cannot pass H2 while failing the timing check).

The cell is a **printed null**, not a kill and not a display candidate, if the sign is right and both point skills are positive, and the LOEO 10th–90th interval of skill against the volatility-matched baseline covers 0.

The cell is a **display candidate** only if it is not killed, both point skills are positive, and that LOEO interval lies entirely above 0. A display candidate still promotes nothing (§12).

These are not kills. They stop the run:

- `VINTAGE_ABSENT` on every origin → `BLOCKED / NO_VINTAGE`.
- `SAMPLE_NOT_FROZEN`, `SAMPLE_IDENTITY_MISMATCH`, `WINDOW`, `EPISODE_ID_ABSENT`, `LOEO_UNDEFINED`.
- A singular feature on a training complement → that complement abstains as `FEATURE_DEGENERATE`. If every complement abstains, `BLOCKED / NO_VARIATION`.

A block is not rescued by imputing the feature, dropping the purge, or switching to the live frame's forward-fill.

## 11. Negative control

**NC — year-stale term premium.** The feature is `tp10_pit` lagged an additional 252 sessions after it is already visible under §5. It is the same vintaged series, so it adds no new source and no new clock.

Pre-committed behavior: NC should **not** matter. Its `BSS` against `B0` should sit at or below 0 at each horizon. It is printed at all three horizons. It is not one of the 12 trials. It cannot be promoted.

Why this control: a term-premium print that has been public for a year is not the rates state at issue. If the stale print matches or beats the timely H1 print, the timely result is a slow confound and rule §10.3 kills the timely cell. The same comparison kills H2, so H2 cannot pass on a factor that the stale term premium already carries.

NC is not a second mechanism hypothesis. A positive NC skill does not become a new claim.

Calendar dummies, the session-of-month index, and a sign-flipped label are not added. The frozen label-shift control in v1.1 §12 stays the property of that protocol. This draft does not rerun it.

## 12. Promotion

Display-only until a later gauntlet. The gauntlet is a new frozen preregistration. It is not this file, not a threshold chosen from these 12 cells, and not a radar weight.

Nulls are printed in the same table as display candidates. A null is not dropped, pooled, or sign-flipped. No alarm, size, gate, rank or order follows from a display candidate. `b_h` is not turned into an alarm here.

This draft freezes no runner, no seed and no hash.

## 13. Known exposure

Previously inspected history is exploratory. The search was filename-only under `research/grey_deer/` for the producer ids and column names. Result bodies were not opened. A bare `MOVE` or `VIX` token was not used: both match ordinary English. The radar column `rates_move` was used instead.

No hit, under those tokens: `hy_oas`, `ig_oas`, `BAMLC0A0CM`, `us10y_real`, `term_premium`, `THREEFYTP`, `T10Y2Y`, `spread_2s10s`, `SOFR`, `IORB`, `STLFSI`, `ofr_fsi`, `DTWEX`, `broad_dollar`, `vix_term`, `EBP`.

Hits, file names only:

`credit_oas`

- `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md`
- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/atlas-run.log`
- `research/grey_deer/evidence/replay-parity-rerun-20260921/episode-atlas.log`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`
- `research/grey_deer/evidence/replay-maturity-20260920/base.log`
- `research/grey_deer/evidence/replay-maturity-20260920/final.log`
- `research/grey_deer/evidence/replay-maturity-20260920/green.log`
- `research/grey_deer/evidence/replay-maturity-20260920/verification.json`

`BAMLH0A0HYM2`

- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/verification.json`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/verification.pre_parity.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`
- `research/grey_deer/evidence/probability-walkforward-20260923/result.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/verification.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/result.json`

`DFII10`

- `research/grey_deer/gd1/GD1_PREREG_2026-08-19.md`
- `research/grey_deer/gd1c/GD1C_SOURCE_RIGHTS_AND_GAPS.md`
- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/verification.json`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/probability-walkforward-20260923/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/verification.pre_parity.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/verification.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/result.json`

`rates_realrate`

- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/atlas-run.log`
- `research/grey_deer/evidence/replay-parity-rerun-20260921/episode-atlas.log`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`

`VIX3M`

- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/verification.json`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/probability-walkforward-20260923/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/verification.pre_parity.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/result.json`
- `research/grey_deer/evidence/displayed-probability-audit-20260922/verification.json`

`vol_term`

- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/atlas-run.log`
- `research/grey_deer/evidence/replay-parity-rerun-20260921/episode-atlas.log`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`

`rates_move`

- `research/grey_deer/evidence/replay-comparability-20260920/real-input-replay.json`
- `research/grey_deer/evidence/episode-warning-path-20260921/atlas-run.log`
- `research/grey_deer/evidence/replay-parity-rerun-20260921/episode-atlas.log`
- `research/grey_deer/evidence/caution-persistence-20260921/result.json`
- `research/grey_deer/evidence/state-ladder-calibration-20260921/result.json`
- `research/grey_deer/evidence/gate-latency-20260921/result.json`

`NFCI`

- `research/grey_deer/gd1/GD1_PREREG_2026-08-19.md`

`DXY`

- `research/grey_deer/GD1_GROK_SCIENTIFIC_REPLAY_HANDOFF_2026-08-19.md`
- `research/grey_deer/gd1/GD1_PREREG_2026-08-19.md`

The frozen pullback stage-1 feature list (`scripts/research/grey_deer_pullback_stage1.py` `FEATURE_COLUMNS`, lines 274–284) is price-path only: `rv20`, `rv63`, `log_rv20`, `log_rv63`, `sma_gap21`, `sma_gap63`, `dd63`, `r5`, `r10`. None of the mechanism columns above is in that list. Naming a feature in a preregistration (`GD1_PREREG`, the handoff, the source-rights note) is not by itself an outcome inspection. The `evidence/**` paths are outcome artifacts of earlier radar work. They are exploratory for any later use of `credit_oas`, `DFII10` / `rates_realrate`, `vol_term` / `VIX3M`, or `rates_move`. H1 and H2 did not match those tokens.

## 14. What a later freeze still has to pin

- The T12 seed, sample hash and episode-id definition, copied verbatim. Not chosen here.
- That `THREEFYTP10` and `STLFSI4` are actually present in the vintage store with non-empty `realtime_start`. This draft did not open the store. Absence at freeze is `BLOCKED / NO_VINTAGE`, not a quiet switch to the live parquet.
- A runner that is not this file. This draft writes no estimator.

No outcome on H1–H9 is computed between this draft and that freeze.
