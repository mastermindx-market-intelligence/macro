---
workstream: WS:REGIME-BRIEFING-CONTEXT
session: claude/hmm-briefing-context-20260909
model: sol
ended_because: ci_handoff
mission: Deliver useful dated regime evidence through the existing briefing reader and shared body.
state_before: >
  W0 was reviewed but waiting on hosted code packs. W1's earlier world-state route missed
  an existing direct reader that discarded asof/basis while prescribing future-direction prose.
changed:
  - path: engine/master_brain.py
    what: Dated context, existing-source freshness, nonforecast prompt law, deterministic bilingual saved note.
  - path: templates/_aibrief_body.html.j2
    what: Escaped macro-only note and keyboard-focusable existing Lens detail trigger.
  - path: .github/ci/legacy-jobs.yml
    what: Move the existing regime-label suite from data health to its existing code-gated brain owner.
verified:
  - claim: Focused reader, producer, and renderer tests pass.
    command: python3 -B -m pytest tests/test_master_brain.py tests/test_regime_label_honesty.py -q
    result: 85 passed after bounded source-basis, fit-cutoff, focusability and code-gate corrections.
  - claim: The actual amended existing code-job pytest step passes with its committed data dependency.
    command: Execute unrun-brain-desks command naming test_master_brain and test_regime_label_honesty.
    result: 247 passed; one omitted immutable market_drivers_log.parquet fixture was materialized unchanged.
  - claim: Real committed input reaches the saved note and full template in isolation.
    command: research/artifacts/regime_briefing_context_20260909/reproduce_local_consumer.py
    result: Model and translation responses are fixtures; thesis append intercepted; not production adoption.
unverified:
  - claim: Exact-candidate independent review and concluded hosted checks.
    what_would_verify: Immutable reviewer return plus real final-head code-pack conclusions and current-base proof.
  - claim: Natural production briefing adoption and model-output quality.
    what_would_verify: Accepted normal producer run, saved source/context/brief, then real browser inspection.
  - claim: Better forecasts or portfolio outcomes.
    what_would_verify: Separate preregistered outcome evaluation; descriptive usefulness is not trading authority.
discoveries: ["DSC:REGIME-BRIEF-READER-ALREADY-EXISTS"]
unresolved:
  - W0 PR7015 remains held independently; its HMM suite owner was queued in pack10 at recovery.
  - Local browser captures use existing saved prose as a fixture, not newly generated model wording.
next_actions:
  - Complete exact-source review and normal Draft/HOLD publication for this same W1 branch.
  - Conclude applicable code and source-compatibility checks without bypass or unrelated repairs.
  - After accepted release, prove normal production adoption through the existing brief surface.
do_not_redo:
  - No duplicate probability route through world_state/brief_context for this existing direct consumer.
  - No new model, ledger, clock, control plane, ranking, sizing, or portfolio rule.
  - No alteration or reissuance of W0 history and no manual production generation.
danger_areas:
  - run(persist=False) still appends the macro thesis ledger; isolate and intercept that effect in tests.
  - A source date must not inherit the brief build date; missing model metadata stays unknown.
  - Code-gated regression coverage differs from post-nightly data-health coverage.
  - The shared regime prompt law changes for all three lenses; only macro receives the new saved note.
---
