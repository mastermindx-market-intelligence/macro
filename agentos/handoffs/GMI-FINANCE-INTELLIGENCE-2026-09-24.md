---
workstream: "WS:GMI-FINANCE-INTELLIGENCE"
session: claude/finance-intelligence-implementation-20260924
model: fable
ended_because: ci_handoff
mission: >
  Implementation carrier and cumulative working checkpoint for
  gmi-finance-fable-ceo-e2e-20260924-chairman-001: ship the Finance Intelligence
  first vertical (Financial Rails & Market Infrastructure — Money Movement + Securities
  Infrastructure) as one read-only, owner-preserving projection with an authenticated
  private API, a dossier UI, Theme Tracker / Financials entries, exact missing/conflict
  states and real-path browser proof; then expand breadth. Fable seat orchestrates;
  fabric lanes build.
state_before: >
  Research/plan/handoff truth existed only on draft/HOLD PR #7786 at
  615f1050e2f7e060d54a3ddfffa80a7127b38d47 (26k files behind main). No implementation
  carrier, no PICKUP_ACK, no START, no Finance product code. Macro main at pickup was
  2400ba0439ea (R12 had observed 9573cd4d). Protected Mastermind master was
  e03eacbf98655d6a560f16784b8b62d531d8076f (Skillpack 1.0.1 / bootstrap 1).
changed:
  - path: agentos/workstreams/WS-GMI-FINANCE-INTELLIGENCE.md
    what: "Minted the Finance Intelligence workstream (owned paths, waves W0–W7, landmines, do_not_redo)."
  - path: agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md
    what: "Created the implementation-operation working checkpoint: pickup receipt, procedure pin, current-main/custody matrix, seat rulings, wave plan, exact next action."
  - path: agentos/decisions/DEC-FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN.md
    what: "Ruled the carrier topology: one seat DRAFT PR is the operation carrier; task work ships as fabric-built PRs off fresh main in dependency order."
  - path: agentos/decisions/DEC-FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS.md
    what: "Ruled the evidence grammar: the read model's source_records mirror the shared curation assertion field names as display-tier projections; canonical evidence stays with the shared assertion + private Research Vault; no Finance ledger."
verified:
  - claim: "Current protected procedure is compatible and loaded from one pin."
    command: "git -C Mastermind fetch origin master; git rev-parse origin/master; git show origin/master:docs/sol_skills/{INDEX,ACTIVE_EXECUTION,WEB_CEO_DELEGATION,COMMISSION_WAVE,WORKER_AVENUE_ROUTING}.md; git log a7d2b304..origin/master --oneline"
    result: "e03eacbf98655d6a560f16784b8b62d531d8076f; skillpack_version 1.0.1, minimum_bootstrap_major 1; the single commit past the packet pin touches control_plane/executive_placement_preference.py only."
  - claim: "PICKUP_ACK for the operation is durably recorded on the research carrier."
    command: "gh pr comment 7786 --body-file pickup_ack_7786.md"
    result: "https://github.com/mastermindx-market-intelligence/macro/pull/7786#issuecomment-5808334105"
  - claim: "The implementation branch descends from then-current main and not from #7786."
    command: "git checkout -b claude/finance-intelligence-implementation-20260924 origin/main; git merge-base --is-ancestor e54e33d8 HEAD; git log --oneline e54e33d8..HEAD"
    result: "HEAD 2400ba0439ea; e54e33d8 (fetched main at pickup) is an ancestor; the two newer commits are [skip ci] bot commits (earnings-wire publish, immune journals)."
  - claim: "All seven R12 dependency PRs are still OPEN and unmerged; heads recorded."
    command: "gh api graphql (one query, seven pullRequest aliases: number,state,isDraft,headRefOid,mergedAt,files)"
    result: "#7870 2deb7588 DRAFT; #7777 4122e3b7 OPEN; #7462 31706d73 DRAFT; #7664 e43c7693 OPEN; #7849 8edbb0b9 OPEN merge-on-green+merge-blocked; #7797 ac2701b6 OPEN hold-for-sol; #7669 2c28d950 DRAFT (358 files)."
  - claim: "D1 (basket_detail custody) is resolved: #7669 DOES own templates/basket_detail.html.j2."
    command: "gh api graphql pullRequest(7669).files(first:100, after:<cursor>) paged four times, filtering paths"
    result: "Page 4 lists templates/basket_detail.html.j2 and templates/baskets_desk.js; R12's fresh read was truncated at the first 100 files."
  - claim: "The Sector Intelligence contract registry auto-discovers new schemas; no contracts.py edit is required for finance_intelligence_read_model.v1."
    command: "git show origin/main:engine/sector_intelligence/contracts.py | sed -n '381,410p'"
    result: "_discover_records rglobs *.schema.json under contracts/sector_intelligence and contracts/biocatalyst; #7777 edits contracts.py only to add a semantic issue function for its own contract."
  - claim: "Neither the shared curation assertion nor the sector dossier contract is on current main."
    command: "git cat-file -e origin/main:contracts/theme_graph/curation_assertion.v1.schema.json; git ls-tree origin/main contracts/sector_intelligence"
    result: "curation_assertion ABSENT; sector_dossier_read_model ABSENT; ten sector-intelligence contracts present."
  - claim: "The accepted private publication owner and its host binding are known."
    command: "git show origin/main:engine/research_vault/r2_store.py | sed -n '1060,1092p'; git show origin/main:.github/workflows/deploy-api-secrets.yml | grep R2_RESEARCH; git show origin/main:.github/workflows/earnings-public-wire.yml | grep -n publish_earnings_private_store"
    result: "build_store precedence local_dir → RESEARCH_LOCAL_STORE → R2_RESEARCH_BUCKET; the four R2_RESEARCH_* secrets are delivered to macro-api only; earnings-public-wire.yml publishes with those secrets on workflow_dispatch/workflow_run."
  - claim: "Fabric lane capacity exists for Wave 1."
    command: "ssh m1/mb/mini2 'ls ~/lanes/ext/active'; ssh mini2 'ls ~/lanes/repos; git -C ~/lanes/repos/macro rev-parse --short HEAD; ls ~/lanes/venv/bin/pytest; which gh codex claude'"
    result: "m1 2/2 (cdv1_t1_pg_facts, mo_a3_mor2_census), mb 1/2 (mo_a3_ric_f3_w1) with a waiting ene dispatcher, mini2 0/2 with macro mirror at 33c73dd9, pytest venv, gh/codex/claude, 148 GB free, load 1.3."
  - claim: "START is durably recorded and Wave 1 lanes are dispatched on the fabric."
    command: "gh pr comment 7786 (START); nohup admission_wait_dispatch.sh mini2 fin_t1_contract 2 36; nohup admission_wait_dispatch.sh mini2 fin_t3_overlap 2 36; grep LANE_LEASE remote_lane_v8_mini2_fin_t1_contract.log"
    result: "START = #7786 comment 5808406935; carrier PR #7887 (DRAFT) head 9f7ec63e; fin_t1_contract ADMITTED on mini2 05:43Z (GLM lease 2a2b25eafc07, remote pid 32877, branch claude/finance-t1-read-model-contract, new-packet mode); fin_t3_overlap queued behind the Energy seat's ene_w1_t3_adapter marker (dispatcher ticking every 300 s)."
  - claim: "Coordination notes are posted on the two shared-custody carriers before any Wave 3 write."
    command: "gh pr comment 7870; gh pr comment 7669"
    result: "#7870 comment 5808435472 (state_of_themes include, app/main include, R11 §14.1 extension request, private prefix); #7669 comment 5808435736 (basket_detail launch include seam)."
  - claim: "No SSH route from the seat to the API host exists; private publication must be a secrets-bearing workflow."
    command: "ssh -o BatchMode=yes root@146.190.142.17; gh api repos/mastermindx-market-intelligence/Mastermind --jq .private"
    result: "Permission denied (publickey); both macro and Mastermind are PUBLIC repos — staging can never be committed; the Finance publish lane rebuilds staging deterministically from the pinned research sha inside a workflow_dispatch run with the R2_RESEARCH_* secrets (packet fin_t6_publish_workflow)."
unverified:
  - claim: "The R4 private-binding ruling on #7780 (candidate ii — Research Vault under one registered prefix) will be accepted for GMI theme research."
    what_would_verify: "A Sol/Chairman reply on #7780 after comment 5807772681; Finance's private path uses the same store/prefix idiom either way."
  - claim: "The Finance extension sections (finance_scope / finance_measurement / finance_rerating_context, R11 §14.1) can be added to the shared curation assertion without breaking #7870's semiconductor fixtures."
    what_would_verify: "A coordination reply from the #7870 seat and a green tests/test_theme_graph_curation_assertion.py with the extension present."
unresolved:
  - "Rights registry (config/theme_sources.yml) carries no SEC filing family; #7870's assert_current_emission_allowed fails closed on unknown families. Until the registry owner admits a family, first-vertical source records display rights_state=SOURCE_RIGHTS_HELD for emission purposes."
  - "Financials launch module seam on basket/us_sector_financials.html is inside templates/basket_detail.html.j2 (held by #7669)."
next_actions:
  - "Consume the fin_t1_contract return (PR by the lane runtime): seat review of the schema against the frozen field list, arm merge-on-green, merge on concluded green; then dispatch fin_t2_projection + fin_t4_private (args pre-staged in $K/ext)."
  - "Consume fin_t3_overlap; wire tests/test_finance_overlap.py into the finance-intelligence job (paths + run) in the T2 or a seat commit."
  - "Wave 2 packets are frozen and pre-staged: fin_t5_staging (deterministic staging builder from research sha + locator receipts), fin_t6_publish_workflow (workflow_dispatch publish lane with R2 secrets), fin_t7_api (authenticated route) — dispatch order T5 ∥ T4 → T7 → T6; the seat dispatches the publish workflow (dry-run first)."
  - "Post coordination notes on #7870 (state_of_themes mount + app/main.py include + R11 §14.1 extension sections) and on #7669 (basket_detail launch include) before any Wave 3 write."
  - "Wave 2: transcribe the eleven first-vertical witness records (V, MA, FI, FIS, CME, ICE, NDAQ, BK, STT, SPGI, MCO) from research/finance/FINANCE_FIRST_VERTICAL_ASSERTION_PACKET_V0_1_2026-09-23.json @615f1050 into the frozen read model through the private owner; ship app/finance_intelligence.py."
do_not_redo:
  - "R1–R12 Finance research and every artifact under research/finance/ at #7786 @615f1050 (read by exact path/SHA)."
  - "Dependency custody census recorded in this file (seven PRs, heads, dispositions) — re-read only the heads before an overlapping write."
  - "Registry auto-discovery, private-store precedence, API-host secret delivery and lane-host capacity checks recorded above."
danger_areas:
  - "Never rebase, cherry-pick or merge #7786; never branch from it."
  - "Never edit engine/theme_graph/store.py, config/theme_crosswalk.yml, data/baskets/membership.json, site/theme.css or templates/theme.css from this programme."
  - "Never put full-fidelity assertion bodies, the research narrative or private API payloads under site/**, templates/**, tests/fixtures/** or browser storage; fixtures are SYNTHETIC."
  - "Lane hosts are sparse clones: new fixtures under data/ need `git add --sparse`; an existing data/ or site/ write truncates the committed artifact."
  - "A new test file wired into a legacy-jobs run: line without a paths: entry reds contract-delta on every PR — add both."
prs: [7786]
decisions:
  - DEC:FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN
  - DEC:FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS
---

# GMI Finance Intelligence — implementation working checkpoint (2026-09-24)

Operation: `gmi-finance-fable-ceo-e2e-20260924-chairman-001` (parent
`gmi-finance-sector-research-20260923-sol-001`). Receiver: Fable 5.1 seat, session
`938d17d6-a768-4217-a28a-321c0cb62da0` (claude8). PICKUP_ACK: #7786 comment 5808334105.

## Source frontier (read by exact path/SHA — DO NOT REDO)

Research carrier PR #7786, `sol/finance-sector-research-20260923`, head
`615f1050e2f7e060d54a3ddfffa80a7127b38d47`:
`agentos/handoffs/GMI-FINANCE-MASTER-FABLE-CEO-HANDOFF-2026-09-24.md`,
`docs/superpowers/plans/2026-09-24-finance-sector-intelligence-implementation.md`,
`research/finance/FINANCE_R11_PRODUCT_AND_VISUALIZATION_ARCHITECTURE_FREEZE_2026-09-23.md`,
`research/finance/FINANCE_R12_CURRENT_MAIN_ARCHITECTURE_COLLISION_AND_CUSTODY_REVIEW_2026-09-24.md`,
`research/finance/FINANCE_RESEARCH_CHECKPOINT_R9_R10_2026-09-23.md`,
`research/finance/FINANCE_PRODUCT_EXPERIENCE_AND_OWNER_PRESERVING_DATA_CONTRACT_2026-09-23.md`,
`research/finance/FINANCE_FIRST_VERTICAL_ASSERTION_PACKET_V0_1_2026-09-23.json` (11 witness
records, 28 source-native assertions, identity RESEARCH_HINT_UNVALIDATED),
`research/finance/FINANCE_R11_SUBTHEME_ATLAS_V0_1_2026-09-23.json` (52 slices, 7 domains).

## Custody matrix at pickup (main 2400ba0439ea, 2026-09-24 05:2xZ)

| Interface | Observed | Finance disposition |
|---|---|---|
| #7870 shared `theme_graph.curation_assertion.v1` (2deb7588, DRAFT/HOLD, STARTed 04:03Z) | not on main; schema requires `scope.canonical_theme_id` + `subject.company_node_id`; R4 private binding open on #7780 | CONSUME_WHEN_ACCEPTED + COORDINATE the R11 §14.1 Finance sections; never fork |
| #7777 `sector_dossier_read_model.v1` (4122e3b7, OPEN) | not on main; registry auto-discovers schemas | FREE for `finance_intelligence_read_model.v1`; CONSUME_WHEN_ACCEPTED for the outer sector object |
| #7462 `engine/theme_graph/store.py` (31706d73, DRAFT) | frozen column proposal | NO EDIT |
| #7664 `scripts/build_state_of_themes.py` (e43c7693, OPEN) | Lane E/C realignment | NO EDIT — Theme Tracker card is a static partial include |
| #7849 `templates/theme.css` + `site/theme.css` (8edbb0b9, armed, merge-blocked) | DS-PR-0a primitives | NO global-token edit; scoped `finance_intelligence.css` |
| #7797 regional shared body (ac2701b6, hold-for-sol) | | REFERENCE ONLY |
| #7669 `templates/basket_detail.html.j2` (2c28d950, DRAFT) | **D1 resolved: owned by #7669** | WAIT_FOR_OWNER for the Financials launch module; Wave 3 alternative = one guarded `{% include %}` after coordination |
| `templates/state_of_themes.html.j2` | last main touch 2026-09-12; #7870 T10 mount not yet in its file list | COORDINATE_SHARED_EDIT (one additive include after the research-priority section) |
| `app/main.py` | #7870 T09 plans `app/theme_research.py` include | COORDINATE_SHARED_EDIT (one additive `include_router`) |
| `scripts/build_site.py`, `.github/workflows/render.yml` | many owners | additive hook + path entry in Wave 3 |
| `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py::CURATED_EXCLUSIVE` | shared | one exclusive gate:code job `finance-intelligence` |
| private publication | earnings idiom over Research Vault; API host has `R2_RESEARCH_*` | same store, ONE registered prefix `finance_intelligence_private/v1`; no new bucket/db/env |
| rights | `config/theme_sources.yml` has no SEC family | display `SOURCE_RIGHTS_HELD` until the registry owner admits a family |

## Seat rulings

- **R-FIN-1 carrier topology** — `DEC:FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN` (records merge at wave boundaries; #7887 = Wave 0; later checkpoints ride fresh records PRs citing the operation key).
- **R-FIN-2 evidence grammar** — `DEC:FINANCE-EVIDENCE-GRAMMAR-MIRRORS-SHARED-ASSERTION-NEVER-FORKS`.
- **R-FIN-3 Theme Tracker card is static** — a template partial with no builder context, so
  `scripts/build_state_of_themes.py` (#7664) is never touched; the card links only.
- **R-FIN-4 route** — `GET /api/sector-intelligence/financials/finance/v1` in a new
  `app/finance_intelligence.py` (no Sector Intelligence router exists on main), using
  `require_user` → `enforce_site_full(always=True)` and the biocatalyst private-header idiom
  (`Cache-Control: private, no-store`, `Vary: Authorization`, `X-Content-Type-Options: nosniff`,
  `X-Robots-Tag: noindex, noarchive`) on every success and error path.
- **R-FIN-5 page** — `templates/finance_intelligence.html.j2` rendered by
  `scripts/build_finance_intelligence_page.py` (capital_structure pattern: `render(root)`,
  `write_page`, additive `build_site.py` hook), paired `templates/finance_intelligence.{js,css}`
  ↔ `site/finance_intelligence.{js,css}`; the shell is public and data-free, browser reads stay
  inside the authenticated API, nothing private persists in localStorage/IndexedDB.

## Wave plan

W1 (now): `fin_t1_contract` + `fin_t3_overlap` on mini2 in parallel; `fin_t2_projection` +
`fin_t4_private` after the schema merges. W2: witness transcription + private publisher + API.
W3: shell/UI + entries (after coordination notes). W4–W6: breadth. W7: qualification, review,
browser proof, production acceptance.

## Exact next action

Open the DRAFT carrier PR, emit START on #7786, dispatch `fin_t1_contract` and
`fin_t3_overlap` to mini2 through `admission_wait_dispatch.sh`.

## Wave 1 addendum (seat 938d17d6, 2026-09-24 06:43Z) — to land on a FRESH records branch after #7887 merges

### changed
- T1 read-model contract: PR #7896 (head 4fddbd33970e) armed merge-on-green. Delivered by fabric lane fin_t1_contract (glm-codex/glm-5.3); the builder exhausted its auto-continue budget after writing complete files; the seat verified on mini2 with `~/lanes/venv/bin/python` (15 passed; `run_ci_pack.py --validate-only` rc 0; `test_ci_pack.py -k "exclusive or curated"` 7 passed), added the 25 import-closure paths (`engine/sector_intelligence/__init__.py` → `launch_slo_verifier` → earnings_narrative → biocatalyst) the exclusive job needed, committed, fetched the commit over SSH and pushed from the seat worktree.
- Lane engine switch: glm-codex/glm-5.3 produced word salad with AUTO_CONTINUE_EXHAUSTED on 3/3 Finance lanes (T1 end-of-run, D1, T3 first turn). All remaining Finance lane args now run `fix_engine: minimax` / `MiniMax-M3`, `review_engine: seat`, rounds 1. D1 and T3 re-dispatched (mb 06:28Z, mini2 06:33Z).
- T2 packet addendum: SHAPE AUTHORITY clause naming the required field families the frozen text did not spell out (snapshot_identity, coverage counts, conflicts left/right, slices indicators/falsifiers/retained_risk/valuation_anchor, macro_matrix item, outer_dossier_ref nulls).
- Packets staged for Wave 3: fin_t8_ui_shell (dossier page shell + hydration from the D1 spec; biocatalyst shell/fetch idiom; no payload in static HTML or browser storage; two art directions; evidence receipt), fin_t9_entries (Theme Tracker sector-deep-dive card outside canonical lanes; Financials launch module gated on #7669 merge), fin_d1_audit_prompt (Opus read-only AUDIT of the D1 spec before T8).

### verified
- `scripts/merge_on_green.py` treats `ci-authority/codex/merge-queue-pilot` as non-binding (`CI_AUTHORITY_INACTIVE_CONTEXT`, `is_non_binding_check`) — the pilot red on #7887 does not block the sweeper. Command: `git show origin/main:scripts/merge_on_green.py | sed -n '650,690p;926,940p'`.
- mini2 `python3` is 3.14 without pytest/jsonschema; the lane venv is `~/lanes/venv/bin/python` (3.14.7 + pytest 9.1.1). Command: `ssh mini2 '~/lanes/venv/bin/python -c "import pytest,jsonschema"'`.

### unverified / open
- #7887 Stop-guard block `ci_failed_unmerged: semantic evidence base_sha mismatch` (main moved while packs ran; classified by the guard as an external WAIT). Whether the sweeper merges on concluded green or marks `merge-blocked` is pending the watcher.
- mini2 HTTPS push hang (osxkeychain, headless) — reproduced once for ~7 min, then a later push authenticated normally; root cause not pinned; the SSH-fetch route is the reliable path.

### do_not_redo (additions)
- Do not re-run fin_t1_contract; the T1 files are on #7896.
- Do not edit mini2's shared git credential config on the dry-run evidence (public repo — ref advertisement needs no auth).

### danger_areas (additions)
- A lane log `r1_fix: … rc=0 out=NNNNNB` is not success; read `~/lanes/ext/lanes/<label>/r1_fix.out.md` and the fix worktree before consuming.
- `git add` in a lane/sparse clone needs `--sparse` for new files under data/, site/, mockups/.

### verified (06:44Z additions)
- #7780 comment 5807772681 (R4 DECISION_REQUEST, Semiconductor seat, 04:36Z): recommends candidate (ii) = canonical bodies through the existing private Research Vault owner (`engine.research_vault.r2_store.build_store`, private `R2_RESEARCH_BUCKET`) under one registered prefix; public `evidence.v1` rows carry bodies only for `direct_display_ok` families. Finance's frozen T4/T5/T6/T7 path is the same owner + its own prefix `finance_intelligence_private/v1` → consumer of the one owner, not a duplicate. Command: `gh api repos/mastermindx-market-intelligence/macro/issues/comments/5807772681 --jq .body`.
- #7870 head moved to `d5b0c00d772e`; ships `contracts/theme_graph/evidence.v1.schema.json` (required: evidence_id, kind[filing|xbrl|8k_counterparty|scrape_receipt|scrape|news_item|operator_curation|comovement_stat|external_classification], published_at, source_ref, licensing_internal_ok/display_ok/redistribution_ok, computed_at). Finance `source_records[].evidence_ref` binds to `evidence_id`; licensing booleans ↔ `rights_state`. No fork needed. Command: `git fetch origin refs/pull/7870/head && git show FETCH_HEAD:contracts/theme_graph/evidence.v1.schema.json`.
- R2 research secrets are usable: `earnings-public-wire.yml` workflow_run completed success 2026-09-24T05:00:55Z (`gh run list --workflow earnings-public-wire.yml -L 2`). The repo-level secrets listing returned nothing (token scope), so existence is proven by use, not by listing.
- Chairman direction (relayed by Industrials/Consumer/Mining notes on #7870, 06:34–06:42Z): every sector consumes the Semiconductor-led shared GMI foundation. Finance alignment note + `sec_edgar` family request posted on #7870 (06:44Z).

### new gate before Wave 2's first REAL publish
- R4 preconditions (a) research bucket has no public r2.dev domain and is not the shared `mastermindx` bucket; (b) `build_store()` refuses a shared bucket; (c) dry-run receipt for the same research_sha. Added to the fin_t6 packet as PRIVACY PRECONDITION; the seat performs the gate, never a lane.

### Sol R4 ruling consumed (06:49Z) — SOL-R4-PRIVATE-BINDING-20260924-HEALTHCARE-R11 (#7780 comment 5808854275, 06:20Z)
- §1 one native owner via `engine.research_vault.r2_store` + registered prefix → Finance prefix `finance_intelligence_private/v1` (T4) registers in the same place as the earnings private prefix. §2 no public-body shortcut → Finance serves bodies only behind the authenticated API; R-FIN-6's `sec_edgar` request concerns display INSIDE the product, not public bodies. §3 immutable write→verify→advertise, identical no-op, conflict refuse, predecessor fencing → added to fin_t4 packet (SOL R4 QUALIFICATIONS). §4 concrete nonce-object privacy proof → fin_t6 gains `mode: nonce_probe` + seat-run public negative reads; the store-fallback landmine (draft DSC) is why the per-run privacy gate stays too. §5 entitlement grace ≤ 86,400 s lives in the shared paywall module Finance reuses. §6 source rights are an independent veto → rights_state derived at read time (already frozen). §7 shared route family `/api/themes/v1/research/{query,evidence}` continues for assertion bodies.
- **Seat ruling R-FIN-7 (records with the next DEC):** the Finance dossier read model keeps its own read route `/api/sector-intelligence/financials/finance/v1` (T7) because it serves a composed sector read model, not assertion bodies; it reuses the identical fences (`require_user` → `enforce_site_full(always=True)`, private headers) and, once #7870 lands, resolves `evidence_ref` through the shared evidence route rather than re-serving bodies. Alternative (serve the dossier through the shared query family) requires the shared owner to extend that route and is recorded as the revisit condition, not adopted unilaterally.
- Posted on #7780 (06:49Z): the r2_store fallback fact (build_store never refuses a shared bucket).

### T3 delivered (06:52Z)
- PR #7900 `feat(sector-intelligence): expose finance overlap context (Finance T3)`, head b1929dbb3cab, built by fabric lane fin_t3_overlap on mb (minimax / MiniMax-M3, 442 s, review deferred to the seat). Seat review: `python3 -m pytest tests/test_finance_overlap.py -q` → 53 passed (files overlaid temporarily in the seat worktree, then removed); public surface == frozen packet; `basket_state_context` never returns ADMITTED (docstring line ~591); no filesystem reads of basket data. Armed merge-on-green. CI wiring deferred to T2 (T3 WIRING addendum).

### Chairman directive consumed (07:46Z) — integrate, never rebuild the base
- Relayed from Astra CEO via the Chairman: the Semiconductor session builds the shared foundation; Finance integrates later. T4 (private evidence path), T5 (private staging), T6 (publish workflow), T7 (serving route) HELD; the T4 lane that had started on m1 was killed at 07:47Z before any commit; their args are quarantined (`*.HELD-foundation-integration-20260924`). Ruling R-FIN-8 supersedes R-FIN-7 (no Finance route; `FI_READ_URL` bound at integration). Continuing: T3 merge, T2, D1a/D1b, T8, T9. Integration items listed in DEC:FINANCE-INTEGRATES-INTO-SHARED-FOUNDATION-NEVER-REBUILDS-BASE.

### Wave 1 closed (08:29Z) — merges, audit, lanes
- T3 #7900 MERGED 08:12:42Z (3ca9c303) after the seat wired `finance_overlap.py` + suite into the `finance-intelligence` job (0fc4be532d13). Wave 1 records #7902 MERGED 08:29:11Z (b558ba6bc17d) by seat squash on concluded green (`mergeStateStatus: UNSTABLE` is the non-binding pilot context; the sweeper leaves such PRs — merge by hand).
- D1a spec #7903 (469e932e) FAILED the read-only Opus audit (comment 5810133462): private payload in static Jinja, invented contract fields, hex light palette, raw missing-state tokens, wrong macro/conflict shapes, ARIA gaps. The seven-step stepper was the SEAT's D1 packet error → `DEC:FINANCE-RERATING-STEPPER-BINDS-FOUR-CONTRACT-PLANES` (R-FIN-9). D1b mockup withdrawn before admission. Repair lane `fin_d1a_repair` (MiniMax, mb, admitted 08:19Z) applies rulings R-A..R-K + 14 greppable self-checks; a SECOND audit gates the mockup (`DSC:DESIGN-SPEC-LANES-BIND-INVENTED-FIELDS-AUDIT-AGAINST-THE-LIVE-SCHEMA-FIRST`).
- T2 lane `fin_t2_projection` admitted on m1 08:16Z (new PR `claude/finance-t2-owner-projection`).
- R11 freeze docs live on the research pin 615f1050 under `research/finance/FINANCE_R11_*` (not on main); read them with `git show <pin>:<path>`.
- verified: `git ls-tree origin/main engine/sector_intelligence/finance_overlap.py tests/test_finance_overlap.py`; `gh pr view 7902 --json state,mergedAt,mergeCommit`.
- do_not_redo: never re-dispatch the D1b mockup or T8 before the second audit PASSes; never bind stepper nodes beyond the four contract planes.

### T2 merged (11:54Z) — composer live; lane PRs open DRAFT
- #7920 `feat(sector-intelligence): compose finance owner reads (Finance T2)` MERGED 11:53:52Z (e4ac37302968) by seat squash at head 588965de (26 checks concluded; only the non-binding merge-queue pilot red). Seat review had ACCEPTED 040060a6 at 09:30Z; the head was refreshed onto main with `gh pr update-branch 7920` after the A seat reverted the unreviewed AM-edition push (d41c5cce → #7927) that had turned `ci-pack-10` red on every open head.
- The PR had stayed **DRAFT since the lane opened it**, so `merge-on-green` could never act on it. Lane-runtime PRs open draft; the seat must `gh pr ready <n>` at review ACCEPTED. The pre-merge gate is now: `gh pr view <n> --json isDraft,headRefOid,mergeStateStatus,reviewDecision,body,comments` + hold grep (`HOLD-FOR-SOL|do not merge`) → ready → `gh pr merge <n> --squash --match-head-commit <head>`.
- Live on origin/main: `engine/sector_intelligence/finance_projection.py` (blob 0f6b2d15) and its suite; the `finance-intelligence` CI job runs contract + overlap + projection suites.
- verified: `git ls-tree origin/main engine/sector_intelligence/finance_projection.py tests/test_finance_intelligence_projection.py`; `python3 -m pytest tests/test_finance_intelligence_projection.py tests/test_finance_overlap.py -q -p no:cacheprovider` → 74 passed at e4ac3730; `git log origin/main --author="Claude Code" --since=2026-09-24T11:00:00Z` → empty (no direct lane pushes).
- D1a status: audits 2–4 FAILED on #7903 heads aef82d77 / 7a23b05c (comments 5810923955, 5812280671, 5812943971) with seat rulings R1–R4 (surface tiers, state-scoped freshness, answer > support, L1 tables ≤8) and D1–D3 (exposure composition, real dark pip, no stance verb). Round 4 is surgical (D1–D3 + B2–B13, "touching any other file fails the lane"); the fifth audit decides the freeze. Round 1 had appended to THIS handoff outside its owned files — reverted at fdc84cb8 by merging main and `git checkout origin/main -- agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md`.
- do_not_redo: never merge a lane PR without reading `isDraft`; never re-dispatch D1b or T8 before audit 5 concludes; T4–T7 stay HELD until #7870 is on main.

### D1 closed (spec FROZEN 2e5c3df6 + mockup ce7fc986) — audits 2–5, seat freeze repair, browser acceptance
- #7903 `design(finance): frozen Finance Intelligence dossier design spec + static mockup (Finance D1)` MERGED 2026-09-24T14:58:16Z (0293b9cfd76f). Head chain: 469e932e (audit 1 FAIL) → 867fd6e9 (round 1; over-edited the handoff, reverted at fdc84cb8) → aef82d77 (round 2, audits 2/3 FAIL) → 7a23b05c (round 3, audit 4 FAIL) → 7ec8fa6a (SURGICAL round 4; audit 5 = FAIL-BUILD-CLASS-ONLY, comment 5814661750) → 2e5c3df6 (seat freeze repair: F1 spine regression, F2 `.fi-disc` CSS + disclosures, F4 light ring, F5 pip float + empty-attribute guard, F6/F7/F8/F9) → c86a469a (D1b mockup, lane fin_d1b_mockup on m1, 715 s) → 1266e2c5 (seat: theme.css link, degraded gallery outside `<main>`, ZH date twins) → ce7fc986 (lane fin_d1b_repair on m1: 8+8 phone cards, 3 hidden disclosures, svg viewBox, select wrap).
- Rulings recorded: DEC:FINANCE-DOSSIER-SPEC-SURFACE-TIERS-STATE-SCOPED-FRESHNESS-AND-ANSWER-FIRST-COMPOSITION (R-C..R-K, R1–R4, D1–D3). Discovery: DSC:EXTERNAL-REPAIR-LANES-OVER-EDIT-LONG-SPECS-EVEN-WHEN-SURGICAL-CAP-THE-AUDITS-AND-LET-THE-SEAT-CLOSE.
- Browser acceptance of the mockup (review copy served over http with theme.css beside it; file:// tabs are static snapshots): 1440 dark/light/EN/ZH + drawer (focus to close, `<main inert>`, Escape restores focus) + tablist (roving tabindex, ArrowRight) PASS; 390 dark/light/EN/ZH PASS after the repair (scrollWidth 390, 8+8 cards, no overflowers). Metrics on #7903 comments (seat review + acceptance).
- The seven L1 sections in frozen §B.0 order: what-changed, rerating-map, system-map, subtheme-atlas, company-exposure, macro-matrix, constraint-map; evidence drawer is an `<aside>`; exactly four hydrated stepper nodes.
- Residuals for T8 (scratchpad packet fin_t8_ui_shell.md RESIDUAL APPENDIX): F3 §D.36 table drift incl. an INTERNAL_ONLY row; `.fi-chip[data-state-freshness]` colour-map claim; B.4 406 stale selector; B.5 462 "sortable"; F10 nested tier-2; svg `viewBox` + preserveAspectRatio emitted by the shell; `.fi-slice-select` row wraps at ≤767; acceptance `scrollWidth <= clientWidth` at 390 in both themes/languages.
- verified: `git ls-tree origin/main research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md mockups/refs/finance_intelligence/finance_intelligence_mockup.html`; `gh pr view 7903 --json state,mergedAt,mergeCommit`; `gh api repos/mastermindx-market-intelligence/macro/issues/comments/5814661750 --jq .body | head -3`.
- do_not_redo: never re-open the frozen spec through a lane round (a change needs a new DEC); never dispatch a mockup/shell lane that lists the spec under OWNED FILES; never mark a lane PR merged-ready without the `isDraft` read; never accept a phone layout without the `scrollWidth <= clientWidth` measurement.

### T8 shell delivered + seat-accepted (#7952) — deviations and the frozen not-connected binding
- Lane fin_t8_ui_shell (m1) opened #7952 at b42691ff with 40 files; the seat removed three outside OWNED FILES (`.claude/scheduled_tasks.json` 15-min PR poller — quota law; `mockups/evidence/finance-t8-shell/SHIP_LOOP_WAIT.json` receipt; `scripts/capture_finance_intelligence_shots.py` unreferenced tooling) and KEPT `config/site_access.yml` public entries for `/finance_intelligence.{html,css,js}` — they mirror biocatalyst's shell/payload split (seat decision; the payload route stays private at integration).
- Frozen interface restored by the seat (b63d7b6b): `<main data-fi-read-url="{{ fi_read_url | default('') }}">` rendered from the builder's `FI_READ_URL = ""` constant (scripts/build_finance_intelligence_page.py); `boot()` reads the attribute, empty → `data-state="not-connected"` + "Not yet connected to the evidence service. / 尚未接入证据服务。" + no fetch; the harness binds its stub through the same attribute; `test_shell_ships_the_not_connected_binding_until_integration` pins it. The lane's `'__FI_READ_URL__'` literal rendered empty skeletons.
- e8ff4812: `.fi-shell[data-state="not-connected"] .fi-meta { display:none }`; the page-local ARIA swapper is the INLINE template script (lane test asserts `"applyAria" not in js`) — a JS duplicate was reverted. theme.js dispatches `langchange` on `document`; probes on `window` are false negatives.
- Browser acceptance (rendered site page served locally with theme.css): 1440/390 × dark/light × EN/ZH + keyboard PASS with metrics on #7952 (seat review comment). MERGED 2026-09-24T16:11:10Z (4c191a3e); production: `.html` 200 and `.css`/`.js` 200 with no `x-regwall` header at 2026-09-24T17:36:27Z after #7956's Caddy reload (served js carries `not_connected`; the page renders `data-fi-read-url=""`).
- Integration binding: set `FI_READ_URL` in the builder (one constant) when the foundation's route is accepted; nothing else in the shell changes.
- verified: `git ls-tree origin/main templates/finance_intelligence.html.j2 templates/finance_intelligence.js site/finance_intelligence.js scripts/build_finance_intelligence_page.py`; `python3 -m pytest tests/test_finance_intelligence_page.py tests/test_finance_intelligence_hydration.py -q` → 25 passed; `curl -sL https://mastermind-x.com/finance_intelligence.html | grep -c 'data-fi-read-url=""'`.
- do_not_redo: never let a lane commit `.claude/scheduled_tasks.json` or ship-loop receipts; never accept a `__PLACEHOLDER__` string in place of the frozen attribute binding; use `set -o pipefail` before chaining a commit on a piped pytest.
- PRODUCTION DEFECT after the merge (found by the live verification, fixed by #7956 MERGED 2026-09-24T17:33:28Z 6b1483f4): the page served 200 but its paired `.css/.js` answered `401 x-regwall: deny`. Shell-asset publicity is enforced at the Caddy edge, not by `config/site_access.yml` alone: `app/deploy/Caddyfile` `@reg_asset` not-path exclusions (two lines) + public asset `path` lists (two lines) must carry the same entries as `public.exact`; `app/regwall.py` PUBLIC_PATHS is html-only. Biocatalyst had all four, finance none. A public shell therefore needs FOUR registrations, and a T8-style packet must name the Caddyfile lines. The same PR healed a T8-introduced red on main: the lane appended the finance builder after `scripts/build_biocatalyst.py` in render.yml's scope case, breaking the literal `tests/test_biocatalyst_page.py` pins — the finance alternation now precedes it.
- verified (edge): `curl -sL -D - -o /dev/null https://mastermind-x.com/finance_intelligence.js | grep -E '^(HTTP|x-regwall)'` → 200 and no deny after the Caddy reload; `python3 -m pytest tests/test_biocatalyst_page.py -q -k "render or macro or workflow"` → 3 passed.
- SECOND PRODUCTION DEFECT (found by the live browser proof after #7956): the T8 page never loaded `theme.js`, which is what wires the shared nav's theme switch and EN/中文 toggle, so both controls were inert on https://www.mastermind-x.com/finance_intelligence.html (live `document.scripts`: logo_config, stock-logos, live_config, live, finance_intelligence.js). Fix #7968 (abdfa97c): `<script src="theme.js" defer>` ahead of the runtime in the template, mirroring biocatalyst.html.j2 lines 251–253. It is spliced into the RENDER-STAMPED site copy as `theme.js?v=3ffc953f`, the sha256[:8] of site/theme.js that optimize_assets.py stamps and that the live biocatalyst/ontology pages serve (200, public, immutable, bytes hash-match). Never overwrite a stamped committed page with unstamped builder output. `test_shell_loads_the_shared_theme_runtime` pins it and was red on the pre-fix template. A suspected null-doc TypeError on `langchange` was RETRACTED: the runtime's `langchange` listener is registered inside `hydrate()`, so the not-connected shell never runs it. MERGED 2026-09-25T00:59:33Z (5600bb63). PRODUCTION PROOF (built-in browser against the live page, acceptance comment on #7968): `theme.js?v=3ffc953f` served. 1440 and 390 × dark/light × EN/中文 all switch through the real nav toggles, with h1 and notice in the matching language and `scrollWidth − clientWidth = 0`. Keyboard with real key events: Settings button → Enter → Tab to the Light/Auto/Dark segment → Enter switches the theme → Tab ×3 to the language switch (`role="switch"`) → Space switches to 中文 and the switch relabels → Escape closes and returns focus to Settings.
- THIRD PRODUCTION DEFECT (found by that proof at 390 dark): only the Finance panel was dark. The page canvas around it stayed on the browser's white default: `theme.css` does not paint body, `.fi-shell` paints `--fi-canvas` only inside its 1200px box, and html/body computed `rgba(0,0,0,0)`. Fix #7974 (64802bea): `body.fi-page { background: var(--fi-canvas); }` plus the `capture_page_evidence.py` 8-cell matrix in `mockups/evidence/finance-t8-page-canvas/` with its EVIDENCE.yml receipt. Pixel check: dark gutters read luminance 18, light 236. The UI-evidence gate passes and fails without the receipt (positive control). MERGED 2026-09-25T01:32:54Z by the sweeper (`ci-gate` SUCCESS; only red was the known pilot). PRODUCTION_PROOF comment https://github.com/mastermindx-market-intelligence/macro/pull/7974#issuecomment-5825229035: production serves `finance_intelligence.css?v=7030d540` containing the rule. A Playwright probe covered 1440/390 × dark/light × en/zh. Dark: body rgb(13,16,24), gutters 16/16, bottom band 27. Light: rgb(232,235,241), 235/235, bottom band 229–230. No overflow in any case. (The older `mockups/evidence/finance-t8-shell/` holds PNGs only, with no receipt or manifest.)
- CONNECTED-STATE a11y fixed ahead of integration by #7969 (9eb7db26 + bd260bbe, stacked on #7968). #7969 was CLOSED as superseded at 01:40Z: after #7968 squash-merged, it and #7973 went DIRTY (site JS `?v=` stamp plus one test hunk), so the conflict was resolved once on #7973, which carries both commits (merge dc0dc37c). The inline swapper applies `data-aria-*` at parse and on `langchange` BEFORE the runtime hydrates or re-renders, so every hydrated control with a hard-coded English `aria-label` stayed English in 中文 (node harness: 8× `Open evidence` in ZH). The runtime now emits names in the current language through `ariaPair(en, zh)` at all six render sites and `nameChip()` for the hero freshness/outer chips, from `labelRow()`, the EN/ZH row `labelFor` resolves. The frozen spec's instruction placeholders (`{common_as_of}`, `{knowledge_cutoff}`, `{§D.12 …}`, `{§D.14 …}`) had been transcribed literally into `data-aria-en/zh`: the as-of/cutoff spans drop theirs (the visible text is the name) and the chips are named by the runtime. This is a declared deviation from the spec's hero markup. Browser proof on a localhost connected fixture copy: EN, EN→中文 toggle and a fresh 中文 load name every control in the page language, with zero placeholder-brace labels (table in the #7969 body) (DSC:NEW-PAGE-SHELL-DEFECTS-HIDE-FROM-TESTS-THEME-JS-CANVAS-AND-RENDER-TIME-ARIA-NAMES). The integration wave's connected proof re-reads these ZH `aria-label`s on live data.
- INDEPENDENT REVIEW (program Task 15) DONE 2026-09-25: a read-only Opus reviewer attacked the T8 shell and reported 4 MAJOR / 11 MINOR, all connected-state only. It confirmed the not-connected production state clean and found drawer focus, tablist keyboard, the slice selector and innerHTML escaping clean. Response #7973 (b42fb96f, stacked on #7969; updated with main at dc0dc37c, JS stamp 89d9c90e = sha256[:8] of the merged site JS; carries #7969), each item re-proven with the reviewer's headless-Chromium probe (`<scratchpad>/probe.py on|off`):
  - D.23 rights now fail CLOSED (only DIRECT_/DERIVED_DISPLAY_OK show value/excerpt).
  - Missing states render as words: identity unresolved; the spec's "No role recorded"; no invented QUALITATIVE/MEASURED/DESCRIBED; a missing plane reads MISSING; unknown tokens read "not recorded".
  - Malformed deep links are ignored instead of blanking the dossier.
  - The same evidence record can be reopened.
  - A missing record says "not on file".
  - source_outage has its own words; the translated `title=` is gone; the coverage eyebrow no longer prints undefined; the chosen view survives langchange.
  - DEFERRED to the integration wave or a design lane: tablist focus after a programmatic langchange; raw edge slugs; the system-map node cap and missing expand control; mobile macro/exposure "more" content; chip state colour never rendering (chipHtml emits only `fi-chip`, so this needs a design pass with UI evidence); repeated "Open evidence" names and `role="status"` (both need screen-reader verification); 22px targets; names on generic elements; payload prose has no `_zh` fields (a contract gap for the shared owner).
- verified (local): `python3 -m pytest tests/test_finance_intelligence_page.py tests/test_finance_intelligence_hydration.py tests/test_finance_entry_points.py -q` → 40 passed, 1 skipped (#7669 BLOCKED_BY_OWNER); each new test red on its pre-fix runtime/template.

- #7973 MERGED 2026-09-25T02:11:52Z (836379db, seat hand-merge `--match-head-commit dc0dc37c`; `ci-gate` SUCCESS; the only red was the known pilot). LIVE by 02:12:07Z. PRODUCTION_PROOF comment https://github.com/mastermindx-market-intelligence/macro/pull/7973#issuecomment-5825553881: across 1440/390 × dark/light × en/zh, all 8 cases are 200 and `not-connected` with 0 read requests, the hero chips and the evidence-missing notice stay hidden, the notice shows in the page language, and there are 0 page or console errors. The connected paths get their live check at integration.
- verified: `curl -sL "https://www.mastermind-x.com/finance_intelligence.js?v=89d9c90e" | shasum -a 256 | cut -c1-8` → 89d9c90e; `curl -sL https://www.mastermind-x.com/finance_intelligence.html | grep -c -E 'data-aria-(en|zh)="[^"]*\{'` → 0.
- LESSON (DIRTY stack): #7969 and #7973 were branched on the UNSQUASHED #7968 commit (abdfa97c). After #7968 squash-merged, any later main edit to the same lines conflicts (here the site JS `?v=` stamp and a test hunk), and GitHub runs no `ci.yml` on a DIRTY PR. The #7973 watcher therefore found no run for 30 minutes. Resolve ONCE on the top of the stack and close the lower PR as superseded; re-derive the stamp as sha256[:8] of the merged site file.

### T9 entry points delivered + seat-accepted (#7957)
- Lane fin_t9_entries (m1) → #7957: `templates/_finance_sector_deep_dive.html.j2` (one card in the tracker's own `.lane-grid`/`.theme-row` idiom, one `<a href="finance_intelligence.html">`, bilingual, no stylesheet, no stage/rank/score in rendered copy) included ONCE in `templates/state_of_themes.html.j2` after the canonical lanes; `templates/_finance_financials_launch.html.j2` DORMANT (skip mode) because #7669 is OPEN — when #7669 merges, add the guarded include in basket_detail.html.j2 under the `us_sector_financials` guard using the host's prefix variable (the partial's `../` href is provisional); `tests/test_finance_entry_points.py`; `finance-intelligence` job wiring (jinja2 + import-closure paths). A 5-line mirror in `tests/test_state_of_themes.py` (synthetic roots resolve the include) is an accepted deviation. Seat removed a root `PR_BODY.md` and a lane-written agentos handoff (lanes never write agentos/).
- MERGED 2026-09-24T17:14:42Z (dafc546f); production: the tracker is nightly/render-baked — proof = `curl -sL https://www.mastermind-x.com/state_of_themes.html | grep -c 'sector-deep-dive'` ≥ 1 after the render lane runs. NOT YET LIVE at 2026-09-25T00:31Z (count 0, HTTP 200): the page is baked by the nightly engine lane (`engine: regime update`, last 2026-09-24T09:39Z — before the merge) and the render.yml push lane is wedged: holder run 35989213316 has its `render` job queued since 12:05Z on `[self-hosted, render-linux]`, no repo or org runner carries that label (`gh api orgs/mastermindx-market-intelligence/actions/runners` census), every later push render auto-cancels in the `pipeline-render` group (36032941916 at dafc546f), and the last render.yml success was 2026-09-22T07:43Z. That outage is shared infrastructure already recorded in the Market OS handoff (operator relabel), not a Finance defect; the next nightly bake is the proof carrier.
- LIVE 2026-09-25 (update to the line above): the nightly engine bake published `state_of_themes.html` with Last-Modified 2026-09-25 00:48:14 GMT, and the watcher first saw it at 01:15:17Z (`sector-deep-dive`=1, `href="finance_intelligence.html"`=1). PRODUCTION_PROOF comment https://github.com/mastermindx-market-intelligence/macro/pull/7957#issuecomment-5825108176 covers a Playwright probe, fresh signed-out context per case, 1440/390 × light/dark × en/zh. Results: all 8 return 200; the card renders (376 px wide at 1440, 350 px at 390); the text follows the language; there is no horizontal overflow. Keyboard (1440 dark en, 390 light zh): Tab from `button.fchip` puts focus on the card with a 2px solid outline; Enter opens `/finance_intelligence.html` with `<main data-state="not-connected">`. DEFECT: the card and its section carried literal English `aria-label`s, so the 中文 accessible name stayed English (Chromium `getByRole(link, name=金融情报)` = 0 in all zh cases). FIX #7977 (`claude/finance-t9-card-aria-language`, head 4a668d74; MERGED 2026-09-25T01:47:19Z as 05b559b8; not live until a rebuild of the page, because push render 36083526681 is pending behind the render-linux wedge and the nightly engine bake is the realistic path) uses `aria-labelledby`/`aria-describedby` over the l-en/l-zh spans (house idiom `_market_regime_strip.html.j2`), pinned by `test_sector_partial_names_follow_the_page_language`, which fails on the old partial. It goes live at the first nightly bake after merge; re-run the probe then and expect zh `getByRole(link, name=金融情报)` = 1.
- verified: `python3 -m pytest tests/test_finance_entry_points.py -q` → 10 passed (3 skipped: basket_detail skip mode); `git ls-tree origin/main templates/_finance_sector_deep_dive.html.j2 templates/_finance_financials_launch.html.j2`.
- do_not_redo: never let a lane write `agentos/` or a root `PR_BODY.md`; never wire the Financials launch include before #7669 is MERGED.
- LIVE RE-CHECK RECIPE (#7977 at the next page rebuild): in a fresh Playwright context per case (localStorage `theme`, `lang`), load `https://www.mastermind-x.com/state_of_themes.html` and expect `a.sector-deep-dive[aria-labelledby="fi-sdd-name fi-sdd-cta"]`, with `getByRole('link', {name: '金融情报'})` = 1 in zh and `{name: 'Finance Intelligence'}` = 1 in en. The quota-free readiness check is `curl -sL https://www.mastermind-x.com/state_of_themes.html | grep -c 'aria-labelledby="fi-sdd-name fi-sdd-cta"'` ≥ 1.
