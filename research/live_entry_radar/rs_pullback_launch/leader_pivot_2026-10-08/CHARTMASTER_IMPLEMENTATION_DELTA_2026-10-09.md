# RS Leader Pullback / ChartMaster-inspired pivot: implementation delta and acceptance frontier

**Recorded:** 2026-10-09 (UTC). **Parent:** `WS:LIVE-ENTRY-RADAR` → `RS Pullback Launch` → existing Leader Pivot research. **Carrier:** Macro draft PR #8649, branch `sol/leader-pivot-publication-p0b30m-20261008-c1`. This is an additive research-and-repair note, not a new workstream, new alert engine, new ledger, or authority grant.

## Executive engineering decision

1. **Finish the existing detector stack.** `engine/us_leader_pullback.py`, `engine/entry_radar/replay/rs_pullback_launch_data.py`, the research-only `leader_pivot_descriptor.py`, and Terminal's existing `entry_radar.json` consumer already exist. A parallel production radar is not warranted.
2. **Keep the patterns distinct.** Existing `completed30m-rejection-same-session-v0` is an *undercut/reclaim* construction, not the public first-green-candle construction attributed to ChartMaster. A first-green comparator must receive a separately frozen definition/version, its own synthetic negative controls, and its own matched economic test. A public mirror is not a complete trading rulebook; do not assert exact private-method replication.
3. **Repair normal CI before widening live publication.** GitHub Actions run [37855750221](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37855750221) failed the `research-price-panel` pack: the Phase-1 test wrapper imported `test_entry_radar_leader_pivot_descriptor` as a top-level module and raised `ModuleNotFoundError` in ordinary pytest. The nested test files shared these top-level sibling imports. The repository has a `tests/__init__.py` package. This carrier's package-qualified import correction retains all original assertions and the existing 65-case nested suite. **A committed correction is not CI proof: qualify its actual run before merge.**
4. **Admit real source data before predicting.** The exact checked-in `PHASE1_ADMISSION_2026-10-07.json` still says `NOT_ADMITTED` and `H1/H2/H3: NOT_TESTED`. Synthetic pivots, source-capture code, successful unit tests, screenshots, and retrospectively corrected bars cannot substitute for a coherent market witness or evidence of an executable entry.
5. **Preserve old owner contracts and authority.** No new lifecycle, store, source decoder, campaign, signal ranker, position sizing, or automatic trade. Existing Phase-1 refusals, same-source reader custody, actual data availability clocks, and Terminal episode semantics remain intact.

## Existing owner census, source and collision boundaries

| Layer | Verified owner / reference | Current bounded conclusion |
|---|---|---|
| Daily leader reset | `engine/us_leader_pullback.py` (Macro main) | Computes LEADER, PULLBACK, RESET_TURN and RESUMED display states. Its original 5–20% close-basis pullback and 260-session history can exclude shallower or young leaders. Do not silently loosen its incumbent v0 |
| Minute aggregation, daily context, incumbent comparison | `engine/entry_radar/replay/rs_pullback_launch_data.py` | Supplies decision-scoped 15m/30m aggregates, PIT guards, eligibility and source refusals. Daily context uses `is_leader` and `controlled_pullback`; it does **not** require the daily RESET_TURN label |
| Current Leader Pivot | Macro [PR #8649](https://github.com/mastermindx-market-intelligence/macro/pull/8649), source head `6da88ab7cd25726e927f5c80e4e33bab23110494` at recovery | Formation plus pure frozen confirmation, invalidation and expiry projection; 65 isolated synthetic conformance cases reported; no registered detector, real witness, probability or current release |
| Capture and raw basis | Macro [#8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623); Terminal [#844](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/844) | Separate draft owners. Retained 1m observations are not equivalent to a reconstructable adjustment-basis receipt or installed qualifying feed. Do not take over their source files |
| Identity and custody | Macro [#8637](https://github.com/mastermindx-market-intelligence/macro/pull/8637) | Separate draft identity observation owner; coherent writer-consumer snapshot and installation remain dependent work |
| Terminal display | `terminal/lib/dislocations/source.ts`, `types.ts` | Existing shared episode-file consumer, freshness and delay display. This specific pivot is not yet proved enrolled and displayed in a real browser |
| Parent completion law | `agentos/workstreams/WS-LIVE-ENTRY-RADAR.md` | Preserve existing Radar truth, intelligence, product and prospective-learning gates; do not declare completion from a child PR merge |

## Why the two 30m patterns are non-equivalent

- **Current rejection v0:** completed current 30m candle has a low strictly below the lowest low of four prior same-session completed 30m candles, closes above that floor, and closes in its upper half; it can be red. Four bars of warmup plus the target candle exclude early regular-session pivots. Frozen high is confirmed by a later completed one-minute **close** strictly above the high plus a caller-declared buffer, not by a touch. Invalidation uses a later completed minute's low below frozen low minus buffer with same-minute failure precedence.
- **Public first-green account:** the first completed green 30m candle after a decline, with subsequent high break and initial stop reference at its low. The available public instructions leave the precise decline/population, premarket/regular-session treatment, gap handling, equality, high-touch versus close-break, adjustment basis, persistence, reset/rearm and exit policy underspecified.
- **Toy counterexample 1:** previous floor $99; current 30m O=99.40 H=100.20 L=99.20 C=100.00: green higher-low reversal, but *not* the rejection v0 because no undercut below 99.
- **Toy counterexample 2:** previous floor $99; current 30m O=100.40 H=100.60 L=98.80 C=100.00: red candle, but valid rejection v0 because of undercut, reclaim and upper-half close.
- **Decision:** treat these as rival hypotheses, do not rename `PIVOT_FORMED` to `FIRST_GREEN`. Implement the green research comparator as additive versioned logic and preserve per-variant full-population denominators.

## Proposed first-green comparator contract (no private-rule fidelity claim)

For bounded research, first predeclare a candidate at an eligible decision timestamp through the existing Phase-1 owner. Use fully completed 30m aggregates from the same declared session and source/basis/identity. Require a current green candle (`close > open`) preceded by an explicit, contiguous sequence of at least one red (`close < open`) candle. Other sequence definitions are separately frozen alternatives; never retroactively tune streak lengths from winners. A flat/doji candle is neither red nor green under v0. If price revisits a low later, preserve the original candidate and its failure; do not repick a more favourable pivot.

A research break-of-high variant may observe the next **completed 1m close**, while a separate intraminute-high-touch variant requires quote/clock and executable fill assumptions unavailable to an OHLC-only exact-order reconstruction. Same 1m minute containing an invalidation and a break is ambiguous; classify conservatively rather than inventing tick order. Use the incumbent `known_at` and source-read receipts. Record the event candle time, decision/first knowable time, actual issue time (if any), and later outcome cutoff independently.

This construction is *proposed* pending implementation and tests, not a shipped detector. Do not introduce a second runtime or source authority to implement it.

## Admission, comparison and stop rules

**Source gates:** qualified security identity across historical corporate actions; stable OHLCV price/volume basis; retained source response and read receipts with true first-seen clocks; exchange session and exceptional-day calendar; genuine complete 1m and 30m windows; eligible prior-day leader context; actual incumbent assessment. Preserve `UNAVAILABLE` and absent/no-event distinct. The inspected bridge uses a 900s finality hold; do not label a 12:00 event as a 12:00 executable alert when first knowable at 12:15. Obtain a separately supported lower-latency feed if live execution is the intended product.

**Pre-registration:** compare (a) incumbent entry, (b) primitive same-information price/time/volatility benchmark, (c) rejection v0, (d) green v0 on the *same* daily cohort; then separately test shallow-leader and post-earnings watchlist cohorts without contaminating incumbent thresholds. Separate forecast endpoints for 30–120m local stabilization, close of session and predeclared multi-session swing horizons. Include entry price, stop execution path, slippage, spreads, failures, abstentions, repeat entries, gap outcomes and per-episode rather than winner-only outcomes. Never import unobserved future data, use hindsight tickers, or tune on chronological holdouts.

**Falsifiers:** if no incremental timing benefit versus a strong matched baseline, keep geometry descriptive, not predictive. If savings vanish after observed-source lag and execution costs, do not advertise improved entry economics. If earlier signals cause excess false starts and tails under common risk, reject early anticipation. If peer strength or news labels fail own missingness/PIT controls, keep them explanatory instead of a hard gate.

## Bounded execution sequence and DONE_WHEN

1. **Normal CI import repair:** package-qualified imports in the existing four test files; run exact normal repository selection; pass nested 65 cases with zero unearned skips, and produce exact tested-head CI proof. Keep PR draft if any check fails.
2. **Source witness:** use separate current source owners' completed deliveries, produce one source-admitted market witness through the existing 1m selector and completed-30m descriptor; independently check source vintage, basis, identity and cutoff. Do not relabel synthetic observations.
3. **Green comparator:** implement separate pure version/contract plus regular, early-session, doji, gap, late-correction, double-touch, equality, expiry and invalidation negatives. Freeze comparator before reading outcomes; no live signal authority.
4. **Radar enrollment and UI:** use the existing canonical episode path, no new event ledger; reveal descriptive state, candidate rationale, staleness, formation/confirmation clocks and unavailable reasons. Pass real signed-in Terminal browser test plus read-replay parity.
5. **Economic/prospective evidence:** matched controls, chronologically held-out outcomes, implementation costs, false-start denominators and forward shadow receipts. Probabilities, rankings, execution or aggressive sizing require separately earned gates.
6. **Acceptance:** complete truth/intelligence/product/learning checks from parent LIVE-ENTRY-RADAR, verify install, selection, actual production payload and user path individually. Draft delivery is not `PROVEN_LIVE`.

## Research provenance and confidence boundaries

The companion prior read-only audit is a local conversation artifact, *not* already canonically stored on GitHub. Its public-source reconstruction used first-person strategy posts mirrored from social media; mirroring and partial exposure limit fidelity. Descriptive market-mechanics hypotheses are inference, not proof of private ChartMaster rules or institutional intent. The original 14-chapter Mastermind report and all negative research outcomes remain controlling and unmodified. This delta adds only new comparison and implementation priorities.

**As-of / proof split:** current protected Skillpack revision `mastermindx-market-intelligence/Mastermind@326c8469a21d7f50fc9ecb1848196bf1c6e66685`; Macro baseline PR head `6da88ab7cd25726e927f5c80e4e33bab23110494`; CI failed run 37855750221; no new real-market acquisition, prospectively confirmed edge, release, deployment, or live trade represented by this note. Any later repair commit requires its own readback, normal CI and real-path proof.

**Frontier:** after this note and import repair, validate normal suite CI and then close the existing real-source identity/basis/first-seen witness without trespassing on #8623/#8637/Terminal #844 carriers. Continue independent green-comparator pure research only while source/market gates remain held.
