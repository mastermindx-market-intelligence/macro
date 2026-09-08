---
key: MACRO-COMMAND-STANCE-IS-GUIDANCE
question: >
  Is the Macro Command stance line allowed to tell a customer what to do
  (watch / start here / no action today), or must it stay a description that
  "never tells you what to do"?
answer: >
  Guidance. The stance is reviewed copy keyed on (section_id, state_key) that
  answers "so what do I do" in plain words — watch, start with this section,
  or no action today — and it is never a score, never a ranking, and never a
  fused composite. The no-score / no-ranking clause of the earlier "it never
  tells you what to do" sentence is kept; the prohibition on guidance is
  dropped.
rationale: >
  Chairman front-end clarity law requires every panel to answer "so what do I
  do" in ten seconds. A stance that only restates the reading fails that law.
  Spec §5 row 62's "never tells you what to do" clause was written to block
  a model-originated recommendation and a page-level score; it was not written
  to forbid reviewed, fail-closed guidance copy. Shipping the stance without
  recording that split would leave the next session believing the dropped
  clause still binds [G14].
alternatives:
  - option: Keep the stance as description-only ("it never tells you what to do")
    why_not: >
      Violates the clarity law. The customer would get a tone bar with no next
      action, and the panel's watching bullets would have to smuggle the
      guidance, which is the wrong slot.
  - option: Let the LLM originate the stance from implications.entries[0]
    why_not: >
      A5 measured those strings as machine text that blow the word budget and
      leak internal ids. LLMs never originate signals (A7).
evidence:
  - "P3 design pin §B D3 — stance is reviewed copy keyed on (section_id, state_key)"
  - "P3 design pin §I.2 — every stance names an action or an explicit watch"
  - "templates/macro_monetary.html.j2 P1 header — 'it never tells you what to do' dropped; no-score / no-ranking clause kept"
  - "DNR:KILL-FUSED-COMPOSITE, DNR:KILL-REGIME-SCORECARD — no score, no ranking"
affects:
  - "templates/macro_monetary.html.j2"
  - "lib/macro_suite_labels.py"
  - "WS:MARKET-ONTOLOGY"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-08
---

## Grounds

Macro Command P3 ships the first five section stances. The P1 template
preamble said the page "never tells you what to do". That sentence blocked
two different things: (1) a model-originated recommendation, and (2) a page
score or ranking. (1) stays forbidden — the stance is a reviewed table, and a
missing key raises and writes no page. (2) stays forbidden — no score. What
is dropped is the reading that a reviewed "Watch — don't chase" line is
itself a violation.

## What would reopen this

A stance that originates a trade, a size, or a fused grade; or a return to
description-only copy that fails the clarity law on a live panel.
