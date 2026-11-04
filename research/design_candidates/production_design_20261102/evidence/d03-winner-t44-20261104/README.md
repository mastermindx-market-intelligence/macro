# D03 T44 — Winner Health boundary and history-track browser evidence

**Status: NOT_ACCEPTED.** The threshold and history disclosures qualify in all 50 measured cells. The complete journey is blocked in 42 cells by existing shared interactions:33 first-tap self-dismissals and 30 assistant-overlap cases, with 21 cells affected by both. Eight desktop English cells have neither measured blocker. This evidence does not mark T44 or D03 accepted.

No product source changed. Baseline is `ffda5424b75bbbb26e33a4d328043bbfb480e6ff`; current protected Mastermind pin is `cb8fa9132770b1967d585e323dd72b145c580601`. Parent: [D03 #10617, continuation6627822417](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6627822417).

## What was exercised

Four explicit `winner_health.v2` fixtures: N11/W, N11/D, N12/W and N12/D. Each uses one readable primary tier, one synthetic named row, a consistent tier-library/row track, an explicit history window and fully matured outcomes. Both N11 fixtures contain outcome values, so suppression must come from the threshold rather than missing input. N12 uses4 of12, avoiding the separate approximation and partial-maturity work held in #7073.

The actual `build_winner_health_page.build(root, fixture)`, Jinja template and `lib.pages.write_page` render into a temporary root. The browser consumes those exact output bytes and repository-owned styles, scripts and fonts. Chromium151.0.7922.34 runs at a Playwright-intercepted loopback origin. No network server, live market input, analogue engine, collector, model, authentication or deployment runs.

The only generated browser configuration is an explicitly disabled live-overlay fixture, using the observed `write_live_config` key contract. All UI assets are real source bytes. The initial pilot's absent live-config404 is retained; the qualified matrix has **no missing resources, external requests or JavaScript errors**. No browser CSS or gesture override is injected.

Normal matrix:4 fixtures × 3 widths(320/390/1440) × 2 languages(EN/ZH) × 2 themes(light/dark) = 48 cells. Two additional cells inspect reduced motion:320/light/EN/N11W and1440/dark/ZH/N12D.

## Content qualification

Assertions inspect the opened, rendered LENS and selected visible language—not hidden `.lens-src` markup. The initial native touch attempt remains a distinct result. When it self-dismisses, a real keyboard Tab step opens the card solely to qualify its content and layout.

| Case | Required observed disclosure | Suppression |
| --- | --- | --- |
| N11 /W | Eleven episodes; thin-record explanation; whole-US-market receipt | Outcome rows, rates and median figures absent |
| N11 /D | Eleven episodes; thin-record explanation; curated receipt; delisting-underrepresentation caveat | Outcome rows, rates and median figures absent |
| N12 /W | Twelve episodes;4 of12 and exact1-in3 example;8 remaining; supplied medians; history-not-forecast and same-cohort prose; later-delisted names included | Thin warning and curated caveat absent |
| N12 /D | Same populated historical outcomes; curated receipt and survivorship limitation | Thin warning and W-specific inclusion claim absent |

N11/W identifies its track in the short receipt; the longer delisting, history-not-forecast and same-cohort sentences belong to the non-thin branch in the existing template. Their absence at N11 is accurately recorded.

All50 cells pass these content checks. Card bounds, horizontal text fit, page width and reachable bottom receipt pass the measured geometry assertions. A receipt fitting inside its card is insufficient for acceptance: hit testing and actual screenshots expose the separate overlay obstruction below.

## Complete-journey results

| Width / mode | Cells | Content passes | First-tap failures | Obscured receipts | Complete measured passes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 320 normal motion |16|16|16|16|0|
| 390 normal motion |16|16|16|4|0|
| 1440 normal motion |16|16|0|8|8|
| 320 reduced motion |1|1|1|1|0|
| 1440 reduced motion |1|1|0|1|0|
| **Total** |**50**|**50**|**33**|**30**|**8**|

The verifier exits1 intentionally because 42 complete journeys remain blocked. Its report distinguishes PASS, BLOCKED and assertion failure; there are zero content/geometry assertion failures, not zero product failures.

### Shared first-tap self-dismissal — existing owner #6860

Native Chromium touch sequence: focusin on the analogue opener opens the LENS sheet and backdrop; the gesture's trailing click is retargeted to BODY; the outside-close handler closes the sheet. A second tap opens it because the trigger already has focus. Keyboard focus also opens it. The original failed pilot and instrumented first/second-tap event traces are retained under `diagnostics/`.

This exact defect is already owned by [#6860](https://github.com/mastermindx-market-intelligence/macro/pull/6860), head `03b21b1a9e0f1b5b517a9a92545bc02824411ced`, branch `claude/lens-sheet-tap-phantom-click`. Its existing paired theme.js/test scope, prior consumer requirements and integration gates remain. [Its continuity](https://github.com/mastermindx-market-intelligence/macro/pull/6860#issuecomment-5622945903) explicitly preserves the shared owner. #7590 independently overlaps the theme.js files. Original-host branch refs exist but no matching registered worktree was found; that observation does not prove abandoned custody.

No alternative gesture controller, source takeover, owner composition or candidate-acceptance claim was made.

### Shared assistant obstructs receipt — mobile owner #8754; desktop remains unqualified

Actual screenshots and text-point hit tests identify `#mmb-boot` / `.mmb-orb` above the LENS receipt. At this baseline its z-index is 2147483000; the LENS is 12600. The existing sheet-lock CSS hides `#mmb-root` but leaves the boot launcher visible. This obstructs 21 mobile and 9 desktop cells including reduced-motion supplements.

[Draft #8754](https://github.com/mastermindx-market-intelligence/macro/pull/8754), head `6037e03596ddc8300e7afd12b241889bf55dc210`, already owns a four-file shared mobile fix. Its CSS hides both launcher lifecycle states under `html.lens-lock`, and its retained evidence covers390px sheet cells. This is **mobile-sheet evidence only**: desktop floating cards do not set that class, so no desktop repair is established by that rule.

The [original International commission](https://github.com/mastermindx-market-intelligence/macro/pull/8754#issuecomment-6539662070) retains its sole integrator and local-only derivative scope with NO_PUSH_NO_CI. That narrower hold is preserved. No change, replay, publication or shared-source composition was performed on that carrier. The additional desktop obstruction remains an explicit acceptance input for the existing shared-overlay owner.

## Interaction and visual checks

Desktop cards open through a native Tab step from the preceding visible stop, and Escape dismisses them while retaining trigger focus. Mobile close-button taps dismiss the keyboard-opened sheet and release scroll lock. This proves those bounded actions, not all Enter/Space, screen-reader or global focus behavior.

Reduced-motion cells have no active LENS entrance animation and use the existing opacity-only transition. Mobile input is browser touch emulation, not physical Safari/iOS proof. No global accessibility or44px-target compliance is claimed.

Representative actual screenshots were visually inspected across N11/N12, W/D, light/dark and EN/ZH. Text hierarchy and wrapping are readable, but the assistant visibly covers receipt information. Mobile screenshots opened by fallback are labeled by their input result in the report; they are not presented as successful first-tap evidence.

Paper was actually inspected in the existing PROPHET file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, D03 contract page `p-D-0`. This was context inspection of an existing UI; no new board or Paper mutation occurred, and no Paper rendering is substituted for the browser results.

## Reproduction and evidence binding

`browser-proof.json` is the original50-cell result, SHA256 `c218a779f45c2dd1e72119ac50c5a4a23b1a6e3bc404a8342d802c1b1f4cc3b5`. The executed matrix driver is retained verbatim at `diagnostics/verify_browser_matrix_executed.py`, SHA256 `6b113dc8ec1c00c733a5ea5d577ac4df98f23c9a9104cbae327c75fdc43967ea`.

The final `verify_browser.py` differs only in source-binding preflight: it permits evidence-only descendant commits while requiring the product tree to match the pinned baseline. The50 browser cases were not rerun after that setup-only change; a separate preflight receipt verifies the binding. The exact executed driver remains available.

Use an admitted checkout containing this evidence and the unchanged baseline product tree. Use a new empty output directory to preserve existing receipts:

```text
python3 verify_browser.py --root /path/to/admitted/checkout --out /path/to/new/proof --preflight
python3 verify_browser.py --root /path/to/admitted/checkout --out /path/to/new/proof
```

The exit 1 and blocked counts are expected on the unchanged source. Requalification becomes useful after a material shared-source change and original-custody reconciliation.

Rendered HTML is retained in lossless .html.gz archives; the report hashes refer to the original served HTML bytes. The initial touch diagnostic is retained verbatim, with a separate archive-aware reader for reproduction. The inventory records every retained artifact, fixture, rendered page and screenshot. The engine and all product-source hashes match before/after. Original #7073, T43, active T41/T46/T47 carriers, #9495 dirt, R8 EFFECT_UNKNOWN and UX hold remain unchanged.

## Next action and hold

Preserve these consumer witnesses for the original #6860 and #8754/shared-overlay integration owners. After lawful integration on an exact source candidate, rerun the first-tap, dismissal and receipt-visibility checks on that candidate, including the desktop overlap. Reuse this unchanged threshold/track qualification; do not replace it with another unbound screenshot.

**Draft/HOLD: no Ready, un-draft, labels, enqueue, auto-merge, merge or deploy.** Content qualification, source fixes, hosted CI, release and user acceptance remain separate.
