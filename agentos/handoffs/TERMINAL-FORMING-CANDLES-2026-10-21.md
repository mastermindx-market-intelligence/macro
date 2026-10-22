---
workstream: WS:TERMINAL-FORMING-CANDLES
session: claude/live-candle-forming-20261021
model: codex
ended_because: ci_handoff
mission: Implement and deliver the first real-time candle slice from the accepted audit, including Hub completeness, live reducer repair, and shared calendar/countdown rules.
state_before: The quote lane retained the latest second rather than a complete forming candle; corrections and accepted history could disagree with live OHLCV, and countdown grouping diverged from historical grouping.
changed:
  - path: hub/lib/formingCandles.js
    what: Own bounded minute-prefix/second-suffix coverage, revisions, correction replacement, and raced-seed repair.
  - path: hub/lib/polygon.js
    what: Integrate authoritative seeding and route old aggregate corrections without advancing the last quote.
  - path: terminal/lib/formingCandles.ts
    what: Project bounded selected timeframes and prevent older quote responses from rolling back current forming state.
  - path: terminal/lib/liveCandle.ts
    what: Replace complete snapshots, preserve partial baselines, fence retained snapshots after accepted history, and admit source-qualified pre/post snapshots with same-price ordering and pane-qualified native handoff.
  - path: terminal/lib/candleCalendar.ts
    what: Use canonical session/resampling rules for live buckets and countdowns.
  - path: terminal/components/ChartPanel.tsx
    what: Reconcile changed bars through one derivation generation and install history fences on initial, daily, and 24H refresh paths.
  - path: terminal/app/api/quote/route.ts
    what: Authenticate before cache reads and enforce the effective seconds-band capability before fresh or cached chart projection.
  - path: terminal/components/TerminalShell.tsx
    what: Carry the selected-timeframe chart quote lane through the existing polling path.
  - path: terminal/docs/pr-crops
    what: Recapture the three affected evidence packets while preserving historical qualifications.
prs: [1102, 1108]
verified:
  - claim: Hub regressions pass after the final seed and correction repairs.
    command: cd hub && npm test
    result: 617 tests in 81 suites passed.
  - claim: The final focused candle, calendar, projection, route, and splice regressions pass.
    command: cd terminal && npx vitest run lib/__tests__/liveCandle.test.ts lib/__tests__/candleCalendar.test.ts lib/__tests__/formingCandles.test.ts lib/__tests__/us24hSessions.test.ts lib/__tests__/quoteRouteView.test.ts lib/__tests__/liveSplice.test.ts lib/__tests__/intradayRouteGates.test.ts lib/__tests__/optionsLevelAxisEvidence.test.ts lib/__tests__/b_pl_6Batch1Evidence.test.ts lib/__tests__/visualIntelligenceEvidence.test.ts lib/__tests__/terminalQuotePublication.test.ts
    result: The final combined focused run passed 176 tests in eleven files, including 21 quote-route access cases and the 23 evidence/publication cases below.
  - claim: The final screenshot readers and quote publication harness pass.
    command: cd terminal && npx vitest run lib/__tests__/optionsLevelAxisEvidence.test.ts lib/__tests__/b_pl_6Batch1Evidence.test.ts lib/__tests__/visualIntelligenceEvidence.test.ts lib/__tests__/terminalQuotePublication.test.ts
    result: 23 tests in four files passed.
  - claim: The final candidate passed the complete hosted CI run.
    command: gh api repos/mastermindx-market-intelligence/mastermind-terminal/actions/runs/39644751193/jobs
    result: All 16 jobs succeeded, including desktop/tablet/mobile/serial browsers, Terminal unit and typecheck, Hub, ingest/signal-layer, PostgreSQL investigation, and the umbrella gate.
  - claim: The protected squash contains the reviewed source.
    command: git fetch origin master && git diff --exit-code ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891 ab5beab6b0c2362414a1da17745587d490e923e8 && git merge-base --is-ancestor ab5beab6b0c2362414a1da17745587d490e923e8 origin/master
    result: PR 1102 merged at 2026-10-21T18:30:47Z; both commit trees are f73fe3826ebee703e01b8b6f24a815e41140cd4b; all 59 changed files match, and the merge is contained by then-fetched protected master eb752cd653f3add2aa67cdcc7b588dae13c86843.
  - claim: The exact merged source is installed and publicly served, with healthy restarted services.
    command: python3 /tmp/candle-release-identity-20261021.py ab5beab6b0c2362414a1da17745587d490e923e8
    result: Release owner exited 0; independent readback exited 0 at 2026-10-21T22:00:21Z. All seven installed source hashes, deployment marker, canonical HEAD, public page and chunk IDs match ab5beab6. Shared build hold is absent. Terminal PID 491443 and quote-hub PID 491538 are active/running; Hub health is OK and Polygon is authenticated.
  - claim: Public quote responses preserve source and capability boundaries after deployment.
    command: python3 /tmp/candle-production-probe-20261021.py; python3 /tmp/candle-production-full-probe-20261021.py
    result: Each 92-second observation returned 39 HTTP 200 samples from polygon-snapshot-rt, with nine regular-path and ten full-path distinct measured last prices. Both observed zero native forming snapshots; ordinary quotes contain no forming payload; both mixed 1s/1m requests return atomic empty quotes and disabledTimeframes [1s].
  - claim: The final snapshot repair preserves partial OHLCV and rejects stale and inadmissible handoffs.
    command: cd terminal && npx vitest run lib/__tests__/liveCandleSnapshot.test.ts lib/__tests__/liveCandle.test.ts lib/__tests__/candleCalendar.test.ts lib/__tests__/formingCandles.test.ts lib/__tests__/tiingoBoatsFreshness.test.ts && npx tsc --noEmit
    result: 119 tests passed in five files, including 47 snapshot cases and the inadmissible BOATS native-handoff regression; TypeScript exited 0.
  - claim: The snapshot repair reaches the rendered chart, synchronization lookup, rollover, and shared countdown at all three required widths.
    command: cd terminal && TERMINAL_E2E_PORT=3197 npm run test:e2e:responsive -- e2e/live-candle-snapshot.spec.ts e2e/forming-candle.spec.ts --workers=1
    result: Six cases passed without retries at 1440x900, 820x1180, and 390x844; screenshots and README are committed under docs/verification/live-candle-snapshot-2026-10-21. They are fixture evidence, not live-market proof.
  - claim: The branch refresh preserves the reviewed follow-up while including the deployed news release.
    command: git diff --exit-code 845e2b558d42f4c80d0108a93cc51ac3235a9631 2e7cb8505cc2521d1e3f0e44768bb2ac2df1a9f3 -- terminal/lib/liveCandle.ts terminal/lib/__tests__/liveCandleSnapshot.test.ts terminal/e2e/live-candle-snapshot.spec.ts docs/verification/live-candle-snapshot-2026-10-21 && git merge-base --is-ancestor 187bf9582b3deba2de49b597e29ccce6356333d3 2e7cb8505cc2521d1e3f0e44768bb2ac2df1a9f3
    result: All seven follow-up paths match and the deployed news release is contained. PR 1108 is armed for protected merge; its current CI run is 39704185148 and is still running at this checkpoint.
unverified:
  - claim: The deployed snapshot follow-up visibly moves a partial pre/post-market candle and rolls into the next minute on actual fresh market observations.
    what_would_verify: During an eligible pre/post session, confirm served release identity, observe qualified price changes update the actual candle while preserving accepted open/volume, and observe a minute rollover with a nonzero shared countdown.
  - claim: Complete native forming snapshots are active and proved during the regular U.S. session.
    what_would_verify: An admitted shared forming-OHLCV publication and a genuine source-to-render pilot, including rollover, corrections, reconnects, and coverage.
unresolved:
  - PR 1102 is deployed and independently verified. The residual snapshot repair is implemented and reviewed in PR 1108 with local tests complete; protected CI, merge, deployment, independent readback, and positive live pre/post-market movement proof remain in progress.
  - Native complete forming snapshots are not active under the preserved delayed AM socket and Next seconds-band controls; the shared producer still needs an admitted candle-specific OHLCV publication.
next_actions:
  - Own PR 1108 CI run 39704185148 through completion and protected merge, then verify the landed seven files and current master ancestry.
  - Recheck the deployed marker and shared hold; deploy only through the git-gated release owner, or verify a newer containing generation without rolling production backward.
  - Run the separate follow-up identity script, inspect service health, and verify current-session behavior; observe positive partial-candle movement and rollover during the next eligible live pre/post session.
  - Finalize and publish these three Macro records through normal CI and merge without an unrelated service deploy; complete native forming publication remains separate.
do_not_redo:
  - The completed audit is accepted; do not restart it.
  - The independent contract review accepted a0ce3290 and the calendar review accepted 389102f5 with bounded qualifications; final calendar bytes are unchanged.
  - The CI publication-harness dependency and screenshot hashes are already repaired in af666f37.
  - The Fabric calendar acceptance call failed with INVALID_ARGUMENT and retry_allowed false; same-carrier status showed NOT_ACCEPTED. Do not blind-retry or relabel the worker formally accepted.
danger_areas:
  - A raced REST prefix is discarded entirely; a partial label does not make stale ownership safe.
  - An old aggregate correction repairs history without becoming a new live quote.
  - Initial, daily, and 24H accepted history all need the retained-snapshot fence, including equal-data background observations.
  - Unknown non-U.S. future session closes remain unknown; static intraday schedules do not imply complete holiday coverage.
  - Strict protected master can move while CI runs; arm only after all source pushes, and verify landed blobs after squash.
discoveries:
  - DSC:TERMINAL-FORMING-CANDLES-NEED-OWNERSHIP-AND-HISTORY-FENCES
decisions:
  - DEC:TERMINAL-ONE-LIVE-BAR-DERIVATION-BOUNDARY
---

## Current state

| Slice | Delivery evidence | Remaining boundary |
| --- | --- | --- |
| First implementation | [Terminal PR 1102](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1102) merged as `ab5beab6b0c2362414a1da17745587d490e923e8`; all 16 CI jobs passed; the release owner and independent readback exited 0. | Initial API/UI observation exposed a pre/post snapshot consumer defect. Native complete forming publication remains separate. |
| Snapshot consumer follow-up | [Terminal PR 1108](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1108), current head `2e7cb8505cc2521d1e3f0e44768bb2ac2df1a9f3`; 119 local tests, TypeScript, six responsive browser cases, and independent reviews passed. [CI run 39704185148](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/39704185148) is running. | Complete protected merge, git-gated deployment, and independent readback. Positive actual pre/post-market movement and rollover are still unverified. |

The PR 1102 readback passed at 2026-10-21T22:00:21Z. All seven installed
source hashes, canonical HEAD, deployment marker, public page/chunk IDs, and
healthy restarted services agreed. Do not rerun that completed deployment.

The initial API observations each returned 39 HTTP 200 samples, with nine
regular-path and ten full-path distinct measured last prices. Both found no
native forming snapshots. The full shape paired a changing
`polygon-snapshot-rt` last with a separate `polygon-delayed` extended quote.
The NVDA 1m ETH chart stayed at its loaded candle with an elapsed 00:00 countdown
between 22:02:11Z and 22:04:01Z. The completed investigation found that the reducer
ignored the qualified snapshot whenever the explicit extended lane was delayed.

PR 1108 repairs that bounded consumer defect. It preserves open/volume, marks
snapshot observations partial, advances the same-price ordering floor, and
permits a native handoff exception only for an extended tick actually admissible
to the pane. The reported production shape and the inadmissible BOATS
counterexample both failed before repair and passed afterward.

## Next uncompleted work

Finish the currently running hosted checks and protected merge. Fetch master
alone afterward, compare the seven owned files against the tested candidate,
and recheck production ancestry before invoking the one release owner. If a newer
deployed generation already contains the change, verify that generation rather
than deploying an ancestor merely to recreate a receipt.

Then verify the follow-up's independent release identity and current-session
health. The U.S. pre/post window is closed at this 2026-10-22T01:20Z checkpoint.
Fixture evidence cannot substitute for positive post-fix market movement.
During the next eligible window, record the exact served SHA, qualified price
updates, preserved open/volume, and a minute rollover/countdown on the actual
chart. Keep that claim separate from native complete OHLCV activation.

## Recovery and evidence

The owned Terminal worktree is
`/Volumes/Mastermind 2/agent-workspaces/claude/5600d31ffa29643a/candle-snapshot-eth-20261021-e269ba04536443f9`,
branch `claude/ssd-candle-snapshot-eth-20261021-e269ba04536443f9`.
Candidate `845e2b558d42f4c80d0108a93cc51ac3235a9631` was refreshed onto
`187bf9582b3deba2de49b597e29ccce6356333d3` as current head
`2e7cb8505cc2521d1e3f0e44768bb2ac2df1a9f3`; all seven owned files match.
Once merged, treat this branch and checkout as historical recovery references,
not a carrier for new work.

The reducer SHA-256 is
`adb523b37703f7c338846cf151268efe1f59dfe2be0cb41c7e6b30fbc766cf80`.
The consolidated snapshot suite contains 47 cases, including the retained BOATS
regression. The final combined run contains 119 cases. Browser fixtures check
the rendered price tail and sync lookup, preserved preceding bar, exactly one
rollover generation, and countdown `00:50 → 00:40 → 00:58`.
Committed captures and their explicit fixture qualification are in
`docs/verification/live-candle-snapshot-2026-10-21/`.

M2 recovery artifacts:

- `/tmp/candle-snapshot-final-unit-20261021.log`
- `/tmp/candle-snapshot-tsc-20261021.log`
- `/tmp/candle-snapshot-e2e-20261021.log`
- `/tmp/candle-snapshot-ci-watch-20261022.log`
- Original immutable release evidence: `/tmp/candle-release-identity-20261021.py`,
  `/tmp/candle-release-identity-20261021.json`, and `/tmp/candle-deploy-20261021.log`.
- Follow-up readback: `/tmp/candle-snapshot-release-identity-20261021.py`;
  default receipt `/tmp/candle-snapshot-release-identity-20261021.json`.
  It requires a full intended SHA and matching page and chunk ID sets. Source
  identity is assessed alongside the exact successful build/deploy and service
  health; an old environment-derived Hub build label is not source identity.

## Invariants and hazards

DSC:TERMINAL-FORMING-CANDLES-NEED-OWNERSHIP-AND-HISTORY-FENCES records the ownership,
correction, accepted-history, shared-calendar, and price-observation invariants.
DEC:TERMINAL-ONE-LIVE-BAR-DERIVATION-BOUNDARY remains the integration owner.

A complete snapshot may retract high, low, or volume. Partial observations must
preserve opaque accepted history and never claim unseen volume. A new history
response wins over a retained snapshot even when the arrays compare equal.
An inadmissible overnight value must not admit an older native revision.
The calendar consumes existing chart grouping and leaves unknown future closes
unknown. Preserve the overnight provider boundary, seconds capability and auth
gates, and the native chart-engine workstream's separate holds.

## Native publication boundary

The source census inspected Macro PR 8660 at immutable head
`6cc0858fa93fa3200268390c9588bcc67358eb23`. Its README and activation record
described pure components without a deployed socket owner, daemon, publisher,
R2 endpoint, or admitted feed lease. Its matured-minute pressure-context
projection is not unfinished OHLCV. Those dated records are not a current
runtime custody census.

Before activating the existing Hub forming path, reconcile current producer,
socket, and publication custody. The admitted candle publication needs a
versioned schema, symbol/session and basis, true UTC interval bounds, OHLCV and
source-condition semantics, source/receipt/publication clocks, producer
generation and revision, coverage/watermark/gap state, and stable bar identity.
Correction replacement, reconnect generations, raced-seed rejection, and
accepted-history fences must survive that boundary.

Keep the delayed Hub socket, the REST snapshot leg's 8000 ms TTL, the Next
seconds-band guard, and the overnight boundary until that producer is admitted.
A TTL does not promise a fresh price every eight seconds. No second vendor
socket or raw paid frames become part of the public quote payload. Fix a latency
target and observation window before the genuine regular-session pilot, then
prove rollover, corrections, reconnects, and coverage.
