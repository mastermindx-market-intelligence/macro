---
key: MACRO-COMMAND-STANCE-IS-GUIDANCE
question: >
  Is the Macro Command stance line allowed to tell a customer what to do
  (watch / start here / no action today), or must the composition footer
  keep disclaiming that the page "never tells you what to do"?
answer: >
  The stance line is guidance. The footer no longer disclaims it. The stance
  is reviewed copy keyed on (section_id, state_key) that answers "so what do
  I do" in plain words — watch, start with this section, or no action today —
  and it is never a score, never a ranking, and never a fused composite. Spec
  §5 row 62 keeps the no-score / no-ranking clause and drops "and it never
  tells you what to do."
rationale: >
  Chairman front-end clarity law requires every panel to answer "so what do I
  do" in ten seconds. A stance that only restates the reading fails that law.
  Spec §4 ships the stance as reviewed guidance. Spec §5 row 62's "never tells
  you what to do" clause was written to block a model-originated recommendation
  and a page-level score; it was not written to forbid reviewed, fail-closed
  guidance copy. Shipping the stance while the footer still disclaimed it would
  leave the next session believing the dropped clause still binds [G14].
alternatives:
  - option: Keep the footer clause "it never tells you what to do"
    why_not: >
      Contradicts §4's stance line. The customer would read a guidance sentence
      and then a footer that denies the page may say what to do.
  - option: Let the LLM originate the stance from implications.entries[0]
    why_not: >
      Those strings are machine text that blow the word budget and leak
      internal ids. LLMs never originate signals (A7).
evidence:
  - "Frozen spec §4 — the stance line is the panel's guidance slot"
  - "Frozen spec §5 row 62 — exact Plain EN/ZH footer; 'never tells you what to do' dropped"
  - "templates/macro_monetary.html.j2 — composition footer uses row 62's exact strings"
  - "DNR:KILL-FUSED-COMPOSITE, DNR:KILL-REGIME-SCORECARD — no score, no ranking"
  - "Spec §8 amendment (Meta-CEO A 2026-09-08): at ≤768 the `.mc-analyst` control is the last chip of the collapsed horizontal rail, not a page-level floating pill. Label stays Ask the analyst / 向分析师提问."
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

Macro Command's stance is reviewed guidance. Spec §5 row 62 rewrites the
composition footer to:

> This page shows what each workspace published. It produces no score and no
> ranking of its own.

The no-score / no-ranking clause is load-bearing for G3. The dropped clause
("and it never tells you what to do") no longer disclaims the stance.

## What would reopen this

A stance that originates a trade, a size, or a fused grade; or a return of
the "never tells you what to do" footer that contradicts the live stance.
