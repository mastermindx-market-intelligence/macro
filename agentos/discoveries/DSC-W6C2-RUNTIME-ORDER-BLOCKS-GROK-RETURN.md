---
key: W6C2-RUNTIME-ORDER-BLOCKS-GROK-RETURN
claim: >
  Mastermind PR #615 exact head 97634130d4bd69c3592502b2bb0e71829c55405c
  closes the four narrow receipt-order defects from its prior head but remains unsafe
  as the canonical consultation return owner. It breaks protected v1 grammar/fingerprints,
  cannot traverse the real managed-Codex attention adapter, records consultation-local
  dispatch/native facts without an exact Wake/provider causal join, has contradictory
  EFFECT_UNKNOWN reducers, and permits foreign or changed answers to receive/consume credit.
falsifier: >
  A newer immutable #615 head must preserve protected v1 exact frames and fingerprints or
  introduce an explicit new schema version; compose through the real Wake/current-writer
  path with a stable persisted nudge identity; derive one coherent effect state from the
  canonical Wake/provider history; bind answer availability and requester consumption to
  the stored request and exact available fingerprint/digest; use canonical RuntimeBinding
  evidence; atomically enforce answer/consumption budgets; and pass the exact negative,
  restart, concurrency, importer, isolated-entrypoint, current-base and hosted checks named
  in review 5196352060.
so_what: >
  W6-C2 remains the first critical-path blocker for Grok Operations and any later Workspace
  consultation return. Do not implement against its current draft contract, configure the
  Grok Bot connection, promote the Grok Wake transport, or grant operational-principal
  authority. Repair #615 on the existing carrier and obtain fresh exact-head Sol review.
kind: architecture
verified_at: 2026-09-14
verified_by: >
  Direct source and current-base review of Mastermind PR #615 at
  97634130d4bd69c3592502b2bb0e71829c55405c; formal REQUEST_CHANGES review
  5196352060; independent lifecycle/effect-law subagent review; protected-v1 and
  restart/answer-lineage probes; exact-head and synthetic-current-base test reproduction.
scope:
  - mastermind
  - "mastermind:common/agent_dialogue_consultation_contract.py"
  - "mastermind:control_plane/consultation_runtime.py"
  - "mastermind:control_plane/remote_codex_operator_adapter.py"
  - "mastermind:integrations/slack_agent_dialogue/persisted_wake_carrier.py"
  - "mastermind:pull/615"
  - "mastermind:pull/624"
confidence: verified
expires: 2026-09-21
---

## Supersession and exact identity

This record supersedes its earlier narrow diagnosis at #615 head
`8e9a8f62c84fcb4234c67f26fe3cbc479030a763` and dismissed review `5195521810`.
R4 head `97634130d4bd69c3592502b2bb0e71829c55405c` truthfully fixes those four
specific cases:

1. INTENT-only restart returns `NOT_DISPATCHED`.
2. consultation-local `NATIVE_ACCEPTED` requires a consultation-local dispatch event.
3. changed dispatch frames/current writer observations are refused.
4. changed recipient-consumption frames/current writer observations are refused.

Those repairs are necessary but insufficient because they do not prove the real Wake/provider
journey or close answer/result identity.

Current protected Mastermind is `af9fce32861f9c1496b85a580e3569712170d92b` with compatible
Skillpack 1.0.1. Protected movement after the review checkout adds only Datadog deployment and
observability files. It is path- and dependency-disjoint from #615. A synthetic merge is
conflict-free and the integrated focused family passes `103 passed, 4 skipped`.

## Current blocking behavior

### 1. Protected v1 is mutated under the same identity

Protected `mastermind.agent_dialogue_consultation.v1` accepts the old exact frame without
`question_message_key` and yields fingerprint
`f63e2e0e2e64939b47e03fc4008115064bca4a51ef6cb02b8ab7025c2cdd19b1`.
The candidate makes `question_message_key` required while retaining the same v1 name, rejects the
protected frame, and yields a different rebuilt fingerprint
`59f67fe58a9fca4ad427eea1a6f4ae0201afa392b98313e0bc720f3249e2fdd4`.
This is a schema/fingerprint break, not compatibility.

### 2. The real Codex ingress refuses the candidate instruction

`CodexConsultationIngress.deliver()` creates free-form consultation text and a random UUID nudge.
The real worker broker and Codex adapter require the frozen `ATTENTION_TURN_INSTRUCTION`; only the
permissive fake accepts the candidate call. The random nudge also bypasses the persisted Wake nudge
identity needed for effect reconciliation.

### 3. Consultation effect facts are not causally joined to Wake

A caller can pass WAKE-shaped strings to mint local `DISPATCH_ATTEMPT`, then caller-supplied
thread/turn values to mint `NATIVE_ACCEPTED`, without authenticating an exact persisted Wake
`DeliveryAttempt` or typed provider observation. Semantic receipts may exist, but they must be
derived from the canonical Wake/provider evidence rather than becoming a parallel effect reducer.

### 4. Late provider evidence leaves contradictory effect truth

After an unsettled dispatch records `EFFECT_UNKNOWN`, a late `NATIVE_ACCEPTED` can be appended.
`resolve_restart()` still returns `EFFECT_UNKNOWN`, while the derived projection removes the blocker
because native acceptance exists. Downstream recipient/answer/requester credit can continue from a
history that another API still declares unresolved.

### 5. Answer availability and consumption are not linked to the stored request/result

Exact probes show:

- a different live requester actor can obtain `ANSWER_AVAILABLE` under the intruder Job/Attempt;
- a different live recipient and binding can answer the original consultation;
- Answer A can be recorded available, then changed Answer A-prime with the same message key and a
  different fingerprint/digest can be consumed even though A-prime was never available.

The runtime must match stored requester, recipient, binding, actor digests, request reference,
artifacts, budget and semantic identity before availability, and requester consumption must match
the exact available fingerprint and semantic digest.

### 6. Additional authority/effect gaps

- Runtime accepts blank fingerprints and can persist them instead of requiring a canonical digest.
- current-recipient validation duplicates partial SQL instead of consuming the canonical harness
  binding projection and has a TOCTOU window before receipt append.
- one-answer counting occurs outside the append transaction, allowing distinct concurrent answers
  to race.
- lateness is caller-controlled instead of derived from trusted time and `valid_until`.
- valid correction history is not accepted by the availability path.

## Proof reproduced

The exact candidate is technically green but semantically blocked:

```text
focused W6-C2 + contract              25 passed
protected Company MCP                 75 passed, 4 skipped
W6-B native round trip                 2 passed
isolated foreign-CWD entrypoint        1 passed
17-file importer family              454 passed, 1 skipped
current-base integrated focused       103 passed, 4 skipped
required hosted test/security          success
```

The direct negative probes above are the discriminating evidence. Green happy-path suites and PR
prose do not establish the missing causal and identity constraints.

## Same-carrier repair boundary

The existing #615 writer must preserve one canonical Executive/Wake/effect plane and repair on the
same PR/branch. Required outcomes are:

1. preserve protected v1 exactly or add an explicit new version and compatibility routing;
2. use the real Wake dispatcher/current-writer path, fixed instruction and stable persisted nudge;
3. authenticate exact Wake attempt and provider observation before semantic dispatch/native credit;
4. use one effect reducer for restart and projection, including late-result reconciliation;
5. bind answer availability and consumption to stored request and exact result digests;
6. require a canonical non-empty fingerprint and canonical RuntimeBinding projection;
7. atomically enforce one answer/one consumption and deterministic expiry/correction history;
8. return RED-to-GREEN negative controls plus focused/importer/native/isolated/current-base/hosted proof.

Do not create a replacement PR, result store, retry plane, callback database, provider route, or
production arm. No Grok implementation wave may bind to draft symbols while this gate remains open.

## Continuation

After #615 returns a new immutable head, Sol performs fresh exact-head review. Only a PASS and
protected interface unlock the first bounded Grok source waves. Because W6-C2 itself must now resolve
schema versioning, the later Grok reasoning-surface wave must use the next lawful version after the
protected W6-C2 contract rather than assuming that `v2` is still free.