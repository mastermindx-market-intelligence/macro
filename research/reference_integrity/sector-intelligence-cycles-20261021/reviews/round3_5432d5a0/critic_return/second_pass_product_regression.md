-----BEGIN RIG AMENDMENT-----
role: product_regression
reviewer_identity: opus-auditor-product-regression-sic-20261021-r3
artifact_sha: 5432d5a0b63a7ed3b6f4131270d58d2bec7c293e
pass: 2
amended_at: "2026-10-22T08:04:22Z"
rationale_received: true
amendments:
  - finding: PRC-033
    action: upheld
    note: 'Upheld as a blocker at 5432d5a0: the cure is only promised, and boards 28/34 still draw HOLD as Watch, don''t chase in warn ink and SELL as Protect gains, with the engine word in a closed drawer. On the author''s question, yes: a frontend-mapped doctrine chip in warn ink beside a visible bullish engine HOLD still regresses baseline C15 (research/reference_integrity/sector-intelligence-cycles-20261021/baseline.yml:275, "do not calculate a competing stance in the frontend") and C17 (keep stance and entry suitability separate). The engine-first line cures the hiding, but a second, frontend-derived action with contradicting ink is exactly a competing stance. I will accept either (a) the engine stance line alone (now.stance/stance_zh with the tone class, as templates/sector_cycles.js:157-162), with the doctrine vocabulary given only as a non-chip legend gloss; or (b) a doctrine chip whose value is a producer-stamped field (an engine-owned mapping emitted in the artifact and cited by file:line), whose ink never contradicts now.tone, and which is labeled as the engine''s mapping, never as a separate call.'
  - finding: PRC-034
    action: upheld
    note: 'Minor; still present at 5432d5a0. It is cured when every enum_zh.json value carries a real origin (a production file:line containing that exact string, or the literal tag deck copy) and grep confirms each cited string exists at its cited line.'
  - finding: PRC-035
    action: upheld
    note: 'Minor; still present at 5432d5a0. The proposed eyebrow is acceptable, provided no grader label on boards 28-36 implies a measured value where no number is drawn and the Neutral-included caption is labeled as a definition.'
  - finding: PRC-025
    action: upheld
    note: 'Still partially cured at 5432d5a0 (XLC Bottoming vs Rolling over on boards 28/34). The family-match test is the right cure: the face read appears only when its phase word belongs to the phase_v2 family, otherwise the read is withheld to the drawer and the face shows a labeled state naming both values. This should be checked on XLC in a re-capture, with the test function cited by file:line, and the engine-side cure stays a producer finding.'
  - finding: PRC-027
    action: upheld
    note: 'Still partially cured at 5432d5a0 (14/16, gaps declared honestly). It is cured when the two gap cells are frozen as boards with manifest rows and board 27 cites them as drawn, 16/16.'
  - finding: PRC-031
    action: upheld
    note: 'Still partially cured at 5432d5a0. It is cured when the ZH face of every ZH board carries no English sector names or page/source labels outside code/drawer elements, sector names come from a cited production ZH source or are tagged deck copy, and verbatim read_zh appears only in the drawer.'
  - finding: PRC-022
    action: upheld
    note: 'Still partially cured at 5432d5a0. A scoped manifest note on the frozen Paper boards that names the up/3m PRIOR 33% cell (and the 38%-of-41 Abstained card) as illustrative and superseded by the R4 hazard cells is an acceptable cure, because the normative home moves to R4; the Paper pixels need not change.'
disposition_notes: 'Judged as frozen at 5432d5a0; no promised cure changes a status. The round-2 cures stand: PRC-024, 026, 028, 029, 030 and 032 cured. The re-freeze commit 793b1aab touches only research manifest.yml/proposal.yml and does not alter design_refs/ or mockups/. Dossier: extending the board-16 note to name the placeholder phase ages and the Slow cycle MODEL rhythm label as superseded by boards 28/34 is an acceptable cure (it would move dossier to EQUIVALENT only once Confluence is homed; until then it stays WORSE). C19: one explicitly labeled FIXTURE state card showing the KM PRIOR cell is admissible as the C19 state home, because the 2026-10-19 capture carries no PRIOR cell; it must use the producer field shape (source PRIOR, cell_verdict, epoch in the drawer), print the fixture label on the face, and never sit in a live card. C23: the declared data gap plus the PRC-035 eyebrow is acceptable. The five journey tasks stay UNKNOWN in this RIG; they are recorded as outside the drawn scope, which is not a cure.'
user_tasks_after_rationale: {brief: EQUIVALENT, cycles: WORSE, dossier: WORSE, rotation: EQUIVALENT}
verdict: BLOCK
conditions:
  - 'SIC-V3 stance: on every Cycles card (boards 28-31, 34-36 and the new boards), the engine stance is drawn on the face from now.stance / now.stance_zh with the tone class from now.tone, matching templates/sector_cycles.js:157-162; a missing stance renders Stance unavailable with no chip; no frontend-derived stance chip is drawn unless its value is a producer-stamped field cited by file:line, and no stance ink contradicts now.tone.'
  - 'SIC-V3 read: the face read appears only when its phase word belongs to the phase_v2 family of the card''s chip (test cited by file:line); otherwise the read is drawer-only and the face shows a labeled state; the XLC row demonstrates this on a captured board.'
  - 'SIC-V3 coverage: board 27 cites 16/16 drawn cells with manifest rows and png_px for the two new boards.'
  - 'SIC-V3 ZH face: no English sector names or page/source labels on the ZH face outside code/drawer elements on boards 30, 34, 35, 36 and the new ZH boards; every ZH string is tagged with a production file:line or deck copy.'
  - 'SIC-V3 enum provenance: every enum_zh.json value names a real origin (an existing production file:line containing the exact string, or deck copy), verified by grep.'
  - 'SIC-V3 grader: no grader label implies a measured value where no number is drawn; the Neutral-included caption is labeled as a definition.'
  - 'SIC-V3 supersession: the board 1/6 notes name the PRIOR 33% cell and the Abstained card as illustrative and superseded; the board 16 note names the placeholder phase ages and the Slow cycle MODEL label as superseded by boards 28/34.'
  - 'SIC-V3 PRIOR home: exactly one labeled FIXTURE state card shows a KM PRIOR cell in the producer field shape, with the fixture label printed on the face, outside any live sector card, and the capability_boards C19 row cites it.'
-----END RIG AMENDMENT-----
