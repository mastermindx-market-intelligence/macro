# TOI W2 Daily-first observational-unit ruling — 2026-10-06

Program: WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE.
Original W2 carrier: Macro #7094 / TOI-W2-0-DATA-CLOCK-V1 at 5bb1bc68c99146fab040aade04bbf1903c51e5b7.
Evidence carrier: #8332.
Disposition: TICKER_SPELL_UNIT_PROPOSED / SCIENTIFIC_ADMISSION_STILL_HOLD. MISSION_COMPLETE:false.

The price-coverage return established that most remaining uncertainty is membership and identity semantics rather than absence of Daily files. This ruling defines the narrowest observable unit that can be constructed before outcomes without inventing historical issuer identity.

## Proposed observational unit

A membership-bounded vendor-ticker spell is the maximal run of Daily observations satisfying all of the following:

1. the ticker is inside the union of PIT S&P1500 membership intervals under the existing inclusive interval law;
2. one unique canonical Massive vendor object resolves through the established exact dot-to-dash join only;
3. every expected NYSE session in the run has a Daily source row;
4. the run never crosses an actual S&P1500 non-membership hiatus.

A continuous S&P600 to S&P400 to S&P500 promotion does not reset the spell when union membership remains continuous. A missing expected source session does reset it. A later re-entry after a real non-membership hiatus starts a new spell. BPFH and UAA/UA remain unresolved and produce no admitted spell unless an owner resolves them before outcomes.

This unit makes only a vendor-ticker observation claim. It does not assert uninterrupted issuer or security identity. Current Data OS aliases are never backdated. Every unavailable PIT member-date remains visible in the coverage ledger rather than being silently removed.

## Source-only census

The census used the same canonical R2 source generation as the prior price-coverage pass and read only parquet date indexes. The R2 manifest remained byte-identical. Seventeen transient connection resets in the first pass were reread once against that same manifest and all recovered; no scientific missingness was inferred from transport failure.

Final source-only results:

- 1,924 PIT membership ticker keys;
- two unresolved vendor keys;
- zero unresolved read errors;
- seven ticker keys have two separate union-membership episodes;
- 3,024 membership-bounded source-contiguous spells;
- median spell length 572 NYSE sessions; p90 1,285; max 1,318;
- 3,017 spells are at least 20 sessions, 1,914 at least 60, 1,869 at least 126, 1,802 at least 200 and 1,767 at least 252;
- 1,918 ticker keys have at least one spell at least 20 sessions and 1,760 have one at least 252.

Those generic session-length counts are readiness diagnostics only. They are not TOI lookback choices or evidence that any model is supported. Each eventual native config must apply its own declared warm-up entirely inside one spell.

## Scientific consequence

This rule prevents three unsafe repairs: using first price as a fabricated listing or membership start, stitching across a source gap, and bridging an index non-membership hiatus after seeing outcomes. It also avoids creating a second security-master system.

It does not prove corporate security continuity inside a spell. The scientific owner must either accept the narrower vendor-ticker-spell estimand and generalization or require a stronger historical identity source before registration. That choice must be frozen before outcomes. An authoritative corporate-action snapshot remains independently required by the current basis ruling.

Until owner adoption, population status remains HOLD. This ruling does not choose a cleaner cohort, register a trial, fit a model or open W3.

## Manifest consequence

The companion Daily-first 22-object manifest draft binds this proposed population block by content digest and keeps all unresolved source, corporate-action, solver, inference and holdout settings fail-closed. Planning fingerprints are drift guards only, not TrialLedger identities.

No market outcome, OHLCV value, model output, TrialLedger write, production mutation, Prophet rank/gate/size or trading authority was produced by this ruling.

