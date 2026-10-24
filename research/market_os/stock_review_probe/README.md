# Stock inspection review — visual candidate and executable behavior evidence

**REVIEW ONLY / SYNTHETIC FIXTURES / NOT PRODUCTION-READY.**

Operation: `market-os-shared-shell-design-20260924-sol-001`; parent `WS:MARKET-OS`; sole branch/PR `sol/market-os-shared-shell-design-20260924` / Macro #7949. Current Chairman directive explicitly calls for sustained, substantial redesign and end-to-end production readiness, not arbitrary 10–20-minute or minor-label-only cycles. Pre-release visual/refinement and actual source/permission/proof gates remain. Comments5826088944 and5826167808 preserve the current directive and mid-phase effects.

## Material design result

In the existing Paper file MASTERMIND PAGES (`01M2WGNCX9475G79JRKJTCM08P`), review page `p-D-0`, added the previously missing dense-stock study:

**09 · Stocks & setups · Inspect without losing place · 1440**, artboard `VIU-0`,1440x900 at8540,0.

The study has a compact primary read, lane filters, separate search/theme/sort controls, a six-row comparison table and a persistent selected-listing inspector. Row inspection and checkbox comparison are separate intents. The NVDA inspector shows meaning, explicit unmeasured options confirmation, and distinct Terminal/save actions. QCOM's unavailable quote is an em dash, not zero. All figures and states are synthetic and labeled. This does not validate a financial model, originate a trade or change any existing engine.

The final screenshot was visually inspected: table, inspector, repeated row lanes and bottom disclosure fit. Native source screenshot `27-stocks-inspector-review.png`, SHA256 `94ee304e5c06579ef4cb1e374cd241eaf26249714d3fb14d860d531721b08c6a`. Working indicator cleared; shared token hash remained `5ae876bc`. Existing seven artboards and original reference pages were preserved. Eight artboard identities are not eight complete designs.

Paper review URL: https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0

## Executable behavior, not a second production service

The four `.mjs` files here are an isolated synthetic model and tests. They are not imported into a production route and have no browser, network, storage, account, quote or trade side effects. They specify interaction invariants for the current owners to consume. Do not adopt this local reducer as a replacement router, retry system, market model or personal-state store.

A separately authored offline HTML behavioral probe and its full source/check bundle were created in the current conversation artifact owner. They implement local filtering, nonmodal inspection, inline comparison, staged updates, null handling and simulated saves. They intentionally do NOT implement country switching, the held mobile drawer, original portal roundtrip, native Paper-to-code export, real Terminal entry or a real account write. Terminal is visibly disabled. The HTML states browser runtime is unverified.

Artifact filenames and exact digests:
- `mastermind_stock_review.html`,37766 bytes: `81804bd396387524a68fccad8b4f88801b2319288451cd0aba41de1c1b8736bc`.
- `mastermind_stock_review_source.zip`,56868 bytes,24 entries: `6221b3f4e7af0f4aa02ac67e35a3df9fd08ce2301ba5f79c4d42933d1f3a7171`.
- Bundled `MANIFEST.json`: `ad2a47fd823dcf83e10c38adae5b53bb79fcef403ed4fad199b1cbe058b18627`.

The HTML/UI source, browser suite and full logs are conversation attachments, not claimed committed by this README. The independently reproducible pure behavior/test files are committed here. If attachment bytes are needed in a later session, retrieve the actual attachment rather than inventing a sandbox path or recreating an export. Exact Paper design remains in Paper.

## Verification actually executed

```text
node --test model.test.mjs display.test.mjs
43 tests,43 passed,0 failed,0 skipped

python build_review.py
standalone file built; repeated build byte-identical

python static_checks.py
17 checks,17 passed,0 failed
browser_checks_executed:0
minimum declared text-token/base-surface contrast:5.352:1
```

Node22.16.0; pure tests use built-in node:test/assert. Initial model scaffold produced22 expected failures before implementation; display scaffold7. The adversarial round had29 pass/4 fail, then33/0 after repairs. Final additional edge/invariant cases produced43/0. Logs, source and checksums are in the attachment bundle. The static check initially rejected a three-digit CSS literal in its own parser; the parser was corrected to expand shorthand colors before the successful check. That technical parser failure was not a browser or permission event.

The four persisted sources were verified by comparing GitHub contents metadata at commit `c61f72ee9af6ae12a61ce1793ed9b0ead6205d60` against Git blob hashes calculated from the exact tested local bytes:
- review-model.mjs:206f8c2a55bd60c3c148adc5c5a4c3070d04a0e2
- model.test.mjs:0ef20816b43b2a2ead02a241b7a545c6c72ef7ae
- review-display.mjs:15dcdbe33e4d13e704e88c7700cfc301d5d2888f
- display.test.mjs:321d611f2090cdd7cf9df0c37df004626ae38919

From repository root, reproduce the pure tests with `node --test research/market_os/stock_review_probe/*.test.mjs`. These results are not full repository CI, browser interaction, accessibility certification or production acceptance.

## Important interaction requirements now falsifiable

- Filtering retains the selected listing and compared identities; hidden selection is disclosed, not discarded.
- A ticker string on two venues is two identities. Never substitute another listing when the original disappears.
- Stable sort keeps ties deterministic and unknown numbers last. Zero remains a valid value.
- New snapshots are staged. Applying buffered data does not declare a failed source recovered.
- A demo save settles only the exact listing AND request identity that originated it; a late earlier response cannot complete a newer attempt.
- Missing/unmatched acknowledgments and truthy nonboolean responses cannot fabricate a success.
- Comparison is bounded and toggles without duplicates; removing a disappeared member remains possible.
- Untrusted labels are escaped; inherited JavaScript property names cannot become presentation tokens.

The missing save-request correlation, acceptance of an uncorrelated completion, buffered-data/source-health conflation, and inherited presentation token all had discriminating failing tests before their repair. This is a material behavior delta, not an inferred improvement from the static image.

## Exact verification boundaries

A compound native Paper JSX/computed-style export and scratch receipt write was explicitly safety-refused before dispatch. It was NOT retried. No export or exact Paper translation is claimed. The independent behavioral probe argues from its own written interaction specification and synthetic fixtures; it does not reconstruct the denied export or replace any held design target.

Chromium navigation to the local behavioral fixture returned `net::ERR_BLOCKED_BY_ADMINISTRATOR` before the first assertion. One non-mutating diagnostic found an administrator URLBlocklist covering navigation. No policy change, alternate browser/address, injected-content route, device or retry was used. The prepared browser suite has ZERO executed behavioral checks and no browser screenshot. Static source/color checks are explicitly not rendered geometry, computed accessibility, focus behavior or latency proof.

These are two distinct action-local boundaries, not a universal Paper/account outage and not EFFECT_UNKNOWN. All prior specifically refused operations remain frozen on their original targets. No exact human credential ceremony or hidden mode telemetry was invented.

## Product acceptance still owed

The product must outperform the current site on the same tasks: understand the market, inspect several candidates without losing context, switch to a qualified native market task, open the exact security, save through the canonical owner and return. Test task completion and context errors with the same dataset/entitlement, not just visual preference.

Candidate performance targets follow Google's Web Vitals guidance: LCP<=2.5s,INP<=200ms,CLS<=0.1 at the75th percentile, separately mobile/desktop. These are unmeasured targets, not achieved results. Source: https://web.dev/articles/vitals . Keep the project's40px standalone-control floor, visible focus and non-obscured keyboard navigation; W3C's target-size minimum has its separate24px/spacing rules and exceptions, not a blanket40px mandate. Sources: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html and https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html . Declared color ratios do not establish full conformance.

Next critical work is the exact original country/mobile/production-path proof under permitted recovery, then current source-custody/implementation admission and a bounded representative deployment. Do not repeat the334-row inventory or34-test historical portal baseline without a relevant invalidator. The first-adoption contract retains native US6/China5 Sector views, Confluence, document scrolling and singular portal/history ownership. Exclude inner-HTML fragments, embeds and utility/operator surfaces from automatic frame wrapping.

Protected procedure for this phase: Mastermind `605cd056c3463c992d85ba76dbcc90fbb758da75`, compatible Skillpack1.0.1/bootstrap1; required companions loaded at that pin. Scoped design/source reference: Macro `22094843f4042db6d9d77ad8847bcdbf9a27faa9`, `_us_act_now_board.html.j2` and `docs/DESIGN_DOCTRINE.md`. No application route, source owner, canonical registry, market data, permission, actual watchlist, merge or deployment changed. No worker/watcher/background execution. Parent mission remains incomplete.
