# Catalyst Intelligence — unified workspace, specialist engines

**R8 design and backend companion.** Extends
`SECTOR_CATALYST_INVESTMENT_INTELLIGENCE_NORTH_STAR.md` and
`DEC:SECTOR-CATALYST-RECOMMENDATION-NORTH-STAR`; it is not another global architecture,
workstream, ranker, event store, scheduler, or model-admission authority.

Current Chairman direction: one beautiful, immediately understandable catalyst-investment
workspace across sectors; recommendations and developing signals together; separate
sector/theme panels exposing candidate breadth, research and methodology. BioCatalyst and
Defense Procurement must remain distinct specialist engines. The R7 sector-switching front
door is superseded by this composition, not its investment ambition or evidence discipline.

**State:** populated synthetic design/prototype and candidate architecture. No native Paper
application, trained backend, production recommendation, model calibration, or default-branch
adoption is established by this document. Existing live restrictions remain in force.

Source basis: Mastermind protected `4c6b206d3fb7fbc6d077faf61ae361bedf259925`;
Macro owner research `8b9cee8b40fa9b009085fd114497f473a52a33da`. This work remains on
Macro #8061, separate from #6712's implementation source.

## 1. The product model

**One investment experience; several specialist research engines.** A customer should not
have to choose an industry before discovering an opportunity. Nor should the same evolving
idea exist once as a signal and again as a disconnected pick.

The primary page contains one candidate universe. Buy, Wait, Watch, Researching and Avoid
are visible stances on candidate cases, not separate products. Qualified picks receive
ranking and prominent interpretation. Developing cases stay discoverable with the missing
qualification explained, not fabricated probabilities or zero returns. Chronological and
return-based orderings are views of that same population. Status and evidence maturity are
independent axes: a high-quality analysis may say Avoid; a newly discovered event may be
Researching. Neither axis should be inferred from the other.

A candidate's front door is a security-level investment assessment with explicit horizon
and price. Its supporting catalyst cases retain their event identities. A company with
three catalysts must not become three apparently independent investments. In a genuinely
multi-event company, the lead row synthesizes the qualified joint assessment; expansion
shows each event and its contribution. If joint valuation is unavailable, publish the
research cases without inventing a combined equity forecast.

The machine's job is to find and assess material changes, conduct specialist research,
translate outcomes into issuer economics and decide whether the price offers an edge.
The customer's job is to understand, inspect and choose—not reproduce that analysis.

## 2. Navigation and three levels of depth

**All catalysts:** one cross-sector opportunity list with a prepared lead, other-sector
highlights, timing, stance, comparable expected return and the principal loss scenario.
One common filter state controls the lead, list, counts and exports. No unfiltered hero
above a filtered list. Unknown estimates sort as explicitly unassessed, not negative or zero.

**Sectors & themes:** two dimensions of the same universe. A sector panel exposes its entire
candidate set, domain research/methodology, evidence coverage and eventual validation record.
A theme can cross sectors. Autonomous systems can include defense platforms and chips;
that does not create an "autonomy model" that blends contract awards with chip qualification.
Every constituent retains its actual engine, native event and financial mechanism.

**Company thesis:** one clear recommendation and strongest caveat, followed by research and
counter-evidence, outcome/payoff branches, valuation/priced-in assumptions and revision
history. Links open source evidence and the relevant specialist method. Returning restores
the original scope, horizon, scroll and initiating focus. Direct URLs must carry enough
state to avoid reopening a different cutoff or silently resetting the investment horizon.

The backend blueprint belongs in builder/research depth, not the default customer nav.
Global navigation must be composed from the existing shared shell in production. The local
prototype shell is a design reference, not permission to create another header family.

## 3. Visual composition

Dark: graphite canvas, restrained luminance depth, clear typographic contrast and blue
wayfinding. Light: cool canvas, white materials, measured text contrast, borders and quiet
shadows. Color describes stance, signed payoff, risk or action; sector identity does not
require rainbow branding. Preserve the shared Inter/type/spacing vocabulary.

The lead delivers company, investment interpretation, horizon, expected return, exact
probability target and failure risk before exposing mechanics. The payoff drawing shows
conditional scenarios, not a fictional historical price chart. Its numbers reconcile to the
same assessment as the table and export. It is schematic: curves are not predicted paths
through time. Smaller adjacent cards reveal opportunities from other sectors immediately.

On mobile the lead and primary action come first, followed by compact cross-sector reads
and the same mixed candidate list. Specialist depth is a readable sequence, not a shrunken
workflow diagram. Whitespace and stronger hierarchy must reduce reading effort; they are
not a substitute for a useful conclusion. A production design still needs independent
visual judgment and a cold-reader comprehension test. Local checks do not confer an award.

## 4. What is shared and what must remain separate

| Layer | Shared responsibilities | Must stay domain-specific |
|---|---|---|
| Evidence foundation | Canonical issuer/security/asset identity; rights; source versions; clocks; research references | Source adapters, specialist extraction, legal/scientific terminology |
| Research | Evidence-bound questions, contradictions, retrieval discipline, model provenance | Protocol scrutiny, award competition, yield/capacity, project permits and other causal reasoning |
| Forecast | Target/horizon/version/uncertainty interface and evaluation discipline | Labels, cohorts, priors, outcome states, timing/hazard model, calibration and release scope |
| Economics | Existing financial facts, dilution, cash/debt, currency and cost conventions | Commercial uptake, funded orders/delivery, yield/units, project milestones and retained economics |
| Selection | Accepted recommendation/entry/risk policy over comparable investment outputs | Domain exclusions, risks and supported horizon/coverage constraints |
| Experience | One case/list, common navigation, continuity, understandable presentation | Specialist methods, source dossier and native-outcome explanation |

BioCatalyst is not renamed to mean every catalyst. It remains the clinical/regulatory
specialist. Defense Procurement remains its separate program/award specialist. Energy,
resources, semiconductors and later event families enter only through their own assessed
scope. A sector classification alone does not identify the correct engine; one sector may
need several event-family adapters. A commercial semiconductor qualification and an export
license decision are different target models even when they concern the same company.

## 5. Canonical owners, not a new platform

`DEC:MARKET-INTEL-PRODUCTIZATION-NO-NEW-WORKSTREAM` assigns user-facing execution to
**WS:MARKET-OS**, and semantic contracts to **WS:ALPHA-INTELLIGENCE-INTEGRATION**.
`security_state.v1` is the compact security projection. **OpportunityCase is a future K5
episodic synthesis identity** and must not be assumed deployed or replaced by an R8 invention.
RetailDecisionPacket, DeskResearchPacket and similar views are projections, not extra truth
objects. OpportunityCase prose must not become a Prophet ranking input.

GMI's existing graph supplies sector/theme membership and temporal economic relationships;
existing Company/Event and Earnings owners supply filings, disclosures and corporate events;
Financial Intelligence/Capital Structure supplies cash, debt, shares and financial semantics.
The Alpha K3E owner matrix preserves **MAS-119** for common expectation semantics and
**MAS-118** for family-specific incorporation science. Existing options, residual, identity,
recommendation, portfolio, alert, publication and evaluation owners retain their jobs.

Concrete owner reference:
`research/alpha_intelligence/expectation_market_dynamics/OWNER_AND_REUSE_MATRIX.md`,
blob `ebd787cae2da3a7c72820199c59e38544f7483b7`. Productization decision blob
`4d9fb65b68a29062b11a78708a16737317c48a6a` at the source basis above.

Before implementation, verify actual accepted seams and availability at the then-current
head. A named owner is not proof a needed method/API exists. Missing capability becomes a
bounded extension of that owner, never a duplicate universal catalyst store or rank service.

## 6. The specialist assessment contract

The following is a **proposed field mapping into existing contracts**, not a new persisted
schema or independently active service. The owning implementation must freeze exact fields.

| Field group | Required semantics |
|---|---|
| Identity | Canonical security; economic asset/program; source-native event; engine/event-family; optional theme references |
| Information | Source versions, publication/observation/effective times, rights, analysis cutoff, evidence coverage |
| Target | Named event/outcome definition, horizon, phase/program stage, resolved/unresolved labeling rule |
| Specialist model | Method/model version, cohort/prior definition, structured findings, counter-evidence, calibration and uncertainty references |
| Outcome distribution | Exhaustive joint states where claimed; time/delay model; dependencies; explicit unavailable dimensions |
| Economic translation | Rights, other assets, volume/price/margin, cash/debt, financing/dilution, conditional value and sensitivity |
| Market comparison | Reference price/time/currency; valuation-inversion assumptions; independent expectation evidence; supported benchmark/cost basis |
| Policy output | Accepted owner decision/rank eligibility; reason; horizon; risk/entry constraints; assessment version |
| Learning | Frozen prediction identity, observation/label maturity, outcome evaluation and correction lineage |

A generic `confidence=0.8` is not sufficient. A clinical endpoint probability, first-cycle
approval probability, procurement win probability and probability of positive net stock
return are distinct targets. Native outcome sets remain typed; probabilities are never
normalized across engines merely because they all range from zero to one.

The prototype now labels Phase III, Phase II, FDA decision, award, down-select and customer
qualification separately. Its generic sector-based clinical/regulatory caption was corrected
after review. Production must obtain these labels from accepted target definitions rather
than hard-coded demo IDs.

## 7. Where cross-sector comparability begins

Comparability begins **after** each specialist result is translated into a stock-return
distribution, not at a shared catalyst score. Require the same investment horizon, reference
price timing convention, currency basis, transaction-cost treatment, benchmark/hurdle and
scenario valuation basis. Calibration uncertainty, liquidity and risk constraints remain
visible. A six-month expected total return cannot be compared to a three-day event reaction
or a twelve-month target merely by dividing or annualizing the number.

For each security/horizon, existing policy consumes expected net return/excess, probability
of profit, probability of the specified hurdle, loss severity/tails, model uncertainty,
liquidity/capacity and concentration. The prototype's expected-return sorting demonstrates
UI mechanics only; it is not an accepted risk-adjusted production ranker. A positive expected
return can still fail the risk policy and appear as Avoid, with the reason attached.

If a shared comparable basis is absent, the candidate remains visible in the integrated
research universe without a comparable rank or numeric payoff claim. Never coerce missing
returns to zero. More data from one engine must not automatically win it more top slots.
Report coverage and selection propensity and test domain imbalance. Fixed sector quotas
are not a substitute for a justified portfolio/ranking policy.

## 8. Themes, repeated companies and dependent catalysts

Theme membership is many-to-many context, not extra independent evidence. Counts distinguish
unique securities, event cases and theme-membership edges. A stock in two themes remains one
security-level exposure. A company containing both a clinical asset and a defense contract
keeps two specialist assessments; an existing joint scenario/portfolio owner integrates
retained economic effects rather than adding standalone percentage upsides.

Dependency groups should preserve shared drug classes, suppliers, budgets, counterparties,
policy changes and common discount-rate exposures. Competing bidders for one exclusive award
cannot all be independently assigned unconstrained high win probabilities. Preserve the
competition set, no-award/multi-award possibilities and incomplete coverage. Independent
simulations are not proof of diversification. The same applies to repeated trials of one
asset and to several companies depending on one customer's capital spending.

## 9. End-to-end backend workflow

1. **Observe and version.** Existing source owners capture evidence and identity once, retaining
rights and three clocks. An amendment or corrected financial fact is a new version, not a
rewrite of yesterday's forecast.
2. **Find affected cases.** Through existing graph/research ownership, map the changed evidence
to assets, issuers and live investment cases. Deduplicate repeated documents before reasoning.
Only a material dependency change schedules reevaluation; page views do not launch research.
3. **Research and challenge.** The existing admitted research workflow executes bounded
specialist questions over a pinned evidence set. Deterministic extraction supplies facts;
LLM research identifies implications and counterarguments with source spans. Persist method
and evidence versions through existing owners. Correlated summaries are not a voting model.
4. **Estimate and value.** Each engine emits its own evaluated target distribution. The existing
financial/valuation owners translate it into horizon-specific diluted equity scenarios,
including the rest of the company. Expectations and sensitivity remain separate evidence.
5. **Select and publish.** Existing recommendation policy decides stance/eligibility. The
existing publisher produces one coherent read snapshot, including accepted versions, coverage
and unavailable components. The product reads that snapshot; it never reranks prose or rebuilds
financial models in the browser.
6. **Observe results.** Existing evaluation retains the original forecast, price, horizon,
coverage, rejection and subsequent outcome. Diagnose research, target, valuation, expectation,
execution and regime errors separately. Recalibration passes the existing release process.

LLM calls, historical scans and valuation fitting belong off the request/render path.
Latency goals are proposed acceptance targets, not measured here: a prepared cached view
should return inside the existing product budget; source-to-recommendation freshness must be
specified per event family. Do not invent a new queue, publication service, invalidation
registry or cache hierarchy to satisfy those goals. Bound payloads, page candidate lists,
and reuse the current typed cursor/snapshot contract where available.

## 10. Consistency, failure and repair

A displayed snapshot binds the candidate set, filter scope, horizon, source/assessment/policy
versions and comparison basis. Counts and ordered pages cannot silently mix generations.
A cursor from an old snapshot must either resolve that immutable view or require an explicit
refresh. Historical detail uses the chosen cutoff, not later documents or current ownership.

One failing engine should withhold only its affected estimates while keeping valid source
facts and other healthy domains usable. However, failure of a shared dependency—identity,
price, financial input or recommendation policy—must invalidate every dependent result.
Do not isolate by sector when the actual dependency crosses sectors. If a ranking population
is partial, show its denominator/scope; the remaining first row is not necessarily the best
opportunity in the intended full universe.

Never display an old Buy as current beside a fresh price without recomputation or an explicit
stale-reference state. Model outage, calibration rejection, missing source and stale evidence
are different conditions. None becomes a confident zero. Auth failure remains distinct from
plan denial. Saving, monitoring and trading remain separately confirmed operations.

The R8 outage control is a **local synthetic scenario**, not an operational repair tool. It
withholds semiconductor estimates and current Buy counts while retaining two semiconductor
candidates and unaffected biotech/defense values. Restoring it makes no real recovery claim.

## 11. Specialist profiles and evidence depth

**BioCatalyst:** phase/indication/modality/endpoint cohorts; protocol, estimand, population,
control, multiplicity, effect size and uncertainty; durability, safety, manufacturing and
regulatory evidence; rights, patient adoption, reimbursement, launch costs and dilution.
Trial success, FDA approval and stock profit are separately evaluated.

**Defense Procurement:** competition, incumbent/technical position, funding and award route;
protests, down-selection, capacity and delivery; funded orders, retained revenue, margins,
working capital and cash. Authorization, appropriation, obligation, ceiling, award, revenue
and profit are not interchangeable. The R8 numerical worksheet is explicitly synthetic:
$240m assumed funded orders × 60% delivered × 18% operating margin = $25.92m contribution,
not whole-company fair value or free cash flow.

**Semiconductors:** qualification/design-in evidence, customer programme, capacity/yield,
unit economics, pricing/mix, cycle and dependency concentration; qualified shipments and
margins produce the financial forecast, not the announcement count.

**Energy/projects and resources:** regulatory/connection/permit/feasibility targets, funding,
construction and commissioning; contracted economics, capex, production, price/cost exposure
and balance-sheet survival. These require event-specific models, not copied clinical priors.

The present additional sector profiles are method designs; the prototype does not imply
new engines are installed. Unassessed energy/resource examples deliberately remain signals
in the same universe without invented forecast numbers.

## 12. Evaluation and first implementation slices

**First slice: full Bio investment case.** The existing owners choose one rights-accessible,
reconstructable event cohort and produce source dossier, specialist targets, joint diluted
valuation, expectations, accepted shadow policy and a complete user-facing case. Test failed,
delayed, no-edge and missing-source cases. Ingestion alone cannot close the slice.

**Second slice: independent Defense case.** Retain its programme/award target and funded-order
financial model. Prove the same investment output on the common horizon/basis; do not reuse
Bio priors or an unqualified raw probability. Delivery requires a working specialist panel
and a full individual thesis as well as the shared list.

**Third slice: cross-domain selection and theme proof.** Two independently qualified engine
outputs, a full candidate denominator, repeated-security/theme deduplication, dependency-aware
risk and partial-failure behavior pass through the incumbent recommendation/publication paths.
Verify that raw success probabilities cannot control cross-sector order. Test both likely
success/negative-EV and positive-EV/risk-rejected counterexamples.

**Then expand scope.** Add each new target family only after extraction accuracy, temporal and
clustered holdouts, calibration, evidence rights and prospective shadow investment utility
pass its preregistered acceptance. Keep eligible coverage and false exclusions visible.
Retrospective LLM evaluation must acknowledge model-weight future-knowledge leakage; retrieval
cutoffs alone cannot remove it. Freeze prospective forecasts and evaluate actual net returns,
benchmark excess, hit rate, payoff ratio, severe losses, turnover and capacity. No percentage
accuracy or excess-return goal in this document is an achieved result.

## 13. Discriminating acceptance cases

These extend, not replace, SC-01 through SC-30 in the shared contract. They are proposed
backend/production proofs, not the local browser assertion count.

- UI-01: the same filtered population includes qualified picks and developing signals; changing
scope updates hero, list, counts and export together.
- UI-02: sector depth includes the entire accessible candidate set, including Watch/Avoid and
unassessed cases; themes retain exact engines and unique-security counts.
- ID-01: two signals for one catalyst update one versioned case; two catalysts for one issuer
do not create independent security recommendations without a qualified joint assessment.
- MD-01: clinical/approval/award/qualification targets retain definitions, cohorts and model
versions; a change to one model cannot relabel another engine's outputs.
- MD-02: same-number probabilities across different targets never establish comparability.
- RK-01: wrong currency/horizon/cost/cutoff or missing calibration excludes comparable rank,
not source visibility; no annualization or zeros repair the mismatch.
- RK-02: a high-success/negative-EV case and positive-EV/tail-risk-rejected case both remain
explainable outside current Buy eligibility.
- DP-01: exclusive-award competitor probabilities and correlated assets are reconciled by the
accepted dependency model rather than summed as independent opportunities.
- VT-01: event→earnings/cash→diluted equity→net return is arithmetically and economically
traceable; partial worksheets cannot masquerade as a complete equity bridge.
- PB-01: page, cursor, counts, headline and export bind one snapshot and policy generation.
- FL-01: one lobe's stale forecast does not erase other valid lobes or retain stale current Buy.
- FL-02: shared-dependency corruption withdraws all affected lobes; a sector-only circuit
breaker must not conceal common input failure.
- PT-01: historical evidence and ownership exclude later corrections unless explicitly replayed;
original recommendations and observed outcomes remain retained.
- EV-01: forecasts and investments have distinct targets and prospective learning, including
failed/discontinued programmes, delistings, no-pick coverage and missed winners.
- UX-01: real readers can identify the idea, stance, date/horizon, expected payoff and principal
risk within seconds; responsive, keyboard and EN/ZH parity are independently checked.

## 14. Exact R8 prototype proof and limits

The self-contained artifact is `CATALYST_INTELLIGENCE_R8_PROTOTYPE.html`, SHA-256
`43081d3d612037f9713cf57839407995602e0dd880be771c7aac3c4f0f98cd1f`.
Twelve fictional candidates, five method profiles, a mixed-stance list, sector methodology,
Autonomous-systems cross-sector theme, company-specific study/award evidence, valuation,
export, return-state continuity and an on-design backend blueprint work locally.

Final browser report: **232 passed / 0 failed**; separate presence discrimination six passed
versus zero/six on R7; 40 full-page theme/desktop/mobile renders and five first-read/fault
captures. All final proof binds the same HTML. Zero page exceptions or external requests.
Repeated viewport assertions are not 232 independent production requirements. Targeted
negative evidence caught a wrong negative-return color, paused-engine Buy counts, lead-footer
spacing and imprecise event-probability captions; each was repaired and rerun. A procurement
caption test also required case-insensitive matching of CSS uppercase text; that was a test
mechanism correction, not a hidden data repair.

A later targeted negative check exposed stale stance leakage: a Buy-only filter still
matched an unavailable-horizon or paused-engine underlying fixture. Three failing checks
were captured before the repair. Current display status and filtering now agree: paused
records say Review paused; unsupported assessed horizons say Not assessed; neither qualifies
as a current Buy. All candidates remain discoverable in the full view. The 232-check final
run and regenerated images bind the repaired artifact, not the earlier 229-check source.

The R7 snapshot is preserved as a linked prior reference, not rebuilt or silently relabelled.
Its old numerical/safety limits remain. No calibrated confidence interval, source corpus,
actual financial model or historical performance is fabricated. English only; Chinese parity,
real account/source/model/portfolio behavior, native rendering and human design acceptance
remain unproven. Static model IDs in this prototype are synthetic labels, not live registries.

## 15. Native Paper and exact continuation

Same Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-K-0`, existing board `1ECU-0`,
content `1EJZ-0`, heading `1EK0-0`. Fresh read still finds only that heading. R8 makes zero
native design mutations while the existing same-file reservation lacks a returned release.
Do not repeat the completed nine-gateway repair, reapply rejected R4/R5 fragments, create a
replacement file to evade custody, or replay safety-held watch/indicator actions.

After lawful existing-owner admission, recompose the same board as the unified opportunity
front door, add its specialist/theme depth and inspect actual native screenshots. Preserve
R1 source references and R7 scientific/financial content. Source adoption of this companion
still requires #8061's review/release process; an open PR is not universal programme adoption.
