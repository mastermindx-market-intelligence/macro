# News evidence-sensitive phrasing repair

Parent: Macro #7953. Operation: news-evidence-phrasing-20260927-sol-001.
Bounded extension to the existing Intelligence Desk; source baseline 90f9fcbe31fff9fe96bd293190372d1c773fab9c (product files unchanged at 93b98bf4a4fad08c62ccc6cdb4a19b7c381a0435).

## Outcome
A developing story must not keep an old model explanation merely because its headline is unchanged. Duplicate arrivals must not buy duplicate model attempts. A disabled/failed/rejected model must leave current deterministic facts, not resurrect a previous interpretation. This is research/news context, not a forecast or trade score.

## Existing owners retained
- intelligence_llm owns the existing optional fact-packet phrasing pass and bounded host-local cache.
- intelligence_desk owns the existing SQLite story packets, merge and atomic snapshot.
- Existing per-shape draft IDs and admin approval remain unchanged. No new outbox, queue, history store, publisher, identity or model provider.
- No provider activation, credentials, real model requests, live source calls or production writes occur in this work.

## Implemented contract
1. Cache keys cover exactly the supplied fact packet plus current prompt, output shapes, configured model policy and length/token budgets. Source/ticker lists are normalized as sets; story IDs retain existing ownership. Legacy headline-only rows are requalified once within the existing budget and replace the same cache row.
2. Same-story/same-fact duplicates share an attempted call within a tick. Existing counters additionally distinguish duplicates and eligible rows deferred by the unchanged attempt cap. Cached rows remain accounted for even after the cap is reached.
3. Changed headline/body/tickers/event lane/source count/market observation retire the stored LLM why and all stale LLM draft shapes. Current incoming accepted copy can replace them; otherwise deterministic copy stands. Chinese explanation follows the winning English fact revision.
4. Expired or unstamped market context clears dependent generated copy in the served view. It does not rewrite historical evidence or call a model. Old draft IDs disappear from the existing snapshot, so the existing server-side approval reread refuses a stale browser click.
5. Existing source validation, number/call-language rules, arming gates, TTL, cache cap, per-tick attempt limit, publication approval and trade boundaries are not relaxed.

## Important limits
The fingerprint authenticates equality of supplied facts, not the truth or independence of those facts. Source diversity is not newly relabeled as independent confirmation. It does not solve event extraction or correction lineage beyond fields that the existing packet actually supplies.
Market as_of remains an input because the model can see it. Changed quote observations may requalify a story even when the headline is unchanged; this protects stale temporal claims but can increase eligible requests. Existing attempt budgets remain the hard cap. These source tests do not establish runtime cost savings, investment value, or actual provider behavior.
Configured model identity is not a claim about which fallback provider answered. Existing retry/failover rules are unchanged. The code-review waiver does not waive editorial approval of a publication draft.

## Evidence
Initial new regressions on original product: 15 failures and one unchanged-input control pass. Extended negative controls restoring both original modules: 20 failures and one control pass, including the real admin path accepting a superseded suggestion into a TEMPORARY fixture outbox. The repaired version refuses that same stale ID before enqueue.
Whole existing suite plus new tests: 91 passed. The original 69 cases remain; no cases are removed or skipped. Separate thin-import proof passed87 tests with pandas/numpy/requests/anthropic/openai/fastapi/PIL/datasketch imports denied and sockets disabled; final current-suite thin proof passed91 with the same network/import prohibitions.
Tests exercise real cache writes, validators, SQLite merges, snapshots and admin reread with only provider calls replaced. No real vendor/model call occurs.
Missing files in the first selected-source snapshot were fetched unchanged before valid controls; those import/lexicon failures are not product bugs.

## Release
Publish one bounded draft PR; fresh applicable CI and current-main integration are required. The parent News program's independent-review waiver applies; no Codex/Executive dependency is created. Deployment of the existing daemon and real served-path verification remain separate obligations. Do not conflate source merge with activation or live acceptance.


## Source-gate qualification
The desk suite previously ran only in marketing-engine (gate:data). It now runs once in the existing unrun-marketing-desk (gate:code); its old data-only occurrence is removed. No new CI job, runner, dependency installation or threshold is introduced.
The unchanged Git-backed scope engine at main93b98bf4a4fad08c62ccc6cdb4a19b7c381a0435 qualifies the actual old/new job:285 ->312 named paths with all previous owners retained; fallback paths unchanged. Existing homepage/free-content/Prophet probe membership is unchanged (this job already selected all three). The job's honest estimated weight rises13 ->16 for its additional test step; no packing limit is raised. This is changed-job analysis, not a claim that the global CI census ran locally.
The actual Git-qualified runtime source passes the complete91-case desk suite. Retained tests include real SQLite persistence, the Content Studio reader, recursive public-field exclusions, bilingual handling, number/call gates, cache budgets, snapshot expiry and old-browser-draft refusal. There is no UI layout change or new browser-capture claim.
