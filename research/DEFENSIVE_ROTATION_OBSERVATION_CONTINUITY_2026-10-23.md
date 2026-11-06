# Defensive rotation: durable observation continuity

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE. Date: October 23, 2026 UTC. Source base: `3b5058cf10a6791d5e8097e514af0c8ff15b9b59`. Operation: `defensive-rotation-notifications-20261023`.

Status: BUILT_AND_LOCALLY_TESTED, DEFAULT_DISABLED, NOT_INDEPENDENTLY_REVIEWED, NOT_DEPLOYED. No user lookup, outbox insertion, notification send, trade, forecast qualification or portfolio-sizing authority was exercised. This is an additive source-continuity slice under the existing rotation owner, not completion of the notification programme.

## Why this slice is necessary

The display slice in Macro PR #10103 exposes existing early two-session observations. Its research identified a retained October 8 observation in an October 9 repository build: XLP rose 1.980434% while SMH fell 3.988930%, yet the confirmed-event arrays were empty. That artifact is evidence of recorded early information, not a historic user-delivery receipt. The full source evidence and interpretation are in `research/DEFENSIVE_ROTATION_REPLAY_2026-10-22.md` at `eb672786de7967a396248cc9272bd72ca9eba12f`.

An email consumer alone cannot turn a stateless snapshot into a reliable notification. The source needs to distinguish the first baseline, a later measured change, a source correction, unavailable data, and repeated unchanged input. It must retain the original observation time, recover after interrupted writes, and never promote a replay into a live pivot.

## Incumbent owners only

`engine/rotation_events.py` remains the source owner. The implementation extends its existing `data/rotation_events/state.json` with `early_observations`, and appends typed `early_observation` receipts to its existing `events.jsonl`. There is no separate watch file, event ledger, scheduler, queue, sender, state service or retry registry. Confirmed lifecycle identifiers and created/closed event counts remain distinct.

`advance_early_observation_history` is a pure descriptive projection. `record_early_observation_history` is the existing nightly owner's guarded persistence operation. `scripts/build_rotation_events.py` calls it only AFTER the normal rotation JSON has been written, and only when all admission conditions below hold.

The same historical reader, `read_ledger_history`, explicitly validates early-observation receipts and reports `excluded_observation_receipts`. They are not counted as confirmed created/closed lifecycle events. Unknown event types and malformed receipts still fail closed. `closed_recent` remains a confirmed-closure reader. This compatibility repair is covered by mixed-ledger tests; it is not silent dropping of newly encountered history.

## Descriptive contract

Only existing registered `defensive_sector` comparisons are eligible. The producer's schema, definition and display-only authority must match. Two-session windows require explicit eligibility, strict source/request/value/end dates, the exact two-session start from the existing US cash calendar, finite typed percent values, absolute returns greater than -100%, and relative wealth consistent within 1e-6 percentage points. Booleans, strings, nulls, non-finite and overflowing numbers cannot become measured zero. Duplicate aliases or a pair ID reused for different instruments abstain rather than add evidence.

The existing `lib.us_cash_calendar` owns trading sessions, holidays, half-days and settlement cutoffs. No second calendar was added. A future source does not advance history. An older observation clock cannot roll it backward. Missing, malformed and stale source evidence is unavailable, not a market reversal.

Receipt kinds:
- First eligible observation: durable baseline, no notification.
- Later source-current change in the signs of the two absolute legs or relative wealth: observed change, or reversal when prior positive relative/absolute evidence is lost.
- Same-session revision of a previously notifiable observation: linked correction. Revising an initial baseline does not invent a prior alert.
- Loss of usable evidence: data withdrawal with values=null; old positive values cannot appear as current.
- Restored evidence or an unobserved multi-session gap: seed continuity again, not a newly asserted market pivot.
- Same evidence: no duplicate receipt; new session with unchanged directional classification can record history without another notification.

These rules describe what changed. They are not calibrated persistence thresholds, a crash forecast, a conviction score, return prediction, ranking or permission to use leverage. Very small sign changes can still be observations; any eventual alert severity/cadence policy must be explicitly tested and must not disguise them as strong trade signals.

Notification-shaped receipts reserve the already documented `macro.rotation_observation.v1` / `sector_rotation_relative` / `notification_only` contract. They include the prior observation identity, source session, actual observed time, verified two-session values and a 24-hour maximum age. A future consumer must ALSO enforce the current expected session and its own preference/entitlement/suppression/quiet-hour gates. This code does not enqueue or send these payloads.

## Crash recovery, not a second retry owner

The canonical observation identity is derived from its semantic fingerprint and predecessor, not the retry's clock. The writer validates and folds the existing ledger before computing a new observation. Therefore an interruption after append but before checkpoint is recoverable even when the next source input differs: the original receipt remains the predecessor, rather than creating two competing histories or restamping its first observation time.

Receipts are appended and flushed before the existing state checkpoint is atomically replaced. Malformed/truncated JSON, hash/content conflict, missing predecessors, a ledger fork, checkpoint disagreement, invalid clocks or a missing backing receipt fail closed. Legacy fields are preserved. Preimage checks detect observed state/ledger drift; they are NOT a cross-process lock. The incumbent single-writer nightly admission remains a required production condition and must be verified before activation. No new lock service was introduced.

A failure is exposed as unavailable, with receipt count unknown rather than falsely zero. A later original-owner run reconciles the ledger. The outbox bridge must read still-eligible canonical receipts, not only the current run's new rows; otherwise a database failure after source advancement would lose an alert. That bridge is not implemented in this slice.

## Dormant integration and effect boundary

Default: `ROTATION_OBSERVATION_RECORDING_ENABLED` absent, or any value other than exact `1`, causes immediate disabled return before path/configuration reads. Setting the flag has NOT been performed in production.

Even with the flag set, the existing builder refuses observation advancement for:
- an explicit generated timestamp (historical/replay build);
- any `art_dir` override (scratch build);
- a non-nightly collection lane;
- noncanonical data or site paths.

When admitted, observed_at is the actual time after the existing JSON publisher returns, not the source bar's date or build-start time. The existing rotation/alert build and schedule are retained. The feature does not run a daemon, watcher or extra collector.

## Executed verification

Final local regression command:

```text
python3 -m pytest -q --basetemp /tmp/rotation-notifications-regression-final \
  tests/test_rotation_observation_state.py tests/test_rotation_observation_builder.py \
  tests/test_rotation_early_context.py tests/test_rotation_events.py tests/test_rotation_events_v2.py \
  tests/test_oracle_ratio_lens.py tests/test_rotation_role_retention.py tests/test_rotation_flow_pit.py \
  tests/test_account_prefs.py tests/test_alert_delivery_drain.py tests/test_mailer.py \
  tests/test_mailer_alert_template.py tests/test_mailer_held_material.py
```

Result: **492 passed, 2 xfailed, 4 warnings**, exit 0. The two expected failures were not changed into passes. The warnings concern existing FastAPI lifecycle deprecations. The new source/builder suites contain 85 cases; focused source/builder checks initially passed 81 before four explicit mixed-ledger/corrupt-checkpoint regressions were added. The original account/drain/mailer baseline passed 189 tests before this work. All tests use isolated fixtures; no live users, DB or email transport were exercised.

The exact HEAD registry blob `data/oracle/ratio_pairs.json` was materialized in the sparse workspace and hash-checked, not regenerated. The new tests and builder path are registered in the incumbent ratio-lens job in `.github/ci/legacy-jobs.yml`; no scheduler or bypass was added. YAML parses, no duplicate paths were introduced in that job, and `git diff --check` passes. Independent review and hosted CI remain required; local tests do not substitute for either.

## Remaining integration and acceptance

1. Consume the ORIGINAL notification-consumer worker `defensive-rotation-notification-consumer-20261023` when its result is readable. Its grant owns preference/category, account checkbox, pure payload/time validation, mailer and existing drain integration; do not duplicate it or assume completion from a controller ID.
2. Design the source-to-outbox bridge using existing auth preference/delivery owners. `lib/user_prefs.py` has no bulk user iterator. An existing GoTrue page reader is `app.marketing_emails._auth_page`; its current fallback can turn a malformed wrapper into an empty roster. It must not be used unqualified or copied into a second identity directory. The subscriber read must preserve unknown-versus-empty, bounded complete pagination, explicit opt-in and current preference revalidation.
3. Preserve the existing sender's idempotency and uncertain-effect handling. The current drain reads/decides rows then calls send_fn; a source PATCH to suppressed does not prove that an already selected or in-flight email was cancelled. Solve and test the relevant stale/correction boundary in the existing owner before activation. Do not add a parallel send/retry plane or a far-future deferred cancellation hack.
4. Commission independent review of the composite source, consumer and exact dependency closure. Verify actual single-writer admission, required CI, ordinary release and rollback controls before enabling recording, then separately qualify any delivery activation.
5. Prove an authenticated opted-in user's natural source transition reaches one canonical event, one appropriate outbox identity, the existing transport receipt and the correct dossier. A mocked send, local test, recorded observation, green CI or merged PR is not this proof.

The Macro entry-card worker remains a separate unresolved original request, and direct SOXX/QQQ coverage plus qualified risk-budget/alpha-policy/option integration remain in the main delivery plan. This source slice does not silently declare those outcomes complete.
