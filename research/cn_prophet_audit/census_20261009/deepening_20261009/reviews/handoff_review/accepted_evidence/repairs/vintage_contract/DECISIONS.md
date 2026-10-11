# Repaired vintage admission contract

## Producer result and review boundary

The repaired producer suite passes **104 coupled checks**: 44 source/clock/mark checks, 32 retention checks, 22 ledger checks, five empirical-parity checks and one custody check. Its empirical-parity pass checks all **1,332 available historical witness bars** and changes none of their stored shape classifications. The original 1,618-row witness table, including unavailable rows, remains intact. The original vintage laboratory's accepted counts and 289-row P&L comparison are unchanged. [Evidence: results.json; verify.py; ../../reviews/vintage_review/VINTAGE_INDEPENDENT_REVIEW.md.]

This is a hash-bound research contract candidate for independent acceptance. Producer PASS is not acceptance by the independent reviewer or proof of production installation. The original review and the two additional pre-seal interface findings are retained separately; this directory changes neither evidence set. The final acceptance record is to be read alongside this producer memo.

## The contract is now connected across components

**Source to row to field.** The market-mark constructor resolves actual immutable fixture bytes, validates their SHA-256, finds one unique instrument/session row and derives the selected field. A supplied bar must exactly equal that row. The comparator repeats the resolution after deserialization and compares the complete mark with its canonical derivation. Changing its price, row hash, basis, source metadata or calendar reference fails. A free valid-looking hash cannot stand in for source bytes. Duplicate source sessions and duplicate JSON identity keys fail. [contract.py: resolve_row, mark_from_source, validate_mark.]

The explicit JSON codec is a test adapter. Production needs this interface at the incumbent Parquet/price/benchmark owner with genuine basis and availability receipts. A content hash provides content identity, not producer authenticity or historical first-seen proof. The fixture does not relabel any stored historical bar as available at an old decision.

**Calendar to both economic endpoints.** The calendar adapter validates ISO session dates, same-China-date anchor clocks and open-before-close. Entry and exit must exist in the supplied calendar. Publication is at or before the actual resolved entry anchor; grading is at or after the exit anchor and source availability. An optional caller entry timestamp must equal the resolved anchor. September 31, an unrelated October entry clock and a future exit cannot pass. Because source availability is blob-wide, every finalized row in that blob must have closed by availability, including unselected rows. The fixture calendar verifies structure and binding; actual exchange sessions still come from the existing calendar owner.

**Retained observation to admitted price.** `retention.py` and the mark constructor use the same `opening_refusal` function. Malformed optional Open/High/Low values remain visible and preserve the native Close/Volume projection. Numeric strings remain unparsed. Missing, Boolean, zero, negative, infinite, enormous or out-of-range opening values receive explicit refusals and cannot reach return arithmetic as qualified opening marks. The tuple iteration preserves hostile scalar values without pandas Series coercion. The exact native `_extract` method is loaded by AST from the independently verified pinned bytes; no collector or vendor is invoked. Close-only rows still support same-anchor close diagnostics.

**Stored history to append.** Every prior event's content hash, kind, schema, identity, dates and correction relation is validated before replay or correction lookup. The unique original key is `(decision_id, ticker)`. `entry_session` is protected content; changing it cannot create a second original. A correction references an authentic original, retains its identity, states a reason and is recorded strictly later. Exact replay is idempotent; duplicate or damaged stored rows refuse before a proposed list is returned. The prototype is an in-memory admission falsifier. Durable immutability and atomic writes remain the existing store owner's obligation.

These original/correction events demonstrate custody of declared records. They are not execution receipts and do not make their prices admissible to the market-mark calculator; the latter always requires the separate source/calendar resolution. The original seven latch fields are preserved in `legacy_snapshot` with `LEGACY_SOURCE_VINTAGE_UNVERIFIED` qualification.

## Meaning of the output

Every admitted comparison is `ALIGNED_MARK_DIAGNOSTIC` with `MARK_ONLY` status. Entry and exit use one source vintage and one declared basis per instrument, and stock/benchmark anchors match exactly. The result is a price-return comparison. It does not certify total return, fillability, transaction costs, original decision knowability or original economic P&L. An HL2 proxy has no manufactured execution timestamp, and benchmark close is never substituted for a missing open.

The scale classifier now requires positive finite OHLC/ratios. Both zero and negative synthetic common scales return `invalid_ohlc`; a valid positive scale remains recognizable. Every retained actual classification still matches. This is an observable shape label, not proof of a split, dividend, adjustment factor or corporate-action cause.

## Implementation translation

Use the existing benchmark extractor to retain optional OHLC and its existing storage owner to preserve source observations. Use existing calendar and basis/availability receipts to implement source-row resolution; do not install the synthetic codec as a second store. Attach original source/decision identities at the existing entry owner and keep corrections separate from originals. The existing outcome grader should call the coupled comparator only for qualified anchors/bases; other rows retain named unavailability. The original `.SZ` basis dispute, missing historical benchmark opens and absent historical publication clocks stay unresolved where evidence cannot be recovered.

No additional broad experiment is needed to choose these interfaces. Required implementation evidence is the actual adapter wired to real immutable Parquet bytes, real calendar/basis/availability receipts, a natural owned publication/entry cycle, and durable original/correction write/read custody. Those tests cannot be replaced by this fixture's PASS count.
