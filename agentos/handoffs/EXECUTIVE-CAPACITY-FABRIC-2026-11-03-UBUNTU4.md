---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/web-ubuntu4-fabric-integration-20261103-c3
model: sol
ended_because: blocked
mission: 'Integrate Ubuntu4 into the existing native Subagent Fabric for useful tasks and retained repository sessions.
  This bounded handoff covers Ubuntu4 only; it does not supersede the separate Executive provider, entitlement or
  job waves.

  '
state_before: 'The original Ubuntu4 source branch and proposed Agent OS record were stale. Mastermind PR #2008 was
  Draft at 3aa5f98a; a later hardware-integrity incident invalidated earlier readiness. The donor had subsequently
  been installed and must be preserved. All provider modes remained held.'
changed:
- path: Mastermind:ops/native_fabric/quota_continuity/UBUNTU4_INTEGRATION.md
  what: Current U4.1-U4.6 gates, source evidence, hardware hold and exact recovery continuation.
- path: Mastermind:ops/native_fabric/quota_continuity/candidate/fabric_task.py
  what: Ubuntu4 sparse host admission and accepted-worktree reclaim within existing admission and custody controls.
- path: Mastermind:ops/native_fabric/quota_continuity/candidate/remote_sub.sh
  what: Matching Ubuntu4 controller host admission and refreshed exact current native closure.
- path: Mastermind:ops/native_fabric/quota_continuity/candidate/fabric_host_qualification.py
  what: Explicit Ubuntu4 Grok qualification alternative to MiniMax; no automatic hold removal.
- path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-11-03-UBUNTU4.md
  what: Replace stale readiness, missing-donor and old review claims with source-linked current evidence.
verified:
- claim: 'Mastermind PR #2008 publishes exact integration head 61562fa130c7d405f3872499beed72726659bb66 and remains
    Draft.'
  command: studio_git_push_current_branch(repository=mastermind, operation_id=ubuntu4-fabric-integration-20261103-c3);
    GitHub GET pulls/2008 and actions/runs?head_sha=61562fa130c7d405f3872499beed72726659bb66
  result: APPLIED; remote/local head match; parents 3aa5f98a1cd8a6c5e5deb9692235fdd59ccdaeea and f374289eb74587eaa755f5bc8e5a3252d00850e0;
    21 owned path differences and no others from protected base. CI 41992252219 queued, not passed.
- claim: The final current source closure is exact and historical release identities are preserved.
  command: python3.12 ops/native_fabric/quota_continuity/rollout/build_review_stage.py; SHA-256 all declared staged
    members; focused pytest historical repair and paired launcher cases
  result: 102 members verified; manifest 9fc709c501468bd3172eadae1e3768585ddc4fa0d3563ebd98d6eca565b324d4; inventory
    e3a38a25b5af3693e393c4b13dbed21fa2c093aaac9f1273179bfcb069cd22fb; final repair run 25 passed. Historical 95/102
    and AUTO identities unchanged.
- claim: Local qualification is partial, not a full passing test suite.
  command: Python 3.12 selected pytest runs and JUnit testcase reconciliation in the original Mastermind workspace
  result: 'Latest observation per unique selected case: 174 passed, 14 failed, three Linux-only skips, zero errors.
    Eleven cases expired before intended controller scenarios; three sparse-Git observation refusals. Load above
    100 observed; root cause not generalized from load.'
- claim: Current Ubuntu4 reachability and hardware acceptance are not established.
  command: 'remote_desktop_commander.list_devices; one BatchMode SSH check to mmx-ubuntu4; read Mastermind #2008
    comment 6628831146'
  result: Original device 44a1ccfd-caed-4942-ad1a-3e5297c801c8 offline; SSH reset by peer. Later incident reports
    corrupt Git bytes, unstable installed-library reads and repeated crashes. No accepted recovery receipt found.
- claim: Automatic Ubuntu4 placement remains held in the selected native release.
  command: Read native-code-releases/CURRENT.json; installed ext/host_pick.py --mode grok --json without refresh
  result: Sequence 30, generation 9691fff17648c82b09152ba285d620abf0fd12d10a9530a7abae0cd1ab96238b; ineligible due
    explicit-canary-only, ssh_unreachable and missing physical metrics. All seven modes held.
- claim: The one original Ubuntu3 paid source audit is terminal and accepted as useful source evidence.
  command: fabric_status; complete paged fabric_result; byte comparison against published 61562fa1; fabric_accept(by=reviewer,
    verification_summary=manual_result_review)
  result: Run u4-source-integration-audit-20261105-c3-a, root ubuntu4-fabric-hardening-20261023, parent ubuntu4-fabric-integration-20261103-c3
    returned rc0 and 9344 response bytes. Accepted complete digest e9aa6aa99c00bebb6969496f68f66964284c0d1191faf12e91bb6615634223f8.
    Audited 3aa5f98a plus f374289e; current runtime matches after only CLI help-text normalization. Its historical-fixture
    findings are repaired in 61562fa1. This is not formal GitHub approval, exact-head hosted CI or Ubuntu4 acceptance.
- claim: The records publication uncertainty was reconciled on the same original carrier.
  command: GitHub GET macro/git/ref/heads/sol/web-ubuntu4-fabric-integration-20261103-c3; studio_git_publish_status(repository=macro,
    operation_id=ubuntu4-fabric-integration-20261103-c3)
  result: Push initially returned EFFECT_UNKNOWN; without retry, GitHub and the original publisher both read back
    local/remote 184fe932203cee530264fe059cd634c90a684147, clean, publication_state APPLIED. The containing follow-up
    records the subsequently accepted audit.
unverified:
- claim: Ubuntu4 has accepted hardware integrity, reachability and provider enrollment.
  what_would_verify: Local-console recovery, then stable trusted-byte/Git/process-health checks, fresh placement
    metrics and legitimate host-local enrollment receipts.
- claim: The new exact source head is release-qualified and installed.
  what_would_verify: Fresh required hosted checks on 61562fa1, applicable GitHub/release controls, then native installer
    proof of the accepted source; preserve Draft/no-merge controls until lawfully released.
- claim: Ubuntu4 can finish ordinary load-balanced tasks and repository sessions.
  what_would_verify: Distinct first-worker START, useful retained result, settled lease and original-parent acceptance;
    promote only that accepted mode and prove normal automatic placement plus an exact-commit sparse repository/session
    task.
unresolved:
- The primary host gate is local-console access to observe boot/login/error/diagnostic state and restore the existing
  approved remote connection. Connectivity alone does not clear the integrity hold.
- Existing donor /home/ubuntu4/lanes/repos/macro was previously qualified at 4a2291747fd2d8d364a3838e1ed2263636bc64a6.
  Preserve it and forensic artifacts; revalidate after hardware recovery instead of recloning.
- Hosted CI 41992252219 is queued at this checkpoint; local controller/security failures remain unqualified, not
  excused. Three Linux-only cases are not proven by the Mac run.
next_actions:
- 'Primary host action: a person at Ubuntu4 observes the existing console and any diagnostic state, then restores
  the approved remote connection without replaying unknown tests. The current assigned session owns subsequent safe
  integrity validation.'
- 'Independent source action: consume exact-head Mastermind CI 41992252219; fix actual candidate defects in PR #2008
  while preserving Draft and existing review/release controls.'
- After hardware recovery, complete legitimate enrollment and accepted native installation, then one distinct first-worker
  qualification, narrow provider promotion, normal placement and real repository/session acceptance.
do_not_redo:
- 'Do not recreate the existing source/records branch, PR #2008 / Macro #10661, qualification root or workstream.'
- 'Do not replay merged qualification PRs #1749/#1784, accepted historical reviews u4-sparse-review-20261103-c3-a
  and -b, or historical failed run u4-qual-20261023-c1.'
- Do not replay the unknown memtester attempt, denied direct-I/O diagnostic or prior credential-source refusal.
  Do not inspect or copy credential bytes.
- Do not reclone/delete the existing Ubuntu4 Macro donor or forensic artifacts.
- Do not change deadlines, strict stderr guards, historical expected hashes, provider holds, leases or native release
  selection to manufacture readiness.
- Do not redo the verified 102-member closure or passing fixture repairs unless relevant source changes. The current
  audit u4-source-integration-audit-20261105-c3-a is terminal and accepted; do not relaunch or reuse it.
danger_areas:
- Earlier physical-readiness and missing-donor claims are superseded by later incident and installation evidence;
  they are not current readiness.
- 'Generic Grok success cannot prove sparse repository parity: existing sparse modes are glm, glm-codex, minimax
  and qwen.'
- Source publication, CI, protected merge, native installation, worker START, result settlement and acceptance are
  separate proofs.
- Qualification-host and repository minting remain separate; bound physical-root support is not introduced, and
  CPU scope stays Ubuntu2/3.
- Agent OS records are proposed continuity until their Git carrier is accepted, not runtime admission or evidence
  of an autonomous wake.
---

# Ubuntu4 native Fabric integration continuation

## §0 State — current 2026-11-05 checkpoint

MISSION_COMPLETE: false. Source is BUILT_NOT_PROVEN at Mastermind commit
`61562fa130c7d405f3872499beed72726659bb66`; PR #2008 remains Draft. Ubuntu4 remains
held and unreachable after a later hardware-integrity incident. No ordinary
Ubuntu4 worker or repository session has been accepted.

The exact source task tree is
[UBUNTU4_INTEGRATION.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/61562fa130c7d405f3872499beed72726659bb66/ops/native_fabric/quota_continuity/UBUNTU4_INTEGRATION.md).
The owning fleet record is [Mastermind #539](https://github.com/mastermindx-market-intelligence/Mastermind/issues/539).
This proposed record stays on existing Macro PR #10661 and does not advance Executive waves.

## §1 What is left — in order

1. At Ubuntu4's local console, observe its boot/login/error state and reconcile any running or prior diagnostics. Restore the existing approved remote connection. Then the assigned session must validate integrity and fresh physical eligibility.
2. In parallel, consume [exact-head CI](https://github.com/mastermindx-market-intelligence/Mastermind/actions/runs/41992252219). The original paid audit is terminal and accepted. Repair real source failures on the existing branch; keep current Draft/release controls.
3. Complete legitimate host-local enrollment and accepted native installation. Prove a distinct supported first worker, useful result, settled lease and same-parent acceptance before lifting only that provider hold.
4. Prove ordinary automatic placement and a real exact-commit repository/session task using the preserved host-local donor.

## §2 What will bite the next receiver

[The later hardware incident](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2008#issuecomment-6628831146)
supersedes earlier readiness receipts. A restored SSH connection is not a hardware-integrity acceptance.
The historical memtester outcome is unknown; the direct-I/O diagnostic and credential-source refusals
remain binding. Do not diagnose RAM/SSD failure or prescribe a BIOS flash from the existing evidence.

Mastermind workspace:
`/Volumes/Mastermind/agent-workspaces/web/ubuntu4-fabric-integration-20261103-c3`.
Records workspace:
`/Volumes/Mastermind/agent-workspaces/macro/web/ubuntu4-fabric-integration-20261103-c3`.
Both use the same existing branch and operation. Preserve ignored/untracked evidence.
A publisher timeout is not evidence of absence: this push returned uncertainty, then the same owner and GitHub both proved APPLIED without a retry.

Paid audit: `u4-source-integration-audit-20261105-c3-a`, root
`ubuntu4-fabric-hardening-20261023`, parent `ubuntu4-fabric-integration-20261103-c3`,
controller PID 72153, Ubuntu3/GLM. The worker returned rc0; the complete 9344-byte response was
reviewed and accepted with digest `e9aa6aa99c00bebb6969496f68f66964284c0d1191faf12e91bb6615634223f8`.
The three runtime members match the audited integration after only help-text normalization; its fixture
findings are repaired in the published source. Do not relaunch this terminal audit or treat its prototype
tests as current-head hosted CI, formal approval or live Ubuntu4 acceptance.

## §3 What was decided and found

No new architecture, scheduler, registry, authority or provider store was created.
Ubuntu4 uses existing sparse routing, worktree custody and qualification machinery.
Current source and immutable historical fixture identities are both verified explicitly.
The hardware hold is a material new invalidator of earlier physical acceptance.

## §4 Not in scope — do not adopt

Preserve all seven provider holds until real accepted evidence releases a specific mode.
Do not widen Grok's sparse adapter, change CPU scope, arm/merge the Draft PRs, copy credentials,
recreate the donor, repeat denied diagnostics or treat an old session as an approver.
The existing Slack coordination thread and hourly enrollment watcher remain the sole transport;
a watcher is attention, not proof of worker execution or completion.
