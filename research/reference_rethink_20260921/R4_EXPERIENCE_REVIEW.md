# R4 — visual clarity, usable explanations and keyboard repair

Status: source-backed review candidate; production is unchanged. Current continuation is `CHECKPOINT.json`, not the historical first-turn README's research-only scope.

## What users gain

The three questions now have the original monoline visual cues, short descriptions and clear arrows. The score's six real named ingredients are links to their own explanations, not decorative or fabricated bars. The selected example gains an explanatory heading rather than leaving interpretation entirely to a paragraph. The full definitions, limitations and source links remain available.

Search supports Enter for an exact alias without selecting an ambiguous answer automatically. The initial page no longer constructs the full hidden result list; it builds results when requested. This is a demonstrated DOM behavior, not a measured loading-speed claim.

The component stylesheet is scoped to the guide or its own dialog. It uses inherited semantic theme tokens rather than modifying global navigation. Light retains white selected surfaces and quiet elevation; dark uses outlined depth and an inset selected surface. Mobile composition is specified in source, but this turn's expanded current-source visual matrix was blocked and is not claimed as passed.

## Keyboard result

The R3 failure was reproduced before repair. The six focusable controls were followed by a step where `document.activeElement` was BODY and `document.hasFocus()` was false, before focus returned to the close button. The repaired endpoint handling keeps normal Tab and Shift+Tab inside the dialog; native inert and Escape behavior remain native. This follows the keyboard contract in https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ .

At view subject `a7b5827dad123a69f963fceec4dfad89d41dd891`, real Chromium 151.0.7922.34 completed 14 forward and 14 reverse steps with document focus and dialog containment, then Escape returned focus to the original control. `r4-focused-browser.json` records the actual sequence and HTML digest. The original failed full qualifier has not been rewritten as a pass.

## Context-only capability and unresolved composition

`mode: context` binds only declared help controls and the existing shared language event. It does not install standalone-page history, search-shortcut or preference handlers, render into the surrounding page, or claim its title. Unit tests cover the unchanged host URL/title/preferences, safe full-guide link and shared-language behavior.

A local browser composition used the unchanged committed `site/macro.html`, all 46 real definitions and the candidate assets, with external requests blocked to keep the test offline. Six existing lookup links were enhanced in browser memory only; the modal opened. The subsequent exact navigation-HTML comparison differed. The cause is unverified: adding the intended data attributes to navigation descendants or existing host startup/scroll behavior could affect that comparison, but neither explanation has been proven. The diagnostic request was refused. Do not claim a real Macro integration pass or change the test to excuse it.

## Qualification and exact remaining work

67 Python and 53 Node tests pass (120 total). Python reported six pre-existing temporary-browser cleanup permission warnings. Desktop and modal screenshots were visually inspected. The downloadable review wrapper now directs owning-dashboard links to the user-provided canonical site when opened as a local file; it does not fetch market data or deploy anything. That wrapper change passed the 67 Python tests, but its separate browser link-check request was blocked.

The two-suite CI enrollment, expanded responsive/browser qualifier, actual Macro composition diagnosis, independent review and production migration/release remain open. The unchanged 20 Paper artboards are still provisional; this work restores their specified details rather than remaking them. No autonomous worker or wake is running.
