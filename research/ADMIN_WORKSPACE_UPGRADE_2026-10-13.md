# Admin workspace upgrade — execution plan

## Outcome and authority

Make admin.mastermind-x.com a clearer daily operating workspace: find the right tool by task, keep frequent destinations close, understand the selected page, and distinguish an old status snapshot from a successful current read. Preserve all 54 routes and their existing backend owners.

Current Chairman request: extensively upgrade the admin panel. Mastermind procedure pin: f9bab9b1f56d747416d80c6f04c810d2960fc2ee, compatible skillpack 1.0.1. Macro source base: 0918bc8c7c69ba4db36c88bc8874da671c3f0572. Source carrier: Ubuntu0 RDC, isolated branch sol/web-admin-panel-upgrade-20261013-c2. No runtime admission or production mutation is implied.

## Design decision

Retain the existing task-grouped sidebar rather than introducing a third inventory or deleting specialized tools. Add a small separately testable workspace module: task search with contextual descriptions, keyboard command dialog, pinned destinations, recent page navigation, and an all-tools directory. These are local presentation preferences, not organizational state, a work queue, or an execution system. Never persist customer identifiers, record contents, credentials, detail URLs or query text.

The global shell should explain the selected page without repeating its entire contents. On the overview, show status first, everyday tasks next, optional research details last. A persistent read-status indicator distinguishes loading, successful observation and failed refresh with a retained snapshot. It reports when the console read succeeded, not when underlying data became fresh. System health claims keep their existing explicit coverage boundary.

Rejected alternatives: a framework rewrite would increase integration risk without fixing the operator journey; deleting or merging specialized screens without proven contract equivalence would lose capabilities; another giant app.js feature would compound the existing monolith.

## Scope and boundaries

- Reuse the canonical NAV_GROUPS inventory and existing Observatory CSS tokens.
- Preserve current auth, CSRF, same-origin checks, confirmations and all backend mutations.
- Do not change the active analytics exclusion work (Macro #9057), Intelligence OS evidence hold (#6651), or Prophet rotation implementation (#7174).
- No new external frontend runtime dependency. Native dialog, DOM and storage only.
- Local preferences must be validated, bounded, optional and resilient to corrupt or unavailable storage.
- Desktop 1440×960 and mobile 390×844; keyboard navigation, focus restoration, empty results and reduced motion.
- Inherited admin design is English/dark-only. Do not claim light/Chinese certification. New material uses existing token families; dual-theme/language migration remains separate work.
- Browser verification uses explicit synthetic fixtures and blocks API writes. Fixture health is not production health.

## Implementation and proof

### 1. Baseline and failing contracts
- Capture the existing overview at desktop and mobile widths.
- Add Node-backed tests for catalog completeness, task search, safe bounded preferences, and truthful read-status state.
- Add browser checks for command search, keyboard activation, pin/recent persistence, focus return, route coverage, failed refresh, mobile overflow and login boundaries.
- Run the new tests and record the expected missing-capability failures.

### 2. Workspace navigation
- Create admin/static/workspace.js with a pure model and small DOM adapter.
- Create admin/static/workspace.css using the existing tokens.
- Integrate with the existing boot/page lifecycle using minimal app.js hooks.
- Deliver new assets through the existing content-hash cache and exact public-static allowlist; preserve API authentication.
- Add page context, search trigger and accessible landmark/login labels in index.html.

### 3. Snapshot trust and operational triage
- Track successful status-read time and refresh errors without replacing the last good snapshot on failure.
- Keep stale/failed reads visible until a successful retry; no automatic retry loop.
- Surface critical resource pressure only from finite, valid observed percentages; retain unknown and unavailable distinctions.
- Test overlapping read results and navigation during refresh before accepting the behavior.

### 4. Review and delivery
- Run focused and broad admin regression tests plus the existing JavaScript checks.
- Exercise real rendered screenshots and keyboard/mobile/error paths; repair defects, then bind evidence to the exact source revision.
- Publish one PR, respect concluded checks and independent review requirements, and use the normal deployment path.
- Verify public asset identities and authenticated production workflows separately. Never promote local fixture proof to production acceptance.

## Review focus

Corrupt/denied storage must not break boot. Search terms must not become HTML. Mobile navigation and the command dialog must not compete for focus. A failed read must not look like a current all-clear. Search/navigation must never issue an administrative mutation.

## Recovery frontier

M2 source acquisition was NOT_APPLIED due to its protected storage reserve; M1 was also below its reserve. Neither safeguard was changed. Ubuntu0 native sparse-worktree acquisition succeeded. No worker was started, no customer data changed, and no deployment occurred. Continue in the same isolated source workspace; do not recreate the operation on a Studio or duplicate pending writes.

## Verification delta — implementation in progress

Static JavaScript syntax, Python server compilation, diff whitespace, and the existing ESLint no-undefined-identifiers guard passed. The combined synthetic browser-fixture and initial pytest command was refused before dispatch and was not retried; no red/green result is claimed for that command. Independent observation of the actual loopback admin server uses no session interception, mock API responses or administrative mutations. It verified the 54-route inventory and task search, then exposed the native search-input Escape behavior: first Escape cleared the query while leaving the dialog open; second Escape closed it. The focused diagnostic proved that cause. An explicit Escape handler now closes the command dialog on the first press; its full observation run remains pending.

### Verified candidate milestone

The independent actual-server browser observation now passes 18 checks with zero JavaScript exceptions and no API writes. This includes first-Escape focus restoration, pin/reload/reversal, all-tools reset, offline failed-refresh visibility, successful retry recovery, mobile overflow and a correctly sized mobile search hit target. Visual review caught the old two-column mobile header putting the new trigger in a 34px drawer cell; the header now has an explicit third column. Duplicate overview refresh chrome is removed when the workspace module is active.

The focused pre-existing admin regression group passes **87 tests**. Two discriminating additions were observed failing before their respective repairs: resource pressure was absent, and an obsolete refresh failure escaped after a newer successful read. Both now pass. Obsolete successes and failures cannot replace or invalidate the latest summary. The latest source and screenshot SHA-256 values are in `research/evidence/admin-workspace-20261013/source-receipt.json`.

The new dependency-free model contracts are included in the existing admin workspace CI step, not a new workflow. The blocked composite command remains unexecuted; ordinary CI results are separately owed. No production mutation, merge or deployment is claimed at this checkpoint.
