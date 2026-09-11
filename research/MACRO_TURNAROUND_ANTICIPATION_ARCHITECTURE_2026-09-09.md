# Macro Turnaround Anticipation — Product and Intelligence Architecture

**Date:** 2026-09-11
**Operation:** `anticipate-macro-turnarounds-continuation-20260909-sol-001`
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@e61f2951136bdc03a7ec2f5f12f960af26656a4c`
**Macro implementation base:** `d1d7273330df22014849d438160c0c393f4763a3`
**Capability state of this slice:** **BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT**

## Outcome before code

### User job

Tell an investor or researcher that a macro contraction, trough, recovery, peak,
or slowdown may be forming **before the consensus narrative is obvious**, while
showing what changed, which independent families agree, which contradict, when
each input was actually known, and why confidence is limited.

### Machine and intelligence job

For an explicit historical or current `as_of` date, select only observations
whose release availability was known by that date; preserve later revisions as
new vintages; normalize level, slope, and acceleration evidence; cap correlated
family concentration; calculate breadth and data quality; preserve phase
hysteresis; and emit a deterministic, correction-safe research artifact.

### Moat

The moat is not one formula. It is the joined system of point-in-time release
vintages, revision history, cross-family and cross-region evidence, causal and
market-confirmation graph context, replayable predictions, calibrated outcome
measurement, transparent corrections, and a premium workflow that lets a user
move from turn alert to drivers, evidence, scenario impact, and watchlist action.

### 10/10 end-state

A live Macro Turnaround Desk continuously maintains US, China, Europe, global
trade, liquidity, credit, inflation, labor, housing, consumer, and market
confirmation evidence. It distinguishes data release, source revision, signal
change, phase change, and confidence change; provides a point-in-time timeline;
shows leading and contradicting families; exposes regime-conditioned scenario
paths; measures real-time lead time and false-turn rate; and learns from every
miss without rewriting history.

## Capability ledger at this checkpoint

| Capability | State | Evidence / boundary |
|---|---|---|
| Point-in-time observation selection | BUILT_NOT_PROVEN | Period and release availability are distinct; future and conflicting vintages fail closed. |
| Revision-safe immutable identity | BUILT_NOT_PROVEN | Input, config, artifact, manifest, source, and replay identities are deterministic and correction-safe. |
| Multi-horizon direction and acceleration | BUILT_NOT_PROVEN | Robust level, short slope, medium slope, acceleration, and explicit unidentifiable-scale withholding. |
| Independent-family breadth | BUILT_NOT_PROVEN | Configured family budgets prevent duplicate-series authority and disclose infeasible family caps. |
| Phase state with hysteresis | BUILT_NOT_PROVEN | Research-only contraction, troughing, early recovery, expansion, peaking, slowdown, or indeterminate state. |
| Correction and evidence-change projection | BUILT_NOT_PROVEN | Active values, vintage identity, revisions, new periods, withdrawals, exclusions, and quality changes stay distinct. |
| Immutable JSON machine consumer | BUILT_NOT_PROVEN | Create-only hard-link publication; identical replay is idempotent; conflicts and symlinks fail closed. |
| Existing canonical full-vintage adapter | BUILT_NOT_PROVEN | Read-only reuse of `engine.release_target_truth`; source and manifest bytes are digest-verified before native Parquet decoding. |
| Point-in-time replay | BUILT_NOT_PROVEN | 156-cutoff PPIFIS replay proves bounded mechanics only; no broad-family or forecast claim. |
| Pre-merge CI ownership | BUILT_NOT_PROVEN | Dedicated `macro-turnaround-research` code-gated job; hosted execution remains required. |
| Calibrated forecast | NOT_BUILT | Raw scores and phases are explicitly unvalidated research values. |
| Broad independent-family real-data panel | NOT_BUILT | PPIFIS-only proof is not macro breadth. |
| Live scheduled production run | NOT_BUILT | No scheduler, queue, publication owner, or product route is introduced. |
| User-facing Macro Turnaround Desk | NOT_BUILT | No UI is called shipped by this source wave. |
| Ranking, gating, sizing, or trade authority | REJECTED_BY_DESIGN | The fixed authority boundary cannot be caller-configured. |

## Architecture and no-rebuild boundaries

1. **Extend the existing observation plane.** A future adapter must read the
   repository's canonical economic observation and provenance records. This
   slice defines no database, event bus, queue, scheduler, identity service, or
   publication store.
2. **Separate deterministic evidence from learned calibration.** The current
   engine creates replayable features and raw scores. Calibration is a later,
   separately versioned model trained only on expanding-window historical
   folds and accepted only after held-out and forward validation.
3. **Keep authority explicit.** Descriptive context and research priority may
   consume this artifact. Forecast, ranking, gating, and trade systems may not.
4. **One correction-safe artifact identity.** `input_hash` binds the exact
   eligible vintage; `config_hash` binds specifications and engine config.
   A revision creates a new artifact. Historical artifacts are immutable.
5. **Fixed authority, not caller policy.** The authority object has no configurable
   constructor. Descriptive context and research priority are the only enabled
   fields; no caller may instantiate an escalated variant.
6. **No family-count masquerade.** Many correlated indicators in one family
   split one capped family share; they cannot simulate independent breadth.
7. **No one-print phase churn.** Enter and hold thresholds are distinct and a
   prior phase is carried through walk-forward evaluation.

## Data, time, null, and correction law

- `period` is the economic period; `available_at` is when that
  exact vintage could first be known. They are never interchangeable.
- A historical run may use only records with both timestamps at or before its
  `as_of` boundary.
- When several vintages exist for one period, the latest vintage available by
  that boundary wins; later vintages remain invisible until released.
- Missing, stale, or short-history indicators never receive neutral synthetic
  values. They are excluded with typed reasons and lower coverage/confidence.
- Excessively stale panels return `indeterminate` with zero confidence,
  rather than preserving a persuasive-looking old signal.
- A correction never mutates a prior artifact. It mints a new input hash and a
  new artifact under the existing publication owner when that owner is wired.

## Deterministic versus model method

This slice is deterministic: transforms, robust normalization, slopes,
acceleration, family caps, breadth, quality, raw evidence scores, and phase
hysteresis. No LLM originates, ranks, sizes, gates, or trades from the result.
A future statistical calibration layer must be point-in-time, regime-aware,
expanding-window, and evaluated on an untouched acceptance period. Narrative
models may explain already-grounded drivers but may not change numeric state.

## Failure states

The engine fails closed on unknown configuration fields, duplicate indicator
keys, invalid booleans, invalid thresholds, empty specifications, and malformed
observations. It excludes future, missing, insufficient-history, and overly
stale series. Below minimum coverage it emits indeterminate/zero confidence.
Both CLIs serialize into a unique complete sibling and publish by create-only
hard link. They never replace existing history; identical reruns are idempotent,
while conflicting, symlink, canonical-data, and generated-site destinations fail.
Malformed input returns nonzero and publishes no success artifact.

## Product path after this source wave

1. Land this source/replay contract through exact-head review, hosted code-gate
   proof, merge, and post-merge source verification.
2. Freeze versioned target and evaluation semantics before fitting or measuring
   any predictive claim.
3. Expand the read-only adapter across genuinely independent growth, labor,
   credit, liquidity, housing, trade, and market-confirmation families without
   creating a second observation store.
4. Build expanding-window and untouched acceptance-period replay; measure Brier
   score, reliability, precision/recall, false-turn rate, phase churn, median lead
   time, and regime-conditioned performance.
5. Add correction learning and narrative explanation only over grounded numeric
   state; narrative models may not change scores or authority.
6. Publish through the existing canonical publication plane and build the premium
   Turnaround Desk only after the data and evaluation gates are accepted.
7. Require real production input, visible browser evidence, correction proof, and
   learning instrumentation before calling the product live.

## Acceptance for this source wave

- Historical selection is release-vintage-safe and invariant to future records,
  input ordering, identical duplication, and post-cutoff corrections.
- Malformed, nonfinite, stale, unidentifiable-scale, irregular-frequency, and
  conflicting evidence fails closed or remains explicitly unavailable.
- Immutable output resists replacement, symlink redirection, and concurrent
  conflicting publishers.
- Manifest and source digests are verified before native canonical-data decoding;
  parser and historical-availability limits are visible in the report.
- The five owning suites run exactly once in a code-gated CI job whose declared
  scope covers the source/replay closure.
- Every authority field beyond descriptive context and research priority is fixed
  false and cannot be enabled through construction.
- Fresh final tests, mutation proof, real bounded replay, independent exact-head
  review, hosted CI, merge, and post-merge verification are all separately recorded.
- A source merge is reported as `BUILT_NOT_PROVEN`, never calibrated, deployed,
  product-live, or trading-authorized.

This document is architecture and implementation evidence. It is not a claim
of calibration, deployment, production proof, or final product acceptance.


## 17. Source-candidate implementation addendum — 2026-09-11

This addendum narrows what the first source PR establishes. It does not change the full product thesis above.

- The source candidate implements a deterministic research engine, an immutable JSON publication path, and a read-only adapter over the existing `engine.release_target_truth` full-vintage owner. It creates no collector, release calendar, observation store, model registry, scheduler, product surface, or authority plane.
- Historical selection uses observation period plus `available_at`; conflicting same-vintage values fail closed. Evidence age is the maximum of economic-period age and release age, so a late revision cannot make an old period economically fresh.
- Family coverage uses configured family budgets. Correlated indicators cannot erase missing independent families through renormalization.
- Unsupported transformation scale, undefined percentage changes, malformed/nonfinite inputs, irregular monthly year-over-year history, duplicate replay cutoffs, and conflicting vintages are unavailable or rejected rather than converted into neutral evidence.
- The point-in-time replay verifies manifest and source bytes before decoding, reuses the canonical release-target normalizer, discloses whether the native Parquet parser ran, distinguishes revisions/new periods/refreshes/withdrawals, and emits create-only research artifacts.
- `score_status=available_research_only`; phase, confidence, horizon, and standardized slopes remain unvalidated research values. The source PR cannot establish economic predictive skill, calibration, product utility, production availability, Prophet eligibility, ranking, gating, sizing, or trade authority.
- The bounded real-data proof is PPIFIS-only. It validates point-in-time selection and reproducibility, not broad macro breadth or independent economic cycles.

The target/evaluation freeze, T1/T2 builder, broader E2 family adapters, baseline scorecards, learned models, correction loop, and premium Turnaround Desk remain later dependency-gated capabilities.
