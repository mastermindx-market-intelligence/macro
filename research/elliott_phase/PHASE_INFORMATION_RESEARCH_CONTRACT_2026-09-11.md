# Elliott phase: information content, measurement compatibility, and a bounded research contract

**Date:** 2026-09-11 UTC  
**Status:** Historical source-review packet; its continuation-first experiment and next-action language are SUPERSEDED / NOT ADMITTED. No market-outcome test, signal authority, production integration, or portfolio action.
**Canonical source pins:** Skillpack `Mastermind@068dcc1533776672844b36ffcde30fad68a4317f`; implementation/research `macro@4b1f8fddcc4eb6f36133fca4d42018678b74d30b`.

> **TOI absorption ruling (2026-09-13):** this file is retained as historical
> provenance for the source investigation. It is not the current experiment
> contract and does not define a standalone Elliott program. The durable source
> finding and sole current anticipation proposal are respectively:
> `research/technical_opportunity/elliott_phase/ELLIOTT_SOURCE_COMPATIBILITY_FINDING_2026-09-11.md`
> and
> `research/technical_opportunity/elliott_phase/ELLIOTT_E0_ADMISSION_PROPOSAL_2026-09-11.md`.
> TOI W1/W2-0 and existing Trial/Evaluation owners retain every admission gate.

## 1. The useful hypothesis is sequence information, not a magic number

The remaining question is whether a causally available interpretation of how an advance developed helps predict its next transition beyond ordinary price context. It is not whether an analyst can draw five labels after a reversal, whether a chosen retracement happens to be near price, or whether an LLM can recognize a chart illustration.

A synthetic pair isolates the distinction. A moves through 100, 110, 104, 124, 119, 129. B moves through 100, 120, 115, 125, 119, 129. Their signed leg-change multisets, initial/final prices, final leg, range, total absolute leg movement, and sum of squared leg changes are identical. Yet A's fourth endpoint is above its first endpoint; B's fourth endpoint overlaps its first-wave territory. A passes that necessary standard-impulse constraint and B fails it.

This is NOT a complete wave validator, and the paths do not have identical moving averages, full histories, or all volatility measurements. The result demonstrates that order can contain information discarded by particular summaries. It does not show that this order predicts market returns. It also does not establish that B is unclassifiable under all other Elliott constructions.

If G is deterministically calculated from the entire price history X, then G cannot supply new information beyond that entire X. It can nevertheless be a useful representation for a limited forecasting model: compression and a disciplined inductive bias may make relevant relationships easier to estimate. That is a representation advantage, not an independent source of confirmation. The empirical comparison must reflect this distinction.

## 2. A wave endpoint is not always the largest price extreme

The primary Elliott sources distinguish pattern completion from simple high/low detection. A truncated fifth can end short of the third wave's extreme, and requires its own subdivisions to support the interpretation [E1]. A triangle completes at the end of its E section; its largest intervening excursion need not be at that endpoint [E2]. These are definitions within the method, not evidence that the resulting forecast is profitable.

This changes both price rulers and time rulers. Calling the largest high 'the fifth-wave end' or the lowest intervening price 'the fourth-wave end' can measure the wrong structural interval. An untyped list of extrema is therefore not a complete Elliott interpretation.

Neely's channeling prescription has additional method-specific constraints. His requirement concerning wave three and the final 2–4 line is explicitly not an orthodox Elliott rule [E3]. His relative-time confirmation rule must not silently be evaluated with endpoints from a different convention [E4]. No source in this research establishes that the GDX author uses Neely's specific method.

A prospective representation needs to distinguish at least the observed price extreme, proposed structural endpoint, basis for the proposal, supporting subdivisions, time the evidence became available, and time the interpretation was announced. These are semantic requirements on existing source/event references—not a proposal for another market-event database.

## 3. Existing owner reused: actual source was audited, not a replacement swing engine

`engine/cycle_ontology.py` already supplies a causal reversal detector, `detect_turns`, and a versioned turn-epoch concept [I1]. Its existing phase wheel is based on standardized position and multi-timeframe momentum, not Elliott's ordinal wave position. Reusing the word 'phase' must not merge these different concepts.

The exact source at the pinned commit was fetched on the authorized Mac. Its 68,960 bytes matched Git blob `9e726868f6c218a84cd50a9f976c77c3a347ac6c`. An isolated excerpt of only `TurnParams`, `_yf`, and `detect_turns` was prepared in the conversation sandbox. Each function/class AST matched a SHA-256 fingerprint computed independently on the fetched source. The production module, its imports, writers, and model runners were not executed. This is a historical source fixture, not a competing implementation.

Nineteen characterization tests and examples passed in the accompanying conversation research archive. Some tests deliberately assert an incompatibility; passing the test does not qualify the code for intraday use. The compact repository probe `source_contract_probe.py` reproduces the central source-contract findings without importing the production module. The archived result `source_contract_probe_results_2026-09-11.json` records explicit excerpt mode: its three function/class ASTs match the source, while `input_matches_full_blob` is correctly false for an excerpt. The full source blob was separately checked on the authorized Mac.

| Observed behavior | Synthetic evidence | Research consequence |
|---|---|---|
| Completed turn geometry remains stable when more valid bars are appended | All tested completed rows across growing prefixes remained in the full-prefix result | A causal foundation already exists; do not rebuild it |
| Month/kind identity is coarse | 29 confirmed alternating daily turns produced two distinct `turn_id` values | An ID-keyed consumer could merge different turns; finer-scale reuse needs owner-approved identity semantics |
| Date serialization discards intraday time | Different five-minute observations shared date-only pivot and confirmation fields | Those fields alone cannot support a four-hour deadline or cross-market event alignment |
| Provisional rows carry `confirmed_at` | The open running extreme has a last-observed date in that field | Consumers must test `provisional`; presence of the field is not confirmation |
| Initialization requires 30 nonmissing bars | No output at 29 bars; first output at 30 contains earlier threshold dates | Actual availability must include initialization/first publication, not only the retro-recorded threshold date |
| Missing rows are dropped | A three-calendar-day interval can become one valid-observation lag | Trading-time, observed-bar time, and calendar time must remain distinct |
| Frequency and basis are declarations | Changing `freq` changed parameter identity but did not resample; changing basis did not adjust values | Caller must supply the declared cadence and price basis |
| Input sorting is a caller precondition | Reversed timestamps were processed in supplied order | Validate input contracts before importing the output into point-in-time research |

The collision is not a finding of data loss in a production consumer. Dense oscillations were deliberately synthetic. The time-resolution findings do not imply the current broader-cycle product is broken. They establish that direct fine-scale reuse is not yet justified.

The source comment mentions a collision suffix, but the inspected function does not add one. Any correction belongs to the existing owner. No source patch, ID migration, threshold change, or new event store was applied.

## 4. OHLC itself can leave the sequence unidentified

An open/high/low/close record of 100/110/90/105 is compatible with both 100→110→90→105 and 100→90→110→105. Under the same 14% reversal rule after identical warmup, the first path yields confirmed peak-then-trough geometry; the second yields a confirmed trough and an open high. The bar's four values alone do not determine the order.

This is an information limit, not a parser implementation bug. For a method that needs intrabar order, the choices are to use properly timestamped finer data, adopt an explicitly coarser close-only estimand, or retain the ambiguous interpretations. One cannot reconstruct a unique order merely by knowing the bar's closing price.

The same principle applies to retrospective outcome grading. When both target and invalidation are touched within one unresolved bar, favorable ordering must not be assumed. Such a case must remain unresolved or contribute an explicitly bounded score under all admissible orderings.

## 5. Scale is an input to the method, not a free discovery dial

On a synthetic advance with modest pullbacks, the same existing function produced six confirmed turns at a 3% setting and only one at 14%. This was a definition diagnostic, not a parameter search on market outcomes. No conclusion about the correct GDX threshold follows.

Directional-change research gives a useful null benchmark: under its Brownian scaling model, event counts vary approximately with volatility squared and inversely with the squared reversal scale [E5]. Therefore, changing scale can create more apparent 'waves' without revealing a new economic cycle. The cited paper also reports a qualification in its empirical currency comparison; its formulas should not be treated as universal GDX laws.

The study must declare how it chooses scale before outcomes. It must not optimize a separate wave threshold for each ticker using that ticker's own successful forecasts. The existing turn epoch owns changes of basis, parameters and detector identity [I1]. This contract creates no substitute identity plane.

## 6. Existing house evidence changes the comparison

The Entry Stack Expansion masterplan previously skipped generic Fibonacci/Elliott and candlestick additions on subjectivity/collinearity grounds [I2]. That is a program-scoped triage decision, not a statistical refutation of every possible sequence hypothesis. It still prevents pretending this is an untouched idea or importing a generic filter without a clearly different construction.

Previous passes recovered the F4/SR repair failures and the protected RH1/CR1/CD1/AF1 prospective charters. Their constraints remain. A new label cannot revive a killed threshold combination, read protected interim outcomes, or appropriate Top Anatomy's reserved cohort or different horizon. The current inquiry neither reopens nor grades those studies.

There is also relevant positive/negative differentiation in the existing Anticipation Phase-0 report [I3]. That report records useful forward-drawdown relationships for some legs on its declared ruler, while its short- and medium-direction tables show approximately no improvement over their own base-rate forecasts. The medium base up-rate is 0.606, so 'no incremental skill' is not literally a 50/50 market. These are existing report claims, not a newly replicated result or a current production qualification.

This is why the wave question must be separated into anticipatory risk, post-confirmation continuation and entry decision value. Success at one does not establish success at the others.

## 7. Superseded proposal history — not current admission law

The continuation-first material below is preserved to show the design history. It is
not an alternate live proposal and cannot be selected after outcomes. The sole current
E0 proposal is anticipation-first at the canonical TOI path named above.

### 7.1 Two forecast origins, never mixed

**Primary proposed question — continuation:** At an actually observable loss-of-pace or reversal event after an advance, does the previously available wave interpretation improve the distribution of subsequent movement beyond a model that sees the same event and ordinary price context?

**Separate later question — anticipation:** Before the reversal is observable, does a provisional late-advance interpretation improve the forecast? This would have its own candidate population, identity, trial budget and admission. It cannot inherit a positive continuation result.

Neither question asks a hindsight labeler whether the later chart 'was really wave C'.

### 7.2 Proposed outcome and horizon

For the continuation question, propose one 20-exchange-session horizon and a three-category first-passage outcome from a common post-publication reference price: downside boundary first, upside boundary first, or neither. A concrete proposed ruler is ±2 times an ATR(20) known by issue time, with the ATR method, basis, corporate-action handling and session calendar bound to the existing owner. The ratio is an outcome ruler, not an order or recommended stop.

Twenty sessions and two ATR units are design choices offered for review, not optimal values established by evidence. No grid of alternate horizons or thresholds may be searched and substituted after results. The registered owner may change the proposal before outcomes, then freeze it once. If that ruler is infeasible or conflicts with a governing contract, the study remains unadmitted rather than improvising another one.

The reference price must be the first eligible observed bar open strictly after actual publication, using an execution-calendar rule agreed before outcomes. All model inputs and the ATR are frozen before that open. This avoids crediting the completed signal bar's close as an available entry after an analysis delay. The proposed horizon ends at the close of the twentieth regular exchange session counting the reference session as session one; intraday candidate cadence, reference-bar width and extended-session handling require explicit owner acceptance. Report issue-to-reference latency rather than silently moving the start backward. No part of the already-observed reversal counts as a subsequent success. Results are measured after the true issue time. Same-bar double touches retain order ambiguity. Halt, delisting, missing observations, provider corrections, and right censoring receive explicit existing-owner handling; unresolved data is not converted into 'neither'.

### 7.3 Same observations and equal treatment of unavailable structure

The baseline and challenger must forecast the same eligible origins and use the same available source vintage. If wave interpretation is unavailable, the challenger falls back to the baseline; the case remains in the main comparison. Report the increment separately on the identifiable subset, but never compare that subset with a broader and harder baseline population.

No candidate is removed because its projected fifth wave extended, its correction became complex, or its alternate count later won. Sequence uncertainty and forecast uncertainty are different: a count can be uncertain while several counts support the same next event.

### 7.4 Comparator ladder

1. Baseline ordinary context: admitted trend, volatility, drawdown, time since observed reversal, and the event's own reverse magnitude/speed/line distance. No new composite authority is created.
2. Same baseline plus a small frozen set of ordered-structure features: overlap, segmentation/degree status and available corrective-form evidence. These must not be misnamed a complete Elliott count when only skeleton constraints are available.
3. Full declared structural interpretation only when supporting subdivisions and parent information are available at the origin. Unavailable fields remain unavailable.
4. Fibonacci features tested separately after a distinct admission; do not pool their contribution into a successful sequence result.

A price-history model with a comparable training budget is an important robustness comparator. If a grammar representation wins only against an artificially weak summary, the claim is narrowed to that comparison—not independent intelligence absent from prices.

### 7.5 Scoring, uncertainty and promotion

Use paired proper probability scores on the common origins: a prespecified multiclass Brier score as the primary comparison, log score as a separately declared diagnostic, with calibration and coverage shown. Proper scoring evaluates probability statements rather than rewarding confidence or a favorable threshold alone [E6].

Estimate uncertainty with the existing time/episode-aware evaluation owner. Do not count multiple charts, variants, intraday updates or highly correlated constituent stocks as independent episodes. Probability recalibration is fitted on prior calibration data only, not the final evaluation outcomes. Development, tuning, and final evaluation stay chronologically separated; overlap and method-selection multiplicity remain in the recorded trial budget [I4, E7].

A nominally positive average is not a trading promotion. The admission must state a minimum worthwhile effect, robustness requirements, power/precision target and an untouched/prospective evaluation population before outcomes. Those numerical admission floors are deliberately NOT invented here. The missing owner ruling is a real uncompleted gate, not hidden 'TBD' engineering work.

### 7.6 What this contract settles and what it does not

Settled for the proposal: specific forecast question, separate anticipation/continuation origins, proposed outcome/horizon, comparator structure, treatment of unavailable and ambiguous data, no probability from labels or ratios, and no reopening of killed/protected constructions.

Still needed before any predictive run: exact eligible universe and data vintage, source-writer/measurement adaptation approval, frozen scale/grammar/availability rules, logged trial/admission, formal statistical floors and designated unexposed/prospective cohort. The GDX episode examined in this conversation is discovery material and is excluded from any claim of untouched validation.

## 8. Deterministic versus statistical versus explanatory work

Deterministic work should establish timestamps, source lineage, bar order when observed, structural constraints, and the arithmetic of announced targets. A statistical model may estimate event probabilities only from the admitted calibration process. An LLM may help explain alternatives, compare the published doctrine and surface contradictions; it cannot originate numeric confidence or scored risk authority from a persuasive wave narrative.

Useful completion is not 'a parser exists'. It is a demonstrated improvement on the declared question, with understandable user/machine delivery and an explicit decision boundary. Before evidence, a faithful reconstruction can improve explanation, but must retain 'unvalidated forecast' rather than borrowing Prophet or Risk Radar authority.

## 9. Superseded disposition and next action — historical only

**Disposition:** preparation advanced; narrow input-contract questions characterized; experiment specified enough for an owner review but NOT admitted, built or proven. No external worker was started, no watcher armed, no queue changed and no market outcome read.

**Next action:** the existing cycle/timing and evaluation owners review the source-compatibility findings and the proposed continuation estimand together. They must accept an exact causally available representation and trial contract, or reject that specific construction. Only then may an outcome study start. Any necessary source adjustment is a separately approved owner change, not a new swing/identity/event plane.

This continuation must not become another loop of redrawing the two original GDX images. Their primary source chain is already recovered; the unresolved author-specific private choices stay unknown.

## Reproduction and publication boundary

Run the compact characterization probe from an existing authorized Macro checkout that already contains the pinned object:

```sh
PYTHONDONTWRITEBYTECODE=1 python research/technical_opportunity/elliott_phase/source_contract_probe.py
```

This reads the exact pinned `engine/cycle_ontology.py` with `git show`, verifies its Git blob and the selected definition ASTs, and executes only those definitions on synthetic arrays. It is not a predictive study. In a partial clone, ensure the pinned object is present under the existing owner's normal access policy; do not use this probe to bootstrap authentication or modify another worker's checkout.

An explicit local source/excerpt may be supplied with `--source`; that mode verifies the same three AST fingerprints and truthfully records whether the supplied bytes are the full pinned blob. The complete 19-case characterization archive also includes the ordered-path and OHLC-ambiguity examples. The compact repository probe does not claim to reproduce all 19 cases.

Source-only review publication does not ratify the experimental contract, amend the kill registry, admit an outcome read, or certify any production consumer. The associated discovery is historical/version-scoped; a later owner repair may supersede it without rewriting the earlier evidence.

## References

All internal sources are pinned to the Macro commit printed above unless otherwise stated. External method sources define methods, not verified market accuracy.

- **I1:** `engine/cycle_ontology.py`, especially `TurnParams`, `turn_epoch`, `detect_turns`, `classify_phase`, and `project_next`. Compact repository reproduction: `research/technical_opportunity/elliott_phase/source_contract_probe.py` and `research/technical_opportunity/elliott_phase/source_contract_probe_results_2026-09-11.json`. Full 19-test source fixture and analytical examples are in the accompanying conversation archive (`analysis/test_contract.py`, `analysis/results.json`, `source/pinned_turn_excerpt.py`).
- **I2:** `research/ENTRY_STACK_EXPANSION_MASTERPLAN_BY_FABLE.md`, section 2: explicit generic Fibonacci/Elliott triage; sections 1, 7, 8 and 10: existing graders/trial process.
- **I3:** `research/ANTICIPATION_PHASE0.md`, forward-drawdown and direction sections.
- **I4:** `engine/lab.py`, `engine/trial_ledger.py`, and existing Live Entry Radar replay owner. This packet does not invoke them.
- **I5:** `agentos/README.md`; `agentos/schema/discovery.schema.yml`.
- **E1:** Elliott Wave International, Truncation: https://www.elliottwave.com/waveopedia/truncation/
- **E2:** Elliott Wave International, Triangles: https://www.elliottwave.com/waveopedia/triangles/
- **E3:** Glenn Neely, channel endpoint convention: https://www.neowave.com/qow/qow-archive-303.asp
- **E4:** Glenn Neely, pattern confirmation: https://www.neowave.com/qow/qow-archive-1109.asp
- **E5:** Glattfelder and Golub, *Bridging the Gap*, arXiv:2204.02682: https://arxiv.org/html/2204.02682v1
- **E6:** Gneiting and Raftery, *Strictly Proper Scoring Rules, Prediction, and Estimation*: https://doi.org/10.1198/016214506000001437
- **E7:** Sullivan, Timmermann and White, *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*: https://doi.org/10.1111/0022-1082.00163
