R-T02R4-01: rounds 1-3 semantics are ACCEPTED at 4623f6e7 — this round is the single ruled change; no refactor, no renames, no taxonomy reordering.
R-T02R4-02 (= R-T02R3-06, restated at the seam): qualification is a property of the CAPTURE returned by `collect_shortage_sweep`; a downstream demotion in `save_shortage_observation` is defence in depth, never the primary rule. `NO_SOURCE_GENERATION` is set in the sweep whenever the page carried no non-empty `meta.last_updated` string and no other failure code fired first.
R-T02R4-03: the new generation-suite test asserts the truthful values (`False`, the exact code, `None`) — never `is not None` alone; no real molecule names.
R-T02R4-04: commit and push after each step; keep every exec under 10 minutes.
