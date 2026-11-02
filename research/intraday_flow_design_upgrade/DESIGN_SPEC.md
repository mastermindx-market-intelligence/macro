# Intraday Flow — implementation design specification

Status: implemented candidate; independent review, editable Paper design and served-release acceptance remain open.
Authority: Chairman's Intraday Flow redesign request; subordinate to MASTER_PLAN.md in this directory.
Source base: macro f754bdee6b803b18191841863c35527c0a74571e.

## Intended experience

A focused scanning desk for the existing fixed universe of institutional leaders.
The page should answer what the model recorded, what evidence is available, and
where to inspect the reasoning. The six deterministic classification keys retain
their original meanings. This design creates no ranking, confidence, trade signal,
freshness threshold or exchange-calendar authority.

The visible order is page identity and session window; a brief status and source
provenance line; six compact classification filters; one eight-row scan; and
selected-name evidence. The repeated hero score, composition ribbon and three
spotlight cards are retired. The complete population remains behind a counted
See all control. The full rule and dealer evidence remains available for every name.

## Two art directions

DARK: calm dark canvas and raised working surfaces; neutral hairlines; restrained
semantic ink; stronger essential explanation text; a filled, quiet options badge.
LIGHT: cool research canvas, white surfaces, neutral borders and small material
shadows; a quiet selected-row fill; transparent hairline options badges.
Both preserve identical ordering, data meaning, navigation, spacing scale and controls.
The canonical theme.css palette and typography remain authoritative. Future spacing,
radius and motion token fallbacks exactly match MASTER_PRODUCT_DESIGN_SYSTEM_V1.
No new token root, raw palette, colored container rails or runtime stylesheet is used.

## Layout and disclosure

Desktop 1440: title/session; compact status/provenance; six stage filters; board
with theme menu, grouping, search and column sorting; a 320 px selected-name panel.
The first candidate is targeted within 300 px below navigation, with six complete
rows visible at 1440 x 900. The side panel identifies the selected name and discloses
the recorded classification, required-input availability, observed source times,
stock-overview link and full-evidence action.

The theme menu contains all nine existing choices: All, Mag7, AI infrastructure,
AI software, AI semiconductors, semicap equipment, reshoring, defense and power grid.
An explicit active-filter summary and reset appear when filtering. Empty results
have a recovery action; zero remains an observed value, separate from unavailable.

At 390 px, the side panel gives way to full-width inline evidence. Stage filters
scroll horizontally with an explicit cue. Price and Activity keep visible labels.
Evidence buttons are at least 44 px high and sit to the left, clear of the existing
floating assistant's action area. The full-width record preserves the user's place.
No page-wide horizontal scroll is permitted.

## Trust and provenance

The session badge names the existing ET clock window. It does not imply an
exchange-calendar check. All classification displays are qualified as Recorded.
Unavailable current prices receive a prominent plain-language statement; optional
missing options flow does not erase observed prices. Source availability does not
assert freshness.

The original coverage-aware three-feed status and canonical lens are retained.
Board construction time is distinct from the price source clock and volume source
clock. Price provenance uses the producer's meta.source_asof, which is the median
real quote clock; per-name evidence uses ts only when tsSynthetic is not true.
Volume provenance uses as_of and the producer's stale flag. No age policy is added.
Missing clocks remain unavailable; the browser's retrieval time is never substituted.

## Advanced evidence landings

| Prior capability | New landing |
|---|---|
| Existing classification and reason | Scan row and selected-name panel, explicitly recorded |
| Price and session activity | Scan columns / labeled mobile fields |
| Approximate call-only direction and unknown side | Full tape evidence, retaining ncp versus net_all distinction |
| Unusual options size flags | Full tape evidence, bilingual badges |
| Seven rule inputs and unknown/false/true state | Full evidence, unchanged computeLegs output |
| Dealer regime, walls, pinning and expected move | Full dealer block |
| Nightly stop, VWAP, session low, ATR and buy zone | Reference levels block |
| Methodology and limitations | Collapsible field guide |
| Complete 116-name population | Counted expansion, preserving filters and ordering |

## Interaction and accessibility

Stage and theme controls are native buttons with aria-pressed. Theme selection closes
its native-details menu; Escape closes it and returns focus. Sorting uses keyboard
buttons and aria-sort, with names/labels initially ascending and numbers descending.
Row and side-panel evidence controls expose aria-expanded and aria-controls.
Data or language renders preserve expanded rows and the focused evidence button.
Reset returns focus to search; counted expansion returns focus to its replacement
control. EN/ZH strings and labels are carried by the existing language mechanism.
Reduced motion removes page animations; the skeleton announces loading once per host.

## Regression migration

The old spotlight animation tests are superseded because that component is removed.
They are replaced by executed burst coalescing, display provenance, ordering, single
scan, and browser interaction checks. Existing classifier, builder, real options
payload, coverage, localization, counted-cap, null-safe and degraded-fact tests remain.
Old tests that pinned inline CSS now read the paired page stylesheet; constraints on
token use apply to both themes. Historical W11 evidence files remain unchanged.
The synthetic browser scenarios are TEST FIXTURES only and never enter site data.

## Required evidence and current limitations

Canonical capture_page_evidence.py supplies the dark/light x EN/ZH x 1440/390 matrix,
plus genuine hover and keyboard-focus states. The isolated browser harness exercises
filtering, empty-result recovery, theme selection, sorting, expansion, focus retention,
cap restoration and loading/empty/missing/partial/stale/populated transport scenarios.

Paper is NOT_APPLIED_TO_PAPER. Exact target 01M2WGNCX9475G79JRKJTCM08P is readable,
but observed catalog 16e6b93f0c51a1574ba8acee4df732052898707a04731d3817530971a88fdefd
is not admitted for writes. The supported owner must independently qualify and release
the catalog before this design is transcribed to editable pages/artboards.
Local screenshots and source implementation do not satisfy that gate or live release.

### Final accessibility refinements

Data refresh preserves focus on row controls, the selected-name evidence action,
the stock-overview link, an opened evidence region and the counted expansion
control. Expanding the population focuses the first newly revealed ticker, so Tab
continues through the additional names. The seven existing rule inputs display
localized Met / Not met / Unavailable state names without changing their values.
Activity help uses a native popover, supports keyboard open and Escape, and cannot
trigger column sorting. Theme menus remain visible on one-name and empty boards.
The menu, focus and touch-target assertions query the current DOM atomically to
avoid treating an already replaced element as the current interactive target.

The phone metric column reserves 44px beside the shared floating assistant; both
unavailable and populated values are checked outside its footprint. The canonical
feed-status help button stays anchored beside its status text instead of occupying
an orphaned line. Shared navigation styling, markup, behavior and script order remain
unchanged. Its observed startup layout shifts are separately documented for review.
