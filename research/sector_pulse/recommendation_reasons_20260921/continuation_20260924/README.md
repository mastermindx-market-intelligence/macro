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

- 110 tests passed;
- fresh-initial, continuation/no-initial-entry, final HOLD, and missing-entry display
  behavior are pinned;
- existing stock-entry missingness and zero-qualified-member behavior remain covered.

A broader local suite request was platform-refused before dispatch and was not retried
through another route. Hosted CI on the new source head remains the full repository gate.

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

## Acceptance boundary

This repair closes only the bounded integration finding. It does not:

- claim the historical China witness is a current recommendation;
- grant continuation entry to every accumulate theme;
- make every constituent buyable;
- change the existing action-card / Prophet / theme-ranking policy;
- prove forward alpha or portfolio outcomes;
- replace normal independent re-review, hosted CI, merge, publication or served-path proof.
