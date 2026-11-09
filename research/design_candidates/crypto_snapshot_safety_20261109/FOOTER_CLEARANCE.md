# Keep the footer action clear of the shared launcher

## Implemented outcome

Crypto's existing content owner now reserves `calc(96px + env(safe-area-inset-bottom,0px))` below the page. At actual document end, the model/methods action and its keyboard focus outline remain clear of the shared Ask Mastermind launcher.

This is one CSS declaration. The shared launcher keeps its existing size, position, hover behavior, stacking, input ownership and locale. No controller, layout breakpoint, extra interface copy or new action is introduced.

## Evidence and sizing decision

Native viewport proof at parent `7fd7d84f8b53ad0cd43c5175d3c149ad0d3ccf62` found eight blocked desktop combinations: four views in each of English and Chinese. The lower-right part of the footer button was intercepted by `#mmb-boot`. The apparent Solana obstruction in a tall-element screenshot was not an actual viewport-bottom obstruction.

The existing shared source sets the desktop launcher at 22px from the bottom. Its measured height is 56px. A reserve of 56 + 22 + 16 = 94px is rounded to the existing four-pixel spacing scale at **96px**. On mobile the launcher uses 16px plus the safe-area bottom inset; the Crypto reserve follows the same inset. No suitable shared clearance token was present in the inspected source.

The previous content reserve was64px. The additional32px gives ordinary document scrolling enough room to expose the last action. It does not try to prevent a floating control from overlapping intermediate content while the user scrolls.

## Scope

| Source owner | Actual change |
|---|---|
| `templates/crypto_intelligence_r4.css` | Existing `.cri` bottom padding:64px →96px plus safe-area inset |
| `site/crypto_intelligence_r4.css` | Exact served copy |
| `site/crypto-r4.html`, `site/vector-r4.html` | Generated asset-version references only |

Asset version: `0bad44b2e1ef`. Reversing the single CSS transformation recovers the exact parent. Seventeen other verifier inputs are byte-exact, including HTML template, JavaScript, view data, builder, projection, tests and shared assets. The renderer uses the retained view JSON; there is no producer run or current-data refresh.

## Focused native verification

Four fresh Chrome157 contexts/pages cover English and Chinese at320px and1440px. The Chinese320 context uses touch input; English uses dark theme and Chinese light. Within each context, actual navigation visits Overview, Bitcoin, Markets and Scenarios.

The proof places keyboard focus on the real footer action, reaches ordinary maximum document scroll, measures the actual launcher and checks five hit-test points across the control. It preserves native layout, timers, pointer/keyboard behavior and the shared launcher. The fixed Date belongs to the historical fixture. No outside HTTP or WebSocket traffic is permitted or observed.

**All16 candidate view/locale/width combinations pass.** All16 model-panel open→Close paths restore the originating view and footer focus. Zero page errors; zero external requests and WebSocket requests. Script11.045s; subprocess11.575s; wrapper11.99s. No saved-snapshot entry is created.

| Measurement | Parent | Candidate |
|---|---:|---:|
| Clear desktop combinations | 0 of8 | 8 of8 |
| Clear mobile combinations | 8 of8 | 8 of8 |
| Desktop control/launcher gap | −14.391 to−13.516px | 17.609 to18.484px |
| Desktop gap beyond focus outline | −20.391 to−19.516px | 11.609 to12.484px |
| Mobile vertical gap | −8.313 to−7.781px; horizontally separated | 23.688 to24.219px |
| Additional scroll extent | — | Exactly32px in all16 combinations |

The parent observer intentionally skips action clicks on blocked desktop controls. Its eight clear mobile action/return paths pass. It records4contexts/pages,9.045s and zero errors/outside traffic.

Before/after comparisons preserve every measured view width/height, footer width/height, button dimensions, text, type size/font family and keyboard focus extent. Launcher rectangles and computed position/offset/pointer/stacking properties are exact. The Overview summary text/fonts remain exact. Four final viewport screenshots, including visible keyboard focus outlines, were inspected.

This is bounded native UI proof for a CSS change, not a new full browser-suite run. The previous Overview, comparison, integrity and saved-case proofs retain their source scopes.

## Builder contract and practical limit

Keep bottom reserve with the existing page-content owner. If the shared launcher later changes its occupied height or bottom inset, remeasure the last action and its visible focus outline at actual document end; update the reserve through the same owner. Do not raise page content above the launcher or add a second launcher/controller.

The native environment reports a0px safe-area inset. CSS support and the zero-inset computed96px value are verified. The expression follows the shared mobile inset, but **a nonzero physical-device safe area was not verified** in this phase.

Paper's comparison Build note records the96px-plus-inset implementation contract and current proof. Its design references remain editable and conserved; this phase changes only that build text, not Paper style geometry.

Next: qualify asset quote values and preserve useful small-price precision. Producer/model policy, paired-window receipts and all existing release/admission/hosted-acceptance holds remain outside this CSS repair. Local historical proof is not production acceptance.
