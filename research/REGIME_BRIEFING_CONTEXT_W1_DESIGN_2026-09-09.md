# W1: useful regime context through the existing briefing reader

Status: design frozen by Sol for bounded implementation under current Chairman continuation; no production claim.
Operation: regime-hmm-w1-briefing-context-20260909-sol-001.
Base: macro a4d33f32dad140acdfa081b21f55ad6d8dcb94d4. Protected procedure: Mastermind f3f2d9155796876009f2d427bfdecc7ee7b63e74.
W0 remains on PR7015, untouched. W1 is a separate context-only capability, not its release or a trading overlay.

## Source correction to the earlier W1 proposal
The older proposal correctly found world_state and brief_context drop probability fields, but missed an
EXISTING direct reader: master_brain._build_regime_path already consumes quad_vector.transition_momentum.
That reader drops source dates and reconstruction basis while instructing the model to describe where a
regime could tip. The shared _REGIME_MAP_LAW repeats that unearned forecast interpretation.
Use this existing direct path; do not add a second probability route via world_state/brief_context.
The existing AI brief bodies are SERVER-rendered through templates/_aibrief_body.html.j2, not aibrief.js.

## Observable outcome
A user can see a dated explanation of the current-state estimate and its limitations in the existing
macro AI brief. The synthesis model receives the same probabilities, source date, missingness and basis.
Diagnostic reconstructed movement cannot be described as a future-state or profit probability.
The confirmed label is preserved even when the model estimate disagrees; no forced consensus.

## Frozen scope
engine/master_brain.py; templates/_aibrief_body.html.j2; existing focused tests. A minimal existing-code-job
suite registration is allowed only if the relevant tests are not already executed before merge.
No HMM fit changes, new dependency/service/store/queue/clock, new page/CSS palette, world_state path,
source ledger writes, rank/gross/entry policy, allocation, output-thesis rules, or paid model calls.
Normal production generation remains the only adoption path. run(persist=False) is NOT a read-only probe:
it still appends the existing macro thesis ledger. Tests isolate roots and intercept ALL model/write effects.

## Contract and method
Extend existing macro.regime_path with one compact probability_context; do not pass reconstructed history.
Copy valid producer p values unchanged (exact Q1..Q4 numeric simplex, finite, nonboolean, range0..1,
four-decimal tolerance0.00021); never normalize corrupt input into a belief. Missing/invalid/degraded
fallback yields an explicit unavailable context, not a measured uniform distribution. Preserve the raw
source asof and optional model_fit_asof/confidence_basis; absent new W0 metadata remains unknown.
Current estimates are descriptive only and historical_replay_eligible is always false. Do not infer future
horizons, return skill or PIT provenance. Heuristic confidence is not a calibrated success probability.
Preserve diagnostic momentum values for compatibility, but carry its basis/date/missingness and replace
both existing forecast-sounding instructions. Unknown basis is stated, never fabricated. Absent/degraded/
stale/undated diagnostics must not be used as current transition direction.
Use existing source freshness machinery: Synapse regime-latest freshness_sla_hours and DataOS
quality.check_freshness with an injected reference time; do not add a new clock, SLA table or store.
A future source date is invalid; invalid/missing registry or clock evidence degrades to unknown freshness.
A valid but stale distribution may be retained ONLY as explicitly dated historical context, never current.

## Visible consumer
The existing producer run attaches a deterministic bilingual regime_evidence note, derived only from
its selected regime_path context, to the saved macro brief. A model-supplied value cannot override it.
Other lenses keep their existing output. The shared body renders this optional macro note using existing
text/material classes and escaped EN/ZH strings; older briefs without it retain their former rendering.
Visible copy distinguishes current estimate, source date, stale/unavailable basis, and not-a-forecast.
Detailed state percentages may be in the existing disclosure/tooltip treatment, not an extra loud score.
Do not alter the fixed house-law badge, section hierarchy, stance vocabulary, or calibrated-authority gates.
Dark/light share semantics but must both remain legible; EN/ZH and390/1440px must be exercised.

## Implementation order and acceptance
First run baseline tests and write discriminating failures. Then repair the existing reader/prompt;
add deterministic saved-output evidence and the shared-renderer note; run focused tests and source guards.
Required cases: valid p unchanged, missing/invalid/bool/nonfinite/oversized p, degraded uniform fallback,
missing/future/source dates, known-stale versus fresh, missing SLA, missing W0 metadata, label disagreement,
momentum basis retained with no forecasting instruction, false model-authored evidence overwritten,
backward-compatible older briefs, unaffected other lenses, escaped source strings, and read-only isolation.
A real committed latest.json must traverse the actual reader to the real template in an isolated proof.
Record source hashes and date, exact candidate, renderer and resulting bilingual visible copy. This is
local real-input proof, never customer production. Full test commands must be real CI code-gate owners.

## Routing and stop
Sol owns the frozen interpretation and final acceptance. A finite native Terra worker may edit only
this isolated W1 worktree; no commits/push/PR/merge/credentials/installed settings, no production data,
no network/model-generation calls, no extra agents or background watcher. Return exact changed paths,
RED/GREEN commands and limits, then terminate. Sol retains release custody. No Executive Job is inferred.
Stop for a source conflict, model/policy change, extra control plane, ambiguous effect or missing consumer.
No permission to modify W0 PR7015 or to turn the separate HMM/RL paper into an allocation rule.

## Source/collision receipt
At pickup, all100 inspected open-PR file inventories had no match for master_brain.py, the shared body,
its named existing tests, world_state or brief_context. This is a bounded100-PR census, not all-estate proof.
PR6974's economic-backdrop changes are in other modules/dashboard source, not this reader/shared-body scope.
The W1 worktree is fresh from current main, separate from W0's reviewed carrier. Its source can be reviewed
while W0 CI runs; production acceptance never transfers between them. The prior W1 route is superseded
ONLY for this briefing consumer. Other Neural Web consumers still need their own owner-routed integration.

## Clarifications from the bounded implementation review
The shared _REGIME_MAP_LAW is embedded in all three lens prompts, so its nonforecast interpretation
changes across macro/China/BTC. Only macro receives the new selected probability context and saved
regime_evidence field; no other lens input, renderer field, model selection or portfolio rule is added.

The regime-label regression suite belongs in the existing code-gated unrun-brain-desks command,
not only the post-nightly data-health lane. Move it once, without duplicate execution or a new job.
The existing contract-delta found six precise dependency-scope omissions in three exclusive jobs;
adding the existing DataOS quality/temporal paths to those scopes is required integration, not a
broader CI redesign. Existing job gates and all unrelated commands remain unchanged.

A tied maximum preserves all supported names and the confirmed label; it must not invent a unique
conflicting winner. Detailed evidence translates the canonical heuristic basis and prints a present
fit cutoff. Missing metadata stays unknown. The existing Lens trigger is keyboard-focusable.
