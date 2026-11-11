# BioCatalyst WMN recovery proof — PR #6712

This directory records the local consumer proof for source commit `3901ec90c4fd5c31df3eeb670c9992a7ac1155d9` (tree `c2a251fccdaf3ce84d3077a15972efa7bc4e6898`). It supplements the earlier recovery at `87ed9b7a1a0d26cb0ca139db18bc0a4531e915ad`; it does not rewrite any historical capture archive.

## Repairs and observed results

The C3 style repair replaces the 31 newly introduced design violations (18 color mixes and 13 radii) with existing design tokens. It preserves the pre-existing BioCatalyst rules.

The C4 behavior repair keeps language changes from converting a locked or unavailable queue into a false empty result, resurrecting rows after a failed append, or clearing the busy/disabled state of an outstanding request. The existing request token, abort, generation, cursor and 409-reload logic remain the owners of network state. Localization does not issue a replacement request.

The six new language scenarios run against both template and served JavaScript. All 12 failed against the old production JavaScript blob `5bdb102b1bc7888449272d41cb4fc6b2386657dd`; the underlying assertion causes are retained in `language-red-causes.json`. The same test blob `f4a30426004e34590df8be73b6440e1e087684c1` passes all 36 request-ownership cases against the repaired JavaScript blob `c9c9ed154bef647445a89f92452427dcb98914d6`. The 36 include the 24 pre-existing request cases and 12 additions.

The actual Chromium journey passes **400 checks across eight combinations**: 1440 and 390 widths, dark and light themes, English and Chinese. It covers card hover, native keyboard focus and selection, selected-event detail identity, the trial-workspace continuation, horizon changes, refresh recovery, 403/503 failures, language changes during failures and pending requests, and actual router pagination from 50 to 51 unique rows. A failed append must not resurrect the first page. A pending append must retain its 50 rows and busy controls, then complete with 51 unique `data-wmn-key` values and no remaining Load more control.

During failure/pending checks, the journey opens the existing Settings pane through gear focus or Enter, tabs to the actual language switch, presses Space, and uses Escape to close it. It does not call `setLang` or stamp DOM state during those scenarios. Initial theme/language setup is explicit fixture configuration. Earlier exploratory Settings helpers did not qualify this journey; only the completed run in `browser-receipt.json` is claimed.

The browser matrix records no JavaScript page errors. Its **40 expected HTTP errors** are preserved as observations of explicit local failure cases; they are not concealed or described as a production health result. The portable runner was additionally exercised for the 390/dark/Chinese case (50 checks); this is a repeatability smoke check, not another 50 distinct product scenarios.

## Bound shell, API fixtures and captures

The shell was regenerated through `scripts.build_biocatalyst.render_from_state`. Its SHA-256 is `728e1ec1078587c62412d6446d35e608163a065e61a013a54ef24eb479e02780`. The nine builder/template/output Git identities are recorded in `render-observation.json`. The **11 actual script/stylesheet assets referenced by that shell** are independently bound in `served-assets.json`.

The served `site/theme.js` is the repository's minified blob `d85bf9fb55cd67faf32dd49e88423fe249fb8855`; it is not mislabeled as the readable template blob `21a1fb1627ac34badc6078cff486f98486e9b773`.

The two-row WMN fixture and the 51-row pagination fixture come from the existing local API test seam and actual repository router. The clock is the test's fixed `m.NOW`. Pagination uses a clearly scoped fixture-only signing key; the actual router signs and validates the cursor. The first response contains 50 rows, the next contains one, and both use the same generation. The fixture preserves private/no-store, Authorization variance, and noindex/noarchive headers. These fixtures do not establish production owner admission, live data freshness, or user entitlement.

The canonical repository capture helper produced **40 images**: eight REST cells and four forced states for each cell (card hover/focus and continuation-link hover/focus), with 1250 ms settling. Their hashes, byte counts, dimensions, applied locale/theme and force states were checked against `manifest.json`. The canonical capture reports no console or failed-response entries and no horizontal document overflow. It retains its seven reported gaps. The semantic journey supplies 12 additional selected/locked/unavailable images under `interactions/`.

Desktop light/English REST and mobile dark/Chinese card-focus images were visually inspected. The screenshots preserve missing-owner and NOT_ESTIMABLE labels and the separate locked trial-registry state. No uncertainty is filled with a fabricated score.

## Gates and packing

`gates.json` records zero blocking design findings, a successful UI-evidence check, and a successful P0B check against the immutable M714-to-C4 source scope. The design scan also reports 25,309 pre-existing nonblocking findings; this repair does not claim to remove them.

`packing.json` records the supported canonical planner measurement using the exact tracked-path inventory: 149,677 paths, SHA-256 `ca6eb06c5c683feb43b57b9d0fcf9acfa95e0689166185c217a378ccc1f180fa`, 30,896 materialized source paths, and zero unreadable suite candidates. The manifest retains 401 owners. The measured BioCatalyst owner weight is 272. The three golden rows are 137/5974/10, 137/5995/10 and 131/5732/10, with zero breaches. No packing limit or manifest weight was raised for the added language cases.

The final publication additionally checks the complete source-plus-evidence tree and unchanged render/served-asset inputs. PR-level natural CI remains a separate result on the eventual published head.

## Reproduction

Install the repository's existing test and Playwright dependencies and provide its normal Chromium installation. The scripts honor `PLAYWRIGHT_BROWSERS_PATH`. Materialize the real `site/` assets through the repository's supported sparse-checkout helper before running them.

```sh
python3 mockups/evidence/biocatalyst-wmn-pr6712-20261111-r2/verify_interactions.py --repo . --output-dir /tmp/wmn-browser-proof
python3 mockups/evidence/biocatalyst-wmn-pr6712-20261111-r2/capture.py --repo . --output-dir /tmp/wmn-canonical-proof
```

Both scripts verify the recorded source and actual served-asset identities before replay. Output goes to the explicitly selected directory. The browser verifier supports `--case 390-dark-zh` for a bounded smoke check. The capture wrapper uses the unchanged repository `scripts/capture_page_evidence.py` implementation. Reproduction is a local synthetic-API proof, not a production request or admission action.

## Acceptance boundary

This record qualifies the repaired local behavior and visual evidence. It does not release the PR's existing holds, claim a nonauthor review, merge or deploy the branch, prove authenticated production access, or establish biological/financial model accuracy. Any owed production and natural-publication proof remains separate.
