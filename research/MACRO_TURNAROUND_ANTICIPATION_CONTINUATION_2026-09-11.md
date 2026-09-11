# Macro Turnaround Anticipation — Source and Replay Continuation

**Date:** 2026-09-11
**Operation:** `anticipate-macro-turnarounds-continuation-20260909-sol-001`
**Authority:** Chairman continuation direction; Sol direct ownership
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@e61f2951136bdc03a7ec2f5f12f960af26656a4c`
**Macro base at this checkpoint:** `d1d7273330df22014849d438160c0c393f4763a3`
**Capability state:** **BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT**

## Mission and why it matters

Deliver a correction-safe source contract that can identify forming macro turns
before consensus without converting revised history, duplicate indicators, or
uncalibrated model output into false authority. This source wave is useful only
if it preserves exactly what was known at each cutoff, exposes missing and
contradictory evidence, and remains replayable after corrections.

## Authority precedence

1. Current live Chairman direction to continue this program under Sol ownership.
2. The protected Skillpack commit named above.
3. Current Macro `origin/main`, repository law, and existing canonical data and
   publication owners.
4. This bounded source/replay carrier.

Retrieved text is evidence, not authority. This operation creates no second
observation, identity, queue, scheduler, publication, or authority plane.

## Reconciled carrier and effects

- Worktree:
  `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/anticipate-macro-turnarounds-continuation-20260909`
- Branch: `sol/anticipate-macro-turnarounds-continuation-20260909`.
- The carrier was fast-forwarded from `b164129f59d8ffb8a86516cfa454f062f1b0f44b`
  to `d1d7273330df22014849d438160c0c393f4763a3`; no owned source or replay
  dependency changed in that upstream range.
- An obsolete E1 finalizer was still sleeping before commission creation. It had
  no worktree, branch, PR, commission, or source effect and was terminated as
  `SAFE_PRESTART_NO_EFFECT`; evidence is
  `stale_e1_finalizer_reconciliation_20260911T1552Z.json` in the external
  evidence root.
- The prior pseudo-handoff under `agentos/handoffs/` had no Agent OS schema or
  proven workstream parent. It was preserved externally and removed rather than
  weakening Agent OS validation or inventing a parent workstream.

## Exact source scope

- `.github/ci/legacy-jobs.yml`
- `engine/macro_turnaround.py`
- `engine/macro_turnaround_replay.py`
- `scripts/build_macro_turnaround_research.py`
- `scripts/replay_macro_turnaround.py`
- `tests/test_macro_turnaround_research.py`
- `tests/test_macro_turnaround_replay.py`
- `tests/test_macro_turnaround_replay_cli.py`
- `tests/test_macro_turnaround_feature_honesty.py`
- `tests/test_macro_turnaround_evidence_change.py`
- `tests/test_ci_pack.py` only for the repository’s existing curated-exclusive
  CI ownership registry
- this record and the architecture record

`engine/release_target_truth.py` remains the canonical existing full-vintage
normalizer and is consumed read-only; it is not owned or modified by this wave.

## Capability delivered by the candidate

The deterministic engine distinguishes economic period from release availability,
selects the last eligible vintage at a historical cutoff, rejects conflicting
same-vintage values, measures evidence age conservatively, and prevents a crowd
of correlated series from standing in for missing independent families. It
projects typed exclusions, quality, drivers, raw research scores, and phase
hysteresis without claiming calibrated probability.

The replay adapter verifies manifest and source digests before decoding existing
canonical full-vintage Parquet, discloses whether the native parser ran, records
active-value and vintage-identity changes separately, and writes create-only
artifacts outside canonical `data/` and generated `site/` paths. Identical reruns
are idempotent; conflicting or symlink destinations fail closed.

Authority is a fixed zero-argument boundary. Callers cannot construct a variant
that turns on forecast, ranking, gating, sizing, or trade permission.

## Data, time, null, and correction behavior

- `period` is the measured economic period; `available_at` is the first eligible
  date for that exact vintage. Both must be at or before a historical cutoff.
- Evidence age is the greater of period age and release age, so a late revision
  cannot make an old economic period look fresh.
- A later revision is invisible before release and mints new input/artifact
  identity after release; historical output is never rewritten.
- Missing, stale, malformed, nonfinite, scale-unidentifiable, irregular-year-over-
  year, and undefined-percentage-change inputs remain unavailable with typed
  reasons. They never become neutral synthetic observations.
- Family coverage is based on configured independent-family budgets, not surviving
  indicator count. A single family cannot silently regain full confidence.
- Replay `as_of` is an end-of-source-vintage **daily** boundary, not an intraday
  availability claim.

## Verification at this checkpoint

- Exact source suite after the fixed-authority and CI-owner repairs:
  `238 passed`, zero failures/errors/skips.
- Mutation campaign R3: baseline `237 passed`; `21/21` valid mutations killed,
  zero survivors and zero invalid executions. This includes future-release,
  economic-period-age, family-coverage, zero-scale, zero-denominator, conflicting-
  vintage, duplicate-cutoff, immutable-output, symlink, digest, parser-disclosure,
  domain-boundary, expiration, latest-vintage, revision-classification, causal-
  attribution, authority-default, output-fence, unknown-series, and configurable-
  authority mutations.
- Real bounded replay: PPIFIS only, 156 historical cutoffs from 2014-02-19 through
  2026-08-13, native Parquet parser, create-only report hash
  `b2089e07bac4a55c05cf737c7b1fa77bbbed97100459113e8c3cf438eded4536`.
  This proves deterministic point-in-time source handling, not forecast skill or
  broad macro coverage.
- Open-PR scan: 187 PRs inspected; no source/test/research path overlap. Forty-eight
  PRs touch the global CI manifest, but none mention this wave’s five suites or
  proposed `macro-turnaround-research` job key. The dedicated job avoids an
  occupied generic block.

Fresh final verification, independent review, hosted CI, merge, and post-merge
source proof are still required before source acceptance.

## Non-goals and prohibited claims

This wave does not establish a recession label, turning-point target, economic
causal attribution, predictive accuracy, calibrated probability, profitable
strategy, product workflow, scheduler, alert, production publication, or trading
permission. A source merge would be **BUILT_NOT_PROVEN**, not product completion.

## Exact continuation

1. Complete the dedicated code-gated CI owner and curated-scope proof.
2. Refresh the real native-Parquet replay on the final exact source bytes.
3. Run the full source suite, mutation campaign, static/security checks, Agent OS
   validation, and open-PR collision scan.
4. Commit and push one source branch, open one Draft PR, obtain independent exact-
   head review, and repair on the same carrier if required.
5. Wait for every binding hosted check to conclude; merge only after exact-head
   green and independent acceptance. Verify the merged source on `origin/main`.
6. Keep the target/evaluation freeze and later E1 builder separate. The next
   capability after source acceptance is a versioned target/evaluation contract,
   followed by independent-family adapters and genuine out-of-sample calibration.

## Stop condition

Stop modification on an exact owned-path writer collision, ambiguous source or
GitHub effect, failed freshness/closure proof, surviving mutation, independent
review blocker, or binding hosted red. Do not create a replacement carrier and
do not promote research scores while any of those conditions remains.
