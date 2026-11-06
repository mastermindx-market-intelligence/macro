# Commission 15 — Validation protocol and contract examples

**Status: proposed research/implementation acceptance design, not a completed experiment.** This companion operationalizes sections E, F, H and L of the [complete report](COMMISSION_15_HARDENED_REPORT.md). No numerical setting below is a measured Mastermind result or a replacement for an existing owner gate. The accepting evaluation owner must freeze these settings or a reasoned alternative before any promotion outcome is inspected.

## 1. Separate the questions being tested

| Test family | Unit | Target | Principal error to avoid |
|---|---|---|---|
| Source semantics | Native record and correction chain | Exact units, identity, clock basis, conditions and scope | A schema-shaped row can still have the wrong meaning. |
| Deterministic measurement | Atomic input manifest → existing coalesced measurement | Same allowed inputs/config produce same output | A coalesced Flow ID is not an atomic print or package ID. |
| Quote-location concordance | Same trade/context universe | Agreement with a named qualified quote implementation | Neither implementation is a true aggressor oracle. |
| Participant/position effect | Source-labelled covered execution or participant record | Correct customer side/open-close/capacity within source coverage | Aggressor and customer are different targets; two sides are not two market trades. |
| Prediction | Incumbent candidate decision with fixed cutoff | Future observable outcome | Contemporaneous explanatory fit is not forward prediction. |
| Entry utility | Same candidate under baseline and frozen overlay | Paired policy outcome with fixed timing/cost/fallback | Midpoint markout is not actual fill or causal impact. |
| Mechanism attribution | Independently adjudicated labelled subset, if it exists | Nonexclusive mechanism evidence | Price reversal cannot create its own forced-selling ground truth. |

The options classification literature and opening-volume literature motivate separate measurement claims; they do not supply a universal promotion threshold. [O28] [O29] [O30] Cont–Kukanov–Stoikov motivates OFI as an explanatory feature, with a distinct future-outcome test. [E01]

## 2. Source-mode declaration

Every input partition and result carries exactly one declared mode, or a documented mixture that cannot be promoted beyond its weakest required component:

- **ACTUAL_AS_SEEN:** original available generations and collector/consumer receipts establish the exact historical Mastermind information set.
- **HISTORICAL_RECEIVABILITY:** original publication evidence plus a declared latency/entitlement model describes a hypothetical eligible observer, not actual Mastermind possession.
- **FINAL_VINTAGE:** today's archive is used for exploratory measurement. It does not claim original historical correction or receipt fidelity.

Unknown correction history cannot be cured by setting available_at equal to event_time. New append-only storage preserves future receipts; it cannot reconstruct lost old receipts.

The existing FS5 scientific availability log is not interchangeable with raw source-event diagnostics. Its byte-addressed source receipts must be read with the incumbent adapter; reserializing JSON changes raw bytes and cannot reproduce a prefix digest. Inline live telemetry and strict candidate receipt shapes must be validated through the appropriate owner adapter even when they display the same schema identifier. [M10] [M18] [M19]

## 3. Adversarial temporal and semantic fixtures

These are **test designs for the later owner**, not fabricated vendor observations.

| Fixture | Concrete setup | Expected result |
|---|---|---|
| Late context | Trade at 09:30:00.200; quote event at .190 arrives locally .210; earlier decision is .206 | The .206 as-seen decision cannot use that quote. A later reconstruction has a later available_at and cannot mutate .206. |
| Same-millisecond ambiguity | Several quotes and a trade share a millisecond without intra-millisecond order | Apply the frozen strict/inclusive/source-order rule; record ambiguity, never invent finer time. |
| Stream post-trade quote | A source emits pre-trade quote, trade, then quote updates; queued worker executes after all arrive | Association uses the captured permitted context, not the latest cache state. |
| Correction after cutoff | Original price/size known 10:00; correction available 10:02 | 10:01 replay uses original eligible generation; later correction produces a new generation and a separately labelled restatement. |
| Cancel ambiguity | Two identical prints share displayed fields; cancel lacks enough linkage | Preserve unresolved linkage or quarantine; do not choose an arbitrary original. |
| Sequence rollover/reset | Vendor sequence wraps or connection restarts; filtered stream skips values | Scoped native identity prevents collision. Gaps are interpreted by the actual source contract, not assumed global continuity. |
| Retroactive reference amendment | Deliverable valid at trade time v is amended with past effective date, assertion received after cutoff T | Event uses the assertion known at T. Final-restated view may use the amendment, without replacing the original. |
| Expired reference interval | Past trade v lies inside an old instrument interval, current decision T does not | Join valid time at v, not T; do not lose the old instrument merely because today's interval differs. |
| Prior-session OI | OI describes D but becomes usable on D+1 | Exclude from decisions on D; use actual availability on D+1. A missing zero-OI message remains unknown unless source semantics prove zero. |
| Projected synthetic clock | Latest wire timestamp derives from process time; native trade time absent | Reject as original market-event clock; preserve existing quote quality/diagnostic status. |
| Sparse BBO | Trade-attached quotes omit many intervening quote updates | At-trade statistics may pass; continuous OFI, duration, depletion and time weighting fail capability admission. |
| Unknown side | A large midpoint/ambiguous print | Include in gross volume and unknown fraction; signed quantity is not silently zero. |
| Adjusted contract | Cash/share deliverable differs from 100 common shares | Standard-contract formulas are withheld or use qualified actual economics. |
| Model change | Same quotes processed with different dividend, exercise or 0DTE convention | New derivation generation, not a market IV/Greek shock. |
| Future label | 30-minute midpoint response requested as input at the original trade | Withheld until horizon and input receipts mature. |
| Venue-selected labels | C1 T+1 participant records used to validate an intraday classifier | Allowed as later labels for the declared covered sample; not same-day inputs or all-OPRA truth. |
| Unavailable market | Halt/outage/closed session before horizon endpoint | Do not carry a stale quote into an executable fill; label censoring/missingness under the frozen rule. |
| Source-collision attempt | Second writer or archive chosen to replace an unresolved source generation | Fail admission; preserve incumbent effect/receipt identity. |

**Integrity gate:** zero known violations in the admitted claimed mode. A failing fixture invalidates the affected capability, not every independently valid field. Exact decimal arithmetic or numerical tolerance is declared per calculation; tolerances cannot conceal material sign, order, eligibility or generation changes.

## 4. Source qualification and coverage

The measurement cohort may contain SPY/QQQ plus 24 PIT-selected names across prior-known liquidity strata. The accepting owner freezes instrument IDs, admissible current/expired options, standard-deliverable eligibility, date/session rules and selection seed. These are feasibility choices, not statistical power claims.

Report four separate denominators:

1. **Capture coverage:** estimated/observed completeness of source events for the stated universe/session, with source-status evidence.
2. **Measurement coverage:** retained eligible prints/windows with all required fields.
3. **Classifiability:** the subset to which the selected side/quote rule applies.
4. **Consumer coverage:** incumbent decisions that received an admissible feature before their deadline.

The current measured block's NBBO-valid fraction is conditional on retained prints. It does not establish complete feed capture, acceptable quote age, positive executable size or coverage of all intended symbols. Current source-validity rules do not automatically contain a finite freshness cutoff. [M18]

All candidate decisions must be accounted for with an admissible feature, frozen fallback, or explicit failure. Proposed promotion default: **100% accounting** and **at least 95% usable-feature coverage** in the declared supported primary population, with the stress breakdown printed separately. A justified source-specific threshold can replace 95% only before outcome inspection. An R0 measurement report can complete with insufficient coverage; insufficient coverage does not earn downstream promotion.

Source health must separate a closed market from an outage, no trades from no feed, an empty source stub from an actual host store, and a fresh manifest from missing payload files. Report content-level existence/row checks in the existing owner, not just a successful request or latest file mtime.

## 5. Timeliness and source-latency contract

Keep market window close, scheduled source availability, actual local receipt, derivation completion and consumer deadline separate.

For the proposed five-minute consumer, a planning operational budget is **99% of feature receipts ready within 30 seconds after the declared upstream input-availability deadline**. This budget excludes no upstream delay from reporting: report total event/window-to-consumer age alongside it. A declared 15-minute delayed source is still 15-minute delayed; the rule does not move its decision back to the market window close.

Freeze budgets per source mode/session. A source requiring T+1 delivery cannot pass a same-day intraday input gate, even if its daily ingestion runs quickly. Vendor latency claims are not measurements of Mastermind's actual consumer path.

## 6. Primary consumer experiment

### 6.1 Estimand and same-candidate design

Use the incumbent Radar/entry candidate ID and its actual admissible decision cutoff T. Primary proposal: **entry timing conditional on the identical candidate list**, with a 30-trading-minute terminal horizon. Five-minute and session-end responses are diagnostics; one/three-session studies form a separate multiple-testing family.

Freeze baseline B and no more than two challenger policies. Fix candidate eligibility, direction supplied by the incumbent, maximum waiting window, outcome horizon, fallback, intended standardized research size, and costs. The new policy may use only the accepted feature families; it cannot create candidates or change exposure sizing.

For a transparent quote-based simulation, define:

~~~text
M0 = valid midpoint at actual decision cutoff T
H  = fixed T + 30 trading-minute endpoint
Pentry(policy) = qualified hypothetical entry price under frozen execution rule
Pexit(policy)  = qualified hypothetical exit price at H under the same rule
d = incumbent direction (+1 or -1), never generated by this experiment
Q0 = fixed admissible research quantity, identical for both policies
N0 = Q0 * M0
fees(policy) = explicit currency costs under the frozen simulation

U(policy), bps of initial standardized notional
  = 10000 * [d * Q0 * (Pexit - Pentry) - fees(policy)] / N0

if policy abstains through its deadline:
  U(policy) = 0

paired primary observation:
  delta_U = U(challenger) - U(baseline)
~~~

Define executable-side prices, displayed-size constraints, stale/crossed/auction exclusions and latency before observing outcomes. Spread cost already embedded in quote-crossing prices must not be charged again. A midpoint-only price-path variant is reported separately. For abstention, comparison with baseline automatically records missed gains and avoided losses; do not award a positive outcome merely for producing no trade.

Keep Q0 fixed across policies, including rounding conventions; do not silently switch to fixed dollars at each policy's entry price. Freeze partial-fill treatment and the corresponding fees. The permitted entry deadline, including assumed latency, must precede the terminal endpoint. The displayed formula assumes the full standardized quantity; any partial-fill extension must retain that same initial notional denominator and a preregistered unfilled-quantity rule.

A quote rule does not prove a fill. If sufficient quote/size/path evidence is absent, simulated execution utility is unobserved. Preserve the candidate in the accounting denominator, disclose censored outcomes and bounds, and refuse promotion when missing outcomes can determine the conclusion. Do not set source failure to a zero-P&L abstention.

Maximum adverse/favorable excursion, source-driven abstention, waiting time and event-specific concentration are secondary diagnostics. Reuse an accepted incumbent barrier/outcome label if it exists; do not define a latent mechanism from the same future price path being predicted.

### 6.2 Independent information and controls

Baseline controls include prior return/volatility/volume, existing spread, time-of-day, sector/market move, catalyst/earnings, liquidity stratum, options magnitude and expiry, and existing candidate state. Retain upstream dependencies so a second redistributor of OPRA does not count as independent evidence.

Test individual blocks and a tightly restricted combined challenger. Any extra model variants are recorded as additional trials in the existing owner record. Fit scaling, selection, missingness rules and calibration only on development data.

### 6.3 Chronological confirmation

Use chronological development, validation and untouched confirmation. Start a new prospective confirmation after the accepted freeze; existing September OA observations remain development/accepted evidence and are not relabelled untouched.

Purge labels whose outcome intervals overlap later validation/confirmation. Keep economic episodes, campaigns/packages and duplicate decisions intact. For uncertainty, resample complete date blocks containing the cross-section and examine issuer/event sensitivity. A later causal observation of the same issuer is not itself leakage; pretending every option leg is independent is.

Freeze the block/cluster estimator, confidence level, number of challengers and multiplicity method. Proposed default: 95% simultaneous confidence for the primary challengers using a preregistered adjustment. One-sided versus two-sided inference is selected at freeze, not after results. An inspected holdout is spent for selection; a redesign needs new evidence.

Freeze aggregation weights before confirmation: equal candidate, equal day or standardized notional weighting answer different questions. The primary estimate, variance model, minimum useful effect and power calculation must use the same weighted estimand. Report concentration and the other sensible weightings as declared sensitivities, without selecting the favorable one after observation.

### 6.4 Power and sample stopping

At least 60 complete sessions is a **proposed minimum observation window**, not sufficient power. Estimate paired daily/block outcome variance on development data and choose the required number of independent blocks before confirmation. As an arithmetic illustration, daily difference standard deviation 8 bp and minimum useful effect 2 bp imply approximately (2.8 × 8 / 2)^2 = 126 independent days for a simple two-sided 5%/80%-power approximation. Dependence/heavy tails can increase it.

The 126-day example assumes a daily/block estimand and a single unadjusted comparison. It is not a candidate-level sample-size result. Actual planning uses the frozen weighting, registered multiplicity adjustment and dependence model, with variance estimated for that exact estimator.

The owner freezes the achievable maximum sessions and cost cap. If the required sample exceeds those constraints, the disposition is INCONCLUSIVE/DEFER. Do not keep reading the same confidence interval until it passes unless an accepted sequential design with error control was preregistered.

## 7. Proposed decision thresholds and falsifiers

| Dimension | Proposed acceptance rule | Meaning of failure |
|---|---|---|
| Causal/semantic integrity | Zero known critical violations; correct grain, clocks, generations, units and condition eligibility | Capability not admitted; diagnostic R0 result can still complete |
| Reproducibility | Same allowed source bytes and definition reproduce accepted deterministic outputs within declared tolerance | Missing/ambiguous source evidence is a named blocked qualification, not permission for new capture |
| Consumer coverage | 100% candidate accounting; proposed ≥95% usable features in supported population, with explicit stress metrics | Restrict scope or deny promotion; never drop difficult decisions |
| Prediction, if a labelled probability task is separately chosen | Proposed ≥1% relative improvement in one proper loss, multiplicity-adjusted interval excludes no improvement | No predictive promotion; no Brier/log-loss claims for unlabelled mechanisms |
| Primary simulated entry utility | Paired mean improvement ≥2 bp and ≥10% of positive baseline measured friction/timing penalty, with adjusted interval above zero | No timing promotion; print absolute gain, tail harm and abstention cost |
| Robustness | Survives declared lag/age/spread/fee/missingness sensitivities; no material subgroup harm beyond a frozen tolerance | Restrict or reject; do not conceal contradictory strata |
| Expensive-source economics | Conservative benefit on realistically addressable workflow notional exceeds annualized incremental cost; proposed investment hurdle 2× cost | Defer direct depth or new recurring source |
| User/research utility | If no defensible execution-notional case exists, measure a separate analyst-time/error-reduction objective | Do not invent trading P&L to justify infrastructure |

The 10% friction comparison is applicable only when its positive baseline denominator is defined and measurable; otherwise use the frozen absolute effect and an explicitly stated economic objective. Neither marketwide turnover nor all company capital is “addressable notional” for this study.

Mechanism explanations should have discriminating falsifiers. If an alleged derivative-driven effect vanishes after price/volatility/expiry controls, or an accumulation claim depends on assuming every at-ask trade is customer opening demand, it fails that interpretation. The underlying observed volume or quote may remain valid.

## 8. R0 completion and honest blocked exits

R0 is accepted as **QUALIFIED_MEASUREMENT** when equivalent accepted proof or the necessary scoped replay supports the named measurement and required fixtures. Reuse an equivalent accepted result when inputs, definition, scope and receipt integrity are unchanged; execute only the precise delta for a new/unqualified claim or material invalidator.

R0 may instead complete as **QUALIFICATION_BLOCKED_WITH_EVIDENCE** when it documents the scoped absence of a required original byte sequence, receipt, correction generation, right or field, or an evidenced access/permission/verification barrier that prevents qualification through the authorized owner. Distinguish observed absence, denied access and unverified existence; an inaccessible store is not an empty store. The return identifies the exact dependency and owner, preserves historical accepted results, states which claims remain unsupported, and proposes one separately admitted remedy. It must not launch a replacement collector, vendor request, source hunt or trial to manufacture a passing packet. This completes input qualification while leaving measurement proof unproven for the affected claim.

These are local research-report dispositions, not new Executive lifecycle enums. Neither outcome activates a feature or changes a signing gate. The accepting principal chooses the next bounded commission. No condition in this protocol authorizes production data acquisition or trading.

## References

The external registry is in [SOURCE_REGISTER.md](SOURCE_REGISTER.md), and the internal census is in [CURRENT_STATE_AND_HARDENING_LOG.md](CURRENT_STATE_AND_HARDENING_LOG.md). Stable links used here follow.

[O28]: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0
[O29]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4098475
[O30]: https://www.mit.edu/~junpan/volume.pdf
[E01]: https://arxiv.org/abs/1011.6402
[M10]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/lib/live_flow_event_stage.py
[M18]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/engine/live_flow.py
[M19]: https://github.com/mastermindx-market-intelligence/macro/blob/59a0789c0e5ffcce15e682b6f3880f3eacc6f6fc/contracts/options/options.trade_nbbo_microstructure.v1.schema.json
