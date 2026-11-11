# W1 proposal — make existing regime uncertainty useful in the real briefing

**Status:** SPEC_ONLY; no W1 worker assigned, no code or production change in this proposal.
**Parent thesis:** research/HMM_REGIME_INTELLIGENCE_RESEARCH_2026-09-09.md. W0 source carrier is PR7015.
**Owner boundary:** existing market-regime-risk producers and Neural Web context consumers; no new model, bus, or trade policy.
**Evidence pin:** macro2419398dde91e08563e91399786046ff7ec8c069.

## The measured missing connection
`world_state._compose_regime` explicitly selects a fixed set of fields from the regime artifact. It
omits both `quad_vector` and `regime_one`. `brief_context._block_market_core` then selects only quad,
confidence, transition_state, and flip_margin from the composed regime block. Therefore adding a
probability or honesty field to the producer alone does not get it to this briefing path.

The exact pinned pure world-state composer was exercised with a synthetic existing-artifact-shaped
input: both probability context and reconstruction basis were absent from its output. Receipt:
`research/artifacts/regime_history_honesty_20260909/world_state_projection_gap.json`.
This finding is limited to these two projections, not a claim that all Neural Web readers lack every
regime probability. Fixing the user journey requires its real final consumer, not another schema alone.

## User and machine job
User question: Why did the environment assessment become less certain while the sticky economic label
stayed the same, what evidence matters, and which next observation would change the interpretation?
The machine must distinguish a current model estimate, a heuristic confidence, a diagnostic change
inside today's fitted coordinates, an actually recorded earlier belief, and an explicit future forecast.
No answer may convert the first four into the fifth merely by using predictive language.

## Proposed vertical path
Existing regime owner -> existing quad_vector publisher -> world_state.regime context ->
brief_context.market_core.regime -> one existing generated briefing/dossier with evidence attribution.

## Proposed compact content contract
Reuse W0's published source fields; do not recompute the HMM or introduce duplicate identities. Carry
only current four-state probability, source asof, model fit cutoff, source/basis, degradation reason,
sticky-label agreement, and heuristic-confidence basis. Do not copy the entire reconstructed history
into a prompt. If diagnostic momentum is included, its reconstruction basis must travel with it.
Exact field nesting/versioning must be frozen after the existing consumer and budget-contract census.

A uniform fallback remains degraded ignorance, not a measured25% market forecast. A malformed simplex
is unavailable, not repaired into an authoritative distribution by the text layer. An unsupported state
is not evidence that an economic environment is impossible. Missing model cutoff or asof is explicitly
unknown, not silently borrowed from the briefing build clock. Current estimates are not future forecasts.

## Deterministic versus model work
The projection and validation are deterministic, consuming emitted fields from the existing owner.
A language model may explain the supplied evidence and formulate explicitly labeled research questions.
It may not manufacture probabilities, use prose certainty as calibration, rank stocks, or adjust risk.
Formatting changes must not alter the neural reliability Kernel, Conditional Fusion, or portfolio policy.

## Acceptance: one useful result, not merely a connected field
A normal production source must pass through both existing projections into the actual briefing input
and visible output. Capture source identity, selected context, emitted explanation, and final rendered
result. The user must be able to answer the stated question and locate supporting evidence without
reading raw JSON. An existing machine consumer must see the same basis and missingness distinctions.

Demonstrate normal, stale, missing, malformed, uniform-fallback, unsupported-state, and sticky-label /
posterior-disagreement cases. The latter is not automatically an error. Verify that truncation/budget
handling never strips the caveat while retaining the probability. Show no historical-reconstruction
value entering an as-issued record. W0's CLI is a prerequisite tool, not proof this briefing already works.

## Ordered implementation after acceptance of this proposal
1. Refresh protected procedure, W0 acceptance, current main, source writers, and exact open-path collisions.
2. Identify the existing published briefing/dossier route and source-to-render tests. Preserve its design
   tokens, EN/ZH, dark/light, desktop/mobile, and permission boundaries. No new standalone regime page.
3. Freeze compact context fields, no-invention rules, null behavior, and budget/truncation behavior.
4. Add failing producer-to-world-state-to-brief-context tests and final-consumer expectation cases.
5. Extend only the existing projections and final consumer. Preserve numerical model and policy outputs.
6. Run exact-head tests, obtain independent review, and prove the real normal publication path plus
   negative states. Do not call a local fixture, a merged schema, or model prose a production result.

## Non-goals and stop conditions
No new regime verdict, graph, signal rank, trading gate, state store, HMM fit, control plane, or model
retraining service. No modifying scope in held PR6685 or policy-transition PR6788. No takeover of an
occupied Cortex/world_state/briefing source writer. If the actual consumer requires an ownership or
semantic change outside this slice, return the concrete conflict for Sol adjudication instead of cloning.

The fresh support census on59,880 track-record rows still rejects all five rich regime axes for
conditioning claims. W1 remains useful explanatory context; it does not reopen the prior reliability
construction or turn thin observations into calibrated return predictions. The research gate itself is
unchanged and its complete receipt is current_conditioning_coverage.json beside the W0 evidence.

## Next proof boundary
W2 must define actual future events/horizons and compare against persistence, prevalence, and continuous-
feature baselines through the existing evaluation owner. W1 descriptive value is not W2 predictive skill;
W2 skill is not permission to alter portfolio weights. No downstream wave is assigned by this document.

## Current-source consumer closure (additional 2026-09-09 investigation)
Rechecked on macro `a55b08aa09c99ef36dc7500c63371126e3d46008`. The concrete US path is
`world_state._compose_regime` -> `brief_context._block_market_core` / `macro_slice` ->
`master_brain.gather_state()['neural_web']` -> `master_brain.synthesize` / `run(lens='macro')` ->
`data/regime/master_brief.json` and `site/master_brief.json` -> the existing AI briefing surface
(`templates/aibrief.html.j2`, existing paired briefing JavaScript). No separate regime page is needed.

**Prior-run context is intentional, not a scheduler defect.** Daily source calls master_brain around
line3489 and build_world_state around4346. ADB-R1 in `AI_DAILY_BRIEF_DEEPWIRE_MASTERPLAN_BY_FABLE.md`
explicitly requires committed prior-run context. W1 must not reorder those jobs, add a second world
builder, or call the old context current-session evidence. The probability object's own asof travels
through the projection and must not be replaced by the fresh briefing/verdict timestamp.

**A dry-looking caller is not necessarily read-only.** `master_brain.run(persist=False)` still calls
`_append_ledger` for the macro lens after synthesis (source lines2774-2775). Never invoke this as a
read-only production probe. Fixture tests must isolate the root and intercept model calls and ledger
effects. Real product proof uses the accepted normal production generator, not a forced paid re-call.

**Compact nesting proposal:** add an optional `regime.probability_context` projection, containing only
the producer's current p, asof, model_fit_asof, source, hard-label agreement, degraded/degrade_reason,
confidence_basis, and optional momentum with its basis/false replay eligibility. Reuse source field
names; do not invent a schema-wide version bump or another posterior. Numeric values and their caveats
form one indivisible context object. The existing10,240-byte macro budget can drop the whole object,
never retain a number while discarding its basis. No reconstructed history list is included.

**Consumer quality gate:** distinguish a current-state estimate from a future-event forecast in both
prompt evidence and visible wording. ADB-R2/R3/R11/R13 continue to govern budget, same-tape dependence,
staleness and zero signal authority. Respect ADB-R16's existing Synapse reader registrations; a new
literal source read needs its existing-owner registration, not a duplicate registry. This closure
narrows the proposed build packet; interface ratification, writer/collision census and browser proof
remain owed. W1 is still SPEC_ONLY and does not authorize a source change on its own.
