---
key: ROUTER-FABRIC-GENERATION-TEARDOWN-AND-ADOPTION-GAPS
claim: On Mastermind 8e25bb32601ef5f40a689da6d6f24149e79e31fa and PR675 module at 4c2dd89e5ff8fa78fc912f8d266cb6409147eb56,
  cleanup of an older TurnKey can delete current-generation visible output and prebind state when the
  native turn identifier is reused.
falsifier: 'Materialize the regression source from Mastermind #675 comment5689675538 and run python3 -m
  pytest test_router_vtp_teardown_20260915.py -q with the exact reviewed module on PYTHONPATH. Old-grant
  revoke and old-generation invalidation must preserve current-generation text and its active prebind,
  while current-generation invalidation must still remove them. Two failures and one passing control were
  observed on the baseline and candidate; unchanged-source success under these same inputs would falsify
  the finding.'
so_what: Do not declare restart/generation isolation or router-fabric production acceptance from the four
  original VTP-M1 fixes. Reuse full TurnKey at the existing cleanup boundary, preserve current teardown
  behavior, and integrate the already tested narrow repair through the incumbent source owner. Do not
  misattribute this inherited defect to PR675 or create another turn identity registry.
kind: landmine
verified_at: 2026-09-15
verified_by: 'Mastermind PR675 comment5689675538; exact-source git comparison 77d25598..4c2dd89e; pytest
  regressions: baseline 2 failed/1 passed; candidate 2 failed/1 passed; current-head normal suite 125
  passed; narrow repair plus regressions 128 passed. Current-head repaired JUnit SHA256 e7f4cf9bb8529c05c8bf66f246ad6d09d921bd3c3676bcfb1a1592d960940b77.'
scope:
- WS:EXECUTIVE-CAPACITY-FABRIC
- mastermind
- control_plane/visible_turn_projection.py
confidence: verified
---

## Exact repair and limits

The existing turn map is keyed by native turn ID; its value carries the full TurnKey. Both last-viewer revocation and generation invalidation must compare the stored key before removing that value or clearing the current prebind. The proposal uses the existing lock and identity, not a new registry. Patch SHA256: `40970d8a7efb058eebe4d89668dcf7a1b7df946022a92fe3ed59575bb3a66b13`; regression-source SHA256: `d3547bed95d85b93e52136f5eecda1a13c7866464155bd279679b452c562c6da`. Both are embedded in the exact PR comment.

The repair was applied and tested only in a separately managed review checkout, then the original bytes were restored. The incumbent branch was not modified. This is BUILT_NOT_PROVEN / REVIEWER_REPAIR_ARTIFACT, not merged or installed code. The defect is source-reproduced, not an assertion that this schedule occurred in live provider traffic.

## Adjacent adoption facts

Macro PR7114 at `abacaeb474ccac5991b8ebc7e30198dd273244b0` has an independently qualified strict opt-in profile, not fleet-wide enforcement. On installed Claude2.1.259 its six existing scripted-loopback scenarios passed;169 focused tests passed. No real model inference, billing-model equality, root-shared budget, Executive Job or production adoption follows from that proof.

Its actual contract-delta release failure is missing workflow wiring for the new safety suites. Macro PR7114 comment5689585459 carries a one-line repair using the existing CI owner: canonical suite discovery is false/false before, true/true after, false/false after restoration;163 focused tests pass with the repair. Patch SHA256 `a361d041f959f1dc4877e3ddb75bb313535c1998e58f483f9dac0995711d8f08`. No waiver or alternate scanner was used.

Macro comment5654307030 also records previously tested but UNINTEGRATED source/CWD binding work. Preserve its patch SHA256 `f46552d6bf5ecbcacc9096f51650805314f1374649e2cd61fd219bae5532946e`; records-only object `33dd4c16b8ccc4490f95f4156f147dbf8bcbdb1e` is not that implementation. This session recovered the record but could not freshly read the remote patch, so its bytes and reported190/7 results are attributed, not independently reverified.

## Source implementation follow-up

Mastermind #678 now carries the bounded full-key cleanup repair at `4e991587d383efb9e934b7a57f860142b32f274d` from protected7642aea1. This is actual committed source, not just the prior review artifact. Its129focused tests pass; hosted/release/installed gates remain separate. The historical baseline failure claim above remains true. Macro #7114's missing-test wiring is also repaired at7f68d90d with hosted contract-delta SUCCESS; do not reproduce that finished fix.
