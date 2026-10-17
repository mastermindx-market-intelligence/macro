# Commission 3 — Hardened Audit: Company KPI & Fundamental Driver Models

**Research date:** 2026-10-04  
**Status:** RESEARCH_ONLY / HARDENED_REPORT / NO_IMPLEMENTATION_AUTHORITY  
**Commission type:** Research / architecture only  
**Production effects:** None  
**Protected Mastermind source-law pin:** `mastermindx-market-intelligence/Mastermind@84df29801d4078724c2b603a136de5aa1532cdfe`  
**Macro estate pin:** `mastermindx-market-intelligence/macro@f9ed175800257b228166dabe8b3ac9a55e74e237`

This report hardens the earlier Commission 3 research. It is deliberately placed under the existing
`research/economic_propagation/` research lane because the current estate already warns against
minting a fourth graph or a duplicate company-economic truth plane. It does not charter a new program,
change Financial Intelligence Fabric (FIF) authority, start FIF-3A4 implementation, modify trading or
portfolio behavior, procure data, or promote any model.

---

# A. Executive conclusion

Mastermind should build deterministic company operating models, but **not as a new standalone
"driver-model platform."** The earlier report was directionally right about the destination and
materially wrong about how much relevant architecture already exists.

The strongest architecture is an extension of the existing **Macro Financial Intelligence Fabric
(FIF)** and **Single-Name Intelligence OS**, with Earnings Intelligence supplying
event/guidance/KPI evidence and Mastermind consuming the resulting receipt-bearing
company-fundamental deltas. FIF already contains a governed 50-metric registry, a deterministic
bitemporal query kernel, explicit `AS_REPORTED`, `LATEST_KNOWN_AS_OF`, and
`LATEST_RESTATED` policies, source/provenance machinery, and a
`financial_intelligence_packet.v1` implementation. The current Single-Name Intelligence design
explicitly calls for issuer twins containing segments, KPIs, business drivers, expectations,
scenarios, and forecast records while forbidding a second truth plane.

The missing layer is narrower and more valuable:

> **A versioned operating-model graph that connects point-in-time observations to company-specific
> economic equations and then to future financial-statement deltas.**

The canonical path should be:

**source observation → normalized KPI/driver observation → company/sector economic equation graph
→ forward financial distribution → expectation comparison → evidence packet**

with **market price reaction remaining separate**.

This matters because disaggregation is not automatically valuable. Academic evidence shows that
component-level forecasting can improve profitability forecasts in some settings, but simply
decomposing statements does not guarantee better forecasts; the benefit depends on the decomposition
and forecasting method. Fairfield and Yohn likewise found that some *changes* in DuPont components
carry incremental forecasting information even when levels do not.

Primary academic reference:
- Esplin et al., profitability forecasting and disaggregation:
  https://ideas.repec.org/a/spr/reaccs/v19y2014i1d10.1007_s11142-013-9256-5.html

The hardened recommendation is therefore **P0 research-to-pilot priority, not P0 broad deployment**.
Build only the smallest extension needed to prove that driver models add point-in-time,
out-of-sample information beyond existing Mastermind fundamentals and market expectations. No
driver, company model, vendor, or evidence family should be promoted merely because the model is
economically intuitive.

---

# B. Current-state census

## B1. Verified estate pins

| Estate | Verified current identity | Finding |
|---|---|---|
| Mastermind | `mastermindx-market-intelligence/Mastermind@84df29801d4078724c2b603a136de5aa1532cdfe` | Verified identical to protected `master` at audit time |
| Macro | `mastermindx-market-intelligence/macro@f9ed175800257b228166dabe8b3ac9a55e74e237` | Verified identical to `main` at audit time |
| Terminal | `mastermindx-market-intelligence/mastermind-terminal@9e2f0bd94a2ee876c7dbafacb072414635277a36` | Verified current `master` during the audit |
| Research Vault | **Subsystem of Macro, not a separate Research Vault repository** | `engine/research_vault/`, `app/research.py`, and `research/RESEARCH_VAULT_MASTERPLAN.md` are Macro-owned implementation |
| Executive DR Vault | `mastermindx-market-intelligence/executive-dr-vault@ea422c92bd29800d1f7fb3ae850236cc44d8c890` | Separate Executive OS disaster-recovery repository; must not be confused with Research Vault |

The protected Mastermind bootstrap was read from the same pinned revision, including
`docs/sol_skills/ACTIVE_EXECUTION.md` and `docs/sol_skills/SESSION_RELIABILITY.md`.

A material observability issue remains: `data/census/CENSUS.md` is itself an older generated census
rather than current source truth. It should not establish present capability without direct repository
inspection.

## B2. What actually exists

| Capability | Current evidence | Hardened state |
|---|---|---|
| Mastermind PIT factor/fundamental lane | `loop/fundamentals.py` | **BUILT**, but its source clock needs qualification |
| Earnings-expectation lane | `portfolio/held_risk.py` | **BUILT**: current SUE/PEAD state plus legacy estimate-revision fields |
| Historical mature analyst-revision series | `research/TREND_PERSISTENCE_PROTOCOL.md` and current estate | **GAP / insufficiently mature** |
| Deterministic bitemporal fundamental query engine | Macro `engine/fundamental_forensics/query.py` | **BUILT** |
| Governed normalized fundamental registry | `engine/fundamental_forensics/metric_registry.py` | **BUILT**, 50-metric closed registry |
| Financial intelligence packet | `engine/fundamental_forensics/financial_intelligence_packet.py` | **BUILT**, but important paths remain fixture/research rather than broad production issuer truth |
| Production attested broad issuer PIT service | latest FIF workstream/closeout | **NOT_BUILT** |
| Earnings event/KPI extraction | Earnings Intelligence capability ledger | **PARTIAL** |
| Guidance extraction/history | Earnings Intelligence | **PARTIAL** |
| Segment/KPI historical series | Earnings Intelligence | **PARTIAL** |
| Single-name issuer twin architecture | Single-Name Intelligence OS design | **DESIGNED / not complete implementation** |
| State-conditioned single-name response model | SNI design | **NOT_BUILT** |
| Multi-horizon calibrated single-name forecast book | SNI design | **NOT_BUILT** |
| Defense/company economic driver taxonomy | `research/defense_intelligence/D0R_DEFENSE_EQUITY_DRIVER_TAXONOMY.md` | **SPEC_ONLY**, but directly relevant architecture |
| Economic-propagation graph separation | `research/economic_propagation/D0_THREE_GRAPH_SEPARATION_MAP.md` | **RESEARCH LAW / anti-duplication prior art** |
| Portfolio V3 Decision Snapshot | Mastermind spec + implementation plan | **SPEC/PLAN ONLY** at the audited protected Mastermind revision; expected implementation files were absent |

The earlier statement that Mastermind had **"no existing structured driver-KPI modules" is
withdrawn**. Macro contains substantial adjacent architecture and implementation. In particular,
FIF is already the canonical owner of source, temporal, semantic, query, evidence and financial
packet truth. Single-Name Intelligence explicitly calls for company-specific KPI trees and business
drivers. Defense Intelligence already specifies an effective-dated economic-archetype/driver
hierarchy.

The existing Economic Propagation research is also directly relevant: it says the economic,
semantic/theme, and market co-movement graphs must not be flattened into one opaque edge, and it
warns against creating a new graph store. Commission 3 should consume that separation rather than
creating another relationship authority.

## B3. The most important PIT correction

Mastermind's current `loop/fundamentals.py` reads Macro's `fundamentals_panel.parquet` and
correctly filters on `asof_date`. But the Macro producer currently constructs that field for this
panel using a **fixed 120-day lag from `period_end`**, rather than the actual filing
acceptance/publication timestamp.

Macro's own temporal standard correctly identifies this as a conservative proxy rather than genuine
historical knowledge time. Other Macro tables have better filing clocks, and FIF's deeper query
machinery is substantially stronger.

Therefore:

> **Mastermind has PIT-aware fundamental infrastructure, but the commonly consumed
> `fundamentals_panel` is not itself sufficient proof of true filing-level PIT knowledge.**

This is a critical distinction. The SEC's APIs expose submissions history and extracted XBRL data,
while the filing package and acceptance clock remain the appropriate source for reconstructing what
was knowable. SEC `frames`, for example, selects a last-filed fact aligned to a calendar frame; it
is not a historical knowledge-state service.

Primary source:
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

The correct implementation owner is therefore FIF's bitemporal/source-occurrence plane—not another
`asof_date` table.

---

# C. State-of-the-art research

## C1. Economic decomposition is useful, but only when it survives forecasting tests

Driver-based modeling has a sound economic rationale: quantities, prices, customer counts,
utilization, retention, backlog, capacity, funding costs and similar variables often sit upstream of
accounting outcomes.

But the research does **not** support a blanket rule that more disaggregation is better. Esplin et
al. find that operating/financing disaggregation improves profitability forecasting only under
particular component-forecasting structures; Fairfield and Yohn find incremental information in
changes in turnover/margin components rather than the raw decomposition itself.

This implies a design law:

> **Economic intelligibility is an admission condition, not evidence of predictive value.**

Every extra driver must earn its place out of sample.

## C2. The sector models really are different

Primary issuer evidence strongly supports sector-specific mechanics.

**Semiconductors.** Micron explicitly decomposes memory revenue changes into **bit shipments, ASP and
mix**, and explains gross-margin changes through ASP, mix and manufacturing-cost changes. TSMC
reports wafer shipments, capacity, technology mix and customer/product breadth.

- Micron filing: https://www.sec.gov/Archives/edgar/data/723125/000072312525000028/mu-20250828.htm
- TSMC annual report: https://investor.tsmc.com/static/annualReports/2025/english/index.html

**Software/SaaS.** Snowflake shows why a generic "SaaS seats × ARPU" model is insufficient: its
product revenue is consumption-based, RPO conversion depends on future consumption, and its reported
net revenue retention has cohort-specific definitions and retrospective adjustments.

- Snowflake filing: https://www.sec.gov/Archives/edgar/data/1640147/000164014726000037/snow-20260731.htm

**Hyperscalers/cloud.** Microsoft reports seats, revenue-per-user effects, workload demand, Azure
growth and AI-infrastructure investment; cloud margin is explicitly affected by infrastructure
investment and mix.

- Microsoft filing: https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm

**Industrials.** Caterpillar reports backlog, dealer inventories, price realization, end-user volume
and manufacturing-cost bridges, demonstrating that shipments, channel inventory and price/cost must
remain distinct.

- Caterpillar filing: https://www.sec.gov/Archives/edgar/data/18230/000001823026000008/cat-20251231.htm

**Energy.** Exxon reports production volumes, realized commodity prices and a disclosed earnings
sensitivity to Brent, an example of a management-provided sensitivity that is stronger evidence than
a regression fitted to a handful of annual observations.

- Exxon filing: https://www.sec.gov/Archives/edgar/data/34088/000003408826000045/xom-20251231.htm

**Consumer.** Starbucks reports comparable sales explicitly through transactions and ticket, while
store count and restructuring can alter the economic perimeter.

- Starbucks earnings release filing:
  https://www.sec.gov/Archives/edgar/data/829224/000082922426000078/sbux-03292026xearningsrele.htm

**Financials.** Financial companies require a different ontology again. JPMorgan exposes average
loans/deposits, NII, credit-loss provisions and charge-offs; insurers expose premiums, rate/exposure
growth, loss ratios, catastrophe effects and investment income; asset managers roll AUM through
flows, markets, FX and acquisitions while fee revenue depends on AUM mix and effective fee rates.

- JPMorgan filing: https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm

## C3. XBRL is foundational, not sufficient

SEC XBRL provides concepts, contexts, units, dimensions and filing-linked facts. The SEC's current
XBRL guide emphasizes that meaning comes from the XBRL information model—including taxonomy
relationships and dimensions—not from where a fact appears in a file. FASB separately publishes
taxonomy implementation guidance, and IFRS maintains its own taxonomy architecture.

- SEC XBRL guide:
  https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-02-17.pdf
- FASB taxonomy implementation guides:
  https://fasb.org/projects/fasb-taxonomies/resources/taxonomy-implementation-guides

Therefore the model must not reduce XBRL to `metric_name/value/period`.

It must preserve contexts, dimensions, units, decimals/scaling, filing/accession, taxonomy version,
issuer extensions, presentation/calculation relationships, duplicate occurrences and amendment
lineage.

XBRL also cannot be the sole KPI source. Many of the most decision-relevant operating KPIs are
issuer-defined, non-GAAP, embedded in earnings releases, decks or transcripts, or change definition
over time.

---

# D. Source landscape

**Evidence classification used here:** `P1` = regulator/government/issuer primary source; `P2` =
peer-reviewed/academic; `P3` = official vendor documentation describing its own product; `P4` =
current Mastermind/Macro code or governed internal contract; `P5` = practitioner/secondary
commentary. The hardened recommendation relies primarily on P1–P4.

| Source | Coverage / history | Latency | PIT / correction quality | Delivery | Rights / cost | Best use |
|---|---|---|---|---|---|---|
| SEC filing packages / submissions | U.S. EDGAR; decades | Filing-time | **High if Mastermind archives accession + acceptance + generations** | API/files/bulk | Public; free | Canonical U.S. filing truth |
| SEC Company Facts / Frames | Broad structured XBRL | Fast | Useful acceleration; **not a substitute for filing-package PIT lineage** | REST JSON | Public; free | Discovery/backfill/cross-check |
| SEC Financial Statement & Notes datasets | Structured statement/note information | Periodic bulk | As-filed extraction; archive vintages yourself | Bulk | Public; free | Large-scale filing analysis |
| FASB / IFRS taxonomies | GAAP / IFRS semantic layer | Annual/versioned | Excellent taxonomy/version provenance | Taxonomy packages | Public/reference terms | Concept/relationship normalization |
| Issuer IR / 8-K / 6-K / decks | Company-specific | Event-time | High source authority; definitions may change | Web/filing/vendor | Copyright/reuse varies | KPIs, guidance, non-GAAP, model definitions |
| FRED/ALFRED | U.S. macro series | Release cadence | **Excellent vintage semantics**; ALFRED records release/revision periods | API/download | Free | Macro driver vintages |
| BEA/BLS | National/industry/labor/prices | Release cadence | Explicit revision regimes; historical values can change materially | API/files | Free | Industry demand/cost drivers |
| EIA | Energy production, price, consumption, inventories | Daily–annual | Strong public data; dataset-specific revision diligence still required | API/bulk | Free | Energy/utility/commodity drivers |
| Federal Reserve regulatory reports | Banks/BHCs | Quarterly etc. | Regulatory filing basis | Forms/bulk depending dataset | Public | Bank balance-sheet drivers |
| Calcbench | SEC-derived financial/disclosure analytics | Minutes claimed | Strong candidate; exact PIT/version semantics require contractual diligence | API | Commercial; likely mid/high | Faster normalized filing layer; not canonical until tested |
| Quartr API | Global IR events, calls, transcripts, filings, slides | Live/near-live claimed | Strong source corpus; historical correction/version semantics require diligence | API | Enterprise/contact sales | Transcript/deck/IR acquisition |
| LSEG I/B/E/S | Global estimates, actuals, guidance, industry KPIs | Continuous | **Strong documented PIT metadata:** announcement/effective/activation dates; long estimate history | API/cloud/bulk/Snowflake | Enterprise/high | Consensus, revisions, guidance, expectation state |
| FactSet Estimates | Global analyst estimates | Continuous | Historical consensus/detail snapshots documented; exact replay semantics still diligence item | Feed/API ecosystem | Enterprise/high | Consensus/revision alternative |
| Bloomberg CoFi PIT | Global actuals/estimates/guidance/prices | Daily/ongoing | **Explicit PIT product**, daily snapshots, corporate-action adjustment | Parquet/API/cloud/Data License | Enterprise/high | Integrated PIT upgrade path |
| S&P Capital IQ + Visible Alpha | Global estimates plus deep line-item/KPI consensus | Continuous | Official materials describe point-in-time integrated data; implementation details need diligence | API/Xpressfeed/cloud | Enterprise/high | Deep KPI/segment consensus |

Primary/official source links:
- SEC market datasets: https://www.sec.gov/data-research/sec-markets-data
- ALFRED real-time periods: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
- EIA Open Data: https://www.eia.gov/opendata/documentation.php
- Federal Reserve FR Y-9C:
  https://www.federalreserve.gov/apps/reportingforms/Report/Index/FR_Y-9C
- Calcbench API: https://www.calcbench.com/api
- Quartr API: https://quartr.com/pricing/api-q4-2025
- LSEG I/B/E/S:
  https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/actuals
- FactSet consensus estimates:
  https://insight.factset.com/resources/factset-consensus-estimates-datafeed
- Bloomberg CoFi PIT:
  https://professional.bloomberg.com/products/data/enterprise-catalog/cofi/
- S&P estimates:
  https://www.spglobal.com/market-intelligence/en/solutions/products/estimates

The public/open baseline should therefore be **SEC filing packages + issuer IR + existing FIF +
ALFRED/official sector datasets**.

The commercial upgrade decision should be made only after a bake-off on actual Mastermind questions.
LSEG is particularly attractive for expectation history because its official documentation exposes
activation/effective/announcement semantics and long history. Bloomberg now has an explicitly
marketed PIT company-financials/estimates/guidance product, so the previous report's assertion that
Bloomberg was "not inherently PIT" is obsolete and withdrawn.

FactSet's official materials establish historical snapshots but do not, from the public documentation
inspected here, prove every correction/replay semantic Mastermind requires. It should therefore be
classified **promising but diligence-required**, not "not PIT" and not automatically safe.

No purchase recommendation is made.

---

# E. Canonical data model

## E1. Temporal law

The existing FIF two-clock architecture should be extended rather than replaced.

| Field | Meaning |
|---|---|
| `event_time` | When the underlying economic activity occurred; may be an instant or interval |
| `period_start/end` | Accounting/KPI measurement interval |
| `source_published_at` | Timestamp asserted by the source |
| `accepted_at` | Regulator acceptance time when applicable |
| `available_at` | Earliest external time the information was lawfully/technically available |
| `observed_at` | First time Mastermind's acquisition plane actually observed it |
| `ingested_at` | Source bytes durably entered Mastermind |
| `known_at` | Earliest time the normalized, validated observation became eligible for canonical queries |
| `as_of` | Query cutoff; **not** a substitute for any of the above |
| `effective_from/to` | Validity interval for definitions, segments, equations, identities or rules |
| `correction_generation` | Monotonic generation within a logical source lineage |
| `rule_available_at` | Earliest historical date a normalization/model rule is permitted in genuine replay |

`known_at` should normally be no earlier than the maximum of applicable external availability,
actual acquisition, required normalization/validation completion, and rule availability.

A later restatement never rewrites an earlier knowledge state.

That is consistent with ALFRED's explicit distinction between observation date and the real-time
period during which a vintage was known.

## E2. Economic ontology

The general graph should be:

**external driver → operating state → KPI → business node → revenue mechanics → cost mechanics →
operating profit → working capital/capex → financing/tax/share count → EPS/FCF**

but every edge has a type.

Required edge types include:

`IDENTITY`, `ADDITIVE`, `MULTIPLICATIVE`, `ROLL_FORWARD`, `RATE_X_BASE`,
`LAGGED_TRANSFER`, `CAPACITY_CONSTRAINT`, `PIECEWISE`, `COHORT`, `WATERFALL`,
`ACCOUNTING_IDENTITY`, `ESTIMATED_SENSITIVITY`, `MANAGEMENT_SENSITIVITY`, and
`SCENARIO_ASSUMPTION`.

This is superior to storing a generic "elasticity" on every edge.

The equation graph is an **issuer operating model**, not the Graph 1 economic-relationship store from
Economic Propagation. Firm-to-firm relationships remain with their existing owners. Where a model
depends on a supplier/customer relationship, it should reference the canonical relationship receipt,
not remint the edge.

## E3. Minimum useful contracts

| Contract | Purpose |
|---|---|
| `economic_node_definition.v1` | Stable driver/KPI/segment/product/customer/channel/account identity, unit and stock/flow semantics |
| `metric_definition_version.v1` | Issuer-specific KPI definition, scope, formula, source span and effective interval |
| `economic_observation.v1` | PIT observation with full clock and source lineage |
| `business_hierarchy.v1` | Effective-dated segment/product/geo/customer/channel structure and eliminations |
| `economic_equation.v1` | Deterministic equation graph and dimensional constraints |
| `model_parameter.v1` | Estimated/stated/physical coefficients with evidence class and validity |
| `model_version.v1` | Complete frozen company/sector graph and rule dependencies |
| `scenario_input.v1` | Explicit hypothetical shock, never confused with observed fact |
| `financial_forecast_distribution.v1` | Output distribution by line item/horizon/model version |
| `expectation_snapshot.v1` | Consensus/guidance/prior-internal expectation with basis and PIT clocks |
| `fundamental_delta_packet.v1` | Observation → affected nodes → financial delta → uncertainty → receipts |
| `model_evaluation.v1` | Prospective/walk-forward performance, calibration and promotion state |

These are **research recommendations**, not accepted contract names. A follow-on implementation owner
must reconcile them against existing FIF/Earnings/SNI schemas before minting any new contract.

Every equation must pass dimensional analysis. A formula that adds "customers" to "dollars," mixes
quarterly flow with point-in-time stock, or multiplies incompatible units should fail closed.

## E4. Definition drift

KPI identity must be versioned separately from the displayed name.

`Net Revenue Retention` from one issuer is not automatically equivalent to another issuer's NRR,
and even one issuer may change cohort, currency, acquisition or consolidation treatment.

Snowflake explicitly describes adjustments to customer counts and NRR for acquisitions,
consolidations and other activity, demonstrating why a historical KPI series cannot be identified
solely by a text label.

---

# F. Derived intelligence

## F1. Sector blueprint matrix

| Sector | Minimum viable economic model | Important constraints / lags | Typical failure |
|---|---|---|---|
| Semiconductors | `units/bits × ASP × mix`; wafer starts → yield → good die → shipments; utilization/capacity → cost/bit; inventory/channel roll-forward | Fab/packaging lead times, node transitions, capacity commitments, inventory NRV | Treating revenue as pure units×price while ignoring yield, mix, inventory and product transitions |
| Software/SaaS | Beginning cohort + new logos/seats + expansion − churn → customers/ARR/consumption; bookings/RPO → revenue-recognition schedule | Contract duration, consumption behavior, renewals, implementation, acquisition adjustments | Treating RPO as guaranteed next-quarter revenue or assuming all SaaS is seat-based |
| Hyperscalers/cloud | Workload/consumption × effective price; capacity/utilization; infrastructure capex → installed compute → depreciation/power; service mix → margin | Multi-year data-center construction, power/accelerator constraints, depreciation lives | Assuming capex immediately produces revenue or ignoring price/performance improvements |
| Industrials | Orders → backlog → cancellations → shipments; units × price/mix; utilization → absorption; price-cost bridge; inventory/WC | Backlog conversion, dealer/channel inventory, supplier lead time | Treating backlog as funded/firm revenue or ignoring channel inventory |
| Energy | Production volume × realized price ± hedge/differential; decline/ramp; lifting/transport costs; capex → future production | Project lead time, outages, decline curves, PSC effects, hedges | Using spot commodity price as realized price or ignoring production-sharing mechanics |
| Consumer | Stores/doors × traffic × conversion × ticket/AOV; mix/promotions; labor/occupancy; inventory/markdown | Store openings, seasonality, promotion timing, channel shift | Equating comparable sales with total revenue or ignoring perimeter/store-count changes |
| Banks | Interest-earning assets × yields − funding base × cost; deposit beta/mix; loan growth; provision/charge-off/allowance; capital | Repricing gaps, deposit migration, credit vintages, regulatory capital | Treating NIM as a primitive rather than an outcome of asset/liability structure |
| Insurers | Exposure × rate × retention/new business → premiums; earned pattern; frequency × severity → losses; reserves; investment assets × yield | Reserve development, catastrophe timing, earning lag | Treating written premium growth as current-period underwriting profit |
| Asset managers | Beginning AUM + flows + market + FX + acquisitions − realizations → ending AUM; average AUM × effective fee rate; performance fees | Market beta, product mix, realization timing | Applying one fee rate to all AUM or confusing market appreciation with organic growth |

The general ontology therefore survives across sectors only if it supports **stock/flow distinctions,
roll-forwards, lags, capacity, nonlinear constraints and sector-specific accounting**.

## F2. Model depth policy

Coverage should not be governed by one opaque score. Maintain visible dimensions:

| Dimension | Question |
|---|---|
| Decision relevance | Does the name materially affect current/future Mastermind decisions? |
| Disclosure richness | Are the economically important KPIs disclosed consistently? |
| PIT history | Can definitions and observations be reconstructed historically without leakage? |
| External observability | Can meaningful drivers be observed between reports? |
| Business stability | Is the operating mechanism stable enough to estimate? |
| Segment complexity | Can material segments be modeled without false precision? |
| Incremental value | Does the model beat simpler baselines? |
| Maintenance burden | Can definition/model drift be monitored economically? |

**Hand-curated** models should be reserved for strategically important names where unique
company-specific mechanics have demonstrated incremental value.

**Sector-template + overrides** should be the default scalable tier.

**Template-only** is appropriate when economic structure is stable but company-specific detail does
not earn its maintenance cost.

**No model / defer** is the correct state when PIT history, definitions, observability or predictive
uplift are inadequate.

Escalation requires evidence; coverage breadth is not itself success.

## F3. LLM boundary

LLMs should produce **candidates and explanations**, never temporal or arithmetic truth.

Cheap models are appropriate for known-document classification, candidate KPI aliasing, table/section
routing, speaker/topic tagging and extracting already well-defined values with exact source spans.

Frontier models are justified for ambiguous definition changes, complex segment/KPI mapping,
management-Q&A causal claims, proposed company-specific equation overrides and reconciliation of
contradictory narrative evidence.

Neither may:

- finalize a numeric fact without deterministic validation;
- decide `known_at`;
- silently convert units;
- repair an accounting identity;
- choose between conflicting source generations;
- invent missing values;
- promote a causal coefficient;
- modify a company equation graph without a versioned review path.

The deterministic validator should verify exact source span, numeric token, sign, scale,
currency/unit, period/context, entity/segment scope, duplicate status, equation consistency and source
generation before admission.

---

# G. Mastermind integration map

The hardened ownership map is:

| Producer | Canonical owner | Output | Evidence family / consumer |
|---|---|---|---|
| SEC / issuer / licensed financial source | **Macro FIF** | Source documents, facts, statement cells, normalized metrics | Fundamentals / SNI / Mastermind |
| Earnings releases / transcripts / decks | **Earnings Intelligence + FIF shared event/source contracts** | KPI/guidance candidates, definitions, claims, receipts | Earnings / company-model inputs |
| Official macro/industry/physical sources | Existing Macro source/data owners | PIT external-driver observations | Operating-driver evidence |
| Firm-to-firm economic relationships | Existing graph/relationship owners under Economic Propagation separation law | Relationship receipts | Referenced by company models; never reminted |
| Company-model extension | **FIF/SNI economic-model layer candidate** | Equation graph, parameters, forecast distributions, fundamental-delta packets | Single-name research |
| Consensus / estimates | Existing expectation owner / licensed estimate lane | `expectation_snapshot` | Earnings expectation |
| Price/options/positioning | Existing market/options owners | Incorporation/positioning evidence | Separate evidence families |
| Mastermind | Existing `loop` / research / later Decision Snapshot consumers | Bounded receipt-bearing company-fundamental evidence | Decision intelligence |

The new layer must **not** own identity, filing storage, transcript storage, market data, estimates,
qledger/evaluation, portfolio mutation, graph relationship truth or Decision Snapshots.

The SNI architecture already states the correct principle: it is a compiler/research layer over
existing owners rather than a replacement truth plane.

---

# H. Empirical validation program

## H1. Forecast design

Every evaluation should be rolling-origin/walk-forward and use the actual knowledge state available
at each historical cutoff.

Test at least:

- next-quarter revenue/margin/EPS/FCF;
- next fiscal year;
- NTM where accounting-period mapping is safe;
- multi-year outputs only for sectors where the physical economics justify them.

Baselines should include:

1. seasonal naïve / last-year-same-quarter;
2. simple trend;
3. existing Mastermind fundamentals;
4. prior internal forecast;
5. consensus when licensed and PIT-safe;
6. sector-template model;
7. company-specific model.

The relevant question is not "is the model statistically significant?" but:

> **Does the driver layer improve genuinely out-of-sample forecasts relative to the information
> Mastermind already possessed?**

Academic forecast-comparison methods such as Diebold-Mariano and Giacomini-White are appropriate for
formal relative-accuracy testing, with the latter explicitly accommodating model misspecification and
conditional predictive ability.

Reference:
- Diebold-Mariano test:
  https://www.tandfonline.com/doi/abs/10.1080/07350015.1995.10524599

## H2. Leakage suite

A serious validation harness must intentionally attempt to break PIT integrity through:

- 10-K/10-Q amendments;
- later comparative recasts;
- taxonomy changes;
- KPI definition drift;
- later issuer segment reorganizations;
- M&A/recast history;
- discontinued operations;
- late or corrected source ingestion;
- macro-data revisions;
- estimate backfills;
- corporate actions;
- transcript corrections;
- revised seasonal adjustments.

Macro data need the same discipline as company data. ALFRED explicitly preserves release/revision
vintages.

- ALFRED API documentation: https://fred.stlouisfed.org/docs/api/fred/alfred.html

## H3. Metrics

Point forecasts should use scale-appropriate MAE/RMSE and scaled errors such as MASE; MAPE should be
avoided when denominators approach zero or change sign.

Probabilistic forecasts should evaluate calibration, interval coverage, CRPS and—where
suitable—log score. Proper scoring rules are specifically designed to reward honest probabilistic
forecasts rather than overconfident intervals.

Reference:
- Gneiting & Raftery, proper scoring rules:
  https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf

Also track bias, sign/directional accuracy, residual autocorrelation, sector/company stability and
error conditional on regime.

Only after fundamental forecast uplift is established should Mastermind test:

`forecast delta → subsequent expectation change → subsequent price information`

and eventually incremental portfolio utility after realistic costs.

## H4. Multiple testing

Driver discovery creates a severe data-mining problem. A program testing hundreds of KPIs, lags,
sectors and horizons will generate apparently successful relationships by chance.

False-discovery control should therefore be explicit; Benjamini-Hochberg provides the canonical FDR
framework.

Reference:
- Benjamini-Hochberg:
  https://rss.onlinelibrary.wiley.com/doi/pdf/10.1111/j.2517-6161.1995.tb02031.x

Pre-registration, frozen model versions, company holdouts, sector holdouts and untouched final
evaluation windows are preferable to repeatedly optimizing the same backtest.

---

# I. Elasticity, causality and uncertainty

## I1. Elasticity evidence hierarchy

Do not store one undifferentiated `elasticity` number.

| Class | Evidence | Allowed interpretation |
|---|---|---|
| A | Accounting identity / deterministic engineering relation | Deterministic coefficient within stated domain |
| B | Contractual or management-disclosed sensitivity with primary evidence | Stated sensitivity; still scenario-dependent |
| C | Credible quasi-experimental / IV / natural-experiment estimate | Causal within explicit identification assumptions |
| D | Stable out-of-sample reduced-form estimate | Predictive association, **not causal** |
| E | Hierarchical/peer prior or analyst judgment | Prior/scenario assumption only |
| F | LLM-suggested relationship | Hypothesis only; no numeric authority |

Confidence should remain multidimensional: **identification quality, measurement quality, stability,
sample support, transportability and definition stability**.

A single five-year regression is not an acceptable default.

Candidate statistical families include distributed lags, partial pooling/hierarchical Bayes,
regularized panel models, state-space/time-varying parameter models and explicit structural-break
tests. Dynamic linear models are designed for learning and forecasting in changing environments,
while Bai-Perron methods provide formal machinery for multiple structural breaks.

Endogeneity must be explicit. Price and volume, customer growth and marketing, utilization and
margins, or capex and demand are often jointly determined. A high historical correlation does not
turn one into a causal driver.

## I2. Parameter expiry

Deterministic identities expire when their definition/economic perimeter changes.

Management sensitivities expire on supersession, material business-mix change or explicit withdrawal.

Statistical coefficients should be recalibrated on a predefined cadence but also invalidated by
structural breaks, KPI-definition changes, major M&A, segment recasts or sustained calibration
failure.

No historical replay may apply a model rule before `rule_available_at` unless explicitly labeled
retrospective research.

## I3. Uncertainty architecture

Keep five uncertainty sources separate:

`observation error`, `parameter uncertainty`, `model-form uncertainty`,
`scenario uncertainty`, and `source/definition uncertainty`.

Use analytic propagation for simple linear identities when valid.

Use Monte Carlo for nonlinear graphs, capacity constraints and correlated driver distributions.

Use bootstrap or Bayesian posterior distributions for estimated parameters.

Use discrete stress scenarios for genuine structural states that cannot honestly be assigned precise
probabilities.

Do **not** sample all drivers independently. Price, volume, mix, utilization, commodity prices, rates,
FX and macro demand often co-move.

The result should be a distribution for each financial target:

`revenue`, `gross_profit`, `operating_income`, `working_capital`, `FCF`, `net_income`,
`diluted_EPS`, and relevant balance-sheet states.

That distribution is **not a stock-price distribution**.

---

# J. Expectations and "already priced"

The first report did not separate these layers strongly enough.

The canonical chain should be:

**Observation Delta**  
→ **Operating Impact**  
→ **Forward Fundamental Delta**  
→ **Expectation Gap**  
→ **Market Incorporation Evidence**

Suppose a driver observation changes.

The operating engine first answers:

> Given model version M and evidence known at T, what changes in future company financials?

Only then should the expectation layer ask:

> How different is that new forecast from the prior internal forecast, management guidance and PIT
> consensus?

Only after that should the market layer ask:

> What price/options/positioning reaction has already occurred relative to comparable historical
> information shocks?

Guidance is therefore an **expectation/constraint object**, not operating truth.

Consensus is a **market-expectation object**, not an operating fact.

Price reaction is an **incorporation observation**, not proof that the fundamental interpretation is
correct.

This separation is essential to prevent double counting. If analyst revisions were used to infer the
fundamental forecast, they cannot then be presented as independent confirmation of that same forecast
without explicitly modeling the dependence.

It also matches the existing Economic Propagation three-graph law: economic relationships, semantic
similarity/theme membership, and market co-movement must remain inspectable and must not be collapsed
into one causal edge or score.

---

# K. Risks, kill criteria and promotion gates

## K1. Major failure modes

The largest risks are not arithmetic errors. They are semantic and epistemic:

**Definition drift:** issuer KPIs retain the same name but change construction.

**Disclosure-selection bias:** companies disclose favorable or strategically useful KPIs and stop
reporting them when relevance changes.

**Conglomerate failure:** one sector template is applied to economically unrelated segments.

**M&A/recast contamination:** current segment history is projected backwards.

**Expectation leakage:** later consensus or guidance state enters historical models.

**Restatement leakage:** final accounting values replace values known at decision time.

**Relationship leakage:** a theme tag, co-movement, ownership link or disclosed agreement is promoted
into a customer/supplier causal edge without canonical relationship evidence.

**Correlation laundering:** multiple representations of the same underlying demand shock appear as
independent evidence.

**Model-form certainty:** a precise equation hides a weak economic assumption.

**Vendor lock-in:** a proprietary KPI taxonomy becomes Mastermind's semantic truth.

**LLM authority creep:** extracted narrative silently becomes numeric/model authority.

## K2. Kill criteria

A candidate driver should be rejected when it lacks a coherent mechanism, fails PIT reconstruction,
is definition-unstable without recoverable versions, or fails incremental walk-forward performance
after existing evidence is controlled.

A company should remain template-only when bespoke overrides do not demonstrate meaningful
incremental forecast or decision value.

An LLM extraction must require review when the KPI is new, definition-changed, custom/nonstandard,
period-ambiguous, unit-ambiguous, conflicts with another source, changes an equation graph, or fails
deterministic reconciliation.

A vendor should not be purchased when it cannot demonstrate the required historical vintages,
correction lineage, identifiers, entitlement/usage rights and sample Mastermind replay cases before
contract.

An evidence family should not reach Decision Snapshots until it demonstrates incremental information
after correlated existing families are controlled.

A company model should be downgraded or retired after sustained OOS deterioration, repeated
structural breaks, unrecoverable KPI definition loss or maintenance cost exceeding demonstrated
decision value.

---

# L. Build priority and bounded implementation handoff

## L1. Priority

| Priority | Recommendation |
|---|---|
| **P0** | Reconcile existing FIF/Earnings/SNI/Economic Propagation contracts; add only the minimum KPI-definition/economic-node/equation/model-version/fundamental-delta semantics that are genuinely absent; repair true PIT input path for pilot data; run a small cross-sector pilot |
| **P1** | Sector-template library, validated KPI extraction, expectation interface, probabilistic uncertainty and elasticity registry |
| **P2** | Broader company coverage, additional official/alternative driver feeds, advanced hierarchical/time-varying sensitivities |
| **Defer** | Broad alternative-data procurement, mass hand-curation, price/valuation integration |
| **Reject** | New parallel fundamental database, new relationship graph, LLM-owned arithmetic, single opaque company score, backtests using current-restated history, unvalidated "causal" elasticities |

## L2. Proposed implementation phases

**Phase 0 — contract convergence.** Reuse FIF's existing temporal/source/query/evidence contracts and
the Economic Propagation three-graph separation. Freeze the smallest additions needed for KPI
identity, economic nodes, equations, model versions and fundamental deltas. No new source plane and no
new firm-relationship graph.

**Phase 1 — three-organism pilot.** Select three economically different companies with strong
primary disclosure—for example one memory/semiconductor model, one consumption/SaaS model and one
industrial/backlog model. Reconstruct PIT history first; do not start with current-only data.

**Phase 2 — deterministic equation engine.** Prove dimensional consistency, stock/flow handling,
lags, capacity constraints, versioning and full provenance. LLM extraction remains outside the
arithmetic core.

**Phase 3 — empirical admission.** Run frozen walk-forward comparisons against naïve, existing
Mastermind and expectation baselines. Do not expand coverage until at least one pilot demonstrates
incremental value.

**Phase 4 — expectation interface.** Join PIT consensus/guidance without making either operating
truth. Produce explicit `fundamental_delta` versus `expectation_delta`.

**Phase 5 — controlled expansion.** Add sector templates only after the pilot proves the architecture
and evaluation protocol.

## L3. Exact bounded follow-on implementation commission

**Mission:** Implement a research-only P0 company-economic-model pilot by extending the existing
Macro Financial Intelligence Fabric and Single-Name Intelligence architecture while preserving the
existing Economic Propagation graph-separation law.

**Allowed scope:** reconcile existing schemas first; add only the minimum versioned contracts that are
actually absent for KPI definitions, economic nodes, equation graphs, parameters, model versions and
fundamental-delta packets; build fixture/PIT-replay tests; populate exactly three approved pilot
issuers from already lawful sources; implement deterministic calculations and validation; register
prospective evaluation outputs with the existing evaluation owner.

**Forbidden scope:** no portfolio/trading authority; no Decision Snapshot promotion; no new truth
database; no new relationship graph; no vendor purchase; no scraping of unlicensed
research/transcripts; no broad-universe rollout; no valuation/price-target engine; no LLM arithmetic;
no automatic company-model generation; no replacement of FIF, Earnings Intelligence, identity,
qledger, estimates, market-data or graph owners; no FIF-3A4 implementation unless separately
commissioned under its accepted architecture.

**DONE_WHEN:** each pilot can accept a versioned statement equivalent to **"Observation X changed by
Y at known time T"** and deterministically return affected future financial line items, approximate
magnitude/distribution, model version, equation path, uncertainty decomposition and complete evidence
lineage; historical replay proves no later corrections or definitions leaked backwards; and the
walk-forward evaluation package can determine whether the driver model adds information beyond
existing Mastermind baselines.

Implementation should stop there for independent review before any production-source expansion or
decision authority.

---

# Adversarial review

The weakest assumption is that detailed operating models will necessarily outperform simpler
financial forecasts. The academic literature itself warns against that conclusion. Complexity is
justified only where decomposition carries stable incremental information.

The second major risk is historical availability. Current Mastermind fundamentals contain PIT-aware
logic but at least one important consumed panel uses a fixed reporting-lag proxy. A beautiful
operating model built on that panel could still produce a contaminated backtest.

The third is KPI survivorship. A model built today can easily use today's KPI definitions to
reinterpret history. That is leakage even when every numeric observation came from an old filing.

The fourth is evidence correlation. Orders, backlog, management guidance, analyst revisions, supplier
activity and price reaction can all encode the same demand shock. The system should expose these as
separate observations but estimate incremental information before treating them as independent
evidence.

The fifth is graph collapse. Existing Economic Propagation research already documents the failure
mode where theme membership, disclosed agreements, residual sympathy or ownership are mislabeled as
customer/supplier economic transfer. Company operating models must reference canonical relationship
receipts and must never infer Graph 1 economic truth from Graph 2/3 evidence.

The sixth is conglomerate and business-model change. Company models require effective-dated economic
structure. A divestiture, AI infrastructure shift, consumption-model evolution or semiconductor node
transition can change the equation graph itself.

The smallest architecture that survives these objections is therefore **not** a massive digital twin.
It is a small, versioned equation graph sitting on FIF's existing temporal/evidence spine, referencing
rather than replacing existing graph owners, with strict typed absence, explicit uncertainty and
prospective evaluation.

---

# Disputed / unresolved findings

The current FIF codebase is materially more mature than the prior report recognized, but the latest
inspected FIF workstream/acceptance record still describes the production attested issuer service as
`NOT_BUILT`. Current code presence therefore must not be equated with broad production PIT truth.

The current `fundamentals_panel` fixed-lag clock is conservative but cannot prove the exact
historical instant when information became available. It may be acceptable for some slow factor
research but should not be the canonical clock for company-event driver models.

The existing Economic Propagation research is not a registered program and explicitly warns against a
new graph store. This report therefore does not claim Economic Propagation ownership of the company
operating-model layer; exact durable ownership must be reconciled against FIF/SNI/Earnings and current
program authority before implementation.

Public vendor documentation establishes substantial capabilities, but licensing, redistribution,
amendment lineage and exact historical replay behavior remain contractual diligence questions. No
vendor has been admitted by this research.

The best number of quarters required for a hand-curated model cannot be fixed globally. A
semiconductor cycle, SaaS cohort model, bank credit book and industrial backlog have different
effective sample sizes and regime structures.

"Causal" should remain reserved for deterministic identities, physical/contractual mechanisms, or
genuinely defensible identification designs. Most historical company elasticities should be labeled
predictive associations.

---

# Corrections to the prior report

| Prior statement | Hardened disposition |
|---|---|
| "No existing structured driver-KPI modules" | **Withdrawn.** Substantial FIF, Earnings Intelligence, SNI and sector-driver architecture exists |
| Current fundamentals effectively provide filing PIT | **Narrowed.** Important `fundamentals_panel` clock is a fixed 120-day proxy; deeper FIF machinery is stronger |
| 13F has "no PIT concern" | **Withdrawn.** Holdings are quarter-end snapshots but public knowledge arrives later; filings can be amended and confidential treatment can delay disclosure |
| Bloomberg/FactSet "not inherently PIT" | **Withdrawn/narrowed.** Bloomberg now explicitly offers PIT company actuals/estimates/guidance; FactSet documents historical estimate snapshots but requires deeper replay diligence |
| Arche as preferred initial PIT service | **Withdrawn pending stronger diligence.** The earlier evidence leaned too heavily on vendor-authored material |
| Generic new canonical tables owned by "data engineering" | **Withdrawn.** Extend FIF and existing canonical owners instead |
| Generic new relationship graph for driver models | **Rejected.** Existing Economic Propagation research requires graph separation and no duplicate graph store |
| "Estimate elasticity from five years" | **Rejected.** Replace with graded identification, shrinkage/dynamic models, break detection and OOS validation |
| Best/base/worst scenarios as uncertainty system | **Rejected as insufficient.** Separate observation, parameter, model, scenario and source uncertainty |
| Automated nightly backtests as default architecture | **Withdrawn.** Evaluation cadence belongs to existing durable owners and should be justified by the consumer capability |
| Broad P0 build across sectors | **Narrowed.** P0 should be a three-organism PIT-correct pilot with promotion gates |
| Research Vault treated as an external repository | **Corrected.** Current Research Vault is a Macro subsystem; `executive-dr-vault` is a different Executive OS DR asset |

---

# Final ruling

The research supports the product thesis but changes the architecture materially.

Mastermind should **not build a new driver-model system from scratch**.

It should extend the Financial Intelligence Fabric with the smallest reconciled economic-model layer
that is:

**point-in-time, effective-dated, equation-based, sector-aware, deterministic where possible,
probabilistic where necessary, provenance-complete, expectation-separated, graph-separation-safe,
correlation-aware, and prospectively evaluated.**

The end-state remains:

> **Observation X changed by Y.**

Mastermind can then answer:

> **Under model version M, using only evidence knowable at T, this changes the distribution of future
> revenue, margin, EPS and FCF by approximately Z through these explicit economic paths, with these
> uncertainties and these source receipts. Relative to the prior internal/market expectation, the
> fundamental surprise is Q. Price incorporation is a separate observation.**

That is substantially closer to an institutional-grade causal-economic model than the architecture
proposed in the first report.
