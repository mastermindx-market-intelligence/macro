---
key: NATIVE-CLAUDE-FAMILY-B-CURRENTNESS-REALIZATION
question: >
  What must Family B correct after executable V1 characterization shows that sealed realm receipts
  do not establish per-realm current enrollment, while the V2 plan also overstates model-resource
  knowledge and unchanged V1 source identity?
answer: >
  Treat the existing receipt as historical integrity, not current execution authority. B2 must
  realize current realm_generation and enrollment state under the incumbent privileged provisioning/
  provider-realm owner, scoped to the exact host_ref and capacity_capability_id, and reject stale or
  caller-selected state for new execution. Preserve historical effect-free replay and the existing
  CF2 claim/broker boundaries. Family-B domain/host placement does not prove nested model-family quota
  algebra; that composes later through existing Provider Control and quota/model-capability owners.
  V1 behavioral compatibility and unchanged pinned-release bytes remain required, but a newly built
  release that edits a V1 material-source file must honestly change its material-source identity.
  Never forge the old hash or create another normalizer to hide that change. This is an author-side
  correction candidate, not independent review, source release, B1 START or production acceptance.
rationale: >
  Current codex_provider_realm.py seals caller-supplied positive generations and reads one global
  fixture enrollment state. Its verifier checks embedded fields and HMAC, not per-realm owner-current
  state. Reusing realm_generation therefore preserves the concept/name but does not establish the
  missing production realization. Separately, engine/provider_capacity.py hashes itself as a V1
  material source, so the B4 instruction to edit it cannot coexist with an unconditional old-digest
  preservation promise. Distinguishing integrity/currentness, domain/model resources and behavior/
  source identity prevents green fixtures or provenance prose from becoming false capability claims.
alternatives:
  - option: Add V2 identity fields and reuse the V1 closure unchanged
    why_not: It has neither per-realm current state nor an owner-issued monotonic current generation.
  - option: Reject all historical receipts after revocation
    why_not: That destroys truthful history; only new execution eligibility must fail currentness.
  - option: Accept a caller-computed registration digest as owner provenance
    why_not: A public hash authenticates no caller; the current fact must come from the accepted owner boundary.
  - option: Treat generic weekly rows as independent per-model wallets
    why_not: The nested shared/model resource relationship has not been represented or proven by Family B.
  - option: Preserve the old V1 material digest while editing its hashed source file
    why_not: It is false source identity and contradicts the existing byte-hashing contract.
  - option: Bypass B0 because the author-side characterization is green
    why_not: Characterization is not independent review, current-base integration or release acceptance.
evidence:
  - "Mastermind@7642aea155d2817219135b24246b55c1d7611c66 control_plane/codex_provider_realm.py blob ab1e475e4f0f2b316f228ffbf2e95218d0219a7a: closure-global enrollment, caller-selected generation, HMAC integrity verifier."
  - "Same protected source ops/executive_os/provider_realm_facts.py blob a07102df9ce6604ff77d92b752c4b518445aa7f5; sandbox full-file Git blob recomputed and matched."
  - "Executed python -m pytest -q test_owner_gap.py in a sandbox: 5 passed in 0.05s; three V1 characterization gaps reproduced and two integrity/refusal controls retained. Unchanged function excerpts, stub catalog and public test key only; not full repository or production proof."
  - "Macro@ad3091c11c336bd20e031301346b17fdfb326450 engine/provider_capacity.py blob 68eda49254003956dd43193ad1284959a0a14593: MATERIAL_SOURCE_PATHS includes itself and _material_rows hashes actual bytes."
  - "Mastermind PR #662 correction commit fc5bbcf15a4fc929618ef9c93a897b66aa218e36, docs/superpowers/specs/2026-09-15-ocr2c-family-b-currentness-and-source-identity-correction.md: exact precedence, evidence hashes, B2 realization gate and review criteria."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/PF1
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-15
---

## Candidate precedence

This decision and the exact paired Mastermind correction supersede only the conflicting currentness,
model-resource and source-identity interpretations in this pending PR's primary architecture,
multi-host amendment and prior Family-B decisions/handoffs. They do not override protected source
law or release the Draft/HOLD. All other Family-B ownership, auth, no-rebuild and effect boundaries
remain unchanged. Independent paired review is still required before B0 source acceptance.

## B2 owner-realization requirement

Before B2 implementation START, identify and freeze the actual incumbent privileged provisioning/
host-config record, mutation seam and read seam for current per-realm state. The current V1 closure
is not that production realization. If absent, return REALM_OWNER_REALIZATION_REQUIRED for a bounded
owner-realization design decision; do not ship receipt-only scaffolding as B2 or add a second account,
realm, quota, credential or lifecycle service.

Historical integrity and current eligibility remain distinct. A new execution must validate current
Macro capability registration plus current realm enrollment/custody, including the existing
claim-to-spawn fence. A replay returns the historical accepted evidence without new provider work.
The reproduced V1 behavior is not itself evidence of a live exploit: absent owner key/enrollment
still refuses; the characterization only establishes what the present receipt cannot prove.

## Provider Control implications

B0-B5 may prove provider-domain/host-realm facts without claiming nested model-family quota-aware
placement. Missing model-resource evidence remains unknown under existing policy; no per-model
wallets or new quota graph are introduced.

The current pinned CF1/H0 release remains untouched. New V1-compatible source may retain schema and
behavior while honestly changing its material receipt after a hashed file changes. V1 must not add
V2 registry paths/native slots merely because they exist. Any changed producer release requires its
normal acceptance/acquisition gate; old digest preservation is not an acceptable substitute.

## Continuation and exact next action

Source writer and carriers remain the existing paired records branches, not a new workstream or
replacement PR. The pre-repair targets were Mastermind #662@30f8a4c1188f19f99622da5503a70b643c1ef167
and Macro #7162@d5ac0d61f1a95b9d21441a6dc3b1905bde6b7c6d. Mastermind's author-side correction is now
fc5bbcf15a4fc929618ef9c93a897b66aa218e36; read this PR's final head at review pickup.

Continue the already-originated independent paired-review operation
`ocr2c-family-b-paired-architecture-review-20260914-sol-001` on Slack
`C0BSBM78V1N/1789456126.495979`. The reviewer must check both new exact heads, this correction,
current-base integration and exact-head CI, and return PASS or REQUEST_CHANGES. No reviewer has been
bound by these records. The Executive read probe returned 401 / manual reauthentication required;
no CEO intent was submitted and no alternative provider/account was selected.

B0 remains SPEC_ONLY / HOLD. B1+ remains unstarted. Do not repeat Family A, change generation names,
promote canary facts into production claims, rerun unchanged polling loops or treat prior-head CI as
new-head acceptance. No provider/credential/runtime/host/browser effect occurred in this repair.
