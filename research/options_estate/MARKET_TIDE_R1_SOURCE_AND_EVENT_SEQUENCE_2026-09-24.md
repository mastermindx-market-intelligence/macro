# Market Tide R1 — source eligibility and event-sequence research

Operation: `market-tide-research-20260924-sol-001`. Parent: Macro #7925. Accountable principal: Sol under the Chairman's live end-to-end commission and continuation. Research only; no forecast, position-sizing, trade, collector or production change.

Procedure: protected Mastermind `1a7d400294b0d37c460b963b8865b40a23173b58`, compatible Skillpack 1.0.1/bootstrap 1, freshly verified unchanged. Source investigation: Macro `5ab62e1b7c6635b85dc4f079803c3376c239f2d2`. Records carrier remains PR #7929 / `claude/market-tide-research-20260924-sol-001`; do not move incumbent source work.

## Decision reached

The first conditional study is an **event-and-price benchmark**, not a Greek-driven timing model. Existing historical breadth cannot enter its primary evaluation without historical membership or first-seen observations. Existing intraday GEX failures remain failures for their tested recipes. Macro-event surprise and post-event reaction belong to a separate post-event information set. The dedicated page should preserve the ordered event sequence and unresolved uncertainty rather than color entire weeks safe or unsafe.

This is a completed source/measurement tranche and a frozen research design. It is NOT a completed empirical study: no new market-return panel, fitted model, empirical effect size or portfolio backtest was produced. The original R0 calendar pilot remains unchanged and unexecuted.

## 1. Actual prior-result recovery

The previously cited local MAS-260 checkpoint `700a33c2cedb65d47aacb47b6d9e07a249b865fd` was not resolvable through GitHub. An owner-native read located the incumbent locked worktree on m2studio:

`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/mas260-exposure-baseline-20260918`

Local HEAD: `b281fe529717656e070abaa15651c75fb74bf93f`; branch `claude/mas260-exposure-baseline-20260918`; original remote carrier #7328. Nothing in that worktree was modified. Its scoped receipt status was clean.

The full 84-line `research/options_estate/EXPOSURE_OUTLOOK_CROSS_INSTRUMENT_ABLATION_2026-09-21.json` was read directly, not inferred from Linear. Actual file SHA-256: `5f241659cda73bb9283de75875b630ee79482ff318df674fb3541f095541b975`.

| Existing experiment | Receipt result | Interpretation retained |
|---|---|---|
| Same-day local GEX, 0DTE within +/-0.5% of spot | QQQ 120-minute mean CRPS improvement -0.00007751462099308137; day-block 95% interval [-0.0001519527692306237, -0.000009965495014855024] | Worse in this frozen comparison; no predictive promotion. |
| Same recipe on IWM | One eligible exposure record | Insufficient data, not evidence that all IWM options information is useless. |
| Dynamic multi-expiry, 0–7 DTE, local +/-0.5%, Theta v1, static-OI repricing | SPY 60-minute improvement 4.3373%; QQQ 1.6582% with interval crossing zero; IWM -0.1017% with interval crossing zero | SPY exploratory lift did not transfer robustly. Do not present one successful slice as a general signal. |

CRPS measures distribution-forecast error; these percentages are not investment returns. Original historical availability, Terminal price admission and dealer-side assumptions remain limitations. Reading the receipt verifies its recorded result and identity, not an independent rerun of its underlying research.

The same incumbent's 500-line handoff also reports that widening-only and signed-CQR interval adjustments failed proper-score gates despite coverage changes. That later calibration conclusion was recovered from its handoff, not independently rerun here. Do not attribute its reported 384 passing tests to this turn.

Keep options exposure context-only for those hypotheses. Do not retune them, loosen coverage thresholds, reinterpret static-OI repricing as position build/unwind, or borrow intraday qualification for daily/swing forecasts. A materially different daily event interaction is a new research question, not a reversal of the old verdict.

## 2. Existing source eligibility

All source files below were read at Macro `5ab62e1b7c6635b85dc4f079803c3376c239f2d2`.

| Input/owner | What the inspected source establishes | R1 disposition |
|---|---|---|
| `engine/event_calendar.py` | Unified context-only calendar; FRED release-date override plus static 2026 schedule; OPEX represented by third-Friday arithmetic and a generic 16:00 label. | Reuse current event owner. Not proof of historical schedule vintages or actual contract-specific settlement. |
| `engine/forward_calendar_context.py` | Current 14-day projection, wall-clock date, absent-tolerant context, no new quantitative authority. | Reuse projection; do not call a current snapshot historical knowledge. |
| `engine/neuralweb/market_memory_breadth_observation.py` | Upstream breadth history is recomputed with today's constituent membership; only the tip may be projected operationally. First durable private-store write owns availability clocks. | Historical recomputed breadth excluded from primary predictive test. Qualify actual first-seen snapshots or historical membership before a breadth increment. |
| `lib/dataos/price.py` | Yahoo `close` means total-return adjusted; `close_price` means split-adjusted structure basis. Adjustment vintage, session and venue are part of identity. | Use existing basis vocabulary. Do not compare adjusted levels with execution prints or use price-only returns as portfolio total returns. |
| `scripts/audit_prices.py` | Yahoo store is heterogeneous/close-only; stock and basket stores differ; some lack opens. The audit itself writes a quality artifact. | Read contracts, do not run a write-bearing collector/audit as a supposedly inert probe. |
| `engine/expectation_state.py` | Per-stock earnings/SUE/hold-thesis context, not macro consensus. | Exclude as a substitute for macro expectations despite its name. |
| `engine/policy_calendar.py` | Federal Register policy-catalyst context, not an FOMC schedule/expectations archive. | No name-based substitution. |
| `scripts/d2_rates_calendar_flows_phase0.py` | Existing Treasury auction, quarter-end rebalance and month-end extension research family with its own preregistration and trial ledger. | Preserve separate ownership; do not create new copies of those studies here. |

Important source blobs: event calendar `ef9ebd3c380da1d81411dd62fc4b2885b231fafe`; breadth observation `9f1abc95f87d0c7d8a390d5ac70217bc18329e70`; price vocabulary `be127fa853a6aafbf0bcb33b58783316ac972faa`.

### Measured local metadata, not a market backtest

An earlier successful, read-only PyArrow footer inspection on m2studio returned:

| Exact path under `/Users/chriswong/Documents/Cluade/macro-main` | Bytes | Rows | Date-statistics range | Columns relevant to eligibility |
|---|---:|---:|---|---|
| `data/yahoo/SPY.parquet` | 243873 | 8458 | 1993-01-29 to 2026-09-04 | close_price, close, volume, Date; no open/high/low |
| `data/breadth/breadth.parquet` | 434437 | 16229 | 1962-03-13 to 2026-09-04 | n_members, pct_above_50, pct_above_200, nh, nl, adv, dec, ad_line, Date |
| `data/breadth/constituents.parquet` | 12754 | 503 | No date column | name, sector, symbol |

`data/stocks/SPY.parquet` and `data/baskets/ohlcv/SPY.parquet` were absent in that checkout. These are local observations, not a claim that the live product/provider has no newer data or that no other store exists. Row count is not effective independent sample size or proof of complete history. Data values, original availability and adjustment vintages were not qualified. Native footer evidence has no per-file immutable hash in this tranche.

A follow-up attempt to hash the same files and inspect QQQ/IWM/RSP metadata was explicitly blocked before tool dispatch. It was not retried. Thus QQQ/IWM/RSP metadata and the price/breadth byte hashes remain UNKNOWN; the prior successful metadata is not upgraded to immutable-corpus proof.

## 3. Research update: information arrives in a sequence

**Alam, Learning About Fed Policy From Macro Announcements: A Tale of Two FOMC Days.** The author's accessible working-paper abstract reports that pre-FOMC returns differ when key macro releases immediately precede FOMC meetings. This motivates an event-sequence hypothesis, but the full method/replication was not verified. Do not adopt the abstract's category definitions or magnitudes as an implemented rule. Author source: https://www.zohairalam.com/ ; linked paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4065084 .

**Acosta, Ajello, Bauer, Loria and Miranda-Agrippino, Financial Market Effects of FOMC Communication, SF Fed WP 2025-30, official page revised August 27, 2026.** The official abstract emphasizes the importance of press conferences and recommends combined statement/conference surprises. The USMPD documentation, updated September 17, 2026, explicitly separates statement, conference, combined-event and minutes windows. These are distinct observations, not four independent votes on one event.

Sources: https://www.frbsf.org/research-and-insights/publications/working-papers/2025/12/financial-market-effects-of-fomc-communication-evidence-from-a-new-event-study-database/ and https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/ .

Only metadata/documentation were qualified; no USMPD dataset was acquired. Main data source is LSEG Tick History. Rights, exact vintage and integration with the incumbent event/research owner remain required before ingestion. Constructed monetary surprises use realized event-window changes: they cannot enter a pre-event predictor. Full-sample factor construction must not masquerade as a historically available live feature.

Version discrepancy: the browser's parsed PDF at the working-paper URL presented an August 2026 revision while screenshots displayed a December 2025 cover/version. This tranche relies on the dated official HTML abstract and database documentation for the limited conclusions above. No numerical table is attributed to the August revision from those mismatched screenshots; quantitative full-paper extraction remains unverified.

### Product consequence

Represent: (a) pre-event vulnerability; (b) statement released but conference unresolved; (c) combined event absorbed, next catalysts still pending. This is a proposed presentation of event evidence under existing owners, not a replacement market-state classifier or new runtime lifecycle. A rate decision's release alone must not automatically clear the event flag.

The original calendar's context-only authority stays intact. Its broad prose conclusion about unconditional pre-event de-risking is not accepted as a proof that every conditional warning is wrong. Conversely, a working-paper interaction is not permission to add a production exposure multiplier.

## 4. C1 frozen research benchmark — not yet data-admitted

**Question:** Does known near-term event timing improve prediction of five-session downside beyond simple price/volatility context, and does deterioration of an otherwise positive trend add incremental information?

This is a conditional predictive association, not causal identification of dealer flows or institutional advance knowledge. Calendar-only R0 remains separate and held; C1 is not an alternate acquisition or relabeled execution of that pilot.

### Information and output clocks

Decision origin is AFTER the completed session's needed inputs become available. Store decision_at, source_available_at, event_schedule_known_at, observation period, instrument/basis and source revision separately. Unknown availability is excluded from the primary cohort, not set to midnight or file-build time. A retrospectively reconstructed sensitivity cohort must remain separately labeled.

Closing indicators cannot authorize a fill at the same close that produced them. An assumed next-open trade cannot claim to avoid an overnight move or release gap already realized before that open. Price-only endpoint research and executable risk management therefore have separate gates. The inspected SPY close-only file cannot establish next-open execution, intraday stop fills or maximum intraday adverse excursion.

### Fixed candidate inputs and target

Requested research dates: January 2017 through August 2026, subject to actual eligibility. SPY is the primary instrument; QQQ and IWM are frozen transfer checks when their input quality is independently qualified. They are correlated markets, not independent replications.

Use existing price-basis owners. Define:

- `v20`: root mean square of the last 20 total-return log returns, including origin session.
- `trend63`: log ratio of the origin split-adjusted close to its close 63 sessions earlier.
- `momentum5`: analogous five-session split-adjusted log return.
- `deterioration`: 1 when trend63 > 0 and momentum5 < 0, otherwise 0. This is a research feature, not a new operational trend classifier.
- `E_CPI`, `E_NFP`, `E_FOMC`: schedule-known indicators for the corresponding event after decision_at and no later than the next cash-session close. FOMC is one combined meeting-day event; the statement and conference are not duplicated as independent daily observations. Missing schedule coverage is unknown, not no event.

Primary outcome is close-sampled five-session downside from origin, normalized by pre-origin volatility:

`Y5 = -min(0, min_{k=1..5} log(TR_close[t+k]/TR_close[t])) / (v20 * sqrt(5))`.

All five endpoints must exist and be mature; v20 must be finite and strictly positive. No forward filling or post-result floor tuning. This target is a normalized total-return close-path excursion, NOT an intraday drawdown or a trading loss. Total volatility and signed return remain separate secondary outputs. One-, three- and ten-session views are descriptive diagnostics, not extra confirmatory discoveries.

### Four locked comparators

- N: prior training-cohort median Y5, the no-feature baseline.
- P: log(v20), trend63, momentum5 and deterioration.
- PE: P plus the three event indicators.
- PEI: PE plus exactly two interactions: deterioration*(E_CPI + E_NFP), and deterioration*E_FOMC.

Including deterioration in P prevents the interaction model from receiving credit merely for adding an omitted nonlinear price feature. No GEX, current-membership historical breadth, realized surprise, full-sample percentile, additional oscillator or optimized OPEX window enters C1.

P/PE/PEI use the same fixed ridge benchmark: minimize mean squared error plus 0.01 times sum of squared non-intercept coefficients; standardize continuous inputs using training-only means/scales, leave indicators as 0/1, do not penalize the intercept, and clip negative predictions to zero. Constant continuous features become zero using training-only diagnostics. These are deliberately frozen benchmark choices, not claims of optimality. No coefficient, window, penalty or feature search after results under this C1 identity.

### Evaluation, precision and falsifiers

Require three full eligible training calendar years before the first test year. Refit monthly using only outcomes mature before the training cutoff; split on dates, never randomly. Five-session overlapping labels are purged across each train/test boundary. Missingness exclusions are identical across paired model comparisons and printed with reasons.

Primary evaluation cohort: held-out origins with at least one known CPI/NFP/FOMC event in the specified next-session window. Report full-sample and non-event results separately. Require at least 40 distinct CPI dates, 40 NFP dates and 30 FOMC dates in the out-of-sample event cohort; these are prespecified feasibility floors, not power guarantees. If source coverage cannot meet them, report insufficient evidence instead of relaxing them.

Primary score: mean absolute prediction error for Y5. Report N/P/PE/PEI, paired absolute and relative improvements, predicted-versus-observed risk strata, sample counts and excluded dates. The two confirmatory comparisons are PEI against P and PEI against PE. Use the same 63-session circular moving-block resamples of the chronological test panel, 10,000 draws, seed 20260924; retain event-date clusters and recompute event-cohort metrics inside each resample. Use 97.5% two-sided percentile intervals for each comparison (Bonferroni family coverage for the two comparisons is nominal 95%, subject to bootstrap assumptions). Blocks of 21 and 126 sessions are labeled sensitivity checks.

A candidate historical result earns further shadow research only if PEI reduces event-cohort MAE by at least 5% relative to P and both confirmatory paired-improvement intervals exclude zero in the favorable direction. The 5% hurdle is a declared programme choice, not a literature estimate or production threshold. Also report chronological eras, leave-one-year-out influence and cross-instrument transfer without pooling them into a larger independent n. Failure against PE means no demonstrated interaction synergy even if PE itself is useful. Failure/insufficient data stays visible; no automatic second attempt or threshold mining.

C1 never promotes a sizing rule. Warning thresholds, false-alarm burden, execution costs, cash carry, foregone rallies and re-entry delays belong to the later decision-value study, frozen before evaluating its outcomes. Historical success cannot replace prospective calibration/qualification.

## 5. First useful product slice and next execution

The first permitted product concept is a read-only composition of existing event records, observed price/trend context, qualified current breadth and options context with explicit evidence maturity. Useful questions: what remains unresolved; what changed after each event; does participation confirm price; which fact would invalidate the assessment? No synthetic confidence percentage or automatic safer-week label.

Market Memory already owns prospective forecast/outcome persistence. Its existing breadth adapter/private-store first-write semantics are the route for an eventual contemporaneous breadth cohort. Market Tide must not create a second calendar, snapshot store, state machine, forecast ledger or review/learning control plane.

Exact next unit: identify the incumbent historical schedule-occurrence/known-at source and the price adjustment/availability receipts needed to admit one C1 daily cohort. Obtain them as bounded read-only evidence from existing owners; do not acquire the previously refused R0 corpus or repeat the blocked hash/metadata action. Then implement the frozen benchmark using existing research/validation owners on the admitted supplied inputs. Where input gates remain absent, preserve a retrospective-only or forward-only disposition rather than lowering the gate. A post-event USMPD research extension and actual breadth increment remain separate, unstarted studies.

## 6. Effects, holds and continuation

No source, data, process, registry or runtime of MAS-260 was altered. No native source writer/worktree was acquired. No worker was dispatched. No watcher/autonomous wake is running. No new market-outcome analysis, source qualification pass, model fit or production/browser result is claimed.

Original R0 download/write denial remains TOOL_DEGRADED / EFFECT_NONE. The additional footer/hash follow-up this turn was also explicitly refused before dispatch, with no PID or result; it was not retried or moved elsewhere. Those exact actions remain held. Earlier successful reads and unrelated permitted GitHub research-record writes retain their own evidence state.

DO_NOT_REDO: original R0 preregistration; original mechanical illustration; #7925/#7929/branch; MAS-260 failed same-day/term/state recipes; its interval-adjustment failures; current calendar, price vocabulary, Market Memory and breadth projector. Do not equate a local file date with service-wide staleness, a receipt with independent replication, a footer with immutable data identity, or record acceptance with empirical success.

The cumulative Agent OS record and #7925 checkpoint are updated on this same carrier. Mission remains incomplete. End this tranche only after their exact source/readback is verified; source review/CI and eventual production proof remain separate gates.
