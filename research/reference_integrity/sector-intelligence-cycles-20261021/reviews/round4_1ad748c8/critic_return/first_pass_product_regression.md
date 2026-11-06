<!-- RIG round 4 · pass 1 · product_regression · reviewer agent a29cc1ceb621c5201 · artifact 1ad748c8e785eda0a3e1f13167a9290c194d07ae ·
     stored byte-exact from the agent's final message (sha256 of the message body below: b33812d7018a6951807e4a28d46ea0fcab3d31fee795804278868fa3fcc36322) -->

STATUS: FAIL

RESULT:
Round 4, pass 1, verdict **BLOCK**. This is the product_regression review of `sector-intelligence-cycles-20261021`, frozen at 1ad748c8e785.

- **Round-3 blocker PRC-033 is cured.** The engine now stamps the doctrine stance and the page only prints the stamped fields. No stance is calculated in the frontend, and no engine stance word or ladder state appears on the main card text.
- **All seven round-3 rows are cured:** PRC-033, 034, 035, 025, 027, 031 and 022.
- **New major finding PRC-036 blocks the review.** The engine's Chinese doctrine words disagree with the copy deck that the Brief draws from, and both disagree with the production templates. As a result the Chinese word 观望 means "Watch" on Cycles, "Stand aside" on Brief, and the engine's WAIT in the drawer.
- **Five new minor findings:** PRC-037 to PRC-041.

```
critic: opus-auditor-product-regression-sic-20261021-r4
reference: sector-intelligence-cycles-20261021
frozen_sha: 1ad748c8e785eda0a3e1f13167a9290c194d07ae
pass: 1 (rationale quarantined)
verdict: BLOCK

round3_dispositions:
  PRC-033: {status: cured, evidence: "engine/cycle_ontology.py:147-157 DOCTRINE_STANCE (HOLD/HIGH-RISK BOUNCE->watch, SELL->protect); :179-186 doctrine_for; called :1064 inside resolve_state (:948); asserts :171-174; tests tests/test_cycle_ontology.py:979/:991/:1007/:1023. Dataset stamp = engine map: XLF HOLD->watch/warn, XLK HIGH-RISK BOUNCE->watch/warn, XLC SELL->protect/warn (example_dataset.json sectors[0..2].now). build_cycles.py:65-68,194-198 prints now.doctrine_stance_en/zh + doctrine_ink only; STANCE_MAP absent. Face grep of cycles.html (details/script/svg/style/code stripped): 0 hits for HOLD|SELL|HIGH-RISK|BOUNCE|卖出|高风险反弹|RALLY|TOP WATCH|ROLLING OVER; 持有 only in the shared-nav string 持有哪个主题. Board 28/39/40: one chip per card + eyebrow 'Engine mapping · Sector Cycles'. Residual vocabulary defects are filed as new rows PRC-036/037, not as a frontend-mapping regression."}
  PRC-034: {status: cured, evidence: "enum_zh.json _source: 7/7 cited production lines grep-contain the exact string (顶部/底部 sector_cycles.js:1144, 板块 :93, 篮子 :736, 价格 :592, 向上 cycle_ontology.py:291, 向下 :312); 已对齐 honestly declared NEW deck copy (grep of templates/ and engine/ finds none)."}
  PRC-035: {status: cured, evidence: "cycles.html face: eyebrow 'Conviction-call grader / How conviction calls are graded'; 'DEFINITION · Conviction-call hit rate over all resolved calls, Neutral included. Not a win rate.' (board 28 grader card). No measured-value claim without a number."}
  PRC-025: {status: cured, evidence: "build_cycles.py:72-77 family_match (engine short label of phase == that of phase_v2), applied :157, recorded in the drawer :181. XLC (Trough vs Downturn) shows 'Clocks disagree · cycle read says Bottoming · phase clock says Rolling over' with the read drawer-only (boards 28/39/40). Residual on the hazard row is filed as PRC-039."}
  PRC-027: {status: cured, evidence: "boards 38 (brief mobile light zh) and 39 (cycles mobile dark en) exist; manifest rows 38/39 name the former gap cells and 16/16. png_px == sips header for all 41 manifest rows (38: 390x4604, 39: 390x4863, 40: 1440x3348; no mismatch). Board 27 PNG not re-read (see GAPS). Desk-composition coverage residual filed as PRC-041."}
  PRC-031: {status: cured, evidence: "capture.log:13,15-17 zh-latin=0 on boards 30/34/35/36 (components/zh_latin_grep.py skips nav/details/code; ALLOW :16 = tickers/SPY/MODEL/PRIOR). My own scan of lang=zh face spans found Latin only in shared production nav strings, the allowlisted PRIOR enum, and the board-40 desk caption (EN board). No English sector names on the ZH face."}
  PRC-022: {status: cured, evidence: "boards_manifest.yml:65 and :210 'Wave 3 (SIC-V3-C16): the PRIOR 33% hazard cell and the Abstained card drawn here are illustrative and superseded by boards 28/34 ...'; :475 'the placeholder phase ages and the Slow cycle MODEL label on this board are superseded by boards 28/34'."}

round2_dispositions_changed: []
round1_residuals: "PRC-001/003/004/005/008 and PRC-024/026/028/029/030/032 remain cured; nothing in the wave-3 delta reopens them."

capability_index_check:
  C19: "capability_boards C19 -> 28; board 28 draws the FIXTURE card ('Fixture — hazard PRIOR cell shape', FIX, 30% MODEL / 33% PRIOR / 50% PRIOR, 'Not a live sector ... Values are illustrative') outside the three live cards; it is the only PRIOR-shaped cell on the face (face grep: PRIOR occurs only inside that card). _fixtures.prior_cell.shape_source engine/hazard_score.py:432-436."
  C14_C24: "-> 28 (verified on the board 28 PNG)."
  C27: "-> 34 (not re-read this round)."
  C09_desk: "board 40: 'Production capture · As of 2026-10-20', caption names site/sector_cycles.html at d86344b93a0b with page stamp 2026-10-20, and states 'the Brief specimen is as of 2026-10-19. The dates differ by design and are not one snapshot.' prod_capture.json: sha d86344b93a0b, asof_prod 2026-10-20, px [1330,818], theme dark."

findings:
  - id: PRC-036
    severity: major
    title: "Two incompatible ZH doctrine vocabularies; 观望 means three different stances"
    evidence:
      - "engine/cycle_ontology.py DOCTRINE_STANCES (:135-140): get_ready 准备就绪, watch 观望——勿追高, protect 保护收益, aside 暂时回避; the comment above it (:127) claims 'the ONE plain-English action vocabulary a product face may show'; mirrored in components/COMPONENTS.md:128."
      - "copy_deck.json:238-241 (Brief chips/lanes): 做好准备, 观察，别追, 保护利润, 暂时观望. Board 38 lanes draw these (行动 / 做好准备 / 观察，别追 / 保护利润 / 暂时观望 / 筑底观察)."
      - "Production uses neither engine set: portfolio.js:1241 and watchlist_risk.js:494 use 做好准备; stage_analysis.html.j2:1497 '观察 —— 别追'; rotation_events.js:200 '观望，不要追高'."
      - "Result in ZH: 观望 is 'Watch' on Cycles (engine stamp), 'Stand aside' on Brief (deck :241), and the engine's WAIT stance_zh (cycle_ontology.py:115, shown verbatim in the Cycles drawer). A ZH reader cannot tell watch from stand-aside, and the four engine ZH words for get_ready, watch, protect and aside have no production origin."
      - "EN also splits: 'Watch — don't chase' (engine; DESIGN_DOCTRINE.md:44) vs 'Watch, don’t chase' (deck :239; Brief face)."
      - "deck :239 cites stage_analysis.html.j2:1497, but that line holds 'Watch — don’t chase'/'观察 —— 别追', not the deck string."
    breaks: "baseline C27 (bilingual and tone), C15 (one stamped stance vocabulary), condition 5 provenance (by analogy)"
    cure: "One EN/ZH doctrine set owned by engine DOCTRINE_STANCES, each ZH value sourced to a production file:line or declared NEW; Brief lanes read the same set; a test asserting copy_deck stance_* == DOCTRINE_STANCES; no ZH doctrine word may equal any STANCES[*].zh."
  - id: PRC-037
    severity: minor
    title: "HOLD->watch rationale is factually false and the ink-safety test is circular"
    evidence: "cycle_ontology.py:150-151 claims 'every HOLD cell is a don't-chase read (Recovery/TOP WATCH, Peak softening)'. But HOLD is also the stance of the non-divergent Recovery/Expansion/Peak x RALLY ON cells (:245-247), the clean-rally states. The tone-safety assert (:171-174) and test :991 pass only because _TONE_INK_GROUPS['bullish'] (:166) was defined to admit warn; the test copies the same table. So an Expansion x RALLY ON sector (engine tone bullish, green in production TONE_CLS) carries an amber 'Watch — don't chase'."
    note: "The mapping row itself is adjudicated (SIC-ADJ-01), so it is not reopened here. The comment must state the truth, and the adjudicator should confirm amber for the clean-rally cells explicitly."
  - id: PRC-038
    severity: minor
    title: "ZH face names the same phase two ways on one card"
    evidence: "The chip draws 回落中 (production sector_cycles.js:602, :1553). The XLF divergence note and the XLC Clocks-disagree read say 阶段时钟为下行 (engine short_zh 下行, cycle_ontology.py:80-81). The EN face uses 'Rolling over' in both places. cycles.html ZH spans."
  - id: PRC-039
    severity: minor
    title: "XLC hazard row direction comes from the legacy clock beside a Rolling-over chip"
    evidence: "Boards 28/39/40, XLC card: hazard row 'up · peak' beside the 'Rolling over' chip. The dataset has now.phase Trough and phase_v2 Downturn, the same family split that build_cycles.py:72-77 withholds from the read. The cells are gaps (non_monotone_cdf), but the direction label still says the open leg is rising."
    cure: "When family_match is false, label the leg direction with its own clock or move it to the drawer."
  - id: PRC-040
    severity: minor
    title: "'Clocks disagree / 时钟分歧' labels two different states"
    evidence: "Board 28: XLF chip 'Clocks disagree' = engine divergence (phase vs timing ladder). XLC read 'Clocks disagree' = legacy-read family mismatch (read vs phase clock). Same text and ZH, different contracts; the cycles.html face shows both."
  - id: PRC-041
    severity: minor
    title: "The new composite-desk composition has single-theme, single-locale evidence"
    evidence: "Board 40 is the only capture of ?desk=composite (desktop/dark/EN; manifest row 40). There is no light, ZH or mobile capture, and the embedded production crop is a dark raster (prod_capture.json theme dark) whose behavior in light theme is unaddressed. Coverage 16/16 counts only the standard grid."

user_tasks:
  brief: "BETTER: lane membership criteria under the titles and two-line rows at 390 (board 38). PRC-036 ZH lane vocabulary diverges from Cycles."
  cycles: "BETTER: no competing stance, family-match rule, isolated FIXTURE PRIOR card, rate-free grader. PRC-036/038/039/040 notes."
  dossier: "EQUIVALENT: placeholders now explicitly superseded (manifest :475); layout not redrawn."
  rotation: EQUIVALENT
  stock_prophet: UNKNOWN
  research: UNKNOWN
  watches: UNKNOWN
  return: UNKNOWN
  keyboard: UNKNOWN

strengths:
  - "The engine owns the doctrine stamp end to end: map, function, resolve_state, crosswalk export and four tests. The specimen stamps through doctrine_for, so it cannot drift."
  - "The production capture on board 40 is honestly labeled (sha, as-of, crop, dates-differ statement on the face)."
  - "enum_zh provenance is fully grep-verifiable."

conditions:
  - "SIC-V4 doctrine vocabulary (PRC-036): one EN/ZH doctrine set owned by engine DOCTRINE_STANCES, used by Cycles chips and Brief lanes alike, each ZH value sourced to production file:line or declared NEW; no doctrine ZH equals any STANCES zh; a test pins deck == engine; boards 30/34/38 re-captured."
  - "SIC-V4 rationale (PRC-037): correct the HOLD comment at cycle_ontology.py:150-151 to list the RALLY ON cells, and get adjudicator confirmation of the amber ink on clean-rally HOLD."
  - "SIC-V4 ZH phase name (PRC-038): face explanations use the chip's ZH label."
  - "SIC-V4 leg direction (PRC-039) and label split (PRC-040): distinct labels for divergence vs read mismatch; the hazard direction is labeled or drawer-only when family_match is false."
  - "SIC-V4 desk coverage (PRC-041): a light (and ZH) capture of the composite desk, or the desk declared review-only and outside the shipped surface."

quarantine_breaches: []
```

EVIDENCE:
- **Freeze check.** HEAD is a2c374ab, a re-freeze commit on top of 1ad748c8. `git diff 1ad748c8e785 --stat -- engine design_refs mockups tests` is empty.
- **Engine reads.** I read `/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/sector-intelligence-macro-7646-82cb8b-35c697a089b670b0/engine/cycle_ontology.py` at :70-81, :110-186, :244-252 and :940-965, plus `tests/test_cycle_ontology.py` at :975-1030.
- **Dataset stamp.** Parsed with python (json only).
- **Face greps.** `cycles.html` and `brief.html` with drawer, script, svg, style and code stripped, plus a scan of the Chinese text spans.
- **Provenance greps.** Every `enum_zh.json` `_source` line, `copy_deck.json:238-241`, and the production templates (stage_analysis, portfolio, watchlist_risk, rotation_events, sector_cycles.js).
- **Manifest.** `boards_manifest.yml` parsed for rows 1/6/16/27/28/38/39/40 and capability_boards; png_px compared with `sips` for all 41 rows.
- **Board images read:** 28, 40, 39 and 38.

GAPS:
- **Not opened this round:** the board 27 PNG (16/16 is taken from manifest rows 38/39) and boards 23/25/30/31/34/37.
- **Drawer first line not checked.** I did not grep the drawer to confirm the engine stance and tone appear verbatim as its first line, as SIC-ADJ-01 requires.
- **"Stance unavailable" not shown on any board.** The code path exists (build_cycles.py:194-198; copy_deck :156), but no captured board demonstrates it.
- **Production chart phase clock unverified.** I did not check whether the "Where they stand" counts in the board-40 production chart use the legacy clock or the phase_v2 clock, so I filed no finding on it.
- **Overdue chip on XLK not checked.** The central month 2026-10 equals the as-of month; I did not verify the producer's overdue rule.
- **Condition numbering differs.** The coordinator numbers the conditions SIC-V3-C01..C17; my receipt bound 8 conditions. I judged against my 8 plus SIC-ADJ-01.

DEVIATIONS:
- About 26 tool calls against a budget of about 20.
- HEAD is the re-freeze commit a2c374ab, not 1ad748c8; the listed paths are byte-identical between them.
- No files were written; this receipt is returned as the reply only. No scripts in the repo were run (the zh-Latin result is cited from `capture.log`).