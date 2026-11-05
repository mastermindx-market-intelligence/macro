# Intraday Flow W11 — evidence receipt

S1 rig: Playwright against fixture feeds on the real `body.page-intraday-flow` page, plus the round-2 overlay-column crops in the same run. `data-theme` / `data-lang` applied via `setTheme` / `setLang` (mismatch refuses). Overlays `.ift-aurora`, `.mx5-aurora`, `.sky-fx`, `#mmb-root`, `#mmb-boot` are removed before each shot. `window.__skyDeck = true`. `prefers-reduced-motion: reduce`. At-rest text is read from computed styles, never from HTML source. PNGs are content-addressed `sha256[:16].png`.

Recapture: `python3 mockups/evidence/intraday-flow-w11/capture.py`

**fixture N = 12.** The full-page fixture holds 12 leaders. Default board shows 8 of 12 with `See all 12` / `查看全部 12 只`; expansion renders exactly 12 rows. It is count-true. The round-2 counted-control crop still shows the page's "Showing 8 of 116" sentence, because that crop is the control, not the fixture census.

Captured 2026-09-21T18:43:47Z at committed head `a53867877c412aa8f538ea94bfee921ff9508540`.
74 cells, 74 overlay-clean. Page anchors: intraday_flow.html#hero, intraday_flow.html#board. Each anchor carries the eight rest cells (desktop/mobile × en/zh × dark/light). Named states, See-all hover/focus, and the six round-2 crops are force-state rows on the hero anchor. They are not extra pages.

## DARK TREATMENT

Command center. Page canvas is the dark sheet, panels are graphite with a hairline and a restrained inset. The stamp is muted instrument type. The `?` control is a small ring; the feed-status tip is an opaque panel so the desk does not wash through. Tape chips are filled info pills on the dark sheet. See-all inherits muted and underlines. Degraded `No read` sits in the aside lane with no glow.

## LIGHT TREATMENT

Research workspace. Forced light theme on the page. The canvas is a cool gray, panels are white, and elevation comes from a shadow instead of a glow. See-all is an ink link with a hover underline — an action on white, not a glow. Stamp type is muted. The `?` control is a white chip with a hairline. Tape chips ghost/hairline in light — recessive by design (`大单` / `新建仓` are transparent ground, a hairline, and muted ink — not filled pills).

## Which mechanisms intentionally differ

Shared: information architecture, bilingual sentences, the See-all control, the feed-status tip, tape-chip words, dealer-line geometry, skeleton geometry, and stance lanes.

Intentionally different material: dark depth is luminance and a restrained edge; light depth is a white plane, a hairline, and a drop shadow. See-all stays muted on dark and becomes an ink link on light. The stamp `?` is a ring on graphite and a white chip on the research canvas. Token substitution alone is not the light design.

**Degraded (light and dark):** a quotes outage during the session paints `No read` / `暂无判断` with `Prices aren't coming through — no read on this name right now` / `行情未送达——该标的暂无判断`. no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11.

Round-2 crops bound in this packet: `stamp-tip-dark-en`, `stamp-tip-light-en`, `control-dark-en`, `control-light-en`, `tip-row-zh`, `outage-stance-en`.
