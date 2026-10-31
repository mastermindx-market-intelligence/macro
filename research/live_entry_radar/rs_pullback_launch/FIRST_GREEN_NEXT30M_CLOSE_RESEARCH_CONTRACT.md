# First green: immediately following 30m close comparator

P1.5 of the existing RS Leadership Suite. Frozen source specification before any market outcome read. It is a research-only comparator, not a claim of exact private-rule replication, source admission, live signal or investment advantage. Original-author replies1911914097999831501 and1912870380693266891 explicitly describe a second candle closing above the first high; the broader discretionary decline and stop/exit details remain unresolved in the original-source evidence ledger.

## Closed definition

Use the existing **one-red** first-green formation and native frozen reference. This comparator does not silently select a two-red origin. The sole confirmation window is the immediately following complete30m candle, from the formation candle's end to that end plus30m, entirely inside the same supplied exchange session. No third/later candle can rescue a failed second candle.

Freeze only after an eligible first-green formation is actually knowable and strictly before that next candle's end. Native reference buffer is a declared research parameter, not qualified exchange tick size. The native reference expires exactly at the next candle's end; a half-day/session-end stub cannot be substituted. The old1m-close confirmation policy stays unchanged and separately identified.

For the new policy, confirmation requires BOTH next-candle C>O and C>frozen_high+buffer, strictly. Equality and doji do not confirm. A high touch or earlier1m close is insufficient. Preserve actual event-window end separately from its first-known and query decision times; this calculation never proves actual issuance, fills or permission to enter.

Risk check: reuse the native progress observer for source/identity/basis/calendar validation, minute-prefix coverage and low invalidation after the knowable formation. A witnessed native low breach is terminal even if later source disappears. At the completed confirmation window, also require its entire low not to breach frozen_low-buffer. This conservatively rejects a breach inside the early part of the window before a delayed formation receipt; when only the window aggregate establishes that fact, report window-level invalidation, not an invented first-breach minute. This is an explicit research choice, not a newly attributed author rule.

Incomplete next candle is WAITING_CONFIRMATION unless a supported invalidation or source refusal already exists. Missing required source is UNAVAILABLE, never a clean nonfire. A fully observed next candle that fails the strict predicates is EXPIRED_NOT_CONFIRMED. A supported satisfying close is GREEN30M_CLOSE_CONFIRMED as a **historical observation** with window_closed=true, not a still-live setup. No post-window price is used to change that observation; later economics/exit belong to the existing evaluation owner.

## One existing owner

Implement only in `engine/entry_radar/replay/first_green_reversal_descriptor.py`. New pure APIs wrap the existing formation freezer and `describe_first_green_progress`; do not copy a minute loop, decoder, source qualifier, event store, scheduler or trading lifecycle. A distinct outer reference binds the native reference and exact window/definition with a consistency digest. That digest is not authentication or authority. The original v0 APIs and outputs must stay unchanged.

All source_admitted, actual_issuance_proven, detector_registered, outcomes_computed and existing financial-authority flags remain false; issued_at remains null. A later query may reconstruct an earlier observation only from source actually visible by that query, and must not backdate issuance. Before the window ends the reader must not inspect an unfinished window as if complete.

## Tests and release gates

Test next-candle close versus1m/touch; green/red/doji/equality; immediate-next only; pending and delayed receipt; source gap before and after delayed formation; native low invalidation and aggregate pre-formation-window low breach; source/identity/basis/calendar changes; reference tampering and unsupported species; early close/stub; future revision invariance; input immutability; all authority false; and exact legacy API/function preservation.

Source-only construction can proceed alongside the pending independent review of the earlier additive variant, because it does not depend on a release or real data. **Release of either change still requires exact-head hosted checks and non-author review.** This is dependency parallelization, not an approval waiver. No historical outcome, holdout or price dataset is accessed for this implementation. Policy comparison and potential trading authority remain under the original scientific protocol.
