# D04 — standalone US heatmap return, complete lists and bounded lifecycle work

## Current Theme List query-render continuation

The successor to `3acd4fb0efe00793fc9987f1a6e45a512b26e5dd` now reuses the complete current Theme List for query-only changes. In the comparable controlled 4× CPU probe, expanded-list clear fell from **678.2 to 175.6 ms**, and expanded query from **512.4 to 121.0 ms**. Query-only List HTML replacement fell from one to zero. The overall 26-action median did not improve; full renders and some clear actions remain slower than 200 ms.

**90 semantic comparisons, 45 affected return cases, 89 Node tests and 84 focused Python tests pass.** Clean retention checks at desktop, 390 and 320 px found zero growth in retained nodes or event listeners. Root inspected the actual screenshots. Source, design, runtime-style and visual-evidence gates pass.

The generated page requests **`heatmap.js?v=46dacb96`** and browser comparison fetched the exact candidate bytes. [Method and limits](THEME_QUERY_REUSE.md) · [Current validation](theme-query-reuse-validation.json).

This section supersedes the earlier expanded-query gap and fingerprint below for this candidate. Historical measurements retain their original source and instrumentation. All 75 whole-programme cases remain unpromoted and release holds remain.

## Historical lifecycle and performance continuation

The published complete-List baseline is `61844ffd1b6e53d8e63122141b1125b3d6219bd3`. Its successor removes redundant US List/history work while preserving the delivered journeys below. History capture stops at the first visible row, skips the offscreen List when no row can be a visible anchor, and retains the original fallback. Filtering no longer repeats positioning, and restored disclosure notifications do not repeat an already-recorded history write.

In the controlled 4× CPU-throttled run, desktop Themes→S&P List median was **186.95 ms**, compared with **1,076.60 ms** before the repair. Final phone medians were **183.15 ms at 390px** and **201.90 ms at 320px**. These are local action-to-frame observations, not field Web Vitals. Complete expanded Theme-list reconstruction still reached approximately **0.8–1.0 seconds** under that stress condition and remains a disclosed performance gap.

The clean final-source lifecycle check collected the retired List and found **zero growth in retained DOM nodes or event listeners** across the exercised cycles at all three widths. Earlier apparent growth was traced to debugger console target handles; the failed instrumented observations and the actual retaining path are preserved, with a separate by-value browser protocol mode for collection proof. No shared observer or overlay was changed on the basis of that artifact.

The generated US page now requests **`heatmap.js?v=d72dc153`**, produced by the existing asset optimizer. An actual local browser response returned 200 and the exact matching JavaScript digest. The previous stamp was stale; only that generated content fingerprint changed in the page.

[Repairs, measurements, profiler attribution and limits](LIFECYCLE_AND_PERFORMANCE.md) · [Current validation](lifecycle-validation.json) · [Current affected browser journeys](../../../ux-evidence/d04-us-heatmap-return-20261104/lifecycle-functional/browser-report.json) · [Cache-stamp/browser readback](../../../ux-evidence/d04-us-heatmap-return-20261104/cache-stamp.json).

This continuation adds scoped A061/A063 evidence. All 75 whole-programme cases remain unpromoted, all release holds remain, and the historical List-access proof below retains its own inputs.


## Delivered behavior and acceptance boundary

The standalone US heatmap at `/sector_heatmap.html` now gives every supplied company and Theme member a reachable list path. Desktop users can choose Map or List; phones keep the existing list-first layout. Search matches ticker, English name and Chinese name. Themes use native disclosures containing the complete supplied member list, including members beyond the treemap and hover-card limits.

The list states the matched and supplied counts. A filtered group shows its matched/full count; the broader market summary remains unchanged and is explicitly described that way. A member-only search opens the matching Theme disclosure and narrows its members. Missing Theme-member returns say **No data / 暂无数据**, separately from a valid zero. The Themes size sort is labelled **Members / 成员数**.

S&P 500 and Themes retain independent timeframe, sort, query, presentation and disclosure settings through the existing native-history owner. Ordinary company/member anchors continue through the incumbent Terminal overlay. Normal settled desktop close retains the initiating anchor and its focus; phone return retains the view and scroll while preserving the overlay's intentional no-refocus behavior. Keyboard users can reach the List controls, rows and native disclosures, and use arrow/Home/End navigation in the existing map/timeframe tab groups.

The earlier return implementation remains: native document Back reconstructs the selected view and restores a logical item/group position. A missing item, changed observation receipt, unavailable timeframe or deliberate later user action produces an explicit limitation instead of a false exact-return claim. The incumbent overlay does not reopen on Forward; this branch does not claim full Back/Forward symmetry.

This is a held source implementation with scoped local browser evidence. It does not accept the whole D04 programme, the real D07/Terminal destination, final Paper composition, account persistence or production. The **75 whole-programme acceptance cases remain unpromoted**, and the **25 inherited reference conditions retain their prior statuses**.

## Source and custody

- Implementation law pin: `690e5316629815ae3e78f65ebdec2eb87f0cad16`; resumed against protected Mastermind `700eef54bca4a2dc4e30d94a6b30dcfa733ad57c`, skillpack 1.0.1 / bootstrap-major 1 compatible.
- Macro acquired base: `bb3b7273f1e9ccb869b6500c97871093eb22005a`.
- Prior return-only implementation: `5c3195cfb8b9644ce20526e94617ac1cb2268ecc`.
- CI import repair and parent of this list-access slice: `a538aa35e3cb5268fe834ff4da1098b68cbe9fa9`.
- Managed operation: `d04-us-heatmap-return-20261104`.
- Sole source writer: the attended D04 root session.
- Branch: `sol/web-d04-us-heatmap-return-20261104`.
- Held draft source carrier: [Macro #10719](https://github.com/mastermindx-market-intelligence/macro/pull/10719).
- Domain evidence carrier: [Macro #7727](https://github.com/mastermindx-market-intelligence/macro/pull/7727).
- Product files: `templates/heatmap.js`, `templates/sector_heatmap.html.j2`, and their two generated served assets.
- Test driver: [verify_us_heatmap_return_browser.py](../../../scripts/verify_us_heatmap_return_browser.py).

The original workspace acquisition and a later repair push each returned an uncertain effect. Both were reconciled through the original installed publisher and source/index reads. No replacement workspace, duplicate push or second writer was introduced.

The opt-in remains `data-hm-history="us-v1"`. Bounded transient configuration lives in the existing native history entry under `mmx.usHeatmap.v1`; unrelated object properties and the exact URL/query/fragment are preserved. Optional per-map presentation and disclosure fields are validated, bounded and backward compatible. Logical member identity is the parent Theme plus ticker, never a row index.

This extends the existing list renderer and history schema. It adds no account save, local/session store, history entry, router, auth provider, data producer, cross-origin transport or shared-shell controller. It refuses incompatible primitive/array history owners and opts out in regional fixtures, iframes and shared-shell contexts.

The history entry stores configuration, an observation receipt and a logical position/focus descriptor. It does not store the market payload or claim replay of prior membership or prices. Current feed data are rendered. Unsupported saved timeframes remain explicit until an available choice is made. When none is available, the notice says that settings are retained and no timeframe is currently available. Map search retains its existing tile emphasis; List search now filters the supplied rows on desktop and phone.

## Published List-access verification at 61844ffd

The final browser run passed **45 cases**, recorded **zero page errors**, and produced **29 functional screenshots**. The unchanged canonical capture owner produced **24 states: eight rest, eight focus and eight hover** across desktop 1440 and mobile 390, EN/ZH, dark/light. The final functional run is separately bound to the final harness hash; accepted canonical captures were retained.

| Browser cases | Count | Scope of proof |
| --- | ---: | --- |
| Desktop native document return | 4 | Exact URL, per-map controls, logical anchor, no additional D04 history entries, destination Forward |
| Phone overlay return | 4 | Existing overlay guard, retained DOM node, scroll and current view survive Back/Forward guard traversal |
| Per-map controls and class cleanup | 1 | Independent S&P/Themes settings without retired host classes |
| Delayed A → B → A selection | 1 | Only the current selection creates a live view/listener |
| Disabled, removed and all-unavailable timeframes | 3 | Retained intent and truthful recovery without silent coercion |
| Changed feed and missing item | 1 | Changed-observation notice and group fallback |
| Later deliberate focus | 1 | Restoration yields to the user's later focus |
| Phone retained query | 1 | The retained query now actually filters the phone list |
| Primitive, array and malformed history | 3 | Foreign state is preserved or safely refused |
| Regional, embedded and shared-shell opt-out | 3 | Neither US return ownership nor new List controls are introduced |
| Native fragment history | 1 | Configuration follows native Back/Forward entries |
| Responsive document return | 1 | Desktop-origin intent and filtering survive a phone return layout |
| Empty and failed payloads | 2 | Saved intent remains; no false restored-success message |
| Committed-feed renderer compatibility | 1 | Both unchanged US feed snapshots render through the existing selection owner |
| Culled stock keyboard access | 1 | A tiny 37th company absent from treemap DOM is searchable, keyboard reachable and correctly transported |
| Complete Theme-member access | 1 | All 40 fixture members, Chinese-name search, no-match recovery, distinct zero/missing values, unchanged summary |
| Browser touch input matrix | 12 | 320/390/1440 × EN/ZH × dark/light, actual touch events, primary targets at least 44 × 44 CSS px, no horizontal page overflow |
| Tablet touch input | 2 | 900px EN/light and ZH/dark |
| Live theme/language/resize/reload | 1 | Logical focus, selected List and initiating row identity are retained in the exercised paths |
| Optional saved-field validation | 1 | Invalid presentation/disclosure values are safely validated |

Functional journeys use the actual generated page/assets with synthetic public-shaped feeds, a labelled same-origin company-detail fixture, and a labelled local Terminal message fixture at the existing local Terminal origin. Chromium `151.0.7922.34` ran with bfcache disabled and reduced motion requested. Browser touch emulation is not physical-device, Safari/iOS or broad cross-browser certification.

The Terminal fixture verifies the incumbent overlay's symbol transport, warm desktop frame reuse, fresh phone frame and normal close/Back behavior. It does **not** establish actual Terminal rendering, authentication, market data, production cross-origin acceptance, iframe keyboard trapping or real destination Escape behavior.

### Committed data and contrast

A separate final-source probe loaded the unchanged repository snapshots and compared all supplied identities against the rendered list:

| Snapshot | Source clock | Source | Complete supplied access |
| --- | --- | --- | --- |
| S&P 500 | 2026-11-02 | `daily-close` | 503 company rows |
| Themes | 2026-11-03 | `finviz-themes` | 268 subsectors and 2,339 parent/member contexts |

The 2,339 contexts are Theme-member relationships, not necessarily unique companies. The maximum members per committed subsector is 16; the controlled 40-member fixture proves access beyond that particular snapshot. These source dates are not claims of current production freshness.

Computed sRGB foreground/background measurements for the new Theme disclosure direction, zero and missing-value labels passed **4.5:1** in all four EN/ZH × dark/light states; the minimum measured ratio was **5.219:1**. This is scoped label proof, not whole-page WCAG certification.

[Committed-list report](../../../ux-evidence/d04-us-heatmap-return-20261104/committed-list-report.json) · [Contrast report](../../../ux-evidence/d04-us-heatmap-return-20261104/contrast-report.json)

### Source checks and canonical receipt

- **89 passed** in the three existing shared heatmap Node suites.
- **84 passed** across heatmap label ink, China gate, Terminal overlay contract, import-pinning and logging/warning hygiene Python suites.
- Design-system added-line ratchet: **0 blocking findings**; existing estate findings remain outside this slice.
- Runtime-style ratchet: passed, **275 JS files / 44 existing injectors / 88 hits**, with no allowance increase.
- UI visual-evidence receipt gate, JavaScript syntax and diff whitespace: passed.
- Served/template JavaScript equality, final browser/product-and-harness hash equality and additional-probe/product hash equality: passed. The committed-data and contrast probes retain the earlier harness hash; their four product hashes are unchanged. The fresh 45-case run binds the final harness.

The canonical scene seeds a valid prior native history entry and uses the synthetic feed. It runs the unmodified `scripts/capture_page_evidence.py` and records its native `mastermind.p0_evidence.v2` manifest. The manifest's nearest Git HEAD is the pre-commit parent; the browser report and final validation bind the actual working-tree product and harness hashes. No claim is based on HEAD alone. Capture timing fields are lab observations, not a performance acceptance or production metric. Authenticated and forced loading/empty/stale/error states omitted by the canonical capture remain explicit gaps; relevant functional fixtures are separately described above. The canonical screenshot scene separately records one connection-refused console error for the local Terminal destination at 127.0.0.1:3100; its raw manifest is retained. It is not successful destination proof and is distinct from the functional suite's zero page errors.

[Final validation and raw check outputs](final-validation.json) · [Functional browser report](../../../ux-evidence/d04-us-heatmap-return-20261104/browser-report.json) · [Canonical manifest](manifest.json) · [Receipt](EVIDENCE.yml)

## Visual self-check and repairs

The root inspected all eight final canonical rest states, representative desktop/phone focus and hover states, final filtered Theme-member captures in both languages/themes at desktop and phone widths, a 320px stress view, and final committed-data company/Theme lists. New controls, source clock, count explanation, member identities and missing values remain readable without horizontal clipping. Names wrap, primary controls retain touch size, and sparse search results do not leave an empty full-width frame. New Theme directional text uses semantic ink on neutral surfaces; missing values use neutral text.

The original return-only work repaired native Back timing, stale selection mounts, retired layout callbacks, all-unavailable timeframe chrome and later user intent. This access slice also preserves a connected row across a resize that remains in List, restores logical focus synchronously during locale/theme rerender, and preserves disclosure state through the exercised native reload/overlay path. It introduces no delayed focus timer.

Dense maps, breadth/statistics panels, hover summaries and existing rotation links remain available. Broader baseline styling, untranslated fixture labels in unchanged summary panels and the existing overlay/copilot are not claimed as a completed page redesign.

## Incumbent Terminal and shared-source boundaries

The Terminal overlay retains ownership of history, scroll and focus. The local proof covers normal close after readiness settles. Source inspection identified an existing untracked 180 ms iframe-focus callback and 90 ms scroll restoration without later-user-intent cancellation. Desktop return holds the original DOM reference; phones intentionally skip explicit link refocus. The branch neither repairs those owner functions nor claims all timing-sensitive A053 behavior. An arbitrary disclosure collapse, unrelated rerender during an open overlay, immediate close at readiness or actual iframe Escape remains outside this proof.

This branch does not import or replace held regional work:

- [#7967](https://github.com/mastermindx-market-intelligence/macro/pull/7967), head `a7d07473b030b2b981dedadac3d6ceafa381c34c`, owns China sector/theme access. Its protected payload/auth-driven reselect must survive future composition. Its forced-reselect second argument differs from D04's return intent; the two booleans cannot be blindly identified.
- [#8144](https://github.com/mastermindx-market-intelligence/macro/pull/8144), head `537513f60aec40a360c31ea65220de11c0da2e0c`, owns regional live refresh, manual List mode, integrity/query presentation and heatmap-overlay repairs. Future composition must reconcile those shared layout hunks with the US-only opt-in and retired-view cleanup.

These are read-only overlap findings, not a merge rehearsal or acceptance of combined unmerged branches. Current checks exercise the acquired mainline plus this slice. A025, A050 and A053 receive scoped US subrequirement evidence; no entire programme acceptance case is promoted.

## Paper, release and continuation

The actual Paper reference `01M3NSZGE8JWN2EZCSF0DT05RM` / `p-8-1` / `N2Y-1` was inspected, including its rendered “Every company remains reachable” list/disclosure reference. No Paper edit was dispatched. At recovery, the legacy Studio Paper adapter refused write qualification for observed catalog `03cb81e960dab705b21b0695f3886d39c4792df629a6419163efef52338182e4` against its old full-catalog expectation `ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9`. A subsequent actual native Mastermind Paper inspect/catalog and exact target read found the current direct route connected to Paper 0.5.18 with `TOOL_SCOPED_CONTRACT_V1`, `accepted_for_write=true` and no incompatible write tools. This read-only capability finding supersedes a blanket catalog blocker; no prepare/edit, unknown-effect replay, adapter installation or user-active-file switch occurred. Exact target/custody/snapshot qualification still applies to each future operation, and final F01/F02 composition remains unqualified. D23 account persistence and shared-shell/production cross-origin return remain with their owners.

No merge, Ready/un-draft, enqueue, auto-merge, held-label change or production deployment is authorized by this delivery.

The optional Fabric commission `d04-us-heatmap-return-20261104-state-tests`, original root/parent `d04-us-heatmap-return-20261104`, original controller PID `72554`, remains separately uncertain. Worker START/root/result were not proven; controller binding was lost. No result was consumed and no retry, replacement, re-home or acceptance occurred. This is **EFFECT_UNKNOWN for that original commission**, not a running/completed worker or review approval. Bounded native reasoning advice was accepted/STOP; root authored, tested and visually checked the source.

Next: observe exact-head CI for the current held draft, record its result in the existing D04 continuation, and repair only an actual owned failure. The finite lifecycle continuation is documented above; expanded-list rendering and field budgets remain explicitly unaccepted. Once owning foundation/runtime interfaces qualify, compose the owned routes, persistence and Paper references and perform the remaining programme journeys. Do not redo accepted Confluence evidence or reconstruct the delivered discovery package without a material change.

## Historical import-hygiene repair

Hosted CI run `41800565111` at `5c3195cfb8b9644ce20526e94617ac1cb2268ecc` found one introduced failure: the browser harness pinned this repository only inside its canonical-capture branch. Base replay passed. The existing pin was moved to module scope before repository imports and the late duplicate removed. No baseline, waiver, test or workflow was weakened.

Local repair verification passed 11 import-pinning tests, 4 logging/warning hygiene tests, a foreign-package resolution probe outside the checkout, and entrypoint help outside the checkout. Product files were unchanged by that repair. [Causal repair receipt](ci-repair.json).

Published repair head `a538aa35e3cb5268fe834ff4da1098b68cbe9fa9` subsequently passed hosted **ci 41821362101** and **fences 41821362098**. This is the repair-head result; the list-access successor requires its own exact-head CI result.
