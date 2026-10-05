---
workstream: WS:PROPHET-US-V4-RECOVERY
session: chatgpt/continue-ceo-project-s0-recovery-20261005-c4
model: sol
ended_because: ci_handoff
prs:
- 8192
mission_complete: false
mission: Continue the recovered Continue CEO Project Prophet programme, closing S0
  source-integrity defects without introducing H1 or financial authority.
state_before: PR8192 bf77 had six demonstrated integrity defect families. A later
  scratch repair was uncommitted; its139-test and six-mutant work was recovered rather
  than rebuilt. Another Prophet session retains Q06/8069 and P1a/8444 source custody.
changed:
- path: scripts/check_prophet_h1_prospective_accrual.py
  what: Require regular single-link source capture, recursively outcome-free physical
    schema, typed unique native keys, coherent identity/group states, and native group
    roster/membership/digest consistency using the existing Context Vector contract.
- path: tests/test_prophet_h1_prospective_accrual.py
  what: Restore and extend discriminating integrity regressions, including all six
    native producer group states and14 new group contradictions. Positive fixtures
    now carry actual owner-compatible group receipts.
- path: research/prophet_v4/S0_CAPTURE_INTEGRITY_R2_20261005.json
  what: Bind native test, eight caught mutation, actual CLI and source-restoration
    evidence to exact source hashes.
verified:
- claim: Recovered repair reproduces before further hardening.
  command: python3 -m pytest tests/test_prophet_h1_prospective_accrual.py tests/test_us_context_vector.py
    -q
  result: 139 passed; native.xml hash in evidence.
- claim: New group-coherence tests distinguish existing defects from genuine producer
    states.
  command: python3 -m pytest tests/test_prophet_h1_prospective_accrual.py -q -k 'owner_generated_group_states
    or group_receipt_coherence'
  result: Before repair:14 failed,6 passed,71 deselected; after repair included in159
    passed,0 failed.
- claim: Final source passes the native verifier and Context Vector regression owners.
  command: python3 -m pytest tests/test_prophet_h1_prospective_accrual.py tests/test_us_context_vector.py
    -q
  result: 159 passed,0 failed; eight intentional source mutants caught by assertions
    with zero collection errors; original source restored.
- claim: Actual CLI uses the same unchanged synthetic owner bytes and writes its stdout
    receipt.
  command: python3 -m scripts.check_prophet_h1_prospective_accrual --expected-session
    2026-09-29 --board-definition board-v1 --root <isolated-fixture> --json-out <receipt>
  result: Native owner positive exit0/S0_CAPTURE_PRESENT; contradictory roster exit2/SOURCE_CONFLICT;
    h1_admitted and model_fit_executed false.
unverified:
- claim: Author-distinct whole-candidate acceptance
  what_would_verify: MastermindX1 review on the new exact head, including the unchanged
    bf77 strict native snapshot reader and repaired checker.
- claim: Normal parent release, supported-base CI and prospective production capture
  what_would_verify: Accept8091 via its owner, normal stack integration onto main,
    required exact-head CI/review, then first ordinary nightly receipt under the existing
    owner.
unresolved:
- Release HOLD remains; no merge, auto-merge, production activation, trial registration
  or outcome access.
- Q06/8069 and P1a/8444 are actively owned by the other recovered Prophet session;
  do not touch its PID43262 or CI-closure refusal.
- Current UI/served-model metadata unverified; sol is the schema-supported organizational
  author label, not a provider-model attestation.
next_actions:
- Publish the verified candidate through the managed branch and expected-bf77 fast-forward
  of existing PR8192; reconcile the exact remote head before any replay.
- Obtain author-distinct whole-source review and consume findings; keep unsupported
  stacked-base authority HOLD.
- After parent8091 acceptance, perform normal stack release and verify the first ordinary
  prospective nightly without reading protected outcomes.
do_not_redo:
- Do not rebuild the recovered patch or repeat accepted139/159 results without material
  invalidation.
- Do not reopen the repaired strict native snapshot reader; its48cb57b2 source hash
  is unchanged.
- Do not create a second Prophet programme, reader, store, group selector, outcome
  authority or replacement PR.
- Do not touch the clean legacy bf77 checkout or old scratch review directory.
danger_areas:
- All tests use synthetic candidate inputs; engineering proof is not H1 admission,
  real-market accuracy or production acceptance.
- The current expected source branch is sol/prophet-h1-accrual-checker-20260929; managed
  continuation branch is operation-derived and distinct. No force update.
- Source-read safety binds one captured byte object to schema, decode and digest.
  Never restore unrestricted reads or outcome projection.
---

# S0 integrity repair — recovered CEO continuity

Existing parent is Macro #6817, operation `prophet-cockpit-four-market-recovery-20260904-sol-001`. The exact conversation title was **Continue CEO Project**, not either heatmap programme. This record preserves a path-disjoint continuation; it does not transfer the other Prophet session's Q06 or first-frame workspace.

Protected procedure and all companions were pinned to `7eac3ec252475600147ec9a376b8ca16403ac4c5`, Skillpack1.0.1/bootstrap1. Current user recovery supplies intent; old comments are evidence, not new authority. Executive V3 was observed read-only. No child worker or background Web execution is claimed.

Managed workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/prophet-s0-integrity-repair-r2-20261005-c4-001`. Evidence root: `/Volumes/Mastermind/tmp/prophet-s0-integrity-repair-r2-20261005-c4-001`. Original patch digest and final source hashes are committed in the companion receipt. Mutation probes restored the exact source before subsequent validation/publication.

The group repair verifies owner-issued membership, rule, basis and roster receipts. It does not select groups or resolve current membership to rewrite history. Explicit missing states remain admissible. Scientific/financial authority stays false.

Current publication/review status belongs to existing PR #8192; cumulative recovery comment5989587949 is the integration frontier. A source commit, test pass, review request or this handoff does not prove merge, installation or ordinary-nightly capture. MISSION_COMPLETE:false.
