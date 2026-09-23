---
workstream: WS:CI-MERGE-CONTROL-PLANE
session: claude/admin-baseline-scope-20260923
model: sol
ended_because: ci_handoff
mission: Restore the unchanged CI selection bounds without losing UK desk safety coverage so the existing Admin release can advance.
state_before: The UK desk's new standalone code job selected a 126th job for the Prophet plan-book probe, exceeding the unchanged 125 limit and holding Admin PR 7665 behind the shared baseline breaker.
changed:
  - path: .github/ci/legacy-jobs.yml
    what: Move the complete UK policy suite into the existing Brain Desks code gate; remove only the redundant standalone wrapper, retaining every suite invocation and gate family.
  - path: tests/test_ci_pack.py
    what: Guard the existing code owner and execute the real UK import scanner against a planted forbidden plan-book import.
verified:
  - claim: The new code-owner regression fails before the manifest repair and passes afterward; the real scanner still rejects a forbidden engine import.
    command: python3.12 -m pytest -q tests/test_ci_pack.py::test_uk_policy_suite_reuses_brain_desks_code_gate tests/test_ci_pack.py::test_uk_policy_global_import_guard_still_catches_planbook
    result: Before 1 failed and 1 passed; after 2 passed.
  - claim: Manifest validity, exclusive closure and the original three packing ratchets pass together.
    command: Eight explicit tests in tests/test_ci_pack.py, including test_curated_exclusive_scopes_cover_their_own_import_closure and test_exclusive_curation_narrows_ordinary_code_prs; exact invocation recorded on PR 7693 comment 5792899940 and baseline-qualification.log.
    result: Canonical sparse profile 8 passed in 240.09 seconds; full checkout 8 passed in 249.84 seconds. Full-tree probes 131/128/125 within unchanged 132/129/125 limits; weights 5800/5561/5567. All five UK dependency and safety probes still select the Brain Desks code owner.
  - claim: Every suite invocation retains its code/data gate and the UK suite source is unchanged.
    command: Compare the gate-and-suite Counter from git show HEAD:.github/ci/legacy-jobs.yml with the working manifest; assert the UK dependency set is retained and git diff on tests/test_uk_policy_brain.py is empty.
    result: All 2030 invocations retained; job wrappers 225 to 224; suite-preservation.json records the proof.
  - claim: The complete combined Brain Desks job passes with full checkout inputs and remains within its five-minute budget.
    command: Execute every python -m pytest command from the modified unrun-brain-desks manifest job, in order, using Python 3.12 and a single 300-second deadline.
    result: 262 + 53 + 117 + 87 = 519 passed, no skips; 67.3 seconds total. Exact commands and results in brain-desks-full-qualification.log.
unverified:
  - claim: This candidate is merged and restores the live baseline and Admin release.
    what_would_verify: Exact-head CI, current integrated baseline, existing merge-controller receipt, and subsequent authenticated Site inventory consumer proof.
unresolved:
  - Main baseline recovery, exact-head release and authenticated Site inventory acceptance remain pending; no live release is claimed by local qualification.
next_actions:
  - Publish this qualified candidate on its same carrier; consume full-gate-receipt.json rather than rerunning accepted local proof.
  - Publish one repair PR, consume exact-head checks and the current baseline, and use the existing merge controller without duplicate dispatch or retry.
  - After PR 7665 merges and deploys, verify authenticated /api/content/links with exact deployed source identity; keep negative fixtures isolated.
do_not_redo:
  - Do not raise the 132/129/125 job limits or the weight/pack budgets.
  - Do not narrow or remove the UK engine/scripts import scan; a Prophet import must still fail.
  - Do not move the UK suite back to data-only coverage or omit any of its tests.
  - Do not reuse the merged PR 7693 repair branch or put this repair into PR 7665.
  - Publisher PR 7768 and Content Studio PR 7609 live acceptance remain do-not-redo.
danger_areas:
  - The scanner's broad coverage is intentional; an exclusive scope omitting unrelated engine Python files would be a false green.
  - A passed PR pack is not a recovered main baseline, a merge, deployment or operator acceptance.
  - PR 7665's old local worktree is stale; preserve its existing remote carrier and custody.
prs: [7665, 7693, 7768]
---

# Admin release dependency: reuse the existing desk gate

Current Chairman intent continues the 54-route Admin mission. Protected procedure is
Mastermind `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1. Source base is
`acec95b438ac7044a2a2827393640342fb24fb0e`; operation is
`ADMIN-BASELINE-SCOPE-20260923`. No worker, provider or new control plane was started.

The new UK job in PR 7771 was correct to bring the complete suite into PR CI. Its
broad import prohibition also correctly selects the Prophet probe. Consolidation,
not suppression, restores the unchanged budget: the existing `unrun-brain-desks`
code job retains the full suite and already supplies all its dependencies. Only
PR 7771's standalone-job placement is superseded; its safety behavior and code-gate
coverage are preserved. Main baseline `35833157320` is the original 126-versus-125
failure; `35824722923` at `5197ec924ba4b1406f6b6d4621719943e5c54f5a` is the prior green.

Evidence stays in `/Volumes/Mastermind/evidence/admin-baseline-scope-20260923/` and
PR 7693 comment `5792899940`. The cumulative Admin continuation stays on PR 7609
comment `5789427638`. The parent mission remains incomplete; this handoff grants no
source custody, merge, deployment, retry, publication or trade authority.
