# CDV-1 foundation integration map — 2026-09-24

Operation: `gmi-consumer-defensive-research-20260923-sol-001`  
Base: `origin/main` @ `10c0d79e29923a92b23d9e6684c3e0979ee39a9b`  
Mode: read-only census and integration recommendation.

STATUS: IN PROGRESS

## Q1 — Foundation inventory

Base `origin/main` is `10c0d79e29923a92b23d9e6684c3e0979ee39a9b`. The candidate heads are #7870 `70fde3c79956bba5b9c4e2365a97b4e4b3b1c3ef`, #7780 `b68069b2e1296bfc772e4f4e3a0c1cc3845f89eb`, and #7777 `4122e3b7e1524482216fb156f201f8229c14011b`. Their complete changed-code stats are: #7870, 59 files under contracts/engine/templates/site/config/tests, `17,241 insertions(+), 11 deletions(-)`; #7780, 13 research/document files, `3,419 insertions(+)`; #7777, five files, `1,688 insertions(+)`. #7870's own handoff says its contract/fixture/rights/guidance/intake/K1-reference/composition layers are accepted, while transport, client, private binding and witness proof remain outstanding (`origin/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9:agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-semiconductor-b-implementation.md:148`). #7777 is still an unmerged feature PR; #7780 is research-only.

### Main foundation inventory

| Item | Version | Status / owner | Purpose |
|---|---|---|---|
| `contracts/evidence_foundation/reference.v1.schema.json` | Evidence Foundation owner-native reference v1 (`origin/main:contracts/evidence_foundation/reference.v1.schema.json:3`) | main, evidence-foundation owner | Pointer-only reference to an immutable owner-native object without copying its body (`:5`). |
| `contracts/evidence_foundation/block.v1.schema.json` | consumer evidence block v1 (`origin/main:contracts/evidence_foundation/block.v1.schema.json:3`) | main, evidence-foundation owner | Bounded consumer projection over one or more references (`:5`). |
| `contracts/evidence_foundation/recipe.v1.schema.json` | consumer recipe v1 (`origin/main:contracts/evidence_foundation/recipe.v1.schema.json:3`) | main, evidence-foundation owner | Versioned ordered composition recipe for one consumer job (`:5`). |
| `contracts/evidence_foundation/vocabulary.v1.json` | `1.0.0` (`origin/main:contracts/evidence_foundation/vocabulary.v1.json:3`) | main, evidence-foundation owner | Closed object/clock/subject/reader vocabulary shared by Evidence Foundation references. |
| `contracts/sector_intelligence/authority_manifest.v1.schema.json` | authority manifest v1 (`origin/main:contracts/sector_intelligence/authority_manifest.v1.schema.json:3`) | main, sector-intelligence owner | States maximum authority, permitted and denied actions, consumers, kill switch and governance references. |
| `contracts/sector_intelligence/entity_link.v1.schema.json` | entity link v1 (`origin/main:contracts/sector_intelligence/entity_link.v1.schema.json:3`) | main, sector-intelligence owner | Binds a source entity to a canonical entity with method and confidence. |
| `contracts/sector_intelligence/evidence_claim.v1.schema.json` | evidence claim v1 (`origin/main:contracts/sector_intelligence/evidence_claim.v1.schema.json:3`) | main, sector-intelligence owner | Consumer-facing evidence claim with refs and degradation context. |
| `contracts/sector_intelligence/feature_snapshot.v1.schema.json` | feature snapshot v1 (`origin/main:contracts/sector_intelligence/feature_snapshot.v1.schema.json:3`) | main, sector-intelligence owner | Dated sector feature inputs for downstream read models. |
| `contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json` | finance intelligence read model v1 (`origin/main:contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json:3`) | main, sector-intelligence owner | Existing finance-panel projection including `rights_profile` fields (`:119,139`). |
| `contracts/sector_intelligence/lobe_run.v1.schema.json` | lobe run v1 (`origin/main:contracts/sector_intelligence/lobe_run.v1.schema.json:3`) | main, sector-intelligence owner | Receipt for one governed sector computation run. |
| `contracts/sector_intelligence/outcome_label.v1.schema.json` | outcome label v1 (`origin/main:contracts/sector_intelligence/outcome_label.v1.schema.json:3`) | main, sector-intelligence owner | Labeled sector outcome with evidence and period. |
| `contracts/sector_intelligence/prediction.v1.schema.json` | prediction v1 (`origin/main:contracts/sector_intelligence/prediction.v1.schema.json:3`) | main, sector-intelligence owner | Governed descriptive prediction projection, not an action authority. |
| `contracts/sector_intelligence/sector_event.v1.schema.json` | sector event v1 (`origin/main:contracts/sector_intelligence/sector_event.v1.schema.json:3`) | main, sector-intelligence owner | Dated, evidenced sector event. |
| `contracts/sector_intelligence/sector_intelligence_packet.v1.schema.json` | packet v1 (`origin/main:contracts/sector_intelligence/sector_intelligence_packet.v1.schema.json:3`) | main, sector-intelligence owner | Governed packet envelope used by downstream dossier/read-model governance. |
| `contracts/sector_intelligence/source_record.v1.schema.json` | source record v1 (`origin/main:contracts/sector_intelligence/source_record.v1.schema.json:3`) | main, sector-intelligence owner | Source identity, clocks and receipt metadata for sector inputs. |
| `contracts/theme_graph/nodes.v1.schema.json`, `edges.v1.schema.json`, `evidence.v1.schema.json`, `capability.v1.schema.json`, `identity_resolution.v1.schema.json`, `node_lifecycle.v1.schema.json`, `probation_proposal.v1.schema.json`, `cn_limit_rules.v1.schema.json` | each is a frozen `.v1` row/schema contract (`origin/main:contracts/theme_graph/README.md:3-5`) | main, theme-graph owner | The semantic spine's bitemporal nodes, edges, evidence, capability, identity, lifecycle, probation and CN limit contracts. |
| `contracts/theme_graph/evidence.v1.schema.json` | theme-graph evidence row v1 (`origin/main:contracts/theme_graph/evidence.v1.schema.json:3-4`) | main, theme-graph owner; #7870 extends it additively | Dated evidence receipt for graph relations, including source/ref and licensing snapshots (`:5`). |
| `engine/sector_intelligence/contracts.py` | explicit sector contract registry (`origin/main:engine/sector_intelligence/contracts.py:1-7`) | main, sector-intelligence owner | Fail-closed discovery, validation and hashing for owned sector contracts. |
| `engine/sector_intelligence/launch_slo_verifier.py` | verifier module; launch-SLO contract is v1 | main, sector-intelligence owner | Verifies launch-SLO evidence for sector contract changes. |
| `engine/theme_graph/{capability,identity,identity_resolution,local_sources,materialize,probation,rights,store}.py` | modules; contracts they produce are v1 (`origin/main:contracts/theme_graph/README.md:3-5`) | main, theme-graph owner | Capability rules, identity topology and Data OS bridge, source vintages, graph materialization, probation, source-family rights and append-only stores. |
| `engine/market_ontology/exposure_map.py`, `ticker_cik_census.py` | modules without an inline contract version | main, market-ontology owner | Exposure and ticker/CIK census support for ontology mapping. |

### PR additions and changes

| Ref / PR | Item | Version | Status / owner | Purpose |
|---|---|---|---|---|
| #7870 | `contracts/theme_graph/curation_assertion.v1.schema.json` + `engine/theme_graph/curation_assertion.py` | `theme_graph.curation_assertion.v1` (`origin/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9:contracts/theme_graph/curation_assertion.v1.schema.json:3,5,26`) | draft PR; authored in Semiconductor B as the one shared payload under R1 (`agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-semiconductor-b-implementation.md:152`) | Tamper-evident curated statement about a theme participant, with all authority flags structurally false. |
| #7870 | `contracts/theme_graph/evidence.v1.schema.json` change | still evidence row v1 | draft PR, additive | Allows one optional encoded `curation_assertion` reference on an evidence row (`contracts/theme_graph/evidence.v1.schema.json:60-65`). |
| #7870 | `engine/theme_graph/admission.py` | path-logic classifier, no versioned schema | draft PR, Semiconductor B T03 | Classifies a candidate evidence root as private or refuses public/symlink/missing/invalid roots (`engine/theme_graph/admission.py:1-15,58-72`). |
| #7870 | `engine/theme_graph/rights.py` changes + registry snapshot API | registry `version: 1` (`config/theme_sources.yml:18`) | draft PR, Semiconductor B T03 | Fresh byte-level registry snapshots and current-emission gating so a rights change reaches emission without rewriting history (`engine/theme_graph/rights.py:126-135,211-241`). |
| #7870 | `contracts/market_ontology/semiconductor_theme_research.v1.schema.json` + `engine/market_ontology/semiconductor_theme_research.py` | schema v1; composition `definition_version 2026-09-24.1` (`engine/market_ontology/semiconductor_theme_research.py:62-66`) | draft PR, Semiconductor B T07/T08 | Pure in-memory composition of theme research with all-false authority, no I/O or scoring (`engine/market_ontology/semiconductor_theme_research.py:1-7,68-76`). |
| #7870 | `contracts/evidence_foundation/vocabulary.v1.json` change + contract tests | still `1.0.0` (`contracts/evidence_foundation/vocabulary.v1.json:3`) | draft PR, evidence-foundation extension accepted in carrier | Extends the shared vocabulary for Semiconductor B subject/context types without creating a second evidence plane. |
| #7870 | `templates/state_of_themes.html.j2` + theme-research CSS/JS | presentation companion to research v1 | draft PR, Semiconductor B display lane | Generic theme-research mount, endpoints, paid/auth gate, evidence drawer and authority refusal on the Theme Tracker page (`templates/state_of_themes.html.j2:641-658`; `site/assets/js/theme-research.js:1-27`). |
| #7780 | 13 research/process/design documents under `research/` | n/a | research PR, Semiconductor B-first planning | Records research, self-review, replay/boundary and design inputs; changes no foundation code. |
| #7777 | `contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json` | `sector_dossier_read_model.v1` / `schema_version 1.0.0` (`origin/sol/stsi1-sector-federation-technology-dossier-20260921:contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json:3-5,34-42`) | feature PR, STSI sector-federation owner | Canonical governed read model for a sector dossier and its receipts/governance/authority ceiling. |
| #7777 | `engine/sector_intelligence/contracts.py` registration + `tests/test_sector_dossier_contract.py` | uses `sector_dossier_read_model.v1` | feature PR | Registers and validates the dossier contract, hash, governance bindings, source refs and authority ceiling (`engine/sector_intelligence/contracts.py:21-33`; `tests/test_sector_dossier_contract.py:250-265`). |

STATUS: ANSWERED

## Q2 — Evidence and rights integration

The foundation separates **owner-native truth**, **pointer receipts**, **consumer projections** and **curation assertions**: an Evidence Foundation reference is pointer-only and never contains the native body (`origin/main:contracts/evidence_foundation/reference.v1.schema.json:5`), a block is a bounded projection (`origin/main:contracts/evidence_foundation/block.v1.schema.json:5`), a recipe composes blocks for one job (`origin/main:contracts/evidence_foundation/recipe.v1.schema.json:5`), and theme-graph evidence is a dated relation receipt (`origin/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9:contracts/theme_graph/evidence.v1.schema.json:5`). CDV-1 should preserve `event_fact.v1` as its owner-native fact shape while exposing provenance through those foundation contracts—not convert facts into theme-graph rows or research values into native receipts.

| CDV-1 concept | Foundation concept | Ruling | Cheapest reconciliation |
|---|---|---|---|
| `event_fact.v1` | Evidence Foundation owner-native object / reference | SAME provenance concept; keep the fact shape | Bind fact identity, clocks, subject and source handles to an Evidence Foundation `reference.v1` after #7870's vocabulary extension merges; never mirror the fact into `theme_graph/evidence.v1`. `event_fact.v1` already carries explicit event, metric, value, period, basis and source span (`origin/main:engine/company_intelligence/event_workspace_build.py:273-285`). |
| `source_document.v1` | owner-native object and native digest/identity | SAME | Keep `SourceDocument` as CDV's document truth. It already carries digest, revision, clocks, rights profile/state, predecessor and held-bytes state (`origin/main:engine/company_intelligence/documents.py:150-173`). Expose a pointer receipt with matching native identity/digest through Evidence Foundation; do not replace document validation with a theme evidence row. |
| `source_span.v1` | Evidence Foundation block / bounded projection; theme research evidence receipt | SAME projection concept; keep the byte-replay contract | Keep `source_span.v1` byte replay as the owner projection (`origin/main:engine/company_intelligence/documents.py:15-25`, `:328-345`, `:468-490`). A dossier should cite its safe span/projection and resolve to the owner document; it must not store full bodies or pretend address-only evidence is replayable. |
| private manifest v2 `workspaces` | workspace is an owner-native dependency closure | SAME; keep in earnings private owner | Plan line 162 defines the roles as receipt roles in one publication, not stores (`origin/sol/consumer-defensive-research-20260923:docs/superpowers/plans/2026-09-23-consumer-defensive-cdv1-implementation.md:162`). Keep the existing private store, pointer and publication owner; do not create a theme-graph publication clone. |
| private manifest `documents` / `source_bodies` | Evidence Foundation references + role-bound private artifacts | SAME ownership; DISJOINT storage mechanics | Evidence Foundation explicitly forbids a body in its reference (`origin/main:contracts/evidence_foundation/reference.v1.schema.json:5`). Keep raw/decoded bodies in role-bound private artifacts, but bind identity, digest and reader metadata to the shared vocabulary/reference rather than inventing a new pointer grammar. |
| private manifest `selections` / `economic_slots` | consumer projection / recipe, not owner truth | SAME consumer semantics; keep in v2 | `selections` name selected native facts and `economic_slots` is a derived display selector resolving an admitted issuer to a record/event (`docs/...cdv1-implementation.md:162-165`). Model the display selection as a bounded recipe/projection when integrating, without making it an issuer registry or second event catalog. |
| `rp_public_primary_v1` | theme-graph rights family registry | CONFLICT: static profile string versus current source-family rights | Keep the profile as a CDV document/span classification, but add a mapping from that profile/SEC source family to `config/theme_sources.yml` and enforce current emission/read permission through `rights.py`. #7870's fresh snapshot returns a byte revision and fails closed on a missing/corrupt registry (`origin/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9:engine/theme_graph/rights.py:126-135`); the snapshot gate refuses unknown/unpermitted families (`:222-241`). |
| `rp_unknown_v1` | fail-closed rights posture | SAME | Leave unknown as unknown. CDV defaults spans/documents to `rp_unknown_v1` (`origin/main:engine/company_intelligence/documents.py:167,315`), matching the foundation's requirement that rights be stated and unknown families refuse (`engine/theme_graph/rights.py:159-176,222-241`). |
| private publication storage | #7870 `admission.py` private-root classifier | DISJOINT for this task | The classifier is filesystem/path based and classifies a candidate evidence root containing `evidence.parquet` (`origin/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9:engine/theme_graph/admission.py:1-15,37-41,58-72`). CDV Task 4 uses an object-store closure with readback and digest checks, so retain that owner validation; use `admission.py` only if/when a filesystem theme-research root is bound. |
| curated economic context | `theme_graph.curation_assertion.v1` | SAME curation concept; do not use it to originate facts | Use the shared assertion for a human/curated statement about theme participation, with source, revision, scope and all-false authority (`contracts/theme_graph/curation_assertion.v1.schema.json:3-5,26-28,217-227`). Keep deterministic CDV interpretation in `earnings.economic_interpretation/v1`; an assertion may inform display, never substitute for a native fact. |

STATUS: ANSWERED

## Q3 — Dossier read model

STATUS: IN PROGRESS

## Q4 — Shell integration

STATUS: IN PROGRESS

## Q5 — Theme-graph admission for Consumer Staples

STATUS: IN PROGRESS

## Q6 — CDV-1 task recommendations

STATUS: IN PROGRESS
