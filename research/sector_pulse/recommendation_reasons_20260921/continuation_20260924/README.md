# Continuation-vs-initial-entry detail repair — 2026-09-24

## Why this repair exists

Independent review **5307123386** on PR #7669 / head
`6942b2b62bad2dfc9d3b50eb7042e0a126b708c4` reproduced a cross-component contradiction:

- the accepted China action-card path can retain a dominant / accumulate theme in
  `buy_now` with `entry_route=continuation`;
- the shared detail-page JavaScript looked only at the initial
  `textures.clean_entry.flag`;
- when that flag was false, the detail hero replaced the native recommendation with
  **WAIT FOR ENTRY**, even though the action card's final current decision still admitted
  the continuation route.

The review used the immutable `cn_pharma_cxo` witness and explicitly prohibited a
second JavaScript continuation classifier or any widening of stock-entry authority.

## Local-state reconciliation before repair

Review also found two unpublished dirty files. No process held this exact worktree when
reconciled. Their exact patch is preserved in PR #7669 comment **5824203418** with
SHA-256:

`638c1d0caa4bd8d53f3c7e76902f6b814e79fd21cbf1cae4dcf1cb6fe6785319`

That partial re-projected recommendation explanation text but did not solve the
continuation-vs-WAIT contradiction. It was restored to exact HEAD before this repair.

## Repair

The detail page now keeps three concepts separate:

1. **Theme rating** — the existing producer recommendation (`ENTER / ACCUMULATE / HOLD / ...`).
2. **Initial entry context** — when the initial clean-entry texture is not confirmed,
   the page says so underneath the rating instead of replacing the rating with a contrary
   blanket wait instruction.
3. **Individual stock entry checks** — the existing stock-entry owner remains authoritative
   for constituent qualification and reasons.

No continuation classifier was added to the detail JavaScript. No score, rank, theme
recommendation, clean-entry function, stock-entry eligibility, sizing, alert or trade
authority changed.

## Discriminating tests

`red.txt` is the actual pre-fix failure transcript with trailing whitespace normalized for Git hygiene. A dominant/accumulate theme with
`clean_entry.flag=false` rendered **WAIT FOR ENTRY** instead of `ACCUMULATE`.

`green.txt` records the affected consumer suites after repair:

- before current-main integration, the two load-bearing recommendation-reason and
  basket-entry suites passed **111 tests** and the broader nine-suite affected surface
  passed **252 tests**;
- after integrating protected main `72038badf7e309dfbdd00120fd0f0e523623fe75`,
  the load-bearing suites pass **111 tests** and the candidate-relevant affected surface
  passes **238 tests**;
- fresh-initial, continuation/no-initial-entry, final HOLD, and missing-entry display
  behavior are pinned;
- existing stock-entry missingness and zero-qualified-member behavior remain covered.

The wider product-chrome suite has one exact protected-main failure in the newly added
`finance_intelligence.html.j2`: the page takes the shared product header but omits
`theme.js`. The integrated candidate carries the exact main blob
`782cf7a1cc304da5cce5b120f1de3746a6637e45`, and an isolated archive of protected main
fails the same test. This separate defect is neither repaired nor waived here.
No full-repository local run is claimed; hosted exact-head CI remains the repository gate.

## Exact cross-component continuation contract

`cross_component_proof.py` closes the review's action-card-to-detail identity gap with
immutable source and input rather than a synthetic continuation flag:

- accepted China action-card source: PR #7567 head
  `6e0beeec8f720333dd72ab47a9e7c39fed6238a1`,
  `engine/china_act_now.py` SHA-256
  `fcb9c8996294e1f9cf0fe5e6835c27785ef4006cf43b9aba58cebff0b05cc8f7`;
- frozen input: commit `88a3f1cfd18f391d2802e9086dc00f6fe5545607`,
  `site/chinabasketdata/baskets.json` SHA-256
  `69c46ef1ec0c60f450dfe6c443d2d01c70da81a91f34c8763c04f747edbb4040`;
- frozen qualification clock: `2026-09-23T05:00:00Z`;
- actual producer result for `cn_pharma_cxo`: `buy_now`,
  `entry_route=continuation`, `theme_decision.status=CURRENT`, final
  `dominant / accumulate`;
- the producer's only raw source read is `wait_pullback`; no bottoming-watch
  observation is present, proving the continuation route does not require another bottom;
- the same immutable input's compiled detail payload is September 22,
  `dominant / accumulate`, with `clean_entry=false`;
- rendering that exact payload through the repaired template preserves ACCUMULATE,
  prints initial-entry context separately and never emits a blanket WAIT instruction.

`cross-component-receipt.json` binds those identities and eight real Chromium cells
(dark/light × EN/ZH × 1440/390). All return HTTP 200, preserve the native rating,
show the separate initial-entry context, and have zero page errors, request failures or
page-wide overflow.

The frozen input predates the later per-stock entry-check payload. The separate
32-state current-page control matrix therefore owns the zero-qualified-stock-table,
fresh-initial, final-demoted and stale/missing-entry controls. The two receipts are
complementary; neither invents stock permission or claims production/current-market proof.

## Generated-page preservation

`page-refresh-proof.json` records the 121 regenerated regional basket pages:

- **1,917 member rows**;
- **1,878 assessed rows**;
- status / buys / uncovered unchanged;
- every non-explanation DETAIL field unchanged;
- original observation dates and generation timestamps retained;
- no collection, rescoring or new quote input.

The real compiled `cn_pharma_cxo` page at repair time is dominant / accumulate,
`clean_entry=false`, with **0 qualified / 14 waiting** constituent checks. It now
contains the native theme rating and the initial-entry context separately, with no
`WAIT FOR ENTRY` literal.

## Browser evidence

`browser-receipt.json` and `browser/` contain **32** local Chromium captures:

- continuation / zero-qualified-member;
- fresh initial entry;
- final-demoted HOLD;
- stale + entry-information-unavailable;
- dark and light;
- English and Chinese;
- 1440 and 390 widths.

All 32 controls:

- show the native theme rating;
- contain no blanket WAIT instruction on the detail hero;
- preserve the stock-entry table;
- show the initial-entry context only when applicable;
- show the existing stale-data banner for dated controls;
- have zero observed page exceptions and no page-wide horizontal overflow.

These are local compiled-source proofs, not authenticated production acceptance.

## Current protected-main integration

The candidate pre-merge head
`a7362d01e3b7609c7c7b59c6ad61ba0cccbf6b8a` was integrated with protected main
`72038badf7e309dfbdd00120fd0f0e523623fe75` on the original PR #7669 carrier.
Source files auto-merged without semantic conflict. The only conflicts were 84 generated
basket-detail pages.

`current_base_integration.py` resolves those generated artifacts through the incumbent
renderer and act-now owner:

- 84 conflicted pages retain exact protected-main embedded inputs;
- 37 non-conflicted pages retain exact candidate embedded inputs;
- all 121 pages render through the auto-merged canonical template;
- **1,858 member rows / 1,827 assessed rows** are preserved from the selected inputs;
- status, buys, uncovered, every non-explanation DETAIL field, observation dates and
  generation stamps remain unchanged;
- the incumbent owner materializes **1,858 stock-entry checks** without adding a new
  classifier, state store or publisher.

`current-base-integration-proof.json` binds every input ref/hash and every generated-page
hash. `current-base-verification.txt` records the focused tests, the 40 browser cells and
the exact inherited current-main failure. The exact-source eight-cell continuation proof
and the 32 control cells were recaptured after integration; all have zero page errors,
zero request failures and no page-wide overflow.

## Acceptance boundary

This repair closes only the bounded integration finding. It does not:

- claim the historical China witness is a current recommendation;
- grant continuation entry to every accumulate theme;
- make every constituent buyable;
- change the existing action-card / Prophet / theme-ranking policy;
- prove forward alpha or portfolio outcomes;
- replace normal independent re-review, hosted CI, merge, publication or served-path proof.
