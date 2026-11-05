---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/agentos-vps-fabric-records-20260918
model: fable
ended_because: complete
mission: >
  Records-only lane: write the durable company-memory records for one completed phase of the Agent
  Fabric program — the VPS economical-provider track ruled at the edges of Sol root
  `C0BSBM78V1N/1789324397.992989` — so a cold stranger can resume the two held verticals without the
  commissioning conversation. No source was changed, no PR was readied, merged or armed, no provider
  was called, no host was touched and no runtime action was taken.
state_before: >
  Nothing in `agentos/` mentioned this track: no record named the two DRAFT/HELD carriers, the
  executive-generation arming state, or the next gate. The workstream `next_action` still led with
  W1-H3 (Mastermind #677) and the 2026-09-16 protected-master pin `7642aea1`; the newest handoff was
  EXECUTIVE-CAPACITY-FABRIC-2026-09-17 (a PF1 native-worker boundary record). The single most
  consequential fact of the phase — that the Executive CEO provenance gate is schema-only — existed
  only inside a Mastermind PR body and the commissioning conversation, and would have died with them.
changed:
  - path: agentos/discoveries/DSC-EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY.md
    what: >
      New discovery record with both admission gates. Claim: the CEO branch of
      `_has_executive_provenance` (`control_plane/executive_runtime.py:928-942` at protected master
      `320f586126b7c82c843ef17612f12d40d20a42e0`) returns True on the schema string alone and discards
      the actor, while `control_plane/ceo_intent.submit_intent` (`ceo_intent.py:731-735`) stamps that
      schema on every admitted v1 intent regardless of actor — so `svc-site-maintenance` (owner_seat
      `coo`, READ/RESEARCH only) obtained a stamp that admits `owner_seat="ceo"`,
      `escalation_target="ceo"` and child Jobs, while `owner_seat="chairman"` is refused. Falsifier:
      `_has_executive_provenance({"schema": "mastermind.ceo_intent.v1", "actor":
      "svc-site-maintenance"}, target="ceo")` returning False on protected master. so_what: an
      actor-aware CEO branch (A2, owned by `executive_runtime.py`, colliding with open PR #699) is a
      security prerequisite before arming any non-CEO principal beyond READ/RESEARCH; A1's own restraint
      bounds the module, not the stamp; and `v2` is not the seam.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-18.md
    what: >
      This continuation record — the cold-stranger test for the VPS economical-provider track: both
      verticals with branch, head, draft/label/auto-merge state; the custody census (A2 and B collisions);
      the executive-generation arming state and next gate; the `do_not_redo` and `danger_areas` lists
      inherited from the Sol root; and the ordered next actions.
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Durable-state edit to the workstream `next_action` field ONLY, per the lane's owned-file scope: a
      new leading paragraph recording the two DRAFT/HELD carriers (Macro #7280 head `284bd893`, Mastermind
      #804 head `3b5182e2`) as awaiting an explicit Sol acceptance ruling, the A1 module's voluntary
      `NOT_YET_ADMITTED` posture, the A2/B custody collisions, the advanced protected-master pin
      `320f586126b7c82c843ef17612f12d40d20a42e0`, the installed-but-UNARMED executive generation
      `8b231e82`, and the HUMAN_AUTH/CREDENTIAL_READINESS gate. The only other bytes changed in that file
      are one tense correction inside the same field (the `7642aea1` pin is now labelled the 2026-09-16
      record-repair pin rather than the current one). `status` was deliberately left `active` and no wave
      row was rewritten: the holds are per-carrier and other waves (CF2-H0, PF1, OCR-2C) remain in
      flight. No `created`/`updated` field was authored and neither generated view
      (`docs/AGENT_OS_STATE.md`, `data/governance/agent_os_state.json`) was touched.
prs: [7280, 804]
discoveries:
  - DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY
verified:
  - claim: "Macro PR #7280 (vertical 1, production API usage modes) is OPEN, DRAFT, carries no labels and no auto-merge, on branch claude/provider-production-modes-20260918 at head 284bd893f5fb2085d597611d065017494f3275db."
    command: "gh pr view 7280 --repo mastermindx-market-intelligence/macro --json number,state,isDraft,headRefName,headRefOid,labels,autoMergeRequest"
    result: "{\"autoMergeRequest\":null,\"headRefName\":\"claude/provider-production-modes-20260918\",\"headRefOid\":\"284bd893f5fb2085d597611d065017494f3275db\",\"isDraft\":true,\"labels\":[],\"number\":7280,\"state\":\"OPEN\"}"
  - claim: "Mastermind PR #804 (vertical 2, tier A1 executive service principal) is OPEN, DRAFT, carries no labels and no auto-merge, on branch claude/executive-service-principal-20260918 at head 3b5182e2545cab671f2da2db6735b51c926baf18."
    command: "gh pr view 804 --repo mastermindx-market-intelligence/Mastermind --json number,state,isDraft,headRefName,headRefOid,labels,autoMergeRequest"
    result: "{\"autoMergeRequest\":null,\"headRefName\":\"claude/executive-service-principal-20260918\",\"headRefOid\":\"3b5182e2545cab671f2da2db6735b51c926baf18\",\"isDraft\":true,\"labels\":[],\"number\":804,\"state\":\"OPEN\"}"
  - claim: "The records in this lane are schema-valid across the whole store."
    command: "python3 scripts/agentos.py validate"
    result: "exit 0; see the record-return file for the captured output."
  - claim: "This lane changed agentos/ paths only and nothing outside the Agent OS knowledge plane."
    command: "git diff --name-only origin/main"
    result: "agentos/discoveries/DSC-EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY.md, agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-18.md, agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md."
  - claim: "The record carrier is a fresh branch off origin/main, not a reused squash-merged branch."
    command: "git fetch origin -q && git rev-list --left-right --count origin/main...HEAD && git ls-remote --heads origin claude/agentos-vps-fabric-records-20260918"
    result: "0	0 behind/ahead before the edit, and the remote branch did not exist (empty ls-remote), so this branch was minted for this lane."
  - claim: "This carrier is a SPARSE worktree, and the lane's writes stay inside agentos/, which is a checked-out top-level directory — so no omitted tree (data, mockups, site, verify_shots) could have been written or truncated."
    command: "python3 scripts/worktree_sparse.py status"
    result: "worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots. Every path in the `git diff --name-only origin/main` result above is under agentos/, so no opt-in (`python3 scripts/worktree_sparse.py full`) was needed and none was run."
unverified:
  - claim: "Vertical 1 carries 76 passing tests and two non-author review rounds (REQUEST_REPAIR, then repair, then APPROVE), and its `.github/ci/legacy-jobs.yml:6081` run-line edit was needed because the suite was the unique scripts/audit_unrun_tests.gated_unrun_suites() hit."
    what_would_verify: "On branch claude/provider-production-modes-20260918 at 284bd893: PYTHONPATH=. python3 -m pytest tests/test_provider_production_modes.py -q, plus python3 scripts/audit_unrun_tests.py and gh pr view 7280 --json reviews."
  - claim: "Vertical 2 carries 9 tests in tests/test_executive_service_principal.py with tests/test_ceo_intent.py (60) and the D8 scanner test green, and its module reports NOT_YET_ADMITTED because the sink refuses a typed schema, a provenance key and constraints.task_kind."
    what_would_verify: "In a Mastermind checkout at head 3b5182e2545cab671f2da2db6735b51c926baf18: python3 -m pytest tests/test_executive_service_principal.py tests/test_ceo_intent.py -q."
  - claim: "Executive generation 8b231e82 is installed but UNARMED/STOPPED (Sol option B), and the next gate is HUMAN_AUTH/CREDENTIAL_READINESS keyed on the Chairman CREDENTIAL_EXPIRES_AT."
    what_would_verify: "Read the Executive runtime's generation/arming surface on the host that holds it, and the Sol ledger entry that authorized option B."
  - claim: "Identifiers C088/C089/C090/C092 exist in NO repository — they are Sol ledger labels."
    what_would_verify: "git grep -n 'C088\\|C089\\|C090\\|C092' in each of macro, charting-app and Mastermind at their then-current default branches."
  - claim: "The provenance-gate reproduction was performed against protected master 320f586126b7c82c843ef17612f12d40d20a42e0."
    what_would_verify: "Run the falsifier command recorded in DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY at that pin and observe True; this records lane did not re-run it."
unresolved:
  - "The schema-only CEO gate is NOT fixed by PR #804: the defect is in executive_runtime.py, which that carrier does not own. A2 (actor-aware gate) is the fix and it collides with open PR #699 on the same file, so it is a coordination act with that PR's owner."
  - "Vertical B (OpenCode native Worker: new control_plane/opencode_worker.py plus one implementation= line in worker_adapter.py:63-68, keeping implemented=False) is NOT started: it collides with PR #762 and #590."
  - "Both verticals are DRAFT and HOLD: they may not be marked ready, merged, armed or auto-merged without an explicit Sol acceptance ruling on root C0BSBM78V1N/1789324397.992989. No ruling has been issued."
  - "The A1 module deliberately reports NOT_YET_ADMITTED, so tier A1 is source-complete but has no admitted production path; the sink still refuses a typed schema, a provenance key and constraints.task_kind."
  - "The Executive generation is installed and UNARMED/STOPPED; arming is gated on HUMAN_AUTH / CREDENTIAL_READINESS, which is a human credential act."
next_actions:
  - "Obtain the explicit Sol acceptance ruling on root C0BSBM78V1N/1789324397.992989 for BOTH held carriers (Macro #7280, Mastermind #804) before any ready/merge/auto-merge action on either."
  - "After (or in parallel with) that ruling: start A2, the actor-aware CEO branch in control_plane/executive_runtime.py, as a security prerequisite — coordinate with the owner of open PR #699 on that file first, and do not attempt it from the A1 carrier."
  - "Then start vertical B (OpenCode native Worker) with the owner of PR #762/#590; keep implemented=False until a separate arming decision."
  - "Re-read DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY and re-run its falsifier against the then-current protected master before trusting the A1 pause as sufficient."
  - "Touch the human credential gate (HUMAN_AUTH / CREDENTIAL_READINESS) only through the Chairman; it is not a session action."
do_not_redo:
  - "Never append MiniMax or GLM to capacity v1: engine/provider_capacity.py is a CLOSED 12-slot surface. This row carries no DNR:<KEY> citation on purpose — grep of research/DO_NOT_REBUILD.md at this carrier finds no capacity-v1 row, so the law is the closed 12-slot surface itself, not a kill-registry row."
  - "Never flip the #7103 plan flags."
  - "Never make brain/provider_waterfall.py an API ladder."
  - "Never fix the schema-only executive provenance gate from a non-owner PR — the A1 carrier could not close it by fence."
  - "Never ready, merge or auto-merge Macro #7280 or Mastermind #804 without an explicit Sol acceptance ruling on root C0BSBM78V1N/1789324397.992989."
  - "Never re-post PICKUP_ACK or START for this operation."
  - "Never treat this handoff as an arming decision: it records state, it authorizes nothing (knowledge plane, not control plane)."
danger_areas:
  - ".github/ci/legacy-jobs.yml — many concurrent writers; the vertical-1 edit is ONE run line at :6081 and must not be widened."
  - "engine/llm_auth.py — concurrent carriers #7179 and #7185."
  - "executive_runtime.py — the A2 slice shares this file with open PR #699; any edit collides."
  - "worker_adapter.py — the B slice shares this file with PR #762/#590, and its implementation= line must stay implemented=False."
  - "The two held carriers themselves: they are PUBLIC DRAFT PRs, and an accidental ready/arm/merge is an authority breach, not a CI mistake."
---

# VPS economical-provider track — where it stands, ranked by what a stranger needs

This lane is RECORDS ONLY. The two verticals below are DRAFT and HELD. The single most important
sentence in this record: **nothing in this track may be readied, merged, armed or auto-merged without an
explicit Sol acceptance ruling on root `C0BSBM78V1N/1789324397.992989`.** The holds are not CI states;
they are authority states.

## The operation

Sol root `C0BSBM78V1N/1789324397.992989`; operation
`agent-fabric-end-to-end-fable-integration-20260913-sol-001`; VPS economical-provider track ruled at
edges `1789694411.329219` and `1789694989.668909`; seat = Claude6 `5fae71cf` (Fable). The two edges are
the only rulings this lane rests on; the identifiers `C088`, `C089`, `C090` and `C092` that appear in
the Sol ledger exist in NO repository — they are ledger labels, not code symbols, and a grep that finds
nothing is the expected result, not a missing file.

## Vertical 1 — production API usage modes (Macro, PR #7280)

Macro PR #7280, branch `claude/provider-production-modes-20260918`, head
`284bd893f5fb2085d597611d065017494f3275db`, DRAFT with a HOLD-FOR-SOL body, no labels, native
auto-merge null (re-verified in this lane: OPEN, isDraft true, labels empty, autoMergeRequest null).
New files: `config/provider_production_modes.v1.json`, `engine/provider_production_modes.py`,
`tests/test_provider_production_modes.py`. Exactly ONE existing-file line changed:
`.github/ci/legacy-jobs.yml:6081`'s run line, appending the new path — needed because the suite was the
unique hit from `scripts/audit_unrun_tests.gated_unrun_suites()`, so a new test file with no run line
would have been an unrun suite rather than a passing one. A stranger resuming this vertical should
re-derive the test count and the review history themselves: this lane did not run them (see the
`unverified` list), it only pinned the carrier state.

## Vertical 2 — tier A1 executive service principal (Mastermind, PR #804)

Mastermind PR #804, branch `claude/executive-service-principal-20260918`, head
`3b5182e2545cab671f2da2db6735b51c926baf18`, DRAFT with a HOLD body (re-verified in this lane: OPEN,
isDraft true, labels empty, autoMergeRequest null). New files:
`control_plane/executive_service_principal.py`, `tests/test_executive_service_principal.py`, and
`docs/EXECUTIVE_SERVICE_PRINCIPAL_A1_2026-09-18.md`. The module reports `NOT_YET_ADMITTED` BY DESIGN: the
intent sink refuses a typed schema, a `provenance` key and `constraints.task_kind`, so there is no
admitted production path for tier A1 yet. That refusal is the module's posture, not a defect in it.

## What this phase actually learned

`DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY` is the load-bearing discovery, and it is why A1 must stay
a pause. The Executive CEO provenance gate reads the envelope's schema string and discards the actor, and
the sink stamps that schema on every admitted v1 intent regardless of actor — so a READ/RESEARCH-only
service principal can obtain a stamp that admits `owner_seat="ceo"` work. The A1 module never passes a
seat, which is why its own Jobs stay `coo`; the hole is stamp reuse by any later runtime holder, and it
is a security prerequisite for arming, not a stylistic gap.

## Custody census — what is blocked by what

| Slice | Owns | Collides with | State |
|---|---|---|---|
| A2 — actor-aware CEO gate | `executive_runtime.py` | open PR #699 | NOT STARTED; prerequisite for arming non-CEO principals |
| B — OpenCode native Worker | new `control_plane/opencode_worker.py` + one `implementation=` line at `worker_adapter.py:63-68` | PR #762 / #590 | NOT STARTED; must keep `implemented=False` |

## Arming state

Executive generation `8b231e82` is installed and UNARMED / STOPPED (Sol option B). The next gate is
HUMAN_AUTH / CREDENTIAL_READINESS, keyed on the Chairman's `CREDENTIAL_EXPIRES_AT`. Nothing in this lane
moved that gate, and nothing here authorizes moving it: it is a human credential act.

## The one thing a resuming session must not get wrong

Both verticals are held by AUTHORITY, not by CI. Re-running CI, rebasing, or clearing a red check on
either carrier does not release it. The release condition is a Sol acceptance ruling on the root named at
the top of this record.
