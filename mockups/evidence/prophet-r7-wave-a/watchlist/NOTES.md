# Prophet R7 Wave A2 - watchlist visual evidence

What was rendered: `/watchlist.html` as the render lane would publish it from this
branch. `templates/watchlist.html.j2` was rendered with build_site's Jinja
environment (autoescape, the `min` and `regex_replace` filters, the `td`/`tr`/
`t_pctile`/`zip`/`SITE_BASE`/`CHANNEL_LABEL` globals). The page context is the
JSON already embedded in the tracked `site/watchlist.html`:
`STATE_DISPLAY`, `WL_STARTERS`, `WRI_REGIME`, `WL_SECTOR_ZH`, the public Supabase
config and the generated stamp. The output then went through the same committed-
form sweeps as the render lane: data-base injection, CSS externalization into
`assets/css/<sha8>.css` and `?v=` asset stamps.

Faithfulness check: the same procedure applied to the merge-base template
reproduced the tracked `site/watchlist.html` byte for byte, and its stylesheet
matched as well.

Captured from a scratch copy of `site/` holding the rebuilt page, its new
externalized stylesheet and this branch's `watchlist.js` / `watchstore.js`.
The capture covered 8 rest cells: desktop 1440 and mobile 390, en and zh,
light and dark. Each rest cell also has a hover cell (`--force-state
"row_hover:hover(.hold tbody tr)"`, files suffixed `--row_hover`), so the
manifest holds 16 cells. All 16 were captured with the requested theme, locale
and forced state applied, with no console errors, no failed responses and no
horizontal overflow at either width. Settle time was 1500 ms so the theme
toggle animation finishes before each shot.

Not committed: the rebuilt `site/watchlist.html`. A faithful render needs its
new `site/assets/css/<sha8>.css`, which is outside this repair's owned files.
Committing the page alone would ship a stylesheet link that resolves to nothing.
The render lane regenerates both files after merge.

Why hover cells are present: no added line contains `:hover` or `:focus`, but
the mobile hide rule adds `.hold .c-wsv, .hold .c-ton`. The `.hold` token is
also the target of `.hold tbody tr:hover` and `.hold thead th.srt:hover`, so
`check_ui_visual_evidence.py` routes the change to hover evidence. The forced
hover lands on the first `.hold tbody tr`. For an anonymous viewer that is the
positions table's empty-state row, so the shots show the row tint from
`.hold tbody tr:hover` in both themes. They do not show a populated holding row,
because no saved rows exist without an account.

Signed-in access tiers and loading, empty, stale and error states are recorded as
manifest gaps: none of them can be produced from static output.
