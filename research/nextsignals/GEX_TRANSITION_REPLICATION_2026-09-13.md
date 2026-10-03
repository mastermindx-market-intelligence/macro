# nextSignals GEX-transition hypothesis — independent Mastermind replication

Status: `NOT_PORTABLE_AS_GENERIC_MASTERMMIND_GEX_SIGNAL`. Research result only. No trading, portfolio, ranking, source-runtime, or deployment authority.

Procedure pin: protected Mastermind `9ed16bf0fcc5b47e870350ff2413ff5c8c73b447`, Sol Skillpack 1.0.1, bootstrap major 1. Macro source/evidence base observed at `aa6750b68ccefeb17043e590b61e8a00565d1837`.

## 1. Question and external hypothesis

Public nextSignals material advances a specific refinement of conventional GEX use: the signal is said to live in **transitions**, not the static GEX number. The June 22 note describes GEX as a vulnerability/instability variable rather than a directional forecast. The August 9–10 material further argues that abrupt support loss can matter while gradual erosion gets bought, and that a fast GEX decline with IV still quiet differs from a decline accompanied by a volatility repricing.

Relevant public source locators:
- https://x.com/TailThatWagsDog/status/2069010251207024944
- https://x.com/TailThatWagsDog/status/2086586019684434031
- https://x.com/TailThatWagsDog/status/2086777156697227282
- https://x.com/TailThatWagsDog/status/2087903847226175683
- https://x.com/TailThatWagsDog/status/2088414279800160691
- https://x.com/TailThatWagsDog/status/2089489844388958436

This study tests transfer into Mastermind's own **reconstructed assumed-sign index-ETF GEX history**. It does not claim to reproduce nextSignals' SPX formula, Signal Sigma data, SqueezeMetrics data, dealer inventory, or private implementation.
## 2. Frozen method

The SPY specification was frozen before reading forward outcomes. A separate cross-index specification was then frozen after the SPY result and before reading any QQQ/IWM/DIA forward outcomes. No thresholds were retuned by instrument or after results.

Primary input is the existing `data/index_gex_history/{SPY,QQQ,IWM,DIA}.parquet` plane. It is reconstructed from ThetaData EOD Greeks × OI and carries the dealer-sign assumption already documented by the Options Sensor contract. Primary analysis keeps `tier=full` only.

Source fingerprints used in this run:

| Root | Full rows | Window | SHA-256 |
|---|---:|---|---|
| SPY | 2,431 | 2017-01-03 → 2026-09-03 | `003f645ead6ebd525986915e382295f8fd1390557f1804475744b76360887c50` |
| QQQ | 2,431 | 2017-01-03 → 2026-09-03 | `4661129df2a012d51a9b8f98be64edf7078cda801876cbc56df12020bf3c79b6` |
| IWM | 2,429 | 2017-01-03 → 2026-09-03 | `93d361efc005f2dbd1051edeb2d7f70645992572ea2648f2d29789f8b40f0089` |
| DIA | 2,419 | 2017-01-03 → 2026-09-03 | `4d6fcb0d80f32bdb005f5915800b0e930775143c1f208ba22bff211912b8a478` |

Frozen transition features use only current and strictly-prior information: daily ΔGEX; its z-score against the prior 252 sessions with ≥126 observations; same-day ΔIV30; and a separately specified GEX-change residual from a prior-only rolling regression on same-day ETF return. Primary source-like events were `NEG_QUIET` = ΔGEX z ≤ -1.5 with ΔIV ≤ +0.5 vol point, and `NEG_REPRICED` = ΔGEX z ≤ -1.5 with ΔIV > +1 vol point. `FAST_NEG` = ΔGEX z ≤ -2.0.

Outcomes were frozen as next-5/10/21-session return, path maximum drawdown, path maximum run-up, and annualized realized volatility. The fixed temporal robustness split is 2017–2023 versus 2024–latest. Twenty-session block bootstrap, 5,000 resamples, and BH-FDR q=0.10 were used for descriptive uncertainty; correlated ETF histories are never pooled as independent trials.
## 3. Main result — the quiet-unwind transfer fails

The source-like claim does **not** generalize as a generic Mastermind ETF-GEX rule. At 10 sessions, `NEG_QUIET − NEG_REPRICED` produced:

| Root | Forward return Δ | Max-drawdown Δ | Realized-vol Δ | 2024+ max-DD Δ |
|---|---:|---:|---:|---:|
| SPY | -0.88 pp | -0.40 pp | -2.25 pp | +0.55 pp |
| QQQ | +0.15 pp | +0.75 pp | -2.81 pp | +0.75 pp |
| IWM | -0.08 pp | +0.34 pp | -2.70 pp | -0.18 pp |
| DIA | +0.58 pp | +0.94 pp | -4.55 pp | +0.69 pp |

For maximum drawdown, negative means the quiet event was worse. Only SPY is worse in the full sample; in the 2024+ slice SPY reverses, and three of four roots show *less* drawdown after quiet compression. The forward-return sign is also mixed across instruments.

The fixed tail summaries tell the same story. Probability of a ≥3% path drawdown within 10 sessions was 27.9% vs 20.2% for SPY quiet vs repriced, but **15.7% vs 34.1% for QQQ, 28.3% vs 34.7% for IWM, and 10.9% vs 31.0% for DIA**. At 21 sessions with a 5% drawdown floor, SPY was 16.7% vs 14.8%, while QQQ/IWM/DIA were 24.0% vs 28.8%, 19.2% vs 29.7%, and 9.4% vs 22.9% respectively.

A particularly important falsifier is volatility: quiet compression had **lower subsequent realized volatility in all four full samples**. This is inconsistent with treating the frozen quiet-unwind formulation as a general higher-volatility warning.
## 4. Fast negative GEX velocity also fails as a generic risk warning

`FAST_NEG` events were common enough to test (SPY 68, QQQ 95, IWM 78, DIA 91). Yet the frozen normalized event did not increase 10-session realized volatility versus eligible non-event days: differences were -3.14 pp SPY, -2.28 pp QQQ, -0.90 pp IWM, and -2.95 pp DIA. Ten-session path drawdown was not worse in any of the four full samples.

This does not establish that abrupt SPX dealer-gamma transitions are useless. It establishes a narrower and operationally important point: **the public nextSignals transition story cannot be copied into Mastermind by applying a generic normalized ΔGEX rule to our reconstructed ETF series.** Instrument ontology, source construction, expiry aggregation, dealer-sign convention, and volatility/term-structure context matter.

The public nextSignals material itself contains this warning in another form. August 17 explicitly says a large GEX unwind accompanied by a VIX repricing was a bad reason to exit, and the August 14–16 `GEX building faster than price explains` condition is labeled watch-only / not robust in testing. Signal Sigma public posts likewise show that GEX behavior is conditional: negative GEX can create both sharp declines and sharp rallies, and positive GEX breadth can sometimes mark exhaustion rather than upside support.

## 5. Mastermind ruling

Do **not** add the nextSignals 8bn/4bn/2bn SPX thresholds, the `quiet unwind` rule, a raw ΔGEX velocity alert, or a `faster than price explains` trading rule to `engine/gex_state.py`, Prophet, Neural Web origination, Risk Radar, or portfolio sizing.

Keep the existing GEX authority boundary intact:

- current `options_structure.gex_state/v1` remains display-tier;
- its dealer-sign basis remains explicitly an assumption;
- LLMs may narrate/de-escalate but do not originate or escalate signals;
- same-day SPX and SPY GEX can disagree materially, so absolute cross-instrument threshold transfer is invalid;
- public nextSignals/Signal Sigma findings remain research hypotheses, not inherited authority.

The useful capability gained here is a **negative transfer result**: we can stop spending cycles trying to transplant this simple GEX-transition family into the existing Mastermind options stack.
## 6. What remains worth testing

The corpus suggests richer, mechanistically distinct hypotheses that were **not** tested here and must not be smuggled into this result: expiry-specific GEX/zomma/vomma interaction, term-structure state, same-tenor GEX replacement after OpEx, strike-shelf migration, and 0DTE intraday hedging transitions. Those require aligned per-expiry/per-strike point-in-time data and their own preregistrations.

The highest-value continuation is therefore not another threshold sweep. It is to finish the corpus system inventory, then map only genuinely non-duplicative concepts into the existing Options Confluence / Options Sensor owners. A future GEX-transition upgrade is worth reopening only if it supplies a different measurable state than the current stability/flip/topology views and survives source-matched replay plus forward shadowing.

## 7. Reproducibility and evidence boundary

The private Chairman research package preserves the frozen preregistrations, deterministic analysis script, complete JSON outputs, block-bootstrap/FDR tables, and source hashes. Raw licensed option data and creator media are not copied into this repository. The derived findings above are sufficient to reproduce the decision boundary from an authorized source checkout.

This record does not accuse the external publisher of error. nextSignals primarily discusses SPX and uses a different data/aggregation stack; Mastermind tested a transfer hypothesis on index ETFs under its own reconstructed assumed-sign series. The correct conclusion is **non-portability**, not external falsification.

## 8. Acceptance and exact next action

This research slice is complete when this record is merged with green repository validation. It establishes neither a new GEX feature nor product completion. Existing production GEX behavior is intentionally unchanged.

Exact next action in the corpus program: move to the next non-overlapping system family — gold regime / debasement / yen-differential and crypto ETF-flow intelligence — while keeping PR #7104's acquisition carrier separate and leaving the active SCE Quant Lab worktree untouched. Any product change from those systems requires its own frozen hypothesis and independent acceptance gate.
