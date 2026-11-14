---
key: CATALYST-COPY-CONTEXT-USES-EXISTING-READ-OWNER
claim: >
  Catalyst's existing account/revision-qualified workspace result provides the read
  identity needed to retire asynchronous case-copy feedback without introducing
  another account or request lifecycle.
falsifier: >
  Inspect terminal/components/catalyst-opportunity/CatalystOpportunityWorkspace.tsx
  at 929e008f689bc834662f52f845d070db3fc8eb00 and run
  npx vitest run lib/__tests__/catalystOpportunityView.test.tsx at Terminal PR #1354
  head 45472fcedad31292d660d54731d4da472ca04f1e: a result reused across an accepted
  new read/account or old feedback rendered after those transitions would refute
  the stated owner fit.
so_what: >
  Bind view-local asynchronous feedback to the incumbent current result plus the
  selected case and attempt. Do not use unchanged source dates or generation
  strings as request identity, add another account/read owner, or mistake list
  filtering for loss of an explicitly selected eligible case. Reuse PR1354's
  source-bound proof before repeating the repair.
kind: architecture
verified_at: 2026-11-09
verified_by: >
  Terminal PR #1354 at 45472fcedad31292d660d54731d4da472ca04f1e;
  docs/verification/catalyst-selection-copy-20261109/manifest.json and checks.txt;
  46 React tests, 18 targeted fixture-browser cases and npx tsc --noEmit passed.
scope:
  - terminal
  - terminal/components/catalyst-opportunity/
  - WS:ALPHA-INTELLIGENCE-INTEGRATION
confidence: verified
---

## Existing owner and demonstrated gap

At protected Terminal `929e008f689bc834662f52f845d070db3fc8eb00`, the workspace already qualified its current result against account identity and read revision before rendering. The view instead resolved explicit selection inside the filtered list and published clipboard completion without an attempt/context guard.

[PR1354](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1354) passes the incumbent result object into the view, resolves explicit selection from the whole current eligible case collection, and binds copy feedback to the active attempt and current read/case context. The initial URL-readiness guard, missing-case behavior and focus rules are part of that same bounded follow-up. Source dates and metrics retain their original meaning.

The result object is an opaque identity, not an authorization decision. Loading, unavailable source or access errors separately suppress the market detail/copy state. The existing workspace and server remain the access owners. The independently supplied Defense research lane remains outside ordinary market-source readiness.

## Proof and limits

The [committed verification bundle](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/45472fcedad31292d660d54731d4da472ca04f1e/docs/verification/catalyst-selection-copy-20261109) binds six implementation/test blobs, original check output and seven unmodified browser captures. Forty-six component checks passed, including actual workspace account/refresh transitions with identical fixture data; eighteen new desktop/tablet/mobile EN/ZH browser cases passed. Narrow Chinese used 320px. Full source TypeScript checking passed.

These are component and synthetic fixture browser observations. They do not establish live entitlement, market freshness, human usability research, a production deployment or completion of the broader Catalyst programme. An issued clipboard write cannot be cancelled; the guard prevents stale success/failure/fallback feedback.

At the recorded delivery milestone PR1354 was Ready at the named head with native auto-merge enabled; protected CI and merge were still pending. Read current GitHub receipts before any release conclusion. This record neither grants release authority nor creates a runner, queue, retry service or workstream owner.

## Continuity

The [Paper audit continuation §23](https://github.com/mastermindx-market-intelligence/Macro/blob/38d8843167b7151312ddd3395ff46f3e26c7bf79/research/design_candidates/production_design_20261102/audit_20261108/WORKFLOW_CONTINUATION_20261108.md) carries the full design/source mapping. Preserve the original programme's still-open source/entitlement/scientific obligations and PR1038's historical denied old-tree test action. PR1354's new materially changed source does not retroactively complete that old test.

The architectural lesson is scoped to the inspected owner and proved transitions. Other surfaces must establish their own incumbent read/selection owner before applying it.
