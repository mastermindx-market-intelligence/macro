# F03-W3-2 · Payoff-fold catalyst chip — research note

Implementation record for A-F03-W3-2 (the chip the F03-W3-1a producer
pre-staged in `site/options_catalyst_links/latest.json`).

## What it is

A single sentence chip on the index-card payoff fold (SPY / QQQ / IWM)
answering exactly one question: **does a Federal Reserve rate decision
land between this close and the expiry these structures use?**
Context only — never rank, score, or size.  Three terminal states,
all read off the same `macro_calendar` envelope:

| state | chip EN (chip ZH) |
|-------|-------------------|
| `before-expiry` | "Fed decision Oct 28 lands before this expiry" (美联储10月28日议息在到期前) |
| `clear` | "No Fed decision before this expiry" (到期前无美联储议息) |
| (absent) | (no element rendered — silence, never "none") |

The chip names the FIRST Fed decision inside the window
(`card_asof < d <= expiration`); the tooltip lists every date with
"and so does …" at two dates and "and so do …" + comma list at three
or more (the plural form is a disclosed, seat-ratified deviation from
the frozen literal; pinned by `…three_dates_verb_agreement_fixes`).
The helper sorts the filtered dates on its own end so a hand-injected
unsorted `fomc` still names the right "first" date.
The word "FOMC" never appears on the page.  The calendar's as-of
renders through the SAME human date-word formatters the chip uses
for its expiry text (`_payoff_lab_expiry_en/zh`), so ZH lands as a
single Chinese sentence rather than an ISO string.
## Why data-driven

Driven by the SAME `engine.event_calendar.fomc_decision_dates` list
the binder reads — no second calendar reader.  The producer emits a
`macro_calendar` envelope key from
`_macro_candidates(asof, horizon_days)`; the consumer
(`scripts/build_options_command.py::_payoff_lab_catalyst`) reads the
same key per-card.  Schema stays
`"mastermind.options_catalyst_links/v1"`; `spec_version` stays at
`SPEC_VERSION` (`"v1"` at engine/options_catalyst_link.py:53).  This
packet is ADDITIVE: the only new field is `macro_calendar`.
## Tri-state law (chip is ABSENT — never "none" — when ANY)

`calendar` is None; `expiration` or `card_asof` is not a YYYY-MM-DD
ISO date; `expiration > calendar["horizon_end"]` (calendar cannot
see that far); `calendar["asof"]` more than 7 calendar days older
than `card_asof` (exactly 7 is acceptable).
## Two art directions (TP-0 2026-08-27)

DARK (`.oew-lab-cat` base — command-center tile, info-tinted text
when `is-before-expiry`, muted transparent fill when `is-clear`): no
leading dot (the packet's `border-radius:50%` dot and `color-mix` tints
trip the design ratchet's radius-/colour-literal rules — dropped by
seat ruling, round 5), no glow, no shadow; `border-radius` is the page's own
`--r-pill` token, `color: var(--ink-info, var(--info))` is the info
tint via plain token references, background and border keep to
`--tile` / `--hair` tokens.  LIGHT (`html[data-theme="light"]
.oew-lab-cat` override — research-workspace white material): same
shape, fill flips to `transparent` on both states; `is-before-expiry`
keeps the info-tinted border, `is-clear` keeps the muted hairline.
@media (max-width:480px) wraps the chip on mobile.  No JS, no runtime
style injection, no `title=` attribute (CI-guarded).
## Evidence matrix

`mockups/evidence/a-f03-w3-2-payoff-catalyst-chip/` (8 PNGs +
EVIDENCE.yml + manifest.json, BARE-filename `file` keys so
`check_ui_visual_evidence.py --diff-file` exits rc 0;
`OEW_PAYOFF_LAB_FORCE_OPEN=1`): 8/8 across dark/light × EN/ZH ×
desktop/mobile; 0 console errors; 0 horizontal overflow; chip visible
on every cell.  Fixture uses a per-root expiration split (SPY
2026-10-30 → `is-before-expiry`, the 2026-10-28 decision inside; QQQ
2026-09-24 → `is-clear`; IWM no chain → absent) on ONE render, so the
8-cell matrix covers BOTH art directions (seat round 5 corrected these
dates to the captured fixture).  No "FOMC" /
"fomc" / "macro_calendar" / "before-expiry" tokens in visible text
(class token `is-before-expiry` is allowed in markup).  Fold's other
elements are byte-identical to the no-calendar render after the
chip's `<p>` is stripped via regex.  Tablet axis OUT (8 PNGs).
## Lag + NOT-do

`site/options_catalyst_links/latest.json` is written by the producer
which runs AFTER `build_options_command` in `daily.yml`.  The chip is
absent on every card until the next nightly lands the new key; the
loader's fail-soft contract preserves the pre-W3-2 fold byte-for-byte.
**Why the daily.yml step order was not moved:** moving
`build_options_catalyst_links` before `build_options_command` in
`.github/workflows/daily.yml` would close the lag, but `.github/**`
is OUT of scope by ruling (FILES list).  No new verdict, rank,
score, or size — producer's `authority` block stays five-false.  No
key added to the pinned workspace loader (pinned BYTE-FOR-BYTE by
`tests/test_render_options_workspace_scope.py`); new artifact is
loaded via `load_catalyst_links`, like `load_intel_brief` /
`load_payoff_lab` / `load_skew_source`.  No touch to `engine/**`,
`scripts/build_options_payoff_lab.py`, the unrun-test config, `data/**`,
`site/**`, `.github/**`, or any other template.  No single-name chip —
that is W3-1b territory, gated on the BOUND+STALE ≥ 10 % ruling.
## Acceptance grep + proof (measured against this commit's merge-base)

Producer — `tests/test_build_options_catalyst_links.py` (CI home: job
`options-catalyst-links` in `.github/ci/legacy-jobs.yml`) cases `i`,
`j`, `k` pin the envelope carries `macro_calendar` from the SAME
`_macro_candidates` list, on the no-stage path too, with non-fomc
candidates filtered out.  Consumer —
`tests/test_options_payoff_lab_consumer.py` (CI home: job
`options-payoff-lab-consumer`): tri-state, exact chip + tip strings,
ONE-render fixture (SPY before-expiry + QQQ clear + IWM absent), both
chip class tokens on the same page.  Workspace-scope —
`tests/test_render_options_workspace_scope.py` stays green.  Proof:
`grep -c macro_calendar scripts/build_options_catalyst_links.py` = 11;
`grep -c '^def load_catalyst_links(' scripts/build_options_command.py`
= 1; `data-payoff-catalyst-chip` = 1, `\.oew-lab-cat` = 6 and `FOMC`
= 0 in `templates/options.html.j2`; `grep -c
"_payoff_lab_catalyst\|data-payoff-catalyst-chip"
tests/test_options_payoff_lab_consumer.py` = 37; 8 PNGs in the
evidence dir; the 5-file pytest set (the three test files above plus
`tests/test_options_catalyst_link.py` and
`tests/test_options_catalyst_links_nightly_shape.py`, `-q`) = 133
passed; `check_design_system.py --mode enforce-added --diff-file`,
`check_runtime_style_injection.py`, `check_ui_visual_evidence.py
--diff-file` all rc 0.