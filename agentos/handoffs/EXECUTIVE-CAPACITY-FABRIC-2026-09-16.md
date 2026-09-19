---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/agentos-capacity-fabric-native-correction-20260916
model: opus
ended_because: complete
mission: >
  Preserve, in the canonical cross-repo knowledge plane, Sol's 2026-09-16 native-versus-compatible
  correction (rulings R21/R22) and the exact next native dependency, together with the current state of
  the Fable principal fabric operation, so a cold stranger can resume without the commissioning
  conversation. Sol's ask, verbatim from R21: "preserve the correction + next native dependency in the
  Agent OS handoff/workstream (macro `agentos/`) at the next owned checkpoint". Records only: this
  session changed no source, merged no Mastermind carrier, released no writer, called no provider,
  touched no host and performed no runtime action.
state_before: >
  The workstream's newest handoff was EXECUTIVE-CAPACITY-FABRIC-2026-09-13, which pinned protected
  Mastermind master at 89d890f0ae526205e762ad2924b6590f35847e8f and listed seven open Wave 1 Draft
  carriers including "#581 e6aca940 HF1-D: add the fixed-profile Claude subscription worker". Nothing in
  the store said what that carrier actually is. Read cold, the wave row, the PR title and the file names
  it lands all say "Claude", so a session sizing native Anthropic Fable/Opus capacity would reasonably
  have counted #581 as the native worker vertical and treated its merge as PF1 progress. Meanwhile #581
  had merged, protected master had moved to 7642aea155d2817219135b24246b55c1d7611c66, and the PF1 wave
  row still said only "with Claude as the preferred first real non-Codex proof" without naming PF1-F0,
  PR #455, or the missing native adapter. The correction existed only in a local kit ruling file outside
  every repository.
changed:
  - path: agentos/discoveries/DSC-CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC.md
    what: >
      New discovery record. Claim, falsifier and so_what for the native-versus-compatible distinction,
      with the byte-level receipts at protected Mastermind master
      7642aea155d2817219135b24246b55c1d7611c66: exactly three subscription profiles (glm, alibaba,
      minimax), no `claude-code` descriptor in control_plane/worker_adapter.py, absent
      control_plane/claude_worker.py and tests/test_executive_claude_worker.py, present PF1 plan doc,
      and PF1's only live carrier PR #455 OPEN/DRAFT at 0a368935ece318c1b7f3301337f75d3a58d61006. Names
      the three closed errors: a #581 merge is not native readiness, #581-era fixtures are not
      production proof, and the native gap does not license a replacement worker outside PF1.
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Durable-state edits only, no completed wave rewritten. The PF1 wave `next_action` now names the
      exact next native dependency (PF1-F0 custody and its current protocol gate; the missing native
      `ClaudeCodeWorkerAdapter` with a dedicated native-auth worker principal and no token-in-environment
      shortcut, through the existing common broker) and cites DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-
      NATIVE-ANTHROPIC. The HF1 umbrella wave `next_action` records that #581 merged as
      27a5d893ca28f7006c1007dffa51e677c9c7a4ab and is a compatible-provider harness, not the native
      vertical. The workstream `next_action` is re-pinned to protected master
      7642aea155d2817219135b24246b55c1d7611c66 and to the current fabric operation. Two `landmines` rows
      and two `do_not_redo` rows were added for the compatible-versus-native boundary; `discoveries`
      gains the new DSC key and `artifacts` gains both new files. No `created`/`updated` field was
      authored and no generated view (docs/AGENT_OS_STATE.md, data/governance/agent_os_state.json) was
      touched.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16.md
    what: >
      This continuation record: the correction with its receipts, the native owner path, the exact next
      native dependency, the current fabric program state at 2026-09-16T02:4xZ, and the boundaries the
      next session must not cross.
prs: []
verified:
  - claim: "Protected Mastermind master is 7642aea155d2817219135b24246b55c1d7611c66, the pin Sol's R21/R22 rulings were issued against."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind fetch -q origin master && git rev-parse origin/master"
    result: "7642aea155d2817219135b24246b55c1d7611c66 — exactly the expected pin, no descendant movement between the ruling and this record."
  - claim: "The reviewed subscription provider catalog contains exactly three providers — GLM, Alibaba and MiniMax — and no Anthropic/native profile."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind show origin/master:config/subscription_provider_profiles.v1.json (parsed for provider/id fields)"
    result: >
      Top-level keys `schema`, `verified_at`, `profiles`. Three profiles: `glm-coding-plan` with
      provider `glm`, `alibaba-token-plan-personal` with provider `alibaba`, `minimax-token-plan` with
      provider `minimax`. Each also carries a `quota_profile.provider` repeating the same value. No
      fourth profile and no Anthropic entry.
  - claim: "control_plane/worker_adapter.py carries no `claude-code` descriptor; what exists is `claude-compatible-subscription`."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind show origin/master:control_plane/worker_adapter.py | grep -n claude"
    result: >
      Exactly three hits and no more — `56: \"claude-compatible-subscription\": AdapterDescriptor(`,
      `57: adapter_id=\"claude-compatible-subscription\",`, `59: \"control_plane.claude_subscription_worker\"`.
      All three are the same descriptor entry; no `claude-code` string appears. The grep firing on this
      file is the positive control that makes the absence of `claude-code` an instrument-verified null.
      The full descriptor table at lines 50-70 holds four ids: `codex-cli` (implemented=True,
      control_plane.codex_worker.CodexWorkerAdapter), `claude-compatible-subscription` (implementation
      control_plane.claude_subscription_worker.ClaudeSubscriptionWorkerAdapter), and the deliberately
      unarmed seams `openai-compatible` and `acp` (both implemented=False).
  - claim: "There is no native Claude worker module or its test at protected master."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind ls-tree origin/master control_plane/claude_worker.py tests/test_executive_claude_worker.py"
    result: "Empty output, exit 0 — neither path exists. `git ls-tree -r --name-only origin/master | grep -i claude` confirms control_plane/claude_subscription_worker.py is the only control_plane Claude module."
  - claim: "The PF1 native-worker plan document exists at protected master."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind ls-tree origin/master docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md"
    result: "100644 blob 5ec3b062264c4146a7c92e1576f1753f788bd440 — present."
  - claim: "The merged subscription worker is the Claude Code harness pointed at the three third-party profiles, by its own source."
    command: "git -C /Users/chriswong/Documents/Cluade/Mastermind show origin/master:control_plane/claude_subscription_worker.py | grep -nE 'subscription_provider_profiles|adapter_id|profile'"
    result: >
      Docstring `:1` reads \"Fixed-profile Claude Code worker for subscription-backed model providers\"
      and `:4` \"reviewed provider profile. The launch request cannot select a provider, base\";
      `:64` imports from `control_plane.subscription_provider_profiles`; `:135`
      `profile = get_profile(binding.profile_id, document=profiles)`; `:264`
      `adapter_id = \"claude-compatible-subscription\"`.
  - claim: "Mastermind PR #581 is MERGED, and its merge did not change any of the four reads above."
    command: "gh pr view 581 -R mastermindx-market-intelligence/Mastermind --json state,mergeCommit,title"
    result: >
      state MERGED, mergeCommit 27a5d893ca28f7006c1007dffa51e677c9c7a4ab, title \"[HF1-D] Add
      fixed-profile Claude subscription worker\". This is a DISCREPANCY against the 2026-09-13 handoff,
      which pinned #581 as an open Draft carrier at head e6aca940. The merge is consistent with Sol's
      R21 law rather than a refutation of it: R21 states \"never treat a #581 merge as native
      readiness\", and every byte-level read above was taken at 7642aea1, which already contains the
      merge.
  - claim: "PF1's native owner path is live only as the provider-free protocol falsifier, still open, still draft, still held."
    command: "gh pr view 455 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,title"
    result: >
      state OPEN, isDraft true, headRefOid 0a368935ece318c1b7f3301337f75d3a58d61006, title
      \"[PF1-F0][HOLD] Provider-free Claude CLI protocol falsifier\" — head matches Sol's R21 pin
      exactly.
  - claim: "Mastermind #676 (Claude parity packet) is OPEN/DRAFT at the head Sol's R21/R22 named as the final composed repair return."
    command: "gh pr view 676 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid"
    result: "state OPEN, isDraft true, headRefOid 7e6a35b66e8ec42a3263fcb7c06379d68bbc474c — matches R21's final candidate head."
  - claim: "Mastermind #677 (W1-H3) is OPEN/DRAFT with its head still at 2575c111210b1f6e51b4c900087a95331284b173."
    command: "gh pr view 677 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid"
    result: >
      state OPEN, isDraft true, headRefOid 2575c111210b1f6e51b4c900087a95331284b173. The R17 B1-B3
      repair round was in progress at this reading and had not yet produced a new head; this is a pin,
      not a promise.
  - claim: "The Agent OS store validates with zero errors after these edits, with no new warning naming this workstream or these records."
    command: "python3 scripts/agentos.py validate"
    result: >
      Exit 0 — 1118 records (69 workstreams, 318 decisions, 270 discoveries, 461 handoffs), 0 errors,
      97 warnings. Baseline on the untouched branch at Macro main
      9579caf3f950f1a2e7b959a9b3b68d26e42e5d06 was 1116 records (269 discoveries, 460 handoffs), 0
      errors, 97 warnings, so the two new records added no warning.
unverified:
  - claim: "PF1-F0's falsifier result, once #455 concludes, will admit or refuse the native CLI protocol boundary."
    what_would_verify: >
      Read #455's own returned falsifier verdict at its then-current head through PF1's existing owner
      and review route. This session read only PR state fields (state, isDraft, headRefOid, title) and
      opened neither the diff nor any falsifier output.
  - claim: "What the `implemented: bool = False` default on the `claude-compatible-subscription` descriptor actually gates at runtime."
    what_would_verify: >
      `git grep -n 'descriptor.implemented\\|\\.implemented' ` across Mastermind at the then-current
      protected master and read every consumer. Within worker_adapter.py itself the field is only
      defined and set (lines 46/53/66/68) and never read, while the `is not implemented` refusal at :87
      branches on the `implementation` string rather than on this flag. The byte-level observation is
      recorded here without any consequence claim attached to it.
  - claim: "Mastermind #676's exact-head hosted `test` run 35045615311 concluded, and the FULL_REREVIEW R22 requires has been returned."
    what_would_verify: >
      The seat's existing non-author review route returning a fresh full re-review of
      7e6a35b66e8ec42a3263fcb7c06379d68bbc474c after that run concludes. R22 caps the outcome at
      APPROVE_AS_SPEC_ONLY regardless. This session polled no CI.
  - claim: "Any Mastermind carrier named in this record is mergeable, ready, or releasable right now."
    what_would_verify: >
      Per-carrier current-base proof, concluded required checks, exact-head independent review and an
      explicit Sol release at action time. Every carrier named here was DRAFT and held at this reading,
      and this session merged, readied, labelled and released nothing.
unresolved:
  - "Whether PF1's native `ClaudeCodeWorkerAdapter` lands as a fifth `ADAPTER_DESCRIPTORS` entry beside `claude-compatible-subscription` or replaces the seam differently — the PF1 plan document was confirmed present by blob SHA but not opened by this session, and the adapter shape is PF1's to choose, not this record's to prescribe."
  - "Where the dedicated native-auth worker principal for a native Claude adapter comes from, given OCR-2C Family A already returned FAMILY_A_NO_SAFE_EQUALITY_WITNESS and FAMILY_A_NO_ROTATION_INVALIDATION. The native identity question and the native adapter question are adjacent and unresolved together; Family B remains a separate architecture gate."
  - "Whether the HF1 umbrella wave can close once the remaining HF1-B/C/D carriers land, or must stay in_progress until PF1 proves one real non-Codex vertical. This record leaves it in_progress and does not decide."
next_actions:
  - "Before sizing, routing, promising or reporting native Anthropic Fable/Opus capacity anywhere, read DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC and re-run its four falsifier commands at the then-current protected Mastermind master. If all four still hold, native capacity is NOT BUILT, whatever a merged carrier is titled."
  - "Track the native dependency through PF1 only: PF1-F0 custody and its current protocol gate on PR #455 (OPEN/DRAFT/HOLD at 0a368935ece318c1b7f3301337f75d3a58d61006), then a native `ClaudeCodeWorkerAdapter` with a dedicated native-auth worker principal and no token-in-environment shortcut, through the existing common broker. Never open a replacement carrier or a second native writer."
  - "Continue the fabric operation agent-fabric-end-to-end-fable-integration-20260913-sol-001 on its existing critical path: W1-H3 (#677) closing Sol R17 B1-B3 on the SAME child, worktree and writer with no replacement PR or branch, and H0 prestage attempt 2 on the existing runner without killing, restarting or duplicating either the Mastermind carrier or the in-progress Macro clone."
  - "As each Wave 1 carrier merges, move its wave row in agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md to `done` with the merge SHA in the same COMPLETED_DO_NOT_REPEAT shape RF1 and HF1-A use — and, for any carrier whose title says Claude, state in the same row whether it is compatible-provider or native."
  - "Re-read every head named in this record before acting on it (`gh pr view <n> -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid`). Heads here are pins taken at 2026-09-16T02:4xZ under an active principal, and #677's repair round was in flight at that moment."
do_not_redo:
  - "Do not treat the merged Mastermind #581 (27a5d893ca28f7006c1007dffa51e677c9c7a4ab, '[HF1-D] Add fixed-profile Claude subscription worker') as native Anthropic capacity or as PF1 progress. It is the Claude Code harness for the three third-party subscription providers in config/subscription_provider_profiles.v1.json — glm-coding-plan, alibaba-token-plan-personal, minimax-token-plan. Sol ruling R21, 2026-09-16: never treat a #581 merge as native readiness."
  - "Do not promote #581-era or #676-era fixture corpora, static check counts, killed mutants or proposed-scenario counts to native capacity or to production proof. Proposed scenarios are not executed canaries, and a passing review or green CI proves neither a native worker, enrollment, telemetry, unattended permission nor COO parity (Sol R22)."
  - "Do not build a native Claude worker, adapter or carrier outside PF1. Native ownership is PF1 `claude-code` / `ClaudeCodeWorkerAdapter` under plan docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md; PF1-F0 custody is PR #455 and it stays held. A second native writer for one operation is the error, not a shortcut around a slow one."
  - "Do not re-review the historical heads 7956f744, 73f69bf5, 50e62355, 8fb0743e or 85a9d127. Each was superseded by a later repair head and each is closed; #676's current head is 7e6a35b66e8ec42a3263fcb7c06379d68bbc474c and #7179's is 889174901bdaabba44a8f60f3179ff7bd32c8061."
  - "Do not restart, kill or duplicate the H0 prestage runner or the in-progress Macro clone, and do not open a replacement child, branch or PR for W1-H3 (#677). Both continue on the SAME existing process, child, worktree and writer per Sol R19."
  - "Do not flip `interactive_only`, `unattended_background_allowed` or `production_backend_allowed` on any provider profile from a canary result. Sol R6 and R13: a successful interactive canary never sets unattended_background_allowed=true, and headless `claude -p` one-act runs are UNATTENDED execution for Mastermind policy unless a current provider-policy receipt explicitly admits that exact mode."
  - "Do not re-derive the native-versus-compatible question by scanning chat, Slack or a local kit file. The four falsifier commands in DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC are the whole procedure, and they run against the repository rather than against anyone's memory."
danger_areas:
  - "Naming collision is the trap this record exists for. A file named claude_subscription_worker.py, a descriptor id beginning `claude-`, and a PR titled 'Claude subscription worker' all describe the Claude Code HARNESS, not Anthropic capacity. The descriptor id says `claude-compatible-subscription`, and the word `compatible` is load-bearing. Read the profile catalog before believing any file name."
  - "Secret-bearing surfaces stay closed. Provider homes, tokens, cookies, API keys, account identifiers, raw host addresses and private endpoints never enter Agent OS, GitHub, Slack or any receipt. Credential movement, rotation and canary arming are Chairman-only acts; a native-auth worker principal for PF1 is a design requirement recorded here, never a credential this store may carry."
  - "This store is a knowledge plane and never a control plane (architecture invariant I1). Nothing written here gates, dispatches, schedules, releases a writer or proves liveness. A record stating a native dependency does not authorize building it; PF1's owner and Sol's release do."
  - "Heads and protected refs move fast under an active principal. #581 went from an open Draft carrier at e6aca940 in the 2026-09-13 record to merged at 27a5d893 by this one, and #677's repair round was in flight at this reading. Re-read refs at action time; never act on a SHA copied out of a record."
  - "The gap between merged and proven is the standing over-claim risk for this workstream. RF1, HF1-A and now #581 are protected source; none has driven a real native provider turn, Ready receipt, Executive Job or installed-host receipt. A records-only edit that writes 'proven' where the truth is 'merged' is a lie the next session will act on."
decisions:
  - DEC:EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT
discoveries:
  - DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC
---

## §0 The correction

Sol ruled on 2026-09-16 (rulings R21 and R22, `orch/fabric/SOL_RULINGS_2026-09-15_2300Z.md`) that
Mastermind #581 is the **Claude Code harness** for GLM, Alibaba and MiniMax subscription providers, and
is **not** an implemented native Anthropic Fable/Opus worker. This session verified that correction
against the repository at protected master `7642aea155d2817219135b24246b55c1d7611c66` rather than
restating it, and every read agreed:

- `config/subscription_provider_profiles.v1.json` holds exactly three profiles — `glm-coding-plan`
  (`glm`), `alibaba-token-plan-personal` (`alibaba`), `minimax-token-plan` (`minimax`). No Anthropic
  profile.
- `control_plane/worker_adapter.py` has no `claude-code` descriptor. Its three `claude` hits are one
  entry, `claude-compatible-subscription`, implemented by
  `control_plane.claude_subscription_worker.ClaudeSubscriptionWorkerAdapter`.
- `control_plane/claude_worker.py` and `tests/test_executive_claude_worker.py` do not exist.
- `docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md` does exist
  (blob `5ec3b062264c4146a7c92e1576f1753f788bd440`).

One fact moved since Sol wrote R21: **#581 is now MERGED**, as
`27a5d893ca28f7006c1007dffa51e677c9c7a4ab`. That is recorded here exactly as found, and it strengthens
rather than weakens the ruling — all four reads above were taken at a pin that already contains the
merge, and R21 anticipated precisely this by forbidding anyone to read a #581 merge as native readiness.

The rejection class Sol named E11 is the general form: **a compatible-provider alias must never be
treated as native Anthropic capacity.** Two corollaries travel with it — a #581 merge is not native
readiness, and #581 fixtures cannot become production proof.

## §1 The native owner path

Native Anthropic capacity belongs to the **PF1** wave and to no one else. Its identity:

| Element | Value |
|---|---|
| Adapter identity | PF1 `claude-code` / `ClaudeCodeWorkerAdapter` |
| Plan | `docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md` |
| Operation | `pf1f0-nested-cache-consistency-repair-20260907-sol-001` |
| Carrier | Slack `C0BSBM78V1N/1788797971.486229` |
| Retained owner | `/root/wbr_f1_native_eligibility` |
| Retained candidate | `545b9176…` |
| Live falsifier | Mastermind PR #455, "[PF1-F0][HOLD] Provider-free Claude CLI protocol falsifier", OPEN / DRAFT / HOLD at `0a368935ece318c1b7f3301337f75d3a58d61006` |

PR #455 is a **provider-free protocol falsifier** — an instrument for disproving assumptions about the
CLI boundary without touching a provider. It is not an implemented worker, and merging it would not
produce one.

## §2 The exact next native dependency

Two things, in this order, and both inside PF1:

1. **PF1-F0 custody and its current protocol gate.** #455 stays on its own writer and its own hold.
   Custody is untouched by any review, ruling or merge recorded here (Sol R22).
2. **The missing native `ClaudeCodeWorkerAdapter`**, carrying a **dedicated native-auth worker
   principal** — no token-in-environment shortcut — routed through the **existing common broker**. No
   new provider-specific broker, lifecycle plane, queue or scheduler.

This dependency is tracked in the capability matrix alongside the #7114 skill/profile integration and
the real realm/capacity producer. It is resolved only through the existing PF1 owner. A replacement
worker, a parallel carrier, or a native claim built on the compatible harness resolves nothing and
creates a second writer for one operation.

The adjacent unresolved question is identity: OCR-2C Family A already returned
`FAMILY_A_NO_SAFE_EQUALITY_WITNESS` and `FAMILY_A_NO_ROTATION_INVALIDATION`, so where a dedicated
native-auth principal comes from is open, and Family B remains a separate architecture gate.

## §3 Current fabric program state (2026-09-16T02:4xZ)

Operation `agent-fabric-end-to-end-fable-integration-20260913-sol-001`, protected Mastermind master
`7642aea155d2817219135b24246b55c1d7611c66`.

| Item | State at this reading |
|---|---|
| W1-H3 #677 | OPEN / DRAFT @ `2575c111210b1f6e51b4c900087a95331284b173`; repair round in progress for Sol R17 B1-B3 (operator ARM/DISARM surface; unloaded-control path must not start the worker; rollback must prove live control reloaded DISARMED). SAME child, worktree and writer. Principal critical path. |
| H0 | Prestage attempt 2 continues on the existing runner. Never kill, restart or duplicate the Mastermind carrier or the in-progress Macro clone. |
| #676 | OPEN / DRAFT @ `7e6a35b66e8ec42a3263fcb7c06379d68bbc474c`; FULL_REREVIEW_REQUIRED; maximum outcome APPROVE_AS_SPEC_ONLY. Passing review or CI proves no native worker, enrollment, telemetry, unattended permission or COO parity. |
| #7179 | @ `889174901bdaabba44a8f60f3179ff7bd32c8061`; R2 owed. DRAFT / HOLD. |
| #671 | REQUEST_CHANGES / HOLD @ `bf06ef8f2453b7592c4312d65f770292446ea141`; R2 B1/B2 live; SAME writer. |
| #7114 | @ `7f68d90d`; repaired but held. Do not poll; consume the next material hosted gate or review return. |
| #7116 | Write withheld. |
| #665 | PARKED. Do not manufacture a receipt store. |
| Family-B #662 / #7162 | B0 gate: needs independent B0 acceptance before B1 and beyond. |
| #675 / #667 | Protected. |

## §4 Not in scope — do not adopt

This record implements, reviews, approves, rebases, labels, readies, releases or merges no Mastermind
carrier; releases no writer; authorizes no provider, host, OAuth, broker, credential or runtime
operation; does not amend `mastermind.provider_capacity.v1`, the CF2-F source law, the Phase 1F-C
placement snapshot or the H0 runbook; does not widen the workstream into Wake, Slack dispatch, Control
Room, browser resources, merge/deploy authority or capital authority; and does not convert a records-only
edit, a green check, a merged slice or a fixture corpus into native capacity, placement proof or
production acceptance.
