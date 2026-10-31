---
workstream: WS:PROPHET-US-ENTRY-TIMING
session: sol/prophet-us-v4-entry-timing-masterplan-20261031
model: sol
ended_because: ci_handoff
mission: >-
  Prepare the existing Prophet US V4 and Entry Timing program for autonomous Fable-led
  delivery with Opus suborchestrators and external Fabric labor.
state_before: >-
  W0 is recorded done, W1 in progress, W2 to do. V4 recovery is on #10174, shared
  product integration is on #6817, US program direction on #6805.
changed:
  - path: research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md
    what: Source-bound completion brief and reusable entry, science and settlement packets.
  - path: research/prophet_v4/PROPHET_US_ENTRY_TIMING_SOURCE_CENSUS_2026-10-31.md
    what: Existing waves, complete R6 B/Q/D index and dated PR census.
  - path: agentos/workstreams/WS-PROPHET-US-ENTRY-TIMING.md
    what: Link the plan and qualify the W1 next action without changing any wave status.
verified:
  - claim: The original August 11 22:30Z bake never ran.
    command: Inspect data/prophet/backfill_disclosures.json and scripts/backfill_prophet_outage_20260811.py at 1c85878983323f9ab38fff56a15771166d0f8aeb.
    result: Later reconstruction is labeled. August 12 and 13 have separate source origination receipts.
  - claim: Merged capture source still has an unbound Data OS alias seam.
    command: Inspect resolve_alias_table, the B4 sources adapter and lib/dataos/identity.py at the same main SHA.
    result: Capture returns None. The owner supports a dated forward/reverse provider. Historical knowledge requires its own proof.
  - claim: The latest recovery draft retains all 30 waves.
    command: Count structured wave statuses on recovery head 29cfb98b15d2f1a7d39489024c69e76fc46b6ff0.
    result: Five done, seven in progress and eighteen to do.
unverified:
  - claim: Held-out W2 entry-timing improvement at acceptable false-positive cost.
    what_would_verify: An eligible preregistered same-population comparison with honest coverage, costs and maturity.
  - claim: Current production A2 settlement and user-visible US B4 path.
    what_would_verify: Full issuer and protected-reader bundle and a same-generation signed-in journey through the serving release.
unresolved:
  - The existing issuer preflight remains on its original root. Read it before overlapping work.
  - The current accepted GMI ThemeState and protected-reader identity remain unproven.
  - The B-17 frozen population has no fully covered historical observation window in the available input.
next_actions:
  - Adjudicate W1 from the missed-bake disclosure and later natural-run controls, retaining the historic outage.
  - Prove one natural B1-to-B4 identity and clock path on the existing source owners and retain a refusal counterexample.
  - Have Fable choose the highest-value independent slice and carry the original B/Q/D and recovery gates through release.
do_not_redo:
  - Preserve the original 30 wave identities, registered B4 experiment and exact unchanged A2 source reviews.
  - Preserve the August 14 replay and the earned B1 episode acceptance.
danger_areas:
  - A CI result or origination receipt cannot establish customer exposure, a fill or production settlement.
  - A study refusal must remain distinguishable from missing market data.
prs: [10174, 10176, 10180, 10202, 10209]
---

# Entry Timing continuation

The planning role is assumed under the current commission. Live source carriers, independent reviews
and release owners remain attached to their existing operations. The current brief is
[Prophet US V4 and Entry Timing](../../research/prophet_v4/PROPHET_US_ENTRY_TIMING_COMPLETION_BRIEF_2026-10-31.md) and its
[source census](../../research/prophet_v4/PROPHET_US_ENTRY_TIMING_SOURCE_CENSUS_2026-10-31.md) is scoped to the US program and its shared dependencies.
The V4 records and broader R7 workstreams retain their own handoffs.
