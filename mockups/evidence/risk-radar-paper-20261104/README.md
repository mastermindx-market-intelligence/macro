# Risk Radar — Paper implementation qualification

## Source and scope

Presentation source: [Macro 9b424c673bd5e0d6c5f5aaa48caeca2d130c6134](https://github.com/mastermindx-market-intelligence/macro/tree/9b424c673bd5e0d6c5f5aaa48caeca2d130c6134).
This integrated source preserves main at affa0fd2e68723efc9e2cbc0e7c791ab70f5a53d.

Design: [Paper Risk Radar system, primary desktop 1-0 and related mobile/evidence boards](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-1-0).
The original primary JSX is preserved in research/design_candidates/risk_radar_paper_20261104/primary.jsx.

This is source qualification for the US Risk Radar shared by standalone Macro and
the beta Macro consumer. These local fixtures contain no account or portfolio
data. They do not establish live publication, authenticated access, formal GitHub
approval, or production acceptance.

## Verified behavior

- 175 complete workspace browser checks; zero page errors.
- 134 focused workspace, envelope-integration and dashboard-render tests passed
  at integration source 734f54b. The subsequent source delta changes only two
  severity-ink CSS rules and the browser assertions that verify them.
- 32 of 32 canonical cells captured: eight resting cells plus real driver hover,
  horizon focus and leadership disclosure focus in each cell.
- Dark/light and EN/ZH layouts; widths 320, 390, 768 and 1440; text-only 200%
  resize at 390 and 1440 in both languages.
- Keyboard navigation, visible focus, same-node inspector navigation,
  help/date retention and restoration, scroll return and reduced motion.
- Risk-severity ink remains identical between languages in both themes and
  at every tested width; high and calm remain visually distinct.
- Missing/malformed values fail closed; zero remains a valid value.
  Native incomplete, contradictory and older-input messages remain literal.
- One or two sentiment lenses retain their original numeric values and pins,
  with all source EN/ZH scale labels beside each available instrument.
- All design additions pass the design-system ratchet; runtime-style injection
  remains within its frozen allowances; all 159 template/site pairs match.

The resize probe doubles computed font sizes in the isolated test document.
It checks fit, horizon readability and text separation from the stance icon.
Its four screenshots are in text-resize/.

## Two immutable input snapshots

The canonical matrix deliberately reproduces the original November 2 reading
using committed inputs at cefa917e39fc249d8c57dcacab7d4a9ab51d24ae. The presentation
itself is the integrated source above. source-inputs.json records the input
hashes and presentation hashes; those presentation bytes were compared with
the integrated commit before this record was written.

A second smoke run uses the final presentation with inputs from integration
commit 734f54bae23cf5ef15c6adecbebe2d018bad1f47. It renders the November 3 reading, Caution and 86/100, with 5%, 12% and 22%
for the three horizons. It opens all four driver views, checks width fit at
desktop/mobile, and records zero page errors. See latest-snapshot-smoke.json,
latest-source-inputs.json and the two latest-*.png captures. The exact bounded
smoke script is retained here; it uses the existing fixture builder's output
and blocks all off-origin requests.

These dates and numbers describe fixtures, not a claim about a live market
reading. Paper's illustrative values are never substituted into production.

## Resting capture matrix

| Viewport | Language | Theme | Capture |
|---|---|---|---|
| desktop | en | dark | [PNG](shots/3644395b745c347f.png) |
| desktop | en | light | [PNG](shots/a8b02370b01d94cc.png) |
| desktop | zh | dark | [PNG](shots/ceb27cc4be189766.png) |
| desktop | zh | light | [PNG](shots/b92819c9a85ae3ea.png) |
| mobile | en | dark | [PNG](shots/8b0f72a6977ae862.png) |
| mobile | en | light | [PNG](shots/cd9c9d5a575c1993.png) |
| mobile | zh | dark | [PNG](shots/d4badddb5a4adadb.png) |
| mobile | zh | light | [PNG](shots/75747a3d453794d9.png) |

The manifest's anonymous access gaps for authenticated tiers are intentional.
Its local target has no nearest Git directory, so the capture tool truthfully
leaves that provenance field unavailable. Source attribution is established
separately by the immutable source and input hashes above. The capture schema
and its measurements are unmodified.

## Existing EW-P4 evidence

The existing probe regenerated all 68 static Radar/Sector Central cases and
all 16 keyboard-disclosure cases at source 734f54bae23cf5ef15c6adecbebe2d018bad1f47.
Its original 31 bound render/fixture paths remain byte-identical in the final
source; every actual Git blob comparison is equal. The later stylesheet-only
severity-ink repair does not affect that static probe. Its historical fixture
base remains
1d253e1d25f22c61d1bcf8126b13b0229f26ccbd.

That static probe does not execute the Risk Radar workspace enhancement and
does not substitute for the 175-check suite or the two requested live paths.

## Release and acceptance still owed

The original source carrier remains sol/web-risk-radar-paper-live-20261104-c3.
A real non-author must approve the final exact PR head and independently arm
the existing merge-on-green controller after checking CI and holds. Then verify
the actual merge, covering render/generated publication, served assets and
browser behavior on both www.mastermind-x.com/macro.html and
beta.mastermind-x.com/macro.html. No new watcher or release mechanism is added.


## CI repair qualification — 2026-11-05 UTC

Repair source `530a11df95e2ed619b0a98e233bcd971c47ffd78` changes only the bilingual sentiment disclaimer and its obsolete sizing-copy regression, plus the implementation record. The changed regression was observed red before repair and green after; the unchanged source claims guard passes. The two-file local suite returned 42 passed, 4 skipped and 2 setup errors because this sparse checkout lacks the market-data store for unrelated real-feature fixtures; those are not reported as passes and no collectors were run.

The existing EW-P4 probe actually regenerated 68 static cases and its 16 keyboard cases at that repair source; all 31 bound render/fixture Git blobs match and the source-equivalence regression passes. Its refreshed receipt is under `research/evidence/ew_p4_descriptive_ui_20261031/receipt.json`. The original 175 workspace checks and 32 canonical captures remain historical qualification at their stated source. They were not rerun or relabelled for this copy-only delta. CSS, JavaScript, calculations, feeds, access controls and the original review request remain unchanged. Hosted candidate CI, formal approval, independent release and both live-site acceptances remain separate unproven gates.
