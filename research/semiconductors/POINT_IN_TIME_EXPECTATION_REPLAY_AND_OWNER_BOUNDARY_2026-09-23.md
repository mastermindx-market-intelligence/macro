# Semiconductor Intelligence — Point-in-Time Expectation Replay and Native-Owner Boundary

**Research installment 5B — 23 September 2026 · principal-owned research · not a production contract or Fable handoff**

Operation: `gmi-semiconductors-research-20260923-sol-001`. Parent: `WS:GMI-THEME-GRAPH`. Existing carrier: Macro draft/HOLD PR #7780, branch `sol/semiconductors-research-20260923`. Research resumes from canonical head `78f9d5be8e53df5b0f2d146ebb4ce5333158fa6a`. Governing protected procedure: Mastermind `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap 1.

This document tests the expectation model from `BUSINESS_MODELS_EXPECTATIONS_AND_RERATING_2026-09-23.md` against current Mastermind ownership and six bounded issuer-guidance replays. It creates no consensus store, price-history store, forecast, valuation signal, basket, ranking, entry, sizing, trade, graph, queue, publisher or runtime authority.

## 1. The implementation boundary is now explicit

The Semiconductor Theme should compose expectation intelligence from existing specialist owners. It should not create a semiconductor-specific expectation database or a universal market-belief object.

| Concern | Current owner / capability | Immediate semiconductor use | Refusal / held dependency |
|---|---|---|---|
| Issuer event, source, guidance and Q&A truth | Earnings Intelligence | Source-backed management guidance and actual-event context | Do not create a second event/guidance store. |
| Financial facts and historical cutoffs | Financial Intelligence Fabric / governed financial semantics | Compatible actuals, definitions and cutoffs when accepted | Do not recompute a second financial fact model. |
| Current analyst-revision snapshots | Existing revisions/expectation owner, `PARTIAL / ACCRUING` | Prospective observations from their actual observation-era birth | They are not deep historical consensus truth. |
| Historical Street consensus | `NOT_BUILT` at required depth; vendor program remains sample/rights gated | Typed unavailable/unlicensed state | Never backfill a current snapshot into history or scrape a shadow estimate history. |
| Common expectation semantics | Future accepted owner federation / existing architecture seam | Consume when accepted | Do not preempt with a GMI or Market-OS expectation DB. |
| Market-incorporation / reaction science | Existing Alpha/expectation and market-data owners | Display only when accepted PIT evidence exists | No universal gap score or causal price attribution from this research. |
| Price and corporate actions | Existing market-data owners; current estate has multiple adjustment vintages and no accepted PIT corporate-action store sufficient for universal replay | Use accepted current/historical observations when the required basis is valid | Degrade/refuse historical rerating attribution when point-in-time adjustment basis is not supported. |

Current repository evidence read for this boundary:

- `research/market_os/FISCAL_RESEARCH_OS_ARCHITECTURE_DELTA_2026-08-22.md`, blob `d925e8a4ee585c1f85d6f8445b3b156af4c24554`: no universal Market-Belief truth store; expectation composition must preserve native owners; current analyst revisions are partial/accruing; deep historical Street consensus is not built at required depth.
- `research/alpha_intelligence/expectation_market_dynamics/VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md`, blob `aebcc08603547e4c26542d2fdf1e3805327b0e18`: institutional-estimates candidates remain sample/rights gated; current snapshots cannot be projected backward to manufacture history.
- `research/entry_stack/W4_EARNINGS_REACTION_PRIOR.md`, blob `8e856081f2319912842157ff3185a8428afa191f`: historical consensus/revision depth was not available for the proposed earnings-dislocation engine; guidance-vs-consensus remained partial.
- `research/earnings_intelligence/g0/G0_EVENT_CLOCK_AND_CONTRACT_CENSUS.md`, blob `c4063ef52c86d7c16e70132f82aaaac92392df85`: event/source clocks exist; live workspaces can truthfully expose `consensus=unlicensed` and forbid beat/miss semantics without a compatible basis; FIF uses source-event and system-recorded cutoffs.
- `research/MASTERMIND_TEMPORAL_DATA_STANDARD.md`, blob `74d3d389648875d6c53b08dedbc0b82de21a0134`: historical point-in-time correctness is a separate problem from current-state reads; later-revised data must not leak into historical analysis.
- `research/MASTERMIND_DATA_SOURCE_CATALOG.md`, blob `2ee99b4d37cecac4f2b4ae6b7e66f42866201684`: multiple price stores can carry different adjustment vintages; an `adjusted` boolean is insufficient without basis/vintage context.

These repository records are evidence of current architecture/capability boundaries. They do not authorize implementation and do not revive historical plans merely because those plans are mentioned.

## 2. Replay method

Each replay has two cuts:

- **Cut A**: only the issuer information published at the earlier earnings/outlook event is permitted.
- **Cut B**: the later result and new management outlook become available.

Allowed output at Cut B:

1. preserve the Cut-A management expectation exactly enough to explain the comparison;
2. add the Cut-B actual and new management expectation;
3. calculate a guide-to-actual delta only when metric, period, unit, accounting basis and business perimeter are compatible;
4. retain assumptions and source clocks;
5. refuse Street-consensus surprise if no accepted historical consensus object exists;
6. refuse causal market rerating attribution when the required point-in-time price/corporate-action basis is not available from an accepted owner.

A result being above a management midpoint is **not** the same as a Street earnings/revenue beat. A new guide being above an old guide is **not** automatically organic acceleration. A price move after the report is **not** a causal proof of which fundamental item mattered.

## 3. Replay PT01 — Foundry / TSMC

### Cut A: Q1 2026 results

The issuer reports Q1 revenue of $35.90 billion and management guidance for Q2 revenue of **$39.0–40.2 billion**, gross margin **65.5–67.5%**, and an exchange-rate assumption of 31.7 USD/NTD.

Source: https://investor.tsmc.com/english/quarterly-results/2026/q1

### Cut B: Q2 2026 results

The issuer reports Q2 revenue of **$40.20 billion** and gross margin of **67.7%**, then guides Q3 revenue to **$44.6–45.8 billion** and gross margin to **65–67%**.

Source: https://investor.tsmc.com/english/quarterly-results/2026/q2

### Allowed replay

- Derived Cut-A Q2 revenue midpoint: `(39.0 + 40.2)/2 = $39.6 billion`.
- Q2 actual versus prior management midpoint: `40.20 / 39.60 - 1 = +1.5152%`.
- Q2 actual is at the high end of prior revenue guidance; actual gross margin is above the prior gross-margin high.
- Q3 revenue-guide midpoint is $45.2 billion; its sequential relationship to Q2 actual may be shown as a management-outlook transition, not as a consensus forecast.

### Forbidden replay

- Do not say TSMC “beat consensus” unless the existing consensus owner supplies the point-in-time comparable object.
- Do not infer that Q3 gross margin will exceed Q2 because revenue guidance rises; management's Q3 margin range is lower than Q2 actual.
- Do not backfill the Q2 actual or Q3 guide into a Cut-A historical view.

## 4. Replay PT02 — Fabless platform / NVIDIA

### Cut A: Q1 FY2027 results

NVIDIA reports Q1 revenue of $81.615 billion and guides Q2 revenue to **$91.0 billion ±2%**. The outlook explicitly assumes **no Data Center compute revenue from China**.

Source: https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027

### Cut B: Q2 FY2027 results

NVIDIA reports Q2 revenue of **$96.221 billion** and guides Q3 to **$108.0 billion ±2%**, again with no China Data Center compute revenue assumed.

Source: https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027

### Allowed replay

- Q2 actual versus prior management point: `96.221 / 91.0 - 1 = +5.7374%`.
- Preserve the explicit China-exclusion assumption on both guide vintages.
- The new Q3 management point is a new expectation observation with its own publication clock.

### Forbidden replay

- Do not label +5.7374% a “consensus surprise.” It is actual versus prior management guide point.
- Do not infer what Q2 would have been with unrestricted China Data Center compute revenue.
- Do not use the new Q3 guide to rewrite what was knowable after Q1.

## 5. Replay PT03 — Semiconductor equipment / ASML

### Cut A: Q1 2026 results

ASML guides Q2 total net sales to **€8.4–9.0 billion** and full-year sales to **€36–40 billion**.

Source: https://www.asml.com/en/news/press-releases/2026/q1-2026-financial-results

### Cut B: Q2 2026 results

ASML reports Q2 total net sales of approximately **€9.3 billion**; its detailed reported value used in the research arithmetic is €9.326 billion. It says results were above guidance, driven primarily by higher-than-expected Installed Base Management sales. It guides Q3 sales to **€11–12 billion** and raises full-year guidance to **€43–45 billion**.

Source: https://www.asml.com/en/news/press-releases/2026/q2-2026-financial-results

### Allowed replay

- Prior Q2 midpoint: €8.7 billion.
- Using the reported detailed value in the research source, Q2 versus prior midpoint: `9.326 / 8.7 - 1 = +7.1954%`.
- Prior FY midpoint: €38 billion; new FY midpoint: €44 billion; management midpoint revision: `44 / 38 - 1 = +15.7895%`.
- Preserve the issuer's attribution to Installed Base Management rather than labeling all upside as new scanner shipments.

### Forbidden replay

- Do not treat system shipments, installed-base sales, bookings and recognized revenue as one measure.
- Do not call the FY midpoint change a Street revision.
- Do not convert strong orders into revenue without the company's recognition/acceptance mechanics.

## 6. Replay PT04 — EDA / Cadence, with a required refusal

### Cut A: FY2025 results / initial FY2026 outlook

Cadence guides FY2026 revenue to **$5.9–6.0 billion** and explicitly states that the outlook **does not include the pending acquisition of Hexagon's Design & Engineering business**.

Source: https://investor.cadence.com/news/news-details/2026/Cadence-Reports-Fourth-Quarter-and-Fiscal-Year-2025-Financial-Results/default.aspx

### Cut B: Q2 2026 results / current FY2026 outlook

Cadence guides FY2026 revenue to **$6.26–6.34 billion** and its business highlights describe continued integration of the acquired Hexagon D&E business.

Source: https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr-ir/2026/cadence-reports-second-quarter-2026-financial-results.html

### Allowed replay

- The displayed management-guide midpoint changes from $5.95 billion to $6.30 billion, a raw total-guide change of `6.30 / 5.95 - 1 = +5.8824%`.
- The view must place an **incomparable-perimeter** warning directly on that delta unless an accepted owner supplies a same-perimeter bridge.

### Required refusal

- The system must refuse to label +5.8824% an **organic guidance revision** from these two sources alone.
- It must not attribute the increase to AI/EDA demand alone because acquisition perimeter changed.
- It must not synthesize an acquired-business revenue contribution that the cited management outlook does not supply.

This is a discriminating acceptance case: refusing a superficially easy calculation is a feature, not missing intelligence.

## 7. Replay PT05 — IP / Arm, with metric-definition change

### Cut A and Cut B scope

Arm's Q1 FYE27 filing reports total revenue of **$1.289 billion**, including **$715 million of royalty revenue** and **$574 million of license and other revenue**. It describes annualized contract value (ACV) of $1.732 billion as committed licensing fees **excluding potential future royalties** and explicitly states ACV is not recognized GAAP revenue. The filing also says that beginning with Q1 FYE27, Arm stopped reporting certain remaining-performance-obligation and license-count metrics because they had become less relevant as the business expanded into production silicon.

Source: https://investors.arm.com/node/8356/html

The same research record preserves prior Q1 management revenue guidance of **$1.26 billion ±$50 million** and Q2 management guidance of **$1.38 billion ±$50 million**.

### Allowed replay

- Q1 actual versus prior management guide point: `1.289 / 1.26 - 1 = +2.3016%`.
- Show royalty and license/other revenue separately because their recognition clocks differ.
- Preserve ACV as an operating metric with its definition version.
- Mark discontinued KPI families as **definition/reporting change**, not zero.

### Forbidden replay

- Do not add ACV to revenue.
- Do not treat an estimated royalty accrual and later licensee reporting adjustment as two independent units of economic activity.
- Do not extend a retired KPI series with zeros after the issuer stops reporting it.

## 8. Replay PT06 — Analog/power / onsemi

### Cut A: Q1 2026 results

Onsemi guides Q2 revenue to **$1.535–1.635 billion**, with explicit GAAP/non-GAAP margin, EPS and diluted-share assumptions.

Source: https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-first-quarter-2026-results

### Cut B: Q2 2026 results

Onsemi reports Q2 revenue of **$1.6035 billion** and guides Q3 revenue to **$1.650–1.750 billion**. Its segment table shows sequentially different outcomes: Power Solutions +13%, Analog and Mixed-Signal +1%, Intelligent Sensing −3%.

Source: https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-second-quarter-2026-results

### Allowed replay

- Prior Q2 midpoint: $1.585 billion.
- Q2 actual versus management midpoint: `1.6035 / 1.585 - 1 = +1.1672%`.
- New Q3 midpoint: $1.700 billion.
- Display the segment divergence beside the company-level improvement.

### Forbidden replay

- Do not label the company-wide change a uniform power/AI/auto recovery when segments differ.
- Do not discard diluted-share assumptions when later moving from company earnings to per-share economics.
- Do not call Q2 above management midpoint an external-consensus beat.

## 9. What these six replays prove—and what they do not

They demonstrate that the **management-guidance-only** first vertical is useful without fabricating a consensus data plane. The same interaction grammar works across foundry, fabless, equipment, EDA/IP and analog/power while still producing different outcomes: valid comparison, assumption-preserving comparison, driver decomposition, or explicit refusal.

They do **not** prove historical Street consensus coverage, causal market incorporation, stock-price forecasting, security-level valuation correctness or production UI behavior. Those remain with their native owners and evidence gates.

The first product vertical should therefore expose four expectation states independently:

1. prior management outlook;
2. actual result;
3. new management outlook;
4. external consensus / house expectation / incorporation evidence **only when a native owner supplies an admissible object**.

When item 4 is unavailable, the correct product state is visible unavailability—not an empty-looking panel that encourages an inferred zero and not a locally scraped substitute.

## 10. Future acceptance cases added by this replay

All remain **NOT_EXECUTED_PRODUCT_SPECIFICATIONS**.

- **PIT-01** A historical Cut-A view cannot expose any Cut-B actual or new guide.
- **PIT-02** Guide-to-actual deltas are labeled management-guide comparisons, never consensus surprises by default.
- **PIT-03** Guide assumptions such as NVIDIA's China exclusion survive comparison and display.
- **PIT-04** TSMC revenue and margin transitions remain separate observations.
- **PIT-05** ASML installed-base attribution is not rewritten as new-system shipment growth.
- **PIT-06** Cadence perimeter change refuses an organic-guide-delta label without a bridge.
- **PIT-07** Arm ACV remains separate from recognized revenue and royalties.
- **PIT-08** Retired issuer KPIs become definition changes/coverage gaps, not zeroes.
- **PIT-09** Onsemi company improvement preserves segment divergence.
- **PIT-10** External consensus remains typed unavailable/unlicensed when the native owner has no admissible PIT object.
- **PIT-11** A current estimate snapshot cannot be backfilled to an earlier research cutoff.
- **PIT-12** Price reaction remains un-attributed when the accepted point-in-time price/corporate-action basis is insufficient.
- **PIT-13** An accepted future consensus object retains provider, contributor/universe, effective/observed clocks and rights state.
- **PIT-14** A management midpoint derived from a range is labeled derived.
- **PIT-15** Acquisition, divestiture and reporting-definition changes can make otherwise identical metric names incomparable.
- **PIT-16** Same-quarter values with different GAAP/non-GAAP bases do not silently compare.
- **PIT-17** Publication time, event/effective time and system observation time remain distinct.
- **PIT-18** The shared Semiconductor UI consumes existing evidence/financial/expectation/market owners; it never writes a parallel expectation or market-belief truth store.

## 11. Exact next research/design frontier

The owner map and bounded replay remove two major uncertainties: we know the first expectation slice can be management-guidance-led, and we know which desired data must remain unavailable until native owners mature.

The next principal steps are:

1. integrate this replay and the business-model dossier into the same research carrier;
2. perform an adversarial consistency pass against the prior four installments so the ontology, capacity states, economic mechanisms and expectation states use one vocabulary;
3. resolve only competitor gaps that could change that vocabulary or first product slice;
4. draft the **Semiconductor native-owner written design specification** around one complete source-to-user journey: industrial evidence + company/business role + prior management outlook + actual + new outlook + limitations/refusals, composed through existing GMI/Earnings/FIF/K1/F04 ownership;
5. stop before implementation until the Chairman reviews that written specification, following the project design gate;
6. after written-spec acceptance, write the implementation plan and then prepare the mature Fable CEO orchestration packet.

Fable remains uncommissioned. No implementation or production acceptance is claimed.

`MISSION_COMPLETE: false`.