# Sol decision packet — Research Vault workbench structural subtype

**Status:** PROPOSED BINDING RULING — independent review required before merge  
**Decision owner:** Sol / product-design architecture  
**Observed Macro source:** `70ecdbafe14e58fb55d39e754ab76a75b75ffda7`  
**Protected Sol procedure:** Mastermind@`4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`  
**Primary route:** `macro:research_vault` / `/research_vault.html`  
**Existing product-program carrier:** #7182

## 1. Decision

Research Vault remains in the **Research** user job and keeps its current registry product-family value
`editorial` until the separate Registry V2 owner accepts a richer structural field.

For design/reference work, the `editorial` family has two adjudicated structural subtypes:

1. **`reading_surface`** — a long-form document or record whose primary job is to read one body of
   work. The existing F/Editorial measure-column + TOC grammar applies.
2. **`research_workbench`** — a corpus/search/browse/inspect surface whose primary job is to find
   relevant source material, understand it with source-bound context, and inspect the exact original.
   It MUST NOT be forced into the long-form measure-column + TOC skeleton.

Current `macro:research_vault` is **`editorial / research_workbench`**.

This is a structural-selection ruling. It does not create a new top-level user job, registry authority,
component system, AI product, corpus, store, viewer, entitlement system, or search plane.

## 2. Why this ruling is required

Current source contains a structural contradiction:

- `MASTER_PRODUCT_INFORMATION_ARCHITECTURE_V1.md` places Research Vault under the Research job and
  describes it as part of reports/record.
- `MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` maps `research_vault.html` to F / `editorial`, whose
  canonical layout is a measure-limited reading column with a TOC rail.
- The same repository's estate census says `editorial` is a catch-all that mixes indexes with the
  documents they index and cannot safely carry structural authority.
- Production `research_vault.html` is not a single reading surface. It already provides a saved/live
  research state, weekly/desk/theme/inventory counts, feed lanes, date/institution/side/theme browsing,
  full-text search, result counts, active filters, authenticated entitlement states, a PDF viewer,
  page thumbnails, find-in-document, related research, zoom/fullscreen/invert, and quota-metered
  download.
- The accepted Research Vault product thesis is explicitly **not a larger PDF shelf and not a separate
  chatbot**. The human journey is source discovery → grounded understanding/comparison → exact
  evidence inspection, while original evidence, source-specific claims, Mastermind synthesis and
  private user context remain distinct.

Forcing this route into the generic F reader would either remove working product capabilities or turn
a searchable corpus/workbench into a decorative article. Both outcomes violate product preservation.

## 3. Structural selection

A route may use `reading_surface` when:

- one document/body is the primary subject;
- navigation is primarily within that body or its local sections;
- search/browse across a corpus is not the primary task;
- entitlement does not materially transform the document-selection workflow.

A route uses `research_workbench` when its primary job requires a meaningful combination of:

- corpus discovery/search/browse;
- source identity and publication/freshness context;
- selected-document inspection;
- explicit access/rights/entitlement states;
- source-bound evidence or grounded interpretation attached to the selected source;
- a path back to the exact original evidence.

The subtype MUST be selected from the actual route/builder/consumer contract, not inferred from the
broad `editorial` registry value alone.

## 4. Research Vault product identity

The workbench identity is the **source-to-evidence loop**, composed from existing primitives and
owners:

1. **Orient** — what arrived / what changed / how fresh is the corpus;
2. **Find** — browse, filter and search the permitted corpus;
3. **Assess** — inspect source identity, publication context and public-safe report summary/evidence;
4. **Understand** — when lawful Research Intelligence is available, show source-bound synthesized
   context with explicit epistemic labeling and missing/stale/invalid/unavailable states;
5. **Inspect original** — open the same source/version/evidence the answer cites;
6. **Continue** — save/open/download only through the existing entitlement and quota owners.

This loop is composition, not a new global component. It does not authorize a second search backend,
PDF viewer, Brain instance, evidence store, lifecycle, quota ledger or rights plane.

## 5. What the governed reference must preserve

A future governed editable reference for Research Vault must preserve at minimum:

### Discovery and corpus truth

- live-vs-saved/snapshot freshness behavior;
- current inventory/desk/recent-publication context using runtime-owned values;
- Latest / highlighted research / Saved jobs without treating editorial highlight as a trade signal;
- browse hierarchy and filters;
- title/summary/full-text query affordance and honest result counts;
- active-filter state and reset behavior;
- source institution, desk type, publication time, language and supported metadata;
- no fake report identities, fabricated tickers, inferred ratings or unsupported metadata.

### Entitlement and source inspection

- anonymous/public preview without leaking protected report bodies;
- authenticated-but-not-entitled state;
- entitled viewer state;
- quota available and quota exhausted states using runtime-owned limits;
- same-source report viewer with page navigation, find-in-document and source/version identity;
- related research only where the existing source/data owner can support it;
- download through the incumbent metered/watermarked path;
- failure states that say what failed and what remains available.

### Research Intelligence integration

A reference may show the existing/future Research Intelligence consumer only as a **bounded companion**
to selected source material. It must:

- distinguish literal source evidence from Mastermind synthesis;
- preserve source/body/version bindings and evidence locators;
- show missing, stale, invalid and unavailable intelligence explicitly;
- never substitute model synthesis for absent literal evidence;
- never promote research synthesis into rank, score, sizing, entry, trade or signal authority;
- retain a direct path to the exact original source;
- use fictional or explicitly synthetic fixtures when live rights or production state are not proven.

The workbench must not become a generic empty chat shell. The source and evidence remain inspectable
even when synthesis is unavailable.

## 6. State and interaction proof matrix

The governed reference / RIG packet must cover the material matrix rather than a happy-path desktop:

- Dark / Light;
- EN / ZH;
- desktop and 390 mobile;
- live refresh / saved snapshot / delayed refresh;
- loading / corpus empty / query-filter empty / stale / error;
- anonymous preview / authenticated non-entitled / entitled / quota-exhausted;
- browse drawer open/closed on mobile;
- selected filters and cleared filters;
- report selected / viewer loading / viewer error;
- find-in-document open with zero and nonzero matches where applicable;
- keyboard focus-visible and touch-safe controls;
- saved/highlighted states where supported;
- Research Intelligence current / missing / stale / invalid / unavailable;
- correction/version change treatment when the selected source has changed.

Runtime/browser evidence remains separately required; editable frames prove intended treatment, not
that authentication, search, quotas or source opening actually work.

## 7. Current source and dependency rulings

At this ruling's observed source:

- `templates/research_vault.html.j2`, `site/research_vault_app.js` and
  `scripts/build_research_vault.py` are the incumbent page owners.
- #7045 is merged and its desk-type/source-label correction is DO_NOT_REDO.
- #7079 is merged and its source-bound Brain evidence path is DO_NOT_REDO.
- #7226 is an unmerged ingestion-liveness carrier; it is not a UI writer.
- #7461 is a held Research Intelligence claim-integrity repair; it is not a UI writer.
- #7522 is a held Brain consumer for rights-safe Research Intelligence; it is not a Vault UI writer.
- #7354/#7387 are held backend intelligence capabilities; they do not own the Vault page.
- #7182 remains the durable research/program continuity carrier.

Design work may proceed with lawful synthetic fixtures and explicit unavailable states; it MUST NOT
claim those held backend capabilities are deployed merely because the editable reference depicts the
intended consumer state.

## 8. Reference direction

The next Research Vault reference should improve the existing product rather than repainting it.

Recommended composition:

1. **Workbench header** — corpus freshness + concise answer to “what changed in research?”
2. **Discovery controls** — browse/search/filter with visible result truth.
3. **Evidence feed** — source-rich report rows/cards with clear publication context.
4. **Selected-source workspace** — source metadata + original-document inspector.
5. **Grounded intelligence companion** — source-bound Research Intelligence/Brain output, visibly
   subordinate to and linked back to evidence.
6. **Entitlement/continuation band** — access/download/save state through incumbent owners.
7. **Methodology/honesty disclosure** — source vs synthesis, coverage limits, rights/access limits.

Desktop may use a split selected-source workspace where it improves the source↔answer loop. Mobile
must recompose into one primary task at a time rather than squeezing a desktop split view.

The existing decorative desk constellation is not a structural identity device and may be simplified
or removed if RIG proves the same institution/source discovery job is preserved more clearly.

## 9. Relationship to existing design law

This packet narrowly supersedes the assumption that every `editorial` route must use the same
measure-column + TOC structure. It does not repeal the Editorial/Research product family.

Until the constitution can be reconciled without colliding with incumbent design-law work:

- `editorial` remains the registry/product-family value;
- `reading_surface` remains the default long-form F grammar;
- this packet is the controlling structural decision for Research Vault;
- no new registry key is minted here;
- the broader Registry V2 owner decides how structural subtype is eventually represented canonically.

Any future generic Paper/Figma “Editorial” starter must not be treated as sufficient structural
authority for Research Vault unless it explicitly represents the workbench subtype.

## 10. Migration and acceptance order

1. Accept this structural ruling through independent exact-head semantic review.
2. Inventory the current Vault's user-visible capabilities and task journey into a RIG baseline.
3. Compose the governed Research Vault workbench reference in the existing Paper file using canonical
   tokens/primitives and synthetic fixtures where production proof is unavailable.
4. Freeze Dark/Light × EN/ZH × desktop/mobile plus the material data/access/interaction states.
5. Run the two independent RIG critics under the existing rationale-quarantine law.
6. Produce the migration packet only after RIG resolves product-regression findings.
7. Touch `templates/research_vault.html.j2` / `site/research_vault_app.js` only after RIG approval,
   on one bounded writer/carrier.
8. Prove the real route in browser with live/snapshot, entitlement, viewer, search, quota and
   source-opening states. Any Research Intelligence acceptance remains bound to its actual deployed
   producer/consumer state and rights.

## 11. Non-goals

This ruling does not:

- merge or release #7182, #7226, #7354, #7387, #7461, #7522 or any Mastermind AI carrier;
- create a second Brain, corpus, vector store, viewer, search service, entitlement system or quota;
- assert customer-facing rights to third-party research that have not been established;
- turn desk type, Top Picks, synthesis or sentiment into trade advice;
- redesign research report landing pages that are already true reading surfaces;
- edit production Research Vault source;
- create a new top-level product job or registry schema;
- prove deployment, authenticated browser behavior, source-opening precision or customer acceptance.

## 12. Acceptance

Before this packet merges:

1. independent semantic review must confirm the subtype preserves both current production capability
   and the source→answer→original product thesis;
2. reviewers must confirm it does not create a competing data/AI/search/rights/control plane;
3. exact-head repository checks must pass;
4. review must confirm the packet is a narrow structural adjudication and not a covert Registry V2
   implementation.

After acceptance, the Research Vault Paper/RIG lane may START even if held backend intelligence
features remain unavailable, provided those states use synthetic fixtures and are labeled
unavailable/provisional rather than claimed live.
