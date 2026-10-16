# Vintage contract repair — design frozen before execution

This repair addresses independent findings V1–V5 against the original laboratory. It does not change the original laboratory, empirical rows, classifications, latch records, source pin, or production owners. Study source remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The original 18-check contract and nine-check retention probe remain evidence about their reviewed versions.

## Falsifiable admission rules

1. A market mark resolves an exact immutable source blob, one unique instrument/session row and its selected field. The comparator repeats that resolution after deserialization. A changed price, row hash, basis, source clock or calendar reference must fail. A syntactically valid free hash string is insufficient.
2. An existing calendar owner supplies the session open and close. Both timestamps must belong to the stated China session date, open must precede close, and sessions must be present in the supplied calendar. Publication is at or before the resolved entry anchor; grading is at or after the resolved exit anchor and source availability. The blob-wide availability clock must be at or after every finalized row's own close, including unselected rows. September 31, a future exit and an unrelated later entry timestamp must fail.
3. Opening admission uses the same scalar/range function as optional-OHLC retention. Missing, malformed, Boolean, nonfinite, nonpositive or out-of-range opening observations stay visible but cannot become an opening mark. Optional-field failures must preserve the exact incumbent Close/Volume projection. Numeric strings remain unparsed and receive a typed refusal. Close-only rows still support appropriately qualified close diagnostics.
4. Every stored original and correction is authenticated and schema-checked before replay or amendment. One original is allowed for each stable `(decision_id, ticker)`. Its entry session is protected content. A separate correction references the original, retains its identity, explains the correction and has a later recording clock. Content hashes provide integrity checking, not signed execution authenticity or durable storage guarantees.
5. A uniform OHLC scale requires finite positive values and ratios. The repaired classifier must preserve every previously retained actual classification; zero/negative synthetic scales must not receive the positive-scale label.

## Test boundary and incumbent implementation seam

The executable uses an explicitly synthetic JSON blob codec and a finite calendar fixture solely to make byte/row/field and clock binding testable. These are not proposed production stores, data feeds or calendar owners. Production must implement the same resolver interface through the incumbent price/benchmark Parquet owner and its genuine basis, availability and calendar receipts. A source hash establishes content identity; it cannot establish who produced the bytes or when the market observation became available. The fixture's declared clocks do not certify historical vendor availability.

All returns are `ALIGNED_MARK_DIAGNOSTIC`, with `MARK_ONLY` execution status. Each instrument uses one source vintage and one declared basis across entry and exit. No total-return, transaction-cost, limit-fill, original economic P&L or execution claim is added. No legacy HL2 proxy is assigned a manufactured timestamp. The seven original latch fields remain unchanged in legacy snapshots; comparisons and corrections are separate.

## Verification sequence

Construct positive source and calendar fixtures; replay original semantic controls through the coupled interfaces; reproduce every independent V1–V5 counterexample with required refusal; test exact native collector Close/Volume compatibility using the already verified pinned `_extract` bytes; recompute the repaired shape classifications across all retained witnesses; preserve exact source/code/results hashes; obtain an independent acceptance pass against the repaired hash. No vendor request, production import, repository source edit, collection or canonical write is involved.
