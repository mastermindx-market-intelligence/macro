# Communications Business Intelligence — Masterplan and First-Vertical Design

**Date:** 2026-09-23. **Revision:** 1. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794, `claude/communications-sector-research-20260923`.
**Status:** Written design for principal review; not accepted implementation, production data, a forecast, a stock recommendation or a delivered Fable commission. The Chairman has assigned the research and planning to Sol and selected Fable for final build integration. This document does not claim the build has started.

## 1. Outcome, ambition and bounded first delivery

The investor must be able to identify a financially relevant change, understand which business captures or loses economics, compare it with a genuinely dated expectation, inspect the supporting and contrary evidence, and continue into the existing company/watchlist workflow. The machine must preserve the business, financial population, source vintage, causal uncertainty and decision authority throughout that journey.

The full Communications ambition is not a directory of stocks. It is a maintained account of how attention, intent, subscription relationships, intellectual property, player spending, network capacity and contractual claims turn into earnings and equity value. The completed family research and the 94-row, 47-label business map are retained design inputs. They are not a complete global census or an admitted security universe. The moat is increasingly qualified economic interpretation and outcome learning, not the number of sources collected.

The first useful delivery answers: **Is advertising growth becoming better retained economics, and what did each business deliver against its dated outlook?** Its fixed comparison population is Meta, Alphabet, The Trade Desk and Magnite. These span owned audiences, discovery, buying services and selling services. They are not ranked investment selections or a newly admitted basket. Alphabet appears once at issuer level; Search, YouTube advertising and Network are distinct business rows, while Cloud and consolidated cash remain issuer context rather than being assigned to advertising.

The source-indexed map rows consumed first are X001–X005, X012–X014. X002 is a mechanism, not another additive revenue segment. X006 (Alphabet Cloud) can explain issuer scope but is not added to the advertising total. Record identifiers remain research navigation; Data OS and GMI supply production identity.

Three capabilities are separately accepted:

1. **Descriptive research workflow:** valid source observations, comparable arithmetic, qualified explanations and a real company journey.
2. **Operational forecasting:** hypotheses and sensitivities qualified against original-vintage future operating outcomes.
3. **Investment decision use:** additional accepted valuation, market and selection evidence under existing Prophet/portfolio/Evaluation owners.

The first delivery owes capability 1. Capabilities 2 and 3 remain explicit program obligations, not inferred consequences of a working screen.

## 2. Verified source frontier and what remains absent

Protected Mastermind procedure is `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1. The current protected master and INDEX were checked unchanged from the fully loaded ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT revision. Macro interface reads use `da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5`; this is not a rebase. The entering research head is `b3b77e50018f416eab32dbc44dc56a1cc4473c0c`.

| Source | Exact blob | Consequence for this design |
|---|---|---|
| `contracts/theme_graph/evidence.v1.schema.json` | `83dece15e98b9c8775a584afcd6ee09811dad220` | Closed evidence receipt; no structured curation assertion yet |
| `engine/theme_graph/store.py` | `63b58860d35bd183c947c85088f83bd53359bb9f` | Fixed evidence columns, keep-first identity, nightly-only writer; an extra schema field alone would be dropped |
| `engine/theme_graph/identity_resolution.py` | `8eefa1c2f5e5d3514f6487bf869f154ce2751011` | Existing GMI/Data OS bridge; parsed symbols are not downstream join keys; issuer and security resolution can differ |
| `contracts/evidence_foundation/README.md` | `a47e898309813636cf167c517492aa569aa296ca` | K1 references rather than stores bodies; unsupported cross-type composition remains refused |
| `app/market_memory.py`, selected route/auth pattern | `cf469bb0c64e0e429d721b2dde6696810314bd9f` | Existing entitled read API and private-header behavior; do not copy its unrelated fetch pools |
| `templates/state_of_themes.html.j2`, selected shell | `05017554bb9e64951d195b52583cfbd462bd2f05` | Existing Theme Tracker and stable route; no need for a replacement dashboard |
| `scripts/build_subsector_confluence.py`, `render_pages` | `d5e6b675cb5d05a15d8744c3fbf8639eecb12237` | Existing stock route shape is `stock.html#<symbol>`; route shape is not identity proof |
| `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`, selected sections | `d39c6b8a666bdd185018b8374b10e97861108e1c` | Canonical components/tokens and separate dark/light art directions |

The Phase 7 interface findings remain scoped to `8db6896dab2199a4b7fc61a005c225380cac7cd6`: Company Theme Exposure is a strict membership projection, and the eighteen-theme crosswalk supplies no direct advertising theme. The later interface reads above do not claim an estate-wide census or prove every private deployment unchanged.

Robotics PR #7773 remains draft at `f10211657c6c31df3c9af73cd4b9484e2dd7690a`. Its written design (blob `d248fd1b4c9b48df8f5c95c3bdd742c2a8ef7007`) and implementation plan (blob `d0a04e96c874395ae51cf44281039c99527dcd86`) propose the native curation extension. That proposal is a dependency to integrate, not code that this design may pretend already exists.

## 3. Architecture decision and rejected alternatives

**Selected:** one native GMI curation-assertion path, extended narrowly for financial/operating measurement; separately typed K1 references; a deterministic F04 consumer; an entitled Macro API; a compact entry in the existing shared page; existing company routes and watchlist actions.

```text
qualified source and reviewed source-scoped assertion
  -> existing GMI evidence writer/store, with accepted optional assertion payload
  -> native reader + explicit K1 curation-subtype reference and all source clocks
  -> F04 comparison of independently qualified business blocks
  -> existing Macro authentication/entitlement boundary
  -> Theme Tracker research module -> resolved existing company route
```

The source body stays with its existing approved retention/evidence owner. K1 stays pointer-only. The API composes existing owner results and writes nothing. A generated response is a derived view, never a second canonical database. No alternate registry, source crawler, refresh daemon, evidence queue, latest-state file or model gateway is introduced.

A separate Communications database/graph is rejected because it duplicates identity, revisions and authority. Overloading Company Theme Exposure with revenue weights is rejected because membership and financial dependence are different contracts. A whole-sector opportunity score is rejected because the required sensitivities, expectations and outcome validation are not established. A static essay library is insufficient because the investor cannot complete the comparison job. A narrowly shared assertion extension plus one complete comparison is the selected path.

## 4. Shared assertion amendment: precise limits

The dependency remains the proposed `theme_graph.curation_assertion.v1` payload, optional `curation_assertion` field, native evidence column/codec and K1 subtype from Robotics. Do not build a parallel Communications assertion type/store. If an accepted successor already exists at implementation time, consume it after an exact semantic comparison instead of implementing the old proposal again.

Two gaps must be resolved within that shared contract:

**Signed measures.** The Robotics plan's universal negative-quantity rejection is correct for physical counts but insufficient for losses and cash outflows. Permit finite signed values only for explicitly defined financial/operating measures whose domain allows them. Camera counts, per-robot quantities and physical capacity remain nonnegative. Negative percentages are allowed only where the definition is a change or other signed measure. Ordinary revenue, headcount and member counts retain their own domain constraints. Neither a broad sign relaxation nor a clamp-to-zero is acceptable.

**Measurement meaning.** Add one optional closed `measurement_context` section to the existing assertion payload for `REPORTED_FINANCIAL_MEASURE` and `REPORTED_OPERATING_MEASURE`. It is required when a Communications metric participates in a calculation. It is absent/null for legacy product assertions. Fields are:

| Field | Required meaning |
|---|---|
| `metric_key` | Versioned consumer-recipe-local name; not a new global metric identity |
| `definition_ref` | Immutable source/admission selector for the exact reported definition |
| `entity_basis` | Issuer, segment, business, region or other disclosed population |
| `population_ref` | Reviewed description/reference fixing the included activity and geography |
| `period_start`, `period_end`, `period_kind` | Actual inclusive reporting interval; quarter/half-year/year/instant and any exception |
| `currency`, `scale` | Currency or null for nonmoney; positive numeric unit multiplier |
| `accounting_basis` | Reported GAAP, issuer-defined adjusted, operational, or explicitly modeled |
| `value_kind` | Point, closed/open range, lower bound, upper bound, or unknown |
| `lower_inclusive`, `upper_inclusive` | Exact source inequality; irrelevant fields are null |
| `value_domain` | Signed amount, nonnegative amount/count, bounded rate or signed rate change |
| `expectation_kind` | Not applicable, company guidance, qualified consensus, or analyst scenario |
| `expectation_vintage` | Exact source publication and original/revised identity, or null |
| `comparability` | As reported, source-restated, accepted bridge, or incompatible; bridge reference when applicable |

Use the existing `observation.value`, `value_high`, unit, precision and gross/net fields; do not duplicate a second numerical truth in `measurement_context`. Point values use `value`, ranges use ordered bounds, lower/upper bounds explicitly retain their kind and inclusivity, and unknown values use null with a reason. First-release monetary inputs are integer source units; percentages use their source precision. The codec must reject nonfinite data and preserve admitted precision. Derived arithmetic uses decimal semantics and emits a decimal string plus a rounded display value; source arithmetic is not implemented through browser floating-point summation.

Guidance remains an observed issuer statement with `statement_mode=FORWARD_TARGET` and its original metric/horizon. It is not an achieved financial fact and does not register GMI as a forecast originator. Keep the shared predicate names; the statement mode makes the content's time status explicit. Scenario outputs are not admitted as reported observations.

The curation revision, exact selector, retained-source vintage, scope, review and predecessor continue to participate in the shared immutable identity. New bytes or a new selector at the same URL/date must not overwrite an earlier assertion. Additive changes preserve legacy rows and existing Robotics tests. This document proposes this narrow amendment; it does not declare the incumbent shared spec retrospectively changed or accepted.

## 5. Clocks, retention, corrections and source admission

The native evidence envelope dates the publication of house curation. Source publication and the financial reporting period remain inside the assertion with their own names; the upstream source is not made contemporaneous by today's review. Preserve source publication grain, observed/retained clocks, review due time, business applicability and correction lineage. Unknown times remain explicit unknown values.

An external URL is source navigation, not immutable retention proof. A source found on the web or cited in the research package has not thereby passed native ingestion, review, rights or publication checks. The public example fixtures in this package deliberately have no native evidence IDs or retention digests.

All accepted detailed current assertion bodies must use an already-approved private binding of the existing owner. The code and fixture path may advance while that binding is being qualified. Live admission and paid publication may not. Fable must record the actual configured native path, owner, generation/digest and public-emitter exclusion proof before admitting real rows. Do not invent a path, bucket, mirror, alternate `DATA_DIR`, or special bypass to clear this condition. The public repository's legacy evidence store must not become a leak of the new paid response.

Corrections append and invalidate affected derived results. A corrected metric is not a second independent observation or an extra persistence print. A withdrawn source retains its historical identity but cannot lead the current explanation. A changed assertion definition can invalidate comparisons while leaving the reported levels useful. The consumer never silently nets competing source interpretations.

Publication health, source recency and reporting age are separate. A Q2 report can be the latest admitted report while still describing Q2. A new source-check timestamp is not a newer economic result. If the owner has not established latest-source completeness, label the view latest accepted evidence, not latest available information.

## 6. Identity and company workflow

Use `resolve_graph_node_identity` / `read_identity_resolution` through the accepted GMI/Data OS bridge, or another explicitly accepted existing owner bridge. Do not rejoin using `source_native_symbol`, guessed CIK-to-ticker maps, display-name similarity, or research row IDs. A source label is allowed without a resolved stock binding; price, valuation, holdings and stock-navigation enrichment are not.

A resolved security does not always imply a resolved issuer. The view must retain both results. Alphabet is one business/issuer comparison with potentially several instrument choices. It must not count GOOG and GOOGL as two independent observations or add the same revenue twice. A default instrument can be used only when the existing route/identity owner supplies it; otherwise show the existing instrument selector or a qualified link state.

The inspected current US stock route shape is `stock.html#<symbol>`. Construct it only from the route-safe symbol supplied by the qualified owner result. Route syntax validation is additional to, not a substitute for, identity validation. The existing stock page owns the watchlist action; this release adds no personal portfolio endpoint and no automatic watchlist write. Acceptance includes the human-initiated existing watchlist journey and an explicit distinction between simply opening the company and saving it.

K1 v1 cannot turn a caller-authored join declaration into a supported security-subject recipe. Compile each native curation block at its evidence subject. F04 presents independently qualified blocks side by side and separately attaches a validated company-route receipt. It does not claim a unified cross-security K1 recipe passed. Unsupported cross-type joins remain visible refusals; this release does not widen K1 identity authority.

## 7. Deterministic comparison and explanation rules

Before a calculation, compare the entity/business population, metric definition, reporting interval, currency, scale, accounting and gross/net basis, source vintage and comparison bridge. The display may compare distinct business roles conceptually; numerical growth and ratios require matched populations. A same-label/same-unit match alone is insufficient.

The initial formula allowlist is small:

- Period change: current minus matched prior.
- Percentage change: `(current/prior - 1) * 100` only when the matched prior is positive and meaningful. Otherwise show absolute change and a qualified loss/turnaround explanation, not an infinite or inverted growth rate.
- Share: numerator divided by the same-scope denominator; require a documented subset relationship. An overlapping category cannot be summed into a partition.
- Guidance comparison: point or interval versus the exact originally published range/floor/ceiling, with inclusive boundaries preserved. Negative/zero reference values do not receive naive percentage surprise labels.
- Cash bridge: each named inflow/outflow exactly once, retaining company-defined formulas. A consolidated bridge is not assigned to Search or another business without allocation evidence.
- Margin: an exact named profit measure over its documented revenue or contribution denominator. Do not put unlike company-defined margins on a uniform competitive ranking.

Comparison outcomes are `COMPARABLE`, `QUALIFIED`, `INCOMPATIBLE`, or `UNAVAILABLE`. Guidance outcomes use plain statements such as within original range, below original floor, above original ceiling, or comparison unavailable. Rounding that straddles a boundary is indeterminate, not forced to a verdict. These outcomes control data interpretation; they create no investment gating or ranking power.

Every explanation has a short conclusion, its exact observed/derived supports, one economic mechanism, at least one relevant limiting or contrary observation, and the next observable condition that could change the read. A mechanism is a house interpretation and must be labeled as such. Management attribution is attributed; it is not independently verified causality. The consumer may not assert a transfer of advertising budgets from one company to another solely from differing growth rates.

The first composer uses deterministic templates and reviewed mechanism copy. No live LLM call is required for extraction, arithmetic or rendering. A later model may propose research or wording through existing review/routing owners, but never self-ratify numbers, source identity, independence, confidence, rank, size or trades. Incomplete evidence yields a narrower useful explanation rather than an invented score.

## 8. First-release evidence and expected interpretation

Public source examples were rechecked during this design pass. They remain unadmitted research fixtures. All comparisons concern the quarter ended 2026-06-30 unless a guidance publication date is named.

| Business | Required first evidence | Expected interpretation and boundary |
|---|---|---|
| Meta advertising / issuer | Impressions +14%, price +12%; issuer revenue 60,801 versus 47,516 and operating income 18,775 versus 20,441, USD millions [M2Q] | Stronger monetization can coexist with lower reported operating profit. Do not infer AI-only revenue or assign consolidated expenses entirely to ads. |
| Meta guidance/cash | Original revenue range 58,000–61,000, USD millions [M1Q]; cash reconciliation 31,862 - 30,116 - 962 = 784 [M2Q] | Actual lies inside the original range. Company FCF includes finance-lease principal; compare definitions before peers. |
| Alphabet discovery/network | Search 63,271 versus 54,190; Network 7,303 versus 7,354, USD millions [G2Q] | Owned-search and network trajectories differ. Consolidated profit, Cloud and investment income are not Search-only results. |
| Alphabet cash | 39,069 - 44,924 = -5,855, USD millions [G2Q] | Signed consolidated FCF; the current source explicitly reports this reconciliation. This improves the prior research's label from a merely computed subtotal, not its value or scope. |
| The Trade Desk | Revenue 715,057 versus 694,039; operating income 101,577 versus 116,777, USD thousands [T2Q]; original revenue floor 750 million [T1Q] | Revenue growth is not equivalent profit growth; actual is below the original company floor, not a verified analyst-consensus miss. |
| Magnite | Contribution ex-TAC 189,595 versus 161,956, USD thousands [MG2Q]; original range 177–181 million [MG1Q] | Above the original issuer-guidance ceiling; keep ex-TAC separate from GAAP revenue. Its named operating-cash measure is adjusted EBITDA less capex, not statement-of-cash-flows CFO. |

No peer total of these receipts is published: the business models, payment stages and gross/net bases differ. No blanket peer winner is emitted. Full disclosure notes and other accounting observations remain in the seven research phases; this compact fixture selects the evidence needed to test the first journey.

## 9. Consumer contract and bounded API

Proposed F04 wire contract: `communications_business_research.v1`, located beside existing market-ontology consumer contracts. Proposed composer: `engine/market_ontology/communications_research.py`. These names are design choices, not files observed at the pin.

The closed response contains: schema/version; deterministic view identity from exact source manifests and recipe version; generated time; coverage and reporting horizons; all-false authority; four fixed business/issuer panels; source-bound observed measures; derived results with formulas and input refs; independent K1 block status; identity/route receipts; qualified explanations; source/rights/freshness gaps. Missing values are null with reason. Unknown fields, nonfinite numbers and unsupported automatic-effect fields refuse validation.

`quality` is ready only when all required data for all four fixed companies is admitted and the intended journey is available. Otherwise it is partial or unavailable with a complete four-company coverage denominator. Optional unavailable consensus or valuation does not by itself make a descriptive panel fail. Removing a missing company from the denominator is forbidden. A partial release is not reported as completion of the four-company acceptance scope.

Proposed route: `GET /api/themes/communications/research/v1`, mounted in the existing Macro app via `app/communications_research.py`. It accepts no caller-supplied source URL, path, arbitrary ticker, formula, prompt, vocabulary, scenario, time cutoff or portfolio object. First version rejects unknown query parameters. Display filters are local to the already admitted response. There is no browser-time crawl or source refresh.

Authentication and `enforce_site_full(..., always=True)` run before private reads. Success, validation failure, authentication/entitlement denial and server errors retain private/no-store, noindex/noarchive, nosniff and appropriate Vary headers. Reuse existing auth/client conventions; do not copy the Market Memory module's unrelated executors/caches or introduce a token cache.

Proposed defensive limits are four issuer panels, at most 96 observed assertions, 32 derived results, 16 source descriptors, 240 characters per short narrative field, and 256 KiB encoded response. These are design budgets, not measured production performance. Oversized/unqualified results refuse or report bounded partial coverage, never truncate silently. Source reading must preserve existing owner resource and concurrency controls.

## 10. UI composition without dashboard inflation

Retain `state_of_themes.html` and its theme-state calculations. Add one compact Research dossiers entry outside the scored canonical-theme collection; do not add a nineteenth theme or modify counts, sorting, cards, lanes, recommendations or the existing builder's calculations. The research label is Communications / 通讯, with Advertising economics / 广告业务经济性 as its initial dossier.

The proposed anchor is `#communications-research`. It opens the existing shared detail interaction, or a small shared-template-owned disclosure module if no accepted reusable interaction exists at implementation. This is not permission for a Communications-only shell or design system. When closed, only the compact entry occupies board space. Full comparison content is fetched after deliberate opening; direct hash navigation counts as opening. Do not add a permanent large hero, diagram or four-column table to the board's default height.

Inside the open research view, the first tier answers what changed, why it matters and what to inspect next. One conclusion and two decisive measures per business precede the expandable financial/evidence detail. Order follows disclosed economic roles, not an attractiveness ranking. A user can align business scopes without implying the numerical definitions are identical.

Desktop may use a role comparison table with semantic row headers; mobile uses the same data in stacked expandable sections. No inaccessible sideways-only matrix. Evidence detail shows period, unit, formula, definition, upstream source date, curation date and limitations. Links come from validated source and route descriptors; source text is escaped, never rendered as executable HTML. URL filters contain only public topic/selection identifiers, never credentials or private response bodies.

**Dark treatment:** canonical dark materials with restrained depth, quiet separators and measured text inks; no animation implying data is live. **Light treatment:** canonical light canvas and white panels, visible hairlines and shadow hierarchy instead of copying dark glow. Layout, semantic state and business meaning remain the same. Use existing tokens and components; new hex palettes, new fonts, runtime stylesheet injection and third navigation families are out of scope.

EN/ZH parity covers business meaning, accounting definitions, date formats, units, missing states and action labels, not just headings. Financial growth sign is textual and semantic coloring follows existing direction rules; access/quality warnings do not flip meaning with locale. Keyboard focus, close/back restoration, reduced motion and screen-reader table/disclosure names are required. A 390-pixel mobile viewport and a 1440-pixel desktop viewport are the proof targets, in both languages and both themes.

On logout, entitlement loss, navigation away or restored browser page, clear or revalidate private view state using the existing auth/session signals. Do not retain a paid payload in localStorage, IndexedDB, service-worker cache, public HTML, source maps or downloadable public fixtures. Theme/language preferences may continue to use existing preference storage. This is not a promise to prevent an authorized reader from manually copying what they are allowed to see.

## 11. Freshness, refresh and failure behavior

Existing source ingestion and GMI admission own refresh. No Communications cron, worker watcher or direct provider call is created. The API reads the accepted generation and a refresh does not transform research text into admitted facts. A failed refresh leaves prior owner evidence historically visible with its quality state; it does not overwrite missing values with zero or mark an old report fresh.

The first view makes one request on open and offers explicit retry/reload when appropriate through existing client policy. It does not poll unchanged state. A correction to a source invalidates only dependent values and explanations. A source-generation change during composition produces a coherent verified input vector or a partial/unavailable result; mixed unseen generations are not silently accepted.

Failures are scoped: one unavailable prior-period metric disables its change calculation, not the observed current level; one unresolved security disables its stock link/enrichment, not the source-attributed business description; rights refusal suppresses the affected content before serialization. Missing required retained evidence or review prevents a panel being ready. Existing Theme Tracker continues when the new module is unavailable.

## 12. Full-program economic, lifecycle and valuation design

The broader system retains family-specific mechanisms from the research rather than copying advertising formulas everywhere.

| Family | Leading economic question | Lifecycle transition to investigate | Main expansion qualification |
|---|---|---|---|
| Search/social/advertising | Is advertiser value becoming retained revenue and cash? | Adoption -> profitable monetization | Comparable spend, monetization and serving-cost evidence |
| Streaming/video | Is cohort contribution replenishing content investment? | Subscriber scale -> retained contribution | Bundle populations, content cash/amortization and rights season |
| Music/IP/agency/publishing | Who owns/controls economics and who keeps productivity gains? | Rights/audience -> recurring retained fees | Contract scope, advances, pass-through and direct relationships |
| Gaming | Do valuable payer cohorts recover development and creator investment? | Launch -> durable player contribution | Payer/recognition/platform definitions and failed-title cohorts |
| Terrestrial networks | Do local cohorts repay build, service and funding cost? | Build -> activation -> mature cash | Geography, capacity, penetration, legacy shutdown and partner claims |
| Satellite/D2D | Does accepted service capacity fund its replacement and obligations? | Demonstration -> paid useful service | Deployment, contract, utilization, replacement and funding evidence |

Current base, incremental sensitivity and conditional opportunity remain separate for each business. Macro inputs are hypotheses about demand, discounting, credit, FX and capital requirements, not a universal sector regime label. Geography means operating demand, costs/assets, currency, legal entity and listing separately. Each family retains its own observation lag and lifecycle criteria.

Valuation research distinguishes matched-horizon earnings revisions from multiple changes, and project value from equity claims. Loss-making/deployment-stage cases use explicit cash, replacement, financing and dilution scenarios, not a forced P/E. No current fair-value estimate or probability is invented by this release. Sensitivity ranges require a source or an accepted model; unknown ranges remain unknown.

The 47-label map is the starting coverage set. China/HK, Canada and other regional expansions preserve source definitions and local business structures. Prior 2022 Netflix, Concord and Frontier cases remain historical study inputs rather than proven trading rules. Telesat backlog composition, China Mobile access, broadcasting breadth and later transaction status remain explicit claim-specific gaps.

## 13. Learning and proactive intelligence without a second outcome system

Descriptive observations can be archived under their native owners now. Conditional operating forecasts enter the existing forward-claim/evaluation owner only through its accepted admission. Do not put every descriptive assertion into QLedger or create a Communications outcome database. A theory about retained economics is not a trade instruction.

The proposed validation sequence is: freeze the hypothesis and horizon; preserve original sources and revisions; establish what was knowable when; qualify the expectation basis; retain failed/delisted cases and point-in-time identities; evaluate incremental information over simple operational and market baselines; then test decision utility separately. Original-guidance comparisons are not analyst consensus. Historical reconstruction using today's research map is not contemporaneous belief.

Do not derive an intraday trading surprise from a date-only source time. Same-day uncertain timing stays uncertain. Release-day prices, later accounting revisions and later known winners cannot be backfilled as predictor inputs. Walk-forward evaluation, country/currency/industry cohorts and multiple-testing controls belong to the incumbent evaluation owner. No forecast edge is claimed from the arithmetic examples in this packet.

When accepted future evidence establishes a material change, existing intelligence-delivery consumers can use the read-only explanation and its exact provenance. Priority ordering, alert cadence and audience delivery remain with their existing owners. This commission does not build a new alert queue or allow model sentiment to size trades. The ambition of proactive useful intelligence survives; activation depends on qualified interfaces rather than a new control plane.

## 14. Phased delivery and ownership

The companion plan details the first advertising vertical. Fable is the intended principal integrator, preserving architecture and adjudicating collisions, privacy, returns and final acceptance. Routine engineering belongs to eligible bounded workers through existing capacity and custody law. This written design is not a dispatch or worker START.

| Delivery unit | Named useful result | Dependency/proof |
|---|---|---|
| Shared prerequisite | One native typed assertion path supports physical and financial evidence without leakage | Shared Robotics/GMI owner accepts the narrow amendment; round-trip and private binding |
| A1: advertising comparison | Four-company real-input comparison reaches company/watchlist workflow | Native evidence, identity, paid API, visible browser proof |
| A2: regional platform comparison | China/Korea platform activity is comparable at its actual reporting grain | Exact identities, definitions, rights and bilingual proof |
| M1: streaming/rights | Retention/content/royalty mechanisms connect to issuer cash | Content and contract evidence; full-season and cohort definitions |
| G1: gaming | Player spending, recognition and development economics stay distinct | Accepted gaming measures and negative launch cases |
| N1: connectivity | Local network and customer cohorts explain capital returns | Footprint/period/partner/funding qualifications |
| S1: satellite | Usable capacity and commitments explain conditional economics | Contract/milestone and replacement/funding evidence |
| E1: outcome-qualified intelligence | Accepted operating forecasts and later decision use | Incumbent evaluation proof, original-vintage histories and separate authority promotion |

Each unit should be a useful vertical slice with a consumer and proof, not a succession of infrastructure-only PRs. Do not require all later research gaps to close before A1. Do not call A1 completion full-sector completion. Reuse the shared template and assertion path across units; a new family changes economic definitions, not the control architecture.

## 15. Acceptance, review and closeout

The companion plan maps CRV-01 through CRV-40 to tests/proofs. They are written requirements, not executed application passes. First-live acceptance requires all four issuer journeys from admitted real sources, the correct period/formulas/limitations, working resolved company navigation, existing watchlist completion, qualified degraded states and negative proof at alternate publication paths. Independent review and exact-head release checks remain mandatory when release is sought.

Required browser matrix is dark/light x EN/ZH x desktop/mobile, with representative entitled, anonymous, free-tier, expired-session, missing-source and corrected-source states. Server access decisions must precede owner reads. Every live data artifact has its actual owner/source generation and release identity; screenshots from fixture pages cannot stand in for production proof.

This phase produces the written design, scoped build plan and source-based reference examples only. It does not execute application tests, claim source admission, resolve the four live identity rows, qualify the private store binding, merge this research PR, or start Fable. These omissions are explicit execution dependencies with named owners, not a claim that the tools are unavailable.

## 16. Public source register for the first example pack

These primary sources were opened on 2026-09-23. The short numeric examples and original paraphrases are research, not whole-document ingestion. Actual production retention/display rights remain separate. Source publication dates are not fixture creation dates.

- **M2Q:** Meta Q2 results, 2026-07-29; highlights, segment revenue and cash reconciliation. https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm
- **M1Q:** Meta Q1 results, 2026-04-29; original Q2 guidance. https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-First-Quarter-2026-Results/
- **G2Q:** Alphabet Q2 results, 2026-07-22; category revenue and reported consolidated FCF reconciliation. https://www.sec.gov/Archives/edgar/data/1652044/000165204426000066/googexhibit991q22026.htm
- **T2Q:** The Trade Desk Q2 results, 2026-08-06; statements of operations. https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-Second-Quarter-2026-Financial-Results/default.aspx
- **T1Q:** The Trade Desk Q1 results, 2026-05-07; original Q2 guidance. https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-First-Quarter-2026-Financial-Results/default.aspx
- **MG2Q:** Magnite Q2 results, 2026-08-05; contribution ex-TAC reconciliation and definition footnotes. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-second-quarter-2026-results
- **MG1Q:** Magnite Q1 results, 2026-05-06; original Q2 guidance. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-first-quarter-2026-results

The prior seven phases and their source registers remain at the incumbent carrier. The first example pack does not retroactively qualify every prior source, coefficient or historical claim. Exact native source paths and blobs are in section 2; all proposed new file/API/schema names in this document are design choices and must not be cited as existing implementation.
