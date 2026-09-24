---
workstream: "WS:PROPHET-US-V4-RECOVERY"
session: sector-release-options-scope-20260924
model: sol
ended_because: ci_handoff
prs: []
mission: Restore the normal declared-scope validation needed to release sector/Prophet fixes, without weakening the existing Options or CI contracts.
state_before: Current Options code job names the source-note suite but omits its literal exclusive path, so native manifest loading and PR contract-delta fail before feature tests.
changed:
  - path: .github/ci/legacy-jobs.yml
    what: Add one omitted source-note test path to the existing Options job; all commands and other jobs unchanged.
  - path: tests/test_options_skew_source_note.py
    what: Add actual code-owner/full-invocation/scope regression; fail on the original omission.
verified:
  - claim: The full affected suite combination passes after a discriminating RED-first check.
    command: python3 -m pytest -q tests/test_options_skew_source_note.py tests/test_options_payoff_lab_consumer.py -p no:cacheprovider
    result: 30 passed on Python3.14 and overlapping30on Python3.12; no skips.
  - claim: Native manifest loading and the changed job's explicit dependency closure are valid.
    command: load_legacy_jobs plus infer_job_scopes for the single options-payoff-lab-consumer owner; compare immutable-base YAML against candidate.
    result: 227jobs accepted;18concrete paths covered,0missing; only one literal addition, all execution/dependency/timeout and other-job mappings identical.
unverified:
  - claim: Full hosted checks, independent review, merge and production recovery.
    what_would_verify: Exact-head hosted/review receipt and existing-owner source release followed by the normal producer-to-consumer proof.
unresolved:
  - The original shared #7802 locked source remains its existing owner and has newer main-composition conflicts; this dependency does not resolve or replace that operation.
next_actions:
  - Consume exact-head hosted CI and an independent source review; return the immutable correction to the existing shared release owner.
  - Keep original sector/Prophet source/publication acceptance separate; no duplicate dispatch or forced merge.
do_not_redo:
  - Do not change the 125/132/129 job ceilings, weight budgets, parser behavior or UK scanner coverage.
  - Do not replay the platform-blocked #7669 code-registration completion or the old UK-scope worker commands.
danger_areas:
  - Manifest-read success is not a full main-baseline or live product outcome.
  - Shared source custody and original release holds remain binding.
---

Protected procedure Mastermind@a0b31114d5d645e73da1333f7258092034a54c34.
Original same-carrier dependency: claude/sector-release-options-scope-20260924.
Source base ca745ef0d7e3294857f1231e93d480c2585b1127.
Current Chairman intent covers the US sector/Prophet mission; direct bounded
implementation reason CRITICAL_PATH_SHORTCUT. Existing shared CI owner #7802
was notified in comment5806062288 before source modification. This adds no new
job, control plane, option signal, price, entitlement, ranking or entry authority.
Detailed proof lives at research/sector_release_options_scope_20260924/.
MISSION_COMPLETE:false. Production acceptance remains owed.
