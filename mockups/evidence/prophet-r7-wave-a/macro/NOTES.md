# Prophet R7 Wave A1: macro page theme.css repair

What this receipt covers: the add-only `theme.css` changes in #9954, which change
`templates/theme.css` and its paired `site/theme.css`.

- A new `--line-quiet` token is defined in both themes (dark `#272C35`, light
  `#E2E6EC`). No rule paints with it in this PR.
- Two later rules repaint the elevated risk-tier text on `/macro.html`
  (`.sx-vw-row--elevated .sg-wx` and `.sx-vw-tier`) with the readable
  `--ink-warn` token instead of the raw `--warn` series hue. This works in both
  themes. The earlier rules stay byte-identical.
- There is a `.nowrap` utility.

## How the cells were made

- The route is `/macro.html` from the PR tree's committed `site/` (site-dir =
  `site/`). This is the page whose elevated-tier text the repair changes. The
  committed page contains one `sx-vw-row--elevated` row.
- 8 rest cells: desktop 1440x900 and mobile 390x844 × en/zh × light/dark.
- #9954 adds no `:hover` or `:focus` rule, so no force-state cells are needed.
- Capture tool: `scripts/capture_page_evidence.py` v1.3.0 as committed on the PR
  head, with `--settle-ms 1500 --timeout-s 30`.

## Gaps

- `/macro.html` is the committed static build, so its data is whatever the PR
  tree carries. The elevated row may be outside the first viewport in some cells,
  because the cells are full-page shots only where the tool takes them.
- `--line-quiet` has no consumer yet, so no cell can show it.
