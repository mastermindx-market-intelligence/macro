# R8 — Context help no longer mutates its host

Mission remains incomplete and production remains unchanged. This wave removes a concrete integration defect in the shared Market Guide consumer while the actual Macro browser composition and production reference migration remain held by separate gates.

## Capability delta

`mode: context` is now genuinely non-invasive with respect to the host container. Before this change, mounting appended `mx-guide` to the supplied host class and `dispose()` always cleared the host's children, even though context mode renders no page UI into that host. On a real dashboard integration that made the component capable of altering or erasing surrounding host content during mount/teardown.

A new regression was written first and failed on the old implementation: a seeded Macro-like host changed from `macro-slot existing` to `macro-slot existing mx-guide`. The repair scopes host class ownership and host clearing to full-page mode only. The same seeded host class and content now survive mount, help open/close and dispose unchanged.

Fresh local verification at implementation commit `da3c09d30e212fa0a82179cd31528b1ef8164a15`:

- `node --test tests/test_market_guide_client.cjs tests/test_market_guide_view.cjs` — 56 passed, 0 failed.
- `python3 -m pytest tests/test_market_guide.py tests/test_market_guide_preview.py -q` — 68 passed; six inherited temporary-Chromium cleanup warnings.
- `git diff --check` — pass before source commit.
- Real Chromium 151.0.7922.34 synthetic host proof using all 46 source-backed definitions: global nav, host outerHTML, title, language and URL remained exactly unchanged across context mount → delegated `data-guide-entry="risk-radar"` click → dialog open → Escape → dispose; the safe full-guide link remained same-origin. Receipt: `r8-evidence/context-browser.json`.

This browser proof is deliberately **not** called actual Macro embedding. It isolates the component behavior that was objectively wrong and proves that behavior fixed in a real DOM.

## Current integration boundaries

A fresh attempt to inspect/run the real local `site/macro.html` composition was again explicitly refused by the OpenAI safety-status layer after the new tool generation became available. That exact lane was frozen and not rerouted through another host/tool. The previous full-Macro navigation discrepancy therefore remains unresolved.

Current observed `origin/main` is `2b2cae6a148f920b5c4e7ebd8df19ed14b159f5a`. Since the carrier's previously integrated base, relevant main movement includes `templates/dashboard.html.j2` and `templates/theme.css`. Open PR #7859 also touches `templates/dashboard.html.j2`; its published patch moves volatility diagnostics into Risk Detail and does not touch the current LOOK UP block, but same-file/current-base integration still requires normal merge-ref proof before release.

Reference PR #6792 remains OPEN/DRAFT at `7853ffeaca41d4d8f33995b1453db2be134ce8a3`. Its latest consumed independent review remains REQUEST_CHANGES on its route/evidence contract. Its builder/template/evidence custody is therefore not superseded or accepted. PR #7647's requested reviewer `mastermindx-2` has not returned a review; requested review is not START or acceptance.

## Procedure and next action

Protected procedure was re-pinned at `Mastermind/master@a0b31114d5d645e73da1333f7258092034a54c34`, compatible Skillpack 1.0.1/bootstrap 1, with INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE and CLOSEOUT loaded from that same commit.

Next critical action remains independent design/reference acceptance plus source-custody reconciliation for #6792. The actual Macro browser diagnostic may resume only after its safety-status boundary changes. Once both gates clear, wire the same shared manifest into the real LOOK UP/context-help path, retain fallback links, prove no navigation or host mutation on the real page, then proceed through current-base CI and normal production proof.

Do not recreate the Paper boards or bilingual registry, do not undo the heading/keyboard/host fixes absent a material invalidator, do not attach synthetic-host proof to a claim of real Macro embedding, and do not overwrite #6792's owned production reference paths.
