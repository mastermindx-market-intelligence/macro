# Market Tide → Prophet Timing State Engine: independent audit and re-census

Date: 2026-10-03. Scope: review the Chairman's supplied report, verify material claims against current sources, and harden the implementation program. No second Deep Research run. No new market experiment or production change is claimed.

Read [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md) for exact revisions, durable links, input hashes and observation limits. References such as G03 and W04 below refer to that ledger. Read [IMPLEMENTATION_MASTERPLAN.md](IMPLEMENTATION_MASTERPLAN.md) and [CONTRACTS_AND_EVALUATION.md](CONTRACTS_AND_EVALUATION.md) for the proposed corrected execution contract.

## 1. Verdict

**REQUEST_CHANGES as an end-to-end execution specification; retain the conditionality thesis as a research hypothesis.** The report is materially useful as a conceptual synthesis. It is not adequate, unchanged, as authority to freeze a new canonical state engine, declare the estate completely censused, infer that every empirical lane is blocked, or promote a model.

Accept its strongest principles: action-specific outcomes; separation of risk from opportunity; provenance and point-in-time discipline; preservation of negative evidence; a simple permanent baseline; one canonical source/consumer path; and no automatic rank, gate, sizing or trading effect. These are supported by the commission and current source boundaries. Do not accept the untested superiority of a particular hybrid ontology, hard-code its six states, or treat the resulting architecture as empirically established.

An existing draft architecture carrier, **Macro #8325**, already addresses several weaknesses: the October 2 Options revival, newer retrospective findings, strategy conditioning, named states as hypotheses and separately blocked feature families. It was found during this audit and read at `604273045df4a277f0895093d8bebcd96a4e795f` [G23–G24]. Credit those corrections; do not duplicate its parent or overwrite its author. This package is a review/amendment delivery for that carrier. It adds the source-backed corrections, explicit contracts, dependency graph, statistical gates, test obligations and operational handoff that its 190-line outline still lacks.

**What is not established:** incremental timing value over existing price/volatility and incumbent context; useful early transition lead; action-policy value after costs; probability calibration; an optimal state taxonomy; or production readiness. A negative or inconclusive scientific result must remain an allowed outcome of the completed research program.

## 2. Method and evidence boundaries

The input files were read in full. Current GitHub PR/source state, three relevant Linear issues, selected actual code, the no-rebuild amendments, Options results and a bounded set of public primary sources were inspected. The audit distinguishes direct source inspection from recorded test/results receipts and from live runtime observations.

The Executive read was unavailable [R01]. Source inspection did not exercise deployed pages, current worker occupancy, the entire dataset estate or the 89-test suite. No current production claim is manufactured from a planning document. Existing refusals were not retried, rephrased or delegated around. This audit's deterministic local work was input hashing and document-structure inspection, not a market backtest.

The report's 104 file-citation tokens and 28 web-citation tokens contain no literal HTTP(S) source URLs in the exported Markdown [I02]. They are useful in the originating conversation but inadequate as the standalone evidence bibliography Astra needs. The accompanying ledger replaces load-bearing references with permanent repository paths and explicit source limitations.

## 3. Material findings and required corrections

### F01 — The source census omitted a current authorization change and an actual new study

**Severity: critical for scope and research ordering.** The October 2 Chairman decision permits specified Options research-only replications, successors and registered positioning interactions [G07–G09]. The supplied report's blanket retirement statements are therefore outdated as research permissions, even where its empirical caution remains appropriate.

The same estate contains an actual 60-cell Theta EOD study with three family-adjusted rejections and no cross-era survivor [G10–G11]. This must enter the hypothesis ledger. Do not rerun it as supposed new work. The allowed conclusion is narrower than either “options work” or “options are dead”: this particular retrospective study supplies weak, era-specific evidence, with PIT still unproven and production authority closed.

**Correction:** preserve old results and exact constructions, consume the October 2 study, apply the current scope-specific amendment, and keep timing/global-regime authority separate. #8325 already incorporates much of this correction; integrate rather than rediscover it.

### F02 — C1 source blockers were incorrectly generalized to the whole program

**Severity: critical for execution.** The supplied report's final frontier and dependency chart put both event and price qualification before B0. Price-only B0 does not require CPI/NFP/FOMC history. C1 does: its current runner validates an event-qualified common cohort even for P [G03].

MAS-94 is a narrow prospective source vertical, not the universal price-history authority. Older actual inventory documents identify additional deep prices, delisted prices, PIT membership and Massive daily history [G21]. Those documents do not qualify the current stores, but their existence prevents the inference that MAS-94's Todo status proves all historical work impossible.

**Correction:** separate B0-price, C1-event and each incremental-family admission. Compare each challenger with B0 on its exact eligible dates, while also reporting B0 on its broader eligible population. Report coverage/selection differences. Do not force all families onto the intersection of the weakest history, and do not silently change C1's frozen cohort. #8325 partly fixes the dependency; the contracts here make it executable.

### F03 — The proposed engine risks duplicating existing state and flow capabilities

**Severity: critical for architecture.** “Market Tide” already denotes an implemented display-tier options-flow builder in Macro [G14], in addition to the external Unusual Whales product [W12]. The new timing capability must not overwrite its JSON keys, accumulators or display meaning.

The shorthand `risk_radar → market_state → regime_vector` is governance context, not a sufficiently precise call graph. The actual `engine/market_state.py` describes its synthesis as display-only; `regime_vector.py` is a thin consumer with existing state storage [G18–G19]. A new “orthogonal” regime probability service could still be a duplicate classifier even without a numeric score.

**Correction:** name the proposed artifact distinctly; census exact source field → transformation → authority-bearing consumer edges. Reuse incumbent observations and optional state IDs. Treat additional learned state representations as research challengers inside a permitted arena, not a new canonical market-state authority. Risk Radar/Grey Deer keeps hazard ownership; PTSE evaluates conditional action evidence.

### F04 — The report overstates its ontology

**Severity: major.** Four layers become three; “superior” representation is asserted without comparisons; dimensions are called orthogonal without a redundancy test; and a six-node topology appears before state-identification experiments [I02 §§Product ontology/model arena]. Ambiguity combines an actual range state with insufficient evidence.

**Correction:** first freeze envelope semantics, provenance, target/horizon IDs and authority boundaries—not a winning taxonomy. Distinguish `observed`, `estimated`, `unknown`, `not_applicable`, `stale` and `conflicted`. A market can be range-bound with excellent data or strongly trending with poor data. Those are different axes. State probability vectors and transition hazards remain absent until a fitted, validated object exists.

### F05 — Forecast targets and decision estimands are not interchangeable

**Severity: critical for scientific validity.** C1 predicts a normalized closing-path downside magnitude [G03]. It neither estimates a crash probability nor evaluates a next-open executable policy. A good index forecast does not establish whether a specific stock should be entered, held, added or sold.

**Correction:** retain C1's exact target and scoring. Register separately a market forecast, a candidate/action outcome and a policy comparison. Action eligibility must exist at decision time: ADD requires an existing holding, REENTRY a prior attributable de-risk episode, CONTINUATION an open eligible position. “Already-working position” cannot be defined using future success. Use next eligible executable prices for policy experiments; never mark a post-close decision as filled at that close.

### F06 — Shadow comparisons are not automatically causal experiments

**Severity: critical before authority.** Identical cohort timestamps are necessary, not sufficient. Selection, evolving Prophet versions, missing candidate opportunities, dependence across names, capital limits and path-dependent exit/re-entry all affect the comparison.

**Correction:** preserve the incumbent candidate census before any timing treatment, rejected/abstained opportunities, policy version and action-specific eligibility. Report paired shadow results as simulated policy value under stated fill/cost assumptions—not causal live uplift. A randomized or other causally identified intervention needs a separate explicit authorization and design. Never infer portfolio returns by summing many overlapping hypothetical positions without capital constraints.

### F07 — The empirical ladder is order-dependent and can miss genuine interactions

**Severity: major.** A one-way B0→B1→… sequence can confound feature value with which family entered first. The report and #8325's “only survivors” phrasing would also eliminate interactions that have no marginal main effect.

**Correction:** run a finite set of B0+family comparisons, admitted-core ablations and mechanism-registered interactions. A marginally null feature may enter a named, preregistered interaction with its null retained and trial charged. No unrestricted combinatorial search. Compare on matched rows and disclose each family's incremental coverage and latency cost.

### F08 — Transition validation is underspecified and vulnerable to look-ahead

**Severity: critical for a state engine.** Full-sample HMM smoothing, hindsight state labels, train/test-shared scaling, retrospectively selected state names and targets defined by the same fitted state model can create impressive but circular results.

**Correction:** use filtered states based only on data available at the decision; fit transformations/state mappings inside training folds. Evaluate against independently frozen observable events or outcomes. Define detection time, onset, warning episodes, hysteresis, censoring, competing recovery/break outcomes and negative lead times. A detector that fires after the break may have descriptive value but has not demonstrated advance warning.

### F09 — Statistical gates are slogans rather than an executable acceptance policy

**Severity: major.** “Calibration,” “era robust,” “policy positive” and “beats B0” lack protected outcome partitions, trial counts, effective-sample support, meaningful effect thresholds and clear rejection/abstention semantics. One-day Gantt placeholders add no information about these gates.

**Correction:** use the finite protocol in CONTRACTS_AND_EVALUATION. Freeze primary loss, effect-size floor, paired uncertainty, calibration fit/evaluation separation, trial family and a one-use final holdout before outcomes. Use power calculations based on independent sessions/episodes, not millions of rows. Already-inspected data remains exploratory. Unknown power, unknown PIT or missing action labels yields `NON_EVALUABLE` or `INCONCLUSIVE`, never a statistical pass.

### F10 — Software completion, scientific qualification and authority are conflated in the sequence

**Severity: critical for shipping useful work.** The report waits until late model waves to create shadow history and product value, while treating a strong model as nearly synonymous with end-to-end completion.

**Correction:** accrue provenance-rich observations and candidate-context joins as soon as lawful owner integration exists, before a model wins. Ship a useful read-only explanation/missingness vertical separately from probabilities. Statistical failure should stop the affected forecast/policy, not erase useful observed context or freeze the entire program. Completion has separate software, observation, research, forecast and authority axes.

### F11 — “Authority=false” is necessary but not enforcement

**Severity: critical for integration.** A consumer may still sort, suppress, recolor as a recommendation, or send alerts from a context-only output. New `permission` fields themselves invite accidental gating.

**Correction:** use typed `action_assessment` records with explicit applicability and evidence status. Enforce no-mutation contracts at each consumer and test identical baseline rankings, admissions, plans and portfolio exposure with timing on/off, absent, stale and adversarial. The absence of an optional timing observation must preserve existing Prophet decisions; it must not globally block new entries. Only an explicitly promoted, scoped decision contract may acquire a fail-closed policy effect.

### F12 — Preserve scientific identity, not every bug or retrospective API shape

**Severity: major.** The report repeatedly says preserve the bridge “unchanged.” Its current use requires ex-post outcomes and cannot issue unlabelled natural-session observations [G04]. It also trusts supplied calendar/availability/rights claims that must be authenticated externally.

**Correction:** freeze C1 as the historical control. When a defect is reproduced, retain its old artifact and introduce a reviewed version, with old/new cohort and result attribution. Split future observation issuance from outcome attachment using existing owners. Verify the round trip of explicit negative-event evidence and a source calendar's completeness; do not call those untested checks proven code defects.

### F13 — The literature is directionally relevant but does not validate this product

**Severity: major.** Momentum-crash papers concern strategy-specific, often long-short behavior; their short-leg rebound economics do not establish a long-only Prophet entry or de-risk rule [W01–W02]. VIX decomposition does not grant a usable decision-time variance-premium feature [W03]. The New York Fed press-conference split is historically bounded by the 2019 institutional change [W04].

Cboe's aggregate net-gamma argument is not a proof of negligible intraday impact in every stress state, and May 2025 statistics must not be labeled October 2026 market facts [W05–W06]. Changepoint methodology is a model candidate, not evidence of trading value [W07].

**Correction:** each external hypothesis must list mechanism, association versus causality, population, horizon, dates, reproducible inputs, counterevidence and transfer risk. Retain these sources as priors. No external result bypasses a local incremental test.

### F14 — Competitor differentiation is a thesis, not a verified absence claim

**Severity: moderate.** First-party checks support the broad product categories in the report [W08–W12]. They do not establish that competitors lack prospective evaluation, or that Mastermind can already reproduce their entitled inputs.

**Correction:** keep the promising workflow hypothesis—candidate-linked, explainable action context and learning—but test it with existing user journeys. Reuse drill-down, historical replay and clear uncertainty patterns without copying proprietary formulas. No purchase, entitlement acquisition or trademark ruling follows from this audit.

### F15 — Scope expansion needs staged action/horizon/market admission

**Severity: major.** Six actions × several horizons × state families × models × instruments can become a huge, weakly powered search. An index-only H5 result cannot support intraday options or a global all-market regime.

**Correction:** begin with a US daily H5 market benchmark and observational NEW_ENTRY context for one currently registered eligible Prophet sleeve. Preserve full product support for all six actions in the contract, with independent evidence gates. Expand to continuation/pullback/add and a complete paired de-risk/re-entry policy, then other horizons/markets only under separate registrations. Strategy holding horizon and forecast horizon remain different fields.

## 4. Updated capability census

Status below is intentionally source-bounded. `BUILT_NOT_PROVEN` means source/record evidence exists but this audit did not establish its current end-to-end production path. `UNVERIFIED` is not equivalent to `NOT_BUILT`.

| Capability | Evidence observed | Disposition / exact remaining proof |
|---|---|---|
| Market Tide research parent | #7925 open [G02] | Keep parent; do not create another mission |
| Existing architecture draft | #8325 open/draft, one masterplan [G23–G24] | Incorporate this amendment under its owner; no overwrite here |
| C1 core and source bridge | Code inspected at e1a6524 [G03–G04] | Salvage frozen control; source/review/release acceptance remains |
| C1 tests | 89 recorded at earlier tested code head [G01] | Historical software evidence; not independently rerun |
| C1 exact-head delivery | Failed visible ci-gate, no formal reviews returned [G05–G06] | HOLD; distinguish CI-owner work from model validity |
| C1 empirical timing edge | PR explicitly records none [G01] | NOT_ESTABLISHED, not a negative market result |
| Existing flow Market Tide | Macro display-tier builder and source paths [G14] | Keep name/key semantics; separate PTSE identifier |
| Options historical revival | Current decision and charter [G08–G09] | Integrate existing arena; research-only amendment |
| New Theta study | 60-cell receipt and independent arithmetic record [G10–G11] | Consume as PIT-unproven retrospective prior; do not rerun gratuitously |
| Older OPEX/vanna/charm | Controlled descriptive robustness [G12] | Preserve exact target/root/era limits; reconcile with new study, do not collapse |
| Options stamp columns | Current stamping source [G13] | Reuse; current population coverage and first-known clocks not proven |
| Options NBBO/campaign/FS | Source-backed WS describes distinct acceptance gates [G22] | Reuse owners; preserve natural proofs and unresolved publication boundaries |
| MAS-260 | Current projection of price/vol shadow and GEX transfer failure [L03] | No takeover of intraday forecast namespace or local unpublished source |
| Prophet strategy model | Current multi-sleeve architecture decision [G17] | Reuse identity/episode/Availability/plans; exact current served chain still to verify |
| Entry policy | Session/risk/liquidity/gap facts in current source [G15] | Do not duplicate or turn into a universal gate |
| Entry Timing ownership | Current WS owns prophet paths, W2 pending [G16] | Joint owner review before source edits |
| Conditional Fusion | Narrow exception in current DNR and referenced masterplan [G07] | Re-read current exact promotion contract before any authority-bearing experiment; no new global exception |
| Market State / vector | Current source confirms existing consumers and degraded semantics [G18–G19] | Trace field-level graph; do not rely on name-level shorthand |
| Grey Deer / Risk Envelope | Referenced incumbents, full current path not audited | Explicit W0 owner/field inventory; not reassigned |
| Release/Event Truth | Current MAS-204 projection and existing source-owner references [L01] | Owner-qualified calendar/known-negative/revision receipts for C1/B2; not a B0 global blocker |
| Market Memory | Current MAS-94 narrow vertical [L02] | Source-clock/persistence design reusable; not proof of historical price admission |
| Historical breadth/prices | Dated inventory with concrete deep/delisted/PIT paths [G21] | Fresh metadata/rights/vintage census before qualification |
| Theme/leadership | Existing ownership documented in Prophet architecture [G17] | Consume current IDs; fresh component/history coverage owed |
| Liquidity/cross-asset | Relevant prior constructs and existing families; no full current panel audit | Source-specific admission; exact killed reversal is not revived by generic timing language |
| Terminal structure | Current arithmetic/units/sign/windowing code [G20] | Reuse typed outputs; no duplicate Greeks/transport |
| PTSE canonical observation artifact | Proposed here; not implemented in this review | W2/W3 vertical |
| PTSE calibrated forecasts | Not demonstrated | Independent model, source, calibration and prospective gates |
| PTSE policy authority | Not granted | Separate bounded adjudication; portfolio/trade authority remains elsewhere |

The census is materially deeper than the report's blanket status but is not a full live data/runtime audit. Every unverified component above has an explicit execution work package. Source limitations must stay visible until actual owner receipts replace them.

## 5. C1 salvage: what exactly survives

Preserve the C1-M1 question and N/P/PE/PEI specification as a benchmark, including its normalized H5 downside target, price basis, exact decision/event window, monthly fitting, training-history guard, maturity, purge and bootstrap design [G03]. The numerical screen compares PEI with P and PE, with the original relative-improvement and event-support criteria; it does not grant promotion. Do not relabel the screen as probability calibration or portfolio alpha.

Preserve source/proof provenance and the distinction between e1a6524 source/records and 2687deb native-tested code. Preserve all prior failures and refusals. No new result was generated by this review, and the draft PR remains unarmed.

Generalize only after acceptance: time/identity validation and reusable pure measurement primitives can be imported by the new research runner. Keep a compatibility fixture proving old C1 outputs and exclusions are unchanged. An event-free runner must have its own experiment ID and report its different eligibility rather than masquerade as the old P arm.

Split future observation issuance from outcome attachment. The live path must not require a future label. Record unavailable history, unavailable probability and unavailable action outcome independently. A successful structural validator proves conformance to supplied fields; it does not prove the inputs were historically available.

## 6. Reconciliation of old and new Options evidence

The July OPEX study mainly offered volatility/path associations and then corrected major confounding and a missing ETF slice [G12]. The October 2 study registered specific direction/excess-return and volatility contrasts over three eras and two horizons [G10]. Their targets, normalization, samples and tests differ. Treating the new vanna-relief nonrejection on SPY-excess returns as a refutation of the older volatility association would repeat the report's transfer error in reverse.

The correct study ledger records, for every construction: formula/version, root universe, target, horizon, era, current-vol/size controls, sign convention, missingness, trial family, point estimate/uncertainty and source eligibility. A proposed vanna interaction must compare signed and unsigned magnitude forms and retain the opposite-sign placebo, because the older ETF result weakens a directional hedge-flow explanation. Front-expiry concentration must be conditioned on root class and era rather than transported as a universal market signal.

MAS-260's specific failed transferable GEX promotion remains failed. The October 2 research reopening permits specified scientific work; it does not retroactively turn failed studies positive or authorize a global GEX forecast. No result in this package demonstrates market timing alpha.

## 7. Original A–N deliverables: quality assessment

| Commission deliverable | Supplied report assessment | Amendment supplied here |
|---|---|---|
| A executive finding | Useful hypothesis; product certainty too strong | Conditional adoption, explicit scientific alternatives and terminal null outcome |
| B current census | Material omissions and insufficient runtime/data separation | Pinned source ledger, newer decisions/results, internal collisions, scoped unknowns |
| C evidence synthesis | Relevant sources; transfer/causality limits incomplete | Source/target matching, newer counterevidence, public-claim qualification |
| D ontology | Plausible but premature | Envelope-first contract; no fixed state topology or orthogonality claim |
| E feature contract | Good field names; no complete current inventory | Owner/path/request matrix, availability grades, missingness and latency admission |
| F empirical findings | Truthfully no new C1 study; ignores newer adjacent results | Explicit actual-result inventory, no fabricated experiment, no nonrejection-as-zero |
| G model arena | Broad menu without finite trial protocol | Bounded first race, paired cohorts, protected tests, negative controls, numeric defaults for ratification |
| H Prophet integration | Correct conceptual separation; insufficient exact consumer enforcement | Episode/strategy/action keys, no-mutation tests, served-path proof obligation |
| I cross-system architecture | Owner names, incomplete field graph | W0 field-level mapping and reuse boundary for each incumbent |
| J experience | Reasonable ideas; page deferred ambiguously | Useful observation-first vertical, clear states and progressive disclosure |
| K promotion | Named stages without executable gates | Separate source/software/statistical/calibration/policy/authority conditions |
| L implementation plan | Wave labels, insufficient dependencies/tests/rollback/ownership | Twelve bounded work packages and universal proof contract |
| M salvage | Right objective, “unchanged” too categorical | Freeze experiment identity; versioned repairs and observation/outcome split |
| N next frontier | Partly blocked by false common-panel dependency | Reconcile #8325, qualify independent lanes, capture prospective receipts immediately |

## 8. Closing finding

The report is worth retaining, not accepting wholesale. The strongest new conclusion is architectural restraint: build an **action-conditioned evidence adapter over existing market and candidate owners**, and let empirical comparisons determine whether additional state or transition models deserve to exist. Useful context can be shipped without pretending to know calibrated action probabilities. Genuine forecast and policy improvements must be earned on the right populations, clocks, costs and protected evidence.

This audit delivery can be complete while the PTSE product remains incomplete. The next package turns that distinction into an executable program instead of using “more research” as a stopping point.
