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


## Re-verification ledger (seat-maintained, 2026-09-24 08:00–08:45Z)

| Round | Exact head | Verdict | Blockers | Seat action |
|---|---|---|---|---|
| #1 | carrier `a753abdf` (lane #7895 `576dd26d`) | REJECT | B1–B3 + pin list (table above) | repair lane `ene_w1_t9_repair2` (mb, glm-5.3) → #7895 `a73215d4`, cherry-picked as `9d1f2530`; sparse markers re-applied `e4c37cff` |
| #2 | `e4c37cff` | REJECT | shape law compared only keys present on both sides (a dropped key passed silently); pin list 17/23; `frozen_at_main` was the lane's merge commit, not on `origin/main` | seat fix `51da7235`: per-field nullable law over the full field list (`"missing"` is a recorded shape); 25-name pin list; regeneration CLI requires HEAD == sha, sha ancestor of `origin/main`, full checkout; four private-only canaries stored in the baseline |
| #3 | `51da7235` | REJECT | `divergence_board` frozen `"null"` but absent from `NULLABLE_SHAPE_FIELDS` — nuclear has never been flagged in `data/foresight/divergence_log.jsonl`, so its first hidden-opportunity flag would red the freeze | seat fix `7111b4ae`: `divergence_board` nullable + explicit null→object case; README regeneration steps (detach to `origin/main`, opt into `data`/`site`, pass `$(git rev-parse HEAD)`); self-referential `public_pages` assert dropped; membership tests assert their own basket |
| #4 (delta) | `7111b4ae` | ACCEPT_WITH_NITS | none | nits applied in the final carrier commit: unused `_assert_section_unchanged` removed; the canary-tuple assert kept only in the public-pages test |

Proof at each seat head: local sparse tree 8 passed / 6 skipped (the six `data`/`site` tests skip by `scripts.worktree_sparse.missing_dirs`); full-checkout run on mb (venv pytest) 14 passed at `51da7235`, re-run at the final head recorded in the carrier checkpoint §8; CI-pack `unrun-subsector-themes` `-k` selection 16/16 and `scripts/check_contract_delta.py --base origin/main` 0 introduced at `a753abdf` and `51da7235`.

Reviewer GAPS carried, not waived: the six `data`/`site` tests are proven only by the full-checkout run (never by the sparse seat tree); the README regeneration steps were read, not executed (read-only review).
