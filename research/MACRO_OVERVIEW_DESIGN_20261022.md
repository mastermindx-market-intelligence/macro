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
The corresponding implementation files are unchanged by this UI work. Intentional
copy expectations were updated; generated-asset checks are run after the normal
post-render transforms, not against the raw development render.
