# WTI physical evidence — dual-theme design adjudication

**Scope:** PR #8125, existing Oil detail, WTI/EIA Slice A only. **MISSION_COMPLETE:false / BUILT_NOT_PROVEN.**

**Adjudicator:** Sol, the authoring/product-review session. This is an explicit visual self-adjudication, not an independent peer approval, a whole-page redesign acceptance, or a release waiver. Independent rereview still must consume the result.

**Reviewed source:** `c3d048cef470f0b4d223daea3c4e41af05ae2fc9`. Integrated main: `dea858959c6f37122fd500dd673c44b271f19fa9`. All 24 canonical viewport captures were visually inspected in six labeled contact sheets derived from the original images, without retouching them. The manifest below, not those review aids, owns the original evidence.

## Governing reference and intended user task

The reference is the existing commodity-detail hierarchy and shared panel/token system, with the accepted R2 WTI/EIA convergence contract (Paper spec07, `2B89-0`). This is not a claim to reproduce every North Star screen. `docs/DESIGN_DOCTRINE.md` owns progressive disclosure; `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §§1/12 owns dark command-center and light research-workspace treatments; `AGENTS.md` theme-art-direction law requires both to be judged independently. There is no newly invented palette, font system, navigation owner or screenshot aesthetic baseline.

The customer task is to read weekly physical context without confusing it with a live quote or a price recommendation, notice that it is stale, and inspect its source/method. The visible order is: subject and limitation → evidence state → three clocks → four measurements → non-directional caveat → stale warning → native source disclosure. The source/method detail is not a second competing primary panel. Four-word English heading, short subtitle and a plain-word stale state keep the entry comprehensible.

## DARK TREATMENT

The WTI section is an opaque graphite panel with a hairline boundary. Its darker inset clock/value wells create luminance separation without bright tiles, neon accents, or decorative gradient charts. The section itself does not add glow or backdrop blur; the surrounding legacy page may use its own shared material. Semibold light values lead muted small labels. The stale badge and warning use warning ink, not red/green market-direction semantics. The receipt action uses the existing blue wayfinding ink, with a visible two-pixel keyboard outline.

Observed judgment: the section is subordinate to the existing decision/MTF pair but remains findable; the three time bases and four measures do not merge into one score. Dark EN and ZH preserve the same structure. The warning and source action remain distinguishable from data. The invalid-derived-label fix remains in force: physical balance is not inferred from an invalid z-score and is not colored as a buy signal.

## LIGHT TREATMENT

Light uses a white research-paper surface above a cool canvas. The explicit light selector supplies the shared card shadow and disables backdrop filtering; clock/value wells and the caveat switch to the cooler canvas fill rather than retaining dark inset slates. Fine neutral borders supply structure. Values use deep neutral ink; warning uses darker warning ink against white; wayfinding and focus retain a crisp blue ring rather than a bloom.

Observed judgment: white panel, cool wells and controlled shadow provide a deliberate paper hierarchy, not merely inverted colors. EN and ZH remain equally readable; the stale badge does not look like market strength/weakness. The section does not become a large saturated color field. Mobile expands vertically instead of squeezing labels and units into narrow columns.

## Mechanisms deliberately shared or different

| Mechanism | Dark | Light | Reason |
|---|---|---|---|
| Panel depth | Opaque graphite / darker inset wells | White paper / cool wells / shared shadow | Different luminance environments need different depth cues |
| Backdrop effect on this section | No new effect | Explicitly disabled | A physical-evidence panel should remain legible, not depend on the backdrop |
| Semantic warning | Warning ink and outline | Deep warning ink and outline | Evidence age is severity, never market direction |
| Focus | Crisp two-pixel blue outline | Crisp two-pixel blue outline | Interaction identity is invariant, not decorative material |
| Layout and data | Three clocks, four values, source disclosure | Same information and order | Theme must never alter the reading or omit limitations |
| Responsive behavior | One-column wells at the existing780px breakpoint | Same reflow | 390px readability rather than sideways scrolling |

Code reference: `templates/commodities.html.j2`, the `.oil-phys*` block and explicit `[data-theme='light']` overrides; `templates/_commodity_oil_physical.html.j2` for plain bilingual state/value/disclosure markup. Shared source is not redefined here.

## Theme-specific degraded-state treatments

| State | Dark treatment | Light treatment | Evidence boundary |
|---|---|---|---|
| STALE_LAST_KNOWN | Amber outline/text; dates and actual values retained in dark wells | Deep warning ink on white; dated values retained in cool wells | This is the actual state captured in all24 cells |
| PARTIAL_EVIDENCE | Warning-colored status, usable verified fields retained, missing fields not zero | Same disclosure with light warning ink and light well structure | VM/template tests; not a live browser claim for this state |
| METHOD_NOT_VERIFIED | Muted qualification, not confidence-green; no qualified claim | Neutral gray qualification on white; same method boundary | Source/template and unit coverage only |
| NOT_CONNECTED / withheld values | Neutral dashed empty well plus plain reason; other price/technical views remain | White/cool empty well, hairline structure, same plain reason | No synthetic zeros or blank success panel; unit/template coverage |
| FETCH_ERROR | Source-unavailable wording; no carried neutral supply conclusion | Same wording with light neutral materials | Not a simulated provider outage in the browser matrix |

A date, source, or receipt failure must not turn into a new market interpretation. The actual captured physical observation remains2026-09-18, distinct from daily analysis2026-09-25. Neither theme presents the current quote clock as a refreshed EIA report. Unsupported publication/receipt instants remain unavailable in disclosure.

## Actual visual findings and repairs

The previous focus captures could report focused/captured while a delayed unrelated oscillator-help sheet dimmed the page. Reviewing the images, not just the manifest counts, exposed it. The exact old driver reproduced the defect. The repaired driver performs Enter→Tab to the EIA link→Shift+Tab→Enter inside the source disclosure and hit-tests the focused text area after screenshot-driven scrolling. It does not hide a tooltip, alter product CSS, or patch shared navigation.

The current captures show clear source focus in both themes and languages. Native centered scrolling makes the tablet/desktop subject readable above the fixed assistant launcher. That is a review position, not a global launcher repair. On mobile the unchanged launcher still occupies the far-right edge of the source row, while its text/triangle and useful keyboard ring remain exposed. At other scroll positions the shared launcher can overlap surrounding content. This inherited behavior remains a separate global-shell follow-up, not a claim of pristine whole-page acceptance.

## Per-cell visual adjudication

The eight required desktop/mobile × EN/ZH × dark/light rest cells and their eight focus counterparts were reviewed. The existing canonical tablet axis adds eight more cells. Each row below names both original, hashed images; the judgments concern this WTI section, not every adjacent legacy widget.

| Viewport / locale / theme | Rest original | Focus original | Visual judgment |
|---|---|---|---|
| desktop 1440 / en / dark | [07c1ad4a2012](captures/07c1ad4a201241a5.png) | [0f19f16ff074](captures/0f19f16ff07498f3--focus.png) | Graphite/inset hierarchy separates3 clocks and4 values; stale warning reads first; focused disclosure is unobscured. |
| desktop 1440 / en / light | [0494dc27dfdc](captures/0494dc27dfdc270e.png) | [bc14a7d4962b](captures/bc14a7d4962b1165--focus.png) | White paper, cool wells and shadow are distinct; units and dates readable; crisp focus with no dark slate. |
| desktop 1440 / zh / dark | [55516a0401a9](captures/55516a0401a9a193.png) | [d05b620b9d2c](captures/d05b620b9d2c3245--focus.png) | Chinese title/state preserve meaning and spacing; neutral supply labels; no untranslated balance word. |
| desktop 1440 / zh / light | [54ca948e3a0a](captures/54ca948e3a0a518c.png) | [b029b3d77f0c](captures/b029b3d77f0c194f--focus.png) | Chinese white-paper layout remains balanced; clock labels and warning fit; ring and disclosure clear. |
| tablet 820 / en / dark | [85eed6dec79e](captures/85eed6dec79e864b.png) | [30f9a534c099](captures/30f9a534c09957ba--focus.png) | At820px the3/4-column rhythm remains legible; centered review position clears warning from launcher. |
| tablet 820 / en / light | [9613e93ced47](captures/9613e93ced474386.png) | [f3766660e48b](captures/f3766660e48b7128--focus.png) | White surface stays distinct from cool context; no clipped metrics; source focus remains visible. |
| tablet 820 / zh / dark | [9a7664272796](captures/9a76642727965cfd.png) | [21bd4ed46909](captures/21bd4ed469093833--focus.png) | Shorter localized copy retains the same hierarchy; values and units remain distinct; no tooltip dimming. |
| tablet 820 / zh / light | [d267510988d3](captures/d267510988d3ec0d.png) | [51a0f82547ae](captures/51a0f82547aeb470--focus.png) | Chinese clock/value groups remain aligned with neutral supply semantics; source ring clear. |
| mobile 390 / en / dark | [de154c449c8f](captures/de154c449c8fe861.png) | [50a61486d30f](captures/50a61486d30f6dcd--focus.png) | One-column wells preserve units and dates; warning wraps; focus text visible, launcher overlaps only far-right edge. |
| mobile 390 / en / light | [f19ebbcb45ec](captures/f19ebbcb45eca4f8.png) | [f3594186e6c5](captures/f3594186e6c59c3f--focus.png) | White/cool stacked rhythm and breathing space retained; no squeezed metrics; clear source text/ring. |
| mobile 390 / zh / dark | [4090a74655a4](captures/4090a74655a496b6.png) | [c9f29098c0fa](captures/c9f29098c0fac2b7--focus.png) | Localized state/caveat wrap without clipping; numerical signs unchanged; no oscillator sheet. |
| mobile 390 / zh / light | [b692cdbc3554](captures/b692cdbc35549d9b.png) | [35fcbb913946](captures/35fcbb91394633a7--focus.png) | Readable localized stacked wells; no dark material residue; source text remains available beside launcher. |

## Supporting checks and scope of verdict

The canonical manifest is `capture.json`, SHA256 `5b9bf7342aa25e46922952b94752926dc2562a3510b4c690cac60f1dad2a2166`; all24 image byte counts and SHA256 values were verified. A supplementary computed-style sample covered19 text instances per theme against their nearest opaque ancestor: minimum5.17:1 dark and4.59:1 light. The diagnostic handles both byte-channel `rgb()` and unit-channel `color(srgb ...)`. This is not a complete alpha-compositing, antialiasing, contrast or accessibility audit.

**Visual self-adjudication:** the bounded WTI section passes the inspected hierarchy/material/EN-ZH/responsive/rest-focus criteria at the recorded states. **Release disposition remains HELD pending independent rereview and exact-current-head CI.** No screen-reader,200%-zoom,live-provider,auth,account-sync,persistence,or whole-page aesthetic acceptance is claimed. Other degraded states still need actual browser/provider-path acceptance when that scope is commissioned. R2 and North Star parent missions remain incomplete.
