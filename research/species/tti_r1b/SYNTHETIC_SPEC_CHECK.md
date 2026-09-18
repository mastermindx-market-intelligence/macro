# TTI R1-B v3 synthetic specification check

**Evidence class:** synthetic-only pre-run specification validation. **No market data read, no outcome opened, no TrialLedger mutation.** This check does not change the frozen v3 preregistration or config and does not establish a trading edge.

Bound inputs:
- v3 prereg SHA256 `3b3d44979715dcf43b1e71a678c9b263485bdef124abaef959fee60273571aa7`
- v3 config SHA256 `62628e9666dda22565c6f6123b80044b86a7fe5ae51f6bd3bd9b6f9915d74bed`
- study id `tti-r1b-exhaustion-reclaim-v3`
- frozen grid 60 cells
- one full five-minute processing-latency bar after decision/confirmation.

Nine deterministic synthetic cases were executed against a small independent transcription of the frozen recipe to ensure the prose/config have one coherent operational interpretation before registration:

1. meaningful strict fresh low + qualifying forming exhaustion;
2. equal low does not qualify as a fresh low;
3. zero-volume candidate is unavailable;
4. reclaim wins on the first confirmation bar and the price-reference entry is candidate index + 3 (one confirmation bar + one full processing bar before the next open);
5. continuation can win before a later reclaim;
6. unresolved three-bar confirmation window expires;
7. a zero-volume confirmation bar makes the confirmation race unavailable rather than a non-fire;
8. a base candidate can become RECLAIM_ONLY without satisfying EXHAUSTION_FORMING;
9. selected events and matched controls obey the same `delay + 2` candidate-index entry-offset law, including immediate selectors.

All nine cases passed. The authoritative implementation still does **not** exist: this is a prereg consistency check, not a shadow engine. When the shared R1-A source gate clears, implementation must be written test-first against the frozen v3 bytes and the full 60-cell TrialLedger registration must predate every R1-B market-data outcome read.

The receipt in `SYNTHETIC_SPEC_CHECK.json` is the machine-readable evidence. V1 and v2 remain DO_NOT_RUN audit artifacts.
