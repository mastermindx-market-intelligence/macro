---
key: A-GUARDS-CORRECT-TOLERANCE-FOR-AN-ABSENT-SUBJECT-STILL-LIES-IN-ITS-VERDICT
claim: >
  `scripts/check_board_contradictions.py` printed `site/factordata/us_standouts.json passes
  all 5 board invariants` about a file that does not exist, and the bug was NOT the tolerance.
  `_check()` returns `[]` for an absent artifact deliberately and correctly — a first run, or
  a nightly that has not emitted yet, is not a violation — but `main()` read an empty
  violation list as COMPLIANCE, so "0 violations because I checked and found none" and "0
  violations because there was nothing to check" printed one indistinguishable sentence. The
  defect lives at the JOIN between a correct predicate and its reporter, which is why 60+
  tests in `tests/test_board_contradictions.py` never caught it: every one of them writes a
  `tmp_path` artifact FIRST, so not one ever asked what the guard says when there is no
  subject. `scripts/check_inline_js.py` carried the ordinary form of the same thing — it walks
  `site/` and printed `OK — inline scripts and on*= handlers under site parse cleanly` over an
  empty tree. Both are now `checked N of M`. **Neither was vacuous in CI**: that artifact is
  TRACKED (`git ls-files --error-unmatch site/factordata/us_standouts.json` resolves), so a
  full CI checkout always has it. The exposure was (a) every fleet session worktree, which is
  sparse by default, so a session running the guard before pushing got a false green, and (b)
  latency — rename, relocate or stop emitting that path and the guard degrades silently from
  validating five invariants to asserting that it did, with green CI, forever.
  `scripts/sparse_guard.py` already existed for exactly this and its docstring names the SEVEN
  guards measured on 2026-08-13; these two were simply missed by that sweep. Nine now.
falsifier: >
  Before: in a sparse worktree (`site/` cone-omitted), `python3
  scripts/check_board_contradictions.py` -> rc=0 and the string "passes all 5 board
  invariants"; `python3 scripts/check_inline_js.py` -> rc=0 and "parse cleanly". After: both
  rc=1 with `::error title=…-vacuous::checked 0 item(s) and would have reported a PASS`.
  Pointed at an absent artifact OUTSIDE the checkout (an honest zero, no sparseness):
  rc=0 and `SKIPPED — checked 0 of 1 artifact(s) … NO invariant was evaluated — this is not a
  pass`. Disproved by any invocation that examines zero subjects and prints an affirmative
  pass, or by a full checkout being refused for an honest zero. Mutation-proven: five mutants
  (each refusal removed, each reach count dropped, and the absent-artifact claim restored) are
  all CAUGHT by `tests/test_sparse_guard_refusals.py` + `tests/test_board_contradictions.py`
  + `tests/test_check_inline_js.py`; 205 passed / 1 skipped across the affected suites.
so_what: >
  Two transferable rules. FIRST: an exit-code test cannot pin a verdict SENTENCE. The mutation
  that restored "an absent artifact passes all 5 board invariants" kept all five of the
  parametrized sparse-refusal cases green, because they assert `rc == 0` and that the remedy
  string is absent — never what the guard claimed. The sentence needed its own test, and this
  was found only by mutating a fix that already looked well covered. SECOND: when a predicate
  is deliberately tolerant of a missing subject, the tolerance and the REPORT need separate
  repairs — keep the exit code, fix the claim. Where to look for the next instance: a guard
  whose "no findings" path is reached by two different routes it cannot name apart. And do not
  hunt this family lexically — three successive regex scans over `scripts/` returned 177, then
  57, then a set that included guards which already print their count, because a lexical
  question cannot answer a semantic one. The cheap discriminator is a positive control: run
  the instrument against an empty subject set and read what it says.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  claude storage-worktree-lifecycle-law seat, session f71c3451. Positive control was the
  ambient sparse worktree itself (`scripts/worktree_sparse.py status` -> data, mockups, site,
  verify_shots omitted); all 27 `site/`-reading guards were run against it, nine already
  refused correctly and named the opt-in command, three exited 0 of which two were these.
scope:
  - macro
confidence: verified
---

## The three scans that did not work, and the one that did

The convergent law from the tenth instance said to look "wherever a reach figure is already
computed for a machine consumer and never shown to a human". Applied literally as a grep over
`scripts/`, that produced **177** candidates; sharpened to guards printing a pass verdict, **57**;
and the second number was wrong too — several of those guards do print their count, and the
regex window had merely clipped it. Each scan returned a clean, plausible, unfalsifiable number,
which is the exact failure mode the law describes, committed by the instrument built to find it.

What worked was a **positive control**: this session's worktree is sparse, so `site/` is genuinely
absent, and the honest question — *what does this guard say when it examined nothing?* — could
simply be asked of all 27 guards that read that tree. Nine already answered correctly. That is
the useful shape of the finding: the fleet had mostly learned this lesson and written the shared
helper for it; what remained was two stragglers and one unpinned sentence.

## Why `check_board_contradictions` is the sharper of the two

The other eight guards in this family have a walk that finds nothing. This one has a predicate
that is *right*:

```python
    if not p.exists():
        # Absent artifact is not a violation (first run or not yet emitted)
        return []
```

That comment is correct and the behaviour should not change. The falsehood was 140 lines away,
in a reporter that had no way to distinguish the two producers of an empty list — so the fix is
two-part and only the first part belongs to `sparse_guard.py`:

| route to "0 violations" | before | after |
|---|---|---|
| checked the artifact, found nothing wrong | `OK — … passes all 5 board invariants` | `OK — checked 1 of 1 artifact(s); … passes all 5` |
| artifact absent, tree sparse-omitted | *(identical line, rc=0)* | `REFUSED — checked 0 item(s) and would have reported a PASS` |
| artifact absent, full checkout (honest) | *(identical line, rc=0)* | `SKIPPED — checked 0 of 1 … this is not a pass` (rc=0) |

## The mutation that mattered

Four of five mutants were caught immediately. The survivor was restoring the false claim on the
absent path — every sparse-refusal case stayed green, because that suite pins exit codes. A
verdict sentence is a separate assertion from a verdict code, and a fix whose only tests are
code-shaped is a fix that can be silently un-made.
