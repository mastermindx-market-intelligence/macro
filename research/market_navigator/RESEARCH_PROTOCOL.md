# Market Navigator research protocol

Version 1.0, 22 October 2026. This is a study-design artifact and source-feasibility
record, not a new trial registry or approval to revive a killed construction.
The existing research owners retain registration, trial accounting and promotion.
No market-return outcome was inspected by the two initial audits below.

## A. Completed research initiation

### A1. Local derivative versus finite repricing

Reproduce:

```
PYTHONPATH=. python scripts/research/market_navigator_model_audit.py \
  --output research/market_navigator/MODEL_AUDIT.json
```

The incumbent `engine.greeks.bs_greeks` supplies all delta/charm mathematics. A fixed
European Black-Scholes grid uses spot 775, IV 0.20, zero rates/dividend, 7 strikes,
4 remaining lifetimes, calls and puts, and 4 fractions of remaining time. None is
an observed option, known dealer position or market forecast.

Results: 224 valid pre-expiry finite comparisons. The largest local-linear versus
finite delta-change discrepancy is 0.17513925, equivalent to 17.513925 underlying
units for the deliberately hypothetical one long 100-unit contract. The worst grid
case has 390 minutes remaining and rolls 90% of that lifetime. This is not a claim
that every tiny time step has a large error.

Separately, 20 of 56 deliberately inadmissible one-calendar-day extrapolations cross
expiry and exceed the unit bound on a single option's delta change. The audit is not
a replacement settlement model. Its analytical charm matches a centered numerical
derivative to maximum relative error 6.39e-8 on this grid. Thus the problem exposed
is not a broken local derivative: it is using that derivative outside a suitable
finite neighborhood or across fixing.

Consequence: integrate the existing finite scenario owner with its full-book and
fixing checks; never multiply an enormous near-expiry charm by an arbitrary full day
and label the result an imminent stock order. Check surface assumptions and inventory
uncertainty separately. Finite repricing is still conditional, not observed flow.

### A2. Official daily volatility-data feasibility

Explicit, bounded foreground acquisition using the existing Cboe daily URL family:

```
PYTHONPATH=. python scripts/research/market_navigator_daily_audit.py \
  --cutoff 2026-10-21 --output research/market_navigator/DAILY_DATA_AUDIT.json \
  --fetch-public-daily
```

The retained report records endpoint, SHA-256, bytes, columns, date bounds, malformed
and duplicate counts. Raw data and credentials are not committed. No scheduler,
production writer or paid acquisition was created.

| Series | Rows through cutoff | First observation | Last observation |
|---|---:|---|---|
| VIX1D | 1,114 | 2022-05-13 | 2026-10-21 |
| VIX | 9,299 | 1990-01-02 | 2026-10-21 |
| VIX3M | 4,299 | 2009-09-18 | 2026-10-21 |

In the acquired VIX1D file, 78 daily lows are at or below 6.88; no daily closes are.
This is measurement coverage, not predictive success. A low does not disclose first
touch time, the contemporaneous SPY level, available option quotes, order fills or
whether the other required conditions held. It cannot validate Michael's intraday
conditional put entry. Values before the published index launch need to be separated
from live disseminated history in any later research. Original availability timestamps
are absent throughout these current-download files, so evidence class is public
reconstruction, not operational point-in-time.

Consequence: daily data can support a descriptive volatility overview; the exact
intraday hypothesis requires joint timestamped observations and its own rights and
registration. A close-only backtest is not a valid proxy for that hypothesis.

## B. Existing negative evidence that must survive

Read these at the source baseline before any study admission:

- `DNR:KILL-ABSOLUTE-VIX-THRESHOLDS`: prior absolute VIX spike/fade construction failed
  statistical support. A VIX1D rule is not automatically the same construction, but
  neither a changed index name nor an attractive threshold is a revival permission.
- `DNR:KILL-CHARM-NARRATIVES`: signed-charm/intensity narratives were killed for
  volatility/size confounding. Only the exact existing Options historical research
  exception supplies a route to renewed positioning research. The model audit above
  is a numerical applicability test, not revival of a directional charm strategy.
- `DNR:KILL-PER-SIGNAL-FAMILY-RELIABILITY`: the prior family x regime reliability grid
  is killed. Do not rebuild a differently named table of momentum/breakout win rates.
  Re-entry needs the incumbent coverage assessment to be estimable and a fresh
  interaction-primary registration. General outcome inspection is not that revival.
- `DNR:KILL-PSS-SR3-PARTICIPATION` and other exact PSS constructions remain closed.
  A breadth descriptive view does not authorize rerunning the failed peer-participation
  entry design. Preserve the exact negative result and its defined population.
- Composite-regime, LLM-originated signal, positioning-fusion and off-horizon verdict
  restrictions remain unchanged. No UI polish, source citation or current assignment
  silently changes those authorities.

The original 32 candidate heuristics are hypotheses, not 32 approved experiments or
features. Map each to existing constructions, controls and rights before allocating
trials. New admissions belong to the existing Research Factory/Options arena.

## C. Research questions in priority order

| Question | Main alternative / falsifier | Minimum usable evidence | Primary output |
|---|---|---|---|
| Are the clocks, units and model assumptions correct? | Apparent signal is stale/misscaled/revised | Source-qualified inputs and mathematical tests | Measurement acceptance or precise rejection |
| Is the analyst's rule reproducible? | Prose allows hindsight or missing triggers | Timestamped original claims + complete follow-ups | Extractable/ambiguous/unscoreable coverage |
| Does volatility normalization improve description? | Raw level mostly reflects time weighting | Same-clock intraday VIX1D plus underlying/options | Measurement decomposition, not automatic directional edge |
| Does exact 6.88 add information? | Same-clock low-vol baseline performs as well | Admitted rule + frozen joint intraday sample | Conditional forecast comparison, after scope review |
| Does the 1.12 curve boundary add value? | Numerator/denominator changes explain it | Aligned VIX/VIX3M and horizon-specific labels | Increment beyond continuous components |
| Does breadth speed add information? | Simple price recovery explains the pattern | Point-in-time constituents and denominator | Increment over price-only recovery, not killed peer-entry revival |
| Are historical transaction zones special? | Round numbers/price pivots explain reactions | Qualified print-level history with corrections | Out-of-sample reaction comparison |
| Do Greek interactions add information? | Same book, volatility and size create apparent confluence | Existing Options research exception + qualified snapshots | Existing arena result with no new production authority |
| Do under-implied earnings moves reverse? | News surprise/guidance/initial gap explain response | Frozen earnings expectations, quotes and event clocks | Stock and executable-option outcomes separately |
| Does waiting improve a defined decision? | Later confirmation sacrifices more than it protects | Exact timing rule, costs and missed opportunities | Utility versus always-enter/never-enter baselines |
| Does the interface improve decisions? | Users misread conditional context as advice | Representative user task study | Comprehension and error rates, not engagement alone |

## D. Corpus acquisition and extraction

The objective is a complete-enough method record, not an imitation model. Resolve the
exact account and time window through the existing provider. Log requested window,
observed oldest/newest post, pages, gaps, edits/deletions and covered post types. A
3,200-post timeline cap or truncated third-party result is not "all posts". Provider
access and licensed use are separately checked. No raw key in chat or public source.

The public X agreement forbids foundation/frontier model training or fine-tuning on
X API/content. Do not fine-tune such a model for this project. Any structured analysis,
retention or retrieval must use actual applicable rights and not imply endorsement.

Extraction fields, with every inference visibly distinguished:

```
source_id, author_id, published_at, captured_at, revision_id, source_span
instrument_ref, evidence_kind, observation_time, decision_time
horizon, original_target, trigger, invalidation, deadline
stated_action_or_hypothetical, stated_uncertainty, followup_refs
extraction_version, annotator_status, ambiguity_reasons, permitted_use
```

Separate independent claims in one post. Preserve comparisons, negations, conditional
scope and every numerical unit. Never invent a stop, target or actual fill. Build a
stratified manually reviewed extraction set across periods, bullish/bearish/neutral
views, successes/failures and long/short posts. Measure exact numeric fidelity, temporal
assignment, condition extraction and unsupported inference, not only text similarity.
A claim that cannot be scored is retained as unscoreable, not silently removed.

## E. Frozen prediction rulers

For each admitted trial the owner record must fix:
- Construction identity and mapping to previous accepted/rejected work.
- Decision information set and exact knowledge cutoff.
- Population/membership, source coverage and source-rights class.
- Trigger, confirmation, invalidation, deadline and evidence prerequisites.
- Prediction target, horizon, baseline, feature groups and ablation plan.
- Permitted parameter alternatives and total trial accounting.
- Training/validation/untouched-test boundaries, purge/embargo and dependence unit.
- Missing/corrected data policy, realistic execution and cost assumptions.
- Primary statistic, uncertainty, practical-value requirement and decision owner.

Targets remain separate: touch, close, path ordering, adverse excursion, realized
volatility, stock return, option P&L and portfolio utility. Missing joint intraday
quotes cannot become a zero-cost option backtest. Close-to-close return is not a
substitute for a stop/target path whose ordering is unknown.

The primary test for incremental information compares the proposed feature to a
reasonable baseline with the same information set, coverage and forecast horizon.
Inspect stability and negative results. A subgroup discovered after seeing the data
is another trial, not an explanation exempt from trial accounting.

No default 50/50 probabilities. Calibration uses separate held-out predictions and
labels; report coverage, sample sizes, uncertainty and base rates. Brier/log loss or
reliability diagrams are useful only for the exact probabilistic target. A probability
of a drawdown is not confidence in the data, nor permission for a trade.

## F. Prospective evaluation and product experiments

Use existing capture and outcome owners, not a new market diary service. Preserve the
first published prediction, its exact inputs and later revisions. Non-triggered
scenarios have their own outcome category. Natural horizon maturity is real; it cannot
be accelerated with hindsight data relabeled as forward evidence.

Measure missed opportunities and abstention alongside false actions. Distinguish:
forecast discrimination; probability calibration; after-cost trade utility; portfolio
risk; user comprehension; and operational freshness. No single metric substitutes for
all six. No user behavior study or tracking instrumentation is launched by this document.

## G. Research stop and promotion logic

Stop a construction for invalid measurements, insufficient temporal coverage,
non-identifiable outcome, failed prior falsifier or scope/rights denial. Repair source
contracts before fitting models. A failed data supplier blocks that input lane only.
An absence of evidence is not a negative result; label it untestable with current data.

A positive retrospective result is a candidate for existing prospective evaluation,
not an automatic release. Promotion follows the incumbent decision owner, with actual
source rights, horizon fit, realistic costs, held-out evidence and production proof.
Never change a failed threshold, horizon or population without recording a new trial.

## References

Source definitions and exact URLs are in MASTERPLAN.md [S1-S6]. The two executed
reports carry actual input/kernel hashes and deterministic reproduction commands.
Public data audit endpoints use the same family documented in
`collectors/cboe_indices.py`; no raw source corpus is published here.
