---
key: PROPHET-US-D02-EPISODE-ADMISSION-GATED
question: >
  May the first extra episode anchor species, `entry_radar_expert_fire`, be admitted now, and
  if not, what exact conditions must hold first? (R6 decision D02, carried by ruling B02-01)
answer: >
  D02 is resolved in principle but admission is GATED. The first extra species is
  `entry_radar_expert_fire`, anchored ONLY on Radar-owned fields already in
  `mastermind.entry_event.v1` — the detector’s own price/time geometry, never a later
  extremum — with its own `intake_class`, a dataset-registry `version` bump, and no new DAG
  step because B1 remains the sole writer. It may be admitted only when BOTH hold:
  (a) `WS:LIVE-ENTRY-RADAR` has frozen and validated the forward-projection contract so the
  B1-consumed relation key is the exact immutable `event_id`, with the legacy
  `ticker|detector_id|decision_session` fallback refused rather than tolerated; and
  (b) a committed `forward.parquet` exists. Until both conditions hold, no code for step 2
  is written. Separately, B02 step 1 closes the anchor vocabulary to
  `turn_watch_reset_low` now and leaves every committed row unchanged.
rationale: >
  The census observed that only one anchor species opens episodes today, every other source
  is attach-only, and the vocabulary is not yet closed, so a silently widened species could be
  admitted without refusal. The best-evidenced extra species is a Radar expert fire, but its
  current relation key can fall back to a ticker/date surrogate and `data/entry_radar/forward.parquet`
  has never been committed. That surrogate is exactly the D02-forbidden shortcut, so closing
  the vocabulary can proceed while the stronger species waits behind both validated identity
  and committed forward evidence.
alternatives:
  - option: Admit `entry_radar_expert_fire` with the existing fallback relation key.
    why_not: The ticker/date surrogate is the D02-forbidden shortcut; B1 must consume the exact immutable `event_id`.
  - option: Anchor the fire on a later extremum after the episode opens.
    why_not: The anchor must use only Radar-owned detector price/time geometry already present in `mastermind.entry_event.v1`.
  - option: Leave `canonical_anchor` open to any anchor kind while D02 waits.
    why_not: A silently widened species would be admitted without refusal; the vocabulary must close with a fail-closed refusal.
  - option: Introduce a second definition era or a second episode writer for the new species.
    why_not: A two-era ledger would make `all_candidates.json` unreadable by the sole canonical reader, and B1 stays the sole writer with no new DAG step.
evidence:
  - research/prophet_v4/r6_program/wave1/B02_EPISODE_REGISTRY_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-B02-01_2026-09-23.md
  - Macro PR 7826, carrying the wave-1 census and ruling
affects:
  - WS:PROPHET-US-V4-RECOVERY
  - WS:LIVE-ENTRY-RADAR
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision D02 in principle through ruling B02-01. Build unit
`pu_w1_b02_anchor_vocab` performs step 1: close `ANCHOR_KINDS` to
`turn_watch_reset_low`, enforce a fail-closed refusal through a new closed
`SUPPRESSION_REASONS` member, and flip the six registry rows from PROPOSED to ACCEPTED
with the 2026-08-28 acceptance citation.

Unresolved: D02 admission remains GATED until BOTH the frozen and validated immutable
`event_id` forward-projection contract and a committed `data/entry_radar/forward.parquet`
exist. Until then, no step-2 code is written. B02-a and B02-b remain carried open items.

## What this decision does not do

It does not admit the extra species, change episode ids or `DEFAULT_DEFINITION_ERA`, add a
new DAG step, or authorize a second writer. It does not unblock B03/B04 by implying D02
admission: those proceed on the closed vocabulary alone, with B04 also waiting on its own
D03/D07 pre-registration.
