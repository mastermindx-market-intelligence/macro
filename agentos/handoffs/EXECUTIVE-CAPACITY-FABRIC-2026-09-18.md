---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/agentos-vps-fabric-fold-20260918
model: fable
ended_because: complete
mission: >
  Records-only checkpoint 2: fold the repaired heads of Macro #7280 and Mastermind #804, the
  service-intent schema decision, the Sol #7289 economics contract, and the Mastermind #600
  return-reader finding into the existing EXECUTIVE-CAPACITY-FABRIC durable record. No source
  was changed, no held PR was readied, merged or armed, no provider was called, no host was
  touched and no runtime action was taken.
state_before: >
  Checkpoint 1 of this same-day handoff (macro #7281 @ 8737d334) had already minted
  DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY and pinned the two DRAFT/HELD carriers at
  Macro #7280 head 284bd893 and Mastermind #804 head 3b5182e2, with A1 still reporting
  NOT_YET_ADMITTED because the sink refused a typed schema. Sol then issued REQUEST_REPAIR
  on both verticals plus an A2 correction (service schema on the existing sink) and ordered
  the #7289 economics contract and the #600 return-reader finding folded into THIS workstream,
  not a new pricing programme.
changed:
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-18.md
    what: >
      Same-day checkpoint 2 (14:00Z): refreshed verified/unverified/do_not_redo/danger_areas/
      next_actions; recorded the immutable repaired heads, the #7289 economics contract, the
      #600 reader link, consumer-composition deferral, and seat/continuation edges.
  - path: agentos/discoveries/DSC-EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY.md
    what: >
      Qualified the claim and body: the schema-only CEO branch still admits RAW v1 stamps;
      #804 A2 now stamps service Jobs with mastermind.executive_service_intent.v1, which that
      branch refuses (StateConflict); residual confined to CEO-origin v1 and owned by
      executive_runtime.py/#699. Falsifier on the RAW v1 stamp remains valid.
  - path: agentos/decisions/DEC-EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK.md
    what: >
      New decision: a non-CEO service principal obtains an admitted Job via one strict
      non-CEO schema on the existing ceo_intent.submit_intent sink (non-v2, coo/coo,
      READ/RESEARCH ceiling, inbox provenance not broadened).
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Durable-state edit to next_action ONLY (status left active): leading paragraph now
      names the repaired heads, the service-intent DEC, #7289, the #600 link, and the
      qualified DSC. No wave row rewritten; no created/updated field authored; generated
      views untouched.
prs: [7280, 804, 7289]
decisions:
  - DEC:EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK
discoveries:
  - DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY
verified:
  - claim: "The records in this lane are schema-valid across the whole store."
    command: "python3 scripts/agentos.py validate"
    result: "exit 0; captured in the lane return file."
  - claim: "This lane changed only the four owned agentos/ paths and nothing outside the Agent OS knowledge plane."
    command: "git diff --name-only origin/main"
    result: "agentos/decisions/DEC-EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK.md, agentos/discoveries/DSC-EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY.md, agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-18.md, agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md."
  - claim: "This carrier is a SPARSE worktree; writes stayed inside agentos/, a checked-out top-level directory, so no omitted tree was written or truncated."
    command: "python3 scripts/worktree_sparse.py status"
    result: "worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots."
  - claim: "The record carrier is claude/agentos-vps-fabric-fold-20260918, minted off origin/main, not a reused squash-merged branch."
    command: "git rev-parse --abbrev-ref HEAD && git merge-base --is-ancestor origin/main HEAD && git rev-parse HEAD origin/main"
    result: "claude/agentos-vps-fabric-fold-20260918; ancestor check exit 0; at edit start HEAD == origin/main == c495a4fb7a01c9ecbcd3cbd91e02bcb102427e04."
unverified:
  - claim: "Macro PR #7280 is OPEN, DRAFT + HOLD-FOR-SOL, labels none, auto-merge null, at immutable repaired head 957927b81926c602b130acdc262fc7b6178fa090."
    what_would_verify: "gh pr view 7280 --repo mastermindx-market-intelligence/macro --json number,state,isDraft,headRefName,headRefOid,labels,autoMergeRequest"
  - claim: "Mastermind PR #804 is OPEN, DRAFT + HOLD body, at immutable repaired head 4c4139b2d30f78a3884c777b144aadf32bfc69ec."
    what_would_verify: "gh pr view 804 --repo mastermindx-market-intelligence/Mastermind --json number,state,isDraft,headRefName,headRefOid,labels,autoMergeRequest"
  - claim: "Sol #7289 economics contract is DRAFT/HOLD, BUILT_NOT_PROVEN, head c95cb6a0b154e1b30e1ed07f012da3d59da3566a, hosted CI 35321406794 queued at ruling time."
    what_would_verify: "gh pr view 7289 --repo mastermindx-market-intelligence/macro --json number,state,isDraft,headRefOid,labels,autoMergeRequest"
  - claim: "Vertical 1 carries 159 tests in tests/test_provider_production_modes.py, R3 REQUEST_REPAIR then R4 APPROVE, and hosted ci run 35330143652 in progress at record time."
    what_would_verify: "On branch claude/provider-production-modes-20260918 at 957927b8: PYTHONPATH=. python3 -m pytest tests/test_provider_production_modes.py -q. Do not claim the hosted run green."
  - claim: "Vertical 2 A1 head a2acae36 = APPROVE + hosted CI 35328140960 SUCCESS; A2 tests/test_ceo_intent.py 66 collected, tests/test_executive_service_principal.py 160 rows, D8 scanner green; hosted CI 35331412994 in progress."
    what_would_verify: "In a Mastermind checkout at 4c4139b2: python3 -m pytest tests/test_executive_service_principal.py tests/test_ceo_intent.py -q. Do not claim run 35331412994 green."
  - claim: "A service stamp does not satisfy the schema-only CEO branch (create_job owner_seat=ceo|chairman → StateConflict); CEO v1/v2 remain byte-identical."
    what_would_verify: "Re-run the #804 A2 refusal tests at head 4c4139b2."
  - claim: "Executive generation 8b231e82 is installed but UNARMED/STOPPED; cron b438623c is hourly; identifiers C088–C092 exist in no repo."
    what_would_verify: "Read the Executive runtime generation/arming surface on the host that holds it; git grep C088|C089|C090|C091|C092 in macro, charting-app and Mastermind at their then-current default branches."
  - claim: "Mastermind #600 return-reader at scripts/web_ceo_offline_delivery_canary.py:271-287 keeps only rows with a populated record.obligation, so delivered/ACK rows are excluded and normal histories print EFFECT_UNKNOWN_UNRESOLVED; candidate consumes WakeLedgerRepository.list_records(obligation_id); measured 5 failed/9 passed → 14 passed; NOT production acceptance."
    what_would_verify: "Read https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5726791963 and the cited lines on that PR's head."
unresolved:
  - "Macro #7280, Mastermind #804 and Sol #7289 remain DRAFT + HOLD. No session may Ready, merge or auto-merge any of them without an explicit Sol acceptance ruling."
  - "Hosted CI for #7280 (35330143652) and #804 A2 (35331412994) was in progress at record time and is NOT claimed green. #7289 hosted CI 35321406794 was queued at ruling time and is BUILT_NOT_PROVEN."
  - "The residual schema-only CEO hole for RAW v1 stamps is NOT fixed by #804: it stays owned by executive_runtime.py / open PR #699."
  - "Consumer composition (extend shared engine/llm_auth.build_providers with production-mode descriptors) is NOT started; it depends on #7179 remote-complete release by that carrier's writer."
  - "Vertical B (OpenCode native Worker) is NOT started: it collides with PR #762 and #590."
  - "A5 authenticated ingress is deferred (App/JWT-bound principal mapping; OAuth caller never selects actor)."
  - "The Mastermind #600 return-reader finding is a link only — not production acceptance and not a new program."
  - "Executive generation 8b231e82 is installed and UNARMED/STOPPED; arming is gated on HUMAN_AUTH / CREDENTIAL_READINESS, a human credential act."
next_actions:
  - "Do not Ready, merge, arm or auto-merge Macro #7280, Mastermind #804 or Sol #7289 without an explicit Sol acceptance ruling."
  - "After #7179's writer marks that carrier remote-complete: extend the SHARED engine/llm_auth.build_providers with reviewed production-mode descriptors consuming engine/provider_production_modes.py; keep make_call as the single fallback/effect owner; GLM adapter over the existing hardened helper; extend provider_workloads.v1 only then; first proof = AI Brief site_batch shadow selecting ONE economical rung."
  - "Residual RAW-v1 CEO-origin stamps: coordinate with the owner of Mastermind #699 on executive_runtime.py. Do not attempt the fix from #804 or any other non-#699 PR."
  - "When the reader's lawful source lane is available, take in the Mastermind #600 return-reader finding (comment 5726791963) as intake on that lane. Do not mint a new program."
  - "Leave A5 authenticated ingress deferred. Owned-elsewhere surfaces stay with their owners: ingress/service #779/#695, App/gateway #797/#779/#818, worker_adapter.py #762."
  - "Touch HUMAN_AUTH / CREDENTIAL_READINESS only through the Chairman; it is not a session action."
  - "Never re-post PICKUP_ACK or START for this operation."
do_not_redo:
  - "Never append MiniMax or GLM to capacity v1: engine/provider_capacity.py is a CLOSED 12-slot surface. This row carries no DNR:<KEY> citation on purpose — grep of research/DO_NOT_REBUILD.md at this carrier finds no capacity-v1 row, so the law is the closed 12-slot surface itself, not a kill-registry row."
  - "Never add a MiniMax/GLM cost table outside lib.ai_costs. #7280 receipts compose into that owner; no separate MiniMax/GLM cost math."
  - "Never broaden executive_inbox.ceo_intent_provenance. It stays CEO-only."
  - "Never let a service intent use the v2 orchestration branch (mastermind.ceo_intent.v2)."
  - "Never fix the schema-only CEO branch from a non-#699 PR. The residual is CEO-origin RAW v1 stamps in executive_runtime.py."
  - "Never flip the #7103 plan flags."
  - "Never make brain/provider_waterfall.py an API ladder."
  - "Never Ready, merge or auto-merge Macro #7280, Mastermind #804 or Sol #7289 without an explicit Sol acceptance ruling."
  - "Never re-post PICKUP_ACK or START for this operation."
  - "Never treat this handoff as an arming decision: it records state, it authorizes nothing (knowledge plane, not control plane)."
danger_areas:
  - ".github/ci/legacy-jobs.yml — many concurrent writers; the vertical-1 edit is a run-line plus the merge-gate provider step and must not be widened."
  - "engine/earnings_qual.py — now shared by earnings and production modes (ADDITIVE _call_openai_compat_detailed; legacy _call_openai_compat tuple contract must stay identical)."
  - "engine/llm_auth.py — concurrent carriers #7179 and #7185; consumer composition waits on #7179 remote-complete."
  - "control_plane/ceo_intent.py — now three schemas (ceo v1, ceo v2, executive_service_intent.v1)."
  - "executive_runtime.py — residual RAW-v1 CEO-origin hole; any edit collides with open PR #699."
  - "worker_adapter.py — the B slice shares this file with PR #762/#590, and its implementation= line must stay implemented=False."
  - "The three held carriers themselves (#7280, #804, #7289): they are PUBLIC DRAFT PRs, and an accidental ready/arm/merge is an authority breach, not a CI mistake."
---

# Checkpoint 2 (14:00Z) — repaired heads, service-intent schema, economics + reader fold

This lane is RECORDS ONLY. Sol rulings 1789717894.450799 / 1789719708.985309 ordered the #7289
exact head and economics contract folded into the existing EXECUTIVE-CAPACITY-FABRIC record,
not a separate pricing programme. Sol input 1789716959.813089 ordered the Mastermind #600
return-reader finding linked into this workstream, not another program. Nothing in this
track may be readied, merged, armed or auto-merged without an explicit Sol acceptance ruling.
The holds are authority states, not CI states.

Seat = Claude6 `5fae71cf` (Fable). Root carrier edges: REPAIR_INTAKE `1789722379.535409`,
A2 START `1789723475.083089`. Cron `b438623c` hourly. Executive generation `8b231e82` remains
UNARMED/STOPPED. Identifiers C088–C092 exist in no repository.

## Vertical 1 — production API usage modes (Macro, PR #7280)

Macro PR #7280, branch `claude/provider-production-modes-20260918`, immutable repaired head
`957927b81926c602b130acdc262fc7b6178fa090`, DRAFT + HOLD-FOR-SOL, labels none, auto-merge
null. Sol REQUEST_REPAIR items B1–B8 (1789699662.814189) implemented: closed in-code
`_MODE_IDENTITY` table (per-field drift refused, zero transport); models `MiniMax-M3` /
`glm-5.3-flash` taken from Sol's #7289 pricing rows; incumbent health classes
`auth` / `usage_limit` / `timeout` / `transport` / `unsupported` / `error`; GLM usage via
ADDITIVE `engine/earnings_qual.py::_call_openai_compat_detailed` (legacy
`_call_openai_compat` tuple contract proven identical across six response shapes);
`price_state` derived only from `lib.ai_costs` (unknown until pricing rows land); closed
`GLM_REQUEST_PROFILE` (temperature + max_tokens ceiling, `UNQUALIFIED_PENDING_CANARY`);
single `_resolve_credential` boundary; a 2xx without usable text is `error` (R3 finding);
bare `#` refused. Non-author reviews: R3 REQUEST_REPAIR (1 item) → R4 APPROVE. 159 tests in
`tests/test_provider_production_modes.py`. Wired into the merge-gate provider step
(`.github/ci/legacy-jobs.yml`). Hosted ci run `35330143652` in progress at record time —
do not claim green.

## Vertical 2 — service principal (Mastermind, PR #804)

Mastermind PR #804, branch `claude/executive-service-principal-20260918`, immutable repaired
head `4c4139b2d30f78a3884c777b144aadf32bfc69ec`, DRAFT + HOLD body.

A1–A3 (Sol 1789699662): intent id = domain-separated (schema, principal_id, operation_key);
typed block carries `requested_authorities` / `effective_authorities=[READ,RESEARCH]` +
`write_authorities=[]`; `submit()` fails closed unless ADMITTED. Head `a2acae36` = APPROVE
+ hosted CI run `35328140960` SUCCESS.

A2 (Sol 1789700503 + census 1789717957; recorded as
`DEC:EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK`):
`INTENT_SCHEMA_SERVICE = "mastermind.executive_service_intent.v1"` +
`RECEIPT_SCHEMA_SERVICE` on the existing sink; service keys = v1 + `principal_id` +
`task_kind`; `svc-` intent ids; reserved actors refused; ceiling READ/RESEARCH in
validator + belt before `create_job`; explicit `owner_seat="coo"`,
`escalation_target="coo"`, no orchestration/binding; `_provenance()` stores the service
schema + evidence fields; `executive_inbox.ceo_intent_provenance` untouched and pinned
CEO-only; service stamp does NOT satisfy the schema-only CEO branch
(`create_job(owner_seat="ceo"|"chairman", provenance=service_stamp)` → StateConflict);
CEO v1/v2 byte-identical. Non-author review R4 APPROVE;
`tests/test_ceo_intent.py` 66 collected, `tests/test_executive_service_principal.py` 160
rows, D8 scanner green; hosted CI run `35331412994` in progress — do not claim green.

Owned-elsewhere: `executive_runtime.py` #699 (raw-v1 residual), ingress/service #779/#695,
App/gateway #797/#779/#818, `worker_adapter.py` #762. A5 authenticated ingress deferred
(App/JWT-bound principal mapping; OAuth caller never selects actor).

## Qualified discovery

`DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY` still holds for RAW
`mastermind.ceo_intent.v1` stamps. The service path no longer mints that stamp. The
residual hole is CEO-origin v1 and stays owned by `executive_runtime.py` / #699.

## Economics contract (Sol #7289)

Sol #7289 head `c95cb6a0b154e1b30e1ed07f012da3d59da3566a`, branch
`claude/provider-pricing-economics-20260918-sol`, DRAFT/HOLD, BUILT_NOT_PROVEN, hosted CI
`35321406794` queued at ruling time. `lib.ai_costs` stays the sole cost owner;
`ai_costs.usage.v1` unchanged; rich rows may carry cache rates + context tiers;
MiniMax-M3 512K/1M tiers, GLM-5.3-Flash post-promo list rate; unpublished cache-write
rates → UNKNOWN. #7280 receipts compose into that owner; no separate MiniMax/GLM cost
math; the later AI Brief shadow compares actual cost from that ledger.

## Mastermind #600 return-reader finding

Sol input 1789716959; GitHub comment
https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5726791963.
`scripts/web_ceo_offline_delivery_canary.py:271-287` keeps only rows with a populated
`record.obligation` (only WAKE_REQUESTED has it) → delivered/ACK rows excluded →
`EFFECT_UNKNOWN_UNRESOLVED` for normal histories; candidate consumes
`WakeLedgerRepository.list_records(obligation_id)`; measured 5 failed/9 passed → 14
passed; NOT production acceptance. Link only; no new program; intake owner = the
reader's lawful source lane when available.

## Consumer composition — not started

Sol 1789700334.315469, after #7280 repair + #7179 release: extend the SHARED
`engine/llm_auth.build_providers` with reviewed production-mode descriptors consuming
`engine/provider_production_modes.py`; `make_call` stays the single fallback/effect
owner; GLM adapter over the existing hardened helper; `provider_workloads.v1`
vocabulary extended only then; first proof = AI Brief `site_batch` shadow order
selecting ONE economical rung. NOT started (depends on #7179 remote-complete release
by its writer).

## Custody census — checkpoint 2

| Slice | Owns | Collides with | State |
|---|---|---|---|
| Service-intent schema on existing sink | `ceo_intent.py` | none for the schema constant | BUILT on #804 repaired head; DRAFT/HOLD |
| Residual actor-aware CEO gate (RAW v1) | `executive_runtime.py` | open PR #699 | NOT STARTED from this track |
| B — OpenCode native Worker | new `control_plane/opencode_worker.py` + one `implementation=` line at `worker_adapter.py:63-68` | PR #762 / #590 | NOT STARTED; must keep `implemented=False` |
| Consumer composition | `engine/llm_auth.build_providers` | #7179 | NOT STARTED; waits on #7179 remote-complete |
| A5 authenticated ingress | App/JWT-bound principal mapping | #797/#779/#818 | DEFERRED |

## Arming state

Executive generation `8b231e82` is installed and UNARMED / STOPPED. The next gate is
HUMAN_AUTH / CREDENTIAL_READINESS, keyed on the Chairman's `CREDENTIAL_EXPIRES_AT`.
Nothing in this lane moved that gate, and nothing here authorizes moving it: it is a
human credential act.

## The one thing a resuming session must not get wrong

#7280, #804 and #7289 are held by AUTHORITY, not by CI. Re-running CI, rebasing, or
clearing a red check on any of those carriers does not release it. The release
condition is an explicit Sol acceptance ruling.

# Checkpoint 1 (landed in macro #7281 @ 8737d334) — first same-day pin

Checkpoint 1 pinned Macro #7280 at head `284bd893f5fb2085d597611d065017494f3275db` and
Mastermind #804 at head `3b5182e2545cab671f2da2db6735b51c926baf18`, both DRAFT/HELD,
and minted `DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY` against the then-current
reproduction (a READ/RESEARCH service principal could obtain a RAW v1 stamp that
admitted `owner_seat="ceo"`). A1 then reported `NOT_YET_ADMITTED` because the sink
refused a typed schema, a provenance key and `constraints.task_kind`. Those heads are
superseded as live pins by Checkpoint 2; the discovery remains in force as qualified
in Checkpoint 2. Sol root `C0BSBM78V1N/1789324397.992989`; operation
`agent-fabric-end-to-end-fable-integration-20260913-sol-001`; VPS economical-provider
track then ruled at edges `1789694411.329219` and `1789694989.668909`.


# PF1 current-continuity addendum — 2026-09-19

Same-carrier records correction for the existing EXECUTIVE-CAPACITY-FABRIC workstream.
It preserves Checkpoint 2 and supersedes only stale PF1 continuation facts.

## Current truth
- Authoritative native PF1 source: `claude/ssd-pf1-native-claude-worker-adapter@5b461fb217e6f0fba5080a12eb98df82b396e6c7`, BUILT / UNMERGED / UNARMED, no PR.
- Exact carrier remains `C0BSBM78V1N/1788797971.486229`.
- R90 remains `HOLD_SAME_OWNER_AND_SOURCE / NO_RETRY / NO_SUCCESSION`; reset prose is not retry/transfer authority.
- Do not create a replacement native writer, branch or carrier because the retained session is unavailable.
- Mastermind #759 common launch-attestation law is protected / DO_NOT_REDO.
- Mastermind #586 R8 is protected as `4948e271e0b7dfa7e8653a6a01bcd1399d113dae`; consume its auth-free validation and bounded cancellation/finalization semantics from current Mastermind.
- Mastermind #762@495e4668 remains `SOURCE_CUSTODY_BLOCKED / CANDIDATE_FOLD_ONLY`; it is fold evidence, not a successor, and its last qualified state still had a current-D8 red plus an unresolved exact-model admission seam.

## Exact-model admission
The first native provider request must fail closed unless the existing Family-B/native-realm config owner supplies a generation-bound effective-policy observation proving the exact one-model/no-fallback contract.
Use a full exact model ID under version-qualified `--restricted`, a single-model allowlist, empty availability fallback and `switchModelsOnFlag=false`.
`/status` alone is insufficient: it does not expose `fallbackModel`, identify every effective key source, or rule out organization/account model substitution.
Ambiguity, substitution, unresolvable allowlist or config-generation drift is a pre-request refusal; post-result model identity is secondary provenance.

## Exact next action
After lawful R90 same-owner resume: re-pin protected Mastermind + same-SHA Skillpack; reconcile retained `5b461fb2...`; consume #759/#586 as DO_NOT_REDO; selectively fold only still-needed #762 deltas; close D8 + exact-model admission; then run fresh current-base behavioral tests and genuine non-author review.
Reuse the protected native preflight surface. Only after the Family-B realm/config owner and those source gates are current may the retained PF1 owner attempt one bounded real Executive child Job.
This addendum is knowledge-plane continuity only: it does not release R90, transfer PF1 custody, authorize provider/login/credential work, Ready/merge held PRs, or create a runtime effect.
