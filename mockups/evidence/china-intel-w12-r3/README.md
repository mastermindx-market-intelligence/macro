# china_intel W12 r3 — canvas-true evidence matrix

Provenance: captured at committed head `090ee9a4c602db82d52cc37b065680468f5c4e8f`.
Manifest `sha` == `git rev-parse HEAD` at capture time (porcelain-empty).

S1 rig: real `report_base` page (body `{ background: var(--bg) }`, nav family,
`window.__skyDeck = true`), Playwright `setTheme`/`setLang` (mismatch refuses),
overlay selectors removed, reduced-motion, **canvas-context viewport regions**
(element box + 72px page margin — never a bare-element screenshot on a
transparent body), settle-before-capture (`document.fonts.ready` then
`getAnimations({subtree:true})` force-finished; SETTLE column asserts
effective opacity == 1 on the content root and a sampled row; unsettled
cells REFUSED). Content-addressed twins (`sha256[:16].png` + alias).
Fixture-rendered (sparse tree: no `data/` / `site/`).

## Art direction

**DARK TREATMENT:** command center — graphite panels, instrument-calm chips,
restrained amber on the staleness/outage chip, luminance depth on dated
brief cards and the method band. Regime tilt is carried by the WORD
(Risk-on vs Neutral), the SIGNED NUMBER (+0.40 vs +0.00), and a
link-tinted ring on `.mc.hot`. Hex on `b.on` is computed-style only;
visible-ink hex parked per packet D8.

**LIGHT TREATMENT:** research workspace — cool canvas, white card material,
hairline borders, shadow instead of glow; same IA, chip states, dates,
source chips, and the same word + signed-number + ring tilt. Warn bloom
is suppressed; ink + hairline carry the stale/outage state. Hex remains
computed-style only; visible-ink hex parked per packet D8.

**Intentional differences:** glow vs shadow; warn bloom vs ink hairline.
Shared: five-state B1 chip, dated-card identity (as-of + source chip),
method-band directory, regime tilt (word + signed number + ring;
ZH-flipped computed-style hex parked per D8).

Theme-specific degraded states are captured in BOTH themes
(`degraded-dark-*` / `degraded-light-*`).

## Visible-ink follow-up (F3) — root cause

r3 named `.cmdbar .mc span { color: var(--muted) }` as outranking
`.regime .on` on `<b class="on">`. That host match is false (`<b>` is
not a `span`; `.cmdbar .mc:not(.regime) b` is excluded by `.regime`).

Cascade probe (getComputedStyle + CDP `CSS.getMatchedStylesForNode`
on the regime-tilted fixture, dark EN):
- `b.on` computes `rgb(31, 154, 85)` via `.regime .on` (the computed-style
  gate is true of the host).
- Glyphs live in the inner `t()` spans (`span.l-en` / `span.l-zh`). The
  only matched color rule on those spans is `.cmdbar .mc span { color:
  var(--muted) }` → `rgb(139, 147, 161)` (`--muted` `#8b93a1`). Inherited
  `.regime .on` loses to that own-color declaration.
- Hex is computed-style only; visible-ink hex parked per packet D8.
  No CSS change this round.

## CORRECTIONS (r3 release record)

- Analogs ship `Ignore` / 「可忽略」 lawfully (packet line 27 doctrine
  vocabulary). The r2 DONE-map line "Analogs keep Watch" is superseded.
  No template change.

## Horizontal page scroll at 390w

- EN: overflow=False scrollWidth=390 clientWidth=390
- ZH: overflow=False scrollWidth=390 clientWidth=390

## Cells

| id | fixture | theme | lang | vp | overlay | SETTLE | judged |
|---|---|---|---|---|---|---|---|
| `fp-dark-en-1440` | baseline | dark | en | desktop | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-dark-en-390` | baseline | dark | en | mobile | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-dark-zh-1440` | baseline | dark | zh | desktop | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-dark-zh-390` | baseline | dark | zh | mobile | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-light-en-1440` | baseline | light | en | desktop | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-light-en-390` | baseline | light | en | mobile | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-light-zh-1440` | baseline | light | zh | desktop | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `fp-light-zh-390` | baseline | light | zh | mobile | clean | settled op=1 | full-page baseline — lead brief above fold, B1 chip + as-of, command 8+expander, stances |
| `b1-state1-dark-en` | b1-fresh | dark | en | desktop | clean | settled op=1 | state-1 suppressed — labeled absence: cmdbar without the chip |
| `b1-state1-dark-zh` | b1-fresh | dark | zh | desktop | clean | settled op=1 | state-1 suppressed — labeled absence: cmdbar without the chip |
| `b1-state1-light-en` | b1-fresh | light | en | desktop | clean | settled op=1 | state-1 suppressed — labeled absence: cmdbar without the chip |
| `b1-state1-light-zh` | b1-fresh | light | zh | desktop | clean | settled op=1 | state-1 suppressed — labeled absence: cmdbar without the chip |
| `b1-state2-dark-en` | b1-mixed | dark | en | desktop | clean | settled op=1 | state-2 mixed — names a still-current feed; chip beside as-of stamp |
| `b1-state2-dark-zh` | b1-mixed | dark | zh | desktop | clean | settled op=1 | state-2 mixed — names a still-current feed; chip beside as-of stamp |
| `b1-state2-light-en` | b1-mixed | light | en | desktop | clean | settled op=1 | state-2 mixed — names a still-current feed; chip beside as-of stamp |
| `b1-state2-light-zh` | b1-mixed | light | zh | desktop | clean | settled op=1 | state-2 mixed — names a still-current feed; chip beside as-of stamp |
| `b1-state3-dark-en` | b1-all_stale | dark | en | desktop | clean | settled op=1 | state-3 all-stale — no feed is current |
| `b1-state3-dark-zh` | b1-all_stale | dark | zh | desktop | clean | settled op=1 | state-3 all-stale — no feed is current |
| `b1-state3-light-en` | b1-all_stale | light | en | desktop | clean | settled op=1 | state-3 all-stale — no feed is current |
| `b1-state3-light-zh` | b1-all_stale | light | zh | desktop | clean | settled op=1 | state-3 all-stale — no feed is current |
| `b1-state4-dark-en` | b1-outage | dark | en | desktop | clean | settled op=1 | state-4 outage — timestamps unavailable, never suppressed; chip beside as-of stamp |
| `b1-state4-dark-zh` | b1-outage | dark | zh | desktop | clean | settled op=1 | state-4 outage — timestamps unavailable, never suppressed; chip beside as-of stamp |
| `b1-state4-light-en` | b1-outage | light | en | desktop | clean | settled op=1 | state-4 outage — timestamps unavailable, never suppressed; chip beside as-of stamp |
| `b1-state4-light-zh` | b1-outage | light | zh | desktop | clean | settled op=1 | state-4 outage — timestamps unavailable, never suppressed; chip beside as-of stamp |
| `b1-state5-dark-en` | b1-undated | dark | en | desktop | clean | settled op=1 | state-5 undated-among — dated oldest + undated named; clause-split |
| `b1-state5-dark-zh` | b1-undated | dark | zh | desktop | clean | settled op=1 | state-5 undated-among — dated oldest + undated named; clause-split |
| `b1-state5-light-en` | b1-undated | light | en | desktop | clean | settled op=1 | state-5 undated-among — dated oldest + undated named; clause-split |
| `b1-state5-light-zh` | b1-undated | light | zh | desktop | clean | settled op=1 | state-5 undated-among — dated oldest + undated named; clause-split |
| `regime-tilted-dark-en` | regime-tilted | dark | en | desktop | clean | settled op=1 | F3 tilted EN — word (Risk-on) + signed number + link-tinted ring; hex is computed-style only; visible-ink hex parked per packet D8 |
| `regime-tilted-light-en` | regime-tilted | light | en | desktop | clean | settled op=1 | F3 tilted EN — word (Risk-on) + signed number + link-tinted ring; hex is computed-style only; visible-ink hex parked per packet D8 |
| `regime-tilted-dark-zh` | regime-tilted | dark | zh | desktop | clean | settled op=1 | F3 tilted ZH — word (偏好风险) + signed number + link-tinted ring; lane-symmetric; hex is computed-style only; visible-ink hex parked per packet D8 |
| `regime-tilted-light-zh` | regime-tilted | light | zh | desktop | clean | settled op=1 | F3 tilted ZH — word (偏好风险) + signed number + link-tinted ring; lane-symmetric; hex is computed-style only; visible-ink hex parked per packet D8 |
| `regime-neutral-dark-en` | regime-neutral | dark | en | desktop | clean | settled op=1 | Neutral tilt — untinted is the honest neutral, not a defect |
| `regime-neutral-dark-zh` | regime-neutral | dark | zh | desktop | clean | settled op=1 | Neutral tilt — untinted is the honest neutral, not a defect |
| `regime-neutral-light-en` | regime-neutral | light | en | desktop | clean | settled op=1 | Neutral tilt — untinted is the honest neutral, not a defect |
| `regime-neutral-light-zh` | regime-neutral | light | zh | desktop | clean | settled op=1 | Neutral tilt — untinted is the honest neutral, not a defect |
| `brief-card-dark-en` | baseline | dark | en | desktop | clean | settled op=1 | Dated brief card with as-of + source chip |
| `brief-card-dark-zh` | baseline | dark | zh | desktop | clean | settled op=1 | Dated brief card with as-of + source chip |
| `brief-card-light-en` | baseline | light | en | desktop | clean | settled op=1 | Dated brief card with as-of + source chip |
| `brief-card-light-zh` | baseline | light | zh | desktop | clean | settled op=1 | Dated brief card with as-of + source chip |
| `foldin-dark-en` | foldin | dark | en | desktop | clean | settled op=1 | No-asof fold-in — 'kept on the lead brief' line |
| `foldin-dark-zh` | foldin | dark | zh | desktop | clean | settled op=1 | No-asof fold-in — 'kept on the lead brief' line |
| `foldin-light-en` | foldin | light | en | desktop | clean | settled op=1 | No-asof fold-in — 'kept on the lead brief' line |
| `foldin-light-zh` | foldin | light | zh | desktop | clean | settled op=1 | No-asof fold-in — 'kept on the lead brief' line |
| `degraded-dark-en` | degraded | dark | en | desktop | clean | settled op=1 | Degraded-AI why — enum→words, never the enum |
| `degraded-dark-zh` | degraded | dark | zh | desktop | clean | settled op=1 | Degraded-AI why — enum→words, never the enum |
| `degraded-light-en` | degraded | light | en | desktop | clean | settled op=1 | Degraded-AI why — enum→words, never the enum |
| `degraded-light-zh` | degraded | light | zh | desktop | clean | settled op=1 | Degraded-AI why — enum→words, never the enum |
| `f8-tip-dark-en` | baseline | dark | en | desktop | clean | settled op=1 | F8 full-name tip OPEN on a truncated name |
| `f8-tip-dark-zh` | baseline | dark | zh | desktop | clean | settled op=1 | F8 full-name tip OPEN on a truncated name |
| `f8-tip-light-en` | baseline | light | en | desktop | clean | settled op=1 | F8 full-name tip OPEN on a truncated name |
| `f8-tip-light-zh` | baseline | light | zh | desktop | clean | settled op=1 | F8 full-name tip OPEN on a truncated name |
| `f11-zh-tip-dark` | baseline | dark | zh | desktop | clean | settled op=1 | F11 ZH 「暂无中文摘要」 with the EN tip OPEN |
| `f11-zh-tip-light` | baseline | light | zh | desktop | clean | settled op=1 | F11 ZH 「暂无中文摘要」 with the EN tip OPEN |
| `method-band-dark-en` | baseline | dark | en | desktop | clean | settled op=1 | Method band post-F9 — no Ignore stance |
| `analogs-dark-en` | baseline | dark | en | desktop | clean | settled op=1 | Analogs L1 stance as shipped (Ignore); sibling L1 panels keep Watch; method-band has none |
| `method-band-dark-zh` | baseline | dark | zh | desktop | clean | settled op=1 | Method band post-F9 — no Ignore stance |
| `analogs-dark-zh` | baseline | dark | zh | desktop | clean | settled op=1 | Analogs L1 stance as shipped (Ignore); sibling L1 panels keep Watch; method-band has none |
| `method-band-light-en` | baseline | light | en | desktop | clean | settled op=1 | Method band post-F9 — no Ignore stance |
| `analogs-light-en` | baseline | light | en | desktop | clean | settled op=1 | Analogs L1 stance as shipped (Ignore); sibling L1 panels keep Watch; method-band has none |
| `method-band-light-zh` | baseline | light | zh | desktop | clean | settled op=1 | Method band post-F9 — no Ignore stance |
| `analogs-light-zh` | baseline | light | zh | desktop | clean | settled op=1 | Analogs L1 stance as shipped (Ignore); sibling L1 panels keep Watch; method-band has none |

Recapture: `python3 mockups/evidence/china-intel-w12-r3/capture.py`
