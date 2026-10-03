# Macro Events & News — implementation checkpoint, 2026-09-29

STATUS: COMPONENT_TESTED / INTEGRATION_BLOCKED / NOT_LIVE / HOLD.

Owner: Sol for Chairman Chris.
Operation: macro-events-news-desk-20260929-sol-001.
Branch: sol/macro-events-news-desk-20260929-sol-001.
Macro acquired base: 650e2ebbe08046bedf10e7eec39def3f62073103.
Governance observation: 9b01b708551196b1f144aa2f98b48bf37f513e26.

## Actual work

New source files are templates/_macro_events_news.html.j2,
templates/macro-events-news.css and templates/macro-events-news.js.
CSS and JavaScript have identical site/ asset mirrors. They are currently
UNWIRED: no parent template, entry card, generated macro.html or live page was
changed. Existing Alert Center V2 custody and separate full feeds are preserved.

The component separates review-worthy changes, a dated calendar, source-backed
news and observational context. It provides briefing/category views, multi-term
search, expandable evidence, specific fund-position headings, real publisher
fields, published-versus-seen dates, empty/unavailable distinctions, and a visible
source-order cap of 24 stories. Only exact URL+title repeats are omitted.

Calendar context is never promoted to a trade instruction. Passed dates do not
imply that releases occurred or results are known. Dislocation unknown/no-call and
stand-aside meanings are preserved. No scoring, risk permission, recommendation,
alert store, network polling, local-storage persistence or trading action added.

## Component-only validation

71 targeted local tests passed: 35 data/render tests and 36 Chromium checks.
Final run: 21.20 seconds. node --check passed. The tested local source SHA-256s
match these repository source files exactly:

- Jinja: 9b14b7c0b613d81cac2bb3bf93b6b72d411c31adf93ed2bdcf0f4e724e180769
- CSS: 3faa78b39714293b1b71656261ef536563388c677f2a876699f5caf1ac3cebd3
- JS: e48e7d63e3c7eb068d74d685a86d60fa3115d4dbe6d9c516a1c1ed1e48dc4987

Matrix: 1440x1000, 390x844, 320x740, 820x1180 and 844x390, each in dark/light and
English/Chinese. Checks include bounds, horizontal overflow, usable body scroll,
44px close control, filters/search/reset/view-more, local keyboard navigation,
source-link escaping, malformed inputs, date/timezone honesty, deliberate JS
failure and static evidence fallback. Eight sampled text roles have minimum
contrast 5.57:1 dark and 5.03:1 light using the supplied theme-token subset.
This is NOT a complete accessibility audit.

A search implicit-column layout bug and insufficient small calendar-tag text
contrast were corrected. Ticker strings, formatted/raw date searches and malformed
list payloads were hardened.

The full test harness, fixtures, run log, eight final desktop/mobile screenshots,
contrast measurements and self-contained HTML previews are in the portable
Macro_Events_News_Component_Checkpoint_20260929.zip artifact returned with this
conversation. They were run in the assistant's local container, NOT in this
repository's CI. The repository checkpoint contains source plus this handoff;
it does not pretend to contain those binary screenshots or the full test harness.

All preview data are labelled examples, not a verified live market briefing.
The preview renders authored HTML in memory against a theme-token subset and a
simple modal-owner stub. Production mx5 lifecycle, Escape, inert background,
focus/scroll restoration, full shared CSS and full dashboard regressions are
NOT verified. Neither build/render publication nor live transport is proved.

## Blocker — binding stop, not a transient retry instruction

The tool refused the attempted dashboard.html.j2 integration before execution:
"This tool call was blocked by OpenAI because we couldn't determine the safety
status of the request."

That edit was not applied and was not retried through another carrier. Do not
merge this checkpoint as a completed UI or bypass the tool denial. The popup and
its entry card are still the incumbent implementation.

Next action requires a genuine permission/authorization resolution. Only then
re-check current source custody, connect the component/assets, reconcile review
versus calendar counts across entry card and popup, run the actual full-template
regressions and modal lifecycle checks, and use normal protected CI/merge/render
and live browser proof. No background continuation or live delivery is claimed.
