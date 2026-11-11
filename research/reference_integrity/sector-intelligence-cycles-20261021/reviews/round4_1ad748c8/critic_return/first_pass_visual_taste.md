<!-- RIG round 4 · pass 1 · visual_taste · reviewer agent a48a38779cafe1df4 · artifact 1ad748c8e785eda0a3e1f13167a9290c194d07ae ·
     stored byte-exact from the agent's final message (sha256 of the message body below: 51c5693c337f4cedbadd5d8079cf48be21143e4219b85d9d22a5c7ed145cc21f) -->

STATUS: FAIL

RESULT:
Round 4, pass 1 at 1ad748c8 returns **BLOCK**. Wave 3 cures the round-3 blocker (VTC-022) and most of the round-3 rows, but it adds one new blocker (VTC-029) and one new major (VTC-028).
- **VTC-029 (blocker):** In Chinese, the Cycles stance chip renders "Watch — don't chase" as 观望——勿追高. On the Brief and in the copy deck, 观望 is the Stand aside stance. So a Chinese reader sees the Stand aside word on the Cycles page.
- **VTC-028 (major):** Each Cycles card face names the next turn in conflicting ways. XLF and XLK show a down leg toward a trough but "Projected next peak". XLC shows "Rolling over" but an up leg toward a peak.

The receipt follows, ready to store byte-exact.

```
-----BEGIN RIG RECEIPT-----
role: visual_taste
reviewer_identity: opus-auditor-visual-taste-sic-20261021-r4
pass: 1
artifact_sha: 1ad748c8e785eda0a3e1f13167a9290c194d07ae
reviewed_at: "2026-11-02T02:14:59Z"
verdict: BLOCK
round3_dispositions:
  - finding: VTC-021
    status: partially_cured
    evidence: 'EN is cured. Boards 28/29/39/40 name one phase per card face ("Rolling over" chip and "in a Rolling over phase" read). XLF "Downturn" appears only in the drawer (cycles.html XLF drawer "clocks phase Downturn · ladder RALLY ON"). The XLC legacy "Bottoming" appears only inside the labeled Clocks-disagree state that names both clocks. ZH is not cured. Board 34, XLF card: the chip says 回落中 but the read says "金融下行阶段" and the note says "阶段时钟为下行". Face-only count with drawers and the hidden desk removed: 回落中 x5, 下行 x7. The ZH face therefore still names the phase two ways.'
  - finding: VTC-022
    status: cured
    evidence: 'brf-lane-qual count is 0 in brief.html. "Buy now", "Take profits" and "Hold what you own · no new buying" appear only inside the lane-provenance drawer (brief.html:295, ab-buy-fold / ab-trim-fold / dash-hold-fold). The hero face is "Leadership is holding." plus participation facts (brief.html:272). "Leadership steady — stay with the leaders." appears only in the drawer as the labeled line "Production regime read" (brief.html:275). Lane subtitles state membership criteria, e.g. "Entry condition confirmed on the as-of date" and "Setup forming; trigger not yet confirmed". Board 38 shows the same in ZH.'
  - finding: VTC-023
    status: cured
    evidence: 'Judged under SIC-ADJ-01. STANCE_MAP is gone from build_cycles.py (:9) and the null path is coded at :68. Each of the 6 card faces has exactly one data-stance chip (watch x4, protect x2) with the "Engine mapping · Sector Cycles" eyebrow (cycles.html, 6/6). Each drawer opens with "Resolved stance · engine" followed by engine word + tone (XLF "HOLD · tone bullish", XLK "HIGH-RISK BOUNCE · tone caution", XLC "SELL · tone bearish"), then doctrine_stance with its engine/cycle_ontology.py :147/:179/:948 citation. Stance ink is warn for watch and protect. Gap: no specimen cell has a null stance ("Stance unavailable" count is 0), so the C02 null rendering is code-only and appears on no board.'
  - finding: VTC-024
    status: partially_cured
    evidence: 'Fixed: the ZH as-of stamp now reads 板块周期情报 (build_cycles.py:36; board 34 head). ZH sector names render (金融, 科技, 通讯服务). rank-IC is rendered as 横截面秩相关 on the ZH face. Remaining: "W5.1" stays on the ZH face (board 34 Methods and limits, card 4, "W5.1 研究已停止"; cycles.html:369, outside any drawer). The capture.log claim zh-latin=0 cannot detect it: components/zh_latin_grep.py tokenizes with [A-Za-z][A-Za-z''\-]+, which needs two letters and never matches "W5.1" or "P(". The EN face also carries the internal study id ("The W5.1 study stopped", board 28), which breaks the plain-words rule (Law 2).'
  - finding: VTC-025
    status: cured
    evidence: 'cycles_repair/README.md:55-63 heights equal the boards_manifest png_px for boards 28/29/30/31/34/35/36/39/40 (2352, 2352, 4326, 4967, 2206, 2206, 4326, 4863, 3348). capture.log wave-3 blocks print data-w="390" data-ovf="" for 30/31/36/39 and 25/26/37/38, plus switcher=6 with the current item, on every re-rendered board.'
  - finding: VTC-026
    status: cured
    evidence: 'Board 28 hero is "Where each sector sits in its cycle" with no title repeat and no chart promise. The context card is filled (as-of, generation sector_cycles.semantic_families.v2, hazard epoch, scope chips). The grader eyebrow is "Conviction-call grader" with a DEFINITION caption and no rate. Nit: the hero card stretches to the context-card height and leaves a large empty lower half (board 28, upper left).'
  - finding: VTC-027
    status: cured
    evidence: 'Board 38 lane rows put the name on line 1 and metrics ("+5.6% 20日对比市场 68 评分") on line 2. capture.log shows data-ovf="" on 25/26/37/38. Judged at downscaled resolution: the 390x4604 board displays at 169 px wide.'
  - finding: VTC-008
    status: withdrawn
    evidence: 'Withdrawal condition holds in every visible file. coverage_matrix.html (board 27) cites 38 and 39 and never 21. README Boards cites no 21. Manifest row 21 is marked "retained as a reviewer index only". proposal.yml is quarantined in pass 1 and was not checked.'
  - finding: VTC-016
    status: partially_cured
    evidence: 'Tied to VTC-024: the W5.1 internal id remains on the ZH face (board 34). Everything else in the row is cured.'
  - finding: VTC-017
    status: cured
    evidence: 'Board 40 draws the composite desk. The production chart capture is labeled "Production capture · As of 2026-10-20" with a caption naming site/sector_cycles.html at d86344b93a0b. The face states that the specimen cards are as of 2026-10-20, the Brief specimen as of 2026-10-19, and that the dates differ by design (cycles.html desk caption). The prod_capture.json fields match the caption. The hero no longer promises an undrawn chart.'
  - finding: VTC-019
    status: cured
    evidence: 'No legacy numerals appear on any face. The legacy phase word survives only as the named clock inside the labeled XLC "Clocks disagree" state, which SIC-V3-C03 requires. The remaining XLC face contradiction comes from the hazard leg and the rhythm projection, not the read, and is filed as VTC-028.'
  - finding: VTC-020
    status: cured
    evidence: 'The duplicated lane qualifiers left with VTC-022. The coverage card title is "Sector measurement coverage" with no "unavailable" (brief.html coverage block; board 38 bottom). Producer em dashes remain a declared producer item.'
round1_residuals: []
findings:
  - id: VTC-028
    severity: major
    finding: 'Each Cycles card face states a next turn that contradicts its own leg. XLF and XLK hazard ladders read "down · trough" while their timing cards read "Projected next peak ≈ 2026-07" and "≈ 2026-10" (boards 28/29/34/35/39/40). XLC wears the "Rolling over" chip but its hazard leg reads "up · peak" and its projection "next peak ≈ 2026-08, Overdue". Source: example_dataset.json sectors[0..1] have rhythm.next_turn=peak against now.hazard.turn_kind=trough; sectors[2] has hazard.direction=up and turn_kind=peak against phase_v2 Downturn. Both are drawn verbatim at build_cycles.py:150. The family-match rule covers only the legacy read against the phase clock, so these other clocks reach the face unlabeled. Cure: reconcile them under the same family rule, or show them inside the labeled disagree state.'
  - id: VTC-029
    severity: blocker
    finding: 'The ZH stance vocabulary is forked and collides with another stance. The Cycles chip renders Watch as 观望——勿追高 and Protect as 保护收益 (engine/cycle_ontology.py:137-138, stamped into example_dataset.json:207/403/586). The production deck renders them as 观察，别追 and 保护利润 (copy_deck.json:239-240, source templates/stage_analysis.html.j2:1497-1499), and Brief board 38 draws those. On the Brief, 观望 is the Stand aside stance (暂时观望 on the face, 观望 in the drawer, copy_deck.json:241). On boards 30/34/35/36, a ZH reader therefore sees the Stand aside word on the single stance chip SIC-ADJ-01 makes authoritative: eight ZH strings for six stances, one of them ambiguous. This breaks doctrine Law 1. It sits in the landed producer, not only in the specimen. Cure: give DOCTRINE_STANCE zh the deck/production strings and re-render the ZH boards.'
  - id: VTC-030
    severity: minor
    finding: 'One label carries two meanings in two places. On XLF the "Clocks disagree" chip in the card head means phase clock versus timing ladder, and its note names only one value ("timing ladder disagrees — the ladder state ... in the provenance drawer"; RALLY ON is drawer-only). On XLC, "Clocks disagree" inside The read means legacy read versus phase clock and names both clocks (boards 28/34/39/40). Either name both clocks in both states, or use distinct labels.'
  - id: VTC-031
    severity: minor
    finding: 'Board 40: the production chart''s "Where they stand" chips read "Rolling over 2" of 11 sectors (Topping 0, Trending 3, Rolling over 2, Prime entry 1, Bottoming 5). The three specimen cards beside it, at the same as-of 2026-10-20, all read "Rolling over". The chart and the cards disagree on phase membership at the same date, and the face does not say that the chart counts the legacy family.'
  - id: VTC-032
    severity: minor
    finding: 'In boards_manifest.yml rows 32 and 33, states_shown still lists "ZH deck copy end-to-end (lane titles + production qualifiers ...)" and "coverage unavailable (measured-sector read withheld)". Both contradict the wave-3 PNGs and the later wave-3 bullet in the same rows. These states are no longer drawn, so the bullets should be annotated or removed.'
  - id: VTC-033
    severity: minor
    finding: 'The fixture card face uses producer field jargon: "fell back to the KM prior: source PRIOR, cell_verdict PRIOR, epoch in the drawer" (boards 28/40; ZH 单元判定 on 34). SIC-V2-C04 moved field identifiers into drawers. Otherwise the card meets C17: exactly one labeled Fixture card, dashed and neutral, outside the live grid, with the PRIOR cell shape.'
  - id: VTC-034
    severity: nit
    finding: 'The ZH read "金融下行阶段，位于200日均线" drops "above" from "above its 200-day" (board 34). The ZH drawer line reads "持有 · 语气 bullish" with the tone left untranslated; drawers are exempt from C06, so this is polish only.'
strengths:
  - 'Board 40 is a strong composite: the labeled production chart instrument sits beside the correction cards, and the as-of difference is stated in prose on the face.'
  - 'Light (28/34) and dark (29/40/39) each read as designed themes with neutral surface hierarchy, even borders and no edge stripes. Stance ink is warn and the fixture card is dashed. The six-link switcher with Cycles/Brief current shows on every re-rendered board (capture.log switcher=6).'
  - 'The Brief hero and lanes are now descriptive. Instruction idioms live only in labeled drawers.'
production_preferable_for: []
quarantine_breaches: []
-----END RIG RECEIPT-----
```

Conditions to clear BLOCK:
- **C-A (VTC-029):** DOCTRINE_STANCE zh uses the deck/production strings (观察，别追 · 保护利润 · 暂时观望 …), and ZH boards 30/34/35/36 are re-rendered.
- **C-B (VTC-028):** no Cycles face shows a hazard leg or next-turn projection that contradicts its phase chip without a labeled disagree state.
- **C-C (VTC-021/024):**
  - the ZH face uses one phase word per card;
  - "W5.1" leaves both faces;
  - zh_latin_grep catches single-letter-plus-digit tokens.
- VTC-030 through VTC-034 are notes.

EVIDENCE:
- **Freeze:** HEAD is a2c374ab. `git diff 1ad748c8 HEAD -- design_refs mockups` is empty; the later commit touches research/ only.
- **Capture logs** (wave-3 blocks):
  - /Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/sector-intelligence-macro-7646-82cb8b-35c697a089b670b0/design_refs/sector-paper-20261021/cycles_repair/capture.log
  - /Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/sector-intelligence-macro-7646-82cb8b-35c697a089b670b0/design_refs/sector-paper-20261021/brief_repair/capture.log
- **DOM greps:** face text versus drawer text was separated in cycles.html and brief.html. ZH stance strings in each file were compared with copy_deck.json:239-241 and engine/cycle_ontology.py:137-138.
- **Data checks:**
  - example_dataset.json: rhythm.next_turn versus hazard.turn_kind, per sector;
  - boards_manifest.yml: rows 1/6/16 and 28–40, and capability_boards;
  - README.md:55-63, coverage_matrix.html and prod_capture.json.
- **PNGs read:** 28, 40, 39, 38, 34 under /Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/sector-intelligence-macro-7646-82cb8b-35c697a089b670b0/mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal/
- **Round-3 row wording:** taken from my own archived receipt, /Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/sector-intelligence-macro-7646-82cb8b-35c697a089b670b0/research/reference_integrity/sector-intelligence-cycles-20261021/reviews/round3_5432d5a0/visual_taste.yml

GAPS:
- **PNGs not opened this pass:** 29, 30, 31, 35, 36 (Cycles) and 23, 25, 26, 32, 33, 37 (Brief).
  - Boards 30/35/36 are judged through the shared DOM and board 34.
  - The Brief boards are judged through brief.html and the capture.log probes.
- **Downscaling:** the mobile boards 38/39 display at about 160–169 px wide, so row-level detail (C10) rests partly on the data-ovf probe.
- **C02 null stance:** no specimen cell is null, so the "Stance unavailable" rendering appears on no board.
- **Board 21 in proposal.yml:** not checked, because the file is quarantined in pass 1.

DEVIATIONS:
- Round-3 row wording came from the archived round3_5432d5a0/visual_taste.yml (my own receipt, not quarantined). I did not open product_regression.yml or Reviewer A's receipt.
- No files were written. The disposition list is keyed `round3_dispositions` rather than `round2_dispositions`; it has the same shape.