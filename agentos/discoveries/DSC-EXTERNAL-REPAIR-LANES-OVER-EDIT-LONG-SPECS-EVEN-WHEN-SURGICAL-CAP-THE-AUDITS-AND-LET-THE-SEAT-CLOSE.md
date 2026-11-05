---
key: EXTERNAL-REPAIR-LANES-OVER-EDIT-LONG-SPECS-EVEN-WHEN-SURGICAL-CAP-THE-AUDITS-AND-LET-THE-SEAT-CLOSE
claim: >
  A MiniMax repair lane given rulings against a ~1,900-line design spec closes most
  enumerated residuals each round but also re-decides sections it was not asked to touch —
  and a SURGICAL packet (enumerated edits with anchors, "touching any other file fails the
  lane") stops cross-FILE drift but NOT within-file drift: the surgical round 4 still added a
  selector that hid the stepper spine, changed the light focus ring and introduced a class
  that does not exist in theme.css, all outside its enumerated edits. The loop ended only by
  capping the audits at five and having the seat apply the final build-class fixes directly.
evidence:
  - PR #7903 heads 469e932e → 867fd6e9 (round 1; also appended 78 lines to agentos/handoffs/GMI-FINANCE-INTELLIGENCE-2026-09-24.md, reverted at fdc84cb8) → aef82d77 (round 2) → 7a23b05c (round 3) → 7ec8fa6a (surgical round 4); read-only Opus audits 5810133462, 5810923955, 5812280671, 5812943971 each FAIL on carried residuals plus NEW findings in untouched sections
  - Audit 5 on the surgical head 7ec8fa6a: FAIL-BUILD-CLASS-ONLY; hunks outside D1–D3/B2–B13 at spec lines 631/655 (spine regression), 595/764 (light ring), 427/452 (`mx-tbl`); seat freeze repair 2e5c3df6 closed them in one commit
falsifier: >
  A future external repair round on a spec of similar length whose audit reports zero hunks
  outside the packet's enumerated edits (`git diff -U0 <before> <after>` attributed line by
  line) refutes the within-file half; a lane loop on such a spec that converges to PASS
  without a seat-applied closing commit refutes the "seat closes" half.
so_what: >
  Commission spec repairs as enumerated edits with anchors from round 2 onward; require the
  lane to quote `git diff -U0` attributed to its edit list; cap the loop at five audits; when
  the fifth audit classifies every residual build-class, the SEAT applies the CSS/markup majors
  itself before any lane that copies the spec verbatim (the mockup), and the rest rides the
  build packet's residual appendix — never a sixth repair round.
kind: landmine
confidence: verified
verified_at: 2026-09-24T13:05:00Z
verified_by: >
  gh pr view 7903 --json commits --jq '[.commits[]|.oid[0:8]]'; gh api repos/mastermindx-market-intelligence/macro/issues/7903/comments --jq '[.[]|select(.body|test("AUDIT|audit"))|.id]'
scope:
  - macro
---

Round-by-round: each lane pass closed roughly three quarters of the enumerated residuals and each audit found two to four new defects elsewhere; the surgical round cut cross-file drift to zero but still produced three out-of-scope hunks. Cost: five Opus read-only audits, one merge-of-main repair of the handoff edit, one seat commit.
