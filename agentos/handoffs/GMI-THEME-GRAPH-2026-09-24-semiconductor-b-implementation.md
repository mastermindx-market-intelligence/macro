---
workstream: "WS:GMI-THEME-GRAPH"
session: claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9
model: fable
ended_because: ci_handoff
mission: >
  Implementation carrier and cumulative working checkpoint for
  gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001: ship Semiconductor Theme
  Intelligence B (paid Themes research journey with the TSMC HBM/advanced-packaging
  witness W-A and the onsemi SiC/GaN/specialty witness W-B) through the existing
  GMI/K1/Earnings/FIF/rights/F04/Macro-API owners, orchestrated by one Fable principal
  with bounded fabric children. C1 (SBD-41..48) stays deferred.
state_before: >
  Research/spec/plan/handoff truth existed only on draft/HOLD PR #7780 at
  b68069b2e1296bfc772e4f4e3a0c1cc3845f89eb. No implementation carrier, no PICKUP_ACK,
  no START, no product code. Macro main at packet preparation was dd4d965de7d52f4c68f6dbc984c7a05a70e0d62b.
changed:
  - path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-semiconductor-b-implementation.md
    what: "Created the implementation-operation working checkpoint: pickup receipt, procedure pin, current-main/custody reconciliation, Fable custody rulings R1-R4, wave plan and exact next action; updated with wave-1 dispatch, the R4/T05 read-only qualifications, the fabric ship-loop incident and the R4 DECISION_REQUEST; updated again after wave-1 integration (38d950bdabb3), the T02 REJECT review and its fix commit (2deb758859d7), the T05 GLM content-filter failure and the wave-2 dispatch queue."
verified:
  - claim: "Current protected procedure is compatible and loaded from one pin."
    command: "git rev-parse origin/master in Mastermind; read docs/sol_skills/INDEX.md, ACTIVE_EXECUTION.md, WEB_CEO_DELEGATION.md, WATCHER_ACTION_LOOP.md, RECONCILE_STATE.md, docs/AGENT_DIALOGUE_SESSION_CLOSE_LAW.md, docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md at that commit"
    result: "Mastermind a7d2b3049e5cdc523e91e61a6e9d70a1cb911157; Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap 1; same pin as the #7780 packet."
  - claim: "PICKUP_ACK for the operation is durably recorded on the packet carrier."
    command: "gh pr comment 7780 --body-file /tmp/pickup_ack_7780.md"
    result: "https://github.com/mastermindx-market-intelligence/macro/pull/7780#issuecomment-5807221991"
  - claim: "Macro main movement since the packet pin is disjoint from every planned B path."
    command: "git diff --stat dd4d965de7d52f4c68f6dbc984c7a05a70e0d62b 9438880952d3375b00a042381705c2e6c85305e3 -- contracts/theme_graph contracts/evidence_foundation contracts/market_ontology engine/theme_graph engine/market_ontology engine/company_intelligence lib/evidence_foundation.py app/main.py app/earnings.py app/paywall.py templates/basket_detail.html.j2 templates/state_of_themes.html.j2 scripts/check_theme_graph_contracts.py tests/test_theme_graph_contracts.py tests/test_evidence_foundation_contract.py config/theme_sources.yml config/theme_crosswalk.yml"
    result: "Empty diff on planned paths; main moved only research_vault catalog + .github/ci options scope (2 files). Carrier base = 9438880952d3375b00a042381705c2e6c85305e3."
  - claim: "Dependency carriers are unchanged since packet preparation and no STARTed or EFFECT_UNKNOWN operation owns the planned implementation."
    command: "gh pr view 7773 7462 7669 --json headRefOid,state,isDraft; gh pr list --search semiconductor; git branch -r | grep -iE 'semi|robot'; Slack search for the operation key and PICKUP_ACK after 2026-09-21"
    result: "#7773 f10211657c6c open/draft; #7462 31706d7322af open/draft (last commit 2026-09-22 03:04 -0700, store.py hunks = strict-read flags at lines 208-300); #7669 2c28d950aa94 open/draft HOLD-FOR-SOL (template hunks in JS render functions ~402-1502). No robotics or semiconductor implementation branch/PR exists. No Slack thread root exists for this operation."
  - claim: "Bounded custody questions were posted to both held source owners."
    command: "gh pr comment 7462 --body-file /tmp/custody_7462.md; gh pr comment 7669 --body-file /tmp/custody_7669.md"
    result: "#7462 issuecomment-5807268400 (one-line EVIDENCE_COLUMNS append); #7669 issuecomment-5807268641 (generic hidden research mount + two asset includes). Both hunks remain frozen until answered."
  - claim: "Native owner interfaces named by the plan exist on the carrier base."
    command: "git show origin/main:<path> for contracts/theme_graph/evidence.v1.schema.json, engine/theme_graph/store.py, engine/theme_graph/rights.py, lib/evidence_foundation.py, contracts/evidence_foundation/vocabulary.v1.json, engine/company_intelligence/{event_workspace,event_workspace_build,issuer_profiles,identity}.py, contracts/financial_intelligence_packet.schema.json, app/earnings.py, app/paywall.py, engine/earnings_narrative/private_publication.py, engine/research_vault/r2_store.py, templates/basket_detail.html.j2, templates/state_of_themes.html.j2, config/theme_sources.yml, config/theme_crosswalk.yml"
    result: "All present. EVIDENCE_COLUMNS has 12 columns and no curation_assertion; rights registry has 3 families (mastermind_curated direct_display_ok; finviz_themes, ths_concepts unresolved); production_registry enrolls AAPL + DHI/PHM/KBH/TOL only; ticker_cik_ledger has ON=1097864 and no TSM row; vocabulary owner_stores has 13 entries and no curation subtype."
  - claim: "START was emitted separately from PICKUP_ACK and the one implementation carrier exists."
    command: "gh pr comment 7780 --body-file start_7780.md; gh pr create --draft --base main"
    result: "START = https://github.com/mastermindx-market-intelligence/macro/pull/7780#issuecomment-5807391383; carrier = #7870 (draft), first commit 545ece0c7177a56627204e77302cd9c2d4d03f3e on base 9438880952d3."
  - claim: "Wave-1 children returned commits that pass their deterministic gates on a second environment (Studio python3.14) before integration."
    command: "python3 -m pytest tests/test_semiconductor_research_inputs.py -q (fe9238b9aeee); python3 -m pytest tests/test_theme_research_private_binding.py tests/test_theme_research_rights_refresh.py -q plus test_theme_sources_registry/test_market_ontology_exposure_map/test_deploy_update_self_heal/test_theme_graph_contracts (d30457d5de7c); python3 -m pytest tests/test_semiconductor_guidance_history.py tests/test_issuer_profiles_a5a.py -q (53c5bd3702f3)"
    result: "T01 9 passed, leak-guard grep NONE, 26 files; T03 30 passed + 364 adjacent passed, store.py diff 0 lines; T06 32 passed + 38 adjacent passed, fixtures leak-guard NONE. Independent Opus READ_ONLY reviews launched for all three (builder != reviewer; MiniMax output under R20)."
  - claim: "Candidate (i) for the R4 private binding is public by construction."
    command: "gh api repos/mastermindx-market-intelligence/macro --jq '{private,visibility,forks_count}'; curl -sI https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/main/data/theme_graph/evidence.parquet; git ls-files data/theme_graph; grep -n 'git add data/' scripts/ci/daily_engine_commit_outputs.sh"
    result: "private=false visibility=public forks=0; raw parquet HTTP 200; evidence.parquet tracked; daily engine job commits data/ (line 64); lib/config.py data_dir() has no env override and store.py path functions take no root argument, so candidate (iii) is not constructible per-store."
  - claim: "The Earnings owner is form-agnostic and only its intake filter blocks a 6-K; onsemi is silently skipped today by the fiscal cross-check."
    command: "read-only Opus qualification over engine/company_intelligence/*, scripts/refresh_event_workspaces.py:210-233,632-634,663-716,1021-1029, engine/fundamental_forensics/metric_registry.py:50-53, data/edgar/ticker_cik_ledger.json; SEC submissions/exhibits for CIK 0001046179 and 0001097864 fetched read-only"
    result: "build_event_workspace + validate_event_workspace accept a real TSMC 6-K unchanged; _select_newest_results_rows admits only 8-K with Item 2.02 and every TSMC 6-K row has items==''; onsemi 52/53-week period ends (2026-04-03, 2026-07-03) fail the calendar cross-check and the 'quarter ended' regex; ticker ledger has ON=1097864 and no TSM; FIF registry excludes IFRS/TWD/20-F (typed gap for W-A financial packet); guidance_item.v1 has no validator and no currency field; tests/test_issuer_profiles_a5a.py:114 pins len(registry)==5."
  - claim: "Wave 1 (T01 fixtures, T03 rights/admission, T06 guidance history) is integrated on the carrier with review nits applied and CI wiring."
    command: "git cherry-pick -x fe9238b9 53c5bd37 d30457d5; edit .github/ci/legacy-jobs.yml (two new run: steps + one suite appended to the company-intelligence core step); python3 scripts/audit_unrun_tests.py; combined pytest"
    result: "Carrier 38d950bdabb3 pushed to #7870; #7874 closed with a pointer; stray claude/semi-b-* origin branches deleted; unrun-suite audit clean except base-inherited tests/test_render_dead_ref_targets.py; ledger outcomes recorded for T01 (MiniMax-M2.7-highspeed, reviewer-accepted) and T03 (glm-5.3-flash, reviewer-accepted)."
  - claim: "The T02 fix commit closes all three review blockers to an independent reviewer's satisfaction."
    command: "general-purpose Opus READ_ONLY re-verification of 2deb758859d7 (Robotics reference payload proof, recursion probe under setrecursionlimit(200), schema closure walk, gate, audit_unrun_tests, identity-test probes)"
    result: "ACCEPT_WITH_NITS: B1/B2/B3 CLOSED (encode of stamped vs unstamped byte-identical, gmi-curation://robotics_automation/gmirca_18d7852490e571465270aa5024442859, caller dict unmutated); 130 passed, 1 xfailed; fixtures unchanged; store.py/basket_detail untouched; identity test admits only https://example.invalid/. Nits taken in 012db0e6dc59."
  - claim: "T10 part 1 (m1 glm-5.3 lane commit f53c7c3845b3) was independently reviewed and REJECTED on two local law violations; everything else is clean."
    command: "general-purpose Opus READ_ONLY review over the T10 review worktree (sparse-checkout disabled): leak/XSS/authority/bilingual/mount checks, pytest, node --check, regression tests/test_state_of_themes.py"
    result: "REJECT. Blocking: (1) time-mode <option> labels built with .l-en/.l-zh spans render both languages concatenated (repo fix pattern site/assets/js/a7851105.js:763-773: data-en/data-zh + langchange relabel); (2) `limitations` (and authorized_coverage) validated but never rendered (root cause: the commission's UI list omitted it; seat rules the LAW authoritative — a coverage caveat is mandatory). Clean: no token/payload/URL leak, zero innerHTML, authority flags refused unless literal false, no client arithmetic on paid figures, mount hidden with the .theme-research[hidden] author-rule guard, basket_detail untouched. Gate 18 passed; node --check clean. tests/test_state_of_themes.py::test_check_validated_claims is RED AT BASE (43 offenders in unrelated templates; zero in T10 files). Ledger outcome recorded review-rejected/accepted_by none."
  - claim: "T02 (shared curation_assertion v1 contract) is integrated after an independent REJECT review whose three blockers are fixed without re-hashing any fixture."
    command: "git cherry-pick -x d559511f2f2b (=7fcbadb7da43); fix commit 2deb758859d7; COLLECT_LANE=nightly pytest over the seven B suites; scripts/check_theme_graph_contracts.py"
    result: "Review blockers: review.review_due_at and source.native_digest were non-nullable (frozen Robotics reference payload carries null for both); encode_assertion refused unstamped payloads instead of minting. Fix: both fields nullable (anyOf null); encode_assertion is the mint path; curation_revision content-validates before hashing via a shared _validated_content (no recursion); decode_assertion(NaN) -> None; authority tests pin the code rule; frozen Robotics payload pinned verbatim as a test; 28-fixture roster pin; T01 identity-leak test admits only https://example.invalid/ URLs. Gate 194 passed, 1 xfailed; contracts script output unchanged; store.py and basket_detail.html.j2 untouched. Independent Opus READ_ONLY re-verification of 2deb758859d7 in flight."
unverified:
  - claim: "T10 part 1 will pass independent review after the bounded fix lane closes the two blockers (bilingual <option> law; limitations/authorized_coverage never rendered) and nits 1/2/4/5/7/8/9."
    what_would_verify: "The T10-FIX executor commit on top of f53c7c3845b3 passing its gate (>=26 tests, node --check) and a second READ_ONLY review returning ACCEPT/ACCEPT_WITH_NITS; then seat cherry-pick of both commits with CI wiring into a node-shipping pack."
  - claim: "GMI has an approved private storage/publication binding for full-fidelity assertions."
    what_would_verify: "T01/T03 evidence from the existing GMI storage and private-publication owners that the incumbent reader/writer can be bound to a non-public runtime root or to the existing private Research Vault store, with current-rights enforcement; no second store."
  - claim: "Earnings owner can enroll TSMC (foreign private issuer, 6-K) and onsemi (8-K) witness sequences with real native objects."
    what_would_verify: "T05 qualification report naming exact owner functions, source documents, event identities and gaps, followed by validated event workspaces fetched through approved accessors."
  - claim: "Either witness is production-proven."
    what_would_verify: "T11/T12 real source -> native owner -> rights/entitlement -> API -> existing page proof, both witnesses, plus negative and non-interference proofs."
unresolved:
  - "SOURCE_COLLISION (lane-local): engine/theme_graph/store.py one-line EVIDENCE_COLUMNS append is frozen pending #7462 source-writer release or terminal state."
  - "SOURCE_COLLISION (lane-local): templates/basket_detail.html.j2 generic research mount + asset includes frozen pending #7669 release or accepted current template identity."
  - "Private binding for live full-fidelity GMI admission is unproven; synthetic contract/composition/test work continues; live admission lane closed."
  - "mastermind-executive MCP connector is unauthenticated in this session; fabric dispatch uses the installed pool/lease-broker CLI (canonical Subagent Fabric surface on this host), not a new queue."
  - "DECISION_REQUEST R4 open on #7780 (issuecomment-5807772681): adopt candidate (ii) — full-fidelity assertion bodies through the existing private Research Vault owner under one registered prefix, reference-only rows in the public parquet — pending Sol/Chairman; live admission (T11) blocked until ruled; preconditions R2_RESEARCH_BUCKET has no public r2.dev domain and PAYWALL_GRACE_SECONDS acceptability unverified."
  - "Fabric incident 2026-09-24: executor lanes running under the Claude Code SDK harness (MiniMax mode) obey the Macro repository ship loop (push, PR, merge-on-green label, gh run watch) despite the lane contract; T01 opened #7874 and armed merge-on-green (disarmed: draft, label removed, custody comment 5807689936, stray watcher killed); T06 pushed claude/semi-b-t06-guidance before its lane was terminated (no PR). Every later packet carries a binding LANE LAW preamble forbidding push/PR/labels/watchers; stray origin branches claude/semi-b-t01-inputs and claude/semi-b-t06-guidance are to be deleted after integration."
  - "Executor return blocks were missing or replaced by ship-loop status for T01 and T03 (stdout 1.5 KB / 2 lines); acceptance therefore rests on the commits, second-environment gates and independent review, not on executor self-report."
  - "Candidate DSC (not yet recorded): GMI evidence parquet is an unregistered artifact on the public raw plane (config/r2_delivery_plane_classification.v1.json:166 DEFAULT_DENY:MACRO_GIT_RAW data/**) while config/theme_sources.yml:34 calls data/theme_graph an internal plane; nothing enforces the internal-plane language."
  - "Candidate DSC (not yet recorded): the Macro executor harness (claude -p under MiniMax/GLM keys) inherits the repository CLAUDE.md ship loop; a lane contract alone does not stop push/PR/merge-on-green."
  - "Dependency PR #7669 is actively executing (latest 2026-09-24T05:09Z 'same-carrier integration executing', head 2c28d950aa94); #7462 unchanged since 03:53Z (head 31706d7322af); custody questions on both unanswered; R4 unruled on #7780 as of the 05:16Z fresh-read."
  - "T05 (operator commission, glm-5.3, mb lane rs_20260924T045106Z_54606) FAILED without a commit: after 39 turns / 552 s every call returned GLM `400 [1301] unsafe or sensitive content` (terminal_reason api_error) — a provider content filter on the TSMC/Taiwan material, not quota or admission. Ledger outcome recorded accepted_by=none, escalated. Re-routed as two MiniMax executor contracts: T05a identity+profiles (issuer_profiles/event_workspace/event_workspace_build + tests/test_semiconductor_earnings_witnesses.py; mb worktree ~/lanes/semi-b-t05-witness-mm) and T05b intake (scripts/refresh_event_workspaces.py DISCOVERY_TICKERS, identity-declared results-6-K discriminator, 52/53-week tolerance + tests/test_semiconductor_earnings_intake.py; m1 worktree ~/lanes/semi-b-t05b-intake). MiniMax may share the same content policy — unverified until a lane returns."
  - "Remote lane capacity: both hosts (m1, mb) sit at the 2-lane ceiling most of the time because other orchestrators' lanes (mo_a3_*, cdv1_*, pu_w3_*) hold slots; wave-2 placement runs through a per-host dispatcher that waits for `pool hosts` ELIGIBLE before calling `pool remote` (no ledger noise, no new queue): mb queue = T07/T08 (glm-5.3 operator) then T05a (MiniMax); m1 queue = T04 (glm-5.3-flash executor), then T05b (MiniMax) once its worktree is minted."
  - "Native `mastermind-opus-auditor` agents stop at a 12-turn cap before producing a verdict on gate-running reviews (two runs lost); independent reviews now run as general-purpose Opus with ROUTE: AUDIT / MODE: READ_ONLY. Candidate feedback record for the fabric owner."
  - "Shared-contract addition: `published_at_grain_mismatch` (grain/date consistency) is enforced beyond the frozen Robotics rule list; documented in contracts/theme_graph/README.md and notified on #7773 (issuecomment-5808287514); the Robotics owner has not acknowledged it — candidate DEC if Robotics objects."
  - "Cross-vertical dependency: the Basic Materials research operation (gmi-basic-materials-research-20260923-sol-001, carrier #7796) posted R10-SHARED-PROFILE-REQUEST-20260924 on #7773 (issuecomment-5808157680) asking the shared owner for the private object class/callable/namespace/generation rule, rights binding, export boundary and dependency carrier. Seat answered with facts only (#7773 issuecomment-5808307684): shared contract = #7870 module/schema; measurement vocabulary is closed and non-negative (no signed/exact-decimal, no materials bases — an amendment request, not a variant); private profile NOT implemented; single next action = the R4 ruling; rights binding = rights.load_registry_snapshot/assert_current_emission_allowed; custody unchanged. R4 addendum posted on #7780 (issuecomment-5808311511): the ruling now gates Semiconductor T11, the Robotics live path and Materials T1/T2. No Materials scope accepted."
  - "T10-FIX executor contract written (scratchpad packets/T10fix_client.txt; owned files site/assets/js/theme-research.js + tests/test_semiconductor_theme_research_ui.py; runs in m1 worktree ~/lanes/semi-b-t10 on top of f53c7c3845b3). Dispatch is held behind T05a/T05b so the mandatory witness path takes the next slots; CI wiring at integration must land in a node-shipping pack (the Theme Tracker pack at legacy-jobs.yml ~14560 has if:false and no setup-node; the publish-r2-client pack ~10188 ships node)."
next_actions:
  - "Dispatch T10-FIX (executor, m1 worktree ~/lanes/semi-b-t10) once T05a and T05b are placed; on its return: gate, second READ_ONLY review, cherry-pick f53c7c3845b3 + the fix commit, wire tests/test_semiconductor_theme_research_ui.py into a node-shipping legacy-jobs pack (+ ci.yml paths), rerun audit_unrun_tests, push; T10 part 2 (basket_detail mount) stays frozen pending #7669."
  - "As wave-2 lanes return (T07/T08, T04, T05a, T05b): disarm check (origin semi-b branches, gh pr list, gh run watch on the host), pull by git bundle, second-environment gate, general-purpose Opus READ_ONLY review, integrate, ledger outcome. If a MiniMax lane also dies on a content filter, decompose further so packets never require reading filing bodies, or escalate the provider question to Sol."
  - "After T07/T08 land: dispatch T09 (API transport; needs fastapi -> mb) with the LANE LAW preamble; after T05a+T05b land: the witness event-workspace mapper work in T08 can bind currency/basis for TSMC (USD guidance vs NT$ actual)."
  - "Fresh-read #7780 for the R4 ruling and #7462/#7669 for custody answers before every substantive write (>=15 min cadence); keep store.py and basket_detail.html.j2 frozen until released; T11 live admission stays blocked until R4 is ruled."
  - "Post the T02/T10 integration checkpoint on #7870 and update this handoff with each integration."
do_not_redo:
  - "Do not repeat the R01-R09 research, A/B/C selection, written design, plan or 48-requirement mapping."
  - "Do not implement on #7780, #7773, #7462 or #7669; do not transplant their hunks."
  - "Do not create a semiconductor-specific graph, evidence/correction ledger, product master, financial/consensus/expectation store, rights registry, queue, scheduler, watcher, auth or publisher."
  - "Do not execute SBD-41..48 / C1."
  - "Do not fork the Robotics-proposed curation_assertion contract into a semiconductor variant; extend the one shared payload (ruling R1)."
danger_areas:
  - "Macro is public: no full-fidelity paid assertion bodies, credentials or private production captures in this carrier."
  - "A synthetic-fixture green is not native admission; an industrial-only pane does not satisfy either witness."
  - "Current issuer identity is not historical lineage; source-only businesses get no fabricated CIK/security/company node."
  - "Fabric executor first-pass acceptance is low (glm-5.3 0.29, MiniMax-M2.7 0.14 over last 20): every child needs an executable deterministic gate and independent review before integration."
prs: [7780, 7870, 7874, 7773, 7462, 7669]
---

# Semiconductor B — implementation operation working checkpoint

OPERATION: `gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001`
PARENT RESEARCH OPERATION: `gmi-semiconductors-research-20260923-sol-001` (carrier #7780, records only)
RECEIVER: Claude Fable 5.1, Claude Desktop Code session `f6dd4b82-d319-4daf-99a4-ef4fe7dfd9ec`, host `Mac-Studio.local`
PROCEDURE PIN: Mastermind `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1 / bootstrap 1
CARRIER BASE: Macro `main` `9438880952d3375b00a042381705c2e6c85305e3`
STATE AT THIS COMMIT: `STARTED` (START issuecomment-5807391383); carrier #7870 holds wave 1 (T01/T03/T06) and T02 with review fixes (head 2deb758859d7 before this commit); T10 under independent review; wave 2 (T04, T07/T08, T05a, T05b) queued on the fabric; `SEMICONDUCTOR_B: NOT_BUILT` (contract/fixture/rights/guidance layers only — no composition, no transport, no live admission, no witness proof); `C1: DEFERRED`; `MISSION_COMPLETE: false`; `EFFECT_UNKNOWN: none`.

## Fable custody rulings inside the accepted B architecture

- **R1 — one shared assertion contract, authored here first.** No Robotics implementation carrier exists and no STARTed operation owns `contracts/theme_graph/curation_assertion.v1.schema.json` or `engine/theme_graph/curation_assertion.py`. B authors the shared `theme_graph.curation_assertion.v1` contract exactly as proposed by the Robotics plan (#7773 Task 1: field groups, closed predicate/statement-mode vocabularies, `gmirca_[0-9a-f]{32}` revision, canonical-JSON codec, `validate_assertion`/`curation_revision`/`encode_assertion`/`decode_assertion`/`source_ref_for`) plus the semiconductor plan's closed optional `industrial_context` object. Two shared generalizations are recorded for the Robotics receiver: `source_ref_for` derives its theme segment from `scope.canonical_theme_id` instead of the literal `robotics`, and `subject.company_node_id` is nullable for source-only businesses. The Robotics receiver consumes the accepted revision; it does not re-author the contract.
- **R2 — store.py column is a frozen lane, not a blocker for B.** The one-line `EVIDENCE_COLUMNS` append waits on #7462 (custody question posted). All other T02 work (schema field, module, guard decoding, tests) proceeds; the round-trip test that needs the column is written RED and lands with the column.
- **R3 — template hunk is a frozen lane.** `templates/basket_detail.html.j2` waits on #7669 (custody question posted). The shared client JS/CSS and the `templates/state_of_themes.html.j2` mount (touched by no open PR) proceed.
- **R4 — private binding question is qualified, not improvised.** The existing private publication owner pattern is `engine/earnings_narrative/private_publication.py` over `engine/research_vault/r2_store` (private bucket, LocalStore for tests) read by `app/earnings.py` after `require_user` + `enforce_site_full(always=True)`. T01/T03 qualify whether the incumbent GMI evidence reader/writer can be bound to a non-public runtime root or published through that existing private store owner under current rights. No new store, bucket, env override or public fallback. If neither existing owner path can be proven, the live-admission lane returns to Sol/Chairman as a DECISION_REQUEST while synthetic work continues.

## Custody map (carrier base)

| Path | Status | Owner / gate |
|---|---|---|
| `contracts/theme_graph/curation_assertion.v1.schema.json`, `engine/theme_graph/curation_assertion.py` | new, free | B authors (R1) |
| `contracts/theme_graph/evidence.v1.schema.json` (optional nullable `curation_assertion`) | free | additive; guard tests |
| `engine/theme_graph/store.py` (`EVIDENCE_COLUMNS` append) | **FROZEN** | #7462 |
| `engine/theme_graph/rights.py` (snapshot API) | free (not in #7462 file set) | T03 |
| `scripts/check_theme_graph_contracts.py`, `tests/test_theme_graph_contracts.py` | free (not in #7462 file set) | T02 |
| `contracts/evidence_foundation/vocabulary.v1.json`, `tests/test_evidence_foundation_contract.py` | free | T04 |
| `engine/company_intelligence/*` witness enrollment | free | T05/T06 |
| `engine/market_ontology/semiconductor_theme_research.py`, `contracts/market_ontology/*.schema.json` | new, free | T07/T08 |
| `app/theme_research.py`, `app/main.py` router include | free | T09 |
| `site/assets/js/theme-research.js`, `site/assets/css/theme-research.css`, `templates/state_of_themes.html.j2` | free | T10 |
| `templates/basket_detail.html.j2` | **FROZEN** | #7669 |
| `scripts/build_state_of_themes.py` | not touched by plan | #7664 lane avoided |
| `data/theme_graph/evidence.parquet` (public Git) | no full-fidelity payload ever | R4 |

## Fabric surface and routing

Canonical Subagent Fabric on this host is the installed `pool` CLI (lease broker + `sub.sh`/`remote_sub.sh`, hosts m1/mb remote lanes, Studio seat local only for grok/ocfree). Routing law R23: seat (this Fable) decomposes/adjudicates; operators (glm-5.3, grok-4.6, cursor) own bounded commissions; executors (MiniMax, qwen, glm-flash) implement; independent review by qwen3.8-max/grok/Opus READ_ONLY audit. Every child packet carries mission, exact source refs, owned files, non-goals, deterministic acceptance gate, stop condition and a fixed return format. `WHY NOT FABLE` for every child: bounded, specified by the accepted plan, deterministic pytest gate available. Native Opus children only for READ_ONLY audit or bounded orchestration under the global routing guard.

## Exact next action

Consume the two in-flight READ_ONLY reviews (T02 re-verification of 2deb758859d7; T10 client f53c7c3845b3), integrate what is accepted with CI wiring, keep the per-host dispatchers placing T07/T08, T04, T05a, T05b as slots open, and hold store.py / basket_detail.html.j2 / live admission frozen until #7462, #7669 and the R4 ruling release them.
