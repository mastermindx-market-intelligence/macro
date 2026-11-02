---
key: TERMINAL-DRAWING-PANE-OWNERSHIP-OVER-CLIP
question: >
  A price-bearing drawing gesture that crosses a pane separator persisted the
  neighbouring pane's reading as a price (Stoch 44 saved as a $44 price), which is what
  produced the reported giant Date + Price Range rectangles with impossible percentages.
  An open PR already clipped the rendered rectangle to the price pane. Ship that, extend
  it, or replace it?
answer: >
  Replace it. A gesture owns the pane it started in for its whole lifetime: snap() takes a
  paneLock, a new gesture hit-tests once on pointerdown, and every continuation passes the
  lock instead of re-hit-testing the pointer's current pane. The locked pointer Y is
  clamped to the owning pane's visible band BEFORE conversion to a price. The clip is kept
  as the cosmetic half only. Delivered by adopting the existing carrier branch
  (mastermind-terminal #753, sol/terminal-range-pane-ownership-20260926) through a
  non-destructive --no-ff merge of its exact observed head onto current master, not by a
  second implementation and not by force-pushing another writer's branch.
rationale: >
  Clipping is a render-time mask, so it hides the symptom and leaves the DOCUMENT wrong:
  the saved endpoint is still an oscillator value on a price scale, so the measurement,
  the percentage label, and every later edit or reload stay wrong. Measured, not argued —
  with the pane lock and clamp removed from snap() and the clip left in place, 8 ownership
  tests fail while the 2 tests that only assert clipping still pass. Clamping in PIXEL
  space and converting afterwards is also what keeps the repair correct on logarithmic and
  inverted scales, which a clamp applied to the converted price would not be.
alternatives:
  - option: Merge the clip-only PR now and fix the persisted value later
    why_not: >
      It would close the operator-visible report while leaving every affected saved
      drawing numerically invalid, and a later repair would then have to decide whether to
      rewrite user documents. Not rewriting them is only free while the corrupt writes are
      still being prevented at the source.
  - option: Re-implement the fix instead of adopting the carrier
    why_not: >
      The carrier's diagnosis and mechanism were correct and its author holds the branch.
      Duplicating it discards their authorship for no technical gain and creates two
      competing heads for one defect.
  - option: Push the integration onto the carrier's own branch
    why_not: >
      Its base was 47 commits behind master and the tree needed changes that should not be
      attributed to its author. A merge preserves all three of their commits as ancestors
      while keeping the new work attributable.
  - option: Repair historical endpoints on load
    why_not: >
      A silent rewrite of saved user drawings cannot be distinguished from data loss by the
      person who drew them, and the packet forbids it. Saved drawings are served back
      unrepaired and stay editable.
evidence:
  - "mastermind-terminal #774 — fix(chart): bind a price-bearing drawing gesture to its owning pane scale"
  - "mastermind-terminal #753 — adopted carrier, head 4b4cf07185100b182495942ce80807c8035842bb"
  - "mastermind-terminal #748 — clip-only, superseded, left open and on hold"
  - "Mutation control: paneLock + clamp removed from snap(), clip retained -> 8 ownership tests red, 2 clip-only tests green"
affects: ["terminal/components/ChartPanel.tsx", "terminal/e2e/drawing-system.spec.ts"]
confidence: high
reversibility: easy
decided_by: opus-terminal04-session
decided_at: 2026-09-29
---

The clip is not wrong, it is just not the fix. Keep it; do not rely on it.
