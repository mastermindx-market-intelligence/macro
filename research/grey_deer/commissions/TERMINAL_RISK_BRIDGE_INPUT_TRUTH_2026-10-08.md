# Terminal risk bridge input-truth implementation plan

Program: WS:GREY-DEER-RISK-INTELLIGENCE / MAS-258 / Macro #8128.
Parent: ALERTFUL_RISK_RADAR_MASTERPLAN_2026-10-08.md.
Status: current Chairman-authorized bounded implementation, not statistical or capital promotion.

## Goal and architecture

Prevent Terminal's existing legacy market-risk bridge from labeling future, malformed, producer-stale or invalid scalar inputs as fresh/live usable evidence. Repair the existing pure projection in place. Do not introduce a new feed, alert engine, score, entitled payload mirror or policy owner.

Source: mastermindx-market-intelligence/mastermind-terminal at d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a.
Source path: ingest/pull_macro_risk.py (blob 51fa6e14558d411f6936f3de58dff502470462b3).
Existing tests: tests/test_market_risk_bridge.py (blob 501be914643f3fa0a3af1d5d1b50041f53bed5be).
Baseline verified on the admitted native Terminal review workspace: 17 passed, zero skipped.

This is independent of the specifically restricted Macro #8132 warning-module execution, Chromium, E02/Chronicle setup and other original-target actions. None of those may be copied, imported, executed or delegated as part of this lane.

## Contract

1. The existing market_risk/v1 schema and is_display_only=true remain. No forecast or action permissions are added.
2. Date freshness accepts an actual date or exact YYYY-MM-DD string. The source contract is a settled session date, not a timestamp. Missing, malformed, impossible and future dates are stale. Preserve the current five-calendar-day budget and its inclusive threshold; changing to a session calendar is a separately versioned integration task.
3. An explicit source stale=true cannot be made fresh by a recent as-of. An invalid explicit stale marker is unverified/stale, rather than truthiness-coerced. An absent marker retains legacy date-derived compatibility for the nightly source.
4. realtime=true requires actual boolean true for both source realtime and live_active, and non-stale evidence. False, missing, numeric and string lookalikes never assert realtime.
5. Numeric projection admits finite real numbers and finite numeric strings; booleans, malformed strings, non-finite floats/strings and overflow yield null. Zero remains legitimate. Preserve integer representation where input is an integer and existing four-decimal rounding for float input. Do not change scoring or clamping policy.
6. Keep the last observed risk words/score when marked stale; do not fabricate a calm state. This does not implement retained-warning episode semantics or establish that a stale historical warning is current.
7. Do not mutate inputs. Output must be serializable with allow_nan=false for the tested scalar positions. No collector, external source fetch, public payload, entitlement, portfolio, ranking or automatic exit is changed by tests.

## Files and test sequence

Create tests/test_market_risk_bridge_input_truth.py. Test future/malformed/whitespace/date-prefix clocks; exact date and zero/boundary controls; producer stale true and invalid markers; strict realtime booleans; NaN/infinity/boolean/overflow scores in the primary, radar and component slots; unchanged input; bilingual and display-only compatibility.

Run new tests against the unchanged source and retain actual failure count. They must fail from the present behavior, not fixture/setup errors.

Patch only ingest/pull_macro_risk.py: strict source-session parsing, stale provenance preservation, finite numeric normalization, and realtime admission. No new dependency; use the standard library.

Run existing and new test modules together, then script-style import from ingest and Python compilation. Inspect the exact diff and source hashes. A subsequent review may add a directly relevant edge-case regression, but unrelated transport/schema/UI redesign is out of this repair.

## Delivery and stop conditions

Source carrier: one new bounded Terminal GitHub branch/PR from the pinned source; no incumbent branch takeover. Native operation-owned workspace is a validation copy, not a second publication owner. Verify published blobs match tested content.

Independent review and required CI remain release gates. No native reviewer or host-qualified pool worker is presently established; do not invent an approval. No merge/deploy/live proof is claimed from unit tests. The larger entitled Grey Deer Terminal mirror remains a separate GD-8B integration, not a public market_risk.json wholesale copy.

Routing: C1_ROUTINE_BOUNDED, material impact, low ambiguity, routine reversible source risk. NO_ELIGIBLE_PRE_EFFECT_WORKER: the existing pool selected MiniMax for census but its host placement returned NO_HOST_ELIGIBLE/UNPROVEN; no worker was started. The principal retains the short, directly testable repair. No Codex/Work or Vercel is used.
