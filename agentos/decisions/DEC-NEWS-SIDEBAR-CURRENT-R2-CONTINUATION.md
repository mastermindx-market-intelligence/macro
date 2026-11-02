---
key: NEWS-SIDEBAR-CURRENT-R2-CONTINUATION
question: "How should the paused Terminal News sidebar project continue after R2 and saved-basis corrections landed?"
answer: >
  Continue from current master through a thin successor to Terminal PR 1081.
  Recover the dated Brief assessment and preserve R2/editorial/token-bound detail
  and Journey 6 save behavior. The next bounded UI slice is full-height reading,
  company-panel hide/restore with working phone Symbol details navigation,
  activity-strip removal and inert one-pass source-text display decoding.
  Defer the old review-control removal until its save semantics are reconciled.
rationale: >
  The old renderer predates current editorial views, evidence handling and the
  saved-basis correction journey. Mark reviewed is currently the sole News save
  entry. Replacing the whole renderer or deleting that action would lose a
  functioning journey. The surviving layout/text improvements can be specified
  against current source without reverting those capabilities.
alternatives:
  - option: "Merge or transplant the old PR 1081 renderer."
    why_not: "It overlaps current R2 and Journey 6 source and would remove newer behavior; its accepted review applies only to its old head."
  - option: "Remove every review control immediately."
    why_not: "The action now also captures the saved evidence basis. No separate News save entry was found and R3 is design-only."
  - option: "Discard the paused project."
    why_not: "The original full-height reading and activity-strip cleanup are still visible needs; the dated shared-Brief assessment remains useful input to E4."
evidence:
  - "Terminal PR 1081 at a10657ee8eaa0aa12c98e2ba5563a8680bfb9c9b; fresh GitHub read on 2026-11-02: open, Draft, merge-blocked, unmerged."
  - "Terminal master fd1e500c54376c7ea763b8eaec23a0929b08f4c8: TickerNewsPanel.tsx, TickerNewsPanel.module.css, newsDisplay.ts and TerminalShell.tsx read from git show."
  - "git grep -n -E 'NewsMarkReviewed|markReviewed\\(|saveBasis\\(' origin/master -- terminal: NewsMarkReviewed used only by TickerNewsPanel; row action calls catchup.markStory."
  - "Terminal PR 1196 merged saved-basis corrections; PR 1129 owns the open ladder-layout follow-up; PR 1130 is R3 design exploration."
  - "Macro research/product_intelligence_local_delivery/NEWS_INTELLIGENCE_RAIL_R2_SPEC_2026-10-22.md at 9af0a33eb38b08d902c3e593cb0e276d3f0d6a18 expressly retained strip, catch-up, review and Mark reviewed in that R2 build."
  - "Macro PR 10351 merged E4_BRIEF_BINDING_CENSUS.md: B1-B4 PARTIAL; B5 NONE at its census head; repaired legacy news inference gates default false."
  - "Authenticated Chrome visit to https://app.mastermind-x.com/terminal on 2026-11-02: News/NVDA rendered 20 stories, activity and review controls, and a visible company panel below News. Read-only DOM measured News at 344x553; a live-interrupted notice was visible. This is an existing-production observation, not successor proof."
  - "Terminal PR 1207 at 515b7e8b6af5d22f33976332953caf3a4abfa151 contains the recovered document and exact continuation; GitHub readback matched the local UTF-8 content."
affects:
  - "WS:NEWS-INTELLIGENCE-ESTATE-CONVERGENCE"
  - "WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT"
  - "mastermind-terminal/terminal/components/news/*"
  - "mastermind-terminal/docs/TICKER_NEWS_SHARED_BRIEFS_2026-10-19.md"
confidence: high
reversibility: easy
decided_by: "ceo-sol / terminal-news-sidebar-20261018-c4 current ChatGPT principal"
decided_at: 2026-11-02
---

# Continue the News reader against current source

The current user asked this seat to resume the News project. This decision is scoped
to the old sidebar mission and its existing E1/E4 task-tree entries. It does not
take over the wider News Intelligence Estate or change its plan, runtime ownership,
source rights, quantitative gates, or active Fable work.

## What the choice preserves

The current editorial view selector, evidence ladder and clocks, member expansion,
NEXT CHECK, Retry, token-bound detail cache, saved basis and Open current remain the
baseline. The planned removal of the plain activity block is a deliberate, narrow
revision to the R2 layout. The original request to remove review chips and Mark
reviewed remains **unfulfilled in this slice**; a later product decision must define
the save action and reviewed/catch-up semantics together. Merely relabeling the
button is not that decision.

The company board must remain mounted while hidden, preserving state when the
reader leaves News. The phone Symbol details action must reveal that existing board
before scrolling to it. Desktop full-height styling must not replace the existing
tablet/mobile document-flow behavior.

## Brief assessment and owner boundaries

The recovered assessment is a dated design input. The current E4 census and
[masterplan](../../research/news_intelligence_estate_20261021/MASTERPLAN.md) remain
the parent programme sources. Existing artifact, cross-process request,
conditional-publication and durable pre-call spending bindings must be qualified
before Brief endpoint/tab implementation. Explicit demand, permission-aware shared
reuse, zero demand/zero inference and revision-safe publication remain the design
requirements. This decision authorizes no model call, job, feed or legacy-path
activation, and creates no new store, scheduler, budget or publication authority.

## Implementation and continuation state

[Terminal PR 1207](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1207)
is the exact task-specific continuation. At source commit
`515b7e8b6af5d22f33976332953caf3a4abfa151` it contains documentation only. The UI
changes above are proposed, not implemented, reviewed or deployed. PR 1081 is
preserved as Draft history and now points to PR 1207.

The bounded implementation run
`terminal-news-sidebar-20261102-c4-current-build-001` returned terminal rc75 /
EXECUTION_NOT_ELIGIBLE from the existing Fabric adapter. Its retained result names
`host_temperature_at_or_above_limit`; response SHA256
`9226eff028a331231dfb4b1b0724ae44285f89240e338de98c6107b2ae6ece4d`.
The adapter still reports `execution_absence_proven=false` and
`retry_allowed=false`. Worker START is unproven and no source result was accepted.
Preserve the run and resolve through its incumbent admission/reconciliation owner;
this knowledge record grants no retry, rerouting or runtime authority.

The broader estate workstream and its existing Fable handoff remain untouched.
The linked PR carries the source/workspace identities, preserved old review and
uncertain-run fences, validation limits and exact next action. This record is a
product decision with a continuation pointer; it does not present a new
programme-wide handoff as the current Fable receiver state.

## Reconsideration

Revisit the retained controls when an agreed current save interaction preserves
the saved evidence basis and correction journey, or when the user explicitly
retires that journey. Revisit this integration choice if current master acquires
the proposed improvements before this slice is implemented. Refresh only affected
source/evidence; do not repeat the accepted E4 census or revive the old renderer.
