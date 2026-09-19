# Macro Turnaround Anticipation — Product and Intelligence Architecture

**Date:** 2026-09-16
**Operation:** `anticipate-macro-turnarounds-continuation-20260909-sol-001`
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@bf843961c0e1b5bd45fa481f0138c71f2a87d4e2`
**Exact integrated source head:** `bd8f56c66d7d1ca2e124285874dfac0af9802a37`
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
| Independent-family breadth | BUILT_NOT_PROVEN | Configured family budgets prevent duplicate-series authority; the caller cap is constrained to `(0, 0.5]`, so one family cannot claim complete breadth. |
| Phase state with hysteresis | BUILT_NOT_PROVEN | Research-only contraction, troughing, early recovery, expansion, peaking, slowdown, or indeterminate state. |
| Correction and evidence-change projection | BUILT_NOT_PROVEN | Active values, vintage identity, revisions, new periods, withdrawals, exclusions, and quality changes stay distinct. |
| Immutable JSON machine consumer | BUILT_NOT_PROVEN | Create-only hard-link publication; identical replay is idempotent; conflicts, symlinks, and canonical `data/` or generated `site/` destinations fail closed. |
| Existing canonical full-vintage adapter | BUILT_NOT_PROVEN | Read-only reuse of `engine.release_target_truth`; source and manifest bytes are digest-verified before native Parquet decoding. |
| Point-in-time replay | BUILT_NOT_PROVEN | 157-cutoff PPIFIS replay proves bounded mechanics only; no broad-family or forecast claim. |
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
   split one capped family share; they cannot simulate independent breadth. The
   caller-visible cap cannot exceed `0.5`, so this protection is not an on/off
   switch disguised as configuration.
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
- Malformed, nonfinite, stale, unidentifiable-scale, irregular monthly
  year-over-year history, irregular replay history, and conflicting evidence
  fail closed or remain explicitly unavailable.
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

## 18. Independent-review repair addendum — 2026-09-15

The first exact-head adversarial review accepted the core temporal, identity,
immutability, CI-ownership, and fixed-authority design but found three release
blockers. The same carrier now closes them without widening capability claims:

- both research CLIs reach a shared publisher guard that rejects repository
  `data/` and generated `site/` destinations before publication;
- `family_weight_cap` is restricted to `(0, 0.5]`, so a single family can never
  configure itself into complete breadth;
- explicit engine and replay regressions prove that a future economic period
  stays invisible even when a malformed source gives it an early release date;
- loader regressions preserve missing-source disclosure and refuse an all-missing
  requested panel; and
- both executable scripts use the repository's unconditional, file-derived
  import pin before any repository import.

Two nonblocking boundaries remain explicit rather than being called solved.
The direct engine/build path assumes caller-supplied regular spacing for
`LEVEL`, `DIFF`, and `PCT_CHANGE`; the canonical replay adapter independently
requires complete monthly active history. Frequency typing is a later contract
rather than an inferred rule in this PR. Also, shared JSON/publication helpers
remain implemented in the build-script module and imported by the replay engine;
that layering cleanup must be a bounded follow-up if adopted, not a reason to
create a duplicate publication or parsing plane here.


## 20. Exact integrated evidence addendum — 2026-09-16

The integrated source at `bd8f56c66d7d1ca2e124285874dfac0af9802a37`
retains the architecture above and closes the accepted rereview's remaining
path-fence regression gaps without widening authority. Exact local evidence is
259 focused tests, 11 import-pin tests, 5 CI-contract tests, and 35/35 killed
mutations. The current manifest-bound PPIFIS proof reconstructs 157 cutoffs from
19,828 full-vintage rows, passes canonical-normalizer parity, preserves immutable
idempotence, and refuses a conflicting replacement.

This remains one inflation-series mechanics proof. Broad independent-family
coverage, a frozen target/evaluation contract, calibrated forecast skill, live
product workflow, production scheduling, and ranking/sizing/gating/trade authority
remain unbuilt or rejected by design as stated in the ledger. Candidate-owned
blobs changed after the accepted `64e76b8` rereview, so fresh exact-head review
and hosted CI are release requirements rather than optional repetition.
