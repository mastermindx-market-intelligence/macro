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
| Seven rule inputs and unknown/false/true state | Full evidence; display availability is distinct from unchanged computeLegs values |
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
Reset returns focus to search; counted expansion continues at the first newly revealed ticker and collapse
returns focus to its replacement control. EN/ZH strings and labels are carried by the existing language mechanism.
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
localized Met / Not met / Unavailable state names. Missing comparison prerequisites
are masked as unavailable only in the presentation; leg values, K, the seven-rule
denominator and classifications remain unchanged.
Activity help uses a native popover, supports keyboard open and Escape, and cannot
trigger column sorting. Theme menus remain visible on one-name and empty boards.
The menu, focus and touch-target assertions query the current DOM atomically to
avoid treating an already replaced element as the current interactive target.

The phone metric column reserves 44px beside the shared floating assistant; both
unavailable and populated values are checked outside its footprint. The canonical
feed-status help button stays anchored beside its status text instead of occupying
an orphaned line. This feature does not customize shared navigation styling, behavior or script
order. The integrated main carries its own shared-shell updates, including the
canonical Expectation Surface research link in the generated page. Its observed startup layout shifts are separately documented for review.

### Independent review refinements

Directional Buy now/In favour colors both follow the canonical locale-specific
rising-price token. A neutral no-read count explains names outside the six stage
counts without adding a trading classification. Full evidence includes source
times, explicitly named nightly context and an unavailable dealer-chain clock.
Phones retain a stock-overview link inside opened evidence. Identical count text
is not repeatedly rewritten into the live region; feed help and dealer strength
are localized, native selects share the focus ring, and untagged names appear only
in All rather than bypassing a specific theme selection.


## R2 — recoverable scan states (principal design decision, 2026-11-03 UTC)

The existing discovery-workspace architecture is retained. This refinement closes
Paper/implementation gaps rather than introducing another skin or signal engine.
Compared approaches: a new dashboard composition duplicates accepted work; decorative
state cards consume the first-screen budget; a compact recovery treatment inside the
existing scan makes failure legible without displacing the table. Select the latter.

### User-facing behavior

1. An unmatched search retains its theme, setup, sort and grouping context. Provide
   **Clear search** (query only) and **Reset all filters** (existing full reset).
   The query is escaped, wraps safely, and is not mistaken for an observed ticker.
   Clear search returns keyboard focus to the original search input.
2. A truly missing/empty embedded watchlist is **Watchlist unavailable**, not zero
   setups and not a filtering result. Show a **Reload page** recovery action; do not
   imply the ordinary quote refresh can re-download the embedded watchlist. Display
   an em dash instead of six fabricated zero stage counts, and label the footer
   **Watchlist unavailable**. No classification or count calculation is changed.
3. A populated watchlist with no filtered matches is **No matching names**, with
   one recovery sentence and a compact reminder that no matches is not no setups.
   Never clear other filters implicitly when only the query is cleared.
4. Retain a recorded scan during source connection/loading; do not hide already
   available observations behind a new full-page spinner. Source state and filters
   remain orthogonal. Existing missing/partial/stale source copy remains truthful.

### Visual and interaction contract

DARK TREATMENT: existing graphite panel, restrained neutral empty-state symbol,
legible muted supporting text, a single filled action surface and quiet secondary
button. No rail, glow, or positive-signal color for unavailable data.
LIGHT TREATMENT: white panel, cool quiet symbol field, existing material shadow and
neutral separators. Preserve the same content hierarchy without dark-mode glow.
Use existing theme/spacing/type/radius tokens with canonical fallbacks only. No
new CSS root or runtime stylesheet. New action targets are at least 44px high;
mobile actions wrap without horizontal overflow. Visible focus remains complete.
Keep the existing compact default scan and six setup controls. No additional
permanent hero, duplicated summary or first-screen vertical cost in normal states.

### Scope and evidence

Allowed: templates/intraday_flow.html.j2, paired intraday-flow.css, generated
site/intraday_flow.html, scoped Intraday tests, browser proof and this existing plan.
Keep the 15 protected classifier/coverage/session/leg functions byte-identical.
No producer, fetch policy, freshness threshold, shared navigation, auth or deployment
change. Do not retry the platform-denied dark-ZH Paper ticker-row batch.

Verify red-first template/site contracts, actual browser Clear-search versus reset
behavior in combined filters, missing-watchlist reload presentation, long/hostile
query escaping, locale/theme parity, focus retention during refresh and zero
horizontal overflow at 390/1440. Retain the prior 280 tests and 515 browser checks.
Paper state samples are editable specifications, not implemented interactions or
independent visual acceptance. Keep original PR10498 Draft/HOLD and release gates.


## R3 · Source details without losing the scan (2026-11-03)

Chairman continued autonomous design-to-implementation; this bounded refinement keeps
Draft/HOLD and existing release gates. Paper references: file01M2WGNCX9475G79JRKJTCM08P,
pagep-26-1, light/EN6ZVB-0 and dark/ZH6ZYE-0. Both are verified editable390×844
illustrative specimens, not observed market data or qualified independent acceptance.

### Chosen approach and alternatives
Keep the existing concise three-feed LENS explanation and all current source clocks.
Add one explicit Sources action beside the existing Refresh, opening a native popover
using the page's already-established native-popover mechanism. A permanently expanded
status dashboard would crowd the scan; putting interactive buttons inside the shared
LENS tooltip would require a shared-system rewrite and violate tooltip semantics.
The native disclosure is page-scoped, nonmodal, keyboard-operable, and consumes no
closed-state layout height. It shares the existing status variables and refresh handler.

### Frozen presentation and interaction
- Title: Source details / 数据来源. Scope note: Board-wide availability; individual
  names can differ / 看板整体可用性；各标的可能不同. Never imply per-name confirmation.
- Price: received/delayed only when the incumbent quotesStatus says live; limited
  coverage is distinct from unavailable when canonical coverage is partial.
- Volume: literal producer stale===true is Marked stale / 已标记过期. Do not invent
  an age rule, calendar rule, threshold or confidence score. Otherwise use existing
  pulseStatus and canonical coverage; availability does not mean current confirmation.
- Options: received/approximate, connecting or unavailable using incumbent flowStatus.
  Missing options infer no direction and do not suppress a valid price.
- Source clocks pass through displaySourceTime; invalid/absent clocks stay unavailable.
  No Date.now substitution and no static specimen timestamp in product source.
- Each row carries a name, plain status, source time and one short meaning line.
  The static dialog header/actions survive asynchronous source renders. The body
  updates independently; a focused Refresh or Back control is never replaced.
- Refresh available data / 刷新可用数据 invokes the existing page refresh handler;
  no new request loop, timer, queue, store or retry policy. Back to scan / 返回扫描,
  Close and Escape preserve filters, selection and scroll; focus returns to invoker.
- Native popover uses role=dialog, aria-labelledby, explicit controls and44px actions.
  Small-screen layout scrolls inside viewport when needed; no page overflow.
- Dark: graphite panel, raised summary, strong essential text, restrained semantic ink.
  Light: white panel on cool canvas, canonical shadow and neutral borders. All styles
  remain in paired intraday-flow.css using canonical tokens; no runtime stylesheet.

### Implementation and acceptance contract
Template owns static panel and pure sourceDetailStatus(lane,status,stale,coverage)
returning bilingual status/meaning plus semantic class. renderSourceDetails() reads
existing state and updates only the body. updateSourceTimes() also refreshes details
without deleting the old clocks or trigger. The15protected functions remain identical.

Red-first source tests cover states, literal-stale flag, partial coverage, invalid
clocks, canonical data mapping, static accessible controls, unchanged pollers and
44px styles. Browser tests cover1440/390×light/dark×EN/ZH, open/close/Escape/focus,
refresh while open, stale/missing/partial fixtures and viewport geometry. Retain
all prior regression assertions; do not weaken the515browser or301pytest proof.

No independent source/visual review or release acceptance is granted by this packet.

## R4 · Field-guide meaning parity (2026-11-03)

Prerequisite satisfied: the actual R3 source at `dcda26d6d58bce0cbbe798d659eb7cdb8f755f9c`
was captured canonically in all 24 requested cells and visually inspected in all 8 resting
variants. Published proof checkpoint: `703f3c9c230730cf9f0f5dbb99c7bd416b85859b`.
R3 source details and its main integration are retained.

### Chosen approach
Refine the existing bilingual field guide inside its native closed-by-default details.
Keep the six classification labels, four subsections, seven checks and all advanced
evidence. The scan's recorded assessment and the source panel's availability limits
must retain the same meaning when a user reads the guide. A new warning panel or
permanent status block would duplicate existing information and add scan height.

### Frozen editorial and interaction contract
- Begin with the evidence and source times. Recorded labels do not establish that
  their conditions still hold now; missing or old observations remain limitations.
- Buy now explains existing washout/reclaim/volume conditions without claiming that
  an unknown quality check passed. Preserve every classifier and reason string.
- Almost ready explains a pending reclaim or waiting for the open. In favour is
  an existing trend assessment. Take profits describes extension/ceiling/pin risk
  without predicting a reversal. Watch describes missing structure or a known trap.
  Stand aside does not establish that the market is quiet.
- Separate approximate call-only buying/selling estimates from calls+puts net premium;
  the combined total alone cannot establish call direction. Missing stays unknown.
  The tape rule is not bid/offer matching; activity counts are recorded observations.
- Dealer information remains daily/nightly chain context. Its source time is unavailable
  here. Nightly stop/buy zone, VWAP, session low and dealer levels stay reference values,
  not confirmed execution or stop levels. Gamma context is not current direction.
- Keep native guide/section controls, keyboard behavior, locale switching, filters,
  selection and closed-state geometry. Add no fetches, timers, freshness thresholds,
  scoring, source/model logic, CSS or shared-navigation change.
- Light uses the existing white panel and neutral hierarchy; dark uses the existing
  graphite panel and muted supporting text. Preserve canonical tokens and styles.

### Editable design and discriminating proof
Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-26-1`:
desktop light EN `71UJ-0`; mobile dark ZH `720J-0`. Both were inspected with all
sections expanded, set to fit content after visible clipping, extracted to adjacent
`paper_r4_guide_*.jsx`, and finished on their exact node IDs. These are guide-copy
specimens; they do not add product headers or replace actual browser verification.
No denied dark-ZH ticker-row batch was recreated.

Implementation scope is the field-guide region in `templates/intraday_flow.html.j2`
and its canonical optimized `site/intraday_flow.html`. Verify exact identity of
all content outside that region, all script bodies, paired CSS and embedded board data
against 703f3c9c. Exercise the real opened guide in 1440/390 × light/dark × EN/ZH, keyboard
controls, locale visibility, overflow, and preservation of filters/selection. Retain
prior model/source/recovery proof; do not manufacture mirror tests for static copy.
Capture the final committed page through the incumbent canonical evidence driver.
Draft/HOLD, denied-effect boundaries and independent acceptance gates remain unchanged.
