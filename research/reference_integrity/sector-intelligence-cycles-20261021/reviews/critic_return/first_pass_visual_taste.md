-----BEGIN RIG RECEIPT-----
role: visual_taste
reviewer_identity: opus-auditor-visual-taste-sic-20261021-r3
pass: 1
artifact_sha: 5432d5a0b63a7ed3b6f4131270d58d2bec7c293e
reviewed_at: "2026-10-22T07:49:25Z"
verdict: BLOCK
round2_dispositions:
  - finding: VTC-013
    status: cured
    evidence: "On the Cycles face, boards 28/34/31/36 draw only the doctrine chips: XLF Watch don't chase, XLK Watch don't chase, XLC Protect gains (cycles.html has data-stance protect x1 and watch x2). Ink is --ink-ok/--ink-warn/--muted (cycles.css:37-41) and engine strings sit in the drawer. Mapping defects are filed separately as VTC-023, and the Brief residue as VTC-022."
  - finding: VTC-014
    status: cured
    evidence: "Both capture.log files sample the full canvas at four points: light (247,248,250) on 23/26/27/28/31/32/34/36 and dark (15,17,21) on 24/25/29/30/33/35/37. si_shell.css block 1 styles .si-page-header and .si-workflow, and the page head is visibly styled on 23/28/34."
  - finding: VTC-015
    status: cured
    evidence: "si_shell.py:24-30,52-56 emits six workflow links. aria-current is on Cycles in boards 28/34/31/36 and on Brief in boards 23/37. At 390px the switcher wraps to two rows (boards 31/37); si_shell.css blocks 4/5 are declared proposals."
  - finding: VTC-016
    status: partially_cured
    evidence: "7 closed cyc-prov drawers now hold the hashes, paths and field names, and the ZH enums (向下 · 底部) land on board 34. Still on the face: English 'Sector Cycles' source label in the ZH as-of (build_cycles.py:28; boards 34/36 page head and hero); English sector names inside the ZH read ('Financials下行阶段', 'Communication Services筑底阶段', board 34); the internal study id 'W5.1' and 'rank-IC' on methods/grader (boards 28/34)."
  - finding: VTC-017
    status: partially_cured
    evidence: "Scoped superseded_by notes on boards_manifest rows 1-8 (e.g. rows 1/5/8 point to 28-31/34-36 and keep the chart instrument from R3) close the reference split. There is still no composite corrected desk, and the 28/34 hero copy promises a 'one-tap cycle-position view' and clickable legs that no corrected board draws (folded into VTC-026)."
  - finding: VTC-018
    status: cured
    evidence: "On board 31 the incompatible_generation banner body wraps inside the events panel, the clock chips are muted (cycles.css:135), and the dated qualifier 'Clocks aligned on the history day 2026-10-16; not current under this banner' plus the Fixture label are shown. Judged at thumbnail resolution only (390x4477 displayed at 174 px wide); no crop was taken."
  - finding: VTC-019
    status: partially_cured
    evidence: "Legacy numerals and dates are stripped from 'The read' (build_cycles.py:59-64; XLF read on board 28 has no 47/100), but the read still narrates the legacy phase against the v2 chip. XLC chip 'Rolling over' with read 'in a Bottoming phase' (boards 28/34); filed as VTC-021."
  - finding: VTC-020
    status: partially_cured
    evidence: "Fixed: '1 day in' (board 23 hero), glyph legend labeled 'theme basket / sector ETF', coverage card now full width (board 23). Remaining: producer em dashes kept verbatim (declared), lane qualifiers that duplicate their titles ('Stand aside / Stand aside', 'Bottoming watch / Bottoming watch', board 23), and the coverage card titled 'unavailable' while printing '11 sectors · 49 baskets'."
round1_residuals:
  - finding: VTC-001
    status: cured
    evidence: "Per boards_manifest row 27 states_shown and rows 12/13/22, Paper boards 12/13/22 are no longer cited as coverage evidence; the Brief is a lane dashboard on 23/24/32/33/37. Board 27 itself was not re-viewed."
  - finding: VTC-002
    status: cured
    evidence: "All specimen boards (23-37) carry the canonical nav and page head via si_shell; Paper headers on 01-22 are scoped by manifest notes. The mobile bar on 31/36/37 shows menu, Terminal, theme and language but no wordmark. That appears to match production, which moves .nav-brand into the drawer at mobile (templates/navigation-refresh.css:1459-1466), but the drawer-open state is not drawn."
  - finding: VTC-006
    status: cured
    evidence: "Board 24 samples (15,17,21) at all four points (brief_repair/capture.log); panels sample (24,27,33) on 25/37."
  - finding: VTC-008
    status: partially_cured
    evidence: "boards_manifest rows 20/21 now carry 'superseded ... retained as a reviewer index only' notes, but board 21's face still says 22 boards against a 38-row set (Paper frozen)."
  - finding: VTC-009
    status: cured
    evidence: "components/components.css:182 sets .spc-model-prior-badge to font 800 var(--fs-label)=11px; the MODEL tags on board 28 are legible."
  - finding: VTC-011
    status: cured
    evidence: "The boards_manifest row 12 note says the single-series legend is not adopted (VTC-011 withdrawn from reference) and the board is superseded_by 23-26/32/33/37."
findings:
  - id: VTC-021
    severity: major
    finding: "One card names its phase three ways: XLC chip 'Rolling over' with read 'Communication Services is in a Bottoming phase'; XLF chip 'Rolling over' with note 'The cycle is in Downturn'. The ZH read on board 34 says 下行阶段 for XLF/XLK while the chip says 回落中, so a reader cannot tell which phase is true (boards 28/34/36; README producer finding 1 admits the read is legacy-family)."
  - id: VTC-022
    severity: blocker
    finding: "The Brief face still carries action language outside the six stances. Under each doctrine title the legacy fold names remain as qualifiers ('Act / Buy now / Entry confirmed today', 'Protect gains / Take profits', 'Stand aside / Hold what you own · no new buying'), and the hero draws 'Leadership steady — stay with the leaders.' in the stance-chip idiom. This contradicts the panel's own 'not advice' line and the drawer-only cure applied to Cycles (board 23/37; brief_repair/README.md wave-2 lane table; brief.css:157)."
  - id: VTC-023
    severity: major
    finding: "STANCE_MAP (cycles_repair/build_cycles.py:57-58) has two defects. It maps a missing engine stance (None) to 'ignore', drawing unknown as a decision rather than an unavailable state. It also collapses SELL into TRIM as 'Protect gains' and AVOID into WAIT as 'Stand aside' with no cited doctrine rationale, so the reference fixes a lossy production contract."
  - id: VTC-024
    severity: minor
    finding: "English is left on the ZH face: as-of source label 'Sector Cycles' hard-coded in build_cycles.py:28 (boards 34/36 page head and hero) and 'Sector Central' on the ZH Brief; English sector names inside ZH reads (board 34); 'W5.1' study id and 'rank-IC' jargon on the methods/grader face in both locales (boards 28/34)."
  - id: VTC-025
    severity: minor
    finding: "Specimen evidence drift. The cycles_repair/README.md Boards table lists only 28-31 with heights 2368/5436/6116, while cycles_repair/capture.log records 2007/3992/4477 and adds 34-36. The cycles capture.log header claims an overflow probe on every mobile cell, but lines 30/31/36 carry no data-w/data-ovf value."
  - id: VTC-026
    severity: minor
    finding: "Cycles desk composition. The hero card repeats the page title ('Sector Cycle Intelligence' under h1 'Sector Intelligence') and its four-line copy promises an absent chart (rebased/log axis, one-tap view, clickable legs). The top-right context card is three chips in a mostly empty panel. The grader eyebrow 'CONVICTION-CALL GRADER: MEASURED HIT RATE' restates the title and promises a rate that is not drawn (boards 28/34/36)."
  - id: VTC-027
    severity: minor
    finding: "At 390px the Brief lane rows squeeze the metric column into 3-4 line stacks ('+7.1% / clean entry / today', '20d vs market', 'Not measured'), while names and stance titles survive (board 37; same pattern on 25/26 per layout). The decision is not lost, but the row reads as a wrapped table rather than a glance row."
strengths:
  - "One shared shell (si_shell.py/css) gives every specimen the production page head, a six-link switcher with the correct current item, and true full-canvas light/dark, proven by pixel samples on every board."
  - "Cycles card faces are now plain: doctrine stance chip, v2 phase, measured-lower-bound phase age, MODEL badge at 11px, gap cells never zero, all identifiers behind closed 'How this was measured' drawers."
  - "Brief lanes are titled by doctrine stance with stance ink only, and direction ink follows the locale; the bottoming strip carries a Watch chip."
  - "The incompatible_generation fixture is labeled, chips are muted and carry a dated qualifier; stale is never presented as live."
  - "ZH parity is now drawn on desktop and mobile for both surfaces (boards 32-36), with producer enums glossed."
production_preferable_for:
  - "None of the presentation cells drawn here; the specimens beat production on shell, stance vocabulary and provenance. Production remains the only drawn source for the chart instrument (boards 01-08 R3 instrument scope) and the tinted Brief hero material (VTC-005 deferral)."
quarantine_breaches: []
-----END RIG RECEIPT-----
