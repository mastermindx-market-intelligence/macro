# Factor Atlas S3 — Options, Positioning and Portfolio Risk

**Native execution edition: 2026-10-11.** This report carries the research decisions into the first native source candidate. It does not claim deployment, live-data acceptance, complete competitive parity or trading authority. The expanded 2026-10-09 research attachment remains a separate historical artifact: SHA-256 `7d19dd459a60dab1ae3dce9b504723c4d4fecc1552e890492cf8337ecc392fdb` (86,815 bytes). This edition is not a byte-for-byte import of that attachment.

## 0. Outcome, source identities and recommendation

A user should be able to inspect the options pricing and positioning context of a well-defined factor, distinguish observed instrument inputs from constituent aggregates and portfolio models, and inspect the coverage and assumptions behind every value. A synthetic equity basket must never be presented as having a directly traded options surface merely because its constituents have options.

Use three explicitly different layers:

1. Actual instrument data: identified contract quotes, trades and published OI, with contract IV/Greeks identified as model-derived even when supplied by a vendor.
2. Constituent descriptions: weighted IV statistics, root-level skew, activity, expiry intensity and concentration. These describe a population; they are not diversified portfolio volatility.
3. Portfolio models: covariance-based expected moves, factor-risk decomposition and conditional hedging scenarios. These carry assumptions and sensitivity, not an observed synthetic-market price or a calibrated probability by default.

Preserve one owner per responsibility: Options Superintelligence owns tape/observations and their existing stores/publication; MSC owns dealer-sign and exposure methodology; the factor-definition owner supplies identity/membership/weights; the existing risk owner supplies historical covariance; existing portfolio/user services own holdings and access. Atlas adds a read/aggregation leaf, not another platform.

### Evidence editions

- Historical full census: Macro `cdbcd143dcfa419ab0637bc11dd4c80368143e2e`; Terminal `bacda5dcc30682f9327e037a2d4425bd9714ac3a`. Findings below explicitly retain that observation boundary; historical plans and tests are not current live proof.
- Native source base: Macro `773d6cc2f18fdbce5441e484abc16eb30d8ba3db`.
- Terminal default reference observed during continuation: `707648d5201494ec42a2429ffb64cc39fb24314e` (no Terminal edits).
- Protected procedure: Mastermind `8e38a4ce8365fb3f0591d5729f228394b35d125d`, compatible Skillpack 1.0.1. The current assignment permits the independent source/test work; runtime admission is not fabricated.
- Native operation: `factor-atlas-s3-native-20261011-c1`, allocator-derived branch `sol/web-factor-atlas-s3-native-20261011-c1`.

## 1. Existing capability census and collisions

| Capability / source | What the historical source inspection establishes | What it does not establish |
|---|---|---|
| `engine/options_hub.py` | Per-root nightly volatility/GEX payloads; ATM/term/smile/history statistics; display-tier contract | Current qualified whole-universe chains or a basket options surface |
| `engine/gex_engine.py` | Repriced gamma profiles, crossings and assumed-sign exposure with thin/invalid-chain guards | Observed dealer ownership or an obligatory future hedge |
| `engine/vex_engine.py` | Vega-weighted exposure, despite ambiguous VEX terminology elsewhere; assumed sign | Vanna, measured inventory, or proof that vega alone determines hedge direction |
| `engine/options_flow.py` | Minute-bar signed-volume/premium and activity summaries with calibration gate | Direct institutional buying, trade-side truth, opening positions, or complete sweep/block classification |
| `engine/flow_signing.py` | Tick/quote-rule comparison and calibration helpers | Quote-rule labels are not exchange participant ground truth |
| `engine/thetadata_store.py` | Existing historical EOD/OI/Greek reader and canonical resolver | An accessible store on every worker or current feed entitlement |
| `engine/factor_exposure.py` | Orthogonalized macro/style betas, covariance and portfolio-risk context | Every theme is an independent statistical factor; every asset market shares a valid clock |
| `engine/theme_crowding.py` / `engine/crowding.py` | Residual co-movement, stretch/fragility context and retained negative empirical findings | A basket-timing signal or exact institutional position |
| `engine/fund_crowding.py` | Requested path absent at the historical pin | Do not commission a duplicate based on this name: related study and `engine/ownership_crowding.py` exist |
| `engine/ownership_crowding.py` | Tracked shares/ADV exit-pressure context with separate ownership and short axes | Purchase cost basis, real-time holdings or a fused ownership/short/options score |
| Terminal `optionsIa.ts`, `OptionsWorkspace`, `flowSource.ts`, `volTypes.ts` | Native categorized workspace and existing backend/R2 routing; percentage-number IV convention; nightly history/smile consumers | A current authenticated user journey, complete chain browser or qualified expected-versus-realized history |
| Terminal `lib/portfolio.ts` / `/portfolio` | Existing `portfolio_positions` service, nullable sizes and user-scoped reads | Permission to create a second portfolio schema or convert watchlists into holdings |

The historical Options Superintelligence masterplan and the 2026-08-08 Options Prophet audit distinguish shipped displays from incomplete classifier, chain, historical and promotion work. Preserve that distinction. Plans, merged source, published data and production user proof are separate evidence classes.

Specific source findings to carry forward:

- The inspected `iv_rank_252` counts historical observations strictly below current IV: percentile semantics, not min-max rank. Do not silently reuse its name as a mathematical specification.
- The legacy root producer interpolated IV levels and used a nearest listed tenor outside the bracket. A legacy scalar therefore cannot certify a standardized 30-day value.
- The legacy volatility payload lacks the per-quote quality and precise publication metadata needed for qualified basket risk. Ad-hoc fields added by a caller do not repair its source contract.
- The older Macro portfolio client re-normalized covered names and defaulted weights. A covered subset must not be labelled the user's complete sized portfolio.
- OI comments conflate position date with publication-labelled date. Reconcile at the existing owner; do not add a blanket second shift.
- Retain the source's weak/negative bar-direction and crowding results. New presentation is not evidence overturning them.

Continuation collision observations: open Factor Atlas S1 #8680 owns factor measurement/source readers; S2 #8677 owns pressure research; S4 #8703 owns native F04 evidence previews; S6 #8696 owns empirical acceptance. The inspected changed paths are disjoint from the new S3 files. S1 head observed `ddf1f07f2059caebb4bfa6b1db6c4008dd97859c`; S2 `8235a335ae866b51484bac8de81383cfce81e745`; S6 `1cc1a3b245311dbc21af548018c1d2b7d5d08684`. These observations neither release those carriers nor authenticate an active worker. Preserve Terminal #780 and #686/#723 ownership; no edits or merge are part of this slice.

## 2. LIQN parity: evidence versus inference

The original investigation found public product/feedback references to factor and basket weighting/navigation, portfolio X-ray and portfolio-risk use cases. It did not obtain an authenticated reproducible numerical options surface or a published proprietary algorithm. The matrix below is a reconstruction programme, not a claim that LIQN uses the proposed formulas.

| Feature to compare | Verified boundary | Plausible mechanisms to discriminate | Mastermind decision |
|---|---|---|---|
| Factor IV / standardized IV | Useful product target; exact LIQN algorithm not verified | Weighted mean, RMS, index/ETF proxy, covariance-derived synthetic number | Show separately labelled constituent statistics and modeled risk |
| Skew / risk reversal / curvature | Numerical methodology not recovered | Strike-based differences, constant-delta interpolation, wing/ATM ratios | Constant-delta definitions only after root surface qualification |
| Expected move | Exact distribution/horizon convention unverified | IV sqrt(time), ATM straddle, historical quantile, covariance model | Explicit model and horizon; no automatic probability |
| Top options metrics / activity | Detailed trade-classification mechanism not verified | Gross volume, OI, approximate premium, quote-signed trades | Preserve observed/activity/estimated distinctions |
| Crowdedness / short-interest factor | Underlying score, weights and timing unverified | Ownership overlap, short ratios, co-momentum, composite | Separate evidence facets; no opaque fused score |
| Portfolio X-ray / risk | Public references, not authenticated numerical validation | Membership sums, univariate betas, multivariate risk attribution | Existing positions plus explicit exposure and marginal risk |

Discriminating observations for a lawful future comparison: change only basket weights; remove low-IV or high-IV constituents; compare an actual ETF option surface with its holdings; hold constituent IV fixed while correlation changes; inspect behaviour with 30–50% missing names; ask whether rank changes from membership revision rather than volatility; compare long-short hedges under higher correlation; inspect exact expiry/known-at clocks. Record UI observation date, input identity and output, without copying proprietary rules or restricted membership datasets.

A defensible competitive advantage is reproducibility and honest uncertainty. Numerical superiority requires matched live observations or preregistered replay; it is not demonstrated by this candidate.

## 3. Actual data entitlement and historical-coverage assessment

The historical Massive manifest was probed 2026-08-08: options snapshots with IV/Greeks/OI were available, but last quote/trade fields were absent in the probe and options trade access was refused. The 2026-06-21 flow research describes a recent options-aggregate window, not deep tick history. Stock tick-depth evidence must never be relabelled options depth.

The public Massive entitlement record describes operator-confirmed stock-market rights. Preserve that record without copying confidential agreements, and verify dataset-specific option/exchange conditions separately. Feed response success and distribution permission are different gates.

ThetaData's historical record reports an options professional/private subscription and trade-stream entitlement, but also records an earlier streaming-login problem and unresolved filed redistribution scope. Those are historical operator/source statements, not a present successful login or a new license interpretation. The existing store layout distinguishes EOD, OI and optional vendor-IV history. A provider's advertised earliest date is not an observed complete history for every requested root.

Databento samples and signing calibrations were bounded historical studies. They are not a current full-universe feed or an authorization for additional spend. Participant-tagged exchange open-close datasets would provide a different evidence class, but no new purchase is authorized here.

Current continuation observation: invoking the existing `engine.thetadata_store.resolve_thetadata_store()` in the acquired M2 workspace returned no store. It checked the configured workspace data root and its existing ops-worktree fallback. No provider request or new collection was made. A public AAPL R2 artifact request in the earlier research returned HTTP 403; it has not been retried or obtained through a mirror.

Required owner data receipt before a real pilot: exact source-host/reader, selected historical anchor, root list, bytes/digests, position/observation/publication/known clocks, quote convention, surface quality, sample dates and gaps, exercise/multiplier identity, dataset-use decision, and caller freshness deadline. Raw licensed data must not be committed as a public test fixture. When the receipt is absent, the result is withheld rather than numerically filled.

## 4. Mathematical specifications — basket volatility

Let original long-only house weights be w_i >= 0 with sum w_i = 1. Let E be the eligible constituent set. Coverage C_w = sum over E of w_i; count coverage C_n = |E|/N; covered weights a_i = w_i/C_w. Report both original coverage and the covered-population denominator. Signed portfolio weights are a different contract and are not accepted by this initial house descriptor.

### 4.1 Root ATM and standardized 30-day IV

Record forward-ATM versus spot-ATM, call/put selection, exercise model, dividends/rates, quote mark convention, settlement time, and annualization. A nearest-strike or nearest-expiry scalar is not automatically a constant-delta or constant-maturity estimate. Root fitting remains with the options owner; the initial leaf consumes qualified root nodes rather than collecting/fitting another chain.

For bracketing calendar tenors T1 < T* < T2, interpolate total variance W(T)=sigma(T)^2 T:

`lambda = (T2-T*)/(T2-T1)`

`W* = lambda W1 + (1-lambda) W2`

`sigma* = sqrt(W*/T*)`

Use actual calendar-year fractions consistently, with 30/365 for the initial ACT/365F target. Exact 30-day nodes are admissible when independently qualified. No extrapolation or nearest-expiry substitution. Reject duplicate/invalid tenors and nonfinite values. A monotonic total-variance check is conservative quality control, not proof of an arbitrage-free surface across changing forwards and corporate actions.

### 4.2 Descriptive aggregations

`mean_IV = sum a_i sigma_i`

`RMS_IV = sqrt(sum a_i sigma_i^2)`

Weighted median is the smallest ordered sigma whose cumulative covered weight reaches one-half. Report the convention at exact ties. Effective covered names `N_eff = 1/sum a_i^2`; also show largest original member weight and largest omitted weight. Premium weights and inverse-IV weights may be research sensitivities, not silent replacements for the house factor's weights.

These answer how options on covered constituents are priced. They are not the volatility of a diversified basket. The first native leaf exposes mean, RMS and weighted median separately.

### 4.3 Rank, percentile and history

Min-max rank: `100*(sigma_now-min(history))/(max(history)-min(history))`; constant history produces null. Declare whether current value is inside the reference window and whether out-of-prior-range values can exceed 0–100. Percentile is an empirical distribution statistic; retain strict-less and midrank tie conventions explicitly. Averaging member percentiles is not the percentile of the basket aggregate.

A 252-session statistic needs 252 eligible prior observations under a specified calendar, methodology and membership policy. Report coverage rather than backfilling missing IV with current observations. Freeze methodology and known-at membership during historical replay; distinguish fixed-current-cohort descriptive history from historically known investable membership. IV histories truncated for UI display cannot silently serve as complete rank histories.

### 4.4 Skew, curvature, term structure and vol-of-vol

With a stated delta convention, `RR25 = IV(call,+0.25 delta)-IV(put,-0.25 delta)` and `BF25 = (IV(call25)+IV(put25))/2-IV(ATM)`. Opposite put-minus-call display signs are permissible only with different explicit labels. Fit/interpolate inside supported root delta brackets; do not infer 25-delta values from a smile lacking deltas, spot/forward or a pricing convention. Aggregate root measures over their own eligible population and disclose its coverage separately from ATM coverage.

Term slope uses actual supplied tenors. Forward variance between T1,T2 is `(sigma2^2*T2-sigma1^2*T1)/(T2-T1)`, not a difference of IV levels presented as a forward vol. Event-containing tenors are identified rather than smoothed into ordinary carry. Vol-of-vol may be the standard deviation of changes in constant-method log IV, with lookback, sampling and annualization disclosed; do not call it an observed volatility-option price. Every missing/sparse wing or expiry stays a gap.

### 4.5 Realized versus implied and portfolio expected moves

For log returns, RV = sample standard deviation times sqrt(trading sessions per year), commonly 252 for the stated US-session model. Calendar time is a separate convention: 30 calendar days is not 30 trading sessions. Carry both horizon units in every contract; use the incumbent market calendar for actual session mapping rather than inventing a weekend TTL/calendar.

The legacy IV-minus-RV spread is a descriptive difference between differently constructed measures. It is not automatically a variance risk premium, cheap/rich verdict, causal forecast or trade.

For an IV-scaled correlation model, D = diag(sigma_i), Sigma = D R D, and:

`EM_30 = sqrt(w' Sigma w * 30/365)`

R from historical returns makes this a hybrid model, not a risk-neutral joint implied distribution. Estimated implied correlation requires actual index-option information and consistent index/constituent variance, weights and horizons; constituent options alone do not identify it. An ATM straddle proxy estimates a different payoff/distributional quantity from one standard deviation. Never translate an uncalibrated model band into a precise containment probability.

Require aligned identities, symmetric finite positive-semidefinite correlation and full positive-weight IV coverage for initial full-basket EM. Do not discard unknown positions and re-normalize them away. Use historical, stressed and scenario correlations side by side. Compare sample, fixed shrinkage, estimated shrinkage and factor-model covariance under identical common-date samples; select by held-out risk calibration and stability, not attractive in-sample results. The original fixed-shrinkage reference is not an estimated Ledoit–Wolf implementation. Do not create a second production covariance owner in this leaf.

## 5. Dealer exposure and order-flow structure

Keep instrument/root and contract identities. Dollar gamma per specified fractional underlying move p is `s_j * Gamma_j * OI_j * multiplier_j * S_j^2 * p`, where s_j is the model's signed dealer inventory assumption, not observed OI. Use actual adjusted-contract multipliers/deliverables, not an unconditional 100.

A factor-level market exposure summary may sum comparable dollar sensitivity across deduplicated roots. It must state the root population and exclude accidental ETF-plus-holdings double counting. Do not average strikes denominated in different underlying prices into a fictitious basket wall. Keep walls by root; normalize distance by that root's spot or expected move for comparison. A common factor shock must state each root's shock/beta path before combining revalued hedge changes.

Vanna is a cross derivative of delta/value with volatility; charm is delta drift with time. Define volatility-point and time direction/units before aggregation. VEX is not a universal synonym: the inspected `vex_engine.py` is vega exposure. Vega exposure is not by itself the delta-hedging demand caused by a volatility shock. Reuse MSC's Greek conventions and models; do not change its sign authority in Atlas.

The long-call/short-put prior can be fragile in single names and concentrated baskets. Index conventions are also assumptions, not universally proven dealer books. Compare at least house prior, sign-reversed or uncertainty ranges, and actual entitled participant evidence where present. Preserve sign uncertainty and scenario dependence in every consumer. Participant-tagged open-close activity still needs starting inventory, coverage and lifecycle reconciliation to support an inventory estimate.

OI is a stock published on its own schedule. Carry `position_asof`, `published_at`, `known_at` and source date-label semantics separately. ThetaData documents morning OI representing prior-day positions; do not apply an extra lag to already publication-labelled data without tracing the owner. Missing OI is not zero. OI changes require comparable contract identity and known releases. Volume exceeding prior OI is activity intensity, not proof all trades open new positions.

Compute put/call volume, OI and premium as ratios of separately summed numerators/denominators. Zero denominators produce null; unknown categories remain unknown. Do not average root ratios without exposing that different estimand. Define 0DTE/near-expiry using contract expiry and the existing session/lifecycle owner. EOD 0DTE aggregates do not establish intraday inventory.

True gross traded premium is sum of trade price*size*multiplier after corrections/conditions. Minute close*volume is a proxy, not exact cash paid. Estimated net premium must sum signed trade/interval premium; applying a final contract sign to all its gross premium can materially overstate net direction. Quote/tick signing, delta-weighted flow and inferred opposite dealer side remain estimates. No NBBO means no claim of observed aggressor direction. NBBO itself does not expose beneficial owner or open/close status.

Sweeps/blocks require entitled trade/exchange/time/condition information and an explicit grouping/classification model. A large single-contract minute is not a proven block. Multi-leg and complex trades, spreads, late prints, cancellations and corrections need their own treatment. Premium unusualness and acceleration must use matched-minute/session, expiry, root and event baselines, robust scale and sufficient prior history. Their statistical abnormality is not an institutional-position assertion.

## 6. Positioning and crowding

Keep distinct panels for short interest, short-sale volume, borrow/locate observations, fund ownership, ETF composition, co-movement and options structure. Do not collapse different clocks and populations into a precise institutional-position estimate.

- Short interest is a dated position snapshot; its publication lag matters. Use float/share-denominator dates and corporate-action identities for ratios and changes. Short-sale volume is trading activity, not a running short-position balance. Days-to-cover depends on the selected ADV window.
- Borrow availability/fees are venue/account-dependent observations and may be unavailable. An absent borrow feed is not evidence that shares are unborrowable. No new broker/account integration is part of the pilot.
- 13F data uses quarter-end holdings and actual filing/acceptance availability. Separate filings, amendments, confidential treatment and security identity. Reported value divided by shares is a quarter-end mark proxy, not acquisition cost. Do not infer intraday fund transactions or complete derivatives/short exposure.
- Ownership concentration and overlap use the tracked-owner denominator. Days to exit at participation rate p is shares/(ADV*p), a scenario not a liquidation prediction. Preserve the existing prohibition on fusing ownership and short/options axes into one score.
- ETF look-through requires dated actual holdings, weights, cash/derivatives and identity. Rebalance exposure depends on a stated index/ETF rule and implementation assumption; membership is not evidence of executed flows. Deduplicate wrappers and underlying exposures.
- Residual co-momentum uses a stated market/sector residualization model and common sample. Report residual correlation, concentration, stretch and ownership separately. Retain earlier weak/negative timing results until genuinely new evidence passes the validation owner.
- Leveraged/inverse ETFs target daily exposure. Multi-day performance depends on the return path, fees and reset; multiplying a multi-day underlying return by stated leverage is not an accepted portfolio model. Conditional rebalance pressure is a scenario with current AUM/exposure assumptions, not observed compelled flow.
- Expiry, option exercise/assignment, buybacks, index changes and hedging calendars are conditional mechanical context. Connect to existing event/market-structure owners, not another event engine.

Options activity may be compared with Session 2's capital-pressure estimates only with matched populations, clocks and units. Agreement between two inferred signs does not promote either into observed institutional buying.

## 7. Portfolio factor X-ray architecture

Read sized positions through the existing user-scoped portfolio service. Hypothetical portfolios are request-scoped unless the existing persistence owner explicitly saves them. Unsized positions remain unsized; missing holdings never become a watchlist-based equal-weight portfolio without an explicit hypothetical label. Compute NAV, gross/net exposure, cash, leverage and FX under the portfolio owner's existing contract.

Membership exposure `e_k=sum_i w_i m_ik` is a taxonomy view. Overlapping memberships need not sum to 100%; offer nonexclusive exposure and a separately defined mutually exclusive sector partition. Do not mistake theme membership for a regression beta or count the same security twice after ETF look-through.

For factor model `r = B f + epsilon`, portfolio beta is `b_p = B' w`; covariance is `Sigma = B F B' + D_residual`. Ordered orthogonalization changes the interpretation of coefficients: retain order and do not mix independent raw single-factor shocks as if they were jointly identified structural effects. Residual covariance assumptions matter for concentrated theme books; a diagonal residual model can understate common omitted risks.

Portfolio sigma is `sqrt(w' Sigma w)`. Marginal sigma contribution is `(Sigma w)_i/sigma`; component contribution is `w_i*(Sigma w)_i/sigma`. Contributions sum to sigma and may be negative for hedges. Zero-risk/perfect-hedge cases must not divide by zero. For covariance/factor contribution charts state whether the denominator is variance or volatility. Never force every contribution positive for display.

Stress correlation is scenario-specific. Higher correlation can reduce a long-short spread's risk, so a universal 'higher correlation means more portfolio risk' assertion is false. Evaluate market, rates, FX, sector/theme and residual scenarios with explicit joint shocks, historical windows and factor-model uncertainty. Historical drawdown attribution must state path, rebalancing and valuation assumptions; arithmetic single-day attribution does not automatically decompose a compounded drawdown.

Options positions require actual contract identity, signed quantity, premium/market value, deliverable, expiry, exercise model, spot/vol/rate/dividend inputs and marks quality. Delta-equivalent exposure is useful but not complete nonlinear risk. Delta-gamma-vega-charm approximations are local scenarios; large/event/near-expiry moves require qualified revaluation. Synthetic spreads preserve legs and sign; no autonomous position sizing or execution is introduced.

The initial S3 source candidate deliberately does not add portfolio storage or production risk math. Its long-only house input refuses negative descriptor weights. Signed-risk examples remain research, and future portfolio work goes to the incumbent position/risk owners.

## 8. Typed native read contracts and integration boundaries

The code in `engine/options_basket_aggregation.py` defines frozen in-process DTOs:

- `Definition(factor_ref, source_ref, source_sha256, known_at)` references the incumbent factor identity; it does not mint or persist one.
- `Member(root, weight, iv, observed_at, known_at, qualified, premium, source_ref, source_sha256, valid_until, method, tenor_calendar_days, year_basis)` carries annual-decimal IV. Accepted initial methods are exact-30 or total-variance-30 under ACT/365F. The source owner supplies quality qualification and its freshness deadline; there is no default 36-hour TTL.
- `Correlation(roots, values, source_ref, source_sha256, observed_at, known_at, valid_until, method)` binds ordered identities to historical/scenario correlation. A matrix without eligible source metadata cannot produce model risk.
- `Policy` carries explicit provisional descriptor thresholds: >=80% original weight, >=80% positive-weight names, >=3 eligible names, and no omitted name above 10% original weight. These are conservative product policy, not statistically proven universal cutoffs. Full expected move requires 100% positive-weight IV coverage regardless of descriptor eligibility.

`aggregate(...)` returns `options_hub.factor_options/v1`: definition provenance; horizon; original coverage/exclusions; covered mean/RMS/weighted median/effective names; an optional descriptor headline; separately labelled hybrid expected move; reported-premium concentration; input receipts; correlation method/receipt; warnings and reason codes. Display-only is true; publication, Prophet and sizing are false. A future native publisher must consume these through the existing Options Hub authority; this source change installs no caller or endpoint.

`engine/options_basket_inputs.py` is the next dependency implemented in the same candidate. `ArtifactReceipt` plus exact bytes enables `inspect_legacy_vol` and `legacy_house_view`. The decoder verifies SHA-256, size, UTF-8, object shape, duplicate keys, finite JSON and root/date identity. The existing caller, not this module, selects the source and supplies its receipt. A matching hash proves bytes, not authenticity or license.

Legacy values stay unqualified even if supplied with invented `qualified`, `known_at` or method keys. Unknown/future artifact availability suppresses numerical values for an as-of read. The current equal-weight registry adapter retains missing roots in its denominator and labels its population hindsight/current-registry, never a PIT backtest. Its schema is `options_hub.factor_legacy_inspection/v1`; qualified IV30 and hybrid risk are always null. No raw-chain cache or provider path is added.

Future positioning contracts must carry metric-specific population, sign/model class, OI position/publication clocks, gross/net units, correction lineage, observation/estimate vocabulary, expiry/Greek conventions and authority. Future portfolio contracts must reference the existing position revision, NAV/FX basis, modeled/unmodeled gross coverage, betas/covariance version and scenario assumptions. They are extensions through existing owners, not new stores.

## 9. Validation, sparse data and acceptance

Mandatory negative cases include missing/empty/zero distinction; booleans/strings/nonfinite numeric values; wrong or duplicated identities; incompatible tenor/year basis; future or unknown known-at; stale source deadlines; invalid covariance dimensions, asymmetry, non-PSD matrices; membership changes and current-versus-PIT confusion; adjusted multipliers; absent/poor wings; wide/locked/crossed/stale quotes; wrong settlement/expiry; and corporate-action mappings.

With 30%, 40% or 50% of names missing, full-basket expected move is null. The eligible-subset descriptor may remain visible with its true denominator; under the initial headline policy those sparse cases do not emit a headline. Missing a 40%-weight name cannot hide behind 90% count coverage. One name dominating 90% of reported premium triggers concentration disclosure, not a silent switch to premium-weighted factor IV.

Source-time admission applies to activity and diagnostics as well as the main risk number. Excluded future/unqualified IV cannot leak through an `inputs` field; stale/future/unidentified premium cannot contaminate concentration. Timely activity can remain visible when IV quality alone fails. Refusal payloads must remain JSON-safe, including NumPy scalar and malformed-metadata inputs.

Replay must use existing source/version selectors and their known-at receipts; this leaf creates none. Freeze basket/method/weight versions and use only information known at each anchor. Evaluate rolling calibration of squared returns versus modeled variance, containment by horizon/regime, stress losses, estimator sensitivity and selective coverage. Use date blocks/overlap-aware inference, not constituent observations as independent portfolio trials. Forward predictive/promotional claims remain with S6 and the existing epistemic gates.

Cost/cadence: reuse per-root published observations rather than refitting chains per basket. For N members, descriptor aggregation is O(N log N) including sorting, expected-move multiplication O(N^2), and the present PSD check O(N^3). Keep small pilot cohorts; a governed covariance owner may later supply reusable qualification. Update nightly/EOD first; intraday activity has separate readiness. No second polling loop. Report measured runtime from receipts rather than promising production latency from a small unit suite.

Acceptance levels: mathematical synthetic tests; native source-contract tests; entitled historical-data receipt; held-out/replay calibration; authenticated UI and degraded-state proof; governed publication/deployment. Passing an earlier level never implies the later levels. Current native-store resolution failure and a separately refused producer-integration test append are explicit outstanding proof boundaries, not disguised as successful live acceptance.

## 10. Prioritized native waves and exact next commission

| Wave | Independently useful result | Prerequisite / owner | Acceptance and rollback |
|---|---|---|---|
| S3-A | Pure qualified IV statistics and hybrid EM, original-weight coverage | Existing definition and risk/vol source contracts | Deterministic tests; no caller/publication; remove only leaf integration if later rolled back |
| S3-B | Exact-byte legacy inspection with honest withholding | Existing Options Hub source selection and receipts | Digests/clock/identity/duplicate tests; no ad-hoc qualification |
| S3-C | One accepted house Mag7 historical measurement on actual source host | Existing historical reader, source-quality/rights and covariance receipts | Real positive or traceable withheld run; no new collection; persist derived receipt only |
| S3-D | Qualified root 30-day ATM/constant-delta terms and historical replay | Options owner rich source contract; Session 1 membership; S6 evaluation | Sparse-chain, events, quote-quality, PIT and estimator sensitivity; no risk publication until admitted |
| S3-E | Factor options UI using the existing Terminal workspace/read path | Accepted artifact contract and source publication | Real authenticated root/basket switch, stale/empty/partial views and no synthetic-surface language |
| S3-F | Root-level exposure/activity and independent positioning facets | MSC, trade/OI ownership, ownership/ETF/short feeds | Sign uncertainty, true publication clocks, deduplication, trade conditions and source-specific rights |
| S3-G | Portfolio factor X-ray and nonlinear positions | Existing portfolio/risk services and qualified position marks | RLS, unsized/unmodeled coverage, negative contributions, stress scenarios; no autonomous sizing |

S3-A and S3-B are the source candidate in this operation; read the cumulative continuation for exact test and publication evidence. None of the later rows is marked built by this table.

### Executable S3-C commission

Outcome: run the existing qualified aggregation on the registry-listed Mag7 cohort at one accepted common historical anchor, comparing mean, RMS, median and the IV-scaled correlation model. Candidate members are AAPL, MSFT, NVDA, AMZN, GOOGL, META and TSLA; the current owner, not this report, must supply the exact admitted definition and weights.

Allowed next work: inspect the existing source-host/reader binding and its nonconfidential receipts; consume already held EOD/historical observations; supply verified root methods/quality/deadlines, identity and covariance; run the existing leaf; save a compact derived receipt on this carrier. No provider purchase/login change, new collector/store, public raw fixture, MSC sign edit, options-to-Prophet promotion or production deployment.

A successful receipt includes operation and immutable source head; original definition/weights digest and knowledge boundary; data refs and root coverage; true observation/publication/known clocks; quality/corporate-action exclusions; covariance sample/method/identity; calculation assumptions; commands/results/output digest; and separately stated remaining gates. A correct withheld real-data result proves withholding only, not complete user capability.

The current local resolver returns NONE. Qualifying an already existing source host is the next data dependency; do not invent a new store or turn the prior R2 403 into permission to switch mirrors. The denied integration-test append remains unapplied and must not be replayed through another carrier. Other ordinary source/test work remains governed by current assignment and source custody.

### Research references and interpretation

Internal source anchors use the historical source pins in section 0 unless a native receipt states otherwise: `research/OPTIONS_FLOW_DATA.md`; `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`; `research/licenses/THETADATA_ENTITLEMENT_RECORD.md`; `data/massive/capability_manifest.json`; `data/baskets/membership.json`; all engine paths in section 1; Terminal `docs/OPTIONS_SUPERINTELLIGENCE_MASTERPLAN_2026-07-31.md`, `docs/MARKET_STRUCTURE_CORE_MASTERPLAN_2026-08-01.md`, and `docs/audits/2026-08-08-options-prophet-system-audit.md`.

Primary/public research retained from the earlier investigation: Cboe implied-correlation methodology (`https://www.cboe.com/us/indices/implied/`); Cboe exchange Open-Close dataset documentation (`https://datashop.cboe.com/cboe-options-open-close-volume-summary`); ThetaData historical open-interest documentation (`https://thetadata.net/docs/operations/option_history_open_interest.html`); FINRA short-interest publication/reporting documentation (`https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest`); SEC Form 13F filing requirements; original covariance-shrinkage and portfolio-risk literature referenced in the expanded report; and the options trade-direction classification study identified there. LIQN public feedback (`https://feedback.liqn.ai/`) is product-reference evidence, not numerical-methodology proof.

This continuation does not claim a fresh external subscription, legal, market or competitive audit. Its new evidence is native code, negative-data behaviour, exact source custody and the current source-reader preflight. The product and measurement gates remain explicit.
