# Structural personality adjudication — healthcare pivot research (October 9, 2026)

**Status: research-only extension to PR #8726 / issue #8718. No new market result, production gate, automated trade or optimal stock/timeframe claim.** This is an evidence-and-collision reconciliation after the original V2 assessment was published. The original V2 report and JSON are preserved unmodified.

## 1. Decisive pre-existing evidence: do not audition a winner for each name

The canonical research precedent is [PTT §6 and §8](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/research/PERSONALITY_TIMING_TAILORING_HANDOFF_FOR_FABLE.md) and the [pre-registered W1-T report](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/reports/ptt_w1_timing_regrade.md). **This work MUST NOT re-propose `DNR:KILL-OUTCOME-AUDITION`.** [The kill registry](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/research/DO_NOT_REBUILD.md) bars selection of each ticker's historical best-performing technical tool as a live gate or decision authority.

The held-out prior study covered **1,300 eligible names and 109,974 TEST signals**, testing selection methods under both a forward-return and a bottom-timing ruler:

| Pre-existing result | Observation | Proper interpretation |
|---|---:|---|
| Per-name in-sample best tool ranked among TEST top two, forward-return study | **33.2% vs 33.3% chance** | No persistent per-name winner |
| Same audit after switching to timing-ruler selection | **35.0% vs 33.3% chance** | The timing-ruler re-test did not rehabilitate audition |
| Structure-derived W1b-pure versus random, median 63-day adverse-excursion uplift | **+0.41 percentage points; 95% CI [+0.13, +1.16]** | Supports measurement-first tailoring on this prior study's scope |
| Structure-derived W1b-pure versus random, within-5%-of-low uplift | **+5.87 percentage points; 95% CI [+3.51, +6.43]** | Supports timing quality on the prior registered ruler, not exact bottoms |
| `called_low` share for the structure-derived tool | **8%, versus 8.4% ambient base** | This tool is better described as a **reset confirmer**, not a precise bottom caller |

These values are **existing repository evidence**, not newly rerun healthcare-specific tests. W1b-pure was an **S-family StochRSI tool at a rung derived from past-only price-path structure**, rather than the best historical P&L among candidate tools. This is the construction to GENERALIZE, subject to fresh intraday validation; it is not blanket evidence that the same 2h/3h/4h formula will succeed.

### JNJ illustrates why "best timeframe" must name its ruler and n

The prior full-sample defensive ladder table shows JNJ timing-ruler U_MAE of:
- 3D: **+0.56 pp (62 events)**
- 1W: **+0.42 pp (34 events)**
- 2W: **+2.32 pp (13 events)**
- 1M: **+2.73 pp (6 events)**

The 1M cell has the largest point estimate on **this** measure, but only six events. Its forward-return-ruler "home" was **1W**, not 1M. Across seven named defensives, five changed their "best" rung when the evaluation criterion changed. **It would be misleading to prescribe JNJ's monthly rung from these cells**, and none of them directly evaluates an intraday 2h, 3h or 4h clock. Preserve all counts, objectives and exposure caveats.

### Distinguish the two products

1. **Tactical pivot probe (1–3 sessions):** can identify an earlier, riskier attempted reversal using price structure and completed lower-timeframe evidence. Must show failed attempts and unconfirmed cases.
2. **Confirmed reset/swing continuation (5–20 sessions or longer):** deliberately pays more confirmation cost to reduce adverse excursion. Later is not always worse; existing research finds the lag can be load-bearing.

Do not mark an eventual 3D confirmed signal as an intraday buy on its earlier open-label date. Compare opportunity recall, shake-outs, adverse excursion, delay, actual executed returns and giveback separately. The owner must choose the intended product/ruler **before** ranking anything.

## 2. Shared structure-derived intraday hypothesis — not 23 outcome-tuned recipes

For exploratory 2h/3h/4h work, use one **pre-registered cross-stock feature-to-clock rule** rather than 23 independently fitted best-of grids. Example proposal **NOT YET IMPLEMENTED OR VALIDATED**:

1. **Past-only structural input:** trailing 252 completed regular sessions plus a fixed, earlier-vintage warm-up. Candidate descriptors: first-order autocorrelation of aggregated returns per clock, Kaufman-style past-only path efficiency, share of movement attributable to overnight/event gaps, swing persistence and data coverage. Corporate actions, early closes, partial bars and missing sessions have explicit coverage abstention.
2. **Measured reversion-by-scale:** choose the clock from an **ex-ante fixed structural rule**, e.g. the most negative stable lag-one return autocorrelation across the *fixed* clock family, with a deterministic tie rule and a pre-registered minimum-sample/stability gate. This is a descendant **hypothesis** of W1b, not an accepted transposition of its 3D/1W/2W measurement. Two windows (e.g. 126 vs 252 sessions) are stability diagnostics, never an opportunity to select whichever looks best in outcome.
3. **Separate signal-family choice:** if a completed daily context and actual price structure support continuation, evaluate trend-pullback; if a support break fails, evaluate sweep/reclaim; after a timestamped material shock, evaluate event-base repair. The family rule must be specified and learned cross-sectionally, not chosen after observing the current ticker's eventual winners.
4. **Abstain on unreliable structure:** insufficient bars, unstable ranks, gap-dominated calendars, ambiguous event knowledge, or a current unfinished required candle yield a fallback baseline or `INSUFFICIENT_EVIDENCE`, **not** a forced personalized clock.
5. **Outcomes validate; they never select per-name tools:** compare the single shared measured-structure routing hypothesis against fixed 2h and 4h baselines and the native multiday confirmation context. Hold exit policy fixed. Use chronological, held-out-name and held-out-event tests, plus clustered uncertainty and matched opportunity/exposure.

The initial **18 study cells** in `strategy_spec_v2.json` are therefore a diagnostic coverage matrix for falsification, **not** permission to deploy each stock's historical winner. If a trial ledger counts cells, all attempted variants and clock-artifact controls must be recorded without data-driven cherry-picking. Do not infer that any one of JNJ/LLY/ABBV/MRK/UNH is currently in the trend, range or repair state.

## 3. Additional source-law and data caveats

- [Personality Signal Suite masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/research/PERSONALITY_SIGNAL_SUITE_MASTERPLAN_BY_FABLE.md) already shipped a display-tier [Personality Timing Codex](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/scripts/build_personality_codex.py) and [W3 forward shadow](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/engine/personality_gate_shadow.py). They are the existing owners for structure measurements and eventual accrual. Do not create a second codex, shadow ledger or regime selector.
- The same masterplan says pre-registered vol×trend class-specific gate selection **did not earn** a distinct class altitude. The PSS F1–F4 and SR1–SR3 standalone timing constructions carry existing negative rulings. New tests must show genuine mechanism differences, not renamed rejected combinations.
- [Healthcare member-dispersion adjudication](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/research/HEALTHCARE_MEMBER_DISPERSION_ROTATION_NOTE.md) explicitly **rejected** a new XLV construction-divergence buy router and relative-strength member-dispersion gates. XLV/peer relative strength may remain **descriptive context or a separately admissible research control**, not an automatic scored buy/short/position-size rule. Existing holdings were latest-only at the earlier adjudication; historical weights must not be backfilled from a current holdings snapshot.
- `DNR:KILL-DIRECTIONAL-SHORTING` means an extension warning or avoid flag is not authorization for directional short signals. Keep top-risk detection, long-profit-protection and any independent short study separate.

## 4. Do not duplicate current live research surfaces

- [Swing Confluence planner, PR #8642](https://github.com/mastermindx-market-intelligence/macro/pull/8642): a draft research-only reusable saved-recipe planner and tests; **not yet an admitted intraday backtester**. Where an accepted recipe contract exists, use it instead of creating another planner.
- [Leader Pivot P0B-30m, PR #8649](https://github.com/mastermindx-market-intelligence/macro/pull/8649): draft 30-minute frozen-reference/confirmation/failure/expiry descriptor with synthetic conformance tests; **not production-proven on the real market path**. Consume its eventual admitted evidence; do not copy its implementation into the healthcare research lane or claim its current draft validates our 30m clock.
- [Native signal quality](https://github.com/mastermindx-market-intelligence/macro/blob/60778ff68aea185c1769420c99d3ce878c911012/engine/signal_quality.py) already owns 3D RSI-MACD/Stoch confluence and two-bucket quality confirmation. Reuse its causal timestamps and source-calendar owner. The old separate research simulator's retrospective fill caveat does not mean all current consumers leak.

**Integration seam:** once these incumbents and research-access gates admit work, the healthcare spec supplies *frozen per-setup research hypotheses, stock-specific test coverage, failure definitions and evaluations* to the existing recipe/replay/TrialLedger pathways. It creates no second signal engine, new producer of trading decisions, branch-colliding worker or buyer authority.

## 5. Required validation and stop decisions

| Gate | Needed evidence | If not satisfied |
|---|---|---|
| Native math | One exact Wilder/EMA/Pine parity contract, with NaN and warm-up behavior tested | Do not compare indicator clocks as though values were equal |
| Candle and clock | Exact NYSE session calendar; no incomplete bucket promoted; research and live weekly gates reconciled | Defer affected signals, never backdate eligibility |
| Event and cost | Pre-event ATR and documented event time, adjusted references/raw executable fills, conservative stop/target ordering | Report `UNTESTED` / refuse event policy claims |
| Trial construction | One shared frozen feature-to-clock algorithm, recorded baselines and trials; no per-name outcome audition | Do not infer ticker-specific optimal clocks |
| Outcomes | All eligible attempts; separated tactical/confirmed horizons; MAE/proximity/shake-out/opportunity capture/net expectancy; cross-stock/event holdouts | No candidate is a winner |
| Consumer proof | The existing owner accepts research outputs under current authority and production/browser proof | Remain `RESEARCH_ONLY` |

**Current boundary:** no historical-market evaluation was run in this continuation because the prior original-host analytic repair/census action received a tool denial. The research-only source analysis and GitHub documentation writes are independent, but **no model/tool/carrier workaround** for that denied action is authorized. The exact next empirical action is safe same-owner reconciliation of the original denial and lawful permission for a genuinely new governed market-data validation using the existing TrialLedger/replay infrastructure. No worker, background return, scheduler or paper/live trade is claimed.

**Sources frozen for this supplement:** `macro/main@60778ff68aea185c1769420c99d3ce878c911012`; protected master procedure `Mastermind/master@326c8469a21d7f50fc9ecb1848196bf1c6e66685`.
