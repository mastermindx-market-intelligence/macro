# R30 + R31 data and model contract

**Current binding update:** [R31 source-bound data contract](r31/data_contract.md) and [machine-readable owner map](r31/source_bindings.json). Terminal Investigation v2 and Alerts are now identified. Bond evidence/scenario admission and the compound rule still require extensions to those existing owners. The baseline unresolved-owner wording below is retained as the R30 historical record, not the current finding.

## Accepted R30 baseline

## Authority and scope

R30 is a read-first research/design extension of the existing Bonds/Forex programme. It does not introduce a new market-state engine, alert store, probability owner, evidence database or deployment. The shapes below are requirements for UI bindings and acceptance; they are not newly registered production schemas.

Repository source was pinned at Macro **62a3f9ad070c7583687aef8c30d53fd1764c6aab**. The reviewed builder is scripts/build_macro_context.py, _build_decision_workspaces. Its output is macro_context.decision_workspaces.v1 with display_only true, claim_scope projection_only and probability_policy withheld. The inspected source supports selecting canonical fields, preserving gaps and dates, and presenting mechanism evidence. It does not grant signal or monitoring authority.

## Verified source paths and exact missing bindings

| Capability | Existing source / fields inspected | UI use | Required implementation work |
| --- | --- | --- | --- |
| Current Bonds interpretation | decision_workspaces.bonds.current_read: health, cycle, duration_lean, curve_trade, yield_curve_regime, recession_risk | Route 01 contextual labels | Preserve source receipts and status; do not turn a projection label into a live recommendation |
| Rates and curve context | world_state.rates_credit.bond_compass.duration / curve_trade; fed_path.policy_rate and implied_bp_12m; mechanism_evidence.real_10y, term_premium, curve_slope_10y3m | Route 02 decomposition and context | Bind a real, internally consistent curve. The available 10Y–3M field is not the 2Y–10Y specimen |
| Equity transmission | rates_credit.drivers_for.equities: note_en, hy_oas, credit_canary, stock_bond_corr where present | Route 05 rates/credit-to-equity evidence | Preserve identity, horizon, method and missing fields; no independent vote per derived view |
| FX and funding | world_state.fx_dollar plus cross_asset_flows.asof, regime, funding_state and confirm.verdict | Route 05 and Forex context bridge | Existing verdict remains attributed to its owner; no new R30 authority inferred |
| Direct USD basis | decision_workspaces.forex.funding_evidence.direct_usd_cross_currency_basis; proxy_funding_state / proxy_asof separately | I06 / I08 | A missing direct series remains unavailable. The builder explicitly forbids substituting CNH basis or funding proxies |
| Issuer filing facts | capital-structure-intelligence; capital_structure.event.v1 and related filing/event/edge provenance | I05 dated facts | This is not a complete maturity/covenant/committed-facility feed. Map legal obligations and roll-forward in the existing owner before claiming coverage |
| Exact CDS observations | No matching top-level dataset established in the bounded local catalog search | I07 current/absent quote states | Resolve licensed reference-entity/instrument feed, conventions, contributors, availability clocks and entitlements |
| Capital substitution | Scheduled issuance fixture and research proposition; no observed buyer allocation link established | Route 04 and capital mechanism in I03 | Resolve holdings, allocation/flow source and investor eligibility. Do not infer origin/destination from price direction |
| Saved cases and monitors | Reusable Paper patterns identified; canonical runtime owner not established by this source review | Route 08, I04, G02 | Resolve existing persistence, revision, evaluation and notification owners. Do not add a parallel store |
| Empirical likelihood | No new R30 model evaluation | I11 withheld/qualification states | Register exact target/horizon and dataset version with the existing evaluation owner, then qualify out of time |

Relevant source dates/gaps already exist in the projection. In particular, the builder retains stale input keys including us10y, real_10y, term_premium, hy_oas, repo and sofr_iorb. Its source receipts distinguish absent, known and anomalous future dates. The UI must not collapse these into reassuring green statuses.

## Bounded read-only data evidence

The connected Data Workspace adapter reported implementation revision **e5e84272bc9128e2577f907de4d4960e84950a9b**. Only capabilities, catalog/description and bounded read operations were used. No Lab run, ingestion, historical model test or production qualification was performed.

### Rates snapshot

- Reference: macro_snapshot:rates_command/latest.json.
- Observed schema: rates_command.v1.
- Data as of **2026-10-08**, built **2026-10-10T11:17:55Z**.
- display_only true; authority false.
- File version: statv1:c46851ac13ae8fb87dc110385269c82e04dd272e1942fb9572607e8adc979e2c.
- Read receipt: 7d441e8b5ef39c07bc024ca4cb4b006ecc7b4dd112743f38220a90d99af4ea5b.

The observed snapshot is dated evidence. Its build date cannot make it an 18 October market observation. The UI fixtures were not populated from this snapshot.

### Macro vintages

- Reference: macro_snapshot:fred_vintage/vintages.parquet.
- Described extent: 16,518 rows, 236,861 bytes; series, period, value, realtime_start, realtime_end.
- File version: statv1:10becad3365aeb18d0369ffcdcda486c9f1fc5f285d468b7bd531b767be29937.
- Registry: macro.fred.vintages; owner macro-dashboard; producer collectors/fred.py::fetch_vintages; revisable release; ALFRED date-published clock.
- A six-row read filtered realtime_start to 1–8 October 2026. It observed series including PAYEMS, WEI, RECPROUSM156N and THREEFYTP10.
- The scan was **incomplete**: 4,246 of 16,518 rows scanned, next offset 4,246.
- Read receipt: cde80872dadc0fe4c3af00be50f8c2496a39f8c8b2a1b14ca3e52fbbbb36ee16.

This establishes date-level versioned macro data in the inspected local binding. It does not establish comprehensive instrument history, intraday knowability or a particular model family for an unbound term-premium field. The statv1 values are metadata version identifiers, not asserted content hashes.

The exact local reference macro_snapshot:macro_context.json returned SOURCE_NOT_FOUND. That result describes that local binding; it does not negate the verified repository builder or prove absence throughout production. Likewise, the bounded CDS catalog search is not an exhaustive audit of every data source.

## Shared case and observation requirements

Bindings must preserve existing canonical identities. Conceptual UI properties are:

- Case identifier and explicit revision, selected hypothesis and initiating question.
- Instrument identifiers, legal issuer/obligor where relevant, benchmark, curve type, tenor, duration and seniority.
- Base currency, quote direction, hedge tenor, comparison horizon, mandate and eligible universe.
- Analysis horizon, market calendar, close convention, observation cutoff, availability cutoff and vintage.
- Observed, derived, estimated, research, manual scenario, replay or synthetic mode.
- Selected evidence IDs, source revisions, return route, active selection, scroll and focus.
- Explicit saved configuration and evaluation identities for persistence or monitoring.

An observation must carry its value or a typed absence; unit; denominator/baseline; instrument/entity; market timestamp; availability timestamp; observation period; vintage; ingestion/build time separately; source/license; revision lineage; transformation version; and applicability/freshness policy. The user need not read all fields at glance. I01 and I03 expose them when needed.

Evidence identity and independence are separate. One yield series can appear in a chart, momentum measure, technical level test and duration estimate. Those descendants retain one underlying lineage. Two publishers repeating a release do not produce two independent economic observations. CDS and cash spread differences can add information, but are not automatically independent confirmations of an issuer’s solvency. Shared observations can support competing hypotheses without multiplying the support count.

Current evidence may advance while a saved case remains frozen. Revisions must permit comparing what was known then with what is now known, including source corrections. Synthetic fixtures and display-only projections cannot enter a qualified observed-support count.

## Financial calculations and comparability

### Yield decomposition and duration

For a declared matching model/curve, nominal yield can be decomposed into an expected short-rate component and term premium. The real-yield/inflation-compensation view is an alternative decomposition; it is not two extra independent votes. Inflation compensation includes risk/liquidity effects and is not a pure forecast. Model family, vintage, tenor and curve convention are mandatory.

Treasury specimen:

- D = 7.8 years, C = 64 years squared.
- Price fraction ≈ −D × change in yield + 0.5 × C × change in yield squared.
- −25 bp gives +1.97%; +25 bp gives −1.93%.
- Scenario expected-rate change −10 bp plus term-premium change +2 bp gives net −8 bp and approximately +0.63%.

Corporate specimen uses **benchmark-rate change**, not all-in corporate yield change:

- Rate duration 5.5 × −8 bp produces +0.44%.
- Spread duration 4.7 × +40 bp produces −1.88%.
- Net first-order price effect is −1.44%.

These calculations exclude carry, roll, FX, transaction costs, taxes and option/nonlinear effects unless separately supplied. A large-shock or optioned instrument requires the appropriate pricing model; a simplified chart cannot certify that model’s applicability.

### Buyer and issuer comparisons

The investor fixture compares a JPY-based, investment-grade mandate with duration eligibility of 7–10 years. Its indicative number is yield less the **current annualized rolling-three-month hedge cost**. It is not a locked return through the bond’s maturity. Keep day count, annualization, spot/forward direction, quote time, collateral and future roll assumptions inspectable. The eligible sovereign instruments still have duration differences.

The AI basket fixture has different duration and risk and is outside the selected mandate. Do not crown its 9.30% headline yield as the buyer’s preferred alternative. The 5 bp Treasury/JGB ordering is especially fragile to hedge renewal and costs.

Issuer-currency comparison holds the borrower, seniority, tenor and resulting base-currency liability constant. Do not compare different countries’ raw sovereign yields as if they were the same issuer’s executable financing costs.

Scheduled gross issuance less redemptions is a supply measure. Settlement dates, cash reinvestment, currency conversion and buyer behavior matter. It is not an observed flow map.

## Monitor contract for the displayed example

The displayed thresholds are a **synthetic configuration**, not current trading levels.

The binding must identify the selected 10Y benchmark, provider’s close convention, calendar/timezone, peer-basket version, baseline close, input freshness rules, availability-lag policy and evaluation cutoff. These are required configuration fields; until the existing owner resolves them, save is a draft/configuration effect rather than qualified activation.

For a deterministic acceptance fixture, define the peer basket as twelve eligible, convention-matched peers with frozen equal weights and all twelve required observations. Peer breadth counts those whose OAS increased at least 15 bp from the prior close. The monitor’s separate basket condition is a mean OAS increase of at least 15 bp; the breadth count is not substituted for that mean.

Conditions:

- Confirm only when the selected 10Y yield closes strictly below 5.08%, peer-basket OAS increases at least 15 bp, and the fresh, aligned funding evidence is explicitly orderly.
- Invalidate when the selected 10Y closes strictly above 5.22% or fresh valid funding evidence establishes stress.
- The observation and availability clocks must pass the per-input policy; a lower-frequency release cannot be made contemporaneous by changing its build date.
- Evaluate five eligible market-session closes after the case’s opening cutoff. A data pause does not silently extend this calendar.
- At the fifth close, evaluate valid invalidation, then confirmation, then expire an unresolved case.
- Fresh known invalidation takes precedence even if another input is unknown. Otherwise unknown/stale critical evidence pauses confirmation.
- Confirmation remains subject to invalidation while the window is open. Closing the window freezes the outcome. Invalidated, expired or closed outcomes are terminal for that window.
- Late evidence is audited and may be reviewed in a new revision; it cannot silently backdate or reopen the closed result.
- Save, activation, evaluation and notification each retain canonical identity. Deliver only the configured state-change events, deduplicated by that owner.

This separates a useful monitor of an unresolved question from an asserted predictive signal.

## Replay and empirical continuation

ALFRED realtime_start is date-level metadata. For intraday replay, same-day observations without independently verified availability time are excluded, or the entire analysis visibly operates at a coarser resolution. This admission rule applies to features, derived indicators, model inputs, annotations, filters and source summaries as well as plotted values. Ingestion time is not an invented publication time.

Before producing any R30 likelihood:

1. Register a precise target and horizon. For a continuation template, freeze ex-ante confirmation/invalidation boundaries and their generation rule at the decision cutoff. Define tie handling and incomplete future windows. The fixture’s absolute 5.08% boundary is not a universal historical training label.
2. Keep arbitrary user monitor configurations distinct from qualified forecast targets. A model trained for one target cannot supply a percentage for another configuration by renaming its output.
3. Assemble licensed point-in-time price, spread, financing, release and funding data with known publication clocks, revisions, survivorship handling and eligible universes.
4. Preregister features and transformations. Technical structure may use close-confirmed breaks/retests, volatility-normalized distance, slope/curvature, momentum and cross-asset relative strength, but each needs a fixed lookback and benchmark. Yield/price duplicates remain one family.
5. Compare a hierarchical or competing-risk model with unconditional/regime base rates and simple price-only/rates-only baselines. Any proposed nonlinear model must demonstrate useful incremental information.
6. Use chronological walk-forward evaluation; train transformations on training data only; purge overlapping label windows at split boundaries; cluster/bootstrap by distinct stress episodes and report effective sample size.
7. Evaluate calibration, Brier/log scores, discrimination where relevant, uncertainty and coverage. Show the full cohort and failure cases, not selected anecdotes. Market reaction prediction and trading profitability require separate validation.
8. Define missing-input, regime-shift and out-of-distribution abstention, and the freshness/version conditions that suspend likelihood display.
9. Record reproducible evaluation receipts with the existing research/model owner before exposing a percentage. The ongoing October 2026 episode is not a completed historical outcome label.

No such R30 empirical test was run here. The finished interface presents conditional paths, sensitivity, evidence and next checks while keeping qualification inspectable.
