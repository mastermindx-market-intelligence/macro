# D04 — standalone US heatmap return

## Delivered behavior and acceptance boundary

This slice preserves the research context of the existing standalone Macro US heatmap at `/sector_heatmap.html`. S&P 500 and Themes retain independent timeframe, sort and raw query settings. Desktop document Back reconstructs the selected view and restores a logical item/group position after native history restoration. A missing item, changed observation receipt, unavailable timeframe or deliberate later user action produces an explicit limitation instead of a false exact-return claim.

Mobile company rows use the existing Terminal overlay. D04 captures the initiating origin, preserves the live heatmap node and yields to that overlay's existing history, scroll and focus ownership. The incumbent overlay does not reopen on Forward; that behavior is unchanged and is not represented as full Back/Forward symmetry.

This is a held source implementation with local browser evidence. It does not accept the whole D04 programme, the D07 destination, final Paper composition, account persistence or a production deployment. The seventy-five whole-programme cases and twenty-five inherited reference conditions retain their previous statuses.

## Source and custody

- Protected Mastermind pin: `690e5316629815ae3e78f65ebdec2eb87f0cad16`.
- Macro acquired base: `bb3b7273f1e9ccb869b6500c97871093eb22005a`.
- Managed operation: `d04-us-heatmap-return-20261104`.
- Sole source writer: the attended D04 root session.
- Branch: `sol/web-d04-us-heatmap-return-20261104`.
- Domain evidence carrier: [Macro #7727](https://github.com/mastermindx-market-intelligence/macro/pull/7727).
- Product files: `templates/heatmap.js`, `templates/sector_heatmap.html.j2`, and their two generated served assets.
- Test driver: [verify_us_heatmap_return_browser.py](../../../scripts/verify_us_heatmap_return_browser.py).

The initial workspace acquisition returned an uncertain effect. The original operation was reconciled through its installed owner and source/index reads before modification. No replacement workspace or second writer was introduced.

The opt-in is `data-hm-history="us-v1"`. Bounded transient configuration lives in the existing native history entry under `mmx.usHeatmap.v1`; unrelated object properties and the exact URL/query/fragment are preserved. The helper adds no history entries, account save, local/session storage, router, auth provider, data producer or cross-origin transport. It refuses incompatible primitive/array history owners and opts out in iframes or when the shared shell exists.

The entry stores configuration, an observation receipt and a logical position/focus descriptor. It does not store the market payload or claim replay of prior membership or prices. Current feed data are rendered. Unsupported saved timeframes stay explicit until an available choice is made. When none is available, the notice states that settings are retained and no timeframe is currently available. The desktop query dims nonmatching tiles; the mobile list explicitly says that the retained query is inactive there.

## Verification

The final browser run passed **27 cases**, recorded **zero page errors**, and produced **13 functional screenshots**. The unchanged canonical capture owner produced all **eight rest states**: desktop 1440 and mobile 390, EN/ZH, dark/light. The canonical manifest and receipt passed the repository visual-evidence gate.

| Browser cases | Count | What the checks establish |
| --- | ---: | --- |
| Desktop document return | 4 | Exact URL, per-map controls, logical anchor, no added D04 history entries, destination Forward |
| Mobile overlay return | 4 | Original overlay guard, retained DOM node, scroll position and current view survive Back/Forward guard traversal |
| Per-map controls and class cleanup | 1 | S&P and Themes retain distinct settings without retired host classes |
| Delayed A → B → A selection | 1 | Only the current selection creates a live view/listener |
| Disabled, removed and all-unavailable timeframes | 3 | No silent coercion or data reveal; retained intent and truthful recovery copy |
| Changed feed and missing item | 1 | Changed observation notice and group fallback |
| Later deliberate focus | 1 | Late restoration does not steal the user's new focus |
| Retained mobile query | 1 | Inactive mobile filtering is disclosed |
| Primitive, array and malformed history | 3 | Foreign state is preserved or safely refused |
| Regional, embedded and shared-shell contexts | 3 | Return owner remains opted out |
| Native fragment history | 1 | Configuration follows native Back/Forward entries |
| Responsive document return | 1 | Desktop-origin intent survives a mobile return layout |
| Empty and failed payloads | 2 | Saved intent remains; no false restored-success message |
| Committed feed compatibility | 1 | Both committed US feeds render through the existing renderer and map selection agrees with the view |

Functional journeys use the actual generated page/assets with synthetic public-shaped populated feeds and a labelled same-origin company-detail fixture. Chromium `151.0.7922.34` ran with bfcache disabled and reduced motion requested. These are controlled reconstruction and overlay-owner checks, not proof of production authentication, live data, D07 content, Safari/iOS hardware or bfcache behavior.

The committed-feed compatibility case separately loads the unchanged repository snapshots: S&P has **503 source tiles**, dated **2026-11-02**, source `daily-close`; Themes has **268 source tiles**, dated **2026-11-03**, source `finviz-themes`. These are snapshot source counts and clocks, not claims of present market freshness or the number visible in one viewport. The committed-feed screenshot waits for the selected map and disables the incumbent 150 ms selector transition during capture.

The canonical capture scene seeds a valid prior native history entry and uses the synthetic feed. It runs the repository's unmodified `scripts/capture_page_evidence.py` and records its native `mastermind.p0_evidence.v2` manifest. It is not a hand-authored evidence schema or a production screenshot.

Final checks on the same source hashes:

- **89 passed** in the three existing shared heatmap Node suites.
- **69 passed** across heatmap label ink, China gate and Terminal overlay contract Python suites.
- Design-system added-line ratchet: **0 blocking findings**. Existing estate findings remain outside this slice.
- Runtime-style ratchet: passed, **275 JS files / 44 existing injectors / 88 hits**, no allowance increase.
- UI visual-evidence receipt gate, JavaScript syntax and diff whitespace: passed.
- Served/template JavaScript equality and browser-report/source hash equality: passed.

[Final validation and raw check outputs](final-validation.json), [functional browser report](../../../ux-evidence/d04-us-heatmap-return-20261104/browser-report.json), [canonical manifest](manifest.json), [receipt](EVIDENCE.yml).

## Visual self-check and repairs

Desktop and phone captures were inspected for the new notice's hierarchy, readability, spacing, clipping, dark/light contrast and EN/ZH presentation. Dense maps, breadth/statistics panels, mobile lists and existing rotation links remain available. Unchanged broader page styling and baseline untranslated fixture/industry labels are not claimed as a completed page redesign or accessibility certification.

Real browser work repaired native Back timing by restoring the logical anchor after pageshow and two animation frames. It also established the mobile overlay's incumbent ownership, retained later user intent, stopped superseded A → B → A mounts and cancelled retired resize/layout callbacks. Visual inspection removed misleading empty data chrome for an unavailable timeframe, clarified the all-unavailable message and corrected a screenshot that caught the map selector midway through its color transition.

## Shared-source composition boundary

This branch does not import or replace held regional work:

- [#7967](https://github.com/mastermindx-market-intelligence/macro/pull/7967), head `a7d07473b030b2b981dedadac3d6ceafa381c34c`, heatmap blob `21fb416da288304394683942d489da4db4acdbd4`, owns China sector/theme access. Its `mountMulti` adds member access checks, protected payload loading and auth-driven reselect. A future composition must keep those checks, combine the selection-epoch guard once, pass the optional US entry to the admitted view, and keep its forced reselect distinct from D04's return intent. The two second-argument booleans cannot be blindly identified.
- [#8144](https://github.com/mastermindx-market-intelligence/macro/pull/8144), head `537513f60aec40a360c31ea65220de11c0da2e0c`, owns regional live refresh, manual list mode, integrity/query presentation and heatmap-overlay repairs. Its changed layout/live-refresh hunks require explicit composition with D04's optional layout callbacks and retired-view cleanup.

These are read-only source-overlap findings. No merge rehearsal or acceptance of the combined unmerged branches is claimed. Current D04 checks exercise the acquired mainline and this slice only.

## Remaining boundaries and successor action

No merge, Ready/un-draft, enqueue, auto-merge, held-label change or production deployment is authorized by this delivery. Paper reads remain possible, but the observed catalog `03cb81e960dab705b21b0695f3886d39c4792df629a6419163efef52338182e4` is not accepted for writes against expected `ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9`. No Paper mutation occurred. P00 owns that runtime qualification; final F01/F02 composition is unqualified. D23 account persistence and shared-shell/cross-origin return remain with their existing owners.

One optional bounded Fabric test-authoring commission remains uncertain: run `d04-us-heatmap-return-20261104-state-tests`, original root/parent `d04-us-heatmap-return-20261104`, original controller PID `72554`. Worker START/root/result were not proven; the controller later lost its binding. No result was consumed, and no retry, re-home, replacement or acceptance occurred. This is preserved as EFFECT_UNKNOWN for that original commission, not a running/completed child or a review approval. The native reasoning adviser supplied bounded read-only advice and was accepted/STOP.

Next: reconcile exact-head held-draft publication and CI in the existing D04 continuation record. Once the corresponding owning foundation/runtime interfaces are qualified, compose the owned routes, persistence and Paper references and perform the remaining programme acceptance journeys. Do not redo the accepted Confluence evidence or reconstruct the delivered discovery package without a material change.
