# Defensive rotation: opted-in notification consumer

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE. Date: October 23, 2026 UTC. Status: implemented and locally qualified; independent composite review, hosted CI, source-to-outbox delivery and production acceptance remain open. No live user preferences, database rows, source flags or emails were changed by this work.

## What is implemented

The existing preferences owner recognizes `sector_rotation_relative`, and the existing bilingual account panel exposes a Defensive leadership changes checkbox. No default opt-in or selected categories were added. Selecting a category does not enable email delivery. Existing account version/acknowledgement and save paths remain authoritative.

The pure `lib/rotation_observation_notification.py` validates the existing frozen observational payload contract. It requires source `macro.rotation_observation.v1`, authority `notification_only`, a declared observed-change/reversal/correction/withdrawal kind, bounded identifiers, distinct strict market symbols, real source/session dates, timezone-aware observed/expiry timestamps, and typed finite two-session returns with consistent relative-wealth arithmetic. Withdrawals explicitly carry null values; reversal/correction/withdrawal carry an earlier, different observation ID. Source/date/clock/calendar uncertainty is unevaluable, not measured zero or an all-clear.

Its time gate uses the existing US cash calendar, including the existing settlement policy, holidays and half-days. A measured source must be the expected completed session at observation time. At delivery time that session must still be current and the notice must be before its expiry. Exact expiry is suppressed. The mail composer does not consult its own hidden clock.

`app/mailer.py` has a deterministic bilingual branch for this category. It shows both absolute legs and relative wealth in percent units, distinguishes the source session from the observed timestamp, labels data withdrawal as unavailable evidence rather than a disproof of the market thesis, and uses the existing static dossier target `sector_central.html#rc-events-mount`. It does not claim the user authored a thesis, holds either security, has a calibrated crash forecast, or has received a leverage recommendation. Caller-provided URLs, labels, advice and sizes do not originate its message.

`engine/alert_delivery_drain.py::decide_row` applies this category's strict contract and time gate within the existing preference, suppression, entitlement, quiet-hour and effect-handling pipeline. Malformed/unevaluable observations do not send; expired observations use the incumbent suppression status. This is not a new sender, queue, schedule, retry registry or delivery service.

## Original worker recovery and adjudication

Original builder `defensive-rotation-notification-consumer-20261023` returned TERMINAL rc0, response SHA256 `9442c67e8c136f250a68ff544db24cf476e1ebb5c2bdeb7904c9898f7b1c21c6`. Its retained response omitted the full helper and tests, so that response alone was not sufficient for source integration or acceptance.

The parent retrieved the complete original diff through the already-configured `mmx-ubuntu3` SSH identity, with BatchMode and strict host-key checking. The exact original scratch was `/home/ubuntu3/lane_scratch/dr3-rot-notif`, not a newly created or replacement worker. No remote source was edited. The scratch's local baseline `e6e7a46c91f2026c765bbb5690a24fd8b472c44e` was not assumed to be the canonical revision: all ten relevant preimages were compared against Macro `2a963d70915728b3c73debd18769e836055044af`, including proof that both new files were absent at the canonical base. Those same source preimages were unchanged at the parent source-continuity carrier.

Recovered original diff: 132,582 bytes, SHA256 `735e1511c9f743a94d5032d8cd87d4cc53c1b7d7c413825a401f18dbbd652288`. It contains the ten declared source/test paths, no binary patch, rename, deletion, executable mode change or unexpected path. The only application precheck failure was an absent sparse-checkout copy of `site/account.js`; materializing the exact HEAD blob, without regenerating it, resolved that. `git apply --check` then passed before the original patch was applied once.

The parent reproduced **525 passed** for the recovered consumer suites. That green run did not constitute acceptance: additional discriminating tests exposed problems not covered by the worker's tests. The original unmodified worker return remains NOT_ACCEPTED as a whole. The current candidate includes the repairs below and still requires independent review.

A separate read-only artifact-recovery commission was issued with a stale, incorrect scratch path and incomplete test-path list. That was a parent briefing error, not evidence the actual original artifact was missing or the worker lacked general source access. Its result is not relied upon. Do not retry, reconstruct or replace the already recovered implementation; preserve/reconcile that read-only request separately.

## Parent repairs after recovery

- Both-negative legs are relative shelter only when the defensive leg actually fell less. Falling more is explicitly negative in both absolute and relative terms; equal losses have no relative advantage. Flat legs and equal gains are not mislabeled as falling or relatively weak. Directional comparisons use the verified absolute legs, so a tolerated rounding residual in relative wealth cannot create a false advantage.
- Integer-to-float overflow and UTC-normalization overflow are handled as invalid/unevaluable inputs rather than escaping the drain. Instrument matching covers the entire string, including rejection of trailing newlines. Calendar return types, explicit nullable withdrawal fields and self-referential prior IDs are checked.
- The evidence link targets the existing static `rc-events-mount` anchor, not an asynchronously inserted element.
- The actual account click handler previously rebuilt categories from only the checkboxes rendered in that panel. That could erase `fif_saved_issuer`, whose control belongs to another surface. It now preserves acknowledged categories not represented by the current controls. An executable Node test invokes the real handler and verifies both adding and removing rotation without changing saved-research selection or enabling email.
- New pure and integration tests run in the incumbent support-email CI job. The existing ratio-lens job's dependency scope was widened to include the calendar and the builder's existing imports after hosted contract-delta reported missing trigger coverage. No gate was weakened or bypassed.

## Executed verification

Recovered original consumer: 525 passed. Corrected consumer plus 38 independent integration regressions: **563 passed**. The added cases cover underperformance during two-leg declines, equal/flat outcomes, tolerance boundaries, huge integers, full symbol matching, UTC overflow, null-field presence, self-reference, calendar uncertainty, fixed navigation, the real source receipt through the actual mail composer, data withdrawal, and the real account preference click handler.

Combined source, builder, ratio, rotation, consumer, preference, drain and mailer regression:

```text
python3 -m pytest -q \
  tests/test_rotation_observation_state.py tests/test_rotation_observation_builder.py \
  tests/test_rotation_observation_notification.py tests/test_rotation_observation_integration.py \
  tests/test_rotation_early_context.py tests/test_rotation_events.py tests/test_rotation_events_v2.py \
  tests/test_oracle_ratio_lens.py tests/test_rotation_role_retention.py tests/test_rotation_flow_pit.py \
  tests/test_account_prefs.py tests/test_alert_delivery_drain.py tests/test_mailer.py \
  tests/test_mailer_alert_template.py tests/test_mailer_held_material.py tests/test_alert_prefs.py
```

Result: **871 passed, 2 existing expected failures, 4 existing deprecation warnings**, exit 0. Both account assets are byte-identical and Node syntax checks pass. The incumbent portable CI manifest validates all 338 jobs. The local contract-delta gate reports zero findings after the dependency-scope repair. These tests use controlled fixtures; they do not prove a live message was sent.

Machine identity/result receipt: `research/evidence/defensive_rotation_observation_20261023/consumer-verification.json`. The earlier `verification.json` remains a historical receipt for the source-only candidate at c7ae9df1bc30759f6947e11be156ace4f2e29c66, not an assertion that every current file retains the old hash.

## Exact remaining delivery obligations

The source recorder and the notification consumer now speak the same tested payload contract. They are NOT yet joined by a production subscriber/outbox bridge. Keep the recording flag absent and this PR in draft until the next bounded integration and independent review are complete.

The next consumer must use the existing identity/preferences and outbox owners, not introduce a new directory or queue. It needs complete, fail-closed subscriber pagination; an explicit subscription activation boundary so a newly opted-in user is not sent an older event as a new one; deterministic per-user fire-event identities; and recovery of still-eligible canonical receipts after enqueue failure. A malformed roster is unknown, not zero subscribers.

The current drain's read/decide/send sequence also requires a verified supersession boundary. A producer PATCH to suppressed does not prove a selected or in-flight email was cancelled. Reuse the incumbent claim/transport mechanism where possible; any necessary extension belongs to that same outbox/transport owner with an independently reviewed compatibility contract. Do not invent a parallel lease, retry queue, future-defer cancellation hack or claim an in-flight delivery can be recalled. Later corrections must retain the original effect and provenance.

Finally qualify the actual single-writer source lane, current source data, hosted CI, normal source release, authenticated opt-in, canonical event/outbox identity, real transport receipt and opening the correct dossier. A preference checkbox, rendered email, mocked sender, local test suite or green PR alone is not full source-to-user acceptance. Alpha-driven portfolio sizing, options qualification and prospective prediction research remain separate obligations in the main delivery plan.

## Exact-head review and final local freeze

The source-only independent review of c7ae9df1bc30759f6947e11be156ace4f2e29c66 returned ACCEPT_FOR_SCOPE, response SHA256 `e528144cba2d1834b9ab859d19a49b3b00a6747d61147d9a223cd89556b63819`. The parent verified all four returned source/test blob identities and zero current diff across the source, builder, tests and calendar. The reviewer reproduced 166 focused tests, the original 492-pass/2-expected-failure regression and 26 additional adversarial cases. It identified no blocking source defects and noted historical calendar-version coupling as a pre-activation consideration. This accepts only the original source slice, not the new consumer or full programme. Its CI-binding statement is qualified by the subsequently observed and now repaired contract-delta trigger gap.

The current combined candidate was frozen by hashing all sixteen changed source/test/CI files before and after a fresh regression run. Both hash sets match; the actual run reports 871 passed, 2 expected failures and 4 warnings, exit 0. The machine receipt was written from that command result rather than reconstructed from conversation counts. Earlier source-only and consumer-only receipts retain their own scope. Independent review of the new composite is still required.
