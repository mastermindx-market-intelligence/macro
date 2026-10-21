STATUS/RESULT/EVIDENCE/GAPS/DEVIATIONS and the receipt are the critic's final message, byte-exact (agent a29cc1ceb621c5201, message msg_011CgFCn178pmaxqaiJUZegs, model claude-opus-5-5, pass 1, rationale-quarantined).

-----BEGIN RIG RECEIPT-----
```yaml
role: product_regression
reviewer_identity: opus-auditor-product-regression-sic-20261021-r1
pass: 1
artifact_sha: 508539c0091ae8d77aea3f9ca009391cf4dbfa9f
reference_id: sector-intelligence-cycles-20261021
verdict: BLOCK
findings:
  - id: PRC-001
    severity: blocker
    capability: "SC-001..SC-007, SC-009..SC-014, SC-021..SC-023, SC-034, SC-091"
    task: task.brief
    boards: ["12-brief-desktop-light-en", "22-brief-desktop-dark-en"]
    finding: "The Brief drops the Act-Now board. Production (prod-desktop-dark-en-central, prod-mobile-light-zh-central) shows five gated lanes: BUY NOW 5 / ALMOST READY 2 / IN FAVOUR - DON'T CHASE 3 / TAKE PROFITS 2 / STAND ASIDE 24. It also shows per-row scores and 20d vs market, the 'N more here - sign in' preview fold, the lanes-only-gated disclaimer and BOTTOMING WATCH (7) with gate chips. None of these appear on boards 12 or 22. They are replaced by 'Three places to investigate' (3 rows). state_matrix.csv:14 still claims brief/locked is PRODUCED from templates/_us_act_now_board.html.j2:31, but no board draws that state. copy_deck brief section has no lane label strings."
  - id: PRC-002
    severity: blocker
    capability: "SC-035, SC-089, U04"
    task: task.brief
    boards: ["12-brief-desktop-light-en", "22-brief-desktop-dark-en"]
    finding: "The Brief has no track record or grader surface and no honest denominator. The production track-record entry point has no home on the Brief."
  - id: PRC-003
    severity: blocker
    capability: "C19, U14"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "The hazard table invents a target: 'Cycle crosses zero' at 38/71/89%, all marked MODEL. engine/hazard_score.py scores P(turn within h months) for the open leg direction only, and has no zero-cross target. '4 of 6 cells use a model fitted on Energy' is unsupported: coefficients are per direction, not per sector. No current-parity caveat (lineage PARITY_FAILS) and no 'display-only, never a signal' footnote is visible. copy_deck hazard_label 'Turn hazard (calibrated)' and hazard_footnote 'isotonic-calibrated ... W4.2 gate' reuse production text without that caveat."
  - id: PRC-004
    severity: blocker
    capability: "C23, U04"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "The track record invents a metric. It says '27.4% Conditional hit rate - 31 of 113 called turns arrived inside their window', next to '12 calls logged in advance since 1 Jan 2026, 4 resolved, 8 still open'. The two denominators cannot both hold. C23 says no standalone grader exists for turn windows, and the Sector Central grader scores conviction calls against forward returns. 'Scored by the Sector Central grader on turns called before they happened' is therefore false."
  - id: PRC-005
    severity: blocker
    capability: "C15, C17"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "The board states 'Tighten risk rather than add.' and shows a 'Protect gains' stance chip. Together with copy_deck stance_act 'Act' (NEW), this turns a descriptive cycle or management state into a trading instruction. Model narrative gains sizing or execution authority, which house law forbids."
  - id: PRC-006
    severity: blocker
    capability: "U03, C16"
    task: task.dossier
    boards: ["12-brief-desktop-light-en", "14-explore-rotation-desktop-light-en", "16-dossier-desktop-dark-en", "22-brief-desktop-dark-en"]
    finding: "Phase age is shown as definite months or weeks ('Late up for 14 months', 'Late up for 19 months', 'month 11', 'Week 31 of this leg') with no status qualifier. At this SHA, engine/cycle_phase_age.py measures sessions with status measured/lower_bound/insufficient_history/source_unavailable/unknown_phase/not_logged (forward_log_replay.v2), stamped by engine/sector_cycles.py _stamp_phase_age. cycles_ia.md:155 and :228-230 still say no producer of true phase age exists. That is stale, so U03 was dispositioned wrongly and lower bounds are shown as facts."
  - id: PRC-007
    severity: blocker
    capability: "C18, C19"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en", "16-dossier-desktop-dark-en"]
    finding: "Descriptive rhythm is mixed with hazard semantics. Board 01 shows a 'Leg end PRIOR-led' window on the price chart. Board 16 shows 'Slow cycle, 9 to 14 months MODEL ... Cycle peak window opens in about 6 weeks'. The MODEL badge sits on a periodicity read that no calibrated model produces."
  - id: PRC-008
    severity: blocker
    capability: "navigation doctrine (CLAUDE.md Navigation source-of-truth)"
    task: task.return
    boards: ["01-cycles-desktop-dark-en", "16-dossier-desktop-dark-en", "12-brief-desktop-light-en", "14-explore-rotation-desktop-light-en", "22-brief-desktop-dark-en"]
    finding: "Boards 01 and 16 draw a third header family: 'Mastermind | Brief Sectors Cycles Research Watches | Search sectors, tickers, notes | EN 中文 | Dark'. Boards 12, 14 and 22 draw a modified site nav with no flags, no Other Assets and no settings gear. Production uses the canonical _site_nav family on both pages. No third header family may be created."
  - id: PRC-009
    severity: blocker
    capability: "U14"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "The lead-lag STOP and inert sizing (size_mult 1.0) appear on no user-facing surface. Inert sizing is noted only in cycles_ia.md:36/:157, and the lead-lag STOP is absent from every proposal file. Combined with PRC-005, users get no signal that these outputs carry no authority."
  - id: PRC-010
    severity: major
    capability: "SC-058"
    task: task.brief
    boards: []
    finding: "Time Machine has no home. Zero hits in any proposal file."
  - id: PRC-011
    severity: major
    capability: "SC-059, SC-060, SC-061, SC-062"
    task: task.research
    boards: []
    finding: "Forming Narratives (ai_watch) has no home. Zero hits."
  - id: PRC-012
    severity: major
    capability: "SC-046"
    task: task.watches
    boards: []
    finding: "Desk-watch has no home. Zero hits."
  - id: PRC-013
    severity: major
    capability: "SC-044, SC-045, SC-049, SC-051, SC-052, SC-053"
    task: task.rotation
    boards: ["14-explore-rotation-desktop-light-en"]
    finding: "Moving and Money surfaces exist only as lens tab names, not drawn: rotation events board, whole-market 269-subsector map, money-flow verdict, sector-ETF flow board, heatmap, index leadership. 'heat' appears twice in copy strings and 'Money' only in the state matrix."
  - id: PRC-014
    severity: major
    capability: "SC-054..SC-057, SC-063..SC-078"
    task: task.rotation
    boards: ["14-explore-rotation-desktop-light-en"]
    finding: "Confluence and the Explore table capabilities have state or copy rows only. No board shows the confluence grid, filters, sortable columns or exports."
  - id: PRC-015
    severity: major
    capability: "SC-024, SC-048"
    task: task.brief
    boards: ["12-brief-desktop-light-en", "22-brief-desktop-dark-en"]
    finding: "The hero handoff block ('THIS WEEK'S HANDOFF - Losing the lead / Taking the lead') and the WHAT CHANGED chips are replaced by a single h1 claim and a 'What changed?' link. The week-over-week change read is lost."
  - id: PRC-016
    severity: major
    capability: "SC-008, SC-038, SC-040"
    task: task.rotation
    boards: ["14-explore-rotation-desktop-light-en"]
    finding: "Reco tags and the 11-sector gated conviction board have no drawn home."
  - id: PRC-017
    severity: major
    capability: "SC-080..SC-086"
    task: task.return
    boards: []
    finding: "The routing contract has no IA home: legacy view anchors, #theme-*, #read-*, hash fallback and deep-link scroll. The six-tab IA gives no mapping for existing inbound links."
  - id: PRC-018
    severity: major
    capability: "C07, copy integrity"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en", "12-brief-desktop-light-en", "14-explore-rotation-desktop-light-en"]
    finding: "The copy deck and boards disagree. (1) The Brief claims '18 reused / 0 NEW', but the boards carry strings missing from the deck ('Three places to investigate', 'Source rank', 'Entry posture', 'Check entry signals', 'Go deeper'). (2) The h1 is 6 words against a 4-word budget. (3) Board 01's phase chips 'Early up / Late up / Early down / Late down' do not match the deck's production chips (Topping-late / Trending / Rolling over / Prime entry / Bottoming). (4) quadrant_body 'Up = gaining speed this week' contradicts board 14's 21-session y-axis."
  - id: PRC-019
    severity: major
    capability: "C12, C14"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "'Engine read' shows analyst-style causal narrative ('crude steadied and refining margins widened') under 'Narrative from engine epoch E-2026-03'. This presents generated prose as an engine measurement."
  - id: PRC-020
    severity: major
    capability: "boards_manifest integrity"
    task: task.dossier
    boards: ["16-dossier-desktop-dark-en", "12-brief-desktop-light-en"]
    finding: "boards_manifest capabilities_covered claims things the pixels do not show. Board 16 lists C10/C11/C12, but no turn markers, leg timeline or narrative are drawn. Board 12 lists R3A-19/27/92, but those states are not drawn."
  - id: PRC-021
    severity: minor
    capability: "state_matrix traceability"
    task: task.research
    boards: []
    finding: "state_matrix.csv mis-maps R3A ids. R3A-19 (auth hydration) is cited for incompatible_generation and invalid_payload, and R3A-30 (fail-soft) for explore/corrected."
  - id: PRC-022
    severity: minor
    capability: "C19"
    task: task.cycles
    boards: ["06-cycles-states-desktop-dark-en", "01-cycles-desktop-dark-en"]
    finding: "The Abstained card's PRIOR '38% of 41 comparable legs' (up, 3 months) conflicts with board 01's up/3m PRIOR of 33%."
  - id: PRC-023
    severity: minor
    capability: "C20, C21"
    task: task.cycles
    boards: ["01-cycles-desktop-dark-en"]
    finding: "'Money rotated in from Utilities on 9 Oct' is a pair-wise flow attribution that the relative-strength evidence may not support."
user_task_matrix:
  task.brief: {verdict: WORSE, reason: "no Act-Now lanes, Bottoming Watch, lane counts, paywall fold or track record"}
  task.rotation: {verdict: EQUIVALENT, reason: "map + accessible list + inspector + playback are strong; Money/Moving/heatmap/conviction surfaces undrawn; axis copy contradiction"}
  task.dossier: {verdict: WORSE, reason: "excellent facts strip/membership dates/zero-vs-missing, but unqualified phase age and MODEL on rhythm"}
  task.cycles: {verdict: WORSE, reason: "invented hazard target, invented grader metric, trading instruction, no parity caveat"}
  task.stock-prophet: {verdict: BETTER, reason: "dated ETF context, Compare in Prophet, 'group strength never makes a stock an entry'"}
  task.research: {verdict: UNKNOWN, reason: "draft-not-saved and read-back strings present; research boards not viewed; language-switch survival unshown"}
  task.watches: {verdict: UNKNOWN, reason: "new surface; 'saving a symbol is not an alert' good; watches boards not viewed"}
  task.return: {verdict: UNKNOWN, reason: "origin chip + Clear context on board 16; legacy anchors unmapped; theme/language state preservation unshown"}
  task.keyboard: {verdict: UNKNOWN, reason: "focus outline kept, keyboard hints on board 01; no journey evidenced"}
strengths:
  - "Accessible Map/List rotation alternative with keyboard text (board 14)"
  - "'Group strength. A separate stock decision.' framing; Compare in Prophet without auto-filter"
  - "Honest zero vs missing ('AMKR has no price yet ... shows no data, not zero'); identity-unresolved row"
  - "Membership-effective vs source-observed dates; 'Not supplied by the source' for relationships"
  - "Recorded vs reconstructed track-record split on dossier states; 'Not a win rate' caption"
  - "Overdue now rendered (C18 upgrade); SSR as-of date shown (C24)"
  - "Full typed degraded-state set with 'still works', design targets labelled as such"
  - "copy_deck EN/ZH parity 213/213 keys, 0 mismatches"
  - "components.css: no stripe rules (only the law comment at :9); :focus-visible outline 2px kept at :43"
production_preferable_for:
  - "task.brief: the Act-Now five-lane board, Bottoming Watch, handoff hero, What-changed chips"
  - "The Map / What's Moving / Money & Breadth / Confluence surfaces"
  - "Time Machine; Forming Narratives; desk-watch"
  - "Cycles hazard and grader honesty (production shows no invented zero-cross target or 113-turn denominator)"
capabilities_without_home: [SC-001, SC-002, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010, SC-011, SC-013, SC-017, SC-020, SC-021, SC-022, SC-023, SC-026, SC-033, SC-034, SC-038, SC-040, SC-041, SC-042, SC-043, SC-045, SC-046, SC-048, SC-049, SC-051, SC-052, SC-053, SC-054, SC-055, SC-056, SC-057, SC-058, SC-059, SC-060, SC-061, SC-062, SC-063, SC-064, SC-066, SC-068, SC-069, SC-070, SC-071, SC-072, SC-073, SC-076, SC-078, SC-080, SC-081, SC-082, SC-083, SC-084, SC-085, SC-086, SC-087, SC-089, SC-091, U01, U03, U06, U12, U13]
capabilities_uncertain: [SC-036, SC-039, SC-050]
images_viewed:
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/12-brief-desktop-light-en.png
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/22-brief-desktop-dark-en.png
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/14-explore-rotation-desktop-light-en.png
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/01-cycles-desktop-dark-en.png
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/16-dossier-desktop-dark-en.png
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/06-cycles-states-desktop-dark-en.png
  - "production/prod-desktop-dark-en-central.png"
  - "production/prod-mobile-light-zh-central.png"
  - "production/prod-desktop-dark-en-cycles.png"
inputs_opened:
  - research/reference_integrity/sector-intelligence-cycles-20261021/baseline.yml
  - mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/boards_manifest.yml
  - "proposal copy_deck.md, copy_deck.json, cycles_ia.md, cycles_ia.csv, state_matrix.md, state_matrix.csv"
  - "design_refs/sector-paper-20261021/components/components.css, specimen.html, COMPONENTS.md"
  - "engine/cycle_phase_age.py (1-52, 142-240), engine/sector_cycles.py (grep, 870-873), engine/hazard_score.py (1-40 + grep)"
quarantine_breaches: []
```
-----END RIG RECEIPT-----

STATUS: FAIL

RESULT:
- The verdict is BLOCK: 9 blockers (PRC-001..009), 11 majors (PRC-010..020) and 3 minors (PRC-021..023).
- The proposal is a real improvement for Prophet hand-off and dossier provenance.
- It loses the Brief's Act-Now and Bottoming Watch decision surface.
- It invents Cycles numbers: a "Cycle crosses zero" MODEL hazard and a 31/113 "called turns" grader.
- It issues a trading instruction ("Tighten risk rather than add.").
- It shows lower-bound phase ages as facts.
- It draws a third header family.
- 66 baseline capabilities have no home.

EVIDENCE:
- **No drift.** `git diff --stat 508539c0..HEAD` over mockups/design_refs/templates/scripts/engine/baseline is empty. The artifact equals the reviewed tree.
- **Capability walk.**
  - The proposal contains no SC-0xx ids. Its 28 R3A ids were walked as the SC numbering.
  - U01, U03, U06, U12 and U13 are never referenced.
  - All of C01..C28 are covered by `cycles_ia.csv` (28 rows). C16, C17, C18 and C23 are PRODUCED_NOT_RENDERED.
- **Absent from every proposal file (0 hits):** Time Machine, Forming Narratives/ai_watch, desk-watch, the lead-lag STOP, lower_bound/insufficient_history, and the production lane labels.
- **Phase age.** `engine/cycle_phase_age.py` measures sessions with a status field (`forward_log_replay.v2`). `cycles_ia.md:155` and `:228-230` still say no producer exists.
- **Doctrine greps.** `components.css` has no stripe rule; its only hit is the comment at :9. `:focus-visible` keeps a 2px outline (:43). Box-shadows are rings and the popover only. `specimen.html` has no site-nav.
- **EN/ZH parity.** `copy_deck.json` has 213/213 keys with both languages, 0 mismatches.
- **State matrix.** It has 102 rows (17 per board family plus 1). Row 14 marks brief/locked PRODUCED from `_us_act_now_board.html.j2:31`, but the boards never draw it.
- **Images.** 9 viewed, listed in the receipt.

GAPS:
- **Boards not viewed:** 00, 02–05, 07–11, 13, 15 and 17–21. This covers the Watches, Research and mobile/ZH boards, so task.research, task.watches, task.return and task.keyboard stay UNKNOWN, and dual-theme/ZH parity was judged on boards 12/22 only.
- **Production templates** (`sector_central.html.j2`, `si_workspace.js`, `sector_cycles.js`) were not read line by line. Production behaviour comes from the captures and the baseline.
- **Uncertain dispositions:** SC-036, SC-039 and SC-050.
- **Not reviewed:** the dark/light art direction as a design adjudication. That belongs to Reviewer B (visual_taste).

DEVIATIONS:
- **Withdrawn finding.** The provisional blocker "board 06 Corrected labelled Produced" is dropped. `state_matrix.csv:91` marks cycles/corrected PRODUCED from `templates/sector_cycles.js:1332`, so my earlier premise was wrong. Findings were renumbered.
- **Path note.** The copy-deck, IA and state-matrix files resolve both under `mockups/.../proposal/` and under `design_refs/sector-paper-20261021/`. Both were read as the same artifact.
- **Read-only throughout.** No edits, no network, and no quarantined file opened.
