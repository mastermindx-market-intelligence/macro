# Mastermind integration map

**Status: research architecture, source-pinned 2026-10-06.** Exact existing owners are established by the current census. Proposed additions below are contracts for a later implementation commission; none is a claim of deployed capability.

## 1. The integrated product

The future capability should publish one evidence-bearing state that existing Mastermind consumers can use consistently:

1. **Conditional dealer-book state:** observed coverage, inferred/scenario inventory and native risk.
2. **Conditional hedge-demand field:** endpoint target changes and attribution under stated spot, surface, time, inventory and hedge-allocation assumptions.
3. **Liquidity and behavior state:** materiality, candidate absorption/acceleration/transition zones and explicit invalidation.
4. **Calibrated forecast state:** prospective touch/hold/break, remaining extrema and close-region distributions, only after empirical qualification.
5. **Adjacent auction state:** venue-specific pre-publication forecast and official-feed nowcast.

A shared output prevents the terminal, research notebooks and downstream consumers from silently using different inventory signs, Greek clocks or probability definitions. The first version remains research-only with trading, portfolio, Prophet, ranking and automated entry authority false.

## 2. Exact reuse map

| Function | Existing owner / artifact | Later additive work | Boundary |
|---|---|---|---|
| Options source access | collectors/thetadata.py | Qualified atomic projection, corrections and source completion receipts where authorized | Adapter capability is not entitlement or retained tape |
| Canonical history / OI | engine/thetadata_store.py; existing EOD/OI/Greek parquet tiers | Series inception, OI vintage and corporate-action reconciliation through this store | No new archive or OI calendar |
| Intraday chain eligibility | scripts/chain_snapshot_poller.py; engine/options_structure_intraday.py; scripts/build_options_structure_intraday.py | Reuse chain IDs and bucket receipts; request additional fields through the owner | Existing U-CHAIN universe and receipt authority survive |
| Flow signing and context | engine/flow_signing.py; engine/live_flow.py; scripts/live_flow_poller.py | Separate quote-location/sign probability from participant/position-effect posterior | Aggregated notable feed is not atomic tape |
| Greek pricing / exposure units | engine/intraday_greeks.py; engine/greeks.py; engine/exposure_math.py | Exact endpoint delta, model convention and per-cell coverage | American/futures exceptions cannot inherit a generic BS convention |
| Current GEX / profile | engine/gex_engine.py; engine/options_hub.py | Retain incumbent baseline, topology and exposure IDs | Existing actual-spot flip fix must not be redone |
| Conditional surface | engine/options_scenario_surface.py; scripts/build_options_scenario_surface.py; merged Macro #7306 | Typed book-state/endpoint-difference extension, uncertainty and attribution | Current v1 is a fixed-OI Greek field |
| Futures tape / liquidity | Existing Data OS, Macro #8451; Massive entitlement lead #7326 | Qualified ES contract, roll, event/depth history, latency and rights | Source admission precedes measurement claims |
| Underlying quote evidence | Existing Terminal Quote Plane; Macro projection identified by Commission 15 | Eligible historical quote-event/depth projection | No second socket, collector, service or latest-only history |
| Off-exchange context | engine/darkpool_signals.py; engine/darkpool_context.py; scripts/build_darkpool_desk.py | Optional qualified intraday execution-memory features | #7990 owns impossible-participation quarantine |
| Multiplicity / trials | engine/trial_ledger.py; incumbent Evaluation OS | New registered claim family and declared inspection budget | No second evaluation framework |
| Candidate / outcome replay | engine/entry_radar/replay; PR0 contract; existing qledger/ledger owner | Paired shadow features on frozen candidates and matured outcomes | Preserve single-writer, candidate identity and existing horizons |
| Options Alpha | Existing options_alpha candidate, exact-option outcome and recovery owner | Reuse only qualified generic primitives if needed | Not a new dealer-pressure publisher or borrowed MomoEdge cohort |
| Distribution | Existing hub API / R2 publication and terminal/lib/flowSource.ts | Add an explicitly typed source key after schema approval | New object path is an owner decision, not invented here |
| User interface | Existing Exposure, Structure, Volatility, Statistics and Flow hosts | Show same canonical state, source age, assumptions and uncertainty | No new workspace taxonomy or opaque score |

Source support: [I11] [I13] [I14] [I19] [I20] [I21] [I22] [I23] [I24] [I25] [I27] [I28] [I29] [I31] [I32] [I33] [I34] [I38] [I39] [I40] [I41] [I42] [I43] [I45] [I46] [I47] [I50] [I52] [I54] [IPR7306] [IPR8451]. Commission 15 remains the accepted quote-owner source where a fresh full runtime census was outside this commission. [I08] [I09] [I10]

### Exposure Outlook is an existing forecast and outcome owner

The final bounded owner check adds Macro #7328 / MAS-260 to this map. Its remote audit/outcome paths are `engine/exposure_outlook_data.py`, `engine/exposure_outlook_prices.py`, `engine/exposure_outlook_outcomes.py` and `engine/exposure_outlook_research.py`. Native Linear separately records a local/unpushed price/volatility shadow generator/writer, strict Terminal consumer and `outlook:{ROOT}` flow-transport seam using `options_hub/outlook/{ROOT}.json`. Reconcile those sources and the separate calibration lane before selecting new module or payload names. They are not present merely because the current main census has similar functions. [M01] [IPR7328]

The recorded GEX promotion refusal survives. Reuse the active price/volatility baseline and observed-outcome owner as an additional incumbent comparator, preserve forecast identity and existing consumer contracts, and give the new inventory claim its own registration. This research supports the observed `WS:MARKET-OS` / `MAS-260` pair as records-only context; no issue/workstream state or implementation carrier changed. [M01] [M02]

## 3. Data contracts before modules

Do not create several new services because the research has several chapters. A later principal should first extend the existing schema with versioned research types. Candidate type names below are proposals, not currently existing API names:

| Proposed contract | Required identity and semantics |
|---|---|
| dealer_book_state | Contract/deliverable, participant coverage, inventory method, prior vintage, as-of and known-at, scenario or posterior, correction lineage, missing-book bounds |
| hedge_demand_scenario | Anchor and endpoint state, pricing/hedge model, surface assumption, native and common units, target hedge change, optional execution policy, exact attribution, numerical and input completeness |
| interaction_zone | Frozen boundaries and extraction method, field topology, liquidity evidence, uncertainty, invalidation, next eligible node; probabilities only from a separate calibrated model |
| intraday_probability_forecast | Target instrument/session, candidate set, horizon, label version, normalized probabilities/quantiles, out-of-sample calibration status, support and drift state |
| auction_pressure_state | Primary listing venue, rule/feed version, current phase, known public/indication fields, forecast versus nowcast, exact close target and vintage |

All types carry a common evidence envelope: model/version, source references, raw event range, receipt range, feature/consumer availability, source completeness, stale/null reasons, uncertainty kind, measurement grade, claim status and all-false authority flags. Field names must be reconciled with current schemas before implementation; this document defines economic requirements.

**Semantic states are explicit:** OBSERVED, INFERRED, SCENARIO, CALIBRATED_PREDICTION and UNAVAILABLE. A product can simultaneously have observed quotes, inferred dealer positions and scenario hedge demand. One overall badge cannot erase those differences.

## 4. Extend the October 3 ontology

The 72-row feature catalog is an extension index, not a replacement score. It records aliases or refinements of OIF-04, OIF-11 through 18 and OIF-29 through 40 where appropriate. Original OIF-01/04/19/22/13/35 pilot primaries retain their existing registrations. New hypotheses receive additive registered identities and separate budgets. [I01] [I03] [I04] [I05]

The accepted P5 v1 population is **SPY/QQQ/IWM**. The proposed mechanism-focused SPX/SPXW-to-ES experiment is a **new research cohort**, not a silent expansion of that acceptance. Its product, settlement, participant-data and outcome contracts must be registered explicitly. A SPY-only feasibility fallback uses existing eligible coverage but cannot be presented as a completed SPX dealer-book experiment.

## 5. Existing Terminal placement

Exposure can show native/common-factor book risk and signed hedge-demand scenarios. Structure can show frozen behavioral zones, uncertainty and materiality. Volatility can expose the selected IV dynamics. Flow retains observed session history and source/sign coverage. Statistics can report prospective calibration through its current owner; Terminal #799 is already an open carrier. Command can summarize those shared facts once qualified.

Current components include terminal/components/OptionsHubView.tsx, gexdesk/GexDeskView.tsx, structure/StructureView.tsx and msc/HedgingCards.tsx. terminal/lib/optionsIa.ts defines seven categories and fourteen panes. Current marketStructure.hedgeProfile already exposes sensitivity/subtotal completeness; new work must preserve that correction. [I45] [I46] [I47] [I48] [I49] [I50] [I51]

The existing flowSource registry maps GEX, GEX history, levels, gexstate, matrix and observed Flow surfaces. It has no inspected explicit scenario-surface key. Publication and natural consumer receipts are separate acceptance gates; merged source does not make a new field available to the UI. Terminal #640/#661 and #768/#769 are current contract/overlay/unknown-cell/expiry seams to coordinate with. [I52] [IPR640] [IPR661] [IPR768] [IPR769]

## 6. Machine-consumer behavior

Downstream research consumers may use qualified values as contextual covariates. Missing inventory, stale quotes, a crossed fixing, unknown denominator or uncalibrated probability produces a typed unavailable/scenario state. It does not fall back silently to zero, a nearest contract, a different root, a reconstructed future vintage or another feed's result.

Any future entry decision experiment must join these fields onto frozen incumbent candidates and evaluate the incremental decision rule. This commission grants no Prophet modification, execution decision, portfolio sizing, ranking override or autonomous trading action. An informative scenario field can ship as research context without ever qualifying for trading authority.

## 7. Implementation acceptance evidence

Require a current bounded owner/collision reread; schema and cohort registration; source receipts and rights; deterministic synthetic accounting witnesses; exact-clock replay; original incumbent outputs or explicitly marked replicas; paired out-of-sample results; consumer publication/availability receipts; and a recorded go/no-go verdict. The roadmap sequences these gates so that a complex UI or broad data purchase does not precede an information-value result.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I01]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I04]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-signal-catalog.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[I08]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/COMMISSION_15_HARDENED_REPORT.md
[I09]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/CURRENT_STATE_AND_HARDENING_LOG.md
[I10]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/VALIDATION_PROTOCOL.md
[I11]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/gex_engine.py
[I13]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/live_flow.py
[I14]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/thetadata.py
[I19]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/thetadata_store.py
[I20]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_hub.py
[I21]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/exposure_math.py
[I22]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/intraday_greeks.py
[I23]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_scenario_surface.py
[I24]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_options_scenario_surface.py
[I25]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/live_flow_poller.py
[I27]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/chain_snapshot_poller.py
[I28]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_structure_intraday.py
[I29]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_options_structure_intraday.py
[I31]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/flow_signing.py
[I32]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_signals.py
[I33]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_context.py
[I34]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_darkpool_desk.py
[I38]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md
[I39]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_alpha_candidate_feed.py
[I40]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_alpha_exact_option_outcome.py
[I41]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_nbbo_cohort.py
[I42]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/trial_ledger.py
[I43]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/entry_radar/replay/__init__.py
[I45]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/optionsIa.ts
[I46]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/workspaces/OptionsWorkspace.tsx
[I47]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/OptionsHubView.tsx
[I48]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/gexdesk/GexDeskView.tsx
[I49]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/structure/StructureView.tsx
[I50]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/marketStructure.ts
[I51]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/msc/HedgingCards.tsx
[I52]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/flowSource.ts
[I54]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/app/hub.py
[IPR640]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/640
[IPR661]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/661
[IPR7306]: https://github.com/mastermindx-market-intelligence/macro/pull/7306
[IPR7328]: https://github.com/mastermindx-market-intelligence/macro/pull/7328
[IPR768]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/768
[IPR769]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/769
[IPR8451]: https://github.com/mastermindx-market-intelligence/macro/pull/8451
[M01]: https://linear.app/mastermindx/issue/MAS-260/options-exposure-outlook-research-calibrated-forecasts-and-terminal
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/aafb9e25b0c12390ef99a9b9c4937fa1198b4bf0/agentos/workstreams/WS-MARKET-OS.md
