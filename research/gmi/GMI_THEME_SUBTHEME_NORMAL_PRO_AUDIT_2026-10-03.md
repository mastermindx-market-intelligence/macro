# GMI Theme/Subtheme Intelligence — Normal Pro Audit and Current-System Census

**Date:** 2026-10-03  
**Mode:** normal Pro audit; no additional Deep Research run  
**Parent:** PR #8324  
**Program:** `WS:GMI-THEME-GRAPH`

## Audit ruling

The research report in PR #8324 has the right north star and ownership philosophy, but its current-state census is too compressed to be the implementation authority by itself. It correctly says not to rebuild D2C/D2D and not to create duplicate owners, but it understates the amount of already-built thematic infrastructure and does not make the current dependency frontier precise enough.

The revised program must begin with **D2 acceptance + ThemeState authority reconciliation + STSI/Theme Intelligence carrier reconciliation**, not a generic architecture wave.

## Protected-source pin

Current protected procedure was re-read from `mastermindx-market-intelligence/Mastermind@20adcaf65c2dd1bb734ab06e215feb1a0eb65659`. INDEX is `mastermind.sol_skillpack.v1` / 1.0.1 / bootstrap-major 1. COLD_START, ACTIVE_EXECUTION, RECONCILE_STATE and WEB_CEO_DELEGATION were loaded from that same commit. SESSION_RELIABILITY is not enrolled by current INDEX.

## Material census findings

### 1. GMI graph substrate is substantially real

Current main contains the GMI graph materializer and owner modules. `engine/theme_graph/materialize.py` explicitly preserves source grain: MEMBER_OF company→basket, EXPRESSES basket→theme, TRACKS ETF→basket; it deliberately refuses to mint a derived company→theme fact. It distinguishes reconstruction from observed history and stores belief time separately from valid time.

D2C is not TODO in implementation truth. #6809 implemented THS membership materialization from the incumbent PIT history and explicitly refuses current-membership backdating. #7458 repaired a real post-merge parquet evidence-ref defect discovered by a 57,010-row replay. These are **DO_NOT_REDO**; what remains is current acceptance, natural-refresh/correction proof, and durable state repair.

D2D is also materially implemented. #7462 contains exact ontology/history/membership/evidence readers, structural-reference navigation, strict parquet refusal, proposal identity verification and research-only curation tooling. It remains DRAFT/HOLD/RESEARCH_INTERNAL_ONLY in its own release record, so it is **BUILT_NOT_PROVEN**, not TODO and not accepted production capability.

### 2. The largest unresolved authority issue is ThemeState

A real predecessor ThemeState already exists today: `engine/neuralweb/thematic_state.py` produces `neuralweb.theme_state.v1`, writes `data/neuralweb/theme_state.json`, mirrors it to `site/neuralwebdata/theme_state.json`, and appends `theme_phase_history.jsonl`. It is context/display-only and composes Foresight, baskets, Radar, narrative, subsector rotation and divergence inputs.

This is not hypothetical. The current evidence-estate census explicitly records that Neural Web ThemeState has **no Theme Graph join in code**. Therefore the problem is not “build ThemeState from scratch”; it is “decide and execute the sole-owner migration.”

The original W3B ruling remains sound: GMI must own canonical ThemeState after D2, and Neural Web predecessor lineage must be extended/superseded/fenced so only one truth store survives. But the implementation plan must treat the live Neural Web producer as an incumbent with migration/cutover risk, not as mere historical context.

### 3. Theme Intelligence is already a multi-lane system

The report compressed Theme Intelligence into “PARTIAL,” but the estate is more specific:

- #7526 Lane A repairs WATCH vs deterioration and emits additive `theme_intelligence.consumer.v1` dimensions. It explicitly does not replace GMI ThemeState.
- #7455 Lane C implements closed-session subtheme leadership observations; current release state remains BUILT_NOT_PROVEN / draft / unmerged.
- #7508 Lane D implements fail-closed group/member entry context and keeps all rank/gate/size/trade authority false.
- #7453 Lane F contains an independent convergence evaluator and records accepted/held sibling states.
- Lane B economic evidence was explicitly recorded by Lane F as NOT_YET_PROVEN at its census point.
- #7664 Lane E presentation/visibility remains held with unresolved source-boundary defects.

These should not be rebuilt as new GMI modules. They should be reconciled into the canonical federation with explicit producer ownership.

### 4. STSI is more advanced than the report implies

The STSI architecture already selects owner-preserving federation rather than a new graph or score. #7211 is the focused Sector Intelligence publication owner and later production evidence cited by #7777 records authenticated HTTP 200 for four protected Sector Intelligence artifacts. #7777 adds the governed dossier read-model contract with typed conflicts, source refs, authority and null-preserving concentration.

Therefore “build federation” is too broad. The next work is to **extend the existing STSI contract from sector-first dossier federation to theme/subtheme federation and bind it to canonical GMI ThemeState**, while preserving #7211 publication ownership.

### 5. Member evidence and entry are existing specialist planes

#7252 already provides source-bound member evidence and detailed missingness/provenance behavior, but remains OPEN/DRAFT/BUILT_NOT_PROVEN pending hosted CI and production-path acceptance.

#7508 already provides entry context and explicitly prevents group entry state from becoming stock eligibility. ThemeState should reference these specialist observations rather than absorb them.

### 6. Subtheme qualification has a newer scientific repair line

#8299 is a newer successor to the #7749/#7455 research line. It repairs missingness-to-leadership leakage, uses a common comparable cohort, makes incomplete groups unavailable rather than ranked, and keeps index participation withheld when coverage is incomplete. It remains BUILT_NOT_PROVEN and explicitly says qualified historical memberships, weights, knowledge clocks, corporate actions/delistings and prices are still required before real-market evaluation.

This materially strengthens the revised evaluation plan: **coverage/missingness qualification is a prerequisite to leadership validation**, not a later polish item.

### 7. Economic thematic research has a real shared-foundation carrier

#7870 is the incumbent shared Theme Research + Semiconductor vertical carrier and explicitly forbids replacement infrastructure. It is PARTIAL / BUILT_NOT_PROVEN / HOLD. #7886 is the GMI Meta-CEO research/integration line and records cross-domain decisions and domain child research.

The revised plan must not “build an economic kernel” as if none exists. It must **accept/reconcile the reusable shared leaf from #7870, separate semiconductor-specific semantics, and prove at least two dissimilar domain adapters**.

### 8. Current durable program state is stale

`WS:GMI-THEME-GRAPH` still says D2C and D2D are TODO. This is a material false-negative project-state defect. The workstream also still sequences D2E→W3B→W3C as though later STSI/Theme Intelligence/economic-research programs had not emerged.

The revised plan must repair Agent OS only after implementation truth is proven. Do not cosmetically flip TODO to done without current acceptance evidence.

## Revised capability ledger

| Capability | State | Audit disposition |
|---|---|---|
| W3A local theme plane | BUILT_NOT_PROVEN | accept/prove, do not rebuild |
| D2C PIT materialization | BUILT_NOT_PROVEN | accept #6809+#7458 on current main |
| D2D ontology/readers | BUILT_NOT_PROVEN | accept #7462 or successor; no duplicate reader |
| D2E rights/coverage acceptance | PARTIAL / NOT CLOSED | make this the first true GMI closure gate |
| Neural Web ThemeState predecessor | PROVEN_LIVE as display/context predecessor; DARK_OR_DISCONNECTED from GMI graph | migrate/reconcile |
| Canonical GMI ThemeState | NOT_BUILT as sole accepted owner | build by migration, not greenfield duplication |
| Theme Intelligence Lane A | BUILT_NOT_PROVEN / source landed historically | consume |
| Lane C subtheme leadership | BUILT_NOT_PROVEN | finish/qualify with #8299 |
| Lane D entry context | BUILT_NOT_PROVEN | consume as specialist |
| Lane E presentation | PARTIAL / HELD | repair through incumbent |
| Lane F evaluator | BUILT_NOT_PROVEN | reuse |
| STSI architecture | SPEC + partial implementation | extend existing federation |
| STSI dossier contract | BUILT_NOT_PROVEN | extend to theme/subtheme |
| Sector publication | PROVEN_LIVE for cited focused artifacts | reuse publisher |
| Member evidence #7252 | BUILT_NOT_PROVEN | finish release/prod proof |
| Economic shared foundation #7870 | PARTIAL / BUILT_NOT_PROVEN | finish/reconcile |
| GMI thematic research #7886 | PARTIAL | fold into shared grammar |
| Company theme exposure | PARTIAL / owner-fragmented | extend incumbent Company owner only |
| Prophet thematic authority | NOT_BUILT by design | context only until Evaluation promotion |
| Prospective theme/subtheme Evaluation | NOT_BUILT end-to-end | begin capture early |

## Research-report corrections

1. Replace “D2C/D2D are BUILT_NOT_PROVEN” with exact acceptance obligations and current carriers.
2. Replace “ThemeState convergence is PARTIAL” with the stronger fact: a live Neural Web predecessor exists and is disconnected from Theme Graph; canonical GMI ThemeState remains unbuilt as sole owner.
3. Replace generic “STSI federation” with an extension of the existing STSI architecture + #7777 dossier contract + #7211 publisher.
4. Treat Theme Intelligence lanes as incumbent specialist producers, not a single vague subsystem.
5. Treat #8299 coverage/missingness qualification as a prerequisite to subtheme scientific evaluation.
6. Treat #7870 as incumbent shared economic-research infrastructure; do not create a replacement kernel.
7. Start prospective snapshot capture before all product integration is complete so evaluation history accrues while implementation proceeds.
8. Separate “source merged,” “contract accepted,” “natural refresh proven,” “published,” “browser proven,” “machine consumed,” and “prospectively evaluated” in every wave.

## True frontier

The old sequence `D2C + D2D → D2E → W3B → W3C` should be updated to:

`D2C/D2D CURRENT ACCEPTANCE → D2E RIGHTS/COVERAGE/ELIGIBILITY CLOSE → THEMESTATE MIGRATION + STSI READ-FEDERATION CONTRACT → parallel specialist convergence (leadership / economic research / company exposure / member evidence) → product + machine consumer migration → discovery/cross-theme → prospective evaluation/promotion`.

W3C cohort intelligence is no longer a standalone final wave; its useful job becomes a consumer of the canonical read model and should be folded into Prophet/US-China cohort context without ranking authority.
