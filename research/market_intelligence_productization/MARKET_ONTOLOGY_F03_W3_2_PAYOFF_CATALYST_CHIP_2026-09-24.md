# F03-W3-2 · Payoff-fold catalyst chip — research note

Implementation record for A-F03-W3-2 (the chip the F03-W3-1a producer
pre-staged in `site/options_catalyst_links/latest.json`).

## What it is

A single sentence chip on the index-card payoff fold (SPY / QQQ / IWM)
that answers exactly one question: **does a Federal Reserve rate
decision land between this close and the expiry these structures use?**
Context only — never rank, never score, never size — sitting inside the
existing fold body immediately above the four payoff rows the W2-5b
packet ships, so the reader sees the answer next to the structures it
qualifies.  Three terminal states, all read off the same
`macro_calendar` envelope the producer writes:

| state | chip EN (chip ZH) |
|-------|-------------------|
| `before-expiry` | "Fed decision Oct 28 lands before this expiry" (美联储10月28日议息在到期前) |
| `clear` | "No Fed decision before this expiry" (到期前无美联储议息) |
| (absent) | (no element rendered — silence, never "none") |

The chip names the FIRST Fed decision inside the window
(`card_asof < d <= expiration`); the tooltip lists every Fed decision in
the window with the "and so does …" clause when there is more than one.
The word "FOMC" never appears on the page — the plain form is "Fed
decision" / "美联储议息".

## Why it is data-driven

The chip is driven by the SAME `engine.event_calendar.fomc_decision_dates`
list the producer's binder reads — no second calendar reader.  The
producer (`scripts/build_options_catalyst_links.py::_macro_calendar`)
emits a `macro_calendar` envelope key built from
`_macro_candidates(asof, horizon_days)`; the consumer
(`scripts/build_options_command.py::_payoff_lab_catalyst`) reads the
same key and decides per-card.  Schema stays
`"mastermind.options_catalyst_links/v1"` with `spec_version` bumped by
its own convention; only the additive key is new.

## Tri-state law (chip is ABSENT — never printed as "none" — when ANY)

`calendar` is None (load_catalyst_links returned None: missing file,
wrong schema, missing `macro_calendar`, or `fomc` not a list);
`expiration` or `card_asof` is not a YYYY-MM-DD ISO date;
`expiration > calendar["horizon_end"]` (calendar cannot see that far);
`calendar["asof"]` more than 7 calendar days older than `card_asof`
(exactly 7 days is acceptable).

## Two art directions (TP-0 2026-08-27)

DARK — command-center luminance tint (12 % ink-info wash on `--tile`,
hairline border at 45 % ink-info over `--hair`, dot glyph in
`currentColor`, no glow).  LIGHT — research-workspace hairline (60 %
ink-info over `--hair`, transparent fill, no shadow, ink-weight border
only — never the same body token as dark).  Both share the SAME
`.oew-lab-cat` selector; the light override sits under
`html[data-theme="light"] .oew-lab-cat`.  `@media (max-width:480px)`
lets the chip wrap on mobile.  No JS, no runtime style injection, no
`title=` attribute (CI-guarded).

## One-night calendar lag

`site/options_catalyst_links/latest.json` is written by the producer
which runs AFTER `build_options_command` in `daily.yml`.  On the night
the producer first runs after merge the chip is absent on every card
until the next nightly; the loader's fail-soft contract preserves the
pre-W3-2 fold byte-for-byte until the new key lands.  Pre-F03-W3-2
callers that never pass `catalyst_links` get no chip and zero other
behaviour change.

## Evidence matrix

`mockups/evidence/a-f03-w3-2-payoff-catalyst-chip/` (12 PNGs + EVIDENCE.yml
+ manifest.json; `capture_page_evidence.py --routes /options.html
--max-pages 1`; `OEW_PAYOFF_LAB_FORCE_OPEN=1` for the open fold):
12/12 captured across dark/light × EN/ZH × desktop/tablet/mobile;
0 console errors; 0 horizontal overflow; chip visible on SPY, QQQ,
IWM in every cell.  No "FOMC" / "fomc" / "macro_calendar" /
"before-expiry" tokens in visible text (class token `is-before-expiry`
is allowed in markup).  Fold's other elements are byte-identical to the
no-calendar render after the chip's `<p>` is stripped via regex.

## What this packet does NOT do

No new verdict, rank, score, or size (display-tier context only).  No
key added to `load_stores` (pinned BYTE-FOR-BYTE by
`tests/test_render_options_workspace_scope.py`); the new artifact is
loaded via `load_catalyst_links`, exactly like `load_intel_brief` /
`load_payoff_lab` / `load_skew_source`.  No touch to `engine/**`,
`scripts/build_options_payoff_lab.py`, `config/unrun_test_waivers.yml`,
`data/**`, `site/**`, `.github/**`, or any other template.

## CI homes

Producer — `tests/test_build_options_catalyst_links.py` cases `i`, `j`
pin the envelope carries `macro_calendar` from the SAME
`_macro_candidates` list AND on the no-stage path too.  Consumer —
`tests/test_options_payoff_lab_consumer.py` (tri-state, loader fail-soft
contract, render fixture, fold unchanged).  Workspace-scope —
`tests/test_render_options_workspace_scope.py` stays green.

## Acceptance grep (measured 2026-09-23 against `origin/main` merge-base)

| grep | count |
|------|-------|
| `scripts/build_options_catalyst_links.py::_macro_calendar` | 1 |
| `scripts/build_options_catalyst_links.py::_macro_candidates` | 5 |
| `scripts/build_options_command.py::load_catalyst_links` | 1 |
| `scripts/build_options_command.py::_payoff_lab_catalyst` | 1 |
| `templates/options.html.j2::data-payoff-catalyst-chip` | 1 |
| `templates/options.html.j2::.oew-lab-cat` | 8 |
| `templates/options.html.j2::html[data-theme="light"] .oew-lab-cat` | 2 |
| `mockups/evidence/a-f03-w3-2-payoff-catalyst-chip/*.png` | 12 |
| `tests/test_options_payoff_lab_consumer.py` W3-2 cases | 11 |

129/129 tests pass on the W3-2 proof line; `check_design_system.py
--mode enforce-added --diff-file`, `check_runtime_style_injection.py`,
and `check_ui_visual_evidence.py --diff-file` all exit 0.
