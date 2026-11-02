# Intraday Flow — design and production upgrade

## 0. Acceptance gates

The Chairman requested a complete Paper redesign and implementation of
https://www.mastermind-x.com/intraday_flow.html on November 1, 2026 (America/Chicago).
This source task tree is a UI-specific child of the existing options-intelligence
programme and WS:INTRADAY-FLOW-P0-RECOVERY. It does not replace the programme plan,
create a workstream, or close existing live-feed or semantics obligations.

DONE_WHEN: editable Paper desktop/mobile designs are inspected and visually accepted;
the real template and rendered page implement the accepted design; existing data,
language, theme, filters, sorting and evidence remain functional; meaningful
regression/browser checks and independent review pass; the normal release path
serves the new page and desktop/mobile user journeys are verified.

Not done unless:
- The page answers which names warrant attention and what must happen next in seconds.
- Current market session, input availability, and recorded assessment time are distinct.
- Missing/stale/off-session data cannot be presented as a live actionable assessment.
- At 1440x900, useful scan content starts within 300px below global navigation.
- No duplicated spotlight/hero/board population and no decorative container edge accents.
- All existing six deterministic classifications, nine theme filters, search, sorting,
  grouping and advanced detail remain available with explicit semantics.
- Keyboard, focus, reduced motion, 390px layout, dark/light and EN/ZH work.
- Real production-shaped data plus missing/partial/loading/empty/stale states are verified.
- No new feed, poller, scoring model, trade authority, price fabrication, or auth bypass.
- Paper readiness, source implementation, CI, merge, deployment and acceptance are
  reported as separate evidence.

## Source identity

- Repository: mastermindx-market-intelligence/macro
- Task tree: research/intraday_flow_design_upgrade/MASTER_PLAN.md
- Initial base: f754bdee6b803b18191841863c35527c0a74571e
- Branch: claude/intraday-flow-design-upgrade-20261101-c2
- Operation: intraday-flow-design-upgrade-20261101-c2
- Protected procedure: Mastermind@19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec,
  mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap-major 1
- Task-tree revision: the Git commit containing this file; subsequent evidence cites
  the exact commit, rather than a self-referential fabricated SHA.
- Source owner: current ChatGPT2 Chairman-assigned redesign session; the current
  authenticated GitHub connector is mastermindx-2.
- Existing organizational record:
  agentos/workstreams/WS-INTRADAY-FLOW-P0-RECOVERY.md
- Existing programme planning carrier: macro #8770.
- Existing semantics repair: macro #6867, preserved independently.
- Organizational linking is pending accepted Agent OS integration; this branch is
  source evidence, not a claim that canonical wave status changed.

## Product decision

Primary persona: a self-directed investor scanning a fixed universe of leaders.
Primary question: What deserves attention, what confirms it, and is the evidence current?

Use the existing discovery-board identity: compact header and count ladder, a single
scan surface, and progressively disclosed evidence. Preserve the canonical global
navigation without page-specific modifications.

DARK TREATMENT: calm navy/charcoal canvas, subtly raised surfaces, strong typography,
neutral hairlines, semantic ink and quiet selection. Remove broad aurora/glow and
colored card rails. LIGHT TREATMENT: cool research canvas, crisp white surfaces,
neutral borders and a restrained shadow; a quiet selected-row fill replaces glow.
Reuse theme.css tokens, canonical typography and icons. No parallel token root.

Desktop: title/session header; short honest status band; compact six-category ladder;
search/theme/group/sort controls; 8-row glance board with counted expansion; adjacent
selected-name evidence where space allows. The row contains ticker/theme, existing
classification, one next-condition sentence, price and activity. Detailed tape,
dealer map, stop reference and full seven-leg evidence retain explicit landings.
Remove repetitive three-card spotlight from default presentation. Do not invent a
new recommendation, confidence score, ranking or signal.

Mobile: compact header, search, horizontally scrollable category controls, compact
stacked scan rows, inline or full-width evidence that preserves the user's place.
No page-wide horizontal scroll. No fixed element may cover the last row/action.

Trust behavior: retain recorded classifications as recorded information when current
required inputs are unavailable. Show a current-data caveat at the assessment, never
bury it in a tooltip. Optional missing options context must not erase valid price
observations. Unknown is unavailable, not zero. Existing canonical freshness and
coverage functions remain the source; preserve #6867's separate timing work.

## Tasks

| ID | Dependencies | Status | Outcome and evidence | Lane / review |
|---|---|---|---|---|
| P1 | none | implementation_complete | Baseline screenshot, live UI observation, template and ownership census; main base above | Principal; design adviser consulted |
| P2 | P1 | blocked | Editable Paper light/dark desktop/mobile and meaningful states; exact file/page/node IDs, screenshots and JSX | Principal designer; Paper schema qualification required |
| P2.1 | P1 | ready | Exact HTML/CSS reference and interaction specification, explicitly NOT_APPLIED_TO_PAPER while gate persists | Principal design; independent visual critique |
| P3 | P2.1 | proposed | Integrate reference into existing template/page; preserve engine and feed contracts; isolated source branch | Bounded economical Fabric builder if admitted |
| P3.1 | P3 | proposed | Functional and responsive state verification; same original semantics tests plus new user-path regressions | Builder; no weakened assertions |
| P4 | P3.1 | proposed | Independent code/visual review and bounded repair on exact candidate | Separate reviewer; principal adjudicates |
| P5 | P2,P4 | blocked | Exact-head CI, permitted integration/release and served desktop/mobile proof | Existing release owner; no premature merge |

The Paper gate blocks canvas effects and final acceptance; independent design-reference
preparation, source integration and offline verification remain useful. A supporting
HTML preview cannot be represented as completion of P2.

## Integration boundaries and falsifiers

Allowed code surfaces: templates/intraday_flow.html.j2, site/intraday_flow.html,
page-scoped paired CSS/JS only if needed, existing Intraday browser tests, and scoped
mockups/evidence plus this plan. Changes to the producer, freshness policy, classifier,
global navigation, auth/paywall, Caddy, data stores, schedulers and infrastructure are
outside this design implementation.

An existing source repair in #6867 changes timing/precursor semantics. Preserve its
branch and do not replay that repair. Keep classification functions intact unless an
independently necessary display-only change has explicit evidence and acceptance.
Reconcile source overlap before release.

Falsifiers: fabricated prices/charts; current buy claims while evidence is unavailable;
lost classifications or details; board only usable by mouse; filters lost on refresh;
state changes caused by CSS/DOM restructuring; translation fallback leaking internal
slugs; absent mobile/dark/light proof; Paper or production claims supported only by
mockups or passing tests.

## Observed Paper gate

On November 1, the direct Mastermind Paper and legacy Studio catalog both reported
paper-desktop 0.5.14 with accepted_for_write=false. Observed catalog:
16e6b93f0c51a1574ba8acee4df732052898707a04731d3817530971a88fdefd.
Expected reviewed catalog:
1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db.
Exact-file read works for MASTERMIND PAGES:
01M2WGNCX9475G79JRKJTCM08P.
No Paper mutation was attempted. Refresh/requalification must follow the existing
guarded Paper owner; changing a hash or using a different carrier to bypass the
write check is not authorized. Default-context DOCUMENT_UNAVAILABLE is separate
from exact-file read serviceability.

## Verification record

Initial live browser reproduced the supplied closed-market screen: six recorded
candidates, missing quotes, duplicate spotlight and board below the first screen.
This is a UI observation, not real-time feed qualification or trading validation.
Source and plan readbacks are recorded by their containing commits.
