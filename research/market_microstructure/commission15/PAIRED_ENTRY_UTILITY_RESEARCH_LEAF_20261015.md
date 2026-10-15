# C15 same-candidate paired entry utility — source-free research kernel

**Scope:** Existing [Commission 15 validation protocol](VALIDATION_PROTOCOL.md) §6.1 under [Massive TP/R0 program #7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367). This is a **pure deterministic research leaf**, not a new source, TrialLedger, auth/tenant service, execution simulator owner, product route or trading signal.

**Status:** BUILT_NOT_PROVEN. No real Massive/SIP T/Q capture, actual candidate consumer receipts, freeze, reference/correction vintages, executable fill or prospective 30-trading-minute experiment has been supplied. All checked observations below are *synthetic*. The tool **never** claims production, source authentication, true fills, predictor skill, entry permission, ranking, alert, sizing or portfolio effects. Existing R0 30s/2m/5m forward labels remain separate.

## Why and when this kernel is useful

Commission 15 compares **the same incumbent Radar/entry candidate** with a frozen baseline B and a frozen challenger; the challenger must not invent new candidates, directions or sizing. A 30-trading-minute outcome cannot be part of the original decision. The source owner must provide original candidate and quote receipts, and the evaluation owner must freeze source/admission, costs, policy, denominator, market-calendar, missingness, testing budget and statistical design **before** examining outcome data. Do not treat `source_mode="ACTUAL_AS_SEEN"` supplied in a dictionary as evidence of genuine custody.

The pure entry point is:

```python
engine.market_microstructure.paired_entry_utility.evaluate_same_candidate(
    candidate=..., baseline=..., challenger=...,
    evaluation_cutoff_ns=..., source_watermark_ns=...,
    watermark_received_ns=..., market_health=...,
    market_health_receipt_sha256=...,
)
```

The strict input dictionaries require one `candidate_id`, ticker/session, supplied evidence mode, frozen original decision/deadline, exact 30-minute **same-session** nominal endpoint, externally supplied calendar receipt, frozen reference `Q0` as research shares (not trade sizing), and `M0` sourced from one independently supplied original **NBBO bid/ask quote** with its own original event-time/available-time/receipt, valid spread and positive size. The research denominator is **recomputed from that bid/ask midpoint and checked for exact equality** to supplied `initial_midpoint_usd`; it cannot be picked independently to amplify a result. This is only an internal contradiction check, *not* independent source authentication. The candidate source and the anchor quote must have been available strictly before decision; their receipt references and max quote-age ≤5s are carried explicitly. The reference `lib.nyse_calendar.is_session` checks the nominal full-session calendar, not early closes or special live halts: `calendar_qualified_by_this_function=false` **always**. The owner must independently prove the exact 30 trading-minute clock, unscheduled halts and early-close model. This v0 intentionally refuses cross-session windows instead of silently inventing overnight continuity.

Both policies must use the **same candidate ID** and freeze **strictly before** the original decision (same-nanosecond ties without native sequencing abstain). The challenger requires an independently supplied consumer receipt and first-available clock **strictly before** that decision; a missing or late overlay becomes **UNOBSERVABLE** rather than a retroactive success. Both hypothetical entry and exit use **strictly prior**, age-limited, crossable NBBO, source-received **strictly before** the relevant entry/horizon instant, and enough displayed top-of-book size for the same frozen `Q0`. A quote whose native event occurred before H but whose local receipt arrived after H **cannot** be simulated as executable at H; it remains UNOBSERVABLE even if a later matured response label might use it as descriptive research. **Both full-fill policies must refer to the identical terminal quote generation** (same source receipt, timestamp, bid/ask and displayed size); giving each policy a different favorable exit snapshot at the same fixed H is a consistency refusal. The kernel chooses **ASK-to-enter/BID-to-exit for longs**, **BID-to-enter/ASK-to-exit for shorts**. It never accepts caller-picked favorable entry/exit prices. These are at best *quote-side research prices*, not broker/exchange fills, impact estimates or guaranteed best execution.

Explicit `fees_usd` are positive/nonnegative fixed decimal **currency costs** only, excluding the spread already paid by quote crossing. Fractions preserve exact arithmetic for both policies:

```text
N0 = Q0 × M0  (frozen for both policies)
U(policy) = 10,000 × [ d × Q0 × (Pexit − Pentry) − fees_usd ] / N0
delta_U = U(challenger) − U(baseline)
```

All three outcomes include exact rational numerator/denominator plus 12-decimal display-only bps; rounding is **not** evidence of zero. A deliberate frozen no-entry decision with a receipt available before deadline and completed evaluation horizon is assigned zero utility; missing quotes/source, stale best quotes, insufficient size, market halt/unknown health, immature source watermark or a feature received too late never become zero returns. Their results have typed `NOT_MATURE`, `CENSORED` or `UNOBSERVABLE` with **null** paired numbers. Signed fractional outcomes are possible, with no automatic sign authority.

The additional `supplied_input_first_knowable_ns` is a lower bound derived from the supplied source watermark and exit/abstention receipts, **not** an actual Terminal or end-user receipt. It is always accompanied by `supplied_input_first_knowable_not_consumer_receipt=true`.

The result always declares `source_authenticated=false`, `calendar_qualified_by_this_function=false`, `actual_consumer_delivery_proven=false`, `simulated_execution_not_fill=true`, `prospective_promotion=false`, `predictive_rank_trading_alert_authority=false` and `forward_outcome_available_to_original_decision=false`. It writes no data or TrialLedger. Use the incumbent `engine.trial_ledger.TrialLedger` externally for actual preregistered challenger counts; nothing here mints a trial, validation result or registry.

## Discriminating local synthetic verification

Run from the isolated Macro workspace:

```sh
PYTHONPATH=. python3 -m pytest -q tests/test_c15_paired_entry_utility.py
python3 -m py_compile engine/market_microstructure/paired_entry_utility.py
```

Fixtures exercise known positive and negative same-candidate paired utilities, exact source-side cross prices, an independent **original midpoint quote denominator** with strictly prior native receipt and exact midpoint conservation, an identical **terminal quote vintage across both policies**, and exclusion of post-horizon quote receipts from simulated H fills. They retain full quantity/size, explicit currency fees, genuine abstain vs source-missing zero, future/late source clocks, immature receipt and market-health censoring, original challenger availability **strictly before** decision, wrong ticker/session, NYSE weekend/nominal-hours refusal, quote-age/stale/locked/same-nanosecond rejection, spread-cross and size constraints, huge/small fixed-point inputs, and **exact nonzero values whose 12-decimal display rounds to zero**.

These deterministic tests are not a market sample, a power calculation, retrospective fitted edge, untouched confirmation, evidence of actual T/Q coverage, or a source-/execution-licensed market trial. The separate upstream TP1/TP-B/TP2 PR test suites remain blocked by the original protected CI enrollment refusal; this bounded research addition cannot amend or bypass that refusal.

## Next actual empirical admission

The source and entitlement owner must provide lawfully licensed singleton TP1 RTH T/Q, original verified available-at and watermark receipts, versioned condition/correction/split/calendar rules, and an independently authorized private consumer path. The incumbent decision/entry owner must provide **frozen, complete original candidate IDs** and baseline/challenger plan and consumer receipts (including failed/missing episodes), quote availability and provenance. The accepted study owner must preregister outcomes, policies, fees, minimum effect, repeated-testing budget, chronological splits, block uncertainty, partial-fill handling (currently **not supported**), and controls *before* viewing forward labels.

Only after those existing gates clear may the owner run the prospective paired 30-trading-minute study against real registered candidate/consumer evidence, with full candidate accounting, missed wins, censored paths and cost sensitivity. A positive synthetic fixture or source-mode label cannot promote a signal or live order.
