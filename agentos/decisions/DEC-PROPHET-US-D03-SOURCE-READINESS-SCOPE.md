---
key: PROPHET-US-D03-SOURCE-READINESS-SCOPE
question: >
  Which Cycle and issuer-event source domains are ready enough to admit a Prophet US
  pilot, and by what gate is "ready" decided? (R6 decision D03, ruling R6-D03-01 v2)
answer: >
  A five-rule readiness gate is ratified verbatim and NO Cycle domain is admitted for a
  pilot on the evidence measured: rule 1 (source-dated vintage depth), rule 2 (membership
  first-date before the study window), rule 3 (delistings and a failed universe present),
  rule 4 (macro-series break knowledge), rule 5 (rights and publication posture). The
  machinery domain (a) is the primary candidate and (b)/(c) are alternatives; all three
  fail rules 1–3 on UNKNOWN vintage depth and absent issuer mapping at the time of ruling.
  B16 is split: B16-a is a read-only, allowlisted closure matrix run that measures the
  five rules without opening any outcome artifact; B16-b is the gated admission that may
  only follow a measured matrix. History is admissible only where a source-dated
  point-in-time row exists; UNKNOWN branches stay prospective-only.
rationale: >
  The two wave-2 censuses (issuer events, Cycle sources) showed that every plausible
  domain rested on unreceipted vintage depth and on membership dates measured at
  2026-07-05 / 2026-08-13, so any pilot admitted now would be fitted on backfilled
  membership and current-only event discovery — the D03 forbidden shortcut. Ratifying the
  gate first, then measuring it read-only, keeps the search open (a kill closes the
  construction tested, not the search space) while refusing a return-selected domain.
alternatives:
  - option: Admit the machinery domain on plausible vintage depth and fix membership later.
    why_not: Rules 2–3 fail on measured first-membership dates; a later fix would backdate membership, which the gate forbids.
  - option: Select the pilot domain by inspecting realised Cycle returns per domain.
    why_not: Outcome-selected domain choice is the forbidden shortcut; B16-a is allowlisted read-only and never opens ledgers, scoreboards or returns.
  - option: Skip the matrix and let B16-b admit on the census prose alone.
    why_not: The census recorded UNKNOWN where depth was not measured; admission requires a measured matrix with receipts per rule.
evidence:
  - research/prophet_v4/r6_program/rulings/R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md
  - research/prophet_v4/r6_program/reviews/RV_D03_RULING_DRAFT_OPUS_2026-09-23.md
  - research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md
  - Macro PRs 7836, 7837 (censuses) and 7841 (ruling v2 after the Opus red-team)
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision D03 in scope: the readiness gate is law for every Cycle and
issuer-event source claim in the Prophet US program, and B16 proceeds only as the split
B16-a (measure) → B16-b (admit). The Opus read-only red-team of the draft (1 BLOCKER /
7 MAJOR / 10 minor) was folded before ratification; v2 is the binding text.

## What this decision does not do

It does not admit any pilot, does not compute or cite a Cycle strategy return, does not
backdate membership, events, GICS or issuer identity, and does not ask the Chairman the
paid-provider question — that question is askable only with a measured matrix attached.
D03 CLOSURE is a separate act recorded by `DEC:PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA`.
