# Source-bound audit: repeated Personality W3 shadow events (2026-10-09)

**Research-only. Proven historical source-ledger identity issue; NOT a live trade failure, not a 2h/3h/4h stock winner.** Original company study owner: Personality Signal Suite W3 (`engine/personality_gate_shadow.py`). Healthcare research owner [#8718](https://github.com/mastermindx-market-intelligence/macro/issues/8718). No second event ledger, signal engine, runtime, or worker is created.

## Measured facts from immutable existing GitHub vintages

The July 27 version of `data/personality_timing/gate_shadow.jsonl` at [commit c77843e3](https://github.com/mastermindx-market-intelligence/macro/blob/c77843e3a3cd78/data/personality_timing/gate_shadow.jsonl), blob `79e75c9599753ebeebb11157024c2f691a6733eb`, contains **158 rows on 2026-07-26 and 158 on 2026-07-27**. Each day has **176 fired comparator-side event legs** because 18 rows fire both sides. **All 176 July 27 event legs repeat the same (symbol, comparator side, timeframe rung, entry date) identity as July 26; zero are new**. The wall-clock as-of alone changed.

The August 10 version at [commit b3d3c38b](https://github.com/mastermindx-market-intelligence/macro/blob/b3d3c38bdce5cd/data/personality_timing/gate_shadow.jsonl), blob `02c73db07fbae00251a843591081623d3d912305`, spans **15 publication dates** from July 26 to August 10, with:

| Measure | Direct source observation |
|---|---:|
| Ledger rows | **1,427** |
| Fired comparator-side observations | **1,658** |
| Unique source event-leg identities | **441** |
| Repeated side-leg appearances on later days | **1,217 (73.4%)** |
| Maximum publication days of one unique event leg | **15** |

Identity includes *side*, so a valid simultaneous uniform/tailored fire is not counted as a cross-arm duplicate. It is within-side republication of the same source bar. The selected 23 healthcare names had only five represented in the sampled ledger: **BMY, BSX, ISRG, PFE and ZTS**; across those, 25 publication rows carried **34 fired legs but only 6 distinct event-leg identities** (28 repeats). That is not sufficient for a five-name strategy result. BSX and ZTS appearing here does not imply their separately generated `site/signals` surface exists in October.

## Causal mechanism in source, not inferred from price performance

[Source code at e01cfb9e](https://github.com/mastermindx-market-intelligence/macro/blob/e01cfb9e9706e0ffbbfa6f1b41383aca42aed4d1/engine/personality_gate_shadow.py): `_fires_on_latest_bar` compares `dates[-1]` to `bars.index[-1]` but does **not** require that a new fully completed source candle has arrived as of this nightly scan. `_scan(root, as_of)` publishes every still-latest fired bar under the passed wall-clock `as_of`, and `update` deduplicates by `(as_of, sym)` only. Same-day reruns are idempotent; a new day with unchanged source bar is not. [Existing tests](https://github.com/mastermindx-market-intelligence/macro/blob/e01cfb9e9706e0ffbbfa6f1b41383aca42aed4d1/tests/test_personality_gate_shadow.py) test same-day idempotency, not two consecutive days on an unchanged last candle.

The source `_timing_shares()` counts graded ledger rows by arm, **not independent source event identities**. As a result, raw row counts and standard errors derived from treating every row as a new fire can be misleading. The current [state file](https://github.com/mastermindx-market-intelligence/macro/blob/e01cfb9e9706e0ffbbfa6f1b41383aca42aed4d1/data/personality_timing/gate_shadow_state.json) reports 6,302 rows and 116 matured grades, but **this audit did not read or regrade its full current JSONL**. Neither its raw count nor its unpaired forward-return medians can establish a per-name timing winner until the duplicate and timing contracts are reconciled.

## Required repair by the incumbent owner only

1. Bind source-event identity to symbol, side, rung and a verified **completed/knowable** source candle timestamp (not wall-clock publication day; `entry_date` is only a proxy because some bars are left/open-labeled).
2. Record a source crossover **once**. Retain existing immutable PIT event rows; do not silently delete or rewrite graded prior publications. Historical regrading needs a named distinct research cohort.
3. Add a test that scans identical price history on two consecutive `as_of` days and produces zero additional fires. Also verify a truly new completed bar, side/rung distinctions, stale-source abstention and weekend/holiday behavior.
4. Build a deduplicated, matched-opportunity comparison with time/name/episode clustering and the previously preregistered bottom-timing ruler; do not choose per-name best-of grids, which are killed by the existing PTT adjudication.
5. Confirm any producer/consumer write change through the incumbent source-custody, CI and production acceptance gates. **This research PR does not alter that owned engine.**

## Reproduction scope

The independent offline audit prototype (Python stdlib; eight synthetic tests passed) is available as a separate conversation attachment; **it is not incorporated into this repository PR**. The counts above were separately obtained from the exact archival GitHub JSONL source bytes through read-only parsing. The short accompanying [machine-readable receipt](SHADOW_EVENT_WITNESS_2026-08-10.json) freezes the source refs and denominators.

**Mission frontier:** healthcare best-strategy ranking remains unproved. The previously denied host historical OHLC backtest/replay is not retried or bypassed by this GitHub-ledger assessment. No trading, benchmark admission, CI bypass, production signal change, model/account switch or background worker was claimed.
