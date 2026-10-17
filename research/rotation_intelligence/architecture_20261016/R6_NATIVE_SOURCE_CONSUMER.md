# R6 — Native Tiingo EOD consumer integration

**Mission:** Chairman-directed continuation of the existing sector-rotation-intelligence programme, Macro PR #9507. Sol is responsible for this source-readiness action. The existence of a historical named source owner is not an additional human approval or reason to sit idle.

## Implemented on the same research carrier

- [lib/dataos/sector_allocation_tiingo.py](../../../lib/dataos/sector_allocation_tiingo.py) is a pure function accepting exactly 13 **already returned** native TiingoResearchHistory objects: eleven sector ETFs, SPY and BIL. It does not access the archive, call a vendor, schedule collection, create a data store or open native outcomes.
- It imports the genuine class from the incumbent lib.dataos.tiingo_reader and derives the 253-session/64-price lookback through the incumbent lib.nyse_calendar. Existing consumers, collectors and source authority are untouched.
- It refuses missing/extra instruments, non-native objects, missing/duplicate sessions, different or future capture cutoffs, future outcome rows, malformed receipt identities, foreign source/symbol, wrong basis, non-finite values, within-series mixed vendor adjustment vintages, and forged historical/PIT/redistribution flags.
- The output is an immutable in-memory retrospective projection with original receipt references and content digest. Its safe summary contains coverage and provenance only, not licensed price values.
- **No rights or predictive promotion:** source_use=UNQUALIFIED; evidence_mode=RETROSPECTIVE_EXPLORATORY_NOT_PIT; historical_pit_admitted, as_known_historically, may_rank, may_gate, may_size and may_trade are all false. Callers must still enforce source, scientific and policy gates.

This is a genuine study-specific adapter to the existing source type, **not** a second data reader. It is not a modification to the earlier nine-node/26-session native synthetic input bridge and does not modify its source or protocol.

## Exact source interface

The current source inspection confirmed the same upstream blobs already verified earlier:

| Existing owner source | Git blob |
|---|---|
| lib/dataos/tiingo_reader.py | 7d39cde303d8b4ee3d05a86478e109577ec91411 |
| lib/dataos/tiingo_views.py | 22d6058648bc111313dd0de5e4a679897b7c25e7 |
| collectors/tiingo_archive.py | d5ea5459bad6c687a4aef919b30c8d9fa4a149c0 |
| lib/nyse_calendar.py | 0ece6439ffe4b081ee7a268fe99b69e1de1216a3 |
| config/dataset_registry.yml | ce492d349d91e73cdf962de8dc110aec96a2bfd5 |

The caller must first obtain valid source objects through the existing read_research_history(source="eod-bars", vendor_symbol=ticker, refs=exact_retained_refs, start_market_date=warmup, end_market_date=origin, observed_before_utc=actual_capture_cutoff, acknowledge_hindsight=True) path under its own applicable permission. The new pure project_histories(histories, anchor_market_day=origin, capture_cutoff_utc=actual_capture_cutoff) consumes those already-authorized native results, and public_summary() exposes only safe metadata. **This path was not invoked on private vendor data in R6.**

A passing 253-session projection is still hindsight-only: one 2026 capture of earlier adjusted closes is not original historical availability. The projection requires one internally consistent adjustment vintage per instrument; it refuses unjustified deep-history plus later short-slice splices even if both datasets have hashes.

## Actual test evidence

[21 reference tests](../../../tests/test_sector_allocation_tiingo.py) passed in the local isolated Python 3.13.5 harness (final run 21/21, 0.690 s). The tests began red against a defined unimplemented interface and then passed on the implementation. py_compile passed. The fake data and minimal test-only mirrors of the exact native type/calendar are *not* a real source read or M2 native-test proof. Three clean adversarial mutations to vintage, PIT and session guards independently made their targeted tests fail. Two additional test-first cases reproduced unhandled TypeError from unhashable receipt references and OverflowError from an implausibly large numeric price; both are now deterministic typed refusals.

Committed Git blob equality was checked against executed local bytes:
- Implementation git blob 54f8f71ccd32e774e072b35c051eeda6d269af57, SHA-256 6234e7daf91af96a8a37e0d4d1122a26161efb2668adc0d0c8ec6e5d300e4c0b.
- Test git blob 3310731d8bd9b7f01c5be2d491763a65da4ad06e, SHA-256 23e780828622686a8366cdf713c8a2fe94313f3db0fa39af67874364359b2f95.

## Honest delivery boundary

The Chairman has assigned the current receiver to drive source-readiness work directly; that does not manufacture machine-readable vendor rights or reverse a previous platform-denied private source-inspection action. The first authentic Data OS read, full private payload/revision/session check, exact BIL gap, historical PIT status, and registered empirical baseline remain **unqualified**. The original Fabric worker run remains EFFECT_UNKNOWN on its own carrier; no replay/duplicate is justified. No native P1/P2/P3, Trial/Vault, live provider fetch, trading model, production release, or alternate source authority was invoked.

**Next:** obtain an actually permissible, source-qualified native read that does not repeat the refused action; exercise this adapter on original native objects and repair any specific observed incompatibility, then integrate it through the existing research/evaluation owner only after rights and science gates pass. Keep PR #9507 Draft/HOLD pending real-source proof, exact-head CI and independent review.
