# Macro News popup — November 1, 2026 upgrade

Operation: macro-news-popup-20261101-c2.
Owner: current Chairman-assigned ChatGPT2 session; native root 01a19a0b-c241-74aa-a42b-6fe12dd2b0e7.
Owning repository: mastermindx-market-intelligence/macro.
Program reference: existing popup design program #7879.
Protected procedure: Mastermind@19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec (skillpack 1.0.1, bootstrap 1).
Source baseline: macro@9af0a33eb38b08d902c3e593cb0e276d3f0d6a18.
Task tree: research/macro_news_popup_20261101/PLAN.md.
Recorded: 2026-11-02 UTC (November 1, America/Chicago).

## Outcome and acceptance

Upgrade the existing live `dlg-news` consumer in macro.html: the first viewport answers what changed and why to pay attention; details expose underlying evidence, source clock, uncertainty, and limits. Preserve alert semantics, existing publisher/identity owners, bilingual support, shared theme and modal ownership. Never promote unverified or stale publications to current verified facts.

DONE_WHEN: implemented source and generated assets agree; the entry -> filter/search -> evidence -> return -> close journey works on desktop/mobile in light/dark and EN/ZH; adversarial temporal/event-identity cases pass; required independent review and release/browser evidence exist. Source delivery, CI, merge, deployment and acceptance remain separate.

## Scope and custody

This is a new bounded improvement of the already-live News popup. It does not install, adopt, retry or replace held Events & News R2 PR #8186, and does not touch its branch/component or the held old integration operation. Preserve its original gate and custody. Preserve other News/intelligence collectors and open #9612/#10136/#10244; no News-page, ticker-news, following/account, provider, scoring, publication-daemon, infrastructure or trading changes.

Expected source: existing `templates/dashboard.html.j2` News-only section, extracted presentation CSS/JS or macros only when needed, paired site assets, the existing release-publication client for a narrowly verified same-event/age defect, and focused tests/evidence. Existing host owns modal lifecycle; no second modal, polling, publication, identity or ranking engine.

## Design decisions

- Keep one briefing feed. Priority, context and source stories share readable row anatomy.
- Each row exposes a concise subject, plain implication, source-kind/status and only supported clocks. Longer explanations/evidence use native details disclosure.
- Search and type filters preserve expansion/focus; show exact displayed counts and distinguish no matches, no data, partial data and delayed updates.
- Priority uses producer tier, never a new browser investment score. Unknown timestamps remain unknown; page-build time is not the observation clock.
- Dark: calm deep surfaces, neutral hairlines and semantic ink. Light: cool canvas, white research surfaces, clear contrast and subtle shadows. No colored container edge, emoji decoration or arbitrary token root.
- Mobile: one content scroller, wrapped controls, reachable close, 44px controls, no horizontal overflow; keyboard/focus and reduced motion preserved.
- Existing Events remains the route for economic release detail; News cannot show mismatched event rows or mutate an unrelated countdown.
- Existing release feed remains the update owner. No unbounded polling loop, fake live indicator or invented refresh timestamp.

## Task tree

| ID | Dependency | Objective and acceptance | Editorial label |
|---|---|---|---|
| N1 | — | Freeze actual source/data/modal boundaries and collision census; inspect screenshot and existing program. | implementation_complete |
| N2 | N1 | Build and screenshot-review production-shaped light/dark responsive design; keep shared semantics and full evidence accessible. | implementation_complete |
| N3 | N2 | Implement the approved News-only presentation and resilient progressive enhancement in the existing consumer. | implementation_complete |
| N4 | N1 | Reproduce publication age/identity defects and apply only verified, nonconflicting fixes to incumbent updater. | implementation_complete |
| N5 | N3,N4 | Targeted adversarial tests, actual browser journey and visual matrix; independent source/design review and bounded repair. | implementation_complete |
| N6 | N5 | Publish exact candidate, satisfy lawful review/CI/release gates, and verify actual served consumer. | in_progress |

## Current source findings and falsifiers

Observed current News markup at source baseline: long explanations always expanded; context opacity .8; alert rows lack clocks; external headline URLs rendered directly. Existing release client blob `1fb1d4f14a64498fd123ccee039dbb8f5530a242` includes all `published_unparsed` rows regardless of the 24-hour cutoff, and attempts text-based ancestor matching for News alert patching. These are source findings; actual regressions must be reproduced before claiming a fix.

Required attacks: CPI row touching payroll alert; generic explainer mentioning several events; two release dates of same series; stale/unparseable/future clocks; malformed payload; old response after newer correction; duplicate request; no-JS; empty/partial/error; untrusted HTML/URL; lost focus during filter/update; reopen/close; EN/ZH parity and 390px overflow.

Historical #7879 polling candidate and accepted unchanged evidence should be reused where valid, not counted twice. The current source audit child is read-only, uses the same original root, and cannot authorize source integration.

## Evidence and release boundary

Evidence is attached at exact candidate revisions. This plan is repository source evidence, not a runtime Job or Agent OS wave. No new workstream is invented. Existing organizational association is #7879; no verified popup-specific Agent OS mapping has been established, so PLAN_NOT_ORG_LINKED is explicit.

No merge, deploy, publication service change, credentials or independent review approval is authorized by this document itself. Current Chairman intent and existing repository/release controls govern each next action.

## Implementation checkpoint — November 2, 2026

N2/N3/N4 source implementation is complete and under verification. Detailed behavior, reproduced failures, passing checks and unproven gates are recorded in VALIDATION.md. Canonical isolated workspace acquired at `/Volumes/Mastermind/agent-workspaces/macro/web/news-intelligence-popup-20261101-c2`; sparse data/site materialization uses the incumbent repository helper. No shared primary checkout or held R2 branch was modified.
