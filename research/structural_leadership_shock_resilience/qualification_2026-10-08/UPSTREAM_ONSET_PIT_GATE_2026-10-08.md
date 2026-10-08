# SLR-P0 — upstream Detector-D point-in-time admission gate

Date: 2026-10-08. Existing Macro PR #8645; research-only, no live or historical outcome values inspected. Protected law pinned to `Mastermind@c7e47c859eb2925c5626931fd511800773ba09ac`. Macro source examined at `eefddf818163c557c2c7aabba05f02a4325b34d2`. Frozen SLR v1.0.1 unchanged (`4136eebc1d57b6d6c682403f1735849c5f9589f4`).

**NEW EVIDENCE: PARENT_ONSET_BENCHMARK_PIT_UNQUALIFIED. This is a data-provenance failure, not evidence that the SLR hypothesis failed.**

## 1. Exact source observation

`scripts/research/build_winner_autopsy.py`, git blob `6d33934bef3ab5f4dc6ce24e060045cfe4220cee`, contains:

- `_TICKER_SECTORS_PATH = _DATA / "breadth" / "ticker_sectors.parquet"` (line 68).
- `_load_sector_of()` (lines 256–268) loads a **single** `ticker -> sector` dictionary from that file, with no event-date, effective-date or knowledge-time argument.
- Full historical `--backfill` passes the same dictionary to `detect_episodes(working_bars, bench_closes, sector_of)` (lines 1018–1022).
- The live/latest watch path similarly passes `sector_of` to `compute_watch_states` (line 1122).

`engine/winner_autopsy.py`, git blob `32ae63b2a91e26f3aebff08e2badd8c566acd088`, resolves the sector ETF benchmark from `sector_of.get(ticker)` and `_GICS_ETF` in `_resolve_benchmark` (lines 185–200). `detect_episodes` selects that one benchmark before computing historical 21- and 42-session excess returns (lines 240–290); the detector threshold is part of onset admission. If a mapping is absent, the engine may use SPY fallback, which is a different benchmark and has explicit `benchmark_fallback` metadata.

**Derived consequence:** even if every later SLR challenge-day peer were repaired with correct GICS-at-C labels, the original onset date D and its prior canonical `continuation` status might already have been selected using an incorrect contemporaneous sector benchmark. This is not repairable by merely replacing a column in the resulting episode table.

This conclusion is about the **source-construction contract**. We have not replayed the retained parent with date-varying data and do not assert the number of contaminated episodes. The initial `winner_episodes.parquet` was harvested at 2026-07-07; a present sector mapping is not historical proof for 2014/2018. The previous study's own input census showed 915 mapped and 922 SPY-fallback broad 2014–2025 onsets, but those are initial-source metadata, not counts of actually corrupted onsets.

## 2. Concrete falsifier of time-invariant classification

The original 2017 MSCI/S&P joint GICS restructuring announcement and November 2018 implementation reminder document movement including Alphabet and Facebook from Information Technology to Communication Services. They also distinguish effective dates for GICS Direct versus MSCI equity indexes.

- https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=C8yMx%2BzdSX8%3D
- https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=A83vYj52YoU%3D

This shows that static GICS assignments **can** be wrong for historical dates. It does not quantify misclassification in the SLR parent, and it cannot itself substitute for an issuer-by-date classification file. SEC historical SIC is a different taxonomy and cannot silently reproduce the GICS transition.

## 3. Minimum admission proof for frozen parent identifiers

**Preferred preserving approach** after actual historical GICS and security identity are positively qualified:

1. On the **unchanged original historical prices**, use a date-indexed sector classification and the frozen, existing `_GICS_ETF` map to evaluate the original Detector-D candidate conditions at each historical session, including benchmark selection, exchange calendar, adjusted-price basis and cooldown. Do not update thresholds, dates or outcomes.
2. For every existing canonical onset D, record whether a fully prefix-causal replay reproduces **both onset eligibility and its first-onset/cooldown identity**. The proper check is full prior-path replay, not just `excess_21d` re-evaluation at D; earlier newly eligible candidates can change the first onset.
3. Likewise verify canonical prior-day watch `continuation` with classifications and prices known/valid by C−1. Re-evaluate only with the declared prefix and without future labels.
4. Partition strictly: `REPRODUCED_EXACTLY`, `DIFFERENT_ONSET`, `NO_LONGER_QUALIFIED`, `UNOBSERVABLE_HISTORY`, `SPY_FALLBACK_WITH_HISTORICAL_SECTOR`, and `SOURCE_BASIS_CONFLICT`. Record counts and source digests for all, without opening forward labels or picking winners.
5. For the frozen `canonical Detector-D onset` SLR population, **do not silently replace a historical onset with a new one**. An unchanged, correctly reproduced parent subset can proceed to the other admission tests if the frozen specification allows its exclusions and statistical power. If meaningful parent replacement is required, publish a **versioned, pre-outcome research amendment** describing the changed population and why its estimand differs. Never rewrite the accepted W3/W4 census or its immutable evidence.
6. Missing dated classifications, issuer lineage, exact price returns, trading-session records or benchmark history must produce an abstention/unobservable status. “Map agreement today” is not historical evidence.

**Important:** a naive filter keeping only episodes whose modern sector equals a newly found historical sector at D still misses the cooldown/earlier-onset issue. A per-name complete-prefix candidate replay is required to prove that an onset is the same mechanical event.

## 4. Scientific decision

The October 7 frozen protocol assumed canonical Detector-D parent onsets were admissible historical identities; this source inspection finds that assumption **unqualified** for PIT sector benchmarking. Reusing the original parent without a source-parity filter may undermine the claim even after historical shock peers are fixed.

The prior independent blockers remain:
- **Historical GICS:** current sector file cannot establish era-correct classifications.
- **Historical security-to-issuer lineage:** current `IssuerMaster` has no historical `asof` reader.
- **Vendor report-time / filing-time:** dated ticker details can include later-filed facts unless knowledge time is separately reconstructed.

The new critical-path ordering is:

`qualified historical sectors + issuer/security identities -> outcome-blind Detector-D parent parity -> first-shock incidence/controls/power -> independent mechanics verification -> historical development outcomes, if still admitted`.

No code changed. No existing live detector, publisher or owner needs to be rewritten for this audit. No protected CR1/AF1 states or outcomes were accessed. The existing research-spec and kill/no-redo boundaries remain unchanged. This research finding does not itself authorize rerunning the original winner census or introducing a second canonical episode store.

**Current classification:** NEW_PIT_PARENT_DEPENDENCY_IDENTIFIED; FROZEN_EXPERIMENT_NOT_ADMITTED; mission incomplete.
