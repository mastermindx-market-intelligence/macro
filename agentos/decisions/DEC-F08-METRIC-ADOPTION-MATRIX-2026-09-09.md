---
key: F08-METRIC-ADOPTION-MATRIX-2026-09-09
type: decision
status: active
workstream: MARKET-OS
question: >
  The F08 architecture freeze names a metric adoption matrix as a V2 entry
  gate: metric to owning module to definition, benchmark, horizon,
  annualization and version, or the literal token NO-OWNER. Which metrics of
  the shipped Terminal V2 holdings readout have an owner, and which stay
  NO-OWNER so a builder may not fork or invent a formula?
answer: >
  Ratify the matrix at research/MARKET_ONTOLOGY_F08_METRIC_ADOPTION_MATRIX_2026-09-09.md.
  Concentration, industry weight, company-size weight and liquidity thickness
  are owned by terminal/lib/portfolioRisk.ts as shipped by terminal#524.
  Sharpe, Sortino and beta are NO-OWNER. engine/portfolio.py stays HOUSE-only.
  Ceiling decision_support_only. The Portfolio Constructor remains
  research-proposal-only. The freeze document itself is not rewritten.
rationale: >
  Freeze §1 says nothing is frozen yet and a builder may neither fork nor
  invent a formula before the matrix is ratified. terminal#524 shipped a
  per-user concentration, factor and liquidity readout over A1A holdings; it
  did not ship Sharpe, Sortino or beta over a user's own positions, which is
  why MO-DELTA-014 stays PARTIAL on the base branch and remains an open row.
  Macro contains no terminal/ tree, so ownership is pinned to the
  Terminal commit recorded in the packet manifest rather than re-read at test
  time. Naming NO-OWNER for the three missing metrics is the safety margin:
  when in doubt, no owner. Inventing an owner during ratification would be
  the same freeze violation the gate exists to stop.
alternatives:
  - option: "Invent owners for Sharpe, Sortino and beta, then rewrite MO-DELTA-014's PARTIAL cell to BUILT_NOT_PROVEN."
    why_not: "terminal#524 does not compute those three over a user's holdings. The freeze forbids forking or inventing a formula. Rewriting MO-DELTA-014's PARTIAL cell on that basis would contradict the base branch and license wrong formulas downstream."
  - option: "Leave the matrix unratified and let each V2 builder pick a formula."
    why_not: "The freeze names the matrix as a V2 entry gate. An unratified gate is not a licence to invent; it is a stop. Packet 6 exists to ratify the gate, not to waive it."
  - option: "Rewrite the freeze document in place to list the owners."
    why_not: "The freeze is a dated architecture record. An amendment in a new dated file keeps the freeze text byte-stable and is the shape the packet spec requires."
evidence:
  - "research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md §1 owner table: risk formula owners UNRESOLVED; engine/portfolio.py stays HOUSE-only; matrix is a V2 entry gate."
  - "macro#7003 / B-REC-B5-1: MO-PAID-036 BUILT_NOT_PROVEN against terminal#524 merge efcd98aa; MO-DELTA-014 stays PARTIAL because Sharpe, Sortino and beta are computed nowhere for a user's own positions."
  - "git ls-tree -r --name-only origin/main | grep -c '^terminal/' returns 0 — macro has no terminal/ tree."
  - "tests/fixtures/b_rec_b5_x_consolidated_manifest.json terminal_pin commit db69d072, pr 524, merge efcd98aa."
affects:
  - "F08 V2 portfolio monitoring read (MO-PAID-036, MO-DELTA-014)"
  - "research/MARKET_ONTOLOGY_F08_METRIC_ADOPTION_MATRIX_2026-09-09.md"
  - "WS:MARKET-OS"
confidence: high
reversibility: costly
decided_by: "Meta-CEO B successor seat, harness session d640f3ef, under DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"
decided_at: 2026-09-09
review_by: 2026-12-09
related:
  - "DEC:F08-PORTFOLIO-CONSTRUCTOR-IS-RESEARCH-ONLY-2026-09-06"
  - "DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"
  - "WS:MARKET-OS"
---

The F08 §1 metric adoption matrix is ratified as
`research/MARKET_ONTOLOGY_F08_METRIC_ADOPTION_MATRIX_2026-09-09.md`. Four
shipped Terminal V2 readouts have an owner; Sharpe, Sortino and beta do not.
The freeze text is untouched. Reversing a `NO-OWNER` row to an invented owner
needs its own ruling and is not granted here.
