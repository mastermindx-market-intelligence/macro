---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/event-intelligence-auction-20260917-sol
model: sol
ended_because: ci_handoff
mission: 'Advance the living Event Intelligence program through a first owner-native
  non-forecast auction/calendar context consumer; parent MarketOntology #6819 remains
  nonterminal.'
state_before: Non-modelled dates showed only event-risk metadata; the existing Treasury
  adapter discarded announcement terms and treated natural FRNs as nominal notes with
  a generic deadline.
changed:
- path: engine/event_calendar.py
  what: Preserve official terms, source and actual deadline; distinguish FRN/TIPS,
    duplicate and conflicting records; attach pure context projection.
- path: templates/dashboard.html.j2
  what: Compose every selected-date context alongside forecasts without another popup
    or feed; retain date/race behavior and fix light-theme title ink.
- path: engine/calendar_event_context.py
  what: Bounded bilingual reference playbooks and announcement facts; no fetch, model,
    forecast, store or trade authority.
- path: research/event_intelligence/auction_context_v1
  what: Source-bound natural-data local component browser proof across eight theme/locale/width
    cases.
verified:
- claim: The full focused calendar/selector/dashboard test set passes.
  command: python -m pytest tests/test_calendar_event_context.py tests/test_calendar_event_context_ui.py
    tests/test_event_calendar.py tests/test_release_radar_date_selection.py tests/test_dashboard_template_render.py
    -q -p no:cacheprovider
  result: 94 passed in 65.95s; real API contracts, null/conflict/hostile inputs, render/selector
    tests included.
- claim: The captured official-source projection works in the actual event component
    without a forecast.
  command: python research/event_intelligence/auction_context_v1/reproduce.py --out
    /tmp/mmx-event-intelligence-proof-final --browser <installed Chromium>
  result: 8 cases passed; 1440/390 x dark/light x EN/ZH, no page errors, keyboard
    and same-/cross-date behavior, no horizontal overflow. Manifest binds exact source
    hashes.
- claim: New import closure is covered by the existing CI owners.
  command: python scripts/check_contract_delta.py --base 60db17a8e6e59381f0648f110035b1cc513da638
  result: 0 introduced, 0 inherited after widening exactly the six reported job path
    lists.
unverified:
- claim: The candidate is merged and live in authenticated production.
  what_would_verify: Concluded exact-head hosted checks, required review, governed
    merge and existing production render; authenticated live browser reads the new
    source-bound terms.
- claim: Per-event LLM assessment and official auction results are implemented.
  what_would_verify: A later existing-owner vertical with release/result/correction
    receipts and qualified existing AI-consumer output. This slice is explicitly a
    reference guide, not that capability.
unresolved:
- Local contract delta is now 0 introduced / 0 inherited; hosted exact-head checks
  and independent review still required.
- No independent reviewer pickup is proven; no worker, runtime job or metered provider
  call created.
- Full local app correctly redirected to sign-in; component proof did not bypass auth.
next_actions:
- Commit/push this exact carrier and create the scoped Draft PR; keep deployment and
  review evidence separate.
- Obtain exact-head review and hosted proof, adjudicate only actual candidate failures,
  then execute the existing merge/render/live verification path.
- Advance official result/correction and grounded assessment composition through the
  existing RIC/F05/AI owners; preserve the full-calendar/history and learning mission.
do_not_redo:
- Do not rebuild the calendar, Chronicle event spine, provider router, private state
  or MarketOntology program.
- Do not reset/rebase/replace this carrier or historical RIC-F1; reconcile each on
  its original carrier.
- Do not use the June cached view-model to regenerate September production.
- Do not repeat the original missing-capability RED tests as a new investigation;
  evidence and method are recorded.
danger_areas:
- No projection is not no intelligence; reference context is not live/model assessment.
- Treasury closingTimeCompetitive and FRN flags are source contracts; CUSIP alone
  is not auction identity.
- No generated site/data changes, direct LLM invocation, price/WI fabrication, rank/size/trade
  authority or authenticated production proof is implied.
- 'Incumbent #7241 publication recovery and #7036 release-diagnostic semantics remain
  untouched.'
---

# Event Intelligence — implementation checkpoint

Mission: living event dossiers, not forecast-only calendars; shared deterministic
and grounded LLM intelligence across Mastermind. Chairman's current continuation
requests sustained execution without repeated confirmations. Preserve existing
MarketOntology A/B ownership and exact F05/RIC/Chronicle/provider owners.

Procedure pin: Mastermind 320f586126b7c82c843ef17612f12d40d20a42e0, skillpack 1.0.1.
Source base: Macro 60db17a8e6e59381f0648f110035b1cc513da638.
Carrier: claude/event-intelligence-auction-20260917-sol; isolated worktree under
macro-main/.claude/worktrees/event-intelligence-auction-20260917-sol.
Parent record: Macro #6819 comment 5722262696. No worker or Executive job created.
Direct bounded execution: no eligible pre-effect worker binding proven; no
competing auction-context writer found in the bounded open-PR/worktree census.

Implemented locally: calendar_event_context pure projection; official auction
metadata/source/time preservation; bilingual same-date renderer; reference
playbooks independent of model coverage; preserved forecast interactions.
RED: 15 producer tests failed and 5 UI tests failed for the absent capability.
Latest complete focused run: 94 passed; candidate render parity is now tested through actual Jinja into tmp_path, not a stale generated snapshot.
Full template/browser/source proof and publication are not yet accepted.

Tool/workspace reconciliation: original --no-checkout carrier had no index.
Same-carrier readback confirmed base 60db17a8 and original creation reflog;
completed read-tree -mu HEAD only after asserting an empty index/worktree.
Inconsistent earlier readbacks of other roots/SHAs are not source authority.
No reset, force push, replacement branch or unknown product effect was repeated.

Current source boundaries: do not edit #7241 publication recovery or #7036
release diagnostics; do not replace RIC-F1 or #7230 research persistence.
Do not redo RED proof, the adopted calendar, Chronicle or provider systems.
Next: finish full render/source/browser evidence, harden null/correction cases,
register tests under existing CI, review exact head, push PR, release only under
actual current gates. No product deployment and no live LLM inference claimed.

## Material proof update

Real official API capture: HTTP 200; seven rows; four covered coupon/FRN events.
Evidence is `research/event_intelligence/auction_context_v1/`. Browser component
matrix 8/8 with no page errors; keyboard and date changes exercised. Natural API
coverage found and fixed the source's actual closing-time key and FRN flags.
The static reading guide is explicitly not a live/model-generated assessment.

Full application/authenticated proof remains held: unauthenticated local full
page redirected to sign-in. This was not bypassed. June cached VM was rejected
for publication. No generated production page was overwritten from stale data.

Final source-bound focused suite: 94 passed. Portable browser proof repeated after the last source fix: 8/8 passed. Widened CI contract check: 0 introduced, 0 inherited. Canonical capture owner additionally emitted 8/8 valid capture cells; Agent OS validation has zero errors.
