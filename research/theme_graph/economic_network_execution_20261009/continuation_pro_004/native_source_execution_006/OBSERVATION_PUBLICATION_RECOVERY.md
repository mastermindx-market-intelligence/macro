# Observation candidate publication recovery

**Candidate cbcc5ee143400af162a252e4faac0f06c7157e37 is published on the original pro003 branch.** The first push failed and is preserved. The subsequent ordinary push completed with exit 0 and an exact remote-head readback. No source commit was rewritten and no alternative implementation carrier was created.

## Candidate and source scope

The candidate's sole parent is **3521765204903320db76ddd84d6a43539ded8e62**, the ordinary integration of prior candidate **693ee939c8a28920ef9de7bc32a9f47a7ba76b82** with accepted main **87b01101ef13aa20ded205f3a2b267b68d094def**. Its 22 changed paths are research evidence only. The 139 checkpoint members and 71 incumbent owner inputs were checked unchanged before the recovery.

The shared CI definition change from accepted main remains preserved. Publication recovery changes no CI definition, source policy, code, test expectation, licence or owner assignment.

## First attempt: actual failure

Managed native process **50875** concluded with exit **1**, runtime **1435.86 seconds**. The actual Git push exit was 1 and the subsequent remote branch read still returned **693ee939**. The worktree remained clean with no ignored files.

Git reported that lazy fetching was disabled and it could not obtain promisor object **a060f005dcb8fb9ec014d56b3dde699b3b7c634f** during packing, followed by the disconnected push. The original wrapper printed a stage named PUBLISHED before asserting the push result. **That label was not a successful publication:** the preserved nonzero exit and unequal remote head control the outcome.

The failed push receipt has SHA-256 **8d94a78672a6594305333e11a2c26f7935267a4b0b14e4539d9fd48869af20a3**. Its original receipt and terminal tool result are retained alongside the recovery.

Two earlier process observations found the packing child active at about 98% CPU. Those observations supported waiting for the original operation rather than issuing a concurrent push; they did not prove that it would succeed.

## Read-only diagnosis

Native read-only process **26515** completed with exit 0. Git metadata showed a shallow, blobless promisor repository. The named object occurs at `data/ai_costs/provider_health.jsonl` in accepted 87b and candidate cbcc, but it is outside the candidate's new object closure after excluding both already accepted parents. The latter closure had **37 entries and zero missing-object markers**.

At the later diagnostic, Git could read the named object's type, and a separate size-only probe reported **545,448 bytes**. This does not retroactively contradict the earlier packing error or prove the complete reason for its duration. No provider-health content was read or copied by this diagnostic.

Read-only process **28209** completed with exit 0. At 15:03:36 UTC, Git's actual remote advertisement returned main **6ced30b9d69f7e5644d74f1f4648def0ac357c42** and the observation branch still at **693ee939**. The repository's own instructions identify the shared object store and explain its blobless history behavior; no shared-store reset, cleanup, config rewrite or repair was performed.

The chosen repair used [Git's documented push negotiation](https://git-scm.com/docs/git-config#Documentation/git-config.txt-pushnegotiate), which discovers common commits through additional negotiation instead of relying only on currently advertised ref tips. This was an appropriate bounded response to an advancing remote main and a complete local new-candidate closure. It is not presented as a general proof that every partial-clone failure has the same cause.

## Recovery: actual publication

The recovery rechecked the original failure receipt, exact local candidate/parent, clean state, all 139 checkpoint members, all 71 owner inputs, complete new object closure and unchanged old remote head. It then ran the ordinary Git push with **command-scoped `push.negotiate=true`**. The existing no-lazy-fetch protection remained in force.

Managed native process **30522** completed with exit **0**, runtime **14.85 seconds**; its Git child was **30606**. The push returned exit 0. A new independent `ls-remote` read returned exactly **cbcc5ee143400af162a252e4faac0f06c7157e37**. The worktree remained clean, no ignored paths appeared and the persistent `push.negotiate` configuration was unchanged.

The recovery receipt is **7,688 bytes**, SHA-256 **4810a1c6cf0679b107a2592a330a80e573ff3841ef504b67c59f563c5b9a961b**. The preflight receipt is **1,414 bytes**, SHA-256 **ecabcf4d1cb4c8c068c3461ab13dcc0f19a6eb4376400fb999f3a0e0c7d1249d**.

The [PR #8711](https://github.com/mastermindx-market-intelligence/macro/pull/8711) body was updated only after the exact candidate was observed published. Its 17,543-character replacement body was then read back byte-for-byte at the unchanged candidate head. The complete body text is archived here.

## Publication is a distinct acceptance boundary

The naturally triggered candidate run is **37949036732**, attempt 1. The independent CI reader found that the PR's base field still reported 87b, while the actual retained plan binds tested merge **ecd49338799e419055737a20f3fb462c4b97bdd8** to actual base **6ced30b9d69f7e5644d74f1f4648def0ac357c42** and candidate cbcc. The actual plan/checkout is the controlling tested-source identity; the stale PR base field is not substituted for it.

This publication record does not claim that the natural run has completed, that the current canonical release gate has passed, that a merge has occurred or that the fresh accepted-source C01 replay has run. Those require their own actual evidence. The earlier successful 693 CI packet and its subsequent freshness refusals remain historical evidence, not a waiver for this candidate.

The same documented command-scoped negotiation may be used for subsequent ordinary publication when appropriate to the actual shared partial clone. It grants no force push, hook bypass, merge waiver, source rewrite or permission to disturb another owner's worktree.
