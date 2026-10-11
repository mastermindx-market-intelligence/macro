# GMI consumer and economic-research source audit

**Audit mode:** standard Pro source audit, not Deep Research. Read-only GitHub investigation plus local synthetic reproduction; no source changes, production runs, external comments, deployments, or model/provider calls.

**Macro source pin:** `bebcb24db8707f93c3acca470590fead13e78dbd`.  
**Terminal source pin:** `mastermindx-market-intelligence/mastermind-terminal@41b8af2da46614cedd2a485214e53003d4f030fc` (default `master`, resolved from GitHub). The remembered repository alias `Terminal` is not the actual repository name.  
**Procedure context:** Mastermind `20adcaf65c2dd1bb734ab06e215feb1a0eb65659`; pinned INDEX and WEB_CEO_DELEGATION reviewed.  
**Boundary:** the integrated audit owns PR-wide historical reconciliation, architecture synthesis, publication and broader GMI scope. Findings here distinguish inspected source, historical receipts, and unobserved current production behavior.

## Executive finding

The revised report correctly recognizes that membership is not economic exposure, that STSI has a governed contract, and that several substantial implementation branches already exist. It still understates the **existing Company Theme Exposure → Terminal delivery chain**, and its proposed convergence omits concrete contract incompatibilities and admission defects that must be resolved before the branches can compose.

There is already a scheduled Company Intelligence sidecar builder, an immutable R2/CAS publisher, an authenticated Terminal BFF, a receipt-verifying resolver, and a mounted Company Theme Context card. These should be migrated in place. They are **not** a graph-backed economic-exposure system, but treating Terminal as greenfield or forcing all publishers through #7211 would duplicate existing machinery.

The most actionable new defect is in #8240: a synthetic reproduction using its own checked-in fixture shows unknown/revoked rights strings admitted as `READY_FOR_RESEARCH_COMPARISON`. Its financial authority flags remain false. The finding is a research-input/admission defect, not evidence of an actual production rights leak.

## 1. Pinned implementation state

| Interface | Inspected source state | Actual capability and limit |
|---|---|---|
| Company Theme Exposure | On Macro main | Closed context-only membership projection, Company Intelligence identity binding, generation hashes, builder, publisher, scheduled caller. Graph economic exposure and current natural product proof are separate obligations. |
| Terminal Company Theme Context | On Terminal master | Same-origin authenticated API, current Company Intelligence validation, R2 marker → immutable manifest → company bytes, lineage quarantine, mounted UI. No graph-backed ThemeState, issuer/security historical exposure, or tactical alert policy. |
| #7211 focused Sector Intelligence publisher | Merged; semantic head `f2c570d4bc169da3dca6aa276bca5b8b6d063b98`, merge `c538c78eef57b810ab36ddc8c7d93ef15a5dec7f` | Existing basket → action board → Sector Central → semantic validator → scoped Git publication. Historical release/readback/authenticated proof is recorded; not re-executed in this audit. It does not yet build the STSI dossier. |
| #7777 governed dossier | Merged; semantic head `f98f429ca1cccb8b87b32a358d0004324b0587b6`, merge `0d5bf78deee6d9d60d74f75be3538a9a46fbe7ee` | Contract + fixture + governance/hash/authority validation. Proposed composer, builder, JS consumer, and XLK payload are absent at inspected main. |
| #7455 closed-session leadership | Open; `ebc7604b624adb8452041d8240f7cda41733f167` | Daily-session technical observations; explicitly current membership, non-PIT, corporate-action basis unverified, context-only. Includes builder and Neural Web receipt integration. |
| #8299 missingness/qualification | Open; `39ba5f7b8e88821c341b1de99344d262afcb8837` | Fixes unavailable-as-zero legacy rotation behavior, comparable cohorts, missing ranks, strict frozen-member outcome coverage, observer capture time, logical hit bounds. Does not establish historical availability or price provenance. |
| #7976 Finviz repricing | Open; `0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff` | Source-local price participation, leader continuity, separately named revisions/events/fragility. PIT helper selects dated structure vintages and exact price endpoints, but does not itself supply full bitemporal or data-rights proof. |
| #7870 shared Theme Research | Open; `f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9` | Closed registry/shell groundwork, paid API, fresh rights-owner check, public Company Intelligence witness loader. Shared types/composer still eagerly imported from Semiconductor; only Semiconductor registration; private evidence tuples unbound; system replay refused. |
| #8240 Prophet Early Leadership | Open; `6d920952dc07731139cefc8a41cbd9bf92be5acf` | Pure research compiler with six caller-supplied inputs and all decision authorities false. No resolver, writer, scheduling or production consumer is introduced. It is not completion of W3C source-selection projection or a generic Prophet/GMI adapter. |

The PR heads were read as exact GitHub metadata; open PR source was read at those heads, not inferred from title/body or treated as protected law.

## 2. Existing Company Theme Exposure → Terminal chain must be retained

### 2.1 What already exists

The Macro contract explicitly calls itself a membership projection, has `AUTHORITY="context_only"`, and closes each exposure item to `theme_id, name_en, name_zh, basket_id, mapping_qualifier`. No exposure weight, direction, revenue/cash-flow magnitude, economic role, issuer ID or security ID exists in that wire item. See [contracts.py:1–35](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/company_theme_exposure/contracts.py#L1-L35).

The producer takes active dated basket membership, validates the crosswalk, derives a crosswalk qualifier from editorial notes, and explicitly says the qualifier is **not a company relationship**. The `direct`/proxy/curated label cannot be promoted to an economic direct/indirect exposure classification. See [views.py:69–105](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/company_theme_exposure/views.py#L69-L105), [108–166](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/company_theme_exposure/views.py#L108-L166).

Unlike the older “builder/publisher with uncertain DAG” census, the current main workflow is explicit: scheduled every three hours, then build the sidecar from Company Intelligence output, membership, crosswalk and `data/neuralweb/theme_state.json`, then call its own R2 publisher. See [company-intelligence.yml:8–17](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/.github/workflows/company-intelligence.yml#L8-L17), [124–149](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/.github/workflows/company-intelligence.yml#L124-L149). It is a sibling publication after Company Intelligence, not part of #7211.

The publisher creates/verifies immutable objects before promoting a sole root marker with compare-and-swap. Crucially, it returns success when R2 credentials are absent; a green process alone cannot prove publication. See [publish_company_theme_exposure_r2.py:113–149](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/scripts/publish_company_theme_exposure_r2.py#L113-L149).

Terminal already serves `/api/company-theme-context/[symbol]` after server-side authentication and rate limiting; it independently resolves current Company Intelligence before accepting the sidecar. See [route.ts:44–96](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/app/api/company-theme-context/%5Bsymbol%5D/route.ts#L44-L96). Its resolver validates the R2 origin, immutable manifest equality, generation IDs, byte length/SHA-256, and Company Intelligence lineage. See [companyThemeExposure.ts:495–558](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/companyThemeExposure.ts#L495-L558).

The UI is actually mounted inside Company Intelligence, not merely an unused component: [CompanyIntelligencePage.tsx:747–762](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/components/fin/CompanyIntelligencePage.tsx#L747-L762). It refuses to show current context against historical events and quarantines mismatched Company Intelligence generations: [CompanyThemeContextCard.tsx:172–211](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/components/fin/CompanyThemeContextCard.tsx#L172-L211).

### 2.2 Migration gates the report needs to name

**Schema incompatibility:** the sidecar only accepts `neuralweb.theme_state.v1`, with an exact set of crosswalk theme IDs and `authority.is_context_only=true`. Renaming or replacing that producer with `theme_state/v1` without an owner migration makes this input invalid. See [views.py:32–66](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/company_theme_exposure/views.py#L32-L66). Terminal's exact-key normalizer also rejects arbitrary new economic fields in v1. This is a coordinated producer/consumer schema migration, not an additive data-file swap.

**Knowledge time:** `added/removed` supports current valid-date roster selection; it has no retained/known/recorded instant. The “point-in-time membership” wording in the local UI is not proof of bitemporal knowability for historical decisions. A graph-backed extension must bind the existing graph membership generation/interval and issuer/security identity owner, not infer knowledge time from `added`.

**Semantic freshness:** the Terminal resolver uses wall time for its 30-second fetch cache, but a successfully fetched old marker is returned as non-stale; normalization only validates the timestamp format and repeats the producer's stored fresh/stale flag. The card then prints “Fresh” from that flag. If both Company Intelligence and the sidecar stop advancing, successful retrieval and matching old generations can still display an old “fresh” receipt. This is a source-inspected failure path; no production incident was claimed. See [companyThemeExposure.ts:182–197](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/companyThemeExposure.ts#L182-L197), [495–558](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/lib/companyThemeExposure.ts#L495-L558), [CompanyThemeContextCard.tsx:49–53](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/components/fin/CompanyThemeContextCard.tsx#L49-L53).

**Completion proof:** read the actual root marker and immutable company object from the authorized owner, bind them to a naturally scheduled run, then verify Terminal's authenticated response and rendered state. Include a correction/removal, an upstream failure, a schema transition, an old-marker-with-successful-HTTP case, and a Company Intelligence/sidecar generation race. Current source wiring is built; natural current product behavior remains unobserved by this audit.

## 3. STSI: strong contract, missing product

The merged dossier contract already includes named dimensions, conflicts, watch conditions, source receipts, knowledge cutoff, common as-of, quality/PIT flag, nested governance and fixed false financial authorities. Hash and packet/run/manifest cross-binding are enforced in [contracts.py:741–870](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/sector_intelligence/contracts.py#L741-L870). Preserve that rather than inventing a parallel dossier store.

It is still **sector-specific**: dossier IDs require `dossier:sector:...`, entity IDs require `sector:...`, ticker and benchmark ticker are mandatory, and nested packet/run/manifest bind to a sector native ID. See [schema:34–61](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json#L34-L61), [135–189](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json#L135-L189). “Extend STSI to theme/subtheme” needs an explicit compatible typed identity/grain version and nested-governance migration. It cannot be achieved by placing a theme ID into an existing sector field.

The accepted implementation plan names the actual unfinished path: `engine/neuralweb/sector_federation.py`, `scripts/build_sector_dossiers.py`, `templates/sector_dossier.js`, and `site/sectordata/sector_dossiers/xlk.json`. All four exact reads returned NOT_FOUND at the inspected main pin. The plan's Task 2 and Task 3 remain the actionable producer route: [plan:893–900](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md#L893-L900), [1418–1425](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md#L1418-L1425). This is a bounded absence claim about the exact incumbent implementation, not a claim that no differently named artifact could exist anywhere.

#7211 currently invokes only baskets, action board, Sector Central and freshness validation: [build_sector_intelligence.py:33–51](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/scripts/build_sector_intelligence.py#L33-L51). Its existing output validator proves same semantic dates and exact hashes for that family: [freshness validator:114–221](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/scripts/check_sector_intelligence_freshness.py#L114-L221). Its scope does not cover Company Intelligence R2, every theme product or Terminal.

The historical #7211 record includes publisher run `35807731340`, publication commit `f8bc00fe15323ced6ff56ef5768124c94cd7f384`, matching deployed HTML and later authenticated common-generation acceptance. Preserve that accepted evidence and its date; do not imply this audit reran it or that it proves the missing dossier. [Cumulative receipt](https://github.com/mastermindx-market-intelligence/macro/pull/7211#issuecomment-5787640075).

## 4. Leadership branches are three different observation families

### #7455: current-membership technical windows

The source explicitly emits `CURRENT_MEMBERSHIP_TECHNICAL_WINDOW_NOT_PIT` and `CORPORATE_ACTION_BASIS_INHERITED_UNVERIFIED`; it exposes declared/priced/current/complete-window counts, unpriced members, short history, stale tape and missing sessions. See [subsector_rotation.py:443–522](https://github.com/mastermindx-market-intelligence/macro/blob/ebc7604b624adb8452041d8240f7cda41733f167/engine/subsector_rotation.py#L443-L522). The output declares unique-instrument equal-weight daily-rebalanced parent/child returns and non-PIT membership: [795–812](https://github.com/mastermindx-market-intelligence/macro/blob/ebc7604b624adb8452041d8240f7cda41733f167/engine/subsector_rotation.py#L795-L812).

This can support honest current descriptive context before historical membership qualification. It must not be delayed unnecessarily for a historical capability it explicitly disclaims, nor promoted to historical causal/evaluation proof. The builder attaches the observation without changing legacy rank, turn or trading policy; [build_subsector_rotation.py:415–438](https://github.com/mastermindx-market-intelligence/macro/blob/ebc7604b624adb8452041d8240f7cda41733f167/scripts/build_subsector_rotation.py#L415-L438).

### #8299: missingness and evaluation qualification

Current main zero-fills unavailable z-scores and can label zero axes “leading.” The branch's `_rotation_metrics` instead chooses one cohort with all four required horizons, emits null and reason when unmeasured, and distinguishes a known tie from unavailable input. See [subsector_rotation.py:61–168](https://github.com/mastermindx-market-intelligence/macro/blob/39ba5f7b8e88821c341b1de99344d262afcb8837/engine/subsector_rotation.py#L61-L168). Preserve this while integrating #7455; both touch the same engine and should not overwrite one another.

The track record freezes members and records observer wall time separately from the session label; every frozen member requires exact endpoints or the whole outcome remains unmeasured. Its hit bounds are logical limits over missing outcomes, explicitly not confidence intervals or selection-bias correction. See [snapshot:164–201](https://github.com/mastermindx-market-intelligence/macro/blob/39ba5f7b8e88821c341b1de99344d262afcb8837/engine/subsector_track_record.py#L164-L201), [outcome:301–344](https://github.com/mastermindx-market-intelligence/macro/blob/39ba5f7b8e88821c341b1de99344d262afcb8837/engine/subsector_track_record.py#L301-L344), [bounds:499–522](https://github.com/mastermindx-market-intelligence/macro/blob/39ba5f7b8e88821c341b1de99344d262afcb8837/engine/subsector_track_record.py#L499-L522). The emitted evaluator explicitly says historical availability and price provenance remain unqualified: [809–835](https://github.com/mastermindx-market-intelligence/macro/blob/39ba5f7b8e88821c341b1de99344d262afcb8837/engine/subsector_track_record.py#L809-L835). Do not use its `validated` local verdict as general GMI alpha acceptance.

### #7976: source-local repricing, not canonical economics

The branch intentionally uses Finviz's incumbent tree and returns. Positive-move concentration is an equal-member return-magnitude diagnostic, not market-cap contribution. Handoff describes a change of price leaders, not money flowing between companies. Durability is a set of named price/revision/event/fragility legs, not a fused confidence score. See [theme_repricing_context.py:1–42](https://github.com/mastermindx-market-intelligence/macro/blob/0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff/engine/theme_repricing_context.py#L1-L42), [552–571](https://github.com/mastermindx-market-intelligence/macro/blob/0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff/engine/theme_repricing_context.py#L552-L571), [theme_rerating_durability.py:1–16](https://github.com/mastermindx-market-intelligence/macro/blob/0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff/engine/theme_rerating_durability.py#L1-L16).

The PIT helper chooses `Vintage.asof <= requested date` and exact exchange-session endpoints. The underlying Vintage carries date/source_ref/tree, not separate source/recorded/known instants. It therefore does not close D2E bitemporal rights/measurement requirements by itself. See [theme_repricing_pit.py:75–112](https://github.com/mastermindx-market-intelligence/macro/blob/0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff/engine/theme_repricing_pit.py#L75-L112), [217–255](https://github.com/mastermindx-market-intelligence/macro/blob/0a6e4d7f518d3ab086da2b1aecfe0d5fa6dac6ff/engine/theme_repricing_pit.py#L217-L255), [current local_sources.Vintage:57–67](https://github.com/mastermindx-market-intelligence/macro/blob/bebcb24db8707f93c3acca470590fead13e78dbd/engine/theme_graph/local_sources.py#L57-L67).

**Required convergence:** use independent typed slots with source-local/canonical identity, window, price basis, weight/rebalance method, denominator, missingness, valid time, knowledge time and quality. Reuse one owner publication and store per existing family. Do not force #7455's raw daily observations and #7976's Finviz returns to have identical numeric values. In particular, unmeasured `exit_watch` booleans must not become reassuring “risk absent”; consumer copy must retain the measurement status alongside them.

## 5. #7870 is a real shared dependency but not a released general economic engine

The branch has useful exact registration and dispatch, per-request rights snapshots, paid auth reuse, and schema/definition checks: [app/theme_research.py:576–661](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/app/theme_research.py#L576-L661).

However the shell imports `OwnerBundle, ResearchQuery, ResearchRefusal` from Semiconductor, and the registry eagerly imports its composer. Only Semiconductor is registered. The shared query type even names the two Semiconductor slice literals, while the API view enum is fixed to manufacturing/commercial/capacity/economics. See [app imports/query:58–73](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/app/theme_research.py#L58-L73), [query body:197–212](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/app/theme_research.py#L197-L212), [registry:50–55](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/engine/market_ontology/theme_research_registry.py#L50-L55), [registry:169–188](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/engine/market_ontology/theme_research_registry.py#L169-L188), [types:96–119](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/engine/market_ontology/semiconductor_theme_research.py#L96-L119).

The real registered loader currently binds only public event workspaces, emits `private_assertions_unbound`, leaves assertions/identity results/financial packets/interpretations/native refs empty, and refuses `system_replay`. Scope filtering deliberately refuses nonempty private families until R4 has a native-subject cohort rule. See [semiconductor_owner_bundle.py:362–447](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/engine/market_ontology/semiconductor_owner_bundle.py#L362-L447). A successful API response from this loader cannot prove a fully populated value-chain graph or economic dossier.

The existing economics view selects one valid management guidance → actual → new outlook sequence. External consensus, house forecast and market incorporation are explicitly unavailable. See [semiconductor_theme_research.py:943–1067](https://github.com/mastermindx-market-intelligence/macro/blob/f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9/engine/market_ontology/semiconductor_theme_research.py#L943-L1067). The report's richer “economic mechanism → cash-flow transmission → valuation → price recognition” grammar is a target, not already built by this branch.

**Required extraction:** move only approved transport/query/bundle/refusal/time/selection/generation primitives into the common owner; remove eager vertical imports; bind vertical-owned view/slice validation through the existing closed registration. Preserve established private binding and rights-owner boundaries. A dissimilar second domain must demonstrate these seams without copying Semiconductor types; it must not make every sector use Semiconductor economics. Private bindings, current-base CI and natural served evidence remain separate work packages.

## 6. #8240 needs contract migration and a concrete rights repair before integration

The compiler is intentionally a pure adapter. It creates no source reader or persistence path; its accepted input `theme_state/v1` differs from the existing Neural Web `neuralweb.theme_state.v1` and existing exposure `company_theme_exposure.v1`. It expects six caller-supplied input families and emits `prophet.early_leadership_evidence/v1`. See [module:1–46](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/engine/prophet_early_leadership_evidence.py#L1-L46), [build signature:422–439](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/engine/prophet_early_leadership_evidence.py#L422-L439).

Useful constraints already implemented include issuer/security/setup lineage binding; candidate and same-issuer aliases excluded from peers; common measurement instants, membership vintage, return window and basis; null singleton peers; no score/rank/trade authority. Preserve them. The peer-exclusion booleans and source references still require production owner-reader proof; a string label is not that proof.

### Reproduced rights defect

The source accepts any nonempty `rights_state` text, then rejects readiness only for exact `RIGHTS_BLOCKED` or `UNAVAILABLE`. See [314](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/engine/prophet_early_leadership_evidence.py#L314), [501–516](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/engine/prophet_early_leadership_evidence.py#L501-L516).

A local source-only reproduction extracted the branch's existing synthetic fixture and changed one field:

| Input rights_state | Actual compiler research_state |
|---|---|
| internal_allowed | READY_FOR_RESEARCH_COMPARISON |
| RIGHTS_BLOCKED | UNAVAILABLE |
| UNAVAILABLE | UNAVAILABLE |
| UNKNOWN | READY_FOR_RESEARCH_COMPARISON |
| REVOKED | READY_FOR_RESEARCH_COMPARISON |
| rights_blocked | READY_FOR_RESEARCH_COMPARISON |

All financial authority flags stayed false. A blocked envelope still carries numeric features; the existing test explicitly asserts retained acceleration on `RIGHTS_BLOCKED`: [test:798–803](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/tests/test_prophet_fusion_w3_structural.py#L798-L803).

**Required repair:** consume the rights owner's closed, verified **computation/measurement** verdict; reject unknown/malformed status; bind registry revision and use-purpose. Separately decide whether denied data may be retained in an internal envelope or must be redacted under that same owner's policy. Neither this compiler nor GMI should invent a second rights policy.

### Typed-null incompatibility

The existing fixture with `dynamics.acceleration=None` throws `theme_acceleration_invalid`. Many theme fields are mandatory numeric values, including fields that current source cannot legitimately produce everywhere. See [theme projection:291–311](https://github.com/mastermindx-market-intelligence/macro/blob/6d920952dc07731139cefc8a41cbd9bf92be5acf/engine/prophet_early_leadership_evidence.py#L291-L311). Do not zero-fill final ThemeState gaps to satisfy this adapter. Define explicit field-level unavailable reasons and a research cohort policy; record exclusion denominators and preserve the source's authority ceiling.

Local reproducibility artifacts are `consumer-src/reproduce_prophet_boundary.py` and `consumer-src/prophet-boundary-reproduction.json`. This narrow run does not substitute for full-suite or production evidence.

#8240 is only Early Leadership research. It must not replace the separate accepted W3C finalized US/CN source-selection projection; root is tracing that obligation.

## 7. Concrete migration sequence for the master plan

1. **Preserve already built carriers.** Keep Company Intelligence/R2 → Terminal context, #7211's Git/site publisher, #7777's governance owner, and each specialist observation owner. Name the producer, consumer and publication family per row.
2. **Freeze the minimal owner interfaces.** Canonical graph entity and membership references; field-level measurement status; valid/known/recorded clocks; compatible ThemeState version; rights purpose/revision; Company Intelligence event lineage; generated projection ID. No new universal score or duplicate identity store.
3. **Repair adapters against those interfaces.** Company Theme Exposure and Terminal normalizers migrate together; #8240 receives verified rights, typed nulls and owner readers; existing Neural Web readers become projections of the accepted canonical state. Prove round-trip identity and lossless withheld/unavailable semantics.
4. **Complete STSI's actual producer and publisher insertion.** Reuse the existing plan's pure composer and single atomic dossier builder, then version its sector-only identity contract for additional grains. Add within #7211 only the paths that publisher owns; retain private economic API and Company Intelligence sidecars on their existing owners.
5. **Integrate leadership with explicit method labels.** #8299's missingness correction is foundational; #7455's current-roster observations can ship with honest non-PIT labels; #7976 remains source-local until mapped and measurement-eligible. Capture ordinary future observations without retroactively making old rows “known.”
6. **Finish #7870's common primitives and real domain bindings.** Preserve current private omissions until accepted R4 binding; prove a second dissimilar domain, then each requested vertical's actual product coverage. A two-domain test proves kernel usability, not completion of all sectors.
7. **Prove natural cross-consumer behavior.** One real source refresh must reach the relevant graph/state, sidecar/dossier and at least two named consumers with exact receipt agreement; repeat for correction/removal and withheld source. Verify semantic aging during a stopped upstream, authenticated UI states, and mixed-generation quarantine. Historical receipts are reused only within their proven scope.
8. **Keep research and decision promotion separate.** Source-level compilation, green CI, emitted “validated,” and current-roster lookbacks do not establish financial usefulness. Preserve W3C ordering/source reasons, existing Prophet admission, B4 availability and Terminal execution ownership until their own evidence and authority gates clear.

## Validation and remaining uncertainty

- Read pinned full source for the inspected files and bounded exact relevant sections; open branches were not mixed into main truth.
- Resolved actual Terminal repo/default pin.
- Inspected seven relevant PR changed-file lists and exact heads.
- Confirmed exact absence of four planned STSI product paths at the Macro pin.
- Reproduced #8240 rights and typed-null behavior using only its checked-in synthetic fixture.
- Did not run production, fetch protected live payloads, trigger workflows, inspect credentials, alter remote state, run broad test suites, or infer present runtime activity from GitHub prose.
- Current live Company Theme Exposure publication/Terminal availability, natural #7211 freshness, full-domain #7870 completion, and all branch release gates remain to be verified by the responsible owners.

