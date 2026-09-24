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
the window with the "and so does …" clause when there are two dates
and "and so do …" plus a comma list at three or more.  The producer
output is already sorted; the helper also sorts the filtered dates on
its own end so a hand-injected unsorted `fomc` still names the
right "first" date.  The word "FOMC" never appears on the page — the
plain form is "Fed decision" / "美联储议息".  The calendar's as-of is
rendered in the tooltip through the SAME human date-word formatters the
chip uses for its expiry text (`_payoff_lab_expiry_en/zh`), so ZH
lands as a single Chinese sentence rather than an ISO string stuck into
a Chinese one.

## Why it is data-driven

The chip is driven by the SAME `engine.event_calendar.fomc_decision_dates`
list the producer's binder reads — no second calendar reader.  The
producer (`scripts/build_options_catalyst_links.py::_macro_calendar`)
emits a `macro_calendar` envelope key built from
`_macro_candidates(asof, horizon_days)`; the consumer
(`scripts/build_options_command.py::_payoff_lab_catalyst`) reads the
same key and decides per-card.  Schema stays
`"mastermind.options_catalyst_links/v1"` and `spec_version` stays at
`SPEC_VERSION` (`"v1"` as defined at engine/options_catalyst_link.py:53) —
this packet is ADDITIVE: the only new field is `macro_calendar`, and
this packet never rewrites `spec_version` itself.  `engine/**` is
out of scope for this packet.

## Tri-state law (chip is ABSENT — never printed as "none" — when ANY)

`calendar` is None (load_catalyst_links returned None: missing file,
wrong schema, missing `macro_calendar`, or `fomc` not a list);
`expiration` or `card_asof` is not a YYYY-MM-DD ISO date;
`expiration > calendar["horizon_end"]` (calendar cannot see that far);
`calendar["asof"]` more than 7 calendar days older than `card_asof`
(exactly 7 days is acceptable).

## Two art directions (TP-0 2026-08-27)

DARK (`.oew-lab-cat` base rule — command-center tile, info-tinted text
when `is-before-expiry`, muted transparent fill when `is-clear`):
the chip carries no leading dot, no glow, no shadow; `border-radius`
is the page's own `--r-pill` token (the SAME family `.oew-aib-lede-chip`
ships), `color: var(--ink-info, var(--info))` is the info tint via
plain token references, background and border keep to `--tile` /
`--hair` tokens.  LIGHT (the `html[data-theme="light"] .oew-lab-cat`
override — research-workspace white material): same shape, fill flips
to `transparent` on both states so the chip never competes with the
cards' white material; `is-before-expiry` keeps the info-tinted
border, `is-clear` keeps the muted hairline.  @media (max-width:480px)
lets the chip wrap on mobile.  No JS, no runtime style injection, no
`title=` attribute (CI-guarded).  Color decisions stay on tokens so
the design-system forward-only ratchet (BLOCKING_RULES on ADDED lines)
never fires on this surface.

## Evidence matrix

`mockups/evidence/a-f03-w3-2-payoff-catalyst-chip/` (8 PNGs +
EVIDENCE.yml + manifest.json, BARE-filename `file` keys so
`check_ui_visual_evidence.py --diff-file` joins them to
`manifest_path.parent` correctly and exits rc 0;
`capture_page_evidence.py --routes /options.html --max-pages 1`;
`OEW_PAYOFF_LAB_FORCE_OPEN=1` for the open fold): 8/8 captured
across dark/light × EN/ZH × desktop/mobile; 0 console errors; 0
horizontal overflow; chip visible on every cell.  No "FOMC" /
"fomc" / "macro_calendar" / "before-expiry" tokens in visible text
(class token `is-before-expiry` is allowed in markup).  Fold's other
elements are byte-identical to the no-calendar render after the
chip's `<p>` is stripped via regex.  Tablet axis is OUT of this
packet's scope (8 PNGs, ruling E).

The `clear` art direction's visual evidence is NOT in this captured
set — the prior capture used a fixture that put a FOMC date inside
both SPY's and QQQ's (card_asof, expiration] windows, so all 8 cells
show the `is-before-expiry` state.  The CSS rule for `.is-clear` is
present and verified by `tests/test_options_payoff_lab_consumer.py
::test_render_with_calendar_exercises_both_chip_states`, which builds
two independent renders covering both states and asserts each
state's class token and 1 chip per render; a re-capture pass beyond
this packet's scope would close the visual side.

## One-night calendar lag

`site/options_catalyst_links/latest.json` is written by the producer
which runs AFTER `build_options_command` in `daily.yml`.  On the night
the producer first runs after merge the chip is absent on every card
until the next nightly; the loader's fail-soft contract preserves the
pre-W3-2 fold byte-for-byte until the new key lands.  Pre-F03-W3-2
callers that never pass `catalyst_links` get no chip and zero other
behaviour change.

**Why the daily.yml step order was not moved.**  Moving
`build_options_catalyst_links` to run before `build_options_command`
in `.github/workflows/daily.yml` would close the lag and let the chip
read the same-night calendar, but `.github/**` is OUT of scope for
this packet by ruling (FILES list) and by site law (the workspace's
`.github/**` carries merge authority and CI gates, never lane packets).
A future packet with `.github/**` scope can land the swap; this packet
documents the lag through the tooltip's "Calendar as of {calendar_asof}"
phrase and the fail-soft loader's behaviour.

## What this packet does NOT do

No new verdict, rank, score, or size (display-tier context only) — the
producer's `authority` block stays five-false.  No key added to the
pinned workspace loader (pinned BYTE-FOR-BYTE by
`tests/test_render_options_workspace_scope.py`); the new artifact is
loaded via `load_catalyst_links`, exactly like `load_intel_brief` /
`load_payoff_lab` / `load_skew_source`.  No touch to `engine/**`,
`scripts/build_options_payoff_lab.py`, the unrun-test config file,
`data/**`, `site/**`, `.github/**`, or any other template.  No
single-name chip — single-name catalyst chips are W3-1b territory, gated
on the BOUND+STALE ≥ 10 % ruling and not in this packet's scope.

## CI homes

Producer — `tests/test_build_options_catalyst_links.py` cases `i`, `j`
pin the envelope carries `macro_calendar` from the SAME
`_macro_candidates` list AND on the no-stage path too.  Consumer —
`tests/test_options_payoff_lab_consumer.py` (tri-state, exact chip
+ tip strings for one/two/three dates and clear state, loader
fail-soft contract, render fixture, fold unchanged, both chip
class tokens present on the page).  Workspace-scope —
`tests/test_render_options_workspace_scope.py` stays green.

## Acceptance grep (measured against the merge-base of this commit)

| grep | count |
|------|-------|
| `scripts/build_options_catalyst_links.py::macro_calendar` | ≥ 3 |
| `scripts/build_options_catalyst_links.py::Fed rate decision` | ≥ 1 |
| `scripts/build_options_command.py::^def load_catalyst_links(` | 1 |
| `scripts/build_options_command.py::^def _payoff_lab_catalyst(` | 1 |
| `templates/options.html.j2::data-payoff-catalyst-chip` | 1 |
| `templates/options.html.j2::.oew-lab-cat` | ≥ 6 |
| `templates/options.html.j2::html[data-theme="light"] .oew-lab-cat` | 2 |
| `grep -cE "FOMC" templates/options.html.j2` | 0 |
| `tests/test_build_options_catalyst_links.py::^def test_(i_envelope\|j_no_stage)` | 2 |
| `tests/test_options_payoff_lab_consumer.py::_payoff_lab_catalyst\|data-payoff-catalyst-chip` | ≥ 6 |
| `mockups/evidence/a-f03-w3-2-payoff-catalyst-chip/*.png` | 8 |

Tests pass on the proof line
(`tests/test_build_options_catalyst_links.py`,
`tests/test_options_catalyst_link.py`,
`tests/test_options_catalyst_links_nightly_shape.py`,
`tests/test_options_payoff_lab_consumer.py`,
`tests/test_render_options_workspace_scope.py`).
`check_design_system.py --mode enforce-added --diff-file`,
`check_runtime_style_injection.py`, and
`check_ui_visual_evidence.py --diff-file` all exit rc 0.

Checks are read by the seat at ratification; this body makes no claim
about their state.
