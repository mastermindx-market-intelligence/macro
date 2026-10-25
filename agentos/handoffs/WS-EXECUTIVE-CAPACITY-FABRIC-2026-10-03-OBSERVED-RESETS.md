---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/codex-observed-reset-refresh-20261003-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Make the existing Codex lane consume fresh provider-initiated resets without
  predicting gifts, restoring stale schedules or inventing reset entitlement.
state_before: >
  The loop already fetched native limits before its gate, but an older reply
  could overwrite a fresh refill and re-block useful work. Missing or malformed
  native windows could normalize to N/A. Parent all-account integration is held.
changed:
  - path: engine/codex_lane/budget.py
    what: Ordered complete snapshot updates, bounded pause clearance and retention of real failures with the latest accepted clock.
  - path: engine/codex_lane/runner.py
    what: Strict native normalization, named-bucket precedence and optional provider permission preservation without account-ID export.
  - path: tests/test_codex_runner_budget.py
    what: Regression, fake native wire and actual loop-consumer cases in the existing PR code-gate suite.
  - path: research/CODEX_AUTOMATIC_RESET_OBSERVATIONS_2026_10_03.md
    what: Provider evidence, existing-owner algorithm, compatibility and explicit live-proof ceiling.
verified:
  - claim: A delayed exhausted snapshot used to undo a fresh gift.
    command: Temporary-root reproduction with actual note_result, note_rate_limits and can_run at a fixed clock.
    result: Original source allowed after refill, then denied at 100 percent and restored the older deadline after the delayed reply.
  - claim: Current targeted owner suite covers the repaired observations and actual loop consumer.
    command: pytest --noconftest tests/test_codex_runner_budget.py with isolated basetemp and no provider calls.
    result: 113 passed and 59 subtests passed; includes native-reader and real-loop omission regressions.
  - claim: Production changes preserve the broader Codex family.
    command: pytest tests/test_codex_runner_budget.py tests/test_codex_lanes.py tests/test_admin_codex.py with normal repository conftest.
    result: >
      Current omission-repair campaign: 351 passed and 59 subtests passed in 37.67s, with normal
      conftest and isolated basetemp. The preliminary 338-pass campaign had four
      inherited temporary-cleanup warnings; its log is preserved.
  - claim: The existing reset planner removes a proposed banked reset after fresh gifted capacity.
    command: Source-pinned synthetic replay of Macro8255 head497bc35 through preview_codex_resets.
    result: PROPOSE_BANKED_RESET_THEN_RUN becomes RUN_CANDIDATE; banked inventory is unchanged, both digests change and live_admission remains false. No native calls or reset effects.
unverified:
  - claim: The patch is installed and all accounts recover from real promotional resets.
    what_would_verify: Exact accepted release, real account binding, qualified native reads and original-parent work consumption through existing owners.
unresolved:
  - New source needs exact-head review and hosted checks; no release or installed activation follows from local proof.
  - Macro8255 remains subject to its original review5389563572; its latest native497 review returned no major issues.
  - A resolve call for inline thread PRRT_kwDOS4LjIs6okiIg lost its response; same-carrier readback still showed unresolved, and no retry was issued.
  - Mastermind1158 merged as29a1e89975be319e7fc955283e048c34c2364dff through the protected queue; installation remains unproven. Its clean original workspace remains preserved by the canonical cleanup observer after branch deletion.
next_actions:
  - Complete source review and hosted acceptance, then use the normal release path with exact-head and current-base checks.
  - Consume the original1158 queue result and8255 review/check outcomes without duplicating workers or replaying unknown effects.
  - Existing Provider Control and Executive owners retain enrollment, global placement, claims and reset execution proof.
do_not_redo:
  - Do not recreate a gift ledger or predict guaranteed grants; use native absolute observations.
  - Do not replay the denied consumer bridge, CI-manifest or7116 publication actions.
  - Do not erase real errors or charge banked resets based solely on a balance increase.
danger_areas:
  - This is a single-account lane correction, not multi-writer CAS or global account identity/admission.
  - API token activity is not remaining included token entitlement; model/effort/speed burn still requires clean measured intervals.
---

The model label is the existing Sol organizational lane, not an attestation of
served model or UI mode. Those remain unverified. Source base is
04967751bd479f0cbda0ca3d813e604e304f3945; protected procedure pin is
Mastermind bdf2a972e68a70270c24d4b5d61a4d60edc4f288.

Evidence: /Volumes/Mastermind/evidence/codex-observed-reset-refresh-20261003-sol-001.
No provider reset, auth repair, account switch, runtime job, service change or new
watcher was performed. Parent mission remains incomplete.

## Partial-payload repair and current source continuation

Initial source3820d093e4b69f181975d83e2706ef2e3e7f4dac is published on Macro8311.
Native review request5966663297 completed at07:25:11Z on3820d09. Its concrete
P1 finding4172147212 also applies to subsequent e6c1314e source and is consumed
in reply4172177478. That review operation is terminal. No old-head result accepts
the subsequently repaired source; a new exact-head review is still required.

A further direct discriminator found that an explicit ordinaryUsageAllowed signal
could disappear when quota fields were incomplete. The native consumer now
returns only the validated permission and observation time in that case; missing
measurements do not become N/A. The existing budget owner denies that partial
packet even with permission=true. Invalid numeric overflow cannot erase a denial.
Original partial-payload checks: six failing subtests; overflow checks: two failing
subtests. Repaired full existing family345PASS/37subtests; no native provider call.
Only the same five source/test/document paths remain in scope.

The actual1158 queue CI37104300662 and frontend37104300678 passed at29a1;
reviewed and merged tree0fe475ba40ff7fd7f5d65df1ce12e5a1a09a12b5 is identical.
Release receipt SHA2565109d2fbb94b146cee899d148fe9189dcaaa437ed552ef602f0c9fee8c7bcdc7.
Mastermind703 return5966720657 preserves installation/account gates. Macro8255
CI37102216371 is now SUCCESS; original reviewer adjudication5966703370 remains
requested, not accepted. No pending reset, source or runtime effect was replayed.


## Optional-permission omission repair

Current protected procedure pin3959aad974f15760ad7a53ab2d7a7ddfcd864ae2 has no
governing procedure/delivery drift from the prior29a1 source. On the same8311
branch, the completed reviewer correctly identified that an omitted optional
permission field caused an entire newer restrictive reading to be discarded.
The actual loop could therefore retain0percent/allowed after a100percent reading.

The repair accepts newer valid meter values and provider reset dates while
retaining the prior permission signal. Known false/null permission is not erased.
A missing field cannot use a carried true value as new evidence to clear a known
newer-protocol pause. Explicit later permission plus a complete fresh reading can
clear the pause normally. Only _apply_rate_limits_to_state and note_rate_limits
change in production; no runner, account, global allocator, release policy or
installed state is changed by this increment.

New discriminators on e6 source:24FAIL/3PASS/2passing subtests; updated owner
113PASS/59subtests; normal-conftest family351PASS/59subtests. Counts overlap.
Evidence is in restrictive-red.log, restrictive-green.log and restrictive-family.log
under the existing evidence directory. The existing native normalizer -> loop ->
budget path now refuses the field-less exhausted packet before any lane callback.
All evidence is synthetic and no provider call is made.

This continues the same source operation without source custody transfer; direct
repair is a bounded critical-path fix after a completed independent review. No
new worker was dispatched through readonly Executive, whose07:38:38Z read still
shows installedb3627c58/Macro88804ed, zero active Jobs/Attempts and no worker proof.
Original8255 formal review5389563572, denied7116/bridge/CI-manifest actions and633
uncertainty remain unchanged. Fresh publication/current-head review/CI are owed.
