# Implementation-ready CEO / Fable handoff

**Commission:** Mastermind Intraday Dealer Pressure, LOD/HOD, EOD and Closing-Pressure Intelligence.  
**Research status:** complete architecture/evidence handoff; no empirical market uplift or production qualification.  
**Source freeze:** Macro c9631f8b2469587dec643bec94b16e77c09ef511; Terminal ad36a332cd4b53af1d917a94f6fb3a10e27dad84; protected Mastermind a6d40ff648671b03bd4d829d84dd066b58ea8c3f.  
**Next work:** a separately authorized, research-only implementation under existing owners.

## 1. Decision requested from the later implementation commission

Implement the smallest experiment that can determine whether **better signed-inventory information and exact hedge-target changes improve fifteen-minute ES excursion forecasts beyond the incumbent-information adapter and simpler price/flow/liquidity models**.

Use a new SPX/SPXW-to-ES research cohort. Preserve accepted P5 v1's SPY/QQQ/IWM next-ten-minute variance, B1-RI/B2-RI and source-refusal contracts. This handoff does not amend them, modify Prophet, create a trade signal or authorize a data purchase. [I01] [I03] [I05]

Do not begin with a universal cross-asset “dealer pressure score,” a new terminal, a full capacity simulator or a neural extreme-price model. The information-value result should determine whether those later complexities are useful.

## 2. Implement these four comparisons first

| Arm | Inventory information | Other inputs and economics | Question |
|---|---|---|---|
| A. Existing assumptions | Prior settled OI under current explicit sign convention plus symmetric alternatives | Same eligible chain, prices, exact-time model, liquidity and outcomes | What can the cheap current baseline do? |
| B. Public-flow update | Eligible public trade/preceding-quote sign with package abstention and feasible capacity scenarios | Same endpoint repricing and source population | Does public information add anything? |
| C. Participant-informed update | Released C1 MM buy-minus-sell contract volumes with full starting-history qualifications | Actual receipt delay; same model and targets | Is better scoped position information valuable? |
| D. Research information diagnostic | More complete/corrected participant history, clearly nontradable if vintages are missing | Same test outcomes; separate evidence grade | Is there potential information masked by source latency/history? |

C and D are not omniscient dealer truth. If adequate evidence excludes a useful gain for the scoped higher-information arm, stop the corresponding endpoint claim. Broader reconstruction stops only when required fifteen-minute, remaining-extreme and close families rule out useful value, or an explicit cost decision leaves the remaining question unresolved. If a useful gain survives real availability, test whether a calibrated public filter recovers enough of it at lower cost.

## 3. Exact first study contract

**Population:** a new declared SPX/SPXW option-risk universe with compatible canonical references; ES is the initial executable price/liquidity coordinate. Begin with admitted PM-settled SPXW cohorts and retain any admitted AM-settled SPX background risk as a separate contract class. No arbitrary strike truncation may be labeled a whole book. Bound excluded risk or declare partial coverage.

**Cohorts:** 0DTE, 1–7 calendar days, and 8+ days at the anchor, with exact fixing, last-tradable and economic settlement states. Separate starting holdings, intraday trading increments and nontrade adjustments.

**Decision times:** proposed one-minute cash-session grid from scheduled open +15 minutes through close −15 minutes, restricted to actually admitted source states. Early closes use the same relative rule. Each forecast becomes eligible only after required source arrival and model completion; ten-minute participant updates retain their true age between releases. Grid choice is a proposed registration setting, not a claim of existing live cadence.

**Primary outcome:** downside and upside next-fifteen-minute excursions from the decision-time ES price, divided by a positive price scale fixed at that time. Mean pinball loss across 0.10/0.50/0.90 quantiles and both excursion sides is the single primary score. Use equal session weight in the final comparison.

**Primary contrast:** add the registered inventory/full-reprice block to the strongest simpler research adapter chosen using development data only. Keep the accepted B1-RI adapter identity distinct from a new target-specific adapter and from native production-policy replay.

**Secondary families:** remaining-session high/low quantiles and probabilities of a new extreme; frozen zone touch/hold/break/gap-through; the 16:00 ES mark; actual SPX index close/extrema when a qualified basis-aware target exists; and matched incumbent candidate adverse-excursion/false-entry outcomes. Share-auction studies have separate venue-specific targets.

**Data grade:** ACTUAL_AS_SEEN, HISTORICAL_RECEIVABILITY or FINAL_VINTAGE as in Commission 15, with synthetic checks separately labeled. A historical research diagnostic cannot silently become a live simulation.

**Sample plan:** 60–120 independent sessions can diagnose feasibility; aim for at least 250 for the initial formal study and extend for precision. A proposed 120/20/20 train/calibration/test template and final 60-session untouched holdout require enough actual chronology; otherwise reserve prospective data and state the limitation. All labels must mature before model freeze. Report 16 governs purging, model search, clustering and multiplicity.

**Proposed useful effect:** a 2% relative primary-loss reduction is a planning hurdle requiring owner confirmation before outcomes, not an observed or universally adequate economic threshold. Report absolute loss, interval width, calibration, latency, coverage, stress/close non-inferiority and total cost. An imprecise null is inconclusive.

### Mandatory first-study extrema and close return

Return three separate frozen verdicts: F1 fifteen-minute excursions (primary); F2 remaining-session upside/downside excursion quantiles; F3 the signed normalized ES close return. F2/F3 use origins at cash close minus 60, 30 and 15 minutes, equal origin/session weighting, identical information arms and target-matched simple/price-volatility baselines. F2 uses 0.10/0.50/0.90 pinball loss; F3 uses 0.10/0.25/0.50/0.75/0.90 pinball loss. Preregister each useful-effect hurdle and multiplicity policy. Report16 `4A is the exact contract. A close non-inferiority result alone does not answer whether inventory improves closing forecasts.

## 4. Exact owner paths and extension scope

| Work item | Existing path / carrier | Deliverable for this slice |
|---|---|---|
| Source and OI admission | collectors/thetadata.py; engine/thetadata_store.py | Qualified event/interval and OI-vintage projection with gap/correction receipts |
| Existing chain universe | scripts/chain_snapshot_poller.py; engine/options_structure_intraday.py | Reuse canonical contract IDs, existing parquet/OI files and bucket-receipt authority |
| Flow evidence | engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py | Preserve atomic source where retained; distinguish aggregations and quote/sign/capacity |
| Book/pressure mechanics | engine/intraday_greeks.py; engine/exposure_math.py; engine/options_scenario_surface.py | Additive research book-state and endpoint-difference contracts using reviewed reference kernels |
| Existing GEX baseline | engine/gex_engine.py; engine/options_hub.py | Freeze current actual-spot regime/profile implementation as comparator |
| ES source/liquidity | Data OS, Macro #8451; quote authority in Commission 15 | Source-qualified contract/roll and price/volume; depth optional after admission |
| Experiment bookkeeping | engine/trial_ledger.py; incumbent Evaluation OS | New cohort/claim and bounded variants, no new framework |
| Existing candidates/outcomes | engine/entry_radar/replay; PR0; existing qledger/ledger owner | Paired shadow feature joins with unchanged candidate identity and single-writer law |
| Publication/UI later | Existing hub/R2 publisher; terminal/lib/flowSource.ts; Exposure/Structure/Statistics hosts | One typed payload; source age, scenario assumptions and probability evidence visible |

Current collision/coordination carriers: Macro #7306 is merged source to reuse; #7327 expiry VEX/CEX and #7322 topology are adjacent; #8451/#7326 cover futures/data questions; #7990 owns darkpool quarantine. Terminal #640/#661/#768/#769 and #799 cover scenario, unknown cells, expiry and Statistics seams. Recheck only the bounded relevant carrier before editing. The report 02 census records exact inspected heads and limits. [IPR7306] [IPR7327] [IPR8451] [IPR7990] [IPR640] [IPR661] [IPR768] [IPR769] [IPR799]

Existing workstream context includes WS:ADVANCED-DATA-OPTIONS, WS:INTRADAY-FLOW-P0-RECOVERY, WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY and WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2. Register the extension with the appropriate incumbent ownership; these names are routing context, not authorization to create a new parallel workstream or alter their acceptance.

### Additional incumbent discovered in the final census

Coordinate with MAS-260 / Macro #7328 before any forecast/outcome module or payload edit. Its existing source/price audit and outcome/research CLI, local/unpushed price/volatility shadow generator, Terminal consumer and separate calibration lane must survive. Reuse the active price/volatility baseline; the recorded GEX predictive hypothesis remains closed for promotion. Report02's addendum distinguishes source evidence from unreplicated negative-test details. This package is supporting research to the observed `WS:MARKET-OS` / `MAS-260` pair, not a replacement operation or a claim of completing that product. [M01] [M02] [IPR7328]

## 5. Minimum economic payload

The slice should emit one versioned record with:

- Native book state, signed-inventory method, covered participants/expiries, starting-history and adjustment limits.
- Anchor, endpoint and source/consumer clocks; exact price/fixing/deliverable revisions.
- Target hedge change in native risk and ES-equivalent contracts; endpoint reference notional, never mislabeled cash or actual flow.
- 0DTE/1–7D/8+D components; exact spot/vol/time/inventory attribution and interaction accounting.
- Numerical coverage and missing-risk bounds; inventory, surface and execution-policy uncertainty separately.
- Expected-volume participation proxy first; executable-capacity estimate only with qualified evidence.
- Forecast target/label/model versions and calibration state, with unavailable outputs null.
- Observation/scenario/prediction evidence types and all-false trading/portfolio/Prophet/policy authority.

The 72-feature catalog is a candidate backlog, not the initial model dimension. Select the small predeclared block that identifies the information comparison. DPF-51 is a conditioned transformation of DPF-24, not independent discovery; aliases retain earlier OIF semantics.

## 6. Acceptance receipts the implementer must return

| Receipt | Required content |
|---|---|
| Source admission | Exact source/contract universe, rights, clocks, coverage, corrections, exclusions, and current owner |
| Study registration | Cohort, frozen features/comparators, labels, primary loss, sample dates, variants, power/futility and non-inferiority rules |
| Mechanical verification | Existing and extended conservation, sign/unit, multiplier, expiry, missing-book and reference-price cases |
| Timing verification | Before/after-release examples; rejected future quotes/OI; consumer completion; original and corrected replay differences |
| Empirical report | Every registered arm/baseline/ablation, paired session uncertainty, calibration, subgroup losses, coverage and cost |
| Negative-result record | Failed hypotheses, inspected variants and whether evidence is negative or inconclusive |
| Prospective shadow | Archived forecasts before outcomes, natural source/publisher/consumer receipts and matured labels |
| Integration verification | Existing source registry/component consumption; no duplicate store/evaluator or policy interference |

This research package already supplies a **62-assertion synthetic mechanics witness**, source and claim registers, full contracts and the proposed study template. It does not supply market data, entitlement receipts, calibrated coefficients or a passing empirical report.

## 7. Practical go/no-go outcomes

**If exact repricing helps but better inventory does not:** extend the honest scenario tool and retain the simple inventory assumptions with visible uncertainty.

**If participant data helps but public inference does not:** compare permitted data cost and latency against the measured gain; do not call the public model equivalent.

**If only liquidity or raw flow helps:** prefer that simpler qualified block through its current owner.

**If early/official auction information helps independently:** advance the adjacent venue-specific auction study, with dealer features earning their own incremental test.

**If nothing clears the useful-effect and calibration bar:** close the tested hypothesis family. Preserve the mechanical/research improvements and negative evidence; do not repackage the same failed claim as a new confidence score.

The implementation mission is therefore narrow enough to falsify the expensive idea and complete enough to build without rediscovering the domain.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I01]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[IPR640]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/640
[IPR661]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/661
[IPR7306]: https://github.com/mastermindx-market-intelligence/macro/pull/7306
[IPR7327]: https://github.com/mastermindx-market-intelligence/macro/pull/7327
[IPR7328]: https://github.com/mastermindx-market-intelligence/macro/pull/7328
[IPR768]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/768
[IPR769]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/769
[IPR799]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/799
[IPR7990]: https://github.com/mastermindx-market-intelligence/macro/pull/7990
[IPR8451]: https://github.com/mastermindx-market-intelligence/macro/pull/8451
[M01]: https://linear.app/mastermindx/issue/MAS-260/options-exposure-outlook-research-calibrated-forecasts-and-terminal
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/aafb9e25b0c12390ef99a9b9c4937fa1198b4bf0/agentos/workstreams/WS-MARKET-OS.md
