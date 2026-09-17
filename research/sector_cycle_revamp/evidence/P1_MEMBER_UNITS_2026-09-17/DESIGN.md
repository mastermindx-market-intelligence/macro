# P1 member-evidence inspection: responsive and dual-theme treatment

Scope: repair independent review of `ce16dc6dc58acf8d9006ab0095c2714702b6bbbe`.
This is the existing basket-detail inspection, not a new route or redesign of Sector Central.
Content law: `docs/DESIGN_DOCTRINE.md`; composition law: `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`.

## User task and invariant

A reader inspects which members support the selected measurement and why a member is unavailable.
The same exact owner projection and the same single DOM roster serve every viewport, language and
visual theme. Representation, search and visibility filters never recalculate an analytical population.
No source, recipe, signal, action roster, new rank or trade permission changes in this repair.

## DARK TREATMENT

The containing panel is a quiet instrument surface on the existing graphite page. The two-pixel blue
accent edge identifies the inspection section, not market direction. Recessed secondary panels hold
controls, counts and the definition; hairlines separate rows. Existing semantic text/ink tokens carry
observed and unavailable states. Numbers use the existing tabular typography. There is no animation,
new glow system or page-local palette. Source/method receipts stay behind the existing details control.

## LIGHT TREATMENT

The panel is a white research sheet on the shared cool canvas, separated by the canonical card shadow.
Its top rule is a neutral one-pixel hairline rather than the dark accent fade. Statistical tiles use
white paper; the definition and table headings use the cooler secondary surface. This distinction keeps
numbers primary while explanation remains readable. Missing values retain neutral bordered labels and
plain reasons, not low-opacity text or a colored warning that could imply a trading signal.

Intentionally different mechanisms: neutral hairline versus luminous accent edge; cast shadow versus
dark luminance separation; white numerical tiles versus recessed dark tiles. The information hierarchy,
font family/weights, state meaning, source scope and interaction behavior are identical. All materials
resolve through existing theme tokens; no token root, font, CSS injection or parallel design system is added.

## Desktop and mobile composition

Desktop keeps the dense four-column table and five-part measurement summary. At 720px and below, the
same table rows become stacked records: member and result first, available/minimum history second,
then the complete reason across the row. There is no horizontal scroll requirement. The table's
explicit roles and header associations remain intact; the desktop header stays accessible when
visually clipped. Available/minimum replaces the ambiguous History used label; 43/25 means 43
available observations against a 25-observation minimum, not a 172% completion bar.

The measurement, search and display-filter controls remain full-width at phone size. Method receipts
retain keyboard-native details/summary behavior. No new motion is introduced. Filters retain all
catalogue members in the source projection even when the visible subset is one member.

## Degraded states

Insufficient history: CBRS remains in the real 24-member catalogue and its full reason is visible
within the phone viewport. Missing benchmark: the controlled six-member fixture retains raw returns,
withholds every relative reading and puts the benchmark-unavailable reason on every visible record.
Both degraded cases are captured in light as well as dark. Empty search remains a plain, full-width
row, never an empty analytical population. Invalid source binding remains quiet absence under the
existing consumer contract, not fabricated zero observations.

## Evidence and visual acceptance

Baseline: the exact ce16 predecessor screenshots in this folder and the sibling benchmark-pair folder.
Before repair, the real phone container was 340px wide while the table was 720px; its reason extended
from x=432 to x=745 outside a 390px viewport. A browser geometry assertion failed on that exact defect.

The repaired evidence keeps every EN/ZH x dark/light x 1440/390 image, including light desktop.
`verify_browser.py` records real normal and insufficient-history screenshots, source-data invariance,
geometry and semantic table presence. The sibling `verify_pages.py` also captures all eight
benchmark-unavailable states. Controlled positive benchmark screenshots explicitly show different raw
and relative magnitudes; they are labelled fixtures, not fabricated market observations.

Artifact bytes and one local compute/render duration are measured in `page_proof.json`. These values
are not incremental feature overhead, production latency or a forward-performance claim. Source and
visual review remain separate from full hosted CI, #7211 publication integration and authenticated
production acceptance.
