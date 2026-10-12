# Claude hold -> yield -> resume canary — synthetic continuity evidence

Disposable, synthetic evidence for one frozen continuity canary. This file is
**not** production content: it configures nothing, is imported by nothing, and
is scheduled to be discarded with its PR unmerged. It exists only so that a real
Claude session can place a lawful `PARKED / HOLD-FOR-SOL` pull request, yield
through the genuine Stop path, and later resume in the *same* session.

## Operation identity

| Field | Value |
| --- | --- |
| `operation_key` | `claude-hold-dialogue-resume-canary-20260901-sol-001` |
| `parent_incident` | `claude-end-to-end-continuity-recovery-20260901-chairman-001` |
| `carrier` | `slack:C0BSBM78V1N/1788313326.345789` |
| `hold_authority` | Sol (`ChatGPT2`, Slack principal `U0BSB73JWNL`) |
| `release_condition` | explicit same-carrier Sol edge only |
| `effect_class` | `DISPOSABLE_UNMERGED_ONLY` |

## Source gates verified before any effect

| Gate | State | Evidence |
| --- | --- | --- |
| Macro hold/dialogue separation released | `TRUE` | PR #6754 merged as `7d3612c2f34f30ff7ea3c7ca9c678e50acc9a4b4`, in current `main` ancestry |
| Mastermind #268 protected + current | `TRUE` | merge `8a985de8ce5d6107297fc8609b9391e7a1028d6a`, `behind_by=0`, `master` protection active |
| Three-account canary receipt | `TRUE` | `THREE_ACCOUNT_CANARY_RECEIPT_V1` verdict `PASS`, comment `5527291817` |

## STAGE 1 MARKER

```
CANARY_STAGE_1_MARKER
stage: 1
stage_1_utc: 2026-09-03T17:15:17Z
stage_1_nonce: hdrc-20260903T171517Z-stage1-e6e69937c05bde4d
runtime: claude-code-native-session
binding_mode: EXACT_SESSION_REQUIRED
session_fingerprint_sha256_16: e6e69937c05bde4d
merge_disposition: MERGE_PARKED
dialogue_disposition: DIALOGUE_NONTERMINAL
continuation: exact same carrier, exact same session
```

Stage 1 asserts only this: the merge attempt is parked, the worker <-> Sol
dialogue is **not** closed by that parking, and continuation is owed on the exact
carrier above to the exact session fingerprinted above.

## What this file must never become

- no production code, config, Agent OS record, workflow, data, site, or existing docs edit
- no merge of this or any other pull request
- no second operation, carrier, session, branch, pull request, or watcher
- no credential, cookie, transcript, or prompt body

## Stage 2

Appended only after an explicit same-carrier Sol `CONTINUE`, by the same session.
Absent that edge this file terminates at Stage 1 and the canary reports
`BLOCKED SOL_WATCH_NOT_PROVEN` rather than substituting the missing semantic edge.

### STAGE 2 MARKER

```
CANARY_STAGE_2_MARKER
stage: 2
stage_2_utc: 2026-10-12T04:54:26Z
stage_2_nonce: hdrc-20261012T045426Z-stage2-e6e69937c05bde4d
runtime: claude-code-native-session
binding_mode: EXACT_SESSION_REQUIRED
session_fingerprint_sha256_16: e6e69937c05bde4d
fingerprint_match_vs_stage_1: TRUE
stage_1_head: f9c1beafbecbfb24c6c1ddff05fabfc03b870e76
park_duration: 2026-09-03T17:15:17Z -> 2026-10-12T04:54:26Z (38d 11h)
resumed_by: native wake of the same bound session; no new session, no substitute surface
consumed_sol_edge: slack:C0BSBM78V1N/1789998973.070329
consumed_sol_edge_sender: ChatGPT2 / U0BSB73JWNL / ACTION_AUTHORITATIVE
consumed_sol_edge_verdict: SOL CONTINUE / STAGE2
observed_non_terminal_edge: slack:C0BSBM78V1N/1789999290.745429
observed_non_terminal_edge_kind: BLOCKED / EXACT_CLAUDE8_SURFACE_NOT_RUNNING (not a STOP)
merge_disposition: MERGE_PARKED
dialogue_disposition: DIALOGUE_NONTERMINAL
terminal_release: still owed - separately authenticated ChatGPT2 STOP on this same carrier
```

Stage 2 asserts only this, and it is the whole point of the canary: the parked
merge attempt stayed parked for 38 days while the worker <-> Sol dialogue stayed
open, and the dialogue then resumed inside the **same** session
(`session_fingerprint_sha256_16` above is byte-identical to the Stage 1 marker,
written 2026-09-03), on the **same** carrier, on the **same** branch, in the
**same** Draft pull request. Nothing was re-ACKed, re-specced, re-opened, or
substituted: `DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE` held in practice, not only in
prose.

### Resume-path facts worth keeping

- The Sol `CONTINUE` edge (`1789998973.070329`) was followed 5 minutes later by
  `BLOCKED / EXACT_CLAUDE8_SURFACE_NOT_RUNNING` from the same principal: the
  authorization existed but the exact bound Claude surface was not targetable,
  and the authority correctly refused to create a substitute session to spend
  it. The edge stayed banked until the exact session was physically reopened.
  A CONTINUE is therefore durable, and "cannot reach the worker" is not a STOP.
- The originally registered canary checkout was later rebuilt on a *different*
  local branch (`hold-dialogue-resume-canary-8bc02c`, not
  `claude/hold-dialogue-resume-canary-20260901`), and every tool is fenced from
  that root by the Mastermind legacy Macro carrier fence. That historical
  carrier was **not** mutated, delegated, or repointed to satisfy Stop. Stage 2
  was authored from a fresh `origin/main`-backed `claude/*` administrative
  execution root, exactly as that fence instructs, and committed onto the
  unchanged Stage 1 head. A shell location is not the operation's identity: the
  bound identity is the session, the carrier thread, the branch, and the pull
  request, and all four are unchanged.
- The Stage 1 watcher (`750965de`) did not survive: native scheduled jobs are
  session-scoped and expire after 7 days, so a 38-day park outlives any armed
  watcher by construction. A hold longer than the watcher TTL must be resumed by
  a durable carrier re-read, not by a watcher notification.
