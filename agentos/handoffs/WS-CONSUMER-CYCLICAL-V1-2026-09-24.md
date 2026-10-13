---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/consumer-cyclical-v1-plnt
model: opus
ended_because: complete
mission: >
  Continue Consumer Cyclical as principal Fable integration owner from the
  accepted R15 handoff; first executable outcome V1 PLNT, preserving the R15
  external gates rather than bypassing or rebuilding them.
state_before: >
  R15 packet accepted on PR #7804 (DRAFT/HOLD), research only. Operation frozen
  at PLACEMENT_STATE WAITING_CAPACITY / RECEIVER_ASSIGNMENT NONE / EXECUTION_STATE
  PRE_START. No Consumer product code existed anywhere.
changed:
  - path: research/consumer_cyclical/v1/V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md
    what: "Admission edge, re-pin receipts, boundary ruling, golden oracle, frozen result semantics, integration rulings A/B"
  - path: agentos/decisions/DEC-CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT.md
    what: "The boundary decision and its alternatives"
  - path: contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json
    what: "V1-CORE contract; closed fact/result/explanation shapes"
  - path: data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json
    what: "Real PLNT Q2 2026 golden fixture, all facts native_admitted false"
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: "Pure Decimal projection; R15 M1-M5 result semantics"
  - path: tests/test_consumer_cyclical_intelligence_read_model_contract.py
    what: "16 contract tests incl. negative cases"
  - path: tests/test_consumer_cyclical_projection.py
    what: "45 tests incl. the real-path fixture-driven gate"
  - path: .github/ci/legacy-jobs.yml
    what: "Exclusive gate job consumer-cyclical-economic-change"
  - path: tests/test_ci_pack.py
    what: "Job name registered in CURATED_EXCLUSIVE"
verified:
  - claim: "All five external owner PR heads are byte-identical to the R15 freeze pins and still OPEN/DRAFT"
    command: "gh pr list --state all --search '7870 7780 7669 7462 7426 7331 in:number' --json number,state,isDraft,headRefOid"
    result: "#7870 3e3a7956d014, #7780 b68069b2e129, #7669 6942b2b62bad, #7462 31706d7322af, #7426 7bc04876747d - all OPEN, isDraft true"
  - claim: "The R15-pinned shared transport is absent from main"
    command: "git rev-parse origin/main:app/theme_research.py"
    result: "fatal: path does not exist in origin/main (exit 128)"
  - claim: "The PLNT Q2 2026 exhibit is retained nowhere, so native admission is unreachable"
    command: "grep -rl 0001637207-26-000042 data/ config/ engine/"
    result: "no matches (exit 1); data/ was materialized first, so this is not a sparse-tree artifact"
  - claim: "All six R6 7.1 golden values are exact and the emitted document validates against the contract"
    command: "python -m pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q"
    result: "61 passed; READY doc 0 schema errors, zero-facts doc 0 schema errors, 0 float( calls"
  - claim: "The shared sector-intelligence contract family still enumerates cleanly with the new contract present"
    command: "python -m pytest tests/test_sector_intelligence_contracts.py tests/test_consumer_cyclical_projection.py -q"
    result: "274 passed"
  - claim: "Agent OS records are schema-clean"
    command: "python3 scripts/agentos.py validate"
    result: "0 errors (111 pre-existing review-overdue warnings on other records)"
unverified:
  - claim: "PR #7942 merges green"
    what_would_verify: "gh pr view 7942 --json state,mergedAt after ci-plan and contract-delta conclude"
  - claim: "V1 is PROVEN_LIVE"
    what_would_verify: "Only a real entitled browser journey through the shared private transport, which is blocked"
unresolved:
  - "#7870 T09 EDGAR-family/fail-closed rights correction, plus T08b/T10e/T10f/T11a"
  - "#7780 cross-vertical profile/dispatch/mount ruling (owns the R15 H2 grammar)"
  - "#7669 template/page custody"
  - "Native admission of the PLNT exhibit by the incumbent source owner"
  - "Cluster provisioning: this M2 is local_only=grok,ocfree; qwen needs a remote host, minimax dies on unrecognized_model MiniMax-M3, and grok was refused at load1 22.8/24"
next_actions:
  - "Carry PR #7942 to squash-merge on concluded-green"
  - "Return the four external blockers to Sol with the receipts in the boundary spec"
  - "Do NOT widen into V2 LTH / V3 LULU / V4 theme journey before V1 returns to Sol"
do_not_redo:
  - "The V1 boundary adjudication - see DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT. Re-deriving it costs a full re-pin and collision census."
  - "Evaluating app/earnings.py as a transport opening. It was steel-manned and rejected on R15 H1's affirmative family selection, not on ignorance."
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation"
  - "The R8 native-staging denial: never retry, rephrase, re-home or delegate around it"
danger_areas:
  - "Fact keys and result keys are disjoint vocabularies that read alike, and confusing them is INVISIBLE to a numeric suite. _build_explanation tested FACT_KEY_* against the set of RESULT keys, so the economic lead was unreachable on every input while 61 tests stayed green - every asserted number was still exact, only the sentence explaining them was missing. Found by verifying from main after the merge, not by the suite."
  - "native_admitted is provenance, not a gate. Gating on it silently empties the whole vertical while its own tests stay green."
  - "A delegate's green suite can encode a world that cannot occur. Drive verification from the committed fixture, not the lane's fixtures."
  - "Duplicate keys in a Python dict literal: the LAST occurrence wins. One silently overrode a correct current_period_fact for several iterations."
  - "$defs/result is additionalProperties:false - internal carriers like value_decimal (a Decimal, not JSON-serialisable) must be stripped before emit."
  - "A new exclusive CI job must be added to CURATED_EXCLUSIVE in tests/test_ci_pack.py; that suite asserts exact set equality and takes ~4.5 min."
prs: [7942, 7945]
decisions:
  - "DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
discoveries:
  - "DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE"
  - "DSC:LANE-HOST-ELIGIBILITY-DOES-NOT-MEASURE-GIT-EGRESS"
---

## Cold-stranger summary

V1 as written asks for an entitled, browser-visible PLNT experience. Every external owner gate R15
named is unmoved and the shared transport is not on `main`, so those legs are **frozen, not rebuilt** —
R15 forbids every construction that would reach them anyway. What shipped is **V1-CORE**: the
deterministic, source-coordinate-bound economic composition, under the already-merged
`contracts/sector_intelligence/` family, following the Finance T1/T2/T3 idiom that landed the same day.

V1-CORE merged and green is **not** `V1 PROVEN_LIVE`. Say so when reporting it.

## Where it was left

Returned to Sol on the research carrier #7804 (comment `5814888647`, 2026-09-24), naming the four
owner blockers and — the load-bearing part — correcting that carrier's standing
`RECEIVER_ASSIGNMENT: NONE / EXECUTION_STATE: PRE_START`. That record was written before the Chairman's
live handoff and, left standing, would have lawfully licensed a **second** Fable receiver onto the same
operation.

Post-merge live verification earned its keep: it found the economic lead unreachable on every input
(see `danger_areas`), repaired on #7945 along with a same-class audit that hardened two further latent
instances of the same root cause. **Verify from `main` after the merge, not from the suite** — this
vertical has now produced two separate defects whose only symptom was invisible to green tests.

Nothing further is executable at this seat. Every remaining V1 leg is owner-gated, and R15 forbids
self-authorizing V2 LTH / V3 LULU / V4 theme journey on a V1 pass.
