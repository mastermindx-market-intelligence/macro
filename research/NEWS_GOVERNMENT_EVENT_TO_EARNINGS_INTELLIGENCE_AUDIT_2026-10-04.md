# MastermindX News, Government & Event-to-Earnings Intelligence — Adversarial Audit and Hardened Architecture

**Research snapshot:** 2026-10-04  
**Commission:** Commission 1 — News, Government & Event-to-Earnings Intelligence  
**Status:** RESEARCH / ARCHITECTURE ONLY  
**Implementation performed:** NO  
**Production code changed:** NO  
**Portfolio or trading behavior changed:** NO  
**New data purchased or source authority granted:** NO

This document supersedes the first research draft for Commission 1. It is an adversarial audit, not an implementation authorization. It deliberately separates merged source truth, held/draft carriers, historical production receipts, current runtime proof, and research recommendations.

## A. Executive conclusion

The core thesis survives the audit, but the architecture and priority change materially.

Mastermind should treat event-to-earnings intelligence as **P0 completion work across existing owners**, not as a new P0 system called an Event-to-Expectation Compiler. The first draft was directionally right that the missing value is the conversion of observations into economic mechanisms, operating KPIs, expectation deltas, and market-incorporation evidence. It was too willing, however, to describe that conversion as a new compiler boundary and it understated how much adjacent work already exists.

The current estate now contains or is actively carrying all of the following:

- an issuer event/document/claim owner in Earnings Intelligence OS / Company Event Intelligence;
- qbus, deterministic news-event classification, novelty/corroboration, and qledger evaluation infrastructure;
- Evidence Foundation contracts that intentionally compose owner-native evidence without a shared evidence store;
- a canonical Theme Graph owner with local-theme/subtheme identity and bitemporal membership semantics, although forward PIT completion is unfinished;
- a held Economic Propagation hypothesis contract/compiler in Macro PR #6514 that already defines relationship-gated mechanism hypotheses, typed abstention, exact identity, clock checks, zero scalar authority, and no new store;
- an active Information→Price / K3E Expectation Market Dynamics programme in Macro PRs #8312 and #8337 with a prospective expectation-capture surface and explicit cutoff queries, although normalization, rights, identity, basis, source-publication clocks, long history, and canonical publication remain incomplete;
- Government Revenue, Federal Register, SEC, Research Vault, FIF, and market-data owners that already cover much of the acquisition and evidence substrate.

Therefore the hardened target is:

    owner-native event/source truth
      -> Evidence Foundation composition
      -> exact identity + dependence + temporal eligibility
      -> economic relationship gate
      -> mechanism / KPI hypothesis with typed abstention
      -> deterministic scenario projection with numeric firewall
      -> existing K3E expectation surface / normalized expectation contract
      -> existing market/pricing owners + K3E Information→Price
      -> qledger / existing grading owners
      -> context-only consumers
      -> future Decision Snapshot only after that owner is production-accepted

The **only clearly missing new analytical primitive** is a deterministic, provenance-complete fundamental-scenario projection that turns an accepted mechanism/KPI hypothesis into inspectable low/base/high operating scenarios without allowing a language model to mint numeric authority. Even that should be a derived view owned by the existing Earnings/Company Event programme, not a new global event store or decision plane.

### Audit verdict on priority

**P0 remains justified**, but only for collision-safe completion of existing event, clock, mechanism, expectation, scenario, replay, and evaluation seams. P0 does **not** justify a new program key, a new global event database, a new evidence store, a new grading ledger, a new theme graph, or a new pricing/expectation owner.

The paid-data recommendation is also narrowed. The first draft made a historical PIT estimates bake-off sound like an immediate P0 dependency. Current Macro evidence changes that conclusion: K3E now has a prospective expectation-capture source and an explicit-cutoff consumer under active acceptance. The correct sequence is to finish and qualify the native prospective expectation plane first. A commercial historical PIT estimates feed becomes **P1 / conditional** if the validation programme needs pre-accrual history that cannot be established lawfully from existing data. No purchase is authorized by this report.

### Hardest architectural laws

1. **No duplicate owner.** Earnings Intelligence owns issuer event/document/claim truth. Theme Graph owns theme truth. Government Revenue owns procurement truth. Evidence Foundation composes; it does not store a second copy. qledger / existing grading owners evaluate. K3E owns expectation-to-market dynamics. Portfolio owners retain decision authority.
2. **No event-to-EPS language-model shortcut.** Models may propose mechanisms, KPI mappings, alternatives, missing assumptions, and falsifiers. Deterministic code owns units, accounting basis, fiscal periods, currency, formulas, market reactions, estimate arithmetic, and promotion.
3. **No historical possession claim from a present-day backfill.** Actual-possession replay and source-availability replay are separate modes and must never be conflated.
4. **No independent evidence by article count.** Source-version, document, claim, real-world event, and origin-family identities are distinct.
5. **No alpha claim from architecture evidence.** Academic and vendor evidence can justify building a measurement system; predictive authority requires Mastermind-specific out-of-sample validation after controls, costs, clustering, and multiple-testing correction.

---

## B. Current-state census

### Repository and procedure pins used for this audit

| Estate | Exact audit pin | Role |
|---|---|---|
| Protected Mastermind | **84df29801d4078724c2b603a136de5aa1532cdfe** | bootstrap/source law, portfolio/Brain, protected procedures |
| Macro | **f9ed175800257b228166dabe8b3ac9a55e74e237** | event, evidence, government, earnings, K3E, theme, Research Vault implementation/research estate |
| Mastermind Terminal | **9e2f0bd94a2ee876c7dbafacb072414635277a36** | canonical Terminal/charting estate |

Protected procedure was loaded from the exact Mastermind pin above:

- https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/INDEX.md
- https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/ACTIVE_EXECUTION.md
- https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/SESSION_RELIABILITY.md

### Hardened capability matrix

The state labels below are intentionally stricter than the first draft. Code in GitHub proves implementation; it does not by itself prove current production operation.

| Capability | Hardened state | Evidence and audit ruling |
|---|---|---|
| qbus | **BUILT_NOT_PROVEN_CURRENT** | Main contains deterministic event keys, body hashes, source tiers, timestamp-quality fields, novelty and echo/corroboration logic. Current runtime freshness was not independently re-proven in this research. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/qbus.py |
| news event classifier | **BUILT / CONTEXT_ONLY / current runtime UNKNOWN** | Deterministic taxonomy covers earnings, guidance, analyst revisions, contracts, customers, products, regulatory and capital-markets events. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/news_events.py |
| importance_v0 | **SHADOW** | Code is explicitly shadow-oriented and novelty-first; it uses novelty, corroboration, source tier and crowding. It should remain an escalation input, not an opaque conviction score. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/importance_v0.py |
| qledger | **BUILT_NOT_PROVEN_CURRENT** | Universal claim/evaluation substrate exists with horizons, placebo/control concepts and independent-date accounting. Current production freshness was not re-proven here. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/qledger.py |
| Earnings Intelligence OS E0–E2 | **DONE for bounded first arc; historically PROVEN_LIVE; current breadth/freshness not re-proven** | Workstream records E0, E1, E1P and E2 done, including historical production generations and Terminal delivery. This is a bounded issuer slice, not proof of broad event-to-earnings completion. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md |
| Company Event Intelligence Spine | **CANONICAL OWNER / substantial historical production receipts** | Canonical docket requires stable event identity, source-addressed documents, deterministic numerical claims, source-span narrative claims, correction propagation, typed missingness, rights profiles and context-only model authority. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/research/COMPANY_EVENT_INTELLIGENCE_SPINE_AND_PREMIUM_IR_SUITE_BUILD_DOCKET_2026-08-01.md |
| company_event.v1 | **BUILT / CONTEXT_ONLY** | Stable CIK-backed issuer identity, fiscal-period event identity, source availability and observation clocks, correction-stable lifecycle. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/company_intelligence/events.py |
| event_workspace.v1 | **BUILT / PARTIAL / CONTEXT_ONLY** | Immutable generations and correction-chain support exist. G0 audit still identifies clock/consensus/reaction gaps. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/company_intelligence/event_workspace.py and https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/research/earnings_intelligence/g0/G0_EVENT_CLOCK_AND_CONTRACT_CENSUS.md |
| Evidence Foundation | **BUILT CONTRACT LAYER / no shared store by design** | EvidenceRef, EvidenceBlock and EvidenceRecipe point to owner-native objects. The README explicitly rejects a shared payload warehouse/index/writer/scheduler. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/contracts/evidence_foundation/README.md |
| Government Revenue / SAM / USAspending | **SUBSTANTIAL BUILT ESTATE; current production freshness not re-proven here** | Existing owner preserves opportunity revisions/first-seen evidence and maintains conservative company-exposure semantics. This commission must build economics on top, not another procurement ingest plane. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/government_revenue/opportunities.py |
| Federal Register collector | **BUILT_NOT_PROVEN_CURRENT** | Deterministic agency/term mapping and official document identifiers exist. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/collectors/federal_register.py |
| Theme Graph | **CANONICAL OWNER / PARTIAL PIT COMPLETION** | The first draft's "no canonical dynamic subtheme identity" statement was too broad. Current Theme Graph has canonical/local-theme identities, bitemporal edges, source-local subthemes, correction semantics and zero authority. However D2C forward PIT vintage completion and W3B sole ThemeState remain TODO. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/contracts/theme_graph/README.md and https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/agentos/workstreams/WS-GMI-THEME-GRAPH.md |
| Historical training-grade subtheme membership | **PARTIAL / NOT COMPLETE** | Local identities and some observed/reconstructed PIT exist, but several source planes still need forward-only vintage completion. Current owner explicitly lists D2C as TODO. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/research/theme_graph/THEME_GRAPH_END_TO_END_COMPLETION_FREEZE_2026-08-27.md |
| Earnings-estimate revisions | **PROSPECTIVE CAPTURE EXISTS; historical institutional PIT series still missing** | Existing analyst_revisions history is a monthly recommendation-trend append log, not a mature historical earnings-estimate revision surface. Evidence: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/analyst_revisions.py |
| K3E expectation capture / Information→Price | **ACTIVE HELD CARRIERS; substantial prospective evidence, not canonical publication** | PR #8312 reports 473,200 observations across 40 UTC days and a bounded source-acceptance programme; raw rows still have UNKNOWN rights and missing canonical identity, units, currency, basis and source-publication clocks. PR #8337 adds explicit-cutoff read-only inspection but keeps normalized_baseline.value null. These are not historical PIT backtest proof. Evidence: https://github.com/mastermindx-market-intelligence/macro/pull/8312 and https://github.com/mastermindx-market-intelligence/macro/pull/8337 |
| Economic Propagation mechanism contract | **BUILT ON HELD DRAFT PR / NOT MERGED / NOT LIVE** | PR #6514 already defines propagation_hypothesis/v1, Graph-1 relationship gating, typed abstention, mechanism hypotheses, exact identity, no scalar authority and no new store. Any Commission 1 mechanism contract must compose through or explicitly supersede this after acceptance; it must not fork a semantic twin. Evidence: https://github.com/mastermindx-market-intelligence/macro/pull/6514 at head 74b6426c8be71adec27df00f2f98172f8528c2b2 |
| Macro Events & News R2 | **BUILT_NOT_PROVEN / UNWIRED / HELD** | PR #8186 is a UI/server projection for official macro results, with clock disclosure and correction handling, but it is not the general company event-to-earnings system and must not be duplicated. Evidence: https://github.com/mastermindx-market-intelligence/macro/pull/8186 |
| Portfolio V3 Decision Snapshot | **SPEC_ONLY / NOT production authority** | Mastermind design still carries NOT_BUILT / BUILT_NOT_PROVEN distinctions and a Decision Snapshot architecture. Commission 1 should be snapshot-ready but must not route around current portfolio owners. Evidence: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md |
| Static Mastermind census | **STALE OBSERVABILITY** | Checked-in census remains generated 2026-07-16. Evidence: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/data/census/CENSUS.md |
| Research Vault | **MACRO-OWNED SUBSYSTEM** | Current code ownership remains under Macro's engine/research_vault plus its storage/delivery plane; no separate repository was established by this audit. |

### Duplicate and adjacent-program audit

The implementation owner must re-census these at start. They are not all merged law, but they are occupied or adjacent territory that cannot be ignored:

- **Earnings Intelligence OS / Company Event Intelligence** — canonical issuer event/document/claim owner.
- **Evidence Foundation** — accepted composition contract; physical shared store refused.
- **K3-D Economic Propagation, PR #6514** — held draft mechanism/relationship contract.
- **K3E Information→Price, PRs #8312 and #8337** — held expectation-source and explicit-cutoff consumer carriers.
- **GMI Theme Graph** — canonical theme/local-theme truth and PIT membership owner.
- **Government Revenue** — procurement opportunity/award identity and revision owner.
- **Macro Events & News R2, PR #8186** — held official-result UI projection.
- **Current GMI audited v3 research, PR #8324** — draft research carrier; useful evidence, not merged source law.
- **Regime mechanism evidence, PR #8306** — adjacent mechanism-evidence work in Neural Web; not an issuer-event owner.
- **FIF** — filing/fundamental truth and PIT fundamentals.
- **qbus / qledger** — qualitative event substrate and evaluation substrate.
- **Decision Snapshot V3** — future consumer, not current authority.

The hardened commission therefore rejects the phrase "build an Event-to-Expectation Compiler" if it implies a new owner. The lawful phrase is **complete an Event-to-Expectation composition lane across current owners**.

---

## C. State-of-the-art research

The research literature supports building a disciplined event-intelligence measurement system. It does **not** establish that a particular Mastermind event feature will generate alpha.

### News and textual information

Tetlock (2007) finds that media pessimism is associated with market pressure and trading volume; Tetlock, Saar-Tsechansky and Macskassy (2008) find that firm-specific negative language contains information about future earnings and short-horizon returns, especially for fundamental stories. These results support the proposition that text contains economically relevant information and that markets may not instantaneously absorb all of it. They do not justify a generic sentiment score or prove that a modern multi-source event pipeline will retain the same edge.

Sources:
- https://doi.org/10.1111/j.1540-6261.2007.01232.x
- https://doi.org/10.1111/j.1540-6261.2008.01362.x

A 2022 Journal of Financial Economics study using 21 million articles finds that material news is related to stock-return jumps and that the relation varies with media visibility, analyst coverage and institutional ownership. That supports event-family and issuer-coverage conditioning rather than one global model:
- https://doi.org/10.1016/j.jfineco.2021.08.002

### Earnings expectations and drift

Bernard and Thomas (1990) document that prices do not fully reflect implications of current earnings for future earnings. Abarbanell and Bernard (1992) find analysts themselves underreact to recent earnings, but that analyst underreaction explains only part of post-earnings-announcement drift. The architectural implication is that earnings surprises, analyst revisions, and market underreaction are distinct evidence families; one should not be used as a proxy for all three.

Sources:
- https://doi.org/10.1016/0165-4101(90)90008-R
- https://doi.org/10.1111/j.1540-6261.1992.tb04010.x

### Economic relationships and secondary transmission

Cohen and Frazzini (2008) report return predictability across economically linked customer-supplier firms. This supports testing secondary transmission through real economic relationships. It also strengthens the need for K3-D's Graph-1 gate: thematic similarity or co-movement is not a substitute for an economic relationship.

Source:
- https://doi.org/10.1111/j.1540-6261.2008.01379.x

### Event-study design and dependence

MacKinlay (1997) remains a foundational reference for event-study design. Kolari and Pynnönen (2010) show that event-date clustering and even modest cross-sectional correlation can cause conventional event-study tests to over-reject. Commission 1 must therefore treat issuer clustering, shared macro events, overlapping events, and cross-sectional dependence as first-class statistical problems.

Sources:
- https://ideas.repec.org/a/aea/jeclit/v35y1997i1p13-39.html
- https://doi.org/10.1093/rfs/hhq072

Harvey, Liu and Zhu (2016) show why conventional significance thresholds are unreliable after extensive factor/data mining. This directly supports preregistration, multiple-hypothesis correction, frozen canaries and a high bar for promotion.

Source:
- https://doi.org/10.1093/rfs/hhv059

### Government procurement

Recent work provides evidence that government procurement can matter economically and that award announcements can move markets, but effects are heterogeneous and subject to information leakage, contract structure and future follow-on economics.

Sources:
- Arora et al. (2025), The Private Value of Innovating for the Government: https://www.nber.org/papers/w33880
- Ferris et al. (2025), Corporate Value Creation and the Award of Procurement Contracts: https://doi.org/10.1002/jcaf.22776
- Carril, Gonzalez-Lira and Walker (2026), Competition under Incomplete Contracts and the Design of Procurement Policies: https://doi.org/10.1257/aer.20221345

The architectural implication is not "government contract = positive earnings." The system must distinguish opportunity, award, funded obligation, ceiling/IDV, modification, execution, recognition timing, competition, and issuer scale.

### Entity/event extraction and abstention

Financial-domain NLP remains imperfect. FinER-ABSA (LREC 2026) reports material weakness on implicit entity recognition even for strong open models. Financial NER evaluations likewise identify persistent failure modes. Selective-prediction research supports explicit abstention when confidence is inadequate.

Sources:
- https://aclanthology.org/2026.lrec-1.149/
- https://aclanthology.org/2025.finnlp-1.15/
- https://aclanthology.org/2021.acl-long.84/
- https://arxiv.org/abs/1908.10063

The correct Mastermind use of LLMs is therefore **bounded extraction and hypothesis generation with abstention**, not silent completion of missing entities, relationships or numbers.

---

## D. Source landscape

"Verified" below means verified from current official/vendor documentation or current repository evidence. Contract-specific rights that were not inspected are marked UNKNOWN rather than inferred.

| Source | Coverage | History | Latency | PIT / vintage quality | Corrections / retractions | Identifiers / delivery | Rights / AI / redistribution | Cost class | Best use |
|---|---|---|---|---|---|---|---|---|---|
| SEC EDGAR / data.sec.gov | filings, submissions, XBRL facts | deep filing history | real-time / near-real-time | **High** when accession and dissemination clocks retained | amendments/new filings explicit | accession, CIK; API + bulk | public federal source; automated-use rules apply; document-specific rights caveats still possible | Open | canonical issuer filing clock and structured facts |
| Issuer IR / press releases | releases, presentations, product/customer/guidance events | issuer-dependent | often earliest first-party disclosure | **High prospectively** with immutable first-seen capture | pages may edit/delete; capture generations | issuer URLs/docs | public access does not prove redistribution or model-training rights | Open acquisition / rights diligence | earliest body-bearing issuer evidence |
| Federal Register + GovInfo | proposed/final rules, notices, official published record | Federal Register bulk from 2000; broader collections vary | publication-cycle | **High** for official publication lifecycle | updated packages and later documents | document number, docket refs; API/bulk/RSS | public government data; attachment rights may vary | Open | regulatory state and effective dates |
| Regulations.gov | dockets, documents, comments, supporting material | broad but agency-dependent | posting/agency workflow | **High/medium** if postedDate, lastModifiedDate, withdrawal and first-seen retained | lastModified/withdrawal semantics explicit; comments may depend on agency approval | docket/document/comment IDs; API | public API; attachment/content caveats | Free API key | rulemaking evolution and industry evidence |
| Congress.gov / GovInfo | bills, status, text, committees, laws | deep official history | legislative cadence | **High** for official status if update clocks retained | bill versions/status transitions explicit | bill/package IDs; API/bulk | public government source | Open | legislation state machine |
| SAM.gov Opportunities | solicitations, sources sought, awards, amendments | public API history is not a full version history | active notices daily; archived weekly | **Medium natively; high prospectively with first-seen version archive** | official API exposes latest active version; all versions require Data Services | notice/solicitation IDs; API | public API key; downstream document rights still require care | Open | earliest government-demand surface |
| USAspending | awards, transactions, IDVs, subawards, recipients | extensive | reporting-driven | **Medium/high** if action date separated from publication/observation | records can update; preserve generations | award/transaction/recipient IDs; API/download | public API | Open | realized obligations and award modifications |
| Grants.gov | funding opportunities | historical opportunities available | posting cadence | **Medium/high** with first-seen capture | amendments matter | opportunity IDs; API/services | public federal source | Open | grants/subsidy opportunity flow |
| FDA / DOJ / FTC / sector agencies | recalls, approvals, enforcement, competition, sector actions | agency-dependent archives | often source-of-record | **High prospectively** | lifecycle differs by agency; must model filed/proposed/final/terminated | agency-native IDs/URLs | public source; attachment caveats | Open | typed sector-specific official events |
| Existing qbus news stack | broad discovery and corroboration | provider-dependent | near-real-time to crawl-bounded | **Mixed** | source/provider-dependent | qbus item/event keys + provider IDs | existing entitlements; body retention/AI rights provider-specific | Existing | discovery, novelty, corroboration |
| LSEG Machine Readable News | Reuters/third-party machine-readable news and analytics | vendor advertises long history | streaming | potentially **High**, entitlement/sample dependent | vendor-defined correction/retraction semantics require sample proof | vendor entity/event IDs; feed/bulk | strict contract; AI/derived/redistribution rights UNKNOWN until contract review | Enterprise | premium-news challenger only if measured incremental value |
| RavenPack News Analytics | large source/entity/event taxonomy and analytics | vendor advertises history from 2003 | real-time commercial | potentially **High**, sample dependent | vendor-defined | vendor IDs/API/feed | strict contract; AI/derived/redistribution UNKNOWN until contract review | Enterprise | event tagging/novelty benchmark, not automatic buy |
| Benzinga Stock News API | US/Canada market news, full text, created/updated timestamps | vendor advertises history from 2010 | intraday / vendor says not delayed | **Medium/high potential**, historical edit semantics need sample | created/updated plus removed-news endpoint documented | article ID; REST/TCP/RSS | vendor says full stories can be embedded; model-training/derived-data rights still contract-dependent | Commercial | lower-friction premium-news challenger |
| Existing K3E expectation capture | current prospective estimate observations | about 40 UTC days in current held audit | collection cadence | **Prospective only; not historical PIT-qualified** | repeated observations/corrections captured; publication clocks incomplete | provider-native ticker/horizon/period; Git-bound receipts | current PR reports UNKNOWN rights; must resolve before broader use | Existing | finish native prospective expectation plane first |
| LSEG I/B/E/S Point-in-Time | analyst detail/consensus, actuals, guidance | official materials advertise US from 1976 / non-US from 1987 for I/B/E/S PIT products | product-dependent; PIT snapshots are a distinct product | **High potential** | activation/stop/restatement semantics available in product family; contract/sample proof still required | broad IDs; API/bulk/FTP/cloud depending product | strict contract; AI/derived/redistribution UNKNOWN until contract review | Enterprise | conditional historical expectation-vintage source |
| FactSet Estimates / PIT | consensus, detail, ratings, guidance, actuals | estimates history from 1999; FactSet PIT paper says PIT database not before Dec 2009 | daily snapshot / API product-dependent | **High potential with explicit limitations** | methodology/history rules documented; exact entitlement/sample proof required | FactSet symbology; API/DataFeed | strict contract; AI/derived/redistribution UNKNOWN | Enterprise | conditional historical PIT challenger |
| FMP / Finnhub estimate products | estimates/recommendations depending entitlement | vendor/product-dependent | API | **UNKNOWN for institutional PIT replay until sampled** | UNKNOWN | vendor IDs/API | existing paid-data memo says do not buy on current evidence; rights entitlement-specific | Existing/Commercial | low-cost challenger only if it clears PIT and rights gates |
| Commercial supply-chain data | supplier/customer/partner relations | vendor-dependent | periodic | **UNKNOWN until effective-date/vintage audit** | relationship revisions/deletions are critical | vendor IDs/API/feed | strict contract | Enterprise | P1/P2 only if it adds lawful PIT relationships beyond house graph |

Primary official/vendor references used in this audit:

- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Regulations.gov API: https://open.gsa.gov/api/regulationsgov/
- SAM Opportunities API: https://open.gsa.gov/api/get-opportunities-public-api/
- USAspending API: https://api.usaspending.gov/docs/endpoints
- GovInfo developers: https://www.govinfo.gov/developers
- LSEG Machine Readable News: https://www.lseg.com/en/data-analytics/financial-news-service/machine-readable-news
- LSEG I/B/E/S broker estimates: https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates
- LSEG I/B/E/S guidance: https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/guidance
- FactSet Estimates overview: https://insight.factset.com/resources/factset-consensus-estimates-datafeed
- FactSet PIT methodology paper: https://insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf
- Benzinga Stock News API: https://www.benzinga.com/apis/cloud-product/stock-news-api/
- RavenPack News Analytics: https://www.ravenpack.com/products/edge/data/news-analytics

### Source-selection law

A commercial source earns a place only if it adds one or more of:

1. materially earlier availability;
2. materially broader high-value event coverage;
3. materially better body-bearing evidence;
4. materially better correction/vintage reconstruction;
5. materially better canonical identifiers;
6. materially better historical PIT eligibility;
7. rights that permit the intended internal/model/derived use;
8. measured incremental predictive or research value after existing Mastermind controls.

Marketing claims alone satisfy none of these gates.

---

## E. Canonical data model

### Architectural ruling: no universal event store

The hardened design uses owner-native identities and Evidence Foundation composition. It does not create a second event database.

The identity hierarchy is:

    source version
      -> document
        -> claim / structured fact
          -> real-world event
            -> entity / product / facility / programme
              -> economic relationship
                -> mechanism hypothesis
                  -> operating KPI
                    -> deterministic scenario projection
                      -> expectation state
                        -> market-incorporation evidence
                          -> evaluated claim

Different owners may legitimately own different levels. Evidence Foundation binds them without pretending they are one native object.

### Temporal model

The first draft did not separate actual possession from hypothetical source availability sharply enough. The hardened clock model is:

| Field | Meaning | Authority / replay rule |
|---|---|---|
| **event_time** | when the real-world event occurred; may be an interval or unknown | never a proxy for public availability |
| **effective_from / effective_to** | when a state, relationship, rule or contract term is economically valid | state validity, not knowledge time |
| **source_created_at** | source-system creation time, if exposed | may precede publication; never automatically public |
| **source_published_at** | publisher-asserted publication time | usable only with timestamp-quality metadata |
| **source_updated_at** | publisher-asserted edit/update time | later version unavailable to earlier replay |
| **scheduled_for** | pre-announced future event/release time | schedule evidence, not event occurrence |
| **source_available_at** | earliest defensible public availability of this exact source version | source-availability replay clock |
| **first_seen_at / observed_at** | first moment Mastermind actually observed this exact version | immutable actual-possession clock |
| **ingested_at** | durable write time inside Mastermind | operational, not necessarily public availability |
| **known_at** | earliest time this Mastermind decision process could legally use the object | for actual-possession replay: max(source_available_at, observed_at) unless owner law is stricter |
| **supersedes** | exact prior source/document/claim version replaced | correction lineage |
| **retracted_at** | time a source/version was withdrawn or invalidated | historical version remains replayable |
| **correction_generation** | immutable generation ordinal/hash lineage | never overwrite prior historical state |
| **timestamp_precision** | exact, second, minute, hour, date-only, interval, unknown | controls permissible market-reaction resolution |
| **timestamp_quality** | source-native, independently observed, crawl-bounded, inferred, unknown | controls replay admissibility |
| **as_of** | caller-supplied decision/replay cutoff | every read is explicit; no ambient latest |

### Two replay modes

**Possession replay** asks: "What did Mastermind actually possess at time t?"  
Eligibility requires known_at <= t, where known_at cannot precede actual observation.

**Source-availability replay** asks: "What could a correctly operating adapter have observed from this source at time t?"  
It may use source_available_at earlier than historical Mastermind observation **only** when the source's historical publication/version timestamp is independently defensible. It must be labelled hypothetical capability replay and may never be reported as actual historical possession.

This distinction is mandatory for the optics-style canary.

### Market-session semantics

Every event-to-price join must also materialize:

- exchange calendar;
- issuer primary listing;
- source timezone and original timezone;
- normalized UTC time;
- session phase: pre-market, regular, after-hours, closed/holiday;
- next tradable bar/time;
- event-time precision;
- whether the event was scheduled;
- whether a price window overlaps another material event.

Date-only source clocks cannot support intraday lead claims.

### Identity and dependence

The system must distinguish:

1. **source_version_id** — exact provider/version bytes or immutable source revision;
2. **document_id** — logical article/filing/release identity across versions;
3. **claim_id** — one extracted or structured assertion;
4. **real_world_event_id** — economic event cluster;
5. **company_id / issuer_id** — canonical corporate identity;
6. **product_id / facility_id / programme_id** — non-security operating identities;
7. **security_id + alias epoch** — listing/security identity over time;
8. **origin_family_id** — common upstream origin for dependence;
9. **evidence_family** — independent analytical family, not source count.

### Deduplication and non-merging law

Merge aggressively at source-version/document level only when identity is strong. Be conservative at real-world-event level.

Never merge solely because:
- headlines are similar;
- tickers overlap;
- two events occur on the same day;
- two sources describe the same broad theme;
- a syndication chain changed wording.

Never split solely because:
- an article was edited;
- a correction changed numbers;
- the same event was reported by multiple desks.

A correction updates source/document/claim generations. It does not automatically fork the underlying real-world event.

### Mechanism contract collision ruling

Commission 1 should **not** mint a new generic Mechanism Chain contract while PR #6514 remains an occupied held carrier. If that contract is accepted, event-to-earnings work should specialize or compose through economic_propagation.propagation_hypothesis/v1. If it is rejected, the implementation owner must preserve its hard-won laws inside the canonical Earnings owner rather than creating a third mechanism schema.

Minimum mechanism semantics remain:

- source event refs;
- target identity and resolution state;
- economic relationship evidence;
- mechanism class;
- operating KPI class;
- direction;
- lag/ramp interval;
- required assumptions;
- alternatives;
- contradictions;
- falsifier;
- evidence spans/refs;
- model/rule provenance;
- typed abstention;
- zero rank/size/gate/trade authority.

### Deterministic fundamental scenario projection

This is the principal additive analytical contract recommended by this audit. It should be a **derived, context-only projection**, not a store.

Each numeric input must carry:

- value;
- unit;
- scale;
- currency where relevant;
- accounting basis;
- metric definition;
- fiscal period and period type;
- segment / geography / product scope;
- sign convention;
- source or empirical-prior reference;
- known_at;
- authority class;
- uncertainty/range if applicable.

Allowed authority classes:

- source_observed_fact;
- deterministic_derivation;
- versioned_empirical_prior;
- explicit_user_or_test_scenario_assumption.

**model_hypothesis is not a numeric authority class.**

Every formula must carry formula_id and formula_version. The calculator must fail closed on incompatible units, currencies, periods, accounting bases, scopes or signs.

Examples:

    recognized_revenue[t]
      = committed_or_obligated_value
      × attributable_share
      × recognition_share[t]

    incremental_revenue
      = incremental_capacity
      × utilization
      × yield
      × ASP

    incremental_gross_profit
      = incremental_revenue
      × incremental_gross_margin

    input_cost_impact
      = exposed_volume
      × unit_cost_delta
      × unhedged_fraction
      × (1 - realized_pass_through)

The engine must distinguish:
- award ceiling vs funded obligation;
- backlog vs recognized revenue;
- gross vs net revenue;
- GAAP vs adjusted/non-GAAP;
- annual vs quarterly periods;
- constant vs reported currency;
- consolidated vs segment metrics;
- units vs thousands/millions;
- pre-tax vs after-tax;
- diluted vs basic share count.

If the chain cannot reconcile to EPS safely, stop at revenue, gross profit, operating income, capex or FCF. **Stopping early is correct behavior.**

### Expectations contract

Do not create a second expectation owner. Finish the existing K3E path.

Provider-neutral normalized expectation fields should include:

- provider;
- provider_record_id;
- observation/vintage id;
- metric;
- fiscal period;
- basis;
- currency;
- scale;
- consensus mean/median;
- high/low or dispersion;
- analyst count where licensed;
- detail-estimate count where licensed;
- revision breadth;
- contributor age distribution;
- source_available_at;
- observed_at;
- known_at;
- correction/supersession semantics;
- basis_match;
- identity_match;
- rights state;
- missingness state.

Pre-event and post-event estimate observations must remain separate. A post-event revision may be an outcome target; it may not leak into the pre-event expectation baseline.

---

## F. Derived intelligence

### Deterministic outputs first

Before any LLM call, compute:

- source/version identity;
- exact and near duplicate status;
- origin-family dependence;
- first seen and first independent confirmation;
- timestamp precision/quality;
- event finality;
- amendment/correction generation;
- structured numeric facts;
- entity/security exact matches;
- source authority for each claim;
- novelty and crowding;
- scheduled/unscheduled state;
- market-session phase;
- issuer-relative materiality inputs.

### LLM outputs

A model may emit:

- candidate event class;
- candidate entity/product/facility mapping;
- candidate economic relationship;
- mechanism alternatives;
- affected KPI;
- direction;
- lag/ramp narrative;
- required numeric assumption slots;
- supporting spans;
- contradictions;
- unknowns;
- falsifier;
- abstention.

A model may **not** emit an authoritative:
- revenue delta;
- margin delta;
- EBITDA/EBIT delta;
- capex delta;
- FCF delta;
- EPS delta;
- target price;
- probability of beat;
- probability of trade success.

### Expectation gap

Expectation gap is not one scalar. Preserve at least:

- scenario range vs pre-event consensus distribution;
- basis-match state;
- analyst count and dispersion;
- pre-event revision trend;
- post-event revision outcome;
- provider/vintage age;
- missingness/rights/identity state.

### "Already priced" is not a label

The first draft was right to reject an intuitive LLM verdict, but the audit strengthens the design.

Market-incorporation evidence should include:

- pre-event abnormal returns over multiple windows;
- event-window abnormal return with market/sector/factor controls;
- abnormal volume;
- overnight gap;
- intraday reaction only when source and market clocks permit;
- options-implied move and volatility/skew changes where available;
- peer/customer/supplier response;
- qbus attention/crowding;
- post-event analyst revisions;
- pre-event leakage/anticipation evidence;
- confounding-event flags;
- overlapping-event flags.

Interpretation should distinguish:

1. **anticipated** — price/consensus moved before public event;
2. **immediate incorporation** — large event-window adjustment;
3. **partial incorporation / candidate underreaction** — modest initial reaction followed by later movement, only after controls;
4. **confounded** — event window contains other material information;
5. **unidentified** — clock or data resolution insufficient.

No "underreaction" model earns authority until out-of-sample validation shows incremental information after existing Mastermind price, qbus, expectation and regime features.

---

## G. Mastermind integration map

| Producer | Canonical owner/artifact | Evidence family | Commission 1 use | Consumer |
|---|---|---|---|---|
| SEC EDGAR | Company Intelligence / FIF | issuer_primary_event, filing_fact | event clock, structured facts, filing body | Earnings/Event, Research |
| Issuer IR/releases | Earnings Intelligence document/source owner | issuer_primary_event | earliest body-bearing issuer evidence | Event workspace |
| qbus/news collectors | qbus + news_events | news_detection, corroboration | discovery, novelty, source dependence | event escalation |
| Government Revenue | native opportunity/award/revision objects | government_demand | procurement lifecycle and realized obligations | mechanism/scenario research |
| Federal Register / Regulations / legislation | official-source/policy owners | policy_regulatory | rule lifecycle and exposure | mechanism/scenario research |
| Theme Graph | WS:GMI-THEME-GRAPH | thematic_relationship | secondary context only; use PIT membership | propagation candidates |
| FIF / PIT fundamentals | canonical filing/fundamental owners | fundamental_state | scenario baselines | deterministic calculator |
| Economic Propagation PR #6514, if accepted | Alpha Intelligence integration contract | economic_relationship/mechanism | relationship-gated mechanism hypothesis | scenario projection |
| K3E expectation capture / EXP-1 | Expectation Market Dynamics | earnings_expectations | pre-event expectation surface | expectation gap |
| Prices/options/breadth | existing market owners | market_pricing | event-study/pricing evidence | K3E Information→Price |
| Evidence Foundation | EvidenceRef / Block / Recipe | composition | cross-owner binding and dependence | Terminal/Brain/future snapshots |
| qledger / existing graders | claim/grade owners | evaluation | preregistered shadow claims | promotion/falsification |
| Decision Snapshot V3 | future portfolio owner | decision-time projection | future consumer only after accepted | portfolio |

### Ownership ruling

The event-to-expectation lane is **not a program key**. It is a composition recipe across these owners.

---

## H. Empirical validation program

### Validation principle

The unit of inference is usually the **real-world event cluster**, not the article. Syndicated articles are not independent observations.

### Preregistration

Before looking at outcome returns for a confirmatory sample, freeze:

- event family;
- eligible sources;
- identity rules;
- source clock rules;
- event clustering rules;
- materiality definition;
- mechanism/KPI taxonomy;
- scenario formulas;
- baseline features;
- outcome horizons;
- abnormal-return model;
- control construction;
- exclusion rules;
- multiple-testing family;
- success/failure thresholds;
- transaction-cost/actionability assumptions.

### Validation layers

| Layer | Question | Metrics |
|---|---|---|
| source/PIT | was exact information legally available? | clock violation rate, replay reconstruction rate |
| dedup | did documents map to correct events/origins? | pairwise precision/recall, cluster purity |
| entity | are company/product/facility identities correct? | precision/recall, unresolved rate |
| relationship | is Graph-1 economic relation real? | precision, abstention calibration |
| event class/finality | is the event typed correctly? | macro/micro F1, confusion matrix |
| mechanism | is the causal path defensible? | blinded acceptance, top-k precision, contradiction rate |
| KPI | is the affected operating metric correct? | precision@k, direction accuracy |
| scenario | are deterministic ranges calibrated? | interval coverage, MAE where meaningful |
| expectation | does the event predict later legitimate revisions? | revision breadth/magnitude, rank IC |
| price | is there incremental information? | abnormal returns, event-window effect, drift |
| secondary propagation | are related-security paths useful? | precision@k, relative spread, false propagation |
| incrementality | does this beat existing Mastermind features? | nested-model uplift, ablation, conditional IC |
| calibration | do probabilities/ranges mean what they say? | Brier/log loss, reliability, coverage |
| actionability | is gross signal economically usable? | turnover, slippage/cost sensitivity, capacity |

### Dependence and overlapping events

Required protections:

- issuer-clustered and event-date-clustered inference;
- block/bootstrap resampling by date and/or issuer;
- Kolari-Pynnönen-style correction or equivalent when event dates cluster;
- exclusion or explicit multi-event modelling when material events overlap;
- shared-macro-event grouping for cross-sectional issuer samples;
- no treating suppliers/customers exposed to one macro event as independent draws;
- frozen origin-family dependence.

### Multiple testing

Use a declared hypothesis family and control false discovery. Report all tested event families, not only winners. A nominal t-statistic around 2 is not a promotion gate after broad search. Use BH/FDR or a stricter preregistered family-wise procedure as appropriate, with Harvey-Liu-Zhu as a warning against factor mining.

### Walk-forward and regime stability

Use rolling-origin / forward-chaining splits. Never random-split future and past events.

Report:
- pre/post-regime performance;
- source-coverage changes;
- model-version changes;
- rights/availability changes;
- issuer-size/liquidity buckets;
- event-family stability;
- calendar-year stability.

### Matched controls and placebos

For each event family, compare against:
- matched issuer non-event dates;
- matched sector/size/liquidity controls;
- random-date placebos;
- qbus-only baseline;
- price/momentum baseline;
- existing earnings/SUE baseline;
- K3E expectation baseline when available.

### Optics-style canary

The optics-style case remains a **frozen canary**, not proof.

At each information frontier record:

    exact source versions available
    possession-replay eligibility
    source-availability-replay eligibility
    event detected?
    identity resolved?
    economic relationship supported?
    mechanism proposed?
    KPI mapped?
    scenario computable?
    expectation baseline available?
    market-incorporation evidence available?
    primary/secondary security path available?
    escalation tier?

Measure recognition lead versus:
- first material abnormal price move;
- broad-news pickup;
- analyst revision;
- later operating/fundamental confirmation.

Daily bars cannot prove intraday lead. A source discovered later cannot be retroactively labelled actual Mastermind possession.

### Promotion

Everything begins SHADOW / context-only. Promotion requires:
- enough independent events;
- stable out-of-sample performance;
- multiple-testing correction;
- calibration;
- incrementality over existing Mastermind;
- acceptable missingness and source drift;
- economic usefulness after realistic costs;
- qledger/existing grader evidence;
- separate owner acceptance.

---

## I. Risks and failure modes

| Failure | Consequence | Control |
|---|---|---|
| publisher edit/backdate | historical leakage | immutable source versions + observed_at |
| source deletion | silent survivorship | tombstone/retracted_at + retained prior receipt where lawful |
| scheduled release mistaken for event | false lead | scheduled_for separate from event_time |
| embargo/source creation mistaken for public availability | lookahead | source_created_at separate from source_available_at |
| backfill treated as historical possession | false alpha | possession vs source-availability replay modes |
| date-only source joined to intraday bars | false precision | timestamp_precision gate |
| syndicated stories counted independently | false corroboration | origin_family_id |
| article identity treated as event identity | duplicate events | layered identity model |
| event clustering over-merges distinct facts | lost information | conservative event merge + claim identities |
| current theme membership used historically | lookahead | Theme Graph PIT edges; D2C gate |
| ticker reused/renamed | identity leakage | security alias epochs + canonical issuer/security IDs |
| award ceiling treated as revenue | huge overstatement | procurement value semantics |
| backlog treated as recognized revenue | timing error | recognition schedule |
| GAAP/non-GAAP mixed | false expectation gap | basis_match fail closed |
| thousands/millions or unit mismatch | pseudo-precision | typed unit/scale validation |
| currency mismatch | false scenario | explicit currency/FX source and timestamp |
| LLM fills missing assumption | fabricated magnitude | numeric firewall |
| empirical prior uses future sample | hidden leakage | prior version/cohort/known_at |
| one event family dominates | non-general result | family-stratified evaluation |
| event-date clustering | false significance | clustered/event-study corrections |
| many hypotheses tried | false discovery | preregistration + FDR |
| source coverage improves over time | survivorship/coverage bias | dated coverage denominator |
| premium source adds no increment | cost/lock-in | controlled bake-off |
| rights prohibit AI processing/derived use | compliance risk | rights gate before retention/model use |
| model upgrade changes extraction | nonstationary labels | model/prompt/schema version receipts |
| K3-D/K3E held carrier assumed canonical | architecture split | acceptance check at implementation start |
| new Event-to-Expectation owner created | duplicate control plane | composition-only ruling |

### Kill criteria

**Official-source adapter:** kill or context-only if historical publication/version time cannot be reconstructed or if the source cannot distinguish corrections sufficiently for the intended replay.

**Premium news vendor:** reject if it does not materially improve lead time, body coverage, correction replay, identifiers or measured incremental value versus existing qbus + official sources; reject if rights do not fit storage/AI/derived use.

**Historical estimates vendor:** reject if point-in-time snapshots, contributor/basis semantics, corrections, corporate actions, identifiers and rights cannot be proven on sample bytes and contract language.

**Supply-chain vendor:** reject if relationships are not effective-dated/vintage-safe enough for historical use, or if precision does not exceed the current owner graph materially.

**Cheap LLM tier:** reject from production triage if blind precision/abstention does not meet the frozen threshold or if deterministic rules perform as well at lower cost.

**Medium mechanism tier:** reject from scenario admission if it cannot maintain high precision on relationship/mechanism/KPI mapping or if it fabricates unsupported specificity.

**Frontier tier:** do not deploy if it fails to improve accepted mechanism quality on the high-ambiguity subset enough to justify latency/cost.

**Scenario projection:** fail closed if any authoritative numeric output can be produced without admissible provenance, basis/unit/period checks and reproducible arithmetic.

**Predictive feature:** reject if incremental out-of-sample value disappears after controls, multiple testing, dependence correction or realistic costs.

---

## J. Build priority after audit

### P0 — do now, inside existing owners

1. **Collision freeze and owner map.** Reconcile current Earnings Intelligence, Evidence Foundation, K3-D PR #6514, K3E PRs #8312/#8337, Theme Graph, Government Revenue, FIF, qbus, qledger, Events & News R2 and Decision Snapshot status before code.
2. **Clock and replay integrity.** Add or validly project the hardened clock model without creating a new time store. Implement separate possession and source-availability replay modes.
3. **Finish native K3E expectation qualification first.** Resolve rights, identity, units, currency, basis and source-publication clocks; finish provider-neutral normalized expectation semantics. Do not buy a historical feed under this commission.
4. **Mechanism integration, not reinvention.** If K3-D is accepted, specialize through it. If not, preserve its relationship-gating/abstention laws under the canonical Earnings owner.
5. **Deterministic fundamental scenario projection + numeric firewall.** This is the principal new analytical primitive.
6. **Event-relative market-incorporation evidence through existing market/K3E owners.** No new Pricing State owner.
7. **Replay harness.** Explicit as_of, exact source generations, identity epochs, relationship/theme vintages and market-session semantics.
8. **qledger / existing grader shadow registration.** No second scoreboard.
9. **Refresh capability census/observability.** The July Mastermind census is too stale for architectural decisions.

### P1 — conditional after P0

- Historical PIT estimates vendor bake-off **only if** prospective K3E accrual cannot answer the required validation horizon. Include I/B/E/S, FactSet and any already-entitled lower-cost sources; do not preselect a winner.
- Premium-news bake-off against current qbus + official sources.
- GMI-owned D2C forward PIT completion and lawful subtheme history consumption.
- Prospective supplier/customer/product/facility relationship enrichment under current graph/identity owners.
- Intraday reaction support where source clocks and market data truly permit it.
- Sector-specific scenario templates.

### P2

- Commercial supply-chain data after PIT/rights proof.
- Cross-border government/regulator expansion.
- Calibrated underreaction classifier after raw incorporation evidence proves value.
- Frontier-model reasoning for the small high-materiality/high-ambiguity subset.
- Empirical mechanism priors after enough clean prospective data.

### Defer

- learned event-importance weights until enough graded labels exist;
- broad historical reconstruction of fine-grained subthemes;
- broad LLM-inferred relationship backfills;
- universal knowledge graph;
- global terminal-news parity for its own sake.

### Reject

- a new global event truth store;
- a new Event-to-Expectation program key;
- a second mechanism schema that duplicates accepted K3-D semantics;
- a second expectation/pricing owner that duplicates K3E;
- one aggregate event-conviction score;
- LLM-generated EPS/revenue/target-price numbers;
- headline-only magnitude extraction;
- current consensus snapshots used as historical PIT data;
- current theme/relationship graphs projected backward;
- syndication counted as independent evidence;
- one retrospective winner as alpha proof;
- portfolio/rank/size/gate authority from this programme.

---

## K. Implementation phases

### Phase 0 — current-source and collision adjudication

At implementation start:
- re-pin protected Mastermind and load current procedures;
- re-pin Macro and Terminal;
- re-check PR #6514, #8312, #8337, #8186, #8324 and any successors;
- re-read current Earnings, Evidence Foundation, Theme Graph, Government Revenue, FIF, qbus and qledger owners;
- produce one owner map.

Acceptance: no proposed field, store, identity or evaluator duplicates a current owner.

### Phase 1 — clocks, identity and replay

For one issuer event, one government event and one corrected source:
- prove source-version identity;
- prove published/available/observed/ingested clocks;
- prove possession replay;
- prove source-availability replay;
- prove correction/retraction lineage;
- prove session-phase resolution.

Acceptance: t-minus-one cannot see future information; later corrections do not rewrite earlier replay.

### Phase 2 — mechanism seam

Use the accepted canonical mechanism owner. If K3-D remains held, do not silently depend on it; obtain the required owner ruling or implement only within the existing Earnings owner without creating a semantic twin.

Acceptance: unresolved identity, absent economic relationship, rights block or clock failure produces typed abstention.

### Phase 3 — deterministic scenario projection

Implement only a small initial family:
- contract/order;
- capacity;
- customer gain/loss;
- input cost/tariff;
- supply constraint;
- guidance/preannouncement.

Acceptance: every output number reproduces exactly from admissible inputs and formula version; incompatible basis/unit/period/currency fails closed.

### Phase 4 — expectations

Finish the native K3E expectation plane and normalized provider-neutral contract before any historical vendor purchase.

Acceptance: pre-event packet contains no post-event estimate; basis/identity/rights missingness remains explicit.

### Phase 5 — market incorporation

Join existing price/options/volume/peer owners to event clocks with market/sector/factor controls and overlap flags.

Acceptance: no intraday claim from date-only clocks or daily bars; confounded windows are typed.

### Phase 6 — tiered models in shadow

Cheap:
- classification/entity/product triage;
- evidence-linked extraction.

Medium:
- mechanism/KPI alternatives;
- assumptions/unknowns/falsifiers.

Frontier:
- only high-materiality/high-ambiguity cases after deterministic escalation.

Every model call records:
- model/version;
- prompt/schema version;
- evidence refs;
- escalation reason;
- cost/latency;
- abstention;
- output generation;
- later grade.

Acceptance: no model output can populate authoritative numeric fields.

### Phase 7 — validation and promotion evidence

Run frozen canaries, broad matched samples, placebos, ablations, walk-forward evaluation, clustering/dependence corrections, multiple-testing correction and cost sensitivity.

Acceptance: only shadow claims are registered. Any promotion is a separate commission.

---

## L. Exact bounded follow-on implementation commission

> **IMPLEMENTATION COMMISSION — EVENT-TO-EXPECTATION P0 COMPLETION, COLLISION-SAFE**
>
> Implement only the bounded P0 completion described in the 2026-10-04 audited Commission 1 report.
>
> This commission does not authorize portfolio/trading changes, ranking, sizing, gating, new provider purchases, a new program key, a new global event store, a new evidence store, a new grading ledger, a new theme graph, or a second expectation/pricing owner.
>
> **Bootstrap**
>
> Re-pin current protected Mastermind and load the current matching Sol procedures. Re-pin Macro and Terminal. Do not assume the report's SHAs remain current.
>
> **Mandatory collision census before code**
>
> Reconcile current state of:
>
> - Earnings Intelligence OS / Company Event Intelligence;
> - Evidence Foundation;
> - K3-D Economic Propagation, including PR #6514 or its successor;
> - K3E Information→Price / Expectation Market Dynamics, including PRs #8312 and #8337 or successors;
> - Theme Graph;
> - Government Revenue;
> - FIF / PIT fundamentals;
> - qbus / news_events / importance_v0;
> - qledger / existing grading owners;
> - Macro Events & News R2;
> - Decision Snapshot / Portfolio V3.
>
> Stop and route a ruling if the proposed implementation would fork an occupied semantic owner.
>
> **Bounded fixture set**
>
> Use:
>
> - one already-supported issuer earnings/company event;
> - one SEC material corporate event;
> - one SAM/USAspending government-demand event;
> - one Federal Register/regulatory event;
> - one correction/retraction case;
> - several syndicated/duplicate news observations of one event.
>
> **Clock contract**
>
> Validly project or materialize owner-compatible:
>
> event_time, effective_from/effective_to, source_created_at, source_published_at, source_updated_at, scheduled_for, source_available_at, observed_at/first_seen_at, ingested_at, known_at, supersedes, retracted_at, correction_generation, timestamp_precision, timestamp_quality, explicit as_of.
>
> Implement separate possession replay and source-availability replay. Never claim historical possession from a later backfill.
>
> **Identity/dependence**
>
> Preserve separate source-version, document, claim, real-world event, issuer/company, product/facility, security-alias and origin-family identities. Syndicated descendants are dependent evidence.
>
> **Mechanism**
>
> Reuse the accepted canonical mechanism contract. If K3-D is accepted, compose through it. If it remains held/rejected, preserve its Graph-1 relationship gate, exact identity, typed abstention, no-scalar and zero-authority laws inside the canonical Earnings owner. Do not mint a parallel mechanism schema.
>
> **Deterministic scenario projection**
>
> Implement a context-only derived view for the bounded event families. Every numeric input carries value, unit, scale, currency, accounting basis, metric definition, fiscal period, scope, sign convention, provenance, known_at and authority class.
>
> Allowed numeric authority classes: source-observed fact, deterministic derivation, versioned empirical prior, explicit user/test scenario assumption.
>
> Language-model hypotheses are never numeric authority.
>
> Fail closed on unit, currency, accounting-basis, fiscal-period or scope mismatch. Stop at the highest defensible operating KPI rather than forcing EPS.
>
> **Expectations**
>
> Finish the current K3E provider-neutral normalized expectation surface. Resolve current rights/identity/basis/clock gaps. Do not buy a provider. Do not synthesize historical PIT estimates from current snapshots.
>
> **Market incorporation**
>
> Use existing price/options/volume/peer owners and K3E Information→Price. Produce inspectable event-study evidence, not an LLM "already priced" label. Mark anticipation, immediate reaction, candidate underreaction, confounding and unidentified states.
>
> **Models**
>
> Deterministic processing first. Cheap model for bounded triage/extraction. Medium model for mechanism/KPI alternatives and falsifiers. Frontier disabled or shadow-only behind deterministic high-materiality/high-ambiguity escalation.
>
> Pin model, prompt and schema versions. Require evidence refs and abstention. No model may rank, size, gate, originate or modify portfolio behavior.
>
> **Evaluation**
>
> Build explicit-as_of replay. Register eligible outputs only as SHADOW claims in qledger/existing grading owners. Include hostile tests for future leakage, correction leakage, backfill-as-possession leakage, current-theme lookahead, syndication dependence, award-ceiling confusion, accounting-basis mismatch, unit/currency mismatch, model-number injection, missing-to-zero conversion, ticker alias drift, duplicate-owner double counting and overlapping-event confounding.
>
> **Required deliverables**
>
> 1. current-source/collision receipt;
> 2. owner map;
> 3. clock/replay contract delta;
> 4. identity/dependence contract delta;
> 5. bounded mechanism composition proof;
> 6. deterministic scenario projection;
> 7. numeric-firewall tests;
> 8. K3E normalized expectation integration proof;
> 9. market-incorporation projection;
> 10. replay tests;
> 11. qledger/existing-grader shadow registration;
> 12. refreshed capability census;
> 13. closeout listing all NOT_BUILT and UNKNOWN items.
>
> **Acceptance**
>
> Accept only if no duplicate owner/control plane is created; historical replay cannot see future generations; possession and source-availability replay remain distinct; corrections preserve prior state; every scenario number has admissible provenance; no LLM can inject authoritative magnitude; source dependence prevents syndicated corroboration inflation; missingness stays typed; expectation and pricing ownership remain K3E/existing owners; all outputs remain context/shadow; and no production trading behavior changes.
>
> **Out of scope**
>
> No provider purchase. No portfolio promotion. No broad historical subtheme reconstruction. No universal knowledge graph. No aggregate event conviction score. No historical PIT estimate fabrication. No optics postmortem beyond a separately frozen replay canary.

---

# Appendix A — Source and evidence register

## A1. Protected and repository evidence

- Mastermind source-law index at audit pin: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/INDEX.md
- ACTIVE_EXECUTION: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/ACTIVE_EXECUTION.md
- SESSION_RELIABILITY: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/sol_skills/SESSION_RELIABILITY.md
- Mastermind census: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/data/census/CENSUS.md
- Portfolio V3 design: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md
- Trend Persistence Protocol: https://github.com/mastermindx-market-intelligence/Mastermind/blob/84df29801d4078724c2b603a136de5aa1532cdfe/research/TREND_PERSISTENCE_PROTOCOL.md
- qbus: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/qbus.py
- news_events: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/news_events.py
- importance_v0: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/importance_v0.py
- qledger: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/qledger.py
- company_event.v1 implementation: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/company_intelligence/events.py
- event_workspace.v1 implementation: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/company_intelligence/event_workspace.py
- Earnings G0 clock census: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/research/earnings_intelligence/g0/G0_EVENT_CLOCK_AND_CONTRACT_CENSUS.md
- Earnings owner decision: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/agentos/decisions/DEC-EARNINGS-INTELLIGENCE-PROGRAM-OWNERSHIP.md
- Evidence Foundation README: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/contracts/evidence_foundation/README.md
- Theme Graph contract: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/contracts/theme_graph/README.md
- Theme Graph workstream: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/agentos/workstreams/WS-GMI-THEME-GRAPH.md
- Government Revenue opportunities: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/government_revenue/opportunities.py
- Federal Register collector: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/collectors/federal_register.py
- analyst revisions: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/engine/analyst_revisions.py
- current active build map: https://github.com/mastermindx-market-intelligence/macro/blob/f9ed175800257b228166dabe8b3ac9a55e74e237/docs/ACTIVE_BUILD_MAP.md
- K3-D Economic Propagation held carrier: https://github.com/mastermindx-market-intelligence/macro/pull/6514
- Information→Price source audit: https://github.com/mastermindx-market-intelligence/macro/pull/8312
- K3E EXP-1 explicit-cutoff consumer: https://github.com/mastermindx-market-intelligence/macro/pull/8337
- Macro Events & News R2: https://github.com/mastermindx-market-intelligence/macro/pull/8186
- GMI audited v3 draft: https://github.com/mastermindx-market-intelligence/macro/pull/8324

## A2. External primary/vendor sources

- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Regulations.gov API: https://open.gsa.gov/api/regulationsgov/
- SAM Opportunities API: https://open.gsa.gov/api/get-opportunities-public-api/
- USAspending API: https://api.usaspending.gov/docs/endpoints
- GovInfo developer hub: https://www.govinfo.gov/developers
- FDA recalls/safety alerts: https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts
- DOJ Antitrust press room: https://www.justice.gov/atr/press-room-0
- FTC press releases: https://www.ftc.gov/news-events/news/press-releases
- LSEG Machine Readable News: https://www.lseg.com/en/data-analytics/financial-news-service/machine-readable-news
- LSEG I/B/E/S: https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates
- FactSet Estimates: https://insight.factset.com/resources/factset-consensus-estimates-datafeed
- FactSet PIT paper: https://insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf
- Benzinga Stock News API: https://www.benzinga.com/apis/cloud-product/stock-news-api/
- RavenPack News Analytics: https://www.ravenpack.com/products/edge/data/news-analytics

## A3. Academic references

- Tetlock 2007: https://doi.org/10.1111/j.1540-6261.2007.01232.x
- Tetlock, Saar-Tsechansky and Macskassy 2008: https://doi.org/10.1111/j.1540-6261.2008.01362.x
- Cohen and Frazzini 2008: https://doi.org/10.1111/j.1540-6261.2008.01379.x
- Bernard and Thomas 1990: https://doi.org/10.1016/0165-4101(90)90008-R
- Abarbanell and Bernard 1992: https://doi.org/10.1111/j.1540-6261.1992.tb04010.x
- MacKinlay 1997: https://ideas.repec.org/a/aea/jeclit/v35y1997i1p13-39.html
- Kolari and Pynnönen 2010: https://doi.org/10.1093/rfs/hhq072
- Harvey, Liu and Zhu 2016: https://doi.org/10.1093/rfs/hhv059
- Arora et al. 2025: https://www.nber.org/papers/w33880
- Carril, Gonzalez-Lira and Walker 2026: https://doi.org/10.1257/aer.20221345
- FinER-ABSA 2026: https://aclanthology.org/2026.lrec-1.149/
- Financial NER 2025: https://aclanthology.org/2025.finnlp-1.15/
- Selective prediction / abstention: https://aclanthology.org/2021.acl-long.84/

---

# Appendix B — Current-state claim matrix

| Claim | State | Durable evidence |
|---|---|---|
| qbus has deterministic event identity/novelty/corroboration primitives | BUILT | Macro f9ed, engine/qbus.py |
| deterministic news event taxonomy exists | BUILT | Macro f9ed, engine/news_events.py |
| importance_v0 is shadow, novelty-first | SHADOW | Macro f9ed, engine/importance_v0.py |
| qledger exists as shared evaluation substrate | BUILT_NOT_PROVEN_CURRENT | Macro f9ed, engine/qledger.py |
| issuer event/document/claim owner already exists | CANONICAL | Earnings owner decision + Company Event docket |
| event_workspace has unresolved clock/consensus/reaction gaps | PARTIAL | G0 event clock census |
| Evidence Foundation is contracts, not a store | BUILT | contracts/evidence_foundation/README.md |
| Theme Graph owns local/canonical theme identity and PIT semantics | CANONICAL / PARTIAL | contracts/theme_graph/README.md |
| full training-grade dynamic subtheme PIT history is complete | FALSE | WS-GMI-THEME-GRAPH D2C remains TODO |
| no dynamic subtheme identity exists at all | FALSE | local_theme nodes and memberships exist |
| mature historical PIT earnings-estimate revision series exists | FALSE | K3E is prospective; current revisions file is not institutional PIT estimates |
| prospective expectation capture exists | TRUE / held acceptance | PR #8312 |
| explicit-cutoff expectation consumer exists | TRUE / held acceptance | PR #8337 |
| generic economic propagation mechanism contract is greenfield | FALSE | held PR #6514 occupies the semantic lane |
| a new shared evidence store is needed | REJECTED | Evidence Foundation physical store refusal |
| Decision Snapshot is current production authority | FALSE | Mastermind V3 spec remains not accepted production authority |
| current static census is fresh | FALSE | generated 2026-07-16 |

---

# Appendix C — Open questions / UNKNOWNs

1. Exact current runtime freshness of qbus, qledger, Federal Register and several Government Revenue collectors was not independently proven in this research.
2. K3-D PR #6514 remains held/unmerged at audit time. Its semantics are occupied prior art, not current merged law.
3. K3E PRs #8312 and #8337 remain held at audit time. Their source/consumer evidence is substantial but canonical publication and normalization remain gated.
4. Current provider rights for K3E expectation captures are explicitly UNKNOWN in the held source audit.
5. Exact AI-processing, derived-data and redistribution rights for LSEG, FactSet, RavenPack, Benzinga, FMP and Finnhub were not established from Mastermind contracts in this commission.
6. Historical PIT estimate coverage sufficient for pre-2026 replay is not currently proven in Mastermind.
7. Full training-grade effective-dated subtheme membership across all source planes is unfinished; GMI D2C remains the owner.
8. No broad blind benchmark of LLM mechanism/KPI extraction against a frozen Mastermind event corpus was run here.
9. No predictive alpha test was run here. The report recommends a validation design; it does not claim predictive success.
10. The exact implementation location for the deterministic scenario projection should be adjudicated by the Earnings owner at implementation start; this report does not create that owner.

---

# Appendix D — Decision log: changes from the first draft

1. **Pins updated.** Protected Mastermind is now 84df2980…, Macro f9ed1758…, Terminal 9e2f0bd9….
2. **Capability labels hardened.** "Built/live" was replaced with stricter BUILT_NOT_PROVEN_CURRENT or historical-PROVEN_LIVE wording where current runtime proof was absent.
3. **Dynamic subtheme finding corrected.** Canonical/local-theme identities and bitemporal membership semantics exist. The real gap is incomplete forward PIT vintage coverage and ThemeState completion.
4. **Expectation gap finding corrected.** Mastermind now has a substantial prospective K3E expectation-capture programme and explicit-cutoff consumer. It still lacks long historical institutional PIT coverage and full normalization.
5. **Paid estimates demoted from unconditional P0.** Finish native K3E first. Historical commercial PIT becomes conditional P1.
6. **Event-to-Expectation Compiler boundary narrowed.** It is now a composition lane, not a new owner/program.
7. **Mechanism contract collision discovered.** Held PR #6514 already occupies the generic economic-propagation hypothesis lane. Commission 1 must not fork it.
8. **Pricing/expectation ownership collision discovered.** K3E Information→Price already owns the expectation-to-market lane. Commission 1 must compose through it.
9. **Temporal model strengthened.** Added source_created_at, scheduled_for, source_available_at, retracted_at, supersedes, timestamp precision/quality, market-session semantics, and separate possession vs source-availability replay.
10. **Numeric firewall strengthened.** Added accounting basis, unit, scale, currency, fiscal period, scope, sign convention and empirical-prior provenance checks.
11. **"Already priced" hardened.** Added anticipation, confounding, overlapping-event and factor-control requirements; no intuitive label.
12. **Validation hardened.** Added preregistration, event/date clustering, block/bootstrap inference, multiple-testing correction, source-coverage drift, regime stability, actionability/costs and explicit falsifiers.
13. **Vendor diligence hardened.** Contract-dependent AI/derived/redistribution rights are UNKNOWN unless proven; marketing claims are separated from observed capability.
14. **P0 redefined.** P0 is completion and integration of current owners plus deterministic scenario/replay infrastructure, not creation of a new system.
15. **No implementation performed.** This document changes research only.

---

# Appendix E — Submission recommendation

**Canonical repository:** mastermindx-market-intelligence/macro  
**Path:** research/NEWS_GOVERNMENT_EVENT_TO_EARNINGS_INTELLIGENCE_AUDIT_2026-10-04.md

Rationale: the canonical event, evidence, earnings, government, K3E, Theme Graph and Research Vault owners are in Macro. Protected Mastermind remains the runtime/source-law authority, but placing this research in Mastermind would separate the architecture record from the implementation owners it constrains.

**Recommended commit message:**  
research: harden event-to-earnings intelligence architecture

**Recommended PR title:**  
research: audit and harden event-to-earnings intelligence architecture

**Recommended PR posture:**  
Draft/reviewable research carrier. No merge claim, production acceptance claim, or implementation authority is created by publication.
