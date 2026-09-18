---
schema: mastermind.agent_os_w4_report_only_ship_capture_architecture.v1
operation_key: agentos-w4-report-only-capture-design-20260907-sol-001
workstream: WS:AGENT-OS
source_base: 20704f4b1bd1b133629325c25af756c5de03af94
protected_mastermind_procedure: d7ffac605c547da593bfa4b4ac2b45ccafd009d6
skillpack_schema: mastermind.sol_skillpack.v1
skillpack_version: 1.0.1
minimum_bootstrap_major: 1
capability_state: SPEC_ONLY
production_effect: NONE
architecture_family: AGENT_OS_W4 / REPORT_ONLY_SHIP_CAPTURE
---

# Agent OS W4 — report-only ship capture architecture

**Date:** 2026-09-07  
**Owner:** Sol, AI CEO  
**Chairman:** Chris  
**Status:** `SPEC_ONLY / RECORDS_ONLY / PRODUCTION_INERT`  
**Organizational parent:** `WS:AGENT-OS`  
**Product ruling:** prove a deterministic, read-only ship report before wiring any fleet hook or write helper.

This document freezes the corrected architecture for the authored Agent OS Phase 4 objective. It changes no hook, CLI, workstream, handoff, branch, pull request, runtime, provider, account, database, scheduler, queue, identity, transcript, or production state. It is not implementation authority.

---

## 1. Executive ruling

The original Phase 4 direction remains valuable: at the end of a bounded source wave, the operator should not have to remember which Agent OS workstream owns the changed paths, whether a current handoff exists, or which durable records may need attention.

The original implementation shape is no longer safe enough to build directly.

Current source shows that `.claude/hooks/ship_loop_guard.py` is a large, fleet-wide session-completion guard. It owns blocking behavior, GitHub/CI/hold reconciliation, any-code escape ceilings, worktree delegation, and Stop-event failure handling. An unexpected Stop-path error can itself be routed through a blocking `guard_error`. The current Claude settings wrap that guard with `scripts/ship_loop_hold_wrapper.py` and a long timeout. Agent OS architecture separately says session lifecycle stays with the ship-loop/CI machinery while Agent OS records organizational continuity.

Therefore W4 is decomposed:

```text
W4A — pure report generator                  FIRST / independently useful
W4B — optional nonblocking hook sidecar      HELD until W4A adoption and provider proof
W4C — explicit advisory claim/release writes HELD as a separate mutation family
```

The first vertical is **W4A: `agentos.ship_report.v1`**.

It deterministically reads an already-acquired local source snapshot and existing Agent OS records, then returns:

- which workstream or workstreams match the explicit identity, advisory branch note, and changed paths;
- which evidence caused the match;
- whether the result is resolved, ambiguous, unclaimed, terminal, or source-unavailable;
- whether a same-workstream handoff is present in the change set;
- whether the workstream or handoff appears to need review;
- one bounded list of recommended organizational follow-ups;
- exact uncertainty and non-effects.

It never edits Agent OS, never updates a claim, never creates a handoff, never blocks Stop, never calls GitHub, never opens a provider, and never asserts worker liveness.

---

## 2. Outcome and 10/10 end state

### 2.1 Primary persona

A bounded Claude, Codex, Fable, Sol, or mechanical source worker preparing to return a result or handoff.

### 2.2 User job

> Before I stop or return, tell me which existing Agent OS workstream this source change belongs to, whether my durable handoff is present, and exactly what organizational record needs attention—without mutating anything or becoming another ship gate.

### 2.3 Machine job

Given explicit, finite inputs, produce one closed, deterministic, correction-safe report that:

1. preserves canonical Agent OS identity and path semantics;
2. distinguishes routing evidence from live ownership;
3. represents ambiguity instead of choosing the most convenient workstream;
4. detects a matching handoff only through current changed-path and parsed-record evidence;
5. emits no source text, secret, absolute host path, transcript, private reasoning, or provider handle;
6. performs no write or network effect;
7. can later be invoked by a hook sidecar without inheriting hook authority.

### 2.4 Ten-second experience

A worker runs one command near a source-return boundary and gets one of these shapes:

```text
RESOLVED
WS:CHAIRMAN-CONTROL-ROOM
Evidence: explicit workstream + 3/3 changed paths matched owns_paths
Handoff: PRESENT_IN_CHANGESET
Next: include exact PR/head/check receipts in the handoff return
Effect: NONE
```

```text
AMBIGUOUS
WS:A and WS:B both match the same path set
Next: request owner adjudication; do not auto-edit either record
Effect: NONE
```

```text
UNCLAIMED
No current workstream owns these changed paths
Next: inspect existing programs/workstreams before minting anything
Effect: NONE
```

The report cannot say a worker is active, a branch is authoritative, a PR is merged, or work is complete unless the caller supplied a typed source fact and the output labels that source and observation time.

### 2.5 Completion proof

W4A is complete only when:

- a real active branch with a matching workstream produces a resolved report;
- a real branch with two overlapping workstreams produces ambiguity, not first-wins;
- a branch containing its correct handoff produces `PRESENT_IN_CHANGESET`;
- removing that handoff produces `MISSING_FROM_CHANGESET` without writing one;
- expired or missing `claim:` notes do not become liveness or lock evidence;
- malformed/unavailable Agent OS input yields a bounded typed result rather than an exception or silent success;
- repository and Agent OS bytes, Git index, branch, and external systems remain unchanged;
- the existing ship-loop guard and wrapper are byte-identical and their focused tests remain unchanged/green;
- the report is useful in a real source-return journey and an operator correctly follows its recommendation.

A schema, CLI flag, green unit test, merged PR, or hook registration is not W4A production acceptance by itself.

---

## 3. Current estate and capability ledger

| Capability | Current state | Evidence / meaning |
|---|---|---|
| Agent OS durable records | `PROVEN_LIVE` | canonical validator and context compiler consume workstreams, decisions, discoveries, and handoffs |
| Agent OS path collision detection | `PARTIAL` | current compiler/validator resolves authored `owns_paths` and uses repository-aware glob matching |
| Agent OS advisory `claim:` note | `PARTIAL` | parsed and displayed as an author note; explicitly not liveness or a gate |
| Ship-loop session guard | `PROVEN_LIVE` at its accepted generations | owns blocking session-completion behavior; not an Agent OS writer |
| Hold wrapper | `PROVEN_LIVE` at accepted generations | adapts ratified hold states; still blocks pending/red and delegates normal behavior |
| Phase 4 report-only capture | `NOT_BUILT` | no closed ship-report contract or pure producer exists |
| Phase 4 hook sidecar | `NOT_BUILT` | no separately proven nonblocking integration exists |
| Phase 4 claim/release helpers | `NOT_BUILT` | no accepted explicit mutation family exists |
| Automatic Agent OS record mutation from a hook | `REJECTED_BY_DESIGN` for W4A | would mix organizational writes with lifecycle enforcement before the read contract is proven |

### 3.1 Load-bearing source facts

- `.claude/settings.json` routes SessionStart and Stop through the existing completion guard/wrapper.
- `ship_loop_guard.py` delegates across worktrees of the same clone and owns SessionStart/Stop behavior.
- an unexpected Stop exception may emit or persist a blocking `guard_error`.
- `ship_loop_hold_wrapper.py` performs Git/GitHub/CI reads and can block or park a ratified hold.
- `scripts/agentos.py compile-context` is explicitly pure read, never writes, and uses repository-aware path semantics.
- Agent OS `claim:` is explicitly advisory and proves no current worker activity.
- the original Phase 4 plan required report-only behavior and a no-block test, but also bundled automatic updates and claim/release helpers into one risky wave.

These facts justify decomposition. They do not authorize implementation.

---

## 4. Approaches considered

### 4.1 Approved — pure report generator, hook and writes deferred

Add one isolated deterministic core plus a thin CLI adapter. The core receives parsed records and typed source facts. It returns a closed report and has no I/O. The adapter may read local Git and the existing Agent OS store through current helpers; it performs no network and no write.

Benefits:

- independently useful before hook integration;
- easiest no-effect proof;
- can be called manually, by tests, by a future sidecar, or by another orchestrator;
- failures cannot block a session when invoked outside the guard;
- separates organizational guidance from lifecycle authority;
- gives W4B a stable consumer contract rather than coupling it to internal guard state.

Cost:

- operators must invoke it manually until W4B is separately accepted;
- W4C writes remain explicit and later.

### 4.2 Rejected for first vertical — edit `ship_loop_guard.py` directly

This would place new Agent OS parsing, path mapping, record-currentness logic, and output behavior inside the largest fleet-wide blocking hook. A defect could prevent Stop or alter established merge/CI/hold semantics. It would also make report adoption impossible to distinguish from lifecycle enforcement.

The direct guard path may be reconsidered only if a later source study proves there is no safer sidecar seam. That decision is outside W4A.

### 4.3 Rejected — build claim/release helpers first

Claim/release commands are mutations. They do not by themselves tell the operator whether the current branch maps uniquely to a workstream, whether a handoff is present, or which evidence is missing. Starting with writes would create a tool that can change records before the system can explain what should change.

### 4.4 Rejected — auto-generate or auto-commit handoffs

A template can help a human, but a hook cannot truthfully author mission, state-before, verified/unverified facts, unresolved work, next actions, do-not-redo boundaries, or danger areas. Automatic prose would be low-quality organizational memory and could turn transient tool output into durable authority.

---

## 5. Canonical ownership and no-rebuild boundary

| Concern | Canonical owner | W4A behavior |
|---|---|---|
| Job / Attempt / Worker / Event lifecycle | Executive OS | no mutation or inference |
| session Stop / merge / CI / hold enforcement | ship-loop guard, wrapper, CI owners | read-only boundary; no import or call from pure core |
| workstreams, decisions, discoveries, handoffs | Agent OS | parse/reference only; no write |
| implementation and checks | GitHub | caller-supplied or local evidence only; no network |
| portfolio projection | Linear | out of scope |
| delivery / ACK / START / RESULT / STOP | Slack/Agent Relay + Executive OS as applicable | out of scope; no inference from records |
| branch/head/diff | local Git | thin adapter read only |
| workstream path claims | Agent OS `owns_paths` | reuse existing repository-aware semantics |
| `claim:` | Agent OS author note | routing evidence only; never lock/liveness |
| handoff quality | source author + review | W4A reports presence/gaps; never writes prose |

Hard prohibitions:

- no second lifecycle, hook registry, queue, watcher, retry, lease, identity, auth, transcript, event, or state plane;
- no network or GitHub API call from W4A;
- no subprocess from the pure core;
- no write to Agent OS, Git, worktree, index, environment, or external service;
- no worker-presence inference from process, tab, branch, claim, or handoff;
- no automatic workstream minting;
- no automatic decision, discovery, handoff, status, next-action, `prs`, or `claim` update;
- no severity/priority invention;
- no model call or model-authored ownership;
- no raw diff, source file contents, transcript, private reasoning, credentials, absolute paths, environment values, or arbitrary mappings in output.

---

## 6. Wave decomposition

### W4A — report-only ship capture

One pure report contract, one thin local adapter, tests, and one real branch proof.

**Capability ceiling after source merge:** `BUILT_NOT_PROVEN`.  
**Capability ceiling after accepted real invocation:** `PARTIAL` for the wider Phase 4 objective.

### W4B — optional nonblocking hook sidecar

Held until W4A is accepted and used manually. A separate design must prove:

- the exact provider hook invocation order and failure semantics;
- that sidecar absence, timeout, invalid JSON, exception, or oversized output can never block Stop or modify the canonical guard result;
- one invocation per relevant boundary, with no polling/daemon;
- no duplicate Git or Agent OS read when the guard already supplies a safe typed snapshot;
- byte-identical guard/wrapper behavior outside the sidecar receipt;
- a kill switch and rollback that do not alter canonical state.

W4B may display or persist an ephemeral report receipt only through an already accepted evidence owner. It may not mutate Agent OS.

### W4C — explicit advisory claim/release writes

Held as a separate mutation family. It requires explicit user/worker intent, exact workstream identity, idempotency, current record SHA, collision check, safe atomic file update, validation, review, and correction behavior. It remains advisory and cannot prove liveness, acquire a lease, or block another worker.

---

## 7. W4A input architecture

### 7.1 Pure core entry point

The implementation plan should preserve this semantic shape while adapting names to existing code:

```python
def compose_ship_report(
    *,
    repository: str,
    repository_sha: str | None,
    branch: str | None,
    base_sha: str | None,
    changed_paths: Sequence[str],
    explicit_workstream: str | None,
    workstreams: Sequence[Mapping[str, Any]],
    handoffs: Sequence[Mapping[str, Any]],
    pull_request: Mapping[str, Any] | None,
    observed_at: str | None,
) -> dict[str, Any]:
    """Pure deterministic Agent OS ship report; no I/O and no mutation."""
```

The core does not read files, call Git, call GitHub, sample a clock, inspect processes, or modify caller-owned values.

### 7.2 Thin adapter

The first adapter may be an additive `agentos.py ship-report` command, but the implementation plan must re-read current source before fixing the exact placement. It may:

- read local HEAD, branch, merge base, and changed path names through the existing Git helper;
- load the existing Agent OS store through the current parser;
- accept an explicit `--workstream` and `--pr`/typed PR evidence;
- accept an explicit `--base` or derive one from an existing local ref;
- accept `--now` for deterministic tests and output metadata;
- render JSON or a fixed text view.

It may not:

- call GitHub or another network service;
- inspect source file contents or raw diffs;
- stage, commit, push, create a branch/PR, or edit Agent OS;
- call the ship-loop guard or wrapper;
- read browser/provider/session/process state;
- use an LLM to resolve a workstream.

### 7.3 Input bounds

- repository: closed known repository key or safe literal, max 128 characters;
- branch: null or safe UTF-8 display string, max 255 characters, control characters refused;
- SHA: null or 40 lowercase hexadecimal characters;
- changed paths: 0–1,024 unique repository-relative paths, each max 512 bytes;
- workstreams: bounded by the current validated Agent OS store;
- handoffs: bounded by the current validated store;
- PR evidence: closed allowlist only;
- no absolute paths, `..` traversal, NUL, control characters, URLs, or arbitrary nested fields.

A bound violation yields a typed `INPUT_REFUSED` report or a static CLI error. It never produces partial output from an unbounded input.

---

## 8. Closed output contract

Target schema:

```text
agentos.ship_report.v1
```

Closed top-level shape:

```json
{
  "schema": "agentos.ship_report.v1",
  "generated_at": "2026-09-07T00:00:00Z",
  "source": {
    "repository": "macro",
    "repository_sha": "0123456789012345678901234567890123456789",
    "base_sha": "abcdefabcdefabcdefabcdefabcdefabcdefabcd",
    "branch": "claude/example",
    "pull_request": null,
    "changed_path_count": 3
  },
  "resolution": {
    "state": "RESOLVED",
    "workstream": "WS:EXAMPLE",
    "candidates": [],
    "reason_codes": []
  },
  "handoff": {
    "state": "PRESENT_IN_CHANGESET",
    "path": "agentos/handoffs/EXAMPLE-2026-09-07.md",
    "record_date": "2026-09-07",
    "reason_codes": []
  },
  "record_review": {
    "workstream_path": "agentos/workstreams/WS-EXAMPLE.md",
    "workstream_changed": false,
    "current_pr_recorded": null,
    "claim": {
      "state": "ABSENT",
      "by": null,
      "branch_match": null,
      "expires": null,
      "liveness_asserted": false
    }
  },
  "recommendations": [
    {
      "code": "HANDOFF_PRESENT_REVIEW_RECEIPTS",
      "target": "agentos/handoffs/EXAMPLE-2026-09-07.md",
      "reason": "A matching handoff is in the change set; verify its exact evidence before return."
    }
  ],
  "degraded": [],
  "non_effects": [
    "NO_AGENT_OS_WRITE",
    "NO_GIT_WRITE",
    "NO_NETWORK",
    "NO_LIFECYCLE_EFFECT",
    "NO_LIVENESS_INFERENCE"
  ]
}
```

### 8.1 Resolution states

```text
RESOLVED
AMBIGUOUS
UNCLAIMED
TERMINAL_WORKSTREAM
SOURCE_UNAVAILABLE
INPUT_REFUSED
```

### 8.2 Candidate evidence kinds

```text
EXPLICIT_WORKSTREAM
EXACT_ADVISORY_BRANCH_NOTE
OWNS_PATH_MATCH
HANDOFF_IN_CHANGESET
```

Each candidate carries only:

```text
workstream
status
matched_path_count
changed_path_count
match_kinds[]
matched_patterns[]
matched_paths[]
claim_state
```

No candidate row says `active_worker`, `locked`, `leased`, `owned_now`, or equivalent.

### 8.3 Handoff states

```text
PRESENT_IN_CHANGESET
MULTIPLE_IN_CHANGESET
MISSING_FROM_CHANGESET
DATED_RECORD_PRESENT_OUTSIDE_CHANGESET
NO_WORKSTREAM
SOURCE_UNAVAILABLE
```

A handoff is `PRESENT_IN_CHANGESET` only when:

- its file path is in the changed-path set;
- it parses as a valid handoff;
- its `workstream` exactly equals the resolved workstream;
- its filename ends in a parseable `YYYY-MM-DD` date before `.md`;
- exactly one such row exists.

The report does not declare handoff prose correct merely because the file parses.

### 8.4 Recommendation codes

Closed first-generation codes:

```text
NO_AGENT_OS_CHANGE_REQUIRED
WORKSTREAM_AMBIGUOUS_REQUEST_ADJUDICATION
WORKSTREAM_UNCLAIMED_INSPECT_EXISTING_RECORDS
TERMINAL_WORKSTREAM_REQUEST_CONTINUATION_RULING
HANDOFF_MISSING_CREATE_OR_UPDATE_BEFORE_RETURN
HANDOFF_MULTIPLE_RECONCILE
HANDOFF_PRESENT_REVIEW_RECEIPTS
WORKSTREAM_RECORD_REVIEW_CANDIDATE
CLAIM_NOTE_ABSENT_INFORMATIONAL
CLAIM_NOTE_EXPIRED_INFORMATIONAL
CLAIM_BRANCH_MISMATCH_INFORMATIONAL
PR_EVIDENCE_NOT_SUPPLIED
SOURCE_UNAVAILABLE_REPAIR_READ_PATH
INPUT_REFUSED_REDUCE_SCOPE
```

Recommendations are explanatory, not commands with execution authority.

### 8.5 Output bound

Canonical UTF-8 JSON is measured before output. Maximum successful output is 65,536 bytes. Overflow returns a static bounded error report with `REPORT_TOO_LARGE`; it never truncates candidates or leaks the rejected value.

---

## 9. Deterministic resolution law

Evaluate in order.

### 9.1 Validate source and inputs

- require a validated Agent OS store snapshot;
- normalize `WS:KEY`, `WS-KEY`, and `KEY` through the existing key law;
- normalize repository-relative paths without resolving the host filesystem;
- deduplicate changed paths in stable lexical order;
- retain the source repository identity for every path match.

### 9.2 Explicit identity

If `explicit_workstream` names one existing record, it is the target candidate. Changed-path and claim evidence still appear and may create a disagreement. An explicit identity does not hide that another workstream also claims the paths.

If the explicit identity is malformed or absent from the store, return `INPUT_REFUSED` or `SOURCE_UNAVAILABLE` as appropriate; do not fuzzy-match.

### 9.3 Advisory branch note

An exact `claim.branch == branch` match is routing evidence only.

- current unexpired note: `EXACT_ADVISORY_BRANCH_NOTE`;
- expired note: candidate evidence plus `CLAIM_NOTE_EXPIRED_INFORMATIONAL`;
- missing `by`/`expires`/branch shape: malformed source, not liveness;
- multiple exact notes: ambiguity unless explicit workstream plus non-conflicting path evidence closes it.

The report never interprets process presence, recent commit time, branch existence, or an unexpired claim as a live worker.

### 9.4 Path ownership

Reuse the existing Agent OS repository-aware `owns_paths` resolution and glob semantics. Do not invent a second matcher.

For each workstream, record exact matched paths and authored patterns.

Resolution:

1. one candidate covers every changed path and no other candidate overlaps any changed path -> `RESOLVED`;
2. explicit workstream plus all changed paths are covered by it and every other overlap is disclosed as non-equal/non-conflicting -> `RESOLVED` with reasons;
3. two or more candidates cover the same changed path, or different candidates split the changed set without an explicit accepted target -> `AMBIGUOUS`;
4. no candidate matches -> `UNCLAIMED`;
5. resolved record is completed, superseded, or abandoned -> `TERMINAL_WORKSTREAM` unless an explicit current continuation decision is in the supplied records.

Do not choose by newest update time, shortest key, first file order, title similarity, number of PRs, authority class, or model confidence.

### 9.5 Handoff detection

Only inspect parsed handoff metadata and path identity. Do not scan handoff prose for magic words.

The latest historical handoff may be shown for orientation, but W4A never calls it current solely because its date is newest. Current return coverage comes from a matching handoff in the change set plus later human/reviewer validation.

### 9.6 Workstream review candidate

The report may recommend reviewing the workstream record when one or more source facts are supplied and differ:

- current PR is not listed in `prs`;
- changed paths fall outside authored `owns_paths`;
- the resolved workstream is terminal;
- explicit identity conflicts with path ownership;
- the changed set includes a new accepted capability/decision/handoff and the workstream is not in the change set.

It does not propose exact status, next-action, wave, PR, or claim mutations. Those require source-author judgment.

---

## 10. Time, null, conflict, and correction behavior

### Time

- `generated_at` is supplied by the adapter or null; the core never samples a clock.
- claim expiry uses the supplied observation time and the existing date grammar.
- Git commit time, file mtime, branch age, and handoff date never prove liveness or acceptance.
- PR/check/deployment times remain separate typed evidence when supplied.

### Null

- null branch means unavailable, not detached or main;
- null PR means not supplied, not no PR;
- null claim means absent/unavailable, not unclaimed worker;
- null handoff path means none established under the current resolution, not proof no handoff exists;
- null SHA means unavailable and degrades evidence.

### Conflict

Conflicts are first-class:

- explicit workstream versus path owner;
- two `owns_paths` owners for one changed path;
- two handoffs for the same resolved workstream in one change set;
- terminal workstream with active-looking branch note;
- PR evidence repository/head mismatch;
- changed path from an unknown repository.

No conflict is majority-voted or resolved by recency.

### Correction

The report is disposable. New source facts produce a new report. It stores no state and supersedes nothing. Durable correction remains an explicit Agent OS record edit reviewed through GitHub.

---

## 11. Error handling and nonblocking law

W4A has two layers:

1. pure core returns typed domain states and never raises for malformed source rows;
2. CLI adapter may return a static error for invalid invocation, unavailable repository, or internal serialization failure.

The manual CLI should use exit codes only for shell/operator ergonomics. A future hook sidecar must translate every W4A absence, timeout, nonzero exit, exception, malformed payload, and output overflow into a nonblocking observational receipt. It may never change the ship-loop decision.

No W4A code imports or calls:

```text
ship_loop_guard
ship_loop_hold_wrapper
GitHub clients
Slack/Linear/Executive OS clients
provider adapters
subprocess/network/filesystem APIs from the pure core
Agent OS write helpers
```

The thin adapter may use only the existing bounded local Git/store read seams frozen by the implementation plan.

---

## 12. Security and privacy

Default output may contain:

- known repository key;
- repository-relative changed paths;
- workstream keys/status;
- authored `owns_paths` patterns;
- safe branch display value;
- exact SHA/PR number when supplied;
- handoff/workstream repository-relative paths;
- closed reason and recommendation codes.

It must never contain:

- absolute host paths;
- environment variables;
- credentials, tokens, cookies, auth headers, secrets;
- raw file/diff contents;
- arbitrary URLs;
- Slack messages, transcripts, prompts, private reasoning;
- provider/session/browser/process identifiers;
- raw exceptions/tracebacks;
- unbounded source mappings;
- Git remote URLs carrying credentials.

Unsafe display strings are replaced by static reason codes. The output never says which secret detector matched.

---

## 13. Failure-state matrix

| Input/state | Required report | Prohibited behavior |
|---|---|---|
| no Agent OS directory/store | `SOURCE_UNAVAILABLE` | create store or workstream |
| invalid Agent OS records | bounded degraded result | silently skip hard invalid owner |
| no changed paths | `UNCLAIMED` or explicit-target orientation | invent source work |
| explicit valid workstream, no path match | conflict/review candidate | pretend path ownership agrees |
| one exact owner | `RESOLVED` | infer live worker |
| overlapping owners | `AMBIGUOUS` | first-wins |
| split changed set across owners | `AMBIGUOUS` | choose majority |
| expired branch claim | informational expiry | call worker absent/dead |
| unexpired branch claim | routing evidence | call worker active/live |
| terminal workstream | `TERMINAL_WORKSTREAM` | reopen automatically |
| handoff absent | `MISSING_FROM_CHANGESET` | write template automatically |
| two matching handoffs | `MULTIPLE_IN_CHANGESET` | choose newest silently |
| PR evidence absent | null + `PR_EVIDENCE_NOT_SUPPLIED` | call no PR |
| head mismatch | conflict | trust title/branch |
| malformed path or overflow | `INPUT_REFUSED` | partial/truncated output |
| pure-core exception | test failure | hide error as no issue |
| future sidecar failure | nonblocking receipt | block Stop |

---

## 14. First implementation slice

### W4A-1 — pure report plus manual CLI

Expected implementation path ceiling, subject to fresh collision census and accepted implementation plan:

```text
engine/agentos_ship_report.py
scripts/agentos.py
tests/test_agentos_ship_report.py
agentos/handoffs/AGENT-OS-W4A-IMPLEMENTATION-2026-09-07.md
agentos/workstreams/WS-AGENT-OS.md
```

The exact plan may narrow this set. A sixth path requires a decision request. `.claude/hooks/ship_loop_guard.py`, `scripts/ship_loop_hold_wrapper.py`, `.claude/settings.json`, and existing hook tests are read-only regression owners.

### Why one workstream update is reserved

An accepted implementation should record W4A's real capability and next action in `WS:AGENT-OS`. That record update occurs only after implementation evidence exists; it is not part of this architecture PR and cannot pre-claim completion.

### Non-goals

- no hook registration;
- no auto-run at Stop;
- no handoff generation;
- no workstream/decision/discovery mutation from the command;
- no claim/release command;
- no GitHub or external integration;
- no default blocking exit;
- no C1 Context Index change;
- no current Agent OS continuation PR takeover;
- no plugin handoff PR change.

---

## 15. Test architecture

### Pure unit tests

- closed keys and vocabularies;
- deterministic serialization under input reorder;
- caller input not mutated;
- explicit exact workstream;
- exact advisory branch note current/expired/malformed;
- one full path owner;
- overlapping owner ambiguity;
- split changed-set ambiguity;
- repository-qualified path separation;
- glob metacharacter and traversal refusal;
- terminal/superseded workstream;
- matching handoff present/missing/multiple;
- PR/head evidence null/match/conflict;
- output bound and multibyte count;
- malicious strings and forbidden fields;
- no model/clock/network/subprocess/filesystem import in pure core.

### Adapter tests

- local branch/head/base/changed paths read through existing helper;
- explicit detached/unborn/no-upstream states remain typed;
- no network call;
- no Git/Agent OS write;
- JSON and text views agree on semantic fields;
- missing store and invalid records degrade honestly;
- `--now` makes output reproducible;
- 0–1,024 changed-path bounds;
- internal error emits static bounded failure.

### Regression tests

- guard, wrapper, settings, and their tests remain byte-identical;
- current Agent OS validation remains at zero new hard errors;
- compile-context output unaffected;
- current collision/source-law tests remain green;
- command never appears as a ship-loop enforcement dependency.

### Mutation tests

The test suite must fail when:

- first matching workstream wins an overlap;
- an unexpired claim becomes `worker_active=true`;
- missing handoff triggers a write;
- branch recency resolves ambiguity;
- raw diff/file contents enter output;
- absolute paths or secrets enter output;
- output truncates instead of refusing;
- core reads a clock/network/subprocess/filesystem;
- terminal workstream is treated as active;
- PR absence becomes `pull_request=false`;
- hook/guard files are edited in W4A.

### Real-path proof

Run W4A against at least:

1. one active branch whose paths uniquely map to one workstream and contain a matching handoff;
2. one held/review branch with no handoff in its change set;
3. one synthetic/fixture overlap that produces ambiguity;
4. one unclaimed path set;
5. one expired advisory claim.

Record before/after Git status, index tree, Agent OS aggregate digest, no-network fence, output digest, and operator interpretation.

---

## 16. Acceptance matrix

### Product usefulness

1. operator can identify the likely workstream in under ten seconds;
2. handoff presence/gap is explicit;
3. next organizational review is clear;
4. ambiguity produces an actionable stop rather than generic warning;
5. output is readable in JSON and fixed text.

### Truth

6. `claim:` is advisory only;
7. branch/process/file time does not prove liveness;
8. path ownership uses existing repository-aware semantics;
9. PR/check/deployment/acceptance stay separate;
10. missing is distinct from false/none;
11. terminal workstreams are not reopened;
12. no model chooses identity.

### Safety

13. pure core performs no I/O;
14. adapter performs no write or network;
15. output is bounded and allowlisted;
16. malicious source strings cannot leak secrets/paths/private material;
17. exceptions cannot become Stop blocks;
18. guard/wrapper/settings bytes are unchanged;
19. no new daemon, poller, cache, database, queue, or state file exists.

### Proof

20. focused and repository-required tests pass on exact source head;
21. independent adversarial review accepts the exact head;
22. real branch proof shows useful output and zero effects;
23. source release is current-base qualified;
24. workstream/handoff records reflect only evidenced capability;
25. W4B and W4C remain held.

---

## 17. W4B admission gate

A later hook-sidecar design may begin only after all are true:

1. W4A source is protected;
2. one real manual invocation is accepted;
3. operators demonstrate that the report changes return behavior usefully;
4. exact Claude/provider hook semantics are proven with executable fixtures, not memory;
5. a sidecar failure cannot affect the canonical guard decision or exit;
6. settings/hook path collisions are clean;
7. one explicit rollback removes only the sidecar;
8. source/output rate is bounded and no recurring watcher/daemon is introduced;
9. Sol accepts the user-visible/noise ruler.

Until then, no `.claude/settings.json` or hook path is authorized.

---

## 18. W4C admission gate

Claim/release or record-update helpers require a separate design because they mutate durable organizational truth.

At minimum:

- explicit action and target workstream;
- exact current file SHA;
- caller identity and authority;
- branch/PR/worktree/effect reconciliation;
- idempotency and compare-and-set behavior;
- schema validation before write;
- append/supersession semantics where applicable;
- no liveness/lease meaning;
- review and rollback;
- `EFFECT_UNKNOWN` handling without retry.

No W4A recommendation code grants W4C permission.

---

## 19. Architecture freeze

Once protected:

1. W4 begins with a pure report, not a hook write.
2. `agentos.ship_report.v1` is disposable derived context, never canonical truth.
3. W4A performs no Agent OS/Git/network/external write.
4. W4A cannot block or modify the ship-loop decision.
5. the pure core has no I/O or clock.
6. the adapter reuses existing local Git/store read seams.
7. existing repository-aware `owns_paths` semantics are reused.
8. explicit workstream identity outranks convenience but does not hide conflicts.
9. `claim:` is routing evidence only and never proves a live worker.
10. overlapping or split ownership is `AMBIGUOUS`, never first-wins or majority-wins.
11. handoff presence is established from parsed metadata plus changed-path identity, not prose scanning.
12. missing handoff yields a recommendation, never automatic generation.
13. output is closed, bounded, privacy-safe, and correction-safe.
14. PR/check/deployment/proof/acceptance remain distinct.
15. `.claude/hooks/ship_loop_guard.py`, `ship_loop_hold_wrapper.py`, and `.claude/settings.json` are read-only in W4A.
16. W4B hook integration is separately designed and proven nonblocking.
17. W4C writes are separately designed, explicit, idempotent, and advisory.
18. no duplicate lifecycle, watcher, queue, cache, state, identity, auth, transcript, retry, or plugin plane is created.
19. implementation starts only after this architecture and a current implementation plan are independently accepted.
20. production acceptance requires a real source-return journey, not schema or CI alone.

---

## 20. Exact next action

1. independently review this architecture and companion decision against current source;
2. after protection, re-pin Macro main and the current Mastermind Skillpack;
3. perform a fresh collision census for the five proposed W4A implementation paths;
4. write an exact test-driven implementation plan;
5. admit one bounded writer—prefer Sonnet/Terra, not Fable—because product ambiguity is then frozen;
6. implement W4A only;
7. prove the manual real-path journey and zero effects;
8. update `WS:AGENT-OS` only with accepted evidence;
9. separately decide whether W4B is worth the fleet risk;
10. keep W4C held until an explicit mutation design exists.

Until those gates pass:

```text
W4A=SPEC_ONLY
W4B=NOT_BUILT / HELD
W4C=NOT_BUILT / HELD
production_effect=NONE
```
