# Target-and-scope decision and baseline specification R1

Continuation of PR #9507. Governing procedure pin remains Mastermind `50107c31531d3b4ab5a18b5acf5e77954a0549e3`; source interfaces inspected at Macro `3ab3382af89242c7b7fe8c65360bd883a7dd3504`. These are selected design choices for the current research commission, not a native V3 amendment, trial registration, held-window read, trading mandate or production permission.

## 1. Resolve the scope now

**Track A remains the existing native seven-pair Leadership Rotation study.** Preserve its H1/H2/H3, frozen cohort, source restrictions, original negative evidence, later amendments and LR-W6 size/power/read gates. This package does not rename those hypotheses or replace their data with a more convenient source.

**Track B first studies allocation among actual US sector ETFs.** The economic object is a sector-instrument allocation, not the ranking of member stocks inside a current sector label. The question is whether a reproducible selector/policy adds net value over simple sector and cash alternatives. Group beta is assessed before residual stock alpha. Industry/theme transfer, macro and flow feature increments, and stock expression follow as separately specified studies under the existing research owners.

The first information set is price-only **as a baseline**, not because technicals are presumed sufficient. Its purpose is to establish a fair hurdle for independent economic information. A collector presence, persuasive causal narrative or sophisticated model is not a reason to skip that hurdle.

### Construction-specific DNR reconciliation

The current Macro DNR entry `KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE` cites a null for the specific rank-linear, as-of-now GICS group-feature construction. Direct review of Mastermind `research/TREND_PERSISTENCE_PREREG_C1.md` at the governing pin, blob `8f280bd41430dc0b49551783a1066b42b068ce8d`, confirms its primary target: **member-stock** forward-return ranking beyond a strong stock-level baseline, using group attributes and current sector labels. It is not a reported test of allocating among eleven traded sector ETF instruments.

Accordingly, the present baseline specification does not re-run C1, use its outcome panel, revive its seven group features or carry its failed hypothesis. This distinction grants no permission to recycle that construction later: stock-alpha, group-context and theme-first-stock-second claims must preserve C1's negative evidence and the exact prospective reopening requirements. New words, a new family name or the same features with slightly different lookbacks do not cure a construction-level prohibition.

The prohibitions on rotation×cycle-position entry confluence, RS-dispersion gates, connect-flow gating, LLM detection and parallel shock classifiers remain. Economic mechanism research is not a licence to rebuild those gates. Any exact collision is resolved before that proposed experiment, without blocking disjoint source/metadata work.

## 2. Fixed first population and cash representation

The primary selection universe is XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV and XLY. SPY is an equity benchmark. BIL is a **bill-ETF proxy**, not a literal Treasury account or risk-free return, and is the first proposed implementable cash comparison. This identifies thirteen input series, not a claim that thirteen source histories are qualified.

Use actual instrument eligibility and first traded observations. XLC's sponsor identifies inception June 18, 2018 and exchange listing June 19; XLRE inception October 7, 2015 and listing October 8. Do not create a pre-listing executable close. Sector composition can change while the ETF remains tradable; report taxonomy breaks when interpreting economic exposures. Do not manufacture stable historical industry exposures from today's holdings.

All eleven sectors must satisfy a common formation-date source/feature condition in the primary comparison. A missing sector does not silently shrink the universe to the convenient nine. Any reduced-cohort study gets a separate explicit population and cannot be used as proof of the eleven-sector claim.

BIL returns require the fund's dividend-reinvested return basis, actual instrument dates and the same valuation endpoints as equities. Do not use a trailing yield as a holding-period return, forward-fill past the last observed date, or subtract the fund expense ratio a second time from a net fund return series. Transaction costs of actually entering or leaving the proxy remain separate. A literal bill ladder is a later cash-instrument study with its own price, maturity and reinvestment contract.

## 3. Fix the experiment's timing geometry

Use the incumbent exchange calendar, not calendar-business-day arithmetic.

- Market-information anchor t is a completed eligible exchange session. Predictor price windows end at t.
- Decision information cutoff is 08:00 America/New_York on the next exchange session e. Every required source must actually be known by that cutoff for a naturally observed forecast. A decision may be recorded at 08:05 after the cutoff; processing latency must be retained.
- The historical execution proxy is the close of e. It is not the signal close at t, an opening fill, an actual order execution or proof of attainable spread/impact.
- The primary valuation endpoint is the close of the twentieth exchange session after e. Thus an entry at e holds through e+20; do not mix twenty observations with twenty elapsed sessions.
- Primary sequential policy decisions use non-overlapping twenty-session holding blocks on one fixed anchor. The first eligible anchor is the first session on or after January 2, 2020 with the complete required warmup and source coverage. Later boundaries are advanced by the calendar, not re-anchored after a missing observation.
- A daily-origin twenty-session forecast diagnostic may later be studied, but its overlapping labels cannot be reported as independent policy trades or naively compounded into a CAGR.

At a sequential policy boundary, previous-period wealth is marked before the next rebalance. Value continuing holdings with their actual drifted weights; do not pretend the portfolio is still at its original equal weights. Charge costs only for actual changes. A switch of the whole book from sector A to B includes a sale and a purchase, not one leg. Initial entry and final liquidation have explicit treatment.

Historical adjusted-close series support a **reconstructed next-close total-return proxy** when their original availability/fill evidence is absent. They must not be described as naturally recorded orders or historically known forecasts. Reconstructions may be useful development material once source use is qualified; they are not promoted into prospective evidence.

## 4. Comparator definitions

These rules are selected to remove analytical discretion before outcomes, not because they have been shown optimal. Equal weights here are experimental comparator rules, not recommended account allocations.

| ID | Rule |
|---|---|
| B0 | Hold BIL throughout the common comparison interval; include actual prescribed opening/closing transaction costs |
| B1 | Hold SPY over the identical interval, with the same entry/exit and cost conventions |
| B2 | Equal-weight the eleven eligible sector ETFs at each scheduled rebalance, with weights drifting between rebalances |
| B3 | Compute each sector's trailing 63-session log total return minus SPY's over the same endpoints at t; select the top three and equal-weight them for the block |
| B4 | Start from B3's three selected slots; a slot is invested in its sector only when that sector's trailing 63-session log total return exceeds BIL's over the same endpoints; otherwise that one-third slot goes to BIL. Aggregate identical BIL slots before charging turnover |

A rank tie is broken by lexicographic ticker order solely for deterministic replication. The fraction and materiality of ties are reported. No threshold tuning, alternate lookback grid or winner-selecting between these baselines is silently allowed. B3 tests relative selection; B4 adds a simple absolute cash hurdle. An advanced model must compare against both the fully invested and cash-aware baselines rather than choosing whichever is easier after results.

Required warmup is at least 252 prior exchange sessions with the basis and completeness needed for all declared features and benchmarks. This is an engineering eligibility condition, not a claim that 252 observations establish statistical power or source rights. The source-readiness audit has not yet certified complete histories or the first executable anchor.

## 5. Outcomes, costs and failed inputs

Primary descriptive policy comparison: the difference in log terminal wealth between two policies started with identical capital and evaluated on common dates. Report complete daily wealth paths, maximum drawdown, realized risk, turnover, bill occupancy and comparison coverage as separate outcomes. Never conflate simple return differences with relative wealth ratios.

Use 10 basis points per actually traded dollar per one-way transaction as the **declared base-cost scenario**, with 5, 25 and 50 basis points as mandatory sensitivity scenarios. These are stress assumptions, not estimates of current market spreads or historical capacity. No net economic or production claim is qualified until actual plausible costs, liquidity and order-size assumptions are validated. No additional fund expense charge is added to a return series already net of that expense. Taxes and account-specific effects are excluded and disclosed.

The cost comparison uses full turnover across risky and bill instruments. Normalizing post-cost target weights must be self-financing; a future evaluator must solve its capital/cost equation consistently rather than obtain free cash from renormalization. Cash held while waiting earns only the specified qualified proxy return. No short borrow, leverage or options are inserted into this long-only baseline.

A missing required input creates an **unavailable research decision**, not an invented zero return, silently reduced universe or evidence that the cash forecast was correct. The primary all-policy comparison retains the complete calendar of intended decisions and reports unavailable/immature/unpriceable cases beside results. A continuous portfolio is not restarted with fresh capital after an inconvenient missing mark. Sparse complete cases may support a labelled episode diagnostic, but not an invented uninterrupted equity curve.

A later operational policy for feed failure—retain positions, stop new trades, or a mandate-specific contingency—is distinct from the forecast's chosen allocation and must be qualified separately. Absence of a price does not by itself authorize liquidation at an imaginary price.

## 6. What remains to register before empirical use

The deterministic baselines and timing geometry above are now explicit. An advanced challenger is **not yet fully registered**: exact feature transformations, fitting/tuning budget, source qualification, economic margin, hypothesis-family accounting, dependence-aware estimator and untouched/prospective evidence must be bound before its confirmatory use.

Use the current TrialLedger and HoldoutVault owners. `TrialLedger.effective_n` counts configurations for multiplicity; it is not the effective number of independent sector-date observations. `register_trials` is a writing decorator/context manager, not a harmless metadata lookup. `HoldoutVault.consume_authorization` spends access under its existing identity/history contract; a new document or a successful schema check must not invoke it implicitly.

Prior studies and all already explored history remain on the prior-exposure record. A new Track B family must account for related prior search; it cannot reset scientific evidence by changing its name. No real-data trial, declared-budget write, seal, peek, dataset generation or native P1/P2/P3 action was performed in this continuation.

## 7. Immediate research order

1. Carry the concrete source defects and thirteen-series coverage requirements into the existing source/readiness owner; do not build another capture system.
2. Qualify source rights, historical basis, available observation images, calendars and common endpoints; classify reconstruction-only separately from prospective admissibility.
3. Specify and test the self-financing baseline evaluator with invented paths through the existing evaluation owner before opening market outcomes.
4. Register the admitted baseline/challenger study using actual source/protocol identities; preserve native Track A's separate gates.
5. Add economic information through predeclared increments; keep stock-expression and cross-market claims separate until their own source and evidence requirements are met.

This sequence advances the sector-allocation objective while retaining prior failures. It is not an instruction to wait for a historical owner name, and it is not permission to bypass an actual live writer, source denial or scientific read boundary.

## Primary external metadata sources

Sponsor XLC listing/inception: https://www.ssga.com/us/en/individual/etfs/state-street-communication-services-select-sector-spdr-etf-xlc

Sponsor XLRE listing/inception: https://www.ssga.com/us/en/individual/etfs/state-street-real-estate-select-sector-spdr-etf-xlre

Sponsor BIL identity and benchmark: https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil

Treasury bill price/discount convention: https://www.treasurydirect.gov/marketable-securities/understanding-pricing/

Only identity/method metadata from these public pages is used here; incidental public performance displays are not a new research dataset or evidence of a result. Any previously inspected market history remains development-only unless an existing owner independently establishes otherwise.
