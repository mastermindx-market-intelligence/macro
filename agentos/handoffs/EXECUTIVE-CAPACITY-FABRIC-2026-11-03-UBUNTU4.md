---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/web-ubuntu4-fabric-integration-20261103-c3
model: sol
ended_because: blocked
mission: >
  Integrate Ubuntu4 into the existing native Subagent Fabric for useful tasks and
  retained repository sessions. This bounded handoff covers Ubuntu4 only; it does
  not supersede the separate Executive provider, entitlement or job waves.
state_before: >
  Ubuntu4 was registered and physically healthy, but all seven provider modes
  were qualification-only. The repository-task adapter and controller excluded
  Ubuntu4, and the receiving lanes/repos directory had no repository donor.
changed:
  - path: "Mastermind:ops/native_fabric/quota_continuity/UBUNTU4_INTEGRATION.md"
    what: "Versioned U4.1-U4.6 task tree, source validation, exact enrollment and real-work proof gates."
  - path: "Mastermind:ops/native_fabric/quota_continuity/candidate/fabric_task.py"
    what: "Add Ubuntu4 to the existing sparse repository host allowlist, preserving all other admission."
  - path: "Mastermind:ops/native_fabric/quota_continuity/candidate/remote_sub.sh"
    what: "Add Ubuntu4 to the matching controller allowlist; retain existing result and session handling."
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: "Add this handoff pointer without changing Executive wave states or claiming live Ubuntu4 capacity."
verified:
  - claim: "The source candidate is published in Mastermind PR #2008 at exact head 5bab743fc8f99e2e2af42619a6975a5778f4ef62."
    command: "studio_git_push_current_branch; GitHub GET repos/mastermindx-market-intelligence/Mastermind/git/ref/heads/sol/web-ubuntu4-fabric-integration-20261103-c3"
    result: "APPLIED; local and remote head match; source tree clean."
  - claim: "Ubuntu4 passes physical placement gates while automatic MiniMax placement remains held."
    command: "pool onboard ubuntu4; python3 <installed-ext>/host_pick.py --mode minimax --explain"
    result: "Binaries present; fresh sensor reachable, zero lanes, approximately 867 GiB disk and 11 GiB memory; automatic-qualification FAIL explicit-canary-only."
  - claim: "Ubuntu4's receiving donor is absent."
    command: "ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=yes mmx-ubuntu4; inspect /home/ubuntu4/lanes/repos"
    result: "Directory exists and has no repository entries. No clone or donor was created."
  - claim: "The new adapter cases and current Ubuntu4 controller/session cases pass offline."
    command: "PYTHONPATH=ops/native_fabric/quota_continuity/tests python3 -m unittest test_ubuntu4_sparse_request -q; separately: python3 -m unittest test_macro_result_controller -q with the same PYTHONPATH; isolated Python3.12 rerun recorded in the source plan"
    result: "8 focused adapter cases passed. All 15 Ubuntu4 controller cases passed; two original Ubuntu0 timing failures passed on isolated rerun. Offline fixtures do not prove provider execution."
  - claim: "Current release declarations match all staged source bytes."
    command: "python3 rollout/build_review_stage.py; verify SHA256 of each staged manifest path; python3.12 -m unittest test_support_policy_source -q"
    result: "102 files verified; manifest 9463889cb7146504095ecf2dee774c28d8ddda5cb50515f2afcb0b7b15cf8563. Five support/current-generation cases passed in the final 15-test focused run."
  - claim: "Independent review identified five stale current-source pins; the exact repair passed all affected checks."
    command: "fabric_result and fabric_accept for u4-sparse-review-20261103-c3-a; python3.12 -m pytest on the five affected current-reader files/cases listed in the Mastermind source plan"
    result: "Terminal rc0, CHANGES_REQUIRED consumed and accepted as useful review; 5bab743f repairs only the five test assertions and evidence note; 8 passed, exit0. Runtime/manifest bytes unchanged."
unverified:
  - claim: "Ubuntu4 has an accepted current-key provider enrollment and can finish a real admitted task."
    what_would_verify: "Approved host-local enrollment followed by one genuine native first-worker run, retained useful result, settled lease and original-parent acceptance."
  - claim: "Ubuntu4 can complete a normal automatically routed repository session."
    what_would_verify: "Narrow promotion of the accepted mode, accepted source release, qualified host-local Macro donor, then an exact-commit ordinary sparse task with retained real session/result."
  - claim: "The source candidate is fully release-qualified."
    what_would_verify: "Independent exact-head source review, required hosted checks, non-author formal approval and the existing protected merge/release process."
unresolved:
  - "All seven Ubuntu4 modes remain qualification-only. Existing credential-owner enrollment action in Mastermind #539 comment 6398589356 remains unresolved; no secret copy or denied-path retry was attempted."
  - "The M2 broad donor/security run is not green: 69 passed and 64 failed because Apple Git emits sparse-index-expansion advice on stderr, rejected by the unchanged strict reader. Preserve this known limitation."
  - "First review u4-sparse-review-20261103-c3-a returned CHANGES_REQUIRED and was accepted as useful review evidence; its five current-reader pin findings were repaired in 5bab743f and all 8 affected tests passed. Follow-up u4-sparse-review-20261103-c3-b is submitted on the same original root/parent; reconcile that distinct review result before release."
next_actions:
  - "Current assigned receiver: inspect Mastermind #539 and PR #2008, reconcile exact branch/source custody and the existing Fabric review; finish permitted source review and hosted qualification on the same carrier."
  - "Chris or the approved credential owner: complete Ubuntu4-local MiniMax enrollment through the incumbent owner action in #539. Do not put credentials in GitHub or chat."
  - "After genuine enrollment, the assigned native owner uses the existing qualification route with a new stable child under root ubuntu4-fabric-hardening-20261023. Verify START, useful result, lease settlement and original-parent acceptance before removing only that mode's hold."
  - "After source acceptance and qualification, prepare Ubuntu4's donor through the incumbent workspace owner and verify an ordinary routed exact-commit task plus retained session."
do_not_redo:
  - "Do not reimplement or replay merged Ubuntu4 qualification PRs #1749 and #1784."
  - "Do not retry historical run u4-qual-20261023-c1 or reuse the current review ID for another request."
  - "Do not weaken qualification holds, sparse donor pins, strict Git stderr checks, deadlines or lease retention to manufacture a pass."
  - "Do not confuse this native Fabric host integration with a new Executive Job, provider registry, scheduler or runtime."
  - "Do not redo the 102-file stage closure or broad Mac donor diagnostic unless its source/environment changes materially."
danger_areas:
  - "Controller launch, SSH return and LOCAL_POLL_EVIDENCE_ONLY are not proof of worker START or accepted result."
  - "The live registry has no physical_lane_root for Ubuntu4; bound-root sparse support is outside this change."
  - "CPU scope remains limited to Ubuntu2/3 and the special qualification-host route remains incompatible with repository minting."
  - "Generated native-code-stage must remain outside tracked source; immutable historical upgrade fixtures keep their original pins."
---

# Ubuntu4 native Fabric integration continuation

## State

MISSION_COMPLETE: false. Capability is PARTIAL / BUILT_NOT_PROVEN. The source
routing repair is published in [Mastermind PR #2008](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2008);
no real Ubuntu4 provider task or session was completed by this work.

The task tree is
[UBUNTU4_INTEGRATION.md at 5bab743f](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5bab743fc8f99e2e2af42619a6975a5778f4ef62/ops/native_fabric/quota_continuity/UBUNTU4_INTEGRATION.md).
The original fleet carrier remains [Mastermind #539](https://github.com/mastermindx-market-intelligence/Mastermind/issues/539).
This organizational link is proposed until this record is accepted through its Git carrier.

## What remains, in order

The primary operational dependency is real Ubuntu4-local provider enrollment.
The existing [credential-owner checkpoint](https://github.com/mastermindx-market-intelligence/Mastermind/issues/539#issuecomment-6398589356)
records the human enrollment action and a sensitive-path refusal. The current
assignment authorizes integration work; it does not supply a missing credential
or override that refusal.

Source review and hosted checks proceed independently. After qualification,
remove only the accepted mode's automatic-placement hold and prove a normal
routed task. Repository sessions additionally require the accepted source release
and a qualified local Macro donor.

## What can surprise the next receiver

The source worktree on M2 is
`/Volumes/Mastermind/agent-workspaces/web/ubuntu4-fabric-integration-20261103-c3`.
The records worktree is the same operation under
`/Volumes/Mastermind/agent-workspaces/macro/web/`.
Both use branch `sol/web-ubuntu4-fabric-integration-20261103-c3` in their own
repositories; they are distinct registered carriers.

The installed native generation observed was sequence 24,
`28faaf101463bcabef578ab1acabdcd270e301c7ed9cedf294e82fd459ccfcce`.
This work did not select a new generation. Offline fixture success is source
evidence only.

## Findings and preserved scope

No new decision or discovery record is minted; the source issue, patch, tests
and this handoff contain the bounded new finding. Existing Executive wave and
entitlement records remain at their own scope.

No Slack counterpart or temporary watcher was created. The native source adviser
is complete. The first Fabric review is terminal and accepted as review work, not
source approval. Follow-up review u4-sparse-review-20261103-c3-b has retained
controller PID 96365; consume its result through the same Fabric owner. The full
first response SHA-256 is 1d09fdd7f19c7ecdf012c8b478a8ee6c56740ed490333554b1b6a4b94e2f07c5.
