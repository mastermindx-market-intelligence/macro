# Sector, Theme, Subtheme and Subsector Intelligence System — Architecture Design

**Date:** 2026-09-20
**Status:** Chairman-approved in-chat direction; written architecture for review. This document creates no implementation, deployment, prediction, ranking, gating, sizing, portfolio, or trading authority.
**Operation:** `sector-theme-subtheme-intelligence-architecture-20260920-sol-001`
**Protected Sol Skillpack:** `mastermindx-market-intelligence/Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`, `mastermind.sol_skillpack.v1` v1.0.1, bootstrap-major 1 compatible.
**Macro architecture pin:** `6eb92c17d73a285f494f59f51427ffcd416dfc5b` (the only movement after the audited `efee0b56978d2e98d2c40e87744431c8c54309d2` pin was path-disjoint `data/research_vault/catalog.json`).
**Canonical organizational owners:** Neural Web federation and authority governor; GMI Theme Graph and ThemeState; specialist sector/subsector/theme engines; MarketOntology F04 product composition; Prophet final technical selection; existing publishers and Evaluation OS.

---

## 0. Executive ruling

Mastermind should not build another sector dashboard, another theme score, or a fourth semantic graph. It should turn the existing sector, subsector, canonical-theme, source-local-subtheme, basket and security intelligence into one coherent hierarchy of read-only product projections.

The selected architecture is an **owner-preserving intelligence federation with page-specific projections**. Existing engines continue to own their facts. Existing identity, evidence, lifecycle, entry, ranking, publication and evaluation owners remain canonical. A shared read layer resolves clocks, quality, relationships and disagreements so every page can explain the same market state without flattening distinct timeframes or scopes into a magic score.

The target user outcome is:

> A serious investor can start at the market or sector level, identify the actual leadership chain, understand whether it is broad or concentrated, distinguish thesis health from entry quality, drill through subsector, theme and subtheme to the supporting companies, see where fresh owner reads disagree and why, and know exactly what evidence would change the interpretation.

The machine outcome is:

> Mastermind composes source-bound, correction-safe, freshness-aware and authority-safe intelligence across `sector → subsector → canonical theme → source-local subtheme → company/security`, preserving every owner dimension and exposing typed conflicts instead of silently averaging them.

Real completion is not a document or a merged foundation. It requires truthful current inputs, a coherent real-state journey on every named page, accepted source-owner integration, deployed browser proof, and domain-specific outcome learning where a predictive or decision-bearing claim is made.

---

## 1. Current capability ledger at the architecture pin

| Capability | State | Governing interpretation |
|---|---|---|
| Consolidated US Sector Intelligence hub | `PARTIAL` | The one-page hub and its major organs exist, but current-generation coherence and publication freshness remain separately unproven while PR #7211 is open. Do not reopen the 2026-08 consolidation. |
| Sector detail pages | `PARTIAL` | ETF cycle, entry, rates, dollar, accumulation, alpha and holdings exist; internal sector decomposition, connected themes, evidence quality and contradiction synthesis do not. |
| Subsector Confluence overview/detail | `PARTIAL` | Entry timing, regime, synthetic group tape, member gates and reliability exist. Economic meaning, parent contribution, persistent leadership, connected themes/subthemes and change intelligence are incomplete. |
| Theme Tracker / ThemeState projection | `PARTIAL` | Lifecycle, thesis, pathways, setup legs, evidence and change tape exist. The current semantic repair in PR #7526 is `BUILT_NOT_PROVEN`, and theme cards do not yet lead into a complete theme dossier. |
| Theme detail pages | `PARTIAL` | Timing, score, group read, cycle, earnings, members and membership history exist. ThemeState thesis health, pathway, evidence, connected hierarchy and typed conflicts are not integrated. |
| GMI canonical/local Theme Graph | `PROVEN_LIVE` substrate | Canonical themes, source-local themes, bitemporal edges, capability sidecar, rights registry and latest-belief readers exist. It remains the sole identity/provenance spine. |
| Source-local subtheme leadership | `BUILT_NOT_PROVEN` | PR #7455 adds closed-session leadership observations with strength, acceleration, persistence, participation, dispersion and concentration; integration, merge, deployment and predictive qualification remain open. |
| Source-bound group/member evidence | `BUILT_NOT_PROVEN` | PR #7252 provides member observations and honest missingness on group-detail pages; publication and deployed acceptance remain open. |
| Fail-closed group entry context | `BUILT_NOT_PROVEN` | PR #7508 preserves group entry and stock eligibility as separate dimensions without changing Board V2 ranking. Lane A integration and release remain open. |
| House Theme Atlas | `BUILT_NOT_PROVEN` | PR #7283 defines Matrix, Clusters, Bubbles and Table over accepted group observations. It remains stacked behind its source dependencies and must not be copied into another explorer. |
| Coherent sector-intelligence publication | `BUILT_NOT_PROVEN` | PR #7211 owns strict producer ordering, generation hashes and focused publication. No second workflow or publisher is permitted. |
| `sector_intelligence_packet.v1` federation | `SPEC_ONLY` / interface-only | The contract and ownership registry exist, but no accepted operational producer composes current owner facts into the packet. |
| Cross-page contradiction explanation | `NOT_BUILT` | Different pages can expose different states without explaining timeframe, scope, freshness, coverage or authority differences. |
| First-class subtheme pages | `NOT_BUILT` | Source-local identity and membership exist in Theme Graph, but no governed user-facing dossier exists. |
| Direct rank/size/gate/trade authority from this program | `REJECTED_BY_DESIGN` | Descriptive composition cannot self-promote into Prophet, portfolio or trading authority. |

### 1.1 Active carriers that this design must consume, not duplicate

- **PR #7526 — Theme Intelligence Lane A.** Owns the `WATCH` versus deterioration repair, correction-safe two-print logic, `PRECIPICE` interpretation and additive `theme_intelligence.consumer.v1` dimensions.
- **PR #7455 — Lane C leadership/subthemes.** Owns closed-session leadership observations and the current semiconductor subtheme proof. This design does not recreate those calculations.
- **PR #7508 — Lane D entry routing.** Owns fail-closed group/member entry context and preserves Board V2 policy. Parent entry state may never be inherited as stock eligibility.
- **PR #7252 — source-bound member evidence.** Owns the group-member observation contract and the current group-detail evidence journey.
- **PR #7283 — House Theme Atlas.** Owns the four comparison representations and display-filter semantics.
- **PR #7211 — publication freshness.** Owns the focused publisher, generation binding and production freshness proof path.

All six remain separate lifecycle carriers. This architecture references their accepted contracts only after each clears its own release gates.

---

## 2. Alternatives considered

### 2.1 Independently improve each page

This would deliver quick visual polish but preserve incompatible vocabularies, page-local clocks, duplicated calculations and unexplained contradictions. It is rejected because it improves presentation without improving system intelligence.

### 2.2 Shared owner-preserving federation with page-specific projections

This activates existing federation contracts, uses ThemeState and Theme Graph as canonical thematic owners, keeps specialist engines authoritative, and gives each page a coherent view of the same relationships, clocks, quality and disagreements. This is the selected architecture.

### 2.3 Merge every function into Sector Central

This would overload an already large hub, duplicate detail-page responsibilities, weaken deep links and make browser/build complexity worse. It is rejected. Sector Central is the command center and router; detail pages remain the depth surfaces.

---

## 3. Product ontology and hierarchy

The product must preserve six different object types:

1. **Sector** — structural economic or allocation grouping, commonly represented by a sector ETF and constituent roster.
2. **Subsector/group** — operating industry or internal leadership group below a sector, including accepted curated group families.
3. **Canonical theme** — a governed economic narrative and thesis in GMI vocabulary.
4. **Source-local subtheme** — a source's concept at the source's own grain, such as a Finviz subtheme or THS concept. It is not canonical vocabulary by default.
5. **Basket** — a price/measurement surface. It may be the primary expression of a theme or only a proxy/supply-chain surface.
6. **Company/security** — issuer and tradable instrument identities, which must remain distinct where the canonical identity owner distinguishes them.

### 3.1 Relationship laws

- `sector CONTAINS subsector` is structural only when an accepted roster/taxonomy owner supplies it.
- `security MEMBER_OF group` retains membership basis, observation/validity interval and current coverage.
- `basket EXPRESSES canonical_theme` is the canonical theme-price relationship; the direct primary basket and supplemental/proxy baskets remain explicitly different.
- `security MEMBER_OF local_theme` may be displayed only according to the source-family rights registry and its own provenance.
- `local_theme RESOLVES_TO canonical_theme` exists only when a curated accepted relation says the vocabularies match. Similar labels or overlapping members are not enough.
- A company-to-theme association derived by composing membership and expression is a **view-time derived claim**, with both source references visible. It is not silently persisted as a new graph fact.
- Cross-sector or cross-theme overlap does not imply causal transmission, independent confirmation, or predictive edge.
- Current-membership historical price calculations remain labelled non-PIT unless the producer proves otherwise.

### 3.2 Stable routes

The architecture retains existing sector, subsector, basket and stock routes. New source-local pages use stable source-bound routes:

```text
subthemes/finviz/<subtheme_key>.html
subthemes/ths/<concept_code>.html
```

The page title may follow the current source label, but the route identity follows the stable source key/code. A rename changes display text, not identity.

---

## 4. Shared read architecture

The system uses a family of existing-owner contracts rather than one universal score or replacement store:

- `sector_intelligence_packet.v1` for governed sector-level federation;
- `theme_intelligence.consumer.v1` for Theme Intelligence dimensions after PR #7526 acceptance;
- `subsector_rotation.closed_session_leadership.v1` for accepted leadership observations after PR #7455 acceptance;
- `group_member_observations.v1` for group/member evidence after PR #7252 acceptance;
- existing group `entry_context` after PR #7508 acceptance;
- ThemeState for canonical theme state;
- Theme Graph latest-belief readers for identity, source-local membership, capability and provenance;
- incumbent outcome/evaluation contracts for calibration.

A deterministic **entity read adapter** composes these owner outputs at build/read time. It may serialize into the incumbent page payload owned by that builder, but it does not become a new canonical database, state machine, event log, publisher, queue or scheduler.

### 4.1 Common view grammar

Every page-level read view exposes the applicable subset of:

```text
identity
relationships
current_dimensions[]
material_changes[]
drivers[]
participation
concentration
coverage_quality
freshness
conflicts[]
watch_conditions[]
outcome_context
source_records[]
authority_caps
```

A dimension is named and owner-bound. Examples include thesis health, lifecycle stage, entry context, cycle state, parent-relative leadership, participation, crowding, macro sensitivity and evidence sufficiency. Dimensions are never fused merely because they share a page.

### 4.2 Conflict grammar

The adapter classifies disagreements before rendering them. A conflict record contains the dimension, two or more owner observations, clocks, coverage, authority, explanation and resolution state.

Allowed classes are:

- `ALIGNED` — comparable observations support the same interpretation.
- `TIMEFRAME_SPLIT` — short, medium or long horizons differ without invalidating one another.
- `SCOPE_SPLIT` — parent sector, child group, theme, subtheme or member differs because the populations differ.
- `FRESHNESS_SPLIT` — an older observation conflicts with a newer one; the older value remains visible but cannot lead the synthesis.
- `COVERAGE_SPLIT` — one read is partial/thin while another has broader coverage.
- `AUTHORITY_SPLIT` — context-only and decision-bearing owners have different roles; context cannot overrule the owner.
- `GENUINE_CONTRADICTION` — fresh, comparable, sufficiently covered owner observations disagree materially.
- `UNAVAILABLE` — the evidence needed to compare is absent or ineligible.

The UI must explain conflicts in plain language. Examples:

- **Thesis intact; entry poor.** Economic evidence is improving, but price participation is narrow and the group is extended.
- **Sector mixed; subtheme strong.** The parent technology sector is not broadening, while memory and compute are accelerating relative to semiconductors.
- **Current signal newer than theme card.** The theme card is stale and cannot lead until its producer advances.

No conflict class is a trade signal, rank or probability.

### 4.3 Time, freshness and correction law

Each observation preserves at least:

- observation/session time;
- generated/computed time;
- knowledge or belief cutoff where the owner supplies one;
- current/stale/partial/missing health;
- source generation or content hash where publication coherence requires it.

Same-session corrections supersede within the owner's contract rather than becoming a second independent confirmation. Distinct dated observations may satisfy persistence/two-print rules only when the owner contract allows it.

A page-level `as of` cannot launder mixed clocks. The page shows the coherent decision horizon and exposes older or lagged dimensions individually. Missing dates remain unknown; checkout/file modification time is never market-data freshness.

### 4.4 Null, false and zero

- Missing data remains `null`/unavailable, never zero.
- `false` means the owner observed and rejected a predicate.
- `0` is a measured numeric value.
- Partial coverage carries the measured numerator, denominator and reason.
- A source-local concept with semantic identity but no accepted measurement remains useful as `semantic_only`; quantitative sections render “not measurable yet.”
- An unavailable production-only source is not described as globally absent.

---

## 5. Common user experience grammar

Every deep intelligence surface follows one recognizable sequence. Not every section appears at every grain, but the meaning and ordering stay stable.

1. **Identity and scope** — what the object is, its parent/children, direct versus proxy expressions, and the current observation horizon.
2. **What changed** — only material transitions since the last accepted owner observation.
3. **Current read** — separate named dimensions with a plain-language synthesis.
4. **Internal composition** — participation, concentration, dispersion, contributors and detractors.
5. **Connected hierarchy** — related sectors, subsectors, canonical themes, source-local subthemes, baskets and members with relationship basis.
6. **Conflicts and missing evidence** — typed disagreement and honest unavailable states.
7. **What would change the read** — observable watch conditions. Front-facing product copy does not use “falsified,” “refuted,” or similar terminal language.
8. **History and outcome context** — only domain-valid cohorts and calibration.
9. **Evidence receipt** — source, clock, coverage, correction and authority detail.

The glance tier answers three questions under a strict word budget: **what is happening, why it matters, and what posture follows**. Technical state names and raw slugs stay in detail/receipts.

---

## 6. Intelligence capabilities

### 6.1 Parent-relative decomposition

Every sector and group explains what is supporting or dragging it. The system distinguishes absolute movement from movement relative to the parent and benchmark. It must show when a parent looks healthy only because one concentrated child is strong.

### 6.2 Participation, dispersion and concentration

A two-stock rally cannot read like broad leadership. Views expose:

- measured/eligible members;
- advancing or confirming participation;
- return/signal dispersion;
- concentration of contribution;
- equal-weight versus cap-weight divergence where both owners exist;
- thin/sparse/new/stale coverage;
- the members responsible for the read.

### 6.3 Persistent versus transient leadership

Accepted owner observations separate one-session movement from:

- strength level;
- acceleration;
- persistence;
- parent-relative leadership;
- reclaim or volume confirmation;
- 1/3/5/10/20/60 completed-session windows.

The product never converts descriptive persistence into predictive authority without Evaluation acceptance.

### 6.4 Material-change intelligence

A change enters the page tape only when an owner observation records a material transition, including:

- lifecycle/stage transition;
- leadership handoff;
- participation regime change;
- concentration shock;
- new or cleared watch condition;
- evidence contradiction;
- freshness degradation or recovery;
- entry context deterioration or qualification;
- thesis-versus-price decoupling.

### 6.5 Evidence sufficiency

Each synthesis names whether evidence is:

- complete;
- partial;
- thin;
- stale;
- conflicted;
- missing;
- non-PIT/current-membership;
- rights-restricted;
- not yet measurable.

Confidence language describes evidence sufficiency, not a model probability, unless the displayed value comes from an accepted calibrated owner.

### 6.6 Regime and causal context

Sector and theme views may consume accepted rates, inflation, dollar, policy, earnings, commodity, options and physical-demand observations. Each remains a named driver with its own method and clock.

Membership overlap, correlation or common movement is not causal transmission. Causal or propagation language requires the accepted relationship/MarketOntology owner and supporting evidence. Otherwise the page says “associated,” “co-moving,” “exposed through,” or “consistent with.”

### 6.7 Outcome learning

Sector ETF states, synthetic subsector indices, thematic baskets and source-local subthemes are separate evaluation domains. A result calibrated on SPDR sectors cannot validate a subsector or theme.

Where a forward claim is eventually proposed, the existing evaluation owner must measure at minimum:

- absolute and benchmark-relative return;
- drawdown and adverse excursion;
- persistence/retention;
- false-alert rate;
- calibration by regime and coverage tier;
- distinct-episode honest N;
- correction and membership-basis sensitivity.

---

## 7. Page architecture

### 7.1 Sector Central — command center and router

Sector Central remains the single US hub. It does not absorb the full detail pages or Atlas.

The existing rail remains recognizable: Overview, Map, What's Moving, Money & Breadth, Explore and Confluence. The semantic upgrade is:

- **Overview:** current leadership regime, material changes, sector handoffs, emerging child groups/themes, principal conflicts and generation health.
- **Map:** sector/theme position and cycle context with one vocabulary bridge; no duplicate ranker.
- **What's Moving:** persistent versus transient movement, child leadership and forming narratives.
- **Money & Breadth:** participation, equal/cap-weight divergence, concentration and flow context.
- **Explore:** sortable descriptive inventory and direct links to dossiers/Atlas.
- **Confluence:** accepted entry-timing and member-routing surfaces, explicitly separate from thesis health and long-horizon leadership.

Every sector row/card exposes:

```text
current state
material change
dominant driver
participation/coverage
strongest supporting child
largest conflict/risk
freshness
sector dossier link
```

Sector Central may summarize child themes and groups, but their detail remains on their owner pages.

### 7.2 Sector detail — full sector dossier

The current ETF-oriented page becomes a sector intelligence dossier while retaining its useful cycle and execution organs.

First viewport:

- sector identity and benchmark/ETF representation;
- plain-language sector state;
- what changed since the previous accepted observation;
- principal driver;
- participation and concentration;
- strongest child group and largest drag;
- current posture and freshness.

Depth sections:

1. **Internal leadership tree** — child subsectors/groups by state, change and contribution.
2. **Breadth and structure** — participation, dispersion, concentration, equal/cap-weight divergence and top-name contribution.
3. **Connected themes/subthemes** — canonical themes and source-local concepts with relationship basis and rights-safe links.
4. **Macro transmission context** — existing rates, inflation and dollar reads plus accepted policy/commodity drivers.
5. **Execution context** — existing cycle, entry setup, chart, accumulation, alpha leaders and holdings.
6. **Conflicts and watch conditions** — typed disagreements and observable conditions that would change the read.
7. **Evidence and outcomes** — source clocks, quality, corrections and sector-domain calibration only.

A sector dossier answers “what is happening inside Technology?” rather than only “how is XLK trading?”

### 7.3 Subsector overview — leadership and timing map

The existing Confluence overview keeps its accepted entry-timing machinery and adds distinct descriptive leadership dimensions:

- current entry context;
- parent-relative leadership;
- acceleration and persistence;
- participation, dispersion and concentration;
- reliability and source coverage;
- parent-sector agreement/conflict;
- material change since the last observation;
- direct links to group and connected-theme dossiers.

The board must not imply that the freshest entry tier is automatically the strongest economic theme. Sorting controls state which dimension they use; changing the display does not recompute the analytical population.

### 7.4 Subsector detail — operating-group dossier

The detail page retains its synthetic chart, group entry/regime read and member table, then adds:

- plain-language definition and structural parent;
- contribution to parent-sector performance and participation;
- accepted multi-window leadership observations;
- concentration and dispersion;
- connected canonical themes and source-local subthemes;
- member attribution: leaders, laggards and signal concentration;
- recent state/change tape;
- typed conflicts and missing evidence;
- source, calendar, membership-basis and corporate-action caveats;
- group-domain outcome context when accepted.

SPDR sector base rates are never presented as subsector proof. Current-membership synthetic history remains explicitly non-PIT where applicable.

### 7.5 Theme Tracker — thesis-health board

Theme Tracker remains the canonical board for thematic thesis health. It adopts the accepted semantics from PR #7526 rather than inventing another lane model.

Each card adds:

- a direct theme-detail link;
- thesis health and entry quality as separate labels;
- one “why this changed” line;
- evidence freshness/coverage state;
- connected leading subthemes when accepted;
- conflict badge when price, evidence and participation disagree;
- plain-language watch conditions.

The existing research-priority list remains a reading order, never attractiveness, expected return or trade priority.

### 7.6 Theme detail — thesis plus execution

Theme detail combines two currently separated product halves.

**Thesis and evidence:** Theme Tracker lane, lifecycle, variant perception, economic mechanism, pathway, watch conditions, evidence references, freshness, contradictions and connected hierarchy.

**Execution and expression:** primary versus proxy baskets, timing/cycle, entry quality, crowding, holdings, earnings, group episodes, membership changes and governed Prophet presence.

The page states the central distinction explicitly:

> A healthy thesis is not necessarily a clean entry. A clean entry is not proof of a healthy thesis.

### 7.7 Source-local subtheme explorer and dossiers

Subthemes become first-class read-only product pages over the accepted Theme Graph local-theme plane. They do not become canonical themes merely because they have pages.

Each dossier shows:

- source-local identity, current label and source family;
- capability state: `semantic_only`, `measurement_candidate` or `measurable`;
- parent source grouping and curated canonical-theme relations, if any;
- structural sector/subsector relationships where supported;
- rights-safe member roster or an explicit rights-restricted state;
- current leadership level, acceleration and persistence when accepted;
- participation, dispersion, concentration and missing-member coverage;
- first/last observed membership intervals and correction status;
- sibling concepts and related primary/proxy baskets;
- evidence receipts and all-false authority caps.

Rights behavior is fail-closed. The current `config/theme_sources.yml` registry determines whether labels, aggregate counts, relationships or member structure may be emitted. A historical row's embedded rights snapshot cannot override the current registry.

A semantic-only concept still receives a useful identity/relationship page. Quantitative sections say “not measurable yet” and explain the missing substrate.

### 7.8 Theme Atlas and heatmaps

The House Theme Atlas remains the compare/discover surface owned by PR #7283:

- Matrix;
- Clusters;
- Bubbles;
- Table.

Atlas controls are display filters only and never alter the measured source population. Missing axes withhold points rather than zero-filling them. Circle proximity is not correlation or causality. Size is never labelled market cap unless the accepted capitalization owner supplies qualified coverage.

Atlas and legacy heatmaps link into canonical-theme, source-local-subtheme and group dossiers. They do not reproduce thesis, evidence, entry or member-detail sections.

---

## 8. Navigation and journey continuity

The global authenticated nav remains owned by `_site_nav.html.j2` / `_navlinks.html.j2`. No third header or local navigation system is introduced.

Required bidirectional journeys are:

```text
Sector Central ↔ sector dossier
sector dossier ↔ child subsector dossier
sector/subsector dossier ↔ canonical theme detail
canonical theme detail ↔ source-local subtheme dossier
all group/theme/subtheme pages ↔ supporting stock/security page
Theme Atlas ↔ theme/group dossiers
```

Every relationship link includes a short basis such as “structural child,” “primary theme basket,” “supplemental proxy,” “source-local membership,” or “curated vocabulary resolution.”

Back links return to the originating context when available and to the canonical hub otherwise. Hash routes and direct URLs remain loadable independently.

---

## 9. Visual and interaction architecture

The implementation follows `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`, `research/DESIGN_MIGRATION_FACTORY_V1.md` and `docs/DESIGN_DOCTRINE.md`.

### 9.1 Shared semantics, distinct art directions

Dark and light share information architecture, state meaning, spacing/type scale, actions, interaction and data contracts.

- **Dark treatment:** command-center depth, restrained luminance hierarchy, quiet instrument surfaces and limited semantic glow.
- **Light treatment:** research-workspace canvas, white material, disciplined hairlines, cooler evidence surfaces and shadow instead of glow.

Token substitution alone is not acceptance. Each material slice requires dark/light × EN/ZH × desktop 1440/mobile 390 evidence.

### 9.2 Progressive disclosure

- Glance cards contain state, change, why and posture.
- Evidence, technical details and methods live in drawers/popovers or dossier depth.
- Raw engine enum names, slugs and untranslated statistics never appear at rest.
- Null/missing/partial states receive plain-language glance copy plus a technical receipt.
- Front-facing language uses “what would change the read” and “what we are watching,” not terminal falsifier/refutation language.

### 9.3 Density and performance

The hub must not inline every member roster or duplicate detail-page payloads. Heavy tables, Atlas views, time-machine data and long evidence lists mount lazily through existing asset conventions.

Page-specific budgets are set in each implementation packet from measured current baselines. No slice may materially increase nightly heavy compute without moving the work to an accepted owner/path outside the render-critical lane.

Substantive styling remains in governed CSS/templates, not opaque runtime `style.textContent` systems or parallel token families.

---

## 10. Data flow

```text
canonical specialist producers
    │
    ├── sector/cycle/breadth/rates/flow owners
    ├── subsector confluence + leadership owners
    ├── ThemeState + thesis + evidence owners
    ├── Theme Graph identity/rights/latest-belief readers
    ├── group/member evidence + entry-context owners
    └── outcome/evaluation owners
            │
            ▼
owner-preserving read adapters
(no new truth, no fused score)
            │
            ├── sector_intelligence_packet.v1
            ├── theme_intelligence.consumer.v1
            ├── group/subtheme read dimensions
            └── conflict/freshness/quality classifications
            │
            ▼
incumbent builders and payloads
            │
            ▼
Sector Central / sector / subsector / theme / subtheme / Atlas views
```

The first accepted producer-to-consumer slice must include a real owner input, deterministic adapter, actual page consumer, discriminating tests and browser evidence. A schema alone is not a capability.

---

## 11. Failure and degradation behavior

- Missing canonical identity blocks the identity-dependent section, not unrelated page sections.
- Unreadable latest-belief Theme Graph data fails the affected relationship view closed; the page does not fall back to raw append-only rows.
- Rights failure hides or degrades the restricted structure and names the current rights state.
- Stale owner observations remain visible only with stale status and cannot lead a fresh synthesis.
- Mixed-generation data creates a visible generation conflict and blocks a coherent headline if the headline depends on the mismatched fields.
- Partial membership preserves the measured denominator and missing identities; it never shrinks the population to manufacture completeness.
- Adapter failure cannot rewrite or mutate owner artifacts.
- Page render failure preserves the last-good page according to the incumbent builder's policy while publication validation remains red/degraded.
- A conflict classifier that lacks comparable clocks or scope returns `UNAVAILABLE`, not `ALIGNED`.
- Browser hydration failure leaves server-rendered identity, state, freshness and navigation usable where the route architecture supports SSR.

No failure triggers a replacement collector, alternate store, browser-side scorer, hidden zero fill or automatic publisher failover.

---

## 12. Authority architecture

The federation is descriptive composition. Default caps are literal false:

```text
is_context_only = true
may_rank = false
may_gate = false
may_size = false
may_escalate = false
may_trade = false
may_modify_prophet = false
```

Specific incumbent owners retain their accepted authority. Prophet may use accepted sector/theme context only through its existing governed contracts; this program does not alter candidate origination, ranking, admission, sizing or withdrawal.

Research priority, thesis health, lifecycle stage, leadership, entry availability and trade selection remain separate concepts. The UI may juxtapose them, but no page composition silently promotes one into another.

The Neural Web A5 governor remains the promotion/authority owner. Evaluation acceptance, not visual prominence or repeated confirmation, is required for any future authority change.

---

## 13. Implementation decomposition

This is an architectural program, not one mega-PR. Each subproject receives its own current-source design/plan and one useful vertical capability.

### STSI-0 — Architecture freeze

This document. It records the hierarchy, owner map, conflict grammar, page roles, authority boundary and release sequence. No product source changes.

### STSI-1 — Sector federation and sector dossier vertical

Activate a real sector-level read through the existing `sector_intelligence_packet.v1` ownership seam and render one complete sector-dossier vertical. The first vertical must include current state, material change, child leadership, participation/concentration, connected themes, conflicts, freshness and evidence on real owner inputs.

### STSI-2 — Theme Tracker ↔ theme detail bridge

Adopt accepted Lane A semantics, preserve thesis health versus entry quality, add governed drill-through and project ThemeState/pathway/evidence into theme detail without duplicating ThemeState.

### STSI-3 — Subsector/group intelligence

Adopt accepted Lane C/P1/D contracts, add parent contribution and multi-window leadership to group detail, and preserve entry timing as a separate dimension.

### STSI-4 — Source-local subtheme explorer

Build rights-aware Finviz/THS local-theme indexes and dossier pages over Theme Graph latest-belief/capability readers. Semantic-only and rights-restricted states must be useful and honest.

### STSI-5 — Sector Central refinement and Atlas adoption

After the dossier contracts are stable and PR #7283 dependencies clear, simplify duplicated hub details, strengthen change/conflict routing and link the accepted Atlas rather than reproducing it.

### STSI-6 — Evaluation and production qualification

Establish domain-specific outcome cohorts, cross-page semantic consistency, focused publication composition and deployed user-path acceptance. This stage does not grant authority automatically.

### 13.1 Dependency order

```text
STSI-0
  └── STSI-1
        ├── STSI-2 (after Lane A accepted)
        ├── STSI-3 (after C/P1/D inputs accepted)
        └── STSI-4 (after identity/rights scope accepted)
              └── STSI-5
                    └── STSI-6
```

STSI-2, STSI-3 and STSI-4 may proceed in parallel only with disjoint source custody and accepted interfaces. PR #7211 remains the incumbent publication path throughout.

---

## 14. Testing strategy

### 14.1 Contract and identity tests

- closed-schema validation for every emitted contract;
- stable identity under label changes;
- latest-belief rather than latest-row Theme Graph reads;
- primary basket versus proxy basket invariants;
- no uncurated local-theme-to-canonical mapping;
- no unsupported company-to-theme fact persistence;
- rights registry fail-closed behavior;
- authority caps literal false unless read from an accepted owner.

### 14.2 Time, correction and quality tests

- observation versus generated versus knowledge clocks remain separate;
- same-date correction supersedes rather than double-counts;
- distinct-date persistence uses only eligible observations;
- stale/fresh/mixed-generation conflict classification;
- null versus false versus zero preservation;
- partial population denominator preservation;
- current-membership/non-PIT disclosure;
- unavailable production-only sources remain typed unavailable.

### 14.3 Conflict tests

Fixtures must kill false reconciliation across:

- timeframe splits;
- parent/child scope splits;
- stale versus current observations;
- thin versus complete coverage;
- context versus authority owners;
- genuine fresh comparable disagreement;
- insufficient clocks/scope returning `UNAVAILABLE`.

### 14.4 Product and browser tests

For each material page slice:

- direct route and bidirectional drill-down work;
- server-rendered glance remains truthful before optional hydration;
- search/filter changes visibility only;
- mobile tables/cards expose the complete reason and missingness state;
- no horizontal overflow at 390px;
- dark/light are independently reviewed art directions;
- EN/ZH state meaning and actions match;
- keyboard and screen-reader semantics are present;
- no raw slugs/internal enums appear at rest;
- no substantive runtime stylesheet system is introduced;
- template/site sync and asset references pass.

### 14.5 Real-input proof

Each vertical executes against committed or otherwise accepted real owner inputs. Controlled fixtures may prove degraded/conflict states but are labelled and never represented as current market data.

A local browser proof is not production acceptance. Merge, focused publication, deployed bytes, authenticated access where required and cache-busted browser behavior are separate receipts.

---

## 15. Program acceptance gates

### 15.1 Truth

- One canonical identity/relationship source per fact.
- Every displayed dimension has owner, method, clock, source reference, coverage and authority.
- Direct/proxy relationships are never reversed.
- Missing evidence remains missing.
- Every cross-page disagreement is classified or explicitly unresolved.
- Rights and PIT limitations are visible and enforced.

### 15.2 Intelligence

- Sector pages identify the actual supporting and dragging child groups.
- Participation and concentration prevent narrow leadership from reading as broad.
- Persistent and transient leadership are separable.
- Thesis health and entry quality are separable.
- Parent/group/member states cannot silently inherit authority from one another.
- Change tapes contain owner-observed material transitions, not regenerated prose noise.

### 15.3 Product

- Sector Central, sector, subsector, theme, subtheme and stock routes form a coherent drill-down loop.
- The default viewport answers what changed, why it matters and the current posture.
- Detail remains available without overwhelming the glance tier.
- Atlas/heatmaps remain discovery/comparison rather than duplicated intelligence dossiers.
- EN/ZH, dark/light, desktop/mobile and accessibility gates pass.

### 15.4 Learning

- Outcome cohorts are grain-specific.
- Calibration and false-alert evidence are preserved by regime/coverage.
- Context-only dimensions cannot be promoted by page composition.
- Future predictive claims register prospectively through existing Evaluation owners.

### 15.5 Production

- Accepted source PRs are merged in dependency order.
- Focused publisher emits one coherent generation through PR #7211's owner path or its accepted successor.
- Deployed page metadata and all consumed artifacts agree on generation/semantic horizon.
- Real browser journeys show no stale fallback, split vintage, broken links, missing assets or console errors.
- A natural follow-on publication advances without manual repair.

---

## 16. Explicit non-goals

This program does not:

- replace GMI Theme Graph or ThemeState;
- create a second sector, theme, subtheme, company or security identity plane;
- create a second event, history, correction, outcome, queue, retry or publication store;
- recalculate accepted owner signals inside templates or browsers;
- copy proprietary competitor code, assets, corpora or branding;
- infer canonical mappings from fuzzy labels or overlap alone;
- infer causal transmission from membership or correlation;
- treat current-membership history as PIT;
- average separate dimensions into a universal sector/theme score;
- let a parent entry state qualify a member stock;
- modify Prophet selection, ranking, sizing or withdrawal policy;
- grant portfolio or trade authority;
- rebuild the Sector Central consolidation, House Theme Atlas, member-observation source or focused publisher;
- make every source-local concept measurable before the substrate and rights permit it.

---

## 17. Open questions that do not block the architecture

1. Which exact sector entity key should anchor `sector_intelligence_packet.v1` across ETF, GICS and Finviz vocabularies? STSI-1 must select from existing canonical identifiers rather than minting an approximate alias.
2. Which owner should supply cap-weight versus equal-weight contribution for non-SPDR group families when qualified capitalization coverage is incomplete?
3. Which local-theme families may expose member structure publicly under the current rights registry, and which require aggregate-only pages?
4. Which material-change thresholds are already owner-defined versus requiring a separately preregistered descriptive policy?
5. Which group/subtheme outcome cohorts have enough distinct episodes for useful calibration, and which must remain descriptive?
6. How should cross-market canonical themes present region-specific subthemes without implying synchronized clocks or identical mechanisms?
7. Which connected-theme relationships belong in Theme Graph versus remain view-time derived relations with visible paths?

Each question receives an owner ruling or bounded research packet before changing production semantics.

---

## 18. Architecture freeze / no-rebuild boundaries

1. **One graph and one ThemeState.** GMI remains canonical.
2. **One focused publisher.** PR #7211 or its accepted successor owns coherent Sector Intelligence publication.
3. **No magic score.** Named dimensions and typed conflicts remain separable.
4. **Thesis and entry are independent.** Neither proves the other.
5. **Parent and member authority do not inherit.** A strong group does not qualify every member.
6. **Primary and proxy baskets stay distinct.** Supplemental price coverage is not identity.
7. **Rights are live registry decisions.** Historical row snapshots do not authorize current display.
8. **PIT limitations are product facts.** Current-membership calculations remain labelled.
9. **Atlas is discovery, dossiers are explanation.** Neither duplicates the other.
10. **Reference vertical before estate-wide migration.** STSI-1 proves one complete real sector journey before broad rollout.
11. **Evaluation is domain-specific.** Sector evidence does not validate subsectors/themes by analogy.
12. **No page composition grants authority.** Promotion remains an explicit governor/evaluation decision.

---

## 19. Exact next action after written-spec approval

Do not write one implementation plan for STSI-1 through STSI-6.

The next bounded design/plan unit is **STSI-1 — Sector Federation and Sector Dossier Vertical**.

At current-source action time, STSI-1 must:

1. resolve the canonical sector identity and existing packet/adaptor ownership;
2. select one real reference sector with meaningful child/theme conflict states;
3. bind existing owner dimensions without recalculation;
4. define the exact sector-dossier read contract and conflict records;
5. name producer, real consumer and existing publication path;
6. specify dark/light and EN/ZH desktop/mobile composition;
7. define discriminating contract, correction, null, authority and browser tests;
8. preserve every active PR dependency and avoid their owned paths until accepted;
9. ship no prediction, rank, gate, size or trade authority.

Only after STSI-1's written plan is approved should source implementation begin.

---

## 20. Self-review checklist

- The document extends existing owners rather than creating a truth plane.
- It does not reopen the completed Sector Central consolidation.
- All six active PR carriers are preserved and consumed only after acceptance.
- Sector, subsector, theme, subtheme, basket and security meanings are distinct.
- Direct and proxy relationships cannot be reversed.
- Cross-page conflict classes preserve timeframe, scope, freshness, coverage and authority differences.
- Null, false, zero, stale, partial, non-PIT and rights-restricted states are explicit.
- Theme health, leadership, entry and stock eligibility remain separate.
- Subtheme pages are source-bound and rights-aware.
- Dark/light and EN/ZH desktop/mobile proof is mandatory.
- Production acceptance requires the real focused publisher and browser journey.
- The next plan is one bounded STSI-1 vertical, not a mega-plan.
