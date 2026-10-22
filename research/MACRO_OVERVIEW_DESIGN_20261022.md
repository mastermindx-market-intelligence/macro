# US macro overview — design and delivery record

Status: implementation complete; release validation in progress.

## Intent

Make the macro dashboard readable as a daily research desk: establish the market
backdrop, make the limits of the read visible, and help a reader find the next
useful question. The user authorized assessment, design, direct implementation,
and final hardening. Root owns the design and implementation; an independent
design critique is advisory.

Source baseline: `64ef5131a5f50fb65f0ad25a049a457e18258495`.
Workspace branch: `claude/ssd-macro-dashboard-design-20261022-29cca618e2a89cb5`.

## Observed problems

The live macro route had no page heading. Its oversized score/gauge and stretched
history chart outweighed the interpretation. Six quote tiles were boxed inside
another card. Event names were truncated in the template before layout, so even a
wide display could not recover them. The Fed glance showed a legacy hike/cut
comparison beside a producer stance that expressly withheld that comparison.
A nested Jinja comment also leaked template punctuation into the page.

## Design decisions

- Give the page a clear bilingual heading and direct section links.
- Lead the hero with the market verdict. Keep the live score, gauge, risk
  qualification, and measured history connected to their existing data owners.
- Use a balanced interpretation/history composition and canonical surface,
  typography, spacing, and color tokens. Remove decorative background blooms.
- Make the market tape one divided surface. Spell out the instrument names,
  preserve futures identity, and expose the existing quote freshness states.
- Use a vertical event agenda with complete bilingual event labels, localized dates,
  and an honest upcoming-window label.
- Strengthen panel headings and the playbook's primary stance while keeping
  supporting prose quieter. Compact secondary cards; use neutral ticker mentions
  and named heating/cooling counts rather than an anonymous rank-height strip.
- Place the existing assistant in the page action area. Move its complete root
  and bootstrap control so handlers, tokens, access rules, and focus return stay
  owned by the shared component; it no longer floats over readings.
- Keep the history available on small screens; let the page stack without
  horizontal overflow.
- Reuse the producer's qualified D1 comparison and present-basis checks for the
  Fed glance. Do not calculate a substitute policy path in the template.

## Boundaries

Shared navigation, theme implementation, signal calculations, thresholds, measured
history geometry, live-data hooks, and existing detail dialogs retain their owners.
The work does not edit the concurrent Fear/Greed detail or Dark Flow insertions.
The scoped stylesheet is a build-time Jinja include, not injected runtime CSS.

## Acceptance

Review the rendered page at 1440×900 and 390×844, in English and Chinese, with
light and dark themes. Inspect hero balance, complete event labels, quote
freshness, mobile wrapping, keyboard focus, and dialog entry/exit. Capture real
hover/focus evidence. Run the design-system and runtime-injection ratchets,
relevant macro regressions, the Fed basis cases, and source/output synchronization.
Keep generated changes scoped to the macro page and its actual dependencies.

The normal build initially lacked `rjsmin` in the host Python environment. The
dependency was installed into a task-specific temporary directory and the normal
build resumed with that directory on its Python path; shared Python was not changed.

## Validation notes

The normal build completed successfully. The final scoped output uses the same
canonical inline-asset externalization and asset-versioning functions as the normal
post-render pipeline. Unrelated generated data and pages were restored from the
worktree baseline.

Anonymous browser checks preserve the registration sheet for detailed risk,
calendar, and market views. The public factors popover opens by keyboard and
closes with Escape. The assistant opens by keyboard and returns focus after
Escape. Neither check sends a chat message or changes an account.

An expanded regression run exposed three untouched baseline failures: two tests
expect synthetic-timestamp quotes to splice into risk-state frames, and the chat
asset detector flags the existing `stock.html#` navigation literal in `theme.js`.
The corresponding implementation files are unchanged by this UI work. The two
quote tests now require rejection and intact nightly fallback, matching the
existing validity owner. The asset detector exempts hrefs only for statically identifiable anchor
assignments. It still rejects HTML-named stylesheet assets, reused link variables,
script/CSS URLs, HTML src URLs, and indexed-node src URLs. Positive controls pin
those distinctions.
Intentional copy expectations were updated; generated-asset checks are run after
the normal post-render transforms, not against the raw development render.

The main-branch rebase retained upstream news translations, current data, and the
complete unchanged detail-dialog region. It removed only the duplicated glance
copy at the conflict sites. Canonical escaping and current asset hashes were
retained after reconciling the generated page; measured score projection was not
replaced with the raw market-state artifact.

## Final local acceptance

- The 14-file macro acceptance run passed: **252 tests, no deselections**.
- The final asset-detector tightening passed its **17-test** launcher suite.
- The canonical evidence matrix captured **32/32** states: eight resting
  desktop/mobile × English/Chinese × light/dark cells, with real card hover,
  factors-button focus, and assistant-button focus for each cell.
- Existing W9 fixture evidence was refreshed: **74/74** states, including missing
  data and empty-state cases. These are fixture renders, not live-data proof.
- The evidence integrity gate, design-system ratchet (zero added blocking
  findings), and runtime-style-injection guard pass. The canonical template/site
  synchronization guard passes with the task's isolated rjsmin dependency.
- Final keyboard checks open factors and the existing assistant, close them with
  Escape, and return assistant focus to its launcher. The assistant focus ring
  remains contained. Measured scroll widths equal the viewport at 390 and 1440.
- The static preview has no page JavaScript exceptions. Its live/API/WebSocket
  routes are unavailable by construction, and the visible stale/unavailable
  states reflect that boundary; it does not establish production feed health.

Cold-load measurement also observed layout movement during existing shared-shell
hydration. The largest diagnostic shift involves the shared navigation search and
control slots. This page-scoped delivery does not change the shared navigation
owner or claim a Core Web Vitals certification. The final resting layouts and
interaction states are the acceptance evidence above.

The independent reviewer supplied visual critique and examined the semantics of
the baseline test repairs. A subsequent bounded source review of the new CSS/JS
includes and changed hero, events, and Fed/Policy markup at `a3e7e82187d2` found
no material regressions. Runtime and production verification remain root-owned.

The first CI run caught an unwired new test module. The eleven Fed/Policy cases
were moved intact into the existing `tests/test_macro_glance.py` suite, which the
dashboard-organs CI job already executes. Its 18 cases pass after consolidation;
no waiver or CI-authority configuration change is involved.

## Shared quote-asset evidence closure

The second CI run identified the required P0B browser-receipt refresh for the
bilingual unavailable-feed copy in `site/live.js`. The other eleven CI packs
passed. The existing fixture renderer and stock-dashboard browser verifier were
run against the final candidate assets for both Canada and Hong Kong, using the
installed Playwright 1.63 package and Chromium 151.0.7922.34. Both verifier
processes exited successfully. Their owner-projection matrices passed 96 primary
cases and 32 degraded controls in total, with 16 freshly captured screenshots.
The screenshots and rendered fixture remain byte-identical to their prior
versions; the current receipts bind the actual loaded assets, including the new
`live.js` digest and the observed favicon request.

The P0B manifest extension was aggregated from the successful receipts and actual
on-disk image digests. Every recorded construction input, loaded asset, verifier,
fixture, and screenshot digest was checked. Its previous extension was preserved
in history, bound to the prior manifest digest and source head `1a6fcf564bc7`.
Historical targets and artifacts were retained. These remain reproducible browser
fixture claims, not canonical-build or production evidence.

The full `tests/test_stock_dashboard_first_frame.py` suite passed: **115 tests**.
The P0B receipt-closure gate also passed against the complete PR changed-path
inventory. This refresh changes only the three evidence JSON files and this
record; it introduces no additional product-code edits.
