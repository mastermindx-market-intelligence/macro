# Defensive rotation: opted-in observation delivery

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE. Date: October 23, 2026 UTC. Status: consumer implementation commissioned; source transition/outbox integration and real delivery acceptance remain incomplete. This extends existing alert owners, not trade authority or a new notification platform.

## Verified gap and rejected audit shortcuts

At Macro source `2a963d70915728b3c73debd18769e836055044af` (existing alert code unchanged from `eb5f608851a8d3ea8181953a28f271ec846240dd`), `scripts/build_rotation_events.py` writes the existing rotation JSON and merges `rotation_events.to_alerts()` rows into `data/subsector_rotation/alerts.jsonl`. `engine/alert_triage.py` consumes that store. This is Alert Command Center visibility, not a per-user email delivery receipt. No rotation-specific outbox producer was found in the bounded source census.

`lib/user_prefs.py` currently recognizes only holdings_material_change, thesis_window and fif_saved_issuer. `engine/alert_delivery_drain.py:decide_row` requires a recognized selected category, explicit email opt-in, successful suppression/entitlement reads and quiet-hour qualification. A generic rotation observation is not a user-authored thesis condition or evidence of an open holding. Do not disguise it as either category.

Read-only Fabric audit `defensive-rotation-alert-path-20261022` returned rc0 / SHA256 `9885ee112aee1f40daea60d492799e670ece78b494229e240ab9b2319df0f5f1`. Its full return is NOT_ACCEPTED: two material claims were false or incomplete.

1. Adding a category to the API does NOT automatically add the account checkbox. `templates/account.js:alertPrefsGroupHTML` hardcodes the existing choices. Both API recognition and actual bilingual UI require integration.
2. The live outbox already has `suppressed`. The proposed far-future deferred-row cancellation workaround is rejected. Existing suppression semantics must be used and in-flight send uncertainty preserved.

## Live schema proof, not a proposed migration

The connected Supabase project discovery identified MarketIntelligence (`fsldfzlxyavsuwqbceod`, ACTIVE_HEALTHY). A single read-only catalog query inspected only `public.alert_outbox`/`public.alert_runs` metadata, constraints, indexes and RLS policies. No user rows, email addresses, credentials, DML or DDL were read or changed.

Observed live contract:
- Both tables exist and have RLS enabled.
- Outbox columns: id uuid, user_id uuid, alert_id nullable uuid, fire_event_id text, channel text, status text, payload jsonb, attempts integer, last_error nullable text, deliver_after/delivered_at nullable timestamptz, created_at timestamptz.
- `alert_outbox_status_check`: pending / deferred / sent / failed / suppressed.
- `alert_outbox_fire_event_id` is a unique index.
- Authenticated SELECT is restricted by `auth.uid() = user_id`; service_role has the existing ALL policy.

This matches the source reservation in `mastermindx-market-intelligence/mastermind-terminal`, `supabase/migrations/0013_alert_runs_outbox.sql`, blob `28a7f72af5726fb04bb9ef1bef1684564cdddf64`. Unlike the migration file alone, the catalog read proves these fields and constraints actually exist. No schema change is required for the bounded consumer contract.

Supabase public documentation was rechecked October 23. Current platform changes to default API exposure are not a reason to widen grants: existing object access and RLS remain untouched. Upcoming TLS changes concern old clients, not a reason to change this application's authorization or transport.

## Frozen DR3 consumer contract

Category: `sector_rotation_relative`. User label: Defensive leadership changes. No default opt-in. Existing account preference save/read, entitlement, suppression, unsubscribe, quiet hours and sender idempotency remain authoritative.

Payload source `macro.rotation_observation.v1`, authority `notification_only`. Types:
- `observed_change`: a newly observed descriptive change, not a forecast or buy instruction.
- `reversal`: a later observed change relative to a named earlier observation.
- `data_withdrawal`: evidence is no longer usable; this does not assert the market thesis was disproved.
- `correction`: explicitly supersedes an earlier observation without rewriting its delivered history.

Required fields: category/source/authority/kind, observation_id, pair_id, num, den, event_as_of, source_as_of, observed_at, not_after, values. Reversal/withdrawal/correction require previous_observation_id. Identity fields are bounded; instrument symbols are distinct, strict uppercase market symbols. No caller-supplied URL or prose can originate an email claim.

For measured kinds, values contains exactly the declared two-session measurement: integer sessions=2, finite numeric numerator_return_pct/denominator_return_pct/ratio_return_pct (booleans and strings rejected), absolute returns greater than -100%, relative wealth identity within 1e-6 percentage points. Data withdrawal has values=null; old positive returns are never presented as current evidence.

Date rules use strict real ISO dates and aware ISO datetimes. The existing `lib.us_cash_calendar.expected_last_session` is the calendar owner. event_as_of must equal its result at observed_at; measured source_as_of equals event_as_of; a withdrawal can refer to older source data. The sender's injected current time must not precede observed_at, must be before not_after and must still map to event_as_of. Bad structure/calendar fails closed as unevaluable. Expired/superseded-session observations use existing suppression, not another retry lifecycle. Weekend/holiday/half-day behavior comes from the existing calendar, not a new weekday approximation.

Email composition is deterministic and bilingual. Show both absolute legs and relative wealth, source date separately from noticed time, and a fixed link to `https://www.mastermind-x.com/sector_central.html#rc-early-context`. Both legs falling must be called relative shelter only. The email says the user subscribed to observations, not that they authored a thesis or hold either security. It does not state measured capital flows, crash probabilities, recommended allocation or leverage.

The consumer builder is `defensive-rotation-notification-consumer-20261023`, root `defensive-rotation-20261022`, parent `chatgpt-defensive-rotation-ceo-20261022`. It may edit/test only isolated scratch and return a patch; no shared source, database, SMTP or GitHub writes. Parent integrates and obtains independent review. Current request delivery is not proof of implementation, execution or acceptance.

## Next source integration: required decisions and invariants

The source producer must remain the existing rotation owner. `early_context` is currently a stateless descriptive reader appended AFTER `run_nightly` has already written state. Adding a new field without addressing this ordering would lose continuity. The next implementation must preserve old confirmed-event identities and behavior while retaining accepted per-pair observations in the existing owner, not a second defensive state file or schedule.

Use the existing state/ledger and outbox with an explicit, reviewed transition contract:
- First eligible observation seeds a baseline; it must not send the entire historical roster as a first-run alert storm.
- A source-current subsequent observation can record an actual descriptive change. Unchanged classifications may update source freshness without repeated emails. No predictive severity is inferred.
- Same-session source revisions are corrections, not newly discovered historic pivots. Withdrawal and restoration retain explicit provenance. Out-of-order observations cannot roll state backward.
- Replay, scratch art_dir, stale store, future timestamps, mixed source basis, partial pair windows and unknown lineage/availability cannot manufacture actionable current events. The producer must document which availability evidence is sufficient for notification; UNKNOWN is not silently upgraded.
- Canonical observation receipts must be durable before delivery. An outbox failure after state advancement cannot permanently drop an alert: the existing producer must be able to replay still-eligible canonical receipts, using deterministic per-user fire_event_id and the existing unique index. No parallel retry queue or local sent-state registry.
- Source withdrawals should suppress not-yet-sent eligible outbox rows using existing semantics. A message already handed to transport cannot be recalled by changing a database status. Preserve the original uncertain/sent effect and issue a clearly linked correction when appropriate; do not claim cancellation proof from a PATCH alone.
- Scheduling remains the existing rotation build and alert drain. A new deployment flag may gate the new category's effects, but it must not create another scheduler, watcher or daemon. Dormant means no user reads, enqueues or sends for this new lane.

These are acceptance requirements, not claims that the source/outbox bridge already exists. The exact source transition schema and atomicity/retention behavior still require implementation review before production activation.

## Release proof

Consumer tests must cover strict payload/time/return validation, all kinds, both-down cases, both languages, hostile inputs and legacy compatibility; preference/category rendering and save/read; entitlement/suppression/quiet hours; no-network mocked sender invocation; and paired asset identity.

Producer tests must add first-run suppression, idempotent rerun, state continuity through the old writer, correction and withdrawal ordering, exact event identities, stale/future source, history/replay isolation, DB read/insert failure, unique-conflict reconciliation and interrupted delivery.

Full proof remains an authenticated user opting into this exact category, a naturally eligible current source transition, one canonical event, one correctly scoped outbox row, existing drain and mailer receipts, and opening the correct dossier. Mocked sends, a database catalog read, a rendered email, a green PR or a manually seeded historical observation do not establish live delivery. No real notifications have been sent by this mission.
