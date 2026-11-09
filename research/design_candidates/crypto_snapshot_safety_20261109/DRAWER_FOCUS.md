# Drawer keyboard focus and the sticky header

> **Later feedback lifetime extension:** [Feedback lifetime](FEEDBACK_LIFETIME.md) now implements the retirement work described below. It uses the existing status/navigation owners and preserves fresh current confirmation and the intentional frozen Remove → Saved result. Focus geometry and this phase's historical proof remain unchanged.

## User outcome

Native forward and reverse keyboard navigation should show the complete focused control and its focus ring inside the existing drawer. The minimum intended clearance is 8px. Existing action and saved-disclosure rings occupy 6px (a 2px outline plus 4px offset), leaving room around the complete ring. Explicit reading restoration using `focus({preventScroll:true})` retains the reader's chosen position.

## Existing owners

The native `#cri-dialog` remains the only drawer scroll container. Its existing sticky header remains in place. The focus, history, storage, status and route owners are unchanged. Layout dimensions and action spacing should stay exact.

The CSS scroll-padding region can account for the actual header plus the focus clearance without adding content padding or blank space. The demonstrated header obstruction is corrected by a measurement that updates only that CSS metric; it never focuses, scrolls, renders, persists reading, alters history or retries an action.

## Acceptance

Native keyboard checks cover open and expired current cases at EN/390, ZH/320 and EN/1440; reverse navigation to a current disclosure at short viewport height; and reverse navigation after a retained title wraps during a wide-to-narrow resize. The actual visible header and focus outline are measured. Preserve route, stored bytes, write counts and outer-page scroll. Reading restoration, locale, newer choices, current review return and feedback timeout remain focused regressions.

## Implemented policy

The existing `.cri-dialog` receives `scroll-padding-block: calc(var(--cri-header-height, 0px) + 9px) 9px`. The requested 9px inset includes a one-pixel allowance for native fractional-coordinate rounding, so the tested control borders remain at least 8px inside the visible reading area. No additional scroll-margin allowance is combined with it.

A guarded ResizeObserver measures only the existing `.cri-dialog-header` border-box height and publishes its rounded-up value to `--cri-header-height`. The browser then uses the resulting viewing region for native focus scrolling. This handles current/saved header variants, title wrapping, locale and viewport-size changes. The observer does not focus, scroll, render, write history or access storage. Updating the metric changes no header or body dimension, so it does not create a resize/layout feedback loop.

The same native dialog scroll position and existing history reading remain authoritative. Explicit `preventScroll:true` focus calls are unchanged. The focus listener and terminal focus sequence are unchanged. Existing action/saved-disclosure rings retain their 2px outline with 4px offset; the current Conditions summary retains its native outline. No ordinary content padding, footer spacer, nested scroller, timing loop or navigation owner is added.


## Exact proof

Parent: `8714a277ddcc865f831021471520667d831304b1` / assets `62cf3bb534f8`. Final assets: `4f86c987c57c`.

| Stage | PID | Outcome | Pytest / subprocess / wrapper |
|---|---:|---|---|
| Exact parent snapshot | 26426 | 21 inputs copied; no runtime changes | — / — / 0.08s |
| Native baseline | 31453 | 7 failed / 41 passed | 43.96 / 45.072 / 45.19s |
| Initial candidate | 39334 | 47 passed / one failed | 39.70 / 39.956 / 40.19s |
| Final candidate | 44600 | 48 passed | 43.40 / 43.656 / 43.86s |
| Publication metadata | 47111 | source, case sets, 22 layout samples and captures verified | — / — / 0.19s |

The **same 48 case IDs and identical test bytes** are used in all three runs. Three new functions contribute 11 cases; 37 cases retain affected action, mutation-reading, history, locale, review return, focus and timeout behavior. No assertion was weakened after the baseline.

The baseline reproduced two clipped expired-Inspect rings and five reverse-Tab header obstructions. On the initial candidate, all header cases and 42 other cases passed. The remaining EN/390 expired-action measurement was 7.84375px from an 8px CSS request because native scrolling rounded fractional geometry. The final product correction requests 9px. The final measured minimum clearance is **9.25px above / 8.84375px below** across the 11 new outcomes. This is native geometry for these fixtures, not an assertion about every future browser or content variant.

Final Chrome **157.0.8103.39**, **48 contexts / 48 pages**, zero page errors, external requests or WebSockets. Twenty-two before/after samples retain exact body height, scroll height, header height and relative control geometry between the parent and final candidate. Normal content dimensions and action spacing are unchanged.

All **28 final PNGs** are retained, alongside three representative baseline captures and one initial-rounding diagnostic: **32 published PNGs**. The 11 new final focus views and three baseline views received visual inspection. The 17 final regression views and one initial diagnostic are retained without claiming new visual inspection. Capture references distinguish their exact runs and scope.

[Native publication receipt](drawer-focus/PUBLICATION_RECEIPT.json), [capture references](drawer-focus/CAPTURE_REFERENCES.json), and the preserved baseline/initial/final runners, outputs, observations and JUnit provide reproduction and case-level detail. This is an affected native run, not a whole application-suite claim.

Seven recorded runtime/generated/test paths change; fourteen inputs stay exact. Both source transformations reverse exactly; removing the appended tests recovers the complete parent browser module. Template and served JS/CSS match. Each HTML page changes only its two asset references. Source JSON, projection, HTML template, builder, server tests and shared assets remain exact.

## Editable reference and next work

Extend the existing QI Save/Remove scorecard and Build 3IP guidance: keyboard navigation keeps complete focus visible while explicit reading restoration preserves scroll. No new Paper specimen or style operation is needed.

Next, retire obsolete feedback and its retained timeout box when the user changes task, closes/reopens, changes language or retries. Preserve fresh current confirmation and the intentional frozen Remove → Saved outcome through the existing status/navigation owners; this phase does not change that lifecycle.


## Source rationale

[CSS Scroll Snap §4.2](https://www.w3.org/TR/css-scroll-snap-1/#scroll-padding) defines scroll-padding as the scrollport's preferred viewing region, including space obscured by fixed or sticky interface elements. It does not add ordinary layout padding. [HTML focus()](https://html.spec.whatwg.org/multipage/interaction.html#dom-focus) makes native programmatic scrolling conditional on preventScroll. These sources describe the mechanism; the recorded Chrome run is the evidence for the implemented behavior.

## Limits

Local historical/synthetic fixtures do not establish hosted/public-route acceptance or market freshness. Existing release, model, alert, result and receipt boundaries remain. Full browser-engine or assistive-technology certification is not inferred.
