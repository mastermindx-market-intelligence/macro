# Filtered-state crop — B-F13-3 round-3 MINOR-3

`help-filtered-account-dark-1440.png` / `help-filtered-account-light-1440.png` are a
**hand-captured supplement** to `manifest.json`, not a re-run of
`scripts/capture_page_evidence.py` — they are not referenced by `manifest.json` and carry
no `resolved_sha_or_none`. Committed separately so `manifest.json` keeps naming only what
that tool actually produced (`EVIDENCE.yml`'s own honesty axis).

## What they prove

Round-3 review MINOR-3: `templates/help.html.j2` used to zero the answers grid's top
border via `.help-a:nth-child(-n+2){border-top:0}`. `:nth-child` counts hidden siblings,
so after a category filter thinned the grid, the *actual* first visible row could still
carry a top hairline (an item that is DOM position 1/2 unfiltered is a different item
than whichever pair is visually first once earlier rows are filtered out). No committed
crop covered a filtered state at all (`manifest.json`'s `force_states` is empty).

The fix replaces the static `:nth-child` rule with a `.help-a-row-first` class the page's
own filter JS (`paint()`) recomputes on every filter/search event, from the actual
*visible* set and the current column count (`window.matchMedia('(max-width:900px)')`).

## How captured

Real user interaction, not a forced CSS class: `python3 -m playwright` (chromium),
loaded `help.html` built by `scripts/build_public_pages.py` served locally, called
`window.setTheme('dark'|'light')`, waited 1700ms (clear of `theme.js`'s ~1100ms
sky-toggle flourish — the same failure mode `manifest.json`'s own recapture note
describes), then **clicked** the "Account" category filter button
(`.help-filter[data-category="account"]`) — the same DOM node and event path a visitor
uses — and screenshotted the answers section once the filter's `paint()` had run.

Filtering to "Account" leaves 5 of 14 answers visible, in DOM order: `change-or-cancel`,
`how-do-i-sign-in`, `reach-a-person`, `after-i-write-in`, `email-and-marketing`. The DOM
order's first two items are `read-a-signal`/`what-is-calibration` (category `research`),
so this filter guarantees the *visually* first row is a different pair of elements than
`:nth-child(-n+2)` would have zeroed — exactly the scenario MINOR-3 named.

Confirmed via computed style at capture time (both themes identical, DOM order is
theme-independent):

```
change-or-cancel      rowFirst=true   border-top-width: 0px
how-do-i-sign-in      rowFirst=true   border-top-width: 0px
reach-a-person         rowFirst=false  border-top-width: 1px
after-i-write-in       rowFirst=false  border-top-width: 1px
email-and-marketing    rowFirst=false  border-top-width: 1px
```

Only the true first visible row (`change-or-cancel`, `how-do-i-sign-in`) carries no top
hairline; every other visible row does — no orphan hairline over the filtered grid, in
either theme.
