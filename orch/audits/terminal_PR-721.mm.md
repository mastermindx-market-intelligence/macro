# Audit record — Terminal #721: coarse pane menu stacking

## Record status and provenance

This records-only reconciliation preserves the September23 audit's useful source findings. Native metadata and the complete two-file patch were inspected on 2026-11-06. No TypeScript, Playwright, browser, deployment or live test was run for this record; original Terminal #721 remains an accepted implementation and DO_NOT_REDO.

- [Product PR #721](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/721), author chriswong6031-creator.
- Source head: `d5dade0a07e26392ee50f65e3b25a69f72d5f37c`.
- Merge: `271bb55e2cc2e703169e17127874098c9670ab8e`, 2026-09-23T05:54:23Z.
- The product body identifies #717 / `3da0c75485fd59284de293701d897c14a4936e0c` as the preceding deployed repair.
- [Original audit](https://github.com/mastermindx-market-intelligence/macro/blob/5d574d4e37cc1f588dfc08c5e20f0cdb46acc51a/orch/audits/terminal_PR-721.mm.md), blob `141bcb43ce80a9df17ea4b6638bf765ce42294be`. The source head and the squash merge are distinct identities.

## Source-supported behavior

Native GitHub reports two changed files, +20/-5:

1. `terminal/app/globals.css` moves the existing `.app:not(.shell-app) .workspace:has(.lg-more){z-index:31}` rule from the phone640px block to the existing responsive860px block. The rule and z-index value are reused; the comment explains the detail rail's ability to intercept lower menu rows on tablet and phone.
2. `terminal/e2e/drawing-system.spec.ts` strengthens the existing coarse collapse test. It obtains the visible Collapse row's bounding box, samples `document.elementFromPoint()` at its center, requires the hit to have a `.lg-more` ancestor, then clicks the row and keeps the existing collapsed-mask consequence check.

The preflight specifically checks ownership by a menu at the sampled point. It is not a proof of every menu row, viewport or interaction; the subsequent click and collapse assertion remain part of the regression. No new breakpoint, renderer, menu owner, persistence format, visible label, translation or theme token is introduced by these two file changes. Test-side selector strings and comments do exist, so “zero new user-visible copy” must not be restated as “no new string literals.”

## Historical evidence and retained limitations

The product body reports a production failure on the preceding #717 deployment: tablet820×1180 had workspace z-index auto and the detail rail intercepted the tap, while phone used31. It reports TypeScript, tablet, mobile, desktop and diff checks passing after the change. The original audit separately reports a plain-language scan with zero added-line findings and six legacy entries. These are attributed historical reports, not new measurements or current estate totals.

The audit describes Terminal's then-standing dark-only doctrine. The diff does not add light-theme rules or change token paint, but a CSS stacking change still has an interaction consequence. Old #717 screenshots alone do not demonstrate that #721's changed tablet hit-test path works. The historical product body's browser assertions and any separately retained actual receipts must keep their original scope; this record does not issue a new evidence exemption.

The historical legacy-copy observations at AlertTimeline, WatchingList, ForecastPage, ExposureMatrix, SectionAccount and visualIntelligenceCopy remain optional context for their existing owners. They are not newly verified debt, a new remediation assignment or a reason to reopen this accepted stacking repair. The source-supported conclusion is limited to the moved CSS rule and stronger regression contract; present production acceptance requires its own product-path evidence.
