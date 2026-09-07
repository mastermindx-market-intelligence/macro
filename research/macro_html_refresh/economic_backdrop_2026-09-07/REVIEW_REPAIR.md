# Exact-head review and bounded parent repair

First independent review: PR6974 `d50deee6479e0820587456b0d2b5505c1f61af19`.
Native review child `macro-economic-backdrop-6974-independent-review-20260907-sol-001`,
actual session `028f69c4-b92f-4b3b-888d-5bc85c699229`, observed Opus5,
Read/Grep/Glob only, no source effect. Exit0 at2026-09-07T06:53:15Z;
head unchanged and worktree clean. Report returned PARTIAL/REQUEST_CHANGES,
not PASS. Public report SHA256:
`8318b8736d3d11767e7f7d9b197fc22a699f153d83076725b7ad6342a3fab0f5`.
Sol consumed and STOPped that finite read-only child in PR6974 comment5566312130.
There is no armed watcher or successor assignment. Sol remains the source owner.

## Findings accepted
MAJOR-1: a blanket reference-period claim is wrong for growth/conditions source
as-of dates. The receipt now distinguishes CPI reference month from source as-of,
and states that calculation/page generation do not refresh economic observations.
MAJOR-2: usable facts with missing or unsupported dates disclose Date unavailable,
in both languages, instead of silently losing their dates beside a known calc cut.
MAJOR-3: source receipt hitboxes now have the same44px floor as Investigate;
actual browser proof must measure both. Date tokens no longer break mid-date.

The internal refusal for an absent required leg no longer records CURRENT as its
reason. Happy-path tests assert all six selected values really resolve. The
runtime stylesheet guard is included in the final verification, not merely assumed.

## Additional false-negative corrected
The first reviewer reasoned that SIMULATED could not influence a headline because
required-source availability excludes it. The real inflation composer at lines268–286
and410–412 explicitly has a positive-weight optional current-month nowcast, carried as
SIMULATED while the required released-CPI set remains LATE_WITHIN_TOLERANCE.

A new test uses that real composer with an available0.2% current-month model input.
It reproduces a healthy required set, a contributing simulated axis component and an
unqualified old headline. The repaired consumer retains the owner's exact state but
adds a visible Includes estimates / 含预估 label. It does not alter model math, make
an estimate an observation, or move the forecast into the released-CPI fact slots.
An absent optional model does not acquire that label; a future model estimate is not
promoted into a new signal or trade instruction.

## Verification scope
Before repair:14 discriminating failures,32passes in the consumer suite. After repair:
46consumer tests pass. The existing dashboard, suite-page and three composer owners
pass together:222tests, no skips, no data-guard exception. The runtime-style-injection
guard reports195JSfiles,45injecting,91hits, all within the unchanged frozen allowances.
The model-presence, date-gap and target-size changes require fresh canonical browser
and immutable-head review proof; earlier d50 captures remain historical, not reused as
proof of the changed UI. The target-size repair is a product usability improvement,
not a claim that this bounded review is a complete WCAG audit.

## Fresh browser result
The real target completed2026-09-07T07:16:05Z with all source hashes unchanged.
The current canonical-interaction receipt passes12cases and3real journeys; every
source-receipt target is44px or larger. Refreshed screenshots use the existing
8-cell capture schema at repaired source commitcdb5a7a2. The earlier d50 snapshots
remain distinguishable and are not the proof of this repair.
