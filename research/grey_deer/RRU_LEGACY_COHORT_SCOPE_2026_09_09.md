# RRU legacy evidence-cohort isolation

Same operation and research carrier PR6989; starting semantic head60873b4.
Protected Skillpack remains Mastermind686af274d8ae1558f3f3ae35e0b3aae68be80a01.
This is a preregistered, synthetic, in-memory continuation, not a production change.

## Smallest next eligibility step

The repaired serializer preserves modern composition, but existing scorecard,
realized-odds and tuner readers select every graded row regardless of construction.
Modern or malformed-modern rows can therefore influence an explicitly legacy result.
Isolate the legacy cohort once in the existing audit owner and reuse that selector
in all three consumers. An explicitly present composition key is never implicit legacy,
including null/empty/invalid values; absent metadata retains prior legacy semantics.
Expose excluded counts in scorecard/tuner metadata without changing odds-map shape.

Tests must show legacy-only numerical parity; modern-only exclusion; mixed-row parity;
malformed-modern exclusion; and the tuner's sample/Brier calculations using the same
cohort as realized odds. Mock file/path and write boundaries; never open a market,
forward or governance ledger. Retain all input rows unchanged. Baseline must fail first.

This does NOT validate implicit legacy data, enable any modern construction, match
new construction identities for promotion, alter an active restriction, or resolve
the existing runner's legacy-grant attachment bug. Do not clear can_force to hide that
separate failing test. Source cutover and policy transition remain blocked.
The absence-as-legacy convention is only the existing pre-migration schema contract;
any future post-cutover missing-identity rule requires the accepted migration boundary.
No denied read, mutation, packet, translator edit or adjacent-boundary test is repeated.
