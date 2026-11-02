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
| P2.1 | P1 | implementation_complete | DESIGN_SPEC.md and the paired template/CSS reference; NOT_APPLIED_TO_PAPER | Principal design; independent visual critique |
| P3 | P2.1 | implementation_complete | Real template, paired page stylesheet and rendered page replaced; 15 core regions byte-identical to base | Principal retained: design judgment and critical path while audit admission waited |
| P3.1 | P3 | implementation_complete | 280 pytest cases; 515 browser checks; 24 canonical screenshots and passing visual receipt | Regression and source-contract evidence; no production claim |
| P3.2 | P3.1 | implementation_complete | Canonical publication asset normalization; 283 pytest cases and 515 browser assertions pass; fresh capture and final-head release checks remain | Deterministic canonical transform; no shared-navigation source change |
| P4 | P3.1 | in_progress | Independent repair follow-up at 99b615153016 returns CODE=PASS; qualified human/Opus visual judgment remains open | Paid reviewer; principal adjudicates |
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

## Current cumulative frontier — 2026-11-02

Source implementation is complete in the isolated branch. The redesigned scan retains
all six classifications, nine theme filters, both languages, both themes, grouping,
numeric/name sorting, call-only context and all seven evidence legs. New phone sort,
explicit Price/Activity labels, keyboard controls, preserved focus/expansion across
refresh, visible input timestamps and a selected-name evidence panel are exercised
by `verify_browser.py`. The final source also preserves focus on the sidebar,
stock-overview link, full evidence region and counted expansion control during
refresh. Expansion continues at the first newly revealed ticker; seven checks have
explicit localized states; Activity help is keyboard accessible and does not sort.
The desktop scan begins 298.98px below navigation with seven
complete rows visible at 1440×900. Fifteen classifier/coverage/session/leg functions
are byte-identical to the initial base; see `model_preservation.json`.

`browser_verification.json` records 515/515 successful checks. All 280 Intraday
pytest cases pass; inline JavaScript syntax and paired stylesheet equality pass. Synthetic empty,
loading, missing, partial, producer-stale and populated responses exist only in the
isolated regression harness. They are not site data or live market evidence.

The principal retained implementation for product judgment and a critical-path
shortcut while the independently commissioned baseline contract audit waited for
its provider lease. The original Fabric audit run
`intraday-design-contract-audit-20261101-c2`, controller 40460, has returned.
Its useful baseline inventory and stale observations are separately adjudicated in
`BASELINE_AUDIT.md`; it is not final implementation acceptance. No duplicate worker
was started. Native design advice is advisory and does
not replace the required independent visual review.

Main `f6fb23200bb2fee8368aecda7f23725ccf4a6add` was merged into the isolated branch
at `aeff31db0803d75e41881fd566e13f6222d4ca05`. The only conflict was the generated
page's cache tags; page-only rendering resolved it. The repaired template and CSS
remain byte-identical to `660136436850d1ad5ff38ffc611525c7c10dc573`. The generated
page additionally receives the current canonical Expectation Surface research link.
The feature does not author or override shared navigation changes. Applicable
AGENTS/CLAUDE and routing/delivery instructions did not change in this integration.

The refreshed canonical capture on `aeff31db0803d75e41881fd566e13f6222d4ca05`
completed 24/24 states with no console errors or failed responses. The two phone
findings from principal visual critique are repaired: metrics remain left of x315
(the measured right edge is x311), and the feed-help trigger stays beside its status.
The matrix and receipt are in `mockups/refs/intraday-flow-upgrade/`.
The visual-receipt guard passed against the material source diff. Four supplemental
actual-click captures show the expanded evidence region on desktop and phone in
light/EN and dark/ZH. Eight additional browser checks confirm that open evidence
also stays within the viewport.

Initial-load traces identify substantial existing shared-navigation/search movement.
Baseline and candidate measurements are in `layout_stability.json`; these are lab
observations, not field-performance acceptance. No shared navigation code or script
order was changed. Global startup performance remains an explicit review limitation.

A fresh Paper catalog read observed version 0.5.18 with the same unqualified catalog
hash and `accepted_for_write=false`; a newer app version did not clear the gate.

The first independent review (`intraday-final-review-20261102-c2`, GLM 5.3)
returned CODE=CHANGES_REQUIRED and VISUAL=PARTIAL. All seven findings have bounded
repairs: locale-correct directional colors, missing-input presentation, phone stock
navigation, quiet unchanged count announcements, localized feed help, native sort
focus and exact theme filtering. See `INDEPENDENT_REVIEW.md`. A display-only mask
leaves legacy leg values and K untouched; missing/zero/positive/fallback inputs are
exercised in both languages. No-read counts reconcile with the six stage counts.

CI and fences passed on `cdc17bf634219135c000b0d97c84d1dd102014c6`; those results
are predecessor evidence. The repaired head requires its own concluded checks.

The latest Paper inspection now reaches the intended MASTERMIND PAGES file and
reports `write_binding_ready=true`. Its unchanged catalog is still not accepted
for writes. The file-context problem is resolved; schema qualification is the
remaining Paper gate. The existing Claude session target discovery separately
reports its Session Bridge owner unavailable, so no qualified visual route is claimed.

The follow-up repair review at `99b6151530160f1fb432277e48274040f2581660`
returned CODE=PASS (xAI / Grok 4.7); the exact return is accepted and adjudicated in
REPAIR_REVIEW.md. It executed independent Node/Chrome probes and source/hash checks,
with its partial-tree test limits stated. Native principal visual critique found no
blocking issue in five representative captures; that is not qualified visual acceptance.
Fences on this proof head passed; CI was still in progress at the documentation checkpoint.
The final matrix retains substantial initial-load movement (desktop CLS 0.681–0.881;
phone 0.252–0.307), so no performance acceptance is claimed.

Next: complete qualified visual/Paper gates, observe concluded binding CI on the
actual final head, and finish the normal integration path once those gates pass.
CLOSEOUT.md preserves the exact resume frontier; the PR carries post-checkpoint CI. See
`PAPER_QUALIFICATION_HANDOFF.md` for the bounded owner remedy. No Paper canvas effect,
merge into main, production deployment, live-page proof or final acceptance has occurred.

## Final main reconciliation — 2026-11-02

Main advanced during final CI observation and created a generated-page cache-tag
conflict. It is resolved in isolated-branch merge `d0201df47d889fb50cef04b5aa2fcda251b1a034`, incorporating
`bca436e58f7069ff8b52d31074f30726cfecf0e4`. The template, page CSS, model and embedded base are unchanged; the
rendered page differs from the reviewed version only by the shared theme cache tag.
The upstream GMI theme variables are unused by this page. Applicable instructions
were unchanged. See MAIN_INTEGRATION.md for the exact source comparison and scope.

The integrated candidate again passes 280 pytest cases and 515 browser checks, plus
design-system, runtime-style and visual-receipt guards. The existing canonical
matrix is carried forward with explicit source/geometry proof, not relabeled as a
new capture. Qualified visual/Paper gates and served production acceptance remain
open. Final-head CI belongs in the PR receipt after this proof update is pushed.


## Recovery delta — 2026-11-02

P3.2 restores canonical generated asset hashes, defer and preload without changing
the reviewed template/CSS or model. MAIN_INTEGRATION.md contains the exact HTML
hash, recovered 0886fff CI pass, 283 pytest and 515 browser results, original
Fabric admission refusal and narrow Paper/visual gates. The normalized artifact
requires its own final capture/CI; predecessor receipts are not future acceptance.
