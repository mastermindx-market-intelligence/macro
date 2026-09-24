# Market topology measurement and integration - research design draft v1

Scope: research and planning for `market-topology-research-20260923-astra-001`, Macro draft PR #7812. This is NOT an accepted production contract, new authority, build commission or validated forecasting model. FABLE_HANDOFF_READY remains false. It translates the completed evidence into concrete interface decisions and identifies what must still be settled here before building.

## 1. User jobs and distinct machine jobs

The user must be able to answer: why has broad market direction been a poor guide to individual holdings; where is economically meaningful progress occurring; is participation widening or only changing identity; are apparent new leaders actually outperforming now; are weak names recovering or simply bouncing; what comparable historical contexts exist and how limited is their evidence?

Machine jobs remain separate:

- Measurement: compute reproducible population, trajectory, drawdown, attribution and concentration facts.
- Historical retrieval: identify dated comparable states with similarities, dissimilarities, missingness and outcome ranges, context-only.
- Forecasting: estimate specified future outcomes only after separate empirical/calibration acceptance. Neither completed industry test earns this authority.
- Decision workflow: expose evidence to the existing intelligence and research-priority consumers. No automatic trade origination, sizing or duplicated posture effect.

A current relative leader, a stock showing fresh outperformance, a historically persistent winner, and an attractive forward entry are not interchangeable outputs.

## 2. Universe design: three denominators, not one silently changing list

The frozen stock trial uses historical S&P 500 membership as an initial research sample. It does not define the final product universe or address all liquid U.S. stocks. Retain the wider ambition, including smaller companies and recent listings, without overstating that pilot's scope.

Use existing security/issuer and universe owners to distinguish:

1. Market census: a declared listing/security-type population, with unknown data represented explicitly. Security identity and share-class/issuer aggregation are policy fields. It must not silently exclude weak names because their prices fell.
2. Currently tradable opportunity set: contemporaneous price/liquidity/venue constraints, separately disclosed. Thresholds are versioned and not tuned to the displayed outcome. The stock trial's USD 5/USD 5m choices remain research choices, not automatically product defaults.
3. Fixed-cohort follow-through: eligibility frozen at a formation date, with subsequent exits, delistings, acquisitions and unresolved outcomes retained. This is the denominator for evaluating what happened to opportunities visible then.

Example of why this matters: if a 100-name cohort has 20 leaders and 20 losers, and all 20 losers disappear under a new price filter, the dynamic leader share rises from 20% to 25% without one new leader. Such eligibility effects must be attributed, not sold as improved breadth.

Issuer-level and security-level counts are both legitimate but cannot be mixed. GOOG/GOOGL-style multiple share classes should not silently count as two independent issuer bets. Industry-portfolio breadth, stock breadth, issuer breadth and cap-weight contribution must have distinct labels. A fixed top quintile is a relative ranking, never a measure that discovers how much of the market is healthy.

Recent IPOs and short-history names require a separate coverage tier. Missing 253 bars does not mean a stock is sideways, weak or uninteresting. The long-history trial cannot settle their behaviour.

## 3. Required input view from existing owners

A research extraction is an immutable view of canonical owner outputs, not a replacement database. Resolve dataset IDs through the current registry and use the existing vendor alias reader.

Per security-session, require or explicitly mark unavailable:

- stable security_id and issuer_id; date-scoped vendor_symbol, venue, security_type and listing/exit status;
- exchange session, effective_at, available_at/known_at when actually known, source revision and correction/adjustment vintage;
- raw OHLC/volume for tradability and execution; split-adjusted structure prices where that question requires them; economically coherent total-return increments for wealth/performance;
- historical industry and capitalization, with the shares/price basis documented, not today's controls backfilled;
- membership intervals and event-effective convention; a separate information-vintage qualification;
- corporate-action and terminal-event references, outcome status and observation/censoring reason;
- per-field quality/null reason, coverage and rights/redistribution class.

The committed reference receipt at Macro cde1e7e5e0cd7134f88a7f78dbeec614976c5090 reports a September 21 identity build, 708/718 of its target resolved. It is positive evidence that an existing identity output exists, not proof that this historical extraction is complete. The raw/local stock panel remains inadmissible to the controlled trial.

Acceptance fixtures must include the existing NVDA/TSLA/AMZN/GOOGL split cases; FB/META/METV and later FB reuse; share classes; membership exit; SIVB/FRC/ATVI terminal economics; an IPO/short-history name; stale input; and an explicitly unknown observation. Do not repair genuine crashes by interpreting every extreme move as a split.

## 4. Measurement payload, not a universal quality score

Each payload must bind operation-independent content identity, schema/feature version, universe policy, entity level, weighting, benchmark, as-of session, available-through time, source/vintage refs, history window and coverage. Runtime operation/job state remains with Executive OS and is not part of a new market-data control plane.

Retain a compact vector with these families:

A. Progress: absolute economic return and benchmark-relative return for declared horizons; median and distribution quantiles; raw positive fraction. Any materiality/no-progress threshold is explicit, with sensitivity evidence. The initial 0.25 volatility-unit threshold is an experimental feature, not accepted truth.

B. Path: trailing maximum/root-mean-square drawdown, time since last high, time underwater, and recovery distance. Signed efficiency is descriptive only: the first industry pilot found it almost rank-equivalent to volatility-normalized momentum. Do not add it as an independent alpha leg by renaming it.

C. Sequence: the full oldest-to-newest sign/magnitude sequence, including +++, -++, ++-, mixed and exact-zero/unknown cases. Three positive blocks mean three positive blocks, not an uninterrupted daily advance or a forecast. Preserve short/intermediate/long views concurrently. The empirical 1992 example forbids treating low +++ share as automatic bad breadth.

D. Identity persistence: rank or cohort retention with defined universe intersection and tie policy. Tag mechanical overlap in trailing measurements. Historical top-quintile survival is descriptive unless future-only outcomes beat appropriate nulls.

E. Fresh versus expired history: for horizon h and lag k<=h,

  delta_momentum_h = new_k_returns - expired_k_returns.

Publish both terms, their benchmark-relative versions and the observed change. An improvement driven by discarded bad history is not fresh outperformance or capital inflow. The measured 25.93% relative example is a descriptive attribution, not a trading edge.

F. Dispersion and concentration: cross-sectional return spread, correlation, sector/industry decomposition, and explicitly weighted contributions where real weights exist. Keep positive and negative contribution concentration separate. Never divide by near-zero net aggregate return to create unstable contribution percentages; never label equal-industry positive-log-return HHI as index-contribution HHI. Price changes alone do not establish institutional accumulation or net capital transfers.

G. Population change: state migrations on common identities, plus listing/membership changes, tradability changes and known/unknown coverage transitions. Entries/exits must not disappear into a renormalized percentage.

Current descriptive labels should be small and literal. A more ambitious 'true leader with runway' classification is still a research target, not a label justified by these experiments.

## 5. Population accounting identity and invariants

For any explicitly defined binary state S and two observations, let C be common eligible identities, E identities entering the universe and X identities exiting it. Then:

  count_S(new)-count_S(old)
    = [C entering S - C leaving S] + count_S(E,new)-count_S(X,old).

Keep transitions involving unknown classification separate from economically measured transitions. Publish the residual and require zero within exact integer arithmetic. For weighted populations also attribute weight changes; count conservation does not prove weighted-share conservation.

Use a full transition table only for genuinely mutually exclusive states. Overlapping flags such as 'relative leader' and 'in an absolute drawdown' must not be summed into a fake 100% population. Unknown is a real reported category, not the complement of leaders and losers.

## 6. Historical analogue interface and forecast firewall

Reuse Macro engine/neuralweb/brain_analogues.py (brain.analogues.v1) for the context-only retrieval seam, subject to owner review. Its existing contract deliberately excludes forecasts/probabilities. Preserve that boundary.

A topology-enriched historical context response should add, not replace, the owning contract's provenance and lag behaviour:

- query universe, horizon, exact as-of and available information;
- feature/vintage/representation version and actually compared feature set;
- comparable history coverage, eligible-candidate count and selected episode dates;
- neighbour distances plus material similarities AND dissimilarities;
- episode-separation rule and concentration in particular eras;
- raw historical outcome distributions with explicit 'descriptive, not calibrated' status;
- no-match/insufficient-support reason when an accepted rule requires abstention.

The first analogue test forced K=20 and failed to beat the historical mean. It cannot be shipped as a probability engine. Its broad empirical 10th-90th ranges did not deliver nominal 80% coverage. A future forecast lane must separately earn base-rate improvement, calibration, stable subgroup support and timing correctness; it must consider shrinkage and no-match without tuning on this already viewed test set.

Store rich lawful observations where current owners support them, but use task-specific representations. Collecting more variables is not a licence to search unconstrained combinations, claim independent sample size from overlapping windows, or prefer a neural encoder before simpler baselines. Macro context must respect release vintages rather than paste today's revised growth/inflation history onto past decisions.

## 7. Existing integration seams and explicit non-goals

Source evidence:

- Macro config/dataset_registry.yml and lib/dataos/{identity,price,temporal,registry}.py own identity/basis/time vocabulary and dataset declarations.
- Macro data/reference/_receipt.json is the existing build-evidence surface, not a separate research claim store.
- Macro engine/neuralweb/brain_analogues.py already owns the US brain historical retrieval helper. Its normalisation rules are context bookkeeping, not a historical forecast protocol.
- Mastermind brain/regime_frame.py at 4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2 defines the single regime reader and rotation-evidence budget seam. The earlier research/eyes/rotation_spec.md overlaps the proposed measurement families. Verify the specific producer/reader functions at build time; do not assume every proposed tensor block is live.
- Existing intelligence/product surfaces consume read-only measurements through the accepted reader. No new code may independently read raw files just because a new panel needs them.

Non-goals: no replacement security master, new historical-memory service, duplicate forecast registry, independent scheduler, lifecycle/watcher plane, new credentials, new trade-sizing path, composite regime score promoted from these results, automatic raw-data repairs, or deployment during research.

## 8. User-visible workflow and acceptance

Workflow A, 'Why is this market difficult?': show the named universe and data date; separate durable progress, recovery-shaped paths, recent setbacks and low-net-progress dispersion; expose concentration and unknown coverage. The explanation must cite measured fields rather than narrate a preselected market story.

Workflow B, 'Where is new leadership emerging?': show recent relative progress, its fresh-versus-expired-history attribution, industry/peer context, prior state, liquidity and data support. Historical persistent winners and new traction should be separate views, not one list that systematically suppresses new entrants. Do not equate a research priority with a buy recommendation.

Workflow C, 'Is this loser bottoming?': show a presently observable recovery attempt, new-low/failure risk observations, event context and unresolved terminal/coverage issues. Never use a future-confirmed trough as a live input or advertise an uncalibrated success probability.

Workflow D, 'What happened in similar environments?': provide dated comparables and dissimilarities, historical outcome spread and support limitations. Failed forecast experiments must remain visible to the intelligence layer; narrative confidence must not override them.

Acceptance tests include: exact source/date replay; causal future perturbation within numerical tolerances; split/rename/terminal fixtures; population-accounting conservation; eligibility-drop illusion; unknown versus zero; full sign-sequence reporting; roll-off identity; null overlap controls; no-match and stale-source rendering; benchmark/basis mismatch refusal; contract-consumer integration; and browser proof of one real input-to-visible-result path. Unit-test green is not product acceptance.

## 9. Candidate build slices - not yet commissioned

Slice 1: qualified existing-owner extraction -> literal measurement vector -> population/accounting view -> user explanation with source/coverage and negative states. Capability: explain the actual structure without pretending to forecast.

Slice 2: existing historical-retrieval owner -> population-aware comparison and dissimilarity/support output -> context-only user workflow. Capability: inspect relevant history without confusing resemblance with probability.

Slice 3: only after independent acceptance of the frozen stock trial and subsequent required validation, add calibrated leader/loser/recovery forecasts through the existing forecasting owner. Capability and acceptance must name the forecast horizon and outcome, not 'AI score'.

Fable would orchestrate implementations and subagent integration of frozen slices, not rediscover the hypotheses. Research remains here until inputs, retained methods, no-match/calibration decisions, precise integration and required proof are settled. The full study is not complete just because Slice 1 can be described now.

## 10. Remaining research decisions

1. Obtain and verify the actual formation-time stock extraction under existing identity/price/fundamental/terminal owners; do not retry the blocked R2 request without a material allowed change.
2. Execute the already frozen stock trial on admitted inputs; preserve the negative industry results and report all primary/secondary outcomes.
3. Test an explicitly declared macro-context/analogue shrinkage/no-match design with vintage-correct information and a fresh evaluation plan; the viewed 2000-2025 analogue sample is not untouched holdout.
4. Resolve market census versus tradability versus fixed-cohort policies, recent-listing coverage, materiality thresholds and cross-horizon onset/delay tradeoffs using data.
5. Turn the final retained definitions into the exact production reader/API/UI contracts and obtain design acceptance before a build-only Fable commission.
