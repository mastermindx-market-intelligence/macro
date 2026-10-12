---
key: PROPHET-US-C-01-EARNINGS-SEQUENCING
question: >
  What earnings/D5 dossier work is ready now, what gates production admission, and how do
  B14 and B08 sequence? (R6 decision C-01)
answer: >
  One real, source-backed dossier is deliverable today — AAPL FY2026 Q3
  (`evt_cik0000320193_2026q3_results`) — as display/reference work only. D5 carries zero
  authority by construction (`ALL_FALSE_AUTHORITY`, empty `fusion_bindings`), so a delivered
  dossier cannot move rank, gate, size or `ENTRY_OPEN` until an explicit Conditional Fusion
  binding exists. Production admission is blocked upstream by B1 episode population: A11 is
  BUILT_NOT_PROVEN and clears only on a natural scheduled `daily.yml` acceptance, never by
  dispatch. Sequencing is B14, the dossier surface, before B08, production admission. The
  ruling commissions `C-DOC` for the named Prophet-owned truth repairs and `C-UNITS` for
  revenue-unit normalization or refusal with a RED→GREEN producer/fixture test.
rationale: >
  The census admitted only the one reachable issuer and found the remaining ranked blockers
  separable into documentation truth, a real unit-comparability defect, contract questions,
  latent corrections, and the external B1 clock. Keeping the first dossier display-tier
  respects D5’s zero-authority construction, while B14-before-B08 gives production admission
  a bounded surface only after the upstream population is naturally proven.
alternatives:
  - option: Dispatch `daily.yml` to produce the missing B1 population.
    why_not: Acceptance depends on the natural scheduled run and its own receipt; dispatch is explicitly not to be used.
  - option: Broaden the allowlist beyond the one real issuer now.
    why_not: Allowlist breadth is an EIO-owned question and is routed as a finding, not built by this ruling.
  - option: Let the AAPL dossier affect ranking, gating, sizing or `ENTRY_OPEN`.
    why_not: D5 has zero authority until an explicit Conditional Fusion binding exists; the current unit is display/reference only.
  - option: Build C-05 before the D5 contract owner rules the binding revision clock.
    why_not: Clock degradation and adapter strictness divergence are held for that contract ruling, not implemented as a premature build.
evidence:
  - research/prophet_v4/r6_program/wave0/C_EARNINGS_D5_READINESS_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-C-01_2026-09-23.md
  - Macro PR 7811 (merged 5d8c71c5), carrying the census and ruling after lane PR 7818 was closed as superseded
affects:
  - WS:PROPHET-US-V4-RECOVERY
  - WS:EARNINGS-INTELLIGENCE-OS
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision C-01 for earnings/D5 readiness and B08/B14 sequencing. The AAPL
reference dossier is the first bounded unit from the committed fixture path.

Unresolved: B08 production admission waits on blocker 1’s natural nightly external clock.
C-05 remains held for the D5 contract owner, and C-06 remains latent until a real correction
chain exists.

## What this decision does not do

It does not grant D5 authority, move rank/gate/size, or make `ENTRY_OPEN` reachable. It does
not dispatch `daily.yml`, synthesize a correction chain, broaden the allowlist, or touch
EIO-owned `engine/company_intelligence/**`.
