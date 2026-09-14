# Theme Observation Integrity W0 — Design

**Operation:** `theme-observation-integrity-w0-20260910-sol-001`
**Authority:** Chairman-approved Sol architecture freeze, 2026-09-10
**Source base:** Macro `d675bbece0848e8587e4070b576e7585e02b5a19`
**Scope:** data/measurement integrity only; no user-interface work in this wave

## 0. Outcome and acceptance

A theme may speak as a whole only from a coherent observed population on a real common market session. A date present only as an all-null index row is not an observation. Dated membership eligibility is not price coverage. A benchmark may not be forward-filled across a terminal missing session to manufacture a common date.

This W0 is complete only when:

1. `nuclear_power` is evaluated on all nine configured live members on the latest coherent session, or the aggregate read explicitly refuses.
2. `memory_storage` is 4/4 or refuses; `semicap_equipment` is 16/16 or discloses every missing member; `power_grid` cannot silently become an OKLO/SMR 2/24 read.
3. An all-null terminal row in the breadth caches never becomes `effective_as_of`.
4. Complete coherent fixtures produce byte-identical price panels, score inputs, labels and recommendations.
5. Existing risk-direction transition logic is untouched; BVI-R1 remains true.
6. Every theme row carries an inspectable observation receipt: configured live population, present columns, actual observations, missing members, coverage, effective session, and whether the aggregate read was admissible.
7. Baskets and theme scoring use the same common observation date. Group Pulse may legitimately use its own OHLCV date, but its own date and denominator remain explicit rather than silently borrowed.

## 1. Verified failure

At the audited 2026-09-09 artifact generation, the three broad US close caches contained a terminal session row with zero populated prices. Their last actual population observation was 2026-09-08. `lib.closes_panel.merge_close_caches()` treated the raw maximum index label as the panel tip. `engine.group_flow._setup()` then added only extras tickers absent as columns, and `engine.theme_scoring.compute_theme_intel()` scored `len(idx)-1`.

That reduced the theme-scoring population without a refusal:

- nuclear: 3/9;
- AI semiconductors: 4/12;
- memory/storage: 0/4;
- semicap equipment: 2/16;
- grid/electrification: 2/24.

The Baskets producer, Group Pulse and Foresight used different source planes, so the final page combined different populations and dates under one apparent theme verdict.

## 2. Existing-owner extension, not a new plane

The canonical owner remains `lib/closes_panel.py`, already the shared US breadth-cache merger and price-basis integrity layer. W0 extends that owner with observation semantics; it does not create a new state store, score, ranker, theme lifecycle, queue, registry or authority plane.

- **Group Reads** continues to own participation evidence.
- **TIL** continues to own theme lifecycle/evidence composition.
- **Theme scoring** keeps its existing formulas and risk rules.
- **Group Pulse** keeps its frozen `group_pulse.v1` coverage/refusal contract.
- **Baskets** remains the equal-weight member tracker.

## 3. Data contract

### 3.1 Panel observation

`merge_close_caches()` must distinguish:

- `raw_tip`: latest index label present in any source frame;
- `tip`: latest returned row with at least one actual price observation;
- `all_null_rows`: every source-calendar label where no returned ticker had a value;
- `dropped_all_null_tail_rows`: the terminal all-null suffix removed after the last effective observation.

Only the terminal all-null suffix is removed from the returned panel. Interior all-null rows remain explicit historical outages rather than being compressed out of time. Never-populated columns remain present; their `behind` value remains `-1`. Per-ticker source selection and measurement-gated whole-column stitching remain unchanged.

### 3.2 Common benchmark session

A shared pure helper aligns a price panel and benchmark close to the latest date where:

- the price panel has at least one actual observation; and
- the benchmark has an actual close on that date.

It trims data after that date and emits a receipt. It never terminal-forward-fills the benchmark. Historical benchmark gaps inside the retained calendar may continue to use the incumbent behavior; W0 closes the terminal-vintage defect only.

### 3.3 Basket population receipt

A shared pure helper receives a close panel, dated membership and an effective date and returns:

- `effective_as_of`;
- `configured_n`: members whose `[added, removed)` window is live;
- `in_panel_n`;
- `observed_n` at the effective date;
- `missing_columns`;
- `missing_at_asof`;
- `coverage`;
- `status`: `complete`, `partial`, or `insufficient`;
- `aggregate_eligible`.

Minimum admissibility follows the established Group Reads floor: at least three observed members and at least 60% configured coverage. This is a measurement floor, not a market signal. A partial but admissible row remains explicitly partial. An insufficient row may not originate a parent score, label or recommendation.

## 4. Correction behavior

- The effective session follows the latest real common observation, not wall clock and not raw index maximum.
- A later corrected source generation can move the effective session forward; the receipt records the new source facts.
- No price is silently filled from a different source merely to reach a fresher date.
- Existing whole-column source/basis rules remain in force.
- The change is deterministic and idempotent for identical input files.

## 5. Theme-scoring behavior

For every configured basket:

1. Build the dated live membership at the effective session.
2. Compute the observation receipt before any aggregate scoring leg.
3. If `aggregate_eligible` is false, append a typed row to top-level `observation_refusals` and do not run the score/label/recommendation path for that basket.
4. If admissible, compute existing formulas on the actual observed members and attach `observation` to the theme row.
5. Preserve existing labels, recommendations, ordering and risk transitions for complete coherent fixtures.

Refused rows are not fabricated as neutral themes and are not silently counted as observed themes. The refusal list is additive and inspectable by current/future consumers without forcing a Theme Tracker UI change in W0.

## 6. Baskets behavior

`compute_baskets()` aligns its close panel and SPY to the same common-session contract before returns, chart dates and member snapshots are built. Each basket row gains the same `observation` receipt. An insufficient basket is omitted under the existing skip behavior, with a line-start Actions warning and a top-level `observation_refusals` record; no half-populated basket prints indistinguishably from a complete one.

## 7. Non-goals

- No score-weight, threshold, label, recommendation, rank, or lifecycle changes.
- No correlation or dispersion gate.
- No rotation × cycle confluence.
- No new composite.
- No Theme Tracker builder/template edits; PR #7010 owns those paths.
- No point-in-time backfill or historical membership reconstruction.
- No row-by-row splicing across adjustment bases.
- No changes to Group Pulse's frozen schema in this wave.

## 8. Failure and degradation rules

- No panel observations: producer returns its incumbent unavailable/`None` state.
- No common benchmark session: producer returns `None`; it does not relabel a stale session as current.
- Malformed membership dates remain governed by the existing basket-registry validation/failure contract; W0 does not create a second validator or reinterpret malformed intervals.
- Coverage below floor: typed refusal, no aggregate score.
- Coverage at/above floor but below complete: score remains possible only with explicit `partial` receipt. This preserves the current Group Reads floor while preventing silent survivor arithmetic.

## 9. Production proof

After unit and integration tests pass, run a read-only replay against the exact committed current cache artifacts in an external receipt directory. The proof must print:

- raw versus effective panel tips;
- dropped all-null sessions;
- nuclear, memory, semicap, grid and defense population receipts;
- complete-data parity hashes for a synthetic control;
- zero committed `data/` or `site/` mutations.

A green test suite or merged PR is not production proof. The current real input must traverse the repaired code path and produce the intended denominator/date result.
