# MO-J1A — affected-company continuation: visual evidence provenance

Read this before judging the captures. Two manifests live here and they show
different things on purpose.

## 1. `manifest.json` — the design, rendered from the committed test fixture

Captured from `site/transmission.html` built with
`tests/fixtures/transmission/chain_state.json` substituted for the production
chain state. **Why:** every one of the 7 production transmission chains is
`dormant` at this revision (verified on `origin/main`,
`data/transmission/chain_state.json`, `asof: 2026-09-25`), and the ruling for
this packet is explicit that a dormant chain gets no companies block and no
CTA. On the page the product serves today the new block therefore renders
nothing at all, so a reviewer looking at the served page could not judge the
design in either theme. The fixture carries 3 non-dormant chains, which render
11 channel disclosures and 36 company links — the real component, real CSS,
real bilingual copy, in a real browser.

The substitution is a render-time input swap only. No capture was edited, no
cell was synthesized, and the production artifact was restored immediately
after the build (`data/` is untouched by this PR).

## 2. `dormant_served_state/manifest.json` — the real served page today

Captured from the same page built with the **real committed production chain
state**. All 7 chains dormant, so the page carries zero `cm-cos` blocks. This
is the required failure state: the continuation must be silent, not empty-shelled,
when no chain is active. Both manifests are the full eight-cell matrix
(desktop/mobile x en/zh x dark/light).

## 3. Why there are no hover/focus interaction cells

This PR adds no per-component `:hover` or `:focus` rule. The page already
carries one global `:focus-visible` outline that covers every focusable element
in the block, and no other link on this page defines its own hover. An earlier
round added three such rules; they were removed as redundant outliers, which
also removes a presentation claim that could not honestly be captured —
interaction states inside a collapsed `<details>` are not reachable by the
capture tool (force states apply to `body`, and a closed disclosure hides its
content from `locator.hover()`).

## 4. What these captures do NOT prove

They do not prove the served journey. The served page at
`https://mastermind-x.com/transmission.html` cannot show this block until a
transmission chain leaves `dormant`, and the operator's VPS pull cron is held
(`# MMX-DISK-TRIAGE-HOLD`, reported on #6902). Acceptance of "visible
transmission desk" stays open until both conditions clear.
