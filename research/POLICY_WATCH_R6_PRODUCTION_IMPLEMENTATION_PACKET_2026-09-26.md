# Policy Watch R6 — production implementation packet

Date: 2026-09-26  
Parent operation: `policy-watch-redesign-20260926-sol-001`  
Owner: Macro draft PR #8048 / branch `sol/policy-watch-redesign-study-20260926`  
State: **SOURCE_READY_PLAN / NOT_IMPLEMENTED / NOT_DEPLOYED**

## 1. Purpose

Turn the accepted product direction from the Policy Watch redesign study into a production-safe implementation sequence without overwriting existing Policy Watch producers, current source-health semantics, or open source work.

The customer-facing visual law is explicit: **Noir is limited to Mastermind OS administration. Policy Watch stays on the existing Mastermind customer design system.** Preserve graphite/light surfaces, blue interaction and provenance, amber caution, house typography, bilingual behavior, and truthful null/failure states. Dark mode remains a normal customer theme; it is not an admin-Noir migration.

This packet is not design acceptance and does not authorize deployment. It exists so implementation can begin from current code rather than reconstructing intent from screenshots.

## 2. Current source identities and collision fence

Current Macro `main` observed during this continuation:

- main commit: `fa85c3b4efe8140aab6c6bff4b813070cf6aa16d`
- `templates/policy_watch.html.j2` blob: `a7e46126baa488760386b1aa8fb34355bbf1e41c`
- current page already owns the official-current panel, FOMC calendar, UK desk, background research, market views, deterministic lifecycle, market-impact research, calls/results and sources.

Open Policy Watch implementation PR #7136 remains a material source collision:
- title: **Policy Watch: add official policy-event discovery feed**
- head: `cb9072f45fcef698a52d0e41bed65d406c69a9d5`
- current status: open / not draft
- it modifies `engine/policy_watch_current.py`, `scripts/build_policy_watch.py`, `templates/policy_watch.html.j2`, `tests/test_policy_watch_ui.py` and evidence/handoff paths.

**Collision rule:** do not begin a competing edit to those shared source paths until #7136 is merged, formally superseded, or its source-writer custody is otherwise reconciled. A stale date alone is not custody release.

## 3. Production thesis

The production page should answer four user questions in order:

1. **What changed?**
2. **What does that change actually mean?**
3. **What should I check next?**
4. **Where is the exact evidence and what remains unknown?**

No user should need to understand the internal research architecture before receiving those answers.

The redesign is a composition change over existing producers, not a new policy engine.

## 4. Four-view information architecture

### A. Briefing — default

Purpose: five-second comprehension.

Owns:
- current official record / latest material change;
- old → new date or wording comparison when the producer has a comparison;
- documented status and relevant source clock;
- next official event;
- one short “why it matters” interpretation;
- one explicit “not measured / not concluded” evidence limit;
- direct source and deeper-detail actions.

Reuse:
- `_policy_watch_current.html.j2`;
- current FOMC calendar mapping;
- UK typed states;
- current analysis snapshot;
- official-event discovery feed if/when #7136 becomes accepted source.

Do not:
- infer “most important” from recency alone;
- turn a policy stage into a market stance;
- collapse source publication, known-at/fetch time and analysis-as-of.

### B. Policy map

Purpose: follow a measure from proposal to implementation without a false progress score.

Owns:
- deterministic lifecycle rows;
- jurisdiction;
- current documented stage;
- stage date precision;
- next documented/unknown step;
- official source;
- source gaps and conflicts;
- background Fed / administration research as dated detail, not first-screen content.

Reuse:
- `lifecycle` view from the deterministic lifecycle owner;
- existing `LEVER_COPY` explanatory copy only where still valid;
- existing stage null/conflict/stale semantics.

No decorative completion percentage. Unknown/undated must remain unknown/undated.

### C. Calendar

Purpose: make official dates and user review dates legible without mixing their authority.

Owns:
- FOMC meeting dates;
- known implementation/compliance dates;
- deterministic stage dates where appropriate;
- source attribution;
- personal review checkpoint affordance only when an existing canonical persistence owner is wired.

Separate lanes:
- **Official date** — sourced external event or implementation date.
- **Research review date** — internal checkpoint, never freshness.
- **Personal reminder** — account feature, only after existing auth/persistence/alerts owner is connected.

Do not invent release times for date-only records.

### D. Calls & evidence

Purpose: preserve accountability.

Owns:
- original proposition / question;
- analysis snapshot;
- counterargument/falsifier;
- review horizon;
- source record;
- measured market outcome, if one actually exists;
- policy implementation outcome as a separate field;
- revision history that never overwrites the original claim.

Reuse the existing calls/results producer and track-record owners. Do not re-score historical calls during a visual migration.

## 5. Existing-capability migration map

| Current surface | R6 home | Production requirement |
|---|---|---|
| Hero rate outlook | Briefing supporting context | De-emphasize relative to actual change |
| Next Fed decisions | Briefing + Calendar | Same calendar owner; no duplicate calendar |
| Quick take/current official panel | Briefing | Preserve current/historical/awaiting distinctions |
| Background research | Policy detail | Preserve date and stale disclosure |
| UK desk | Briefing/Policy map desk selector | Preserve every typed UK failure state independently |
| Market views | Briefing excerpt + Calls & evidence | Preserve analysis-as-of and dissent |
| Fed task-force research | Policy detail | Dated research, not official-state substitute |
| Policy stages | Policy map | Preserve lifecycle source/date precision |
| Market impact | Policy detail / Calls & evidence | Interpretation, not causal proof |
| Calls & results | Calls & evidence | Preserve original record and denominator |
| Sources | Contextual evidence drawer + source registry | One-click evidence from every major claim |
| PR #7136 official-event feed | Briefing / source activity | Discovery context only; no rank/gate/trade authority |

## 6. Customer design-system contract

Canonical consumer visual source is current Macro `templates/theme.css` plus governed Paper customer references.

Use:
- `--bg / --panel / --panel2 / --text / --muted / --line`;
- `--info / --link` for interaction and provenance;
- `--warn` for real caution/uncertainty;
- `--ok` only for validated success/freshness semantics;
- existing `gbtn` / glass button family where appropriate;
- current site typography and type ramp.

Do not:
- apply Mastermind OS Noir/admin styling;
- use inverse black/white buttons as the defining visual grammar;
- invent purple “premium” accents;
- use bullish/bearish market colors for policy status;
- mint new shared tokens for this page unless a demonstrated cross-product design-system gap exists.

### Hierarchy targets

Desktop:
- page identity: 28–32 px;
- lead change: 28–34 px;
- section title: 17–20 px;
- body: 14–15 px;
- metadata: 11–12.5 px;
- one dominant action per focal panel.

Mobile:
- preserve the same information order;
- first useful action visible without reading the entire card;
- 44 px product target for primary controls;
- no body horizontal scroll;
- date ranges stay atomic;
- evidence drawer becomes a full-height sheet/detail route.

## 7. First implementation slice after source-collision clearance

**Slice R6-A: Briefing only.**

Change only composition and presentation around already-owned data.

Target source paths:
- `templates/policy_watch.html.j2`
- `templates/_policy_watch_current.html.j2`
- `tests/test_policy_watch_ui.py`
- existing visual-evidence fixture path under `mockups/evidence/policy-watch-*/`

Avoid builder changes unless the existing template genuinely lacks a required field.

R6-A must:
1. reduce the hero to page identity + source/analysis clock;
2. make the current official change the dominant content;
3. place old/new comparison and official source adjacent;
4. surface one evidence-limit sentence;
5. keep the next official event visible;
6. reduce top-level navigation to Briefing / Policy map / Calendar / Calls & evidence;
7. keep old deep sections reachable during migration rather than deleting them;
8. preserve EN/ZH and light/dark;
9. preserve all current typed null/degraded states.

No alert integration, personal exposure, new event producer, scoring change or source expansion in R6-A.

## 8. Migration mechanics

Prefer progressive migration over a big-bang template rewrite.

Phase 1:
- add the four-view local navigation;
- render new Briefing using existing producer objects;
- retain legacy deep sections below or behind the corresponding destination anchors;
- keep stable existing section IDs temporarily for deep links.

Phase 2:
- move deterministic lifecycle into Policy map composition;
- move calendar records into Calendar composition;
- move calls/results/sources into Calls & evidence;
- maintain compatibility anchors until browser/deep-link evidence says they can be removed.

Phase 3:
- remove redundant legacy wrappers only after parity and browser proof;
- retain the underlying producer contracts.

No new client-side router is required for the first production slice. Anchor navigation and progressive disclosure are sufficient unless user testing demonstrates a real need for route state.

## 9. Required failure-state behavior

Production acceptance must explicitly exercise:

- healthy source, no new record;
- source outage;
- stale source;
- latest record invalid, older usable record retained;
- latest official decision unavailable;
- analysis unavailable while official record is present;
- desk disabled;
- analysis date missing;
- lifecycle no coverage;
- lifecycle rights suppressed;
- conflicting lifecycle records;
- empty search/filter state;
- no closed calls / no denominator;
- personal persistence unavailable if a note/reminder feature is later connected.

A missing analysis must never become a “neutral” market read. A missing source must never become “no policy activity.”

## 10. Test contract

Before changing production template behavior, add RED-first assertions for the new composition while retaining existing truth tests.

Functional:
- four local destinations present;
- Briefing contains current official record, source, status and relevant clock;
- previous/current comparison is present only when producer supplies both;
- official date and review date use separate labels/contracts;
- UK failure states remain desk-scoped;
- analysis unavailable does not hide official record;
- original call and revised view remain separately inspectable;
- no new trade/rank/gate/sizing authority.

Visual matrix:
- EN/ZH × dark/light × 1440 and 390 = 8 primary cells;
- stress widths: 320, 768, 1024;
- long Chinese labels;
- missing fields;
- stale/outage/analysis-unavailable;
- 200% zoom/reflow check.

Browser:
- zero horizontal overflow;
- no console/page errors;
- no failed same-origin asset requests;
- keyboard reaches every interactive control;
- focus visible and restored after overlays;
- Escape closes modal/sheet;
- source links remain direct and distinguishable;
- deep anchors return to the correct section.

Accessibility:
- WCAG 2.2 AA target;
- color is never the only state signal;
- no placeholder-only labels;
- target sizing verified rather than inferred;
- reduced-motion behavior does not hide state.

## 11. Performance and implementation quality

Use existing site assets and typography. Do not add a new frontend framework for this page.

Acceptance targets should be measured against the current built page, not invented:
- no unnecessary JS dependency for static composition;
- no remote font or image dependency introduced;
- no duplicate source fetch;
- no background polling added by the redesign;
- existing build-time data remains build-time unless an accepted product capability requires otherwise.

Any later account note/reminder/alert feature must reuse existing auth, persistence and alert owners. It must not create a Policy Watch-specific scheduler or data store.

## 12. Source-owner integration with PR #7136

If #7136 merges first:
- rebase the R6 implementation on merged main;
- consume its official-event feed as an optional Briefing/source-activity input;
- keep its discovery-only authority ceiling;
- rerun its rights/time/degraded-state tests as part of Policy Watch acceptance.

If #7136 is superseded:
- consume only the accepted replacement producer;
- do not rebuild the event collector inside R6.

If #7136 remains actively owned:
- do not modify its overlapping paths in parallel;
- continue only non-overlapping design/proof work.

## 13. Paper-to-production contract

Paper is the editable visual authority for accepted R6 composition; production implementation uses real template/data owners.

Do not rebuild CSS by eyeballing screenshots. Once the guarded Paper schema is qualified again:
1. apply the already-prepared customer color-role correction;
2. reconcile the R4/R5 navigation placement;
3. capture accepted native screens;
4. extract native JSX/style values for exact spacing/type/token mapping;
5. implement equivalent composition in Jinja using existing component classes/tokens rather than copying generated JSX verbatim.

Paper proof does not replace browser proof. Browser proof does not replace source provenance.

## 14. Release gate

Do not call the redesign production-ready until all of the following are true:

- source-collision owner resolved;
- exact implementation head reviewed;
- current Policy Watch truth/data tests green;
- required visual matrix captured from production-shaped build;
- degraded states inspected;
- EN/ZH and light/dark parity verified;
- accessibility/keyboard checks complete;
- no current-source or lifecycle semantics regressed;
- normal CI green on exact head;
- deployed public page bound to accepted merge/release identity;
- real public-browser route checked after deployment.

Green CI alone is not acceptance.

## 15. Exact next source action

While the guarded Paper schema is incompatible, **do not modify overlapping production paths**.

First source action after either #7136 merge/supersession or a proven custody release:
- create one implementation branch from then-current `main`;
- implement R6-A Briefing only;
- write RED-first UI/preservation assertions;
- produce the eight-cell visual matrix;
- return exact head + test/browser evidence for review before expanding to Policy map, Calendar or Calls & evidence.

Until then, preserve the verified R5 prototype, the existing Paper artboards and all producer contracts.