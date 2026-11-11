# Adjudication of the independent RUN-D re-derivations (2026-11-11)

Two independent re-derivations of the published beta evaluation
(`site/prophet/beta_evaluation.json` at Macro `c3d967b9fd`, protocol header sha256
`3be32166…2ada` @ `07f1c9cd8c`, data pin `b5a5c846f8b5…`) reported differences:

1. **ChatGPT Pro run D** — `/tmp/rotation-core/pro_runs/PRO_RUN_D_answer.md`
   (also Macro issue #11014), 15 numbered differences, full independent code.
2. **Kimi re-derivation** — `/tmp/prophet-eval-rederive/REPORT_RUN_D.md`,
   14 unblinding differences (large overlap with run D).

A third independent run (the stock-minus-sector diagnosis,
`/tmp/prophet-eval-diagnosis/REPORT.md`) reproduced the event-study table to 6
decimals and motivated deviations D7/D8 in the correction.

**Method.** Every finding below was reproduced on this engine before receiving a
verdict — nothing was taken from either report on trust. Verdicts:
`CONFIRMED DEFECT` (engine/runner behaviour wrong, fixed with a regression test),
`CONFIRMED DISCLOSURE` (numbers right, presentation incomplete, fixed in the
artifact/docs), `CONVENTION` (frozen header decides, or the header is silent and the
incumbent reading is defensible — disclosed, sometimes with a sensitivity),
`NOT CONFIRMED`. No frozen rule, comparator, seed, population rule or data pin
changed; the header hash is verified before every run. The corrected artifact is a
dated CORRECTION that retains every superseded figure beside the corrected one.

**Bottom line.** Two engine defects confirmed and fixed (final-close trade cost;
price-cache bytes unverified against the pin). The verdict does not move: the release
stays **L0 descriptive**, every headline interval still spans zero (corrected C6
−3.2351% total, +1.4108 pp vs SPY, CI [−10.509, +13.221]). The stop rule was checked
before the correction was written.

## Findings

| # | Finding (run D §; Kimi) | Verdict | Evidence reproduced on this engine | Disposition |
|---|---|---|---|---|
| 1 | Reference basis: excess measured vs gross SPY index, not costed C1 (D-1; both) | CONVENTION + disclosure | C1 identity exact: costed C1 = SPY gross − 3 bp entry (−4.6745% vs −4.6459%, excess −0.0286 pp). Gross-index basis is the header's `excess_total_vs_spy` | `vs_passive_market.reference_basis` note added; C1 row always carried the costed number |
| 2 | **Final-close trade cost computed but never consumed** (D-2; Kimi fee item) | **CONFIRMED DEFECT** | toy book: 2 sessions, {} target at final close — cost vanished in v1, charged now. Full book: C6 costs 1.1826% → 1.2822%, total −3.1382% → −3.2351%, excess +1.5077 → +1.4108 pp; C3/C4/C5 terminal rebalance now charged (≤0.2 pp); C1/C2/X6 unaffected | engine `simulate_book(charge_terminal_trade_cost=True)`; deviation D6; regression test `test_terminal_trade_cost_charged_at_final_close` |
| 3 | Fee timing (next-day application) wrong? (Kimi) | NOT CONFIRMED | cost at close d enters `(1+g)(1−pending_cost)−1` at d+1 — the correct one-day carry; both re-derivations agree after reading | no change (test `test_c1_passive_held_through_invariant_under_flag` pins the entry-cost case) |
| 4 | Missing held marks zero-filled (LFUS, SBH) (D-4; Kimi) | CONVENTION + **CONFIRMED DISCLOSURE** | exactly 2 entered positions (LFUS, SBH) hold assets whose closes stop in-window; engine holds them flat (`stale_asset_days` 31 counted but never itemised) | `coverage.held_path_gap_positions` list, `held_path_gaps`/`held_path_complete_positions`, sensitivity `missing_marks_total_loss_stress` (−4.4205% total, +0.2254 pp [−11.552, +11.919]); helpers `held_path_gaps`/`first_gap_total_loss_rets` with tests |
| 5 | Coverage statement measures entry marks only (D-5; Kimi) | **CONFIRMED DISCLOSURE** | priced_share = entry marks; the 2 gapped positions pass the gate then run flat | `coverage.priced_share_basis` states the basis; held-path completeness now a separate visible count |
| 6 | ZWS counted missing though pinned; input bytes never verified against the pin (D-6; Kimi) | **CONFIRMED DEFECT** | pin `ls-tree` blob ids vs `git hash-object` over the whole cache: 1,522/1,522 parquets byte-identical, only ZWS false-missing (blob exists in pin), 35 tickers genuinely absent. ZWS was eligible on every date but never selected → no frozen number moves; census 36 → 35 | `load_prices` verifies every blob id, reads pin blobs on mismatch; `PinnedInputs` reads ALL non-price inputs from the pin (fail-closed); `data_clocks.prices.pin_verified`; test `test_load_prices_verifies_against_pin` |
| 7 | Last rule-book rebalance cost dropped (D-7) | **CONFIRMED DEFECT** (same root as #2) | C3/C4/C5 final rebalance target at 2026-11-06 close; v1 dropped its cost | same fix; deviation D3 rewritten to the corrected state |
| 8 | Arithmetic annualisation (D-8; Kimi) | CONVENTION | header names no annualisation; arithmetic (mean × 252) is the incumbent and both re-derivations used it; geometric differs by <8% relative on these horizons | stated in the cost-conventions limitation |
| 9 | Bootstrap draw order / RNG stream (D-9) | NOT CONFIRMED | baseline rerun at the pinned engine reproduced the committed artifact byte-for-byte (except `code.commit`); both re-derivations reproduced every CI to 8 decimals | no change |
| 10 | X6 cost-free arithmetic reference (D-10) | CONVENTION | header defines X6 as arithmetic daily mix "w(t−1) in SPY and 1−w in BIL"; cost-free by definition | already disclosed (headline item on X6); unchanged |
| 11 | No top-three concentration view (D-11) | **CONFIRMED DISCLOSURE** | top-3 contributors AMR/CRCL/TEM; removing them: −5.0104% total, −0.3645 pp vs SPY — the sign of the headline rests on three names | `post_hoc_diagnostics.*.without_top3_contributors` (C6/C7/C6A); headline sentence added |
| 12 | MRNA called "reconstruction"; census 16 vs 17 minted (D-12; Kimi) | **CONFIRMED (labels)** | 17 outage-backfill plans minted overall = 14 receipted replays + 3 synthetic-board reconstructions; era count 16 = 13 + 3; RIO-BULL-20260731 outside the era. MRNA is a receipted replay of the 2026-08-09 bake (instantiated 2026-08-11T05:32:28Z), not a reconstruction | census fields in `population.excluded_cohort` (`overall_minted_outage_backfill` etc.); RESULTS_v1.md line 38 corrected; this table |
| 13 | Superseded block should carry all-plan deltas (D-13) | CONVENTION (as designed) | superseded rows recomputed with the same pinned engine/seed/prices — v1 numbers retained verbatim, now also under the legacy fee flag | unchanged besides the legacy-flag guarantee |
| 14 | Undated conversions not addressed (D-14; Kimi) | CONVENTION (entry rule) + **CONFIRMED DISCLOSURE** | 78 era plans terminal-state `converted` with no dated fill (the `filled_date` key exists, its value empty in all 78 → E falls back to P, matching run D exactly); 68 of them hold clean through the window | `population.undated_conversions` (ids + basis); sensitivity `excluding_undated_conversions`: 430 positions, −5.7289% total, −1.0831 pp [−12.081, +9.522] — still spans zero; helper `undated_converted_ids` with test |
| 15 | "Not authenticated by any second source" now stale (D-15) | **CONFIRMED (stale caveat)** | two post-publication second sources: ChartExchange EOD sweep (62.96 → 174.38 raw/adjusted agree) and Yahoo live-chart API (all 64 sessions) | `population.mrna.price_authentication` updated, labelled as post-publication audit evidence; RESULTS_v1.md line 153 annotated |
| 16 | Sector-fund yardstick conflates member choice with cap-weight drag (diagnosis; CEO ruling) | **CONFIRMED YARDSTICK GAP** | equal-weight same-sector member mean vs ETF: −0.6261 pp [−1.196, −0.043] at H21, −2.1477 [−2.755, −1.442] at H42; picks vs member benchmark −2.4103 [−3.550, −1.303] / −3.2774 [−5.590, −0.703]; placebo (1,000 random-member draws) 95% range [−1.615, +0.490] at H21 and [−3.716, −0.443] at H42 — diagnosis cross-check [−1.65, +0.36] / [−3.80, −0.49] | `event_study.member_benchmark` (deviation D7), own engine code `member_benchmark_event_study` + `event_rows`; regression tests `test_event_rows_ruler_and_legs`, `test_member_benchmark_identity_peers_and_published_exclusion`, `test_member_benchmark_two_peers_placebo_spans_their_range`; frozen event-study numbers untouched |
| 17 | Off-index picks carry a quarter to a third of the event-study gap (diagnosis; CEO ruling) | **CONFIRMED DISCLOSURE** (after-the-fact) | 46 of 732 published plans off the PIT S&P 1500 at the signal date (31 entered positions); H21: their gap −10.4569 pp (n 31) vs members −2.4357 (n 383); excluding them −3.0363 → −2.4357 (contribution −0.6006 pp); H42: −19.3904 (n 24) vs −3.8877, contribution −1.5375 — matches the diagnosis exclusion table exactly | `sensitivity.off_index_picks` (deviation D8) with membership-file limits restated; after-the-fact label |
| 18 | Event-study dropna / misc conventions (Kimi) | CONVENTION | unmatured horizons dropped by rule (matured-only); immaterial to every reported mean | unchanged |

## Corrected headline beside superseded (C6, primary population)

| Figure | Superseded (v1, c3d967b9fd) | Corrected (2026-11-11) | Reason |
|---|---|---|---|
| Total net return | −3.1382% | −3.2351% | final-close trade cost charged (D6) |
| Excess vs SPY (total) | +1.5077 pp | +1.4108 pp | same |
| 95% CI (total) | [−10.4939, +13.3861] | [−10.5090, +13.2209] | same |
| Costs paid | 1.1826% | 1.2822% | same |
| Release level | L0 descriptive | L0 descriptive | unchanged; all gates re-checked |

Commit references: engine + runner + tests on this branch — see the correction commit
recorded in `site/prophet/beta_evaluation.json` `code.commit` (this branch,
`fable/prophet-beta-evaluation-audit-20261111`).
