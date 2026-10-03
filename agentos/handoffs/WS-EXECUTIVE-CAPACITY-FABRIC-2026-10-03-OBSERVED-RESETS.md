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
    result: 107 passed and 37 subtests passed; includes 25 new test methods over the base owner suite.
  - claim: Production changes preserve the broader Codex family.
    command: pytest tests/test_codex_runner_budget.py tests/test_codex_lanes.py tests/test_admin_codex.py with normal repository conftest.
    result: >
      Final campaign: 345 passed and 37 subtests passed in 37.33s, with normal
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
Native review request5966663297 received the Codex bot eyes acknowledgement;
no terminal review or native summary was observed at the latest read. Do not
start a second reviewer or let an old-head result approve this subsequent repair.

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
