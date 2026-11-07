China family edge-stripe sweep (PR #10748): REST and interaction evidence

What changed: templates/china.html.j2 drops its colored container edges under the Chairman design rule of 2026-10-18 (docs/DESIGN_DOCTRINE.md §3). The .nbcard state bar, the .nb-entry state top edges, the .alert left edge, the first-cell inset stripes, the BOARD DELAYED and risk-strip left edges, and the .nb-cau-pop colored row divider are gone. Borders are an even neutral 1px var(--line), and padding compensates for every removed edge.

Why interaction shots: the diff touches selectors that also have :hover / :focus-within rules (a.nbcard:hover, a.nbcard:has(.nb-cau:...), .nb-cau:hover/.nb-cau:focus-within .nb-cau-pop, a.alert:hover). manifest.json records real Playwright hover and focus on the first a.nbcard (nbcard-hover, nbcard-focus) in all eight desktop/mobile × en/zh × dark/light cells, alongside the eight REST cells.

What it shows: in every state, rest, hover and focus, the card carries no top bar. Hover keeps the existing lift and link-colored even border. Focus keeps a complete, even focus ring.

Input, stated plainly: the sparse worktree cannot render china_stocks.html from data, so this is the live production page of 2026-11-04 with this PR's CSS and inline-style edits applied to its externalized assets/css/*.css (and the risk-strip inline style), served through a local proxy. Every asset the page did not change was fetched from production. The 26 failed responses in the manifest are the page's live/*.json and cn_prophet_live.js feeds, which the proxy could not fetch anonymously. They are data feeds, not this PR's CSS.

Not shown: that day's data rendered no .nb-cau caution popover and no a.alert, so neither popover hover nor alert hover could be captured live. Their only changes are the popover row divider (now var(--line)) and the alert's even border with +3px left padding.

Reproduce: python3 scripts/capture_page_evidence.py --base-url <proxy>/new --routes /china_stocks.html --viewports desktop,mobile --locales en,zh --themes dark,light --force-state 'nbcard-hover:hover(a.nbcard)' --force-state 'nbcard-focus:focus(a.nbcard)' --output-dir mockups/evidence/china-edge-stripes-10748/captures --manifest mockups/evidence/china-edge-stripes-10748/manifest.json --settle-ms 1500
