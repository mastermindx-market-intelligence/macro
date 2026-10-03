---
key: SECTOR-CATALYST-RECOMMENDATION-NORTH-STAR
question: >
  Are sector catalyst products complete when they brief events and expose evidence,
  or must they deliver ranked, evidence-backed stock recommendations?
answer: >
  The north star is ranked stock recommendations with explicit investment horizons,
  calibrated catalyst-outcome probabilities, conditional equity payoffs, priced-in
  expectations, complete source-grounded theses and prospective learning. Briefings,
  calendars, research browsers and facts-only slices support that outcome; they are
  not the finished product. Recommendations and developing signals share one
  cross-sector workspace, with distinct specialist engines and sector/theme depth.
rationale: >
  The Chairman explicitly rejected the briefing-only ceiling in the BioCatalyst
  redesign and applied the investment-intelligence mandate to Defense Procurement
  and future sector research lobes. Users should receive researched judgments, not
  assemble them from raw documents or analyst to-do lists. Validity and release gates
  must make recommendations trustworthy rather than permanently remove them from
  the intended design.
alternatives:
  - option: End with a facts-only catalyst calendar and research workflow
    why_not: >
      Preserves source truth but fails the expressly requested investment-selection
      outcome and shifts the core analytical work back to the customer.
  - option: Use uncalibrated LLM confidence or sentiment as a buy score
    why_not: >
      Persuasive prose is not demonstrated edge. Scientific, regulatory and investment
      outcomes differ; pricing, loss severity and costs can reverse the recommendation.
  - option: Build a separate all-purpose ingestion, identity, rank and execution stack per sector
    why_not: >
      Duplicates existing canonical owners. Domain-specific models and evidence must
      compose with the shared intelligence, recommendation and evaluation systems.
  - option: Merge clinical, procurement and other catalyst models into one generic score
    why_not: >
      Shared presentation and investment comparisons do not make different targets,
      priors, evidence or causal models interchangeable.
evidence:
  - "Current Chairman direction recorded in substance on macro#6712 comment5851663121."
  - "https://github.com/mastermindx-market-intelligence/macro/pull/6712#issuecomment-5851663121"
  - "agentos/workstreams/WS-BIOCATALYST-CORE-PRODUCT.md at1990a8b8bb2c02ce8595648dcf2cad1f44e29e88: current facts-only slice and existing ownership limits."
  - "agentos/workstreams/WS-DEFENSE-PROCUREMENT-V3.md at1990a8b8bb2c02ce8595648dcf2cad1f44e29e88: existing financial-alpha program and Government Revenue substrate."
  - "research/SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md: shared implementation and acceptance contract."
  - "Current R8 Chairman direction: unify catalyst signals and picks across sectors while keeping specialist engines separate; recorded in research/CATALYST_INTELLIGENCE_UNIFIED_WORKSPACE_AND_ENGINE_CONTRACT.md."
affects:
  - "WS:MARKET-OS"
  - "WS:BIOCATALYST-CORE-PRODUCT"
  - "WS:DEFENSE-PROCUREMENT-V3"
  - "WS:GMI-THEME-GRAPH"
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/biocatalyst_decision_intelligence_v3/"
  - "research/defense_intelligence/"
  - "research/SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md"
  - "research/CATALYST_INTELLIGENCE_UNIFIED_WORKSPACE_AND_ENGINE_CONTRACT.md"
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-26
---

# Sector catalyst intelligence must culminate in investment selection

## The Chairman's actual intent

The customer-facing north star is a ranked page of stocks to buy, with the relevant
catalyst, dates, investment timeframe, estimated likelihood of positive and negative
outcomes, potential rerating magnitude, what is already priced in, and the actual
investment thesis behind each recommendation. The underlying system researches the
company and its economics extensively rather than merely summarizing a press release.

For BioCatalyst this includes earnings, filings, transcripts, scientific papers, FDA
filings/notices, prior phase I/II/III studies, therapeutic-area and modality history,
company execution expertise, statistical design and granular trial evidence. Deterministic
capture and normalization supply the facts; evidence-bound LLM research and evaluated
models determine what those facts imply. The same investment contract applies to Defense
Procurement with its own program, budget, award, execution and financial evidence.

The aspiration is a high proportion of strong realized investment outcomes with positive
risk-adjusted expected value. It is not to win every bet, fabricate certainty, maximize a
cosmetic win rate, or hide losses. Achieving that aspiration is an empirical obligation,
not a result established by the Chairman's direction or this record.

## What is superseded, and what is not

This decision supersedes the **design interpretation** in BioCatalyst R6 that a prepared
briefing is the ultimate product. R6's readable hierarchy, evidence transparency and
working interactions remain reusable. The earlier R4/R5 primary layouts were already
rejected; do not restore their research-task-first composition.

It does not retroactively broaden an accepted facts-only production slice, revive
`DNR:KILL-PHASE3-START-WEIGHT`, waive historical method/source holds, authorize unreviewed
model deployment, or turn Agent OS into an admission service. A generic "no probabilities
in this accepted payload" remains true of that payload until its owner approves a successor.
It must no longer be cited as a reason to omit the capability from the future design.

No prior DEC is deleted or globally superseded: existing identity, financial, event,
rights, temporal, recommendation, evaluation and trading owners remain intact. This is an
additive product-direction decision. Its source-publication status must be reported
separately from live implementation readiness.

## Required result

A future builder should be able to trace one stock pick through:

**rank and stance → reference price and horizon → event/timing definition → outcome
probabilities → conditional diluted equity values → market-expectation comparison →
scientific/commercial evidence and counter-thesis → versioned recommendation → measured
investment outcome.**

A calendar, a source lake, a model-only score, an elegant dashboard or a green test suite
is not this complete vertical. Abstention is legitimate when the accepted policy says
there is no adequate edge; making the product permanently abstain is not fulfillment.

## Placement and reuse

Use the shared contract at
`research/SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md`. Domain plans link to it
rather than copying competing versions. GMI / Research Vault, Company/Event and Earnings,
Financial Intelligence / Capital Structure, Alpha/expectations, recommendation/entry and
existing evaluation/portfolio owners keep their respective jobs. Sector lobes supply
specialist evidence, features and evaluated assessments through those owners.

Confidence "high" above means confidence that this accurately records the Chairman's
choice. It is not confidence in any stock, model, forecast or achievable win rate.

## R8 refinement — one workspace, not one specialist model

The subsequent Chairman direction keeps ranked recommendations as the intended outcome
but rejects R7's sector-switching front door and a separate picks-versus-signals experience.
Use one **Catalyst Intelligence** candidate universe across relevant sectors. Buy, Wait,
Watch, Researching and Avoid are stances within it. A developing signal becomes stronger
evidence for the same investment case rather than a disconnected second product.

BioCatalyst and Defense Procurement remain distinct specialist engines with their own
targets, priors, evidence, timing, calibration and financial mechanisms. Sector panels
expose their complete candidate sets, methodology and evidence coverage. Themes cut across
those sectors through the existing GMI graph; they do not invent a blended theme model or
turn repeated membership into independent exposures. Clinical pass probability is never
ranked directly against procurement win probability. Compare only qualified investment
outputs on a common horizon/currency/price/cost/benchmark basis through the accepted owner.

The detailed companion is
[`CATALYST_INTELLIGENCE_UNIFIED_WORKSPACE_AND_ENGINE_CONTRACT.md`](../../research/CATALYST_INTELLIGENCE_UNIFIED_WORKSPACE_AND_ENGINE_CONTRACT.md).
It refines the shared north-star contract's presentation and backend composition, not its
requirements for calibration, source rights, economic depth or prospective learning.
WS:MARKET-OS remains the product owner and WS:ALPHA-INTELLIGENCE-INTEGRATION the semantic
owner; OpportunityCase remains its future gated K5 identity, not a new R8 store.

This refinement does not retrospectively certify the R7 prototype, merge the underlying
engines, or widen any live production authority. Source adoption and implementation
acceptance remain distinct. Preserve historical R7 evidence; its front-door composition
is superseded, not silently rewritten as a failed test or an accepted production design.
