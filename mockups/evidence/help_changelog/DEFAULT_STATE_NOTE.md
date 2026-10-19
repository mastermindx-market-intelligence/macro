# Default (unfiltered) state crop — B-F13-3 round-4 MINOR-3

`help-default-unfiltered-dark-1440.png` / `help-default-unfiltered-light-1440.png` are a
**hand-captured supplement** to `manifest.json`, not a re-run of
`scripts/capture_page_evidence.py` — they are not referenced by `manifest.json` and carry
no `resolved_sha_or_none`. Committed separately so `manifest.json` keeps naming only what
that tool actually produced (`EVIDENCE.yml`'s own honesty axis) — same idiom as
`FILTERED_STATE_NOTE.md`.

## What they prove

Round-4 review MINOR-3: `manifest.json`'s `target.resolved_sha_or_none` is
`78d84feafdb3073a7f2f021da0954430abd7bbfb`, three heads behind this PR's current head —
captured while the answers grid's first-row hairline was still suppressed by the pure-CSS
`.help-a:nth-child(-n+2)` rule. The round-3 fix (see `FILTERED_STATE_NOTE.md`) replaced
that rule with a `.help-a-row-first` class the page's own filter JS (`paint()`)
recomputes, now called once unconditionally at load as well as on every filter/search
event. The two round-3 crops prove the *filtered* state under the new mechanism; nothing
committed at the current head proved the ordinary, no-filter-applied default state still
renders correctly under it — i.e. that calling `paint()` at load produces the same visual
result the old CSS-only rule gave for the common case every visitor actually lands on.

## How captured

`scripts/build_public_pages.py`'s `build()` run against this exact working tree (head
`dcd0eee135cc5edef65ba91c4a170b4d5ff9068b`) to produce a real `help.html`, served locally
over plain HTTP (`python3 -m http.server`) alongside the committed `theme.css`/`theme.js`
so `_public_chrome_js.html.j2`'s theme toggle behaves exactly as in production. Loaded
with `playwright` (chromium) at 1440×1400, called `window.setTheme('dark'|'light')`,
waited 1700ms (clear of `theme.js`'s ~1100ms sky-toggle flourish, same margin
`FILTERED_STATE_NOTE.md` uses), took no action (no click, no search input — this is the
page exactly as a fresh visitor sees it), and screenshotted the answers section.

Read back via computed style at capture time (both themes identical, DOM order is
theme-independent, no filter applied — `data-directory-state="complete"`,
`help-result-count` reads `21` = 7 links + 14 answers):

```
read-a-signal          rowFirst=true   border-top-width: 0px
what-is-calibration    rowFirst=true   border-top-width: 0px
how-do-you-know        rowFirst=false  border-top-width: 1px
look-up-a-term          rowFirst=false  border-top-width: 1px
```

Only the true first visible row (`read-a-signal`, `what-is-calibration` — the same pair
`.help-a:nth-child(-n+2)` used to zero, since no filter has thinned the grid) carries no
top hairline; every other row does. `paint()` running unconditionally at load reproduces
the pre-existing default appearance exactly; the two crops are the visual confirmation.

## Scope note (not fixed here)

Investigated separately in this round: whether `paint()` at load regresses the
*degraded* (`entries` empty) state's null-disclosure panel. It does not — that branch of
`templates/help.html.j2` never renders `#help-search`, so the page's IIFE returns at
`if(!query)return;` before `paint()` is ever reached, and the server-rendered
"No links available · 0" panel (no `hidden` attribute) is left untouched. Confirmed by
rendering the template directly with `entries=[]`: the emitted HTML contains no
`id="help-search"` element at all.
