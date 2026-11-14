# Preserve requested historical index population in the canonical grader

Date: 2026-11-14 UTC. Parent: Chairman's November 13 entry/regime-confluence commission;
WS:PROPHET-CONDITIONAL-FUSION, related research PR #11241 and Linear MAS-120.
This is a bounded input-correctness repair, not the completion of the broader
strategy program or MAS-120's earlier species/analogue project.

## Discovery and economic consequence

The canonical `engine.grading.as_of_panel` promises a point-in-time population.
Its PIT loader read `src` (sp500/sp400/sp600) but then discarded that column when
normalizing the frame. The downstream group filter was therefore unreachable.
A request for sp500, sp400 or sp600 silently returned the union while marking it
`pit`. This can confound a historical experiment's population even with perfectly
computed prices, signals and statistical tests. The fixed eleven-name mechanism
pilot does NOT use this membership function and is unaffected.

A second boundary existed: if the requested group's historical selection was
empty or group identity unavailable, the old code could retain the unscoped union
or fall back to today's survivors. Missing index history is not proof that an
index had zero members, and neither is permission to widen a declared universe.

## Bounded correction

The loader preserves optional `src`. An explicit group is filtered jointly with
its historical start/end tenure. Missing identity, absent group or no recorded
members at that date returns an empty `cold-start` panel with an explicit unknown
coverage note. No such request silently broadens. Existing as-of-ledger priority,
unscoped PIT membership, and the legacy unscoped cold-start behavior are unchanged.
No return formula, barrier, exit rule, price adjustment, trial, live ranking,
position size, grade store or trade execution changed.

## Ownership and exact source

Protected procedure: Mastermind `8323d7a774a72da20d0e4db21c9080398da185e7`.
Macro repair base: `e2a90d858053ec8da814b1d83225318017ff3083`.
Original source first observed at `6bbc4b0fc694c847077661ff5bf4c19ea41e4e81`;
these two native grading files had no intervening changes. Adjacent open #11001
owns grading_stats/calibration files, not these paths. No other writer or its PR
was taken over. The original pilot remains isolated and its native source bytes
unchanged while its process runs.

Single Studio-owned repair operation: `entry-pit-group-repair-20261114`, branch
`sol/web-entry-pit-group-repair-20261114`. The acquire response was unqualified;
same-owner status reconciled the exact clean workspace/base before any edit.
There was no cross-carrier retry or alternate source checkout.

## Verification and genuine consumer proof

Twelve new population-identity cases were added to the existing canonical grader
test file before the fix: **9 failed / 3 passed**. After the correction, the existing
grader, grading-spine and universe-history suites report **179 passed / 1 skipped**.
The skip is the existing optional real-data test in the sparse checkout. New tests
cover all three groups, tenure, loader preservation, unknown/case-mismatched group,
missing source/group column, empty historical selection, unchanged unscoped behavior
and as-of-ledger precedence. Existing CI ownership already executes this test file;
no workflow, permission, check, budget or gate was changed.

The real source membership Parquet at the repair base has 3,286 rows, SHA256
`7b34316c0561619ba052f02036ec1fbe7fff3d00dcda3e7acb7dffda10582eca`.
The repaired existing `as_of_panel` consumer matched direct source group/tenure
selection exactly in nine checks (three groups at January 2 in 2015/2020/2025).
Counts are retained in `entry_pit_group_repair_2026_11_14.json`.

Notably, the source records no sp600 members for the 2015 sample date. This now
reports unavailable group history, NOT a proven empty historical index and NOT a
fallback to other index members. Exact agreement with this source does not prove
its historical completeness or the availability/adjustment basis of member prices.
Those remain separate research qualification requirements.

## Release and rollback boundary

This source repair uses the repository's ordinary protected delivery controller
and exact-head binding checks. No direct/admin merge or invented independent
approval is authorized. PR publication, green local tests, controller enrollment
and actual merge remain separate receipts. Rollback is a source revert through
the same delivery path; historical grades are not rewritten automatically.

## Coverage-label correction from current source inspection

A bounded source-presence audit found that the repair base already contains an
expanded dead-name store (352,598 rows / 426 names). Therefore the inherited fixed
claim that pre-2025 dead-name prices do not exist was no longer supportable. The
PIT note now says only what this function proves: source group/tenure selection,
not historical completeness, member-price coverage or adjustment basis. All nine
real-source cases were rerun after this note correction; 179 tests still pass.

The audit also finds missing basket-OHLCV files for 154 of 499 recorded 2015 sp500
members, before considering the separate dead-name store or archived/alias sources.
That is a file-presence diagnostic, NOT a count of definitively unavailable prices
or a declaration that the expanded dead-name store is unqualified. Exact dates,
identity, source eligibility and basis still need their own existing-owner checks.
