# Opus READ_ONLY review — Energy W1 T9 nuclear non-regression freeze

Artifact: lane PR #7895 head `576dd26d` as integrated on carrier #7881 at `a753abdf` (test module, baseline fixture, README; CI wiring not read by the reviewer). Reviewer: Opus `reviewer`, MODE READ_ONLY, 2026-09-24 ~08:15–08:40Z. Local run: 1 passed / 6 skipped (sparse tree). Verdict: **REJECT** — 3 BLOCKING, 6 NIT. Seat disposition: all accepted; REQUEST_REPAIR #2 (`ene_w1_t9_repair2`, mb) posted on #7895.

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| B1 | `foresight` frozen but nightly-computed (`engine/neuralweb/thematic_state.py:328-338` copies from `site/basketdata/foresight_cascade.json`; 9/18 themes changed it across the last 29 regime updates; Nuclear unchanged 29/29 only by sitting in a capped text tier) | volatility census of 29 `theme_state.json` revisions | shape-only |
| B2 | `narrative` frozen but computed from `narrative_emergence.json` (null today only because `_read_narrative_tickers` expects list `legs`; artifact carries dict `legs`) | `thematic_state.py:243-249, 382-395` | shape-only |
| B3 | shape check fails when `radar`/`basket_intel` come back null (`thematic_state.py:430-431` returns `… or None`; 3 themes null at head) | fixture pins "array" | nullable shape law |
| — | pin test omits foresight/narrative/stance/story/stage_*/falsifier_label/leadership_context/entry_context | test:216-232 | full 23-name list |
| N1–N6 | reserved joins pinned null; `lane_rank` shape "tuple"; self-referential sha asserts + code-only canaries; curated `subsector_keys` unfrozen; regeneration CLI unchecked; generic canary "realized price" | — | fixed in the same pass |

Passed: semantic 12 disjointness (moving CCJ/LEU into nuclear_power fails both checks); `frozen_at_main` is a real main ancestor; hashing consistent; sparse markers via `missing_dirs`; `__main__` inert under pytest. Not checked by the reviewer: privacy canaries against current pages (item 5), CI wiring (item 6) — the seat's local wiring checks (CI-pack 16/16, contract-delta 0 introduced) cover item 6.
