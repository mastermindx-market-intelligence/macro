---
key: INTL-GS-GB1-GRAPH-BOUNDARY-CHIP
question: >
  How does the §14 "Graph boundary" concept (row 4: fixed 11-market graph vs qualified candidates vs
  structural research) render in the W2B market dossier when no admitted edge producer exists?
answer: >
  One gs_chip in the W2B dossier Typed-edges card (Q4 · Q5) band-head row, sourced from engine LABELS
  (structural_graph_member → neutral, qualified_candidate → warn-dashed, structural_research →
  muted-dashed) and carrying data-graph-boundary; exactly one footnote = engine reasons via reason_copy
  plus the first interpretation limit, in EN and ZH. Production passes edges=[] (no admitted edge
  producer) and stamps edge_basis: "no_admitted_edge_set", stated in the footnote. On aggregates/shape
  errors the chip is omitted and a graph_boundary_unavailable note is emitted instead. Follow-up lane
  intl-gs-w2b-gb1-r1 also lands R-14 (sha256 pin of _w2b_css_region() bytes) and R-11 B8 (AST scan over
  function defaults).
rationale: >
  The graph-boundary fact is structural and proven (engine/intl_global_graph_boundary.py landed via
  #10286), so it is displayable without any edge producer; but the frozen rights matrix has no
  emission-permitted candidate source, so no admitted edge set may be implied. A single chip plus one
  reason footnote keeps the claim exactly as strong as the evidence — membership vocabulary from the
  engine, an explicit no_admitted_edge_set basis stamp, and fail-safe omission when the data shape is
  wrong — never a drawn edge, a rank or an implied transmission path.
alternatives:
  - option: Render nothing until an admitted edge producer exists.
    why_not: >
      The membership distinction (graph member vs qualified candidate vs structural research) is proven
      and §14 row 4 requires it to be legible; withholding it hides a settled structural fact, it does
      not protect one.
  - option: Compute and draw candidate edges from available sources.
    why_not: >
      No emission-permitted candidate source exists in the frozen rights matrix; drawing edges would
      imply an admitted edge set that does not exist.
evidence:
  - "Seat ruling 2026-10-31 (provenance: this records PR, lane/intl-gs-rec7-r2; continuation handoff section \"Seat ruling 2026-10-31 DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP\")"
  - "engine/intl_global_graph_boundary.py on main via #10286 (head 92a211e1d4e07d0d1e65d76f3044f1ca210968d5 → d444ae6713b008aede6197f01989d44fa5122e4c, 2026-10-31T10:45:49Z; gh pr view 10286 --json state,mergeCommit,mergedAt → MERGED)"
  - "W2B dossier surface on main via #10278 (head c2a3de654b843924dbc95f7a5b0c8b47382d4d69 → a99b539578003e7dfd32394dc1e839cba7f8bb0a, 2026-10-31T15:05:04Z; gh pr view 10278 → MERGED)"
  - "W5 census §14 row 4 (research/INTL_GLOBAL_SURVEILLANCE_W5_CENSUS_2026-10-31.md) — PARTIAL at census base 6e721225, closed-moved by #10286"
affects:
  - "WS:INTL-GLOBAL-SURVEILLANCE"
  - "templates/intl_workspace/* (W2B dossier Typed-edges card)"
  - "engine/intl_global_graph_boundary.py"
  - "follow-up lane intl-gs-w2b-gb1-r1 (R-14 sha256 pin of _w2b_css_region() bytes; R-11 B8 AST scan over function defaults)"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-31
review_by: 2026-11-30
---

## Scope

Binds the rendering contract for the §14 "Graph boundary" label on the W2B dossier surface only. It does
not create an edge producer, does not add any rights-matrix row, and does not change the frozen
11-market links graph or 14-ETF VAR.

## Options considered

One gs_chip from engine LABELS with a reason footnote and an explicit no_admitted_edge_set basis stamp
(ruled); render nothing until an edge producer exists (rejected); draw candidate edges from available
sources (rejected — no emission-permitted candidate source).

## Consequences

- The dossier Typed-edges band-head carries at most one graph-boundary chip with data-graph-boundary;
  its vocabulary and reasons come from the engine LABELS/reason_copy, EN/ZH, plus the first
  interpretation limit.
- Production states edge_basis "no_admitted_edge_set" in the footnote while edges=[] holds; the chip
  never implies a drawn edge.
- Aggregates/shape errors omit the chip and emit graph_boundary_unavailable (fail-safe).
- The gb1 follow-up lane also lands the R-14 sha256 pin of _w2b_css_region() bytes and the R-11 B8 AST
  scan over function defaults.

## Provenance

The seat ruling of 2026-10-31, recorded in this records PR (lane/intl-gs-rec7-r2) and mirrored in the
continuation handoff section "Seat ruling 2026-10-31 DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP".
