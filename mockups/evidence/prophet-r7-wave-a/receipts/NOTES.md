# Prophet R7 Wave A3: passed-on receipts specimen

What this receipt covers: the CSS, markup and disclosure states that #9955 adds in
`templates/_prophet_receipts.html.j2` (`pvr_css`, `pvr_receipts`, `pvr_today_count`).

## How the specimen was made

- `source/component.html` is rendered from the real template, not hand-copied. It
  uses the build_site Jinja environment (FileSystemLoader on `templates/`,
  autoescape on) and the same `{% import "_prophet_receipts.html.j2" as pvr %}` /
  `{{ pvr.pvr_css() }}` calls that `templates/dashboard.html.j2` makes.
- The page links the real `site/theme.css` and `site/theme.js`, so theme and
  language switching come from the production chrome. The specimen frame uses tokens
  only (`--panel`, `--line`, `--r-card`, `--r-ctl`, `--font-ui`, `--fs-*`, `--muted`)
  and has no accent stripe on any edge.
- The data is a fixture, and `sample=true` prints the in-component sample disclaimer.
  It has six passed-on names across the three reasons: two `validation_failed`
  (plan-data refusals), two `plan_not_built` and two `ran_too_far`. One name has no
  score, and two have a sector.

## States shown

1. Today count: `pvr_today_count` with label, total and the plain link.
2. Collapsed: `pvr_receipts` at the default limit of 4. Refusals come first, then
   score descending, and two names sit behind one "Show 2 more" disclosure.
3. Expanded: the same list with every `<details>` opened by a two-line script after
   render. It shows the refusal body (what did not verify, no entry, timing or exit,
   next build) and the research-link-only body for the other reasons.
4. Empty: `passed = 0`, no groups and `{}`. All three macro calls render 0
   characters (the counts are printed in the caption), so no heading or empty box
   reaches a page. The dashed slot holds that empty output.

## Cells

- 8 rest cells: desktop 1440x900 and mobile 390x844 × en/zh × light/dark.
- The force-state `rc-focus:focus(.pvr-rc-sum)` covers the added
  `.pvr-rc-sum:focus-visible` rule in both themes and both locales (8 more cells).
  The first summary in the document is the collapsed list's first row. The ring is a
  complete outline, not an edge stripe.
- Capture tool: `scripts/capture_page_evidence.py` v1.3.0 as committed on the PR
  head (sha256 8d753e28...). Run with site-dir set to the repository root,
  `--settle-ms 1500 --timeout-s 30`. Result: 16/16 captured.

## Gaps

- The specimen shows the component, not its placement inside `dashboard.html`.
  #9955 does not change dashboard placement, and the dashboard page is
  data-dependent.
- The "Ask Mastermind" launcher in the cells is injected by the production
  `theme.js`. It is not part of this component.
