# Marketing copy: grouped-number rejection — 2026-11-14

## Reproduction at committed source

`copywriter._NUMBER_RE` had no comma-group branch. Its bare-integer branch
reads `221,000` as `221` and `000`, and `219,000` as `219` and `000`. A
model-generated sentence quoting *exactly* the source packet's figures then
fails `validate_copy` with four `number not in whitelist` violations, even when
the whitelist contains `["221,000", "219,000"]`.

This is a writer-stage rejection, upstream of the outbox/approval evidence
handoff in #11249. The prior content-plan audit found numerous number-rule
drops, but no ledger census isolates this comma subgroup. No numerical estimate
of recovered posts is claimed.

## Repair and safety

Parse valid thousands groups as one numeric token before the general percent,
price and integer branches. Allow only comma-grouping equivalent spellings in
the writer's whitelist check; an altered underlying number remains rejected.

Six targeted source tests passed with direct execution: grouped count and price,
seven-digit amount, grouping equivalence, invented 222,000 negative, existing
percent/price/multiplier forms, and malformed grouping. `compileall` and
`git diff --check` passed. The local runtime lacks pytest; hosted binding CI
remains the release gate. No generation, outbox, or X publication was invoked.

**Integration:** Held editorial PR #7493 changes other `copywriter.py` hunks;
do not erase, override or clear its CHANGES_REQUESTED/merge-blocked state.
PR #11249 separately addresses the outbox/approval evidence loss. Both must be
integrated through normal exact-head CI/holds before fresh production proof.
