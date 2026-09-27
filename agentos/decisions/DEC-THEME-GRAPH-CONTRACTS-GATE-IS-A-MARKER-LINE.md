---
key: THEME-GRAPH-CONTRACTS-GATE-IS-A-MARKER-LINE
question: "Does exit code 0 from scripts/check_theme_graph_contracts.py prove the theme-graph contracts hold?"
answer: >
  No, and the earlier definition of this operation's Gate C as "the script exits
  0" is WITHDRAWN as hollow. Gate C is redefined as: stdout contains the literal
  string `theme graph contracts OK`. The script has two independent paths to a
  zero exit with contracts violated. Without `--strict` a real breach returns 0
  by design (the flag's own help text calls the default "advisory rc 0"). And
  when breaches are empty but notices are not, the script returns 0 while
  SUPPRESSING its own success line - so rc 0 covers both "all good" and
  "indeterminate". Passing `--strict` is still worthwhile so a breach is also
  non-zero, but `--strict` plus rc 0 is not sufficient, because it clears
  breaches and says nothing about notices. If `data/` is not materialised the
  honest verdict is INDETERMINATE, not pass.
rationale: >
  A gate whose pass condition is satisfied by a tree that violates the contract
  is not a gate; it is a ritual that converts an untested dimension into a
  passing one. Two independent holes were found in this one. The weaker hole
  (indeterminate notices) was raised by the shared script's owner. The stronger
  hole is the advisory breach path, and it was this seat's own exposure: every
  Gate C result this operation had recorded was an exit code, so a breach would
  have read as green. It is not a theoretical reading - the shared owner's own
  run on materialised data produced 1168 identity_resolution rows violating the
  state-to-ids biconditional and exited 0 anyway. The marker line is the correct
  instrument because it is printed on exactly one path, the one where both
  breaches and notices are empty, which is the only state that actually means
  the contracts hold.
alternatives:
  - option: "Keep exit code 0 as the gate and always pass --strict."
    why_not: >
      --strict only makes a BREACH non-zero. The notices path still returns 0
      with the success line suppressed, so an indeterminate run is
      indistinguishable from a clean one by exit code alone.
  - option: "Patch the script so notices also return non-zero."
    why_not: >
      It is a shared script owned by another lane and consumed by several
      verticals; changing its exit semantics from a Robotics carrier would alter
      other lanes' gate results without their adjudication. Reading the marker
      line costs nothing and changes no shared behaviour. The measurement was
      handed to the owner instead.
  - option: "Treat a missing data/ directory as a pass because nothing breached."
    why_not: >
      Nothing could breach, because nothing was read. That is the instrument
      producing a confident null, which is the failure this operation has
      already recorded twice.
evidence:
  - "scripts/check_theme_graph_contracts.py at #7870 head a0d7b054ff23, 87600B: line 1099 prints \"theme graph contracts OK ...\" guarded by `if not breaches` (1097) AND `if not notices` (1098); line 1101 `return 0`; line 1109 `return 1 if strict else 0`; line 1582 help text \"return 1 on a breach (CI); default is advisory rc 0\""
  - "Same line numbers verified independently at 1e38d5c955dc and a0d7b054ff23"
  - "Controls on the read: 21 occurrences of 'def ' (positive), 0 occurrences of a nonsense token (negative)"
  - "Shared owner's empirical confirmation on materialised data: 1168 identity_resolution rows violating the state<->ids biconditional, exit 0"
  - "Macro PR #7870 comment 5852920768 (this measurement posted to the shared owner, including this seat's own exposure)"
affects:
  - "WS:GMI-THEME-GRAPH"
  - "scripts/check_theme_graph_contracts.py"
confidence: high
reversibility: easy
decided_by: "session 17c9f82c-8981-43d5-bf95-307691cb27cd (principal seat, operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001)"
decided_at: 2026-09-26
---

# Scope of this record

This fixes what Gate C means for operation `gmi-robotics-fable-ceo-e2e-20260923-chairman-001`,
and reports a measured property of a shared script. It does not purport to redefine any other
vertical's gate or to change the script's behaviour. Any lane that currently records a Gate C
result as an exit code is relying on a condition the script does not enforce, which is why the
measurement is recorded here rather than left on a PR comment thread.

# The falsifier

If the script is later changed so that both the breach path and the notices path return non-zero,
exit code 0 becomes sufficient and this record should be superseded rather than edited. Until
then, a Gate C claim that cites an exit code and not the marker line is unproven, in either
direction.
